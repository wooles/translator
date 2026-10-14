# 🏛️ KODEKS ZASAD POTOKU AVT (WORKSPACE RULES — TRANSLATOR STANDARD 4.0)

Dokument ten stanowi jedyne źródło prawdy (Single Source of Truth) definiujące nienaruszalne reguły architektoniczne, lingwistyczne i procesowe asystenta AI oraz zespołów wieloagentowych w repozytorium `translator`.

---

## 🎯 1. NADRZĘDNA FILOZOFIA: ELIMINACJA PRZYCZYN ŹRÓDŁOWYCH W 5 WARSTWACH
1. **Uwagi Operatora jako Drogowskaz Taksonomiczny:** Każde zgłoszenie błędu wskazuje na awarię całej klasy zjawisk w silniku. Obowiązuje kategoryczny zakaz ograniczania naprawy do pojedynczego słowa, zdania czy tytułu anime.
2. **Obowiązkowy Protokół 5 Warstw (Ingress -> State -> Egress):**
   Każda modyfikacja architektoniczna musi symetrycznie zabezpieczać cały potok:
   - **Warstwa 1 (Profiler & Triangulacja – `profiler.py`, `metadata.py`):** Epistemiczna Triangulacja Płci (asymetryczna akustyka F0 `librosa.pyin` + morfosyntaktyka JA *yakuwarigo* + koreferencja `spaCy` EN z izolacją podmiotu `nsubj`), odporny parsing napisów (`pysubs2`), kanoniczny fallback sezonowy API (`strip_season_suffix`).
   - **Warstwa 2 (Pamięć Serii & Ontologia – `series_memory.py`, `scene_discourse.py`):** Modele Pydantic (`CharacterProfile`, `CharacterIdentity`, `PersonaInterval`), klasyfikacja ontologiczna (`ANTHROPONYM`, `TOPONYM`, `CHREMATONYM`), Automat Tożsamości Diegetycznej (`apparent_gender` vs `true_gender`), dziedziczenie aliasów wiekowych (`Young/Child X`), `SpeakerTurn` (propagacja liczby mnogiej i Dyadic Turn-Taking 2. osoby) oraz zamrożona matryca 7 przypadków `DeclensionParadigm`.
   - **Warstwa 3 (Kanon & Kontrakt Tłumacza – `translator.py`, `rules.py`, `manga_canon.py`):** Nadrzędność oficjalnego polskiego kanonu mangowego. Czyste prompty nastawione na dramaturgię i subtekst seiyū (Lean Script Doctor ~5 800 znaków), zasilane twardym kontraktem Pydantic (`speaker_gender`, `target_gender`, `addressee_number`, `DeclensionParadigm` z nakazem odmiany przez przypadki).
   - **Warstwa 4 (Deterministyczna Bramka Jakości – `avt_linter.py`, `translator.py`):** W 100% deterministyczny silnik korekty morfosyntaktycznej post-generation oraz kontroli technicznej (0.00 PLN, brak wywołań LLM).
   - **Warstwa 5 (Tarcza Regresyjna CI/CD – `test_system.py`):** Atomowe testy rodzin izomorficznych (minimum 5 różnych leksykalnie przykładów na klasę problemu + kontrprzykłady negatywne).

---

