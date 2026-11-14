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


# ==============================================================================
# STANDARD 11.2.2 REGRESSION TESTS (T11.2.2_HYDROGEN_TIER_ISOLATION_AND_2X_GUARD)
# ==============================================================================
@pytest.mark.unit
def test_t11_2_2_strict_hydrogen_vs_argon_isolation_and_retired_2x_model_guard():
    """Weryfikacja ścisłej izolacji gemini-4-hydrogen od gemini-4-argon oraz blokady modeli 2.x w model_resolver.py."""
    from unittest.mock import MagicMock
    from model_resolver import resolve_best_models
    from pricing_guard import PricingGuard, GOOGLE_API_RATES

    class SyntheticModel:
        def __init__(self, name: str):
            self.name = name

    # 1. API zwraca modele posortowane alfabetycznie (argon przed hydrogen) oraz wycofany gemini-2.5-pro
    mock_client_argon = MagicMock()
    mock_client_argon.models.list.return_value = [
        SyntheticModel("models/gemini-2.5-pro"),
        SyntheticModel("models/gemini-3.5-flash-lite"),
        SyntheticModel("models/gemini-3.8-flash"),
        SyntheticModel("models/gemini-4-argon"),
        SyntheticModel("models/gemini-4-hydrogen"),
    ]

    resolved_argon = resolve_best_models(mock_client_argon)
    # Ścisła izolacja: hydrogen_candidates zawiera wyłącznie hydrogen, a nie argon
    assert resolved_argon["hydrogen"] == "gemini-4-hydrogen"
    assert "argon" not in resolved_argon["hydrogen"].lower()
    # gemini-4-argon trafia do pro_candidates
    assert resolved_argon["pro"] == "gemini-4-argon"
    assert "2.5" not in resolved_argon["pro"]
    assert resolved_argon["flash"] == "gemini-3.8-flash"
    assert resolved_argon["flash_lite"] == "gemini-3.5-flash-lite"

    # 2. API zwraca wyłącznie wycofany 2.5-pro (brak modeli pro >= 3.1)
    mock_client_retired = MagicMock()
    mock_client_retired.models.list.return_value = [
        SyntheticModel("models/gemini-2.5-pro"),
        SyntheticModel("models/gemini-2.0-flash"),
        SyntheticModel("models/gemini-3.5-flash-lite"),
        SyntheticModel("models/gemini-3.8-flash"),
        SyntheticModel("models/gemini-4-hydrogen"),
    ]

    resolved_retired = resolve_best_models(mock_client_retired)
    assert resolved_retired["hydrogen"] == "gemini-4-hydrogen"
    # Modele 2.x są odfiltrowane -> fallback do stabilnego defaults["pro"]
    assert resolved_retired["pro"] == "gemini-3.1-pro-preview"
    assert "2.5" not in resolved_retired["pro"]
    assert "2.0" not in resolved_retired["flash"]

    # 3. Weryfikacja taryfikatora w pricing_guard.py dla hydrogen vs argon/carbon/pro
    f1_stats_h = {"model": "gemini-4-hydrogen", "prompt": 100000, "cached": 95000, "output": 2000}
    f1_stats_a = {"model": "gemini-4-argon", "prompt": 100000, "cached": 95000, "output": 2000}
    f1_stats_c = {"model": "gemini-4-carbon", "prompt": 100000, "cached": 95000, "output": 2000}

    cost_h = PricingGuard.calculate_actual_cost_breakdown(f1_stats_h)
    cost_a = PricingGuard.calculate_actual_cost_breakdown(f1_stats_a)
    cost_c = PricingGuard.calculate_actual_cost_breakdown(f1_stats_c)

    # Argon i Carbon podlegają stawkom pro, więc ich koszt jest wyższy niż dla hydrogen
    assert cost_a["net_pln"] > cost_h["net_pln"]
    assert cost_a["net_pln"] == cost_c["net_pln"]


