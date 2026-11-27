# Raport Wdrożenia: Mikro-Hotfix `12.2.2` (Obserwowalność Loggera `U1–U8` — `0.00 PLN`, `0 B` diff Z16)

- **Data wydania:** `2026-11-27`
- **Status wydania:** **`CERTIFIED IN TESTS / AWAITING AUDIT`**
- **Gałąź / Baza startowa:** `main`, baza startowa `d16b869` (`12.2.1 + 12.2.1a CLOSED`)
- **Model produkcyjny:** `gemini-4-hydrogen` (`D-1 Flash F1/F2 — REJECTED BY OPERATOR`, `AVT_CONSOLIDATE_F2="0"`)
- **Commity atomowe (`2/2`):**
  1. `193810f` — `feat(logger): 12.2.2 [1/2] — U1–U8 observability upgrade (F2 score breakdown, line_ids/rules/A-1/A-3/C-1 telemetry, f2_raw/post_f2/EQG diffs, whisper_tags/acoustics batch_id, atomic checkpoint, A/B off-by-one fix)`
  2. `HEAD` — `test(logger): 12.2.2 [2/2] — non-tautological U1–U8 observability tests + PROJECT_MEMORY & Raport_wdrozenia_12.2.2`
- **Izolacja `Z16`, `DEF-02` i brak zmian tłumaczeniowych (`0 B` diffu względem `d16b869`):**
  - Wszystkie `30` plików chronionych Z16 ([avt_linter.py](../avt_linter.py), [verifier.py](../verifier.py), [client_factory.py](../client_factory.py), [rules.py](../rules.py), [test_system.py](../test_system.py), [verify_purity.py](../verify_purity.py), [pricing_guard.py](../pricing_guard.py), [main.py](../main.py), [context_cache.py](../context_cache.py), `series_memory/.onomastic_lexicon.json`, `series_memory/*_bible.json`), [scene_discourse.py](../scene_discourse.py), [series_memory.py](../series_memory.py), [profiler.py](../profiler.py), [sign_detector.py](../sign_detector.py) oraz metoda `_resolve_line_addressee` zachowują **`0 B` zmian** w historii commitów `d16b869..HEAD`.
  - **Świadoma decyzja Operatora (odrzucenie `Z16-amendment #17`):** `thoughts` rejestrowane wyłącznie w F1 ([translator.py](../translator.py)), bez dotykania `verifier.py` ani `pricing_guard.py`.
  - **Brak wpływu na wyjście tłumaczenia:** identyczne prompty do Gemini i identyczna punktacja `_score_phase2_editorial_risk`; wyłącznie warstwa telemetryczna, atomowy zapis checkpointu oraz korekta narzędzia A/B offline.

---

## 1. Zestawienie Usprawnień Obserwowalności (`U1–U8`)

| ID | Waga | Zakres plików | Wdrożona funkcjonalność i kompatybilność wsteczna |
|---|---|---|---|
| `U1` | CRITICAL | [translator.py](../translator.py), [pipeline_logger.py](../pipeline_logger.py) | Wydzielono `_score_phase2_editorial_risk_detailed` (zwraca `(score, critical_cot, reasons)`), delegując `_score_phase2_editorial_risk` przy 100% zgodności wstecznej. `_select_hydrogen_phase2_candidates` zapisuje w każdym słowniku `orig_it`: `f2_score`, `f2_score_reasons`, `f2_batch_p90`, `f2_batch_cap`, `f2_selected` oraz `f2_not_selected_reason` (`None` / `"score_zero"` / `"below_batch_cap"` / `"evicted_for_a1_pair"`). `phase2_verifier` rejestruje `f2_selection_summary`. |
| `U2` | CRITICAL | [pipeline_logger.py](../pipeline_logger.py), [translator.py](../translator.py) | `_prepare_batch_prompt` zapisuje `last_f1_rendered_characters`; `log_phase1_batch` przyjmuje opcjonalne `focused_rules`, `locked_glossary_count`, `rendered_characters`, `line_ids` (uporządkowana lista `orig_idx` zamykająca lukę `G6` przy FBF); `log_phase2_verifier` (tryb `1:1` i skonsolidowany) rejestruje mapę `line_ids` (`local->orig`) i aktywny kontekst; `_extract_line_observability_meta` wypełnia `notes_meta` (`a1_pair_tag`, `a3_tv_hint`, `c1_neighbors`, `obs13c_target_conf`, `obs13c_suppressed`, `scene_tone`) wraz z `batch_id`, `local_id`, `style`, `is_sign`, `is_song`, `is_internal_monologue` w `line_evolution`. |
| `U3` | HIGH | [translator.py](../translator.py), [pipeline_logger.py](../pipeline_logger.py) | Rejestracja `f2_raw_pl`, `f2_changes_made` i listy etapów `post_f2_fixes` (`post_f2:italic_style_strip`, `post_f2:radio_impersonal`, `post_f2:obs19_trailing_period`, `post_f2:a5_numeric_expansion`, `post_f2:locked_glossary_enforce`, `post_f2:a1_split_pair_guard`) w `line_evolution`. W `translate_file` zapisano `sign_detector_events`, snapshot przed/po `EpisodeQualityGate` (`eqg_diffs`) oraz `avt_metrics["ass_events_count"]` w `quality_gate_pricing`. |
| `U4` | HIGH | [pipeline_logger.py](../pipeline_logger.py), [translator.py](../translator.py) | `log_acoustics_and_whisper` przyjmuje `batch_id: Optional[int] = None` (zapis w zdarzeniu JSONL i nagłówku sekcji `full_trace.log`); w `log_line_evolution` zastąpiono martwy klucz `whisper_disambiguation` złożeniem `speaker_voice \| prosody \| pragmatic_register`. |
| `U5` | MEDIUM | [pipeline_logger.py](../pipeline_logger.py), [translator.py](../translator.py) | Dodano pole `"thoughts"` obok `"output"` w `last_batch_token_usage` F1 (zachowując semantykę `output = cands + thoughts` dla `PricingGuard`); dodano `runtime_meta` (`git_head`, `consolidate_f2`, `resumed_from_checkpoint`) w `log_cli_init`, zdarzenie `stage="budget_audit"` przez `log_budget_audit` i wspólny helper `_emit_budget_audit` (`INIT`, `ZERO_CACHE_LEAN`, `ACTIVE`, `PARTIAL_HIT`, `BYPASS`, `WARN`, `HALT` przed `os._exit(1)`, `CHECKPOINT_RESUME`) oraz atomowy zapis `.checkpoint.json` poprzez `_write_json_atomic` (`.tmp` + `flush` + `os.fsync` + `os.replace`). |
| `U6` | MEDIUM | [pipeline_logger.py](../pipeline_logger.py), [translator.py](../translator.py) | `log_series_bible` rejestruje opcjonalne `locked_glossary` oraz `ram_sanitization_notes` (adnotacje sanitacji z RAM, statystyki rekordów P0 / zweryfikowanej płci i lokalne blokady tytułów bez edycji `series_memory.py`). |
| `U7` | LOW | [translator.py](../translator.py), [pipeline_logger.py](../pipeline_logger.py) | `phase1_batch` serializuje `raw_response` przez `model_dump(exclude_none=True)` (eliminacja zbędnych pól `null`); `EpisodeFlightRecorder` posiada `_io_error_count` oraz `_handle_io_error` logujące jednokrotne ostrzeżenie `logger.warning` przy zachowaniu trybu fail-safe (zero rzucanych wyjątków, 100% wstecznej kompatybilności parametrów `= None`). |
| `U8` | HIGH | [verify_f2_consolidation_ab.py](../tools/verify_f2_consolidation_ab.py) | Naprawiono przesunięcie `off-by-one` (`(lid - first_id) + 1`) w `load_phase2_items_from_events` (obsługuje `str` i `Path`): używa jawnego `p1_payload["line_ids"]` w nowych logach `12.2.2+` oraz `enumerate(present_lids, 1)` w starszych logach z lukami FBF, a także odczytuje wprost `is_sign`, `is_song`, `local_id`, `batch_id`, `f2_score`, `notes_meta`. |

