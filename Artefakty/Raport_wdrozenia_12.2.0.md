# Raport Wdrożenia: Standard `12.2.0` (`OBS-13a/b/c`, `C-1` oraz autoryzowany `Z16-amendment #16`: `C-2`, `A-2`)

- **Data wydania:** `2026-11-26`
- **Gałąź / Baza startowa:** `main`, punkt wyjścia `bd4c76b` (`Standard 12.1.0 + 12.1.0a CLOSED`)
- **Model produkcyjny:** `gemini-4-hydrogen` (`D-1 Flash F1/F2 — REJECTED BY OPERATOR`, `AVT_CONSOLIDATE_F2="0"`)
- **Commity atomowe (`6/6`):**
  1. `7f897cd` — `fix(discourse): 12.2.0 [1/6] — OBS-13a local-window polylogue Z2 addressee guard & 6-8 line F1 history`
  2. `0581d27` — `fix(discourse): 12.2.0 [2/6] — OBS-13b collective/chorus speaker F0 shield & default VIRILE group`
  3. `bbdcbdb` — `fix(pipeline): 12.2.0 [3/6] — OBS-13c real target_confidence 0.90 Z2 gate & C-1 read-only F2 neighbors`
  4. `9947688` — `fix(z16): 12.2.0 [4/6] — Z16-amendment #16: genre-adaptive F2 tone (C-2) & Filar CLXXI numerical parser (A-2)`
  5. `e58358b` — `test(pipeline): 12.2.0 [5/6] — non-tautological production-schema tests for OBS-13a/b/c, C-1, C-2, A-2 & DEF-02/A-3`
  6. `HEAD` — `docs(release): 12.2.0 [6/6] — PROJECT_MEMORY (ARB-083, Z16-amendment #16, OBS-13 CLOSED, D-1 REJECTED) & Raport_wdrozenia_12.2.0`
- **Izolacja `scene_discourse.py` i pozostałych 27 plików Z16:** **`0 B` diffu** względem `bd4c76b` na `scene_discourse.py`, `scene_snapper.py`, `whisper_disambiguator.py`, `series_memory.py`, `profiler.py`, `client_factory.py`, `rules.py`, `test_system.py`, `verify_purity.py`, `pricing_guard.py`, `main.py`, `context_cache.py`, `series_memory/.onomastic_lexicon.json` oraz wszystkich `series_memory/*_bible.json`.

---

## 1. Zestawienie Wdrożonych Usprawnień (`OBS-13a/b/c`, `C-1`, `C-2`, `A-2`)

| Mechanizm | Plik(i) | Zakres i efekt architektoniczny |
|---|---|---|
| `OBS-13a` | [translator.py](../translator.py) | `_analyze_local_polylogue_window` analizuje okno `6` linii dialogowych w granicach `DEF-02` i blokuje zgadywanie `prev_interlocutor`/Lookahead przy krótkim 1–2-słownym wtrąceniu osoby trzeciej w polylogu (`>= 3` mówców), zachowując aktywny ping-pong oraz lokalne pytania 2. os. z natychmiastową odpowiedzią; historia F1 rozszerzona do `6` (diada) / `8` (polylog) linii przy utrzymaniu cap `4` w F2 oraz zgodności `test_system.py:6323`. |
| `OBS-13b` | [translator.py](../translator.py) | `_classify_collective_speaker_actor` chroni etykiety chóralne/zbiorowe (`BROTHERS`, `CROWD`, `ALL`, listy z separatorami `/ & + |`) przed dziedziczeniem płci `FEMININE` z wysokiego F0 (`251 Hz`), wymusza `Grupa_1os_lm=VIRILE` (lub `NON_VIRILE` wyłącznie dla potwierdzonych żeńskich grup w `SeriesBible`) i pomija sufiksy techniczne typu `/ID`. |
| `OBS-13c` | [translator.py](../translator.py) | `format_dry_telemetry_tag` utrzymuje domyślny próg `target_min_confidence=0.80` (100% zgodności wstecznej `TEST 178/178` w `test_system.py:17342–17348`), a wywołania produkcyjne w `_prepare_batch_prompt` i `_process_phase1_only` propagują rzeczywistą pewność z `_compute_effective_target_confidence` przy progu `target_min_confidence=0.90`, tłumiąc niepewne hipotezy `< 0.90` w telemetrii i `pass1_items`. |
| `C-1` | [translator.py](../translator.py) | `_attach_phase2_readonly_neighbor_context` dołącza skrócony kontekst sąsiednich pominiętych linii (`Poprzednia` / `Następna`, w ramach sceny `DEF-02`) wyłącznie do `notes` kandydatów F2 bez eskalacji CoT (`2048` LOW). |
| `C-2` | [verifier.py](../verifier.py), [translator.py](../translator.py) | `Z16-amendment #16` (`verifier.py:790`, `+1/-1`): usunięcie sztywnej frazy „u polskich nastolatków” na rzecz naturalnego stylu dostosowanego do gatunku, epoki i postaci; `_append_phase2_genre_tone_rule` przekazuje realia `setting_and_era` i `dominant_tone` do `focused_rules_str`. |
| `A-2` | [avt_linter.py](../avt_linter.py) | `Z16-amendment #16` (`avt_linter.py:7570–7579`, `+10/-2`): `EpisodeQualityGate` (`Filar CLXXI`) akceptuje angielskie separatory tysięcy (`1,500`, `1,250,000` ↔ `1500`, `1 250 000`) i wojskowe zapisy czasu (`1420 Hours` ↔ `14:20`) bez fałszywych alarmów, przy zachowaniu detekcji realnych mutacji liczb. |

