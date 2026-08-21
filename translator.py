"""
Główny silnik tłumaczenia napisów z wykorzystaniem analizy multimodalnej Gemini Flash.
Zawiera mechanizmy:
1. Pełnego zachowania Typesettingu (TS) i pozycjonowania na ekranie (\\an8, \\pos, \\c, Style, Warstwy)
2. Automatycznego pobierania wiedzy z AniList (fabuła, postacie, płeć) na podstawie nazwy pliku
3. Słuchania oryginalnego japońskiego audio (Multimodal Speech Recognition & Japanese Vocabulary)
4. Rejestru Postaci (Character Registry / Cast Tracker) - długoterminowe zapamiętywanie płci i relacji
5. Kontekstu Przyszłego (Lookahead Window) - podgląd kolejnych kwestii do wykrywania płci i kontekstu
6. Usuwania i sanityzacji uszkodzonych tagów ASS (brak śmieci typu {\\t(2840,3799,\\)
7. Bezwzględnej deduplikacji napisów o identycznym czasie trwania
8. 100% zachowania oryginalnych znaczników czasowych (timingu)
9. Autozapisu (checkpointing) i automatycznego wznawiania
"""

import os
import sys

# Wymuszenie pełnej obsługi znaków UTF-8 (w tym japońskich znaków Kanji/Kana)
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

# Wyciszenie ostrzeżeń deweloperskich z biblioteki google_genai
logging.getLogger("google_genai").setLevel(logging.ERROR)
logging.getLogger("google_genai.models").setLevel(logging.ERROR)

from google import genai
from google.genai import types

from rules import get_translation_system_prompt
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

def extract_typesetting_tags(raw_text: str) -> Tuple[str, str]:
    """
    Wyodrębnia poprawne tagi pozycjonowania i stylizacji ASS (np. {\\an8}, {\\pos(x,y)}, {\\fad(..)})
    z początku kwestii, aby zachować Typesetting i pozycję na ekranie.
    Zwraca: (prefix_tagów, czysty_tekst_dialogu)
    """
    if not raw_text:
        return "", ""
    
    # Wykrywanie początkowych bloków tagów ASS
    match = re.match(r"^((?:\{[^}]+\})+)", raw_text)
    if match:
        tag_prefix = match.group(1)
        # Upewniamy się, że to nie jest uszkodzony tag (musi zawierać znaki komend ASS)
        if "\\" in tag_prefix and not tag_prefix.endswith("\\"):
            remaining = raw_text[len(tag_prefix):]
            clean_remaining = sanitize_sub_text(remaining)
            return tag_prefix, clean_remaining

    return "", sanitize_sub_text(raw_text)

