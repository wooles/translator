# 🧠 PAMIĘĆ PROJEKTU I STANU SESJI ANTIGRAVITY (PROJECT MEMORY & OPERATIONAL TELEMETRY)

Dokument ten stanowi zsynchronizowany rejestr stanu operacyjnego potoku, telemetrii CI/CD, historii incydentów oraz most wiedzy pomiędzy komputerami roboczymi (PC 1 i PC 2) dla asystenta AI Antigravity.
Zasady normatywne i aksjomaty inżynierskie definiuje wyłącznie `AGENTS.md` (Single Source of Truth).

---

## 🎯 1. AKTUALNY STATUS POTOKU (Stan na 12.10.2026)
- **Status CI/CD:** `STATUS: WDROŻONE I ZWERYFIKOWANE (157/157 PASSED) - VICTORY CONFIRMED`
- **Gałąź i Commit:** `main` (pełna integracja Standardu 3.0, Zero-Cosmetic Protocol, INC-AVT-004 i Autonomous Multi-Agent Mandate)
- **Środowisko:** Python 3.13 (.venv), Windows PowerShell, bezpośrednie klucze Google AI Studio API (`use_vertex = 0`)
- **Mandat Autonomicznego Zespołu Wieloagentowego:**
  Rozwiązywanie wszelkich błędów zgłoszonych przez Operatora odbywa się wyłącznie przez autonomiczny zespół wieloagentowy (Autonomous AVT Team) z podwójną kontradyktoryjną bramką jakości (Reviewers & Challengers) oraz niezależnym audytem kryminalistycznym (wymóg uzyskania werdyktu VICTORY CONFIRMED przed raportem końcowym).
- **Format pracy zespołu:** Hierarchiczny Protokół Czteroagentowy (Standard 3.0):
  * **OPERATOR (Człowiek):** Wyłączny właściciel praw zapisu I/O (autoryzacja komendą: `ZATWIERDZAM DOSSIER - WDROŻYĆ DO KODU`).
  * **AGENT 4:** Autonomous Operational Supervisor (Anti-Loop Watchdog, Triage, Dossier dla Operatora, weto Zero-Cosmetic: `STATUS: ODRZUCONO WEWNĘTRZNIE - WYKRYTO PUDROWANIE SYMPTOMÓW ZAMIAST NAPRAWY KODU SILNIKA`).
  * **AGENT 3:** Chief Epistemic Architect & AVT Dramaturge (Ontologia, 4-stopniowy audyt Root-Cause Deconstruction, kontrakty Pydantic, czerwony test).
  * **AGENT 1:** Lead Systems Implementer (Prototypowanie RAM, Diff Preview, eliminacja fabryk błędów u źródła).
  * **AGENT 2:** Adversarial Reviewer & ASS-Fuzzing (18 Wymiarów Audytu, Breathing Space Index).
  * **Żelazny Bezpiecznik Potoku:** Zero Premature Synthesis oraz Zero-Cosmetic Gate – bezwzględny zakaz pomijania Fazy 2 i Faz 3–4; każde Dossier musi zawierać [CERTYFIKAT ELIMINACJI ŹRÓDŁOWEJ] i opierać się na rzeczywistych logach laboratoryjnych ze środowiska RAM.

---

## 🔄 2. PROCEDURA SYNCHRONIZACJI WIELOSTANOWISKOWEJ (PC 1 <-> PC 2)

- **Na nowym/drugim PC (inicjalizacja):**
  ```powershell
  git add . ; git commit -m "Zapis przed pobraniem" ; git pull --no-rebase origin main --no-edit
  ```
- **Codzienna praca:**
  * Aby pobrać i zaktualizować kod o zmiany z drugiego PC: uruchom `POBIERZ_ZMIANY_Z_CHMURY.bat`.
  * Aby zatwierdzić i wysłać zmiany do drugiego PC: uruchom `WYSLIJ_ZMIANY_DO_CHMURY.bat`.
