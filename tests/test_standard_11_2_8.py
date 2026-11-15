# -*- coding: utf-8 -*-
"""
Testy regresyjne i integracyjne Standardu 11.2.8 (T11.2.8):
1. test_t11_2_8_adaptive_f1_thinking_budget: Adaptacyjny poziom myślenia Fazy 1 (3072 CoT dla <=360 linii, 0 CoT dla >360 linii).
2. test_t11_2_8_anilist_resilience_and_lexicon_fallback: Nagłówki User-Agent/Origin/Referer i fallback do leksykonów (INC-AVT-056).
3. test_t11_2_8_pricing_guard_f1_thinking_sync: Synchronizacja PricingGuard z poziomem CoT Fazy 1 (LOW ~2.21 PLN, MEDIUM ~3.32 PLN).
4. test_t11_2_8_cache_ui_telemetry_gate: Bramka telemetrii rzeczywistego cache, Hard Halt (ContextCacheDiscountError) i eliminacja Phantom Cache Discount (INC-AVT-057).
5. test_t11_2_8_cache_ui_telemetry_bypass: Weryfikacja flagi obejścia AVT_ALLOW_UNCACHED_BILLING=1.
6. test_t11_2_8_multi_season_bible_hygiene: Izolacja wielosezonowa w _resolve_bible_path i higiena baz SeriesBible (INC-AVT-058).
"""

import json
import os
import urllib.error
import urllib.request
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from metadata import ExternalGenderResolver
from pricing_guard import PricingGuard
from series_memory import SeriesBible
from translator import MultimodalTranslator, ContextCacheDiscountError, _resolve_bible_path


@pytest.mark.unit
def test_t11_2_8_adaptive_f1_thinking_budget():
    """
    Weryfikuje adaptacyjne wyznaczanie budżetu CoT Fazy 1 w MultimodalTranslator:
    - tryb 'auto': 300 linii -> 3072 CoT (MEDIUM), 500 linii -> 0 CoT (LOW)
    - tryb 'medium': wymuszenie 3072 CoT niezależnie od liczby linii
    - tryb 'low': wymuszenie 0 CoT niezależnie od liczby linii.
    """
    # 1. Tryb auto: 300 linii -> MEDIUM (3072)
    t_auto = MultimodalTranslator(
        api_key="synthetic_api_key_test_12345",
        model="gemini-4-hydrogen",
        enable_verifier=False,
        thinking_f1="auto"
    )
    b_300 = t_auto.resolve_f1_thinking_budget(300)
    assert b_300 == 3072, f"Oczekiwano budżetu 3072 dla 300 linii, otrzymano: {b_300}"
    assert t_auto.phase1_thinking_budget == 3072

    # Tryb auto: 500 linii -> LOW (0)
    b_500 = t_auto.resolve_f1_thinking_budget(500)
    assert b_500 == 0, f"Oczekiwano budżetu 0 dla 500 linii, otrzymano: {b_500}"
    assert t_auto.phase1_thinking_budget == 0

    # 2. Tryb jawny medium: wymusza 3072 nawet przy 500 liniach
    t_med = MultimodalTranslator(
        api_key="synthetic_api_key_test_12345",
        model="gemini-4-hydrogen",
        enable_verifier=False,
        thinking_f1="medium"
    )
    b_med = t_med.resolve_f1_thinking_budget(500)
    assert b_med == 3072, f"Oczekiwano wymuszonego budżetu 3072 w trybie medium, otrzymano: {b_med}"
    assert t_med.phase1_thinking_budget == 3072

    # 3. Tryb jawny low: wymusza 0 nawet przy 300 liniach
    t_low = MultimodalTranslator(
        api_key="synthetic_api_key_test_12345",
        model="gemini-4-hydrogen",
        enable_verifier=False,
        thinking_f1="low"
    )
    b_low = t_low.resolve_f1_thinking_budget(300)
    assert b_low == 0, f"Oczekiwano wymuszonego budżetu 0 w trybie low, otrzymano: {b_low}"
    assert t_low.phase1_thinking_budget == 0


