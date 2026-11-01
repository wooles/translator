from unittest.mock import MagicMock
from verifier import RefinedLine, RefinedBatchResponse
import pytest
from verifier import _guard_phase2_regressions, normalize_ass_tags, DialogueVerifier


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
    en_prep = "We are fighting against Monika today."
    f1_prep = "Walczymy dzisiaj przeciwko Monika."
    f2_lost = "Walczymy dzisiaj z Monika."
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


# Test dla Sekcji 2C.3
@pytest.mark.parametrize(
    "prev_pl,f1_pl,f2_pl,en_src,prev_en,expected_pl",
    [
        (
            "Kwestia poprzednia.",
            "Ale to {\\i1}świetnie{\\i0} wygląda!",
            "{\\i1}Ale to świetnie{\\i0} wygląda!{\\i0}",
            "That is {\\i1}so{\\i0} cool!",
            "Previous line.",
            "Ale to {\\i1}świetnie{\\i0} wygląda!",
        ),
        (
            "To bezcelowe!",
            "- Chcę odejść...\n- To bezcelowe!",
            "- Odejdę...\n- Bezcelowe!",
            "- I want to leave...\n- That's pointless!",
            "That's pointless!",
            "- Odejdę...\n- To bezcelowe!",
        ),
        (
            "Poprzednia.",
            "...wiedziałem, że to ty, Rywalu.",
            "{\\i1}Wiedziałem, Rywalu.{\\i0}",
            "I knew it would be you, Rival.",
            "Prev.",
            "...wiedziałem, że to ty, Rywalu.",
        ),
    ],
)
def test_guard_phase2_rejects_orphan_i0_syncs_hyphen_dual_voice_and_keeps_clause(
    prev_pl, f1_pl, f2_pl, en_src, prev_en, expected_pl
):
    """Weryfikuje odrzucanie osieroconego {\\i0}, synchronizację dwugłosu z '-' oraz ochronę zdania podrzędnego."""
    res = DialogueVerifier._guard_phase2_regressions(
        f1_pl=f1_pl,
        refined_pl=f2_pl,
        source_en=en_src,
        prev_line_pl=prev_pl,
        prev_line_en=prev_en,
    )
    assert res == expected_pl


# Test dla Sekcji 2C.6
@pytest.mark.parametrize(
    "en_sign,f1_sign,f2_sign,glossary_map,expected_sign",
    [
        (
            "MYSTERIOUS ITEM",
            "TAJEMNICZY PRZEDMIOTOWY ARTEFAKT",
            "TAJEMNICZY PRZEDMIOTOWY ARTEFAKT",
            {"MYSTERIOUS ITEM": "TAJEMNICZY PRZEDMIOT"},
            "TAJEMNICZY PRZEDMIOT",
        ),
        (
            "SECRET PASS",
            "TAJNY BILETOWY KLUCZ",
            "TAJNY BILETOWY KLUCZ",
            {"SECRET PASS": "TAJNY BILET"},
            "TAJNY BILET",
        ),
    ],
)
def test_sign_orthography_enforces_strict_lexical_correspondence_with_en_text(
    en_sign, f1_sign, f2_sign, glossary_map, expected_sign
):
    """Weryfikuje ścisłą odpowiedniość leksykalną 1:1 krótkich napisów is_sign względem en_text."""
    res = DialogueVerifier.enforce_sign_nominative_orthography(
        f1_pl=f1_sign,
        refined_pl=f2_sign,
        source_en=en_sign,
        is_sign=True,
        canonical_glossary=glossary_map,
    )
    assert res == expected_sign



# ==============================================================================
# STANDARD 9.4 TESTS (T4.4, T4.6)
# ==============================================================================

