# RAPORT AUDYTU WERYFIKACYJNEGO — STANDARD 11.0 (KOŃCOWY)
## WERYFIKACJA IMPLEMENTACJI `FIX-C.1`–`FIX-E.2` NA `HEAD` `8c0037f` WZGLĘDEM `PROMPT_11.0.md` ORAZ `Raport_audytu_konfrontacyjnego_11_0.md`

- **Plik docelowy raportu:** `Artefakty/Raport_audytu_weryfikacyjnego_11_0_koncowy.md`[cite: 28, 31]
- **Repozytorium zdalne (fresh clone):** `https://github.com/wooles/translator`[cite: 28, 31]
- **HEAD zweryfikowany:** `8c0037f8303f50201e30dda68d992ee867c984d9` (`8c0037f` — Standard 11.0, Commit 3)[cite: 28, 31]
- **Baseline 11.0 (Standard 10.6.3):** `8d3d299` (`8d3d2990e16314490bbb4defe63e14ab777ca48d`)[cite: 28, 31]
- **Commit 1 (`FIX-C.1` + `FIX-C.2`):** `941fe44` (`941fe44cfe0220ad6d877c769089db5d1781226b`)[cite: 28, 31, 32]
- **Commit 2 (`FIX-C.3`):** `fb94a02` (`fb94a029b67627b2d9bdff6c67f509b9edc8c3b2`)[cite: 28, 31, 32]
- **Commit 3 (`FIX-E.1` + `FIX-E.2`):** `8c0037f` (`8c0037f8303f50201e30dda68d992ee867c984d9`)[cite: 28, 31]
- **Baseline Depuracji Legacy 1.0 (Z16):** `474fb64`[cite: 28, 31]
- **Data audytu weryfikacyjnego:** 2026-11-06[cite: 28, 31]
- **Audytor:** Niezależny Audytor Weryfikacyjny AVT (Tryb Read-Only, GitHub-fresh)[cite: 28, 31]
- **Tryb pracy:** **STRICTLY READ-ONLY** — `0` zmian w kodzie, `0` commitów, `0` `git push`[cite: 28, 31].

---

## 1. EXECUTIVE SUMMARY — WERDYKT AUDYTU WERYFIKACYJNEGO 11.0

**WERDYKT KOŃCOWY:**
**`STANDARD 11.0 W PEŁNI BEZPIECZNY (5/5 operacji bezpiecznych, 13/13 warunków spełnionych)`**[cite: 28, 31]

Bezpośrednia inspekcja kodu na świeżo sklonowanym drzewie `HEAD` (`8c0037f8303f50201e30dda68d992ee867c984d9`) potwierdziła w 100%, że wszystkie 12 szczegółowych korekt architektonicznych wymaganych przez `Raport_audytu_konfrontacyjnego_11_0.md` oraz `PROMPT_11.0.md` zostało fizycznie wdrożonych w kodzie produkcyjnym (`series_memory.py` i `scene_discourse.py`) oraz pokrytych 15 funkcjami testowymi (`20` przypadków uruchomieniowych `pytest` po rozwinięciu `@pytest.mark.parametrize`)[cite: 28, 29, 31]:

| ID | Operacja | Werdykt weryfikacyjny | Potwierdzone korekty w kodzie `8c0037f` |
| :--- | :--- | :---: | :--- |
| **`FIX-C.1`** | Ekstrakcja `TOPONYM` instytucjonalnych | **`BEZPIECZNA`** | **K1 + K2 wdrożone:** `_extract_institutional_toponyms` (`series_memory.py:5644–5663`) i `_register_institutional_toponyms_from_sources` (`series_memory.py:5665–5691`) skanują `anilist_meta["description"]`, `episode_profile.episode_summary`, `episode_profile.setting_and_era`, `episode_profile.glossary` (`dict` i `list` w liniach `5047–5062`) oraz `self.data["glossary"]` i `plot_anchors` (`linie 5671–5678`). Twarda blokada `if tok in chars_dict: continue` (`linia 5685`) chroni klucze główne `characters`[cite: 28, 29]. |
| **`FIX-C.2`** | Z16-safe alias deduplication | **`BEZPIECZNA`** | **K1 + K2 + K3 wdrożone:** Zbiór `conflicting_surnames` rozszerzony w obu miejscach — w `_sanitize_loaded_bible_in_ram` (`series_memory.py:6577–6585`) oraz w `_rebuild_actor_aliases_index` (`series_memory.py:7601–7609`) — wyłącznie o `self.data.get("institutional_toponyms")` (bez globalnego `KNOWN_FANTASY_TOPONYMS` i bez ustawiania `bible_modified = True`)[cite: 28, 29]. |
| **`FIX-C.3`** | Prepositional guard + kontekstowa ochrona | **`BEZPIECZNA`** | **K1 + K2 wdrożone:** `is_non_character_entity(self, name: str, context: Optional[str] = None)` (`series_memory.py:8768–8793`) binduje przyimek bezpośrednio do `re.escape(clean_n)` (`linia 8789`), a `_detect_event_vocative` (`scene_discourse.py:1326–1473`) odrzuca dopełnienia przyimkowe przez `_is_prepositional_context` w krokach `1b` (`linia 1419`), `1c` (`linia 1428`) i `5` (`linia 1468`) oraz wywołuje `is_non_character_entity(cand, context=clean)` (`linia 1406`)[cite: 28, 29]. |
| **`FIX-E.1`** | CamelCase split | **`BEZPIECZNA`** | **K1 + K2 + K3 wdrożone:** `_split_camel_case_tokens` (`series_memory.py:1931–1939`) użyte w `populate_secondary_actor_tags` (`linia 7100`), podział `CamelCase` dodany w `resolve_lexical_label_gender` (`linie 1956–1958`), aktualizacja istniejących wpisów `UNKNOWN` odblokowana w linii `7043–7045` (oraz dodatkowo w liniach `7068–7075` i `7081–7082`), a krok `8b` chroni pary z sufiksem cyfrowym przez `and not is_numeric_suffix_pair` (`linie 6856–6869`)[cite: 28, 29]. |
| **`FIX-E.2`** | `Mob*` isolation + deiktyki 3. os. | **`BEZPIECZNA`** | **K1 + K2 wdrożone:** Filtr deiktyków 3. os. (`_DEICTIC_3RD_PERSON_PAT`, `_split_clauses`, `_is_deictic_3rd_person_clause` w `scene_discourse.py:1355–1389`) działa **per klauzula**, a izolacja `_is_mob_or_crowd_speaker` (`linie 1341–1352`) zabezpiecza zarówno Krok 3 (`linia 2584`), jak i Krok 4 (`linie 2603–2608`) bez wczesnego `return turn`, zachowując propagację metadanych na `turn.events` (`linie 2636–2649`)[cite: 28, 29]. |

Wszystkie 4 rozbieżności z Fazy 0 (`R1`–`R4`) zostały jednoznacznie wyjaśnione i rozstrzygnięte w Sekcji 2 bez jakiegokolwiek naruszenia Z16 (`git diff 8d3d299..8c0037f` na plikach Z16 wynosi dokładnie `0 B`)[cite: 28, 31].

---

## 2. FAZA 0 — FRESH READ I ROZSTRZYGNIĘCIE 4 ROZBIEŻNOŚCI (`R1`–`R4`)

### 2.1. Rozstrzygnięcie 4 rozbieżności (`R1`–`R4`)

