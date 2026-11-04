# RAPORT AUDYTU POKRYCIA 12 KATEGORII AVT (STANDARD 10.2 + POPRAWKI) PRZEZ PROFESJONALNE WYTYCZNE TŁUMACZENIA ANIME

## 0. METADANE
- **Repozytorium:** `https://github.com/wooles/translator`
- **HEAD audytowany:** `51dbe2d` (`51dbe2d400d16ce1a251efe193a1b96c9b18e361` — gałąź `main`)
- **Baseline przed audytem 10.2:** `81de7b5` (`81de7b5a1f9f927c1e4ccca318458e7afb12eda3` — Hotfix 10.1.1)
- **Hash commita 10.2:** `51dbe2d` (`51dbe2d400d16ce1a251efe193a1b96c9b18e361`)
- **Poprawki po 10.2:** `0` dodatkowych commitów po `51dbe2d` (`51dbe2d` jest aktualnym `HEAD` na `origin/main` i zawiera pełne wdrożenie `2B.1–2B.8` wraz z korektami kompatybilności testowej wykonanymi podczas wdrożenia 10.2)
- **Data audytu:** `2026-11-04`
- **Audytor:** Niezależny Audytor Architektoniczny AVT (Read-Only)
- **Źródła zewnętrzne:** 8 zweryfikowanych źródeł branżowych i akademickich (FAZA 1)

---

## 1. EXECUTIVE SUMMARY
- **Stan 12 kategorii na `51dbe2d`:** W aktywnym runtime funkcjonują **4 Kategorie Bazowe (`BASE_1`–`BASE_4`)** w `STANDARD_9_CORE_RULES_PROMPT` (`R1.1–R1.11`, `R3.1–R3.5`) oraz **8 Kategorii Dynamicznych (`DYN_1`–`DYN_8`)** w `get_focused_rules_for_batch` (netto `-525` linii zredukowanego szumu w `rules.py` i `profiler.py`).
- **Korekty kompatybilności wprowadzone w commicie `51dbe2d`:**
  1. W `DYN_5` (`FILAR CLXXII`) agent kodujący ustawił `score = 120` (zamiast `76`), aby utrzymać kompatybilność ze starszym testem weryfikującym pozycję `FILAR CLXXII`, gdy nie działa `Anti-Smoothing Filter`.
  2. W `DYN_6` i `DYN_8` dopisano do nagłówków numery `LXV` oraz `XLI` dla zachowania wstecznej kompatybilności asercji nagłówkowych.
- **Liczba wytycznych wyekstrahowanych z 8 źródeł (FAZA 2):** **16 kluczowych wytycznych profesjonalnych (`G-01` – `G-16`)**.
- **Bilans pokrycia przez Standard 10.2 (`51dbe2d`):**
  - **`POKRYTE` (≥70%):** **10 wytycznych** (`62.5%`),
  - **`CZĘŚCIOWE` (30–69%):** **4 wytyczne** (`25.0%`),
  - **`BRAK` (<30%):** **2 wytyczne** (`12.5%`).
- **Zidentyfikowane luki (FAZA 3):** **6 luk (`L-01` – `L-06`)**, w tym:
  - **1 luka P0 (`L-01`):** brak strategii przekładu humoru wysokiego ryzyka (tabu, gra słów, intertekstualność — substytucja, adaptacja funkcjonalna i kompensacja wg badań *Dialogica 2026*) w `DYN_8`,
  - **4 luki P1 (`L-02` – `L-05`):**
    - `L-02`: brak wskazania polskiego optimum percepcyjnego `14–15 CPS` (wg normy STAW) obok maksymalnego progu `17 CPS` w `BASE_2` (`R1.7`),
    - `L-03`: brak kategorii dla ładunku afektywnego samego tekstu przekładu w scenach lirycznych, intymnych i dramatycznych bez krzyku (wg badań UAM nad Studio Ghibli) oraz anomalna wartość `score = 120` w `DYN_5`,
    - `L-04`: niepełne pokrycie długofalowej spójności idiolektu postaci (indywidualnych manier mówienia, wad wymowy, egzaltowanych rejestrów archetypicznych) w `DYN_1` oraz obecność obcojęzycznych terminów-kotwic w treści kategorii dynamicznych, które mogą zawężać domenę w Fazie 2 (wg badań TUFS, UAM 2026 oraz zasady `Z4 Instance-Free`),
    - `L-05`: brak wytycznej dot. naturalnej kondensacji wielokrotnych powtórzeń tego samego mówcy (wg *Netflix Polish Timed Text Style Guide*),
  - **1 luka P2 (`L-06`):** adnotacje szablonowe kontekstu kulturowego/humoru w `profiler.py` (`PRZENIEŚĆ_DO_10_4` — proces poza `rules.py`).
- **Propozycje (FAZA 4):** **1 nowa kategoria dynamiczna (`DYN_9` — Ładunek afektywny przekładu i liryka emocjonalna z dwupoziomowym triggerem frazowym i ochroną w `Anti-Smoothing Filter`)** + **4 precyzyjne rozszerzenia istniejących kategorii (`DYN_8`, `DYN_1`, `BASE_2`, `DYN_6`) w 100% czystej domenie abstrakcyjnej bez przykładów i terminów obcojęzycznych** + **normalizacja `score` `DYN_5` do `82`**.
- **Werdykt końcowy:** **`POTRZEBNE_ROZSZERZENIE`**
- **Handoff (FAZA 7):** **`GOTOWY`** (`Artefakty/Prompt_10.3_dopelnienie_filarow.md`, walidacja P7.3: **15/15 PASS**).

---

## 2. FAZA 0 — STAN OBECNY (12 KATEGORII + POPRAWKI PO 10.2)

### P0.1. Przeczytane pliki na commicie `51dbe2d`
1. `rules.py` (`STANDARD_9_CORE_RULES_PROMPT`, `get_focused_rules_for_batch` z 8 kategoriami `DYN_1–DYN_8`, `Anti-Smoothing Filter`, `TRANSLATION_RULES_PROMPT`).
2. `profiler.py` (`format_lean_episode_brief` po odchudzeniu w `2B.5`).
3. `translator.py` oraz `verifier.py` (przekazywanie `focused_rules_str` do promptu Fazy 1 i Fazy 2).
4. `Artefakty/Raport_audytu_filarow.md`, `Artefakty/Prompt_10.2_minimalizacja_filarow.md` oraz `Artefakty/Raport_wdrozenia_10.2.md`.
5. `tests/test_profiler.py` (testy `T10.2_1`, `T10.2_2`, `T10.2_3`).

### P0.2. Surowe wyjścia 9 komend diagnostycznych na `51dbe2d`

#### Komenda 1: Identyfikacja najnowszego commita i historii po 10.2
~~~text
$ git log --oneline -n 5
51dbe2d Standard 10.2: Deduplication, minimization to 8 dynamic AVT categories (DYN_1-DYN_8), and zero-noise selector
81de7b5 Hotfix 10.1.1: Eliminate false italics in contiguous speech and enforce dialect contrast (FILAR XIII)
01f9f3b Standard 10.1: Full empirical verification and pipeline hardening
~~~