@pytest.mark.unit
def test_verify_batch_nullifies_changes_made_when_text_unchanged(monkeypatch):
    from context_cache import ContextCacheManager
    monkeypatch.setattr(ContextCacheManager, "get_or_create_cache", lambda *args, **kwargs: "mock_cache")
    """
    T4.4 (Operacja 2B.11): Prawidłowy stan changes_made = None,
    gdy refined_pl po normalizacji białych znaków jest tożsamy z f1_pl.
    """
    mock_pool = MagicMock()
    mock_client = MagicMock()
    mock_pool.get_client.return_value = mock_client
    mock_pool.clients = [mock_client]
    mock_response = MagicMock()
    mock_response.text = "{}"
    mock_response.parsed = RefinedBatchResponse(lines=[
        RefinedLine(
            id=1,
            refined_pl="Wiem o wszystkim, co się wczoraj wydarzyło.",
            changes_made="[Filar IV] Zmiana szyku zdania"
        ),
        RefinedLine(
            id=2,
            refined_pl="Pójdziemy  tam   jutro rano.",
            changes_made="[Filar LX] Usunięcie podwójnych spacji"
        ),
        RefinedLine(
            id=3,
            refined_pl="To absolutnie niedopuszczalne!",
            changes_made="[Filar IV] Usunięcie dosłownej kalki"
        ),
    ])
    mock_client.models.generate_content.return_value = mock_response

    verifier = DialogueVerifier(client=mock_pool)
    batch_items = [
        {"id": 1, "en": "I know about everything that happened yesterday.", "pl": "Wiem o wszystkim, co się wczoraj wydarzyło."},
        {"id": 2, "en": "We will go there tomorrow morning.", "pl": "Pójdziemy tam jutro rano."},
        {"id": 3, "en": "That is completely unacceptable.", "pl": "To jest kompletnie nie do przyjęcia."},
    ]

    result = verifier.verify_batch(batch_items=batch_items)
    assert len(result) == 3
    # 1. Identyczny tekst -> changes_made zresetowane do None
    assert result[0].changes_made is None
    # 2. Tożsamy semantycznie / po normalizacji spacji -> changes_made zresetowane do None
    assert result[1].changes_made is None
    # 3. Rzeczywista zmiana leksykalna -> changes_made zachowane
    assert result[2].changes_made == "[Filar IV] Usunięcie dosłownej kalki"


@pytest.mark.unit
@pytest.mark.parametrize(
    "prev_pl,f1_pl,f2_pl,source_en,kwargs,expected_output",
    [
        # Kategoria 17: ellipsis_continuation_syntax - ochrona wielokropka i małej litery
        (
            "Jeśli nie zdążymy na czas...",
            "...stracimy szansę na ucieczkę.",
            "Stracimy szansę na ucieczkę.",
            "We will lose our chance to escape.",
            {},
            "...stracimy szansę na ucieczkę."
        ),
        # Kategoria 18: first_person_modal_and_conditional_loss - ochrona trybu przypuszczającego 1. os.
        (
            None,
            "Wolałbym tego nie robić w tej chwili.",
            "Lepiej tego nie robić w tej chwili.",
            "I would rather not do this right now.",
            {},
            "Wolałbym tego nie robić w tej chwili."
        ),
        # Kategoria 19: past_to_present_tense_shift - ochrona czasu przeszłego
        (
            None,
            "Zrobiłem wszystko, o co prosiłeś.",
            "Robię wszystko, o co prosisz.",
            "I did everything you asked for.",
            {},
            "Zrobiłem wszystko, o co prosiłeś."
        ),
        # Kategoria 20: over_application_italics - usunięcie nadmiarowej kursywy w dialogu z adresatem
        (
            None,
            "Musimy natychmiast ruszać w drogę!",
            "{\\i1}Musimy natychmiast ruszać w drogę!{\\i0}",
            "We have to get moving immediately!",
            {"is_internal_monologue": False, "target_gender": "MALE"},
            "Musimy natychmiast ruszać w drogę!"
        ),
        # Kontrprzykład: poprawna redakcja bez naruszenia invariantów zostaje zaakceptowana
        (
            None,
            "To jest moja osobista sprawa.",
            "To moja prywatna sprawa.",
            "That is my personal matter.",
            {},
            "To moja prywatna sprawa."
        ),
    ]
)
def test_guard_phase2_preserves_ellipsis_continuation_conditional_and_past_tense(
    prev_pl, f1_pl, f2_pl, source_en, kwargs, expected_output
):
    """
    T4.6 (Operacja 2C.2 & 2C.6): Weryfikacja ochrony ciągłości zdań z wielokropkiem,
    trybu przypuszczającego 1. os., czasu przeszłego oraz nadmiarowej kursywy.
    """
    res = DialogueVerifier._guard_phase2_regressions(
        f1_pl=f1_pl,
        refined_pl=f2_pl,
        source_en=source_en,
        prev_line_pl=prev_pl,
        **kwargs
    )
    assert res == expected_output


# ==============================================================================
# STANDARD 9.5 TESTS (T5.2, T5.6)
# ==============================================================================

