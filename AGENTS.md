# 🏛️ KODEKS ZASAD POTOKU AVT (WORKSPACE RULES — TRANSLATOR STANDARD 4.9)

Dokument ten stanowi jedyne źródło prawdy (Single Source of Truth) definiujące nienaruszalne reguły architektoniczne, lingwistyczne i procesowe asystenta AI oraz zespołów wieloagentowych w repozytorium `translator`.

---

## 🎯 1. NADRZĘDNA FILOZOFIA: ELIMINACJA PRZYCZYN ŹRÓDŁOWYCH W 5 WARSTWACH
1. **Uwagi Operatora jako Drogowskaz Taksonomiczny:** Każde zgłoszenie błędu wskazuje na awarię całej klasy zjawisk w silniku. Obowiązuje kategoryczny zakaz ograniczania naprawy do pojedynczego słowa, zdania czy tytułu anime.
2. **Obowiązkowy Protokół 5 Warstw (Ingress -> State -> Egress):**
   Każda modyfikacja architektoniczna musi symetrycznie zabezpieczać cały potok:
   - **Warstwa 1 (Profiler & Triangulacja – `profiler.py`, `metadata.py`):** Epistemiczna Triangulacja Płci (asymetryczna akustyka F0 `librosa.pyin` z Voiced-Frame Pooling >= 25 ramek, filtracją IQR/median > 0.35 i std > 50 Hz + Directional Consensus Purity z ograniczeniem pewności < 0.95 przy entropii/purity < 0.65 i progiem >= 0.85 dla czystego konsensusu + morfosyntaktyka JA *yakuwarigo* [neutralne formalne watakushi=0.0] + dwustronne składanie diakrytyków `normalize_ascii_diacritics` + koreferencja `spaCy` EN z izolacją podmiotu `nsubj`), odporny parsing napisów (`pysubs2`), kanoniczny fallback sezonowy API (`strip_season_suffix`).
   - **Warstwa 2 (Pamięć Serii & Ontologia – `series_memory.py`, `scene_discourse.py`):** Modele Pydantic (`CharacterProfile`, `CharacterIdentity`, `PersonaInterval`), samolecząca sanitacja pamięci w RAM (`_sanitize_loaded_bible_in_ram`), klasyfikacja ontologiczna (`ANTHROPONYM`, `TOPONYM`, `CHREMATONYM`), Automat Tożsamości Diegetycznej (`apparent_gender` vs `true_gender`), dziedziczenie aliasów wiekowych i relacyjnych (`Young/Child X`, `[Owner]'s Son/Daughter/Kid`), SubTurn Pivot Partitioning (rozcinanie tury przy zmianie adresata), symetryczny rachunek zbiorów We_Group (`We_Group = scene_participants - excluded_addressee`), trójstanowa virility (`VIRILE` / `NON_VIRILE` / `AMBIGUOUS`) oraz zamrożona matryca 7 przypadków `DeclensionParadigm`.
   - **Warstwa 3 (Kanon & Kontrakt Tłumacza – `translator.py`, `rules.py`, `manga_canon.py`):** Nadrzędność oficjalnego polskiego kanonu mangowego. Stylistic Freedom Invariance (pełna autonomia stylistyczna LLM: elipsa, inwersja, ruchome końcówki, czas teraźniejszy). Modular World-State Telemetry (`format_dry_telemetry_tag`, próg pewności >= 0.80, bez wartości None/AMBIGUOUS). Twardy kontrakt Pydantic (`speaker_gender`, `target_gender`, `addressee_number`, `DeclensionParadigm` z nakazem odmiany przez przypadki).
   - **Warstwa 4 (Deterministyczna Bramka Jakości – `avt_linter.py`, `translator.py`):** W 100% deterministyczny silnik korekty morfosyntaktycznej post-generation (0.00 PLN, brak wywołań LLM). Stem-First Execution Order (oboczności rdzenne `o:ó` i `ę:ą` przed ogólnymi sufiksami), inwariant morfemu przeszłego `-ł-` / `-l-` (ochrona czasu teraźniejszego na `-am`/`-em` i 3. osoby), zamknięta biała lista nośników ruchomych końcówek (`bym/byś/żeś`), ochrona fałszywych klitek (`tym/ktoś/coś`), zaimków przeczących i uogólniających (`nikt, każdy, ktokolwiek`), ścisła ochrona korpusu symetrycznych par ról osobowych (Zasada 16), Strażnik Homonimii Miejscownika w `is_plural_text` (`w powiecie`, `w mieście`) oraz QuoteShield / maskowanie tagów ASS `{...}`.
   - **Warstwa 5 (Tarcza Regresyjna CI/CD – `test_system.py`):** Atomowe testy rodzin izomorficznych (minimum 5 różnych leksykalnie przykładów na klasę problemu + kontrprzykłady negatywne; 171/171 PASSED, Zero Regression Lock).

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
   - **Voiced-Frame Pooling:** Zamiast odrzucania krótkich linii, agregacja do 8 czystych wypowiedzi (maksymalnie 10.0 s łącznie). Pomiar ważny przy zebraniu >= 25 ramek dźwięcznych (`voiced_flag == True` oraz `voiced_prob >= 0.60`).
   - **Filtracja Intonacji i Szumu:** Odrzucenie próbek przy jednoczesnym `IQR(F0) / median(F0) > 0.35` ORAZ `std(F0) > 50 Hz`.
   - **Asymetria Fizjologiczna Krtani:** Mediana F0 <= 135 Hz nadaje twardy determinizm męski (`F0_hard_masculine = True`, pewność 1.0, prawo weta łamane tylko przy Score_EN <= -8). Dla całego pasma F0 > 135 Hz waga akustyki wynosi `0.0` (ochrona przed niskimi głosami kobiecymi 140–170 Hz oraz kobiecymi seiyū dubbingującymi chłopców >170 Hz).
