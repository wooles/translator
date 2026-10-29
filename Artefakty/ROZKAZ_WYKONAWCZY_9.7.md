# ROZKAZ WYKONAWCZY DLA AGENTA KODUJĄCEGO: WDROŻENIE PROMPTU NAPRAWCZEGO 9.7

## 1. PLIKI WEJŚCIOWE I DOCELOWE (ARTEFAKTY)

Twoim zadaniem jest pełne wdrożenie specyfikacji architektonicznej **Wersji 9.7**, aktualizacja statusu audytowego w raporcie wersji 9.6, udokumentowanie wdrożenia 9.7 w nowym raporcie wdrożeniowym oraz **przeprowadzenie walidacji empirycznej na odcinku audytowanym**.

### Pliki do odczytu / zapisu (Write/Update):
1. **Specyfikacja do wdrożenia (Read):**
   `C:\Users\Piotrek\Desktop\translator\Artefakty\Prompt_9.7.md`
2. **Szkielet raportu wersji 9.7 do całkowitego wypełnienia (Write):**
   `C:\Users\Piotrek\Desktop\translator\Artefakty\Raport_wdrozenia_9.7.md`
3. **Dokument referencyjny — pełne szkielety kodu testów T7.1–T7.4 i instrukcja aktualizacji Raportu 9.6 (Read):**
   `C:\Users\Piotrek\Desktop\translator\Artefakty\ZADANIE_4_WALIDACJA_9.7.md`
   - Sekcja `4.3. Rekord „Nowe testy"` — pełne szkielety kodu Pythona dla T7.1–T7.4 (z `import pytest`, `@pytest.mark.parametrize`, placeholderami `<RZECZYWISTY_*>`, pełnymi asercjami).
   - Sekcja `4.10. Aktualizacja statusu i Sekcji 12 w Raport_wdrozenia_9.6.md` — konkretne pola do zmiany + treść Sekcji 12 do dopisania.
4. **Raport wersji 9.6 do aktualizacji statusu, Sekcji 6C i dopisania Sekcji 12 (Update):**
   `C:\Users\Piotrek\Desktop\translator\Artefakty\Raport_wdrozenia_9.6.md`

### Pliki baseline odcinka audytowanego (Read, BEZWZGLĘDNIE NIETYKALNE):
5. `C:\Users\Piotrek\Desktop\translator\Artefakty\Sasaki to Pii-chan S2 - 04_post96.ass` (baseline `.ass` po 9.6)
6. `C:\Users\Piotrek\Desktop\translator\Artefakty\Sasaki to Pii-chan S2 - 04_post96_full_trace.log` (baseline `.log` po 9.6)
7. `C:\Users\Piotrek\Desktop\translator\Artefakty\przebieg_tłumaczenia_post96.txt` (baseline przebiegu konsolowego po 9.6)

### Plik źródłowy EN do re-tłumaczenia (Read — źródło wejściowe KROKU 3A):
8. `C:\Users\Piotrek\Desktop\translator\Artefakty\EN_Sasaki to Pii-chan S2 - 04.ass` (oryginalne napisy angielskie odcinka)

Przeczytaj plik `Prompt_9.7.md`, `Raport_wdrozenia_9.7.md` oraz `ZADANIE_4_WALIDACJA_9.7.md` w całości przed podjęciem jakichkolwiek działań w repozytorium.

---

## 2. CEL INŻYNIERYJNY WERSJI 9.7

Wdrożenie wersji 9.6 (`commit c87b22f`) wyeliminowało 4 z 5 błędów z audytu 9.5 (oczyszczenie `Adresat:` z nawiasów F0, zdjęcie całoliniowej kursywy, normalizacja `\n → \N`, czystość ASR), ale wprowadziło **1 regresję krytyczną z operacji 2B.1** oraz pozostawiło **3 drobne luki brzegowe**. Celem wersji **9.7** jest domknięcie:

1. **Regresja kaskadowej duplikacji dwuczłonowych antroponimów P0 + globalne zanieczyszczenie `aliases` w Kroku 6 (`2C.1`):**
   - Post-processing `translator.py:5785-5800` rozwija aliasy członowe (`<IMIE>`, `<NAZWISKO>`) do pełnej nazwy `<IMIE> <NAZWISKO>`, co w ID: 48 i ID: 52 daje `<IMIE_N>\N<IMIE> <NAZWISKO> <IMIE> <NAZWISKO> <NAZWISKO>`.
   - `map_bilingual_role_aliases` dopisuje aliasy z tytułu do wszystkich 22 postaci P0 zamiast do jednej pasującej fonetycznie.
