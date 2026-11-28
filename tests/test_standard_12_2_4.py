# -*- coding: utf-8 -*-
"""
Standard 12.2.4 Regression Suite (S2: Flex F2 + PricingGuard Flex 0.5x + Z16-amendment #17).
100% Z1-pure synthetic test suite operating on real genai.Client + httpx.MockTransport & PricingGuard.
"""

import json
import time
from pathlib import Path

import httpx
import pytest
from google import genai
from google.genai import types as genai_types

from pricing_guard import PricingGuard
from series_memory import SeriesBible
from translator import (
    BatchTranslationResponse,
    LineTranslation,
    MultimodalTranslator,
    SceneDiagnosis,
)
from verifier import LeanRefinedBatchResponse, LeanRefinedLine, RefinedLine


def _make_mock_genai_client(handler) -> genai.Client:
    http_client = httpx.Client(transport=httpx.MockTransport(handler))
    client = genai.Client(
        api_key="mock_k0",
        http_options=genai_types.HttpOptions(httpx_client=http_client),
    )
    if getattr(client._api_client, "_httpx_client", None) is not http_client:
        client._api_client._httpx_client = http_client
    return client


def _make_translator_with_transport(tmp_path: Path, handler, enable_verifier: bool = True) -> MultimodalTranslator:
    tr = MultimodalTranslator(api_key="mock_k0", model="gemini-4-hydrogen", enable_verifier=enable_verifier)
    mock_c = _make_mock_genai_client(handler)
    tr.client_pool_f1.clients = [mock_c]
    tr.client_pool.clients = [mock_c]
    tr.client = mock_c
    tr.trace_dir = str(tmp_path)
    tr.series_bible = SeriesBible("SyntheticSeries1224", storage_dir=tmp_path)
    tr.system_prompt = "lean system prompt"
    if hasattr(tr, "verifier") and tr.verifier is not None:
        tr.verifier.client_pool.clients = [mock_c]
        tr.verifier.client = mock_c
        tr.verifier.system_prompt = "lean verifier prompt"
    return tr


def _sample_f2_batch():
    return [
        {
            "id": 1,
            "orig_idx": 1,
            "start_ms": 1000,
            "end_ms": 2500,
            "speaker": "mowca_a",
            "en": "Let us check the perimeter right now.",
            "pl": "Sprawdźmy obwód w tej chwili.",
            "speaker_confidence": 1.0,
            "target_confidence": 1.0,
        }
    ]


# ------------------------------------------------------------------------------
# 1. Verifier default 'standard' sends NO Flex headers/fields & 0 flex tokens
# ------------------------------------------------------------------------------
@pytest.mark.unit
def test_s2_verifier_default_standard_no_flex_headers(tmp_path: Path, monkeypatch):
    monkeypatch.delenv("AVT_SERVICE_TIER", raising=False)
    monkeypatch.setattr(time, "sleep", lambda *a, **kw: None)

    seen_requests = []
    ok_payload = LeanRefinedBatchResponse(
        lines=[LeanRefinedLine(id=1, refined_pl="Sprawdźmy teraz obwód.", changes_made="Zwięzłość")]
    ).model_dump_json()

    def _handler(request: httpx.Request) -> httpx.Response:
        if request.method == "GET":
            return httpx.Response(200, json={"models": []})
        body = json.loads(request.content.decode("utf-8"))
        seen_requests.append(
            {
                "url": str(request.url),
                "header_tier": request.headers.get("X-Gemini-Service-Tier"),
                "body_tier": body.get("serviceTier") or body.get("service_tier"),
            }
        )
        return httpx.Response(
            200,
            json={
                "candidates": [{"content": {"role": "model", "parts": [{"text": ok_payload}]}}],
                "usageMetadata": {"promptTokenCount": 420, "cachedContentTokenCount": 0, "candidatesTokenCount": 55, "thoughtsTokenCount": 25},
            },
        )

    tr = _make_translator_with_transport(tmp_path, _handler, enable_verifier=True)
    res = tr.verifier.verify_batch(_sample_f2_batch(), batch_idx=0)
    assert len(res) == 1 and isinstance(res[0], RefinedLine)
    assert len(seen_requests) == 1
    assert seen_requests[0]["header_tier"] is None
    assert seen_requests[0]["body_tier"] is None

    tl_usage = tr.verifier._thread_local.last_batch_token_usage
    assert tl_usage["service_tier"] == "standard"
    assert "response_service_tier_header" not in tl_usage
    assert tr.verifier.current_episode_tokens["prompt"] == 420
    assert tr.verifier.current_episode_tokens["output"] == 80
    assert tr.verifier.current_episode_tokens.get("flex_prompt", 0) == 0
    assert tr.verifier.current_episode_tokens.get("flex_output", 0) == 0


