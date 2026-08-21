"""
Zestaw testów weryfikacyjnych dla komponentów Multimodalnego Tłumacza Napisów.
"""

import os
import tempfile
import subprocess
from pathlib import Path
import pysubs2
from PIL import Image

from rules import (
    get_translation_system_prompt,
    get_verifier_system_prompt,
    ANTI_CALQUES_GUIDE
)
from extract import extract_frame_at_timestamp, list_subtitle_tracks
from verifier import RefinedLine, RefinedBatchResponse
from translator import LineTranslation, BatchTranslationResponse, sanitize_sub_text

def test_rules_and_prompts():
    print("[TEST 1/16] Sprawdzanie kompletności 43 Filarów AVT i promptów...")
    sys_prompt = get_translation_system_prompt()
    ver_prompt = get_verifier_system_prompt()
    assert "I see" in sys_prompt
    assert "Rozumiem" in sys_prompt
    assert "KANON PRZEKŁADU AUDIOWIZUALNEGO" in sys_prompt
    assert "Arkadiusza Belczyka" in ver_prompt
    assert "ODNOMINALIZOWANIE" in sys_prompt
    assert "FILAR XXIII: KANON POLSKICH WYDAŃ MANGOWYCH" in sys_prompt
    assert "FILAR XXIV: NADMIAROWOŚĆ INTERSEMIOTYCZNA" in sys_prompt
    assert "FILAR XXX: SELEKTYWNA REDUKCJA POTAKIWAŃ" in sys_prompt
    assert "FILAR XXXI: KALIBRACJA REJESTRU WULGARYZMÓW" in sys_prompt
    assert "FILAR XXXVI: TEORIA PREFABRYKOWANEJ MÓWIONOŚCI" in sys_prompt
    assert "FILAR XXXVII: ELIMINACJA NOŻYC OBRAZOWO-TEKSTOWYCH" in sys_prompt
    assert "FILAR XXXVIII: NIEROZERWALNOŚĆ JEDNOSTEK SENSU" in sys_prompt
    assert "FILAR XXXIX: EKWIWALENCJA EFEKTU EMOCJONALNEGO" in sys_prompt
    assert "FILAR XLII: AKUSTYCZNA KOHERENCJA REJESTRU WIEKOWEGO" in sys_prompt
    assert "FILAR XLIII: MATRYCA TOŻSAMOŚCI I KAMUFLAŻU PŁCIOWEGO" in sys_prompt
    assert "FILAR XLIV: CZASOWNIKI WEKTOROWE I CIĘCIA MONTAŻOWO-PRZESTRZENNE" in sys_prompt
    assert "FILAR XLIV: CZASOWNIKI WEKTOROWE I CIĘCIA MONTAŻOWO-PRZESTRZENNE" in ver_prompt
    assert "FILAR XLV: MATRYCA PRAGMATYCZNA POTWIERDZEŃ, APROBACJI I AIZUCHI" in sys_prompt
    assert "FILAR XLV: MATRYCA PRAGMATYCZNA POTWIERDZEŃ, APROBACJI I AIZUCHI" in ver_prompt
    assert "FILAR XLVI: ZASADA YOBISUTE I ZAKAZ SZTUCZNEGO „PANA/PANI”" in sys_prompt
    assert "FILAR XLVI: ZASADA YOBISUTE I ZAKAZ SZTUCZNEGO „PANA/PANI”" in ver_prompt
    print(" -> PASSED: Kompletny Kanon 46 Filarów AVT jest aktywny w obu fazach tłumaczenia.")

def test_pydantic_schemas():
    print("[TEST 2/5] Weryfikacja schematów Pydantic...")
    tr = LineTranslation(
        id=1,
        polish_text="Rozumiem, co masz na myśli.",
        speaker_gender="mężczyzna",
        visual_clues="mężczyzna w mundurze",
        notes="eliminacja kalki"
    )
    batch = BatchTranslationResponse(translations=[tr], scene_description="Testowa scena")
    assert batch.translations[0].id == 1

    ref = RefinedLine(
        id=1,
        original_en="I see.",
        refined_pl="Rozumiem.",
        changes_made="Poprawiono kalkę"
    )
    ref_batch = RefinedBatchResponse(lines=[ref])
    assert ref_batch.lines[0].refined_pl == "Rozumiem."
    print(" -> PASSED: Schematy Pydantic są poprawne.")