2. **Płeć leksykalna etykiet P2 `Boy`/`Girl` w `populate_secondary_actor_tags` (`2C.2`):** ID: 58 ma `Adresat: Boy (FEMININE)` zamiast `(MASCULINE)`.
3. **Normalizacja `\N` vs spacja przy `changes_made: null` (`2C.3`):** 3 puste wpisy `[Redaktor Dialogów]` dla linii różniących się wyłącznie spacja vs `\N`.
4. **Artefakty `.? ??000` w ASR (`2C.4`):** ID: 79 ma nielingwistyczny ciąg przed partykułą końcową.

---

## 3. BEZWZGLĘDNA PROCEDURA WYKONANIA (KROK PO KROKU)

### KROK 0A: Aktualizacja `Raport_wdrozenia_9.6.md` oraz pomiar stanu bazowego PRZED modyfikacjami 9.7

Zanim zmodyfikujesz kod produkcyjny:

1. **Aktualizacja Raportu 9.6:**
   Otwórz `C:\Users\Piotrek\Desktop\translator\Artefakty\Raport_wdrozenia_9.6.md` i wykonaj aktualizację **zgodnie z sekcją `4.10. Aktualizacja statusu i Sekcji 12 w Raport_wdrozenia_9.6.md`** z pliku `ZADANIE_4_WALIDACJA_9.7.md`. Skrót operacji:
   - w Sekcji 1 zmień pole `Commit wdrożenia` na `c87b22f (feat(pipeline): Wdrozenie Standardu 9.6)`.
   - w Sekcji 1 zmień pole `Status wdrożenia` na:
     `FORMALNIE WDROŻONE (195/195 fast, 348/348 full, 4 bramki PASS), 4/5 BŁĘDÓW WYELIMINOWANE, 1 REGRESJA W 2B.1 (ID: 48, 52) — kontynuacja w 9.7`.
   - w Sekcji 6C w wierszu `BŁĄD 3` zaktualizuj status na: `CZĘŚCIOWO (naprawiono ID: 94 i Krok 6, lecz podmiana aliasów w 2B.1 zduplikowała dwuczłonowe imię w ID: 48 i ID: 52)`.
   - na końcu pliku dopisz **Sekcję 12 (`## 12. UWAGI AUDYTOWE PO WERYFIKACJI EMPIRYCZNEJ 9.6`)** — pełna treść Sekcji 12 w sekcji `4.10` pliku `ZADANIE_4_WALIDACJA_9.7.md`.

2. **Freeze SHA256 baseline PRZED zmianami:**
   Zapisz sumy SHA256 dla następujących plików (do porównania po walidacji empirycznej):
   - 3 pliki baseline: `Sasaki to Pii-chan S2 - 04_post96.ass`, `Sasaki to Pii-chan S2 - 04_post96_full_trace.log`, `przebieg_tłumaczenia_post96.txt`.
   - 1 plik źródłowy EN: `EN_Sasaki to Pii-chan S2 - 04.ass`.
   - 10 plików kodu produkcyjnego: `translator.py`, `profiler.py`, `scene_discourse.py`, `series_memory.py`, `verifier.py`, `avt_linter.py`, `sign_detector.py`, `metadata.py`, `flight_recorder.py`, `rules.py`.
   Zapisz uzyskane wartości w notatniku roboczym.

3. **Pomiar stanu bazowego (przed modyfikacjami 9.7):**
   - tryb szybki: `.\.venv\Scripts\python.exe -m pytest` (oczekiwane: 195 passed, 0 failed, 0 error, ~20,18 s)
   - tryb pełny: `.\.venv\Scripts\python.exe -m pytest -m ""` (oczekiwane: 348 passed, 0 failed, 0 error, ~15,2 min)
   - Wpisz uzyskane wyniki w **Sekcji 4 (`4A. Tryb fast` i `4B. Tryb full`)** pliku `Raport_wdrozenia_9.7.md`.

### KROK 0B: Wykonanie Fazy 0 (Obowiązkowa weryfikacja kodu i flag 0.L–0.O)

