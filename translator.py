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

# Force full UTF-8 support (including Japanese Kanji/Kana characters)
if sys.platform == "win32":
    try:
        import ctypes
        ctypes.windll.kernel32.SetConsoleOutputCP(65001)
        ctypes.windll.kernel32.SetConsoleCP(65001)
    except Exception:
        pass
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import re
import time
import json
import logging
import threading
import tempfile
import sqlite3
import unicodedata
import concurrent.futures
from typing import List, Optional, Dict, Any, Tuple
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
from metadata import get_anime_context, format_anime_context_for_prompt
from memory import TranslationMemory, format_translation_memory_for_prompt
from profiler import EpisodeProfiler, EpisodeProfile, format_episode_profile_for_prompt, format_lean_episode_brief
from whisper_engine import JapaneseWhisperEngine
from whisper_disambiguator import WhisperDisambiguator
from avt_linter import AVTLinter
from romaji_helper import to_romaji
from series_memory import (
    SeriesBible, extract_clean_speaker_name, INHERENT_FEMALE_NOUNS, INHERENT_MALE_NOUNS,
    GENERIC_CATEGORY_TAGS, is_generic_actor_or_category, FEMALE_ROLE_KEYWORDS,
    MALE_ROLE_KEYWORDS, BOY_ROLE_KEYWORDS
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
from client_factory import format_friendly_api_error, patch_google_genai_schema_sanitizer

patch_google_genai_schema_sanitizer()

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
    # Strip restrictive clip/iclip rectangles designed for shorter English text
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

    style_lower = (event.style or "").lower()
    name_lower = (event.name or "").lower()
    ts_lower = (ts_prefix or "").lower()
    text_raw = (event.plaintext or event.text or "").strip()

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

    if re.match(r"^(episode|odcinek|chapter|rozdział|act|akt|part|część)\s+(\d+|[ivxlcdm]+)", text_raw, re.IGNORECASE):
        is_sign = True
        details.append("plansza tytułowa odcinka/rozdziału")

    if r"\frz" in ts_lower or r"\org" in ts_lower or r"\clip" in ts_lower or r"\p1" in ts_lower:
        is_sign = True
        details.append("obrócony/wklejony graficznie w perspektywę kadrów")

    if r"\pos" in ts_lower and not is_sign:
        # Check if it has custom graphic colors or rotation
        if r"\c&h" in ts_lower or r"\1c&h" in ts_lower or r"\3c&h" in ts_lower:
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
    (e.g., 'Uh', 'Och!', 'Uch', 'Hmph', 'Ah', 'Gah', 'Tch') that do not carry
    lexical meaning and pollute the screen against professional AVT standards.
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
            return "W audio pada 'Kanojo-tachi' (kobiety) -> Popraw 'Oni/Ich' na 'One/Je/Kobiety' (Filar XCVI)."

    # 2. Kikanaide vs 'Wolę nie wiedzieć'
    if "聞かないで" in jp_text or "kikanaide" in jp_lower:
        if any(w in pl_lower for w in ["wolę nie wiedzieć", "nie chcę wiedzieć", "nie chcę słyszeć"]):
            return "W audio pada 'Kikanaide' (prośba mówcy: 'Nie pytaj') -> Popraw 'Wolę nie wiedzieć' na 'Nawet nie pytaj...' (Filar CI)."

    # 3. Kure / Kase vs 'Proszę'
    if ("くれ" in jp_text or "kure" in jp_lower or "kase" in jp_lower) and "kudasai" not in jp_lower:
        if pl_lower.startswith("proszę") or "czy możesz" in pl_lower or "czy mógłbyś" in pl_lower:
            return "W audio pada szorstki tryb rozkazujący (-kure/-kase) -> Zamień sztuczne 'Proszę...' na bezpośredni rozkaz (Filar CIII)."

    # 4. Yobisute, -kun, -chan, and peer -san vs artificial 'Pan / Pani'
    honorific_noble_keys = ["様", "先生", "殿", "隊長", "部長", "課長", "社長", "師匠", "sama", "sensei", "dono", "taichou", "buchou", "kachou", "shachou", "shishou"]
    if any(p in pl_lower for p in ["panie ", "pani ", "pan ", "pana ", "panu ", "panią "]) and not any(s in jp_text for s in honorific_noble_keys):
        if not any(s in jp_lower for s in honorific_noble_keys):
            if any(s in jp_text for s in ["君", "くん", "ちゃん"]) or any(s in rom_lower for s in ["kun", "chan", "-kun", "-chan"]):
                return "W audio pada rówieśniczy sufiks '-kun' / '-chan' -> Stosuj samo imię na 'ty' w wołaczu bez form pan/pani (Filar XLVI / C)."
            return "W audio brak sufiksu wyższego szacunku (-sama/-sensei/-dono) -> Usuń sztuczny dystans 'Pan/Pani' i zastosuj samo imię w wołaczu (Filar C)."

    # 5. Haragei & Trailing Particles (-kedo, -kara, -tara) vs completing the sentence
    trailing_keys = ["kedo", "kara", "tara", "monode", "shi"]
    if any(clean_jp.endswith(p) for p in ["けど", "から", "たら", "し"]) or any(rom_lower.endswith(k) for k in trailing_keys):
        if len(pl_text.split()) > 7 and not pl_text.endswith("..."):
            return "Kwestia urywa się na partykułę zawieszenia (Haragei) -> Zastosuj wielokropek niedopowiedzenia zamiast sztucznego dopowiadania reszty zdania (Filar CV)."

    # 6. Aizuchi (Un, Sou, Fumu) vs wordy subtitles
    aizuchi_keys = ["un", "sou", "fumu", "ee", "sou da", "sou da ne", "sou desu ne"]
    if clean_jp in ["うん", "そう", "ふむ", "ええ", "そうだ", " glass", "そうですね"] or rom_lower in aizuchi_keys:
        if len(pl_text.split()) > 2:
            return "Krótkie Aizuchi podtrzymujące kontakt -> Zredukuj do oszczędnego 'Mhm' / 'No' / 'Jasne' (Filar CVI)."

    # 7. Oyaji vs stiff 'mój ojciec'
    if ("親父" in clean_jp or "おやじ" in clean_jp or "oyaji" in rom_lower) and "mój ojciec" in pl_lower:
        return "W audio pada potoczne/buntownicze 'Oyaji' -> Zastąp sztywne 'mój ojciec' naturalnym 'stary' lub 'ojciec' (Filar CIX)."

    # 8. Giri and Sumimasen in gratitude/saving context
    if ("済みません" in clean_jp or "すみません" in clean_jp or "sumimasen" in rom_lower) and any(w in en_text.lower() for w in ["saved", "water", "food", "help", "thank"]):
        if pl_lower.startswith("przepraszam"):
            return "W audio pada 'Sumimasen' jako dług wdzięczności (Giri) -> Zamień monotonne 'Przepraszam' na 'Dziękuję!' / 'Nie trzeba było...' / 'Wybacz kłopot...' (Filar CX & CLI)."

    # 9. Ii desu / Kekkou desu in refusal vs health state
    if ("いいです" in clean_jp or "ii desu" in rom_lower or "kekkou" in rom_lower or "結構" in clean_jp):
        if any(w in pl_lower for w in ["nic mi nie jest", "nic mi... nie jest", "wszystko w porządku", "dobrze się czuję"]):
            return "W audio pada 'ii desu' (odmowa / rezygnacja) -> Zastąp błędny stan zdrowia ('Nic mi nie jest') poprawną odmową: 'Ja... podziękuję.' / 'Nie mam ochoty.' / 'Ja zostanę.' (Filar CXVII)."

    # 10. Sasuga (reputation / praise / typical excellence) vs literal whole/all calque
    if "さすが" in clean_jp or "流石" in clean_jp or "sasuga" in rom_lower:
        if pl_lower.startswith("całe ") or pl_lower.startswith("cały ") or pl_lower.startswith("to cały ") or "wszyscy" in pl_lower:
            return "W audio pada 'Sasuga' (uznanie/podziw dla kunsztu i reputacji: 'jak przystało na...') -> Zamień mylącą kalkę ('Całe plemię...') na szlachetne 'Jak przystało na [postać/plemię]...' / 'Tego należało się spodziewać po...' (Filar CXI)."

    # 11. Warukatta / Warikatta / Warui (singular informal apology) vs plural 'Wybaczcie'
    warui_keys = ["warukatta", "warikatta", "warui", "warui na", "warukatta na", "warukattana", "warikattana"]
    if any(k in rom_lower for k in warui_keys) or any(k in clean_jp for k in ["悪かった", "悪い"]):
        if any(w in pl_lower for w in ["wybaczcie", "przeproście", "przepraszamy"]):
            return "W audio pada pojedyncze 'Warukatta na / Warui' (Moja wina / Wybacz) -> Zamień błędną liczbę mnogą ('Wybaczcie') na naturalną liczbę pojedynczą: 'Wybacz...' lub 'Moja wina...' (Filar CXXVI)."

    # 12. Wakaru / Wakaruu (empathic agreement / shared feeling) vs adjective exclamations (Genialne/Wspaniale)
    wakaru_keys = ["wakaru", "wakaruu", "wakaru-", "wakaru yo", "wakaru wa", "wakaru na", "wakaruze", "wakaruzo"]
    if any(clean_jp.startswith(k) or clean_jp == k for k in ["分かる", "わかる", "分かるー", "わかるー", "分かる～", "わかる～", "分かるよ", "わかるよ"]) or any(k in rom_lower for k in wakaru_keys):
        if any(w in pl_lower for w in ["genialne", "wspaniale", "doskonale", "świetnie", "bystry", "mądry"]):
            return "W audio pada 'Wakaru / Wakaruu' (empatyczna zgoda/współodczuwanie: 'No nie?' / 'Totalnie!' / 'Też tak myślę!' / 'Prawda?' / 'Wiem!') -> Odrzuć błędną przymiotnikową ocenę ('Genialne!') na rzecz naturalnej polskiej zgody i potwierdzenia (Filar XLIII / CVI)."

    # 13. Sore na / Sore! / Sore da (youth agreement / absolute validation) vs literal 'To to!' / 'Ta rzecz!'
    sorena_keys = ["sore na", "sore!", "sore da", "sore da yo", "sore da na"]
    if any(clean_jp.startswith(k) or clean_jp == k for k in ["それな", "それ！", "それだ", "それだよ"]) or any(k in rom_lower for k in sorena_keys):
        if any(w in pl_lower for w in ["ta rzecz", "to to", "właśnie to coś", "tamtą rzecz"]):
            return "W audio pada potoczne 'Sore na!' (absolutna zgoda z rozmówcą) -> Zamień dosłowną kalkę na żywe: 'Otóż to!' / 'Rel!' / 'W punkt!' / 'Święta prawda!' (Filar XLIII)."

    # 14. Tashika ni / Tashika ni ne (conceding a point / admitting truth) vs stiff 'Z pewnością'
    tashika_keys = ["tashika ni", "tashikani", "tashika ni ne", "tashikani ne"]
    if any(clean_jp.startswith(k) or clean_jp == k for k in ["確かに", "たしかに", "確かにね", "たしかにね"]) or any(k in rom_lower for k in tashika_keys):
        if pl_lower.startswith("z pewnością") or pl_lower.startswith("pewnie tak"):
            return "W audio pada 'Tashika ni' (przyznanie racji: 'W sumie racja' / 'To prawda' / 'Faktycznie') -> Zastąp sztywne 'Z pewnością...' naturalnym przyznaniem racji (Filar XLIII)."

    # 15. Naruhodo / Naruhodo ne (realization / understanding mechanics) vs stiff 'Rzeczywiście' / 'Rozumiem'
    naruhodo_keys = ["naruhodo", "naruhodone", "naruhodo na", "naruhodo ne"]
    if any(clean_jp.startswith(k) or clean_jp == k for k in ["なるほど", "なるほどね", "なるほどな"]) or any(k in rom_lower for k in naruhodo_keys):
        if pl_lower == "rzeczywiście." or pl_lower == "rozumiem.":
            return "W audio pada 'Naruhodo' (olśnienie/zrozumienie toku myśli) -> Zastąp urzędowe 'Rozumiem/Rzeczywiście' żywym: 'A, w ten sposób!' / 'Wszystko jasne.' / 'A, o to chodzi.' (Filar XLIII)."

    # 16. Sou iu koto ka / Sou iu koto ne (deducing the truth) vs literal 'Więc tak to jest'
    souiukoto_keys = ["sou iu koto ka", "sou iu koto ne", "souiu koto ka", "souiukoto ka"]
    if any(k in clean_jp for k in ["そういうことか", "そういう事か", "そういうことね"]) or any(k in rom_lower for k in souiukoto_keys):
        if "więc tak to jest" in pl_lower or "taka to rzecz" in pl_lower:
            return "W audio pada 'Sou iu koto ka' (domyślenie się sedna sprawy) -> Zastąp kalkę naturalnym: 'A więc o to chodzi!' / 'Czyli tak to wygląda!' (Filar XLIII)."

    # 17. Uso / Uso desho / Masaka (disbelief / shock) vs literal 'Kłamstwo!'
    uso_keys = ["uso", "uso-", "uso!", "uso desho", "uso daro", "usodesho", "masaka"]
    if clean_jp in ["嘘", "うそ", "うそー", "嘘でしょ", "うそでしょ", "まさか"] or rom_lower in uso_keys:
        if any(w in pl_lower for w in ["kłamstwo", "kłamiesz", "to kłamstwo", "kłamco"]):
            return "W audio pada wykrzyknik zdziwienia 'Uso! / Uso desho?' -> Zamień nienaturalne 'Kłamstwo!' na naturalne: 'Żartujesz?' / 'Serio?' / 'Bez jaj!' / 'Nie wierzę!' (Filar XLIII)."

    # 18. Maji de? / Maji ka? (youth disbelief) vs stiff 'Czy to prawda?'
    maji_keys = ["maji de", "majide", "maji ka", "majika", "maji kayo", "majikayo"]
    if any(k in clean_jp for k in ["マジで", "まじで", "マジか", "まじか", "マジかよ"]) or any(k in rom_lower for k in maji_keys):
        if any(w in pl_lower for w in ["czy to prawda", "prawdziwie", "prawdziwe to"]):
            return "W audio pada młodzieżowe 'Maji de? / Maji ka?' -> Zamień sztywne 'Czy to prawda?' na żywe: 'Serio?' / 'Poważnie?' / 'Nie gadaj!' (Filar XLIII)."

    # 19. Yappari / Yahari / Yappa (confirmation of suspicion) vs literal 'Po wszystkim' / 'Zgodnie z oczekiwaniami'
    yappari_keys = ["yappari", "yahari", "yappa", "yappari na", "yapparina"]
    if any(k in clean_jp for k in ["やっぱり", "やはり", "やっぱ", "やっぱな"]) or any(k in rom_lower for k in yappari_keys):
        if any(w in pl_lower for w in ["po wszystkim", "zgodnie z oczekiwaniami", "jak oczekiwano"]):
            return "W audio pada 'Yappari / Yahari' (potwierdzenie domysłów) -> Zamień kalkę na naturalne: 'Wiedziałem!' / 'Jednak miałem rację!' / 'A jednak!' / 'Tak jak myślałem.' (Filar XLIII)."

    # 20. Desho? / Daro? (seeking validation / 'Told you so!') vs archaic 'Czyż nie?'
    desho_keys = ["desho", "deshou", "desho?", "daro", "darou", "daro?"]
    if clean_jp in ["でしょ", "でしょう", "でしょ？", "だろ", "だろう", "だろ？"] or rom_lower in desho_keys:
        if "czyż nie" in pl_lower:
            return "W audio pada potoczne 'Desho? / Daro?' -> Zamień archaiczne 'Czyż nie?' na naturalne: 'A nie mówiłem?' / 'No widzisz?' / 'No nie?' / 'Prawda?' (Filar XLIII)."

    # 21. Nani kore? (shock at bizarre situation/object) vs literal 'Co to za rzecz?'
    nanikore_keys = ["nani kore", "nanikore", "nanda kore", "nandakore"]
    if any(k in clean_jp for k in ["何これ", "なにこれ", "なんだこれ", "何だこれ"]) or any(k in rom_lower for k in nanikore_keys):
        if "co to za rzecz" in pl_lower or "czym jest ta rzecz" in pl_lower:
            return "W audio pada 'Nani kore?' (zdumienie sytuacją/obiektem) -> Zastąp sztywne 'Co to za rzecz?' naturalnym: 'Co to ma być?' / 'A to co znowu?' (Filar XLIII)."

    # 22. Hybrydy honoryfikatywne (Pani Sensei / Panie Senpai / Panie Taichou)
    hybrid_patterns = ["pani sensei", "panie sensei", "pan sensei", "pani senpai", "panie senpai", "pan senpai", "panie taichou", "panie shishou", "panie buchou"]
    if any(h in pl_lower for h in hybrid_patterns):
        return "Wykryto hybrydę honoryfikatywną ('Pani Sensei' / 'Panie Senpai') -> Zastąp czystym 'Sensei' / 'Senpai' lub naturalnym polskim tytułem 'Mistrzu' / 'Pani [Nazwisko]' (Filar XLVIII)."

    # 23. Kakegoe (Yotto, Yoisho, Dokkoisho, Yoi kora) vs polite 'Proszę'
    kakegoe_keys = ["yotto", "yoisho", "dokkoisho", "yoi kora", "yoikora", "eisa"]
    if any(k in rom_lower for k in kakegoe_keys) or any(k in clean_jp for k in ["よっと", "よいしょ", "どっこいしょ", "よいこら", "えいさ"]):
        if any(w in pl_lower for w in ["proszę", "oto jest", "oto masz", "oto proszę"]):
            return "W audio pada 'Yotto/Yoisho' (Kakegoe - odgłos wysiłku fizycznego/kinezjatyki) -> Zastąp zwrot grzecznościowy naturalnym odgłosem: 'Hop...', 'I siup...', 'Raz, dwa...' lub elipsą (Filar XVIII)."

    # 24. Chigaimasu / Chigau (Deictic negation vs 'Nie o niego' / 'Różni się')
    chigau_keys = ["chigaimasu", "chigau", "chigau yo", "chigau wa", "chigee", "chigee yo", "chiga-"]
    if any(k in clean_jp for k in ["違います", "ちがいます", "違う", "ちがう", "ちげえ", "ちげえよ"]) or any(k in rom_lower for k in chigau_keys):
        if any(w in pl_lower for w in ["nie o niego", "nie o nią", "nie o to", "różni się", "to inne"]):
            if "him" in en_text.lower() or "he" in en_text.lower():
                return "W audio pada 'Chigaimasu / Chigau' (zaprzeczenie tożsamości osoby: 'Not him') -> Zastąp naturalnym: 'To nie on!' lub 'To pomyłka!' (Filar CXXXVII)."
            elif "her" in en_text.lower() or "she" in en_text.lower():
                return "W audio pada 'Chigaimasu / Chigau' (zaprzeczenie tożsamości: 'Not her') -> Zastąp: 'To nie ona!' lub 'To pomyłka!' (Filar CXXXVII)."
            return "W audio pada 'Chigaimasu / Chigau' (sprostowanie sytuacji/nieporozumienia) -> Zastąp: 'To nie tak!' / 'To pomyłka!' / 'Wcale nie!' (Filar CXXXVII)."

    # 25. Douzo / Osaki ni douzo ('After you' / 'Be my guest' vs 'Po tobie' / 'Bądź moim gościem')
    douzo_keys = ["douzo", "osaki ni", "osakini", "dozo"]
    if any(k in clean_jp for k in ["どうぞ", "お先に", "お先にどうぞ"]) or any(k in rom_lower for k in douzo_keys):
        if "po tobie" in pl_lower:
            return "W audio pada 'Douzo / Osaki ni' (ustąpienie pierwszeństwa: 'After you') -> Zastąp: 'Proszę przodem!' lub 'Pani/Pan ma pierwszeństwo' (Filar CXXXVII)."
        if "bądź moim gościem" in pl_lower:
            return "W audio pada 'Douzo' (zachęta: 'Be my guest') -> Zastąp: 'Bardzo proszę!' / 'Śmiało!' / 'Częstuj się!' (Filar CXXXVII)."

    # 26. Hontou da yo na / Wakaru ('Tell me about it' vs 'Powiedz mi o tym')
    if any(k in rom_lower for k in ["tell me", "hontou da", "wakaru", "hontou ni"]) or any(k in clean_jp for k in ["本当だな", "ほんとうだな", "わかる"]):
        if "powiedz mi o tym" in pl_lower:
            return "Wykryto kalkę angielskiego idiomu 'Tell me about it!' -> Zamień błędne 'Powiedz mi o tym' na naturalną polską zgodę: 'Nawet mi nie mów!' / 'Wiem coś o tym!' / 'Święta prawda!' (Filar CXXXVII)."

    # 27. Omae ga iu na ('Look who's talking' vs 'Spójrz, kto mówi')
    if any(k in clean_jp for k in ["お前が言うな", "あんたが言うな", "お前もな", "omae ga iu na"]) or "omae ga iu" in rom_lower:
        if "spójrz kto mówi" in pl_lower or "spójrz, kto mówi" in pl_lower or "patrz kto mówi" in pl_lower:
            return "W audio pada 'Omae ga iu na!' (wytknięcie hipokryzji: 'Look who's talking') -> Zastąp kalkę żywym: 'Kto to mówi!' / 'Odezwał się!' / 'Sam nie jesteś lepszy!' (Filar CXXXVII)."

    # 28. Makasete / Ryoukai ('On it!' vs 'Na tym!')
    if any(k in clean_jp for k in ["任せて", "まかせて", "了解", "りょうかい"]) or any(k in rom_lower for k in ["makasete", "ryoukai", "ryokai"]):
        if pl_lower.strip() in ["na tym!", "na tym.", "na tym"]:
            return "W audio pada 'Makasete / Ryoukai' ('On it!') -> Zastąp: 'Już się robi!' / 'Zajmę się tym!' / 'Zrozumiałem!' (Filar CXXXVII)."

    # 29. Mochiron / Atarimae ('You bet!' vs 'Zakładasz się!')
    if any(k in clean_jp for k in ["もちろん", "当たり前", "あたりまえ", "勿論"]) or any(k in rom_lower for k in ["mochiron", "atarimae"]):
        if any(w in pl_lower for w in ["zakładasz się", "zakład!", "zakładaj się"]):
            return "W audio pada 'Mochiron / Atarimae' ('You bet!') -> Zastąp kalkę: 'Pewnie!' / 'I to jak!' / 'Jasna sprawa!' (Filar CXXXVII)."

    # 30. Yokatta na ('Good for you!' vs 'Dobre dla ciebie!')
    if any(k in clean_jp for k in ["よかったな", "よかったね", "良かったな", "良かったね"]) or any(k in rom_lower for k in ["yokatta na", "yokatta ne", "yokattana"]):
        if "dobre dla ciebie" in pl_lower:
            return "W audio pada 'Yokatta na' (radość/gratulacje: 'Good for you!') -> Zastąp kalkę: 'To świetnie!' / 'Cieszę się!' / 'Brawo ty!' (Filar CXXXVII)."

    # 31. Daijoubu / Ii desu ('I'm good / I'm fine' vs 'Jestem dobry!')
    if any(k in clean_jp for k in ["大丈夫", "だいじょうぶ", "いいです", "結構です"]) or any(k in rom_lower for k in ["daijoubu", "ii desu", "kekkou desu"]):
        if "jestem dobry" in pl_lower:
            return "W audio pada 'Daijoubu / Ii desu' ('I'm good') -> Zastąp kalkę: 'Dziękuję, postoję' / 'Nie trzeba' / 'Wszystko gra' (Filar CXXXVII)."

    # 32. Betsu ni ('Not really' vs 'Nieszczególnie' / 'Oddzielnie')
    if any(k in clean_jp for k in ["別に", "べつに"]) or "betsu ni" in rom_lower or "betsuni" in rom_lower:
        if any(w in pl_lower for w in ["nieszczególnie", "oddzielnie", "specjalnie nie"]):
            return "W audio pada 'Betsu ni...' (zawoalowana obojętność/zbycie) -> Zastąp sztuczne 'Nieszczególnie' żywym: 'Nic takiego...' / 'Nieważne...' / 'Nie, nic...' (Filar CXXXVII)."

    # 33. Ii kara / Mou ii (impatience / brush-off vs literal 'Bo dobrze' / 'To już jest dobre')
    if any(k in clean_jp for k in ["いいから", "もういい"]) or any(k in rom_lower for k in ["ii kara", "iikara", "mou ii", "mouii"]):
        if "bo dobrze" in pl_lower or "to już jest dobre" in pl_lower or "ponieważ dobrze" in pl_lower:
            return "W audio pada 'Ii kara! / Mou ii!' (zniecierpliwienie/zbycie tematu) -> Zastąp kalkę: 'Mniejsza o to!' / 'Po prostu to zrób!' / 'Daj spokój!' / 'Mam dość!' (Filar CXXXVII)."

    # 34. Chikushou / Kuso / Yabai / Shimatta (Radar Audio: silny wykrzyknik kryzysowy)
    if any(k in clean_jp for k in ["ちくしょう", "畜生", "くそ", "糞", "やばい", "ヤバい", "しまった"]) or any(k in rom_lower for k in ["chikushou", "chikusho", "kuso", "yabai", "shimatta"]):
        if any(w in pl_lower for w in ["ojej", "o nie", "ups", "rany", "kurczę"]):
            return "W audio pada silny wykrzyknik kryzysowy (Chikushō/Kuso/Yabai) -> Wzmocnij polski ładunek emocjonalny (Filar CXLIV: 'Szlag by to!', 'Niech to szlag!', 'Do diabła!')."

    # 35. Matte / Chotto matte (rozkaz zatrzymania)
    if any(k in clean_jp for k in ["待って", "まって", "ちょっと待って"]) or any(k in rom_lower for k in ["matte", "chotto matte"]):
        if "poczekaj minutę" in pl_lower or "chwilę czasu" in pl_lower:
            return "W audio pada 'Matte / Chotto matte' -> Użyj naturalnego: 'Czekaj!' / 'Stój!' / 'Chwila!' (Filar CXLI)."

    # 36. Yamero / Yamenai ka (żądanie zaprzestania przemocy/działania)
    if any(k in clean_jp for k in ["やめろ", "辞めろ", "やめないか", "止めて", "やめて"]) or any(k in rom_lower for k in ["yamero", "yamete", "yamenaika"]):
        if any(w in pl_lower for w in ["nie rób tego", "przestań to robić"]):
            return "W audio pada 'Yamero / Yamete' -> 'Przestań!' / 'Zostaw to!' / 'Stój!' / 'Dosyć!' (Filar CXLIV)."

    # 37. Shinde iru (stan rezultatywny vs trwające umieranie)
    if any(k in clean_jp for k in ["死んでいる", "死んでる"]) or any(k in rom_lower for k in ["shinde iru", "shinderu"]):
        if "umiera" in pl_lower:
            return "W audio pada 'Shinde iru' (stan dokonany) -> Użyj formy dokonanej: 'Nie żyje!' / 'Jest martwy!' / 'Zginął!' (Filar CXLI)."

    # 38. Tabun / Osoraku (domysł vs kategoryczne 'na pewno' / 'na pewno nie')
    if any(k in clean_jp for k in ["たぶん", "多分", "恐らく", "おそら"]) or any(k in rom_lower for k in ["tabun", "osoraku"]):
        if any(w in pl_lower for w in ["na pewno", "z całą pewnością", "bezwzględnie", "wykluczone"]):
            return "W audio seiyuu mówi 'Tabun / Osoraku' (niepewność/domysł: 'Chyba / Może / Raczej') -> Wyraź domysł: 'Chyba...' / 'Pewnie...' / 'Raczej...' (Filar CXLVII)."

    # 39. Yappari / Yahari ('After all' vs 'Wiedziałem! / A jednak!')
    if any(k in clean_jp for k in ["やっぱり", "やはり", "矢張り"]) or any(k in rom_lower for k in ["yappari", "yahari"]):
        if any(w in pl_lower for w in ["po wszystkim", "mimo wszystko"]):
            return "W audio seiyuu mówi 'Yappari / Yahari' (potwierdzenie przypuszczenia) -> Zastąp: 'Wiedziałem!' / 'A jednak!' / 'Tak jak myślałem...' (Filar CXLVII)."

    # 40. Sasuga / Sasuga ni ('As expected' vs 'Jak przystało / Bez przesady')
    if any(k in clean_jp for k in ["さすが", "流石"]) or any(k in rom_lower for k in ["sasuga", "sasugani", "sasuga ni"]):
        if any(w in pl_lower for w in ["zgodnie z oczekiwaniami", "jak oczekiwano"]):
            return "W audio seiyuu mówi 'Sasuga / Sasuga ni' -> Zastąp: 'Jak przystało na mistrza!' / 'Nawet jak na niego to przesada!' / 'Bez przesady...' (Filar CXLVII)."

    # 41. Douse ('Anyway' vs fatalistyczne 'I tak...')
    if any(k in clean_jp for k in ["どうせ", "何れ"]) or "douse" in rom_lower or "dōse" in rom_lower:
        if "w każdym razie" in pl_lower or "tak czy inaczej" in pl_lower:
            return "W audio seiyuu mówi 'Douse' (fatalizm i rezygnacja) -> Zastąp płytkie 'W każdym razie' autentycznym ładunkiem: 'I tak nic z tego...' / 'Przecież i tak...' / 'Bez różnicy...' (Filar CXLVII)."

    # 42. Masaka (szok / niedowierzanie vs kategoryczne wykluczenie)
    if any(k in clean_jp for k in ["まさか"]) or "masaka" in rom_lower:
        if any(w in pl_lower for w in ["żadna droga", "w żaden sposób", "żadnym sposobem"]):
            return "W audio seiyuu mówi 'Masaka' (szok i niedowierzanie) -> Zastąp kalkę: 'Niemożliwe!' / 'Nie mów, że...!' / 'Chyba kpisz!' / 'To nie może być prawda!' (Filar CXLVII)."

    # 43. Shikata ga nai / Shouganai ('It can't be helped' vs 'Trudno / Nic nie poradzimy')
    if any(k in clean_jp for k in ["仕方がない", "しょうがない", "仕様がない", "仕方がねえ"]) or any(k in rom_lower for k in ["shikata ga nai", "shouganai", "shikatanai", "shou ga nai"]):
        if any(w in pl_lower for w in ["nie da się pomóc", "nie można pomóc", "nie da się temu zaradzić"]):
            return "W audio seiyuu mówi 'Shikata ga nai / Shouganai' (pogodzenie z losem) -> Zastąp kalkę z angielskiego: 'Trudno...' / 'Nic na to nie poradzimy...' / 'Nie ma rady...' / 'Siła wyższa...' (Filar CXLVII)."

    # 44. Zettai ni / Kanarazu (kategoryczna obietnica/pewność)
    if any(k in clean_jp for k in ["絶対に", "絶対", "必ず"]) or any(k in rom_lower for k in ["zettai", "kanarazu"]):
        if any(w in pl_lower for w in ["może ", "chyba ", "prawdopodobnie "]):
            return "W audio seiyuu mówi 'Zettai ni / Kanarazu' (100% kategoryczna pewność/przysięga) -> Nie osłabiaj kwestii do 'może/chyba'! Użyj: 'Na pewno!' / 'Bezwzględnie!' / 'Za nic w świecie!' (Filar CXLVII)."

    # 45. Ottotto / Acchichi / Itta / Sammu (Somatyczne Odruchy Ciała i Kakegoe vs angielskie kalki)
    if any(k in clean_jp for k in ["おっとっと", "おっと", "オットット", "あっちっち", "熱っ", "さっむ", "痛っ"]) or any(k in rom_lower for k in ["ottotto", "ototo", "acchichi", "sammu", "itta"]):
        if any(w in pl_lower for w in ["oho, spokojnie", "oho, ostrożnie", "oho spokojnie", "spokojnie..."]):
            return "W audio seiyuu mówi 'Ottotto' (wykrzyknik utraty równowagi / potknięcia) -> Zastąp naturalnym odruchem: 'Ło, ło, ło...!', 'Uuu, powoli...!' lub usuń napis (Filar XVIII)."
        if "to jest gorące" in pl_lower or "to gorące" in pl_lower:
            return "W audio pada 'Acchichi / Atsu' (oparzenie termiczne) -> Zastąp szkolny opis odruchem bólu: 'Ała!' / 'Parzy!' / 'Cholera, gorące!' (Filar XVIII)."
        if "to jest zimne" in pl_lower or "to zimne" in pl_lower:
            return "W audio pada 'Sammu / Samui' (szok termiczny) -> Zastąp szkolny opis: 'Brrr!' / 'Ale mróz!' / 'Lodowata!' (Filar XVIII)."
        if "to boli" in pl_lower:
            return "W audio seiyuu mówi 'Itta / Ita' (nagły ból mechaniczny) -> Zastąp opis stanu odruchem: 'Ała!' / 'Auć!' / 'Niech to...!' (Filar XVIII)."

    # 46. Hontō na no ka / Tashika na no ka / Makoto ka (Weryfikacja Wieści i Wiarygodności vs urzędowe 'To prawda?')
    if any(k in clean_jp for k in ["本当なのか", "本当か", "本当ね", "確かなのか", "誠か", "実か"]) or any(k in rom_lower for k in ["honto nano ka", "hontou na no ka", "honto ka", "tashika na no ka", "makoto ka"]):
        if any(w in pl_lower for w in ["to prawda?", "czy to prawda?"]):
            return "W audio seiyuu mówi 'Hontō na no ka / Tashika na no ka' (żołnierski wstrząs / weryfikacja wieści) -> Zastąp żywym odruchem: 'To pewne?!' / 'Jesteś pewna?!' / 'Więc to prawda...?!' / 'Na pewno?!' / 'Prawdę mówisz?!' (Filar CXLVIII)."

    # 47. Haragei: Daijōbu & Chotto (Zawoalowane Odmowy vs pozorne zgody)
    if "大丈夫" in clean_jp or "daijoubu" in rom_lower or "daijobu" in rom_lower:
        if any(w in pl_lower for w in ["w porządku.", "w porządku!", "w porządku?"]):
            if any(w in en_text.lower() for w in ["help", "need", "want", "tea", "water", "okay", "fine", "alright", "careful"]):
                return "W audio seiyuu mówi 'Daijōbu' w odpowiedzi na ofertę/troskę (Haragei - zawoalowana odmowa) -> Wyraź odmowę: 'Nie trzeba, dziękuję' / 'Obejdzie się' / 'Dam radę' / 'Poradzę sobie' (Filar CXLIX)."
    if "ちょっと" in clean_jp or "chotto" in rom_lower:
        if any(w in pl_lower for w in ["trochę...", "to trochę...", "trochę."]) and not any(w in pl_lower for w in ["poczekaj", "chwil", "zaraz"]):
            return "W audio seiyuu mówi 'Chotto...' w tonie wahania/odmowy (Haragei) -> Zastąp autentyczną polską odmową: 'Raczej nie da rady...' / 'Obawiam się, że to niemożliwe...' / 'Z tym będzie kłopot...' (Filar CXLIX)."

    # 48. Hora! & Fuzja ze Słuchem i Prozodią (Popędzanie vs Złośliwy Triumf vs Rzut)
    if "ほら" in clean_jp or "hora" in rom_lower:
        is_shouting = any(w in prosody_lower for w in ["krzyk", "wzburzenie", "wzrost energii", "dbfs > -12"]) or en_text.endswith("!")
        is_sarcastic = any(w in prosody_lower for w in ["sarkazm", "dystans"]) or "miro" in rom_lower or "ne" in rom_lower or "見ろ" in clean_jp
        if any(w in pl_lower for w in ["spójrz", "patrz ", "popatrz", "zobacz"]):
            if is_sarcastic or "hora miro" in rom_lower or "見ろ" in clean_jp:
                return "W audio seiyuu mówi 'Hora miro / Hora ne' (złośliwy triumf) -> Zastąp triumfem: 'A nie mówiłem?!' / 'Widzisz?!' / 'Masz za swoje!' (Filar CL)."
            elif is_shouting or any(w in en_text.lower() for w in ["come on", "hurry", "quick", "faster", "get moving"]):
                return "W audio seiyuu krzyczy 'Hora!' (popędzanie / wysoka energia foniczna) -> Użyj: 'No dalej!' / 'Rusz się!' / 'Śmiało!' / 'Szybciej!' (Filar CL)."
            elif any(w in en_text.lower() for w in ["take this", "here", "catch"]):
                return "W audio pada 'Hora!' przy podaniu/rzucie przedmiotu -> Użyj: 'Masz!' / 'Łap!' / 'Trzymaj!' (Filar CL)."

    # 49. Rytualne Formuły Sytuacyjne Aisatsu (Ittekimasu, Tadaima, Ojama shimasu)
    if any(k in clean_jp for k in ["行ってきます", "行ってらっしゃい", "お邪魔します", "ただいま", "おかえり"]) or any(k in rom_lower for k in ["ittekimasu", "itterasshai", "ojama shimasu", "tadaima", "okaeri"]):
        if any(w in pl_lower for w in ["pójdę i wrócę", "idź i wróć", "będę przeszkadzał", "przeszkadzam", "wróciłem do domu", "witaj w domu"]):
            return "W audio seiyuu używa rytualnej formuły powitania/wyjścia (Aisatsu) -> Zastąp szkolną kalkę naturalną polszczyzną: 'Wychodzę!' / 'Trzymaj się!' / 'Dzień dobry!' / 'Przepraszam za najście' / 'Wróciłem!' (Filar CLI)."

    # 50. Abunai! & Tasukete! (Okrzyki Bojowe i Bezpośrednie Zagrożenie Życia)
    if any(k in clean_jp for k in ["危ない", "危ねえ", "危ねっ"]) or any(k in rom_lower for k in ["abunai", "abune", "abunee"]):
        if any(w in pl_lower for w in ["niebezpiecznie", "to jest niebezpieczne", "niebezpieczeństwo"]):
            return "W audio seiyuu krzyczy 'Abunai!' (śmiertelne zagrożenie / okrzyk bojowy) -> Zastąp natychmiastowym rozkazem taktycznym: 'Padnij!' / 'Kryj się!' / 'Uważaj!' / 'Z drogi!' (Filar CLII)."
    if "助けて" in clean_jp or "tasukete" in rom_lower:
        if any(w in pl_lower for w in ["ocal mnie", "uratuj mnie"]):
            return "W audio seiyuu woła 'Tasukete!' w zagrożeniu życia -> Użyj dynamicznego: 'Ratunku!' / 'Pomocy!' / 'Niech ktoś pomoże!' (Filar CLII)."

    # 51. Yare yare & Mendokusai & Shouganai (Westchnienia Znużenia i Ciężaru - Filar CLIII)
    yare_keys = ["yare yare", "yareyare", "yare-yare", "yare yare daze", "yareyaredaze"]
    if any(k in clean_jp for k in ["やれやれ", "やれやれだぜ"]) or any(k in rom_lower for k in yare_keys):
        if any(w in pl_lower for w in ["dobre nieszczęście", "dobra żałość", "daj mi przerwę", "no cóż, no cóż", "o drogi", "dobre niebiosa"]):
            return "W audio seiyuu wzdycha 'Yare yare' -> Zastąp kalkę angielską naturalną polszczyzną: 'Ja nie mogę...' / 'Litości...' / 'Ręce opadają...' / 'Uff...' (Filar CLIII)."

    if any(k in clean_jp for k in ["めんどくさい", "面倒"]) or any(k in rom_lower for k in ["mendokusai", "mendou", "mendou da"]):
        if any(w in pl_lower for w in ["co za ból", "jaki ból", "to jest ból", "jest uciążliwe"]):
            return "W audio seiyuu mówi 'Mendokusai' -> Użyj naturalnego zniechęcenia: 'Ale mi się nie chce...' / 'Co za męczarnia...' / 'Dajcie mi spokój...' (Filar CLIII)."

    if any(k in clean_jp for k in ["しょうがない", "仕方がない", "しょうがねえ"]) or any(k in rom_lower for k in ["shou ga nai", "shouganai", "shikata ga nai", "shouganee"]):
        if any(w in pl_lower for w in ["nie można temu pomóc", "nie da się temu pomóc", "tak po prostu jest"]):
            return "W audio seiyuu mówi 'Shou ga nai' -> Zastąp kalkę 'Nie można temu pomóc' naturalnym: 'Trudno...' / 'Nic na to nie poradzimy' / 'Nie mamy wyboru' (Filar CLIII)."

    # 52. Oi oi & Maa maa & Nante kotta & Iikagen ni shiro (Szok, Pacyfikowanie i Furia - Filar CLIII)
    if any(k in clean_jp for k in ["おいおい", "おいおいおい"]) or any(k in rom_lower for k in ["oi oi", "oioi"]):
        if any(w in pl_lower for w in ["hej hej", "hej, hej"]):
            return "W audio seiyuu reaguje 'Oi, oi...' na absurd rozmówcy -> Zamień wołające 'Hej, hej!' na mitygujące: 'Ej, zaraz, zaraz...' / 'Ej, chwila...' / 'Ej, bez przesady!' (Filar CLIII)."

    if any(k in clean_jp for k in ["まあまあ"]) or any(k in rom_lower for k in ["maa maa", "maamaa"]):
        if any(w in pl_lower for w in ["cóż, cóż", "cóż cóż", "tak sobie"]):
            return "W audio seiyuu ucisza spór 'Maa, maa...' -> Zamień kalkę na pacyfikujące: 'Spokojnie, no już...' / 'Bez nerwów...' / 'Dajcie spokój...' (Filar CLIII)."

    if any(k in clean_jp for k in ["なんてこった", "なんて事だ"]) or any(k in rom_lower for k in ["nante kotta", "nante koto da"]):
        if any(w in pl_lower for w in ["co za rzecz", "co to za sprawa", "jaka to rzecz"]):
            return "W audio seiyuu mówi 'Nante kotta!' -> Zastąp kalkę naturalnym wykrzyknikiem pecha: 'Niech to szlag!' / 'Co za pech!' / 'Jasny gwint!' (Filar CLIII)."

    if any(k in clean_jp for k in ["いい加減にしろ", "いい加減にしなさい"]) or any(k in rom_lower for k in ["iikagen ni shiro", "iikagen"]):
        if any(w in pl_lower for w in ["zrób to z umiarem", "bądź umiarkowany", "umiarkowanie"]):
            return "W audio seiyuu krzyczy 'Iikagen ni shiro!' -> Zastąp absurdalną kalkę gniewnym: 'Przestań wreszcie!' / 'Miarka się przebrała!' / 'Dość tego!' (Filar CLIII)."

    # 53. Yokatta & Yatta! (Ulga i Triumf - Filar CLIII / CLVIII)
    if any(k in clean_jp for k in ["よかった", "良かった"]) or any(k in rom_lower for k in ["yokatta", "yokattane", "yokatta na"]):
        if pl_lower.strip() in ["to było dobre.", "to było dobre!", "było dobrze.", "było dobrze!"] or pl_lower.startswith("to było dobre"):
            return "W audio seiyuu wzdycha z ulgą 'Yokatta...' -> Użyj naturalnej ulgi: 'Całe szczęście...' / 'Kamień z serca...' / 'Uff, jak dobrze...' (Filar CLIII/CLVIII)."

    if any(k in clean_jp for k in ["やった", "やったー", "やったぜ", "やったぞ"]) or any(k in rom_lower for k in ["yatta", "yattaa", "yattaze", "yattazo"]):
        if pl_lower.strip() in ["zrobiłem to.", "zrobiłem to!", "zrobiłam to.", "zrobiłam to!"] and not any(w in en_text.lower() for w in ["i made it happen", "i manufactured"]):
            return "W audio seiyuu krzyczy z radości 'Yatta!' (sukces/zwycięstwo) -> Zastąp sztywne 'Zrobiłem to!' naturalnym: 'Udało się!' / 'Mamy to!' / 'Wyszło!' / 'Jest!' (Filar CLIII/CLVIII)."

    # 54. Logika Odpowiedzi na Przeczenia (Echo Agreement: Hai/Un vs Iie/Uun - Filar CLIV)
    is_neg_q = any(w in en_text.lower() for w in ["don't you", "aren't you", "didn't you", "can't you", "won't you", "haven't you", "isn't it"]) or any(k in clean_jp for k in ["ないの", "ないか", "ない？", "ないのか", "ないですか"]) or any(k in rom_lower for k in ["nai no", "nai ka", "nai desu ka"])
    if is_neg_q:
        if any(clean_jp.startswith(k) or clean_jp == k for k in ["はい", "うん", "ええ"]) or any(rom_lower.startswith(k) or rom_lower == k for k in ["hai", "un", "ee"]):
            if pl_lower.startswith("tak") or pl_lower.startswith("jasne") or pl_lower == "tak." or pl_lower == "tak!":
                return "W audio pada 'Hai/Un' jako potwierdzenie przeczenia (Echo Agreement) -> W języku polskim odpowiadamy na fakt: 'Nie' / 'Nie idę' / 'Zgadza się, nie wiem' (Filar CLIV)."

    # 55. Kansai-ben Jibun ('Ty') & Relacje Trzecioosobowe (Onii-chan / Onee-chan - Filar CLIV)
    is_kansai = any(k in clean_jp for k in ["ねん", "やろ", "へん", "せや", "あかん"]) or any(k in rom_lower for k in ["nen", "yaro", "hen", "seya", "akan", "honma"])
    if is_kansai and ("自分" in clean_jp or "jibun" in rom_lower):
        if any(w in pl_lower for w in ["ja ", "mnie ", "siebie ", "samemu", "sobie "]) and not any(w in pl_lower for w in ["ty ", "ciebie ", "tobie ", "cię "]):
            return "W audio w dialekcie Kansai pada 'Jibun' w odniesieniu do rozmówcy -> 'Jibun' w Kansai to 'TY'! Zamień 'ja/siebie' na 'ty/ciebie' ('Co ty wyprawiasz?!', Filar CLIV)."

    if any(k in clean_jp for k in ["お兄ちゃん", "お姉ちゃん"]) or any(k in rom_lower for k in ["onii-chan", "onee-chan", "oniichan", "oneechan"]):
        if any(w in pl_lower for w in ["starszy brat", "starsza siostra", "onii-chan", "onee-chan"]):
            return "W audio postać mówi o bracie/siostrze w 3. osobie -> Zastąp sztuczne 'Starszy brat / Onii-chan' naturalnym 'Mój brat' / 'Brat mi powiedział' (Filar CLIV)."

    # 56. Repetycje Myśli i Separacja od Dialogu Mówionego (Tomerarenai / I can't stop it - Filar CLV)
    if any(k in clean_jp for k in ["止められない", "無理だ", "駄目だ"]) or any(k in rom_lower for k in ["tomerarenai", "muri da", "dame da"]) or any(w in en_text.lower() for w in ["can't stop it", "cannot stop it", "can't hold it"]):
        if any(w in pl_lower for w in ["nie chcę, żebyś", "stracił fanki", "przeze mnie", "twoje fanki"]):
            return "W audio w myślach pada repetycja paniki 'Tomerarenai...' (Nie powstrzymam tego...) -> Oddziel myśli od dialogu diegetycznego: 'Nie powstrzymam tego...' (Filar CLV)."

    # 57. Hitori ni shite vs Hottoite (Prośba o Samotność vs Odepchnięcie Natręta - Filar CLVI)
    if any(k in clean_jp for k in ["一人にして", "独りにして", "ひとりにして", "一人で", "独りで"]) or any(k in rom_lower for k in ["hitori ni shite", "hitori de", "hitorinisite", "hitori"]):
        if any(w in pl_lower for w in ["daj mi spokój", "daj spokój", "odczep się", "spadaj", "odwal się"]):
            return "W audio pada 'Hitori ni shite' (一人にして = prośba o samotność w cierpieniu/płaczu, od kanji 一人 = sam). Zastąp opryskliwe 'Daj mi spokój' intymnym: 'Zostaw mnie samą/samego' lub 'Chcę być sam(a)' (Filar CLVI)."

    # 58. Betsuni vs Nandemonai (Chłodny Dystans / Foch vs Uspokajanie - Filar CLVI)
    if ("別に" in clean_jp or "betsuni" in rom_lower) and any(w in en_text.lower() for w in ["nothing", "it's nothing", "not really"]):
        if any(w in pl_lower for w in ["to nic takiego", "nie ma sprawy", "nic się nie stało"]):
            return "W audio pada 'Betsuni' (別に = chłód emocjonalny, foch, dystans). Zastąp uspokajające 'To nic takiego' trafnym: 'Wcale nie', 'Nieważne' lub 'Mniejsza z tym' (Filar CLVI)."

    # 59. Kolaps Formy Adresatywnej / Spurious 'Pan/Pani' przy 'You' na 'Ty' (Filar CLVII)
    if any(w in en_text.lower() for w in ["you won", "you did", "you saw", "you told", "you said", "you have", "you had", "you were", "you know", "did you", "have you", "why did you"]):
        if any(w in pl_lower for w in ["wygrał pan", "wygrała pani", "zrobił pan", "zrobiła pani", "widział pan", "widziała pani", "powiedział pan", "powiedziała pani", "pan wie", "pani wie", "wie pan", "wie pani", "pan widzi", "pani widzi", "pan myśli", "pani myśli", "pan mówi", "pani mówi"]):
            return "Wykryto kolaps formy adresatywnej (Pronominal Address Drift - Filar CLVII)! Angielskie 'you' w relacji nieformalnej/koleżeńskiej lub po imieniu przetłumaczono sztucznie per 'pan/pani'. Zamień 'wygrał pan' na 'wygrałeś', 'pan wie' na 'wiesz' itp.!"

    # 60. Zgodność Foniczno-Semantyczna Seiyū i Test Ucha Widza (Filar CLVIII)
    if any(k in clean_jp for k in ["一人にして", "独りにして", "ひとりにして"]) or "hitori ni shite" in rom_lower or "hitori" in rom_lower:
        if any(w in pl_lower for w in ["daj mi spokój", "daj spokój"]):
            return "W audio pada 'Hitori' (sam/sama). Zastąp opryskliwe 'Daj mi spokój' intymnym: 'Zostaw mnie samą/samego' (Filar CLVIII)."

    if any(k in clean_jp for k in ["助けて", "たすけて"]) or "tasukete" in rom_lower:
        if any(w in pl_lower for w in ["ocal mnie", "uratuj mnie"]):
            return "W audio pada 'Tasukete' (krzyk o pomoc). Zastąp teatralne 'Ocal mnie' naturalnym: 'Ratunku!' / 'Pomóż mi!' (Filar CLVIII)."

    if any(k in clean_jp for k in ["やめろ", "やめて"]) or "yamero" in rom_lower or "yamete" in rom_lower:
        if any(w in pl_lower for w in ["nie rób tego", "nie czyń"]):
            return "W audio pada 'Yamero/Yamete' (sprzeciw). Zastąp 'Nie rób tego' naturalnym: 'Przestań!' / 'Stój!' (Filar CLVIII)."

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
                    "[⚠️ ALARM DYSONANSU AFEKTYWNEGO / SARKAZMU]: W audio seiyū słychać chłód/ironię/dystans! "
                    "Zastosuj polską zjadliwość, ironię lub sarkazm: 'Też mi pomoc...', 'Akurat...', 'Wielkie mi dzięki...', 'Taa, jasne...', 'Jeszcze czego...']"
                )

    # 62. Echo Agreement Discrepancy (Iie / Uun vs 'Nie' na pytanie z przeczeniem)
    if any(k in clean_jp for k in ["いいえ", "ううん", "いや"]) or any(k in rom_lower.split() for k in ["iie", "uun", "iya"]):
        if any(w in en_text.lower() for w in ["don't you", "aren't you", "didn't you", "can't you", "won't you", "isn't it"]):
            if re.match(r"^\s*(nie|n-nie)[\.!\?…]*$", pl_lower.strip()):
                return "W audio pada 'Iie/Uun' w odpowiedzi na pytanie z przeczeniem (odrzucenie negacji: 'Wiem!' / 'Idę!' / 'Właśnie, że tak!') -> Zastosuj polskie zaprzeczenie przeczenia ('Wiem!' / 'Idę!' / 'Właśnie, że tak!') (Filar CLIV)."

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

    # 4. Mały Chłopiec / Shounen (Boku, Ore, Oira, Boku-chan, Niichan, Neechan)
    if any(k in clean_jp for k in ["ぼく", "ボク", "おいら", "ボクちゃん", "ぼくちゃん", "にいちゃん", "ねえちゃん"]) or any(k in rom_lower for k in ["boku ", "boku,", "boku-", "oira", "niichan", "neechan", "boku wa", "boku ga"]):
        return "Mały chłopiec / Shounen (mimo wysokiego głosu seiyū BEZWZGLĘDNIE rodzaj MĘSKI: -łem, -łem się, 'Zgubiłem się', 'Chciałem pomóc' - Filar CXXXVI)"

    # 5. Mała Dziewczynka / Shojo (Atashi, Uchi, Onii-chan, Onee-chan, -na no)
    if any(k in clean_jp for k in ["あたち", "あたし", "ウチ", "お兄ちゃん", "お姉ちゃん", "おにいちゃん", "おねえちゃん"]) or any(k in rom_lower for k in ["atashi", "atachi", "onii-chan", "onee-chan", "oniichan", "oneechan"]):
        return "Mała dziewczynka / Shojo (wysoki głos dziecięcy, rodzaj ŻEŃSKI: -łam, -łam się, 'Zgubiłam się', 'Chciałam pomóc' - Filar CXXXVI)"

    # 6. Youth / Casual Slang (-ssu, -yatsu, -chatt, -tteba)
    if any(k in clean_jp for k in ["っす", "やつ", "ちゃった", "ってば"]) or any(k in rom_lower for k in ["-ssu", " ssu", "yatsu", "chatta", "tteba"]):
        return "Młodzieżowy / Swobodny (luźny styl potoczny, dynamiczne skróty)"
        
    # 7. Romantic Intimate / Kokuhaku (daisuki, aishiteru, zutto issho)
    if any(k in clean_jp for k in ["大好き", "愛してる", "ずっと一緒"]) or any(k in rom_lower for k in ["daisuki", "aishiteru", "zutto issho"]):
        return "Czuły miłosny / Kokuhaku (wyznanie miłosne 'Kocham cię', eliminacja friendzone)"

    # 8. Satsuma-ben (Chesto, Gowasu, Oddon, Jaddo, Mosu)
    if any(k in clean_jp for k in ["チェスト", "ごわす", "でごわす", "おっどん", "じゃっど", "もす"]) or any(k in rom_lower for k in ["chesto", "gowasu", "oddon", "jaddo", "mosu"]):
        return "Dialekt Satsuma / Satsuma-ben (fonetyczne ściągnięcia, twarda artykulacja 'Cukszma', elizje apostrofowe 'Sierżan'', hermetyczny szyfr wojenny - Filar CXXXV)"

    # 9. Kansai-ben / Osaka & Kyoto (-nen, -yaro, honma, akan, seyana, -dosu, oideyasu)
    if any(k in clean_jp for k in ["ねん", "やろ", "ほんま", "あかん", "せやな", "どす", "おいでやす"]) or any(k in rom_lower for k in ["-nen", "honma", "akan", "seyana", "nande ya", "dosu", "oideyasu"]):
        return "Dialekt Kansai / Kansai-ben (zadziorna, błyskotliwa miejska polszczyzna z humorem / aksamitny styl salonowy Kioto - Filar CXXXV)"

    # 10. Tohoku-ben & Tsugaru-ben (-dabe, -daccha, ora, nda, -zura, nashite)
    if any(k in clean_jp for k in ["だべ", "だっちゃ", "おら", "ずら", "なして"]) or any(k in rom_lower for k in ["-dabe", "-daccha", "dappe", "zura", "nashite"]):
        return "Dialekt Tohoku / Tsugaru-ben (ciepła, gawędziarska mowa prowincjonalna 'dyć prawda', 'no przeca' - Filar CXXXV)"

    # 11. Hiroshima-ben & Yakuza (-jaken, -jakee, -noo, buchi, taigii)
    if any(k in clean_jp for k in ["じゃけん", "じゃけえ", "たいぎい", "ぶち"]) or any(k in rom_lower for k in ["jaken", "jakee", "taigii", "buchi"]):
        return "Dialekt Hiroshima / Półświatek Yakuzy (szorstki, bezkompromisowy slang gangsterski 'bo ci łeb urwę' - Filar CXXXV)"

    # 12. Hakata-ben & Kyūshū (-to?, -bai, -tai, suitoo, batten)
    if any(k in clean_jp for k in ["ばい", "たい", "好いとー", "ばってん"]) or any(k in rom_lower for k in ["-bai", "-tai", "suitoo", "batten"]):
        return "Dialekt Hakata / Kiusiu (śpiewna, bezpośrednia, urocza mowa południowa - Filar CXXXV)"

    # 13. Okinawa-ben & Uchinaaguchi (Haisai, Mensoore, Nankurunaisa, -saa)
    if any(k in clean_jp for k in ["はいさい", "はいたい", "めんそーれ", "なんくるないさ"]) or any(k in rom_lower for k in ["haisai", "haitai", "mensoore", "nankurunaisa"]):
        return "Dialekt Okinawa / Uchinaaguchi (słoneczny, zrelaksowany ton wyspiarski 'Spokojna głowa' - Filar CXXXV)"

    # 14. Hokkaido-ben (Namara, Shibareru, Shitakke)
    if any(k in clean_jp for k in ["なまら", "しばれる", "したっけ"]) or any(k in rom_lower for k in ["namara", "shibareru", "shitakke"]):
        return "Dialekt Hokkaido (surowa, lakoniczna mowa pionierów północy i traperów - Filar CXXXV)"
        
    return None

