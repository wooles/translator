# 📋 RAPORT WDROŻENIOWY — HOTFIX 11.1.6: DOMKNIĘCIE STRAŻNIKA GLOSARIUSZA, RECONCYLIACJI RÓL RELACYJNYCH, DEDUPLIKACJI WHISPER ASR I IZOLACJI MÓWCÓW OFF-SCREEN

- **Repozytorium:** `https://github.com/wooles/translator` (gałąź `main`)
- **Data wdrożenia:** `2026-11-12`
- **Wersja standardu przed wdrożeniem:** `Standard 11.1.5 (Discourse Telemetry & Sociolinguistic Gate Certified Baseline)`
- **Wersja standardu docelowa:** `Standard 11.1.6 (Full Glossary Inflection Guard, Cross-Speaker ASR Dedup & Off-Screen Discourse Isolation Baseline)`
- **Punkt wyjścia (HEAD przed wdrożeniem):** `79f6e6919c570eb3d8edd4cb5705881f5f9c9e13` (`79f6e69`)
- **Commit 1 (fix):** `d69d3f3004104ddad01cf9455c534a3dcb8b9664` (`d69d3f3`)
- **Commit 2 (test — Nowy Commit Certyfikacji Kodu):** `0651e17ed250bf9be31b9670695b8e0f86d481b3` (`0651e17`)
- **Commit 3 (docs — Release):** `HEAD` (Bieżący commit dokumentacyjny)
- **Baseline Ochrony Z16 (Depuracja Legacy 1.0):** `a6d40bb09d60b2d986d919de98044c6e2d9c838b` (`a6d40bb`) — **0 B diffu na wszystkich plikach chronionych**

---

## 1. PODSUMOWANIE WYKONAWCZE I CELE HOTFIXU 11.1.6

Hotfix 11.1.6 domyka cztery kluczowe obszary wykazane w audycie weryfikacyjnym 11.1.5 jako luki integracyjne lub zjawiska rezydualne:
1. **Zadanie 1 (BŁĄD-1 / INC-AVT-028):** Wprowadzenie deterministycznego strażnika terminologii kanonicznej `enforce_locked_glossary_terms` w `translator.py`. Strażnik działa zarówno bezpośrednio po wygenerowaniu odpowiedzi w Fazie 1, jak i po weryfikacji w Fazie 2. Obsługuje odcinanie prefiksów tytularnych (np. `Lord`, `Lady`, `Sir`), dopasowywanie form liczby mnogiej w języku angielskim oraz automatyczną konwersję odwróconych synonimów przymiotnikowych do kanonicznego szyku Rzeczownik + Dopełniacz.
2. **Zadanie 2 (BŁĄD-2 / INC-AVT-029):** Wzbogacenie procedury `_reconcile_registry_gender_in_memory` w `series_memory.py` o gramatyczny słownik rzeczowników ról relacyjnych (np. `ojciec`, `matka`, `syn`, `córka`, `brat`, `siostra`). Procedura parsuje relacje skierowane postaci, ustala deterministyczną płeć P0 na podstawie rzeczownika roli i uzgadnia rekordy postaci w pamięci RAM bez mutowania fizycznych plików bazy wiedzy.
3. **Zadanie 3 (BŁĄD-3 / INC-AVT-030):** Implementacja filtru `sanitize_aligned_whisper_transcripts` w `whisper_disambiguator.py`. Filtr usuwa halucynacje i przecieki tekstu japońskiego Whisper ASR między sąsiadującymi kwestiami na podstawie kryterium gęstości czasowej oraz minimalizacji odchylenia długości transkrypcji od liczby słów w kwestii dialogowej.
4. **Zadanie 4 (BŁĄD-4 / INC-AVT-031):** Izolacja mówców tła i narracji off-screen o stylach takich jak `Italics - Top` w `scene_discourse.py` (`_is_offscreen_speaker_excluded`). Tacy mówcy nie są traktowani jako aktywni adresaci dialogu w scenie, a złożone etykiety aktorów w napisach zachowują pełną integralność.

---

## 2. SZCZEGÓŁOWA ANALIZA IMPLEMENTACJI W WARSTWACH 1–4

### 2.1. Zadanie 1: `enforce_locked_glossary_terms` w `translator.py`
- Zdefiniowano uniwersalną funkcję `enforce_locked_glossary_terms(en_text, candidate_pl, glossary_entries, phase1_pl)`.
- Funkcja analizuje wpisy glosariusza odcinka i potoku (`combined_glossary`), identyfikuje terminy EN z pominięciem prefiksów tytularnych (`TITLE_PREFIXES`) oraz z uwzględnieniem końcówek liczby mnogiej (`s`, `es`).
- W przypadku wykrycia odwróconego synonimu przymiotnikowego koryguje go do kanonicznej postaci fleksyjnej (np. z dopasowaniem odpowiedniego przypadka).
- Wpięta symetrycznie:
  - W Fazie 1 (`phase1_batch`, tuż po odebraniu tekstu z modelu LLM i formatowaniu).
  - W Fazie 2 (po weryfikacji przez model Verifiera, chroniąc formę kanoniczną przed degradacją synonimiczną).