2. **Directional Consensus Purity i Czystość Analizy NLP:**
   - **Directional Consensus Purity:** Przy 100% czystości sygnałów (purity == 1.0) i >= 2 niezależnych dowodach pewność wynosi >= 0.85. Przy sprzecznościach lub zanieczyszczeniu sygnału (purity < 0.65) pewność jest bezwzględnie tłumiona poniżej 0.95 (do 0.70), blokując agresywne nadpisywanie w Linterze.
   - **Neutralność Formalnego Zaimka Watakushi:** Japoński zaimek *watakushi* (i warianty formalne *watashi* w rejestrze dworskim/urzędowym) otrzymuje wagę 0.0 (pełna neutralność genderowa).
   - **Dwustronne Składanie Diakrytyków (`normalize_ascii_diacritics`):** Odporność dopasowywania metadanych i onomastyki na akcenty, przegłosy i umlauty (Unicode NFKD ASCII-folding).
   - Łączenie kwestii z przerwą Delta_t < 1.5 s w akapity przed analizą koreferencji.
   - **Vocative Filter:** Wykluczenie zwrotów adresatywnych w 2. osobie (*"Ray, you..."*) ze zliczania podmiotów 3. osoby.
   - **Dependency Subject Isolation:** Zaimki `he/she` ze zdania następującego są przypisywane do postaci X wyłącznie wtedy, gdy w zdaniu tym nie wystąpiła inna nazwa własna (`PROPN`) jako nowy podmiot (`nsubj`/`nsubjpass`).
3. **Dwuwarstwowa Bramka Monologu Wewnętrznego i Sanitacja CJK:**
   - Cudzysłowy `「 」` i `『 』` to zawsze mowa głośna (zakaz traktowania jako myśli). Nawiasy `【 】`, `《 》`, `［ ］` to skille/szyldy. Notki `[TL: ...]` i `[SFX: ...]` są wycinane przed analizą NLP.
   - **Ścieżka 1 (Nawiasy Myśli):** Cała kwestia w `( )` lub `（ ）` albo styl `Thoughts/Internal` -> `is_internal_monologue = True` (niezależnie od tego, czy w scenie istnieje `target_speaker`).
   - **Ścieżka 2 (Sama Kursywa `{\i1}`):** Daje `is_internal_monologue = True` WYŁĄCZNIE gdy `target_speaker is None`, brak wołacza/wykrzyknika zewnętrznego, brak znaczników 2. osoby (`has_2nd_person_marker`) i brak stylu `Offscreen/Radio/Flashback`.
   - **Niewidzialność Monologu Wewnętrznego dla Dyskursu Zewnętrznego:** Kwestie sklasyfikowane jako monolog wewnętrzny nie ustawiają adresata ani nie zanieczyszczają oczekiwań dyskursywnych partnera sceny.
