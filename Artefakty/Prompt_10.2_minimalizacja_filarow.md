# PROMPT WYKONAWCZY (STANDARD 10.2) — DEDUPLIKACJA, MINIMALIZACJA I PRECYZYJNA SELEKCJA FILARÓW AVT W `rules.py`

- **Wersja docelowa:** `10.2`
- **Wersja poprzednia (baseline):** `10.1.1` (HEAD `81de7b5` / `81de7b5a1f9f927c1e4ccca318458e7afb12eda3`)
- **Baseline Depuracji Legacy 1.0 (Z16):** `474fb64`
- **Zakres:** Minimalizacja i deduplikacja aktywnych Filarów AVT w `rules.py` i `profiler.py` oraz przebudowa selektora `get_focused_rules_for_batch` bez naruszania archiwum Z16.

---

## PREAMBUŁA

Niniejszy prompt wykonawczy realizuje wnioski z kompleksowego audytu systemu Filarów AVT przeprowadzonego po certyfikacji Hotfixu 10.1.1 (`81de7b5`). Pełny kontekst diagnostyczny zawiera dokument: `Artefakty/Raport_audytu_filarow.md` (commit `81de7b5`, sekcje 3–9). Wersja otrzymuje oznaczenie `10.2`, ponieważ operacja porządkuje i kondensuje warstwę selekcji dynamicznej w `rules.py` oraz `profiler.py` przy zachowaniu dotychczasowego kontraktu architektonicznego `STANDARD_9_CORE_RULES_PROMPT` i zamrożonego archiwum `TRANSLATION_RULES_PROMPT`.

**Trzy nadrzędne cele wdrożenia 10.2:**
1. **Minimalna liczba aktywnych Filarów w runtime:** redukcja architektury wykonawczej do **12 ortogonalnych Kategorii Wykonawczych AVT** (4 Kategorie Bazowe zawsze aktywne w `STANDARD_9_CORE_RULES_PROMPT` + maksymalnie 8 Kategorii Dynamicznych w `get_focused_rules_for_batch`).
2. **Całkowita unikalność treści (Zero Duplikacji):** wyeliminowanie wszystkich 22 zidentyfikowanych duplikatów pomiędzy `STANDARD_9_CORE_RULES_PROMPT`, `get_focused_rules_for_batch` oraz `format_lean_episode_brief` w `profiler.py`.
3. **Precyzyjna, wysokoprogowa selekcja:** wyeliminowanie nadaktywnych triggerów szumowych, które dotychczas wybierały 3 ogólne reguły w niemal każdej paczce dialogowej; dla standardowej paczki dialogowej pozbawionej zjawisk specjalnych selektor ma zwracać pusty ciąg znaków, pozostawiając autorytet 4 Kategoriom Bazowym.

**Zasady nadrzędne Standardu 9.0 (obowiązujące w 100%):**
- **Z1 (Zero-Literal):** całkowity zakaz umieszczania w kodzie, regułach i testach jakichkolwiek nazw własnych z audytowanych serii.
- **Z2 (Pure Positive Domain):** wszystkie sformułowania kategorii w `rules.py` i `profiler.py` opisują wyłącznie pożądany stan docelowy w formie pozytywnej.
- **Z3 (Primary LLM Translation Authority):** kategorie w `rules.py` stanowią wskazówki metajęzykowe dla modelu LLM, a selektor dynamiczny jedynie dobiera instrukcje adekwatne do sygnałów sceny.
- **Z4 (Instance-Free Metalinguistic Architecture):** wszystkie wzorce regularne w selektorze operują wyłącznie na kategoriach językowych, sufiksach gramatycznych i markerach rejestru.
- **Z16 (Ochrona Depuracji Legacy 1.0):** całkowity zakaz modyfikacji `test_system.py`, `tests/archive/`, 3 gałęzi `# DEFENSIVE_FALLBACK` w `avt_linter.py`, `pytest.ini` oraz historycznych nagłówków w stałej `TRANSLATION_RULES_PROMPT` wymaganych przez `test_system.py`.

---

## FAZA 0 — CZYTANIE KODU I WERYFIKACJA PRZED ZMIANAMI (OBOWIĄZKOWA)

Przed przystąpieniem do jakichkolwiek modyfikacji agent kodujący ma obowiązek przeczytać następujące pliki i uruchomić komendy diagnostyczne:

### P0.1. Pliki do przeczytania
1. `Artefakty/Raport_audytu_filarow.md` — sekcje 3–9 (mapa treści, tabela 22 duplikatów `D-1..D-22`, tabela 5 sprzeczności `S-1..S-5`, tabela precyzji triggerów P5.2 oraz mapa konsolidacji P6.2).
2. `rules.py` — w szczególności `STANDARD_9_CORE_RULES_PROMPT` (linie `2525–2685`) oraz pełną funkcję `get_focused_rules_for_batch` (linie `2688–3520`).
3. `profiler.py` — funkcję `format_lean_episode_brief` i sekcję `TOPOLOGIA SCENY I OCHRONA PŁCI`.
4. `translator.py` oraz `verifier.py` — miejsca wywołania `get_focused_rules_for_batch` i wstrzykiwania `focused_rules_str`.
5. `avt_linter.py` — potwierdzenie, które numery Filarów są używane jako etykiety logów w `EpisodeQualityGate`.
6. `verify_purity.py` oraz `tests/test_profiler.py` — sprawdzenie istniejących bramek czystości metajęzykowej i testów selektora.

### P0.2. Komendy diagnostyczne Fazy 0
1. Sprawdzenie wszystkich asercji w `test_system.py` oraz `tests/` odwołujących się do `get_focused_rules_for_batch` i numerów `FILAR`:
   `grep -rn "get_focused_rules_for_batch\|FILAR " tests/ test_system.py`
2. Sprawdzenie aktualnej liczby bloków warunkowych w `get_focused_rules_for_batch`:
   `grep -n "SKUP SIĘ NA: FILAR" rules.py`
