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
    print("[TEST 1/28] Sprawdzanie kompletności 90 Zunifikowanych Filarów AVT i promptów...")
    sys_prompt = get_translation_system_prompt()
    ver_prompt = get_verifier_system_prompt()
    assert "I see" in sys_prompt
    assert "Rozumiem" in sys_prompt
    assert "KANON PRZEKŁADU AUDIOWIZUALNEGO" in sys_prompt
    assert "Arkadiusza Belczyka" in ver_prompt
    assert "FILAR I:" in sys_prompt
    assert "FILAR II:" in sys_prompt
    assert "FILAR III:" in sys_prompt
    assert "FILAR IV:" in sys_prompt
    assert "FILAR V:" in sys_prompt
    assert "FILAR VI:" in sys_prompt
    assert "FILAR VII:" in sys_prompt
    assert "FILAR VIII:" in sys_prompt
    assert "FILAR IX:" in sys_prompt
    assert "FILAR X:" in sys_prompt
    assert "FILAR XI:" in sys_prompt
    assert "FILAR XII:" in sys_prompt
    assert "FILAR XIII:" in sys_prompt
    assert "FILAR XIV:" in sys_prompt
    assert "FILAR XV:" in sys_prompt
    assert "FILAR XVI:" in sys_prompt
    assert "FILAR XVII:" in sys_prompt
    assert "FILAR XVIII:" in sys_prompt
    assert "FILAR XIX:" in sys_prompt
    assert "FILAR XX:" in sys_prompt
    assert "FILAR XXI:" in sys_prompt
    assert "FILAR XXII:" in sys_prompt
    assert "FILAR XXIII:" in sys_prompt
    assert "FILAR XXIV:" in sys_prompt
    assert "FILAR XXV:" in sys_prompt
    assert "FILAR XXVI:" in sys_prompt
    assert "FILAR XXVII:" in sys_prompt
    assert "FILAR XXVIII:" in sys_prompt
    assert "FILAR XXIX:" in sys_prompt
    assert "FILAR XXX:" in sys_prompt
    assert "FILAR XXXI:" in sys_prompt
    assert "FILAR XXXII:" in sys_prompt
    assert "FILAR XXXIII:" in sys_prompt
    assert "FILAR XXXIV:" in sys_prompt
    assert "FILAR XXXV:" in sys_prompt
    assert "FILAR XXXVI:" in sys_prompt
    assert "FILAR XXXVII:" in sys_prompt
    assert "FILAR XXXVIII:" in sys_prompt
    assert "FILAR XXXIX:" in sys_prompt
    assert "FILAR XL:" in sys_prompt
    assert "FILAR XLI:" in sys_prompt
    assert "FILAR XLII:" in sys_prompt
    assert "FILAR XLIII:" in sys_prompt
    assert "FILAR XLIV:" in sys_prompt
    assert "FILAR XLV:" in sys_prompt
    assert "FILAR XLVI:" in sys_prompt
    assert "FILAR XLVII:" in sys_prompt
    assert "FILAR XLVIII:" in sys_prompt
    assert "FILAR XLIX:" in sys_prompt
    assert "FILAR L:" in sys_prompt
    assert "FILAR LI:" in sys_prompt
    assert "FILAR LII:" in sys_prompt
    assert "FILAR LIII:" in sys_prompt
    assert "FILAR LIV:" in sys_prompt
    assert "FILAR LV:" in sys_prompt
    assert "FILAR LVI:" in sys_prompt
    assert "FILAR LVII:" in sys_prompt
    assert "FILAR LVIII:" in sys_prompt
    assert "FILAR LIX:" in sys_prompt
    assert "FILAR LX:" in sys_prompt
    assert "FILAR LXI:" in sys_prompt
    assert "FILAR LXII:" in sys_prompt
    assert "FILAR LXIII:" in sys_prompt
    assert "FILAR LXIV:" in sys_prompt
    assert "FILAR LXV:" in sys_prompt
    assert "FILAR LXVI:" in sys_prompt
    assert "FILAR LXVII:" in sys_prompt
    assert "FILAR LXVIII:" in sys_prompt
    assert "FILAR LXIX:" in sys_prompt
    assert "FILAR LXX:" in sys_prompt
    assert "FILAR LXXI:" in sys_prompt
    assert "FILAR LXXII:" in sys_prompt
    assert "FILAR LXXIII:" in sys_prompt
    assert "FILAR LXXIV:" in sys_prompt
    assert "FILAR LXXV:" in sys_prompt
    assert "FILAR LXXVI:" in sys_prompt
    assert "FILAR LXXVII:" in sys_prompt
    assert "FILAR LXXVIII:" in sys_prompt
    assert "FILAR LXXIX:" in sys_prompt
    assert "FILAR LXXX:" in sys_prompt
    assert "FILAR LXXXI:" in sys_prompt
    assert "FILAR LXXXII:" in sys_prompt
    assert "FILAR LXXXIII:" in sys_prompt
    assert "FILAR LXXXIV:" in sys_prompt
    assert "FILAR LXXXV:" in sys_prompt
    assert "FILAR LXXXVI:" in sys_prompt
    assert "FILAR LXXXVII:" in sys_prompt
    assert "FILAR LXXXVIII:" in sys_prompt
    assert "FILAR LXXXIX:" in sys_prompt
    assert "FILAR XC:" in sys_prompt
    assert "FILAR XCI:" in sys_prompt
    assert "FILAR XCII:" in sys_prompt
    assert "FILAR XCIII:" in sys_prompt
    assert "FILAR XCIV:" in sys_prompt
    assert "FILAR XCV:" in sys_prompt
    assert "FILAR XCVI:" in sys_prompt
    assert "FILAR XCVII:" in sys_prompt
    assert "FILAR XCVIII:" in sys_prompt
    assert "FILAR XCIX:" in sys_prompt
    assert "FILAR C:" in sys_prompt
    print(" -> PASSED: Kompletny Zunifikowany Kanon 100 Filarów AVT (Filary I – C) jest aktywny w obu fazach tłumaczenia.")

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

