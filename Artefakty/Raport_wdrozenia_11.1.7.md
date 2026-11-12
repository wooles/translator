# 📋 RAPORT WDROŻENIOWY — MIKRO-HOTFIX 11.1.7: ROZRÓŻNIENIE TAGU MONOLOGU IMIĘ(M), DEDUPLIKACJA INTRA-SPEAKER WHISPER ASR, OCHRONA INTENCJI PYTAJNEJ I POWTÓRZEŃ W EQG ORAZ KANON 3-WYRAZOWEGO GLOSARIUSZA

- **Repozytorium:** `https://github.com/wooles/translator` (gałąź `main`)
- **Data wdrożenia:** `2026-11-12`
- **Wersja standardu przed wdrożeniem:** `Standard 11.1.6 (Full Glossary Inflection Guard, Cross-Speaker ASR Dedup & Off-Screen Discourse Isolation Baseline)`
- **Wersja standardu docelowa:** `Standard 11.1.7 (Monologue Tag Disambiguation, Intra-Speaker ASR Dedup, Question & Repetition Authority Guard & 3-Word Glossary Canon Baseline)`
- **Punkt wyjścia (HEAD przed wdrożeniem):** `79e596047227faf9e82353d28113733f1031d57d` (`79e5960`)
- **Commit 1 (fix):** `854a4b35929c06b22fc0329fe469e01d0616ccd8` (`854a4b3`)
- **Commit 2 (test — Nowy Commit Certyfikacji Kodu):** `a733c068d2c1bf29af517bbb0a5059826bb7e5c7` (`a733c06`)
- **Commit 3 (docs — Release):** `HEAD` (Bieżący commit dokumentacyjny)
- **Baseline Ochrony Z16 (Depuracja Legacy 1.0):** `854a4b35929c06b22fc0329fe469e01d0616ccd8` (`854a4b3` — po autoryzacji `Z16-amendment #12` dla `avt_linter.py`; bezwzględne 0 B diffu na pozostałych plikach chronionych względem `a6d40bb09d60b2d986d919de98044c6e2d9c838b`)

---

## 1. PODSUMOWANIE WYKONAWCZE I CELE MIKRO-HOTFIXU 11.1.7

Mikro-Hotfix 11.1.7 eliminuje cztery klasy rezydualnych błędów retrospektywnych (`BŁĄD-HIST-1..4` / `INC-AVT-032..035`) zidentyfikowanych w audycie operacyjnym:
1. **Zadanie 1 (BŁĄD-HIST-1 / INC-AVT-032):** Usunięcie fałszywej maskulinizacji postaci żeńskich posiadających przyklejony techniczny tag monologu wewnętrznego `(M)` bez spacji (np. `Heroine(M)`). Wprowadzono precyzyjną separację `is_glued_single_m` od jawnych oznaczeń płci ze spacją (`Soldier (M)`), a w Kroku 3 potoku `translator.py` zapewniono pierwszeństwo zweryfikowanej tożsamości z `SeriesBible` nad heurystykami aktora.
2. **Zadanie 2 (BŁĄD-HIST-2 / INC-AVT-033):** Rozszerzenie sanityzatora Whisper ASR w `whisper_disambiguator.py` o deduplikację kolejnych segmentów tego samego mówcy (`len(speakers) == 1`) przy rozbieżności tekstu angielskiego z wyborem segmentu o optymalnym budżecie sylabicznym, a także obniżenie progu deduplikacji między-mówcowej z 6 do 3 znaków.
3. **Zadanie 3 (BŁĄD-HIST-3 / INC-AVT-034):** Zabezpieczenie intencji pytajnej modelu LLM oraz celowych powtórzeń ekspresywnych w `EpisodeQualityGate` w `avt_linter.py` (w ramach autoryzowanego `Z16-amendment #12`): blokada usuwania `?`, gdy występuje w `source_en`, usunięcie `W porządku` z afirmatywnego strippingu oraz usunięcie `\s*` z `stutter_pat` chroniące onomatopeje i wołacze rozdzielone spacjami.
4. **Zadanie 4 (BŁĄD-HIST-4 / INC-AVT-035):** Wyrównywanie asymetrii znaczników stylizacyjnych `{\i1}...{\i0}` w `extract_typesetting_tags`, rozszerzenie `enforce_locked_glossary_terms` na 3-wyrazowe terminy kanoniczne z zachowaniem odmiany rzeczownika nadrzędnego oraz ujednolicenie progu podziału plansz do 38 CPL (Filar XCVIII).

---

## 2. SZCZEGÓŁOWA ANALIZA IMPLEMENTACJI W WARSTWACH 1–4

### 2.1. Zadanie 1: Rozróżnienie tagu monologu `Imię(M)` od jawnej płci `(M)` ze spacją
- W `metadata.py` w metodzie `normalize_actor_tag` dodano wykrywanie przyklejonego tagu monologu:
  ```python
  is_glued_single_m = tag_val == "m" and bool(re.search(r"[a-zA-ZąćęłńóśźżĄĆĘŁŃÓŚŹŻ]\(\s*m\s*\)$", raw_name.strip(), flags=re.IGNORECASE))
  ```
- Gdy `is_glued_single_m` jest prawdziwe, pole `gender` przyjmuje wartość `None` (zamiast fałszywego `"MALE"`), dzięki czemu postać żeńska pobiera swoją rzeczywistą płeć z `SeriesBible`.
- Tag ze spacją (np. `Soldier (M)`) zachowuje deterministyczną płeć `gender = "MALE"`.
- Wprowadzono symetryczną obsługę `is_glued_single_m` w `scene_discourse.py` (`normalize_actor_tag` oraz `_normalize_event_actor`).
- W Kroku 3 `translator.py` zweryfikowana płeć postaci z bazy wiedzy `self.series_bible.get_character_gender(cl_act)` ma bezwzględne pierwszeństwo nad surowym tagiem `ex_gen`.

