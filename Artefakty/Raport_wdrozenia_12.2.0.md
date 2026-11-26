# Raport Wdrożenia: Standard `12.2.0` + `12.2.0a` + `12.2.0b` (`OBS-13a/b/c`, `C-1` oraz autoryzowany `Z16-amendment #16`: `C-2`, `A-2`)

- **Data wydania:** `2026-11-26`
- **Gałąź / Baza startowa:** `main`, punkt wyjścia `bd4c76b` (`Standard 12.1.0 + 12.1.0a CLOSED`)
- **Model produkcyjny:** `gemini-4-hydrogen` (`D-1 Flash F1/F2 — REJECTED BY OPERATOR`, `AVT_CONSOLIDATE_F2="0"`)
- **Werdykt końcowy:** **`ACCEPT — STANDARD 12.2.0 CLOSED & CAŁA MAPA 12.x CLOSED`**
- **Commity atomowe (`6/6` + `12.2.0a` + `12.2.0b`):**
  1. `7f897cd` — `fix(discourse): 12.2.0 [1/6] — OBS-13a local-window polylogue Z2 addressee guard & 6-8 line F1 history`
  2. `0581d27` — `fix(discourse): 12.2.0 [2/6] — OBS-13b collective/chorus speaker F0 shield & default VIRILE group`
  3. `bbdcbdb` — `fix(pipeline): 12.2.0 [3/6] — OBS-13c real target_confidence 0.90 Z2 gate & C-1 read-only F2 neighbors`
  4. `9947688` — `fix(z16): 12.2.0 [4/6] — Z16-amendment #16: genre-adaptive F2 tone (C-2) & Filar CLXXI numerical parser (A-2)`
  5. `e58358b` — `test(pipeline): 12.2.0 [5/6] — non-tautological production-schema tests for OBS-13a/b/c, C-1, C-2, A-2 & DEF-02/A-3`
  6. `11bafcf` — `docs(release): 12.2.0 [6/6] — PROJECT_MEMORY (ARB-083, Z16-amendment #16, OBS-13 CLOSED, D-1 REJECTED) & Raport_wdrozenia_12.2.0`
  7. `de4aeb2` — `fix(12.2.0a): align F1 header with 0.90 Z2 gate, preserve dyadic/ping-pong T-V at 0.80 fallback, keep female-only collectives NON_VIRILE & word-safe C-2 truncation`
  8. `HEAD` — `docs(release): 12.2.0b — benchmark metrics, OBS-17/OBS-18 registry, final 12.x closure`
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

---

## 4. Suplement Mikro-Hotfix `12.2.0a` (`de4aeb2`)

Audyt konfrontacyjny przed płatnym benchmarkiem ujawnił `4` defekty w warstwie integracyjnej `translator.py` (wszystkie zamknięte atomowym commitem `de4aeb2` z **`0 B` diffu** w `verifier.py`, `avt_linter.py`, `scene_discourse.py` oraz pozostałych `27` plikach Z16 względem `11bafcf`):

| ID | Waga | Zakres w [translator.py](../translator.py) | Rozwiązanie i efekt |
|---|---|---|---|
| `BUG #1` | KRYTYCZNY | `L5360–5421` (`_prepare_batch_prompt`) | Obliczenie `poly_ctx_f1` i `eff_tgt_conf_f1` przeniesiono przed konstrukcję nagłówka `Kwestia [ID: ...]`; usunięto sprzeczność między nagłówkiem a `📡 TELEMETRIA` przy `< 0.90`. |
| `BUG #2` | WYSOKI | `L2230–2243` (`_compute_effective_target_confidence`) | Utrzymano pewność `0.92` (`>= 0.90`) dla potwierdzonego ping-ponga lub jednoznacznej lokalnej diady przy fallbacku `0.80` z `scene_discourse.py` (spadek utraconych linii diadycznych na *Chii Fuyo-07*: `37 → 0`, pełna ochrona `A-3` T-V na *Sasaki S2-08*). |
| `BUG #3` | ŚREDNI | `L2351–2364, 2430–2431` (`_classify_collective_speaker_actor`) | Wydzielono `_FEMALE_ONLY_COLLECTIVE_LABELS` (`sisters/girls/women/siostry/dziewczyny/kobiety`) dające domyślne `NON_VIRILE` także przy braku rekordu w `SeriesBible`. |
| `BUG #4` | DROBNY | `L2456–2509` (`_truncate_on_word_boundary`) | Bezpieczne ucinanie na granicy wyrazu z limitami `160` znaków (`era_summary`) i `80` znaków (`tone_summary`), eliminujące cięcie wyrazów w opisie epoki `C-2`. |

- **Weryfikacja `12.2.0a` (`de4aeb2`):**
  - [test_standard_12_2_0.py](../tests/test_standard_12_2_0.py): rozszerzone z `9` do **`13/13 PASSED`** (`tests/` łącznie **`522/522 PASSED`**).
  - Regresja `11.2.23..12.1.0`: **`49/49 PASSED`**.
  - `test_system.py -m "not slow and not network" -k "not test_batch_coalescence_ssot_prompt_and_cot_streamlining_guard"`: **`70 passed, 154 deselected`**.
  - `verify_purity.py`: **`12/12 PASS`**.

---

## 5. Wyniki Finalnego Benchmarku 2-Odcinkowego (`2026-11-26`, `de4aeb2`)

