import pytest
import pysubs2
from series_memory import SeriesBible
from scene_discourse import build_discourse_topology, SceneDiscourseGraph
from translator import MultimodalTranslator, synchronize_ass_event_metadata_and_styles


def test_speaker_gender_arbitration_p0_priority_and_sign_isolation(tmp_path):
    bible_file = tmp_path / "discourse_test_bible.json"
    bible = SeriesBible(bible_path=bible_file, storage_dir=tmp_path)
    bible.data["characters"] = {
        "Wojownik MeskiAlfa": {
            "description": "MĘŻCZYZNA (zweryfikowano przez EpisodeQualityGate)",
            "gender": "MALE",
            "grammatical_gender": "MASCULINE",
            "confidence": 1.0,
            "priority": "P0",
            "has_verified_gender": True,
            "aliases": ["MeskiAliasAlfa", "Wojownik MeskiAlfa"]
        },
        "Czarodziejka ZenskaBeta": {
            "description": "KOBIETA (zweryfikowano przez EpisodeQualityGate)",
            "gender": "FEMALE",
            "grammatical_gender": "FEMININE",
            "confidence": 1.0,
            "priority": "P0",
            "has_verified_gender": True,
            "aliases": ["ZenskiAliasBeta", "Czarodziejka ZenskaBeta"]
        }
    }
    bible._rebuild_actor_aliases_index()

    translator = MultimodalTranslator.__new__(MultimodalTranslator)
    translator.series_bible = bible
    translator.character_registry = {
        "Wojownik MeskiAlfa": "MĘŻCZYZNA (P0 zweryfikowano)",
        "Czarodziejka ZenskaBeta": "KOBIETA (P0 zweryfikowano)"
    }

    # 1. P0 record immunity: Wojownik MeskiAlfa (MALE P0) voiced with female acoustic pitch F0 (~230 Hz / sopran)
    # The verified P0 record MUST prevail over the acoustic pitch!
    ev_male = pysubs2.SSAEvent(start=1000, end=3000, text="Jestem gotów do drogi.", name="Wojownik MeskiAlfa")
    male_gender, male_alerts = translator._arbitrate_speaker_gender(
        event=ev_male,
        raw_phase1_gender=None,
        batch_id=1,
        speaker_tags={1: "sopran żeński ~230 Hz"},
        pl_candidate="Jestem gotów do drogi."
    )
    assert male_gender == "mężczyzna"
    assert any("rekord_p0" in a for a in male_alerts)

    # Czarodziejka ZenskaBeta (FEMALE P0) with male acoustic pitch (bas ~110 Hz)
    ev_fem = pysubs2.SSAEvent(start=3500, end=5500, text="Czekałam na ten moment.", name="Czarodziejka ZenskaBeta")
    fem_gender, fem_alerts = translator._arbitrate_speaker_gender(
        event=ev_fem,
        raw_phase1_gender=None,
        batch_id=2,
        speaker_tags={2: "bas męski ~110 Hz"},
        pl_candidate="Czekałam na ten moment."
    )
    assert fem_gender == "kobieta"
    assert any("rekord_p0" in a for a in fem_alerts)

    # 2. Sign isolation: is_sign receives ungendered default telemetry
    ev_sign = pysubs2.SSAEvent(start=6000, end=8000, text="Szyld karczmy", style="Sign")
    setattr(ev_sign, "is_sign", True)
    sign_gender, sign_alerts = translator._arbitrate_speaker_gender(
        event=ev_sign,
        raw_phase1_gender=None,
        batch_id=3,
        pl_candidate="Szyld karczmy"
    )
    assert sign_gender in ("NEUTRAL", None)
    assert any("napis_ekranowy" in a for a in sign_alerts)

    # 3. Synchronize ASS event.name with verified speaker_name and offscreen styles
    ev_sync = pysubs2.SSAEvent(start=8500, end=10000, text="Głos spoza kadru.", name="MeskiAlfa (S1E1)")
    synced = synchronize_ass_event_metadata_and_styles(
        ev_sync,
        speaker_name="Wojownik MeskiAlfa",
        is_offscreen=True
    )
    assert synced.name == "Wojownik MeskiAlfa"
    assert "Offscreen" in synced.style
    assert "{\\i1}" in synced.text

    # 4. Topology builder verification
    events = [ev_male, ev_fem, ev_sign]
    turns = build_discourse_topology(events, series_bible=bible)
    assert len(turns) >= 2


def test_telemetry_preserves_explicit_event_actor_and_verified_p0_gender():
    from scene_discourse import SceneDiscourseGraph

    bible = SeriesBible(slug="discourse_test_telemetry", db_path=":memory:")
    bible.sync_verified_profile_entity(
        name="Bohater",
        gender="MALE",
        has_verified_gender=True
    )
    event = pysubs2.SSAEvent(start=1000, end=3000, text="Tekst kwestii", name="Bohater")
    
    telemetry = SceneDiscourseGraph.arbitrate_event_telemetry(
        event=event,
        series_bible=bible,
        aux_telemetry={"speaker_gender": "FEMALE"}  # Contradicted by auxiliary signal
    )
    assert telemetry["speaker_name"] == "Bohater"
    assert telemetry["speaker_gender"] == "MALE"
    assert telemetry["has_verified_gender"] is True


def test_asr_window_isolation_and_empty_asr_for_is_sign_events():
    from profiler import EpisodeProfiler

    # 1. Signs receive empty ASR string regardless of raw audio
    assert EpisodeProfiler.sanitize_event_asr("Tło rozmowy w karczmie", is_sign=True) == ""
    assert EpisodeProfiler.sanitize_event_asr("Tytuł odcinka z audio", style="Ep Title") == ""
    assert EpisodeProfiler.sanitize_event_asr("Napis ekranowy", style="Sign") == ""
    assert EpisodeProfiler.sanitize_event_asr("Podpis pod planszą", style="Caption") == ""

    # 2. Dialogue lines preserve strictly isolated speech window
    speech = "Kwestia dialogowa bohatera"
    assert EpisodeProfiler.sanitize_event_asr(speech, is_sign=False, style="Default") == speech


@pytest.mark.parametrize(
    "raw_actor,speaker_p0,addressee_p0,expected_speaker_label,expected_group",
    [
        # DANE TESTOWE: kategoria — surowy separator "/" w polu aktora + scena żeńska (P0.3).
        ("/", "FEMALE", "FEMALE", "POLYLOGUE", "NON_VIRILE"),
        # Kategoria — postać o p0_gender=MALE w scenie żeńskiej (P0.3).
        ("BohaterAlfa", "MALE", "FEMALE", "BohaterAlfa", "NON_VIRILE"),
    ],
)
def test_arbitrate_telemetry_enforces_p0_gender_non_virile_and_polylogue_tag(
    raw_actor, speaker_p0, addressee_p0, expected_speaker_label, expected_group
):
    """Weryfikuje prymat p0_gender mówcy i adresata, kategorię NON_VIRILE oraz czyszczenie separatora '/'."""
    from scene_discourse import SceneDiscourseGraph
    telemetry_node = SceneDiscourseGraph.arbitrate_event_telemetry(
        raw_actor=raw_actor,
        verified_p0_gender=speaker_p0,
        verified_addressee_p0_gender=addressee_p0,
        has_verified_gender=True,
        scene_female_only=True,
    )
    assert telemetry_node["speaker_name"] == expected_speaker_label
    assert telemetry_node["p0_gender"] == speaker_p0
    assert telemetry_node["addressee_gender"] == addressee_p0
    assert telemetry_node["group_virility"] == expected_group


