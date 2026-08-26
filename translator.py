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
from avt_formatter import split_subtitle_syntactically, calculate_cps
from prosody_engine import AudioProsodyEngine
from speaker_diarizer import SpeakerVoiceClassifier
from typesetting_matcher import TypesettingColorMatcher
from user_feedback import UserFeedbackManager
from glossary_manager import GlossaryManager

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

def detect_event_visual_type(event: pysubs2.SSAEvent, ts_prefix: str) -> Dict[str, Any]:
    """
    Analyzes ASS tags, position, rotation, color, and style to distinguish
    on-screen text (manga titles, signs, posters, boards) from standard spoken dialogue.
    """
    is_sign = False
    details = []

    style_lower = (event.style or "").lower()
    name_lower = (event.name or "").lower()
    ts_lower = (ts_prefix or "").lower()

    if any(s in style_lower for s in ["sign", "title", "note", "top", "manga", "screen", "ts", "typesetting", "card"]):
        is_sign = True
        details.append(f"styl='{event.style}'")

    if any(n in name_lower for n in ["sign", "title", "note", "typesetting", "screen"]):
        is_sign = True
        details.append(f"aktor='{event.name}'")

    if r"\pos" in ts_lower:
        is_sign = True
        details.append("pozycjonowany na ekranie (\\pos)")

    if r"\frz" in ts_lower or r"\org" in ts_lower:
        is_sign = True
        details.append("obrócony/wklejony w perspektywę mangi (\\frz)")

    if any(an in ts_lower for an in [r"\an7", r"\an8", r"\an9", r"\an4", r"\an5", r"\an6"]):
        is_sign = True
        details.append("położenie poza dolnym marginesem (\\an)")

    if r"\c&h" in ts_lower or r"\1c&h" in ts_lower:
        is_sign = True
        details.append("indywidualny kolor graficzny")

    desc = ", ".join(details) if details else "standardowy dolny dialog"
    return {
        "is_sign": is_sign,
        "type_label": "NAPIS EKRANOWY / TYTUŁ (Sign/Typesetting)" if is_sign else "MÓWIONY DIALOG POSTACI",
        "visual_details": desc
    }

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

    # 4. Yobisute vs 'Pan / Pani'
    if ("panie " in pl_lower or "pani " in pl_lower) and not any(s in jp_text for s in ["様", "先生", "殿", "隊長"]):
        if not any(s in jp_lower for s in ["sama", "sensei", "dono", "taichou"]):
            return "W audio brak sufiksu szacunku (-sama/-sensei) -> Usuń sztuczne 'Pan/Pani' i zastosuj samo imię w wołaczu (Filar C)."

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
    style_name = (getattr(ev, "style", "") or "").lower()
    song_style_keywords = ["op", "ed", "song", "theme", "insert", "karaoke", "romaji", "kanji", "piosenka", "śpiew", "music"]
    if any(k in style_name for k in song_style_keywords):
        return True
    if any(sym in text for sym in ["♪", "♫", "🎶", "♬"]):
        return True
    return False

def apply_simultaneous_dialogue_formatting(events: List[Any]) -> List[Any]:
    """
    Simultaneous Dialogue Formatting (AVT Standard):
    When two characters speak simultaneously during an overlapping time window,
    adds dialogue dashes (- Line) to immediately distinguish parallel voices.
    """
    if len(events) < 2:
        return events

    # Chronological sort
    sorted_events = sorted(events, key=lambda e: e.start)
    n = len(sorted_events)
    simultaneous_indices = set()

    for i in range(n):
        ev_a = sorted_events[i]
        # Skip on-screen signs and song lines
        if (ev_a.style or "").lower() in ["sign", "signs", "title"] or "♪" in ev_a.text or r"\an8" in ev_a.text:
            continue
        for j in range(i + 1, n):
            ev_b = sorted_events[j]
            if (ev_b.style or "").lower() in ["sign", "signs", "title"] or "♪" in ev_b.text or r"\an8" in ev_b.text:
                continue
            if ev_b.start >= ev_a.end - 150:
                break  # subsequent lines are outside overlap window

            # Overlap in time by at least 300 ms
            overlap = min(ev_a.end, ev_b.end) - max(ev_a.start, ev_b.start)
            if overlap >= 300:
                simultaneous_indices.add(i)
                simultaneous_indices.add(j)

    for idx in simultaneous_indices:
        ev = sorted_events[idx]
        ts_prefix, clean_body = extract_typesetting_tags(ev.text)
        if not clean_body or clean_body.startswith(("-", "–", "—", "[", "(")):
            continue
        # Add AVT dialogue dash
        ev.text = f"{ts_prefix}- {clean_body}" if ts_prefix else f"- {clean_body}"

    return sorted_events

