# PROMPT WYKONAWCZY (STANDARD 10.5) — OPTYMALIZACJA TRIGGERA DYN_8 ORAZ SYNCHRONIZACJA NORMY CPS 14–15 W FAZIE 2

## METADANE
- **Wersja docelowa:** `10.5`
- **Wersja poprzednia (baseline):** `10.4` (`ebbe426`)
- **Commit wdrożenia:** `b2095bb` (`b2095bb5b64abe39c1dd5fbcebfd999d40351b19`)
- **Podstawa audytowa:** `Artefakty/Raport_audytu_doboru_filarow_i_obciazenia_llm.md` (rekomendacje P1: `R-01` i `R-02`)

## ZAKRES OPERACJI IMPLEMENTACYJNYCH
1. **Operacja `2B.1` (`R-01`):** Zawężenie wyrażenia regularnego `culture_signs_pat` w kategorii `DYN_8` (`rules.py`) poprzez usunięcie wieloznacznych słów ogólnych (`sign`, `notice`, `warning`, `ep \d+`, `episode`), które powodowały fałszywe wzbudzanie kategorii kulturowo-humorystycznej w zwykłym dialogu. Wykrywanie napisów ekranowych realizowane jest przez flagę strukturalną `has_sign_flag`.
2. **Operacja `2B.2` (`R-02`):** Synchronizacja opisu budżetu czytelniczego w szablonie Fazy 2 (`verifier.py`) z regułą bazową `R1.7` (celowanie w polskie optimum percepcyjne `14–15` znaków na sekundę przy zachowaniu maksymalnego pułapu `17` znaków na sekundę `CPS` i limitu `38` znaków w linii `CPL`) oraz deduplikacja checklisty weryfikatora względem `STANDARD_9_CORE_RULES_PROMPT`.
3. **Operacja `2B.3` (Testy regresyjne):** Dodanie testów `T10.5_1` (`test_t10_5_1_no_false_positive_dyn8_verify_sign_notice_episode`), `T10.5_2` (`test_t10_5_2_verifier_cps_norm_aligned_with_r17`) oraz `T10.5_3` (`test_t10_5_3_verifier_checklist_deduplicated`) w `tests/test_profiler.py`.

## DOKUMENTACJA WDROŻENIA
Pełny raport z realizacji i walidacji CI/CD znajduje się w pliku `Artefakty/Raport_wdrozenia_10.5.md`.
