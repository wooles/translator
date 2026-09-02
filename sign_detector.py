# -*- coding: utf-8 -*-
"""
Visual Sign Detection & OCR Engine Module.
Detects missing, hardcoded on-screen title cards, locations, and time banners
(e.g., 'PRESENT DAY / げんざい' -> '[ CZASY WSPÓŁCZESNE ]') and generates top-aligned subtitles.

Equipped with 3 strict anti-collision safety guards to prevent duplicate subtitles on translated frames.
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
    screen_region: Optional[str] = Field(
        default="top",
        description="Rzeczywiste położenie tekstu/planszy na kadrze: 'bottom_right', 'bottom_left', 'top_right', 'top_left', 'top_center', 'center', 'bottom_center'"
    )


class VisualSignDetector:
    """
    Intelligent detector for missing on-screen title cards with 3 anti-collision safety guards.
    """

    @staticmethod
    def find_subtitle_gaps(
        subs: pysubs2.SSAFile,
        min_gap_ms: int = 3500,
        margin_ms: int = 1500,
        max_gaps_to_scan: int = 8
    ) -> List[Tuple[int, int]]:
        """
        SAFETY GUARDS 1 & 2 (Collision Guard & Zero-Gap Rule):
        Finds time intervals (gaps) in subtitle file where for at least min_gap_ms
        there are NO subtitles (neither dialogue nor signs), maintaining safe margin_ms.
        """
        if not subs.events:
            return []

        # Chronological event sorting
        sorted_events = sorted(subs.events, key=lambda ev: ev.start)
        
        # Merge overlapping events into occupied time spans
        occupied_intervals: List[Tuple[int, int]] = []
        for ev in sorted_events:
            # Skip empty events
            if not ev.text.strip():
                continue
            
            s = max(0, ev.start - margin_ms)
            e = ev.end + margin_ms
            
            if occupied_intervals and occupied_intervals[-1][1] >= s:
                # Extend last interval
                occupied_intervals[-1] = (occupied_intervals[-1][0], max(occupied_intervals[-1][1], e))
            else:
                occupied_intervals.append((s, e))

        gaps: List[Tuple[int, int]] = []
        
        # 1. Check gap before first subtitle
        if occupied_intervals and occupied_intervals[0][0] > min_gap_ms:
            gaps.append((1000, occupied_intervals[0][0]))

        # 2. Check gaps between subtitles
        for i in range(len(occupied_intervals) - 1):
            gap_start = occupied_intervals[i][1]
            gap_end = occupied_intervals[i + 1][0]
            if (gap_end - gap_start) >= min_gap_ms:
                gaps.append((gap_start, gap_end))

        # Limit scanned gaps to longest/most prominent ones
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
        Scans frames from designated safe gaps and generates ASS Sign events for detected cards.
        Includes seamless fallback switching and circuit-breaker for 503 server load.
        """
        if not gaps or not os.path.exists(video_path):
            return []

        detected_events: List[pysubs2.SSAEvent] = []
        logger.info(f"VisualSignDetector: Scanning {len(gaps)} safe time gaps for title cards...")

        prompt = """Jesteś Ekspertem Wizyjnym Przekładu Audiowizualnego (AVT Sign Detector).
Przeanalizuj przesłaną klatkę wideo z anime i oceń, czy widnieje na niej GŁÓWNA PLANSZA TYTUŁOWA, NAZWA MIEJSCA, DATA lub BELKA CZASOWA (np. 'PRESENT DAY / げんざい', 'TOKIO', 'ROK 1907', 'PROLOG', tytuł odcinka).

ZASADY BEZPIECZEŃSTWA (FILTR ANTYKOLIZYJNY):
1. Zwróć is_title_or_banner = True TYLKO dla wyraźnych, centralnych plansz/napisów ekranowych przeznaczonych dla widza (krótkie hasła: 1-4 słowa).
2. Zwróć is_title_or_banner = False jeśli:
   - To zwykła scena z postaciami lub krajobraz bez dużych napisów.
   - Tekst na ekranie to gęsty tekst z tła (strona w notesie, gazeta, list, ekran komputera, manga, plakat w tle).
   - Tekst jest nieczytelny lub nie stanowi planszy narracyjnej.
3. Jeśli is_title_or_banner = True:
   - podaj zwięzłe, naturalne polskie tłumaczenie w translation_pl (np. 'CZASY WSPÓŁCZESNE', 'OBECNIE', 'LONDYN, 1888').
   - wskaż w screen_region precyzyjne położenie tekstu na kadrze: 'bottom_right' (prawy dolny róg), 'bottom_left' (lewy dolny róg), 'top_right' (prawy górny róg), 'top_left' (lewy górny róg), 'top_center' (górna belka), 'center' (środek kadru).

Zwróć wynik w formacie JSON zgodnym ze schematem DetectedSign."""

        consecutive_errors = 0

        for gap_start, gap_end in gaps:
            if consecutive_errors >= 2:
                logger.info("VisualSignDetector: Skipping remaining gaps due to Google 503 load and finalizing subtitles...")
                break

            # Timestamp at middle of gap
            mid_ms = (gap_start + gap_end) // 2
            frame_path = None
            try:
                frame_path = extract_frame_at_timestamp(video_path, mid_ms, max_width=640)
                if not frame_path or not os.path.exists(frame_path):
                    continue

                pil_img = Image.open(frame_path)
                
                try:
                    gen_cfg_kwargs = {
                        "response_mime_type": "application/json",
                        "response_schema": DetectedSign,
                        "temperature": 0.1,
                    }
                    if "3.7" in model.lower() or "3.1-pro" in model.lower():
                        gen_cfg_kwargs["thinking_config"] = types.ThinkingConfig(thinking_budget=0)

                    response = client.models.generate_content(
                        model=model,
                        contents=[prompt, pil_img],
                        config=types.GenerateContentConfig(**gen_cfg_kwargs)
                    )
                    consecutive_errors = 0

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
                                prefix = TypesettingColorMatcher.enhance_sign_typesetting(
                                    sign_type=sign_info.banner_type or "sign",
                                    image_path=frame_path,
                                    region=sign_info.screen_region or "top"
                                )
                                styled_text = f"{prefix}[ {clean_pl} ]"
                            except Exception:
                                styled_text = r"{\an8\fs26\bord1.5\shad1\c&HFFFFFF&\3c&H101020&}[ " + clean_pl + r" ]"
                            
                            new_ev = pysubs2.SSAEvent(
                                start=event_start,
                                end=event_end,
                                text=styled_text,
                                style="Sign"
                            )
                            detected_events.append(new_ev)
                            logger.info(f"VisualSignDetector: Detected sign at {event_start/1000:.1f}s: '{sign_info.original_text}' -> '[ {clean_pl} ]'")
                except Exception as e_model:
                    consecutive_errors += 1
                    logger.debug(f"VisualSignDetector: Model error: {e_model}")

            except Exception as e:
                consecutive_errors += 1
                logger.debug(f"VisualSignDetector: Error analyzing gap {gap_start}-{gap_end}ms: {e}")
            finally:
                if frame_path and os.path.exists(frame_path):
                    try:
                        os.remove(frame_path)
                    except OSError:
                        pass

        return detected_events
