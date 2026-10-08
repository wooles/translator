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

### 🔍 18 Wymiarów Audytu Agenta 2:
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
12. **Ślepota modalności wizualnej (The Visual Grounding Void)** – weryfikacja wektora wzroku, mimiki, obecności postaci i linii off-screen.
13. **Zatrucie językiem pośredniczącym (Pivot Collapse / The English Bottleneck)** – eliminacja spłaszczeń angielskiego pivotu i partykuł modalnych.
14. **Lingwistyczna teoria ról i kamuflażu (Yakuwarigo & Code-Switching)** – stylizacja języka ról i dynamiczne przełączanie rejestru.
15. **Asymetria chronemiczna (Mora-timed JA vs Stress-timed PL)** – uwzględnienie różnicy między czasem morowym a akcentowym.
16. **Wielokanałowość semantyczna japońskiego pisma (Ateji, Gikun i Goroawase)** – zachowanie fuzji podwójnej warstwy kanji/furigana.
17. **Pustka kulturowa i zakaz przypisów w AVT (Zero-Footnote Constraint)** – bezwzględny zakaz przypisów na ekranie, bezszwowa enkapsulacja.
18. **Teoremat o sprzeczności kryteriów i Wielokryterialna Funkcja Straty AVT (Barrier Augmented Lagrangian)**:
    - Optymalizacja: $\mathcal{L}_{\text{AVT}}(\theta) = \mathcal{L}_{\text{sem}}(y, x) + \alpha \mathcal{L}_{\text{flu}}(y) + \mathcal{P}_{\text{AVT}}(y, \Delta t)$ przy twardym warunku $\text{CPS}(y, \Delta t) \le \text{CPS}_{\max}$.
    - Asymetryczna bariera tempa czytania $\Phi(\text{CPS})$ z karą kwadratową powyżej $20.0$ zn/s.
    - Asymetryczna bariera geometrii $\Psi(\text{CPL})$ ($2 \times 38$ znaków) oraz głodzenia repliki $\Omega(\text{len})$.
    - Dynamiczne mnożniki Lagrange'a $\lambda_{\text{cps}}^{(k+1)}$ aktualizowane gradientem wstępującym.
    - Selekcja Script Doctor Fazy 2 funkcją nagrody: $R = r_{\text{sem}} + 0.3 r_{\text{flu}} - [2.5 \Phi(\text{CPS}) + 5.0 \Psi(\text{CPL})]$.

Iteracja kończy się dopiero po wystawieniu przez Agenta 2:
`STATUS: ZATWIERDZENIE ARCHITEKTONICZNE (ZERO BŁĘDÓW) - GOTOWY DO DECYZJI OPERATORA`.

---

## 🧠 5. ARCHITEKTURA FAZY 2: SELEKCJA BEST-OF-N Z WIELOKRYTERIALNĄ FUNKCJĄ NAGRODY ANTY-GOODHART (SCRIPT DOCTOR HARNESS)

### 🎯 5.1. Cel i Aksjomaty Architektoniczne
Tradycyjna optymalizacja karająca wyłącznie za przekroczenie sufitu CPS ($\text{CPS} > 17.0$) prowadzi do **katastrofalnego efektu Goodharta**:
- Model uczy się, że najprostszą drogą do zera kar jest drastyczna amputacja dialogu.
- Skutkiem jest kastracja ładunku emocjonalnego seiyū, wycinanie partykuł modalnych (*przecież*, *no*, *chyba*, *zaś*), degradacja stylizacji postaci oraz zastępowanie soczystej polszczyzny jałowymi, telegraficznymi równoważnikami zdań.

Faza 2 (Script Doctor / Re-ranking Best-of-N) egzekwuje **Dwustronną Asymetryczną Studnię Potencjału (Asymmetric Dead-Band Potential)**:
1. **Twarde limity geometryczne ekranu:** Obrona fizjologii oka widza ($\text{CPS} \le 17.0$, $\text{CPL} \le 38$, $\max 2$ linie).
2. **Obrona dynamiki gry seiyū (Bariera Podłogowa Anty-Sterylność):** Kara za nadmierne spłaszczenie kwestii, gdy oryginał japoński niesie gęsty potok mowy ($\rho_x = \text{moras}(x) / \Delta t \ge 9.0$).

---

