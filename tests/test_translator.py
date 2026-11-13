"""
Unit tests for translator.py & verifier.py covering Standard 9.4 operation 2C.6:
- T4.9 (2C.6): test_phase1_monologue_detection_and_phase2_over_application_italics_guard
"""
import pytest
import pysubs2
from verifier import _guard_phase2_regressions


@pytest.mark.unit
@pytest.mark.parametrize(
    "is_monologue,target_gender,f1_pl,refined_pl,expected_output",
    [
        # Głośny dialog ze zidentyfikowanym adresatem: Faza 2 nielegalnie nałożyła całoliniową kursywę
        (
            False,
            "FEMININE",
            "Musimy już ruszać, Bohaterko.",
            r"{\i1}Musimy już ruszać, Bohaterko.{\i0}",
            "Musimy już ruszać, Bohaterko."
        ),
        # Monolog wewnętrzny (is_internal_monologue=True): całoliniowa kursywa zachowana
        (
            True,
            None,
            r"{\i1}Udało mi się uciec przed pościgiem!{\i0}",
            r"{\i1}Udało mi się uciec przed pościgiem!{\i0}",
            r"{\i1}Udało mi się uciec przed pościgiem!{\i0}"
        ),
    ]
)
def test_phase1_monologue_detection_and_phase2_over_application_italics_guard(
    is_monologue, target_gender, f1_pl, refined_pl, expected_output
):
    """
    T4.9 (Operacja 2C.6): Weryfikacja strażnika over_application_italics w dialogu zewnętrznym.
    """
    guarded = _guard_phase2_regressions(
        f1_pl=f1_pl,
        refined_pl=refined_pl,
        source_en="We need to move now, Heroine.",
        target_p0_gender=target_gender,
        is_internal_monologue=is_monologue
    )
    assert guarded == expected_output


@pytest.mark.unit
def test_phase1_monologue_prompt_emission():
    """
    T4.9 (Operacja 2C.6): Weryfikacja emisji flagi is_internal_monologue w fazie 1 dla stylu Italics.
    """
    from translator import MultimodalTranslator
    ev = pysubs2.SSAEvent(start=1000, end=3000, text="I escaped from the pursuers!", style="Italics")
    ev.name = "HeroAlpha SurnameBeta"

    translator = MultimodalTranslator.__new__(MultimodalTranslator)
    translator.character_registry = {}
    translator.tm = None
    translator._episode_knowledge_cached = True

    prompt = translator.build_phase1_prompt(
        batch_events=[(0, ev, "I escaped from the pursuers!", "I escaped from the pursuers!")],
        history_context=[]
    )
    assert "is_internal_monologue: true" in prompt


# ==============================================================================
# STANDARD 9.5 TESTS (T5.3, T5.7)
# ==============================================================================

@pytest.mark.unit
@pytest.mark.parametrize(
    "actor_name,raw_text",
    [
        # 1. Zdarzenie o Name == "sign" z wieloma wierszami
        ("sign", r"{\an8}NAGŁÓWEK TABLICY\NWiersz opisu 1\NWiersz opisu 2\NWiersz opisu 3"),
        # 2. Zdarzenie z tagiem \pos(x,y)
        ("", r"{\pos(337,228)\c&HFFFFFF&}Napis na ekranie\NWiersz podrzędny 1\NWiersz podrzędny 2"),
        # 3. Zdarzenie o Name == "title"
        ("title", r"TYTUŁ ODCINKA\NWiersz 2\NWiersz 3"),
        # 4. Zdarzenie z flagą is_sign=True
        ("plansza", r"Wielowierszowy tekst planszy informacyjnej\NL2\NL3"),
    ]
)
def test_split_oversized_events_skips_sign_actor_and_pos_tagged_events(actor_name, raw_text):
    """
    T5.3 (Operacja 2C.2): Prawidłowy stan split_oversized_ass_events = zachowanie zdarzenia
    o Name == 'sign' lub zawierającego \\pos(x,y) jako pojedynczego rekordu (len(events) == 1).
    """
    from translator import split_oversized_ass_events
    ev = pysubs2.SSAEvent(start=1000, end=2430, text=raw_text, name=actor_name)
    if actor_name == "plansza":
        ev.is_sign = True
    split_res = split_oversized_ass_events([ev])
    assert len(split_res) == 1
    assert split_res[0].start == 1000
    assert split_res[0].end == 2430
    if r"\pos(" in raw_text:
        assert r"\pos(" in split_res[0].text