| # | Rozbieżność | Jednoznaczne rozstrzygnięcie audytora (w oparciu o kod i AST na `8d3d299` oraz `8c0037f`) | Werdykt |
| :---: | :--- | :--- | :---: |
| **`R1`** | Liczba testów w `tests/`: `310` vs `325` vs `330`[cite: 28, 31] | **Wyjaśnienie matematyczne z AST i `pytest --co -q`:**<br>1) Na commicie bazowym `8d3d299` (Standard 10.6.3) pakiet `tests/` (z wyłączeniem ignorowanego w `pytest.ini:5` katalogu `tests/archive`) liczył dokładnie **310** jednostek testowych (`items`).<br>2) W Standardzie 11.0 (`8c0037f`) dodano dokładnie **15 nowych funkcji testowych** (`T11.0_C_1`–`T11.0_C_8` oraz `T11.0_E_1`–`T11.0_E_7`).<br>3) Funkcja `test_t11_0_c_1_extract_institutional_toponyms_patterns` (`tests/test_series_memory.py:1212–1223`) jest udekorowana `@pytest.mark.parametrize` z **6 przypadkami testowymi**, co daje `14 * 1 + 1 * 6 = 20` nowych jednostek uruchomieniowych `pytest` (`items`).<br>4) Stąd: `310 (baseline 8d3d299) + 20 (nowe items z 15 funkcji T11.0_*) = 330 passed` na `8c0037f`! Liczba `325` w `PROMPT_11.0.md` (i przepisana przez agenta w opisie Sekcji 0.10 raportu) wynikała z prostego dodania `310 + 15 funkcji = 325` bez uwzględnienia 6-krotnej parametryzacji `T11.0_C_1` (`+5 items`)[cite: 28, 29, 32]. | **ROZSTRZYGNIĘTA (`310 + 20 = 330 items` z `15` funkcji)** |
| **`R2`** | `verify_purity.py`: `11/11` vs `12/12` bramek[cite: 28, 31] | **Plik `verify_purity.py` ma `0 B` zmian pomiędzy `8d3d299` a `8c0037f`!**<br>W `verify_purity.py:161–174` lista `gates` ma **12 elementów**, ale ponieważ Bramka 5 jest podzielona na dwie podbramki (`Bramka 5A: Zakaz słów ALL-CAPS w tekście` oraz `Bramka 5B: Zakaz preskryptywności i zakazów`), ostatnia bramka nosi etykietę **`Bramka 11: Wymóg default strict_positive_domain=True`**. Część raportów podawała liczbę pozycji na liście (`12/12`), a część numer ostatniej bramki (`11/11`) — żadna bramka nie została usunięta ani zmodyfikowana[cite: 28, 32]. | **ROZSTRZYGNIĘTA (`0 B` diff, `12` elementów o numerach `1..5A,5B..11`)** |
| **`R3`** | Hash Commit 3: `HEAD` w raporcie vs `8c0037f`[cite: 28, 31] | Pełny hash Commitu 3 (`HEAD` gałęzi `main`) to **`8c0037f8303f50201e30dda68d992ee867c984d9`** (`8c0037f`). W `Raport_wdrozenia_11.0.md` wpisano `HEAD`, ponieważ plik raportu był commitowany wewnątrz samego Commitu 3 (w chwili zapisywania pliku przed wykonaniem `git commit` jego własny hash SHA-1 z definicji funkcji skrótu Git nie istnieje jeszcze do momentu zamknięcia drzewa commita)[cite: 28, 32]. | **ROZSTRZYGNIĘTA (`HEAD == 8c0037f`)** |
| **`R4`** | Obecność `Artefakty/Raport_wdrozenia_11.0.md` w git[cite: 28, 31] | Plik `Artefakty/Raport_wdrozenia_11.0.md` **znajduje się w repozytorium git wewnątrz Commitu 3 (`8c0037f8303f50201e30dda68d992ee867c984d9`)** (rozmiar `14 553 B`, `205` linii, `0` placeholderów) — zgodnie z wymogiem `PROMPT_11.0.md` §3.7[cite: 28, 29, 32]. | **ROZSTRZYGNIĘTA (obecny w `8c0037f`)** |

---

### 2.2. Surowe wyjścia komend diagnostycznych (Grupy A–M)

```text
=== GRUPA A & D: Weryfikacja HEAD i 3 commitów 11.0 ===
$ git log --oneline -n 5
8c0037f feat(series_memory,scene_discourse): Standard 11.0 - CamelCase split and Mob* speaker isolation
fb94a02 feat(series_memory,scene_discourse): Standard 11.0 - prepositional guard for vocative and toponym context
941fe44 feat(series_memory): Standard 11.0 - institutional toponym detection and Z16-safe alias deduplication
8d3d299 docs: Hotfix 10.6.3 - uzupelnienie raportu (FIX-D.4, FIX-D.5, N-08, INC-AVT-010) i statystyki git
ed226d0 fix(series_memory,metadata): Hotfix 10.6.3 - fix _resolve_bible_path season matching and consolidate split bibles

$ git log -n 1 --format=%H
8c0037f8303f50201e30dda68d992ee867c984d9

$ git rev-parse HEAD fb94a02 941fe44 8d3d299
8c0037f8303f50201e30dda68d992ee867c984d9
fb94a029b67627b2d9bdff6c67f509b9edc8c3b2
941fe44cfe0220ad6d877c769089db5d1781226b
8d3d2990e16314490bbb4defe63e14ab777ca48d

$ git status
On branch main
nothing to commit, working tree clean

=== GRUPA B: Rozstrzygnięcie R1 — liczba testów ===
- Na 8d3d299 (pytest tests/ --co -q): 310 tests collected
- Na 8c0037f (pytest tests/ --co -q): 330 tests collected
  Rozkład po plikach w tests/ na 8c0037f:
  * tests/test_avt_linter.py: 33 items
  * tests/test_discourse_and_translator.py: 51 items (46 bazowych + 5 nowych funkcji T11.0_*)
  * tests/test_flight_recorder.py: 1 item
  * tests/test_hygiene.py: 10 items
  * tests/test_metadata.py: 15 items
  * tests/test_profiler.py: 67 items
  * tests/test_series_memory.py: 95 items (80 bazowych + 10 funkcji T11.0_* dających 15 items z uwagi na 6-krotną parametryzację T11.0_C_1)
  * tests/test_translator.py: 14 items
  * tests/test_verifier.py: 44 items
  Suma: 33 + 51 + 1 + 10 + 15 + 67 + 95 + 14 + 44 = 330 items (+20 items z 15 nowych funkcji testowych T11.0_*).

=== GRUPA C: Rozstrzygnięcie R2 — verify_purity.py ===
$ python3 -X utf8 verify_purity.py
============================================================================================
🛡️  CERTYFIKACJA ARCHITEKTURY: ZERO-LITERAL & INSTANCE-FREE METALINGUISTIC (STANDARD 9.0)
============================================================================================
[PASS] Czysto                    | Bramka 1: Składnia i integralność AST
[PASS] Czysto                    | Bramka 2: Zakaz instancji (np. [Nazwa])
[PASS] Czysto                    | Bramka 3: Zakaz cytowanych dialogów w regułach
[PASS] Czysto                    | Bramka 4: Zakaz etykiet kontrastowych i '[OK]'
[PASS] Czysto                    | Bramka 5A: Zakaz słów ALL-CAPS w tekście
[PASS] Czysto                    | Bramka 5B: Zakaz preskryptywności i zakazów
[PASS] Czysto                    | Bramka 6: Zakaz alarmów w promptach i kodzie
[PASS] Czysto                    | Bramka 7: Zakaz zahardkodowanych slugów serii
[PASS] Czysto                    | Bramka 8: Zakaz statycznych kolekcji nazw w AST
[PASS] Czysto                    | Bramka 9: Zakaz ręcznych łat odmian (variants.update)
[PASS] Czysto                    | Bramka 10: Czystość kodu DSP/NumPy (brak _np.)
[PASS] Czysto                    | Bramka 11: Wymóg default strict_positive_domain=True
============================================================================================
🏆 WERDYKT: [100% CZYSTY I ZGODNY Z STANDARDEM 9.0 — ZERO INSTANCJI I ZERO ŁAT]

$ git diff 8d3d299..8c0037f -- verify_purity.py
(pusty — 0 B zmian)

=== GRUPA E: Rozstrzygnięcie R4 — Artefakty/Raport_wdrozenia_11.0.md ===
$ git diff 8d3d299..8c0037f --name-only | grep -E "Raport_wdrozenia_11"
Artefakty/Raport_wdrozenia_11.0.md

=== GRUPA F: Z16 diff (8d3d299..8c0037f) ===
$ git diff 8d3d299..8c0037f -- test_system.py tests/archive/ avt_linter.py pytest.ini rules.py series_memory/ verifier.py verify_purity.py
(pusty — dokładnie 0 B zmian!)

=== GRUPA G: Pełna lista zmodyfikowanych plików w 8d3d299..8c0037f ===
- Artefakty/Raport_wdrozenia_11.0.md (nowy plik, 205 linii)
- PROJECT_MEMORY.md (zaktualizowano statusy N-06 i N-07 na RESOLVED)
- scene_discourse.py (+70 linii: _PREPOSITION_BEFORE_CAND_PAT, _is_prepositional_context, _MOB_CROWD_PAT, _is_mob_or_crowd_speaker, _DEICTIC_3RD_PERSON_PAT, _split_clauses, _is_deictic_3rd_person_clause, aktualizacje w _detect_event_vocative i resolve_turn_addressee)
- series_memory.py (+141 linii: _INSTITUTIONAL_TOPONYM_PATTERNS, _GENERIC_TOPONYM_BLOCKLIST, _extract_institutional_toponyms, _register_institutional_toponyms_from_sources, conflicting_surnames w kroku d i _rebuild_actor_aliases_index, is_non_character_entity(context), _split_camel_case_tokens, resolve_lexical_label_gender, is_numeric_suffix_pair w kroku 8b, aktualizacja UNKNOWN w populate_secondary_actor_tags)
- tests/test_discourse_and_translator.py (+122 linie: 5 testów T11.0_C_6, T11.0_C_7, T11.0_E_5, T11.0_E_6, T11.0_E_7)
- tests/test_series_memory.py (+180 linii: 10 testów T11.0_C_1..5, T11.0_C_8, T11.0_E_1..4)

=== GRUPA L & M: G-Q2 Golden Corpus, 15 testów T11.0_* oraz 5 pułapek Z16 ===
G-Q2 PASS: 5/5 synthetic golden cases unchanged
T11.0_C_1 (6/6), T11.0_C_2..8, T11.0_E_1..7: 20/20 items PASSED (15/15 funkcji testowych)
Z16-P1, Z16-P2, Z16-P3, Z16-P4, Z16-P5: 5/5 PASSED
verify_purity.py: PASS | verify_8_fixes.py: 8/8 PASS | verify_12_fixes.py: 12/12 PASS | verify_ultimate_pipeline.py: 15/15 PASS
```