### 📐 5.2. Formalna Matematyczna Funkcja Nagrody Anty-Goodhart
Model oceny wariantu $y$ przy czasie planszy $\Delta t$, gęstości mor japońskiego oryginału $\rho_x = \frac{\text{moras}(x)}{\Delta t}$ oraz telemetrii akustycznej $a$:

$$R_{\text{AVT}}(y \mid x, \Delta t, a) = R_{\text{base}}(y, x) - \Big[ P_{\text{band}}(y, \Delta t, \rho_x) + \lambda_{\text{cpl}} \cdot \Psi(\text{CPL}(y)) + L_{\text{drama}}(y, x, a) \Big]$$

#### Składowe Kary:
1. **Asymetryczny sufit CPS (Fizjologia oka - Hard Barrier):**
   $$\Phi_{\text{ceil}}(\text{CPS}) = \ln\left(1 + \exp\left(\frac{\text{CPS} - 17.0}{0.8}\right)\right) + \mathbb{I}(\text{CPS} > 20.0) \cdot (\text{CPS} - 20.0)^2$$
   - $\text{CPS} \le 17.0$: Kara $\approx 0.0$.
   - $17.0 < \text{CPS} \le 20.0$: Kara rośnie liniowo/gładko.
   - $\text{CPS} > 20.0$: Bezwzględna dyskwalifikacja kandydata (kara $50.0+$).

2. **Bezpiecznik anty-Goodhart (Podłoga CPS zależna od gęstości mor - Anti-Sterility Barrier):**
   $$\text{CPS}_{\text{target}}(\rho_x) = \min(13.5, \; 7.5 + 0.5 \cdot \rho_x)$$
   $$\Phi_{\text{floor}}(\text{CPS}, \rho_x) = \max\big(0, \; \text{CPS}_{\text{target}}(\rho_x) - \text{CPS}\big)^2$$
   - Jeśli $\text{CPS} < \text{CPS}_{\text{target}}$, a w oryginale trwa gęsty dialog seiyū ($\rho_x \ge 9.0$ mor/s), naliczana jest dotkliwa kara za kastrację ekspresji.

3. **Integralność afektywna audio-tekst ($L_{\text{drama}} / D_{\text{aff}}$):**
   $$D_{\text{aff}} = \| e_{\text{text}}(y) - a_{\text{audio}} \|_2^2$$
   - Arousal "AGGRESSIVE" lub "HYSTERIC" bez ładunku emocjonalnego $\to$ Kara $10.0$.
   - Hesitation w audio (`has_vocal_hesitation == True`) z wyciętym wielokropkiem lub pauzą $\to$ Kara $8.0$.

4. **Geometria linii ASS ($\Psi(\text{CPL})$):**
   Maksymalnie 2 wiersze po 38 znaków czystego tekstu (bez tagów `{...}`).
   $$\Psi(\text{CPL}(y)) = \sum_{l \in \text{lines}(y)} \max\big(0, \; \text{len}(l) - 38\big)^2 + \mathbb{I}(|\text{lines}(y)| > 2) \cdot 50.0$$

---

### 📜 5.3. Kontrakt Promptu Sterującego Fazą 2 (Script Doctor)