3. Sprawdzenie słów negatywnych lub wielkich liter wewnątrz `get_focused_rules_for_batch`:
   `sed -n '2688,$p' rules.py | grep -nE "NIE|Niedopuszczalne|unikaj|zamiast|ZAWSZE|KONSEKWENTNIE"`

---

## SEKCJA 1 — NOWA STRUKTURA 12 KATEGORII WYKONAWCZYCH AVT

Nowa architektura wykonawcza dzieli się na **4 Kategorie Bazowe** (w `STANDARD_9_CORE_RULES_PROMPT`, bez zmian w numeracji `R1.1–R1.11` i `R3.1–R3.5`) oraz **8 Kategorii Dynamicznych** w `get_focused_rules_for_batch` (lub **10**, jeśli użytkownik zdecyduje o rozdzieleniu `DYN_7` i `DYN_8`).

### 1.1. Kategorie `AUTORYTATYWNE` (wdrażane obligatoryjnie)

| Nowa Kategoria | Zastępowane / Scalane Filary | Rola w architekturze | Zasada zachowania kompatybilności nagłówka |
| :--- | :--- | :--- | :--- |
| **`[KATEGORIA_BASE_1]`** | `R1.1–R1.4` *(zastępuje w selektorze `FILAR LXV` oraz `FILAR XCII & XCIII`)* | Stały rdzeń składni mówionej, szyku rematycznego, pro-dropu, werbalizacji i dopełniacza negacji w `STANDARD_9_CORE_RULES_PROMPT`. | Pozostaje w `STANDARD_9_CORE_RULES_PROMPT`; z `get_focused_rules_for_batch` znikają duplikujące wpisy `LXV` i `XCII & XCIII`. |
| **`[KATEGORIA_BASE_2]`** | `R1.7–R1.9` *(zastępuje w selektorze `FILAR CXII` oraz `FILAR LXXI`)* | Stały rdzeń zwięzłości AVT (`CPS/CPL`), rytmu wypowiedzi i ekonomii słowa w `STANDARD_9_CORE_RULES_PROMPT`. | Pozostaje w `STANDARD_9_CORE_RULES_PROMPT`; z `get_focused_rules_for_batch` znikają wpisy `CXII` oraz `LXXI`. |
| **`[KATEGORIA_BASE_3]`** | `R1.5–R1.6`, `R3.1–R3.5` *(zastępuje w selektorze `FILAR CLXXI` oraz duplikaty w `profiler.py`)* | Stały rdzeń spójności płci P0, adresata, wołacza, cytatów i liczebników w `STANDARD_9_CORE_RULES_PROMPT`. | Pozostaje w `STANDARD_9_CORE_RULES_PROMPT`; z `get_focused_rules_for_batch` znika wpis `CLXXI`. |
| **`[KATEGORIA_BASE_4]`** | `R1.10–R1.11` *(zastępuje w selektorze `FILAR LXXXIV & LXXXV`)* | Stały rdzeń formatowania ASS, kursywy myśli i wielokropków w `STANDARD_9_CORE_RULES_PROMPT`. | Pozostaje w `STANDARD_9_CORE_RULES_PROMPT`; z `get_focused_rules_for_batch` znika wpis `LXXXIV & LXXXV`. |
| **`[KATEGORIA_DYN_1]`** (Priorytet: `95`) | `FILAR XIII` + `FILAR XII` + `FILAR CVI–CXI` | Dialekty regionalne, gwara, sociolekty młodzieżowe, tiki werbalne oraz kontrast rejestrów przy parafrazie wewnątrzscenicznej. | Nagłówek wpisu zachowuje oznaczenie `FILAR XIII & XII`, zapewniając pełną zgodność z testami `T10.1.1_P2a`. |
| **`[KATEGORIA_DYN_2]`** (Priorytet: `92`) | `FILAR XIV` + `FILAR XXX` | Archaizacja, etykieta dworska, rejestr wysoki, sakralny i mowa mędrców/starców. | Nagłówek wpisu zachowuje oznaczenie `FILAR XIV & XXX`. |
| **`[KATEGORIA_DYN_3]`** (Priorytet: `84`) | `FILAR XXV, XXVI, XXVII, XXVIII, XXIX` + `FILAR CLVII` | Kompleksowa adaptacja honoryfikatorów (`-san`, `-sama`, `-sensei`, `-senpai`), zasada `yobisute` oraz jednolitość rejestru adresatywnego w scenie. | Nagłówek wpisu łączy oznaczenia `FILAR XXV, XXVI, XXVII, XXVIII, XXIX & CLVII` w pojedynczy slot selektora. |
| **`[KATEGORIA_DYN_4]`** (Priorytet: `88`) | `FILAR CXXXVI` + `FILAR XCVI` + `FILAR XV` | Triangulacja wieku i płci przy nietypowym F0 (chłopiec z wysokim F0, starsza kobieta z niskim F0), rejestr dziecięcy oraz rodzaj niemęskoosobowy grup kobiecych (`kanojo-tachi`). | Nagłówek wpisu łączy oznaczenia `FILAR CXXXVI, XCVI & XV` w pojedynczy slot selektora. |
| **`[KATEGORIA_DYN_5]`** (Priorytet: `76`) | `FILAR CLXXII` + `FILAR LXVI` + `FILAR LXXV` + `FILAR XVI, XVII, XVIII & XXXIII` | Ekspresja skrajnego afektu głosu seiyū (szloch, panika, drżenie), krótkie takty oddechowe w walce, szczyt F0 oraz somatyczne oddawanie okrzyków wysiłkowych (`kakegoe`/`ottotto`). | Nagłówek wpisu łączy oznaczenia `FILAR CLXXII, LXVI, LXXV, XVIII, XXXIII, XVI & XVII` w pojedynczy slot selektora, po usunięciu słów o „polszczyźnie bezterminowej” i „usuwaniu napisu”. |
| **`[KATEGORIA_DYN_6]`** (Priorytet: `80`) | `FILAR CLXV` + `FILAR CLXIX` + `FILAR CLXXIX` | Ciągłość składniowa zdań rozbitych na dwa sąsiednie zdarzenia ASS, płynne wejścia po przeskokach scen oraz naturalne pary przylegania w krótkich ripostach. | Nagłówek wpisu łączy oznaczenia `FILAR CLXV, CLXIX & CLXXIX`. |