### 2.2. Zadanie 2: Deduplikacja Whisper ASR dla kolejnych kwestii tego samego mówcy
- W `whisper_disambiguator.py:sanitize_aligned_whisper_transcripts` zaimplementowano dwutorową deduplikację transkrypcji ASR:
  1. **Między różnymi mówcami (`len(speakers) > 1`):** deduplikacja przy długości tekstu JP $\ge 6$ znaków lub przy długości $\ge 3$ znaków, jeśli teksty angielskie są rozbieżne (`len(distinct_en) > 1`).
  2. **Dla tego samego mówcy (`len(speakers) == 1`):** deduplikacja przy długości tekstu JP $\ge 6$ znaków i rozbieżnych tekstach angielskich (`len(distinct_en) > 1`). Transkrypcja pozostaje przypisana do tego zdarzenia, którego estymowany budżet sylabiczny wykazuje najmniejsze odchylenie bezwzględne `_syl_dev`.

### 2.3. Zadanie 3: Ochrona intencji pytajnej z source_en i powtórzeń w EpisodeQualityGate (Z16-amendment #12)
- W `avt_linter.py` w ramach autoryzowanego `Z16-amendment #12`:
  - W `audit_and_fix_entire_episode` (linia 11425) dodano warunek `and "?" not in src_en_q` zapobiegający usuwaniu pytajnika z polskich zdań, gdy `source_en` wyraża intencję pytajną.
  - Usunięto frazę `W porządku` z afirmatywnego strippingu pytajników.
  - W regułach detekcji jąkania `stutter_pat` (linie 1391 i 7599) wyeliminowano opcjonalną spację `\s*`:
    ```python
    stutter_pat = r"\b([A-Za-ząćęłńóśźżA-ZĄĆĘŁŃÓŚŹŻ]{2,}[\.!\?…]+)\1(?!\w)"
    ```
    Dzięki temu powtórzenia rozdzielone spacjami (`Carol? Carol?`, `Bum... bum... bum...`, `Nie... nie...`) pozostają w pełni nienaruszone jako ekspresywny element dramaturgii.

### 2.4. Zadanie 4: Równowaga znaczników stylizacji, obsługa 3-wyrazowych terminów glosariusza i próg 38 CPL
- W `translator.py:extract_typesetting_tags` zaimplementowano detekcję asymetrii tagów kursywy: jeśli znacznik otwierający `\i1` znajduje się w prefiksie tagów, a znacznik zamykający `{\i0}` w tekście pozostałym, są one usuwane symetrycznie, eliminując sieroce `{\i0}` i niezamknięte `{\i1}`.
- W `translator.py:enforce_locked_glossary_terms` dodano obsługę terminów 3-wyrazowych (`len(pl_words) == 3`), zachowując prawidłową odmianę rzeczownika nadrzędnego:
  ```python
  candidate_pl = f"{noun_w} {canon_mid} {canon_gen}"
  ```
- W `avt_linter.py:11450` (Z16-amendment #12) skorygowano próg długości linii plansz i tytułów z `> 45` do standardowego limitu `> 38` znaków (CPL $\le 38$).

---

## 3. PAKIET TESTÓW REGRESYJNYCH I METRYKI CI/CD

W Commicie 2 (`a733c068d2c1bf29af517bbb0a5059826bb7e5c7`) dodano 4 kompleksowe testy jednostkowo-integracyjne:
1. `tests/test_metadata.py::test_t11_1_7_b1_monologue_m_tag_does_not_override_female_character_gender` — **PASS**
2. `tests/test_discourse_and_translator.py::test_t11_1_7_b2_whisper_same_speaker_consecutive_duplicate_dedup` — **PASS**
3. `tests/test_avt_linter.py::test_t11_1_7_b3_eqg_preserves_question_mark_and_intentional_repetition_when_present_in_source_en` — **PASS**
4. `tests/test_translator.py::test_t11_1_7_b4_extract_typesetting_tags_and_three_word_glossary_guard` — **PASS**

### Stan końcowy metryk:
- **Pakiet testów jednostkowych i integracyjnych:** `427 passed, 153 deselected in 54.55s` (100% PASS, 0 błędów, 0 ostrzeżeń).
- **verify_purity.py:** `12/12 PASS` (100% Czysty, zero instancji, zero łatek onomastycznych).
- **verify_8_fixes.py:** `8/8 PASS` (Pełna zgodność architektoniczna).
- **verify_12_fixes.py:** `12/12 PASS` (Pełna integralność 12 punktów potoku).
- **verify_ultimate_pipeline.py:** `15/15 PASS` (15 bramek runtime i architektury).
- **audit_diff.ps1:** `4/4 PASS` — `[VICTORY CONFIRMED -- KOD CZYSTY I UOGOLNIONY]`.
- **Baseline Z16 (Depuracja Legacy 1.0):** Autoryzowany `Z16-amendment #12` w `avt_linter.py` (linie 1391, 7599, 11425, 11450). Wszystkie pozostałe pliki chronione Z16 zachowują bezwzględne `0 B diffu` względem `a6d40bb09d60b2d986d919de98044c6e2d9c838b`.

---

## 4. CERTYFIKAT ZGODNOŚCI ARCHITEKTONICZNEJ

Potok AVT w rewizji `Standard 11.1.7 Baseline` spełnia wszystkie wymogi Zero-Literal Pure Positive Domain Architecture oraz Primary LLM Translation Authority. Wszystkie operacje wykonano w środowisku lokalnym przy zerowym koszcie zewnętrznym (0.00 PLN).
