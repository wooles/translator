# Raport Wdrożenia: Standard `12.1.0` (Pakiet A — Domknięcie Jakości z Benchmarku `12.0.0` + `OBS-16`)

- **Data wydania:** `2026-11-26`
- **Gałąź / Baza startowa:** `main`, punkt wyjścia `e6116ee` (`12.0.0b`)
- **Commity atomowe (`4/4`):**
  1. `6a4bbce` — `fix(pipeline): 12.1.0 [1/4] — F2 split-sentence & echo pair consistency guard (A-1)`
  2. `74b8820` — `fix(pipeline): 12.1.0 [2/4] — directional T-V register pinning, aristocratic title lock & spoken numeric expansion (A-3, A-4, A-5)`
  3. `bfc9b58` — `test(pipeline): 12.1.0 [3/4] — non-tautological production-schema tests for A-1, A-3, A-4, A-5 in tests/test_standard_12_1_0.py`
  4. `HEAD` — `docs(release): 12.1.0 [4/4] — PROJECT_MEMORY (OBS-16, D-1 REJECTED, 12.0.0b, ARB-082) & Raport_wdrozenia_12.1.0`
- **Izolacja Z16 i modułów zamrożonych:** **`0 B` diffu** względem `e6116ee` na wszystkich `29` plikach chronionych Z16 (`avt_linter.py`, `verifier.py`, `client_factory.py`, `rules.py`, `test_system.py`, `verify_purity.py`, `pricing_guard.py`, `main.py`, `context_cache.py`, `series_memory/.onomastic_lexicon.json`, `series_memory/*_bible.json`) oraz w `scene_discourse.py`, `scene_snapper.py`, `whisper_disambiguator.py` i `series_memory.py`.
- **Wyłączenia poza `12.1.0`:**
  - **`D-1` (Flash F1/F2):** definitywnie odrzucone (`REJECTED BY OPERATOR — quality-first policy; no model change in 12.x horizon`).
  - **`A-2` (`avt_linter.py` Filar CLXXI) & `OBS-13a/b/c`:** odroczone do `12.2.0` (wspólny `Z16-amendment #16`).
  - **`F-1` (`AVT_CONSOLIDATE_F2`):** pozostaje domyślnie wyłączone (`0`) zgodnie z `12.0.0b`.

---

## 1. Podsumowanie 4 Usprawnień (`A-1`, `A-3`, `A-4`, `A-5`)

| Mechanizm | Moduł | Problem z benchmarku `12.0.0` | Rozwiązanie w `12.1.0` |
|---|---|---|---|
| `A-1` | [translator.py](../translator.py) | Izolowana edycja F2 linii `#195` albo `#167` łamała składnię/przypadek względem niezweryfikowanego następnika `#196` / echa `#168` | Warstwa 1: `_is_split_sentence_pair` + `_is_lexical_echo_pair` parują sąsiada w `_select_hydrogen_phase2_candidates` (`<= 50%` paczki) z adnotacją `[Para spójności z #...]`. Warstwa 2: `_guard_phase2_split_pair_integrity` usuwa dopisane kropki lub cofa rozbite konflikty modalno-bezokolicznikowe przy niezweryfikowanym następniku |
| `A-3` | [translator.py](../translator.py) | Dryf formalnej formy (`pan/pani` -> `ty`) przez niedopasowanie aliasów lub odwrócony kierunek relacji asymetrycznych | `_resolve_tv_address_form` rozwiązuje zbiory aliasów mówcy i adresata w relacjach kierunkowych `LHS -> RHS` z `episode_profile` i `SeriesBible`, filtruje `[KOBIETA/MĘŻCZYZNA (Adresat) - ... 'ty']`, wstrzykuje dyrektywę w `_prepare_batch_prompt` oraz `[Zwrot T-V: ...]` do `notes` bez eskalacji CoT (`2048` LOW) |
| `A-4` | [translator.py](../translator.py) | Niespójny przekład powtarzających się tytułów arystokratycznych (`lady X` vs `panna X`) | `_extract_episode_honorific_title_locks` buduje słownikowy lock w RAM (`self.combined_glossary`, bez zapisu na dysk i z pierwszeństwem Kanonu/Biblii) oraz zasila `active_gloss_entries` przed `enforce_locked_glossary_terms` w F2 |
| `A-5` | [translator.py](../translator.py) | Biurowe skróty liczbowe (`500 mln!`, `5 tys.`) pojawiające się w dialogach mówionych po kondensacji F2 | `_expand_spoken_numeric_abbreviations` odmienia pełne liczebniki (`milion/miliony/milionów/miliona`, `miliard...`, `tysiąc...`) poza tagami `{...}` z ochroną plansz `is_sign=True`, wsparte regułą F2 `_append_phase2_numeric_hygiene_rule` |

