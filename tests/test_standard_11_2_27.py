"""
Zestaw testów regresyjnych dla Standardu 11.2.27:
1. test_def05_glossary_slash_and_semicolon_variants_never_inject_separator_or_destroy_dialogue
2. test_obs02_case_variant_generic_registry_entries_deduplicated_by_rich_p0_entry
"""

import pytest
import pysubs2

from translator import MultimodalTranslator, enforce_locked_glossary_terms


@pytest.mark.unit
def test_def05_glossary_slash_and_semicolon_variants_never_inject_separator_or_destroy_dialogue():
    """
    Standard 11.2.27 (DEF-05): Wpisy glosariusza z separatorem wariantów '/' lub ';'
    oznaczają alternatywę wyboru, nigdy frazę wielowyrazową do wstrzyknięcia do dialogu.
    Weryfikuje pełne zachowanie treści linii #313/#314, przełączanie między wariantami w F2,
    fallback bez '/' oraz kontrolę zachowawczą dla zwykłych terminów wielowyrazowych.
    """
    gloss_slash = [{"term_en": "enchant", "translation_pl": "zakląć / wzmocnić"}]
    gloss_semi = [{"term_en": "enchant", "translation_pl": "zakląć ; wzmocnić"}]

    # Przypadek A (odwzorowanie linii #313): zachowanie treści 'zakląć cudzy sprzęt' bez separatora
    en_a = "There's a limit to how much Hero can enchant another person's equipment,"
    p1_a = "Bohater może zakląć cudzy sprzęt tylko do pewnego limitu,"
    cand_a = "Bohater może zakląć cudzy sprzęt tylko do pewnego limitu,"

    for gl in (gloss_slash, gloss_semi):
        res_a = enforce_locked_glossary_terms(en_text=en_a, candidate_pl=cand_a, glossary_entries=gl, phase1_pl=p1_a)
        assert res_a == "Bohater może zakląć cudzy sprzęt tylko do pewnego limitu,"
        assert "/" not in res_a
        assert ";" not in res_a
        assert "zakląć cudzy sprzęt" in res_a

    # Przypadek B (odwzorowanie linii #314): F2 przełącza wariant 'wzmocnić' -> 'zakląć'
    en_b = "but he can enchant his own gear much more."
    p1_b = "ale własny może wzmocnić znacznie bardziej."
    cand_b = "ale własny może zakląć znacznie mocniej."

    for gl in (gloss_slash, gloss_semi):
        res_b = enforce_locked_glossary_terms(en_text=en_b, candidate_pl=cand_b, glossary_entries=gl, phase1_pl=p1_b)
        assert res_b == "ale własny może zakląć znacznie mocniej."
        assert "/" not in res_b
        assert ";" not in res_b
        assert "zakląć znacznie mocniej" in res_b

    # Przypadek C: F2 usuwa oba warianty, a F1 zachowało poprawny wariant bez '/' -> fallback do F1
    cand_c = "ale własny może poprawić znacznie mocniej."
    res_c = enforce_locked_glossary_terms(en_text=en_b, candidate_pl=cand_c, glossary_entries=gloss_slash, phase1_pl=p1_b)
    assert res_c == p1_b
    assert "/" not in res_c

    # Przypadek D: bezpiecznik na skażone phase1_pl zawierające dosłowny separator '/' lub ';'
    p1_polluted_slash = "Bohater może zakląć / wzmocnić sprzęt."
    cand_d = "Bohater może poprawić sprzęt."
    res_d_slash = enforce_locked_glossary_terms(
        en_text=en_a,
        candidate_pl=cand_d,
        glossary_entries=gloss_slash,
        phase1_pl=p1_polluted_slash,
    )
    assert res_d_slash == cand_d
    assert "/" not in res_d_slash

    p1_polluted_semi = "Bohater może zakląć ; wzmocnić sprzęt."
    res_d_semi = enforce_locked_glossary_terms(
        en_text=en_a,
        candidate_pl=cand_d,
        glossary_entries=gloss_semi,
        phase1_pl=p1_polluted_semi,
    )
    assert res_d_semi == cand_d
    assert ";" not in res_d_semi

    # Przypadek E (kontrola zachowawcza): standardowy termin 2-wyrazowy w przypadku zależnym (DEF-01)
    gloss_2w = [{"term_en": "Radiant Beast", "translation_pl": "Promienna Bestia"}]
    res_e = enforce_locked_glossary_terms(
        en_text="She stopped the Radiant Beast on the bridge.",
        candidate_pl="Zatrzymała Promienną Bestię na moście.",
        glossary_entries=gloss_2w,
        phase1_pl="Zatrzymała Promienna Bestia na moście.",
    )
    assert "Promienną Bestię" in res_e
    assert res_e == "Zatrzymała Promienną Bestię na moście."


@pytest.mark.unit
def test_obs02_case_variant_generic_registry_entries_deduplicated_by_rich_p0_entry():
    """
    Standard 11.2.27 (OBS-02 case-variant): Wpisy tła zapisane wielkimi literami
    ('BOHATERKA_A', 'SOJUSZNICZKA_B') są wycinane przez bogatsze wpisy P0 tej samej postaci,
    przy jednoczesnej ochronie P0 przed samo-usunięciem oraz zachowaniu unikalnego wpisu tła ('STATYSTA_C').
    """
    tr = MultimodalTranslator(
        api_key="mock_k0",
        model="gemini-4-hydrogen",
        enable_verifier=False,
    )
    tr.character_registry = {
        "BOHATERKA_A": "Postać epizodyczna / tło",
        "Bohaterka_A": "kobieta (Młoda wojowniczka, główna bohaterka.)",
        "Bohaterka_A Nazwisko": {
            "description": "Główny bohater (kobieta)",
            "priority": "P0",
            "has_verified_gender": True,
            "aliases": ["BOHATERKA_A", "Bohaterka_A", "Bohaterka_A Nazwisko"],
        },
        "SOJUSZNICZKA_B": "Postać epizodyczna / tło",
        "Sojuszniczka_B Nazwisko": {
            "description": "postać (Postać)",
            "priority": "P0",
            "has_verified_gender": True,
            "aliases": ["SOJUSZNICZKA_B", "Sojuszniczka_B", "Sojuszniczka_B Nazwisko"],
        },
        "STATYSTA_C": "Postać epizodyczna / tło",
    }

    ev = pysubs2.SSAEvent(start=1000, end=2000, text="Test dialogue line.", name="Bohaterka_A")
    prompt = tr._prepare_batch_prompt(
        batch_events=[(0, ev, "Test dialogue line.", "")],
        history_context=[],
    )

    assert "• BOHATERKA_A:" not in prompt
    assert "• SOJUSZNICZKA_B:" not in prompt
    assert "• Bohaterka_A:" in prompt
    assert "• Bohaterka_A Nazwisko:" in prompt
    assert "• Sojuszniczka_B Nazwisko:" in prompt
    assert "• STATYSTA_C:" in prompt