---

## 2. Audyt 5 Warstw `Z16-amendment #16`

- **Warstwa 1 (`Z1` Zero-Literal Purity):** `verify_purity.py` zwróciło **`12/12 PASS`** — brak nazw własnych i zakazanych dyrektyw w kodzie oraz w `tests/test_standard_12_2_0.py`.
- **Warstwa 2 (`Z2` Pure Positive Domain):** niepewne hipotezy adresata (`< 0.90`) oraz wieloosobowe wtrącenia bez potwierdzonej wymiany pozostają w dziedzinie identycznościowej (`(None, None)`), a `Filar CLXXI` redukuje fałszywe alarmy dla separatorów tysięcy i godzin wojskowych.
- **Warstwa 3 (`Z3` Primary LLM Authority):** usunięcie arbitralnego rejestru „polskich nastolatków” w `verifier.py:790`; otwarte wskazówki gatunkowo-epokowe w `translator.py`.
- **Warstwa 4 (Prefiks Cache & Budżet CoT):** zmiana w `verifier.py:790` znajduje się w prompcie użytkownika poza `system_prompt` (`0 B` diffu w `rules.py` i `system_prompt`); budżet CoT pozostaje `2048` (LOW).
- **Warstwa 5 (Integralność regresyjna Z16):** `git diff --stat bd4c76b..HEAD` na Z16 ograniczony wyłącznie do `verifier.py` (`+1/-1`) i `avt_linter.py` (`+10/-2`); `0 B` diffu na pozostałych 27 plikach Z16 i `scene_discourse.py`.

---

## 3. Bramki `DEF-02`, Zestawy Testowe i Replay Offline

- **Bramki przyrostowe po Commitach 1–3:**
  - Po Commit `1/6` (`OBS-13a`): `87 passed in 19.97s` + `verify_purity.py 12/12 PASS`.
  - Po Commit `2/6` (`OBS-13b`): `87 passed in 18.37s` + `verify_purity.py 12/12 PASS`.
  - Po Commit `3/6` (`OBS-13c + C-1`): `87 passed in 17.74s` + `test_system.py` `70 passed, 154 deselected in 22.22s` + `verify_purity.py 12/12 PASS`.
- **Zestawy końcowe (`e58358b`):**
  - `tests/test_standard_12_2_0.py`: **9 passed in 18.91s**.
  - `tests/test_standard_11_2_23.py .. test_standard_12_1_0.py`: **49 passed in 25.89s**.
  - `tests/` (cały katalog): **518 passed in 198.33s (0:03:18)**.
  - `test_system.py -m "not slow and not network" -k "not test_batch_coalescence_ssot_prompt_and_cot_streamlining_guard"`: **70 passed, 154 deselected in 26.92s** (w tym `TEST 178/178` `format_dry_telemetry_tag`).
  - `verify_purity.py`: **12/12 PASS** | `verify_8_fixes.py`: **8/8 PASS** | `verify_12_fixes.py`: **12/12 PASS** | `verify_ultimate_pipeline.py`: **15/15 PASS**.
  - `audit_diff.ps1 -BaseRef "bd4c76b"`: **`VICTORY CONFIRMED -- KOD CZYSTY I UOGOLNIONY`**.
- **Offline replay na logach `12.0.0` (`0.00 PLN`):**
  - *Chii Fuyo-07* (`20261126_194433_events.jsonl`): `#322 ELSIE` → `(None, None), conf: 0.0` (brak fałszywego `Adresat: REIN`); `#8 BROTHERS` (`251 Hz`) → `has_FEMININE: False, has_VIRILE: True`; `A-3 LILY -> ELSIE` → `'na ty (Ty / Elsie / Mistrzyni)'`.
  - *Sasaki S2-08* (`20261126_195819_events.jsonl`): `#250/#259/#263/#270` (`Sasaki -> Shizuka`) → wszystkie `4` z `('kobieta', 'Shizuka (Kobieta)', 0.95, 'pan/pani (Futari Shizuko / pani Futari)')`; `#190` (`1,500 meters` → `1500 metrów`) & `#205` (`1420 Hours` → `14:20`) → `SAS_CLXXI_FALSE_ALARMS: []` (**0** fałszywych alarmów).
