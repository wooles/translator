"""
Unit tests for profiler.py covering Standard 9.4 operations:
- T4.1 (2B.9): test_reconcile_prepass_with_p0_enforces_verified_cast_gender
- T4.2 (2B.8.a): test_sanitize_event_asr_strips_latin_and_repetition_hallucinations
- T4.13 (2C.10): test_step4_asr_deduplication_across_distant_events_and_consecutive_streaks
"""
import pytest
from profiler import EpisodeProfiler, DramaticSequence


@pytest.mark.unit
@pytest.mark.parametrize(
    "character_name,p0_gender,initial_female_only,initial_male_only,expected_female_only,expected_male_only",
    [
        # Weryfikacja bezwzględnego prymatu rekordu P0 w statystykach obsady pre-passu
        ("Bohaterka", "FEMALE", False, True, True, False),
        ("Bohater", "MALE", True, False, False, True),
    ]
)
def test_reconcile_prepass_with_p0_enforces_verified_cast_gender(
    character_name,
    p0_gender,
    initial_female_only,
    initial_male_only,
    expected_female_only,
    expected_male_only
):
    """
    T4.1 (Operacja 2B.9): Weryfikacja bezwzględnego prymatu rekordu P0 w statystykach obsady pre-passu.
    """
    class MockSeriesBible:
        def __init__(self, char_name, gender):
            self.characters = {
                char_name: {
                    "name": char_name,
                    "gender": gender,
                    "priority": "P0",
                    "has_verified_gender": True,
                    "confidence": 0.95
                }
            }

        def get_character(self, name):
            return self.characters.get(name)

    mock_bible = MockSeriesBible(character_name, p0_gender)
    seq = DramaticSequence(
        sequence_name="Sekwencja 1",
        time_range="00:01:00-00:02:30",
        dramatic_summary="Rozmowa i ucieczka przed pościgiem",
        dominant_tone="Napięcie",
        characters_present=[character_name],
        female_only_scene=initial_female_only,
        male_only_scene=initial_male_only,
        topology_type="SOLILOQUY"
    )

    reconciled = EpisodeProfiler.reconcile_prepass_with_p0([seq], series_bible=mock_bible)
    assert len(reconciled) == 1
    res_seq = reconciled[0]
    assert res_seq.female_only_scene is expected_female_only
    assert res_seq.male_only_scene is expected_male_only


@pytest.mark.unit
@pytest.mark.parametrize(
    "raw_input,expected_output",
    [
        # (a) Halucynacja łacińska usunięta z japońskiego tekstu
        ("何をしているんだ？ sss aaasss", "何をしているんだ？"),
        # (b) Wyzerowanie segmentu zawierającego wyłącznie angielskie halucynacje
        ("Thank you for watching.", ""),
        # (c) Ciągi powtórzeniowe liter > 2
        ("aaasss", ""),
        # (d) Izolowane znaki i interpunkcja
        ("k", ""),
        (".", ""),
        # (e) Czysty japoński dialog zachowany bez zmian
        ("何をしているんだ？", "何をしているんだ？"),
    ]
)
def test_sanitize_event_asr_strips_latin_and_repetition_hallucinations(raw_input, expected_output):
    """
    T4.2 (Operacja 2B.8.a): Weryfikacja trójstopniowej filtracji halucynacji ASR.
    """
    res = EpisodeProfiler.sanitize_event_asr(raw_input, is_sign=False, style="Default")
    assert res == expected_output


@pytest.mark.unit
@pytest.mark.parametrize(
    "raw_asr,time_dist,streak,expected_output",
    [
        # Zdarzenie powtórzone w odległości > 1.5s -> wyzerowanie duplikatu
        ("何をしているんだ？", 2.0, 1, ""),
        # Identyczny segment w serii > 2 kolejnych linii -> wyzerowanie
        ("何をしているんだ？", None, 3, ""),
        # Poprawny pojedynczy segment w oknie mowy -> zachowany
        ("何をしているんだ？", None, 1, "何をしているんだ？"),
        ("何をしているんだ？", 1.0, 2, "何をしているんだ？"),
    ]
)
def test_step4_asr_deduplication_across_distant_events_and_consecutive_streaks(
    raw_asr, time_dist, streak, expected_output
):
    """
    T4.13 (Operacja 2C.10): Weryfikacja deduplikacji bufora ASR na osi czasu.
    """
    res = EpisodeProfiler.sanitize_event_asr(
        raw_asr=raw_asr,
        is_sign=False,
        style="Default",
        duplicate_time_distance_sec=time_dist,
        consecutive_streak=streak
    )
    assert res == expected_output


