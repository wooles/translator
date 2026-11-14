# 🏛️ RAPORT WDROŻENIOWY — HOTFIX 11.2.7
## Certyfikacja Hotfixu 11.2.7 (Real Server CachedContent >= 32k Threshold Enforcement, Phase 1 JSON Truncation Guard & Dynamic Prompt Compaction Baseline)

- **Repozytorium:** `https://github.com/wooles/translator` (gałąź `main`)
- **Punkt wyjścia (HEAD baseline 11.2.6):** `9e5c8e6d951a6cc5da24fef1f17930be882bb8c8` (`9e5c8e6`)
- **Commit 1 (Kod produkcyjny):** `e501090` (`fix(pipeline): enforce real server cache threshold >= 32k, lift phase 1 output token cap to 16k, and compact prompt metadata (11.2.7)`)
- **Commit 2 (Testy i Certyfikacja Kodu):** `e63204e4fffc3066ebcd7abe2eb89e5f882657df` (`e63204e`)
- **Commit 3 (Dokumentacja i Zamknięcie Wydania):** `HEAD`
- **Baseline ochrony Z16 (Depuracja Legacy 1.0):** `c197db73c3dabf887dddbf2337dc3a1d8cff598c` (`c197db7` — **bezwzględne 0 B diffu na wszystkich plikach chronionych Z16!**)
- **Data certyfikacji:** 2026-11-14
- **Koszt wykonania:** 0.00 PLN (100% lokalne silniki, brak zapytań chmurowych)

---

## 1. CEL I ZAKRES WDROŻENIA

Hotfix 11.2.7 rozwiązuje trzy luki empiryczne ujawnione podczas symulacji pełnego odcinka (518 linii / 19 paczek) z użyciem modelu `gemini-4-hydrogen`:

1. **INC-AVT-051 (Gwarancja przekroczenia progu 32 768 tokenów dla prawdziwego serwerowego CachedContent):**
   - W `translator.py` w `__init__` klasy `MultimodalTranslator` przełączono `lean=False` zarówno dla promptu systemowego Fazy 1 (`get_translation_system_prompt(keep_honorifics=keep_honorifics, lean=False)`), jak i dla Fazy 2 (`DialogueVerifier(..., lean=False)`).
   - Pełny kanon rzemiosła zwiększa rozmiar tekstu buforowanego z `~38k` znaków (`~12k` tokenów — odrzucane przez serwer Google jako `< 32 768` tokenów) do `~211k` znaków (`~53k–60k` tokenów `> 32 768` tokenów).
   - W `context_cache.py` w metodzie `ContextCacheManager.get_or_create_cache` dodano bezpiecznik progu: gdy klient posiada `caches.create`, jeśli `len(system_instruction) < 140000`, w `anchor_content` dołączany jest pełny kanon referencyjny z `rules.get_translation_system_prompt(keep_honorifics=True, lean=False)`. Dzięki temu wywołanie `client.caches.create` zawsze przekracza próg 32 768 tokenów i jest poprawnie akceptowane przez infrastrukturę Google z rabatem `-95%`.
   - Zachowano natychmiastowy zwrot `"__IMPLICIT_CACHE_95__"` dla klientów testowych bez `caches.create`, gwarantując 100% kompatybilności wstecznej.

2. **INC-AVT-052 (Usunięcie pułapki `max_output_tokens = 4096` i optymalizacja myślenia CoT Fazy 1):**
   - W `translator.py` w metodzie `_call_gemini_with_retry` podniesiono limit wyjściowy dla modelu `is_hydrogen` do bezpiecznego pułapu `gen_config_kwargs["max_output_tokens"] = 16384` (eliminacja obcinania odpowiedzi JSON w gęstych paczkach 30-liniowych, gdzie `thoughts + candidates > 4096`).
   - Do wytycznych promptu systemowego dodano regułę ekonomiki syntezy Fazy 1, instruującą model do przeprowadzania zwięzłej analizy w 2–3 krótkich zdaniach, co redukuje narzut tokenów myślenia w Fazie 1.

