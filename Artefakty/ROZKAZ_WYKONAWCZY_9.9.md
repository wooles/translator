# ROZKAZ WYKONAWCZY DLA AGENTA KODUJĄCEGO: WDROŻENIE PROMPTU NAPRAWCZEGO 9.9

## 1. PLIKI WEJŚCIOWE I DOCELOWE (ARTEFAKTY)

Twoim zadaniem jest pełne wdrożenie specyfikacji architektonicznej **Wersji 9.9** (mikro-domknięcie architektoniczne 9.8: symetria `We_Group`/`You_Group`, legalizacja non-TTY CLI i higiena `TEST 222`), aktualizacja statusu audytowego w raporcie wersji 9.8 oraz udokumentowanie wdrożenia 9.9 w nowym raporcie wdrożeniowym.

### Pliki do odczytu / zapisu (Write/Update):
1. **Specyfikacja do wdrożenia (Read):**
   `C:\Users\Piotrek\Desktop\translator\Artefakty\Prompt_9.9.md`
   - Sekcja 5 → Wykaz nowych testów `T9.1` i `T9.2` — **pełne szkielety kodu** (import pytest, @pytest.mark.parametrize, placeholdery, asercje).
2. **Szkielet raportu wersji 9.9 do całkowitego wypełnienia (Write):**
   `C:\Users\Piotrek\Desktop\translator\Artefakty\Raport_wdrozenia_9.9.md`
3. **Raport wersji 9.8 do aktualizacji statusu, Sekcji 7 i dopisania Sekcji 12 (Update):**
   `C:\Users\Piotrek\Desktop\translator\Artefakty\Raport_wdrozenia_9.8.md`
4. **Dokument referencyjny — rekordy walidacji testowej i gotowa Sekcja 12 do Raportu 9.8 (Read):**
   `C:\Users\Piotrek\Desktop\translator\Artefakty\ZADANIE_4_WALIDACJA_9.9.md`
   - Sekcja `4.10. Aktualizacja statusu i Sekcji 12 w Raport_wdrozenia_9.8.md` — **gotowa treść Sekcji 12 do wklejenia 1:1**.
   - Sekcja `4.3. Rekord „Nowe testy"` — odesłanie do `Prompt_9.9.md` Sekcja 5.

### Pliki baseline odcinka audytowanego (Read, BEZWZGLĘDNIE NIETYKALNE):
5. `C:\Users\Piotrek\Desktop\translator\Artefakty\Sasaki to Pii-chan S2 - 04_post98.ass` (baseline `.ass` po 9.8)
6. `C:\Users\Piotrek\Desktop\translator\Artefakty\Sasaki to Pii-chan S2 - 04_post98_full_trace.log` (baseline `.log` po 9.8)
7. `C:\Users\Piotrek\Desktop\translator\Artefakty\przebieg_tłumaczenia_post98.txt` (baseline przebiegu po 9.8)

### Plik źródłowy EN (Read — kontekst, NIE re-tłumaczenie):
8. `C:\Users\Piotrek\Desktop\translator\Artefakty\EN_Sasaki to Pii-chan S2 - 04.ass`

### Kontekst historyczny (opcjonalny, do cross-reference ZAKAZÓW):
9. `C:\Users\Piotrek\Desktop\translator\Artefakty\Prompt_9.7.md` — ZAKAZY 1–10 z Sekcji 6 obowiązują w 9.9 bez zmian.
10. `C:\Users\Piotrek\Desktop\translator\Artefakty\Prompt_9.8.md` — poprzednia specyfikacja (kontekst operacji 2A).

Przeczytaj `Prompt_9.9.md`, `Raport_wdrozenia_9.9.md` oraz `ZADANIE_4_WALIDACJA_9.9.md` w całości przed podjęciem jakichkolwiek działań w repozytorium.

---

## 2. CEL INŻYNIERYJNY WERSJI 9.9

Wdrożenie wersji 9.8 (`commit 783dffd`) **w pełni domknęło empirycznie 6/6 zagadnień z audytu 9.7** (Etap 1/2 = 6/6 WYELIMINOWANY), ale audyt architektoniczny (Etap 2/2) zidentyfikował **3 zadania domykające (Zasada 8 CZĘŚCIOWO + MAIN.PY Scope Deviation CZĘŚCIOWO + ryzyka brzegowe w `translator.py`)**:

1. **`2B.1` (main.py):** Legalizacja i pokrycie testem `T9.1` funkcji `resolve_cli_inputs_and_honorifics` (obsługa `--subs`, `KEEP_HONORIFICS` przy `!sys.stdin.isatty()`), wydzielonej z `main.py:349-350, 384-385`.
2. **`2C.1` (translator.py):** Symetria `MALE`/`FEMALE` w `_precompute_episode_scene_genders` oraz separacja `has_male_speaker_in_line` (sterującej `Grupa_1os_lm`) od płci adresata (sterującej wyłącznie `Grupa_2os_lm`).
3. **`2C.2` (test_system.py):** Higiena `TEST 222` (parametryzacja lub rozszerzenie `T8.1` przez `T9.2`) oraz aktualizacja licznika końcowego w `__main__`.

**UWAGA:** Iteracja 9.9 **NIE wymaga re-tłumaczenia odcinka** — Etap 1/2 audytu 9.8 potwierdził 6/6 WYELIMINOWANY w `post98`. Zmiany w 9.9 są wyłącznie architektoniczne (kod + testy).

---

## 3. BEZWZGLĘDNA PROCEDURA WYKONANIA (KROK PO KROKU)

### KROK 0A: Aktualizacja `Raport_wdrozenia_9.8.md` oraz pomiar stanu bazowego PRZED modyfikacjami 9.9

Zanim zmodyfikujesz kod produkcyjny:

1. **Aktualizacja Raportu 9.8:**

   **UWAGA:** Pełna treść Sekcji 12 do wklejenia do `Raport_wdrozenia_9.8.md` znajduje się w pliku:
   `C:\Users\Piotrek\Desktop\translator\Artefakty\ZADANIE_4_WALIDACJA_9.9.md` → sekcja `4.10. Aktualizacja statusu i Sekcji 12 w Raport_wdrozenia_9.8.md`.
   Skopiuj ją **1:1** do końca `Raport_wdrozenia_9.8.md`.

   Otwórz `C:\Users\Piotrek\Desktop\translator\Artefakty\Raport_wdrozenia_9.8.md`:
   - w Sekcji 1 zmień pole `Status wdrożenia` na:
     `FORMALNIE WDROŻONE (207/207 fast, 360/360 full, 4 bramki PASS), 6/6 ZAGADNIEŃ WYELIMINOWANYCH EMPIRYCZNIE, 2/7 ZASAD ARCHITEKTONICZNYCH CZĘŚCIOWO (Zasada 8, MAIN.PY Scope Deviation) — domknięcie w 9.9`.
   - w Sekcji 7 (`OCENA NIEDEGRADACYJNOŚCI`) dodaj podpunkt: `Zasada 8 — CZĘŚCIOWO: TEST 222 bez @pytest.mark.parametrize (D4); brak testu jednostkowego dla main.py:349-350, 384-385 i translator.py:6174-6176.`
   - na końcu pliku wklej **kompletną Sekcję 12** z `ZADANIE_4_WALIDACJA_9.9.md` sekcja 4.10.

2. **Freeze SHA256 baseline PRZED zmianami:**
   Zapisz sumy SHA256 dla następujących plików:
   - 3 pliki baseline: `Sasaki to Pii-chan S2 - 04_post98.ass`, `Sasaki to Pii-chan S2 - 04_post98_full_trace.log`, `przebieg_tłumaczenia_post98.txt`.
   - 1 plik źródłowy EN: `EN_Sasaki to Pii-chan S2 - 04.ass`.
   - 3 pliki kodu produkcyjnego modyfikowane w 9.9: `translator.py`, `main.py`, `test_system.py`.
   - 1 plik testowy modyfikowany w 9.9: `tests/test_discourse_and_translator.py`.
   Zapisz uzyskane wartości w notatniku roboczym.

3. **Pomiar stanu bazowego (przed modyfikacjami 9.9):**
   - tryb szybki: `.\.venv\Scripts\python.exe -m pytest` (oczekiwane: 207 passed, 153 deselected, ~15,65 s)
   - tryb pełny: `.\.venv\Scripts\python.exe -m pytest -m ""` (oczekiwane: 360 passed, 0 failed, 0 error)
   - Wpisz uzyskane wyniki w **Sekcji 3 (`STAN BAZOWY`)** pliku `Raport_wdrozenia_9.9.md`.

### KROK 0B: Wykonanie Fazy 0 (Obowiązkowa weryfikacja kodu i Tabeli P0.2)

