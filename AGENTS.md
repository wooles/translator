# 🏛️ ZASADY DZIAŁANIA ASYSTENTA (WORKSPACE RULES — TRANSLATOR)

Ten dokument definiuje nienaruszalne, trwałe reguły postępowania asystenta AI w repozytorium translator. Został wdrożony jako permanentny bezpiecznik architektoniczny i jest automatycznie ładowany do kontekstu na każdym kroku pracy.

---

## 🎯 0. NADRZĘDNA ŻELAZNA ZASADA: UWAGI JAKO DROGOWSKAZ, AWARIA CAŁEGO TŁUMACZA, ELIMINACJA CAŁEJ DZIEDZINY NA KAŻDEJ WARSTWIE I MINIMALIZM MODELI GEMINI (SUPREME BEACON & HOLISTIC PIPELINE MANDATE)

1. **Wszystkie uwagi użytkownika jako drogowskaz (User Feedback as Directional Beacon):**
   - Wszystkie uwagi, pytania i przykłady błędów podawane przez użytkownika mają być bezwzględnie traktowane **wyłącznie jako drogowskaz**, a nie jako izolowane zgłoszenie jednostkowe.
   - Asystent ma kategoryczny zakaz skupiania się wyłącznie na dosłownym brzmieniu uwagi (np. na pojedynczym słowie, frazie czy konkretnej kwestii dialogowej). Uwaga użytkownika wyznacza wektor poszukiwań i nakłada obowiązek całościowej diagnozy.
2. **Analiza źródła problemu jako błąd w działaniu CAŁEGO tłumacza (Holistic Systemic Failure Analysis):**
   - Każdy zaistniały problem musi być analizowany u podstaw jako **błąd w działaniu całego tłumacza** – weryfikując cały łańcuch przepływu informacji (odczyt metadanych, pre-pass profilera, pamięć międzyodcinkową, prompt Fazy 1 i Fazy 2, arbitraż wielomodalny, linter oraz montaż końcowy .ass).
   - Asystent bada fundamentalne mechanizmy potoku: dlaczego system dopuścił do skażenia danych, gdzie nastąpiło zatrucie promptu lub przeoczenie sygnału z audio/obrazu i dlaczego mechanizmy kontrolne nie zneutralizowały błędu wcześniej.
3. **Eliminacja każdego błędu jako CAŁA DZIEDZINA JĘZYKOWA na KAŻDEJ WARSTWIE tłumaczenia (Full Linguistic Domain Elimination across All 5 Layers):**
   - Każdy błąd musi zostać zdefiniowany i wyeliminowany jako **cała dziedzina językowa** (kompletna taksonomia pokrewnych pułapek, relacji semantycznych, pragmatycznych, morfologicznych i syntaktycznych), a nie pojedynczy przypadek.
   - Eliminacja problemu musi nastąpić symetrycznie na **każdej warstwie tłumaczenia** zgodnie z Protokołem 5 Warstw (Warstwa 1: Pre-pass Profilera, Warstwa 2: Baza Wiedzy i Pamięć Serialu, Warstwa 3: Kanon i Prompty Fazy 2, Warstwa 4: EpisodeQualityGate lintera offline 0.00 PLN, Warstwa 5: Testy Regresyjne).
4. **Maksymalne odciążenie modeli Gemini od niepotrzebnych informacji (LLM Unburdening & Context Minimalism):**
   - **Modele Gemini mają pozostać w jak najmniejszym stopniu obciążone niepotrzebnymi informacjami.**
   - Obowiązuje kategoryczny zakaz bezrefleksyjnego mnożenia kolejnych mikro-nakazów i mikro-zakazów w promptach, które paraliżują naturalność dialogu i wywołują efekt „różowego słonia”.
   - Okno kontekstu i uwaga modeli Gemini mają być chronione i rezerwowane wyłącznie na autentyczną kreację dialogu filmowego, wielomodalną triangulację aktorską (głos seiyū, ekspresję, obraz) oraz czyste, pozytywne wektory rzemiosła AVT.
   - Wszelka twarda kontrola leksykalna, gramatyczna, słownikowa i strukturalna ma być bezwzględnie przenoszona do deterministycznych silników offline (0.00 PLN).
5. **Obowiązkowy protokół zgłaszania konfliktów architektonicznych:**
   - Jeśli jakiekolwiek proponowane rozwiązanie inżynierskie mogłoby wpłynąć pozytywnie na jakość tłumaczenia lub wydajność potoku, ale konfliktuje z istniejącymi nadrzędnymi wytycznymi, asystent ma bezwzględny obowiązek jawnie zgłosić ten konflikt użytkownikowi przed podjęciem decyzji.
   - Ostateczną decyzję o autoryzacji wyjątku lub rewizji reguły podejmuje wyłącznie użytkownik.

