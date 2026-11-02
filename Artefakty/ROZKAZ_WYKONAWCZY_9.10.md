# ROZKAZ WYKONAWCZY DLA AGENTA KODUJĄCEGO — WDROŻENIE WERSJI 9.10



## 0. NOTA KRYTYCZNA — PLIKI AUDYTORA WYMAGAJĄ POPRAWEK PRZED IMPLEMENTACJĄ



Pliki `Prompt_9.10.md` i `Raport_wdrozenia_9.10.md` zapisane przez model audytujący **wymagają 5 poprawek** (wykrytych w analizie porównawczej). Poprawki muszą być zastosowane **w KROKU -1** tego ROZKAZU, **przed** jakąkolwiek modyfikacją kodu produkcyjnego.



| # | Plik | Problem | Wpływ na wdrożenie |

|---|---|---|---|

| **P1** | `Prompt_9.10.md` | Brak Sekcji 5A.3 (Warunek ukończenia a–p) — audytor urwał na wzorcach testów | Agent kodujący nie ma checklisty (a)–(p); ryzyko pominięcia warunków |

| **P2** | `Prompt_9.10.md` | Sekcja 6 ZAKAZY urwana w połowie zdania, bez zamknięcia bloku | Brak pełnej listy ZAKAZ 1–12; ryzyko naruszenia zakazów |

| **P3** | `Prompt_9.10.md` | Testy T10.3 i T10.4 zawierają **hardcoded wartości polskie** (`"kodu wewnętrznego"`, `"Gdybyśmy tylko wiedzieli..."`) — naruszenie Zero-Literal | Testy złamią Zasadę 1; audyt 9.10 wykryje regresję |

| **P4** | `Raport_wdrozenia_9.10.md` | Szkielet ma tylko 6 sekcji (brak: D1–D6, ocena niedegradacyjności, SELF-CHECK, 6C, 10, 11, 12, 13) | Agent nie będzie miał gdzie zaraportować walidacji empirycznej, degradacji, decyzji zamknięcia |

| **P5** | `Raport_wdrozenia_9.10.md` | Tabela P0.3 nie zawiera 4 placeholderów (`TERMIN_PRZYMIOTNIKOWY_D_1`, `TERMIN_PRZYMIOTNIKOWY_N_1`, `CIAG_PL_1`, `CIAG_PL_2`) | Agent nie będzie mógł wypełnić testów T10.3/T10.4 (po P3) |



**Dodatkowo (poza poprawkami):** Bramki `verify_12_fixes.py` (4/12 PASS) i `verify_ultimate_pipeline.py` (11/15 PASS) wymagają **audytu per-assertion** — to KROK 3A tego ROZKAZU (bug_pattern vs bug_code vs obsolete_check).



---



## 1. PLIKI WEJŚCIOWE I DOCELOWE



### Pliki do odczytu / zapisu (Write/Update):

1. **Specyfikacja (Read+Write)** — `C:\Users\Piotrek\Desktop\translator\Artefakty\Prompt_9.10.md`

   - **Wersja wyjściowa od audytora** — wymaga 3 poprawek (P1, P2, P3) w KROKU -1

   - Po poprawkach: specyfikacja operacji 2B.1–2B.4 + Phase 0 + wzorce T10.1–T10.4 + Sekcja 5A.3 + Sekcja 6 ZAKAZY

2. **Szkielet raportu (Read+Write)** — `C:\Users\Piotrek\Desktop\translator\Artefakty\Raport_wdrozenia_9.10.md`

   - **Wersja wyjściowa od audytora** — wymaga 2 poprawek (P4, P5) w KROKU -1

   - Po poprawkach: 13 sekcji gotowych do wypełnienia w KROKU 4

3. **Raport poprzedniej iteracji (Update)** — `C:\Users\Piotrek\Desktop\translator\Artefakty\Raport_wdrozenia_9.9.md`

   - Aktualizacja statusu (Sekcja 1) + dopisanie Sekcji 13 akapitem o zamknięciu



### Pliki baseline odcinka Hyouken S2-04 (Read, BEZWZGLĘDNIE NIETYKALNE):

4. `C:\Users\Piotrek\Desktop\translator\Artefakty\Hyouken no Majutsushi ga Sekai wo Suberu S2 - 04.ass`

5. `C:\Users\Piotrek\Desktop\translator\Artefakty\Hyouken no Majutsushi ga Sekai wo Suberu S2 - 04_full_trace.log`

