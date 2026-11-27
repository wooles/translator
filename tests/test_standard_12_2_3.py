# -*- coding: utf-8 -*-
"""
Standard 12.2.3 Regression Suite (Q1 + Q3 + Q4 + Q2 Phase 1 Opt-In Flex — 0.00 PLN, 0 B diff Z16).
100% Z1-pure synthetic test suite operating on real production classes & functions.
"""

import json
import time
from pathlib import Path
from types import SimpleNamespace

import httpx
import pysubs2
import pytest
from PIL import Image
from google import genai
from google.genai import types as genai_types

import model_resolver
import series_memory
import sign_detector
from client_factory import MultiKeyClientPool
from pipeline_logger import EpisodeFlightRecorder
from profiler import EpisodeProfile, EpisodeProfiler
from series_memory import SeriesBible
from sign_detector import DetectedSign, VisualSignDetector
from translator import (
    BatchTranslationResponse,
    LineTranslation,
    MultimodalTranslator,
    SceneDiagnosis,
    _compute_adaptive_f2_episode_cap,
)
from verifier import RefinedBatchResponse, RefinedLine


def _make_mock_genai_client(handler) -> genai.Client:
    http_client = httpx.Client(transport=httpx.MockTransport(handler))
    client = genai.Client(
        api_key="mock_k0",
        http_options=genai_types.HttpOptions(httpx_client=http_client),
    )
    if getattr(client._api_client, "_httpx_client", None) is not http_client:
        client._api_client._httpx_client = http_client
    return client


class _DummyPbar:
    def write(self, msg: str) -> None:
        pass

    def set_postfix_str(self, s: str) -> None:
        pass

    def update(self, n: int = 1) -> None:
        pass

    def refresh(self) -> None:
        pass


def _make_translator(tmp_path: Path, handler) -> MultimodalTranslator:
    tr = MultimodalTranslator(api_key="mock_k0", model="gemini-4-hydrogen", enable_verifier=True)
    mock_c = _make_mock_genai_client(handler)
    tr.client_pool_f1.clients = [mock_c]
    tr.client_pool.clients = [mock_c]
    tr.client = mock_c
    tr.trace_dir = str(tmp_path)
    tr.series_bible = SeriesBible("SyntheticSeries1223", storage_dir=tmp_path)
    if hasattr(tr, "verifier") and tr.verifier is not None:
        tr.verifier.client_pool.clients = [mock_c]
        tr.verifier.client = mock_c
    return tr


