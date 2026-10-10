# 🧠 PAMIĘĆ PROJEKTU I STANU SESJI ANTIGRAVITY (PROJECT MEMORY & OPERATIONAL TELEMETRY)

Dokument ten stanowi zsynchronizowany rejestr stanu operacyjnego potoku, telemetrii CI/CD, historii incydentów oraz most wiedzy pomiędzy komputerami roboczymi (PC 1 i PC 2) dla asystenta AI Antigravity.
Zasady normatywne i aksjomaty inżynierskie definiuje wyłącznie `AGENTS.md` (Single Source of Truth).

---

## 🎯 1. AKTUALNY STATUS POTOKU (Stan na 10.10.2026)
- **Status CI/CD:** `STATUS: WDROŻONE I ZWERYFIKOWANE (155/155 PASSED) - KOD W CHMURZE GITHUB`
- **Gałąź i Commit:** `main` (commit: `1ea2260` — pełna integracja INC-AVT-002)
- **Środowisko:** Python 3.13 (.venv), Windows PowerShell, bezpośrednie klucze Google AI Studio API (`use_vertex = 0`)
- **Format pracy zespołu:** Hierarchiczny Protokół Czteroagentowy (Standard 3.0):
  * **OPERATOR (Człowiek):** Wyłączny właściciel praw zapisu I/O (autoryzacja komendą: `ZATWIERDZAM DOSSIER - WDROŻYĆ DO KODU`).
  * **AGENT 4:** Autonomous Operational Supervisor (Anti-Loop Watchdog, Triage, Dossier dla Operatora).
  * **AGENT 3:** Chief Epistemic Architect & AVT Dramaturge (Ontologia, kontrakty Pydantic, czerwony test).
  * **AGENT 1:** Lead Systems Implementer (Prototypowanie RAM, Diff Preview).
  * **AGENT 2:** Adversarial Reviewer & ASS-Fuzzing (18 Wymiarów Audytu, Breathing Space Index).

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
