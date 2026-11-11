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
            "BohaterAlfa WspolneNazwisko": {"description": "mężczyzna (bohater)", "gender": "MALE", "priority": "P0", "has_verified_gender": True},
            "BohaterkaBeta WspolneNazwisko": {"description": "kobieta (bohaterka)", "gender": "FEMALE", "priority": "P0", "has_verified_gender": True},
            "Sign Board": {"description": "szyld informacyjny", "is_sign": True},
            "Boy A": "chłopiec w tle",
            "Guard 1": "strażnik bramy",
            "Wydarzenie Przeszłe": {"description": "wspomnienie bitwy", "source": "continuity_bridge_alerts"}
        },
        glossary={
            "WspolneNazwisko": "Ród WspolneNazwisko",
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
    assert "BohaterAlfa WspolneNazwisko" in chars
    assert "BohaterkaBeta WspolneNazwisko" in chars

    # 2. Surname alias collision prohibition:
    # BohaterAlfa (MALE) and BohaterkaBeta (FEMALE) share the surname "WspolneNazwisko".
    # The bare surname "WspolneNazwisko" must NOT be assigned as an alias to either!
    artur_aliases = chars["BohaterAlfa WspolneNazwisko"].get("aliases", [])
    helena_aliases = chars["BohaterkaBeta WspolneNazwisko"].get("aliases", [])
    assert "WspolneNazwisko" not in artur_aliases
    assert "wspolnenazwisko" not in [a.lower() for a in artur_aliases if len(a.split()) == 1]
    assert "WspolneNazwisko" not in helena_aliases
    assert "wspolnenazwisko" not in [a.lower() for a in helena_aliases if len(a.split()) == 1]

    # First names should be present
    assert "BohaterAlfa" in artur_aliases
    assert "BohaterkaBeta" in helena_aliases

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
        "M": "Generał BohaterAlfa NazwiskoBeta",
        "D": "Generała BohateraAlfa NazwiskoBeta",
        "C": "Generałowi BohaterowiAlfa NazwiskoBeta",
        "B": "Generała BohateraAlfa NazwiskoBeta",
        "N": "Generałem BohateremAlfa NazwiskoBeta",
        "Ms": "Generale BohaterzeAlfa NazwiskoBeta",
        "W": "Generale BohaterzeAlfa NazwiskoBeta"
    }
    rec = bible.sync_verified_profile_entity(
        name="Generał BohaterAlfa NazwiskoBeta",
        gender="MALE",
        has_verified_gender=True,
        declension_map=decl_map
    )
    assert rec["gender"] == "MALE"
    assert rec["has_verified_gender"] is True
    assert rec["priority"] == "P0"
    assert rec["confidence"] >= 0.95

    # 2. Assert full 7-case declension retrieval via get_declension
    assert bible.get_declension("Generał BohaterAlfa NazwiskoBeta", "M") == "Generał BohaterAlfa NazwiskoBeta"
    assert bible.get_declension("Generał BohaterAlfa NazwiskoBeta", "Ms") == "Generale BohaterzeAlfa NazwiskoBeta"
    assert bible.get_declension("Generał BohaterAlfa NazwiskoBeta", "W") == "Generale BohaterzeAlfa NazwiskoBeta"
    assert bible.get_declension("Nieznany Byt", "M") == "Nieznany Byt"


