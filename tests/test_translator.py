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
            "Musimy już ruszać, Ayako.",
            r"{\i1}Musimy już ruszać, Ayako.{\i0}",
            "Musimy już ruszać, Ayako."
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
        source_en="We need to move now, Ayako.",
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
        # 1. Styl Italics bez znaczników kursywy -> automatyczne otoczenie pojedynczą parą {\i1}...{\i0}
        ("Italics", "To musi być jakaś pułapka.\nMuszę uważać.", r"{\i1}To musi być jakaś pułapka.\NMuszę uważać.{\i0}"),
        # 2. Styl Flashback_Italics z wewnętrznym duplikatem -> oczyszczenie do pojedynczej pary
        ("Flashback_Italics", r"{\i1}Wspomnienie dawnych dni{\i0}\n{\i1}nadal boli.{\i0}", r"{\i1}Wspomnienie dawnych dni\Nnadal boli.{\i0}"),
        # 3. Kontrprzykład: zwykły styl Default bez myśli -> brak automatycznego otaczania kursywą
        ("Default", "Wszyscy na stanowiska!", "Wszyscy na stanowiska!"),
    ]
)
def test_phase1_postprocess_wraps_italics_style_and_normalizes_single_italic_block(
    style_name, input_draft, expected_wrapped
):
    """
    T5.7 (Operacja 2C.6): Prawidłowy stan tekstu Fazy 1 dla stylu Italics
    = pojedyncza para {\\i1}...{\\i0} obejmująca cały tekst oraz separator \\N zamiast \\n.
    """
    import pysubs2
    from translator import format_phase1_candidate_text

    event = pysubs2.SSAEvent(start=1000, end=3000, text=input_draft, style=style_name)
    pl_cand = format_phase1_candidate_text(input_draft, event, is_sign=False)
    is_im = any(k in style_name.lower() for k in ["italic", "thoughts", "internal"])

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