# ------------------------------------------------------------------------------
# Q1: Adaptive F2 episode cap scaling & short episode invariance
# ------------------------------------------------------------------------------
@pytest.mark.unit
def test_q1_adaptive_f2_episode_cap_scaling_and_short_episode_invariance(tmp_path: Path, monkeypatch):
    # 1. Pure boundary & monotonicity contract
    assert _compute_adaptive_f2_episode_cap(None) == 115
    assert _compute_adaptive_f2_episode_cap(0) == 115
    assert _compute_adaptive_f2_episode_cap(-12) == 115
    assert _compute_adaptive_f2_episode_cap(180) == 115
    assert _compute_adaptive_f2_episode_cap(200) == 115
    assert _compute_adaptive_f2_episode_cap(359) == 115
    assert _compute_adaptive_f2_episode_cap(360) == 115

    cap_450 = _compute_adaptive_f2_episode_cap(450)
    assert 115 < cap_450 < 170
    assert cap_450 == 144

    assert _compute_adaptive_f2_episode_cap(532) == 170
    assert _compute_adaptive_f2_episode_cap(580) == 170
    assert _compute_adaptive_f2_episode_cap(950) == 170

    # Default parameter backward compatibility on _select_hydrogen_phase2_candidates
    many_scored = [
        {
            "id": i,
            "orig_idx": i,
            "start_ms": i * 2000,
            "end_ms": i * 2000 + 1200,
            "speaker": f"spk_{i}",
            "en": "We have to move immediately.",
            "pl": "Musimy ruszać w tej chwili.",
            "speaker_confidence": 0.75,
            "target_confidence": 1.0,
            "ambiguity_note": "sprawdź kontekst",
        }
        for i in range(1, 201)
    ]

    recorded_f2_ids = []

    def _f2_handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content.decode("utf-8"))
        # Echo RefinedLine for every line mentioned in prompt
        # Use shared pass items parsed simply by returning empty corrections (original preserved)
        return httpx.Response(
            200,
            json={
                "candidates": [
                    {
                        "content": {
                            "role": "model",
                            "parts": [{"text": RefinedBatchResponse(lines=[]).model_dump_json()}],
                        }
                    }
                ],
                "usageMetadata": {"promptTokenCount": 300, "cachedContentTokenCount": 0, "candidatesTokenCount": 20},
            },
        )

    tr = _make_translator(tmp_path, _f2_handler)
    # Default cap in _select_hydrogen_phase2_candidates (total_batches=1, len=400 -> max 200 by 50%, capped at 115)
    dup_400 = [dict(it, id=idx + 1, orig_idx=idx + 1) for idx, it in enumerate(many_scored + many_scored)]
    sel_default = tr._select_hydrogen_phase2_candidates(dup_400, total_batches=1)
    assert len(sel_default) == 115

    # 2. End-to-end _process_phase2_only wiring: total_lines=200 -> 115 vs total_lines=580 -> 170
    monkeypatch.setattr(tr.verifier, "model", "gemini-4-hydrogen")
    monkeypatch.setattr(tr.verifier, "system_prompt", "lean prompt")
    original_select = tr._select_hydrogen_phase2_candidates

    def _spy_select(pass1_items, total_batches=6, episode_line_cap=115):
        res = original_select(pass1_items, total_batches=total_batches, episode_line_cap=episode_line_cap)
        recorded_f2_ids.append((episode_line_cap, len(res)))
        return res

    monkeypatch.setattr(tr, "_select_hydrogen_phase2_candidates", _spy_select)

    base_p1 = {
        "b_idx": 0,
        "pass1_items": dup_400,
        "untranslated_in_batch": [(it["id"], pysubs2.SSAEvent(start=0, end=1000, text=it["en"]), it["en"], "") for it in dup_400],
        "total_batches": 1,
        "is_ass": True,
        "pbar": _DummyPbar(),
    }

    monkeypatch.setenv("AVT_ALLOW_UNCACHED_BILLING", "1")
    tr._process_phase2_only(dict(base_p1, total_lines=200))
    tr._process_phase2_only(dict(base_p1, total_lines=580))

    assert recorded_f2_ids == [(115, 115), (170, 170)]

    # 3. Verify _process_phase1_only stores total_lines into phase1_data
    def _p1_handler(request: httpx.Request) -> httpx.Response:
        resp_obj = BatchTranslationResponse(
            scene_diagnosis=SceneDiagnosis(
                dramatic_context="Syntetyczna scena",
                dialogue_flow="Dialog",
                audio_intent_check="Spójne",
                dominant_tone="Neutralny",
            ),
            translations=[LineTranslation(id=1, polish_text="Idziemy.", speaker_gender="MALE", speaker_name="mowca_a")],
        )
        return httpx.Response(
            200,
            json={
                "candidates": [{"content": {"role": "model", "parts": [{"text": resp_obj.model_dump_json()}]}}],
                "usageMetadata": {"promptTokenCount": 400, "cachedContentTokenCount": 0, "candidatesTokenCount": 40},
            },
        )

    tr_p1 = _make_translator(tmp_path, _p1_handler)
    tr_p1.system_prompt = "lean"
    monkeypatch.setenv("AVT_ALLOW_UNCACHED_BILLING", "1")
    ev1 = pysubs2.SSAEvent(start=0, end=1200, name="mowca_a", text="Let's go.")
    fake_batches = [[(i + 1, ev1, "Let's go.", "")] for i in range(12)]
    p1_out = tr_p1._process_phase1_only(
        b_idx=0,
        batch=[(1, ev1, "Let's go.", "")],
        untranslated_in_batch=[(1, ev1, "Let's go.", "")],
        batches=fake_batches,
        video_path=None,
        is_ass=True,
        anime_meta={},
        episode_profile=None,
        anime_context_str="",
        episode_profile_str="",
        series_bible_str="",
        manga_canon_str="",
        combined_glossary={},
        all_user_rules=[],
        history=[],
        pbar=_DummyPbar(),
        translated_results={},
    )
    assert p1_out["total_lines"] == 12