# Test dla Sekcji 2C.2
@pytest.mark.parametrize(
    "event_actor,inferred_actor,p0_gender,expected_actor,expected_gram_gender",
    [
        ("ExplicitSpeakerA", "NeighborSpeakerB", "FEMALE", "ExplicitSpeakerA", "FEMININE"),
        ("ExplicitMaleHero", "ExplicitMaleHero", "MALE", "ExplicitMaleHero", "MASCULINE"),
        ("/", "NeighborSpeakerB", "FEMALE", "POLYLOGUE", "FEMININE"),
    ],
)
def test_arbitrate_telemetry_preserves_explicit_event_actor_and_male_p0(
    event_actor, inferred_actor, p0_gender, expected_actor, expected_gram_gender
):
    """Weryfikuje zachowanie jawnego aktora z [Events], mapowanie MALE->MASCULINE oraz zamianę '/' na POLYLOGUE."""
    node = SceneDiscourseGraph.arbitrate_event_telemetry(
        raw_actor=event_actor,
        inferred_actor=inferred_actor,
        verified_p0_gender=p0_gender,
        has_verified_gender=True,
    )
    assert node["speaker_name"] == expected_actor
    assert node["grammatical_gender"] == expected_gram_gender



# ==============================================================================
# STANDARD 9.4 TESTS (T4.5)
# ==============================================================================

@pytest.mark.unit
def test_arbitrate_telemetry_enforces_p0_gender_for_inferred_and_explicit_speakers(tmp_path):
    """
    T4.5 (Operacja 2C.1): Prawidłowy stan telemetrii speaker_gender = P0 gender
    (series_bible.get_character(speaker).gender) dla wywnioskowanego mówcy
    oraz jawnego mówcy, niezależnie od scene_female_only i defaultu sceny.
    """
    from series_memory import SeriesBible
    from scene_discourse import SceneDiscourseGraph

    bible_path = tmp_path / "telemetry_test_bible.json"
    bible = SeriesBible(bible_path=bible_path, storage_dir=tmp_path)
    bible.sync_verified_profile_entity(
        name="HeroAlpha SurnameBeta",
        gender="MALE",
        has_verified_gender=True
    )
    bible.data["characters"]["HeroAlpha SurnameBeta"]["aliases"] = ["HeroAlpha"]
    bible.sync_verified_profile_entity(
        name="BohaterkaGamma",
        gender="FEMALE",
        has_verified_gender=True
    )
    bible.data["characters"]["BohaterkaGamma"]["aliases"] = ["BohaterkaG"]
    bible._rebuild_actor_aliases_index()

    # 1. Wywnioskowany mówca (inferred_actor) z pustym raw_actor w scenie pozornie wyłącznie kobiecej
    t1 = SceneDiscourseGraph.arbitrate_event_telemetry(
        event=pysubs2.SSAEvent(start=1000, end=3000, text="Musimy walczyć!", name=""),
        inferred_actor="HeroAlpha SurnameBeta",
        series_bible=bible,
        scene_female_only=True,
        aux_telemetry={"speaker_gender": "FEMALE"}
    )
    assert t1["speaker_name"] == "HeroAlpha SurnameBeta"
    assert t1["speaker_gender"] == "MALE"
    assert t1["grammatical_gender"] == "MASCULINE"
    assert t1["has_verified_gender"] is True

    # 2. Jawny mówca męski (raw_actor) w scenie z domyślnym rodzajem żeńskim
    t2 = SceneDiscourseGraph.arbitrate_event_telemetry(
        event=pysubs2.SSAEvent(start=4000, end=6000, text="Osłonię cię!", name="HeroAlpha"),
        series_bible=bible,
        scene_female_only=True,
    )
    assert t2["speaker_name"] == "HeroAlpha"
    assert t2["speaker_gender"] == "MALE"
    assert t2["has_verified_gender"] is True

    # 3. Adresat z bazy wiedzy P0
    t3 = SceneDiscourseGraph.arbitrate_event_telemetry(
        event=pysubs2.SSAEvent(start=7000, end=9000, text="Dziękuję, BohaterkaGamma.", name="HeroAlpha"),
        series_bible=bible,
        addressee="BohaterkaGamma"
    )
    assert t3["addressee_gender"] == "FEMALE"

    # 4. Izolacja napisów ekranowych (is_sign) - neutralna telemetria
    t4 = SceneDiscourseGraph.arbitrate_event_telemetry(
        event=pysubs2.SSAEvent(start=9500, end=11000, text="Kamień milowy", style="Sign"),
        is_sign=True,
        series_bible=bible
    )
    assert t4["is_sign"] is True
    assert t4["speaker_gender"] == "NEUTRAL"


# ==============================================================================
# STANDARD 9.5 TESTS (T5.1)
# ==============================================================================

@pytest.mark.unit
@pytest.mark.parametrize(
    "actor_name,expected_gender_tag",
    [
        ("HeroAlpha SurnameBeta", "MASCULINE"),
        ("Neighbor", "FEMININE"),
        ("BohaterkaBeta", "FEMININE"),
    ]
)
def test_translator_runtime_telemetry_uses_arbitrate_p0_and_bilingual_aliases(actor_name, expected_gender_tag, tmp_path):
    """
    T5.1 (Operacja 2B.1 + 2C.1): Prawidłowy stan ciągu Telemetria: w translator.py = 100% zgodności
    MASCULINE/FEMININE z p0_gender (w tym przez dwujęzyczny alias roli) oraz zachowanie jawnego Name z [Events] ponad tagiem F0.
    """
    from series_memory import SeriesBible
    from scene_discourse import SceneDiscourseGraph
    from translator import format_dry_telemetry_tag
    import pysubs2

    bible = SeriesBible(anime_title="SeriaTestowaAlfa", storage_dir=tmp_path)
    bible.sync_verified_profile_entity(
        name="HeroAlpha SurnameBeta",
        gender="MALE",
        has_verified_gender=True
    )
    bible.sync_verified_profile_entity(
        name="BohaterkaBeta",
        gender="FEMALE",
        has_verified_gender=True
    )
    bible.data.setdefault("characters", {})["Sąsiadka"] = {
        "name": "Sąsiadka",
        "gender": "FEMALE",
        "grammatical_gender": "FEMININE",
        "confidence": 1.0,
        "priority": "P0",
        "has_verified_gender": True,
        "aliases": ["Sąsiadka"],
        "description": "Sąsiadka (kobieta)"
    }
    # Mapuj dwujęzyczne aliasy ról
    bible.map_bilingual_role_aliases(["Neighbor", "HeroAlpha SurnameBeta", "BohaterkaBeta"])

    ev = pysubs2.SSAEvent(start=1000, end=3000, text="Tekst wypowiedzi", name=actor_name)
    telem = SceneDiscourseGraph.arbitrate_event_telemetry(
        event=ev,
        series_bible=bible,
        aux_telemetry={"speaker_gender": "UNKNOWN"}
    )
    spk_gram = telem.get("grammatical_gender")
    assert spk_gram == expected_gender_tag
    assert telem.get("speaker_name") == actor_name

    dry_tag = format_dry_telemetry_tag(
        speaker_gender=spk_gram,
        speaker_confidence=1.0,
        speaker_name=telem.get("speaker_name")
    )
    assert f"Mówca: {actor_name} ({expected_gender_tag})" in dry_tag


# ==============================================================================
# STANDARD 9.6 TESTS (T6.1)
# ==============================================================================
@pytest.mark.unit
@pytest.mark.parametrize(
    "raw_actor,polluted_target_actor,speaker_p0,target_p0,is_monologue,expected_clean_target,expected_target_gender",
    [
        (
            "BohaterkaGamma",
            "HeroAlpha (Kobieta)",
            "FEMALE",
            "MALE",
            False,
            "HeroAlpha",
            "MASCULINE",
        ),
        (
            "HeroAlpha",
            "BohaterkaGamma (Mężczyzna - Scena Wyłącznie Męska)",
            "MALE",
            "FEMALE",
            False,
            "BohaterkaGamma",
            "FEMININE",
        ),
        (
            "HeroAlpha",
            "HeroAlpha (Mężczyzna - Scena Wyłącznie Męska)",
            "MALE",
            "MALE",
            True,
            "",
            None,
        ),
    ],
)
def test_arbitrate_telemetry_strips_f0_parentheses_from_target_actor_and_enforces_p0(
    raw_actor,
    polluted_target_actor,
    speaker_p0,
    target_p0,
    is_monologue,
    expected_clean_target,
    expected_target_gender,
):
    from series_memory import SeriesBible
    from scene_discourse import SceneDiscourseGraph

    bible = SeriesBible(slug="test_target_actor_clean_p0")
    bible.sync_verified_profile_entity("HeroAlpha", "MALE", has_verified_gender=True)
    bible.sync_verified_profile_entity("BohaterkaGamma", "FEMALE", has_verified_gender=True)

    res = SceneDiscourseGraph.arbitrate_event_telemetry(
        raw_actor=raw_actor,
        target_actor=polluted_target_actor,
        series_bible=bible,
        is_internal_monologue=is_monologue,
    )
    assert res.get("target_actor", "") == expected_clean_target
    assert res.get("target_gender") == expected_target_gender or res.get("addressee_gender") in (expected_target_gender, "MALE" if expected_target_gender == "MASCULINE" else "FEMALE")
    assert "(Kobieta) (MASCULINE)" not in res.get("dry_telemetry", "")
    assert "(Mężczyzna) (FEMININE)" not in res.get("dry_telemetry", "")


