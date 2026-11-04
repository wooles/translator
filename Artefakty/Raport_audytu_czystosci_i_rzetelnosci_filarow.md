# RAPORT AUDYTU CZYSTOŚCI JĘZYKOWEJ I RZETELNOŚCI FILARÓW AVT

## 0. METADANE
- **Repozytorium:** `https://github.com/wooles/translator`
- **HEAD audytowany:** `9f4df49` (`9f4df49fbeb399e8bed1af979ee8b2ba97f082a4` — Standard 10.3 na gałęzi `main`)
- **Suplement powiązany:** `Artefakty/Raport_audytu_czystosci_i_rzetelnosci_filarow_SUPLEMENT.md`
- **Data audytu (zamknięcie):** `2026-11-04`
- **Audytor:** Niezależny Audytor Architektoniczny AVT
- **Zakres:** Diagnostyka czystości metajęzykowej (`Z1–Z4`) oraz weryfikacja rzetelności merytorycznej względem 5 zweryfikowanych źródeł profesjonalnych.

---

## 1. EXECUTIVE SUMMARY
- **Liczba Filarów w `rules.py` (commit `9f4df49`):**
  - **Warstwa Bazowa (`STANDARD_9_CORE_RULES_PROMPT` — zawsze aktywna w runtime):** **4 makro-filary arabskie** (`FILAR 1` – `FILAR 4`) podzielone na **16 reguł alfanumerycznych** (`R1.1–R1.11` oraz `R3.1–R3.5`).
  - **Warstwa Dynamiczna (`get_focused_rules_for_batch` — warunkowa w runtime):** **9 ortogonalnych Kategorii Dynamicznych (`DYN_1` – `DYN_9`)**, grupujących w swoich nagłówkach **39 unikalnych rzymskich numerów Filarów**.
  - **Warstwa Pasywna (`TRANSLATION_RULES_PROMPT` — zamrożone archiwum Z16):** **180 unikalnych rzymskich numerów Filarów** (`FILAR I` – `FILAR CLXXX`), nieaktywnych w domyślnym potoku (`use_lean_prompt=True`).
- **Liczba naruszeń `Z1 (Zero-Literal — nazwy własne z anime)`: `0`**.
- **Liczba naruszeń `Z4 (przykłady konkretnych zdań dialogowych)`: `0`**.
- **Liczba sprzeczności merytorycznych z profesjonalnymi wytycznymi AVT: `0`**.
- **Liczba naruszeń `P1` (do naprawy w hotfixie 10.4): `1`** (`N-01` — japońskie zapożyczenie `seiyū` w aktywnym prompcie `FILAR 2` / `R1.8` oraz `DYN_5`, linie `2564`, `2573`, `2855`).
- **Liczba obserwacji `P2` (kosmetyczne / Z16 / dług techniczny do backlogu 11.0): `4`** (`N-02`, `N-03`, `N-04`, `N-05` — po przeklasyfikowaniu `N-05` z `P1` na `P2`).
- **Werdykt końcowy:** **`PASS_Z_DROBNYMI`** (1 obserwacja `P1` skierowana do hotfixu `10.4`, 1 obserwacja `P2` dot. regexów skierowana do backlogu `11.0`).

---

## 2. FAZA 0 — INWENTARYZACJA

- **F0.1:** W `rules.py` występuje **180 unikalnych rzymskich numerów Filarów** (`FILAR I–CLXXX` w `TRANSLATION_RULES_PROMPT`, z czego 39 zgrupowano w `DYN_1–DYN_9`) oraz **4 makro-filary arabskie** (`FILAR 1–4`, 16 reguł `R1.1–R3.5`) w `STANDARD_9_CORE_RULES_PROMPT`.
- **F0.2:** Zawsze aktywne (base): `FILAR 1–4` (`R1.1–R1.11`, `R3.1–R3.5`).
- **F0.3:** Warunkowe (dynamic): 9 kategorii `DYN_1–DYN_9` w `get_focused_rules_for_batch`.
- **F0.4:** W `profiler.py` (`format_lean_episode_brief`, linia `688–689`) znajduje się jednozdaniowa kotwica odsyłająca do `R1.4` i `R3.1–R3.5`.
- **F0.5:** Maksymalny numer rzymski to `FILAR CLXXX` (180), numeracja jest ciągła.

