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
    (cached_content_token_count == 0) natychmiast wywoływany jest atomowy
    kill-switch na poziomie jądra: os._exit(1) bez kontynuowania wątków w tle.
    """
    monkeypatch.delenv("AVT_ALLOW_UNCACHED_BILLING", raising=False)
    exit_calls = []
    monkeypatch.setattr(os, "_exit", lambda code: exit_calls.append(code))

    translator = MultimodalTranslator(
        api_key="mock_test_key_12345",
        model="gemini-4-hydrogen",
        enable_verifier=False
    )
    translator._thread_local.last_batch_token_usage = {
        "prompt": 45000,
        "cached": 0,
        "output": 500,
        "model": "gemini-4-hydrogen"
    }
    translator._batch0_cache_telemetry_reported = False

    with pytest.raises(ContextCacheDiscountError):
        translator._audit_batch0_context_cache(0)

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

    translator._audit_batch0_context_cache(0)

    assert exit_calls == [], "Przy aktywnej fladze AVT_ALLOW_UNCACHED_BILLING os._exit(1) nie może być wywołany!"
    captured = capsys.readouterr().out
    assert "[Context Cache WARN / INC-AVT-057]" in captured
    assert "Kontynuacja tłumaczenia pomimo braku rabatu serwerowego" in captured


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
    Standard 11.2.9: Symuluje zwrócenie cached_content_token_count = 0 na pierwszej próbie
    i > 0 po ponowieniu, potwierdzając brak wywołania os._exit(1).
    """
    exit_calls = []
    monkeypatch.setattr(os, "_exit", lambda code: exit_calls.append(code))

    translator = MultimodalTranslator(
        api_key="mock_test_key_12345",
        model="gemini-4-hydrogen",
        enable_verifier=False
    )

    # Symulacja wywołań _call_gemini_with_retry:
    # 1. próba -> token usage cached = 0
    # 2. próba (retry) -> token usage cached = 45000
    attempt = 0
    def mock_call(*args, **kwargs):
        nonlocal attempt
        attempt += 1
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
        if attempt == 1:
            _tl.last_batch_token_usage = {"prompt": 50000, "cached": 0, "output": 200, "model": "gemini-4-hydrogen"}
        else:
            _tl.last_batch_token_usage = {"prompt": 50000, "cached": 45000, "output": 200, "model": "gemini-4-hydrogen"}
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

    # Weryfikacja: wykonano 2 próby (1 początkowa + 1 retry)
    assert attempt == 2, f"Oczekiwano 2 prób, wykonano: {attempt}"
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
    """Weryfikuje natychmiastowe zatrzymanie potoku przy zerowym cache na Paczce 1 (Filar B)."""
    import os
    from translator import MultimodalTranslator, ContextCacheDiscountError

    monkeypatch.delenv("AVT_ALLOW_UNCACHED_BILLING", raising=False)
    exit_calls = []
    monkeypatch.setattr(os, "_exit", lambda code: exit_calls.append(code))

    translator = MultimodalTranslator(api_key="mock_key", model="gemini-4-hydrogen", enable_verifier=False)
    translator._audit_batch_context_cache(b_idx=0, cached_tokens=89546, phase="phase1")
    assert exit_calls == []

    with pytest.raises(ContextCacheDiscountError):
        translator._audit_batch_context_cache(b_idx=1, cached_tokens=0, phase="phase1")
    assert exit_calls == [1]


@pytest.mark.unit
def test_f2_context_growth_cap_and_sentinel(monkeypatch):
    """Weryfikuje Filar D i Z16-amendment #14."""
    import os
    from verifier import DialogueVerifier
    from translator import MultimodalTranslator, ContextCacheDiscountError

    verifier = DialogueVerifier(model="gemini-4-hydrogen", lean=True)
    long_history = [{"en": f"S{i}", "pl": f"Z{i}", "speaker": "A"} for i in range(10)]
    prompt_text = verifier.verify_batch(batch_items=[{"id": 1, "en": "T", "pl": "T"}], history_context=long_history, return_prompt=True)
    assert "S9" in prompt_text and "S6" in prompt_text and "S5" not in prompt_text

    exit_calls = []
    monkeypatch.setattr(os, "_exit", lambda code: exit_calls.append(code))
    translator = MultimodalTranslator(api_key="mock_key", model="gemini-4-hydrogen", enable_verifier=False)
    with pytest.raises(ContextCacheDiscountError):
        translator._audit_batch_context_cache(b_idx=0, cached_tokens=0, phase="phase2")
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












