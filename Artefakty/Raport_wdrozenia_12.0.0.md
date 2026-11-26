# Raport Wdrożenia: Standard `12.0.0` (Etap 1 — Architektura Jakości Stylistycznej, Zero-Cache SSOT, Konsolidacja F2 i Pętla Uczenia)

- **Data wydania:** `2026-11-26`
- **Gałąź / Zakres commitów:** `main` (`365e260..HEAD`, `6` atomowych commitów)
- **Status bramki Z16 + izolacji dyskursu:** **`0 B` diffu** względem `365e260` (i `6f1b310`) na wszystkich `29` plikach chronionych Z16 (`avt_linter.py`, `verifier.py`, `client_factory.py`, `rules.py`, `test_system.py`, `verify_purity.py`, `pricing_guard.py`, `main.py`, `context_cache.py`, `series_memory/.onomastic_lexicon.json`, `series_memory/*_bible.json`), na `scene_discourse.py` oraz na funkcji `_resolve_line_addressee` w `translator.py`.

---

## 1. Mapa 6 Atomowych Commitów

| Commit | Temat | Zakres mechanizmów |
|---|---|---|
| `8979eb3` | `fix(ingestion): 12.0.0 [1/6] — clean prosody/Whisper/StyleMatrix signals & RAM hygiene` | `A-1`, `A-2`, `A-3`, `E-1`, `E-2` |
| `0de71c0` | `feat(profiler): 12.0.0 [2/6] — stylistic data bridge, sequence tone & Bible glossary feed` | `B-1`, `B-2`, `B-3`, `D-1` |
| `93b1f5c` | `perf(prompts): 12.0.0 [3/6] — Zero-Cache SSOT dedup, episode SIGN dedup & stylistic F2 scoring` | `F-2/C-1`, `F-3`, `D-2` |
| `8f0c0bc` | `perf(phase2): 12.0.0 [4/6] — consolidated F2 batches, thread-safe retry observer (OBS-06) & A/B harness` | `F-1`, `H-3` (`OBS-06`) |
| `bc5c5f2` | `feat(learning): 12.0.0 [5/6] — TM quality_tier auto-ingestion & user-edit diff CLI` | `G-1`, `G-2` |
| `HEAD` | `docs(release): Standard 12.0.0 — PROJECT_MEMORY (ARB-081), Raport_wdrozenia_12.0.0 & link hygiene` | Dokumentacja & higiena linków |

---

## 2. Audyt 5 Warstw (`CORNERSTONE.md` — Prawo 12)

1. **Warstwa 1 (Ingestia, Sygnały Akustyczne i Profiler — [translator.py](../translator.py), [whisper_engine.py](../whisper_engine.py), [style_matrix.py](../style_matrix.py), [profiler.py](../profiler.py)):**
   - **`A-1`:** `_filter_dialogue_audio_events` odfiltrowuje napisy ekranowe i piosenki przed analizą F0 i wyznaczeniem prozodii; `STAFF_METADATA` jest przepuszczane 1:1 bez tłumaczenia.
   - **`A-2`:** konserwatywne odrzucanie segmentów Whisper o wysokim `no_speech_prob` oraz niskim `avg_logprob` eliminuje halucynacje dźwiękowe.
   - **`A-3`:** `StyleMatrix` rozpoznaje klucze napisów końcowych/personelu przed regułą `ALL CAPS`, nie degradowiąc napisów płacowych do plansz ekranowych.
   - **`B-1`, `D-1`:** `format_lean_episode_brief` eksportuje `episode_summary`, `dialogue_stylization`, `domain_expertise`, `key_conventions`, `yojijukugo_and_idioms`, do `20` relacji, adaptacyjną dyrektywę rejestru gatunkowego (`D-1`) oraz rozwiązane `relationship_pivots` w oknie `±20000 ms`.
   - **`B-2`, `B-3`:** `_resolve_active_dramatic_sequence` przekazuje aktywny ton sekwencji do F1 i F2; `SeriesBible` ładuje się przed `profile_episode`, przekazując kanoniczny glosariusz serii do Profilera.
2. **Warstwa 2 (Pamięć Serii i Ontologia w RAM — [series_memory.py](../series_memory.py)):**
   - **`E-1`:** `_strip_honorifics_from_registry_in_ram` czyści sufiksy honoryfikatywne w pamięci RAM przy `keep_honorifics=False` z bezwzględnym zachowaniem `0 B` diffu na dysku (`series_memory/*_bible.json`).
   - **`E-2`:** `_normalize_cyrillic_homoglyphs_in_latin` obejmuje krótkie słowa `1..4`-znakowe złożone wyłącznie z homoglifów cyrylickich, chroniąc poprawne tokeny wtrąceń obcojęzycznych z literami spoza zbioru homoglifów.
