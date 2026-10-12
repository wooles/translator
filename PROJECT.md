# Project: INC-AVT-004 Root Cause Engine Remediation (Standard 3.0)

## Architecture
The AVT Pipeline operates across 5 defensive layers:
- **Warstwa 1 (Profiler / Kontrakt Pydantic & WhisperDisambiguator)**:
  `whisper_disambiguator.py` provides acoustic & lexical disambiguation tags (`addressee_number`: `PLURAL`, `DUAL`, `SINGULAR`; `speaker_gender`).
- **Warstwa 2 (Baza Wiedzy / SeriesMemory & SeriesBible)**:
  `series_memory.py` maintains canon knowledge (`SeriesBible`), character registry, gender resolution (`get_character_gender`, `resolve_actor_gender`), toponym sanitization (`sanitize_toponymic_origin_and_companionship`), and prevents audio contamination of character entities.
- **Warstwa 3 (Kanon & Modele LLM / Translator)**:
  `translator.py` performs translation passes while adhering strictly to verified metadata, preventing acoustic pitch from polluting character gender registries.
- **Warstwa 4 (EpisodeQualityGate & Linter offline 0.00 PLN)**:
  `avt_linter.py` provides deterministic single-token harmonization ($W_i \to W'_i$), plural addressee pronoun harmonization, predicate adjective/noun gender agreement with possessives, and masculine vocative protection.
- **Warstwa 5 (Testy Regresyjne)**:
  `test_system.py` contains 156 existing atomic tests. Extended with atomic Test 157 covering all 6 phenomena of INC-AVT-004 with positive and negative assertion controls (157/157 PASS). Further hardened with adversarial suites `test_adversarial_challenger1.py` and `test_adversarial_challenger2.py`.

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | R1: Toponym Sanitization & Glossary Integration | Dynamically read `custom_glossary` and series glossary in `sanitize_toponymic_origin_and_companionship()`, add Tensei Kizoku toponyms (`Seitz`, `Canarre`, `Lamberg`) to `KNOWN_FANTASY_TOPONYMS`, protect against false instrumental ('z Seitzem' -> 'z Seitz', 'z Canarrem' -> 'z Canarre', 'z Lambergem' -> 'z Lamberg'), update phonetic prepositions ('ze Seitz' -> 'z Seitz'), and block `SeriesBible.update_from_episode_profile()` from generating declensions for non-character entities. Support ASS line breaks `\N`, `\h`, inline tags, and phonetic `ze` before inflected toponyms. | M1 | ORIGINAL_REQUEST § R1, Explorer 1 |
| 2 | R2: Plural Addressee Guard & Pronoun Harmonizer | Expand `WhisperDisambiguator` plural markers. In `avt_linter.py`, implement `harmonize_2nd_person_singular_to_plural_pronouns()` activated when `wdd_tag.addressee_is_group == True` or a 2nd person plural verb is present (`tęsknicie`, `poddajcie się`, `słuchajcie`, and imperative stems in `-czcie`, `-ńcie`, `-żcie`, `-rzcie`, `-dźcie`, `-śćcie`), converting singular 2nd person pronouns ('do ciebie' -> 'do was', 'cię' -> 'was', 'tobie' -> 'wam', 'z tobą' -> 'z wami') with strict protection for demonstrative pronoun 'ci' and homophonic nouns on '-cie'. | M1 | ORIGINAL_REQUEST § R2, Explorer 1 |
| 3 | R3: Age Variant Gender Inheritance & Imperative Predicate | In `series_memory.py`, implement Pass 0 in `get_character_gender()` and `resolve_actor_gender()` for age prefixes (`Young`, `Kid`, `Little`, `Baby`, `Child`) inheriting gender from base name (`Young Braham` -> MALE from `Braham`). In `avt_linter.py`, include `bądź`/`bądźcie` in `has_2nd_person_marker` (preventing false soliloquy classification) and extend `pat_adj` with negative imperative `nie bądź` / `nie bądźcie` ('nie bądź naiwna' -> 'nie bądź naiwny' for male addressee). | M1 | ORIGINAL_REQUEST § R3, Explorer 2 |
| 4 | R4: Social Role Pairs with Possessive Pronouns | Expand `PREDICATE_MODS_INSTRUMENTAL` and `PREDICATE_MODS_NOMINATIVE` in `avt_linter.py` with possessive pronouns (`swoim`/`swoją`, `waszym`/`waszą`, `swój`/`swoja`, `wasz`/`wasza`, `ulubionym`/`ulubioną`), make `pat_pn` modifier matching flexible for adjectives ending with `-ą`/`-a`, and ensure cascading conversion of phrases like 'jesteś moją najlepszą uczennicą' -> 'jesteś moim najlepszym uczniem' for male addressee. | M1 | ORIGINAL_REQUEST § R4, Explorer 3 |
| 5 | R5: Elimination of Seiyū Audio Contamination & Bible Hygiene | In `translator.py` and `series_memory.py`, prevent acoustic pitch ("dziecięcy") from defaulting to FEMALE, block `update_character_gender_from_audio()` from marking male/boy role keywords (`Kid`, `Son`, `Boy`, `Young`, `Bro`, `Brother`) as FEMALE, implement auto-sanitization in `_sanitize_bible_integrity()`, and heal `Tensei_Kizoku_Kantei_Skill_de_Nariagaru_bible.json` (Zaht's Kid -> MALE, Braham's Bro -> MALE, Seitz Captain -> MALE). | M1 | ORIGINAL_REQUEST § R5, Explorer 2 |
| 6 | R6: Masculine Vocative Deterministic Shield | In `avt_linter.py` (`EpisodeQualityGate.audit_and_fix_entire_episode`), replace raw nominative lookup with declension dictionary `character_declensions[cname]["W"]` anchored by punctuation. When verified masculine vocative ('Rietzie', 'Brahamie', 'Arsie', 'Rayu') is present and no female vocative exists, enforce `is_target_male = True` and single-token harmonization of 2nd person singular past verbs ('byłaś' -> 'byłeś', 'zrobiłaś' -> 'zrobiłeś') while leaving 3rd person verbs untouched. | M1 | ORIGINAL_REQUEST § R6, Explorer 3 |
| 7 | R7: Atomic Test 157 & CI/CD Validation | Create atomic Test 157 `test_tensei_kizoku_s3_root_cause_vocative_and_audience_guard()` in `test_system.py` testing all 6 phenomena with double-sided assertions (positive fixes + negative false-positive guards), register in `__main__`, and verify 157/157 passing. | M1 | ORIGINAL_REQUEST § R7, Explorer 3 |
| 8 | R8: Independent Forensic Audit & Executive Dossier | Conduct dual adversarial reviews (2 Reviewers), empirical stress testing (2 Challengers), independent forensic integrity audit (VICTORY CONFIRMED), and compile Executive Dossier with `[CERTYFIKAT ELIMINACJI ŹRÓDŁOWEJ]`. | M1 | ORIGINAL_REQUEST § R8 |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | INC-AVT-004 Remediation & CI/CD Pass | Engine algorithmic remediation (R1–R6) across `series_memory.py`, `whisper_disambiguator.py`, `avt_linter.py`, `translator.py`, bible hygiene, Test 157 in `test_system.py`, and complete dual adversarial + forensic audit. | Survey completed | DONE |

## Code Layout
- `series_memory.py`: Toponym origin sanitization, `KNOWN_FANTASY_TOPONYMS`, `SeriesBible.update_from_episode_profile` non-character entity guard, `get_character_gender` age prefix & kinship suffix inheritance, `update_character_gender_from_audio` boy role guard, `_sanitize_bible_integrity`.
- `whisper_disambiguator.py`: Expansion of plural markers and collective vocatives.
- `avt_linter.py`: Plural pronoun harmonizer, `has_2nd_person_marker` imperative support, `pat_adj` negative imperative expansion, `PREDICATE_MODS` possessive pronoun expansion, flexible predicate modifier matching, masculine vocative detection via `decl["W"]` and addressee target forcing.
- `translator.py`: Audio F0 arbitration boy role check, prevention of female registration for boy roles.
- `series_memory/Tensei_Kizoku_Kantei_Skill_de_Nariagaru_bible.json`: Hygiene cleanup of Zaht's Kid, Braham's Bro, Seitz Captain.
- `test_system.py`: Atomic Test 157 and main runner registration (157/157).
- `test_adversarial_challenger1.py`: Adversarial test suite for R1 and R2 under ASS tags and line breaks (144 tests).
- `test_adversarial_challenger2.py`: Adversarial test suite for R3–R6 (48 tests).