### 1.2. Kategorie `[WYMAGA DECYZJI UŻYTKOWNIKA]`

| Nowa Kategoria | Zastępowane / Scalane Filary | Rola w architekturze | Warunek wdrożenia |
| :--- | :--- | :--- | :--- |
| **`[KATEGORIA_DYN_7]`** (Priorytet: `72`) | `FILAR XLIX, L & LI` + `FILAR LIV, LV & LVI` | Skonsolidowany rejestr specjalistyczny dla scen taktyczno-bojowych, sportowych, medycznych, naukowych i dedukcji śledczych. | Scalić w jeden blok z nagłówkiem `FILAR XLIX, L, LI, LIV, LV & LVI` po zatwierdzeniu przez użytkownika (w razie braku decyzji zachować jako 2 osobne bloki w czystej domenie pozytywnej). |
| **`[KATEGORIA_DYN_8]`** (Priorytet: `70`) | `FILAR LX & LXI` + `FILAR CIV & CV` + `FILAR CXVIII & CXIX` + `FILAR LXXVIII & LXXIX` | Skonsolidowana adaptacja kulturowo-wizualna: gry słowne (`dajare`), onomatopeje w dialogu (`giongo`), kulinaria/realia oraz zwięzłe napisy ekranowe (`signs`). | Scalić w jeden blok z nagłówkiem `FILAR LXXVIII, LXXIX, LX, LXI, CIV, CV, CXVIII & CXIX` po zatwierdzeniu przez użytkownika (w razie braku decyzji zachować jako osobne bloki w czystej domenie pozytywnej). |

---

## SEKCJA 2 — OPERACJE IMPLEMENTACYJNE

### Podsekcja 2A — Operacje `AUTORYTATYWNE` (obligatoryjne)

#### Operacja `2B.1` — Usunięcie 6 nadmiarowych bloków duplikujących `STANDARD_9_CORE_RULES_PROMPT` z selektora dynamicznego
- **Finding:** `D-1`, `D-2`, `D-3`, `D-9`, `D-10` z FAZY 2 raportu audytu.
- **Lokalizacja:** `rules.py` — wnętrze funkcji `get_focused_rules_for_batch` (linie `2605–3025`).
- **Instrukcja:** Usuń z funkcji `get_focused_rules_for_batch` niezależne bloki warunkowe generujące wpisy dla: (1) `FILAR LXV` (szyk rematyczny), (2) `FILAR XCII & XCIII` (dopełniacz negacji), (3) `FILAR CXII` (zwięzłość krótkich kwestii), (4) `FILAR LXXI` (eliminacja tarcia leksykalnego), (5) `FILAR LXXXIV & LXXXV` (monolog wewnętrzny), (6) `FILAR CLXXI` (zgodność liczebników). Wszystkie 6 zagadnień znajduje się już w zawsze aktywnym `STANDARD_9_CORE_RULES_PROMPT` (`R1.1`, `R1.4`, `R1.7`, `R1.11`, `R3.5`). Sprawdź w Fazie 0 (`P0.2` komenda 1), czy żaden zamrożony test w `test_system.py` nie wywołuje bezpośrednio `get_focused_rules_for_batch` z asercją na te 6 numerów — jeśli jakikolwiek test w `test_system.py` wymaga obecności danego identyfikatora rzymskiego przy specyficznym wejściu, dołącz ten identyfikator rzymski do nagłówka odpowiedniej skonsolidowanej kategorii `DYN_1–DYN_6`.
- **Oczekiwany efekt:** Zwykłe zdania zawierające wielokropek, przeczenie lub liczbę przestają zaśmiecać sekcję `SKONCENTROWANA UWAGA DLA TEJ SCENY`.
- **Test regresyjny:** `T10.2_1` w SEKCJI 4.

#### Operacja `2B.2` — Konsolidacja aktywnych bloków dynamicznych do 6 Kategorii Rdzeniowych (`DYN_1` – `DYN_6`)
- **Finding:** `D-4`, `D-5`, `D-6`, `D-7`, `D-8`, `D-12` z FAZY 2 oraz `XII`, `XV`, `CVI`, `CLXXIX` z FAZY 4 raportu audytu.
- **Lokalizacja:** `rules.py` — wnętrze funkcji `get_focused_rules_for_batch`.
- **Instrukcja:** Połącz nakładające się bloki warunkowe w 6 rozłącznych kategorii dynamicznych (`[KATEGORIA_DYN_1]` do `[KATEGORIA_DYN_6]`) zgodnie z tabelą w SEKCJI 1.1:
  1. W `DYN_1` połącz `FILAR XIII` z `FILAR XII` (sociolekty młodzieżowe) i tikami słownymi maskotek (`CVI–CXI`).
  2. W `DYN_2` zachowaj połączony blok `FILAR XIV & XXX`.
  3. W `DYN_3` połącz w jeden wpis trzy dotychczasowe bloki honoryfikatywne: `FILAR XXV, XXVII & XXVIII`, `FILAR XXVI & XXIX` oraz `FILAR CLVII`.
  4. W `DYN_4` połącz w jeden wpis `FILAR CXXXVI`, `FILAR XCVI` oraz `FILAR XV`.
  5. W `DYN_5` połącz w jeden wpis cztery dotychczasowe bloki prozodyczno-afektywne: `FILAR CLXXII`, `FILAR LXVI`, `FILAR LXXV` oraz `FILAR XVIII, XXXIII, XVI & XVII`.
  6. W `DYN_6` połącz `FILAR CLXV & CLXIX` z `FILAR CLXXIX`.
