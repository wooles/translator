# 🧠 PAMIĘĆ PROJEKTU I STANU SESJI ANTIGRAVITY (PROJECT MEMORY & OPERATIONAL TELEMETRY)

Dokument ten stanowi zsynchronizowany rejestr stanu operacyjnego potoku, telemetrii CI/CD, historii incydentów oraz most wiedzy pomiędzy komputerami roboczymi (PC 1 i PC 2). Zasady normatywne definiuje wyłącznie `AGENTS.md` (Standard 9.1).

---

## 🎯 1. AKTUALNY STATUS POTOKU (Stan na 03.11.2026 — Standard 10.1 Certyfikowany Baseline)
- **Aktualny certyfikowany standard produkcyjny:** `Standard 10.1 (Production Certified Baseline)`
- **Commit certyfikacji kodu:** `b9b9e2a` (`b9b9e2a7c63bdf2f70711a5f9e5ed538debb35d7`)
- **Commit ochrony Depuracji Legacy 1.0 (Z16):** `474fb64`
- **Stan metryk:** `468 collected` (`315 passed` fast unit/integration + `153 deselected` slow/network), `20` produkcyjnych baz `SeriesBible`, `42` produkcyjne leksykony `fansub_lexicons`, `4/4` bramki (`verify_purity.py`, `verify_12_fixes.py`, `verify_ultimate_pipeline.py`, `audit_diff.ps1`) w stanie `PASS`.
- **Status CI/CD:** `STATUS: CERTYFIKOWANY PRODUKCYJNIE (315/315 FAST PASSED, 4/4 BRAMKI PASS) - VICTORY CONFIRMED`
- **Zasada utrzymaniowa post-10.1:** Wszelkie przyszłe prace rozwojowe startują z certyfikowanego baseline'u `Standard 10.1` i podlegają nienaruszalnym zasadom `Z1`, `Z2`, `Z3`, `Z4` oraz `Z16`.
- **Gałąź i Architektura:** `main` (Standard 10.1: Wariant (d) — Hybrydowa Straż Dowodowa [Hybrid Evidence Guard & Pipeline Hardening], Zero Morphosyntactic Mutation in Production [`VARIANT_D_PURE_LLM_MORPHOLOGY = True`, T(x) = x], Narrow Safety Net P0 and EN w `EpisodeQualityGate.apply_narrow_safety_net_p0_en`, Pre-translacyjna Ingestia AniList P0 do `SeriesBible.characters` z paradygmatami odmiany nazw, Fonetyczna Normalizacja Aliasów `ph <-> f` w O(1) z samoleczącym indeksem, Trwałe Wyeliminowanie Pętli Rewersji `authoritative_dialogue` w Kroku 18 `translator.py`, Reguła Wołacza Tytułów dla nazw obcych na `-tz` [`Kapitanie [Imię]`, `Panie [Imię]`], Programowa Bariera Regresji Fazy 2 `_guard_phase2_regressions` w `DialogueVerifier`, Rygorystyczna Higiena ASS [usuwanie spacji z tagów i przenoszenie wiszących spójników przed `\N`], Stabilna Identyfikacja Zdarzeń `[ID: {event_id}]`, Full-Codebase Zero-Anime-Literal Invariant & 12/12 w `verify_purity.py`, 4/4 w `audit_diff.ps1`)
- **Środowisko:** Python 3.13 (`.venv`), Windows PowerShell, `ffmpeg` (PATH), `librosa.pyin`, `soundfile`, `pysubs2`, `spaCy en_core_web_sm` (100% offline 0.00 PLN), bezpośrednie klucze Google AI Studio API (`use_vertex = 0`).
- **Dyrektywa Wykonawcza Testów:**
  * Testy przyrostowe podczas kodowania (< 2 s): `.\.venv\Scripts\python.exe -m pytest -k "<nazwa_testu>"`
  * Szybki pakiet regresyjny: `.\.venv\Scripts\python.exe -m pytest -q` (315 passed, 153 deselected)
  * Audyt śledczy diffu: `powershell -ExecutionPolicy Bypass -File .\audit_diff.ps1 -ForbiddenTerms "<lista>"`
  * 4 bramki kwalifikacyjne: `python verify_purity.py`, `python verify_12_fixes.py`, `python verify_ultimate_pipeline.py`, `audit_diff.ps1`

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

