# E2E Test Infra: translator (Standard 3.0)

## Test Philosophy
- Requirement-driven, opaque-box, and regression-shielded verification.
- Zero-Cosmetic Enforcement: Every defect fix must be validated at the Python code level, verified API/cache fallback, and relational slot independence.

## Feature Inventory
| # | Feature | Source | Tier 1 | Tier 2 | Tier 3 |
|---|---------|--------|:------:|:------:|:------:|
| 1 | R1: Zero-Cosmetic Protocol | ORIGINAL_REQUEST § R1 | 5 | 5 | ✓ |
| 2 | R2: 4-Stopniowy Audyt Fabryki Błędów | ORIGINAL_REQUEST § R2 | 5 | 5 | ✓ |
| 3 | R3.1: Fallback Normalizacyjny AniList | ORIGINAL_REQUEST § R3.1 | 5 | 5 | ✓ |
| 4 | R3.2: Eliminacja Odwróconej Inferencji | ORIGINAL_REQUEST § R3.2 | 5 | 5 | ✓ |
| 5 | R3.3: Priorytet P0 Zweryfikowanej Płci | ORIGINAL_REQUEST § R3.3 | 5 | 5 | ✓ |
| 6 | R3.4: Sanacja Bazy Hyouken S2 | ORIGINAL_REQUEST § R3.4 | 5 | 5 | ✓ |
| 7 | R4: Certyfikat Eliminacji Źródłowej | ORIGINAL_REQUEST § R4 | 5 | 5 | ✓ |
| 8 | R5: Test 156 i Zestaw 156/156 PASSED | ORIGINAL_REQUEST § R5 | 5 | 5 | ✓ |

## Test Architecture
- Test Runner: `python test_system.py`
- Pass/Fail Semantics: 156/156 PASSED (100.0%), exit code 0.
- Test 156 (`test_hyouken_s2_root_cause_anilist_fallback_and_addressee_guard`):
  1. Weryfikacja działania `strip_season_suffix()` dla `S2`, `Season 2`, `Part 2`, `Cour 2`, `2nd Season`.
  2. Weryfikacja zapytania `fetch_anilist_metadata("Hyouken no Majutsushi ga Sekai wo Suberu S2")` zwracającego dane serii macierzystej ze zweryfikowaną płcią Ray White (`has_verified_gender = True`).
  3. Weryfikacja odporności `update_from_episode_profile()` na syntetycznym obiekcie `SeriesBible`: relacja `Ray White -> Amelia Rose [KOBIETA (Adresat)... byłaś / zrobiłaś]` nie nadaje Rayowi cech kobiety.
  4. Weryfikacja czystości `Hyouken_no_Majutsushi_ga_Sekai_wo_Suberu_S2_bible.json`: Ray White (MALE), Ariane Olgren (FEMALE), Rebecca Bradley (FEMALE), Lydia Ainsworth (FEMALE), Stella White (FEMALE / siostra).

## Coverage Thresholds
- Unit & Integration Tests: 156 testów w `test_system.py`.
- Regression: Zero failures across all existing 155 tests + Test 156 (156/156 PASSED).