- **Oczekiwany efekt:** Żadna kategoria semantyczna (np. honoryfikatory lub prozodia walki) nie może już zająć więcej niż 1 slotu z puli `max_rules=3`.
- **Test regresyjny:** `T10.2_2` w SEKCJI 4.

#### Operacja `2B.3` — Przepisanie wszystkich kategorii w `get_focused_rules_for_batch` na czystą domenę pozytywną (Z1/Z2/Z4) oraz rozszerzenie `Anti-Smoothing Filter`
- **Finding:** `S-1`, `S-2`, `S-4`, `S-5` z FAZY 3 raportu audytu.
- **Lokalizacja:** `rules.py` — teksty wszystkich kategorii w `get_focused_rules_for_batch` oraz blok `Anti-Smoothing Filter`.
- **Instrukcja:**
  1. Zredaguj teksty wszystkich kategorii w `get_focused_rules_for_batch` tak, aby spełniały w 100% wymogi `verify_purity.py`: zero słów negatywnych i preskryptywnych (usuń wszystkie wystąpienia `NIE`, `nie`, `Niedopuszczalne`, `unikaj`, `zamiast`, `zakaz`, `błąd`, `musi`, `zawsze`, `nigdy`), zero skrótów `np.`, zero cytowanych dialogów w cudzysłowach/apostrofach, zero słów pisanych wersalikami ALL-CAPS wewnątrz zdania opisowego.
  2. W `DYN_5` (dawny `FILAR XVIII` i `FILAR CLXXII`) usuń frazę sugerującą zwracanie pustego napisu (`S-4`) oraz usuń frazę o „polszczyźnie bezterminowej” (`S-1`/`S-2`), skupiając opis wyłącznie na afekcie głosu seiyū, rytmie oddechu i somatycznych okrzykach wysiłkowych.
  3. Rozszerz `Anti-Smoothing Filter` na końcu `get_focused_rules_for_batch` tak, aby chronił zarówno `DYN_1` (`FILAR XIII`), jak i `DYN_2` (`FILAR XIV & XXX`) przed jakimikolwiek regułami wygładzającymi rejestr.
- **Oczekiwany efekt:** Cała funkcja `get_focused_rules_for_batch` przechodzi rygor czystości metajęzykowej Z1/Z2/Z4 i jest wolna od wewnętrznych sprzeczności.
- **Test regresyjny:** `T10.2_3` w SEKCJI 4.

#### Operacja `2B.4` — Zaostrzenie triggerów i ustanowienie nowej hierarchii priorytetów w `get_focused_rules_for_batch`
- **Finding:** `P5.2` z FAZY 5 oraz `P6.3` z FAZY 6 raportu audytu.
- **Lokalizacja:** `rules.py` — warunki regularne i wartości punktowe `score` w `get_focused_rules_for_batch`.
- **Instrukcja:**
  1. W `DYN_1` (`en_slang_pat` / `paraphrase_pat`): usuń ze wzorca angielskiego pospolite czasowniki potoczne `gonna`, `wanna`, `gotta` (zachowując jednoznaczne markery gwary/slangu: `ain't`, `y'all`, `'em`, `nah`, `whoever they be`, `'cause`, wielokrotne gerundia z apostrofem `\w+in'` oraz markery subkulturowe), a we wzorcu `paraphrase_pat` wymagaj konstrukcji relacjonującej czyjąś wypowiedź (np. połączenia z 3. osobą lub cudzysłowu parafrazy), aby zwykłe pytanie o znaczenie słowa nie wyzwalało gwary.
  2. W `DYN_4` (dawny `XCVI` + `CXXXVI`): usuń ze wzorca angielskiego ogólne zaimki `they`, `them`, `their` (które dopasowują się do przedmiotów), pozostawiając jawne rzeczowniki zbiorowości kobiecej, markery japońskie `kanojo-tachi` oraz markery wieku/roli (`boy`, `kid`, `child`, `grandma`, `matron`, `shonen`).
  3. W `DYN_5` (Afekt / Walka / Somatyka): usuń wyzwalanie na pojedynczym wykrzykniku `!` lub zwykłym `eh`/`ah`; wymagaj co najmniej gęstej koncentracji wykrzykników w paczce, jawnych słów szlochu/paniki/walki lub obecności somatycznych okrzyków wysiłkowych (`ottotto`, `kakegoe`, `ugh`, `grr`, `pant`, `gasp`).
  4. Ustaw jednoznaczną hierarchię `score` zgodnie z SEKCJĄ 1 (`DYN_1: 95`, `DYN_2: 92`, `DYN_4: 88`, `DYN_3: 84`, `DYN_6: 80`, `DYN_5: 76`, `DYN_7: 72`, `DYN_8: 70`).
  5. Dla paczki zwykłego dialogu, w której żaden z wyspecjalizowanych warunków nie został spełniony, funkcja ma zwracać pusty ciąg znaków `""`.
- **Oczekiwany efekt:** Selektor wybiera wyłącznie kategorie rzeczywiście obecne w scenie i zwraca `""` dla standardowych dialogów.
- **Test regresyjny:** `T10.2_1` oraz `T10.2_2` w SEKCJI 4.

#### Operacja `2B.5` — Usunięcie duplikacji reguł bazowych z `format_lean_episode_brief` w `profiler.py`
- **Finding:** `D-15` z FAZY 2 oraz `F0.10` z FAZY 0 raportu audytu.
- **Lokalizacja:** `profiler.py` — funkcja `format_lean_episode_brief` (sekcja `TOPOLOGIA SCENY I OCHRONA PŁCI`).
- **Instrukcja:** Odchudź statyczną stopkę doklejaną na końcu `format_lean_episode_brief` w `profiler.py`, usuwając z niej powtórzenie pełnej reguły `Dopełniacza Negacji` (`R1.4`) oraz ogólnych opisów gramatycznych duplikujących `STANDARD_9_CORE_RULES_PROMPT`, a pozostawiając w `EPISODE BRIEF` wyłącznie zwięzłe dane specyficzne dla danego odcinka (gatunek, rejestr, postacie, formy adresatywne, paradygmaty odmiany imion i zablokowaną terminologię). Sprawdź w Fazie 0, czy żaden test w `tests/test_profiler.py` lub `test_system.py` nie sprawdza usuniętego zdania — jeśli jakikolwiek test sprawdza obecność określonej frazy nagłówkowej w `format_lean_episode_brief`, zachowaj sam jednozdaniowy nagłówek kompatybilności.
- **Oczekiwany efekt:** Eliminacja podwójnego przesyłania tych samych reguł gramatycznych w prompcie systemowym i w `EPISODE BRIEF`.
- **Test regresyjny:** Istniejący pakiet `tests/test_profiler.py` + `T10.2_3`.

