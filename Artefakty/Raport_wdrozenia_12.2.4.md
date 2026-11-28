# Raport wdrożenia Standard 12.2.4 (`S2` — Flex dla F2 + `PricingGuard` Flex `0.5x` + autoryzowany `Z16-amendment #17` — `0.00 PLN`)

**Data:** `2026-11-28`  
**Baza startowa (`main`):** `de8efcd62ff81fbc80a240ab16ee364b833ef0b3` (`de8efcd`, `12.2.3 + 12.2.3a CLOSED`)  
**Status:** `CERTIFIED IN TESTS / AWAITING AUDIT` (`0.00 PLN` wydatku na API; autoryzowany `Z16-amendment #17` wyłącznie w `verifier.py` i `pricing_guard.py`)

---

## 1. Zakres zmian, łańcuch commitów i izolacja plików (`de8efcd..HEAD`)

W ramach wdrożenia Standardu `12.2.4` zrealizowano `4` atomowe commity na gałęzi `main`:

1. `c30f5d0` — `fix(z16): 12.2.4 [1/4] — Z16-amendment #17: opt-in Gemini Flex Inference & 2x 503 fallback in verifier.py (S2)`
2. `a8cbb3c` — `fix(z16): 12.2.4 [2/4] — Z16-amendment #17: Flex 0.5x rate accounting in pricing_guard.py + flex token counters in translator.py`
3. `67e50f9` — `test(pipeline): 12.2.4 [3/4] — non-tautological HTTP & billing tests for S2 (verifier Flex + PricingGuard Flex)`
4. `[4/4]` — `docs(release): 12.2.4 [4/4] — PROJECT_MEMORY (Z16-amendment #17, Q2 PASS, R1 REJECT, OBS-25..27) & Raport_wdrozenia_12.2.4 (5-layer audit)`

Zmodyfikowano/utworzono wyłącznie `6` dozwolonych plików:

- [verifier.py](../verifier.py) *(autoryzowany `Z16-amendment #17` — wyłącznie wnętrze `DialogueVerifier.verify_batch`, `L1053–1340`)*
- [pricing_guard.py](../pricing_guard.py) *(autoryzowany `Z16-amendment #17` — wyłącznie wnętrze `PricingGuard.calculate_actual_cost_breakdown`, `L317–413`)*
- [translator.py](../translator.py) *(akumulacja `flex_prompt`/`flex_cached`/`flex_output` w `_call_gemini_with_retry`, delty w `_compute_session_net_pln` i odtwarzanie checkpointu; `0 B` w `_resolve_line_addressee`)*
- [test_standard_12_2_4.py](../tests/test_standard_12_2_4.py) *(`5` nietautologicznych testów HTTP + billing S2)*
- [PROJECT_MEMORY.md](../PROJECT_MEMORY.md) *(status `12.2.4`, zamknięcia `Q2 PASS` / `R1 REJECT`, rejestr `OBS-25..27`, `ARB-087`)*
- [Raport_wdrozenia_12.2.4.md](Raport_wdrozenia_12.2.4.md) *(niniejszy raport)*

**Bezwzględne `0 B` diffu:** pozostałe `28` plików chronionych Z16 (`avt_linter.py`, `client_factory.py`, `rules.py`, `test_system.py`, `verify_purity.py`, `main.py`, `context_cache.py`, `.onomastic_lexicon.json`, `20` plików `*_bible.json`), `scene_discourse.py`, `model_resolver.py`, `pipeline_logger.py`, `profiler.py`, `sign_detector.py`, `series_memory.py`, `tools/verify_f2_consolidation_ab.py` oraz `translator.py:_resolve_line_addressee`.

---

## 2. Specyfikacja wdrożonego rozwiązania `S2`

### 2.1. `Z16-amendment #17` cz. 1 — [verifier.py](../verifier.py) (`verify_batch`, `L1053–1340`)
- Odczyt `resolve_service_tier()` i aplikacja `apply_service_tier_to_config(cfg_kwargs, active_service_tier, self.model)` bezpośrednio przed `types.GenerateContentConfig(**cfg_kwargs)`. Domyślna wartość `AVT_SERVICE_TIER` pozostaje `"standard"`.
- Odczyt nagłówka odpowiedzi `extract_response_service_tier_header(response)` oraz wyznaczenie `effective_tier`: zapis `"service_tier"` (i opcjonalnego `"response_service_tier_header"`) w `_thread_local.last_batch_token_usage` **nawet przy braku `usage_metadata`**, a przy aktywnym `usage_metadata` akumulacja `flex_prompt`, `flex_cached`, `flex_output` w `self.current_episode_tokens` przez `.get(..., 0)`.
- Odporność na wyjątki czasu wykonania (`isinstance(e, (TimeoutError, concurrent.futures.TimeoutError))` w `is_timeout`) oraz deterministyczny bezpiecznik `2× 503/timeout -> standard` **zawsze przed** blokiem fallbacku modelu (`active_service_tier != "flex"` w warunku zejścia do `gemini-3.8-flash`).