Zgodnie z sekcją `FAZA 0 — CZYTANIE KODU (OBOWIĄZKOWA)` w `Prompt_9.7.md`:

1. Przeczytaj w całości pliki z listy `P0.1`: `translator.py` (linie 4500, 5785-5800), `series_memory.py` (linie ~5366, ~6224 — `map_bilingual_role_aliases`, `populate_secondary_actor_tags`, `_sanitize_loaded_bible_in_ram`), `verifier.py` (linie ~455, ~992 — `normalize_phase2_line_and_reason`, `verify_batch`), `profiler.py` (linie 348-431 — `sanitize_event_asr`).
2. Zlokalizuj dokładne linie kodu i sygnatury metod, a następnie wypełnij **Tabelę P0.2 (Mapowanie plan ↔ kod)** oraz **Sekcję 2.3 (Lista rozbieżności)** w `Raport_wdrozenia_9.7.md`.
3. Dobierz dane testowe z `SeriesBible` / `en_text` odcinka testowego (innego niż odcinek audytowany, przy zachowaniu 100% rygoru Zero-Literal i Zero-Onomastic Leakage) i wypełnij **Tabelę P0.3** w `Raport_wdrozenia_9.7.md`.
4. Rozstrzygnij i udokumentuj w **Sekcji 2.4** pliku `Raport_wdrozenia_9.7.md` wszystkie cztery flagi weryfikacyjne:
   - **FLAGA PHASE 0.L** (przyczyna czterokrotnej duplikacji dwuczłonowego antroponimu w ID: 48 i ID: 52 oraz dopisania aliasów do wszystkich 22 postaci P0) — zidentyfikuj dokładne linie `translator.py:5785-5800` i `series_memory.py:6224` (`map_bilingual_role_aliases`).
   - **FLAGA PHASE 0.M** (inferencja płci leksykalnej w `SeriesBible.populate_secondary_actor_tags`) — zidentyfikuj, dlaczego `Boy` i `Girl` dostają `UNKNOWN` zamiast odpowiednio `MALE`/`FEMALE`.
   - **FLAGA PHASE 0.N** (porównywanie `Szkic` vs `Szlif` przy różnicy wyłącznie spacja vs `\N`) — zidentyfikuj warunek wypisujący `[Redaktor Dialogów]` w `translator.py:4500` i porównanie `f1_pl` vs `refined_pl` w `verifier.py:455`.
   - **FLAGA PHASE 0.O** (artefakty `.? ??000` wewnątrz japońskiego segmentu ASR) — zidentyfikuj kolejność czyszczenia `jp_part` w `profiler.py:348-431`.

**WARUNEK PRZEJŚCIA DO KROKU 1:** Tabele P0.2, P0.3, Sekcja 2.3 i Sekcja 2.4 wypełnione 100%. Brak wypełnienia = NIE PRZECHODŹ DALEJ.

### KROK 1: Implementacja operacji w kodzie produkcyjnym (Zgodnie z Sekcją 2 i Sekcją 4 `Prompt_9.7.md`)

Wdróż wszystkie operacje w kolejności określonej w Sekcji 4 `Prompt_9.7.md`:

1. **Etap Wdrożeniowy 2 — `OPERACJA 2C.1` (`translator.py` + `series_memory.py`):**
   - **Selektywne dopasowanie aliasu z tytułu serii w `SeriesBible` (`series_memory.py`):**
     - W `map_bilingual_role_aliases` / `_sanitize_loaded_bible_in_ram` **nigdy nie dopisuj** aliasu wyodrębnionego z `title_romaji` (np. `<RZECZYWISTY_ALIAS_JAPOŃSKI_1>` / `<RZECZYWISTY_RDZEŃ_PO_ODCIĘCIU_1>`) do wszystkich postaci w pętli.
     - Przypisz go **wyłącznie** do tej pojedynczej encji w `self.data["characters"]`, której kanoniczna nazwa `char_name` (lub istniejący opis) dzieli z rdzeniem aliasu `<RZECZYWISTY_RDZEŃ_PO_ODCIĘCIU_1>` wspólny prefiks fonetyczny (np. `char_name.lower().startswith(stem.lower()[:2])` przy `" " not in char_name`).
     - Oczyść w `_sanitize_loaded_bible_in_ram` tablice `aliases` pozostałych postaci P0 z omyłkowo dopisanych obcych aliasów.
   - **Całkowita blokada rozwijania części składowych antroponimów wieloczłonowych (`translator.py`, `series_memory.py`):**
     - Usuń duplikujące wywołanie podmiany aliasów po `AVTLinter (D_pos)` w `translator.py:5785-5800` — po zakończeniu `AVTLinter` i `EpisodeQualityGate` żaden kod nie może już mutować nazw własnych poza kontrolą `dpos_text` (`ass_text` musi być w 100% zgodny z `dpos_text` po uwzględnieniu jawnie zalogowanych poprawek EQG).
     - W funkcji zamieniającej japoński alias z honoryfikatorem (`-chan` / `-kun`) na kanoniczny paradygmat przy `keep_honorifics: false`:
       - operacja może dotyczyć **wyłącznie** tokenów posiadających wprost sufiks honoryfikatywny (`-chan`, `-kun`, `-sama`, `-san`) lub obciętego rdzenia hipokorystycznego, który **nie jest** częścią składową (`char_name.split()`) żadnego wieloczłonowego antroponimu (`" " in char_name`).
       - jeśli w zdaniu polskim występuje już którykolwiek człon kanonicznej nazwy encji (`any(part.lower() in text.lower() for part in char_name.split())` lub którykolwiek przypadek z `declensions[char_name].values()`), **nigdy nie wykonuj żadnej podmiany** dla tej encji (pełne poszanowanie Primary LLM Translation Authority — w ID: 48, ID: 52 i ID: 94 modele Fazy 1 i Fazy 2 same wygenerowały bezbłędne formy).

2. **Etap Wdrożeniowy 3 — `OPERACJA 2C.2` (`series_memory.py`):**
   - W `SeriesBible.populate_secondary_actor_tags` podczas tworzenia wpisu dla etykiety drugoplanowej sprawdź tokeny składowe nazwy etykiety (po `lower()`):
     - jeśli nazwa zawiera jednoznaczny angielski lub polski rzeczownik męski ze zbioru `{"boy", "man", "men", "guy", "male", "father", "dad", "brother", "son", "uncle", "grandfather", "waiter", "king", "prince", "lord", "chłopiec", "mężczyzna", "chłopak", "ojciec", "brat"}`, ustaw `"gender": "MALE"`, `"grammatical_gender": "MASCULINE"`, `"confidence": 0.90`, `"priority": "P1"`.
     - jeśli nazwa zawiera jednoznaczny rzeczownik żeński ze zbioru `{"girl", "woman", "women", "lady", "female", "mother", "mom", "sister", "daughter", "aunt", "grandmother", "waitress", "queen", "princess", "dziewczyna", "kobieta", "dziewczynka", "matka", "siostra"}`, ustaw `"gender": "FEMALE"`, `"grammatical_gender": "FEMININE"`, `"confidence": 0.90`, `"priority": "P1"`.

3. **Etap Wdrożeniowy 4 — `OPERACJA 2C.3` (`verifier.py` + `translator.py`):**
   - W funkcji porównującej `_norm_cmp(s)` w `DialogueVerifier.normalize_phase2_line_and_reason` (`verifier.py`) oprócz zdejmowania zewnętrznych tagów `{\i1}...{\i0}` zamieniaj każdy znacznik `\N` (wraz z otaczającymi spacjami `r"\s*\\N\s*"`) na pojedynczą spację `" "` i redukuj wielokrotne spacje `r"\s+"` do `" "`.
   - Jeśli po takiej normalizacji `_norm_cmp(f1_pl) == _norm_cmp(refined_pl)` (co oznacza, że słowa i interpunkcja nie uległy żadnej zmianie, a zmieniło się co najwyżej miejsce łamania wiersza `\N`), ustaw `changes_made = None` i **pomiń wypisywanie pustego bloku `[Redaktor Dialogów]` w konsoli** w `translator.py`.

4. **Etap Wdrożeniowy 4 (kontynuacja) — `OPERACJA 2C.4` (`profiler.py`):**
   - W `EpisodeProfiler.sanitize_event_asr` (`profiler.py`) na części japońskiej `jp_part` (przed wygenerowaniem `[romaji]`) dodaj wycinanie artefaktowych klastrów złożonych z wielokrotnych znaków zapytania/interpunkcji i zer/cyfr:
     ```python
     jp_part = re.sub(r"[.,!?\s]*\?+[\s?0-9.,!]*", "", jp_part)
     jp_part = re.sub(r"0{2,}", "", jp_part)
     ```
   - **UWAGA:** Przed wdrożeniem regexu sprawdź, czy nie usuwa prawidłowych znaków japońskich. Dodaj testy przypadków brzegowych w T7.4.

