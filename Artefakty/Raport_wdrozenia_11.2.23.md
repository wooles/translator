# 🏛️ RAPORT WDROŻENIOWY — STANDARD 11.2.23
## Certyfikacja Standardu 11.2.23 (Inflection-Aware Glossary Lock, Calibrated Speaker-Change Lowercase Risk, Scene-Cut Addressee Reset, Prompt Registry Dedup & RAM-Only Parent Gender Reconciliation)

- **Repozytorium:** `https://github.com/wooles/translator` (gałąź `main`)
- **Punkt wyjścia (HEAD baseline 11.2.22):** `16f574b2a13d34b2b634e9edfa4c461390c3e77c` (`16f574b`)
- **Commit 1 (Kod produkcyjny):** `44a61cf` (`fix(pipeline): inflection-aware glossary lock, calibrated speaker-change lowercase risk, scene-cut addressee reset, prompt registry dedup and RAM-only parent gender reconciliation (11.2.23)`)
- **Commit 2 (Testy i Certyfikacja Kodu):** `c33e220` (`test(pipeline): add 5 non-tautological regression tests for DEF-01, DEF-02, DEF-03, OBS-01 (RAM-only) and OBS-02 (11.2.23)`)
- **Commit 3 (Dokumentacja i Zamknięcie Wydania):** `HEAD` (`docs(release): certify Standard 11.2.23 — glossary inflection guard, P90 speaker-change risk, scene-cut addressee reset, registry dedup and RAM-only parent gender reconciliation`)
- **Baseline ochrony Z16 (Depuracja Legacy 1.0):** `c197db73c3dabf887dddbf2337dc3a1d8cff598c` (`c197db7` — **bezwzględne 0 B diffu na wszystkich 29 plikach chronionych Z16!**)
- **Data certyfikacji:** 2026-11-24
- **Koszt wykonania:** 0.00 PLN (100% lokalne silniki, brak zapytań chmurowych)

---

## 1. CEL I ZAKRES WDROŻENIA

Standard 11.2.23 rozwiązuje 5 kluczowych problemów jakościowych i optymalizacyjnych zidentyfikowanych w potoku AVT, uodparniając glosariusz na odmianę gramatyczną, kalibrując selekcję ryzyka redakcyjnego, zabezpieczając ciągłość dyskursu na granicach scen oraz redukując narzut tokenów w prompcie:

1. **MODUŁ A1 (`DEF-01`): Odporna na fleksję i `\\N` ochrona glosariusza (`translator.py:enforce_locked_glossary_terms`):**
   - W `enforce_locked_glossary_terms` zastąpiono sztywne dopasowanie podciągu `trans_low in cand_low` zaawansowaną normalizacją spacji/`\\N` oraz algorytmem dopasowania rdzeniowego (`_polish_stem`, `_term_preserved_in_candidate`).
   - Zachowuje poprawnie odmienione formy fleksyjne wielowyrazowych terminów (np. celownik, narzędnik) wprowadzone przez Fazę 2, zapobiegając cofaniu poprawnej odmiany do formy mianownikowej z Fazy 1.
   - Gdy termin z glosariusza zostanie całkowicie zastąpiony obcym słownictwem, zachowano deterministyczne przywrócenie kanonicznego terminu z Fazy 1.

2. **MODUŁ A2 (`DEF-03`): Wytyczna wielkiej litery F1 i skalibrowana waga P90 dla wejścia nowego mówcy (`translator.py:_select_hydrogen_phase2_candidates`):**
   - Doprecyzowano wytyczną interpunkcyjną w promptach F1: kontynuacja małą literą po wielokropku dotyczy wyłącznie wypowiedzi tego samego mówcy; wejście nowego mówcy rozpoczyna się wielką literą.
   - W `_select_hydrogen_phase2_candidates` zaimplementowano detekcję wejścia nowego mówcy z małą literą (`_is_speaker_change_lowercase`).
   - Waga ryzyka jest dynamicznie kalibrowana do 90. percentyla (`P90`) niezerowych ryzyk bieżącej paczki (`max(p90, 40)`), co gwarantuje zakwalifikowanie linii do selektywnej Fazy 2 w ramach sufitu `episode_line_cap = 115`.
   - Linia otrzymuje zwięzłą wskazówkę redakcyjną w `notes` bez eskalacji budżetu myślenia weryfikatora (utrzymanie ekonomicznego CoT `LOW 2048`).