---

## 3. FAZA 1 — ANALIZA CZYSTOŚCI JĘZYKOWEJ FILARÓW

| Identyfikator / Numer | Tytuł kategorii / Filaru | Źródło (`base` / `dynamic` / `pasywny`) | Czy zawiera nazwy własne? (`Y/N`) | Czy zawiera przykłady zdań? (`Y/N`) | Z4 (tekst dla LLM) | Z4 (wewnętrzny regex Pythona) | Uwagi audytorskie (`9f4df49`) |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **`FILAR 1` (`R1.1`–`R1.6`)** | Składnia, Pro-Drop, Werbalizacja i Rekcja | `base` | `N` | `N` | `Y` | `N/A` | 100% czysta domena gramatyczno-składniowa. |
| **`FILAR 2` (`R1.7`–`R1.9`)** | Zwięzłość AVT, Rytm Seiyū i Paralingwistyka | `base` | `N` | `N` | **`N` (`N-01 P1`)** | `N/A` | Zawiera loanword `SEIYŪ` / `seiyū` w liniach `2564` i `2573` -> do zamiany na `aktor głosowy` w `10.4`. |
| **`FILAR 3` (`R3.1`–`R3.5`)** | Spójność Rodzaju Gramatycznego P0, Adresata, Cytatów i Liczebników | `base` | `N` | `N` | `Y` | `N/A` | 100% czysta domena fleksyjna. |
| **`FILAR 4` (`R1.10`–`R1.11`)** | Formatowanie Techniczne ASS, Wielokropki i Kursywa | `base` | `N` | `N` | `Y` | `N/A` | 100% czysta domena techniczna ASS. |
| **`DYN_1`: `FILAR XIII & XII`** | Dialekty Regionalne, Gwara, Sociolekty i Kontrast Rejestrów | `dynamic` (`95`) | `N` | `N` | `Y` | `N` (`N-05 P2`) | Tekst dla LLM w 100% czysty; regex wewnętrzny zawiera markery JP (dług techniczny `N-05 P2`). |
| **`DYN_2`: `FILAR XIV & XXX`** | Archaizacja, Etykieta Dworska i Rejestr Wysoki | `dynamic` (`92`) | `N` | `N` | `Y` | `N` (`N-05 P2`) | Tekst dla LLM w 100% czysty; regex wewnętrzny zawiera markery JP (`N-05 P2`). |
| **`DYN_4`: `FILAR CXXXVI, XCVI & XV`** | Triangulacja Wieku i Płci oraz Grupy Niemęskoosobowe | `dynamic` (`88`) | `N` | `N` | `Y` | `N` (`N-05 P2`) | Tekst dla LLM w 100% czysty; regex wewnętrzny zawiera markery JP (`N-05 P2`). |
| **`DYN_3`: `FILAR XXV..XXIX & CLVII`** | Tytulatura, Forma Rówieśnicza i Harmonia Adresatywna | `dynamic` (`84`) | `N` | `N` | `Y` | `N` (`N-05 P2`) | Tekst dla LLM w 100% czysty; regex wewnętrzny zawiera sufiksy JP (`N-05 P2`). |
| **`DYN_5`: `FILAR CLXXII..XVII`** | Dynamiczny Prymat Afektu, Prozodia Oddechu i Somatyka | `dynamic` (`82`) | `N` | `N` | **`N` (`N-01 P1`)** | `N` (`N-05 P2`) | Tekst zawiera loanword `seiyū` w linii `2855` (`N-01 P1`); regex zawiera `ottotto|kakegoe` (`N-05 P2`). |
| **`DYN_6`: `FILAR CLXV, LXV, CLXIX & CLXXIX`** | Ciągłość Zdań Rozbitych, Szyk Rematyczny i Pary Przylegania | `dynamic` (`80`) | `N` | `N` | `Y` | `Y` | 100% czysta domena składniowo-dyskursywna w tekście i regexie. |
| **`DYN_9`: `FILAR XIX & LXXVI`** | Ładunek Afektywny Przekładu, Melancholia i Liryka Emocjonalna | `dynamic` (`74`) | `N` | `N` | `Y` | `N` (`N-05 P2`) | Tekst dla LLM w 100% czysty; regex wewnętrzny zawiera markery JP (`N-05 P2`). |
| **`DYN_7`: `FILAR XLIX..LVI`** | Rejestry Specjalistyczne: Taktyczno-Bojowy, Medyczny i Śledczy | `dynamic` (`72`) | `N` | `N` | `Y` | `Y` | 100% czysta domena specjalistyczna w tekście i regexie. |
| **`DYN_8`: `FILAR LXXVIII..CXIX`** | Adaptacja Kulturowa, Gry Słowne, Onomatopeje i Napisy Ekranowe | `dynamic` (`70`) | `N` | `N` | `Y` | `N` (`N-05 P2`) | Tekst dla LLM w 100% czysty; regex wewnętrzny zawiera markery JP (`N-05 P2`). |
| **`TRANSLATION_RULES_PROMPT`** | Pasywny Monument Archiwalny (`FILAR I–CLXXX`) | `pasywny` (`Z16`) | `N` | `N` | `N/A (Z16)` | `N/A` | Zamrożone przez Zasadę 16 (`test_system.py`). |

