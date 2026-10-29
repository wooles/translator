# ROZKAZ WYKONAWCZY DLA AGENTA KODUJĄCEGO: WDROŻENIE PROMPTU NAPRAWCZEGO 9.8

## 1. PLIKI WEJŚCIOWE I DOCELOWE (ARTEFAKTY)

Twoim zadaniem jest pełne wdrożenie specyfikacji architektonicznej **Wersji 9.8** (mikro-domknięcie operacji 2C.2 z 9.7), aktualizacja statusu audytowego w raporcie wersji 9.7, udokumentowanie wdrożenia 9.8 w nowym raporcie wdrożeniowym oraz **przeprowadzenie walidacji empirycznej na odcinku audytowanym**.

### Pliki do odczytu / zapisu (Write/Update):
1. **Specyfikacja do wdrożenia (Read):**
   `C:\Users\Piotrek\Desktop\translator\Artefakty\Prompt_9.8.md`
   - Sekcja 5 (Wykaz nowego testu T8.1) — **pełny szkielet kodu testu** (import pytest, @pytest.mark.parametrize, placeholdery, asercje).
2. **Szkielet raportu wersji 9.8 do całkowitego wypełnienia (Write):**
   `C:\Users\Piotrek\Desktop\translator\Artefakty\Raport_wdrozenia_9.8.md`
3. **Raport wersji 9.7 do aktualizacji statusu, Sekcji 6C i dopisania Sekcji 12 (Update):**
   `C:\Users\Piotrek\Desktop\translator\Artefakty\Raport_wdrozenia_9.7.md`
4. **Dokument referencyjny — rekordy walidacji testowej i gotowa Sekcja 12 do Raportu 9.7 (Read):**
   `C:\Users\Piotrek\Desktop\translator\Artefakty\ZADANIE_4_WALIDACJA_9.8.md`
   - Sekcja `4.10. Aktualizacja statusu i Sekcji 12 w Raport_wdrozenia_9.7.md` — **gotowa treść Sekcji 12 do wklejenia 1:1** (nie tylko instrukcja, co zmienić).
   - Sekcja `4.3. Rekord „Nowe testy"` — odesłanie do `Prompt_9.8.md` Sekcja 5 (bez duplikatu szkieletu T8.1).

### Pliki baseline odcinka audytowanego (Read, BEZWZGLĘDNIE NIETYKALNE):
5. `C:\Users\Piotrek\Desktop\translator\Artefakty\Sasaki to Pii-chan S2 - 04_post97.ass` (baseline `.ass` po 9.7)
6. `C:\Users\Piotrek\Desktop\translator\Artefakty\Sasaki to Pii-chan S2 - 04_post97_full_trace.log` (baseline `.log` po 9.7)
7. `C:\Users\Piotrek\Desktop\translator\Artefakty\przebieg_tłumaczenia_post97.txt` (baseline przebiegu po 9.7)

### Plik źródłowy EN do re-tłumaczenia (Read — źródło wejściowe KROKU 3A):
8. `C:\Users\Piotrek\Desktop\translator\Artefakty\EN_Sasaki to Pii-chan S2 - 04.ass` (oryginalne napisy angielskie odcinka)

### Kontekst historyczny (opcjonalny, do cross-reference ZAKAZÓW):
9. `C:\Users\Piotrek\Desktop\translator\Artefakty\Prompt_9.7.md` — ZAKAZY 1–10 z Sekcji 6 obowiązują w 9.8 bez zmian.

Przeczytaj `Prompt_9.8.md`, `Raport_wdrozenia_9.8.md` oraz `ZADANIE_4_WALIDACJA_9.8.md` w całości przed podjęciem jakichkolwiek działań w repozytorium.

---

## 2. CEL INŻYNIERYJNY WERSJI 9.8

Wdrożenie wersji 9.7 (`commit 1e27a17`) wyeliminowało 4 z 5 zagadnień z audytu 9.6 (duplikacja antroponimu, `\N` vs spacja, artefakty `.? ??000`, regresje 2A.1–2A.7), ale pozostawiło **1 mikro-lukę w runtime w operacji 2C.2**. Audyt 9.7 zdiagnozował ją precyzyjnie jako **trójstopniowy mechanizm**:

1. **`populate_secondary_actor_tags`** (`series_memory.py:6287, 6299`): etykiety leksykalne `Boy`, `Girl`, `Man`, `Woman` mają `has_verified_gender: False` (mimo poprawnej płci `MALE`/`FEMALE`).
2. **`audit_speaker_metadata_against_audio`** (`translator.py:2911, 2945`): wywołana z `_resolve_line_addressee`, widzi `has_verified_gender: False` i **traktuje `Boy` jako niezweryfikowany tag**, nadpisując płeć na `FEMALE` pod wpływem `scene_gender="FEMALE"` → `Adresat: Boy (FEMININE)` w ID: 58.
3. **`_precompute_episode_scene_genders`** (`translator.py:1788-1793`): `female_only_scene: True` z `dramatic_sequences` ustawia `episode_scene_genders[orig_idx] = "kobieta"` dla całego przedziału czasowego, nie sprawdzając, czy w linii mówi mężczyzna → `Grupa_1os_lm: NON_VIRILE` na liniach mówców męskich (ID: 36–60).

**Cel 9.8:** Trzyetapowe domknięcie — flaga `has_verified_gender: True` dla etykiet leksykalnych, early return w `audit_speaker_metadata_against_audio`, wykluczenie `is_fem_scene` / `NON_VIRILE` w obecności mówcy lub adresata męskiego.

---

## 3. BEZWZGLĘDNA PROCEDURA WYKONANIA (KROK PO KROKU)

### KROK 0A: Aktualizacja `Raport_wdrozenia_9.7.md` oraz pomiar stanu bazowego PRZED modyfikacjami 9.8

Zanim zmodyfikujesz kod produkcyjny:

1. **Aktualizacja Raportu 9.7:**

   **UWAGA:** Pełna treść Sekcji 12 do wklejenia do `Raport_wdrozenia_9.7.md` znajduje się w pliku:
   `C:\Users\Piotrek\Desktop\translator\Artefakty\ZADANIE_4_WALIDACJA_9.8.md` → sekcja `4.10. Aktualizacja statusu i Sekcji 12 w Raport_wdrozenia_9.7.md`.
   Skopiuj ją **1:1** do końca `Raport_wdrozenia_9.7.md`.

   Otwórz `C:\Users\Piotrek\Desktop\translator\Artefakty\Raport_wdrozenia_9.7.md`:
   - w Sekcji 1 zmień pole `Status wdrożenia` na:
     `FORMALNIE WDROŻONE (204/204 fast, 357/357 full, 4 bramki PASS), 3/4 KATEGORII WYELIMINOWANE W 100%, 1 MIKRO-LUKA W 2C.2 (ID: 58) — domknięcie w 9.8`.
   - w Sekcji 6C w wierszu `Kategoria Problemu 2` (`2C.2`) zaktualizuj status na: `CZĘŚCIOWO (poprawne MALE/FEMALE w Kroku 6 i ID: 59–60, lecz w ID: 58 audit_speaker_metadata_against_audio nadpisało płeć Boy przez brak has_verified_gender: True)`.
   - na końcu pliku wklej **kompletną Sekcję 12** z `ZADANIE_4_WALIDACJA_9.8.md` sekcja 4.10.

2. **Freeze SHA256 baseline PRZED zmianami:**
   Zapisz sumy SHA256 dla następujących plików (do porównania po walidacji empirycznej):
   - 3 pliki baseline: `Sasaki to Pii-chan S2 - 04_post97.ass`, `Sasaki to Pii-chan S2 - 04_post97_full_trace.log`, `przebieg_tłumaczenia_post97.txt`.
   - 1 plik źródłowy EN: `EN_Sasaki to Pii-chan S2 - 04.ass`.
   - 2 pliki kodu produkcyjnego modyfikowane w 9.8: `series_memory.py`, `translator.py`.
   - 1 plik testowy modyfikowany w 9.8: `tests/test_discourse_and_translator.py`.
   Zapisz uzyskane wartości w notatniku roboczym.

