# 🧠 PAMIĘĆ PROJEKTU I STANU SESJI ANTIGRAVITY (PROJECT MEMORY & OPERATIONAL TELEMETRY)

Dokument ten stanowi zsynchronizowany rejestr stanu operacyjnego potoku, telemetrii CI/CD, historii incydentów oraz most wiedzy pomiędzy komputerami roboczymi (PC 1 i PC 2). Zasady normatywne definiuje wyłącznie `AGENTS.md` (Standard 9.1).

---

## 🎯 1. AKTUALNY STATUS POTOKU (Stan na 2026-11-12 — Standard 11.1.6 Certyfikowany Baseline)
- **Aktualny certyfikowany standard produkcyjny:** `Standard 11.1.6 (Full Glossary Inflection Guard, Cross-Speaker ASR Dedup & Off-Screen Discourse Isolation Baseline)`
- **Commit certyfikacji kodu:** `0651e17ed250bf9be31b9670695b8e0f86d481b3` (`0651e17`)
- **Commity implementacyjne 11.1:** `5b7306d` (Commit 1), `5b17ea7` (Commit 2), `2b4bc7d` (Commit 3), `8b72887` (Commit 4), `8a7dd31` (Commit 5), `218af2e` (Commit 6)
- **Commity Hotfixu 11.1.1:** `328729f` (Commit 1), `9de0b83` (Commit 2), `07c4684` (Commit 3), `96acac7` (Commit 4)
- **Commity Hotfixu 11.1.2:** `74766d8` (Commit 1), `1b540e3` (Commit 2), `8313658` (Commit 3), `326b7e0` (Commit 4)
- **Commity Hotfixu 11.1.2a:** `d310969` (Commit 1), `a928569` (Commit 2)
- **Commity Hotfixu 11.1.3:** `25e9300` (Commit 1), `ed9dc5f` (Commit 2), `879fb04` (Commit 3)
- **Commity Hotfixu 11.1.3a:** `4be5ab0` (Commit 1), `842b9e9` (Commit 2), `7011407` (Commit 3)
- **Commity Hotfixu 11.1.4:** `a6d40bb` (Commit 1), `38ad629` (Commit 2), `3057e97` (Commit 3)
- **Commity Hotfixu 11.1.4a:** `1b4d52a` (Commit 1), `d4a456c` (Commit 2), `4eb863c` (Commit 3)
- **Commity Hotfixu 11.1.4b:** `03db100` (Commit 1), `bd52c4c` (Commit 2), `dd950ba` (Commit 3)
- **Commity Hotfixu 11.1.5:** `13afb42` (Commit 1), `3c70a55` (Commit 2), `79f6e69` (Commit 3)
- **Commity Hotfixu 11.1.6:**
  * Commit 1 (`d69d3f3004104ddad01cf9455c534a3dcb8b9664`): `fix(pipeline): enforce phase1/2 inflected glossary canon, relation role gender reconciliation, ASR cross-speaker dedup, and off-screen addressee isolation (11.1.6)`
  * Commit 2 (`0651e17ed250bf9be31b9670695b8e0f86d481b3`): `test(regression): add 4 end-to-end unit tests for 11.1.6 glossary inflection, relation roles, ASR dedup, and off-screen discourse` — **NOWY COMMIT CERTYFIKACJI KODU**
  * Commit 3 (`HEAD`): `docs(release): certify Standard 11.1.6 baseline in AGENTS.md, PROJECT_MEMORY.md, and implementation report`