- Git wykonuje bezpieczne scalenie trójstronne (3-way merge) – lokalne zmiany nie są nadpisywane.

---

## 📋 3. REJESTR ROZWIĄZANYCH INCYDENTÓW TRANSLATORSKICH

### 🔹 INC-AVT-001 (*Mahou Shoujo Ikusei Keikaku: Restart*)
- **Defekty:** Błędna męska atrybucja fleksyjna głównej bohaterki (Musia), skażenie cytatów męskich w mowie kobiet, nieodmienność obcych imion żeńskich na spółgłoskę.
- **Wdrożenie 5 Warstw:**
  1. *Warstwa 1 (`profiler.py`):* Topologia sceny i wymóg concordancji żeńskiej w briefie.
  2. *Warstwa 2 (`series_memory.py`):* Katalog `FOREIGN_FEMALE_CONSONANT_NAMES`, ochrona imion męskich na `-a`, sanitizery dopełniacza negacji.
  3. *Warstwa 3 (`rules.py`):* Filary CLXXXVII (Topologia Płci) i CLXXXVIII (Rekcja Zaprzeczona & Kanon Mangowy), Krok 3 CoT (budżet 6144).
  4. *Warstwa 4 (`avt_linter.py`):* Tarcza Cytatów (`QuoteShield`) chroniąca przed $W_i \to W'_i$, Krok 4g sanacji mianownikowej.
  5. *Warstwa 5 (`test_system.py`):* Asercje 139–142, stan testów: 142/142 PASSED.

### 🔹 INC-AVT-002 (*Sasaki to Pii-chan S2*)
- **Defekty:** 
  1. Diada chłopięca Boy A / Boy B: żeńska forma (*kupiłaś* -> *kupiłeś*).
  2. Pakt Sasaki <-> Peeps: wzajemna błędna fleksja (*wróciłaś* -> *wróciłeś*, *przewidziałaś* -> *przewidziałeś*).
  3. Tytulatura monarsza Króla Herz: błędna kalka z EN (*twoja wysokość* -> *Wasza Wysokość*).
  4. Akustyczna halucynacja fatyczna po dyrektywie: *Dzikie?* -> *Rozumiem.*
  5. Mowa w stylu `Italics` (telefon Shizuki do Sasakiego) błędnie uznana za solilokwium (*Spałaś? Czy zrobiłaś* -> *Spałeś? Czy zrobiłeś*).
  6. Rząd przyimka 'o' w odniesieniu do osoby: biernik zamiast miejscownika (*wspomniałam o ciebie* -> *wspomniałam o tobie*).
- **Wdrożenie 5 Warstw:**
  1. *Warstwa 1 (`series_memory.py`):* Obsługa ról numerowanych (`Boy A`, `Boy 1`, `Girl A`) z priorytetem P0 cast-lock dla seiyū żeńskich. Odmaskowanie monarchów w `is_non_character_entity()`.
  2. *Warstwa 2 (`Sasaki_to_Pii_chan_2nd_Season_bible.json`):* Rejestracja relacji addressee `Sasaki <-> Peeps` i `Shizuka -> Sasaki`. Rejestracja Króla Herz. Toponim *Równiny Rectan* jako `[NIE-POSTAĆ]`.
  3. *Warstwa 3 (`rules.py`):* Kanon PWN tytulatury monarszej w Filarze LX.
  4. *Warstwa 4 (`avt_linter.py`):* Obsługa `has_2nd_person_marker` w stylach `Italics` wykluczająca fałszywe solilokwium; deterministyczny sanitizer tytulatury, kakegoe oraz rządu przyimka `o tobie`.
  5. *Warstwa 5 (`test_system.py`):* Test 155 (`test_sasaki_to_piichan_s2_holistic_incident_guard`), stan testów: 155/155 PASSED (100.0%).

