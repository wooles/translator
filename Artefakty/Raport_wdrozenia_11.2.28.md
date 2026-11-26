# 🏛️ RAPORT WDROŻENIOWY — STANDARD 11.2.28 & MIKRO-HOTFIX 11.2.28a
## Certyfikacja Standardu 11.2.28 + Hotfixu 11.2.28a (`BUG #1`, `BUG #2`, `ev.name`, `OBS-09` negatyw oraz Rejestr `OBS-03 → OBS-15` & `KNOWN GAP`)

- **Repozytorium:** `https://github.com/wooles/translator` (gałąź `main`)
- **Punkt wyjścia (HEAD baseline 11.2.27):** `6f1b310a83927aa1529835e9da20d02cb083f55b` (`6f1b310`)
- **Commity Standardu 11.2.28:**
  * **Commit 1:** `22cbbd1` (`fix(pipeline): Standard 11.2.28 — OBS-12, OBS-14, OBS-15a/b/c, OBS-09, OBS-11 (0 B diff Z16)`)
  * **Commit 2:** `0933e73` (`test(pipeline): Standard 11.2.28 — non-tautological regression tests (tests/test_standard_11_2_28.py)`)
  * **Commit 3:** `d853d79` (`docs(release): Standard 11.2.28 — PROJECT_MEMORY (ARB-080, OBS-07..OBS-15) & Raport_wdrozenia_11.2.28`)
- **Commity Mikro-Hotfixu 11.2.28a (bazującego na `d853d79`):**
  * **Commit 1:** `56cebbf` (`fix(pipeline): Hotfix 11.2.28a — BUG #1 (OBS-15c quotes), BUG #2 (OBS-15b rich desc), scene_snapper ev.name (0 B diff Z16)`)
  * **Commit 2:** `818f1ec` (`test(pipeline): Hotfix 11.2.28a — regression tests for BUG #1, BUG #2, OBS-09 negative (LUKA #4) & ev.name`)
  * **Commit 3:** `HEAD` (`docs(release): Hotfix 11.2.28a — sync OBS-03..OBS-15 & KNOWN GAP registry in PROJECT_MEMORY & Raport_wdrozenia_11.2.28`)
