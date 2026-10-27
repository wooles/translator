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


def test_verifier_guard_restores_phase1_on_continuation_and_tag_imbalance():
    from verifier import DialogueVerifier

    cases = [
        (
            "...nie popełnilibyśmy tego błędu.",
            "...nie popełnić tego błędu.",
            "",
            "Gdybyśmy tylko wiedzieli...",
            "...nie popełnilibyśmy tego błędu."
        ),
        (
            "...naszego dowódcy.",
            "...nasz dowódca.",
            "",
            "Zgodnie z rozkazem...",
            "...naszego dowódcy."
        ),
        (
            "Myślałem, że osobą za to odpowiedzialną będziesz ty.",
            "Myślałem, że to ktoś inny.",
            "I thought the person who was responsible would be you.",
            None,
            "Myślałem, że osobą za to odpowiedzialną będziesz ty."
        ),
        (
            r"{\i1}Uwaga!{\i0}",
            r"{\i1}Uwaga!{\i0}{\i0}",
            "",
            None,
            r"{\i1}Uwaga!{\i0}"
        ),
    ]

    for f1_pl, refined_pl, source_en, prev_line_pl, expected in cases:
        result = DialogueVerifier._guard_phase2_regressions(
            f1_pl=f1_pl,
            refined_pl=refined_pl,
            source_en=source_en,
            prev_line_pl=prev_line_pl
        )
        assert result == expected


@pytest.mark.parametrize(
    "f1_sign_text,f2_sign_text,source_en,glossary_nominative,expected_sign_text",
    [
        ("TAJEMNICZY CUKIERK", "TAJEMNICZY CUKIERK",
         "Mysterious Candy", {"Mysterious Candy": "TAJEMNICZY CUKIEREK"},
         "TAJEMNICZY CUKIEREK"),
        ("ZŁOTY PIERŚCIEŃK", "ZŁOTY PIERŚCIEŃK",
         "Golden Ring", {"Golden Ring": "ZŁOTY PIERŚCIEŃ"},
         "ZŁOTY PIERŚCIEŃ"),
    ],
)
def test_verifier_restores_canonical_nominative_orthography_on_is_sign(
    f1_sign_text, f2_sign_text, source_en, glossary_nominative, expected_sign_text
):
    """Weryfikuje korektę ortograficzną formy mianownika M na planszach is_sign: true względem rekordu P0."""
    from verifier import DialogueVerifier
    result = DialogueVerifier.enforce_sign_nominative_orthography(
        f1_pl=f1_sign_text,
        refined_pl=f2_sign_text,
        source_en=source_en,
        is_sign=True,
        canonical_glossary=glossary_nominative,
    )
    assert result == expected_sign_text


@pytest.mark.parametrize(
    "prev_pl,f1_pl,f2_mutated,en_src,prev_en,expected_restored",
    [
        # Kategoria 1: inwersja osoby 2. os. lm. ↔ 1. os. lm. w pytaniu przytoczonym.
        ("Zapytali o nasze plany.", "Co macie zamiar zrobić?", "Co mamy zamiar zrobić?",
         "What do you plan to do?", "They asked about our plans.", "Co macie zamiar zrobić?"),
        # Kategoria 2: zmiana liczby 1. os. lp. → 1. os. lm. wbrew jawnemu zaimkowi EN.
        ("Czekam na wiadomość.", "Zaraz przyślę ci raport.", "Zaraz prześlemy ci raport.",
         "I'll send you the report right away.", "I am waiting for news.", "Zaraz przyślę ci raport."),
        # Kategoria 3: redukcja nadrzędnego czasownika epistemicznego.
        ("Dlaczego milczysz?", "Myślałam, że wszystko pamiętasz.", "Wszystko pamiętasz.",
         "I thought you remembered everything.", "Why are you silent?", "Myślałam, że wszystko pamiętasz."),
        # Kategoria 4: niesynchronizowany drugi wiersz dwugłosu.
        ("– To bezcelowe!", "– Nie traćmy czasu!\\N– To bezcelowe!", "– Nie traćmy czasu!\\N– Nie ma to sensu!",
         "– Don't waste time!\\N– That's pointless!", "That's pointless!", "– Nie traćmy czasu!\\N– To bezcelowe!"),
    ],
)
def test_guard_phase2_restores_person_number_epistemic_verb_and_dual_voice_line2(
    prev_pl, f1_pl, f2_mutated, en_src, prev_en, expected_restored
):
    """Weryfikuje ochronę osoby, liczby lp., czasownika epistemicznego oraz 2. wiersza dwugłosu w OPERACJI 14."""
    from verifier import DialogueVerifier
    result = DialogueVerifier._guard_phase2_regressions(
        f1_pl=f1_pl,
        refined_pl=f2_mutated,
        source_en=en_src,
        prev_line_pl=prev_pl,
        prev_line_en=prev_en,
    )
    assert result == expected_restored