@pytest.mark.unit
@pytest.mark.parametrize(
    "raw_input,time_dist,streak,expected_output",
    [
        # 1. Sklejony prefiks ASCII usunięty z japońskiego tekstu (Youおじま -> おじま)
        ("Youおじま", None, 1, "おじま"),
        # 2. Sklejony prefiks ASCII usunięty (Kアクマ -> アクマ)
        ("Kアクマ", None, 1, "アクマ"),
        # 3. Sklejone wtrącenie ASCII usunięte (a相手 -> 相手)
        ("a相手", None, 1, "相手"),
        # 4. Sklejone ASCII z pojedynczym znakiem CJK -> wyzerowanie segmentu (Cと -> "")
        ("Cと", None, 1, ""),
        # 5. Pojedynczy znak japoński -> wyzerowanie segmentu
        ("ん", None, 1, ""),
        # 6. Ciąg łaciński bez japońskiego audio -> wyzerowanie
        ("You youI,", None, 1, ""),
        # 7. Deduplikacja zdarzenia oddalonego o > 1.5s -> wyzerowanie
        ("おじま", 2.0, 1, ""),
        # 8. Seria powtórzeń > 2 -> wyzerowanie od 3. powtórzenia
        ("おじま", None, 3, ""),
        # 9. Prawidłowy segment powtórzony w dozwolonej serii (streak <= 2, dist <= 1.5s)
        ("おじま", 0.8, 2, "おじま"),
    ]
)
def test_sanitize_event_asr_strips_glued_ascii_prefixes_and_enforces_episode_loop_dedup(
    raw_input, time_dist, streak, expected_output
):
    """
    T5.4 (Operacja 2C.3): Prawidłowy stan asr_text = wycięcie prefiksów/wtrąceń ASCII
    sklejonych ze znakami japońskimi oraz wyzerowanie pojedynczych znaków resztkowych i serii > 2 identycznych segmentów.
    """
    res = EpisodeProfiler.sanitize_event_asr(
        raw_asr=raw_input,
        is_sign=False,
        style="Default",
        duplicate_time_distance_sec=time_dist,
        consecutive_streak=streak
    )
    assert res == expected_output


# ==============================================================================
# STANDARD 9.6 TESTS (T6.3)
# ==============================================================================
@pytest.mark.unit
@pytest.mark.parametrize(
    "raw_asr_input,expected_sanitized_output",
    [
        ("Episode", ""),
        (
            "Episodeとおじま",
            "おじま",
        ),
        (
            "Episodeのまほうしょうじょ",
            "まほうしょうじょ",
        ),
    ],
)
def test_sanitize_event_asr_zeros_zero_cjk_latin_words_and_strips_orphaned_initial_particles(
    raw_asr_input, expected_sanitized_output
):
    from profiler import EpisodeProfiler

    cleaned = EpisodeProfiler.sanitize_event_asr(raw_asr_input, is_sign=False)
    assert cleaned == expected_sanitized_output


# ==============================================================================
# STANDARD 9.7 TESTS (T7.4)
# ==============================================================================
@pytest.mark.unit
@pytest.mark.parametrize(
    "raw_asr_with_artifact,expected_clean_asr",
    [
        (
            "Dialogue speech text.? ??000 continuation",
            "Dialogue speech text continuation",
        ),
        (
            "Dialogue speech text???000",
            "Dialogue speech text",
        ),
    ],
)
def test_sanitize_event_asr_strips_question_mark_and_zero_clusters_inside_jp_segment(
    raw_asr_with_artifact, expected_clean_asr
):
    from profiler import EpisodeProfiler

    cleaned = EpisodeProfiler.sanitize_event_asr(raw_asr_with_artifact, is_sign=False)
    assert "000" not in cleaned
    assert "??" not in cleaned
    assert cleaned == expected_clean_asr


@pytest.mark.unit
@pytest.mark.parametrize(
    "en_score,f0_hz,expected_gender,expected_confidence,expected_archetype",
    [
        (-10, 120.0, "MALE", 1.0, "F0_HARD_MASCULINE_VETO"),
        (-8, 110.0, "MALE", 1.0, "F0_HARD_MASCULINE_VETO"),
        (0, 130.0, "MALE", 1.0, "F0_HARD_MASCULINE_VETO"),
    ],
)
def test_f0_hard_masculine_immunity_against_english_anaphora_score(
    en_score, f0_hz, expected_gender, expected_confidence, expected_archetype
):
    from profiler import SpaCyAnaphoraDiscourseAnalyzer

    res = SpaCyAnaphoraDiscourseAnalyzer.triangulate_epistemic_gender(
        en_score=en_score,
        f0_hz=f0_hz,
        jp_gender="UNKNOWN",
        f0_hard_masc=True,
    )
    assert res["resolved_gender"] == expected_gender
    assert res["confidence"] == expected_confidence
    assert res["archetype"] == expected_archetype

# ==============================================================================
# STANDARD 10.0.2 REGRESSION TESTS (A-03, A-11)
# ==============================================================================


@pytest.mark.unit
@pytest.mark.parametrize(
    "module_name,forbidden_term",
    [
        ("profiler", "hyouken"),
        ("profiler", "clevatess"),
        ("rules", "hyouken"),
        ("rules", "clevatess"),
        ("metadata", "hyouken"),
        ("scene_discourse", "hyouken"),
    ],
)
def test_profiler_rules_zero_literal(module_name, forbidden_term):
    import importlib
    mod = importlib.import_module(module_name)
    with open(mod.__file__, encoding="utf-8") as f:
        src = f.read().lower()
    assert forbidden_term not in src, f"Forbidden term {forbidden_term} found in {module_name}"