6. `C:\Users\Piotrek\Desktop\translator\Artefakty\przebieg_tlumaczenia_hyouken.txt`

7. `C:\Users\Piotrek\Desktop\translator\Artefakty\EN_Hyouken no Majutsushi ga Sekai wo Suberu S2 - 04.ass`

8. `C:\Users\Piotrek\Desktop\translator\Artefakty\Hyouken_no_Majutsushi_ga_Sekai_wo_Suberu_S2_bible.json` (WYMAGA regeneracji przez `_sanitize_loaded_bible_in_ram`, NIE ręcznej edycji)



### Kontekst historyczny (Read):

9. `C:\Users\Piotrek\Desktop\translator\Artefakty\Prompt_9.7.md` — ZAKAZY 1–10 z Sekcji 6

10. `C:\Users\Piotrek\Desktop\translator\Artefakty\Prompt_9.9.md` — kontekst operacji 2A



Przeczytaj `Prompt_9.10.md`, `Raport_wdrozenia_9.10.md` oraz `Raport_wdrozenia_9.9.md` w całości **PRZED** wykonaniem KROKU -1.



---



## 2. CEL INŻYNIERYJNY WERSJI 9.10



Audyt generalizacji międzyseryjnej na Hyouken S2-04 (Etap 1/2: 5/9 CZYSTY, 4/9 wymaga 9.10; Etap 2/2: 3/7 SPEŁNIONE, 4/7 CZĘŚCIOWO) zidentyfikował 4 zadania domykające:



1. **`2B.1`:** Ochrona strukturalnego `p0_gender` w `metadata.py` (`get_anime_context` — koniec domyślnego `"mężczyzna"` przy neutralnym opisie) + dziedziczenie płci przez jednoczłonowe aliasy dwuczłonowych P0 + ochrona `FEMALE` w `series_memory.py` (`INHERENT_FEMALE_NOUNS`, `POLISH_FEMALE_NAMES`, `UNIVERSAL_FEMALE_NAMES_ON_A`, `FOREIGN_FEMALE_CONSONANT_NAMES`).

2. **`2B.2`:** Filtracja ontologiczna etykiet zbiorowych/małoliterowych/adnotowanych (`Both`, `All`, `pants`, `Carol?`, `ElisaHeart`) + dodanie `-ny/-na/-ne` do `is_polish_adjective` + blokada generowania paradygmatów męskożywotnych dla wielowyrazowych terminów apelatywnych i dopełniaczy l.mn. na `-ów`.

3. **`2B.3`:** Podłączenie `prev_line_f1`/`prev_line_en` w `pass1_items` i `verify_batch` (aktywacja Kategorii 12, 13, 17 w runtime) + reset bufora deduplikacji ASR w `translate_file`.

4. **`2B.4`:** `Artefakty` w `norecursedirs` + **audyt per-assertion** bramek CI/CD (`verify_12_fixes.py` 4/12, `verify_ultimate_pipeline.py` 11/15).



**UWAGA:** Iteracja 9.10 **WYMAGA walidacji empirycznej** (re-tłumaczenie Hyouken S2-04 lub innego odcinka). To NIE jest mikro-iteracja architecture-only (jak 9.9) — Etap 2/2 wykrył 4/7 zasad CZĘŚCIOWO.



---



## 3. PROCEDURA WYKONANIA (KROK PO KROKU)



### KROK -1 (OBOWIĄZKOWY) — SANACJA PLIKÓW AUDYTORA



Przed jakąkolwiek implementacją kodu produkcyjnego zastosuj 5 poprawek do `Prompt_9.10.md` i `Raport_wdrozenia_9.10.md`. Poprawki muszą być zastosowane **dosłownie** (verbatim), bez modyfikacji merytorycznej.



#### PATCH-1 (P1) — Uzupełnienie Sekcji 5A.3 w `Prompt_9.10.md`



**Miejsce wstawienia:** bezpośrednio **po** wzorcach testów T10.1–T10.4 (blok kodu Pythona zamykający Sekcję 5A), **przed** `SEKCJA 6: ZAKAZY`.



**Treść do wstawienia (verbatim):**