# ==============================================================================
# STANDARD 9.7 TESTS (T7.2)
# ==============================================================================
@pytest.mark.unit
@pytest.mark.parametrize(
    "secondary_tag,expected_gender,expected_grammatical_gender",
    [
        ("Boy", "MALE", "MASCULINE"),
        ("Girl", "FEMALE", "FEMININE"),
    ],
)
def test_populate_secondary_actor_tags_infers_lexical_gender_for_boy_and_girl_tags(
    secondary_tag, expected_gender, expected_grammatical_gender
):
    from series_memory import SeriesBible
    from scene_discourse import SceneDiscourseGraph

    bible = SeriesBible(slug="test_secondary_lexical_gender")
    bible.populate_secondary_actor_tags([secondary_tag])
    char_entry = bible.get_character(secondary_tag)
    assert char_entry is not None
    assert char_entry.get("gender") == expected_gender
    assert char_entry.get("grammatical_gender") == expected_grammatical_gender

    res = SceneDiscourseGraph.arbitrate_event_telemetry(
        raw_actor="BohaterkaDelta",
        target_actor=secondary_tag,
        series_bible=bible,
        is_internal_monologue=False,
    )
    assert res.get("target_gender") == expected_grammatical_gender or res.get("addressee_gender") == expected_grammatical_gender


# ==============================================================================
# STANDARD 9.8 TESTS (T8.1)
# ==============================================================================
@pytest.mark.unit
@pytest.mark.parametrize(
    "secondary_tag,scene_gender_override,expected_audited_gender,expected_telemetry_gender",
    [
        ("Boy", "FEMALE", "MALE", "MASCULINE"),
        ("Girl", "MALE", "FEMALE", "FEMININE"),
    ],
)
def test_secondary_lexical_gender_immunity_against_scene_gender_override_and_male_speaker_non_virile_ban(
    secondary_tag, scene_gender_override, expected_audited_gender, expected_telemetry_gender
):
    from series_memory import SeriesBible
    from scene_discourse import SceneDiscourseGraph

    bible = SeriesBible(slug="test_lexical_gender_immunity_98")
    bible.populate_secondary_actor_tags([secondary_tag])
    char_entry = bible.get_character(secondary_tag)
    assert char_entry is not None
    assert char_entry.get("has_verified_gender") is True

    audited_g, is_cont = bible.audit_speaker_metadata_against_audio(
        secondary_tag, audio_gender=scene_gender_override, scene_gender=scene_gender_override
    )
    assert is_cont is False
    assert audited_g == expected_audited_gender
    assert bible.get_character(secondary_tag).get("gender") == expected_audited_gender

    res = SceneDiscourseGraph.arbitrate_event_telemetry(
        raw_actor="HeroAlpha",
        verified_p0_gender="MALE",
        target_actor=f"{secondary_tag} (Kobieta)",
        series_bible=bible,
        scene_female_only=True,
        is_internal_monologue=False,
    )
    assert res.get("target_gender") == expected_telemetry_gender


# ==============================================================================
# STANDARD 9.9 TESTS (T9.1, T9.2)
# ==============================================================================
import argparse


@pytest.mark.unit
@pytest.mark.parametrize(
    "subs_arg,env_honorifics,expected_inputs,expected_keep_honorifics",
    [
        ("episode_input_a.ass", "true", ["episode_input_a.ass"], True),
        ("episode_input_b.ass", "false", ["episode_input_b.ass"], False),
    ],
)
def test_non_tty_cli_resolves_subs_argument_and_honorifics_env_without_stdin_prompt(
    subs_arg, env_honorifics, expected_inputs, expected_keep_honorifics
):
    from main import resolve_cli_inputs_and_honorifics

    ns = argparse.Namespace(input=None, subs=subs_arg, no_honorifics=False, honorifics=False)
    raw_inputs, keep_hon = resolve_cli_inputs_and_honorifics(
        ns, is_tty=False, env_keep_honorifics=env_honorifics
    )
    assert raw_inputs == expected_inputs
    assert keep_hon is expected_keep_honorifics


@pytest.mark.unit
@pytest.mark.parametrize(
    "spk_gram,spk_gender,scene_female_only,expected_we_virility,expected_group_virility",
    [
        ("MASCULINE", "MALE", True, "VIRILE", "NON_VIRILE"),
        ("FEMININE", "FEMALE", True, "NON_VIRILE", "NON_VIRILE"),
    ],
)
def test_we_group_virility_depends_on_speaker_gender_and_preserves_female_we_group_with_male_target(
    spk_gram, spk_gender, scene_female_only, expected_we_virility, expected_group_virility
):
    from scene_discourse import SceneDiscourseGraph
    import pysubs2

    event = pysubs2.SSAEvent(start=1000, end=3000, text="Tekst wypowiedzi.", name="Mówca")
    res = SceneDiscourseGraph.arbitrate_event_telemetry(
        event=event,
        aux_telemetry={
            "grammatical_gender": spk_gram,
            "speaker_gender": spk_gender,
        },
        scene_female_only=scene_female_only,
    )
    assert res.get("we_virility") == expected_we_virility
    assert res.get("group_virility") == expected_group_virility


@pytest.mark.unit
@pytest.mark.parametrize(
    "raw_actor_label,expected_speaker_name,expected_speaker_gender,expected_grammatical_gender",
    [
        ("Bohater (M)", "Bohater", "MALE", "MASCULINE"),
        ("Bohaterka (F)", "Bohaterka", "FEMALE", "FEMININE"),
        ("Aktor (120Hz)", "Aktor", "UNKNOWN", "UNKNOWN"),
    ],
)
def test_arbitrate_telemetry_extracts_explicit_actor_gender_before_f0_parentheses_strip(
    raw_actor_label, expected_speaker_name, expected_speaker_gender, expected_grammatical_gender
):
    from scene_discourse import SceneDiscourseGraph
    import pysubs2

    event = pysubs2.SSAEvent(start=1000, end=3000, text="Kwestia dialogowa.", name=raw_actor_label)
    res = SceneDiscourseGraph.arbitrate_event_telemetry(event=event)
    assert res.get("speaker_name") == expected_speaker_name
    assert res.get("speaker_gender") == expected_speaker_gender
    assert res.get("grammatical_gender") == expected_grammatical_gender


# ==============================================================================
# STANDARD 10.0.2 REGRESSION TESTS (A-09 Wzorzec 1, A-11)
# ==============================================================================