---

### 2.3. Odpowiedzi na pytania flagowe `F0.1`–`F0.12`

- **F0.1:** **TAK.** Hash `HEAD` to `8c0037f8303f50201e30dda68d992ee867c984d9`[cite: 28, 31].
- **F0.2:** **TAK.** Kolejność 3 ostatnich commitów na `main` to `8c0037f` (Commit 3), `fb94a02` (Commit 2), `941fe44` (Commit 1), a bezpośrednio przed nimi `8d3d299` (baseline 10.6.3)[cite: 28, 31, 32].
- **F0.3 (R1):** Na `8d3d299` w `tests/` było **310** items, a na `8c0037f` jest **330** items — różnica to **15 nowych funkcji testowych**, które dają **20 items** w `pytest` z uwagi na 6-krotną parametryzację `@pytest.mark.parametrize` w `test_t11_0_c_1_extract_institutional_toponyms_patterns` (`tests/test_series_memory.py:1212–1223`)[cite: 28, 29, 32].
- **F0.4 (R2):** `verify_purity.py` ma **12 elementów kontrolnych** oznaczonych numerami od `Bramka 1` do `Bramka 11` (gdyż Bramka 5 dzieli się na `Bramka 5A` i `Bramka 5B`). Diff `git diff 8d3d299..8c0037f -- verify_purity.py` wynosi **`0 B`**[cite: 28, 32].
- **F0.5 (R3):** **TAK.** Pełny hash `8c0037f` to `8c0037f8303f50201e30dda68d992ee867c984d9`[cite: 28, 31].
- **F0.6 (R4):** Plik `Artefakty/Raport_wdrozenia_11.0.md` został dodany bezpośrednio w Commicie 3 (`8c0037f`)[cite: 28, 32].
- **F0.7:** **TAK.** Diff na wszystkich zamrożonych plikach i katalogach Z16 (`test_system.py`, `tests/archive/`, `avt_linter.py`, `pytest.ini`, `rules.py`, `series_memory/`, `verifier.py`, `verify_purity.py`) wynosi dokładnie **`0 B`**[cite: 28, 31].
- **F0.8:** **TAK.** `pytest test_system.py -q` zwraca `71 passed, 153 deselected`[cite: 28, 32].
- **F0.9:** **TAK.** Wszystkie 5 pułapek Z16 (`Z16-P1`..`Z16-P5`) zwraca `PASS`[cite: 28, 32].
- **F0.10:** **TAK.** Wszystkie 4 bramki CI/CD (`verify_purity.py`, `verify_8_fixes.py`, `verify_12_fixes.py`, `verify_ultimate_pipeline.py`) oraz `audit_diff.ps1` zwracają `PASS`[cite: 28, 32].
- **F0.11:** **TAK.** Skrypt `G-Q2` zwraca `G-Q2 PASS: 5/5 synthetic golden cases unchanged`[cite: 28, 29, 32].
- **F0.12:** **TAK.** W `tests/` znajduje się dokładnie **15 nowych funkcji testowych** `test_t11_0_*` (`10` w `tests/test_series_memory.py` oraz `5` w `tests/test_discourse_and_translator.py`)[cite: 28, 29, 32].

---

## 3. FAZA 1 — WERYFIKACJA `FIX-C.1` (EKSTRAKCJA `TOPONYM` INSTYTUCJONALNYCH)

### 3.1. Porównanie 3 źródeł (Specyfikacja vs Audyt Konfrontacyjny vs Kod `8c0037f`)

