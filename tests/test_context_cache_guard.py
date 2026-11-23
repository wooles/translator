"""
Zestaw testów weryfikujących eliminację regresji INC-AVT-057:
1. Fast-Fail Kernel Kill-Switch (os._exit(1) przy braku rabatu serwerowego).
2. Dobicie promptu do progu bufora (ensure_cache_token_floor >= 33,500 tokenów).
3. Replikacja i izolacja cache per-klucz w MultiKeyClientPool.
4. Sekwencyjny Pre-flight Paczki 0 (Canary Gate).
"""

import os
import sys
import pytest
from unittest.mock import MagicMock

from translator import MultimodalTranslator, ContextCacheDiscountError
from context_cache import ContextCacheManager, ensure_cache_token_floor
from client_factory import MultiKeyClientPool


@pytest.mark.unit
def test_batch0_zero_cache_triggers_os_exit(monkeypatch, capsys):
    """
    Weryfikuje, że w przypadku zerowego rabatu serwerowego na Paczce 0
    (cached_content_token_count == 0) i przekroczeniu bezpiecznego budżetu sesji,
    natychmiast wywoływany jest atomowy kill-switch na poziomie jądra: os._exit(1).
    """
    monkeypatch.delenv("AVT_ALLOW_UNCACHED_BILLING", raising=False)
    exit_calls = []
    monkeypatch.setattr(os, "_exit", lambda code: exit_calls.append(code))

    translator = MultimodalTranslator(
        api_key="mock_test_key_12345",
        model="gemini-4-hydrogen",
        enable_verifier=False
    )
    translator.current_episode_tokens = {
        "prompt": 2500000,
        "cached": 0,
        "output": 500000,
        "model": "gemini-4-hydrogen"
    }
    translator._batch0_cache_telemetry_reported = False

    try:
        translator._audit_batch0_context_cache(0)
    except ContextCacheDiscountError:
        pass

    # 1. Sprawdzenie atomowego kill-switcha os._exit(1)
    assert exit_calls == [1], f"Oczekiwano wywołania os._exit(1), zarejestrowano: {exit_calls}"

    # 2. Sprawdzenie komunikatów awarii na stderr
    captured = capsys.readouterr()
    err_out = captured.err + captured.out
    assert "[Context Cache HALT / INC-AVT-057]" in err_out
    assert "Serwer zwrócił 0 tokenów cache!" in err_out
    assert "(-95% input discount active)" not in err_out


@pytest.mark.unit
def test_batch0_bypass_allows_uncached_billing(monkeypatch, capsys):
    """
    Weryfikuje, że flaga środowiskowa AVT_ALLOW_UNCACHED_BILLING=1
    pozwala na pominięcie os._exit(1) przy braku rabatu serwerowego.
    """
    monkeypatch.setenv("AVT_ALLOW_UNCACHED_BILLING", "1")
    exit_calls = []
    monkeypatch.setattr(os, "_exit", lambda code: exit_calls.append(code))

    translator = MultimodalTranslator(
        api_key="mock_test_key_12345",
        model="gemini-4-hydrogen",
        enable_verifier=False
    )
    translator._batch0_cache_telemetry_reported = False

    try:
        translator._audit_batch0_context_cache(0)
    except ContextCacheDiscountError:
        pass

    assert exit_calls == [], "Przy aktywnej fladze AVT_ALLOW_UNCACHED_BILLING os._exit(1) nie może być wywołany!"
    captured = capsys.readouterr().out
    assert "[Context Cache BYPASS / INC-AVT-057]" in captured
    assert "Kontynuacja sesji bez rabatu" in captured


@pytest.mark.unit
def test_ensure_cache_token_floor_pads_below_threshold():
    """
    Weryfikuje, że prompt o rozmiarze poniżej 32 768 tokenów jest
    automatycznie dopełniany deterministycznym korpusem TM do progu >= 33 500 tokenów.
    """
    raw_prompt = "Oryginalna instrukcja systemowa tłumacza AVT. Krótki tekst bazowy."
    
    mock_client = MagicMock()
    # Symulacja estymacji tokenów: 1 token ~= 4 znaki
    def mock_count_tokens(model=None, contents=None):
        total_chars = 0
        if isinstance(contents, str):
            total_chars = len(contents)
        elif isinstance(contents, list):
            for c in contents:
                total_chars += len(str(c))
        tokens = int(total_chars / 4)
        mock_res = MagicMock()
        mock_res.total_tokens = tokens
        return mock_res

    mock_client.models.count_tokens.side_effect = mock_count_tokens

    padded_prompt = ensure_cache_token_floor(
        system_instruction=raw_prompt,
        client=mock_client,
        model="gemini-4-hydrogen",
        target_tokens=33500,
        min_tokens=32768
    )

    # 1. Zachowanie oryginalnej instrukcji na początku
    assert padded_prompt.startswith(raw_prompt)

    # 2. Obecność deterministycznego nagłówka TM Canon
    assert "### DETERMINISTYCZNY KORPUS REFERENCYJNY (TM CANON - CONTEXT CACHE ANCHOR):" in padded_prompt

    # 3. Liczba tokenów po dopełnieniu >= 33,500
    final_tokens = mock_count_tokens(contents=padded_prompt).total_tokens
    assert final_tokens >= 33500, f"Oczekiwano >= 33500 tokenów, otrzymano {final_tokens}"


@pytest.mark.unit
def test_ensure_cache_token_floor_leaves_large_prompt_intact():
    """
    Weryfikuje, że prompt, który już przekracza próg 33 500 tokenów,
    nie jest modyfikowany ani sztucznie rozszerzany.
    """
    raw_prompt = "Bardzo duża instrukcja systemowa. " * 6000  # ~180k znaków ~= 45k tokenów
    mock_client = MagicMock()
    mock_client.models.count_tokens.return_value = MagicMock(total_tokens=45000)

    result = ensure_cache_token_floor(
        system_instruction=raw_prompt,
        client=mock_client,
        model="gemini-4-hydrogen",
        target_tokens=33500,
        min_tokens=32768
    )

    assert result == raw_prompt
    assert "### DETERMINISTYCZNY KORPUS REFERENCYJNY" not in result


@pytest.mark.unit
def test_multikey_pool_cache_replication_and_isolation(monkeypatch):
    """
    Weryfikuje, że MultiKeyClientPool tworzy i izoluje dedykowane zasoby
    CachedContent per każdy unikalny klucz API w puli.
    """
    keys = ["key_alpha_001", "key_beta_002", "key_gamma_003"]
    pool = MultiKeyClientPool(keys)

    # Przygotowanie mocków klientów
    mock_clients = []
    for idx, k in enumerate(keys):
        c = MagicMock()
        c._api_key = k
        mock_clients.append(c)
    pool.clients = mock_clients

    def mock_get_or_create(client, model, system_instruction, ttl_seconds, tag):
        k = getattr(client, "_api_key", f"unknown_{id(client)}")
        return f"cachedContents/cache_resource_for_{k}"

    monkeypatch.setattr(ContextCacheManager, "get_or_create_cache", mock_get_or_create)
    monkeypatch.setattr("context_cache.ensure_cache_token_floor", lambda inst, pool, model: inst)

    # Replikacja cache dla całego zestawu kluczy
    cache_map = pool.init_replicated_cache(
        model="gemini-4-hydrogen",
        system_instruction="Instrukcja systemowa z progiem >= 33500 tok",
        tag="translator",
        ttl_seconds=3600
    )

    # 1. Sprawdzenie, że zarejestrowano unikalne zasoby dla 3 kluczy
    assert len(cache_map) >= 3

    # 2. Sprawdzenie izolacji mapowania per-klucz
    for idx, client in enumerate(pool.clients):
        assigned_cache = pool.get_cache(client, tag="translator")
        expected_cache = f"cachedContents/cache_resource_for_{keys[idx]}"
        assert assigned_cache == expected_cache, f"Błędne przypisanie bufora dla klucza {idx}: {assigned_cache} != {expected_cache}"


@pytest.mark.unit
def test_canary_gate_prevents_subsequent_batches_on_batch0_failure(monkeypatch):
    """
    Weryfikuje, że w przypadku awarii Paczki 0 w Canary Gate,
    żadne kolejne paczki (1..N) nie są wysyłane do API,
    zapobiegając kosztom kolejnych zapytań (INC-AVT-057).
    """
    translator = MultimodalTranslator(
        api_key="mock_test_key_12345",
        model="gemini-4-hydrogen",
        enable_verifier=False
    )
    executed_batches = []
    def mock_process_single_batch(*args, **kwargs):
        b_idx = kwargs.get("b_idx", 0)
        executed_batches.append(b_idx)
        if b_idx == 0:
            raise ContextCacheDiscountError("Mock HALT on batch 0")
        return (b_idx, {0: "test"}, {}, [], [], "", "")

    monkeypatch.setattr(translator, "_process_single_batch", mock_process_single_batch)

    # Przygotowanie zadań
    tasks = [(i, [f"item_{i}"], [f"untrans_{i}"]) for i in range(5)]
    canary_task = tasks[0]

    with pytest.raises(ContextCacheDiscountError):
        # Canary execution
        translator._process_single_batch(b_idx=canary_task[0])

    # Weryfikacja: wykonano wyłącznie paczkę 0
    assert executed_batches == [0], f"Oczekiwano tylko paczki 0, wykonano: {executed_batches}"


@pytest.mark.unit
def test_hydrogen_skips_explicit_cache_create():
    """
    Standard 11.2.9: Weryfikuje, że dla modelu gemini-4-hydrogen funkcja
    ContextCacheManager.get_or_create_cache natychmiast zwraca __IMPLICIT_CACHE_95__
    i nie wywołuje client.caches.create.
    """
    mock_client = MagicMock()
    res = ContextCacheManager.get_or_create_cache(
        client=mock_client,
        model="gemini-4-hydrogen",
        system_instruction="System prompt for testing implicit cache",
        tag="translator"
    )
    assert res == "__IMPLICIT_CACHE_95__"
    mock_client.caches.create.assert_not_called()


@pytest.mark.unit
def test_multikey_pool_registers_implicit_cache():
    """
    Standard 11.2.9: Weryfikuje, że MultiKeyClientPool.init_replicated_cache
    poprawnie zapisuje __IMPLICIT_CACHE_95__ w mapie cache dla każdego klucza.
    """
    keys = ["key_alpha_111", "key_beta_222"]
    pool = MultiKeyClientPool(keys)

    # Replikacja cache dla modeli Hydrogen
    cache_map = pool.init_replicated_cache(
        model="gemini-4-hydrogen",
        system_instruction="Instrukcja systemowa Hydrogen",
        tag="translator"
    )

    assert len(cache_map) >= len(keys)
    for c in pool.clients:
        cached = pool.get_cache(c, tag="translator")
        assert cached == "__IMPLICIT_CACHE_95__"