```markdown

### 5A.3. Warunek ukończenia wdrożenia (definicja pozytywna — punkty (a)–(p))



Prawidłowy stan ukończenia wdrożenia 9.10 = jednoczesne spełnienie szesnastu warunków pozytywnych:



- **(a)** Wszystkie operacje z Sekcji 2A (`2A.1–2A.2`) utrzymane w stanie nienaruszonym.

- **(b)** Brak regresji w operacjach wdrożonych w wersjach 9.4–9.9.

- **(c)** Wszystkie operacje z Sekcji 2B (`2B.1–2B.4`) w pełni wdrożone w runtime.

- **(d)** Wszystkie reguły z Sekcji 1 (`R1.1–R1.11`) i Sekcji 3 (`R3.1–R3.5`) zachowane w czystej formie pozytywnej.

- **(e)** Wszystkie 4 nowe testy jednostkowe (`T10.1–T10.4`) zaimplementowane i sparametryzowane (≥ 2 warianty każdy).

- **(f)** `komenda_fast` (`pytest`): 100% PASSED (≥ 216 instancji), `0 FAILED`, `0 ERROR`, czas wykonania < 60 s.

- **(g)** `komenda_full` (`pytest -m ""` lub `pytest -m "slow or not slow"`): 100% PASSED (≥ 369 instancji), `0 FAILED`, `0 ERROR`.

- **(h)** `komenda_slow` (`pytest -m slow`) oraz `komenda_network` (`pytest -m network`): 100% PASSED.

- **(i)** Bramki CI/CD (`verify_purity.py`, `verify_ultimate_pipeline.py`, `verify_12_fixes.py`) zwracają 100% PASS lub FAIL z jawnym uzasadnieniem (patrz 2B.4 + KROK 3A).

- **(j)** `audit_diff.ps1` zwraca status VICTORY CONFIRMED.

- **(k)** Phase 0 ukończona z wypełnionymi tabelami P0.2 i P0.3 w `Raport_wdrozenia_9.10.md`.

- **(l)** Każdy nowy test `T10.1–T10.4` zweryfikowany empirycznie pod kątem falsyfikowalności i wolny od anty-wzorców `D1–D6`.

- **(m)** **Walidacja empiryczna (obowiązkowa):** re-tłumaczenie Hyouken S2-04 potwierdza 5/5 wyeliminowanych kategorii w Sekcji 6C raportu.

- **(n)** Żaden z 212 testów domyślnych (116 `KEEP` + 96 z 9.4–9.9) nie został usunięty ani osłabiony.

- **(o)** Katalog `tests/archive/` oraz 3 gałęzie `# DEFENSIVE_FALLBACK` w `avt_linter.py` nietknięte.

- **(p)** Wszystkie pola `<DO_WYPEŁNIENIA_*>` w `Raport_wdrozenia_9.10.md` wypełnione (0 placeholderów).

```



#### PATCH-2 (P2) — Uzupełnienie Sekcji 6 ZAKAZY w `Prompt_9.10.md`



**Miejsce:** na końcu pliku `Prompt_9.10.md` — zastąp urwane zdanie `...zakaz wycieku literalnego).` pełną listą ZAKAZ 1–12 i zamknięciem.



**Treść do wstawienia (verbatim):**



```markdown

## SEKCJA 6: ZAKAZY ARCHITEKTONICZNE (DZIEDZICZONE Z 9.7 + ROZSZERZENIA 9.10)



1. **ZAKAZ 1** (mutacji tekstu poza `AVTLinter` i `EpisodeQualityGate`).

2. **ZAKAZ 2** (podmiany członów antroponimów wieloczłonowych).

3. **ZAKAZ 3** (globalnego dopisywania aliasów tytułowych).

4. **ZAKAZ 4** (Test-Only Wiring i mockowania logiki domenowej w testach).

5. **ZAKAZ 5** (pomijania Phase 0 i walidacji empirycznej).

6. **ZAKAZ 6** (naruszania 212 testów domyślnych i 153 `MARK_SLOW`).

7. **ZAKAZ 7** (modyfikacji `DEFENSIVE_FALLBACK` i `tests/archive/`).

8. **ZAKAZ 8** (pozostawiania placeholderów w raporcie).

9. **ZAKAZ 9** (modyfikacji `.ass`/`.json` — Zero-Cosmetic; wyjątek: `Hyouken_..._bible.json` wymaga regeneracji przez `_sanitize_loaded_bible_in_ram`, nie ręcznej edycji).

10. **ZAKAZ 10** (wycieku Zero-Literal — konkretne wartości w kodzie, testach i `rules.py`).

11. **ZAKAZ 11** (generowania sztucznych `.ass`/`.log` w `Artefakty/` — walidacja empiryczna tylko przez rzeczywiste re-tłumaczenie).