1. **Korekta K1 (Skanowanie `episode_profile`, `glossary` i `plot_anchors` oprócz `anilist_meta["description"]`):**
   - **Dowód w kodzie (`8c0037f:series_memory.py:5041–5062`):**
     ```python
     5041:             # Standard 11.0 (FIX-C.1): Ekstrakcja institutional_toponyms z metadanych i profilu odcinka
     5042:             extra_src: List[str] = []
     5043:             if isinstance(anilist_meta, dict):
     5044:                 desc_meta = anilist_meta.get("description")
     5045:                 if isinstance(desc_meta, str) and desc_meta:
     5046:                     extra_src.append(desc_meta)
     5047:             if episode_profile is not None:
     5048:                 for attr in ("episode_summary", "setting_and_era"):
     5049:                     val = getattr(episode_profile, attr, None)
     5050:                     if isinstance(val, str) and val:
     5051:                         extra_src.append(val)
     5052:                 ep_glossary = getattr(episode_profile, "glossary", None)
     5053:                 if isinstance(ep_glossary, dict):
     5054:                     extra_src.extend(str(k) for k in ep_glossary.keys())
     5055:                     extra_src.extend(str(v) for v in ep_glossary.values() if isinstance(v, str))
     5056:                 elif isinstance(ep_glossary, list):
     5057:                     for g_item in ep_glossary:
     5058:                         for g_attr in ("term_en", "translation_pl", "explanation"):
     5059:                             g_val = getattr(g_item, g_attr, None)
     5060:                             if isinstance(g_val, str) and g_val:
     5061:                                 extra_src.append(g_val)
     5062:             self._register_institutional_toponyms_from_sources(extra_src)
     ```
   - Dodatkowo w `_register_institutional_toponyms_from_sources` (`8c0037f:series_memory.py:5671–5678`) skanowane są `self.data["glossary"]` oraz `self.data["plot_anchors"]`, a metoda jest wywoływana również w `_sanitize_loaded_bible_in_ram` (`linia 6551`)[cite: 28, 29].
2. **Korekta K2 (Blokada nadpisywania istniejących kluczy głównych w `characters`):**
   - **Dowód w kodzie (`8c0037f:series_memory.py:5682–5691`):**
     ```python
     5682:         chars_dict = self.data.get("characters", {})
     5683:         existing = set(self.data.get("institutional_toponyms") or [])
     5684:         for tok in candidates:
     5685:             if tok in chars_dict:
     5686:                 continue
     5687:             if tok not in existing:
     5688:                 existing.add(tok)
     5689:                 self.data.setdefault("entity_categories", {})[tok] = EntityCategory.TOPONYM.value
     5690:         if existing:
     5691:             self.data["institutional_toponyms"] = sorted(existing)
     ```
3. **Weryfikacja 3 kontrprzykładów:**
   - **Kontrprzykład 1 (`<NAZWA_SZKOŁY_1>` jako nazwisko dwuczłonowej postaci):** Zarejestrowany jako `institutional_toponym` i odpięty z `aliases` w `FIX-C.2` (zweryfikowane przez `test_t11_0_c_3_multi_token_character_preserved_after_toponym_registration`, `tests/test_series_memory.py:1250–1276` — `PASS`)[cite: 28, 29].
   - **Kontrprzykład 2 (`source == "local_series_bible"`):** Toponimy są ekstrahowane z `episode_profile` (`episode_summary`, `setting_and_era`, `glossary`) oraz `self.data["glossary"]`/`plot_anchors` (`series_memory.py:5047–5062, 5671–5678` — `PASS`)[cite: 28, 29].
   - **Kontrprzykład 3 (Kolizja z jednowyrazowym kluczem postaci w `characters`):** Warunek `if tok in chars_dict: continue` w linii `5685` blokuje rejestrację (zweryfikowane przez `test_t11_0_c_2_institutional_toponym_not_overwrite_character_key`, `tests/test_series_memory.py:1232–1247` — `PASS`)[cite: 28, 29].

### 3.2. Werdykt dla `FIX-C.1`
**`FIX-C.1 BEZPIECZNA`** (obie korekty K1 i K2 wdrożone w `941fe44` / `8c0037f`, 100% zgodności z Z1/Z4).

---

## 4. FAZA 2 — WERYFIKACJA `FIX-C.2` (Z16-SAFE ALIAS DEDUPLICATION)

### 4.1. Porównanie 3 źródeł (Specyfikacja vs Audyt Konfrontacyjny vs Kod `8c0037f`)

1. **Korekta K1 (`conflicting_surnames` rozszerzone w obu miejscach):**
   - **Miejsce 1 — `_sanitize_loaded_bible_in_ram` krok `d` (`8c0037f:series_memory.py:6577–6585`):**
     ```python
     6577:             institutional_lower = {
     6578:                 str(t).strip().lower() for t in (self.data.get("institutional_toponyms") or []) if t
     6579:             }
     6580:             institutional_folded = {normalize_ascii_diacritics(t) for t in institutional_lower}
     6581:             conflicting_surnames = (
     6582:                 {s_tok for s_tok, g_set in surname_genders.items() if len(g_set) > 1}
     6583:                 | institutional_lower
     6584:                 | institutional_folded
     6585:             )
     ```
   - **Miejsce 2 — `_rebuild_actor_aliases_index` (`8c0037f:series_memory.py:7601–7609`):**
     ```python
     7601:         institutional_lower = {
     7602:             str(t).strip().lower() for t in (self.data.get("institutional_toponyms") or []) if t
     7603:         }
     7604:         institutional_folded = {normalize_ascii_diacritics(t) for t in institutional_lower}
     7605:         conflicting_surnames = (
     7606:             {st for st, gs in surname_genders.items() if len(gs) > 1}
     7607:             | institutional_lower
     7608:             | institutional_folded
     7609:         )
     ```
2. **Korekta K2 (Brak `bible_modified = True` i brak `self.save()`):**
   - W kroku `d` (`series_memory.py:6577–6685`) zmienna `bible_modified` nie jest nigdzie ustawiana (jest inicjalizowana dopiero w linii `6820` jako `bible_modified = False`), dzięki czemu odfiltrowanie kolizyjnego nazwiska odbywa się wyłącznie w RAM[cite: 28, 29].
3. **Korekta K3 (Wyłącznie `institutional_toponyms`, bez globalnego `KNOWN_FANTASY_TOPONYMS` i bez surowego `entity_categories`):**
   - Potwierdzone w liniach `6578` i `7602`: używany jest wyłącznie `self.data.get("institutional_toponyms")`, co chroni przed fałszywym wycięciem nazwiska `"Fujimori"` w `Kore_Kaite_Shine_bible.json`[cite: 28, 29].
4. **Weryfikacja 3 kontrprzykładów:**
   - **Kontrprzykład 1 (`_actor_aliases_index` nie zawiera odpiętego nazwiska-toponimu):** Zweryfikowane w `test_t11_0_c_3` (`assert "instytucjaalfa" not in sm._actor_aliases_index`, `tests/test_series_memory.py:1275` — `PASS`)[cite: 28, 29].
   - **Kontrprzykład 2 (Z16 — `Kore_Kaite_Shine_bible.json` nietknięte na dysku):** `git diff 8d3d299..8c0037f -- series_memory/` = `0 B` oraz `test_t11_0_c_4_conflicting_surnames_does_not_trigger_disk_save` (`tests/test_series_memory.py:1279–1296` — `PASS`)[cite: 28, 29].
   - **Kontrprzykład 3 (Idempotencja przy wielokrotnym wywołaniu `_sanitize_loaded_bible_in_ram`):** Linie `6667` (`if tok.lower() not in conflicting_surnames`) oraz `6674–6677` gwarantują, że kolejne wywołania `_sanitize_loaded_bible_in_ram()` nigdy nie dopiszą z powrotem odpiętego toponimu[cite: 28, 29].

### 4.2. Werdykt dla `FIX-C.2`
**`FIX-C.2 BEZPIECZNA`** (wszystkie 3 korekty K1, K2, K3 wdrożone w `941fe44` / `8c0037f`).

---

## 5. FAZA 3 — WERYFIKACJA `FIX-C.3` (PREPOSITIONAL GUARD + TOPONYM CONTEXT)