class CharacterInfo(BaseModel):
    name: str = Field(description="Imię lub określenie postaci (np. 'Arata', 'Minami', 'Nauczyciel')")
    gender: str = Field(description="Płeć postaci: 'mężczyzna', 'kobieta' lub 'inna'")
    role: Optional[str] = Field(default=None, description="Krótka rola lub relacja, np. 'główny bohater', 'koleżanka z klasy'")

class LineTranslation(BaseModel):
    id: int = Field(description="ID kwestii dialogowej z wejścia")
    polish_text: str = Field(description="Przetłumaczona kwestia na język polski z uwzględnieniem płci, sceny i eliminacji kalek")
    speaker_gender: Optional[str] = Field(default=None, description="Zidentyfikowana płeć postaci mówiącej (np. 'mężczyzna', 'kobieta')")
    visual_clues: Optional[str] = Field(default=None, description="Krótka notatka o kadrze")
    notes: Optional[str] = Field(default=None, description="Uwagi redakcyjne")

class BatchTranslationResponse(BaseModel):
    scene_diagnosis: Optional[SceneDiagnosis] = Field(default=None, description="Obowiązkowa diagnoza sytuacji, intencji i podtekstu sceny PRZED tłumaczeniem")
    translations: List[LineTranslation] = Field(description="Lista przetłumaczonych kwestii")
    scene_description: Optional[str] = Field(default=None, description="Krótki opis sceny na kadrze")
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
        
        timeout_ms = int(os.getenv("GEMINI_HTTP_TIMEOUT_MS", "120000"))
        self.client = genai.Client(api_key=self.api_key, http_options=types.HttpOptions(timeout=timeout_ms))
        self.model = model
        self.model_phase1 = model
        self.model_phase2 = model_phase2 or model
        self.batch_size = batch_size
        self.enable_verifier = enable_verifier
        self.max_image_width = max_image_width
        self.keep_honorifics = keep_honorifics
        self.thinking_budget_phase2 = thinking_budget_phase2
        self.system_prompt = get_translation_system_prompt(keep_honorifics=keep_honorifics)
        
        # Episode Profiler (Pre-pass Glossary & Character Matrix)
        self.profiler = EpisodeProfiler(client=self.client, model=self.model_phase1)
        
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
                client=self.client,
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

        # 00a. User Golden Examples and Feedback (Top Priority)
        if user_feedback_str:
            lines.append(user_feedback_str)

        # 00b. Deterministic Glossary Overrides
        if glossary_str:
            lines.append(glossary_str)

        # 00c. Focused Scene Rules (Eliminate Lost-in-the-Middle)
        if focused_rules_str:
            lines.append(focused_rules_str)

        # 0a. Official Polish Manga Canon
        if manga_canon_str:
            lines.append(manga_canon_str)

        # 0b. Series Bible cross-episode continuity
        if series_bible_str:
            lines.append(series_bible_str)

        # 0b. Episode profile glossary and relationships
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

        candidate_models = [self.model]
        if "flash" in self.model.lower():
            m1 = active_models.get("flash", "gemini-3.7-flash")
            m2 = active_models.get("flash_backup", "gemini-3.6-flash")
            candidate_models = [m1, m2] if m1 != m2 else [m1]
            if not hasattr(self, "phase1_rotation_idx"):
                self.phase1_rotation_idx = 0
            current_model_idx = self.phase1_rotation_idx % len(candidate_models)
            self.phase1_rotation_idx += 1
        elif "pro" in self.model.lower():
            m_pro = active_models.get("pro", "gemini-3.1-pro-preview")
            candidate_models = [m_pro]
            current_model_idx = 0
        else:
            current_model_idx = 0

        attempt = 0

        while True:
            attempt += 1
            current_model = candidate_models[current_model_idx]
            try:
                from context_cache import ContextCacheManager
                cached_name = ContextCacheManager.get_or_create_cache(
                    client=self.client,
                    model=current_model,
                    system_instruction=self.system_prompt
                )
                gen_config_kwargs = {
                    "response_mime_type": "application/json",
                    "response_schema": schema_class,
                    "temperature": 0.25,
                }
                if "3.7" in current_model.lower() or "3.1-pro" in current_model.lower() or "pro" in current_model.lower():
                    if self.enable_verifier:
                        gen_config_kwargs["thinking_config"] = types.ThinkingConfig(thinking_budget=0)
                    else:
                        gen_config_kwargs["thinking_config"] = types.ThinkingConfig(thinking_budget=1024)

                if cached_name:
                    gen_config_kwargs["cached_content"] = cached_name
                else:
                    gen_config_kwargs["system_instruction"] = self.system_prompt

                response = self.client.models.generate_content(
                    model=current_model,
                    contents=contents,
                    config=types.GenerateContentConfig(**gen_config_kwargs)
                )

                if hasattr(response, "usage_metadata") and response.usage_metadata:
                    um = response.usage_metadata
                    self.current_episode_tokens["prompt"] += getattr(um, "prompt_token_count", 0) or 0
                    self.current_episode_tokens["cached"] += getattr(um, "cached_content_token_count", 0) or 0
                    cands = getattr(um, "candidates_token_count", 0) or 0
                    thoughts = getattr(um, "thoughts_token_count", 0) or 0
                    self.current_episode_tokens["output"] += (cands + thoughts)
                    self.current_episode_tokens["model"] = current_model

                if hasattr(response, "parsed") and response.parsed is not None:
                    return response.parsed
                else:
                    return schema_class.model_validate(json.loads(response.text))

            except Exception as e:
                err_str = str(e).lower()
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
                
                # Instant switch between the two top Flash versions on 503, 504, or 429
                if (is_unavailable or is_timeout or is_rate_limit) and len(candidate_models) > 1:
                    next_idx = (current_model_idx + 1) % len(candidate_models)
                    if next_idx != current_model_idx:
                        print(f"\n[Tłumacz / Faza 1]: Przełączanie na alternatywny najwyższy model Flash: {candidate_models[next_idx]} (płynny load-balancing)...")
                        current_model_idx = next_idx
                        time.sleep(1)
                        continue

                if is_timeout:
                    wait_time = min(3 + attempt * 2, 15)
                    timeout_sec = int(os.getenv("GEMINI_HTTP_TIMEOUT_MS", "120000")) // 1000
                    print(f"\n[Tłumacz / Faza 1]: Serwer Google potrzebował więcej czasu na odpowiedź (limit {timeout_sec}s).")
                    print(f"  [..] Odczekuję {wait_time}s i ponawiam próbę #{attempt}...")
                    time.sleep(wait_time)
                elif is_unavailable:
                    wait_time = min(4 + attempt * 2, 20)
                    print(f"\n[Tłumacz / Faza 1]: Chwilowe przeciążenie serwerów Google (503 UNAVAILABLE na {current_model}).")
                    print(f"  [..] Utrzymuję najwyższą jakość modelu bez redukcji.")
                    print(f"  Odczekuję {wait_time}s i ponawiam próbę #{attempt}...")
                    time.sleep(wait_time)
                elif is_rate_limit:
                    wait_time = min(6 + attempt * 3, 30)
                    print(f"\n[Tłumacz / Faza 1]: Chwilowy limit minutowy zapytań (429 Rate Limit na {current_model}).")
                    print(f"  [..] Chwila przerwy na reset limitu ({wait_time}s)... Wznawiam automatycznie (próba #{attempt}).")
                    time.sleep(wait_time)
                else:
                    wait_time = min(4 + attempt * 2, 20)
                    clean_msg = str(e).split("{")[0].strip() if "{" in str(e) else str(e)
                    print(f"\n[Tłumacz / Faza 1]: Ponawianie próby #{attempt} za {wait_time}s ({clean_msg})...")
                    time.sleep(wait_time)

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

        manga_canon_entry = None
        for cand in candidates_to_match:
            if cand:
                manga_canon_entry = self.manga_canon.find_canon_for_series(cand)
                if manga_canon_entry:
                    break

        manga_canon_str = ""
        if manga_canon_entry:
            manga_canon_str = self.manga_canon.format_canon_for_prompt(manga_canon_entry)
            print(f"  [Kanon Mangi]: Wczytano oficjalną polską terminologię ({manga_canon_entry.get('publisher', 'Wydawnictwo')})")
            if manga_canon_entry.get("glossary"):
                self.series_bible.update_from_episode_profile(
                    episode_name="Kanon Mangi",
                    characters={},
                    glossary=manga_canon_entry["glossary"]
                )

        series_bible_str = self.series_bible.format_for_prompt()
        if series_bible_str:
            print(f"  [Biblia Serialu]: Wczytano ciągłość sezonu dla serii '{series_title or self.series_bible.slug}'")

        # 0d. Combined User and Series Bible Glossary (Deterministic)
        series_gloss_dict = self.series_bible.data.get("glossary", {}) if hasattr(self, "series_bible") and self.series_bible else {}
        combined_glossary = self.glossary_manager.get_combined_glossary(series_gloss_dict)
        if combined_glossary:
            print(f"  [Słownik Deterministyczny]: Aktywnych {len(combined_glossary)} żelaznych terminów.")

        user_rules_cnt = len(self.user_feedback.list_all())
        if user_rules_cnt > 0:
            print(f"  [Korekty Użytkownika]: Wczytano {user_rules_cnt} złotych reguł (Few-Shot Prompting).")

        # 0e. Pre-warming and Context Cache Hard Protection (guarantees -75% discount)
        from context_cache import ContextCacheManager
        print(f"  [Infrastruktura Finansowa]: Weryfikacja i rozgrzewanie pamięci Context Cache...")
        c1 = ContextCacheManager.ensure_cache_ready(self.client, self.model_phase1, self.system_prompt)
        if not c1:
            raise RuntimeError(
                f"KATEGORYCZNA BLOKADA FINANSOWA: Nie udało się aktywować serwerowego Context Cache dla {self.model_phase1}. "
                "Aby uchronić Twój portfel przed naliczeniem 4-krotnie wyższej stawki pełnej ($1.25/1M), proces został bezpiecznie wstrzymany. "
                "Sprawdź połączenie z Google API lub stan konta i spróbuj ponownie."
            )
        if self.verifier and hasattr(self.verifier, "client") and hasattr(self.verifier, "model") and hasattr(self.verifier, "system_prompt"):
            c2 = ContextCacheManager.ensure_cache_ready(self.verifier.client, self.verifier.model, self.verifier.system_prompt)
            if not c2:
                raise RuntimeError(
                    f"KATEGORYCZNA BLOKADA FINANSOWA: Nie udało się aktywować serwerowego Context Cache dla weryfikatora ({self.verifier.model}). "
                    "Aby uchronić Twój portfel przed naliczeniem 4-krotnie wyższej stawki pełnej, proces został bezpiecznie wstrzymany."
                )

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
            if episode_profile.glossary:
                terms_preview = ", ".join([f"'{g.term_en}' -> '{g.translation_pl}'" for g in episode_profile.glossary])
                print(f"  [Słowniczek Odcinka]: {terms_preview}")
        if self.whisper:
            print(f"  [Lokalny Whisper STT]: AKTYWNY (model {self.whisper.model_size})")

        batches = [
            raw_entries[i:i + self.batch_size]
            for i in range(0, total_lines, self.batch_size)
        ]

        with tqdm(total=total_lines, desc="Tłumaczenie dialogów", unit="linii") as pbar:
            pbar.start_t = time.time()
            already_done = sum(1 for item in raw_entries if item[0] in translated_results)
            if already_done > 0:
                pbar.update(already_done)

            for b_idx, batch in enumerate(batches):
                if cancel_check and cancel_check():
                    print("\n[Tłumacz]: Otrzymano sygnał przerwania (⏹ Stop). Bezpieczne zatrzymanie i zapis stanu...")
                    break

                untranslated_in_batch = [item for item in batch if item[0] not in translated_results]
                if not untranslated_in_batch:
                    continue

                # Retrieve upcoming lines (Lookahead Window)
                lookahead_events = []
                if b_idx + 1 < len(batches):
                    lookahead_events = batches[b_idx + 1][:4]

                # 2. Extract 1-2 key video frames for the batch
                temp_frames: List[str] = []
                image_contents = []

                if video_path and os.path.exists(video_path):
                    timestamps_to_extract = [
                        (untranslated_in_batch[0][1].start + untranslated_in_batch[0][1].end) // 2
                    ]
                    if len(untranslated_in_batch) > 6:
                        mid_idx = len(untranslated_in_batch) // 2
                        timestamps_to_extract.append(
                            (untranslated_in_batch[mid_idx][1].start + untranslated_in_batch[mid_idx][1].end) // 2
                        )

                    for ts in timestamps_to_extract:
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
                contents: List[Any] = []
                # Console preview of Whisper status in phonetic Romaji
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

                # Update global Character Registry
                if batch_response and batch_response.characters_identified:
                    for char in batch_response.characters_identified:
                        if char.name:
                            desc = f"{char.gender} ({char.role or 'postać'})"
                            self.character_registry[char.name] = desc
                if batch_response and batch_response.scene_description:
                    pbar.write(f" ├─ [Kontekst] {batch_response.scene_description}")

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
                scene_desc = batch_response.scene_description if batch_response else ""

                for idx, (orig_idx, event, clean_en, ts_prefix) in enumerate(untranslated_in_batch):
                    batch_id = idx + 1
                    pl_candidate = ""
                    speaker_gender = None
                    notes = ""
                    vtype = detect_event_visual_type(event, ts_prefix)
                    cps, is_fast = calculate_cps(clean_en, event.start, event.end)
                    cps_warn = f"Tempo CPS: {cps:.1f} (czas {(event.end - event.start)/1000.0:.1f}s)" if is_fast else ""

                    if batch_response:
                        for tr in batch_response.translations:
                            if tr.id == batch_id:
                                pl_candidate = sanitize_sub_text(tr.polish_text)
                                speaker_gender = tr.speaker_gender
                                notes = f"{tr.visual_clues or ''} {tr.notes or ''}".strip()
                                break

                    if not pl_candidate:
                        pl_candidate = clean_en

                    jp_text = whisper_transcriptions.get(batch_id, "") if whisper_transcriptions else ""
                    romaji_str = to_romaji(jp_text) if jp_text else ""
                    audio_jp_str = f"{jp_text} [{romaji_str}]" if romaji_str and romaji_str != jp_text else jp_text

                    audio_discrepancy_msg = detect_audio_discrepancy(audio_jp_str, pl_candidate, clean_en)

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
                        "cps_warning": cps_warn,
                        "notes": notes,
                        "is_sign": vtype["is_sign"],
                        "visual_type": vtype["type_label"],
                        "visual_details": vtype["visual_details"],
                        "is_song": is_song_line(event, clean_en)
                    })

                # 6. Optional Phase 2 Verifier (Script Doctor)
                all_user_rules = self.user_feedback.list_all()

                if self.enable_verifier and hasattr(self, 'verifier'):
                    pbar.set_postfix_str("Faza 2 (Redakcja Dialogów Pro)...")
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
                        if r.changes_made:
                            pbar.write(f" └─ [Redaktor Dialogów] {r.changes_made}")
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
                        if item.get("is_song"):
                            clean_no_notes = re.sub(r"^[♪♫♬\s]+|[♪♫♬\s]+$", "", final_text).strip()
                            if clean_no_notes:
                                final_text = f"♪ {clean_no_notes} ♪"
                        for fix in fixes + gloss_fixes:
                            pbar.write(f"  [AVT Linter/Słownik] {fix}")
                        formatted_final = split_subtitle_syntactically(final_text, max_line_len=42, is_ass=is_ass, is_sign=item.get("is_sign", False))
                        translated_results[item["orig_idx"]] = formatted_final
                        history.append({"en": item["en"], "pl": formatted_final})
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
                        if item.get("is_song"):
                            clean_no_notes = re.sub(r"^[♪♫♬\s]+|[♪♫♬\s]+$", "", final_text).strip()
                            if clean_no_notes:
                                final_text = f"♪ {clean_no_notes} ♪"
                        for fix in fixes + gloss_fixes:
                            pbar.write(f"  [AVT Linter/Słownik] {fix}")
                        formatted_final = split_subtitle_syntactically(final_text, max_line_len=42, is_ass=is_ass, is_sign=item.get("is_sign", False))
                        translated_results[item["orig_idx"]] = formatted_final
                        history.append({"en": item["en"], "pl": formatted_final})

                # Harmonize concurrent screen subtitles (e.g. speech balloon + dialogue with identical EN text)
                en_to_best_pl: Dict[str, str] = {}
                for item in pass1_items:
                    en_norm = item["en"].strip().lower()
                    pl_res = translated_results.get(item["orig_idx"], "")
                    if pl_res and "to robi" not in pl_res.lower():
                        en_to_best_pl[en_norm] = pl_res

                for item in pass1_items:
                    en_norm = item["en"].strip().lower()
                    if en_norm in en_to_best_pl:
                        cur_pl = translated_results.get(item["orig_idx"], "")
                        if "to robi" in cur_pl.lower():
                            translated_results[item["orig_idx"]] = en_to_best_pl[en_norm]

                # Auto-save checkpoint after each batch (persisting token usage)
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

                pbar.update(len(untranslated_in_batch))
                
                if progress_callback:
                    try:
                        from pricing_guard import PricingGuard
                        f1_stats = self.current_episode_tokens
                        f2_stats = self.verifier.current_episode_tokens if self.verifier else None
                        cur_cost_pln = PricingGuard.calculate_actual_cost_pln(f1_stats, f2_stats)
                        # Prepare recent translation previews for UI live monitor
                        recent_previews = []
                        for it in pass1_items:
                            o_idx = it["orig_idx"]
                            recent_previews.append({
                                "id": o_idx + 1,
                                "en": it["en"],
                                "pl": translated_results.get(o_idx, "")
                            })
                        progress_callback(len(translated_results), total_lines, recent_previews, cur_cost_pln)
                    except Exception:
                        pass

                time.sleep(2.0)

        # 7. Construct final subtitle file preserving styles, positioning, and typesetting
        final_subs = pysubs2.SSAFile()
        # Copy full stylesheet (fonts, colors, positions)
        final_subs.styles = subs.styles.copy()
        final_subs.info = subs.info.copy()
        # Force WrapStyle: 2 (no arbitrary line wrapping by video player)
        final_subs.info["WrapStyle"] = "2"

        for orig_idx, orig_event, _, ts_prefix in raw_all_entries:
            master_id = sub_to_master.get(orig_idx, orig_idx)
            if master_id not in translated_results:
                continue
            
            clean_translated_text = sanitize_sub_text(translated_results[master_id])
            if not clean_translated_text:
                continue

            # Reattach Typesetting tags to translated text
            full_event_text = f"{ts_prefix}{clean_translated_text}" if ts_prefix else clean_translated_text

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
        
        # Remove checkpoint file upon successful completion
        if checkpoint_path.exists():
            try:
                os.remove(str(checkpoint_path))
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
            
            print("─" * 60)
            print(f"  💰 RZECZYWISTY KOSZT ODCINKA: {actual_cost_pln:.2f} PLN")
            print(f"  ├─ Faza 1 (Szkic/OCR): {cost_f1_pln:.2f} PLN [Prompt: {f1_stats.get('prompt',0)} (Cached: {f1_stats.get('cached',0)}), Wyjście: {f1_stats.get('output',0)}]")
            if f2_stats:
                cot_budget = getattr(self.verifier, 'thinking_budget', 1600)
                print(f"  └─ Faza 2 (Reżyseria Pro): {cost_f2_pln:.2f} PLN [Prompt: {f2_stats.get('prompt',0)} (Cached: {f2_stats.get('cached',0)}), Wyjście+CoT {cot_budget}: {f2_stats.get('output',0)}]")
            print("─" * 60)
        except Exception:
            pass

        # Clean up server-side Context Cache objects to avoid storage fees
        try:
            from context_cache import ContextCacheManager
            ContextCacheManager.cleanup_all_active_caches(self.client)
            if self.verifier and hasattr(self.verifier, "client") and self.verifier.client != self.client:
                ContextCacheManager.cleanup_all_active_caches(self.verifier.client)
        except Exception:
            pass

        return output_path
