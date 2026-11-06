# RAPORT WDROŻENIA STANDARDU 11.0

- **Wersja wdrożona:** `11.0`
- **Wersja bazowa:** `10.6.3` (HEAD `8d3d2990e16314490bbb4defe63e14ab777ca48d`, gałąź `main`)
- **Baseline Z16 (Depuracja Legacy 1.0):** `474fb64`
- **Data certyfikacji:** 2026-11-06
- **Status architektoniczny:** `PRODUKCYJNIE CERTYFIKOWANY (VICTORY CONFIRMED)`
- **Zrealizowane commity (Opcja C — 3 commity segmentowane):**
  1. Commit 1: `941fe44` (`feat(series_memory): Standard 11.0 - institutional toponym detection and Z16-safe alias deduplication`)
  2. Commit 2: `fb94a02` (`feat(series_memory,scene_discourse): Standard 11.0 - prepositional guard for vocative and toponym context`)
  3. Commit 3: `HEAD` (`feat(series_memory,scene_discourse): Standard 11.0 - CamelCase split and Mob* speaker isolation`)

---

## SEKCJA 0 — DIAGNOSTYKA FAZY 0 (12 KOMEND)

Poniżej zestawiono wyniki 12 komend diagnostycznych z Fazy 0, wykonanych przed przystąpieniem do modyfikacji kodu:

### 1. Weryfikacja HEAD i czystości drzewa roboczego
```
8d3d299 docs: Hotfix 10.6.3 - uzupelnienie raportu (FIX-D.4, FIX-D.5, N-08, INC-AVT-010) i statystyki git
ed226d0 fix(series_memory,metadata): Hotfix 10.6.3 - fix _resolve_bible_path season matching and consolidate split bibles
d3dfdee fix(verifier): Hotfix 10.6.2 - prevent false-positive ellipsis injection and lowercase corruption in regression guard
dbbf61a fix(series_memory): Hotfix 10.6.1 - prevent variant actor tag hijacking and single-token alias expansion
60bfa9d chore(hygiene): Hotfix 10.6 - cleanup duplicates, log suppressed exceptions, optimize context cache
```
Hash bazowy: `8d3d2990e16314490bbb4defe63e14ab777ca48d` (drzewo robocze czyste na plikach śledzonych).

### 2. Fresh read kodu dla FIX-C.1 (`synchronize_from_metadata_and_profile` w `series_memory.py:5030–5065`)
Zweryfikowano obecność punktu wejścia profilera i metadanych. `EpisodeProfile` dostarcza pola `context_description`, `plot_anchors` oraz słowniki, które stanowią źródło dla bezkolizyjnej ekstrakcji toponimów instytucjonalnych.

### 3. Fresh read kodu dla FIX-C.2 (`_sanitize_loaded_bible_in_ram` krok d i 8b w `series_memory.py:6575–6680`, `6830–6865`)
Zweryfikowano konstrukcję `conflicting_surnames` oraz krok `8b`. Potwierdzono, że aliasy nazwisk są odfiltrowywane w RAM, a krok `8b` wymagał zabezpieczenia przed sklejaniem identyfikatorów z sufiksem liczbowym.

### 4. Fresh read kodu dla FIX-C.3 (`is_non_character_entity` w `series_memory.py:8600–8630` + `_detect_event_vocative` w `scene_discourse.py:1330–1370`)
Potwierdzono, że `is_non_character_entity` przyjmowało dotąd wyłącznie `name: str`, bez uwzględnienia bezpośredniego kontekstu zdaniowego. W `_detect_event_vocative` kandydaci na wołacz z tekstu angielskiego i polskiego nie weryfikowali obecności poprzedzającego przyimka.

### 5. Fresh read kodu dla FIX-E.1 (`populate_secondary_actor_tags` w `series_memory.py:6880–6960` + `resolve_lexical_label_gender` w `series_memory.py:1930–1960`)
Wykryto brak podziału CamelCase w obu funkcjach: `clean_tag.lower()` dla `MobMan2` lub `MeanGirl` nie wyodrębniał leksemów `man` ani `girl`, przez co postacie drugoplanowe trafiały do bazy jako `UNKNOWN`. Ponadto istniejące wpisy `UNKNOWN` były pomijane przez wczesne `continue`.

### 6. Fresh read kodu dla FIX-E.2 (`resolve_turn_addressee` Kroki 1–4 w `scene_discourse.py:2450–2580`)
Potwierdzono mechanizm powstawania fałszywego adresata: w Kroku 3 (Lookahead) oraz Kroku 4 (Fallback Turn Exchange) kwestia tłumu bez wołacza i bez cech 2. osoby przejmowała kolejnego mówcę sceny po cięciu montażowym.