12. **ZAKAZ 12** (manipulacji bramkami `verify_*.py` przez osłabianie asercji — dopuszczalna wyłącznie aktualizacja patternu do aktualnej implementacji, jeśli kod jest poprawny i widać to w diff).



---



**Koniec Prompt_9.10.md.**

```



#### PATCH-3 (P3a) — Sanacja testu T10.3 w `Prompt_9.10.md`



**Miejsce:** blok `@pytest.mark.parametrize` w `test_declension_generator_handles_ny_adjectives_and_plural_genitive_phrases`.



**Zamiana (find & replace):**



```python

# BYŁO (hardcoded wartości polskie):

("kodu wewnętrznego", "kodem wewnętrznym"),



# MA BYĆ (placeholdery):

("<RZECZYWISTY_TERMIN_PRZYMIOTNIKOWY_D_1>", "<RZECZYWISTY_TERMIN_PRZYMIOTNIKOWY_N_1>"),

```



#### PATCH-4 (P3b) — Sanacja testu T10.4 w `Prompt_9.10.md`



**Miejsce:** blok `@pytest.mark.parametrize` w `test_verify_batch_passes_adjacent_prev_line_to_ellipsis_continuation_guard`.



**Zamiana (find & replace) — dwa warianty:**



```python

# BYŁO (wariant 1, hardcoded):

(

    "Gdybyśmy tylko wiedzieli...",

    "...uniknęlibyśmy tej zasadzki.",

    "Uniknęlibyśmy tej zasadzki.",

    "...uniknęlibyśmy tej zasadzki.",

),

# MA BYĆ (wariant 1, placeholdery):

(

    "<RZECZYWISTY_CIAG_PL_1>...",

    "...<RZECZYWISTY_CIAG_PL_2>.",

    "<RZECZYWISTY_CIAG_PL_2>.",

    "...<RZECZYWISTY_CIAG_PL_2>.",

),



# BYŁO (wariant 2, hardcoded):

(

    "Nasza ostatnia szansa...",

    "...właśnie przepadła bezpowrotnie.",

    "Właśnie przepadła bezpowrotnie.",

    "...właśnie przepadła bezpowrotnie.",

),

# MA BYĆ (wariant 2, placeholdery):

(

    "<RZECZYWISTY_CIAG_PL_2>...",

    "...<RZECZYWISTY_CIAG_PL_1>.",

    "<RZECZYWISTY_CIAG_PL_1>.",

    "...<RZECZYWISTY_CIAG_PL_1>.",

),

```



#### PATCH-5 (P4+P5) — Rozszerzenie `Raport_wdrozenia_9.10.md` z 6 do 13 sekcji



**Miejsce:** na końcu pliku `Raport_wdrozenia_9.10.md` — **dopisz** sekcje 7–13 (zachowując istniejące 1–6).



**Treść do dopisania (verbatim):**



```markdown

## 7. OCENA NIEDEGRADACYJNOŚCI



### 7A. Zasada 8 — Częściowa (baza wyjściowa 9.9)

`<DO_WYPEŁNIENIA_OCENA_8>`



### 7B. Zasada 8 — Po wdrożeniu 9.10

`<DO_WYPEŁNIENIA_OCENA_8_PO_9_10>`



### 7C. Zasada 3 (Primary LLM Authority) — Generalizacja

`<DO_WYPEŁNIENIA_OCENA_3>`



### 7D. Zasada 4 (Instance-Free) — Generalizacja

`<DO_WYPEŁNIENIA_OCENA_4>`



## 8. MECHANIZMY DEGRADACJI — D1–D6



| Test | D1 | D2 | D3 | D4 | D5 | D6 | Status |

|---|---|---|---|---|---|---|---|

| T10.1 | `<DO_WYPEŁNIENIA>` | `<DO_WYPEŁNIENIA>` | `<DO_WYPEŁNIENIA>` | `<DO_WYPEŁNIENIA>` | `<DO_WYPEŁNIENIA>` | `<DO_WYPEŁNIENIA>` | `<DO_WYPEŁNIENIA>` |

| T10.2 | `<DO_WYPEŁNIENIA>` | `<DO_WYPEŁNIENIA>` | `<DO_WYPEŁNIENIA>` | `<DO_WYPEŁNIENIA>` | `<DO_WYPEŁNIENIA>` | `<DO_WYPEŁNIENIA>` | `<DO_WYPEŁNIENIA>` |

| T10.3 | `<DO_WYPEŁNIENIA>` | `<DO_WYPEŁNIENIA>` | `<DO_WYPEŁNIENIA>` | `<DO_WYPEŁNIENIA>` | `<DO_WYPEŁNIENIA>` | `<DO_WYPEŁNIENIA>` | `<DO_WYPEŁNIENIA>` |