@pytest.mark.unit
@pytest.mark.parametrize(
    "speaker_actor,speaker_gender,target_actor,target_gender,scene_female_only,expected_we_virility",
    [
        ("HeroAlpha", "MALE", "HeroineBeta", "FEMALE", True, "VIRILE"),
        ("HeroineBeta", "FEMALE", "HeroAlpha", "MALE", True, "NON_VIRILE"),
    ],
)
def test_arbitrate_telemetry_we_virility_respects_speaker_p0_gender_in_female_scene(
    speaker_actor, speaker_gender, target_actor, target_gender, scene_female_only, expected_we_virility
):
    from series_memory import SeriesBible
    from scene_discourse import SceneDiscourseGraph
    import pysubs2
    bible = SeriesBible(slug="test_we_virility_p0", db_path=":memory:")
    bible.sync_verified_profile_entity(speaker_actor, speaker_gender, has_verified_gender=True)
    bible.sync_verified_profile_entity(target_actor, target_gender, has_verified_gender=True)
    event = pysubs2.SSAEvent(start=1000, end=3000, text="Kwestia.", name=speaker_actor)
    telem = SceneDiscourseGraph.arbitrate_event_telemetry(
        event=event,
        raw_actor=speaker_actor,
        target_actor=target_actor,
        series_bible=bible,
        scene_female_only=scene_female_only,
        is_internal_monologue=False,
    )
    assert telem["we_virility"] == expected_we_virility


@pytest.mark.unit
@pytest.mark.parametrize(
    "group_participants,expected_virility",
    [
        ([("HeroineA", "FEMALE"), ("HeroineB", "FEMALE")], "NON_VIRILE"),
        ([("HeroineA", "FEMALE")], "AMBIGUOUS"),
        ([("HeroA", "MALE"), ("HeroineB", "FEMALE")], "VIRILE"),
    ],
)
def test_virility_threshold_ge_2(group_participants, expected_virility):
    from scene_discourse import classify_we_group_gender
    from series_memory import SeriesBible
    bible = SeriesBible(slug="test_virility_thresh", db_path=":memory:")
    for name, g in group_participants:
        bible.sync_verified_profile_entity(name, g, has_verified_gender=True)
    names_set = {p[0] for p in group_participants}
    virility, _ = classify_we_group_gender(names_set, series_bible=bible)
    assert virility == expected_virility


# ==============================================================================
# STANDARD 10.0.3 / 10.1 REGRESSION TESTS (2B.3, 2B.4, 2B.5)
# ==============================================================================


@pytest.mark.unit
@pytest.mark.parametrize(
    "speaker_gender,f0_val,generic_addressee,expected_target_gender,expected_gram_gender",
    [
        ("FEMALE", 295.0, "Mężczyzna", "MALE", "MASCULINE"),
        ("FEMALE", 285.0, "Grupa Mężczyzn", "MALE", "MASCULINE"),
        ("FEMALE", 270.0, "Dwóch Mężczyzn", "MALE", "MASCULINE"),
        ("MALE", 115.0, "Kobieta", "FEMALE", "FEMININE"),
        ("MALE", 120.0, "Grupa Kobiet", "FEMALE", "FEMININE"),
        ("MALE", 280.0, "Strażnik Zamkowy", "MALE", "MASCULINE"),
        ("MALE", 265.0, "Mieszkaniec Miasta", "MALE", "MASCULINE"),
    ],
)
def test_generic_addressee_and_role_labels_immune_to_speaker_f0_contamination(
    speaker_gender, f0_val, generic_addressee, expected_target_gender, expected_gram_gender
):
    from scene_discourse import SceneDiscourseGraph

    telem = SceneDiscourseGraph.arbitrate_event_telemetry(
        raw_actor="SpeakerAlpha",
        verified_p0_gender=speaker_gender,
        target_actor=generic_addressee,
        f0_hz=f0_val,
    )
    assert telem["addressee_gender"] == expected_target_gender
    assert "target_grammatical_gender" in telem, \
        f"Brak klucza 'target_grammatical_gender' w telemetrii: {list(telem.keys())}"
    assert telem["target_grammatical_gender"] == expected_gram_gender
    assert telem["target_gender"] == expected_gram_gender


@pytest.mark.unit
@pytest.mark.parametrize(
    "explicit_actor,p0_gender,expected_speaker_name",
    [
        ("HeroAlpha", "MALE", "HeroAlpha"),
        ("HeroineBeta", "FEMALE", "HeroineBeta"),
    ],
)
def test_explicit_ass_actor_not_overwritten_by_hallucinated_diarization(
    explicit_actor, p0_gender, expected_speaker_name
):
    from series_memory import SeriesBible
    from scene_discourse import SceneDiscourseGraph
    bible = SeriesBible(slug="test_explicit_actor", db_path=":memory:")
    bible.sync_verified_profile_entity(explicit_actor, p0_gender, has_verified_gender=True)
    telem = SceneDiscourseGraph.arbitrate_event_telemetry(
        raw_actor=explicit_actor,
        target_actor="OtherSpeaker",
        series_bible=bible,
    )
    assert telem["speaker_name"] == expected_speaker_name
    assert telem["speaker_p0_verified"] is True


@pytest.mark.unit
@pytest.mark.parametrize(
    "first_person_form,expected_gender",
    [
        ("myślałem, że to koniec", "MALE"),
        ("miałem go na oku", "MALE"),
        ("zebrałem ludzi", "MALE"),
        ("usłyszałem hałas", "MALE"),
    ],
)
def test_male_first_person_forms_override_acoustic_f0_feminine(
    first_person_form, expected_gender
):
    from scene_discourse import SceneDiscourseGraph
    telem = SceneDiscourseGraph.arbitrate_event_telemetry(
        raw_actor="SoldierAlpha",
        polish_text=first_person_form,
        f0_hz=320.0,
    )
    assert telem["speaker_gender"] == expected_gender, \
        f"Forma 1. os. '{first_person_form}' powinna dać {expected_gender}, otrzymano {telem['speaker_gender']}"


# T10.1.7 (C-2) -> tests/test_discourse_and_translator.py
@pytest.mark.unit
@pytest.mark.parametrize("speaker_p0_gender,expected_gender", [
    ("MALE", "MALE"),
    ("FEMALE", "FEMALE"),
])
def test_arbitrate_event_telemetry_honors_speaker_p0_gender_kwarg(speaker_p0_gender, expected_gender):
    from scene_discourse import SceneDiscourseGraph
    res = SceneDiscourseGraph.arbitrate_event_telemetry(
        raw_actor="HeroAlpha",
        speaker_p0_gender=speaker_p0_gender,
        target_actor="HeroineBeta",
    )
    assert res.get("speaker_gender") == expected_gender


@pytest.mark.unit
def test_t11_0_c_6_detect_event_vocative_rejects_prepositional_candidate(tmp_path):
    """FIX-C.3b: nazwa własna poprzedzona przyimkiem ('with InstytucjaAlfa,') nie jest klasyfikowana jako wołacz."""
    from series_memory import SeriesBible
    from scene_discourse import _detect_event_vocative
    sm = SeriesBible(anime_title="Seria Testowa", storage_dir=tmp_path)
    sm.data["characters"] = {
        "Bohaterka InstytucjaAlfa": {
            "gender": "FEMALE",
            "priority": "P0",
            "has_verified_gender": True,
            "aliases": ["Bohaterka", "InstytucjaAlfa"],
        }
    }
    result = _detect_event_vocative(
        "This event is also supposed to deepen friendly relations with InstytucjaAlfa,",
        series_bible=sm,
        current_speaker="MowcaPierwszy",
    )
    assert result == (None, None) or result[0] is None


@pytest.mark.unit
def test_t11_0_c_7_detect_event_vocative_accepts_true_vocative(tmp_path):
    """FIX-C.3b: prawdziwy wołacz na początku zdania (bez przyimka) jest poprawnie rozpoznawany."""
    from series_memory import SeriesBible
    from scene_discourse import _detect_event_vocative
    sm = SeriesBible(anime_title="Seria Testowa", storage_dir=tmp_path)
    sm.data["characters"] = {
        "BohaterAlfa": {
            "gender": "MALE",
            "priority": "P0",
            "has_verified_gender": True,
            "aliases": ["BohaterAlfa"],
        }
    }
    result = _detect_event_vocative(
        "BohaterAlfa, chodź tutaj!",
        series_bible=sm,
        current_speaker="MowcaDrugi",
    )
    assert result[0] == "BohaterAlfa"
    assert result[1] == "MALE"