- **Status 11.1.6:** `CERTIFIED / CLOSED (2026-11-12)`
- **Commit ochrony Depuracji Legacy 1.0 (Z16):** `a6d40bb09d60b2d986d919de98044c6e2d9c838b` (`a6d40bb` — nienaruszalne 0 B diffu na plikach chronionych)
- **Stan metryk:** `352 passed` w `tests/` oraz `71 passed, 153 deselected` w `test_system.py` (łącznie `423 passed` fast unit/integration + `153 deselected` slow/network), `20` produkcyjnych baz `SeriesBible`, `42` produkcyjne leksykony `fansub_lexicons`, `4/4` bramki CI/CD (`verify_purity.py` 12/12, `verify_8_fixes.py` 8/8, `verify_12_fixes.py` 12/12, `verify_ultimate_pipeline.py` 15/15) oraz `audit_diff.ps1` w stanie `PASS`.
- **Status CI/CD:** `STATUS: CERTYFIKOWANY PRODUKCYJNIE (352/352 TESTS PASSED, 71/71 SYSTEM PASSED, 4/4 BRAMKI PASS) - VICTORY CONFIRMED`
- **Zasada utrzymaniowa post-11.1:** Wszelkie przyszłe prace rozwojowe startują z certyfikowanego baseline'u `Standard 11.1` i podlegają nienaruszalnym zasadom `Z1`, `Z2`, `Z3`, `Z4` oraz `Z16`.
- **Gałąź i Architektura:** `main` (Standard 11.1.6: Strażnik Glosariusza Fazy 1 i 2, Odwracanie Synonimów Przymiotnikowych, Reconcyliacja Ról Relacyjnych P0 w RAM, Cross-Speaker ASR Whisper Deduplikacja i Filtr Mikro-Kwestii, Izolacja Mówców Off-Screen 'Italics - Top' oraz Zachowanie Nazw Aktorów Złożonych w ASS, Certyfikacja Kodu `0651e17ed250bf9be31b9670695b8e0f86d481b3`, Nienaruszalny Baseline Z16 `a6d40bb09d60b2d986d919de98044c6e2d9c838b`, Zero-Literal Pure Positive Domain Invariant Architecture & Primary LLM Translation Authority)
- **Środowisko:** Python 3.13 (`.venv`), Windows PowerShell, `ffmpeg` (PATH), `librosa.pyin`, `soundfile`, `pysubs2`, `spaCy en_core_web_sm` (100% offline 0.00 PLN), bezpośrednie klucze Google AI Studio API (`use_vertex = 0`).
- **Dyrektywa Wykonawcza Testów:**
  * Testy przyrostowe podczas kodowania (< 2 s): `.\.venv\Scripts\python.exe -m pytest -k "<nazwa_testu>"`
  * Szybki pakiet regresyjny: `.\.venv\Scripts\python.exe -m pytest -q` (337 passed w tests/, 71 passed i 153 deselected w test_system.py)
  * Audyt śledczy diffu: `powershell -ExecutionPolicy Bypass -File .\audit_diff.ps1 -ForbiddenTerms "<lista>"`
  * 4 bramki kwalifikacyjne: `python verify_purity.py`, `python verify_8_fixes.py`, `python verify_12_fixes.py`, `python verify_ultimate_pipeline.py`

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
## INC-AVT-010 (Standard 11.1) — Konflikt Z16-vs-Z3: `f1_starts_lower` w `verifier.py`

**Status:** `RESOLVED (Standard 11.1, Commit 4 — Z16-amendment #3)`
**Zidentyfikowano:** 2026-11-05, raport wykonawczy 10.6.3 (`ed226d0`)
**Zamknięto:** 2026-11-07 (Commit 4 Standardu 11.1, hash `8b72887`)

### Rozwiązanie (11.1)
W ramach autoryzowanego `Z16-amendment #3` usunięto warunek `f1_starts_lower` z warunku 17a w `_guard_phase2_regressions` (`verifier.py`) oraz zsynchronizowano asercję Testu 219 w `test_system.py`, przywracając pełny prymat Primary LLM Authority (Z3) — brak sztucznego wstrzykiwania wielokropka w linii Fazy 1 rozpoczynającej się bez kropek.

### 🔹 INC-AVT-011 (Standard 11.1: Uszczelnienie verify_purity.py — Z16-amendment #1)
- **Status:** `RESOLVED (Standard 11.1, Commit 1 — Z16-amendment #1, hash 5b7306d)`
- **Rozwiązanie:** Rozszerzenie `FILES_TO_AUDIT` (na 30 modułów runtime + testy + narzędzia) oraz uszczelnienie bramek AST w `verify_purity.py` (Bramka 2, 4 i 8).

### 🔹 INC-AVT-012 (Standard 11.1: Neutralizacja Kodu i Zasobów — Z16-amendment #2)
- **Status:** `RESOLVED (Standard 11.1, Commit 3 — Z16-amendment #2, hash 2b4bc7d)`
- **Rozwiązanie:** Całkowite oczyszczenie kodu z nazw własnych, dialektów i prescriptive phrases w `avt_linter.py`, `rules.py`, `series_memory.py`, `fansub_miner.py`, `glossary_manager.py`, `user_feedback.py` oraz `translator.py`. Dynamiczna detekcja dyskursu w `WhisperDisambiguator.detect_batch_discourse_categories` (zamknięcie `N-05`).

### 🔹 INC-AVT-013 (Standard 11.1: Autoryzowana Aktualizacja Testu 219 — Z16-amendment #3)
- **Status:** `RESOLVED (Standard 11.1, Commit 4 — Z16-amendment #3, hash 8b72887)`
- **Rozwiązanie:** Aktualizacja asercji Testu 219 w `test_system.py:19353` pod kątem Primary LLM Authority (Z3) i usunięcia `f1_starts_lower`, ustanawiając nowy nienaruszalny baseline Z16 (`8b72887`).

### 🔹 INC-AVT-014 (Hotfix 11.1.1: Uszczelnienie verify_purity.py — Z16-amendment #4)
- **Status:** `RESOLVED (Hotfix 11.1.1, Commit 1 — Z16-amendment #4, hash 328729f)`
- **Rozwiązanie:** Usunięcie hardkodowanego zbioru `KNOWN_NAMES_LOWER`, dodanie `tests/*.py` do zbioru skanowanych `LOGIC_FILES`, wprowadzenie walidacji AST dla zmiennych onomastycznych w `ast.Assign` i `ast.AnnAssign`, eliminując luki audytowe (Pozycja 23).