4. **Automat Tożsamości Diegetycznej, Podział SubTurn Pivot i Dziedziczenie Aliasów:**
   - Wiązanie interwałów `PersonaInterval(apparent_gender, valid_from_ep, valid_to_ep)` z `episode_index` (odporność na tłumaczenie odcinków poza kolejnością).
   - Egzekwowanie `apparent_gender` w dialogu publicznym; aktywacja `true_gender` wyłącznie w monologu wewnętrznym lub rozmowie sam na sam z powiernikiem (`knows_secret`). Dekonspiracja (`EP_RUPTURE`) wyzwalana skokiem fazowym Delta Score_EN niezależnie od wysokości F0.
   - **SubTurn Pivot Partitioning:** Automatyczne rozcinanie tury mówcy na niezależne pod-segmenty (SubTurn) przy wykryciu punktu obrotu adresata (Addressee Pivot), np. przy zwrotach wołaczowych do różnych postaci w jednej wypowiedzi, spójnikach przeciwstawnych czy zmianie rejestru mowy/myśli.
   - Rekurencyjne dziedziczenie `true_gender` dla prefiksów temporalnych/stanowych (`Young, Child, Kid, Little, Baby, Old, Future, Past, Masked`) oraz rozwiązywanie etykiet posesywnych (`[Owner]'s Son/Daughter/Kid`) z blokadą domyślnej feminizacji ról dziecięcych w retrospekcjach.

---

## ✍️ 4. KOMPLETNA MORFOSYNTAKTYKA POLSKA, TOPOLOGIA 2. OSOBY I ONOMASTYKA PWN
1. **Topologia Dyskursu 2. Osoby, SubTurn i Okno Tury (`SpeakerTurn`):**
   - **Dyadic Turn-Taking:** Rozwiązywanie `target_actor` (`target_gender`) z jawnego wołacza w turze (Delta_t < 2.5 s) lub automatycznie z poprzedniego mówcy w wymianie zdań (Delta_t < 5.0 s), z uwzględnieniem progresywnego Lookaheadu (< 2.0 s) ze znacznikami ASS `\N`.
   - **Vocative-Predicate Lock:** Męski wołacz (`decl["W"]` lub tytuł męski) w obrębie tury bezwzględnie blokuje żeńskie końcówki czasowników (`-łaś -> -łeś`, `-łabyś -> -łbyś`), przymiotników orzecznikowych (`nie bądź naiwna -> naiwny`) oraz rzeczowników predykatywnych w narzędniku (`moją najlepszą uczennicą -> moim najlepszym uczniem`).
   - **Harmonizacja Liczby Adresata (`PLURAL "YOU"`):** Wykrycie wykładnika mnogiego w którejkolwiek linii tury (polskie `-cie`, angielskie `you guys/all`, konstrukcje dystrybucyjne `your + [plural_noun]`, japońskie `omaera, kisamara, temeera, minna, -tachi`) wymusza wsteczną i progresywną konwersję pojedynczych form 2. os. na mnogie (`do ciebie -> do was`, `ty -> wy`, `jesteś -> jesteście`) w całej turze.
   - **Strażnik Homonimii Miejscownika w `is_plural_text`:** Rzeczowniki w miejscowniku lp. na `-cie` występujące po przyimkach rzędu miejscownikowego (`w powiecie`, `na świecie`, `w mieście`) nie mogą być błędnie interpretowane jako formy rozkazujące 2. os. lm. czasowników.
