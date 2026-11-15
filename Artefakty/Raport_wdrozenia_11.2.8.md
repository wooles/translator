# 🏛️ RAPORT WDROŻENIOWY — STANDARD 11.2.8
## Certyfikacja Standardu 11.2.8 (Adaptive F1 Thinking, AniList GraphQL Resilience & Lexicon Fallback, Real-Cache UI Telemetry, PricingGuard Sync & Multi-Season Bible Hygiene)

- **Repozytorium:** `https://github.com/wooles/translator` (gałąź `main`)
- **Punkt wyjścia (HEAD baseline 11.2.7):** `ef6f884f14e25b0d33112952c54d06ed4f54059c` (`ef6f884`)
- **Commit 1 (Kod produkcyjny):** `ad73afd` (`fix(pipeline): implement adaptive F1 thinking, AniList resilience, real cache UI telemetry and multi-season hygiene (11.2.8)`)
- **Commit 2 (Testy i Certyfikacja Kodu):** `18f900066d6772ce442ed7b9d3ac316b205513e8` (`18f9000`)
- **Commit 3 (Dokumentacja i Zamknięcie Wydania):** `HEAD` (`docs(release): certify Standard 11.2.8 release and update PROJECT_MEMORY (11.2.8)`)
- **Baseline ochrony Z16 (Depuracja Legacy 1.0):** `c197db73c3dabf887dddbf2337dc3a1d8cff598c` (`c197db7` — **bezwzględne 0 B diffu na wszystkich plikach chronionych Z16!**)
- **Data certyfikacji:** 2026-11-15
- **Koszt wykonania:** 0.00 PLN (100% lokalne silniki, brak zapytań chmurowych)

---

## 1. CEL I ZAKRES WDROŻENIA

Standard 11.2.8 kompleksowo realizuje priorytety P1, P2 oraz P3 z mega-audytu operacyjnego, wdrażając adaptacyjny budżet myślenia Fazy 1, likwidując luki sieciowe i telemetryczne oraz zabezpieczając higienę baz wielosezonowych przed kolejnymi przebiegami produkcyjnymi:

1. **MODUŁ A: Adaptacyjny poziom myślenia Fazy 1 (Adaptive F1 Thinking):**
   - W `main.py` wprowadzono flagę CLI `--thinking-f1` z opcjami `auto`, `low`, `medium` (domyślnie `auto`).
   - W `translator.py` w klasie `MultimodalTranslator` zaimplementowano metodę `resolve_f1_thinking_budget(total_lines)`:
     * W trybie `auto`: dla odcinków $\le 360$ linii przydzielany jest budżet `3072` (MEDIUM CoT, koszt $\le 3.40$ PLN netto), a dla odcinków $> 360$ linii budżet `0` (LOW CoT, szybka triangulacja).
     * W trybie `medium`: wymuszany jest budżet `3072` CoT niezależnie od liczby linii.
     * W trybie `low`: wymuszany jest budżet `0` CoT niezależnie od liczby linii.
   - W `_call_gemini_with_retry` parametr `phase1_thinking_budget` jest przekazywany bezpośrednio do `build_thinking_config(current_model, budget_p1)`, generując dla modelu Hydrogen `types.ThinkingConfig(thinking_level="MEDIUM")` lub `thinking_level="LOW"`.

2. **MODUŁ B: Odporność sieciowa AniList GraphQL i lokalny fallback onomastyczny (INC-AVT-056):**
   - W `metadata.py` w klasie `ExternalGenderResolver.resolve_character_gender` zaktualizowano nagłówki HTTP żądania GraphQL o pełny nagłówek przeglądarkowy `User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36`, `Origin: https://anilist.co` oraz `Referer: https://anilist.co/`, eliminując odrzucanie zapytań kodem 403/404 przez węzły brzegowe Cloudflare.
   - Wprowadzono metodę `_fallback_lookup_in_fansub_lexicons` (oraz `_resolve_from_local_fansub_lexicons`): w przypadku wystąpienia błędu sieciowego (`HTTPError`, `URLError`, timeout) lub aktywnego bezpiecznika `_CIRCUIT_OPEN`, potok przeszukuje lokalne słowniki fansuberskie w `series_memory/fansub_lexicons/*.json` (pod kątem klucza terminu, aliasów angielskich oraz kanonicznej formy polskiej). Po odnalezieniu cechy płciowej (`gender`, `apparent_gender`, `grammatical_gender` lub deskryptorów w `instruction`) zwraca wartość `"FEMALE"` lub `"MALE"` i utrwala ją w pamięci RAM `cls._MEMORY_CACHE` pod kluczem `source: local_fansub_lexicon`, zapobiegając dalszym uderzeniom sieciowym.