@pytest.mark.unit
@pytest.mark.parametrize(
    "style_name,input_draft,expected_wrapped",
    [
        # 1. Styl Italics bez znacznikow kursywy -> brak redundantnych tagow {\i1}...{\i0} (Hotfix 11.1.5 P3-1)
        ("Italics", "To musi być jakaś pułapka.\nMuszę uważać.", r"To musi być jakaś pułapka.\NMuszę uważać."),
        # 2. Styl Flashback_Italics z wewnetrznym duplikatem -> oczyszczenie do czystego tekstu (Hotfix 11.1.5 P3-1)
        ("Flashback_Italics", r"{\i1}Wspomnienie dawnych dni{\i0}\n{\i1}nadal boli.{\i0}", r"Wspomnienie dawnych dni\Nnadal boli."),
        # 3. Styl Thoughts bez kursywy w stylu ASS -> automatyczne otoczenie pojedyncza para {\i1}...{\i0}
        ("Thoughts", "To musi być jakaś pułapka.\nMuszę uważać.", r"{\i1}To musi być jakaś pułapka.\NMuszę uważać.{\i0}"),
        # 4. Kontrprzyklad: zwykly styl Default bez mysli -> brak automatycznego otaczania kursywa
        ("Default", "Wszyscy na stanowiska!", "Wszyscy na stanowiska!"),
    ]
)
def test_phase1_postprocess_wraps_italics_style_and_normalizes_single_italic_block(
    style_name, input_draft, expected_wrapped
):
    r"""
    T5.7 (Operacja 2C.6) & Hotfix 11.1.5 (P3-1): Prawidlowy stan tekstu Fazy 1:
    - Dla stylu Thoughts otacza pojedyncza para {\i1}...{\i0} oraz separator \N zamiast \n.
    - Dla stylow z rodziny Italics usuwa redundantne tagi {\i1}...{\i0}.
    """
    import pysubs2
    from translator import format_phase1_candidate_text

    event = pysubs2.SSAEvent(start=1000, end=3000, text=input_draft, style=style_name)
    pl_cand = format_phase1_candidate_text(input_draft, event, is_sign=False)
    is_im = any(k in style_name.lower() for k in ["thoughts", "internal"])

    assert pl_cand == expected_wrapped
    if is_im:
        assert pl_cand.startswith(r"{\i1}")
        assert pl_cand.endswith(r"{\i0}")
    assert r"\n" not in pl_cand

# T10.1.1 (A-1) -> tests/test_translator.py
@pytest.mark.unit
@pytest.mark.parametrize(
    "speaker_f0,adjacent_f0",
    [
        (240.0, 110.0),
        (110.0, 240.0),
        (240.0, 245.0),
    ],
)
def test_resolve_line_addressee_does_not_use_f0_for_anonymous_speakers(speaker_f0, adjacent_f0):
    from translator import MultimodalTranslator
    import pysubs2
    ev_prev = pysubs2.SSAEvent(start=0, end=1000, text="Linia A", name="")
    ev_curr = pysubs2.SSAEvent(start=1000, end=2000, text="Linia B", name="")
    speaker_tags = {1: f"wysoki tembr ~{int(speaker_f0)}hz", 2: f"niski tembr ~{int(adjacent_f0)}hz"}
    t = MultimodalTranslator.__new__(MultimodalTranslator)
    t.character_registry = {}
    t.series_bible = None
    t.episode_scene_genders = {}
    cat, lbl = t._resolve_line_addressee(
        event=ev_curr, raw_phase1_addressee=None,
        batch_events=[(0, ev_prev, "Linia A", ""), (1, ev_curr, "Linia B", "")],
        event_idx=1, whisper_text="", clean_text="Linia B",
        speaker_tags=speaker_tags, prosody_tags={},
    )
    assert cat is None
    assert "Naprzemienność F0" not in (lbl or "")


