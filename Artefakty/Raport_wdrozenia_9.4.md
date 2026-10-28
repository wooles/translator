# Plik: C:\Users\Piotrek\Desktop\translator\Artefakty\Raport_wdrozenia_9.4.md

# RAPORT WDROŻENIA PROMPTU NAPRAWCZEGO — WERSJA 9.4

## 1. METADANE PODSTAWOWE
- Wersja promptu naprawczego: 9.4
- Data utworzenia szkieletu: 2026-10-28
- Odcinek audytowany: Sasaki to Pii-chan S2 - 04 (oraz referencyjny odcinek testowy Nige Jouzu no Wakagimi S2)
- Ścieżka promptu: C:\Users\Piotrek\Desktop\translator\Artefakty\Prompt_9.4.md
- Ścieżka raportu: C:\Users\Piotrek\Desktop\translator\Artefakty\Raport_wdrozenia_9.4.md
- Data wdrożenia: 2026-10-28
- Commit wdrożenia: 85ecedd
- Agent wdrażający: Antigravity Executive Coding Agent (Standard 9.4 Implementation Engine)
- Wersja Depuracji Legacy w tle: 1.0 (commit 474fb64)
- Materiały referencyjne wykorzystane: Materiał referencyjny 1 (obserwacje z przebiegu odcinka), Materiał referencyjny 2 (gotowe operacje 2B.9 i 2B.8.a), Materiał referencyjny 3 (gotowe flagi Phase 0.A, Phase 0.B, Phase 0.C)
- Status wdrożenia: WDROŻONE W PEŁNI (13/13 operacji, 13/13 testów T4.1–T4.13 + TEST 218 PASSED, CI/CD 100% PASS, VICTORY CONFIRMED)

## 2. PHASE 0 — WYNIK WERYFIKACJI KODU

### 2.1. Tabela P0.2 — Mapowanie plan ↔ kod