3. **Pomiar stanu bazowego (przed modyfikacjami 9.8):**
   - tryb szybki: `.\.venv\Scripts\python.exe -m pytest` (oczekiwane: 204 passed, 153 deselected, ~22,84 s)
   - tryb pełny: `.\.venv\Scripts\python.exe -m pytest -m ""` (oczekiwane: 357 passed, 0 failed, 0 error)
   - Wpisz uzyskane wyniki w **Sekcji 4 (`4A. Tryb fast` i `4B. Tryb full`)** pliku `Raport_wdrozenia_9.8.md`.

### KROK 0B: Wykonanie Fazy 0 (Obowiązkowa weryfikacja kodu i Flagi 0.P)

Zgodnie z sekcją `FAZA 0 — CZYTANIE KODU (OBOWIĄZKOWA)` w `Prompt_9.8.md`:

1. Przeczytaj w całości:
   - `series_memory.py` — `populate_secondary_actor_tags` (`linia ~6253`), `audit_speaker_metadata_against_audio` (cała funkcja), `masculine_lexicon` / `feminine_lexicon` (stałe modułowe).
   - `translator.py` — `_precompute_episode_scene_genders` (`linie 1775-1850`), `_resolve_line_addressee` (`linie 2890-2950`), `_prepare_batch_prompt` (`linie 3045-3165`), `_process_single_batch` (`linie 3950-4035`).
2. Zlokalizuj dokładne linie kodu i sygnatury metod, a następnie wypełnij **Tabelę P0.2 (Mapowanie plan ↔ kod)** oraz **Sekcję 2.3 (Lista rozbieżności)** w `Raport_wdrozenia_9.8.md`.
3. Dobierz dane testowe z `SeriesBible` / `en_text` odcinka testowego (innego niż odcinek audytowany, przy zachowaniu 100% rygoru Zero-Literal i Zero-Onomastic Leakage) i wypełnij **Tabelę P0.3** w `Raport_wdrozenia_9.8.md`.
4. Rozstrzygnij i udokumentuj w **Sekcji 2.4** pliku `Raport_wdrozenia_9.8.md` **Flagę 0.P**:
   - **FLAGA PHASE 0.P** (interakcja `populate_secondary_actor_tags` z `audit_speaker_metadata_against_audio` oraz `is_fem_scene` w `translator.py`):
     - Dlaczego w `_resolve_line_addressee` (`translator.py:2911, 2945`) wywołanie `audit_speaker_metadata_against_audio` zmieniło płeć `next_spk = "Boy"` z `"MALE"` na `"FEMALE"` przy `next_sc_g = "FEMALE"`.
     - Dlaczego w `_prepare_batch_prompt` (`translator.py:3145`) i `_process_single_batch` (`translator.py:3960, 4000`) zmienna `is_fem_scene` pozostawała `True` na liniach, w których mówcą lub adresatem jest postać męska (`MALE` / `MASCULINE`).

**WARUNEK PRZEJŚCIA DO KROKU 1:** Tabele P0.2, P0.3, Sekcja 2.3 i Sekcja 2.4 (z Flagą 0.P) wypełnione 100%. Brak wypełnienia = NIE PRZECHODŹ DALEJ.

### KROK 1: Implementacja operacji 2C.1 (Zgodnie z Sekcją 2 `Prompt_9.8.md`)

Wdróż wszystkie 3 podkroki operacji 2C.1:

1. **Twarda weryfikacja leksykalna (`series_memory.py`):**
   W `SeriesBible.populate_secondary_actor_tags` dla etykiet dopasowanych do `masculine_lexicon` lub `feminine_lexicon` (takich jak `Boy`, `Girl`, `Man`, `Woman`) ustaw:
   - `"has_verified_gender": True`
   - `"confidence": 0.95`
   - (płeć i `grammatical_gender` — zgodnie z leksykonem, bez zmian)

   Uzasadnienie: słownikowe znaczenie rzeczownika pospolitego oznaczającego płeć ludzką stanowi **twardy niezmiennik leksykalny** i nie podlega odwróceniu przez estymację akustyczną ani statystykę sceny.

