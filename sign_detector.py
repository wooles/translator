# -*- coding: utf-8 -*-
"""
Moduł Wizyjnej Detekcji Plansz i Napisów Ekranowych (Visual Sign Detector & OCR Engine).
Wykrywa brakujące w pliku napisów, wtopione w wideo plansze tytułowe, lokacje i ramy czasowe
(np. 'PRESENT DAY / げんざい' -> '[ CZASY WSPÓŁCZESNE ]') i generuje dla nich eleganckie napisy górne.

Posiada 3 twarde bezpieczniki antykolizyjne zapobiegające dublowaniu napisów na tłumaczonych kadrach.
"""

import os
import json
import logging
import tempfile
from typing import List, Tuple, Optional, Dict, Any
from pathlib import Path
from pydantic import BaseModel, Field
import pysubs2
from PIL import Image

from google import genai
from google.genai import types
from extract import extract_frame_at_timestamp

logger = logging.getLogger("sign_detector")


class DetectedSign(BaseModel):
    is_title_or_banner: bool = Field(
        description="True TYLKO jeśli na kadrze widnieje duża, centralna plansza tytułowa, data, nazwa miejsca lub rama czasowa (np. 'PRESENT DAY', 'ROK 1907', 'TOKIO', tytuł odcinka). False jeśli to zwykła scena, tło lub gęsty tekst z notesu/książki."
    )
    original_text: Optional[str] = Field(
        default="",
        description="Oryginalny tekst planszy (angielski lub japoński, np. 'PRESENT DAY / げんざい')"
    )
    translation_pl: Optional[str] = Field(
        default="",
        description="Zwięzłe, eleganckie polskie tłumaczenie planszy w mianowniku, wersalikami lub zwięzłą frazą (np. 'CZASY WSPÓŁCZESNE', 'ROK 1907', 'TOKIO')"
    )
    banner_type: Optional[str] = Field(
        default="TIME_OR_LOCATION",
        description="Typ planszy: 'TIME_BANNER', 'LOCATION_BANNER', 'EPISODE_TITLE', 'CHAPTER_SIGN'"
    )