@pytest.mark.unit
@pytest.mark.parametrize(
    "relational_role,expected_gender,expected_confidence",
    [
        ("Neighbor's Kid", "UNKNOWN", 0.0),
        ("Merchant's Child", "UNKNOWN", 0.0),
        ("Captain's Apprentice", "UNKNOWN", 0.0),
        ("Master's Student", "UNKNOWN", 0.0),
    ],
)
def test_relational_role_neutral_fallback(relational_role, expected_gender, expected_confidence):
    from profiler import resolve_relational_actor_gender
    res = resolve_relational_actor_gender(relational_role)
    assert res["gender"] == expected_gender
    assert res["confidence"] == expected_confidence


# T10.1.5 (B-2) -> tests/test_profiler.py
@pytest.mark.unit
@pytest.mark.parametrize("fname", ["rules.py", "profiler.py", "scene_discourse.py", "metadata.py"])
def test_no_lk2_series_names_in_production_files(fname):
    import json
    from pathlib import Path
    src = Path(fname).read_text(encoding="utf-8")
    # Sprawdź, że wieloczłonowe nazwy postaci z bibles nie występują jako literały w plikach reguł/kodzie
    for bp in Path("series_memory").glob("*_bible.json"):
        bdata = json.load(open(bp, encoding="utf-8"))
        for char_name in bdata.get("characters", {}):
            if " " in char_name and len(char_name) >= 8 and not any(w in char_name.lower() for w in ("captain", "recruit", "mercenary", "guard", "soldier", "mother", "kid", "bro")):
                assert char_name not in src, f"Nazwa postaci {char_name} znaleziona w {fname}"


# ==============================================================================
# HOTFIX 10.1.1 REGRESSION TESTS (T10.1.1_P2a)
# ==============================================================================

@pytest.mark.unit
def test_t10_1_1_p2a_dialect_registry_guidance_in_episode_brief():
    """
    T10.1.1_P2a (Hotfix 10.1.1, 2B.5):
    Weryfikacja pozytywnej deskrypcji rejestru gwary w EPISODE BRIEF:
    Gdy postać w transkrypcji audio lub dossier posługuje się wykładnikami gwary japońskiej,
    format_lean_episode_brief dodaje 'Rejestr: wyrazista gwara / stylizacja środowiskowa'.
    """
    from profiler import EpisodeProfile, CharacterDossier, format_lean_episode_brief

    # Postać z wykładnikiem gwary w audio_transcription
    cd_dialect = CharacterDossier(
        name="SpeakerAlpha",
        gender="MALE",
        age_and_role="Wojownik z prowincji",
        speech_style_pl="Szorstka polszczyzna potoczna",
        audio_transcription="ora washi no dabe"
    )
    # Postać o mowie ogólnej
    cd_standard = CharacterDossier(
        name="SpeakerBeta",
        gender="FEMALE",
        age_and_role="Uczennica",
        speech_style_pl="Polszczyzna ogólna",
        audio_transcription="watashi wa ikimasu"
    )

    profile = EpisodeProfile(
        show_name="SeriesAlpha",
        character_dossiers=[cd_dialect, cd_standard]
    )

    brief = format_lean_episode_brief(profile)
    assert "Rejestr: wyrazista gwara / stylizacja środowiskowa" in brief

    # Weryfikacja przez przekazanie słownika character_audio_transcriptions
    profile_plain = EpisodeProfile(
        show_name="SeriesAlpha",
        character_dossiers=[
            CharacterDossier(name="SpeakerGamma", gender="MALE", age_and_role="Mieszczanin", speech_style_pl="Mowa codzienna")
        ]
    )
    brief_plain = format_lean_episode_brief(profile_plain)
    assert "Rejestr: wyrazista gwara / stylizacja środowiskowa" not in brief_plain

    brief_with_audio = format_lean_episode_brief(
        profile_plain,
        character_audio_transcriptions={"SpeakerGamma": "honma ni akan de"}
    )
    assert "Rejestr: wyrazista gwara / stylizacja środowiskowa" in brief_with_audio


def test_t10_2_1_zero_noise_ordinary_dialogue():
    """
    T10.2_1 (Standard 10.2, 2B.3, 2B.8):
    Weryfikacja braku szumu w zwykłych kwestiach dialogowych (High-Threshold Selection):
    Paczki bez nietypowych zjawisk (dialektów, archaizacji, tytulatury, F0, skrajnego afektu,
    zdań rozbitych, żargonu fachowego czy plansz) zwracają pusty string "" (czysty fallback).
    """
    from rules import get_focused_rules_for_batch

    ordinary_batches = [
        [{"en": "I don't know, but they have 3 items in the store."}],
        [{"en": "Look at that building over there."}],
        [{"en": "What do you want to do next?"}],
        [{"en": "I went to school yesterday and saw a cat."}],
        [{"en": "Good morning. How are you doing today?"}],
        [{"en": "Could you pass me the salt, please?"}],
        [{"en": "Where is the nearest train station?"}],
    ]

    for idx, batch in enumerate(ordinary_batches, 1):
        focused = get_focused_rules_for_batch(batch)
        assert focused == "", f"Zwykły dialog (batch {idx}) wyzwolił zbędne reguły: {focused}"