| T10.4 | `<DO_WYPEŁNIENIA>` | `<DO_WYPEŁNIENIA>` | `<DO_WYPEŁNIENIA>` | `<DO_WYPEŁNIENIA>` | `<DO_WYPEŁNIENIA>` | `<DO_WYPEŁNIENIA>` | `<DO_WYPEŁNIENIA>` |



## 9. MECHANIZMY DEGRADACJI W ISTNIEJĄCYM PAKIECIE



- Nienaruszalność Depuracji Legacy 1.0 (commit `474fb64`): `<DO_WYPEŁNIENIA_WERYFIKACJA_DEPURACJI>`

- Nienaruszalność 3 gałęzi `# DEFENSIVE_FALLBACK` w `avt_linter.py` (linie ~7612, 7752, 11472): `<DO_WYPEŁNIENIA_WERYFIKACJA_FALLBACK>`

- Nienaruszalność testów 9.4–9.9: `<DO_WYPEŁNIENIA_WERYFIKACJA_9_4_9_9>`



## 10. WARUNEK UKOŃCZENIA — CHECKLIST



- [ ] (a) Operacje 2A.1–2A.2 utrzymane

- [ ] (b) Brak regresji w operacjach 9.4–9.9

- [ ] (c) Operacje 2B.1–2B.4 wdrożone

- [ ] (d) Reguły R1.1–R1.11 i R3.1–R3.5 zachowane pozytywnie

- [ ] (e) Testy T10.1–T10.4 zaimplementowane i sparametryzowane

- [ ] (f) `komenda_fast`: 100% PASSED, czas < 60 s

- [ ] (g) `komenda_full`: 100% PASSED

- [ ] (h) `komenda_slow` / `komenda_network`: 100% PASSED

- [ ] (i) Bramki CI/CD: 100% PASS lub jawne uzasadnienie FAIL w Sekcji 6D

- [ ] (j) `audit_diff.ps1`: VICTORY CONFIRMED

- [ ] (k) Phase 0 ukończona z P0.2 i P0.3

- [ ] (l) Testy T10.1–T10.4 zweryfikowane pod kątem falsyfikowalności i D1–D6

- [ ] (m) Walidacja empiryczna (Sekcja 6C) wykonana — 5/5 kategorii wyeliminowanych

- [ ] (n) 212 testów domyślnych nietknięte

- [ ] (o) `tests/archive/` i 3 DEFENSIVE_FALLBACK nietknięte

- [ ] (p) Wszystkie pola `<DO_WYPEŁNIENIA_*>` wypełnione (0 wystąpień)



## 11. SELF-CHECK RAPORTU



- [ ] Wszystkie pola `<DO_WYPEŁNIENIA_*>` wypełnione (0 wystąpień w pliku)

- [ ] Brak literalnych danych z audytowanego odcinka w kodzie, testach i sekcjach architektonicznych

- [ ] Raport zapisany pod ścieżką: `C:\Users\Piotrek\Desktop\translator\Artefakty\Raport_wdrozenia_9.10.md`

- [ ] Raport spójny z plikiem `Prompt_9.10.md` (po 5 poprawkach)

- [ ] `Raport_wdrozenia_9.9.md` zaktualizowany (status + Sekcja 13)



## 12. UWAGI AUDYTOWE PO WERYFIKACJI EMPIRYCZNEJ 9.10



`<DO_WYPEŁNIENIA_UWAGI_12>`



---



## 13. DECYZJA O ZAMKNIĘCIU ITERACJI 9.10



`<DO_WYPEŁNIENIA_SEKCJA_13>`

```



**Dodatkowo — uzupełnij Tabelę P0.3 (Sekcja 2.2 w istniejącym szkielecie) o 4 nowe placeholdery:**



```markdown

| `<RZECZYWISTY_TERMIN_PRZYMIOTNIKOWY_D_1>` | `<DO_WYPEŁNIENIA>` | Glosariusz | Forma D. terminu z przymiotnikiem na -ny |

| `<RZECZYWISTY_TERMIN_PRZYMIOTNIKOWY_N_1>` | `<DO_WYPEŁNIENIA>` | Glosariusz | Forma N. terminu z przymiotnikiem na -ny |

| `<RZECZYWISTY_CIAG_PL_1>` | `<DO_WYPEŁNIENIA>` | F1 / PL | Linia poprzedzająca parę ellipsis |