### KROK 2: Implementacja 4 nowych testów jednostkowych (`T7.1–T7.4`) + testu integracyjnego

**UWAGA:** Pełne szkielety kodu testów T7.1–T7.4 (z `import pytest`, `@pytest.mark.parametrize`, placeholderami `<RZECZYWISTY_*>`, pełnymi asercjami) znajdują się w pliku:
`C:\Users\Piotrek\Desktop\translator\Artefakty\ZADANIE_4_WALIDACJA_9.7.md` → sekcja `4.3. Rekord „Nowe testy"`.

Agent kodujący **powinien skorzystać z tych szkieletów jako wzorca strukturalnego** i dostosować je po Phase 0 (P0.2 — sygnatury metod):
- T7.1 wywołuje `bible.apply_canonical_alias_declension(...)` — jeśli metoda nie istnieje w kodzie, utwórz ją lub dostosuj test do istniejącej metody.
- T7.3 wywołuje `DialogueVerifier.is_lexically_identical_ignoring_linebreak(...)` — jeśli metoda nie istnieje, utwórz ją lub dostosuj test.

1. Zaimplementuj wszystkie 4 sparametryzowane testy jednostkowe (`T7.1–T7.4`) ze szkieletów strukturalnych z `ZADANIE_4_WALIDACJA_9.7.md` sekcja `4.3` w następujących plikach:
   - `tests/test_series_memory.py` (`T7.1`: `test_multi_token_anthroponym_immunity_against_component_alias_duplication_and_selective_title_alias`)
   - `tests/test_discourse_and_translator.py` (`T7.2`: `test_populate_secondary_actor_tags_infers_lexical_gender_for_boy_and_girl_tags`)
   - `tests/test_verifier.py` (`T7.3`: `test_normalize_phase2_treats_space_to_ass_newline_wrapping_as_lexical_identity`)
   - `tests/test_profiler.py` (`T7.4`: `test_sanitize_event_asr_strips_question_mark_and_zero_clusters_inside_jp_segment`)
2. Dodaj integracyjny test `test_standard_9_7_suite` w pliku `test_system.py` (analogicznie do `test_standard_9_4_suite` z wersji 9.4).
3. Zastąp wszystkie placeholdery `<RZECZYWISTY_*>` danymi z Tabeli P0.3 (pochodzącymi z odcinka testowego spoza audytu — 0 literalnych wycieków z odcinka audytowanego!).
4. Zweryfikuj empirycznie falsyfikowalność każdego z 4 testów (mutacja kodu → FAILED, przywrócenie → PASS) oraz brak anty-wzorców `D1–D6`.

### KROK 3: Przestrzeganie Sekcji 6 (`ZAKAZY 1–10`) i uruchomienie bramek CI/CD

Bezwzględnie przestrzegaj wszystkich 10 zakazów z Sekcji 6 `Prompt_9.7.md` (zakaz mutacji tekstu poza `AVTLinter`/`EQG`, zakaz podmiany członów antroponimów wieloczłonowych, zakaz globalnego dopisywania aliasów tytułowych, zakaz Test-Only Wiring, zakaz pomijania Phase 0 i walidacji empirycznej, zakaz naruszania 195 testów KEEP i 153 MARK_SLOW, zakaz modyfikacji `DEFENSIVE_FALLBACK` i `tests/archive/`, zakaz placeholderów w raporcie, zakaz modyfikacji `.ass`/`.json`, zakaz wycieku Zero-Literal).

Uruchom kolejno w terminalu:

```bash
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m pytest -m ""
.\.venv\Scripts\python.exe verify_purity.py
.\.venv\Scripts\python.exe verify_ultimate_pipeline.py
.\.venv\Scripts\python.exe verify_12_fixes.py
powershell -ExecutionPolicy Bypass -File audit_diff.ps1
```

**Oczekiwane wyniki:**
- `pytest` (fast): 100% PASSED (≥ 203 instancje testowe), 0 FAILED, 0 ERROR, czas < 60 s.
- `pytest -m ""` (full): 100% PASSED (≥ 356 instancji), 0 FAILED, 0 ERROR.
- 3 bramki `.py`: PASS 100%.
- `audit_diff.ps1`: VICTORY CONFIRMED.