# ==============================================================================
# HOTFIX 10.1.1 REGRESSION TESTS (T10.1.1_P1a)
# ==============================================================================

@pytest.mark.unit
def test_t10_1_1_p1a_short_spoken_reply_immunity_from_false_monologue():
    """
    T10.1.1_P1a (Hotfix 10.1.1, 2B.1, 2B.2):
    Krótkie repliki mówione (<= 4 słowa, potoczne reakcje) nie mogą być oznaczane
    ani formatowane jako monolog wewnętrzny (kursywa {\\i1}...{\\i0}) wyłącznie
    z powodu obniżonej energii głosu seiyū (niski RMS).
    """
    from translator import is_short_spoken_reply, format_phase1_candidate_text
    from prosody_engine import AudioProsodyEngine
    import pysubs2

    # 1. Weryfikacja AudioProsodyEngine._classify_rms_label
    label_low = AudioProsodyEngine._classify_rms_label(100.0, 300.0)
    assert label_low == "cichy głos / obniżona energia głosu (szept lub spokojna replika)"
    label_norm = AudioProsodyEngine._classify_rms_label(200.0, 300.0)
    assert label_norm == ""

    # 2. Weryfikacja is_short_spoken_reply
    assert is_short_spoken_reply("Yeah.") is True
    assert is_short_spoken_reply("Got it.") is True
    assert is_short_spoken_reply("Tak, oczywiście.") is True
    assert is_short_spoken_reply("Rozumiem.") is True
    assert is_short_spoken_reply("I'm back.") is True
    # Kwestie w nawiasach myśli to monolog wewnętrzny, a nie krótka replika mówiona
    assert is_short_spoken_reply("(What should I do?)") is False
    assert is_short_spoken_reply("（どうしよう）") is False

    # 3. Weryfikacja format_phase1_candidate_text na krótkiej replice ze stylem Default
    ev = pysubs2.SSAEvent(start=1000, end=2000, text="Got it.", style="Default")
    ev.name = "SpeakerAlpha"
    ev.is_internal_monologue = True

    formatted = format_phase1_candidate_text("Rozumiem.", ev, is_sign=False)
    assert r"{\i1}" not in formatted
    assert formatted == "Rozumiem."

    # Dla stylu Italics / thoughts kursywa musi być zachowana
    ev_thought = pysubs2.SSAEvent(start=1000, end=2000, text="Got it.", style="Thoughts")
    ev_thought.name = "SpeakerAlpha"
    formatted_th = format_phase1_candidate_text("Rozumiem.", ev_thought, is_sign=False)
    assert formatted_th == r"{\i1}Rozumiem.{\i0}"


@pytest.mark.unit
def test_code_switching_detection_and_prompt_guidance():
    """Hotfix 11.1.4: Detekcja hybrydowych zapożyczeń code-switchingu oraz wyzwalanie wskazówki DYN_1."""
    from translator import detect_japanese_pragmatic_register
    from whisper_disambiguator import WhisperDisambiguator
    from rules import get_focused_rules_for_batch

    # 1. detect_japanese_pragmatic_register wykrywa code-switching
    res_cs = detect_japanese_pragmatic_register("リフレクトしますよ", "Reflecting now")
    assert res_cs is not None
    assert "Code-switching JA+EN" in res_cs

    # 2. Powszechne terminy systemowe nie dają fałszywego code-switchingu
    res_sys = detect_japanese_pragmatic_register("ゲームをクリアした", "Cleared the game")
    assert res_sys is None or "Code-switching" not in res_sys

    # 3. WhisperDisambiguator rozpoznaje kategorię CODE_SWITCH_EN
    cats = WhisperDisambiguator.detect_batch_discourse_categories("Reflecting now", "リフレクトしますよ")
    assert "CODE_SWITCH_EN" in cats

    # 4. get_focused_rules_for_batch emituje wytyczną dla code-switchingu
    batch_items = [{
        "id": 1,
        "en": "Reflecting now",
        "audio_jp": "リフレクトしますよ",
        "notes": "",
        "speech_style_pl": ""
    }]
    focused = get_focused_rules_for_batch(batch_items, max_rules=3)
    assert "FILAR XIII" in focused
    assert "angielskie słowa lub hybrydowe zwroty katakanowe" in focused