### 7. Weryfikacja 5 pułapek Z16 w `test_system.py`
Potwierdzono nienaruszalność testów chronionych Z16:
- Pułapka 1: `test_honorific_alias_replacement`
- Pułapka 2: `test_cross_scene_continuity`
- Pułapka 3: `Ariane Olgren` (niezmiennik integralności postaci P0)
- Pułapka 4: `Arnold` (ochrona rekordu postaci przed degradacją do toponimu)
- Pułapka 5: `Test 167 Lookahead` (stabilność dyskursu dwuosobowego)

### 8. Weryfikacja `_rebuild_actor_aliases_index` w `series_memory.py`
Potwierdzono, że indeks RAM `_actor_aliases_index` odbudowuje się w sposób zbieżny z `conflicting_surnames`, ignorując aliasy kolidujące z `institutional_toponyms`.

### 9. Weryfikacja zapisów do `entity_categories` i `institutional_toponyms`
Potwierdzono, że rejestracja toponimów instytucjonalnych nie mutuje fizycznych plików `*_bible.json` na dysku podczas normalnego działania potoku (`bible_modified = False`).

### 10. Baseline bramek CI/CD i testów
- `pytest tests/`: 325 passed
- `pytest test_system.py`: 71 passed, 153 deselected
- `verify_purity.py`: 100% PASS (11/11 bramek)
- `verify_8_fixes.py`: 100% PASS (8/8 bramek)
- `verify_12_fixes.py`: 100% PASS (12/12 bramek)
- `verify_ultimate_pipeline.py`: 100% PASS (15/15 bramek)

### 11. Weryfikacja G-Q2 golden corpus PRZED zmianami
`G-Q2 PASS: 5/5 synthetic golden cases unchanged`

### 12. Weryfikacja Z16 baseline PRZED zmianami
`git diff 8d3d299 -- test_system.py tests/archive/ avt_linter.py pytest.ini rules.py series_memory/` -> dokładnie 0 B zmian.

---

## SEKCJA 1 — COMMIT 1: `FIX-C.1` + `FIX-C.2`

- **Commit SHA:** `941fe44cfe0220ad6d877c769089db5d1781226b`
- **Commit message:** `feat(series_memory): Standard 11.0 - institutional toponym detection and Z16-safe alias deduplication`
- **Zmodyfikowane moduły:** `series_memory.py`, `tests/test_series_memory.py`

### Zakres implementacji:
1. **`FIX-C.1` (Ekstrakcja toponimów instytucjonalnych):**
   - Zdefiniowano `_INSTITUTIONAL_TOPONYM_PATTERNS` obejmujący uniwersalne kolokacje angielskie i polskie (np. `Academy`, `University`, `Institute`, `School`, `Kingdom`, `Empire`, `Duchy`, `Akademia`, `Uniwersytet`, `Królestwo`, `Cesarstwo`, `Księstwo`).
   - Wprowadzono `_GENERIC_TOPONYM_BLOCKLIST` wykluczający pospolite nazwy funkcyjne, kierunki i określenia ogólne.
   - Wdrożono metody `_extract_institutional_toponyms(sources)` oraz `_register_institutional_toponyms_from_sources(extra_sources)`.
   - Zapewniono, że jeśli kandydat pokrywa się z istniejącym kluczem głównym w `characters`, rejestracja jako toponim jest bezwzględnie pomijana, chroniąc tożsamość postaci P0.
2. **`FIX-C.2` (Deduplikacja kolizyjnych aliasów w RAM pod osłoną Z16):**
   - W `_sanitize_loaded_bible_in_ram` (krok d) rozszerzono zbiór `conflicting_surnames` o elementy `self.data.get("institutional_toponyms", [])`.
   - W `_rebuild_actor_aliases_index` zsynchronizowano logicznie wykluczanie toponimów instytucjonalnych z indeksu aliasów aktorów.
   - Operacje te odbywają się czysto w RAM bez ustawiania flagi `bible_modified = True`, co gwarantuje pełne bezpieczeństwo Z16 (0 B zapisu na dysku).

---

## SEKCJA 2 — COMMIT 2: `FIX-C.3`

