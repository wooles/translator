"""
Zestaw nienaruszalnych, nietautologicznych testów regresyjnych dla Standardu 12.2.0:
- Commit 1 (3 testy): OBS-13a — lokalny polylog Z2 (wtrącenie osoby trzeciej, aktywny ping-pong, historia F1 6–8 linii vs F2 cap 4)
- Commit 2 (1 test): OBS-13b — ochrona aktora zbiorowego/chóru przed F0 FEMININE oraz domyślny VIRILE
- Commit 3 (2 testy): OBS-13c (próg >= 0.90 z kompatybilnością wsteczną 0.80 i propagacją target_confidence) + C-1 (sąsiedzi read-only F2 bez eskalacji CoT)
- Commit 4 (2 testy): Z16-amendment #16 — C-2 (gatunkowo-adaptacyjny ton F2) oraz A-2 (Filar CLXXI separatory tysięcy i czas wojskowy)
- Regresja DEF-02 (1 test): 5 geometrii cięć scen z 11.2.25 + pauza 5000 ms między scenami
"""

import json
import httpx
import pytest
import pysubs2
from google import genai
from google.genai import types as genai_types

from avt_linter import EpisodeQualityGate
from profiler import EpisodeProfile, DramaticSequence
from scene_discourse import SceneDiscourseGraph
from series_memory import SeriesBible
from translator import (
    MultimodalTranslator,
    format_dry_telemetry_tag,
    _compute_effective_target_confidence,
    _append_phase2_genre_tone_rule,
)
from verifier import DialogueVerifier


def _make_mock_genai_client(handler) -> genai.Client:
    http_client = httpx.Client(transport=httpx.MockTransport(handler))
    c = genai.Client(api_key="mock_k0", http_options=genai_types.HttpOptions(httpx_client=http_client))
    if getattr(c._api_client, "_httpx_client", None) is not http_client:
        c._api_client._httpx_client = http_client
    return c


class _DummyPbar:
    def write(self, msg: str) -> None:
        pass

    def set_postfix_str(self, s: str) -> None:
        pass

    def refresh(self) -> None:
        pass


def _build_synthetic_bible(tmp_path) -> SeriesBible:
    sb = SeriesBible(anime_title="Seria Gamma", storage_dir=tmp_path)
    sb.data["characters"] = {
        "Dowódca_A": {
            "name": "Dowódca_A",
            "gender": "FEMALE",
            "grammatical_gender": "FEMININE",
            "confidence": 0.98,
            "priority": "P0",
            "has_verified_gender": True,
            "aliases": ["Dowódca_A"],
            "description": "kobieta (postać)",
            "entity_category": "ANTHROPONYM",
        },
        "Agent_A": {
            "name": "Agent_A",
            "gender": "MALE",
            "grammatical_gender": "MASCULINE",
            "confidence": 0.98,
            "priority": "P0",
            "has_verified_gender": True,
            "aliases": ["Agent_A"],
            "description": "mężczyzna (postać)",
            "entity_category": "ANTHROPONYM",
        },
        "Agent_B": {
            "name": "Agent_B",
            "gender": "FEMALE",
            "grammatical_gender": "FEMININE",
            "confidence": 0.98,
            "priority": "P0",
            "has_verified_gender": True,
            "aliases": ["Agent_B"],
            "description": "kobieta (postać)",
            "entity_category": "ANTHROPONYM",
        },
        "Oficer_C": {
            "name": "Oficer_C",
            "gender": "MALE",
            "grammatical_gender": "MASCULINE",
            "confidence": 0.98,
            "priority": "P0",
            "has_verified_gender": True,
            "aliases": ["Oficer_C"],
            "description": "mężczyzna (postać)",
            "entity_category": "ANTHROPONYM",
        },
        "Obserwator_D": {
            "name": "Obserwator_D",
            "gender": "FEMALE",
            "grammatical_gender": "FEMININE",
            "confidence": 0.98,
            "priority": "P0",
            "has_verified_gender": True,
            "aliases": ["Obserwator_D"],
            "description": "kobieta (postać)",
            "entity_category": "ANTHROPONYM",
        },
    }
    sb._rebuild_actor_aliases_index()
    return sb