## 🚫 2. ŻELAZNY PROTOKÓŁ ZERO-COSMETIC I 4 RYGLE ANTY-PROTEZOWE
Kategorycznie ZAKAZUJE SIĘ uznawania jakiegokolwiek błędu za naprawiony poprzez:
1. **Ręczną edycję danych lub wyjścia:** Modyfikację plików `*_bible.json`, glosariuszy, cache'u lub wyjściowych napisów `.ass`/`.srt` (pliki danych mogą zmieniać się wyłącznie jako automatyczny rezultat działania naprawionego kodu Pythona).
2. **Łatanie powierzchniowe w Linterze:** Dopisywanie doraźnych regexów w `avt_linter.py` maskujących pojedynczy objaw bez naprawy reprezentacji wiedzy w Warstwach 1–3.
3. **Ukryte Hardkodowanie w Kodzie Pythona (Zero-Literal & Zero-Stem Leakage):** Umieszczanie w produkcyjnych plikach `.py` (poza `test_system.py`) konkretnych imion własnych, nazw krain, frakcji czy ich rdzeni słowotwórczych pochodzących ze zgłoszenia błędu (zakaz słowników wyjątków typu `EXCEPTIONS = {"Imię": "Forma"}`).
4. **Pozorowane „Łatanie Promptem” (No Prompt-Stuffing):** Dopisanie samej instrukcji tekstowej do promptu LLM bez wdrożenia deterministycznej logiki w Pythonie (parsera, reguły grafu dyskursu, walidatora Pydantic i korektora morfosyntaktycznego).

---

## 🎙️ 3. EPISTEMICZNA TRIANGULACJA PŁCI, AUTOMAT DIEGETYCZNY I PARSING NAPISÓW
1. **Higiena Strumienia Audio i Limit CPU (`librosa.pyin`):**
   - Jawne mapowanie japońskiej ścieżki audio w FFmpeg: `-map 0:a:m:language:jpn? -map 0:a:0 -vn -acodec pcm_s16le -ar 16000 -ac 1`.
   - Zakaz mielenia 24 minut audio przez pYIN: pobranie 3–5 czystych wycinków mowy (1.5–2.0 s, łącznie <= 10 s per postać). Dyskwalifikacja próbek z muzyką/krzykiem (std(F0) > 50 Hz).
   - **Asymetria Fizjologiczna Krtani:** Mediana F0 <= 135 Hz nadaje twardy determinizm męski (`F0_hard_masculine = True`, pewność 1.0, prawo weta łamane tylko przy Score_EN <= -8). Dla całego pasma F0 > 135 Hz waga akustyki wynosi `0.0` (ochrona przed niskimi głosami kobiecymi 140–170 Hz oraz kobiecymi seiyū dubbingującymi chłopców >170 Hz).
2. **Czystość Analizy NLP i Drzewo Zależności (`spaCy en_core_web_sm`):**
   - Łączenie kwestii z przerwą Delta_t < 1.5 s w akapity przed analizą koreferencji.
   - **Vocative Filter:** Wykluczenie zwrotów adresatywnych w 2. osobie (*"Ray, you..."*) ze zliczania podmiotów 3. osoby.
   - **Dependency Subject Isolation:** Zaimki `he/she` ze zdania następującego są przypisywane do postaci X wyłącznie wtedy, gdy w zdaniu tym nie wystąpiła inna nazwa własna (`PROPN`) jako nowy podmiot (`nsubj`/`nsubjpass`).
3. **Dwuwarstwowa Bramka Monologu Wewnętrznego i Sanitacja CJK:**
   - Cudzysłowy `「 」` i `『 』` to zawsze mowa głośna (zakaz traktowania jako myśli). Nawiasy `【 】`, `《 》`, `［ ］` to skille/szyldy. Notki `[TL: ...]` i `[SFX: ...]` są wycinane przed analizą NLP.
   - **Ścieżka 1 (Nawiasy Myśli):** Cała kwestia w `( )` lub `（ ）` albo styl `Thoughts/Internal` -> `is_internal_monologue = True` (niezależnie od tego, czy w scenie istnieje `target_speaker`).
   - **Ścieżka 2 (Sama Kursywa `{\i1}`):** Daje `is_internal_monologue = True` WYŁĄCZNIE gdy `target_speaker is None`, brak wołacza/wykrzyknika zewnętrznego, brak znaczników 2. osoby (`has_2nd_person_marker`) i brak stylu `Offscreen/Radio/Flashback`.