| `<RZECZYWISTY_CIAG_PL_2>` | `<DO_WYPEŁNIENIA>` | F1 / PL | Kontynuacja po wielokropku |

```



**Weryfikacja KROKU -1 (blok przed przejściem dalej):**



1. `Select-String -Path "...\Prompt_9.10.md" -Pattern "5A\.3\. Warunek ukończenia"` → znaleziono

2. `Select-String -Path "...\Prompt_9.10.md" -Pattern "ZAKAZ 12"` → znaleziono

3. `Select-String -Path "...\Prompt_9.10.md" -Pattern "kodu wewnętrznego|Gdybyśmy tylko wiedzieli"` → **0 wystąpień** (po P3/P4)

4. `(Get-Content "...\Raport_wdrozenia_9.10.md").Count` → ≥ 13 nagłówków `##` (sekcje 1–13)

5. `Select-String -Path "...\Raport_wdrozenia_9.10.md" -Pattern "DO_WYPEŁNIENIA_OCENA_8"` → znaleziono



**Jeśli którakolwiek weryfikacja fail — NIE PRZECHODŹ do KROKU 0A.**



---



### KROK 0A — Baseline + freeze SHA256 + pomiar stanu bazowego



1. **Aktualizacja `Raport_wdrozenia_9.9.md`:**

   - Sekcja 1: pole `Status wdrożenia` → `DOMKNIĘTE PRZEZ 9.10 (commit <WSTAWISZ>)`.

   - Sekcja 13: dopisz akapit: `Iteracja 9.9 domknięta przez 9.10 — audyt generalizacji na Hyouken S2-04 wykrył 4 zadania wymagające uogólnienia (patrz Raport_wdrozenia_9.10.md Sekcja 12).`



2. **Freeze SHA256** dla:

   - 3 baseline: `.ass`, `.log`, `przebieg_tlumaczenia_hyouken.txt`

   - 1 EN.ass + 1 `bible.json`

   - 5 plików kodu modyfikowanych: `metadata.py`, `series_memory.py`, `translator.py`, `verifier.py`, `pytest.ini`

   - 3 pliki bramek: `verify_12_fixes.py`, `verify_ultimate_pipeline.py`, `avt_linter.py`



3. **Pomiar stanu bazowego:**

   - `.\.venv\Scripts\python.exe -m pytest` (oczekiwane: 212 passed, 153 deselected)

   - `.\.venv\Scripts\python.exe -m pytest -m "slow or not slow"` (oczekiwane: 365 passed)

   - Bramki: `verify_purity.py`, `verify_ultimate_pipeline.py`, `verify_12_fixes.py`, `audit_diff.ps1`



Wyniki wpisz w Sekcji 4 (`STAN BAZOWY`) `Raport_wdrozenia_9.10.md`.



### KROK 0B — Phase 0 (Obowiązkowa)



Przeczytaj w całości pliki z P0.1 (patrz `Prompt_9.10.md` po PATCH-1/2). Wypełnij **Tabelę P0.2** (4 operacje) i **Tabelę P0.3** (13 placeholderów: 9 oryginalnych + 4 nowe z PATCH-5).



**WARUNEK PRZEJŚCIA:** Tabele P0.2 i P0.3 wypełnione 100%.



### KROK 1 — Implementacja `2B.1` — Ochrona strukturalnego `p0_gender`



1. **`metadata.py` (`get_anime_context`):** odczyt `c_val.get("gender")` PRZED testem tekstowym opisu. Fallback `None`, NIE `"mężczyzna"`.

2. **`series_memory.py` (`_sanitize_loaded_bible_in_ram`, `get_character_gender`, `resolve_actor_gender`):** ochrona `FEMALE` dla `INHERENT_FEMALE_NOUNS` / `POLISH_FEMALE_NAMES` / `UNIVERSAL_FEMALE_NAMES_ON_A` / `FOREIGN_FEMALE_CONSONANT_NAMES` + dziedziczenie płci z aliasów dwuczłonowych P0.

3. **`translator.py` (budowa `actor_map`):** `get_character_gender(cl_act)` PRZED `generate_polish_name_declension(cl_act, ...)`.



### KROK 2 — Implementacja `2B.2` — Filtracja ontologiczna + higiena deklinacji



1. **`metadata.py` (`normalize_actor_tag`):** usuń końcowe `?`/`!`, doklejone sufiksy `Heart`/`Thought`/`Voice`/`Internal`/`Sign`.