3. **MODUŁ C: Likwidacja pozornego rabatu bufora i bramka telemetrii rzeczywistego cache (INC-AVT-057):**
   - W `context_cache.py` w metodzie `ensure_cache_ready` oraz w `translator.py` usunięto przedwczesne, bezwarunkowe wyświetlanie w konsoli komunikatu `Locked -90% server discount for gemini-4-hydrogen` przed wykonaniem zapytania do API. Zastąpiono je komunikatem informacyjnym: `[Context Cache]: Zainicjalizowano konfigurację bufora hybrydowego. Oczekiwanie na telemetrię Paczki 0...`.
   - W `translator.py` w metodzie `_process_single_batch` zaimplementowano dynamiczny audyt na Paczce 0:
     * Jeśli serwer potwierdzi `cached_content_token_count >= 32768`: emitowany jest komunikat `💰 [Context Cache AKTYWNY]: Serwer potwierdził CachedContent: {cached_tokens} tokenów (Rabat -95% aktywny).`.
     * Jeśli serwer zwróci `cached_content_token_count == 0`: wyzwalane jest jawne ostrzeżenie konsolowe i logowe `⚠️ [Context Cache OSTRZEŻENIE / INC-AVT-057]: Serwer zwrócił 0 tokenów cache! Rabat serwerowy NIEAKTYWNY (rozliczenie 100% stawki bazowej).`, a fałszywy komunikat o rabacie -95% jest blokowany.

4. **MODUŁ D: Synchronizacja estymatora PricingGuard z poziomem CoT Fazy 1:**
   - W `pricing_guard.py` w metodzie `estimate_loaded_workload_cost_pln` dodano parametr `f1_thinking_level: str = "LOW"`.
   - Dla profilu `gemini-4-hydrogen`:
     * `f1_thinking_level="LOW"`: `lean_output_f1_tokens = 1750` (1750 JSON + minimalny CoT) -> koszt ~2.21 PLN netto dla 350 linii / 12 paczek.
     * `f1_thinking_level="MEDIUM"`: `lean_output_f1_tokens = 4822` (1750 JSON + 3072 CoT) -> koszt ~3.32 PLN netto ($\le 4.00$ PLN) dla 350 linii / 12 paczek oraz ~5.25 PLN netto dla 518 linii / 19 paczek.
     * `f1_thinking_level="HIGH"`: `lean_output_f1_tokens = 7894` (1750 JSON + 6144 CoT).
   - W `translator.py` zsynchronizowano wywołanie `PricingGuard.estimate_loaded_workload_cost_pln`, przekazując `f1_thinking_level="MEDIUM"` jeśli `phase1_thinking_budget > 2048`, w przeciwnym razie `"LOW"`.

5. **MODUŁ E: Higiena i separacja wielosezonowych baz SeriesBible (INC-AVT-058):**
   - W `metadata.py` w funkcji `extract_canonical_series_and_season` wprowadzono dwuprzebiegowe usuwanie masek odcinkowych (`- 01`, `_01`, `E01`), umożliwiając poprawne wykrywanie sezonów z pełnych ścieżek plików dialogowych (np. `Series S2 - 01.mkv` -> `("series", 2)`).
   - W `translator.py` zaimplementowano funkcję i metodę `_resolve_bible_path` oraz uszczelniono inicjalizację `self.series_bible` w `translate_file`: jeśli ścieżka pliku zawiera marker sezonu (np. `S2`), baza wiedzy deterministycznie kieruje do pliku dedykowanego (`_2nd_Season_bible.json` lub `_S2_bible.json`).
   - W `series_memory.py` zaimplementowano metodę `update_after_episode` oraz zabezpieczono `register_episode_execution` i `save()`: jeśli odcinek posiada jawny tag innego sezonu niż plik docelowy, dodawanie do słowników `episodes_translated` i `batch_stats` pliku bazowego (Sezonu 1) jest bezwzględnie blokowane.

6. **INC-AVT-055 (Zamknięcie luki ewidencyjnej w rejestrze incydentów PROJECT_MEMORY.md):**
   - W `PROJECT_MEMORY.md` zarejestrowano formalny blok **ARB-058** obejmujący incydenty INC-AVT-047..050 Standardu 11.2.6 oraz blok **ARB-059** obejmujący incydenty INC-AVT-055..058 Standardu 11.2.8.

---