### 🔹 INC-AVT-007 (Architektura Standardu 7.0: *Zero-Literal Pure Positive Domain Invariant Architecture & Primary LLM Translation Authority*)
- **Wdrożenie 8 Modułów Systemowych (Offline 0.00 PLN):**
  1. *Zero-Literal Pure Positive Domain Invariant Architecture:* Każdy operator systemowy \(T\) w potoku jest zdefiniowany wyłącznie poprzez swoją dziedzinę pozytywną (\(\mathcal{D}_{\text{pos}}\)) opartą na kompletnym, zweryfikowanym stanie ontologicznym P0 (`confidence >= 0.95`, `unknown_count == 0`). Poza dziedziną pozytywną obowiązuje matematyczna funkcja identycznościowa: \(\forall x \notin \mathcal{D}_{\text{pos}}, T(x) = x\).
  2. *Primary LLM Translation Authority:* Model LLM w `translator.py` stanowi autorytatywne źródło przekładu, stylistyki, fleksji i składni. Usunięcie wtórnych kaskad mutujących w pętli post-processingu i na końcu odcinka.
  3. *Declarative World-State Telemetry:* `format_dry_telemetry_tag` (próg pewności >= 0.80), czysto pasywny wektor stanu świata bez imperatywnych zakazów/nakazów, wykrzykników i wartości None, UNKNOWN, AMBIGUOUS w tagu telemetrii.
  4. *CharacterRecord Positive Schema & O(1) In-RAM Alias Index:* Słownik `characters` zawiera wyłącznie byty osobowe (`EntityCategory.ANTHROPONYM`) z polami strukturalnymi (`gender`, `grammatical_gender`, `confidence`, `priority`, `has_verified_gender`, `aliases`) i czystym polem `description` (oczyszczonym z dyrektyw gramatycznych). Separacja relacji skierowanych (\(X \to Y\)) do dedykowanej struktury `relations`. Indeks aliasów w RAM \(\mathcal{O}(1)\).
  5. *Kanoniczna Normalizacja Etykiet Aktora:* `normalize_actor_tag` (odcinanie nawiasów technicznych, ekstrakcja jawnych tagów P0 M/F, normalizacja NFKD).
  6. *Rozłączne Zbiory We_Group i You_Group:* Symetryczna klasyfikacja virility (`VIRILE` / `NON_VIRILE` / `AMBIGUOUS`) z odcięciem mówcy dla You_Group i zewnętrznego adresata dla We_Group.
  7. *Domena Pozytywna DeclensionParadigm:* Ochrona deskrypcji złożonych i wyrazów na polskie sufiksy przymiotnikowe w przypadkach zależnych (\(T(x) = x\)).
  8. *Architektura Odwzorowania Identycznościowego w avt_linter.py:* Automatyczna detekcja trybu produkcyjnego (`is_production`), wyłączenie mutatorów leksykalnych i afektywnych na rzecz ochrony tekstu LLM, ochrona pod osłoną `mask_ass_tags_and_quotes`. Rozszerzenie suity testowej do 174 testów (Testy 172–174, 174/174 PASSED, Zero Regression Lock Standardu 7.0).

### 🔹 INC-AVT-008 (Architektura Standardu 7.1: *Strict Positive Domain Production Routing, Legacy Monolith Bypass & Ontological Normalization*)
- **Wdrożenie 5 Modułów Systemowych (Offline 0.00 PLN):**
  1. *Strict Positive Domain Production Routing:* Potok produkcyjny w `translator.py` (L4104 i L5174) przekazuje `strict_positive_domain=True` do `AVTLinter.lint_and_fix_line` oraz `EpisodeQualityGate.audit_and_fix_entire_episode`.
  2. *Identity Pass-Through for Legacy Monolith:* W trybie `strict_positive_domain=True` Fazy 1–6 monolitu bramki są całkowicie pomijane. Wykonywana jest wyłącznie Faza 0 (higiena ASS) oraz Faza 7 (higiena interpunkcji), a pod osłoną `mask_ass_tags_and_quotes` uruchamiane są wyłącznie zunifikowane operatory czystej domeny pozytywnej D_pos (confidence >= 0.95, unknown_count == 0). Wszelki dialog poza D_pos zachowuje tożsamość \(T(x) = x\).
  3. *Kompatybilność Wsteczna (Backward Compatibility):* Domyślna wartość `strict_positive_domain: bool = False` we wszystkich metodach zapewnia 100% kompatybilności wstecznej dla starszych testów jednostkowych potoku.
  4. *Ontological SeriesBible Normalization & CharacterRegistryDict:* Promocja płci z pola `description` do pól strukturalnych z priorytetem P0 (`confidence >= 0.95`), separacja relacji skierowanych do struktury `relations` z transparentnym fallbackiem `CharacterRegistryDict` oraz automatyczna indeksacja aliasów pierwszych imion w RAM \(\mathcal{O}(1)\).
  5. *Szereg Współrzędny Przymiotników i Pełny Paradygmat Ułomny 'powinien':* Symetryczne uzgadnianie obu członów szeregu współrzędnego przymiotników po łączniku 2. osoby według `target_gender` oraz obsługa pełnego paradygmatu `powinien + był/była/byli/były` (1. i 2. os. lp. oraz 1. i 2. os. lm. VIRILE/NON_VIRILE). Rozszerzenie suity testowej do 178 testów (Testy 175–178, 178/178 PASSED, Zero Regression Lock Standardu 7.1).