### 🔹 INC-AVT-003 (*Hyouken no Majutsushi ga Sekai wo Suberu S2*)
- **Defekty:**
  1. Ślepota AniList na zapytania z sufiksem sezonu `S2` skutkująca błędem 404, pustym wynikiem i brakiem pobrania zweryfikowanej obsady z serii macierzystej.
  2. Błąd odwróconej inferencji relacji A -> B w `update_from_episode_profile()`: przypisanie tagu `[KOBIETA (Adresat)]` i form 2. os. lp. do podmiotu mówcy (Ray White) oraz form męskich do postaci żeńskich (Ariane, Rebecca, Lydia) przez wadliwy warunek `panie / pan`.
  3. Przebicie heurystyki relacji nad zweryfikowaną płcią z AniList (`has_verified_gender = True`) i blokada nadpisywania wpisów heurystycznych.
  4. Skażenie bazy wiedzy `Hyouken_no_Majutsushi_ga_Sekai_wo_Suberu_S2_bible.json` i zapętlenie cache w `get_anime_context()`.
- **Wdrożenie 5 Warstw:**
  1. *Warstwa 1 (`metadata.py`):* Normalizacja zapytań AniList z fallbackiem `strip_season_suffix()` odcinającym sufiksy sezonowe (`S2`, `Season 2`, `Part 2`, `Cour 2`, `2nd Season`) oraz priorytet P0 dla zweryfikowanej płci (`has_verified_gender = True`).
  2. *Warstwa 2 (`series_memory.py` & JSON):* Eliminacja odwróconej inferencji w `update_from_episode_profile()` (izolacja slotu mówcy od tagów adresatywnych, usunięcie wadliwego warunku linii 3951-3952, odblokowanie nadpisywania wpisów relacyjnych przez dane zweryfikowane). Oczyszczenie `Hyouken_no_Majutsushi_ga_Sekai_wo_Suberu_S2_bible.json`.
  3. *Warstwa 3 (`rules.py` / `AGENTS.md`):* Zero-Cosmetic Protocol, 4-stopniowy audyt fabryki błędów, [CERTYFIKAT ELIMINACJI ŹRÓDŁOWEJ].
  4. *Warstwa 4 (`avt_linter.py`):* EpisodeQualityGate zasilany nieskażonym rejestrem postaci z priorytetem zweryfikowanej płci P0.
  5. *Warstwa 5 (`test_system.py`):* Test 156 (`test_hyouken_s2_root_cause_anilist_fallback_and_addressee_guard`), stan testów: 156/156 PASSED (100.0%).

