import pytest
from series_memory import SeriesBible, EntityCategory, generate_polish_name_declension


def test_series_bible_entity_filtering_and_glossary_priority(tmp_path):
    bible_file = tmp_path / "test_series_bible.json"
    bible = SeriesBible(bible_path=bible_file, storage_dir=tmp_path)

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


def test_series_bible_syncs_verified_p0_gender_and_full_compound_declension():
    bible = SeriesBible(slug="test_series_contract", db_path=":memory:")
    
    # 1. Sync verified profile entity with P0 gender and 7-case compound declension
    decl_map = {
        "M": "Generał Janusz Korwin",
        "D": "Generała Janusza Korwina",
        "C": "Generałowi Januszowi Korwinowi",
        "B": "Generała Janusza Korwina",
        "N": "Generałem Januszem Korwinem",
        "Ms": "Generale Januszu Korwinie",
        "W": "Generale Januszu Korwinie"
    }
    rec = bible.sync_verified_profile_entity(
        name="Generał Janusz Korwin",
        gender="MALE",
        has_verified_gender=True,
        declension_map=decl_map
    )
    assert rec["gender"] == "MALE"
    assert rec["has_verified_gender"] is True
    assert rec["priority"] == "P0"
    assert rec["confidence"] >= 0.95

    # 2. Assert full 7-case declension retrieval via get_declension
    assert bible.get_declension("Generał Janusz Korwin", "M") == "Generał Janusz Korwin"
    assert bible.get_declension("Generał Janusz Korwin", "Ms") == "Generale Januszu Korwinie"
    assert bible.get_declension("Generał Janusz Korwin", "W") == "Generale Januszu Korwinie"
    assert bible.get_declension("Nieznany Byt", "M") == "Nieznany Byt"


@pytest.mark.parametrize(
    "entity_id,contaminated_gender,verified_profile_gender,relation_key",
    [
        # DANE TESTOWE: encja żeńska z historycznie zatrutym p0_gender=MALE + relacja z etykietą [MĘŻCZYZNA (Adresat)].
        ("Helena", "MALE", "FEMALE", "Artur -> Helena"),
        ("Anna", "MALE", "FEMALE", "Wojownik -> Anna"),
    ],
)
def test_sanitize_bible_in_ram_aligns_character_and_relation_gender_with_p0(
    entity_id, contaminated_gender, verified_profile_gender, relation_key
):
    """Weryfikuje oczyszczanie w pamięci RAM zatrutych flag płci postaci i adresatów relacji zgodnie z P0."""
    from series_memory import SeriesBible
    bible = SeriesBible(slug="test_ram_sanitization", db_path=":memory:")
    bible.data["characters"][entity_id] = {
        "gender": contaminated_gender,
        "grammatical_gender": "MASCULINE",
        "has_verified_gender": True,
    }
    bible.data["relations"][relation_key] = "Relacja [MĘŻCZYZNA (Adresat)]"
    bible.sync_verified_profile_entity(
        name=entity_id,
        gender=verified_profile_gender,
        has_verified_gender=True,
    )
    bible._sanitize_loaded_bible_in_ram()
    assert bible.get_character_gender(entity_id) == verified_profile_gender
    assert "KOBIETA (Adresat)" in bible.data["relations"][relation_key]


# Test dla Sekcji 2B.3
@pytest.mark.parametrize(
    "entity_name,profiler_paradigm,expected_vocative",
    [
        (
            "HeroAlpha SurnameBeta",
            {
                "M": "HeroAlpha SurnameBeta",
                "D": "HeroAlphaa SurnameBety",
                "C": "HeroAlphaowi SurnameBecie",
                "B": "HeroAlphaa SurnameBetę",
                "N": "HeroAlphaem SurnameBetą",
                "Ms": "HeroAlphie SurnameBecie",
                "W": "HeroAlphie SurnameBecie",
            },
            "HeroAlphie SurnameBecie",
        ),
        (
            "HeroGamma SurnameDelta",
            {
                "M": "HeroGamma SurnameDelta",
                "D": "HeroGammy SurnameDelty",
                "C": "HeroGammie SurnameDelcie",
                "B": "HeroGammę SurnameDeltę",
                "N": "HeroGammą SurnameDeltą",
                "Ms": "HeroGammie SurnameDelcie",
                "W": "HeroGammo SurnameDelto",
            },
            "HeroGammo SurnameDelto",
        ),
    ],
)
def test_sync_profile_entity_transfers_full_inflected_paradigm_over_frozen_nominative(
    entity_name, profiler_paradigm, expected_vocative
):
    """Weryfikuje priorytet zdeklinowanego paradygmatu z EpisodeProfiler nad zamrożonym mianownikiem w SeriesBible."""
    bible = SeriesBible(slug="test_paradigm_transfer")
    bible.data["declensions"][entity_name] = {k: entity_name for k in ("M", "D", "C", "B", "N", "Ms", "W")}
    bible.sync_verified_profile_entity(
        name=entity_name,
        gender="MALE",
        has_verified_gender=True,
        declension_map=profiler_paradigm,
    )
    assert bible.data["declensions"][entity_name]["W"] == expected_vocative


# Test dla Sekcji 2C.1
@pytest.mark.parametrize(
    "entity_name,legacy_desc,profile_gender",
    [
        ("EntityOne", "MĘŻCZYZNA (zweryfikowano przez EpisodeQualityGate)", "FEMALE"),
        ("EntityTwo", "MĘŻCZYZNA (wyodrębniono z relacji serii)", "FEMALE"),
    ],
)
def test_sanitize_ram_overrides_legacy_eqg_and_relation_extracted_male_flags(
    entity_name, legacy_desc, profile_gender
):
    """Weryfikuje nadpisanie w pamięci RAM historycznych flag MALE z adnotacją EQG/relacji stanem P0."""
    bible = SeriesBible(slug="test_legacy_override")
    bible.data["characters"][entity_name] = {
        "description": legacy_desc,
        "gender": "MALE",
        "grammatical_gender": "MASCULINE",
        "has_verified_gender": True,
    }
    bible.data["relations"][f"SpeakerX -> {entity_name}"] = "Zwrot [MĘŻCZYZNA (Adresat)]"
    bible.sync_verified_profile_entity(name=entity_name, gender=profile_gender, has_verified_gender=True)
    bible._sanitize_loaded_bible_in_ram()
    assert bible.get_character_gender(entity_name) == profile_gender
    assert "KOBIETA (Adresat)" in bible.data["relations"][f"SpeakerX -> {entity_name}"]

