# Raport Wdrożenia: Mikro-Hotfix `12.2.1` (`OBS-19`..`OBS-23` — `0.00 PLN`, `0 B` diff Z16)

- **Data wydania:** `2026-11-27`
- **Gałąź / Baza startowa:** `main`, baza startowa `53751a4` (`12.2.0b` + [check_z16_lock.ps1](../tools/check_z16_lock.ps1))
- **Model produkcyjny:** `gemini-4-hydrogen` (`D-1 Flash F1/F2 — REJECTED BY OPERATOR`, `AVT_CONSOLIDATE_F2="0"`)
- **Commity atomowe (`3/3` + `12.2.1a`):**
  1. `e06c224` — `fix(pipeline): 12.2.1 [1/3] — OBS-19 + OBS-20 (typografia F2: kropki po kursywie i wielowierszowa kursywa)`
  2. `05798bc` — `fix(pipeline): 12.2.1 [2/3] — OBS-21 + OBS-22 (guard '/' w rejestrze/kolektywach + glosariusz i filtr bliskości Sign OCR)`
  3. `40053a2` — `fix(pipeline): 12.2.1 [3/3] — OBS-23 (priorytet catchphrases, scoring F2 literówek/zapowiedzi) + tests + docs`
  4. `HEAD` — `fix(12.2.1a): eliminate false positives in OBS-23 typo & announcement F2 detectors + sync 12.2.1a docs`
- **Izolacja `Z16` i `DEF-02` (`0 B` diffu względem `53751a4`):**
  - Wszystkie `30` plików chronionych Z16 (`avt_linter.py`, `verifier.py`, `client_factory.py`, `rules.py`, `test_system.py`, `verify_purity.py`, `pricing_guard.py`, `main.py`, `context_cache.py`, `series_memory/.onomastic_lexicon.json`, `series_memory/*_bible.json`), `scene_discourse.py` oraz metoda `_resolve_line_addressee` (`L4444..L4824` w `translator.py`) zachowują **`0 B` zmian** w historii commitów `53751a4..HEAD`.

---

## 1. Zestawienie Wdrożonych Napraw (`OBS-19`..`OBS-23`)

| ID | Plik(i) | Zakres i charakter rozwiązania | Charakter |
|---|---|---|---|
| `OBS-19` | [translator.py](../translator.py) | Wydzielono `_restore_phase2_trailing_period` wywołane w F2 post-processing: inspekcja końcowej interpunkcji na tekście widzialnym (bez tagów `{...}`) oraz wstawianie brakującej kropki bezpośrednio **przed** zamykającym blokiem tagów (np. `{\i0}`), bez dopisywania `.` po `}` (`0` wystąpień `....`). | 100% deterministyczny |
| `OBS-20` | [translator.py](../translator.py) | Dodano `_has_non_italic_alnum_text` oraz rozróżnienie w `extract_typesetting_tags`: dla kwestii w całości pisanych kursywą (również dwuwierszowych z `\N`) usuwane są zarówno `\i1`, jak i `\i0`; dla kursywy częściowej zachowywana jest pełna para `{\i1}...{\i0}` na początku `remaining`. | 100% deterministyczny |
| `OBS-21` | [translator.py](../translator.py) | Zaostrzono `is_generic_actor_or_category` (wrapper w `translator.py` bez ruszania `series_memory.py`), `_register_character_safe` oraz strażnik Whispera (`L4316`) przeciw tokenom bez znaków alfanumerycznych (`"/"`, `"//"`, `"-"`); w `_classify_collective_speaker_actor` bezaktorowe separatory zwracają `"DUAL_DIALOGUE"` tłumiące `FEMININE` / `POLYLOGUE (FEMININE)` w F1 i F2 bez wymuszania `Grupa_1os_lm`. | 100% deterministyczny |
| `OBS-22` | [sign_detector.py](../sign_detector.py), [translator.py](../translator.py) | Dodano `VisualSignDetector.is_near_existing_sign` (domyślnie `proximity_ms=3000`) i rozszerzono `detect_signs_in_gaps` o `custom_glossary`, `existing_events` i `sign_proximity_ms`: luki w pobliżu istniejącej planszy są pomijane **przed** ekstrakcją klatki i wywołaniem API, a pozostałe otrzymują zablokowany glosariusz w prompcie + deterministyczne uzgodnienie przez `enforce_locked_glossary_terms`. | 100% deterministyczny (filtr) / wspomagany (OCR) |
| `OBS-23` (cz. 1) | [profiler.py](../profiler.py), [translator.py](../translator.py) | Dodano `_split_catchphrase_variants` i `_map_catchphrase_variant_pairs` oraz przeorganizowano `resolve_profile_alerts_to_events`, `format_episode_profile_for_prompt` i fallbacki F1/F2 tak, by `character_catchphrases` miały priorytet nad `danger_lines_prescan` i tłumiły sprzeczne `pułapka_profilera` przy pokryciu tokenów (`len >= 4`). | 100% deterministyczny |
| `OBS-23` (cz. 2) | [translator.py](../translator.py) | Dodano pozytywną regułę F1 `_append_phase1_official_announcement_rule` (czystą pod kątem `Bramka 5B`) oraz detektory `_detect_polish_typo_anomaly` (`+40`) i `_detect_official_announcement_line` (`+30`) w `_score_phase2_editorial_risk`. | **Półdeterministyczny** *(zwiększa prawdopodobieństwo wyłapania błędów LLM w F2 bez 100% gwarancji generacyjnej)* |