#### Operacja `2B.6` — Rozszerzenie weryfikacji czystości domenowej (Z1/Z2/Z4) na wyjście `get_focused_rules_for_batch`
- **Finding:** `S-5` z FAZY 3 oraz rekomendacja `P2` z FAZY 7 raportu audytu.
- **Lokalizacja:** `verify_purity.py` oraz `tests/test_profiler.py`.
- **Instrukcja:** Dodaj w `tests/test_profiler.py` (oraz opcjonalnie jako dodatkową kontrolę w `verify_purity.py` bez zmiany licznika 12 komunikatów `[PASS]`, lub wewnątrz istniejącej Bramki 5B) weryfikację gwarantującą, że żadna z kategorii zwracanych przez `get_focused_rules_for_batch` nie zawiera słów negatywnych (`nie`, `zakaz`, `unikaj`, `zamiast`, `niedopuszczalne`), skrótu `np.`, cytowanych dialogów w apostrofach ani nazw własnych.
- **Oczekiwany efekt:** Trwała blokada regresji Z1/Z2/Z4 w dynamicznym selektorze Filarów.
- **Test regresyjny:** `T10.2_3` w SEKCJI 4.

---

### Podsekcja 2B — Operacje `[WYMAGA DECYZJI UŻYTKOWNIKA]`

**UWAGA DLA AGENTA KODUJĄCEGO:** Przed wdrożeniem poniższych dwóch operacji (`2B.7` i `2B.8`) sprawdź, czy użytkownik zatwierdził je w wiadomości zlecającej. Jeśli użytkownik zatwierdził cały prompt bez zastrzeżeń — wdróż je razem z Podsekcją 2A. Jeśli użytkownik nakazał pominięcie operacji warunkowych — pozostaw te bloki jako osobne kategorie (po przepisaniu ich treści na czystą domenę pozytywną zgodnie z `2B.3`) i odnotuj to w raporcie wdrożenia.

#### Operacja `2B.7` `[WYMAGA DECYZJI UŻYTKOWNIKA]` — Konsolidacja rejestrów specjalistycznych (`XLIX–LI` + `LIV–LVI` → `DYN_7`)
- **Finding:** `D-13` z FAZY 2 raportu audytu.
- **Lokalizacja:** `rules.py` — `get_focused_rules_for_batch`.
- **Instrukcja:** Połącz dwa bloki rejestrów specjalistycznych (`FILAR XLIX, L & LI` — żargon bojowy/sportowy oraz `FILAR LIV, LV & LVI` — rejestr medyczno-śledczy) w jedną skonsolidowaną kategorię `[KATEGORIA_DYN_7]` o priorytecie `72` i nagłówku `FILAR XLIX, L, LI, LIV, LV & LVI - Rejestry Specjalistyczne: Taktyczno-Bojowy, Medyczny i Śledczy`.
- **Test regresyjny:** `T10.2_2` w SEKCJI 4.

#### Operacja `2B.8` `[WYMAGA DECYZJI UŻYTKOWNIKA]` — Konsolidacja adaptacji kulturowej i napisów (`LX–LXI` + `CIV–CV` + `CXVIII–CXIX` + `LXXVIII–LXXIX` → `DYN_8`)
- **Finding:** `D-11` oraz `D-14` z FAZY 2 raportu audytu.
- **Lokalizacja:** `rules.py` — `get_focused_rules_for_batch`.
- **Instrukcja:** Połącz cztery rzadkie bloki kulturowo-wizualne (kalambury `LX & LXI`, onomatopeje `CIV & CV`, kulinaria `CXVIII & CXIX` oraz napisy ekranowe `LXXVIII & LXXIX`) w jedną skonsolidowaną kategorię `[KATEGORIA_DYN_8]` o priorytecie `70` i nagłówku `FILAR LXXVIII, LXXIX, LX, LXI, CIV, CV, CXVIII & CXIX - Adaptacja Kulturowa, Kalambury, Onomatopeje i Napisy Ekranowe`.
- **Test regresyjny:** `T10.2_2` w SEKCJI 4.

---

## SEKCJA 3 — NOWA LOGIKA SELEKCJI W `get_focused_rules_for_batch`