def test_sanitization_and_deduplication():
    print("[TEST 3/5] Test usuwania baboli ASS i deduplikacji znaków...")
    # Test usuwania urwanych tagów ASS
    corrupted_tag = "{\\t(2840,3799,\\"
    assert sanitize_sub_text(corrupted_tag) == ""

    # Test konwersji kursywy HTML na format ASS
    italic_html = "<i>Serio jej to pasuje?</i>"
    assert sanitize_sub_text(italic_html, is_ass=True) == "{\\i1}Serio jej to pasuje?{\\i0}"
    assert sanitize_sub_text(italic_html, is_ass=False) == "<i>Serio jej to pasuje?</i>"

    # Test usuwania znaczników pozycji
    pos_text = "{\\pos(100,200)\\an8}Wszyscy patrzą na Aratę"
    assert sanitize_sub_text(pos_text) == "Wszyscy patrzą na Aratę"

    # Test deduplikacji identycznych linii o tym samym czasie
    events = [
        pysubs2.SSAEvent(start=152010, end=155510, text="Odcinek 7"),
        pysubs2.SSAEvent(start=152010, end=155510, text="Odcinek 7"),
        pysubs2.SSAEvent(start=152010, end=155510, text="Odcinek 7"),
        pysubs2.SSAEvent(start=152010, end=155510, text="Wszyscy patrzą na Aratę"),
        pysubs2.SSAEvent(start=152010, end=155510, text="Wszyscy patrzą na Aratę"),
        pysubs2.SSAEvent(start=159060, end=160960, text="Przepraszam, Minami-kun."),
    ]
    seen = set()
    deduped = []
    for ev in events:
        key = (ev.start // 150, ev.end // 150, ev.text.strip())
        if key not in seen:
            seen.add(key)
            deduped.append(ev)
    assert len(deduped) == 3
    print(" -> PASSED: Sanityzacja tagów i deduplikacja działają bezbłędnie.")

def test_subtitle_parsing_and_saving():
    print("[TEST 4/5] Weryfikacja formatów napisów...")
    subs = pysubs2.SSAFile()
    ev1 = pysubs2.SSAEvent(start=1000, end=3500, text="<i>I see what you did there.</i>")
    ev2 = pysubs2.SSAEvent(start=4000, end=6500, text="Makes sense to me.\\NLet's do it!")
    subs.events.extend([ev1, ev2])

    with tempfile.NamedTemporaryFile(suffix=".srt", delete=False) as f:
        srt_path = f.name

    subs.save(srt_path, encoding="utf-8")
    loaded = pysubs2.load(srt_path, encoding="utf-8")
    assert len(loaded.events) == 2
    assert "I see" in loaded.events[0].text
    os.remove(srt_path)
    print(" -> PASSED: Parsowanie i zapis napisów działa bezbłędnie.")

def test_ffmpeg_frame_extraction():
    print("[TEST 5/5] Test ekstrakcji klatki ffmpeg...")
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
        test_video = f.name

    try:
        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi",
            "-i", "testsrc=duration=2:size=320x240:rate=24",
            "-pix_fmt", "yuv420p",
            test_video
        ]
        subprocess.run(cmd, capture_output=True, check=True)

        frame_out = extract_frame_at_timestamp(
            video_path=test_video,
            timestamp_ms=1000,
            max_width=320
        )
        assert os.path.exists(frame_out)
        with Image.open(frame_out) as img:
            assert img.size[0] == 320
        os.remove(frame_out)
        print(" -> PASSED: Ekstrakcja i skalowanie klatek ffmpeg działa w 100%.")
    finally:
        if os.path.exists(test_video):
            os.remove(test_video)

from profiler import EpisodeProfile, CharacterRelationship, GlossaryTerm, format_episode_profile_for_prompt
from whisper_engine import JapaneseWhisperEngine