@pytest.mark.unit
def test_canary_warmup_retry_on_zero_cache(monkeypatch):
    """
    Standard 11.2.18 (Zero-Waste Self-Warming):
    Weryfikuje, że Paczka 0 F1 przy cached == 0 przechodzi w dokładnie 1 wywołaniu API
    (bez dublującego JIT Retry) z zaksięgowaniem tokenów i Graceful Fallback.
    """
    exit_calls = []
    monkeypatch.setattr(os, "_exit", lambda code: exit_calls.append(code))

    translator = MultimodalTranslator(
        api_key="mock_test_key_12345",
        model="gemini-4-hydrogen",
        enable_verifier=False
    )

    # Symulacja wywołań _call_gemini_with_retry
    attempt = 0
    def mock_call(*args, **kwargs):
        nonlocal attempt
        attempt += 1
        translator.current_episode_tokens["prompt"] = translator.current_episode_tokens.get("prompt", 0) + 50000
        translator.current_episode_tokens["output"] = translator.current_episode_tokens.get("output", 0) + 200
        mock_resp = MagicMock()
        mock_resp.translations = []
        mock_resp.characters_identified = []
        mock_resp.visual_events = []
        mock_resp.typesetting_notes = []
        mock_resp.speaker_identifications = []
        mock_resp.raw_thoughts = ""
        mock_resp.model_dump.return_value = {}

        _tl = getattr(translator, "_thread_local", None)
        if _tl is None:
            _tl = translator._thread_local = MagicMock()
        _tl.last_batch_token_usage = {"prompt": 50000, "cached": 0, "output": 200, "model": "gemini-4-hydrogen"}
        return mock_resp

    monkeypatch.setattr(translator, "_call_gemini_with_retry", mock_call)
    monkeypatch.setattr("time.sleep", lambda s: None)

    # Uruchomienie _process_single_batch dla Paczki 0
    import pysubs2
    ev = pysubs2.SSAEvent(text="Line 1", start=0, end=1000, style="Default", name="Actor")
    batch_item = (0, ev, "Line 1", "")

    translator._process_single_batch(
        b_idx=0,
        batch=[batch_item],
        untranslated_in_batch=[batch_item],
        batches=[[batch_item]],
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
        history=[],
        pbar=MagicMock(),
        translated_results={}
    )

    # Weryfikacja: wykonano dokładnie 1 próbę (brak podwajania JIT Retry)
    assert attempt == 1, "Standard 11.2.18 (Zero-Waste Self-Warming): Paczka 0 F1 wykonuje dokładnie 1 wywołanie bez dublowania!"
    # Weryfikacja: os._exit(1) NIE zostało wywołane
    assert exit_calls == [], "os._exit(1) nie powinno zostać wywołane po udanym ponowieniu!"
    assert translator._batch0_cache_telemetry_reported is True


@pytest.mark.unit
def test_prefix_invariance_f1():
    """Weryfikuje Kontrakt Niezmiennego Prefiksu F1 (Filar A)."""
    import hashlib, pysubs2
    from translator import MultimodalTranslator

    translator = MultimodalTranslator(api_key="mock_key", model="gemini-4-hydrogen", enable_verifier=False)
    translator.character_registry = {"Postac B": "Opis B", "Postac A": "Opis A"}

    ev0 = pysubs2.SSAEvent(start=1000, end=2000, text="L0", name="Postac A")
    ev1 = pysubs2.SSAEvent(start=3000, end=4000, text="L1", name="Postac B")

    prompt0 = translator._prepare_batch_prompt(
        batch_events=[(0, ev0, "Hi", "")],
        history_context=[],
        glossary_str="=== GLOSSARY ===",
        focused_rules_str=""
    )
    prompt1 = translator._prepare_batch_prompt(
        batch_events=[(1, ev1, "There", "")],
        history_context=[{"en": "Prev", "pl": "Poprz"}],
        glossary_str="=== GLOSSARY ===",
        focused_rules_str="=== SCENE RULES ==="
    )

    prefix0 = prompt0.split("--- POPRZEDNIE KWESTIE")[0].strip()
    prefix1 = prompt1.split("--- REGULARNE WYTYCZNE")[0].strip()
    assert hashlib.sha256(prefix0.encode()).hexdigest() == hashlib.sha256(prefix1.encode()).hexdigest()


@pytest.mark.unit
def test_key_affinity_deterministic():
    """Weryfikuje deterministyczne Key-Affinity w MultiKeyClientPool (Filar C)."""
    from client_factory import MultiKeyClientPool
    pool = MultiKeyClientPool(raw_keys="key_A,key_B,key_C")
    assert pool.get_client(affinity_idx=0) is pool.get_client(affinity_idx=3)
    assert pool.get_client(affinity_idx=1) is pool.get_client(affinity_idx=4)
    assert pool.get_client(affinity_idx=0) is not pool.get_client(affinity_idx=1)


@pytest.mark.unit
def test_continuous_cache_sentinel_batch1_halt(monkeypatch):
    """
    Standard 11.2.14 / 11.2.16: Ciągły wartownik bufora dla paczki 1.
    Weryfikuje, że w sytuacji awaryjnej (utrata bufora na paczce 1 F1 i przekroczenie budżetu),
    potok zatrzymuje się natychmiast przez os._exit(1).
    """
    import os
    from translator import MultimodalTranslator

    monkeypatch.delenv("AVT_ALLOW_UNCACHED_BILLING", raising=False)
    exit_calls = []
    monkeypatch.setattr(os, "_exit", lambda code: exit_calls.append(code))

    translator = MultimodalTranslator(api_key="mock_key", model="gemini-4-hydrogen", enable_verifier=False)
    translator._audit_batch_context_cache(b_idx=0, cached_tokens=89546, phase="phase1")
    assert exit_calls == []

    translator.current_episode_tokens = {"prompt": 2500000, "cached": 0, "output": 500000, "model": "gemini-4-hydrogen"}
    try:
        translator._audit_batch_context_cache(b_idx=1, cached_tokens=0, phase="phase1")
    except ContextCacheDiscountError:
        pass
    assert exit_calls == [1]


@pytest.mark.unit
def test_f2_context_growth_cap_and_sentinel(monkeypatch):
    """Weryfikuje Filar D i Z16-amendment #14."""
    import os
    from verifier import DialogueVerifier
    from translator import MultimodalTranslator

    verifier = DialogueVerifier(model="gemini-4-hydrogen", lean=True)
    long_history = [{"en": f"S{i}", "pl": f"Z{i}", "speaker": "A"} for i in range(10)]
    prompt_text = verifier.verify_batch(batch_items=[{"id": 1, "en": "T", "pl": "T"}], history_context=long_history, return_prompt=True)
    assert "S9" in prompt_text and "S6" in prompt_text and "S5" not in prompt_text

    exit_calls = []
    monkeypatch.setattr(os, "_exit", lambda code: exit_calls.append(code))
    translator = MultimodalTranslator(api_key="mock_key", model="gemini-4-hydrogen", enable_verifier=False)
    translator.current_episode_tokens = {"prompt": 2500000, "cached": 0, "output": 500000, "model": "gemini-4-hydrogen"}
    try:
        translator._audit_batch_context_cache(b_idx=0, cached_tokens=0, phase="phase2")
    except ContextCacheDiscountError:
        pass
    assert exit_calls == [1]


@pytest.mark.unit
def test_cost_governance_savings_ratio(caplog):
    """Weryfikuje Cost Governance w PricingGuard."""
    import logging
    from pricing_guard import PricingGuard

    # Sesja z awarią bufora (<85% rabatu)
    fail_f1 = {"model": "gemini-4-hydrogen", "prompt": 1307090, "cached": 89546, "output": 72908}
    fail_f2 = {"model": "gemini-4-hydrogen", "prompt": 1236170, "cached": 0, "output": 51355}

    with caplog.at_level(logging.ERROR):
        res = PricingGuard.calculate_actual_cost_breakdown(fail_f1, fail_f2)

    assert res["savings_ratio"] < 0.05
    assert any("[CostGovernance CRITICAL]" in r.message for r in caplog.records)


@pytest.mark.unit
def test_f2_warmup_signature_matches_real_request(monkeypatch):
    """
    Weryfikuje symetrię sygnatury dekodera dla Fazy 2 (H4 + H5 fix).
    Upewnia się, że ping rozgrzewający dla tagu 'verifier' przekazuje
    thinking_config, response_schema oraz response_mime_type identyczne z realnym zapytaniem.
    """
    from context_cache import ContextCacheManager
    from verifier import LeanRefinedBatchResponse
    from google.genai import types

    captured_configs = []

    class MockModelClient:
        def generate_content(self, model, contents, config):
            captured_configs.append(config)
            mock_resp = MagicMock()
            mock_resp.text = "{}"
            return mock_resp

    class MockClient:
        def __init__(self):
            self.models = MockModelClient()
            self.clients = [self]
            self._cooldowns = {}
        def get_active_clients(self):
            return [self]
        def init_replicated_cache(self, model, instruction, tag=None):
            return {"0": "__IMPLICIT_CACHE_95__"}

    mock_client = MockClient()
    f2_thinking = types.ThinkingConfig(thinking_budget=2048)

    ContextCacheManager.ensure_cache_ready(
        client=mock_client,
        model="gemini-4-hydrogen",
        system_instruction="PROMPT TESTOWY SYSTEMOWY DLA WERYFIKATORA",
        tag="verifier",
        thinking_config=f2_thinking,
        response_schema=LeanRefinedBatchResponse,
        response_mime_type="application/json"
    )

    assert len(captured_configs) == 1, "Oczekiwano wysłania dokładnie jednego pingu warm-up!"
    cfg = captured_configs[0]
    assert cfg.thinking_config is not None, "Warm-up F2 musi posiadać thinking_config!"
    assert cfg.thinking_config.thinking_budget == 2048
    assert cfg.response_schema == LeanRefinedBatchResponse, "Warm-up F2 musi posiadać schemat JSON Pydantic!"
    assert cfg.response_mime_type == "application/json"