### 2.2. Zadanie 2: Reconcyliacja ról relacyjnych w `series_memory.py`
- Rozbudowano `_reconcile_registry_gender_in_memory` o korpus 32 rzeczowników żeńskich (`FEMALE_ROLE_NOUNS`) oraz 33 rzeczowników męskich (`MALE_ROLE_NOUNS`).
- Dodano parser relacji skierowanych `\(([^)]+?)\s*->\s*([^)]+?)\)`, który wyodrębnia nazwę relacji i dopasowuje jej rdzeń do korpusu.
- Jeśli postać posiada niejednoznaczną płeć (`UNKNOWN`) lub brak rekordu, procedura w pamięci RAM uzgadnia `gender = "FEMALE"` lub `gender = "MALE"`, ustawia `has_verified_gender = True` i aktualizuje powiązane tagi relacji.

### 2.3. Zadanie 3: Deduplikacja okien Whisper ASR w `whisper_disambiguator.py`
- Dodano metodę `sanitize_aligned_whisper_transcripts(whisper_dict, events)`.
- Rozwiązuje dwa zjawiska zaszumienia:
  1. Mikro-kwestie (czas trwania $\le 2200$ ms, liczba słów EN $\le 2$, długość transkrypcji JP $> 12$ znaków) otrzymują pusty ciąg transkrypcji ASR.
  2. Zduplikowane transkrypcje przypisane do sąsiednich kwestii różnych mówców: transkrypcja pozostaje wyłącznie przy tej kwestii, której oczekiwana długość mowy ($2.2 \times \text{liczba słów}$) wykazuje najmniejsze odchylenie bezwzględne od długości tekstu JP.

### 2.4. Zadanie 4: Izolacja mówców off-screen w `scene_discourse.py`
- Dodano funkcję `_is_offscreen_speaker_excluded(turn, characters_present)`.
- Mówcy kwestii o stylach off-screen (np. `Italics - Top`, `Flashback`, `Narration`) niebędący fizycznie obecni na scenie nie są ustawiani jako adresaci w procedurach Lookback, Lookahead ani Turn Exchange.
- W `split_oversized_ass_events` w `translator.py` zastosowano separator `\s+/\s+`, chroniąc zbitki ról bez spacji (np. `Worker A/B`).

---

## 3. PAKIET TESTÓW REGRESYJNYCH I METRYKI CI/CD

W Commicie 2 (`0651e17ed250bf9be31b9670695b8e0f86d481b3`) zaimplementowano 4 testy jednostkowo-integracyjne Standardu 11.1.6:
1. `tests/test_hygiene.py::test_t11_1_6_b1_glossary_enforced_when_phase1_uses_synonym_or_plural` — **PASS**
2. `tests/test_series_memory.py::test_t11_1_6_b2_relations_role_noun_gender_reconciliation` — **PASS**
3. `tests/test_discourse_and_translator.py::test_t11_1_6_b3_whisper_cross_speaker_hallucination_dedup` — **PASS**
4. `tests/test_discourse_and_translator.py::test_t11_1_6_b4_offscreen_addressee_isolation_and_compound_actor_ass` — **PASS**

### Stan końcowy metryk:
- **Pakiet testów jednostkowych i integracyjnych:** `423 passed, 153 deselected in 48.25s` (100% PASS, 0 błędów, 0 ostrzeżeń).
- **verify_purity.py:** `12/12 PASS` (100% Czysty, zero instancji, zero łatek onomastycznych).
- **verify_8_fixes.py:** `8/8 PASS` (Pełna zgodność architektoniczna).
- **verify_12_fixes.py:** `12/12 PASS` (Pełna integralność 12 punktów potoku).
- **verify_ultimate_pipeline.py:** `15/15 PASS` (15 bramek runtime i architektury).
- **audit_diff.ps1:** `4/4 PASS` — `[VICTORY CONFIRMED -- KOD CZYSTY I UOGOLNIONY]`.
- **Baseline Z16 (Depuracja Legacy 1.0):** Dokładnie `0 B diffu` na wszystkich plikach chronionych względem commita `a6d40bb09d60b2d986d919de98044c6e2d9c838b`.

---

## 4. CERTYFIKAT ZGODNOŚCI ARCHITEKTONICZNEJ

Potok AVT w rewizji `Standard 11.1.6 Baseline` spełnia wszystkie wymagania Zero-Literal Pure Positive Domain Architecture oraz Primary LLM Translation Authority. Wszystkie operacje wykonano w środowisku lokalnym przy zerowym koszcie zewnętrznym (0.00 PLN).