```markdown
ROLA: Elitarny Script Doctor AVT i Sędzia Optymalizacyjny (JA/EN -> PL).

ZADANIE:
Oceń N kandydatów tłumaczenia dla pojedynczej planszy napisów ASS.
Zastosuj Wielokryterialną Funkcję Nagrody z Bezpiecznikiem Anty-Goodhart,
aby wybrać wariant optymalny pod kątem dramaturgii i geometrii ekranu.
Jeśli żaden kandydat nie spełnia kryteriów, przeprowadź precyzyjną mikronaprawę.

REGUŁY KALKULACJI STRAT I KAR (Anti-Goodhart Loss):

1. BARIERA SUFITOWA CPS (Fizjologia Oka - Hard Barrier):
   - CPS <= 17.0: Kara = 0.0.
   - 17.0 < CPS <= 20.0: Kara rośnie liniowo (3.0 * (CPS - 17.0)).
   - CPS > 20.0: Bezwzględna dyskwalifikacja kandydata (Kara = 50.0).

2. BEZPIECZNIK ANTY-GOODHART: BARIERA PODŁOGOWA CPS (Anti-Sterility Barrier):
   - Jeśli CPS < cps_target_floor, a w oryginale trwa gęsty dialog seiyū (mora_density >= 9.0 mor/s):
     Nalicz karę: 2.5 * (cps_target_floor - CPS).
   - ODRZUĆ kandydatów spłaszczonych emocjonalnie do lakonicznych równoważników zdań,
     jeśli usuwają oni kluczowe partykuły modalne, ekspresję i nastawienie mówcy.

3. INTEGRALNOŚĆ AFEKTYWNO-DRAMATURGICZNA (Audio-Text Alignment):
   - Jeśli audio_telemetry.arousal_level to "AGGRESSIVE" lub "HYSTERIC", tekst MUSI posiadać
     ładunek emocjonalny (odpowiednia leksyka, wykrzyknik, partykuły wzmacniające: "przecież", "no").
     Brak ładunku = Kara 10.0.
   - Jeśli audio_telemetry.has_vocal_hesitation jest TRUE, wycięcie wielokropka wstrzymania
     głosu lub wahania ("...", "…", "—") = Kara 8.0.

4. GEOMETRIA CPL (Format ASS):
   - Maksymalnie 2 linie tekstu, rozdzielone sekwencją \N.
   - Maksymalnie 38 znaków w pojedynczym wierszu (bez tagów {...}).
   - Przekroczenie limitu znaku w linii = Kara 4.0 za każdy nadmiarowy znak.

5. INTEGRALNOŚĆ GRAMATYCZNA I MORFOLOGICZNA:
   - Zero nominative freezing (bezwzględny wymóg poprawnego przypadku i rekcji zaprzeczonej).
   - Ścisła zgodność z płcią mówcy i adresata podaną w obiekcie "discourse".

PROCEDURA DECYZYJNA:
1. Oblicz sumaryczną karę dla każdego kandydata:
   Total_Penalty = cps_penalty + anti_goodhart_floor_penalty + affective_mismatch_penalty + cpl_geometry_penalty
2. Wybierz kandydata o najmniejszej karze.
3. Jeśli wybrany kandydat ma Total_Penalty > 0, ustaw `requires_micro_repair: true`
   i w `final_subtitle_text` wygeneruj skorygowaną polską kwestię mieszczącą się w paśmie [cps_target_floor, 17.0].
```

---

### 💻 5.4. Kanoniczny Wzorzec Implementacyjny Harnessu w Pythonie
Wzorzec deterministycznego przygotowania danych, interakcji z modelem i deterministycznego bezpiecznika w Warstwie 4:

```python
import dataclasses
import json
import re
from typing import List, Dict, Any
from google import genai
from google.genai import types

def prepare_doctor_payload(
    candidates_raw: List[str],
    duration_s: float,
    source_ja: str,
    source_mora_count: int,
    audio_telemetry: Dict[str, Any],
    discourse_context: Dict[str, Any]
) -> Dict[str, Any]:
    dur = max(0.5, duration_s)
    source_density = source_mora_count / dur
    cps_floor = min(13.5, 7.5 + 0.5 * source_density)
    
    evaluated = []
    for idx, text in enumerate(candidates_raw):
        pure = re.sub(r"\{[^}]*\}", "", text)
        lines = pure.split(r"\N")
        char_len = len(pure.replace(r"\N", ""))
        cps = char_len / dur
        cpl_errs = sum(max(0, len(l.strip()) - 38) for l in lines)
        
        evaluated.append({
            "candidate_id": idx,
            "text": text,
            "char_count": char_len,
            "cps": round(cps, 2),
            "lines_count": len(lines),
            "cpl_overflow_chars": cpl_errs
        })

    return {
        "timing": {
            "duration_s": round(dur, 3),
            "cps_target_floor": round(cps_floor, 2),
            "cps_hard_ceiling": 17.0,
            "cps_rejection_barrier": 20.0
        },
        "source": {
            "ja": source_ja,
            "mora_count": source_mora_count,
            "mora_density": round(source_density, 2)
        },
        "audio_telemetry": {
            "f0_median_hz": audio_telemetry.get("f0_median"),
            "arousal_level": audio_telemetry.get("arousal"),
            "has_vocal_hesitation": audio_telemetry.get("has_hesitation", False)
        },
        "discourse": discourse_context,
        "candidates": evaluated
    }

class ScriptDoctorSelector:
    def __init__(self, client: genai.Client, model_name: str = "gemini-2.5-pro"):
        self.client = client
        self.model_name = model_name

    def select_and_repair(self, payload: Dict[str, Any], schema: Dict[str, Any]) -> Dict[str, Any]:
        prompt_content = f"DANE WEJŚCIOWE DO ANALIZY:\n```json\n{json.dumps(payload, ensure_ascii=False, indent=2)}\n```\nWybierz najlepszego kandydata lub dokonaj mikronaprawy zgodnie z zasadami anty-Goodhart."

        config = types.GenerateContentConfig(
            temperature=0.1,
            top_p=0.95,
            response_mime_type="application/json",
            response_schema=schema,
            system_instruction="Jesteś modułem Fazy 2 (Script Doctor) w potoku AVT. Decyduj ściśle w oparciu o dostarczone metryki i rubrykę anty-Goodhart."
        )

        response = self.client.models.generate_content(
            model=self.model_name,
            contents=prompt_content,
            config=config
        )

        result = json.loads(response.text)
        return self._post_validate(result, payload)

    def _post_validate(self, result: Dict[str, Any], payload: Dict[str, Any]) -> Dict[str, Any]:
        final_text = result["final_subtitle_text"]
        pure_text = re.sub(r"\{[^}]*\}", "", final_text).replace(r"\N", "")
        dur = payload["timing"]["duration_s"]
        final_cps = len(pure_text) / dur

        if final_cps > 20.0:
            lines = final_text.split(r"\N")
            result["final_subtitle_text"] = r"\N".join(l[:38] for l in lines)
            result["verdict_rationale"] += " [Failsafe: przycięto awaryjnie w post-walidacji]"

        return result
```