3. **Warstwa 3 (Kanon, Prompty Zero-Cache SSOT & F2 — [translator.py](../translator.py)):**
   - **`F-2/C-1`:** `_build_ssot_lean_bible_str` i deduplikacja sekcji w promptach Lean eliminują duplikację reguł/glosariuszy między kartą odcinka a kontekstem F1/F2.
   - **`F-3`:** `_deduplicate_episode_signs` scala powtarzające się plansze ekranowe przy zachowaniu indywidualnego mapowania czasowego i wymuszenia `ALL CAPS` podczas zapisu `.ass`.
   - **`D-2`, `F-1`, `H-3`:** `_score_phase2_editorial_risk` premiuje linie z pivotami dramatycznymi/alertami Profilera ponad krótkie repliki; `_consolidate_phase2_batches` i `_execute_consolidated_phase2_group` redukują liczbę wywołań F2 przez barierę konsolidacji (`AVT_CONSOLIDATE_F2=0` wyłącza natychmiastowo); `_enter_f2_retry_observer`/`_exit_f2_retry_observer` realizują obserwację błędów `503/429` przez `threading.local()`.
4. **Warstwa 4 & Pętla Uczenia (Deterministyczny Linter `0 B` + TM — [memory.py](../memory.py), [learn_from_edits.py](../tools/learn_from_edits.py)):**
   - **`G-1`:** idempotentna migracja `quality_tier` (`1` = korekta ludzka, `2` = baza legacy, `3` = auto-ingest odcinka AI) z preferencją wyższego autorytetu w `find_relevant_examples` i bezpiecznym hookiem `_auto_ingest_episode_to_tm` (`AVT_TM_AUTO_INGEST=0` wyłącza).
   - **`G-2`:** narzędzie CLI [learn_from_edits.py](../tools/learn_from_edits.py) porównuje `--raw` z `--edited`, zasila `UserFeedbackManager` i promuje poprawione pary do TM jako `quality_tier=1`.
5. **Warstwa 5 (Tarcza Regresyjna — [test_standard_12_0_0.py](../tests/test_standard_12_0_0.py)):**
   - `19` nowych, nietautologicznych testów jednostkowych i integracyjnych pokrywających wszystkie mechanizmy `A-1..H-3` i `G-1..G-2`.

---

## 3. Wyniki Weryfikacji i Benchmark A/B Fazy 2 (`F-1`)

### 3.1. Bramki Statyczne i Zestawy Testów
- `verify_purity.py`: **12/12 bramek PASS** (`WERDYKT: 100% CZYSTY I ZGODNY Z STANDARDEM 9.0`).
- `pytest tests/test_standard_12_0_0.py -v`: **19/19 PASSED**.
- `pytest tests/ -q`: **491 passed**.
- `pytest test_system.py -m "not slow and not network" -k "not test_batch_coalescence_ssot_prompt_and_cot_streamlining_guard" -q`: **70 passed, 154 deselected**.
- `verify_8_fixes.py`: **PASS** (`WSZYSTKIE 8 UWAG ZOSTAŁO W 100% ZAADRESOWANYCH I NAPRAWIONYCH!`).
- `verify_12_fixes.py`: **12/12 PASS**.
- `verify_ultimate_pipeline.py`: **15/15 PASS**.
- `audit_diff.ps1 -BaseRef "365e260"`: **WERDYKT: VICTORY CONFIRMED -- KOD CZYSTY I UOGOLNIONY**.

### 3.2. Benchmark A/B Konsolidacji F2 ([verify_f2_consolidation_ab.py](../tools/verify_f2_consolidation_ab.py))
- **Tryb offline (`--dry-run` na logu produkcyjnym `logs/chii_fuyo_ASW__Chii_Fuyo_-_07__1080p_HEVC__AB658E9E__extracted_20261125_223445_events.jsonl`):**
  - **Wariant A (1:1):** `8 wywołań F2`, `64 linii`.
  - **Wariant B (Skonsolidowany `F-1`):** `2 wywołania F2`, `64 linii`, oszacowanie kosztu `~0.5100 PLN`.
- **Tryb `--live` (porównanie jakości odpowiedzi API):** w środowisku wdrożeniowym nie był skonfigurowany klucz `GEMINI_API_KEY`, w związku z czym uruchomienie `--live` na prawdziwym modelu Hydrogen pozostaje do wykonania przez Operatora po wdrożeniu (`AVT_CONSOLIDATE_F2=0` stanowi bezpieczny przełącznik wycofania bez zmian w kodzie).

---

## 4. Rejestr `OBS-06`, `OBS-13` i `KNOWN GAP`