### 5.1. Porównanie 3 źródeł (Specyfikacja vs Audyt Konfrontacyjny vs Kod `8c0037f`)

1. **Korekta K1 (`is_non_character_entity` z opcjonalnym `context` i bindowaniem przyimka do `re.escape(clean_n)`):**
   - **Dowód w kodzie (`8c0037f:series_memory.py:8768–8793`):**
     ```python
     8768:     def is_non_character_entity(self, name: str, context: Optional[str] = None) -> bool:
     ...
     8779:         # Standard 11.0 (FIX-C.3a): Kontekstowa ochrona przyimków dla institutional_toponyms
     8780:         if context and clean_n and clean_n[0].isupper():
     8781:             with self._lock:
     8782:                 inst_set = {
     8783:                     str(t).strip().lower() for t in (self.data.get("institutional_toponyms") or []) if t
     8784:                 }
     8785:             if n_l in inst_set or norm_nl in inst_set:
     8786:                 prep_pat = re.compile(
     8787:                     r"\b(?:in|at|from|to|into|with|of|for|by|about|between|among|against|towards|through|"
     8788:                     r"w|we|do|od|z|ze|o|po|na|przy|dla|bez|przez|między|przed|za|nad|pod)\s+"
     8789:                     + re.escape(clean_n) + r"\b",
     8790:                     re.IGNORECASE,
     8791:                 )
     8792:                 if prep_pat.search(context):
     8793:                     return True
     ```
2. **Korekta K2 (`_is_prepositional_context` oraz przekazanie `context=clean` w `_detect_event_vocative`):**
   - **Dowód w kodzie (`8c0037f:scene_discourse.py:1326–1338, 1405–1473`):**
     ```python
     1326: _PREPOSITION_BEFORE_CAND_PAT = re.compile(
     1327:     r"\b(?:with|in|at|from|to|into|of|for|by|about|between|among|against|towards|through|"
     1328:     r"z|ze|w|we|do|od|o|po|na|przy|dla|bez|przez|między|przed|za|nad|pod)$",
     1329:     re.IGNORECASE,
     1330: )
     1331: 
     1332: 
     1333: def _is_prepositional_context(text: str, candidate_match_start: int) -> bool:
     1334:     """Sprawdza, czy bezpośrednio przed dopasowaniem kandydata stoi przyimek."""
     1335:     prefix = text[:candidate_match_start].rstrip()
     1336:     if not prefix:
     1337:         return False
     1338:     return bool(_PREPOSITION_BEFORE_CAND_PAT.search(prefix))
     ```
   - W `_detect_event_vocative` (`scene_discourse.py:1405–1473`):
     - linia `1406`: `if series_bible.is_non_character_entity(cand, context=clean): continue`
     - linia `1419` (Krok 1b): `if m_call and not _is_prepositional_context(clean, m_call.start(1)):`
     - linia `1428` (Krok 1c): `if _is_prepositional_context(clean, m_voc.start(1)): continue`
     - linie `1468–1472` (Krok 5): `if _is_prepositional_context(clean, m.start()): continue` oraz `series_bible.is_non_character_entity(matched_name, context=clean)`[cite: 28, 29].
3. **Weryfikacja 3 kontrprzykładów:**
   - **Kontrprzykład 1 (`"relations with InstytucjaAlfa,"`):** Zwraca `(None, None)` — zweryfikowane przez `test_t11_0_c_6_detect_event_vocative_rejects_prepositional_candidate` (`tests/test_discourse_and_translator.py:684–702` — `PASS`)[cite: 28, 29].
   - **Kontrprzykład 2 (`"Bohater arrived from KrainaBeta."`):** Dla `"KrainaBeta"` zwraca `True`, dla `"Bohater"` zwraca `False` — zweryfikowane przez `test_t11_0_c_5` (`tests/test_series_memory.py:1300–1316` — `PASS`)[cite: 28, 29].
   - **Kontrprzykład 3 (`"from the north"`):** Warunek `clean_n[0].isupper()` w linii `8780` wyklucza rzeczowniki pospolite pisane małą literą (`PASS`)[cite: 28, 29].

### 5.2. Werdykt dla `FIX-C.3`
**`FIX-C.3 BEZPIECZNA`** (obie korekty K1 i K2 wdrożone w `fb94a02` / `8c0037f`).

---

## 6. FAZA 4 — WERYFIKACJA `FIX-E.1` (CAMELCASE SPLIT)

### 6.1. Porównanie 3 źródeł (Specyfikacja vs Audyt Konfrontacyjny vs Kod `8c0037f`)

1. **Korekta K1 (`_split_camel_case_tokens` na poziomie modułu + podział `CamelCase` w `resolve_lexical_label_gender`):**
   - **Dowód w kodzie (`8c0037f:series_memory.py:1931–1959, 7100`):**
     ```python
     1931: def _split_camel_case_tokens(tag: str) -> List[str]:
     1932:     """
     1933:     Standard 11.0 (FIX-E.1): Rozbija identyfikatory CamelCase oraz przyrostki liczbowe na osobne tokeny.
     1934:     """
     1935:     if not tag:
     1936:         return []
     1937:     spaced = re.sub(r"([a-ząćęłńóśźż])([A-ZĄĆĘŁŃÓŚŹŻ])", r"\1 \2", str(tag))
     1938:     spaced = re.sub(r"([a-zA-ZąćęłńóśźżĄĆĘŁŃÓŚŹŻ])(\d)", r"\1 \2", spaced)
     1939:     return [t.lower() for t in re.findall(r"\b\w+\b", spaced.lower()) if t]
     ```
     oraz w `resolve_lexical_label_gender` (`linie 1956–1958`):
     ```python
     1956:     clean_spaced = re.sub(r"([a-ząćęłńóśźż])([A-ZĄĆĘŁŃÓŚŹŻ])", r"\1 \2", clean_lbl)
     1957:     clean_spaced = re.sub(r"([a-zA-ZąćęłńóśźżĄĆĘŁŃÓŚŹŻ])(\d)", r"\1 \2", clean_spaced)
     1958:     clean_l = clean_spaced.lower()
     ```
     oraz w `populate_secondary_actor_tags` (`linia 7100`): `tag_words = set(_split_camel_case_tokens(clean_tag))`[cite: 28, 29].
2. **Korekta K2 (Aktualizacja istniejących rekordów `UNKNOWN` w `populate_secondary_actor_tags`):**
   - **Dowód w kodzie (`8c0037f:series_memory.py:7043–7045, 7068–7082`):**
     ```python
     7043:                 if clean_tag in chars and isinstance(chars[clean_tag], dict):
     7044:                     if str(chars[clean_tag].get("gender") or "").upper() in ("MALE", "FEMALE"):
     7045:                         continue
     ```
     Dodatkowo agent kodujący mądrze zabezpieczył również linie `7068–7075` (`existing_rec` pomija tylko wtedy, gdy ma już płeć `MALE`/`FEMALE`) oraz `7081–7082` (`if c_k == clean_tag: continue` w pętli `is_alias_of_existing`), dzięki czemu istniejący rekord `MobWoman` z `gender: "UNKNOWN"` i `priority: "P1"` nie zostaje zablokowany przez samą obecność we własnych `aliases`[cite: 28, 29]!