### 🔹 INC-AVT-015 (Hotfix 11.1.1: Neutralizacja Modułów Produkcyjnych i Ekstrakcja Leksykonu Onomastycznego — Z16-amendment #5)
- **Status:** `RESOLVED (Hotfix 11.1.1, Commit 2 — Z16-amendment #5, hash 9de0b83)`
- **Rozwiązanie:** Wyeksportowanie 12 zestawów onomastycznych (576 leksemów, w tym klucz fansub_male_roles) do `series_memory/.onomastic_lexicon.json` z dynamicznym ładowaniem `_load_onomastic_lexicon()`, neutralizacja prescriptive phrase w `rules.py` (DYN_7), dynamiczne bazy wiedzy w `profiler.py`, syntetyczne fixtures w `metadata.py`, dynamiczne serie w `user_feedback.py` oraz usunięcie wszystkich plików produkcyjnych z allowlisty migracyjnej (Pozycje 1–18).

### 🔹 INC-AVT-016 (Hotfix 11.1.1: Neutralizacja Pakietu Testów, Nowy Baseline Z16 i Certyfikacja — Z16-amendment #6)
- **Status:** `RESOLVED (Hotfix 11.1.1, Commit 3 — Z16-amendment #6, hash 07c4684)`
- **Rozwiązanie:** Neutralizacja 7 plików testowych na syntetyczne nazwy (`tests/test_metadata.py`, `tests/test_discourse_and_translator.py`, `tests/test_verifier.py`, `tests/test_avt_linter.py`, `tests/test_translator.py`, `tests/test_profiler.py`, `tests/test_series_memory.py`), ekstrakcja `_reset_episode_state_for_file` w `translator.py` i naprawa Testu 2 oraz Testu 4 w `tests/test_pipeline_flow.py`, dodanie pod-przypadku pozytywnego dla wielokropka w Test 219 (`test_system.py:19358`), całkowite opróżnienie `TEMPORARY_11_1_MIGRATION_ALLOWLIST = set()` (0 naruszeń w 42 plikach) oraz ustanowienie nowego nienaruszalnego baseline'u Z16 na hashu `07c46843f354662bb2a9799bad127134f3359ef0` (Pozycje 19–26).

### 🔹 INC-AVT-017 (Hotfix 11.1.2: Neutralizacja Literałów Wykonywalnych — Z16-amendment #7)
- **Status:** `RESOLVED (Hotfix 11.1.2, Commit 1 — Z16-amendment #7, hash 74766d80a06e0dbb880dc75c5d14cecea2afb766)`
- **Rozwiązanie:** Dynamiczna diaryzacja w `avt_linter.py:8620–8642` bez obiektu `self` z zachowaniem Testu 150, dynamiczne reguły dla nieodmiennych toponimów francuskich w `avt_linter.py:1027–1035, 7071` ze zbioru `INDECLINABLE_FRENCH_TOPONYMS` z zachowaniem Testu 107, uogólnienie wyzwalaczy w `rules.py:3077, 3182, 3360` oraz usunięcie tokenu z `series_memory.py:8431, 8500`.

### 🔹 INC-AVT-018 (Hotfix 11.1.2: Rozszerzenie Bramki 2 i Neutralizacja Egzemplifikacji — Z16-amendment #8)
- **Status:** `RESOLVED (Hotfix 11.1.2, Commit 2 — Z16-amendment #8, hash 1b540e30fd2e109aceaa42fc0efcf1457afc42a6)`
- **Rozwiązanie:** Rozszerzenie regexu `RE_EXEMPLAR_INTRODUCERS` w `verify_purity.py:49–51` bez globalnego `re.IGNORECASE` (użycie inline `(?i:...)`), neutralizacja przykładów i imion w regułach `rules.py` (linie 305, 992, 1041–1042, 1118, 1143, 1550–1552, 2239–2242, 2299–2300), komentarzach i etykietach `avt_linter.py` (linie 217, 1045, 2119, 7166, 7174) oraz docstringach i komentarzach `series_memory.py` (linie 2325, 2333, 2341, 3111, 3122, 3548, 3892, 4230–4232, 8388). Ustanowienie nowego baseline'u ochrony Z16 (`1b540e3`).