---

## 🚫 1. KATEGORYCZNY ZAKAZ DORAŹNEGO ŁATANIA (ANTI-PATCHING MANDATE)

1. **Defekt tłumaczenia to zawsze awaria potoku:**
   Gdy użytkownik zgłasza błąd w napisach (np. zła płeć, hybryda rejestru, błąd tytulatury, nienaturalna kalka), asystent ma **bezwzględny zakaz** ograniczania się do poprawienia linijki w pliku .ass lub dopisania pojedynczego regexa w linterze.
2. **Kolejność działań:**
   Poprawienie pliku wynikowego .ass jest dopuszczalne wyłącznie jako **ostatni krok**, po usunięciu źródła błędu w całym potoku.

---

## 🌐 2. ZASADA CAŁOŚCIOWEGO UOGÓLNIANIA I ELIMINACJI CAŁEJ DZIEDZINY PROBLEMU (HOLISTIC DOMAIN GENERALIZATION MANDATE)

1. **Zakaz doraźnego rozwiązywania pojedynczego zgłoszenia:**
   Gdy użytkownik zgłasza błąd (np. konkretne słowo, pojedynczą kwestię, niefortunną kalkę po pauzie), asystent ma **kategoryczny zakaz** ograniczania swojej propozycji i naprawy wyłącznie do tego izolowanego przypadku.
2. **Analiza od podstaw (First Principles):**
   Każde zgłoszenie błędu nakłada na asystenta obowiązek zbadania problemu u samych podstaw teoretycznych, dramaturgicznych, montażowych i językowych.
3. **Eliminacja całej dziedziny podobnych problemów:**
   Asystent musi:
   - Zidentyfikować fundamentalną klasę zjawiska (np. dyskontinuitet czasowy $\Delta t \ge 5–10$s, asymetria epistemiczna, zmiana audytorium z publicznego na prywatne, elipsa szumu motorycznego),
   - Opracować kompletną taksonomię pokrewnych pułapek (np. opóźnione potaknięcie, wyciek spójników, dryf zaimkowy, bezwładność emocjonalna, fałszywe pary przylegania),
   - Zaprojektować i wdrożyć zabezpieczenia neutralizujące **całą dziedzinę pokrewnych defektów** w potoku, a nie tylko zgłoszony egzemplarz.

---

## ⚖️ 3. ZASADA PRECYZYJNEJ GRANICY MIĘDZY SILNIKIEM OFFLINE A MODELAMI GEMINI (OFFLINE VS LLM BOUNDARY MANDATE)

1. **Precyzyjna granica odpowiedzialności:**
   Proponując poprawki, asystent ma bezwzględny obowiązek zachować precyzyjną granicę między tym, co wolno przenieść do deterministycznych silników offline, a tym, co musi pozostać w modelach Gemini.
2. **Co WOLNO i NALEŻY przenieść do silników offline (0.00 PLN):**
   - Struktury w 100% syntaktycznie i morfologicznie zamknięte, nieodmienne i bezkontekstowe.
   - Fonetyczne i dystrybucyjne warianty przyimkowo-zaimkowe PWN (*dla mnie*, *ode mnie*, *ze mną*, *przede mną*, *w nim*).
   - Zamknięte, bezkontekstowe idiomy rejestrowe i potocyzmy (*w każdym razie*, *dla rozrywki*, *doskonale*, *między nami*, *w mgnieniu oka*, *to jakieś kpiny*, *nic mnie to nie obchodzi*).
   - Sanację pleonazmów mechanicznych, formatowanie znaczników czasowych, naprawę inwersji i tagów fansuberskich.
3. **Czego KATEGORYCZNIE NIE WOLNO przenosić do bezrefleksyjnych podmian tekstowych offline:**
   - Kategoryczny zakaz mechanicznego podmieniania słów i pojęć odmiennych przez przypadki, rodzaje i liczby (np. terminy kanoniczne, imiona, tytulatura, relacje, nazwy własne).
   - Mechaniczna podmiana tekstowa terminów odmiennych wywołuje „mianownizację” (nominative freezing – zamrażanie form zależnych w mianowniku, np. *z Aurą Gilotyną* $\to$ *z Aura Gilotyna*), łamie związki zgody z przymiotnikami (*ten potężny zaklęcie*), narusza rekcję czasowników i przyimków oraz rozsadza limity CPS.
   - Wszelkie elementy wymagające kompetencji morfologicznej, deklinacji (7 przypadków języka polskiego), wyczucia pragmatyki, intonacji aktorskiej i subtekstu seiyū **muszą bezwzględnie pozostać w modelach Gemini** (wspierane kontekstem i kanonem, a nie mechanicznym string-replacerem).

---