@pytest.mark.unit
def test_t11_0_e_5_mob_man_vocative_works(tmp_path):
    """FIX-E.2: jawny wołacz od MobMan ustawia target_speaker."""
    import pysubs2
    from series_memory import SeriesBible
    from scene_discourse import SpeakerTurn, resolve_turn_addressee
    sm = SeriesBible(anime_title="Seria Testowa", storage_dir=tmp_path)
    sm.data["characters"] = {
        "BohaterAlfa": {"gender": "MALE", "priority": "P0", "has_verified_gender": True, "aliases": ["BohaterAlfa"]}
    }
    turn = SpeakerTurn(speaker="MobMan", events=[pysubs2.SSAEvent(start=0, end=2000, text="BohaterAlfa, chodź tu!")])
    result = resolve_turn_addressee(turn, previous_turn=None, series_bible=sm)
    assert result.target_speaker == "BohaterAlfa"


@pytest.mark.unit
def test_t11_0_e_6_mob_deictic_3rd_person_not_vocative(tmp_path):
    """FIX-E.2: zdania deiktyczne 3. osoby od Mob* nie przypisują monarchy ani księżniczki jako adresata."""
    import pysubs2
    from series_memory import SeriesBible
    from scene_discourse import SpeakerTurn, resolve_all_speaker_turns
    sm = SeriesBible(anime_title="Seria Testowa", storage_dir=tmp_path)
    sm.data["characters"] = {
        "KsiezniczkaBeta": {
            "gender": "FEMALE",
            "priority": "P0",
            "has_verified_gender": True,
            "aliases": ["KsiezniczkaBeta"],
        },
        "MonarchaAlfa": {
            "gender": "MALE",
            "priority": "P0",
            "has_verified_gender": True,
            "aliases": ["MonarchaAlfa"],
        },
    }
    t1 = SpeakerTurn(
        speaker="MobMan",
        events=[pysubs2.SSAEvent(start=1000, end=3000, text="Is that the famous KsiezniczkaBeta?")],
    )
    t2 = SpeakerTurn(
        speaker="MobWoman",
        events=[pysubs2.SSAEvent(start=3500, end=5500, text="They say she's been in InstytucjaAlfa all this time.")],
    )
    t3 = SpeakerTurn(
        speaker="MonarchaAlfa",
        events=[pysubs2.SSAEvent(start=6400, end=9000, text="Welcome to the festival.")],
    )
    resolve_all_speaker_turns([t1, t2, t3], series_bible=sm)
    assert t1.target_speaker != "KsiezniczkaBeta"
    assert t2.target_speaker != "MonarchaAlfa"


@pytest.mark.unit
def test_t11_0_e_7_mob_deictic_per_clause_keeps_vocative(tmp_path):
    """FIX-E.2: filtr deiktyków 3. os. działa per klauzula i zachowuje wołacz z pierwszego zdania."""
    import pysubs2
    from series_memory import SeriesBible
    from scene_discourse import SpeakerTurn, resolve_turn_addressee
    sm = SeriesBible(anime_title="Seria Testowa", storage_dir=tmp_path)
    sm.data["characters"] = {
        "BohaterAlfa": {"gender": "MALE", "priority": "P0", "has_verified_gender": True, "aliases": ["BohaterAlfa"]},
        "KsiezniczkaBeta": {
            "gender": "FEMALE",
            "priority": "P0",
            "has_verified_gender": True,
            "aliases": ["KsiezniczkaBeta"],
        },
    }
    turn = SpeakerTurn(
        speaker="MobMan",
        events=[pysubs2.SSAEvent(start=0, end=3000, text="BohaterAlfa, słyszałeś? Is that the famous KsiezniczkaBeta?")],
    )
    result = resolve_turn_addressee(turn, previous_turn=None, series_bible=sm)
    assert result.target_speaker == "BohaterAlfa"



@pytest.mark.unit
def test_t11_1_3_3_episodic_male_roles_lexical_and_registry_arbitration(tmp_path):
    """
    T11.1.3_3 (INC-AVT-021): Weryfikacja rozszerzenia SECONDARY_LEXICAL_MALE_NOUNS o role epizodyczne
    (w tym ról Bandit A, Lookout, Rebel) oraz pierwszenstwa rejestru postaci przed zerowaniem generycznym.
    """
    import pysubs2
    from series_memory import SECONDARY_LEXICAL_MALE_NOUNS, SeriesBible
    from translator import MultimodalTranslator

    for expected_role in ["bandit", "brigand", "thug", "rebel", "retainer", "lookout", "soldier", "guard", "mercenary", "warrior"]:
        assert expected_role in SECONDARY_LEXICAL_MALE_NOUNS

    tr = MultimodalTranslator.__new__(MultimodalTranslator)
    tr.character_registry = {}
    tr.FEMALE_ROLE_KEYWORDS = ["kobieta", "dziewczyna", "female", "girl", "woman"]
    tr.MALE_ROLE_KEYWORDS = ["mezczyzna", "chlopak", "male", "boy", "man"]
    tr.BOY_ROLE_KEYWORDS = ["chlopiec", "boy", "kid"]
    tr.series_bible = SeriesBible(anime_title="SeriaTestowaAlfa", storage_dir=tmp_path)

    ev_bandit = pysubs2.SSAEvent(start=1000, end=3000, text="Hand over your money!")
    ev_bandit.name = "Bandit A"
    g_bandit, alerts_bandit = tr._arbitrate_speaker_gender(ev_bandit, raw_speaker_name="Bandit A")
    assert g_bandit == "mężczyzna"

    ev_lookout = pysubs2.SSAEvent(start=3500, end=5000, text="Enemy approaching!")
    ev_lookout.name = "Lookout"
    g_lookout, _ = tr._arbitrate_speaker_gender(ev_lookout, raw_speaker_name="Lookout")
    assert g_lookout == "mężczyzna"

    tr.character_registry["Rebel"] = "mezczyzna (partyzant)"
    ev_rebel = pysubs2.SSAEvent(start=5500, end=7000, text="We fight for freedom.")
    ev_rebel.name = "Rebel"
    g_rebel, _ = tr._arbitrate_speaker_gender(ev_rebel, raw_speaker_name="Rebel")
    assert g_rebel == "mężczyzna"


@pytest.mark.unit
def test_t11_1_3_4_low_pitch_elderly_female_vs_deep_male_f0_shield(tmp_path):
    """
    T11.1.3_4 (INC-AVT-021 / P2-1 / P3-1): Tarcza krtaniowa F0 <= 135 Hz vs F0 > 135 Hz na rzeczywistych
    etykietach SpeakerVoiceClassifier.classify_pitch_register, ochrona altu kobiecego oraz weto Fazy 1.
    """
    import pysubs2
    from series_memory import SeriesBible
    from speaker_diarizer import SpeakerVoiceClassifier
    from translator import MultimodalTranslator

    tr = MultimodalTranslator.__new__(MultimodalTranslator)
    tr.character_registry = {}
    tr.FEMALE_ROLE_KEYWORDS = ["kobieta", "dziewczyna", "female", "girl", "woman"]
    tr.MALE_ROLE_KEYWORDS = ["mezczyzna", "chlopak", "male", "boy", "man"]
    tr.BOY_ROLE_KEYWORDS = ["chlopiec", "boy", "kid"]
    tr.series_bible = SeriesBible(anime_title="SeriaTestowaAlfa", storage_dir=tmp_path)

    ev_alto = pysubs2.SSAEvent(start=1000, end=3000, text="Hear my wisdom.")
    ev_alto.name = "StarszaKobietaAlfa"
    tags_alto = {0: SpeakerVoiceClassifier.classify_pitch_register(142.0)}
    g_alto, _ = tr._arbitrate_speaker_gender(
        ev_alto,
        raw_speaker_name="StarszaKobietaAlfa",
        speaker_tags=tags_alto,
        batch_id=0,
        raw_phase1_gender="kobieta"
    )
    assert g_alto == "kobieta"

    ev_deep = pysubs2.SSAEvent(start=3500, end=5000, text="Halt.")
    ev_deep.name = "StraznikAlfa"
    tags_deep = {0: SpeakerVoiceClassifier.classify_pitch_register(110.0)}
    g_deep, _ = tr._arbitrate_speaker_gender(
        ev_deep,
        raw_speaker_name="StraznikAlfa",
        speaker_tags=tags_deep,
        batch_id=0,
        raw_phase1_gender=None
    )
    assert g_deep == "mężczyzna"

    ev_shout = pysubs2.SSAEvent(start=5500, end=7000, text="Uwooooogh!")
    ev_shout.name = "WojownikAlfa"
    tags_shout = {0: SpeakerVoiceClassifier.classify_pitch_register(240.0)}
    g_shout, alerts_shout = tr._arbitrate_speaker_gender(
        ev_shout,
        raw_speaker_name="WojownikAlfa",
        speaker_tags=tags_shout,
        batch_id=0,
        raw_phase1_gender="mężczyzna"
    )
    assert g_shout == "mężczyzna"
    assert any("weto_krzyku_f0" in a for a in alerts_shout)


