import pytest
import pysubs2
from series_memory import SeriesBible
from scene_discourse import build_discourse_topology, SceneDiscourseGraph
from translator import MultimodalTranslator, synchronize_ass_event_metadata_and_styles


def test_speaker_gender_arbitration_p0_priority_and_sign_isolation(tmp_path):
    bible_file = tmp_path / "discourse_test_bible.json"
    bible = SeriesBible(bible_path=bible_file, storage_dir=tmp_path)
    bible.data["characters"] = {
        "Wojownik Jan": {
            "description": "MĘŻCZYZNA (zweryfikowano przez EpisodeQualityGate)",
            "gender": "MALE",
            "grammatical_gender": "MASCULINE",
            "confidence": 1.0,
            "priority": "P0",
            "has_verified_gender": True,
            "aliases": ["Jan", "Wojownik Jan"]
        },
        "Czarodziejka Anna": {
            "description": "KOBIETA (zweryfikowano przez EpisodeQualityGate)",
            "gender": "FEMALE",
            "grammatical_gender": "FEMININE",
            "confidence": 1.0,
            "priority": "P0",
            "has_verified_gender": True,
            "aliases": ["Anna", "Czarodziejka Anna"]
        }
    }
    bible._rebuild_actor_aliases_index()

    translator = MultimodalTranslator.__new__(MultimodalTranslator)
    translator.series_bible = bible
    translator.character_registry = {
        "Wojownik Jan": "MĘŻCZYZNA (P0 zweryfikowano)",
        "Czarodziejka Anna": "KOBIETA (P0 zweryfikowano)"
    }

    # 1. P0 record immunity: Wojownik Jan (MALE P0) voiced with female acoustic pitch F0 (~230 Hz / sopran)
    # The verified P0 record MUST prevail over the acoustic pitch!
    ev_male = pysubs2.SSAEvent(start=1000, end=3000, text="Jestem gotów do drogi.", name="Wojownik Jan")
    male_gender, male_alerts = translator._arbitrate_speaker_gender(
        event=ev_male,
        raw_phase1_gender=None,
        batch_id=1,
        speaker_tags={1: "sopran żeński ~230 Hz"},
        pl_candidate="Jestem gotów do drogi."
    )
    assert male_gender == "mężczyzna"
    assert any("rekord_p0" in a for a in male_alerts)

    # Czarodziejka Anna (FEMALE P0) with male acoustic pitch (bas ~110 Hz)
    ev_fem = pysubs2.SSAEvent(start=3500, end=5500, text="Czekałam na ten moment.", name="Czarodziejka Anna")
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
    assert sign_gender is None
    assert any("napis_ekranowy" in a for a in sign_alerts)

    # 3. Synchronize ASS event.name with verified speaker_name and offscreen styles
    ev_sync = pysubs2.SSAEvent(start=8500, end=10000, text="Głos spoza kadru.", name="Jan (S1E1)")
    synced = synchronize_ass_event_metadata_and_styles(
        ev_sync,
        speaker_name="Wojownik Jan",
        is_offscreen=True
    )
    assert synced.name == "Wojownik Jan"
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
        ("Artur", "MALE", "FEMALE", "Artur", "NON_VIRILE"),
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
        name="Tokiyuki Hōjō",
        gender="MALE",
        has_verified_gender=True
    )
    bible.data["characters"]["Tokiyuki Hōjō"]["aliases"] = ["Tokiyuki"]
    bible.sync_verified_profile_entity(
        name="Ayako",
        gender="FEMALE",
        has_verified_gender=True
    )
    bible.data["characters"]["Ayako"]["aliases"] = ["Aya"]
    bible._rebuild_actor_aliases_index()

    # 1. Wywnioskowany mówca (inferred_actor) z pustym raw_actor w scenie pozornie wyłącznie kobiecej
    t1 = SceneDiscourseGraph.arbitrate_event_telemetry(
        event=pysubs2.SSAEvent(start=1000, end=3000, text="Musimy walczyć!", name=""),
        inferred_actor="Tokiyuki Hōjō",
        series_bible=bible,
        scene_female_only=True,
        aux_telemetry={"speaker_gender": "FEMALE"}
    )
    assert t1["speaker_name"] == "Tokiyuki Hōjō"
    assert t1["speaker_gender"] == "MALE"
    assert t1["grammatical_gender"] == "MASCULINE"
    assert t1["has_verified_gender"] is True

    # 2. Jawny mówca męski (raw_actor) w scenie z domyślnym rodzajem żeńskim
    t2 = SceneDiscourseGraph.arbitrate_event_telemetry(
        event=pysubs2.SSAEvent(start=4000, end=6000, text="Osłonię cię!", name="Tokiyuki"),
        series_bible=bible,
        scene_female_only=True,
    )
    assert t2["speaker_name"] == "Tokiyuki"
    assert t2["speaker_gender"] == "MALE"
    assert t2["has_verified_gender"] is True

    # 3. Adresat z bazy wiedzy P0
    t3 = SceneDiscourseGraph.arbitrate_event_telemetry(
        event=pysubs2.SSAEvent(start=7000, end=9000, text="Dziękuję, Ayako.", name="Tokiyuki"),
        series_bible=bible,
        addressee="Ayako"
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