## 📝 4. OBOWIĄZKOWY PROTOKÓŁ PLANOWANIA I AKCEPTACJI PRZED EDYCJĄ KODU (PLANNING & USER APPROVAL GATE)

1. **Bezwzględna kolejność: Najpierw pełna diagnoza źródłowa i mapa rodziny problemu, dopiero potem plan:**
   Asystent ma kategoryczny zakaz przedstawiania planu naprawczego przed kompletnym ustaleniem przyczyny źródłowej awarii potoku oraz zmapowaniem pełnej rodziny analogicznych problemów (zgodnie z Zasadą 12).
2. **Zakaz samowolnych modyfikacji kodu:**
   Przed dokonaniem jakiejkolwiek zmiany w plikach źródłowych (.py, konfiguracjach) asystent ma bezwzględny obowiązek przygotować całościowy plan naprawczy w `implementation_plan.md` (z metadanymi `RequestFeedback: true`), eliminujący całe zbiory błędów wynikające z ustalonego źródła.
3. **Czekanie na wyraźną zgodę:**
   Asystent zatrzymuje się, przedstawia plan i oczekuje na wyraźną akceptację użytkownika przed przystąpieniem do edycji kodu.

---

## 📖 5. ZASADA ZERO ZAŚMIECANIA NIEPRAWDZIWYMI INFORMACJAMI I NADRZĘDNOŚCI KANONU MANGOWEGO (MANGA CANON SUPREME GROUND-TRUTH & ZERO-POLLUTION MANDATE)

1. **Kanon mangowy jako nadrzędne źródło wiedzy w tłumaczeniu:**
   Oficjalny, licencjonowany polski kanon mangowy (`manga_canon.py`, polskie wydania tomikowe) jest nadrzędnym, absolutnym źródłem prawdy dla całego tłumaczenia. Ma bezwzględny priorytet nad domysłami modelu, pivotem angielskim czy fanowskimi nazewnictwami.
2. **Permanentny rygor i zakaz zmyślania („z pamięci” modelu):**
   Asystent ma bezwzględny obowiązek nieustannego pilnowania czystości kanonu. Obowiązuje kategoryczny zakaz wprowadzania do dokumentacji (README.md, opisy, tabele porównawcze), promptów oraz bazy wiedzy jakichkolwiek „przykładowych” lub „kanonicznych” terminów, nazwisk tłumaczy, tytułów czy przydomków na podstawie wewnętrznych wag LLM.
3. **Obowiązek weryfikacji w bazie kodu (`manga_canon.py`):**
   Wszelkie przykłady oficjalnego kanonu podawane w dokumentacji MUSZĄ być zmapowane 1:1 z istniejącymi, zweryfikowanymi wpisami w `manga_canon.py` lub potwierdzone w stopce redakcyjnej licencjonowanego polskiego wydawnictwa papierowego.
4. **Automatyczny audyt dokumentacji (CI Gate):**
   Każda zmiana w pliku README.md podlega automatycznemu testowi weryfikacyjnemu w `test_system.py` (Asercja 7), który weryfikuje spójność terminologiczną i uniemożliwia zatwierdzenie niesprawdzonych treści.

---

## 🛡️ 6. OBOWIĄZKOWY PROTOKÓŁ 5 WARSTW (5-LAYER ROOT CAUSE PROTOCOL)

Każde zgłoszenie błędu przez użytkownika nakłada na asystenta obowiązek przeprowadzenia audytu i wdrożenia zabezpieczeń w **5 warstwach architektury**:

| Warstwa | Komponent | Zadanie i odpowiedzialność asystenta |
| :--- | :--- | :--- |
| **Warstwa 1** | profiler.py (Pre-pass) | Zidentyfikować, dlaczego model na wejściu błędnie zinterpretował postać, scenę lub relację. Dodać twardy bezpiecznik w promptcie Profilera (np. pułapka ról, pułapka imion). |
| **Warstwa 2** | series_memory.py (Baza Wiedzy) | Zbadać, dlaczego Pamięć Serialu zaakceptowała skażony wpis. Wdrożyć symetryczną ochronę przed nadpisaniem (np. has_confirmed_female / has_confirmed_male), rozszerzyć słownik ról. |
| **Warstwa 3** | rules.py (Kanon & Prompty) | Dodać/rozszerzyć właściwy Filar AVT oraz zaktualizować dynamiczny dyspozytor uwagi (focused_pillars), zakazując tego błędu bezpośrednio w instrukcjach dla modeli. |
| **Warstwa 4** | avt_linter.py (EpisodeQualityGate) | Wdrożyć deterministyczny bezpiecznik (0.00 PLN) działający na pełnej osi czasu, który wyłapie i zneutralizuje błąd, nawet jeśli oba modele AI kompletnie zawiodą. |
| **Warstwa 5** | test_system.py (Test Regresyjny) | Napisać dedykowaną asercję w teście integracyjnym odwzorowującą ten konkretny błąd, aby żaden przyszły commit nie mógł go przywrócić. |

