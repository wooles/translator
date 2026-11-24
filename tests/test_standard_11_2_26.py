"""
Zestaw testów integracyjnych dla Standardu 11.2.26 (OBS-04 — Telemetria ponowień API):
1. test_obs04_f1_http_503_via_httpx_mock_transport_logs_retry_before_phase1_batch
2. test_obs04_f1_retry_error_types_429_504_and_timeout_recorded_sequentially
3. test_obs04_f2_http_503_via_httpx_mock_transport_logs_retry_before_phase2_verifier_and_restores_hook
"""

import concurrent.futures
import json
import httpx
import pytest
import pysubs2
from google import genai
from google.genai import types

from pipeline_logger import EpisodeFlightRecorder
from translator import MultimodalTranslator, BatchTranslationResponse


class _DummyPbar:
    def write(self, msg: str) -> None:
        pass

    def set_postfix_str(self, s: str) -> None:
        pass

    def refresh(self) -> None:
        pass

    def update(self, n: int = 1) -> None:
        pass


def _build_genai_client_with_mock_transport(handler) -> genai.Client:
    """Buduje prawdziwy obiekt google.genai.Client oparty o httpx.MockTransport."""
    httpx_client = httpx.Client(transport=httpx.MockTransport(handler))
    client = genai.Client(
        api_key="test_key_0",
        http_options=types.HttpOptions(httpx_client=httpx_client),
    )
    if getattr(client._api_client, "_httpx_client", None) is not httpx_client:
        client._api_client._httpx_client = httpx_client
    return client


def _make_gemini_ok_response(payload_obj: dict, prompt_tokens: int, cand_tokens: int, thought_tokens: int = 0) -> httpx.Response:
    body = {
        "candidates": [
            {
                "content": {
                    "role": "model",
                    "parts": [{"text": json.dumps(payload_obj, ensure_ascii=False)}],
                }
            }
        ],
        "usageMetadata": {
            "promptTokenCount": prompt_tokens,
            "cachedContentTokenCount": 0,
            "candidatesTokenCount": cand_tokens,
            "thoughtsTokenCount": thought_tokens,
        },
    }
    return httpx.Response(200, json=body)