---

### 🔹 INC-AVT-009 (Architektura Standardu 8.0: *Full-Codebase Zero-Anime-Literal Invariant, Default strict_positive_domain=True & Dynamic SeriesBible Resolution*)
- **Wdrożenie 4 Modułów Systemowych (Offline 0.00 PLN):**
  1. *Full-File Zero-Anime-Literal Invariant (Linia 1 do Końca):* W żadnym z 9 produkcyjnych plików .py (	ranslator.py, vt_linter.py, series_memory.py, scene_discourse.py, profiler.py, metadata.py, 
ules.py, erifier.py, whisper_disambiguator.py) nie występuje ani jeden literał z 41 zakazanych nazw własnych z anime (dokładnie 0 trafień w kodzie, słownikach, docstringach i komentarzach od linii 1 do EOF).
  2. *Domyślny Tryb Produkcyjny strict_positive_domain: bool = True:* Wszystkie publiczne metody lintera (AVTLinter.lint_and_fix_line, AVTLinter.lint_subtitles, EpisodeQualityGate.audit_and_fix_entire_episode) mają domyślnie ustawioną wartość strict_positive_domain: bool = True. Poza Dziedziną Pozytywną \(D_{\\text{pos}}\) (\(\\text{confidence} \\ge 0.95\)) obowiązuje ścisłe odwzorowanie tożsamościowe \(T(x) = x\) chroniące autonomię modelu LLM.
  3. *Dynamiczny Fallback Sezonowy Baz Wiedzy (SeriesBible._resolve_bible_path):* Automatyczne rozwiązywanie ścieżek wielosezonowych (strip_season_suffix) przy inicjalizacji SeriesBible z tytułów bazowych lub wariantów sezonowych, eliminujące puste bazy przy wielosezonowych tytułach serii.
  4. *Ekwiwalencja Zbiorów Tokenów w Pass 1 (get_character_gender):* Rozpoznawanie tożsamości postaci wieloczłonowych w odwróconym szyku japońskim/zachodnim (Family Given vs Given Family) przez porównanie zbiorów tokenów (	okens_set == clean_tokens_set). Rozszerzenie suity testowej do 179 testów (Test 179, 179/179 PASSED, Zero Regression Lock Standardu 8.0).

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
| **2026-10-17** | `ARB-026` | Architektura | **Zero-Literal Pure Positive Domain Invariant Architecture**: Każdy operator systemowy T zdefiniowany wyłącznie przez D_pos; poza nią T(x) = x. | 0.00 PLN |
| **2026-10-17** | `ARB-027` | Model LLM | **Primary LLM Translation Authority**: Eliminacja wtórnych kaskad mutujących w post-processingu i na końcu odcinka. | 0.00 PLN |
| **2026-10-17** | `ARB-028` | Telemetria | **Declarative World-State Telemetry**: `format_dry_telemetry_tag` przy progu >= 0.80 bez wartości None/UNKNOWN/AMBIGUOUS. | 0.00 PLN |
| **2026-10-17** | `ARB-029` | Pamięć / Ontologia | **CharacterRecord Positive Schema & O(1) Alias Index**: Czyste pole description, separacja relacji skierowanych (X -> Y). | 0.00 PLN |
| **2026-10-17** | `ARB-030` | Normalizacja Etykiet | **Kanoniczna Normalizacja Etykiet Aktora**: `normalize_actor_tag` (odcinanie tagów technicznych, ekstrakcja P0 M/F, NFKD). | 0.00 PLN |
| **2026-10-17** | `ARB-031` | Dyskurs / Zbiory | **Rozłączne Zbiory We_Group & You_Group**: Symetryczna klasyfikacja virility z odcięciem mówcy dla 2. os. i adresata dla 1. os. lm. | 0.00 PLN |
| **2026-10-17** | `ARB-032` | Fleksja PWN | **Domena Pozytywna DeclensionParadigm**: Ochrona deskrypcji złożonych i sufiksów przymiotnikowych w przypadkach zależnych (T(x) = x). | 0.00 PLN |
| **2026-10-17** | `ARB-033` | Jakość / Linter | **Odwzorowanie Identycznościowe w Linterze**: Automatyczne `is_production`, wyłączenie mutatorów afektywnych, ochrona tekstu LLM. | 0.00 PLN |
| **2026-10-17** | `ARB-034` | Routing Potoku | **Strict Positive Domain Production Routing**: `strict_positive_domain=True` w L4104 i L5174 potoku produkcyjnego `translator.py`. | 0.00 PLN |
| **2026-10-17** | `ARB-035` | Monolit Bramki | **Legacy Monolith Bypass & Identity Pass-Through**: Pominięcie Faz 1-6 monolitu bramki i ochrona swobody stylistycznej LLM (\(\forall x \notin \mathcal{D}_{\text{pos}}, T(x) = x\)). | 0.00 PLN |
| **2026-10-17** | `ARB-036` | Ontologia / Pamięć | **Ontological Purification & CharacterRegistryDict**: Promocja płci do P0, separacja `relations` z transparentnym fallbackiem i aliasy pierwszych imion O(1). | 0.00 PLN |
| **2026-10-17** | `ARB-037` | Morfosyntaktyka | **Szereg Współrzędny Przymiotników i Paradygmat Powinien**: Symetryczna concordancja przymiotników i pełna odmiana czasownika ułomnego `powinien` (1. i 2. os., VIRILE/NON_VIRILE). | 0.00 PLN |
| **2026-10-17** | ARB-038 | Higiena Kodu | **Full-Codebase Zero-Anime-Literal Invariant**: Ekstirpacja 41 nazw anime w 9 plikach od linii 1 do EOF. | 0.00 PLN |
| **2026-10-17** | ARB-039 | Architektura | **Domyślny strict_positive_domain=True**: Wymuszenie czystej domeny pozytywnej D_pos i Identity Pass-Through. | 0.00 PLN |
| **2026-10-17** | ARB-040 | Pamięć / Ontologia | **Dynamiczny Fallback Sezonowy i Token-Set Equivalence**: _resolve_bible_path i obsługa szyku japońskiego w P0. | 0.00 PLN |
| **2026-10-18** | ARB-041 | Telemetria | **Pełna Deklaratywna Telemetria**: Zamiana strzałek dyrektywnych `->` i alarmów na czyste deskryptory stanu audio (`Sygnał audio JP: ...`, `Kotwica semantyczna audio JP: ...`, `[TELEMETRIA: ...]`). | 0.00 PLN |
| **2026-10-18** | ARB-042 | Kanon / Zasady | **Ekstirpacja 4 Klastrów Onomastycznych w rules.py**: Całkowite oczyszczenie reguł z literałów dialektów i postaci przy zachowaniu identyfikatorów filarów. | 0.00 PLN |
| **2026-10-18** | ARB-043 | Tarcza Regresyjna | **Synchronizacja Asercji Testowych (Standard 8.0)**: Dopasowanie 61 asercji do deklaratywnej telemetrii (179/179 PASSED, 0 naruszeń we wszystkich 5 bramkach). | 0.00 PLN |
| **2026-10-19** | `ARB-044` | Architektura Wariantu (d) | **Hybrydowa Straż Dowodowa (Standard 9.0)**: Odcięcie mutatorów lintera w produkcji ($T(x) = x$), Narrow Safety Net $P_0 \cap \text{EN}$, pre-translacyjna ingestia AniList $P_0$, aliasy $ph \leftrightarrow f$ w $\mathcal{O}(1)$, eliminacja pętli rewersji w Kroku 18, wołacz tytularny `-tz`, bariera regresji Fazy 2, higiena ASS i stabilne `[ID: event_id]` (183/183 PASSED). | 0.00 PLN |