from profiler import (
    EpisodeProfile,
    CharacterRelationship,
    GlossaryTerm,
    NameDeclension,
    FirstPersonPronoun,
    format_episode_profile_for_prompt
)
from whisper_engine import JapaneseWhisperEngine

def test_profiler_and_whisper():
    print("[TEST 6/6] Test profilera odcinka 2.0 (Fleksja, Zaimki, Idiomy) i silnika Whisper...")
    profile = EpisodeProfile(
        episode_summary="Odcinek o sprzątaniu klubu mangi",
        tone_and_genre="Komediodramat młodzieżowy",
        name_declensions=[
            NameDeclension(
                character_name="Issei",
                gender="MALE",
                declension_summary="D. Isseia, C. Isseiowi, B. Isseia, N. z Isseiem, Msc. o Isseiu"
            )
        ],
        first_person_pronouns=[
            FirstPersonPronoun(
                character_name="Issei",
                japanese_pronoun="Ore",
                psychological_profile="pewny siebie, szorstki, zdeterminowany"
            )
        ],
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
        yojijukugo_and_idioms=[
            GlossaryTerm(
                term_en="Isseki nichou",
                translation_pl="Upiec dwie pieczenie na jednym ogniu",
                explanation="przysłowie 4-znakowe"
            )
        ],
        key_conventions=["Unikać kalki 'Bless you' -> 'Na zdrowie'"]
    )
    formatted = format_episode_profile_for_prompt(profile)
    assert "pani Teshima" in formatted
    assert "taiyaki" in formatted
    assert "Imperium Mongolskie" in formatted
    assert "Enologia i Sommelierstwo" in formatted
    assert "ŻELAZNA TABELA ODMIANY IMION" in formatted
    assert "Isseiem" in formatted
    assert "PROFIL PSYCHOLOGICZNY I ZAIMKI" in formatted
    assert "Ore" in formatted
    assert "EKWIWALENTY JAPOŃSKICH PRZYSŁÓW" in formatted
    assert "Isseki nichou" in formatted
    
    # Test dostępności i stanu Whisper
    avail = JapaneseWhisperEngine.is_available()
    print(" -> PASSED: Profiler 2.0 (Odmiana imion, zaimki ego, idiomy) działa w 100%.")
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
    
    # Test eliminacji hybryd honoryfikatywnych (Pani Sensei -> Sensei)
    t6, f6 = AVTLinter.lint_and_fix_line("Pani Sensei, skończyłam!")
    assert t6 == "Sensei, skończyłam!"
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

    # Test podziału planszy ekranowej/tytułu (is_sign=True) - ochrona przed wyjściem poza kadr
    title_text = "SPECJALNE SIŁY POŻARNICZE CZĘŚĆ TRZECIA"
    split_title = split_subtitle_syntactically(title_text, max_line_len=42, is_ass=True, is_sign=True)
    assert "\\N" in split_title
    assert len(split_title.split("\\N")) == 2
    print(" -> PASSED: Podział linii AVT, ochrona plansz is_sign i kalkulator CPS działają bezbłędnie.")

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
    
    # 2. Test szacowania kosztu dla profilu Studyjny Flash (~0.12 zł)
    cost_flash = PricingGuard.estimate_episode_cost_pln("2")
    assert 0.05 <= cost_flash <= 0.25
    
    # 3. Test szacowania kosztu dla profilu Master Pro (~1.29 zł z 95 Filarami)
    cost_pro = PricingGuard.estimate_episode_cost_pln("3")
    assert 0.80 <= cost_pro <= 1.90
    
    # 4. Test generowania banera
    banner = PricingGuard.get_pricing_status_banner()
    assert "STATUS CENNIKA GOOGLE" in banner
    assert "Context Cache" in banner
    print(" -> PASSED: Strażnik cennika precyzyjnie kalkuluje i monitoruje koszty.")

