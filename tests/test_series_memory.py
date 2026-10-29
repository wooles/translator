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



# ==============================================================================
# STANDARD 9.4 TESTS (T4.8, T4.12)
# ==============================================================================

@pytest.mark.unit
def test_sanitize_ram_cleans_character_descriptions_and_resolves_relation_tv_asymmetry(tmp_path):
    """
    T4.8 (Operacja 2C.5): Weryfikacja czyszczenia opisów postaci w RAM (eliminacja
    sprzecznych znaczników płciowych) oraz sanityzacji asymetrii relacji T/V.
    """
    bible_file = tmp_path / "sanitize_ram_test.json"
    bible = SeriesBible(bible_path=bible_file, storage_dir=tmp_path)
    
    # 1. Postać męska ze skażeniem "KOBIETA" w polu description
    bible.data["characters"]["Tokiyuki Hōjō"] = {
        "description": "KOBIETA (błędna flaga historyczna) - główny dziedzic rodu",
        "gender": "MALE",
        "grammatical_gender": "MASCULINE",
        "has_verified_gender": True,
        "priority": "P0"
    }

    # 2. Relacja z asymetrią: deskryptor "RELACJA HIERARCHICZNA" sprzeczny z "per ty" i "przyjaciel"
    # oraz błędny znacznik adresata [KOBIETA (Adresat)] dla postaci męskiej P0
    bible.data["relations"]["Yorishige -> Tokiyuki Hōjō"] = (
        "[RELACJA HIERARCHICZNA] [KOBIETA (Adresat)] rozmawiają per ty jako serdeczni przyjaciele"
    )

    # Wykonanie samoleczącej sanityzacji w RAM
    bible._sanitize_loaded_bible_in_ram()

    # Asercja 1: pole description oczyszczone ze sprzecznej flagi KOBIETA
    clean_desc = bible.data["characters"]["Tokiyuki Hōjō"]["description"]
    assert "KOBIETA" not in clean_desc
    assert bible.data["characters"]["Tokiyuki Hōjō"]["gender"] == "MALE"

    # Asercja 2: relacja oczyszczona z błędnej hierarchii i oznaczona jako reżim POUFNY
    rel_desc = bible.data["relations"]["Yorishige -> Tokiyuki Hōjō"]
    assert "RELACJA HIERARCHICZNA" not in rel_desc
    assert "reżim: POUFNY" in rel_desc
    # Asercja 3: znacznik adresata zsynchronizowany z P0 męskim
    assert "MĘŻCZYZNA (Adresat)" in rel_desc


@pytest.mark.unit
@pytest.mark.parametrize(
    "compound_term,gender,expected_genitive,expected_instrumental",
    [
        # T4.12 (Operacja 2C.9): Złożenia dwuwyrazowe z przydawką dopełniaczową
        ("Władca Ciemności", "MALE", "Władcy Ciemności", "Władcą Ciemności"),
        ("Książę Piekieł", "MALE", "Księcia Piekieł", "Księciem Piekieł"),
        ("Mistrz Miecza", "MALE", "Mistrza Miecza", "Mistrzem Miecza"),
    ]
)
def test_declension_preserves_genitive_modifier_in_compound_terms_and_transfers_p0_paradigm(
    compound_term, gender, expected_genitive, expected_instrumental, tmp_path
):
    """
    T4.12 (Operacja 2C.9): Weryfikacja ochrony przydawki dopełniaczowej w terminach złożonych
    oraz transferu pełnego 7-przypadkowego paradygmatu P0 do SeriesBible.
    """
    # 1. Zachowanie drugiego członu (przydawki dopełniaczowej)
    decl = generate_polish_name_declension(compound_term, gender)
    assert decl["M"] == compound_term
    assert decl["D"] == expected_genitive
    assert decl["N"] == expected_instrumental
    # Drugi człon pozostaje nienaruszony w dopełniaczu i narzędniku
    assert compound_term.split()[-1] in decl["D"]
    assert compound_term.split()[-1] in decl["N"]

    # 2. Bezwarunkowy transfer pełnego 7-przypadkowego paradygmatu P0
    bible_file = tmp_path / "transfer_p0_test.json"
    bible = SeriesBible(bible_path=bible_file, storage_dir=tmp_path)
    p0_paradigm = {
        "M": compound_term,
        "D": expected_genitive,
        "C": f"{expected_genitive[:-1]}i",
        "B": expected_genitive,
        "N": expected_instrumental,
        "Ms": f"{expected_genitive[:-1]}y",
        "W": compound_term
    }
    bible.sync_verified_profile_entity(
        name=compound_term,
        gender=gender,
        has_verified_gender=True,
        declension_map=p0_paradigm
    )
    saved_decl = bible.data["declensions"][compound_term]
    for case in ("M", "D", "C", "B", "N", "Ms", "W"):
        assert saved_decl[case] == p0_paradigm[case]
        assert len(saved_decl[case]) > 0