def _make_prod_pass1_item(
    idx: int,
    en: str,
    pl: str,
    speaker_name: str = "Agent_A",
    start_ms: int = 1000,
    end_ms: int = 3000,
    calque_score: float = 0.0,
    is_sign: bool = False,
) -> dict:
    ev = pysubs2.SSAEvent(start=start_ms, end=end_ms, text=en, name=speaker_name, style="Default")
    return {
        "id": idx,
        "orig_idx": idx - 1,
        "event": ev,
        "style": "Default",
        "is_thought": False,
        "is_internal_monologue": False,
        "is_missing_translation": False,
        "is_blind_draft": False,
        "calque_score": calque_score,
        "duration_s": max(0.2, (end_ms - start_ms) / 1000.0),
        "time_gap_s": 0.0,
        "time_gap_ms": 0,
        "cps": 12.0,
        "start_ms": start_ms,
        "end_ms": end_ms,
        "en": en,
        "pl": pl,
        "prev_line_f1": "",
        "prev_line_en": "",
        "speaker_name": speaker_name,
        "speaker_gender": "mężczyzna",
        "speaker_confidence": 1.0,
        "addressee": None,
        "target_gender": None,
        "target_confidence": 1.0,
        "addressee_label": "",
        "telemetry_tag": f"[Mówca: {speaker_name} (MASCULINE)]",
        "declension_paradigms": [],
        "semiotic_layer": "",
        "screen_region": None,
        "visual_typesetting": None,
        "speaker_voice": "",
        "prosody": "",
        "audio_jp": "",
        "audio_alert": "",
        "ambiguity_note": "",
        "canonical_glossary_term": "",
        "relation_tag": "",
        "pragmatic_register": "",
        "visual_subtext": "",
        "literal_meaning": "",
        "cps_warning": "",
        "condensation_directive": "",
        "notes": "",
        "third_person_subject": "",
        "plural_group_gender": "AMBIGUOUS",
        "you_group_gender": "AMBIGUOUS",
        "semantic_anchor": "",
        "is_sign": is_sign,
        "visual_type": "Napis ekranowy" if is_sign else "Dialog",
        "visual_details": "",
        "is_song": False,
        "active_scene_tone": "",
    }


@pytest.mark.unit
def test_obs13a_local_polylogue_third_party_interjection_suppresses_false_addressee(tmp_path):
    """
    OBS-13a: W lokalnym polylogu (>= 3 mówców) krótkie 1-2-słowne wtrącenie osoby trzeciej
    (Oficer_C: 'Dowódca_A...') między kwestiami Dowódca_A nie może wywołać zgadywania
    prev_interlocutor ani wyciec jako 'Adresat: Oficer_C (MASCULINE)' w telemetrii.
    """
    sb = _build_synthetic_bible(tmp_path)
    tr = MultimodalTranslator(api_key="mock_k0", model="gemini-4-hydrogen", enable_verifier=False)
    tr.series_bible = sb
    tr.character_registry = {
        "Dowódca_A": "kobieta (postać)",
        "Agent_B": "kobieta (postać)",
        "Oficer_C": "mężczyzna (postać)",
    }

    events = [
        pysubs2.SSAEvent(start=10000, end=12200, name="Agent_B", text="Why did she ask us to stay?"),
        pysubs2.SSAEvent(start=12300, end=14600, name="Dowódca_A", text="Oh, did she explain the whole contract?"),
        pysubs2.SSAEvent(start=14900, end=16100, name="Oficer_C", text="Dowódca_A..."),
        pysubs2.SSAEvent(start=17200, end=21500, name="Dowódca_A", text="You would blame yourself if you knew our unit was dissolving."),
    ]
    batch_events = [(i, ev, ev.text, "") for i, ev in enumerate(events)]

    addr_cat, addr_lbl = tr._resolve_line_addressee(
        event=events[3],
        raw_phase1_addressee=None,
        batch_events=batch_events,
        event_idx=3,
        clean_text=events[3].text,
    )
    assert (addr_cat, addr_lbl) == (None, None)

    prompt = tr._prepare_batch_prompt(batch_events=batch_events, history_context=[])
    line4_block = prompt.split("Kwestia [ID: 4]")[1]
    assert "Adresat: Oficer_C" not in line4_block


