# 🏛️ RAPORT WDROŻENIOWY — STANDARD 11.2.28
## Certyfikacja Standardu 11.2.28 (`OBS-12`, `OBS-14`, `OBS-15a/b/c`, `OBS-09`, `OBS-11` oraz Rejestr `OBS-07 → OBS-15`)

- **Repozytorium:** `https://github.com/wooles/translator` (gałąź `main`)
- **Punkt wyjścia (HEAD baseline 11.2.27):** `6f1b310a83927aa1529835e9da20d02cb083f55b` (`6f1b310`)
- **Commit 1 (Kod produkcyjny):** `22cbbd1` (`fix(pipeline): Standard 11.2.28 — OBS-12, OBS-14, OBS-15a/b/c, OBS-09, OBS-11 (0 B diff Z16)`)
- **Commit 2 (Testy regresyjne):** `0933e73` (`test(pipeline): Standard 11.2.28 — non-tautological regression tests (tests/test_standard_11_2_28.py)`)
- **Commit 3 (Dokumentacja i Zamknięcie Wydania):** `HEAD` (`docs(release): Standard 11.2.28 — PROJECT_MEMORY (ARB-080, OBS-07..OBS-15) & Raport_wdrozenia_11.2.28`)
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

---

## 2. REJESTR `OBS-07 → OBS-15` I STATUS `KNOWN GAP`

| ID | Status w `11.2.28` | Decyzja / Lokalizacja |
| :--- | :--- | :--- |
| `OBS-07` | `CLOSED / WONTFIX` | Jednostkowa wariacja stylistyczna LLM poza zakresem deterministycznych reguł. |
| `OBS-08` | `OPEN (DEFERRED)` | Niuanse rejestru/idiomów odroczone poza `11.2.28` (brak zmian Z16). |
| `OBS-09` | `RESOLVED` | `whisper_disambiguator.py:format_compact_ssot_tag` (`WUJ` / `CIOTKA`). |
| `OBS-10` | `OPEN (DEFERRED)` | Obserwacja odroczona poza `11.2.28` (brak zmian Z16). |
| `OBS-11` | `RESOLVED` | `translator.py:sanitize_sub_text` + `_append_phase2_linebreak_hygiene_rule`. |
| `OBS-12` | `RESOLVED` | `translator.py:_normalize_cyrillic_homoglyphs_in_latin` w `sanitize_sub_text`. |
| `OBS-13a/b/c` | `DEFERRED → 11.2.29` | Celowe zamrożenie (`0 B` diffu w `scene_discourse.py` oraz `_resolve_line_addressee`). |
| `OBS-14` | `RESOLVED` | `scene_snapper.py:SceneShotSnapper.snap_subtitles_to_cuts` (`next_same_layer_start`). |
| `OBS-15a` | `RESOLVED` | `series_memory.py:update_from_episode_profile` (`overwrite_existing_glossary`) + `translator.py`. |
| `OBS-15b` | `RESOLVED` | `translator.py:_prepare_batch_prompt` (`_is_generic_character_desc`). |
| `OBS-15c` | `RESOLVED` | `series_memory.py` (`<Imię>`, RAM-only 0 B disk diff) + `translator.py`. |

- **Status `KNOWN GAP` do `11.2.29`:** `OBS-13a/b/c`, `DEF-04`, `OBS-01`, `OBS-03`, `OBS-06`, `OBS-08`, `OBS-10`.

---

## 3. METRYKI CI/CD I IZOLACJA Z16

- `tests/test_standard_11_2_28.py`: **14 / 14 PASSED**
- `tests/`: **466 / 466 PASSED** (`452 + 14`)
- `test_system.py`: **70 PASSED, 154 DESELECTED**
- Bramki kwalifikacyjne: `verify_purity.py` (**11/11 PASS**), `verify_8_fixes.py` (**8/8 PASS**), `verify_12_fixes.py` (**12/12 PASS**), `verify_ultimate_pipeline.py` (**15/15 PASS**)
- Audyt śledczy: `audit_diff.ps1 -BaseRef "6f1b310"` -> **VICTORY CONFIRMED**
- Izolacja Z16 i `scene_discourse.py` względem `6f1b310`: **0 B DIFF**