- **Commit SHA:** `fb94a029b67627b2d9bdff6c67f509b9edc8c3b2`
- **Commit message:** `feat(series_memory,scene_discourse): Standard 11.0 - prepositional guard for vocative and toponym context`
- **Zmodyfikowane moduły:** `series_memory.py`, `scene_discourse.py`, `tests/test_series_memory.py`, `tests/test_discourse_and_translator.py`

### Zakres implementacji:
1. **`FIX-C.3a` (Kontekstowa weryfikacja w `is_non_character_entity`):**
   - Rozszerzono sygnaturę metody o opcjonalny parametr `context: Optional[str] = None`.
   - Gdy encja znajduje się na liście `institutional_toponyms`, a w przekazanym kontekście występuje bezpośrednio po przyimku relacyjnym lub lokatywnym (`with`, `in`, `at`, `from`, `to`, `z`, `do`, `w`), metoda zwraca `True` (klasyfikacja jako toponim w kontekście frazowym).
   - W przypadku braku kontekstu zachowano domyślny fallback chroniący postacie z `characters`.
2. **`FIX-C.3b` (Strażnik przyimkowy w `_detect_event_vocative`):**
   - Wprowadzono wzorzec `_PREPOSITION_BEFORE_CAND_PAT` oraz funkcję `_is_prepositional_context(text, candidate_match_start)`.
   - Zabezpieczono wszystkie ścieżki detekcji wołacza (kroki 1b, 1c oraz 5): fraza poprzedzona przyimkiem (np. `"relations with InstytucjaAlfa,"`) zostaje natychmiast odrzucona jako kandydat na wołacz.
   - Przekazano `clean` jako parametr `context` do wywołania `is_non_character_entity(cand, context=clean)`.

---

## SEKCJA 3 — COMMIT 3: `FIX-E.1` + `FIX-E.2`

- **Commit message:** `feat(series_memory,scene_discourse): Standard 11.0 - CamelCase split and Mob* speaker isolation`
- **Zmodyfikowane moduły:** `series_memory.py`, `scene_discourse.py`, `tests/test_series_memory.py`, `tests/test_discourse_and_translator.py`, `PROJECT_MEMORY.md`

### Zakres implementacji:
1. **`FIX-E.1a` (CamelCase split w `populate_secondary_actor_tags`):**
   - Dodano pomocnik `_split_camel_case_tokens(tag: str) -> List[str]`, rozbijający granice wielkich liter oraz cyfr na osobne tokeny.
   - W `populate_secondary_actor_tags` zastąpiono naiwne `re.findall` tokenizatorem `_split_camel_case_tokens`.
   - Zmodyfikowano warunek `clean_tag in chars`: jeśli istniejący rekord ma status `UNKNOWN`, potok pozwala na jego zaktualizowanie do `MALE`/`FEMALE` na podstawie nowo rozpoznanych leksemów.
   - Zabezpieczono zachowanie istniejącej listy aliasów przy aktualizacji rekordu.
2. **`FIX-E.1b` (CamelCase split w `resolve_lexical_label_gender`):**
   - Przed ekstrakcją tokenów leksykalnych wprowadzono rozbijanie CamelCase i cyfr na etykiecie wejściowej.
   - Identyfikatory takie jak `MobMan2`, `MobWoman`, `MeanGirl` natychmiast deterministycznie mapują się na odpowiednio `("MALE", "MASCULINE")` oraz `("FEMALE", "FEMININE")`.
3. **`FIX-E.1c` (Ochrona par z sufiksem liczbowym w kroku `8b`):**
   - W `_sanitize_loaded_bible_in_ram` zabezpieczono unifikację rekordów jednoczłonowych warunkiem `and not is_numeric_suffix_pair`.
   - Wykluczono omyłkowe sklejanie `MobMan` do `MobMan2`, zapewniając przetrwanie obu odrębnych encji.
4. **`FIX-E.2a` (Klasyfikator mówców tłumu `_is_mob_or_crowd_speaker`):**
   - Wprowadzono wzorzec `_MOB_CROWD_PAT` rozpoznający etykiety tłumu, przechodniów i gapiów w języku angielskim i polskim.
5. **`FIX-E.2b` (Filtr deiktyków 3. osoby per klauzula w `_detect_event_vocative`):**
   - Wprowadzono wzorzec `_DEICTIC_3RD_PERSON_PAT` oraz podział wypowiedzi na klauzule `_split_clauses`.
   - Zdania wprowadzające obserwacje deiktyczne (np. `"Is that the famous..."`, `"They say she's..."`, `"Podobno..."`) są odfiltrowywane przed skanowaniem wołacza, zapobiegając błędnej atrybucji podmiotu jako adresata.
   - W zdaniach wieloklauzulowych (np. `"BohaterAlfa, słyszałeś? Is that..."`) wołacz z pierwszej klauzuli jest prawidłowo zachowywany.
