# 🏛️ RAPORT WDROŻENIOWY — STANDARD 11.2.5
## Certyfikacja Standardu 11.2.5 (External Ontological Grounding, Impersonal Dispatch Guard, Eponym Identity Protection & Collective Role Sanitization Baseline)

- **Repozytorium:** `https://github.com/wooles/translator` (gałąź `main`)
- **Punkt wyjścia (HEAD baseline 11.2.3):** `0132db0529142904190ff9e1ca4b58511b056541` (`0132db0`)
- **Commit 1 (Kod produkcyjny):** `dcbbe50` (`feat(pipeline): external gender resolver, impersonal radio dispatch, eponym guard and collective role sanitization (11.2.5)`)
- **Commit 2 (Testy i Certyfikacja Kodu):** `37029a4c9713fbe376699512e9100f5599ce7e0a` (`37029a4`)
- **Commit 3 (Dokumentacja i Zamknięcie Wydania):** `HEAD`
- **Baseline ochrony Z16 (Depuracja Legacy 1.0):** `c197db73c3dabf887dddbf2337dc3a1d8cff598c` (`c197db7` — **bezwzględne 0 B diffu na wszystkich plikach chronionych Z16!**)
- **Data certyfikacji:** 2026-11-14
- **Koszt wykonania:** 0.00 PLN (100% lokalne silniki, brak zapytań chmurowych)

---

## 1. CEL I ZAKRES WDROŻENIA

Standard 11.2.5 rozwiązuje 4 kluczowe problemy telemetryczne, ontologiczne i semantyczne potoku AVT:

1. **INC-AVT-043 (Zewnętrzne Ugruntowanie Ontologiczne AniList GraphQL & In-Memory Reconcile):**
   - W `metadata.py` wdrożono klasę `ExternalGenderResolver`, która odpytuje endpoint AniList Character GraphQL z rygorem `Franchise Matching Guard` (porównanie znormalizowanego sluga franczyzy z tytułami romaji i english powiązanych mediów).
   - Zaimplementowano bufor dyskowy `series_memory/.external_character_cache.json` z atomowym zapisem do pliku tymczasowego `.tmp` i zamianą, eliminując ponowne zapytania sieciowe.
   - Wprowadzono bezpiecznik awaryjny `Circuit Breaker` (3 kolejne błędy otwierają bezpiecznik, blokując dalsze próby) z metodą `reset_circuit_breaker()`, podpiętą pod `reset_anilist_circuit_breaker()`.
   - W `series_memory.py` rozszerzono `_reconcile_registry_gender_in_memory` o skanowanie `dramatic_summary`, `female_only_scene`, pełną odmianę polskich tytułów przez przypadki, dziedziczenie płci wariantów `-like`/`-clone` oraz fallback do `ExternalGenderResolver` dla postaci `UNKNOWN`.

2. **INC-AVT-044 (Ochrona Łączności Radiowej i Meldunków Wojskowych — Radio & Dispatch Invariance):**
   - W `translator.py` wprowadzono regułę *Radio & Dispatch Invariance* do promptów systemowych Fazy 1 i Fazy 2 (DialogVerifier), nakazującą tłumaczenie meldunków odbioru (`"Roger."`, `"Copy that."`, `"Understood."`, `"Acknowledged."`, `"Wilco."`) w formie bezosobowej (`"Przyjęto."`, `"Zrozumiano."`) lub żeńskiej (`"Przyjęłam."`, `"Zrozumiałam."`).
   - W Fazie 1 (`_process_single_batch`) oraz Fazie 2 (`translate_subtitles`) dodano deterministyczną podmianę fałszywych form męskich (`"Przyjąłem."` -> `"Przyjęto."`/`"Przyjęłam."`) w przypadku mówców niepotwierdzonych męsko.

3. **INC-AVT-045 (Ochrona Tożsamości Eponimów i Odblokowanie Paradygmatów TOPONYM):**
   - W `series_memory.py` w funkcji `_compute_toponym_declension` dodano strażnika eponimów: jeśli sprawdzany leksem znajduje się w zbiorze kanonicznych imion męskich (`CANONICAL_MALE_NAMES`) lub spółgłoskowych żeńskich (`FOREIGN_FEMALE_CONSONANT_NAMES`), funkcja natychmiast zwraca `None` (Identity Pass-Through), zabezpieczając imiona postaci przed zniekształceniem jako toponimy.
   - W `SeriesBible.get_declension_paradigm` odblokowano kategorię `EntityCategory.TOPONYM` z przeszukiwaniem słowników `places` i `declensions` oraz fallbackiem do `DeclensionParadigm.create_for_name`.

4. **INC-AVT-046 (Sanitacja Ról Zbiorowych i Orszaku — SECONDARY_COLLECTIVE_ROLES):**
   - W `series_memory.py` zdefiniowano zamrożony zbiór `SECONDARY_COLLECTIVE_ROLES` (`torimaki`, `retinue`, `followers`, `servants`, `attendants`, `guards`, `soldiers`, `squad`, `escort`, `unit`, `crowd`).
   - W funkcjach `populate_secondary_actor_tags` oraz w pętli relacji `clean_p` zablokowano fałszywą feminizację i maskulinizację orszaku/straży, wymuszając dla bytów zbiorowych stan `gender: "UNKNOWN"`, `priority: "P2"`, `has_verified_gender: False`.

---

## 2. METRYKI TESTÓW I WERYFIKACJI

- **Pakiet testów jednostkowych i integracyjnych:**
  - `432 passed` fast tests (361 w `tests/` + 71 w `test_system.py`)
  - `153 deselected` slow/network
  - Łącznie: `585 collected`
  - Czas wykonania: ~50s
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

1. `dcbbe50`: `feat(pipeline): external gender resolver, impersonal radio dispatch, eponym guard and collective role sanitization (11.2.5)`
2. `37029a4c9713fbe376699512e9100f5599ce7e0a` (`37029a4`): `test(pipeline): add regression tests for external gender resolver, radio dispatches, and eponym routing` — **NOWY COMMIT CERTYFIKACJI KODU**
3. `HEAD`: `docs(release): certify Standard 11.2.5 baseline in AGENTS.md, PROJECT_MEMORY.md, and implementation report`