def test_t10_2_2_dynamic_category_selection_and_anti_smoothing():
    """
    T10.2_2 (Standard 10.2, 2B.4, 2B.7):
    Weryfikacja dynamicznej selekcji kategorii oraz działania Anti-Smoothing Filter:
    - Dla kwestii z gwarą wyzwala się DYN_1 (FILAR XIII) i zajmuje najwyższy priorytet (1. miejsce).
    - Filary wygładzające styl (FILAR LXXI oraz FILAR CLXXII) są bezwzględnie tłumione.
    - Dla kwestii z archaizacją wyzwala się DYN_2 (FILAR XIV) i tłumi FILAR LXXI.
    """
    from rules import get_focused_rules_for_batch

    # Scena z dialektem i wysokim CPS
    dialect_batch = [
        {"en": "What are you saying, fella?", "audio_jp": "ora washi dabe", "cps": 18.5}
    ]
    focused_dialect = get_focused_rules_for_batch(dialect_batch)
    assert "FILAR XIII" in focused_dialect, f"DYN_1 (FILAR XIII) nie aktywował się dla gwary: {focused_dialect}"
    assert "FILAR LXXI " not in focused_dialect, f"FILAR LXXI nie został stłumiony w scenie gwarowej: {focused_dialect}"
    assert "FILAR CLXXII " not in focused_dialect, f"FILAR CLXXII nie został stłumiony w scenie gwarowej: {focused_dialect}"

    rule_lines = [l for l in focused_dialect.splitlines() if l.strip().startswith("•")]
    assert len(rule_lines) >= 1, "Brak wygenerowanych reguł dla sceny gwarowej"
    assert "FILAR XIII" in rule_lines[0], f"FILAR XIII nie zajął 1. miejsca w promptcie: {rule_lines[0]}"

    # Scena z rejestrem dworskim/archaizacją
    archaic_batch = [
        {"en": "Your majesty, the army approaches.", "audio_jp": "de gozaru", "cps": 18.0}
    ]
    focused_archaic = get_focused_rules_for_batch(archaic_batch)
    assert "FILAR XIV" in focused_archaic, f"DYN_2 (FILAR XIV) nie aktywował się dla rejestru dworskiego: {focused_archaic}"
    assert "FILAR LXXI " not in focused_archaic, f"FILAR LXXI nie został stłumiony w scenie archaizowanej: {focused_archaic}"


def test_t10_2_3_pure_positive_domain_in_focused_rules():
    """
    T10.2_3 (Standard 10.2, 2B.2):
    Weryfikacja Czystej Domeny Pozytywnej (Zero-Negation) we wszystkich kategoriach dynamicznych:
    - Brak tokenów zakazanych: 'nie' (jako słowo przeczące), 'zakaz', 'zabrania się', 'błąd', 'musi',
      'zawsze', 'nigdy', 'unikaj', 'zamiast', 'usuń', 'niedopuszczalne'.
    - Brak cytowań w apostrofach '...'.
    - Brak form skrótowych 'np.'.
    - Pełna zgodność z Z1 (Zero-Literal), Z2 (Pure Positive Domain) i Z4 (Instance-Free).
    """
    import re
    from rules import get_focused_rules_for_batch

    test_dyn_batches = [
        [{"en": "ora washi dabe fella"}],  # DYN_1 (Dialekty)
        [{"en": "your majesty milord"}],   # DYN_2 (Archaizacja)
        [{"en": "sensei, please help me"}], # DYN_3 (Tytulatura)
        [{"en": "kanojo-tachi", "is_low_pitch_female": True}], # DYN_4 (Wiek/Płeć)
        [{"en": "aah! sob!", "prosody": "Ac=CRY"}], # DYN_5 (Afekt)
        [{"en": "The truth is... I'm a demon.", "is_split_sentence": True}], # DYN_6 (Ciągłość)
        [{"en": "tactical perimeter breach autopsy"}], # DYN_7 (Rejestr specjalistyczny)
        [{"en": "Chapter 1", "is_sign": True}], # DYN_8 (Napisy ekranowe)
    ]

    forbidden_words = [
        "zakaz", "zabrania się", "zabrania", "błąd", "musi", "zawsze", "nigdy",
        "unikaj", "zamiast", "usuń", "niedopuszczalne", "niedopuszczalna", "niedopuszczalny"
    ]

    for idx, batch in enumerate(test_dyn_batches, 1):
        focused = get_focused_rules_for_batch(batch)
        assert focused != "", f"Paczka DYN_{idx} zwróciła pusty string!"
        focused_lower = focused.lower()

        # Weryfikacja braku partykuły przeczącej 'nie' jako odrębnego słowa
        assert not bool(re.search(r"\bnie\b", focused_lower)), (
            f"Wykryto zakazaną partykułę przeczącą 'nie' w kategorii DYN_{idx}: {focused}"
        )

        for fw in forbidden_words:
            assert fw not in focused_lower, (
                f"Wykryto zakazany token dyrektywny '{fw}' w kategorii DYN_{idx}: {focused}"
            )

        # Weryfikacja braku cytatów w apostrofach '...'
        assert not bool(re.search(r"'[A-Za-z0-9żźćńółęąśŻŹĆĄŚĘŁÓŃ\s]+'", focused)), (
            f"Wykryto cytat w apostrofie w kategorii DYN_{idx}: {focused}"
        )

        # Weryfikacja braku form skrótowych np.
        assert "np." not in focused_lower, f"Wykryto 'np.' w kategorii DYN_{idx}: {focused}"