**WARUNEK ZATRZYMANIA:** Jeśli którakolwiek bramka zwróci FAIL:
- Zatrzymaj wdrożenie.
- Wskaż w raporcie zwrotnym (KROK 5) dokładny błąd i plik.
- NIE PRZECHODŹ do KROKU 3A.

### KROK 3A: WALIDACJA EMPIRYCZNA (OBOWIĄZKOWA — WARUNEK (m) Prompt_9.7.md)

Po uzyskaniu wszystkich zielonych bramek CI/CD z KROKU 3 wykonaj walidację empiryczną na odcinku audytowanym.

1. **Freeze SHA256 baseline** (przed uruchomieniem re-tłumaczenia):
   - `C:\Users\Piotrek\Desktop\translator\Artefakty\Sasaki to Pii-chan S2 - 04_post96.ass` (baseline po 9.6)
   - `C:\Users\Piotrek\Desktop\translator\Artefakty\Sasaki to Pii-chan S2 - 04_post96_full_trace.log` (baseline po 9.6)
   - `C:\Users\Piotrek\Desktop\translator\Artefakty\przebieg_tłumaczenia_post96.txt` (baseline po 9.6)
   - `C:\Users\Piotrek\Desktop\translator\Artefakty\EN_Sasaki to Pii-chan S2 - 04.ass` (źródło EN do re-tłumaczenia)
   Zapisz uzyskane sumy SHA256 w Sekcji 6C Raportu 9.7.

2. **Re-tłumaczenie Sasaki to Pii-chan S2-04 w trybie Mistrzowskim (opcja 3 — gemini-3.8-flash CoT 6144):**
   - Uruchom `translator.py` z parametrem `subs_path` wskazującym na plik źródłowy EN:
     `C:\Users\Piotrek\Desktop\translator\Artefakty\EN_Sasaki to Pii-chan S2 - 04.ass`
   - Zapisz wyjście jako `C:\Users\Piotrek\Desktop\translator\Artefakty\Sasaki to Pii-chan S2 - 04_post97.ass` (NIE nadpisuj baseline).
   - Zapisz log jako `C:\Users\Piotrek\Desktop\translator\Artefakty\Sasaki to Pii-chan S2 - 04_post97_full_trace.log`.
   - Zapisz pełny przebieg konsolowy jako `C:\Users\Piotrek\Desktop\translator\Artefakty\przebieg_tłumaczenia_post97.txt`.

3. **Porównanie 5 pozycji z audytu 9.6 (kryteria WYELIMINOWANY):**

| Pozycja | Operacja | Kryterium WYELIMINOWANY | Miejsce w baseline |
|---|---|---|---|
| 1. Duplikacja antroponimu + globalne aliasy | 2C.1 | ID: 48 i ID: 52 mają pojedyncze `<IMIE_N/D> <NAZWISKO>` (0 duplikacji); `aliases` w Kroku 6 tylko dla encji pasującej fonetycznie | ID: 48, ID: 52, Krok 6 |
| 2. Płeć leksykalna P2 | 2C.2 | `Boy` → `MALE`/`MASCULINE`, `Girl` → `FEMALE`/`FEMININE` w `populate_secondary_actor_tags`; ID: 58 ma `Adresat: Boy (MASCULINE)` | ID: 58 |
| 3. Kursywa całoliniowa (kontrola regresji z 9.6) | 2A.4 | ID: 187 bez całoliniowego `{\i1}...{\i0}`; ID: 26 z kursywą częściową | ID: 187, ID: 26 |
| 4. `\N` vs spacja | 2C.3 | 0 pustych wpisów `[Redaktor Dialogów]` dla linii różniących się wyłącznie `\N` vs spacja | Paczka 3 #6, #16, Paczka 2 #13 |
| 5. Artefakty `.? ??000` | 2C.4 | 0 artefaktów `.? ??000` w `JP Audio (Whisper):`; ID: 79 czyste | ID: 79 |

4. **Wypełnij Sekcję 6C w `Raport_wdrozenia_9.7.md`:**
   - Tabela 5 wierszy z kolumnami: Zagadnienie / Operacja / Stan w post96 / Stan po 9.7 / Status.
   - Status każdego zagadnienia: `WYELIMINOWANY` / `CZĘŚCIOWO` / `POZOSTAŁ`.
   - SHA256 nowych plików (`_post97.ass`, `_post97_full_trace.log`, `przebieg_tłumaczenia_post97.txt`).