2. **Ochrona etykiet o inherentnej płci leksykalnej (`series_memory.py`, `audit_speaker_metadata_against_audio`):**
   Na samym początku `SeriesBible.audit_speaker_metadata_against_audio(speaker_name, ...)`:
   ```python
   if speaker_name in self.data["characters"]:
       char = self.data["characters"][speaker_name]
       if char.get("has_verified_gender") is True:
           canonical_gender = char.get("gender", "UNKNOWN")
           return (canonical_gender, False)

   speaker_tokens = set(speaker_name.lower().split())
   if speaker_tokens & (INHERENT_MALE_NOUNS | INHERENT_FEMALE_NOUNS):
       canonical_gender = "MALE" if speaker_tokens & INHERENT_MALE_NOUNS else "FEMALE"
       return (canonical_gender, False)
   ```
   gdzie `INHERENT_MALE_NOUNS` i `INHERENT_FEMALE_NOUNS` — stałe modułowe w `series_memory.py` (zbiory rzeczowników pospolitych oznaczających płeć ludzką, w tym `boy`, `man`, `girl`, `woman` — pełna lista w `Prompt_9.8.md` Sekcja 2 → 2C.1 → Implementacja punkt 2).

3. **Wykluczenie `is_fem_scene=True` i `NON_VIRILE` w obecności mówcy lub adresata męskiego (`translator.py`):**

   a. **W `_precompute_episode_scene_genders`** (`translator.py:1788-1793`):
   Po przypisaniu `scene_genders` z `dramatic_sequences`, dla każdego zdarzenia `(orig_idx, ev)` sprawdź płeć jawnego aktora `ev.name` w `SeriesBible` / `resolve_actor_gender`:
   ```python
   if actor_gender == "MALE":
       scene_genders[orig_idx] = "mężczyzna"
   ```
   Pojedyncza kwestia wypowiadana przez mężczyznę nigdy nie ma `scene_gender == "kobieta"`.

   b. **W `_prepare_batch_prompt`** (`translator.py:3045, 3145`) i **`_process_single_batch`** (`translator.py:3960, 4000`):
   Zdefiniuj:
   ```python
   has_male_participant_in_line = (
       spk_gram_tag == "MASCULINE"
       or tgt_gram_tag == "MASCULINE"
       or line_spk_gender == "mężczyzna"
       or line_addr_cat in ["mężczyzna", "mężczyzna_dual", "grupa_mężczyzn"]
   )
   if has_male_participant_in_line:
       is_fem_scene = False
       if line_pl_grp == "NON_VIRILE":
           line_pl_grp = "VIRILE"
   ```

### KROK 2: Implementacja testu jednostkowego `T8.1` + testu integracyjnego

**UWAGA:** Pełny szkielet testu T8.1 (z `import pytest`, `@pytest.mark.parametrize`, placeholderami `<RZECZYWISTY_*>` i asercjami) znajduje się w pliku:
`C:\Users\Piotrek\Desktop\translator\Artefakty\Prompt_9.8.md` → Sekcja 5 → Wykaz nowego testu T8.1 (marker: unit).
Plik `ZADANIE_4_WALIDACJA_9.8.md` → sekcja 4.3 zawiera wyłącznie odesłanie do tego szkieletu (bez duplikatu).

1. **Test jednostkowy `T8.1`** w pliku `tests/test_discourse_and_translator.py`:
   - Nazwa: `test_secondary_lexical_gender_immunity_against_scene_gender_override_and_male_speaker_non_virile_ban`
   - Marker: `unit`
   - Parametryzacja: `Boy` + `scene_gender_override=FEMALE` → oczekiwane `MALE`/`MASCULINE`; `Girl` + `scene_gender_override=MALE` → oczekiwane `FEMALE`/`FEMININE`.
   - Asercje: `has_verified_gender is True`; `audit_speaker_metadata_against_audio` zwraca `(expected_audited_gender, False)`; mutacja NIE nastąpiła; `arbitrate_event_telemetry(... target_actor=f"{tag} (Kobieta)", scene_female_only=True ...)` → `target_gender == expected_telemetry_gender`.