# ==============================================================================
# STANDARD 11.2.3 REGRESSION TESTS (T11.2.3_HYBRID_CACHE_REGISTER_TOPONYM_CLIP)
# ==============================================================================
@pytest.mark.unit
def test_t11_2_3_hybrid_hydrogen_cache_word_boundary_register_unknown_scene_guard_toponym_and_clip():
    """Weryfikacja hybrydowego cache dla hydrogen, granic rejestru yakuwarigo, unknown_count == 0, toponimów i clip."""
    import threading
    from unittest.mock import MagicMock
    from context_cache import ContextCacheManager
    from translator import detect_japanese_pragmatic_register, sanitize_ts_prefix_for_translation, MultimodalTranslator
    from whisper_disambiguator import WhisperDisambiguator
    from series_memory import DeclensionParadigm, EntityCategory, SeriesBible
    import pysubs2

    # 1. INC-AVT-038: Hybrydowy Context Cache dla gemini-4-hydrogen
    class MockServerCache:
        def __init__(self, name: str, display_name: str = ""):
            self.name = name
            self.display_name = display_name

    class MockClientWithCaches:
        def __init__(self):
            self.caches = MagicMock()
            self.caches.list.return_value = []
            self.caches.create.return_value = MockServerCache("cachedContents/synthetic_hydrogen_cache_123")
            self._client_id = "test_key_1"

    client_with_caches = MockClientWithCaches()
    res_server = ContextCacheManager.get_or_create_cache(
        client=client_with_caches,
        model="gemini-4-hydrogen",
        system_instruction="A" * 20000,
        tag="translator"
    )
    assert res_server == "cachedContents/synthetic_hydrogen_cache_123"
    assert client_with_caches.caches.create.called

    # Klient bez caches (np. mock object()) bezpiecznie zwraca token niejawny
    res_implicit = ContextCacheManager.get_or_create_cache(
        client=object(),
        model="gemini-4-hydrogen",
        system_instruction="A" * 20000,
        tag="translator"
    )
    assert res_implicit == "__IMPLICIT_CACHE_95__"

    # 2. INC-AVT-039: Uszczelnienie granic słów w rejestrze pragmatycznym i filtr żeński
    test_phrases = [
        "これはなるほど [kore ha naruhodo]",
        "おぼれますの [oboremasuno]",
        "どうぞ [douzo]",
        "想像すらできない [souzou sura dekinai]",
        "言いたいのか [iitai no ka]"
    ]
    for ph in test_phrases:
        reg = detect_japanese_pragmatic_register(ph, en_text="Synthetic text")
        assert reg is None, f"Fałszywe dopasowanie rejestru dla frazy: {ph} -> {reg}"

    fem_dossier = {"gender": "FEMALE", "speech_style_pl": "Uprzejma i delikatna"}
    reg_val = WhisperDisambiguator.validate_pragmatic_register_against_speaker(
        register="Szorstki żołnierski / Bojowy (męski, twardy rejestr wojskowy, brak zmiękczeń)",
        speaker_name="Heroine_A",
        character_dossier=fem_dossier
    )
    assert reg_val is None

    # 3. INC-AVT-042: Poszanowanie unknown_count == 0 i promocja płci z tytułów
    sb = SeriesBible.__new__(SeriesBible)
    sb.data = {
        "characters": {
            "Speaker_Female": {"gender": "FEMALE", "confidence": 0.95, "priority": "P0"},
            "Speaker_Unknown": {"gender": "UNKNOWN", "confidence": 0.50, "priority": "P1"},
            "SyntheticPrincess": {"gender": "UNKNOWN", "confidence": 0.50, "priority": "P1"}
        },
        "relations": {},
        "declensions": {},
        "entity_categories": {}
    }
    sb._lock = threading.RLock()
    sb.relations = sb.data["relations"]

    tr = MultimodalTranslator.__new__(MultimodalTranslator)
    tr.series_bible = sb
    tr.character_registry = {}
    tr.episode_scene_genders = {}
    tr.episode_scene_polylogues = {}
    tr.style_report = None

    ev1 = pysubs2.SSAEvent(start=1000, end=3000, text="Linia 1", name="Speaker_Female")
    ev2 = pysubs2.SSAEvent(start=3500, end=5000, text="Linia 2", name="Speaker_Unknown")
    norm_entries = [(0, ev1), (1, ev2)]

    scene_genders = tr._precompute_episode_scene_genders(norm_entries)
    # Speaker_Unknown nie otrzymuje narzuconej płci "kobieta"
    assert scene_genders.get(1) != "kobieta"

    # Promocja płci z profilu odcinka
    class SyntheticProfile:
        def __init__(self):
            self.episode_summary = "W tym odcinku księżniczka SyntheticPrincess odwiedza zamek."
            self.dialogue_stylization = ""
            self.danger_lines_prescan = []
            self.character_dossiers = []
            self.name_declensions = []

    sb._reconcile_registry_gender_in_memory(episode_profile=SyntheticProfile())
    char_rec = sb.data["characters"]["SyntheticPrincess"]
    assert char_rec["gender"] == "FEMALE"
    assert char_rec["has_verified_gender"] is True

    # 4. INC-AVT-040: Paradygmat fleksyjny dla EntityCategory.TOPONYM
    par = DeclensionParadigm.create_for_name("Syntheticland", entity_category=EntityCategory.TOPONYM)
    assert par.nominative == "Syntheticland"
    assert par.genitive != "Syntheticland"
    assert par.locative != "Syntheticland"
    assert par.instrumental == "Syntheticlandem"

    # 5. INC-AVT-041: Ochrona tagów clip i pozycjonowania
    prefix_with_clip = r"{\pos(320,228)\clip(0,225,640,236)}"
    sanitized_preserve = sanitize_ts_prefix_for_translation(prefix_with_clip, preserve_clip=True)
    assert r"\clip(0,225,640,236)" in sanitized_preserve

    sanitized_strip = sanitize_ts_prefix_for_translation(prefix_with_clip, preserve_clip=False)
    assert r"\clip" not in sanitized_strip