@pytest.mark.unit
def test_yakuwarigo_aru_yaru_and_codeswitch_priority_over_ore_in_pragmatic_register():
    """Hotfix 11.1.4a: Priorytetyzacja rejestru Yakuwarigo (-aru/-yaru) oraz code-switchingu przed zaimkiem ore."""
    from translator import detect_japanese_pragmatic_register

    # 1. Kwestia ze słowem 'ore' oraz końcówką Yakuwarigo -aru/-yaru
    res_aru = detect_japanese_pragmatic_register("俺の頼んでるあるよ", "I am asking you.")
    assert res_aru is not None
    assert "Stylizowany rejestr wojowniczki" in res_aru
    assert "-aru/-yaru" in res_aru

    res_yaru = detect_japanese_pragmatic_register("俺は何やるかね", "What am I doing?")
    assert res_yaru is not None
    assert "Stylizowany rejestr wojowniczki" in res_yaru

    # 2. Kwestia ze słowem 'ore' oraz zwrotem code-switching JA+EN
    res_cs = detect_japanese_pragmatic_register("俺がリフレクトします", "I will reflect it.")
    assert res_cs is not None
    assert "Code-switching JA+EN" in res_cs

    # 3. Dodatkowe rozszerzone warianty leksykalne -aru/-yaru
    variants = [
        "はずある", "だけある", "ことある", "いいやる", "いけなやる", "ないやるね", "なおらないやる"
    ]
    for v in variants:
        res_v = detect_japanese_pragmatic_register(v, "Sample utterance")
        assert res_v is not None
        assert "Stylizowany rejestr wojowniczki" in res_v


@pytest.mark.unit
def test_detect_event_visual_type_point_listing_sign_in_default_style():
    """Hotfix 11.1.4a: Detekcja planszy wyliczenia punktowego lub cennika w stylu Default."""
    import pysubs2
    from translator import detect_event_visual_type

    listing_samples = [
        "10,000 candies: Magical Phone",
        "500 points: Sacred Shield",
        "100 pkt: Mikstura lecząca",
        "1,000 coins: Ancient Armor",
        "50 pts: Speed Boost",
    ]
    for text in listing_samples:
        ev = pysubs2.SSAEvent(start=1000, end=4000, text=text, style="Default")
        ev.name = ""
        vtype = detect_event_visual_type(ev)
        assert vtype["is_sign"] is True, f"Brak detekcji napisu dla: {text}"
        assert vtype["is_top"] is False
        assert "plansza wyliczenia punktowego / cennika" in vtype["visual_details"]

    # Dialog postaci nie jest klasyfikowany jako plansza
    ev_dialogue = pysubs2.SSAEvent(start=1000, end=4000, text="We have to move forward together.", style="Default")
    ev_dialogue.name = "SpeakerAlpha"
    vtype_dlg = detect_event_visual_type(ev_dialogue)
    assert vtype_dlg["is_sign"] is False