2. **`series_memory.py` (`populate_secondary_actor_tags`, `is_generic_actor_or_category`):** odrzuć etykiety zbiorowe (`both`, `all`, `everyone`, `wszyscy`, `oboje`, `obie`, `obaj`), wyrazy małoliterowe.

3. **`series_memory.py` (`is_polish_adjective`):** dodaj `ny`/`na`/`ne` do `ADJ_ENDINGS` przy `len >= 5`.

4. **`series_memory.py` (`generate_polish_name_declension`):** blokada doklejania końcówek do `-ów`/`-om`/`-ami`/`-ach`, wykluczenie haseł glosariusza niebędących postaciami.



### KROK 3 — Implementacja `2B.3` — prev_line + reset ASR



1. **`translator.py` (`_process_single_batch`):** `prev_line_f1` i `prev_line_en` w `pass1_items`.

2. **`verifier.py` (`verify_batch`):** fallback `batch_items[idx - 1]` lub `history_context[-1]`.

3. **`translator.py` (`translate_file`):** reset `self._asr_last_seen_end_sec = {}`, `self._asr_last_text = None`, `self._asr_consecutive_streak = 0`.



### KROK 3A — Audyt per-assertion bramek CI/CD + `2B.4`



**UWAGA KRYTYCZNA:** Audyt wykrył FAIL:

- `verify_12_fixes.py`: **4/12 PASS** (8 asercji FAIL)

- `verify_ultimate_pipeline.py`: **11/15 PASS** (4 asercje FAIL)



**Dla KAŻDEJ asercji FAIL (12 punktów verify_12 + 4 punkty verify_ultimate):**



1. Znajdź wzorzec regex/string w skrypcie.

2. Znajdź odpowiadający kod w repo (`grep`).

3. Rozstrzygnij:

   - **(a) bug_pattern:** kod poprawny, regex skryptu nieaktualny (np. `input()` vs `resolve_cli_inputs_and_honorifics` po 9.9) → **zaktualizuj pattern w skrypcie**.

   - **(b) bug_code:** kod nie zawiera wymaganej operacji → **napraw kod** w module.

   - **(c) obsolete_check:** asercja weryfikuje invariant usunięty przez 9.x → **udokumentuj w Sekcji 6D raportu z jawnym uzasadnieniem FAIL** (nie osłabiaj bramki, nie usuwaj asercji — ZAKAZ 12).



**Po rozstrzygnięciu:** dodaj `Artefakty` do `norecursedirs` w `pytest.ini`:

```ini

norecursedirs = .agents tests/archive .git .venv node_modules Artefakty

```



Uruchom ponownie 4 bramki, wyniki wpisz w Sekcji 6D.



### KROK 3B — Implementacja testów `T10.1–T10.4`



Pełne szkielety w `Prompt_9.10.md` Sekcja 5A (po PATCH-3 i PATCH-4). Skopiuj, dostosuj po Phase 0, zastąp placeholdery wartościami z Tabeli P0.3. Zweryfikuj falsyfikowalność (mutacja → FAILED) i brak D1–D6.



### KROK 3C — Bramki CI/CD po zmianach



```powershell

.\.venv\Scripts\python.exe -m pytest

.\.venv\Scripts\python.exe -m pytest -m "slow or not slow"

.\.venv\Scripts\python.exe verify_purity.py

.\.venv\Scripts\python.exe verify_ultimate_pipeline.py

.\.venv\Scripts\python.exe verify_12_fixes.py

powershell -ExecutionPolicy Bypass -File audit_diff.ps1

```



**WARUNEK ZATRZYMANIA:** FAIL bez uzasadnienia w Sekcji 6D = STOP. Wróć do KROKU 3A.



### KROK 3D — WALIDACJA EMPIRYCZNA



Re-tłumaczenie Hyouken S2-04 (lub innego odcinka). Porównaj z baseline SHA256. **Oczekiwane 5/5 wyeliminowanych:**



1. 0 rekordów żeńskich z `gender: "MALE"` w bible (po `_sanitize_loaded_bible_in_ram`).

2. 0 rekordów nie-antroponimicznych (`Both`, `All`, `pants`, `Carol?`, `ElisaHeart`).

3. Poprawne paradygmaty `-ny`/`-ów` (brak `Siedmiu Wielkich Magówa`).

4. Kategoria 17 `ellipsis_continuation_syntax` aktywna w runtime.

5. `pytest`: 0 błędów kolekcji; bramki 100% PASS lub jawne uzasadnienie.



