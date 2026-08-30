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
import tempfile
import sqlite3
from typing import List, Optional, Dict, Any, Tuple
from pathlib import Path
from PIL import Image
from pydantic import BaseModel, Field
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
from profiler import EpisodeProfiler, EpisodeProfile, format_episode_profile_for_prompt
from whisper_engine import JapaneseWhisperEngine
from avt_linter import AVTLinter
from romaji_helper import to_romaji
from series_memory import SeriesBible
from manga_canon import MangaCanonRegistry
from avt_formatter import (
    split_subtitle_syntactically,
    calculate_cps,
    calculate_condensation_directive,
    snap_subtitles_to_shot_cuts,
    format_diegetic_sound_wall,
    clean_text_for_len
)
from prosody_engine import AudioProsodyEngine
from speaker_diarizer import SpeakerVoiceClassifier
from typesetting_matcher import TypesettingColorMatcher
from user_feedback import UserFeedbackManager
from glossary_manager import GlossaryManager
from client_factory import format_friendly_api_error

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

def detect_event_visual_type(event: pysubs2.SSAEvent, ts_prefix: str) -> Dict[str, Any]:
    """
    Analyzes ASS tags, position, rotation, color, and style to distinguish
    on-screen text (manga titles, signs, posters, boards) from standard spoken dialogue (including top dialogue).
    """
    is_sign = False
    is_top = False
    details = []

    style_lower = (event.style or "").lower()
    name_lower = (event.name or "").lower()
    ts_lower = (ts_prefix or "").lower()

    if any(s in style_lower for s in ["sign", "title", "poster", "board", "screen", "typesetting", "card", "ts", "napis", "tytuł", "szyld"]):
        is_sign = True
        details.append(f"styl='{event.style}'")

    if any(n in name_lower for n in ["sign", "title", "poster", "board", "typesetting", "screen", "napis"]):
        is_sign = True
        details.append(f"aktor='{event.name}'")

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

def detect_audio_discrepancy(jp_text: str, pl_text: str, en_text: str) -> Optional[str]:
    """
    Automated discrepancy detector comparing Japanese voice recognition (Whisper)
    against Phase 1 draft translation.
    """
    if not jp_text or not pl_text:
        return None

    jp_lower = jp_text.lower()
    pl_lower = pl_text.lower()

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
                return "W audio pada rówieśniczy sufiks '-kun' / '-chan' -> Kategoryczny zakaz dodawania 'Pan/Pani' do imienia; stosuj samo imię na 'ty' w wołaczu (Filar XLVI / C)."
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
            return "W audio pada 'Sumimasen' jako dług wdzięczności (Giri) -> Zamień monotonne 'Przepraszam' na 'Wybacz kłopot...' / 'Nie trzeba było...' (Filar CX)."

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
        
    # 4. Youth / Casual Slang (-ssu, -yatsu, -chatt, -tteba)
    if any(k in clean_jp for k in ["っす", "やつ", "ちゃった", "ってば"]) or any(k in rom_lower for k in ["-ssu", " ssu", "yatsu", "chatta", "tteba"]):
        return "Młodzieżowy / Swobodny (luźny styl potoczny, dynamiczne skróty)"
        
    # 5. Romantic Intimate / Kokuhaku (daisuki, aishiteru, zutto issho)
    if any(k in clean_jp for k in ["大好き", "愛してる", "ずっと一緒"]) or any(k in rom_lower for k in ["daisuki", "aishiteru", "zutto issho"]):
        return "Czuły miłosny / Kokuhaku (wyznanie miłosne 'Kocham cię', eliminacja friendzone)"
        
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
        return text
        
    ts_prefix, clean_body = extract_typesetting_tags(text)
    # Strip leading dash on single-speaker line
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

def create_adaptive_batches(raw_entries: list, base_batch_size: int = 24, max_batch_size: int = 32) -> list:
    """
    Groups subtitle events into coherent, scene-aligned batches of 24-32 lines,
    adapting to dialogue density and scene pauses (> 4.0s gap starts a new batch).
    """
    if not raw_entries:
        return []

    batches = []
    current_batch = []
    current_words = 0

    for item in raw_entries:
        ev = item[1]
        text_clean = clean_text_for_len(item[2])
        words = len(text_clean.split())

        is_full = len(current_batch) >= max_batch_size
        is_dense = len(current_batch) >= base_batch_size and current_words >= 140
        is_scene_break = current_batch and (ev.start - current_batch[-1][1].end) > 4000 and len(current_batch) >= 18

        if is_full or is_dense or is_scene_break:
            batches.append(current_batch)
            current_batch = []
            current_words = 0

        current_batch.append(item)
        current_words += max(1, words)

    if current_batch:
        batches.append(current_batch)

    return batches

class CharacterInfo(BaseModel):
    name: str = Field(description="Imię lub określenie postaci (np. 'Arata', 'Minami', 'Nauczyciel')")
    gender: str = Field(description="Płeć postaci: 'mężczyzna', 'kobieta' lub 'inna'")
    role: Optional[str] = Field(default=None, description="Krótka rola lub relacja, np. 'główny bohater', 'koleżanka z klasy'")