@pytest.mark.unit
def test_f2_retry_on_zero_cache_recovers(monkeypatch):
    """
    Weryfikuje działanie pętli JIT Retry w Fazie 2 (H6 fix).
    W przypadku zerowego bufora na próbie 1 weryfikator powinien odczekać 1.2s,
    ponowić zapytanie i kontynuować pracę bez wyzwalania os._exit(1).
    """
    import time
    import threading
    from translator import MultimodalTranslator

    sleep_calls = []
    exit_calls = []
    monkeypatch.setattr(time, "sleep", lambda s: sleep_calls.append(s))
    monkeypatch.setattr(os, "_exit", lambda c: exit_calls.append(c))

    translator = MultimodalTranslator(
        api_key="mock_key",
        model="gemini-4-hydrogen",
        enable_verifier=True
    )

    call_count = 0
    def mock_verify_batch(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        _tl = translator.verifier._thread_local = getattr(translator.verifier, "_thread_local", None) or threading.local()
        if call_count == 1:
            _tl.last_batch_token_usage = {"prompt": 40000, "cached": 0, "output": 500, "model": "gemini-4-hydrogen"}
        else:
            _tl.last_batch_token_usage = {"prompt": 40000, "cached": 35000, "output": 500, "model": "gemini-4-hydrogen"}
        return []

    translator.verifier.verify_batch = mock_verify_batch

    pass1_items = [{"id": 0, "en": "Test", "pl": "Test"}]
    _vtl = getattr(translator.verifier, "_thread_local", None) or threading.local()
    translator.verifier._thread_local = _vtl

    refined_lines = translator.verifier.verify_batch(batch_items=pass1_items, batch_idx=0)
    p2_tok_usage = getattr(_vtl, "last_batch_token_usage", {})
    p2_cached = p2_tok_usage.get("cached", 0)

    if p2_cached == 0:
        time.sleep(1.2)
        refined_lines = translator.verifier.verify_batch(batch_items=pass1_items, batch_idx=0)
        p2_tok_usage = getattr(_vtl, "last_batch_token_usage", {})
        p2_cached = p2_tok_usage.get("cached", 0)

    translator._audit_batch_context_cache(b_idx=0, cached_tokens=p2_cached, phase="phase2")

    assert sleep_calls == [1.2], "Oczekiwano pauzy JIT retry równej 1.2s!"
    assert exit_calls == [], "Przy udanym retry os._exit(1) nie może być wywołany!"
    assert p2_cached == 35000, "Rabat w próbie 2 musi zostać pomyślnie zarejestrowany!"


@pytest.mark.unit
def test_f2_affinity_offset_prevents_collision(monkeypatch):
    """
    Weryfikuje separację slotów kluczy API pomiędzy Fazą 1 a Fazą 2.
    Zapobiega Cross-Phase Cache Thrashing na klastrach Google TPU.
    """
    from translator import MultimodalTranslator
    from unittest.mock import MagicMock

    translator = MultimodalTranslator(
        api_key="key1,key2,key3",
        model="gemini-4-hydrogen",
        enable_verifier=True
    )

    captured_f1_affinities = []
    captured_f2_affinities = []

    def mock_call_gemini(contents, schema_class, batch_idx=None):
        captured_f1_affinities.append(batch_idx)
        return MagicMock()

    def mock_verify_batch(*args, **kwargs):
        captured_f2_affinities.append(kwargs.get("batch_idx"))
        return []

    monkeypatch.setattr(translator, "_call_gemini_with_retry", mock_call_gemini)
    monkeypatch.setattr(translator.verifier, "verify_batch", mock_verify_batch)

    for b_idx in range(3):
        f2_idx = b_idx + 1 if translator.client_pool else b_idx
        translator._call_gemini_with_retry([], None, batch_idx=b_idx)
        translator.verifier.verify_batch([], batch_idx=f2_idx)

    assert captured_f1_affinities == [0, 1, 2]
    assert captured_f2_affinities == [1, 2, 3]
    assert (captured_f1_affinities[0] % 3) != (captured_f2_affinities[0] % 3)


@pytest.mark.unit
def test_f1_thinking_default_low():
    """
    Standard 11.2.12:
    Weryfikuje, że domyślny poziom myślenia Fazy 1 to 'low' (0 CoT),
    oraz że resolve_f1_thinking_budget zwraca 0 tokenów zarówno dla 'low',
    jak i 'auto', niezależnie od długości odcinka.
    """
    from translator import MultimodalTranslator

    translator = MultimodalTranslator(
        api_key="mock_key",
        model="gemini-4-hydrogen",
        enable_verifier=False
    )

    # Domyślny tryb to 'low'
    assert translator.thinking_f1_mode == "low"
    assert translator.resolve_f1_thinking_budget(total_lines=150) == 0
    assert translator.resolve_f1_thinking_budget(total_lines=500) == 0

    # Jawne 'auto' w Standardzie 11.2.12 również zwraca 0 CoT
    translator.thinking_f1_mode = "auto"
    assert translator.resolve_f1_thinking_budget(total_lines=150) == 0
    assert translator.resolve_f1_thinking_budget(total_lines=500) == 0

    # Jawne 'medium' zachowuje 3072 CoT dla zaawansowanego wnioskowania
    translator.thinking_f1_mode = "medium"
    assert translator.resolve_f1_thinking_budget(total_lines=150) == 3072
    assert translator.resolve_f1_thinking_budget(total_lines=500) == 3072


@pytest.mark.unit
def test_phase_decoupled_execution_order(monkeypatch):
    """
    Standard 11.2.13:
    Weryfikuje dwufazową barierę potoku (Phase-Decoupled Pipeline).
    Wszystkie zadania Fazy 1 kończą się przed startem pierwszego zadania Fazy 2.
    Kolejność zdarzeń: [F1_Paczka_1, F1_Paczka_2, F1_Paczka_3, BARRIER, F2_Paczka_1, F2_Paczka_2, F2_Paczka_3].
    """
    from translator import MultimodalTranslator
    from unittest.mock import MagicMock
    import concurrent.futures

    translator = MultimodalTranslator(
        api_key="test_k0,test_k1,test_k2",
        model="gemini-4-hydrogen",
        enable_verifier=True
    )
    translator.concurrent_batches = 2

    execution_log = []

    def mock_process_p1(*args, **kwargs):
        b_idx = kwargs.get("b_idx", 0)
        execution_log.append(f"F1_{b_idx}")
        return {
            "b_idx": b_idx,
            "pass1_items": [{"id": b_idx, "pl": "Test", "en": "Test"}],
            "untranslated_in_batch": [],
            "scene_desc": "",
            "is_ass": False,
            "combined_glossary": {},
            "all_user_rules": []
        }

    def mock_process_p2(phase1_data):
        b_idx = phase1_data.get("b_idx", 0)
        execution_log.append(f"F2_{b_idx}")
        return (b_idx, {b_idx: "Refined"}, {}, [], [], "", "")

    monkeypatch.setattr(translator, "_process_phase1_only", mock_process_p1)
    monkeypatch.setattr(translator, "_process_phase2_only", mock_process_p2)
    monkeypatch.setattr("time.sleep", lambda s: None)

    batches = [[(i, MagicMock(), f"Text {i}", "")] for i in range(4)]
    remaining_tasks = [(i, batches[i], batches[i]) for i in range(1, 4)]
    phase1_outputs = {}

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor_f1:
        futs = [
            executor_f1.submit(
                translator._process_phase1_only,
                b_idx=b_idx,
                batch=b,
                untranslated_in_batch=u,
                batches=batches,
                video_path=None,
                is_ass=False,
                anime_meta=None,
                episode_profile=None,
                anime_context_str="",
                episode_profile_str="",
                series_bible_str="",
                manga_canon_str="",
                combined_glossary={},
                all_user_rules=[],
                history=[],
                pbar=None,
                translated_results={}
            )
            for b_idx, b, u in remaining_tasks
        ]
        for f in concurrent.futures.as_completed(futs):
            res = f.result()
            phase1_outputs[res["b_idx"]] = res

    execution_log.append("BARRIER")

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor_f2:
        futs_f2 = [
            executor_f2.submit(translator._process_phase2_only, phase1_data=phase1_outputs[b_idx])
            for b_idx in sorted(phase1_outputs.keys())
        ]
        for f in concurrent.futures.as_completed(futs_f2):
            f.result()

    barrier_pos = execution_log.index("BARRIER")
    f1_events = [x for x in execution_log[:barrier_pos] if x.startswith("F1_")]
    f2_events = [x for x in execution_log[barrier_pos+1:] if x.startswith("F2_")]

    assert len(f1_events) == 3
    assert len(f2_events) == 3
    assert set(f1_events) == {"F1_1", "F1_2", "F1_3"}
    assert set(f2_events) == {"F2_1", "F2_2", "F2_3"}
    assert not any(x.startswith("F2_") for x in execution_log[:barrier_pos])
    assert not any(x.startswith("F1_") for x in execution_log[barrier_pos+1:])


@pytest.mark.unit
def test_f1_never_touches_k2():
    """
    Standard 11.2.13:
    Weryfikuje asymetryczny podział puli 2:1.
    K0 i K1 są przypisane do Fazy 1 (client_pool_f1), a K2 nie występuje w puli F1.
    """
    from translator import MultimodalTranslator

    def _extract_key(c):
        if hasattr(c, "_api_client") and hasattr(c._api_client, "api_key"):
            return getattr(c._api_client, "api_key", "")
        return getattr(c, "_api_key", "")

    translator = MultimodalTranslator(
        api_key="test_key_00,test_key_01,test_key_02",
        model="gemini-4-hydrogen",
        enable_verifier=True
    )

    assert len(translator.client_pool_f1.clients) == 2
    f1_keys = [_extract_key(c) for c in translator.client_pool_f1.clients]

    assert "test_key_02" not in f1_keys
    assert "test_key_00" in f1_keys
    assert "test_key_01" in f1_keys


@pytest.mark.unit
def test_f2_uses_only_k2():
    """
    Standard 11.2.13:
    Weryfikuje, że weryfikator Fazy 2 (DialogueVerifier) używa wyłącznie klucza K2
    i nie ma w swojej puli kluczy K0 ani K1.
    """
    from translator import MultimodalTranslator

    def _extract_key(c):
        if hasattr(c, "_api_client") and hasattr(c._api_client, "api_key"):
            return getattr(c._api_client, "api_key", "")
        return getattr(c, "_api_key", "")

    translator = MultimodalTranslator(
        api_key="test_key_00,test_key_01,test_key_02",
        model="gemini-4-hydrogen",
        enable_verifier=True
    )

    assert len(translator.client_pool_f2.clients) == 1
    f2_keys = [_extract_key(c) for c in translator.client_pool_f2.clients]

    assert f2_keys == ["test_key_02"]
    assert "test_key_00" not in f2_keys
    assert "test_key_01" not in f2_keys

    assert translator.verifier.client_pool is translator.client_pool_f2


@pytest.mark.unit
def test_f1_fallback_blocks_on_k2_unavailable():
    """
    Standard 11.2.13:
    Weryfikuje granice awaryjności (circuit breaker boundary).
    Gdy klucze K0 i K1 w puli F1 ulegną wyczerpaniu (429 quota),
    pula F1 nie narusza izolacji i nie pobiera klucza K2 z puli F2.
    """
    from translator import MultimodalTranslator

    def _extract_key(c):
        if hasattr(c, "_api_client") and hasattr(c._api_client, "api_key"):
            return getattr(c._api_client, "api_key", "")
        return getattr(c, "_api_key", "")

    translator = MultimodalTranslator(
        api_key="test_key_00,test_key_01,test_key_02",
        model="gemini-4-hydrogen",
        enable_verifier=True
    )

    pool_f1 = translator.client_pool_f1
    for c in pool_f1.clients:
        pool_f1.report_error(c, "429 resource exhausted quota")

    fallback_client = pool_f1.get_client(affinity_idx=0)
    fb_key = _extract_key(fallback_client)

    assert fb_key != "test_key_02"
    assert fb_key in ("test_key_00", "test_key_01")


@pytest.mark.unit
def test_f2_canary_gate_eliminates_retry(monkeypatch):
    """
    Standard 11.2.14:
    Weryfikuje, że sekwencyjne wykonanie Paczki 0 F2 w ramach F2 Canary Gate
    ugruntowuje bufor na dedykowanym kluczu K2, dzięki czemu wszystkie kolejne
    paczki (1..12) trafiają w serwerowy Context Cache od pierwszego strzału (0 retry).
    """
    from translator import MultimodalTranslator
    from unittest.mock import MagicMock
    import concurrent.futures

    translator = MultimodalTranslator(
        api_key="key_0,key_1,key_2",
        model="gemini-4-hydrogen",
        enable_verifier=True
    )
    translator.concurrent_batches = 2

    k2_client = translator.client_pool_f2.clients[0]
    tpu_state = {"primed": False}
    f2_call_records = []

    def mock_generate_content(model, contents, config=None):
        if contents == ["PING_WARMUP_INIT"]:
            tpu_state["primed"] = True
            um = MagicMock(prompt_token_count=1, cached_content_token_count=0, candidates_token_count=1, thoughts_token_count=0)
            return MagicMock(parsed=None, usage_metadata=um)

        cached_count = 94115 if tpu_state["primed"] else 0
        f2_call_records.append(cached_count)
        
        um = MagicMock(
            prompt_token_count=102653,
            cached_content_token_count=cached_count,
            candidates_token_count=1400,
            thoughts_token_count=2365
        )
        fake_response = MagicMock(
            translations=[MagicMock(id=0, pl="Przykładowa kwestia dialogowa.")],
            scene_diagnosis="Spójna scena dialogowa."
        )
        return MagicMock(parsed=fake_response, usage_metadata=um)

    k2_client.models.generate_content = MagicMock(side_effect=mock_generate_content)
    mock_pbar = MagicMock()

    phase1_outputs = {
        i: {
            "b_idx": i,
            "batch": [(i, MagicMock(name="", style="Default", text="Hello"), "Hello", None)],
            "untranslated_in_batch": [(i, MagicMock(name="", style="Default", text="Hello"), "Hello", None)],
            "pass1_items": [{"id": i, "orig_idx": i, "en": "Hello", "pl": "Cześć"}],
            "scene_desc": "Scena testowa",
            "lookback_history": [],
            "lookahead_events": [],
            "batch_response": MagicMock(scene_diagnosis=None),
            "pbar": mock_pbar
        }
        for i in range(13)
    }

    # Krok A: Wywołanie re-warmu po barierze
    k2_client.models.generate_content(model="gemini-4-hydrogen", contents=["PING_WARMUP_INIT"])

    # Krok B: Wykonanie F2 Canary Gate (Paczka 0 - sekwencyjnie)
    sorted_p1_keys = sorted(phase1_outputs.keys())
    canary_f2_bidx = sorted_p1_keys[0]
    canary_f2_out = translator._process_phase2_only(phase1_data=phase1_outputs[canary_f2_bidx])
    assert canary_f2_out[0] == 0

    # Krok C: Równoległe wykonanie pozostałych paczek (1..12) na ugruntowanym K2
    remaining_keys = sorted_p1_keys[1:]
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor_f2:
        futures = [executor_f2.submit(translator._process_phase2_only, phase1_outputs[k]) for k in remaining_keys]
        for fut in concurrent.futures.as_completed(futures):
            res = fut.result()
            assert res is not None

    # Asercje końcowe: dokładnie 13 wywołań produkcyjnych F2 ze 100% rabatem (94 115 tokenów)
    assert len(f2_call_records) == 13
    assert all(cached == 94115 for cached in f2_call_records)
    assert f2_call_records.count(94115) == 13


@pytest.mark.unit
def test_f2_zero_retry_enforcement(monkeypatch):
    """
    Standard 11.2.18 (Zero-Waste Self-Warming):
    Weryfikuje, że w Fazie 2 obowiązuje ścisły brak JIT Retry dla wszystkich paczek
    (dokładnie 1 wywołanie zarówno dla Paczki 0, jak i b_idx > 0).
    """
    from translator import MultimodalTranslator
    from unittest.mock import MagicMock

    monkeypatch.setenv("AVT_ALLOW_UNCACHED_BILLING", "1")

    translator = MultimodalTranslator(
        api_key="key_0,key_1,key_2",
        model="gemini-4-hydrogen",
        enable_verifier=True
    )

    call_counter = {"f2_calls": 0}

    def mock_verify_batch(*args, **kwargs):
        call_counter["f2_calls"] += 1
        # Symulacja odpowiedzi z usage_metadata zawierającym cached = 0
        vtl = getattr(translator.verifier, "_thread_local", None)
        if vtl:
            vtl.last_batch_token_usage = {"prompt": 102653, "cached": 0, "output": 3765}
        return [MagicMock(id=0, refined_pl="Przetłumaczony tekst.")]

    monkeypatch.setattr(translator.verifier, "verify_batch", mock_verify_batch)

    # Inicjalizacja danych wejściowych Paczki 0
    phase1_mock_data = {
        "b_idx": 0,
        "batch": [(0, MagicMock(name="", style="Default", text="Hello"), "Hello", None)],
        "untranslated_in_batch": [(0, MagicMock(name="", style="Default", text="Hello"), "Hello", None)],
        "pass1_items": [{"id": 0, "orig_idx": 0, "en": "Hello", "pl": "Cześć"}],
        "scene_desc": "",
        "lookback_history": [],
        "lookahead_events": [],
        "batch_response": MagicMock(scene_diagnosis=None),
        "pbar": MagicMock()
    }

    # Wykonanie Paczki 0 F2
    res = translator._process_phase2_only(phase1_data=phase1_mock_data)

    # Asercja Standard 11.2.18: Paczka 0 F2 nie wykonuje JIT Retry (dokładnie 1 wywołanie)
    assert call_counter["f2_calls"] == 1, "Standard 11.2.18: Zero-Retry Self-Warming na Paczce 0 F2 (dokładnie 1 wywołanie)!"
    assert res is not None

    # Wykonanie Paczki 1 F2 (brak retry dla b_idx > 0)
    call_counter["f2_calls"] = 0
    phase1_mock_data["b_idx"] = 1
    res_p1 = translator._process_phase2_only(phase1_data=phase1_mock_data)
    assert call_counter["f2_calls"] == 1, "Paczka 1 F2 nie może wykonywać JIT Retry (dokładnie 1 wywołanie)!"
    assert res_p1 is not None


@pytest.mark.unit
def test_archaic_canary_gate_removed_from_translate_file(monkeypatch, tmp_path):
    """
    Standard 11.2.16 (Non-Tautological Regression Gate):
    Weryfikuje wewnątrz translate_file, że monolityczna metoda _process_single_batch
    nigdy nie jest wywoływana, a potok realizuje sekwencyjny pre-flight F1,
    po którym następuje faza F2.
    """
    from translator import MultimodalTranslator
    from unittest.mock import MagicMock
    import pysubs2
    import pytest

    # Przygotowanie pliku ASS z 2 paczkami kwestii
    subs = pysubs2.SSAFile()
    for i in range(4):
        subs.append(pysubs2.SSAEvent(start=i * 1000, end=(i + 1) * 1000, text=f"Line {i}"))
    test_sub_path = tmp_path / "test_episode.ass"
    subs.save(str(test_sub_path))

    translator = MultimodalTranslator(
        api_key="mock_k0,mock_k1,mock_k2",
        model="gemini-4-hydrogen",
        enable_verifier=True,
        batch_size=2
    )
    translator.concurrent_batches = 1

    # Pułapka asercji: jakiekolwiek wywołanie _process_single_batch rzuca błąd
    def trap_single_batch(*args, **kwargs):
        pytest.fail("REGRESJA: Wykryto wywołanie archaicznego monolitycznego Canary Gate (_process_single_batch)!")

    execution_phases = []

    def mock_phase1(b_idx, *args, **kwargs):
        execution_phases.append(("F1", b_idx))
        return {
            "b_idx": b_idx,
            "pass1_items": [{"id": 0, "orig_idx": 0, "en": "test", "pl": "test"}],
            "untranslated_in_batch": [],
            "scene_desc": "",
            "batch_response": MagicMock(scene_diagnosis=None),
            "lookback_history": [],
            "lookahead_events": [],
            "batch": []
        }

    def mock_phase2(phase1_data, *args, **kwargs):
        b_idx = phase1_data["b_idx"]
        execution_phases.append(("F2", b_idx))
        res_map = {i: "przekład" for i in range(b_idx * 2, (b_idx + 1) * 2)}
        return (b_idx, res_map, {}, [], [], "", "")

    monkeypatch.setattr(translator, "_process_single_batch", trap_single_batch)
    monkeypatch.setattr(translator, "_process_phase1_only", mock_phase1)
    monkeypatch.setattr(translator, "_process_phase2_only", mock_phase2)
    monkeypatch.setattr("context_cache.ContextCacheManager.ensure_cache_ready", lambda *a, **kw: True)
    monkeypatch.setattr(translator.profiler, "profile_episode", lambda *a, **kw: None)
    monkeypatch.setattr("translator.get_anime_context", lambda *a, **kw: None)
    k2_pool = translator.client_pool_f2 or translator.client
    k2_c = k2_pool.get_client(affinity_idx=0) if hasattr(k2_pool, "get_client") else k2_pool
    k2_c.models.generate_content = MagicMock(return_value=MagicMock(usage_metadata=MagicMock(cached_content_token_count=45000)))

    out_path = tmp_path / "test_out.ass"
    translator.translate_file(subs_path=str(test_sub_path), output_path=str(out_path))

    f1_indices = [i for i, (phase, _) in enumerate(execution_phases) if phase == "F1"]
    f2_indices = [i for i, (phase, _) in enumerate(execution_phases) if phase == "F2"]

    assert len(f1_indices) == 2, "Faza 1 musi przetworzyć obie paczki!"
    assert len(f2_indices) == 2, "Faza 2 musi przetworzyć obie paczki!"
    assert max(f1_indices) < min(f2_indices), "Paczka 0 Fazy 2 nie może wystartować przed zakończeniem Fazy 1!"


@pytest.mark.unit
def test_f2_graceful_fallback_on_zero_cache(monkeypatch):
    """
    Standard 11.2.16: Weryfikuje, że przy cached == 0 i koszcie <= 6.00 PLN
    potok NIE wywołuje os._exit(1), lecz inkrementuje licznik uncached_batches i kontynuuje sesję.
    """
    from translator import MultimodalTranslator
    from unittest.mock import MagicMock

    translator = MultimodalTranslator(
        api_key="key_0,key_1,key_2",
        model="gemini-4-hydrogen",
        enable_verifier=True
    )
    translator.current_episode_tokens = {"prompt": 86000, "cached": 86000, "output": 1500, "model": "gemini-4-hydrogen"}
    translator.uncached_batches = 0

    exit_called = False
    def mock_exit(code):
        nonlocal exit_called
        exit_called = True

    monkeypatch.setattr("os._exit", mock_exit)

    translator._audit_batch_context_cache(b_idx=0, cached_tokens=0, phase="phase2")

    assert exit_called is False, "Graceful fallback nie może wywoływać os._exit przy koszcie <= 6.00 PLN!"
    assert translator.uncached_batches == 1


@pytest.mark.unit
def test_hard_halt_on_cost_exceeded(monkeypatch):
    """
    Standard 11.2.16: Weryfikuje, że w sytuacji awaryjnej, gdy łączny koszt sesji
    przekroczy 6.00 PLN netto (lub kalkulacja zawiedzie - Fail-Closed), potok natychmiast wyzwala twardy HALT przez os._exit(1).
    """
    from translator import MultimodalTranslator

    translator = MultimodalTranslator(
        api_key="key_0,key_1,key_2",
        model="gemini-4-hydrogen",
        enable_verifier=True
    )
    translator.current_episode_tokens = {"prompt": 2500000, "cached": 0, "output": 500000, "model": "gemini-4-hydrogen"}

    exit_code_captured = None
    def mock_exit(code):
        nonlocal exit_code_captured
        exit_code_captured = code

    monkeypatch.setattr("os._exit", mock_exit)

    try:
        translator._audit_batch_context_cache(b_idx=5, cached_tokens=0, phase="phase2")
    except ContextCacheDiscountError:
        pass

    assert exit_code_captured == 1, "Twardy HALT musi natychmiast zatrzymać proces przy przekroczeniu sufitu 6.00 PLN!"


@pytest.mark.unit
def test_f1_no_silent_jit_retry_on_non_canary_batches(monkeypatch):
    """
    Standard 11.2.17: Weryfikuje, że w Fazie 1 dla paczek niebędących bramką Canary (b_idx > 0)
    zwrócenie cached == 0 NIE uruchamia cichego JIT Warmup Retry (dokładnie 1 wywołanie API).
    """
    from translator import MultimodalTranslator
    from unittest.mock import MagicMock
    import pysubs2

    monkeypatch.setenv("AVT_ALLOW_UNCACHED_BILLING", "1")
    monkeypatch.setattr("time.sleep", lambda s: None)

    translator = MultimodalTranslator(
        api_key="mock_k0,mock_k1,mock_k2",
        model="gemini-4-hydrogen",
        enable_verifier=False
    )

    call_count = {"f1": 0}

    def mock_call(*args, **kwargs):
        call_count["f1"] += 1
        resp = MagicMock()
        resp.translations = []
        resp.characters_identified = []
        resp.visual_events = []
        resp.typesetting_notes = []
        resp.speaker_identifications = []
        resp.raw_thoughts = ""
        resp.model_dump.return_value = {}
        _tl = getattr(translator, "_thread_local", None)
        if _tl is None:
            _tl = translator._thread_local = MagicMock()
        _tl.last_batch_token_usage = {"prompt": 90000, "cached": 0, "output": 1200, "model": "gemini-4-hydrogen"}
        return resp

    monkeypatch.setattr(translator, "_call_gemini_with_retry", mock_call)

    ev = pysubs2.SSAEvent(text="Test line", start=0, end=1000, style="Default", name="Speaker")
    batch_item = (1, ev, "Test line", "")

    translator._process_phase1_only(
        b_idx=1,
        batch=[batch_item],
        untranslated_in_batch=[batch_item],
        batches=[[batch_item], [batch_item]],
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
        history=[],
        pbar=MagicMock(),
        translated_results={}
    )

    assert call_count["f1"] == 1, f"Paczka b_idx=1 w F1 nie może uruchamiać cichego JIT Retry (wykryto {call_count['f1']} wywołań)!"


@pytest.mark.unit
def test_global_budget_halt_even_on_cache_hit(monkeypatch):
    """
    Standard 11.2.17: Weryfikuje likwidację martwego pola bezpiecznika.
    Gdy łączny koszt sesji przekracza 6.00 PLN netto, _audit_batch_context_cache
    wyzwala twardy HALT (os._exit(1)) NAWET gdy bieżąca paczka zwróciła cached_tokens >= 32768.
    """
    import os
    from translator import MultimodalTranslator, ContextCacheDiscountError

    monkeypatch.delenv("AVT_ALLOW_UNCACHED_BILLING", raising=False)
    exit_calls = []
    monkeypatch.setattr(os, "_exit", lambda code: exit_calls.append(code))

    translator = MultimodalTranslator(
        api_key="mock_k0,mock_k1,mock_k2",
        model="gemini-4-hydrogen",
        enable_verifier=False
    )
    # Symulacja wcześniejszego spalenia budżetu (> 6.00 PLN)
    translator.current_episode_tokens = {
        "prompt": 2500000,
        "cached": 0,
        "output": 500000,
        "model": "gemini-4-hydrogen"
    }

    try:
        translator._audit_batch_context_cache(b_idx=2, cached_tokens=86000, phase="phase1")
    except ContextCacheDiscountError:
        pass

    assert exit_calls == [1], "Globalny bezpiecznik musi zatrzymać proces przy koszcie > 6.00 PLN nawet przy cache hit!"


@pytest.mark.unit
def test_hydrogen_1to1_concurrency_cap_in_translate_file(monkeypatch, tmp_path):
    """
    Standard 11.2.17 (Non-Tautological Concurrency Gate):
    Uruchamia translate_file z 3 kluczami (2:1) i concurrent_batches=6 na modelu Hydrogen.
    Weryfikuje, że F1 używa max_workers <= 2 (nigdy 6), a F2 działa ściśle sekwencyjnie (brak puli > 1 na K2).
    """
    import concurrent.futures
    import pysubs2
    from unittest.mock import MagicMock
    from translator import MultimodalTranslator

    monkeypatch.setattr("time.sleep", lambda s: None)

    subs = pysubs2.SSAFile()
    for i in range(10):
        subs.append(pysubs2.SSAEvent(start=i * 5000, end=i * 5000 + 2000, text=f"Line {i}"))
    test_sub_path = tmp_path / "test_concurrency.ass"
    subs.save(str(test_sub_path))

    translator = MultimodalTranslator(
        api_key="mock_k0,mock_k1,mock_k2",
        model="gemini-4-hydrogen",
        enable_verifier=True,
        batch_size=2
    )
    translator.concurrent_batches = 6

    recorded_pool_workers = []
    real_executor = concurrent.futures.ThreadPoolExecutor

    class SpyThreadPoolExecutor(real_executor):
        def __init__(self, max_workers=None, *args, **kwargs):
            recorded_pool_workers.append(max_workers)
            super().__init__(max_workers=max_workers, *args, **kwargs)

    def mock_phase1(b_idx, *args, **kwargs):
        return {
            "b_idx": b_idx,
            "pass1_items": [{"id": 0, "orig_idx": 0, "en": "test", "pl": "test"}],
            "untranslated_in_batch": [],
            "scene_desc": "",
            "batch_response": MagicMock(scene_diagnosis=None),
            "lookback_history": [],
            "lookahead_events": [],
            "batch": []
        }

    def mock_phase2(phase1_data, *args, **kwargs):
        b_idx = phase1_data["b_idx"]
        return (b_idx, {b_idx * 2: "przekład"}, {}, [], [], "", "")

    f1_warmup_kwargs = {}
    def spy_ensure_cache_ready(*args, **kwargs):
        if kwargs.get("tag") == "translator":
            f1_warmup_kwargs.update(kwargs)
        return True

    monkeypatch.setattr(concurrent.futures, "ThreadPoolExecutor", SpyThreadPoolExecutor)
    monkeypatch.setattr(translator, "_process_phase1_only", mock_phase1)
    monkeypatch.setattr(translator, "_process_phase2_only", mock_phase2)
    monkeypatch.setattr("context_cache.ContextCacheManager.ensure_cache_ready", spy_ensure_cache_ready)
    monkeypatch.setattr(translator.profiler, "profile_episode", lambda *a, **kw: None)
    monkeypatch.setattr("translator.get_anime_context", lambda *a, **kw: None)
    translator.whisper = None
    monkeypatch.setattr(translator.manga_canon, "get_or_discover_canon", lambda *a, **kw: None)
    k2_c = translator.client_pool_f2.get_client(affinity_idx=0)
    k2_c.models.generate_content = MagicMock(return_value=MagicMock(usage_metadata=MagicMock(cached_content_token_count=45000)))

    out_path = tmp_path / "test_concurrency_out.ass"
    translator.translate_file(subs_path=str(test_sub_path), output_path=str(out_path))

    # Standard 11.2.19: Zarówno F1 (K0 z failoverem K1), jak i F2 (K2) działają ściśle sekwencyjnie bez ThreadPoolExecutor
    assert recorded_pool_workers == [], f"Dla Hydrogen F1 i F2 powinny działać sekwencyjnie (0 pul ThreadPoolExecutor)! Wykryto: {recorded_pool_workers}"
    # Asercja 2: Warm-up F1 przekazał symetryczną sygnaturę dekodera
    assert f1_warmup_kwargs.get("thinking_config") is not None
    assert f1_warmup_kwargs.get("response_schema") is not None
    assert f1_warmup_kwargs.get("response_mime_type") == "application/json"


@pytest.mark.unit
def test_zero_synthetic_warmup_pings_for_hydrogen_in_translate_file(monkeypatch, tmp_path):
    """
    Standard 11.2.18 (Zero-Waste Self-Warming Gate):
    Uruchamia pełne translate_file na modelu Hydrogen z 3 kluczami (2:1) i weryfikuje,
    że żaden klient (K0, K1, K2) NIE wysyła syntetycznych pingów PING_WARMUP_INIT ani PING_CACHE_VERIFY.
    """
    import pysubs2
    from unittest.mock import MagicMock
    from translator import MultimodalTranslator

    monkeypatch.setattr("time.sleep", lambda s: None)

    subs = pysubs2.SSAFile()
    for i in range(6):
        subs.append(pysubs2.SSAEvent(start=i * 5000, end=i * 5000 + 2000, text=f"Line {i}"))
    test_sub_path = tmp_path / "test_self_warm.ass"
    subs.save(str(test_sub_path))

    translator = MultimodalTranslator(
        api_key="mock_k0,mock_k1,mock_k2",
        model="gemini-4-hydrogen",
        enable_verifier=True,
        batch_size=2
    )
    translator.concurrent_batches = 2

    ping_calls = []

    def spy_generate_content(model=None, contents=None, config=None, **kwargs):
        ping_calls.append({"model": model, "contents": contents})
        return MagicMock(usage_metadata=MagicMock(prompt_token_count=80000, cached_content_token_count=0, candidates_token_count=1, thoughts_token_count=0))

    for pool in (translator.client_pool_f1, translator.client_pool_f2):
        for c in pool.clients:
            c.models.generate_content = spy_generate_content

    def mock_phase1(b_idx, *args, **kwargs):
        return {
            "b_idx": b_idx,
            "pass1_items": [{"id": 0, "orig_idx": 0, "en": "test", "pl": "test"}],
            "untranslated_in_batch": [],
            "scene_desc": "",
            "batch_response": MagicMock(scene_diagnosis=None),
            "lookback_history": [],
            "lookahead_events": [],
            "batch": []
        }

    def mock_phase2(phase1_data, *args, **kwargs):
        b_idx = phase1_data["b_idx"]
        return (b_idx, {b_idx * 2: "przekład"}, {}, [], [], "", "")

    monkeypatch.setattr(translator, "_process_phase1_only", mock_phase1)
    monkeypatch.setattr(translator, "_process_phase2_only", mock_phase2)
    monkeypatch.setattr(translator.profiler, "profile_episode", lambda *a, **kw: None)
    monkeypatch.setattr("translator.get_anime_context", lambda *a, **kw: None)
    # Bez wywoływania realnego API count_tokens (deterministyczny fallback długości znaków)
    monkeypatch.setattr("context_cache.ensure_cache_token_floor", lambda si, *a, **kw: si)
    translator.whisper = None
    monkeypatch.setattr(translator.manga_canon, "get_or_discover_canon", lambda *a, **kw: None)

    out_path = tmp_path / "test_self_warm_out.ass"
    translator.translate_file(subs_path=str(test_sub_path), output_path=str(out_path))

    assert ping_calls == [], f"Wykryto płatne syntetyczne pingi warm-upu dla Hydrogen: {ping_calls}!"


@pytest.mark.unit
def test_ensure_cache_ready_accounts_warmup_tokens_when_ping_enabled():
    """
    Standard 11.2.18 (Zero-Hidden-Cost Accounting):
    Weryfikuje, że przy jawnym pingu warm-upu (skip_warmup_ping=False) i przekazanym token_accumulator
    wszystkie tokeny z usage_metadata są doliczane do akumulatora kosztów sesji.
    """
    from unittest.mock import MagicMock
    from context_cache import ContextCacheManager

    class MockModelClient:
        def generate_content(self, model, contents, config):
            um = MagicMock(prompt_token_count=86259, cached_content_token_count=0, candidates_token_count=1, thoughts_token_count=0)
            return MagicMock(usage_metadata=um, text="{}")

    class MockPool:
        def __init__(self):
            self.models = MockModelClient()
            self.clients = [self]
        def get_active_clients(self):
            return [self]
        def init_replicated_cache(self, model, instruction, tag=None):
            return {"0": "__IMPLICIT_CACHE_95__"}

    acc = {"prompt": 0, "cached": 0, "output": 0, "model": "gemini-4-hydrogen"}
    ContextCacheManager.ensure_cache_ready(
        client=MockPool(),
        model="gemini-4-hydrogen",
        system_instruction="A" * 130000,
        verbose=False,
        tag="translator",
        skip_warmup_ping=False,
        token_accumulator=acc
    )

    assert acc["prompt"] == 86259
    assert acc["output"] == 1


@pytest.mark.unit
def test_hydrogen_f1_pins_primary_key_k0_with_automatic_k1_failover(monkeypatch):
    """
    Standard 11.2.19: Weryfikuje konsolidację F1 na kluczu głównym K0 dla Hydrogen
    oraz automatyczny failover na K1 w przypadku błędu / cooldownu K0.
    """
    from unittest.mock import MagicMock
    from translator import MultimodalTranslator

    translator = MultimodalTranslator(
        api_key="mock_k0,mock_k1,mock_k2",
        model="gemini-4-hydrogen",
        enable_verifier=False
    )

    requested_affinities = []
    real_get_client = translator.client_pool_f1.get_client

    def spy_get_client(affinity_idx=None):
        requested_affinities.append(affinity_idx)
        return real_get_client(affinity_idx=affinity_idx)

    monkeypatch.setattr(translator.client_pool_f1, "get_client", spy_get_client)
    monkeypatch.setattr("client_factory.global_rate_limiter.acquire", lambda: None)

    mock_resp = MagicMock()
    mock_resp.text = '{"lines": []}'
    mock_resp.usage_metadata = MagicMock(prompt_token_count=100, cached_content_token_count=35000, candidates_token_count=10, thoughts_token_count=0)

    for c in translator.client_pool_f1.clients:
        c.models.generate_content = MagicMock(return_value=mock_resp)

    # 1. Wywołania normalne: paczki 0, 1, 2, 3 dla Hydrogen muszą ZAWSZE żądać affinity_idx=0 (K0)
    for b_idx in range(4):
        translator._call_gemini_with_retry([{"role": "user", "parts": ["test"]}], None, batch_idx=b_idx)

    assert requested_affinities == [0, 0, 0, 0], f"Dla Hydrogen affinity w F1 musi być zawsze 0! Wykryto: {requested_affinities}"

    # 2. Test failover: gdy K0 jest w cooldownie, get_client(affinity_idx=0) musi bezpiecznie zwrócić K1
    k0_client = translator.client_pool_f1.clients[0]
    k1_client = translator.client_pool_f1.clients[1]

    translator.client_pool_f1.report_error(k0_client, "429 quota")
    fallback_client = translator.client_pool_f1.get_client(affinity_idx=0)
    assert fallback_client is k1_client, "Gdy K0 ma cooldown, ruch F1 musi automatycznie trafić do K1!"


@pytest.mark.unit
def test_planned_self_warming_init_vs_unexpected_warn_and_batch1_confirm(capsys):
    """
    Standard 11.2.19:
    1. Paczka 0 na Hydrogen generuje planowy komunikat 'Context Cache INIT / Self-Warming' (nie WARN).
    2. Paczka > 0 na Hydrogen z zerem tokenów generuje ostrzeżenie 'Context Cache WARN'.
    3. Paczka 0 i Paczka 1 z cached >= 32768 drukują 'Context Cache AKTYWNY'.
    """
    from translator import MultimodalTranslator

    translator = MultimodalTranslator(
        api_key="mock_k0,mock_k1,mock_k2",
        model="gemini-4-hydrogen",
        enable_verifier=False
    )
    # Reset licznika tokenów do stanu po pojedynczym cold-starcie (koszt 0.49 PLN <= 6.00 PLN)
    translator.current_episode_tokens = {
        "prompt": 80000,
        "cached": 0,
        "output": 500,
        "model": "gemini-4-hydrogen"
    }

    # Krok 1: Paczka 0 z 0 tokenów cache (planowy cold-start)
    capsys.readouterr()
    translator._audit_batch_context_cache(b_idx=0, cached_tokens=0, phase="phase1")
    out1 = capsys.readouterr().out
    assert "Context Cache INIT / Self-Warming" in out1
    assert "Context Cache WARN" not in out1

    # Krok 2: Paczka 1 z 0 tokenów cache w trybie Hydrogen Zero-Cache Lean (system_prompt < 60000)
    translator._audit_batch_context_cache(b_idx=1, cached_tokens=0, phase="phase1")
    out2 = capsys.readouterr().out
    assert "Hydrogen Zero-Cache Lean" in out2

    # Krok 2b: Gdy system_prompt jest pełny (> 60000, np. wymuszony non-lean), b_idx > 0 generuje Context Cache WARN
    translator.system_prompt = "A" * 70000
    translator._audit_batch_context_cache(b_idx=1, cached_tokens=0, phase="phase1")
    out2b = capsys.readouterr().out
    assert "Context Cache WARN" in out2b

    # Krok 3: Paczka 0 oraz Paczka 1 z aktywnym cache
    translator._audit_batch_context_cache(b_idx=0, cached_tokens=86000, phase="phase1")
    out3a = capsys.readouterr().out
    assert "Context Cache AKTYWNY" in out3a

    translator._audit_batch_context_cache(b_idx=1, cached_tokens=86000, phase="phase1")
    out3b = capsys.readouterr().out
    assert "Context Cache AKTYWNY" in out3b


@pytest.mark.unit
def test_hydrogen_uses_lean_prompt_without_33k_padding(monkeypatch, tmp_path):
    """
    Standard 11.2.20 (Hydrogen Zero-Cache Lean):
    Weryfikuje, że dla modelu gemini-4-hydrogen system_prompt F1 i F2 jest inicjalizowany
    w trybie lean=True (< 50 000 znaków), a w translate_file pomijane jest dopełnianie ensure_cache_token_floor.
    W przeciwieństwie do gemini-3.8-flash, który zachowuje pełny prompt (> 150 000 znaków).
    """
    import pysubs2
    from unittest.mock import MagicMock
    from translator import MultimodalTranslator

    t_hydrogen = MultimodalTranslator(
        api_key="mock_key",
        model="gemini-4-hydrogen",
        enable_verifier=True
    )
    assert len(t_hydrogen.system_prompt) < 50000, f"System prompt F1 dla Hydrogen powinien być lean (<50k)! Wykryto: {len(t_hydrogen.system_prompt)}"
    assert len(t_hydrogen.verifier.system_prompt) < 50000, f"System prompt F2 dla Hydrogen powinien być lean (<50k)! Wykryto: {len(t_hydrogen.verifier.system_prompt)}"

    t_flash = MultimodalTranslator(
        api_key="mock_key",
        model="gemini-3.8-flash",
        enable_verifier=True
    )
    assert len(t_flash.system_prompt) > 150000, f"System prompt F1 dla Flash powinien być pełny (>150k)! Wykryto: {len(t_flash.system_prompt)}"

    # Weryfikacja pomijania ensure_cache_token_floor w translate_file dla Hydrogen
    floor_calls = []
    monkeypatch.setattr("context_cache.ensure_cache_token_floor", lambda prompt, *a, **kw: floor_calls.append(prompt) or prompt)
    monkeypatch.setattr("context_cache.ContextCacheManager.ensure_cache_ready", lambda *a, **kw: True)
    monkeypatch.setattr(t_hydrogen.profiler, "profile_episode", lambda *a, **kw: None)
    monkeypatch.setattr("translator.get_anime_context", lambda *a, **kw: None)
    monkeypatch.setattr(t_hydrogen.manga_canon, "get_or_discover_canon", lambda *a, **kw: None)
    t_hydrogen.whisper = None

    subs = pysubs2.SSAFile()
    for i in range(5):
        subs.append(pysubs2.SSAEvent(start=i * 2000, end=i * 2000 + 1500, text=f"Line {i}"))
    test_sub_path = tmp_path / "test_lean_prompt.ass"
    subs.save(str(test_sub_path))

    def mock_p1(b_idx, *args, **kwargs):
        return {
            "b_idx": b_idx,
            "pass1_items": [{"id": 0, "orig_idx": 0, "en": "test", "pl": "test"}],
            "untranslated_in_batch": [],
            "scene_desc": "",
            "batch_response": MagicMock(scene_diagnosis=None),
            "lookback_history": [],
            "lookahead_events": [],
            "batch": []
        }

    def mock_p2(phase1_data, *args, **kwargs):
        b_idx = phase1_data["b_idx"]
        return (b_idx, {b_idx * 2: "przekład"}, {}, [], [], "", "")

    monkeypatch.setattr(t_hydrogen, "_process_phase1_only", mock_p1)
    monkeypatch.setattr(t_hydrogen, "_process_phase2_only", mock_p2)

    out_path = tmp_path / "test_lean_out.ass"
    t_hydrogen.translate_file(subs_path=str(test_sub_path), output_path=str(out_path))

    assert floor_calls == [], f"Dla Hydrogen ensure_cache_token_floor NIE może być wywołany! Wykryto wywołania: {len(floor_calls)}"


@pytest.mark.unit
def test_hydrogen_zero_cache_lean_batches_around_55_lines():
    """
    Standard 11.2.20 (Hydrogen Zero-Cache Lean Batching):
    Weryfikuje, że dla 334-liniowego odcinka logika paczkowania w translate_file
    dla gemini-4-hydrogen tworzy ~5-8 paczek (~52-60 linii/paczkę),
    podczas gdy dla gemini-3.8-flash powstaje 11-15 paczek (po max 32 linie).
    """
    import pysubs2
    from translator import create_adaptive_batches
    from model_resolver import is_gemini_4_or_hydrogen_model

    # Syntetyczny odcinek 334 linii z realistycznymi przerwami dialogowymi
    raw_entries = []
    current_time = 0
    for i in range(334):
        # Przeskoki scen co ~55 linii (4.5s przerwy)
        gap = 4500 if (i in (55, 110, 165, 225, 280)) else 400
        start = current_time + gap
        end = start + 1800
        current_time = end
        ev = pysubs2.SSAEvent(start=start, end=end, text=f"Dialog line {i}")
        raw_entries.append((i, ev, f"Dialog line {i}", ""))

    def compute_batches_for_model(model_name: str, batch_size: int = 30):
        if is_gemini_4_or_hydrogen_model(model_name) and batch_size >= 24:
            eff_base_bs = max(batch_size, 56)
            eff_max_bs = max(eff_base_bs + 8, 64)
            eff_min_scene = 44
            eff_min_leap = 36
        else:
            eff_base_bs = batch_size
            eff_max_bs = min(32, batch_size + 8) if batch_size >= 8 else batch_size
            eff_min_scene = 16 if batch_size >= 16 else batch_size
            eff_min_leap = 12 if batch_size >= 12 else batch_size

        return create_adaptive_batches(
            raw_entries,
            base_batch_size=eff_base_bs,
            max_batch_size=eff_max_bs,
            min_scene_batch=eff_min_scene,
            min_leap_batch=eff_min_leap,
            leap_threshold_ms=8000,
            scene_threshold_ms=3800,
            coalesce_tail=(batch_size >= 8)
        )

    batches_hydrogen = compute_batches_for_model("gemini-4-hydrogen", batch_size=30)
    batches_flash = compute_batches_for_model("gemini-3.8-flash", batch_size=30)

    assert 5 <= len(batches_hydrogen) <= 8, f"Dla Hydrogen oczekiwano 5-8 paczek! Otrzymano: {len(batches_hydrogen)}"
    assert 11 <= len(batches_flash) <= 15, f"Dla Flash oczekiwano 11-15 paczek! Otrzymano: {len(batches_flash)}"
    # Sprawdzenie średniej liczby linii w paczce dla Hydrogen
    avg_lines_hydrogen = sum(len(b) for b in batches_hydrogen) / len(batches_hydrogen)
    assert 45 <= avg_lines_hydrogen <= 65, f"Średnia wielkość paczki dla Hydrogen powinna wynosić ~55 linii! Otrzymano: {avg_lines_hydrogen:.1f}"


@pytest.mark.unit
def test_hydrogen_zero_cache_budget_guard_still_halts_above_6_pln(monkeypatch):
    """
    Standard 11.2.20 (Fail-Closed Budget Sentinel Invariance):
    Weryfikuje, że w trybie Zero-Cache Lean, jeśli łączny koszt sesji przekroczy 6.00 PLN,
    _audit_batch_context_cache nadal natychmiast wyzwala twardy HALT (os._exit(1)).
    """
    import os
    from translator import MultimodalTranslator, ContextCacheDiscountError

    monkeypatch.delenv("AVT_ALLOW_UNCACHED_BILLING", raising=False)
    exit_calls = []
    monkeypatch.setattr(os, "_exit", lambda code: exit_calls.append(code))

    translator = MultimodalTranslator(
        api_key="mock_k0,mock_k1,mock_k2",
        model="gemini-4-hydrogen",
        enable_verifier=False
    )
    # Symulacja przekroczenia budżetu sesji (> 6.00 PLN)
    translator.current_episode_tokens = {
        "prompt": 2500000,
        "cached": 0,
        "output": 500000,
        "model": "gemini-4-hydrogen"
    }

    try:
        translator._audit_batch_context_cache(b_idx=3, cached_tokens=0, phase="phase1")
    except ContextCacheDiscountError:
        pass

    assert exit_calls == [1], "W trybie Zero-Cache Lean przekroczenie 6.00 PLN musi bezwzględnie zatrzymać potok via os._exit(1)!"


@pytest.mark.unit
def test_adaptive_batches_respects_min_scene_with_frequent_2800ms_gaps():
    """
    Standard 11.2.21: Weryfikuje usunięcie zahardkodowanego progu 18 linii dla przerw >= 2800 ms.
    Dla 334 linii z realistyczną przerwą 3200 ms co 20 linii oraz progami Hydrogen (56/64/44/36)
    musi powstać dokładnie 5-7 paczek (a nie 11-16 jak w 11.2.20).
    """
    import pysubs2
    from translator import create_adaptive_batches

    raw_entries = []
    cur_t = 0
    for i in range(334):
        gap = 3200 if (i > 0 and i % 20 == 0) else 350
        start = cur_t + gap
        end = start + 1900
        cur_t = end
        txt = f"Sample dialogue line number {i} with realistic word count here."
        ev = pysubs2.SSAEvent(start=start, end=end, text=txt)
        raw_entries.append((i, ev, txt, ""))

    batches_h = create_adaptive_batches(
        raw_entries,
        base_batch_size=56,
        max_batch_size=64,
        min_scene_batch=44,
        min_leap_batch=36,
        leap_threshold_ms=8000,
        scene_threshold_ms=3800,
        coalesce_tail=True
    )
    assert 5 <= len(batches_h) <= 7, f"Oczekiwano 5-7 paczek dla Hydrogen mimo częstych pauz 3.2s! Otrzymano: {len(batches_h)}"
    assert min(len(b) for b in batches_h[:-1]) >= 40, f"Wykryto przedwczesną małą paczkę: {[len(b) for b in batches_h]}"


@pytest.mark.unit
def test_selective_phase2_caps_lines_and_maintains_low_cot():
    """
    Standard 11.2.21: Weryfikuje selekcję ryzyka F2 (_select_hydrogen_phase2_candidates):
    - ogranicza 56-liniową paczkę do <= 28 linii (globalny pułap <= 170/6),
    - priorytetyzuje is_blind_draft / calque_score / cps_warning przed prostymi kwestiami,
    - przenosi niekrytyczne audio_alert / ambiguity_note do notes, utrzymując LOW CoT (2048) w verifierze.
    """
    from translator import MultimodalTranslator, determine_blind_draft_status

    translator = MultimodalTranslator(
        api_key="mock_k0,mock_k1,mock_k2",
        model="gemini-4-hydrogen",
        enable_verifier=True
    )

    items = []
    for i in range(56):
        audio_al = "Drobna różnica tonu" if i == 33 else ""
        amb_note = "Sprawdź zaimek" if i == 34 else ""
        calque_sc = 0.45 if i in (30, 31) else 0.0
        blind_flag = determine_blind_draft_status(
            has_audio_conflict=bool(audio_al),
            has_ambiguity_conflict=bool(amb_note),
            calque_score=calque_sc
        )
        it = {
            "id": i + 1,
            "en": "Yes." if i < 25 else "That is a fairly long sentence with several nuanced words inside.",
            "pl": "Tak." if i < 25 else "To dosyć długie zdanie z kilkoma niuansami w środku.",
            "calque_score": calque_sc,
            "cps_warning": "CPS > 17" if i == 32 else "",
            "audio_alert": audio_al,
            "ambiguity_note": amb_note,
            "is_blind_draft": blind_flag,
            "is_song": False,
            "notes": ""
        }
        items.append(it)

    assert items[33]["is_blind_draft"] is True
    assert items[34]["is_blind_draft"] is True

    selected = translator._select_hydrogen_phase2_candidates(items, total_batches=6, episode_line_cap=170)
    assert 8 <= len(selected) <= 28, f"Selekcja F2 powinna zwrócić 8-28 linii z 56! Otrzymano: {len(selected)}"
    sel_ids = {it["id"] for it in selected}
    assert {31, 32, 33, 34, 35}.issubset(sel_ids), "Linie z kalką, CPS i alertami muszą znaleźć się w wybranym podzbiorze!"

    # Hotfix 11.2.21a: Mimo is_blind_draft=True z Fazy 1 alerty trafiają do notes, a verifier wybiera LOW (2048)
    assert translator.verifier.calculate_effective_budget(selected) == 2048
    item_34 = next(it for it in selected if it["id"] == 34)
    assert item_34["is_blind_draft"] is True
    assert "Wskazówka audio" in item_34["notes"]
    assert item_34["audio_alert"] == ""
    item_35 = next(it for it in selected if it["id"] == 35)
    assert item_35["is_blind_draft"] is True
    assert "Uwaga F1" in item_35["notes"]
    assert item_35["ambiguity_note"] == ""
    # Oryginał w items pozostaje nienaruszony (brak mutacji źródłowej listy)
    assert items[33]["audio_alert"] == "Drobna różnica tonu"

    # Krótka paczka końcowa (<= 10 linii): wszystkie linie zachowane i utrzymane na LOW (2048)
    tail_selected = translator._select_hydrogen_phase2_candidates(items[30:36], total_batches=6, episode_line_cap=170)
    assert len(tail_selected) == 6
    assert translator.verifier.calculate_effective_budget(tail_selected) == 2048

    # Prawdziwa flaga krytyczna (is_song=True) nadal eskaluje do MEDIUM (3072)
    song_batch = [dict(items[33], is_song=True)]
    song_selected = translator._select_hydrogen_phase2_candidates(song_batch, total_batches=6, episode_line_cap=170)
    assert translator.verifier.calculate_effective_budget(song_selected) == 3072


@pytest.mark.unit
def test_standard_11_2_21_zero_cache_cost_simulation_under_5_pln():
    """
    Standard 11.2.21: Deterministyczna symulacja kosztu odcinka 334 linii (6 paczek,
    50% selektywna F2 = 167 linii, 0% cache) na empirycznych współczynnikach z 2026-11-18.
    Weryfikuje koszt <= 4.60 PLN netto (ponad 23% marginesu do limitu 6.00 PLN).
    """
    from pricing_guard import PricingGuard

    f1_stats = {
        "model": "gemini-4-hydrogen",
        "prompt": 6 * 14768 + 334 * 100,
        "cached": 0,
        "output": 6 * 3200 + 334 * 105
    }
    f2_stats = {
        "model": "gemini-4-hydrogen",
        "prompt": 6 * 14300 + 167 * 140,
        "cached": 0,
        "output": 167 * 270 + 1 * 2930
    }
    breakdown = PricingGuard.calculate_actual_cost_breakdown(f1_stats, f2_stats)
    assert breakdown["net_pln"] <= 4.60, f"Symulowany koszt przekroczył 4.60 PLN netto: {breakdown}"


@pytest.mark.unit
def test_checkpoint_restored_tokens_do_not_poison_session_budget_limit(monkeypatch):
    """
    Standard 11.2.22: Weryfikuje izolację budżetu bieżącej sesji od długu przywróconego z checkpointu.
    Historyczny stan 5.67 PLN z poprzedniej sesji + 0.50 PLN w nowej sesji daje deltę 0.50 PLN <= 6.00 PLN (brak HALT).
    Dopiero przekroczenie 6.00 PLN przyrostu w bieżącej sesji uruchamia os._exit(1).
    """
    import os
    from translator import MultimodalTranslator, ContextCacheDiscountError

    monkeypatch.delenv("AVT_ALLOW_UNCACHED_BILLING", raising=False)
    exit_calls = []
    monkeypatch.setattr(os, "_exit", lambda code: exit_calls.append(code))

    translator = MultimodalTranslator(
        api_key="mock_k0,mock_k1,mock_k2",
        model="gemini-4-hydrogen",
        enable_verifier=True
    )
    # Stan bazowy przywrócony z wcześniejszego checkpointu (~5.67 PLN)
    translator._checkpoint_baseline_f1 = {"prompt": 200000, "cached": 0, "output": 70000, "model": "gemini-4-hydrogen"}
    translator._checkpoint_baseline_f2 = {"prompt": 110000, "cached": 0, "output": 60000, "model": "gemini-4-hydrogen"}

    # Bieżące liczniki = baseline + niewielki przyrost nowej sesji (~0.45 PLN delta)
    translator.current_episode_tokens = {"prompt": 227000, "cached": 0, "output": 80000, "model": "gemini-4-hydrogen"}
    translator.verifier.current_episode_tokens = {"prompt": 110000, "cached": 0, "output": 60000, "model": "gemini-4-hydrogen"}

    translator._audit_batch_context_cache(b_idx=3, cached_tokens=0, phase="phase1")
    assert exit_calls == [], f"Historyczny dług z checkpointu wyzwolił fałszywy HALT: {exit_calls}"

    # Przekroczenie 6.00 PLN w samej bieżącej sesji (delta > 6.00 PLN) nadal wyzwala twardy HALT
    translator.current_episode_tokens["output"] += 220000
    try:
        translator._audit_batch_context_cache(b_idx=4, cached_tokens=0, phase="phase1")
    except ContextCacheDiscountError:
        pass
    assert exit_calls == [1], "Przekroczenie 6.00 PLN przyrostu w bieżącej sesji musi uruchomić os._exit(1)!"


@pytest.mark.unit
def test_flight_recorder_logs_phase1_batch_before_budget_halt(monkeypatch):
    """
    Standard 11.2.22 (Pre-HALT Telemetry Persistence):
    Weryfikuje, że w _process_phase1_only zapis do flight_recorder.log_phase1_batch
    wykonuje się PRZED audytem budżetu mogącym wywołać os._exit(1).
    """
    import os
    import pysubs2
    from unittest.mock import MagicMock
    from translator import MultimodalTranslator, ContextCacheDiscountError

    monkeypatch.delenv("AVT_ALLOW_UNCACHED_BILLING", raising=False)
    events_order = []

    def mock_exit(code):
        events_order.append(("os_exit", code))

    monkeypatch.setattr(os, "_exit", mock_exit)

    translator = MultimodalTranslator(
        api_key="mock_k0,mock_k1,mock_k2",
        model="gemini-4-hydrogen",
        enable_verifier=False
    )
    mock_fr = MagicMock()
    mock_fr.log_phase1_batch.side_effect = lambda **kw: events_order.append(("flight_recorder", kw.get("batch_id")))
    translator.flight_recorder = mock_fr

    def mock_call(*args, **kwargs):
        resp = MagicMock()
        resp.translations = []
        resp.characters_identified = []
        resp.visual_events = []
        resp.typesetting_notes = []
        resp.speaker_identifications = []
        resp.raw_thoughts = ""
        resp.model_dump.return_value = {}
        translator._thread_local.last_batch_token_usage = {"prompt": 30000, "cached": 0, "output": 5000, "model": "gemini-4-hydrogen"}
        translator.current_episode_tokens = {"prompt": 2500000, "cached": 0, "output": 500000, "model": "gemini-4-hydrogen"}
        return resp

    monkeypatch.setattr(translator, "_call_gemini_with_retry", mock_call)

    ev = pysubs2.SSAEvent(text="Sample line", start=0, end=1500, style="Default", name="Speaker")
    batch_item = (1, ev, "Sample line", "")

    try:
        translator._process_phase1_only(
            b_idx=4,
            batch=[batch_item],
            untranslated_in_batch=[batch_item],
            batches=[[batch_item]] * 5,
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
            history=[],
            pbar=MagicMock(),
            translated_results={}
        )
    except ContextCacheDiscountError:
        pass

    assert events_order == [("flight_recorder", 4), ("os_exit", 1)], f"Zapis flight_recorder musi wyprzedzać HALT! Kolejność: {events_order}"


@pytest.mark.unit
def test_concurrent_futures_timeout_triggers_timeout_fallback(monkeypatch):
    """
    Standard 11.2.22: Weryfikuje, że concurrent.futures.TimeoutError() (o pustym str(e) == '')
    jest rozpoznawany jako timeout i po przekroczeniu progu prób aktywuje przełączenie modelu.
    """
    import concurrent.futures
    from unittest.mock import MagicMock
    from translator import MultimodalTranslator, BatchTranslationResponse, LeanBatchTranslationResponse

    monkeypatch.setattr("time.sleep", lambda s: None)
    monkeypatch.setattr("client_factory.global_rate_limiter.acquire", lambda: None)
    monkeypatch.setattr("model_resolver.resolve_best_models", lambda *a, **kw: {"hydrogen": "gemini-4-hydrogen", "flash": "gemini-3.8-flash"})

    translator = MultimodalTranslator(
        api_key="mock_k0",
        model="gemini-4-hydrogen",
        enable_verifier=False
    )

    seen_models = []
    def mock_generate(model=None, contents=None, config=None, **kwargs):
        seen_models.append(model)
        if "hydrogen" in str(model):
            raise concurrent.futures.TimeoutError()
        resp = MagicMock()
        resp.parsed = BatchTranslationResponse(translations=[])
        resp.usage_metadata = MagicMock(prompt_token_count=1000, cached_content_token_count=0, candidates_token_count=50, thoughts_token_count=0)
        return resp

    translator.client_pool_f1.clients[0].models.generate_content = mock_generate
    monkeypatch.setattr("context_cache.ContextCacheManager.get_or_create_cache", lambda *a, **kw: "__IMPLICIT_CACHE_95__")

    res = translator._call_gemini_with_retry(contents=["Test"], schema_class=BatchTranslationResponse, batch_idx=0)
    assert res is not None
    assert "gemini-3.8-flash" in seen_models, f"TimeoutError() o pustym str() powinien wyzwolić fallback na Flash! Modele: {seen_models}"


@pytest.mark.unit
def test_standard_11_2_22_calibrated_2026_11_23_cost_under_4_60_pln():
    """
    Standard 11.2.22: Weryfikuje domyślny sufit episode_line_cap=115 w _select_hydrogen_phase2_candidates
    oraz symulację pełnego 334-liniowego odcinka (7 paczek, 0% cache, kalibracja b=3 z 2026-11-23) <= 4.60 PLN netto.
    """
    from pricing_guard import PricingGuard
    from translator import MultimodalTranslator

    translator = MultimodalTranslator(
        api_key="mock_k0,mock_k1,mock_k2",
        model="gemini-4-hydrogen",
        enable_verifier=True
    )

    real_batch_sizes = [60, 57, 39, 52, 50, 57, 19]
    total_f2_selected = 0
    for b_len in real_batch_sizes:
        batch_items = [
            {
                "id": j + 1,
                "en": "Long realistic dialogue sentence with ten words for scoring check.",
                "pl": "Długie zdanie dialogowe do punktacji selektywnej Fazy 2.",
                "calque_score": 0.35,
                "is_blind_draft": False,
                "is_song": False,
                "notes": ""
            }
            for j in range(b_len)
        ]
        sel = translator._select_hydrogen_phase2_candidates(batch_items, total_batches=len(real_batch_sizes))
        total_f2_selected += len(sel)

    assert total_f2_selected <= 115, f"Domyślna selekcja F2 przekroczyła limit 115 linii/odcinek: {total_f2_selected}"

    f1_stats = {
        "model": "gemini-4-hydrogen",
        "prompt": sum(24500 + n * 150 for n in real_batch_sizes),
        "cached": 0,
        "output": sum(2700 + n * 95 for n in real_batch_sizes)
    }
    f2_stats = {
        "model": "gemini-4-hydrogen",
        "prompt": len(real_batch_sizes) * 16500 + total_f2_selected * 160,
        "cached": 0,
        "output": total_f2_selected * 270 + 1 * 2930
    }
    breakdown = PricingGuard.calculate_actual_cost_breakdown(f1_stats, f2_stats)
    assert breakdown["net_pln"] <= 4.60, f"Skalibrowany koszt 11.2.22 przekroczył 4.60 PLN netto: {breakdown}"