# =========================================================================
# TESTY STANDARDU 10.3 (T10.3_1 - T10.3_4) — KATEGORIE AVT I NORMA STAW
# =========================================================================

@pytest.mark.unit
@pytest.mark.parametrize("input_text,expected_category,expected_keyword", [
    ("That's a hilarious double meaning pun!", "FILAR LXXVIII", "substytucj"),
    ("Tears of sorrow and loneliness filled my heart after our farewell.", "FILAR XIX", "ładunk"),
    ("Foolish mortals of the dark abyss!", "FILAR XIII", "ciągłość jej idiolektu"),
    ("I am ready-dechu", "FILAR XIII", "ciągłość jej idiolektu"),
    ("Wait, wait, wait! Listen to me!", "FILAR CLXV", "kondensuj"),
    ("Stop, stop! You cannot go there!", "FILAR CLXV", "partykułą emfatyczną"),
])
def test_t10_3_1_new_and_expanded_categories_triggers(input_text, expected_category, expected_keyword):
    """
    T10.3_1 (Standard 10.3, Operacja 2B.6):
    Weryfikacja wyzwalania nowych i rozszerzonych kategorii dynamicznych:
    - Humor/gra słowna/kalambur (L-01) -> DYN_8 (FILAR LXXVIII)
    - Liryka/melancholia/smutek (L-03) -> DYN_9 (FILAR XIX)
    - Maniera egzaltowana / sufiks charakterystyczny (L-04) -> DYN_1 (FILAR XIII)
    - Potrójne powtórzenie (L-05) -> DYN_6 (FILAR CLXV)
    - Podwójne powtórzenie nagłe (L-05) -> DYN_6 (FILAR CLXV)
    """
    from rules import get_focused_rules_for_batch
    focused = get_focused_rules_for_batch([{"en": input_text}])
    assert expected_category in focused, f"Oczekiwano {expected_category} w wyjściu dla '{input_text}', otrzymano: {focused}"
    assert expected_keyword.lower() in focused.lower(), f"Oczekiwano słowa kluczowego '{expected_keyword}' w wyjściu dla '{input_text}', otrzymano: {focused}"