class LineTranslation(BaseModel):
    id: int = Field(description="ID kwestii dialogowej z wejścia")
    polish_text: str = Field(description="Przetłumaczona kwestia na język polski z uwzględnieniem płci, sceny i eliminacji kalek")
    speaker_gender: Optional[str] = Field(default=None, description="Płeć mówcy: 'mężczyzna' lub 'kobieta'")
    visual_subtext: Optional[str] = Field(default=None, description="Maks. 6 słów o mimice, gestach lub hierarchii przestrzennej (np. 'klęczy przed chanem', 'uśmiech, zaciśnięta pięść') lub null")
    literal_meaning: Optional[str] = Field(default=None, description="Dosłowny idiom JP (maks. 5 słów) tylko w razie potrzeby, inaczej null")
    notes: Optional[str] = Field(default=None, description="Kluczowa notatka (maks. 5 słów) tylko w razie potrzeby, inaczej null")

class BatchTranslationResponse(BaseModel):
    scene_diagnosis: Optional[SceneDiagnosis] = Field(default=None, description="Syntetyczna diagnoza sytuacji i podtekstu sceny PRZED tłumaczeniem (1-2 zwięzłe zdania)")
    translations: List[LineTranslation] = Field(description="Lista przetłumaczonych kwestii")
    characters_identified: Optional[List[CharacterInfo]] = Field(default=None, description="Zidentyfikowane lub nowo odkryte postacie i ich płeć")