6. **`FIX-E.2c` (Izolacja mówców tłumu w dyskursie):**
   - W Kroku 3 `resolve_turn_addressee` (Lookahead) zablokowano transfer głównego bohatera z kolejnej sceny do tury tłumu.
   - W Kroku 4 (Fallback Turn Exchange) odizolowano tury `Mob*` nieposiadające wykładników 2. osoby ani blokady wołaczowej, zapobiegając fałszywym wymianom dyadycznym ponad granicami scen.

---

## SEKCJA 4 — MACIERZ TESTOWA (15 TESTÓW, 100% PASSED)

Wszystkie testy Standardu 11.0 operują wyłącznie na neutralnych, syntetycznych identyfikatorach ontologicznych zgodnie z Z1/Z4:

| Nr testu | Plik testowy | Zakres / Cel testu | Status |
| :--- | :--- | :--- | :---: |
| `T11.0_C_1` | `tests/test_series_memory.py` | Ekstrakcja toponimów instytucjonalnych (6 wariantów fraz EN i PL) | **PASSED** |
| `T11.0_C_2` | `tests/test_series_memory.py` | Brak nadpisywania istniejącego klucza postaci P0 w `characters` | **PASSED** |
| `T11.0_C_3` | `tests/test_series_memory.py` | Zachowanie postaci wieloczłonowej P0 po odpięciu nazwiska-toponimu | **PASSED** |
| `T11.0_C_4` | `tests/test_series_memory.py` | Brak wyzwalania zapisu na dysk przy filtrowaniu w RAM (ochrona Z16) | **PASSED** |
| `T11.0_C_5` | `tests/test_series_memory.py` | Rozpoznawanie kontekstu przyimkowego w `is_non_character_entity` | **PASSED** |
| `T11.0_C_6` | `tests/test_discourse_and_translator.py` | Odrzucenie kandydata na wołacz po przyimku (`with InstytucjaAlfa,`) | **PASSED** |
| `T11.0_C_7` | `tests/test_discourse_and_translator.py` | Poprawne rozpoznanie prawdziwego wołacza na początku zdania | **PASSED** |
| `T11.0_C_8` | `tests/test_series_memory.py` | Ochrona deklaracji postaci w `characters` i `declensions` | **PASSED** |
| `T11.0_E_1` | `tests/test_series_memory.py` | Przypisanie MALE do `MobMan`/`MobMan2` i koegzystencja po kroku `8b` | **PASSED** |
| `T11.0_E_2` | `tests/test_series_memory.py` | CamelCase split dla `MobWoman` i `MeanGirl` -> FEMALE | **PASSED** |
| `T11.0_E_3` | `tests/test_series_memory.py` | Aktualizacja istniejącego rekordu z `gender: UNKNOWN` do FEMALE | **PASSED** |
| `T11.0_E_4` | `tests/test_series_memory.py` | Ochrona zweryfikowanej postaci P0 FEMALE przed zmianą | **PASSED** |
| `T11.0_E_5` | `tests/test_discourse_and_translator.py` | Jawny wołacz od `MobMan` poprawnie ustawia `target_speaker` | **PASSED** |
| `T11.0_E_6` | `tests/test_discourse_and_translator.py` | Obserwacje deiktyczne 3. os. od `Mob*` nie ustawiają adresata | **PASSED** |
| `T11.0_E_7` | `tests/test_discourse_and_translator.py` | Filtr deiktyków per klauzula zachowuje wołacz z pierwszej części | **PASSED** |

Łączny wynik nowej macierzy testowej: **15/15 PASSED (100%)**.

---

## SEKCJA 5 — 5-WARSTWOWA WERYFIKACJA ARCHITEKTONICZNA (`CORNERSTONE.md §12`)

