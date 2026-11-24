# 🏛️ RAPORT WDROŻENIOWY — STANDARD 11.2.24 (Z16-AMENDMENT #15 / DEF-04)
## Certyfikacja Standardu 11.2.24 (Dependent Interrogative Comma SSOT Guard across series_memory and avt_linter)

- **Repozytorium:** `https://github.com/wooles/translator` (gałąź `main`)
- **Punkt wyjścia (HEAD baseline 11.2.23a):** `e595b5274d260654d1a83268b86691642852b9bc` (`e595b52`)
- **Commit 1 (Kod produkcyjny):** `0910539` (`fix(linter): preserve mandatory comma before 'czy' in dependent interrogative clauses via SSOT helper across series_memory and avt_linter (Z16-amendment #15 / DEF-04, 11.2.24)`)
- **Commit 2 (Testy i Certyfikacja Kodu):** `6b500a2` (`test(linter): verify DEF-04 dependent interrogative comma guard across Test A/B/C/D and all 3 execution points (11.2.24)`)
- **Commit 3 (Dokumentacja i Zamknięcie Wydania):** `HEAD` (`docs(release): certify Standard 11.2.24 (Z16-amendment #15) — DEF-04 dependent interrogative comma guard across all 3 SSOT points`)
- **Autoryzacja Z16-amendment #15:** Wyłącznie zlokalizowana edycja 1 pliku chronionego Z16 (`avt_linter.py` — linie 18–24, 1000, 11417).
- **Baseline ochrony Z16 (Depuracja Legacy 1.0):** `c197db73c3dabf887dddbf2337dc3a1d8cff598c` (`c197db7` — **bezwzględne 0 B diffu na wszystkich 28 pozostałych plikach chronionych Z16!**)
- **Ochrona plików nieobjętych Standardem 11.2.24:** `translator.py`, `scene_discourse.py`, `pipeline_logger.py` oraz `series_memory/*.json` zachowują dokładne 0 B diffu względem `e595b52`.
- **Data certyfikacji:** 2026-11-24
- **Koszt wykonania:** 0.00 PLN (100% lokalne silniki deterministyczne, brak zapytań chmurowych)

---

## 1. CEL I ZAKRES WDROŻENIA

Standard 11.2.24 stanowi całościową, bezwyjątkową eliminację przyczyny źródłowej defektu **`DEF-04` (Filar LX Interpunkcja)** — błędnego usuwania obowiązkowego przecinka w zdaniach podrzędnych pytajnych zależnych przed spójnikiem `czy (bez|nie|tak)`:

1. **Przyczyna źródłowa `DEF-04`:**
   - Wcześniejsza uproszczona reguła lintera traktowała każde wystąpienie `\b([A-Za-ząćęłńóśźż0-9\-]+),\s+czy\s+(bez|nie|tak)\b` jako potoczną alternatywę rozłączną (np. *w kapciach czy bez*), chroniąc jedynie inicjalny wołacz wielką literą na początku zdania (Standard 9.4 2B.10).
   - W rezultacie zdania podrzędne pytajne zależne (np. *pytała, czy nie chciałabym tu zostać*, *nie wiem, czy nie lepiej zostać*, *sprawdź, czy nie zamknęli bramy*) traciły normatywny, obowiązkowy przecinek wprowadzający zdanie podrzędne.
   - Trzy niezależne punkty wykonania potoku (`series_memory.py:TYPO_NORMALIZATIONS`, `avt_linter.py:AVTLinter.FIXED_REPLACEMENTS` oraz `avt_linter.py:EpisodeQualityGate.audit_and_fix_entire_episode`) posiadały zdublowane, niespójne implementacje.

2. **Architektura Czystej Domeny Pozytywnej i Jedna Funkcja SSOT:**
   - W module `series_memory.py` zdefiniowano jedną kanoniczną funkcję SSOT `strip_binary_alt_comma_before_czy(m: re.Match) -> str` oraz pomocnicze niemutowalne kolekcje tokenów:
     - `_INTERROGATIVE_EPISTEMIC_PREFIXES`: zbiór prefiksów czasowników pytajnych i epistemicznych (*pyta*, *zapyta*, *spyt*, *powiedz*, *wiedz*, *sprawdz*, *zastanaw*, *ciekaw*, *wątp*, *zgadnij*, *zobacz*, etc.).
     - `_INTERROGATIVE_EPISTEMIC_EXACT`: formy fleksyjne nieregularne (*wiem*, *wiesz*, *powiem*, *zgadnę*, *zgadł*, etc.).
     - `_ALLOWED_CZY_BRIDGE_WORDS`: dozwolone krótkie słowa pomostowe wtrącone (zaimki, partykuły, przysłówki, fraza *nie mam pojęcia*, maks. 3 słowa).
     - `_is_interrogative_epistemic_verb(tok)`: precyzyjny selektor wykluczający niepytajne formy czasownika *zgadzać się* (*zgadzam się, czy nie?* -> alternatywa rozłączna bez przecinka).
   - Funkcja SSOT zachowuje przecinek (`m.group(0)`) w dwóch ściśle zdefiniowanych przypadkach pozytywnych:
     - Wołacz inicjalny / początek kwestii (Standard 9.4 2B.10).
     - Zdanie podrzędne pytajne zależne po czasowniku/frazie epistemicznej (bezpośrednio lub przez dozwolony mostek zaimkowy).
   - Poza tymi przypadkami (czysta frazowa alternatywa rozłączna bez czasownika pytajnego) zbędny przecinek jest usuwany (`f"{m.group(1)} czy {m.group(2)}"`).