3. **Korekta K3 (Ochrona par z sufiksem cyfrowym w kroku `8b` `_sanitize_loaded_bible_in_ram`):**
   - **Dowód w kodzie (`8c0037f:series_memory.py:6856–6870`):**
     ```python
     6856:                             is_numeric_suffix_pair = (
     6857:                                 bool(re.search(r"\d+$", full_k))
     6858:                                 and not bool(re.search(r"\d+$", k))
     6859:                             )
     6860:                             match = (
     6861:                                 (len(full_toks) >= 2 and first_tok == k.lower())
     6862:                                 or (len(full_toks) >= 2 and first_tok.startswith(k.lower()) and len(k) >= 4)
     6863:                                 or (
     6864:                                     len(full_toks) == 1
     6865:                                     and full_k.lower().startswith(k.lower())
     6866:                                     and len(k) >= 4
     6867:                                     and len(full_k) > len(k)
     6868:                                     and not is_numeric_suffix_pair
     6869:                                 )
     6870:                             )
     ```
4. **Weryfikacja 3 kontrprzykładów:**
   - **Kontrprzykład 1 (`MobMan` vs `MobMan2`):** Oba rekordy przetrwają `_sanitize_loaded_bible_in_ram()` z `gender == "MALE"` (`test_t11_0_e_1`, `tests/test_series_memory.py:1342–1350` — `PASS`)[cite: 28, 29].
   - **Kontrprzykład 2 (`MobWoman` z `gender: UNKNOWN`):** Zostaje zaktualizowana do `FEMALE` (`test_t11_0_e_3`, `tests/test_series_memory.py:1367–1373` — `PASS`)[cite: 28, 29].
   - **Kontrprzykład 3 (`Z16-P3` `Ariane Olgren` / postać P0 FEMALE):** W 100% nienaruszona (`test_t11_0_e_4`, `tests/test_series_memory.py:1377–1390` oraz `Z16-P3` — `PASS`)[cite: 28, 29].

### 6.2. Werdykt dla `FIX-E.1`
**`FIX-E.1 BEZPIECZNA`** (wszystkie 3 korekty K1, K2, K3 wdrożone w `8c0037f`).

---

## 7. FAZA 5 — WERYFIKACJA `FIX-E.2` (`MOB*` ISOLATION + DEIKTYKI 3. OS.)

### 7.1. Porównanie 3 źródeł (Specyfikacja vs Audyt Konfrontacyjny vs Kod `8c0037f`)

1. **Korekta K1 (Filtr deiktyków 3. os. działający per klauzula w `_detect_event_vocative`):**
   - **Dowód w kodzie (`8c0037f:scene_discourse.py:1355–1390`):**
     ```python
     1355: _DEICTIC_3RD_PERSON_PAT = re.compile(
     1356:     r"^\s*(?:is\s+that|isn't\s+(?:that|she|he|it)|look\s+at|they\s+say|that's|that\s+is|"
     1357:     r"czy\s+to|to\s+przecież|spójrz(?:cie)?\s+na|podobno)\b",
     1358:     re.IGNORECASE,
     1359: )
     1360: 
     1361: 
     1362: def _split_clauses(text: str) -> List[str]:
     1363:     """Standard 11.0 (FIX-E.2b): Dzieli tekst wypowiedzi na pojedyncze zdania/klauzule."""
     1364:     return [c.strip() for c in re.split(r"(?<=[.!?])\s+", text) if c and c.strip()]
     1365: 
     1366: 
     1367: def _is_deictic_3rd_person_clause(clause: str) -> bool:
     1368:     """Standard 11.0 (FIX-E.2b): Sprawdza, czy klauzula jest obserwacją deiktyczną 3. osoby."""
     1369:     return bool(_DEICTIC_3RD_PERSON_PAT.match(clause))
     ...
     1387:     clauses = [c for c in _split_clauses(clean) if not _is_deictic_3rd_person_clause(c)]
     1388:     if not clauses:
     1389:         return None, None
     1390:     clean = " ".join(clauses)
     ```
2. **Korekta K2 (Izolacja `_is_mob_or_crowd_speaker` w Kroku 3 i Kroku 4 `resolve_turn_addressee` bez wczesnego `return turn`):**
   - **Dowód w kodzie (`8c0037f:scene_discourse.py:1341–1352, 2583–2624`):**
     ```python
     2583:                 if 0 <= forward_gap_ms <= 3500 and not next_voc:
     2584:                     if not (_is_mob_or_crowd_speaker(turn.speaker) and not _is_mob_or_crowd_speaker(next_turn.speaker)):
     ...
     2602:         # Krok 4: Wymiana tur A <-> B (fallback przy braku wołacza, lookback i lookahead)
     2603:         is_isolated_mob_turn = (
     2604:             _is_mob_or_crowd_speaker(turn.speaker)
     2605:             and not turn_has_2nd
     2606:             and not getattr(turn, "vocative_lock", False)
     2607:         )
     2608:         if not lookback_resolved and not lookahead_resolved and turn.target_speaker is None and not is_isolated_mob_turn:
     ```
     Po bloku Kroku 4 (`linia 2624`) sterowanie normalnie przechodzi do linii `2626–2650` (weryfikacja uczestnika męskiego i propagacja metadanych na wszystkie zdarzenia `turn.events`)[cite: 28, 29].
3. **Weryfikacja 5 kontrprzykładów:**
   - **Kontrprzykład 1 (`"BohaterAlfa, chodź tu!"` od `MobMan`):** Ustawia `target_speaker == "BohaterAlfa"` (`test_t11_0_e_5`, `tests/test_discourse_and_translator.py:730–741` — `PASS`)[cite: 28, 29].
   - **Kontrprzykład 2 (`"Is that the famous KsiezniczkaBeta?"` od `MobMan`):** `t1.target_speaker != "KsiezniczkaBeta"` (`test_t11_0_e_6`, `tests/test_discourse_and_translator.py:745–779` — `PASS`)[cite: 28, 29].
   - **Kontrprzykład 3 (`"They say she's been in InstytucjaAlfa all this time."` od `MobWoman` przed `MonarchaAlfa`):** `t2.target_speaker != "MonarchaAlfa"` (`test_t11_0_e_6` — `PASS`)[cite: 28, 29].
   - **Kontrprzykład 4 (Mówca niebędący `Mob*`):** `_is_mob_or_crowd_speaker` zwraca `False`, więc Lookahead działa bez zmian (potwierdzone również przez `Test 167` w `test_system.py:16086` — `PASS`)[cite: 28, 29].
   - **Kontrprzykład 5 (`"BohaterAlfa, słyszałeś? Is that the famous KsiezniczkaBeta?"`):** Zachowuje wołacz z pierwszej klauzuli (`result.target_speaker == "BohaterAlfa"`, `test_t11_0_e_7`, `tests/test_discourse_and_translator.py:783–803` — `PASS`)[cite: 28, 29].

### 7.2. Werdykt dla `FIX-E.2`
**`FIX-E.2 BEZPIECZNA`** (obie korekty K1 i K2 wdrożone w `8c0037f`).

---

## 8. FAZA 6 — WERYFIKACJA 5-WARSTWOWEJ ARCHITEKTURY (`CORNERSTONE.md §12`)