@pytest.mark.unit
def test_obs13a_confirmed_ping_pong_in_polylogue_preserves_addressee_and_a3_tv(tmp_path):
    """
    OBS-13a + A-3: Gdy w scenie z >= 3 mówcami trwa potwierdzona wymiana dwugłosowa (ping-pong)
    między Agent_A i Agent_B, _resolve_line_addressee zachowuje adresata (pewność >= 0.90),
    a F1 wstrzykuje zarówno [Adresat: Agent_B (FEMININE)], jak i dyrektywę A-3 Rejestr T-V.
    """
    sb = _build_synthetic_bible(tmp_path)
    sb.data["relations"] = {
        "Agent_A -> Agent_B": "Zwrot: 'pani Agent_B / Agent_B' (oficjalna relacja służbowa)",
    }
    tr = MultimodalTranslator(api_key="mock_k0", model="gemini-4-hydrogen", enable_verifier=False)
    tr.series_bible = sb
    tr.character_registry = {
        "Agent_A": "mężczyzna (postać)",
        "Agent_B": "kobieta (postać)",
        "Oficer_C": "mężczyzna (postać)",
        "Obserwator_D": "kobieta (postać)",
    }

    events = [
        pysubs2.SSAEvent(start=1000, end=3000, name="Oficer_C", text="Watch the southern ridge."),
        pysubs2.SSAEvent(start=3100, end=5000, name="Obserwator_D", text="Sensors are calibrated."),
        pysubs2.SSAEvent(start=5200, end=7200, name="Agent_B", text="Have you checked the flight manifest yet?"),
        pysubs2.SSAEvent(start=7300, end=9300, name="Agent_A", text="Yes, there are two unscheduled deliveries."),
        pysubs2.SSAEvent(start=9400, end=11600, name="Agent_B", text="Should we intercept them before landing?"),
        pysubs2.SSAEvent(start=11700, end=14100, name="Agent_A", text="If I may suggest, let us hold position until dawn."),
    ]
    batch_events = [(i, ev, ev.text, "") for i, ev in enumerate(events)]

    addr_cat, addr_lbl = tr._resolve_line_addressee(
        event=events[5],
        raw_phase1_addressee=None,
        batch_events=batch_events,
        event_idx=5,
        clean_text=events[5].text,
    )
    assert addr_cat == "kobieta"
    assert addr_lbl == "Agent_B (Kobieta)"

    prompt = tr._prepare_batch_prompt(batch_events=batch_events, history_context=[])
    line6_block = prompt.split("Kwestia [ID: 6]")[1]
    assert "Adresat: Agent_B (FEMININE)" in line6_block
    assert "Rejestr T-V (Agent_A -> Agent_B): pan/pani" in line6_block


@pytest.mark.unit
def test_obs13a_f1_history_window_expands_to_6_and_8_lines_while_f2_keeps_cap_4():
    """
    OBS-13a: Rozszerzenie historii przeszłej w F1 do 6 linii w diadzie (<= 2 aktorów)
    oraz 8 linii w polylogu (>= 3 aktorów), przy zachowaniu limitu <= 4 linii w F2 DialogueVerifier.
    """
    tr = MultimodalTranslator(api_key="mock_k0", model="gemini-4-hydrogen", enable_verifier=True)
    hist_10 = [
        {
            "speaker": "Agent_A" if i % 2 == 0 else "Agent_B",
            "speaker_name": "Agent_A" if i % 2 == 0 else "Agent_B",
            "en": f"Historical statement {i}.",
            "pl": f"Historyczna wypowiedź {i}.",
            "is_thought": False,
        }
        for i in range(1, 11)
    ]

    dyad_batch = [
        (0, pysubs2.SSAEvent(start=20000, end=22000, name="Agent_A", text="Moving out now."), "Moving out now.", ""),
        (1, pysubs2.SSAEvent(start=22100, end=24000, name="Agent_B", text="Right behind you."), "Right behind you.", ""),
    ]
    prompt_dyad = tr._prepare_batch_prompt(batch_events=dyad_batch, history_context=hist_10)
    dyad_hist_lines = [l for l in prompt_dyad.splitlines() if "[Poprzednio]" in l or "[Początek wywodu" in l]
    assert len(dyad_hist_lines) == 6
    assert "Historyczna wypowiedź 5." in prompt_dyad
    assert "Historyczna wypowiedź 4." not in prompt_dyad

    poly_batch = dyad_batch + [
        (2, pysubs2.SSAEvent(start=24200, end=26000, name="Oficer_C", text="Hold the corridor."), "Hold the corridor.", ""),
    ]
    prompt_poly = tr._prepare_batch_prompt(batch_events=poly_batch, history_context=hist_10)
    poly_hist_lines = [l for l in prompt_poly.splitlines() if "[Poprzednio]" in l or "[Początek wywodu" in l]
    assert len(poly_hist_lines) == 8
    assert "Historyczna wypowiedź 3." in prompt_poly
    assert "Historyczna wypowiedź 2." not in prompt_poly

    verifier = DialogueVerifier(
        client=_make_mock_genai_client(lambda req: httpx.Response(200, json={})),
        model="gemini-4-hydrogen",
    )
    f2_prompt = verifier.verify_batch(
        batch_items=[{"id": 1, "en": "Moving out now.", "pl": "Ruszam.", "speaker_gender": "MASCULINE", "notes": ""}],
        history_context=hist_10,
        return_prompt=True,
    )
    f2_hist_lines = [l for l in f2_prompt.splitlines() if "[Poprzednio]" in l or "[Koniec poprzedniej]" in l]
    assert len(f2_hist_lines) <= 4
    assert "Historyczna wypowiedź 7." in f2_prompt
    assert "Historyczna wypowiedź 6." not in f2_prompt


