# 🏛️ RAPORT WDROŻENIOWY — STANDARD 11.2.25
## Certyfikacja Standardu 11.2.25 (Domknięcie residualnej luki DEF-02 w `translator._resolve_line_addressee` i `lookback_history`)

- **Repozytorium:** `https://github.com/wooles/translator` (gałąź `main`)
- **Punkt wyjścia (HEAD baseline 11.2.24):** `6852a5a841c4f2e151fe48610d91eb43c44de360` (`6852a5a`)
- **Commit 1 (Kod produkcyjny):** `e4bdf85` (`fix(pipeline): enforce scene_discourse UNSPECIFIED reset and FFmpeg scene-cut boundary in _resolve_line_addressee and lookback_history (residual DEF-02, 11.2.25)`)
- **Commit 2 (Testy i Certyfikacja Kodu):** `22ddc18` (`test(pipeline): verify residual DEF-02 across all 5 production scene-cut geometries and standalone _resolve_line_addressee guard (11.2.25)`)
- **Commit 3 (Dokumentacja i Zamknięcie Wydania):** `HEAD` (`docs(release): certify Standard 11.2.25 — residual DEF-02 scene-cut addressee guard in translator._resolve_line_addressee`)
- **Baseline ochrony Z16 (`c197db7` + Z16-amendment #15 z `6852a5a`):** **bezwzględne 0 B diffu** na wszystkich plikach chronionych Z16 oraz na `scene_discourse.py`, `pipeline_logger.py` i `series_memory.py` względem `6852a5a`.
- **Data certyfikacji:** 2026-11-24
- **Koszt wykonania:** 0.00 PLN (100% lokalne silniki, brak wywołań sieciowych LLM)

---

## 1. CEL I PRZYCZYNA ŹRÓDŁOWA (`DEF-02` RESIDUAL)

Audyt przebiegu produkcyjnego dla `<ODCINEK>` (`<SERIA>`) na HEAD `6852a5a` wykazał, że `scene_discourse.py` poprawnie wyzerowało adresata (`target_speaker='UNSPECIFIED'`, `target_gender='UNSPECIFIED'`, `target_confidence=0.0`) na wszystkich 5 liniach granicznych (`#80`, `#189`, `#255`, `#264`, `#293`). Mimo tego stara postać z poprzedniej sceny pojawiała się w `telemetry_tag` z dwóch przyczyn w `translator.py`:

1. **Brak znaczników czasu `start_ms`/`end_ms` w `lookback_history` (`translator.py` w gałęzi `b_idx > 0`):**
   Wpis historii budowany z `prev_batch` nie zapisywał czasu rozpoczęcia i zakończenia poprzedniej kwestii, przez co linia otwierająca nową paczkę (`event_idx == 0`, przypadek `#264`) ślepo dziedziczyła mówcę z końca poprzedniej paczki pomimo przerwy `4630 ms` i 2 cięć FFmpeg.
2. **Wtórne obchodzenie resetu `UNSPECIFIED` w `_resolve_line_addressee` (`translator.py`):**
   Metoda `_resolve_line_addressee` wykonywała wsteczne wyszukiwanie do `8000 ms`, przeszukiwanie `lookback_history` bez kontroli przerw oraz forward lookahead do `6000 ms` bez sprawdzania, czy `scene_discourse.py` oznaczyło już zdarzenie jako `UNSPECIFIED`, i bez honorowania granicy cięć FFmpeg (`>= 3500 ms` lub `>= 2500 ms` z granicą w `self.scene_cuts_ms`).

---

## 2. ZAKRES WDROŻONYCH ZMIAN (`translator.py`, 0 B DIFFU W `scene_discourse.py`)

1. **Poprawka 1A (`translator.py` — `lookback_history` z `prev_batch`):**
   Dodano zapis pól `"start_ms"` i `"end_ms"` dla każdego elementu `lookback_history` budowanego z `prev_batch`.
2. **Poprawka 1B (`translator.py` — `_resolve_line_addressee`):**
   - Wprowadzono poszanowanie jawnego resetu z `scene_discourse.py`: gdy `target_speaker == "UNSPECIFIED"`, `target_gender == "UNSPECIFIED"`, brak `vocative_lock` i brak jawnej wskazówki `raw_norm`, metoda zwraca bezpośrednio `(None, None)`.
   - Zdefiniowano jednolitą bramkę `_is_scene_cut_boundary(t_prev_end, t_curr_start)` o identycznym kontrakcie co w `scene_discourse.py` (`gap >= 3500 ms` lub `gap >= 2500 ms` z granicą `b_cut` w `self.scene_cuts_ms`).
   - Objęto kontrolą cięć scen, ochroną przed szyldami (`_NON_DIALOGUE_ACTORS`) i myślami wewnętrznymi (`italic`, `is_internal_monologue`, `is_thought`) wszystkie trzy gałęzie: wyszukiwanie wsteczne (`event_idx > 0`), `lookback_history` (`event_idx == 0`) oraz forward lookahead.
3. **Nowe testy regresyjne (`tests/test_standard_11_2_25.py`):**
   - `test_def02_residual_5_production_scene_cuts_do_not_leak_stale_addressee`: weryfikuje pełny łańcuch produkcyjny (`SceneDiscourseGraph.build_discourse_topology` → `_resolve_line_addressee` → `arbitrate_event_telemetry` → `format_dry_telemetry_tag`) na wszystkich 5 geometriach czasowych (`#80`, `#189`, `#255`, `#264` przez `lookback_history` i `#293`).
   - `test_def02_residual_standalone_resolve_line_addressee_respects_scene_cuts_and_preserves_intrascene`: weryfikuje bezpośrednie wywołania `_resolve_line_addressee` na cięciach `>= 3500 ms`, cięciach FFmpeg `2500–3499 ms`, granicy paczek `lookback_history` oraz kontrolę zachowawczą wewnątrz sceny (`gap = 640 ms`).

---

## 3. PLAN KOLEJNYCH ITERACJI I ZNANE OBSERWACJE

- **Standard 11.2.25 (bieżący):** domknięcie residualnej luki `DEF-02` w `translator.py`.
- **Standard 11.2.26 (planowany):** `OBS-04` (`pipeline_logger.py:log_retry`).
- **Kandydat do Standardu 11.2.27:** `OBS-05` (`\NI` w Fazie 2).
- **KNOWN GAP do weryfikacji w kolejnym przebiegu:** `DEF-01`, `DEF-04`, `OBS-01` (po wdrożeniu w `11.2.23`/`11.2.24` oczekują na potwierdzenie w kolejnym przebiegu end-to-end); `OBS-03` (`pricing_guard.py:379`) poza zakresem.

---

## 4. METRYKI CI/CD I AUDYT ŚLEDCZY

- `tests/test_standard_11_2_25.py`: **2 / 2 PASSED**
- `tests/`: **447 / 447 PASSED**
- `test_system.py`: **70 PASSED, 154 DESELECTED**
- Bramki kwalifikacyjne: `verify_purity.py` (**11/11 PASS**), `verify_8_fixes.py` (**8/8 PASS**), `verify_12_fixes.py` (**12/12 PASS**), `verify_ultimate_pipeline.py` (**15/15 PASS**)
- Audyt śledczy: `audit_diff.ps1 -BaseRef "6852a5a"` -> **VICTORY CONFIRMED**
- Izolacja Z16 i zakresu względem `6852a5a`: **0 B DIFF**