4. **Automat Tożsamości Diegetycznej i Dziedziczenie Aliasów:**
   - Wiązanie interwałów `PersonaInterval(apparent_gender, valid_from_ep, valid_to_ep)` z `episode_index` (odporność na tłumaczenie odcinków poza kolejnością).
   - Egzekwowanie `apparent_gender` w dialogu publicznym; aktywacja `true_gender` wyłącznie w monologu wewnętrznym lub rozmowie sam na sam z powiernikiem (`knows_secret`). Dekonspiracja (`EP_RUPTURE`) wyzwalana skokiem fazowym Delta Score_EN niezależnie od wysokości F0.
   - Rekurencyjne dziedziczenie `true_gender` dla prefiksów temporalnych/stanowych (`Young, Child, Kid, Little, Baby, Old, Future, Past, Masked`) oraz rozwiązywanie etykiet posesywnych (`[Owner]'s Son/Daughter/Kid`) z blokadą domyślnej feminizacji ról dziecięcych w retrospekcjach.

---

## ✍️ 4. KOMPLETNA MORFOSYNTAKTYKA POLSKA, TOPOLOGIA 2. OSOBY I ONOMASTYKA PWN
1. **Topologia Dyskursu 2. Osoby i Okno Tury (`SpeakerTurn`):**
   - **Dyadic Turn-Taking:** Rozwiązywanie `target_actor` (`target_gender`) z jawnego wołacza w turze (Delta_t < 2.5 s) lub automatycznie z poprzedniego mówcy w wymianie zdań (Delta_t < 5.0 s).
   - **Vocative-Predicate Lock:** Męski wołacz (`decl["W"]` lub tytuł męski) w obrębie tury bezwzględnie blokuje żeńskie końcówki czasowników (`-łaś -> -łeś`, `-łabyś -> -łbyś`), przymiotników orzecznikowych (`nie bądź naiwna -> naiwny`) oraz rzeczowników predykatywnych w narzędniku (`moją najlepszą uczennicą -> moim najlepszym uczniem`).
   - **Harmonizacja Liczby Adresata (`PLURAL "YOU"`):** Wykrycie wykładnika mnogiego w którejkolwiek linii tury (polskie `-cie`, angielskie `you guys/all`, konstrukcje dystrybucyjne `your + [plural_noun]`, japońskie `omaera, kisamara, temeera, minna, -tachi`) wymusza wsteczną i progresywną konwersję pojedynczych form 2. os. na mnogie (`do ciebie -> do was`, `ty -> wy`, `jesteś -> jesteście`) w całej turze.
2. **Klasyfikacja Ontologiczna Bytów i Rekcja Przyimkowa:**
   - Rozróżnienie `ANTHROPONYM` (osoba; pierwszeństwo rejestracji w `characters` nad toponimami glosariusza) vs `TOPONYM` (kraina/miasto po konstrukcjach `from [Place]`, `people of [Place]`, `ci z [Place]`) vs `CHREMATONYM`.
   - **Wszystkie Polskie Przyimki i Rozdział Semantyczny `z`:**
     * *Dopełniacz:* `dla, do, od, z/ze (pochodzenie: skąd?), bez, u, koło, obok, blisko, wokół, pośród, wśród, spod, zza, znad, wzdłuż, podczas, mimo, według, wskutek, wobec, naprzeciw`. Przyimek pochodzenia `z` przed `TOPONYM` (`ci z [Toponym]`) kategorycznie blokuje i usuwa fałszywy sufiks narzędnika `-em`!
     * *Celownik:* `dzięki, przeciw, przeciwko, ku, wbrew`.
     * *Biernik:* `przez, na, w, o, za, pod, nad, przed, między, poza (ruch dynamiczny)`.
     * *Narzędnik:* `z/ze (towarzystwo: z kim? + ANTHROPONYM), za, pod, nad, przed, między, poza (stan statyczny)`.
     * *Miejscownik:* `o (o tobie, zakaz biernika *o ciebie*), w, na, po, przy`.
   - **Odporność na podział wiersza ASS:** Zastąpienie naiwnego `\b` przy nazwach własnych granicą odporną na znaczniki ASS: `(?:^|\\[Nnh]|[^\w])`.