def _read_jsonl_events(jsonl_path) -> list:
    return [
        json.loads(line)
        for line in jsonl_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


@pytest.mark.unit
def test_obs04_f1_http_503_via_httpx_mock_transport_logs_retry_before_phase1_batch(tmp_path, monkeypatch):
    """
    Standard 11.2.26 (OBS-04): Symuluje HTTP 503 -> 200 OK na prawdziwej warstwie httpx.MockTransport
    wewnątrz _process_phase1_only i weryfikuje z dysku plik events.jsonl oraz brak podwójnego bilingu.
    """
    monkeypatch.setattr("time.sleep", lambda s: None)
    monkeypatch.setattr("client_factory.global_rate_limiter.acquire", lambda: None)
    monkeypatch.setattr("context_cache.ContextCacheManager.get_or_create_cache", lambda *a, **kw: "__IMPLICIT_CACHE_95__")
    monkeypatch.setattr(
        "model_resolver.resolve_best_models",
        lambda *a, **kw: {"hydrogen": "gemini-4-hydrogen", "flash": "gemini-3.8-flash"},
    )

    call_counter = [0]

    def handler(request: httpx.Request) -> httpx.Response:
        call_counter[0] += 1
        if call_counter[0] == 1:
            return httpx.Response(
                503,
                json={
                    "error": {
                        "code": 503,
                        "message": "The model is overloaded. Please try again later.",
                        "status": "UNAVAILABLE",
                    }
                },
            )
        return _make_gemini_ok_response(
            payload_obj={
                "translations": [{"id": 1, "polish_text": "Przetłumaczona kwestia."}],
            },
            prompt_tokens=1234,
            cand_tokens=180,
            thought_tokens=70,
        )

    real_transport_client = _build_genai_client_with_mock_transport(handler)

    translator = MultimodalTranslator(
        api_key="test_key_0",
        model="gemini-4-hydrogen",
        enable_verifier=False,
    )
    translator.client_pool_f1.clients = [real_transport_client]
    translator.client = real_transport_client

    rec = EpisodeFlightRecorder(
        anime_slug="test_series",
        filename="ep01",
        trace_dir=tmp_path,
        enabled=True,
    )
    translator.flight_recorder = rec

    ev = pysubs2.SSAEvent(start=1000, end=3000, text="Sample dialogue line.", style="Default", name="Speaker_A")
    batch = [(1, ev, "Sample dialogue line.", "")]

    translator._process_phase1_only(
        b_idx=0,
        batch=batch,
        untranslated_in_batch=batch,
        batches=[batch],
        video_path=None,
        is_ass=True,
        anime_meta={"title": "Test Series"},
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

    assert call_counter[0] == 2
    events = _read_jsonl_events(rec.jsonl_path)
    retry_indices = [i for i, e in enumerate(events) if e.get("stage") == "retry"]
    phase1_indices = [i for i, e in enumerate(events) if e.get("stage") == "phase1_batch"]

    assert len(retry_indices) == 1, f"Oczekiwano dokładnie 1 zdarzenia retry, otrzymano: {events}"
    assert len(phase1_indices) == 1, f"Oczekiwano dokładnie 1 zdarzenia phase1_batch, otrzymano: {events}"
    assert retry_indices[0] < phase1_indices[0], "Wpis retry musi poprzedzać phase1_batch w events.jsonl"

    retry_ev = events[retry_indices[0]]
    p = retry_ev["payload"]
    assert retry_ev["stage"] == "retry"
    assert retry_ev["batch_id"] == 0
    assert "timestamp_iso" in retry_ev
    assert p["batch_id"] == 0
    assert p["phase"] == "F1"
    assert p["error_type"] == "503"
    assert p["attempt_number"] == 1
    assert isinstance(p["wait_ms"], int) and p["wait_ms"] > 0
    assert bool(p["timestamp"])
    assert p["model"] == "gemini-4-hydrogen"

    phase1_ev = events[phase1_indices[0]]
    tu = phase1_ev["payload"]["token_usage"]
    assert tu["prompt"] == 1234
    assert tu["output"] == 250
    assert translator.current_episode_tokens["prompt"] == 1234
    assert translator.current_episode_tokens["output"] == 250

    log_txt = rec.log_path.read_text(encoding="utf-8")
    assert "[RETRY | F1 | Paczka 0 | Próba #1]" in log_txt


@pytest.mark.unit
def test_obs04_f1_retry_error_types_429_504_and_timeout_recorded_sequentially(tmp_path, monkeypatch):
    """
    Standard 11.2.26 (OBS-04): Weryfikuje klasyfikację i sekwencyjny zapis ponowień
    429 -> 504 -> TimeoutError w events.jsonl dla paczki batch_idx=2.
    """
    monkeypatch.setattr("time.sleep", lambda s: None)
    monkeypatch.setattr("client_factory.global_rate_limiter.acquire", lambda: None)
    monkeypatch.setattr("context_cache.ContextCacheManager.get_or_create_cache", lambda *a, **kw: "__IMPLICIT_CACHE_95__")
    monkeypatch.setattr(
        "model_resolver.resolve_best_models",
        lambda *a, **kw: {"hydrogen": "gemini-4-hydrogen", "flash": "gemini-3.8-flash"},
    )

    call_counter = [0]

    def handler(request: httpx.Request) -> httpx.Response:
        call_counter[0] += 1
        if call_counter[0] == 1:
            return httpx.Response(
                429,
                json={"error": {"code": 429, "message": "Resource has been exhausted.", "status": "RESOURCE_EXHAUSTED"}},
            )
        if call_counter[0] == 2:
            return httpx.Response(
                504,
                json={"error": {"code": 504, "message": "Deadline exceeded.", "status": "DEADLINE_EXCEEDED"}},
            )
        if call_counter[0] == 3:
            raise concurrent.futures.TimeoutError()
        return _make_gemini_ok_response(
            payload_obj={"translations": []},
            prompt_tokens=500,
            cand_tokens=40,
        )

    real_transport_client = _build_genai_client_with_mock_transport(handler)

    translator = MultimodalTranslator(
        api_key="test_key_0",
        model="gemini-4-hydrogen",
        enable_verifier=False,
    )
    translator.client_pool_f1.clients = [real_transport_client]
    translator.client = real_transport_client

    rec = EpisodeFlightRecorder(
        anime_slug="test_series",
        filename="ep01",
        trace_dir=tmp_path,
        enabled=True,
    )
    translator.flight_recorder = rec

    res = translator._call_gemini_with_retry(contents=["Test"], schema_class=BatchTranslationResponse, batch_idx=2)
    assert res is not None
    assert call_counter[0] == 4

    events = _read_jsonl_events(rec.jsonl_path)
    retry_evs = [e for e in events if e.get("stage") == "retry" and e.get("batch_id") == 2]
    assert len(retry_evs) == 3, f"Oczekiwano 3 rekordów retry dla paczki 2, otrzymano: {retry_evs}"
    assert [e["payload"]["error_type"] for e in retry_evs] == ["429", "504", "TimeoutError"]
    assert [e["payload"]["attempt_number"] for e in retry_evs] == [1, 2, 3]
    for e in retry_evs:
        assert e["payload"]["phase"] == "F1"
        assert isinstance(e["payload"]["wait_ms"], int) and e["payload"]["wait_ms"] > 0
        assert bool(e["payload"]["timestamp"])


@pytest.mark.unit
def test_obs04_f2_http_503_via_httpx_mock_transport_logs_retry_before_phase2_verifier_and_restores_hook(tmp_path, monkeypatch):
    """
    Standard 11.2.26 (OBS-04): Weryfikuje telemetrię ponowień F2 (phase='F2') na HTTP 503 -> 200 OK
    przez scoped obserwator na client_pool_f2 bez modyfikacji chronionego Z16 verifier.py,
    a także przywrócenie oryginalnej metody report_error po zakończeniu.
    """
    monkeypatch.setattr("time.sleep", lambda s: None)
    monkeypatch.setattr("client_factory.global_rate_limiter.acquire", lambda: None)
    monkeypatch.setattr("context_cache.ContextCacheManager.get_or_create_cache", lambda *a, **kw: "__IMPLICIT_CACHE_95__")
    monkeypatch.setattr(
        "model_resolver.resolve_best_models",
        lambda *a, **kw: {"hydrogen": "gemini-4-hydrogen", "flash": "gemini-3.8-flash"},
    )

    call_counter = [0]

    def handler(request: httpx.Request) -> httpx.Response:
        call_counter[0] += 1
        if call_counter[0] == 1:
            return httpx.Response(
                503,
                json={
                    "error": {
                        "code": 503,
                        "message": "The service is currently unavailable.",
                        "status": "UNAVAILABLE",
                    }
                },
            )
        return _make_gemini_ok_response(
            payload_obj={
                "lines": [{"id": 1, "refined_pl": "Szlifowana kwestia.", "changes_made": "Zwięzłość"}]
            },
            prompt_tokens=900,
            cand_tokens=110,
            thought_tokens=50,
        )

    real_transport_client = _build_genai_client_with_mock_transport(handler)

    translator = MultimodalTranslator(
        api_key="test_key_0",
        model="gemini-4-hydrogen",
        enable_verifier=True,
    )
    translator.client_pool_f2.clients = [real_transport_client]
    translator.verifier.client = real_transport_client

    rec = EpisodeFlightRecorder(
        anime_slug="test_series",
        filename="ep01",
        trace_dir=tmp_path,
        enabled=True,
    )
    translator.flight_recorder = rec

    ev = pysubs2.SSAEvent(start=1000, end=3000, text="Sample dialogue line.", style="Default", name="Speaker_A")
    pass1_items = [
        {
            "id": 1,
            "orig_idx": 1,
            "en": "Sample dialogue line.",
            "pl": "Wstępny przekład.",
            "speaker": "Speaker_A",
            "speaker_name": "Speaker_A",
            "style": "Default",
            "notes": "",
            "is_sign": False,
        }
    ]
    phase1_data = {
        "b_idx": 0,
        "pass1_items": pass1_items,
        "untranslated_in_batch": [(1, ev, "Sample dialogue line.", "")],
        "scene_desc": "Test scene",
        "batch_response": None,
        "lookback_history": [],
        "lookahead_events": [],
        "scoped_series_bible_str": "",
        "user_feedback_str": "",
        "glossary_str": "",
        "episode_profile_str": "",
        "manga_canon_str": "",
        "batch_glossary_items": [],
        "speakers_on_ty": set(),
        "scene_has_first_name_vocative": False,
        "is_ass": True,
        "pbar": _DummyPbar(),
        "combined_glossary": {},
        "all_user_rules": [],
        "episode_profile": None,
        "total_batches": 1,
    }

    orig_report = translator.verifier.client_pool.report_error
    translator._process_phase2_only(phase1_data)

    assert translator.verifier.client_pool.report_error == orig_report
    assert call_counter[0] == 2

    events = _read_jsonl_events(rec.jsonl_path)
    retry_indices = [i for i, e in enumerate(events) if e.get("stage") == "retry"]
    p2_indices = [i for i, e in enumerate(events) if e.get("stage") == "phase2_verifier"]

    assert len(retry_indices) == 1, f"Oczekiwano dokładnie 1 zdarzenia retry F2, otrzymano: {events}"
    assert len(p2_indices) == 1, f"Oczekiwano dokładnie 1 zdarzenia phase2_verifier, otrzymano: {events}"
    assert retry_indices[0] < p2_indices[0], "Wpis retry F2 musi poprzedzać phase2_verifier w events.jsonl"

    retry_ev = events[retry_indices[0]]
    p = retry_ev["payload"]
    assert retry_ev["batch_id"] == 0
    assert p["phase"] == "F2"
    assert p["error_type"] == "503"
    assert p["attempt_number"] == 1
    assert p["wait_ms"] > 0
    assert bool(p["timestamp"])