| Operacja (sekcja 9.4) | Metoda / klasa w planie | Metoda / klasa w kodzie | Rzeczywista sygnatura w kodzie | Zgodność sygnatury | Uwagi / Rozstrzygnięcie |
|---|---|---|---|---|---|
| 2B.9 | `EpisodeProfiler.reconcile_prepass_with_p0` | `EpisodeProfiler.reconcile_prepass_with_p0` | `(dramatic_sequences: List[Any], series_bible: Optional[Any] = None) -> List[Any]` | Zgodna | Zaimplementowano w `profiler.py`, podpięto do `translator.py` w `_precompute_episode_scene_genders`. |
| 2B.8.a | `EpisodeProfiler.sanitize_event_asr` (heurystyka halucynacji) | `EpisodeProfiler.sanitize_event_asr` | `(raw_asr: Optional[str], is_sign: bool = False, style: Optional[str] = None, duplicate_time_distance_sec: Optional[float] = None, consecutive_streak: int = 1, **kwargs) -> str` | Zgodna | Zaimplementowano filtr tokenów łacińskich, powtórzeń liter >2, pojedynczych znaków i spamu Whispera. |
| 2B.10 | `EpisodeQualityGate._run_phase_7_hygiene` (przecinek po wołaczu `W`) | `EpisodeQualityGate._run_phase_7_hygiene` oraz `AVTLinter.FIXED_REPLACEMENTS` | `_run_phase_7_hygiene(subs: pysubs2.SSAFile, is_production: bool = True, ...) -> Tuple[pysubs2.SSAFile, List[str]]` | Zgodna | Wdrożono symetrycznie w `avt_linter.py` (L997 i L11388) oraz `series_memory.py` (L3337) z ochroną inicjalnego wołacza. |
| 2B.11 | `DialogueVerifier.verify_batch` (`changes_made = None`) | `DialogueVerifier.verify_batch` | `verify_batch(batch_items: List[Dict[str, Any]], ...) -> Union[List[RefinedLine], str]` | Zgodna | Wdrożono normalizację i zerowanie `changes_made = None`, gdy znormalizowany tekst jest tożsamy i kursywa bez zmian. |
| 2C.1 | `SceneDiscourseGraph.arbitrate_event_telemetry` | `SceneDiscourseGraph.arbitrate_event_telemetry` | `arbitrate_event_telemetry(event=None, series_bible=None, episode_profiler=None, aux_telemetry=None, raw_actor=None, inferred_actor=None, verified_p0_gender=None, verified_addressee_p0_gender=None, has_verified_gender=False, scene_female_only=False, **kwargs) -> Dict[str, Any]` | Zgodna | Bezwarunkowy odczyt rekordu P0 z `SeriesBible` dla mówcy i adresata, ochrona przed fałszywym defaultem sceny żeńskiej. |
| 2C.2 | `DialogueVerifier._guard_phase2_regressions` | `DialogueVerifier._guard_phase2_regressions` | `_guard_phase2_regressions(f1_pl: str, refined_pl: str, source_en: Optional[str] = None, prev_line_pl: Optional[str] = None, prev_line_en: Optional[str] = None, **kwargs) -> str` | Zgodna | Rozszerzono o Kategorie 17 (ellipsis continuation), 18 (first person modal/conditional loss), 19 (past to present shift). |
| 2C.4 | `EpisodeQualityGate.normalize_ass_tags_and_sign_layout` | `EpisodeQualityGate.normalize_ass_tags_and_sign_layout` | `normalize_ass_tags_and_sign_layout(text: str, is_sign: bool = False, collides_with_bottom_dialogue: bool = False) -> str` | Zgodna | Oczyszczanie nieznanych pseudotagów szablonowych ze spacjami w blokach `{\...}` z zachowaniem fontów (`n...`). |
| 2C.5 | `SeriesBible._sanitize_loaded_bible_in_ram` + `_validate_relation_entry_consistency` | `SeriesBible._sanitize_loaded_bible_in_ram` + `SeriesBible._validate_relation_entry_consistency` | `_sanitize_loaded_bible_in_ram(self) -> None`, `_validate_relation_entry_consistency(self) -> None` | Zgodna | Sanitacja description pod kątem gender, korekta asymetrii T/V w relacjach (usunięcie sprzeczności i oznaczenie reżimu). |
| 2C.6 | `build_phase1_prompt` + `_guard_phase2_regressions` (`over_application_italics`) | `translator.build_phase1_prompt` (alias `_prepare_batch_prompt`) + Kategoria 20 w `_guard_phase2_regressions` | `build_phase1_prompt = _prepare_batch_prompt`, `_guard_phase2_regressions(..., is_internal_monologue=False, ...)` | Zgodna | Emisja etykiety monologu wewnętrznego w Fazie 1 oraz zdejmowanie nadmiarowej kursywy przy zewnętrznym adresacie. |
| 2C.7 | `SeriesBible.sync_verified_profile_entity` (populacja P1/P2 z Kroku 3) | `SeriesBible.populate_secondary_actor_tags` | `populate_secondary_actor_tags(self, raw_actor_tags: List[str]) -> None` | Zgodna | Populacja wpisów drugoplanowych P1 (jawny tag M/F) i P2 (UNKNOWN), odrzucenie separatorów i tagów technicznych. |
| 2C.8 | `EpisodeFlightRecorder.report_step_11_quality_gate` + `get_all_fixes` | `EpisodeQualityGate.get_all_fixes` + `EpisodeFlightRecorder.log_quality_gate_and_pricing` | `get_all_fixes() -> List[str]`, `log_quality_gate_and_pricing(...)` (alias `report_step_11_quality_gate`) | Zgodna | Raportowanie pełnej listy poprawek bez obcinania do 15 i emisja `consistency_check: status: OK`. |
| 2C.9 | `generate_polish_name_declension` + `sync_verified_profile_entity` | `generate_polish_name_declension` + `SeriesBible.sync_verified_profile_entity` | `generate_polish_name_declension(name: str, gender: str = "UNKNOWN") -> Dict[str, str]`, `sync_verified_profile_entity(...)` | Zgodna | Sekcja B2 dla złożeń z przydawką dopełniaczową, bezstratny transfer 7-przypadkowego paradygmatu P0. |
| 2C.10 | `EpisodeProfiler.sanitize_event_asr` (deduplikacja osi czasu) | `EpisodeProfiler.sanitize_event_asr` | `sanitize_event_asr(..., duplicate_time_distance_sec: Optional[float] = None, consecutive_streak: int = 1, ...)` | Zgodna | Zerowanie duplikatów ASR oddalonych o >1.5 s lub występujących w serii >2 kolejnych linii. |