@pytest.mark.unit
def test_obs13b_collective_chorus_blocks_high_f0_feminine_and_defaults_virile(tmp_path, monkeypatch):
    """
    OBS-13b: Etykiety chóralne/zbiorowe (BROTHERS, CROWD, Agent_A/Oficer_B) przy wysokim F0 (251 Hz)
    nie otrzymują indywidualnej płci FEMININE i ustawiają Grupa_1os_lm=VIRILE; pojedyncza postać
    z sufiksem technicznym (Agent_B/ID) zachowuje FEMININE, a potwierdzona grupa wyłącznie żeńska
    otrzymuje NON_VIRILE.
    """
    monkeypatch.setattr("time.sleep", lambda s: None)
    monkeypatch.setattr("client_factory.global_rate_limiter.acquire", lambda: None)
    monkeypatch.setattr("context_cache.ContextCacheManager.get_or_create_cache", lambda *a, **kw: "__IMPLICIT_CACHE_95__")

    sb = _build_synthetic_bible(tmp_path)
    sb.data["characters"]["SISTERS_TEAM"] = {
        "name": "SISTERS_TEAM",
        "gender": "FEMALE",
        "grammatical_gender": "FEMININE",
        "confidence": 0.98,
        "priority": "P0",
        "has_verified_gender": True,
        "aliases": ["SISTERS_TEAM"],
        "entity_category": "ANTHROPONYM",
    }
    sb.data["characters"]["SIÓSTR_KLAN"] = dict(sb.data["characters"]["SISTERS_TEAM"], name="SIÓSTR_KLAN", aliases=["SIÓSTR_KLAN"])
    sb._rebuild_actor_aliases_index()

    ev_brothers = pysubs2.SSAEvent(start=1000, end=2500, name="BROTHERS", text="Welcome back!")
    ev_crowd = pysubs2.SSAEvent(start=2600, end=4000, name="CROWD", text="Hurrah!")
    ev_mixed_slash = pysubs2.SSAEvent(start=4100, end=5600, name="Agent_A/Oficer_C", text="Watch out!")
    ev_fem_tech = pysubs2.SSAEvent(start=5700, end=7200, name="Agent_B/ID", text="Copy that.")
    ev_fem_pair = pysubs2.SSAEvent(start=7300, end=8800, name="Dowódca_A/Agent_B", text="We found it.")
    batch_events = [
        (0, ev_brothers, ev_brothers.text, ""),
        (1, ev_crowd, ev_crowd.text, ""),
        (2, ev_mixed_slash, ev_mixed_slash.text, ""),
        (3, ev_fem_tech, ev_fem_tech.text, ""),
        (4, ev_fem_pair, ev_fem_pair.text, ""),
    ]

    def handler(request: httpx.Request) -> httpx.Response:
        body = {
            "scene_diagnosis": None,
            "translations": [
                {"id": 1, "polish_text": "Wróciłeś!", "speaker_name": "BROTHERS"},
                {"id": 2, "polish_text": "Brawo!", "speaker_name": "CROWD"},
                {"id": 3, "polish_text": "Uwaga!", "speaker_name": "Agent_A/Oficer_C"},
                {"id": 4, "polish_text": "Przyjęłam.", "speaker_name": "Agent_B/ID"},
                {"id": 5, "polish_text": "Znalazłyśmy to.", "speaker_name": "Dowódca_A/Agent_B"},
            ],
            "characters_identified": [],
        }
        return httpx.Response(
            200,
            json={
                "candidates": [{"content": {"role": "model", "parts": [{"text": json.dumps(body)}]}}],
                "usageMetadata": {"promptTokenCount": 700, "cachedContentTokenCount": 0, "candidatesTokenCount": 90, "thoughtsTokenCount": 0},
            },
        )

    tr = MultimodalTranslator(api_key="mock_k0", model="gemini-4-hydrogen", enable_verifier=True)
    mock_c = _make_mock_genai_client(handler)
    tr.client_pool_f1.clients = [mock_c]
    tr.client_pool.clients = [mock_c]
    tr.client = mock_c
    tr.series_bible = sb
    tr.scene_is_female_only = True  # Nawet w scenie żeńskiej BROTHERS nie mogą dostać NON_VIRILE ani FEMININE
    tr.episode_scene_genders = {0: "kobieta", 1: "kobieta", 2: "kobieta", 3: "kobieta", 4: "kobieta"}
    tr.character_registry = {"Agent_B": "kobieta (postać)", "Dowódca_A": "kobieta (postać)"}

    speaker_tags = {
        1: "wysoki / sopran / 251 Hz (F0=251 Hz)",
        2: "wysoki / 248 Hz",
        3: "wysoki / 255 Hz",
        4: "sopran / 245 Hz",
        5: "sopran / 240 Hz",
    }

    prompt_f1 = tr._prepare_batch_prompt(batch_events=batch_events, history_context=[], speaker_tags=speaker_tags)
    block1 = prompt_f1.split("Kwestia [ID: 1]")[1].split("Kwestia [ID: 2]")[0]
    assert "Mówca: BROTHERS (FEMININE)" not in block1
    assert "BROTHERS (Kobieta)" not in block1
    assert "Grupa_1os_lm: VIRILE" in block1

    block4 = prompt_f1.split("Kwestia [ID: 4]")[1].split("Kwestia [ID: 5]")[0]
    assert "Mówca: Agent_B/ID (FEMININE)" in block4

    block5 = prompt_f1.split("Kwestia [ID: 5]")[1]
    assert "Grupa_1os_lm: NON_VIRILE" in block5

    p1 = tr._process_phase1_only(
        b_idx=0,
        batch=batch_events,
        untranslated_in_batch=batch_events,
        batches=[batch_events],
        video_path=None,
        is_ass=True,
        anime_meta=None,
        episode_profile=None,
        anime_context_str="",
        episode_profile_str="",
        series_bible_str="",
        manga_canon_str="",
        combined_glossary={},
        all_user_rules=[],
        translated_results={},
        history=[],
        pbar=_DummyPbar(),
    )
    items = p1["pass1_items"]
    assert items[0]["speaker_gender"] is None
    assert items[0]["speaker_confidence"] == 0.0
    assert items[0]["plural_group_gender"] == "VIRILE"
    assert "Mówca: BROTHERS (FEMININE)" not in items[0]["telemetry_tag"]
    assert "Grupa_1os_lm: VIRILE" in items[0]["telemetry_tag"]

    assert items[1]["plural_group_gender"] == "VIRILE"
    assert "FEMININE" not in items[1]["telemetry_tag"]
    assert items[2]["plural_group_gender"] == "VIRILE"
    assert "FEMININE" not in items[2]["telemetry_tag"]

    assert items[3]["speaker_gender"] == "kobieta"
    assert "FEMININE" in items[3]["telemetry_tag"]

    assert items[4]["speaker_gender"] is None
    assert items[4]["plural_group_gender"] == "NON_VIRILE"
    assert "Grupa_1os_lm: NON_VIRILE" in items[4]["telemetry_tag"]


