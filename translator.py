# -*- coding: utf-8 -*-
"""
Main Subtitle Translation Engine Module with Gemini Multimodal Processing.
Features:
1. Full Typesetting (TS) & on-screen positioning preservation (\\an8, \\pos, \\c, Styles, Layers).
2. Automated AniList knowledge retrieval (synopsis, characters, genders) based on filename.
3. Original Japanese audio listening (Multimodal Speech Recognition & Japanese Vocabulary).
4. Character Registry / Cast Tracker - persistent character gender and relationship memory.
5. Lookahead Window - preview of upcoming lines for context and gender resolution.
6. ASS corrupted tag sanitization.
7. Deduplication of identical subtitle events.
8. 100% original timestamp timing preservation.
9. Auto-checkpointing and automatic session resumption.
"""

import os
import sys
import logging

logger = logging.getLogger("translator")

# Force full UTF-8 support (including Japanese Kanji/Kana characters)
if sys.platform == "win32":
    try:
        import ctypes
        ctypes.windll.kernel32.SetConsoleOutputCP(65001)
        ctypes.windll.kernel32.SetConsoleCP(65001)
    except Exception:
        logger.debug("Operacja ustawienia strony kodowej konsoli zakończona wyjątkiem", exc_info=True)
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        logger.debug("Operacja rekonfiguracji strumieni konsoli zakończona wyjątkiem", exc_info=True)

import re
import time
import json
import logging
import threading
import tempfile
import contextlib
import sqlite3
import unicodedata
import copy
import concurrent.futures
from typing import List, Optional, Dict, Any, Tuple, Union
from pathlib import Path
from PIL import Image
from pydantic import BaseModel, Field, ConfigDict
import pysubs2
from tqdm import tqdm

# Silence developer warnings from google_genai library
logging.getLogger("google_genai").setLevel(logging.ERROR)
logging.getLogger("google_genai.models").setLevel(logging.ERROR)
logger = logging.getLogger("translator")

from google import genai
from google.genai import types

from rules import get_translation_system_prompt, get_focused_rules_for_batch, SceneDiagnosis
from verifier import DialogueVerifier, RefinedLine
from extract import extract_frame_at_timestamp, extract_audio_slice
from metadata import get_anime_context, format_anime_context_for_prompt, normalize_actor_tag, normalize_anime_slug
from memory import TranslationMemory, format_translation_memory_for_prompt
from profiler import EpisodeProfiler, EpisodeProfile, format_episode_profile_for_prompt, format_lean_episode_brief
from whisper_engine import JapaneseWhisperEngine
from whisper_disambiguator import WhisperDisambiguator
from avt_linter import (
    AVTLinter, harmonize_text_2nd_person_plural, harmonize_verbal_gender_1st_and_2nd,
    harmonize_copula_and_predicate_adjective, harmonize_2nd_person_predicate_nouns,
    strip_false_ablative_instrumental, fix_masculine_vocative_tz,
    has_2nd_person_plural_verb,
    harmonize_virile_group_1st_person_plural, strip_false_feminine_instrumental,
    harmonize_plural_group_gender, fix_hybrid_ty_jestescie,
    restore_deictic_masculine_role_from_context, harmonize_powinien_paradigm,
    harmonize_2nd_person_singular_to_plural_pronouns
)
from romaji_helper import to_romaji
from series_memory import (
    SeriesBible, extract_clean_speaker_name, INHERENT_FEMALE_NOUNS, INHERENT_MALE_NOUNS,
    SECONDARY_LEXICAL_MALE_NOUNS,
    GENERIC_CATEGORY_TAGS, is_generic_actor_or_category, is_sign_entity, FEMALE_ROLE_KEYWORDS,
    MALE_ROLE_KEYWORDS, BOY_ROLE_KEYWORDS, EntityCategory, DeclensionParadigm,
    classify_entity_category, generate_polish_name_declension, is_plural_actor
)
from manga_canon import MangaCanonRegistry
from avt_formatter import (
    split_subtitle_syntactically,
    calculate_cps,
    calculate_condensation_directive,
    clamp_sub_second_cps,
    snap_subtitles_to_shot_cuts,
    format_diegetic_sound_wall,
    clean_text_for_len
)
from prosody_engine import AudioProsodyEngine
from speaker_diarizer import SpeakerVoiceClassifier
from typesetting_matcher import TypesettingColorMatcher, VisualTypesettingData
from user_feedback import UserFeedbackManager
from glossary_manager import GlossaryManager
from scene_discourse import DualVoiceTagPreserver, DeicticDiscourseEngine, DiarizationSanityChecker, build_discourse_topology, SceneDiscourseGraph
from profiler import EpisodeProfiler
from client_factory import format_friendly_api_error, patch_google_genai_schema_sanitizer
from pipeline_logger import EpisodeFlightRecorder

patch_google_genai_schema_sanitizer()

def format_dry_telemetry_tag(
    speaker_gender: Optional[str] = None,
    speaker_confidence: float = 1.0,
    target_gender: Optional[str] = None,
    target_confidence: float = 1.0,
    plural_group_gender: Optional[str] = None,
    plural_confidence: float = 1.0,
    you_group_gender: Optional[str] = None,
    you_group_confidence: float = 1.0,
    speaker_name: Optional[str] = None,
    target_name: Optional[str] = None,
    register: Optional[str] = None,
    **kwargs: Any
) -> str:
    """
    Buduje zwięzły opisowy mikro-tag dołączając wyłącznie segmenty (Mówca, Adresat, Grupa_1os_lm, Grupa_2os_lm, Rejestr),
    których pewność wynosi >= 0.80. Nigdy nie emituje wartości None ani AMBIGUOUS!
    """
    spk = speaker_gender or kwargs.get("speaker") or kwargs.get("spk")
    spk_conf = kwargs.get("spk_conf", kwargs.get("speaker_conf", speaker_confidence))
    spk_n = speaker_name or kwargs.get("spk_name") or kwargs.get("speaker_actor") or kwargs.get("speaker_name")

    tgt = target_gender or kwargs.get("target") or kwargs.get("addressee") or kwargs.get("addressee_gender")
    tgt_conf = kwargs.get("tgt_conf", kwargs.get("target_conf", target_confidence))
    tgt_n = target_name or kwargs.get("tgt_name") or kwargs.get("target_actor") or kwargs.get("target_name")

    grp = plural_group_gender or kwargs.get("plural_group") or kwargs.get("group_gender") or kwargs.get("grupa_1os_lm")
    grp_conf = kwargs.get("grp_conf", kwargs.get("plural_conf", kwargs.get("group_conf", plural_confidence)))

    you_grp = you_group_gender or kwargs.get("you_group") or kwargs.get("grupa_2os_lm")
    you_conf = kwargs.get("you_conf", kwargs.get("you_group_conf", kwargs.get("you_confidence", you_group_confidence)))

    reg = register or kwargs.get("register") or kwargs.get("social_register") or kwargs.get("pragmatic_register") or kwargs.get("rejestr")

    # Standard 9.6 (Operacja 2C.1): Oczyszczanie nawiasów F0 z nazw mówcy i adresata
    if spk_n:
        spk_n = re.sub(r"\s*\([^)]*\)", "", str(spk_n)).strip()
        spk_n = re.sub(r"\s{2,}", " ", spk_n)
    if tgt_n:
        tgt_n = re.sub(r"\s*\([^)]*\)", "", str(tgt_n)).strip()
        tgt_n = re.sub(r"\s{2,}", " ", tgt_n)

    # Izolacja napisów ekranowych (is_sign: true)
    is_sign = kwargs.get("is_sign", False) or (spk_n and spk_n.lower() in ("sign", "signs", "txt", "title", "caption", "szyld", "napis", "board", "screen"))
    if is_sign:
        return "[Mówca: sign (NEUTRAL)]"

    # Izolacja monologu wewnętrznego i tożsamości mówcy z adresatem
    is_internal_monologue = kwargs.get("is_internal_monologue", False) or kwargs.get("is_thought", False)
    if is_internal_monologue or (tgt_n and spk_n and tgt_n.lower() == spk_n.lower()):
        tgt = None
        tgt_n = None

    segments = []

    def _is_valid_telemetry_val(val: Any) -> bool:
        if val is None:
            return False
        s = str(val).strip()
        if not s or s.lower() in ("none", "ambiguous", "unknown", "nieznana", "nieznany"):
            return False
        return True

    try:
        spk_c = float(spk_conf)
    except Exception:
        spk_c = 1.0 if _is_valid_telemetry_val(spk) else 0.0

    try:
        tgt_c = float(tgt_conf)
    except Exception:
        tgt_c = 1.0 if _is_valid_telemetry_val(tgt) else 0.0

    try:
        grp_c = float(grp_conf)
    except Exception:
        grp_c = 1.0 if _is_valid_telemetry_val(grp) else 0.0

    try:
        you_c = float(you_conf)
    except Exception:
        you_c = 1.0 if _is_valid_telemetry_val(you_grp) else 0.0

    if _is_valid_telemetry_val(spk) and spk_c >= 0.80:
        if _is_valid_telemetry_val(spk_n):
            segments.append(f"Mówca: {spk_n} ({spk})")
        else:
            segments.append(f"Mówca: {spk}")

    if _is_valid_telemetry_val(tgt) and tgt_c >= 0.80:
        if _is_valid_telemetry_val(tgt_n):
            segments.append(f"Adresat: {tgt_n} ({tgt})")
        else:
            segments.append(f"Adresat: {tgt}")

    if _is_valid_telemetry_val(grp) and grp_c >= 0.80:
        segments.append(f"Grupa_1os_lm: {grp}")

    if _is_valid_telemetry_val(you_grp) and you_c >= 0.80:
        segments.append(f"Grupa_2os_lm: {you_grp}")

    if _is_valid_telemetry_val(reg):
        segments.append(f"Rejestr: {reg}")

    poly = kwargs.get("polylogue") or kwargs.get("scena")
    if _is_valid_telemetry_val(poly):
        segments.append(f"Scena: {poly}")

    if not segments:
        return ""

    return f"[{' | '.join(segments)}]"

def synchronize_ass_event_metadata_and_styles(
    event: pysubs2.SSAEvent,
    speaker_name: Optional[str] = None,
    is_offscreen: bool = False,
    style_italic: Optional[int] = None
) -> pysubs2.SSAEvent:
    """
    Synchronizuje pole event.name z wyznaczonym, kanonicznym speaker_name oraz
    ustawia styl offscreen / formatowanie kursywy dla kwestii wypowiadanych spoza kadru.
    Standard 9.3: Zachowuje kursywę dla stylów o czcionce prostej (style_italic == 0).
    """
    if speaker_name:
        clean_spk, _ = normalize_actor_tag(str(speaker_name))
        if clean_spk and not is_generic_actor_or_category(clean_spk):
            event.name = clean_spk
    elif getattr(event, "name", None):
        clean_ev_n, _ = normalize_actor_tag(str(event.name))
        if clean_ev_n and not is_generic_actor_or_category(clean_ev_n):
            event.name = clean_ev_n

    if is_offscreen:
        curr_style = str(getattr(event, "style", "") or "")
        if "offscreen" not in curr_style.lower() and "narrat" not in curr_style.lower():
            if curr_style:
                event.style = f"{curr_style} - Offscreen"
            else:
                event.style = "Offscreen"
        if not re.search(r"\{\\i1\}", event.text):
            event.text = f"{{\\i1}}{event.text}{{\\i0}}"
    elif style_italic in (1, -1):
        event.text = re.sub(r"\{\\i[01]\}", "", event.text).strip()
    return event

def segment_hybrid_events(events: List[pysubs2.SSAEvent], style_report: Optional[Any] = None) -> List[pysubs2.SSAEvent]:
    """
    Standard 9.0 (Sekcja 2 pkt 3, R3.1):
    Klasyfikacja semiotyczna i segmentacja linii hybrydowych.
    Linie łączące napis ekranowy (warstwa bez małych liter lub szyld) oraz dialog
    rozbija na osobne zdarzenia Dialogue: w .ass z osobną klasyfikacją każdej warstwy.
    """
    segmented: List[pysubs2.SSAEvent] = []
    for ev in events:
        text = getattr(ev, "text", "") or ""
        if r"\N" in text or "\n" in text:
            parts = [p.strip() for p in re.split(r"\\[Nnh]|\n", text) if p.strip()]
            if len(parts) >= 2:
                is_part_sign = []
                for p in parts:
                    clean_p = re.sub(r"\{[^}]*\}", "", p).strip()
                    has_letters = bool(re.search(r"[a-zA-ZąćęłńóśźżĄĆĘŁŃÓŚŹŻ]", clean_p))
                    has_lowercase = bool(re.search(r"[a-ząćęłńóśźż]", clean_p))
                    is_sign_layer = (has_letters and not has_lowercase) or (clean_p.startswith("[") and clean_p.endswith("]"))
                    is_part_sign.append(is_sign_layer)
                
                if any(is_part_sign) and not all(is_part_sign):
                    for p, is_s in zip(parts, is_part_sign):
                        sub_ev = copy.deepcopy(ev)
                        sub_ev.text = p
                        if is_s:
                            setattr(sub_ev, "is_sign", True)
                        else:
                            setattr(sub_ev, "is_sign", False)
                        segmented.append(sub_ev)
                    continue

        segmented.append(ev)
    return segmented

def split_oversized_ass_events(events: List[pysubs2.SSAEvent]) -> List[pysubs2.SSAEvent]:
    """
    Standard 9.0 (Sekcja 2 pkt 5, pkt 7, R3.9):
    1. Konwertuje semantyczne znaki \\n 1:1 do \\N w .ass.
    2. Czyści pole Name przed eksportem (usuwa techniczne separatory wielogłosu /, |, &, +).
    3. Treść przekraczającą limity .ass (> 2 wiersze) rozbija na kolejne zdarzenia Dialogue: o kolejnych przedziałach czasowych.
    """
    processed: List[pysubs2.SSAEvent] = []
    for ev in events:
        # Standard 9.0 Positive Domain: Ochrona napisów ekranowych przed rozbijaniem (Standard 9.5, 2C.2, R3.4)
        ev_name_clean = str(getattr(ev, "name", "") or "").strip().lower()
        ev_text_raw = getattr(ev, "text", "") or ""
        is_protected_sign = (
            getattr(ev, "is_sign", False)
            or ev_name_clean in ("sign", "signs", "txt", "title", "board", "screen")
            or bool(re.search(r"\\(?:pos|move|fad|an[4-9])\(", ev_text_raw))
            or any(tag in ev_text_raw.lower() for tag in (r"\pos(", r"\move(", r"\an5", r"\an7", r"\an8", r"\an9"))
        )
        if is_protected_sign:
            text_with_N = ev_text_raw.replace("\r\n", r"\N").replace("\n", r"\N")
            ev.text = text_with_N
            processed.append(ev)
            continue

        # 1. Clean Name field (T7 / R3.9)
        if getattr(ev, "name", None):
            raw_n = ev.name.strip()
            from metadata import normalize_actor_tag
            clean_n, _ = normalize_actor_tag(raw_n)
            clean_n = re.sub(r"[/|&+]+", " ", clean_n).strip()
            clean_n = re.sub(r"\s+", " ", clean_n).strip()
            ev.name = clean_n

        # 2. Convert \n 1:1 to \N (T5 / Sekcja 2 pkt 5)
        raw_text = getattr(ev, "text", "") or ""
        text_with_N = raw_text.replace("\r\n", r"\N").replace("\n", r"\N")
        ev.text = text_with_N

        # 3. Check for multi-line overflow (> 2 lines)
        parts = [p.strip() for p in text_with_N.split(r"\N") if p.strip()]
        total_dur = max(0, ev.end - ev.start)

        if len(parts) > 2 and total_dur >= 1000:
            chunk_pairs = [parts[j:j+2] for j in range(0, len(parts), 2)]
            num_chunks = len(chunk_pairs)
            chunk_ms = total_dur // num_chunks
            for k, pair in enumerate(chunk_pairs):
                c_start = ev.start + k * chunk_ms
                c_end = (ev.start + (k + 1) * chunk_ms) if k < num_chunks - 1 else ev.end
                c_ev = copy.deepcopy(ev)
                c_ev.start = c_start
                c_ev.end = c_end
                c_ev.text = r"\N".join(pair)
                processed.append(c_ev)
        else:
            processed.append(ev)

    return processed

def extract_typesetting_tags(raw_text: str) -> Tuple[str, str]:
    """
    Extracts valid ASS positioning and styling tags (e.g., {\\an8}, {\\pos(x,y)}, {\\fad(..)})
    from the start of a subtitle line to preserve Typesetting and screen positioning.
    Returns: (tag_prefix, clean_dialogue_text)
    """
    if not raw_text:
        return "", ""
    
    # Detect leading ASS tag blocks
    match = re.match(r"^((?:\{[^}]+\})+)", raw_text)
    if match:
        tag_prefix = match.group(1)
        # Ensure it is a valid tag block with ASS command characters
        if "\\" in tag_prefix and not tag_prefix.endswith("\\"):
            remaining = raw_text[len(tag_prefix):]
            clean_remaining = sanitize_sub_text(remaining)
            return tag_prefix, clean_remaining

    return "", sanitize_sub_text(raw_text)

def sanitize_ts_prefix_for_translation(ts_prefix: str) -> str:
    """
    Sanitizes ASS typesetting tag prefixes before reattaching to translated Polish text:
    - Strips restrictive \\clip(...) / \\iclip(...) bounding boxes that crop/hide longer Polish translations.
    - Cleans empty or malformed tag blocks e.g. "{}".
    """
    if not ts_prefix:
        return ""
    # Strip restrictive clip/iclip bounding boxes designed for shorter English text
    cleaned = re.sub(r"\\i?clip\([^)]*\)", "", ts_prefix)
    # Clean empty tag braces {}
    cleaned = re.sub(r"\{\s*\}", "", cleaned)
    return cleaned

def detect_event_visual_type(event: pysubs2.SSAEvent, ts_prefix: str = "", style_report: Optional[Any] = None) -> Dict[str, Any]:
    """
    Analyzes ASS tags, position, rotation, color, text content, and style to distinguish
    on-screen text (manga titles, signs, posters, boards, episode titles) from standard spoken dialogue (including top dialogue).
    Uses StyleMatrixEngine when available for geometric certainty.
    """
    if style_report is not None:
        from style_matrix import EventRole
        role, detail = style_report.classify_single_event(event)
        is_sign = role in (EventRole.SIGN_LOCATIONAL, EventRole.SIGN_OVERLAY)
        is_top = role == EventRole.DIALOGUE_TOP
        if is_sign:
            type_label = "NAPIS EKRANOWY / TYTUŁ (Sign/Typesetting)"
        elif is_top:
            type_label = "MÓWIONY DIALOG W TLE / NA GÓRZE EKRANU (Top Dialogue)"
        else:
            type_label = "MÓWIONY DIALOG POSTACI"
        return {
            "is_sign": is_sign,
            "is_top": is_top,
            "type_label": type_label,
            "visual_details": detail
        }

    is_sign = False
    is_top = False
    details = []

    try:
        from sign_detector import VisualSignDetector
        sign_det = VisualSignDetector.detect_signs(event)
        if isinstance(sign_det, dict) and sign_det.get("is_sign"):
            is_sign = True
            details.append("VisualSignDetector.detect_signs")
    except Exception:
        logger.debug("Wizualna detekcja napisów zakończona wyjątkiem", exc_info=True)

    style_lower = (event.style or "").lower()
    name_lower = (event.name or "").lower()
    ts_lower = (ts_prefix or "").lower()
    text_raw = (event.plaintext or event.text or "").strip()

    # Structural uppercase / ALL-CAPS sign (Standard 9.0)
    clean_t = re.sub(r"\{[^}]*\}", "", text_raw).strip()
    has_letters = bool(re.search(r"[a-zA-ZąćęłńóśźżĄĆĘŁŃÓŚŹŻ]", clean_t))
    has_lowercase = bool(re.search(r"[a-ząćęłńóśźż]", clean_t))
    if has_letters and not has_lowercase:
        is_sign = True
        details.append("Tekst bez małych liter (ALL CAPS)")

    style_is_sub = bool(re.search(r"\bsubtitles?\b", style_lower))
    if not style_is_sub and (
        re.search(r"\b(sign|signs|caption|captions|title|titles|poster|board|typesetting|card|napis|napisy|tytuł|tytuły|szyld|szyldy)\b", style_lower)
        or style_lower.startswith("caption")
        or "on-screen" in style_lower
        or style_lower == "ts"
    ):
        is_sign = True
        details.append(f"styl='{event.style}'")

    if not style_is_sub and re.search(r"\b(sign|signs|title|titles|poster|board|typesetting|napis)\b", name_lower):
        is_sign = True
        details.append(f"aktor='{event.name}'")

    if name_lower.strip() in ("sign", "signs", "txt", "title", "board", "screen"):
        is_sign = True
        details.append(f"aktor='{event.name}' (sign)")

    if re.match(r"^(episode|odcinek|chapter|rozdział|act|akt|part|część)\s+(\d+|[ivxlcdm]+)", text_raw, re.IGNORECASE):
        is_sign = True
        details.append("plansza tytułowa odcinka/rozdziału")

    if r"\frz" in ts_lower or r"\org" in ts_lower or r"\clip" in ts_lower or r"\p1" in ts_lower:
        is_sign = True
        details.append("obrócony/wklejony graficznie w perspektywę kadrów")

    if (r"\pos" in ts_lower or r"\move" in ts_lower or r"\pos" in text_raw.lower() or r"\move" in text_raw.lower()) and not is_sign:
        # Standard 9.5 (2C.2): \pos lub \move bez osobowego aktora = bezwarunkowo is_sign = True
        if not name_lower or name_lower.strip() in ("sign", "signs", "txt", "title", "board", "screen") or is_generic_actor_or_category(name_lower):
            is_sign = True
            details.append("pozycjonowany napis ekranowy (\\pos/\\move)")
        elif r"\c&h" in ts_lower or r"\1c&h" in ts_lower or r"\3c&h" in ts_lower:
            is_sign = True
            details.append("pozycjonowany napis graficzny (\\pos)")
        else:
            is_top = True
            details.append("dialog pozycjonowany (\\pos)")

    if any(an in ts_lower for an in [r"\an7", r"\an8", r"\an9", r"\an4", r"\an5", r"\an6"]) or "top" in style_lower:
        if not is_sign:
            is_top = True
            details.append("dialog górny / postać w tle (\\an8/Top)")

    if is_sign:
        type_label = "NAPIS EKRANOWY / TYTUŁ (Sign/Typesetting)"
    elif is_top:
        type_label = "MÓWIONY DIALOG W TLE / NA GÓRZE EKRANU (Top Dialogue)"
    else:
        type_label = "MÓWIONY DIALOG POSTACI"

    desc = ", ".join(details) if details else "standardowy dolny dialog"
    return {
        "is_sign": is_sign,
        "is_top": is_top,
        "type_label": type_label,
        "visual_details": desc
    }

def is_isolated_paralinguistic_clutter(orig_en: str, translated_pl: str, is_sign: bool = False) -> bool:
    """
    Identifies isolated mimic/vocal grunts, sighs, and paralinguistic clutter
    that do not carry lexical meaning and pollute the screen against professional AVT standards.
    """
    if is_sign:
        return False
        
    pl_clean = re.sub(r"[\s\"'«»„”!?.…]+", "", (translated_pl or "")).lower()
    en_clean = re.sub(r"[\s\"'«»„”!?.…]+", "", (orig_en or "")).lower()
    
    clutter_words = {
        "och", "uch", "uh", "ah", "ugh", "gah", "hmph", "hmpf", 
        "tsk", "fu", "pff", "uff", "uf", "ech", "guh", "ku", "eh", "oh"
    }
    
    if pl_clean in clutter_words:
        # If English was also just a short grunt or paralinguistic sound
        if not en_clean or en_clean in clutter_words or len(en_clean) <= 4:
            return True
            
    return False

def detect_audio_discrepancy(jp_text: str, pl_text: str, en_text: str, prosody: str = "") -> Optional[str]:
    """
    Automated discrepancy detector comparing Japanese voice recognition (Whisper)
    and audio acoustic prosody (tone, dBFS, shouting vs sarcasm) against Phase 1 draft translation.
    """
    if not pl_text:
        return None

    jp_text = jp_text or ""
    en_text = en_text or ""
    jp_lower = jp_text.lower()
    pl_lower = pl_text.lower()
    prosody_lower = prosody.lower() if prosody else ""

    # Extract clean Romaji text (from [Romaji] brackets) and clean Japanese
    clean_jp = re.sub(r"\[.*?\]", "", jp_text).strip()
    romaji_match = re.findall(r"\[(.*?)\]", jp_text)
    rom_lower = romaji_match[0].strip().lower() if romaji_match else jp_lower

    # 1. Kanojo-tachi vs masculine forms
    if "彼女たち" in jp_text or "kanojo-tachi" in jp_lower or "kanojotachi" in jp_lower:
        if any(w in pl_lower for w in ["oni ", "ich ", "mężczyźni", "chłopcy", "byli", "poszli", "zrobili"]):
            return "Sygnał audio JP: 'Kanojo-tachi' (grupa wyłącznie żeńska 3. os. lm. 'one/ich')"

    # 2. Kikanaide vs 'Wolę nie wiedzieć'
    if "聞かないで" in jp_text or "kikanaide" in jp_lower:
        if any(w in pl_lower for w in ["wolę nie wiedzieć", "nie chcę wiedzieć", "nie chcę słyszeć"]):
            return "Sygnał audio JP: 'Kikanaide' (prośba mówcy o zaniechanie dociekań: 'nie pytaj')"

    # 3. Kure / Kase vs 'Proszę'
    if ("くれ" in jp_text or "kure" in jp_lower or "kase" in jp_lower) and "kudasai" not in jp_lower:
        if pl_lower.startswith("proszę") or "czy możesz" in pl_lower or "czy mógłbyś" in pl_lower:
            return "Sygnał audio JP: szorstki rejestr dyrektywny (-kure / -kase / -shiro)"

    # 4. Yobisute, -kun, -chan, and peer -san vs artificial 'Pan / Pani'
    honorific_noble_keys = ["様", "先生", "殿", "隊長", "部長", "課長", "社長", "師匠", "sama", "sensei", "dono", "taichou", "buchou", "kachou", "shachou", "shishou"]
    if any(p in pl_lower for p in ["panie ", "pani ", "pan ", "pana ", "panu ", "panią "]) and not any(s in jp_text for s in honorific_noble_keys):
        if not any(s in jp_lower for s in honorific_noble_keys):
            if any(s in jp_text for s in ["君", "くん", "ちゃん"]) or any(s in rom_lower for s in ["kun", "chan", "-kun", "-chan"]):
                return "Sygnał audio JP: sufiks rówieśniczy (-kun / -chan, relacja symetryczna)"
            return "Sygnał audio JP: brak honoryfikatywu wyższego szacunku (-sama / -sensei / -dono)"

    # 5. Haragei & Trailing Particles (-kedo, -kara, -tara) vs completing the sentence
    trailing_keys = ["kedo", "kara", "tara", "monode", "shi"]
    if any(clean_jp.endswith(p) for p in ["けど", "から", "たら", "し"]) or any(rom_lower.endswith(k) for k in trailing_keys):
        if len(pl_text.split()) > 7 and not pl_text.endswith("..."):
            return "Sygnał audio JP: haragei (wypowiedź eliptyczna zawieszona na partykule 'kedo/kara')"

    # 6. Aizuchi (Un, Sou, Fumu) vs wordy subtitles
    aizuchi_keys = ["un", "sou", "fumu", "ee", "sou da", "sou da ne", "sou desu ne"]
    if clean_jp in ["うん", "そう", "ふむ", "ええ", "そうだ", " glass", "そうですね"] or rom_lower in aizuchi_keys:
        if len(pl_text.split()) > 2:
            return "Sygnał audio JP: aizuchi (minimalny wokalny sygnał podtrzymania kontaktu)"

    # 7. Oyaji vs stiff 'mój ojciec'
    if ("親父" in clean_jp or "おやじ" in clean_jp or "oyaji" in rom_lower) and "mój ojciec" in pl_lower:
        return "Sygnał audio JP: 'Oyaji' (nieformalne określenie ojca w rejestrze męskim)"

    # 8. Giri and Sumimasen in gratitude/saving context
    if ("済みません" in clean_jp or "すみません" in clean_jp or "sumimasen" in rom_lower) and any(w in en_text.lower() for w in ["saved", "water", "food", "help", "thank"]):
        if pl_lower.startswith("przepraszam"):
            return "Sygnał audio JP: 'Sumimasen' (dług wdzięczności giri, podziękowanie za trud)"

    # 9. Ii desu / Kekkou desu in refusal vs health state
    if ("いいです" in clean_jp or "ii desu" in rom_lower or "kekkou" in rom_lower or "結構" in clean_jp):
        if any(w in pl_lower for w in ["nic mi nie jest", "nic mi... nie jest", "wszystko w porządku", "dobrze się czuję"]):
            return "Sygnał audio JP: 'ii desu / kekkou' (uprzejma rezygnacja lub odmowa przyjęcia oferty)"

    # 10. Sasuga (reputation / praise / typical excellence) vs literal whole/all calque
    if "さすが" in clean_jp or "流石" in clean_jp or "sasuga" in rom_lower:
        if pl_lower.startswith("całe ") or pl_lower.startswith("cały ") or pl_lower.startswith("to cały ") or "wszyscy" in pl_lower:
            return "Sygnał audio JP: 'Sasuga' (uznanie dla kunsztu, reputacji i klasy rozmówcy)"

    # 11. Warukatta / Warikatta / Warui (singular informal apology) vs plural 'Wybaczcie'
    warui_keys = ["warukatta", "warikatta", "warui", "warui na", "warukatta na", "warukattana", "warikattana"]
    if any(k in rom_lower for k in warui_keys) or any(k in clean_jp for k in ["悪かった", "悪い"]):
        if any(w in pl_lower for w in ["wybaczcie", "przeproście", "przepraszamy"]):
            return "Sygnał audio JP: 'Warukatta / Warui' (męskie, bezpośrednie przyznanie się do błędu)"

    # 12. Wakaru / Wakaruu (empathic agreement / shared feeling) vs adjective exclamations (Genialne/Wspaniale)
    wakaru_keys = ["wakaru", "wakaruu", "wakaru-", "wakaru yo", "wakaru wa", "wakaru na", "wakaruze", "wakaruzo"]
    if any(clean_jp.startswith(k) or clean_jp == k for k in ["分かる", "わかる", "分かるー", "わかるー", "分かる～", "わかる～", "分かるよ", "わかるよ"]) or any(k in rom_lower for k in wakaru_keys):
        if any(w in pl_lower for w in ["genialne", "wspaniale", "doskonale", "świetnie", "bystry", "mądry"]):
            return "Sygnał audio JP: 'Wakaru' (empatyczne współodczuwanie i pełne zrozumienie stanu rozmówcy)"

    # 13. Sore na / Sore da (potwierdzenie młodzieżowe)
    sorena_keys = ["sore na", "sore!", "sore da", "sore da yo", "sore da na"]
    if any(clean_jp.startswith(k) or clean_jp == k for k in ["それな", "それ！", "それだ", "それだよ"]) or any(k in rom_lower for k in sorena_keys):
        if any(w in pl_lower for w in ["ta rzecz", "to to", "właśnie to coś", "tamtą rzecz"]):
            return "Sygnał audio JP: Sore na (młodzieżowa aprobata wypowiedzi przedmówcy)"

    # 14. Tashika ni / Tashika ni ne (przyznanie racji)
    tashika_keys = ["tashika ni", "tashikani", "tashika ni ne", "tashikani ne"]
    if any(clean_jp.startswith(k) or clean_jp == k for k in ["確かに", "たしかに", "確かにね", "たしかにね"]) or any(k in rom_lower for k in tashika_keys):
        if pl_lower.startswith("z pewnością") or pl_lower.startswith("pewnie tak"):
            return "Sygnał audio JP: Tashika ni (racjonalne przyznanie racji argumentacji rozmówcy)"

    # 15. Naruhodo / Naruhodo ne (zrozumienie toku myślenia)
    naruhodo_keys = ["naruhodo", "naruhodone", "naruhodo na", "naruhodo ne"]
    if any(clean_jp.startswith(k) or clean_jp == k for k in ["なるほど", "なるほどね", "なるほどな"]) or any(k in rom_lower for k in naruhodo_keys):
        if pl_lower == "rzeczywiście." or pl_lower == "rozumiem.":
            return "Sygnał audio JP: Naruhodo (zrozumienie toku rozumowania)"

    # 16. Sou iu koto ka / Sou iu koto ne (dedukcja prawdy)
    souiukoto_keys = ["sou iu koto ka", "sou iu koto ne", "souiu koto ka", "souiukoto ka"]
    if any(k in clean_jp for k in ["そういうことか", "そういう事か", "そういうことね"]) or any(k in rom_lower for k in souiukoto_keys):
        if "więc tak to jest" in pl_lower or "taka to rzecz" in pl_lower:
            return "Sygnał audio JP: sou iu koto ka (samodzielne domyślenie się sedna sprawy)"

    # 17. Uso / Uso desho / Masaka (szok i niedowierzanie)
    uso_keys = ["uso", "uso-", "uso!", "uso desho", "uso daro", "usodesho", "masaka"]
    if clean_jp in ["嘘", "うそ", "うそー", "嘘でしょ", "うそでしょ", "まさか"] or rom_lower in uso_keys:
        if any(w in pl_lower for w in ["kłamstwo", "kłamiesz", "to kłamstwo", "kłamco"]):
            return "Sygnał audio JP: Uso (emocjonalny szok i nagłe niedowierzanie)"

    # 18. Maji de / Maji ka (młodzieżowe zwątpienie)
    maji_keys = ["maji de", "majide", "maji ka", "majika", "maji kayo", "majikayo"]
    if any(k in clean_jp for k in ["マジで", "まじで", "マジか", "まじか", "マジかよ"]) or any(k in rom_lower for k in maji_keys):
        if any(w in pl_lower for w in ["czy to prawda", "prawdziwie", "prawdziwe to"]):
            return "Sygnał audio JP: Maji de (młodzieżowe zwątpienie i pytanie o powagę)"

    # 19. Yappari / Yahari / Yappa (potwierdzenie intuicji)
    yappari_keys = ["yappari", "yahari", "yappa", "yappari na", "yapparina"]
    if any(k in clean_jp for k in ["やっぱり", "やはり", "やっぱ", "やっぱな"]) or any(k in rom_lower for k in yappari_keys):
        if any(w in pl_lower for w in ["po wszystkim", "zgodnie z oczekiwaniami", "jak oczekiwano"]):
            return "Sygnał audio JP: Yappari (potwierdzenie wcześniejszych podejrzeń)"

    # 20. Desho / Daro (retoryczne potwierdzenie)
    desho_keys = ["desho", "deshou", "desho?", "daro", "darou", "daro?"]
    if clean_jp in ["でしょ", "でしょう", "でしょ？", "だろ", "だろう", "だろ？"] or rom_lower in desho_keys:
        if "czyż nie" in pl_lower:
            return "Sygnał audio JP: Desho / daro (retoryczne potwierdzenie własnej racji)"

    # 21. Nani kore (zdumienie sytuacją)
    nanikore_keys = ["nani kore", "nanikore", "nanda kore", "nandakore"]
    if any(k in clean_jp for k in ["何これ", "なにこれ", "なんだこれ", "何だこれ"]) or any(k in rom_lower for k in nanikore_keys):
        if "co to za rzecz" in pl_lower or "czym jest ta rzecz" in pl_lower:
            return "Sygnał audio JP: Nani kore (zdumienie kuriozalną sytuacją lub obiektem)"


    # 22. Hybrydy honoryfikatywne (Pani Sensei / Panie Senpai / Panie Taichou)
    hybrid_patterns = ["pani sensei", "panie sensei", "pan sensei", "pani senpai", "panie senpai", "pan senpai", "panie taichou", "panie shishou", "panie buchou"]
    if any(h in pl_lower for h in hybrid_patterns):
        return "Sygnał audio JP: zwrot honoryfikatywny do nauczyciela/starszego rangą bez tytułomanii"

    # 23. Kakegoe (Yotto, Yoisho, Dokkoisho, Yoi kora) vs polite 'Proszę'
    kakegoe_keys = ["yotto", "yoisho", "dokkoisho", "yoi kora", "yoikora", "eisa"]
    if any(k in rom_lower for k in kakegoe_keys) or any(k in clean_jp for k in ["よっと", "よいしょ", "どっこいしょ", "よいこら", "えいさ"]):
        if any(w in pl_lower for w in ["proszę", "oto jest", "oto masz", "oto proszę"]):
            return "Sygnał audio JP: kakegoe (odgłos wysiłku fizycznego przy podnoszeniu/ruchu)"

    # 24. Chigaimasu / Chigau (Deictic negation vs 'Nie o niego' / 'Różni się')
    chigau_keys = ["chigaimasu", "chigau", "chigau yo", "chigau wa", "chigee", "chigee yo", "chiga-"]
    if any(k in clean_jp for k in ["違います", "ちがいます", "違う", "ちがう", "ちげえ", "ちげえよ"]) or any(k in rom_lower for k in chigau_keys):
        if any(w in pl_lower for w in ["nie o niego", "nie o nią", "nie o to", "różni się", "to inne"]):
            if "him" in en_text.lower() or "he" in en_text.lower():
                return "Sygnał audio JP: 'Chigau' (stanowcze zaprzeczenie tożsamości osoby: 'to nie on')"
            elif "her" in en_text.lower() or "she" in en_text.lower():
                return "Sygnał audio JP: 'Chigau' (stanowcze zaprzeczenie tożsamości osoby: 'to nie ona')"
            return "Sygnał audio JP: 'Chigau' (stanowcze zaprzeczenie tożsamości osoby lub stanowi rzeczy)"

    # 25. Douzo / Osaki ni douzo ('After you' / 'Be my guest' vs 'Po tobie' / 'Bądź moim gościem')
    douzo_keys = ["douzo", "osaki ni", "osakini", "dozo"]
    if any(k in clean_jp for k in ["どうぞ", "お先に", "お先にどうぞ"]) or any(k in rom_lower for k in douzo_keys):
        if "po tobie" in pl_lower or "bądź moim gościem" in pl_lower:
            return "Sygnał audio JP: 'Douzo' (uprzejme ustąpienie pierwszeństwa lub zachęta do działania)"

    # 26. Hontou da yo na / Wakaru ('Tell me about it' vs 'Powiedz mi o tym')
    if any(k in rom_lower for k in ["tell me", "hontou da", "wakaru", "hontou ni"]) or any(k in clean_jp for k in ["本当だな", "ほんとうだな", "わかる"]):
        if "powiedz mi o tym" in pl_lower:
            return "Sygnał audio JP: empatyczne potwierdzenie wspólnego doświadczenia ('nawet mi nie mów')"

    # 27. Omae ga iu na (wytknięcie hipokryzji)
    if any(k in clean_jp for k in ["お前が言うな", "あんたが言うな", "お前もな", "omae ga iu na"]) or "omae ga iu" in rom_lower:
        if "spójrz kto mówi" in pl_lower or "spójrz, kto mówi" in pl_lower or "patrz kto mówi" in pl_lower:
            return "Sygnał audio JP: Omae ga iu na (wytknięcie hipokryzji rozmówcy)"

    # 28. Makasete / Ryoukai (gotowość zadania)
    if any(k in clean_jp for k in ["任せて", "まかせて", "了解", "りょうかい"]) or any(k in rom_lower for k in ["makasete", "ryoukai", "ryokai"]):
        if pl_lower.strip() in ["na tym!", "na tym.", "na tym"]:
            return "Sygnał audio JP: Makasete / ryoukai (pewność podjęcia zadania: biorę to na siebie)"

    # 29. Mochiron / Atarimae (oczywistość faktu)
    if any(k in clean_jp for k in ["もちろん", "当たり前", "あたりまえ", "勿論"]) or any(k in rom_lower for k in ["mochiron", "atarimae"]):
        if any(w in pl_lower for w in ["zakładasz się", "zakład!", "zakładaj się"]):
            return "Sygnał audio JP: mochiron / atarimae (niepodważalna oczywistość faktu)"

    # 30. Yokatta na (radość z sukcesu)
    if any(k in clean_jp for k in ["よかったな", "よかったね", "良かったな", "良かったね"]) or any(k in rom_lower for k in ["yokatta na", "yokatta ne", "yokattana"]):
        if "dobre dla ciebie" in pl_lower:
            return "Sygnał audio JP: yokatta na (szczera radość z czyjegoś sukcesu)"

    # 31. Daijoubu / Ii desu (odmowa pomocy)
    if any(k in clean_jp for k in ["大丈夫", "だいじょうぶ", "いいです", "結構です"]) or any(k in rom_lower for k in ["daijoubu", "ii desu", "kekkou desu"]):
        if "jestem dobry" in pl_lower:
            return "Sygnał audio JP: daijōbu (powściągliwa odmowa pomocy: nie trzeba)"


    # 32. Betsu ni ('Not really' vs 'Nieszczególnie' / 'Oddzielnie')
    if any(k in clean_jp for k in ["別に", "べつに"]) or "betsu ni" in rom_lower or "betsuni" in rom_lower:
        if any(w in pl_lower for w in ["nieszczególnie", "oddzielnie", "specjalnie nie"]):
            return "Sygnał audio JP: 'Betsu ni...' (emocjonalny chłód, dystansowanie się lub zbycie tematu)"

    # 33. Ii kara / Mou ii (impatience / brush-off vs literal 'Bo dobrze' / 'To już jest dobre')
    if any(k in clean_jp for k in ["いいから", "もういい"]) or any(k in rom_lower for k in ["ii kara", "iikara", "mou ii", "mouii"]):
        if "bo dobrze" in pl_lower or "to już jest dobre" in pl_lower or "ponieważ dobrze" in pl_lower:
            return "Sygnał audio JP: 'Mou ii / Ii kara' (zniecierpliwienie, uraza lub ucięcie dyskusji)"

    # 34. Chikushou / Kuso / Yabai / Shimatta (Radar Audio: silny wykrzyknik kryzysowy)
    if any(k in clean_jp for k in ["ちくしょう", "畜生", "くそ", "糞", "やばい", "ヤバい", "しまった"]) or any(k in rom_lower for k in ["chikushou", "chikusho", "kuso", "yabai", "shimatta"]):
        if any(w in pl_lower for w in ["ojej", "o nie", "ups", "rany", "kurczę"]):
            return "Sygnał audio JP: silny wykrzyknik wzburzenia kryzysowego (Chikushō / Kuso / Yabai)"

    # 35. Matte / Chotto matte (rozkaz zatrzymania)
    if any(k in clean_jp for k in ["待って", "まって", "ちょっと待って"]) or any(k in rom_lower for k in ["matte", "chotto matte"]):
        if "poczekaj minutę" in pl_lower or "chwilę czasu" in pl_lower:
            return "Sygnał audio JP: 'Matte' (gwałtowne żądanie wstrzymania ruchu rozmówcy)"

    # 36. Yamero / Yamenai ka (żądanie zaprzestania przemocy/działania)
    if any(k in clean_jp for k in ["やめろ", "辞めろ", "やめないか", "止めて", "やめて"]) or any(k in rom_lower for k in ["yamero", "yamete", "yamenaika"]):
        if any(w in pl_lower for w in ["nie rób tego", "przestań to robić"]):
            return "Sygnał audio JP: 'Yamero / Yamete' (ostry sprzeciw, protest lub żądanie przerwania ataku)"

    # 37. Shinde iru (stan rezultatywny vs trwające umieranie)
    if any(k in clean_jp for k in ["死んでいる", "死んでる"]) or any(k in rom_lower for k in ["shinde iru", "shinderu"]):
        if "umiera" in pl_lower:
            return "Sygnał audio JP: 'Shinde iru' (aspekt dokonany: stan zgonu, a nie proces umierania)"

    # 38. Tabun / Osoraku (domysł vs pewne 'na pewno' / 'na pewno nie')
    if any(k in clean_jp for k in ["たぶん", "多分", "恐らく", "おそら"]) or any(k in rom_lower for k in ["tabun", "osoraku"]):
        if any(w in pl_lower for w in ["na pewno", "z całą pewnością", "stuprocentowo", "wykluczone"]):
            return "Sygnał audio JP: 'Tabun / Osoraku' (wysoki stopień przypuszczenia i niepewności)"

    # 39. Yappari / Yahari (potwierdzenie podejrzeń)
    if any(k in clean_jp for k in ["やっぱり", "やはり", "矢張り"]) or any(k in rom_lower for k in ["yappari", "yahari"]):
        if any(w in pl_lower for w in ["po wszystkim", "mimo wszystko"]):
            return "Sygnał audio JP: 'Yappari' (potwierdzenie wcześniejszych podejrzeń intuicyjnych)"

    # 40. Sasuga / Sasuga ni ('As expected' vs 'Jak przystało / Bez przesady')
    if any(k in clean_jp for k in ["さすが", "流石"]) or any(k in rom_lower for k in ["sasuga", "sasugani", "sasuga ni"]):
        if any(w in pl_lower for w in ["zgodnie z oczekiwaniami", "jak oczekiwano"]):
            return "Sygnał audio JP: 'Sasuga' (uznanie dla kunsztu, reputacji i klasy rozmówcy)"

    # 41. Douse ('Anyway' vs fatalistyczne 'I tak...')
    if any(k in clean_jp for k in ["どうせ", "何れ"]) or "douse" in rom_lower or "dōse" in rom_lower:
        if "w każdym razie" in pl_lower or "tak czy inaczej" in pl_lower:
            return "Sygnał audio JP: 'Douse' (ton rezygnacji, cynizmu i fatalizmu wobec losu)"

    # 42. Masaka (szok / niedowierzanie vs kategoryczne wykluczenie)
    if any(k in clean_jp for k in ["まさか"]) or "masaka" in rom_lower:
        if any(w in pl_lower for w in ["żadna droga", "w żaden sposób", "żadnym sposobem"]):
            return "Sygnał audio JP: 'Masaka' (paraliżujący szok poznawczy wobec nieoczekiwanego obrotu spraw)"

    # 43. Shikata ga nai / Shouganai ('It can't be helped' vs 'Trudno / Nic nie poradzimy')
    if any(k in clean_jp for k in ["仕方がない", "しょうがない", "仕様がない", "仕方がねえ"]) or any(k in rom_lower for k in ["shikata ga nai", "shouganai", "shikatanai", "shou ga nai"]):
        if any(w in pl_lower for w in ["nie da się pomóc", "nie można pomóc", "nie da się temu zaradzić"]):
            return "Sygnał audio JP: 'Shouganai' (stoickie pogodzenie się z nieuchronnym biegiem wydarzeń)"

    # 44. Zettai ni / Kanarazu (kategoryczna obietnica/pewność)
    if any(k in clean_jp for k in ["絶対に", "絶対", "必ず"]) or any(k in rom_lower for k in ["zettai", "kanarazu"]):
        if any(w in pl_lower for w in ["może ", "chyba ", "prawdopodobnie "]):
            return "Sygnał audio JP: 'Zettai ni' (stuprocentowa pewność realizacji)"

    # 45. Ottotto / Acchichi / Itta / Sammu (Somatyczne Odruchy Ciała i Kakegoe vs angielskie kalki)
    if any(k in clean_jp for k in ["おっとっと", "おっと", "オットット", "あっちっち", "熱っ", "さっむ", "痛っ"]) or any(k in rom_lower for k in ["ottotto", "ototo", "acchichi", "sammu", "itta"]):
        if any(w in pl_lower for w in ["oho, spokojnie", "oho, ostrożnie", "oho spokojnie", "spokojnie..."]):
            return "Sygnał audio JP: ottotto (odruchowa utrata równowagi / potknięcie)"
        if "to jest gorące" in pl_lower or "to gorące" in pl_lower:
            return "Sygnał audio JP: acchichi (somatyczna reakcja na oparzenie termiczne)"
        if "to jest zimne" in pl_lower or "to zimne" in pl_lower:
            return "Sygnał audio JP: samui (somatyczna reakcja na szok termiczny / przejmujące zimno)"
        if "to boli" in pl_lower:
            return "Sygnał audio JP: itta (somatyczny okrzyk nagłego bólu mechanicznego)"

    # 46. Hontō na no ka / Tashika na no ka / Makoto ka (weryfikacja wiarygodności raportu)

    if any(k in clean_jp for k in ["本当なのか", "本当か", "本当ね", "確かなのか", "誠か", "実か"]) or any(k in rom_lower for k in ["honto nano ka", "hontou na no ka", "honto ka", "tashika na no ka", "makoto ka"]):
        if any(w in pl_lower for w in ["to prawda?", "czy to prawda?"]):
            return "Sygnał audio JP: 'Hontō na no ka' (żołnierskie żądanie weryfikacji raportu faktograficznego)"

    # 47. Haragei: Daijōbu & Chotto (Zawoalowane Odmowy vs pozorne zgody)
    if "大丈夫" in clean_jp or "daijoubu" in rom_lower or "daijobu" in rom_lower:
        if any(w in pl_lower for w in ["w porządku.", "w porządku!", "w porządku?"]):
            if any(w in en_text.lower() for w in ["help", "need", "want", "tea", "water", "okay", "fine", "alright", "careful"]):
                return "Sygnał audio JP: 'Daijōbu' (haragei: powściągliwa odmowa / brak potrzeby pomocy)"
    if "ちょっと" in clean_jp or "chotto" in rom_lower:
        if any(w in pl_lower for w in ["trochę...", "to trochę...", "trochę."]) and not any(w in pl_lower for w in ["poczekaj", "chwil", "zaraz"]):
            return "Sygnał audio JP: 'Chotto...' (zawieszenie głosu oznaczające odmowę lub zakłopotanie)"

    # 48. Hora! & Fuzja ze Słuchem i Prozodią (Popędzanie vs Złośliwy Triumf vs Rzut)
    if "ほら" in clean_jp or "hora" in rom_lower:
        is_shouting = any(w in prosody_lower for w in ["krzyk", "wzburzenie", "wzrost energii", "dbfs > -12"]) or en_text.endswith("!")
        is_sarcastic = any(w in prosody_lower for w in ["sarkazm", "dystans"]) or "miro" in rom_lower or "ne" in rom_lower or "見ろ" in clean_jp
        if any(w in pl_lower for w in ["spójrz", "patrz ", "popatrz", "zobacz"]):
            if is_sarcastic or "hora miro" in rom_lower or "見ろ" in clean_jp:
                return "Sygnał audio JP: Hora miro (złośliwy lub pouczający triumf)"
            elif is_shouting or any(w in en_text.lower() for w in ["come on", "hurry", "quick", "faster", "get moving"]):
                return "Sygnał audio JP: Hora (energiczne popędzenie do działania lub przekazanie rekwizytu)"
            elif any(w in en_text.lower() for w in ["take this", "here", "catch"]):
                return "Sygnał audio JP: Hora (energiczne popędzenie do działania lub przekazanie rekwizytu)"

    # 49. Rytualne Formuły Sytuacyjne Aisatsu (Ittekimasu, Tadaima, Ojama shimasu)
    if any(k in clean_jp for k in ["行ってきます", "行ってらっしゃい", "お邪魔します", "ただいま", "おかえり"]) or any(k in rom_lower for k in ["ittekimasu", "itterasshai", "ojama shimasu", "tadaima", "okaeri"]):
        if any(w in pl_lower for w in ["pójdę i wrócę", "idź i wróć", "będę przeszkadzał", "przeszkadzam", "wróciłem do domu", "witaj w domu"]):
            return "Sygnał audio JP: rytualna japońska formuła domowa / wyjściowa (Aisatsu)"

    # 50. Abunai! & Tasukete! (Okrzyki Bojowe i Bezpośrednie Zagrożenie Życia)
    if any(k in clean_jp for k in ["危ない", "危ねえ", "危ねっ"]) or any(k in rom_lower for k in ["abunai", "abune", "abunee"]):
        if any(w in pl_lower for w in ["niebezpiecznie", "to jest niebezpieczne", "niebezpieczeństwo"]):
            return "Sygnał audio JP: Abunai (krzyk bojowy ostrzegający przed bezpośrednim zagrożeniem życia)"
    if "助けて" in clean_jp or "tasukete" in rom_lower:
        if any(w in pl_lower for w in ["ocal mnie", "uratuj mnie"]):
            return "Sygnał audio JP: Tasukete (dramatyczne wezwanie ratunku w śmiertelnym niebezpieczeństwie)"

    # 51. Yare yare & Mendokusai & Shouganai (Westchnienia Znużenia i Ciężaru)
    yare_keys = ["yare yare", "yareyare", "yare-yare", "yare yare daze", "yareyaredaze"]
    if any(k in clean_jp for k in ["やれやれ", "やれやれだぜ"]) or any(k in rom_lower for k in yare_keys):
        if any(w in pl_lower for w in ["dobre nieszczęście", "dobra żałość", "daj mi przerwę", "no cóż, no cóż", "o drogi", "dobre niebiosa"]):
            return "Sygnał audio JP: 'Yare yare' (zrezygnowane westchnienie znużenia i ciężaru emocjonalnego)"

    if any(k in clean_jp for k in ["めんどくさい", "面倒"]) or any(k in rom_lower for k in ["mendokusai", "mendou", "mendou da"]):
        if any(w in pl_lower for w in ["co za ból", "jaki ból", "to jest ból", "jest uciążliwe"]):
            return "Sygnał audio JP: 'Mendokusai' (ostentacyjne zniechęcenie i udręka koniecznością wysiłku)"

    if any(k in clean_jp for k in ["しょうがない", "仕方がない", "しょうがねえ"]) or any(k in rom_lower for k in ["shou ga nai", "shouganai", "shikata ga nai", "shouganee"]):
        if any(w in pl_lower for w in ["nie można temu pomóc", "nie da się temu pomóc", "tak po prostu jest"]):
            return "Sygnał audio JP: 'Shouganai' (stoickie pogodzenie się z nieuchronnym biegiem wydarzeń)"

    # 52. Oi oi & Maa maa & Nante kotta & Iikagen ni shiro (Szok, Pacyfikowanie i Furia)
    if any(k in clean_jp for k in ["おいおい", "おいおいおい"]) or any(k in rom_lower for k in ["oi oi", "oioi"]):
        if any(w in pl_lower for w in ["hej hej", "hej, hej"]):
            return "Sygnał audio JP: 'Oi, oi...' (niedowierzanie i zdezorientowanie absurdem wypowiedzi)"

    if any(k in clean_jp for k in ["まあまあ"]) or any(k in rom_lower for k in ["maa maa", "maamaa"]):
        if any(w in pl_lower for w in ["cóż, cóż", "cóż cóż", "tak sobie"]):
            return "Sygnał audio JP: 'Maa, maa...' (uspokajający gest pacyfikacji rodzącego się sporu)"

    if any(k in clean_jp for k in ["なんてこった", "なんて事だ"]) or any(k in rom_lower for k in ["nante kotta", "nante koto da"]):
        if any(w in pl_lower for w in ["co za rzecz", "co to za sprawa", "jaka to rzecz"]):
            return "Sygnał audio JP: nante kotta (ekspresyjny okrzyk bezsilności wobec katastrofy)"

    if any(k in clean_jp for k in ["いい加減にしろ", "いい加減にしなさい"]) or any(k in rom_lower for k in ["iikagen ni shiro", "iikagen"]):
        if any(w in pl_lower for w in ["zrób to z umiarem", "bądź umiarkowany", "umiarkowanie"]):
            return "Sygnał audio JP: iikagen ni shiro (ostateczne wyczerpanie cierpliwości mówcy)"

    # 53. Yokatta & Yatta! (Ulga i Triumf)
    if any(k in clean_jp for k in ["よかった", "良かった"]) or any(k in rom_lower for k in ["yokatta", "yokattane", "yokatta na"]):
        if pl_lower.strip() in ["to było dobre.", "to było dobre!", "było dobrze.", "było dobrze!"] or pl_lower.startswith("to było dobre"):
            return "Sygnał audio JP: 'Yokatta...' (głębokie opadnięcie napięcia i ulga po zażegnaniu kryzysu)"

    if any(k in clean_jp for k in ["やった", "やったー", "やったぜ", "やったぞ"]) or any(k in rom_lower for k in ["yatta", "yattaa", "yattaze", "yattazo"]):
        if pl_lower.strip() in ["zrobiłem to.", "zrobiłem to!", "zrobiłam to.", "zrobiłam to!"] and not any(w in en_text.lower() for w in ["i made it happen", "i manufactured"]):
            return "Sygnał audio JP: Yatta (spontaniczny wybuch triumfu i radości z odniesionego sukcesu)"

    # 54. Logika Odpowiedzi na Przeczenia (Echo Agreement: Hai/Un vs Iie/Uun)
    is_neg_q = any(w in en_text.lower() for w in ["don't you", "aren't you", "didn't you", "can't you", "won't you", "haven't you", "isn't it"]) or any(k in clean_jp for k in ["ないの", "ないか", "ない？", "ないのか", "ないですか"]) or any(k in rom_lower for k in ["nai no", "nai ka", "nai desu ka"])
    if is_neg_q:
        if any(clean_jp.startswith(k) or clean_jp == k for k in ["はい", "うん", "ええ"]) or any(rom_lower.startswith(k) or rom_lower == k for k in ["hai", "un", "ee"]):
            if pl_lower.startswith("tak") or pl_lower.startswith("jasne") or pl_lower == "tak." or pl_lower == "tak!":
                return "Sygnał audio JP: 'Hai/Un' (lub 'Iie/Uun') na pytanie z przeczeniem (Echo Agreement w logice japońskiej)"

    # 55. Kansai-ben Jibun ('Ty') & Relacje Trzecioosobowe (Onii-chan / Onee-chan)
    is_kansai = any(k in clean_jp for k in ["ねん", "やろ", "へん", "せや", "あかん"]) or any(k in rom_lower for k in ["nen", "yaro", "hen", "seya", "akan", "honma"])
    if is_kansai and ("自分" in clean_jp or "jibun" in rom_lower):
        if any(w in pl_lower for w in ["ja ", "mnie ", "siebie ", "samemu", "sobie "]) and not any(w in pl_lower for w in ["ty ", "ciebie ", "tobie ", "cię "]):
            return "Sygnał audio JP: 'Jibun' jako zaimek 2. osoby 'ty' w rejestrze dialektalnym zachodnim"

    if any(k in clean_jp for k in ["お兄ちゃん", "お姉ちゃん"]) or any(k in rom_lower for k in ["onii-chan", "onee-chan", "oniichan", "oneechan"]):
        if any(w in pl_lower for w in ["starszy brat", "starsza siostra", "onii-chan", "onee-chan"]):
            return "Sygnał audio JP: miano starszego rodzeństwa użyte w perspektywie 3. osoby"

    # 56. Repetycje Myśli i Separacja od Dialogu Mówionego (Tomerarenai)
    if any(k in clean_jp for k in ["止められない", "無理だ", "駄目だ"]) or any(k in rom_lower for k in ["tomerarenai", "muri da", "dame da"]) or any(w in en_text.lower() for w in ["can't stop it", "cannot stop it", "can't hold it"]):
        if any(w in pl_lower for w in ["nie chcę, żebyś", "stracił fanki", "przeze mnie", "twoje fanki"]):
            return "Sygnał audio JP: repetycja paniki w monologu wewnętrznym ('Tomerarenai...')"

    # 57. Hitori ni shite vs Hottoite
    if any(k in clean_jp for k in ["一人にして", "独りにして", "ひとりにして", "一人で", "独りで"]) or any(k in rom_lower for k in ["hitori ni shite", "hitori de", "hitorinisite", "hitori"]):
        if any(w in pl_lower for w in ["daj mi spokój", "daj spokój", "odczep się", "spadaj", "odwal się"]):
            return "Sygnał audio JP: 'Hitori ni shite' (prośba o pozostawienie w samotności w cierpieniu)"

    # 58. Betsuni vs Nandemonai
    if ("別に" in clean_jp or "betsuni" in rom_lower) and any(w in en_text.lower() for w in ["nothing", "it's nothing", "not really"]):
        if any(w in pl_lower for w in ["to nic takiego", "nie ma sprawy", "nic się nie stało"]):
            return "Sygnał audio JP: 'Betsu ni...' (emocjonalny chłód, dystansowanie się lub zbycie tematu)"

    # 59. Kolaps Formy Adresatywnej / Spurious 'Pan/Pani' przy 'You' na 'Ty'
    if any(w in en_text.lower() for w in ["you won", "you did", "you saw", "you told", "you said", "you have", "you had", "you were", "you know", "did you", "have you", "why did you"]):
        if any(w in pl_lower for w in ["wygrał pan", "wygrała pani", "zrobił pan", "zrobiła pani", "widział pan", "widziała pani", "powiedział pan", "powiedziała pani", "pan wie", "pani wie", "wie pan", "wie pani", "pan widzi", "pani widzi", "pan myśli", "pani myśli", "pan mówi", "pani mówi"]):
            return "Sygnał audio JP: swobodna relacja koleżeńska w 2. osobie (bez dystansu formalnego pan/pani)"

    # 60. Zgodność Foniczno-Semantyczna Seiyū i Test Ucha Widza
    if any(k in clean_jp for k in ["一人にして", "独りにして", "ひとりにして"]) or "hitori ni shite" in rom_lower or "hitori" in rom_lower:
        if any(w in pl_lower for w in ["daj mi spokój", "daj spokój"]):
            return "Sygnał audio JP: 'Hitori ni shite' (prośba o pozostawienie w samotności w cierpieniu)"

    if any(k in clean_jp for k in ["助けて", "たすけて"]) or "tasukete" in rom_lower:
        if any(w in pl_lower for w in ["ocal mnie", "uratuj mnie"]):
            return "Sygnał audio JP: Tasukete (dramatyczne wezwanie ratunku w śmiertelnym niebezpieczeństwie)"

    if any(k in clean_jp for k in ["やめろ", "やめて"]) or "yamero" in rom_lower or "yamete" in rom_lower:
        if any(w in pl_lower for w in ["nie rób tego", "nie czyń"]):
            return "Sygnał audio JP: 'Yamero / Yamete' (ostry sprzeciw, protest lub żądanie przerwania ataku)"


    # 61. Dysonans Afektywny i Sarkazm (Acoustic Incongruity Engine)
    is_sarcastic_prosody = any(w in prosody_lower for w in [
        "sarkazm", "dystans", "chłód", "cynizm", "ironia", "drwiąc", "flat", "falling", "chłodny sarkazm"
    ])
    if is_sarcastic_prosody:
        polite_en_patterns = [
            "thank you", "thanks", "good job", "well done", "nice work", "great job",
            "i'm sorry", "sorry", "excuse me", "my bad", "what a help", "so helpful",
            "glad to hear", "happy to help", "you're the best"
        ]
        polite_jp_patterns = [
            "arigatou", "arigato", "tasukatta", "gomen", "gomenne", "sumimasen",
            "sasuga", "yokatta", "ureshii", "wakarimashita"
        ]
        has_polite_en = any(p in en_text.lower() for p in polite_en_patterns)
        has_polite_jp = any(p in rom_lower for p in polite_jp_patterns) or any(k in clean_jp for k in ["ありがとう", "助かった", "ごめん", "すみません", "流石", "さすが", "よかった"])
        if has_polite_en or has_polite_jp:
            if any(w in pl_lower for w in ["dziękuję", "dzięki", "dobra robota", "świetna robota", "przepraszam", "cieszę się", "wspaniale"]):
                return (
                    "[TELEMETRIA: dysonans afektywny / sarkazm: w audio seiyū słychać chłód, ironię lub dystans]"
                )

    # 62. Echo Agreement Discrepancy (Iie / Uun vs 'Nie' na pytanie z przeczeniem)
    if any(k in clean_jp for k in ["いいえ", "ううん", "いや"]) or any(k in rom_lower.split() for k in ["iie", "uun", "iya"]):
        if any(w in en_text.lower() for w in ["don't you", "aren't you", "didn't you", "can't you", "won't you", "isn't it"]):
            if re.match(r"^\s*(nie|n-nie)[\.!\?…]*$", pl_lower.strip()):
                return "Sygnał audio JP: 'Iie/Uun' na pytanie z przeczeniem (Echo Agreement w logice japońskiej)"

    return None

def detect_japanese_pragmatic_register(jp_text: str, en_text: str = "") -> Optional[str]:
    """
    Analyzes Whisper Japanese transcription and English text to detect the socio-pragmatic register
    (e.g., Feudal Samurai/Vassal, Aristocratic Ojou-sama, Tough Soldier, Youth Slang, Romantic Kokuhaku).
    """
    if not jp_text:
        return None
        
    clean_jp = re.sub(r"\[.*?\]", "", jp_text).strip().lower()
    romaji_match = re.findall(r"\[(.*?)\]", jp_text)
    rom_lower = romaji_match[0].strip().lower() if romaji_match else clean_jp
    
    # 1. Feudal Vassal / Samurai / Humble Servitude (Gozaru, De gozaimasu, Mousu, Tsukamatsuru, Kashikomari)
    if any(k in clean_jp for k in ["ござる", "でございます", "ございます", "申す", "仕る", "殿", "上様", "かしこまり", "畏まり"]) or any(k in rom_lower for k in ["gozaru", "gozaimasu", "mousu", "tsukamatsuru", "dono", "uesama", "kashikomari"]):
        return "Feudalny poddańczy / Wasal (stylizacja na 'Panie mój / Wasza Miłość', szacunek poddańczy)"
        
    # 2. Aristocratic / Ojou-sama / Noble Lady (-desu wa, -kashira, -asobase)
    if any(k in clean_jp for k in ["ですわ", "かしら", "あそばせ", "わたくし"]) or any(k in rom_lower for k in ["desu wa", "kashira", "asobase", "watakushi"]):
        return "Arystokratyczny / Ojou-sama (elegancka, dystyngowana polszczyzna damy)"
        
    # 3. Tough Soldier / Battle Slang (-ze, -zo, temee, kisama, ore)
    if any(k in clean_jp for k in ["ぜ", "ぞ", "てめえ", "貴様", "野郎", "俺"]) or any(k in rom_lower for k in ["-ze", " ze", "-zo", " zo", "temee", "kisama", "yarou", "ore"]):
        return "Szorstki żołnierski / Bojowy (męski, twardy rejestr wojskowy, brak zmiękczeń)"

    # 4. Rejestr młodzieńczy / chłopięcy (Boku, Ore, Oira, Boku-chan, Niichan, Neechan)
    if any(k in clean_jp for k in ["ぼく", "ボク", "おいら", "ボクちゃん", "ぼくちゃん", "にいちゃん", "ねえちゃん"]) or any(k in rom_lower for k in ["boku ", "boku,", "boku-", "oira", "niichan", "neechan", "boku wa", "boku ga"]):
        return "Rejestr młodzieńczy / chłopięcy (głos dziecięcy seiyū, tożsamość podmiotu: rodzaj męski)"

    # 5. Rejestr dziewczęcy (Atashi, Uchi, Onii-chan, Onee-chan, -na no)
    if any(k in clean_jp for k in ["あたち", "あたし", "ウチ", "お兄ちゃん", "お姉ちゃん", "おにいちゃん", "おねえちゃん"]) or any(k in rom_lower for k in ["atashi", "atachi", "onii-chan", "onee-chan", "oniichan", "oneechan"]):
        return "Rejestr dziewczęcy (wysoki tembr seiyū, tożsamość podmiotu: rodzaj żeński)"

    # 6. Youth / Casual Slang (-ssu, -yatsu, -chatt, -tteba)
    if any(k in clean_jp for k in ["っす", "やつ", "ちゃった", "ってば"]) or any(k in rom_lower for k in ["-ssu", " ssu", "yatsu", "chatta", "tteba"]):
        return "Młodzieżowy / Swobodny (luźny styl potoczny, dynamiczne skróty)"
        
    # 7. Romantic Intimate / Kokuhaku (daisuki, aishiteru, zutto issho)
    if any(k in clean_jp for k in ["大好き", "愛してる", "ずっと一緒"]) or any(k in rom_lower for k in ["daisuki", "aishiteru", "zutto issho"]):
        return "Czuły miłosny / Kokuhaku (wyznanie miłosne 'Kocham cię', eliminacja friendzone)"

    # 8. Rejestr gwarowy południowo-zachodni (Chesto, Gowasu, Oddon, Jaddo, Mosu)
    if any(k in clean_jp for k in ["チェスト", "ごわす", "でごわす", "おっどん", "じゃっど", "もす"]) or any(k in rom_lower for k in ["chesto", "gowasu", "oddon", "jaddo", "mosu"]):
        return "Rejestr gwarowy południowo-zachodni (fonetyczne ściągnięcia, twarda archaiczna artykulacja)"

    # 9. Rejestr gwarowy zachodni (-nen, -yaro, honma, akan, seyana, -dosu, oideyasu)
    if any(k in clean_jp for k in ["ねん", "やろ", "ほんま", "あかん", "せやな", "どす", "おいでやす"]) or any(k in rom_lower for k in ["-nen", "honma", "akan", "seyana", "nande ya", "dosu", "oideyasu"]):
        return "Rejestr gwarowy zachodni (zadziorna, błyskotliwa ekspresja potoczna)"

    # 10. Rejestr gwarowy północny prowincjonalny (-dabe, -daccha, ora, nda, -zura, nashite)
    if any(k in clean_jp for k in ["だべ", "だっちゃ", "おら", "ずら", "なして"]) or any(k in rom_lower for k in ["-dabe", "-daccha", "dappe", "zura", "nashite"]):
        return "Rejestr gwarowy północny prowincjonalny (ciepła, gawędziarska mowa prowincjonalna)"

    # 11. Rejestr szorstki półświatka (-jaken, -jakee, -noo, buchi, taigii)
    if any(k in clean_jp for k in ["じゃけん", "じゃけえ", "たいぎい", "ぶち"]) or any(k in rom_lower for k in ["jaken", "jakee", "taigii", "buchi"]):
        return "Rejestr szorstki półświatka (bezkompromisowy żargon uliczny)"

    # 12. Rejestr gwarowy południowy (-to?, -bai, -tai, suitoo, batten)
    if any(k in clean_jp for k in ["ばい", "たい", "好いとー", "ばってん"]) or any(k in rom_lower for k in ["-bai", "-tai", "suitoo", "batten"]):
        return "Rejestr gwarowy południowy (śpiewna, bezpośrednia mowa melodyjna)"

    # 13. Rejestr gwarowy wyspiarski (Haisai, Mensoore, Nankurunaisa, -saa)
    if any(k in clean_jp for k in ["はいさい", "はいたい", "めんそーれ", "なんくるないさ"]) or any(k in rom_lower for k in ["haisai", "haitai", "mensoore", "nankurunaisa"]):
        return "Rejestr gwarowy wyspiarski (słoneczny, zrelaksowany ton regionalny)"

    # 14. Rejestr gwarowy surowy (Namara, Shibareru, Shitakke)
    if any(k in clean_jp for k in ["なまら", "しばれる", "したっけ"]) or any(k in rom_lower for k in ["namara", "shibareru", "shitakke"]):
        return "Rejestr gwarowy surowy (lakoniczna, powściągliwa ekspresja północy)"
        
    return None

def get_audio_semantic_anchor(jp_text: str, en_text: str = "") -> Optional[str]:
    """
    SAGE (Seiyū Acoustic Grounding Engine).
    Analyzes Whisper Japanese transcription and English text to detect dangerous pivot ambiguities
    and auditory anchor discrepancies. Returns declarative semantic anchors.
    """
    if not jp_text:
        return None
    clean_jp = re.sub(r"\[.*?\]", "", jp_text).strip().lower()
    romaji_match = re.findall(r"\[(.*?)\]", jp_text)
    rom_lower = romaji_match[0].strip().lower() if romaji_match else to_romaji(clean_jp).lower()
    en_lower = (en_text or "").lower()

    # 1. Hitori ni shite vs Hottoite / Leave me alone
    if any(k in clean_jp for k in ["一人にして", "独りにして", "ひとりにして", "一人で", "独りで"]) or any(k in rom_lower for k in ["hitori ni shite", "hitori de", "hitorinisite", "hitori"]):
        if any(w in en_lower for w in ["leave me alone", "alone", "by myself", "give me a break", "peace"]):
            return "Kotwica semantyczna audio JP: '一人にして (Hitori ni shite)' (intencja: potrzeba samotności i odosobnienia w cierpieniu)"

    # 2. Betsuni vs Nandemonai / It's nothing
    if ("別に" in clean_jp or "betsuni" in rom_lower) and any(w in en_lower for w in ["nothing", "not really", "it's fine", "never mind"]):
        return "Kotwica semantyczna audio JP: '別に (Betsuni)' (afekt: emocjonalny chłód, dystansowanie się, zbycie tematu)"

    # 3. Mou ii vs Kekkou desu / That's enough / It's fine
    if ("もういい" in clean_jp or "mou ii" in rom_lower or "mouii" in rom_lower) and any(w in en_lower for w in ["enough", "it's fine", "forget it"]):
        return "Kotwica semantyczna audio JP: 'もういい (Mou ii)' (intencja: rezygnacja, urażona duma, ucięcie dyskusji)"

    # 4. Gaman dekinai vs Yurusenai / I can't take it
    if any(k in clean_jp for k in ["我慢できない", "耐えられない"]) or any(k in rom_lower for k in ["gaman dekinai", "taerarenai"]):
        return "Kotwica semantyczna audio JP: '我慢できない (Gaman dekinai)' (afekt: ból fizyczny lub psychiczny przekraczający wytrzymałość)"

    # 5. Yokatta
    if any(k in clean_jp for k in ["よかった", "良かった"]) or any(k in rom_lower for k in ["yokatta", "yokattane"]):
        if any(w in en_lower for w in ["good", "great", "glad", "relief", "thank goodness", "thank god"]):
            return "Kotwica semantyczna audio JP: 'よかった (Yokatta)' (afekt: kamień z serca, głęboka ulga po zażegnaniu kryzysu)"

    # 6. Yatta
    if any(k in clean_jp for k in ["やった", "やったー"]) or any(k in rom_lower for k in ["yatta", "yattaa"]):
        if any(w in en_lower for w in ["did it", "done it", "i did", "we did", "yes", "hooray"]):
            return "Kotwica semantyczna audio JP: 'やった (Yatta)' (afekt: spontaniczny wybuch triumfu i radości z sukcesu)"

    # 7. Uso / Maji
    if any(k in clean_jp for k in ["嘘", "うそ", "マジ", "まじ"]) or any(k in rom_lower for k in ["uso", "maji"]):
        if any(w in en_lower for w in ["lie", "lying", "no way", "really", "kidding", "serious"]):
            return "Kotwica semantyczna audio JP: '嘘/マジ (Uso / Maji)' (afekt: szok poznawczy i nagłe niedowierzanie)"

    # 8. Mendokusai
    if any(k in clean_jp for k in ["めんどくさい", "面倒くさい", "面倒"]) or any(k in rom_lower for k in ["mendokusai", "mendou"]):
        if any(w in en_lower for w in ["pain", "bother", "hassle", "trouble", "annoying", "drag"]):
            return "Kotwica semantyczna audio JP: '面倒くさい (Mendokusai)' (afekt: ostentacyjne zniechęcenie i udręka koniecznością wysiłku)"

    # 9. Tasukete
    if any(k in clean_jp for k in ["助けて", "たすけて"]) or any(k in rom_lower for k in ["tasukete", "tasukete kure"]):
        if any(w in en_lower for w in ["help", "save"]):
            return "Kotwica semantyczna audio JP: '助けて (Tasukete)' (akt mowy: dramatyczne wezwanie ratunku w śmiertelnym niebezpieczeństwie)"

    # 10. Yamero / Yamete
    if any(k in clean_jp for k in ["やめろ", "やめて", "止めろ", "止めて"]) or any(k in rom_lower for k in ["yamero", "yamete"]):
        if any(w in en_lower for w in ["stop", "don't"]):
            return "Kotwica semantyczna audio JP: 'やめろ/やめて (Yamero / Yamete)' (akt mowy: ostry sprzeciw, protest lub żądanie przerwania ataku)"

    # 11. Shikata ga nai / Shou ga nai
    if any(k in clean_jp for k in ["しょうがない", "仕方がない", "仕方ない"]) or any(k in rom_lower for k in ["shou ga nai", "shikata ga nai", "shouganai", "shikatanai"]):
        if any(w in en_lower for w in ["help", "choice", "way"]):
            return "Kotwica semantyczna audio JP: 'しょうがない (Shou ga nai)' (postawa: stoickie pogodzenie się z nieuchronnym losem)"

    # 12. Pronoun: omae / kimi / kisama / temee
    if any(k in clean_jp for k in ["お前", "君", "貴様", "てめえ"]) or any(k in rom_lower.split() for k in ["omae", "kimi", "kisama", "temee"]):
        if any(w in en_lower for w in ["you", "your"]):
            return "Kotwica semantyczna audio JP: zaimek 2. osoby ('omae / kimi / kisama / temee') (relacja bezpośrednia na 'ty', brak dystansu formalnego)"

    # 13. Pronoun: ore / boku
    if any(k in clean_jp for k in ["俺", "僕"]) or any(k in rom_lower.split() for k in ["ore", "boku"]):
        if any(w in en_lower for w in ["i ", "i'm", "i've", "my ", "me"]):
            return "Kotwica semantyczna audio JP: męski zaimek 1. osoby ('ore / boku') (tożsamość podmiotu: rejestr męski)"

    # 14. Pronoun: atashi / atai
    if any(k in clean_jp for k in ["あたし", "あtai", "あたい"]) or any(k in rom_lower.split() for k in ["atashi", "atai"]):
        if any(w in en_lower for w in ["i ", "i'm", "i've", "my ", "me"]):
            return "Kotwica semantyczna audio JP: żeński zaimek 1. osoby ('atashi / atai') (tożsamość podmiotu: rejestr żeński)"

    # 15. Pivot: Iku vs Coming
    if any(k in clean_jp for k in ["行く", "いく", "行きます", "行こう", "いこう"]) or any(k in rom_lower.split() for k in ["iku", "ikimasu", "ikou"]):
        if any(w in en_lower for w in ["coming", "i'm coming", "on my way"]):
            return "Kotwica semantyczna audio JP: '行く (Iku)' (wektor deiktyczny: ruch OD mówcy w stronę celu)"

    # 16. Pivot: Naruhodo vs Sou ka vs Wakatta / I see
    if any(k in clean_jp for k in ["なるほど", "成程"]) or "naruhodo" in rom_lower:
        if any(w in en_lower for w in ["i see", "makes sense", "understand"]):
            return "Kotwica semantyczna audio JP: 'なるほど (Naruhodo)' (poznanie: zrozumienie toku rozumowania rozmówcy / olśnienie)"
    elif any(k in clean_jp for k in ["そうか", "そっか"]) or any(k in rom_lower.split() for k in ["souka", "sokka", "sou ka"]):
        if any(w in en_lower for w in ["i see", "is that so"]):
            return "Kotwica semantyczna audio JP: 'そうか/そっか (Sou ka / Sokka)' (poznanie: powściągliwe przyjęcie informacji do wiadomości)"

    # 17. Pivot: Chigau / Chigaimasu
    if any(k in clean_jp for k in ["違う", "ちがう", "違います", "ちがいます"]) or any(k in rom_lower.split() for k in ["chigau", "chigaimasu", "chiga"]):
        if any(w in en_lower for w in ["no", "wrong", "not true", "not like that", "mistake"]):
            return "Kotwica semantyczna audio JP: '違う/違います (Chigau / Chigaimasu)' (akt mowy: stanowcze zaprzeczenie tożsamości lub faktom)"

    # 18. Pivot: Ii desu / Kekkou desu
    if any(k in clean_jp for k in ["いいです", "結構です", "けっこうです"]) or any(k in rom_lower.split() for k in ["ii desu", "kekkou", "kekkou desu"]):
        if any(w in en_lower for w in ["fine", "good", "okay", "no thanks"]):
            return "Kotwica semantyczna audio JP: '結構です/いいです (Kekkou desu / Ii desu)' (pragmatyka: uprzejme podziękowanie połączone z odmową oferty)"

    # 19. Urusai / Damare
    if any(k in clean_jp for k in ["うるさい", "うるせえ", "うるせー", "だまれ", "黙れ"]) or any(k in rom_lower.split() for k in ["urusai", "urusaina", "urusee", "uruse-", "ussee", "damare"]):
        return "Kotwica semantyczna audio JP: 'うるさい/黙れ (Urusai / Damare)' (akt mowy: uciszanie rozmówcy, poirytowanie gadaniem)"

    # 20. Tadaima / Okaeri
    if any(k in clean_jp for k in ["ただいま", "おかえり", "お帰り"]) or any(k in rom_lower.split() for k in ["tadaima", "okaeri"]):
        return "Kotwica semantyczna audio JP: formuła 'Tadaima / Okaeri' (aisatsu: rytualne domowe powitanie po powrocie)"

    # 21. Shiranai yo / Shiranai
    if any(k in clean_jp for k in ["知らないよ", "しらないよ", "知らねえよ", "知らん"]) or any(k in rom_lower.split() for k in ["shiranaiyo", "shiranai yo", "shiraneeyo", "shiran"]):
        if any(w in en_lower for w in ["care", "warn", "see if i care", "don't blame me", "suit yourself", "don't know", "i don't care"]):
            return "Kotwica semantyczna audio JP: '知らないよ (Shiranai yo)' (intencja: odcięcie się od konsekwencji czynów rozmówcy w tonie ostrzeżenia)"

    # 22. Katte ni shiro / Katte ni
    if any(k in clean_jp for k in ["勝手にしろ", "かってにしろ", "勝手にしなさい", "勝手に"]) or any(k in rom_lower.split() for k in ["katte ni shiro", "kattenishiro", "katte"]):
        if any(w in en_lower for w in ["whatever", "suit yourself", "as you like", "want", "please"]):
            return "Kotwica semantyczna audio JP: '勝手にしろ (Katte ni shiro)' (intencja: wzgardliwe zerwanie sporu i pozostawienie rozmówcy własnemu losowi)"

    # 23. Itadakimasu
    if any(k in clean_jp for k in ["いただきます", "頂きます"]) or "itadakimasu" in rom_lower:
        if any(w in en_lower for w in ["feast", "dinner", "eat", "food", "devour", "dig in"]):
            return "Kotwica semantyczna audio JP: 'いただきます (Itadakimasu)' (pragmatyka: drapieżne lub rytualne spożycie ofiary w kontekście starcia)"

    # 24. Echo Agreement - Hai / Iie on Negative Questions
    if any(k in clean_jp for k in ["いいえ", "ううん", "いや"]) or any(k in rom_lower.split() for k in ["iie", "uun", "iya"]):
        if any(w in en_lower for w in ["no", "nope"]):
            return "Kotwica semantyczna audio JP: 'いいえ/ううん/いや (Iie / Uun / Iya)' (logika japońska: zaprzeczenie pytania z negacją)"
    elif any(k in clean_jp for k in ["はい", "うん", "ええ"]) or any(k in rom_lower.split() for k in ["hai", "un", "ee"]):
        if any(w in en_lower for w in ["yes", "yeah", "right"]):
            return "Kotwica semantyczna audio JP: 'はい/うん/ええ (Hai / Un / Ee)' (logika japońska: potwierdzenie pytania z negacją)"

    return None

def sanitize_sub_text(text: str, is_ass: bool = True) -> str:
    """
    Cleans subtitle text from broken tags, unclosed brackets, and artifacts,
    converting HTML tags <i> / <b> to native ASS formatting {\\i1}...{\\i0}.
    """
    if not text:
        return ""
    
    if is_ass:
        # Convert <i> and <b> to ASS {\i1} and {\b1}
        text = re.sub(r"<i>(.*?)</i>", r"{\\i1}\1{\\i0}", text, flags=re.IGNORECASE)
        text = re.sub(r"<b>(.*?)</b>", r"{\\b1}\1{\\b0}", text, flags=re.IGNORECASE)
        # Strip any remaining raw HTML tags
        text = re.sub(r"</?[a-zA-Z][^>]*>", "", text)
        # Strip corrupted ASS tags (preserving {\i1}, {\i0}, {\b1}, {\b0})
        text = re.sub(r"\{(?!(?:\\i[01]|\\b[01]))[^}]*\}?", "", text)
        text = re.sub(r"\{[^\\]*$", "", text)
        # Deduplicate repeated adjacent tags (e.g. {\i1}{\i1} -> {\i1})
        text = re.sub(r"(\{\\i[01]\})+", r"\1", text)
        text = re.sub(r"(\{\\b[01]\})+", r"\1", text)
    else:
        # For SRT: convert ASS tags to HTML
        text = re.sub(r"\{\\i1\}(.*?)\{\\i0\}", r"<i>\1</i>", text)
        text = re.sub(r"\{\\b1\}(.*?)\{\\b0\}", r"<b>\1</b>", text)
        # Strip all curly bracket tags
        text = re.sub(r"\{[^}]*\}?", "", text)
        # Strip unwanted HTML tags except <i>, </i>, <b>, </b>
        text = re.sub(r"</?(?!(?:i|b)\b)[a-zA-Z][^>]*>", "", text)

    # Normalize whitespace and line breaks
    text = re.sub(r"[ \t]+", " ", text).strip()
    return text

def is_song_line(ev: Any, text: str) -> bool:
    """Detects whether subtitle line is part of a song (OP/ED/Theme/Song/Karaoke) or musical note text."""
    if not text:
        return False
    
    clean_strip = text.strip()
    # 1. Signs, brackets, headers, top captions are NEVER songs
    if clean_strip.startswith("[") and clean_strip.endswith("]"):
        return False
    if r"\an8" in text or r"\an7" in text or r"\an9" in text or r"\pos" in text:
        return False
        
    style_name = (getattr(ev, "style", "") or "").lower().strip()
    if style_name in ["sign", "signs", "title", "top", "caption", "typesetting", "location", "header", "on-screen"]:
        return False

    # 2. Check for explicit musical note symbols in the original text
    if any(sym in text for sym in ["♪", "♫", "🎶", "♬"]):
        return True

    # 3. Match song-specific style names (OP_Roman, ED_Kanji, Theme, Song, Karaoke)
    style_normalized = style_name.replace("_", " ").replace("-", " ")
    if re.search(r"\b(op|ed|opening|ending|song|songs|theme|insert|insert song|karaoke|romaji|kanji|piosenka|śpiew|music)\b", style_normalized):
        return True
        
    return False

def clean_orphaned_dialogue_dashes(text: str) -> str:
    """
    Strips accidental leading dialogue dashes on single-speaker lines.
    In AVT standards, a dialogue dash ('- ') is ONLY valid when two different
    characters speak in the same subtitle block (e.g., '- Line 1\\N- Line 2').
    If a subtitle has only one speaker, leading dashes are visual noise.
    """
    if not text:
        return text
    
    # If the text has a second line with a dash (e.g. "\N- " or "\n- "), it is a valid dual-speaker block!
    if r"\N-" in text or r"\N -" in text or r"\N–" in text or r"\N –" in text or "\n-" in text or "\n -" in text:
        ts_prefix, clean_body = extract_typesetting_tags(text)
        parts = re.split(r"\\N|\\n|\n", clean_body)
        if len(parts) == 2:
            p0 = re.sub(r"^[-–—]\s*", "", parts[0]).strip()
            p1 = re.sub(r"^[-–—]\s*", "", parts[1]).strip()
            sep = r"\N" if r"\N" in text else "\n"
            return f"{ts_prefix}- {p0}{sep}- {p1}"
        return text
        
    ts_prefix, clean_body = extract_typesetting_tags(text)

    # In-line dual speaker turn (e.g. "Gratulacje... - Rozpacz po przegranej...")
    dual_turn_match = re.match(r"^[-–—]?\s*(.+?(?:[.!?…]+|\]|\))\s*)[-–—]\s*((?:\{[^\}]*\})*[A-ZĄĆĘŁŃÓŚŹŻa-ząćęłńóśźż…\[].+)$", clean_body, re.DOTALL)
    if dual_turn_match:
        p1 = re.sub(r"^[-–—]\s*", "", dual_turn_match.group(1)).strip()
        p2 = re.sub(r"^[-–—]\s*", "", dual_turn_match.group(2)).strip()
        sep = r"\N"
        return f"{ts_prefix}- {p1}{sep}- {p2}"

    # Asymmetric dual speaker lines where line 1 starts with a dash and line 2 starts a distinct sentence
    if r"\N" in clean_body or "\n" in clean_body:
        parts = re.split(r"\\N|\\n|\n", clean_body)
        if len(parts) == 2:
            p0 = parts[0].strip()
            p1 = parts[1].strip()
            if re.match(r"^[-–—]\s+", p0) and re.search(r"[.!?…]$", p0):
                if re.match(r"^[A-ZĄĆĘŁŃÓŚŹŻ0-9„\"'\(]", p1):
                    clean_p0 = re.sub(r"^[-–—]\s*", "", p0).strip()
                    clean_p1 = re.sub(r"^[-–—]\s*", "", p1).strip()
                    sep = r"\N" if r"\N" in text else "\n"
                    return f"{ts_prefix}- {clean_p0}{sep}- {clean_p1}"

    # Strip leading dash on genuine single-speaker line
    clean_body = re.sub(r"^[-–—]\s*", "", clean_body)
    return f"{ts_prefix}{clean_body}" if ts_prefix else clean_body

def apply_simultaneous_dialogue_formatting(events: List[Any]) -> List[Any]:
    """
    Simultaneous Dialogue Formatting (AVT Standard):
    Ensures that single-speaker lines do NOT have orphaned leading dashes,
    while multi-speaker lines within a single subtitle block correctly use dialogue dashes.
    """
    for ev in events:
        if ev.text and not is_song_line(ev, ev.text):
            ev.text = clean_orphaned_dialogue_dashes(ev.text)
    return events

def create_adaptive_batches(
    raw_entries: list,
    base_batch_size: int = 24,
    max_batch_size: int = 34,
    min_scene_batch: int = 16,
    min_leap_batch: int = 12,
    leap_threshold_ms: int = 8000,
    scene_threshold_ms: int = 3800,
    coalesce_tail: Optional[bool] = None
) -> list:
    """
    Groups subtitle events into coherent, scene-aligned batches,
    adapting to dialogue density and scene pauses while preventing costly micro-batch fragmentation:
    - Major scene break (>= 3800ms gap) starts a new batch if current batch has reached at least min_scene_batch (16) lines.
    - Massive temporal leap (>= 8000ms gap) starts a new batch if current batch has reached at least min_leap_batch (12) lines.
    - Standard dramatic beat break (>= 2800ms gap) starts a new batch when current batch has reached at least 18 lines.
    - Continuous dialogue without scene cuts stays together up to max_batch_size (34 lines) or 150 words.
    Short sub-scenes (< 12-16 lines) are safely coalesced into the current batch with an explicit intra-batch
    scene cut marker ([ZMIANA SCENY / CIĘCIE MONTAŻOWE: Δt = X.Xs]), ensuring zero extra API overhead ($0.00 PLN)
    and 100% dramatic protection.
    """
    if not raw_entries:
        return []

    if coalesce_tail is None:
        coalesce_tail = (len(raw_entries) >= 40)

    batches = []
    current_batch = []
    current_words = 0

    for item in raw_entries:
        ev = item[1]
        text_clean = clean_text_for_len(item[2])
        words = len(text_clean.split())

        is_full = len(current_batch) >= max_batch_size
        is_dense = len(current_batch) >= base_batch_size and current_words >= 150

        gap_ms = (ev.start - current_batch[-1][1].end) if current_batch else 0
        is_scene_break = current_batch and (
            (gap_ms >= leap_threshold_ms and len(current_batch) >= min_leap_batch) or
            (gap_ms >= scene_threshold_ms and len(current_batch) >= min_scene_batch) or
            (gap_ms >= 2800 and len(current_batch) >= 18)
        )

        # Syntactic Sentence Boundary Coalescence:
        # Prevent cutting batches across compound sentences / enjambment when gap < 2000ms (or 3500ms for incomplete sentences)
        is_sentence_continuation = False
        if current_batch and len(current_batch) < (max_batch_size + 4):
            prev_txt = clean_text_for_len(current_batch[-1][2]).strip()
            curr_txt = text_clean.strip()
            prev_ends_incomplete = (
                prev_txt.endswith((",", "-", "–", "—", "...", "…")) or
                bool(re.search(r"\b(?:and|but|that|which|because|so|if|or|i|a|że|bo|choć|chociaż|gdy|kiedy|więc|zatem)\s*$", prev_txt, re.IGNORECASE))
            )
            curr_starts_lower = bool(curr_txt and curr_txt[0].islower() and not curr_txt.startswith(("http", "www")))
            prev_has_terminal_punct = bool(re.search(r"[.!?][\"'”’)]*\s*$", prev_txt))
            curr_starts_continuation_word = bool(re.match(
                r"^(?:and|but|that|which|because|so|if|or|however|therefore|although|though|since|unless|until|while|where|i|a|że|bo|choć|chociaż|gdy|kiedy|więc|zatem|ponieważ|bowiem|gdyż|lecz|ale|zaś|natomiast)\b",
                curr_txt,
                re.IGNORECASE
            ))
            max_cont_gap = 3500 if (prev_ends_incomplete or curr_starts_lower) else 2000
            if gap_ms < max_cont_gap:
                is_sentence_continuation = prev_ends_incomplete or curr_starts_lower or (not prev_has_terminal_punct and curr_starts_continuation_word)

        if (is_full or is_dense or is_scene_break) and not is_sentence_continuation:
            batches.append(current_batch)
            current_batch = []
            current_words = 0

        current_batch.append(item)
        current_words += max(1, words)

    if current_batch:
        # Trailing Batch Coalescence & Rebalancing:
        # Prevent costly micro-batches (< 8 lines) at the tail of the episode.
        if coalesce_tail and batches and len(current_batch) < 8:
            total_tail = len(batches[-1]) + len(current_batch)
            if total_tail <= max_batch_size:
                # 1. Coalescence: merge cleanly into preceding batch, saving an entire API round-trip
                batches[-1].extend(current_batch)
            else:
                # 2. Rebalance: distribute items evenly between batches[-1] and current_batch
                combined = batches[-1] + current_batch
                split_idx = len(combined) // 2
                batches[-1] = combined[:split_idx]
                batches.append(combined[split_idx:])
        else:
            batches.append(current_batch)

    return batches

class CharacterInfo(BaseModel):
    model_config = ConfigDict(extra="ignore")
    name: str = Field(description="Kanoniczne miano lub określenie postaci")
    gender: str = Field(description="Płeć postaci: 'mężczyzna', 'kobieta' lub 'inna'")
    role: Optional[str] = Field(default=None, description="Krótki opis roli lub relacji fabularnej")

class LineTranslation(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: int = Field(description="ID kwestii dialogowej z wejścia")
    polish_text: str = Field(description="Przetłumaczona kwestia na język polski z uwzględnieniem płci, sceny i eliminacji kalek")
    speaker_name: Optional[str] = Field(default=None, description="Miano postaci z bazy wiedzy / kartoteki mówiącej tę kwestię lub null jeśli nieznana")
    speaker_gender: Optional[str] = Field(default=None, description="Płeć mówcy: 'mężczyzna' lub 'kobieta'")
    speaker_grammatical_gender: Optional[str] = Field(
        default=None,
        description=(
            "Płeć gramatyczna wypowiedzi w 1. osobie: 'MASCULINE', 'FEMININE' lub 'NEUTRAL' (dla form bezosobowych). "
            "Określa zgodność morfologiczną orzeczeń 1. osoby w języku polskim. "
            "W przypadku ról chłopięcych/męskich granych przez żeńskie seiyū (cross-gender casting) "
            "wskazana jest wartość 'MASCULINE'."
        )
    )
    addressee: Optional[str] = Field(
        default=None,
        description=(
            "Odbiorca kwestii w scenie: "
            "'kobieta', 'mężczyzna', 'grupa_kobiet' (niemęskoosobowa), "
            "'grupa_mężczyzn' (męskoosobowa), 'grupa_mieszana' (męskoosobowa) "
            "lub 'brak' (monolog wewnętrzny/myśl)."
        )
    )
    target_gender: Optional[str] = Field(
        default=None,
        description="Płeć adresata/odbiorcy kwestii: 'MASCULINE', 'FEMININE' lub null."
    )
    addressee_number: Optional[str] = Field(
        default=None,
        description="Liczba gramatyczna adresata: 'SINGULAR' (l. pojedyncza 'ty') lub 'PLURAL' (l. mnoga 'wy')."
    )
    semiotic_layer: Optional[str] = Field(default="spoken_on_screen", description="Warstwa semiotyczna: 'spoken_on_screen' (mowa w kadrze), 'spoken_off_screen' (komentarz zza kadru), 'manga_balloon' (dymek/halucynacja), 'inner_thought' (myśli), 'diegetic_sign' (plansza/napis)")
    screen_region: Optional[str] = Field(default=None, description="Dla planszy/tytułu/napisu ekranowego: wskaż wykryte na kadrze położenie japońskiego napisu: 'bottom_right' (prawy dolny róg), 'bottom_left' (lewy dolny róg), 'top_right' (prawy górny róg), 'top_left' (lewy górny róg), 'bottom_center' (dół), 'top_center' (góra), 'center' (środek) lub null dla zwykłych dialogów.")
    visual_typesetting: Optional[VisualTypesettingData] = Field(default=None, description="Dla planszy/tytułu/napisu ekranowego/onomatopei: precyzyjne współrzędne 2D [ymin, xmin, ymax, xmax] w skali 0-1000, umiejscowienie 'above'/'below', kąt obrotu rotation_deg (-45 do 45) oraz kolory HEX lub null dla zwykłej mowy.")
    visual_subtext: Optional[str] = Field(default=None, description="Maks. 10-12 słów w formacie 'Stan: Emocja + Akcja fizyczna'. Podawaj TYLKO gdy mimika/gest przeczy słowom lub wnosi ukryty podtekst niewidoczny w tekście (asymetria obrazu i tekstu), w przeciwnym razie null.")
    literal_meaning: Optional[str] = Field(default=None, description="Dosłowny idiom JP (maks. 5 słów) tylko w razie potrzeby, inaczej null")
    notes: Optional[str] = Field(default=None, description="Kluczowa notatka (maks. 5 słów) tylko w razie potrzeby, inaczej null")
    ambiguity_note: Optional[str] = Field(default=None, description="W razie niejednoznaczności referencyjnej lub leksykalnej: krótka flaga dla Fazy 2 (maks. 6 słów), inaczej null")


class BatchTranslationResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    scene_diagnosis: Optional[SceneDiagnosis] = Field(default=None, description="Syntetyczna diagnoza sytuacji i podtekstu sceny PRZED tłumaczeniem (1-2 zwięzłe zdania)")
    translations: List[LineTranslation] = Field(description="Lista przetłumaczonych kwestii")
    characters_identified: Optional[List[CharacterInfo]] = Field(default=None, description="Zidentyfikowane lub nowo odkryte postacie i ich płeć")

from series_memory import CANONICAL_MALE_NAMES_ON_A

def detect_third_person_mentions(
    clean_text: str,
    speaker: Optional[str],
    character_registry: Optional[Dict[str, str]] = None,
    series_bible: Optional[Any] = None
) -> List[str]:
    """
    Scans clean dialogue text for 3rd-person character mentions.
    Injects strict gender and past-tense agreement directives (Filar CLXII)
    when a character (especially male with a name ending in '-a') is discussed
    by another speaker, preventing gender drift across points of view.
    """
    if not clean_text:
        return []

    speaker_clean = (speaker or "").strip()
    speaker_lower = speaker_clean.lower()
    directives = []
    seen_names = set()

    # Aggregate candidate characters and their confirmed genders
    candidates: Dict[str, str] = {}  # name -> "MALE" or "FEMALE"

    # 1. From Character Registry
    if character_registry:
        for full_name, details in list(character_registry.items()):
            if not full_name:
                continue
            desc_lower = str(details).lower()
            gen = None
            if any(k in desc_lower for k in FEMALE_ROLE_KEYWORDS):
                gen = "FEMALE"
            elif any(k in desc_lower for k in MALE_ROLE_KEYWORDS):
                gen = "MALE"
            
            # Split multi-name slashes like "<Postac_A> / <Postac_B>"
            parts = [p.strip() for p in re.split(r"[/,]", full_name) if p.strip()]
            for p in parts:
                if len(p) >= 3 and gen:
                    candidates[p] = gen

    # 2. From Series Bible characters
    if series_bible and hasattr(series_bible, "data"):
        bible_chars = series_bible.get_characters_snapshot() if hasattr(series_bible, "get_characters_snapshot") else dict(series_bible.data.get("characters", {}))
        for c_key, c_val in list(bible_chars.items()):
            desc_str = c_val.get("description", "") if isinstance(c_val, dict) else str(c_val)
            desc_lower = desc_str.lower()
            gen = None
            if any(k in desc_lower for k in FEMALE_ROLE_KEYWORDS):
                gen = "FEMALE"
            elif any(k in desc_lower for k in MALE_ROLE_KEYWORDS):
                gen = "MALE"
            
            # c_key might be "<Postac_A> -> <Postac_B>" or "<Postac_B>"
            names = re.findall(r"\b[A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]{2,}\b", c_key)
            for n in names:
                if n not in candidates:
                    if gen:
                        candidates[n] = gen
                    elif n.lower() in CANONICAL_MALE_NAMES_ON_A:
                        candidates[n] = "MALE"

    # 3. Canonical Male Names on '-a' (Filar CLXII)
    for c_name in CANONICAL_MALE_NAMES_ON_A:
        cap_name = c_name.capitalize()
        if cap_name not in candidates:
            candidates[cap_name] = "MALE"

    # Scan clean_text for candidates
    for name, gender in candidates.items():
        name_lower = name.lower()
        # Skip if character is the speaker
        if speaker_lower and (name_lower == speaker_lower or name_lower in speaker_lower or speaker_lower in name_lower):
            continue
        if name_lower in seen_names:
            continue

        # Match name as a whole word in English text (or possessive <Postac>'s)
        if re.search(rf"\b{re.escape(name)}(?:'s)?\b", clean_text, re.IGNORECASE):
            seen_names.add(name_lower)
            if gender == "MALE":
                directives.append(
                    f"[PODMIOT 3. OSOBY: '{name}' to MĘŻCZYZNA -> WYMAGANE orzeczenia męskie w czasie przeszłym: '{name} ostrzegał/mówił/był' (Filar CLXII)]"
                )
            elif gender == "FEMALE":
                directives.append(
                    f"[PODMIOT 3. OSOBY: '{name}' to KOBIETA -> WYMAGANE orzeczenia żeńskie w czasie przeszłym: '{name} ostrzegała/mówiła/była']"
                )

    return directives

def detect_scene_social_context(
    batch_events: List[Tuple[int, pysubs2.SSAEvent, str, str]],
    history_context: Optional[List[Dict[str, Any]]] = None,
    lookahead_events: Optional[List[Tuple[int, pysubs2.SSAEvent, str, str]]] = None,
    character_registry: Optional[Dict[str, str]] = None,
    series_bible: Optional[Any] = None
) -> Optional[str]:
    """
    Dynamic Crowd vs 1-on-1 (Uchi-Soto & Crowd Density Tracker).
    Analyzes active speakers and characters across sliding dialogue window (+-6 lines / 15s).
    - If exactly 2 distinct characters in private conversation: tags 1-on-1 mode (direct 'ty' required).
    - If 3+ characters or higher status figure (chan, ruler, sensei, general) present:
      tags group / Uchi-Soto distancing and etiquette protocol.
    """
    if not batch_events:
        return None

    active_speakers: List[str] = []

    # 1. From history context
    if history_context:
        for h in history_context[-4:]:
            spk = (h.get("speaker") or h.get("speaker_name") or "").strip()
            if spk and spk not in active_speakers:
                active_speakers.append(spk)

    # 2. From current batch
    for item in batch_events:
        ev = item[1] if len(item) > 1 else None
        if ev and getattr(ev, "name", None):
            spk = ev.name.strip()
            if spk and spk not in active_speakers:
                active_speakers.append(spk)

    # 3. From lookahead preview
    if lookahead_events:
        for item in lookahead_events[:4]:
            fut_ev = item[1] if len(item) > 1 else None
            if fut_ev and getattr(fut_ev, "name", None):
                spk = fut_ev.name.strip()
                if spk and spk not in active_speakers:
                    active_speakers.append(spk)

    NON_CHAR_LABELS = {"sign", "title", "caption", "typeset", "op", "ed", "all", "wszyscy", "tłum", "crowd", "napis", "szyld", "narrator", "voice"}
    clean_speakers = [s for s in active_speakers if s.lower() not in NON_CHAR_LABELS and not any(k in s.lower() for k in ["sign", "title", "napis", "ts"])]

    HIGH_STATUS_KEYWORDS = [
        "władca", "chan", "arystokrat", "król", "książę", "księżniczk", "generał",
        "dowódca", "nauczyciel", "sensei", "mistrz", "szef", "lord", "lady", "tsar",
        "tsarina", "cesarz", "cesarzowa", "chana", "chanem", "kapłan", "kanclerz", "dyrektor"
    ]

    high_status_found: Optional[str] = None
    all_known_chars: Dict[str, str] = {}
    if character_registry:
        all_known_chars.update(dict(character_registry))
    if series_bible and hasattr(series_bible, "data") and "characters" in series_bible.data:
        bible_chars = series_bible.get_characters_snapshot() if hasattr(series_bible, "get_characters_snapshot") else dict(series_bible.data.get("characters", {}))
        for k, v in list(bible_chars.items()):
            desc = v.get("description", "") if isinstance(v, dict) else str(v)
            if k not in all_known_chars:
                all_known_chars[k] = desc

    for spk in clean_speakers:
        for cname, cdesc in list(all_known_chars.items()):
            if cname.lower() in spk.lower() or spk.lower() in cname.lower():
                cd_lower = str(cdesc).lower()
                if any(k in cd_lower for k in HIGH_STATUS_KEYWORDS):
                    high_status_found = f"{spk} ({cdesc})"
                    break
        if high_status_found:
            break

    if high_status_found:
        return f"[KADR ZBIOROWY / UCHI-SOTO: W scenie obecna jest postać wyższa rangą ({high_status_found}) -> Wymóg oficjalnego dystansu i protokołu dworskiego/szkolnego]"

    if len(clean_speakers) == 2:
        return f"[KADR 1-NA-1: Rozmowa w cztery oczy ({clean_speakers[0]} i {clean_speakers[1]}) -> Standardowy wymóg bezpośredniego 'ty' i 2. os. lp.]"

    if len(clean_speakers) >= 3:
        speakers_str = ", ".join(clean_speakers[:4])
        return f"[KADR ZBIOROWY / UCHI-SOTO: Scena wieloosobowa ({speakers_str}) -> Wymóg zachowania odpowiedniego dystansu społecznego i protokołu relacji (Uchi-Soto)]"

def calculate_syntactic_calque_score(en_text: str, pl_text: str) -> float:
    """
    Calculates a syntactic and phraseological calque score [0.0 - 1.0] between source EN and candidate PL.
    Measures:
    1. Direct literal fansub clichés (e.g., 'i mean' -> 'mam na myśli', 'it's not like' -> 'to nie tak, że',
       'here' -> 'tutaj', 'you know' -> 'wiesz', 'can't be helped' -> 'nie da się nic / nic się nie poradzi',
       'are you saying' -> 'mówisz, że / chcesz powiedzieć', 'what is it' -> 'co to jest', 'all right' -> 'w porządku',
       'by any chance' -> 'przypadkiem', 'no way' -> 'nie ma mowy').
    2. Structural and word count isomorphism (ratio ~ 1.0) indicating word-for-word copy.
    Returns float score between 0.0 and 1.0. A score >= 0.65 triggers blind-draft masking.
    """
    if not en_text or not pl_text:
        return 0.0

    en_clean = clean_text_for_len(en_text).lower().strip()
    pl_clean = clean_text_for_len(pl_text).lower().strip()

    if not en_clean or not pl_clean:
        return 0.0

    score = 0.0

    # 1. Known Fansub Cliché Calque Pairs (strong signal)
    CLICHE_CALQUE_PAIRS = [
        (r"\bi mean\b", r"\bmam na myśli\b"),
        (r"\bit'?s not like\b", r"\bto nie tak,\s*że\b|\bto nie tak że\b"),
        (r"\bcan'?t be helped\b", r"\bnic się nie (poradzi|da)\b|\bnie da się nic\b|\bnie da się temu zaradzić\b"),
        (r"^(here\b|here,\b|here!\b)", r"^(tutaj\b|tutaj,\b|tutaj!\b)"),
        (r"\byou know\b", r"\bwiesz\b"),
        (r"\bare you saying\b", r"\bmówisz,\s*że\b|\bchcesz powiedzieć,\s*że\b|\bmówisz że\b"),
        (r"\bwhat is it\b", r"\bco to jest\b"),
        (r"\bwhat'?s wrong\b", r"\bco jest nie tak\b"),
        (r"\bdon'?t tell me\b", r"\btylko mi nie mów\b|\bnie mów mi,\s*że\b"),
        (r"\bnot at all\b", r"\bani trochę\b|\bcałkowicie nie\b"),
        (r"\bby any chance\b", r"\bprzypadkiem\b|\bczy przypadkiem\b"),
        (r"\bin other words\b", r"\binnymi słowy\b"),
        (r"\bto be honest\b", r"\bszczerze mówiąc\b"),
        (r"\bno way\b", r"\bnie ma mowy\b"),
        (r"^(sure\b|sure,\b)", r"^(jasne\b|jasne,\b)"),
        (r"\bfrom now on\b", r"\bod teraz\b"),
        (r"\bwhat should (i|we) do\b", r"\bco (mam|mamy) zrobić\b"),
    ]

    cliche_matches = 0
    for en_pat, pl_pat in CLICHE_CALQUE_PAIRS:
        if re.search(en_pat, en_clean) and re.search(pl_pat, pl_clean):
            cliche_matches += 1

    if cliche_matches >= 1:
        score += 0.45 * min(2, cliche_matches)

    # 2. Structural & Word Count Isomorphism
    en_words = re.findall(r"\b[a-zA-Z0-9']+\b", en_clean)
    pl_words = re.findall(r"\b[a-zA-Z0-9ąćęłńóśźżĄĆĘŁŃÓŚŹŻ']+\b", pl_clean)

    if len(en_words) >= 3 and len(pl_words) >= 3:
        len_ratio = min(len(en_words), len(pl_words)) / max(len(en_words), len(pl_words))
        if len_ratio >= 0.85:
            score += 0.20
        elif len_ratio >= 0.70:
            score += 0.10

    # 3. Punctuation Mirroring (identical terminal punctuation and mid-sentence commas)
    if en_clean.endswith("?") and pl_clean.endswith("?"):
        score += 0.05
    elif en_clean.endswith("!") and pl_clean.endswith("!"):
        score += 0.05
    elif en_clean.endswith("...") and pl_clean.endswith("..."):
        score += 0.05

    # 4. Starting Token Calque Mirror (starter matching)
    STARTERS = [("wait", "czekaj"), ("listen", "słuchaj"), ("look", "spójrz"), ("see", "widzisz"), ("hey", "hej")]
    for en_st, pl_st in STARTERS:
        if en_clean.startswith(en_st) and pl_clean.startswith(pl_st):
            score += 0.15
            break

    return min(1.0, round(score, 2))


def determine_blind_draft_status(
    has_audio_conflict: bool = False,
    has_ambiguity_conflict: bool = False,
    has_severe_trap: bool = False,
    has_temporal_conflict: bool = False,
    calque_score: float = 0.0,
    en_text: str = "",
    pl_text: str = ""
) -> bool:
    """
    Determines whether a line in Phase 1 draft should be marked as blind draft
    (requiring autonomous translation from Japanese audio / scene dynamics in Phase 2
    to eliminate anchoring bias).
    Guarantees 100% resilient evaluation with default arguments.
    """
    if has_audio_conflict or has_ambiguity_conflict or has_severe_trap or has_temporal_conflict:
        return True
    if calque_score >= 0.65:
        return True
    if calque_score >= 0.40 and (en_text or pl_text):
        txt = f"{en_text} {pl_text}".lower()
        if any(c in txt for c in ["co ty", "co robisz", "nie może być", "niemożliwe", "co do", "doprawdy", "what are you doing", "no way", "impossible", "what the"]):
            return True
    return False

def is_short_spoken_reply(text: str, prev_text: str = "", same_speaker_neighbor_unitalicized: bool = False) -> bool:
    """
    Sprawdza, czy linia jest krótką repliką mówioną w dialogu (<= 4 słowa lub typowe potoczne potwierdzenie/negacja/reakcja),
    która NIE powinna być oznaczana jako monolog wewnętrzny tylko ze względu na cichą prozodię (niski RMS).
    """
    if not text:
        return False
    clean_txt = re.sub(r"\{.*?\}", "", text)
    clean_txt = re.sub(r"\\[nN]|\r?\n", " ", clean_txt).strip()
    if (clean_txt.startswith("(") and clean_txt.endswith(")")) or (clean_txt.startswith("（") and clean_txt.endswith("）")):
        return False

    words = re.findall(r"\b[A-Za-z0-9ąćęłńóśźżĄĆĘŁŃÓŚŹŻ'-]+\b", clean_txt)
    word_count = len(words)

    conversational_tokens = {
        "yes", "yeah", "yep", "no", "nope", "okay", "ok", "right", "sure", "got it", "i see",
        "wait", "hey", "hello", "hi", "thanks", "thank you", "please", "sorry", "excuse me",
        "really", "what", "huh", "hm", "hmm", "ah", "oh", "eh", "good morning", "good night",
        "understood", "fine", "alright", "coming", "im back", "i'm back", "lets go", "let's go",
        "tak", "nie", "jasne", "dobrze", "zgoda", "czekaj", "hej", "cześć", "dzięki", "dziękuję",
        "proszę", "przepraszam", "naprawdę", "co", "aha", "mhm", "no", "chodźmy", "wróciłem", "wróciłam"
    }

    lower_txt = clean_txt.lower().strip(" .!?,:;-–—")
    if lower_txt in conversational_tokens:
        return True

    if word_count <= 4:
        if any(w.lower() in conversational_tokens for w in words):
            return True
        if same_speaker_neighbor_unitalicized:
            return True
        if word_count <= 2:
            return True

    if same_speaker_neighbor_unitalicized and word_count <= 5:
        return True

    return False

def format_phase1_candidate_text(pl_candidate: str, event: Any, is_sign: bool = False) -> str:
    r"""
    Formatuje tekst kandydata Fazy 1: normalizuje separatory \r\n i \n do \N
    oraz dla stylu Italics / myśli otacza pojedynczą parą {\i1}...{\i0} (Standard 9.5, 2C.6, R1.9).
    """
    if not pl_candidate:
        return ""
    cand = sanitize_sub_text(pl_candidate)
    cand = re.sub(r"\\[nN]|\r?\n", r"\\N", cand)

    st_ev_lower = str(getattr(event, "style", "")).lower()
    italic_attr = getattr(event, "italic", 0)
    has_italic_style = any(k in st_ev_lower for k in ["italic", "flashback_italic", "thoughts", "internal"]) or italic_attr in (1, -1)
    ev_en = getattr(event, "text", "") or ""
    is_internal_monologue = getattr(event, "is_internal_monologue", False) or has_italic_style

    if is_internal_monologue and not has_italic_style:
        if is_short_spoken_reply(cand, ev_en):
            is_internal_monologue = False

    if is_internal_monologue and cand and not is_sign:
        clean_im = re.sub(r"\{\\i[01]\}", "", cand).strip()
        clean_im = re.sub(r"\s*\\N\s*", r"\\N", clean_im)
        cand = f"{{\\i1}}{clean_im}{{\\i0}}"
    return cand


class MultimodalTranslator:
    _STATUS_LOCK = threading.Lock()
    _STATUS_ACTIVE: bool = False
    _LAST_STATUS_TIME: float = 0.0

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gemini-3.5-flash-lite",
        model_phase2: Optional[str] = None,
        batch_size: int = 24,
        enable_verifier: bool = True,
        max_image_width: int = 540,
        keep_honorifics: bool = True,
        use_whisper: bool = True,
        whisper_model_size: str = "kotoba-tech/kotoba-whisper-v2.0-faster",
        thinking_budget_phase2: Optional[int] = None,
        trace_log: bool = True,
        trace_dir: Optional[Union[str, Path]] = "logs"
    ):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError(
                "Nie znaleziono klucza API Gemini! Ustaw zmienną środowiskową GEMINI_API_KEY "
                "lub utwórz plik .env z wpisem GEMINI_API_KEY=twój_klucz"
            )
        
        timeout_sec = float(os.getenv("GEMINI_HTTP_TIMEOUT_SEC", "90.0"))
        from client_factory import get_genai_client, MultiKeyClientPool
        self.client_pool = MultiKeyClientPool(raw_keys=self.api_key, timeout_sec=timeout_sec)
        self.client = self.client_pool.get_client()
        self.model = model
        self.model_phase1 = model
        self.model_phase2 = model_phase2 or model
        self.batch_size = batch_size
        self.enable_verifier = enable_verifier
        self.max_image_width = max_image_width
        self.keep_honorifics = keep_honorifics
        self.phase1_thinking_budget = 0  # Phase 1 is guaranteed to run with CoT=0 for rapid triangulation
        self.thinking_budget_phase2 = thinking_budget_phase2
        self.trace_log = trace_log
        self.trace_dir = trace_dir
        self.flight_recorder: Optional[EpisodeFlightRecorder] = None
        self.system_prompt = get_translation_system_prompt(keep_honorifics=keep_honorifics, lean=True)
        self.linter = AVTLinter
        
        # Episode Profiler (Pre-pass Glossary & Character Matrix)
        self.profiler = EpisodeProfiler(client=self.client_pool or self.client, model=self.model_phase1)
        
        # Optional local Japanese Whisper engine (Speech-to-Text)
        self.whisper = None
        if use_whisper and JapaneseWhisperEngine.is_available():
            try:
                self.whisper = JapaneseWhisperEngine(model_size=whisper_model_size)
            except Exception:
                self.whisper = None
        
        # Phase 2 - Script Doctor / Editorial Verifier
        if self.enable_verifier:
            self.verifier = DialogueVerifier(
                client=self.client_pool or self.client,
                model=self.model_phase2,
                keep_honorifics=keep_honorifics,
                thinking_budget=self.thinking_budget_phase2
            )
        
        # In-episode character memory (Character Registry)
        self.character_registry: Dict[str, str] = {}
        self.combined_glossary: Dict[str, str] = {}
        self.series_bible = None
        
        # Translation Memory from subtitle corpus
        try:
            self.tm = TranslationMemory()
            # Check if index needs building
            baza_dir = Path(__file__).parent / "baza napisów"
            if baza_dir.exists():
                with sqlite3.connect(self.tm.db_path) as conn:
                    cnt = conn.execute("SELECT COUNT(*) FROM translation_pairs").fetchone()[0]
                if cnt == 0:
                    self.tm.index_database_directory(baza_dir)
        except Exception:
            self.tm = None

        # Official Polish Manga Canon Registry (Waneko, JPF, Studio JG etc.)
        self.manga_canon = MangaCanonRegistry()

        # User Feedback Database (Few-Shot Golden Examples) & Deterministic Glossary
        self.user_feedback = UserFeedbackManager()
        self.glossary_manager = GlossaryManager()

        # Real token counter for the current episode
        self.current_episode_tokens: Dict[str, Any] = {"prompt": 0, "cached": 0, "output": 0, "model": self.model}
        import threading
        self._thread_local = threading.local()
        self._thread_local.last_batch_token_usage = {}
        self.lock = threading.RLock()
        # Smart Batch Queueing & Pacing:
        # Default to 1-by-1 streaming pacing mode (eliminates TPU congestion and provides live instant updates)
        default_concurrency = 1
        self.concurrent_batches = int(os.getenv("CONCURRENT_BATCHES", str(default_concurrency)))

    FEMALE_ROLE_KEYWORDS = FEMALE_ROLE_KEYWORDS
    MALE_ROLE_KEYWORDS = MALE_ROLE_KEYWORDS
    BOY_ROLE_KEYWORDS = BOY_ROLE_KEYWORDS
    lock = threading.RLock()
    _thread_local = threading.local()

    def get_character_registry_snapshot(self) -> Dict[str, str]:
        """Returns a thread-safe atomic snapshot copy of character_registry."""
        lock = getattr(self, "lock", None)
        ctx = lock if lock is not None else contextlib.nullcontext()
        with ctx:
            reg = getattr(self, "character_registry", None)
            return dict(reg) if reg else {}

    def _register_character_safe(self, name: str, gender: str, role: str = "") -> None:
        """
        Safely registers or updates a character in self.character_registry with
        symmetrical immutable protection (cannot downgrade/overwrite confirmed FEMALE with MALE
        or confirmed MALE with FEMALE). Thread-safe.
        """
        if not name:
            return
        clean_name = name.strip()
        new_desc = f"{gender} ({role or 'postać'})".strip()
        new_lower = new_desc.lower()

        lock = getattr(self, "lock", None)
        ctx = lock if lock is not None else contextlib.nullcontext()
        with ctx:
            if not hasattr(self, "character_registry") or self.character_registry is None:
                self.character_registry = {}
            if clean_name in self.character_registry:
                existing_desc = self.character_registry[clean_name]
                existing_lower = existing_desc.lower()

                is_heuristic_existing = "(wyodrębniono z relacji" in existing_lower or "wyodrębniono z relacji" in existing_lower
                if not is_heuristic_existing:
                    has_confirmed_female = any(w in existing_lower for w in self.FEMALE_ROLE_KEYWORDS)
                    is_incoming_male = any(w in new_lower for w in self.MALE_ROLE_KEYWORDS)
                    if has_confirmed_female and is_incoming_male:
                        # Symmetrical lock: reject male overwrite for confirmed female
                        return

                    has_confirmed_male = any(w in existing_lower for w in self.MALE_ROLE_KEYWORDS)
                    is_incoming_female = any(w in new_lower for w in self.FEMALE_ROLE_KEYWORDS)
                    if has_confirmed_male and is_incoming_female:
                        # Symmetrical lock: reject female overwrite for confirmed male
                        return

            self.character_registry[clean_name] = new_desc

    def _precompute_episode_scene_genders(
        self,
        events: List[Any],
        whisper_transcriptions: Optional[Dict[int, str]] = None,
        episode_profile: Optional[Any] = None
    ) -> Dict[int, str]:
        """
        Pre-computes scene cast genders across the entire episode timeline (0.00 PLN).
        1. Maps dramatic_sequences from episode_profile (female_only_scene / male_only_scene)
           across their time_range to event indices.
        2. Splits dialogue events into continuous scenes (gap < 10000ms, max span 180s).
        3. Uses SeriesBible.infer_scene_cast_from_text on the combined scene dialogue
           and audio transcriptions to assign a scene-level gender ('FEMALE' -> 'kobieta',
           'MALE' -> 'mężczyzna') to every event index in that scene.
        """
        if not events:
            return {}

        norm_entries = []
        for i, item in enumerate(events):
            if isinstance(item, tuple) and len(item) >= 2:
                orig_idx = item[0]
                ev = item[1]
            else:
                orig_idx = i
                ev = item
            norm_entries.append((orig_idx, ev))

        scene_genders: Dict[int, str] = {}
        if not hasattr(self, "episode_scene_polylogues") or self.episode_scene_polylogues is None:
            self.episode_scene_polylogues = {}
        else:
            self.episode_scene_polylogues.clear()

        # 1. Parse dramatic_sequences from EpisodeProfile (Pre-pass Profilera z arbitrażem P0, 2B.9)
        if episode_profile and getattr(episode_profile, "dramatic_sequences", None):
            from profiler import EpisodeProfiler
            episode_profile.dramatic_sequences = EpisodeProfiler.reconcile_prepass_with_p0(
                episode_profile.dramatic_sequences,
                series_bible=getattr(self, "series_bible", None)
            )
            def _parse_time_range_to_ms(tr_str: str) -> Optional[Tuple[int, int]]:
                if not tr_str or ("-" not in tr_str and "–" not in tr_str):
                    return None
                parts = re.split(r"[-–]", tr_str)
                if len(parts) != 2:
                    return None
                def _to_ms(t_part: str) -> Optional[int]:
                    subparts = t_part.strip().split(":")
                    try:
                        if len(subparts) == 2:
                            return int(float(subparts[0])) * 60000 + int(float(subparts[1])) * 1000
                        elif len(subparts) == 3:
                            return int(float(subparts[0])) * 3600000 + int(float(subparts[1])) * 60000 + int(float(subparts[2])) * 1000
                    except Exception:
                        return None
                    return None
                s_ms = _to_ms(parts[0])
                e_ms = _to_ms(parts[1])
                if s_ms is not None and e_ms is not None and e_ms >= s_ms:
                    return s_ms, e_ms
                return None

            for seq in episode_profile.dramatic_sequences:
                tr_str = getattr(seq, "time_range", "")
                ms_range = _parse_time_range_to_ms(tr_str)
                if not ms_range:
                    continue
                seq_start_ms, seq_end_ms = ms_range

                # Populate POLYLOGUE (n=M) when len(characters_present) >= 3 or topology_type == "POLYLOGUE"
                chars_present = getattr(seq, "characters_present", []) or []
                topo_type = getattr(seq, "topology_type", "")
                if len(chars_present) >= 3 or topo_type == "POLYLOGUE":
                    n_count = len(chars_present) if len(chars_present) >= 3 else 3
                    poly_str = f"POLYLOGUE (n={n_count})"
                    for orig_idx, ev in norm_entries:
                        ev_s = getattr(ev, "start", 0)
                        ev_e = getattr(ev, "end", 0)
                        if (ev_s >= seq_start_ms and ev_s <= seq_end_ms) or (ev_e >= seq_start_ms and ev_e <= seq_end_ms):
                            self.episode_scene_polylogues[orig_idx] = poly_str

                is_fem = getattr(seq, "female_only_scene", False)
                is_male = getattr(seq, "male_only_scene", False)
                if not (is_fem or is_male):
                    continue
                target_g = "kobieta" if is_fem else "mężczyzna"
                for orig_idx, ev in norm_entries:
                    ev_s = getattr(ev, "start", 0)
                    ev_e = getattr(ev, "end", 0)
                    if (ev_s >= seq_start_ms and ev_s <= seq_end_ms) or (ev_e >= seq_start_ms and ev_e <= seq_end_ms):
                        scene_genders[orig_idx] = target_g

            # Weryfikacja płci aktora po dramatic_sequences (Standard 9.8, 2C.1):
            # Pojedyncza kwestia wypowiadana przez mężczyznę nigdy nie ma scene_gender == "kobieta"
            from series_memory import resolve_actor_gender
            for orig_idx, ev in norm_entries:
                act_name = getattr(ev, "name", "")
                if act_name:
                    act_gender = resolve_actor_gender(act_name, self.character_registry, getattr(self, "series_bible", None))
                    if act_gender == "MALE":
                        scene_genders[orig_idx] = "mężczyzna"
                    elif act_gender == "FEMALE":
                        scene_genders[orig_idx] = "kobieta"

        # 2. Continuous scenes clustering & SeriesBible inference
        if getattr(self, "series_bible", None):
            scenes: List[List[Tuple[int, Any]]] = []
            curr_scene: List[Tuple[int, Any]] = []

            for orig_idx, ev in norm_entries:
                text = getattr(ev, "text", "")
                if is_song_line(ev, text):
                    continue
                if not curr_scene:
                    curr_scene.append((orig_idx, ev))
                    continue

                last_orig_idx, last_ev = curr_scene[-1]
                gap = ev.start - last_ev.end
                span = ev.end - curr_scene[0][1].start

                if gap > 10000 or span > 180000:
                    scenes.append(curr_scene)
                    curr_scene = [(orig_idx, ev)]
                else:
                    curr_scene.append((orig_idx, ev))

            if curr_scene:
                scenes.append(curr_scene)

            for sc in scenes:
                scene_indices = [idx for idx, _ in sc]
                scene_texts = [getattr(ev, "text", "") for _, ev in sc if getattr(ev, "text", "")]
                scene_whisper = [whisper_transcriptions.get(idx, "") for idx in scene_indices if whisper_transcriptions and idx in whisper_transcriptions]

                sc_gender = None
                if hasattr(self.series_bible, "infer_scene_cast_from_text"):
                    _, sc_gender = self.series_bible.infer_scene_cast_from_text(scene_texts, whisper_texts=scene_whisper)

                if not sc_gender:
                    fem_count = 0
                    male_count = 0
                    for _, ev in sc:
                        raw_act = getattr(ev, "name", "")
                        clean_act = re.sub(r"\s*\([^)]*\)", "", str(raw_act or "")).strip()
                        if clean_act and not is_generic_actor_or_category(clean_act):
                            char_rec = self.series_bible.get_character(clean_act)
                            if isinstance(char_rec, dict):
                                g_act = str(char_rec.get("gender") or "").upper()
                                if g_act == "FEMALE":
                                    fem_count += 1
                                elif g_act == "MALE":
                                    male_count += 1
                    if fem_count > 0 and male_count == 0:
                        sc_gender = "FEMALE"
                    elif male_count > 0 and fem_count == 0:
                        sc_gender = "MALE"

                if sc_gender == "FEMALE":
                    for idx in scene_indices:
                        scene_genders[idx] = "kobieta"
                elif sc_gender == "MALE":
                    for idx in scene_indices:
                        scene_genders[idx] = "mężczyzna"

            # Per-line fallback for explicit characters with verified P0/P1 gender (Standard 9.6/9.8, 2C.1)
            for orig_idx, ev in norm_entries:
                raw_act = getattr(ev, "name", "")
                clean_act = re.sub(r"\s*\([^)]*\)", "", str(raw_act or "")).strip()
                if clean_act and not is_generic_actor_or_category(clean_act):
                    char_rec = self.series_bible.get_character(clean_act) if getattr(self, "series_bible", None) else None
                    g_act = None
                    if isinstance(char_rec, dict):
                        g_act = str(char_rec.get("gender") or "").upper()
                    elif hasattr(self, "character_registry") and self.character_registry:
                        from series_memory import resolve_actor_gender
                        g_act = resolve_actor_gender(clean_act, self.character_registry, getattr(self, "series_bible", None))
                    if g_act == "MALE":
                        scene_genders[orig_idx] = "mężczyzna"
                    elif g_act == "FEMALE":
                        scene_genders[orig_idx] = "kobieta"

        return scene_genders

    def _arbitrate_speaker_gender(
        self,
        event: pysubs2.SSAEvent,
        raw_phase1_gender: Optional[str] = None,
        batch_id: int = 0,
        speaker_tags: Optional[Dict[int, str]] = None,
        whisper_transcriptions: Optional[Dict[int, str]] = None,
        pl_candidate: str = "",
        raw_speaker_name: Optional[str] = None,
        event_idx: Optional[int] = None
    ) -> Tuple[Optional[str], List[str]]:
        """
        Multi-Signal Gender Arbitration Engine (0.00 PLN).
        Arbitrates speaker gender across independent sources using Hierarchy of Authority:
        1. Canonical Authority: self.series_bible & self.character_registry (VETO POWER)
        2. Acoustic & Linguistic Ground Truth: F0 Pitch (speaker_tags) & Japanese seiyū markers (whisper)
        3. Phase 1 Draft: raw_phase1_gender

        Returns: (resolved_gender, arbitration_alerts)
        """
        alerts = []
        canonical_gender = None
        raw_spk = (getattr(event, "name", None) or raw_speaker_name or "").strip()
        spk_clean = extract_clean_speaker_name(raw_spk) or raw_spk
        spk_lower = spk_clean.lower()
        if spk_lower in GENERIC_CATEGORY_TAGS or raw_spk.lower() in GENERIC_CATEGORY_TAGS:
            raw_spk = ""
            spk_clean = ""
            spk_lower = ""
        tokens = set(re.findall(r"\b[a-ząćęłńóśźżA-ZĄĆĘŁŃÓŚŹŻ]+\b", spk_lower)) if spk_lower else set()
        raw_tokens = set(re.findall(r"\b[a-ząćęłńóśźżA-ZĄĆĘŁŃÓŚŹŻ]+\b", raw_spk.lower())) if raw_spk else set()

        # 0. Inherent lexical gender check (inherent nouns)
        if (
            spk_lower in INHERENT_FEMALE_NOUNS
            or any(t in INHERENT_FEMALE_NOUNS for t in tokens)
            or any(t in INHERENT_FEMALE_NOUNS for t in raw_tokens)
        ):
            canonical_gender = "kobieta"
        elif (
            spk_lower in INHERENT_MALE_NOUNS
            or any(t in INHERENT_MALE_NOUNS for t in tokens)
            or any(t in INHERENT_MALE_NOUNS for t in raw_tokens)
            or spk_lower in SECONDARY_LEXICAL_MALE_NOUNS
            or any(t in SECONDARY_LEXICAL_MALE_NOUNS for t in tokens)
            or any(t in SECONDARY_LEXICAL_MALE_NOUNS for t in raw_tokens)
        ):
            canonical_gender = "mężczyzna"

        # 1. Canonical Authority Check
        if not canonical_gender and (spk_clean or raw_spk):
            for check_name in [spk_clean, raw_spk]:
                if check_name and check_name in self.character_registry:
                    desc = self.character_registry[check_name].lower()
                    if any(k in desc for k in self.FEMALE_ROLE_KEYWORDS):
                        canonical_gender = "kobieta"
                        break
                    elif any(k in desc for k in self.MALE_ROLE_KEYWORDS):
                        canonical_gender = "mężczyzna"
                        break

            if not canonical_gender and hasattr(self, "series_bible") and self.series_bible:
                if hasattr(self.series_bible, "get_character_gender"):
                    b_gen = self.series_bible.get_character_gender(spk_clean)
                    if b_gen == "FEMALE":
                        canonical_gender = "kobieta"
                    elif b_gen == "MALE":
                        canonical_gender = "mężczyzna"

                if not canonical_gender and hasattr(self.series_bible, "data"):
                    b_chars = self.series_bible.data.get("characters", {})
                    # Pass 1: exact match
                    for b_name, b_val in b_chars.items():
                        clean_b = extract_clean_speaker_name(b_name).lower()
                        if spk_lower == b_name.lower() or clean_b == spk_lower:
                            if isinstance(b_val, dict):
                                g_field = b_val.get("gender")
                                if g_field == "MALE":
                                    canonical_gender = "mężczyzna"
                                    break
                                elif g_field == "FEMALE":
                                    canonical_gender = "kobieta"
                                    break
                            b_desc = b_val.get("description", "") if isinstance(b_val, dict) else str(b_val)
                            b_lower = b_desc.lower()
                            if any(k in b_lower for k in self.FEMALE_ROLE_KEYWORDS):
                                canonical_gender = "kobieta"
                                break
                            elif any(k in b_lower for k in self.MALE_ROLE_KEYWORDS):
                                canonical_gender = "mężczyzna"
                                break

                    # Pass 2: token match if exact match not found
                    if not canonical_gender:
                        cand_gens = []
                        for b_name, b_val in b_chars.items():
                            if spk_lower in b_name.lower().split():
                                b_desc = b_val.get("description", "") if isinstance(b_val, dict) else str(b_val)
                                b_lower = b_desc.lower()
                                if any(k in b_lower for k in self.FEMALE_ROLE_KEYWORDS):
                                    cand_gens.append("kobieta")
                                elif any(k in b_lower for k in self.MALE_ROLE_KEYWORDS):
                                    cand_gens.append("mężczyzna")
                        if cand_gens and len(set(cand_gens)) == 1:
                            canonical_gender = cand_gens[0]

        if not canonical_gender:
            if is_generic_actor_or_category(spk_clean):
                spk_clean = ""
            if is_generic_actor_or_category(raw_spk):
                raw_spk = ""

        # 1b. Episode Scene Cast Pre-computation Check (Continuous Scene Ground Truth for Anonymous Lines)
        if not canonical_gender and not spk_clean:
            check_idx = event_idx if event_idx is not None else batch_id
            if hasattr(self, "episode_scene_genders") and self.episode_scene_genders:
                if check_idx in self.episode_scene_genders:
                    canonical_gender = self.episode_scene_genders[check_idx]
                elif getattr(event, "_orig_idx", None) in self.episode_scene_genders:
                    canonical_gender = self.episode_scene_genders[getattr(event, "_orig_idx")]
                if canonical_gender == "kobieta":
                    alerts.append("[TELEMETRIA: mówca_sceny=żeński]")
                elif canonical_gender == "mężczyzna":
                    alerts.append("[TELEMETRIA: mówca_sceny=męski]")

        if not canonical_gender and not spk_clean:
            cand_texts = [pl_candidate] if pl_candidate else []
            if hasattr(event, "text") and event.text:
                cand_texts.append(event.text)
            if hasattr(self, "series_bible") and self.series_bible and cand_texts and hasattr(self.series_bible, "infer_scene_cast_from_text"):
                jp_curr_text = (whisper_transcriptions.get(batch_id, "") if whisper_transcriptions else "")
                whisper_list = [jp_curr_text] if jp_curr_text else None
                _, inf_g = self.series_bible.infer_scene_cast_from_text(cand_texts, whisper_texts=whisper_list)
                if inf_g == "FEMALE":
                    canonical_gender = "kobieta"
                    alerts.append("[TELEMETRIA: baza_wiedzy_scena=żeńska]")
                elif inf_g == "MALE":
                    canonical_gender = "mężczyzna"

        # Check if speaker is explicitly a boy or young male character to prevent female pitch contamination
        is_boy_actor = False
        if spk_clean:
            is_boy_actor = bool(re.search(r"\b(kid|son|boy|young|bro|brother|chłopak|chłopiec|syn|brat|młodzieniec)\b", spk_clean, re.IGNORECASE))
            if not is_boy_actor and spk_clean in self.character_registry:
                c_desc = str(self.character_registry[spk_clean]).lower()
                is_boy_actor = any(k in c_desc for k in ["kid", "son", "boy", "young", "bro", "brother", "chłopak", "chłopiec", "syn", "brat", "młodzieniec"]) or any(k in c_desc for k in self.BOY_ROLE_KEYWORDS)
            if not is_boy_actor and hasattr(self, "series_bible") and self.series_bible and hasattr(self.series_bible, "data"):
                b_info = self.series_bible.data.get("characters", {}).get(spk_clean, {})
                b_desc = (b_info.get("description", "") if isinstance(b_info, dict) else str(b_info)).lower()
                is_boy_actor = any(k in b_desc for k in ["kid", "son", "boy", "young", "bro", "brother", "chłopak", "chłopiec", "syn", "brat", "młodzieniec"]) or any(k in b_desc for k in self.BOY_ROLE_KEYWORDS)

        # 2. Acoustic & Linguistic Ground Truth
        raw_norm = (raw_phase1_gender or "").lower()
        phase1_is_female = any(w in raw_norm for w in ["kobieta", "żeńsk", "female", "dziewczyn"])
        phase1_is_male = any(w in raw_norm for w in ["mężczyzna", "męsk", "male", "chłopak"])

        acoustic_gender = None
        if speaker_tags and batch_id in speaker_tags:
            v_tag = speaker_tags[batch_id].lower()
            if "dziecięcy" in v_tag:
                # Young boy characters frequently voiced by female seiyū - do NOT force female
                if not is_boy_actor:
                    acoustic_gender = "kobieta"
            elif "sopran" in v_tag or "wysoki tembr" in v_tag:
                if not is_boy_actor:
                    acoustic_gender = "kobieta"
            elif "alt starszej" in v_tag or "ochrypły alt" in v_tag or "alt żeński" in v_tag:
                # Raspy or mature female alto / contralto voice - ambiguous pitch, NOT male
                acoustic_gender = None
            elif "żeńsk" in v_tag and "alt" not in v_tag and "ochrypł" not in v_tag:
                hz_match = re.search(r"~(\d+)\s*hz", v_tag)
                if hz_match:
                    hz_val = int(hz_match.group(1))
                    if hz_val >= 195:
                        acoustic_gender = "kobieta" if not is_boy_actor else None
                    elif hz_val <= 135 and not phase1_is_female:
                        acoustic_gender = "mężczyzna"
                    elif 135 < hz_val <= 155:
                        acoustic_gender = None
                else:
                    acoustic_gender = "kobieta" if not is_boy_actor else None
            elif "baryton" in v_tag or "bas" in v_tag:
                acoustic_gender = "mężczyzna"
            elif "męsk" in v_tag and "alt" not in v_tag and "ochrypł" not in v_tag:
                acoustic_gender = "mężczyzna"

        if not acoustic_gender and speaker_tags and batch_id in speaker_tags:
            v_tag = speaker_tags[batch_id].lower()
            # Hotfix 11.1.3a (P2-1): dopuszczenie etykiet "niski tembr" z SpeakerVoiceClassifier
            # przy zachowaniu progu krtaniowego <= 135 Hz i ochrony deklaracji żeńskiej z Fazy 1.
            if "niski tembr" in v_tag or ("alt" not in v_tag and "ochrypł" not in v_tag and "sopran" not in v_tag):
                hz_match = re.search(r"~(\d+)\s*hz", v_tag)
                if hz_match:
                    hz_val = int(hz_match.group(1))
                    if hz_val <= 135 and not phase1_is_female:
                        acoustic_gender = "mężczyzna"

        raw_jp = whisper_transcriptions.get(batch_id, "") if whisper_transcriptions else ""
        if isinstance(raw_jp, dict):
            jp_text = str(raw_jp.get("text", "")).lower()
        else:
            jp_text = str(raw_jp).lower()
        wdd_tag = WhisperDisambiguator.disambiguate_line(
            clean_en="",
            jp_audio=jp_text,
            speaker=spk_clean,
            character_registry=self.character_registry,
            series_bible=getattr(self, "series_bible", None)
        )
        jp_female_marker = (wdd_tag.speaker_gender == "FEMALE") or any(m in jp_text for m in ["atashi", "あたし", "atai", "あtai", "kashira", "かしら", "わよ", "wayo"])
        jp_male_marker = (wdd_tag.speaker_gender == "MALE") or any(m in jp_text for m in ["ore", "俺", "boku", "僕"])

        # Persist definitive Japanese acoustic pronoun evidence to Character Registry and Series Bible
        if spk_clean and not canonical_gender and not is_generic_actor_or_category(spk_clean):
            if wdd_tag.speaker_gender == "MALE":
                self._register_character_safe(spk_clean, "mężczyzna", role="seiyū Whisper")
                if hasattr(self, "series_bible") and self.series_bible and hasattr(self.series_bible, "update_character_gender_from_audio"):
                    self.series_bible.update_character_gender_from_audio(spk_clean, "MALE")
            elif wdd_tag.speaker_gender == "FEMALE":
                if not is_boy_actor:
                    self._register_character_safe(spk_clean, "kobieta", role="seiyū Whisper")
                    if hasattr(self, "series_bible") and self.series_bible and hasattr(self.series_bible, "update_character_gender_from_audio"):
                        self.series_bible.update_character_gender_from_audio(spk_clean, "FEMALE")



        tag_text = ((speaker_tags.get(batch_id, "") or speaker_tags.get(event_idx, "")) if speaker_tags else "").lower()
        tag_is_fem = (
            ("sopran" in tag_text or "wysoki tembr" in tag_text)
            and "niski tembr" not in tag_text
            and "średni tembr" not in tag_text
        )
        has_female_audio = (acoustic_gender == "kobieta") or jp_female_marker or tag_is_fem

        # Sign isolation: signs receive ungendered default telemetry
        is_sign = (
            getattr(event, "is_sign", False)
            or (hasattr(event, "style") and str(event.style).lower() in ("sign", "signs", "napis", "napisy"))
            or is_sign_entity(spk_clean)
        )
        if is_sign:
            return None, ["[TELEMETRIA: typ=napis_ekranowy]"]

        # Telemetria dyskursu scenicznego (Standard 9.2)
        _disc_telem = SceneDiscourseGraph.arbitrate_event_telemetry(
            event=event,
            series_bible=getattr(self, "series_bible", None),
            aux_telemetry={"speaker_gender": canonical_gender}
        )
        _sanitized_whisper = EpisodeProfiler.sanitize_event_asr(
            whisper_transcriptions.get(batch_id, "") if whisper_transcriptions else "",
            is_sign=is_sign,
            style=getattr(event, "style", None)
        )

        # Check for verified P0 status
        has_verified_p0 = False
        if spk_clean in self.character_registry:
            desc_check = str(self.character_registry[spk_clean]).lower()
            if "zweryfikowan" in desc_check or "p0" in desc_check or "anilist" in desc_check:
                has_verified_p0 = True
        if hasattr(self, "series_bible") and self.series_bible and hasattr(self.series_bible, "data"):
            b_info = self.series_bible.data.get("characters", {}).get(spk_clean, {})
            if isinstance(b_info, dict) and (b_info.get("has_verified_gender") or b_info.get("priority") == "P0"):
                has_verified_p0 = True

        # Standard 9.0 Pure Positive Domain Invariant:
        # Verified P0 record from Series Bible or Character Registry is the SOLE authority.
        # Fallback to FEMININE, F0 heuristics, and ASR token guessing are completely removed.
        if canonical_gender in ("kobieta", "mężczyzna", "FEMALE", "MALE"):
            res_g = "kobieta" if canonical_gender in ("kobieta", "FEMALE") else "mężczyzna"

            # Check for boy / crossgender seiyū voice
            char_desc_lower = ""
            if spk_clean in self.character_registry:
                char_desc_lower = str(self.character_registry[spk_clean]).lower()
            elif hasattr(self, "series_bible") and self.series_bible and hasattr(self.series_bible, "data"):
                b_info = self.series_bible.data.get("characters", {}).get(spk_clean, {})
                char_desc_lower = (b_info.get("description", "") if isinstance(b_info, dict) else str(b_info)).lower()

            boy_keywords = getattr(self, "BOY_ROLE_KEYWORDS", None) or globals().get("BOY_ROLE_KEYWORDS", ["chłopiec", "chłopak", "boy", "kid", "son", "młodzieniec"])
            is_boy_or_crossgender = is_boy_actor or any(k in char_desc_lower for k in boy_keywords) or any(k in spk_lower for k in boy_keywords)

            if res_g == "mężczyzna" and is_boy_or_crossgender and has_female_audio:
                alerts.append(f"[TELEMETRIA: mówca='{spk_clean}', płeć=mężczyzna, rola_chłopięca=crossgender_seiyū]")
                return "mężczyzna", alerts

            # Acoustic Primacy Gate (Filar CLXXIV): Untrusted fansub tag contradicted by female audio or scene
            has_masc_self = bool(re.search(r"\b(gotów|pewien|świadom|byłem|miałem|widziałem|wiedziałem|zrobiłem|pomyślałem|chciałem|mogłem|poszedłem|powiedziałem|czułem|słyszałem|wróciłem|dostałem|znalazłem|oddałem|zgubiłem|uratowałem|przyszedłem)\b", pl_candidate, re.IGNORECASE))
            if res_g == "mężczyzna" and not is_boy_or_crossgender and has_female_audio and not (has_verified_p0 and has_masc_self):
                is_scene_female = False
                check_idx = event_idx if event_idx is not None else batch_id
                if hasattr(self, "episode_scene_genders") and self.episode_scene_genders:
                    if self.episode_scene_genders.get(check_idx) == "kobieta" or self.episode_scene_genders.get(getattr(event, "_orig_idx", None)) == "kobieta":
                        is_scene_female = True

                is_cont = False
                if hasattr(self, "series_bible") and self.series_bible and hasattr(self.series_bible, "audit_speaker_metadata_against_audio"):
                    aud_res, is_cont = self.series_bible.audit_speaker_metadata_against_audio(
                        spk_clean,
                        audio_gender="FEMALE" if has_female_audio else None,
                        whisper_gender="FEMALE" if jp_female_marker else None,
                        scene_gender="FEMALE" if is_scene_female else None
                    )
                    if is_cont and aud_res == "FEMALE":
                        has_female_audio = True

                if has_female_audio and (is_cont or not is_boy_or_crossgender):
                    alerts.append(f"[TELEMETRIA: mówca='{spk_clean}', płeć=kobieta, źródło=prymat_akustyczny_seiyū]")
                    return "kobieta", alerts

            if (phase1_is_male and res_g == "kobieta") or (phase1_is_female and res_g == "mężczyzna"):
                alerts.append(f"[TELEMETRIA: mówca='{spk_clean}', płeć={res_g}, źródło=weto_kanonu]")
            else:
                alerts.append(f"[TELEMETRIA: mówca='{spk_clean}', płeć={res_g}, źródło=rekord_p0]")
            has_masc_verb = bool(re.search(r"\b(byłem|miałem|widziałem|wiedziałem|zrobiłem|pomyślałem|chciałem|mogłem|poszedłem|powiedziałem|czułem|słyszałem|wróciłem|dostałem|znalazłem|oddałem|zgubiłem|uratowałem|przyszedłem|doniósłbym|wiedziałbym|mógłbym|chciałbym|miałbym|zrobiłbym|byłbym|wolałbym|musiałbym|poszedłbym|zraniłem|skrzywdziłem|zostawiłem|poczułem|zobaczyłem)\b", pl_candidate, re.IGNORECASE))
            if res_g == "kobieta" and has_masc_verb:
                alerts.append(f"[TELEMETRIA: mówca='{spk_clean}', płeć=kobieta, korekta_fleksyjna=-łam/-łabym/-łaś]")
            return res_g, alerts

        # Jeśli postać nie ma rekordu P0 w SeriesBible/registry:
        # Rozstrzygaj na podstawie japońskich znaczników dyskursywnych (Whisper) oraz akustyki F0:
        if jp_male_marker:
            if tag_is_fem or acoustic_gender == "kobieta":
                alerts.append(f"[TELEMETRIA: mówca='{spk_clean}', płeć=mężczyzna, zaimek_boku_ore=crossgender_seiyū]")
            else:
                alerts.append("[TELEMETRIA: odsłuch_f0_whisper=mężczyzna, weto_akustyczne]")
            return "mężczyzna", alerts
        if jp_female_marker:
            alerts.append("[TELEMETRIA: odsłuch_f0_whisper=kobieta, weto_akustyczne]")
            return "kobieta", alerts
        if acoustic_gender == "kobieta" and not is_boy_actor:
            if phase1_is_male and not jp_female_marker:
                alerts.append(f"[TELEMETRIA: mówca='{spk_clean}', płeć=mężczyzna, źródło=wizja_faza1, weto_krzyku_f0]")
                return "mężczyzna", alerts
            alerts.append("[TELEMETRIA: odsłuch_f0_whisper=kobieta, weto_akustyczne]")
            return "kobieta", alerts
        if acoustic_gender == "mężczyzna":
            alerts.append("[TELEMETRIA: odsłuch_f0_whisper=mężczyzna, weto_akustyczne]")
            return "mężczyzna", alerts

        # Phase 1 fallback when no acoustic contradiction
        if phase1_is_female:
            alerts.append(f"[TELEMETRIA: mówca='{spk_clean}', płeć=kobieta, źródło=faza1_draft]")
            return "kobieta", alerts
        elif phase1_is_male:
            alerts.append(f"[TELEMETRIA: mówca='{spk_clean}', płeć=mężczyzna, źródło=faza1_draft]")
            return "mężczyzna", alerts

        # Brak rekordu P0 -> brak zgadywania, zwracamy UNKNOWN (confidence=0.0)
        return "UNKNOWN", alerts

    def _resolve_line_addressee(
        self,
        event: pysubs2.SSAEvent,
        raw_phase1_addressee: Optional[str],
        batch_events: List[Tuple[int, pysubs2.SSAEvent, str, str]],
        event_idx: int,
        whisper_text: str = "",
        clean_text: str = "",
        orig_idx: Optional[int] = None,
        lookback_history: Optional[List[Dict[str, Any]]] = None,
        speaker_tags: Optional[Dict[int, str]] = None,
        prosody_tags: Optional[Dict[int, str]] = None
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Multimodal Addressee & Number Resolution Engine (0.00 PLN).
        Resolves addressee category and label based on:
        1. Phase 1 frame analysis (raw_phase1_addressee: 'grupa_kobiet', 'grupa_mężczyzn', 'grupa_mieszana', 'kobieta', 'mężczyzna')
        2. Whisper JP pluralis markers (-tachi, -ra, minna, shokun, zen'in, mina-sama)
        3. Intra-scene dialogue alternation (1-on-1 turn between known speakers)
        4. Textual vocative analysis (first-name callout in line text)

        Returns: (addressee_category, addressee_label)
        - addressee_category: "grupa_kobiet" | "grupa_mężczyzn" | "grupa_mieszana" | "kobieta" | "mężczyzna" | "brak" | None
        - addressee_label: zwięzła etykieta tożsamości lub liczby gramatycznej adresata
        """
        if isinstance(whisper_text, dict):
            whisper_text = str(whisper_text.get("text", ""))
        else:
            whisper_text = str(whisper_text or "")
        raw_norm = (raw_phase1_addressee or "").strip().lower()
        clean_lower = clean_text.lower()
        jp_lower = whisper_text.lower()
        wdd_tag = WhisperDisambiguator.disambiguate_line(clean_en=clean_text, jp_audio=whisper_text)
        has_jp_plural = (wdd_tag.addressee_number == "PLURAL") or any(m in jp_lower for m in [
            "tachi", "たち", "達", "omae-ra", "お前ら", "kisama-ra", "貴様ら", "minna", "みんな", "皆",
            "shokun", "諸君", "zen'in", "全員", "mina-sama", "皆様", "domo", "ども", "共"
        ])

        # Strict collective vocative check: requires a direct group vocative or explicit group address syntax.
        # Excludes 3rd-person statements ("everyone is/was/has", "with everyone") and direct object idioms ("tell you all", "that's all").
        has_collective_vocative = bool(re.search(
            r"^(?:everyone|everybody|guys|team|class|all of you|ladies and gentlemen|people)[,!\?]|"
            r"\b(?:attention everyone|listen up,?\s*(?:everyone|guys|team|all of you)?)\b|"
            r"\b(?:to all of you|for all of you)\b",
            clean_lower
        ))
        is_universal_crowd_vocative = bool(re.search(
            r"^(?:everyone|everybody|class|people|all of you|ladies and gentlemen)[,!\?]|"
            r"\b(?:attention everyone|listen up,?\s*(?:everyone|all of you)?)\b",
            clean_lower
        ))
        has_plural_evidence = (has_jp_plural or has_collective_vocative) and (wdd_tag.addressee_number != "SINGULAR" or is_universal_crowd_vocative)

        # 0a. Strict Dual Addressee Check (Dual Audio Ground Truth & Both/Two Vocative Gate)
        is_dual_address = (wdd_tag.addressee_number == "DUAL") or bool(re.search(
            r"\b(?:both\s+of\s+you|you\s+two|two\s+of\s+you|the\s+two\s+of\s+you)\b", clean_lower
        ))
        if is_dual_address:
            curr_spk_str = (getattr(event, "name", None) or getattr(event, "actor", None) or "").strip().lower()
            other_chars = []
            if batch_events:
                for b_item in batch_events:
                    b_ev = b_item[1] if len(b_item) > 1 else None
                    if b_ev:
                        b_spk = (getattr(b_ev, "name", None) or getattr(b_ev, "actor", None) or "").strip()
                        if b_spk and b_spk.lower() != curr_spk_str and b_spk not in other_chars:
                            other_chars.append(b_spk)
            for cname in (list(self.character_registry.keys()) if hasattr(self, "character_registry") and self.character_registry else []):
                if len(cname) >= 3 and re.search(rf"\b{re.escape(cname)}\b", clean_text, re.IGNORECASE):
                    if cname not in other_chars and cname.lower() != curr_spk_str:
                        other_chars.append(cname)

            dual_type = "UNKNOWN"
            if getattr(self, "series_bible", None) and hasattr(self.series_bible, "get_dual_pair_gender_type") and len(other_chars) >= 2:
                dual_type = self.series_bible.get_dual_pair_gender_type(other_chars)

            if dual_type == "DUAL_FEMALE":
                return "kobieta_dual", "Dwie Kobiety (Liczebnik podwójny: obie)"
            elif dual_type == "DUAL_MALE":
                return "mężczyzna_dual", "Dwóch Mężczyzn (Liczebnik podwójny: obaj)"
            elif dual_type == "DUAL_MIXED":
                return "para_mieszana_dual", "Para Mieszana (Liczebnik zbiorowy: oboje / dwoje)"

            # Fallback to lexical hints in raw_phase1 or clean_lower
            has_f = any(w in clean_lower for w in ["girl", "girls", "lady", "ladies", "women"]) or any(w in raw_norm for w in ["kobieta", "żeńsk", "female", "grupa_kobiet"])
            has_m = any(w in clean_lower for w in ["boy", "boys", "men"]) or any(w in raw_norm for w in ["mężczyzna", "męsk", "male", "grupa_mężczyzn"])
            if has_f and not has_m:
                return "kobieta_dual", "Dwie Kobiety (Liczebnik podwójny: obie)"
            elif has_m and not has_f:
                return "mężczyzna_dual", "Dwóch Mężczyzn (Liczebnik podwójny: obaj)"
            else:
                return "para_mieszana_dual", "Para Mieszana (Liczebnik zbiorowy: oboje / dwoje)"

        # 0. Strict Plural Group Check (Audio Ground Truth & Collective Vocative Gate)
        # Category grupa_... is ONLY permitted if there is verifiable plural evidence in audio or collective vocative.
        # Without evidence, raw_norm 'grupa_...' is rejected as an ungrounded hallucination.
        if has_plural_evidence:
            if is_universal_crowd_vocative:
                return "grupa_mieszana", "Grupa Mieszana (Zbiorowość/L. mnoga męskoosobowa)"

            check_idx = orig_idx if orig_idx is not None else (getattr(event, "_orig_idx", None) if getattr(event, "_orig_idx", None) is not None else event_idx)
            sc_g = (self.episode_scene_genders.get(check_idx) if hasattr(self, "episode_scene_genders") and self.episode_scene_genders else None)

            has_explicit_male = any(w in clean_lower for w in ["boy", "boys", "men", "chłopak", "panowie"]) or any(w in raw_norm for w in ["grupa_mężczyzn", "mężczyzna", "mężczyzn", "męsk", "male", "chłopak", "żołnierz"])
            has_explicit_female = any(w in clean_lower for w in ["girl", "girls", "lady", "ladies", "women", "dziewcz", "kobiet"]) or any(w in raw_norm for w in ["grupa_kobiet", "kobieta", "kobiet", "żeńsk", "female", "dziewczyn"])

            has_gendered_female = has_explicit_female or (sc_g == "kobieta")
            has_gendered_male = has_explicit_male or (sc_g == "mężczyzna")

            if has_gendered_female and not has_explicit_male:
                return "grupa_kobiet", "Grupa Kobiet (L. mnoga niemęskoosobowa)"
            elif has_gendered_male and not has_explicit_female:
                return "grupa_mężczyzn", "Grupa Mężczyzn (L. mnoga męskoosobowa)"
            else:
                return "grupa_mieszana", "Grupa Mieszana (Zbiorowość/L. mnoga męskoosobowa)"

        # 1. Textual Vocative Check (Calling someone by name in line text)
        for cname in list(self.character_registry.keys()):
            if len(cname) >= 3 and re.search(rf"\b{re.escape(cname)}[,!?]", clean_text, re.IGNORECASE):
                cdesc = self.character_registry.get(cname, "").lower()
                if any(k in cdesc for k in self.FEMALE_ROLE_KEYWORDS):
                    return "kobieta", f"{cname} (Kobieta)"
                elif any(k in cdesc for k in self.MALE_ROLE_KEYWORDS):
                    return "mężczyzna", f"{cname} (Mężczyzna)"

        # 1b. Onomastic Vocative Check (Direct address in English/Polish script, vocative address)
        from series_memory import is_inherently_female_name, MALE_EXCEPTIONS_ON_A, is_generic_actor_or_category
        voc_m = re.search(r"(?<!\b[Pp]anie\s)(?<!\b[Pp]ani\s)(?<!\b[Pp]anno\s)(?<!\b[Pp]anu\s)(?<!\b[Mm]istrzu\s)(?<!\b[Ll]ordzie\s)\b([A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]{2,})[,?!]", clean_text)
        if voc_m:
            cand_name = voc_m.group(1)
            cand_lower = cand_name.lower()
            if not is_generic_actor_or_category(cand_lower) and cand_lower not in ["wait", "look", "what", "why", "stop", "sorry", "excuse", "proszę", "przepraszam", "zaraz", "chwila", "czekaj", "słuchaj", "patrz", "widzisz"]:
                bible_gen = "UNKNOWN"
                if getattr(self, "series_bible", None) and hasattr(self.series_bible, "get_character_gender"):
                    bible_gen = self.series_bible.get_character_gender(cand_name, allow_generic_nouns=False)
                if bible_gen == "FEMALE" or is_inherently_female_name(cand_name):
                    return "kobieta", f"{cand_name} (Kobieta)"
                elif bible_gen == "MALE" or cand_lower in MALE_EXCEPTIONS_ON_A:
                    return "mężczyzna", f"{cand_name} (Mężczyzna)"

        # 2. 1-on-1 Dialogue Alternation (Ping-Pong Turn & Linguistic Context)
        curr_spk = (getattr(event, "name", None) or getattr(event, "actor", None) or "").strip()
        from series_memory import resolve_actor_gender, extract_clean_speaker_name, is_inherently_female_name, is_generic_actor_or_category

        # 1. Multi-Step Backward Interlocutor Search (up to 4 events, delta_t <= 8.0s)
        prev_interlocutor = None
        prev_interlocutor_ev = None
        if event_idx > 0 and curr_spk:
            curr_clean = extract_clean_speaker_name(curr_spk).lower()
            for b_off in range(1, min(5, event_idx + 1)):
                cand_item = batch_events[event_idx - b_off]
                cand_ev = cand_item[1] if len(cand_item) > 1 else None
                cand_spk = (getattr(cand_ev, "name", None) or getattr(cand_ev, "actor", None) or "").strip()
                cand_clean = extract_clean_speaker_name(cand_spk).lower()
                if cand_ev and abs(getattr(event, "start", 0) - getattr(cand_ev, "end", 0)) > 8000:
                    break
                if cand_clean and cand_clean != curr_clean:
                    prev_interlocutor = cand_spk
                    prev_interlocutor_ev = cand_ev
                    break
        elif event_idx == 0 and curr_spk:
            curr_clean = extract_clean_speaker_name(curr_spk).lower()
            if lookback_history:
                for cand_h in reversed(lookback_history[-4:]):
                    cand_spk = (cand_h.get("speaker") or cand_h.get("speaker_name") or "").strip()
                    cand_clean = extract_clean_speaker_name(cand_spk).lower()
                    if cand_clean and cand_clean != curr_clean:
                        prev_interlocutor = cand_spk
                        prev_g = (cand_h.get("speaker_gender") or "").strip().lower()
                        if prev_g in ["kobieta", "female", "żeński"]:
                            return "kobieta", f"{cand_spk} (Kobieta)"
                        elif prev_g in ["mężczyzna", "male", "męski"]:
                            return "mężczyzna", f"{cand_spk} (Mężczyzna)"
                        break

        if prev_interlocutor:
            p_res = resolve_actor_gender(prev_interlocutor, self.character_registry, getattr(self, "series_bible", None))
            if getattr(self, "series_bible", None) and hasattr(self.series_bible, "audit_speaker_metadata_against_audio"):
                p_sc_g = None
                p_orig_idx = getattr(prev_interlocutor_ev, "_orig_idx", None) if (prev_interlocutor_ev and getattr(prev_interlocutor_ev, "_orig_idx", None) is not None) else None
                if p_orig_idx is None and 'b_off' in locals():
                    p_orig_idx = event_idx - b_off
                if p_orig_idx is not None and hasattr(self, "episode_scene_genders") and self.episode_scene_genders:
                    raw_sc = self.episode_scene_genders.get(p_orig_idx)
                    if raw_sc in ["kobieta", "female", "FEMALE"]:
                        p_sc_g = "FEMALE"
                    elif raw_sc in ["mężczyzna", "male", "MALE"]:
                        p_sc_g = "MALE"
                p_audio_g = None
                if speaker_tags and p_orig_idx is not None:
                    p_tag = (speaker_tags.get(p_orig_idx + 1) or speaker_tags.get(p_orig_idx) or "").lower()
                    if any(w in p_tag for w in ["żeński", "kobieta", "female", "alt", "sopran"]):
                        p_audio_g = "FEMALE"
                    elif any(w in p_tag for w in ["męski", "mężczyzna", "male", "baryton", "bas"]):
                        p_audio_g = "MALE"
                p_res_audited, is_cont = self.series_bible.audit_speaker_metadata_against_audio(prev_interlocutor, audio_gender=p_audio_g, scene_gender=p_sc_g)
                if is_cont:
                    p_res = p_res_audited
            if p_res == "FEMALE":
                return "kobieta", f"{prev_interlocutor} (Kobieta)"
            elif p_res == "MALE":
                return "mężczyzna", f"{prev_interlocutor} (Mężczyzna)"

        # 2. Forward Interlocutor Lookahead (Turn Opening Dialogue, delta_t <= 6.0s)
        if len(batch_events) > event_idx + 1:
            curr_clean = extract_clean_speaker_name(curr_spk).lower()
            for f_off in range(1, min(4, len(batch_events) - event_idx)):
                next_item = batch_events[event_idx + f_off]
                next_ev = next_item[1] if len(next_item) > 1 else None
                next_spk = (getattr(next_ev, "name", None) or getattr(next_ev, "actor", None) or "").strip()
                next_clean = extract_clean_speaker_name(next_spk).lower()
                if next_ev and abs(getattr(next_ev, "start", 0) - getattr(event, "end", 0)) > 6000:
                    break
                if next_clean and next_clean != curr_clean:
                    next_res = resolve_actor_gender(next_spk, self.character_registry, getattr(self, "series_bible", None))
                    if getattr(self, "series_bible", None) and hasattr(self.series_bible, "audit_speaker_metadata_against_audio"):
                        next_sc_g = None
                        next_orig_idx = getattr(next_ev, "_orig_idx", None) if getattr(next_ev, "_orig_idx", None) is not None else (event_idx + f_off)
                        if hasattr(self, "episode_scene_genders") and self.episode_scene_genders:
                            raw_sc = self.episode_scene_genders.get(next_orig_idx)
                            if raw_sc in ["kobieta", "female", "FEMALE"]:
                                next_sc_g = "FEMALE"
                            elif raw_sc in ["mężczyzna", "male", "MALE"]:
                                next_sc_g = "MALE"
                        next_audio_g = None
                        if speaker_tags and next_orig_idx is not None:
                            n_tag = (speaker_tags.get(next_orig_idx + 1) or speaker_tags.get(next_orig_idx) or "").lower()
                            if any(w in n_tag for w in ["żeński", "kobieta", "female", "alt", "sopran"]):
                                next_audio_g = "FEMALE"
                            elif any(w in n_tag for w in ["męski", "mężczyzna", "male", "baryton", "bas"]):
                                next_audio_g = "MALE"
                        next_res_audited, is_cont = self.series_bible.audit_speaker_metadata_against_audio(next_spk, audio_gender=next_audio_g, scene_gender=next_sc_g)
                        if is_cont:
                            next_res = next_res_audited
                    if next_res == "FEMALE":
                        return "kobieta", f"{next_spk} (Kobieta)"
                    elif next_res == "MALE":
                        return "mężczyzna", f"{next_spk} (Mężczyzna)"
                    break

        # 2b. Scene-Cast Exclusive Gender Check (When all present characters are women or all are men)
        from series_memory import resolve_actor_gender
        batch_spks = set()
        for b_item in batch_events:
            b_ev = b_item[1] if len(b_item) > 1 else None
            b_name = (getattr(b_ev, "name", None) or getattr(b_ev, "actor", None) or "").strip()
            if b_name and not is_generic_actor_or_category(b_name):
                batch_spks.add(b_name)

        if len(batch_spks) >= 2:
            all_fem = True
            all_male = True
            for cand_spk in batch_spks:
                cand_g = resolve_actor_gender(cand_spk, self.character_registry, getattr(self, "series_bible", None))
                if cand_g != "FEMALE":
                    all_fem = False
                if cand_g != "MALE":
                    all_male = False
            if all_fem:
                other_spks = [s for s in batch_spks if s != curr_spk]
                rec_target = other_spks[0] if other_spks else list(batch_spks)[0]
                return "kobieta", f"{rec_target} (Kobieta - Scena Wyłącznie Kobieca)"
            elif all_male:
                other_spks = [s for s in batch_spks if s != curr_spk]
                rec_target = other_spks[0] if other_spks else list(batch_spks)[0]
                return "mężczyzna", f"{rec_target} (Mężczyzna - Scena Wyłącznie Męska)"

        if getattr(self, "series_bible", None) and hasattr(self.series_bible, "infer_scene_cast_from_text"):
            batch_texts = [b_item[1].text for b_item in batch_events if len(b_item) > 1 and getattr(b_item[1], "text", None)]
            whisper_list = [whisper_text] if whisper_text else None
            _, inf_g = self.series_bible.infer_scene_cast_from_text(batch_texts, whisper_texts=whisper_list)
            if inf_g == "FEMALE":
                return "kobieta", "Kobieta (Scena Wyłącznie Kobieca - Kotwica Bazy Wiedzy)"
            elif inf_g == "MALE":
                return "mężczyzna", "Mężczyzna (Scena Wyłącznie Męska - Kotwica Bazy Wiedzy)"

        # 2c. Pre-pass Episode Scene Cast Check (Fallback for Continuous Scene Ground Truth)
        check_idx = orig_idx if orig_idx is not None else (getattr(event, "_orig_idx", None) if getattr(event, "_orig_idx", None) is not None else event_idx)
        if check_idx is not None and hasattr(self, "episode_scene_genders") and self.episode_scene_genders:
            if check_idx in self.episode_scene_genders:
                sc_g = self.episode_scene_genders[check_idx]
                if sc_g == "kobieta":
                    return "kobieta", "Kobieta (Scena Wyłącznie Kobieca - Pre-pass Odcinka)"
                elif sc_g == "mężczyzna":
                    return "mężczyzna", "Mężczyzna (Scena Wyłącznie Męska - Pre-pass Odcinka)"

        # 3. Japanese Audio Addressee Clues (K1/K4)
        if wdd_tag.addressee_gender == "FEMALE":
            lbl = f"{wdd_tag.kinship_term} (Kobieta)" if wdd_tag.kinship_term else "Kobieta (z audio seiyū)"
            return "kobieta", lbl
        elif wdd_tag.addressee_gender == "MALE":
            lbl = f"{wdd_tag.kinship_term} (Mężczyzna)" if wdd_tag.kinship_term else "Mężczyzna (z audio seiyū)"
            return "mężczyzna", lbl

        # 4. Fallback to Single Person Detection (Safely degrades unverified plural tags to singular)
        if any(w in raw_norm for w in ["kobieta", "kobiet", "żeńsk", "female", "dziewczyn"]):
            return "kobieta", "Kobieta"
        elif any(w in raw_norm for w in ["mężczyzna", "mężczyzn", "męsk", "male", "chłopak"]):
            return "mężczyzna", "Mężczyzna"
        elif "brak" in raw_norm or "self" in raw_norm or "monolog" in raw_norm:
            return "brak", "Brak (Monolog / Myśl)"

        return None, None

    def build_phase1_prompt(self, *args, **kwargs):
        """Alias dla _prepare_batch_prompt (Standard 9.4 P0.2 / 2C.6)."""
        return self._prepare_batch_prompt(*args, **kwargs)

    def _prepare_batch_prompt(
        self,
        batch_events: List[Tuple[int, pysubs2.SSAEvent, str, str]],
        history_context: List[Dict[str, str]],
        lookahead_events: List[Tuple[int, pysubs2.SSAEvent, str, str]] = None,
        anime_context_str: str = "",
        episode_profile_str: str = "",
        episode_profile: Optional[EpisodeProfile] = None,
        whisper_transcriptions: Optional[Dict[int, str]] = None,
        series_bible_str: str = "",
        prosody_tags: Optional[Dict[int, str]] = None,
        speaker_tags: Optional[Dict[int, str]] = None,
        manga_canon_str: str = "",
        user_feedback_str: str = "",
        glossary_str: str = "",
        focused_rules_str: str = ""
    ) -> str:
        """
        Builds the prompt text for the current dialogue batch including:
        - Few-Shot Golden Examples & User Feedback
        - Deterministic Glossary Overrides
        - Context-Aware Focused AVT Rules
        - Official Polish Manga Canon
        - Cross-Episode Series Bible Continuity
        - Episode Profile (Glossary & Relationship Matrix)
        - AniList metadata context
        - Translation Memory examples
        - Character Registry
        - Previous dialogue history
        - Lookahead Window preview
        - Whisper Speech-to-Text transcription
        - Audio prosody and speaker diarization tags
        - CPS reading speed warnings
        """
        lines = []

        # 00c. Focused Scene Rules (Dynamic per-batch - always included)
        if focused_rules_str:
            lines.append(focused_rules_str)

        # Static Episode Knowledge (Only appended if not already baked into Cached System Instructions)
        if not getattr(self, "_episode_knowledge_cached", False):
            if user_feedback_str:
                lines.append(user_feedback_str)
            if glossary_str:
                lines.append(glossary_str)
            if manga_canon_str:
                lines.append(manga_canon_str)
            if series_bible_str:
                lines.append(series_bible_str)
            if episode_profile_str:
                lines.append(episode_profile_str)
            elif anime_context_str:
                lines.append(anime_context_str)

        # 0c. Translation Memory golden examples (Domain-Locked to current series)
        if self.tm:
            try:
                batch_queries = [item[2] for item in batch_events]
                series_hint = getattr(self, "series_title", None) or (self.series_bible.anime_title if hasattr(self, "series_bible") and self.series_bible else None)
                tm_examples = self.tm.find_relevant_examples(
                    batch_queries,
                    max_examples=3,
                    series_title=series_hint,
                    require_same_series=True if series_hint else False
                )
                if tm_examples:
                    lines.append(format_translation_memory_for_prompt(tm_examples))
            except Exception:
                logger.debug("Formatowanie pamięci tłumaczeniowej zakończone wyjątkiem", exc_info=True)

        # 1. Just-In-Time Character Scoping (Scene-level isolation - Anti-Saturation)
        if self.character_registry:
            batch_corpus = " ".join([
                clean_t for _, _, clean_t, _ in batch_events
            ]).lower()
            if history_context:
                batch_corpus += " " + " ".join([(h.get("en") or "") + " " + (h.get("pl") or "") for h in history_context]).lower()
            if lookahead_events:
                batch_corpus += " " + " ".join([str(item[2] if len(item) > 2 else "") for item in lookahead_events]).lower()

            active_speakers = {
                extract_clean_speaker_name(ev.name).strip().lower() for _, ev, _, _ in batch_events if getattr(ev, "name", None)
            }
            if history_context:
                for h in history_context[-4:]:
                    spk = extract_clean_speaker_name(h.get("speaker") or h.get("speaker_name") or "").strip().lower()
                    if spk:
                        active_speakers.add(spk)

            def _is_entity_present(ent_name: str) -> bool:
                cl = extract_clean_speaker_name(ent_name).strip().lower()
                if not cl or len(cl) < 3:
                    return False
                for p in re.split(r"[/,]", cl):
                    p_clean = p.strip()
                    if len(p_clean) >= 3:
                        p_stem = p_clean[:max(3, len(p_clean) - 2)]
                        if p_clean in active_speakers or any(s in p_clean or p_clean in s for s in active_speakers if len(s) >= 3):
                            return True
                        if p_stem in batch_corpus:
                            return True
                return False

            active_chars = {}
            for name, details in list(self.character_registry.items()):
                if "->" in name:
                    # Relationship: require both participants to be present in scene
                    parts = [p.strip() for p in name.split("->", 1)]
                    if len(parts) == 2 and _is_entity_present(parts[0]) and _is_entity_present(parts[1]):
                        active_chars[name] = details
                else:
                    # Individual character: require presence in scene
                    if _is_entity_present(name):
                        active_chars[name] = details

            if active_chars:
                lines.append("--- ZNANE POSTACIE W BIEŻĄCEJ SCENIE (spójność ról i płci) ---")
                for name, details in active_chars.items():
                    det_str = str(details)
                    clean_det = re.sub(r"\[(?:KOBIETA|MĘŻCZYZNA|PARA DWÓCH|RELACJA HIERARCHICZNA|OCHRONA PRZESKOKÓW|GRUPA|W 2\. os\.|Wymóg|Filar|T-V Invariance)[^\]]*\]", "", det_str, flags=re.IGNORECASE)
                    clean_det = re.sub(r"\s+", " ", clean_det).strip()
                    lines.append(f"• {name}: {clean_det or det_str}")
                lines.append("-------------------------------------------------------------\n")

        # 2. Previous dialogue history
        if history_context:
            lines.append("--- POPRZEDNIE KWESTIE W SCENIE (kontekst przeszły) ---")
            history_slice = []
            if len(history_context) >= 5:
                last_spk = (history_context[-1].get("speaker") or history_context[-1].get("speaker_name") or "").strip().lower()
                first_spk = (history_context[0].get("speaker") or history_context[0].get("speaker_name") or "").strip().lower()
                if last_spk and first_spk and last_spk == first_spk:
                    # Continuous monologue detected: anchor on initial premise + last 3 lines (exact 4-line budget)
                    history_slice = [("monologue_start", history_context[0])] + [("normal", h) for h in history_context[-3:]]
            if not history_slice:
                history_slice = [("normal", h) for h in history_context[-4:]]

            for mode, h in history_slice:
                spk_label = ""
                spk_name = (h.get("speaker") or h.get("speaker_name") or "").strip()
                spk_gen = (h.get("speaker_gender") or "").strip()
                if spk_name and spk_gen:
                    spk_label = f" (Mówca: {spk_name} | {spk_gen})"
                elif spk_name:
                    spk_label = f" (Mówca: {spk_name})"
                elif spk_gen:
                    spk_label = f" (Mówca: {spk_gen})"
                
                mode_label = " [💭 Myśl wewnętrzna]" if h.get("is_thought") else ""
                prefix_label = f"[Początek wywodu: {spk_name}]" if mode == "monologue_start" else "[Poprzednio]"

                if h.get("pl"):
                    lines.append(f"{prefix_label}{spk_label}{mode_label} EN: {h['en']} -> PL: {h['pl']}")
                else:
                    lines.append(f"{prefix_label}{spk_label}{mode_label} EN: {h['en']}")
            lines.append("-------------------------------------------------------\n")

        # 2b. Dynamic Crowd vs 1-on-1 (Uchi-Soto & Crowd Density Tracker)
        social_context = detect_scene_social_context(
            batch_events=batch_events,
            history_context=history_context,
            lookahead_events=lookahead_events,
            character_registry=self.get_character_registry_snapshot(),
            series_bible=getattr(self, "series_bible", None)
        )
        if social_context:
            lines.append("--- STATUS SPOŁECZNY SCENY (UCHI-SOTO / KADR 1-NA-1 VS ZBIOROWY) ---")
            lines.append(social_context)
            lines.append("-------------------------------------------------------------------\n")

        # 3. Lines to translate
        lines.append("Przekład kwestii na naturalną, żywą polszczyznę mówioną z zachowaniem filmowego rytmu dialogu:\n"
                     "1. Syntaktyka i ciągłość: całe zdania rozbite na linijki tworzą spójną całość z naturalnym polskim szykiem wyrazów.\n"
                     "2. Liczba i płeć: w dialogach bezpośrednich forma adresatywna (bezpośrednia lub grzecznościowa) oraz formy fleksyjne zgodne z relacją społeczną postaci, wektorem stanu sceny i rejestrem seiyū.\n"
                     "3. Triangulacja EN+JP+obraz: skrypt EN dostarcza treść i fakty, japońskie audio rejestr emocjonalny, a kadr obrazu napisy ekranowe.\n"
                     "4. Kwestie wielogłosu: wypowiedzi dwóch osób w jednej kwestii rozdzielane na osobne linie ('- Kwestia 1\\N- Kwestia 2').\n"
                     "5. Naturalność: żywy język dialogowy zamiast kalek dosłownych i struktur obcojęzycznych:")

        for idx, (original_idx, event, clean_text, ts_prefix) in enumerate(batch_events):
            start_str = pysubs2.time.ms_to_str(event.start)
            end_str = pysubs2.time.ms_to_str(event.end)
            vtype = detect_event_visual_type(event, ts_prefix, style_report=getattr(self, "style_report", None))
            duration_s = max(0.2, (event.end - event.start) / 1000.0)
            cps, is_fast = calculate_cps(clean_text, event.start, event.end)

            acoustic_cues = []
            if speaker_tags and (idx + 1) in speaker_tags:
                acoustic_cues.append(f"Głos: {speaker_tags[idx + 1]}")
            if prosody_tags and (idx + 1) in prosody_tags:
                acoustic_cues.append(f"Ton: {prosody_tags[idx + 1]}")
            acoustic_str = f" [{', '.join(acoustic_cues)}]" if acoustic_cues else ""

            # Dynamic cause-and-effect relationship detection with preceding line (intra-batch and cross-batch)
            relation_tag = ""
            prev_clean = ""
            prev_pl_ref = ""
            curr_is_affirmation = False
            is_prev_directive = False
            is_prev_wh = False
            is_prev_neg_q = False
            time_gap_ms = 0

            try:
                prev_ev_end = None
                if idx > 0 and not vtype["is_sign"]:
                    prev_clean = batch_events[idx - 1][2].strip()
                    prev_ev_end = batch_events[idx - 1][1].end
                elif idx == 0 and not vtype["is_sign"] and history_context:
                    prev_h = history_context[-1]
                    prev_clean = prev_h.get("en", "").strip()
                    prev_pl_ref = prev_h.get("pl", "").strip().lower()
                    if "end_ms" in prev_h:
                        prev_ev_end = prev_h["end_ms"]

                if prev_ev_end is not None:
                    time_gap_ms = max(0, event.start - prev_ev_end)

                is_shot_cut = False
                cuts_list = getattr(self, "scene_cuts_ms", None) or []
                if cuts_list and prev_ev_end is not None:
                    from scene_snapper import SceneShotSnapper
                    is_shot_cut = SceneShotSnapper.is_shot_boundary(event.start, prev_ev_end, cuts_list)

                is_black_fade = False
                black_list = getattr(self, "black_intervals_ms", None) or []
                if black_list and prev_ev_end is not None:
                    from scene_snapper import SceneShotSnapper
                    is_black_fade = SceneShotSnapper.is_black_fade_boundary(event.start, prev_ev_end, black_list)

                raw_whisper_item = whisper_transcriptions.get(idx + 1, "") if whisper_transcriptions else ""

                # Whisper Telemetry Sanity Guard (0.00 PLN)
                is_halluc_loop = WhisperDisambiguator.detect_hallucination_loop(raw_whisper_item)
                if is_halluc_loop:
                    jp_audio_line = ""
                elif isinstance(raw_whisper_item, dict):
                    jp_audio_line = str(raw_whisper_item.get("text", "")).lower()
                else:
                    jp_audio_line = str(raw_whisper_item).lower()

                is_phantom = WhisperDisambiguator.filter_voice_activity(raw_whisper_item)
                is_low_conf = WhisperDisambiguator.assess_acoustic_confidence(raw_whisper_item) == "LOW"

                if prev_clean or is_shot_cut or is_black_fade:
                    prev_clean_lower = prev_clean.lower()
                    clean_en_lower = clean_text.lower().strip()

                    # Czy wystąpił dyskontinuitet czasowy lub przeskok sceny (Filar CLXV)
                    is_prev_private_request = any(
                        w in prev_clean_lower for w in ["in private", "talk alone", "on our own", "somewhere quiet", "alone"]
                    ) or any(
                        w in prev_pl_ref for w in ["na osobności", "w cztery oczy", "porozmawiać", "pogadać", "w ustronne"]
                    )
                    is_curr_delayed_agreement = any(
                        clean_en_lower.startswith(w) for w in ["sure,", "sure.", "sure!", "all right,", "all right.", "yeah, what", "ok, what", "okay, what"]
                    )

                    wdd_tag = WhisperDisambiguator.disambiguate_line(
                        clean_en=clean_text,
                        jp_audio=jp_audio_line,
                        speaker=event.name,
                        character_registry=self.character_registry,
                        series_bible=getattr(self, "series_bible", None),
                        prev_clean_en=prev_clean,
                        prev_clean_pl=prev_pl_ref,
                        time_gap_ms=time_gap_ms
                    )
                    if is_phantom:
                        wdd_tag.is_phantom_audio = True
                    if is_low_conf:
                        wdd_tag.low_acoustic_confidence = True
                    if is_halluc_loop:
                        wdd_tag.is_hallucination_loop = True
                    if prosody_tags and "Ac=SHOCK_DROP" in prosody_tags.get(idx + 1, ""):
                        wdd_tag.is_shock_drop = True
                    compact_wdd_tag = WhisperDisambiguator.format_compact_ssot_tag(wdd_tag)

                    is_split_continuation = bool(
                        prev_clean.endswith(("...", "—", "-", "…")) or clean_text.strip().startswith(("...", "…"))
                    )
                    if is_split_continuation:
                        relation_tag = " [🔗 SPÓJNOŚĆ SKŁADNIOWA: Kontynuacja myśli urwanej wielokropkiem przez cięcie montażowe (L-cut/J-cut) – ZACHOWAJ MAŁĄ LITERĘ I CIĄGŁOŚĆ ZDANIA!]"
                    elif is_black_fade:
                        relation_tag = f" [🎬 CIĘCIE SCENY (Fade to Black / Eyecatch): Przejście przez czerń (pauza {time_gap_ms/1000.0:.1f}s) – nowa sekwencja (Filar CLXV); otwórz scenę ze świeżą energią i adekwatną intonacją]"
                    elif prosody_tags and "Ac=SHOCK_DROP" in prosody_tags.get(idx + 1, ""):
                        relation_tag = f" [TELEMETRIA: załamanie_energii_seiyū (szok/zamilknięcie, Ac=SHOCK_DROP)]"
                    elif (is_shot_cut or time_gap_ms >= 3800) and (is_prev_private_request or is_curr_delayed_agreement):
                        relation_tag = f" [🎬 CIĘCIE SCENY (FFmpeg) / DYSKONTINUITET CZASOWY: Nowe ujęcie (pauza {time_gap_ms/1000.0:.1f}s) / Zmiana sceny (Filar CLXV) – nowa rozmowa, otwarcie interakcji]"
                    elif (is_shot_cut or time_gap_ms >= 3800) and not is_split_continuation:
                        relation_tag = f" [🎬 CIĘCIE SCENY (FFmpeg) / ZMIANA SCENY: Nowe ujęcie (pauza {time_gap_ms/1000.0:.1f}s) – nowa sekwencja (Filar CLXV); zachowaj świeży początek nowej sceny]"
                    else:
                        # Standardowa analiza par sąsiedztwa w obrębie tej samej sceny
                        curr_is_affirmation = any(
                            clean_en_lower.startswith(w) for w in ["yes", "y-yes", "yeah", "yep", "right", "okay", "ok"]
                        ) or any(
                            w in jp_audio_line for w in ["hai", "はい", "ee", "ええ", "un", "うん"]
                        )

                        prev_jp = ""
                        if idx > 0 and whisper_transcriptions:
                            prev_raw = whisper_transcriptions.get(idx, "")
                            prev_jp = (str(prev_raw.get("text", "")) if isinstance(prev_raw, dict) else str(prev_raw or "")).lower()
                        elif idx == 0 and history_context:
                            hist_raw = history_context[-1].get("audio_jp", "")
                            prev_jp = (str(hist_raw.get("text", "")) if isinstance(hist_raw, dict) else str(hist_raw or "")).lower()

                        is_prev_directive = any(
                            w in prev_clean_lower for w in [
                                "watch your step", "be careful", "watch out", "look out", "mind the",
                                "careful", "hold on", "wait", "listen", "don't move", "hurry", "stay back",
                                "follow me", "step back", "take care"
                            ]
                        ) or any(
                            w in prev_pl_ref for w in [
                                "uważaj", "uważajcie", "ostrożnie", "czekaj", "zaczekaj", "poczekaj",
                                "stój", "stójcie", "nie ruszaj", "pospiesz", "chodź", "chodźcie", "ruszaj",
                                "trzymaj się"
                            ]
                        ) or any(
                            w in prev_jp for w in [
                                "ki o tsukete", "kiwotsukete", "abunai", "chotto matte", "mate",
                                "tomare", "ugoku na", "hayaku", "気をつけ", "危ない", "待って", "止まれ"
                            ]
                        )

                        is_prev_wh = prev_clean.endswith("?") and (
                            any(w in prev_clean_lower for w in ["what", "where", "why", "how", "who", "when", "which", "whose", "whom"]) or
                            bool(re.search(r"\b(dokąd|gdzie|skąd|kiedy|dlaczego|czemu|po\s+co|kto|kogo|komu|kim|co|czego|czym|jak|jaki|jaka|jakie|jakim|jakich|o\s+co|o\s+czym|z\s+kim)\b", prev_pl_ref, re.IGNORECASE))
                        )

                        is_prev_neg_q = prev_clean.endswith("?") and (
                            any(w in prev_clean_lower for w in ["don't", "aren't", "didn't", "can't", "won't", "haven't", "isn't"]) or
                            bool(re.search(r"\bnie\s+(jest|jesteś|jesteście|są|był|była|było|byli|byłeś|byłaś|będzie|będziesz|będą|ma|masz|macie|chcesz|chce|chcecie|wiesz|wie|wiecie|możesz|może|możecie|idziesz|idzie|idziecie|zrobisz|mówisz|widzisz|słyszysz)\b", prev_pl_ref, re.IGNORECASE))
                        )

                        if is_prev_directive and curr_is_affirmation:
                            relation_tag = " [RELACJA: Reakcja na ostrzeżenie/dyrektywę (Filar CXLVI & XLIII) – potwierdź gotowość: 'Dobrze / D-Dobrze / Jasne / Będę uważać / W porządku']"
                        elif is_prev_wh and curr_is_affirmation:
                            relation_tag = " [RELACJA: Odpowiedź na pytanie otwarte (Filar CXLVI) – wahanie seiyū: 'Eee...' / 'E-Eee...' / 'Cóż...']"
                        elif (wdd_tag and wdd_tag.polar_agreement) or (is_prev_neg_q and curr_is_affirmation):
                            relation_tag = " [RELACJA: Potwierdzenie przeczenia / Echo Agreement (Filar CLIV) – odpowiedź na fakt: 'Nie / Zgadza się / Wcale nie']"
                        elif prev_clean.endswith("?"):
                            relation_tag = " [RELACJA: Prawdopodobna odpowiedź/reakcja na pytanie]"
                        elif any(prev_clean_lower.startswith(w) for w in ["come,", "let's", "shall we", "look,", "hey,"]):
                            relation_tag = " [RELACJA: Prawdopodobna reakcja / zgoda / odmowa na zaproszenie/propozycję]"
                        elif prev_clean.endswith("...") or prev_clean.endswith("…") or clean_text.strip().startswith("...") or clean_text.strip().startswith("…"):
                            relation_tag = " [SPÓJNOŚĆ SKŁADNIOWA: Kontynuacja myśli rozbitej wielokropkiem – użyj orzeczenia osobowego w formie zgodnej z podmiotem (np. '...daje wyniki', a nie imiesłowu)]"
                else:
                    wdd_tag = WhisperDisambiguator.disambiguate_line(
                        clean_en=clean_text,
                        jp_audio=jp_audio_line,
                        speaker=event.name,
                        character_registry=self.character_registry,
                        series_bible=getattr(self, "series_bible", None)
                    )
                    compact_wdd_tag = WhisperDisambiguator.format_compact_ssot_tag(wdd_tag)

                # Whisper JP-First Semantic Override & Anti-Pivot Cliché Detection (Filar CLXVI)
                clean_en_lower = clean_text.lower().strip()
                is_en_cliche = any(clean_en_lower.startswith(w) for w in ["sure", "all right", "yeah", "here", "i'm fine", "i am fine", "wait"])
                has_jp_affirmation = any(tok in jp_audio_line for tok in ["hai", "ee", "un", "wakatta", "はい", "ええ", "うん", "分かった"])
                if is_en_cliche and not has_jp_affirmation and jp_audio_line:
                    if any(tok in jp_audio_line for tok in ["nani", "dou shita", "doushita", "nan da", "何", "どうした", "なんだ"]):
                        k_alert = f"[TELEMETRIA: klisza_fansuberska: w audio pytanie '{jp_audio_line}']"
                        relation_tag = f"{relation_tag} {k_alert}".strip() if relation_tag else f" {k_alert}"
                    elif len(clean_text.split()) <= 2 and any(w == "here" for w in re.findall(r"\b[a-zA-Z]+\b", clean_en_lower)) and any(tok in jp_audio_line for tok in ["yoisho", "dokkoisho", "hora", "douzo"]):
                        s_alert = "[TELEMETRIA: szum_kinezjatyczny: gest/kakegoe seiyū]"
                        relation_tag = f"{relation_tag} {s_alert}".strip() if relation_tag else f" {s_alert}"
            except Exception:
                relation_tag = ""
                compact_wdd_tag = ""

            # Fuzzy Entity Casing Normalizer: Ensure proper names from series bible & character registry have uppercase first letter
            clean_display_text = clean_text
            canonical_entities = set()
            if self.character_registry:
                canonical_entities.update(list(self.character_registry.keys()))
            if hasattr(self, "series_bible") and self.series_bible and hasattr(self.series_bible, "data"):
                canonical_entities.update(list(self.series_bible.data.get("characters", {}).keys()))
            for ent in canonical_entities:
                clean_ent = extract_clean_speaker_name(ent).strip()
                if clean_ent and len(clean_ent) >= 3 and clean_ent[0].isupper() and "->" not in clean_ent:
                    pattern_parts = []
                    for c in clean_ent:
                        base = unicodedata.normalize("NFD", c)[0]
                        if base != c:
                            pattern_parts.append(f"[{re.escape(c)}{re.escape(base)}]")
                        else:
                            pattern_parts.append(re.escape(c))
                    pattern = r"(?i)\b" + "".join(pattern_parts) + r"\b"
                    clean_display_text = re.sub(pattern, clean_ent, clean_display_text)

            if vtype["is_sign"]:
                # Kondensacja krótkich plansz z punktorem (Standard 9.5, 2C.2)
                if (event.end - event.start) <= 2500 and ("•" in clean_display_text or "●" in clean_display_text) and len(clean_display_text) > 120:
                    clean_display_text = clean_display_text.split(r"\N")[0].split("\n")[0].strip()
                lines.append(f"Kwestia [ID: {idx + 1}] [TYP: [NAPIS] {vtype['type_label']}] (Czas: {start_str} - {end_str}, Cechy: {vtype['visual_details']}):")
                lines.append(f"  📄 SKRYPT PODSTAWOWY EN (TREŚĆ I MAJUSKUŁA): {clean_display_text}")

                # Active Line Glossary Pinning: Check if any canonical glossary terms appear in sign
                active_gloss = getattr(self, "combined_glossary", {})
                if active_gloss:
                    clean_lower = clean_text.lower()
                    for term_en, term_pl in active_gloss.items():
                        if term_en and len(term_en) >= 3 and term_en.lower() in clean_lower:
                            lines.append(f"  📖 SŁOWNIK KANONICZNY: '{term_en}' => '{term_pl}'")
                lines.append(f"  Kontekst wizualny: napis lub plansza na ekranie (samodzielny tytuł, szyld, tablica).")
                lines.append(f"  Przekład jako samodzielny tytuł lub napis w kadrze.")
                lines.append(f"  Położenie i typesetting: obiekt 'visual_typesetting' (detected_box_1000 [ymin, xmin, ymax, xmax], placement, rotation_deg, kolory HEX, screen_region).")
                lines.append(f"  Typografia: treść napisu lub planszy w kadrze.")
            else:
                # Standard 9.5 (Operacja 2C.1, R3.2): Wywołanie arbitrate_event_telemetry
                from scene_discourse import SceneDiscourseGraph
                is_fem_scene_check = (getattr(self, "episode_scene_genders", {}).get(original_idx) == "kobieta") or getattr(self, "scene_is_female_only", False)
                disc_telem = SceneDiscourseGraph.arbitrate_event_telemetry(
                    event=event,
                    series_bible=getattr(self, "series_bible", None),
                    episode_profiler=getattr(self, "profiler", None),
                    raw_actor=event.name,
                    scene_female_only=is_fem_scene_check,
                    is_sign=vtype["is_sign"]
                )
                p0_spk_gram = disc_telem.get("grammatical_gender")
                if p0_spk_gram in ("MASCULINE", "FEMININE"):
                    line_spk_gender = "mężczyzna" if p0_spk_gram == "MASCULINE" else "kobieta"
                else:
                    line_spk_gender, _ = self._arbitrate_speaker_gender(
                        event=event,
                        raw_phase1_gender=None,
                        batch_id=idx + 1,
                        speaker_tags=speaker_tags,
                        whisper_transcriptions=whisper_transcriptions,
                        pl_candidate="",
                        raw_speaker_name=event.name,
                        event_idx=original_idx
                    )
                line_addr_cat, line_addr_lbl = self._resolve_line_addressee(
                    event=event,
                    raw_phase1_addressee=None,
                    batch_events=batch_events,
                    event_idx=idx,
                    whisper_text=(whisper_transcriptions.get(idx + 1, "") if whisper_transcriptions else ""),
                    clean_text=clean_text,
                    orig_idx=original_idx,
                    lookback_history=history_context,
                    speaker_tags=speaker_tags,
                    prosody_tags=prosody_tags
                )

                if line_addr_cat in ["grupa_kobiet", "kobieta_dual"]:
                    reg_desc = "L. mnoga niemęskoosobowa"
                elif line_addr_cat in ["grupa_mężczyzn", "mężczyzna_dual"]:
                    reg_desc = "L. mnoga męskoosobowa"
                elif line_addr_cat in ["grupa_mieszana", "para_mieszana_dual"]:
                    reg_desc = "L. mnoga / para mieszana"
                elif line_addr_cat == "kobieta":
                    reg_desc = "2. os. lp. 'ty' do kobiety"
                elif line_addr_cat == "mężczyzna":
                    reg_desc = "2. os. lp. 'ty' do mężczyzny"
                else:
                    reg_desc = "Kontekstowy / Naturalny"

                if event.name and not is_generic_actor_or_category(event.name):
                    spk_label = event.name
                    if line_spk_gender:
                        spk_label += f" ({line_spk_gender.capitalize()})"
                elif line_spk_gender:
                    spk_label = line_spk_gender.capitalize()
                else:
                    spk_label = "Postać"

                if line_addr_lbl:
                    addr_label = line_addr_lbl
                elif line_addr_cat:
                    addr_label = line_addr_cat.replace("_", " ").capitalize()
                else:
                    addr_label = "Nieokreślony / Monolog"

                lines.append(f"Kwestia [ID: {idx + 1}] [TYP: [DIALOG] {vtype['type_label']}]{relation_tag} (Czas: {start_str} - {end_str}) [MÓWCA: {spk_label} | ADRESAT: {addr_label} | REJESTR: {reg_desc}]{acoustic_str}:")
                lines.append(f"  📄 SKRYPT PODSTAWOWY EN (TREŚĆ SEMANTYCZNA I FAKTY): {clean_display_text}")

                # Detekcja monologu wewnętrznego (Standard 9.4, 2C.6, Hotfix 10.1.1 2B.2)
                st_lower = str(getattr(event, "style", "")).lower()
                italic_attr = getattr(event, "italic", 0)
                has_italic_style = any(k in st_lower for k in ["italic", "flashback_italic", "thoughts", "internal"]) or italic_attr in (1, -1)
                is_short_reply = is_short_spoken_reply(clean_display_text)
                has_target = bool(disc_telem.get("target_actor") or (line_addr_cat and line_addr_cat.lower() not in ("unknown", "unknown_individual", "monologue", "unknown_plural", "monolog")))
                is_spoken_style = any(st_lower == s or st_lower.startswith(s) for s in ["default", "normal", "main", "dialogue", "alt"])
                has_thought_brackets = ("(" in clean_display_text and ")" in clean_display_text) or ("（" in clean_display_text and "）" in clean_display_text)

                if is_short_reply or has_target or (is_spoken_style and not has_thought_brackets):
                    is_internal_monologue = has_italic_style and not is_short_reply
                else:
                    has_whisper_monologue = "monolog wewnętrzny" in relation_tag
                    is_internal_monologue = has_italic_style or has_whisper_monologue
                if is_internal_monologue:
                    lines.append("  💭 TRYB WYPOWIEDZI: MONOLOG WEWNĘTRZNY / MYŚLI (is_internal_monologue: true) — Wymagane tagi {\\i1}...{\\i0} w phase1_text.")

                # Pre-Generation Morphosyntactic Contract (Stream 4 - Standard 3.0 / 9.5)
                contract_spk_gender = "UNKNOWN"
                if p0_spk_gram in ("MASCULINE", "FEMININE"):
                    contract_spk_gender = p0_spk_gram
                elif line_spk_gender:
                    g_l = line_spk_gender.lower()
                    if any(k in g_l for k in ["mężczyzna", "male", "chłopak", "boy"]):
                        contract_spk_gender = "MASCULINE"
                    elif any(k in g_l for k in ["kobieta", "female", "dziewczyn", "girl"]):
                        contract_spk_gender = "FEMININE"

                contract_target_gender = "UNKNOWN"
                p0_tgt_gram = disc_telem.get("target_gender")
                if p0_tgt_gram in ("MASCULINE", "FEMININE"):
                    contract_target_gender = p0_tgt_gram
                elif line_addr_cat:
                    a_l = line_addr_cat.lower()
                    if any(k in a_l for k in ["kobieta", "female", "dziewczyn", "kobieta_dual", "grupa_kobiet"]):
                        contract_target_gender = "FEMININE"
                    elif any(k in a_l for k in ["mężczyzna", "male", "chłopak", "mężczyzna_dual", "grupa_mężczyzn"]):
                        contract_target_gender = "MASCULINE"

                contract_addr_number = "PLURAL" if (
                    line_addr_cat in ["grupa_kobiet", "grupa_mężczyzn", "grupa_mieszana", "kobieta_dual", "mężczyzna_dual", "para_mieszana_dual"]
                    or is_plural_actor(addr_label)
                ) else "SINGULAR"

                detected_entities: List[str] = []
                if event.name and not is_generic_actor_or_category(event.name):
                    cl_spk = extract_clean_speaker_name(event.name).strip()
                    if cl_spk and len(cl_spk) >= 3 and cl_spk not in detected_entities:
                        detected_entities.append(cl_spk)

                known_names = set()
                if self.character_registry:
                    known_names.update([extract_clean_speaker_name(k).strip() for k in self.character_registry.keys() if "->" not in k])
                sb_inst = getattr(self, "series_bible", None)
                if sb_inst and hasattr(sb_inst, "data"):
                    known_names.update([extract_clean_speaker_name(k).strip() for k in sb_inst.data.get("characters", {}).keys() if "->" not in k])
                    known_names.update(list(sb_inst.data.get("places", {}).keys()))

                for kn in sorted(known_names, key=lambda x: len(x), reverse=True):
                    if len(kn) >= 3 and re.search(rf"\b{re.escape(kn)}\b", clean_text, re.IGNORECASE):
                        if kn not in detected_entities and len(detected_entities) < 2:
                            detected_entities.append(kn)

                entity_cat_strs = []
                paradigm_strs = []
                for ent in detected_entities:
                    cat_enum = classify_entity_category(ent, series_bible=sb_inst)
                    entity_cat_strs.append(f"{ent}: {cat_enum.value}")
                    par = None
                    if sb_inst and hasattr(sb_inst, "get_declension_paradigm"):
                        par = sb_inst.get_declension_paradigm(ent)
                    if not par:
                        ent_g = "MALE" if contract_spk_gender == "MASCULINE" and ent == event.name else ("FEMALE" if contract_spk_gender == "FEMININE" and ent == event.name else "UNKNOWN")
                        par = DeclensionParadigm.create_for_name(ent, gender=ent_g)
                    if par:
                        paradigm_strs.append(f"{ent}(D:{par.D}, C:{par.C}, B:{par.B}, N:{par.N}, Ms:{par.Ms}, W:{par.W})")

                target_actor_name = line_addr_lbl if line_addr_lbl else (getattr(event, "target_actor", None) or getattr(event, "target_speaker", None))
                if is_internal_monologue:
                    target_actor_name = None
                    contract_target_gender = "UNKNOWN"
                pragmatic_reg = detect_japanese_pragmatic_register(jp_audio_line, clean_text) if (jp_audio_line and "detect_japanese_pragmatic_register" in globals()) else None
                reg_name = pragmatic_reg or (reg_desc if reg_desc and "Kontekstowy" not in reg_desc else getattr(event, "register", None))

                is_fem_scene = (getattr(self, "episode_scene_genders", {}).get(original_idx) == "kobieta") or getattr(self, "scene_is_female_only", False)
                has_male_speaker_in_line = (
                    contract_spk_gender == "MASCULINE"
                    or line_spk_gender == "mężczyzna"
                )
                has_male_addressee_in_line = (
                    contract_target_gender == "MASCULINE"
                    or line_addr_cat in ["mężczyzna", "mężczyzna_dual", "grupa_mężczyzn"]
                )
                if has_male_speaker_in_line:
                    is_fem_scene = False

                if is_fem_scene:
                    pl_grp_val = "NON_VIRILE"
                    you_grp_val = "VIRILE" if (has_male_addressee_in_line or line_addr_cat in ["grupa_mężczyzn", "mężczyzna_dual", "grupa_mieszana", "para_mieszana_dual"]) else ("NON_VIRILE" if line_addr_cat in ["grupa_kobiet", "kobieta_dual"] else None)
                else:
                    pl_grp_val = "VIRILE" if (has_male_speaker_in_line or line_addr_cat in ["grupa_mężczyzn", "mężczyzna_dual"] or (contract_addr_number == "PLURAL" and getattr(self, "scene_has_male", False))) else ("NON_VIRILE" if contract_addr_number == "PLURAL" else None)
                    if has_male_speaker_in_line and pl_grp_val == "NON_VIRILE":
                        pl_grp_val = "VIRILE"
                    you_grp_val = "VIRILE" if (has_male_addressee_in_line or line_addr_cat in ["grupa_mężczyzn", "mężczyzna_dual", "grupa_mieszana", "para_mieszana_dual"]) else ("NON_VIRILE" if line_addr_cat in ["grupa_kobiet", "kobieta_dual"] else None)

                batch_actors = {getattr(b_ev, "name", "") for _, b_ev, _, _ in batch_events if getattr(b_ev, "name", "") and not is_generic_actor_or_category(getattr(b_ev, "name", ""))}
                poly_val = getattr(self, "episode_scene_polylogues", {}).get(original_idx)
                if not poly_val and len(batch_actors) >= 3:
                    poly_val = f"POLYLOGUE (n={len(batch_actors)})"

                dry_telemetry = format_dry_telemetry_tag(
                    speaker_gender=contract_spk_gender,
                    speaker_confidence=1.0 if str(contract_spk_gender).lower() in ("masculine", "feminine") else 0.0,
                    target_gender=contract_target_gender,
                    target_confidence=1.0 if str(contract_target_gender).lower() in ("masculine", "feminine") else 0.0,
                    plural_group_gender=pl_grp_val,
                    plural_confidence=1.0 if pl_grp_val else 0.0,
                    you_group_gender=you_grp_val,
                    you_group_confidence=1.0 if you_grp_val else 0.0,
                    speaker_name=disc_telem.get("speaker_name") or event.name or "UNKNOWN",
                    target_name=target_actor_name if target_actor_name else None,
                    register=reg_name if reg_name else None,
                    polylogue=poly_val
                )
                if dry_telemetry:
                    lines.append(f"  📡 TELEMETRIA: {dry_telemetry}")
                if paradigm_strs:
                    lines.append(f"  📖 Paradygmat odmiany: {'; '.join(paradigm_strs)}")
                elif entity_cat_strs:
                    lines.append(f"  🏷️ Kategorie encji: {', '.join(entity_cat_strs)}")
                if compact_wdd_tag:
                    cleaned_wdd = re.sub(r"\bK[13]\b", "", compact_wdd_tag)
                    cleaned_wdd = re.sub(r"\[\s*\]", "", cleaned_wdd)
                    cleaned_wdd = re.sub(r"\s+", " ", cleaned_wdd).strip()
                    if cleaned_wdd and cleaned_wdd not in ("🎙️", "🎙️ :"):
                        lines.append(f"  {cleaned_wdd}")
                subj_3p = detect_third_person_mentions(
                    clean_text=clean_text,
                    speaker=event.name,
                    character_registry=self.character_registry,
                    series_bible=getattr(self, "series_bible", None)
                )
                for s3 in subj_3p:
                    lines.append(f"  {s3}")

                # Active Line Glossary Pinning: Check if any canonical glossary terms appear in this line
                active_gloss = getattr(self, "combined_glossary", {})
                if active_gloss:
                    clean_lower = clean_text.lower()
                    for term_en, term_pl in active_gloss.items():
                        if term_en and len(term_en) >= 3 and term_en.lower() in clean_lower:
                            lines.append(f"  📖 SŁOWNIK KANONICZNY: '{term_en}' => '{term_pl}' (forma bazowa – w dialogu ZAWSZE odmieniaj przez polskie przypadki!)")
                if vtype.get("is_top"):
                    lines.append(f"  Dialog górny: dialog w tle lub oddali – naturalny dialog mówiony.")
                is_split_part = (
                    clean_text.strip().startswith("...")
                    or clean_text.strip().startswith("…")
                    or prev_clean.endswith("...")
                    or prev_clean.endswith("…")
                )
                if duration_s <= 0.6 and not is_split_part:
                    lines.append(f"  Informacja o tempie: mikro-kwestia (czas {duration_s:.1f}s, tempo {cps:.1f} z/s) – MIKRO-KWESTIA / DŹWIĘK WAHANIA (zwięzłość 1-2 słów).")
                elif duration_s <= 0.6 and is_split_part:
                    lines.append(f"  Informacja o tempie: krótki czas trwania ({duration_s:.1f}s, tempo {cps:.1f} z/s) – fragment zdania rozbitego wielokropkiem (ZACHOWAJ CIĄGŁOŚĆ SKŁADNIOWĄ).")
                elif is_fast:
                    lines.append(f"  Informacja o tempie: tempo CPS ({cps:.1f} z/s, czas {duration_s:.1f}s) – szybka kwestia (kondensacja AVT).")

                max_pl_chars = min(76, int(max(0.5, duration_s) * 17.0))
                lines.append(f"  Parametry planszy: budżet {max_pl_chars} znaków (tempo czytania do 17.0 z/s, max 2 wiersze).")

            if whisper_transcriptions and idx + 1 in whisper_transcriptions:
                raw_jp_item = whisper_transcriptions[idx + 1]
                is_halluc = WhisperDisambiguator.detect_hallucination_loop(raw_jp_item)
                is_phantom = WhisperDisambiguator.filter_voice_activity(raw_jp_item)
                is_low_conf = WhisperDisambiguator.assess_acoustic_confidence(raw_jp_item) == "LOW"

                if is_halluc:
                    jp_text = ""
                elif isinstance(raw_jp_item, dict):
                    jp_text = str(raw_jp_item.get("text", "")).strip()
                else:
                    jp_text = str(raw_jp_item).strip()
                from profiler import EpisodeProfiler
                jp_text = EpisodeProfiler.sanitize_event_asr(
                    jp_text,
                    is_sign=vtype["is_sign"],
                    style=getattr(event, "style", None)
                )

                if is_phantom and not vtype["is_sign"]:
                    lines.append("  🎙️ GŁOS SEIYŪ: [Audio: Tło muzyczne / SFX / brak mowy seiyū]")
                elif jp_text and not vtype["is_sign"]:
                    romaji_str = to_romaji(jp_text)
                    jp_display = f"{jp_text} [{romaji_str}]" if romaji_str and romaji_str != jp_text else jp_text
                    if is_low_conf:
                        lines.append(f"  🎙️ GŁOS SEIYŪ (KOTWICA FONICZNA - NISKA PEWNOŚĆ / KRZYK): {jp_display}")
                    else:
                        lines.append(f"  🎙️ GŁOS SEIYŪ (KOTWICA FONICZNA, REJESTR, AFEKT I PŁEĆ): {jp_display}")
                    semantic_anchor = get_audio_semantic_anchor(jp_text, clean_text)
                    if semantic_anchor:
                        lines.append(f"  🎯 ZGODNOŚĆ FONICZNO-SEMANTYCZNA (FILAR CLVIII): {semantic_anchor}")
                    if duration_s <= 0.8 and any(h in jp_text for h in ["え", "う", "あの", "えっと", "ん", "ま…", "あ…", "え…"]) and len(clean_text.split()) > 2:
                        lines.append(f"  [TELEMETRIA: wahanie_audio_jp: w audio seiyū wahanie ('{jp_display}')]")
            if episode_profile:
                pinned_alerts = getattr(self, "profile_line_alerts", {}).get(original_idx) or getattr(self, "profile_line_alerts", {}).get(idx)
                if pinned_alerts:
                    for pa in pinned_alerts:
                        lines.append(f"  {pa}")
                else:
                    if getattr(episode_profile, "danger_lines_prescan", None):
                        for dl in episode_profile.danger_lines_prescan:
                            if dl.english_phrase and dl.english_phrase.lower() in clean_text.lower():
                                guide = getattr(dl, "contextual_guidance", "")
                                lines.append(f"  [TELEMETRIA: pułapka_kontekstowa: {dl.contextual_trap} | wskazówka: {guide}]")
                                break
                    if getattr(episode_profile, "character_catchphrases", None):
                        for cp in episode_profile.character_catchphrases:
                            if cp.original_phrase and cp.original_phrase.lower() in clean_text.lower():
                                lines.append(f"  [💬 KWESTIA-WIZYTÓWKA: '{cp.canonical_pl}' ({cp.context_notes})]")
                                break
                    if getattr(episode_profile, "puns_and_wordplays", None):
                        for pun in episode_profile.puns_and_wordplays:
                            if pun.original_joke_or_pun and pun.original_joke_or_pun.lower() in clean_text.lower():
                                lines.append(f"  [🃏 GRA SŁOWNA: {pun.polish_transcreation}]")
                                break

        # 4. Lookahead window
        if lookahead_events:
            lines.append("\n--- Podgląd kolejnych kwestii (kontekst dyskursu) ---")
            for _, fut_ev, future_text, _ in lookahead_events[:4]:
                fut_spk = f" (Mówca: {fut_ev.name})" if fut_ev and getattr(fut_ev, "name", None) else ""
                lines.append(f"[Kolejna kwestia]{fut_spk} EN: {future_text}")
            lines.append("-----------------------------------------------------")

        return "\n".join(lines)

    build_phase1_prompt = _prepare_batch_prompt

    def _call_gemini_with_retry(self, contents: List[Any], schema_class) -> Any:
        """
        Reliable API call with automated handling of rate limits (429) and server overloads (503).
        In Phase 1, seamlessly alternates and switches between the two highest Flash models
        (e.g., Gemini 3.7 Flash and Gemini 3.6 Flash) for optimal throughput and quota distribution,
        while maintaining the absolute highest model version for Phase 2 verification.
        """
        from model_resolver import resolve_best_models
        active_models = resolve_best_models(self.client)

        current_model = self.model
        attempt = 0

        while True:
            attempt += 1
            cached_name = None
            try:
                from context_cache import ContextCacheManager
                gen_config_kwargs = {
                    "response_mime_type": "application/json",
                    "response_schema": schema_class,
                    "temperature": 0.25,
                }
                # Phase 1: Always enforce thinking_budget=0 (CoT=0) for any Flash/Pro models (regardless of version)
                # ensuring rapid triangulation with zero thinking token cost.
                is_reasoning_capable = ("flash" in current_model.lower() or "pro" in current_model.lower() or "thinking" in current_model.lower() or "reasoning" in current_model.lower()) and "lite" not in current_model.lower()
                if is_reasoning_capable:
                    budget_p1 = getattr(self, "phase1_thinking_budget", 0)
                    gen_config_kwargs["thinking_config"] = types.ThinkingConfig(thinking_budget=budget_p1)

                import concurrent.futures

                last_used_client = None
                def _single_generate():
                    nonlocal cached_name, last_used_client
                    from client_factory import global_rate_limiter
                    global_rate_limiter.acquire()
                    active_c = self.client_pool.get_client() if hasattr(self, "client_pool") and self.client_pool else self.client
                    last_used_client = active_c
                    cached_name = ContextCacheManager.get_or_create_cache(
                        client=active_c,
                        model=current_model,
                        system_instruction=self.system_prompt,
                        tag="translator"
                    )
                    cfg_kwargs = dict(gen_config_kwargs)
                    if cached_name:
                        cfg_kwargs["cached_content"] = cached_name
                    else:
                        is_paid = ("flash" in current_model.lower() or "pro" in current_model.lower()) and "lite" not in current_model.lower()
                        if is_paid:
                            cached_name = ContextCacheManager.get_or_create_cache(
                                client=active_c,
                                model=current_model,
                                system_instruction=self.system_prompt,
                                tag="translator"
                            )
                            if cached_name:
                                cfg_kwargs["cached_content"] = cached_name
                            else:
                                raise RuntimeError(
                                    f"KATEGORYCZNA BLOKADA FINANSOWA: Zablokowano próbę wysłania 33k tokenów bez aktywnego rabatu -90% dla {current_model}."
                                )
                        if "cached_content" not in cfg_kwargs:
                            cfg_kwargs["system_instruction"] = self.system_prompt
                    cfg = types.GenerateContentConfig(**cfg_kwargs)
                    return active_c.models.generate_content(
                        model=current_model,
                        contents=contents,
                        config=cfg
                    )

                # Direct generation using thread-safe client pool and token bucket limiter with hard 95s watchdog
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
                    fut = ex.submit(_single_generate)
                    response = fut.result(timeout=95.0)

                if not hasattr(self, "_thread_local") or self._thread_local is None:
                    self._thread_local = threading.local()
                self._thread_local.last_batch_token_usage = {}
                if hasattr(response, "usage_metadata") and response.usage_metadata:
                    um = response.usage_metadata
                    p_cnt = getattr(um, "prompt_token_count", 0) or 0
                    c_cnt = getattr(um, "cached_content_token_count", 0) or 0
                    cands = getattr(um, "candidates_token_count", 0) or 0
                    thoughts = getattr(um, "thoughts_token_count", 0) or 0
                    out_cnt = (cands + thoughts)
                    self._thread_local.last_batch_token_usage = {
                        "prompt": p_cnt,
                        "cached": c_cnt,
                        "output": out_cnt,
                        "model": current_model,
                    }
                    with self.lock:
                        self.current_episode_tokens["prompt"] += p_cnt
                        self.current_episode_tokens["cached"] += c_cnt
                        self.current_episode_tokens["output"] += out_cnt
                        self.current_episode_tokens["model"] = current_model

                if hasattr(response, "parsed") and response.parsed is not None:
                    with MultimodalTranslator._STATUS_LOCK:
                        if MultimodalTranslator._STATUS_ACTIVE:
                            print(f"  └─ [OK / Faza 1]: Połączenie z Google API przywrócone.")
                            MultimodalTranslator._STATUS_ACTIVE = False
                            MultimodalTranslator._LAST_STATUS_TIME = 0.0
                    return response.parsed
                else:
                    res = schema_class.model_validate(json.loads(response.text))
                    with MultimodalTranslator._STATUS_LOCK:
                        if MultimodalTranslator._STATUS_ACTIVE:
                            print(f"  └─ [OK / Faza 1]: Połączenie z Google API przywrócone.")
                            MultimodalTranslator._STATUS_ACTIVE = False
                            MultimodalTranslator._LAST_STATUS_TIME = 0.0
                    return res

            except Exception as e:
                err_str = str(e).lower()
                if hasattr(self, "client_pool") and self.client_pool and last_used_client:
                    self.client_pool.report_error(last_used_client, err_str)

                is_cache_err = "403" in err_str or "cachedcontent" in err_str or "permission" in err_str
                if is_cache_err and cached_name:
                    from context_cache import ContextCacheManager
                    ContextCacheManager.invalidate_cache(current_model, self.system_prompt, client=last_used_client, tag="translator")
                    with MultimodalTranslator._STATUS_LOCK:
                        print(f"\n[Context Cache]: Wykryto unieważniony cache serwerowy na kluczu -> automatyczna regeneracja...")
                    cached_name = None
                    time.sleep(0.5)
                    continue

                is_billing_exhausted = "prepayment" in err_str or "depleted" in err_str or ("billing" in err_str and "credit" in err_str)
                if is_billing_exhausted:
                    print("\n" + "!" * 75)
                    print("  [!] [AWARIA KONTA GOOGLE AI STUDIO / PŁATNOŚCI]:")
                    print("  Wyczerpały się środki przedpłacone (Prepayment Credits / Limit wydatków)!")
                    print("  Komunikat Google: 'Your prepayment credits are depleted.'")
                    print("  -> Wejdź na https://aistudio.google.com/ i doładuj środki, aby kontynuować.")
                    print("!" * 75 + "\n")
                    raise RuntimeError("Wyczerpane środki na koncie Google AI Studio (Prepayment Credits Depleted).")

                # Anti-Spin-Lock Circuit Breaker: Hard stop to protect quota and funds
                num_keys = len(self.client_pool.clients) if hasattr(self, "client_pool") and self.client_pool else 1
                max_allowed_attempts = max(25, num_keys * 8)
                if attempt >= max_allowed_attempts:
                    raise RuntimeError(
                        f"ŚCISŁA BLOKADA BEZPIECZEŃSTWA: Osiągnięto limit {attempt} prób dla partii w Fazie 1. "
                        f"Ostatni wyjątek: {e}. Proces wstrzymano w celu ochrony budżetu przed niekontrolowanymi zapytaniami."
                    )

                is_timeout = "504" in err_str or "deadline" in err_str or "timeout" in err_str or "timed out" in err_str
                is_unavailable = "503" in err_str or "unavailable" in err_str or "high demand" in err_str
                is_rate_limit = "429" in err_str or "quota" in err_str or "resource_exhausted" in err_str or "rate" in err_str

                import random
                import time as _time
                if is_unavailable or is_timeout:
                    cycle = attempt // max(1, num_keys)
                    wait_time = min(4.0, 1.5 + 0.5 * min(cycle, 5) + random.uniform(0.1, 0.4))
                else:
                    if attempt % max(1, num_keys) != 0:
                        wait_time = 0.2 + random.uniform(0.05, 0.15)
                    else:
                        cycle = attempt // max(1, num_keys)
                        wait_time = min(3.0, 0.6 + 0.4 * min(cycle, 4) + random.uniform(0.1, 0.3))

                friendly_msg = format_friendly_api_error(e)
                with MultimodalTranslator._STATUS_LOCK:
                    if not MultimodalTranslator._STATUS_ACTIVE:
                        print(f"\n[Status / Faza 1]: {friendly_msg} -> oczekiwanie na serwery Google i automatyczna rotacja kluczy...")
                        MultimodalTranslator._STATUS_ACTIVE = True

                time.sleep(wait_time)

    def _process_single_batch(
        self,
        b_idx: int,
        batch: List[Any],
        untranslated_in_batch: List[Any],
        batches: List[List[Any]],
        video_path: Optional[str],
        is_ass: bool,
        anime_meta: Optional[Dict[str, Any]],
        episode_profile: Optional[Any],
        anime_context_str: str,
        episode_profile_str: str,
        series_bible_str: str,
        manga_canon_str: str,
        combined_glossary: Dict[str, str],
        all_user_rules: List[Any],
        history: List[Dict[str, str]],
        pbar: Any,
        translated_results: Optional[Dict[int, str]] = None
    ) -> Tuple[int, Dict[int, str], Dict[int, str], List[Any], List[Dict[str, Any]], str, str]:
        """
        Translates and refines a single batch of dialogue lines (Thread-Safe).
        """
        # Micro-stagger entry across worker threads to avoid burst gateway collisions on Google TPUs
        if self.concurrent_batches > 1:
            time.sleep((b_idx % self.concurrent_batches) * 0.4)

        # Retrieve upcoming lines (Lookahead Window)
        lookahead_events = []
        if b_idx + 1 < len(batches):
            lookahead_events = batches[b_idx + 1][:4]

        # Retrieve previous lines (Lookback Window / Local Scene Continuity)
        lookback_history = []
        if b_idx > 0 and b_idx - 1 < len(batches):
            prev_batch = batches[b_idx - 1]
            for prev_orig_idx, prev_event, prev_clean_en, _ in prev_batch[-4:]:
                prev_pl = translated_results.get(prev_orig_idx, "") if translated_results else ""
                spk = prev_event.name.strip() if getattr(prev_event, "name", None) else ""
                from verifier import _is_whole_line_italic
                is_th = "italic" in (prev_event.style or "").lower() or _is_whole_line_italic(prev_event.text or "")
                lookback_history.append({
                    "en": prev_clean_en,
                    "pl": prev_pl,
                    "speaker": spk,
                    "is_thought": is_th
                })
        elif history:
            if hasattr(self, "lock"):
                with self.lock:
                    history_snapshot = list(history)
            else:
                history_snapshot = list(history)
            lookback_history = list(history_snapshot[-4:])

        # 2. Extract 3-4 intelligent key video frames for the batch (Storyboard & Visual OCR)
        temp_frames: List[str] = []
        image_contents = []

        if video_path and os.path.exists(video_path):
            raw_timestamps: List[int] = []
            
            # 1. Start line
            raw_timestamps.append((untranslated_in_batch[0][1].start + untranslated_in_batch[0][1].end) // 2)

            # 2. Priority: Signs and On-screen captions for OCR
            for _, ev, clean_txt, ts_pref in untranslated_in_batch:
                vtype = detect_event_visual_type(ev, ts_pref, style_report=getattr(self, "style_report", None))
                if vtype.get("is_sign") or (clean_txt.startswith("[") and clean_txt.endswith("]")):
                    sign_ts = (ev.start + ev.end) // 2
                    raw_timestamps.append(sign_ts)
                    if len(raw_timestamps) >= 4:
                        break

            # 3. Middle / Scene transition frames
            N = len(untranslated_in_batch)
            if N >= 8 and len(raw_timestamps) < 4:
                raw_timestamps.append((untranslated_in_batch[N // 3][1].start + untranslated_in_batch[N // 3][1].end) // 2)
                raw_timestamps.append((untranslated_in_batch[(2 * N) // 3][1].start + untranslated_in_batch[(2 * N) // 3][1].end) // 2)
            elif N >= 3 and len(raw_timestamps) < 3:
                raw_timestamps.append((untranslated_in_batch[N // 2][1].start + untranslated_in_batch[N // 2][1].end) // 2)

            # 4. End of scene / Reaction frame
            if N >= 2 and len(raw_timestamps) < 4:
                raw_timestamps.append((untranslated_in_batch[-1][1].start + untranslated_in_batch[-1][1].end) // 2)

            # Sort and deduplicate timestamps (min 1500ms apart)
            raw_timestamps = sorted(raw_timestamps)
            deduped_ts: List[int] = []
            for ts in raw_timestamps:
                if not deduped_ts or all(abs(ts - existing) >= 1500 for existing in deduped_ts):
                    deduped_ts.append(ts)
                if len(deduped_ts) >= 4:
                    break

            for ts in deduped_ts:
                try:
                    frame_path = extract_frame_at_timestamp(
                        video_path=video_path,
                        timestamp_ms=ts,
                        max_width=self.max_image_width
                    )
                    temp_frames.append(frame_path)
                except Exception:
                    logger.debug("Zapis klatki referencyjnej zakończony wyjątkiem", exc_info=True)

            for fpath in temp_frames:
                try:
                    img = Image.open(fpath)
                    image_contents.append(img)
                except Exception:
                    logger.debug("Wczytanie klatki obrazu zakończone wyjątkiem", exc_info=True)

        # 2b. Extract audio slice and run LOCAL Whisper transcription + Prosody + Diarization (100% offline)
        temp_audio_file = None
        whisper_transcriptions: Dict[int, str] = {}
        prosody_tags: Dict[int, str] = {}
        speaker_tags: Dict[int, str] = {}
        if video_path and os.path.exists(video_path):
            try:
                batch_start = untranslated_in_batch[0][1].start
                batch_end = untranslated_in_batch[-1][1].end
                if 0 < (batch_end - batch_start) <= 360000:
                    temp_audio_file = extract_audio_slice(
                        video_path=video_path,
                        start_ms=batch_start,
                        end_ms=batch_end
                    )
                    events_tuples = [(idx + 1, item[1]) for idx, item in enumerate(untranslated_in_batch)]
                    
                    # 1. Local Whisper transcription with character and terminology context
                    if self.whisper:
                        whisper_prime_keywords = []
                        if anime_meta:
                            t_nat = anime_meta.get("title_native")
                            t_rom = anime_meta.get("title_romaji")
                            if t_nat:
                                whisper_prime_keywords.append(t_nat)
                            elif t_rom:
                                whisper_prime_keywords.append(t_rom)

                        if episode_profile:
                            if getattr(episode_profile, "name_declensions", None):
                                whisper_prime_keywords.extend([nd.character_name for nd in episode_profile.name_declensions if nd.character_name][:6])
                            if getattr(episode_profile, "characters", None):
                                for c in episode_profile.characters:
                                    if getattr(c, "speaker", None):
                                        whisper_prime_keywords.append(c.speaker)
                                    if getattr(c, "listener", None):
                                        whisper_prime_keywords.append(c.listener)

                        # Safe keyword filtering for Japanese Whisper (no Polish characters or role labels)
                        sanitized_kw = []
                        for kw in whisper_prime_keywords:
                            if not kw:
                                continue
                            clean_k = re.sub(r"\(.*?\)", "", kw).strip()
                            if not clean_k or len(clean_k) < 2:
                                continue
                            if re.search(r"[ąćęłńóśźżĄĆĘŁŃÓŚŹŻ]", clean_k):
                                continue
                            if clean_k.lower() in ("mężczyzna", "kobieta", "postać", "narrator", "man", "woman", "unknown", "głos", "dziewczyna", "chłopak"):
                                continue
                            if clean_k not in sanitized_kw:
                                sanitized_kw.append(clean_k)

                        initial_prompt_str = "、".join(sanitized_kw[:8]) if sanitized_kw else None

                        whisper_transcriptions = self.whisper.transcribe_batch_scene(
                            scene_wav_path=temp_audio_file,
                            batch_start_ms=batch_start,
                            events=events_tuples,
                            initial_prompt=initial_prompt_str
                        )
                        # Standard 9.5 (Operacja 2C.3, R3.5): Pętla sanityzacji i deduplikacji czasowej ASR w Kroku 4
                        # Standard 11.1 (LUKA-E3-01): Lokalny stan deduplikacji ASR w obrębie paczki (brak wyścigu wątków)
                        local_asr_last_seen_end_sec: Dict[str, float] = {}
                        local_asr_last_text = ""
                        local_asr_consecutive_streak = 0

                        for b_id, ev in events_tuples:
                            if getattr(ev, "is_sign", False) or str(getattr(ev, "style", "")).lower() in ("sign", "signs", "napis", "napisy") or is_sign_entity(getattr(ev, "name", "")):
                                whisper_transcriptions[b_id] = ""
                                continue

                            raw_txt = whisper_transcriptions.get(b_id, "")
                            raw_s = raw_txt.get("text", "") if isinstance(raw_txt, dict) else str(raw_txt or "")
                            san_txt = EpisodeProfiler.sanitize_event_asr(
                                raw_s,
                                is_sign=getattr(ev, "is_sign", False),
                                style=getattr(ev, "style", None)
                            )
                            cur_start_sec = ev.start / 1000.0
                            cur_end_sec = ev.end / 1000.0
                            norm_jp = re.sub(r"\[.*?\]", "", san_txt).strip()
                            norm_jp = re.sub(r"\s+", "", norm_jp)

                            if norm_jp:
                                if norm_jp == local_asr_last_text:
                                    local_asr_consecutive_streak += 1
                                else:
                                    local_asr_last_text = norm_jp
                                    local_asr_consecutive_streak = 1

                                last_end = local_asr_last_seen_end_sec.get(norm_jp)
                                if last_end is not None and (cur_start_sec - last_end) > 1.5:
                                    san_txt = ""
                                elif local_asr_consecutive_streak > 2:
                                    san_txt = ""
                                else:
                                    local_asr_last_seen_end_sec[norm_jp] = cur_end_sec

                            if isinstance(raw_txt, dict):
                                raw_txt["text"] = san_txt
                                whisper_transcriptions[b_id] = raw_txt
                            else:
                                whisper_transcriptions[b_id] = san_txt

                    # 2. Local prosody analysis (RMS dBFS / whisper / shout)
                    prosody_tags = AudioProsodyEngine.analyze_scene_prosody(
                        wav_path=temp_audio_file,
                        batch_start_ms=batch_start,
                        events=events_tuples
                    )

                    # 3. Local diarization and F0 pitch estimation
                    speaker_tags = SpeakerVoiceClassifier.classify_scene_speakers(
                        wav_path=temp_audio_file,
                        batch_start_ms=batch_start,
                        events=events_tuples
                    )
            except Exception as e:
                pbar.write(f" ├─ [Ostrzeżenie Audio/Whisper]: {e}")
                pass

        if self.flight_recorder:
            try:
                self.flight_recorder.log_acoustics_and_whisper(
                    f0_metrics={"prosody_tags": prosody_tags, "speaker_tags": speaker_tags},
                    whisper_results=whisper_transcriptions
                )
            except Exception:
                logger.debug("Zapis zdarzenia rejestratora fazy 1 zakończony wyjątkiem", exc_info=True)

        # 3. Dynamic contextual rules, user golden feedback, and deterministic glossary
        batch_en_queries = [item[2] for item in untranslated_in_batch]
        relevant_feedback = self.user_feedback.find_relevant_feedback(
            batch_en_queries,
            anime_title=anime_meta.get("title", "") if anime_meta else ""
        )
        user_feedback_str = self.user_feedback.format_for_prompt(relevant_feedback)
        glossary_str = self.glossary_manager.format_for_prompt(combined_glossary)
        batch_items_for_rules = []
        for idx, (orig_idx, ev, clean_txt, ts_pref) in enumerate(untranslated_in_batch):
            b_id = idx + 1
            dur_s = max(0.05, (ev.end - ev.start) / 1000.0)
            cps_val, _ = calculate_cps(clean_txt, ev.start, ev.end)
            style_str = ev.style or ""
            from verifier import _is_whole_line_italic
            is_th = "italic" in style_str.lower() or _is_whole_line_italic(ev.text or "")
            is_internal_monologue = getattr(ev, "is_internal_monologue", False) or is_th
            if is_internal_monologue and not ("italic" in style_str.lower() or "thoughts" in style_str.lower()):
                if is_short_spoken_reply(clean_txt):
                    is_internal_monologue = False
            vtype_info = detect_event_visual_type(ev, ts_pref, style_report=getattr(self, "style_report", None))
            batch_items_for_rules.append({
                "id": b_id,
                "orig_idx": orig_idx,
                "en": clean_txt,
                "audio_jp": (whisper_transcriptions.get(b_id, "") if whisper_transcriptions else "") if not vtype_info["is_sign"] else "",
                "style": style_str,
                "is_thought": is_th,
                "is_internal_monologue": is_internal_monologue,
                "duration_s": dur_s,
                "cps": cps_val,
                "is_sign": vtype_info["is_sign"],
                "speaker_gender": self.character_registry.get(ev.name),
                "speaker": ev.name or "UNKNOWN",
                "speaker_name": ev.name or "UNKNOWN",
                "prosody": (prosody_tags.get(b_id, "") if not vtype_info["is_sign"] else ""),
                "speaker_voice": (speaker_tags.get(b_id, "") if not vtype_info["is_sign"] else ""),
                "is_song": is_song_line(ev, clean_txt)
            })
        focused_rules_str = get_focused_rules_for_batch(batch_items_for_rules, max_rules=3)

        # Dynamic JIT Scoping of Series Bible Context for current batch
        scoped_series_bible_str = series_bible_str
        if getattr(self, "series_bible", None) and hasattr(self.series_bible, "format_scoped_for_batch"):
            batch_corpus = " ".join([item[2] for item in untranslated_in_batch if len(item) > 2])
            lookback_txt = " ".join([h.get("en", "") for h in lookback_history]) if lookback_history else ""
            lookahead_txt = " ".join([item[2] for item in lookahead_events if len(item) > 2]) if lookahead_events else ""
            batch_spks = {item[1].name for item in untranslated_in_batch if len(item) > 1 and getattr(item[1], "name", None)}
            scoped_series_bible_str = self.series_bible.format_scoped_for_batch(
                batch_text=batch_corpus,
                active_speakers=batch_spks,
                lookback_text=lookback_txt,
                lookahead_text=lookahead_txt
            )

        # 3b. Text prompt with AniList knowledge, character registry, lookahead, and phonetic cues
        prompt_text = self._prepare_batch_prompt(
            untranslated_in_batch,
            lookback_history,
            lookahead_events=lookahead_events,
            anime_context_str=anime_context_str,
            episode_profile_str=episode_profile_str,
            episode_profile=episode_profile,
            whisper_transcriptions=whisper_transcriptions,
            series_bible_str=scoped_series_bible_str,
            prosody_tags=prosody_tags,
            speaker_tags=speaker_tags,
            manga_canon_str=manga_canon_str,
            user_feedback_str=user_feedback_str,
            glossary_str=glossary_str,
            focused_rules_str=focused_rules_str
        )

        # 4. Call Gemini (Vision + Whisper text context)
        if whisper_transcriptions:
            jp_raw_list = [
                str(v.get("text", "")).strip() if isinstance(v, dict) else str(v or "").strip()
                for v in whisper_transcriptions.values() if v
            ]
            jp_raw_list = [t for t in jp_raw_list if t]
            if jp_raw_list:
                romaji_samples = [to_romaji(text) for text in jp_raw_list[:2]]
                romaji_line = " | ".join(romaji_samples)
                if len(romaji_line) > 75:
                    romaji_line = romaji_line[:72] + "..."
                pbar.write(f" ├─ [Odsłuch JP] \"{romaji_line}\"")

        # 4. Call Gemini (Vision + Text)
        contents: List[Any] = []
        contents.extend(image_contents)
        contents.append(prompt_text)

        pbar.set_postfix_str("Faza 1 (Wizja + Audio)...")
        t0_phase1 = time.perf_counter()
        batch_response = self._call_gemini_with_retry(
            contents=contents,
            schema_class=BatchTranslationResponse
        )
        elapsed_phase1 = round(max(0.0, time.perf_counter() - t0_phase1), 2)

        if self.flight_recorder:
            try:
                raw_resp = batch_response.model_dump() if hasattr(batch_response, "model_dump") else (batch_response.dict() if hasattr(batch_response, "dict") else str(batch_response))
                p1_tok_usage = None
                _tl = getattr(self, "_thread_local", None)
                _last_tu = getattr(_tl, "last_batch_token_usage", None) if _tl is not None else None
                if _last_tu:
                    p1_tok_usage = dict(_last_tu)
                self.flight_recorder.log_phase1_batch(
                    batch_id=b_idx,
                    prompt_dump=prompt_text,
                    raw_response=raw_resp,
                    response_time_sec=elapsed_phase1,
                    token_usage=p1_tok_usage
                )
            except Exception:
                logger.debug("Rejestracja odpowiedzi modelu zakończona wyjątkiem", exc_info=True)

        # Update global Character Registry with thread lock and safe registration
        with self.lock:
            if batch_response and batch_response.characters_identified:
                for char in batch_response.characters_identified:
                    if char.name:
                        self._register_character_safe(char.name, char.gender, char.role or "postać")
        scene_desc = ""
        if batch_response:
            if getattr(batch_response, "scene_diagnosis", None) and batch_response.scene_diagnosis:
                diag = batch_response.scene_diagnosis
                parts = []
                if getattr(diag, "dramatic_context", None) and diag.dramatic_context.strip():
                    parts.append(f"Kontekst: {diag.dramatic_context.strip()}")
                if getattr(diag, "dialogue_flow", None) and diag.dialogue_flow.strip():
                    parts.append(f"Dynamika: {diag.dialogue_flow.strip()}")
                if getattr(diag, "audio_intent_check", None) and diag.audio_intent_check.strip():
                    parts.append(f"Intencja Audio: {diag.audio_intent_check.strip()}")
                if getattr(diag, "dominant_tone", None) and diag.dominant_tone.strip():
                    parts.append(f"Rejestr: {diag.dominant_tone.strip()}")
                if getattr(diag, "power_dynamic", None) and diag.power_dynamic.strip():
                    parts.append(f"Władza/Status: {diag.power_dynamic.strip()}")
                if getattr(diag, "epistemic_asymmetry", None) and diag.epistemic_asymmetry.strip():
                    parts.append(f"Teoria Umysłu: {diag.epistemic_asymmetry.strip()}")
                if getattr(diag, "table_read_mouth_feel", None) and diag.table_read_mouth_feel.strip():
                    parts.append(f"Próba Stolikowa: {diag.table_read_mouth_feel.strip()}")
                scene_desc = " | ".join(parts)
            elif getattr(batch_response, "scene_description", None):
                scene_desc = batch_response.scene_description or ""

        if scene_desc:
            pbar.write(f" ├─ [Kontekst] {scene_desc}")

        # Clean up temporary frames and audio files
        for fpath in temp_frames:
            try:
                os.remove(fpath)
            except OSError:
                pass
        if temp_audio_file and os.path.exists(temp_audio_file):
            try:
                os.remove(temp_audio_file)
            except OSError:
                pass

        # 5. Process Phase 1 response
        pass1_items = []

        for idx, (orig_idx, event, clean_en, ts_prefix) in enumerate(untranslated_in_batch):
            batch_id = idx + 1
            pl_candidate = ""
            speaker_gender = None
            notes = ""
            vtype = detect_event_visual_type(event, ts_prefix, style_report=getattr(self, "style_report", None))
            cps, is_fast = calculate_cps(clean_en, event.start, event.end)
            cps_warn = f"Tempo CPS: {cps:.1f} (czas {(event.end - event.start)/1000.0:.1f}s)" if is_fast else ""
            condensation_dir = calculate_condensation_directive(clean_en, event.start, event.end)

            visual_sub = ""
            lit_mean = ""
            screen_reg = None
            v_typesetting = None
            ambiguity_note = ""
            semiotic_layer = "spoken_on_screen"
            raw_addressee = None
            has_audio_conflict = False
            has_ambiguity_conflict = False
            has_severe_trap = False
            has_temporal_conflict = False

            # Deterministyczne otaczanie {\i1}...{\i0} dla stylu Italics / myśli (Standard 9.5, 2C.6, R1.9)
            st_ev_lower = str(getattr(event, "style", "")).lower()
            italic_attr = getattr(event, "italic", 0)
            has_italic_style = any(k in st_ev_lower for k in ["italic", "flashback_italic", "thoughts", "internal"]) or italic_attr in (1, -1)
            is_internal_monologue = getattr(event, "is_internal_monologue", False) or has_italic_style
            if is_internal_monologue and not has_italic_style:
                if is_short_spoken_reply(clean_en):
                    is_internal_monologue = False

            if batch_response:
                for tr in batch_response.translations:
                    if tr.id == batch_id:
                        pl_candidate = format_phase1_candidate_text(tr.polish_text, event, is_sign=bool(vtype.get("is_sign")))


                        # Kondensacja krótkich plansz z punktorem (Standard 9.5, 2C.2, R1.5)
                        if vtype.get("is_sign") and ((event.end - event.start) <= 2500):
                            if ("•" in clean_en or "●" in clean_en) and len(clean_en) > 120:
                                first_line_en = clean_en.split(r"\N")[0].split("\n")[0].strip()
                                first_line_pl = pl_candidate.split(r"\N")[0].split("\n")[0].strip()
                                if first_line_pl:
                                    pl_candidate = first_line_pl






                        speaker_gender = tr.speaker_gender
                        raw_addressee = getattr(tr, 'addressee', None)
                        raw_speaker_name = getattr(tr, 'speaker_name', None)
                        semiotic_layer = getattr(tr, 'semiotic_layer', 'spoken_on_screen') or 'spoken_on_screen'
                        screen_reg = getattr(tr, 'screen_region', None)
                        v_typesetting = getattr(tr, 'visual_typesetting', None)
                        visual_sub = getattr(tr, 'visual_subtext', '') or ''
                        lit_mean = getattr(tr, 'literal_meaning', '') or ''
                        notes = f"{getattr(tr, 'visual_clues', '') or ''} {getattr(tr, 'notes', '') or ''}".strip()
                        ambiguity_note = getattr(tr, 'ambiguity_note', '') or ''
                        break

            is_missing_tr = False
            if not pl_candidate:
                pl_candidate = clean_en
                is_missing_tr = True
                notes = f"{notes} [TELEMETRIA: luka_faza_1: kwestia pominięta w szkicu, wymagany przekład z EN i audio JP]".strip()

            # Multimodal Addressee & Plural Group Resolution Engine (0.00 PLN)
            jp_curr_text = whisper_transcriptions.get(batch_id, "") if whisper_transcriptions else ""
            addressee_cat, addressee_label = self._resolve_line_addressee(
                event=event,
                raw_phase1_addressee=raw_addressee,
                batch_events=untranslated_in_batch,
                event_idx=idx,
                whisper_text=jp_curr_text,
                clean_text=clean_en,
                orig_idx=orig_idx,
                lookback_history=lookback_history,
                speaker_tags=speaker_tags,
                prosody_tags=prosody_tags
            )

            # Standard 9.5 (Operacja 2C.1, R3.2): Bezpośrednie wywołanie arbitrate_event_telemetry
            from scene_discourse import SceneDiscourseGraph
            is_fem_scene = (getattr(self, "episode_scene_genders", {}).get(orig_idx) == "kobieta") or getattr(self, "scene_is_female_only", False)

            # Operacja 2B.5: Ochrona jawnego aktora z kolumny Name pliku .ass przed nadpisaniem
            clean_ass_actor = (getattr(event, "name", None) or "").strip()
            effective_raw_actor = raw_speaker_name or event.name
            sb_inst = getattr(self, "series_bible", None)
            if clean_ass_actor and not is_generic_actor_or_category(clean_ass_actor):
                if sb_inst and hasattr(sb_inst, "resolve_character_record"):
                    ass_rec = sb_inst.resolve_character_record(clean_ass_actor)
                    if ass_rec is not None:
                        effective_raw_actor = clean_ass_actor

            disc_telem = SceneDiscourseGraph.arbitrate_event_telemetry(
                event=event,
                series_bible=sb_inst,
                episode_profiler=getattr(self, "profiler", None),
                raw_actor=effective_raw_actor,
                scene_female_only=is_fem_scene,
                target_actor=addressee_label or addressee_cat,
                is_sign=vtype.get("is_sign", False),
                is_internal_monologue=is_internal_monologue
            )
            p0_spk_gram = disc_telem.get("grammatical_gender")
            if p0_spk_gram in ("MASCULINE", "FEMININE"):
                speaker_gender = "mężczyzna" if p0_spk_gram == "MASCULINE" else "kobieta"
                spk_conf = 1.0
                arb_alerts = []
            else:
                resolved_gender, arb_alerts = self._arbitrate_speaker_gender(
                    event=event,
                    raw_phase1_gender=speaker_gender,
                    batch_id=batch_id,
                    speaker_tags=speaker_tags,
                    whisper_transcriptions=whisper_transcriptions,
                    pl_candidate=pl_candidate,
                    raw_speaker_name=raw_speaker_name,
                    event_idx=orig_idx
                )
                speaker_gender = resolved_gender
                is_spk_hypothesis = any("hipoteza_faza_1" in a for a in arb_alerts)
                spk_conf = 0.70 if is_spk_hypothesis else (1.0 if speaker_gender else 0.0)

            if arb_alerts:
                notes = f"{notes} {' '.join(arb_alerts)}".strip()

            is_tgt_hypothesis = bool(addressee_label and "Hipoteza Faza 1" in addressee_label)
            tgt_conf = 0.70 if is_tgt_hypothesis else (1.0 if addressee_cat else 0.0)

            # Declarative Scene State Telemetry Vector (Standard 7.0 SSOT / 9.5 / 9.8)
            spk_gram_tag = p0_spk_gram if p0_spk_gram in ("MASCULINE", "FEMININE") else (
                "MASCULINE" if speaker_gender and any(w in str(speaker_gender).lower() for w in ["male", "mężczyzna", "chłopak"]) else (
                    "FEMININE" if speaker_gender and any(w in str(speaker_gender).lower() for w in ["female", "kobieta", "dziewczyna"]) else None
                )
            )
            p0_tgt_gram = disc_telem.get("target_gender")
            tgt_gram_tag = p0_tgt_gram if p0_tgt_gram in ("MASCULINE", "FEMININE") else (
                "FEMININE" if addressee_cat in ["kobieta", "kobieta_dual", "grupa_kobiet"] else (
                    "MASCULINE" if addressee_cat in ["mężczyzna", "mężczyzna_dual", "grupa_mężczyzn"] else None
                )
            )

            has_male_speaker_in_line = (
                spk_gram_tag == "MASCULINE"
                or speaker_gender == "mężczyzna"
            )
            has_male_addressee_in_line = (
                tgt_gram_tag == "MASCULINE"
                or addressee_cat in ["mężczyzna", "mężczyzna_dual", "grupa_mężczyzn"]
            )
            if has_male_speaker_in_line:
                is_fem_scene = False

            if is_fem_scene:
                line_pl_grp = "NON_VIRILE"
                line_you_grp = "VIRILE" if (has_male_addressee_in_line or addressee_cat in ["grupa_mężczyzn", "mężczyzna_dual", "grupa_mieszana", "para_mieszana_dual"]) else ("NON_VIRILE" if addressee_cat in ["grupa_kobiet", "kobieta_dual"] else "AMBIGUOUS")
            else:
                line_pl_grp = "VIRILE" if (has_male_speaker_in_line or addressee_cat in ["grupa_mężczyzn", "mężczyzna_dual", "grupa_mieszana", "para_mieszana_dual"] or getattr(self, "scene_has_male", False)) else ("NON_VIRILE" if addressee_cat in ["grupa_kobiet", "kobieta_dual"] else "AMBIGUOUS")
                line_you_grp = "VIRILE" if (has_male_addressee_in_line or addressee_cat in ["grupa_mężczyzn", "mężczyzna_dual", "grupa_mieszana", "para_mieszana_dual"]) else ("NON_VIRILE" if addressee_cat in ["grupa_kobiet", "kobieta_dual"] else "AMBIGUOUS")

            if has_male_speaker_in_line and line_pl_grp == "NON_VIRILE":
                line_pl_grp = "VIRILE"

            batch_actors_f2 = {getattr(b_ev, "name", "") for _, b_ev, _, _ in untranslated_in_batch if getattr(b_ev, "name", "") and not is_generic_actor_or_category(getattr(b_ev, "name", ""))}
            poly_val_f2 = getattr(self, "episode_scene_polylogues", {}).get(orig_idx)
            if not poly_val_f2 and len(batch_actors_f2) >= 3:
                poly_val_f2 = f"POLYLOGUE (n={len(batch_actors_f2)})"
            resolved_spk_name = disc_telem.get("speaker_name") or raw_speaker_name or event.name or "UNKNOWN"
            resolved_tgt_name = disc_telem.get("target_actor") or (addressee_label if addressee_label else None)
            if is_internal_monologue:
                resolved_tgt_name = None
                tgt_gram_tag = None

            line_dry_telemetry = format_dry_telemetry_tag(
                speaker_gender=spk_gram_tag,
                speaker_confidence=spk_conf,
                target_gender=tgt_gram_tag,
                target_confidence=1.0 if p0_tgt_gram in ("MASCULINE", "FEMININE") else tgt_conf,
                plural_group_gender=line_pl_grp if line_pl_grp != "AMBIGUOUS" else None,
                plural_confidence=1.0 if line_pl_grp != "AMBIGUOUS" else 0.0,
                you_group_gender=line_you_grp if line_you_grp != "AMBIGUOUS" else None,
                you_group_confidence=1.0 if line_you_grp != "AMBIGUOUS" else 0.0,
                speaker_name=resolved_spk_name,
                target_name=resolved_tgt_name,
                polylogue=poly_val_f2
            )
            if line_dry_telemetry:
                notes = f"{notes} {line_dry_telemetry}".strip()

            # Line-Level Pinning: Direct Profiler alerts for this specific line
            pinned_alerts = getattr(self, "profile_line_alerts", {}).get(orig_idx) or getattr(self, "profile_line_alerts", {}).get(idx)
            if pinned_alerts:
                for pa in pinned_alerts:
                    notes = f"{notes} {pa}".strip()
            elif episode_profile:
                if getattr(episode_profile, "danger_lines_prescan", None):
                    for dl in episode_profile.danger_lines_prescan:
                        if dl.english_phrase and dl.english_phrase.lower() in clean_en.lower():
                            guide = getattr(dl, "contextual_guidance", "")
                            trap_tag = f"[TELEMETRIA: pułapka_profilera: {dl.contextual_trap} | wskazówka: {guide}]"
                            notes = f"{notes} {trap_tag}".strip()
                            break
                if getattr(episode_profile, "character_catchphrases", None):
                    for cp in episode_profile.character_catchphrases:
                        if cp.original_phrase and cp.original_phrase.lower() in clean_en.lower():
                            cp_tag = f"[💬 KWESTIA-WIZYTÓWKA: '{cp.canonical_pl}']"
                            notes = f"{notes} {cp_tag}".strip()
                            break
                if getattr(episode_profile, "puns_and_wordplays", None):
                    for pun in episode_profile.puns_and_wordplays:
                        if pun.original_joke_or_pun and pun.original_joke_or_pun.lower() in clean_en.lower():
                            pun_tag = f"[🃏 GRA SŁOWNA: {pun.polish_transcreation}]"
                            notes = f"{notes} {pun_tag}".strip()
                            break

            # 3rd-person character mention detection (Filar CLXII)
            subj_3p = detect_third_person_mentions(
                clean_text=clean_en,
                speaker=event.name,
                character_registry=self.character_registry,
                series_bible=getattr(self, "series_bible", None)
            )
            subj_3p_str = " ".join(subj_3p) if subj_3p else ""

            if vtype["is_sign"]:
                raw_jp_cand = ""
                jp_text = ""
                romaji_str = ""
                audio_jp_str = ""
            else:
                raw_jp_cand = whisper_transcriptions.get(batch_id, "") if whisper_transcriptions else ""
                jp_text = str(raw_jp_cand.get("text", "")).strip() if isinstance(raw_jp_cand, dict) else str(raw_jp_cand or "").strip()
                romaji_str = to_romaji(jp_text) if jp_text else ""
                audio_jp_str = f"{jp_text} [{romaji_str}]" if romaji_str and romaji_str != jp_text else jp_text

            semantic_anchor = get_audio_semantic_anchor(jp_text, clean_en)
            if semantic_anchor and not lit_mean:
                lit_mean = f"[KOTWICA AUDIO]: {semantic_anchor}"

            audio_discrepancy_msg = detect_audio_discrepancy(audio_jp_str, pl_candidate, clean_en, prosody=prosody_tags.get(batch_id, ""))
            pragmatic_reg = detect_japanese_pragmatic_register(audio_jp_str, clean_en)

            # Ping-pong dialogowy (Filar CXLVI & XLIII) oraz Ciągłość Międzybatchowa
            relation_tag = ""
            prev_clean = ""
            prev_clean_lower = ""
            prev_pl = ""
            prev_jp = ""
            prev_is_thought = False
            curr_is_affirmation = False
            is_prev_directive = False
            is_prev_wh = False
            is_prev_neg_q = False

            prev_ev_end = None
            time_gap_ms = 0
            time_gap_s = 0.0
            try:
                if idx > 0 and not vtype["is_sign"]:
                    prev_clean = untranslated_in_batch[idx - 1][2].strip()
                    prev_clean_lower = prev_clean.lower()
                    prev_pl = pass1_items[idx - 1].get("pl", "").lower() if idx - 1 < len(pass1_items) else ""
                    prev_jp = pass1_items[idx - 1].get("audio_jp", "").lower() if idx - 1 < len(pass1_items) else ""
                    prev_is_thought = pass1_items[idx - 1].get("is_thought", False) if idx - 1 < len(pass1_items) else False
                    prev_ev_end = untranslated_in_batch[idx - 1][1].end
                elif idx == 0 and b_idx > 0 and b_idx - 1 < len(batches) and not vtype["is_sign"]:
                    # Cross-batch continuity: pobierz ostatnią kwestię z poprzedniego batcha
                    prev_batch = batches[b_idx - 1]
                    if prev_batch:
                        last_item = prev_batch[-1]
                        prev_clean = last_item[2].strip() if len(last_item) > 2 else ""
                        prev_clean_lower = prev_clean.lower()
                        prev_orig_idx = last_item[0]
                        prev_pl = (translated_results.get(prev_orig_idx, "") if translated_results else "").lower()
                        prev_event = last_item[1]
                        prev_is_thought = "italic" in (prev_event.style or "").lower() or r"\i1" in (prev_event.text or "")
                        prev_ev_end = prev_event.end
                elif idx == 0 and lookback_history and not vtype["is_sign"]:
                    prev_h = lookback_history[-1]
                    prev_clean = prev_h.get("en", "").strip()
                    prev_clean_lower = prev_clean.lower()
                    prev_pl = prev_h.get("pl", "").lower()
                    prev_is_thought = prev_h.get("is_thought", False)
                    prev_ev_end = prev_h.get("end_ms")

                if prev_ev_end is not None:
                    time_gap_ms = max(0, event.start - prev_ev_end)
                    time_gap_s = time_gap_ms / 1000.0

                is_shot_cut = False
                cuts_list = getattr(self, "scene_cuts_ms", None) or []
                if cuts_list and prev_ev_end is not None:
                    from scene_snapper import SceneShotSnapper
                    is_shot_cut = SceneShotSnapper.is_shot_boundary(event.start, prev_ev_end, cuts_list)

                if prev_clean or is_shot_cut:
                    # Sprawdź dyskontinuitet czasowy i przeskoki scen (Filar CLXV)
                    is_prev_private_request = any(
                        w in prev_clean_lower for w in ["in private", "talk alone", "on our own", "somewhere quiet", "alone"]
                    ) or any(
                        w in prev_pl for w in ["na osobności", "w cztery oczy", "porozmawiać", "pogadać", "w ustronne"]
                    )
                    is_curr_delayed_agreement = any(
                        clean_en.lower().strip().startswith(w) for w in ["sure,", "sure.", "sure!", "all right,", "all right.", "yeah, what", "ok, what", "okay, what"]
                    )

                    if is_shot_cut or (time_gap_ms >= 3800 and (is_prev_private_request or is_curr_delayed_agreement)):
                        relation_tag = f"[🎬 CIĘCIE SCENY (FFmpeg) / DYSKONTINUITET CZASOWY: Pauza {time_gap_s:.1f}s / Nowa scena (Filar CLXV) – postacie zmieniły lokację; otwarcie nowej rozmowy]"
                    elif is_shot_cut or (time_gap_ms >= 3800 and not (prev_clean.endswith("...") or prev_clean.endswith("—") or prev_clean.endswith("-"))):
                        relation_tag = f"[🎬 CIĘCIE SCENY (FFmpeg) / ZMIANA SCENY: Pauza {time_gap_s:.1f}s – nowa sekwencja (Filar CLXV); zresetuj kontekst emocjonalny i spójniki z poprzedniej sceny]"
                    else:
                        # Sprawdź, czy poprzednia linijka to dyrektywa/ostrzeżenie/polecenie
                        is_prev_directive = any(
                            w in prev_clean_lower for w in [
                                "watch your step", "be careful", "watch out", "look out", "mind the",
                                "careful", "hold on", "wait", "listen", "don't move", "hurry", "stay back",
                                "follow me", "step back", "take care"
                            ]
                        ) or any(
                            w in prev_pl for w in [
                                "uważaj", "uważajcie", "ostrożnie", "czekaj", "zaczekaj", "poczekaj",
                                "stój", "stójcie", "nie ruszaj", "pospiesz", "chodź", "chodźcie", "ruszaj",
                                "trzymaj się"
                            ]
                        ) or any(
                            w in prev_jp for w in [
                                "ki o tsukete", "kiwotsukete", "abunai", "chotto matte", "mate",
                                "tomare", "ugoku na", "hayaku", "気をつけ", "危ない", "待って", "止まれ"
                            ]
                        )

                        # Czy bieżąca kwestia to potwierdzenie afirmatywne (tak/hai/yes)?
                        curr_is_affirmation = any(
                            clean_en.lower().strip().startswith(w) for w in ["yes", "y-yes", "yeah", "yep", "right", "okay", "ok"]
                        ) or any(
                            w in audio_jp_str.lower() for w in ["hai", "はい", "ee", "ええ", "un", "うん"]
                        )

                        is_prev_wh = prev_clean.endswith("?") and (
                            any(w in prev_clean_lower for w in ["what", "where", "why", "how", "who", "when", "which", "whose", "whom"]) or
                            bool(re.search(r"\b(dokąd|gdzie|skąd|kiedy|dlaczego|czemu|po\s+co|kto|kogo|komu|kim|co|czego|czym|jak|jaki|jaka|jakie|jakim|jakich|o\s+co|o\s+czym|z\s+kim)\b", prev_pl, re.IGNORECASE))
                        )

                        is_prev_neg_q = prev_clean.endswith("?") and (
                            any(w in prev_clean_lower for w in ["don't", "aren't", "didn't", "can't", "won't", "haven't", "isn't"]) or
                            bool(re.search(r"\bnie\s+(jest|jesteś|jesteście|są|był|była|było|byli|byłeś|byłaś|będzie|będziesz|będą|ma|masz|macie|chcesz|chce|chcecie|wiesz|wie|wiecie|możesz|może|możecie|idziesz|idzie|idziecie|zrobisz|mówisz|widzisz|słyszysz)\b", prev_pl, re.IGNORECASE))
                        )

                        if is_prev_directive and curr_is_affirmation:
                            relation_tag = "[PING-PONG DIALOGOWY: Odpowiedź na ostrzeżenie/dyrektywę – po polsku naturalnie: 'Dobrze / D-Dobrze / Jasne / Będę uważać / W porządku' (Filar CXLVI & XLIII)]"
                        elif is_prev_wh and curr_is_affirmation:
                            relation_tag = "[PING-PONG DIALOGOWY: Odpowiedź na pytanie otwarte – w japońskim audio seiyū padło wahanie: użyj 'Eee...' / 'E-Eee...' / 'Cóż...' (Filar CXLVI)]"
                        elif is_prev_neg_q and curr_is_affirmation:
                            relation_tag = "[PING-PONG DIALOGOWY: Odpowiedź na pytanie z przeczeniem (Echo Agreement) – w japońskim audio seiyū potwierdza przeczenie ('Hai/Un' = racja, nie jest tak); po polsku odpowiadamy na fakt: 'Nie / Nie idę / Wcale nie / Skądże' (Filar CLIV)]"
                        elif prev_clean.endswith("?"):
                            relation_tag = "[PING-PONG DIALOGOWY: Odpowiedź/riposta na pytanie - zgraj leksykę i emocję (Filar CXLVI)]"
                        elif any(prev_clean_lower.startswith(w) for w in ["come,", "let's", "shall we", "look,", "hey,"]):
                            relation_tag = "[PING-PONG DIALOGOWY: Reakcja na propozycję/zaczepkę (Filar CXLVI)]"
                        elif prev_clean.endswith("...") or prev_clean.endswith("…"):
                            relation_tag = "[PING-PONG DIALOGOWY: Prawdopodobna kontynuacja myśli urwanej wielokropkiem (...)]"

                    # Whisper JP-First Semantic Override & Anti-Pivot Cliché Detection (Filar CLXVI)
                    is_en_cliche = any(clean_en.lower().strip().startswith(w) for w in ["sure", "all right", "yeah", "here", "i'm fine", "i am fine", "wait"])
                    has_jp_affirmation = any(tok in jp_text.lower() for tok in ["hai", "ee", "un", "wakatta", "はい", "ええ", "うん", "分かった"])
                    if is_en_cliche and not has_jp_affirmation and jp_text:
                        if any(tok in jp_text.lower() for tok in ["nani", "dou shita", "doushita", "nan da", "何", "どうした", "なんだ"]):
                            relation_tag = f"{relation_tag} [TELEMETRIA: klisza_fansuberska: w audio pytanie '{jp_text}']".strip()
                        elif len(clean_en.split()) <= 2 and any(w == "here" for w in re.findall(r"\b[a-zA-Z]+\b", clean_en.lower())) and any(tok in jp_text.lower() for tok in ["yoisho", "dokkoisho", "hora", "douzo"]):
                            relation_tag = f"{relation_tag} [TELEMETRIA: szum_kinezjatyczny: gest/kakegoe seiyū]".strip()
            except Exception:
                relation_tag = ""

            dur_s = max(0.05, (event.end - event.start) / 1000.0)
            style_str = event.style or ""
            from verifier import _is_whole_line_italic
            is_th = "italic" in style_str.lower() or _is_whole_line_italic(event.text or "")
            is_internal_monologue = getattr(event, "is_internal_monologue", False) or is_th
            if is_internal_monologue and not ("italic" in style_str.lower() or "thoughts" in style_str.lower()):
                if is_short_spoken_reply(clean_en):
                    is_internal_monologue = False

            # Bariera Zmiany Mówcy i Stylu (Thought-to-Speech Firewall)
            if prev_is_thought and not is_th and audio_jp_str and not vtype["is_sign"]:
                boundary_alert = "[⚠️ ZMIANA TRYBU: Koniec myśli wewnętrznej! Ta kwestia to dialog na głos w kadrze – styl prosty bez kursywy {\\i1}, żywa mowa dialogowa!]"
                relation_tag = f"{relation_tag} {boundary_alert}".strip()

            # Dynamic Crowd vs 1-on-1 (Uchi-Soto & Crowd Density Tracker)
            social_context = detect_scene_social_context(
                batch_events=untranslated_in_batch,
                history_context=lookback_history,
                lookahead_events=lookahead_events,
                character_registry=self.character_registry,
                series_bible=getattr(self, "series_bible", None)
            )
            if social_context and not vtype["is_sign"]:
                relation_tag = f"{relation_tag} {social_context}".strip()

            # Dynamic Emotional Breakdown & Affective Primacy Engine (0.00 PLN)
            breakdown_alert = AudioProsodyEngine.detect_emotional_breakdown(
                prosody_tag=prosody_tags.get(batch_id, ""),
                whisper_text=jp_text
            )
            if breakdown_alert and not vtype["is_sign"]:
                relation_tag = f"{relation_tag} {breakdown_alert}".strip()
                notes = f"{notes} {breakdown_alert}".strip()

            # Blind-Drafting on Conflict Engine & Syntactic Calque Scorer (0.00 PLN)
            # Detect whether Phase 1 draft is at severe risk of anchoring bias
            has_audio_conflict = bool(audio_discrepancy_msg) or any(
                k in audio_jp_str.lower() for k in ["hitori", "一人", "独り", "betsuni", "別に", "yokatta", "よかった", "yatta", "やった"]
            )
            has_ambiguity_conflict = bool(ambiguity_note)
            has_severe_trap = bool(notes and any(k in notes for k in ["[TELEMETRIA: pułapka_profilera", "[TELEMETRIA: relacja", "[TELEMETRIA: klisza"]))
            has_temporal_conflict = bool(relation_tag and ("DYSKONTINUITET CZASOWY" in relation_tag or "klisza_fansuberska" in relation_tag))
            calque_score = calculate_syntactic_calque_score(clean_en, pl_candidate) if not is_missing_tr else 0.0
            is_blind_draft = determine_blind_draft_status(
                has_audio_conflict=has_audio_conflict,
                has_ambiguity_conflict=has_ambiguity_conflict,
                has_severe_trap=has_severe_trap,
                has_temporal_conflict=has_temporal_conflict,
                calque_score=calque_score
            )

            clean_ev_name = event.name.strip() if getattr(event, "name", None) else ""
            resolved_spk_name = clean_ev_name or (raw_speaker_name.strip() if raw_speaker_name else "")
            if is_generic_actor_or_category(resolved_spk_name):
                resolved_spk_name = ""

            # Line-Level Active Manga Canon Pinning (Point 1 of Manifesto)
            manga_canon_line_alerts = []
            active_canon_terms = getattr(self, "combined_glossary", {})
            if active_canon_terms:
                en_low = clean_en.lower()
                for t_src, t_trg in active_canon_terms.items():
                    if t_src and len(t_src) >= 3 and t_src.lower() in en_low:
                        manga_canon_line_alerts.append(f"'{t_src}' => '{t_trg}'")
            manga_canon_line_str = " | ".join(manga_canon_line_alerts[:3]) if manga_canon_line_alerts else ""

            p2_paradigms: List[str] = []
            if resolved_spk_name and len(resolved_spk_name) >= 3:
                sb_inst = getattr(self, "series_bible", None)
                par = None
                if sb_inst and hasattr(sb_inst, "get_declension_paradigm"):
                    par = sb_inst.get_declension_paradigm(resolved_spk_name)
                if not par:
                    ent_g = "MALE" if (speaker_gender and any(w in str(speaker_gender).lower() for w in ["male", "mężczyzna", "chłopak"])) else ("FEMALE" if (speaker_gender and any(w in str(speaker_gender).lower() for w in ["female", "kobieta", "dziewczyna"])) else "UNKNOWN")
                    par = DeclensionParadigm.create_for_name(resolved_spk_name, gender=ent_g)
                if par:
                    p2_paradigms.append(f"{resolved_spk_name}(D:{par.D}, C:{par.C}, B:{par.B}, N:{par.N}, Ms:{par.Ms}, W:{par.W})")

            if pass1_items:
                prev_line_f1 = pass1_items[-1].get("pl", "")
                prev_line_en = pass1_items[-1].get("en", "")
            elif lookback_history:
                prev_line_f1 = lookback_history[-1].get("pl", "")
                prev_line_en = lookback_history[-1].get("en", "")
            else:
                prev_line_f1 = ""
                prev_line_en = ""

            pass1_items.append({
                "id": batch_id,
                "orig_idx": orig_idx,
                "event": event,
                "style": style_str,
                "is_thought": is_th,
                "is_internal_monologue": is_internal_monologue,
                "is_missing_translation": is_missing_tr,
                "is_blind_draft": is_blind_draft,
                "calque_score": calque_score,
                "duration_s": dur_s,
                "time_gap_s": time_gap_s,
                "time_gap_ms": time_gap_ms,
                "cps": cps,
                "start_ms": event.start,
                "end_ms": event.end,
                "en": clean_en,
                "pl": pl_candidate,
                "prev_line_f1": prev_line_f1,
                "prev_line_en": prev_line_en,
                "speaker_name": resolved_spk_name,
                "speaker_gender": speaker_gender if spk_conf >= 0.95 else None,
                "speaker_confidence": spk_conf,
                "raw_speaker_gender_hypothesis": speaker_gender if spk_conf < 0.95 else None,
                "addressee": addressee_cat if tgt_conf >= 0.95 else None,
                "target_gender": addressee_cat if tgt_conf >= 0.95 else None,
                "target_confidence": tgt_conf,
                "raw_addressee_hypothesis": addressee_cat if tgt_conf < 0.95 else None,
                "addressee_label": addressee_label,
                "telemetry_tag": line_dry_telemetry,
                "declension_paradigms": p2_paradigms,
                "semiotic_layer": semiotic_layer,
                "screen_region": screen_reg,
                "visual_typesetting": v_typesetting,
                "speaker_voice": speaker_tags.get(batch_id, ""),
                "prosody": prosody_tags.get(batch_id, ""),
                "audio_jp": audio_jp_str,
                "audio_alert": audio_discrepancy_msg or "",
                "ambiguity_note": ambiguity_note or "",
                "canonical_glossary_term": manga_canon_line_str,
                "relation_tag": relation_tag,
                "pragmatic_register": pragmatic_reg or "",
                "visual_subtext": visual_sub or "",
                "literal_meaning": lit_mean or "",
                "cps_warning": cps_warn,
                "condensation_directive": condensation_dir or "",
                "notes": notes,
                "third_person_subject": subj_3p_str,
                "plural_group_gender": line_pl_grp,
                "you_group_gender": line_you_grp,
                "semantic_anchor": semantic_anchor or "",
                "is_sign": vtype["is_sign"],
                "visual_type": vtype["type_label"],
                "visual_details": vtype["visual_details"],
                "is_song": is_song_line(event, clean_en)
            })

        # Determine speakers and scene-level informal status (Filar CLVII - T-V Invariance & Honorific Vocative Shield)
        speakers_on_ty = set()
        speakers_formal = set()
        scene_has_first_name_vocative = False
        for it in pass1_items:
            pl_cand = it.get("pl", "")
            en_txt = it.get("en", "")
            spk = (it.get("speaker_name") or "").strip()
            
            # Detect formal honorific address in line: "Panie Janie", "Pani Mario", "Mistrzu Janie"
            has_formal_vocative = bool(re.search(
                r"\b(panie|pani|panno|panu|pana|mistrzu|lordzie|książę|panienko|profesorze|doktorze)\s+([A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]+)\b",
                pl_cand,
                re.IGNORECASE
            )) or bool(re.search(
                r"\b(lord|master|lady|sir|madam|doctor|professor)\s+([A-Z][a-z]+)\b",
                en_txt,
                re.IGNORECASE
            ))
            if has_formal_vocative and spk:
                speakers_formal.add(spk)

            # Detect true first-name vocative in PL or EN (bare name direct address)
            # Must NOT be preceded by "Panie / Pani / Mr. / Ms." or formal titles
            first_name_match = re.search(r"(?<!\b[Pp]anie\s)(?<!\b[Pp]ani\s)(?<!\b[Pp]anno\s)(?<!\b[Pp]anu\s)(?<!\b[Mm]istrzu\s)(?<!\b[Ll]ordzie\s)\b([A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]{2,})[,?!]", pl_cand) or re.search(r"(?<!\b[Mm]r\.\s)(?<!\b[Mm]s\.\s)(?<!\b[Mm]rs\.\s)(?<!\b[Ll]ord\s)(?<!\b[Mm]aster\s)(?<!\b[Ll]ady\s)\b([A-Z][a-z]{2,})[,?!]", en_txt)
            if first_name_match and not has_formal_vocative:
                voc_word = first_name_match.group(1).lower()
                if voc_word not in ["proszę", "przepraszam", "panie", "pani", "panno", "panu", "sensei", "senpai", "mistrzu", "ojcze", "matko", "mamo", "tato", "bądź", "daj", "stój", "wait", "look", "what", "why", "stop", "sorry", "excuse"]:
                    scene_has_first_name_vocative = True
                    if spk:
                        speakers_on_ty.add(spk)
            
            # Detect informal Polish phrasing: "wiesz", "zobacz", "nie mów", "poczekaj", "daj spokój"
            if not has_formal_vocative and re.search(r"\b(zobacz|spójrz|czekaj|poczekaj|powiedz|nie\s+mów|wiesz|słuchaj|daj\s+spokój|nie\s+bądź|twój|twoja|twoje|cię|ciebie|tobą|tobie)\b", pl_cand, re.IGNORECASE):
                if spk:
                    speakers_on_ty.add(spk)

        # Line-level address drift pinning before Phase 2 Verifier
        for it in pass1_items:
            spk = (it.get("speaker_name") or "").strip()
            has_formal_voc = bool(re.search(
                r"\b(panie|pani|panno|panu|pana|mistrzu|lordzie|książę|panienko)\s+([A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]+|doktorze|profesorze|inspektorze|prezesie|dyrektorze|kierowniku|komisarzu)\b",
                it["pl"],
                re.IGNORECASE
            ))
            has_formal_address_in_line = has_formal_voc or bool(re.search(r"\b(niech\s+(pan|pani)|dziękuję\s+(panu|pani)|proszę\s+(pana|pani)|(pana|pani)\s+zdaniem)\b", it["pl"], re.IGNORECASE))
            if not has_formal_address_in_line and spk not in speakers_formal:
                is_item_informal = (spk in speakers_on_ty) if spk else (scene_has_first_name_vocative and not bool(re.search(r"\b(pan|pani|panu|pana)\b", it["pl"], re.IGNORECASE)))
                if is_item_informal:
                    if re.search(r"\b(wygrał|wygrała|zrobił|zrobiła|widział|widziała|powiedział|powiedziała|słyszał|słyszała|był|była|miał|miała|chciał|chciała|mógł|mogła|wiedział|wiedziała|wie|widzi|myśli|mówi|ma)\s+(pan|pani)\b|\b(pan|pani)\s+(wygrał|wygrała|zrobił|zrobiła|widział|widziała|słyszał|słyszała|powiedział|powiedziała|wie|widzi|myśli|mówi)\b", it["pl"], re.IGNORECASE):
                        target_addr = (it.get("addressee") or "").lower()
                        is_female_target = "kobieta" in target_addr or (it.get("addressee_label") and "kobieta" in it["addressee_label"].lower())
                        drift_alert = "[TELEMETRIA: relacja_na_ty: rejestr_bezpośredni]"
                        it["notes"] = f"{it.get('notes', '')} {drift_alert}".strip()

            # Multimodal Addressee Warning Pinning (Filar CLXIII):
            # Handled via structured attributes it['addressee'] & it['addressee_label'] in SSOT prompt generator.

            # Auditory Anchor Pinning (Filar CLVIII)
            audio_jp_str = str(it.get("audio_jp", "")).lower()
            if audio_jp_str and not it.get("is_sign"):
                pl_check = str(it.get("pl", "")).lower()
                if any(k in audio_jp_str for k in ["hitori", "一人", "独り", "ひとり"]) and ("daj mi spokój" in pl_check or "dajcie mi spokój" in pl_check):
                    it["notes"] = f"{it.get('notes', '')} [TELEMETRIA: audio_anchor=Hitori (samotność)]".strip()
                elif any(k in audio_jp_str for k in ["betsuni", "別に"]) and ("to nic takiego" in pl_check or "nie ma sprawy" in pl_check):
                    it["notes"] = f"{it.get('notes', '')} [TELEMETRIA: audio_anchor=Betsuni (chłód/dystans)]".strip()
                elif any(k in audio_jp_str for k in ["yokatta", "よかった", "良かった"]) and "to było dobre" in pl_check:
                    it["notes"] = f"{it.get('notes', '')} [TELEMETRIA: audio_anchor=Yokatta (ulga)]".strip()
                elif any(k in audio_jp_str for k in ["yatta", "やった"]) and ("zrobiłem to" in pl_check or "zrobiłam to" in pl_check):
                    it["notes"] = f"{it.get('notes', '')} [TELEMETRIA: audio_anchor=Yatta (triumf)]".strip()

            # Focalization & Dramatic Irony Guard (Filar CLXI)
            clean_en_lower = str(it.get("en", "")).lower()
            pl_check = str(it.get("pl", "")).lower()
            audio_jp_str = str(it.get("audio_jp", "")).lower()

            # Check 1: 3rd person in source (EN/JP) turned into 1st person in PL candidate
            has_3rd_person_source = any(tok in clean_en_lower for tok in ["by the", "written by", "paper by", "essay by"]) and not any(tok in clean_en_lower for tok in ["my ", "i ", "me ", "mine"])
            has_1st_person_pl = bool(re.search(r"\b(mój|moja|moje|moim|moich|moją|mego)\s+(esej|praca|artykuł|traktat|tekst)\b", pl_check))
            if has_3rd_person_source and has_1st_person_pl:
                focal_alert = "[TELEMETRIA: tożsamość_incognito: 3. osoba mówcy]"
                it["notes"] = f"{it.get('notes', '')} {focal_alert}".strip()

            # Check 2: Unsolicited thought italicization
            orig_ev = it.get("event")
            orig_ev_text = orig_ev.text if orig_ev and getattr(orig_ev, "text", None) else it.get("en", "")
            if r"\i1" not in orig_ev_text and not it.get("is_thought", False):
                if r"\i1" in str(it.get("pl", "")) and audio_jp_str:
                    unsolicited_italics_alert = "[TELEMETRIA: dialog_diegetyczny: mowa na głos bez kursywy]"
                    it["notes"] = f"{it.get('notes', '')} {unsolicited_italics_alert}".strip()

        # 6. Optional Phase 2 Verifier (Script Doctor - 100% Guaranteed Verification)
        batch_results: Dict[int, str] = {}
        batch_regions: Dict[int, str] = {}
        refined_dict: Dict[int, str] = {it["id"]: sanitize_sub_text(it["pl"]) for it in pass1_items}
        refined_region_dict: Dict[int, str] = {it["id"]: it.get("screen_region") for it in pass1_items if it.get("screen_region")}
        refined_typesetting_dict: Dict[int, Any] = {it["id"]: it.get("visual_typesetting") for it in pass1_items if it.get("visual_typesetting")}

        cot_info_str = ""
        if self.enable_verifier and hasattr(self, 'verifier'):
            budget_val = getattr(self.verifier, "calculate_effective_budget", lambda items: getattr(self.verifier, "thinking_budget", 2048))(pass1_items)
            model_tag = "Flash" if "flash" in getattr(self.verifier, "model", "").lower() else "Pro"
            cot_info_str = f"Faza 2 (Redakcja {model_tag} CoT: {budget_val})"
            with self.lock:
                pbar.set_postfix_str(f"{cot_info_str}...")
                pbar.refresh()
            pbar.write(f" ├─ [{cot_info_str}]")
            # Staggered entry (350ms per thread) to prevent simultaneous TPU burst collisions on 503
            stagger_sec = (b_idx % max(1, self.concurrent_batches)) * 0.35
            if stagger_sec > 0:
                time.sleep(stagger_sec)
            phase2_focused_rules = get_focused_rules_for_batch(pass1_items, max_rules=3)
            refined_lines: List[RefinedLine] = self.verifier.verify_batch(
                batch_items=pass1_items,
                scene_summary=scene_desc or "",
                episode_profile_str=episode_profile_str,
                user_feedback_str=user_feedback_str,
                glossary_str=glossary_str,
                focused_rules_str=phase2_focused_rules,
                series_bible_str=scoped_series_bible_str,
                manga_canon_str=manga_canon_str,
                history_context=lookback_history,
                lookahead_events=lookahead_events,
                character_registry=self.character_registry,
                scene_diagnosis=getattr(batch_response, "scene_diagnosis", None) if batch_response else None
            )
            refined_dict.update({r.id: sanitize_sub_text(r.refined_pl) for r in refined_lines})
            refined_region_dict.update({r.id: r.screen_region for r in refined_lines if getattr(r, 'screen_region', None)})
            refined_typesetting_dict.update({r.id: r.visual_typesetting for r in refined_lines if getattr(r, 'visual_typesetting', None)})

            if self.flight_recorder:
                try:
                    self.flight_recorder.log_phase2_verifier(
                        batch_id=b_idx,
                        cot_budget=budget_val if 'budget_val' in locals() else 0,
                        prompt_dump="",
                        raw_response=[r.model_dump() if hasattr(r, "model_dump") else (r.dict() if hasattr(r, "dict") else str(r)) for r in refined_lines]
                    )
                except Exception:
                    logger.debug("Rejestracja weryfikacji w locie zakończona wyjątkiem", exc_info=True)

            any_redaction_printed = False
            for r in refined_lines:
                orig_item = next((it for it in pass1_items if it["id"] == r.id), None)
                orig_pl = orig_item["pl"] if orig_item else ""
                clean_ref = sanitize_sub_text(r.refined_pl)
                ch_desc = (getattr(r, 'changes_made', '') or '').strip()

                # Strip internal ASS tags (like {\i1}, {\i0}) and normalize newlines for pure, clean console display (Standard 9.6, 2C.5, Standard 9.7, 2C.3)
                disp_orig = re.sub(r"\{[^\}]*\}", "", str(orig_pl or "")).replace("\\r\\n", "\\N").replace("\\n", "\\N").replace("\r\n", "\\N").replace("\n", "\\N").strip()
                disp_ref = re.sub(r"\{[^\}]*\}", "", str(clean_ref or "")).replace("\\r\\n", "\\N").replace("\\n", "\\N").replace("\r\n", "\\N").replace("\n", "\\N").strip()

                # Check if there is an actual textual modification or meaningful redaction note
                from verifier import DialogueVerifier
                lexically_same = DialogueVerifier.is_lexically_identical_ignoring_linebreak(disp_orig, disp_ref)
                has_meaningful_note = bool(ch_desc and "Zweryfikowano" not in ch_desc and ch_desc.lower() != "null")
                has_text_change = bool(disp_orig and (disp_orig != disp_ref) and not (lexically_same and not has_meaningful_note))

                if has_text_change:
                    any_redaction_printed = True
                    clean_note = ch_desc if ch_desc.startswith("[") else (f"[{ch_desc}]" if ch_desc else "")
                    pillar_note = f" {clean_note}" if clean_note else ""

                    pbar.write(f" └─ [Redaktor Dialogów] #{r.id}{pillar_note}")
                    pbar.write(f"    ├─ Szkic:  \"{disp_orig}\"")
                    pbar.write(f"    └─ Szlif:  \"{disp_ref}\"")

            if not any_redaction_printed:
                pbar.write(f" └─ [Redaktor Dialogów] Zweryfikowano bez uwag (100% zgodności z Kanonem AVT)")

        # Standard 7.0 Primary Translation Authority:
        # Tekst z Fazy 1 i Fazy 2 traktowany jest jako autorytatywny bez wtórnych mutacji liczby zaimków przed linterem.

        scene_has_male = False
        for it in pass1_items:
            s_name = (it.get("speaker_name") or "").strip()
            s_gen = it.get("speaker_gender")
            t_gen = it.get("target_gender")
            s_str = str(s_gen or "").lower()
            t_str = str(t_gen or "").lower()
            if s_gen and "female" not in s_str and "kobieta" not in s_str and "dziewczyna" not in s_str and any(w in s_str for w in ["male", "mężczyzna", "chłopak"]):
                scene_has_male = True
                break
            if t_gen and "female" not in t_str and "kobieta" not in t_str and "dziewczyna" not in t_str and any(w in t_str for w in ["male", "mężczyzna", "chłopak"]):
                scene_has_male = True
                break
            if s_name:
                if hasattr(self, "series_bible") and self.series_bible and hasattr(self.series_bible, "get_character_gender"):
                    if self.series_bible.get_character_gender(s_name, allow_generic_nouns=False) == "MALE":
                        scene_has_male = True
                        break
                elif s_name in getattr(self, "character_registry", {}):
                    cd = self.character_registry[s_name].lower()
                    if any(k in cd for k in getattr(self, "MALE_ROLE_KEYWORDS", [])):
                        scene_has_male = True
                        break
            v_voice = str(it.get("speaker_voice", "")).lower()
            if any(k in v_voice for k in ["baryton", "bas", "tenor", "chłopięcy", "męski"]) and "alt" not in v_voice:
                scene_has_male = True
                break

        prev_linted_line = (lookback_history[-1]["pl"] if lookback_history else "")
        for item in pass1_items:
            raw_final = sanitize_sub_text(refined_dict.get(item["id"], item["pl"]))
            alias_fixes = []
            if not self.keep_honorifics and not item.get("is_sign", False):
                if hasattr(self, "series_bible") and self.series_bible:
                    decl_final = self.series_bible.apply_canonical_alias_declension(
                        raw_final,
                        source_en=item.get("en", ""),
                        keep_honorifics=self.keep_honorifics
                    )
                    if decl_final != raw_final:
                        alias_fixes.append(f"[SeriesBible P0 Alias] Odmiana aliasu kanonicznego: '{raw_final}' -> '{decl_final}'")
                        raw_final = decl_final
            # Triangulate effective gender from character registry, audio F0 voice, and pragmatic clues (Filar CXXXVI)
            spk_gen = item.get("speaker_gender")
            spk_voice = item.get("speaker_voice", "")
            spk_name = (item.get("speaker_name") or "").strip()
            if not spk_gen and spk_name:
                if spk_name in self.character_registry:
                    cd = self.character_registry[spk_name].lower()
                    if any(k in cd for k in self.FEMALE_ROLE_KEYWORDS):
                        spk_gen = "kobieta"
                    elif any(k in cd for k in self.MALE_ROLE_KEYWORDS):
                        spk_gen = "mężczyzna"
                elif hasattr(self, "series_bible") and self.series_bible and hasattr(self.series_bible, "get_character_gender"):
                    bg = self.series_bible.get_character_gender(spk_name, allow_generic_nouns=False)
                    if bg == "FEMALE":
                        spk_gen = "kobieta"
                    elif bg == "MALE":
                        spk_gen = "mężczyzna"

            if not spk_gen:
                v_lower = spk_voice.lower()
                if "sopran" in v_lower or "alt żeński" in v_lower:
                    spk_gen = "kobieta"
                elif "alt starszej" in v_lower or "ochrypły alt" in v_lower:
                    # Low raspy voice (could be elderly female) - do not force male!
                    pass
                elif any(k in v_lower for k in ["baryton", "bas", "tenor", "chłopięcy", "męski"]) and "alt" not in v_lower and "ochrypł" not in v_lower:
                    spk_gen = "mężczyzna"
                elif "żeński" in v_lower:
                    spk_gen = "kobieta"

            has_formal_voc = bool(re.search(
                r"\b(panie|pani|panno|panu|pana)\s+([A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]+|doktorze|profesorze|inspektorze|prezesie|dyrektorze|kierowniku|komisarzu)\b",
                raw_final,
                re.IGNORECASE
            ))
            is_item_informal = ((spk_name in speakers_on_ty) if spk_name else scene_has_first_name_vocative) and not has_formal_voc
            try:
                final_text, fixes = self.linter.lint_and_fix_line(
                    text=raw_final,
                    speaker_gender=spk_gen,
                    speaker_confidence=item.get("speaker_confidence", 1.0),
                    is_all_girls_scene=False,
                    is_sign=item.get("is_sign", False),
                    user_feedback_rules=all_user_rules,
                    custom_glossary=combined_glossary,
                    is_informal_ty=is_item_informal,
                    audio_jp=item.get("audio_jp", ""),
                    prev_line_text=prev_linted_line,
                    source_en=item.get("en", ""),
                    addressee_gender=item.get("target_gender") or item.get("addressee"),
                    target_gender=item.get("target_gender") or item.get("addressee"),
                    target_confidence=item.get("target_confidence", 1.0),
                    addressee_number=item.get("addressee_number"),
                    plural_group_gender=item.get("plural_group_gender", "AMBIGUOUS"),
                    you_group_gender=item.get("you_group_gender", "AMBIGUOUS"),
                    scene_has_male_participant=scene_has_male,
                    strict_positive_domain=True
                )
            except TypeError:
                final_text, fixes = self.linter.lint_and_fix_line(
                    text=raw_final,
                    speaker_gender=spk_gen,
                    is_all_girls_scene=False,
                    is_sign=item.get("is_sign", False),
                    user_feedback_rules=all_user_rules,
                    custom_glossary=combined_glossary,
                    is_informal_ty=is_item_informal,
                    audio_jp=item.get("audio_jp", ""),
                    prev_line_text=prev_linted_line,
                    source_en=item.get("en", ""),
                    addressee_gender=item.get("target_gender") or item.get("addressee"),
                    target_gender=item.get("target_gender") or item.get("addressee"),
                    addressee_number=item.get("addressee_number"),
                    scene_has_male_participant=scene_has_male
                )
            prev_linted_line = final_text
            # Deterministic glossary overrides
            final_text, gloss_fixes = GlossaryManager.apply_deterministic_overrides(final_text, combined_glossary)
            if item.get("is_song") and not item.get("is_sign"):
                clean_no_notes = re.sub(r"^[♪♫♬\s]+|[♪♫♬\s]+$", "", final_text).strip()
                if clean_no_notes:
                    final_text = f"♪ {clean_no_notes} ♪"
            for fix in fixes + gloss_fixes + alias_fixes:
                pbar.write(f"  [AVT Linter/Słownik] {fix}")
            start_m = item.get("start_ms", item["event"].start if "event" in item else 0)
            end_m = item.get("end_ms", item["event"].end if "event" in item else 1000)
            eff_max_len = 42 if item.get("is_sign", False) else 38
            formatted_final = split_subtitle_syntactically(final_text, max_line_len=eff_max_len, is_ass=is_ass, is_sign=item.get("is_sign", False))
            batch_results[item["orig_idx"]] = formatted_final

            if self.flight_recorder:
                try:
                    self.flight_recorder.log_line_evolution(
                        line_id=item.get("orig_idx", item["id"]),
                        start_ms=start_m,
                        end_ms=end_m,
                        actor=item.get("speaker_name") or item.get("speaker") or "",
                        en_text=item.get("en", ""),
                        jp_audio=item.get("audio_jp", ""),
                        whisper_tags=str(item.get("whisper_disambiguation", "")),
                        telemetry_tag=item.get("telemetry_tag", ""),
                        phase1_pl=item.get("pl", ""),
                        phase2_pl=refined_dict.get(item["id"], item["pl"]),
                        linter_pl=final_text,
                        fixes_applied=fixes + gloss_fixes + alias_fixes
                    )
                except Exception:
                    logger.debug("Rejestracja wyników lintera zakończona wyjątkiem", exc_info=True)

            eff_reg = refined_region_dict.get(item["id"]) or item.get("screen_region")
            if eff_reg:
                batch_regions[item["orig_idx"]] = eff_reg
            eff_ts = refined_typesetting_dict.get(item["id"]) or item.get("visual_typesetting")
            if eff_ts:
                item["visual_typesetting"] = eff_ts

        # Harmonize concurrent screen subtitles (e.g. speech balloon + dialogue with identical EN text)
        en_to_best_pl: Dict[str, str] = {}
        for item in pass1_items:
            en_norm = item["en"].strip().lower()
            pl_res = batch_results.get(item["orig_idx"], "")
            if pl_res and "to robi" not in pl_res.lower():
                en_to_best_pl[en_norm] = pl_res

        for item in pass1_items:
            en_norm = item["en"].strip().lower()
            if en_norm in en_to_best_pl:
                cur_pl = batch_results.get(item["orig_idx"], "")
                if "to robi" in cur_pl.lower():
                    batch_results[item["orig_idx"]] = en_to_best_pl[en_norm]

        return b_idx, batch_results, batch_regions, untranslated_in_batch, pass1_items, scene_desc, cot_info_str

    def _reset_episode_state_for_file(self, subs_file: Path) -> str:
        """Standard 11.1 (LUKA-E5-01): Resetuje series_bible i style_report między odcinkami różnych serii."""
        init_slug = normalize_anime_slug(subs_file.stem) or "anime"
        if hasattr(self, "series_bible") and self.series_bible is not None:
            bible_series = getattr(self.series_bible, "slug", None) or getattr(self.series_bible, "series_name", None)
            if bible_series and bible_series != init_slug:
                self.series_bible = None
        self.style_report = None
        return init_slug

    def translate_file(
        self,
        subs_path: str,
        video_path: Optional[str] = None,
        output_path: Optional[str] = None,
        progress_callback = None,
        cancel_check = None
    ) -> str:
        """
        Main method to translate a subtitle file preserving full Typesetting, styles, and timing.
        """
        subs_file = Path(subs_path)
        # Reset character registry and token counters for new episode
        self.character_registry = {}
        self._asr_last_seen_end_sec = {}
        self._asr_last_text = ""
        self._asr_consecutive_streak = 0
        self.current_episode_tokens = {"prompt": 0, "cached": 0, "output": 0, "model": self.model}
        if not hasattr(self, "_thread_local") or self._thread_local is None:
            self._thread_local = threading.local()
        self._thread_local.last_batch_token_usage = {}
        if self.verifier:
            self.verifier.current_episode_tokens = {"prompt": 0, "cached": 0, "output": 0, "model": self.verifier.model}

        init_slug = self._reset_episode_state_for_file(subs_file)
        if getattr(self, "trace_log", True):
            try:
                self.flight_recorder = EpisodeFlightRecorder(
                    anime_slug=init_slug,
                    filename=subs_file.stem,
                    trace_dir=getattr(self, "trace_dir", "logs"),
                    enabled=True
                )
            except Exception:
                self.flight_recorder = None
        else:
            self.flight_recorder = None

        if self.flight_recorder:
            try:
                self.flight_recorder.log_cli_init(
                    cli_args={
                        "subs_path": subs_path,
                        "video_path": video_path,
                        "output_path": output_path,
                        "batch_size": self.batch_size,
                        "keep_honorifics": self.keep_honorifics,
                        "enable_verifier": self.enable_verifier,
                        "use_whisper": bool(self.whisper)
                    },
                    paths={
                        "subs_file": str(subs_file),
                        "video_path": video_path,
                        "output_path": output_path
                    },
                    models={
                        "phase1_model": self.model_phase1,
                        "phase2_model": getattr(self.verifier, "model", None) if self.verifier else None
                    },
                    context_cache_info={"model": self.model_phase1},
                    client_pool_info={"active_clients": len(getattr(self.client_pool, "clients", [1])) if getattr(self, "client_pool", None) else 1}
                )
            except Exception:
                logger.debug("Inicjalizacja rejestratora zdarzeń zakończona wyjątkiem", exc_info=True)

        is_ass = not str(subs_file).lower().endswith(".srt")

        from avt_linter import load_subtitle_file_resilient
        subs = load_subtitle_file_resilient(subs_file)

        # Standard 11.1 (LUKA-E1-01): Initialize StyleMatrixEngine BEFORE segment_hybrid_events
        from style_matrix import analyze_subtitles
        self.style_report = analyze_subtitles(subs)
        subs.events = segment_hybrid_events(subs.events, style_report=self.style_report)
        print(self.style_report.format_user_friendly_summary())

        if self.flight_recorder:
            try:
                classified_sample = []
                for idx_ev, ev_item in enumerate(subs.events[:50]):
                    ts_pref_c, clean_c = extract_typesetting_tags(ev_item.text)
                    v_info = detect_event_visual_type(ev_item, ts_pref_c, style_report=getattr(self, "style_report", None))
                    classified_sample.append({
                        "id": idx_ev + 1,
                        "start": ev_item.start,
                        "end": ev_item.end,
                        "style": ev_item.style,
                        "raw_actor_name": getattr(ev_item, "name", ""),
                        "type_label": v_info.get("type_label", "DIALOG"),
                        "is_sign": v_info.get("is_sign", False),
                        "en_raw": clean_c or ev_item.text
                    })
                style_summary_dict = (
                    self.style_report.get_summary()
                    if getattr(self, "style_report", None) and hasattr(self.style_report, "get_summary")
                    else (getattr(self.style_report, "styles", {}) if hasattr(self, "style_report") else {})
                )
                self.flight_recorder.log_ingestion(
                    encoding="utf-8",
                    total_events=len(subs.events),
                    style_matrix=style_summary_dict,
                    events_classified=classified_sample
                )
            except Exception:
                logger.debug("Rejestracja profilu stylów zakończona wyjątkiem", exc_info=True)

        # 0. Retrieve anime metadata from AniList (with Gemini Parametric Knowledge Fallback)
        ref_filename = video_path if video_path else subs_path
        client_for_meta = getattr(self, "client_pool", None) or self.client
        anime_meta = get_anime_context(ref_filename, client=client_for_meta)
        anime_context_str = ""
        
        if anime_meta:
            anime_context_str = format_anime_context_for_prompt(anime_meta)
            title_name = anime_meta.get("title_romaji") or anime_meta.get("title_english") or "Seria"
            char_count = len(anime_meta.get("characters", []))
            print(f"\n[Baza Wiedzy Anime]: Rozpoznano serię: '{title_name}'")
            if anime_meta.get("genres"):
                print(f"[Baza AniList] Gatunki: {', '.join(anime_meta['genres'])}")
            if anime_meta.get("setting_tags"):
                print(f"[Baza AniList] [Realia świata / Epoka]: {', '.join(anime_meta['setting_tags'])}")
            if anime_meta.get("detected_domains"):
                print(f"[Baza AniList] [Dziedzina specjalistyczna]: {', '.join(anime_meta['detected_domains'])}")
            print(f"[Baza AniList] Wczytano opis fabuły oraz {char_count} postaci z ich płcią i rolami.")
            
            # Standard 9.0 Wariant (d): Wczesna inicjalizacja i zasilenie SeriesBible oraz character_registry
            from series_memory import SeriesBible, generate_polish_name_declension
            if not getattr(self, "series_bible", None):
                self.series_bible = SeriesBible(anime_title=title_name)

            for c in anime_meta.get("characters", []):
                c_name = c.get("name")
                c_gen = c.get("gender")
                c_role = c.get("role", "postać")
                if c_name:
                    norm_gender = c_gen.upper() if c_gen else "UNKNOWN"
                    gramm_gender = "MASCULINE" if norm_gender == "MALE" else ("FEMININE" if norm_gender == "FEMALE" else "UNKNOWN")
                    has_ver = bool(c.get("has_verified_gender") or (c_gen and c_gen.upper() in ("MALE", "FEMALE")))
                    char_entry = {
                        "gender": norm_gender,
                        "grammatical_gender": gramm_gender,
                        "confidence": 1.0 if has_ver else 0.8,
                        "priority": "P0",
                        "has_verified_gender": has_ver,
                        "aliases": c.get("aliases", []),
                        "description": f"{c_role} ({c_gen or 'unknown'})"
                    }
                    self.series_bible.data.setdefault("characters", {})[c_name] = char_entry
                    gender_pl = "mężczyzna" if norm_gender == "MALE" else ("kobieta" if norm_gender == "FEMALE" else "postać")
                    self._register_character_safe(c_name, gender_pl, c_role)

        # Generowanie paradygmatów odmiany dla wszystkich unikalnych aktorów
        actor_map = {}
        from metadata import normalize_actor_tag
        from series_memory import generate_polish_name_declension, COLLECTIVE_LABELS, is_generic_actor_or_category
        for ev_it in subs.events:
            raw_spk = getattr(ev_it, "name", "")
            if raw_spk and raw_spk not in actor_map:
                cl_act, ex_gen = normalize_actor_tag(raw_spk)
                actor_map[raw_spk] = {"clean_name": cl_act, "extracted_gender": ex_gen}
                if getattr(self, "series_bible", None) and cl_act:
                    effective_gender = ex_gen
                    if not effective_gender:
                        sb_g = self.series_bible.get_character_gender(cl_act)
                        if sb_g in ("MALE", "FEMALE"):
                            effective_gender = sb_g
                    is_invalid_tag = (
                        cl_act.lower() in COLLECTIVE_LABELS
                        or (len(cl_act.split()) == 1 and cl_act[0].islower())
                        or is_generic_actor_or_category(cl_act)
                    )
                    if not is_invalid_tag:
                        a_decl = generate_polish_name_declension(cl_act, effective_gender or "UNKNOWN")
                        if a_decl and a_decl.get("M"):
                            self.series_bible.data.setdefault("declensions", {})[cl_act] = a_decl
        self.actor_map = actor_map
        if getattr(self, "series_bible", None) and hasattr(self.series_bible, "populate_secondary_actor_tags"):
            self.series_bible.populate_secondary_actor_tags(list(actor_map.keys()))

        if self.flight_recorder:
            try:
                self.flight_recorder.log_metadata(
                    clean_slug=self.flight_recorder.anime_slug,
                    anilist_meta=anime_meta,
                    actor_mappings=actor_map
                )
            except Exception:
                logger.debug("Rejestracja metadanych serii zakończona wyjątkiem", exc_info=True)

        # 1. Clean events and compress frame-by-frame animations (FBF Animation Deduplication)
        raw_all_entries = []
        for i, ev in enumerate(subs.events):
            if ev.is_comment:
                continue
            ts_prefix, clean = extract_typesetting_tags(ev.text)
            if not clean:
                clean = sanitize_sub_text(ev.plaintext)
            if not clean:
                continue
            raw_all_entries.append((i, ev, clean, ts_prefix))

        # Compress animated typesetting (e.g. 1100 sub-frames of 'CHIN' reduced to 1 API call)
        raw_entries = []
        sub_to_master = {}
        last_text = None
        last_style = None
        last_end = -1
        current_master_orig_idx = None

        for orig_idx, ev, clean, ts_prefix in raw_all_entries:
            is_fbf_animation = (
                last_text is not None and
                clean.strip().lower() == last_text.strip().lower() and
                ev.style == last_style and
                (ev.start <= last_end + 200) and
                ((ev.end - ev.start) <= 300 or r"\pos" in ts_prefix or r"\move" in ts_prefix or r"\fsc" in ts_prefix or r"\clip" in ts_prefix)
            )

            if is_fbf_animation and current_master_orig_idx is not None:
                sub_to_master[orig_idx] = current_master_orig_idx
                last_end = max(last_end, ev.end)
            else:
                current_master_orig_idx = orig_idx
                raw_entries.append((orig_idx, ev, clean, ts_prefix))
                sub_to_master[orig_idx] = current_master_orig_idx
                last_text = clean
                last_style = ev.style
                last_end = ev.end
        # 1c. Deictic Discourse & Dual-Voice Turn-Taking Resolution (0.00 PLN)
        for re_idx, (orig_idx, ev, clean, ts_prefix) in enumerate(raw_entries):
            if DualVoiceTagPreserver.is_dual_voice(ev.text):
                lines_m = DualVoiceTagPreserver.DUAL_VOICE_STRICT_REGEX.match(ev.text.strip())
                if lines_m:
                    l_a = lines_m.group(2).strip()
                    l_b = (lines_m.group(4) if lines_m.lastindex >= 4 else lines_m.group(3)).strip()
                    spk_a, spk_b, dmeta = DeicticDiscourseEngine.resolve_deictic_hierarchy(l_a, l_b, getattr(ev, "name", ""))
                    ev.name = f"{spk_a} / {spk_b}"
                    next_idx = re_idx + 1
                    while next_idx < len(raw_entries):
                        n_orig_idx, n_ev, n_clean, n_ts = raw_entries[next_idx]
                        delta_ms = n_ev.start - ev.end
                        cont_spk = DeicticDiscourseEngine.audit_monologue_topic_continuation(n_clean, last_speaker=spk_a, delta_ms=delta_ms)
                        if cont_spk:
                            n_ev.name = cont_spk
                            next_idx += 1
                        else:
                            break

        total_lines = len(raw_entries)
        fbf_saved = len(raw_all_entries) - total_lines
        if fbf_saved > 0:
            print(f"\n[Optymalizacja Typesettingu]: Wykryto i skompresowano {fbf_saved} animowanych mikronapisów FBF (Zaoszczędzono {fbf_saved} zapytań API!).")
        print(f"\n[Translator] Załadowano {total_lines} unikalnych kwestii do przetłumaczenia (z {len(raw_all_entries)} wszystkich zdarzeń ASS).")
        print(f"[Translator] Model: {self.model} | Paczka: {self.batch_size} kwestii")
        print(f"[Translator] Honoryfikatory (-kun, -chan, -san): {'ZACHOWANE (Styl Anime/Fansub)' if self.keep_honorifics else 'USUWANE (Czysta polszczyzna/Netflix)'}")
        print(f"[Translator] Typesetting & Pozycjonowanie (ASS Styles): ZACHOWANE")
        if self.tm:
            with sqlite3.connect(self.tm.db_path) as conn:
                pair_count = conn.execute("SELECT COUNT(*) FROM translation_pairs").fetchone()[0]
            print(f"[Translator] Pamięć Tłumaczeniowa (Baza Anime): AKTYWNA ({pair_count:,} sparowanych wzorców dialogowych)")
        if video_path and os.path.exists(video_path):
            print(f"[Translator] Tryb multimodalny aktywny (wideo: {Path(video_path).name})")
        else:
            print("[Translator] Tryb tekstowy.")

        history: List[Dict[str, str]] = []
        translated_results: Dict[int, str] = {}
        translated_regions: Dict[int, str] = {}
        translated_typesetting: Dict[int, Any] = {}
        translated_addressees: Dict[int, str] = {}
        translated_speakers: Dict[int, str] = {}
        episode_whisper_transcriptions: Dict[int, str] = {}

        # 1b. Search for checkpoint files (multiple paths and candidate formats)
        checkpoint_path = None
        if video_path and os.path.exists(video_path):
            checkpoint_path = Path(video_path).with_suffix(".checkpoint.json")
        else:
            checkpoint_path = subs_file.with_suffix(".checkpoint.json")

        candidate_checkpoints = []
        if video_path:
            vp = Path(video_path)
            candidate_checkpoints.extend([
                vp.with_suffix(".checkpoint.json"),
                vp.parent / f"{vp.stem}.checkpoint.json",
                vp.parent / f"{vp.stem}.json",
                vp.with_suffix(".json"),
            ])
        if subs_path:
            sp = Path(subs_path)
            candidate_checkpoints.extend([
                sp.with_suffix(".checkpoint.json"),
                sp.parent / f"{sp.stem}.checkpoint.json",
                sp.parent / f"{sp.stem}.json",
                sp.with_suffix(".json"),
            ])

        found_checkpoint_path = None
        restored_f1_tokens = None
        restored_f2_tokens = None
        for cand in candidate_checkpoints:
            if cand and cand.exists() and cand.is_file():
                try:
                    with open(cand, "r", encoding="utf-8") as cp_file:
                        saved_data = json.load(cp_file)
                        if isinstance(saved_data, dict) and len(saved_data) > 0:
                            if "translated_results" in saved_data:
                                translated_results = {int(k): str(v) for k, v in saved_data["translated_results"].items() if str(k).isdigit()}
                                translated_regions = {int(k): str(v) for k, v in saved_data.get("translated_regions", {}).items() if str(k).isdigit()}
                                translated_typesetting = {int(k): v for k, v in saved_data.get("translated_typesetting", {}).items() if str(k).isdigit()}
                                translated_addressees = {int(k): str(v) for k, v in saved_data.get("translated_addressees", {}).items() if str(k).isdigit()}
                                translated_speakers = {int(k): str(v) for k, v in saved_data.get("translated_speakers", {}).items() if str(k).isdigit()}
                                token_usage = saved_data.get("token_usage", {})
                                restored_f1_tokens = token_usage.get("f1")
                                restored_f2_tokens = token_usage.get("f2")
                            else:
                                translated_results = {int(k): str(v) for k, v in saved_data.items() if str(k).isdigit()}
                            if translated_results:
                                found_checkpoint_path = cand
                                break
                except Exception:
                    logger.debug("Odczyt punktu kontrolnego zakończony wyjątkiem", exc_info=True)

        if restored_f1_tokens and isinstance(restored_f1_tokens, dict):
            for k in ["prompt", "cached", "output"]:
                self.current_episode_tokens[k] = self.current_episode_tokens.get(k, 0) + restored_f1_tokens.get(k, 0)
            if "model" in restored_f1_tokens and restored_f1_tokens["model"]:
                self.current_episode_tokens["model"] = restored_f1_tokens["model"]
        if restored_f2_tokens and isinstance(restored_f2_tokens, dict) and self.verifier:
            for k in ["prompt", "cached", "output"]:
                self.verifier.current_episode_tokens[k] = self.verifier.current_episode_tokens.get(k, 0) + restored_f2_tokens.get(k, 0)
            if "model" in restored_f2_tokens and restored_f2_tokens["model"]:
                self.verifier.current_episode_tokens["model"] = restored_f2_tokens["model"]

        if found_checkpoint_path and translated_results:
            print("\n" + "═" * 60)
            print(f"  [AUTOZAPIS / WZNOWIENIE]: Znaleziono plik checkpointu!")
            print(f"  Plik: {found_checkpoint_path.name}")
            print(f"  Wczytano {len(translated_results)}/{total_lines} gotowych kwestii dialogowych.")
            if restored_f1_tokens:
                print(f"  Przywrócono stan zużycia tokenów z wcześniejszej sesji.")
            print("═" * 60 + "\n")
        else:
            print("[Autozapis]: Brak wcześniejszego checkpointu. Rozpoczynanie tłumaczenia.")

        # Stalowa reguła: Zachowanie oryginalnych piosenek z Openingów i Endingów (OP/ED) bez tłumaczenia AI
        song_lines_preserved = 0
        for orig_idx, ev, clean, ts_prefix in raw_entries:
            if is_song_line(ev, clean):
                if orig_idx not in translated_results:
                    translated_results[orig_idx] = clean
                    song_lines_preserved += 1

        if song_lines_preserved > 0:
            print(f"  [Kanon OP/ED]: Zachowano {song_lines_preserved} wersów piosenek (Opening/Ending) w oryginalnej wersji bez wysyłania do AI (0 PLN).")

        # 0. Episode Profiler (Pre-pass Glossary & Relationship Matrix)
        profile_cache_path = None
        if subs_path:
            profile_cache_path = str(Path(subs_path).with_suffix(".profile.json"))
        elif video_path:
            profile_cache_path = str(Path(video_path).with_suffix(".profile.json"))

        all_dialogue_sample = "\n".join([f"{e.name or 'Postać'}: {sanitize_sub_text(e.text)}" for _, e, _, _ in raw_entries])
        
        print("\n[Profiler Odcinka]: Analiza fabuły, relacji postaci, realiów epoki i budowanie słowniczka...")
        episode_profile = self.profiler.profile_episode(
            subs_text_sample=all_dialogue_sample,
            anime_metadata_str=anime_context_str,
            cache_path=profile_cache_path
        )
        episode_profile_str = format_lean_episode_brief(episode_profile) if episode_profile else ""

        if self.flight_recorder:
            try:
                cache_st = "hit" if (profile_cache_path and os.path.exists(profile_cache_path)) else "computed"
                self.flight_recorder.log_profile_prepass(
                    cache_status=cache_st,
                    episode_profile=episode_profile,
                    profile_brief=episode_profile_str
                )
            except Exception:
                logger.debug("Rejestracja profilu odcinka zakończona wyjątkiem", exc_info=True)

        # 0b. Initialize and load Series Bible (Cross-Episode Continuity)
        series_title = ""
        if anime_meta:
            series_title = anime_meta.get("title_romaji") or anime_meta.get("title_english") or ""
        if not series_title:
            ref_path = video_path or subs_path or ""
            if ref_path:
                series_title = Path(ref_path).stem.split(" - ")[0].replace("[ASW]", "").replace("[Erai-raws]", "").strip()
        if not getattr(self, "series_bible", None):
            self.series_bible = SeriesBible(anime_title=series_title)
        # Pre-populate global Character Registry from persistent Series Bible
        if self.series_bible and hasattr(self.series_bible, "data"):
            bible_chars = self.series_bible.data.get("characters", {})
            for b_name, b_val in bible_chars.items():
                b_desc = b_val.get("description", "") if isinstance(b_val, dict) else str(b_val)
                if b_name and b_desc:
                    for p in re.split(r"[/,]", b_name):
                        clean_p = p.strip()
                        if len(clean_p) >= 3 and clean_p not in self.character_registry:
                            self.character_registry[clean_p] = b_desc

        if episode_profile:
            # Pre-populate global Character Registry from Episode Profile dossiers and declensions first
            if getattr(episode_profile, "character_dossiers", None):
                for cd in episode_profile.character_dossiers:
                    if cd.name:
                        gender_pl = "kobieta" if cd.gender.upper() == "FEMALE" else ("mężczyzna" if cd.gender.upper() == "MALE" else cd.gender)
                        self._register_character_safe(cd.name, gender_pl, cd.age_and_role or 'postać')
            if getattr(episode_profile, "name_declensions", None):
                for nd in episode_profile.name_declensions:
                    if nd.character_name:
                        gender_pl = "kobieta" if nd.gender.upper() == "FEMALE" else ("mężczyzna" if nd.gender.upper() == "MALE" else nd.gender)
                        self._register_character_safe(nd.character_name, gender_pl, 'postać')

            char_dict = {}
            for c in episode_profile.characters:
                char_key = f"{c.speaker} -> {c.listener}" if c.listener else c.speaker
                char_dict[char_key] = f"Zwrot: '{c.address_form}' ({c.relationship_type})"

            # Also persist standalone confirmed characters from Character Registry into Series Bible
            for cname, creg in list(self.character_registry.items()):
                if cname and cname not in char_dict:
                    char_dict[cname] = creg

            gloss_dict = {g.term_en: g.translation_pl for g in episode_profile.glossary}
            plot_anchors_dict = {}
            if getattr(episode_profile, "continuity_bridge_alerts", None):
                for cba in episode_profile.continuity_bridge_alerts:
                    c_guide = getattr(cba, "continuity_guidance", "")
                    if cba.term_or_event and c_guide:
                        plot_anchors_dict[cba.term_or_event] = c_guide

            rels_dict = {}
            if getattr(episode_profile, "character_relationships", None):
                for rel in episode_profile.character_relationships:
                    if rel.speaker and rel.listener:
                        rels_dict[f"{rel.speaker}->{rel.listener}"] = f"{rel.address_form} ({rel.relationship_type})"

            ref_name = Path(video_path).stem if video_path else (Path(subs_path).stem if subs_path else "Odcinek")
            self.series_bible.update_from_episode_profile(
                episode_name=ref_name,
                characters=char_dict,
                glossary=gloss_dict,
                plot_anchors=plot_anchors_dict,
                relationships=rels_dict
            )

        # Standard 9.0: Synchronize SeriesBible and CharacterRegistry from Krok 3 & 5
        if hasattr(self, "series_bible") and self.series_bible:
            if hasattr(self.series_bible, "synchronize_from_metadata_and_profile"):
                self.series_bible.synchronize_from_metadata_and_profile(
                    anilist_meta=anime_meta,
                    episode_profile=episode_profile
                )
            for c_k, c_v in getattr(self.series_bible, "characters", {}).items():
                if c_k and c_k not in self.character_registry:
                    g = c_v.get("gender") if isinstance(c_v, dict) else None
                    g_pl = "kobieta" if g == "FEMALE" else ("mężczyzna" if g == "MALE" else (g or "postać"))
                    role = c_v.get("role", "postać") if isinstance(c_v, dict) else "postać"
                    self._register_character_safe(c_k, g_pl, role)

        # 0c. Match Official Polish Manga Canon
        candidates_to_match = [series_title]
        if anime_meta:
            if anime_meta.get("title_romaji"): candidates_to_match.append(anime_meta["title_romaji"])
            if anime_meta.get("title_english"): candidates_to_match.append(anime_meta["title_english"])
        if subs_path:
            candidates_to_match.append(Path(subs_path).stem)
        if video_path:
            candidates_to_match.append(Path(video_path).stem)

        manga_canon_entry = self.manga_canon.get_or_discover_canon(
            series_title=series_title,
            candidates=candidates_to_match,
            anime_meta=anime_meta,
            client=self.client_pool or self.client
        )

        manga_canon_str = ""
        if manga_canon_entry:
            manga_canon_str = self.manga_canon.format_canon_for_prompt(manga_canon_entry)
            print(f"  [Kanon Mangi]: Wczytano oficjalny polski kanon: '{manga_canon_entry.get('title')}' ({manga_canon_entry.get('publisher', 'Wydawnictwo')})")
            if manga_canon_entry.get("glossary"):
                self.series_bible.update_from_episode_profile(
                    episode_name="Kanon Mangi",
                    characters={},
                    glossary=manga_canon_entry["glossary"]
                )

        series_bible_str = self.series_bible.format_for_prompt()
        if series_bible_str:
            print(f"  [Biblia Serialu]: Wczytano ciągłość sezonu dla serii '{series_title or self.series_bible.slug}'")

        # 0d. Combined User, Manga Canon and Series Bible Glossary (4-Tier Authority Hierarchy)
        series_gloss_dict = self.series_bible.data.get("glossary", {}) if hasattr(self, "series_bible") and self.series_bible else {}
        manga_canon_dict = manga_canon_entry.get("glossary", {}) if manga_canon_entry else {}
        profiler_gloss_dict = {g.term_en: g.translation_pl for g in episode_profile.glossary} if (episode_profile and episode_profile.glossary) else {}

        combined_glossary = self.glossary_manager.get_combined_glossary(
            series_glossary=series_gloss_dict,
            manga_canon_glossary=manga_canon_dict,
            profiler_glossary=profiler_gloss_dict,
            keep_honorifics=self.keep_honorifics
        )
        self.combined_glossary = combined_glossary
        if combined_glossary:
            print(f"  [Słownik Deterministyczny]: Aktywnych {len(combined_glossary)} terminów (Hierarchia: Kanon Mangi > Biblia Serialu > Profiler > Słownik Użytkownika).")

        # Standard 9.5 (Operacja 2B.1, 2C.4, R3.1): Zasilenie i synchronizacja SeriesBible przed logowaniem Kroku 6
        if hasattr(self, "series_bible") and self.series_bible:
            actor_keys = list(getattr(self, "actor_map", {}).keys()) if hasattr(self, "actor_map") else []
            if not actor_keys:
                actor_keys = [getattr(ev, "name", "") for ev in subs.events if getattr(ev, "name", "")]
            if hasattr(self.series_bible, "populate_secondary_actor_tags"):
                self.series_bible.populate_secondary_actor_tags(actor_keys)
            if hasattr(self.series_bible, "map_bilingual_role_aliases"):
                self.series_bible.map_bilingual_role_aliases(actor_keys)

            # Transfer paradygmatów z Kroku 5 (EpisodeProfiler) do SeriesBible
            declension_map = {}
            if episode_profile:
                if getattr(episode_profile, "character_dossiers", None):
                    for cd in episode_profile.character_dossiers:
                        cd_name = getattr(cd, "name", "")
                        cd_decl = getattr(cd, "declension", None) or getattr(cd, "paradigms", None)
                        if cd_name and cd_decl and isinstance(cd_decl, dict):
                            declension_map[cd_name] = cd_decl
                if getattr(episode_profile, "name_declensions", None):
                    for nd in episode_profile.name_declensions:
                        nd_name = getattr(nd, "character_name", "")
                        nd_cases = getattr(nd, "cases", None) or getattr(nd, "declension", None)
                        if not nd_cases and getattr(nd, "declension_summary", None):
                            from series_memory import SeriesBible
                            nd_cases = SeriesBible.parse_step5_declension_line(nd.declension_summary)
                        if nd_name and nd_cases and isinstance(nd_cases, dict):
                            declension_map[nd_name] = nd_cases

            if declension_map:
                self.series_bible.data.setdefault("declensions", {}).update(declension_map)
                for cd_name, cd_cases in declension_map.items():
                    if hasattr(self.series_bible, "sync_verified_profile_entity"):
                        c_rec = self.series_bible.data.get("characters", {}).get(cd_name, {})
                        c_gen = c_rec.get("gender") if isinstance(c_rec, dict) else None
                        self.series_bible.sync_verified_profile_entity(cd_name, gender=c_gen, declension_map=cd_cases)

            # Sanitacja i regeneracja paradygmatów w RAM oraz zapis na dysk i synchronizacja z Artefakty/ (Operacja H4)
            if hasattr(self.series_bible, "_sanitize_loaded_bible_in_ram"):
                self.series_bible._sanitize_loaded_bible_in_ram()
            if hasattr(self.series_bible, "save"):
                self.series_bible.save()

            # Trwałość populate_secondary_actor_tags bezpośrednio przed logowaniem Kroku 6 (Operacja 2C.4)
            if hasattr(self.series_bible, "populate_secondary_actor_tags"):
                self.series_bible.populate_secondary_actor_tags(actor_keys)

        if self.flight_recorder:
            try:
                char_reg = getattr(self.series_bible, "characters", {}) if hasattr(self, "series_bible") and self.series_bible else {}
                rel_dict = getattr(self.series_bible, "relations", {}) if hasattr(self, "series_bible") and self.series_bible else {}
                decl_dict = getattr(self.series_bible, "declensions", {}) if hasattr(self, "series_bible") and self.series_bible else {}
                bible_sum = {
                    "slug": getattr(self.series_bible, "slug", "") or (self.flight_recorder.anime_slug if self.flight_recorder else init_slug),
                    "characters_count": len(char_reg),
                    "glossary_count": len(combined_glossary) if combined_glossary else 0,
                    "relations_count": len(rel_dict),
                    "declensions_count": len(decl_dict)
                }
                self.flight_recorder.log_series_bible(
                    bible_summary=bible_sum,
                    character_registry=char_reg,
                    relations=rel_dict,
                    declensions=decl_dict
                )
            except Exception:
                logger.debug("Rejestracja bazy wiedzy serii zakończona wyjątkiem", exc_info=True)

        user_rules_cnt = len(self.user_feedback.list_all())
        user_feedback_str = self.user_feedback.format_for_prompt()
        if user_rules_cnt > 0:
            print(f"  [Korekty Użytkownika]: Wczytano {user_rules_cnt} złotych reguł (Few-Shot Prompting).")

        # 0e. Format static episode strings
        glossary_str = self.glossary_manager.format_for_prompt(combined_glossary)
        if manga_canon_entry and not manga_canon_str:
            manga_canon_str = self.manga_canon.format_canon_for_prompt(manga_canon_entry)
        episode_profile_str = format_lean_episode_brief(episode_profile) if episode_profile else ""

        if episode_profile:
            if not manga_canon_entry and episode_profile.manga_canon_source:
                print(f"  [Kanon Mangi]: Rozpoznano oficjalny polski przekład ({episode_profile.manga_canon_source})")
            if episode_profile.setting_and_era:
                print(f"  [Filar XV - Epoka i Realia Świata]: {episode_profile.setting_and_era}")
            if episode_profile.domain_expertise:
                print(f"  [Filar XVI - Dziedzina Specjalistyczna]: {episode_profile.domain_expertise}")
            if episode_profile.dialogue_stylization:
                print(f"  [Stylizacja Językowa]: {episode_profile.dialogue_stylization}")
            if episode_profile.tone_and_genre:
                print(f"  [Ton i Rejestr Dialogów]: {episode_profile.tone_and_genre}")
            if episode_profile.characters:
                print(f"  [Relacje i Etykieta]: Rozpoznano relacje dla {len(episode_profile.characters)} postaci.")
            if episode_profile.danger_lines_prescan:
                print(f"  [Skaner Min Językowych]: Wykryto {len(episode_profile.danger_lines_prescan)} niebezpiecznych pułapek kontekstowych (uzbrojone dyrektywy).")
            if episode_profile.relationship_pivots:
                print(f"  [Punkty Zwrotne Relacji]: Zabezpieczono {len(episode_profile.relationship_pivots)} dynamicznych zmian relacji w trakcie odcinka.")
            if episode_profile.character_catchphrases:
                print(f"  [Powiedzonka Postaci]: Zamrożono {len(episode_profile.character_catchphrases)} unikalnych kwestii-wizytówek.")
            if episode_profile.character_dossiers:
                print(f"  [Matryca Idiolektów]: Skonfigurowano unikalną stylizację mowy dla {len(episode_profile.character_dossiers)} bohaterów.")
            if episode_profile.glossary:
                terms_preview = ", ".join([f"'{g.term_en}' -> '{g.translation_pl}'" for g in episode_profile.glossary[:6]])
                suffix = "..." if len(episode_profile.glossary) > 6 else ""
                print(f"  [Słowniczek Odcinka]: {terms_preview}{suffix}")

        # Pre-pass Line Resolver: bind danger lines & catchphrases to concrete line indices
        self.profile_line_alerts = {}
        if episode_profile and raw_entries:
            try:
                from profiler import resolve_profile_alerts_to_events
                self.profile_line_alerts = resolve_profile_alerts_to_events(episode_profile, raw_entries)
                if self.profile_line_alerts:
                    print(f"  [Pre-pass Line Resolver]: Dopięto wytyczne Profilera do {len(self.profile_line_alerts)} kwestii na osi czasu.")
            except Exception as e_res:
                logger.warning(f"Niepowodzenie Pre-pass Line Resolvera ({e_res})")

        # 0f. Bake static Episode Knowledge (Profile, Glossary, Series Bible, User Feedback) into Cached System Instructions
        episode_knowledge_blocks = []
        if user_feedback_str:
            episode_knowledge_blocks.append(f"{user_feedback_str}")
        if glossary_str:
            episode_knowledge_blocks.append(f"{glossary_str}")
        if manga_canon_str:
            episode_knowledge_blocks.append(f"{manga_canon_str}")
        if series_bible_str:
            episode_knowledge_blocks.append(f"{series_bible_str}")
        if episode_profile_str:
            episode_knowledge_blocks.append(f"{episode_profile_str}")
        elif anime_context_str:
            episode_knowledge_blocks.append(f"{anime_context_str}")

        if episode_knowledge_blocks:
            full_ep_knowledge = "\n\n".join(episode_knowledge_blocks)
            self.system_prompt = f"{self.system_prompt}\n\n=== WIEDZA I WYTYCZNE DLA TEGO ODCINKA (PROFIL, SŁOWNIK, CIĄGŁOŚĆ) ===\n{full_ep_knowledge}"
            self._episode_knowledge_cached = True
            if self.verifier and hasattr(self.verifier, "system_prompt"):
                self.verifier.system_prompt = f"{self.verifier.system_prompt}\n\n=== WIEDZA I WYTYCZNE DLA TEGO ODCINKA (PROFIL, SŁOWNIK, CIĄGŁOŚĆ) ===\n{full_ep_knowledge}"
                self.verifier._episode_knowledge_cached = True

        # Check if translation is already 100% complete from checkpoint
        untranslated_count = sum(1 for item in raw_entries if item[0] not in translated_results and not is_song_line(item[1], item[2]))
        if untranslated_count > 0:
            # Pre-warming and Context Cache Hard Protection across all client pool keys (guarantees -90% discount)
            from context_cache import ContextCacheManager
            print(f"  [Infrastruktura Finansowa]: Weryfikacja i rozgrzewanie pamięci Context Cache z pełną wiedzą odcinka...")
            pool_or_c1 = self.client_pool if hasattr(self, "client_pool") and self.client_pool else self.client
            c1 = ContextCacheManager.ensure_cache_ready(pool_or_c1, self.model_phase1, self.system_prompt, tag="translator")
            if not c1:
                raise RuntimeError(
                    f"KATEGORYCZNA BLOKADA FINANSOWA: Nie udało się aktywować serwerowego Context Cache dla {self.model_phase1}. "
                    "Aby uchronić Twój portfel przed naliczeniem 10-krotnie wyższej stawki pełnej, proces został bezpiecznie wstrzymany. "
                    "Sprawdź połączenie z Google API lub stan konta i spróbuj ponownie."
                )
            if self.verifier and hasattr(self.verifier, "model") and hasattr(self.verifier, "system_prompt"):
                pool_or_c2 = getattr(self.verifier, "client_pool", None) or getattr(self.verifier, "client", None)
                c2 = ContextCacheManager.ensure_cache_ready(pool_or_c2, self.verifier.model, self.verifier.system_prompt, tag="verifier")
                if not c2:
                    raise RuntimeError(
                        f"KATEGORYCZNA BLOKADA FINANSOWA: Nie udało się aktywować serwerowego Context Cache dla weryfikatora ({self.verifier.model}). "
                        "Aby uchronić Twój portfel przed naliczeniem 10-krotnie wyższej stawki pełnej, proces został bezpiecznie wstrzymany."
                    )

            if self.whisper:
                try:
                    self.whisper._initialize_model()
                except Exception as e:
                    logger.warning(f"Whisper warm-up failed: {e}")

            # Pre-warm Context Cache sequentially for all clients before parallel threads start (Zero-Race Lock)
            try:
                from context_cache import ContextCacheManager
                clients_to_warm = self.client_pool.clients if hasattr(self, "client_pool") and self.client_pool else [self.client]
                for c in clients_to_warm:
                    ContextCacheManager.get_or_create_cache(client=c, model=self.model_phase1, system_instruction=self.system_prompt, tag="translator")
                    if self.enable_verifier and self.verifier:
                        ContextCacheManager.get_or_create_cache(client=c, model=self.verifier.model, system_instruction=self.verifier.system_prompt, tag="verifier")
            except Exception:
                logger.debug("Rozgrzewanie pamięci podręcznej kontekstu zakończone wyjątkiem", exc_info=True)
        else:
            print(f"  [Autozapis]: Wszystkie kwestie dialogowe ({len(translated_results)}) wczytane z checkpointu. Pomijanie rozgrzewania API.")

        # Precompute episode scene genders across timeline (0.00 PLN)
        self.episode_scene_genders = self._precompute_episode_scene_genders(
            raw_entries,
            whisper_transcriptions=episode_whisper_transcriptions,
            episode_profile=episode_profile
        )
        if self.episode_scene_genders:
            f_scenes = sum(1 for g in self.episode_scene_genders.values() if g == "kobieta")
            m_scenes = sum(1 for g in self.episode_scene_genders.values() if g == "mężczyzna")
            print(f"  [Pre-pass Sceniczny Odcinka]: Wykryto ciągłość obsady dla {len(self.episode_scene_genders)} kwestii ({f_scenes} żeńskich, {m_scenes} męskich).")

        # Detect FFmpeg scene cuts and black frames once per episode (0.00 PLN)
        self.scene_cuts_ms = []
        self.black_intervals_ms = []
        if video_path and os.path.exists(video_path):
            try:
                from scene_snapper import SceneShotSnapper
                self.scene_cuts_ms = SceneShotSnapper.detect_scene_cuts_ffmpeg(video_path, threshold=0.38)
                self.black_intervals_ms = SceneShotSnapper.detect_black_frames_ffmpeg(video_path)
                if self.scene_cuts_ms:
                    print(f"  [FFmpeg Scene Cuts]: Wykryto {len(self.scene_cuts_ms)} cięć montażowych w wideo.")
                if self.black_intervals_ms:
                    print(f"  [FFmpeg Black Fades]: Wykryto {len(self.black_intervals_ms)} przejść przez czerń (Fade to Black).")
            except Exception as e:
                logger.warning(f"Nie udało się wykryć cięć montażowych lub czerni: {e}")

        batches = create_adaptive_batches(
            raw_entries,
            base_batch_size=self.batch_size,
            max_batch_size=min(32, self.batch_size + 8),
            min_scene_batch=16,
            min_leap_batch=12,
            leap_threshold_ms=8000,
            scene_threshold_ms=3800,
            coalesce_tail=True
        )

        discourse_turns = SceneDiscourseGraph.build_discourse_topology([item[1] for item in raw_entries], series_bible=self.series_bible)
        if self.flight_recorder:
            try:
                batches_sum = [
                    {
                        "batch_id": b_idx,
                        "line_count": len(b),
                        "first_id": b[0][0] if b else None,
                        "last_id": b[-1][0] if b else None,
                        "start_ms": int(getattr(b[0][1], "start", 0)) if b and len(b[0]) > 1 else 0,
                        "end_ms": int(getattr(b[-1][1], "end", 0)) if b and len(b[-1]) > 1 else 0
                    }
                    for b_idx, b in enumerate(batches)
                ]
                self.flight_recorder.log_scene_discourse(
                    scene_boundaries=getattr(self, "scene_cuts_ms", []),
                    turns=discourse_turns,
                    batches_summary=batches_sum
                )
            except Exception:
                logger.debug("Rejestracja struktury dyskursu zakończona wyjątkiem", exc_info=True)

        with tqdm(
            total=total_lines,
            desc="Tłumaczenie dialogów",
            unit="linii",
            file=sys.stdout,
            dynamic_ncols=True,
            leave=True,
            mininterval=0.1
        ) as pbar:
            pbar.start_t = time.time()
            already_done = sum(1 for item in raw_entries if item[0] in translated_results)
            if already_done > 0:
                pbar.update(already_done)
                pbar.refresh()

            # Collect all batches that need translation
            tasks_to_run = []
            for b_idx, batch in enumerate(batches):
                untranslated = [item for item in batch if item[0] not in translated_results]
                if untranslated:
                    tasks_to_run.append((b_idx, batch, untranslated))

            all_user_rules = self.user_feedback.list_all()

            if tasks_to_run:
                active_keys_count = len(self.client_pool.get_active_clients()) if hasattr(self, "client_pool") and self.client_pool else 1
                max_workers = min(self.concurrent_batches, len(tasks_to_run))
                if max_workers > 1:
                    print(f"\n  [Kolejka Paczek]: Uruchamianie równoległego tłumaczenia ({max_workers} paczek w locie / {active_keys_count} aktywnych kluczy API)...")
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                        future_to_bidx = {
                            executor.submit(
                                self._process_single_batch,
                                b_idx=b_idx,
                                batch=batch,
                                untranslated_in_batch=untranslated,
                                batches=batches,
                                video_path=video_path,
                                is_ass=is_ass,
                                anime_meta=anime_meta,
                                episode_profile=episode_profile,
                                anime_context_str=anime_context_str,
                                episode_profile_str=episode_profile_str,
                                series_bible_str=series_bible_str,
                                manga_canon_str=manga_canon_str,
                                combined_glossary=combined_glossary,
                                all_user_rules=all_user_rules,
                                history=history,
                                pbar=pbar,
                                translated_results=translated_results
                            ): b_idx
                            for b_idx, batch, untranslated in tasks_to_run
                        }

                        for future in concurrent.futures.as_completed(future_to_bidx):
                            if cancel_check and cancel_check():
                                print("\n[Tłumacz]: Otrzymano sygnał przerwania (⏹ Stop)...")
                                break
                            try:
                                b_res_idx, batch_res, batch_regs, untrans_items, pass1_items, sc_desc, b_cot = future.result()
                                with self.lock:
                                    for orig_idx, text_res in batch_res.items():
                                        translated_results[orig_idx] = text_res
                                    for orig_idx, reg_res in batch_regs.items():
                                        if reg_res:
                                            translated_regions[orig_idx] = reg_res
                                    for it in pass1_items:
                                        if it.get("visual_typesetting"):
                                            translated_typesetting[it["orig_idx"]] = it["visual_typesetting"]
                                        if it.get("addressee"):
                                            translated_addressees[it["orig_idx"]] = it["addressee"]
                                        if it.get("speaker_name") and not is_generic_actor_or_category(it["speaker_name"]):
                                            translated_speakers[it["orig_idx"]] = it["speaker_name"]
                                        if it.get("audio_jp"):
                                            episode_whisper_transcriptions[it["orig_idx"]] = it["audio_jp"]
                                            # Standard 11.1 (LUKA-E2-01): Odświeżenie wpisu w self.episode_scene_genders dla orig_idx
                                            if hasattr(self, "episode_scene_genders") and self.episode_scene_genders is not None and getattr(self, "series_bible", None):
                                                if hasattr(self.series_bible, "infer_scene_cast_from_text"):
                                                    try:
                                                        _, sc_g = self.series_bible.infer_scene_cast_from_text([it.get("en", "")], whisper_texts=[it["audio_jp"]])
                                                        if sc_g == "FEMALE":
                                                            self.episode_scene_genders[it["orig_idx"]] = "kobieta"
                                                        elif sc_g == "MALE":
                                                            self.episode_scene_genders[it["orig_idx"]] = "mężczyzna"
                                                    except Exception:
                                                        logger.debug("Błąd odświeżania płci sceny z audio_jp", exc_info=True)
                                        pl_final = batch_res.get(it["orig_idx"], it.get("pl", ""))
                                        if pl_final:
                                            history.append({
                                                "orig_idx": it["orig_idx"],
                                                "en": it["en"],
                                                "pl": pl_final,
                                                "speaker": it.get("speaker_name", ""),
                                                "speaker_gender": it.get("speaker_gender", ""),
                                                "is_thought": it.get("is_thought", False),
                                                "end_ms": it.get("end_ms", 0),
                                                "start_ms": it.get("start_ms", 0)
                                            })
                                    history.sort(key=lambda x: x.get("orig_idx", 0))
                                    if len(history) > 30:
                                        history[:] = history[-30:]
                                    # Save checkpoint safely
                                    try:
                                        checkpoint_payload = {
                                            "translated_results": dict(translated_results),
                                            "translated_regions": dict(translated_regions),
                                            "translated_typesetting": {
                                                str(k): (v.model_dump() if hasattr(v, "model_dump") else (v.dict() if hasattr(v, "dict") else v))
                                                for k, v in list(translated_typesetting.items())
                                            },
                                            "translated_addressees": dict(translated_addressees),
                                            "translated_speakers": dict(translated_speakers),
                                            "token_usage": {
                                                "f1": dict(self.current_episode_tokens),
                                                "f2": dict(self.verifier.current_episode_tokens) if self.verifier and hasattr(self.verifier, "current_episode_tokens") else None
                                            }
                                        }
                                        with open(checkpoint_path, "w", encoding="utf-8") as cp_file:
                                            json.dump(checkpoint_payload, cp_file, ensure_ascii=False)
                                    except Exception:
                                        logger.debug("Zapis punktu kontrolnego zakończony wyjątkiem", exc_info=True)

                                    if b_cot:
                                        pbar.set_postfix_str(f"{b_cot}...")
                                    pbar.update(len(untrans_items))
                                    pbar.refresh()

                                if progress_callback:
                                    try:
                                        from pricing_guard import PricingGuard
                                        f1_s = self.current_episode_tokens
                                        f2_s = self.verifier.current_episode_tokens if self.verifier else None
                                        cur_c = PricingGuard.calculate_actual_cost_pln(f1_s, f2_s)
                                        recent_prev = [
                                            {"id": it["orig_idx"] + 1, "en": it["en"], "pl": translated_results.get(it["orig_idx"], "")}
                                            for it in pass1_items
                                        ]
                                        progress_callback(len(translated_results), total_lines, recent_prev, cur_c)
                                    except Exception:
                                        logger.debug("Wywołanie funkcji postępu zakończone wyjątkiem", exc_info=True)
                            except Exception as e:
                                pbar.write(f" 🔴 [Niepowodzenie Paczki]: {format_friendly_api_error(e)}")
                                pbar.refresh()
                else:
                    print(f"\n  [Kolejka Paczek]: Płynne tłumaczenie sekwencyjne (1 paczka na raz / rotacja {active_keys_count} aktywnych kluczy API)...")
                    for loop_i, (b_idx, batch, untranslated) in enumerate(tasks_to_run):
                        if cancel_check and cancel_check():
                            print("\n[Tłumacz]: Otrzymano sygnał przerwania (⏹ Stop)...")
                            break
                        if loop_i > 0:
                            time.sleep(0.25)
                        try:
                            b_res_idx, batch_res, batch_regs, untrans_items, pass1_items, sc_desc, b_cot = self._process_single_batch(
                                b_idx=b_idx,
                                batch=batch,
                                untranslated_in_batch=untranslated,
                                batches=batches,
                                video_path=video_path,
                                is_ass=is_ass,
                                anime_meta=anime_meta,
                                episode_profile=episode_profile,
                                anime_context_str=anime_context_str,
                                episode_profile_str=episode_profile_str,
                                series_bible_str=series_bible_str,
                                manga_canon_str=manga_canon_str,
                                combined_glossary=combined_glossary,
                                all_user_rules=all_user_rules,
                                history=history,
                                pbar=pbar,
                                translated_results=translated_results
                            )
                            with self.lock:
                                for orig_idx, text_res in batch_res.items():
                                    translated_results[orig_idx] = text_res
                                for orig_idx, reg_res in batch_regs.items():
                                    if reg_res:
                                        translated_regions[orig_idx] = reg_res
                                for it in pass1_items:
                                    if it.get("visual_typesetting"):
                                        translated_typesetting[it["orig_idx"]] = it["visual_typesetting"]
                                    if it.get("addressee"):
                                        translated_addressees[it["orig_idx"]] = it["addressee"]
                                    if it.get("speaker_name") and not is_generic_actor_or_category(it["speaker_name"]):
                                        translated_speakers[it["orig_idx"]] = it["speaker_name"]
                                    if it.get("audio_jp"):
                                        episode_whisper_transcriptions[it["orig_idx"]] = it["audio_jp"]
                                    pl_final = batch_res.get(it["orig_idx"], it.get("pl", ""))
                                    if pl_final:
                                        history.append({
                                            "orig_idx": it["orig_idx"],
                                            "en": it["en"],
                                            "pl": pl_final,
                                            "speaker": it.get("speaker_name", ""),
                                            "speaker_gender": it.get("speaker_gender", ""),
                                            "is_thought": it.get("is_thought", False)
                                        })
                                history.sort(key=lambda x: x.get("orig_idx", 0))
                                if len(history) > 30:
                                    history[:] = history[-30:]
                                try:
                                    checkpoint_payload = {
                                        "translated_results": translated_results,
                                        "translated_regions": translated_regions,
                                        "translated_typesetting": {
                                            str(k): (v.model_dump() if hasattr(v, "model_dump") else (v.dict() if hasattr(v, "dict") else v))
                                            for k, v in translated_typesetting.items()
                                        },
                                        "translated_addressees": translated_addressees,
                                        "token_usage": {
                                            "f1": self.current_episode_tokens,
                                            "f2": self.verifier.current_episode_tokens if self.verifier else None
                                        }
                                    }
                                    with open(checkpoint_path, "w", encoding="utf-8") as cp_file:
                                        json.dump(checkpoint_payload, cp_file, ensure_ascii=False)
                                except Exception:
                                    logger.debug("Zapis punktu kontrolnego zakończony wyjątkiem", exc_info=True)
                                if b_cot:
                                    pbar.set_postfix_str(f"{b_cot}...")
                                pbar.update(len(untrans_items))
                                pbar.refresh()

                            if progress_callback:
                                try:
                                    from pricing_guard import PricingGuard
                                    f1_s = self.current_episode_tokens
                                    f2_s = self.verifier.current_episode_tokens if self.verifier else None
                                    cur_c = PricingGuard.calculate_actual_cost_pln(f1_s, f2_s)
                                    recent_prev = [
                                        {"id": it["orig_idx"] + 1, "en": it["en"], "pl": translated_results.get(it["orig_idx"], "")}
                                        for it in pass1_items
                                    ]
                                    progress_callback(len(translated_results), total_lines, recent_prev, cur_c)
                                except Exception:
                                    logger.debug("Wywołanie funkcji postępu zakończone wyjątkiem", exc_info=True)
                        except Exception as e:
                            pbar.write(f" 🔴 [Niepowodzenie Paczki]: {format_friendly_api_error(e)}")
                            pbar.refresh()

            # 6.9. Zero-Gap Healing Pass: uzupełnienie ewentualnych brakujących kwestii po awariach paczek
            missing_entries = [item for item in raw_entries if item[0] not in translated_results]
            if missing_entries:
                pbar.write(f"\n  [Zero-Gap Guard]: Wykryto {len(missing_entries)} nieprzetłumaczonych kwestii po pętli głównej. Uruchamianie pasażu uzupełniającego (Healing Pass)...")
                healing_batches = create_adaptive_batches(missing_entries, base_batch_size=min(12, len(missing_entries)), max_batch_size=16)
                for h_bidx, h_batch in enumerate(healing_batches):
                    try:
                        _, h_res, h_regs, _, h_pass1, _, h_cot = self._process_single_batch(
                            b_idx=len(batches) + h_bidx,
                            batch=h_batch,
                            untranslated_in_batch=h_batch,
                            batches=batches,
                            video_path=video_path,
                            is_ass=is_ass,
                            anime_meta=anime_meta,
                            episode_profile=episode_profile,
                            anime_context_str=anime_context_str,
                            episode_profile_str=episode_profile_str,
                            series_bible_str=series_bible_str,
                            manga_canon_str=manga_canon_str,
                            combined_glossary=combined_glossary,
                            all_user_rules=all_user_rules,
                            history=history,
                            pbar=pbar,
                            translated_results=translated_results
                        )
                        with self.lock:
                            for orig_idx, text_res in h_res.items():
                                translated_results[orig_idx] = text_res
                            for orig_idx, reg_res in h_regs.items():
                                if reg_res:
                                    translated_regions[orig_idx] = reg_res
                            for it in h_pass1:
                                if it.get("visual_typesetting"):
                                    translated_typesetting[it["orig_idx"]] = it["visual_typesetting"]
                                if it.get("addressee"):
                                    translated_addressees[it["orig_idx"]] = it["addressee"]
                            if h_cot:
                                pbar.set_postfix_str(f"{h_cot}...")
                            pbar.update(len(h_res))
                            pbar.refresh()

                        if progress_callback:
                            try:
                                from pricing_guard import PricingGuard
                                f1_s = self.current_episode_tokens
                                f2_s = self.verifier.current_episode_tokens if self.verifier else None
                                cur_c = PricingGuard.calculate_actual_cost_pln(f1_s, f2_s)
                                recent_prev = [
                                    {"id": it["orig_idx"] + 1, "en": it["en"], "pl": translated_results.get(it["orig_idx"], "")}
                                    for it in h_pass1
                                ]
                                progress_callback(len(translated_results), total_lines, recent_prev, cur_c)
                            except Exception:
                                logger.debug("Wywołanie funkcji postępu zakończone wyjątkiem", exc_info=True)
                    except Exception as h_err:
                        pbar.write(f"  [Zero-Gap Guard]: Niepowodzenie paczki uzupełniającej ({h_err}). Próba ratunkowa linijka po linijce...")
                        pbar.refresh()
                        for s_item in h_batch:
                            if s_item[0] in translated_results:
                                continue
                            try:
                                _, s_res, s_regs, _, s_pass1, _, s_cot = self._process_single_batch(
                                    b_idx=len(batches) + 500,
                                    batch=[s_item],
                                    untranslated_in_batch=[s_item],
                                    batches=batches,
                                    video_path=video_path,
                                    is_ass=is_ass,
                                    anime_meta=anime_meta,
                                    episode_profile=episode_profile,
                                    anime_context_str=anime_context_str,
                                    episode_profile_str=episode_profile_str,
                                    series_bible_str=series_bible_str,
                                    manga_canon_str=manga_canon_str,
                                    combined_glossary=combined_glossary,
                                    all_user_rules=all_user_rules,
                                    history=history,
                                    pbar=pbar,
                                    translated_results=translated_results
                                )
                                with self.lock:
                                    for orig_idx, text_res in s_res.items():
                                        translated_results[orig_idx] = text_res
                                    for orig_idx, reg_res in s_regs.items():
                                        if reg_res:
                                            translated_regions[orig_idx] = reg_res
                                    for it in s_pass1:
                                        if it.get("visual_typesetting"):
                                            translated_typesetting[it["orig_idx"]] = it["visual_typesetting"]
                                        if it.get("addressee"):
                                            translated_addressees[it["orig_idx"]] = it["addressee"]
                                    if s_cot:
                                        pbar.set_postfix_str(f"{s_cot}...")
                                    pbar.update(len(s_res))
                                    pbar.refresh()
                            except Exception as s_err:
                                pbar.write(f"  [Zero-Gap Guard]: Awaryjna linia #{s_item[0] + 1} nie powiodła się: {s_err}")
                                pbar.refresh()

            # Końcowa weryfikacja integralności Zero-Gap przed zapisem
            missing_final = [item for item in raw_entries if item[0] not in translated_results and not is_song_line(item[1], item[2])]
            if missing_final:
                pbar.write(f"\n  ℹ️ [TELEMETRIA ZERO-GAP]: Nie udało się przetłumaczyć {len(missing_final)} kwestii dialogowych!")
                pbar.write(f"     Plik checkpointu zostanie zachowany w celu bezstratnego dokończenia.")
            pbar.refresh()

        # 7. Construct final subtitle file preserving styles, positioning, and typesetting
        final_subs = pysubs2.SSAFile()
        # Copy full stylesheet (fonts, colors, positions)
        final_subs.styles = subs.styles.copy()
        final_subs.info = subs.info.copy()
        # Force WrapStyle: 2 (no arbitrary line wrapping by video player)
        final_subs.info["WrapStyle"] = "2"

        try:
            playres_x = int(subs.info.get("PlayResX", 1920) or 1920)
        except Exception:
            playres_x = 1920
        try:
            playres_y = int(subs.info.get("PlayResY", 1080) or 1080)
        except Exception:
            playres_y = 1080
        if playres_x <= 0:
            playres_x = 1920
        if playres_y <= 0:
            playres_y = 1080

        for orig_idx, orig_event, _, ts_prefix in raw_all_entries:
            master_id = sub_to_master.get(orig_idx, orig_idx)
            
            # If line is an OP/ED song, preserve original event text, styling and karaoke tags exactly 1:1
            if is_song_line(orig_event, orig_event.text):
                new_event = orig_event.copy()
                final_subs.events.append(new_event)
                continue

            raw_pl = translated_results.get(master_id)
            if not raw_pl:
                raw_pl = orig_event.text

            clean_translated_text = sanitize_sub_text(raw_pl)
            if not clean_translated_text:
                clean_translated_text = sanitize_sub_text(orig_event.text)

            # Professional AVT Anti-Clutter: Drop isolated paralinguistic grunts and interjections
            is_sign_flag = detect_event_visual_type(orig_event, ts_prefix, style_report=getattr(self, "style_report", None))["is_sign"]
            if is_isolated_paralinguistic_clutter(orig_event.text, clean_translated_text, is_sign=is_sign_flag):
                continue

            if not self.keep_honorifics and not is_sign_flag:
                # Strip Japanese honorific suffixes (-senpai, -kun, -chan, -san, -sama, -sensei)
                clean_translated_text = re.sub(
                    r"([A-ZĄĆĘŁŃÓŚŹŻa-ząćęłńóśźż]+)-(?:senpai|kun|chan|san|sama|sensei|dono|tan|pyon)\b",
                    r"\1",
                    clean_translated_text,
                    flags=re.IGNORECASE
                )

            # Typesetting Proximity 2.0: Anchor signs/titles to the detected visual quadrant or fallback to top
            clean_check = clean_translated_text.strip()
            ts_prefix_applied = sanitize_ts_prefix_for_translation(ts_prefix or "")
            item_region = translated_regions.get(master_id)
            style_clean = (orig_event.style or "").lower()
            style_is_sub = bool(re.search(r"\bsubtitles?\b", style_clean))
            has_sign_style = not style_is_sub and (
                bool(re.search(r"\b(sign|signs|title|titles|typeset|typesetting|caption|captions)\b", style_clean))
                or style_clean.startswith("caption")
            )
            is_title_card = bool(re.match(r"^(episode|odcinek|chapter|rozdział|act|akt|part|część)\s+(\d+|[ivxlcdm]+)", clean_check, re.IGNORECASE))

            if is_sign_flag or is_title_card or (clean_check.startswith("[") and clean_check.endswith("]")) or has_sign_style:
                target_style = getattr(subs, "styles", {}).get(orig_event.style) if hasattr(subs, "styles") else None
                item_ts_data = translated_typesetting.get(master_id)
                if item_ts_data:
                    if isinstance(item_ts_data, dict):
                        if "screen_region" not in item_ts_data and item_region:
                            item_ts_data["screen_region"] = item_region
                    else:
                        try:
                            if not getattr(item_ts_data, "screen_region", None) and item_region:
                                setattr(item_ts_data, "screen_region", item_region)
                        except Exception:
                            logger.debug("Przypisanie regionu ekranowego zakończone wyjątkiem", exc_info=True)

                    ts_prefix_applied = TypesettingColorMatcher.generate_pixel_perfect_ass_tags(
                        typesetting_data=item_ts_data,
                        playres_x=playres_x,
                        playres_y=playres_y,
                        prefix=ts_prefix_applied,
                        style=target_style
                    )
                else:
                    if r"\pos" in ts_prefix_applied:
                        # Preserve original subtitle's custom coordinates without corrupting
                        pass
                    elif item_region:
                        pos_tag = TypesettingColorMatcher.calculate_optimal_sign_position(region=item_region)
                        ts_prefix_applied = re.sub(r"\{\\an\d\}|\\an\d", "", ts_prefix_applied).strip()
                        ts_prefix_applied = f"{pos_tag}{ts_prefix_applied}"
                    elif not (r"\an" in ts_prefix_applied or r"\pos" in ts_prefix_applied):
                        ts_prefix_applied = r"{\an8}" + ts_prefix_applied

                    # Sign Contrast & Visibility Guard (Filar AVT Contrast Invariance)
                    ts_prefix_applied = TypesettingColorMatcher.ensure_sign_contrast(ts_prefix_applied, style=target_style)

            # Reattach Typesetting tags to translated text
            full_event_text = f"{ts_prefix_applied}{clean_translated_text}" if ts_prefix_applied else clean_translated_text

            new_event = orig_event.copy()
            new_event.text = full_event_text
            new_event.addressee = translated_addressees.get(master_id)
            spk = translated_speakers.get(master_id)
            is_offs = getattr(orig_event, "is_offscreen", False) or "offscreen" in str(getattr(orig_event, "style", "")).lower()
            new_event = synchronize_ass_event_metadata_and_styles(new_event, speaker_name=spk, is_offscreen=is_offs)
            new_event.source_en = getattr(orig_event, "plaintext", None) or orig_event.text
            final_subs.events.append(new_event)

        # 7.0. Format simultaneous dialogues (Simultaneous Dialogue AVT)
        final_subs.events = apply_simultaneous_dialogue_formatting(final_subs.events)

        # 7.1. Visual Sign Detector & OCR for subtitle gaps
        if video_path and os.path.exists(video_path):
            try:
                from sign_detector import VisualSignDetector
                gaps = VisualSignDetector.find_subtitle_gaps(final_subs, min_gap_ms=3500, margin_ms=1500)
                if gaps:
                    detected_signs = VisualSignDetector.detect_signs_in_gaps(
                        video_path=video_path,
                        gaps=gaps,
                        client=self.client,
                        model=self.model_phase1
                    )
                    if detected_signs:
                        for sign_ev in detected_signs:
                            final_subs.events.append(sign_ev)
                        final_subs.events.sort(key=lambda ev: ev.start)
            except Exception as e:
                logger.warning(f"Wizyjny Detektor Plansz: Pomijanie detekcji plansz ({e})")

        # 7.2. Cinematic Shot Snapping (SceneShotSnapper - Netflix AVT Standard)
        if video_path and os.path.exists(video_path):
            try:
                from scene_snapper import SceneShotSnapper
                cuts = getattr(self, "scene_cuts_ms", None) or SceneShotSnapper.detect_scene_cuts_ffmpeg(video_path)
                if cuts:
                    kfs = getattr(self, "keyframes_ms", None)
                    final_subs.events, snapped_cnt = SceneShotSnapper.snap_subtitles_to_cuts_and_keyframes(final_subs.events, cuts, keyframes_ms=kfs)
                    if snapped_cnt > 0:
                        logger.info(f"[SceneShotSnapper]: Dociągnięto {snapped_cnt} krawędzi napisów do cięć montażowych i klatek kluczowych.")
            except Exception as e:
                logger.warning(f"SceneShotSnapper: Pomijanie ({e})")

        final_subs.events.sort(key=lambda ev: ev.start)

        # 7.3. Global Episode Quality Gate & Human-Eye Common Sense Audit (0.00 PLN)
        try:
            from avt_linter import EpisodeQualityGate
            try:
                final_subs, qg_fixes = EpisodeQualityGate.audit_and_fix_entire_episode(
                    final_subs,
                    custom_glossary=combined_glossary,
                    user_feedback_rules=all_user_rules,
                    character_registry=self.character_registry,
                    series_bible=getattr(self, "series_bible", None),
                    line_addressees=translated_addressees,
                    line_speakers=translated_speakers,
                    source_subs=subs,
                    whisper_transcriptions=episode_whisper_transcriptions,
                    enforce_line_split=True,
                    strict_positive_domain=True
                )
            except TypeError:
                final_subs, qg_fixes = EpisodeQualityGate.audit_and_fix_entire_episode(
                    final_subs,
                    custom_glossary=combined_glossary,
                    user_feedback_rules=all_user_rules,
                    character_registry=self.character_registry,
                    series_bible=getattr(self, "series_bible", None),
                    line_addressees=translated_addressees,
                    line_speakers=translated_speakers,
                    source_subs=subs,
                    whisper_transcriptions=episode_whisper_transcriptions,
                    enforce_line_split=True
                )
            if qg_fixes:
                en_warnings = [f for f in qg_fixes if "nieprzetłumaczony angielski" in f]
                if en_warnings:
                    print(f"\n  ℹ️ [RAPORT EPISODE QUALITY GATE]: Wykryto {len(en_warnings)} nieprzetłumaczonych kwestii angielskich:")
                    for ew in en_warnings[:5]:
                        print(f"     └─ {ew}")
                    if len(en_warnings) > 5:
                        print(f"     └─ ... i {len(en_warnings) - 5} kolejnych.")
                logger.info(f"[EpisodeQualityGate]: Przeprowadzono całościowy audyt zdroworozsądkowy ({len(qg_fixes)} poprawek integralności).")
                for f in qg_fixes[:5]:
                    logger.info(f"  ├─ {f}")
                if len(qg_fixes) > 5:
                    logger.info(f"  └─ ... i {len(qg_fixes) - 5} kolejnych poprawek.")
                if getattr(self, "series_bible", None):
                    try:
                        self.series_bible.assimilate_quality_gate_invariants(qg_fixes)
                        logger.info("[SeriesBible]: Pomyślnie zasymilowano trwałe niezmienniki z EpisodeQualityGate do Biblii Serialu.")
                    except Exception as e_sb:
                        logger.warning(f"[SeriesBible]: Niepowodzenie asymilacji niezmienników ({e_sb})")
        except Exception as e:
            logger.warning(f"EpisodeQualityGate: Pomijanie ({e})")

        if not output_path:
            stem = subs_file.stem
            if stem.endswith(".en"):
                stem = stem[:-3]
            ext = subs_file.suffix
            if video_path:
                output_path = str(Path(video_path).parent / f"{Path(video_path).stem}{ext}")
            else:
                output_path = str(subs_file.parent / f"{stem}{ext}")

        # Standard 9.0/9.1 (Sekcja 2 pkt 5, pkt 6, pkt 7, R3.9):
        # 1. Konwersja znaków \n 1:1 do \N w .ass.
        # 2. Czyszczenie pola Name i synchronizacja z wyznaczonym speaker_name oraz offscreen/kursywa.
        # 3. Rozbicie kwestii przekraczających limity (> 2 wiersze) na kolejne zdarzenia Dialogue:
        for ev in final_subs.events:
            is_offs = getattr(ev, "is_offscreen", False) or "offscreen" in str(getattr(ev, "style", "")).lower()
            ev = synchronize_ass_event_metadata_and_styles(ev, speaker_name=getattr(ev, "name", None), is_offscreen=is_offs)
        final_subs.events = split_oversized_ass_events(final_subs.events)

        final_subs.save(output_path, encoding="utf-8")
        
        # Remove checkpoint and temporary profile cache files only upon truly 100% complete dialogue translation
        missing_dialogue_at_end = [item for item in raw_entries if item[0] not in translated_results and not is_song_line(item[1], item[2])]
        if not missing_dialogue_at_end:
            if checkpoint_path.exists():
                try:
                    os.remove(str(checkpoint_path))
                except OSError:
                    pass

            if profile_cache_path and os.path.exists(profile_cache_path):
                try:
                    os.remove(profile_cache_path)
                except OSError:
                    pass
        else:
            print(f"  ⚠️ [AUTOZAPIS]: Plik checkpointu {checkpoint_path.name} został ZACHOWANY, ponieważ brakuje {len(missing_dialogue_at_end)} kwestii dialogowych. Uruchom ponowne tłumaczenie, aby bezstratnie dokończyć brakujące linie!")

        print(f"\n[Sukces] Przetłumaczone, wyczyszczone napisy z zachowanym Typesettingiem zapisano w: {output_path}")

        # Calculate and display total real episode cost based on token usage
        try:
            from pricing_guard import PricingGuard
            f1_stats = self.current_episode_tokens
            f2_stats = self.verifier.current_episode_tokens if self.verifier else None
            breakdown = PricingGuard.calculate_actual_cost_breakdown(f1_stats, f2_stats)
            actual_cost_pln = breakdown["net_pln"]
            cost_gross_pln = breakdown["gross_pln"]
            cost_f1_pln = breakdown["f1_net_pln"]
            cost_f2_pln = breakdown["f2_net_pln"]
            std_gross_pln = breakdown["standard_gross_pln"]
            cache_savings_pln = breakdown["savings_pln"]

            print("\n" + "═" * 72)
            print(f"  💰 RZECZYWISTY KOSZT ODCINKA: {actual_cost_pln:.2f} PLN netto (~{cost_gross_pln:.2f} PLN brutto z VAT 23%)")
            print(f"  ├─ Faza 1 (Szkic & OCR Sparse): {cost_f1_pln:.2f} PLN netto")
            print(f"  │   └─ Wejście: {f1_stats.get('prompt',0):,} tok (Cached: {f1_stats.get('cached',0):,}) | Wyjście: {f1_stats.get('output',0):,} tok")
            if f2_stats:
                print(f"  ├─ Faza 2 (Reżyseria & Elastic CoT): {cost_f2_pln:.2f} PLN netto")
                print(f"  │   └─ Wejście: {f2_stats.get('prompt',0):,} tok (Cached: {f2_stats.get('cached',0):,}) | Wyjście+CoT: {f2_stats.get('output',0):,} tok")
            print(f"  ├─ 🛡️ Rabat Context Cache (-90%): Zaoszczędzono ~{cache_savings_pln:.2f} PLN (Standardowo bez rabatu: ~{std_gross_pln:.2f} PLN brutto)")
            print(f"  └─ ℹ️ Rozliczenia Google Cloud: Wyciągi bankowe zawierają 23% VAT i sumują wszystkie próby oraz testy z danego dnia.")
            print("═" * 72 + "\n")

            if getattr(self, "series_bible", None):
                ref_name = Path(video_path).stem if video_path else (Path(subs_path).stem if subs_path else "Odcinek")
                try:
                    self.series_bible.register_episode_execution(
                        episode_name=ref_name,
                        batch_count=len(batches),
                        dialogue_count=total_lines,
                        cost_pln=actual_cost_pln
                    )
                except Exception:
                    logger.debug("Kalkulacja kosztów końcowych zakończona wyjątkiem", exc_info=True)
        except Exception:
            logger.debug("Finalizacja rozliczenia zadania zakończona wyjątkiem", exc_info=True)

        if self.flight_recorder:
            try:
                self.flight_recorder.log_quality_gate_and_pricing(
                    quality_gate_fixes=qg_fixes if 'qg_fixes' in locals() else [],
                    avt_metrics={"total_lines": total_lines, "events_count": len(final_subs.events)},
                    pricing_summary=breakdown if 'breakdown' in locals() else {}
                )
                self.flight_recorder.finalize()
            except Exception:
                logger.debug("Finalizacja rejestratora zdarzeń zakończona wyjątkiem", exc_info=True)

        # Clean up server-side Context Cache objects across all clients in the pool to avoid storage fees
        try:
            from context_cache import ContextCacheManager
            if hasattr(self, "client_pool") and self.client_pool and hasattr(self.client_pool, "clients"):
                for c in self.client_pool.clients:
                    ContextCacheManager.cleanup_all_active_caches(c)
            else:
                ContextCacheManager.cleanup_all_active_caches(self.client)
            if self.verifier and hasattr(self.verifier, "client") and self.verifier.client != self.client:
                ContextCacheManager.cleanup_all_active_caches(self.verifier.client)
        except Exception:
            logger.debug("Czyszczenie aktywnych obiektów pamięci podręcznej zakończone wyjątkiem", exc_info=True)

        return output_path

# Alias for backwards compatibility
TranslatorEngine = MultimodalTranslator
Translator = MultimodalTranslator

if __name__ == "__main__":
    from main import main
    main()