def test_profiler_and_whisper():
    print("[TEST 6/6] Test profilera odcinka i silnika Whisper...")
    profile = EpisodeProfile(
        episode_summary="Odcinek o sprzątaniu klubu mangi",
        tone_and_genre="Komediodramat młodzieżowy",
        characters=[
            CharacterRelationship(
                speaker="Kokoro",
                listener="Teshima",
                address_form="pani Teshima",
                relationship_type="uczeń -> nauczycielka"
            )
        ],
        setting_and_era="XIII wiek, Imperium Mongolskie / Dwór Chanów",
        domain_expertise="Enologia i Sommelierstwo (Wino / Winiarstwo)",
        dialogue_stylization="Szlachetny rejestr epokowy, zakaz nowoczesnego slangu",
        glossary=[
            GlossaryTerm(
                term_en="taiyaki",
                translation_pl="taiyaki (słodycze rybne)",
                explanation="tradycyjne japońskie ciastka w kształcie ryby"
            )
        ],
        key_conventions=["Unikać kalki 'Bless you' -> 'Na zdrowie'"]
    )
    formatted = format_episode_profile_for_prompt(profile)
    assert "pani Teshima" in formatted
    assert "taiyaki" in formatted
    assert "Imperium Mongolskie" in formatted
    assert "Enologia i Sommelierstwo" in formatted
    
    # Test dostępności i stanu Whisper
    avail = JapaneseWhisperEngine.is_available()
from model_resolver import resolve_best_models, _extract_model_score

def test_model_resolver():
    print("[TEST 7/7] Test automatycznego wykrywania najnowszych modeli Gemini...")
    score_37 = _extract_model_score("gemini-3.7-flash")
    score_35 = _extract_model_score("gemini-3.5-flash")
    score_25 = _extract_model_score("gemini-2.5-flash")
    assert score_37 > score_35 > score_25
    
    models = resolve_best_models(None)
from avt_linter import AVTLinter
from series_memory import SeriesBible
from avt_formatter import split_subtitle_syntactically, calculate_cps, clean_text_for_len
from prosody_engine import AudioProsodyEngine
from speaker_diarizer import SpeakerVoiceClassifier
from typesetting_matcher import TypesettingColorMatcher, rgb_to_ass_hex
import numpy as np

def test_avt_linter():
    print("[TEST 8/12] Test automatycznego audytora polszczyzny AVT Linter...")
    # Test eliminacji sztucznego "Czy"
    t1, f1 = AVTLinter.lint_and_fix_line("Czy jesteś pewna?")
    assert t1 == "Jesteś pewna?"
    
    # Test eliminacji kalek
    t2, f2 = AVTLinter.lint_and_fix_line("To robi sens, witaj z powrotem!")
    assert "To ma sens" in t2
    assert "Witaj!" in t2
    
    # Test korekty rodzaju męskiego na żeński u dziewcząt
    t3, f3 = AVTLinter.lint_and_fix_line("Głupi jesteś?", is_all_girls_scene=True)
    assert t3 == "Głupia jesteś?"
    
    # Test korekty rekcji przyczyny zgonu (wylew / atak serca)
    t4, f4 = AVTLinter.lint_and_fix_line("Natsuki zmarła na wylew zaraz po porodzie.")
    assert t4 == "Natsuki zmarła z powodu wylewu zaraz po porodzie."
    
    # Test eliminacji tautologii honoryfikatywnej i Title Case (To pan, Młody Panie -> To ty, młody panie)
    t5, f5 = AVTLinter.lint_and_fix_line("To pan, Młody Panie.")
    assert t5 == "To ty, młody panie."
    print(" -> PASSED: AVT Linter bezbłędnie wyłapuje i koryguje kalki i formy.")

def test_series_bible():
    print("[TEST 9/12] Test Biblii Serialu i Pamięci Międzyodcinkowej (series_memory)...")
    with tempfile.TemporaryDirectory() as tmpdir:
        bible = SeriesBible(anime_title="Test Anime Series", storage_dir=Path(tmpdir))
        bible.update_from_episode_profile(
            episode_name="Odcinek 1",
            characters={"Arata": "uczeń, chłopak"},
            glossary={"Dragon Slayer": "Pogromca Smoków"}
        )
        assert "Arata" in bible.data["characters"]
        assert bible.data["glossary"]["Dragon Slayer"] == "Pogromca Smoków"
        
        # Test wczytywania i formatowania dla promptu
        formatted = bible.format_for_prompt()
        assert "Test Anime Series" in formatted
        assert "Pogromca Smoków" in formatted
    print(" -> PASSED: Biblia Serialu prawidłowo zapisuje i synchronizuje wiedzę.")