@pytest.mark.unit
def test_validate_relation_strips_nested_bracket_clause_and_sanitizes_legacy_declensions(tmp_path):
    """
    T5.5 (Operacja 2C.4): Prawidłowy stan SeriesBible w RAM = czyste usunięcie
    pełnej klauzuli RELACJA HIERARCHICZNA (... [Imię] ... -sama] we wpisie poufnym,
    regeneracja uszkodzonych paradygmatów z dysku oraz korekta ortograficzna rdzenia wołacza W.
    """
    bible_file = tmp_path / "test_validate_relation_95.json"
    bible = SeriesBible(bible_path=bible_file, storage_dir=tmp_path)

    # 1. Sprawdzenie usunięcia zagnieżdżonej klauzuli hierarchicznej z relacji poufnej
    bible.data["relations"]["Yorishige -> Tokiyuki"] = (
        "[RELACJA HIERARCHICZNA (mistrz-uczeń: [Tokiyuki], eliminacja hybryd 'Tokiyuki... ma pan' "
        "oraz odporność na opuszczanie -sama)] serdeczna rozmowa przyjaciół per ty"
    )

    # 2. Sprawdzenie usunięcia osieroconego ogona po dawnych regexach
    bible.data["relations"]["Artur -> Helena"] = (
        "poufna rozmowa per ty', eliminacja hybryd 'Helena... ma pan' oraz odporność na opuszczanie -sama]"
    )

    # 3. Sprawdzenie regeneracji uszkodzonych paradygmatów wczytanych z dysku (np. ńa, e'a)
    bible.data["declensions"]["Przestrzeń"] = {
        "M": "Przestrzeń",
        "D": "Przestrzeńa",
        "C": "Przestrzeńowi",
        "B": "Przestrzeń",
        "N": "Przestrzeńem",
        "Ms": "Przestrzeńie",
        "W": "Przestrzeń"
    }
    bible.data["declensions"]["Pole"] = {
        "M": "Pole",
        "D": "Pole'a",
        "C": "Pole'owi",
        "B": "Pole",
        "N": "Pole'em",
        "Ms": "Polu",
        "W": "Pole"
    }

    # Wywołanie samoleczącej sanityzacji w RAM
    bible._sanitize_loaded_bible_in_ram()

    # Asercja 1: klauzula hierarchiczna całkowicie usunięta, reżim poufny zachowany
    rel_yorishige = bible.data["relations"]["Yorishige -> Tokiyuki"]
    assert "RELACJA HIERARCHICZNA" not in rel_yorishige
    assert "-sama]" not in rel_yorishige
    assert "eliminacja hybryd" not in rel_yorishige
    assert "reżim: POUFNY" in rel_yorishige
    assert "serdeczna rozmowa przyjaciół per ty" in rel_yorishige

    # Asercja 2: osierocony ogon usunięty
    rel_artur = bible.data["relations"]["Artur -> Helena"]
    assert "eliminacja hybryd" not in rel_artur
    assert "-sama]" not in rel_artur
    assert "poufna rozmowa per ty" in rel_artur

    # Asercja 3: uszkodzone sufiksy zregenerowane
    decl_przestrzen = bible.data["declensions"]["Przestrzeń"]
    assert decl_przestrzen["D"] != "Przestrzeńa"
    assert "ńa" not in decl_przestrzen["D"]
    assert "ńowi" not in decl_przestrzen["C"]

    decl_pole = bible.data["declensions"]["Pole"]
    assert decl_pole["D"] != "Pole'a"
    assert "e'a" not in decl_pole["D"]
    assert "e'owi" not in decl_pole["C"]

    # 4. Sprawdzenie korekty ortograficznej rdzenia wołacza W (SeriesBible.align_vocative_orthography)
    # Kanoniczny wołacz w bazie z podwójną spółgłoską: Abaddon -> Abaddonie
    bible.data["declensions"]["Abaddon"] = {
        "M": "Abaddon", "D": "Abaddona", "C": "Abaddonowi", "B": "Abaddona",
        "N": "Abaddonem", "Ms": "Abaddonie", "W": "Abaddonie"
    }
    misspelled_vocative = "Poczekaj, Abadonie!"
    corrected_vocative = SeriesBible.align_vocative_orthography(misspelled_vocative, declensions=bible.data["declensions"])
    assert corrected_vocative == "Poczekaj, Abaddonie!"


