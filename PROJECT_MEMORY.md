# 🧠 PAMIĘĆ PROJEKTU I STANU ROZMOWY ANTIGRAVITY (PROJECT MEMORY & SESSION STATE)

Dokument ten stanowi trwały, zsynchronizowany most wiedzy pomiędzy komputerami roboczymi (PC 1 i PC 2) dla asystenta AI Antigravity.

---

## 🎯 1. AKTUALNY STATUS PROJEKTU (Stan na 03.10.2026)
- **Status:** `STATUS: WDROŻONE I ZWERYFIKOWANE (142/142 PASSED) - KOD W CHMURZE GITHUB`
- **Ostatni zatwierdzony cel:** Całkowita eliminacja dwóch krytycznych wad translacyjnych:
  1. **Niezgodności płciowej** (męskie formy u mówczyń, błędne formy adresatywne w diadach i polilogach, załamanie liczby mnogiej żeńskiej `-yście` vs `-iście`).
  2. **Błędów deklinacji i rekcji** (nominative freezing kanonu mangi, gwałcenie dopełniacza przy zaprzeczeniu *Genitive of Negation*, amputacje/zniekształcenia obcych imion żeńskich i męskich).
- **Format pracy zespołu:** Zespół dwuagentowy:
  - **Agent 1:** Lead Systems Implementer
  - **Agent 2:** Adversarial Architecture Reviewer (audyt pod kątem efektów drugiego rzędu, hierarchii Chomsky'ego, teorii kanału transmisyjnego, problemu uziemiania symboli).

---

## 🏛️ 2. PRZEGLĄD WDROŻENIA W 5 WARSTWACH ARCHITEKTURY

1. **Warstwa 1 (`profiler.py`):**
   - W `format_lean_episode_brief` dodano sekcję `TOPOLOGIA SCENY I UZGADNIANIE PŁCI` (wymóg form żeńskich 1. i 2. os., liczby mnogiej żeńskiej `-yście`, zaimek `one`, oraz ścisła rekcja zaprzeczona).
2. **Warstwa 2 (`series_memory.py`):**
   - Dodano katalog `FOREIGN_FEMALE_CONSONANT_NAMES` (`Chulan`, `Frieren`, `Fern`, `Carmen`, `Miriam`, `Ines` itd.) gwarantujący 100% nieodmienność żeńskich imion obcych na spółgłoskę we wszystkich 7 przypadkach ($M=D=C=B=N=Ms=W$).
   - Ochrona męskich imion na `-a` (`Soma`, `Akira`, `Koba`) w `CANONICAL_MALE_NAMES`.
   - Zaimplementowano funkcje deterministyczne: `replace_with_case_preservation`, `sanitize_genitive_of_negation`, `sanitize_canon_compound_oblique_cases` wpięte do `sanitize_lexical_text`.
3. **Warstwa 3 (`rules.py` & `verifier.py`):**
   - **Filar CLXXXVII:** Zarządzanie Płcią w Topologii Sceny.
   - **Filar CLXXXVIII:** Ścisła Rekcja Zaprzeczona i Prewencja Mianownizacji Kanonu.
   - Triggery 128 i 129 w `get_active_rules`.
   - Krok 3 myślenia CoT (Faza 2, budżet 6144) z jawnym audytem negatywnym płci, dopełniacza przy negacji i odmiany terminów kanonu po przyimkach.
4. **Warstwa 4 (`avt_linter.py`):**
   - **Tarcza Cytatów (`QuoteShield`):** Pełna ochrona cytatów w cudzysłowach (`„...”`, `»...«`, `«...»`, `"..."`) przed modyfikacją $W_i \to W'_i$ (ochrona męskich cytatów w wypowiedziach kobiet).
   - Krok 4g w `EpisodeQualityGate`: deterministyczna korekta rekcji zaprzeczonej oraz zamrożonych form mianownikowych kanonu po przyimkach (*z Aura Gilotyna* -> *z Aurą Gilotyną*, *dla Wielki Chan* -> *dla Wielkiego Chana*).
5. **Warstwa 5 (`test_system.py`):**
   - 142 testy regresyjne kończące się 100% sukcesem (nowe Asercje 139, 140, 141, 142).

---

## 🔄 3. PROCEDURA SYNCHRONIZACJI KODU (PC 1 <-> PC 2)

- **Na nowym/drugim PC (pierwszy raz):**
  ```powershell
  git add . ; git commit -m "Zapis przed pobraniem" ; git pull --no-rebase origin main --no-edit
  ```
- **Na co dzień:**
  - Aby pobrać i uzupełnić kod o zmiany z drugiego PC: uruchom `POBIERZ_ZMIANY_Z_CHMURY.bat`.
  - Aby wysłać swoje nowe zmiany do drugiego PC: uruchom `WYSLIJ_ZMIANY_DO_CHMURY.bat`.
- Git wykonuje bezpieczne scalenie trójstronne (3-way merge) – **żadne lokalne usprawnienia nie są nadpisywane**.

---

## 👥 4. ŻELAZNY PROTOKÓŁ ZESPOŁU DWUAGENTOWEGO (Zasada 20 AGENTS.md, /learn)

Podczas pracy w konfiguracji zespołu dwuagentowego (np. przy procedurze `/goal` lub głębokim refaktorze potoku):
- **Agent 1:** Lead Systems Implementer (przygotowuje plan w 5 warstwach, analizuje kod, projektuje architekturę i testy).
- **Agent 2:** Adversarial Reviewer & Systemic Auditor (przeprowadza bezkompromisowy audyt planu Agenta 1).

### 🔍 11 Wymiarów Audytu Agenta 2:
1. **Efekty drugiego rzędu (Second-Order Vulnerabilities)** – czy naprawa jednego błędu nie psuje innego modułu.
2. **Ukryte założenia (Hidden Assumptions)** – niewypowiedziane domysły o strukturze wejściowej i tagach ASS.
3. **Martwe punkty na styku kodu deterministycznego (Deterministic Boundary Blindspots)** – zachowanie czystej granicy 0.00 PLN vs LLM.
4. **Matematyczny brak informacji w kanale transmisyjnym (Shannon Information Deficit)** – unikanie zgadywania cech bez sygnału źródłowego.
5. **Autoregresyjne załamanie rozkładu (Autoregressive Mode Collapse)** – prewencja pętli powtórzeń i zubożenia leksykalnego.
6. **Błąd kategorii w hierarchii Chomsky’ego (Chomsky Hierarchy Category Error)** – zakaz parsowania gramatyk złożonych prostym regexem.
7. **Kaskadowa utrata rozkładów prawdopodobieństwa (Cascading Probability Loss)** – zakaz przedwczesnego blokowania interpretacji w Fazie 1.
8. **Problem uziemiania symboli (Symbol Grounding Problem)** – uziemianie pojęć w semantyce sceny, seiyū i wideo.
9. **Deiksa sytuacyjna (Situational Deixis Failure)** – poprawna orientacja przestrzenna, relacja ja-ty i zmiana audytorium.
10. **Utrata wspólnej przestrzeni poznawczej (Common Ground Depletion)** – uwzględnianie asymetrii wiedzy postaci i widza.
11. **Nieizomorficzność topologiczna przestrzeni pojęciowych i spadek stopni swobody** – zakaz sztucznego rzutowania struktur JA/EN na PL.

Iteracja kończy się dopiero po wystawieniu przez Agenta 2:
`STATUS: ZATWIERDZENIE ARCHITEKTONICZNE (ZERO BŁĘDÓW) - GOTOWY DO DECYZJI OPERATORA`.