@pytest.mark.unit
def test_t11_1_3_5_slash_dyad_mixed_gender_virile_telemetry(tmp_path):
    """
    T11.1.3_5 (P3-A): Weryfikacja arbitrazu virility dla diad i grup laczonych separatorem (POLYLOGUE).
    """
    import pysubs2
    from series_memory import SeriesBible
    from scene_discourse import SceneDiscourseGraph

    sm = SeriesBible(anime_title="SeriaTestowaAlfa", storage_dir=tmp_path)
    sm.data["characters"] = {
        "BohaterAlfa": {"gender": "MALE", "priority": "P0", "has_verified_gender": True, "aliases": ["BohaterAlfa"]},
        "BohaterkaBeta": {"gender": "FEMALE", "priority": "P0", "has_verified_gender": True, "aliases": ["BohaterkaBeta"]},
        "PostacGamma": {"gender": "FEMALE", "priority": "P0", "has_verified_gender": True, "aliases": ["PostacGamma"]},
    }

    ev_mixed = pysubs2.SSAEvent(start=1000, end=4000, text="We are coming!")
    ev_mixed.name = "BohaterAlfa / BohaterkaBeta"
    telem_mixed = SceneDiscourseGraph.arbitrate_event_telemetry(
        event=ev_mixed,
        series_bible=sm
    )
    assert telem_mixed["speaker_name"] == "POLYLOGUE"
    assert telem_mixed["speaker_gender"] == "MALE"
    assert telem_mixed["grammatical_gender"] == "MASCULINE"
    assert telem_mixed["we_virility"] == "VIRILE"
    assert telem_mixed["group_virility"] == "VIRILE"
    assert "[Mówca: POLYLOGUE (MASCULINE)]" in telem_mixed.get("dry_telemetry", "")

    ev_female = pysubs2.SSAEvent(start=4500, end=7000, text="We will do our best!")
    ev_female.name = "BohaterkaBeta / PostacGamma"
    telem_fem = SceneDiscourseGraph.arbitrate_event_telemetry(
        event=ev_female,
        series_bible=sm
    )
    assert telem_fem["speaker_name"] == "POLYLOGUE"
    assert telem_fem["speaker_gender"] == "FEMALE"
    assert telem_fem["grammatical_gender"] == "FEMININE"
    assert telem_fem["we_virility"] == "NON_VIRILE"
    assert telem_fem["group_virility"] == "NON_VIRILE"
    assert "[Mówca: POLYLOGUE (FEMININE)]" in telem_fem.get("dry_telemetry", "")


@pytest.mark.unit
def test_whisper_disambiguator_no_false_positive_dialect_on_common_verbs():
    """Hotfix 11.1.4: Powszechne czasowniki z 'べ' i 'おら' nie wyzwalają fałszywego DIALECT_JP."""
    from whisper_disambiguator import WhisperDisambiguator
    false_positives = [
        ("He stated that truth.", "彼はそう述べた"),
        ("If you compare them both.", "比べれば分かる"),
        ("Everything was finished.", "全て終わった"),
        ("It cannot be cured.", "直らない傷だ"),
        ("A pure and noble stream.", "清らかな川だ"),
    ]
    for en, jp in false_positives:
        cats = WhisperDisambiguator.detect_batch_discourse_categories(en, jp)
        assert "DIALECT_JP" not in cats, f"Fałszywy DIALECT_JP dla: {jp}"


@pytest.mark.unit
def test_whisper_disambiguator_detects_yakuwarigo_aru_yaru_desuwa_ssu_nano():
    """Hotfix 11.1.4: Formy Yakuwarigo (-aru/-yaru, -desu wa, -ssu, -nano) wyzwalają DIALECT_JP."""
    from whisper_disambiguator import WhisperDisambiguator
    yakuwarigo_cases = [
        ("Let's go then.", "行くべ！"),
        ("I will go there.", "おらは行くぞ"),
        ("What are you doing?", "何やるかね"),
        ("I am right here.", "てるあるよ"),
        ("Good afternoon to you.", "ご機嫌よう、ですわ"),
        ("That is impossible.", "無理っすよ"),
        ("It has all gathered.", "揃ったなの"),
    ]
    for en, jp in yakuwarigo_cases:
        cats = WhisperDisambiguator.detect_batch_discourse_categories(en, jp)
        assert "DIALECT_JP" in cats, f"Brak DIALECT_JP dla formy: {jp}"


@pytest.mark.unit
def test_dual_quantifier_you_two_in_mixed_gender_scene_resolves_virile():
    """Hotfix 11.1.4a: Arbitraż kwantyfikatora dualnego ('you two' / 'お二人') w scenie mieszanej jako męskoosobowy (VIRILE)."""
    import pysubs2
    from translator import MultimodalTranslator
    from series_memory import SeriesBible

    sm = SeriesBible(slug="test_dual_virile", db_path=":memory:")
    sm.sync_verified_profile_entity("BohaterMęski", "MALE", has_verified_gender=True)
    sm.sync_verified_profile_entity("BohaterkaŻeńska", "FEMALE", has_verified_gender=True)

    tr = MultimodalTranslator(api_key="mock_key")
    tr.series_bible = sm
    tr.character_registry = {
        "BohaterMęski": {"gender": "MALE", "grammatical_gender": "MASCULINE"},
        "BohaterkaŻeńska": {"gender": "FEMALE", "grammatical_gender": "FEMININE"}
    }

    # 1. Test detekcji dual w _resolve_line_addressee dla angielskiego 'you two'
    ev_spk = pysubs2.SSAEvent(start=1000, end=3000, text="You two should get ready.")
    ev_spk.name = "SpeakerAlpha"
    batch_evs = [
        (1, ev_spk, "You two should get ready.", ""),
        (2, pysubs2.SSAEvent(start=3100, end=4000, text="Yes.", name="BohaterMęski"), "Yes.", ""),
        (3, pysubs2.SSAEvent(start=4100, end=5000, text="Understood.", name="BohaterkaŻeńska"), "Understood.", "")
    ]

    cat_en, label_en = tr._resolve_line_addressee(
        event=ev_spk,
        raw_phase1_addressee=None,
        batch_events=batch_evs,
        event_idx=0,
        whisper_text="",
        clean_text="You two should get ready."
    )
    assert cat_en == "para_mieszana_dual"
    assert "Para Mieszana" in label_en

    # 2. Test detekcji dual w _resolve_line_addressee dla japońskiego 'お二人'
    cat_jp, label_jp = tr._resolve_line_addressee(
        event=ev_spk,
        raw_phase1_addressee=None,
        batch_events=batch_evs,
        event_idx=0,
        whisper_text="お二人は準備してください",
        clean_text="Please get ready."
    )
    assert cat_jp == "para_mieszana_dual"
    assert "Para Mieszana" in label_jp


