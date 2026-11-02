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
    from metadata import normalize_actor_tag
    norm_actor, parsed_g = normalize_actor_tag(actor_tag)
    assert norm_actor == actor_tag
    assert sanitized_asr == expected_asr



# ==============================================================================
# STANDARD 9.4 TESTS (T4.10)
# ==============================================================================

@pytest.mark.unit
def test_step3_secondary_actors_populate_p1_and_p2_entries_in_series_bible(tmp_path):
    """
    T4.10 (Operacja 2C.7): Populacja postaci drugoplanowych z raw_actor_tags:
    - postacie z jawną płcią w nawiasie (np. 'Gojirō (M)') -> priority='P1', gender='MALE', confidence=0.70
    - postacie żeńskie (np. 'Shizuka (F)') -> priority='P1', gender='FEMALE', confidence=0.70
    - postacie bez płci (np. 'Żołnierz') -> priority='P2', gender='UNKNOWN', confidence=0.50
    - separatory ('/', '\\') i tagi techniczne (Sign, Txt) są odrzucane.
    """
    from series_memory import SeriesBible

    bible_file = tmp_path / "secondary_actors_test.json"
    bible = SeriesBible(bible_path=bible_file, storage_dir=tmp_path)

    raw_tags = [
        "Gojirō (M)",
        "Shizuka (F)",
        "Żołnierz",
        "/",
        "Sign",
        "Txt",
        ""
    ]

    bible.populate_secondary_actor_tags(raw_tags)
    chars = bible.data.get("characters", {})

    # 1. Postać męska z jawnym tagiem -> P1 MALE
    assert "Gojirō" in chars
    assert chars["Gojirō"]["priority"] == "P1"
    assert chars["Gojirō"]["gender"] == "MALE"
    assert chars["Gojirō"]["grammatical_gender"] == "MASCULINE"
    assert chars["Gojirō"]["confidence"] == 0.70
    assert chars["Gojirō"]["has_verified_gender"] is False

    # 2. Postać żeńska z jawnym tagiem -> P1 FEMALE
    assert "Shizuka" in chars
    assert chars["Shizuka"]["priority"] == "P1"
    assert chars["Shizuka"]["gender"] == "FEMALE"
    assert chars["Shizuka"]["grammatical_gender"] == "FEMININE"
    assert chars["Shizuka"]["confidence"] == 0.70

    # 3. Postać bez płci -> P2 UNKNOWN
    assert "Żołnierz" in chars
    assert chars["Żołnierz"]["priority"] == "P2"
    assert chars["Żołnierz"]["gender"] == "UNKNOWN"
    assert chars["Żołnierz"]["confidence"] == 0.50

    # 4. Separatory i napisy odrzucone
    assert "/" not in chars
    assert "Sign" not in chars
    assert "Txt" not in chars

# ==============================================================================
# STANDARD 10.0.2 REGRESSION TESTS (A-12)
# ==============================================================================


@pytest.mark.unit
@pytest.mark.parametrize(
    "anime_title",
    ["Clevatess", "Golden Kamuy", "Silent Witch"],
)
def test_get_anime_context_offline_bible(anime_title):
    from metadata import get_anime_context
    ctx = get_anime_context(f"[SubGroup] {anime_title} - 01.mkv")
    assert ctx is not None
    assert ctx.get("source") == "local_series_bible"
    assert "genres" in ctx
    assert "characters" in ctx
    assert len(ctx["characters"]) >= 2