def get_audio_semantic_anchor(jp_text: str, en_text: str = "") -> Optional[str]:
    """
    SAGE (Seiyū Acoustic Grounding Engine).
    Analyzes Whisper Japanese transcription and English text to detect dangerous pivot ambiguities
    and auditory anchor discrepancies (e.g., 'leave me alone' -> Hitori ni shite vs Hottoite,
    'it's nothing' -> Betsuni vs Nandemonai, 'that was good' -> Yokatta, 'I did it' -> Yatta).
    Returns an explicit disambiguation anchor directive for the translation prompt (Filar CLVI / CLVIII).
    """
    if not jp_text:
        return None
    clean_jp = re.sub(r"\[.*?\]", "", jp_text).strip().lower()
    romaji_match = re.findall(r"\[(.*?)\]", jp_text)
    rom_lower = romaji_match[0].strip().lower() if romaji_match else to_romaji(clean_jp).lower()
    en_lower = (en_text or "").lower()

    # 1. Hitori ni shite vs Hottoite / Leave me alone (Filar CLVI / CLVIII)
    if any(k in clean_jp for k in ["一人にして", "独りにして", "ひとりにして", "一人で", "独りで"]) or any(k in rom_lower for k in ["hitori ni shite", "hitori de", "hitorinisite", "hitori"]):
        if any(w in en_lower for w in ["leave me alone", "alone", "by myself", "give me a break", "peace"]):
            return "W audio pada '一人にして (Hitori ni shite)' = samotność, bycie samemu w rozpaczy/bólu -> Tłumacz jako: 'Zostaw mnie samą/samego' / 'Chcę być sam(a)' (Filar CLVI/CLVIII)."

    # 2. Betsuni vs Nandemonai / It's nothing (Filar CLVI / CLVIII)
    if ("別に" in clean_jp or "betsuni" in rom_lower) and any(w in en_lower for w in ["nothing", "not really", "it's fine", "never mind"]):
        return "W audio pada '別に (Betsuni)' = chłód emocjonalny, foch, dystans -> Tłumacz jako: 'Wcale nie' / 'Nieważne' / 'Mniejsza z tym' (Filar CLVI/CLVIII)."

    # 3. Mou ii vs Kekkou desu / That's enough / It's fine (Filar CLVI / CLVIII)
    if ("もういい" in clean_jp or "mou ii" in rom_lower or "mouii" in rom_lower) and any(w in en_lower for w in ["enough", "it's fine", "forget it"]):
        return "W audio pada 'もういい (Mou ii)' = rezygnacja, urażona duma -> Tłumacz jako: 'Wystarczy' / 'Daj spokój' / 'Koniec tematu' (Filar CLVI/CLVIII)."

    # 4. Gaman dekinai vs Yurusenai / I can't take it (Filar CLVI / CLVIII)
    if any(k in clean_jp for k in ["我慢できない", "耐えられない"]) or any(k in rom_lower for k in ["gaman dekinai", "taerarenai"]):
        return "W audio pada 'Gaman dekinai' (ból fizyczny/psychiczny) -> Tłumacz jako: 'Dłużej tego nie zniosę / Nie wytrzymam' (Filar CLVI/CLVIII)."

    # 5. Yokatta (Filar CLVIII)
    if any(k in clean_jp for k in ["よかった", "良かった"]) or any(k in rom_lower for k in ["yokatta", "yokattane"]):
        if any(w in en_lower for w in ["good", "great", "glad", "relief", "thank goodness", "thank god"]):
            return "W audio pada 'よかった (Yokatta)' = ulga, kamień z serca -> Tłumacz jako: 'Całe szczęście...' / 'Jak dobrze...' (Filar CLVIII)."

    # 6. Yatta (Filar CLVIII)
    if any(k in clean_jp for k in ["やった", "やったー"]) or any(k in rom_lower for k in ["yatta", "yattaa"]):
        if any(w in en_lower for w in ["did it", "done it", "i did", "we did", "yes", "hooray"]):
            return "W audio pada 'やった (Yatta)' = triumf, radość z sukcesu -> Tłumacz jako: 'Udało się!' / 'Mamy to!' / 'Jest!' (Filar CLVIII)."

    # 7. Uso / Maji (Filar CLVIII)
    if any(k in clean_jp for k in ["嘘", "うそ", "マジ", "まじ"]) or any(k in rom_lower for k in ["uso", "maji"]):
        if any(w in en_lower for w in ["lie", "lying", "no way", "really", "kidding", "serious"]):
            return "W audio pada '嘘/マジ (Uso/Maji)' = szok i niedowierzanie -> Tłumacz jako: 'Nie wierzę!' / 'Żartujesz?!' / 'Bez jaj!' (Filar CLVIII)."

    # 8. Mendokusai (Filar CLVIII)
    if any(k in clean_jp for k in ["めんどくさい", "面倒くさい", "面倒"]) or any(k in rom_lower for k in ["mendokusai", "mendou"]):
        if any(w in en_lower for w in ["pain", "bother", "hassle", "trouble", "annoying", "drag"]):
            return "W audio pada '面倒くさい (Mendokusai)' = zniechęcenie, udręka -> Tłumacz jako: 'Ale mi się nie chce...' / 'Co za męczarnia...' (Filar CLVIII)."

    # 9. Tasukete (Filar CLVIII)
    if any(k in clean_jp for k in ["助けて", "たすけて"]) or any(k in rom_lower for k in ["tasukete", "tasukete kure"]):
        if any(w in en_lower for w in ["help", "save"]):
            return "W audio pada '助けて (Tasukete)' = krzyk o pomoc -> Tłumacz jako: 'Ratunku!' / 'Pomóż mi!' (Filar CLVIII)."

    # 10. Yamero / Yamete (Filar CLVIII)
    if any(k in clean_jp for k in ["やめろ", "やめて", "止めろ", "止めて"]) or any(k in rom_lower for k in ["yamero", "yamete"]):
        if any(w in en_lower for w in ["stop", "don't"]):
            return "W audio pada 'やめろ/やめて (Yamero/Yamete)' = sprzeciw/protest -> Tłumacz jako: 'Przestań!' / 'Stój!' / 'Zostaw!' (Filar CLVIII)."

    # 11. Shikata ga nai / Shou ga nai (Filar CLVIII)
    if any(k in clean_jp for k in ["しょうがない", "仕方がない", "仕方ない"]) or any(k in rom_lower for k in ["shou ga nai", "shikata ga nai", "shouganai", "shikatanai"]):
        if any(w in en_lower for w in ["help", "choice", "way"]):
            return "W audio pada 'しょうがない (Shou ga nai)' = pogodzenie się z losem -> Tłumacz jako: 'Trudno...' / 'Nic na to nie poradzimy' / 'Nie mamy wyboru' (Filar CLVIII)."

    # 12. Pronoun: omae / kimi / kisama / temee (Filar CLVII / CLVIII)
    if any(k in clean_jp for k in ["お前", "君", "貴様", "てめえ"]) or any(k in rom_lower.split() for k in ["omae", "kimi", "kisama", "temee"]):
        if any(w in en_lower for w in ["you", "your"]):
            return "W audio seiyū zaimek 2. osoby na 'ty' ('omae/kimi/kisama') -> Tłumacz bezpośrednio w 2. osobie na 'ty' (Filar CLVII/CLVIII)."

    # 13. Pronoun: ore / boku (Filar CXXXVI / CLVIII)
    if any(k in clean_jp for k in ["俺", "僕"]) or any(k in rom_lower.split() for k in ["ore", "boku"]):
        if any(w in en_lower for w in ["i ", "i'm", "i've", "my ", "me"]):
            return "W audio seiyū męski zaimek 1. osoby ('ore/boku') -> Mówca to mężczyzna/chłopak! Stosuj męskie formy przeszłe (-łem, -łem się) (Filar CXXXVI/CLVIII)."

    # 14. Pronoun: atashi / atai (Filar XIII / CLVIII)
    if any(k in clean_jp for k in ["あたし", "あtai", "あたい"]) or any(k in rom_lower.split() for k in ["atashi", "atai"]):
        if any(w in en_lower for w in ["i ", "i'm", "i've", "my ", "me"]):
            return "W audio seiyū damski zaimek 1. osoby ('atashi') -> Mówca to kobieta/dziewczyna! Stosuj żeńskie formy przeszłe (-łam, -łam się) (Filar XIII/CLVIII)."

    # 15. Pivot: Iku vs Coming (Filar CLXI / CLVIII)
    if any(k in clean_jp for k in ["行く", "いく", "行きます", "行こう", "いこう"]) or any(k in rom_lower.split() for k in ["iku", "ikimasu", "ikou"]):
        if any(w in en_lower for w in ["coming", "i'm coming", "on my way"]):
            return "W audio pada '行く (Iku)' = ruch OD mówcy -> Tłumacz zgodnie z kierunkiem ruchu: 'Idę!' / 'Już idę!' / 'Zaraz będę!' (zamiast sztucznego: 'Przychodzę') (Filar CLXI/CLVIII)."

    # 16. Pivot: Naruhodo vs Sou ka vs Wakatta / I see (Filar CLVIII)
    if any(k in clean_jp for k in ["なるほど", "成程"]) or "naruhodo" in rom_lower:
        if any(w in en_lower for w in ["i see", "makes sense", "understand"]):
            return "W audio pada 'なるほど (Naruhodo)' = zrozumienie toku myślenia -> Tłumacz jako: 'A więc tak...' / 'Rozumiem twój tok myślenia' / 'No proszę...' (Filar CLVIII)."
    elif any(k in clean_jp for k in ["そうか", "そっか"]) or any(k in rom_lower.split() for k in ["souka", "sokka", "sou ka"]):
        if any(w in en_lower for w in ["i see", "is that so"]):
            return "W audio pada 'そうか/そっか (Sou ka/Sokka)' = powściągliwe przyjęcie do wiadomości -> Tłumacz jako: 'Doprawdy?' / 'A więc tak...' / 'Tak sądzisz?' / 'Jasne...' (Filar CLVIII)."

    # 17. Pivot: Chigau / Chigaimasu (Filar CLVIII)
    if any(k in clean_jp for k in ["違う", "ちがう", "違います", "ちがいます"]) or any(k in rom_lower.split() for k in ["chigau", "chigaimasu", "chiga"]):
        if any(w in en_lower for w in ["no", "wrong", "not true", "not like that", "mistake"]):
            return "W audio pada '違う/違います (Chigau/Chigaimasu)' = gwałtowne zaprzeczenie pomyłce -> Tłumacz jako: 'Wcale nie!' / 'To pomyłka!' / 'Źle to rozumiesz!' / 'Wcale tak nie jest!' (Filar CLVIII)."

    # 18. Pivot: Ii desu / Kekkou desu (Filar CLVIII)
    if any(k in clean_jp for k in ["いいです", "結構です", "けっこうです"]) or any(k in rom_lower.split() for k in ["ii desu", "kekkou", "kekkou desu"]):
        if any(w in en_lower for w in ["fine", "good", "okay", "no thanks"]):
            return "W audio seiyū odrzuca ofertę ('結構です/いいです') -> Zastosuj formę uprzejmej odmowy: 'Nie trzeba' / 'Obejdzie się' / 'Dziękuję, nie trzeba' (Filar CLVIII)."

    # 19. Urusai / Damare (Filar CLXX - Speech Act Class 1: Uciszanie i Irytacja)
    if any(k in clean_jp for k in ["うるさい", "うるせえ", "うるせー", "だまれ", "黙れ", "静かに"]) or any(k in rom_lower.split() for k in ["urusai", "urusaina", "urusee", "uruse-", "ussee", "damare", "shizukani"]):
        return "W audio pada 'うるさい / 黙れ (Urusai / Damare)' = poirytowanie gadaniem/zrzędzeniem rozmówcy (zamiast obcego 'Ale żenada...') -> Tłumacz jako: 'Ale marudzisz...', 'Daj mi spokój...', 'Nie truj...', 'Ale gadasz...', 'Ucisz się...' lub 'Przestań wreszcie...' (Filar CLXX)."

    # 20. Tadaima / Okaeri (Filar CLXX - Harmonizacja Aisatsu)
    if any(k in clean_jp for k in ["ただいま", "おかえり", "お帰り"]) or any(k in rom_lower.split() for k in ["tadaima", "okaeri"]):
        return "W audio pada formuła domowa 'Tadaima / Okaeri' -> Unikaj twierdzącego echa czasownikowego ('Wróciłam' -> 'Wróciłaś')! Zastosuj naturalne polskie powitanie domowników: 'Witaj w domu!', 'O, już jesteś?' lub 'Dobrze, że jesteś!' (Filar CLXX)."

    # 21. Shiranai yo / Shiranai (Filar CLVI / SAGE Intent Anchor)
    if any(k in clean_jp for k in ["知らないよ", "しらないよ", "知らねえよ", "知らん"]) or any(k in rom_lower.split() for k in ["shiranaiyo", "shiranai yo", "shiraneeyo", "shiran"]):
        if any(w in en_lower for w in ["care", "warn", "see if i care", "don't blame me", "suit yourself", "don't know", "i don't care"]):
            return "W audio seiyū mówi '知らないよ (Shiranai yo)' w tonie ostrzeżenia/irytacji -> Tłumacz jako ostrzeżenie: 'Ostrzegałem cię!' / 'Jeszcze pożałujesz!' / 'Nie moja wina!' / 'Rób jak chcesz!' (Filar CLVI)."

    # 22. Katte ni shiro / Katte ni (Filar CLVI / SAGE Intent Anchor)
    if any(k in clean_jp for k in ["勝手にしろ", "かってにしろ", "勝手にしなさい", "勝手に"]) or any(k in rom_lower.split() for k in ["katte ni shiro", "kattenishiro", "katte"]):
        if any(w in en_lower for w in ["whatever", "suit yourself", "as you like", "want", "please"]):
            return "W audio pada '勝手にしろ (Katte ni shiro)' = wzgardliwe zerwanie sporu -> Tłumacz jako: 'Rób, co chcesz!' / 'A rób se, co chcesz!' / 'Na własne ryzyko!' (Filar CLVI)."

    # 23. Itadakimasu (Filar CLVI / SAGE Intent Anchor)
    if any(k in clean_jp for k in ["いただきます", "頂きます"]) or "itadakimasu" in rom_lower:
        if any(w in en_lower for w in ["feast", "dinner", "eat", "food", "devour", "dig in"]):
            return "W audio pada 'いただきます (Itadakimasu)' w kontekście drapieżnika/walki -> Tłumacz jako okrzyk drapieżnika: 'Czas na żer!' / 'Pora na posiłek!' / 'Zaraz cię pożrę!' (Filar CLVI)."

    # 24. Echo Agreement - Hai / Iie on Negative Questions (Filar CLIV / CLVIII)
    if any(k in clean_jp for k in ["いいえ", "ううん", "いや"]) or any(k in rom_lower.split() for k in ["iie", "uun", "iya"]):
        if any(w in en_lower for w in ["no", "nope"]):
            return "W audio pada zaprzeczenie 'いいえ/ううん/いや (Iie/Uun/Iya)'. Jeśli poprzednie zdanie było pytaniem z przeczeniem (np. 'Nie idziesz?', 'Nie wiesz?'), mówca ZAPRZECZA negacji (twierdząc: 'Wiem!' / 'Idę!' / 'Właśnie, że tak!') -> Zastosuj polskie zaprzeczenie przeczenia: 'Wiem!' / 'Idę!' / 'Właśnie, że tak!' (Filar CLIV)."
    elif any(k in clean_jp for k in ["はい", "うん", "ええ"]) or any(k in rom_lower.split() for k in ["hai", "un", "ee"]):
        if any(w in en_lower for w in ["yes", "yeah", "right"]):
            return "W audio pada potwierdzenie 'はい/うん/ええ (Hai/Un/Ee)'. Jeśli poprzednie zdanie było pytaniem z przeczeniem (np. 'Nie idziesz?', 'Nie wiesz?'), w języku polskim oznacza to POTWIERDZENIE NEGACJI: 'Nie.' / 'Nie idę.' / 'Nie wiem.' (Filar CLIV)."

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
    name: str = Field(description="Imię lub określenie postaci (np. 'Arata', 'Minami', 'Nauczyciel')")
    gender: str = Field(description="Płeć postaci: 'mężczyzna', 'kobieta' lub 'inna'")
    role: Optional[str] = Field(default=None, description="Krótka rola lub relacja, np. 'główny bohater', 'koleżanka z klasy'")

