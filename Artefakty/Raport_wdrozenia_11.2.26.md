# 🏛️ RAPORT WDROŻENIOWY — STANDARD 11.2.26 (`OBS-04`)
## Certyfikacja Standardu 11.2.26 (Telemetria ponowień API Fazy 1 i Fazy 2 w `pipeline_logger.py` i `translator.py`)

- **Repozytorium:** `https://github.com/wooles/translator` (gałąź `main`)
- **Punkt wyjścia (HEAD baseline 11.2.25):** `0961c31738769419fa21bb5e69e88732cc3e8634` (`0961c31`)
- **Commit 1 (Kod produkcyjny):** `96f5730` (`fix(telemetry): add EpisodeFlightRecorder.log_retry and record F1/F2 API retry events (503/429/504/TimeoutError) in events.jsonl before batch completion (OBS-04, 11.2.26)`)
- **Commit 2 (Testy integracyjne `httpx.MockTransport`):** `58a362d` (`test(telemetry): add httpx.MockTransport integration tests verifying retry events in events.jsonl before phase1_batch and phase2_verifier (OBS-04, 11.2.26)`)
- **Commit 3 (Dokumentacja i Zamknięcie Wydania):** `HEAD` (`docs(release): certify Standard 11.2.26 (OBS-04) — API retry telemetry in pipeline_logger and translator`)
- **Baseline ochrony Z16 (`c197db7` + Z16-amendment #15 z `6852a5a`):** **bezwzględne 0 B diffu** na wszystkich 29 plikach chronionych Z16 (w tym `verifier.py`, `client_factory.py`, `pricing_guard.py`) oraz na `scene_discourse.py` i `series_memory.py` względem `0961c31`.
- **Data certyfikacji:** 2026-11-24
- **Koszt wykonania:** 0.00 PLN (testy integracyjne oparte o prawdziwy `google.genai.Client` z transportem `httpx.MockTransport` i dyskowym `EpisodeFlightRecorder`)

---

## 1. CEL I ZAKRES WDROŻENIA (`OBS-04`)

Standard 11.2.26 domyka obserwację `OBS-04` z audytów produkcyjnych `<SERIA>` / `<ODCINEK>`, eliminując lukę telemetrii ponowień API w dziennikach `events.jsonl` oraz `full_trace.log`:

1. **`pipeline_logger.py:EpisodeFlightRecorder.log_retry`:**
   - Zapisuje ustrukturyzowane zdarzenie `stage="retry"` w `events.jsonl` (przez `self.record_event`) z polami top-level `timestamp_iso`, `stage`, `batch_id`, `line_id` oraz pełnym słownikiem `payload` (`batch_id`, `phase`, `error_type`, `attempt_number`, `wait_ms`, `timestamp`, `model`, `error_detail` przycięte do 300 znaków).
   - Zapisuje czytelną linię diagnostyczną `[RETRY | {phase} | Paczka {batch_id} | Próba #{attempt_number}] Typ: {error_type} | Oczekiwanie: {wait_ms} ms | Model: {model}` w `full_trace.log`.
2. **`translator.py:_classify_retry_error_type` i `_log_retry_telemetry` (Faza 1):**
   - Deterministyczna klasyfikacja błędów do kanonicznych typów (`"TimeoutError"`, `"503"`, `"429"`, `"504"`, `"403"`, `"404"`, `"500"` lub nazwa wyjątku).
   - Rejestracja ponowienia przed `time.sleep(...)` na wszystkich 3 ścieżkach Fazy 1 w `_call_gemini_with_retry`: unieważnienie cache `403`, przełączenie fallbackowe modelu oraz główny backoff `503`/`429`/`504`/`TimeoutError`.
3. **`translator.py:_process_phase2_only` (Faza 2 bez naruszania Z16):**
   - Scoped obserwator w bloku `try...finally` na `client_pool_f2.report_error` rejestrujący zdarzenia `phase="F2"` przed kolejnym wywołaniem API i przywracający oryginalną metodę w `finally`, zachowując dokładne **0 B diffu** w chronionym `verifier.py` i `client_factory.py`.
4. **Testy integracyjne (`tests/test_standard_11_2_26.py`):**
   - Weryfikacja na prawdziwym stosie HTTP `google.genai.Client` + `httpx.MockTransport` oraz prawdziwym zapisie na dysku w `tmp_path`:
     * `test_obs04_f1_http_503_via_httpx_mock_transport_logs_retry_before_phase1_batch` (`retry` ściśle przed `phase1_batch`, brak podwójnego bilingu).
     * `test_obs04_f1_retry_error_types_429_504_and_timeout_recorded_sequentially` (`429` → `504` → `TimeoutError` jako próby `1, 2, 3`).
     * `test_obs04_f2_http_503_via_httpx_mock_transport_logs_retry_before_phase2_verifier_and_restores_hook` (`retry` `phase="F2"` przed `phase2_verifier` oraz przywrócenie `report_error`).

---

## 2. METRYKI CI/CD, GOTOWOŚĆ DO PRZEBIEGU §4.4 I IZOLACJA Z16

- `tests/test_standard_11_2_26.py`: **3 / 3 PASSED**
- `tests/test_flight_recorder.py`: **3 / 3 PASSED**
- `tests/`: **450 / 450 PASSED**
- `test_system.py`: **70 PASSED, 154 DESELECTED**
- Bramki kwalifikacyjne: `verify_purity.py` (**11/11 PASS**), `verify_8_fixes.py` (**8/8 PASS**), `verify_12_fixes.py` (**12/12 PASS**), `verify_ultimate_pipeline.py` (**15/15 PASS**)
- Audyt śledczy: `audit_diff.ps1 -BaseRef "0961c31"` -> **VICTORY CONFIRMED**
- Izolacja Z16 i zakresu względem `0961c31`: **0 B DIFF**
- Status przebiegu kontrolnego (§4.4): potok gotowy do pełnej weryfikacji end-to-end z kompletną telemetrią `retry` dla Fazy 1 i Fazy 2.