@pytest.mark.unit
def test_t11_2_8_anilist_resilience_and_lexicon_fallback(monkeypatch, tmp_path):
    """
    Weryfikuje obecność nagłówków User-Agent, Origin i Referer w zleceniu GraphQL
    oraz poprawność deterministycznego fallbacku do lokalnych leksykonów fansuberskich (INC-AVT-056).
    """
    captured_requests = []

    def mock_urlopen(req, timeout=3.0):
        captured_requests.append(req)
        # Symulacja błędu sieciowego HTTP 404 (odrzucenie przez węzeł brzegowy)
        raise urllib.error.HTTPError(
            url="https://graphql.anilist.co",
            code=404,
            msg="Not Found",
            hdrs={},
            fp=None
        )

    monkeypatch.setattr(urllib.request, "urlopen", mock_urlopen)

    # Przygotowanie izolowanego leksykonu w tmp_path
    synthetic_lex_dir = tmp_path / "fansub_lexicons"
    synthetic_lex_dir.mkdir(parents=True, exist_ok=True)
    lex_file = synthetic_lex_dir / "synthetic_series.json"
    lex_file.write_text(
        json.dumps({
            "anime_slug": "synthetic_series",
            "anime_title": "Synthetic Series",
            "terms": {
                "syntheticheroinebeta": {
                    "canonical_pl": "SyntheticHeroineBeta",
                    "gender": "FEMALE",
                    "instruction": "Kobieta, główna protagonistka."
                },
                "syntheticheroalpha": {
                    "canonical_pl": "SyntheticHeroAlpha",
                    "gender": "MALE",
                    "instruction": "Mężczyzna, dowódca."
                }
            }
        }, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    @classmethod
    def patched_resolve_local(cls, character_name: str, series_slug: str = ""):
        clean_c = character_name.strip().lower()
        for f in synthetic_lex_dir.glob("*.json"):
            with open(f, "r", encoding="utf-8") as lf:
                data = json.load(lf)
            terms = data.get("terms", {})
            if clean_c in terms:
                g = str(terms[clean_c].get("gender", "")).upper()
                if g in ("FEMALE", "MALE"):
                    return g
        return None

    monkeypatch.setattr(ExternalGenderResolver, "_resolve_from_local_fansub_lexicons", patched_resolve_local)
    monkeypatch.setattr(ExternalGenderResolver, "CACHE_FILE", tmp_path / ".external_character_cache.json")
    ExternalGenderResolver.reset_circuit_breaker()
    ExternalGenderResolver._MEMORY_CACHE = {}

    # Wywołanie dla postaci żeńskiej
    res_female = ExternalGenderResolver.resolve_character_gender(
        "syntheticheroinebeta",
        series_slug="synthetic_series"
    )

    # 1. Sprawdzenie nagłówków zapytania HTTP
    assert len(captured_requests) > 0, "Zapytanie HTTP powinno zostać zainicjowane przed fallbackiem."
    req = captured_requests[0]
    user_agent = req.get_header("User-agent") or req.get_header("User-Agent")
    origin = req.get_header("Origin")
    referer = req.get_header("Referer")

    assert user_agent and "Mozilla/5.0" in user_agent and "Chrome/130" in user_agent, f"Niepoprawny User-Agent: {user_agent}"
    assert origin == "https://anilist.co", f"Niepoprawny Origin: {origin}"
    assert referer == "https://anilist.co/", f"Niepoprawny Referer: {referer}"

    # 2. Sprawdzenie wyniku fallbacku lokalnego
    assert res_female == "FEMALE", f"Oczekiwano FEMALE z lokalnego leksykonu, otrzymano: {res_female}"
    cache_entry = ExternalGenderResolver._MEMORY_CACHE.get("syntheticheroinebeta::synthetic_series")
    assert cache_entry is not None
    assert cache_entry.get("gender") == "FEMALE"
    assert cache_entry.get("source") == "local_fansub_lexicon"

    # Wywołanie dla postaci męskiej
    res_male = ExternalGenderResolver.resolve_character_gender(
        "syntheticheroalpha",
        series_slug="synthetic_series"
    )
    assert res_male == "MALE", f"Oczekiwano MALE z lokalnego leksykonu, otrzymano: {res_male}"


test_t11_2_8_anilist_graphql_headers_and_fallback = test_t11_2_8_anilist_resilience_and_lexicon_fallback


@pytest.mark.unit
def test_t11_2_8_pricing_guard_f1_thinking_sync():
    """
    Weryfikuje synchronizację PricingGuard z poziomem myślenia Fazy 1:
    - 350 linii / 12 paczek z f1_thinking_level='LOW': koszt ~2.21 PLN netto
    - 350 linii / 12 paczek z f1_thinking_level='MEDIUM': koszt ~3.32 PLN netto (<= 4.00 PLN)
    - 518 linii / 19 paczek z f1_thinking_level='MEDIUM': koszt ~5.25 PLN netto.
    """
    # 1. 350 linii / 12 paczek LOW
    est_low = PricingGuard.estimate_loaded_workload_cost_pln(
        profile="3",
        lines_count=350,
        batches_count=12,
        has_cache=True,
        f1_thinking_level="LOW"
    )
    assert est_low.get("f1_thinking_level") == "LOW"
    assert est_low["net_pln"] == 2.21, f"Oczekiwano 2.21 PLN netto dla LOW, otrzymano: {est_low['net_pln']}"

    # 2. 350 linii / 12 paczek MEDIUM
    est_med = PricingGuard.estimate_loaded_workload_cost_pln(
        profile="3",
        lines_count=350,
        batches_count=12,
        has_cache=True,
        f1_thinking_level="MEDIUM"
    )
    assert est_med.get("f1_thinking_level") == "MEDIUM"
    assert est_med["net_pln"] == 3.32, f"Oczekiwano 3.32 PLN netto dla MEDIUM, otrzymano: {est_med['net_pln']}"
    assert est_med["net_pln"] <= 4.00, "Koszt MEDIUM dla standardowego odcinka nie może przekroczyć 4.00 PLN netto"

    # 3. 518 linii / 19 paczek MEDIUM
    est_dense = PricingGuard.estimate_loaded_workload_cost_pln(
        profile="3",
        lines_count=518,
        batches_count=19,
        has_cache=True,
        f1_thinking_level="MEDIUM"
    )
    assert est_dense.get("f1_thinking_level") == "MEDIUM"
    assert est_dense["net_pln"] == 5.25, f"Oczekiwano 5.25 PLN netto dla 518 linii MEDIUM, otrzymano: {est_dense['net_pln']}"


@pytest.mark.unit
def test_t11_2_8_cache_ui_telemetry_gate(monkeypatch, capsys):
    """
    Weryfikuje, że w przypadku braku potwierdzenia tokenów buforowanych na Paczce 0
    (cached_content_token_count == 0) wyzwalane jest jawne zatrzymanie INC-AVT-057
    (os._exit(1) / ContextCacheDiscountError), a fałszywy komunikat o rabacie -95% jest blokowany.
    """
    exits = []
    monkeypatch.setattr(os, "_exit", lambda code: exits.append(code))

    translator = MultimodalTranslator(
        api_key="dummy_api_key_test_12345",
        model="gemini-4-hydrogen",
        enable_verifier=False
    )

    # 1. Symulacja Paczki 0 z cached == 0 (awaria serwerowego buforowania -> Hard Halt)
    translator._thread_local.last_batch_token_usage = {
        "prompt": 55000,
        "cached": 0,
        "output": 1200,
        "model": "gemini-4-hydrogen"
    }
    translator._batch0_cache_telemetry_reported = False

    with pytest.raises(ContextCacheDiscountError) as exc_info:
        translator._audit_batch0_context_cache(0)
    assert exits == [1], f"Oczekiwano wywołania os._exit(1), zarejestrowano: {exits}"
    assert "Brak aktywnego rabatu Context Cache" in str(exc_info.value)

    captured_halt = capsys.readouterr().err + capsys.readouterr().out
    assert "[Context Cache HALT / INC-AVT-057]" in captured_halt or "[Context Cache WARN / INC-AVT-057]" in captured_halt
    assert "(-95% input discount active)" not in captured_halt

    # 2. Symulacja Paczki 0 z aktywnym CachedContent >= 32768
    translator._batch0_cache_telemetry_reported = False
    translator._thread_local.last_batch_token_usage["cached"] = 53400

    translator._audit_batch0_context_cache(53400)
    captured_active = capsys.readouterr().out
    assert "[Context Cache ACTIVE]" in captured_active or "[Context Cache AKTYWNY]" in captured_active
    assert "53400" in captured_active
    assert "(-95% input discount active)" in captured_active or "Rabat -95% aktywny" in captured_active
    assert "HALT" not in captured_active


@pytest.mark.unit
def test_t11_2_8_cache_ui_telemetry_bypass(monkeypatch, capsys):
    """
    Weryfikuje, że flaga środowiskowa AVT_ALLOW_UNCACHED_BILLING=1
    pozwala pominąć twarde zatrzymanie potoku przy cached == 0.
    """
    monkeypatch.setenv("AVT_ALLOW_UNCACHED_BILLING", "1")
    translator = MultimodalTranslator(
        api_key="dummy_api_key_test_12345",
        model="gemini-4-hydrogen",
        enable_verifier=False
    )
    translator._audit_batch0_context_cache(0)
    captured = capsys.readouterr().out
    assert "[Context Cache HALT / INC-AVT-057]" in captured or "[Context Cache WARN / INC-AVT-057]" in captured
    assert "AVT_ALLOW_UNCACHED_BILLING" in captured


@pytest.mark.unit
def test_t11_2_8_multi_season_bible_hygiene(tmp_path):
    """
    Weryfikuje izolację wielosezonową w _resolve_bible_path oraz higienę
    SeriesBible zapobiegającą zanieczyszczaniu baz Sezonu 1 danymi z sequeli (INC-AVT-058).
    """
    s1_file = tmp_path / "syntheticseries_bible.json"
    s2_file = tmp_path / "syntheticseries_2nd_season_bible.json"

    s1_file.write_text(json.dumps({
        "anime_title": "SyntheticSeries",
        "characters": {},
        "episodes_translated": ["SyntheticSeries - 01"],
        "batch_stats": {"SyntheticSeries - 01": {"dialogues": 50, "batches": 2}}
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    s2_file.write_text(json.dumps({
        "anime_title": "SyntheticSeries 2nd Season",
        "characters": {},
        "episodes_translated": [],
        "batch_stats": {}
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    # 1. Weryfikacja resolwera _resolve_bible_path dla ścieżek z frazą S2 lub 2nd_Season
    resolved_s2_mkv = _resolve_bible_path("SyntheticSeries S2 - 01.mkv", storage_dir=tmp_path)
    assert resolved_s2_mkv.name == "syntheticseries_2nd_season_bible.json", f"Oczekiwano bazy sezonu 2, otrzymano: {resolved_s2_mkv.name}"

    resolved_s2_ass = _resolve_bible_path("SyntheticSeries 2nd Season - 02.ass", storage_dir=tmp_path)
    assert resolved_s2_ass.name == "syntheticseries_2nd_season_bible.json", f"Oczekiwano bazy sezonu 2, otrzymano: {resolved_s2_ass.name}"

    resolved_s1_ass = _resolve_bible_path("SyntheticSeries - 02.ass", storage_dir=tmp_path)
    assert resolved_s1_ass.name == "syntheticseries_bible.json", f"Oczekiwano bazy sezonu 1, otrzymano: {resolved_s1_ass.name}"

    # 2. Weryfikacja higieny w SeriesBible: blokada zanieczyszczania bazy Sezonu 1 danymi z Sezonu 2
    bible_s1 = SeriesBible(anime_title="SyntheticSeries", storage_dir=tmp_path)
    assert bible_s1.file_path.name == "syntheticseries_bible.json"

    # Próba zarejestrowania odcinka drugiego sezonu w bazie pierwszego sezonu
    bible_s1.update_after_episode(
        episode_name="SyntheticSeries S2 - 01",
        batch_count=6,
        dialogue_count=120,
        cost_pln=1.80
    )

    # Odcinek S2 NIE MOŻE trafić do bazy S1
    assert "SyntheticSeries S2 - 01" not in bible_s1.data["episodes_translated"]
    assert "SyntheticSeries S2 - 01" not in bible_s1.data["batch_stats"]

    # Rejestracja odcinka zgodnego (Sezon 1) musi powieść się prawidłowo
    bible_s1.update_after_episode(
        episode_name="SyntheticSeries - 02",
        batch_count=5,
        dialogue_count=100,
        cost_pln=1.50
    )
    assert "SyntheticSeries - 02" in bible_s1.data["episodes_translated"]
    assert "SyntheticSeries - 02" in bible_s1.data["batch_stats"]


test_t11_2_8_multi_season_bible_path_resolution = test_t11_2_8_multi_season_bible_hygiene