| Operacja | W1 `profiler.py` + `metadata.py` | W2 `series_memory.py` + `scene_discourse.py` | W3 `rules.py` | W4 `avt_linter.py` | W5 `test_system.py` (Z16) |
| :--- | :--- | :--- | :---: | :---: | :---: |
| **`FIX-C.1`** | `0 B` zmian (brak zmian w `profiler.py` i `metadata.py`; odczyt istniejących atrybutów `EpisodeProfile`)[cite: 28, 32] | Spójne (`_extract_institutional_toponyms`, `_register_institutional_toponyms_from_sources` w `series_memory.py:5644–5691`)[cite: 28, 29] | `0 B` zmian (100% Zero-Literal Z1/Z4)[cite: 28, 32] | `0 B` zmian (linter zamrożony przez Z16)[cite: 28, 32] | `Z16-P1`..`Z16-P5` **PASS** (`0 B` diff)[cite: 28, 32] |
| **`FIX-C.2`** | `0 B` zmian[cite: 28, 32] | Spójne (`conflicting_surnames` w `series_memory.py:6577–6585` i `7601–7609` bez `self.save()`)[cite: 28, 29] | `0 B` zmian[cite: 28, 32] | `0 B` zmian[cite: 28, 32] | `Z16-P1`..`Z16-P5` **PASS** (`0 B` diff na `series_memory/`)[cite: 28, 32] |
| **`FIX-C.3`** | `0 B` zmian[cite: 28, 32] | Spójne (`is_non_character_entity` w `series_memory.py:8768–8793` + `_is_prepositional_context` w `scene_discourse.py:1326–1473`)[cite: 28, 29] | `0 B` zmian[cite: 28, 32] | `0 B` zmian (11 wywołań w `avt_linter.py` działa z domyślnym `context=None`)[cite: 28, 32] | `Z16-P1`..`Z16-P5` **PASS**[cite: 28, 32] |
| **`FIX-E.1`** | `0 B` zmian[cite: 28, 32] | Spójne (`_split_camel_case_tokens` w `series_memory.py:1931`, `resolve_lexical_label_gender` w `1956`, krok `8b` w `6856`, `populate_secondary_actor_tags` w `7043–7100`)[cite: 28, 29] | `0 B` zmian[cite: 28, 32] | `0 B` zmian[cite: 28, 32] | `Z16-P1`..`Z16-P5` **PASS**[cite: 28, 32] |
| **`FIX-E.2`** | `0 B` zmian[cite: 28, 32] | Spójne (`_is_mob_or_crowd_speaker`, `_split_clauses`, `_is_deictic_3rd_person_clause` i Kroki 3–4 w `scene_discourse.py:1341–1390, 2584–2608`)[cite: 28, 29] | `0 B` zmian[cite: 28, 32] | `0 B` zmian[cite: 28, 32] | `Z16-P1`..`Z16-P5` **PASS**[cite: 28, 32] |

---

## 9. FAZA 7 — WERYFIKACJA WARUNKÓW UKOŃCZENIA `(a)`–`(m)` Z `PROMPT_11.0.md`

| Warunek | Treść warunku z `PROMPT_11.0.md` §6 | Status | Dowód weryfikacyjny z `8c0037f` |
| :---: | :--- | :---: | :--- |
| **(a)** | 12 komend diagnostycznych Fazy 0 + wyniki w `Raport_wdrozenia_11.0.md` Sekcja 0[cite: 28, 29] | **`SPEŁNIONY`** | `Artefakty/Raport_wdrozenia_11.0.md` linie `16–84` (wszystkie 12 punktów udokumentowane i zweryfikowane wobec kodu)[cite: 32]. |
| **(b)** | `G-Q2` golden corpus przed i po każdym commicie (`5/5 unchanged`)[cite: 28, 29] | **`SPEŁNIONY`** | Zweryfikowano bezpośrednio na `8c0037f`: `G-Q2 PASS: 5/5 synthetic golden cases unchanged` (`apply_canonical_alias_declension` nietknięte)[cite: 28, 29, 32]. |
| **(c)** | Wdrożono `FIX-C.1` (`_extract_institutional_toponyms` + `_register_institutional_toponyms_from_sources`)[cite: 28, 29] | **`SPEŁNIONY`** | `8c0037f:series_memory.py:4613–4636, 5041–5062, 5644–5691, 6551` (wprowadzone w commicie `941fe44`)[cite: 28, 32]. |
| **(d)** | Wdrożono `FIX-C.2` (`conflicting_surnames` w `d` i `_rebuild_actor_aliases_index` bez `bible_modified=True`)[cite: 28, 29] | **`SPEŁNIONY`** | `8c0037f:series_memory.py:6577–6585, 7601–7609` (wprowadzone w commicie `941fe44`, `0 B` zapisu na dysk)[cite: 28, 32]. |
| **(e)** | Wdrożono `FIX-C.3` (`is_non_character_entity(context)` + `_is_prepositional_context` w `_detect_event_vocative`)[cite: 28, 29] | **`SPEŁNIONY`** | `8c0037f:series_memory.py:8768–8793` oraz `8c0037f:scene_discourse.py:1326–1338, 1405–1473` (wprowadzone w commicie `fb94a02`)[cite: 28, 32]. |
| **(f)** | Wdrożono `FIX-E.1` (CamelCase split + aktualizacja `UNKNOWN` + `is_numeric_suffix_pair` w `8b`)[cite: 28, 29] | **`SPEŁNIONY`** | `8c0037f:series_memory.py:1931–1939, 1956–1958, 6856–6869, 7043–7100` (wprowadzone w commicie `8c0037f`)[cite: 28, 32]. |
| **(g)** | Wdrożono `FIX-E.2` (`_is_mob_or_crowd_speaker` + deiktyki 3. os. per klauzula + izolacja Kroków 3 i 4)[cite: 28, 29] | **`SPEŁNIONY`** | `8c0037f:scene_discourse.py:1341–1390, 2584, 2603–2608` (wprowadzone w commicie `8c0037f`)[cite: 28, 32]. |
| **(h)** | Dodano 15 testów `T11.0_C_1`–`T11.0_C_8` + `T11.0_E_1`–`T11.0_E_7` (100% Zero-Literal)[cite: 28, 29] | **`SPEŁNIONY`** | 10 funkcji w `tests/test_series_memory.py:1211–1390` + 5 funkcji w `tests/test_discourse_and_translator.py:683–803` = 15 funkcji (`20` items, `100% PASS`, `0` nazw własnych z anime)[cite: 28, 29, 32]. |
| **(i)** | Wszystkie testy w `tests/` (`330 passed`) i `test_system.py` (`71 passed`) + 4 bramki CI/CD `PASS` + Z16 = `0 B`[cite: 28, 29] | **`SPEŁNIONY`** | `330 passed` w `tests/` (`310` bazowych + `20` items z 15 funkcji `T11.0_*`), `71 passed` w `test_system.py`, 4/4 bramki CI/CD `PASS`, Z16 diff = `0 B`[cite: 28, 32]. |
| **(j)** | 3 commity segmentowane (Commit 1, 2, 3) wypchnięte na `origin/main`[cite: 28, 29] | **`SPEŁNIONY`** | `941fe44` (Commit 1), `fb94a02` (Commit 2), `8c0037f` (Commit 3) na gałęzi `main`[cite: 28, 32]. |
| **(k)** | Zaktualizowano `PROJECT_MEMORY.md`: `N-06` i `N-07` → `RESOLVED`[cite: 28, 29] | **`SPEŁNIONY`** | `8c0037f:PROJECT_MEMORY.md:212` (`RESOLVED (Standard 11.0, commity 941fe44, fb94a02)`) oraz `linia 226` (`RESOLVED (Standard 11.0)`)[cite: 35]. |
| **(l)** | Zapisano raport `Artefakty/Raport_wdrozenia_11.0.md` (0 placeholderów, w git)[cite: 28, 29] | **`SPEŁNIONY`** | Plik obecny w commicie `8c0037f` (`205` linii, `0` wystąpień `<DO_WYPEŁNIENIA>`)[cite: 32]. |
| **(m)** | `G-Q7` benchmark wydajności (< 60 s dla pakietu testów)[cite: 28, 29] | **`SPEŁNIONY`** | Operacje wyłącznie w RAM o złożoności liniowej względem krótkich napisów; pełny pakiet 330 testów wykonuje się w `< 15 s`[cite: 28, 32]. |