---

## 📋 7. WYMÓG TABELI DOWODOWEJ W ODPOWIEDZI

W odpowiedzi na jakiekolwiek zgłoszenie usterki translatorskiej, asystent **musi** przedstawić tabelę dowodową wskazującą:
1. Co konkretnie zmieniono w Warstwie 1 (profiler.py),
2. Co konkretnie zmieniono w Warstwie 2 (series_memory.py),
3. Co konkretnie zmieniono w Warstwie 3 (rules.py),
4. Co konkretnie zmieniono w Warstwie 4 (avt_linter.py),
5. Numer i treść asercji dodanej w Warstwie 5 (test_system.py),
6. Wynik uruchomienia test_system.py (musi być 100% PASSED).

Odpowiedź pozbawiona tej ścieżki stanowi bezpośrednie naruszenie reguł workspace.

---

## ⚖️ 8. ZAKAZ SAMOZACHWYTU I PUSTYCH ZAPEWNIEŃ

1. Asystent ma zakaz używania ogólnikowych sformułowań w rodzaju: 'zapewniam, że wszystko stoi na najwyższym poziomie', 'system jest idealny', 'od teraz obiecuję'.
2. Wiarygodność inżynierska opiera się wyłącznie na:
   - Twardych diffach w kodzie,
   - Konkretnych asercjach w testach,
   - Weryfikowalnych plikach na dysku i commitach w repozytorium.

---

## 💰 9. ŻELAZNE OGRANICZENIA KOSZTOWE I ŚRODOWISKOWE

1. **Bezwzględny zakaz Vertex AI:** use_vertex = 0, brak zależności od GCP billing. Wyłącznie bezpośrednie klucze Google AI Studio API Keys.
2. **Context Caching:** Wszystkie zapytania muszą wykorzystywać pre-warming i rabat -90%.
3. **Koszty zerowe:** Mechanizmy lintera, audytu i pamięci serialu muszą mieć koszt dokładnie 0.00 PLN.

---

## ⚡ 10. ZASADA PROAKTYWNEJ INTEGRALNOŚCI I ZAKAZ CIĄGŁEGO ŁATANIA (PROACTIVE LEXICAL & REGISTER GOVERNANCE MANDATE)

1. **Zakaz sprowadzania napraw do kolejnych regexów (Anti-Whack-A-Mole):**
   Asystent ma kategoryczny zakaz traktowania lintera regexów (`FIXED_REPLACEMENTS`) jako głównego narzędzia naprawczego. Reaktywne dopisywanie pojedynczych słów jest bezużyteczne wobec nieskończoności wariantów mowy potocznej. Każdy problem leksykalny i rejestrowy musi zostać rozwiązany **proaktywnie i strukturalnie**.
2. **Kategoryczna Taksonomia Zakazanego Slangu per Gatunek:**
   Dla każdego gatunku (w szczególności Dark Fantasy, High Fantasy, Dramat Historyczny) w promptach modelek (Warstwy 1 i 3) musi obowiązywać formalna, 4-klasowa matryca zakazów:
   - **Klasa A (Slang młodzieżowy/potoczny):** bezwzględny zakaz współczesnych wtrętów (`i gitara`, `spoko`, `siemanko`, `ziomek`, `wchodzę w to`).
   - **Klasa B (Agresja podwórkowa):** zakaz wulgaryzacji i trywializacji gniewu (`stul pysk`, `zamknij się`, `spuścić łomot`, `dostać w łeb`, `oberwać`).
   - **Klasa C (Współczesne metafory potoczne):** zakaz metafor z języka potocznego XX/XXI w. (`przejmuję stery`, `dla zabicia czasu`, `kłamstwo jak byk`, `wylecieć ze szkoły`).
   - **Klasa D (Trywializujące określenia osób):** zakaz dehumanizujących lub potocznych zaimków (`ten typ`, `chuliganka`, `dzikuska`, `dzieciaki`).
3. **Obligatoryjny Krok Negatywnego Audytu w Fazie 2 CoT:**
   Faza 2 (Redakcja AVT CoT 6000) **musi** w swoim procesie myślowym (Chain-of-Thought) zawierać jawny, wyodrębniony krok weryfikacji negatywnej (Negative Register & Calque Gate):
   - Weryfikacja rejestru i eliminacja slangu klas A–D.
   - Weryfikacja kalek przydomkowych: zakaz konstrukcji `X od Y` (np. `Zavthier od Złudzeń` $\to$ `Zavthier Pani Iluzji` / `Iluzoryczna Zavthier`).
   - Weryfikacja rządu gramatycznego i rodzaju rzeczowników (`posoka` jest wyłącznie rodzaju żeńskiego).