- **`OBS-06`:** `RESOLVED IN CODE (12.0.0, H-3 threading.local() ref-counted dispatcher)` — wymaga weryfikacji produkcyjnej przy `max_workers_f2 >= 2`.
- **`OBS-13a/b/c`:** `DEFERRED → 12.1.0` (`0 B` diffu w `scene_discourse.py` i `_resolve_line_addressee`).
- **`KNOWN GAP` (`OPEN (non-blocking — awaiting prod benchmark)`):** `DEF-04`, `OBS-01`, `OBS-04`, `DEF-05`, `OBS-09`, `OBS-11`, `OBS-12`, `OBS-14`, `OBS-15` oraz wszystkie nowo wdrożone mechanizmy `12.0.0` (`A-1..H-3`, `G-1..G-2`, `F-1 --live`).

---

## 5. Hotfix `12.0.0a` (Domknięcie Audytu Konfrontacyjnego `12.0.0`)

- **Baza startowa:** `1ebbea1` (`Standard 12.0.0`)
- **Commity Hotfixu `12.0.0a`:** `db12547` (`fix(pipeline)`), `23290c7` (`test(pipeline)`), `HEAD` (`docs(release)`)
- **Izolacja Z16 i dyskursu:** **`0 B` diffu** względem `365e260` i `1ebbea1` na wszystkich `29` plikach chronionych Z16, `scene_discourse.py`, `_resolve_line_addressee` oraz `client_pool_f1`/`client_pool_f2`.

| Defekt | Moduł | Przyczyna źródłowa w `1ebbea1` | Naprawa w `12.0.0a` |
|---|---|---|---|
| `BUG #1` (`A-1`) | [translator.py](../translator.py) | `_filter_dialogue_audio_events` rozpakowywał wyłącznie 4-krotki i rzucał `IndexError` na produkcyjnych 2-krotkach `(b_id, SSAEvent)` z linii `4990` | Obsługa 2/3/4-krotek z ekstrakcją tagów ASS i zwrotem oryginalnego kształtu elementu |
| `BUG #2` (`F-1`) | [translator.py](../translator.py) | `_consolidate_phase2_batches` zapisywał `scene_diagnosis` jako `str`, blokując sekcję diagnozy i `elif scene_summary` w `verifier.py` | Budowa strukturalnego `dict` (`dramatic_context`, `dominant_tone`, ...) oraz wstrzyknięcie aktywnego tonu `B-2` z `episode_profile` |
| `BUG #3` (`F-1` A/B) | [verify_f2_consolidation_ab.py](../tools/verify_f2_consolidation_ab.py) | Nieistniejący klucz `payload["items"]`, fallback na `refined_pl` + placeholdery, podwójna selekcja oraz zerowe `tok_a`/`tok_b` w `--live` | Pełna rekonstrukcja z `scene_discourse` + `line_evolution` + `phase1_batch` (`8 -> 3` wywołania, `112` linii w *Chii Fuyo-07*) + sumowanie `_thread_local.last_batch_token_usage` |
| `BUG #4` (`G-1`) | [translator.py](../translator.py) | Odczyt nieistniejącego `self.series_bible.series_title` powodował fallback na nazwę pliku wideo i `0` trafień `require_same_series=True` | Priorytetowy odczyt `self.series_bible.anime_title` z fallbackiem na `self.series_title` i nazwę pliku |
| `BUG #5` (`F-3`) | [translator.py](../translator.py) | Surowe `.upper()` zamieniało tagi inline `{\i1}`, `{\b1}`, `\N`, `\n`, `\h` na wielkie litery | Helper `_uppercase_preserving_ass_tags` podnoszący wielkość liter wyłącznie poza `{...}` i `\[Nnh]` |

### Wyniki bramek po Hotfixie `12.0.0a`
- `pytest tests/test_standard_12_0_0.py -v`: **24 / 24 PASSED** (w tym `test_bug1..test_bug5`).
- `pytest tests/ -q`: **496 passed**.
- `pytest test_system.py -m "not slow and not network" -k "not test_batch_coalescence_ssot_prompt_and_cot_streamlining_guard" -q`: **70 passed, 154 deselected**.
- Bramki statyczne i audyt: `verify_purity.py` **12/12 PASS**, `verify_8_fixes.py` **8/8 PASS**, `verify_12_fixes.py` **12/12 PASS**, `verify_ultimate_pipeline.py` **15/15 PASS**, `audit_diff.ps1 -BaseRef "365e260"` **VICTORY CONFIRMED**.
- Dry-run `verify_f2_consolidation_ab.py --events logs/chii_fuyo_ASW__Chii_Fuyo_-_07__1080p_HEVC__AB658E9E__extracted_20261125_223445_events.jsonl`: **Wariant A: `8 wywołań F2, 112 linii`** vs **Wariant B: `3 wywołania F2, 112 linii`** (`~0.4300 PLN` szacowanego spadku kosztu promptu).