3. **INC-AVT-053 (Dynamiczna kompakcja metadanych promptu i deduplikacja cech akustycznych):**
   - W `_prepare_batch_prompt` wiersz parametrów planszy (`Parametry planszy: budżet {max_pl_chars} znaków...`) jest emitowany wyłącznie dla napisów ekranowych (`vtype["is_sign"]`) lub dla kwestii o wysokim tempie czytania (`cps > 14.5`), redukując zbędne powtórzenia dla normalnego dialogu.
   - W `_process_single_batch` przed wywołaniem `DialogueVerifier.verify_batch` zaimplementowano deduplikację `speaker_voice` i `prosody`: jeśli kolejna kwestia pochodzi od tego samego mówcy i cechy akustyczne są identyczne z już wyemitowanymi, w duplikacie ustawiane są wartości puste `""`, oszczędzając kolejne tokeny niebuforowane w Fazie 2.

4. **INC-AVT-054 (Kalibracja estymatora obciążenia roboczego `PricingGuard`):**
   - W `PricingGuard.estimate_loaded_workload_cost_pln` zaktualizowano `system_prompt_tokens = 55000` (pełny `CachedContent` po stawce `$0.075/1M`) oraz skalibrowano parametry wejściowe paczek z uwzględnieniem kompakcji i deduplikacji akustycznej (`batch_input_tokens = 7100`, `lean_output_f1_tokens = 1750`, `lean_output_f2_tokens = 1500`, `p2_input_tokens = 1800`), uzyskując:
     * 350 linii / 12 paczek: `~2.21 PLN netto` (rygor sufitu `<= 3.50 PLN`).
     * 518 linii / 19 paczek: `~3.50 PLN netto` (rygor sufitu `<= 3.80 PLN`).

---

## 2. METRYKI TESTÓW I WERYFIKACJI

- **Pakiet testów jednostkowych i integracyjnych:**
  - `434 passed` fast tests (363 w `tests/` + 71 w `test_system.py`)
  - `153 deselected` slow/network
  - Łącznie: `587 collected`
  - Czas wykonania: ~57s
- **Bramki kwalifikacyjne CI/CD:**
  - `verify_purity.py`: **PASS (11/11)** — 100% czystość AST, zero nazw własnych, zero słów preskryptywnych, rygor `strict_positive_domain=True`
  - `verify_8_fixes.py`: **PASS (8/8)** — Pełna eliminacja przyczyn źródłowych
  - `verify_12_fixes.py`: **PASS (12/12)** — Integralność dyskursu i brak wycieków
  - `verify_ultimate_pipeline.py`: **PASS (15/15)** — Niezmienniki runtime i architektury
  - `audit_diff.ps1`: **PASS (4/4)** — `WERDYKT: [VICTORY CONFIRMED -- KOD CZYSTY I UOGOLNIONY]`
- **Ochrona Z16:**
  - `git diff c197db73c3dabf887dddbf2337dc3a1d8cff598c -- test_system.py tests/archive/ avt_linter.py pytest.ini rules.py verifier.py verify_purity.py "series_memory/*_bible.json" series_memory/.onomastic_lexicon.json "series_memory/fansub_lexicons/*.json"`: **0 B diffu**.

---

## 3. SEKWENCJA COMMITÓW

1. `e501090`: `fix(pipeline): enforce real server cache threshold >= 32k, lift phase 1 output token cap to 16k, and compact prompt metadata (11.2.7)`
2. `e63204e4fffc3066ebcd7abe2eb89e5f882657df` (`e63204e`): `test(pipeline): add regression suite for real server cache threshold, output token limit, and prompt compaction (11.2.7)` — **NOWY COMMIT CERTYFIKACJI KODU**
3. `HEAD`: `docs(release): certify Standard 11.2.7 Real Server Cache Threshold, Phase 1 JSON Truncation Guard & Dynamic Prompt Compaction Baseline`