@pytest.mark.parametrize(
    "entity_id,contaminated_gender,verified_profile_gender,relation_key",
    [
        # DANE TESTOWE: encja żeńska z historycznie zatrutym p0_gender=MALE + relacja z etykietą [MĘŻCZYZNA (Adresat)].
        ("BohaterkaBeta", "MALE", "FEMALE", "BohaterAlfa -> BohaterkaBeta"),
        ("BohaterkaGamma", "MALE", "FEMALE", "Wojownik -> BohaterkaGamma"),
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
    bible.data["characters"]["HeroAlpha SurnameBeta"] = {
        "description": "KOBIETA (błędna flaga historyczna) - główny dziedzic rodu",
        "gender": "MALE",
        "grammatical_gender": "MASCULINE",
        "has_verified_gender": True,
        "priority": "P0"
    }

    # 2. Relacja z asymetrią: deskryptor "RELACJA HIERARCHICZNA" sprzeczny z "per ty" i "przyjaciel"
    # oraz błędny znacznik adresata [KOBIETA (Adresat)] dla postaci męskiej P0
    bible.data["relations"]["MasterGamma -> HeroAlpha SurnameBeta"] = (
        "[RELACJA HIERARCHICZNA] [KOBIETA (Adresat)] rozmawiają per ty jako serdeczni przyjaciele"
    )

    # Wykonanie samoleczącej sanityzacji w RAM
    bible._sanitize_loaded_bible_in_ram()

    # Asercja 1: pole description oczyszczone ze sprzecznej flagi KOBIETA
    clean_desc = bible.data["characters"]["HeroAlpha SurnameBeta"]["description"]
    assert "KOBIETA" not in clean_desc
    assert bible.data["characters"]["HeroAlpha SurnameBeta"]["gender"] == "MALE"

    # Asercja 2: relacja oczyszczona z błędnej hierarchii i oznaczona jako reżim POUFNY
    rel_desc = bible.data["relations"]["MasterGamma -> HeroAlpha SurnameBeta"]
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
    bible.data["relations"]["MasterGamma -> HeroAlpha"] = (
        "[RELACJA HIERARCHICZNA (mistrz-uczeń: [HeroAlpha], eliminacja hybryd 'HeroAlpha... ma pan' "
        "oraz odporność na opuszczanie -sama)] serdeczna rozmowa przyjaciół per ty"
    )

    # 2. Sprawdzenie usunięcia osieroconego ogona po dawnych regexach
    bible.data["relations"]["BohaterAlfa -> BohaterkaBeta"] = (
        "poufna rozmowa per ty', eliminacja hybryd 'BohaterkaBeta... ma pan' oraz odporność na opuszczanie -sama]"
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
    rel_yorishige = bible.data["relations"]["MasterGamma -> HeroAlpha"]
    assert "RELACJA HIERARCHICZNA" not in rel_yorishige
    assert "-sama]" not in rel_yorishige
    assert "eliminacja hybryd" not in rel_yorishige
    assert "reżim: POUFNY" in rel_yorishige
    assert "serdeczna rozmowa przyjaciół per ty" in rel_yorishige

    # Asercja 2: osierocony ogon usunięty
    rel_artur = bible.data["relations"]["BohaterAlfa -> BohaterkaBeta"]
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
    # Kanoniczny wołacz w bazie z podwójną spółgłoską: Bohateronn -> Bohateronnie
    bible.data["declensions"]["Bohateronn"] = {
        "M": "Bohateronn", "D": "Bohateronna", "C": "Bohateronnowi", "B": "Bohateronna",
        "N": "Bohateronnem", "Ms": "Bohateronnie", "W": "Bohateronnie"
    }
    misspelled_vocative = "Poczekaj, Bohateronie!"
    corrected_vocative = SeriesBible.align_vocative_orthography(misspelled_vocative, declensions=bible.data["declensions"])
    assert corrected_vocative == "Poczekaj, Bohateronnie!"


# ==============================================================================
# STANDARD 9.6 TESTS (T6.4)
# ==============================================================================
@pytest.mark.unit
@pytest.mark.parametrize(
    "step5_line,entity_name,expected_d,expected_n,expected_w",
    [
        (
            "HeroAlphon: M. HeroAlphon, D. HeroAlphona, C. HeroAlphona, B. HeroAlphona, N. HeroAlphonem, Ms. HeroAlphonie, W. HeroAlphon",
            "HeroAlphon",
            "HeroAlphona",
            "HeroAlphonem",
            "HeroAlphon",
        ),
        (
            "MasterGamma: M: MasterGamma, D: MasterGammago, C: MasterGammamu, B: MasterGammago, N: MasterGammam, Ms: MasterGammam, W: MasterGamma",
            "MasterGamma",
            "MasterGammago",
            "MasterGammam",
            "MasterGamma",
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
        "aliases": [entity_name, "Alphon-chan", "Alphon"],
    }
    bible.data["declensions"][entity_name] = {k: entity_name for k in ("M", "D", "C", "B", "N", "Ms", "W")}
    parsed_map = SeriesBible.parse_step5_declension_line(step5_line)
    bible.sync_verified_profile_entity(entity_name, "MALE", has_verified_gender=True, declension_map=parsed_map)
    assert bible.data["declensions"][entity_name]["D"] == expected_d
    assert bible.data["declensions"][entity_name]["N"] == expected_n
    assert bible.data["declensions"][entity_name]["W"] == expected_w

    # Weryfikacja podmiany zdrobnienia/aliasu z honoryfikatorem na kanoniczny narzędnik N
    source_en = "Maybe I'll go with Alphon-chan."
    f1_pl = "Może pójdę z Alphon."
    res = SeriesBible.substitute_canonical_honorific_alias(
        text=f1_pl,
        source_en=source_en,
        series_bible=bible,
        declensions=bible.data["declensions"],
        characters=bible.data["characters"],
    )
    if entity_name == "HeroAlphon":
        assert res == "Może pójdę z HeroAlphonem."


# ==============================================================================
# STANDARD 9.7 TESTS (T7.1)
# ==============================================================================
@pytest.mark.unit
@pytest.mark.parametrize(
    "source_en,f2_pl,expected_final_pl",
    [
        (
            "What about HeroAlpha SurnameBeta.",
            "{\\i1}Zastanawiam się,\\Nco z HeroAlphą SurnameBetą.{\\i0}",
            "{\\i1}Zastanawiam się,\\Nco z HeroAlphą SurnameBetą.{\\i0}",
        ),
        (
            "Looking at HeroAlpha SurnameBeta.",
            "{\\i1}Spójrz tutaj\\Nz opisem HeroAlphy SurnameBety.{\\i0}",
            "{\\i1}Spójrz tutaj\\Nz opisem HeroAlphy SurnameBety.{\\i0}",
        ),
    ],
)
def test_multi_token_anthroponym_immunity_against_component_alias_duplication_and_selective_title_alias(
    source_en, f2_pl, expected_final_pl
):
    from series_memory import SeriesBible

    bible = SeriesBible(slug="test_multi_token_immunity")
    bible.sync_verified_profile_entity(
        "HeroAlpha SurnameBeta",
        "MALE",
        has_verified_gender=True,
        declension_map={
            "M": "HeroAlpha SurnameBeta",
            "D": "HeroAlphy SurnameBety",
            "N": "HeroAlphą SurnameBetą",
        },
    )
    bible.sync_verified_profile_entity(
        "HeroAlpha",
        "MALE",
        has_verified_gender=True,
        declension_map={"M": "HeroAlpha", "N": "HeroAlphą"},
    )
    bible.sync_verified_profile_entity("EntityGamma", "MALE", has_verified_gender=True)
    bible.map_bilingual_role_aliases(["Alpha-chan"])

    assert "Alpha-chan" not in bible.data["characters"]["EntityGamma"]["aliases"]
    assert "Alpha-chan" not in bible.data["characters"]["HeroAlpha SurnameBeta"]["aliases"]

    out_pl = bible.apply_canonical_alias_declension(text=f2_pl, source_en=source_en, keep_honorifics=False)
    assert out_pl == expected_final_pl
    assert "SurnameBet" in out_pl


# ==============================================================================
# STANDARD 9.10 TESTS (T10.1, T10.2, T10.3)
# ==============================================================================


@pytest.mark.unit
@pytest.mark.parametrize(
    "full_name,short_name,gender,desc,expected_short_gender,expected_genitive",
    [
        (
            "PostacKonsonantD NazwiskoD",
            "PostacKonsonantD",
            "FEMALE",
            "postać (Postać drugoplanowa)",
            "FEMALE",
            "PostacKonsonantD",
        ),
        (
            "Sister",
            "Sister",
            "FEMALE",
            "postać drugoplanowa",
            "FEMALE",
            "Sister",
        ),
    ],
)
def test_structural_gender_preservation_and_short_alias_female_consonant_indeclinability(
    full_name, short_name, gender, desc, expected_short_gender, expected_genitive
):
    from series_memory import SeriesBible, generate_polish_name_declension

    bible = SeriesBible(slug="test_9_10_structural_gender", db_path=":memory:")
    bible.data["characters"][full_name] = {
        "name": full_name,
        "gender": gender,
        "grammatical_gender": "FEMININE",
        "confidence": 0.95,
        "priority": "P0",
        "has_verified_gender": True,
        "aliases": [full_name, short_name],
        "description": desc,
    }
    bible._sanitize_loaded_bible_in_ram()
    assert bible.get_character_gender(full_name) == expected_short_gender
    assert bible.get_character_gender(short_name) == expected_short_gender
    decl = generate_polish_name_declension(short_name, bible.get_character_gender(short_name))
    assert decl["D"] == expected_genitive


@pytest.mark.unit
@pytest.mark.parametrize(
    "raw_tag,expected_clean,should_be_filtered",
    [
        ("Everyone", "Everyone", True),
        ("crowd", "crowd", True),
        ("PostacKonsonantD?", "PostacKonsonantD", False),
    ],
)
def test_actor_tag_ontological_filtering_strips_punctuation_and_rejects_non_personal_tags(
    raw_tag, expected_clean, should_be_filtered
):
    from metadata import normalize_actor_tag
    from series_memory import SeriesBible

    clean_t, _ = normalize_actor_tag(raw_tag)
    assert clean_t == expected_clean
    bible = SeriesBible(slug="test_9_10_filtering", db_path=":memory:")
    bible.populate_secondary_actor_tags([raw_tag])
    if should_be_filtered:
        assert raw_tag not in bible.data["characters"]
        assert clean_t not in bible.data["characters"]
    else:
        assert clean_t in bible.data["characters"]


@pytest.mark.unit
@pytest.mark.parametrize(
    "phrase,expected_d,expected_n",
    [
        ("Czterech Jeźdźców", "Czterech Jeźdźców", "Czterech Jeźdźców"),
        ("system obronny", "systemu obronnego", "systemem obronnym"),
    ],
)
def test_declension_generator_handles_ny_adjectives_and_plural_genitive_phrases(
    phrase, expected_d, expected_n
):
    from series_memory import generate_polish_name_declension

    decl = generate_polish_name_declension(phrase, "MALE")
    assert decl["D"] == expected_d
    assert decl["N"] == expected_n


@pytest.mark.unit
@pytest.mark.parametrize(
    "tag,expected_generic",
    [
        ("mężczyzna", True),
        ("kobieta", True),
        ("Everyone", True),
        ("both", True),
        ("Vali", False),
        ("Violet", False),
    ],
)
def test_series_bible_is_generic_actor_or_category_method_and_function_equivalence(tag, expected_generic):
    from series_memory import SeriesBible, is_generic_actor_or_category

    bible = SeriesBible(slug="test_generic_equiv", db_path=":memory:")
    assert is_generic_actor_or_category(tag) is expected_generic
    assert bible.is_generic_actor_or_category(tag) is expected_generic
    assert SeriesBible.is_generic_actor_or_category(tag) is expected_generic


# ============================================================================
# HOTFIX 9.10.1 REGRESSION TESTS (T10.1.1 - T10.1.3)
# ============================================================================


# WZORZEC T10.1.1 (Operacja H1) -> tests/test_series_memory.py
@pytest.mark.unit
@pytest.mark.parametrize(
    "name,gender,expected_n",
    [
        ("BohaterkaConsonante", "FEMALE", "BohaterkaConsonante"),
        ("BohaterkaConsonant", "FEMALE", "BohaterkaConsonant"),
        ("obronny", "MALE", "obronnym"),
    ],
)
def test_female_consonant_historical_names_are_indeclinable(name, gender, expected_n):
    from series_memory import generate_polish_name_declension
    decl = generate_polish_name_declension(name, gender)
    assert decl["N"] == expected_n


# WZORZEC T10.1.2 (Operacja H3) -> tests/test_series_memory.py
@pytest.mark.unit
@pytest.mark.parametrize(
    "name,expected_d",
    [
        ("PostacKonsonantA NazwiskoConsonantA", "PostacKonsonantA NazwiskoConsonantA"),
        ("PostacKonsonantB NazwiskoConsonantB", "PostacKonsonantB NazwiskoConsonantB"),
    ],
)
def test_bipartite_female_name_indeclinable(name, expected_d):
    from series_memory import generate_polish_name_declension
    decl = generate_polish_name_declension(name, "FEMALE")
    assert decl["D"] == expected_d


# WZORZEC T10.1.3 (Operacja H2) -> tests/test_series_memory.py
@pytest.mark.unit
@pytest.mark.parametrize("dict_key", ["terminology", "glossary"])
def test_terminology_alias_propagates_female_gender(dict_key):
    from series_memory import SeriesBible
    bible = SeriesBible(slug="test_9_10_1_terminology", db_path=":memory:")
    bible.data["characters"]["PostacKonsonantC"] = {
        "gender": "FEMALE",
        "grammatical_gender": "FEMININE",
        "priority": "P0",
        "has_verified_gender": True,
    }
    bible.data[dict_key] = {
        "PostacKonsonantC": "cesarzowa BohaterkaConsonantC"
    }
    bible._sanitize_loaded_bible_in_ram()
    assert "BohaterkaConsonantC" in bible.data["characters"]
    assert bible.data["characters"]["BohaterkaConsonantC"]["gender"] == "FEMALE"
    assert bible.data["declensions"]["BohaterkaConsonantC"]["gender"] == "FEMALE"

# ==============================================================================
# STANDARD 10.0.2 REGRESSION TESTS (A-01, A-02, A-04, A-13)
# ==============================================================================


@pytest.mark.unit
@pytest.mark.parametrize(
    "constant_attr",
    [
        "CANONICAL_MALE_NAMES",
        "UNIVERSAL_FEMALE_NAMES_ON_A",
        "FEMALE_LEXICON_NAMES",
        "FOREIGN_FEMALE_CONSONANT_NAMES",
    ],
)
def test_onomastic_lists_purity(constant_attr):
    from pathlib import Path
    import series_memory
    items = getattr(series_memory, constant_attr, None)
    assert items is not None, f"Constant {constant_attr} not found"
    items_lower = {str(x).lower() for x in items}
    forbidden_terms = set()
    for bible_file in Path("series_memory").glob("*_bible.json"):
        if "test" in bible_file.name.lower():
            continue
        prefix = bible_file.stem.replace("_bible", "").split("_")[0].lower()
        if len(prefix) >= 6 and prefix not in ("golden", "silent", "sayonara", "kingdom"):
            forbidden_terms.add(prefix)
    intersection = items_lower & forbidden_terms
    assert not intersection, f"Forbidden anime literals found in {constant_attr}: {intersection}"


@pytest.mark.unit
def test_typo_normalizations_clean():
    from pathlib import Path
    import series_memory
    forbidden_terms = set()
    for bible_file in Path("series_memory").glob("*_bible.json"):
        if "test" in bible_file.name.lower():
            continue
        prefix = bible_file.stem.replace("_bible", "").split("_")[0].lower()
        if len(prefix) >= 6 and prefix not in ("golden", "silent", "sayonara", "kingdom"):
            forbidden_terms.add(prefix)
    typos = getattr(series_memory, "TYPO_NORMALIZATIONS", [])
    for item in typos:
        pat = item[0] if isinstance(item, (list, tuple)) else str(item)
        for forbidden_term in forbidden_terms:
            assert forbidden_term not in pat.lower(), f"Forbidden term {forbidden_term} in typo pattern {pat}"
        assert not pat.startswith("chr("), f"Obfuscation in {pat}"


@pytest.mark.unit
@pytest.mark.parametrize(
    "raw_phrase,expected_sanitized",
    [
        ("chłopak z InstytucjaAlfa", "chłopak z InstytucjaAlfa"),
        ("zbieg z KrainaBeta", "zbieg z KrainaBeta"),
        ("uczeń z UczelniaGamma", "uczeń z UczelniaGamma"),
        ("rycerz z Królestwa KrólestwoDelta", "rycerz z Królestwa KrólestwoDelta"),
    ],
)
def test_toponyms_zero_literal(raw_phrase, expected_sanitized):
    from series_memory import sanitize_toponymic_origin_and_companionship, _BASE_KNOWN_FANTASY_TOPONYMS
    assert len(_BASE_KNOWN_FANTASY_TOPONYMS) == 0
    out = sanitize_toponymic_origin_and_companionship(raw_phrase)
    assert out == expected_sanitized


@pytest.mark.unit
@pytest.mark.parametrize(
    "rel_raw,expected_clean_rel",
    [
        (
            "Zwrot: 'BohaterzeAlfa' [MĘŻCZYZNA (Adresat) - W 2. os. lp. 'ty' wymóg form męskich: byłeś / zrobiłeś / jesteś pewien]', zakaz hybryd 'Imię... ma pan' oraz odporność na opuszczanie -sama] [reżim: FORMALNY]",
            "Zwrot: 'BohaterzeAlfa' [MĘŻCZYZNA (Adresat) - W 2. os. lp. 'ty' wymóg form męskich: byłeś / zrobiłeś / jesteś pewien] [reżim: FORMALNY]",
        ),
        (
            "Zwrot: 'BohaterkoBeta' [KOBIETA (Adresat) - W 2. os. lp. 'ty' wymóg form żeńskich: byłaś / zrobiłaś / jesteś pewna] [PARA DWÓCH KOBIET: w odniesieniu do obu kobiet stosuj wyłącznie formy żeńskie 'obie / dla was obu / was obie', wykluczona forma 'oboje' (Filar CLXXIII)]",
            "Zwrot: 'BohaterkoBeta' [KOBIETA (Adresat) - W 2. os. lp. 'ty' wymóg form żeńskich: byłaś / zrobiłaś / jesteś pewna] [PARA DWÓCH KOBIET: w odniesieniu do obu kobiet stosuj wyłącznie formy żeńskie 'obie / dla was obu / was obie']",
        ),
    ],
)
def test_bible_five_anomalies_sanitized(rel_raw, expected_clean_rel, tmp_path):
    from series_memory import SeriesBible
    bible = SeriesBible(slug="test_bible_anom", db_path=":memory:")
    bible.data = {
        "characters": {
            "Soldiers": {"description": "żołnierze", "gender": "UNKNOWN"},
            "Crowd": {"description": "tłum", "gender": "UNKNOWN"},
            "FemaleHero SharedSurname": {"gender": "FEMALE", "aliases": ["SharedSurname", "Heroine"]},
            "MaleHero SharedSurname": {"gender": "MALE", "aliases": ["SharedSurname", "Hero"]},
            "PostacObcaE Foreign": {"gender": "FEMALE", "aliases": ["PostacObcaE"]},
        },
        "declensions": {
            "PostacObcaE Foreign": {"M": "PostacObcaE Foreign", "D": "PostacObcaE Foreigna", "N": "PostacObcaE Foreignem", "gender": "FEMALE"},
        },
        "entity_categories": {
            "Seven Grand Sorcerers": "CHREMATONYM"
        },
        "relations": {
            "A -> B": rel_raw
        },
        "relationships": {
            "A -> B": rel_raw
        }
    }
    bible._sanitize_loaded_bible_in_ram()
    chars = bible.data["characters"]
    assert "Soldiers" not in chars
    assert "Crowd" not in chars
    assert "SharedSurname" not in chars["FemaleHero SharedSurname"]["aliases"]
    assert "SharedSurname" not in chars["MaleHero SharedSurname"]["aliases"]
    assert bible.data["declensions"]["PostacObcaE Foreign"]["D"] == "PostacObcaE Foreign"
    assert bible.data["declensions"]["PostacObcaE Foreign"]["N"] == "PostacObcaE Foreign"
    assert bible.data["entity_categories"]["Seven Grand Sorcerers"] == "CHREMATONYM"
    assert bible.data["relations"]["A -> B"] == expected_clean_rel


# ==============================================================================
# STANDARD 10.0.3 / 10.1 REGRESSION TESTS (2B.1, 2B.2)
# ==============================================================================


@pytest.mark.unit
@pytest.mark.parametrize(
    "short_name,full_name,p0_gender,expected_gram_gender",
    [
        ("HeroAlpha", "HeroAlpha Louventis", "MALE", "MASCULINE"),
        ("InventorBeta", "InventorBeta Seymarrowis", "MALE", "MASCULINE"),
        ("CommanderGamma", "CommanderGamma Musesis", "MALE", "MASCULINE"),
        ("TacticianDelta", "TacticianDelta Fujimiyas", "FEMALE", "FEMININE"),
        ("NobleEpsilon", "NobleEpsilon Plaidis", "FEMALE", "FEMININE"),
    ],
)
def test_addressee_and_speaker_gender_use_p0_alias_priority_over_p2_duplicate(
    short_name, full_name, p0_gender, expected_gram_gender
):
    from series_memory import SeriesBible
    from scene_discourse import SceneDiscourseGraph

    bible = SeriesBible(slug="test_p0_alias_priority", db_path=":memory:")
    bible.sync_verified_profile_entity(
        full_name,
        p0_gender,
        has_verified_gender=True,
    )
    # Symulacja duplikatu P2 UNKNOWN powstałego z krótkiego tagu .ass
    bible.data["characters"][short_name] = {
        "name": short_name,
        "gender": "UNKNOWN",
        "grammatical_gender": "UNKNOWN",
        "priority": "P2",
        "has_verified_gender": False,
        "confidence": 0.5,
        "aliases": [short_name],
    }
    bible._sanitize_loaded_bible_in_ram()

    # 1. Duplikat P2 musi zostać usunięty z characters na rzecz P0 (Wariant A z U2)
    assert short_name not in bible.data["characters"], \
        f"Duplikat P2 '{short_name}' nie został usunięty z characters po _sanitize_loaded_bible_in_ram"

    # 2. Arbitraż telemetrii dla krótkiego imienia w roli adresata musi zwrócić płeć P0
    telem = SceneDiscourseGraph.arbitrate_event_telemetry(
        raw_actor="OtherSpeaker",
        target_actor=short_name,
        series_bible=bible,
        f0_hz=310.0 if p0_gender == "MALE" else 115.0,  # Kontr-F0 mówcy (test odporności na H2!)
    )
    assert telem["target_gender"] == expected_gram_gender
    assert telem["addressee_gender"] == p0_gender, \
        f"addressee_gender={telem['addressee_gender']!r}, oczekiwano {p0_gender!r} (płeć P0)"
    assert telem["target_p0_verified"] is True


# T10.1.2 (A-2) -> tests/test_series_memory.py
@pytest.mark.unit
def test_load_dynamic_boy_keywords_has_no_hardcoded_series_names(monkeypatch):
    from pathlib import Path
    import series_memory
    # Wyłącz skanowanie plików *_bible.json z dysku, aby przetestować czystą listę statyczną w kodzie
    monkeypatch.setattr(Path, "exists", lambda self: False)
    kws = [k.lower() for k in series_memory._load_dynamic_boy_keywords()]
    allowed_generic = {
        "chłopiec", "chłopak", "boy", "syn", "młodzieniec", "książę",
        "dziecko płci męskiej", "pax", "bocchan", "crossgender", "cross-gender",
        "seiyū żeński", "żeńskie seiyū", "uczeń", "schoolboy", "lad", "kid",
        "shōnen", "shonen", "brat", "brother", "wnuk", "grandson",
        "10 lat", "dziedzic", "panicz", "młody pan", "waka", "wakagimi", "waka-sama",
    }
    unexpected = [k for k in kws if k not in allowed_generic]
    assert not unexpected, f"Znaleziono zahardkodowane imiona własne w liście statycznej: {unexpected}"


# T10.1.3 (A-3) -> tests/test_series_memory.py
@pytest.mark.unit
def test_static_series_specific_titles_migrated_from_code_to_bible():
    import json
    from pathlib import Path
    src = Path("series_memory.py").read_text(encoding="utf-8")
    # Żaden specyficzny termin kanoniczny z plików manga_canon/*.json nie może być zahardkodowany w series_memory.py
    for p in Path("manga_canon").glob("*.json"):
        if p.name.startswith("."):
            continue
        data = json.load(open(p, encoding="utf-8"))
        for en_term, pl_term in data.get("glossary", {}).items():
            if len(pl_term) >= 6 and " " in pl_term:
                assert pl_term.lower() not in src.lower(), f"Termin {pl_term} nadal zahardkodowany w series_memory.py"


# T10.1.4 (B-1) -> tests/test_series_memory.py
@pytest.mark.unit
def test_fansub_lexicon_no_synthetic_files_and_tmp_path_support(tmp_path):
    from pathlib import Path
    from series_memory import SeriesBible
    lex_dir = Path("series_memory/fansub_lexicons")
    before = set(lex_dir.glob("*.json")) if lex_dir.exists() else set()
    # Instancjonowanie testowej serii nie może tworzyć pliku w series_memory/fansub_lexicons/
    _ = SeriesBible(anime_title="TestSyntheticCleanerSeries", storage_dir=tmp_path)
    after = set(lex_dir.glob("*.json")) if lex_dir.exists() else set()
    assert before == after
    bad_files = [f.name for f in after if f.name.lower().startswith(("test", "synthetic", "stale", "multiarrow"))]
    assert not bad_files, f"Syntetyczne leksykony w repozytorium: {bad_files}"


# T10.1.6 (C-1) -> tests/test_series_memory.py
@pytest.mark.unit
def test_glossary_terms_reclassified_to_chrematonym_or_toponym():
    from pathlib import Path
    import json
    for p in sorted(Path("series_memory").glob("*_bible.json")):
        d = json.load(open(p, encoding="utf-8"))
        glossary = d.get("glossary", {})
        characters = d.get("characters", {})
        ent_cats = d.get("entity_categories", {})
        for term in glossary:
            if term in characters:
                continue
            if term in ent_cats:
                assert ent_cats[term] in ("CHREMATONYM", "TOPONYM"), f"{p.name}/{term}: {ent_cats[term]}"


# T10.1.8 (C-3) -> tests/test_series_memory.py
@pytest.mark.unit
@pytest.mark.parametrize("raw_anchor", [
    "Nie zmieniaj na X, stosuj Y.",
    "Zakaz używania terminu X.",
    "Unikaj formy X w dialogu.",
])
def test_plot_anchors_negative_phrases_normalized_to_positive(raw_anchor):
    from series_memory import SeriesBible
    bible = SeriesBible(slug="test_plot_anchors_positive", db_path=":memory:")
    bible.data["plot_anchors"] = {"[Rzeczownik]": raw_anchor}
    bible._sanitize_loaded_bible_in_ram()
    result = bible.data["plot_anchors"]["[Rzeczownik]"].lower()
    has_negative = any(n in result for n in ["nie zmieniaj", "nie zmieniać", "zakaz ", "unikaj "])
    assert not has_negative, f"Pozostała fraza negatywna: {result}"


# ==============================================================================
# STANDARD 10.6.1 TESTS (T10.6.1_1, T10.6.1_2, T10.6.1_3, T10.6.1_4)
# ==============================================================================


@pytest.mark.unit
def test_t10_6_1_1_variant_actor_suffix_soul_does_not_hijack_base_character(tmp_path):
    """
    Standard 10.6.1 (FIX-A.1): Weryfikuje, że techniczny tag aktora z sufiksem stanu
    (wariant HeroineSoul) nie przejmuje krótkiego aliasu ('Heroine') od głównej postaci P0
    ('Heroine Royalhouse').
    """
    from series_memory import SeriesMemoryManager

    sm = SeriesMemoryManager("test_series_10_6_1_1", memory_dir=str(tmp_path))
    sm.data["characters"] = {
        "HeroineSoul": {
            "description": "Postać epizodyczna / tło",
            "gender": "FEMALE",
            "grammatical_gender": "FEMININE",
            "has_verified_gender": True,
            "confidence": 0.95,
            "priority": "P0",
            "aliases": ["Heroine", "HeroineSoul"],
            "entity_category": "ANTHROPONYM",
        },
        "Heroine Royalhouse": {
            "name": "Heroine Royalhouse",
            "description": "KOBIETA (wyodrębniono z relacji serii)",
            "gender": "FEMALE",
            "grammatical_gender": "FEMININE",
            "has_verified_gender": True,
            "confidence": 0.95,
            "priority": "P0",
            "aliases": ["Royalhouse", "Heroine", "Heroine Royalhouse"],
            "entity_category": "ANTHROPONYM",
        },
    }
    sm.data["declensions"] = {
        "HeroineSoul": {k: "HeroineSoul" for k in ("M", "D", "C", "B", "N", "Ms", "W")},
        "Heroine Royalhouse": {k: "Heroine Royalhouse" for k in ("M", "D", "C", "B", "N", "Ms", "W")},
    }
    sm._sanitize_loaded_bible_in_ram()

    rec = sm.resolve_character_record("Heroine")
    assert rec is not None
    assert rec.get("name") == "Heroine Royalhouse" or "Royalhouse" in rec.get("aliases", [])


@pytest.mark.unit
def test_t10_6_1_2_populate_secondary_actor_tags_strips_soul_suffix(tmp_path):
    """
    Standard 10.6.1 (FIX-A.1a): Weryfikuje, że populate_secondary_actor_tags nie tworzy
    osobnej encji P0 dla tagu 'PrincessAlphaSoul', gdy istnieje 'PrincessAlpha Royal'.
    """
    from series_memory import SeriesMemoryManager

    sm = SeriesMemoryManager("test_series_10_6_1_2", memory_dir=str(tmp_path))
    sm.data["characters"] = {
        "PrincessAlpha Royal": {
            "name": "PrincessAlpha Royal",
            "gender": "FEMALE",
            "grammatical_gender": "FEMININE",
            "priority": "P0",
            "has_verified_gender": True,
            "aliases": ["PrincessAlpha", "PrincessAlpha Royal"],
            "entity_category": "ANTHROPONYM",
        }
    }
    actor_mappings = {
        "PrincessAlpha": {"clean_name": "PrincessAlpha", "extracted_gender": None},
        "PrincessAlphaSoul": {"clean_name": "PrincessAlphaSoul", "extracted_gender": None},
    }
    sm.populate_secondary_actor_tags(actor_mappings)
    assert "PrincessAlphaSoul" not in sm.data["characters"]


@pytest.mark.unit
@pytest.mark.parametrize(
    "pl_in,en_in,expected_pl",
    [
        (
            "Jestem Heroine, trzecia księżniczka.",
            "I'm Heroine, the third princess.",
            "Jestem Heroine, trzecia księżniczka.",
        ),
        (
            "Księżniczko Heroine, to nie przystoi.",
            "Princess Heroine, that expression is unbecoming.",
            "Księżniczko Heroine, to nie przystoi.",
        ),
        (
            "Oto ja, Heroine Royalhouse, urocza starsza siostra!",
            "I am Heroine Royalhouse, adorable older sister.",
            "Oto ja, Heroine Royalhouse, urocza starsza siostra!",
        ),
    ],
)
def test_t10_6_1_3_apply_canonical_alias_declension_never_injects_camel_case_soul(
    tmp_path, pl_in, en_in, expected_pl
):
    """
    Standard 10.6.1 (FIX-A.2): Weryfikuje, że apply_canonical_alias_declension nigdy nie
    podmienia imienia 'Heroine' na techniczny klucz 'HeroineSoul'.
    """
    from series_memory import SeriesMemoryManager

    sm = SeriesMemoryManager("test_series_10_6_1_3", memory_dir=str(tmp_path))
    sm.data["characters"] = {
        "HeroineSoul": {
            "description": "Postać epizodyczna / tło",
            "gender": "FEMALE",
            "grammatical_gender": "FEMININE",
            "has_verified_gender": True,
            "confidence": 0.95,
            "priority": "P0",
            "aliases": ["Heroine", "HeroineSoul"],
            "entity_category": "ANTHROPONYM",
        },
        "Heroine Royalhouse": {
            "name": "Heroine Royalhouse",
            "description": "KOBIETA",
            "gender": "FEMALE",
            "grammatical_gender": "FEMININE",
            "has_verified_gender": True,
            "confidence": 0.95,
            "priority": "P0",
            "aliases": ["Royalhouse", "Heroine", "Heroine Royalhouse"],
            "entity_category": "ANTHROPONYM",
        },
    }
    sm.data["declensions"] = {
        "HeroineSoul": {k: "HeroineSoul" for k in ("M", "D", "C", "B", "N", "Ms", "W")},
        "Heroine Royalhouse": {k: "Heroine Royalhouse" for k in ("M", "D", "C", "B", "N", "Ms", "W")},
    }
    sm._sanitize_loaded_bible_in_ram()

    out_pl, fixes = sm.apply_canonical_alias_declension(pl_in, source_en=en_in, keep_honorifics=False)
    assert out_pl == expected_pl
    assert "HeroineSoul" not in out_pl


@pytest.mark.unit
def test_t10_6_1_4_single_token_surname_toponym_not_expanded_to_full_person_name(tmp_path):
    """
    Standard 10.6.1 (FIX-A.2): Weryfikuje, że jednowyrazowa nazwa własna w narzędniku
    ('przyjazne relacje z Kingdomem', EN: 'friendly relations with Kingdom') nie zostaje
    rozszerzona do pełnego imienia i nazwiska postaci ('z Lady Kingdom') posiadającej
    alias 'Kingdom'.

    Dane testowe są w 100% syntetyczne (rdzeń 'Kingdom' oznacza tu fikcyjne państwo/
    akademię; 'Lady Kingdom' to fikcyjna postać używająca tego samego członu jako
    nazwiska). Forma narzędnika 'Kingdomem' jest celowo niepoprawna fleksyjnie i służy
    wyłącznie jako wejście do testowanego modułu.
    """
    from series_memory import SeriesMemoryManager

    sm = SeriesMemoryManager("test_series_10_6_1_4", memory_dir=str(tmp_path))
    sm.data["characters"] = {
        "Lady Kingdom": {
            "name": "Lady Kingdom",
            "gender": "FEMALE",
            "grammatical_gender": "FEMININE",
            "has_verified_gender": True,
            "confidence": 1.0,
            "priority": "P0",
            "aliases": ["Kingdom", "Lady", "Lady Kingdom"],
            "entity_category": "ANTHROPONYM",
        }
    }
    sm.data["declensions"] = {
        "Lady Kingdom": {
            "M": "Lady Kingdom",
            "D": "Lady Kingdom",
            "C": "Lady Kingdom",
            "B": "Lady Kingdom",
            "N": "Lady Kingdom",
            "Ms": "Lady Kingdom",
            "W": "Lady Kingdom",
            "gender": "FEMALE",
        }
    }

    pl_in = "To święto ma zacieśnić przyjazne relacje z Kingdomem,"
    en_in = "This event is also supposed to deepen friendly relations with Kingdom,"
    out_pl, _ = sm.apply_canonical_alias_declension(pl_in, source_en=en_in, keep_honorifics=False)
    assert out_pl == pl_in

# ==============================================================================
# STANDARD 10.6.3 REGRESSION TESTS (T10.6.3_2 – T10.6.3_8)
# ==============================================================================
@pytest.mark.unit
def test_t10_6_3_2_resolve_bible_path_finds_s2_for_ii(tmp_path):
    import json
    from series_memory import SeriesMemoryManager

    (tmp_path / "synthetic_anime_base_s2_bible.json").write_text(
        '{"anime_title": "Synthetic Anime Base S2", "characters": {}}', encoding="utf-8"
    )
    sm = SeriesMemoryManager(anime_title="Synthetic Anime Base II", storage_dir=tmp_path)
    resolved = sm._resolve_bible_path()
    assert resolved.name == "synthetic_anime_base_s2_bible.json"


@pytest.mark.unit
def test_t10_6_3_3_resolve_bible_path_finds_ii_for_s2(tmp_path):
    import json
    from series_memory import SeriesMemoryManager

    (tmp_path / "synthetic_anime_base_ii_bible.json").write_text(
        '{"anime_title": "Synthetic Anime Base II", "characters": {}}', encoding="utf-8"
    )
    sm = SeriesMemoryManager(anime_title="Synthetic Anime Base S2", storage_dir=tmp_path)
    resolved = sm._resolve_bible_path()
    assert resolved.name == "synthetic_anime_base_ii_bible.json"


@pytest.mark.unit
def test_t10_6_3_4_resolve_bible_path_does_not_match_season_1_for_season_2(tmp_path):
    import json
    from series_memory import SeriesMemoryManager

    (tmp_path / "synthetic_anime_base_bible.json").write_text(
        '{"anime_title": "Synthetic Anime Base", "characters": {}}', encoding="utf-8"
    )
    sm = SeriesMemoryManager(anime_title="Synthetic Anime Base S2", storage_dir=tmp_path)
    resolved = sm._resolve_bible_path()
    assert resolved.name != "synthetic_anime_base_bible.json"
    assert not resolved.exists() or resolved.name.lower() == "synthetic_anime_base_s2_bible.json"


@pytest.mark.unit
def test_t10_6_3_5_resolve_bible_path_matches_season_1_for_bare_title(tmp_path):
    import json
    from series_memory import SeriesMemoryManager

    (tmp_path / "synthetic_anime_base_bible.json").write_text(
        '{"anime_title": "Synthetic Anime Base", "characters": {}}', encoding="utf-8"
    )
    sm = SeriesMemoryManager(anime_title="Synthetic Anime Base", storage_dir=tmp_path)
    resolved = sm._resolve_bible_path()
    assert resolved.name == "synthetic_anime_base_bible.json"


@pytest.mark.unit
def test_t10_6_3_6_consolidate_split_bibles_merges_characters(tmp_path):
    import json
    from series_memory import consolidate_split_bibles

    bible_a = {
        "anime_title": "Synthetic Anime Base S2",
        "characters": {"Alpha Hero": {"gender": "MALE", "priority": "P0", "has_verified_gender": True, "aliases": ["Alpha Hero"]}},
        "episodes_translated": ["ep01"],
    }
    bible_b = {
        "anime_title": "Synthetic Anime Base II",
        "characters": {"Beta Heroine": {"gender": "FEMALE", "priority": "P0", "has_verified_gender": True, "aliases": ["Beta Heroine"]}},
        "episodes_translated": ["ep02"],
    }
    (tmp_path / "synthetic_anime_base_s2_bible.json").write_text(json.dumps(bible_a), encoding="utf-8")
    (tmp_path / "synthetic_anime_base_ii_bible.json").write_text(json.dumps(bible_b), encoding="utf-8")
    pairs = consolidate_split_bibles(tmp_path)
    assert len(pairs) == 1
    merged = json.loads((tmp_path / "synthetic_anime_base_s2_bible.json").read_text(encoding="utf-8"))
    assert "Alpha Hero" in merged["characters"]
    assert "Beta Heroine" in merged["characters"]
    assert set(merged["episodes_translated"]) == {"ep01", "ep02"}


@pytest.mark.unit
def test_t10_6_3_7_consolidate_split_bibles_does_not_merge_different_seasons(tmp_path):
    import json
    from series_memory import consolidate_split_bibles

    bible_s1 = {"anime_title": "Synthetic Anime Base", "characters": {}, "episodes_translated": ["ep01"]}
    bible_s2 = {"anime_title": "Synthetic Anime Base 2nd Season", "characters": {}, "episodes_translated": ["ep01"]}
    (tmp_path / "synthetic_anime_base_bible.json").write_text(json.dumps(bible_s1), encoding="utf-8")
    (tmp_path / "synthetic_anime_base_2nd_season_bible.json").write_text(json.dumps(bible_s2), encoding="utf-8")
    pairs = consolidate_split_bibles(tmp_path)
    assert pairs == []
    assert (tmp_path / "synthetic_anime_base_bible.json").exists()
    assert (tmp_path / "synthetic_anime_base_2nd_season_bible.json").exists()


@pytest.mark.unit
def test_t10_6_3_8_consolidate_split_bibles_is_idempotent(tmp_path):
    import json
    from series_memory import consolidate_split_bibles

    bible_a = {"anime_title": "Synthetic Anime Base S2", "characters": {}, "episodes_translated": ["ep01"]}
    bible_b = {"anime_title": "Synthetic Anime Base II", "characters": {}, "episodes_translated": ["ep02"]}
    (tmp_path / "synthetic_anime_base_s2_bible.json").write_text(json.dumps(bible_a), encoding="utf-8")
    (tmp_path / "synthetic_anime_base_ii_bible.json").write_text(json.dumps(bible_b), encoding="utf-8")
    pairs_first = consolidate_split_bibles(tmp_path)
    assert len(pairs_first) == 1
    pairs_second = consolidate_split_bibles(tmp_path)
    assert pairs_second == []


@pytest.mark.unit
@pytest.mark.parametrize(
    "text,expected",
    [
        ("Located at InstytucjaAlfa Academy, the cadets train.", ["InstytucjaAlfa"]),
        ("The KrainaBeta Kingdom is at war.", ["KrainaBeta"]),
        ("UczelniaGamma University hosts the tournament.", ["UczelniaGamma"]),
        ("Akademia sztuk InstytucjaAlfa wita nowych uczniów.", ["InstytucjaAlfa"]),
        ("No institutions here.", []),
        ("Located at the city center.", []),
    ],
)
def test_t11_0_c_1_extract_institutional_toponyms_patterns(tmp_path, text, expected):
    """FIX-C.1: ekstrakcja institutional_toponyms z tekstu EN i PL."""
    from series_memory import SeriesBible
    sm = SeriesBible(anime_title="Seria Testowa", storage_dir=tmp_path)
    result = sm._extract_institutional_toponyms([text])
    assert result == expected


@pytest.mark.unit
def test_t11_0_c_2_institutional_toponym_not_overwrite_character_key(tmp_path):
    """FIX-C.1: institutional_toponym nie nadpisuje istniejącego klucza głównego w characters."""
    from series_memory import SeriesBible
    sm = SeriesBible(anime_title="Seria Testowa", storage_dir=tmp_path)
    sm.data["characters"] = {
        "InstytucjaAlfa": {
            "gender": "FEMALE",
            "priority": "P0",
            "has_verified_gender": True,
            "aliases": ["InstytucjaAlfa"],
        }
    }
    sm._register_institutional_toponyms_from_sources(["InstytucjaAlfa Academy"])
    assert "InstytucjaAlfa" not in sm.data.get("institutional_toponyms", [])
    assert "InstytucjaAlfa" in sm.data["characters"]


@pytest.mark.unit
def test_t11_0_c_3_multi_token_character_preserved_after_toponym_registration(tmp_path):
    """FIX-C.1 + FIX-C.2: dwuczłonowa postać P0 pozostaje w characters i declensions po odpięciu nazwiska-toponimu."""
    from series_memory import SeriesBible
    sm = SeriesBible(anime_title="Seria Testowa", storage_dir=tmp_path)
    sm.data["characters"] = {
        "Bohaterka InstytucjaAlfa": {
            "gender": "FEMALE",
            "priority": "P0",
            "has_verified_gender": True,
            "aliases": ["Bohaterka", "InstytucjaAlfa", "Bohaterka InstytucjaAlfa"],
        }
    }
    sm.data["declensions"] = {
        "Bohaterka InstytucjaAlfa": {
            "M": "Bohaterka InstytucjaAlfa",
            "D": "Bohaterki InstytucjaAlfa",
            "N": "Bohaterką InstytucjaAlfa",
        }
    }
    sm._register_institutional_toponyms_from_sources(["InstytucjaAlfa Academy"])
    sm._sanitize_loaded_bible_in_ram()
    assert "Bohaterka InstytucjaAlfa" in sm.data["characters"]
    assert "Bohaterka InstytucjaAlfa" in sm.data["declensions"]
    assert "Bohaterka" in sm.data["characters"]["Bohaterka InstytucjaAlfa"]["aliases"]
    assert "InstytucjaAlfa" not in sm.data["characters"]["Bohaterka InstytucjaAlfa"]["aliases"]
    assert "instytucjaalfa" not in sm._actor_aliases_index


@pytest.mark.unit
def test_t11_0_c_4_conflicting_surnames_does_not_trigger_disk_save(tmp_path):
    """FIX-C.2: filtrowanie kolizyjnego nazwiska w RAM nie wywołuje zapisu na dysk (ochrona Z16)."""
    from series_memory import SeriesBible
    sm = SeriesBible(anime_title="Seria Testowa", storage_dir=tmp_path)
    sm.data["characters"] = {
        "Bohater KrainaBeta": {
            "gender": "MALE",
            "priority": "P0",
            "has_verified_gender": True,
            "aliases": ["Bohater", "KrainaBeta", "Bohater KrainaBeta"],
        }
    }
    sm.data["institutional_toponyms"] = ["KrainaBeta"]
    sm.data["entity_categories"] = {"KrainaBeta": "TOPONYM"}
    files_before = set(tmp_path.iterdir())
    sm._sanitize_loaded_bible_in_ram()
    files_after = set(tmp_path.iterdir())
    assert files_before == files_after


@pytest.mark.unit
def test_t11_0_c_5_is_non_character_entity_with_prepositional_context(tmp_path):
    """FIX-C.3a: is_non_character_entity rozpoznaje kontekst przyimkowy dla toponimu instytucjonalnego."""
    from series_memory import SeriesBible
    sm = SeriesBible(anime_title="Seria Testowa", storage_dir=tmp_path)
    sm.data["characters"] = {
        "Bohater KrainaBeta": {
            "gender": "MALE",
            "priority": "P0",
            "has_verified_gender": True,
            "aliases": ["Bohater", "KrainaBeta"],
        }
    }
    sm.data["institutional_toponyms"] = ["KrainaBeta"]
    sm.data["entity_categories"] = {"KrainaBeta": "TOPONYM"}
    assert sm.is_non_character_entity("KrainaBeta") is False
    assert sm.is_non_character_entity("KrainaBeta", context="friendly relations with KrainaBeta,") is True
    assert sm.is_non_character_entity("Bohater", context="Bohater arrived from KrainaBeta.") is False


@pytest.mark.unit
def test_t11_0_c_8_character_preserved_with_prepositional_context(tmp_path):
    """FIX-C.3a: wywołanie is_non_character_entity z kontekstem zachowuje postać w characters i declensions."""
    from series_memory import SeriesBible
    sm = SeriesBible(anime_title="Seria Testowa", storage_dir=tmp_path)
    sm.data["characters"] = {
        "Bohaterka UczelniaGamma": {
            "gender": "FEMALE",
            "has_verified_gender": True,
            "aliases": ["Bohaterka", "UczelniaGamma"],
        }
    }
    sm.data["declensions"] = {
        "Bohaterka UczelniaGamma": {"M": "Bohaterka UczelniaGamma", "D": "Bohaterki UczelniaGamma"}
    }
    sm.data["institutional_toponyms"] = ["UczelniaGamma"]
    assert sm.is_non_character_entity("UczelniaGamma", context="w UczelniaGamma") is True
    assert "Bohaterka UczelniaGamma" in sm.data["characters"]
    assert "Bohaterka UczelniaGamma" in sm.data["declensions"]



@pytest.mark.unit
def test_t11_0_e_1_camelcase_split_mob_man_2(tmp_path):
    """FIX-E.1: MobMan i MobMan2 otrzymują gender=MALE i oba klucze przetrwają _sanitize_loaded_bible_in_ram."""
    from series_memory import SeriesBible
    sm = SeriesBible(anime_title="Seria Testowa", storage_dir=tmp_path)
    sm.data["characters"] = {}
    sm.populate_secondary_actor_tags(["MobMan", "MobMan2"])
    sm._sanitize_loaded_bible_in_ram()
    assert sm.data["characters"]["MobMan"]["gender"] == "MALE"
    assert sm.data["characters"]["MobMan2"]["gender"] == "MALE"


@pytest.mark.unit
def test_t11_0_e_2_camelcase_split_mob_woman_and_mean_girl(tmp_path):
    """FIX-E.1: MobWoman -> FEMALE, MeanGirl -> FEMALE (w SeriesBible oraz resolve_lexical_label_gender)."""
    from series_memory import SeriesBible, resolve_lexical_label_gender
    sm = SeriesBible(anime_title="Seria Testowa", storage_dir=tmp_path)
    sm.data["characters"] = {}
    sm.populate_secondary_actor_tags(["MobWoman", "MeanGirl"])
    assert sm.data["characters"]["MobWoman"]["gender"] == "FEMALE"
    assert sm.data["characters"]["MeanGirl"]["gender"] == "FEMALE"
    assert resolve_lexical_label_gender("MobWoman")[0] == "FEMALE"
    assert resolve_lexical_label_gender("MobMan2")[0] == "MALE"


@pytest.mark.unit
def test_t11_0_e_3_unknown_gender_can_be_updated(tmp_path):
    """FIX-E.1: istniejący rekord MobWoman z gender=UNKNOWN zostaje zaktualizowany do FEMALE."""
    from series_memory import SeriesBible
    sm = SeriesBible(anime_title="Seria Testowa", storage_dir=tmp_path)
    sm.data["characters"] = {"MobWoman": {"gender": "UNKNOWN", "priority": "P1", "aliases": ["MobWoman"]}}
    sm.populate_secondary_actor_tags(["MobWoman"])
    assert sm.data["characters"]["MobWoman"]["gender"] == "FEMALE"


@pytest.mark.unit
def test_t11_0_e_4_verified_p0_female_not_changed_by_camelcase_split(tmp_path):
    """FIX-E.1: zweryfikowana postać P0 FEMALE pozostaje nienaruszona."""
    from series_memory import SeriesBible
    sm = SeriesBible(anime_title="Seria Testowa", storage_dir=tmp_path)
    sm.data["characters"] = {
        "Bohaterka Pierwsza": {
            "gender": "FEMALE",
            "has_verified_gender": True,
            "priority": "P0",
            "aliases": ["Bohaterka", "Pierwsza", "Bohaterka Pierwsza"],
        }
    }
    sm.populate_secondary_actor_tags(["BohaterkaPierwsza"])
    assert sm.data["characters"]["Bohaterka Pierwsza"]["gender"] == "FEMALE"


@pytest.mark.unit
def test_series_bible_character_record_persists_speech_register(tmp_path):
    """Hotfix 11.1.4: SeriesBible zapisuje speech_register, formatuje go w scoped context i nadpisuje relację przy P0."""
    from series_memory import SeriesBible

    sm = SeriesBible(anime_title="Seria Testowa", storage_dir=tmp_path)
    sm.data["characters"] = {}

    # 1. Rejestracja postaci z rejestrem mowy
    rec = sm.register_character(
        name="WojowniczkaAlfa",
        gender="FEMALE",
        description="Mistrzyni miecza",
        speech_register="Stylizowany rejestr wojowniczki (-aru/-yaru)"
    )
    assert rec.get("speech_register") == "Stylizowany rejestr wojowniczki (-aru/-yaru)"
    assert sm.data["characters"]["WojowniczkaAlfa"]["speech_register"] == "Stylizowany rejestr wojowniczki (-aru/-yaru)"

    # 2. format_scoped_for_batch wypisuje [Rejestr: ...]
    scoped_txt = sm.format_scoped_for_batch("WojowniczkaAlfa wyciąga miecz.")
    assert "WojowniczkaAlfa" in scoped_txt
    assert "[Rejestr: Stylizowany rejestr wojowniczki (-aru/-yaru)]" in scoped_txt

    # 3. Postać z heurystyką relacji zostaje zaktualizowana przez sync_verified_profile_entity
    sm.data["characters"]["PostacRelacyjna"] = {
        "name": "PostacRelacyjna",
        "gender": "UNKNOWN",
        "grammatical_gender": "UNKNOWN",
        "confidence": 0.5,
        "priority": "P2",
        "has_verified_gender": False,
        "aliases": ["PostacRelacyjna"],
        "description": "Postać (wyodrębniono z relacji serii)",
        "entity_category": "ANTHROPONYM"
    }
    updated = sm.sync_verified_profile_entity(
        name="PostacRelacyjna",
        gender="FEMALE",
        has_verified_gender=True,
        description="Główna dowódczyni",
        speech_register="Dystyngowany rejestr arystokratyczny"
    )
    assert updated["gender"] == "FEMALE"
    assert updated["has_verified_gender"] is True
    assert updated["description"] == "Główna dowódczyni"
    assert updated.get("speech_register") == "Dystyngowany rejestr arystokratyczny"
    assert "wyodrębniono z relacji serii" not in updated["description"]