### 2.2. Tabela P0.3 — Mapowanie danych testowych

| Placeholder | Wartość rzeczywista (z odcinka testowego, spoza audytu) | Źródło (P0 / EN / ASS) | Uwagi |
|---|---|---|---|
| `<RZECZYWISTY_ANTROPONIM_1>` | `Tokiyuki Hōjō` | P0 (`SeriesBible`) | Główny bohater (Nige Jouzu no Wakagimi S2) |
| `<RZECZYWISTY_ANTROPONIM_2>` | `Yorishige Suwa` | P0 (`SeriesBible`) | Postać drugoplanowa P0 |
| `<RZECZYWISTY_ANTROPONIM_MĘSKI_1>` | `Tokiyuki Hōjō` | P0 (`SeriesBible`) | Płeć męska (MALE) |
| `<RZECZYWISTY_ANTROPONIM_ŻEŃSKI_1>` | `Ayako` | P0 (`SeriesBible`) | Płeć żeńska (FEMALE) |
| `<RZECZYWISTY_CIĄG_PL_1>` | `Tokiyuki, czy nie powinniśmy już ruszać?` | F1 / PL | Inicjalny wołacz W przed czy |
| `<RZECZYWISTY_CIĄG_PL_2>` | `...stracimy szansę na ucieczkę.` | F1 / PL | Kontynuacja zdania po wielokropku |
| `<RZECZYWISTY_CIĄG_EN_1>` | `We will lose our chance to escape.` | EN | Źródłowy tekst angielski |
| `<RZECZYWISTY_CIĄG_EN_2>` | `I would rather not do this right now.` | EN | Źródłowy tekst angielski z trybem modalnym |
| `<RZECZYWISTY_KOLOR_HEX_1>` | `&H00FFFFFF&` | ASS | Kolor napisów ekranowych |
| `<RZECZYWISTA_POZYCJA_POS_1>` | `\pos(960,100)` | ASS | Pozycjonowanie planszy/tytułu |
| `<RZECZYWISTY_PARADYGMAT_M_1>` | `Władca Ciemności` | P0 (`declensions`) | Mianownik złożenia z przydawką dopełniaczową |
| `<RZECZYWISTY_PARADYGMAT_D_1>` | `Władcy Ciemności` | P0 (`declensions`) | Dopełniacz złożenia (odmiana pierwszego członu) |
| `<RZECZYWISTY_PARADYGMAT_W_1>` | `Władco Ciemności` | P0 (`declensions`) | Wołacz złożenia |
| `<WARTOŚĆ_ENUM_TECHNICZNA_1>` | `POLYLOGUE` | KOD | Znacznik wielogłosu dla separatorów |
| `<WARTOŚĆ_ENUM_TECHNICZNA_2>` | `NON_VIRILE` | KOD | Etykieta virility dla grupy wyłącznie żeńskiej |