3. **MODUŁ A3 (`DEF-02`): Reset propagacji adresata na cięciu sceny (`scene_discourse.py:resolve_turn_addressee`):**
   - Wprowadzono funkcję detekcji granicy sceny `_is_scene_cut_or_long_gap(prev_end, curr_start, scene_boundaries)`.
   - W przypadku pauzy międzyscenowej $\ge 3500$ ms LUB obecności cięcia montażowego FFmpeg przy pauzie $\ge 2500$ ms następuje deterministyczny reset domyślnego adresata (`target = UNSPECIFIED`, `target_gender = UNSPECIFIED`), eliminując fałszywe przenoszenie płci poprzedniego rozmówcy do nowej sceny.
   - Krótkie wymiany dialogowe wewnątrz sceny ($< 2500$ ms) zachowują naturalne łączenie z poprzednim mówcą.

4. **MODUŁ A4 (`OBS-02`): Deduplikacja aliasów w prompcie wejściowym (`translator.py:_prepare_batch_prompt`):**
   - W sekcji `ZNANE POSTACIE W ODCINKU` wdrożono deduplikację redundantnych wpisów o generycznych opisach (`Postać epizodyczna / tło`), których nazwa stanowi alias bogatszego wpisu kanonicznego P0.
   - Pozwala to zaoszczędzić około 1–2k tokenów na każdą paczkę bez jakiejkolwiek mutacji danych na dysku.

5. **MODUŁ B6 (`OBS-01`): Uzgadnianie płci rodzica w RAM (`series_memory.py:_sanitize_loaded_bible_in_ram`):**
   - W kroku `0e` metody `_sanitize_loaded_bible_in_ram` wdrożono automatyczne uzgadnianie płci i rodzaju gramatycznego rodzica na podstawie relacji (np. relacja 'Matka'/'Matko' wymusza `FEMALE` / `FEMININE`, relacja 'Ojciec'/'Ojcze' wymusza `MALE` / `MASCULINE`).
   - Zmiana zachodzi wyłącznie w strukturze danych w pamięci RAM, zachowując bezwzględne 0 B diffu na dysku w plikach `*_bible.json`.

6. **ŚWIADOME WYŁĄCZENIA POZA ZAKRES STANDARDU 11.2.23:**
   - `DEF-04` (`avt_linter.py:11419`): plik chroniony Z16 — odłożony do osobnego Standardu `11.2.24` (wymaga formalnej autoryzacji Z16-amendment #15).
   - `OBS-03` (`pricing_guard.py:379`): plik chroniony Z16 (kosmetyka etykiety logu) — poza zakresem `11.2.23`.
   - `OBS-04` (`pipeline_logger.py` — brak metody `log_retry`): odłożony do Standardu `11.2.25` w celu zachowania atomowości `11.2.23`.
   - Brak modyfikacji modelu kosztowego (Zero-Cache Lean, batching `56/64/44/36`, sufit `episode_line_cap = 115` nienaruszone).

---

## 2. METRYKI TESTÓW I WERYFIKACJI

- **Pakiet testów jednostkowych i integracyjnych:**
  - `420 passed` w `tests/` (w tym 5 nowych testów Standardu 11.2.23 w `test_standard_11_2_23.py`)
  - `71 passed, 153 deselected` w `test_system.py`
  - Łącznie: `491 passed` fast tests, `153 deselected`
- **4 bramki kwalifikacyjne potoku:**
  - `verify_purity.py`: 11/11 PASS (100% czysty kod AST, zero instancji onomastycznych)
  - `verify_8_fixes.py`: 8/8 PASS
  - `verify_12_fixes.py`: 12/12 PASS
  - `verify_ultimate_pipeline.py`: 15/15 PASS
- **Audyt śledczy diffu:**
  - `audit_diff.ps1 -BaseRef "16f574b"`: `WERDYKT: [VICTORY CONFIRMED -- KOD CZYSTY I UOGOLNIONY]`
- **Ochrona Z16:**
  - `git diff --stat c197db7..HEAD -- verifier.py client_factory.py rules.py avt_linter.py test_system.py verify_purity.py pricing_guard.py main.py context_cache.py series_memory/`: **0 B DIFF (BEZWZGLĘDNA CZYSTOŚĆ)**
