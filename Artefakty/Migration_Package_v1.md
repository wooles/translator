# KONTEKST PROJEKTU: POTOK AVT — KONTYNUACJA PO MIGRACJI

## PROJEKT

Potok tłumaczenia audiowizualnego anime (AVT) zbudowany na LLM. Architektura:
- **Faza 1:** pierwotne tłumaczenie (Primary LLM Translation Authority — nadrzędny autorytet).
- **Faza 2 (`DialogueVerifier`):** weryfikacja stylistyczna + deterministyczne strażniki regresji.
- **Post-processing offline:** `AVTLinter`, `EpisodeQualityGate`, higiena ASS.
- **Pipeline danych:** `SeriesBible` (rekordy P0 płci), `SceneDiscourseGraph` (telemetria), `EpisodeProfiler` (profil odcinka), `RuleDispatcher` (selekcja reguł).

## ZASADY NADRZĘDNE (Standard 9.0)

1. **Zero-Literal** — reguły operują na kategoriach metajęzyka architektury. Zero cytatów zdań, imion, konkretnych literałów jako przykładów.
2. **Pure Positive Domain Invariant** — każda reguła definiuje dopuszczalny stan pozytywnie („prawidłowy stan = X"). Stany spoza zbioru są niepoprawne z definicji.
3. **Primary LLM Translation Authority** — `phase1_text` to nadrzędny autorytet. Faza 2 i post-processing nie zmieniają formy bez dowodu z rekordu P0 (`p0_gender`, `has_verified_gender: true`) lub jednoznacznego `en_text` / `pronouns_en`.
4. **Instance-Free Metalinguistic Architecture** — opisy kategoriopochodne, nie instancyjne.

## STAN PRACY (na moment migracji)

**Wykonane:**
- **Plan Naprawczy 1.0** operacji testowych — audyt 20 operacji K1–K4 (wynik: 2 WYŁĄCZYĆ, 8 NAPRAWIĆ, 10 POZOSTAWIĆ).
- **Audyt EP01** — wykryto 8 błędów (2 objęte Planem 1.0, 1 nieobjęty, 5 w konfliktach pełnych).
- **Prompt Naprawczy 9.2** wygenerowany — 6 zmian (2B.1 + 2C.1–2C.5) + reguły R1.1–R1.5, R3.1–R3.3 + 2 refaktory testów + 6 nowych testów parametryzowanych.
- **Wdrożenie 9.2** — zakończone (commit 88b7327): 6 zmian w `verifier.py`, `avt_linter.py`, `series_memory.py`, `scene_discourse.py`, `rules.py`; 6 nowych testów PASSED + 13 dodatkowych; wszystkie bramki `verify_*` 100% PASS; `audit_diff.ps1` VICTORY.

**Do wykonania teraz:**
1. **Weryfikacja regresji EP01** — czy 8 błędów z EP01 zostało wyeliminowanych po wdrożeniu 9.2, czy pojawiły się nowe.
2. **Prompt Naprawczy 9.3** — dla kolejnego odcinka EP02, z harmonizacją względem 9.2 (auto-inkrementacja 9.2 → 9.3).

## ZADANIE DO WYKONANIA W TYM CZWARCIE

**Tryb 2-etapowy, harmonizacja z Promptem Naprawczym 9.2.**

**Wejścia:**
- Para EP01_post: `.ass` + `.log` — **nowy przebieg potoku po wdrożeniu 9.2** (do weryfikacji regresji).
- Para EP02: `.ass` + `.log` — kolejny odcinek (dowolny: pre- lub post-9.2).

**Etap 1/2 — analiza:**
- Weryfikacja regresji EP01_post: zestawienie z 8 błędami z EP01_pre. Czy zniknęły? Czy pojawiły się nowe? Czy decyzje 9.2 działają?
- Audyt EP02: wykrycie błędów + cross-reference z Promptem 9.2 (2A/2B/2C).
- Rozkład błędów + tabela konfliktów z 9.2.

**Etap 2/2 — Prompt Naprawczy 9.3:**
- **Sekcja 2A:** operacje z 9.2 potwierdzone empirycznie w EP01_post i/lub EP02.
- **Sekcja 2B:** nowe operacje spoza 9.2 (jeśli wykryte).
- **Sekcja 2C:** konflikty z 9.2 (dowód empiryczny > analiza teoretyczna).
- Reguły R1.x / R3.x zaktualizowane o nowe wnioski.
- Walidacja testowa nowych decyzji.

## OCZEKIWANA STRUKTURA ODPOWIEDZI

- **Etap 1/2:** raport weryfikacji regresji EP01 + audyt EP02 + rozkład + tabela konfliktów z 9.2.
- **Etap 2/2:** Prompt Naprawczy 9.3 w bloku kodu `markdown` + rekordy walidacji testowej + SELF-CHECK.

**Po Etapie 1/2 napiszę „kontynuuj" — nie powtarzaj wtedy wejść.**

## PLIKI — DOŁĄCZONE DO TEJ WIADOMOŚCI

- `EP01_post.ass` + `EP01_post.log` — para EP01 z nowego przebiegu potoku (post-9.2).
- `EP02.ass` + `EP02.log` — para EP02.