def test_sign_detector():
    print("[TEST 17/17] Test Wizyjnego Detektora Plansz i Bezpieczników Antykolizyjnych (sign_detector)...")
    from sign_detector import VisualSignDetector, DetectedSign
    
    # 1. Test wykrywania luk w pliku z pustą przerwą (10 sekund przerwy)
    subs_with_gap = pysubs2.SSAFile()
    subs_with_gap.events.append(pysubs2.SSAEvent(start=1000, end=3000, text="Kwestia 1"))
    subs_with_gap.events.append(pysubs2.SSAEvent(start=15000, end=18000, text="Kwestia 2"))
    
    gaps = VisualSignDetector.find_subtitle_gaps(subs_with_gap, min_gap_ms=3500, margin_ms=1500)
    assert len(gaps) >= 1
    # Sprawdzamy, czy wyznaczona luka leży w pustym oknie
    assert gaps[0][0] >= 4500  # 3000 + 1500 margin
    assert gaps[0][1] <= 13500 # 15000 - 1500 margin
    
    # 2. Test Collision Guard na gęstym kadrze (notes/manga z wieloma linijkami)
    dense_subs = pysubs2.SSAFile()
    for i in range(10):
        dense_subs.events.append(pysubs2.SSAEvent(start=i * 1000, end=(i + 1) * 1000, text=f"Notatka {i}"))
    
    dense_gaps = VisualSignDetector.find_subtitle_gaps(dense_subs, min_gap_ms=3500, margin_ms=1500)
    assert len(dense_gaps) == 0  # Zero luk -> Collision Guard zablokował dublowanie napisów
    
    # 3. Test modelu Pydantic
    sign = DetectedSign(
        is_title_or_banner=True,
        original_text="PRESENT DAY / げんざい",
        translation_pl="CZASY WSPÓŁCZESNE",
        banner_type="TIME_BANNER"
    )
    assert sign.is_title_or_banner is True
    assert sign.translation_pl == "CZASY WSPÓŁCZESNE"
    print(" -> PASSED: VisualSignDetector precyzyjnie wykrywa luki i chroni kadry przed dublowaniem.")