---

## 2. Wyniki Testów Regresyjnych i Bramek Jakościowych (`0.00 PLN`)

Wszystkie pakiety wykonano na finalnym kodzie Commitu `1/2` (`193810f`) oraz z testami Commitu `2/2`:

- **[test_standard_12_2_2.py](../tests/test_standard_12_2_2.py) + regresja `12.x` + [test_flight_recorder.py](../tests/test_flight_recorder.py):** **`68 passed in 57.74s`** (`8` testów `test_standard_12_2_2.py`, `3` testy `test_flight_recorder.py`, `7` testów `12.2.1`, `13` testów `12.2.0`, `11` testów `12.1.0`, `26` testów `12.0.0`).
- **Pełny pakiet `tests/`:** **`537 passed in 233.60s (0:03:53)`** (w tym `12/12 PASSED` w `tests/test_hygiene.py` potwierdzające brak cichych bloków `except Exception: pass` w modułach krytycznych).
- **`test_system.py` (`-m "not slow and not network" -k "not test_batch_coalescence_ssot_prompt_and_cot_streamlining_guard"`):** **`70 passed, 154 deselected in 22.11s`** (łącznie **`607 passed`**).
- **4 bramki kwalifikacyjne CI/CD:**
  - `verify_purity.py`: **`12/12 PASS`** (`Z1`-clean we wszystkich plikach produkcyjnych, narzędziu A/B i testach)
  - `verify_8_fixes.py`: **`8/8 PASS`**
  - `verify_12_fixes.py`: **`12/12 PASS`**
  - `verify_ultimate_pipeline.py`: **`15/15 PASS`**
- **Audyt śledczy i blokada `Z16`:**
  - `tools/check_z16_lock.ps1 -BaseRef "d16b869..HEAD"`: **`PASS - Z16 (0 B DIFF) & DEF-02 CHRONIONE`** (`EXIT 0`)
  - `audit_diff.ps1 -BaseRef "d16b869"`: **`VICTORY CONFIRMED`**
  - `git diff --stat d16b869..HEAD`: wyłącznie `6` dozwolonych plików.

---

## 3. Weryfikacja Replayu Offline na Logach z `logs/` (`U8`, `0.00 PLN`)

Uruchomiono `load_phase2_items_from_events` w trybie offline na `3` najnowszych produkcyjnych plikach `events.jsonl` z `logs/`:

1. **Log paczki 1 z luką FBF (`ID 71` skompresowane między `ID 70` i `ID 72`):** zrekonstruowano `54` linie w paczce `1`, mapując `orig_idx=70 -> local_id=13`, **`orig_idx=72 -> local_id=14`** oraz `orig_idx=73 -> local_id=15` (bez przesunięcia `off-by-one` na `15` w starszych logach bez `line_ids`).
2. **Dwa pozostałe logi wielopaczkowe (`6` oraz `8` paczek produkcyjnych):** pełna rekonstrukcja bez błędów schematu (`0` wyjątków; `orig_idx=72` mapowane spójnie na oczekiwane `local_id` wewnątrz paczki `1`: odpowiednio `13` oraz `16`).