2. **Symetryczny Rachunek Zbiorów We_Group i Trójstanowa Virility:**
   - **Rachunek Zbiorów:** Grupa 'My' (1. os. lm.) w scenie jest wyliczana symetrycznie:
     `We_Group = scene_participants - excluded_addressee`
     (gdy mówca zwraca się w 2. os. do słuchacza jako zewnętrznego obiektu, słuchacz jest odejmowany ze zbioru We_Group; przy czynności inkluzywnej We_Group obejmuje wszystkich obecnych).
   - **Trójstanowa Kategoryzacja Virility:**
     * `VIRILE` (min. 1 potwierdzony mężczyzna w We_Group) -> wymuszenie form męskoosobowych (`-liśmy / -liście`, `byliśmy ... -li`).
     * `NON_VIRILE` (wyłącznie potwierdzone kobiety w We_Group, zero mężczyzn) -> zachowanie i ochrona form niemęskoosobowych (`-łyśmy / -łyście`).
     * `AMBIGUOUS` (brak potwierdzonego składu płciowego) -> neutralność fleksyjna, brak wymuszenia.
   - **Izolacja Cięcia Sceny (Cross-Scene Cut Isolation):** Uczestnicy nie przenikają przez granice cięcia montażowego (Delta_t >= 3.5 s bez aktywnego dialogu lub zmiana stylu Default <-> Flashback/Narration). Byt narracyjny (`Narrator`, `Radio`, `Voiceover`, `Sign`) jest bezwzględnie wykluczony ze zbioru We_Group.
3. **Morfologia Trzonów, Stem-First Execution Order i Ochrona Klitek:**
   - **Stem-First Execution Order:** Polskie oboczności rdzenne samogłosek `o:ó` (*mogłaś -> mógłbyś*, *pomogłaś -> pomógłbyś*, *wiozłaś -> wiózłbyś*) oraz `ę:ą` (*wzięłaś -> wziąłeś*, *wzięłabyś -> wziąłbyś*, *zaczęłaś -> zacząłeś*) muszą być wykonywane PRZED ogólną podmianą sufiksów fleksyjnych.
   - **Inwariant Morfemu Przeszłego `-ł-` / `-l-`:** Bezwzględna ochrona czasu teraźniejszego 1. osoby na `-am`/`-em` (*mam, znam, czekam, rozumiem, wiem*) przed fałszywą maskulinizacją/feminizacją.
   - **Zamknięta Biała Lista Nośników Ruchomych Końcówek:** Partykuły i spójniki ruchome (`bym, byś, żeś, żebyś, abyś, iżbyś, gdybyś, czyś`) są harmonizowane w obrębie klauzuli z zachowaniem ochrony form inwersyjnych czasu przyszłego złożonego (*czekał będziesz / walczyła będę*).
   - **Ochrona Fałszywych Klitek i Zaimków Uogólniających:** Wykluczenie fałszywych dopasowań klitycznych z zaimków narzędnikowych i nieokreślonych (*tym, kimś, czymś, ktoś, coś, kiedyś, gdzieś*) oraz podmiotów uogólniających i przeczących (*nikt nie brał, każda wiedziała, ktokolwiek słyszał*).
   - **Ścisła Ochrona Korpusu Par Ról Osobowych (Zasada 16):** Uzgadnianie par ról osobowych w 2. osobie orzeczenia imiennego (*najlepszą uczennicą -> najlepszym uczniem*) przy 100% ochronie żeńskich rzeczowników abstrakcyjnych, metaforycznych i epikoenicznych odnoszonych do mężczyzn (*jesteś moją nadzieją, jesteś moją jedyną szansą, jesteś moją zgubą* pozostają NIENARUSZONE; pełny korpus >= 165 par ról społecznych).
   - **Separacja Trzonów Przymiotnikowych i Rzeczownikowych na `-owa` vs `-owi / -owie`:** Bezwzględna separacja żeńskich końcówek przymiotnikowych `-owa` od męskiego celownika `-owi`/mianownika lm `-owie`.
   - **QuoteShield i Maskowanie Tagów ASS:** Wszystkie znaczniki stylizacyjne `{...}` oraz cytaty dialogowe `„...”` / `"..."` są maskowane przed analizą fleksyjną i odzyskiwane po zakończeniu procedury.