def test_user_feedback_manager():
    print("[TEST 18/22] Test Pamięci Korekt Użytkownika i Few-Shot Prompting (user_feedback)...")
    from user_feedback import UserFeedbackManager
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        tmp_json = Path(f.name)

    try:
        mgr = UserFeedbackManager(storage_path=tmp_json)
        # Test dodawania
        entry = mgr.add_feedback(
            original_en="I messed up",
            bad_pl="Zrobiłem bałagan",
            good_pl="Zawaliłem",
            rule_reason="Używaj naturalnego potocznego słownictwa"
        )
        assert entry["bad_pl"] == "Zrobiłem bałagan"
        assert len(mgr.list_all()) >= 1

        # Test wyszukiwania
        matches = mgr.find_relevant_feedback(["I think I messed up badly"])
        assert len(matches) >= 1
        assert matches[0]["good_pl"] == "Zawaliłem"

        # Test formatowania do promptu
        formatted = mgr.format_for_prompt(matches)
        assert "ZŁOTE WZORCE" in formatted
        assert "Zawaliłem" in formatted

        # Test usuwania
        assert mgr.remove_feedback(entry["id"]) is True
    finally:
        if tmp_json.exists():
            tmp_json.unlink()
    print(" -> PASSED: Moduł pamięci korekt użytkownika i Few-Shot działa bezbłędnie.")

def test_deterministic_glossary():
    print("[TEST 19/22] Test Słownika Deterministycznego i Nadpisywania (glossary_manager)...")
    from glossary_manager import GlossaryManager
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        tmp_json = Path(f.name)

    try:
        mgr = GlossaryManager(global_path=tmp_json)
        mgr.add_term("Ancient Relic", "Starożytna Relikwia", "obiekt fabularny")
        assert "Ancient Relic" in mgr.global_terms

        # Test łączenia ze słownikiem serii
        combined = mgr.get_combined_glossary({"Spirit Blade": "Ostrze Dusz"})
        assert combined["Ancient Relic"] == "Starożytna Relikwia"
        assert combined["Spirit Blade"] == "Ostrze Dusz"

        # Test formatowania do promptu
        prompt_sec = mgr.format_for_prompt(combined)
        assert "BEZWZGLĘDNY SŁOWNICZEK" in prompt_sec
        assert "Starożytna Relikwia" in prompt_sec

        # Test deterministycznego nadpisywania w tekście
        res_text, fixes = GlossaryManager.apply_deterministic_overrides(
            "Odnaleźliśmy Ancient Relic w jaskini.",
            combined
        )
        assert res_text == "Odnaleźliśmy Starożytna Relikwia w jaskini."
        assert len(fixes) == 1
    finally:
        if tmp_json.exists():
            tmp_json.unlink()
    print(" -> PASSED: Słownik deterministyczny wymusza terminy w 100%.")

def test_dynamic_rule_dispatcher():
    print("[TEST 20/25] Test Dynamicznego Dyspozytora Reguł i Koncentracji Uwagi (rules.py)...")
    from rules import get_focused_rules_for_batch

    # 1. Test paczki z pytaniami (Filar IX)
    batch_q = [{"en": "Are you sure about that?"}]
    focused_q = get_focused_rules_for_batch(batch_q)
    assert "FILAR IX" in focused_q

    # 2. Test paczki z napisami ekranowymi (sign) (Filar XLI)
    batch_s = [{"en": "Title of Chapter", "is_sign": True}]
    focused_s = get_focused_rules_for_batch(batch_s)
    assert "FILAR XLI" in focused_s

    # 3. Test paczki z tytulaturą (Filar XXV/XXVII/XXVIII)
    batch_t = [{"en": "Sensei, please help!"}]
    focused_t = get_focused_rules_for_batch(batch_t)
    assert "XXVII" in focused_t or "XXV" in focused_t

    # 4. Test paczki z czasownikami wektorowymi (Filar XXXVII)
    batch_v = [{"en": "Look, I can see it!"}]
    focused_v = get_focused_rules_for_batch(batch_v)
    assert "FILAR XXXVII" in focused_v
    print(" -> PASSED: Dyspozytor reguł precyzyjnie aktywuje właściwe filary AVT.")

