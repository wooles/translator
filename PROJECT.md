# Project: True Root-Cause & Anti-Cosmetic Mandate (Standard 3.0) + INC-AVT-003 Resolution

## Architecture
Potok AVT (Standard 3.0) składa się z 5 warstw:
1. **Warstwa 1 (Profiler / Schematy Wejściowe / API Metadata):** `metadata.py` - odpytywanie AniList GraphQL, normalizacja tytułów serii, odcinanie sufiksów sezonowych (`S2`, `Season 2`, `Part 2`, `Cour 2`, `2nd Season`), oznaczanie `has_verified_gender = True` z kanonu.
2. **Warstwa 2 (Baza Wiedzy / SeriesMemory):** `series_memory.py` - pamięć serii (`SeriesBible`), separacja ról w relacjach `A -> B` (mówca `idx = 0` vs adresat `idx = 1`), eliminacja odwróconej inferencji, priorytet P0 dla zweryfikowanej płci z AniList nad heurystykami tekstowymi.
3. **Warstwa 3 (Kanon Mangowy & Prompty Filarów):** `AGENTS.md` (Zasada 0, Zasada 1 Zero-Cosmetic Protocol, Sekcja 20 Hierarchiczny Protokół 4-Agentowy), `PROJECT_MEMORY.md` (telemetria i rejestr architektury).
4. **Warstwa 4 (Linter / Bramka Jakości Offline 0.00 PLN):** `avt_linter.py` - zakaz doraźnych regexów maskujących błędy silnika.
5. **Warstwa 5 (Testy Regresyjne CI/CD):** `test_system.py` - Test 156 weryfikujący fallback sezonowy AniList, odporność na skażenie mówcy przez tag `[KOBIETA (Adresat)]` oraz czystość bazy `Hyouken S2` (156/156 PASSED).

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | R1: Zero-Cosmetic Protocol | Kodyfikacja bezwzględnego zakazu 3 protez (ręczna edycja json, pojedynczy regex lintera, ręczna edycja .ass) i weto Agenta 4 w AGENTS.md i PROJECT_MEMORY.md | M1 | ORIGINAL_REQUEST § R1 |
| 2 | R2: 4-Stopniowy Audyt Fabryki Błędów | Procedura dla Agenta 3 i 4: 1. Identyfikacja fabryki, 2. Audyt asymetrii API/cache, 3. Test generalizacji, 4. Fizyczna reprezentacja w Pythonie | M1 | ORIGINAL_REQUEST § R2 |
| 3 | R4: Certyfikat Eliminacji Źródłowej | Aktualizacja formatu Executive Dossier o obowiązkową sekcję `[CERTYFIKAT ELIMINACJI ŹRÓDŁOWEJ]` w AGENTS.md | M1 | ORIGINAL_REQUEST § R4 |
| 4 | R3.1: Fallback Normalizacyjny w metadata.py | Implementacja `strip_season_suffix()` i fallbacku w `fetch_anilist_metadata()` odcinającego `S2`, `Season 2`, `Part 2`, `Cour 2`, `2nd Season` przy 404 | M2 | ORIGINAL_REQUEST § R3.1 |
| 5 | R3.2: Eliminacja Odwróconej Inferencji w series_memory.py | Separacja ról w `update_from_episode_profile()`: zakaz przypisywania tagu `[... (Adresat)]` i form 2. os. lp. (`byłaś`, `zrobiłaś`) do mówcy (`idx = 0`), usunięcie fałszywego męskiego wymuszenia w relacjach hierarchicznych | M2 | ORIGINAL_REQUEST § R3.2 |
| 6 | R3.3: Priorytet P0 dla Zweryfikowanej Płci AniList | Wymuszenie priorytetu P0 dla `has_verified_gender = True` w `series_memory.py` i `translator.py` nad heurystykami relacji tekstowych | M2 | ORIGINAL_REQUEST § R3.3 |
| 7 | R3.4: Sanacja Bazy Hyouken S2 Bible | Oczyszczenie `Hyouken_no_Majutsushi_ga_Sekai_wo_Suberu_S2_bible.json` (Ray White -> MALE, Ariane -> FEMALE, Rebecca -> FEMALE, Lydia -> FEMALE, Stella White -> FEMALE / młodsza siostra) | M3 | ORIGINAL_REQUEST § R3.4 |
| 8 | R5.1: Test 156 w test_system.py | Atomowy test regresyjny (Test 156) weryfikujący fallback AniList, odporność `update_from_episode_profile()` na profilu syntetycznym i brak skażenia | M4 | ORIGINAL_REQUEST § R5.1 |
| 9 | R5.2: Pełny Zestaw Testów CI/CD 156/156 | Wykonanie pełnego zestawu testów ze statusem 156/156 PASSED (100.0%) | M4 | ORIGINAL_REQUEST § R5.2 |
| 10 | R5.3: Synchronizacja Git | Wysłanie zmian do repozytorium GitHub (`git status`, `git push`) | M4 | ORIGINAL_REQUEST § R5.3 |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| 1 | M1: Kodyfikacja Zasad i Szablonu Dossier | AGENTS.md (Zasada 0, Zasada 1, Sekcja 20) oraz PROJECT_MEMORY.md (ARB-005..007, INC-AVT-003, telemetria) | none | DONE |
| 2 | M2: Naprawa Silnika Algorytmicznego | metadata.py (strip_season_suffix, fetch_anilist_metadata fallback), series_memory.py (update_from_episode_profile, P0 verified gender priority), translator.py | none | DONE |
| 3 | M3: Sanacja Bazy Wiedzy Hyouken S2 | Hyouken_no_Majutsushi_ga_Sekai_wo_Suberu_S2_bible.json (korekta 5 postaci, usunięcie skażonych tagów relacji i błędnych deklinacji) | M2 | DONE |
| 4 | M4: Test Regresyjny 156, CI/CD 156/156 i Git Sync | test_system.py (Test 156 + main runner), uruchomienie testów (156/156 PASSED), synchronizacja git | M1, M2, M3 | DONE |

