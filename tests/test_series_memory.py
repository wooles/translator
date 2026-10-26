import pytest
from series_memory import SeriesBible, EntityCategory, generate_polish_name_declension


def test_series_bible_entity_filtering_and_glossary_priority(tmp_path):
    bible_file = tmp_path / "test_series_bible.json"
    bible = SeriesBible(bible_path=bible_file)

    # 1. Update from episode profile with mixed entities:
    # - Real character
    # - Sign entry (is_sign: true)
    # - Generic roles (Boy A, Guard)
    # - Continuity bridge alert
    bible.update_from_episode_profile(
        episode_name="Episode 01",
        characters={
            "Artur Pendelton": {"description": "mężczyzna (bohater)", "gender": "MALE", "priority": "P0", "has_verified_gender": True},
            "Helena Pendelton": {"description": "kobieta (bohaterka)", "gender": "FEMALE", "priority": "P0", "has_verified_gender": True},
            "Sign Board": {"description": "szyld informacyjny", "is_sign": True},
            "Boy A": "chłopiec w tle",
            "Guard 1": "strażnik bramy",
            "Wydarzenie Przeszłe": {"description": "wspomnienie bitwy", "source": "continuity_bridge_alerts"}
        },
        glossary={
            "Pendelton": "Ród Pendeltonów",
            "Szermierz": "Mistrz Miecza"
        }
    )

    chars = bible.data.get("characters", {})
    decls = bible.data.get("declensions", {})

    # Signs, generic roles, and continuity bridge alerts must be completely filtered out
    assert "Sign Board" not in chars
    assert "Sign Board" not in decls
    assert "Boy A" not in chars
    assert "Boy A" not in decls
    assert "Guard 1" not in chars
    assert "Guard 1" not in decls
    assert "Wydarzenie Przeszłe" not in chars
    assert "Wydarzenie Przeszłe" not in decls

    # Real characters must be present
    assert "Artur Pendelton" in chars
    assert "Helena Pendelton" in chars

    # 2. Surname alias collision prohibition:
    # Artur (MALE) and Helena (FEMALE) share the surname "Pendelton".
    # The bare surname "Pendelton" must NOT be assigned as an alias to either!
    artur_aliases = chars["Artur Pendelton"].get("aliases", [])
    helena_aliases = chars["Helena Pendelton"].get("aliases", [])
    assert "Pendelton" not in artur_aliases
    assert "pendelton" not in [a.lower() for a in artur_aliases if len(a.split()) == 1]
    assert "Pendelton" not in helena_aliases
    assert "pendelton" not in [a.lower() for a in helena_aliases if len(a.split()) == 1]

    # First names should be present
    assert "Artur" in artur_aliases
    assert "Helena" in helena_aliases

    # 3. Canonical priority of EpisodeProfiler glossary definitions over auto-generated forms
    # Glossary defines "Szermierz" -> "Mistrz Miecza"
    p_paradigm = bible.get_declension_paradigm("Szermierz")
    assert p_paradigm is not None
    # Must use canonical translation target from glossary ("Mistrz Miecza"), not generic auto-declension
    assert "Mistrz Miecza" in p_paradigm.M
    assert "Mistrza Miecza" in p_paradigm.D