# ------------------------------------------------------------------------------
# Q3: Extreme CPS > 25 priority boost (+60) & bypass of trivial_short penalty
# ------------------------------------------------------------------------------
@pytest.mark.unit
def test_q3_extreme_cps_above_25_gets_plus60_and_bypasses_trivial_short(tmp_path: Path):
    # Dialogue with 24 chars in 0.6s -> CPS = 40.0 > 25.0, <= 5 words & <= 25 chars (normally trivial short!)
    high_cps_item = {
        "id": 10,
        "orig_idx": 10,
        "start_ms": 1000,
        "end_ms": 1600,
        "speaker": "spk_a",
        "en": "Run away right now!",
        "pl": "Uciekaj stąd natychmiast",  # 24 chars -> 24 / 0.6 = 40.0 CPS, 3 words
        "is_sign": False,
        "speaker_confidence": 1.0,
        "target_confidence": 1.0,
    }
    sc_hi, crit_hi, reasons_hi = MultimodalTranslator._score_phase2_editorial_risk_detailed(high_cps_item)
    assert (sc_hi, crit_hi) == MultimodalTranslator._score_phase2_editorial_risk(high_cps_item)
    assert "cps_extreme:+60" in reasons_hi
    assert not any(r.startswith("trivial_short") for r in reasons_hi)
    assert sc_hi >= 60

    # Dialogue with CPS <= 25.0 (24 chars in 1.0s = 24.0 CPS) -> NO cps_extreme:+60
    normal_cps_item = dict(high_cps_item, id=11, orig_idx=11, start_ms=2000, end_ms=3000)
    sc_norm, _, reasons_norm = MultimodalTranslator._score_phase2_editorial_risk_detailed(normal_cps_item)
    assert "cps_extreme:+60" not in reasons_norm
    assert sc_norm == 0

    # Sign item with > 25 CPS -> excluded (signs follow different visual rules)
    sign_cps_item = dict(high_cps_item, id=12, orig_idx=12, is_sign=True)
    sc_sign, _, reasons_sign = MultimodalTranslator._score_phase2_editorial_risk_detailed(sign_cps_item)
    assert "cps_extreme:+60" not in reasons_sign
    assert sc_sign == 0

    # Verify high_cps_item wins F2 slot over low-risk candidates in selector
    tr = _make_translator(tmp_path, lambda req: httpx.Response(200, json={}))
    batch_items = [dict(high_cps_item, id=1, orig_idx=1)]
    for i in range(2, 16):
        batch_items.append({
            "id": i,
            "orig_idx": i,
            "start_ms": i * 5000,
            "end_ms": i * 5000 + 2500,
            "speaker": f"spk_{i}",
            "en": "I understand the plan.",
            "pl": "Rozumiem cały ten plan.",
            "relation_tag": "ally",
            "speaker_confidence": 1.0,
            "target_confidence": 1.0,
        })
    selected = tr._select_hydrogen_phase2_candidates(batch_items, total_batches=6, episode_line_cap=48)
    selected_ids = {it["id"] for it in selected}
    assert 1 in selected_ids