---

## 4. FAZA 2 — WERYFIKACJA RZETELNOŚCI I ZGODNOŚCI Z PROFESJONALNYMI WYTYCZNYMI

Wszystkie 13 aktywnych grup Filarów (`FILAR 1–4` oraz `DYN_1–DYN_9`) wykazuje **pełną zgodność merytoryczną** z 5 zweryfikowanymi źródłami profesjonalnymi (*Netflix Polish TTSG 2024*, *STAW / Doktorat SBC Judyty Mężyk*, *TUFS Lisa Sanders*, *Dialogica 2026 Olga Pióro*, *UAM 2026*). Szczegółowe macierze znajdują się w pierwszej wersji raportu oraz w suplemencie.

---

## 5. FAZA 3 — IDENTYFIKACJA NARUSZEŃ I REKOMENDACJE ( PO REKLASYFIKACJI )

### 5.1. Uzasadnienie przeklasyfikowania N-01 (`P2 -> P1`)
> N-01 przeklasyfikowano z P2 na P1 na podstawie suplementu audytorskiego (`SUPLEMENT.md`, sekcja P1.4). Termin `seiyū` (japoński loanword) występuje w aktywnym prompcie bazowym (`R1.8`, linie `2564` i `2573`) oraz w kategorii dynamicznej `DYN_5` (linia `2855`). W polskim AVT standardowym terminem jest `aktor głosowy`. Użycie `seiyū` w prompcie dla LLM może prowadzić do kopiowania tego terminu do polskiego wyjścia. Naprawa w hotfixie 10.4.

### 5.2. Uzasadnienie przeklasyfikowania N-05 (`P1 -> P2`)
> N-05 przeklasyfikowano z P1 na P2 po analizie semantyki Zasady 4 (Instance-Free). Regex w `get_focused_rules_for_batch` (`en_slang_pat`, `jp_dialect_pat`, `archaic_pat`, `honorific_pat`, `age_gender_pat`, `combat_affect_pat`, `lyric_high_pat`, `lyric_support_pat`, `culture_signs_pat`) to **wewnętrzny mechanizm detekcji**, nie treść promptu LLM. LLM nigdy nie widzi tych regexów — widzi wyłącznie **wynik** (`True`/`False`), który decyduje o dodaniu **czystego** tekstu reguły do promptu. Tokeny japońskie w regexach to **kategorie językowe** (partykuły dialektu, honoryfikatory), a nie **instancje** (imiona, tytuły serii). Zasada 4 (Z4) zakazuje **instancji** (nazw własnych z anime), a nie **kategorii** (japońskich partykuł). W związku z tym N-05 nie jest naruszeniem Z4 w ścisłym sensie — jest to **dług techniczny** (niejednorodność architektoniczna: teksty Filarów czyste, regexy z japońskimi tokenami). Rozwiązanie: przenieść japońskie tokeny z `rules.py` do `whisper_disambiguator.py` w ramach backlogu 11.0.