class MultimodalTranslator:
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
        
        timeout_sec = float(os.getenv("GEMINI_HTTP_TIMEOUT_SEC", "45.0"))
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
        self.system_prompt = get_translation_system_prompt(keep_honorifics=keep_honorifics)
        
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

    def _prepare_batch_prompt(
        self,
        batch_events: List[Tuple[int, pysubs2.SSAEvent, str, str]],
        history_context: List[Dict[str, str]],
        lookahead_events: List[Tuple[int, pysubs2.SSAEvent, str, str]] = None,
        anime_context_str: str = "",
        episode_profile_str: str = "",
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

        # 0c. Translation Memory golden examples
        if self.tm:
            try:
                batch_queries = [item[2] for item in batch_events]
                tm_examples = self.tm.find_relevant_examples(batch_queries, max_examples=4)
                if tm_examples:
                    lines.append(format_translation_memory_for_prompt(tm_examples))
            except Exception:
                pass

        # 1. Character Registry
        if self.character_registry:
            lines.append("--- ZNANE POSTACIE W TYM FILMIE (dla zachowania spójności płci i imion) ---")
            for name, details in self.character_registry.items():
                lines.append(f"• {name}: {details}")
            lines.append("--------------------------------------------------------------------------\n")

        # 2. Previous dialogue history
        if history_context:
            lines.append("--- POPRZEDNIE KWESTIE W SCENIE (kontekst przeszły) ---")
            for h in history_context[-4:]:
                lines.append(f"[Poprzednio] EN: {h['en']} -> PL: {h['pl']}")
            lines.append("-------------------------------------------------------\n")

        # 3. Lines to translate
        lines.append("Przetłumacz poniższe kwestie dialogowe na naturalny język polski. "
                     "PAMIĘTAJ: Kwestie często tworzą jedno długie zdanie rozbite na kilka linijek – ZAWSZE analizuj CAŁE ZDANIA od początku do końca, dbając o piękny, naturalny polski szyk wyrazów i płynność gramatyczną między linijkami! "
                     "DIALOGI 1-NA-1 I LICZBA GRAMATYCZNA: Gdy w scenie/kadrze rozmawiają ze sobą dwie postacie (1-na-1), angielskie dwuznaczne 'you' (np. 'Did you hear...?', 'Did you see...?', 'Do you know...?') BEZWZGLĘDNIE tłumacz w 2. osobie liczby POJEDYNCZEJ ('Słyszałeś?' / 'Słyszałaś?', 'Widziałeś?', 'Wiesz?'). KATEGORYCZNY ZAKAZ form liczby mnogiej ('Słyszeliście?') w rozmowach dwuosobowych! "
                     "ŻEŃSKOOSOBOWOŚĆ OBSADY: Dialogi między uczennicami/dziewczętami bezwzględnie tłumacz w RODZAJU ŻEŃSKIM (np. 'Głupia jesteś?' / 'Oszalałaś?', 'Jesteś pewna?', 'Widziałaś to?', 'poszłam', 'zrobiłam'). ZAKAZ form męskich ('Głupi jesteś?') w rozmowach dziewcząt! "
                     "PRZYNALEŻNOŚĆ I 3. OSOBA: Frazy typu '[Imię]'s dad / mom / manga' (np. 'Akafuku's dad!') tłumacz w 3. osobie ('Tata Akafuku!'). BEZWZGLĘDNY ZAKAZ zamiany imienia innej postaci na 1. osobę ('to mój tata' -> BŁĄD!). "
                     "Użyj załączonych klatek wideo do WIZUALNEGO ODCZYTANIA (OCR) JAPOŃSKICH NAPISÓW (chmurki jak いいよね, tablice, telefony, szyldy) oraz japońskiego audio do ustalenia emocji i kontekstu sytuacji. "
                     "Jeśli podano japońską transkrypcję (JP), opieraj sens bezpośrednio na japońskim oryginale! "
                     "BEZWZGLĘDNIE unikaj tłumaczenia 1:1, kalek i sztywnych definicji (np. 'That bombed' -> 'To mi nie wyszło', 'I'm home' -> 'Wróciłam!', 'I see' -> 'Rozumiem'):")

        for idx, (original_idx, event, clean_text, ts_prefix) in enumerate(batch_events):
            start_str = pysubs2.time.ms_to_str(event.start)
            end_str = pysubs2.time.ms_to_str(event.end)
            vtype = detect_event_visual_type(event, ts_prefix)
            duration_s = max(0.2, (event.end - event.start) / 1000.0)
            cps, is_fast = calculate_cps(clean_text, event.start, event.end)

            acoustic_cues = []
            if speaker_tags and (idx + 1) in speaker_tags:
                acoustic_cues.append(f"Głos: {speaker_tags[idx + 1]}")
            if prosody_tags and (idx + 1) in prosody_tags:
                acoustic_cues.append(f"Ton: {prosody_tags[idx + 1]}")
            acoustic_str = f" [{', '.join(acoustic_cues)}]" if acoustic_cues else ""

            # Dynamic cause-and-effect relationship detection with preceding line
            relation_tag = ""
            if idx > 0 and not vtype["is_sign"]:
                prev_clean = batch_events[idx - 1][2].strip()
                if prev_clean.endswith("?"):
                    relation_tag = " [RELACJA: Prawdopodobna odpowiedź/reakcja na pytanie]"
                elif any(prev_clean.lower().startswith(w) for w in ["come,", "let's", "shall we", "look,", "hey,"]):
                    relation_tag = " [RELACJA: Prawdopodobna reakcja / zgoda / odmowa na zaproszenie/propozycję]"
                elif prev_clean.endswith("...") or prev_clean.endswith("…"):
                    relation_tag = " [RELACJA: Prawdopodobna kontynuacja myśli rozbitej wielokropkiem]"

            if vtype["is_sign"]:
                lines.append(f"Kwestia [ID: {idx + 1}] [TYP: [NAPIS] {vtype['type_label']}] (Czas: {start_str} - {end_str}, Cechy: {vtype['visual_details']}):")
                lines.append(f"  (!) UWAGA WIZUALNA: To jest NAPIS / TYTUŁ NA EKRANIE (np. tytuł mangi, rozdział, tablica, napis wklejony w kadr).")
                lines.append(f"  Przetłumacz ten tekst jako SAMODZIELNY TYTUŁ/NAPIS (np. 'The Princess's Favor' / '姫様のご寵愛' -> 'Łaska księżniczki' / 'Faworyta księżniczki').")
                lines.append(f"  BEZWZGLĘDNY ZAKAZ wklejania tu fragmentów dialogów mówionych przez postacie!")
            else:
                speaker_name = event.name if event.name else "Postać"
                lines.append(f"Kwestia [ID: {idx + 1}] [TYP: [DIALOG] {vtype['type_label']}]{relation_tag} (Czas: {start_str} - {end_str}, Mówca: '{speaker_name}'){acoustic_str}:")
                if vtype.get("is_top"):
                    lines.append(f"  (!) DIALOG GÓRNY / W TLE: To jest dialog postaci w tle/oddali. Formatuj jako naturalny dialog mówiony (Sentence case). BEZWZGLĘDNY ZAKAZ nawiasów kwadratowych [...] i ZAKAZ wielkich liter ALL-CAPS!")
                if is_fast:
                    lines.append(f"  (!) TEMPO CPS ({cps:.1f} z/s, czas {duration_s:.1f}s): Szybka kwestia! Zastosuj zwięzłą kondensację Belczyka.")

            if whisper_transcriptions and idx + 1 in whisper_transcriptions:
                jp_text = whisper_transcriptions[idx + 1]
                if jp_text and not vtype["is_sign"]:
                    romaji_str = to_romaji(jp_text)
                    jp_display = f"{jp_text} [{romaji_str}]" if romaji_str and romaji_str != jp_text else jp_text
                    lines.append(f"  JP (GŁÓWNA KOTWICA SEMANTYCZNA - Słuchaj intencji aktora): {jp_display}")
            lines.append(f"  EN (Pomocniczy skrypt do czasu/ogólnego sensu): {clean_text}")

        # 4. Lookahead window
        if lookahead_events:
            lines.append("\n--- PODGLĄD NASTĘPNYCH KWESTII (NIE TŁUMACZ ICH! Użyj tylko do zrozumienia kontekstu i płci) ---")
            for _, _, future_text, _ in lookahead_events[:4]:
                lines.append(f"[Wkrótce] EN: {future_text}")
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
                # Phase 1: Always enforce thinking_budget=0 (CoT=0) for reasoning-capable models (Flash 3.7+, 3.8+, 4.0+, Pro)
                # ensuring rapid triangulation with zero thinking token cost.
                is_reasoning_capable = any(k in current_model.lower() for k in ["3.7", "3.8", "4.", "pro", "thinking", "reasoning"]) and "lite" not in current_model.lower()
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
                        system_instruction=self.system_prompt
                    )
                    cfg_kwargs = dict(gen_config_kwargs)
                    if cached_name:
                        cfg_kwargs["cached_content"] = cached_name
                    else:
                        cfg_kwargs["system_instruction"] = self.system_prompt
                    cfg = types.GenerateContentConfig(**cfg_kwargs)
                    return active_c.models.generate_content(
                        model=current_model,
                        contents=contents,
                        config=cfg
                    )

                # Direct generation using thread-safe client pool and token bucket limiter
                response = _single_generate()

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
                    if attempt > 1:
                        print(f"  └─ [OK / Faza 1]: Połączenie z Google API przywrócone (próba #{attempt}).")
                    return response.parsed
                else:
                    res = schema_class.model_validate(json.loads(response.text))
                    if attempt > 1:
                        print(f"  └─ [OK / Faza 1]: Połączenie z Google API przywrócone (próba #{attempt}).")
                    return res

            except Exception as e:
                err_str = str(e).lower()
                if hasattr(self, "client_pool") and self.client_pool and last_used_client:
                    self.client_pool.report_error(last_used_client, err_str)

                is_cache_err = "403" in err_str or "cachedcontent" in err_str or "permission" in err_str
                if is_cache_err and cached_name:
                    from context_cache import ContextCacheManager
                    ContextCacheManager.invalidate_cache(current_model, self.system_prompt)
                    cached_name = None
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

                is_timeout = "504" in err_str or "deadline" in err_str or "timeout" in err_str or "timed out" in err_str
                is_unavailable = "503" in err_str or "unavailable" in err_str or "high demand" in err_str
                is_rate_limit = "429" in err_str or "quota" in err_str or "resource_exhausted" in err_str or "rate" in err_str

                import random
                num_keys = len(self.client_pool.clients) if hasattr(self, "client_pool") and self.client_pool else 1
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
                if attempt == 1:
                    print(f"\n[Tłumacz / Faza 1]: {friendly_msg} -> oczekiwanie i automatyczna rotacja kluczy API...")
                elif attempt % max(1, num_keys * 3) == 0:
                    print(f"  ├─ [Status / Faza 1]: {friendly_msg} (próba #{attempt}, ponawianie w tle)...")
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
        pbar: Any
    ) -> Tuple[int, Dict[int, str], List[Any], List[Dict[str, Any]], str]:
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

        # 2. Extract 3-4 intelligent key video frames for the batch (Storyboard & Visual OCR)
        temp_frames: List[str] = []
        image_contents = []

        if video_path and os.path.exists(video_path):
            raw_timestamps: List[int] = []
            
            # 1. Start line
            raw_timestamps.append((untranslated_in_batch[0][1].start + untranslated_in_batch[0][1].end) // 2)

            # 2. Priority: Signs and On-screen captions for OCR
            for _, ev, clean_txt, ts_pref in untranslated_in_batch:
                vtype = detect_event_visual_type(ev, ts_pref)
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
        focused_rules_str = get_focused_rules_for_batch([
            {
                "en": item[2],
                "is_sign": detect_event_visual_type(item[1], item[3])["is_sign"],
                "speaker_gender": self.character_registry.get(item[1].name)
            }
            for item in untranslated_in_batch
        ])

        # 3b. Text prompt with AniList knowledge, character registry, lookahead, and phonetic cues
        prompt_text = self._prepare_batch_prompt(
            untranslated_in_batch,
            history,
            lookahead_events=lookahead_events,
            anime_context_str=anime_context_str,
            episode_profile_str=episode_profile_str,
            whisper_transcriptions=whisper_transcriptions,
            series_bible_str=series_bible_str,
            prosody_tags=prosody_tags,
            speaker_tags=speaker_tags,
            manga_canon_str=manga_canon_str,
            user_feedback_str=user_feedback_str,
            glossary_str=glossary_str,
            focused_rules_str=focused_rules_str
        )

        # 4. Call Gemini (Vision + Whisper text context)
        if whisper_transcriptions:
            jp_raw_list = [v for v in whisper_transcriptions.values() if v]
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

        # Update global Character Registry with thread lock
        with self.lock:
            if batch_response and batch_response.characters_identified:
                for char in batch_response.characters_identified:
                    if char.name:
                        desc = f"{char.gender} ({char.role or 'postać'})"
                        self.character_registry[char.name] = desc
        scene_desc = ""
        if batch_response:
            if getattr(batch_response, "scene_diagnosis", None) and batch_response.scene_diagnosis:
                scene_desc = getattr(batch_response.scene_diagnosis, "dramatic_context", "") or ""
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
            vtype = detect_event_visual_type(event, ts_prefix)
            cps, is_fast = calculate_cps(clean_en, event.start, event.end)
            cps_warn = f"Tempo CPS: {cps:.1f} (czas {(event.end - event.start)/1000.0:.1f}s)" if is_fast else ""
            condensation_dir = calculate_condensation_directive(clean_en, event.start, event.end)

            visual_sub = ""
            lit_mean = ""
            if batch_response:
                for tr in batch_response.translations:
                    if tr.id == batch_id:
                        pl_candidate = sanitize_sub_text(tr.polish_text)
                        speaker_gender = tr.speaker_gender
                        visual_sub = getattr(tr, 'visual_subtext', '') or ''
                        lit_mean = getattr(tr, 'literal_meaning', '') or ''
                        notes = f"{getattr(tr, 'visual_clues', '') or ''} {getattr(tr, 'notes', '') or ''}".strip()
                        break

            if not pl_candidate:
                pl_candidate = clean_en

            jp_text = whisper_transcriptions.get(batch_id, "") if whisper_transcriptions else ""
            romaji_str = to_romaji(jp_text) if jp_text else ""
            audio_jp_str = f"{jp_text} [{romaji_str}]" if romaji_str and romaji_str != jp_text else jp_text

            audio_discrepancy_msg = detect_audio_discrepancy(audio_jp_str, pl_candidate, clean_en)
            pragmatic_reg = detect_japanese_pragmatic_register(audio_jp_str, clean_en)

            pass1_items.append({
                "id": batch_id,
                "orig_idx": orig_idx,
                "en": clean_en,
                "pl": pl_candidate,
                "speaker_gender": speaker_gender,
                "speaker_voice": speaker_tags.get(batch_id, ""),
                "prosody": prosody_tags.get(batch_id, ""),
                "audio_jp": audio_jp_str,
                "audio_alert": audio_discrepancy_msg or "",
                "pragmatic_register": pragmatic_reg or "",
                "visual_subtext": visual_sub or "",
                "literal_meaning": lit_mean or "",
                "cps_warning": cps_warn,
                "condensation_directive": condensation_dir or "",
                "notes": notes,
                "is_sign": vtype["is_sign"],
                "visual_type": vtype["type_label"],
                "visual_details": vtype["visual_details"],
                "is_song": is_song_line(event, clean_en)
            })

        # 6. Optional Phase 2 Verifier (Script Doctor)
        batch_results: Dict[int, str] = {}

        if self.enable_verifier and hasattr(self, 'verifier'):
            pbar.set_postfix_str("Faza 2 (Redakcja Dialogów Pro)...")
            # Staggered entry (350ms per thread) to prevent simultaneous TPU burst collisions on 503
            stagger_sec = (b_idx % max(1, self.concurrent_batches)) * 0.35
            if stagger_sec > 0:
                time.sleep(stagger_sec)
            refined_lines: List[RefinedLine] = self.verifier.verify_batch(
                batch_items=pass1_items,
                scene_summary=scene_desc or "",
                episode_profile_str=episode_profile_str,
                user_feedback_str=user_feedback_str,
                glossary_str=glossary_str,
                focused_rules_str=focused_rules_str
            )
            refined_dict = {r.id: sanitize_sub_text(r.refined_pl) for r in refined_lines}
            for r in refined_lines:
                orig_item = next((it for it in pass1_items if it["id"] == r.id), None)
                orig_pl = orig_item["pl"] if orig_item else ""
                clean_ref = sanitize_sub_text(r.refined_pl)
                ch_desc = (getattr(r, 'changes_made', '') or '').strip()
                
                # Check if there is an actual textual modification or meaningful redaction note
                has_text_change = orig_pl and (orig_pl.strip() != clean_ref.strip())
                has_meaningful_note = bool(ch_desc and "Zweryfikowano" not in ch_desc and ch_desc.lower() != "null")
                
                if has_text_change or has_meaningful_note:
                    clean_note = ch_desc if ch_desc.startswith("[") else (f"[{ch_desc}]" if ch_desc else "")
                    pillar_note = f" {clean_note}" if clean_note else ""
                    
                    # Strip internal ASS tags (like {\i1}, {\i0}) for pure, clean console display
                    disp_orig = re.sub(r"\{[^\}]*\}", "", orig_pl).strip()
                    disp_ref = re.sub(r"\{[^\}]*\}", "", clean_ref).strip()
                    
                    pbar.write(f" └─ [Redaktor Dialogów] #{r.id}{pillar_note}")
                    pbar.write(f"    ├─ Szkic:  \"{disp_orig}\"")
                    pbar.write(f"    └─ Szlif:  \"{disp_ref}\"")
            for item in pass1_items:
                raw_final = sanitize_sub_text(refined_dict.get(item["id"], item["pl"]))
                final_text, fixes = AVTLinter.lint_and_fix_line(
                    text=raw_final,
                    speaker_gender=item.get("speaker_gender"),
                    is_all_girls_scene=True,
                    is_sign=item.get("is_sign", False),
                    user_feedback_rules=all_user_rules,
                    custom_glossary=combined_glossary
                )
                # Deterministic glossary overrides
                final_text, gloss_fixes = GlossaryManager.apply_deterministic_overrides(final_text, combined_glossary)
                if item.get("is_song") and not item.get("is_sign"):
                    clean_no_notes = re.sub(r"^[♪♫♬\s]+|[♪♫♬\s]+$", "", final_text).strip()
                    if clean_no_notes:
                        final_text = f"♪ {clean_no_notes} ♪"
                for fix in fixes + gloss_fixes:
                    pbar.write(f"  [AVT Linter/Słownik] {fix}")
                formatted_final = split_subtitle_syntactically(final_text, max_line_len=42, is_ass=is_ass, is_sign=item.get("is_sign", False))
                batch_results[item["orig_idx"]] = formatted_final
        else:
            for item in pass1_items:
                raw_final = sanitize_sub_text(item["pl"])
                final_text, fixes = AVTLinter.lint_and_fix_line(
                    text=raw_final,
                    speaker_gender=item.get("speaker_gender"),
                    is_all_girls_scene=True,
                    is_sign=item.get("is_sign", False),
                    user_feedback_rules=all_user_rules,
                    custom_glossary=combined_glossary
                )
                # Deterministic glossary overrides
                final_text, gloss_fixes = GlossaryManager.apply_deterministic_overrides(final_text, combined_glossary)
                if item.get("is_song") and not item.get("is_sign"):
                    clean_no_notes = re.sub(r"^[♪♫♬\s]+|[♪♫♬\s]+$", "", final_text).strip()
                    if clean_no_notes:
                        final_text = f"♪ {clean_no_notes} ♪"
                for fix in fixes + gloss_fixes:
                    pbar.write(f"  [AVT Linter/Słownik] {fix}")
                formatted_final = split_subtitle_syntactically(final_text, max_line_len=42, is_ass=is_ass, is_sign=item.get("is_sign", False))
                batch_results[item["orig_idx"]] = formatted_final

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

        return b_idx, batch_results, untranslated_in_batch, pass1_items, scene_desc

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

        try:
            subs = pysubs2.load(str(subs_file), encoding="utf-8")
        except UnicodeDecodeError:
            subs = pysubs2.load(str(subs_file), encoding="latin2")

        # 0. Retrieve anime metadata from AniList
        ref_filename = video_path if video_path else subs_path
        anime_meta = get_anime_context(ref_filename)
        anime_context_str = ""
        
        if anime_meta:
            anime_context_str = format_anime_context_for_prompt(anime_meta)
            title_name = anime_meta.get("title_romaji") or anime_meta.get("title_english") or "Seria"
            char_count = len(anime_meta.get("characters", []))
            print(f"\n[Baza AniList] Rozpoznano serię: '{title_name}'")
            if anime_meta.get("genres"):
                print(f"[Baza AniList] Gatunki: {', '.join(anime_meta['genres'])}")
            if anime_meta.get("setting_tags"):
                print(f"[Baza AniList] [Realia świata / Epoka]: {', '.join(anime_meta['setting_tags'])}")
            if anime_meta.get("detected_domains"):
                print(f"[Baza AniList] [Dziedzina specjalistyczna]: {', '.join(anime_meta['detected_domains'])}")
            print(f"[Baza AniList] Wczytano opis fabuły oraz {char_count} postaci z ich płcią i rolami.")
            
            # Pre-populate character registry from AniList
            for c in anime_meta.get("characters", []):
                self.character_registry[c["name"]] = f"{c['gender']} ({c['role']})"

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
        if restored_f2_tokens and isinstance(restored_f2_tokens, dict) and self.verifier:
            for k in ["prompt", "cached", "output"]:
                self.verifier.current_episode_tokens[k] = self.verifier.current_episode_tokens.get(k, 0) + restored_f2_tokens.get(k, 0)

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
        episode_profile_str = format_episode_profile_for_prompt(episode_profile)

        # 0b. Initialize and load Series Bible (Cross-Episode Continuity)
        series_title = ""
        if anime_meta:
            series_title = anime_meta.get("title_romaji") or anime_meta.get("title_english") or ""
        if not series_title:
            ref_path = video_path or subs_path or ""
            if ref_path:
                series_title = Path(ref_path).stem.split(" - ")[0].replace("[ASW]", "").replace("[Erai-raws]", "").strip()
        self.series_bible = SeriesBible(anime_title=series_title)
        if episode_profile:
            char_dict = {}
            for c in episode_profile.characters:
                char_key = f"{c.speaker} -> {c.listener}" if c.listener else c.speaker
                char_dict[char_key] = f"Zwrot: '{c.address_form}' ({c.relationship_type})"
            gloss_dict = {g.term_en: g.translation_pl for g in episode_profile.glossary}
            ref_name = Path(video_path).stem if video_path else (Path(subs_path).stem if subs_path else "Odcinek")
            self.series_bible.update_from_episode_profile(
                episode_name=ref_name,
                characters=char_dict,
                glossary=gloss_dict
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

        # 0d. Combined User, Manga Canon and Series Bible Glossary (Deterministic)
        series_gloss_dict = self.series_bible.data.get("glossary", {}) if hasattr(self, "series_bible") and self.series_bible else {}
        if manga_canon_entry and manga_canon_entry.get("glossary"):
            series_gloss_dict.update(manga_canon_entry["glossary"])
        combined_glossary = self.glossary_manager.get_combined_glossary(series_gloss_dict)
        if manga_canon_entry and manga_canon_entry.get("glossary"):
            combined_glossary.update(manga_canon_entry["glossary"])
        if combined_glossary:
            print(f"  [Słownik Deterministyczny]: Aktywnych {len(combined_glossary)} żelaznych terminów (w tym 100% Kanonu Mangowego).")

        user_rules_cnt = len(self.user_feedback.list_all())
        user_feedback_str = self.user_feedback.format_for_prompt()
        if user_rules_cnt > 0:
            print(f"  [Korekty Użytkownika]: Wczytano {user_rules_cnt} złotych reguł (Few-Shot Prompting).")

        # 0e. Format static episode strings
        glossary_str = self.glossary_manager.format_for_prompt(combined_glossary)
        manga_canon_str = f"\nOFICJALNY KANON MANGOWY ({manga_canon_entry['publisher']}):\n" + "\n".join([f"- '{k}' = '{v}'" for k, v in manga_canon_entry.get('glossary', {}).items()]) if manga_canon_entry else ""
        episode_profile_str = format_episode_profile_for_prompt(episode_profile) if episode_profile else ""

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

        # Pre-warming and Context Cache Hard Protection across all client pool keys (guarantees -90% discount)
        from context_cache import ContextCacheManager
        print(f"  [Infrastruktura Finansowa]: Weryfikacja i rozgrzewanie pamięci Context Cache z pełną wiedzą odcinka...")
        pool_or_c1 = self.client_pool if hasattr(self, "client_pool") and self.client_pool else self.client
        c1 = ContextCacheManager.ensure_cache_ready(pool_or_c1, self.model_phase1, self.system_prompt)
        if not c1:
            raise RuntimeError(
                f"KATEGORYCZNA BLOKADA FINANSOWA: Nie udało się aktywować serwerowego Context Cache dla {self.model_phase1}. "
                "Aby uchronić Twój portfel przed naliczeniem 10-krotnie wyższej stawki pełnej, proces został bezpiecznie wstrzymany. "
                "Sprawdź połączenie z Google API lub stan konta i spróbuj ponownie."
            )
        if self.verifier and hasattr(self.verifier, "model") and hasattr(self.verifier, "system_prompt"):
            pool_or_c2 = getattr(self.verifier, "client_pool", None) or getattr(self.verifier, "client", None)
            c2 = ContextCacheManager.ensure_cache_ready(pool_or_c2, self.verifier.model, self.verifier.system_prompt)
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
                ContextCacheManager.get_or_create_cache(client=c, model=self.model_phase1, system_instruction=self.system_prompt)
                if self.enable_verifier and self.verifier:
                    ContextCacheManager.get_or_create_cache(client=c, model=self.verifier.model, system_instruction=self.verifier.system_prompt)
        except Exception:
            pass

        batches = create_adaptive_batches(
            raw_entries,
            base_batch_size=self.batch_size,
            max_batch_size=min(32, self.batch_size + 8)
        )

        with tqdm(total=total_lines, desc="Tłumaczenie dialogów", unit="linii") as pbar:
            pbar.start_t = time.time()
            already_done = sum(1 for item in raw_entries if item[0] in translated_results)
            if already_done > 0:
                pbar.update(already_done)

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
                                pbar=pbar
                            ): b_idx
                            for b_idx, batch, untranslated in tasks_to_run
                        }

                        for future in concurrent.futures.as_completed(future_to_bidx):
                            if cancel_check and cancel_check():
                                print("\n[Tłumacz]: Otrzymano sygnał przerwania (⏹ Stop)...")
                                break
                            try:
                                b_res_idx, batch_res, untrans_items, pass1_items, sc_desc = future.result()
                                with self.lock:
                                    for orig_idx, text_res in batch_res.items():
                                        translated_results[orig_idx] = text_res
                                    # Save checkpoint safely
                                    try:
                                        checkpoint_payload = {
                                            "translated_results": translated_results,
                                            "token_usage": {
                                                "f1": self.current_episode_tokens,
                                                "f2": self.verifier.current_episode_tokens if self.verifier else None
                                            }
                                        }
                                        with open(checkpoint_path, "w", encoding="utf-8") as cp_file:
                                            json.dump(checkpoint_payload, cp_file, ensure_ascii=False)
                                    except Exception:
                                        pass

                                pbar.update(len(untrans_items))

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
                else:
                    print(f"\n  [Kolejka Paczek]: Płynne tłumaczenie sekwencyjne (1 paczka na raz / rotacja {active_keys_count} aktywnych kluczy API)...")
                    for loop_i, (b_idx, batch, untranslated) in enumerate(tasks_to_run):
                        if cancel_check and cancel_check():
                            print("\n[Tłumacz]: Otrzymano sygnał przerwania (⏹ Stop)...")
                            break
                        if loop_i > 0:
                            time.sleep(0.25)
                        try:
                            b_res_idx, batch_res, untrans_items, pass1_items, sc_desc = self._process_single_batch(
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
                                pbar=pbar
                            )
                            with self.lock:
                                for orig_idx, text_res in batch_res.items():
                                    translated_results[orig_idx] = text_res
                                try:
                                    checkpoint_payload = {
                                        "translated_results": translated_results,
                                        "token_usage": {
                                            "f1": self.current_episode_tokens,
                                            "f2": self.verifier.current_episode_tokens if self.verifier else None
                                        }
                                    }
                                    with open(checkpoint_path, "w", encoding="utf-8") as cp_file:
                                        json.dump(checkpoint_payload, cp_file, ensure_ascii=False)
                                except Exception:
                                    pass
                            pbar.update(len(untrans_items))

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

        # 7. Construct final subtitle file preserving styles, positioning, and typesetting
        final_subs = pysubs2.SSAFile()
        # Copy full stylesheet (fonts, colors, positions)
        final_subs.styles = subs.styles.copy()
        final_subs.info = subs.info.copy()
        # Force WrapStyle: 2 (no arbitrary line wrapping by video player)
        final_subs.info["WrapStyle"] = "2"

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
            is_sign_flag = detect_event_visual_type(orig_event, ts_prefix)["is_sign"]
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

            # Auto-elevate bracketed signs/captions '[ ... ]' to top (\an8) if missing positioning to prevent collision with bottom subs/hardsubs
            clean_check = clean_translated_text.strip()
            ts_prefix_applied = sanitize_ts_prefix_for_translation(ts_prefix or "")
            if (clean_check.startswith("[") and clean_check.endswith("]")) or "sign" in (orig_event.style or "").lower():
                if not (r"\an" in ts_prefix_applied or r"\pos" in ts_prefix_applied):
                    ts_prefix_applied = r"{\an8}" + ts_prefix_applied

            # Reattach Typesetting tags to translated text
            full_event_text = f"{ts_prefix_applied}{clean_translated_text}" if ts_prefix_applied else clean_translated_text

            new_event = orig_event.copy()
            new_event.text = full_event_text
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
                cuts = SceneShotSnapper.detect_scene_cuts_ffmpeg(video_path)
                if cuts:
                    final_subs.events, snapped_cnt = SceneShotSnapper.snap_subtitles_to_cuts(final_subs.events, cuts)
                    if snapped_cnt > 0:
                        logger.info(f"[SceneShotSnapper]: Dociągnięto {snapped_cnt} krawędzi napisów do cięć montażowych.")
            except Exception as e:
                logger.warning(f"SceneShotSnapper: Pomijanie ({e})")

        final_subs.events.sort(key=lambda ev: ev.start)

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
        
        # Remove checkpoint and temporary profile cache files upon successful completion
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

        print(f"\n[Sukces] Przetłumaczone, wyczyszczone napisy z zachowanym Typesettingiem zapisano w: {output_path}")

        # Calculate and display total real episode cost based on token usage
        try:
            from pricing_guard import PricingGuard
            f1_stats = self.current_episode_tokens
            f2_stats = self.verifier.current_episode_tokens if self.verifier else None
            actual_cost_pln = PricingGuard.calculate_actual_cost_pln(f1_stats, f2_stats)
            cost_f1_pln = PricingGuard.calculate_actual_cost_pln(f1_stats, None)
            cost_f2_pln = max(0.0, actual_cost_pln - cost_f1_pln) if f2_stats else 0.0
            
            cached_tok_total = f1_stats.get('cached', 0) + (f2_stats.get('cached', 0) if f2_stats else 0)
            cache_savings_pln = (cached_tok_total / 1_000_000) * (0.75 - 0.075) * 4.0

            print("\n" + "═" * 68)
            print(f"  💰 RZECZYWISTY KOSZT ODCINKA: {actual_cost_pln:.2f} PLN")
            print(f"  ├─ Faza 1 (Szkic & OCR Sparse): {cost_f1_pln:.2f} PLN")
            print(f"  │   └─ Wejście: {f1_stats.get('prompt',0):,} tok (Cached: {f1_stats.get('cached',0):,}) | Wyjście: {f1_stats.get('output',0):,} tok")
            if f2_stats:
                print(f"  └─ Faza 2 (Reżyseria & Elastic CoT): {cost_f2_pln:.2f} PLN")
                print(f"      └─ Wejście: {f2_stats.get('prompt',0):,} tok (Cached: {f2_stats.get('cached',0):,}) | Wyjście+CoT: {f2_stats.get('output',0):,} tok")
            print(f"  🛡️ Oszczędność Context Cache (-90% rabat): ~{cache_savings_pln:.2f} PLN")
            print("═" * 68 + "\n")
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
