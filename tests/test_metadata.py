import pytest
from pathlib import Path
from metadata import clean_anime_filename, normalize_anime_slug
from pipeline_logger import EpisodeFlightRecorder


def test_clean_slug_consistency_and_single_header_logging(tmp_path):
    # 1. Verification of clean_anime_filename and normalize_anime_slug
    # on diverse release strings (without using forbidden anime names)
    sample_releases = [
        ("[SubGroup] Brave Adventurer - 01 [1080p HEVC][12345678].mkv", "Brave Adventurer", "brave_adventurer"),
        ("Brave.Adventurer.S01E05.1080p.WEB-DL.x264.mkv", "Brave Adventurer", "brave_adventurer"),
        ("[ReleaseHub] Mystic Kingdom Season 2 - 12 (720p).ass", "Mystic Kingdom Season 2", "mystic_kingdom"),
        ("Silver_Knight_EP08_REPACK_1080p.mkv", "Silver Knight", "silver_knight"),
    ]

    for raw, expected_clean, expected_slug in sample_releases:
        cleaned = clean_anime_filename(raw)
        slug = normalize_anime_slug(raw)
        assert expected_clean.lower() in cleaned.lower(), f"Błąd czyszczenia '{raw}': otrzymano '{cleaned}'"
        assert expected_slug == slug, f"Błąd sluga '{raw}': oczekiwano '{expected_slug}', otrzymano '{slug}'"

    # 2. Verification of EpisodeFlightRecorder clean_slug consistency and log_cli_init idempotency
    log_dir = tmp_path / "test_flight_logs"
    recorder = EpisodeFlightRecorder(
        anime_slug="brave_adventurer",
        filename="Brave_Adventurer_01",
        trace_dir=log_dir,
        enabled=True
    )

    # Calling log_cli_init multiple times MUST be idempotent: header written exactly ONCE
    recorder.log_cli_init(
        cli_args={"subs_path": "input.ass"},
        paths={"input": "input.ass"},
        models={"main": "test-model"}
    )
    recorder.log_cli_init(
        cli_args={"subs_path": "input.ass"},
        paths={"input": "input.ass"},
        models={"main": "test-model"}
    )

    # Log metadata (KROK 3)
    recorder.log_metadata(
        clean_slug=recorder.anime_slug,
        anilist_meta={"title": "Brave Adventurer"},
        actor_mappings={"Knight": "Rycerz"}
    )

    # Log series bible (KROK 6)
    bible_summary = {
        "slug": recorder.anime_slug,
        "characters_count": 2,
        "declensions_count": 2
    }
    recorder.log_series_bible(
        bible_summary=bible_summary,
        character_registry={"Rycerz": "MĘŻCZYZNA"},
        relations={},
        declensions={"Rycerz": {"M": "Rycerz", "D": "Rycerza"}}
    )

    # Read log file and verify assertions
    log_content = recorder.log_path.read_text(encoding="utf-8")
    
    # Exactly one CLI init header
    assert log_content.count("[KROK 1: CLI & INICJALIZACJA PROCESU]") == 1, (
        "Nagłówek KROK 1 powinien wystąpić dokładnie jeden raz!"
    )
    # Both KROK 3 and KROK 6 must be recorded with consistent slug
    assert "[KROK 3: METADANE ZEWNĘTRZNE I NORMALIZACJA AKTORÓW]" in log_content
    assert "[KROK 6: PAMIĘĆ SERII SERIESBIBLE I PARADYGMATY ODMIANY]" in log_content
    assert "Znormalizowany slug serii: brave_adventurer" in log_content
    assert '"slug": "brave_adventurer"' in log_content


from profiler import EpisodeProfiler

# Test dla Sekcji 2B.2
@pytest.mark.parametrize(
    "actor_tag,known_female_entities,asr_text,time_gap_sec,expected_gender,expected_asr",
    [
        ("EntityAlpha", {"EntityAlpha": "FEMALE"}, "powtórzone_audio", 10.5, "FEMALE", ""),
        ("EntityBeta", {"EntityBeta": "FEMALE"}, "bieżące_audio", 0.2, "FEMALE", "bieżące_audio"),
    ],
)
def test_actor_normalization_exact_token_and_asr_window_isolation(
    actor_tag, known_female_entities, asr_text, time_gap_sec, expected_gender, expected_asr
):
    """Weryfikuje dokładne dopasowanie tokenu aktora oraz izolację okna czasowego ASR względem duplikatów."""
    sanitized_asr = EpisodeProfiler.sanitize_event_asr(
        raw_asr=asr_text,
        is_sign=False,
        duplicate_time_distance_sec=time_gap_sec,
    )
    assert known_female_entities[actor_tag] == expected_gender
    assert sanitized_asr == expected_asr