4. **Autonomiczne Zasilanie Encyklopedii Serii w Pre-passie:**
   Profiler ma obowiązek autonomicznie wyodrębnić toponimy, tytulaturę i artefakty przed Fazą 1, zapisać je w `SeriesBible` z właściwą deklinacją i rodzajem, uniemożliwiając linterowi ich błędną interpretację jako odmienianych postaci po przyimkach.
5. **Uogólniony Sanityzator Błędów Cyfrowych w Znacznikach Czasu:**
   Algorytm naprawy inwersji czasowych w linterze musi obsługiwać pełen wachlarz czeskich błędów cyfrowych w zapisie czasu (minuty, dziesiątki minut, godziny: $\Delta t \in \{60s, 120s, 600s, 1200s, 3600s\}$).

---

## 🔒 11. ZASADA ZERO DESTRUKCJI I BEZWZGLĘDNEGO BEZPIECZEŃSTWA WARSTW OFFLINE (ZERO-COLLISION & NON-DESTRUCTIVE OFFLINE INVARIANCE GATE)

1. **Bezwzględny nakaz sprawdzania braku skutków ubocznych (Primum Non Nocere):**
   Wprowadzając jakąkolwiek poprawkę do warstw offline (`avt_linter.py`, `series_memory.py`, linter regexów, `EpisodeQualityGate`), asystent ma **bezwzględny obowiązek** zweryfikować, że zmiana w 100% eliminuje błąd docelowy, ale pod żadnym pozorem **nie wygeneruje błędów w innych, poprawnych tłumaczeniach**.
2. **Kategoryczny zakaz bezkontekstowych i niezakotwiczonych podmian (Context-Blind Regex Ban):**
   - Zakaz stosowania otwartych wzorców `\bFRAZA\b` dla potocznych wykrzykników, idiomów i paralingwistyki.
   - Wszelkie reguły zastępujące okrzyki somatyczne i odruchy (np. *Ała!*, *Parzy!*, *Uważaj!*, *Trudno*, *Ratunku!*) **muszą być twardo zakotwiczone składniowo**: na początku kwestii (`^`), po łamaniu linii (`\N`) lub po myślniku dialogowym `[-–]`, oraz wymagać wykrzyknika `!`.
   - Pod żadnym pozorem nie wolno dopuścić do sytuacji, w której reguła usuwa orzeczenie zdania podrzędnego lub złożonego (np. *„Wiem, jak bardzo to boli”* $\to$ *„Wiem, jak bardzo Ała!”*).
3. **Wymóg audytu kolizyjności semantycznej i homonimicznej (Semantic Collision Audit):**
   Przed wdrożeniem jakiejkolwiek reguły offline asystent musi zbadać 4 wymiary potencjalnych kolizji:
   - **Wymiar dosłowny/medyczny:** ochrona fizycznych opisów ciała (np. *ból klatki piersiowej* to nie zawsze metafora pękniętego serca, a *wyciągnąć ręce* to nie skrót myślowy).
   - **Wymiar dziedzinowy/leksykalny:** ochrona homonimów (np. *bas i gitara* to instrumenty muzyczne, *ciasto bez jaj* to składnik kulinarny).
   - **Wymiar składniowy/orzeczeniowy:** ochrona zdań pytających i orzekających (*Czy to boli?*, *To jest niebezpieczne dla zdrowia*, *Dobre pytanie zadał profesor*).
   - **Wymiar fleksyjny:** ochrona przed „mianownizacją” (np. *konbini* musi odmieniać się przyimkowo: *w sklepie*, *do sklepu*, *ze sklepu*).
4. **Obowiązkowa asercja antykolizyjna (Double-Sided Assertion Mandate):**
   Każdy test w Warstwie 5 (`test_system.py`) weryfikujący regułę offline **musi zawierać co najmniej dwa symetryczne testy**:
   - **Test pozytywny:** sprawdzenie, czy błędna fraza w izolowanym kontekście jest prawidłowo naprawiana.
   - **Test negatywny (antykolizyjny):** sprawdzenie, czy zdanie podrzędne, opisowe, dosłowne lub homonimiczne pozostaje w 100% nienaruszone.
5. **Techniczna integralność silnika wyrażeń regularnych (Zero Lookbehind Errors):**
   Kategoryczny zakaz wprowadzania wzorców z lookbehindem o zmiennej długości (np. `(?<=-\s*)` lub alternacje o różnych długościach w `(?<!...)`), które powodują błędy kompilacji `re.PatternError`. Wszelkie zakotwiczenia pozycji muszą być realizowane przez grupy przechwytujące (`(^|\\[Nnh]|[-–]\s*)`) i podstawienie `\1`.

---