Funkcja `get_focused_rules_for_batch` w `rules.py` ma działać według następującego algorytmu:
1. **Normalizacja wejścia (kompatybilna wstecz):** Funkcja przyjmuje dotychczasowe argumenty (`batch_items_or_text`, `max_rules: Optional[int] = None`, `batch_text_en: Optional[str] = None`, `whisper_text_jp: str = ""`), łącząc teksty angielskie oraz transkrypcje japońskie z paczki. Domyślny limit `max_rules` przy wartości `None` wynosi `3`.
2. **Ewaluacja wyłącznie 8 wysokoprogowych Kategorii Dynamicznych (`DYN_1` – `DYN_8`):**
   - `DYN_1` (`score = 95`): aktywowana wyłącznie przy jednoznacznych markerach gwary/slangu EN, dialektu JP lub konstrukcji parafrazującej słowa innej postaci w cudzysłowie.
   - `DYN_2` (`score = 92`): aktywowana wyłącznie przy markerach archaizacji, tytulatury dworskiej/królewskiej lub japońskich zaimków starczych/archaicznych (`washi`, `sessha`, `warawa`, `onushi`, `gozaru`).
   - `DYN_4` (`score = 88`): aktywowana przy markerach wieku/roli wrażliwej na F0 (chłopiec, dziecko, staruszka, matrona) lub jawnej grupie kobiecej (`kanojo-tachi`).
   - `DYN_3` (`score = 84`): aktywowana przy wystąpieniu japońskich honoryfikatorów (`-san`, `-sama`, `-kun`, `-chan`, `-sensei`, `-senpai`) lub zwrotów hierarchicznych w dialogu.
   - `DYN_6` (`score = 80`): aktywowana przy wystąpieniu zdań rozbitych wielokropkiem kontynuacyjnym na styku dwóch kolejnych linii lub dwugłosów dialogowych.
   - `DYN_5` (`score = 76`): aktywowana wyłącznie przy wysokim zagęszczeniu ekspresji afektywnej/bojowej, znacznikach drżenia/załamania głosu z DSP lub somatycznych okrzykach wysiłkowych (`ottotto`, `kakegoe`).
   - `DYN_7` (`score = 72`): aktywowana przy słownictwie taktyczno-bojowym, sportowym, medycznym lub śledczym.
   - `DYN_8` (`score = 70`): aktywowana przy napisach ekranowych (`is_sign`), grach słownych, onomatopejach lub realiach kulinarnych.
3. **Rozszerzony `Anti-Smoothing Filter`:** Jeśli na liście kandydatów znajduje się `DYN_1` (`FILAR XIII`) lub `DYN_2` (`FILAR XIV & XXX`), wszelkie reguły wygładzające rejestr są wykluczane.
4. **Czysty Fallback:** Jeśli żaden z powyższych 8 warunków nie zostanie spełniony (zwykła rozmowa bez specyficznych zjawisk), funkcja zwraca pusty string `""` (0 nadmiarowych Filarów dynamicznych).

---

## SEKCJA 4 — WALIDACJA TESTOWA (NOWE TESTY REGRESYJNE)

Dodaj w `tests/test_profiler.py` trzy nowe, sparametryzowane testy jednostkowe (`@pytest.mark.unit`, `@pytest.mark.parametrize` z minimum 3 wariantami każdy, w 100% zgodne z Zero-Literal):

1. **`T10.2_1` — `test_focused_rules_zero_noise_on_ordinary_dialogue_batches`:**
   - Weryfikuje, że dla zwykłych zdań dialogowych zawierających wielokropek (`...`), spójnik `but`, przeczenie `not`/`don't`, pojedynczy wykrzyknik `!`, zaimek `they` odnoszący się do przedmiotów lub zwykłą liczbę (np. `"I don't know, but they have 3 items..."`), funkcja `get_focused_rules_for_batch` zwraca pusty string `""` (lub nie zwraca usuniętych duplikatów `FILAR LXV`, `FILAR XCII`, `FILAR CXII`, `FILAR LXXI`, `FILAR CLXXI`).
2. **`T10.2_2` — `test_focused_rules_consolidated_categories_and_priority_order`:**
   - Weryfikuje, że dla poszczególnych zjawisk specjalnych aktywowane są właściwe skonsolidowane kategorie (`DYN_1` dla gwary/slangu, `DYN_2` dla archaizacji/dworskości, `DYN_3` dla honoryfikatorów, `DYN_4` dla wieku/płci/grupy kobiecej, `DYN_5` dla somatycznych okrzyków walki), oraz że przy jednoczesnym wystąpieniu gwary (`DYN_1`, score 95) i niższych kategorii, `DYN_1` zajmuje pierwsze miejsce na liście.
3. **`T10.2_3` — `test_all_focused_rules_outputs_satisfy_pure_positive_domain_and_zero_literal`:**
   - Wywołuje `get_focused_rules_for_batch` z syntetycznymi wejściami aktywującymi wszystkie 8 kategorii dynamicznych (`DYN_1` – `DYN_8`) przy `max_rules=10` i weryfikuje, że zwrócony tekst: (a) nie zawiera słów przeczących i zakazujących (`\bnie\b`, `\bzakaz\b`, `\bunikaj\b`, `\bzamiast\b`, `\bniedopuszczalne\b`, `\busuń\b`), (b) nie zawiera skrótu `\bnp\.`, (c) nie zawiera cytowanych dialogów w apostrofach `'...'`, (d) nie zawiera żadnych nazw własnych z audytowanych serii.

---

## SEKCJA 5 — WARUNKI UKOŃCZENIA (a)–(n)

