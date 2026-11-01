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