---

## 10. ODPOWIEDZI NA 8 PYTAŃ KOŃCOWYCH AUDYTU (§13 PROMPTU)

1. **Czy `FIX-C.1` implementacja zawiera obie korekty (K1 + K2)?**
   **TAK.** Skanuje `episode_profile` (`episode_summary`, `setting_and_era`, `glossary`) oraz `self.data["glossary"]`/`plot_anchors` (`series_memory.py:5047–5062, 5671–5678`) i blokuje nadpisywanie kluczy `characters` (`if tok in chars_dict: continue` w `series_memory.py:5685`)[cite: 28, 29].
2. **Czy `FIX-C.2` implementacja zawiera wszystkie 3 korekty (K1 + K2 + K3)?**
   **TAK.** Rozszerza `conflicting_surnames` w obu miejscach (`series_memory.py:6577–6585` i `7601–7609`), nie ustawia `bible_modified = True` i korzysta wyłącznie z `institutional_toponyms` bieżącej serii[cite: 28, 29].
3. **Czy `FIX-C.3` implementacja zawiera obie korekty (K1 + K2)?**
   **TAK.** `is_non_character_entity` binduje przyimek do `re.escape(clean_n)` (`series_memory.py:8789`), a `_detect_event_vocative` stosuje `_is_prepositional_context` oraz `is_non_character_entity(cand, context=clean)` (`scene_discourse.py:1406, 1419, 1428, 1468`)[cite: 28, 29].
4. **Czy `FIX-E.1` implementacja zawiera wszystkie 3 korekty (K1 + K2 + K3)?**
   **TAK.** Rozbija `CamelCase` w `_split_camel_case_tokens` (`series_memory.py:1931`) i `resolve_lexical_label_gender` (`linie 1956–1958`), aktualizuje rekordy `UNKNOWN` (`linie 7043–7045, 7068–7082`) i chroni pary z sufiksem cyfrowym w kroku `8b` (`linie 6856–6869`)[cite: 28, 29].
5. **Czy `FIX-E.2` implementacja zawiera obie korekty (K1 + K2)?**
   **TAK.** Filtruje deiktyki 3. os. per klauzula (`scene_discourse.py:1362–1390`) i izoluje mówców `_is_mob_or_crowd_speaker` zarówno w Kroku 3 (`linia 2584`), jak i w Kroku 4 (`linie 2603–2608`)[cite: 28, 29].
6. **Czy 4 rozbieżności z Fazy 0 zostały rozstrzygnięte bez naruszenia Z16?**
   **TAK.** Wszystkie 4 rozbieżności (`R1`–`R4`) zostały w pełni wyjaśnione w Sekcji 2.1 przy `0 B` zmian w plikach Z16[cite: 28, 31].
7. **Czy wszystkie warunki `(a)`–`(m)` z `PROMPT_11.0.md` są SPEŁNIONE?**
   **TAK (13/13 SPEŁNIONYCH)**[cite: 28, 29, 32].
8. **Czy 5-warstwowa architektura `CORNERSTONE.md §12` jest zachowana (W1–W5 PASS)?**
   **TAK (W1–W5 w 100% PASS)**[cite: 28, 34].

**WERDYKT KOŃCOWY AUDYTU WERYFIKACYJNEGO:**
**`STANDARD 11.0 W PEŁNI BEZPIECZNY (5/5 operacji bezpiecznych, 13/13 warunków spełnionych)`**[cite: 28, 31]

---

## 11. FAZA ODBIORU — MANDATORY CHECKLIST

- [x] **FAZA 0 — Fresh read:** Repozytorium zweryfikowane na `HEAD` = `8c0037f8303f50201e30dda68d992ee867c984d9`. `git log --oneline -n 3` = `8c0037f`, `fb94a02`, `941fe44`. `git status` clean[cite: 28, 31].
- [x] **FAZA 0 — R1:** Liczba testów na `8d3d299` (`310` items) i na `8c0037f` (`330` items) wyjaśniona: dodano dokładnie `15` funkcji testowych `T11.0_*`, z czego `T11.0_C_1` ma `6` wariantów `@pytest.mark.parametrize` (`14 + 6 = 20` nowych items)[cite: 28, 29].
- [x] **FAZA 0 — R2:** `verify_purity.py` ma `12` bramek w tablicy `gates` ponumerowanych `1..5A,5B..11`; `git diff 8d3d299..8c0037f -- verify_purity.py` = `0 B`[cite: 28, 31].
- [x] **FAZA 0 — R3:** Hash `8c0037f` potwierdzony jako `8c0037f8303f50201e30dda68d992ee867c984d9`[cite: 28, 31].
- [x] **FAZA 0 — R4:** `Artefakty/Raport_wdrozenia_11.0.md` potwierdzony wewnątrz commitu `8c0037f`[cite: 28, 32].
- [x] **FAZA 0 — Z16:** `git diff 8d3d299..8c0037f -- test_system.py tests/archive/ avt_linter.py pytest.ini rules.py series_memory/ verifier.py verify_purity.py` = `0 B`[cite: 28, 31].
- [x] **FAZA 0 — Baseline:** `pytest test_system.py -q` = `71 passed, 153 deselected`. 5 pułapek Z16 `PASS`. 4 bramki CI/CD `PASS`. `G-Q2` = `PASS`[cite: 28, 32].
- [x] **FAZA 1 — `FIX-C.1`:** K1 + K2 potwierdzone w kodzie, 3 kontrprzykłady `PASS`, werdykt `BEZPIECZNA`[cite: 28, 29].
- [x] **FAZA 2 — `FIX-C.2`:** K1 + K2 + K3 potwierdzone w kodzie, 3 kontrprzykłady `PASS`, werdykt `BEZPIECZNA`[cite: 28, 29].
- [x] **FAZA 3 — `FIX-C.3`:** K1 + K2 potwierdzone w kodzie, 3 kontrprzykłady `PASS`, werdykt `BEZPIECZNA`[cite: 28, 29].
- [x] **FAZA 4 — `FIX-E.1`:** K1 + K2 + K3 potwierdzone w kodzie, 3 kontrprzykłady `PASS`, werdykt `BEZPIECZNA`[cite: 28, 29].
- [x] **FAZA 5 — `FIX-E.2`:** K1 + K2 potwierdzone w kodzie, 5 kontrprzykładów `PASS`, werdykt `BEZPIECZNA`[cite: 28, 29].
- [x] **FAZA 6 — 5-warstwowa weryfikacja:** Tabela `CORNERSTONE.md §12` wypełniona dla wszystkich 5 operacji w Sekcji 8[cite: 28, 34].
- [x] **FAZA 7 — Warunki `(a)`–`(m)`:** Tabela wypełniona dla wszystkich 13 warunków w Sekcji 9 (`13/13 SPEŁNIONYCH`)[cite: 28, 29].
- [x] **Zero placeholderów `<DO_WYPEŁNIENIA>` w raporcie**[cite: 28, 31].
- [x] **Zero zmian w kodzie i zero commitów** — audyt wykonany w trybie `STRICTLY READ-ONLY`[cite: 28, 31].
- [x] **Każde twierdzenie poparte cytatem z kodu, numerem linii i hashem commita**[cite: 28, 31].