---

## Backlog 11.0 — N-05: Oczyszczenie regexów w `get_focused_rules_for_batch` z japońskich tokenów leksykalnych

**Status:** `OPEN` (P2, dług techniczny, nie blokuje 10.4)
**Zidentyfikowano:** Standard 10.3 (`9f4df49`), audyt czystości i rzetelności Filarów (`Raport_audytu_czystosci_i_rzetelnosci_filarow_SUPLEMENT.md`, FAZA 0)
**Przeklasyfikowano:** z P1 na P2 przed hotfixem 10.4 (na podstawie analizy semantyki Z4)

### Problem

W funkcji `get_focused_rules_for_batch` (`rules.py`) wewnętrzne wzorce regularne (regex) zawierają japońskie tokeny leksykalne:

- **`DYN_1`** (`en_slang_pat`, `jp_dialect_pat`): `wagahai`, `dechu`, `nyan`, `pyon`, `zura`, `gero`, `dabe`, `akan`, `chau`, `honma`, `yaro`, `seya`, `wakatten`, `shiran`, 8 znaków kana (`やん`, `やろ`, `ほんま`, `ちゃう`, `あかん`, `じゃけん`, `だべ`, `っす`)
- **`DYN_2`** (`archaic_pat`): `ojou`, `washi`, `sessha`, `warawa`, `onushi`, `gozaru`
- **`DYN_3`** (`honorific_pat`): `san`, `sama`, `kun`, `chan`, `sensei`, `senpai`, `dono`
- **`DYN_4`** (`age_gender_pat`): `kanojo-tachi`, `onnatachi`, `shonen`, `baba`, `bba`
- **`DYN_5`** (`combat_affect_pat`): `ottotto`, `kakegoe`
- **`DYN_8`** (`culture_signs_pat`): `tsukkomi`, `boke`, `neta`, `gyagu`, `dajare`, `giongo`, `gitaigo`, `bento`, `onigiri`, `ramen`, `udon`, `soba`, `tempura`, `sushi`, `sake`, `mochi`, `takoyaki`, `okonomiyaki`, `kotatsu`, `yukata`, `kimono`
- **`DYN_9`** (`lyric_high_pat`, `lyric_support_pat`): `namida`, `sayonara`, `sabishii`, `kanashii`, `natsukashii`, `itoshii`