Zgodnie z sekcją `FAZA 0 — CZYTANIE KODU (OBOWIĄZKOWA)` w `Prompt_9.9.md`:

1. Przeczytaj w całości:
   - `translator.py` — linie `1945-2038` (`_precompute_episode_scene_genders`), `3260-3282` (`_prepare_batch_prompt`), `4085-4125` (`_process_single_batch`), `6170-6177` (`__main__`).
   - `main.py` — linie `340-395` (obsługa `args.input`, `args.subs`, `sys.stdin.isatty()`, `KEEP_HONORIFICS`).
   - `tests/test_discourse_and_translator.py` — linie `405-451` (`T8.1`).
   - `test_system.py` — linie `19500-19778` (`test_standard_9_8_suite` i licznik w `__main__`).
2. Wypełnij **Tabelę P0.2 (Mapowanie plan ↔ kod)** w `Raport_wdrozenia_9.9.md` — dla 3 operacji `2B.1`, `2C.1`, `2C.2`.
3. Dobierz dane testowe z `SeriesBible` / `en_text` odcinka testowego (innego niż odcinek audytowany, Zero-Literal i Zero-Onomastic Leakage) i wypełnij **Tabelę P0.3** w `Raport_wdrozenia_9.9.md`.

**WARUNEK PRZEJŚCIA DO KROKU 1:** Tabele P0.2 i P0.3 wypełnione 100%. Brak wypełnienia = NIE PRZECHODŹ DALEJ.

### KROK 1: Implementacja `2B.1` — Formalna legalizacja non-TTY CLI (`main.py`)

1. **W `main.py` wydziel czystą funkcję:**
   ```python
   from typing import List, Optional, Tuple

   def resolve_cli_inputs_and_honorifics(
       args, is_tty: bool, env_keep_honorifics: str
   ) -> Tuple[List[str], Optional[bool]]:
       raw_inputs: List[str] = []
       if getattr(args, "input", None):
           raw_inputs = [args.input] if isinstance(args.input, str) else list(args.input)
       if not raw_inputs and getattr(args, "subs", None):
           raw_inputs = [args.subs]

       if getattr(args, "no_honorifics", False):
           keep_honorifics: Optional[bool] = False
       elif getattr(args, "honorifics", False):
           keep_honorifics = True
       elif is_tty:
           keep_honorifics = None  # sygnał: interaktywny prompt w main()
       else:
           keep_honorifics = env_keep_honorifics.lower() == "true"

       return raw_inputs, keep_honorifics
   ```
2. **W `main()`** zastąp inline obsługę `--subs` i `KEEP_HONORIFICS` wywołaniem `resolve_cli_inputs_and_honorifics(args, sys.stdin.isatty(), os.getenv("KEEP_HONORIFICS", "false"))`.
3. **Zachowaj dotychczasowe zachowanie** — `--subs`, `KEEP_HONORIFICS`, `!sys.stdin.isatty()` muszą działać identycznie.

### KROK 2: Implementacja `2C.1` — Symetria `We_Group`/`You_Group` i symetria `MALE`/`FEMALE` (`translator.py`)

1. **W `_precompute_episode_scene_genders`** (`translator.py:1948-1956` i `2019-2034`):
   - Dla `act_gender == "MALE"`: `scene_genders[orig_idx] = "mężczyzna"`.
   - Dla `act_gender == "FEMALE"`: `scene_genders[orig_idx] = "kobieta"`.
   - Symetria musi być pełna — brak gałęzi `elif` w jednej płci, a w drugiej obecnej.

2. **W `_prepare_batch_prompt`** (`translator.py:3265-3277`) i **`_process_single_batch`** (`translator.py:4099-4116`):
   - Zdefiniuj **oddzielnie**:
     ```python
     has_male_speaker_in_line = (
         spk_gram_tag == "MASCULINE"
         or line_spk_gender == "mężczyzna"
     )
     has_male_addressee_in_line = (
         tgt_gram_tag == "MASCULINE"
         or line_addr_cat in ["mężczyzna", "mężczyzna_dual", "grupa_mężczyzn"]
     )
     ```
   - Jeśli `has_male_speaker_in_line`: `is_fem_scene = False` i `pl_grp_val = "VIRILE"` (dotyczy `Grupa_1os_lm`).
   - Jeśli mówczyni żeńska (`spk_gram_tag == "FEMININE"`) w scenie kobiecej (`episode_scene_genders.get(orig_idx) == "kobieta"`) z pojedynczym adresatem męskim (`tgt_gram_tag == "MASCULINE"`) — `Grupa_1os_lm` pozostaje `NON_VIRILE` (bo mówczyni mówi w imieniu grupy kobiecej), a `Grupa_2os_lm` = `MASCULINE` (bo adresatem jest mężczyzna).
   - **Reguła separacji:** `has_male_addressee_in_line` wpływa wyłącznie na `Grupa_2os_lm`, nie na `Grupa_1os_lm`.