---

## 🚨 6. HIERARCHICZNY PROTOKÓŁ PRACY ZESPOŁU CZTEROAGENTOWEGO (STANDARD 3.0)

Wszystkie zgłoszenia defektów dialogowych podlegają pod Żelazny Protokół Obsługi Incydentów 3.0:
1. **OPERATOR (Jedyny Właściciel I/O):** Fizyczny zapis do repozytorium następuje wyłącznie po komendzie: `ZATWIERDZAM DOSSIER - WDROŻYĆ DO KODU`.
2. **AGENT 4 (Autonomous Operational Supervisor):** Pełnomocnik Operatora i jedyny punkt kontaktu. Egzekwuje dyscyplinę, przerywa spory po 2 iteracjach (Anti-Loop Watchdog), rozdziela ruch na Fast-Track (< 2 min) i Deep Incident Track, audytuje rzetelność A3 i A1 oraz syntetyzuje 1-stronicowe Dossier Decyzyjne.
3. **AGENT 3 (Chief Epistemic Architect):** Analiza ontologiczna (Root Cause), twarde kontrakty Pydantic (`speaker_grammatical_gender`), czerwony test regresyjny i Wskaźnik Rytmu Oddechowego (Breathing Space Index).
4. **AGENT 1 (Lead Implementer):** Prototypowanie w RAM, Diff Preview, naprawa u źródła w schematach danych Pydantic, zakaz puchnięcia lintera.
5. **AGENT 2 (Adversarial Reviewer & ASS-Fuzzing):** Audyt 18 wymiarów, weryfikacja złośliwych tagów ASS (`{\i1}`, `\pos`, `\an8`, `\N`, `\h`), obrona dramaturgii przed prawem Goodharta oraz atak na zjawiska spoza okna (max 1 runda poprawek).
6. **Golden Corpus Anchor Gate:** Bezwzględny wymóg **100.0% sukcesu** na Scenach Kotwiczących (Zero Regression Tolerance), $\ge 99.0\%$ na Broader Corpus, $\ge 99.8\%$ na atrybucji płci.
7. **Permanentny Standard Raportowania (Ujednolicona Tabela Dowodowa 5 Warstw):** Każda odpowiedź asystenta podsumowująca obsługę błędu Operatora musi zawierać zreformowaną Tabelę Dowodową 5 Warstw (Warstwa 1: Kontrakt Pydantic; Warstwa 2: Fast/Deep Track & Rejestr Długu; Warstwa 3: Anti-Goodhart & Breathing Space Index; Warstwa 4: ASS-Fuzzing & Visual Token Resilience; Warstwa 5: Anchor Scenes 100.0% & CI/CD PASS) stanowiącą twardy certyfikat inżynierski.