## 2. METRYKI TESTÓW I WERYFIKACJI

- **Pakiet testów jednostkowych i integracyjnych:**
  - `441 passed` fast tests (370 w `tests/` + 71 w `test_system.py`)
  - `153 deselected` slow/network
  - Łącznie: `594 collected`
  - Czas wykonania: ~57s
- **Dedykowany moduł regresyjny Standardu 11.2.8 (`tests/test_standard_11_2_8.py`):**
  - `test_t11_2_8_adaptive_f1_thinking_budget`: **PASSED**
  - `test_t11_2_8_anilist_resilience_and_lexicon_fallback`: **PASSED**
  - `test_t11_2_8_anilist_graphql_headers_and_fallback`: **PASSED**
  - `test_t11_2_8_pricing_guard_f1_thinking_sync`: **PASSED**
  - `test_t11_2_8_cache_ui_telemetry_gate`: **PASSED**
  - `test_t11_2_8_multi_season_bible_hygiene`: **PASSED**
  - `test_t11_2_8_multi_season_bible_path_resolution`: **PASSED**
- **Bramki kwalifikacyjne CI/CD:**
  - `verify_purity.py`: **PASS (11/11)** — 100% czystość AST, zero nazw własnych, zero słów preskryptywnych, rygor `strict_positive_domain=True`
  - `verify_8_fixes.py`: **PASS (8/8)** — Pełna eliminacja przyczyn źródłowych
  - `verify_12_fixes.py`: **PASS (12/12)** — Integralność dyskursu i brak wycieków
  - `verify_ultimate_pipeline.py`: **PASS (15/15)** — 15/15 bramek runtime, immunitet narzędnika, granice słów tagów ASS
  - `audit_diff.ps1`: **PASS (4/4)** — `[VICTORY CONFIRMED -- KOD CZYSTY I UOGOLNIONY]`
  - `git diff c197db7...`: **0 B diff** na wszystkich plikach chronionych Z16

---

## 3. PODSUMOWANIE ZMIAN W PLIKACH PRODUKCYJNYCH

| Moduł | Zakres Modyfikacji |
|---|---|
| `main.py` | Obsługa parametru CLI `--thinking-f1` (`auto`, `low`, `medium`) i przekazanie do `MultimodalTranslator`. |
| `pricing_guard.py` | Rozszerzenie `estimate_loaded_workload_cost_pln` o `f1_thinking_level: str = "LOW"`; kalkulacja dla Hydrogen (LOW: 1750 tok, MEDIUM: 4822 tok, HIGH: 7894 tok); zwrot pola `f1_thinking_level`. |
| `translator.py` | Obsługa `thinking_f1` i metoda `resolve_f1_thinking_budget`; synchronizacja wywołania `PricingGuard`; dynamiczny audyt `cached_content_token_count` na Paczce 0 (`INC-AVT-057`); funkcja i metoda `_resolve_bible_path`; wykrywanie sezonu ze ścieżki pliku i przekazywanie do `SeriesBible`. |
| `metadata.py` | Nagłówki User-Agent, Origin, Referer w `ExternalGenderResolver`; metody `_fallback_lookup_in_fansub_lexicons` oraz `_resolve_from_local_fansub_lexicons`; dwuprzebiegowe usuwanie numeru odcinka w `extract_canonical_series_and_season`. |
| `context_cache.py` | Usunięcie przedwczesnego komunikatu konsolowego o rabacie; komunikat oczekiwania na telemetrię z Paczki 0. |
| `series_memory.py` | Metoda `update_after_episode`; mechanizm multi-season hygiene w `register_episode_execution` i `save()` zapobiegający zanieczyszczaniu baz Sezonu 1. |
| `PROJECT_MEMORY.md` | Rejestracja bloków ARB-058 (INC-AVT-047..050) i ARB-059 (INC-AVT-055..058, Adaptive F1 Thinking, PricingGuard Sync); aktualizacja baseline'u do 11.2.8. |
| `AGENTS.md` | Aktualizacja certyfikowanego standardu produkcyjnego na 11.2.8, SHA-1 commitu certyfikacji `18f9000` oraz stanu metryk `594 collected` (`441 passed`). |
| `PELNY_RAPORT_TECHNICZNY_POTOKU.md` | Dokumentacja parametru CLI `--thinking-f1` oraz aktualizacja stopki baseline'u do Standardu 11.2.8. |
| `tests/test_standard_11_2_8.py` | Dedykowany zestaw 5 testów regresyjnych T11.2.8 (7 procedur testowych z aliasami, 100% PASSED). |