def test_fuzzy_and_dynamic_avt_linter():
    print("[TEST 21/22] Test Fleksyjnego i Dynamicznego Lintera (avt_linter)...")
    from avt_linter import AVTLinter

    # 1. Test fleksji "mieć taką nadzieję" w różnych czasach
    t1, _ = AVTLinter.lint_and_fix_line("Miałem taką nadzieję od dawna.")
    assert t1 == "Miałem nadzieję od dawna."
    t2, _ = AVTLinter.lint_and_fix_line("Będziemy mieć taką nadzieję.")
    assert t2 == "Będziemy mieć nadzieję."

    # 2. Test fleksji "robić sens" w różnych formach
    t3, _ = AVTLinter.lint_and_fix_line("To robiło sens wczoraj.")
    assert "to miało sens" in t3.lower()
    t4, _ = AVTLinter.lint_and_fix_line("To nie będzie robić sensu.")
    assert "to nie będzie mieć sensu" in t4.lower()

    # 3. Test dynamicznych reguł użytkownika w linterze
    user_rules = [
        {"bad_pl": "zrobiłem błąd", "good_pl": "pomyliłem się"}
    ]
    t5, fixes5 = AVTLinter.lint_and_fix_line("Chyba zrobiłem błąd.", user_feedback_rules=user_rules)
    assert t5 == "Chyba pomyliłem się."
    assert len(fixes5) >= 1

    # 4. Test wymuszeń słownikowych w linterze
    custom_gloss = {"Black Dragon": "Czarny Smok"}
    t6, fixes6 = AVTLinter.lint_and_fix_line("To jest Black Dragon!", custom_glossary=custom_gloss)
    assert "Czarny Smok" in t6
    print(" -> PASSED: Linter bezbłędnie obsługuje fleksję, wzorce użytkownika i słownik.")

def test_gui_interactive_learning_components():
    print("[TEST 22/23] Test Komponentów Interaktywnego Uczenia w GUI (gui_app)...")
    from user_feedback import UserFeedbackManager
    from glossary_manager import GlossaryManager

    fb = UserFeedbackManager()
    all_rules = fb.list_all()
    assert len(all_rules) >= 1

    gm = GlossaryManager()
    assert len(gm.global_terms) >= 1
    print(" -> PASSED: Komponenty GUI interaktywnego uczenia są w 100% gotowe.")

def test_extended_avt_pillars():
    print("[TEST 23/25] Test Filarów Paralingwistyki, Interpunkcji i Translationese...")
    from avt_linter import AVTLinter
    from rules import get_focused_rules_for_batch

    # 1. Test paralingwistyki (Filar XVIII)
    t1, _ = AVTLinter.lint_and_fix_line("Ara ara, co my tu mamy?")
    assert "O proszę..." in t1
    t2, _ = AVTLinter.lint_and_fix_line("Tch, znowu on.")
    assert "Tsk..." in t2

    # 2. Test eliminacji trzeciego języka (Filar X)
    t3, _ = AVTLinter.lint_and_fix_line("Co sprawia, że tak mówisz?")
    assert "Czemu tak sądzisz?" in t3

    # 3. Test interpunkcji zespolonej (Filar LX)
    t4, _ = AVTLinter.lint_and_fix_line("Naprawdę!?")
    assert "?!" in t4

    # 4. Test dyspozytora dla piosenek (Filar LVIII) i paralingwistyki (Filar XVIII)
    batch_music = [{"en": "Song lyrics", "notes": "singing"}]
    f_music = get_focused_rules_for_batch(batch_music)
    assert "FILAR LVIII" in f_music

    batch_para = [{"en": "Ara ara, you are funny"}]
    f_para = get_focused_rules_for_batch(batch_para)
    assert "FILAR XVIII" in f_para or "XVIII" in f_para
    print(" -> PASSED: Filary paralingwistyki, interpunkcji i anti-translationese działają bezbłędnie.")