- **(a)** Przeczytano wszystkie pliki z Fazy 0 (`P0.1`) oraz wykonano 3 komendy diagnostyczne (`P0.2`), zapisując ich surowe wyjścia w Sekcji 0 raportu wdrożenia.
- **(b)** Z funkcji `get_focused_rules_for_batch` w `rules.py` usunięto 6 nadmiarowych bloków duplikujących `STANDARD_9_CORE_RULES_PROMPT` (`Operacja 2B.1`).
- **(c)** Skonsolidowano aktywne bloki w `get_focused_rules_for_batch` do maksymalnie 8 rozłącznych Kategorii Dynamicznych (`DYN_1` – `DYN_8`) z zachowaniem identyfikatorów rzymskich w nagłówkach (`Operacja 2B.2`, `2B.7`, `2B.8`).
- **(d)** Wszystkie teksty zwracane przez `get_focused_rules_for_batch` są w 100% w czystej domenie pozytywnej (Z2), bez literałów (Z1/Z4), bez `np.` i bez cytatów w apostrofach (`Operacja 2B.3`).
- **(e)** Rozszerzono `Anti-Smoothing Filter` na `DYN_2` (`FILAR XIV & XXX`) oraz zaostrzono triggery w `get_focused_rules_for_batch`, uzyskując pusty zwrot `""` dla zwykłych zdań dialogowych (`Operacja 2B.3`, `2B.4`).
- **(f)** Odchudzono `format_lean_episode_brief` w `profiler.py` z powtórzeń reguł bazowych (`Operacja 2B.5`).
- **(g)** Stała `TRANSLATION_RULES_PROMPT` w `rules.py` pozostała nienaruszona jako pasywne archiwum Z16 dla `test_system.py`.
- **(h)** Wszystkie 3 nowe testy regresyjne (`T10.2_1`, `T10.2_2`, `T10.2_3`) oraz 4 testy z `10.1.1` (`T10.1.1_P1a..P2b`) przechodzą w 100%.
- **(i)** Pakiet `pytest tests/ -q` przechodzi w 100% (`0 failed`).
- **(j)** Pełny pakiet `pytest -q` przechodzi w 100% (`0 failed`, `153 deselected`).
- **(k)** Wszystkie 4 bramki kwalifikacyjne CI/CD (`verify_purity.py`, `verify_12_fixes.py`, `verify_ultimate_pipeline.py`, `audit_diff.ps1`) zwracają `PASS`.
- **(l)** Zasada Z16 zachowana w 100% (`git diff 474fb64..HEAD -- test_system.py tests/archive/ pytest.ini` wykazuje wyłącznie zatwierdzony wcześniej hotfix `10.0.4` w linii 19585 `test_system.py` i `0` nowych zmian; 3 gałęzie `# DEFENSIVE_FALLBACK` w `avt_linter.py` nienaruszone).
- **(m)** Wszystkie 20 realnych bibles w `series_memory/*_bible.json` pozostają w 100% nienaruszone (`git status series_memory/` czysty).
- **(n)** Zapisano kompletny raport `Artefakty/Raport_wdrozenia_10.2.md` (0 placeholderów `<DO_WYPEŁNIENIA>`), wykonano commit i push na `origin/main`, a `git status` jest czysty.

---

## SEKCJA 6 — ZAKAZY

1. **ZAKAZ 1 (Z16 — Ochrona Depuracji Legacy 1.0):** Bezwzględny zakaz modyfikacji `test_system.py`, `tests/archive/`, 3 gałęzi `# DEFENSIVE_FALLBACK` w `avt_linter.py` oraz `pytest.ini`.
2. **ZAKAZ 2 (Ochrona Archiwum `TRANSLATION_RULES_PROMPT`):** Nie usuwaj i nie zmieniaj nagłówków `FILAR I` – `FILAR CLXXX` wewnątrz pasywnej stałej `TRANSLATION_RULES_PROMPT` w `rules.py` — są one wymagane przez zamrożone testy w `test_system.py`. Minimalizacja dotyczy aktywnego selektora `get_focused_rules_for_batch` oraz `profiler.py`.
3. **ZAKAZ 3 (Z1 / Zero-Literal):** W kodzie produkcyjnym, w opisach kategorii w `rules.py` oraz w testach `tests/test_*.py` obowiązuje całkowity zakaz używania konkretnych nazw własnych z anime.
4. **ZAKAZ 4 (Z2 / Pure Positive Domain i `verify_purity.py`):** W opisach kategorii w `rules.py` obowiązuje całkowity zakaz używania słów przeczących (`nie`, `zakaz`, `zabrania się`, `unikaj`, `zamiast`, `niedopuszczalne`, `błąd`, `usuń`), skrótu `np.`, cytowanych zdań w apostrofach/cudzysłowach oraz słów ALL-CAPS wewnątrz treści reguły.
5. **ZAKAZ 5 (Z3 / Primary LLM Authority):** Selektor `get_focused_rules_for_batch` służy wyłącznie do doboru instrukcji metajęzykowych dla modelu LLM — zakaz dodawania deterministycznych podmian tekstu poza domeną pozytywną `D_pos`.
6. **ZAKAZ 6 (Z4 / Instance-Free):** Wszystkie wzorce regularne w `get_focused_rules_for_batch` muszą operować wyłącznie na kategoriach językowych, sufiksach i markerach rejestru, bez hardkodowania imion lub tytułów serii.
7. **ZAKAZ 7 (Ochrona `STANDARD_9_CORE_RULES_PROMPT`):** Nie usuwaj żadnej z 16 reguł `R1.1–R1.11` ani `R3.1–R3.5` z `STANDARD_9_CORE_RULES_PROMPT`.
8. **ZAKAZ 8 (Ochrona `series_memory/`):** Nie modyfikuj żadnego z 20 plików `series_memory/*_bible.json` ani 42 plików `series_memory/fansub_lexicons/*.json`.
9. **ZAKAZ 9 (Obsługa operacji warunkowych):** Operacje oznaczone `[WYMAGA DECYZJI UŻYTKOWNIKA]` (`2B.7` i `2B.8`) wdrażaj zgodnie z dyspozycją użytkownika; w przypadku braku zgody na konsolidację `DYN_7`/`DYN_8` zachowaj je jako osobne bloki po oczyszczeniu ich języka zgodnie z `2B.3` i zaraportuj w `Raport_wdrozenia_10.2.md`.
10. **ZAKAZ 10 (Brak placeholderów):** W finalnym `Artefakty/Raport_wdrozenia_10.2.md` nie może pozostać ani jeden znacznik `<DO_WYPEŁNIENIA>`.

---

## SEKCJA 7 — UWAGI KRYTYCZNE (KNOWN RISKS Z AUDYTU)

1. **`R1` — Ryzyko niezgodności nagłówków z istniejącymi testami w `test_system.py` lub `tests/`:**
   - **Opis:** Istniejące testy jednostkowe mogą sprawdzać obecność konkretnego numeru rzymskiego (np. `"FILAR XIII"`, `"FILAR CXXXVI"`, `"FILAR CLVII"`) w stringu zwracanym przez `get_focused_rules_for_batch`.
   - **Mitygacja:** W nagłówkach wszystkich 8 skonsolidowanych Kategorii Dynamicznych (`DYN_1` – `DYN_8`) zachowaj jawne numery rzymskie scalanych Filarów (np. `[SKUP SIĘ NA: FILAR XIII & XII - ...]`, `[SKUP SIĘ NA: FILAR XXV, XXVI, XXVII, XXVIII, XXIX & CLVII - ...]`).