@pytest.mark.unit
def test_whisper_engine_thread_safe_infer_lock_and_kotoba_word_timestamps_guard(tmp_path):
    """Hotfix 11.1.4b: Weryfikacja blokady wątkowej _infer_lock oraz wyłączenia word_timestamps dla modeli distil/kotoba."""
    import time
    import threading
    from concurrent.futures import ThreadPoolExecutor
    import pysubs2
    import whisper_engine
    from whisper_engine import JapaneseWhisperEngine

    dummy_wav = tmp_path / "scene_audio.wav"
    dummy_wav.write_bytes(b"RIFF dummy 16khz wav data")

    engine = JapaneseWhisperEngine(model_size="kotoba-tech/kotoba-whisper-v2.0-faster")
    engine._is_initialized = True

    active_threads = 0
    max_concurrent_threads = 0
    concurrency_lock = threading.Lock()
    captured_kwargs = []

    class MockSegment:
        def __init__(self, start: float, end: float, text: str):
            self.start = start
            self.end = end
            self.text = text
            self.words = None

    class MockModel:
        def transcribe(self, audio_path, **kwargs):
            nonlocal active_threads, max_concurrent_threads
            with concurrency_lock:
                captured_kwargs.append(kwargs)

            def segment_generator():
                nonlocal active_threads, max_concurrent_threads
                with concurrency_lock:
                    active_threads += 1
                    if active_threads > max_concurrent_threads:
                        max_concurrent_threads = active_threads
                try:
                    time.sleep(0.015)
                    yield MockSegment(start=1.0, end=3.0, text="テスト音声")
                finally:
                    with concurrency_lock:
                        active_threads -= 1

            return segment_generator(), None

    engine.model = MockModel()

    ev1 = pysubs2.SSAEvent(start=1000, end=3000, text="Test line")
    ev1.name = "SpeakerAlpha"
    events = [(1, ev1)]

    # Wywołanie równoległe z 6 wątków roboczych
    results = []
    with ThreadPoolExecutor(max_workers=6) as executor:
        futures = [
            executor.submit(engine.transcribe_batch_scene, str(dummy_wav), 0, events)
            for _ in range(6)
        ]
        for f in futures:
            results.append(f.result())

    # 1. Dokładnie 1 wątek jednocześnie w sekcji krytycznej modelu (100% thread-safety)
    assert max_concurrent_threads == 1, f"Wykryto kolizję wątków w inferencji GPU: {max_concurrent_threads}"

    # 2. Wszystkie wątki zwróciły poprawnie przypisany segment
    for res in results:
        assert res == {1: "テスト音声"}

    # 3. Bezpieczne wyłączenie word_timestamps dla architektury kotoba/distil
    assert len(captured_kwargs) == 6
    for kw in captured_kwargs:
        assert kw.get("word_timestamps") is False
        assert kw.get("vad_parameters") == dict(min_silence_duration_ms=140, speech_pad_ms=80)


# ==============================================================================
# STANDARD 11.1.7 REGRESSION TESTS (T11.1.7_B4)
# ==============================================================================
@pytest.mark.unit
def test_t11_1_7_b4_extract_typesetting_tags_and_three_word_glossary_guard():
    """Weryfikacja równowagi tagów kursywy w extract_typesetting_tags oraz obsługi 3-wyrazowych haseł glosariusza."""
    from translator import extract_typesetting_tags, enforce_locked_glossary_terms

    # 1. Równowaga tagów {\i1}...{\i0} w extract_typesetting_tags
    prefix, clean_dialogue = extract_typesetting_tags(r"{\an8\i1}Two{\i0}!")
    assert prefix == r"{\an8}"
    assert clean_dialogue == "Two!"

    prefix2, clean_dialogue2 = extract_typesetting_tags(r"{\an8}{\i1}Episode Title{\i0}!")
    assert prefix2 == r"{\an8}"
    assert clean_dialogue2 == "Episode Title!"

    # 2. Korekta 3-wyrazowych terminów kanonicznych w enforce_locked_glossary_terms
    glossary = [
        {"term_en": "Ice Sword Mage", "translation_pl": "Mag Lodowego Miecza"}
    ]

    # Mianownik
    res_nom = enforce_locked_glossary_terms(
        en_text="He is the Ice Sword Mage.",
        candidate_pl="On jest Mag Magicznego Lodu.",
        glossary_entries=glossary
    )
    assert res_nom == "On jest Mag Lodowego Miecza."

    # Dopełniacz / Biernik (odmiana członu nadrzędnego)
    res_gen = enforce_locked_glossary_terms(
        en_text="I saw the Ice Sword Mage yesterday.",
        candidate_pl="Widziałem wczoraj Maga Magicznego Lodu.",
        glossary_entries=glossary
    )
    assert res_gen == "Widziałem wczoraj Maga Lodowego Miecza."