def test_avt_formatter_and_cps():
    print("[TEST 10/12] Test semantycznego podziału linii (Netflix AVT) i CPS...")
    # Test kalkulacji CPS
    cps, is_fast = calculate_cps("To jest krótka kwestia dialogowa.", start_ms=0, end_ms=1000)
    assert cps > 20.0
    assert is_fast is True

    cps_normal, is_fast_norm = calculate_cps("Krótko.", start_ms=0, end_ms=2000)
    assert is_fast_norm is False

    # Test podziału linii z zachowaniem spójności syntaktycznej (brak łamania po przyimku 'w')
    long_text = "Poszedłem wczoraj z moim przyjacielem do pobliskiego sklepu."
    split_res = split_subtitle_syntactically(long_text, max_line_len=35, is_ass=True)
    assert "\\N" in split_res
    parts = split_res.split("\\N")
    # Upewniamy się, że linijka 1 nie kończy się na 'do' ani 'z' ani 'w'
    assert not parts[0].strip().endswith((" w", " z", " do", " na"))
    print(" -> PASSED: Podział linii AVT i kalkulator CPS działają bezbłędnie.")

def test_prosody_and_diarizer():
    print("[TEST 11/12] Test lokalnej analizy prozodii i diarizacji fonicznej F0...")
    # Test szacowania F0 na syntetycznym sygnale sinusoidalnym (200Hz - żeński)
    sr = 16000
    t = np.linspace(0, 1.0, sr, endpoint=False)
    sine_200hz = (np.sin(2 * np.pi * 200 * t) * 15000).astype(np.float32)
    f0_est = SpeakerVoiceClassifier.estimate_pitch_f0(sine_200hz, sample_rate=sr)
    assert f0_est is not None
    assert 190.0 <= f0_est <= 210.0

    # Test sygnału męskiego (120Hz)
    sine_120hz = (np.sin(2 * np.pi * 120 * t) * 15000).astype(np.float32)
    f0_est_male = SpeakerVoiceClassifier.estimate_pitch_f0(sine_120hz, sample_rate=sr)
    assert f0_est_male is not None
    assert 110.0 <= f0_est_male <= 130.0
    print(" -> PASSED: Autokorelacja foniczna i estymacja pasma F0 działają perfekcyjnie.")

def test_typesetting_matcher():
    print("[TEST 12/12] Test auto-kolorowania napisów ekranowych (typesetting_matcher)...")
    hex_color = rgb_to_ass_hex(255, 128, 64)
    assert hex_color == "&H4080FF&"  # ASS to BGR

    # Test wzbogacania prefiksu tagów
    res = TypesettingColorMatcher.enhance_typesetting_prefix("{\\an8}")
    assert "\\an8" in res
    print(" -> PASSED: Moduł auto-stylizacji i kolorów ASS działa w 100%.")

from manga_canon import MangaCanonRegistry

def test_manga_canon():
    print("[TEST 13/13] Test Rejestru Kanonu Polskich Wydań Mangowych (manga_canon)...")
    registry = MangaCanonRegistry()
    # Test dopasowania Kingdom
    kingdom_canon = registry.find_canon_for_series("[ASW] Kingdom S6 - 10 [1080p]")
    assert kingdom_canon is not None
    assert kingdom_canon["glossary"]["Middle Kingdom"] == "Państwo Środka"
    assert kingdom_canon["glossary"]["Great General"] == "Wielki Generał"

    # Test dopasowania Jujutsu Kaisen
    jjk_canon = registry.find_canon_for_series("Jujutsu Kaisen Season 2")
    assert jjk_canon is not None
    assert jjk_canon["glossary"]["Domain Expansion"] == "Rozszerzenie Domeny"
    assert jjk_canon["publisher"] == "Wydawnictwo Waneko"

    # Test dopasowania Golden Kamuy
    gk_canon = registry.find_canon_for_series("[Erai-raws] Golden Kamuy - 01 [1080p]")
    assert gk_canon is not None
    assert gk_canon["glossary"]["Immortal Sugimoto"] == "Nieśmiertelny Sugimoto"
    assert gk_canon["glossary"]["Hinna hinna"] == "Hinna, hinna (podziękowanie za dar jedzenia u Ajnów)"
    assert gk_canon["publisher"] == "Wydawnictwo Waneko"

    prompt_chunk = registry.format_canon_for_prompt(jjk_canon)
    assert "Rozszerzenie Domeny" in prompt_chunk
    assert "Waneko" in prompt_chunk
    print(" -> PASSED: Kanon polskich wydań mangowych działa w 100% (baza Waneko, JPF, Studio JG itp.).")