5. **WARUNEK ZATRZYMANIA:** Jeśli którekolwiek z 5 pozycji ma status `CZĘŚCIOWO` lub `POZOSTAŁ`:
   - **NIE zgłaszaj sukcesu.**
   - W Raporcie 9.7 w sekcji 1 `Status wdrożenia` wpisz: `CZĘŚCIOWO WDROŻONE — [liczba] pozycji pozostało, wymaga iteracji 9.8`.
   - W raporcie zwrotnym (KROK 5) wskaż, która pozycja pozostała i jaką ma przyczynę systemową.

### KROK 4: Kompletne wypełnienie `Raport_wdrozenia_9.7.md`

Otwórz plik `C:\Users\Piotrek\Desktop\translator\Artefakty\Raport_wdrozenia_9.7.md` i:
1. Wypełnij wszystkie sekcje i pola `<DO_WYPEŁNIENIA_*>`:
   - Sekcję 1 (metadane, data, commit hash, status),
   - Sekcję 2 (`2.1 Tabela P0.2`, `2.2 Tabela P0.3`, `2.3 Lista rozbieżności`, `2.4 Weryfikacja flag Phase 0.L–0.O`),
   - Sekcję 4 (`4A` i `4B` — stan bazowy),
   - Sekcję 6 (`6A`, `6B` — stan końcowy oraz `6C` — tabela walidacji empirycznej 5 pozycji z audytu 9.6),
   - Sekcję 7 i Sekcję 8 (weryfikacja `D1–D6` dla `T7.1–T7.4`),
   - Sekcję 10 i Sekcję 11 (zaznaczenie wszystkich pozycji `[x]` na listach kontrolnych).
2. Zweryfikuj komendą:
   `Select-String -Path "C:\Users\Piotrek\Desktop\translator\Artefakty\Raport_wdrozenia_9.7.md" -Pattern "DO_WYPEŁNIENIA"`
   że w pliku raportu pozostało dokładnie **0 niewypełnionych placeholderów**. Jeśli > 0, wróć do KROKU 4 pkt 1 i uzupełnij brakujące pola.
3. Zweryfikuj, że w `Raport_wdrozenia_9.6.md` pola `Commit wdrożenia` i `Status wdrożenia` NIE zawierają wartości `HEAD` / `W TOKU` (muszą zawierać `c87b22f` i status `FORMALNIE WDROŻONE, 4/5 WYELIMINOWANE, 1 REGRESJA`).

### KROK 5: RAPORT ZWROTNY (CO AGENT MA ODESŁAĆ)

Po zakończeniu wdrożenia (KROKI 0–4) i walidacji empirycznej (KROK 3A) odeszlij:

1. **Podsumowanie** — 1–2 akapity: co zostało wdrożone, główne rozbieżności „plan mówi X, kod ma Y".
2. **Ścieżki zapisanych plików:**
   - `C:\Users\Piotrek\Desktop\translator\Artefakty\Raport_wdrozenia_9.7.md` (wypełniony)
   - `C:\Users\Piotrek\Desktop\translator\Artefakty\Sasaki to Pii-chan S2 - 04_post97.ass`
   - `C:\Users\Piotrek\Desktop\translator\Artefakty\Sasaki to Pii-chan S2 - 04_post97_full_trace.log`
   - `C:\Users\Piotrek\Desktop\translator\Artefakty\przebieg_tłumaczenia_post97.txt`
3. **SHA256** wszystkich czterech plików + commit hash.
4. **Status każdego z 5 zagadnień** (1–5): `WYELIMINOWANY` / `CZĘŚCIOWO` / `POZOSTAŁ` z krótkim uzasadnieniem (1 linia każdy).
5. **Liczba RUNTIME ORPHANS wpiętych** (z Phase 0 lista vs zrealizowane — jeśli dotyczy).
6. **Lista rozbieżności „plan mówi X, kod ma Y"** — wszystkie z Phase 0 + napotkane w trakcie implementacji.
7. **Flagi niespełnionych warunków ukończenia** (jeśli jakieś).
8. **Data i godzina zakończenia wdrożenia.**

---

**KONIEC ROZKAZU WYKONAWCZEGO 9.7.**