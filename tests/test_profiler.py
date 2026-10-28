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
        # Tokiyuki Hōjō / Ayako z Nige Jouzu no Wakagimi S2 (SeriesBible P0)
        ("Ayako", "FEMALE", False, True, True, False),
        ("Yorishige Suwa", "MALE", True, False, False, True),
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