3. **Podpięcie SSOT we wszystkich 3 punktach potoku:**
   - `series_memory.py:TYPO_NORMALIZATIONS`: podpięcie `strip_binary_alt_comma_before_czy` zamiast lambdy.
   - `avt_linter.py:AVTLinter.FIXED_REPLACEMENTS`: import i bezpośrednie użycie funkcji SSOT w regule Filaru LX.
   - `avt_linter.py:EpisodeQualityGate.audit_and_fix_entire_episode`: eliminacja lokalnej funkcji `_strip_alt_comma` i delegacja do funkcji SSOT.

4. **Świadome wyłączenia poza zakres Standardu 11.2.24:**
   - `OBS-04` (`pipeline_logger.py` — rejestracja ponowień `log_retry`): świadomie odłożony do Standardu `11.2.25`.
   - `OBS-03` (`pricing_guard.py:379`): plik chroniony Z16 — poza zakresem.
   - `translator.py`, `scene_discourse.py`, `series_memory/*.json`: bez jakichkolwiek modyfikacji (0 B diffu).

---

## 2. METRYKI TESTÓW I CERTYFIKACJA CI/CD

- **Nowy pakiet testów regresyjnych:**
  - `tests/test_avt_linter.py::test_standard_11_2_24_def04_dependent_interrogative_comma_ssot`: **25/25 PASSED (100%)**
    - **Grupa A (11 przypadków):** Zdania podrzędne pytajne po czasownikach epistemicznych — przecinek zachowany.
    - **Grupa B (3 przypadki):** Czysta alternatywa rozłączna — przecinek usunięty.
    - **Grupa C (7 przypadków):** Przypadki graniczne (*nie mam pojęcia*, *powiedz mi szczerze*, *zapytała go cicho*, wykluczenie *zgadzam/zgadza się*, dopełnienia po *zobacz*).
    - **Grupa D (4 przypadki):** Złożone zdania z podwójnym *czy* — selektywna ochrona pierwszego wystąpienia pytajnego i usunięcie przecinka w drugim wystąpieniu alternatywnym.
  - Weryfikacja obejmuje symultanicznie wszystkie 3 punkty wykonania potoku: `sanitize_lexical_text`, `AVTLinter.lint_and_fix_line(strict_positive_domain=False)` oraz `EpisodeQualityGate.audit_and_fix_entire_episode`.

- **Łączne metryki pakietu testów:**
  - `tests/`: **445 passed** (100% sukcesu, 0 failed)
  - `test_system.py`: **70 passed, 154 deselected** (0 failed)
  - Łącznie: **515 passed** fast tests

- **4 bramki kwalifikacyjne CI/CD:**
  - `verify_purity.py`: **11/11 PASS** (100% czysty kod AST, zero instancji onomastycznych, zero preskryptywności)
  - `verify_8_fixes.py`: **8/8 PASS**
  - `verify_12_fixes.py`: **12/12 PASS**
  - `verify_ultimate_pipeline.py`: **15/15 PASS**

- **Audyt śledczy diffu:**
  - `audit_diff.ps1 -BaseRef "e595b52"`: **WERDYKT: [VICTORY CONFIRMED -- KOD CZYSTY I UOGOLNIONY]**

- **Weryfikacja integralności Z16:**
  - Pozostałe 28 plików chronionych Z16 względem `c197db7`: **0 B DIFF (BEZWZGLĘDNA CZYSTOŚĆ)**
  - Pliki `translator.py`, `scene_discourse.py`, `pipeline_logger.py` względem `e595b52`: **0 B DIFF**
  - Zakres zmian w `avt_linter.py`: ściśle ograniczony do autoryzowanego Z16-amendment #15 (+4 / -17 linii).
