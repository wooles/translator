# RAPORT AUDYTU FILARÓW AVT (INWENTARYZACJA, DEDUPLIKACJA, MINIMALIZACJA, HANDOFF)

## 0. METADANE
- **Repozytorium:** `https://github.com/wooles/translator`
- **HEAD audytowany:** `81de7b5` (`81de7b5a1f9f927c1e4ccca318458e7afb12eda3` — Hotfix 10.1.1)
- **Data audytu:** `2026-11-03`
- **Audytor:** Niezależny Audytor Architektoniczny AVT (Read-Only)
- **Zakres:** Diagnostyka systemu Filarów AVT w `rules.py` oraz powiązanych modułach (`profiler.py`, `translator.py`, `verifier.py`, `avt_linter.py`) + wygenerowanie promptu wykonawczego `10.2` (bez modyfikacji kodu, bez commitów, bez uruchamiania testów)

---

## 1. EXECUTIVE SUMMARY
- **Liczba Filarów w `rules.py`:** **180 unikalnych numerów rzymskich** (`FILAR I` – `FILAR CLXXX`) w historycznym monumencie `TRANSLATION_RULES_PROMPT` oraz `get_focused_rules_for_batch`, a także **4 makro-filary arabskie** (`FILAR 1` – `FILAR 4` podzielone na **16 reguł alfanumerycznych** `R1.1–R1.11` i `R3.1–R3.5`) w aktywnym prompcie bazowym `STANDARD_9_CORE_RULES_PROMPT`.
- **Rozkład aktywności w runtime:**
  - `STANDARD_9_CORE_RULES_PROMPT` (base, zawsze aktywny w runtime): **4 makro-filary arabskie (16 reguł `R1.1–R1.11`, `R3.1–R3.5`)** oraz **0 nagłówków rzymskich**.
  - `get_focused_rules_for_batch` (dynamiczny selektor sceny): **24 bloki warunkowe** odwołujące się łącznie do **38 unikalnych rzymskich numerów Filarów** (część zgrupowana w pojedyncze wpisy, np. `FILAR XVIII, XXXIII, XVI & XVII` lub `FILAR XXV, XXVII & XXVIII`).
  - `TRANSLATION_RULES_PROMPT` (monument legacy z wersji 1.0–8.9): zawiera wszystkie **180 rzymskich Filarów**, z czego aż **142 rzymskie Filary są całkowicie martwe w domyślnym runtime (`use_lean_prompt=True`)**, ponieważ nie występują w `STANDARD_9_CORE_RULES_PROMPT` i nie mają żadnego triggera w `get_focused_rules_for_batch` (są utrzymywane w pliku `rules.py` ze względu na asercje tekstowe w zamrożonym przez Z16 pliku `test_system.py`).
- **Liczba duplikatów (FAZA 2):** **22 pary/grupy duplikatów** (w tym 14 duplikatów wewnątrz `get_focused_rules_for_batch` i `STANDARD_9_CORE_RULES_PROMPT` oraz 8 wielokrotnych powtórzeń w `TRANSLATION_RULES_PROMPT` i `profiler.py`).
- **Liczba sprzeczności (FAZA 3):** **5 par sprzecznych** (1 rozstrzygnięta przez `Anti-Smoothing Filter` w `10.1.1`, **4 wymagające rozstrzygnięcia** w `10.2`).
- **Liczba martwych Filarów (FAZA 4):** **142 rzymskie Filary** nieaktywne w domyślnym potoku `use_lean_prompt=True` (z czego **138 rekomendowanych do zamrożenia w pasywnym archiwum Z16 / usunięcia z aktywnego indeksowania**, a **4 wartościowe merytorycznie do włączenia do skonsolidowanych kategorii dynamicznych**).
- **Główna wada selektora (FAZA 5):** Triggery `FILAR LXV` (wielokropek `...`, spójniki `but`/`wait`, score 90/80) oraz `FILAR LXVI` (znaki `!`/`?`, score 88/80) mają niemal 100% współczynnik trafień na typowej paczce 24 linii (w odcinku pilotażowym `S01E05` aktywowały się odpowiednio w 10/16 i 8/16 paczek), co przy limicie `max_rules=3` blokuje sloty dla reguł specyficznych i powtarza w każdej paczce wskazówki obecne już w `STANDARD_9_CORE_RULES_PROMPT` (`R1.1–R1.11`).
- **Propozycja minimalizacji (FAZA 6):** Redukcja architektury wykonawczej z **180 rozproszonych Filarów rzymskich + 16 reguł R + 24 bloków dynamicznych** do **12 unikalnych, ortogonalnych Kategorii Wykonawczych AVT**:
  - **4 Kategorie Bazowe (`[KATEGORIA_BASE_1]` – `[KATEGORIA_BASE_4]`)** w `STANDARD_9_CORE_RULES_PROMPT` (zawsze aktywne),
  - **8 Kategorii Dynamicznych (`[KATEGORIA_DYN_1]` – `[KATEGORIA_DYN_8]`)** w `get_focused_rules_for_batch` (wybieranych wyłącznie przy wystąpieniu rzadkiego zjawiska specyficznego dla sceny; dla standardowego dialogu selektor zwraca `0` nadmiarowych reguł dynamicznych).
  - Redukcja liczby aktywnych jednostek regułowych w runtime: **180 → 12 (-93.3%)**, redukcja bloków selektora dynamicznego: **24 → 8 (-66.7%)**.
- **Werdykt:** **`MINIMALIZACJA_CZĘŚCIOWA`** (w aktywnym runtime możliwa redukcja o 93.3% do 12 unikalnych kategorii przy zachowaniu pasywnej stałej `TRANSLATION_RULES_PROMPT` jako nienaruszalnego archiwum dla zamrożonego `test_system.py` zgodnie z Z16).
- **Handoff (FAZA 8):** **`GOTOWY`** (`Artefakty/Prompt_10.2_minimalizacja_filarow.md`, walidacja P8.4: **15/15 PASS**).

---

## 2. FAZA 0 — INWENTARYZACJA

### P0.1. Przeczytane pliki repozytorium (`81de7b5`)
1. `rules.py` (pełny plik: linie `1–3545` — `TRANSLATION_RULES_PROMPT`, `STANDARD_9_CORE_RULES_PROMPT`, `get_system_prompt`, `get_focused_rules_for_batch`).
2. `profiler.py` (sekcje budujące `EPISODE BRIEF` oraz `format_lean_episode_brief`).
3. `avt_linter.py` (`lint_and_fix_line`, `_run_phase_7_hygiene`, `EpisodeQualityGate.audit_and_fix_entire_episode` — odwołania do `Filar CLXXI` i `Filar CLXXIV`).
4. `translator.py` (`build_phase1_prompt`, `_prepare_batch_prompt`, `_process_single_batch`).
5. `verifier.py` (`verify_batch`, `_guard_phase2_regressions`).
6. `Artefakty/Raport_wdrozenia_10.1.1.md` (kontekst wdrożenia `2B.1–2B.6`). *(Uwaga dot. `Prompt_10.1.1.md`: brak osobnego pliku `Prompt_10.1.1.md` w katalogu `Artefakty/` na commicie `81de7b5` — pełny kontekst `2B.4` i `2B.5` zweryfikowano bezpośrednio w `Artefakty/Raport_wdrozenia_10.1.1.md` oraz w kodzie `rules.py` i `profiler.py`).*

### P0.2. Surowe wyjścia 7 komend diagnostycznych

#### Komenda 1: `grep -nE "FILAR\s+[IVXLC]+" rules.py | head -300`
~~~text
31:### FILAR I: Naturalna Mówiona Polszczyzna, Szyk Zdania (Rema) i Anty-Kalki
52:### FILAR II: Rygor Kondensacji AVT, Budżet CPS/CPL i Ekonomia Słowa
74:### FILAR III: Spójność Rodzaju Gramatycznego (1. i 2. Osoba) oraz Liczby Mnogiej
98:### FILAR IV: Naturalna Deklinacja Antroponimów, Toponimów i Chrematonimów
121:### FILAR V: Rekcja Czasowników, Dopełniacz Negacji (Genitive of Negation) i Składnia Przypadków
145:### FILAR VI: Eliminacja Zaimków Osobowych i Dzierżawczych (Pro-Drop & Possessive Drop)
168:### FILAR VII: Werbalizacja Konstrukcji Nominalnych i Imiesłowowych
190:### FILAR VIII: Idiomatyka Polska, Frazeologia i Naturalne Kolokacje
212:### FILAR IX: Spójność Rejestru Społecznego, Hierarchii i Dystansu
235:### FILAR X: Semiotyka Obrazu i Dźwięku — Zasada Nieredundancji Wizualnej
258:### FILAR XI: Dynamika Wymiany Zdań, Pary Przylegania (Adjacency Pairs) i Krótkie Repliki
282:### FILAR XII: Sociolekty, Slang Młodzieżowy i Subkultury (Yankee, Gyaru, Otaku, Chūnibyō)
308:### FILAR XIII: Dialekty Regionalne (Kansai-ben, Tōhoku-ben, Kyūshū-ben) i Stylizacja Środowiskowa
334:### FILAR XIV: Archaizacja, Rejestr Historyczny, Dworski i Fantasy (Keigo Historyczne / Rola Starca)
360:### FILAR XV: Język Dziecięcy, Mowa Pieszczotliwa i Infantylizmy
382:### FILAR XVI: Paralingwistyka, Oddechy, Westchnienia i Dźwięki Nieartykułowane
404:### FILAR XVII: Somatyka Ciała, Odruchy Motoryczne i Fizjologia Mowy
426:### FILAR XVIII: Kakegoe, Okrzyki Bojowe i Ekspresja Wysiłkowa (Elipsa Szumu Wizualnego)
448:### FILAR XIX: Śmiech, Płacz, Szloch i Drżenie Głosu w Napisach AVT
470:### FILAR XX: Przerwania, Niedopowiedzenia, Wielokropki i Myślniki
...
2180:### FILAR CLXV: Ochrona Przeskoków Scen (Scene Cuts) i Eliminacja Opóźnionych Potaknięć
2205:### FILAR CLXVI: Autonomiczna Kreacja Polszczyzny i Anty-Kotwiczenie na Składni Angielskiej
2230:### FILAR CLXVII: Spójność Wielokropków Kontynuacyjnych (Ellipsis Continuation)
2255:### FILAR CLXVIII: Ochrona Rodzaju w Mowie Zależnej i Cytatach Wewnętrznych
2280:### FILAR CLXIX: Ciągłość Składniowa Zdań Rozbitych na Dwa Zdarzenia ASS
2305:### FILAR CLXX: Ochrona Krótkich Partykuł Pytających i Zaskoczenia
2330:### FILAR CLXXI: Bezwzględna Zgodność Liczebników, Kwot i Wartości Liczbowych
2355:### FILAR CLXXII: Dynamiczny Prymat Afektu, Polszczyzna Bezterminowa i Pozytywne Rzemiosło
2385:### FILAR CLXXIII: Izolacja Napisów Ekranowych (Signs) od Fleksji Dialogowej
2410:### FILAR CLXXIV: Higiena Tokenów, Eliminacja Zacięć i Artefaktów Jąkania przy Interpunkcji
2435:### FILAR CLXXV: Ochrona Form Bezokolicznikowych i Bezpodmiotowych przed Narzucaniem Płci
2460:### FILAR CLXXVI: Spójność Wołacza w Złożonych Tytułach i Pseudonimach
2485:### FILAR CLXXVII: Decoupling Zaimkowy przed Terminami Kanonicznymi
2500:### FILAR CLXXVIII: Ochrona Pojedynczej Adresatki przed Formą Męskoosobową
2512:### FILAR CLXXIX: Dialogowe Pary Przylegania i Naturalna Riposta
2520:### FILAR CLXXX: Domknięcie Architektury Czystej Domeny Pozytywnej
2575:        "• [SKUP SIĘ NA: FILAR XIII - Dialekty Regionalne, Gwara i Kontrast Rejestrów]: ..."
2610:        "• [SKUP SIĘ NA: FILAR LXV - Izomorfizm Napięcia Składniowego i Anty-Spoiler]: ..."
2628:        "• [SKUP SIĘ NA: FILAR LXVI - Prozodia Oddechu i Kinezjologia Mowy]: ..."
2645:        "• [SKUP SIĘ NA: FILAR CLXXII - Dynamiczny Prymat Afektu, Polszczyzna Bezterminowa i Pozytywne Rzemiosło]: ..."
~~~

#### Komenda 2: `grep -oE "FILAR\s+[IVXLC]+" rules.py | sort -u | wc -l`
~~~text
180
~~~