### 2.2. `Z16-amendment #17` cz. 2 — [pricing_guard.py](../pricing_guard.py) (`calculate_actual_cost_breakdown`, `L317–413`) & [translator.py](../translator.py)
- Wewnątrz `calculate_actual_cost_breakdown` zaimplementowano lokalne funkcje pomocnicze `_resolve_model_rate` oraz `_calc_phase_cost_usd`:
  - Gdy `stats` zawiera dowolny z kluczy `("flex_prompt", "flex_cached", "flex_output")`, rozlicza tokeny flex ze stawką **`0.5×`**, a pozostałe ze stawką **`1.0×`**.
  - W przeciwnym razie dla `service_tier == "flex"` nakłada mnożnik **`0.5×`** na całą fazę; przy braku trybu Flex zachowuje wynik co do grosza identyczny z wariantem standardowym.
  - Struktura zwracanego słownika oraz wyliczenie `standard_net_pln`, `savings_pln` i `savings_ratio` pozostały niezmienione (dla pełnego `S2` z `100%` F2 Flex i mieszanym F1 koszt odcinka spada z `4.21 PLN` do `2.22 PLN`, oszczędność `1.99 PLN`, `47.27%`).
- W [translator.py](../translator.py): F1 zapisuje pod-liczniki `flex_*` przy `effective_tier == "flex"`, `_compute_session_net_pln` wylicza delty sesji dla wszystkich `6` pól, a odtwarzanie checkpointu wczytuje również `flex_prompt`/`flex_cached`/`flex_output` przez `.get(k, 0)`.

---

## 3. Obowiązkowy Audyt 5 Warstw (`CORNERSTONE.md` Prawo 12)

| Warstwa | Moduły | Zakres wdrożenia / weryfikacja izolacji | Status |
| --- | --- | --- | --- |
| **Warstwa 1 (Ingress & Konfiguracja)** | [model_resolver.py](../model_resolver.py), [profiler.py](../profiler.py), [sign_detector.py](../sign_detector.py) | `0 B` diffu; użycie współdzielonego kontraktu `resolve_service_tier` (domyślnie `"standard"`), `apply_service_tier_to_config` i `extract_response_service_tier_header` wprowadzonego w `12.2.3`. Zero własnych literałów Z1 (`verify_purity.py` `12/12 PASS`). | `PASS` |
| **Warstwa 2 (Stan, F1 & Pamięć)** | [translator.py](../translator.py), [series_memory.py](../series_memory.py), [scene_discourse.py](../scene_discourse.py) | F1 akumuluje `flex_prompt`/`flex_cached`/`flex_output` przy `effective_tier == "flex"`, `_compute_session_net_pln` i checkpoint przenoszą pełne delty budżetu. `0 B` diffu w `series_memory.py`, `scene_discourse.py` oraz `_resolve_line_addressee`. | `PASS` |
| **Warstwa 3 (Kanon & Weryfikator F2)** | [verifier.py](../verifier.py), [rules.py](../rules.py) | Autoryzowany `Z16-amendment #17` ściśle wewnątrz `verify_batch` (`L1053–1340`): zero zmian `system_prompt`, zero zmian modeli (`gemini-4-hydrogen` zachowany), fallback `2× 503/TimeoutError -> standard` poprzedza fallback modelu; `0 B` diffu w `rules.py`. | `PASS` |
| **Warstwa 4 (Rozliczenie & Bramka Jakości)** | [pricing_guard.py](../pricing_guard.py), [avt_linter.py](../avt_linter.py) | Autoryzowany `Z16-amendment #17` ściśle wewnątrz `calculate_actual_cost_breakdown` (`L317–413`): dokładne rozliczanie `0.5×` Flex i mieszanych przebiegów Flex/Standard bez naruszenia sygnatury i zgodności wstecznej; `0 B` diffu w `avt_linter.py` i pozostałych metodach `pricing_guard.py`. | `PASS` |
| **Warstwa 5 (Tarcza Regresyjna CI/CD)** | [test_standard_12_2_4.py](../tests/test_standard_12_2_4.py), [test_system.py](../test_system.py) | `5/5` nowych testów HTTP/billing S2 w `test_standard_12_2_4.py`, `549/549` w `tests/`, `70 passed` (`154 deselected`) w `test_system.py`, `4/4` bramki (`12/12`, `8/8`, `12/12`, `15/15`), `check_z16_lock.ps1` i `audit_diff.ps1` w stanie `PASS`. | `PASS` |

---

## 4. Tabela wpływu na 5 Pułapek Z16 (`Z16-P1..P5`)

Wszystkie `5` historycznych pułapek regresyjnych Z16 zostało zweryfikowanych bezpośrednio offline (`0.00 PLN`) oraz przez brak jakichkolwiek zmian w [series_memory.py](../series_memory.py), [metadata.py](../metadata.py), [test_system.py](../test_system.py) i plikach `series_memory/*_bible.json`:

| ID Pułapki | Zakres kontraktu Z16 | Lokalizacja / Moduł | Wpływ `12.2.4` | Wynik weryfikacji |
| --- | --- | --- | --- | --- |
| **`Z16-P1`** | Sezonowy fallback `SeriesBible._resolve_bible_path` przy braku sufiksu sezonu (`self_season is None` -> `_S2_bible.json`) | `series_memory.py` / `test_system.py:12283, 12411` | **Nie dotknięta** (`0 B` diffu) | `PASS` (zweryfikowano offline + `0 B` diffu) |
| **`Z16-P2`** | Dopasowanie jawnego sufiksu sezonu w `SeriesBible._resolve_bible_path` (`cand_season == self_season` -> `*_2nd_Season_bible.json`) | `series_memory.py` / `test_system.py:14693` | **Nie dotknięta** (`0 B` diffu) | `PASS` (zweryfikowano offline + `0 B` diffu) |
| **`Z16-P3`** | Zachowanie obu rekordów płci i deklinacji w `consolidate_split_bibles` / bazie serii (`FEMALE` + wpis `declensions`) | `series_memory.py` / `test_system.py:14881–14900` | **Nie dotknięta** (`0 B` diffu) | `PASS` (zweryfikowano offline + `0 B` diffu) |
| **`Z16-P4`** | Niezmienniczość wielkości liter i transliteracja diakrytyków w `clean_anime_slug` | `series_memory.py` / `test_system.py:4839` | **Nie dotknięta** (`0 B` diffu) | `PASS` (`test_series_memory.py` + `0 B` diffu + offline check) |
| **`Z16-P5`** | Zamrożony kontrakt funkcji `strip_season_suffix` | `metadata.py` / `test_system.py:14753–14771` | **Nie dotknięta** (`0 B` diffu) | `PASS` (`test_metadata.py` + `0 B` diffu + offline check) |

*(Uwaga metodologiczna: w szybkim przebiegu `test_system.py -m "not slow and not network"` testy macierzyste mają znaczniki `@pytest.mark.slow`/`@pytest.mark.network` i podlegają odfiltrowaniu w puli `154 deselected`; ich kontrakty domenowe zweryfikowano równolegle w pakietach `test_metadata.py`, `test_series_memory.py` oraz bezpośrednią kontrolą offline `Z16_TRAPS_1_TO_5_VERIFIED_OFFLINE: 5/5 PASS`.)*

---

## 5. Wyniki testów, bramek kwalifikacyjnych i statystyka diffu (`de8efcd..HEAD`)

- **Testy celowane S2 ([test_standard_12_2_4.py](../tests/test_standard_12_2_4.py)):** **`5 passed in 9.00s`**:
  - `test_s2_verifier_default_standard_no_flex_headers`
  - `test_s2_verifier_opt_in_flex_sends_header_records_telemetry_and_flex_tokens`
  - `test_s2_verifier_flex_two_503_or_timeout_fallback_to_standard_same_hydrogen_model`
  - `test_s2_pricing_guard_flex_exact_and_mixed_fallback_accounting`
  - `test_s2_translator_mixed_f1_flex_and_fallback_accumulates_exact_flex_counters`
- **Pakiet `12.2.4 + 12.2.3 + verifier + context_cache + translator`:** **`126 passed in 66.45s (0:01:06)`**.
- **Pełny katalog `tests/`:** **`549 passed, 1 pre-existing warning in 260.46s (0:04:20)`**.
- **Pakiet [test_system.py](../test_system.py) (`-m "not slow and not network" -k "not test_batch_coalescence_ssot_prompt_and_cot_streamlining_guard"`):** **`70 passed, 154 deselected in 22.12s`**.
- **4 bramki kwalifikacyjne CI/CD:**
  - [verify_purity.py](../verify_purity.py): **`12/12 PASS`**
  - [verify_8_fixes.py](../verify_8_fixes.py): **`8/8 PASS`**
  - [verify_12_fixes.py](../verify_12_fixes.py): **`12/12 PASS`**
  - [verify_ultimate_pipeline.py](../verify_ultimate_pipeline.py): **`15/15 PASS`**
- **Statystyka diffu kodu/testów przed commitem dokumentacji (`git diff --stat de8efcd..67e50f9`):**
  - `pricing_guard.py`: `90` zmian (`44+ / 46-`, wyłącznie `calculate_actual_cost_breakdown`)
  - `verifier.py`: `61` zmian (`52+ / 9-`, wyłącznie `verify_batch`)
  - `translator.py`: `17` zmian (`14+ / 3-`, pod-liczniki `flex_*` / budżet / checkpoint)
  - `tests/test_standard_12_2_4.py`: `374` nowe linie (`100% Z1-pure`)
  - Dokumentacja w commicie `[4/4]`: [PROJECT_MEMORY.md](../PROJECT_MEMORY.md) oraz [Raport_wdrozenia_12.2.4.md](Raport_wdrozenia_12.2.4.md).
- **Decyzje i obserwacje zarejestrowane bez zmian kodu:** `Q2 Faza 1` (`CLOSED — PASS`, rachunek `3,17 PLN` vs `4,21 PLN`, `-45,7%` F1), `R1` (`CLOSED — REJECT`, Recall `20%`, FPR `9,99%`), oraz otwarte nieblokujące `OBS-25`, `OBS-26`, `OBS-27` w [PROJECT_MEMORY.md](../PROJECT_MEMORY.md).