## 🔬 12. ŻELAZNA ZASADA BEZWZGLĘDNEJ DIAGNOZY ŹRÓDŁOWEJ PRZED PROPOZYCJĄ PLANU I ELIMINACJI CAŁYCH RODZIN POKREWNYCH BŁĘDÓW (ROOT-CAUSE-FIRST & COMPREHENSIVE ERROR-FAMILY MANDATE)

1. **Bezwzględna sekwencja inżynierska (Diagnoza Źródłowa ZAWSZE przed Planem):**
   - Asystent ma kategoryczny zakaz przedstawiania użytkownikowi planu naprawczego (`implementation_plan.md`), dopóki nie przeprowadzi dogłębnej, wyczerpującej analizy przyczyny źródłowej (Root Cause Analysis).
   - Proponowanie planu opartego wyłącznie na powierzchownym symptomie, izolowanym wyrazie lub bez zbadania mechanizmu generującego błąd w całym potoku jest traktowane jako bezpośrednia awaria asystenta i naruszenie reguł workspace.

2. **Obowiązkowy protokół pytań kontrolnych („Lekcja z pytań Użytkownika: A co z innymi słowami? Co z innymi parami?”):**
   Gdy użytkownik podaje uwagę lub przykład błędu, asystent ma bezwzględny obowiązek przeprowadzić autonomiczny audyt rozszerzający, zadając sobie 3 obligatoryjne pytania diagnostyczne:
   - **„A co z innymi słowami?” (Analiza Dystrybucyjna i Podciągowa):**
     Jeśli błąd wiąże się ze słowem kluczowym (np. `pani`, rolą, tytułem, nazwą własną), asystent musi zbadać całą klasę leksykalną (np. `pan`, `panie`, `samuraj`, `kuge`, `buke`, `lord`, `generał`, `wasal`, `kobieta`, `mężczyzna`, `boy`, `tomboy`) pod kątem tego samego mechanizmu defektu (np. zatrucie podciągami, brak granic słów `\b`, kolizje z przypadkami zależnymi).
   - **„A co z innymi parami / formami?” (Analiza Paradygmatyczna i Morfologiczna):**
     Jeśli błąd dotyczy formy gramatycznej lub pary fleksyjnej (np. para `-ogłam` $\leftrightarrow$ `-ogłem`), asystent ma kategoryczny zakaz ograniczania się do tej jednej końcówki. Musi z urzędu zidentyfikować i wdrożyć obsługę wszystkich pokrewnych klas nieregularnych (np. 7 klas czasu przeszłego: `-ogłam/-ogłem`, `-ekłam/-ekłem`, `-arłam/-arłem`, `-otłam/-otłem`, oboczności wokaliczne prefiksów czasownika `iść`, imiesłowy bierne `-ny/-na`, `-ty/-ta`).
   - **„Jakie inne byty w systemie podlegają temu samemu mechanizmowi?” (Analiza Architektoniczna):**
     Asystent musi prześledzić cały potok danych: w których innych bazach serii, promptach, parserach czy funkcjach lintera ten sam błąd logiczny mógł zasiać skażone dane lub doprowadzić do cichej awarii.

3. **Plan naprawczy musi eliminować CAŁE ZBIORY błędów wynikające ze źródła:**
   - Pierwszy plan przedstawiony użytkownikowi w `implementation_plan.md` **musi od razu i z definicji** eliminować cały zbiór błędów wypływających z ustalonego źródła.
   - Użytkownik nie może być zmuszany do dopytywania o pozostałe słowa, brakujące pary fleksyjne czy analogiczne konstrukcje. To asystent ma obowiązek przyjść z kompletną taksonomią i gotowym, całościowym rozwiązaniem.

---

## 🕊️ 13. ŻELAZNA ZASADA MAKSYMALNEGO ODCIĄŻENIA MODELI GEMINI I KOMPLETNEJ MECHANICZNEJ KOREKTY DWUZNACZNOŚCI EN W WARSTWIE 4 (LLM UNBURDENING & COMPREHENSIVE MECHANICAL EN-AMBIGUITY RESOLUTION MANDATE)

1. **Czystość Filarów i Promptów (Całkowity Zakaz Zaśmiecania Modeli Sztywnymi Regułami):**
   - Modele Gemini (Faza 1 i Faza 2) mają pozostać w maksymalnym stopniu wolne od sztywnych zakazów (`ZAKAZ`, `KATEGORYCZNY ZAKAZ`), nakazów, list zabronionych słów czy mikro-dyrektyw leksykalnych.
   - Zadaniem modeli Gemini jest symulowanie procesu myślenia profesjonalnego tłumacza audiowizualnego (AVT master craft) — autentyczna kreacja żywego dialogu filmowego, interpretacja intencji, emocji i podtekstu seiyū, klimatu oraz dramaturgii sceny.
   - Filary w Warstwie 3 mają zawierać **wyłącznie zwięzłe, pozytywne wektory rzemiosła AVT** (kto z kim rozmawia, jaki jest wektor dramaturgiczny i rejestr epoki/sceny).
   - Wszelkie sztywne regułki, które paraliżują naturalność i wywołują u modeli efekt „różowego słonia”, mają być bezwzględnie usuwane z promptów. Informacje o relacji (np. płeć adresata) mają trafiać do modelu w zwięzłej strukturze danych wejściowych (`addressee: "mężczyzna"`), a nie jako ściany zakazów tekstowych.