class LineTranslation(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: int = Field(description="ID kwestii dialogowej z wejścia")
    polish_text: str = Field(description="Przetłumaczona kwestia na język polski z uwzględnieniem płci, sceny i eliminacji kalek")
    speaker_name: Optional[str] = Field(default=None, description="Imię postaci z bazy AniList / kartoteki mówiącej tę kwestię (np. 'Kenji', 'Yui') lub null jeśli nieznana")
    speaker_gender: Optional[str] = Field(default=None, description="Płeć mówcy: 'mężczyzna' lub 'kobieta'")
    addressee: Optional[str] = Field(
        default=None,
        description=(
            "Odbiorca kwestii na kadrze/w scenie: "
            "'kobieta' (pojedyncza), 'mężczyzna' (pojedynczy), "
            "'grupa_kobiet' (grupa samych kobiet/dziewcząt - wymóg form: zrobiłyście/byłyście), "
            "'grupa_mężczyzn' (grupa samych mężczyzn - wymóg form: zrobiliście/byliście), "
            "'grupa_mieszana' (mężczyźni i kobiety / tłum - wymóg form: zrobiliście/byliście) "
            "lub 'brak' (myśl/monolog)"
        )
    )
    semiotic_layer: Optional[str] = Field(default="spoken_on_screen", description="Warstwa semiotyczna: 'spoken_on_screen' (mowa w kadrze), 'spoken_off_screen' (komentarz zza kadru), 'manga_balloon' (dymek/halucynacja), 'inner_thought' (myśli), 'diegetic_sign' (plansza/napis)")
    screen_region: Optional[str] = Field(default=None, description="Dla planszy/tytułu/napisu ekranowego: wskaż wykryte na kadrze położenie japońskiego napisu: 'bottom_right' (prawy dolny róg), 'bottom_left' (lewy dolny róg), 'top_right' (prawy górny róg), 'top_left' (lewy górny róg), 'bottom_center' (dół), 'top_center' (góra), 'center' (środek) lub null dla zwykłych dialogów.")
    visual_typesetting: Optional[VisualTypesettingData] = Field(default=None, description="Dla planszy/tytułu/napisu ekranowego/onomatopei: precyzyjne współrzędne 2D [ymin, xmin, ymax, xmax] w skali 0-1000, umiejscowienie 'above'/'below', kąt obrotu rotation_deg (-45 do 45) oraz kolory HEX lub null dla zwykłej mowy.")
    visual_subtext: Optional[str] = Field(default=None, description="Maks. 10-12 słów w formacie 'Stan: Emocja + Akcja fizyczna'. Podawaj TYLKO gdy mimika/gest przeczy słowom lub wnosi ukryty podtekst niewidoczny w tekście (asymetria obrazu i tekstu), w przeciwnym razie null.")
    literal_meaning: Optional[str] = Field(default=None, description="Dosłowny idiom JP (maks. 5 słów) tylko w razie potrzeby, inaczej null")
    notes: Optional[str] = Field(default=None, description="Kluczowa notatka (maks. 5 słów) tylko w razie potrzeby, inaczej null")
    ambiguity_note: Optional[str] = Field(default=None, description="W razie wątpliwości (np. niejasny zaimek it/he, dwuznaczność słowa, brak pewności): krótka flaga dla Fazy 2 (maks. 6 słów), inaczej null")

class BatchTranslationResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    scene_diagnosis: Optional[SceneDiagnosis] = Field(default=None, description="Syntetyczna diagnoza sytuacji i podtekstu sceny PRZED tłumaczeniem (1-2 zwięzłe zdania)")
    translations: List[LineTranslation] = Field(description="Lista przetłumaczonych kwestii")
    characters_identified: Optional[List[CharacterInfo]] = Field(default=None, description="Zidentyfikowane lub nowo odkryte postacie i ich płeć")

CANONICAL_MALE_NAMES_ON_A = {
    "shira", "akira", "gaara", "ashitaka", "kiba", "soma", "kenta",
    "ryoma", "hanza", "koba", "soya", "toma", "genga", "sinbad", "judar", "alibaba"
}

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
        for full_name, details in character_registry.items():
            if not full_name:
                continue
            desc_lower = str(details).lower()
            gen = None
            if any(k in desc_lower for k in FEMALE_ROLE_KEYWORDS):
                gen = "FEMALE"
            elif any(k in desc_lower for k in MALE_ROLE_KEYWORDS):
                gen = "MALE"
            
            # Split multi-name slashes like "Fatima / Sitara"
            parts = [p.strip() for p in re.split(r"[/,]", full_name) if p.strip()]
            for p in parts:
                if len(p) >= 3 and gen:
                    candidates[p] = gen

    # 2. From Series Bible characters
    if series_bible and hasattr(series_bible, "data"):
        bible_chars = series_bible.data.get("characters", {})
        for c_key, c_val in bible_chars.items():
            desc_str = c_val.get("description", "") if isinstance(c_val, dict) else str(c_val)
            desc_lower = desc_str.lower()
            gen = None
            if any(k in desc_lower for k in FEMALE_ROLE_KEYWORDS):
                gen = "FEMALE"
            elif any(k in desc_lower for k in MALE_ROLE_KEYWORDS):
                gen = "MALE"
            
            # c_key might be "Sitara -> Shira" or "Shira"
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

        # Match name as a whole word in English text (or possessive e.g. Shira's)
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
        all_known_chars.update(character_registry)
    if series_bible and hasattr(series_bible, "data") and "characters" in series_bible.data:
        for k, v in series_bible.data["characters"].items():
            desc = v.get("description", "") if isinstance(v, dict) else str(v)
            if k not in all_known_chars:
                all_known_chars[k] = desc

    for spk in clean_speakers:
        for cname, cdesc in all_known_chars.items():
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
        return f"[KADR 1-NA-1: Rozmowa w cztery oczy ({clean_speakers[0]} i {clean_speakers[1]}) -> Kategoryczny wymóg bezpośredniego 'ty' i 2. os. lp.]"

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

    # 4. Starting Token Calque Mirror (e.g. 'Wait,' -> 'Czekaj,', 'Listen,' -> 'Słuchaj,')
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
        thinking_budget_phase2: Optional[int] = None
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
        self.system_prompt = get_translation_system_prompt(keep_honorifics=keep_honorifics, lean=True)
        
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
        self.lock = threading.Lock()
        # Smart Batch Queueing & Pacing:
        # Default to 1-by-1 streaming pacing mode (eliminates TPU congestion and provides live instant updates)
        default_concurrency = 1
        self.concurrent_batches = int(os.getenv("CONCURRENT_BATCHES", str(default_concurrency)))

    FEMALE_ROLE_KEYWORDS = FEMALE_ROLE_KEYWORDS
    MALE_ROLE_KEYWORDS = MALE_ROLE_KEYWORDS
    BOY_ROLE_KEYWORDS = BOY_ROLE_KEYWORDS

    def _register_character_safe(self, name: str, gender: str, role: str = "") -> None:
        """
        Safely registers or updates a character in self.character_registry with
        symmetrical immutable protection (cannot downgrade/overwrite confirmed FEMALE with MALE
        or confirmed MALE with FEMALE).
        """
        if not name:
            return
        clean_name = name.strip()
        new_desc = f"{gender} ({role or 'postać'})".strip()
        new_lower = new_desc.lower()

        if clean_name in self.character_registry:
            existing_desc = self.character_registry[clean_name]
            existing_lower = existing_desc.lower()

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

        # 1. Parse dramatic_sequences from EpisodeProfile (Pre-pass Profilera)
        if episode_profile and getattr(episode_profile, "dramatic_sequences", None):
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
                is_fem = getattr(seq, "female_only_scene", False)
                is_male = getattr(seq, "male_only_scene", False)
                if not (is_fem or is_male):
                    continue
                tr_str = getattr(seq, "time_range", "")
                ms_range = _parse_time_range_to_ms(tr_str)
                if not ms_range:
                    continue
                seq_start_ms, seq_end_ms = ms_range
                target_g = "kobieta" if is_fem else "mężczyzna"
                for orig_idx, ev in norm_entries:
                    ev_s = getattr(ev, "start", 0)
                    ev_e = getattr(ev, "end", 0)
                    if (ev_s >= seq_start_ms and ev_s <= seq_end_ms) or (ev_e >= seq_start_ms and ev_e <= seq_end_ms):
                        scene_genders[orig_idx] = target_g

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

                if hasattr(self.series_bible, "infer_scene_cast_from_text"):
                    _, sc_gender = self.series_bible.infer_scene_cast_from_text(scene_texts, whisper_texts=scene_whisper)
                    if sc_gender == "FEMALE":
                        for idx in scene_indices:
                            scene_genders[idx] = "kobieta"
                    elif sc_gender == "MALE":
                        for idx in scene_indices:
                            scene_genders[idx] = "mężczyzna"

        return scene_genders

    def _arbitrate_speaker_gender(
        self,
        event: pysubs2.SSAEvent,
        raw_phase1_gender: Optional[str],
        batch_id: int,
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
        if is_generic_actor_or_category(raw_spk):
            raw_spk = ""
        spk_clean = extract_clean_speaker_name(raw_spk) or raw_spk
        spk_lower = spk_clean.lower()
        tokens = set(re.findall(r"\b[a-ząćęłńóśźżA-ZĄĆĘŁŃÓŚŹŻ]+\b", spk_lower))

        # 0. Inherent lexical gender check (e.g. "Girl\\Italic", "Woman", "Boy")
        if not is_generic_actor_or_category(spk_clean):
            if spk_lower in INHERENT_FEMALE_NOUNS or any(t in INHERENT_FEMALE_NOUNS for t in tokens):
                canonical_gender = "kobieta"
            elif spk_lower in INHERENT_MALE_NOUNS or any(t in INHERENT_MALE_NOUNS for t in tokens):
                canonical_gender = "mężczyzna"

        # 1. Canonical Authority Check
        if not canonical_gender and spk_clean:
            for check_name in [spk_clean, raw_spk]:
                if check_name in self.character_registry:
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

        # 1b. Episode Scene Cast Pre-computation Check (Continuous Scene Ground Truth for Anonymous Lines)
        if not canonical_gender and not spk_clean:
            check_idx = event_idx if event_idx is not None else batch_id
            if hasattr(self, "episode_scene_genders") and self.episode_scene_genders:
                if check_idx in self.episode_scene_genders:
                    canonical_gender = self.episode_scene_genders[check_idx]
                elif getattr(event, "_orig_idx", None) in self.episode_scene_genders:
                    canonical_gender = self.episode_scene_genders[getattr(event, "_orig_idx")]
                if canonical_gender == "kobieta":
                    alerts.append("[🚨 SCENA KOBIECA (Pre-pass Sceniczny): Mówczyni żeńska! Wymóg form żeńskich w 1. os. (-łam/-łabym) i 2. os. (-łaś / wzburzoną)]")
                elif canonical_gender == "mężczyzna":
                    alerts.append("[🚨 SCENA MĘSKA (Pre-pass Sceniczny): Mówca męski! Wymóg form męskich w 1. os. (-łem/-łbym) i 2. os. (-łeś / wzburzonego)]")

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
                    alerts.append("[🚨 SCENA KOBIECA (Baza Wiedzy): Mówczyni żeńska! Wymóg form żeńskich w 1. os. (-łam/-łabym) i 2. os. (-łaś / wzburzoną)]")
                elif inf_g == "MALE":
                    canonical_gender = "mężczyzna"

        # 2. Acoustic & Linguistic Ground Truth
        acoustic_gender = None
        if speaker_tags and batch_id in speaker_tags:
            v_tag = speaker_tags[batch_id].lower()
            if "sopran" in v_tag or "dziecięcy" in v_tag or "wysoki tembr" in v_tag:
                acoustic_gender = "kobieta"
            elif "alt starszej" in v_tag or "ochrypły alt" in v_tag or "alt żeński" in v_tag:
                # Raspy or mature female alto / contralto voice - ambiguous pitch, NOT male
                acoustic_gender = None
            elif "żeńsk" in v_tag and "alt" not in v_tag and "ochrypł" not in v_tag:
                hz_match = re.search(r"~(\d+)\s*hz", v_tag)
                if hz_match:
                    hz_val = int(hz_match.group(1))
                    if hz_val >= 195:
                        acoustic_gender = "kobieta"
                    elif hz_val <= 150:
                        acoustic_gender = "mężczyzna"
                else:
                    acoustic_gender = "kobieta"
            elif "baryton" in v_tag or "bas" in v_tag:
                acoustic_gender = "mężczyzna"
            elif "męsk" in v_tag and "alt" not in v_tag and "ochrypł" not in v_tag:
                acoustic_gender = "mężczyzna"

        raw_jp = whisper_transcriptions.get(batch_id, "") if whisper_transcriptions else ""
        if isinstance(raw_jp, dict):
            jp_text = str(raw_jp.get("text", "")).lower()
        else:
            jp_text = str(raw_jp).lower()
        wdd_tag = WhisperDisambiguator.disambiguate_line(clean_en="", jp_audio=jp_text)
        jp_female_marker = (wdd_tag.speaker_gender == "FEMALE") or any(m in jp_text for m in ["atashi", "あたし", "atai", "あtai", "kashira", "かしら", "わよ", "wayo"])
        jp_male_marker = (wdd_tag.speaker_gender == "MALE") or any(m in jp_text for m in ["ore", "俺", "boku", "僕"])

        # Persist definitive Japanese acoustic pronoun evidence to Character Registry and Series Bible
        if spk_clean and not canonical_gender and not is_generic_actor_or_category(spk_clean):
            if wdd_tag.speaker_gender == "MALE":
                self._register_character_safe(spk_clean, "mężczyzna", role="seiyū Whisper")
                if hasattr(self, "series_bible") and self.series_bible and hasattr(self.series_bible, "update_character_gender_from_audio"):
                    self.series_bible.update_character_gender_from_audio(spk_clean, "MALE")
            elif wdd_tag.speaker_gender == "FEMALE":
                self._register_character_safe(spk_clean, "kobieta", role="seiyū Whisper")
                if hasattr(self, "series_bible") and self.series_bible and hasattr(self.series_bible, "update_character_gender_from_audio"):
                    self.series_bible.update_character_gender_from_audio(spk_clean, "FEMALE")

        raw_norm = (raw_phase1_gender or "").lower()
        phase1_is_female = any(w in raw_norm for w in ["kobieta", "żeńsk", "female", "dziewczyn"])
        phase1_is_male = any(w in raw_norm for w in ["mężczyzna", "męsk", "male", "chłopak"])

        # 3. Hierarchy Arbitration & Veto Evaluation
        # Case A: Canonical Authority prevails
        if canonical_gender == "kobieta":
            # Acoustic Primacy: If voice is confirmed male (acoustic_gender == "mężczyzna" or jp_male_marker),
            # reject false female assignment (e.g. from family surname collision like Honoka Tomine vs Issei Tomine)
            char_d = (self.character_registry.get(spk_clean, "") or "") if spk_clean else ""
            char_d_low = char_d.lower()
            is_low_pitch = any(k in char_d_low for k in ["starsza", "dojrzała", "babcia", "matrona", "cesarzow", "chatun", "wiedźma", "ochrypł"])
            if hasattr(self, "series_bible") and self.series_bible and hasattr(self.series_bible, "is_low_pitch_female") and self.series_bible.is_low_pitch_female(spk_clean):
                is_low_pitch = True

            if (acoustic_gender == "mężczyzna" and not is_low_pitch) or jp_male_marker:
                alerts.append(f"[🚨 WETO AKUSTYCZNE SEIYŪ: Męski głos F0/Whisper unieważnił fałszywy tag żeński dla '{spk_clean}'! Zastosowano 'mężczyzna']")
                canonical_gender = "mężczyzna"
            else:
                if phase1_is_male:
                    alerts.append(f"[🚨 ALARM ARBITRAŻU: Faza 1 błędnie przypisała rodzaj męski dla potwierdzonej kobiety '{spk_clean}'! Zastosowano Weto Kanonu -> wymuszono 'kobieta']")
                has_masc_verb = bool(re.search(r"\b(byłem|miałem|widziałem|wiedziałem|zrobiłem|pomyślałem|chciałem|mogłem|poszedłem|powiedziałem|czułem|słyszałem|wróciłem|dostałem|znalazłem|oddałem|zgubiłem|uratowałem|przyszedłem|doniósłbym|wiedziałbym|mógłbym|chciałbym|miałbym|zrobiłbym|byłbym|wolałbym|musiałbym|poszedłbym|zraniłem|skrzywdziłem|zostawiłem|poczułem|zobaczyłem)\b", pl_candidate, re.IGNORECASE))
                if has_masc_verb:
                    alerts.append(f"[🚨 ALARM KOREKTY FLEKSYJNEJ: Faza 1 wygenerowała formę męską (-łem/-łbym) dla mówczyni '{spk_clean}'! Faza 2 BEZWZGLĘDNIE musi zastosować formę żeńską (-łam / -łabym / -łaś)!]")
                return "kobieta", alerts

        if canonical_gender == "mężczyzna":
            # Check if character is marked as a young boy or cross-gender role (voiced by female seiyū)
            char_desc_lower = ""
            if spk_clean in self.character_registry:
                char_desc_lower = str(self.character_registry[spk_clean]).lower()
            elif hasattr(self, "series_bible") and self.series_bible and hasattr(self.series_bible, "data"):
                b_val = self.series_bible.data.get("characters", {}).get(spk_clean, {})
                char_desc_lower = (b_val.get("description", "") if isinstance(b_val, dict) else str(b_val)).lower()

            is_boy_or_crossgender = any(k in char_desc_lower for k in self.BOY_ROLE_KEYWORDS) or any(k in spk_lower for k in ["chłopiec", "chłopak", "boy", "bocchan"])

            if is_boy_or_crossgender:
                alerts.append(f"[🎯 ALARM CROSS-GENDER CHŁOPIĘCY: Postać męska '{spk_clean}' (młody chłopiec/syn/książę) dubbingowana przez żeńskie seiyū! Zablokowano nadpisanie głosem F0 -> zachowano 'mężczyzna']")
                return "mężczyzna", alerts

            # Acoustic Primacy Gate (Filar CLXXIV): Untrusted fansub tag contradicted by female audio or scene
            tag_text = ((speaker_tags.get(batch_id, "") or speaker_tags.get(event_idx, "")) if speaker_tags else "").lower()
            tag_is_fem = any(k in tag_text for k in ["żeńsk", "sopran", "kobieta", "alt"])
            has_female_audio = (acoustic_gender == "kobieta") or jp_female_marker or tag_is_fem
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

            if has_female_audio or (is_scene_female and is_cont):
                alerts.append(f"[🚨 ALARM PRYMATU AKUSTYCZNEGO (Filar CLXXIV): Tag aktora '{spk_clean}' (mężczyzna) sprzeczny z głosem żeńskim seiyū / skażony w scenie! Zastosowano korektę akustyczną -> wymuszono 'kobieta']")
                return "kobieta", alerts

            if phase1_is_female:
                alerts.append(f"[🚨 ALARM ARBITRAŻU: Faza 1 błędnie przypisała rodzaj żeński dla potwierdzonego mężczyzny '{spk_clean}'! Zastosowano Weto Kanonu -> wymuszono 'mężczyzna']")
            return "mężczyzna", alerts

        # Case B: Cross-Gender Voice Shield (Filar CLXXI)
        # If speaker uses male first-person pronouns (boku/ore/bocchan) with high female F0 pitch,
        # male pronoun OVERRIDES high female pitch (vital for anime where adult female seiyū dub young boys).
        if jp_male_marker and acoustic_gender == "kobieta":
            alerts.append(f"[🎯 ALARM CROSS-GENDER (Filar CLXXI): Wysoki tembr F0 (~kobiecy), lecz seiyū używa męskiego zaimka 'boku/ore'! Wymuszono rodzaj męski (młody chłopiec)]")
            return "mężczyzna", alerts

        if jp_female_marker and acoustic_gender == "mężczyzna":
            alerts.append(f"[🎯 ALARM CROSS-GENDER: Niski tembr F0, lecz seiyū używa żeńskiego zaimka 'atashi/kashira'! Wymuszono 'kobieta']")
            return "kobieta", alerts

        # Case C: Acoustic / Japanese linguistic Ground Truth overrides unknown Phase 1
        if (acoustic_gender == "kobieta" or jp_female_marker) and phase1_is_male:
            char_d = (self.character_registry.get(spk_clean, "") or "") if spk_clean else ""
            char_d_low = char_d.lower()
            is_boy = any(k in char_d_low for k in self.BOY_ROLE_KEYWORDS) or any(k in spk_lower for k in ["chłopiec", "chłopak", "boy", "bocchan"])
            if is_boy:
                alerts.append(f"[🎯 ALARM CROSS-GENDER CHŁOPIĘCY: Głos żeński F0 seiyū, lecz kontekst/rola '{spk_clean}' wskazuje młodego chłopca! Zachowano rodzaj męski z Fazy 1]")
                return "mężczyzna", alerts
            alerts.append(f"[🚨 ALARM ARBITRAŻU AKUSTYCZNEGO: Faza 1 wskazała rodzaj męski, lecz obiektywny odsłuch F0/Whisper wykazuje głos żeński! Wymuszono 'kobieta']")
            return "kobieta", alerts

        if jp_male_marker and phase1_is_female:
            alerts.append(f"[🚨 ALARM ARBITRAŻU: Faza 1 wskazała rodzaj żeński, lecz seiyū używa jednoznacznie męskiego zaimka 'ore/boku'! Wymuszono 'mężczyzna']")
            return "mężczyzna", alerts
        elif acoustic_gender == "mężczyzna" and phase1_is_female:
            char_d = (self.character_registry.get(spk_clean, "") or "") if spk_clean else ""
            char_d_low = char_d.lower()
            is_matron = any(k in char_d_low for k in ["starsza", "dojrzała", "babcia", "matrona", "cesarzow", "chatun", "wiedźma", "ochrypł"])
            if self.series_bible and hasattr(self.series_bible, "is_low_pitch_female") and self.series_bible.is_low_pitch_female(spk_clean):
                is_matron = True
            if is_matron:
                alerts.append(f"[ℹ️ INFO ARBITRAŻU: Faza 1 wskazała rodzaj żeński przy niskim tembrze F0 – potwierdzono dojrzały/ochrypły głos żeński (Filar CXXXVI/CLXXI) -> zachowano 'kobieta']")
                return "kobieta", alerts
            alerts.append(f"[🚨 ALARM ARBITRAŻU AKUSTYCZNEGO: Faza 1 wskazała rodzaj żeński, lecz obiektywny odsłuch F0 wykazuje głos męski (baryton/bas)! Wymuszono 'mężczyzna']")
            return "mężczyzna", alerts

        # Case C: Direct Phase 1 or Fallback
        if phase1_is_female:
            return "kobieta", alerts
        elif phase1_is_male:
            return "mężczyzna", alerts
        elif acoustic_gender:
            return acoustic_gender, alerts
        elif jp_female_marker:
            return "kobieta", alerts
        elif jp_male_marker:
            return "mężczyzna", alerts

        return None, alerts

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
        - addressee_label: np. "Grupa Kobiet (L. mnoga niemęskoosobowa: -łyście)", "Naie (Kobieta)"
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
            for cname in (self.character_registry.keys() if hasattr(self, "character_registry") and self.character_registry else []):
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
                return "grupa_mieszana", "Grupa Mieszana (Zbiorowość/L. mnoga męskoosobowa: -liście)"

            check_idx = orig_idx if orig_idx is not None else (getattr(event, "_orig_idx", None) if getattr(event, "_orig_idx", None) is not None else event_idx)
            sc_g = (self.episode_scene_genders.get(check_idx) if hasattr(self, "episode_scene_genders") and self.episode_scene_genders else None)

            has_explicit_male = any(w in clean_lower for w in ["boy", "boys", "men", "chłopak", "panowie"]) or any(w in raw_norm for w in ["grupa_mężczyzn", "mężczyzna", "mężczyzn", "męsk", "male", "chłopak", "żołnierz"])
            has_explicit_female = any(w in clean_lower for w in ["girl", "girls", "lady", "ladies", "women", "dziewcz", "kobiet"]) or any(w in raw_norm for w in ["grupa_kobiet", "kobieta", "kobiet", "żeńsk", "female", "dziewczyn"])

            has_gendered_female = has_explicit_female or (sc_g == "kobieta")
            has_gendered_male = has_explicit_male or (sc_g == "mężczyzna")

            if has_gendered_female and not has_explicit_male:
                return "grupa_kobiet", "Grupa Kobiet (L. mnoga niemęskoosobowa: -łyście)"
            elif has_gendered_male and not has_explicit_female:
                return "grupa_mężczyzn", "Grupa Mężczyzn (L. mnoga męskoosobowa: -liście)"
            else:
                return "grupa_mieszana", "Grupa Mieszana (Zbiorowość/L. mnoga męskoosobowa: -liście)"

        # 1. Textual Vocative Check (Calling someone by name in line text)
        for cname in self.character_registry.keys():
            if len(cname) >= 3 and re.search(rf"\b{re.escape(cname)}[,!?]", clean_text, re.IGNORECASE):
                cdesc = self.character_registry[cname].lower()
                if any(k in cdesc for k in self.FEMALE_ROLE_KEYWORDS):
                    return "kobieta", f"{cname} (Kobieta)"
                elif any(k in cdesc for k in self.MALE_ROLE_KEYWORDS):
                    return "mężczyzna", f"{cname} (Mężczyzna)"

        # 1b. Onomastic Vocative Check (Direct address in English/Polish script, e.g. "Monika, ...", "Moniko, ...")
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

        # 2. 1-on-1 Dialogue Alternation (Ping-Pong Turn & Acoustic F0 Alternation)
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

        # 2a. Acoustic F0 Alternation in Anonymous Dialogue
        if speaker_tags:
            def _extract_voice_gender(tag_text: str) -> Optional[str]:
                t = (tag_text or "").lower()
                if any(k in t for k in ["żeński", "kobieta", "female", "alt", "sopran"]):
                    return "kobieta"
                if any(k in t for k in ["męski", "mężczyzna", "male", "bas", "baryton", "tenor"]):
                    return "mężczyzna"
                hz_matches = [int(m.group(1)) for m in re.finditer(r"(\d+)\s*hz", t)]
                if hz_matches:
                    avg_hz = sum(hz_matches) / len(hz_matches)
                    if avg_hz >= 175:
                        return "kobieta"
                    elif avg_hz <= 155:
                        return "mężczyzna"
                return None

            curr_tag = speaker_tags.get(event_idx + 1, "") or speaker_tags.get(orig_idx, "")
            curr_v_gen = _extract_voice_gender(curr_tag)

            adj_tag = ""
            if event_idx > 0 and (event_idx in speaker_tags):
                adj_tag = speaker_tags[event_idx]
            elif (event_idx + 2) in speaker_tags:
                adj_tag = speaker_tags[event_idx + 2]
            elif lookback_history and lookback_history[-1].get("speaker_voice"):
                adj_tag = lookback_history[-1]["speaker_voice"]

            adj_v_gen = _extract_voice_gender(adj_tag)
            if curr_v_gen and adj_v_gen and curr_v_gen != adj_v_gen:
                if adj_v_gen == "kobieta":
                    return "kobieta", "Kobieta (Rozmowa 1-na-1 / Naprzemienność F0)"
                elif adj_v_gen == "mężczyzna":
                    return "mężczyzna", "Mężczyzna (Rozmowa 1-na-1 / Naprzemienność F0)"

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
                pass

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
            for name, details in self.character_registry.items():
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
                    lines.append(f"• {name}: {details}")
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
            character_registry=self.character_registry,
            series_bible=getattr(self, "series_bible", None)
        )
        if social_context:
            lines.append("--- STATUS SPOŁECZNY SCENY (UCHI-SOTO / KADR 1-NA-1 VS ZBIOROWY) ---")
            lines.append(social_context)
            lines.append("-------------------------------------------------------------------\n")

        # 3. Lines to translate
        lines.append("Przetłumacz poniższe kwestie na naturalny, żywy język polski, dbając o filmowy rytm dialogu:\n"
                     "1. SYNTAKTYKA I CIĄGŁOŚĆ: Analizuj całe zdania rozbite na linijki. Dbaj o naturalny polski szyk wyrazów i płynność gramatyczną.\n"
                     "2. LICZBA I PŁEĆ: W rozmowach 1-na-1 'you' tłumacz w 2. osobie l. pojedynczej ('ty'). Płeć form przeszłych dopasuj ściśle do metadanych i audio seiyū.\n"
                     "3. TRIANGULACJA EN+JP+OBRAZ: Skrypt EN daje logikę i nazwy, japońskie audio daje rejestr/tonację i zgodność z uchem widza, a klatki wideo służą do odczytu napisów ekranowych.\n"
                     "4. WIELOGŁOS: Wypowiedzi dwóch osób w jednej kwestii rozdziel na dwie linie ('- Kwestia 1\\N- Kwestia 2').\n"
                     "5. NATURALNOŚĆ: Bezwzględnie unikaj sztucznych kalek i sztywnych definicji (np. 'That bombed' -> 'Nie wyszło mi', 'I'm home' -> 'Wróciłam!', 'I see' -> 'Rozumiem'):")

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
                        relation_tag = f" [⚡ PĘKNIĘCIE AFEKTYWNE (Filar CLXXVIII, Ac=SHOCK_DROP): Gwałtowne załamanie energii seiyū (szok/zamilknięcie); wygaś ładunek emocjonalny do szeptu/zduszonego głosu w harmonii z aktorem]"
                    elif (is_shot_cut or time_gap_ms >= 3800) and (is_prev_private_request or is_curr_delayed_agreement):
                        relation_tag = f" [🎬 CIĘCIE SCENY (FFmpeg) / DYSKONTINUITET CZASOWY: Nowe ujęcie (pauza {time_gap_ms/1000.0:.1f}s) / Zmiana sceny (Filar CLXV) – nowa rozmowa: 'Więc o co chodzi?' / 'Słucham cię']"
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
                        k_alert = f"[🎙️ ALARM KLISZY FANSUBERSKIEJ (Filar CLXVI): W audio padło pytanie '{jp_audio_line}' bez potaknięcia – zignoruj angielskie 'Sure/Yeah', tłumacz: 'O co chodzi?' / 'Co się stało?']"
                        relation_tag = f"{relation_tag} {k_alert}".strip() if relation_tag else f" {k_alert}"
                    elif len(clean_text.split()) <= 2 and any(w == "here" for w in re.findall(r"\b[a-zA-Z]+\b", clean_en_lower)) and any(tok in jp_audio_line for tok in ["yoisho", "dokkoisho", "hora", "douzo"]):
                        s_alert = "[🎙️ ALARM SZUMU KINEZJATYCZNEGO (Filar IV/XVIII/CLXVI): W audio seiyū jest gest/kakegoe – oddaj sytuacyjnie: 'Proszę / Trzymaj' lub zastosuj elipsę]"
                        relation_tag = f"{relation_tag} {s_alert}".strip() if relation_tag else f" {s_alert}"
            except Exception:
                relation_tag = ""
                compact_wdd_tag = ""

            # Fuzzy Entity Casing Normalizer: Ensure proper names from series bible & character registry have uppercase first letter
            clean_display_text = clean_text
            canonical_entities = set()
            if self.character_registry:
                canonical_entities.update(self.character_registry.keys())
            if hasattr(self, "series_bible") and self.series_bible and hasattr(self.series_bible, "data"):
                canonical_entities.update(self.series_bible.data.get("characters", {}).keys())
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
                lines.append(f"Kwestia [ID: {idx + 1}] [TYP: [NAPIS] {vtype['type_label']}] (Czas: {start_str} - {end_str}, Cechy: {vtype['visual_details']}):")
                lines.append(f"  📄 SKRYPT PODSTAWOWY EN (TREŚĆ I MAJUSKUŁA): {clean_display_text}")

                # Active Line Glossary Pinning: Check if any canonical glossary terms appear in sign
                active_gloss = getattr(self, "combined_glossary", {})
                if active_gloss:
                    clean_lower = clean_text.lower()
                    for term_en, term_pl in active_gloss.items():
                        if term_en and len(term_en) >= 3 and term_en.lower() in clean_lower:
                            lines.append(f"  📖 SŁOWNIK KANONICZNY: '{term_en}' => '{term_pl}' (wymóg terminologiczny; unikaj powtarzania deskryptorów)")
                lines.append(f"  (!) UWAGA WIZUALNA: To jest NAPIS / TYTUŁ NA EKRANIE (np. tytuł odcinka/rozdziału, tytuł mangi, tablica, szyld, plansza).")
                lines.append(f"  Przetłumacz ten tekst jako SAMODZIELNY TYTUŁ/NAPIS (np. 'The Princess's Favor' / '姫様のご寵愛' -> 'Łaska księżniczki').")
                lines.append(f"  (!) POŁOŻENIE I TYPESETTING (Pixel-Perfect Grounding): Spójrz na klatkę wideo i w obiekcie 'visual_typesetting' podaj Bounding Box japońskiego napisu 'detected_box_1000' [ymin, xmin, ymax, xmax] (0-1000), pozycję 'placement' ('above'/'below'/'overlay'/'beside_right'/'beside_left'), kąt obrotu 'rotation_deg' (-45 do 45) oraz kolory HEX ('primary_color_hex', 'outline_color_hex'). W 'screen_region' wskaż kwadrant.")
                lines.append(f"  (Typografia: przetłumacz wyłącznie treść napisu/planszy na ekranie)")
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
                    reg_desc = "L. mnoga niemęskoosobowa / dwie kobiety ('wy': -łyście / 'obie')"
                elif line_addr_cat in ["grupa_mężczyzn", "mężczyzna_dual"]:
                    reg_desc = "L. mnoga męskoosobowa / dwóch mężczyzn ('wy': -liście / 'obaj')"
                elif line_addr_cat in ["grupa_mieszana", "para_mieszana_dual"]:
                    reg_desc = "L. mnoga / para mieszana ('wy': -liście / liczebnik zbiorowy: 'oboje')"
                elif line_addr_cat == "kobieta":
                    reg_desc = "2. os. lp. 'ty' do kobiety (-łaś / wzburzoną)"
                elif line_addr_cat == "mężczyzna":
                    reg_desc = "2. os. lp. 'ty' do mężczyzny (-łeś / wzburzonego)"
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
                lines.append(f"  📄 SKRYPT PODSTAWOWY EN (TREŚĆ, FAKTY, SKŁADNIA I MAJUSKUŁA): {clean_display_text}")
                if compact_wdd_tag:
                    lines.append(f"  {compact_wdd_tag}")
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
                            lines.append(f"  📖 SŁOWNIK KANONICZNY: '{term_en}' => '{term_pl}' (forma bazowa – w dialogu ZAWSZE odmieniaj przez polskie przypadki!; unikaj powtarzania deskryptorów: jeśli w zdaniu jest już 'z prowincji', 'na górze', stosuj samą nazwę)")
                if vtype.get("is_top"):
                    lines.append(f"  (!) DIALOG GÓRNY / W TLE: Dialog postaci w tle/oddali – formatuj jako naturalny dialog mówiony (Sentence case).")
                is_split_part = (
                    clean_text.strip().startswith("...")
                    or clean_text.strip().startswith("…")
                    or prev_clean.endswith("...")
                    or prev_clean.endswith("…")
                )
                if duration_s <= 0.6 and not is_split_part:
                    lines.append(f"  (!) MIKRO-KWESTIA / DŹWIĘK WAHANIA (czas {duration_s:.1f}s, tempo {cps:.1f} z/s): Kwestia trwa ułamek sekundy! Zastosuj Filar CXXXIV: zredukuj do 1-2 słów (np. 'Znaczy...', 'Ech...', 'Cóż...').")
                elif duration_s <= 0.6 and is_split_part:
                    lines.append(f"  (!) KRÓTKI CZAS TRWANIA ({duration_s:.1f}s, tempo {cps:.1f} z/s): Fragment zdania rozbitego wielokropkiem! ZACHOWAJ CIĄGŁOŚĆ SKŁADNIOWĄ (Filar LVI & CLXIX) i zwięzłość AVT.")
                elif is_fast:
                    lines.append(f"  (!) TEMPO CPS ({cps:.1f} z/s, czas {duration_s:.1f}s): Szybka kwestia! Zastosuj zwięzłą kondensację Belczyka.")

                max_pl_chars = min(76, int(max(0.5, duration_s) * 17.0))
                lines.append(f"  (!) BUDŻET ZNAKOWY AVT: Maksymalnie {max_pl_chars} znaków ze spacjami (tempo czytania 17.0 z/s, max 2 wiersze na ekranie) – NIE PRZEKRACZAJ!")

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
                        lines.append(f"  [🎙️ ALARM ROZBIEŻNOŚCI AUDIO JP]: W audio seiyū padło krótkie wahanie ('{jp_display}') – ogranicz kwestię do samego wahania: 'Znaczy...', 'Cóż...', 'Ech...'.")
            if episode_profile:
                pinned_alerts = getattr(self, "profile_line_alerts", {}).get(original_idx) or getattr(self, "profile_line_alerts", {}).get(idx)
                if pinned_alerts:
                    for pa in pinned_alerts:
                        lines.append(f"  {pa}")
                else:
                    if getattr(episode_profile, "danger_lines_prescan", None):
                        for dl in episode_profile.danger_lines_prescan:
                            if dl.english_phrase and dl.english_phrase.lower() in clean_text.lower():
                                lines.append(f"  [🚨 PUŁAPKA PROFILERA: {dl.contextual_trap} => DYREKTYWA: {dl.mandatory_direction}]")
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
            lines.append("\n--- PODGLĄD NASTĘPNYCH KWESTII (NIE TŁUMACZ ICH! Użyj tylko do zrozumienia kontekstu i płci) ---")
            for _, fut_ev, future_text, _ in lookahead_events[:4]:
                fut_spk = f" (Mówca: {fut_ev.name})" if fut_ev and getattr(fut_ev, "name", None) else ""
                lines.append(f"[Wkrótce]{fut_spk} EN: {future_text}")
            lines.append("------------------------------------------------------------------------------------------------")

        return "\n".join(lines)

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

                if hasattr(response, "usage_metadata") and response.usage_metadata:
                    um = response.usage_metadata
                    with self.lock:
                        self.current_episode_tokens["prompt"] += getattr(um, "prompt_token_count", 0) or 0
                        self.current_episode_tokens["cached"] += getattr(um, "cached_content_token_count", 0) or 0
                        cands = getattr(um, "candidates_token_count", 0) or 0
                        thoughts = getattr(um, "thoughts_token_count", 0) or 0
                        self.current_episode_tokens["output"] += (cands + thoughts)
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
                    print("  [!] [BŁĄD KONTA GOOGLE AI STUDIO / PŁATNOŚCI]:")
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
                        f"KATEGORYCZNA BLOKADA BEZPIECZEŃSTWA: Osiągnięto limit {attempt} prób dla partii w Fazie 1. "
                        f"Ostatni błąd: {e}. Proces wstrzymano w celu ochrony budżetu przed niekontrolowanymi zapytaniami."
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
                is_th = "italic" in (prev_event.style or "").lower() or r"\i1" in (prev_event.text or "")
                lookback_history.append({
                    "en": prev_clean_en,
                    "pl": prev_pl,
                    "speaker": spk,
                    "is_thought": is_th
                })
        elif history:
            lookback_history = list(history[-4:])

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
                    pass

            for fpath in temp_frames:
                try:
                    img = Image.open(fpath)
                    image_contents.append(img)
                except Exception:
                    pass

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
            is_th = "italic" in style_str.lower() or r"\i1" in (ev.text or "")
            vtype_info = detect_event_visual_type(ev, ts_pref, style_report=getattr(self, "style_report", None))
            batch_items_for_rules.append({
                "id": b_id,
                "orig_idx": orig_idx,
                "en": clean_txt,
                "audio_jp": whisper_transcriptions.get(b_id, "") if whisper_transcriptions else "",
                "style": style_str,
                "is_thought": is_th,
                "duration_s": dur_s,
                "cps": cps_val,
                "is_sign": vtype_info["is_sign"],
                "speaker_gender": self.character_registry.get(ev.name),
                "speaker": ev.name,
                "prosody": prosody_tags.get(b_id, ""),
                "speaker_voice": speaker_tags.get(b_id, ""),
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
        batch_response = self._call_gemini_with_retry(
            contents=contents,
            schema_class=BatchTranslationResponse
        )

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
            if batch_response:
                for tr in batch_response.translations:
                    if tr.id == batch_id:
                        pl_candidate = sanitize_sub_text(tr.polish_text)
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
                notes = f"{notes} [🚨 LUKA W FAZIE 1: Kwestia pominięta w szkicu! PRZETŁUMACZ OD ZERA Z EN I AUDIO JP!]".strip()

            # Multi-Signal Gender Arbitration Engine (0.00 PLN)
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
            if arb_alerts:
                notes = f"{notes} {' '.join(arb_alerts)}".strip()

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

            # Line-Level Pinning: Direct Profiler alerts for this specific line
            pinned_alerts = getattr(self, "profile_line_alerts", {}).get(orig_idx) or getattr(self, "profile_line_alerts", {}).get(idx)
            if pinned_alerts:
                for pa in pinned_alerts:
                    notes = f"{notes} {pa}".strip()
            elif episode_profile:
                if getattr(episode_profile, "danger_lines_prescan", None):
                    for dl in episode_profile.danger_lines_prescan:
                        if dl.english_phrase and dl.english_phrase.lower() in clean_en.lower():
                            trap_tag = f"[🚨 PUŁAPKA PROFILERA: {dl.contextual_trap} => DYREKTYWA: {dl.mandatory_direction}]"
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
                        relation_tag = f"[🎬 CIĘCIE SCENY (FFmpeg) / DYSKONTINUITET CZASOWY: Pauza {time_gap_s:.1f}s / Nowa scena (Filar CLXV) – postacie zmieniły lokację; otwarcie rozmowy: 'Więc o co chodzi?' / 'No to o co chodzi?' / 'Słucham cię']"
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
                            relation_tag = f"{relation_tag} [🎙️ ALARM KLISZY FANSUBERSKIEJ (Filar CLXVI): W audio padło pytanie '{jp_text}' bez potaknięcia – zignoruj angielskie 'Sure/Yeah', tłumacz: 'O co chodzi?' / 'Co się stało?']".strip()
                        elif len(clean_en.split()) <= 2 and any(w == "here" for w in re.findall(r"\b[a-zA-Z]+\b", clean_en.lower())) and any(tok in jp_text.lower() for tok in ["yoisho", "dokkoisho", "hora", "douzo"]):
                            relation_tag = f"{relation_tag} [🎙️ ALARM SZUMU KINEZJATYCZNEGO (Filar IV/XVIII/CLXVI): W audio seiyū jest gest/kakegoe – oddaj sytuacyjnie: 'Proszę / Trzymaj' lub zastosuj elipsę]".strip()
            except Exception:
                relation_tag = ""

            dur_s = max(0.05, (event.end - event.start) / 1000.0)
            style_str = event.style or ""
            is_th = "italic" in style_str.lower() or r"\i1" in (event.text or "")

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
            has_severe_trap = bool(notes and any(k in notes for k in ["[🚨 PUŁAPKA PROFILERA", "[🚨 ALARM FILAR", "[🎙️ ALARM KLISZY"]))
            has_temporal_conflict = bool(relation_tag and ("DYSKONTINUITET CZASOWY" in relation_tag or "ALARM KLISZY FANSUBERSKIEJ" in relation_tag))
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

            pass1_items.append({
                "id": batch_id,
                "orig_idx": orig_idx,
                "event": event,
                "style": style_str,
                "is_thought": is_th,
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
                "speaker_name": resolved_spk_name,
                "speaker_gender": speaker_gender,
                "addressee": addressee_cat,
                "addressee_label": addressee_label,
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
            
            # Detect formal honorific address in line: "Panie Arato", "Pani Shizuku", "Mistrzu Ken"
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

            # Detect true first-name vocative in PL or EN (bare name, e.g. "Shizuku, dlaczego?!", "Shizuku, why?!")
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
                        rep_verb = "wygrałaś" if is_female_target else "wygrałeś"
                        drift_alert = f"[🚨 ALARM FILAR CLVII: Relacja na 'ty' po imieniu – zastosuj 2. os. '{rep_verb}' / 'wiesz']"
                        it["notes"] = f"{it.get('notes', '')} {drift_alert}".strip()

            # Multimodal Addressee Warning Pinning (Filar CLXIII):
            # Handled via structured attributes it['addressee'] & it['addressee_label'] in SSOT prompt generator.

            # Auditory Anchor Pinning (Filar CLVIII)
            audio_jp_str = str(it.get("audio_jp", "")).lower()
            if audio_jp_str and not it.get("is_sign"):
                pl_check = str(it.get("pl", "")).lower()
                if any(k in audio_jp_str for k in ["hitori", "一人", "独り", "ひとり"]) and ("daj mi spokój" in pl_check or "dajcie mi spokój" in pl_check):
                    it["notes"] = f"{it.get('notes', '')} [🚨 ALARM FILAR CLVIII: W audio pada 'Hitori' – tłumacz: 'Zostaw mnie samą/samego']".strip()
                elif any(k in audio_jp_str for k in ["betsuni", "別に"]) and ("to nic takiego" in pl_check or "nie ma sprawy" in pl_check):
                    it["notes"] = f"{it.get('notes', '')} [🚨 ALARM FILAR CLVIII: W audio pada 'Betsuni' – tłumacz: 'Wcale nie' / 'Mniejsza z tym']".strip()
                elif any(k in audio_jp_str for k in ["yokatta", "よかった", "良かった"]) and "to było dobre" in pl_check:
                    it["notes"] = f"{it.get('notes', '')} [🚨 ALARM FILAR CLVIII: W audio pada 'Yokatta' – tłumacz: 'Całe szczęście']".strip()
                elif any(k in audio_jp_str for k in ["yatta", "やった"]) and ("zrobiłem to" in pl_check or "zrobiłam to" in pl_check):
                    it["notes"] = f"{it.get('notes', '')} [🚨 ALARM FILAR CLVIII: W audio pada 'Yatta' – tłumacz: 'Udało się!']".strip()

            # Focalization & Dramatic Irony Guard (Filar CLXI)
            clean_en_lower = str(it.get("en", "")).lower()
            pl_check = str(it.get("pl", "")).lower()
            audio_jp_str = str(it.get("audio_jp", "")).lower()

            # Check 1: 3rd person in source (EN/JP) turned into 1st person in PL candidate
            has_3rd_person_source = any(tok in clean_en_lower for tok in ["by the", "written by", "paper by", "essay by"]) and not any(tok in clean_en_lower for tok in ["my ", "i ", "me ", "mine"])
            has_1st_person_pl = bool(re.search(r"\b(mój|moja|moje|moim|moich|moją|mego)\s+(esej|praca|artykuł|traktat|tekst)\b", pl_check))
            if has_3rd_person_source and has_1st_person_pl:
                focal_alert = "[🚨 ALARM FILAR CLXI: Tożsamość incognito – zachowaj 3. osobę mówcy zgodnie z oryginałem]"
                it["notes"] = f"{it.get('notes', '')} {focal_alert}".strip()

            # Check 2: Unsolicited thought italicization
            orig_ev = it.get("event")
            orig_ev_text = orig_ev.text if orig_ev and getattr(orig_ev, "text", None) else it.get("en", "")
            if r"\i1" not in orig_ev_text and not it.get("is_thought", False):
                if r"\i1" in str(it.get("pl", "")) and audio_jp_str:
                    unsolicited_italics_alert = "[🚨 ALARM FILAR CLXI: Dialog diegetyczny – usuń kursywę i traktuj jako mowę na głos]"
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
            any_redaction_printed = False
            for r in refined_lines:
                orig_item = next((it for it in pass1_items if it["id"] == r.id), None)
                orig_pl = orig_item["pl"] if orig_item else ""
                clean_ref = sanitize_sub_text(r.refined_pl)
                ch_desc = (getattr(r, 'changes_made', '') or '').strip()

                # Check if there is an actual textual modification or meaningful redaction note
                has_text_change = orig_pl and (orig_pl.strip() != clean_ref.strip())
                has_meaningful_note = bool(ch_desc and "Zweryfikowano" not in ch_desc and ch_desc.lower() != "null")

                if has_text_change or has_meaningful_note:
                    any_redaction_printed = True
                    clean_note = ch_desc if ch_desc.startswith("[") else (f"[{ch_desc}]" if ch_desc else "")
                    pillar_note = f" {clean_note}" if clean_note else ""

                    # Strip internal ASS tags (like {\i1}, {\i0}) for pure, clean console display
                    disp_orig = re.sub(r"\{[^\}]*\}", "", orig_pl).strip()
                    disp_ref = re.sub(r"\{[^\}]*\}", "", clean_ref).strip()

                    pbar.write(f" └─ [Redaktor Dialogów] #{r.id}{pillar_note}")
                    pbar.write(f"    ├─ Szkic:  \"{disp_orig}\"")
                    pbar.write(f"    └─ Szlif:  \"{disp_ref}\"")

            if not any_redaction_printed:
                pbar.write(f" └─ [Redaktor Dialogów] Zweryfikowano bez uwag (100% zgodności z Kanonem AVT)")

        prev_linted_line = (lookback_history[-1]["pl"] if lookback_history else "")
        for item in pass1_items:
            raw_final = sanitize_sub_text(refined_dict.get(item["id"], item["pl"]))
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
            final_text, fixes = AVTLinter.lint_and_fix_line(
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
                addressee_gender=item.get("addressee")
            )
            prev_linted_line = final_text
            # Deterministic glossary overrides
            final_text, gloss_fixes = GlossaryManager.apply_deterministic_overrides(final_text, combined_glossary)
            if item.get("is_song") and not item.get("is_sign"):
                clean_no_notes = re.sub(r"^[♪♫♬\s]+|[♪♫♬\s]+$", "", final_text).strip()
                if clean_no_notes:
                    final_text = f"♪ {clean_no_notes} ♪"
            for fix in fixes + gloss_fixes:
                pbar.write(f"  [AVT Linter/Słownik] {fix}")
            start_m = item.get("start_ms", item["event"].start if "event" in item else 0)
            end_m = item.get("end_ms", item["event"].end if "event" in item else 1000)
            final_text = clamp_sub_second_cps(final_text, start_m, end_m)
            formatted_final = split_subtitle_syntactically(final_text, max_line_len=42, is_ass=is_ass, is_sign=item.get("is_sign", False))
            batch_results[item["orig_idx"]] = formatted_final
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
        self.current_episode_tokens = {"prompt": 0, "cached": 0, "output": 0, "model": self.model}
        if self.verifier:
            self.verifier.current_episode_tokens = {"prompt": 0, "cached": 0, "output": 0, "model": self.verifier.model}

        is_ass = not str(subs_file).lower().endswith(".srt")

        from avt_linter import load_subtitle_file_resilient
        subs = load_subtitle_file_resilient(subs_file)

        # Initialize StyleMatrixEngine for geometric and semantic ASS classification
        from style_matrix import analyze_subtitles
        self.style_report = analyze_subtitles(subs)
        print(self.style_report.format_user_friendly_summary())

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
            
            # Pre-populate character registry from AniList (AniList SSOT rule):
            # ONLY define character gender if explicitly verified in AniList (Male/Female).
            # If missing/None, leave uncommitted so dynamic episode-level data resolves it.
            for c in anime_meta.get("characters", []):
                c_name = c.get("name")
                c_gen = c.get("gender")
                if c_name and c.get("has_verified_gender") and c_gen:
                    self._register_character_safe(c_name, c_gen, c.get("role", "postać"))
                elif c_name:
                    if c_name not in self.character_registry:
                        self.character_registry[c_name] = f"postać ({c.get('role', 'postać')})"

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
                    pass

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
            print(f"  [Żelazna Reguła OP/ED]: Zachowano {song_lines_preserved} wersów piosenek (Opening/Ending) w oryginalnej wersji bez wysyłania do AI (0 PLN).")

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

        # 0b. Initialize and load Series Bible (Cross-Episode Continuity)
        series_title = ""
        if anime_meta:
            series_title = anime_meta.get("title_romaji") or anime_meta.get("title_english") or ""
        if not series_title:
            ref_path = video_path or subs_path or ""
            if ref_path:
                series_title = Path(ref_path).stem.split(" - ")[0].replace("[ASW]", "").replace("[Erai-raws]", "").strip()
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
            for cname, creg in self.character_registry.items():
                if cname and cname not in char_dict:
                    char_dict[cname] = creg

            gloss_dict = {g.term_en: g.translation_pl for g in episode_profile.glossary}
            plot_anchors_dict = {}
            if getattr(episode_profile, "continuity_bridge_alerts", None):
                for cba in episode_profile.continuity_bridge_alerts:
                    if cba.term_or_event and cba.continuity_directive:
                        plot_anchors_dict[cba.term_or_event] = cba.continuity_directive

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
                logger.warning(f"Błąd Pre-pass Line Resolvera ({e_res})")

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
                pass
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
                                            "translated_results": translated_results,
                                            "translated_regions": translated_regions,
                                            "translated_typesetting": {
                                                str(k): (v.model_dump() if hasattr(v, "model_dump") else (v.dict() if hasattr(v, "dict") else v))
                                                for k, v in translated_typesetting.items()
                                            },
                                            "translated_addressees": translated_addressees,
                                            "translated_speakers": translated_speakers,
                                            "token_usage": {
                                                "f1": self.current_episode_tokens,
                                                "f2": self.verifier.current_episode_tokens if self.verifier else None
                                            }
                                        }
                                        with open(checkpoint_path, "w", encoding="utf-8") as cp_file:
                                            json.dump(checkpoint_payload, cp_file, ensure_ascii=False)
                                    except Exception:
                                        pass

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
                                        pass
                            except Exception as e:
                                pbar.write(f" 🔴 [Błąd Paczki]: {format_friendly_api_error(e)}")
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
                                    pass
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
                                    pass
                        except Exception as e:
                            pbar.write(f" 🔴 [Błąd Paczki]: {format_friendly_api_error(e)}")
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
                                pass
                    except Exception as h_err:
                        pbar.write(f"  [Zero-Gap Guard]: Błąd paczki uzupełniającej ({h_err}). Próba ratunkowa linijka po linijce...")
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
                pbar.write(f"\n  🚨 [ALARM ZERO-GAP]: Nie udało się przetłumaczyć {len(missing_final)} kwestii dialogowych!")
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

            # Professional AVT Anti-Clutter: Drop isolated paralinguistic grunts ("Och!", "Uch!", "Uh!", "Hmph!")
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
                            pass

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
            if not getattr(new_event, "name", None) or not str(new_event.name).strip() or is_generic_actor_or_category(str(new_event.name)):
                spk = translated_speakers.get(master_id)
                if spk and not is_generic_actor_or_category(spk):
                    new_event.name = spk
                else:
                    new_event.name = ""
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
                    print(f"\n  ⚠️ [ALARM EPISODE QUALITY GATE]: Wykryto {len(en_warnings)} nieprzetłumaczonych kwestii angielskich:")
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
                        logger.warning(f"[SeriesBible]: Błąd asymilacji niezmienników ({e_sb})")
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
                    pass
        except Exception:
            pass

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
            pass

        return output_path

# Alias for backwards compatibility
TranslatorEngine = MultimodalTranslator