class VisualSignDetector:
    """
    Inteligentny detektor brakujących plansz ekranowych z 3 bezpiecznikami antykolizyjnymi.
    """

    @staticmethod
    def find_subtitle_gaps(
        subs: pysubs2.SSAFile,
        min_gap_ms: int = 3500,
        margin_ms: int = 1500,
        max_gaps_to_scan: int = 8
    ) -> List[Tuple[int, int]]:
        """
        BEZPIECZNIK 1 & 2 (Collision Guard & Zero-Gap Rule):
        Wyszukuje przedziały czasowe (luki) w pliku napisów, w których przez co najmniej min_gap_ms
        nie ma ŻADNYCH napisów (ani dialogów, ani znaków), zachowując bezpieczny margines margin_ms.
        """
        if not subs.events:
            return []

        # Sortowanie zdarzeń chronologicznie
        sorted_events = sorted(subs.events, key=lambda ev: ev.start)
        
        # Łączenie nakładających się zdarzeń w zajęte przedziały czasowe
        occupied_intervals: List[Tuple[int, int]] = []
        for ev in sorted_events:
            # Pomijamy zdarzenia całkowicie puste
            if not ev.text.strip():
                continue
            
            s = max(0, ev.start - margin_ms)
            e = ev.end + margin_ms
            
            if occupied_intervals and occupied_intervals[-1][1] >= s:
                # Rozszerzamy ostatni przedział
                occupied_intervals[-1] = (occupied_intervals[-1][0], max(occupied_intervals[-1][1], e))
            else:
                occupied_intervals.append((s, e))

        gaps: List[Tuple[int, int]] = []
        
        # 1. Sprawdzenie luki przed pierwszym napisem
        if occupied_intervals and occupied_intervals[0][0] > min_gap_ms:
            gaps.append((1000, occupied_intervals[0][0]))

        # 2. Sprawdzenie luk między napisami
        for i in range(len(occupied_intervals) - 1):
            gap_start = occupied_intervals[i][1]
            gap_end = occupied_intervals[i + 1][0]
            if (gap_end - gap_start) >= min_gap_ms:
                gaps.append((gap_start, gap_end))

        # Ograniczenie liczby skanowanych luk do najdłuższych / najważniejszych
        gaps.sort(key=lambda g: g[1] - g[0], reverse=True)
        return gaps[:max_gaps_to_scan]

    @staticmethod
    def detect_signs_in_gaps(
        video_path: str,
        gaps: List[Tuple[int, int]],
        client: genai.Client,
        model: str = "gemini-3.7-flash"
    ) -> List[pysubs2.SSAEvent]:
        """
        Skanuje klatki z wyznaczonych bezpiecznych luk i tworzy zdarzenia ASS typu Sign dla wykrytych plansz.
        Posiada mechanizm płynnego przełączania modeli (fallback) oraz circuit-breaker na wypadek 503.
        """
        if not gaps or not os.path.exists(video_path):
            return []

        detected_events: List[pysubs2.SSAEvent] = []
        logger.info(f"VisualSignDetector: Skanowanie {len(gaps)} bezpiecznych luk czasowych w poszukiwaniu plansz...")

        prompt = """Jesteś Ekspertem Wizyjnym Przekładu Audiowizualnego (AVT Sign Detector).
Przeanalizuj przesłaną klatkę wideo z anime i oceń, czy widnieje na niej GŁÓWNA PLANSZA TYTUŁOWA, NAZWA MIEJSCA, DATA lub BELKA CZASOWA (np. 'PRESENT DAY / げんざい', 'TOKIO', 'ROK 1907', 'PROLOG', tytuł odcinka).

ZASADY BEZPIECZEŃSTWA (FILTR ANTYKOLIZYJNY):
1. Zwróć is_title_or_banner = True TYLKO dla wyraźnych, centralnych plansz/napisów ekranowych przeznaczonych dla widza (krótkie hasła: 1-4 słowa).
2. Zwróć is_title_or_banner = False jeśli:
   - To zwykła scena z postaciami lub krajobraz bez dużych napisów.
   - Tekst na ekranie to gęsty tekst z tła (strona w notesie, gazeta, list, ekran komputera, manga, plakat w tle).
   - Tekst jest nieczytelny lub nie stanowi planszy narracyjnej.
3. Jeśli is_title_or_banner = True, podaj zwięzłe, naturalne polskie tłumaczenie w translation_pl (np. 'CZASY WSPÓŁCZESNE', 'OBECNIE', 'LONDYN, 1888').

Zwróć wynik w formacie JSON zgodnym ze schematem DetectedSign."""

        candidate_models = [model]
        for fallback in ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-3.6-flash"]:
            if fallback not in candidate_models:
                candidate_models.append(fallback)

        current_model_idx = 0
        consecutive_errors = 0

        for gap_start, gap_end in gaps:
            if consecutive_errors >= 2:
                logger.info("VisualSignDetector: Pomijanie dalszych luk (przeciążenie serwerów Google 503) i zapisywanie napisów...")
                break

            # Punkt czasowy w środku luki
            mid_ms = (gap_start + gap_end) // 2
            frame_path = None
            try:
                frame_path = extract_frame_at_timestamp(video_path, mid_ms, max_width=640)
                if not frame_path or not os.path.exists(frame_path):
                    continue

                pil_img = Image.open(frame_path)
                
                success = False
                for m_idx in range(current_model_idx, len(candidate_models)):
                    cur_model = candidate_models[m_idx]
                    try:
                        gen_cfg_kwargs = {
                            "response_mime_type": "application/json",
                            "response_schema": DetectedSign,
                            "temperature": 0.1,
                        }
                        if "3.7" in cur_model.lower() or "3.1-pro" in cur_model.lower():
                            gen_cfg_kwargs["thinking_config"] = types.ThinkingConfig(thinking_budget=0)

                        response = client.models.generate_content(
                            model=cur_model,
                            contents=[prompt, pil_img],
                            config=types.GenerateContentConfig(**gen_cfg_kwargs)
                        )
                        current_model_idx = m_idx
                        consecutive_errors = 0
                        success = True

                        if response.text:
                            data = json.loads(response.text)
                            sign_info = DetectedSign.model_validate(data)
                            
                            if sign_info.is_title_or_banner and sign_info.translation_pl:
                                clean_pl = sign_info.translation_pl.strip().strip("[]").upper()
                                event_duration = min(4000, gap_end - gap_start - 500)
                                event_start = gap_start + 250
                                event_end = event_start + max(2000, event_duration)

                                try:
                                    from typesetting_matcher import TypesettingColorMatcher
                                    base_prefix = r"{\fs26\bord2\shad1}[ "
                                    enhanced_prefix = TypesettingColorMatcher.enhance_sign_typesetting(
                                        original_prefix=base_prefix,
                                        sign_type="header",
                                        image_path=frame_path,
                                        region="top"
                                    )
                                    styled_text = f"{enhanced_prefix}{clean_pl} ]"
                                except Exception:
                                    styled_text = r"{\an8\fs26\bord1.5\shad1\c&HFFFFFF&\3c&H101020&}[ " + clean_pl + r" ]"
                                
                                new_ev = pysubs2.SSAEvent(
                                    start=event_start,
                                    end=event_end,
                                    text=styled_text,
                                    style="Sign"
                                )
                                detected_events.append(new_ev)
                                logger.info(f"VisualSignDetector: Wykryto planszę na {event_start/1000:.1f}s: '{sign_info.original_text}' -> '[ {clean_pl} ]'")
                        break
                    except Exception as e_model:
                        err_str = str(e_model).lower()
                        if "503" in err_str or "unavailable" in err_str or "429" in err_str:
                            continue
                        else:
                            break
                
                if not success:
                    consecutive_errors += 1

            except Exception as e:
                consecutive_errors += 1
                logger.debug(f"VisualSignDetector: Błąd analizy luki {gap_start}-{gap_end}ms: {e}")
            finally:
                if frame_path and os.path.exists(frame_path):
                    try:
                        os.remove(frame_path)
                    except OSError:
                        pass

        return detected_events