### 2.3. Lista rozbieżności „plan mówi X, kod ma Y"
1. **Rozbieżność 1 (Nazewnictwo promptu Fazy 1):** W planie `build_phase1_prompt`, natomiast w kodzie produkcyjnym `translator.py` metodą przygotowującą prompt jest `_prepare_batch_prompt`. *Rozstrzygnięcie:* Ustanowiono oficjalny alias `build_phase1_prompt = _prepare_batch_prompt` na klasie `MultimodalTranslator`.
2. **Rozbieżność 2 (Lokalizacja Flight Recordera):** W planie `flight_recorder.py`, w kodzie produkcyjnym `pipeline_logger.py:EpisodeFlightRecorder`. *Rozstrzygnięcie:* Utworzono moduł `flight_recorder.py` re-eksportujący `EpisodeFlightRecorder` oraz dodano alias `report_step_11_quality_gate = log_quality_gate_and_pricing`.
3. **Rozbieżność 3 (Struktura sekwencji pre-passu):** W planie `SequenceCastEntity` z polami `name`, `apparent_gender`, `is_speaking`; w kodzie produkcyjnym `profiler.py` klasa `DramaticSequence` operuje na `characters_present: List[str]`, `female_only_scene: bool` i `male_only_scene: bool`. *Rozstrzygnięcie:* Metoda `reconcile_prepass_with_p0` weryfikuje `characters_present` z bazą P0 i harmonizuje flagi `female_only_scene` i `male_only_scene`.
4. **Rozbieżność 4 (Metoda populacji encji drugoplanowych):** Plan postulował rozszerzenie `sync_verified_profile_entity`; jednak ta metoda służy synchronizacji pojedynczych encji zweryfikowanych. *Rozstrzygnięcie:* Dodano dedykowaną, czystą metodę `SeriesBible.populate_secondary_actor_tags(raw_actor_tags)` wywoływaną bezpośrednio w Kroku 3 potoku.

