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
    ev.name = "Tokiyuki Hōjō"

    translator = MultimodalTranslator.__new__(MultimodalTranslator)
    translator.character_registry = {}
    translator.tm = None
    translator._episode_knowledge_cached = True

    prompt = translator.build_phase1_prompt(
        batch_events=[(0, ev, "I escaped from the pursuers!", "I escaped from the pursuers!")],
        history_context=[]
    )
    assert "is_internal_monologue: true" in prompt
