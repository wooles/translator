# 🧠 PAMIĘĆ PROJEKTU I STANU SESJI ANTIGRAVITY (PROJECT MEMORY & OPERATIONAL TELEMETRY)

Dokument ten stanowi zsynchronizowany rejestr stanu operacyjnego potoku, telemetrii CI/CD, historii incydentów oraz most wiedzy pomiędzy komputerami roboczymi (PC 1 i PC 2). Zasady normatywne definiuje wyłącznie `AGENTS.md` (Standard 4.9).

---

## 🎯 1. AKTUALNY STATUS POTOKU (Stan na 16.10.2026)
- **Status CI/CD:** `STATUS: WDROŻONE I ZWERYFIKOWANE (167/167 -> 171/171 PASSED) - VICTORY CONFIRMED`
- **Gałąź i Architektura:** `main` (Standard 4.9: Stylistic Freedom Invariance, Modular World-State Telemetry, Voiced-Frame Pooling, Directional Consensus Purity, SubTurn Pivot Partitioning, Symetryczny Rachunek Zbiorów We_Group, Stem-First Execution Order, Inwariant Morfemu Przeszłego `-ł-` / `-l-`, Zamknięta Biała Lista Nośników Ruchomych Końcówek, Ochrona Zaimków Uogólniających, Strażnik Homonimii Miejscownika w `is_plural_text`, Ochrona Korpusu Par Ról Osobowych, Zero-Literal-Leakage Protocol & `audit_diff.ps1` Forensic Gate)
- **Środowisko:** Python 3.13 (`.venv`), Windows PowerShell, `ffmpeg` (PATH), `librosa.pyin`, `soundfile`, `pysubs2`, `spaCy en_core_web_sm` (100% offline 0.00 PLN), bezpośrednie klucze Google AI Studio API (`use_vertex = 0`).
- **Dyrektywa Wykonawcza Testów:**
  * Testy przyrostowe podczas kodowania (< 2 s): `.\.venv\Scripts\python.exe -m pytest -k "<nazwa_testu>"`
  * Audyt śledczy diffu: `powershell -ExecutionPolicy Bypass -File .\audit_diff.ps1 -ForbiddenTerms "<lista>"`
  * Pełny pakiet regresyjny (~12 min, uruchamiany wyłącznie raz w Fazie 4): `.\.venv\Scripts\python.exe -m pytest` (171/171 PASSED)

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
  4. *Deterministyczna Fleksja Nazw Własnych (`series_memory.py`, `translator.py`, `avt_linter.py`):* Zamrożona matryca 7 przypadków `DeclensionParadigm`, detektor japońskich mor CV `-e` (brak apostrofu dla wymawianego `-e`, ochrona dla angielskiego niemego `-e` w *White'a*), końcówka `-u` w Miejscowniku i Wołaczu dla tematów na afrykaty i spółgłoski stwardniałe (`-tz, -c, -cz, -sz`), pełny kontrakt i korektor 1. oraz 2. osoby (Testy 155–160, 160/160 PASSED; rozszerzenie do Testów 161–167).

### 🔹 INC-AVT-006 (Architektura Standardu 4.9: *Stylistic Freedom, World-State Telemetry, Set Algebra & Isomorphic Defense*)
- **Wdrożenie 6 Modułów Systemowych (Offline 0.00 PLN):**
  1. *Stylistic Freedom Invariance & World-State Telemetry (`translator.py`):* Pełna swoboda stylistyczna LLM (elipsa, inwersja, czas teraźniejszy, ruchome końcówki). Generowanie mikro-tagu `format_dry_telemetry_tag` przy progu pewności >= 0.80 bez emitowania wartości pustych lub niejednoznacznych.
  2. *Voiced-Frame Pooling & Directional Consensus Purity (`profiler.py`):* Agregacja >= 25 ramek dźwięcznych `librosa.pyin` z filtracją `IQR/median > 0.35` i `std > 50 Hz`. Tłumienie pewności < 0.95 (do 0.70) przy `purity < 0.65` i podnoszenie do >= 0.85 przy czystym konsensusie 1.0. Neutralność formalnych zaimków JA (*watakushi* = 0.0).
  3. *SubTurn Pivot Partitioning & Ściana Cięcia Sceny (`scene_discourse.py`):* Automatyczny podział ciągłej tury na pod-segmenty (SubTurn) przy zmianie adresata, spójnikach przeciwstawnych lub zmianie rejestru mowy/myśli. Niewidzialność monologu wewnętrznego dla dyskursu zewnętrznego.
  4. *Symetryczny Rachunek Zbiorów We_Group i Trójstanowa Virility (`scene_discourse.py`):* `We_Group = scene_participants - excluded_addressee`. Odjęcie zewnętrznego adresata w 2. os. zachowuje formy niemęskoosobowe (`NON_VIRILE`, *-łyśmy*) dla grup kobiecych. Wykluczenie Narratora i Radio.
  5. *Stem-First Execution Order & Inwariant Morfemu Przeszłego (`avt_linter.py`):* Oboczności samogłosek rdzennych `o:ó` i `ę:ą` przed sufiksami ogólnymi. Ochrona czasu teraźniejszego 1. os. na `-am`/`-em` oraz 3. osoby po zaimkach narzędnikowych i nieokreślonych (`tym, ktoś, coś`) i podmiotach przeczących (`nikt, każdy`).
  6. *Ochrona Onomastyczna i Par Ról (`avt_linter.py`, `series_memory.py`):* Ścisła biała lista dopełniacza instytucji nijakich po `z` (*z biura, z ministerstwa, z miasta*), naprawa wołacza afrykat *-tzie -> -tzu*, ortografia przymiotników *-nki -> ciency*, Strażnik Homonimii Miejscownika w `is_plural_text` (*w powiecie, na świecie*), ochrona rzeczowników metaforycznych (*jesteś moją nadzieją*) i QuoteShield. Rozszerzenie suity testowej do 171 testów (Testy 168–171, 171/171 PASSED).

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
| **2026-10-16** | `ARB-016` | Swoboda Stylistyczna | **Stylistic Freedom Invariance**: Pełna autonomia stylistyczna LLM (elipsa, inwersja, czas teraźniejszy, ruchome końcówki). | 0.00 PLN |
| **2026-10-16** | `ARB-017` | Telemetria | **Modular World-State Telemetry**: `format_dry_telemetry_tag` przy progu >= 0.80, kategoryczny zakaz emitowania None/AMBIGUOUS. | 0.00 PLN |
| **2026-10-16** | `ARB-018` | Akustyka Audio | **Voiced-Frame Pooling**: Agregacja >= 25 ramek voiced `librosa.pyin` z filtracją `IQR/median > 0.35` i `std > 50 Hz`. | 0.00 PLN |
| **2026-10-16** | `ARB-019` | Epistemologia | **Directional Consensus Purity**: Tłumienie pewności < 0.95 przy purity < 0.65; wektor >= 0.85 przy czystym konsensusie 1.0. | 0.00 PLN |
| **2026-10-16** | `ARB-020` | Graf Dyskursu | **SubTurn Pivot Partitioning**: Rozcinanie tury mówcy na niezależne pod-tury przy Addressee Pivot oraz izolacja myśli. | 0.00 PLN |
| **2026-10-16** | `ARB-021` | Liczba Mnoga | **We_Group Set Algebra**: `We_Group = scene_participants - excluded_addressee` z trójstanową virility (VIRILE/NON_VIRILE/AMBIGUOUS). | 0.00 PLN |
| **2026-10-16** | `ARB-022` | Morfosyntaktyka | **Stem-First Execution Order**: Oboczności rdzenne `o:ó` i `ę:ą` przed ogólną podmianą sufiksów fleksyjnych. | 0.00 PLN |
| **2026-10-16** | `ARB-023` | Czas Przeszły | **Inwariant Morfemu Przeszłego `-ł-` / `-l-`**: Ochrona czasu teraźniejszego na `-am`/`-em` przed fałszywą fleksją przeszłą. | 0.00 PLN |
| **2026-10-16** | `ARB-024` | Klitki i Podmioty | **Zamknięta Biała Lista Klitkowa**: `bym/byś/żeś` z ochroną fałszywych klitek (`tym/ktoś/coś`) i podmiotów przeczących (`nikt/każdy`). | 0.00 PLN |
| **2026-10-16** | `ARB-025` | Homonimia PWN | **Strażnik Homonimii Miejscownika**: `w powiecie`, `na świecie`, `w mieście` wykluczone z flagowania jako 2. os. lm. czasownika. | 0.00 PLN |
