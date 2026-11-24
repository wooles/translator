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


---

## 3. SUPLEMENT: HOTFIX 11.2.23a (ELIMINACJA 3 LUK Z AUDYTU KONFRONTACYJNEGO 4aae11a)

Hotfix 11.2.23a eliminuje 3 specyficzne luki produkcyjne wykryte w audycie konfrontacyjnym commita `4aae11a`:

1. **BUG #1 (`OBS-02`): Eliminacja samo-usuwania postaci P0 w deduplikacji `character_registry` (`translator.py`):**
   - W commicie `4aae11a` płaski zbiór `covered_aliases` powodował, że każda postać P0 posiadająca generyczny opis (np. `"postać (Postać)"` lub `"Postać epizodyczna / tło"`) dopisywała swoją własną nazwę do zbioru pokrytych aliasów, przez co usuwała samą siebie z renderowanego promptu (utrata 26 postaci P0 w symulacji produkcyjnej).
   - Wdrożono mapę `alias_owners` ze ścisłym porządkiem rang `rank = (1 if is_non_generic else 0, len(tokens), 1 if is_p0 else 0)`. Wpis generyczny jest pomijany wyłącznie wtedy, gdy istnieje **inny** właściciel (`o_low != name_low`) o **ściśle wyższej randze** (`o_rank > my_rank`). Ścisła nierówność całkowicie eliminuje samo-przykrycie oraz wycinanie wpisów równej rangi.

2. **BUG #2 (`DEF-03`): Odczyt produkcyjnego klucza `"speaker_name"` w `_is_speaker_change_lowercase` (`translator.py`):**
   - Produkcyjna pętla Fazy 1 zapisuje etykietę mówcy w słowniku `pass1_items` pod kluczem `"speaker_name"`, podczas gdy funkcja `_is_speaker_change_lowercase` odczytywała wyłącznie `"speaker"` i `"actor"`, zwracając `False` dla 100% linii w środowisku produkcyjnym.
   - Dodano odczyt `prev_item.get("speaker_name")` oraz `curr_item.get("speaker_name")` z zachowaniem pełnej kompatybilności wstecznej.

3. **BUG #3 (`DEF-02`): Okablowanie `scene_boundaries` z FFmpeg w `SceneDiscourseGraph.build_discourse_topology` (`scene_discourse.py` i `translator.py`):**
   - Produkcyjny punkt wejścia topologii dyskursu `SceneDiscourseGraph.build_discourse_topology` nie przyjmował parametru `scene_boundaries`, a `translator.py` wywoływało go bez przekazania wykrytych cięć `self.scene_cuts_ms`. W efekcie bramka cięcia FFmpeg dla pauz 2500–3499 ms pozostawała nieaktywna w produkcji.
   - Dodano parametr `scene_boundaries: Optional[List[int]] = None` do `build_discourse_topology` oraz `SceneDiscourseGraph.build_discourse_topology` i przekazano `scene_boundaries=getattr(self, "scene_cuts_ms", None)` z poziomu `translator.py`.

4. **Commity Hotfixu 11.2.23a:**
   - Commit 1 (`5f0ba5a`): `fix(pipeline): prevent P0 self-deletion in prompt registry dedup, read speaker_name in DEF-03 detector and wire FFmpeg scene_boundaries into SceneDiscourseGraph (11.2.23a)`
   - Commit 2 (`d0e23dd`): `test(pipeline): lock production speaker_name schema, P0 anti-self-deletion and SceneDiscourseGraph FFmpeg scene_boundaries wiring (11.2.23a)`
   - Commit 3 (`HEAD`): `docs(release): certify Hotfix 11.2.23a — P0 dedup rank guard, speaker_name DEF-03 wiring and FFmpeg scene_boundaries pass-through`