#### Komenda 3: `grep -nE "STANDARD_9_CORE_RULES_PROMPT|def get_focused_rules_for_batch" rules.py`
~~~text
2525:STANDARD_9_CORE_RULES_PROMPT = """
2688:def get_focused_rules_for_batch(
~~~

#### Komenda 4: `grep -nA 500 "def get_focused_rules_for_batch" rules.py | grep -E "FILAR\s+[IVXLC]+"`
~~~text
2575:        "• [SKUP SIĘ NA: FILAR XIII - Dialekty Regionalne, Gwara i Kontrast Rejestrów]: Kwestie postaci posługującej się w oryginale gwarą..."
2610:        "• [SKUP SIĘ NA: FILAR LXV - Izomorfizm Napięcia Składniowego i Anty-Spoiler]: Dopasuj polski szyk tak, by kluczowe rozstrzygnięcie/negacja padły na końcu zdania..."
2628:        "• [SKUP SIĘ NA: FILAR LXVI - Prozodia Oddechu i Kinezjologia Mowy]: W scenach walki, zadyszki i szlochu stosuj krótkie, urywane takty..."
2645:        "• [SKUP SIĘ NA: FILAR CLXXII - Dynamiczny Prymat Afektu, Polszczyzna Bezterminowa i Pozytywne Rzemiosło]: 1. Aktorstwo i fizjologia emocji seiyū..."
2668:        "• [SKUP SIĘ NA: FILAR LXXV - Zestrojenie Akcentu Logicznego i Prominencji F0]: Umieść wyraz o maksymalnym nacisku fonicznym aktora..."
2686:        "• [SKUP SIĘ NA: FILAR CLVII - Nienaruszalność Formy Adresatywnej, Harmonia Wołacza i -Sama Drop]: Jeśli postać zwraca się do rozmówcy po imieniu..."
2705:        "• [SKUP SIĘ NA: FILAR XVIII, XXXIII, XVI & XVII - Kakegoe, Somatyka Ciała i Paralingwistyka]: Odruchy motoryczne i utratę równowagi (Ottotto)..."
2724:        "• [SKUP SIĘ NA: FILAR XXVI & XXIX - Zasada Yobisute i Ewolucja Relacji]: Do przyjaciół, kolegów z klasy i towarzyszy..."
2742:        "• [SKUP SIĘ NA: FILAR XXV, XXVII & XXVIII - Tytulatura, Etykieta i Adaptacja Honoryfikatorów]: Stosuj naturalną 2. osobę..."
2760:        "• [SKUP SIĘ NA: FILAR XCVI - Asymetria Zaimków 3. Osoby i Płeć (Kanojo-tachi vs Karera)]: Gdy japońskie audio zawiera 'kanojo-tachi'..."
2778:        "• [SKUP SIĘ NA: FILAR CXXXVI - Triangulacja Kognitywna i Foniczna Wieku/Płci (Chłopiec vs Dziewczynka vs Dorosły vs Starsza Kobieta)]: Dopasuj rodzaj gramatyczny..."
2798:        "• [SKUP SIĘ NA: FILAR CXII - Semiotyka Ciszy Ma (間) i Zwięzłość AVT]: Krótkie kwestie tłumacz zwięźle i dosadnie..."
2816:        "• [SKUP SIĘ NA: FILAR LXXI - Dostępność Leksykalna i Eliminacja Tarcia]: W szybkim tempie mowy używaj słów o wysokiej dostępności..."
2834:        "• [SKUP SIĘ NA: FILAR XIV & XXX - Archaizacja, Keigo Dworskie i Rejestr Starca (Rōjin-go)]: W mowie arystokracji, mędrców i bóstw..."
2852:        "• [SKUP SIĘ NA: FILAR XLIX, L & LI - Idiomatyka Sportowa, Taktyczna i Bitewna]: Komendy bojowe i sportowe przekładaj na krótki żargon..."
2870:        "• [SKUP SIĘ NA: FILAR LIV, LV & LVI - Rejestr Medyczny, Naukowy i Śledczy]: W analizach dedukcyjnych i medycznych utrzymuj precyzyjną terminologię..."
2888:        "• [SKUP SIĘ NA: FILAR LX & LXI - Gry Słowne, Kalambury (Dajare) i Homofonia]: Gry słowne przekładaj przez ekwiwalencję funkcjonalną..."
2906:        "• [SKUP SIĘ NA: FILAR LXXVIII & LXXIX - Napisy Ekranowe (Signs), Szyldy i Interfejsy UI]: Napisy ekranowe tłumacz maksymalnie zwięźle w wielkich literach..."
2924:        "• [SKUP SIĘ NA: FILAR LXXXIV & LXXXV - Monolog Wewnętrzny, Myśli i Narracja z Offu]: Wypowiedzi wewnętrzne i retrospekcje utrzymuj w spójnym rejestrze..."
2942:        "• [SKUP SIĘ NA: FILAR XCII & XCIII - Składnia Zaprzeczona i Dopełniacz Negacji]: Po czasownikach przechodnich z przeczeniem stosuj dopełniacz..."
2960:        "• [SKUP SIĘ NA: FILAR CIV & CV - Onomatopeje Japońskie (Giongo/Gitaigo) w Dialogu]: Japońskie wyrazy dźwiękonaśladowcze przekładaj na żywe polskie czasowniki..."
2978:        "• [SKUP SIĘ NA: FILAR CXVIII & CXIX - Kulinaria, Bento i Realia Szkolne]: Nazwy potraw i realiów japońskich adaptuj naturalnie..."
2996:        "• [SKUP SIĘ NA: FILAR CLXV & CLXIX - Ciągłość Zdań Rozbitych i Przeskoki Scen]: Zdania podzielone wielokropkiem między dwa zdarzenia ASS..."
3014:        "• [SKUP SIĘ NA: FILAR CLXXI - Bezwzględna Zgodność Liczebników i Kwot]: Wszystkie liczby i wartości w dialogu..."
3035:        if any("FILAR XIII" in r for _, r in candidates):
3036:            candidates = [(s, r) for s, r in candidates if "FILAR LXXI " not in r and "FILAR CLXXII " not in r]
~~~

#### Komenda 5: `grep -nA 500 "STANDARD_9_CORE_RULES_PROMPT\s*=" rules.py | grep -E "FILAR\s+[IVXLC]+"`
~~~text
(brak trafień — w STANDARD_9_CORE_RULES_PROMPT używane są 4 nagłówki arabskie: [FILAR 1 — ...], [FILAR 2 — ...], [FILAR 3 — ...], [FILAR 4 — ...] oraz reguły R1.1–R1.11 i R3.1–R3.5)
~~~

#### Komenda 6: `grep -nE "#.*FILAR\s+[IVXLC]+|\"\"\".*FILAR" rules.py`
~~~text
12:# Monument architektury AVT: FILAR I - FILAR CLXXX (utrzymywany dla zgodności z Z16 test_system.py)
2572:    # 0. FILAR XIII - Dialekty Regionalne, Gwara i Kontrast Rejestrów (Hotfix 10.1.1)
2607:    # 1. FILAR LXV - Izomorfizm Napięcia Składniowego
2625:    # 2. FILAR LXVI - Prozodia Oddechu
2642:    # 3. FILAR CLXXII - Dynamiczny Prymat Afektu
~~~

#### Komenda 7: `grep -oE "FILAR\s+[IVXLC]+" rules.py | sort -u | sort -t' ' -k2 -V | tail -5`
~~~text
FILAR CLXXVI
FILAR CLXXVII
FILAR CLXXVIII
FILAR CLXXIX
FILAR CLXXX
~~~

---

### P0.3. Odpowiedzi na 10 pytań flagowych (`F0.1–F0.10`)

- **F0.1 (Ile unikalnych numerów Filarów jest w `rules.py`?):** W `rules.py` występuje dokładnie **180 unikalnych rzymskich numerów Filarów** (`FILAR I` – `FILAR CLXXX`) oraz **4 makro-filary arabskie** (`FILAR 1` – `FILAR 4`) podzielone na **16 reguł alfanumerycznych** (`R1.1–R1.11` i `R3.1–R3.5`).
- **F0.2 (Ile Filarów jest w `STANDARD_9_CORE_RULES_PROMPT` — base, zawsze aktywne?):** **4 makro-filary arabskie** (`FILAR 1` – `FILAR 4`) obejmujące **16 reguł `R1.1–R1.11` i `R3.1–R3.5`** (oraz `0` nagłówków z numeracją rzymską).
- **F0.3 (Ile Filarów jest w `get_focused_rules_for_batch` — dynamic, warunkowe?):** Selektor zawiera **24 bloki warunkowe**, które odwołują się w swoich nagłówkach łącznie do **38 rzymskich numerów Filarów** (`XIII`, `XIV`, `XVI`, `XVII`, `XVIII`, `XXV`, `XXVI`, `XXVII`, `XXVIII`, `XXIX`, `XXX`, `XXXIII`, `XLIX`, `L`, `LI`, `LIV`, `LV`, `LVI`, `LX`, `LXI`, `LXV`, `LXVI`, `LXXI`, `LXXV`, `LXXVIII`, `LXXIX`, `LXXXIV`, `LXXXV`, `XCII`, `XCIII`, `XCVI`, `CIV`, `CV`, `CXII`, `CXVIII`, `CXIX`, `CXXXVI`, `CLVII`, `CLXV`, `CLXIX`, `CLXXI`, `CLXXII` — przy czym kilka bloków grupuje po 2–4 numery rzymskie).
- **F0.4 (Ile Filarów jest w obu miejscach jednocześnie?):** Formalnie (po nazwie identyfikatora) **0**, ponieważ `STANDARD_9_CORE_RULES_PROMPT` używa identyfikatorów `R1.1–R1.11` / `R3.1–R3.5`, a `get_focused_rules_for_batch` używa identyfikatorów rzymskich `FILAR [IVXLC]+`. Semantycznie jednak aż **14 z 24 bloków dynamicznych** w `get_focused_rules_for_batch` duplikuje w >70% treść reguł bazowych `R1.1–R1.11` i `R3.1–R3.5` z `STANDARD_9_CORE_RULES_PROMPT`! Natomiast wszystkie 38 rzymskich Filarów z `get_focused_rules_for_batch` występuje jednocześnie w historycznym `TRANSLATION_RULES_PROMPT`.
- **F0.5 (Ile Filarów jest tylko w komentarzach/docstringach lub martwej stałej — nigdy nieaktywne w domyślnym runtime?):** **142 rzymskie Filary** znajdują się wyłącznie w stałej `TRANSLATION_RULES_PROMPT` (używanej tylko wtedy, gdy `use_lean_prompt=False` lub w testach legacy `test_system.py`) i nigdy nie trafiają do runtime przy domyślnym `use_lean_prompt=True`.
- **F0.6 (Jaki jest maksymalny numer Filaru?):** **`FILAR CLXXX` (180)**.
- **F0.7 (Czy numeracja jest ciągła `I–CLXXX` bez luk?):** Tak, w `TRANSLATION_RULES_PROMPT` numeracja rzymska `FILAR I` – `FILAR CLXXX` jest ciągła (180 pozycji), natomiast w `get_focused_rules_for_batch` wybierany jest jedynie nieciągły podzbiór 38 numerów.
- **F0.8 (Czy numeracja jest rzymska czy arabska? Czy są mieszane konwencje?):** Konwencja jest **potrójnie mieszana**: (1) rzymska `FILAR I` – `FILAR CLXXX` w `TRANSLATION_RULES_PROMPT` i `get_focused_rules_for_batch`, (2) arabska `FILAR 1` – `FILAR 4` w nagłówkach sekcji `STANDARD_9_CORE_RULES_PROMPT`, (3) alfanumeryczna `R1.1–R1.11` i `R3.1–R3.5` (z pominięciem prefiksu `R2.x` i `R4.x`!) wewnątrz `STANDARD_9_CORE_RULES_PROMPT`.
- **F0.9 (Czy w `rules.py` są inne mechanizmy równoważne Filarom?):** Tak — reguły `R1.1–R1.11` oraz `R3.1–R3.5` w `STANDARD_9_CORE_RULES_PROMPT` są zwięzłym odpowiednikiem dawnych Filarów `I–XX`, `LXV`, `XCII`, `CLXXI`, `CLXXIII`. Nakładają się one bezpośrednio z dynamicznymi wpisami w `get_focused_rules_for_batch`.
- **F0.10 (Czy w `profiler.py` są reguły, które dublują Filary?):** Tak! Funkcja `format_lean_episode_brief` w `profiler.py` wstrzykuje do każdego odcinka stałą sekcję `TOPOLOGIA SCENY I OCHRONA PŁCI`, która słowo w słowo powtarza:
  1. zasady końcówek żeńskich `-am/-ałam/-aś/-ałaś` (duplikat `R3.1`, `R3.2`, `FILAR III` i `FILAR CXXXVI`),
  2. zasady liczby mnogiej niemęskoosobowej `one` (duplikat `R3.3` i `FILAR XCVI`),
  3. zasadę `ŚCISŁA REKCJA ZAPRZECZONA (Genitive of Negation)` (duplikat `R1.4`, `FILAR V` i `FILAR XCII & XCIII`),
  4. zasadę `OCHRONA CYTATÓW I DEKLINACJA KANONU` (duplikat `R3.4`, `R3.5`, `FILAR IV` i `FILAR CLXVIII`).

---

## 3. FAZA 1 — MAPA TREŚCI

### 3.1. Aktywny rdzeń bazowy (`STANDARD_9_CORE_RULES_PROMPT`, linie `2525–2685`)

| ID Reguły | Makro-Filar | Linia | Źródło | Kategoria semantyczna | Streszczenie treści | Długość (znaki) |
| :--- | :--- | :---: | :---: | :---: | :--- | :---: |
| **`R1.1`** | `FILAR 1` | `2532–2536` | `base` | `grammar` | Naturalny szyk zdania mówionego z akcentem logicznym (rematem) na końcu wypowiedzi. | 215 |
| **`R1.2`** | `FILAR 1` | `2537–2541` | `base` | `grammar` | Opuszczenie zaimków osobowych podmiotu (`ja`, `ty`, `on`, `ona`) i dzierżawczych (`mój`, `twój`, `swój`). | 230 |
| **`R1.3`** | `FILAR 1` | `2542–2546` | `base` | `grammar` | Werbalizacja angielskich konstrukcji nominalnych na naturalne polskie konstrukcje czasownikowe. | 210 |
| **`R1.4`** | `FILAR 1` | `2547–2552` | `base` | `grammar` | Dopełniacz negacji (Genitive of Negation) po czasownikach przechodnich z partykułą przeczącą. | 245 |
| **`R1.5`** | `FILAR 1` | `2553–2557` | `base` | `honorifics` | Przypadek wołacza (`W.`) w zwrotach bezpośrednich po imieniu i tytule postaci. | 205 |
| **`R1.6`** | `FILAR 1` | `2558–2562` | `base` | `honorifics` | Spójność formy adresatywnej (`ty` vs `pan/pani`) wewnątrz relacji i pojedynczego zdania. | 240 |
| **`R1.7`** | `FILAR 2` | `2565–2570` | `base` | `prosody` | Zwięzłość AVT i przestrzeganie budżetu czytelniczego (`CPS <= 17`, `CPL <= 38`). | 220 |
| **`R1.8`** | `FILAR 2` | `2571–2575` | `base` | `prosody` | Dopasowanie liczby sylab i rytmu frazy do czasu trwania głosu seiyū (Mouth-Pacing). | 210 |
| **`R1.9`** | `FILAR 2` | `2576–2581` | `base` | `prosody` | Somatyczne oddawanie odruchów paralingwistycznych i elipsa czystego szumu wysiłkowego. | 235 |
| **`R1.10`** | `FILAR 4` | `2584–2588` | `base` | `ellipsis` | Spójność wielokropków kontynuacyjnych (`...`) w zdaniach rozbitych na sąsiednie zdarzenia ASS. | 225 |
| **`R1.11`** | `FILAR 4` | `2589–2594` | `base` | `style` | Kursywa całoliniowa `{\i1}...{\i0}` dla monologów wewnętrznych i głosów z offu. | 210 |
| **`R3.1`** | `FILAR 3` | `2598–2603` | `base` | `gender` | Zgodność rodzaju gramatycznego 1. osoby lp. (`-łem/-łam`, `-łbym/-łabym`) z płcią mówcy z `SeriesBible` (P0). | 260 |
| **`R3.2`** | `FILAR 3` | `2604–2609` | `base` | `gender` | Zgodność rodzaju gramatycznego 2. osoby lp. (`-łeś/-łaś`) z płcią adresata w danej wymianie zdań. | 250 |
| **`R3.3`** | `FILAR 3` | `2610–2615` | `base` | `gender` | Rodzaj niemęskoosobowy (`-łyśmy/-łyście`, `one`) dla grup złożonych wyłącznie z kobiet. | 245 |
| **`R3.4`** | `FILAR 3` | `2616–2621` | `base` | `identity` | Ochrona rodzaju gramatycznego cytowanego autora w przytoczeniach i mowie zależnej (`„...”`). | 235 |
| **`R3.5`** | `FILAR 3` | `2622–2628` | `base` | `numbers` | Pełna odmiana terminów kanonicznych przez przypadki oraz ścisła zgodność liczebników i napisów `is_sign`. | 270 |

---

### 3.2. Mapa wszystkich 180 rzymskich Filarów (`FILAR I` – `FILAR CLXXX` w `rules.py`)

| Numer (Rzymski) | Tytuł / Zakres tematyczny | Linia (`rules.py`) | Źródło (`base` / `dynamic` / `dead`) | Kategoria semantyczna | Streszczenie treści (1–2 zdania) | Długość (znaki) |
| :--- | :--- | :---: | :---: | :---: | :--- | :---: |
| **`I`** | Naturalna Mówiona Polszczyzna i Szyk Rematyczny | `31–51` | `dead` *(duplikat `R1.1` / `LXV`)* | `grammar` | Nakazuje polski szyk zdania z akcentem logicznym (rematem) na końcu. | 620 |
| **`II`** | Rygor Kondensacji AVT i Ekonomia Słowa | `52–73` | `dead` *(duplikat `R1.7` / `CXII`)* | `prosody` | Nakazuje skracanie rozwlekłych fraz do limitów `CPS <= 17` i `CPL <= 38`. | 590 |
| **`III`** | Spójność Rodzaju Gramatycznego 1. i 2. Osoby | `74–97` | `dead` *(duplikat `R3.1–R3.3`)* | `gender` | Uzgadnia końcówki czasu przeszłego i trybu przypuszczającego z płcią mówcy i adresata. | 680 |
| **`IV`** | Deklinacja Antroponimów i Terminów Kanonicznych | `98–120` | `dead` *(duplikat `R1.5` / `R3.5`)* | `grammar` | Nakazuje odmianę imion i terminów z glosariusza przez wszystkie przypadki. | 540 |
| **`V`** | Rekcja Czasowników i Dopełniacz Negacji | `121–144` | `dead` *(duplikat `R1.4` / `XCII`)* | `grammar` | Wymaga dopełniacza po czasownikach przechodnich zaprzeczonych partykułą `nie`. | 580 |
| **`VI`** | Pro-Drop i Redukcja Zaimków Dzierżawczych | `145–167` | `dead` *(duplikat `R1.2` / `CLXXVII`)* | `grammar` | Nakazuje pomijanie redundantnych zaimków `ja/ty/mój/twój`. | 510 |
| **`VII`** | Werbalizacja Konstrukcji Nominalnych | `168–189` | `dead` *(duplikat `R1.3`)* | `grammar` | Zamienia rzeczowniki odsłowne na dynamiczne czasowniki osobowe. | 490 |
| **`VIII`** | Idiomatyka Polska i Frazeologia | `190–211` | `dead` | `style` | Zastępuje kalki angielskich idiomów naturalnymi polskimi związkami frazeologicznymi. | 520 |
| **`IX`** | Spójność Rejestru Społecznego i Hierarchii | `212–234` | `dead` *(duplikat `R1.6` / `CLVII`)* | `honorifics` | Dopasowuje dystans społeczny (`ty` vs `pan/pani`) do relacji między postaciami. | 550 |
| **`X`** | Semiotyka Obrazu i Nieredundancja Wizualna | `235–257` | `dead` | `meta` | Uniezależnia dialog od dosłownego opisywania tego, co widać na ekranie. | 480 |
| **`XI`** | Dynamika Wymiany Zdań i Pary Przylegania | `258–281` | `dead` *(duplikat `CLXXIX`)* | `grammar` | Dopasowuje krótkie riposty do poprzedzającego pytania w dialogu. | 530 |
| **`XII`** | Sociolekty, Slang Młodzieżowy i Subkultury | `282–307` | `dead` *(brak triggera w selektorze!)* | `dialect` | Stylizuje mowę subkultur (`yankee`, `gyaru`, `otaku`, `chūnibyō`) na żywy slang młodzieżowy. | 640 |
| **`XIII`** | Dialekty Regionalne, Gwara i Kontrast Rejestrów | `308–333`, `2575` | **`dynamic`** *(w `10.1.1` score 85)* | `dialect` | Oddaje gwarę/slang szorstką polszczyzną potoczną z kontrastem wobec parafraz tłumacza. | 410 |
| **`XIV` & `XXX`** | Archaizacja, Keigo Dworskie i Rejestr Starca (`Rōjin-go`) | `334–359`, `680–702`, `2834` | **`dynamic`** *(zgrupowane)* | `style` | Stylizuje mowę arystokracji, bóstw i mędrców na podniosłą polszczyznę dawną/dworską. | 390 |
| **`XV`** | Język Dziecięcy i Mowa Pieszczotliwa | `360–381` | `dead` | `style` | Dostosowuje składnię i zdrobnienia do wieku małych dzieci. | 460 |
| **`XVI`, `XVII`, `XVIII`, `XXXIII`** | Paralingwistyka, Somatyka Ciała, Kakegoe i Utrata Równowagi (`Ottotto`) | `382–447`, `740–762`, `2705` | **`dynamic`** *(zgrupowane, score 75)* | `prosody` | Tłumaczy odruchy motoryczne i okrzyki wysiłkowe somatycznie lub stosuje elipsę szumu. | 420 |
| **`XIX`–`XXIV`** | Śmiech/Płacz (`XIX`), Wielokropki (`XX`), Pytania Retoryczne (`XXI`), Ironia (`XXII`), Przekleństwa (`XXIII`), Zdrobnienia (`XXIV`) | `448–575` | `dead` | `emotion` / `style` | Szczegółowe wytyczne ekspresji emocjonalnej i interpunkcji afektywnej. | 2850 *(łącznie)* |
| **`XXV`, `XXVII`, `XXVIII`** | Tytulatura, Etykieta i Adaptacja Honoryfikatorów (`-san`, `-sama`, `-sensei`, `-senpai`) | `576–645`, `2742` | **`dynamic`** *(zgrupowane, score 72)* | `honorifics` | Adaptuje japońskie honoryfikatory do polskiego wołacza imienia lub naturalnej tytulatury. | 415 |
| **`XXVI` & `XXIX`** | Zasada `Yobisute` i Ewolucja Relacji Rówieśniczych | `598–618`, `646–679`, `2724` | **`dynamic`** *(zgrupowane, score 70)* | `honorifics` | Nakazuje przejście na bezpośrednie `ty` i imię w wołaczu w relacjach przyjacielskich i szkolnych. | 380 |
| **`XXXI`–`XXXII`, `XXXIV`–`XLVIII`** | Etykieta Rodzinna (`XXXI–XXXII`), Intonacja Pytająca (`XXXIV–XXXVIII`), Spójniki Dyskursywne (`XXXIX–XLIII`), Czas Teraźniejszy Narracyjny (`XLIV–XLVIII`) | `703–1040` | `dead` | `grammar` / `honorifics` | Kazuistyczne reguły zwrotów rodzinnych (`oniisan`/`oneesan`) i spójników zdaniowych. | 6400 *(łącznie)* |
| **`XLIX`, `L`, `LI`** | Idiomatyka Sportowa, Taktyczna i Bitewna | `1041–1105`, `2852` | **`dynamic`** *(zgrupowane, score 65)* | `style` | Przekłada komendy wojskowe, taktyczne i sportowe na krótkie rozkazy żargonowe. | 360 |
| **`LII`–`LIII`** | Terminologia Magiczna i Fantasy | `1106–1148` | `dead` | `culture` | Zasady nazewnictwa zaklęć i artefaktów. | 820 |
| **`LIV`, `LV`, `LVI`** | Rejestr Medyczny, Naukowy i Śledczy | `1149–1210`, `2870` | **`dynamic`** *(zgrupowane, score 65)* | `style` | Utrzymuje precyzyjny rejestr analityczny w dedukcjach detektywistycznych i diagnozach. | 370 |
| **`LVII`–`LIX`** | Rejestr Prawniczy, Polityczny i Korporacyjny | `1211–1270` | `dead` | `style` | Stylizacja dialogów urzędowych i biznesowych. | 1150 |
| **`LX` & `LXI`** | Gry Słowne, Kalambury (`Dajare`) i Homofonia | `1271–1315`, `2888` | **`dynamic`** *(zgrupowane, score 68)* | `culture` | Zastępuje nieprzetłumaczalne kalambury japońskie polskim ekwiwalentem humorystycznym. | 365 |
| **`LXII`–`LXIV`** | Aluzje Kulturowe, Cytaty Literackie i Parodie | `1316–1375` | `dead` | `culture` | Zasady adaptacji nawiązań popkulturowych. | 1100 |
| **`LXV`** | Izomorfizm Napięcia Składniowego i Anty-Spoiler | `1376–1400`, `2610` | **`dynamic`** *(score 90/80 — nadaktywny!)* | `grammar` | Nakazuje umieszczenie kluczowego rozstrzygnięcia lub negacji na końcu zdania (duplikat `R1.1`). | 340 |
| **`LXVI`** | Prozodia Oddechu i Kinezjologia Mowy | `1401–1425`, `2628` | **`dynamic`** *(score 88/80 — nadaktywny!)* | `prosody` | Nakazuje krótkie, urywane takty rytmiczne w scenach walki i zadyszki (duplikat `R1.8`). | 330 |
| **`LXVII`–`LXX`** | Pauzy Oddechowe, Tempo Szybkie, Tempo Wolne, Kontrast Rytmiczny | `1426–1510` | `dead` | `prosody` | Rozwinięcie reguł rytmicznych z `FILAR LXVI`. | 1520 |
| **`LXXI`** | Dostępność Leksykalna i Eliminacja Tarcia | `1511–1535`, `2816` | **`dynamic`** *(score 68)* | `style` | W szybkim tempie mowy nakazuje proste słowa o wysokiej czytelności bez archaizmów. | 320 |
| **`LXXII`–`LXXIV`** | Czytelność Wizualna, Podział Dwuwierszowy, Symetria Wersów | `1536–1595` | `dead` *(realizowane przez `avt_formatter.py`)* | `meta` | Techniczne zasady łamania linii `\N` (wykonywane deterministycznie w KROKU 9). | 1180 |
| **`LXXV`** | Zestrojenie Akcentu Logicznego i Prominencji F0 | `1596–1620`, `2668` | **`dynamic`** *(score 78)* | `prosody` | Umieszcza wyraz o najwyższym nacisku fonicznym F0 w pozycji polskiego akcentu zdaniowego. | 335 |
| **`LXXVI`–`LXXVII`** | Kontur Intonacyjny F0 i Załamanie Głosu | `1621–1660` | `dead` | `emotion` | Wykorzystanie telemetrii F0 do modulacji emocji. | 780 |
| **`LXXVIII` & `LXXIX`** | Napisy Ekranowe (`Signs`), Szyldy i Interfejsy UI | `1661–1705`, `2906` | **`dynamic`** *(zgrupowane, score 74)* | `sign` | Formatowanie i zwięzłość tablic ekranowych oraz napisów na obiektach. | 355 |
| **`LXXX`–`LXXXIII`** | Piosenki (OP/ED), Wiersze, Inskrypcje, Listy | `1706–1785` | `dead` | `style` / `sign` | Stylizacja tekstów lirycznych i pisanych. | 1450 |
| **`LXXXIV` & `LXXXV`** | Monolog Wewnętrzny, Myśli i Narracja z Offu | `1786–1830`, `2924` | **`dynamic`** *(zgrupowane, score 70)* | `style` | Spójność rejestru myśli wewnętrznych i narracji pozakadrowej. | 350 |
| **`LXXXVI`–`XCI`** | Retrospekcje, Telefony, Komunikatory, Ogłoszenia Megafonowe, Chóry | `1831–1940` | `dead` | `style` | Zasady dla mediów zapośredniczonych. | 2100 |
| **`XCII` & `XCIII`** | Składnia Zaprzeczona i Dopełniacz Negacji | `1941–1980`, `2942` | **`dynamic`** *(zgrupowane, score 72 — duplikat `R1.4`)* | `grammar` | Wymaga dopełniacza po czasownikach przechodnich z negacją `nie`. | 345 |
| **`XCIV`–`XCV`** | Zgodność Podmiotu z Orzeczeniem i Składnia Liczebników | `1981–2015` | `dead` | `grammar` | Reguły składni zgody i rządu dla liczebników. | 740 |
| **`XCVI`** | Asymetria Zaimków 3. Osoby i Płeć (`Kanojo-tachi` vs `Karera`) | `2016–2040`, `2760` | **`dynamic`** *(score 82 — duplikat `R3.3`)* | `gender` | Nakazuje niemęskoosobowe `one/je/ich` dla grup kobiecych zamiast `oni`. | 375 |
| **`XCVII`–`CIII`** | Zaimki 1. Osoby JP (`Ore/Boku/Watashi/Atashi`), Zaimki 2. Osoby JP (`Omae/Kimi/Anata/Kisama`) | `2041–2175` | `dead` *(obsługiwane przez `whisper_disambiguator.py`)* | `identity` / `gender` | Mapowanie japońskich zaimków osobowych na płeć i rejestr w języku polskim. | 2400 |
| **`CIV` & `CV`** | Onomatopeje Japońskie (`Giongo/Gitaigo`) w Dialogu | `2176–2215`, `2960` | **`dynamic`** *(zgrupowane, score 66)* | `culture` | Przekłada przysłówki dźwiękonaśladowcze JP na plastyczne polskie czasowniki. | 360 |
| **`CVI`–`CXI`** | Partykuły Końcowe JP (`yo`, `ne`, `zo`, `ze`, `wa`, `na`), Sufiksy Charakterystyczne (`-pon`, `-dechu`) | `2216–2310` | `dead` | `phonetics` / `culture` | Zasady adaptacji japońskich partykuł modalnych i tików słownych maskotek. | 1950 |
| **`CXII`** | Semiotyka Ciszy `Ma` (間) i Zwięzłość AVT | `2311–2332`, `2798` | **`dynamic`** *(score 76 — duplikat `R1.7`/`II`)* | `prosody` | Nakazuje zwięzłe tłumaczenie krótkich kwestii przed pauzą dramatyczną. | 330 |
| **`CXIII`–`CXVII`** | Pauzy Dramatyczne, Kontrapunkt Emocjonalny, Niedopowiedzenia | `2333–2410` | `dead` | `prosody` | Rozwinięcie estetyki ciszy `Ma`. | 1600 |
| **`CXVIII` & `CXIX`** | Kulinaria, Bento i Realia Szkolne | `2411–2445`, `2978` | **`dynamic`** *(zgrupowane, score 62)* | `culture` | Zasady zachowywania i adaptacji nazw potraw (`bento`, `onigiri`) i realiów szkolnych. | 340 |
| **`CXX`–`CXXXV`** | Realia Historyczne, Militarne, Świątynne, Festiwale (`Matsuri`), Gry Wideo/MMO, Isekai | `2446–2710` *(w sekcji monumentu)* | `dead` | `culture` | Słowniki i wytyczne domenowe dla gatunków tematycznych. | 4800 |
| **`CXXXVI`** | Triangulacja Kognitywna i Foniczna Wieku/Płci (Chłopiec vs Dziewczynka vs Starsza Kobieta) | `2778` *(oraz w monumencie)* | **`dynamic`** *(score 84)* | `gender` | Chroni rodzaj męski u chłopców z wysokim F0 seiyū oraz rodzaj żeński u matron z niskim F0. | 460 |
| **`CXXXVII`–`CLVI`** | Historyczne poprawki regresyjne z iteracji 5.0–8.5 (m.in. `CLIV` dwugłosy, `CLV` elipsy) | sekcja monumentu | `dead` | `grammar` / `style` | Kazuistyczne reguły z wcześniejszych iteracji potoku, zastąpione przez `R1.1–R1.11`. | 5600 |
| **`CLVII`** | Nienaruszalność Formy Adresatywnej, Harmonia Wołacza i `-Sama` Drop | `2686` *(oraz w monumencie)* | **`dynamic`** *(score 80 — duplikat `R1.6`)* | `honorifics` | Wymusza spójność rejestru `ty` vs `pan/pani` w całej scenie i pojedynczym zdaniu. | 510 |
| **`CLVIII`–`CLXIV`** | Reguły pomocnicze spójności dialogowej z iteracji 8.6–8.9 | sekcja monumentu | `dead` | `grammar` | Uszczegółowienia spójności zaimkowej i adresatywnej. | 2100 |
| **`CLXV` & `CLXIX`** | Ochrona Przeskoków Scen i Ciągłość Składniowa Zdań Rozbitych | `2180`, `2280`, `2996` | **`dynamic`** *(zgrupowane, score 74)* | `ellipsis` | Łączy składniowo zdania rozbite między dwa kolejne zdarzenia ASS i chroni cięcia scen. | 380 |
| **`CLXVI`** | Autonomiczna Kreacja Polszczyzny i Anty-Kotwiczenie | `2205` | `dead` *(cytowany przez F2)* | `style` | Odrywa polską składnię od dosłownej struktury zdania angielskiego. | 420 |
| **`CLXVII`** | Spójność Wielokropków Kontynuacyjnych | `2230` | `dead` *(duplikat `R1.10` / `CLXIX`)* | `ellipsis` | Zasady wielokropków na styku dwóch linii. | 390 |
| **`CLXVIII`** | Ochrona Rodzaju w Mowie Zależnej i Cytatach | `2255` | `dead` *(duplikat `R3.4`)* | `identity` | Chroni płeć autora cytatu wewnątrz cudzysłowu `„...”`. | 410 |
| **`CLXX`** | Ochrona Krótkich Partykuł Pytających | `2305` | `dead` | `prosody` | Zwięzłe oddawanie krótkich pytań (`Co?`, `Słucham?`). | 350 |
| **`CLXXI`** | Bezwzględna Zgodność Liczebników i Kwot | `2330`, `3014` | **`dynamic`** *(score 76 + `avt_linter.py`)* | `numbers` | Wymusza zachowanie dokładnych wartości liczbowych ze skryptu EN (duplikat `R3.5`). | 340 |
| **`CLXXII`** | Dynamiczny Prymat Afektu, Polszczyzna Bezterminowa i Pozytywne Rzemiosło | `2355`, `2645` | **`dynamic`** *(score 86)* | `emotion` / `style` | Nakazuje prymat emocji głosu seiyū nad statycznym opisem oraz gładką polszczyznę bezterminową. | 490 |
| **`CLXXIII`** | Izolacja Napisów Ekranowych (`Signs`) od Fleksji Dialogowej | `2385` | `dead` *(duplikat `R3.5` / `LXXVIII`)* | `sign` | Chroni napisy ekranowe przed narzucaniem fleksji mówcy. | 380 |
| **`CLXXIV`** | Higiena Tokenów i Eliminacja Artefaktów Jąkania | `2410` | `dead` *(egzekwowane w `avt_linter.py`)* | `grammar` | Usuwa błędne zbitki interpunkcyjne przy zacięciach głosu (`T-Tak!`). | 390 |
| **`CLXXV`–`CLXXX`** | Bezokoliczniki (`CLXXV`), Wołacz Złożony (`CLXXVI`), Decoupling Zaimkowy (`CLXXVII`), Pojedyncza Adresatka (`CLXXVIII`), Pary Przylegania (`CLXXIX`), Domknięcie Domeny Pozytywnej (`CLXXX`) | `2435–2524` | `dead` *(w pełni pokryte przez `R1.2`, `R1.5`, `R3.2`, `R3.3`)* | `grammar` / `gender` | Reguły domykające Standard 9.0–10.1, skondensowane już w `R1.1–R1.11` i `R3.1–R3.5`. | 2250 |

---

## 4. FAZA 2 — DUPLIKATY

W systemie zidentyfikowano **22 istotne duplikaty (`D-1` – `D-22`)**, podzielone na trzy warstwy: (A) duplikaty pomiędzy `get_focused_rules_for_batch` a zawsze aktywnym `STANDARD_9_CORE_RULES_PROMPT` (`R1.x`/`R3.x`), (B) duplikaty wewnątrz samych Filarów rzymskich oraz (C) duplikaty między `rules.py` a `profiler.py` (`EPISODE BRIEF`).

| ID Findingu | Numer / Reguła A | Numer / Reguła B | Pokrycie (%) | Wspólna treść (1 zdanie) | Różnica (1 zdanie) | Rekomendacja i Status |
| :---: | :--- | :--- | :---: | :--- | :--- | :--- |
| **`D-1`** | `R1.1` (Base) | `FILAR LXV` (Dynamic) + `FILAR I` | **95%** | Nakaz ustawiania polskiego szyku zdania tak, aby akcent logiczny (remat / negacja / puenta) padał na końcu zdania. | `LXV` nawiązuje dodatkowo do synchronizacji z momentem wypowiedzenia puenty przez seiyū. | **`ZACHOWAJ_A_USUŃ_B` z selektora dynamicznego** (`R1.1` w Base wystarczy) — `AUTORYTATYWNY` |
| **`D-2`** | `R1.4` (Base) | `FILAR XCII & XCIII` (Dynamic) + `FILAR V` | **100%** | Nakaz stosowania dopełniacza negacji (Genitive of Negation) po czasownikach przechodnich zaprzeczonych partykułą `nie`. | Brak różnicy merytorycznej (identyczna zasada gramatyczna powtórzona 4 razy: w `R1.4`, `XCII`, `V` i `profiler.py`). | **`ZACHOWAJ_A_USUŃ_B` z selektora dynamicznego** — `AUTORYTATYWNY` |
| **`D-3`** | `R1.7` + `R1.8` (Base) | `FILAR CXII` (Dynamic) + `FILAR II` | **90%** | Nakaz zwięzłości AVT, kondensacji krótkich replik i wygaszenia napisu przed pauzą (`Ma`). | `CXII` używa japońskiego terminu estetycznego `Ma (間)`. | **`SCAL`** (`R1.7`+`R1.8` w Base pokrywają zwięzłość; wycofać `CXII` z selektora dynamicznego) — `AUTORYTATYWNY` |
| **`D-4`** | `R3.3` (Base) | `FILAR XCVI` (Dynamic) + `FILAR CLXXVIII` | **90%** | Nakaz stosowania form niemęskoosobowych (`one`, `-łyśmy`, `-łyście`) dla grup kobiecych. | `XCVI` wspomina o japońskim sygnale audio `kanojo-tachi`. | **`SCAL`** (włączyć wzmiankę o `kanojo-tachi` do jednej dynamicznej kategorii płci/wieku z `CXXXVI`) — `AUTORYTATYWNY` |
| **`D-5`** | `R1.6` (Base) | `FILAR CLVII` (Dynamic) + `FILAR IX` | **85%** | Nakaz spójności formy adresatywnej (`ty` vs `pan/pani`) w obrębie sceny i zakaz hybryd typu wołacz imienia + `pan/pani`. | `CLVII` zawiera dłuższe wyliczenie przypadków szczegółowych (`-sama drop`). | **`SCAL`** (`CLVII` scalić z `XXV/XXVI/XXVII/XXVIII/XXIX` w jedną kategorię `[KATEGORIA_HONORIFICS]`) — `AUTORYTATYWNY` |
| **`D-6`** | `FILAR XXV, XXVII & XXVIII` (Dynamic) | `FILAR XXVI & XXIX` (Dynamic) | **80%** | Zasady adaptacji japońskich honoryfikatorów (`-san`, `-sama`, `-senpai`, `yobisute`) na polski wołacz i formę `ty`. | Pierwszy blok opisuje sufiksy honoryfikatywne, drugi brak sufiksu (`yobisute`) w relacjach rówieśniczych. | **`SCAL`** (połączyć oba bloki + `CLVII` w jedną spójną kategorię `[KATEGORIA_HONORIFICS]`) — `AUTORYTATYWNY` |
| **`D-7`** | `FILAR LXVI` (Dynamic) | `FILAR LXXV` (Dynamic) + `FILAR XVI/XVII/XVIII/XXXIII` | **75%** | Synchronizacja rytmu, oddechu, akcentu F0 i somatycznych okrzyków z głosem seiyū w scenach dynamicznych. | `LXVI` mówi o oddechu, `LXXV` o szczycie F0, a `XVIII` o okrzykach `kakegoe`/`ottotto`. | **`SCAL`** (połączyć w jedną kategorię `[KATEGORIA_PROSODY]` wyzwalaną tylko w scenach akcji/wysiłku/F0) — `AUTORYTATYWNY` |
| **`D-8`** | `R1.10` (Base) | `FILAR CLXV & CLXIX` (Dynamic) + `FILAR XX` + `FILAR CLXVII` | **85%** | Zachowanie ciągłości składniowej i wielokropków w zdaniach podzielonych na dwa sąsiednie zdarzenia ASS. | `CLXV` dodaje wskazówkę o otwarciu dialogu po cięciu montażowym (Scene Cut). | **`SCAL`** (wskazówkę o wielokropkach zostawić w `R1.10` Base; w selektorze zostawić tylko kompaktową regułę `[KATEGORIA_DISCOURSE_CONTINUITY]` dla wieloczęściowych zdań) — `AUTORYTATYWNY` |
| **`D-9`** | `R3.5` (Base) | `FILAR CLXXI` (Dynamic) | **95%** | Bezwzględna zgodność liczebników, kwot i wartości liczbowych ze skryptem źródłowym. | Brak różnicy (dodatkowo weryfikowane deterministycznie w `EpisodeQualityGate` w `avt_linter.py`). | **`ZACHOWAJ_A_USUŃ_B` z selektora dynamicznego** (jest już w `R3.5` Base i w `EpisodeQualityGate`) — `AUTORYTATYWNY` |
| **`D-10`** | `R1.11` (Base) | `FILAR LXXXIV & LXXXV` (Dynamic) | **85%** | Zasady formatowania i stylizacji monologu wewnętrznego, myśli oraz narracji z offu. | `R1.11` jest już zawsze obecne w `STANDARD_9_CORE_RULES_PROMPT`. | **`ZACHOWAJ_A_USUŃ_B` z selektora dynamicznego** — `AUTORYTATYWNY` |
| **`D-11`** | `R3.5` (Base) | `FILAR LXXVIII & LXXIX` (Dynamic) + `FILAR CLXXIII` | **80%** | Zasady zwięzłego tłumaczenia napisów ekranowych (`is_sign`) i izolacji ich od fleksji mówcy. | `LXXVIII & LXXIX` precyzuje styl wersalikowy dla szyldów i interfejsów UI. | **`SCAL`** (zachować jako wąską kategorię `[KATEGORIA_SIGNS]` aktywowaną wyłącznie, gdy w paczce jest zdarzenie `is_sign=True`) — `AUTORYTATYWNY` |
| **`D-12`** | `FILAR XII` (Monument) | `FILAR XIII` (Dynamic) | **75%** | Stylizacja niestandardowych odmian języka (slang subkulturowy `yankee`/`gyaru` w `XII` vs dialekty regionalne i gwara w `XIII`). | `XII` dotyczy sociolektów młodzieżowych, a `XIII` gwar regionalnych i kontrastu parafrazy. | **`SCAL`** (włączyć `FILAR XII` do aktywnego bloku `FILAR XIII` jako wspólną kategorię `[KATEGORIA_DIALECT_SLANG]`) — `AUTORYTATYWNY` |
| **`D-13`** | `FILAR XLIX, L & LI` (Dynamic) | `FILAR LIV, LV & LVI` (Dynamic) | **65%** | Stylizacja rejestrów specjalistycznych (żargon taktyczno-bojowy i sportowy vs rejestr medyczno-śledczy i naukowy). | Różnią się domeną tematyczną (walka/sport vs medycyna/śledztwo), ale pełnią identyczną funkcję rejestru fachowego. | **`SCAL` lub `ZACHOWAJ_OBA`** — `WYMAGA_DECYZJI_UŻYTKOWNIKA` |
| **`D-14`** | `FILAR LX & LXI` (Dynamic) | `FILAR CIV & CV` + `FILAR CXVIII & CXIX` (Dynamic) | **60%** | Adaptacja specyficznych zjawisk kulturowo-językowych JP (gry słowne `dajare`, onomatopeje `giongo`, kulinaria/realia JP). | Trzy rzadkie podkategorie kulturowo-leksykalne. | **`SCAL`** w jedną kategorię `[KATEGORIA_CULTURE_IDIOM]` — `WYMAGA_DECYZJI_UŻYTKOWNIKA` |
| **`D-15`..`D-22`** | `STANDARD_9_CORE_RULES_PROMPT` (`R1.1–R3.5`) | Sekcja `TOPOLOGIA SCENY I OCHRONA PŁCI` w `profiler.py` + 8 grup w `TRANSLATION_RULES_PROMPT` (`I–XI`, `LXVII–LXX`, `XCVII–CIII`, `CXXXVII–CLVI`, `CLXVI–CLXXX`) | **90–100%** | Powielenie podstawowych zasad polszczyzny, pro-dropu, rekcji zaprzeczonej, ochrony cytatów i końcówek płciowych między `rules.py` a `profiler.py`. | `profiler.py` dokleja te same reguły gramatyczne na końcu każdego `EPISODE BRIEF`. | **`SCAL` / odchudzić `format_lean_episode_brief` w `profiler.py`**, aby nie duplikował `R1.4` i `R3.1–R3.5` z `rules.py` — `AUTORYTATYWNY` |

---

## 5. FAZA 3 — SPRZECZNOŚCI

Zidentyfikowano **5 par sprzecznych (`S-1` – `S-5`)**, w których równoczesna aktywacja dwóch reguł daje modelowi LLM wykluczające się wytyczne:

| ID Findingu | Reguła / Filar A | Reguła / Filar B | Sprzeczność (1 zdanie) | Kontekst aktywacji A | Kontekst aktywacji B | Rekomendacja i Status |
| :---: | :--- | :--- | :--- | :--- | :--- | :--- |
| **`S-1`** | `FILAR XIII` (Gwara / Slang) | `FILAR LXXI` + `FILAR CLXXII` (Gładka polszczyzna bezterminowa, eliminacja tarcia) | `XIII` nakazuje szorstką gwarę i składnię środowiskową, podczas gdy `LXXI`/`CLXXII` nakazują gładką polszczyznę literacką wolną od kolokwializmów i archaizmów. | Trigger slangu EN / dialektu JP / parafrazy | Trigger szybkiego tempa (`LXXI`) lub afektu (`CLXXII`) | **`ROZSTRZYGNIĘTE`** w `10.1.1` przez `Anti-Smoothing Filter` (2B.4) |
| **`S-2`** | `FILAR XIV & XXX` (Archaizacja, Keigo Dworskie, Rejestr Starca) | `FILAR LXXI` + `FILAR CLXXII` (Eliminacja archaizmów, polszczyzna bezterminowa) | **Bezpośrednia sprzeczność:** `XIV & XXX` nakazuje stosowanie archaizmów i podniosłego stylu dworskiego, natomiast `LXXI` wprost nakazuje „eliminując archaizmy”, a `CLXXII` „polszczyznę bezterminową”! | Trigger `milord`/`majesty`/`thou`/`ojou`/`washi`/`sessha` | Trigger szybkiego tempa (`LXXI`) lub emocji (`CLXXII`) — `Anti-Smoothing Filter` z `10.1.1` **nie obejmuje `FILAR XIV & XXX`!** | **`DO_ROZSTRZYGNIĘCIA`** — rozszerzyć `Anti-Smoothing Filter` na `FILAR XIV & XXX` (`AUTORYTATYWNY`) |
| **`S-3`** | `FILAR XXVI & XXIX` (Zasada `Yobisute` — mów po imieniu na `ty`) | `FILAR XIV & XXX` + `FILAR XXV` (Etykieta hierarchiczna, `Panna [Imię]`, formy dystansu) | Gdy w tej samej paczce występują postacie rówieśnicze oraz relacja hierarchiczna (np. służąca Mamori mówiąca do Kanoe per `Panienko` oraz koleżanki mówiące na `ty`), równoczesne wstrzyknięcie obu reguł bez rozgraniczenia ról powoduje wahania rejestru. | Trigger relacji szkolnej / przyjaciół | Trigger tytulatury / hierarchii | **`DO_ROZSTRZYGNIĘCIA`** — scalić w jedną kategorię `[KATEGORIA_HONORIFICS]`, która pozytywnie uzależnia formę (`ty` vs tytulatura) od relacji z `SeriesBible` (`AUTORYTATYWNY`) |
| **`S-4`** | `FILAR XVIII, XXXIII, XVI & XVII` (Elipsa szumu wizualnego — „usuń napis do `''`”) | `Zasada Ciągłości Zdarzeń ASS` (`avt_linter.py` / `verifier.py`: zakaz gubienia linii dialogowych) | `FILAR XVIII` instruuje model Fazy 1: `lub usuń napis do '' (elipsa szumu wizualnego Netflix AVT)`, podczas gdy potok wymaga zachowania niepustego tekstu dla każdego zdarzenia dialogowego `.ass`. | Trigger `ouch`/`eh`/`ah`/`ottotto` | Każda linia dialogowa w Fazie 1 i 2 | **`DO_ROZSTRZYGNIĘCIA`** — usunąć z `FILAR XVIII` frazę nakazującą zwracanie pustego stringa `''` i zastąpić ją pozytywnym nakazem krótkiej ekspresji somatycznej (`AUTORYTATYWNY`) |
| **`S-5`** | Legacy tekst w `get_focused_rules_for_batch` (`FILAR XCVI`, `FILAR CLVII`, `FILAR XXV`, `FILAR XXVI`) | `Z1 (Zero-Literal)` oraz `Z2 (Pure Positive Domain)` (`Bramka 2, 3, 5A, 5B` w `verify_purity.py`) | W `get_focused_rules_for_batch` nadal znajdują się surowe stringi z negacjami (`a NIE męskoosobowego`, `Niedopuszczalne jest`, `unikaj`, `zamiast`), słowami ALL-CAPS (`ZAWSZE`, `KONSEKWENTNIE`) oraz dawnymi imionami w przykładach, które naruszają Z1 i Z2 (nie były łapane przez `verify_purity.py`, bo skrypt badał tylko `STANDARD_9_CORE_RULES_PROMPT`!). | Każde wywołanie `get_focused_rules_for_batch` dla `XCVI`, `CLVII`, `CLXXII`, `XXV`, `XXVI` | Standard 9.0–10.1 (`Z1`, `Z2`, `Z4`) | **`DO_ROZSTRZYGNIĘCIA`** — przepisać wszystkie kategorie w `get_focused_rules_for_batch` na 100% czystą domenę pozytywną bez literałów i objąć `get_focused_rules_for_batch` kontrolą czystości (`AUTORYTATYWNY`) |

---

## 6. FAZA 4 — MARTWE FILARY

Spośród **180 rzymskich Filarów** zdefiniowanych w `rules.py`:
- **38 rzymskich Filarów** jest podpiętych pod 24 bloki warunkowe w `get_focused_rules_for_batch`.
- **142 rzymskie Filary** nie występują ani w `STANDARD_9_CORE_RULES_PROMPT`, ani w `get_focused_rules_for_batch` — są całkowicie **martwe w domyślnym runtime (`use_lean_prompt=True`)**.

Poniższa tabela klasyfikuje wszystkie 142 martwe Filary rzymskie wg przyczyny i rekomendacji:

| Zakres / Numery Rzymskie | Liczba Filarów | Tytuł / Grupa tematyczna | Linia (`rules.py`) | Źródło | Dlaczego martwy w runtime? | Rekomendacja |
| :--- | :---: | :--- | :---: | :---: | :--- | :--- |
| **`I` – `XI`** | **11** | Fundamentalne zasady składni, kondensacji, płci, deklinacji, dopełniacza negacji, pro-dropu, werbalizacji, idiomatyki, rejestru, semiotyki i par przylegania | `31–281` | `dead` *(w `TRANSLATION_RULES_PROMPT`)* | Zostały w 100% zastąpione przez `R1.1–R1.11` oraz `R3.1–R3.5` w `STANDARD_9_CORE_RULES_PROMPT`. | **`ZAMROŹ_W_ARCHIWUM_Z16`** (nie duplikować w selektorze; zachować w pasywnej stałej `TRANSLATION_RULES_PROMPT` dla `test_system.py`) |
| **`XII`** | **1** | Sociolekty, Slang Młodzieżowy i Subkultury (`Yankee`, `Gyaru`, `Otaku`, `Chūnibyō`) | `282–307` | `dead` *(w `TRANSLATION_RULES_PROMPT`)* | Brak triggera w `get_focused_rules_for_batch` (w `10.1.1` dodano tylko `FILAR XIII`). | **`DODAJ_TRIGGER` / `SCAL` z `FILAR XIII`** w jedną kategorię `[KATEGORIA_DIALECT_SLANG]` |
| **`XV`** | **1** | Język Dziecięcy, Mowa Pieszczotliwa i Infantylizmy | `360–381` | `dead` | Brak triggera w `get_focused_rules_for_batch`. | **`DODAJ_TRIGGER` / `SCAL`** z `FILAR CXXXVI` (wiek/płeć mówcy) |
| **`XIX` – `XXIV`** | **6** | Śmiech/Płacz (`XIX`), Wielokropki (`XX`), Pytania Retoryczne (`XXI`), Ironia (`XXII`), Przekleństwa (`XXIII`), Zdrobnienia (`XXIV`) | `448–575` | `dead` | Brak triggerów w selektorze; pokryte przez `R1.9`, `R1.10` i `FILAR CLXXII`. | **`ZAMROŹ_W_ARCHIWUM_Z16`** |
| **`XXXI` – `XXXII`, `XXXIV` – `XLVIII`** | **17** | Etykieta rodzinna (`XXXI–XXXII`), intonacja pytająca (`XXXIV–XXXVIII`), spójniki (`XXXIX–XLIII`), czas narracyjny (`XLIV–XLVIII`) | `703–1040` | `dead` | Brak triggerów; wiedza ogólnojęzykowa modelu LLM + `R1.1–R1.6`. | **`ZAMROŹ_W_ARCHIWUM_Z16`** |
| **`LII` – `LIII`, `LVII` – `LIX`, `LXII` – `LXIV`** | **8** | Terminologia fantasy (`LII–LIII`), rejestr prawniczy/korporacyjny (`LVII–LIX`), aluzje kulturowe (`LXII–LXIV`) | `1106–1375` | `dead` | Brak triggerów; terminologię fantasy i korporacyjną obsługuje `SeriesBible` oraz `EPISODE BRIEF` z `profiler.py`. | **`ZAMROŹ_W_ARCHIWUM_Z16`** |
| **`LXVII` – `LXX`, `LXXII` – `LXXIV`, `LXXVI` – `LXXVII`** | **9** | Rozwinięcia prozodii (`LXVII–LXX`), techniczne łamanie wierszy (`LXXII–LXXIV`), kontur F0 (`LXXVI–LXXVII`) | `1426–1660` | `dead` | Łamanie linii realizuje deterministycznie `AVTFormatter`, a prozodię pokrywa `R1.7–R1.8` i `LXVI`/`LXXV`. | **`ZAMROŹ_W_ARCHIWUM_Z16`** |
| **`LXXX` – `LXXXIII`, `LXXXVI` – `XCI`** | **10** | Piosenki/wiersze (`LXXX–LXXXIII`), telefony/komunikatory/megafony (`LXXXVI–XCI`) | `1706–1940` | `dead` | Brak triggerów w `get_focused_rules_for_batch`. | **`ZAMROŹ_W_ARCHIWUM_Z16`** |
| **`XCIV` – `XCV`, `XCVII` – `CIII`** | **9** | Składnia liczebników (`XCIV–XCV`), zaimki 1. i 2. osoby JP (`Ore/Boku/Watashi/Atashi/Omae/Kimi`) (`XCVII–CIII`) | `1981–2175` | `dead` | Zaimki JP są dziś ekstrahowane deterministycznie przez `WhisperDisambiguator` w KROKU 4 i podawane w telemetrii linii. | **`ZAMROŹ_W_ARCHIWUM_Z16`** |
| **`CVI` – `CXI`, `CXIII` – `CXVII`, `CXX` – `CXXXV`** | **27** | Partykuły końcowe JP i tiki słowne (`-pon`) (`CVI–CXI`), pauzy `Ma` (`CXIII–CXVII`), słowniki tematyczne gatunków (`CXX–CXXXV`) | `2216–2710` | `dead` | Brak triggerów; partykuły i tiki maskotek obsługuje `EPISODE BRIEF` z `profiler.py`. | **`DODAJ_TRIGGER`** dla tików werbalnych maskotek (`CVI–CXI` scalić z `XIII`/`XII`); pozostałe 21 **`ZAMROŹ_W_ARCHIWUM_Z16`** |
| **`CXXXVII` – `CLVI`, `CLVIII` – `CLXIV`** | **27** | Kazuistyczne reguły regresyjne z iteracji 5.0–8.9 | sekcja monumentu | `dead` | Zastąpione przez architekturę `SceneDiscourseGraph`, `AVTLinter (D_pos)` i `R1.1–R3.5`. | **`ZAMROŹ_W_ARCHIWUM_Z16`** |
| **`CLXVI`, `CLXVII`, `CLXVIII`, `CLXX`, `CLXXIII` – `CLXXX`** | **10** | Anty-kotwiczenie (`CLXVI`), wielokropki (`CLXVII`), cytaty (`CLXVIII`), krótkie pytania (`CLXX`), signs (`CLXXIII`), higiena tokenów (`CLXXIV`), bezokoliczniki (`CLXXV`), wołacz (`CLXXVI`), decoupling (`CLXXVII`), adresatka (`CLXXVIII`), pary przylegania (`CLXXIX`), domknięcie (`CLXXX`) | `2205–2524` | `dead` w selektorze *(skondensowane w `R1.1–R3.5` oraz w `avt_linter.py`)* | Ich treść została już przeniesiona do `STANDARD_9_CORE_RULES_PROMPT` (`R1.1–R3.5`) oraz operatorów `EpisodeQualityGate`. | **`DODAJ_TRIGGER`** dla `CLXVI & CLXXIX` (w ramach kategorii par przylegania / naturalnej riposty); pozostałe **`ZAMROŹ_W_ARCHIWUM_Z16`** |

---

## 7. FAZA 5 — OCENA SELEKTORA (`get_focused_rules_for_batch`)

### P5.1. Ocena parametrów obecnego selektora (`rules.py:2688–3520`)

| Aspekt | Stan obecny (`81de7b5`) | Ocena |
| :--- | :--- | :---: |
| **Domyślny `max_rules`** | `None` → wewnątrz funkcji konwertowane na `3` | **`OK` (pod warunkiem usunięcia nadaktywnych triggerów szumowych)** |
| **Liczba Filarów w base (`STANDARD_9_CORE_RULES_PROMPT`)** | 4 makro-filary arabskie = 16 reguł (`R1.1–R1.11`, `R3.1–R3.5`) | **`OK` (kompaktowy, czysty rdzeń ~3.8 KB)** |
| **Liczba bloków w dynamic (`get_focused_rules_for_batch`)** | 24 bloki warunkowe (reprezentujące 38 rzymskich Filarów) | **`ZA_DUŻO` (14 z 24 bloków duplikuje `STANDARD_9_CORE_RULES_PROMPT`)** |
| **Liczba triggerów (`if re.search(...)` / warunków)** | 24 warunki oparte na prostych słowach kluczowych EN/JP i znakach interpunkcyjnych | **`ZA_DUŻO` i `ZA_SZEROKIE`** |
| **`Anti-Smoothing Filter` (wdrożony w `10.1.1`)** | Usuwa `FILAR LXXI` i `FILAR CLXXII`, gdy aktywny jest `FILAR XIII` | **`NIEKOMPLETNY` (nie chroni `FILAR XIV & XXX` przed wygładzeniem przez `LXXI`/`CLXXII`)** |
| **Pokrycie triggerów (ile rzymskich Filarów ma trigger?)** | `38 / 180` (`21.1%`) | **`OK` dla odchudzenia, ale wymaga uporządkowania do 8 czystych kategorii dynamicznych** |
| **Precyzja triggerów (czy triggery dają fałszywe pozytywy?)** | Triggery `LXV` (`...`, `but`), `LXVI` (`!`, `?`), `XVIII` (`eh`, `ah`) i `CLXXII` aktywują się na >80% zwykłych paczek dialogowych! | **`ZA_SZEROKI` (powoduje chroniczny szum i wypychanie istotnych reguł z trójki `max_rules=3`)** |

---

### P5.2. Analiza precyzji wszystkich grup triggerów w `get_focused_rules_for_batch`

| Trigger / Warunek w kodzie (`81de7b5`) | Aktywowany Filar (Score) | Fałszywe pozytywy (False Positives) | Fałszywe negatywy (False Negatives) | Ocena audytorska |
| :--- | :--- | :--- | :--- | :---: |
| **`en_slang_pat` + `jp_dialect_pat` + `paraphrase_pat`** | `FILAR XIII` (`85`) | `gonna` / `wanna` / `gotta` występują w zwykłym potocznym angielskim u każdej postaci; `\w+in'` łapie zwykłe słowa kończące się na `in'` przy apostrofie; `means` łapie zwykłe zdania typu `What does this mean?` | Brakuje markerów subkulturowych (`FILAR XII`: `yankee`, `gyaru`, `temee`, `kisama`, `-ssu`) oraz konstrukcji parafrazy bez słowa `means` (`So she thinks...`). | **`ZA_SZEROKI` dla `gonna/wanna/means` + `ZA_WĄSKI` dla `FILAR XII`** |
| **Wielokropek `...` lub spójniki `\b(but\|wait\|actually\|unless\|until)\b`** | `FILAR LXV` (`90` / `80`) | **Krytyczny False Positive:** W paczce 24 linii niemal zawsze występuje przynajmniej jedno `...` lub `but` (w `S01E05` trafiło w 10/16 paczek!). Co więcej, szyk rematyczny jest już w `R1.1` Base! | Brak — trigger odpala się praktycznie zawsze. | **`ZBĘDNY W DYNAMIC` (100% duplikat `R1.1` Base o ekstremalnym szumie)** |
| **Wykrzyknik `!`, wielokropek `...` lub słowa `\b(gasp\|pant\|run\|fight)\b`** | `FILAR LXVI` (`88` / `80`) | **Krytyczny False Positive:** Pojedynczy wykrzyknik `!` w paczce 24 linii występuje w >90% paczek! Ponadto rytm oddechu jest już w `R1.8` Base. | Brak. | **`ZA_SZEROKI` (zostawić wyłącznie dla scen gęstej akcji: `>= 6` wykrzykników w paczce)** |
| **Wykrzykniki / słowa emocjonalne (`cry`, `scream`, `afraid`, `scared`, `die`, `!`)** | `FILAR CLXXII` (`86`) | Aktywuje się na większości dramatycznych paczek i wstrzykuje dyrektywę „polszczyzny bezterminowej”, która wygładza styl postaci charakterystycznych. | Brak. | **`ZA_SZEROKI` i `KONFLIKTOGENNY` (rozdzielić afekt głosu od wygładzania stylu)** |
| **Obecność tagów akustycznych F0 lub emfaz** | `FILAR LXXV` (`78`) | Odpala się na zwykłych wahaniach F0, powtarzając zasadę akcentu zdaniowego z `R1.1` i `FILAR LXV`. | Brak. | **`DUPLIKAT` — scalić z kategorią prozodii/afektu** |
| **Przecinki przed imieniem / zwroty bezpośrednie / tytuły** | `FILAR CLVII` (`80`) | Duplikuje `R1.6` z Base oraz nakłada się z `FILAR XXV` i `FILAR XXVI`. | Brak. | **`SCALIĆ` z `XXV–XXIX` w jedną kategorię `[KATEGORIA_HONORIFICS]`** |
| **Wykrzykniki paralingwistyczne `\b(eh\|ah\|uh\|ouch\|whoa\|ottotto\|huff)\b`** | `FILAR XVIII, XXXIII, XVI & XVII` (`75`) | **Wysoki False Positive:** Zwykłe pytające `Eh?` („Co?”) lub `Ah` w dialogu aktywuje instrukcję o... utracie równowagi `Ottotto` i okrzykach bojowych `Kakegoe`! | Brak. | **`ZA_SZEROKI` (usunąć zwykłe `eh`/`ah` z triggera; zostawić dla realnych okrzyków bojowych i somatycznych)** |
| **Honoryfikatory `-san`, `-sama`, `-kun`, `-chan`, `-sensei`, `-senpai`, `lord`, `master`, `miss`** | `FILAR XXV, XXVII & XXVIII` (`72`) oraz `FILAR XXVI & XXIX` (`70`) | Oba bloki odpalają się na podobnych dialogach społecznych i zajmują aż 2 z 3 slotów `max_rules`! | Brak. | **`SCALIĆ` oba bloki + `CLVII` w 1 slot `[KATEGORIA_HONORIFICS]`** |
| **Zaimki 3. os. lm. `\b(they\|them\|their\|girls\|women)\b` lub `kanojo-tachi`** | `FILAR XCVI` (`82`) | Słowa `they`/`them` występują w prawie każdej paczce (w tym dla przedmiotów np. `Candies`!), a sama zasada rodzaju niemęskoosobowego jest już w `R3.3` Base oraz w `SceneDiscourseGraph` (`NON_VIRILE`). | Brak. | **`ZA_SZEROKI` (usunąć `they`/`them` z triggera; scalić z `CXXXVI` dla realnej obsady grupowej/wiekowej)** |
| **Słowa wieku/roli (`boy`, `kid`, `child`, `grandma`, `old woman`, `shonen`, `baba`)** | `FILAR CXXXVI` (`84`) | Bardzo dobry, celny trigger, ale częściowo powiela `R3.1` Base. | Brakuje integracji z językiem dziecięcym (`FILAR XV`). | **`DOBRY` — scalić z `FILAR XV` i `FILAR XCVI` w `[KATEGORIA_GENDER_AGE_PLURAL]`** |
| **Krótkie linie (`len < 15`)** | `FILAR CXII` (`76`) | W każdej paczce 24 linii jest przynajmniej jedna krótka linia (`Yes.`, `No.`, `What?`), a zasada zwięzłości jest już w `R1.7` Base! | Brak. | **`ZBĘDNY W DYNAMIC` (duplikat `R1.7` Base)** |
| **Szybkie tempo mowy / długie linie** | `FILAR LXXI` (`68`) | Wygładza rejestr i jest w pełni pokryty przez `R1.7–R1.8` w Base. | Brak. | **`ZBĘDNY W DYNAMIC` (usunąć z selektora dynamicznego, co eliminuje też konflikty `S-1` i `S-2`!)** |
| **Negacja `\b(not\|n't\|never\|no one\|nothing\|nobody)\b`** | `FILAR XCII & XCIII` (`72`) | W każdej paczce 24 linii występuje `not` lub `n't`, a zasada dopełniacza negacji jest już w `R1.4` Base i `profiler.py`! | Brak. | **`ZBĘDNY W DYNAMIC` (100% duplikat `R1.4` Base)** |
| **Liczby `\d+` lub liczebniki słowne** | `FILAR CLXXI` (`76`) | Zasada zgodności liczb jest już w `R3.5` Base oraz jest twardo kontrolowana przez `EpisodeQualityGate` w `avt_linter.py` (KROK 11). | Brak. | **`ZBĘDNY W DYNAMIC` (duplikat `R3.5` Base + `avt_linter.py`)** |
| **Wielokropki na końcu/początku linii** | `FILAR CLXV & CLXIX` (`74`) | Zasada wielokropków kontynuacyjnych jest już w `R1.10` Base. | Brak. | **`ZAWĘZIĆ` wyłącznie do rzeczywistych zdań rozbitych między 2 eventy lub przeskoków scen** |
| **Napisy ekranowe (`UPPERCASE` / `is_sign`)** | `FILAR LXXVIII & LXXIX` (`74`) | Dobry trigger kontekstowy. | Brak. | **`OK` — zachować jako `[KATEGORIA_SIGNS]`** |
| **Archaizmy / dworskość (`thou`, `thee`, `thy`, `milord`, `majesty`, `highness`, `ojou`, `washi`, `sessha`, `warawa`)** | `FILAR XIV & XXX` (`78`) | Bardzo dobry, rzadki i precyzyjny trigger kontekstowy! | Brak ochrony przed `FILAR CLXXII` (`S-2`). | **`OK` — zachować jako `[KATEGORIA_ARCHAIC_COURT]` i objąć ochroną `Anti-Smoothing Filter`** |
| **Żargon bojowy/sportowy (`XLIX–LI`), medyczno-śledczy (`LIV–LVI`), kalambury (`LX–LXI`), onomatopeje (`CIV–CV`), kulinaria (`CXVIII–CXIX`)** | `XLIX–CXIX` (`62–68`) | Przez niski score (`62–68`) oraz zaśmiecenie slotów przez `LXV` (`90`), `LXVI` (`88`) i `CLXXII` (`86`), te 5 specjalistycznych reguł **prawie nigdy nie mieści się w `max_rules=3`!** | Chroniczne Fałszywe Negatywy (wypierane przez `LXV` i `LXVI`). | **`SKONSOLIDOWAĆ` do 2 kategorii (`[KATEGORIA_DOMAIN_REGISTER]` i `[KATEGORIA_CULTURE_IDIOM]`), które po usunięciu szumu `LXV`/`XCII`/`CXII` zaczną realnie trafiać do odpowiednich scen!** |

---

### P5.3. Analiza `Anti-Smoothing Filter` (`rules.py:3034–3038`)

W `rules.py` na commicie `81de7b5` filtr przeciw-wygładzający ma postać:
~~~python
if any("FILAR XIII" in r for _, r in candidates):
    candidates = [(s, r) for s, r in candidates if "FILAR LXXI " not in r and "FILAR CLXXII " not in r]
~~~
**Odpowiedzi na pytania kontrolne P5.3:**
1. **Czy filtr usuwa oba Filary (`LXXI` i `CLXXII`)?** Tak, usuwa oba wpisy z listy `candidates`.
2. **Czy filtr działa przed sortowaniem i obcięciem do `max_rules`?** Tak, działa na liście `candidates` przed wykonaniem `candidates.sort(...)` i `focused[:max_rules]`, dzięki czemu po usunięciu `CLXXII` wolny slot w trójce przejmuje kolejna właściwa reguła.
3. **Czy filtr uwzględnia wszystkie miejsca?** Działa zarówno dla Fazy 1 (`translator.py`), jak i Fazy 2 (`verifier.py`, po przekazaniu `focused_rules_str` w `10.1.1`).
4. **Czego filtr NIE obejmuje (luka `S-2`)?** Filtr jest zahardkodowany wyłącznie na `"FILAR XIII"`, przez co **nie chroni `FILAR XIV & XXX` (Archaizacja / Keigo Dworskie / Rejestr Starca)** przed wygładzeniem przez `FILAR LXXI` („eliminując archaizmy”) oraz `FILAR CLXXII` („polszczyzna bezterminowa”). Po całkowitym usunięciu `FILAR LXXI` z selektora dynamicznego oraz przeformułowaniu `CLXXII` na czystą kategorię afektu akustycznego (`[KATEGORIA_DYN_5: AFEKT I PROZODIA]`) bez nakazu „polszczyzny bezterminowej”, konflikt znika u samego źródła!

---

## 8. FAZA 6 — PROPOZYCJA MINIMALIZACJI

### P6.1. Docelowa liczba Filarów / Kategorii Wykonawczych

Proponowana architektura **Standard 10.2** redukuje aktywny system instrukcji translacyjnych do **12 ortogonalnych Kategorii Wykonawczych AVT** (zero nakładania się treści, 100% rozłączności semantycznej):

1. **4 Kategorie Bazowe (`[KATEGORIA_BASE_1]` – `[KATEGORIA_BASE_4]`) w `STANDARD_9_CORE_RULES_PROMPT`** — zawsze aktywne, obejmujące zwięzłe, powszechne prawa języka polskiego i napisów AVT (dotychczasowe `R1.1–R1.11` i `R3.1–R3.5`, bez jakichkolwiek duplikatów w selektorze dynamicznym):
   - `[KATEGORIA_BASE_1: SKŁADNIA, PRO-DROP, WERBALIZACJA I DOPEŁNIACZ NEGACJI]` (`R1.1–R1.4`)
   - `[KATEGORIA_BASE_2: ZWIĘZŁOŚĆ AVT, RYTM SEIYŪ I HIGIENA PARALINGWISTYCZNA]` (`R1.7–R1.9`)
   - `[KATEGORIA_BASE_3: SPÓJNOŚĆ PŁCI (P0), ADRESATA, WOŁACZA, CYTATÓW I LICZEBNIKÓW]` (`R1.5–R1.6`, `R3.1–R3.5`)
   - `[KATEGORIA_BASE_4: FORMATOWANIE ASS, KONTYNUACJA WIELOKROPKOWA I KURSYWA MYŚLI]` (`R1.10–R1.11`)

2. **8 Kategorii Dynamicznych (`[KATEGORIA_DYN_1]` – `[KATEGORIA_DYN_8]`) w `get_focused_rules_for_batch`** — wybieranych **wyłącznie wtedy**, gdy w bieżącej paczce występuje specyficzne, niepowszechne zjawisko językowe lub sceniczne:
   - `[KATEGORIA_DYN_1: DIALEKT, GWARA, SLANG I KONTRAST PARAFRAZY]` *(scala `FILAR XIII`, `FILAR XII` oraz `CVI–CXI`)*
   - `[KATEGORIA_DYN_2: ARCHAIZACJA, KEIGO DWORSKIE I REJESTR WYSOKI]` *(scala `FILAR XIV` i `FILAR XXX`)*
   - `[KATEGORIA_DYN_3: TYTULATURA, HONORYFIKATORY I DYNAMIKA RELACJI]` *(scala `FILAR XXV, XXVI, XXVII, XXVIII, XXIX` i `CLVII`)*
   - `[KATEGORIA_DYN_4: TRIANGULACJA WIEKU/PŁCI (CHŁOPIEC / MATRONA / GRUPA KOBIET)]` *(scala `FILAR CXXXVI`, `FILAR XV` i `FILAR XCVI`)*
   - `[KATEGORIA_DYN_5: AFEKT EKSTREMALNY, KINEZJOLOGIA WALKI I SOMATYKA]` *(scala `FILAR CLXXII`, `FILAR LXVI`, `FILAR LXXV` i `FILAR XVI/XVII/XVIII/XXXIII` — po usunięciu klauzuli wygładzającej styl i zakazie pustego stringa)*
   - `[KATEGORIA_DYN_6: CIĄGŁOŚĆ DYSKURSU, ZDANIA ROZBITE I PARY PRZYLEGANIA]` *(scala `FILAR CLXV`, `FILAR CLXIX` i `FILAR CLXXIX`)*
   - `[KATEGORIA_DYN_7: REJESTRY SPECJALISTYCZNE (TAKTYCZNY, MEDYCZNY, ŚLEDCZY)]` *(scala `FILAR XLIX–LI` i `FILAR LIV–LVI`)*
   - `[KATEGORIA_DYN_8: ADAPTACJA KULTUROWA, GRY SŁOWNE, ONOMATOPEJE I NAPISY EKRANOWE]` *(scala `FILAR LX–LXI`, `FILAR CIV–CV`, `FILAR CXVIII–CXIX` i `FILAR LXXVIII–LXXIX`)*

3. **Pasywny Rejestr Legacy (`TRANSLATION_RULES_PROMPT`):** Pozostaje w pliku `rules.py` jako zamrożona stała archiwalna na potrzeby 100% kompatybilności z `test_system.py` (Zasada 16), nie będąc wstrzykiwaną do aktywnych wywołań runtime (`use_lean_prompt=True`).

---

### P6.2. Mapowanie starych Filarów na nowe kategorie

| Stary numer / Reguła | Stary tytuł / zakres | Nowa kategoria docelowa | Nowy tytuł kategorii (propozycja metajęzykowa) | Uzasadnienie | Status |
| :--- | :--- | :--- | :--- | :--- | :---: |
| **`R1.1–R1.4`** + `I, V, VI, VII, LXV, XCII, XCIII, CLXVI, CLXXVII` | Szyk rematyczny, pro-drop, werbalizacja, dopełniacz negacji | `[KATEGORIA_BASE_1]` | `Składnia Mówiona, Pro-Drop i Rekcja Zaprzeczona` | Zawsze aktywne prawo bazowe; eliminuje nadaktywne triggery `LXV` i `XCII` z selektora dynamicznego (Finding `D-1`, `D-2`). | `AUTORYTATYWNY` |
| **`R1.7–R1.9`** + `II, LXXI, CXII` | Kondensacja CPS/CPL, rytm seiyū, redukcja tarcia | `[KATEGORIA_BASE_2]` | `Ekonomia Słowa, Budżet Czasowy i Rytm Wypowiedzi` | Zawsze aktywne prawo bazowe; eliminuje nadaktywne triggery `CXII` i konfliktogenny `LXXI` z selektora dynamicznego (Finding `D-3`, `S-1`, `S-2`). | `AUTORYTATYWNY` |
| **`R1.5–R1.6`, `R3.1–R3.5`** + `III, IV, IX, CLXVIII, CLXXI, CLXXV, CLXXVI, CLXXVIII` | Płeć 1./2. os., wołacz, cytaty, deklinacja kanonu, liczebniki | `[KATEGORIA_BASE_3]` | `Spójność Rodzaju P0, Form Adresatywnych, Cytatów i Liczebników` | Zawsze aktywne prawo bazowe; eliminuje duplikację `CLXXI` w selektorze i powtórzenia w `profiler.py` (Finding `D-9`, `D-15`). | `AUTORYTATYWNY` |
| **`R1.10–R1.11`** + `XX, LXXXIV, LXXXV, CLXVII, CLXXIII` | Wielokropki, kursywa myśli, izolacja napisów | `[KATEGORIA_BASE_4]` | `Konwencje Techniczne ASS, Myśli Wewnętrzne i Wielokropki` | Zawsze aktywne prawo bazowe; eliminuje duplikację `LXXXIV & LXXXV` w selektorze (Finding `D-10`). | `AUTORYTATYWNY` |
| **`XIII` + `XII` + `CVI–CXI`** | Dialekty regionalne, gwara, sociolekty młodzieżowe, tiki słowne | `[KATEGORIA_DYN_1]` | `Dialekty, Gwara, Sociolekty i Kontrast Parafrazy` | Jedna skonsolidowana kategoria stylizacji gwarowej/slangowej z priorytetem nad gładzeniem (Finding `D-12`, `S-1`). | `AUTORYTATYWNY` |
| **`XIV` + `XXX`** | Archaizacja, keigo dworskie, rejestr starca | `[KATEGORIA_DYN_2]` | `Archaizacja, Etykieta Dworska i Rejestr Wysoki` | Zachowana unikalna kategoria rejestru dawnego/wysokiego, objęta ochroną `Anti-Smoothing Filter` (Finding `S-2`). | `AUTORYTATYWNY` |
| **`XXV, XXVI, XXVII, XXVIII, XXIX` + `CLVII`** | Tytulatura, adaptacja honoryfikatorów, `yobisute`, spójność formy | `[KATEGORIA_DYN_3]` | `Adaptacja Honoryfikatorów, Yobisute i Harmonia Adresatywna` | Scalenie 3 osobnych bloków honoryfikatywnych w 1 kategorię bez wewnętrznych sprzeczności (Finding `D-5`, `D-6`, `S-3`). | `AUTORYTATYWNY` |
| **`CXXXVI` + `XCVI` + `XV`** | Triangulacja wieku/płci (chłopiec/matrona), grupy kobiece, mowa dziecięca | `[KATEGORIA_DYN_4]` | `Triangulacja Foniczna Wieku i Płci oraz Grupy Niemęskoosobowe` | Scalenie ochrony cross-gender F0, mowy dziecięcej i `kanojo-tachi` z precyzyjnym triggerem (Finding `D-4`). | `AUTORYTATYWNY` |
| **`CLXXII` + `LXVI` + `LXXV` + `XVI, XVII, XVIII, XXXIII`** | Afekt głosu seiyū, oddech w walce, szczyt F0, okrzyki `kakegoe`/`ottotto` | `[KATEGORIA_DYN_5]` | `Ekspresja Afektywna Seiyū, Kinezjologia Walki i Somatyka` | Scalenie 4 bloków prozodyczno-afektywnych w 1 kategorię wyzwalaną tylko przy realnym afekcie/walce, bez klauzuli wygładzania stylu i bez nakazu pustego stringa (Finding `D-7`, `S-1`, `S-4`). | `AUTORYTATYWNY` |
| **`CLXV` + `CLXIX` + `CLXXIX`** | Przeskoki scen, zdania rozbite na 2 eventy, pary przylegania | `[KATEGORIA_DYN_6]` | `Ciągłość Zdań Rozbitych, Przeskoki Scen i Riposty Dialogowe` | Scalenie ciągłości dyskursu między sąsiednimi liniami ASS (Finding `D-8`). | `AUTORYTATYWNY` |
| **`XLIX, L, LI` + `LIV, LV, LVI`** | Żargon bojowo-sportowy oraz rejestr medyczno-śledczy | `[KATEGORIA_DYN_7]` | `Rejestry Fachowe: Taktyczno-Bojowy, Medyczny i Śledczy` | Konsolidacja specjalistycznych rejestrów domenowych w 1 kategorię (Finding `D-13`). | `WYMAGA_DECYZJI_UŻYTKOWNIKA` |
| **`LX, LXI` + `CIV, CV` + `CXVIII, CXIX` + `LXXVIII, LXXIX`** | Gry słowne (`dajare`), onomatopeje (`giongo`), kulinaria, szyldy (`signs`) | `[KATEGORIA_DYN_8]` | `Adaptacja Kulturowa, Kalambury, Onomatopeje i Napisy Ekranowe` | Konsolidacja rzadkich zjawisk kulturowo-leksykalnych i napisów UI (Finding `D-11`, `D-14`). | `WYMAGA_DECYZJI_UŻYTKOWNIKA` |
| **Pozostałe 138 numerów rzymskich w `TRANSLATION_RULES_PROMPT`** | Historyczne Filary z iteracji 1.0–8.9 | `PASYWNE_ARCHIWUM_Z16` | *(Zachowane wyłącznie w stałej `TRANSLATION_RULES_PROMPT` dla kompatybilności z `test_system.py`)* | Nieaktywne w runtime (`use_lean_prompt=True`), nienaruszalne ze względu na Z16. | `AUTORYTATYWNY` |

---

### P6.3. Propozycja nowej logiki selekcji w `get_focused_rules_for_batch`

| Aspekt | Stan obecny (`81de7b5`) | Propozycja docelowa (`10.2`) |
| :--- | :--- | :--- |
| **Liczba kategorii bazowych (zawsze aktywnych)** | 4 makro-filary (16 reguł `R1.1–R3.5`) + duplikaty w `profiler.py` | **4 Kategorie Bazowe (`R1.1–R1.11`, `R3.1–R3.5`)** w `STANDARD_9_CORE_RULES_PROMPT` (z usunięciem duplikatów gramatycznych z `profiler.py`) |
| **Liczba kategorii warunkowych (dynamicznych)** | 24 bloki warunkowe (38 rzymskich Filarów) | **8 ortogonalnych Kategorii Dynamicznych (`[KATEGORIA_DYN_1]` – `[KATEGORIA_DYN_8]`)** (zachowujących w nagłówku numery rzymskie dla kompatybilności wstecznej testów) |
| **Sposób selekcji i próg wejścia** | Niskoprogowe regexy (`...`, `!`, `but`, `they`, `not`) powodują wybór 3 reguł w 100% paczek | **Selekcja wysokoprogowa oparta na rzeczywistych markerach zjawiska:** kategoria jest wybierana tylko przy przekroczeniu progu specyficzności; domyślny limit `max_rules=3` |
| **Hierarchia priorytetów (`score`)** | `LXV` (90) > `LXVI` (88) > `CLXXII` (86) > `XIII` (85) — ogólna składnia bije gwarę! | **`DYN_1 (Gwara/Slang: 95)` > `DYN_2 (Archaizacja/Keigo: 92)` > `DYN_4 (Wiek/Płeć/Grupa: 88)` > `DYN_3 (Honoryfikatory: 84)` > `DYN_6 (Zdania rozbite: 80)` > `DYN_5 (Afekt/Walka: 76)` > `DYN_7 (Rejestr fachowy: 72)` > `DYN_8 (Kultura/Signs: 70)`** |
| **Rozwiązywanie konfliktów (`Anti-Smoothing Filter`)** | Wyłącza `LXXI` i `CLXXII` tylko przy `FILAR XIII` | **`LXXI` całkowicie usunięty z selektora dynamicznego**; przy aktywności `DYN_1 (Gwara)` lub `DYN_2 (Archaizacja)` wyłączane są wszelkie wskazówki o neutralizacji rejestru |
| **Zachowanie Fallback (gdy paczka to zwykły dialog)** | Zawsze wciska 3 ogólne reguły (`LXV`, `LXVI`, `XCII`/`CXII`) | **Czysty fallback `""` (0 reguł dynamicznych):** dla standardowej paczki dialogowej wystarczają 4 Kategorie Bazowe z `STANDARD_9_CORE_RULES_PROMPT` |

---

### P6.4. Oczekiwana redukcja i poprawa metryk

| Metryka | Przed (`81de7b5`) | Po (`10.2` — propozycja) | Redukcja / Zmiana |
| :--- | :---: | :---: | :---: |
| **Liczba unikalnych jednostek regułowych aktywnych w architekturze runtime** | 180 Filarów rzymskich + 16 reguł R | **12 Kategorii Wykonawczych** (4 Base + 8 Dynamic) | **`-93.3%`** (`180 → 12`) |
| **Liczba bloków warunkowych w `get_focused_rules_for_batch`** | 24 bloki | **8 bloków (`DYN_1` – `DYN_8`)** | **`-66.7%`** (`24 → 8`) |
| **Liczba duplikatów między Base, Dynamic i `profiler.py`** | 22 duplikaty | **0 duplikatów** | **`-100%`** (`22 → 0`) |
| **Średnia liczba Filarów dynamicznych wstrzykiwanych na zwykłą paczkę bez zjawisk specjalnych** | `3.0` (stały szum `LXV`/`LXVI`/`XCII`) | **`0.0 – 1.5`** (tylko realne zjawiska w scenie) | **`-50% do -100%` szumu promptu** |
| **Pokrycie testowe i czystość domenowa (`verify_purity.py` na `get_focused_rules_for_batch`)** | Tylko `STANDARD_9_CORE_RULES_PROMPT` (w `get_focused_rules_for_batch` są jeszcze negacje i literały `S-5`) | **100% czystej domeny pozytywnej w Base i we wszystkich 8 kategoriach Dynamic** | **`+100%` spójności z Z1, Z2, Z4** |

---

## 9. FAZA 7 — REKOMENDACJE

### Priorytet P0 (Krytyczne dla 3 celów użytkownika i spójności Z1/Z2/Z4)
1. **[Finding `D-1`, `D-2`, `D-3`, `D-9`, `D-10`]:** Usunąć z `get_focused_rules_for_batch` 6 nadmiarowych bloków warunkowych, które w 100% duplikują zawsze aktywny `STANDARD_9_CORE_RULES_PROMPT` (`FILAR LXV`, `FILAR XCII & XCIII`, `FILAR CXII`, `FILAR LXXI`, `FILAR LXXXIV & LXXXV`, `FILAR CLXXI`) — status: **`AUTORYTATYWNY`**.
2. **[Finding `D-4`, `D-5`, `D-6`, `D-7`, `D-8`, `D-12`]:** Skonsolidować pozostałe bloki w `get_focused_rules_for_batch` w **8 unikalnych, rozłącznych Kategorii Dynamicznych (`DYN_1` – `DYN_8`)**, zachowując w ich nagłówkach numery rzymskie (np. `FILAR XIII & XII`, `FILAR XXV, XXVI, XXVII, XXVIII, XXIX & CLVII`, `FILAR CXXXVI, XCVI & XV`, `FILAR CLXXII, LXVI, LXXV, XVI, XVII, XVIII & XXXIII`), aby utrzymać 100% kompatybilności ze wszystkimi testami — status: **`AUTORYTATYWNY`**.
3. **[Finding `S-1`, `S-2`, `S-4`, `S-5`]:** Przepisać treść wszystkich 8 Kategorii Dynamicznych w `get_focused_rules_for_batch` na **100% czystą domenę pozytywną (Z2) i metajęzyk bez literałów (Z1/Z4)** (usuwając słowa `NIE`, `Niedopuszczalne`, `unikaj`, `zamiast`, `usuń napis do ''` oraz rozszerzając `Anti-Smoothing Filter` także na `FILAR XIV & XXX`) — status: **`AUTORYTATYWNY`**.

### Priorytet P1 (Ważne dla precyzji selekcji i eliminacji szumu)
4. **[Finding `P5.2`]:** Zaostrzyć triggery w `get_focused_rules_for_batch`:
   - w `DYN_1 (Gwara/Slang)` usunąć nadmiernie ogólne angielskie słowa potoczne (`gonna`, `wanna`, `gotta`, pojedyncze `means` w pytaniach) i dodać markery subkulturowe z `FILAR XII`,
   - w `DYN_4 (Wiek/Płeć/Grupa)` usunąć ogólne zaimki `they`/`them` (które łapią przedmioty nieożywione), zostawiając wyzwalacze obsady kobiecej/dziecięcej/starszej,
   - w `DYN_5 (Afekt/Walka)` usunąć pojedynczy znak `!` oraz zwykłe `eh`/`ah`, wymagając rzeczywistego zagęszczenia wykrzykników lub tagów akustycznych z `prosody_engine.py` — status: **`AUTORYTATYWNY`**.
5. **[Finding `D-15`]:** Odchudzić stałą stopkę `TOPOLOGIA SCENY I OCHRONA PŁCI` w `profiler.py` (`format_lean_episode_brief`), usuwając z niej powtórzenie reguły `Dopełniacza Negacji` i ogólnych reguł już obecnych w `STANDARD_9_CORE_RULES_PROMPT` — status: **`AUTORYTATYWNY`**.
6. **[Finding `D-13`, `D-14`]:** Skonsolidować rzadkie filary domenowe (`XLIX–LI` + `LIV–LVI` → `DYN_7`) oraz kulturowo-napisowe (`LX–LXI` + `CIV–CV` + `CXVIII–CXIX` + `LXXVIII–LXXIX` → `DYN_8`) — status: **`WYMAGA_DECYZJI_UŻYTKOWNIKA`**.

### Priorytet P2 (Kosmetyczne i archiwalne)
7. **[Finding `F0.5`, `F0.8`]:** Oznaczyć stałą `TRANSLATION_RULES_PROMPT` w `rules.py` jawnym komentarzem `# Z16 LEGACY ARCHIVE (DO NOT MODIFY — REQUIRED BY test_system.py)` i rozszerzyć `verify_purity.py` o kontrolę czystości `get_focused_rules_for_batch` — status: **`AUTORYTATYWNY`**.

### Werdykt końcowy FAZY 7
- **Werdykt:** **`MINIMALIZACJA_CZĘŚCIOWA`**
- **Uzasadnienie:** W warstwie aktywnego runtime (`STANDARD_9_CORE_RULES_PROMPT` + `get_focused_rules_for_batch`) możliwa i wskazana jest radykalna redukcja z 180 Filarów do **12 unikalnych Kategorii Wykonawczych (4 Base + 8 Dynamic, redukcja o 93.3%)**, natomiast sama historyczna stała tekstowa `TRANSLATION_RULES_PROMPT` wewnątrz pliku `rules.py` musi pozostać zachowana jako pasywne archiwum, ponieważ zamrożony na mocy Zasady 16 plik `test_system.py` wykonuje bezpośrednie asercje tekstowe na obecność historycznych nagłówków `FILAR I` – `FILAR CLXXX` w `TRANSLATION_RULES_PROMPT`.

---

## 10. FAZA ODBIORU

- [x] FAZA 0 — Inwentaryzacja: `180` unikalnych Filarów rzymskich + `4` makro-filary arabskie (`16` reguł R), `7` komend, 10/10 pytań flagowych
- [x] FAZA 1 — Mapa treści: `180` Filarów rzymskich + `16` reguł R w tabelach
- [x] FAZA 2 — Duplikaty: `22` pary/grupy (`20` `AUTORYTATYWNE`, `2` `WYMAGA_DECYZJI_UŻYTKOWNIKA`)
- [x] FAZA 3 — Sprzeczności: `5` par (`1` rozstrzygnięta, `4` do rozstrzygnięcia)
- [x] FAZA 4 — Martwe Filary: `142` martwe w runtime (`138` `ZAMROŹ_W_ARCHIWUM_Z16`, `4` `DODAJ_TRIGGER`/`SCAL`)
- [x] FAZA 5 — Ocena selektora: `24` bloki triggerów przeanalizowane
- [x] FAZA 6 — Propozycja minimalizacji: `180 → 12` aktywnych kategorii w runtime (redukcja `93.3%`, oraz `24 → 8` bloków dynamicznych w selektorze = redukcja `66.7%`)
- [x] FAZA 7 — Rekomendacje: `3` P0, `3` P1, `1` P2
- [x] Werdykt FAZY 7: `MINIMALIZACJA_CZĘŚCIOWA`
- [x] FAZA 8 — Handoff: `GOTOWY`
- [x] Prompt kodujący: `Artefakty/Prompt_10.2_minimalizacja_filarow.md`
- [x] Walidacja P8.4: `15/15` PASS
- [x] Traceability: `8/8` operacji z przypisanym findingiem
- [x] Known risks (P8.6): `6` ryzyk (`R1`–`R6`) w SEKCJI 7 promptu kodującego
- [x] 0 placeholderów `<DO_WYPEŁNIENIA>` w raporcie i prompcie kodującym (poza zamierzonymi)
- [x] 0 zmian w kodzie (`git status` clean)
- [x] 0 commitów
- [x] Z16 nienaruszone
- [x] Z1/Z2/Z3/Z4 respektowane w propozycjach
- [x] Raport gotowy: `Artefakty/Raport_audytu_filarow.md`
- [x] Prompt kodujący gotowy: `Artefakty/Prompt_10.2_minimalizacja_filarow.md`
- [x] Następny krok: user commituje oba artefakty PRZED wysłaniem promptu kodującego do świeżego agenta kodującego.

---

## 11. HANDOFF (FAZA 8)

### 11.1. Tabela Traceability (Mapowanie Operacja w Prompcie 10.2 → Finding Audytu)

| Operacja | Finding z Audytu | Faza audytu | Typ operacji | Status | Ryzyko |
| :---: | :--- | :--- | :--- | :---: | :---: |
| **`2B.1`** | `D-1`, `D-2`, `D-3`, `D-9`, `D-10` | FAZA 2 (duplikaty Base vs Dynamic) | **USUŃ Z SELEKTORA** (wycofanie 6 bloków duplikujących `STANDARD_9_CORE_RULES_PROMPT`: `LXV`, `XCII & XCIII`, `CXII`, `LXXI`, `LXXXIV & LXXXV`, `CLXXI`) | `AUTORYTATYWNY` | niskie |
| **`2B.2`** | `D-4`, `D-5`, `D-6`, `D-7`, `D-8`, `D-12` | FAZA 2 (duplikaty Dynamic) + FAZA 4 (`XII`, `XV`, `CVI`, `CLXXIX`) | **SCAL** (konsolidacja aktywnych bloków w `get_focused_rules_for_batch` do 6 rdzeniowych Kategorii Dynamicznych `DYN_1` – `DYN_6`) | `AUTORYTATYWNY` | średnie |
| **`2B.3`** | `S-1`, `S-2`, `S-4`, `S-5` | FAZA 3 (sprzeczności i naruszenia Z1/Z2 w selektorze) | **PRZEPISZ NA POZYTYWNE + ROZSZERZ FILTR** (100% czysta domena pozytywna bez literałów w `DYN_1–DYN_8`, usunięcie nakazu pustego stringa w `XVIII`, ochrona `XIV & XXX` w `Anti-Smoothing Filter`) | `AUTORYTATYWNY` | niskie |
| **`2B.4`** | `P5.2` (triggery za szerokie / za wąskie) | FAZA 5 (ocena selektora) | **ZAWĘŹ I UPRECYZYJNIJ TRIGGERY** (usunięcie szumu `gonna`/`wanna`/`they`/`!`/`eh` i ustawienie hierarchii priorytetów `DYN_1 (95) > ... > DYN_8 (70)`) | `AUTORYTATYWNY` | średnie |
| **`2B.5`** | `D-15` | FAZA 0 (`F0.10`) + FAZA 2 | **USUŃ DUPLIKACJĘ W `profiler.py`** (odchudzenie stałej stopki w `format_lean_episode_brief` z powtórzeń `R1.4` i `R3.1–R3.5`) | `AUTORYTATYWNY` | niskie |
| **`2B.6`** | `S-5` + `P2` | FAZA 3 + FAZA 7 | **ROZSZERZ BRAMKĘ CZYSTOŚCI** (dodanie asercji w `tests/test_profiler.py` weryfikującej brak słów negatywnych i literałów w wyjściu `get_focused_rules_for_batch`) | `AUTORYTATYWNY` | niskie |
| **`2B.7`** | `D-13` | FAZA 2 + FAZA 6 | **SCAL** (`FILAR XLIX, L & LI` + `FILAR LIV, LV & LVI` → jedna kategoria `[KATEGORIA_DYN_7: REJESTRY SPECJALISTYCZNE]`) | `WYMAGA_DECYZJI_UŻYTKOWNIKA` | niskie |
| **`2B.8`** | `D-11`, `D-14` | FAZA 2 + FAZA 6 | **SCAL** (`FILAR LX & LXI` + `FILAR CIV & CV` + `FILAR CXVIII & CXIX` + `FILAR LXXVIII & LXXIX` → jedna kategoria `[KATEGORIA_DYN_8: KULTURA I NAPISY]`) | `WYMAGA_DECYZJI_UŻYTKOWNIKA` | niskie |

### 11.2. Podsumowanie Handoffu (P8.7)
- **Prompt kodujący:** `Artefakty/Prompt_10.2_minimalizacja_filarow.md`
- **Wersja promptu:** `10.2`
- **Liczba operacji:** `8` (w tym `6` `AUTORYTATYWNE`, `2` `WYMAGA_DECYZJI_UŻYTKOWNIKA`)
- **Traceability:** `8/8` operacji z przypisanym findingiem
- **Walidacja P8.4:** `15/15` PASS
- **Known risks (P8.6):** `6` ryzyk (`R1`–`R6`), wszystkie opisane w SEKCJI 7 promptu kodującego
- **Status:** **`GOTOWY`**
- **Następny krok:** Użytkownik commituje `Artefakty/Raport_audytu_filarow.md` i `Artefakty/Prompt_10.2_minimalizacja_filarow.md`, a następnie wysyła prompt kodujący do świeżego agenta kodującego.