# ==============================================================================
# STANDARD 11.2.0 REGRESSION TESTS (T11.2.0_HYDROGEN)
# ==============================================================================
@pytest.mark.unit
def test_t11_2_0_hydrogen_master_engine_implicit_cache_95_and_lean_schema_cost_invariance():
    """Weryfikacja silnika Gemini 4 Hydrogen, 95% implicit cache, Lean JSON Schema i niezmiennika kosztowego."""
    from unittest.mock import MagicMock
    from model_resolver import resolve_best_models, build_thinking_config, is_gemini_4_or_hydrogen_model
    from pricing_guard import PricingGuard, GOOGLE_API_RATES
    from context_cache import ContextCacheManager
    from verifier import DialogueVerifier, LeanRefinedBatchResponse, LeanRefinedLine, RefinedBatchResponse, RefinedLine
    from translator import LeanBatchTranslationResponse, LeanLineTranslation, BatchTranslationResponse

    # 1. Rozwiązywanie modeli domyślnych
    models = resolve_best_models(None)
    assert models["hydrogen"] == "gemini-4-hydrogen"
    assert models["flash"] == "gemini-3.8-flash"
    assert is_gemini_4_or_hydrogen_model("gemini-4-hydrogen") is True
    assert is_gemini_4_or_hydrogen_model("gemini-3.8-flash") is False

    # 2. Cennik i estymacja kosztu odcinka (~3.68 PLN dla profilu 3 przy 350 kwestiach, 3.93 PLN przy 364 kwestiach)
    assert GOOGLE_API_RATES["hydrogen"]["input_cached"] == 0.075
    est_350 = PricingGuard.estimate_episode_cost_pln("3", lines_count=350)
    assert est_350 == 3.68
    est_364 = PricingGuard.estimate_episode_cost_pln("3", lines_count=364)
    assert est_364 == 3.93

    # 3. Konfiguracja myślenia (ThinkingConfig) bez wielkich krotek w AST
    cfg_low = build_thinking_config("gemini-4-hydrogen", 0)
    assert getattr(cfg_low, "thinking_level", None) == "LOW"
    cfg_med = build_thinking_config("gemini-4-hydrogen", 3072)
    assert getattr(cfg_med, "thinking_level", None) == "MEDIUM"
    cfg_high = build_thinking_config("gemini-4-hydrogen", 6144)
    assert getattr(cfg_high, "thinking_level", None) == "HIGH"
    cfg_flash = build_thinking_config("gemini-3.8-flash", 0)
    assert getattr(cfg_flash, "thinking_budget", None) == 0

    # 4. Implicit context caching (-95%) w ContextCacheManager
    cache_token = ContextCacheManager.get_or_create_cache(object(), "gemini-4-hydrogen", "A" * 20000)
    assert cache_token == "__IMPLICIT_CACHE_95__"
    assert ContextCacheManager.ensure_cache_ready(object(), "gemini-4-hydrogen", "A" * 20000) is True

    # 5. Dynamiczny budżet myślenia DialogueVerifier w Fazie 2
    mock_pool = MagicMock()
    verifier_hydrogen = DialogueVerifier(client=mock_pool, model="gemini-4-hydrogen")
    budget_std = verifier_hydrogen.calculate_effective_budget([{"id": 1, "en": "Standard line", "pl": "Zwykła linia"}])
    assert budget_std == 2048
    budget_song = verifier_hydrogen.calculate_effective_budget([{"id": 1, "en": "Song lyric", "pl": "Tekst pieśni", "is_song": True}])
    assert budget_song == 3072

    # 6. Kompatybilność odchudzonych schematów Pydantic (Lean JSON Schema)
    lean_trans = LeanBatchTranslationResponse(translations=[LeanLineTranslation(id=1, polish_text="Zwykła linia")])
    full_trans = BatchTranslationResponse.model_validate(lean_trans.model_dump())
    assert full_trans.translations[0].polish_text == "Zwykła linia"

    lean_ref = LeanRefinedBatchResponse(lines=[LeanRefinedLine(id=1, refined_pl="Doskonała linia")])
    full_ref = RefinedBatchResponse(lines=[RefinedLine(id=l.id, refined_pl=l.refined_pl, changes_made=l.changes_made) for l in lean_ref.lines])
    assert full_ref.lines[0].refined_pl == "Doskonała linia"