Benchmark wykonano na żywo na modelu `gemini-4-hydrogen` przy domyślnym `AVT_CONSOLIDATE_F2="0"` (tryb 1:1 Zero-Cache Lean).

### 5.1. Metryki kosztowe i techniczne

| Odcinek | Koszt netto (`brutto`) | Podział F1 / F2 | Tryb F2 / CoT | Linie F2 (szlify) | Czas | Błędy API / retry | Maks. CPL | Linie `> 22` CPS | Błędy ASS / `DEF-02` | Redukcja niepewnych `Adresat:` |
|---|---|---|---|---|---|---|---|---|---|---|
| *Chii Fuyo-07* | `4.59 PLN` (`~5.65 PLN`) | `2.82` / `1.77` | 1:1 (`8/8` paczek) / `2048 LOW` | `117/386` (`29`) | `5 min 12 s` | `0` / `0` | `40` | `0` | `0` / `0` | `247 → 143` |
| *Sasaki S2-08* | `3.85 PLN` (`~4.74 PLN`) | `2.35` / `1.51` | 1:1 (`6/6` paczek) / `2048 LOW` | `123/326` (`20`) | `4 min 25 s` | `0` / `0` | `41` | `1` okrzyk `22.5` (`#2`) | `0` / `0` | `190 → 133` |
| **Łącznie** | **`8.44 PLN netto`** (`~10.39 PLN`, śr. `~4.22 PLN/odc.` `<= 6.00 PLN`) | `5.17` / `3.28` | `1:1` / `2048 LOW` | `240/712` (`49`) | `9 min 37 s` | **`0` / `0`** | `41` | `1` okrzyk | **`0` / `0`** | `437 → 276` |

### 5.2. Weryfikacja punktów kontrolnych (`10/10 PASS`)

| Punkt kontrolny | Obszar / mechanizm | Zweryfikowany wynik na żywo | Status |
|---|---|---|---|
| `A-1` | Spójność par w F2 | Prawidłowe domknięcie echa `#167–168` oraz zdania rozbitego `#195–196` | `PASS` |
| `A-2` | `Filar CLXXI` parser liczb | `1500 metrów` oraz `14:20` bez fałszywych alarmów liczbowych | `PASS` |
| `A-3` (Sasaki) | Kierunkowy T-V | `4/4` `pani` na relacji *Sasaki → Shizuka* | `PASS` |
| `A-3` (Chii) | Kierunkowy T-V | `100%` `na ty` (*Lily → Elsie*) oraz `panie prezesie` (*Margaret → CEO*) | `PASS` |
| `A-4` | Lock tytułów arystokratycznych | `3/3` konsekwentne `lady Elsa` w całym odcinku | `PASS` |
| `A-5` | Ekspansja liczebników mówionych | Poprawna pełna forma mówiona `500 milionów!` | `PASS` |
| `OBS-13a` | Lokalny polylog Z2 | `#322`: poprawne `obwinialibyście się, gdybyście wiedzieli` bez błędnego adresata | `PASS` |
| `OBS-13b` | Chór / mówca zbiorowy | `BROTHERS` i `ALL` bez etykiety `FEMININE`, z `Grupa_1os_lm: VIRILE` | `PASS` |
| `OBS-13c + C-1` | Próg pewności `0.90` i sąsiedzi F2 | Spójna redukcja niepewnych `Adresat:` (`247 → 143` oraz `190 → 133`) przy zachowaniu diad (`0` utraconych na *Chii*) | `PASS` |
| `C-2` | Rejestr gatunkowo-adaptacyjny F2 | `0` wystąpień narzuconej frazy „u polskich nastolatków” w promptach F2 | `PASS` |

### 5.3. Obserwacje nieblokujące i zamknięcie mapy `12.x`

- **`OBS-17` (`NISKI` — `OPERATIONAL / NO CODE ACTION`):** `Local series_bible JSON has historical gender distortion (Lily Flambert: MALE); operator-level fix, not code-level` — lokalny plik JSON poza repozytorium git; mimo zniekształcenia osiągnięto `0/52` błędów płci mówcy i `0/25` adresata w polskim tekście dzięki profilowi i audio; korekta ręczna w lokalnym pliku JSON Operatora.
- **`OBS-18` (`NISKI` — `OPEN / MONITOR ONLY`):** `Occasional LLM micro-variants` (drobna wielkość liter / dobór leksykalny po korekcie F2, np. `#322` mała litera po wielokropku poprzedniego mówcy, `#363` `'dojść'` vs `'dołączyć'`); bez ingerencji w kod, chyba że wzorzec powtórzy się `>= 3` razy w pojedynczym odcinku.
- **Decyzja strategiczna i kierunek post-12.x:** Potwierdzono **`D-1 (Flash F1/F2) — REJECTED BY OPERATOR`**, flagowym modelem produkcyjnym pozostaje `gemini-4-hydrogen` przy `AVT_CONSOLIDATE_F2="0"`. Łańcuch `e6116ee` (`12.0.0b`) → `bd4c76b` (`12.1.0a`) → `de4aeb2` (`12.2.0a`) → `HEAD` (`12.2.0b`) zamyka **całą mapę `12.x` (`CLOSED — ACCEPT`)** z wyborem **Opcji A (produkcja)** bez prewencyjnego otwierania `12.3.0`/`13.x`.