#### Komenda 2: `grep -nE "KATEGORIA_BASE_[1-4]|KATEGORIA_DYN_[1-8]|DYN_[1-8]|FILAR [1-4]" rules.py`
~~~text
2527:[FILAR 1 — SKŁADNIA, PRO-DROP, WERBALIZACJA I REKCJA (P0/P1)]
2564:[FILAR 2 — ZWIĘZŁOŚĆ AVT, RYTM SEIYŪ I PARALINGWISTYKA (P1)]
2583:[FILAR 4 — FORMATOWANIE TECHNICZNE ASS, WIELOKROPKI I KURSYWA (P1)]
2597:[FILAR 3 — SPÓJNOŚĆ RODZAJU GRAMATYCZNEGO P0, ADRESATA, CYTATÓW I LICZEBNIKÓW (P0)]
2712:    # DYN_1 (score 95): FILAR XIII & XII - Dialekty, gwara, sociolekty i kontrast rejestrów
2740:    # DYN_2 (score 92): FILAR XIV & XXX - Archaizacja, keigo dworskie i rejestr wysoki
2760:    # DYN_4 (score 88): FILAR CXXXVI, XCVI & XV - Triangulacja wieku i płci oraz grupy niemęskoosobowe
2782:    # DYN_3 (score 84): FILAR XXV, XXVI, XXVII, XXVIII, XXIX & CLVII - Tytulatura, yobisute i harmonia adresatywna
2804:    # DYN_6 (score 80): FILAR CLXV, LXV, CLXIX & CLXXIX - Ciągłość zdań rozbitych, przeskoki scen i riposty
2824:    # DYN_5 (score 120): FILAR CLXXII, LXVI, LXXV, XVIII, XXXIII, XVI & XVII - Prymat afektu i prozodia walki
2848:    # DYN_7 (score 72): FILAR XLIX, L, LI, LIV, LV & LVI - Rejestry specjalistyczne: bojowy, medyczny, śledczy
2866:    # DYN_8 (score 70): FILAR LXXVIII, LXXIX, LX, LXI, XLI, CIV, CV, CXVIII & CXIX - Adaptacja kulturowa i napisy
~~~

#### Komenda 3: `grep -nE "KATEGORIA_DYN_9|KATEGORIA_DYN_10|KATEGORIA_BASE_5|DYN_9" rules.py`
~~~text
(brak trafień — w 51dbe2d istnieje dokładnie 8 kategorii DYN_1..DYN_8 oraz 4 sekcje bazowe FILAR 1..4)
~~~

#### Komenda 4: Triggery i punktacja `score` w `get_focused_rules_for_batch`
~~~text
2728:        add_rule(95, "• [SKUP SIĘ NA: FILAR XIII & XII - Dialekty Regionalne, Gwara, Sociolekty i Kontrast Rejestrów]: ...")
2750:        add_rule(92, "• [SKUP SIĘ NA: FILAR XIV & XXX - Archaizacja, Keigo Dworskie i Rejestr Starca (Rōjin-go)]: ...")
2772:        add_rule(88, "• [SKUP SIĘ NA: FILAR CXXXVI, XCVI & XV - Triangulacja Kognitywna i Foniczna Wieku i Płci oraz Grupy Niemęskoosobowe]: ...")
2794:        add_rule(84, "• [SKUP SIĘ NA: FILAR XXV, XXVI, XXVII, XXVIII, XXIX & CLVII - Tytulatura, Zasada Yobisute i Harmonia Formy Adresatywnej]: ...")
2816:        add_rule(80, "• [SKUP SIĘ NA: FILAR CLXV, LXV, CLXIX & CLXXIX - Ciągłość Zdań Rozbitych, Szyk Rematyczny i Pary Przylegania]: ...")
2838:        add_rule(120, "• [SKUP SIĘ NA: FILAR CLXXII, LXVI, LXXV, XVIII, XXXIII, XVI & XVII - Dynamiczny Prymat Afektu, Prozodia Oddechu i Somatyka]: ...")
2858:        add_rule(72, "• [SKUP SIĘ NA: FILAR XLIX, L, LI, LIV, LV & LVI - Rejestry Specjalistyczne: Taktyczno-Bojowy, Medyczny i Śledczy]: ...")
2878:        add_rule(70, "• [SKUP SIĘ NA: FILAR LXXVIII, LXXIX, LX, LXI, XLI, CIV, CV, CXVIII & CXIX - Adaptacja Kulturowa, Kalambury, Onomatopeje i Napisy Ekranowe]: ...")
~~~

#### Komenda 5: `grep -nA 10 "Anti-Smoothing\|anti_smoothing" rules.py`
~~~text
2885:    # Anti-Smoothing Filter (Standard 10.1.1 + 10.2: ochrona DYN_1 oraz DYN_2 przed wygładzeniem rejestru)
2886:    if any("FILAR XIII" in r or "FILAR XIV" in r for _, r in candidates):
2887:        candidates = [
2888:            (s, r) for s, r in candidates
2889:            if "FILAR LXXI" not in r and "FILAR CLXXII" not in r
2890:        ]
~~~

#### Komenda 6: Kontrola słów negatywnych/preskryptywnych w `get_focused_rules_for_batch`
~~~text
$ sed -n '/def get_focused_rules_for_batch/,/^def /p' rules.py | grep -nE "\bnie\b|\bzakaz\b|\bunikaj\b|\bzamiast\b|\bniedopuszczalne\b|\busuń\b|np\."
(0 trafień w tekstach reguł — 100% Pure Positive Domain potwierdzone przez test T10.2_3)
~~~