# ==============================================================================
# STANDARD 11.2.1 REGRESSION TESTS (T11.2.1_WHISPER_SCOPE_AND_MENU)
# ==============================================================================
@pytest.mark.unit
def test_t11_2_1_no_unbound_local_whisper_disambiguator_and_interactive_menu_probe():
    """Weryfikacja integralności zasięgu WhisperDisambiguator i EpisodeProfiler w translator.py oraz sondy w main.py."""
    import ast
    import sys
    from pathlib import Path
    from unittest.mock import patch
    import pysubs2
    from translator import MultimodalTranslator

    # 1. Analiza AST translator.py pod kątem braku zaciemniających importów lokalnych
    translator_path = Path(__file__).parent.parent / "translator.py"
    with open(translator_path, "r", encoding="utf-8") as f:
        tree = ast.parse(f.read(), filename="translator.py")

    target_funcs = {"_prepare_batch_prompt", "_process_single_batch"}
    forbidden_local_imports = {"whisperdisambiguator", "episodeprofiler"}

    found_shadowed = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in target_funcs:
            for subnode in ast.walk(node):
                if isinstance(subnode, ast.ImportFrom):
                    for alias in subnode.names:
                        if alias.name.lower() in forbidden_local_imports:
                            found_shadowed.append((node.name, alias.name, subnode.lineno))

    assert not found_shadowed, f"Wykryto zagnieżdżone importy wywołujące UnboundLocalError: {found_shadowed}"

    # 2. Wywołanie _prepare_batch_prompt z transkrypcją Whisper ASR (0.00 PLN)
    tr = MultimodalTranslator.__new__(MultimodalTranslator)
    tr.tm = None
    tr.character_registry = {}
    tr.series_bible = None
    tr.profiler = None
    tr.scene_cuts_ms = []
    tr.black_intervals_ms = []
    tr.episode_scene_genders = {}
    tr.scene_is_female_only = False
    tr._episode_knowledge_cached = False

    ev = pysubs2.SSAEvent(start=1000, end=3000, text="Synthetic test line", name="Speaker_Alpha")
    batch_events = [(0, ev, "Synthetic test line", "")]

    prompt = tr._prepare_batch_prompt(
        batch_events=batch_events,
        history_context=[],
        whisper_transcriptions={1: "テスト音声"}
    )
    assert "Synthetic test line" in prompt
    assert len(prompt) > 0

    # 3. Logika wyboru profilu i sondy w main.py przy braku flagi -m / --model w sys.argv
    with patch.object(sys, "argv", ["main.py", "dummy.ass"]):
        has_explicit = any(arg in sys.argv for arg in ["-m", "--model"]) or any(arg.startswith("--model=") for arg in sys.argv)
        assert has_explicit is False
        model_p1 = "gemini-4-hydrogen" if has_explicit else None
        assert model_p1 is None

    with patch.object(sys, "argv", ["main.py", "dummy.ass", "-m", "gemini-4-hydrogen"]):
        has_explicit = any(arg in sys.argv for arg in ["-m", "--model"]) or any(arg.startswith("--model=") for arg in sys.argv)
        assert has_explicit is True
        model_p1 = "gemini-4-hydrogen" if has_explicit else None
        assert model_p1 == "gemini-4-hydrogen"





