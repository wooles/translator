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