@pytest.mark.unit
def test_obs13c_confidence_090_gate_preserves_backward_compat_080_and_propagates_real_conf(tmp_path, monkeypatch):
    """
    OBS-13c: format_dry_telemetry_tag zachowuje domyślny próg 0.80 (zgodność TEST 178/178),
    natomiast wywołania produkcyjne wymuszają próg 0.90 i propagują rzeczywistą pewność z eventu
    (0.85 zostaje wytłumione z telemetrii oraz notes F2; 0.95 zostaje zachowane).
    """
    monkeypatch.setattr("time.sleep", lambda s: None)
    monkeypatch.setattr("client_factory.global_rate_limiter.acquire", lambda: None)
    monkeypatch.setattr("context_cache.ContextCacheManager.get_or_create_cache", lambda *a, **kw: "__IMPLICIT_CACHE_95__")

    # 1. Zgodność wsteczna domyślnego progu 0.80 vs jawnego 0.90
    assert format_dry_telemetry_tag(target_gender="FEMININE", target_confidence=0.85) == "[Adresat: FEMININE]"
    assert format_dry_telemetry_tag(target_gender="FEMININE", target_confidence=0.85, target_min_confidence=0.90) == ""

    sb = _build_synthetic_bible(tmp_path)
    ev0 = pysubs2.SSAEvent(start=100, end=900, name="Agent_B", text="Did you inspect the perimeter?")
    ev1 = pysubs2.SSAEvent(start=1000, end=2500, name="Agent_A", text="Look at the northern ridge.")
    ev1.target_speaker = "Agent_B"
    ev1.target_confidence = 0.85  # niska pewność z polylogu (ma zostać wytłumiona w 12.2.0)

    ev2 = pysubs2.SSAEvent(start=2600, end=4200, name="Agent_A", text="Check the second gate now.")
    ev2.target_speaker = "Agent_B"
    ev2.target_confidence = 0.95  # wysoka pewność z diady

    assert _compute_effective_target_confidence(ev1, "kobieta", "Agent_B (Kobieta)") == pytest.approx(0.85)
    assert _compute_effective_target_confidence(ev2, "kobieta", "Agent_B (Kobieta)") == pytest.approx(0.95)

    batch_events = [(0, ev0, ev0.text, ""), (1, ev1, ev1.text, ""), (2, ev2, ev2.text, "")]

    def handler(request: httpx.Request) -> httpx.Response:
        body = {
            "scene_diagnosis": None,
            "translations": [
                {"id": 1, "polish_text": "Sprawdziłeś obwód?", "speaker_name": "Agent_B"},
                {"id": 2, "polish_text": "Spójrz na północną grań.", "speaker_name": "Agent_A"},
                {"id": 3, "polish_text": "Sprawdź teraz drugą bramę.", "speaker_name": "Agent_A"},
            ],
            "characters_identified": [],
        }
        return httpx.Response(
            200,
            json={
                "candidates": [{"content": {"role": "model", "parts": [{"text": json.dumps(body)}]}}],
                "usageMetadata": {"promptTokenCount": 600, "cachedContentTokenCount": 0, "candidatesTokenCount": 70, "thoughtsTokenCount": 0},
            },
        )

    tr = MultimodalTranslator(api_key="mock_k0", model="gemini-4-hydrogen", enable_verifier=True)
    mock_c = _make_mock_genai_client(handler)
    tr.client_pool_f1.clients = [mock_c]
    tr.client_pool.clients = [mock_c]
    tr.client = mock_c
    tr.series_bible = sb
    tr.character_registry = {"Agent_A": "mężczyzna (postać)", "Agent_B": "kobieta (postać)"}

    prompt = tr._prepare_batch_prompt(batch_events=batch_events, history_context=[])
    p_line1 = prompt.split("Kwestia [ID: 2]")[1].split("Kwestia [ID: 3]")[0]
    p_line2 = prompt.split("Kwestia [ID: 3]")[1]
    assert "Adresat:" not in p_line1
    assert "Adresat: Agent_B (FEMININE)" in p_line2

    p1 = tr._process_phase1_only(
        b_idx=0,
        batch=batch_events,
        untranslated_in_batch=batch_events,
        batches=[batch_events],
        video_path=None,
        is_ass=True,
        anime_meta=None,
        episode_profile=None,
        anime_context_str="",
        episode_profile_str="",
        series_bible_str="",
        manga_canon_str="",
        combined_glossary={},
        all_user_rules=[],
        translated_results={},
        history=[],
        pbar=_DummyPbar(),
    )
    _, it1, it2 = p1["pass1_items"]
    assert it1["target_confidence"] == pytest.approx(0.85)
    assert it1["addressee"] is None
    assert it1["addressee_label"] == ""
    assert "Adresat:" not in it1["telemetry_tag"]

    assert it2["target_confidence"] == pytest.approx(0.95)
    assert it2["addressee"] == "kobieta"
    assert "Adresat: Agent_B (FEMININE)" in it2["telemetry_tag"]