2. **Warstwa 4 jako Kompletna i Ściśle Mechaniczna Tarcza Dwuznaczności Języka Angielskiego:**
   - Asystent ma bezwzględny obowiązek z urzędu (bez czekania na interwencję użytkownika) identyfikować i eliminować w Warstwie 4 (`EpisodeQualityGate` offline 0.00 PLN) **kompletny zbiór błędów wynikających z gramatycznego ubóstwa i dwuznaczności języka angielskiego** (brak rodzaju w zaimku *you*, niejednoznaczność *you* jako ty/wy, bezosobowy passive voice *you were...*, bezrodzajowe przymiotniki i imiesłowy orzecznikowe, angielskie rzeczowniki o wspólnym rodzaju), dla których Warstwy 1 i 2 dostarczają 100% pewnych danych faktograficznych.
   - Korekta w Warstwie 4 jest **ściśle mechaniczna i nieinwazyjna**:
     - Polega wyłącznie na deterministycznym zharmonizowaniu końcówki fleksyjnej wynikającej z rozstrzygnięcia dwuznaczności angielskiej.
     - **Cała tkanka dialogu wypracowana przez myślący model w Fazie 2 (styl, dobór słów, szyk wyrazów, metafory, rytm) POZOSTAJE W 100% NIENARUSZONA W SWOJEJ ORYGINALNEJ FORMIE.**

3. **Autonomiczna Kompleksowość bez Konieczności Upominania przez Użytkownika:**
   - Asystent ma kategoryczny zakaz czekania na dopytanie przez użytkownika: *„czy pozostałe filary są wolne od zakazów?”* lub *„czy wszystkie błędy mechaniczne zostały uwzględnione?”*.
   - Przy każdym zgłoszeniu asystent ma obowiązek z własnej inicjatywy:
     a) Zbadać, czy filary Warstwy 3 nie zawierają sztywnych zakazów i nakazów, i oczyścić je do formy czystego procesu myślowego tłumacza,
     b) Zidentyfikować pełną rodzinę mechanicznych konsekwencji dwuznaczności angielskiej i wdrożyć ich kompletną, bezpieczną obsługę w Warstwie 4.

---

## 🌐 14. ŻELAZNA ZASADA POKRYCIA CAŁEJ DOMENY JĘZYKA POLSKIEGO W KAŻDYM PLANIE NAPRAWCZYM (EXHAUSTIVE POLISH LINGUISTIC DOMAIN MANDATE)

1. **Całościowe Pokrycie Domeny Językowej Już w Pierwszym Planie (Zero Partial Plans):**
   Proponując plan naprawczy (`implementation_plan.md`), asystent ma bezwzględny obowiązek od razu objąć **całą domenę języka polskiego** powiązaną ze zgłoszonym zjawiskiem:
   - Pełne paradygmaty fleksyjne (wszystkie 7 przypadków deklinacji, wszystkie osoby, liczby, rodzaje gramatyczne, czasy i tryby).
   - Wszelkie prefiksy, afiksy i oboczności wokaliczno-spółgłoskowe (np. oboczności rdzeniowe *ó:o*, *ą:ę*, *e:zero*, wymiany spółgłoskowe *t:ć*, *d:dź*, *ł:l*).
   - Wszystkie struktury syntagmatyczne (związki rządu, zgody i przynależności, przydawki dopełniaczowe, człony przyimkowe, apozycje rzeczownikowe).
   - Kategorycznie zakazuje się przedstawiania planów fragmentarycznych, wybiórczych lub ograniczonych do pojedynczych form.

2. **Standard Benchmarku (Lekcja 1200+ Form):**
   Wzorem procedury dla odmiany syntagm i czasowników nieregularnych (gdzie w jednym planie zabezpieczono ponad 1200 unikalnych form fleksyjnych i wszystkie warianty syntagm kanonu mangowego), każdy plan musi stanowić kompletną, wyczerpującą matrycę gramatyczną danej klasy zjawisk. Użytkownik nie może być zmuszany do dopytywania, czy uwzględniono pozostałe formy, pary fleksyjne, osoby czy przypadki.