# ------------------------------------------------------------------------------
# Q4: OBS-18 actorless scene-cut lowercase guard
# ------------------------------------------------------------------------------
@pytest.mark.unit
def test_q4_obs18_actorless_scene_cut_lowercase_guard():
    # Known different speakers with tiny gap -> triggers lowercase guard
    assert MultimodalTranslator._is_speaker_change_lowercase(
        {"speaker": "mowca_a", "start_ms": 1000, "end_ms": 2000, "pl": "Gotowe."},
        {"speaker": "mowca_b", "start_ms": 2100, "end_ms": 3000, "pl": "tak, ruszajmy."},
    ) is True

    # Known SAME speaker -> does not trigger on short gap
    assert MultimodalTranslator._is_speaker_change_lowercase(
        {"speaker": "mowca_a", "start_ms": 1000, "end_ms": 2000, "pl": "Chwila..."},
        {"speaker": "mowca_a", "start_ms": 2100, "end_ms": 3000, "pl": "nie jestem pewien."},
    ) is False

    # Unknown / missing actors ("", "unknown", "postać", "/"):
    # - short gap (< 3500 ms) -> False (legitimate continuation)
    # - scene-cut gap (>= 3500 ms) + lowercase start -> True (Q4 OBS-18 guard!)
    # - scene-cut gap (>= 3500 ms) + uppercase start -> False (already clean)
    for unk_label in ("", "unknown", "/", "postać", "Postać"):
        prev_u = {"speaker": unk_label, "start_ms": 1000, "end_ms": 2000, "pl": "Idziemy dalej."}
        assert MultimodalTranslator._is_speaker_change_lowercase(
            prev_u,
            {"speaker": unk_label, "start_ms": 2500, "end_ms": 3800, "pl": "wciąż czekamy."},
        ) is False
        assert MultimodalTranslator._is_speaker_change_lowercase(
            prev_u,
            {"speaker": unk_label, "start_ms": 5500, "end_ms": 6800, "pl": "wciąż czekamy."},
        ) is True
        assert MultimodalTranslator._is_speaker_change_lowercase(
            prev_u,
            {"speaker": unk_label, "start_ms": 5500, "end_ms": 6800, "pl": "Wciąż czekamy."},
        ) is False

    # ASS tag masking + ellipsis immunity preserved
    assert MultimodalTranslator._is_speaker_change_lowercase(
        {"speaker": "", "start_ms": 1000, "end_ms": 2000, "pl": "Koniec sceny."},
        {"speaker": "", "start_ms": 7000, "end_ms": 8000, "pl": r"{\i1}nowe otwarcie."},
    ) is True
    assert MultimodalTranslator._is_speaker_change_lowercase(
        {"speaker": "", "start_ms": 1000, "end_ms": 2000, "pl": "Zawieszenie..."},
        {"speaker": "", "start_ms": 7000, "end_ms": 8000, "pl": "...dalszy ciąg."},
    ) is False


# ------------------------------------------------------------------------------
# Q2 (Unit): Opt-in Flex config resolver, default Standard & response header parser
# ------------------------------------------------------------------------------
@pytest.mark.unit
def test_q2_flex_opt_in_default_standard_and_config_application(monkeypatch):
    # Default MUST remain 'standard' when AVT_SERVICE_TIER is unset or invalid
    monkeypatch.delenv("AVT_SERVICE_TIER", raising=False)
    assert model_resolver.resolve_service_tier() == "standard"

    monkeypatch.setenv("AVT_SERVICE_TIER", "unexpected_value")
    assert model_resolver.resolve_service_tier() == "standard"

    monkeypatch.setenv("AVT_SERVICE_TIER", " FLEX ")
    assert model_resolver.resolve_service_tier() == "flex"
    assert model_resolver.resolve_service_tier("standard") == "standard"

    # apply_service_tier_to_config under 'standard' leaves config untouched
    base_cfg = {"temperature": 0.2, "thinking_config": genai_types.ThinkingConfig(thinking_budget=0)}
    std_cfg = model_resolver.apply_service_tier_to_config(base_cfg, "standard", "gemini-4-hydrogen")
    assert "service_tier" not in std_cfg
    assert "http_options" not in std_cfg

    # apply_service_tier_to_config under 'flex' sets both SDK service_tier & HTTP header while preserving existing headers
    existing_http_cfg = {"http_options": {"headers": {"X-Custom": "alpha"}}}
    flex_cfg = model_resolver.apply_service_tier_to_config(existing_http_cfg, "flex", "gemini-4-hydrogen")
    assert flex_cfg["service_tier"] == "flex"
    assert flex_cfg["http_options"].headers["X-Gemini-Service-Tier"] == "flex"
    assert flex_cfg["http_options"].headers["X-Custom"] == "alpha"

    # Validate against real installed google-genai GenerateContentConfig model
    sdk_cfg = genai_types.GenerateContentConfig(**flex_cfg)
    assert sdk_cfg.service_tier == genai_types.ServiceTier.FLEX
    assert sdk_cfg.http_options.headers["X-Gemini-Service-Tier"] == "flex"

    # Case-insensitive response header extraction
    fake_resp = SimpleNamespace(
        sdk_http_response=SimpleNamespace(headers={"Content-Type": "application/json", "x-gemini-service-tier": "flex"})
    )
    assert model_resolver.extract_response_service_tier_header(fake_resp) == "flex"
    assert model_resolver.extract_response_service_tier_header(SimpleNamespace()) is None