@pytest.mark.unit
def test_c1_f2_readonly_neighbors_attached_without_cot_escalation_and_respects_scene_cut():
    """
    C-1: Przy selekcji F2 wybrana linia (#10) otrzymuje w `notes` wyłącznie sąsiadów z tej samej
    sceny (#9), nie przekracza cięcia sceny DEF-02 przed #11 (4200 ms), renderuje się w prompcie F2
    oraz utrzymuje ekonomiczny budżet CoT 2048 (LOW).
    """
    tr = MultimodalTranslator(api_key="mock_k0", model="gemini-4-hydrogen", enable_verifier=True)

    pass1_items = []
    for i in range(1, 21):
        st = i * 4000
        en = st + 1500
        if i == 9:
            pass1_items.append(_make_prod_pass1_item(
                idx=9,
                en="Have we sealed the eastern vault?",
                pl="Zamknęliśmy już wschodni skarbiec?",
                speaker_name="Agent_B",
                start_ms=36500,
                end_ms=38000,
                calque_score=0.0,
            ))
        elif i == 10:
            pass1_items.append(_make_prod_pass1_item(
                idx=10,
                en="Let us make sure of the seals right now before leaving.",
                pl="Upewnijmy się natychmiast co do pieczęci przed odejściem.",
                speaker_name="Agent_A",
                start_ms=39000,
                end_ms=41000,
                calque_score=0.88,
            ))
        elif i == 11:
            pass1_items.append(_make_prod_pass1_item(
                idx=11,
                en="Next morning at the harbor.",
                pl="Następnego ranka w porcie.",
                speaker_name="Oficer_C",
                start_ms=45200,  # pauza 4200 ms >= 3500 ms -> cięcie sceny DEF-02
                end_ms=47000,
                calque_score=0.0,
            ))
        else:
            pass1_items.append(_make_prod_pass1_item(
                idx=i,
                en=f"Neutral control sentence number {i}.",
                pl=f"Neutralne zdanie kontrolne {i}.",
                speaker_name="Agent_A",
                start_ms=st,
                end_ms=en,
                calque_score=0.45 if (i <= 8 or i == 13) else 0.0,
            ))

    selected = tr._select_hydrogen_phase2_candidates(pass1_items, total_batches=6, episode_line_cap=115)
    sel_ids = {it["id"] for it in selected}
    assert 10 in sel_ids
    assert 9 not in sel_ids
    assert 11 not in sel_ids

    it10 = next(it for it in selected if it["id"] == 10)
    assert '[Poprzednia #9 (read-only, NIE zwracaj w JSON) Agent_B: "Zamknęliśmy już wschodni skarbiec?"]' in it10["notes"]
    assert "Następna #11" not in it10["notes"]
    assert not it10["audio_alert"]
    assert not it10["ambiguity_note"]
    assert tr.verifier.calculate_effective_budget(selected) == 2048

    verifier = DialogueVerifier(
        client=_make_mock_genai_client(lambda req: httpx.Response(200, json={})),
        model="gemini-4-hydrogen",
    )
    f2_prompt = verifier.verify_batch(batch_items=selected, return_prompt=True)
    assert "Poprzednia #9 (read-only, NIE zwracaj w JSON) Agent_B" in f2_prompt