### Dlaczego to NIE jest naruszenie Z4

Regex detekcji to **wewnętrzny mechanizm selekcji** (`True`/`False`), a nie **treść promptu** wysyłanego do LLM. LLM widzi wyłącznie **czysty** tekst reguły. Tokeny japońskie w regexach to **kategorie językowe** (partykuły dialektu, honoryfikatory), nie **instancje** (imiona, tytuły serii). Zasada 4 (Z4) zakazuje **instancji**, nie **kategorii**.

### Rozwiązanie (11.0)

**Opcja A (rekomendowana):** Przenieść japońskie tokeny z `rules.py` do `whisper_disambiguator.py` i przekazywać do `get_focused_rules_for_batch` **gotowe znaczniki** (`[ZNACZNIK_REJESTRU]`, `[ZNACZNIK_HONORYFIKATU]`, `[ZNACZNIK_SLANGU]`, `[ZNACZNIK_KULTUROWY]`, `[ZNACZNIK_EMOCJONALNY]`). Wtedy `rules.py` operuje **wyłącznie** na kategoriach metajęzykowych.

**Opcja B (minimalna):** Zostawić regexy bez zmian, dodać test `T11.0_1`, który dokumentuje istniejący stan (dług) — bez naprawy. Nie rekomendowane (test dokumentujący bug bez naprawy jest bezsensowny).

**Opcja C (odrzucona):** Usunąć japońskie tokeny z regexów bez przeniesienia ich do `whisper_disambiguator.py` — pogorszyłoby to precyzję triggerów (`DYN_1`, `DYN_5`, `DYN_8`, `DYN_9` przestałyby wykrywać japońskie markery).

### Ryzyko

- **Refaktoryzacja (Opcja A):** średnie. Zmiana logiki detekcji może wpłynąć na precyzję triggerów (fałszywe pozytywy/negatywy). Wymaga testów `T11.0_*` weryfikujących, że po refaktoryzacji `DYN_1`, `DYN_5`, `DYN_8`, `DYN_9` aktywują się na tych samych wejściach co przed.
- **Bez naprawy (Opcja B):** zerowe. Kod działa poprawnie, dług jest świadomie zaakceptowany.

### Priorytet

**Niski (P2).** N-05 nie blokuje 10.4 ani kolejnych hotfixów. Może zostać odłożone do 11.0 lub pominięte, jeśli priorytety się zmienią.


## Backlog 11.0 — N-06: Kolizja homonimiczna TOPONYM vs ANTHROPONYM (<NAZWA_SZKOŁY_1>)