### KROK 3: Implementacja `2C.2` — Higiena `TEST 222` (`test_system.py`)

1. **W `test_system.py:19777`** zaktualizuj tekstowy komunikat podsumowujący w `if __name__ == "__main__":` tak, aby odzwierciedlał rzeczywistą liczbę wywoływanych funkcji testowych (`(222/222)`).
2. **W `test_system.py:19506-19550`** (`test_standard_9_8_suite`):
   - Dodaj `@pytest.mark.slow` (jeśli test integracyjny jest długi i nie powinien wchodzić do `fast`), albo
   - Dodaj `@pytest.mark.parametrize` z ≥ 2 przypadkami (jeśli ma pozostać w `fast`).
   - Wybór należy do agenta — zależnie od charakteru testu (suite integracyjny).

### KROK 4: Implementacja testów `T9.1` i `T9.2` (`tests/test_discourse_and_translator.py`)

**UWAGA:** Pełne szkielety testów `T9.1` i `T9.2` znajdują się w `Prompt_9.9.md` → Sekcja 5. Skopiuj i dostosuj po Phase 0.

1. **`T9.1`** — `test_non_tty_cli_resolves_subs_argument_and_honorifics_env_without_stdin_prompt`:
   - `@pytest.mark.unit`, `@pytest.mark.parametrize` (2 przypadki: `subs_arg` + `env_honorifics` → oczekiwane `raw_inputs` + `keep_honorifics`).
   - Wywołanie `resolve_cli_inputs_and_honorifics(ns, is_tty=False, env_keep_honorifics=env_honorifics)`.
   - Asercje: `raw_inputs == expected_inputs`, `keep_hon is expected_keep_honorifics`.

2. **`T9.2`** — `test_we_group_virility_depends_on_speaker_gender_and_preserves_female_we_group_with_male_target`:
   - `@pytest.mark.unit`, `@pytest.mark.parametrize` (2 przypadki: `spk_gram` + `tgt_gram` + `is_fem_scene_init` → oczekiwane `we_group`).
   - Asercje: `we_group == expected_we_group` (VIRILE dla mówcy MASCULINE; NON_VIRILE dla mówczyni FEMININE w scenie kobiecej z męskim adresatem).

3. Zastąp wszystkie placeholdery `<RZECZYWISTY_*>` danymi z Tabeli P0.3.
4. Zweryfikuj empirycznie falsyfikowalność obu testów (mutacja kodu → FAILED, przywrócenie → PASS) oraz brak anty-wzorców `D1–D6`.

### KROK 5: Przestrzeganie ZAKAZÓW 1–10 z `Prompt_9.7.md` i uruchomienie bramek CI/CD

Bezwzględnie przestrzegaj **wszystkich 10 zakazów z Sekcji 6 `Prompt_9.7.md`** (dziedziczone przez 9.9 bez zmian — `Prompt_9.9.md` nie zawiera sekcji ZAKAZÓW explicite, ale 9.9 jest mikro-iteracją 9.8/9.7 i dziedziczy wszystkie ograniczenia):
1. Zakaz mutacji tekstu poza `AVTLinter` i `EpisodeQualityGate`.
2. Zakaz podmiany członów antroponimów wieloczłonowych.
3. Zakaz globalnego dopisywania aliasów tytułowych.
4. Zakaz Test-Only Wiring i mockowania logiki domenowej.
5. Zakaz pomijania Phase 0 i walidacji empirycznej.
6. Zakaz naruszania 207 testów `KEEP` i 153 `MARK_SLOW`.
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
- `pytest` (fast): 100% PASSED (≥ 211 instancji), 0 FAILED, 0 ERROR, czas < 60 s.
- `pytest -m ""` (full): 100% PASSED (≥ 364 instancji), 0 FAILED, 0 ERROR.
- 3 bramki `.py`: PASS 100%.
- `audit_diff.ps1`: VICTORY CONFIRMED.