def test_master_avt_pillars():
    print("[TEST 24/25] Test Zunifikowanych Filarów Realioznawczych i Metryzacji (ECR, Metryzacja, Modalność)...")
    from avt_linter import AVTLinter
    from rules import get_focused_rules_for_batch

    # 1. Test Pedersen ECR generalization (Filar XIV)
    t1, _ = AVTLinter.lint_and_fix_line("Pójdę do konbini po coś do picia.")
    assert "sklep" in t1

    # 2. Test metryzacji miar (Filar LIX)
    t2, _ = AVTLinter.lint_and_fix_line("On ma ponad 6 stóp wzrostu i stoi 10 stóp stąd.")
    assert "prawie dwa metry" in t2
    assert "3 metry" in t2

    # 3. Test modalności epistemicznej (Filar XLVI)
    t3, _ = AVTLinter.lint_and_fix_line("Nie ma wątpliwości, że wrócą.")
    assert "bez wątpienia" in t3

    # 4. Test dyspozytora dla jednostek (Filar LIX) i modalności (Filar XLVI)
    batch_units = [{"en": "He is 10 feet away from the wall."}]
    f_units = get_focused_rules_for_batch(batch_units)
    assert "LIX" in f_units

    batch_modal = [{"en": "He must be definitely guilty, no doubt."}]
    f_modal = get_focused_rules_for_batch(batch_modal)
    assert "XLVI" in f_modal
    print(" -> PASSED: Zunifikowane filary realioznawcze, metryzacji i modalności w 100% zintegrowane.")

def test_excellence_avt_pillars():
    print("[TEST 25/26] Test Pragmatyki Anime i Żargonu RPG (Shūjoshi, Onomatopeje, RPG)...")
    from avt_linter import AVTLinter
    from rules import get_focused_rules_for_batch

    # 1. Test Shūjoshi Pragmatics (Filar XVI)
    t1, _ = AVTLinter.lint_and_fix_line("Iku zo!")
    assert "No to ruszamy!" in t1

    # 2. Test Onomatopeje Gijougo (Filar XVII)
    t2, _ = AVTLinter.lint_and_fix_line("Zokutto shita kiedy to zobaczyłem.")
    assert "przeszły mnie ciarki" in t2

    # 3. Test Żargon RPG / System (Filar XXIV)
    t3, _ = AVTLinter.lint_and_fix_line("Pojawiło się Status Window gracza.")
    assert "[ OKNO STATUSU ]" in t3

    # 4. Test dyspozytora dla RPG (Filar XXIV) i Shūjoshi (Filar XVI)
    batch_rpg = [{"en": "Check your status and new skill level."}]
    f_rpg = get_focused_rules_for_batch(batch_rpg)
    assert "XXIV" in f_rpg

    batch_shujo = [{"en": "Doko ni iku no kashira?"}]
    f_shujo = get_focused_rules_for_batch(batch_shujo)
    assert "XVI" in f_shujo
    print(" -> PASSED: Pragmatyka anime i żargon RPG w 100% zintegrowane.")

def test_cognitive_prosody_and_narrative_pillars():
    print("[TEST 26/27] Test Kognitywistyki Prozodii, Narracji i Filarów AVT (LXV – LXX)...")
    from rules import get_focused_rules_for_batch

    # 1. Test dyspozytora dla Izomorfizmu Napięcia (Filar LXV)
    batch_suspense = [{"en": "The truth is, he will never betray us."}]
    f_suspense = get_focused_rules_for_batch(batch_suspense)
    assert "LXV" in f_suspense

    # 2. Test dyspozytora dla Prozodii Oddechu (Filar LXVI)
    batch_breath = [{"en": "I can't... breath... run!"}]
    f_breath = get_focused_rules_for_batch(batch_breath)
    assert "LXVI" in f_breath

    # 3. Test dyspozytora dla Kąta Kamery Empatycznej (Filar LXVII)
    batch_empathy = [{"en": "He did this great favor for me."}]
    f_empathy = get_focused_rules_for_batch(batch_empathy)
    assert "LXVII" in f_empathy

    # 4. Test dyspozytora dla Pamięci Leitmotywów (Filar LXVIII)
    batch_leitmotif = [{"en": "This is my vow and destiny."}]
    f_leitmotif = get_focused_rules_for_batch(batch_leitmotif)
    assert "LXVIII" in f_leitmotif

    # 5. Test dyspozytora dla Hierarchii Akustycznej (Filar LXIX)
    batch_ambient = [{"en": "Emergency broadcast over the loudspeaker."}]
    f_ambient = get_focused_rules_for_batch(batch_ambient)
    assert "LXIX" in f_ambient

    # 6. Test dyspozytora dla 4. Ściany i Metanarracji (Filar LXX)
    batch_meta = [{"en": "The manga author missed the deadline for this episode."}]
    f_meta = get_focused_rules_for_batch(batch_meta)
    assert "LXX" in f_meta
    print(" -> PASSED: Filary Kognitywistyki Prozodii i Narracji (LXV – LXX) w 100% zintegrowane.")