2. **Test integracyjny `test_standard_9_8_suite`** w `test_system.py` (analogicznie do `test_standard_9_4_suite` z wersji 9.4 i `test_standard_9_7_suite` z 9.7).

3. Zastąp wszystkie placeholdery `<RZECZYWISTY_*>` danymi z Tabeli P0.3 (pochodzącymi z odcinka testowego spoza audytu — 0 literalnych wycieków z odcinka audytowanego!).

4. Zweryfikuj empirycznie falsyfikowalność `T8.1` (mutacja kodu → FAILED, przywrócenie → PASS) oraz brak anty-wzorców `D1–D6`.

### KROK 3: Przestrzeganie ZAKAZÓW 1–10 z `Prompt_9.7.md` i uruchomienie bramek CI/CD

Bezwzględnie przestrzegaj **wszystkich 10 zakazów z Sekcji 6 `Prompt_9.7.md`** (dziedziczone przez 9.8 bez zmian — `Prompt_9.8.md` nie zawiera sekcji ZAKAZÓW explicite, ale 9.8 jest mikro-iteracją 9.7 i dziedziczy wszystkie ograniczenia):
1. Zakaz mutacji tekstu poza `AVTLinter` i `EpisodeQualityGate`.
2. Zakaz podmiany członów antroponimów wieloczłonowych.
3. Zakaz globalnego dopisywania aliasów tytułowych.
4. Zakaz Test-Only Wiring i mockowania logiki domenowej w testach.
5. Zakaz pomijania Phase 0 i walidacji empirycznej.
6. Zakaz naruszania 204 testów `KEEP` i 153 `MARK_SLOW`.
7. Zakaz modyfikacji `DEFENSIVE_FALLBACK` i `tests/archive/`.
8. Zakaz pozostawiania placeholderów w raporcie.
9. Zakaz modyfikacji `.ass`/`.json` (Zero-Cosmetic).
10. Zakaz wycieku Zero-Literal.

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
- `pytest` (fast): 100% PASSED (≥ 206 instancji testowych), 0 FAILED, 0 ERROR, czas < 60 s.
- `pytest -m ""` (full): 100% PASSED (≥ 359 instancji), 0 FAILED, 0 ERROR.
- 3 bramki `.py`: PASS 100%.
- `audit_diff.ps1`: VICTORY CONFIRMED.

**WARUNEK ZATRZYMANIA:** Jeśli którakolwiek bramka zwróci FAIL:
- Zatrzymaj wdrożenie.
- Wskaż w raporcie zwrotnym (KROK 5) dokładny błąd i plik.
- NIE PRZECHODŹ do KROKU 3A.

### KROK 3A: WALIDACJA EMPIRYCZNA (OBOWIĄZKOWA)

Po uzyskaniu wszystkich zielonych bramek CI/CD z KROKU 3 wykonaj walidację empiryczną na odcinku audytowanym.

1. **Freeze SHA256 baseline** (przed uruchomieniem re-tłumaczenia):
   - `C:\Users\Piotrek\Desktop\translator\Artefakty\Sasaki to Pii-chan S2 - 04_post97.ass` (baseline po 9.7)
   - `C:\Users\Piotrek\Desktop\translator\Artefakty\Sasaki to Pii-chan S2 - 04_post97_full_trace.log` (baseline po 9.7)
   - `C:\Users\Piotrek\Desktop\translator\Artefakty\przebieg_tłumaczenia_post97.txt` (baseline po 9.7)
   - `C:\Users\Piotrek\Desktop\translator\Artefakty\EN_Sasaki to Pii-chan S2 - 04.ass` (źródło EN)
   Zapisz uzyskane sumy SHA256 w Sekcji 6C Raportu 9.8.