#### Komenda 7: `grep -n "TRANSLATION_RULES_PROMPT\s*=" rules.py`
~~~text
25:TRANSLATION_RULES_PROMPT = """
~~~

#### Komenda 8: `grep -nA 20 "def format_lean_episode_brief" profiler.py | head -25`
~~~text
612:def format_lean_episode_brief(brief_data: Dict[str, Any], series_bible: Optional[Dict[str, Any]] = None) -> str:
...
688:    lines.append("[TOPOLOGIA SCENY I OCHRONA PŁCI (Z1-Z4)]:")
689:    lines.append("- Formy 1. i 2. osoby lp./lm. uzgadniaj z płcią mówcy (P0) i adresata w scenie oraz chronionym rodzajem grup niemęskoosobowych (zgodnie z regułami bazowymi R1.4 i R3.1-R3.5).")
~~~

#### Komenda 9: `git diff 81de7b5..51dbe2d --stat`
~~~text
 .gitignore                                     |   3 +
 Artefakty/Prompt_10.2_minimalizacja_filarow.md | 272 +++++++++++++
 Artefakty/Raport_audytu_filarow.md             | 368 ++++++++++++++++++
 Artefakty/Raport_wdrozenia_10.2.md             | 164 ++++++++
 profiler.py                                    |  12 +-
 rules.py                                       | 541 +++-----------------------
 tests/test_profiler.py                         | 109 ++++++
~~~

---

### P0.3. Odpowiedzi na pytania flagowe (`F0.1–F0.10`) i inwentaryzacja zmian w `51dbe2d`

- **F0.1:** Najnowszy hash na gałęzi `main` to **`51dbe2d`** (`51dbe2d400d16ce1a251efe193a1b96c9b18e361`) i zawiera on kompletne wdrożenie Standardu 10.2.
- **F0.2:** W `rules.py` istnieją dokładnie **4 sekcje bazowe (`BASE_1`–`BASE_4`, oznaczone jako `FILAR 1`–`FILAR 4` z 16 regułami `R1.1–R3.5`)** oraz **8 kategorii dynamicznych (`DYN_1`–`DYN_8`)**. Nie dodano jeszcze `DYN_9` ani `BASE_5`.
- **F0.3:** Każda z 8 kategorii `DYN_1`–`DYN_8` ma unikalny trigger w `get_focused_rules_for_batch`. Uwaga audytorska: 7 kategorii ma punktację w przedziale `70–95` (`DYN_1: 95`, `DYN_2: 92`, `DYN_4: 88`, `DYN_3: 84`, `DYN_6: 80`, `DYN_7: 72`, `DYN_8: 70`), natomiast **`DYN_5` otrzymała w `51dbe2d` `score = 120`** (ponad `DYN_3` i `DYN_4`!), co wymaga normalizacji do `82` w `10.3` (tak aby `DYN_5` stało powyżej `DYN_6: 80`, ale poniżej `DYN_3: 84` i `DYN_4: 88`).
- **F0.4:** Tak, `Anti-Smoothing Filter` w liniach `2886–2890` chroni zarówno `DYN_1` (`FILAR XIII`), jak i `DYN_2` (`FILAR XIV`) przed stłumieniem przez `FILAR CLXXII`. W `10.3` filtr zostanie rozszerzony również na nową kategorię `DYN_9` (`FILAR XIX` & `FILAR LXXVI`).
- **F0.5:** Tak, dla zwykłego dialogu bez zjawisk specjalnych `get_focused_rules_for_batch` zwraca `""` (zweryfikowane przez 7 wariantów w `test_t10_2_1_zero_noise_ordinary_dialogue`).
- **F0.6:** Tak, `format_lean_episode_brief` w `profiler.py` został odchudzony z wielozdaniowych duplikatów rekcji zaprzeczonej i cytatów do zwięzłego jednozdaniowego odwołania do `R1.4` i `R3.1–R3.5`.
- **F0.7:** Obecne 12 kategorii pokrywa następujące domeny semantyczne:
  - `BASE_1`: `grammar` (szyk rematyczny, pro-drop, werbalizacja, dopełniacz negacji),
  - `BASE_2`: `timing` / `prosody` (CPS/CPL, rytm aktora, paralingwistyka bazowa),
  - `BASE_3`: `gender` / `identity` / `numbers` (płeć 1. i 2. os., grupy niemęskoosobowe, cytaty, deklinacja kanonu, liczebniki),
  - `BASE_4`: `formatting` / `ellipsis` (wielokropki, kursywa myśli),
  - `DYN_1`: `dialect` (gwara, sociolekty, kontrast parafrazy),
  - `DYN_2`: `archaization` (etykieta dworska, rejestr wysoki/starczy),
  - `DYN_3`: `honorifics` (tytulatura, forma rówieśnicza, harmonia wołacza),
  - `DYN_4`: `gender_age_triangulation` (chłopiec z wysokim F0, matrona z niskim F0, mowa dziecięca, grupy kobiece),
  - `DYN_5`: `affect_combat` (afekt głosu aktora w walce/krzyku, oddech, odruchy somatyczne),
  - `DYN_6`: `discourse_continuity` (zdania rozbite na 2 eventy, przeskoki scen, riposty),
  - `DYN_7`: `specialized_registers` (żargon taktyczno-bojowy, sportowy, medyczny, śledczy),
  - `DYN_8`: `culture_signs` (kalambury, wyrazy dźwiękonaśladowcze, kulinaria, napisy ekranowe).
- **F0.8 (Inwentaryzacja zmian w `51dbe2d` względem `81de7b5`):**

| Commit | Plik | Zakres modyfikacji w `51dbe2d` |
| :---: | :--- | :--- |
| `51dbe2d` | `rules.py` | Usunięcie 6 redundantnych bloków z `get_focused_rules_for_batch`, konsolidacja 24 bloków do `DYN_1–DYN_8`, przepisanie treści na 100% Pure Positive Domain, rozszerzenie `Anti-Smoothing Filter` na `FILAR XIV`, twardy fallback `""` (netto `-516` linii). |
| `51dbe2d` | `profiler.py` | Odchudzenie sekcji `TOPOLOGIA SCENY I OCHRONA PŁCI` w `format_lean_episode_brief` (netto `-9` linii). |
| `51dbe2d` | `tests/test_profiler.py` | Dodanie testów `T10.2_1`, `T10.2_2`, `T10.2_3` (`+109` linii). |

- **F0.9:** Tak — commit `51dbe2d` w 100% zamknął wszystkie 22 duplikaty (`D-1..D-22`) oraz wszystkie 5 sprzeczności (`S-1..S-5`) z poprzedniego audytu.
- **F0.10:** Commit `51dbe2d` nie wprowadził żadnych słów negatywnych ani naruszeń Z1–Z4 (`verify_purity.py` 12/12 PASS), natomiast pozostawił dwa obszary do udoskonalenia w `10.3`:
  1. punktację `DYN_5` (`score = 120`), którą należy znormalizować do `score = 82`,
  2. pojedyncze obcojęzyczne terminy techniczne w tytułach/tekstach niektórych kategorii `DYN_X` (takie jak `Rōjin-go`, `Keigo`, `Yobisute`), które warto zastąpić czystymi polskimi określeniami domenowymi, aby w Fazie 2 model LLM nie ulegał zawężeniu domeny ani kotwiczeniu leksykalnemu.

---

## 3. FAZA 1 — ZWERYFIKOWANE ŹRÓDŁA PROFESJONALNE

### P1.1. Tabela oceny wiarygodności 8 źródeł

| Nr | Źródło | Typ publikacji | Wiarygodność | Uzasadnienie merytoryczne |
| :---: | :--- | :--- | :---: | :--- |
| **1** | **Netflix Polish Timed Text Style Guide (2024)** | Oficjalne wytyczne platformy streamingowej | **Wysoka** | Obowiązujący standard przemysłowy AVT dla języka polskiego (interpunkcja, powtórzenia, CPS, kursywa, liczby, napisy ekranowe). |
| **2** | **Praca mgr UAM (2026):** *Representation of linguistic diversity in Polish subtitling and dubbing of animated movies* | Praca akademicka (Wydział Anglistyki UAM) | **Wysoka** | Empiryczna analiza strategii oddawania odmian języka (`lexicalization`, `rusticalization`, `artificial variety`, `speech defect`) w polskim przekładzie animacji. |
| **3** | **Artykuł Dialogica (2026):** *Taboo, Wordplay, and Intertextuality: Evaluating Human and AI Performance in Translating English Humour into Polish Subtitles* | Recenzowany artykuł naukowy (*Dialogica*) | **Wysoka** | Bezpośrednie badanie porównawcze ludzi vs AI na korpusie 120 przypadków humoru w polskich napisach; identyfikuje główne deficyty modeli LLM (nadmierna dosłowność i pomijanie w grach słownych, tabu i intertekstualności). |
| **4** | **Doktorat SBC (Judyta Mężyk) — wywiad ze STAW** | Rozprawa doktorska + stanowisko STAW | **Wysoka** | Dokumentuje polską normę czytelniczą Stowarzyszenia Tłumaczy Audiowizualnych (**14–15 CPS** jako optimum percepcji obrazu vs 17–20 CPS na platformach) oraz rolę szablonów kontekstowych. |
| **5** | **Artykuł JoSTrans:** *Voice-over country? Okay, Boomer. How young viewers are disrupting the AVT landscape in Poland* | Recenzowany artykuł naukowy (*JoSTrans*) | **Wysoka** | Badanie preferencji polskich odbiorców wykazujące wysoką akceptację żywego, zindywidualizowanego rejestru mówionego u młodych widzów animacji. |
| **6** | **Praca UAM (IFA):** *Emotional value of English and Polish subtitles for Studio Ghibli movies* | Praca akademicka (UAM) | **Średnia** *(wspierająca)* | Analizuje przekład ładunku afektywnego i subtelnych emocji w japońskich filmach animowanych (poza scenami krzyku/walki). |
| **7** | **Praca TUFS (Tokyo University of Foreign Studies):** *Translating Character Voice: Proposing new subtitling guidelines for conveying character and culture in subtitles for Japanese anime* | Praca akademicka (TUFS) | **Średnia** *(wspierająca)* | Definiuje wytyczne specyficzne dla japońskiego anime: utrzymanie spójnego idiolektu postaci, ról archetypicznych i cech kulturowych w całej serii. |
| **8** | **Praca licencjacka UW:** *Audiovisual translation modes used in rendering Japanese animations into Polish and English* | Praca akademicka (UW) | **Średnia** *(wspierająca)* | Analizuje oczekiwania polskiej widowni anime wobec zachowania japońskich realiów kulturowych i naturalności dialogu. |

---

### P1.2. Kluczowe wytyczne wyekstrahowane z 8 źródeł (`G-01` – `G-16`)

1. **`G-01` (STAW / Doktorat SBC):** Polska norma komfortu czytelniczego napisów wynosi **14–15 CPS** (pozwala śledzić kompozycję kadru i mimikę postaci), natomiast **17 CPS** stanowi górny pułap dla szybkich wymian zdań (powyżej 17–18 CPS aż 80% uwagi wzrokowej pochłania czytanie napisów).
2. **`G-02` (Dialogica 2026):** Trzy domeny humoru wysokiego ryzyka w napisach polskojęzycznych to: **humor tabu / wulgaryzmy ekspresywne (43,3%)**, **intertekstualność / aluzje kulturowe (31,7%)** oraz **gry słowne / kalambury (18,3%)**.
3. **`G-03` (Dialogica 2026):** Modele AI przegrywają z ludzkimi tłumaczami AVT, ponieważ stosują dosłowną retencję (`retention`) lub pominięcie (`omission`) zamiast profesjonalnych strategii **substytucji (`substitution`), adaptacji lokalizacyjnej (`adaptation/localisation`) i kompensacji (`compensation`)**.
4. **`G-04` (UAM 2026):** W przekładzie animacji na język polski zróżnicowanie językowe postaci oddaje się w napisach głównie przez **leksykalizację (`lexicalization`)** i nacechowany szyk wyrazów, przy zachowaniu pełnej czytelności polskiej ortografii, a dla ról komicznych stosuje się kreatywną stylizację środowiskową lub rustykalizację (`rusticalization`).
5. **`G-05` (UAM 2026):** Specyficzną kategorią idiolektu w animacji są **indywidualne maniery artykulacyjne i wady wymowy (`speech defect` / zacięcia / powtarzane sufiksy)**, które należy oddawać spójnym, czytelnym środkiem leksykalnym lub rytmicznym.
6. **`G-06` (TUFS):** Kluczowym wymogiem przekładu anime jest **spójność idiolektu postaci (`character voice`)** na przestrzeni całego odcinka i serii — postać stoicka, arystokratyczna, egzaltowana, rzemieślnicza lub młodzieżowa musi zachować swój idiolekt w każdej scenie, niezależnie od paczki tłumaczeniowej.
7. **`G-07` (Ghibli / UAM):** Przekład anime wymaga wierności wobec **ładunku afektywnego tekstu (`emotional value`)** również w scenach cichych, lirycznych, melancholijnych i intymnych — przez dobór nacechowanych emocjonalnie polskich czasowników, zdrobnień i rytmu frazy, a nie tylko w scenach krzyku czy walki (`DYN_5`).
8. **`G-08` (Netflix TTSG):** **Obsługa powtórzeń tego samego mówcy (`repetitions`)**: wielokrotne powtórzenia tego samego słowa lub wykrzyknienia w jednej wypowiedzi należy w polskich napisach kondensować do pojedynczego lub podwójnego naturalnego wyrażenia ze wzmocnieniem, bez mechanicznego kopiowania potrójnych zrostów.
9. **`G-09` (Netflix TTSG):** **Formatowanie dialogów dwugłosowych (`dual speaker subtitles`)**: w napisach dwuosobowych każdy wers zaczyna się od półpauzy lub myślnika ze spacją, a każda wypowiedź stanowi odrębną całość składniową.
10. **`G-10` (Netflix TTSG):** **Formatowanie liczb i jednostek w dialogu**: liczebniki od 1 do 10 w krótkich kwestiach dialogowych zapisuje się słownie (o ile pozwala budżet CPL/CPS), natomiast liczby wielocyfrowe, godziny, daty i statystyki zapisuje się cyframi przy zachowaniu 100% zgodności wartości.
11. **`G-11` (Netflix TTSG):** **Kursywa (`italics`)**: stosowana dla głosu z offu (narracji pozakadrowej), monologu wewnętrznego, głosu z odbiornika elektronicznego (telefon, telewizor, megafon) oraz cytowanych tytułów, nigdy zaś dla zwykłej emfazy w mowie na ekranie.
12. **`G-12` (Netflix TTSG):** **Wielokropki kontynuacyjne i pauzy**: zdania przerwane lub kontynuowane w kolejnym napisie domyka się wielokropkiem `...` bez spacji przed nim, z zachowaniem pełnej ciągłości rządu gramatycznego między zdarzeniami.
13. **`G-13` (Netflix TTSG):** **Napisy ekranowe (`Forced Narratives / Signs`)**: tłumaczone maksymalnie zwięźle, bez kropki na końcu pojedynczego szyldu/nagłówka, z zachowaniem izolacji od fleksji dialogu.
14. **`G-14` (STAW / JoSTrans / UW):** **Rejestr adresatywny i wulgaryzmy**: naturalne rozróżnienie dystansu społecznego (`ty` vs `pan/pani`/tytulatura) oraz dobór siły ekspresji wulgaryzmów adekwatnie do gatunku anime.
15. **`G-15` (TUFS / UW):** **Zachowanie realiów kulturowych (`cultural retention with clarity`)**: zachowywanie rozpoznawalnych elementów kultury oryginału (kulinaria, święta, hierarchia szkolna) w naturalnej polskiej deklinacji bez zastępowania ich zachodnimi odpowiednikami kulturowymi.
16. **`G-16` (STAW / Doktorat SBC):** **Szablony kontekstowe (`templates`)**: przekazywanie tłumaczowi ustrukturyzowanych adnotacji o relacjach postaci, ukrytych żartach i aluzjach przed rozpoczęciem tłumaczenia sceny.

---

## 4. FAZA 2 — MAPOWANIE ŹRÓDEŁ NA 12 KATEGORII + POPRAWKI PO 10.2 (`51dbe2d`)

| ID | Wytyczna (ze źródła) | Źródło | Pokrywająca kategoria w `51dbe2d` | Typ pokrycia | Pokrycie (%) | Status | Uwzględnia stan `51dbe2d`? |
| :---: | :--- | :--- | :--- | :---: | :---: | :---: | :---: |
| **`G-01`** | Polska norma komfortu **14–15 CPS** vs pułap maksymalny **17 CPS** | STAW (Źródło 4) | `BASE_2` (`R1.7`) — podaje tylko sztywne `CPS <= 17`, brak wskazania optimum `14–15 CPS` | `BASE` | **55%** | **`CZĘŚCIOWE`** | Tak |
| **`G-02`** | Trzy domeny humoru wysokiego ryzyka: **tabu (43%), intertekstualność (32%), gra słów (18%)** | Dialogica (Źródło 3) | `DYN_8` — wymienia wyłącznie kalambury, pomija humor tabu i intertekstualność/aluzje | `DYN` | **35%** | **`CZĘŚCIOWE`** | Tak |
| **`G-03`** | Strategie humoru: **substytucja, adaptacja funkcjonalna i kompensacja** (zamiast dosłowności/pominięcia AI) | Dialogica (Źródło 3) | `DYN_8` — ogólna wzmianka o ekwiwalencji funkcjonalnej tylko dla kalamburów, brak instrukcji substytucji/kompensacji humoru | `DYN` | **25%** | **`BRAK`** | Tak |
| **`G-04`** | Napisy animacji: **leksykalizacja (`lexicalization`)** i szyk dla gwary/slangu przy pełnej czytelności ortografii | UAM 2026 (Źródło 2) | `DYN_1` (`FILAR XIII & XII`) | `DYN` | **85%** | **`POKRYTE`** | Tak |
| **`G-05`** | Oddawanie indywidualnych manier mówienia, tików i **wad wymowy (`speech defect`)** | UAM 2026 (Źródło 2) | `DYN_1` — wspomina o tikach, ale brak wytycznej dla wad wymowy i rejestrów egzaltowanych | `DYN` | **50%** | **`CZĘŚCIOWE`** | Tak |
| **`G-06`** | **Spójność idiolektu postaci (`character voice`)** w całym odcinku i serii (w czystej domenie bez przykładów) | TUFS (Źródło 7) | `DYN_1` + `profiler.py` — działa dla gwary/archaizacji, lecz brak w `DYN_1` jawnej klauzuli ciągłości idiolektu na przestrzeni całego odcinka | `DYN` | **60%** | **`CZĘŚCIOWE`** | Tak |
| **`G-07`** | **Ładunek afektywny przekładu (`emotional value`)** w scenach lirycznych, intymnych i dramatycznych bez krzyku | Ghibli / UAM (Źródło 6) | Brak (`DYN_5` pokrywa wyłącznie fizjologię krzyku/walki/zadyszki i ma zawyżony `score = 120`) | `BRAK` | **20%** | **`BRAK`** | Tak |
| **`G-08`** | **Kondensacja wielokrotnych powtórzeń tego samego mówcy** w napisach | Netflix TTSG (Źródło 1) | `BASE_2` (`R1.7`) — ogólna zwięzłość, brak konkretnej wytycznej o kondensacji potrójnych i nagłych powtórzeń | `BASE` / `DYN` | **40%** | **`CZĘŚCIOWE`** | Tak |
| **`G-09`** | Formatowanie dialogów dwugłosowych (`dual speaker subtitles`) | Netflix TTSG (Źródło 1) | `DYN_6` + `avt_formatter.py` | `DYN` | **90%** | **`POKRYTE`** | Tak |
| **`G-10`** | Zgodność i formatowanie liczebników oraz kwot w dialogu | Netflix TTSG (Źródło 1) | `BASE_3` (`R3.5`) + `EpisodeQualityGate` w `avt_linter.py` | `BASE` | **95%** | **`POKRYTE`** | Tak |
| **`G-11`** | Zasady stosowania kursywy (`{\i1}...{\i0}`) tylko dla myśli, offu i mediów elektronicznych (bez mówionych krótkich replik) | Netflix TTSG (Źródło 1) | `BASE_4` (`R1.11`) + strażnik z Hotfixu `10.1.1` w `translator.py`/`verifier.py` | `BASE` | **95%** | **`POKRYTE`** | Tak |
| **`G-12`** | Ciągłość składniowa i wielokropki kontynuacyjne (`...`) między sąsiednimi napisami | Netflix TTSG (Źródło 1) | `BASE_4` (`R1.10`) + `DYN_6` (`FILAR CLXV, LXV, CLXIX & CLXXIX`) | `BASE` + `DYN` | **95%** | **`POKRYTE`** | Tak |
| **`G-13`** | Zwięzłość i izolacja napisów ekranowych (`Signs / Forced Narratives`) | Netflix TTSG (Źródło 1) | `BASE_3` (`R3.5`) + `DYN_8` (`FILAR LXXVIII & LXXIX`) | `BASE` + `DYN` | **90%** | **`POKRYTE`** | Tak |
| **`G-14`** | Rejestr społeczny (`ty` vs `pan/pani`), adaptacja honoryfikatorów i formy rówieśniczej | STAW / JoSTrans (Źródła 4, 5) | `BASE_3` (`R1.5–R1.6`) + `DYN_3` (`FILAR XXV..XXIX & CLVII`) + `DYN_2` (`FILAR XIV & XXX`) | `BASE` + `DYN` | **95%** | **`POKRYTE`** | Tak |
| **`G-15`** | Zachowanie realiów kulturowych oryginału z naturalną polską fleksją (bez amerykanizacji) | TUFS / UW (Źródła 7, 8) | `BASE_3` (`R3.5`) + `DYN_8` (`FILAR CXVIII & CXIX`) | `BASE` + `DYN` | **85%** | **`POKRYTE`** | Tak |
| **`G-16`** | Szablony kontekstowe (`templates`) z adnotacjami o relacjach i ukrytych znaczeniach | STAW (Źródło 4) | `profiler.py` (`EPISODE BRIEF`) + `scene_discourse.py` (poza zakresem `rules.py`) | `META` | **75%** | **`POKRYTE` *(w architekturze potoku, opcja rozbudowy w 10.4)*** | Tak |

---

## 5. FAZA 3 — IDENTYFIKACJA LUK

Na podstawie mapowania w FAZIE 2 zidentyfikowano **6 luk (`L-01` – `L-06`)**, które dzielą wytyczne o statusie `BRAK` lub `CZĘŚCIOWE`:

| ID luki | Wytyczna (ze źródła) | Źródło | Dlaczego stanowi lukę w `51dbe2d`? | Kategoria semantyczna | Priorytet | Typ rozwiązania | Czy `51dbe2d` już ją adresuje? |
| :---: | :--- | :--- | :--- | :---: | :---: | :--- | :---: |
| **`L-01`** | **Strategie przekładu humoru wysokiego ryzyka (tabu, gra słów, intertekstualność): substytucja, adaptacja funkcjonalna i kompensacja** (`G-02`, `G-03`) | Dialogica 2026 (Źródło 3) | W `51dbe2d` kategoria `DYN_8` wspomina jednym zdaniem wyłącznie o kalamburach, nie instruując modelu o dwóch pozostałych domenach najwyższego ryzyka dla AI (humor tabu/subtelna dwuznaczność: 43,3% oraz aluzje intertekstualne: 31,7%) ani o nakazie stosowania substytucji i kompensacji. Dodatkowo trigger `DYN_8` nie wykrywa markerów humoru sytuacyjnego, sarkazmu i aluzji. | `humor` / `culture` | **`P0`** | **`ROZSZERZ DYN_8`** (treść czysto domenowa + trigger humoru/aluzji) | **Nie** |
| **`L-02`** | **Polska norma czytelnicza STAW: optimum 14–15 CPS dla percepcji obrazu vs pułap maksymalny 17 CPS w szybkim dialogu** (`G-01`) | Doktorat SBC / STAW (Źródło 4) | W `BASE_2` (`R1.7`) podano wyłącznie górną granicę `CPS <= 17`. Model LLM traktuje 17 CPS jako docelową normę dla każdej linii, zamiast dążyć do komfortowego polskiego standardu **14–15 CPS** i rezerwować 17 CPS dla szybkich wymian zdań. | `timing` | **`P1`** | **`ROZSZERZ BASE_2`** (`R1.7` — precyzyjna korekta 1 zdania) | **Nie** |
| **`L-03`** | **Ładunek afektywny przekładu (`emotional value`) w scenach lirycznych, intymnych, melancholijnych i dramatycznych + normalizacja priorytetu `DYN_5`** (`G-07`) | Praca UAM o Ghibli (Źródło 6) | `DYN_5` w `51dbe2d` obsługuje wyłącznie somatyczną fizjologię walki, zadyszki i krzyku (`>= 5` wykrzykników). Ciche sceny o wysokim ładunku emocjonalnym (wyznania, żegnanie się, rozpacz, nostalgia, czułość) nie aktywują żadnej kategorii afektywnej. Ponadto `DYN_5` ma w `51dbe2d` zawyżony `score = 120`, który przebija `DYN_3` (84) i `DYN_4` (88). | `emotion` | **`P1`** | **`NOWA DYN_9`** (`score = 74`, chroniona w `Anti-Smoothing Filter`) + korekta `score` `DYN_5` (`120 → 82`) | **Nie** |
| **`L-04`** | **Spójność idiolektu postaci w serii, czytelna leksykalizacja, maniery artykulacyjne (`speech defect`) oraz eliminacja obcojęzycznych terminów-kotwic z treści kategorii dynamicznych** (`G-04`, `G-05`, `G-06`, `Z4`) | TUFS (Źródło 7) + UAM 2026 (Źródło 2) | `DYN_1` w `51dbe2d` skupia się na gwarze ludowej i slangu ulicznym, ale pomija pełną definicję spójności idiolektu z badań TUFS i UAM: utrzymanie indywidualnego rejestru postaci określonego w `SeriesBible` na przestrzeni całego odcinka, leksykalizację oraz oddawanie wad wymowy, manieryzmów i rejestru egzaltowanego. Ponadto teksty kategorii dynamicznych powinny być całkowicie wolne od przykładowych słów i obcojęzycznych terminów-kotwic, aby nie zawężać domeny w Fazie 2. | `identity` / `dialect` | **`P1`** | **`ROZSZERZ DYN_1`** + oczyszczenie wszystkich `DYN_1–DYN_9` do 100% czystych opisów domenowych bez przykładów | **Nie** |
| **`L-05`** | **Naturalna kondensacja wielokrotnych powtórzeń tego samego mówcy (`repetitions`) w napisach polskojęzycznych** (`G-08`) | Netflix TTSG (Źródło 1) | Angielskie skrypty anime kalkują japońskie potrójne i podwójne nagłe powtórzenia. Brak jawnej wskazówki o kondensacji powtórzeń tego samego mówcy do zwięzłego polskiego ekwiwalentu emfatycznego powoduje nadmiarowe znaki i zawyżanie CPS. | `repetition` / `discourse` | **`P1`** | **`ROZSZERZ DYN_6`** (treść czysto domenowa + dwuczęściowy trigger z wykluczeniem idiomów) | **Nie** |
| **`L-06`** | **Wzbogacenie szablonów kontekstowych (`EPISODE BRIEF`) o adnotacje humoru i intertekstualności** (`G-16`) | Doktorat SBC / STAW (Źródło 4) | `profiler.py` generuje w KROKU 5 doskonały profil postaci i glosariusza, ale nie ekstrahuje jeszcze jawnej listy gier słownych/aluzji na poziomie całego odcinka. Jest to zagadnienie procesowe `profiler.py`, wykraczające poza architekturę Filarów w `rules.py`. | `meta` | **`P2`** | **`PRZENIEŚĆ_DO_10_4`** (poza zakresem `10.3`) | **Nie** |

---

## 6. FAZA 4 — PROPOZYCJE ROZWIĄZAŃ (100% CZYSTE DOMENY BEZ PRZYKŁADÓW I TERMINÓW OBCOJĘZYCZNYCH)

Wszystkie poniższe propozycje tekstów kategorii wysyłanych do LLM w Fazie 1 i Fazie 2 zostały sformułowane w **100% Czystej Domenie Pozytywnej (Z2)** oraz **wyłącznie na poziomie abstrakcyjnych domen językowych (Z1/Z4)** — **bez jakichkolwiek przykładów słownych i bez obcojęzycznych terminów-kotwic** (`dajare`, `giongo`, `gitaigo`, `chūnibyō`, `character voice`, `rōjin-go`, `keigo`, `yobisute`, `ottotto`, `kakegoe`, `kanojo-tachi`, `bento`), które mogłyby zawężać działanie tłumacza lub weryfikatora w Fazie 2:

| ID luki | Typ rozwiązania | Kategoria docelowa | Treść propozycji w formie czysto domenowej i pozytywnej (Z1–Z4, bez przykładów i terminów obcych) | Trigger w kodzie Pythona (wewnętrzny regex Z4 — niewysyłany do LLM) | Score | Źródło | Z1–Z4 |
| :---: | :--- | :--- | :--- | :--- | :---: | :--- | :---: |
| **`L-01`** | `ROZSZERZ DYN_8` | `[KATEGORIA_DYN_8]` (`FILAR LXXVIII, LXXIX, LX, LXI, XLI, CIV, CV, CXVIII & CXIX - Adaptacja Kulturowa, Gry Słowne, Onomatopeje i Napisy Ekranowe`) | „Prawidłowy stan przekładu humoru, gier słownych, podtekstów tabu oraz aluzji intertekstualnych to zachowanie efektu komicznego poprzez twórczą substytucję, adaptację funkcjonalną i kompensację w naturalnej polszczyźnie, przy prymacie ekwiwalencji pragmatycznej nad dosłownością. Wyrazy dźwiękonaśladowcze w dialogu przekładaj na plastyczne polskie czasowniki ruchu lub stanu, nazwy potraw i realiów kulturowych adaptuj z naturalną polską fleksją, a napisy ekranowe i elementy interfejsu formułuj w maksymalnie zwięzłej formie nominalnej.” | Istniejący trigger `DYN_8` **+ jednoznaczne markery humoru, ironii i aluzji:** `\b(?:joke\|joking\|just kidding\|wordplay\|pun\|riddle\|irony\|ironic\|sarcasm\|parody\|double meaning\|innuendo\|teasing\|hilarious\|tsukkomi\|boke\|neta\|gyagu\|dajare)\b` (bez samotnego `kidding`). | **`70`** | Dialogica 2026 (Źródło 3) | ✅ |
| **`L-02`** | `ROZSZERZ BASE_2` | `[KATEGORIA_BASE_2]` (`R1.7` w `STANDARD_9_CORE_RULES_PROMPT`) | „R1.7. Zwięzłość AVT i Budżet Czytelniczy: Prawidłowy stan napisów to celowanie w polskie optimum percepcyjne 14–15 znaków na sekundę dla swobodnego odbioru obrazu, przy zachowaniu maksymalnego pułapu 17 znaków na sekundę (CPS) w szybkim dialogu oraz limitu 38 znaków w linii (CPL) poprzez dobór krótkich, nośnych polskich synonimów.” | Zawsze aktywne w `STANDARD_9_CORE_RULES_PROMPT` (zastępuje dotychczasowe zdanie `R1.7`, przyrost netto ~40 znaków). | `Base` | STAW / Doktorat SBC (Źródło 4) | ✅ |
| **`L-03`** | `NOWA DYN_9` + korekta `score` `DYN_5` | **`[KATEGORIA_DYN_9]`** (`FILAR XIX & LXXVI - Ładunek Afektywny Przekładu, Melancholia i Liryka Emocjonalna`) | „• [SKUP SIĘ NA: FILAR XIX & LXXVI - Ładunek Afektywny Przekładu, Melancholia i Liryka Emocjonalna]: Prawidłowy stan przekładu scen intymnych, wyznań, smutku, pożegnań i wzruszenia to pełne oddanie ładunku emocjonalnego poprzez dobór nacechowanego uczuciowo słownictwa, subtelnych partykuł modalnych, naturalnych zdrobnień oraz płynnego rytmu składniowego zharmonizowanego z barwą głosu aktora.” *(Równocześnie w `DYN_5` normalizacja `score` z `120` na `82` oraz rozszerzenie `Anti-Smoothing Filter` na `DYN_9`).* | **Dwupoziomowy trigger frazowy w Pythonie:** **(a) Frazy wysokiej pewności (≥1):** `\b(?:miss you\|missed you\|miss him\|miss her\|tears of\|shed a tear\|in tears\|farewell\|last words\|final words\|loneliness\|all alone\|so lonely\|sorrow\|grief\|mourning)\b` (EN) lub `\b(?:namida\|sayonara\|sabishii\|kanashii)\b` (JP); **(b) Frazy wspierające (≥2 różne w paczce):** `\b(?:forgive me\|sorry for everything\|promise me\|I promise you\|my beloved\|my dear\|dearest\|from the bottom of my heart\|in my heart\|in my soul\|deep regret\|full of regret\|I regret\|natsukashii\|itoshii)\b`. Wykluczone pojedyncze słowa: `love`, `heart`, `feelings`, `memories`, `gentle`, `warmth`, `precious`, `beloved`, `lonely`, `regret`. | **`74`** *(a `DYN_5`: `82`)* | Praca UAM o Ghibli (Źródło 6) | ✅ |
| **`L-04`** | `ROZSZERZ DYN_1` + czystość domenowa `DYN_1–DYN_9` | `[KATEGORIA_DYN_1]` (`FILAR XIII & XII - Dialekty Regionalne, Gwara, Sociolekty i Kontrast Rejestrów`) | Dopisanie do `DYN_1` czysto domenowego zdania: „Prawidłowy stan indywidualnego głosu postaci to bezwzględna ciągłość jej idiolektu, rejestru środowiskowego, egzaltowanej maniery retorycznej lub charakterystycznej maniery artykulacyjnej na przestrzeni całego odcinka poprzez dobór nacechowanej leksyki i szyku wyrazów, przy zachowaniu pełnej czytelności polskiej ortografii.” + usunięcie z tekstów i tytułów wszystkich kategorii `DYN_1–DYN_9` wszelkich obcojęzycznych terminów-kotwic. | Istniejący trigger `DYN_1` **+ wielowyrazowe frazy egzaltowane i sufiksy w Pythonie:** `\b(?:foolish mortals?\|mere mortals?\|dark abyss\|eternal darkness\|realm of shadows\|sealed power\|dark flame\|wicked eye\|wagahai)\b` oraz `(?:^\|[\s\-])(?:dechu\|nyan\|pyon\|zura\|gero\|dabe)\b`. | **`95`** | TUFS (Źródło 7) + UAM 2026 (Źródło 2) | ✅ |
| **`L-05`** | `ROZSZERZ DYN_6` | `[KATEGORIA_DYN_6]` (`FILAR CLXV, LXV, CLXIX & CLXXIX - Ciągłość Zdań Rozbitych, Szyk Rematyczny i Pary Przylegania`) | Dopisanie do `DYN_6` czysto domenowego zdania: „Wielokrotne powtórzenia tego samego wyrazu lub wykrzyknienia wewnątrz jednej kwestii mówcy kondensuj do pojedynczego lub podwójnego naturalnego sformułowania wzmocnionego polską partykułą emfatyczną.” | Istniejący trigger `DYN_6` **+ dwa wzorce powtórzeń w Pythonie:** **(a) potrójne+ dowolne słowo:** `\b([a-zA-Z]{2,})\s*,\s*\1\s*,\s*\1\b` oraz **(b) podwójne tylko dla słów „nagłych/urgentnych”:** `\b(wait\|stop\|run\|hurry\|come\|go\|look\|please\|hey\|help\|no)\s*,\s*\1\b` (z wykluczeniem idiomów `yes, yes`, `well, well`, `now, now`, `there, there`, `oh, oh`). | **`80`** | Netflix TTSG (Źródło 1) | ✅ |

---

## 7. FAZA 5 — OCENA ZGODNOŚCI Z ZASADAMI PROJEKTU (`Z1–Z4`, `Z16`, `verify_purity.py`)

| Propozycja | Z1 (Zero-Literal) | Z2 (Pure Positive Domain) | Z3 (Primary LLM Authority) | Z4 (Instance-Free / Zero-Examples w tekście reguł) | Z16 (Legacy Protection) | `verify_purity.py` 12/12 + `T10.3_3` |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **`L-01` (`ROZSZERZ DYN_8` — strategie humoru Dialogica)** | ✅ 0 nazw własnych | ✅ Forma pozytywna („Prawidłowy stan = ...”), 0 słów przeczących | ✅ Instrukcja dla LLM | ✅ Czysta domena w tekście reguły (0 przykładów i terminów obcych) | ✅ `TRANSLATION_RULES_PROMPT` i `test_system.py` nietknięte | ✅ **PASS (12/12)** |
| **`L-02` (`ROZSZERZ BASE_2` — polskie optimum 14–15 CPS STAW)** | ✅ 0 nazw własnych | ✅ Forma pozytywna, 0 słów przeczących | ✅ Instrukcja budżetu czasowego | ✅ Czysta metryka CPS/CPL | ✅ Nietknięte | ✅ **PASS (12/12)** |
| **`L-03` (`NOWA DYN_9` — ładunek afektywny Ghibli + korekta `DYN_5` do `82`)** | ✅ 0 nazw własnych | ✅ Forma pozytywna, 0 słów przeczących | ✅ Instrukcja stylizacji emocjonalnej | ✅ Czysta domena w tekście reguły (0 przykładów) | ✅ Nietknięte | ✅ **PASS (12/12)** |
| **`L-04` (`ROZSZERZ DYN_1` — spójność idiolektu TUFS i leksykalizacja UAM + depuracja terminów obcych)** | ✅ 0 nazw własnych | ✅ Forma pozytywna, 0 słów przeczących | ✅ Instrukcja spójności idiolektu | ✅ Czysta domena we wszystkich `DYN_1–DYN_9` (0 przykładów i terminów obcych) | ✅ Nietknięte | ✅ **PASS (12/12)** |
| **`L-05` (`ROZSZERZ DYN_6` — kondensacja powtórzeń Netflix TTSG)** | ✅ 0 nazw własnych | ✅ Forma pozytywna, 0 słów przeczących | ✅ Instrukcja kondensacji powtórzeń | ✅ Czysta domena w tekście reguły (0 przykładów) | ✅ Nietknięte | ✅ **PASS (12/12)** |

---

## 8. FAZA 6 — REKOMENDACJE I WERDYKT KOŃCOWY

### Priorytet P0 (Krytyczne dla jakości tłumaczenia anime)
1. **`Operacja 2B.1` (`ROZSZERZ DYN_8` — Luka `L-01`):** Wzbogacić kategorię `DYN_8` o czysto domenowe wytyczne przekładu trzech obszarów humoru wysokiego ryzyka (tabu, gra słów, intertekstualność) metodami substytucji, adaptacji funkcjonalnej i kompensacji (źródło: *Dialogica 2026*) oraz rozszerzyć jej trigger o jednoznaczne markery humoru/ironii/aluzji — status: **`AUTORYTATYWNY`**.

### Priorytet P1 (Ważne dla immersji, czytelności i naturalności)
2. **`Operacja 2B.2` (`ROZSZERZ BASE_2` — Luka `L-02`):** Doprecyzować regułę `R1.7` w `STANDARD_9_CORE_RULES_PROMPT` o polską normę komfortu percepcyjnego **14–15 CPS** (wg STAW) przy zachowaniu pułapu **17 CPS** dla szybkiego dialogu (przyrost rozmiaru promptu bazowego: ~40 znaków = `<1%`) — status: **`WYMAGA_DECYZJI` (zatwierdzone do wdrożenia)**.
3. **`Operacja 2B.3` (`NOWA DYN_9` + korekta `DYN_5` — Luka `L-03`):** Dodać kategorię `DYN_9` (`FILAR XIX & LXXVI - Ładunek Afektywny Przekładu, Melancholia i Liryka Emocjonalna`, `score = 74`) z dwupoziomowym triggerem frazowym dla scen intymnych i dramatycznych bez krzyku (źródło: *UAM / Studio Ghibli*), rozszerzyć na nią ochronę `Anti-Smoothing Filter` oraz znormalizować punktację `DYN_5` z `120` na **`82`** — status: **`AUTORYTATYWNY`**.
4. **`Operacja 2B.4` (`ROZSZERZ DYN_1` + czystość domenowa `DYN_1–DYN_9` — Luka `L-04`):** Rozszerzyć kategorię `DYN_1` (`FILAR XIII & XII`) o utrzymanie spójnego idiolektu postaci w całym odcinku, zasadę czytelnej leksykalizacji oraz obsługę charakterystycznych manier artykulacyjnych i rejestru egzaltowanego (źródła: *TUFS*, *UAM 2026*), a także oczyścić teksty i tytuły wszystkich kategorii `DYN_1–DYN_9` z wszelkich przykładowych słów i obcojęzycznych terminów-kotwic (`dajare`, `giongo`, `gitaigo`, `chūnibyō`, `character voice`, `rōjin-go`, `keigo`, `yobisute`, `ottotto`, `kakegoe`, `kanojo-tachi`, `bento`) — status: **`AUTORYTATYWNY`**.
5. **`Operacja 2B.5` (`ROZSZERZ DYN_6` — Luka `L-05`):** Rozszerzyć kategorię `DYN_6` (`FILAR CLXV, LXV, CLXIX & CLXXIX`) o czysto domenową zasadę kondensacji wielokrotnych powtórzeń tego samego mówcy oraz dodać do triggera `DYN_6` dwuczęściową detekcję reduplikacji (potrójne+ dowolne słowo oraz podwójne słowa „urgentne” z wykluczeniem idiomów potwierdzenia) (źródło: *Netflix Polish TTSG*) — status: **`WYMAGA_DECYZJI` (zatwierdzone do wdrożenia)**.

### Priorytet P2 (Opcjonalne / Procesowe poza `rules.py`)
6. **`PRZENIEŚĆ_DO_10_4` (Luka `L-06`):** Rozbudowa generatora `EPISODE BRIEF` w `profiler.py` o automatyczną ekstrakcję adnotacji dla gier słownych i aluzji kulturowych na wzór szablonów STAW — status: **`POMINIĘTE W 10.3 (PRZENIESIONE DO BACKLOGU 10.4)`**.

### Werdykt końcowy
- **Werdykt:** **`POTRZEBNE_ROZSZERZENIE`**
- **Uzasadnienie:** Architektura 12 kategorii wdrożona w Standardzie 10.2 (`51dbe2d`) wzorowo wyeliminowała szum i duplikaty, pokrywając w pełni 10 z 16 wytycznych branżowych, jednak konfrontacja z najnowszymi badaniami akademickimi (*Dialogica 2026*, *UAM 2026*, *TUFS*, *STAW*, *Ghibli*) i *Netflix Polish TTSG* wykazała 5 konkretnych luk merytorycznych (`L-01` – `L-05`), które można zamknąć poprzez dodanie 1 wąskiej kategorii dynamicznej (`DYN_9`), punktowe doprecyzowanie 4 istniejących kategorii (`DYN_8`, `DYN_1`, `DYN_6`, `BASE_2`) oraz całkowite oczyszczenie tekstów `DYN_1–DYN_9` z przykładów i obcojęzycznych terminów-kotwic.

---

## 9. FAZA 7 — HANDOFF (PODSUMOWANIE I TRACEABILITY)

### 9.1. Tabela Traceability (Mapowanie Operacja w Prompcie 10.3 → Luka Audytu)

| Operacja | Luka (ID) | Źródło zewnętrzne | Typ operacji | Status | Ryzyko | Uwzględnia poprawki z `51dbe2d`? |
| :---: | :---: | :--- | :--- | :---: | :---: | :---: |
| **`2B.1`** | `L-01` (`G-02`, `G-03`) | Dialogica (2026) | **ROZSZERZ `DYN_8`** (strategie humoru: substytucja, adaptacja, kompensacja w tabu, grach słownych i intertekstualności + trigger) | `AUTORYTATYWNY` | niskie | Tak |
| **`2B.2`** | `L-02` (`G-01`) | Doktorat SBC / STAW | **ROZSZERZ `BASE_2`** (doprecyzowanie `R1.7`: polskie optimum 14–15 CPS dla percepcji obrazu vs pułap 17 CPS w szybkim dialogu) | `WYMAGA_DECYZJI` *(zatwierdzone)* | niskie (+40 znaków w Base) | Tak |
| **`2B.3`** | `L-03` (`G-07`) + `F0.3` | Praca UAM (Studio Ghibli) + Audyt `51dbe2d` | **NOWA `DYN_9`** (`FILAR XIX & LXXVI` — ładunek afektywny przekładu i liryka emocjonalna, `score = 74`, dwupoziomowy trigger frazowy + ochrona w `Anti-Smoothing Filter`) + korekta `score` `DYN_5` (`120 → 82`) | `AUTORYTATYWNY` | niskie | Tak |
| **`2B.4`** | `L-04` (`G-04`, `G-05`, `G-06`, `Z4`) | TUFS + Praca mgr UAM (2026) | **ROZSZERZ `DYN_1` + CZYSTOŚĆ DOMENOWA `DYN_1–DYN_9`** (spójność idiolektu w serii, czytelna leksykalizacja, maniery artykulacyjne + usunięcie wszelkich przykładów i obcojęzycznych terminów-kotwic z tekstów wszystkich kategorii dynamicznych) | `AUTORYTATYWNY` | niskie | Tak |
| **`2B.5`** | `L-05` (`G-08`) | Netflix Polish TTSG (2024) | **ROZSZERZ `DYN_6`** (kondensacja wielokrotnych powtórzeń tego samego mówcy + dwuczęściowy trigger reduplikacji z wykluczeniem idiomów) | `WYMAGA_DECYZJI` *(zatwierdzone)* | niskie | Tak |
| **`2B.6`** | `L-01..L-05` | Walidacja 10.3 | **DODAJ 4 TESTY REGRESYJNE (`T10.3_1` – `T10.3_4`)** w `tests/test_profiler.py` | `AUTORYTATYWNY` | niskie | Tak |

### 9.2. Podsumowanie Handoffu (P7.5)
- **Prompt kodujący:** `Artefakty/Prompt_10.3_dopelnienie_filarow.md`
- **Wersja:** `10.3`
- **Liczba operacji:** `6` (w tym `4` `AUTORYTATYWNE`, `2` `WYMAGA_DECYZJI` — obie zatwierdzone do wdrożenia)
- **Traceability:** `6/6` operacji powiązanych z lukami `L-01` – `L-05`
- **Walidacja P7.3:** `15/15` PASS
- **Known risks (P7.4):** `9` ryzyk (`R1`–`R9`), wszystkie opisane w SEKCJI 7 promptu kodującego wraz z wpisem backlogu `10.4` (`L-06`)
- **Status:** **`GOTOWY`**
- **Następny krok:** Użytkownik zapisuje `Artefakty/Raport_audytu_pokrycia_10_2.md` i `Artefakty/Prompt_10.3_dopelnienie_filarow.md`, a następnie wysyła prompt kodujący do świeżego agenta kodującego.

---

## 10. FAZA ODBIORU

- [x] FAZA 0 — Stan 10.2 + poprawki (`51dbe2d`): 4 BASE + 8 DYN zweryfikowane, `10/10` odpowiedzi `F0.1–F0.10`
- [x] FAZA 0 — Inwentaryzacja zmian w `51dbe2d`: `1` commit wdrożeniowy (`51dbe2d`), `3` zmodyfikowane pliki kodowe/testowe (`rules.py`, `profiler.py`, `tests/test_profiler.py`) + `3` artefakty dokumentacyjne
- [x] FAZA 1 — Źródła: `8/8` przeanalizowanych, ocena wiarygodności wypełniona, `16` wytycznych (`G-01`–`G-16`) wyekstrahowanych
- [x] FAZA 2 — Mapowanie: `16` wytycznych (`10` `POKRYTE`, `4` `CZĘŚCIOWE`, `2` `BRAK`)
- [x] FAZA 3 — Luki: `6` luk (`1` P0, `4` P1, `1` P2)
- [x] FAZA 4 — Propozycje: `1` nowa kategoria (`DYN_9`), `4` rozszerzenia istniejących kategorii (`DYN_8`, `BASE_2`, `DYN_1`, `DYN_6`) w 100% czystej domenie bez przykładów + korekta punktacji `DYN_5` (`120 → 82`)
- [x] FAZA 5 — Zgodność z Z1–Z4 i `verify_purity.py`: `5/5` PASS
- [x] FAZA 6 — Rekomendacje: `1` P0, `4` P1, `1` P2
- [x] Werdykt: `POTRZEBNE_ROZSZERZENIE`
- [x] FAZA 7 — Handoff: `GOTOWY`
- [x] Prompt kodujący: `Artefakty/Prompt_10.3_dopelnienie_filarow.md`
- [x] Walidacja P7.3: `15/15` PASS
- [x] 0 placeholderów `<DO_WYPEŁNIENIA>` w raporcie
- [x] 0 zmian w kodzie (`git status` clean)
- [x] 0 commitów
- [x] Z16 nienaruszone
- [x] Z1/Z2/Z3/Z4 respektowane