**Status:** `OPEN` (P2, dług techniczny w telemetrii, nie wpływa na tekst wyjściowy .ass po 10.6.1, nie blokuje 10.6.3)
**Zidentyfikowano:** `Raport_audytu_arnold_toponym_i_duplikacji_bible.md` (2026-11-05, Defekt C)

### Problem

W `series_bible` token `<NAZWA_SZKOŁY_1>` istnieje wyłącznie jako jednowyrazowy alias nazwiska rekordu ANTHROPONYM `<NAZWA_POSTACI_1>`, a nie jako osobny wpis TOPONYM w `entity_categories`. W efekcie `is_non_character_entity("<NAZWA_SZKOŁY_1>")` (`series_memory.py:8606–8617`) zwraca `False`, a telemetria w kwestii z `relations with <NAZWA_SZKOŁY_1>` przypisuje `Adresat: <NAZWA_SZKOŁY_1> (FEMININE)`.

### Rozwiązanie (11.0)

Wdrożenie operacji `FIX-C.1` (ekstrakcja nazw instytucji/lokacji z opisu serii do `entity_categories` jako `TOPONYM`), `FIX-C.2` (odpięcie kolidującego jednowyrazowego aliasu nazwiska w kroku `8f` `_sanitize_loaded_bible_in_ram`) oraz `FIX-C.3` (kontekstowa ochrona przyimków lokatywnych/relacyjnych w `is_non_character_entity`).


## Backlog 11.0 — N-07: Adresowanie mówców tłumu Mob* i rozbijanie identyfikatorów CamelCase

**Status:** `OPEN` (P2, dług techniczny w telemetrii, nie wpływa na tekst wyjściowy .ass, nie blokuje 10.6.3)
**Zidentyfikowano:** `Raport_audytu_arnold_toponym_i_duplikacji_bible.md` (2026-11-05, Defekt E)

### Problem

1. `populate_secondary_actor_tags` (`series_memory.py:6941`) używa `re.findall(r"\b\w+\b", clean_tag.lower())`, co nie dzieli identyfikatorów CamelCase (`<GRUPA_TŁUMU_1>` typu `MobMan2`, `MobWoman`, `MeanGirl`), przez co mówcy tłumu otrzymują w `series_bible` `gender: "UNKNOWN"`.
2. W `scene_discourse.py` (`resolve_turn_addressee`) przy braku zweryfikowanej płci poprzedniego mówcy tłumu Forward Lookahead przypisuje jako adresata mówcę kolejnej sceny po cięciu montażowym (`<BYT_KRÓLEWSKI_1>`).

### Rozwiązanie (11.0)

Wdrożenie operacji `FIX-E.1` (rozbijanie granic CamelCase i cyfr przed klasyfikacją leksykalną w `populate_secondary_actor_tags`) oraz `FIX-E.2` (izolacja mówców `Mob*`/`Crowd*` w `resolve_turn_addressee` przy braku wykładników 2. osoby).


## Backlog 11.0 — N-08: Historyczne rozszczepienie odcinka S2-02 w pliku bazowym <SERIA_BASE>_bible.json

**Status:** `OPEN` (P3, historyczny artefakt w metadanych `episodes_translated`, nie wpływa na jakość tłumaczenia, nie blokuje 10.6.3)
**Zidentyfikowano:** `Raport_audytu_weryfikacyjnego_10_6_3_defekt_D.md` oraz aneks uzupełniający (2026-11-05)

### Problem

Przed naprawą `_resolve_bible_path` w 10.6.3 (`FIX-D.1`) odcinek `S2 - 02` serii `<SERIA_BASE>` został zapisany w pliku `<SERIA_BASE>_bible.json` (`season_num=None`), podczas gdy odcinek `S2 - 01` zapisał się w `<SERIA_BASE>_2nd_Season_bible.json` (`season_num=2`). Ponieważ oba pliki są śledzone w repozytorium git i objęte ochroną Z16, a `consolidate_split_bibles` celowo nie łączy różnych sezonów (`None` vs `2`, zgodnie z `T10.6.3_7`), wpis ten pozostaje nienaruszony w 10.6.3.

### Rozwiązanie (11.0)

Dodanie w `tools/consolidate_bibles.py` opcjonalnej flagi `--migrate-misplaced-season-episodes` (uruchamianej lokalnie przez operatora poza reżimem Z16), która przenosi wpisy `episodes_translated` i `batch_stats` zawierające jawny znacznik `S2` z pliku `<SERIA_BASE>_bible.json` do `<SERIA_BASE>_2nd_Season_bible.json`.