# ==============================================================================
# STANDARD 9.6 TESTS (T6.4)
# ==============================================================================
@pytest.mark.unit
@pytest.mark.parametrize(
    "step5_line,entity_name,expected_d,expected_n,expected_w",
    [
        (
            "Tokiyuki: M. Tokiyuki, D. Tokiyukiego, C. Tokiyukiego, B. Tokiyukiego, N. Tokiyukim, Ms. Tokiyukim, W. Tokiyuki",
            "Tokiyuki",
            "Tokiyukiego",
            "Tokiyukim",
            "Tokiyuki",
        ),
        (
            "Yorishige: M: Yorishige, D: Yorishigego, C: Yorishigemu, B: Yorishigego, N: Yorishigem, Ms: Yorishigem, W: Yorishige",
            "Yorishige",
            "Yorishigego",
            "Yorishigem",
            "Yorishige",
        ),
    ],
)
def test_step5_dot_separator_paradigm_parsing_and_honorific_alias_canonical_declension(
    step5_line, entity_name, expected_d, expected_n, expected_w
):
    from series_memory import SeriesBible

    bible = SeriesBible(slug="test_dot_paradigm_and_alias")
    bible.data["characters"][entity_name] = {
        "name": entity_name,
        "gender": "MALE",
        "grammatical_gender": "MASCULINE",
        "confidence": 0.95,
        "priority": "P0",
        "has_verified_gender": True,
        "aliases": [entity_name, "Toki-chan", "Toki"],
    }
    bible.data["declensions"][entity_name] = {k: entity_name for k in ("M", "D", "C", "B", "N", "Ms", "W")}
    parsed_map = SeriesBible.parse_step5_declension_line(step5_line)
    bible.sync_verified_profile_entity(entity_name, "MALE", has_verified_gender=True, declension_map=parsed_map)
    assert bible.data["declensions"][entity_name]["D"] == expected_d
    assert bible.data["declensions"][entity_name]["N"] == expected_n
    assert bible.data["declensions"][entity_name]["W"] == expected_w

    # Weryfikacja podmiany zdrobnienia/aliasu z honoryfikatorem na kanoniczny narzędnik N
    source_en = "Maybe I'll go with Toki-chan."
    f1_pl = "Może pójdę z Toki."
    res = SeriesBible.substitute_canonical_honorific_alias(
        text=f1_pl,
        source_en=source_en,
        series_bible=bible,
        declensions=bible.data["declensions"],
        characters=bible.data["characters"],
    )
    if entity_name == "Tokiyuki":
        assert res == "Może pójdę z Tokiyukim."
