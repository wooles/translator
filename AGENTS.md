# 🏛️ ZASADY DZIAŁANIA ASYSTENTA (WORKSPACE RULES — TRANSLATOR)

Ten dokument definiuje nienaruszalne, trwałe reguły postępowania asystenta AI w repozytorium translator. Został wdrożony jako permanentny bezpiecznik architektoniczny i jest automatycznie ładowany do kontekstu na każdym kroku pracy.

---

## 🚫 1. KATEGORYCZNY ZAKAZ DORAŹNEGO ŁATANIA (ANTI-PATCHING MANDATE)

1. **Defekt tłumaczenia to zawsze awaria potoku:**
   Gdy użytkownik zgłasza błąd w napisach (np. zła płeć, hybryda rejestru, błąd tytulatury, nienaturalna kalka), asystent ma **bezwzględny zakaz** ograniczania się do poprawienia linijki w pliku .ass lub dopisania pojedynczego regexa w linterze.
2. **Kolejność działań:**
   Poprawienie pliku wynikowego .ass jest dopuszczalne wyłącznie jako **ostatni krok**, po usunięciu źródła błędu w całym potoku.

---

## 🛡️ 2. OBOWIĄZKOWY PROTOKÓŁ 5 WARSTW (5-LAYER ROOT CAUSE PROTOCOL)

Każde zgłoszenie błędu przez użytkownika nakłada na asystenta obowiązek przeprowadzenia audytu i wdrożenia zabezpieczeń w **5 warstwach architektury**:

| Warstwa | Komponent | Zadanie i odpowiedzialność asystenta |
| :--- | :--- | :--- |
| **Warstwa 1** | profiler.py (Pre-pass) | Zidentyfikować, dlaczego model na wejściu błędnie zinterpretował postać, scenę lub relację. Dodać twardy bezpiecznik w promptcie Profilera (np. pułapka ról, pułapka imion). |
| **Warstwa 2** | series_memory.py (Baza Wiedzy) | Zbadać, dlaczego Pamięć Serialu zaakceptowała skażony wpis. Wdrożyć symetryczną ochronę przed nadpisaniem (np. has_confirmed_female / has_confirmed_male), rozszerzyć słownik ról. |
| **Warstwa 3** | rules.py (Kanon & Prompty) | Dodać/rozszerzyć właściwy Filar AVT oraz zaktualizować dynamiczny dyspozytor uwagi (focused_pillars), zakazując tego błędu bezpośrednio w instrukcjach dla modeli. |
| **Warstwa 4** | avt_linter.py (EpisodeQualityGate) | Wdrożyć deterministyczny bezpiecznik (0.00 PLN) działający na pełnej osi czasu, który wyłapie i zneutralizuje błąd, nawet jeśli oba modele AI kompletnie zawiodą. |
| **Warstwa 5** | test_system.py (Test Regresyjny) | Napisać dedykowaną asercję w teście integracyjnym odwzorowującą ten konkretny błąd, aby żaden przyszły commit nie mógł go przywrócić. |

---

## 📋 3. WYMÓG TABELI DOWODOWEJ W ODPOWIEDZI

W odpowiedzi na jakiekolwiek zgłoszenie usterki translatorskiej, asystent **musi** przedstawić tabelę dowodową wskazującą:
1. Co konkretnie zmieniono w Warstwie 1 (profiler.py),
2. Co konkretnie zmieniono w Warstwie 2 (series_memory.py),
3. Co konkretnie zmieniono w Warstwie 3 (rules.py),
4. Co konkretnie zmieniono w Warstwie 4 (avt_linter.py),
5. Numer i treść asercji dodanej w Warstwie 5 (test_system.py),
6. Wynik uruchomienia test_system.py (musi być 100% PASSED).

Odpowiedź pozbawiona tej ścieżki stanowi bezpośrednie naruszenie reguł workspace.

---

## ⚖️ 4. ZAKAZ SAMOZACHWYTU I PUSTYCH ZAPEWNIEŃ

1. Asystent ma zakaz używania ogólnikowych sformułowań w rodzaju: 'zapewniam, że wszystko stoi na najwyższym poziomie', 'system jest idealny', 'od teraz obiecuję'.
2. Wiarygodność inżynierska opiera się wyłącznie na:
   - Twardych diffach w kodzie,
   - Konkretnych asercjach w testach,
   - Weryfikowalnych plikach na dysku i commitach w repozytorium.

---

## 💰 5. ŻELAZNE OGRANICZENIA KOSZTOWE I ŚRODOWISKOWE

1. **Bezwzględny zakaz Vertex AI:** use_vertex = 0, brak zależności od GCP billing. Wyłącznie bezpośrednie klucze Google AI Studio API Keys.
2. **Context Caching:** Wszystkie zapytania muszą wykorzystywać pre-warming i rabat -90%.
3. **Koszty zerowe:** Mechanizmy lintera, audytu i pamięci serialu muszą mieć koszt dokładnie 0.00 PLN.

---

## 📖 6. ZASADA ZERO-CONFABULATION W DOKUMENTACJI I KANONIE (GROUND-TRUTH SOURCING)

1. **Zakaz generowania terminów „z pamięci” modelu:**
   Asystent ma bezwzględny zakaz wprowadzania do dokumentacji (README.md, opisy, tabele porównawcze, prompty) jakichkolwiek „przykładowych” lub „kanonicznych” terminów, nazwisk tłumaczy, tytułów czy przydomków na podstawie wewnętrznych wag LLM.
2. **Obowiązek weryfikacji w bazie kodu (`manga_canon.py`):**
   Wszelkie przykłady oficjalnego kanonu podawane w dokumentacji MUSZĄ być zmapowane 1:1 z istniejącymi, zweryfikowanymi wpisami w `manga_canon.py` lub potwierdzone w stopce redakcyjnej licencjonowanego polskiego wydawnictwa papierowego.
3. **Automatyczny audyt dokumentacji (CI Gate):**
   Każda zmiana w pliku README.md podlega automatycznemu testowi weryfikacyjnemu w `test_system.py` (Asercja 7), który weryfikuje spójność terminologiczną i uniemożliwia zatwierdzenie niesprawdzonych treści.