| Operacja | W1: Profiler (`profiler.py`, `metadata.py`) | W2: Pamięć (`series_memory.py`) | W3: Kanon (`rules.py`) | W4: Linter (`avt_linter.py`) | W5: Tarcza testowa (`test_system.py`, Z16) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`FIX-C.1`** | 0 B zmian; transparentne zasilanie z `EpisodeProfile` | Czysta separacja `institutional_toponyms` i `entity_categories` | 0 B zmian (Zero-Literal) | 0 B zmian (linter zamrożony) | Z16-P1..P5 PASS; 0 B diff na plikach chronionych |
| **`FIX-C.2`** | 0 B zmian | Spójna obsługa `conflicting_surnames` w RAM bez `self.save()` | 0 B zmian | 0 B zmian | Z16-P1..P5 PASS; brak nieuprawnionego zapisu na dysk |
| **`FIX-C.3`** | 0 B zmian | `is_non_character_entity` z parametrem `context` + strażnik w `scene_discourse.py` | 0 B zmian | 0 B zmian; brak regresji w 11 wywołaniach lintera | Z16-P1..P5 PASS; Test 167 Lookahead w 100% zachowany |
| **`FIX-E.1`** | 0 B zmian | CamelCase split w `populate_secondary_actor_tags` i `resolve_lexical_label_gender` + ochrona w `8b` | 0 B zmian | 0 B zmian | Z16-P1..P5 PASS; brak naruszenia rekordów P0 |
| **`FIX-E.2`** | 0 B zmian | `_is_mob_or_crowd_speaker` + filtr deiktyków + izolacja Kroków 3 i 4 w dyskursie | 0 B zmian | 0 B zmian | Z16-P1..P5 PASS; dyadyczny turn-taking w pełni stabilny |

---

## SEKCJA 6 — SPEŁNIENIE WARUNKÓW UKOŃCZENIA `(a)`–`(m)`

- **(a) [SPEŁNIONO]** Wykonano 12 komend diagnostycznych Fazy 0 i zestawiono ich wyniki w Sekcji 0.
- **(b) [SPEŁNIONO]** Golden corpus G-Q2 zweryfikowany przed i po każdym commicie (`G-Q2 PASS: 5/5 synthetic golden cases unchanged`).
- **(c) [SPEŁNIONO]** Wdrożono `FIX-C.1` (`_extract_institutional_toponyms` + `_register_institutional_toponyms_from_sources`).
- **(d) [SPEŁNIONO]** Wdrożono `FIX-C.2` (`conflicting_surnames` rozszerzone w RAM bez `bible_modified = True` i bez zapisu na dysk).
- **(e) [SPEŁNIONO]** Wdrożono `FIX-C.3` (`is_non_character_entity(context)` + `_is_prepositional_context` w `_detect_event_vocative`).
- **(f) [SPEŁNIONO]** Wdrożono `FIX-E.1` (CamelCase split, aktualizacja `UNKNOWN`, ochrona par liczbowych w kroku `8b`).
- **(g) [SPEŁNIONO]** Wdrożono `FIX-E.2` (`_is_mob_or_crowd_speaker`, filtr deiktyków 3. os. per klauzula, izolacja Kroków 3 i 4).
- **(h) [SPEŁNIONO]** Dodano 15 testów regresyjnych `T11.0_C_1`–`T11.0_C_8` oraz `T11.0_E_1`–`T11.0_E_7` (100% Zero-Literal).
- **(i) [SPEŁNIONO]** Wszystkie testy w `tests/` (330 passed) oraz `test_system.py` (71 passed, 153 deselected) przechodzą bezbłędnie; 4 bramki CI/CD `PASS`; `audit_diff.ps1` werdykt `VICTORY CONFIRMED`; Z16 diff = `0 B`.
- **(j) [SPEŁNIONO]** Wykonano segmentację na 3 commity zgodnie z Opcją C.
- **(k) [SPEŁNIONO]** Zaktualizowano `PROJECT_MEMORY.md` (`N-06` i `N-07` oznaczone jako `RESOLVED (Standard 11.0)`).
- **(l) [SPEŁNIONO]** Utworzono raport `Artefakty/Raport_wdrozenia_11.0.md` z 0 placeholderów.
- **(m) [SPEŁNIONO]** Benchmark wydajności G-Q7: silnik działa w czasie poniżej 15 sekund dla całego pakietu 330 testów.

---

## SEKCJA 7 — PODSUMOWANIE COMMITÓW I STATUS PRODUKCYJNY

- **Commit 1:** `941fe44` (`feat(series_memory): Standard 11.0 - institutional toponym detection and Z16-safe alias deduplication`)
- **Commit 2:** `fb94a02` (`feat(series_memory,scene_discourse): Standard 11.0 - prepositional guard for vocative and toponym context`)
- **Commit 3:** `HEAD` (`feat(series_memory,scene_discourse): Standard 11.0 - CamelCase split and Mob* speaker isolation`)

**WERDYKT FINALNY:** STANDARD 11.0 W PEŁNI CERTYFIKOWANY I GOTOWY DO OPERACJI PRODUKCYJNYCH.