@pytest.mark.unit
@pytest.mark.parametrize(
    "f1_pl,refined_pl,spk_p0,has_ver,expected_output",
    [
        # 1. Mówca P0 męski: próba wprowadzenia formy żeńskiej -łam -> wymuszenie męskiej -łem
        ("Wróciłem do domu przed zmrokiem.", "Wróciłam do domu przed zmrokiem.", "MALE", True, "Wróciłem do domu przed zmrokiem."),
        # 2. Mówca P0 męski z formą przypuszczającą: -łabym -> -łbym
        ("Zrobiłbym to inaczej.", "Zrobiłabym to inaczej.", "MASCULINE", True, "Zrobiłbym to inaczej."),
        # 3. Mówca P0 żeński: próba wprowadzenia formy męskiej -łem -> wymuszenie żeńskiej -łam
        ("Czekałam na ciebie pod bramą.", "Czekałem na ciebie pod bramą.", "FEMALE", True, "Czekałam na ciebie pod bramą."),
        # 4. Kontrprzykład: mówca P0 męski i zachowana poprawna forma męska -> brak ingerencji
        ("Znalazłem rozwiązanie.", "Odnazłem właściwe rozwiązanie.", "MALE", True, "Odnazłem właściwe rozwiązanie."),
    ]
)
def test_guard_phase2_enforces_p0_speaker_gender_on_past_tense_shift(
    f1_pl, refined_pl, spk_p0, has_ver, expected_output
):
    """
    T5.2 (Operacja 2B.2): Prawidłowy stan wyjścia _guard_phase2_regressions dla mówcy o zweryfikowanym p0_gender
    = zachowanie/wymuszenie formy zgodnej z p0_gender mówcy (źródło autorytetu: rekord P0).
    """
    res = DialogueVerifier._guard_phase2_regressions(
        f1_pl=f1_pl,
        refined_pl=refined_pl,
        speaker_p0_gender=spk_p0,
        has_verified_gender=has_ver
    )
    assert res == expected_output


@pytest.mark.unit
@pytest.mark.parametrize(
    "prev_pl,prev_en,f1_pl,refined_pl,expected_output",
    [
        # 1. Poprzednia linia kończy się '...', bieżąca nie ma '...' w F1 ani F2 -> dodanie '... '
        (
            "Nasz plan...",
            "Our plan...",
            "Zostanie zrealizowany jutro.",
            "Zostanie zrealizowany jutro.",
            "... zostanie zrealizowany jutro."
        ),
        # 2. Linia z kursywą {\\i1}...{\\i0} -> '... ' wewnątrz znacznika kursywy
        (
            "Gdybyśmy tylko...",
            "If only we...",
            r"{\i1}Mieli więcej czasu.{\i0}",
            r"{\i1}Mieli więcej czasu.{\i0}",
            r"{\i1}... mieli więcej czasu.{\i0}"
        ),
        # 3. Kontrprzykład: poprzednia linia kończy się kropką w EN (nie jest zawieszonym zdaniem) -> brak dodawania '...'
        (
            "Koniec części pierwszej.",
            "End of part one.",
            "Rozpoczynamy naradę.",
            "Rozpoczynamy naradę.",
            "Rozpoczynamy naradę."
        ),
    ]
)
def test_guard_phase2_bridges_ellipsis_continuation_across_nominal_opening_line(
    prev_pl, prev_en, f1_pl, refined_pl, expected_output
):
    """
    T5.6 (Operacja 2C.5): Prawidłowy stan drugiej linii po linii zakończonej '...'
    = obecność inicjalnego wielokropka '...' zapewniającego ciągłość składniową.
    """
    res = DialogueVerifier._guard_phase2_regressions(
        f1_pl=f1_pl,
        refined_pl=refined_pl,
        prev_line_pl=prev_pl,
        prev_line_en=prev_en
    )
    assert res == expected_output


# ==============================================================================
# STANDARD 9.6 TESTS (T6.2, T6.5)
# ==============================================================================
@pytest.mark.unit
@pytest.mark.parametrize(
    "source_en,f1_pl,refined_pl,is_internal_monologue,expected_pl",
    [
        (
            r"I'm just glad that {\i1}you{\i0} are!",
            "Cieszę się, że tobie nic nie jest",
            r"{\i1}Cieszę się, że tobie nic nie jest{\i0}",
            False,
            "Cieszę się, że tobie nic nie jest",
        ),
        (
            r"{\i1}Maybe this space is like magical girls.{\i0}",
            r"{\i1}Cieszę się, że tobie nic nie jest{\i0}",
            r"{\i1}Cieszę się, że tobie nic nie jest{\i0}",
            True,
            r"{\i1}Cieszę się, że tobie nic nie jest{\i0}",
        ),
    ],
)
def test_guard_phase2_strips_whole_line_italics_when_source_en_has_only_partial_emphasis(
    source_en, f1_pl, refined_pl, is_internal_monologue, expected_pl
):
    from verifier import DialogueVerifier

    out = DialogueVerifier._guard_phase2_regressions(
        f1_pl=f1_pl,
        refined_pl=refined_pl,
        source_en=source_en,
        is_internal_monologue=is_internal_monologue,
        target_gender="FEMININE",
    )
    assert out == expected_pl