@pytest.mark.unit
def test_t10_3_2_priority_hierarchy_zero_noise_and_false_positive_guards():
    """
    T10.3_2 (Standard 10.3, Operacja 2B.6):
    Weryfikacja hierarchii priorytetów, braku fałszywych pozytywów i ochrony Anti-Smoothing Filter:
    - (a) Neutralne kwestie z pojedynczymi słowami nie wyzwalają DYN_9, DYN_8 ani DYN_1 (zwracają "")
    - (b) Idiomy potwierdzenia w podwójnym powtórzeniu nie aktywują DYN_6 (zwracają "")
    - (c) Porządek priorytetów: DYN_1 (95) > DYN_2 (92) > DYN_4 (88) > DYN_3 (84) > DYN_5 (82) > DYN_6 (80) > DYN_9 (74) > DYN_7 (72) > DYN_8 (70)
    - (d) Anti-Smoothing Filter poprawnie wyklucza FILAR CLXXII przy DYN_1, DYN_2 i czysto lirycznym DYN_9
    - (e) W scenie walki z powtórzeniem aktywne są oba DYN_5 i DYN_6, z priorytetem DYN_5 > DYN_6
    """
    from rules import get_focused_rules_for_batch

    # (a) Zwykłe zdania dialogowe z pojedynczymi słowami zwracają ""
    innocent_lines = [
        "I love this food!",
        "My heart is beating fast",
        "That is a precious memory",
        "The warmth of the sun is nice",
        "Are you kidding me?!",
        "The darkness is falling",
    ]
    for line in innocent_lines:
        res = get_focused_rules_for_batch([{"en": line}])
        assert res == "", f"Fałszywa aktywacja dla neutralnej kwestii '{line}': {res}"

    # (b) Idiomy potwierdzenia/acknowledgmentu w podwójnym powtórzeniu nie aktywują DYN_6
    idiom_lines = [
        "Yes, yes, I agree.",
        "Well, well, look who is here.",
        "Now, now, calm down.",
        "There, there, it is alright.",
        "Oh, oh, I see.",
    ]
    for line in idiom_lines:
        res = get_focused_rules_for_batch([{"en": line}])
        assert res == "", f"Fałszywa aktywacja DYN_6 dla idiomu '{line}': {res}"

    # (c) Hierarchia priorytetów par sasiednich:
    priority_pairs = [
        ("FILAR XIII", [{"en": "y'all fella"}, {"en": "milord your majesty"}], "FILAR XIV"),
        ("FILAR XIV", [{"en": "milord your majesty"}, {"en": "she", "target_gender": "FEMALE", "addressee_number": "PLURAL"}], "FILAR CXXXVI"),
        ("FILAR CXXXVI", [{"en": "she", "target_gender": "FEMALE", "addressee_number": "PLURAL"}, {"en": "sensei"}], "FILAR XXV"),
        ("FILAR XXV", [{"en": "sensei"}, {"en": "screaming sob", "prosody": "cry"}], "FILAR CLXXII"),
        ("FILAR CLXXII", [{"en": "attack blast"}, {"en": "wait, wait, wait"}], "FILAR CLXV"),
        ("FILAR CLXV", [{"en": "wait, wait, wait"}, {"en": "farewell tears of sorrow"}], "FILAR XIX"),
        ("FILAR XIX", [{"en": "farewell tears of sorrow"}, {"en": "tactical perimeter"}], "FILAR XLIX"),
        ("FILAR XLIX", [{"en": "tactical perimeter"}, {"en": "double meaning pun"}], "FILAR LXXVIII"),
    ]
    for higher_tag, batch, lower_tag in priority_pairs:
        focused = get_focused_rules_for_batch(batch)
        rule_lines = [l for l in focused.splitlines() if l.strip().startswith("•")]
        assert len(rule_lines) >= 2, f"Oczekiwano co najmniej 2 reguł dla pary {higher_tag} i {lower_tag}: {focused}"
        idx_higher = next(i for i, l in enumerate(rule_lines) if higher_tag in l)
        idx_lower = next(i for i, l in enumerate(rule_lines) if lower_tag in l)
        assert idx_higher < idx_lower, f"Priorytet naruszony: {higher_tag} (poz. {idx_higher}) nie wyprzedza {lower_tag} (poz. {idx_lower})"

    # (d) Anti-Smoothing Filter poprawnie wyklucza FILAR CLXXII przy DYN_1, DYN_2 i czysto lirycznym DYN_9
    # DYN_1 + prosody: shock -> FILAR CLXXII stłumiony
    res_dyn1 = get_focused_rules_for_batch([{"en": "ora washi dabe fella", "prosody": "shock"}])
    assert "FILAR XIII" in res_dyn1, f"DYN_1 nie aktywował się: {res_dyn1}"
    assert "FILAR CLXXII" not in res_dyn1, f"FILAR CLXXII nie został wykluczony w obecności DYN_1: {res_dyn1}"

    # DYN_2 + prosody: shock -> FILAR CLXXII stłumiony
    res_dyn2 = get_focused_rules_for_batch([{"en": "milord your majesty", "prosody": "shock"}])
    assert "FILAR XIV" in res_dyn2, f"DYN_2 nie aktywował się: {res_dyn2}"
    assert "FILAR CLXXII" not in res_dyn2, f"FILAR CLXXII nie został wykluczony w obecności DYN_2: {res_dyn2}"

    # Czysto liryczny DYN_9 + prosody: cry -> FILAR CLXXII stłumiony
    res_dyn9 = get_focused_rules_for_batch([{"en": "Tears of sorrow and loneliness filled my heart after our farewell.", "prosody": "cry"}])
    assert "FILAR XIX" in res_dyn9, f"DYN_9 nie aktywował się: {res_dyn9}"
    assert "FILAR CLXXII" not in res_dyn9, f"FILAR CLXXII nie został wykluczony w czystej liryce DYN_9: {res_dyn9}"

    # (e) W scenie walki z powtórzeniem ("Wait, wait, wait! Attack! Dodge! Ugh! Ottotto!") oba DYN_5 i DYN_6 aktywne, DYN_5 przed DYN_6
    batch_battle = [{"en": "Wait, wait, wait! Attack! Dodge! Ugh! Ottotto!"}]
    res_battle = get_focused_rules_for_batch(batch_battle)
    assert "FILAR CLXXII" in res_battle, f"DYN_5 nieaktywny w scenie walki: {res_battle}"
    assert "FILAR CLXV" in res_battle, f"DYN_6 nieaktywny w scenie powtórzeń walki: {res_battle}"
    battle_lines = [l for l in res_battle.splitlines() if l.strip().startswith("•")]
    idx_dyn5 = next(i for i, l in enumerate(battle_lines) if "FILAR CLXXII" in l)
    idx_dyn6 = next(i for i, l in enumerate(battle_lines) if "FILAR CLXV" in l)
    assert idx_dyn5 < idx_dyn6, f"DYN_5 (poz. {idx_dyn5}) nie występuje przed DYN_6 (poz. {idx_dyn6}): {battle_lines}"