---

## 2. Wyniki Testów Regresyjnych i Bramek Jakościowych

- **[test_standard_12_2_1.py](../tests/test_standard_12_2_1.py):** `6 / 6 PASSED` (`8.54s`), zero nazw własnych anime (`Z1`-clean).
- **Pakiet regresyjny `11.2.23..12.2.1` + `test_translator.py`:** **`95 passed in 47.45s`**.
- **Pełny pakiet `tests/`:** **`528 passed in 262.57s (0:04:22)`**.
- **`test_system.py` (`-m "not slow and not network" -k "not test_batch_coalescence_ssot_prompt_and_cot_streamlining_guard"`):** **`70 passed, 154 deselected in 22.42s`** (łącznie **`598 passed`**).
- **4 bramki kwalifikacyjne CI/CD:**
  - `verify_purity.py`: **`12/12 PASS`**
  - `verify_8_fixes.py`: **`8/8 PASS`**
  - `verify_12_fixes.py`: **`12/12 PASS`**
  - `verify_ultimate_pipeline.py`: **`15/15 PASS`**
- **Audyt śledczy i blokada Z16 (`tools/check_z16_lock.ps1` i `audit_diff.ps1`):**
  - `tools/check_z16_lock.ps1 -BaseRef "53751a4..HEAD"`: **`EXIT 0 — PASS - Z16 (0 B DIFF) & DEF-02 CHRONIONE`** *(na lokalnym working tree tej stacji istnieją sprzed zadania zmodyfikowane lokalnie przez uruchomienia runtime dwa pliki `series_memory/*_bible.json`, celowo nietknięte przez wdrożenie)*.
  - `audit_diff.ps1 -BaseRef "53751a4"` (po zacommitowaniu `tests/test_standard_12_2_1.py`): **`VICTORY CONFIRMED`** (`4/4` bramek PASS).

---

## 3. Weryfikacja Replayu Strukturalnego (`0.00 PLN`)

W katalogu `logs/` na tej stacji nie było surowego pliku `events.jsonl` z sesji docelowej, dlatego odtworzono deterministycznie wszystkie 6 klas wzorców wejściowych z raportu błędu przy użyciu funkcji produkcyjnych:

1. **Interpunkcja wewnątrz `{\i0}` i wielokropek:** brak dopisywania `.` po `}` (`0` wystąpień `....`).
2. **Wielowierszowa kursywa `\N`:** pełne zdjęcie `{\i1}` i `{\i0}` bez osieroconych tagów (`0` pół-kursyw).
3. **Dwugłos bezaktorowy `actor="/"`:** `"/"` nie trafia do `character_registry` ani `series_bible`, `_classify_collective_speaker_actor("/") == "DUAL_DIALOGUE"`, brak `POLYLOGUE (FEMININE)`.
4. **Bliskość plansz `Sign OCR` (`165290..168500` vs `170250..176540`):** `VisualSignDetector.is_near_existing_sign(..., proximity_ms=3000)` zwraca `True` i blokuje zbędne wywołanie API.
5. **Warianty rozdzielone `/` (`TermA / TermB`) w `character_catchphrases`:** `resolve_profile_alerts_to_events` podpina `KWESTIA-WIZYTÓWKA` i tłumi sprzeczne `pułapka_profilera` w obu liniach oraz w fallbackach F1/F2.
6. **Priorytetyzacja F2 (`ID 85` oficjalna zapowiedź + `ID 93` literówka `najibardziej`):** oba elementy selekcjonowane przez `_select_hydrogen_phase2_candidates` w paczce testowej (`>= p90`), podczas gdy zwykłe dialogi dostają `+0` punktów z nowych detektorów.

---

## 4. Suplement Mikro-Hotfix `12.2.1a` (`HEAD`)

Audyt jakościowy po wdrożeniu `40053a2` zidentyfikował `2` źródła fałszywych alarmów w detektorach scoringu F2 `OBS-23` oraz brakujący hash końcowy w dokumentacji (`BUG #1–#3`), zamknięte jednym atomowym commitem z **`0 B` diffu** w `30` plikach Z16, `scene_discourse.py`, `sign_detector.py`, `profiler.py` oraz `translator.py:_resolve_line_addressee`:

| ID | Waga | Zakres w [translator.py](../translator.py) | Rozwiązanie i efekt |
|---|---|---|---|
| `BUG #1` | WYSOKI | `L2606–2689`, `L7556` (`_detect_polish_typo_anomaly`) | Usunięto nadmiernie szeroką pętlę powtórzeń sylabowych `([a-ząćęłńóśźż]{2,3})\1` oraz nieużywaną stałą `_VALID_REPEATED_SYLLABLE_PREFIXES` (zero martwego kodu), eliminując fałszywe alarmy na rzeczownikach `-nienie` (`uwolnienie`, `wspomnienie`, `wyjaśnienie`, `zapomnienie`, `zatrudnienie`), wyrazach typu `lilie`/`Szszsz...` oraz imionach z powtórzoną sylabą; zachowano 3 wysokoprecyzyjne reguły (`naji...`, `jesterem`, `ji` + zbitka spółgłosek) i dodano izolację `not item.get("is_sign")`. |
| `BUG #2` | ŚREDNI | `L2606–2610`, `L7561` (`_EN_OFFICIAL_ANNOUNCEMENT_SCORE_RE`) | Usunięto ogólne `new\s+students` ze wzorca scoringowego (ujednolicając go z precyzyjnymi sygnałami zapowiedzi ceremonialnych) oraz odizolowano detektor od plansz ekranowych (`not item.get("is_sign")`) w `_score_phase2_editorial_risk`. |
| `BUG #3` | DROBNY | [PROJECT_MEMORY.md](../PROJECT_MEMORY.md), [Raport_wdrozenia_12.2.1.md](Raport_wdrozenia_12.2.1.md) | Zaktualizowano hash Commitu 3/3 `12.2.1` (`40053a2`), status na `CERTIFIED IN TESTS / AWAITING AUDIT` oraz rejestry testów po `12.2.1a`. |

- **Weryfikacja `12.2.1a` (`0.00 PLN`):**
  - [test_standard_12_2_1.py](../tests/test_standard_12_2_1.py): rozszerzone z `6` do **`7 / 7 PASSED`** (`test_obs23_12_2_1a_false_positive_protection`).
  - Pełny katalog `tests/`: **`529 / 529 PASSED`**.
  - `test_system.py -m "not slow and not network" -k "not test_batch_coalescence_ssot_prompt_and_cot_streamlining_guard"`: **`70 passed, 154 deselected`**.
  - `4/4` bramki CI/CD (`verify_purity.py` `12/12`, `verify_8_fixes.py` `8/8`, `verify_12_fixes.py` `12/12`, `verify_ultimate_pipeline.py` `15/15`), `check_z16_lock.ps1 -BaseRef "53751a4..HEAD"` (`PASS`) oraz `audit_diff.ps1 -BaseRef "40053a2"` (`VICTORY CONFIRMED`).