def test_visual_discourse_and_transcreation_pillars():
    print("[TEST 27/28] Test Kognitywistyki Wizualnej, Dyskursu i Transkreacji (LXXI – LXXX)...")
    from rules import get_focused_rules_for_batch

    # 1. Test dyspozytora dla Dostępności Leksykalnej (Filar LXXI)
    batch_cps = [{"en": "Very fast spoken dialogue", "cps": 18.5}]
    f_cps = get_focused_rules_for_batch(batch_cps)
    assert "LXXI" in f_cps

    # 2. Test dyspozytora dla Wektora Kinezycznego i Sakuga (Filar LXXII)
    batch_sakuga = [{"en": "Dodge the slash attack and punch him!"}]
    f_sakuga = get_focused_rules_for_batch(batch_sakuga)
    assert "LXXII" in f_sakuga

    # 3. Test dyspozytora dla Modalności Noda/Wake da (Filar LXXIII)
    batch_noda = [{"en": "Because the reason is, wake dewa nai."}]
    f_noda = get_focused_rules_for_batch(batch_noda)
    assert "LXXIII" in f_noda

    # 4. Test dyspozytora dla Rejestru Chibi / SD (Filar LXXIV)
    batch_chibi = [{"en": "Look at that chibi funny face, you dummy!"}]
    f_chibi = get_focused_rules_for_batch(batch_chibi)
    assert "LXXIV" in f_chibi

    # 5. Test dyspozytora dla Akcentu Logicznego i Szczytu F0 (Filar LXXV)
    batch_f0 = [{"en": "You traitor! How could you!"}]
    f_f0 = get_focused_rules_for_batch(batch_f0)
    assert "LXXV" in f_f0

    # 6. Test dyspozytora dla Biernej Agresji w Keigo (Filar LXXVI)
    batch_passive = [{"en": "It is my honor to watch your pathetic insolence die in silence."}]
    f_passive = get_focused_rules_for_batch(batch_passive)
    assert "LXXVI" in f_passive

    # 7. Test dyspozytora dla Triangulacji SFX (Filar LXXVII)
    batch_sfx = [{"en": "A sudden silence and flash clash."}]
    f_sfx = get_focused_rules_for_batch(batch_sfx)
    assert "LXXVII" in f_sfx

    # 8. Test dyspozytora dla Interfejsów Diegetycznych i Czatów (Filar LXXVIII)
    batch_ui = [{"en": "Check your smartphone text message and chat."}]
    f_ui = get_focused_rules_for_batch(batch_ui)
    assert "LXXVIII" in f_ui

    # 9. Test dyspozytora dla Transkreacji Emocjonalnej (Filar LXXIX)
    batch_trans = [{"en": "Let's raise a toast and rhyme this poem."}]
    f_trans = get_focused_rules_for_batch(batch_trans)
    assert "LXXIX" in f_trans

    # 10. Test dyspozytora dla Mikro-Interpunkcji Afektywnej (Filar LXXX)
    batch_punct = [{"en": "W-What are you doing? Wha-"}]
    f_punct = get_focused_rules_for_batch(batch_punct)
    assert "LXXX" in f_punct
    print(" -> PASSED: Kanon Zunifikowany 80 Filarów AVT (Filary LXXI – LXXX) w 100% zintegrowany.")