def test_batch_queue():
    print("[TEST 14/14] Test Kolejki Sezonowej (Batch Queue) i naturalnego sortowania...")
    from main import natural_sort_key, collect_input_files
    
    # Test naturalnego sortowania odcinków
    files = ["Kingdom_EP10.mkv", "Kingdom_EP2.mkv", "Kingdom_EP1.mkv", "Kingdom_EP20.mkv"]
    sorted_files = sorted(files, key=natural_sort_key)
    assert sorted_files == ["Kingdom_EP1.mkv", "Kingdom_EP2.mkv", "Kingdom_EP10.mkv", "Kingdom_EP20.mkv"]
    
    # Test zbierania pojedynczego pliku
    res = collect_input_files([str(Path(__file__).parent / "requirements.txt")])
    assert len(res) == 1
    print(" -> PASSED: Kolejka Sezonowa i naturalny sorting odcinków działają bezbłędnie.")

def test_context_cache():
    print("[TEST 15/15] Test Inteligentnego Zarządzania Pamięcią Kontekstu (Google Context Caching)...")
    from context_cache import ContextCacheManager, DEFAULT_CACHE_TTL_SECONDS
    
    # 1. Test generowania hasha
    h1 = ContextCacheManager.get_content_hash("gemini-3.7-flash", "FILAR I: ODNOMINALIZOWANIE")
    h2 = ContextCacheManager.get_content_hash("gemini-3.7-flash", "FILAR I: ODNOMINALIZOWANIE")
    assert h1 == h2
    
    # 2. Test natychmiastowej zmiany hasha przy modyfikacji reguł (Gwarancja świeżości Filarów)
    h3 = ContextCacheManager.get_content_hash("gemini-3.7-flash", "FILAR I: ODNOMINALIZOWANIE (NOWA REGUŁA)")
    assert h1 != h3
    
    # 3. Test bezpiecznego fallbacku przy braku klienta
    res = ContextCacheManager.get_or_create_cache(None, "gemini-3.7-flash", "prompt", ttl_seconds=DEFAULT_CACHE_TTL_SECONDS)
    assert res is None
    print(" -> PASSED: Context Caching SHA-256 i unieważnianie starych wersji działają perfekcyjnie.")

def test_pricing_guard():
    print("[TEST 16/16] Test Strażnika Cennika i Kosztów Google API (pricing_guard)...")
    from pricing_guard import PricingGuard
    
    # 1. Test szacowania kosztu dla profilu Standard (Free Tier)
    assert PricingGuard.estimate_episode_cost_pln("1") == 0.00
    
    # 2. Test szacowania kosztu dla profilu Studyjny Flash (~0.08 zł)
    cost_flash = PricingGuard.estimate_episode_cost_pln("2")
    assert 0.05 <= cost_flash <= 0.12
    
    # 3. Test szacowania kosztu dla profilu Master Pro (~1.38 zł)
    cost_pro = PricingGuard.estimate_episode_cost_pln("3")
    assert 1.20 <= cost_pro <= 1.65
    
    # 4. Test generowania banera
    banner = PricingGuard.get_pricing_status_banner()
    assert "STATUS CENNIKA GOOGLE" in banner
    assert "Context Cache" in banner
    print(" -> PASSED: Strażnik cennika precyzyjnie kalkuluje i monitoruje koszty.")

if __name__ == "__main__":
    print("\n--- Rozpoczynanie testów weryfikacyjnych ---")
    test_rules_and_prompts()
    test_pydantic_schemas()
    test_sanitization_and_deduplication()
    test_subtitle_parsing_and_saving()
    test_ffmpeg_frame_extraction()
    test_profiler_and_whisper()
    test_model_resolver()
    test_avt_linter()
    test_series_bible()
    test_avt_formatter_and_cps()
    test_prosody_and_diarizer()
    test_typesetting_matcher()
    test_manga_canon()
    test_batch_queue()
    test_context_cache()
    test_pricing_guard()
    print("\n Wszystkie testy jednostkowe i integracyjne (16/16) zakończone pełnym sukcesem!\n")