### 🔹 INC-AVT-019 (Hotfix 11.1.2a: Mikro-domknięcie Literałów Z1 w rules.py — Z16-amendment #9)
- **Status:** `RESOLVED (Hotfix 11.1.2a, Commit 1 — Z16-amendment #9, hash d31096945a977d6a179891d87dcfd2a05c0c5bca)`
- **Rozwiązanie:** Neutralizacja przykładów w `FILAR XXVII` (`rules.py:309, 311, 312` -> `<Nazwisko>-sensei`, `Pani <Nazwisko>`) oraz w `FILAR CXXXII` (`rules.py:1117` -> `[plemię <Nazwa> / kapitana]`) w ramach formalnego `Z16-amendment #9` z re-certyfikacją 5 pułapek Z16 i testem negatywnym Bramki 8. Reklasyfikacja werdyktu Hotfixu 11.1.2 do `ZGODNY Z ZASTRZEŻENIAMI` i ustanowienie nowego baseline'u Z16 (`d31096945a977d6a179891d87dcfd2a05c0c5bca`).

### 🔹 INC-AVT-020 (Hotfix 11.1.3: Naprawa Indeksowania Krotek w log_scene_discourse)
- **Status:** `RESOLVED (Hotfix 11.1.3, Commit 1 — hash 25e93008061e89cf2bb52554e2eb27ef5c9528d2)`
- **Rozwiązanie:** Zastąpienie błędnych indeksów `b[0][3]` oraz `b[-1][4]` w `translator.py:5634–5635` bezpiecznym odczytem właściwości `start` i `end` z obiektu `SSAEvent` (`b[0][1]` oraz `b[-1][1]`), eliminujące wyjątek `IndexError: tuple index out of range` przy rejestracji dyskursu w `EpisodeFlightRecorder`.

### 🔹 INC-AVT-021 (Hotfix 11.1.3: Arbitraż Płci Ról Epizodycznych P2 i Tarcza Krzyku Bojowego)
- **Status:** `RESOLVED (Hotfix 11.1.3, Commit 2 — hash ed9dc5f33c0ea341db5b0a34c73413f135401bda)`
- **Rozwiązanie:** Rozszerzenie `SECONDARY_LEXICAL_MALE_NOUNS` o rzeczowniki ról obozowych i zbrojnych w `series_memory.py`, zachowanie `spk_clean` na czas sprawdzenia `character_registry` i `series_bible` w `translator.py`, zawężenie `tag_is_fem` do sopranu, tarcza krtaniowa F0 <= 135 Hz vs F0 > 135 Hz oraz respektowanie płci męskiej z Fazy 1 przed nadpisaniem wysokim F0 okrzyku bojowego (`weto_krzyku_f0`).

### 🔹 INC-AVT-022 (Hotfix 11.1.3: Rejestracja Czasu Odpowiedzi, Zużycia Tokenów i Podsumowania Stylów)
- **Status:** `RESOLVED (Hotfix 11.1.3, Commit 1 — hash 25e93008061e89cf2bb52554e2eb27ef5c9528d2)`
- **Rozwiązanie:** Przekazywanie `response_time_sec` i `token_usage` do `log_phase1_batch` w `translator.py:3971` z pomiarem czasu `time.perf_counter()` oraz przekazywanie słownikowego zestawienia `style_report.get_summary()` do `log_ingestion` w `translator.py:4994`.

### 🔹 INC-AVT-021a (Hotfix 11.1.3a: Domknięcie P2-1, P3-1 i P3-2 — tarcza F0 <= 135 Hz dla SpeakerVoiceClassifier i izolacja wątkowa tokenów)
- **Status:** `RESOLVED (Hotfix 11.1.3a, Commity 1–2 — certyfikacja kodu: 842b9e945cfed4bab04e2d3864a1cd657e50f832)`
- **Rozwiązanie:** Dopuszczenie przedrostka `"niski tembr"` w `translator.py:2302` odblokowujące tarczę krtaniową F0 <= 135 Hz dla rzeczywistych etykiet `SpeakerVoiceClassifier.classify_pitch_register(f0)` przy `raw_phase1_gender=None`, izolacja wątkowa `_thread_local.last_batch_token_usage` w `translator.py` oraz ujednolicenie testów `T11.1.3_2` i `T11.1.3_4` z rzeczywistymi obiektami potoku.

### 🔹 INC-AVT-023 (Hotfix 11.1.4: Detekcja Yakuwarigo, Code-Switchingu JA/EN i Ochrona Przed Fałszywym Dialektem)
- **Status:** `RESOLVED (Hotfix 11.1.4, Commity 1–2 — certyfikacja kodu: 38ad629ae1ec343d3dfeb9d4e57691339dc2ffb5)`
- **Rozwiązanie:** Usunięcie niezakotwiczonych pojedynczych znaków `"べ"` i `"おら"` z `jp_dialect_tokens` w `whisper_disambiguator.py` eliminujące fałszywą klasyfikację pospolitych czasowników (`述べた`, `比べれば`, `全て`, `直らない`). Rozszerzenie wzorców o formy zakotwiczone oraz rejestry *Yakuwarigo* (`-aru`, `-yaru`, `-desu wa`, `-masu wa`, `-desu koto`, `-ssu`, `-nano`). Dodanie kategorii `CODE_SWITCH_EN` dla hybrydowych zapożyczeń katakanowych z wykluczeniem terminów systemowych i aktywacja wytycznej DYN_1 w `rules.py`.