@pytest.mark.unit
def test_whisper_disambiguator_detects_kansai_yade_hiragana():
    """Hotfix 11.1.4a: WhisperDisambiguator poprawnie rozpoznaje dialektalny znacznik 'やで' w zapisie hiragany."""
    from whisper_disambiguator import WhisperDisambiguator

    en_text = "That's how it is."
    jp_text = "そうやで"
    cats = WhisperDisambiguator.detect_batch_discourse_categories(en_text, jp_text)
    assert "DIALECT_JP" in cats, f"Brak DIALECT_JP dla japońskiego tekstu: {jp_text}"

    # Weryfikacja dodatkowych form z hiraganą 'やで'
    more_samples = [
        "ほんまやで",
        "あかんやで",
        "知らんやで"
    ]
    for s in more_samples:
        c = WhisperDisambiguator.detect_batch_discourse_categories("It is true.", s)
        assert "DIALECT_JP" in c, f"Brak DIALECT_JP dla formy: {s}"


@pytest.mark.unit
def test_T11_1_5_sociolinguistic_register_gated_by_character_dossier():
    """Hotfix 11.1.5 (P1-1 / INC-AVT-026 / E-04): Weryfikacja bramkowania tagu socjolingwistycznego przez profil postaci."""
    from whisper_disambiguator import WhisperDisambiguator

    # 1. Rejestr dziewczęcy zablokowany dla starszego lub męskiego mówcy
    reg_girl = "Rejestr: Rejestr dziewczęcy"
    dossier_elder_male = {"name": "Speaker_Alpha", "gender": "MALE", "age_class": "ELDERLY"}
    res1 = WhisperDisambiguator.validate_pragmatic_register_against_speaker(
        register=reg_girl,
        speaker_name="Speaker_Alpha",
        character_dossier=dossier_elder_male
    )
    assert res1 is None

    dossier_girl = {"name": "Speaker_Beta", "gender": "FEMALE", "age_class": "CHILD"}
    res2 = WhisperDisambiguator.validate_pragmatic_register_against_speaker(
        register=reg_girl,
        speaker_name="Speaker_Beta",
        character_dossier=dossier_girl
    )
    assert res2 == reg_girl

    # 2. Szorstki żołnierski / Bojowy pomijany dla arystokraty bez krzyku bojowego w prozodii
    reg_soldier = "Rejestr: Szorstki żołnierski / Bojowy"
    dossier_noble = {"name": "Speaker_Gamma", "gender": "FEMALE", "dialect_category": "arystokratyczny styl dworski"}
    res_noble = WhisperDisambiguator.validate_pragmatic_register_against_speaker(
        register=reg_soldier,
        speaker_name="Speaker_Gamma",
        character_dossier=dossier_noble,
        prosody_tags="spokojny ton konwersacyjny"
    )
    assert res_noble is None

    res_noble_battle = WhisperDisambiguator.validate_pragmatic_register_against_speaker(
        register=reg_soldier,
        speaker_name="Speaker_Gamma",
        character_dossier=dossier_noble,
        prosody_tags="krzyk bojowy / silne wzburzenie"
    )
    assert res_noble_battle == reg_soldier

    # 3. Feudalny poddańczy / Wasal pomijany dla standardowego powitania w settingu współczesnym
    reg_feudal = "Rejestr: Feudalny poddańczy / Wasal"
    res_office = WhisperDisambiguator.validate_pragmatic_register_against_speaker(
        register=reg_feudal,
        speaker_name="Speaker_Delta",
        audio_jp="ohayou gozaimasu",
        clean_en="Good morning",
        setting_era="Modern Office"
    )
    assert res_office is None

    res_feudal_knight = WhisperDisambiguator.validate_pragmatic_register_against_speaker(
        register=reg_feudal,
        speaker_name="Speaker_Delta",
        audio_jp="ohayou gozaimasu, -dono",
        clean_en="Good morning, my lord",
        setting_era="Fantasy kingdom"
    )
    assert res_feudal_knight == reg_feudal

    # 4. Gwarowy południowy pomijany dla standardowej polszczyzny literackiej bez idiolektu
    reg_dialect = "Rejestr: Rejestr gwarowy południowy"
    dossier_std = {"name": "Speaker_Epsilon", "dialect_category": "standardowa polszczyzna literacka"}
    res_std = WhisperDisambiguator.validate_pragmatic_register_against_speaker(
        register=reg_dialect,
        speaker_name="Speaker_Epsilon",
        character_dossier=dossier_std
    )
    assert res_std is None

    res_idiolect = WhisperDisambiguator.validate_pragmatic_register_against_speaker(
        register=reg_dialect,
        speaker_name="Speaker_Epsilon",
        character_dossier=dossier_std,
        audio_jp="douja"
    )
    assert res_idiolect == reg_dialect


@pytest.mark.unit
def test_T11_1_5_unknown_actor_scene_gender_stability_and_male_only_constraint():
    """Hotfix 11.1.5 (P1-3 / E-03): Weryfikacja stałości rodzaju gramatycznego aktora i egzekwowania male_only_scene."""
    from scene_discourse import SceneDiscourseGraph
    import pysubs2

    # 1. Konsensus płci per aktor w odcinku
    events = [
        pysubs2.SSAEvent(start=1000, end=3000, text="First statement", name="Speaker_Alpha"),
        pysubs2.SSAEvent(start=4000, end=6000, text="Second statement", name="Speaker_Alpha"),
        pysubs2.SSAEvent(start=7000, end=9000, text="Third statement", name="Speaker_Beta"),
    ]
    f0_map = {0: 125.0, 1: 130.0, 2: 230.0}
    consensus = SceneDiscourseGraph.compute_actor_gender_consensus(events, f0_by_line=f0_map)
    assert consensus.get("Speaker_Alpha") == "MALE"
    assert consensus.get("Speaker_Beta") == "FEMALE"

    # 2. Ograniczenie z topologii sekwencji dramatycznej (male_only_scene)
    sdg = SceneDiscourseGraph()
    ev_test = pysubs2.SSAEvent(start=1500, end=2500, text="Line in male scene", name="Speaker_Unknown")
    class DummySeq:
        time_range = "00:01-00:05"
        male_only_scene = True
        female_only_scene = False

    telemetry = sdg.arbitrate_event_telemetry(
        event=ev_test,
        actor="Speaker_Unknown",
        dramatic_sequences=[DummySeq()]
    )
    assert telemetry.get("speaker_gender") == "MALE"


@pytest.mark.unit
def test_T11_1_5_third_person_title_mention_not_locked_as_addressee_and_sign_isolation():
    """Hotfix 11.1.5 (P2-1 / INC-AVT-027 / E-05 / E-06 / E-10): Weryfikacja filtru składniowego 3. osoby i izolacji napisów ekranowych."""
    from scene_discourse import _detect_event_vocative, resolve_turn_addressee, SpeakerTurn, SceneDiscourseGraph
    import pysubs2

    class DummySeriesBible:
        def __init__(self):
            self.data = {"characters": {"Target_Hero": {"name": "Target_Hero", "aliases": ["Duke Target_Hero"]}}}
            self.alias_to_canonical = {"duke target_hero": "Target_Hero", "target_hero": "Target_Hero"}
        def resolve_alias(self, a):
            return self.alias_to_canonical.get(a.lower(), a)
        def get_character_gender(self, name):
            return "MALE"

    sb = DummySeriesBible()

    # 1. Konstrukcja referencyjna 3. osoby nie blokuje postaci jako bezpośredniego adresata
    ev_3rd = pysubs2.SSAEvent(start=1000, end=3000, text="I came on behalf of Duke Target_Hero.")
    voc_name, voc_g = _detect_event_vocative(ev_3rd, series_bible=sb)
    assert voc_name is None
    assert voc_g is None

    # Bezpośredni zwrot wołaczowy zostaje prawidłowo wykryty
    ev_direct = pysubs2.SSAEvent(start=1000, end=3000, text="Target_Hero, please listen carefully!")
    voc_dir, voc_dir_g = _detect_event_vocative(ev_direct, series_bible=sb)
    assert voc_dir == "Target_Hero"

    # 2. Izolacja napisów ekranowych (is_sign)
    turn_sign = SpeakerTurn(speaker="sign", events=[pysubs2.SSAEvent(start=100, end=200, text="Sign content")])
    turn_sign.is_sign = True
    resolved_sign = resolve_turn_addressee(turn_sign, prior_turns=[], series_bible=sb)
    assert resolved_sign.target_speaker is None
    assert resolved_sign.target_confidence == 0.0

    # 3. Czysta reprezentacja SpeakerTurn.__repr__
    repr_str = repr(resolved_sign)
    assert "None" not in repr_str
    assert "AMBIGUOUS" not in repr_str

    # 4. Zachowanie etykiety aktora złożonego w telemetry_tag
    sdg = SceneDiscourseGraph()
    ev_compound = pysubs2.SSAEvent(start=1000, end=2000, text="Reporting for duty.", name="Worker A/B")
    comp_telem = sdg.arbitrate_event_telemetry(event=ev_compound, actor="Worker A/B")
    tag_str = comp_telem.get("telemetry_tag", "")
    assert "Mówca: Worker A/B" in tag_str
    assert "Scena: POLYLOGUE" in tag_str