## Interface Contracts
### metadata.py ↔ series_memory.py & translator.py
- `strip_season_suffix(title: str) -> Optional[str]`:
  Zwraca oczyszczony tytuł franczyzy nadrzędnej (np. `"Hyouken no Majutsushi ga Sekai wo Suberu"` dla `"Hyouken no Majutsushi ga Sekai wo Suberu S2"`), lub `None` jeśli tytuł nie zawiera sufiksu sezonowego.
- `fetch_anilist_metadata(title: str) -> Optional[Dict]`:
  Przy braku wyników lub błędzie 404 dla zapytania bazowego, sprawdza `strip_season_suffix(title)` i ponawia zapytanie.
  Zwraca listę postaci z polami `name`, `gender`, `has_verified_gender: bool`.
- `SeriesBible.update_from_episode_profile(characters: Dict[str, str])`:
  Dla kluczy relacyjnych `A -> B`:
  - `idx = 0` (mówca): całkowity zakaz dziedziczenia cech z tagu `[... (Adresat)]` oraz form czasownikowych 2. osoby lp. (`byłaś`, `zrobiłaś`).
  - `idx = 1` (adresat): dziedziczy cechy adresata.
  - Priorytet P0: jeśli postać posiada `has_verified_gender == True` (lub dane z AniList), relacje tekstowe nie mogą zmienić jej płci.

## Code Layout
- `AGENTS.md` - Kodeks Zasad Potoku AVT (Standard 3.0)
- `PROJECT_MEMORY.md` - Persistent architectural memory, incident log, arbitration register
- `metadata.py` - Metadata harvesting & AniList GraphQL client
- `series_memory.py` - Series memory & SeriesBible data structure
- `translator.py` - Core AVT translation engine & character registration
- `series_memory/Hyouken_no_Majutsushi_ga_Sekai_wo_Suberu_S2_bible.json` - Serialized knowledge base
- `test_system.py` - Comprehensive CI/CD test suite (Tests 1–156)