# ------------------------------------------------------------------------------
# Q2 (F1 Runtime): 2x 503 in Flex falls back to Standard on SAME Hydrogen model + CLI meta
# ------------------------------------------------------------------------------
@pytest.mark.unit
def test_q2_flex_f1_two_503_fallback_to_standard_same_hydrogen_model_and_cli_meta(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(time, "sleep", lambda *a, **kw: None)
    monkeypatch.setenv("AVT_SERVICE_TIER", "flex")

    seen_requests = []
    call_counter = {"n": 0}
    ok_resp = BatchTranslationResponse(
        scene_diagnosis=SceneDiagnosis(
            dramatic_context="Syntetyczna scena F1",
            dialogue_flow="Wymiana zdań",
            audio_intent_check="Spójne",
            dominant_tone="Neutralny",
        ),
        translations=[LineTranslation(id=1, polish_text="Gotowe.", speaker_gender="UNKNOWN", speaker_name="")],
    ).model_dump_json()

    def _flex_fallback_handler(request: httpx.Request) -> httpx.Response:
        if request.method == "GET":
            return httpx.Response(200, json={"models": []})
        call_counter["n"] += 1
        body = json.loads(request.content.decode("utf-8"))
        seen_requests.append(
            {
                "url": str(request.url),
                "header_tier": request.headers.get("X-Gemini-Service-Tier"),
                "body_tier": body.get("serviceTier") or body.get("service_tier"),
            }
        )
        if call_counter["n"] <= 2:
            return httpx.Response(
                503,
                json={"error": {"code": 503, "message": "Service Unavailable (flex overload)", "status": "UNAVAILABLE"}},
            )
        return httpx.Response(
            200,
            headers={"X-Gemini-Service-Tier": "standard"},
            json={
                "candidates": [{"content": {"role": "model", "parts": [{"text": ok_resp}]}}],
                "usageMetadata": {
                    "promptTokenCount": 600,
                    "cachedContentTokenCount": 0,
                    "candidatesTokenCount": 50,
                    "thoughtsTokenCount": 12,
                },
            },
        )

    tr = _make_translator(tmp_path, _flex_fallback_handler)
    parsed = tr._call_gemini_with_retry(["Przetłumacz: Ready."], BatchTranslationResponse, batch_idx=0)
    assert isinstance(parsed, BatchTranslationResponse)
    assert len(seen_requests) == 3

    # All 3 attempts MUST stay on gemini-4-hydrogen (zero Flash downgrade during Flex fallback!)
    for rec in seen_requests:
        assert "gemini-4-hydrogen" in rec["url"]
        assert "flash" not in rec["url"].lower()

    # First 2 attempts used Flex; 3rd switched to Standard
    assert seen_requests[0]["header_tier"] == "flex"
    assert seen_requests[1]["header_tier"] == "flex"
    assert str(seen_requests[0]["body_tier"]).lower() == "flex"
    assert str(seen_requests[1]["body_tier"]).lower() == "flex"
    assert seen_requests[2]["header_tier"] is None
    assert seen_requests[2]["body_tier"] is None

    usage = tr._thread_local.last_batch_token_usage
    assert usage["service_tier"] == "standard"
    assert usage["response_service_tier_header"] == "standard"

    # End-to-end translate_file cli_init runtime_meta["service_tier"] == "flex" + phase1_batch token_usage
    happy_headers = []

    def _happy_flex_handler(request: httpx.Request) -> httpx.Response:
        if request.method == "GET":
            return httpx.Response(200, json={"models": []})
        happy_headers.append(request.headers.get("X-Gemini-Service-Tier"))
        return httpx.Response(
            200,
            headers={"X-Gemini-Service-Tier": "flex"},
            json={
                "candidates": [{"content": {"role": "model", "parts": [{"text": ok_resp}]}}],
                "usageMetadata": {"promptTokenCount": 512, "cachedContentTokenCount": 0, "candidatesTokenCount": 44},
            },
        )

    tr2 = _make_translator(tmp_path, _happy_flex_handler)
    tr2.enable_verifier = False
    tr2.verifier = None
    tr2.system_prompt = "lean"
    monkeypatch.setenv("AVT_ALLOW_UNCACHED_BILLING", "1")
    monkeypatch.setenv("AVT_CONSOLIDATE_F2", "0")
    monkeypatch.setattr("translator.get_anime_context", lambda *a, **kw: {})
    monkeypatch.setattr(tr2.manga_canon, "get_or_discover_canon", lambda *a, **kw: None)
    monkeypatch.setattr(tr2.profiler, "profile_episode", lambda *a, **kw: None)
    monkeypatch.setattr(
        series_memory,
        "SeriesBible",
        lambda *a, **kw: SeriesBible(*a, storage_dir=tmp_path, **kw),
    )

    ass_in = tmp_path / "syn_q2_ep01.ass"
    subs = pysubs2.SSAFile()
    subs.events.append(pysubs2.SSAEvent(start=0, end=1000, name="mowca_a", text="Ready."))
    subs.save(str(ass_in))

    tr2.translate_file(str(ass_in), output_path=str(tmp_path / "out_q2.ass"))
    assert "flex" in happy_headers

    jsonl_path = Path(tr2.flight_recorder.jsonl_path)
    events = [json.loads(line) for line in jsonl_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    cli_events = [e for e in events if e["stage"] == "cli_init"]
    assert cli_events and cli_events[0]["payload"]["runtime_meta"]["service_tier"] == "flex"
    p1_events = [e for e in events if e["stage"] == "phase1_batch"]
    assert p1_events
    assert p1_events[0]["payload"]["token_usage"]["service_tier"] == "flex"
    assert p1_events[0]["payload"]["token_usage"]["response_service_tier_header"] == "flex"


# ------------------------------------------------------------------------------
# Q2 (Profiler + VisualSignDetector): Respect default 'standard', opt-in 'flex', & 2x 503 fallback
# ------------------------------------------------------------------------------
@pytest.mark.unit
def test_q2_flex_profiler_and_sign_detector_respect_opt_in_and_503_fallback(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(time, "sleep", lambda *a, **kw: None)

    # 1. Profiler under default 'standard' vs 'flex' + 2x 503 fallback
    prof_tiers_std = []

    def _prof_std_handler(request: httpx.Request) -> httpx.Response:
        prof_tiers_std.append(request.headers.get("X-Gemini-Service-Tier"))
        return httpx.Response(
            200,
            json={
                "candidates": [
                    {
                        "content": {
                            "role": "model",
                            "parts": [{"text": EpisodeProfile(episode_summary="Syntetyczny profil").model_dump_json()}],
                        }
                    }
                ],
                "usageMetadata": {"promptTokenCount": 200, "cachedContentTokenCount": 0, "candidatesTokenCount": 30},
            },
        )

    monkeypatch.delenv("AVT_SERVICE_TIER", raising=False)
    std_pool = MultiKeyClientPool(raw_keys="mock_k0")
    std_pool.clients = [_make_mock_genai_client(_prof_std_handler)]
    prof_std = EpisodeProfiler(client=std_pool, model="gemini-4-hydrogen")
    res_std = prof_std.profile_episode("1 [mowca_a]: Hello there.")
    assert isinstance(res_std, EpisodeProfile)
    assert prof_tiers_std == [None]

    prof_calls = []
    prof_n = {"i": 0}

    def _prof_flex_handler(request: httpx.Request) -> httpx.Response:
        prof_n["i"] += 1
        body = json.loads(request.content.decode("utf-8"))
        prof_calls.append(
            {
                "url": str(request.url),
                "header": request.headers.get("X-Gemini-Service-Tier"),
                "body": body.get("serviceTier") or body.get("service_tier"),
            }
        )
        if prof_n["i"] <= 2:
            return httpx.Response(
                503,
                json={"error": {"code": 503, "message": "503 Unavailable", "status": "UNAVAILABLE"}},
            )
        return httpx.Response(
            200,
            json={
                "candidates": [
                    {
                        "content": {
                            "role": "model",
                            "parts": [{"text": EpisodeProfile(episode_summary="Po fallbacku standard").model_dump_json()}],
                        }
                    }
                ],
                "usageMetadata": {"promptTokenCount": 200, "cachedContentTokenCount": 0, "candidatesTokenCount": 30},
            },
        )

    monkeypatch.setenv("AVT_SERVICE_TIER", "flex")
    flex_pool = MultiKeyClientPool(raw_keys="mock_k0")
    flex_pool.clients = [_make_mock_genai_client(_prof_flex_handler)]
    prof_flex = EpisodeProfiler(client=flex_pool, model="gemini-4-hydrogen")
    res_flex = prof_flex.profile_episode("1 [mowca_a]: Hi again.")
    assert isinstance(res_flex, EpisodeProfile)
    assert res_flex.episode_summary == "Po fallbacku standard"
    assert len(prof_calls) == 3
    assert all("gemini-4-hydrogen" in c["url"] for c in prof_calls)
    assert [c["header"] for c in prof_calls] == ["flex", "flex", None]

    # 2. VisualSignDetector under 'flex' + 2x 503 fallback on gap 1 & 2, succeeding in 'standard' on gap 3
    frame_counter = {"k": 0}

    def _fake_extract_frame(video_path: str, ts_ms: int, max_width: int = 640) -> str:
        frame_counter["k"] += 1
        img_path = tmp_path / f"gap_frame_{frame_counter['k']}_{ts_ms}.png"
        Image.new("RGB", (16, 16), color=(10, 20, 30)).save(img_path)
        return str(img_path)

    monkeypatch.setattr(sign_detector, "extract_frame_at_timestamp", _fake_extract_frame)

    sign_calls = []
    sign_n = {"i": 0}

    def _sign_flex_handler(request: httpx.Request) -> httpx.Response:
        sign_n["i"] += 1
        body = json.loads(request.content.decode("utf-8"))
        sign_calls.append(
            {
                "url": str(request.url),
                "header": request.headers.get("X-Gemini-Service-Tier"),
                "body": body.get("serviceTier") or body.get("service_tier"),
            }
        )
        if sign_n["i"] <= 2:
            return httpx.Response(
                503,
                json={"error": {"code": 503, "message": "503 Unavailable", "status": "UNAVAILABLE"}},
            )
        ok_sign = DetectedSign(
            is_title_or_banner=True,
            original_text="CHAPTER ONE",
            translation_pl="ROZDZIAŁ PIERWSZY",
            banner_type="CHAPTER_SIGN",
            screen_region="top_center",
        ).model_dump_json()
        return httpx.Response(
            200,
            json={
                "candidates": [{"content": {"role": "model", "parts": [{"text": ok_sign}]}}],
                "usageMetadata": {"promptTokenCount": 150, "cachedContentTokenCount": 0, "candidatesTokenCount": 25},
            },
        )

    sign_client = _make_mock_genai_client(_sign_flex_handler)
    dummy_vid = tmp_path / "synthetic_video.mkv"
    dummy_vid.write_bytes(b"")
    gaps = [(1000, 5000), (10000, 14000), (20000, 24000)]
    events = VisualSignDetector.detect_signs_in_gaps(
        video_path=str(dummy_vid),
        gaps=gaps,
        client=sign_client,
        model="gemini-4-hydrogen",
    )
    assert len(sign_calls) == 3
    assert all("gemini-4-hydrogen" in c["url"] for c in sign_calls)
    assert [c["header"] for c in sign_calls] == ["flex", "flex", None]
    assert len(events) == 1
    assert "ROZDZIAŁ PIERWSZY" in events[0].text
