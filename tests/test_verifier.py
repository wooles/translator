import pytest
from verifier import _guard_phase2_regressions, normalize_ass_tags


def test_guard_phase2_regressions_authority_and_ass_tags():
    # 1. Normalization of malformed ASS tags
    malformed = "{i1}Wypowiedź z kursywą{i0} oraz zwykły tekst."
    normalized = normalize_ass_tags(malformed)
    assert "{\\i1}" in normalized
    assert "{\\i0}" in normalized

    # 2. Regression guard: Mood flip without English modal change
    # English has indicative, Phase 1 has indicative, Phase 2 arbitrarily flipped to conditional
    en_ind = "I know the answer to this question."
    f1_ind = "Znam odpowiedź na to pytanie."
    f2_cond = "Wiedziałbym, jaka jest odpowiedź na to pytanie."
    guarded_mood = _guard_phase2_regressions(
        f1_pl=f1_ind,
        refined_pl=f2_cond,
        source_en=en_ind,
        speaker_p0_gender="MALE"
    )
    assert guarded_mood == f1_ind, f"Oczekiwano zachowania Fazy 1 dla trybu oznajmującego: {guarded_mood}"

    # 3. Regression guard: Loss of gendered past tense for verified P0
    # Phase 1 had feminine past tense, Phase 2 neutralized to present tense
    en_past = "I arrived yesterday."
    f1_past = "Dotarłam wczoraj na miejsce."
    f2_pres = "Docieram na miejsce."
    guarded_past = _guard_phase2_regressions(
        f1_pl=f1_past,
        refined_pl=f2_pres,
        source_en=en_past,
        speaker_p0_gender="FEMALE"
    )
    assert guarded_past == f1_past, f"Oczekiwano zachowania Fazy 1 dla czasu przeszłego P0: {guarded_past}"

    # 4. Regression guard: Enclitic to stressed pronoun replacement mid-sentence
    # Phase 1 had natural enclitic pronoun 'cię', Phase 2 replaced with heavy 'ciebie' mid-sentence without contrast
    en_enc = "I saw you in the hall."
    f1_enc = "Widziałem cię na korytarzu."
    f2_str = "Widziałem ciebie na korytarzu."
    guarded_enc = _guard_phase2_regressions(
        f1_pl=f1_enc,
        refined_pl=f2_str,
        source_en=en_enc,
        speaker_p0_gender="MALE"
    )
    assert guarded_enc == f1_enc, f"Oczekiwano zachowania enklityki z Fazy 1: {guarded_enc}"

    # 5. Regression guard: Loss of prepositional governance for invariable anthroponym
    en_prep = "We are fighting against Carol today."
    f1_prep = "Walczymy dzisiaj przeciwko Carol."
    f2_lost = "Walczymy dzisiaj z Carol."
    guarded_prep = _guard_phase2_regressions(
        f1_pl=f1_prep,
        refined_pl=f2_lost,
        source_en=en_prep,
        speaker_p0_gender="FEMALE"
    )
    assert guarded_prep == f1_prep, f"Oczekiwano zachowania rekcji przyimkowej z Fazy 1: {guarded_prep}"