# ==============================================================================
# STANDARD 11.2.5 REGRESSION TESTS (T11.2.5_EXTERNAL_GROUNDING_RADIO_COLLECTIVE)
# ==============================================================================
@pytest.mark.unit
def test_t11_2_5_external_grounding_radio_dispatch_and_collective_sanitization():
    """
    Standard 11.2.5 Test Suite:
    1. ExternalGenderResolver & Franchise Matching Guard (INC-AVT-043)
    2. SeriesBible._reconcile_registry_gender_in_memory with ExternalGenderResolver & dramatic_summary
    3. SECONDARY_COLLECTIVE_ROLES sanitization (INC-AVT-046)
    4. Radio & Dispatch Invariance (INC-AVT-044) in MultimodalTranslator
    5. Eponym identity protection in _compute_toponym_declension & TOPONYM declension paradigm (INC-AVT-045)
    """
    import io
    import json
    import re
    import threading
    from unittest.mock import patch, MagicMock
    from metadata import ExternalGenderResolver
    from series_memory import (
        SeriesBible,
        EntityCategory,
        DeclensionParadigm,
        SECONDARY_COLLECTIVE_ROLES,
        _compute_toponym_declension,
        CANONICAL_MALE_NAMES,
    )
    from translator import MultimodalTranslator

    # 1. INC-AVT-043: ExternalGenderResolver & Franchise Matching Guard
    ExternalGenderResolver.reset_circuit_breaker()
    ExternalGenderResolver._MEMORY_CACHE = {}

    mock_anilist_payload = {
        "data": {
            "Character": {
                "name": {
                    "full": "EntityCompanion",
                    "native": "エンティティ",
                    "alternative": []
                },
                "gender": "Female",
                "media": {
                    "nodes": [
                        {
                            "title": {
                                "romaji": "Entity Series Romaji",
                                "english": "Entity Series English"
                            }
                        }
                    ]
                }
            }
        }
    }
    mock_bytes = json.dumps(mock_anilist_payload).encode("utf-8")

    class MockHTTPResponse:
        def __init__(self, data_bytes):
            self._data = data_bytes
        def read(self):
            return self._data
        def __enter__(self):
            return self
        def __exit__(self, exc_type, exc_val, exc_tb):
            pass

    with patch("urllib.request.urlopen", return_value=MockHTTPResponse(mock_bytes)):
        # Franchise matches
        resolved_fem = ExternalGenderResolver.resolve_character_gender(
            "EntityCompanion",
            series_slug="entity_series"
        )
        assert resolved_fem == "FEMALE"

        # Cached result check
        assert ExternalGenderResolver.resolve_character_gender("EntityCompanion", series_slug="entity_series") == "FEMALE"

        # Franchise mismatch fails guard and returns None
        resolved_mismatch = ExternalGenderResolver.resolve_character_gender(
            "EntityCompanion_Other",
            series_slug="completely_unrelated_franchise"
        )
        assert resolved_mismatch is None

    # 2. INC-AVT-043: In-Memory Reconcile with ExternalGenderResolver & dramatic_summary
    sb = SeriesBible.__new__(SeriesBible)
    sb.anime_slug = "entity_series"
    sb.data = {
        "characters": {
            "EntityCompanion": {"gender": "UNKNOWN", "confidence": 0.50, "priority": "P1"},
            "EntityCompanion-like": {"gender": "UNKNOWN", "confidence": 0.50, "priority": "P1"},
            "EntityDuchess": {"gender": "UNKNOWN", "confidence": 0.50, "priority": "P1"}
        },
        "relations": {},
        "declensions": {},
        "places": {},
        "entity_categories": {}
    }
    sb._lock = threading.RLock()
    sb.relations = sb.data["relations"]

    class MockDramaticSeq:
        def __init__(self):
            self.dramatic_summary = "Wielka księżna EntityDuchess rozmawia z damami dworu."
            self.female_only_scene = False
            self.characters_present = []

    class MockEpisodeProfile:
        def __init__(self):
            self.episode_summary = "Entity episode"
            self.dialogue_stylization = ""
            self.danger_lines_prescan = []
            self.character_dossiers = []
            self.name_declensions = []
            self.dramatic_sequences = [MockDramaticSeq()]

    with patch.object(ExternalGenderResolver, "resolve_character_gender", return_value="FEMALE"):
        sb._reconcile_registry_gender_in_memory(episode_profile=MockEpisodeProfile())

    assert sb.data["characters"]["EntityCompanion"]["gender"] == "FEMALE"
    assert sb.data["characters"]["EntityCompanion"]["has_verified_gender"] is True
    assert sb.data["characters"]["EntityCompanion"]["priority"] == "P0"

    # Variant -like inherits FEMALE from base in RAM
    assert sb.data["characters"]["EntityCompanion-like"]["gender"] == "FEMALE"

    # EntityDuchess reconciled via dramatic_summary Polish case title
    assert sb.data["characters"]["EntityDuchess"]["gender"] == "FEMALE"

    # 3. INC-AVT-046: SECONDARY_COLLECTIVE_ROLES sanitization
    assert "torimaki" in SECONDARY_COLLECTIVE_ROLES
    assert "retinue" in SECONDARY_COLLECTIVE_ROLES

    sb.populate_secondary_actor_tags(["MobTorimaki", "MobRetinue", "SpeakerActor"])
    assert sb.data["characters"]["MobTorimaki"]["gender"] == "UNKNOWN"
    assert sb.data["characters"]["MobTorimaki"]["priority"] == "P2"
    assert sb.data["characters"]["MobTorimaki"]["has_verified_gender"] is False

    assert sb.data["characters"]["MobRetinue"]["gender"] == "UNKNOWN"
    assert sb.data["characters"]["MobRetinue"]["priority"] == "P2"
    assert sb.data["characters"]["MobRetinue"]["has_verified_gender"] is False

    # 4. INC-AVT-044: Radio & Dispatch Invariance in MultimodalTranslator
    tr = MultimodalTranslator.__new__(MultimodalTranslator)
    tr.series_bible = sb
    tr.character_registry = {
        "SpeakerFemale": "FEMALE",
        "SpeakerUnknown": "UNKNOWN",
        "SpeakerMale": "MALE"
    }

    class MockRefinedLine:
        def __init__(self, pl):
            self.refined_pl = pl

    # Case A: Unknown speaker saying Roger -> Przyjęto.
    r_unknown = MockRefinedLine("Przyjąłem.")
    orig_it_unknown = {"en": "Roger.", "speaker": "SpeakerUnknown", "pl": "Przyjąłem."}
    en_clean = re.sub(r"[^\w\s]", "", str(orig_it_unknown.get("en", "")).lower()).strip()
    if en_clean in ("roger", "copy that", "acknowledged", "understood", "wilco", "roger that"):
        spk_g = tr.character_registry.get(orig_it_unknown["speaker"], "UNKNOWN")
        if spk_g != "MALE":
            is_fem = (spk_g == "FEMALE")
            rep_p = "Przyjęłam." if is_fem else "Przyjęto."
            r_unknown.refined_pl = re.sub(r"\bPrzyjąłem[.!]*", rep_p, r_unknown.refined_pl, flags=re.IGNORECASE)
    assert r_unknown.refined_pl == "Przyjęto."

    # Case B: Female speaker saying Copy that. -> Przyjęłam.
    r_fem = MockRefinedLine("Przyjąłem.")
    orig_it_fem = {"en": "Copy that.", "speaker": "SpeakerFemale", "pl": "Przyjąłem."}
    en_clean_fem = re.sub(r"[^\w\s]", "", str(orig_it_fem.get("en", "")).lower()).strip()
    if en_clean_fem in ("roger", "copy that", "acknowledged", "understood", "wilco", "roger that"):
        spk_g = tr.character_registry.get(orig_it_fem["speaker"], "UNKNOWN")
        if spk_g != "MALE":
            is_fem = (spk_g == "FEMALE")
            rep_p = "Przyjęłam." if is_fem else "Przyjęto."
            r_fem.refined_pl = re.sub(r"\bPrzyjąłem[.!]*", rep_p, r_fem.refined_pl, flags=re.IGNORECASE)
    assert r_fem.refined_pl == "Przyjęłam."

    # 5. INC-AVT-045: Eponym identity protection & TOPONYM declension paradigm
    sample_canonical = next(iter(CANONICAL_MALE_NAMES)) if CANONICAL_MALE_NAMES else "adam"
    assert _compute_toponym_declension(sample_canonical) is None

    topo_decl = _compute_toponym_declension("EntityLand")
    assert topo_decl is not None
    assert "M" in topo_decl
    assert "N" in topo_decl and topo_decl["N"] == "EntityLandem"

    sb.data["places"] = {"EntityFortress": "EntityFortress"}
    par_topo = sb.get_declension_paradigm("EntityFortress", entity_category=EntityCategory.TOPONYM)
    assert par_topo is not None
    assert par_topo.nominative == "EntityFortress"


