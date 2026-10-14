# 🧠 PAMIĘĆ PROJEKTU I STANU SESJI ANTIGRAVITY (PROJECT MEMORY & OPERATIONAL TELEMETRY)

Dokument ten stanowi zsynchronizowany rejestr stanu operacyjnego potoku, telemetrii CI/CD, historii incydentów oraz most wiedzy pomiędzy komputerami roboczymi (PC 1 i PC 2). Zasady normatywne definiuje wyłącznie `AGENTS.md` (Standard 4.0).

---

## 🎯 1. AKTUALNY STATUS POTOKU (Stan na 13.10.2026)
- **Status CI/CD:** `STATUS: WDROŻONE I ZWERYFIKOWANE (160/160 PASSED -> CEL ROZBUDOWY: 166/166 PASSED) - VICTORY CONFIRMED`
- **Gałąź i Architektura:** `main` (Standard 4.0: Epistemiczna Triangulacja Płci, Odporny Parsing CJK, Automat Tożsamości Diegetycznej, Deterministyczna Fleksja `DeclensionParadigm`, Zero-Literal-Leakage Protocol & `audit_diff.ps1` Forensic Gate)
- **Środowisko:** Python 3.13 (`.venv`), Windows PowerShell, `ffmpeg` (PATH), `librosa.pyin`, `soundfile`, `pysubs2`, `spaCy en_core_web_sm` (100% offline 0.00 PLN), bezpośrednie klucze Google AI Studio API (`use_vertex = 0`).
- **Dyrektywa Wykonawcza Testów:**
  * Testy przyrostowe podczas kodowania (< 2 s): `.\.venv\Scripts\python.exe -m pytest -k "<nazwa_testu>"`
  * Audyt śledczy diffu: `powershell -ExecutionPolicy Bypass -File .\audit_diff.ps1 -ForbiddenTerms "<lista>"`
  * Pełny pakiet regresyjny (~12 min, uruchamiany wyłącznie raz w Fazie 4): `.\.venv\Scripts\python.exe -m pytest`

---

## 🔄 2. PROCEDURA SYNCHRONIZACJI WIELOSTANOWISKOWEJ (PC 1 <-> PC 2)
- **Inicjalizacja na drugim PC:**
  `git add . ; git commit -m "Zapis przed pobraniem" ; git pull --no-rebase origin main --no-edit`
- **Codzienna praca:** `POBIERZ_ZMIANY_Z_CHMURY.bat` (pull) oraz `WYSLIJ_ZMIANY_DO_CHMURY.bat` (commit & push).

---

## 📋 3. REJESTR ROZWIĄZANYCH INCYDENTÓW I WDROŻEŃ ARCHITEKTONICZNYCH

### 🔹 INC-AVT-001 (*Mahou Shoujo Ikusei Keikaku: Restart*)
- **Naprawa:** Topologia sceny i concordancja żeńska w `profiler.py`, nieodmienność obcych imion żeńskich na spółgłoskę w `series_memory.py`, `QuoteShield` chroniący cytaty w `avt_linter.py` (Testy 139–142, 142/142 PASSED).

### 🔹 INC-AVT-002 (*Sasaki to Pii-chan S2*)
- **Naprawa:** Obsługa ról numerowanych (`Boy A`, `Girl A`) z priorytetem P0 przeciw wysokiemu F0 seiyū, odmaskowanie monarchów w `is_non_character_entity()`, kanon PWN tytulatury monarszej (*Wasza Wysokość*), wykluczenie fałszywego solilokwium w stylu `Italics` przy obecności markerów 2. osoby (`has_2nd_person_marker`), korekta rządu `o tobie` (Test 155, 155/155 PASSED).

### 🔹 INC-AVT-003 (*Hyouken no Majutsushi ga Sekai wo Suberu S2*)
- **Naprawa:** Fallback sezonowy `strip_season_suffix()` w `metadata.py` (eliminacja błędów 404 AniList dla `S2/Season 2`), ścisła separacja slotu mówcy (idx=0) od adresata (idx=1) w `update_from_episode_profile()`, blokada nadpisywania zweryfikowanej płci P0 przez heurystyki relacyjne (Test 156, 156/156 PASSED).