@pytest.mark.unit
def test_t11_1_6_b3_whisper_cross_speaker_hallucination_dedup():
    """
    Standard 11.1.6 (BŁĄD-3 / DEFEKT 2):
    Weryfikuje WhisperDisambiguator.sanitize_aligned_whisper_transcripts:
    (a) czyszczenie wycieku ASR (>12 znaków JP) dla 1-słowej mikro-kwestii ('Here.', 880ms).
    (b) deduplikację między dwoma różnymi mówcami (zachowanie tylko dla kwestii o pasującym budżecie sylabicznym).
    """
    from whisper_disambiguator import WhisperDisambiguator

    events_meta = [
        {"id": 1, "en_text": "Here.", "duration_ms": 880, "speaker": "Worker_Alpha"},
        {"id": 2, "en_text": "Are you really going there right now?", "duration_ms": 3200, "speaker": "Worker_Alpha"},
        {"id": 3, "en_text": "Yes.", "duration_ms": 1100, "speaker": "Worker_Beta"}
    ]
    whisper_results = {
        1: "それでは本日の作戦を開始するぞ (soredewa honjitsu no sakusen)",
        2: "本当に今からそこへ行くつもりなのか",
        3: "本当に今からそこへ行くつもりなのか"
    }

    sanitized = WhisperDisambiguator.sanitize_aligned_whisper_transcripts(events_meta, whisper_results)

    # (a) Mikro-kwestia zostaje wyczyszczona z wycieku
    assert sanitized[1] == ""

    # (b) Między mówcami A i B transkrypcja zostaje zachowana tylko u mówcy A
    assert sanitized[2] == "本当に今からそこへ行くつもりなのか"
    assert sanitized[3] == ""


@pytest.mark.unit
def test_t11_1_6_b4_offscreen_addressee_isolation_and_compound_actor_ass():
    """
    Standard 11.1.6 (BŁĄD-4 / E-05b):
    Weryfikuje, że:
    1. Mówca ze stylu 'Italics - Top' spoza characters_present nie staje się adresatem kwestii Default.
    2. Generyczny string 'Mężczyzna' nie trafia do 'Adresat:' w telemetry_tag.
    3. Nazwa aktora złożonego 'Worker A/B' zachowuje ukośnik '/' w SSAEvent.name.
    """
    import pysubs2
    from scene_discourse import SpeakerTurn, resolve_turn_addressee, SceneDiscourseGraph

    class MockSequence:
        def __init__(self, time_range, characters_present):
            self.time_range = time_range
            self.characters_present = characters_present

    class MockBible:
        def __init__(self):
            self.dramatic_sequences = [
                MockSequence(time_range="00:01:00-00:02:00", characters_present=["Hero_Alpha", "Hero_Beta"])
            ]

    bible = MockBible()

    # 1. Mówca ze stylu 'Italics - Top' (Offscreen_Guy) nie może zostać wybrany jako adresat dla kwestii Default
    ev_turn = pysubs2.SSAEvent(start=70000, end=72000, text="Where are you going?", style="Default", name="Hero_Alpha")
    turn_curr = SpeakerTurn(speaker="Hero_Alpha", events=[ev_turn])
    turn_curr.style = "Default"

    ev_next = pysubs2.SSAEvent(start=72200, end=74000, text="Breaking news report.", style="Italics - Top", name="Offscreen_Guy")
    turn_next = SpeakerTurn(speaker="Offscreen_Guy", events=[ev_next])
    turn_next.style = "Italics - Top"

    resolved_turn = resolve_turn_addressee(
        turn_curr,
        previous_turn=None,
        series_bible=bible,
        next_turn=turn_next,
        prior_turns=[]
    )
    assert resolved_turn.target_speaker != "Offscreen_Guy"

    # 2. Blokada generycznego 'Mężczyzna' w Adresat:
    sdg = SceneDiscourseGraph()
    ev_generic = pysubs2.SSAEvent(start=1000, end=2000, text="Hello.", name="Speaker_Alpha")
    telem = sdg.arbitrate_event_telemetry(
        event=ev_generic,
        actor="Speaker_Alpha",
        target_actor="Mężczyzna",
        target_gender="MASCULINE"
    )
    telemetry_tag = telem.get("telemetry_tag", "")
    assert "Adresat: Mężczyzna" not in telemetry_tag

    # 3. Zachowanie ukośnika '/' dla 'Worker A/B' w SSAEvent
    from translator import split_oversized_ass_events
    ev_worker = pysubs2.SSAEvent(start=1000, end=2000, text="Working hard.", name="Worker A/B")
    cleaned_events = split_oversized_ass_events([ev_worker])
    assert cleaned_events[0].name == "Worker A/B"


# ==============================================================================
# STANDARD 11.1.7 REGRESSION TESTS (T11.1.7_B2)
# ==============================================================================
@pytest.mark.unit
def test_t11_1_7_b2_whisper_same_speaker_consecutive_duplicate_dedup():
    """Weryfikacja deduplikacji segmentów ASR dla kolejnych kwestii tego samego oraz różnych mówców."""
    from whisper_disambiguator import WhisperDisambiguator

    # 1. Ten sam mówca: dwie kolejne kwestie z różnymi tekstami EN i identycznym japońskim segmentem ASR
    events_same_spk = [
        {"id": 1, "speaker": "SpeakerAlpha", "en_text": "This is a very long sentence spoken by the main character.", "duration_ms": 3000},
        {"id": 2, "speaker": "SpeakerAlpha", "en_text": "Short line.", "duration_ms": 800},
    ]
    # Segment o długości 17 znaków: lepiej pasuje do id: 1 (10 słów * 2.2 = 22 vs len 17) niż do id: 2 (2 słowa * 2.2 = 4.4 vs len 17)
    whisper_results_same = {
        1: "長い日本語の文章がここにありますよ",
        2: "長い日本語の文章がここにありますよ",
    }
    sanitized_same = WhisperDisambiguator.sanitize_aligned_whisper_transcripts(events_same_spk, whisper_results_same)
    assert sanitized_same[1] == "長い日本語の文章がここにありますよ"
    assert sanitized_same[2] == ""

    # 2. Różni mówcy: krótki 4-znakowy przeciek ASR między dwoma różnymi mówcami o różnych tekstach EN
    events_diff_spk = [
        {"id": 10, "speaker": "SpeakerAlpha", "en_text": "Wait for me right now!", "duration_ms": 1500},
        {"id": 11, "speaker": "SpeakerBeta", "en_text": "No.", "duration_ms": 500},
    ]
    whisper_results_diff = {
        10: "待ってよ",  # 4 znaki, 5 słów EN: abs(4 - 11) = 7
        11: "待ってよ",  # 4 znaki, 1 słowo EN: abs(4 - 2.2) = 1.8 -> lepiej pasuje do id: 11
    }
    sanitized_diff = WhisperDisambiguator.sanitize_aligned_whisper_transcripts(events_diff_spk, whisper_results_diff)
    assert sanitized_diff[10] == ""
    assert sanitized_diff[11] == "待ってよ"