def detect_event_visual_type(event: pysubs2.SSAEvent, ts_prefix: str) -> Dict[str, Any]:
    """
    Analizuje tagi ASS, pozycję, kąt obrotu, kolor oraz styl napisu,
    aby precyzyjnie odróżnić napisy ekranowe (tytuły mang, znaki, plakaty, tablice)
    od standardowych dialogów mówionych.
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

def sanitize_sub_text(text: str, is_ass: bool = True) -> str:
    """
    Czyści tekst ze śmieci formatowania ASS, niedomkniętych nawiasów i zbędnych znaków,
    jednocześnie poprawnie konwertując tagi HTML <i> / <b> na natywne formatowanie ASS {\\i1}...{\\i0}.
    """
    if not text:
        return ""
    
    if is_ass:
        # Konwersja <i> i <b> na format ASS {\i1} i {\b1}
        text = re.sub(r"<i>(.*?)</i>", r"{\\i1}\1{\\i0}", text, flags=re.IGNORECASE)
        text = re.sub(r"<b>(.*?)</b>", r"{\\b1}\1{\\b0}", text, flags=re.IGNORECASE)
        # Usunięcie wszelkich pozostałych surowych tagów HTML
        text = re.sub(r"</?[a-zA-Z][^>]*>", "", text)
        # Usunięcie uszkodzonych tagów ASS (z zachowaniem {\i1}, {\i0}, {\b1}, {\b0})
        text = re.sub(r"\{(?!(?:\\i[01]|\\b[01]))[^}]*\}?", "", text)
        text = re.sub(r"\{[^\\]*$", "", text)
    else:
        # Dla SRT: konwersja tagów ASS na HTML
        text = re.sub(r"\{\\i1\}(.*?)\{\\i0\}", r"<i>\1</i>", text)
        text = re.sub(r"\{\\b1\}(.*?)\{\\b0\}", r"<b>\1</b>", text)
        # Usunięcie wszelkich tagów klamrowych
        text = re.sub(r"\{[^}]*\}?", "", text)
        # Usunięcie niechcianych tagów HTML z wyjątkiem <i>, </i>, <b>, </b>
        text = re.sub(r"</?(?!(?:i|b)\b)[a-zA-Z][^>]*>", "", text)

    # Normalizacja spacji i enterów
    text = re.sub(r"[ \t]+", " ", text).strip()
    return text

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
        whisper_model_size: str = "large-v3-turbo"
    ):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError(
                "Nie znaleziono klucza API Gemini! Ustaw zmienną środowiskową GEMINI_API_KEY "
                "lub utwórz plik .env z wpisem GEMINI_API_KEY=twój_klucz"
            )
        
        self.client = genai.Client(api_key=self.api_key)
        self.model = model
        self.model_phase1 = model
        self.model_phase2 = model_phase2 or model
        self.batch_size = batch_size
        self.enable_verifier = enable_verifier
        self.max_image_width = max_image_width
        self.keep_honorifics = keep_honorifics
        self.system_prompt = get_translation_system_prompt(keep_honorifics=keep_honorifics)
        
        # Profiler Odcinka (Pre-pass Glossary & Character Matrix)
        self.profiler = EpisodeProfiler(client=self.client, model=self.model_phase1)
        
        # Opcjonalny lokalny japoński Whisper (Speech-to-Text)
        self.whisper = None
        if use_whisper and JapaneseWhisperEngine.is_available():
            try:
                self.whisper = JapaneseWhisperEngine(model_size=whisper_model_size)
            except Exception:
                self.whisper = None
        
        # Faza 2 - Script Doctor (może działać na modelu Pro)
        if self.enable_verifier:
            self.verifier = DialogueVerifier(
                client=self.client,
                model=self.model_phase2,
                keep_honorifics=keep_honorifics
            )
        
        # Pamięć postaci w filmie (Character Registry)
        self.character_registry: Dict[str, str] = {}
        
        # Pamięć Tłumaczeniowa z korpusu (Translation Memory)
        try:
            self.tm = TranslationMemory()
            # Sprawdzenie czy baza wymaga zaindeksowania
            baza_dir = Path(__file__).parent / "baza napisów"
            if baza_dir.exists():
                with sqlite3.connect(self.tm.db_path) as conn:
                    cnt = conn.execute("SELECT COUNT(*) FROM translation_pairs").fetchone()[0]
                if cnt == 0:
                    self.tm.index_database_directory(baza_dir)
        except Exception:
            self.tm = None

        # Rejestr Oficjalnego Kanonu Polskich Wydań Mangowych (Waneko, JPF, Studio JG itp.)
        self.manga_canon = MangaCanonRegistry()

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
        manga_canon_str: str = ""
    ) -> str:
        """
        Tworzy tekst promptu dla danej paczki kwestii wraz z:
        - Oficjalnym Kanonem Mangi (Wydawnictwa Waneko, JPF, Studio JG itp.)
        - Biblią Serialu (Pamięć Międzyodcinkowa)
        - Profilem odcinka (Słowniczek i Macierz Relacji)
        - Kontekstem fabuły z bazy AniList
        - Wzorcami z Pamięci Tłumaczeniowej (Translation Memory)
        - Rejestrem znanych postaci (Character Registry)
        - Historią poprzednich dialogów
        - Podglądem nadchodzących kwestii (Lookahead Window)
        - Japońską transkrypcją mowy ze słuchu (Whisper STT)
        - Cechami prozodii audio (szept/krzyk) i klasyfikacją głosu (diarizacja)
        - Ostrzeżeniami tempa czytania CPS
        """
        lines = []

        # 0a. Oficjalny Kanon Polskiego Wydania Mangi
        if manga_canon_str:
            lines.append(manga_canon_str)

        # 0b. Ciągłość terminologiczna z Biblii Serialu
        if series_bible_str:
            lines.append(series_bible_str)

        # 0b. Słowniczek i Macierz Relacji z Profilera Odcinka (lub kontekst AniList w razie braku profilera)
        if episode_profile_str:
            lines.append(episode_profile_str)
        elif anime_context_str:
            lines.append(anime_context_str)

        # 0c. Złote przykłady z Pamięci Tłumaczeniowej (Translation Memory)
        if self.tm:
            try:
                batch_queries = [item[2] for item in batch_events]
                tm_examples = self.tm.find_relevant_examples(batch_queries, max_examples=4)
                if tm_examples:
                    lines.append(format_translation_memory_for_prompt(tm_examples))
            except Exception:
                pass

        # 1. Rejestr znanych postaci
        if self.character_registry:
            lines.append("--- ZNANE POSTACIE W TYM FILMIE (dla zachowania spójności płci i imion) ---")
            for name, details in self.character_registry.items():
                lines.append(f"• {name}: {details}")
            lines.append("--------------------------------------------------------------------------\n")

        # 2. Historia poprzednich kwestii
        if history_context:
            lines.append("--- POPRZEDNIE KWESTIE W SCENIE (kontekst przeszły) ---")
            for h in history_context[-4:]:
                lines.append(f"[Poprzednio] EN: {h['en']} -> PL: {h['pl']}")
            lines.append("-------------------------------------------------------\n")

        # 3. Kwestie do przetłumaczenia
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

            if vtype["is_sign"]:
                lines.append(f"Kwestia [ID: {idx + 1}] [TYP: [NAPIS] {vtype['type_label']}] (Czas: {start_str} - {end_str}, Cechy: {vtype['visual_details']}):")
                lines.append(f"  (!) UWAGA WIZUALNA: To jest NAPIS / TYTUŁ NA EKRANIE (np. tytuł mangi, rozdział, tablica, napis wklejony w kadr).")
                lines.append(f"  Przetłumacz ten tekst jako SAMODZIELNY TYTUŁ/NAPIS (np. 'The Princess's Favor' / '姫様のご寵愛' -> 'Łaska księżniczki' / 'Faworyta księżniczki').")
                lines.append(f"  BEZWZGLĘDNY ZAKAZ wklejania tu fragmentów dialogów mówionych przez postacie!")
            else:
                speaker_name = event.name if event.name else "Postać"
                lines.append(f"Kwestia [ID: {idx + 1}] [TYP: [DIALOG] {vtype['type_label']}] (Czas: {start_str} - {end_str}, Mówca: '{speaker_name}'){acoustic_str}:")
                if is_fast:
                    lines.append(f"  (!) TEMPO CPS ({cps:.1f} z/s, czas {duration_s:.1f}s): Szybka kwestia! Zastosuj zwięzłą kondensację Belczyka.")

            if whisper_transcriptions and idx + 1 in whisper_transcriptions:
                jp_text = whisper_transcriptions[idx + 1]
                if jp_text and not vtype["is_sign"]:
                    lines.append(f"  JP (Japoński oryginał z mowy): {jp_text}")
            lines.append(f"  EN (Napisy pomocnicze): {clean_text}")

        # 4. Podgląd przyszłych kwestii (Lookahead)
        if lookahead_events:
            lines.append("\n--- PODGLĄD NASTĘPNYCH KWESTII (NIE TŁUMACZ ICH! Użyj tylko do zrozumienia kontekstu i płci) ---")
            for _, _, future_text, _ in lookahead_events[:4]:
                lines.append(f"[Wkrótce] EN: {future_text}")
            lines.append("------------------------------------------------------------------------------------------------")

        return "\n".join(lines)

    def _call_gemini_with_retry(self, contents: List[Any], schema_class) -> Any:
        """
        Bezpieczne wywołanie API z automatyczną obsługą chwilowych limitów minutowych (429) i przeciążeń (503).
        Wykorzystuje inteligentną pulę modeli flagowych (Tier-Preserving Model Pool), aby zapewnić
        100% najwyższą jakość tłumaczenia bez wielominutowych przestojów.
        """
        # Pula wyłącznie dwóch absolutnie najnowszych modeli flagowych (Gemini 3.7 i 3.6 Flash)
        candidate_models = [self.model]
        if "flash" in self.model.lower():
            for m in ["gemini-3.7-flash", "gemini-3.6-flash"]:
                if m not in candidate_models:
                    candidate_models.append(m)
        elif "pro" in self.model.lower():
            for m in ["gemini-3.1-pro-preview"]:
                if m not in candidate_models:
                    candidate_models.append(m)
        # Ograniczenie do maksymalnie 2 najnowszych modeli
        candidate_models = candidate_models[:2]

        attempt = 0
        current_model_idx = 0

        while True:
            attempt += 1
            current_model = candidate_models[current_model_idx]
            try:
                from context_cache import ContextCacheManager
                cached_name = ContextCacheManager.get_or_create_cache(
                    client=self.client,
                    model=current_model,
                    system_instruction=self.system_prompt,
                    ttl_seconds=7200
                )
                gen_config_kwargs = {
                    "response_mime_type": "application/json",
                    "response_schema": schema_class,
                    "temperature": 0.25,
                }
                if cached_name:
                    gen_config_kwargs["cached_content"] = cached_name
                else:
                    gen_config_kwargs["system_instruction"] = self.system_prompt

                response = self.client.models.generate_content(
                    model=current_model,
                    contents=contents,
                    config=types.GenerateContentConfig(**gen_config_kwargs)
                )
                if hasattr(response, "parsed") and response.parsed is not None:
                    return response.parsed
                else:
                    return schema_class.model_validate(json.loads(response.text))

            except Exception as e:
                err_str = str(e).lower()
                is_billing_exhausted = "prepayment" in err_str or "depleted" in err_str or ("billing" in err_str and "credit" in err_str)
                if is_billing_exhausted:
                    print("\n" + "!" * 75)
                    print("  [!] [BŁĄD KONTA GOOGLE AI STUDIO / PŁATNOŚCI]:")
                    print("  Wyczerpały się środki przedpłacone (Prepayment Credits / Limit wydatków)!")
                    print("  Komunikat Google: 'Your prepayment credits are depleted.'")
                    print("  -> Wejdź na https://aistudio.google.com/ i doładuj środki, aby kontynuować.")
                    print("!" * 75 + "\n")
                    raise RuntimeError("Wyczerpane środki na koncie Google AI Studio (Prepayment Credits Depleted).")

                is_unavailable = "503" in err_str or "unavailable" in err_str or "high demand" in err_str
                is_rate_limit = "429" in err_str or "quota" in err_str or "resource_exhausted" in err_str or "rate" in err_str
                
                # Jeśli po 2 próbach dany model ma 503 na serwerach Google, natychmiast sięgamy po flagowy 3.6/3.5
                if is_unavailable and len(candidate_models) > 1 and attempt >= 2:
                    next_idx = (current_model_idx + 1) % len(candidate_models)
                    if next_idx != current_model_idx:
                        print(f"\n[Tłumacz / Faza 1]: Model {current_model} jest przeciążony u Google (503).")
                        print(f"  [>>] Płynne przełączenie na bezpośredni model flagowy {candidate_models[next_idx]} (100% jakość bez czekania)...")
                        current_model_idx = next_idx
                        time.sleep(1)
                        continue

                if is_unavailable:
                    wait_time = min(4 + attempt * 2, 20)
                    print(f"\n[Tłumacz / Faza 1]: Chwilowe przeciążenie serwerów Google (503 UNAVAILABLE na {current_model}).")
                    print(f"  [..] Utrzymuję najwyższą jakość modelu bez redukcji.")
                    print(f"  Odczekuję {wait_time}s i ponawiam próbę #{attempt}...")
                    time.sleep(wait_time)
                elif is_rate_limit:
                    wait_time = min(6 + attempt * 3, 30)
                    print(f"\n[Limit minutowy Google / 429 na {current_model}]: Chwila przerwy na reset limitu ({wait_time}s)... Wznawiam automatycznie (próba #{attempt}).")
                    time.sleep(wait_time)
                else:
                    wait_time = min(4 + attempt * 2, 20)
                    print(f"\n[Tłumacz / Faza 1]: Ponawianie próby #{attempt} za {wait_time}s ({e})...")
                    time.sleep(wait_time)

    def translate_file(
        self,
        subs_path: str,
        video_path: Optional[str] = None,
        output_path: Optional[str] = None,
        progress_callback = None
    ) -> str:
        """
        Główna metoda tłumacząca plik z napisami z pełnym zachowaniem Typesettingu, stylów i timingu.
        """
        subs_file = Path(subs_path)
        if not subs_file.exists():
            raise FileNotFoundError(f"Nie znaleziono pliku napisów: {subs_path}")

        is_ass = not str(subs_file).lower().endswith(".srt")

        try:
            subs = pysubs2.load(str(subs_file), encoding="utf-8")
        except UnicodeDecodeError:
            subs = pysubs2.load(str(subs_file), encoding="latin2")

        # 0. Pobranie metadanych anime z AniList
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
            
            # Wstępne wypełnienie rejestru postaci z bazy AniList
            for c in anime_meta.get("characters", []):
                self.character_registry[c["name"]] = f"{c['gender']} ({c['role']})"

        # 1. Czyszczenie kwestii i ekstrakcja tagów Typesettingu
        raw_entries = []
        for i, ev in enumerate(subs.events):
            if ev.is_comment:
                continue
            ts_prefix, clean = extract_typesetting_tags(ev.text)
            if not clean:
                clean = sanitize_sub_text(ev.plaintext)
            if not clean:
                continue
            raw_entries.append((i, ev, clean, ts_prefix))

        total_lines = len(raw_entries)
        print(f"\n[Translator] Załadowano {total_lines} kwestii dialogowych do przetłumaczenia.")
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

        # 1b. Szukanie plików checkpointu (wielokrotne ścieżki i formaty)
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
        for cand in candidate_checkpoints:
            if cand and cand.exists() and cand.is_file():
                try:
                    with open(cand, "r", encoding="utf-8") as cp_file:
                        saved_data = json.load(cp_file)
                        if isinstance(saved_data, dict) and len(saved_data) > 0:
                            translated_results = {int(k): str(v) for k, v in saved_data.items() if str(k).isdigit()}
                            if translated_results:
                                found_checkpoint_path = cand
                                break
                except Exception:
                    pass

        if found_checkpoint_path and translated_results:
            print("\n" + "═" * 60)
            print(f"  [AUTOZAPIS / WZNOWIENIE]: Znaleziono plik checkpointu!")
            print(f"  Plik: {found_checkpoint_path.name}")
            print(f"  Wczytano {len(translated_results)}/{total_lines} gotowych kwestii dialogowych.")
            print("═" * 60 + "\n")
        else:
            print("[Autozapis]: Brak wcześniejszego checkpointu. Rozpoczynanie tłumaczenia.")

        # 0. Profiler Odcinka (Pre-pass Glossary & Relationship Matrix)
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

        # 0b. Inicjalizacja i wczytanie Biblii Serialu (Pamięć Międzyodcinkowa Sezonu)
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
            self.series_bible.update_from_episode_profile(
                episode_name=Path(subs_path).stem if subs_path else "Odcinek",
                characters=char_dict,
                glossary=gloss_dict
            )

        # 0c. Sprawdzenie Oficjalnego Kanonu Polskiego Wydania Mangi (Waneko, JPF, Studio JG, Hanami itp.)
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
            already_done = sum(1 for item in raw_entries if item[0] in translated_results)
            if already_done > 0:
                pbar.update(already_done)

            for b_idx, batch in enumerate(batches):
                untranslated_in_batch = [item for item in batch if item[0] not in translated_results]
                if not untranslated_in_batch:
                    continue

                # Pobieramy nadchodzące kwestie (Lookahead Window)
                lookahead_events = []
                if b_idx + 1 < len(batches):
                    lookahead_events = batches[b_idx + 1][:4]

                # 2. Inteligentna ekstrakcja 1-2 kluczowych klatek dla paczki
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

                # 2b. Ekstrakcja wycinka audio i Błyskawiczna LOKALNA transkrypcja Whisper + Prozodia + Diarizacja (100% Offline / 0 zł)
                temp_audio_file = None
                whisper_transcriptions: Dict[int, str] = {}
                prosody_tags: Dict[int, str] = {}
                speaker_tags: Dict[int, str] = {}
                if video_path and os.path.exists(video_path):
                    try:
                        batch_start = untranslated_in_batch[0][1].start
                        batch_end = untranslated_in_batch[-1][1].end
                        if 0 < (batch_end - batch_start) <= 120000:
                            temp_audio_file = extract_audio_slice(
                                video_path=video_path,
                                start_ms=batch_start,
                                end_ms=batch_end
                            )
                            events_tuples = [(idx + 1, item[1]) for idx, item in enumerate(untranslated_in_batch)]
                            
                            # 1. Lokalna transkrypcja Whisper
                            if self.whisper:
                                whisper_transcriptions = self.whisper.transcribe_batch_scene(
                                    scene_wav_path=temp_audio_file,
                                    batch_start_ms=batch_start,
                                    events=events_tuples
                                )

                            # 2. Lokalna analiza prozodii (RMS dBFS / szept / krzyk)
                            prosody_tags = AudioProsodyEngine.analyze_scene_prosody(
                                wav_path=temp_audio_file,
                                batch_start_ms=batch_start,
                                events=events_tuples
                            )

                            # 3. Lokalna diarizacja i szacowanie barwy głosu F0
                            speaker_tags = SpeakerVoiceClassifier.classify_scene_speakers(
                                wav_path=temp_audio_file,
                                batch_start_ms=batch_start,
                                events=events_tuples
                            )
                    except Exception:
                        pass

                # 3. Prompt tekstowy z bazą wiedzy AniList, rejestrem postaci, lookaheadem i cechami fonicznymi
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
                    manga_canon_str=manga_canon_str
                )

                # 4. Wywołanie Gemini (Obraz + Tekst ze słuchu Whisper) - Zero opłat za streaming audio do Google!
                contents: List[Any] = []
                # Podgląd statusu Whisper w konsoli (Romaji fonetyczne - czytelne na każdym terminalu)
                if whisper_transcriptions:
                    jp_raw_list = [v for v in whisper_transcriptions.values() if v]
                    if jp_raw_list:
                        romaji_samples = [to_romaji(text) for text in jp_raw_list[:2]]
                        romaji_line = " | ".join(romaji_samples)
                        if len(romaji_line) > 75:
                            romaji_line = romaji_line[:72] + "..."
                        pbar.write(f" ├─ [Odsłuch JP] \"{romaji_line}\"")

                # 4. Wywołanie Gemini (Obraz + Tekst)
                contents: List[Any] = []
                contents.extend(image_contents)
                contents.append(prompt_text)

                pbar.set_postfix_str("Faza 1 (Wizja + Audio)...")
                batch_response = self._call_gemini_with_retry(
                    contents=contents,
                    schema_class=BatchTranslationResponse
                )

                # Aktualizacja globalnego Rejestru Postaci (Character Registry)
                if batch_response and batch_response.characters_identified:
                    for char in batch_response.characters_identified:
                        if char.name:
                            desc = f"{char.gender} ({char.role or 'postać'})"
                            self.character_registry[char.name] = desc
                if batch_response and batch_response.scene_description:
                    pbar.write(f" ├─ [Kontekst] {batch_response.scene_description}")

                # Czyszczenie klatek i audio tymczasowego
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

                # 5. Przetwarzanie odpowiedzi Fazy 1
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

                    pass1_items.append({
                        "id": batch_id,
                        "orig_idx": orig_idx,
                        "en": clean_en,
                        "pl": pl_candidate,
                        "speaker_gender": speaker_gender,
                        "speaker_voice": speaker_tags.get(batch_id, ""),
                        "prosody": prosody_tags.get(batch_id, ""),
                        "cps_warning": cps_warn,
                        "notes": notes,
                        "is_sign": vtype["is_sign"],
                        "visual_type": vtype["type_label"],
                        "visual_details": vtype["visual_details"]
                    })

                # 6. Opcjonalna II faza weryfikatora (Redakcja Literacka)
                if self.enable_verifier and hasattr(self, 'verifier'):
                    pbar.set_postfix_str("Faza 2 (Redakcja Dialogów Pro)...")
                    refined_lines: List[RefinedLine] = self.verifier.verify_batch(
                        batch_items=pass1_items,
                        scene_summary=scene_desc or "",
                        episode_profile_str=episode_profile_str
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
                            is_sign=item.get("is_sign", False)
                        )
                        for fix in fixes:
                            pbar.write(f"  [AVT Linter] {fix}")
                        formatted_final = split_subtitle_syntactically(final_text, max_line_len=42, is_ass=is_ass)
                        translated_results[item["orig_idx"]] = formatted_final
                        history.append({"en": item["en"], "pl": formatted_final})
                else:
                    for item in pass1_items:
                        raw_final = sanitize_sub_text(item["pl"])
                        final_text, fixes = AVTLinter.lint_and_fix_line(
                            text=raw_final,
                            speaker_gender=item.get("speaker_gender"),
                            is_all_girls_scene=True,
                            is_sign=item.get("is_sign", False)
                        )
                        for fix in fixes:
                            pbar.write(f"  [AVT Linter] {fix}")
                        formatted_final = split_subtitle_syntactically(final_text, max_line_len=42, is_ass=is_ass)
                        translated_results[item["orig_idx"]] = formatted_final
                        history.append({"en": item["en"], "pl": formatted_final})

                # Harmonizacja równoczesnych napisów ekranowych (chmurka + dialog o identycznej treści EN)
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

                # Autozapis checkpointu po każdej przetłumaczonej paczce
                try:
                    with open(checkpoint_path, "w", encoding="utf-8") as cp_file:
                        json.dump(translated_results, cp_file, ensure_ascii=False)
                except Exception:
                    pass

                pbar.update(len(untranslated_in_batch))
                time.sleep(2.0)

        # 7. Budowa końcowego pliku z zachowaniem stylów, pozycjonowania i typesettingu
        final_subs = pysubs2.SSAFile()
        # Kopiowanie pełnego arkusza stylów (czcionki, kolory, położenie napisów)
        final_subs.styles = subs.styles.copy()
        final_subs.info = subs.info.copy()

        seen_events = set()

        for orig_idx, orig_event, _, ts_prefix in raw_entries:
            if orig_idx not in translated_results:
                continue
            
            clean_translated_text = sanitize_sub_text(translated_results[orig_idx])
            if not clean_translated_text:
                continue

            dedup_key = (orig_event.start // 150, orig_event.end // 150, clean_translated_text, orig_event.style)
            if dedup_key in seen_events:
                continue

            seen_events.add(dedup_key)

            # Ponowne dołączenie tagów Typesettingu do przetłumaczonego tekstu
            full_event_text = f"{ts_prefix}{clean_translated_text}" if ts_prefix else clean_translated_text

            new_event = orig_event.copy()
            new_event.text = full_event_text
            final_subs.events.append(new_event)

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
        
        # Usunięcie pliku checkpointu po pomyślnym ukończeniu całości
        if checkpoint_path.exists():
            try:
                os.remove(str(checkpoint_path))
            except OSError:
                pass

        print(f"\n[Sukces] Przetłumaczone, wyczyszczone napisy z zachowanym Typesettingiem zapisano w: {output_path}")
        return output_path
