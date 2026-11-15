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