2. **`R2` — Ryzyko nadmiernego wyciszenia selektora dla istotnych scen (False Negatives):**
   - **Opis:** Zbyt wąskie wyrażenie regularne mogłoby pominąć scenę wymagającą stylizacji gwarowej, dworskiej lub ochrony wieku/płci.
   - **Mitygacja:** Zachowaj wszystkie zweryfikowane w `10.1.1` markery gwary EN/JP oraz markery archaizacji i wieku/płci, usuwając wyłącznie pospolite słowa ogólnojęzykowe (`gonna`, `wanna`, `gotta`, `but`, `not`, `they`, pojedynczy znak `!` i `...`).
3. **`R3` — Ryzyko wygładzenia rejestru archaicznego/dworskiego (`DYN_2`):**
   - **Opis:** Jeśli w scenie z mową dworską/starczą (`FILAR XIV & XXX`) pojawi się wysoki afekt (`DYN_5`), model mógłby wygładzić archaizmy, gdyby w `DYN_5` pozostał nakaz „polszczyzny bezterminowej”.
   - **Mitygacja:** Operacja `2B.3` usuwa klauzulę „polszczyzny bezterminowej” z `DYN_5` i obejmuje `DYN_2` ochroną `Anti-Smoothing Filter`.
4. **`R4` — Ryzyko utraty niuansu przy scalaniu rejestrów specjalistycznych i kulturowych (`2B.7`, `2B.8`):**
   - **Opis:** Scalenie żargonu bojowego z medyczno-śledczym (`DYN_7`) lub kalamburów z onomatopejami i szyldami (`DYN_8`) łączy różne poddomeny.
   - **Mitygacja:** Obie operacje oznaczono jako `[WYMAGA DECYZJI UŻYTKOWNIKA]`, a sformułowanie skonsolidowanej kategorii wymienia wprost sposób postępowania dla każdego z łączonych zjawisk.
5. **`R5` — Ryzyko naruszenia `verify_purity.py` przy redagowaniu tekstów kategorii:**
   - **Opis:** Użycie pojedynczego słowa `nie`, `zamiast`, `unikaj`, skrótu `np.` lub cudzysłowu w nowym tekście kategorii spowoduje błąd bramki czystości.
   - **Mitygacja:** Obowiązkowy test `T10.2_3` oraz uruchomienie `verify_purity.py` przed commitem.
6. **`R6` — Ryzyko przypadkowej modyfikacji `TRANSLATION_RULES_PROMPT` lub `test_system.py` (Z16):**
   - **Opis:** Usunięcie Filarów z pasywnej stałej `TRANSLATION_RULES_PROMPT` złamałoby testy w `test_system.py`.
   - **Mitygacja:** ZAKAZ 1 i ZAKAZ 2 — `TRANSLATION_RULES_PROMPT` oraz `test_system.py` pozostają nietknięte.

---

## TEMPLATE RAPORTU WDROŻENIA (`Artefakty/Raport_wdrozenia_10.2.md`)

~~~markdown
# RAPORT WDROŻENIA STANDARDU 10.2 (DEDUPLIKACJA I MINIMALIZACJA FILARÓW AVT)

## 0. DIAGNOSTYKA WSTĘPNA (FAZA 0)
- **Surowe wyjścia 3 komend diagnostycznych (P0.2):** `<wklej surowe wyjścia>`
- **Potwierdzenie stanu wejściowego (`81de7b5`):** `<opis>`

## 1. METADANE GIT
- **Commit bazowy:** `81de7b5`
- **Commit docelowy (10.2):** `<HASH>`

## 2. TABELA REALIZACJI OPERACJI (2B.1 – 2B.8)
| Operacja | Finding | Status (`WDROŻONA` / `POMINIĘTA`) | Lokalizacja (`plik:linie`) | Opis zmiany |
| :---: | :--- | :---: | :--- | :--- |
| `2B.1` | `D-1..D-3, D-9, D-10` | ... | `rules.py:...` | ... |
| `2B.2` | `D-4..D-8, D-12` | ... | `rules.py:...` | ... |
| `2B.3` | `S-1, S-2, S-4, S-5` | ... | `rules.py:...` | ... |
| `2B.4` | `P5.2, P6.3` | ... | `rules.py:...` | ... |
| `2B.5` | `D-15` | ... | `profiler.py:...` | ... |
| `2B.6` | `S-5, P2` | ... | `tests/test_profiler.py:...` | ... |
| `2B.7` | `D-13` | ... | `rules.py:...` | ... |
| `2B.8` | `D-11, D-14` | ... | `rules.py:...` | ... |

## 3. CYTATY KODU PO NAPRAWIE
- Nowa postać `get_focused_rules_for_batch` w `rules.py`
- Odchudzona sekcja w `profiler.py`
- Nowe testy `T10.2_1` – `T10.2_3` w `tests/test_profiler.py`

## 4. WYNIKI 4 BRAMEK KWALIFIKACYJNYCH CI/CD (SUROWE WYJŚCIA)
- `verify_purity.py`: `<surowe wyjście>`
- `verify_12_fixes.py`: `<surowe wyjście>`
- `verify_ultimate_pipeline.py`: `<surowe wyjście>`
- `audit_diff.ps1`: `<surowe wyjście>`

## 5. WYNIKI PYTEST I POTWIERDZENIE NIENARUSZALNOŚCI Z16 ORAZ BIBLES
- `pytest tests/ -q`: `<surowe wyjście>`
- `pytest -q`: `<surowe wyjście>`
- `git diff 81de7b5..HEAD --stat -- series_memory/ test_system.py avt_linter.py pytest.ini`: `<surowe wyjście>`

## 6. CHECKLISTA WARUNKÓW UKOŃCZENIA (a)–(n)
- [x] (a) ... [x] (n)
- **Werdykt końcowy:** `PASS`
~~~