**WARUNEK ZATRZYMANIA:** Jeśli którakolwiek bramka zwróci FAIL:
- Zatrzymaj wdrożenie.
- Wskaż w raporcie zwrotnym (KROK 7) dokładny błąd i plik.
- NIE PRZECHODŹ do KROKU 6.

### KROK 6: Kompletne wypełnienie `Raport_wdrozenia_9.9.md`

Otwórz plik `C:\Users\Piotrek\Desktop\translator\Artefakty\Raport_wdrozenia_9.9.md` i:
1. Wypełnij wszystkie sekcje i pola `<DO_WYPEŁNIENIA_*>`:
   - Sekcję 1 (metadane, data, commit hash, status),
   - Sekcję 2 (`2.1 Tabela P0.2`, `2.2 Tabela P0.3`),
   - Sekcję 3 (stan bazowy),
   - Sekcję 4 (nowe testy `T9.1`, `T9.2`),
   - Sekcję 5 (stan końcowy fast + full + bramki CI/CD),
   - Sekcję 6 (weryfikacja `D1–D6`),
   - Sekcję 7 (SELF-CHECK).
2. Zweryfikuj komendą:
   `Select-String -Path "C:\Users\Piotrek\Desktop\translator\Artefakty\Raport_wdrozenia_9.9.md" -Pattern "DO_WYPEŁNIENIA"`
   że w pliku raportu pozostało dokładnie **0 niewypełnionych placeholderów**. Jeśli > 0, wróć do KROKU 6 pkt 1 i uzupełnij brakujące pola.
3. Zweryfikuj, że w `Raport_wdrozenia_9.8.md` pola `Status wdrożenia` i `Sekcja 12` są zaktualizowane.

### KROK 7: RAPORT ZWROTNY (CO AGENT MA ODESŁAĆ)

Po zakończeniu wdrożenia (KROKI 0–6) odeszlij:

1. **Podsumowanie** — 1–2 akapity: co zostało wdrożone, jaka była rozbieżność między planem (P0.2) a kodem.
2. **Ścieżki zapisanych plików:**
   - `C:\Users\Piotrek\Desktop\translator\Artefakty\Raport_wdrozenia_9.9.md` (wypełniony)
3. **SHA256** zmodyfikowanych plików (`translator.py`, `main.py`, `test_system.py`, `tests/test_discourse_and_translator.py`) + commit hash.
4. **Status operacji 2B.1:** `WDROŻONE` / `CZĘŚCIOWO` / `POZOSTAŁ` z krótkim uzasadnieniem.
5. **Status operacji 2C.1:** `WDROŻONE` / `CZĘŚCIOWO` / `POZOSTAŁ`.
6. **Status operacji 2C.2:** `WDROŻONE` / `CZĘŚCIOWO` / `POZOSTAŁ`.
7. **Wyniki bramek CI/CD:** `pytest` fast/full, 3 bramki `.py`, `audit_diff.ps1`.
8. **Lista rozbieżności „plan mówi X, kod ma Y"** — wszystkie z Phase 0 + napotkane w trakcie implementacji.
9. **Flagi niespełnionych warunków ukończenia** (jeśli jakieś).
10. **Data i godzina zakończenia wdrożenia.**

---

## 4. DEFINICJA UKOŃCZENIA (a)–(j)

Wdrożenie uznaje się za zakończone **wyłącznie przy jednoczesnym spełnieniu**:

- **(a)** Wszystkie operacje z Sekcji 2A `Prompt_9.9.md` utrzymane (`2A.1–2A.2`).
- **(b)** Wszystkie operacje z Sekcji 2B i 2C `Prompt_9.9.md` wdrożone (`2B.1`, `2C.1`, `2C.2`).
- **(c)** Testy `T9.1` i `T9.2` zaimplementowane i sparametryzowane (≥ 2 przypadki każdy) + `TEST 222` zaktualizowany (marker lub parametryzacja).
- **(d)** `komenda_fast` (`pytest`): 100% PASSED (≥ 211 instancji), 0 FAILED, 0 ERROR, czas < 60 s.
- **(e)** `komenda_full` (`pytest -m ""`): 100% PASSED (≥ 364 instancji), 0 FAILED, 0 ERROR.
- **(f)** Bramki CI/CD (`verify_purity.py`, `verify_ultimate_pipeline.py`, `verify_12_fixes.py`) PASS 100%; `audit_diff.ps1` VICTORY CONFIRMED.
- **(g)** Phase 0 ukończona z tabelami P0.2, P0.3 (w `Raport_wdrozenia_9.9.md`).
- **(h)** Testy `T9.1` i `T9.2` zweryfikowane pod kątem falsyfikowalności i wolne od D1–D6.
- **(i)** Żaden z 207 testów domyślnych i 153 `MARK_SLOW` nie został usunięty; 3 gałęzie `# DEFENSIVE_FALLBACK` w `avt_linter.py` nietknięte; `tests/archive/` nietknięty.
- **(j)** Wszystkie pola `<DO_WYPEŁNIENIA_*>` w `Raport_wdrozenia_9.9.md` wypełnione (0 wystąpień); `Raport_wdrozenia_9.8.md` zaktualizowany (status + Sekcja 12).