2. **Re-tłumaczenie Sasaki to Pii-chan S2-04 w trybie Mistrzowskim (opcja 3 — gemini-3.8-flash CoT 6144):**
   - Uruchom `translator.py` z parametrem `subs_path` wskazującym na plik źródłowy EN:
     `C:\Users\Piotrek\Desktop\translator\Artefakty\EN_Sasaki to Pii-chan S2 - 04.ass`
   - Zapisz wyjście jako `C:\Users\Piotrek\Desktop\translator\Artefakty\Sasaki to Pii-chan S2 - 04_post98.ass` (NIE nadpisuj baseline).
   - Zapisz log jako `C:\Users\Piotrek\Desktop\translator\Artefakty\Sasaki to Pii-chan S2 - 04_post98_full_trace.log`.
   - Zapisz pełny przebieg konsolowy jako `C:\Users\Piotrek\Desktop\translator\Artefakty\przebieg_tłumaczenia_post98.txt`.

3. **Porównanie mikro-luki 2C.2 (kryteria WYELIMINOWANY):**

| Pozycja | Miejsce w baseline post97 | Kryterium WYELIMINOWANY w post98 |
|---|---|---|
| `Adresat: Boy` | ID: 58 (`0:04:56.83`) → `Boy (FEMININE)` | `Adresat: Boy (MASCULINE)` — 0 wystąpień `Boy (FEMININE)` w całym logu |
| `Grupa_1os_lm: NON_VIRILE` na mówcy MALE | ID: 36–60 (linie mówców męskich) | 0 wystąpień `Grupa_1os_lm: NON_VIRILE` na liniach z `Mówca: <ANTROPONIM> (MASCULINE)` |
| Kontrola regresji 9.7 (2C.1) | ID: 48, ID: 52 | `<RZECZYWISTY_ANTROPONIM_DWUCZŁONOWY_1>` pojedyncze wystąpienie (0 duplikacji) |
| Kontrola regresji 9.7 (2C.3) | 0 pustych `[Redaktor Dialogów]` w post97 | 0 pustych `[Redaktor Dialogów]` |
| Kontrola regresji 9.7 (2C.4) | 0 artefaktów `.? ??000` w post97 | 0 artefaktów `.? ??000` |
| Kontrola regresji 2A.1–2A.7 | 100% napraw z 9.5/9.6 | `events_count == total_lines == 260`; 0 małych `\n`; 0 całoliniowych kursyw w ID: 187; 100% telemetrii P0 |

4. **Wypełnij Sekcję 6C w `Raport_wdrozenia_9.8.md`:**
   - Tabela 2 wierszy dla mikro-luki + 4 wierszy kontroli regresji.
   - Status każdego zagadnienia: `WYELIMINOWANY` / `CZĘŚCIOWO` / `POZOSTAŁ`.
   - SHA256 nowych plików (`_post98.ass`, `_post98_full_trace.log`, `przebieg_tłumaczenia_post98.txt`).

5. **WARUNEK ZATRZYMANIA:** Jeśli mikro-luka 2C.2 ma status `CZĘŚCIOWO` lub `POZOSTAŁ`:
   - **NIE zgłaszaj sukcesu.**
   - W Raporcie 9.8 w sekcji 1 `Status wdrożenia` wpisz: `CZĘŚCIOWO WDROŻONE — mikro-luka 2C.2 pozostała, wymaga iteracji 9.9`.
   - W raporcie zwrotnym (KROK 5) wskaż, co konkretnie nie zadziałało.

### KROK 4: Kompletne wypełnienie `Raport_wdrozenia_9.8.md`

Otwórz plik `C:\Users\Piotrek\Desktop\translator\Artefakty\Raport_wdrozenia_9.8.md` i:
1. Wypełnij wszystkie sekcje i pola `<DO_WYPEŁNIENIA_*>`:
   - Sekcję 1 (metadane, data, commit hash, status),
   - Sekcję 2 (`2.1 Tabela P0.2`, `2.2 Tabela P0.3`, `2.3 Lista rozbieżności`, `2.4 Flaga 0.P`),
   - Sekcję 4 (`4A` i `4B` — stan bazowy),
   - Sekcję 6 (`6A`, `6B` — stan końcowy oraz `6C` — tabela walidacji empirycznej),
   - Sekcję 7 i Sekcję 8 (weryfikacja `D1–D6` dla `T8.1`),
   - Sekcję 10 i Sekcję 11 (zaznaczenie wszystkich pozycji `[x]` na listach kontrolnych).