### 🔹 INC-AVT-024 (Hotfix 11.1.4: Most Idiolektów CharacterDossier -> Lean Brief i Persystencja Speech Register w SeriesBible)
- **Status:** `RESOLVED (Hotfix 11.1.4, Commity 1–2 — certyfikacja kodu: 38ad629ae1ec343d3dfeb9d4e57691339dc2ffb5)`
- **Rozwiązanie:** Przenoszenie `speech_style_pl` i `idiolect_matrix` z profilera do zwięzłego briefu w `profiler.py` (`Styl i idiolekt: ...`), zasilanie metadanych partii `speech_style_pl` i `notes` w `translator.py`, zapis i persystencja pola `speech_register` w `SeriesBible` z formatowaniem `[Rejestr: ...]` w `format_scoped_for_batch` oraz nadpisywanie notki relacji (`wyodrębniono z relacji serii`) przy nadejściu zweryfikowanej tożsamości P0.

### 🔹 INC-AVT-025 (Hotfix 11.1.4: Word-Level ASR Whisper, Deduplikacja Prefiksów i Normalizacja Etykiet @Handle)
- **Status:** `RESOLVED (Hotfix 11.1.4, Commity 1–2 — certyfikacja kodu: 38ad629ae1ec343d3dfeb9d4e57691339dc2ffb5)`
- **Rozwiązanie:** Włączenie `word_timestamps=True` i przypisywanie słów po środkach czasowych `[start, end]` w `whisper_engine.py`, odcinanie powtórzonych prefiksów ASR z poprzedniej linii w pętli sanityzacji `translator.py`, dopuszczenie nazw mówców z prefiksem `@` w normalizatorze majuskuły oraz ochrona wysokiego rejestru dam/ojou-sama przed slangiem gamingowym w promptcie weryfikatora.

### 🔹 INC-AVT-026 (Hotfix 11.1.4a: Priorytetyzacja Rejestru Yakuwarigo -aru/-yaru i Code-Switchingu oraz Synchronizacja Telemetrii do Notes)
- **Status:** `RESOLVED (Hotfix 11.1.4a, Commity 1–2 — certyfikacja kodu: d4a456cf95d7c002bec9c0a18d1eb69070d78424)`
- **Rozwiązanie:** Przeniesienie ewaluacji `-aru/-yaru` oraz `Code-switching JA+EN` przed szorstki żargon z zaimkiem `ore` w `detect_japanese_pragmatic_register` (rozszerzenie leksyki o formy `頼んでるある`, `はずある`, `何やるか`, etc.), a także wczesna ewaluacja audio JP i rejestru socjopragmatycznego w `_process_single_batch` przed wygenerowaniem mikro-tagu `line_dry_telemetry` i doklejeniem do `notes`.

### 🔹 INC-AVT-027 (Hotfix 11.1.4a: Arbitraż Kwantyfikatora Dualnego „you two” / „お二人” w Scenach Mieszanych)
- **Status:** `RESOLVED (Hotfix 11.1.4a, Commity 1–2 — certyfikacja kodu: d4a456cf95d7c002bec9c0a18d1eb69070d78424)`
- **Rozwiązanie:** Wykrywanie wykładników podwójności w 2. osobie (`you two`, `both of you`, `お二人`, `二人とも`) w `_resolve_line_addressee` oraz `_process_single_batch`; weryfikacja płci uczestników sceny w `untranslated_in_batch` i wymuszenie męskoosobowej liczby mnogiej (`line_you_grp = "VIRILE"` i `has_male_addressee_in_line = True`) przy obecności co najmniej jednego mężczyzny i jednej kobiety.

### 🔹 INC-AVT-028 (Hotfix 11.1.4a: Korekta Tokenu Hiragany „やで” w WhisperDisambiguator i Detekcja Plansz Cennika)
- **Status:** `RESOLVED (Hotfix 11.1.4a, Commity 1–2 — certyfikacja kodu: d4a456cf95d7c002bec9c0a18d1eb69070d78424)`
- **Rozwiązanie:** Naprawa literówki w tokenie zachodniojapońskim `"やde"` -> `"やで"` w `WhisperDisambiguator.detect_batch_discourse_categories` oraz dodanie weryfikacji strukturalnej plansz wyliczenia punktowego / cennika (`^\d[\d,.\s]*\s*(?:points?|pts|candies|coins|gold|yen|¥)\s*:\s*\S+`) w `detect_event_visual_type` uniemożliwiającej błędną klasyfikację planszy jako dialogu w stylu Default.