4. **Klasyfikacja Ontologiczna Bytów i Rekcja Przyimkowa:**
   - Rozróżnienie `ANTHROPONYM` vs `TOPONYM` (kraina/miasto po konstrukcjach ablatywnych `from [Place]`, `people of [Place]`, `ci z [Place]`) vs `CHREMATONYM`.
   - **Ścisła Biała Lista Dopełniacza Rzeczowników Nijakich/Instytucji po `z`:** Ochrona dopełniacza pospolitych rzeczowników nijakich instytucji (*z biura, z ministerstwa, z miasta, z królestwa, z dowództwa*) zakończonych na `-a` przed skażeniem narzędnikiem żeńskim (*-ą*); zachowanie prawdziwego narzędnika towarzyszenia wyłącznie dla realnych postaci kobiecych (*poszedł z Anną*).
   - **Usuwanie Fałszywego Narzędnika Ablatywnego:** Przywracanie poprawnej formy toponimu po przyimku pochodzenia `z` (*z [Toponym]* zamiast błędnego *-em*), w tym przez podziały linii ASS `\N`.
   - **Ortografia Przymiotników Męskoosobowych od Tematów Twardych `-nki`:** Poprawność alternacji fonetycznej (*ciency*, bezbłędna blokada hiperpoprawnego *cieńscy*).
   - **Dystrybucja Końcówki `-u` w Ms i W:** Tematy męskie zakończone na afrykaty (*-tz -> -tzu*, np. *Laurentzu, Moritzu, Fritzu*; automatyczna korekta błędnego *-tzie -> -tzu*).

---

## 📐 5. METRYKI EKRANOWE ASS, FUNKCJA NAGRODY AVT I HIGIENA REJESTRU
1. **Stylistic Freedom Invariance i Modular World-State Telemetry:**
   - **Stylistic Freedom Invariance:** Pełna autonomia stylistyczna LLM w doborze naturalnego rejestru polszczyzny mówionej (elipsa podmiotu, inwersja orzeczenia, ruchome końcówki fleksyjne, naturalny czas teraźniejszy). Czyste prompty nastawione na dramaturgię i subtekst seiyū.
   - **Modular World-State Telemetry (`format_dry_telemetry_tag`):** Emitowanie do promptu wyłącznie zwartych, opisowych mikro-tagów telemetrycznych o wysokim stopniu pewności (próg confidence >= 0.80): `[Mówca: ... | Adresat: ... | Grupa_1os_lm: ...]`. Kategoryczny zakaz emitowania pustych lub niejednoznacznych wartości (*None, AMBIGUOUS, UNKNOWN*).
2. **Fizyczne Ograniczenia Planszy i Pętla na Tekście Polskim:**
   - `CPS_PL = len(pure_text_bez_tagow_ASS) / max(Delta_t, 0.5) <= 17.0` (dynamiczny sufit znaków: `min(76, int(Delta_t * 17.0))`, max 2 linie, `CPL <= 38`).
   - **Wielokryterialna Funkcja Nagrody AVT (Asymmetric Dead-Band Potential – ochrona przed kastracją dialogu):**
     `R_AVT(y | x, Delta_t, a) = R_base(y, x) - [ P_band(y, Delta_t, rho_x) + lambda_cpl * Psi(CPL(y)) + L_drama(y, x, a) ]`
     Dla gęstego dialogu japońskiego (`rho_x = moras(x) / Delta_t >= 9.0 mor/s`) obowiązuje minimalna podłoga `CPS_target(rho_x) = min(13.5, 7.5 + 0.5 * rho_x)`.
3. **Nadzór Rejestru i Bezpieczeństwo Warstwy 4 (Primum Non Nocere):**
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
   - **Finalny Acceptance Gate (Faza 4):** Niezależny Victory Auditor uruchamia DOKŁADNIE RAZ pełny pakiet wszystkich testów (`.\.venv\Scripts\python.exe -m pytest`, wymagane 100% PASSED, Zero Regression Lock: 171/171) i publikuje **Executive Dossier** z sekcją `[CERTYFIKAT ELIMINACJI ŹRÓDŁOWEJ]`.
3. **Ograniczenia Środowiskowe i Kosztowe:**
   - Środowisko Windows (`.venv`), ścieżki przez `pathlib.Path`, wywołania `subprocess` jako lista argumentów bez `shell=True`.
   - Zakaz Vertex AI (`use_vertex = 0`), zakaz zewnętrznych modeli wymagających tokenów chmurowych (`pyannote.audio`). Wszystkie silniki profilera, triangulacji, pamięci i lintera działają lokalnie przy koszcie dokładnie **0.00 PLN**.