2. Zweryfikuj komendą:
   `Select-String -Path "C:\Users\Piotrek\Desktop\translator\Artefakty\Raport_wdrozenia_9.8.md" -Pattern "DO_WYPEŁNIENIA"`
   że w pliku raportu pozostało dokładnie **0 niewypełnionych placeholderów**. Jeśli > 0, wróć do KROKU 4 pkt 1 i uzupełnij brakujące pola.
3. Zweryfikuj, że w `Raport_wdrozenia_9.7.md` pola `Status wdrożenia` i `Sekcja 12` są zaktualizowane (nie zawierają `HEAD` / `W TOKU`).

### KROK 5: RAPORT ZWROTNY (CO AGENT MA ODESŁAĆ)

Po zakończeniu wdrożenia (KROKI 0–4) i walidacji empirycznej (KROK 3A) odeszlij:

1. **Podsumowanie** — 1–2 akapity: co zostało wdrożone, jaka była rozbieżność między planem (P0.2) a kodem.
2. **Ścieżki zapisanych plików:**
   - `C:\Users\Piotrek\Desktop\translator\Artefakty\Raport_wdrozenia_9.8.md` (wypełniony)
   - `C:\Users\Piotrek\Desktop\translator\Artefakty\Sasaki to Pii-chan S2 - 04_post98.ass`
   - `C:\Users\Piotrek\Desktop\translator\Artefakty\Sasaki to Pii-chan S2 - 04_post98_full_trace.log`
   - `C:\Users\Piotrek\Desktop\translator\Artefakty\przebieg_tłumaczenia_post98.txt`
3. **SHA256** wszystkich czterech plików + commit hash.
4. **Status mikro-luki 2C.2:** `WYELIMINOWANY` / `CZĘŚCIOWO` / `POZOSTAŁ` z krótkim uzasadnieniem (1–2 linie).
5. **Status kontroli regresji 9.7** (2C.1, 2C.3, 2C.4, 2A.1–2A.7): 4 × `WYELIMINOWANY` / `POZOSTAŁ` z krótkim uzasadnieniem.
6. **Lista rozbieżności „plan mówi X, kod ma Y"** — wszystkie z Phase 0 + napotkane w trakcie implementacji.
7. **Flagi niespełnionych warunków ukończenia** (jeśli jakieś).
8. **Data i godzina zakończenia wdrożenia.**

---

## 4. DEFINICJA UKOŃCZENIA (a)–(k)

Wdrożenie uznaje się za zakończone **wyłącznie przy jednoczesnym spełnieniu**:

- **(a)** Wszystkie operacje z Sekcji 2A `Prompt_9.8.md` utrzymane (`2A.1–2A.4`).
- **(b)** Operacja 2C.1 z Sekcji 2C `Prompt_9.8.md` wdrożona w pełni (3 podkroki).
- **(c)** Test `T8.1` zaimplementowany i sparametryzowany (≥ 2 przypadki) + `test_standard_9_8_suite` w `test_system.py`.
- **(d)** `komenda_fast` (`pytest`): 100% PASSED (≥ 206 instancji), 0 FAILED, 0 ERROR, czas < 60 s.
- **(e)** `komenda_full` (`pytest -m ""`): 100% PASSED (≥ 359 instancji), 0 FAILED, 0 ERROR.
- **(f)** Bramki CI/CD (`verify_purity.py`, `verify_ultimate_pipeline.py`, `verify_12_fixes.py`) PASS 100%; `audit_diff.ps1` VICTORY CONFIRMED.
- **(g)** Phase 0 ukończona z tabelami P0.2, P0.3 oraz rozstrzygniętą Flagą 0.P (w `Raport_wdrozenia_9.8.md`).
- **(h)** Test `T8.1` zweryfikowany pod kątem falsyfikowalności (mutacja → FAILED, przywrócenie → PASS) i wolny od D1–D6.
- **(i)** Żaden z 204 testów domyślnych (116 `KEEP` + 88 z 9.4–9.7) i 153 `MARK_SLOW` nie został usunięty; 3 gałęzie `# DEFENSIVE_FALLBACK` w `avt_linter.py` nietknięte; `tests/archive/` nietknięty.
- **(j)** Wszystkie pola `<DO_WYPEŁNIENIA_*>` w `Raport_wdrozenia_9.8.md` wypełnione (0 wystąpień); `Raport_wdrozenia_9.7.md` zaktualizowany (status + Sekcja 12).
- **(k)** **WALIDACJA EMPIRYCZNA WYKONANA:** re-tłumaczenie Sasaki S2-04 w trybie Mistrzowskim zakończone sukcesem; **mikro-luka 2C.2 ma status `WYELIMINOWANY`** (0 wystąpień `Boy (FEMININE)`, 0 `Grupa_1os_lm: NON_VIRILE` na liniach mówców MALE), a **regresje 9.7 utrzymane** (ID: 48, ID: 52, ID: 79, `\n` vs `\N`, kursywa ID: 187, telemetria P0).