Wyniki wpisz w Sekcji 6C.



### KROK 4 — Kompletne wypełnienie `Raport_wdrozenia_9.10.md`



Wypełnij wszystkie pola `<DO_WYPEŁNIENIA_*>` we wszystkich 13 sekcjach (po PATCH-5). Weryfikacja:



```powershell

Select-String -Path "C:\Users\Piotrek\Desktop\translator\Artefakty\Raport_wdrozenia_9.10.md" -Pattern "DO_WYPEŁNIENIA"

```

→ **0 wystąpień**.



### KROK 5 — Aktualizacja `Raport_wdrozenia_9.9.md`



- Sekcja 1: `Status wdrożenia` → `DOMKNIĘTE PRZEZ 9.10 (commit <HASH>)`.

- Sekcja 13: akapit o zamknięciu przez 9.10.



### KROK 7 — RAPORT ZWROTNY



Odeślij:



1. **Podsumowanie** — 1–2 akapity: co wdrożone, rozbieżność P0.2 vs kod, wyniki audytu per-assertion bramek.

2. **Ścieżki:** `Raport_wdrozenia_9.10.md` (wypełniony), `Raport_wdrozenia_9.9.md` (zaktualizowany).

3. **SHA256** zmodyfikowanych plików + commit hash.

4. **Status 2B.1/2B.2/2B.3/2B.4:** `WDROŻONE` / `CZĘŚCIOWO` / `POZOSTAŁ`.

5. **Lista bramek:** bug_pattern / bug_code / obsolete_check per asercja FAIL.

6. **Wyniki CI/CD:** fast/full, 3 bramki `.py`, `audit_diff.ps1`.

7. **Walidacja 6C:** 5/5 potwierdzone.

8. **Rozbieżności** Phase 0 + napotkane.

9. **Flagi niespełnionych warunków** (jeśli).

10. **Data i godzina zakończenia.**



---



## 4. DEFINICJA UKOŃCZENIA (a)–(p)



Identyczna jak w `Prompt_9.10.md` Sekcja 5A.3 (po PATCH-1). Spełnienie 16/16 punktów = wdrożenie ukończone.



**Krytyczne:** walidacja empiryczna (KROK 3D) jest **OBOWIĄZKOWA** — 9.10 to nie mikro-iteracja.



---



## 5. ZAKAZY



Pełna lista ZAKAZ 1–12 w `Prompt_9.10.md` Sekcja 6 (po PATCH-2). Dodatkowo:



- **ZAKAZ 13 (KROK -1):** Nie pomiń żadnej z 5 poprawek (P1–P5). Wdrożenie bez KROKU -1 = wdrożenie na wadliwej specyfikacji.

- **ZAKAZ 14 (KROK 3A):** Nie osłabiaj asercji bramek — dopuszczalne wyłącznie: bug_pattern (aktualizacja do aktualnej implementacji), bug_code (naprawa kodu), obsolete_check (jawne udokumentowanie FAIL).



---



## 6. CHECKLISTA PRZED URUCHOMIENIEM



```

[ ] Prompt_9.10.md — istnieje (wersja od audytora)

[ ] Raport_wdrozenia_9.10.md — istnieje (wersja od audytora, 6 sekcji)

[ ] Raport_wdrozenia_9.9.md — istnieje (wypełniony przez agenta po 9.9)

[ ] Hyouken no Majutsushi ga Sekai wo Suberu S2 - 04.ass — baseline .ass po 9.9

[ ] Hyouken no Majutsushi ga Sekai wo Suberu S2 - 04_full_trace.log — baseline .log po 9.9

[ ] przebieg_tlumaczenia_hyouken.txt — oryginalny przebieg konsolowy (56 KB)

[ ] EN_Hyouken no Majutsushi ga Sekai wo Suberu S2 - 04.ass — źródło EN

[ ] Hyouken_no_Majutsushi_ga_Sekai_wo_Suberu_S2_bible.json — baza wiedzy

[ ] Prompt_9.7.md — ZAKAZY 1-10

[ ] Prompt_9.9.md — kontekst operacji 2A

[ ] .venv\Scripts\python.exe — środowisko sprawne

[ ] KROK -1 (5 poprawek) zaplanowany jako pierwsza akcja

```



---



**KONIEC ROZKAZU WYKONAWCZEGO 9.10.**

<ADDITIONAL_METADATA>
The current local time is: 2026-10-31T01:37:25+01:00.
</ADDITIONAL_METADATA>