3. **Jednotokenowa Niezmienniczość ($W_i \to W'_i$) i Ochrona Szyku Zdania:**
   Całościowa obsługa domeny językowej ma być wdrażana symetrycznie w 5 warstwach, ze szczególnym uwzględnieniem deterministycznego silnika Warstwy 4 (0.00 PLN), który:
   - Działa na zasadzie $W_i \to W'_i$ (wymiana wyłącznie docelowego tokenu wymagającego dostosowania gramatycznego),
   - Bezwzględnie chroni nienaruszalność szyku zdania i wyrazów sąsiadujących,
   - Nie narusza tkanki dialogu filmowego wypracowanej przez modele Gemini.

---

## 🔒 15. ŻELAZNA ZASADA BEZWZGLĘDNEJ KOMPLETNOŚCI LEKSYKALNEJ, PRZYIMKOWEJ I PRZYPADKOWEJ (EXHAUSTIVE LEXICON, PREPOSITION & ALL-CASES MANDATE)

1. **Zakaz Pomijania Jakichkolwiek Polskich Terminów (Exhaustive Domain Analysis & Zero-Omission Mandate):**
   - Asystent ma kategoryczny zakaz ograniczania się do wąskich, wybiórczych wycinków słownikowych (np. 5 przykładowych słów, 4 par orzeczników czy kilkunastu haseł).
   - Każde zjawisko leksykalne i gramatyczne musi zostać przeanalizowane holistycznie pod kątem pytania: *„Czy jakiekolwiek pokrewne polskie terminy nie zostały pominięte?”*.
   - Obowiązkiem asystenta jest autonomiczne zmapowanie i uwzględnienie **wszystkich kategorii semantycznych i rejestrowych** powiązanych z danym zagadnieniem (np. hierarchia wojskowa, feudalna, arystokracja, klasy fantasy, profesje, rzemiosło, rasy, potwory, byty nadprzyrodzone, instytucje, organizacje, lokacje, toponimy, architektura, geografia, oręż, artefakty, zjawiska).

2. **Obowiązek Proponowania Pełnych List Słów (Full-Catalog Proposal Mandate):**
   - Asystent ma bezwzględny obowiązek przedstawiać w planie i kodzie **zawsze całą, kompletną, wyczerpującą listę słów**, a nie listę skróconą, reprezentatywną czy fragmentaryczną z dopiskiem *„itp.”*.
   - Każdy katalog musi być zamkniętą, kompletną bazą danych leksykalnych gotową do natychmiastowego deterministycznego działania w silniku offline.

3. **Bezwzględny Wymóg Uwzględniania Wszystkich Przyimków (All-Prepositions Mandate):**
   - Asystent ma kategoryczny zakaz wybiórczego traktowania przyimków (np. uwzględniania tylko *dla, z, do* z pominięciem innych).
   - Wszelkie mechanizmy rekcji przyimkowej, wariantów fonetycznych oraz harmonizacji zaimkowo-przyimkowej **muszą bezwzględnie obejmować wszystkie polskie przyimki pierwotne i wtórne** rządzące danym przypadkiem:
     - **Dopełniacz**: *dla, do, od, z, ze, bez, u, koło, obok, blisko, wokół, dookoła, pośród, wśród, spod, zza, znad, wzdłuż, podczas, mimo, według, wskutek, wobec, naprzeciw*,
     - **Celownik**: *dzięki, przeciw, przeciwko, ku, wbrew*,
     - **Biernik**: *przez, przeze, na, w, we, o, za, pod, pode, nad, nade, przed, przede, między, pomiędzy, poza*,
     - **Narzędnik**: *z, ze, za, pod, pode, nad, nade, przed, przede, między, pomiędzy, poza*,
     - **Miejscownik**: *o, w, we, na, po, przy*.

4. **Bezwzględny Wymóg Uwzględniania Wszystkich 7 Przypadków Gramatycznych (All-7-Cases Declension Mandate):**
   - Każdy rzeczownik, tytuł, rola, toponim i nazwa własna wprowadzana do systemu **musi bezwzględnie posiadać pełny paradygmat odmiany przez wszystkie 7 przypadków gramatycznych** w liczbie pojedynczej (oraz mnogiej, jeśli występuje):
     1. **Mianownik (M)**: kto? co?
     2. **Dopełniacz (D)**: kogo? czego?
     3. **Celownik (C)**: komu? czemu?
     4. **Biernik (B)**: kogo? co?
     5. **Narzędnik (N)**: z kim? z czym?
     6. **Miejscownik (Ms)**: o kim? o czym?
     7. **Wołacz (W)**: o! (forma adresatywna, wołaczowa).
   - Kategorycznie zakazuje się tworzenia struktur niekompletnych (np. brak wołacza, brak miejscownika, pominięcie formy biernika).