---

## 2. Wyniki Testów, Bramek i Replayu Offline

### 2.1. Zestawy Testów i Bramki Jakościowe
- `pytest tests/test_standard_12_1_0.py -v`: **8 / 8 PASSED**.
- `pytest tests/test_standard_12_0_0.py tests/test_standard_11_2_23.py tests/test_standard_11_2_25.py -v`: **33 / 33 PASSED** (`26` + `5` + `2`).
- `pytest tests/ -q`: **506 passed**.
- `pytest test_system.py -m "not slow and not network" -k "not test_batch_coalescence_ssot_prompt_and_cot_streamlining_guard" -q`: **70 passed, 154 deselected**.
- `verify_purity.py`: **12/12 PASS** (`WERDYKT: 100% CZYSTY I ZGODNY Z STANDARDEM 9.0 — ZERO INSTANCJI I ZERO ŁAT`).
- `verify_8_fixes.py`: **PASS** (`8/8`).
- `verify_12_fixes.py`: **12/12 PASS**.
- `verify_ultimate_pipeline.py`: **15/15 PASS**.
- `audit_diff.ps1 -BaseRef "e6116ee"`: **WERDYKT: VICTORY CONFIRMED -- KOD CZYSTY I UOGOLNIONY**.

### 2.2. Offline Replay na Logach `12.0.0` (`0.00 PLN`)
- **`sasaki_to_pii_ASW__Sasaki_to_Pii-chan_S2_-_08__1080p_HEVC__2C78C80E__extracted_20261126_195819_events.jsonl`:**
  - `A-1` echo `#167–168`: wykryte (`True`) i sparowane w `_select_hydrogen_phase2_candidates` (`True, True`).
  - `A-1` zdanie rozbite `#195–196`: wykryte (`True`) i sparowane w `_select_hydrogen_phase2_candidates` (`True, True`).
  - `A-3` pary `#250/#259/#263/#270` (`Sasaki -> Shizuka`): wszystkie 4 rozwiązane jednoznacznie jako `'pan/pani (Futari Shizuko / pani Futari)'` z pełnym pominięciem odwrotnego kierunku `Shizuka -> Sasaki`.
  - `A-4` epizodyczne tytuły arystokratyczne: `{'Lady Elsa': 'lady Elsa'}` (w RAM, brak fałszywych dopasowań).
- **`chii_fuyo_ASW__Chii_Fuyo_-_07__1080p_HEVC__AB658E9E__extracted_20261126_194433_events.jsonl`:**
  - `A-4` epizodyczne tytuły: `{}` (czysto, zero fałszywych locków).
  - `A-5` linia `#355`: `"Pożyczę 500 mln!"` -> `"Pożyczę 500 milionów!"`.

---

## 3. Nowa Obserwacja Operacyjna (`OBS-16`)
- **`OBS-16` (`OPEN (non-blocking)`):** skrypty `.bat` uruchamiające potok nie dziedziczą zmiennych środowiskowych sesji PowerShell; zmienne sterujące wymagają jawnego `setlocal` + `set VAR=...`, wpisu w `.env` albo przekazania przez flagi CLI.