# ------------------------------------------------------------------------------
# 2. Verifier opt-in 'flex' sends header + body tier, reads response header, accumulates flex_*
# ------------------------------------------------------------------------------
@pytest.mark.unit
def test_s2_verifier_opt_in_flex_sends_header_records_telemetry_and_flex_tokens(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("AVT_SERVICE_TIER", "flex")
    monkeypatch.setattr(time, "sleep", lambda *a, **kw: None)

    seen_requests = []
    ok_payload = LeanRefinedBatchResponse(
        lines=[LeanRefinedLine(id=1, refined_pl="Sprawdźmy teraz obwód.", changes_made="Zwięzłość")]
    ).model_dump_json()

    def _handler(request: httpx.Request) -> httpx.Response:
        if request.method == "GET":
            return httpx.Response(200, json={"models": []})
        body = json.loads(request.content.decode("utf-8"))
        seen_requests.append(
            {
                "url": str(request.url),
                "header_tier": request.headers.get("X-Gemini-Service-Tier"),
                "body_tier": body.get("serviceTier") or body.get("service_tier"),
            }
        )
        return httpx.Response(
            200,
            headers={"X-Gemini-Service-Tier": "flex"},
            json={
                "candidates": [{"content": {"role": "model", "parts": [{"text": ok_payload}]}}],
                "usageMetadata": {"promptTokenCount": 900, "cachedContentTokenCount": 100, "candidatesTokenCount": 70, "thoughtsTokenCount": 30},
            },
        )

    tr = _make_translator_with_transport(tmp_path, _handler, enable_verifier=True)
    res = tr.verifier.verify_batch(_sample_f2_batch(), batch_idx=0)
    assert len(res) == 1
    assert len(seen_requests) == 1
    assert "gemini-4-hydrogen" in seen_requests[0]["url"]
    assert seen_requests[0]["header_tier"] == "flex"
    assert str(seen_requests[0]["body_tier"]).upper() == "FLEX"

    tl_usage = tr.verifier._thread_local.last_batch_token_usage
    assert tl_usage["service_tier"] == "flex"
    assert tl_usage["response_service_tier_header"] == "flex"
    assert tr.verifier.current_episode_tokens["prompt"] == 900
    assert tr.verifier.current_episode_tokens["cached"] == 100
    assert tr.verifier.current_episode_tokens["output"] == 100
    assert tr.verifier.current_episode_tokens["flex_prompt"] == 900
    assert tr.verifier.current_episode_tokens["flex_cached"] == 100
    assert tr.verifier.current_episode_tokens["flex_output"] == 100


# ------------------------------------------------------------------------------
# 3. Verifier Flex 2x 503/TimeoutError fallback -> 'standard' on SAME Hydrogen model
# ------------------------------------------------------------------------------
@pytest.mark.unit
def test_s2_verifier_flex_two_503_or_timeout_fallback_to_standard_same_hydrogen_model(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("AVT_SERVICE_TIER", "flex")
    monkeypatch.setattr(time, "sleep", lambda *a, **kw: None)

    seen_requests = []
    attempt_num = {"n": 0}
    ok_payload = LeanRefinedBatchResponse(
        lines=[LeanRefinedLine(id=1, refined_pl="Sprawdźmy teraz obwód.", changes_made=None)]
    ).model_dump_json()

    def _handler(request: httpx.Request) -> httpx.Response:
        if request.method == "GET":
            return httpx.Response(200, json={"models": []})
        attempt_num["n"] += 1
        body = json.loads(request.content.decode("utf-8"))
        seen_requests.append(
            {
                "url": str(request.url),
                "header_tier": request.headers.get("X-Gemini-Service-Tier"),
                "body_tier": body.get("serviceTier") or body.get("service_tier"),
            }
        )
        if attempt_num["n"] == 1:
            raise TimeoutError()
        if attempt_num["n"] == 2:
            return httpx.Response(
                503,
                json={"error": {"code": 503, "message": "Service Unavailable (flex busy)", "status": "UNAVAILABLE"}},
            )
        return httpx.Response(
            200,
            headers={"X-Gemini-Service-Tier": "standard"},
            json={
                "candidates": [{"content": {"role": "model", "parts": [{"text": ok_payload}]}}],
                "usageMetadata": {"promptTokenCount": 510, "cachedContentTokenCount": 0, "candidatesTokenCount": 60, "thoughtsTokenCount": 20},
            },
        )

    tr = _make_translator_with_transport(tmp_path, _handler, enable_verifier=True)
    res = tr.verifier.verify_batch(_sample_f2_batch(), batch_idx=0)
    assert len(res) == 1
    assert len(seen_requests) == 3

    # ZERO downgrade to Flash — all 3 calls hit gemini-4-hydrogen
    for rec in seen_requests:
        assert "gemini-4-hydrogen" in rec["url"]
        assert "flash" not in rec["url"].lower()
    assert tr.verifier.model == "gemini-4-hydrogen"

    # Calls #1 and #2 sent flex; call #3 fell back to standard
    assert seen_requests[0]["header_tier"] == "flex"
    assert seen_requests[1]["header_tier"] == "flex"
    assert seen_requests[2]["header_tier"] is None
    assert seen_requests[2]["body_tier"] is None

    tl_usage = tr.verifier._thread_local.last_batch_token_usage
    assert tl_usage["service_tier"] == "standard"
    assert tl_usage["response_service_tier_header"] == "standard"
    assert tr.verifier.current_episode_tokens["prompt"] == 510
    assert tr.verifier.current_episode_tokens["output"] == 80
    assert tr.verifier.current_episode_tokens.get("flex_prompt", 0) == 0
    assert tr.verifier.current_episode_tokens.get("flex_output", 0) == 0


# ------------------------------------------------------------------------------
# 4. PricingGuard exact Flex 0.5x & mixed fallback accounting
# ------------------------------------------------------------------------------
@pytest.mark.unit
def test_s2_pricing_guard_flex_exact_and_mixed_fallback_accounting():
    f1_base = {"prompt": 269_059, "cached": 0, "output": 32_519, "model": "gemini-4-hydrogen"}
    f2_base = {"prompt": 183_171, "cached": 0, "output": 17_281, "model": "gemini-4-hydrogen"}

    # 1. Backward compatibility (standard, no flex_* / service_tier)
    std = PricingGuard.calculate_actual_cost_breakdown(f1_base, f2_base, usd_pln=4.0)
    assert std["net_pln"] == 4.21
    assert std["f1_net_pln"] == 2.59
    assert std["f2_net_pln"] == 1.62
    assert std["standard_net_pln"] == 4.21
    assert std["savings_pln"] == 0.0

    # 2. Mixed Flex F1 (main flex batches + 1 standard fallback tail batch) + Standard F2
    f1_mixed = {
        **f1_base,
        "flex_prompt": 245_800,
        "flex_cached": 0,
        "flex_output": 29_710,
    }
    mixed_f1_only = PricingGuard.calculate_actual_cost_breakdown(f1_mixed, f2_base, usd_pln=4.0)
    assert mixed_f1_only["f1_net_pln"] == 1.41
    assert mixed_f1_only["f2_net_pln"] == 1.62
    assert mixed_f1_only["net_pln"] == 3.02
    assert mixed_f1_only["standard_net_pln"] == 4.21
    assert mixed_f1_only["savings_pln"] == 1.19

    # 3. Full S2 (Mixed Flex F1 + 100% Flex F2)
    f2_flex = {
        **f2_base,
        "flex_prompt": 183_171,
        "flex_cached": 0,
        "flex_output": 17_281,
    }
    full_s2 = PricingGuard.calculate_actual_cost_breakdown(f1_mixed, f2_flex, usd_pln=4.0)
    assert full_s2["f1_net_pln"] == 1.41
    assert full_s2["f2_net_pln"] == 0.81
    assert full_s2["net_pln"] == 2.22
    assert full_s2["standard_net_pln"] == 4.21
    assert full_s2["savings_pln"] == 1.99
    assert full_s2["savings_ratio"] >= 0.47

    # 4. Simple service_tier="flex" flag without flex_* sub-counters -> exact 0.5x standard rate
    f1_flag_flex = {**f1_base, "cached": 100_000, "service_tier": "flex"}
    f2_flag_flex = {**f2_base, "cached": 80_000, "service_tier": "flex"}
    f1_flag_std = {**f1_base, "cached": 100_000}
    f2_flag_std = {**f2_base, "cached": 80_000}
    res_flag_flex = PricingGuard.calculate_actual_cost_breakdown(f1_flag_flex, f2_flag_flex, usd_pln=4.0)
    res_flag_std = PricingGuard.calculate_actual_cost_breakdown(f1_flag_std, f2_flag_std, usd_pln=4.0)
    assert abs(res_flag_flex["net_pln"] - round(res_flag_std["net_pln"] * 0.5, 2)) <= 0.01
    assert res_flag_flex["standard_net_pln"] == res_flag_std["standard_net_pln"] == 4.21


# ------------------------------------------------------------------------------
# 5. Translator mixed F1 (Batch 0 Flex + Batch 1 2x503->Standard fallback) exact counters
# ------------------------------------------------------------------------------
@pytest.mark.unit
def test_s2_translator_mixed_f1_flex_and_fallback_accumulates_exact_flex_counters(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("AVT_SERVICE_TIER", "flex")
    monkeypatch.setattr(time, "sleep", lambda *a, **kw: None)

    batch_resp = BatchTranslationResponse(
        scene_diagnosis=SceneDiagnosis(
            dramatic_context="Syntetyczna scena testowa",
            dialogue_flow="Dialog",
            audio_intent_check="Spójne",
            dominant_tone="Neutralny",
        ),
        translations=[LineTranslation(id=1, polish_text="Gotowe.", speaker_gender="MALE", speaker_name="mowca_a")],
    ).model_dump_json()

    post_call = {"n": 0}

    def _handler(request: httpx.Request) -> httpx.Response:
        if request.method == "GET":
            return httpx.Response(200, json={"models": []})
        post_call["n"] += 1
        # Batch 0 (call #1): succeeds on Flex (1200 in, 150 out)
        if post_call["n"] == 1:
            return httpx.Response(
                200,
                headers={"X-Gemini-Service-Tier": "flex"},
                json={
                    "candidates": [{"content": {"role": "model", "parts": [{"text": batch_resp}]}}],
                    "usageMetadata": {"promptTokenCount": 1200, "cachedContentTokenCount": 0, "candidatesTokenCount": 120, "thoughtsTokenCount": 30},
                },
            )
        # Batch 1 (calls #2, #3 -> 503 in flex; call #4 -> 200 in standard with 900 in, 110 out)
        if post_call["n"] in (2, 3):
            return httpx.Response(
                503,
                json={"error": {"code": 503, "message": "503 Unavailable", "status": "UNAVAILABLE"}},
            )
        return httpx.Response(
            200,
            headers={"X-Gemini-Service-Tier": "standard"},
            json={
                "candidates": [{"content": {"role": "model", "parts": [{"text": batch_resp}]}}],
                "usageMetadata": {"promptTokenCount": 900, "cachedContentTokenCount": 0, "candidatesTokenCount": 90, "thoughtsTokenCount": 20},
            },
        )

    tr = _make_translator_with_transport(tmp_path, _handler, enable_verifier=False)
    res0 = tr._call_gemini_with_retry(["Paczka 0"], BatchTranslationResponse, batch_idx=0)
    res1 = tr._call_gemini_with_retry(["Paczka 1"], BatchTranslationResponse, batch_idx=1)

    assert isinstance(res0, BatchTranslationResponse)
    assert isinstance(res1, BatchTranslationResponse)
    assert post_call["n"] == 4

    tok = tr.current_episode_tokens
    assert tok["prompt"] == 2100
    assert tok["output"] == 260
    assert tok["flex_prompt"] == 1200
    assert tok["flex_cached"] == 0
    assert tok["flex_output"] == 150

    mixed_cost = PricingGuard.calculate_actual_cost_breakdown(tok, None, usd_pln=4.0)
    all_std_cost = PricingGuard.calculate_actual_cost_breakdown(
        {"prompt": 2100, "cached": 0, "output": 260, "model": "gemini-4-hydrogen"},
        None,
        usd_pln=4.0,
    )
    all_flex_cost = PricingGuard.calculate_actual_cost_breakdown(
        {"prompt": 2100, "cached": 0, "output": 260, "flex_prompt": 2100, "flex_output": 260, "model": "gemini-4-hydrogen"},
        None,
        usd_pln=4.0,
    )
    assert all_flex_cost["net_pln"] <= mixed_cost["net_pln"] <= all_std_cost["net_pln"]
    expected_usd = (
        ((900 + 0.5 * 1200) / 1_000_000) * 1.50
        + ((110 + 0.5 * 150) / 1_000_000) * 7.50
    )
    assert mixed_cost["net_pln"] == round(expected_usd * 4.0, 2)