**Brak spełnienia któregokolwiek warunku = wdrożenie NIEZAKOŃCZONE.**

**UWAGA:** Walidacja empiryczna (re-tłumaczenie odcinka) **NIE jest wymagana w 9.9** — Etap 1/2 audytu 9.8 potwierdził 6/6 WYELIMINOWANY w `post98`. 9.9 jest iteracją wyłącznie architektoniczną.

---

## 5. ZAKAZY (dziedziczone z `Prompt_9.7.md` Sekcja 6 — obowiązują w 9.9 bez zmian)

1. **ZAKAZ 1** (Zakaz mutacji tekstu poza `AVTLinter` i `EpisodeQualityGate`).
2. **ZAKAZ 2** (Zakaz podmiany członów antroponimów wieloczłonowych).
3. **ZAKAZ 3** (Zakaz globalnego dopisywania aliasów tytułowych do wszystkich postaci).
4. **ZAKAZ 4** (Zakaz Test-Only Wiring i mockowania logiki domenowej w testach).
5. **ZAKAZ 5** (Zakaz pomijania Phase 0).
6. **ZAKAZ 6** (Zakaz naruszania 207 testów domyślnych i 153 `MARK_SLOW`).
7. **ZAKAZ 7** (Zakaz modyfikacji `DEFENSIVE_FALLBACK` i `tests/archive/`).
8. **ZAKAZ 8** (Zakaz pozostawiania placeholderów w raporcie).
9. **ZAKAZ 9** (Zakaz modyfikacji `.ass`/`.json` — Zero-Cosmetic).
10. **ZAKAZ 10** (Zakaz wycieku Zero-Literal).

**Dodatkowy zakaz dla 9.9:**
11. **ZAKAZ 11** (Zakaz re-tłumaczenia odcinka — 9.9 jest iteracją wyłącznie architektoniczną; re-tłumaczenie `post99` byłoby marnotrawstwem API i nie wnosi nowych dowodów empirycznych; Etap 1/2 audytu 9.8 potwierdził 6/6 WYELIMINOWANY w `post98`).

---

## 6. CHECKLISTA PRZED URUCHOMIENIEM

```
[ ] Prompt_9.9.md — zapisany pod C:\Users\Piotrek\Desktop\translator\Artefakty\Prompt_9.9.md
[ ] Raport_wdrozenia_9.9.md — zapisany (szkielet) pod C:\Users\Piotrek\Desktop\translator\Artefakty\Raport_wdrozenia_9.9.md
[ ] ZADANIE_4_WALIDACJA_9.9.md — zapisany pod C:\Users\Piotrek\Desktop\translator\Artefakty\ZADANIE_4_WALIDACJA_9.9.md
[ ] Raport_wdrozenia_9.8.md — istnieje (wypełniony przez agenta po 9.8)
[ ] Sasaki to Pii-chan S2 - 04_post98.ass — baseline .ass po 9.8 (Read, NIE re-tłumaczenie)
[ ] Sasaki to Pii-chan S2 - 04_post98_full_trace.log — baseline .log po 9.8
[ ] przebieg_tłumaczenia_post98.txt — baseline przebiegu po 9.8
[ ] EN_Sasaki to Pii-chan S2 - 04.ass — źródło EN (kontekst)
[ ] SHA256 baseline zapisane SAMODZIELNIE
[ ] .venv\Scripts\python.exe — środowisko uruchomieniowe sprawne
```

---

**KONIEC ROZKAZU WYKONAWCZEGO 9.9.**