@pytest.mark.unit
def test_c2_genre_adaptive_f2_prompt_removes_teenager_hardcode_and_injects_era_tone():
    """
    C-2 (Z16-amendment #16): Prompt użytkownika DialogueVerifier nie zawiera sztywnej frazy
    o polskich nastolatkach, używa neutralnej instrukcji gatunkowej, a _append_phase2_genre_tone_rule
    wstrzykuje epokę i ton sceny bez naruszania system_prompt.
    """
    verifier = DialogueVerifier(
        client=_make_mock_genai_client(lambda req: httpx.Response(200, json={})),
        model="gemini-4-hydrogen",
    )
    sys_prompt_before = verifier.system_prompt
    f2_prompt = verifier.verify_batch(
        batch_items=[{"id": 1, "en": "Hail the duke.", "pl": "Witaj, książę.", "speaker_gender": "MASCULINE", "notes": ""}],
        return_prompt=True,
    )
    assert "nastolatk" not in f2_prompt.lower()
    assert "dostosowanym do gatunku, epoki i charakteru postaci" in f2_prompt
    assert verifier.system_prompt == sys_prompt_before

    hist_profile = EpisodeProfile(
        setting_and_era="Późne średniowiecze, szlachta i zakon rycerski",
        dramatic_sequences=[
            DramaticSequence(
                sequence_name="Rada zamkowa",
                time_range="00:00 - 03:00",
                dramatic_summary="Spór o honor rodu.",
                dominant_tone="surowy dramat dworski",
            )
        ],
    )
    rules_hist = _append_phase2_genre_tone_rule(
        "REJESTR: zachowaj dystans.",
        episode_profile=hist_profile,
        active_sequence_str="Rada zamkowa | Ton: surowy dramat dworski | Spór",
    )
    assert "TON GATUNKU I EPOKI:" in rules_hist
    assert "Późne średniowiecze, szlachta i zakon rycerski" in rules_hist
    assert "ton sceny: surowy dramat dworski" in rules_hist

    # Z2: przy braku metadanych epoki i tonu reguła pozostaje nienaruszona
    assert _append_phase2_genre_tone_rule("REJESTR: zachowaj dystans.", episode_profile=None, active_sequence_str="") == "REJESTR: zachowaj dystans."


@pytest.mark.unit
def test_a2_filar_clxxi_accepts_thousand_separators_and_military_time_while_catching_real_mutations():
    """
    A-2 (Z16-amendment #16): EpisodeQualityGate (Filar CLXXI) nie zgłasza fałszywych alarmów
    dla angielskich separatorów tysięcy ('1,500' -> '1500' / '1 500') ani czasu wojskowego
    ('1420 Hours' -> '14:20'), ale nadal wyłapuje realne mutacje liczb ('500' -> '50').
    """
    subs = pysubs2.SSAFile()

    ev1 = pysubs2.SSAEvent(start=1000, end=3000, text="Oddalone o 1500 metrów stąd.")
    ev1.source_en = "Located about 1,500 meters away."

    ev2 = pysubs2.SSAEvent(start=3500, end=5500, text="Kosztuje to 1 250 000 kredytów.")
    ev2.source_en = "It costs 1,250,000 credits."

    ev3 = pysubs2.SSAEvent(start=6000, end=8500, text="Tego dnia o 14:20 w bazie lotniczej.")
    ev3.source_en = "That Day at 1420 Hours, A Certain Airfield."

    ev4 = pysubs2.SSAEvent(start=9000, end=11000, text="Pożyczę 50 monet.")
    ev4.source_en = "I'll borrow 500 coins."

    subs.events.extend([ev1, ev2, ev3, ev4])
    _, fixes = EpisodeQualityGate.audit_and_fix_entire_episode(subs, strict_positive_domain=True)

    clxxi_fixes = [f for f in fixes if "Filar CLXXI" in f]
    assert len(clxxi_fixes) == 1
    assert "Linia #4" in clxxi_fixes[0]
    assert "500" in clxxi_fixes[0] and "50" in clxxi_fixes[0]