### 🔹 INC-AVT-004 (*Tensei Kizoku, Kantei Skill de Nariagaru 3rd Season*)
- **Defekty:**
  1. Toponim Seitz: błędna odmiana "ci z Seitzem" zamiast "ci z Seitz" w obecności znaków nowego wiersza `\N` łamiących dopasowania regexowe `\b`.
  2. Liczba mnoga audytorium: "Mam do ciebie pytanie!" do wrogich żołnierzy zamiast "Mam do was pytanie!" przy wykrytym audytorium mnogim.
  3. Męska postać w retrospekcji: Verzud Captain do Young Brahama "Nie bądź naiwna" zamiast "Nie bądź naiwny" (błędna atrybucja żeńska młodocianego chłopca).
  4. Harmonizacja par ról z zaimkiem dzierżawczym: "Jesteś moją najlepszą uczennicą" do męskiego Brahama zamiast "Jesteś moim najlepszym uczniem".
  5. Skażenie audio seiyū: syn Zahta (*Zaht's Kid*) oznaczony jako kobieta przez wysoki tembr dorosłej aktorki seiyū ("Wiem, ale wolałabym...").
  6. Wołacz męski a forma czasownika: "Tylko ty byłaś w stanie, Rietzie" do mężczyzny Rietza zamiast "byłeś w stanie".
- **Wdrożenie 5 Warstw:**
  1. *Warstwa 1 (`translator.py` & `series_memory.py`):* Blokada atrybucji `FEMALE` dla ról dziecięcych męskich (`is_boy_or_male_role`) na podstawie wysokiego tembru audio seiyū ($F_0 \ge 195\text{ Hz}$) oraz kontrakt `speaker_grammatical_gender`.
  2. *Warstwa 2 (`series_memory.py` & JSON):* Uniwersalna ochrona toponimów `(?:^|\\[Nnh]|[^\w])` odporna na znaczniki `\N`, katalog `KNOWN_FANTASY_TOPONYMS`, blokada wstrzykiwania toponimów do słownika postaci w `update_from_episode_profile()`, rekurencyjne dziedziczenie płci dla prefiksów wieku (`Young`, `Kid`, `Little`, `Baby`, `Child`, `Młody`, `Mały`), sanacja `Tensei_Kizoku_Kantei_Skill_de_Nariagaru_bible.json`.
  3. *Warstwa 3 (`whisper_disambiguator.py` & Prompty):* Rozszerzenie japońskich markerów mnogich (`anta-tachi`, `temee-ra`, `kimi-tachi`) i angielskich wołaczy zbiorowych (`you guys`, `soldiers`, `troops`, `men`) z wymuszeniem `addressee_is_group = True`.
  4. *Warstwa 4 (`avt_linter.py`):* `harmonize_2nd_person_singular_to_plural_pronouns()` z odpornością na znaki podziału linii `\N`, rozszerzenie `PLURAL_2ND_PERSON_VERB_PAT` o końcówki spółgłoskowe trybu rozkazującego (`-czcie`, `-ńcie`, `-żcie`, `-rzcie`, `-dźcie`, `-ście`, `-źcie`), strażnik składniowy miejscownika dla `powiecie`, obsługa negacji trybu rozkazującego `nie bądź` + przymiotnik, kaskadowe rozszerzenie orzeczników o zaimki dzierżawcze (`swoim`/`swoją`, `waszym`/`waszą`), deterministyczna tarcza wołacza męskiego `decl["W"]` zakotwiczona interpunkcją.
  5. *Warstwa 5 (`test_system.py`):* Test 157 (`test_tensei_kizoku_s3_root_cause_vocative_and_audience_guard`), 157/157 PASSED (100.0%).

---

## 📐 4. METRYKI OPERACYJNE POTOKU I ARCHITEKTURA ANTY-GOODHART

- **Fizyczne Ograniczenia Ekranu ASS:**
  * $\text{CPS} \le 17.0$ (tempo czytania; próg dyskwalifikacji $\text{CPS} > 20.0$).
  * $\text{CPL} \le 38$ znaków na wiersz, maksymalnie 2 wiersze na planszę.
- **Asymetryczna Studnia Potencjału (Asymmetric Dead-Band Potential):**
  * Zabezpieczenie przed kastracją dramaturgiczną: w gęstym dialogu seiyū ($\rho_x = \text{moras}(x) / \Delta t \ge 9.0$) obowiązuje minimalna podłoga CPS:
    $$\text{CPS}_{\text{target}}(\rho_x) = \min(13.5, \; 7.5 + 0.5 \cdot \rho_x)$$
  * Odpowiedzialność implementacyjna: algorytm selekcji kandydata zintegrowany w module `translator.py` / `verifier.py` (Script Doctor).
- **Progi Jakościowe Golden Corpus:**
  * Anchor Scenes (Sceny Kotwiczące): bezwzględne **100.0% PASSED** (Zero Regression Tolerance).
  * Broader Corpus: $\ge 99.0\%$ PASSED.
  * Atrybucja Płci: $\ge 99.8\%$ PASSED.

---

## 🛡️ 5. REJESTR DŁUGU TECHNICZNEGO I ARBITRAŻY ARCHITEKTONICZNYCH

| Data | ID Decyzji | Obszar | Opis Rozstrzygnięcia | Koszt |
| :--- | :--- | :--- | :--- | :--- |
| **2026-10-03** | `ARB-001` | Płeć / Kanon | Wdrożenie `FOREIGN_FEMALE_CONSONANT_NAMES` i `QuoteShield` w Warstwie 4 dla ochrony cytatów. | 0.00 PLN |
| **2026-10-10** | `ARB-002` | Onomastyka / Realm Masking | Naprawa `is_non_character_entity()` — encje zarejestrowane jawnie jako postaci w `characters` mają priorytet nad toponimami glosariusza (`Herz` vs `Kingdom of Herz`). | 0.00 PLN |
| **2026-10-10** | `ARB-003` | Mowa Zapośredniczona | Styl `Italics` z markerami 2. osoby (`has_2nd_person_marker`) traktowany jako rozmowa (telefon/radio), a nie solilokwium wewnętrzne. | 0.00 PLN |
| **2026-10-10** | `ARB-004` | Granica Determinizmu | Brak aktywnych mikro-zapytań LLM w Warstwie 4; zachowano 100% determinizmu offline (0.00 PLN). Dług technologiczny regexów: 0. | 0.00 PLN |
| **2026-10-11** | `ARB-005` | Architektura / Jakość | **Zero-Cosmetic Protocol (Standard 3.0)**: Kategoryczny zakaz uznawania za rozwiązanie poprawek w JSON/linterze/ASS bez naprawy silnika Pythona. Weto Agenta 4. | 0.00 PLN |
| **2026-10-11** | `ARB-006` | Metadane / API | **AniList Season Fallback**: Automatyczne usuwanie sufiksów sezonowych (`S2`, `Season 2` etc.) w przypadku błędu 404 zapytania bazowego, gwarantujące pobranie kanonicznej obsady. | 0.00 PLN |
| **2026-10-11** | `ARB-007` | Pamięć Serii / Relacje | **Strict Addressee Slot Separation & P0 Gender Priority**: Tagi `[... (Adresat)]` i cechy 2. os. lp. aplikowane wyłącznie do odbiorcy (idx=1), zakaz modyfikacji cech podmiotu mówcy (idx=0). Zweryfikowana płeć AniList ma priorytet P0 nad heurystykami. | 0.00 PLN |
| **2026-10-12** | `ARB-008` | Onomastyka / Toponimy | **Toponym Origin & ASS `\N` Isolation**: Zastąpienie `\b` uniwersalnym separatorem granic `(^|\\[Nnh]|[^\w])` chroniącym przed łamaniem dopasowań przez twardy enter ASS `\N`. Dodanie `KNOWN_FANTASY_TOPONYMS` i ochrona relacji pochodzenia. | 0.00 PLN |
| **2026-10-12** | `ARB-009` | Składnia / Liczba Mnoga | **Plural Addressee Guard & Consonant Imperatives**: Wykrywanie audytorium mnogiego w WDD i linterze z obsługą spółgłoskowych tematów rozkazujących (`-czcie`, `-ńcie`, `-żcie` itd.) oraz strażnikiem homonimicznym `powiecie` (rzeczownik w miejscowniku vs czasownik). | 0.00 PLN |
| **2026-10-12** | `ARB-010` | Płeć / Seiyū Audio | **Age-Variant Gender Inheritance & Seiyū Boy Role Guard**: Rekurencyjne dziedziczenie płci z imienia bazowego dla prefiksów wieku (`Young`, `Kid`) oraz twardy bezpiecznik blokujący nadpisywanie płci postaci chłopięcych przez akustyczny pitch dorosłych aktorek seiyū. | 0.00 PLN |
| **2026-10-12** | `ARB-011` | Fleksja / Wołacz | **Masculine Vocative Shield**: Deterministyczna harmonizacja form 2. os. lp. w oparciu o wołacz ze słownika odmian (`decl["W"]`) zakotwiczony interpunkcją (`Rietzie, ... byłaś -> byłeś`), chroniący orzeczenia 3. osoby. | 0.00 PLN |