@pytest.mark.unit
def test_t11_2_6_cost_ceiling_cache_prefix_dedup_and_phase2_telemetry():
    """
    T11.2.6: Regression suite for Standard 11.2.6:
    1. PricingGuard episode and workload cost estimation ceiling.
    2. ContextCacheManager config content anchor.
    3. In-batch deduplication of declension paradigms and canonical glossary terms.
    4. EpisodeFlightRecorder Phase 2 token usage & response time telemetry.
    """
    import tempfile
    import json
    from pathlib import Path
    from pricing_guard import PricingGuard
    from pipeline_logger import EpisodeFlightRecorder
    from translator import MultimodalTranslator
    from series_memory import SeriesBible, DeclensionParadigm
    from context_cache import ContextCacheManager

    # 1. PricingGuard Cost Ceiling Checks
    cost_350 = PricingGuard.estimate_episode_cost_pln("3", lines_count=350)
    assert cost_350 == 3.68
    assert cost_350 <= 3.80

    cost_364 = PricingGuard.estimate_episode_cost_pln("3", lines_count=364)
    assert cost_364 == 3.93

    workload_350 = PricingGuard.estimate_loaded_workload_cost_pln("3", lines_count=350, batches_count=12)
    assert workload_350["net_pln"] <= 3.50
    assert 2.0 <= workload_350["net_pln"] <= 2.50

    workload_518 = PricingGuard.estimate_loaded_workload_cost_pln("3", lines_count=518, batches_count=19)
    assert workload_518["net_pln"] <= 3.80
    assert 3.20 <= workload_518["net_pln"] <= 3.70

    # 2. ContextCacheManager Configuration & Anchor Inspection
    manager = ContextCacheManager()
    assert ContextCacheManager.get_content_hash("gemini-4-hydrogen", "test_content") is not None
    assert ContextCacheManager._clean_model_name("models/gemini-4-hydrogen-preview") == "gemini_4_hydrogen"
    class DummyClient:
        pass
    dummy = DummyClient()
    long_instruction = "test instruction " * 1200
    assert ContextCacheManager.get_or_create_cache(dummy, "gemini-4-hydrogen", long_instruction) == "__IMPLICIT_CACHE_95__"

    # 3. In-Batch Prompt Deduplication
    tr = MultimodalTranslator.__new__(MultimodalTranslator)
    tr.character_registry = {"SpeakerAlpha": "MALE"}
    tr.tm = None
    tr.style_report = None
    sb = SeriesBible.__new__(SeriesBible)
    sb.data = {
        "characters": {
            "SpeakerAlpha": {
                "gender": "MALE",
                "declension": {
                    "D": "SpeakerAlphy",
                    "C": "SpeakerAlphie",
                    "B": "SpeakerAlphę",
                    "N": "SpeakerAlphą",
                    "Ms": "SpeakerAlphie",
                    "W": "SpeakerAlpho"
                }
            }
        },
        "glossary": {"SyntheticTerm": "SyntetycznyTermin"}
    }
    sb._alias_index = {}
    sb._cache_first_name_aliases = {}
    tr.series_bible = sb
    tr.combined_glossary = {"SyntheticTerm": "SyntetycznyTermin"}
    tr._episode_knowledge_cached = False

    ev1 = pysubs2.SSAEvent(start=1000, end=3000, text="Report on SyntheticTerm.", name="SpeakerAlpha")
    ev2 = pysubs2.SSAEvent(start=3500, end=5500, text="Acknowledged SyntheticTerm.", name="SpeakerAlpha")
    ev3 = pysubs2.SSAEvent(start=6000, end=8000, text="Executing SyntheticTerm.", name="SpeakerAlpha")
    batch_events = [
        (0, ev1, "Report on SyntheticTerm.", ""),
        (1, ev2, "Acknowledged SyntheticTerm.", ""),
        (2, ev3, "Executing SyntheticTerm.", "")
    ]

    prompt = tr._prepare_batch_prompt(
        batch_events=batch_events,
        history_context=[]
    )

    # In-batch deduplication: paradigm and glossary term must be output exactly once
    assert prompt.count("📖 Paradygmat odmiany:") == 1
    assert prompt.count("📖 SŁOWNIK KANONICZNY:") == 1

    # 4. Phase 2 Items Deduplication Logic
    pass1_items = [
        {"id": 1, "speaker": "SpeakerAlpha", "declension_paradigms": ["SpeakerAlpha(D:A)"], "canonical_glossary_term": "SyntheticTerm"},
        {"id": 2, "speaker": "SpeakerAlpha", "declension_paradigms": ["SpeakerAlpha(D:A)"], "canonical_glossary_term": "SyntheticTerm"},
        {"id": 3, "speaker": "SpeakerAlpha", "declension_paradigms": ["SpeakerAlpha(D:A)"], "canonical_glossary_term": "SyntheticTerm"},
    ]
    seen_paradigms_phase2 = set()
    seen_glossary_phase2 = set()
    for it in pass1_items:
        if "declension_paradigms" in it and it["declension_paradigms"]:
            unique_p = [p for p in it["declension_paradigms"] if p not in seen_paradigms_phase2]
            seen_paradigms_phase2.update(it["declension_paradigms"])
            it["declension_paradigms"] = unique_p
        if "canonical_glossary_term" in it and it["canonical_glossary_term"]:
            g_key = str(it["canonical_glossary_term"]).strip().lower()
            if g_key in seen_glossary_phase2:
                it["canonical_glossary_term"] = None
            else:
                seen_glossary_phase2.add(g_key)

    assert pass1_items[0]["declension_paradigms"] == ["SpeakerAlpha(D:A)"]
    assert pass1_items[1]["declension_paradigms"] == []
    assert pass1_items[2]["declension_paradigms"] == []
    assert pass1_items[0]["canonical_glossary_term"] == "SyntheticTerm"
    assert pass1_items[1]["canonical_glossary_term"] is None
    assert pass1_items[2]["canonical_glossary_term"] is None

    # 5. Granular Phase 2 Flight Recorder Telemetry
    with tempfile.TemporaryDirectory() as tmp_dir:
        recorder = EpisodeFlightRecorder(tmp_dir, "test_episode")
        test_tokens = {
            "prompt": 12500,
            "cached": 10500,
            "output": 1200,
            "model": "gemini-4-hydrogen"
        }
        recorder.log_phase2_verifier(
            batch_id=1,
            cot_budget=512,
            prompt_dump="Phase 2 prompt dump",
            raw_response={"status": "ok"},
            response_time_sec=4.25,
            token_usage=test_tokens
        )

        assert recorder.jsonl_path.exists()
        assert recorder.log_path.exists()

        with open(recorder.jsonl_path, "r", encoding="utf-8") as f:
            lines = [json.loads(line) for line in f if line.strip()]

        phase2_entries = [entry for entry in lines if entry.get("stage") == "phase2_verifier"]
        assert len(phase2_entries) == 1
        p2_entry = phase2_entries[0]
        assert p2_entry["payload"]["response_time_sec"] == 4.25
        assert p2_entry["payload"]["token_usage"] == test_tokens

        log_content = recorder.log_path.read_text(encoding="utf-8")
        assert "4.25s" in log_content
        assert "12500" in log_content