### 🔹 INC-AVT-029 (Hotfix 11.1.4b: Serializacja Inferencji CUDA `_infer_lock` i Ochrona Przed Crashem CTranslate2 align w `whisper_engine.py`)
- **Status:** `RESOLVED (Hotfix 11.1.4b, Commity 1–2 — certyfikacja kodu: bd52c4c88e859b86e864ab9db96b8233a0be7d3e)`
- **Rozwiązanie:** Otoczenie wywołań `model.transcribe` oraz konsumpcji generatora `list(segments)` blokiem `with self._infer_lock:` w `transcribe_audio_slice` oraz `transcribe_batch_scene` (eliminacja kolizji wielowątkowej i błędu Access Violation 0xC0000005 w CTranslate2) oraz wyłączenie `word_timestamps=False` dla modeli o architekturze `kotoba`/`distil` (ochrona przed niestabilną funkcją C++ `Whisper::align` na 2-warstwowym dekoderze Distil-Whisper w float16).

### 🔹 INC-AVT-030 (Hotfix 11.1.5 / INC-AVT-026 z audytu 20261111_211338: Bramkowanie tagów socjolingwistycznych Rejestr: przez profil postaci)
- **Status:** `RESOLVED (Hotfix 11.1.5, Commity 1–2 — certyfikacja kodu: 3c70a557b77ce2b83bf9bcf5875bf6fe57f70db7)`
- **Rozwiązanie:** Wdrożenie deterministycznej metody `WhisperDisambiguator.validate_pragmatic_register_against_speaker` weryfikującej zgodność wykrytych dynamicznych etykiet pragmatycznych z `character_dossiers`, `character_registry` oraz cechami mówcy: blokada `Rejestr dziewczęcy` dla mężczyzn i seniorów, blokada `Szorstki żołnierski / Bojowy` dla rejestru dworskiego bez krzyku bojowego w prozodii, neutralizacja `Feudalny poddańczy / Wasal` dla standardowego keigo bez archaizmów feudalnych oraz walidacja rejestrów gwarowych (0.00 PLN).

### 🔹 INC-AVT-031 (Hotfix 11.1.5 / INC-AVT-027 z audytu 20261111_211338: Filtr składniowy 3. osoby adresata, in-memory sanitacja SeriesBible i ochrona glosariusza)
- **Status:** `RESOLVED (Hotfix 11.1.5, Commity 1–2 — certyfikacja kodu: 3c70a557b77ce2b83bf9bcf5875bf6fe57f70db7)`
- **Rozwiązanie:**
  1. Wdrożenie `_is_third_person_syntactic_context` w `scene_discourse.py` eliminującego fałszywy `lock=True` po zwrotach 3. osoby (`on behalf of`, `under`, `worthy of`, `of`, `to`, dopełniacz saksoński `'s`, orzeczenia 3. os.) oraz filtr obecności w scenie z `dramatic_sequences.characters_present`.
  2. Izolacja napisów ekranowych `is_sign` przed dziedziczeniem adresatów i czysta reprezentacja `SpeakerTurn` (eliminacja `'None'` i `'AMBIGUOUS'`).
  3. Konsensus płci per aktor w odcinku (`compute_actor_gender_consensus`) i egzekwowanie `male_only_scene` / `female_only_scene` z topologii sekwencji dramatycznych.
  4. In-memory reconcyliacja płci (`_reconcile_registry_gender_in_memory`), rewalidacja toponimów (`_sanitize_entity_categories_in_memory`) i wzbogacanie zdegenerowanych paradygmatów (`_enrich_declensions_from_profile`) w `series_memory.py` z zachowaniem 0 B diffu na dysku (Z16).
  5. Normalizacja znaczników `<i>...</i>` i zbędnych tagów kursywy na stylach `Italics` oraz ochrona zablokowanego glosariusza przed dryfem synonimicznym Fazy 2 w `translator.py`.

