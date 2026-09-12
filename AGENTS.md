# 🏛️ ZASADY DZIAŁANIA ASYSTENTA (WORKSPACE RULES — TRANSLATOR)

Ten dokument definiuje nienaruszalne, trwałe reguły postępowania asystenta AI w repozytorium translator. Został wdrożony jako permanentny bezpiecznik architektoniczny i jest automatycznie ładowany do kontekstu na każdym kroku pracy.

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

## 📝 3. OBOWIĄZKOWY PROTOKÓŁ PLANOWANIA I AKCEPTACJI PRZED EDYCJĄ KODU (PLANNING & USER APPROVAL GATE)

1. **Zakaz samowolnych modyfikacji kodu:**
   Przed dokonaniem jakiejkolwiek zmiany w plikach źródłowych (.py, konfiguracjach) asystent ma bezwzględny obowiązek przygotować plan naprawczy w `implementation_plan.md` (z metadanymi `RequestFeedback: true`).
2. **Czekanie na wyraźną zgodę:**
   Asystent zatrzymuje się, przedstawia plan i oczekuje na wyraźną akceptację użytkownika przed przystąpieniem do edycji kodu.

---

## 🛡️ 4. OBOWIĄZKOWY PROTOKÓŁ 5 WARSTW (5-LAYER ROOT CAUSE PROTOCOL)

Każde zgłoszenie błędu przez użytkownika nakłada na asystenta obowiązek przeprowadzenia audytu i wdrożenia zabezpieczeń w **5 warstwach architektury**:

| Warstwa | Komponent | Zadanie i odpowiedzialność asystenta |
| :--- | :--- | :--- |
| **Warstwa 1** | profiler.py (Pre-pass) | Zidentyfikować, dlaczego model na wejściu błędnie zinterpretował postać, scenę lub relację. Dodać twardy bezpiecznik w promptcie Profilera (np. pułapka ról, pułapka imion). |
| **Warstwa 2** | series_memory.py (Baza Wiedzy) | Zbadać, dlaczego Pamięć Serialu zaakceptowała skażony wpis. Wdrożyć symetryczną ochronę przed nadpisaniem (np. has_confirmed_female / has_confirmed_male), rozszerzyć słownik ról. |
| **Warstwa 3** | rules.py (Kanon & Prompty) | Dodać/rozszerzyć właściwy Filar AVT oraz zaktualizować dynamiczny dyspozytor uwagi (focused_pillars), zakazując tego błędu bezpośrednio w instrukcjach dla modeli. |
| **Warstwa 4** | avt_linter.py (EpisodeQualityGate) | Wdrożyć deterministyczny bezpiecznik (0.00 PLN) działający na pełnej osi czasu, który wyłapie i zneutralizuje błąd, nawet jeśli oba modele AI kompletnie zawiodą. |
| **Warstwa 5** | test_system.py (Test Regresyjny) | Napisać dedykowaną asercję w teście integracyjnym odwzorowującą ten konkretny błąd, aby żaden przyszły commit nie mógł go przywrócić. |

---

## 📋 5. WYMÓG TABELI DOWODOWEJ W ODPOWIEDZI

W odpowiedzi na jakiekolwiek zgłoszenie usterki translatorskiej, asystent **musi** przedstawić tabelę dowodową wskazującą:
1. Co konkretnie zmieniono w Warstwie 1 (profiler.py),
2. Co konkretnie zmieniono w Warstwie 2 (series_memory.py),
3. Co konkretnie zmieniono w Warstwie 3 (rules.py),
4. Co konkretnie zmieniono w Warstwie 4 (avt_linter.py),
5. Numer i treść asercji dodanej w Warstwie 5 (test_system.py),
6. Wynik uruchomienia test_system.py (musi być 100% PASSED).

Odpowiedź pozbawiona tej ścieżki stanowi bezpośrednie naruszenie reguł workspace.

---

## ⚖️ 6. ZAKAZ SAMOZACHWYTU I PUSTYCH ZAPEWNIEŃ

1. Asystent ma zakaz używania ogólnikowych sformułowań w rodzaju: 'zapewniam, że wszystko stoi na najwyższym poziomie', 'system jest idealny', 'od teraz obiecuję'.
2. Wiarygodność inżynierska opiera się wyłącznie na:
   - Twardych diffach w kodzie,
   - Konkretnych asercjach w testach,
   - Weryfikowalnych plikach na dysku i commitach w repozytorium.

---

## 💰 7. ŻELAZNE OGRANICZENIA KOSZTOWE I ŚRODOWISKOWE

1. **Bezwzględny zakaz Vertex AI:** use_vertex = 0, brak zależności od GCP billing. Wyłącznie bezpośrednie klucze Google AI Studio API Keys.
2. **Context Caching:** Wszystkie zapytania muszą wykorzystywać pre-warming i rabat -90%.
3. **Koszty zerowe:** Mechanizmy lintera, audytu i pamięci serialu muszą mieć koszt dokładnie 0.00 PLN.

---

## 📖 8. ZASADA ZERO-CONFABULATION W DOKUMENTACJI I KANONIE (GROUND-TRUTH SOURCING)

1. **Zakaz generowania terminów „z pamięci” modelu:**
   Asystent ma bezwzględny zakaz wprowadzania do dokumentacji (README.md, opisy, tabele porównawcze, prompty) jakichkolwiek „przykładowych” lub „kanonicznych” terminów, nazwisk tłumaczy, tytułów czy przydomków na podstawie wewnętrznych wag LLM.
2. **Obowiązek weryfikacji w bazie kodu (`manga_canon.py`):**
   Wszelkie przykłady oficjalnego kanonu podawane w dokumentacji MUSZĄ być zmapowane 1:1 z istniejącymi, zweryfikowanymi wpisami w `manga_canon.py` lub potwierdzone w stopce redakcyjnej licencjonowanego polskiego wydawnictwa papierowego.
3. **Automatyczny audyt dokumentacji (CI Gate):**
   Każda zmiana w pliku README.md podlega automatycznemu testowi weryfikacyjnemu w `test_system.py` (Asercja 7), który weryfikuje spójność terminologiczną i uniemożliwia zatwierdzenie niesprawdzonych treści.

---

## ⚡ 9. ZASADA PROAKTYWNEJ INTEGRALNOŚCI I ZAKAZ CIĄGŁEGO ŁATANIA (PROACTIVE LEXICAL & REGISTER GOVERNANCE MANDATE)

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