@pytest.mark.unit
@pytest.mark.parametrize(
    "f1_pl,raw_f2_pl,raw_reason,expected_refined_pl,expected_changes_made",
    [
        (
            r"{\i1}Może pójdę z HeroAlphonem\NCieszę się, że tobie nic nie jest{\i0}",
            "{\\i1}Może pójdę z HeroAlphonem\nCieszę się, że tobie nic nie jest{\\i0}",
            "[Filar I] Zmiana podziału wiersza.",
            r"{\i1}Może pójdę z HeroAlphonem\NCieszę się, że tobie nic nie jest{\i0}",
            None,
        ),
        (
            r"Może pójdę z HeroAlphonem\NCieszę się, że tobie nic nie jest",
            r"Może pójdę z HeroAlphonem\nCieszę się, że tobie nic nie jest",
            "[Filar II] Korekta.",
            r"Może pójdę z HeroAlphonem\NCieszę się, że tobie nic nie jest",
            None,
        ),
    ],
)
def test_verify_batch_normalizes_lowercase_newlines_to_ass_uppercase_before_comparison(
    f1_pl, raw_f2_pl, raw_reason, expected_refined_pl, expected_changes_made
):
    from verifier import DialogueVerifier

    norm_pl, norm_reason = DialogueVerifier.normalize_phase2_line_and_reason(
        f1_pl=f1_pl, refined_pl=raw_f2_pl, changes_made=raw_reason
    )
    assert norm_pl == expected_refined_pl
    assert "\n" not in norm_pl
    assert norm_reason is expected_changes_made


# ==============================================================================
# STANDARD 9.7 TESTS (T7.3)
# ==============================================================================
@pytest.mark.unit
@pytest.mark.parametrize(
    "f1_pl,f2_pl_with_linebreak,raw_reason,expected_changes_made",
    [
        (
            "Nie wiem czy to prawda",
            "Nie wiem\\Nczy to prawda",
            None,
            None,
        ),
        (
            "{\\i1}Nie wiem czy to prawda{\\i0}",
            "{\\i1}Nie wiem\\Nczy to prawda{\\i0}",
            None,
            None,
        ),
    ],
)
def test_normalize_phase2_treats_space_to_ass_newline_wrapping_as_lexical_identity(
    f1_pl, f2_pl_with_linebreak, raw_reason, expected_changes_made
):
    from verifier import DialogueVerifier

    norm_pl, norm_reason = DialogueVerifier.normalize_phase2_line_and_reason(
        f1_pl=f1_pl, refined_pl=f2_pl_with_linebreak, changes_made=raw_reason
    )
    assert "\\N" in norm_pl
    assert norm_reason is expected_changes_made
    assert DialogueVerifier.is_lexically_identical_ignoring_linebreak(f1_pl, norm_pl) is True


# ==============================================================================
# STANDARD 9.10 TESTS (T10.4)
# ==============================================================================


@pytest.mark.unit
@pytest.mark.parametrize(
    "line1_pl,line2_f1,line2_f2_mutated,expected_line2",
    [
        (
            "Jeśli tam pójdziemy...",
            "...odkryjemy prawdę.",
            "odkryjemy prawdę.",
            "...odkryjemy prawdę.",
        ),
        (
            "odkryjemy prawdę...",
            "...Jeśli tam pójdziemy.",
            "Jeśli tam pójdziemy.",
            "...Jeśli tam pójdziemy.",
        ),
    ],
)
def test_verify_batch_passes_adjacent_prev_line_to_ellipsis_continuation_guard(
    monkeypatch, line1_pl, line2_f1, line2_f2_mutated, expected_line2
):
    from unittest.mock import MagicMock
    from verifier import DialogueVerifier, RefinedBatchResponse, RefinedLine
    from context_cache import ContextCacheManager

    monkeypatch.setattr(ContextCacheManager, "get_or_create_cache", lambda *a, **kw: "mock_cache")
    mock_pool = MagicMock()
    mock_client = MagicMock()
    mock_pool.get_client.return_value = mock_client
    mock_pool.clients = [mock_client]
    mock_resp = MagicMock()
    mock_resp.text = "{}"
    mock_resp.parsed = RefinedBatchResponse(
        lines=[
            RefinedLine(id=1, refined_pl=line1_pl, changes_made=None),
            RefinedLine(id=2, refined_pl=line2_f2_mutated, changes_made="[Filar I] Korekta"),
        ]
    )
    mock_client.models.generate_content.return_value = mock_resp

    verifier = DialogueVerifier(client=mock_pool)
    batch_items = [
        {"id": 1, "en": "If only we knew...", "pl": line1_pl},
        {"id": 2, "en": "...we would have avoided this ambush.", "pl": line2_f1},
    ]
    res = verifier.verify_batch(batch_items=batch_items)
    assert res[1].refined_pl == expected_line2