---
## 📐 4. METRYKI OPERACYJNE POTOKU
- **Ograniczenia Ekranu ASS:** `CPS_PL <= 17.0` (dyskwalifikacja `> 20.0`), `CPL <= 38`, max 2 wiersze.
- **Podłoga Gęstości Seiyū:** `CPS_target(rho_x) = min(13.5, 7.5 + 0.5 * rho_x)` dla `rho_x >= 9.0 mor/s`.
- **Progi Golden Corpus:** Anchor Scenes = **100.0% PASSED**, Broader Corpus `>= 99.0%`, Atrybucja Płci `>= 99.8%`.
- **Macierz testowa Standardu 11.1.5:** `tests/` = `347 passed`, `test_system.py` = `71 passed, 153 deselected` (`5/5` pułapek Z16 `PASS`, 0 failing, Zero Regression Lock).

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
| **2026-11-08** | `ARB-045` | Higiena Kodu | **Z16-amendment #9**: Neutralizacja ostatnich przykładów Z1 w `rules.py` (`FILAR XXVII` L309–312, `FILAR CXXXII` L1117) i re-certyfikacja baseline'u Z16 (`d310969`). | 0.00 PLN |
| **2026-11-09** | `ARB-046` | Telemetria / Dyskurs | **Telemetria Dyskursu i Arbitraż Ról Epizodycznych P2 (Standard 11.1.3)**: Naprawa indeksowania krotek w `log_scene_discourse` (INC-AVT-020), metryki czasu i zużycia tokenów Fazy 1 (INC-AVT-022), estymator kosztu P3-B (3150 tokenów), arbitraż płci ról epizodycznych P2 z ochroną F0 krzyku bojowego (INC-AVT-021) oraz rozstrzyganie virility diad mieszanych w POLYLOGUE (P3-A). | 0.00 PLN |
| **2026-11-10** | `ARB-047` | Telemetria / Testy | **Domknięcie Hotfixu 11.1.3a (P2-1, P3-1, P3-2)**: Odblokowanie tarczy F0 `<= 135 Hz` dla rzeczywistych etykiet `SpeakerVoiceClassifier`, izolacja wątkowa `_thread_local.last_batch_token_usage` w `translator.py` oraz ujednolicenie testów `T11.1.3_2` i `T11.1.3_4` z rzeczywistymi obiektami potoku. | 0.00 PLN |
| **2026-11-11** | `ARB-048` | Socjolingwistyka / ASR | **Wdrożenie Hotfixu 11.1.4 (P1-1..P1-6)**: Odkotwiczenie fałszywych dopasowań dialektu na czasownikach pospolitych, obsługa rejestru wojowniczki (-aru/-yaru), ojou-sama (-masu wa, -desu koto) oraz dziewczęcego (-nano), detekcja code-switchingu JA/EN (CODE_SWITCH_EN), most idiolektów CharacterDossier -> brief, persystencja speech_register w SeriesBible, word-level ASR Whisper z dedupem prefiksów i ochrona etykiet @Handle w translator.py (Z16-amendment #10). | 0.00 PLN |
| **2026-11-11** | `ARB-049` | Yakuwarigo / Dual / Cennik | **Wdrożenie Mikro-Hotfixu 11.1.4a (P2-RES-01, P2-RES-02, P3-RES-01, P3-RES-02)**: Priorytetyzacja rejestru -aru/-yaru i code-switchingu przed zaimkiem ore, wczesna synchronizacja rejestru do notes, arbitraż virility kwantyfikatora dualnego ('you two' / 'お二人') w diadach mieszanych, korekta tokenu hiragany やで oraz detekcja plansz wyliczeń punktowych w stylu Default (Z16-amendment #11). | 0.00 PLN |
| **2026-11-11** | `ARB-050` | Whisper / CUDA Thread-Safety | **Wdrożenie Mikro-Hotfixu 11.1.4b**: Serializacja inferencji GPU `with self._infer_lock:`, wyłączenie niestabilnego CTranslate2::Whisper::align (`word_timestamps=False`) dla modeli Kotoba/Distil-Whisper i czulszy VAD min_silence_duration_ms=140. | 0.00 PLN |
| **2026-11-11** | `ARB-051` | Dyskurs / Rejestr / Glosariusz | **Wdrożenie Hotfixu 11.1.5 (P1-1..P3-2)**: Bramkowanie telemetrii `Rejestr:` przez profil postaci (INC-AVT-030), in-memory reconcyliacja płci, toponimów i paradygmatów w `series_memory.py` (0 B diff na Z16), filtr składniowy 3. osoby `_is_third_person_syntactic_context` oraz obecności w scenie z `dramatic_sequences.characters_present` (INC-AVT-031), izolacja `is_sign`, konsensus płci aktora w odcinku, normalizacja znaczników `<i>` i ochrona zablokowanego glosariusza przed dryfem Fazy 2. | 0.00 PLN |

---

## Backlog 11.0 — N-05: Oczyszczenie regexów w `get_focused_rules_for_batch` z japońskich tokenów leksykalnych

**Status:** `RESOLVED (Standard 11.1, Commit 3 — Z16-amendment #2, hash 2b4bc7d)`
**Zaktualizowano:** 2026-11-07 (Commit 4 domykający Standard 11.0)
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

**Status:** `RESOLVED (Standard 11.0, commity 941fe44, fb94a02)`
**Zweryfikowano w audycie weryfikacyjnym 11.0:** `Artefakty/Raport_audytu_weryfikacyjnego_11_0_koncowy.md` — werdykt `FIX-C.1 BEZPIECZNA`, `FIX-C.2 BEZPIECZNA`, `FIX-C.3 BEZPIECZNA`
**Zidentyfikowano:** `Raport_audytu_arnold_toponym_i_duplikacji_bible.md` (2026-11-05, Defekt C)

### Problem

W `series_bible` token `<NAZWA_SZKOŁY_1>` istnieje wyłącznie jako jednowyrazowy alias nazwiska rekordu ANTHROPONYM `<NAZWA_POSTACI_1>`, a nie jako osobny wpis TOPONYM w `entity_categories`. W efekcie `is_non_character_entity("<NAZWA_SZKOŁY_1>")` (`series_memory.py:8606–8617`) zwraca `False`, a telemetria w kwestii z `relations with <NAZWA_SZKOŁY_1>` przypisuje `Adresat: <NAZWA_SZKOŁY_1> (FEMININE)`.

### Rozwiązanie (11.0)

Wdrożenie operacji `FIX-C.1` (ekstrakcja nazw instytucji/lokacji ze słownika, kotwic fabularnych i profilu odcinka do `entity_categories` jako `TOPONYM` pod kluczem `institutional_toponyms`, commit `941fe44`), `FIX-C.2` (odpięcie kolidującego jednowyrazowego nazwiska w RAM bez wywoływania zapisu na dysk, commit `941fe44`) oraz `FIX-C.3` (kontekstowa ochrona przyimków lokatywnych/relacyjnych w `is_non_character_entity` i filtr przyimkowy w `_detect_event_vocative`, commit `fb94a02`).


## Backlog 11.0 — N-07: Adresowanie mówców tłumu Mob* i rozbijanie identyfikatorów CamelCase

**Status:** `RESOLVED (Standard 11.0, commit 8c0037f)`
**Zweryfikowano w audycie weryfikacyjnym 11.0:** `Artefakty/Raport_audytu_weryfikacyjnego_11_0_koncowy.md` — werdykt `FIX-E.1 BEZPIECZNA`, `FIX-E.2 BEZPIECZNA`
**Zidentyfikowano:** `Raport_audytu_arnold_toponym_i_duplikacji_bible.md` (2026-11-05, Defekt E)

### Problem

1. `populate_secondary_actor_tags` (`series_memory.py:6941`) używa `re.findall(r"\b\w+\b", clean_tag.lower())`, co nie dzieli identyfikatorów CamelCase (`<GRUPA_TŁUMU_1>` typu `MobMan2`, `MobWoman`, `MeanGirl`), przez co mówcy tłumu otrzymują w `series_bible` `gender: "UNKNOWN"`.
2. W `scene_discourse.py` (`resolve_turn_addressee`) przy braku zweryfikowanej płci poprzedniego mówcy tłumu Forward Lookahead przypisuje jako adresata mówcę kolejnej sceny po cięciu montażowym (`<BYT_KRÓLEWSKI_1>`).

### Rozwiązanie (11.0)

Wdrożenie operacji `FIX-E.1` (rozbijanie granic CamelCase i cyfr w `_split_camel_case_tokens`, aktualizacja rekordów `UNKNOWN` w `populate_secondary_actor_tags`, podział w `resolve_lexical_label_gender` oraz ochrona par z sufiksem liczbowym w kroku `8b`) oraz `FIX-E.2` (izolacja mówców `Mob*`/`Crowd*` w Krokach 3 i 4 `resolve_turn_addressee` oraz filtr deiktyków 3. os. per klauzula w `_detect_event_vocative`).


## Backlog 11.0 — N-08: Historyczne rozszczepienie odcinka S2-02 w pliku bazowym <SERIA_BASE>_bible.json

**Status:** `OPEN` (P3, przeniesione do backlogu 11.1 — poza zakresem 11.0; wymaga uruchomienia `tools/consolidate_bibles.py --migrate-misplaced-season-episodes` lokalnie przez operatora poza reżimem Z16)
**Zaktualizowano:** 2026-11-07 (Commit 4 domykający Standard 11.0)
**Zidentyfikowano:** `Raport_audytu_weryfikacyjnego_10_6_3_defekt_D.md` oraz aneks uzupełniający (2026-11-05)

### Problem

Przed naprawą `_resolve_bible_path` w 10.6.3 (`FIX-D.1`) odcinek `S2 - 02` serii `<SERIA_BASE>` został zapisany w pliku `<SERIA_BASE>_bible.json` (`season_num=None`), podczas gdy odcinek `S2 - 01` zapisał się w `<SERIA_BASE>_2nd_Season_bible.json` (`season_num=2`). Ponieważ oba pliki są śledzone w repozytorium git i objęte ochroną Z16, a `consolidate_split_bibles` celowo nie łączy różnych sezonów (`None` vs `2`, zgodnie z `T10.6.3_7`), wpis ten pozostaje nienaruszony w 10.6.3.

### Rozwiązanie (11.0)

Dodanie w `tools/consolidate_bibles.py` opcjonalnej flagi `--migrate-misplaced-season-episodes` (uruchamianej lokalnie przez operatora poza reżimem Z16), która przenosi wpisy `episodes_translated` i `batch_stats` zawierające jawny znacznik `S2` z pliku `<SERIA_BASE>_bible.json` do `<SERIA_BASE>_2nd_Season_bible.json`.