### 5.3. Zbiorcza tabela naruszeń i obserwacji (`N-01` – `N-05`)

| ID | Lokalizacja | Typ naruszenia / obserwacji | Konkretny fragment (`9f4df49`) | Rekomendacja | Priorytet |
| :---: | :--- | :--- | :--- | :--- | :---: |
| **`N-01`** | `FILAR 2` (`R1.8`, linie `2564, 2573`) oraz `DYN_5` (`rules.py:2855`) | **`Z4` (japoński loanword `seiyū` w aktywnym prompcie LLM)** | `RYTM SEIYŪ`, `czasu trwania głosu seiyū`, `fizjologia emocji seiyū` | Zastąpić polską kategorią metajęzykową **`[AKTOR_GŁOSOWY]`** w hotfixie `10.4` + dodać test `T10.4_1`. | **`P1`** *(Hotfix 10.4)* |
| **`N-02`** | `FILAR 2` (`R1.7`, `rules.py:2569`) | Parametr techniczny CPL (`38 CPL` vs `42 CPL` Netflix) | `limit 38 znaków w linii (CPL)` | Zachować `38 CPL` jako bezpieczniejszy podzbiór normy `42 CPL` dla dużych czcionek `.ass` 1080p. | **P2** *(Zachować)* |
| **`N-03`** | `TRANSLATION_RULES_PROMPT` (`rules.py:25–2524`) | Archiwum Legacy (`Z16-locked`) | Pasywna stała `TRANSLATION_RULES_PROMPT` | **NIE RUSZAĆ (Zasada 16)**. | **P2** *(Z16-locked)* |
| **`N-04`** | `profiler.py:688–689` | Backlog (`L-06`) | `format_lean_episode_brief` | Opcjonalna rozbudowa o adnotacje kontekstowe humoru/aluzji na poziomie odcinka w `11.0`. | **P2** *(Backlog 11.0)* |
| **`N-05`** | `get_focused_rules_for_batch` (`rules.py:2716–2936`) | Dług techniczny (japońskie tokeny leksykalne wewnątrz regexów detekcji Pythona) | Wewnętrzne wzorce `en_slang_pat`, `jp_dialect_pat`, `archaic_pat`, `honorific_pat`, `age_gender_pat`, `combat_affect_pat`, `lyric_high_pat`, `culture_signs_pat` | Przenieść japońskie tokeny detekcyjne z `rules.py` do `whisper_disambiguator.py` w ramach Standardu `11.0`. | **P2** *(Backlog 11.0)* |

---

## 6. FAZA ODBIORU

- [x] FAZA 0 — Inwentaryzacja: `180` unikalnych numerów rzymskich Filarów + `4` makro-filary arabskie (`16` reguł `R1.1–R3.5`)
- [x] FAZA 1 — Analiza czystości: `0` nazw własnych z anime (`Z1`), `0` przykładów zdań dialogowych (`Z4`), `1` japoński loanword w aktywnym tekście (`seiyū` -> `N-01 P1`)
- [x] FAZA 2 — Weryfikacja rzetelności: `13/13` aktywnych grup Filarów w pełni zgodnych merytorycznie z 5 źródłami profesjonalnymi (`0` sprzecznych)
- [x] FAZA 3 — Naruszenia i obserwacje po reklasyfikacji: `0` P0, `1` P1 (`N-01` -> hotfix `10.4`), `4` P2 (`N-02`, `N-03`, `N-04`, `N-05` -> `N-05` przeklasyfikowano z P1 na P2 do backlogu `11.0`)
- [x] Werdykt końcowy: **`PASS_Z_DROBNYMI`**
- [x] 0 placeholderów `<DO_WYPEŁNIENIA>`
- [x] 0 zmian w kodzie produkcyjnym
- [x] Z16 nienaruszone
- [x] Z1/Z2/Z3/Z4 respektowane