**Brak spełnienia któregokolwiek warunku = wdrożenie NIEZAKOŃCZONE.**

---

## 5. ZAKAZY (dziedziczone z `Prompt_9.7.md` Sekcja 6 — obowiązują w 9.8 bez zmian)

1. **ZAKAZ 1** (Zakaz mutacji tekstu poza `AVTLinter` i `EpisodeQualityGate`).
2. **ZAKAZ 2** (Zakaz podmiany członów antroponimów wieloczłonowych).
3. **ZAKAZ 3** (Zakaz globalnego dopisywania aliasów tytułowych do wszystkich postaci).
4. **ZAKAZ 4** (Zakaz Test-Only Wiring i mockowania logiki domenowej w testach `T8.1`).
5. **ZAKAZ 5** (Zakaz pomijania Phase 0 i walidacji empirycznej).
6. **ZAKAZ 6** (Zakaz naruszania 204 testów domyślnych i 153 `MARK_SLOW`).
7. **ZAKAZ 7** (Zakaz modyfikacji `DEFENSIVE_FALLBACK` i `tests/archive/`).
8. **ZAKAZ 8** (Zakaz pozostawiania placeholderów w raporcie).
9. **ZAKAZ 9** (Zakaz modyfikacji `.ass`/`.json` — Zero-Cosmetic).
10. **ZAKAZ 10** (Zakaz wycieku Zero-Literal).

---

## 6. CHECKLISTA PRZED URUCHOMIENIEM

```
[ ] Prompt_9.8.md — zapisany pod C:\Users\Piotrek\Desktop\translator\Artefakty\Prompt_9.8.md
[ ] Raport_wdrozenia_9.8.md — zapisany (szkielet) pod C:\Users\Piotrek\Desktop\translator\Artefakty\Raport_wdrozenia_9.8.md
[ ] ZADANIE_4_WALIDACJA_9.8.md — zapisany pod C:\Users\Piotrek\Desktop\translator\Artefakty\ZADANIE_4_WALIDACJA_9.8.md
[ ] Raport_wdrozenia_9.7.md — istnieje (wypełniony przez agenta po 9.7)
[ ] Sasaki to Pii-chan S2 - 04_post97.ass — baseline .ass po 9.7
[ ] Sasaki to Pii-chan S2 - 04_post97_full_trace.log — baseline .log po 9.7
[ ] przebieg_tłumaczenia_post97.txt — baseline przebiegu po 9.7
[ ] EN_Sasaki to Pii-chan S2 - 04.ass — źródło EN do re-tłumaczenia
[ ] SHA256 baseline zapisane SAMODZIELNIE (4 pliki: 3 baseline + 1 EN)
[ ] .venv\Scripts\python.exe — środowisko uruchomieniowe sprawne
```

---

**KONIEC ROZKAZU WYKONAWCZEGO 9.8.**