- **Baseline ochrony Z16 (`c197db7` + Z16-amendment #15 z `6852a5a` + wyłączenie `11.2.29`):** **bezwzględne 0 B diffu** na wszystkich 29 plikach chronionych Z16 (`avt_linter.py`, `verifier.py`, `client_factory.py`, `rules.py`, `test_system.py`, `verify_purity.py`, `pricing_guard.py`, `main.py`, `context_cache.py`, 20 baz `*_bible.json`, `series_memory/.onomastic_lexicon.json`, leksykony) oraz na odroczonym `scene_discourse.py` względem `6f1b310`.
- **Data certyfikacji:** 2026-11-25
- **Koszt wykonania:** 0.00 PLN (weryfikacja deterministyczna oraz bramki AST w 100% lokalnie)

---

## 1. ZAKRES ZMIAN TECHNICZNYCH (4 MODUŁY POZA Z16)

1. **`OBS-12` (`translator.py`):**
   - Dodano mapę `_CYRILLIC_TO_LATIN_HOMOGLYPHS` oraz funkcję `_normalize_cyrillic_homoglyphs_in_latin` wywoływaną w `sanitize_sub_text`.
   - Rozwiązuje zarówno tokeny mieszane (łacińsko-cyrylickie homogliffy wizualne), jak i samotne jednoliterowe homogliffy w kontekście łacińskim oraz po separatorze `\N`, zachowując w 100% nienaruszone prawdziwe cytaty cyrylickie oraz tekst JP/EN (z pełną idempotentnością).
2. **`OBS-14` (`scene_snapper.py`):**
   - W `SceneShotSnapper.snap_subtitles_to_cuts` dodano wykrywanie warstwy napisów/góry (`_is_top_or_sign_event`: style `Signs/Top/...`, tagi `\an[789]`, `\pos`, `\move`) oraz prekomputację `next_same_layer_start` dla kolejnych niepokrywających się kwestii tej samej warstwy (tolerancja `<= 20 ms`).
   - Wydłużenie krótkich replik do `min_duration_ms = 700` oraz dosunięcie `cut - 80` jest przycinane do `next_same_layer_start`, eliminując sztuczne nakładki między kwestiami dolnymi przy pełnej izolacji napisów ekranowych.
3. **`OBS-15a / 15b / 15c` (`series_memory.py` + `translator.py`):**
   - **`OBS-15a`:** Do `SeriesBible.update_from_episode_profile` dodano parametr `overwrite_existing_glossary: bool = True`. Wywołanie z Profilera Tier 3 przekazuje `False` (ochrona istniejącego Kanonu Mangi Tier 1 oraz ręcznych haseł serii bez blokowania nowych haseł), natomiast Kanon Mangi Tier 1 przekazuje `True`.
   - **`OBS-15b`:** W `translator.py:_prepare_batch_prompt` rozszerzono `_is_generic_character_desc` o generyczne opisy wyłącznie płci (`"mężczyzna (postać)"`, `"kobieta (postać)"`, itp.), usuwając puste duplikaty aliasowe przy zachowaniu ról opisowych.
   - **`OBS-15c`:** W `series_memory.py:_sanitize_character_entry` zmieniono placeholder `'Pan / Panie [Imię]'` na `'Pan / Panie <Imię>'`; dodano współdzielony pomocnik `_strip_hierarchical_relation_leaks` czyszczący w RAM zarówno pełne zagnieżdżone klauzule `[RELACJA HIERARCHICZNA ... [Imię] ... -sama]`, jak i osierocone ogony `', eliminacja hybryd ... -sama]` przy **0 B diffu na dysku** (`_sanitize_loaded_bible_in_ram` nie uruchamia `self.save()` dla higieny `# 8c`), oraz analogiczne czyszczenie `_strip_relation_meta_tags` w `translator.py:_prepare_batch_prompt`.
4. **`OBS-09` (`whisper_disambiguator.py`):**
   - W `WhisperDisambiguator.format_compact_ssot_tag` dodano jawne wskazówki dla ról `WUJ` (`"Relacja: Wuj/starszy mężczyzna (MĘŻCZYZNA)"`) oraz `CIOTKA` (`"Relacja: Ciotka/starsza kobieta (KOBIETA)"`), zachowywane nienaruszenie po filtrze `K1`/`K3` w `translator.py`.
5. **`OBS-11` (`translator.py`):**
   - W `sanitize_sub_text` dodano zwijanie pustych podwójnych/potrójnych łamań linii ASS (`\N\N`, `\N \N` -> `\N`).
   - Dodano modułowy pomocnik `_append_phase2_linebreak_hygiene_rule(focused_rules_str, batch_items)` wywoływany po `get_focused_rules_for_batch` w `_process_phase2_only`, wstrzykujący wytyczną łamania linii wyłącznie wtedy, gdy paczka Fazy 2 zawiera `\N`.

### Hotfix 11.2.28a (Domknięcie Audytu Konfrontacyjnego 11.2.28)
1. **`BUG #1` ([series_memory.py](../series_memory.py)):** W `_strip_hierarchical_relation_leaks` oraz w `_reconcile_registry_gender_in_memory` usunięto bezwarunkowe wycinanie `r"'\s*,"` -> `","`; sprzątanie artefaktów po wycieku uruchamia się wyłącznie przy wykryciu wycieku (`cleaned != text`) z pochłanianiem opcjonalnego prowadzącego `',`/`'` przez same reguły wycinające oraz ograniczeniem sprzątania do `r"\]\s*'(?!\s*\w)"` -> `"]"`, w pełni chroniąc poprawne cytaty i tytuły w apostrofach (`'Tytuł Dzieła',`).
2. **`BUG #2` ([translator.py](../translator.py)):** W `_is_generic_character_desc` usunięto `"mężczyzna (postać"` i `"kobieta (postać"` z `startswith(...)`, pozostawiając jedynie ścisłe warianty bez treści fabularnej w zbiorze dokładnym (`"mężczyzna (postać)"`, `"kobieta (postać)"`, `"mężczyzna (postać drugoplanowa)"`, `"kobieta (postać drugoplanowa)"`, `"mężczyzna (postać epizodyczna)"`, `"kobieta (postać epizodyczna)"`), dzięki czemu bogate opisy P0 zaczynające się od `"mężczyzna (postać), ..."` pozostają w prompcie.
3. **`ev.name` `SIGN`/`EPTITLE` ([scene_snapper.py](../scene_snapper.py)):** W `_is_top_or_sign_event` dodano sprawdzenie `name.startswith("sign") or name == "eptitle"` (`ev.name`/`ev.actor`), izolując napisy ze stylem `Default` od warstwy dolnego dialogu (`0 B` diffu w `avt_linter.py`).

---

## 2. REJESTR `OBS-03 → OBS-15` I STATUS `KNOWN GAP` (`11.2.28a`)

| ID | Priorytet | Dokładny status w `11.2.28a` | Uwaga / Opis |
| :--- | :--- | :--- | :--- |
| **OBS-03** | `NISKI` | `OPEN (non-blocking)` | `pricing_guard.py:379` — kosmetyka logu (Z16, poza zakresem). |
| **OBS-05** | `NISKI` | `CLOSED` | 4. czysty przebieg z rzędu (0/25 F2, skumulowanie 1/139 = 0.72% w 6 przebiegach). |
| **OBS-06** | `NISKI` | `OPEN (non-blocking)` | Współbieżność obserwatora F2 przy `max_workers_f2 >= 2`. |
| **OBS-07** | `NISKI` | `OPEN (non-blocking)` | Byty nieludzkie z `UNKNOWN` płcią + wysokie F0. |
| **OBS-08** | `NISKI` | `CLOSED (zastrzeżenie)` | `DEF-03` przepuszczony przez `batch_cap` — reopen przy `>= 3` wypchniętych liniach `is_spk_ch` w jednym przebiegu. |
| **OBS-10** | `NISKI` | `CLOSED` | Mutacje `AVTLinter` w `strict_positive_domain=True` — `0/412` w przebiegu kontrolnym, jednorazowy problem starej bazy. |
| **OBS-09** | `NISKI` | `OPEN (non-blocking)` | Mechanizm wdrożony w `11.2.28`, test negatywny dodany w `11.2.28a`; oczekuje na przebieg produkcyjny z `ojisan`/`obasan` (nie zamykać bez produkcji). |
| **OBS-11** | `NISKI` | `OPEN (non-blocking)` | Mechanizm wdrożony w `11.2.28`; oczekuje na przebieg produkcyjny z `\N\N` (nie zamykać bez produkcji). |
| **OBS-12** | `WYSOKI` | `OPEN (non-blocking)` | Homoglif cyrylicki U+043E w F2 — mechanizm wdrożony w `11.2.28`; oczekuje na przebieg produkcyjny z homoglifem (nie zamykać bez produkcji). |
| **OBS-13a/b/c** | `ŚREDNI` | `DEFERRED → 11.2.29` | Płeć/liczba adresata i chóru — celowe zamrożenie (`0 B` diffu w `scene_discourse.py` oraz `_resolve_line_addressee`). |
| **OBS-14** | `NISKI` | `OPEN (non-blocking)` | Nakładki po wydłużeniu krótkich replik do `700 ms` — mechanizm wdrożony w `11.2.28` + `ev.name` w `11.2.28a`; replay potwierdził `0 ms` nakładek, ale wymagany przebieg produkcyjny (nie zamykać bez produkcji). |
| **OBS-15a/b/c** | `NISKI` | `OPEN (non-blocking)` | Dryf terminologii, generyczne duplikaty płci i osierocony ogon `SeriesBible` — mechanizmy wdrożone w `11.2.28` + `BUG #1/#2` w `11.2.28a`; wymagany przebieg produkcyjny (nie zamykać bez produkcji). |
| **`KNOWN GAP`** | — | **`DEF-04`, `OBS-01`, `OBS-04`, `DEF-05`** | Pokryte jednostkowo, wymagają dedykowanych wyzwalaczy w przebiegu produkcyjnym. |

---

## 3. METRYKI CI/CD I IZOLACJA Z16 (`11.2.28a`)

- `tests/test_standard_11_2_28.py`: **20 / 20 PASSED**
- `tests/`: **472 / 472 PASSED** (`466 + 6`)
- `test_system.py`: **70 PASSED, 154 DESELECTED**
- Bramki kwalifikacyjne: `verify_purity.py` (**11/11 PASS**), `verify_8_fixes.py` (**8/8 PASS**), `verify_12_fixes.py` (**12/12 PASS**), `verify_ultimate_pipeline.py` (**15/15 PASS**)
- Audyt śledczy: `audit_diff.ps1 -BaseRef "6f1b310"` -> **VICTORY CONFIRMED**
- Izolacja Z16 i `scene_discourse.py` względem `6f1b310`: **0 B DIFF**