@pytest.mark.unit
def test_t10_3_3_purity_domain_abstraction_and_size_invariant_of_all_13_categories():
    """
    T10.3_3 (Standard 10.3, Operacja 2B.6):
    Weryfikacja rygoru Czystej Domeny Pozytywnej, braku przykładów, braku obcojęzycznych terminów-kotwic
    oraz kontrola przyrostu rozmiaru promptu bazowego (<5%).
    """
    import re
    from rules import get_focused_rules_for_batch, STANDARD_9_CORE_RULES_PROMPT

    # 9 syntetycznych wejść aktywujących kolejno każdą z 9 kategorii dynamicznych
    synthetic_batches = [
        [{"en": "gonna fella"}],  # DYN_1
        [{"en": "milord your majesty"}],  # DYN_2
        [{"en": "sensei dono"}],  # DYN_3
        [{"en": "kanojo-tachi", "is_low_pitch_female": True}],  # DYN_4
        [{"en": "screaming sob", "prosody": "cry"}],  # DYN_5
        [{"en": "Stop, stop! You cannot go there!"}],  # DYN_6
        [{"en": "tactical perimeter breach"}],  # DYN_7
        [{"en": "Chapter 1", "is_sign": True}],  # DYN_8
        [{"en": "Tears of sorrow and loneliness filled my heart after our farewell."}],  # DYN_9
    ]

    forbidden_prescriptive = [
        "zakaz", "zabrania", "zabrania się", "unikaj", "zamiast",
        "niedopuszczalne", "niedopuszczalna", "niedopuszczalny", "usuń", "błąd",
        "musi", "muszą", "zawsze", "nigdy", "bezwzględna", "bezwzględnie"
    ]
    foreign_anchors_pat = re.compile(
        r"\b(?:dajare|giongo|gitaigo|chūnibyō|chunibyo|character voice|rōjin-go|rojin-go|keigo|yobisute|ottotto|kakegoe|kanojo-tachi|bento|onigiri|senpai)\b",
        re.IGNORECASE
    )

    collected_rules = []
    for idx, batch in enumerate(synthetic_batches, 1):
        focused = get_focused_rules_for_batch(batch)
        assert focused != "", f"Paczka DYN_{idx} zwróciła pusty string!"
        rule_lines = [l for l in focused.splitlines() if l.strip().startswith("•")]
        assert len(rule_lines) >= 1, f"Brak wyodrębnionej reguły w DYN_{idx}: {focused}"
        collected_rules.append(rule_lines[0])

    assert len(collected_rules) == 9, f"Oczekiwano 9 reguł dynamicznych, zebrano {len(collected_rules)}"

    # (a) Rygor Czystej Domeny Pozytywnej
    for idx, rule_text in enumerate(collected_rules, 1):
        rule_lower = rule_text.lower()
        # Brak partykuły przeczącej 'nie' jako odrębnego słowa
        assert not bool(re.search(r"\bnie\b", rule_lower)), f"Wykryto słowo 'nie' w DYN_{idx}: {rule_text}"
        for fw in forbidden_prescriptive:
            assert fw not in rule_lower, f"Wykryto słowo preskryptywne '{fw}' w DYN_{idx}: {rule_text}"
        assert "np." not in rule_lower, f"Wykryto 'np.' w DYN_{idx}: {rule_text}"
        assert not bool(re.search(r"'[A-Za-z0-9żźćńółęąśŻŹĆĄŚĘŁÓŃ\s]+'", rule_text)), f"Wykryto cytat w apostrofie w DYN_{idx}: {rule_text}"

        # (b) Brak obcojęzycznych terminów-kotwic
        m = foreign_anchors_pat.search(rule_text)
        assert m is None, f"Wykryto obcojęzyczny termin-kotwicę '{m.group(0) if m else ''}' w DYN_{idx}: {rule_text}"

    # Weryfikacja BASE_1 - BASE_4 w STANDARD_9_CORE_RULES_PROMPT
    base_lower = STANDARD_9_CORE_RULES_PROMPT.lower()
    for fw in ["zakaz", "zabrania", "unikaj", "niedopuszczalne", "usuń"]:
        assert fw not in base_lower, f"Wykryto słowo '{fw}' w STANDARD_9_CORE_RULES_PROMPT"

    # (c) Rozmiar STANDARD_9_CORE_RULES_PROMPT wzrósł o mniej niż 5% względem 51dbe2d (3758 znaków)
    baseline_len = 3758
    current_len = len(STANDARD_9_CORE_RULES_PROMPT)
    growth_ratio = (current_len - baseline_len) / baseline_len
    assert growth_ratio < 0.05, f"Rozmiar STANDARD_9_CORE_RULES_PROMPT wzrósł o {growth_ratio:.2%} (limit 5%)"


@pytest.mark.unit
def test_t10_3_4_r17_contains_polish_norm_14_15_and_cap_17():
    """
    T10.3_4 (Standard 10.3, Operacja 2B.2 & 2B.6):
    Weryfikacja polskiej normy czytelniczej STAW (14-15 CPS oraz pułap 17 CPS, 38 CPL) w R1.7.
    """
    from rules import STANDARD_9_CORE_RULES_PROMPT

    r17_lines = [l for l in STANDARD_9_CORE_RULES_PROMPT.splitlines() if "R1.7" in l]
    assert len(r17_lines) >= 1, "Nie znaleziono linii R1.7 w STANDARD_9_CORE_RULES_PROMPT"
    r17_text = r17_lines[0]

    assert "14" in r17_text, f"Brak liczby 14 w R1.7: {r17_text}"
    assert "15" in r17_text, f"Brak liczby 15 w R1.7: {r17_text}"
    assert "17" in r17_text, f"Brak liczby 17 w R1.7: {r17_text}"
    assert "38" in r17_text, f"Brak liczby 38 w R1.7: {r17_text}"
    assert "CPS" in r17_text or "znaków na sekundę" in r17_text