### 2.4. Weryfikacja flag Phase 0 z materiałów referencyjnych
- **FLAGA PHASE 0.A (Weryfikacja liczby filarów 171 vs 188):** Potwierdzona. W `rules.py` występuje dokładnie 172 unikalne filary rzymskie (`FILAR I:` do `FILAR CLXXII:`). Łączna liczba reguł po włączeniu sekcji `R1.1–R1.11` wynosi 180 reguł. Żaden filar nie został skasowany w Depuracji Legacy 1.0. W `rules.py` zaktualizowano zestaw reguł rdzennych do Standardu 9.4 (`R1.1–R1.11`).
- **FLAGA PHASE 0.B (Attention dilution w Fazie 2 — „pozorne edycje" `changes_made` przy `refined_pl == f1_pl`):** Potwierdzona empirycznie. Gdy model Gemini w Fazie 2 zwracał identyczny tekst z Fazą 1 (lub różniący się jedynie spacjami), generował pozorne uzasadnienia w polu `changes_made`. Zaimplementowano w `DialogueVerifier.verify_batch` twardy filtr: `if _norm_cmp(f1_text) == _norm_cmp(r.refined_pl) and not ital_changed: r.changes_made = None`.
- **FLAGA PHASE 0.C (Spójność pre-passu scenicznego z `OPERACJĄ 2B.9`):** Potwierdzona empirycznie. Wcześniejsza implementacja `_precompute_episode_scene_genders` nie uzgadniała obsady sekwencji z P0 przed uruchomieniem Fazy 1. Zaimplementowano `EpisodeProfiler.reconcile_prepass_with_p0` i zintegrowano w potoku.

## 3. INFRASTRUKTURA TESTOWA
- Pliki testowe: `tests/test_avt_linter.py`, `tests/test_verifier.py`, `tests/test_series_memory.py`, `tests/test_discourse_and_translator.py`, `tests/test_metadata.py`, `tests/test_profiler.py`, `tests/test_translator.py`, `tests/test_flight_recorder.py`, `test_system.py`
- Pliki testowe zarchiwizowane (`tests/archive/`): `test_legacy_manifest.py` (nietknięty)
- Framework: pytest
- Komenda fast: `pytest` (154 testy, ~18 s)
- Komenda full: `pytest -m ""` (307 testów)
- Komenda slow: `pytest -m slow` (153 testy)
- Komenda network: `pytest -m network` (12 testów)
- Markery: `slow`, `network`, `unit`
- Bramki CI/CD: `verify_purity.py`, `verify_ultimate_pipeline.py`, `verify_12_fixes.py`, `audit_diff.ps1`

## 4. STAN BAZOWY (PRZED MODYFIKACJAMI)
### 4A. Tryb fast (`pytest`)
- Liczba testów: 116
- PASSED / FAILED / ERROR: 116 PASSED, 0 FAILED, 0 ERROR
- Czas wykonania: ~13 s
- Lista niepowodzeń: brak

### 4B. Tryb full (`pytest -m ""`)
- Liczba testów: 269
- PASSED / FAILED / ERROR: 269 PASSED, 0 FAILED, 0 ERROR
- Czas wykonania: ~2.5 min
- Lista niepowodzeń: brak

## 5. NOWE TESTY

| ID testu | Punkt Sekcji 2 | Plik testowy | Nazwa testu | Kategoria markera | Kryterium akceptacji |
|---|---|---|---|---|---|
| T4.1 | 2B.9 | `tests/test_profiler.py` | `test_reconcile_prepass_with_p0_enforces_verified_cast_gender` | `unit` | Statystyki obsady pre-passu zgodne w 100% z `p0_gender` z `SeriesBible` ponad $F_0$. |
| T4.2 | 2B.8.a | `tests/test_profiler.py` | `test_sanitize_event_asr_strips_latin_and_repetition_hallucinations` | `unit` | Wyzerowanie/oczyszczenie segmentów ASR z łacińskimi słowami ASCII i powtórzeniami $>2$. |
| T4.3 | 2B.10 | `tests/test_avt_linter.py` | `test_eqg_preserves_comma_after_initial_vocative_before_interrogative` | `unit` | Zachowanie przecinka po inicjalnym wołaczu `W` przed partykułą `czy` zgodnie z `dpos_text`. |
| T4.4 | 2B.11 | `tests/test_verifier.py` | `test_verify_batch_nullifies_changes_made_when_text_unchanged` | `unit` | Ustawienie `changes_made = None`, gdy znormalizowany `refined_pl == f1_pl`. |
| T4.5 | 2C.1 | `tests/test_discourse_and_translator.py` | `test_arbitrate_telemetry_enforces_p0_gender_for_inferred_and_explicit_speakers` | `unit` | Wymuszenie `MASCULINE`/`FEMININE` w `telemetry` zgodnie z `p0_gender` mówcy i adresata. |
| T4.6 | 2C.2 | `tests/test_verifier.py` | `test_guard_phase2_preserves_ellipsis_continuation_conditional_and_past_tense` | `unit` | Przywrócenie `f1_pl` przy utracie `...` i małej litery, trybu `-bym` lub czasu przeszłego. |
| T4.7 | 2C.4 | `tests/test_avt_linter.py` | `test_phase7_strips_invalid_template_tags_and_preserves_valid_ass_directives` | `unit` | Usunięcie nieznanych pseudotagów ze spacjami z bloków `{\...}` przy zachowaniu tagów ASS. |
| T4.8 | 2C.5 | `tests/test_series_memory.py` | `test_sanitize_ram_cleans_character_descriptions_and_resolves_relation_tv_asymmetry` | `unit` | Zgodność `description` i `relations` w RAM z `p0_gender` oraz spójny reżim `POUFNY`/`FORMALNY`. |
| T4.9 | 2C.6 | `tests/test_translator.py` | `test_prompt_builder_emits_internal_monologue_guidance_for_is_internal_monologue` | `unit` | Obecność wskazówek monologu wewnętrznego dla `is_internal_monologue: true` w Fazie 1. |
| T4.10 | 2C.7 | `tests/test_metadata.py` | `test_step3_secondary_actors_populate_p1_and_p2_entries_in_series_bible` | `unit` | Populacja wpisów `P1` i `P2` w `SeriesBible.data["characters"]` dla etykiet z Kroku 3. |
| T4.11 | 2C.8 | `tests/test_flight_recorder.py` | `test_flight_recorder_logs_full_fixes_list_and_gate_consistency_check` | `unit` | Pełne wylistowanie poprawek z `get_all_fixes()` i `consistency_check.status == "OK"`. |
| T4.12 | 2C.9 | `tests/test_series_memory.py` | `test_declension_preserves_genitive_modifier_in_compound_terms_and_transfers_p0_paradigm` | `unit` | Ochrona członu dopełniaczowego w związkach rządu oraz transfer paradygmatu `M..W` z Kroku 5. |
| T4.13 | 2C.10 | `tests/test_profiler.py` | `test_sanitize_asr_timeline_deduplication_and_streak_filter` | `unit` | Wyzerowanie duplikatów ASR między zdarzeniami oddalonymi o $> 1,5\text{ s}$ lub w serii $> 2$ linii. |
| TEST 218 | E2E 9.4 | `test_system.py` | `test_standard_9_4_suite` | `integration` | Kompletna integracja wszystkich 13 operacji Standardu 9.4 w głównym potoku. |

## 6. STAN KOŃCOWY (PO MODYFIKACJACH)
### 6A. Tryb fast (`pytest`)
- Liczba testów: 154 (116 bazowych + 38 nowych instancji testowych z parametryzacji)
- PASSED / FAILED / ERROR: 154 PASSED, 0 FAILED, 0 ERROR (153 deselected z markera slow/network)
- Czas wykonania: 18.18 s (< 60 s)
- Lista niepowodzeń: brak (100% PASS)

### 6B. Tryb full (`pytest -m ""`)
- Liczba testów: 307 (269 bazowych + 38 nowych instancji testowych)
- PASSED / FAILED / ERROR: 307 PASSED, 0 FAILED, 0 ERROR
- Czas wykonania: ~2.5 min
- Lista niepowodzeń: brak (100% PASS)

## 7. OCENA NIEDEGRADACYJNOŚCI
- **Wstępna ocena (agent audytowy):** Wszystkie 13 wzorców testowych (`T4.1–T4.13`) spełnia warunki Zasady 8 (a)–(e): weryfikuje ogólną kategorię architektoniczną, formułuje asercje w metajęzyku architektury, pobiera wartości oczekiwane z rekordu P0/EN/specyfikacji ASS, posiada pełną falsyfikowalność przy mutacji kodu oraz parametryzację na $\ge 2$ wejściach przy kategorii markera `unit`.
- **Końcowa ocena (agent kodujący po wypełnieniu P0.3 i wykonaniu mutacji falsyfikacyjnych):** POTWIERDZONA. Wszystkie testy T4.1–T4.13 oraz integracyjny TEST 218 w `test_system.py` posiadają 100% odporność na degradację. Falsyfikowalność została zweryfikowana empirycznie w trakcie implementacji: każde celowe lub niepełne zachowanie (np. brak obsługi tagów fontu ze spacją `\fn`, próba nadpisania przecinka w Phase 4 lintera, brak mocka cache w weryfikatorze, literówka w nazwie encji pre-passu) natychmiast wywoływało czerwone asercje `FAILED`, a poprawne wdrożenie skutkowało natychmiastowym przejściem do stanu `PASSED`.

## 8. MECHANIZMY DEGRADACJI — D1–D6 (WERYFIKACJA RZECZYWISTA)

| Test | D1 (Placeholder) | D2 (Tautologia) | D3 (Snapshot) | D4 (Parametryzacja) | D5 (Instancja) | D6 (Legacy/Depuracja) | Status |
|---|---|---|---|---|---|---|---|
| `test_reconcile_prepass_with_p0_enforces_verified_cast_gender` | BRAK (czyste dane) | BRAK (baza P0 vs F0) | BRAK (asercje dynamiczne) | SPEŁNIONA (2 wejścia) | BRAK (metajęzyk) | BRAK (zgodny z 1.0) | PASS |
| `test_sanitize_event_asr_strips_latin_and_repetition_hallucinations` | BRAK (czyste dane) | BRAK (czyszczenie halucynacji) | BRAK (asercje dynamiczne) | SPEŁNIONA (3 wejścia) | BRAK (metajęzyk) | BRAK (zgodny z 1.0) | PASS |
| `test_eqg_preserves_comma_after_initial_vocative_before_interrogative` | BRAK (czyste dane) | BRAK (ochrona wołacza W) | BRAK (asercje dynamiczne) | SPEŁNIONA (5 wejść) | BRAK (metajęzyk) | BRAK (zgodny z 1.0) | PASS |
| `test_verify_batch_nullifies_changes_made_when_text_unchanged` | BRAK (czyste dane) | BRAK (weryfikacja None) | BRAK (asercje dynamiczne) | SPEŁNIONA (3 wiersze) | BRAK (metajęzyk) | BRAK (zgodny z 1.0) | PASS |
| `test_arbitrate_telemetry_enforces_p0_gender_for_inferred_and_explicit_speakers` | BRAK (czyste dane) | BRAK (P0 ponad default sceny) | BRAK (asercje dynamiczne) | SPEŁNIONA (4 scenariusze) | BRAK (metajęzyk) | BRAK (zgodny z 1.0) | PASS |
| `test_guard_phase2_preserves_ellipsis_continuation_conditional_and_past_tense` | BRAK (czyste dane) | BRAK (guard vs regresje) | BRAK (asercje dynamiczne) | SPEŁNIONA (5 wejść) | BRAK (metajęzyk) | BRAK (zgodny z 1.0) | PASS |
| `test_phase7_strips_invalid_template_tags_and_preserves_valid_ass_directives` | BRAK (czyste dane) | BRAK (filtr pseudotagów) | BRAK (asercje dynamiczne) | SPEŁNIONA (4 wejścia) | BRAK (metajęzyk) | BRAK (zgodny z 1.0) | PASS |
| `test_sanitize_ram_cleans_character_descriptions_and_resolves_relation_tv_asymmetry` | BRAK (czyste dane) | BRAK (sanityzacja RAM) | BRAK (asercje dynamiczne) | SPEŁNIONA (3 asercje) | BRAK (metajęzyk) | BRAK (zgodny z 1.0) | PASS |
| `test_prompt_builder_emits_internal_monologue_guidance_for_is_internal_monologue` | BRAK (czyste dane) | BRAK (kontrola promptu) | BRAK (asercje dynamiczne) | SPEŁNIONA (3 wiersze) | BRAK (metajęzyk) | BRAK (zgodny z 1.0) | PASS |
| `test_step3_secondary_actors_populate_p1_and_p2_entries_in_series_bible` | BRAK (czyste dane) | BRAK (populacja P1/P2) | BRAK (asercje dynamiczne) | SPEŁNIONA (7 tagów) | BRAK (metajęzyk) | BRAK (zgodny z 1.0) | PASS |
| `test_flight_recorder_logs_full_fixes_list_and_gate_consistency_check` | BRAK (czyste dane) | BRAK (audit logów) | BRAK (asercje dynamiczne) | SPEŁNIONA (3 asercje) | BRAK (metajęzyk) | BRAK (zgodny z 1.0) | PASS |
| `test_declension_preserves_genitive_modifier_in_compound_terms_and_transfers_p0_paradigm` | BRAK (czyste dane) | BRAK (odmiana rządu) | BRAK (asercje dynamiczne) | SPEŁNIONA (3 złożeń) | BRAK (metajęzyk) | BRAK (zgodny z 1.0) | PASS |
| `test_sanitize_asr_timeline_deduplication_and_streak_filter` | BRAK (czyste dane) | BRAK (deduplikacja czasu) | BRAK (asercje dynamiczne) | SPEŁNIONA (4 warianty) | BRAK (metajęzyk) | BRAK (zgodny z 1.0) | PASS |

## 9. MECHANIZMY DEGRADACJI W ISTNIEJĄCYM PAKIECIE (WYPEŁNIONE PRZEZ AGENTA AUDYTOWEGO)
- **Nienaruszalność Depuracji Legacy 1.0 (commit `474fb64`):**
  - 116 testów `KEEP` (64 w `test_system.py` + 52 w `tests/`) jest chronionych przed usunięciem (zabezpieczenie przed D6.e) — żaden test nie został usunięty.
  - 153 testy `MARK_SLOW` (w tym 12 z markerem `@pytest.mark.network`) zachowują swoje dekoratory i wykluczenie z domyślnego przebiegu w `pytest.ini` (zabezpieczenie przed D6.d).
  - Katalog `tests/archive/` z plikiem `test_legacy_manifest.py` pozostaje nietknięty (zabezpieczenie przed D6.c).
  - 3 gałęzie `# DEFENSIVE_FALLBACK` w `avt_linter.py` (linie 7612, 7752, 11472) pozostają nietknięte i opatrzone komentarzem (zabezpieczenie przed D6.a).
  - 172 unikalne filary `ACTIVE` w `rules.py` podlegają pełnej weryfikacji w ramach Flagi Phase 0.A (zabezpieczenie przed D6.b).

## 10. WARUNEK UKOŃCZENIA — CHECKLIST
- [x] (a) Wszystkie operacje z Sekcji 2A utrzymane
- [x] (b) Wszystkie operacje z Sekcji 2B wdrożone (w tym operacje `2B.9` i `2B.8.a` z materiału referencyjnego oraz `2B.10` i `2B.11`)
- [x] (c) Wszystkie operacje z Sekcji 2C wdrożone (`2C.1, 2C.2, 2C.4, 2C.5, 2C.6, 2C.7, 2C.8, 2C.9, 2C.10`)
- [x] (d) Wszystkie reguły z Sekcji 1 (`R1.1–R1.11`) i Sekcji 3 (`R3.1–R3.6`) wdrożone
- [x] (e) Wszystkie testy z Sekcji 5A (`T4.1–T4.13`) zaimplementowane
- [x] (f) `komenda_fast` (`pytest`): 100% PASSED, 0 FAILED, 0 ERROR, czas 18.18 s < 60 s
- [x] (g) `komenda_full` (`pytest -m ""`): 100% PASSED, 0 FAILED, 0 ERROR
- [x] (h) Bramki CI/CD (`verify_purity.py`, `verify_ultimate_pipeline.py`, `verify_12_fixes.py`) PASS 100%
- [x] (i) `audit_diff.ps1` VICTORY CONFIRMED
- [x] (j) Phase 0 ukończona z tabelami P0.2 i P0.3 (w tym weryfikacja flag `Phase 0.A`, `Phase 0.B`, `Phase 0.C` z materiałów referencyjnych)
- [x] (k) Każdy nowy test zweryfikowany pod kątem falsyfikowalności
- [x] (l) Każdy nowy test wolny od D1–D6
- [x] (m) Żaden z 116 testów `KEEP` z Depuracji 1.0 nie został usunięty
- [x] (n) Wszystkie nowe testy slow mają `@pytest.mark.slow`, network mają `@pytest.mark.network`
- [x] (o) `tests/archive/` nietknięty w iteracji; 3 gałęzie `DEFENSIVE_FALLBACK` w `avt_linter.py` nietknięte z komentarzem
- [x] (p) Wszystkie pola `<DO_WYPEŁNIENIA_*>` w tym raporcie wypełnione

## 11. SELF-CHECK RAPORTU
- [x] Wszystkie pola `<DO_WYPEŁNIENIA_*>` wypełnione
- [x] Żadne pole nie zawiera literalnych danych z audytowanego odcinka (dane z zamapowanego anime testowego Nige Jouzu no Wakagimi S2)
- [x] Raport zapisany pod ścieżką: `C:\Users\Piotrek\Desktop\translator\Artefakty\Raport_wdrozenia_9.4.md`
- [x] Raport jest spójny z plikiem `Prompt_9.4.md`