3. **Paradygmat 7 Przypadków (`DeclensionParadigm`) i Norma Ortograficzna PWN:**
   - Zamrożona matryca (M, D, C, B, N, Ms, W) w `SeriesBible` (zakaz *Nominative Freezing*).
   - **Nieodmienność żeńska:** Obce i japońskie imiona żeńskie zakończone na spółgłoskę lub samogłoskę inną niż `-a` (*Rin, Megumi, Yuki*) są bezwzględnie nieodmienne.
   - **Zasada Apostrofu PWN (CV-Mora Detector):** Apostrof wyłącznie po niemym fonetycznie `-e` (*White'a, Wayne'a, George'a*). Kategoryczny zakaz apostrofu po wymawianych spółgłoskach (*Raya, Renem*) oraz po japońskich otwartych morach zakończonych na wymawiane `-e` (*-ke, -te, -ne, -me, -re, -se, -ze, -be, -ge*).
   - **Dystrybucja końcówki `-u` w Ms i W:** Tematy męskie zakończone na afrykaty, głoski stwardniałe, tylnojęzykowe i miękkie (`tz, c, dz, cz, sz, rz, ż, sh, ch, k, g, j, y, l`) przyjmują w Miejscowniku i Wołaczu końcówkę **`-u`** (np. `-tz -> -tzu`; automatyczna korekta błędnego `-tzie -> -tzu`).
   - **Morfologia trzonów i ortografia:** Pełna obsługa oboczności (*ó:o, ą:ę, e:zero, k:c, g:dz*), separacja żeńskich końcówek przymiotnikowych `-owa` od męskiego celownika `-owi`/mianownika lm `-owie`, korekta alternacji męskoosobowych od tematów `-nki` (`ciency`, blokada `cieńscy`), tarcza homonimii (`POLISH_COMMON_NOUN_HOMONYMS`, strażnik miejscownika `w powiecie` vs czasownika `powiecie`) oraz pełny korpus >= 165 par ról społecznych.
   - **Postacie Epizodyczne (`NEUTRAL`, 1–2 kwestie):** Status `is_transient = True` (brak blokady P0, otwarcie na leniwą promocję) oraz bezwzględny wymóg form bezczasownikowych/bezosobowych/teraźniejszych.

---

## 📐 5. METRYKI EKRANOWE ASS, FUNKCJA NAGRODY AVT I HIGIENA REJESTRU
1. **Fizyczne Ograniczenia Planszy i Pętla na Tekście Polskim:**
   - `CPS_PL = len(pure_text_bez_tagow_ASS) / max(Delta_t, 0.5) <= 17.0` (dynamiczny sufit znaków: `min(76, int(Delta_t * 17.0))`, max 2 linie, `CPL <= 38`).
   - **Wielokryterialna Funkcja Nagrody AVT (Asymmetric Dead-Band Potential – ochrona przed kastracją dialogu):**
     `R_AVT(y | x, Delta_t, a) = R_base(y, x) - [ P_band(y, Delta_t, rho_x) + lambda_cpl * Psi(CPL(y)) + L_drama(y, x, a) ]`
     Dla gęstego dialogu japońskiego (`rho_x = moras(x) / Delta_t >= 9.0 mor/s`) obowiązuje minimalna podłoga `CPS_target(rho_x) = min(13.5, 7.5 + 0.5 * rho_x)`.
2. **Nadzór Rejestru i Bezpieczeństwo Warstwy 4 (Primum Non Nocere):**
   - Eliminacja 4 klas slangu w gatunkach historycznych/fantasy: Klasa A (młodzieżowy: *spoko, i gitara*), Klasa B (wulgarny: *stul pysk*), Klasa C (współczesne metafory: *przejmuję stery*), Klasa D (trywializacje: *ten typ, dzikuska*).
   - Jednotokenowa harmonizacja fleksyjna (`W_i -> W'_i`) z ochroną cytatów (`QuoteShield`). Zakaz otwartych wzorców dla wykrzykników (wymagane zakotwiczenie `^`, `\N`, `[-–]` i `!`), redukcja *kakegoe* wyłącznie przy wypowiedziach <= 2 słów. Zakaz lookbehindów o zmiennej długości.
   - Defensywna telemetria (brak cichych bloków `except:`) oraz sanityzacja czeskich błędów zegara (`Delta_t in {60, 120, 600, 1200, 3600} s`).

---

## 👑 6. TRYBY PRACY ZESPOŁU WIELOAGENTOWEGO, AUDYT ŚLEDCZY I DYREKTYWA PYTEST
1. **Dwa Tryby Wywołania:**
   - **Tryb Autonomiczny (`/goal`, `/teamwork-preview`):** Zespół wieloagentowy (Project Orchestrator, równoległe sub-agenty wykonawcze, Reviewers & Challengers w 18 wymiarach AVT + ASS-Fuzzing, Forensic AST Auditor oraz Victory Auditor) realizuje pełny cykl naprawczy z fizyczną modyfikacją plików `.py` aż do uzyskania werdyktu **`VICTORY CONFIRMED`**. W trybie `/teamwork-preview STANDBY` zespół oczekuje na wklejenie listy błędów przed startem Fazy 0.
   - **Tryb Konsultacyjny / Planowania:** Gdy Operator prosi wyłącznie o analizę lub plan bez komendy wdrożeniowej, edycja plików następuje po akceptacji Operatora.
2. **Obowiązkowa Weryfikacja Śledcza (`audit_diff.ps1`) i Dyrektywa Szybkości `pytest`:**
   - **Ochrona przed 12-minutowym wąskim gardłem pytest:** W trakcie implementacji (Fazy 1–3) obowiązuje KATEGORYCZNY ZAKAZ uruchamiania pełnego pakietu testów. Agenty uruchamiają wyłącznie szybkie testy celowane (< 2 s):
     `.\.venv\Scripts\python.exe -m pytest -k "<nazwa_nowego_testu>"`
   - **Forensic AST Audit:** Przed zamknięciem zadania audytor weryfikuje `git diff` skryptem:
     `powershell -ExecutionPolicy Bypass -File .\audit_diff.ps1 -ForbiddenTerms "<DYNAMIC_LITERAL_BLACKLIST>"`
     (kod wyjścia `0`: brak zmian w JSON/ASS, brak wycieku nazw własnych do kodu produkcyjnego, brak martwego kodu, brak mockowania logiki domenowej). Zakaz modyfikacji pliku `audit_diff.ps1`.
   - **Finalny Acceptance Gate (Faza 4):** Niezależny Victory Auditor uruchamia DOKŁADNIE RAZ pełny pakiet wszystkich testów (`.\.venv\Scripts\python.exe -m pytest`, wymagane 100% PASSED, Zero Regression) i publikuje **Executive Dossier** z sekcją `[CERTYFIKAT ELIMINACJI ŹRÓDŁOWEJ]`.
3. **Ograniczenia Środowiskowe i Kosztowe:**
   - Środowisko Windows (`.venv`), ścieżki przez `pathlib.Path`, wywołania `subprocess` jako lista argumentów bez `shell=True`.
   - Zakaz Vertex AI (`use_vertex = 0`), zakaz zewnętrznych modeli wymagających tokenów chmurowych (`pyannote.audio`). Wszystkie silniki profilera, triangulacji, pamięci i lintera działają lokalnie przy koszcie dokładnie **0.00 PLN**.