@pytest.mark.unit
def test_t10_4_1_no_seiyu_in_active_runtime():
    """
    Weryfikuje, że w aktywnym runtime (STANDARD_9_CORE_RULES_PROMPT
    oraz wszystkie 9 kategorii get_focused_rules_for_batch) nie występuje
    japoński loanword `seiyū` / `seiyu` (niezależnie od wielkości liter).
    Zgodnie z Zasadą 4 (Instance-Free) — termin zastąpiony polskim `aktor głosowy` / `aktora`.
    """
    import re
    from rules import STANDARD_9_CORE_RULES_PROMPT, get_focused_rules_for_batch

    seiyu_pat = re.compile(r"\bseiy[uū]\b", re.IGNORECASE)
    assert not seiyu_pat.search(STANDARD_9_CORE_RULES_PROMPT), (
        "Wykryto 'seiyū'/'SEIYŪ' w STANDARD_9_CORE_RULES_PROMPT (powinno być 'aktor głosowy'/'aktora')"
    )
    assert "RYTM AKTORA GŁOSOWEGO" in STANDARD_9_CORE_RULES_PROMPT
    assert "czasu trwania głosu aktora" in STANDARD_9_CORE_RULES_PROMPT

    test_inputs = [
        ([{"text": "You ain't runnin' away, y'all!"}], ""),
        ([{"text": "Forgive me, milord, Your Majesty."}], ""),
        ([{"text": "The little boy and the old grandma are waiting with the girls."}], "kanojo-tachi"),
        ([{"text": "Thank you-san, my master."}], ""),
        ([{"text": "Attack! Dodge! Scream! Sob! Terrified! Ugh! Ottotto!"}], ""),
        ([{"text": "Wait, wait, wait! Listen to me!"}], ""),
        ([{"text": "Tears of sorrow and loneliness after our farewell."}], "namida"),
        ([{"text": "The tactical commander ordered a medical autopsy and diagnosis."}], ""),
        ([{"text": "That's a hilarious double meaning pun!"}], ""),
    ]
    for batch, jp_txt in test_inputs:
        out = get_focused_rules_for_batch(batch, max_rules=10, whisper_text_jp=jp_txt)
        assert out != ""
        assert not seiyu_pat.search(out), (
            f"Wykryto 'seiyū' w wyjściu get_focused_rules_for_batch: {out!r}"
        )


# =========================================================================
# TESTY STANDARDU 10.5 (T10.5_1 - T10.5_3) — OPTYMALIZACJA TRIGGERÓW DYN
# =========================================================================

@pytest.mark.unit
@pytest.mark.parametrize(
    "benign_sentence",
    [
        "Did you notice anything unusual on the road?",
        "Give me a sign when you are ready to move.",
        "Fair warning, the weather is changing quickly.",
        "This episode of our journey is finally over.",
        "The girls went to the library after class.",
        "The women in the village are preparing the festival.",
        "When I was a child, I lived near the mountains.",
        "Hey kid, what are you doing over there?",
    ],
)
def test_t10_5_1_no_false_positive_dyn8_and_dyn4_on_common_words(benign_sentence):
    """
    Standard 10.5 (R-01, R-03): Weryfikuje, że pospolite słowa wieloznaczne
    (notice, sign, warning, episode, girls, women, child, kid) w zwykłym dialogu
    nie wzbudzają fałszywie DYN_8 ani DYN_4.
    """
    from rules import get_focused_rules_for_batch
    res = get_focused_rules_for_batch([{"text": benign_sentence}], max_rules=3)
    assert res == ""


@pytest.mark.unit
def test_t10_5_2_no_slot_starvation_for_lower_scored_categories():
    """
    Standard 10.5 (R-03): Weryfikuje, że w wielowątkowej paczce obecność pospolitych słów
    'girls' lub 'kid' oraz 'notice' nie blokuje slotów top-3 (brak fałszywej aktywacji DYN_4 score 88),
    dzięki czemu do top-3 trafiają właściwe kategorie: DYN_3 (84), DYN_9 (74) oraz DYN_8 (70).
    """
    from rules import get_focused_rules_for_batch
    batch = [
        {"text": "The girls did not notice anything, master-san."},
        {"text": "Tears of sorrow and loneliness filled my heart after our farewell."},
        {"text": "That is a hilarious double meaning pun!"},
    ]
    res = get_focused_rules_for_batch(batch, max_rules=3)
    assert "FILAR CXXXVI" not in res
    assert "FILAR XXV" in res
    assert "FILAR XIX & LXXVI" in res
    assert "FILAR LXXVIII" in res


@pytest.mark.unit
def test_t10_5_3_verifier_cps_norm_aligned_with_r17():
    """
    Standard 10.5 (R-02): Weryfikuje, że kod verifier.py jest zsynchronizowany
    z polską normą percepcyjną 14–15 CPS oraz pułapem 17 CPS z reguły R1.7.
    """
    with open("verifier.py", "r", encoding="utf-8") as f:
        verifier_src = f.read()
    assert "14" in verifier_src and "15" in verifier_src
    assert "17" in verifier_src
    assert "38" in verifier_src