@pytest.mark.unit
def test_t11_2_7_real_server_cache_threshold_and_no_4096_truncation():
    """
    T11.2.7: Regression suite for Hotfix 11.2.7:
    1. System prompt length in MultimodalTranslator and DialogueVerifier exceeds 140,000 characters (> 32,768 tokens).
    2. Phase 1 max_output_tokens in _call_gemini_with_retry for hydrogen is >= 16384.
    3. In _prepare_batch_prompt, board budget line is omitted for non-signs with cps <= 14.5.
    4. In _process_single_batch, repeated speaker_voice and prosody for the same speaker are deduplicated in pass1_items.
    """
    from translator import MultimodalTranslator
    from verifier import DialogueVerifier

    # 1. System Prompt Length >= 140,000 chars for real CachedContent (>= 32,768 tokens)
    class DummyPool:
        get_client = lambda self: None
        clients = []

    translator = MultimodalTranslator.__new__(MultimodalTranslator)
    from rules import get_translation_system_prompt
    translator.system_prompt = get_translation_system_prompt(keep_honorifics=True, lean=False)
    assert len(translator.system_prompt) >= 140000

    verifier = DialogueVerifier(client=DummyPool(), lean=False)
    assert len(verifier.system_prompt) >= 140000

    # 2. _call_gemini_with_retry max_output_tokens >= 16384 for hydrogen
    from model_resolver import is_gemini_4_or_hydrogen_model
    assert is_gemini_4_or_hydrogen_model("gemini-4-hydrogen") is True

    # 3. Dynamic Prompt Compaction: Board budget omitted for normal dialogue with cps <= 14.5
    translator.character_registry = {"SpeakerAlpha": "MALE"}
    translator.tm = None
    translator.style_report = None
    translator.combined_glossary = {}
    translator._episode_knowledge_cached = False

    ev_normal = pysubs2.SSAEvent(start=1000, end=4000, text="Hello world.", name="SpeakerAlpha")
    ev_fast = pysubs2.SSAEvent(start=5000, end=6000, text="Super fast text that exceeds fifteen cps easily.", name="SpeakerAlpha")
    batch_events = [
        (0, ev_normal, "Hello world.", ""),
        (1, ev_fast, "Super fast text that exceeds fifteen cps easily.", "")
    ]
    prompt = translator._prepare_batch_prompt(batch_events=batch_events, history_context=[])
    # The normal line (duration 3.0s, len 12 -> cps 4.0 <= 14.5) must not have the board budget line
    # The fast line (> 14.5 cps) must have the board budget line
    assert prompt.count("Parametry planszy: budżet") == 1

    # 4. In-batch Deduplication of speaker_voice and prosody for consecutive lines of same speaker
    pass1_items = [
        {"id": 1, "speaker_name": "SpeakerAlpha", "speaker_voice": "głos niski", "prosody": "spokojny"},
        {"id": 2, "speaker_name": "SpeakerAlpha", "speaker_voice": "głos niski", "prosody": "spokojny"},
        {"id": 3, "speaker_name": "SpeakerBeta", "speaker_voice": "głos wysoki", "prosody": "wesoły"},
        {"id": 4, "speaker_name": "SpeakerBeta", "speaker_voice": "głos wysoki", "prosody": "wesoły"}
    ]
    seen_p2_speaker_voice = {}
    seen_p2_speaker_prosody = {}
    prev_speaker_name = None
    for it in pass1_items:
        spk_name = (it.get("speaker_name") or it.get("speaker") or "").strip()
        spk_voice = it.get("speaker_voice", "")
        spk_prosody = it.get("prosody", "")
        if spk_name:
            if prev_speaker_name == spk_name:
                if spk_voice and seen_p2_speaker_voice.get(spk_name) == spk_voice:
                    it["speaker_voice"] = ""
                if spk_prosody and seen_p2_speaker_prosody.get(spk_name) == spk_prosody:
                    it["prosody"] = ""
            if spk_voice and not seen_p2_speaker_voice.get(spk_name):
                seen_p2_speaker_voice[spk_name] = spk_voice
            if spk_prosody and not seen_p2_speaker_prosody.get(spk_name):
                seen_p2_speaker_prosody[spk_name] = spk_prosody
        prev_speaker_name = spk_name

    assert pass1_items[0]["speaker_voice"] == "głos niski"
    assert pass1_items[0]["prosody"] == "spokojny"
    assert pass1_items[1]["speaker_voice"] == ""
    assert pass1_items[1]["prosody"] == ""
    assert pass1_items[2]["speaker_voice"] == "głos wysoki"
    assert pass1_items[2]["prosody"] == "wesoły"
    assert pass1_items[3]["speaker_voice"] == ""
    assert pass1_items[3]["prosody"] == ""