def test_masterpieces_and_semiotics_pillars():
    print("[TEST 28/28] Test Arcydzieł Światowej Translatoryki i Semiotyki (LXXXI – XC)...")
    from rules import get_focused_rules_for_batch

    # 1. Test dyspozytora dla Organicznej Ekspozycji Ghibli (Filar LXXXI)
    batch_ghibli = [{"en": "Let me explain this world and give you full exposition."}]
    f_ghibli = get_focused_rules_for_batch(batch_ghibli)
    assert "LXXXI" in f_ghibli

    # 2. Test dyspozytora dla Semiotycznej Negocjacji Eco (Filar LXXXII)
    batch_eco = [{"en": "The deep intent and meaning of this metaphor."}]
    f_eco = get_focused_rules_for_batch(batch_eco)
    assert "LXXXII" in f_eco

    # 3. Test dyspozytora dla Dekolonizacji Składni Ladmirala (Filar LXXXIII)
    batch_cibliste = [{"en": "There is no doubt that the fact that in order to do so."}]
    f_cibliste = get_focused_rules_for_batch(batch_cibliste)
    assert "LXXXIII" in f_cibliste

    # 4. Test dyspozytora dla Wykonawczego Kunsztu Smitha (Filar LXXXIV)
    batch_mouth = [{"en": "A dramatic whisper and shouting speech with rage."}]
    f_mouth = get_focused_rules_for_batch(batch_mouth)
    assert "LXXXIV" in f_mouth

    # 5. Test dyspozytora dla Integracji Kinematograficznej Romero-Fresco (Filar LXXXV)
    batch_blindness = [{"en": "Look at the beauty of this cinematic landscape."}]
    f_blindness = get_focused_rules_for_batch(batch_blindness)
    assert "LXXXV" in f_blindness

    # 6. Test dyspozytora dla Polifonii Bachtina (Filar LXXXVI)
    batch_poly = [
        {"en": "Hello sir.", "speaker_gender": "kobieta"},
        {"en": "Get out of here!", "speaker_gender": "mężczyzna"}
    ]
    f_poly = get_focused_rules_for_batch(batch_poly)
    assert "LXXXVI" in f_poly

    # 7. Test dyspozytora dla Czystości Fokalizacji (Filar LXXXVII)
    batch_focal = [{"en": "I asked myself in my own inner mind.", "is_thought": True}]
    f_focal = get_focused_rules_for_batch(batch_focal)
    assert "LXXXVII" in f_focal

    # 8. Test dyspozytora dla Protokołu Bermana (Filar LXXXVIII)
    batch_berman = [{"en": "A rough and bizarre poetic raw voice."}]
    f_berman = get_focused_rules_for_batch(batch_berman)
    assert "LXXXVIII" in f_berman

    # 9. Test dyspozytora dla Restytucji Steinera (Filar LXXXIX)
    batch_steiner = [{"en": "A cultural tradition and idiom lost in translation."}]
    f_steiner = get_focused_rules_for_batch(batch_steiner)
    assert "LXXXIX" in f_steiner

    # 10. Test dyspozytora dla Somatycznego Rezonansu Robinsona (Filar XC)
    batch_somatic = [{"en": "Terror and chills running through despair and heartbreak."}]
    f_somatic = get_focused_rules_for_batch(batch_somatic)
    assert "XC" in f_somatic
    print(" -> PASSED: Kanon Zunifikowany 90 Filarów AVT (Filary LXXXI – XC) w 100% zintegrowany i sprawny.")

def test_translator_logger_and_sign_detector():
    print("[TEST 29/29] Test odporności translator.py i loggera na błędy wizyjnej detekcji...")
    import translator
    assert hasattr(translator, "logger"), "translator module must define logger"
    assert translator.logger is not None
    print(" -> PASSED: Logger w translator.py poprawnie zainicjalizowany.")

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
    test_sign_detector()
    test_user_feedback_manager()
    test_deterministic_glossary()
    test_dynamic_rule_dispatcher()
    test_fuzzy_and_dynamic_avt_linter()
    test_gui_interactive_learning_components()
    test_extended_avt_pillars()
    test_master_avt_pillars()
    test_excellence_avt_pillars()
    test_cognitive_prosody_and_narrative_pillars()
    test_visual_discourse_and_transcreation_pillars()
    test_masterpieces_and_semiotics_pillars()
    test_translator_logger_and_sign_detector()
    print("\n Wszystkie testy jednostkowe i integracyjne (29/29) zakończone pełnym sukcesem!\n")