### 🔹 INC-AVT-004 (*Tensei Kizoku, Kantei Skill de Nariagaru 3rd Season*)
- **Naprawa:** Ochrona granic nazw własnych przy podziałach linii ASS `(?:^|\\[Nnh]|[^\w])`, klasyfikacja toponimów i ochrona przyimka pochodzenia `z` przed fałszywym narzędnikiem (`ci z [Toponym]`), dziedziczenie płci dla prefiksów wiekowych (`Young/Child/Kid X`) oraz etykiet relacyjnych (`X's Kid`), harmonizacja liczby mnogiej adresata w turze mówcy (`SpeakerTurn`) oraz blokada wołacza męskiego (`Vocative-Predicate Lock`) dla form 2. osoby: czasowników, przymiotników (`nie bądź naiwny`) i rzeczowników predykatywnych (`moim najlepszym uczniem`).

### 🔹 INC-AVT-005 (Architektura Rdzenia: *Epistemiczna Triangulacja, Automat Diegetyczny i Fleksja PWN*)
- **Wdrożenie 4 Filarów Systemowych (Offline 0.00 PLN):**
  1. *Epistemiczna Triangulacja Płci (`profiler.py`):* Ekstrakcja japońskiej ścieżki FFmpeg, oszczędne próbkowanie `librosa.pyin` (<= 10 s, filtr szumu std(F0) > 50 Hz), twardy determinizm męski dla F0 <= 135 Hz i zerowa waga akustyki dla F0 > 135 Hz, rekonstrukcja akapitowa i izolacja podmiotu `nsubj` w `spaCy`.
  2. *Odporny Parsing Napisów (`scene_discourse.py`):* Ochrona japońskich cudzysłowów mowy głośnej `「 」`/`『 』` i tagów skilli `【 】`/`《 》`, wycinanie notek `[TL: ...]`, dwuwarstwowa bramka `is_internal_monologue()` (priorytet nawiasów `( )`/`（ ）` nad `target_speaker` oraz rygorystyczna bramka bezpieczeństwa dla samej kursywy `{\i1}`).
  3. *Automat Tożsamości Diegetycznej (`series_memory.py`, `scene_discourse.py`):* Interwały `PersonaInterval` powiązane z `episode_index` (Out-of-Order Safety), ochrona maski `apparent_gender` w dialogu publicznym, aktywacja `true_gender` w myślach i z powiernikiem (`knows_secret`), detekcja dekonspiracji (`EP_RUPTURE`) ze skoku fazowego anaforyki.
  4. *Deterministyczna Fleksja Nazw Własnych (`series_memory.py`, `translator.py`, `avt_linter.py`):* Zamrożona matryca 7 przypadków `DeclensionParadigm`, detektor japońskich mor CV `-e` (brak apostrofu dla wymawianego `-e`, ochrona dla angielskiego niemego `-e` w *White'a*), końcówka `-u` w Miejscowniku i Wołaczu dla tematów na afrykaty i spółgłoski stwardniałe (`-tz, -c, -cz, -sz`), pełny kontrakt i korektor 1. oraz 2. osoby (Testy 155–160, 160/160 PASSED; rozszerzenie do Testów 161–166).

---

## 📐 4. METRYKI OPERACYJNE POTOKU
- **Ograniczenia Ekranu ASS:** `CPS_PL <= 17.0` (dyskwalifikacja `> 20.0`), `CPL <= 38`, max 2 wiersze.
- **Podłoga Gęstości Seiyū:** `CPS_target(rho_x) = min(13.5, 7.5 + 0.5 * rho_x)` dla `rho_x >= 9.0 mor/s`.
- **Progi Golden Corpus:** Anchor Scenes = **100.0% PASSED**, Broader Corpus `>= 99.0%`, Atrybucja Płci `>= 99.8%`.

---

## 🛡️ 5. REJESTR DŁUGU TECHNICZNEGO I ARBITRAŻY ARCHITEKTONICZNYCH

| Data | ID Decyzji | Obszar | Opis Rozstrzygnięcia | Koszt |
| :--- | :--- | :--- | :--- | :--- |
| **2026-10-03** | `ARB-001` | Płeć / Cytaty | Nieodmienność obcych imion żeńskich na spółgłoskę i `QuoteShield` w Warstwie 4. | 0.00 PLN |
| **2026-10-10** | `ARB-002` | Onomastyka | Pierwszeństwo encji zarejestrowanych w `characters` nad toponimami glosariusza (`is_non_character_entity`). | 0.00 PLN |
| **2026-10-10** | `ARB-003` | Mowa Zapośredniczona | Styl `Italics` z markerami 2. os. lub adresem zewnętrznym traktowany jako dialog, a nie monolog. | 0.00 PLN |
| **2026-10-10** | `ARB-004` | Determinizm Offline | Całkowity zakaz zapytań LLM w Warstwie 4; 100% determinizmu offline. | 0.00 PLN |
| **2026-10-11** | `ARB-005` | Architektura | **Zero-Cosmetic Protocol**: Zakaz łatania JSON/ASS/lintera bez naprawy silnika Pythona. | 0.00 PLN |
| **2026-10-11** | `ARB-006` | Metadane / API | **AniList Season Fallback**: Automatyczne odcinanie sufiksów sezonowych (`S2`, `Season 2`) przy 404. | 0.00 PLN |
| **2026-10-11** | `ARB-007` | Graf Relacji | Separacja slotu mówcy (idx=0) od adresata (idx=1) oraz priorytet P0 dla zweryfikowanej płci. | 0.00 PLN |
| **2026-10-12** | `ARB-008` | Toponimy / ASS `\N` | Granica `(?:^|\\[Nnh]|[^\w])` odporna na `\N`, klasyfikacja `TOPONYM` i blokada narzędnika `-em` po `z` pochodzenia. | 0.00 PLN |
| **2026-10-12** | `ARB-009` | Liczba Mnoga | Detekcja audytorium mnogiego w `SpeakerTurn` (`-cie`, `your + [plural]`, JA `omaera`) i wsteczna harmonizacja `you -> wy/was`. | 0.00 PLN |
| **2026-10-12** | `ARB-010` | Aliasy Wiekowe | Rekurencyjne dziedziczenie `true_gender` dla prefiksów (`Young/Child X`) oraz etykiet relacyjnych (`X's Kid/Son`). | 0.00 PLN |
| **2026-10-12** | `ARB-011` | Druga Osoba / Wołacz | Dyadic Turn-Taking i `Vocative-Predicate Lock` uzgadniający czasowniki, przymiotniki i rzeczowniki predykatywne 2. osoby. | 0.00 PLN |
| **2026-10-13** | `ARB-012` | Triangulacja Płci | Asymetria akustyczna `librosa.pyin` (F0 <= 135 Hz męski bas, F0 > 135 Hz waga 0%) + izolacja podmiotu `nsubj` w `spaCy`. | 0.00 PLN |
| **2026-10-13** | `ARB-013` | Automat Diegetyczny | Interwały `PersonaInterval` z `episode_index`, dwuwarstwowa bramka monologu i ochrona cudzysłowów `「 」`/`『 』`. | 0.00 PLN |
| **2026-10-13** | `ARB-014` | Fleksja PWN | `DeclensionParadigm`: detektor japońskich mor CV `-e` (zakaz apostrofu) vs nieme angielskie `-e`, końcówka `-u` w W/Ms po afrykatach (`-tz -> -tzu`). | 0.00 PLN |
| **2026-10-13** | `ARB-015` | Audyt Śledczy AST | Wdrożenie `Zero-Literal & Stem Leakage` oraz obowiązkowego skanera `audit_diff.ps1` i szybkiej ścieżki `pytest -k`. | 0.00 PLN |