@pytest.mark.unit
def test_12_2_0_def02_regression_5_scene_cuts_and_sasaki_pattern(tmp_path):
    """
    Regresja DEF-02 po zmianach 12.2.0: 5 geometrii cięć z 11.2.25 (#80, #189, #255, #264 cross_batch, #293)
    oraz pauza międzyscenowa 5000 ms zachowują pełny reset UNSPECIFIED i zero wycieku Adresat.
    """
    sb = _build_synthetic_bible(tmp_path)
    cases = [
        {"id": "#80", "cuts": [388346, 390849], "prev": pysubs2.SSAEvent(start=383600, end=386320, name="Dowódca_A", text="Be careful."), "curr": pysubs2.SSAEvent(start=391130, end=393330, name="Agent_A", text="Situation inside."), "cross": False},
        {"id": "#189", "cuts": [832790], "prev": pysubs2.SSAEvent(start=830100, end=831840, name="Oficer_C", text="Stay there."), "curr": pysubs2.SSAEvent(start=835020, end=837040, name="Agent_B", text="What was that?"), "cross": False},
        {"id": "#255", "cuts": [1042250], "prev": pysubs2.SSAEvent(start=1036820, end=1041260, style="Main - Italics", name="Obserwator_D", text="I knew it."), "curr": pysubs2.SSAEvent(start=1043980, end=1046760, name="Oficer_C", text="State your business."), "cross": False},
        {"id": "#264", "cuts": [1072488, 1073990], "prev": pysubs2.SSAEvent(start=1068830, end=1072460, name="Dowódca_A", text="Leave it to me."), "curr": pysubs2.SSAEvent(start=1077090, end=1078640, name="Agent_A", text="Nothing moved."), "cross": True},
        {"id": "#293", "cuts": [1177510], "prev": pysubs2.SSAEvent(start=1172560, end=1176840, style="Main - Italics", name="Agent_B", text="Long ago."), "curr": pysubs2.SSAEvent(start=1180240, end=1181740, name="Agent_A", text="Outer gate open."), "cross": False},
        {"id": "#163->164", "cuts": [], "prev": pysubs2.SSAEvent(start=700000, end=703000, name="Agent_A", text="Report later."), "curr": pysubs2.SSAEvent(start=708000, end=710000, name="Agent_B", text="Starting debrief."), "cross": False},
    ]

    for c in cases:
        tr = MultimodalTranslator(api_key="mock_k0", model="gemini-4-hydrogen", enable_verifier=False)
        tr.series_bible = sb
        tr.scene_cuts_ms = list(c["cuts"])
        evs = [c["prev"], c["curr"]]
        SceneDiscourseGraph.build_discourse_topology(evs, series_bible=sb, scene_boundaries=c["cuts"])
        assert getattr(c["curr"], "target_speaker", None) == "UNSPECIFIED", c["id"]

        if c["cross"]:
            batch_events = [(0, c["curr"], c["curr"].text, "")]
            idx = 0
            lh = [{"en": c["prev"].text, "pl": "Poprzednia.", "speaker": c["prev"].name, "speaker_gender": "kobieta", "is_thought": False, "start_ms": c["prev"].start, "end_ms": c["prev"].end}]
        else:
            batch_events = [(0, c["prev"], c["prev"].text, ""), (1, c["curr"], c["curr"].text, "")]
            idx = 1
            lh = None

        addr_cat, addr_lbl = tr._resolve_line_addressee(
            event=c["curr"],
            raw_phase1_addressee=None,
            batch_events=batch_events,
            event_idx=idx,
            clean_text=c["curr"].text,
            lookback_history=lh,
        )
        assert (addr_cat, addr_lbl) == (None, None), c["id"]
        eff_conf = _compute_effective_target_confidence(c["curr"], addr_cat, addr_lbl)
        assert eff_conf == 0.0
        tag = format_dry_telemetry_tag(
            speaker_gender="MASCULINE",
            speaker_confidence=1.0,
            target_gender=None,
            target_confidence=eff_conf,
            speaker_name=c["curr"].name,
            target_min_confidence=0.90,
        )
        assert "Adresat:" not in tag
