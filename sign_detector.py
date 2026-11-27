# -*- coding: utf-8 -*-
"""
Visual Sign Detection & OCR Engine Module.
Detects missing, hardcoded on-screen title cards, locations, and time banners
(e.g., 'PRESENT DAY / げんざい' -> '[ CZASY WSPÓŁCZESNE ]') and generates top-aligned subtitles.

Equipped with 3 strict anti-collision safety guards to prevent duplicate subtitles on translated frames.
"""

import os
import re
import json
import logging
import tempfile
from typing import List, Tuple, Optional, Dict, Any
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
import pysubs2
from PIL import Image

from google import genai
from google.genai import types
from extract import extract_frame_at_timestamp
from model_resolver import (
    is_gemini_4_or_hydrogen_model,
    build_thinking_config,
    resolve_service_tier,
    apply_service_tier_to_config,
)

logger = logging.getLogger("sign_detector")


class DetectedSign(BaseModel):
    model_config = ConfigDict(extra="ignore")
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
    def detect_signs(event_or_events: Any) -> Any:
        """
        Klasyfikuje zdarzenie (lub listę zdarzeń) jako napis ekranowy (Standard 9.5, 2C.2, R3.4):
        - Każde zdarzenie o Name w ("sign", "signs", "txt", "title", "board", "screen")
        - LUB zawierające w tekście tag \\pos( / \\move( przy braku osobowego aktora w Name
        otrzymuje bezwarunkowo flagę is_sign = True.
        """
        def _check_ev(ev: Any) -> bool:
            if ev is None:
                return False
            if isinstance(ev, dict):
                n = str(ev.get("name") or ev.get("actor") or "").strip().lower()
                t = str(ev.get("text") or "").lower()
                is_s = bool(ev.get("is_sign"))
            else:
                n = str(getattr(ev, "name", "") or getattr(ev, "actor", "") or "").strip().lower()
                t = str(getattr(ev, "text", "") or "").lower()
                is_s = bool(getattr(ev, "is_sign", False))
            if is_s:
                return True
            if n in ("sign", "signs", "txt", "title", "board", "screen"):
                return True
            if (r"\pos(" in t or r"\move(" in t) and (not n or n in ("sign", "signs", "txt", "title", "board", "screen")):
                return True
            return False

        if isinstance(event_or_events, list):
            res = []
            for item in event_or_events:
                is_sgn = _check_ev(item)
                if hasattr(item, "is_sign"):
                    setattr(item, "is_sign", is_sgn)
                res.append(is_sgn)
            return res
        return _check_ev(event_or_events)

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
    def is_near_existing_sign(
        event_start_ms: int,
        event_end_ms: int,
        existing_events: Optional[List[Any]],
        proximity_ms: int = 3000,
    ) -> bool:
        """
        Deterministyczny filtr bliskości plansz (Standard 12.2.1 OBS-22):
        Zwraca True, jeśli okno [event_start_ms - proximity_ms, event_end_ms + proximity_ms]
        przecina się z istniejącą planszą / napisem ekranowym w existing_events.
        """
        if not existing_events:
            return False

        for ev in existing_events:
            if ev is None:
                continue
            if isinstance(ev, dict):
                ev_start = int(ev.get("start", 0) or 0)
                ev_end = int(ev.get("end", 0) or 0)
                style_low = str(ev.get("style") or "").strip().lower()
                raw_text = str(ev.get("text") or "")
                is_s = bool(ev.get("is_sign"))
            else:
                ev_start = int(getattr(ev, "start", 0) or 0)
                ev_end = int(getattr(ev, "end", 0) or 0)
                style_low = str(getattr(ev, "style", "") or "").strip().lower()
                raw_text = str(getattr(ev, "text", "") or "")
                is_s = bool(getattr(ev, "is_sign", False))

            if not raw_text.strip() and not is_s:
                continue

            raw_low = raw_text.lower()
            vis_text = re.sub(r"\{[^}]*\}", "", raw_text)
            vis_text = vis_text.replace(r"\N", " ").replace(r"\n", " ")
            alpha_letters = re.sub(r"[^A-Za-zĄĆĘŁŃÓŚŹŻąćęłńóśźż]", "", vis_text)
            is_all_caps_sign = len(alpha_letters) >= 6 and alpha_letters.isupper()

            ev_is_sign = (
                is_s
                or VisualSignDetector.detect_signs(ev)
                or any(tok in style_low for tok in ("sign", "title", "top"))
                or any(tag in raw_low for tag in (r"\an8", r"\an5", r"\pos(", r"\move("))
                or is_all_caps_sign
            )
            if not ev_is_sign:
                continue

            if (event_start_ms - proximity_ms) <= ev_end and (event_end_ms + proximity_ms) >= ev_start:
                return True

        return False

    @staticmethod
    def _normalize_glossary_entries(custom_glossary: Any) -> List[Dict[str, str]]:
        """Normalizes dict or list glossary inputs into unified canonical entries."""
        entries: List[Dict[str, str]] = []
        if not custom_glossary:
            return entries
        if isinstance(custom_glossary, dict):
            for k, v in custom_glossary.items():
                t_en = str(k or "").strip()
                t_pl = str(v or "").strip()
                if t_en and t_pl:
                    entries.append({"term_en": t_en, "translation_pl": t_pl})
        elif isinstance(custom_glossary, (list, tuple)):
            for item in custom_glossary:
                if isinstance(item, dict):
                    t_en = str(item.get("term_en") or "").strip()
                    t_pl = str(item.get("translation_pl") or "").strip()
                else:
                    t_en = str(getattr(item, "term_en", "") or "").strip()
                    t_pl = str(getattr(item, "translation_pl", "") or "").strip()
                if t_en and t_pl:
                    entries.append({"term_en": t_en, "translation_pl": t_pl})
        return entries

    @staticmethod
    def detect_signs_in_gaps(
        video_path: str,
        gaps: List[Tuple[int, int]],
        client: genai.Client,
        model: str = "gemini-2.5-flash",
        custom_glossary: Optional[Any] = None,
        existing_events: Optional[List[Any]] = None,
        sign_proximity_ms: int = 3000,
    ) -> List[pysubs2.SSAEvent]:
        """
        Scans frames from designated safe gaps and generates ASS Sign events for detected cards.
        Includes seamless fallback switching and circuit-breaker for 503 server load.
        """
        if not gaps or not os.path.exists(video_path):
            return []

        detected_events: List[pysubs2.SSAEvent] = []
        glossary_entries = VisualSignDetector._normalize_glossary_entries(custom_glossary)
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

        if glossary_entries:
            gloss_lines = [
                f"- '{g['term_en']}' -> '{g['translation_pl']}'"
                for g in glossary_entries[:25]
            ]
            prompt += (
                "\n\nKANONICZNA TERMINOLOGIA SERII (zastosuj dokładne polskie odpowiedniki pojęć i tytułów):\n"
                + "\n".join(gloss_lines)
            )

        consecutive_errors = 0
        active_service_tier = resolve_service_tier()
        consecutive_flex_503 = 0

        for gap_start, gap_end in gaps:
            if consecutive_errors >= 2:
                logger.info("VisualSignDetector: Skipping remaining gaps due to Google 503 load and finalizing subtitles...")
                break

            # Filtr bliskości przed wywołaniem ekstraktora klatek i API Gemini (OBS-22)
            event_duration = min(4000, max(0, gap_end - gap_start - 500))
            event_start = gap_start + 250
            event_end = event_start + max(2000, event_duration)
            mid_ms = (gap_start + gap_end) // 2
            if existing_events and (
                VisualSignDetector.is_near_existing_sign(
                    event_start, event_end, existing_events, proximity_ms=sign_proximity_ms
                )
                or VisualSignDetector.is_near_existing_sign(
                    mid_ms, mid_ms, existing_events, proximity_ms=sign_proximity_ms
                )
            ):
                logger.info(
                    f"VisualSignDetector: Pominięto lukę {gap_start}-{gap_end}ms z powodu bliskości istniejącej planszy (<= {sign_proximity_ms}ms)."
                )
                continue

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
                    }
                    if is_gemini_4_or_hydrogen_model(model):
                        gen_cfg_kwargs["thinking_config"] = build_thinking_config(model, 0)
                    else:
                        gen_cfg_kwargs["temperature"] = 0.1
                        if any(k in model.lower() for k in ["3.7", "3.8", "flash", "pro"]) and "lite" not in model.lower():
                            gen_cfg_kwargs["thinking_config"] = types.ThinkingConfig(thinking_budget=0)

                    gen_cfg_kwargs = apply_service_tier_to_config(gen_cfg_kwargs, active_service_tier, model)

                    response = client.models.generate_content(
                        model=model,
                        contents=[prompt, pil_img],
                        config=types.GenerateContentConfig(**gen_cfg_kwargs)
                    )
                    consecutive_errors = 0
                    consecutive_flex_503 = 0

                    if response.text:
                        data = json.loads(response.text)
                        sign_info = DetectedSign.model_validate(data)
                        
                        if sign_info.is_title_or_banner and sign_info.translation_pl:
                            clean_pl = sign_info.translation_pl.strip().strip("[]").strip()
                            if glossary_entries and clean_pl:
                                try:
                                    from translator import enforce_locked_glossary_terms
                                    clean_pl = enforce_locked_glossary_terms(
                                        en_text=sign_info.original_text or clean_pl,
                                        candidate_pl=clean_pl,
                                        glossary_entries=glossary_entries,
                                        phase1_pl=None,
                                    )
                                except Exception:
                                    pass
                            clean_pl = clean_pl.upper()

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
                    err_low = str(e_model).lower()
                    is_transient = (
                        "503" in err_low
                        or "unavailable" in err_low
                        or "high demand" in err_low
                        or "504" in err_low
                        or "deadline" in err_low
                        or "timeout" in err_low
                        or "timed out" in err_low
                    )
                    if active_service_tier == "flex" and is_transient:
                        consecutive_flex_503 += 1
                        if consecutive_flex_503 >= 2:
                            active_service_tier = "standard"
                            consecutive_flex_503 = 0
                            consecutive_errors = 0
                            logger.warning(
                                f"[Flex Fallback SignDetector]: 2x 503/timeout w trybie flex -> przełączenie na service_tier='standard' (model {model})."
                            )
                        else:
                            logger.debug(f"VisualSignDetector (flex): przejściowy błąd 503/timeout ({consecutive_flex_503}/2): {e_model}")
                    else:
                        consecutive_flex_503 = 0
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
