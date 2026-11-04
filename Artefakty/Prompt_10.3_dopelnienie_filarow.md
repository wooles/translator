# PROMPT WYKONAWCZY (STANDARD 10.3) — DOPEŁNIENIE KATEGORII WYKONAWCZYCH AVT W `rules.py` NA PODSTAWIE ZWERYFIKOWANYCH ŹRÓDEŁ PROFESJONALNYCH (WERSJA POPRAWIONA I ZAUTORYZOWANA)

- **Wersja docelowa:** `10.3`
- **Wersja poprzednia (baseline):** `10.2` (HEAD `51dbe2d` / `51dbe2d400d16ce1a251efe193a1b96c9b18e361`)
- **Baseline przed 10.2:** `81de7b5` (Hotfix 10.1.1)
- **Baseline Depuracji Legacy 1.0 (Z16):** `474fb64`
- **Zakres:** Uzupełnienie systemu Kategorii Wykonawczych AVT w `rules.py` o brakujące wytyczne profesjonalnego przekładu anime (1 nowa kategoria `DYN_9` + 4 punktowe rozszerzenia `DYN_8`, `BASE_2`, `DYN_1`, `DYN_6` + normalizacja priorytetu `DYN_5` do `82` + oczyszczenie tekstów i tytułów wszystkich kategorii `DYN_1–DYN_9` z przykładowych słów i obcojęzycznych terminów-kotwic).
- **Status decyzji użytkownika dla Podsekcji 2B (`Operacje 2B.2` i `2B.5`):** **ZATWIERDZONE DO WDROŻENIA** — wykonaj pełny zakres wszystkich 6 operacji (`2B.1` – `2B.6`) oraz wszystkich 4 testów (`T10.3_1` – `T10.3_4`).

**Kluczowe udoskonalenia architektoniczne w tej wersji promptu 10.3:**
1. **100% Czyste Domeny bez przykładów i obcojęzycznych terminów-kotwic w treści Filarów (Ochrona Fazy 2):** wszystkie teksty i tytuły kategorii `DYN_1` – `DYN_9` wstrzykiwane do promptu LLM (w Fazie 1 i Fazie 2) muszą operować **wyłącznie na polskich, abstrakcyjnych domenach językowych i translatorycznych**, bez jakichkolwiek przykładowych słów oraz bez obcojęzycznych terminów technicznych (`dajare`, `giongo`, `gitaigo`, `chūnibyō`, `character voice`, `rōjin-go`, `keigo`, `yobisute`, `ottotto`, `kakegoe`, `kanojo-tachi`, `bento`, `-san`, `-sama`). Zapobiega to zjawisku *Domain Narrowing* i *Lexical Anchoring* w Fazie 2 (`verifier.py`).
2. **Zawężenie triggera `DYN_9` (Zero False Positives):** zamiast pojedynczych słów ogólnych (`love`, `heart`, `feelings`, `memories`, `gentle`, `warmth`, `precious`, `beloved`, `lonely`, `regret`) zastosowano w kodzie Pythona **dwupoziomowy trigger frazowy**: (a) frazy wysokiej pewności (wystarczy 1 trafienie) oraz (b) frazy wspierające (wymagane ≥2 różne trafienia w paczce).
3. **Zawężenie triggerów `DYN_1` i `DYN_8`:** wyeliminowano z `DYN_1` pojedyncze słowa ogólne (`darkness`, `foolish`, `pathetic`, `realm`) na rzecz wielowyrazowych fraz egzaltowanych, a w `DYN_8` zastąpiono samotne `kidding` frazą `just kidding`, chroniąc dramatyczne kwestie przed fałszywą aktywacją.
4. **Rozszerzenie `Anti-Smoothing Filter` z ochroną scen walki:** filtr chroni `DYN_1` (`FILAR XIII`), `DYN_2` (`FILAR XIV`) oraz `DYN_9` (`FILAR XIX` / `FILAR LXXVI`), przy czym dla `DYN_9` wyklucza `FILAR CLXXII` wyłącznie wtedy, gdy w paczce nie występują twarde markery walki/somatyki `DYN_5`.
5. **Zawężenie triggera powtórzeń w `DYN_6`:** rozdzielenie na (a) potrójne+ powtórzenia dowolnego słowa oraz (b) podwójne powtórzenia wyłącznie słów „nagłych/urgentnych” (`wait`, `stop`, `no`, `run`, `help`, `hurry`, `come`, `go`, `look`, `please`, `hey`), z jawnym wykluczeniem idiomów potwierdzenia (`yes, yes`, `well, well`, `now, now`, `there, there`).
6. **Korekta `DYN_5` score do `82` oraz test `T10.3_4`:** `DYN_5` otrzymuje priorytet `82` (między `DYN_3: 84` a `DYN_6: 80`), a test `T10.3_4` weryfikuje obecność norm `14–15` i `17` w `R1.7`.

---

## PREAMBUŁA

Niniejszy prompt wykonawczy realizuje wnioski z audytu pokrycia Standardu 10.2 (`51dbe2d`) przez 8 zweryfikowanych źródeł branżowych i akademickich (m.in. *Netflix Polish Timed Text Style Guide*, wytyczne *STAW*, badania *Dialogica 2026*, *UAM 2026*, *TUFS*, *JoSTrans*). Pełny kontekst diagnostyczny znajduje się w pliku `Artefakty/Raport_audytu_pokrycia_10_2.md` (sekcje 4–6). Wersja otrzymuje oznaczenie `10.3`, ponieważ zachowuje pełną architekturę i kontrakt Standardu 10.2 (`51dbe2d`), wprowadzając wyłącznie chirurgiczne dopełnienie dla 5 zidentyfikowanych luk merytorycznych (`L-01` – `L-05`).

**Zasady nadrzędne Standardu 9.0 (obowiązujące w 100%):**
- **Z1 (Zero-Literal):** całkowity zakaz umieszczania w kodzie, regułach i testach jakichkolwiek nazw własnych z anime.
- **Z2 (Pure Positive Domain):** wszystkie sformułowania nowych i rozszerzanych kategorii w `rules.py` muszą być w 100% w formie pozytywnej („Prawidłowy stan = X”), bez słów przeczących i preskryptywnych (`nie`, `zakaz`, `zabrania`, `unikaj`, `zamiast`, `niedopuszczalne`, `usuń`, `błąd`, `błędem`, `musi`, `muszą`, `zawsze`, `nigdy`), bez skrótu `np.`, bez cytatów w apostrofach i bez słów ALL-CAPS wewnątrz zdania.
- **Z3 (Primary LLM Translation Authority):** kategorie są instrukcjami metajęzykowymi dla modelu LLM, a nie deterministycznymi wymuszaczami.
- **Z4 (Instance-Free & Example-Free Metalinguistic Architecture):** tekst kategorii wysyłany do LLM operuje **wyłącznie na czystych domenach językowych**, bez żadnych przykładowych słów i bez obcojęzycznych terminów technicznych w treści lub tytule reguły.
- **Z16 (Ochrona Depuracji Legacy 1.0):** całkowity zakaz modyfikacji `test_system.py`, `tests/archive/`, 3 gałęzi `# DEFENSIVE_FALLBACK` w `avt_linter.py`, `pytest.ini` oraz pasywnej stałej `TRANSLATION_RULES_PROMPT` w `rules.py`.

---

## FAZA 0 — CZYTANIE KODU I WERYFIKACJA PRZED ZMIANAMI (OBOWIĄZKOWA)

Przed przystąpieniem do jakichkolwiek modyfikacji agent kodujący ma obowiązek przeczytać następujące pliki i uruchomić komendy diagnostyczne:

### P0.1. Pliki do przeczytania
1. `Artefakty/Raport_audytu_pokrycia_10_2.md` — sekcje 4–6 (mapowanie źródeł `G-01..G-16`, tabela luk `L-01..L-06`, tabela propozycji pozytywnych).
2. `rules.py` — sekcja `STANDARD_9_CORE_RULES_PROMPT` (w szczególności `R1.7`) oraz funkcja `get_focused_rules_for_batch` (linie `2688–2910` na commicie `51dbe2d`).
3. `translator.py`, `verifier.py` oraz `profiler.py` — potwierdzenie integracji `get_focused_rules_for_batch`.
4. `verify_purity.py`, `verify_12_fixes.py`, `verify_ultimate_pipeline.py` oraz `tests/test_profiler.py` — sprawdzenie istniejących bramek i testów `T10.2_1`, `T10.2_2`, `T10.2_3`.

### P0.2. Komendy diagnostyczne Fazy 0 (zapisz surowe wyjścia w raporcie)
1. Sprawdzenie aktualnych kategorii i punktacji `score` w `get_focused_rules_for_batch`:
   `grep -nE "# DYN_|add_rule\(" rules.py`
2. Sprawdzenie aktualnego brzmienia reguły `R1.7` w `STANDARD_9_CORE_RULES_PROMPT`:
   `grep -nA 5 "R1\.7\." rules.py`
3. Sprawdzenie wszystkich testów w `tests/test_profiler.py` oraz bramek weryfikujących `CLXXII` i `R1.7`:
   `grep -rn "def test_\|CLXXII\|R1\.7" tests/ test_system.py verify_*.py`
4. Sprawdzenie aktualnego brzmienia `Anti-Smoothing Filter`:
   `grep -nA 10 "Anti-Smoothing\|anti_smoothing" rules.py`

---

## SEKCJA 1 — NOWA KATEGORIA DYNAMICZNA (`DYN_9`)

Wprowadź do funkcji `get_focused_rules_for_batch` w `rules.py` jedną nową kategorię dynamiczną (`[KATEGORIA_DYN_9]`):

| Kategoria | Nagłówek kompatybilności | Treść w formie czysto domenowej i pozytywnej (Z1–Z4, zero przykładów) | Trigger w kodzie Pythona (wewnętrzny wzorzec Z4 — niewysyłany do LLM) | Priorytet (`score`) |
| :--- | :--- | :--- | :--- | :---: |
| **`[KATEGORIA_DYN_9]`** | `FILAR XIX & LXXVI - Ładunek Afektywny Przekładu, Melancholia i Liryka Emocjonalna` | Prawidłowy stan przekładu scen intymnych, wyznań, smutku, pożegnań i wzruszenia to pełne oddanie ładunku emocjonalnego poprzez dobór nacechowanego uczuciowo słownictwa, subtelnych partykuł modalnych, naturalnych zdrobnień oraz płynnego rytmu składniowego zharmonizowanego z barwą głosu aktora. | **Dwupoziomowy trigger frazowy:** **(a) Frazy wysokiej pewności (wystarczy ≥1 trafienie):** `\b(?:miss you\|missed you\|miss him\|miss her\|tears of\|shed a tear\|in tears\|farewell\|last words\|final words\|loneliness\|all alone\|so lonely\|sorrow\|grief\|mourning)\b` (EN) lub `\b(?:namida\|sayonara\|sabishii\|kanashii)\b` (JP); **(b) Frazy wspierające (wymagane ≥2 różne trafienia w paczce):** `\b(?:forgive me\|sorry for everything\|promise me\|I promise you\|my beloved\|my dear\|dearest\|from the bottom of my heart\|in my heart\|in my soul\|deep regret\|full of regret\|I regret\|natsukashii\|itoshii)\b` (EN+JP). **Jawnie wykluczone jako pojedyncze słowa:** `love`, `heart`, `feelings`, `memories`, `gentle`, `warmth`, `precious`, `beloved`, `lonely`, `regret`. | **`74`** |

---

## SEKCJA 2 — ROZSZERZENIA ISTNIEJĄCYCH KATEGORII (`2B.1` – `2B.6`)

### Podsekcja 2A — Operacje `AUTORYTATYWNE` (obligatoryjne)

#### Operacja `2B.1` — Rozszerzenie `DYN_8` o strategie przekładu humoru wysokiego ryzyka (Dialogica 2026) w czystej domenie
- **Luka:** `L-01` (`G-02`, `G-03`) z FAZY 3 raportu audytu.
- **Lokalizacja:** `rules.py` — blok `DYN_8` (`FILAR LXXVIII, LXXIX, LX, LXI, XLI, CIV, CV, CXVIII & CXIX`) w `get_focused_rules_for_batch`.
- **Instrukcja:**
  1. Rozszerz tekst kategorii `DYN_8` w czystej domenie pozytywnej i całkowicie bez obcojęzycznych terminów-kotwic, tak aby instruował model o trzech obszarach humoru wysokiego ryzyka (gry słowne, podteksty tabu oraz aluzje intertekstualne) i wskazywał, że prawidłowym stanem przekładu humoru jest zachowanie efektu komicznego poprzez twórczą substytucję, adaptację funkcjonalną i kompensację w naturalnej polszczyźnie przy prymacie ekwiwalencji pragmatycznej nad dosłownością (zachowując jednocześnie czysto domenowe wskazówki o wyrazach dźwiękonaśladowczych, realiach kulturowych i napisach ekranowych).
  2. Rozszerz wewnętrzny wzorzec wyzwalający `DYN_8` w Pythonie o jednoznaczne anglojęzyczne i japońskie markery humoru, ironii, kalamburów i aluzji (`\b(?:joke|joking|just kidding|wordplay|pun|riddle|irony|ironic|sarcasm|parody|double meaning|innuendo|teasing|hilarious|tsukkomi|boke|neta|gyagu|dajare)\b`). Nie używaj samotnego słowa `kidding` ani `funny`, aby uniknąć fałszywych pozytywów w dramatycznych pytaniach typu `"Are you kidding me?!"`.
- **Wpływ na prompt:** `0` znaków w Base; +1 zdanie czysto domenowe w `DYN_8` wyłącznie wtedy, gdy w scenie występuje humor, gra słowna, onomatopeja, realia kulturowe lub napis ekranowy.
- **Test regresyjny:** `T10.3_1` i `T10.3_3` w SEKCJI 4.

#### Operacja `2B.3` — Dodanie kategorii `DYN_9` (Ładunek afektywny przekładu) oraz normalizacja `score` `DYN_5` do `82`
- **Luka:** `L-03` (`G-07`) z FAZY 3 oraz `F0.3` z FAZY 0 raportu audytu.
- **Lokalizacja:** `rules.py` — blok `DYN_5` oraz nowy blok `DYN_9` w `get_focused_rules_for_batch`.
- **Instrukcja:**
  1. Dodaj w `get_focused_rules_for_batch` blok `DYN_9` (`score = 74`) zgodnie ze specyfikacją w SEKCJI 1.
  2. W bloku `DYN_5` (`FILAR CLXXII, LXVI, LXXV, XVIII, XXXIII, XVI & XVII`) znormalizuj punktację `score` z `120` na **`82`**, tak aby ustanowić hierarchię priorytetów: `DYN_1: 95 > DYN_2: 92 > DYN_4: 88 > DYN_3: 84 > DYN_5: 82 > DYN_6: 80 > DYN_9: 74 > DYN_7: 72 > DYN_8: 70`. Wartość `82` gwarantuje, że w scenie walki z powtórzeniem (`"Wait, wait, wait! Attack!"`) afekt walki (`DYN_5: 82`) ma pierwszeństwo przed ciągłością dyskursu (`DYN_6: 80`), a jednocześnie ustępuje ochronie płci/wieku (`DYN_4: 88`) i honoryfikatorom (`DYN_3: 84`).
- **Wpływ na prompt:** `0` znaków w Base; `DYN_9` aktywuje się wyłącznie w scenach lirycznych/emocjonalnych.
- **Test regresyjny:** `T10.3_2` w SEKCJI 4.

#### Operacja `2B.4` — Rozszerzenie `DYN_1` o spójność idiolektu postaci oraz oczyszczenie tekstów i tytułów wszystkich kategorii `DYN_1–DYN_9` z przykładów i terminów obcojęzycznych
- **Luka:** `L-04` (`G-04`, `G-05`, `G-06`, `Z4`) z FAZY 3 raportu audytu.
- **Lokalizacja:** `rules.py` — blok `DYN_1` (`FILAR XIII & XII`) oraz pozostałe bloki `DYN_2–DYN_8` w `get_focused_rules_for_batch`.
- **Instrukcja:**
  1. Uzupełnij treść `DYN_1` o czysto domenową wskazówkę w formie pozytywnej, że prawidłowym stanem indywidualnego głosu postaci jest bezwzględna ciągłość jej idiolektu, rejestru środowiskowego, egzaltowanej maniery retorycznej lub charakterystycznej maniery artykulacyjnej na przestrzeni całego odcinka poprzez dobór nacechowanej leksyki i szyku wyrazów przy zachowaniu pełnej czytelności polskiej ortografii.
  2. Oczyść teksty i tytuły (część po myślniku w `[SKUP SIĘ NA: FILAR ... - <Tytuł>]: <Treść>`) wszystkich kategorii `DYN_1–DYN_9` z jakichkolwiek przykładowych słów oraz obcojęzycznych terminów-kotwic (`dajare`, `giongo`, `gitaigo`, `chūnibyō`, `character voice`, `rōjin-go`, `keigo`, `yobisute`, `ottotto`, `kakegoe`, `kanojo-tachi`, `bento`, `onigiri`, `senpai`, `-san`, `-sama`), zastępując je wyłącznie polskimi pojęciami domenowymi (np. *etykieta dworska*, *rejestr sędziwy*, *bezpośrednia forma rówieśnicza*, *odruchy somatyczne i ekspresja wysiłkowa*, *grupy niemęskoosobowe*, *gry słowne*, *wyrazy dźwiękonaśladowcze*, *realia kulturowe i kulinarne*). Sprawdź w Fazie 0 (`P0.2` komenda 3), czy żaden test w `test_system.py` lub `tests/` nie wymaga obecności konkretnego słowa w stringu zwracanym przez `get_focused_rules_for_batch` — rzymskie numery `FILAR ...` w nagłówkach pozostają w 100% zachowane.
  3. Rozszerz wewnętrzny wzorzec wyzwalający `DYN_1` w Pythonie o wielowyrazowe frazy maniery egzaltowanej (`\b(?:foolish mortals?|mere mortals?|dark abyss|eternal darkness|realm of shadows|sealed power|dark flame|wicked eye)\b`), zaimek `wagahai` oraz japońskie sufiksy charakterystyczne (`(?:^|[\s\-])(?:dechu|nyan|pyon|zura|gero|dabe)\b`). Nie używaj pojedynczych słów ogólnych (`darkness`, `foolish`, `pathetic`, `realm`), aby uniknąć fałszywych pozytywów w zwykłych dialogach fantasy.
- **Wpływ na prompt:** `0` znaków w Base; 100% czystości domenowej w Fazie 1 i Fazie 2.
- **Test regresyjny:** `T10.3_1` oraz `T10.3_3` w SEKCJI 4.

#### Operacja `2B.6` — Dodanie testów regresyjnych `T10.3_1`, `T10.3_2`, `T10.3_3`, `T10.3_4` w `tests/test_profiler.py`
- **Luka:** `L-01..L-05` z FAZY 3 raportu audytu.
- **Lokalizacja:** `tests/test_profiler.py`.
- **Instrukcja:** Dodaj 4 nowe sparametryzowane testy jednostkowe opisane w SEKCJI 4.

---

### Podsekcja 2B — Operacje `[WYMAGA DECYZJI UŻYTKOWNIKA — ZATWIERDZONE DO WDROŻENIA]`

**DYREKTYWA WYKONAWCZA:** Użytkownik zatwierdził obie poniższe operacje (`2B.2` oraz `2B.5`) do wdrożenia razem z Podsekcją 2A. Wdróż je w całości i uruchom test `T10.3_4`.

#### Operacja `2B.2` — Doprecyzowanie `BASE_2` (`R1.7`) o polskie optimum czytelnicze 14–15 CPS (STAW)
- **Luka:** `L-02` (`G-01`) z FAZY 3 raportu audytu.
- **Lokalizacja:** `rules.py` — reguła `R1.7` wewnątrz `STANDARD_9_CORE_RULES_PROMPT`.
- **Instrukcja:** Zaktualizuj jednozdaniowy opis `R1.7` w `STANDARD_9_CORE_RULES_PROMPT` (w 100% w czystej domenie pozytywnej i bez przykładów), wskazując celowanie w polskie optimum percepcyjne `14–15` znaków na sekundę dla swobodnego odbioru obrazu przy zachowaniu maksymalnego pułapu `17` znaków na sekundę (`CPS`) w szybkim dialogu oraz limitu `38` znaków w linii (`CPL`). Zachowaj nienaruszony identyfikator `R1.7.` oraz wszystkie słowa kluczowe wymagane przez `verify_12_fixes.py`, `verify_ultimate_pipeline.py` i `verify_purity.py`.
- **Wpływ na rozmiar promptu bazowego:** Przyrost netto wynosi ok. `+40` znaków (`<1%` rozmiaru `STANDARD_9_CORE_RULES_PROMPT`).
- **Test regresyjny:** `verify_purity.py` + `T10.3_3` + `T10.3_4`.

#### Operacja `2B.5` — Rozszerzenie `DYN_6` o kondensację wielokrotnych powtórzeń tego samego mówcy (Netflix TTSG)
- **Luka:** `L-05` (`G-08`) z FAZY 3 raportu audytu.
- **Lokalizacja:** `rules.py` — blok `DYN_6` (`FILAR CLXV, LXV, CLXIX & CLXXIX`) w `get_focused_rules_for_batch`.
- **Instrukcja:**
  1. Dopisz do tekstu `DYN_6` jedno czysto domenowe zdanie w formie pozytywnej (bez przykładów) wskazujące, że wielokrotne powtórzenia tego samego wyrazu lub wykrzyknienia wewnątrz jednej kwestii mówcy kondensuje się do pojedynczego lub podwójnego naturalnego sformułowania wzmocnionego polską partykułą emfatyczną.
  2. Dodaj do wewnętrznego warunku aktywacji `DYN_6` w Pythonie **dwa rozłączne wzorce**:
     - **(a) Potrójne i dłuższe powtórzenia (dowolny wyraz ≥2 litery):** `\b([a-zA-Z]{2,})\s*,\s*\1\s*,\s*\1\b` (z flagą `re.IGNORECASE`) — aktywuje `DYN_6`.
     - **(b) Podwójne powtórzenia wyłącznie słów „nagłych/urgentnych”:** `\b(wait|stop|run|hurry|come|go|look|please|hey|help|no)\s*,\s*\1\b` (z flagą `re.IGNORECASE`) — aktywuje `DYN_6`.
     - **(c) Wykluczone z aktywacji `DYN_6` (idiomy potwierdzenia/acknowledgmentu):** `yes`, `yeah`, `ok`, `well`, `now`, `there`, `oh`, `ah`, `sure`, `right`, `fine`, `good`, `thanks`, `hello`, `bye` — te słowa w podwójnym powtórzeniu są naturalnymi idiomami i są wykluczone przez zamkniętą listę w punkcie (b).
- **Wpływ na prompt:** `0` znaków w Base; aktywuje `DYN_6` wyłącznie na kwestiach z powtórzeniami „urgentnymi” lub potrójnymi.
- **Test regresyjny:** `T10.3_1` oraz `T10.3_2` w SEKCJI 4.

---

## SEKCJA 3 — AKTUALIZACJA TRIGGERÓW I `ANTI-SMOOTHING FILTER`

1. **Hierarchia priorytetów (`score`) dla 9 Kategorii Dynamicznych (`DYN_1` – `DYN_9`):**
   - `DYN_1` (`FILAR XIII & XII` — Dialekty Regionalne, Gwara, Sociolekty i Kontrast Rejestrów): **`95`**
   - `DYN_2` (`FILAR XIV & XXX` — Archaizacja, Etykieta Dworska i Rejestr Wysoki): **`92`**
   - `DYN_4` (`FILAR CXXXVI, XCVI & XV` — Triangulacja Wieku i Płci oraz Grupy Niemęskoosobowe): **`88`**
   - `DYN_3` (`FILAR XXV..XXIX & CLVII` — Tytulatura, Forma Rówieśnicza i Harmonia Formy Adresatywnej): **`84`**
   - `DYN_5` (`FILAR CLXXII, LXVI, LXXV, XVIII, XXXIII, XVI & XVII` — Dynamiczny Prymat Afektu, Prozodia Oddechu i Somatyka): **`82`** *(skorygowane z `120` na `82`)*
   - `DYN_6` (`FILAR CLXV, LXV, CLXIX & CLXXIX` — Ciągłość Zdań Rozbitych, Szyk Rematyczny i Pary Przylegania): **`80`**
   - `DYN_9` (`FILAR XIX & LXXVI` — Ładunek Afektywny Przekładu, Melancholia i Liryka Emocjonalna): **`74`** *(nowa kategoria)*
   - `DYN_7` (`FILAR XLIX, L, LI, LIV, LV & LVI` — Rejestry Specjalistyczne: Taktyczno-Bojowy, Medyczny i Śledczy): **`72`**
   - `DYN_8` (`FILAR LXXVIII, LXXIX, LX, LXI, XLI, CIV, CV, CXVIII & CXIX` — Adaptacja Kulturowa, Gry Słowne, Onomatopeje i Napisy Ekranowe): **`70`**

2. **Rozszerzenie `Anti-Smoothing Filter` na `DYN_9`:**
   - Gdy aktywna jest kategoria `DYN_1` (`FILAR XIII`) lub `DYN_2` (`FILAR XIV`), `Anti-Smoothing Filter` bezwzględnie usuwa z listy kandydatów `FILAR LXXI` oraz `FILAR CLXXII` (zgodnie z testem `T10.2_2`).
   - Gdy aktywna jest kategoria `DYN_9` (`FILAR XIX & LXXVI`), `Anti-Smoothing Filter` usuwa `FILAR LXXI`, a także usuwa `FILAR CLXXII` (chyba że w paczce wystąpiły twarde markery walki/somatyki, takie jak `attack`, `dodge`, `stomp`, `crush`, `ottotto`, `kakegoe`). Dzięki temu w czysto lirycznej scenie ze łzami i wykrzyknieniami emocjonalnymi `DYN_9` jest chroniony przed stłumieniem, a w scenie bezpośredniej walki z powtórzeniem aktywne pozostają `DYN_5` i `DYN_6`.

3. **Ochrona Zero-Noise (`T10.2_1`):**
   - Żaden z nowych ani rozszerzonych triggerów (`DYN_1`, `DYN_6`, `DYN_8`, `DYN_9`) nie może aktywować się na 7 zwykłych zdaniach dialogowych z testu `test_t10_2_1_zero_noise_ordinary_dialogue`.

---

## SEKCJA 4 — WALIDACJA TESTOWA (4 NOWE TESTY REGRESYJNE)

Dodaj w `tests/test_profiler.py` **cztery** nowe testy jednostkowe (`@pytest.mark.unit`, z użyciem `@pytest.mark.parametrize`, w 100% zgodne z Zero-Literal):

1. **`T10.3_1` — `test_t10_3_1_new_and_expanded_categories_triggers`:**
   - Weryfikuje na 5 sparametryzowanych wariantach, że:
     - scena z humorem/aluzją/kalamburem (`"That's a hilarious double meaning pun!"`) aktywuje `DYN_8` i zwraca instrukcję o substytucji/adaptacji/kompensacji (`L-01`),
     - scena liryczno-emocjonalna (`"Tears of sorrow and loneliness filled my heart after our farewell."`) aktywuje nową kategorię `DYN_9` (`FILAR XIX & LXXVI`) (`L-03`),
     - scena z manierą egzaltowaną lub sufiksem charakterystycznym (`"Foolish mortals of the dark abyss!"` / `"I am ready-dechu"`) aktywuje `DYN_1` i zawiera wskazówkę o ciągłości idiolektu (`L-04`),
     - kwestia z potrójnym powtórzeniem tego samego mówcy (`"Wait, wait, wait! Listen to me!"`) aktywuje `DYN_6` i zawiera wskazówkę o kondensacji powtórzeń (`L-05`),
     - kwestia z podwójnym powtórzeniem słowa „urgentnego” (`"Stop, stop! You cannot go there!"`) aktywuje `DYN_6`.

2. **`T10.3_2` — `test_t10_3_2_priority_hierarchy_zero_noise_and_false_positive_guards`:**
   - Weryfikuje, że:
     - **(a)** zwykłe zdania dialogowe z pojedynczymi słowami (`"I love this food!"`, `"My heart is beating fast"`, `"That is a precious memory"`, `"The warmth of the sun is nice"`, `"Are you kidding me?!"`, `"The darkness is falling"`) zwracają `""` (brak fałszywej aktywacji `DYN_9`, `DYN_8` i `DYN_1`),
     - **(b)** idiomy potwierdzenia/acknowledgmentu (`"Yes, yes, I agree."`, `"Well, well, look who is here."`, `"Now, now, calm down."`, `"There, there, it is alright."`, `"Oh, oh, I see."`) nie aktywują `DYN_6` (zwracają `""`),
     - **(c)** hierarchia priorytetów spełnia porządek: `DYN_1 (95) > DYN_2 (92) > DYN_4 (88) > DYN_3 (84) > DYN_5 (82) > DYN_6 (80) > DYN_9 (74) > DYN_7 (72) > DYN_8 (70)`,
     - **(d)** przy aktywacji `DYN_1`, `DYN_2` lub czysto lirycznego `DYN_9` filtr `Anti-Smoothing Filter` poprawnie wyklucza `FILAR CLXXII`,
     - **(e)** w scenie walki z powtórzeniem (`"Wait, wait, wait! Attack! Dodge! Ugh! Ottotto!"`) **oba** `DYN_5` (`82`) i `DYN_6` (`80`) są aktywne, a `DYN_5` występuje przed `DYN_6`.

3. **`T10.3_3` — `test_t10_3_3_purity_domain_abstraction_and_size_invariant_of_all_13_categories`:**
   - Iteruje po liście 9 syntetycznych wejść (aktywujących kolejno każdą z 9 kategorii dynamicznych `DYN_1` – `DYN_9`, dzięki czemu wszystkie 9 tekstów zostaje pobranych bez wzajemnego wykluczenia przez `Anti-Smoothing Filter`) oraz pobiera `STANDARD_9_CORE_RULES_PROMPT` (`BASE_1` – `BASE_4`) i weryfikuje, że:
     - **(a)** 100% tekstu wszystkich 13 kategorii spełnia rygor Czystej Domeny Pozytywnej (brak słów `nie`, `zakaz`, `zabrania`, `unikaj`, `zamiast`, `niedopuszczalne`, `usuń`, `błąd`, `musi`, `zawsze`, `nigdy`, brak `np.`, brak apostrofów cytujących),
     - **(b)** teksty wszystkich 9 kategorii dynamicznych `DYN_1` – `DYN_9` operują wyłącznie na czystych domenach i **nie zawierają żadnych przykładowych słów ani obcojęzycznych terminów-kotwic** (`\b(?:dajare|giongo|gitaigo|chūnibyō|chunibyo|character voice|rōjin-go|rojin-go|keigo|yobisute|ottotto|kakegoe|kanojo-tachi|bento|onigiri|senpai)\b` z `re.IGNORECASE`),
     - **(c)** rozmiar `STANDARD_9_CORE_RULES_PROMPT` wzrósł o mniej niż `5%` względem `51dbe2d`.

4. **`T10.3_4` — `test_t10_3_4_r17_contains_polish_norm_14_15_and_cap_17`:**
   - Pobiera `STANDARD_9_CORE_RULES_PROMPT`, wyodrębnia linię reguły `R1.7` i weryfikuje, że zawiera ona liczby `14`, `15` oraz `17` (oraz `38`), potwierdzając wdrożenie polskiej normy czytelniczej STAW (`Operacja 2B.2`).

---

## SEKCJA 5 — WARUNKI UKOŃCZENIA (a)–(n)

- **(a)** Przeczytano wszystkie pliki z Fazy 0 (`P0.1`) oraz wykonano 4 komendy diagnostyczne (`P0.2`), zapisując ich surowe wyjścia w Sekcji 0 raportu wdrożenia.
- **(b)** Rozszerzono kategorię `DYN_8` o czysto domenowe strategie przekładu humoru wysokiego ryzyka (substytucja, adaptacja, kompensacja) i markery humoru/aluzji (`Operacja 2B.1`, Luka `L-01`).
- **(c)** Doprecyzowano kategorię `BASE_2` (`R1.7`) o polskie optimum czytelnicze `14–15` znaków na sekundę obok pułapu `17` znaków na sekundę (`Operacja 2B.2`, Luka `L-02`).
- **(d)** Dodano nową kategorię `DYN_9` (`FILAR XIX & LXXVI` — Ładunek Afektywny Przekładu, Melancholia i Liryka Emocjonalna, `score = 74`) z zawężonym dwupoziomowym triggerem frazowym oraz znormalizowano `score` `DYN_5` z `120` na `82` (`Operacja 2B.3`, Luka `L-03`).
- **(e)** Rozszerzono kategorię `DYN_1` o ciągłość idiolektu postaci i leksykalizację oraz oczyszczono teksty i tytuły wszystkich kategorii `DYN_1–DYN_9` z przykładowych słów i obcojęzycznych terminów-kotwic (`Operacja 2B.4`, Luka `L-04`).
- **(f)** Rozszerzono kategorię `DYN_6` o kondensację wielokrotnych powtórzeń tego samego mówcy z jawnym podziałem na (a) potrójne+ dowolne, (b) podwójne „urgentne”, (c) wykluczone idiomy potwierdzenia (`Operacja 2B.5`, Luka `L-05`).
- **(g)** Rozszerzono `Anti-Smoothing Filter` na `DYN_9` (`FILAR XIX` i `FILAR LXXVI`) — obok `DYN_1` i `DYN_2`.
- **(h)** Stała `TRANSLATION_RULES_PROMPT` w `rules.py` pozostała w 100% nienaruszona jako pasywne archiwum Z16.
- **(i)** Wszystkie 4 nowe testy regresyjne (`T10.3_1`, `T10.3_2`, `T10.3_3`, `T10.3_4`) oraz testy `T10.2_1..T10.2_3` i `T10.1.1_P1a..P2b` przechodzą w 100%.
- **(j)** Pakiet `pytest tests/ -q` przechodzi w 100% (`256+ passed, 0 failed`).
- **(k)** Pełny pakiet `pytest -q` przechodzi w 100% (`327+ passed, 153 deselected, 0 failed`).
- **(l)** Wszystkie 4 bramki kwalifikacyjne CI/CD (`verify_purity.py`, `verify_12_fixes.py`, `verify_ultimate_pipeline.py`, `audit_diff.ps1`) zwracają `PASS` (`12/12`, `12/12`, `15/15`, `4/4`).
- **(m)** Zasada Z16 zachowana w 100% (`git diff 51dbe2d..HEAD -- test_system.py tests/archive/ avt_linter.py pytest.ini` jest całkowicie pusty — `0` zmian). Wszystkie 20 realnych bibles w `series_memory/*_bible.json` pozostają w 100% nienaruszone (`git diff 51dbe2d..HEAD -- series_memory/` jest całkowicie pusty — `0` zmian).
- **(n)** Zapisano kompletny raport `Artefakty/Raport_wdrozenia_10.3.md` (0 placeholderów `<DO_WYPEŁNIENIA>`), wykonano commit i push na `origin/main`, a `git status` jest czysty. W raporcie jawnie odnotowano, że `L-06` (szablony kontekstowe w `profiler.py`) jest **przeniesione do 10.4** (wymaga wpisu w backlogu 10.4).

---

## SEKCJA 6 — ZAKAZY

1. **ZAKAZ 1 (Z16 — Ochrona Depuracji Legacy 1.0):** Bezwzględny zakaz modyfikacji `test_system.py`, `tests/archive/`, 3 gałęzi `# DEFENSIVE_FALLBACK` w `avt_linter.py` oraz `pytest.ini`.
2. **ZAKAZ 2 (Ochrona Archiwum `TRANSLATION_RULES_PROMPT`):** Bezwzględny zakaz modyfikacji lub usuwania nagłówków `FILAR I` – `FILAR CLXXX` wewnątrz pasywnej stałej `TRANSLATION_RULES_PROMPT` w `rules.py`.
3. **ZAKAZ 3 (Z1 / Zero-Literal):** Całkowity zakaz używania konkretnych nazw własnych z anime w `rules.py`, `profiler.py` oraz `tests/test_*.py`.
4. **ZAKAZ 4 (Z2 / Pure Positive Domain i `verify_purity.py`):** W nowych i rozszerzanych kategoriach w `rules.py` obowiązuje całkowity zakaz używania słów przeczących i preskryptywnych (`nie`, `zakaz`, `zabrania`, `unikaj`, `zamiast`, `niedopuszczalne`, `błąd`, `błędem`, `usuń`, `musi`, `muszą`, `zawsze`, `nigdy`), skrótu `np.`, cytowanych zdań w apostrofach/cudzysłowach oraz słów ALL-CAPS wewnątrz zdania.
5. **ZAKAZ 5 (Z3 / Primary LLM Authority):** Zakaz wprowadzania deterministycznych podmian tekstu w `rules.py` — kategorie pełnią wyłącznie funkcję instrukcji dla modelu LLM.
6. **ZAKAZ 6 (Z4 / Instance-Free):** Wszystkie wzorce regularne w `get_focused_rules_for_batch` muszą operować wyłącznie na kategoriach językowych, strukturach składniowych i sufiksach.
7. **ZAKAZ 7 (Ochrona struktury 10.2):** Nie przepisuj od nowa i nie usuwaj istniejących kategorii `BASE_1`–`BASE_4` ani `DYN_1`–`DYN_8` wdrożonych w `51dbe2d` — wykonaj wyłącznie ich punktowe uzupełnienie i oczyszczenie domenowe zdefiniowane w SEKCJI 1 i SEKCJI 2.
8. **ZAKAZ 8 (Kontrola rozmiaru `STANDARD_9_CORE_RULES_PROMPT`):** Rozszerzenie `BASE_2` (`R1.7`) nie może zwiększyć rozmiaru `STANDARD_9_CORE_RULES_PROMPT` o więcej niż `100` znaków (`<3%`).
9. **ZAKAZ 9 (Ochrona `series_memory/`):** Bezwzględny zakaz modyfikacji jakichkolwiek plików w `series_memory/`.
10. **ZAKAZ 10 (Brak placeholderów):** W finalnym `Artefakty/Raport_wdrozenia_10.3.md` nie może pozostać ani jeden znacznik `<DO_WYPEŁNIENIA>`.
11. **ZAKAZ 11 (Trigger `DYN_9` — brak pojedynczych słów ogólnych):** Trigger `DYN_9` nie może aktywować się na pojedynczych słowach `love`, `heart`, `feelings`, `memories`, `gentle`, `warmth`, `precious`, `beloved`, `lonely`, `regret` — wymagane są frazy z grupy (a) lub ≥2 różne markery z grupy (b).
12. **ZAKAZ 12 (Trigger `DYN_6` — brak idiomów):** Trigger `DYN_6` nie może aktywować się na idiomach potwierdzenia/acknowledgmentu (`yes`, `yeah`, `ok`, `well`, `now`, `there`, `oh`, `ah`, `sure`, `right`, `fine`, `good`, `thanks`, `hello`, `bye`) w podwójnym powtórzeniu.
13. **ZAKAZ 13 (Zero przykładów i obcojęzycznych terminów-kotwic w treści Filarów wysyłanych do LLM):** W tekstach i tytułach kategorii `DYN_1` – `DYN_9` przekazywanych do `add_rule(...)` obowiązuje całkowity zakaz umieszczania przykładowych słów oraz obcojęzycznych terminów technicznych (`dajare`, `giongo`, `gitaigo`, `chūnibyō`, `character voice`, `rōjin-go`, `keigo`, `yobisute`, `ottotto`, `kakegoe`, `kanojo-tachi`, `bento`, `onigiri`, `senpai`). Tekst kategorii musi operować wyłącznie na polskich nazwach domen językowych.

---

## SEKCJA 7 — KNOWN RISKS I BACKLOG

### 7.1. Known risks (ryzyka zidentyfikowane w audycie + z analizy poprawek)

1. **`R1` — Ryzyko nadmiernego zwiększenia rozmiaru promptu bazowego przy rozszerzeniu `BASE_2` (`L-02`):**
   - **Mitygacja:** Modyfikacja `R1.7` polega na dopisaniu zaledwie kilku słów (`14–15 znaków na sekundę`) wewnątrz istniejącego zdania `R1.7`, co zwiększa prompt bazowy o ok. 40 znaków (`<1%`), a `L-05` skierowano do `DYN_6` zamiast `BASE_3`.
2. **`R2` — Ryzyko zbyt szerokiego triggera dla nowej kategorii `DYN_9` (Ładunek afektywny):**
   - **Mitygacja:** Trigger `DYN_9` został zawężony do fraz wysokiej pewności (`miss you`, `farewell`, `loneliness`, `tears of`, `namida`, `sayonara`) oraz wymaga ≥2 różnych markerów dla fraz wspierających. Test `T10.3_2 (a)` weryfikuje brak aktywacji na `"I love this food!"`, `"My heart is beating fast"`, `"That is a precious memory"`.
3. **`R3` — Ryzyko kolizji rozszerzonego `DYN_1` lub `DYN_9` z `DYN_5`:**
   - **Mitygacja:** `DYN_1` (score 95) i `DYN_2` (score 92) zachowują najwyższe priorytety i są chronione przez `Anti-Smoothing Filter`. `DYN_9` (score 74) jest również chroniony przez `Anti-Smoothing Filter` w scenach lirycznych, bez blokowania `DYN_5` (`score 82`) w scenach walki.
4. **`R4` — Ryzyko naruszenia `verify_purity.py` (12/12) lub kotwiczenia modelu w Fazie 2 przez przykłady/terminy obce:**
   - **Mitygacja:** Operacja `2B.4`, ZAKAZ 13 oraz test `T10.3_3 (b)` gwarantują, że wszystkie 9 kategorii dynamicznych operuje wyłącznie na czystych domenach bez przykładów i terminów obcojęzycznych.
5. **`R5` — Ryzyko naruszenia Z16 (`TRANSLATION_RULES_PROMPT` lub `test_system.py`):**
   - **Mitygacja:** ZAKAZ 1 i ZAKAZ 2; `git diff 51dbe2d..HEAD -- test_system.py` musi być pusty.
6. **`R6` — Ryzyko fałszywego pozytywu na zwykłym dialogu przy detekcji powtórzeń w `DYN_6` (`L-05`):**
   - **Mitygacja:** Wzorzec został podzielony na dwa (potrójne+ dowolne, podwójne tylko „urgentne”) z wykluczeniem idiomów (`yes`, `well`, `now`, `there`, `oh`, `ah`, `sure`, `right`, `fine`, `good`, `thanks`, `hello`, `bye`) — test `T10.3_2 (b)` weryfikuje brak fałszywych pozytywów.
7. **`R7` — Ryzyko duplikacji treści między `DYN_5` (fizjologia krzyku/walki) a `DYN_9` (ładunek afektywny tekstu w scenach lirycznych):**
   - **Mitygacja:** `DYN_5` i `DYN_9` są całkowicie ortogonalne: `DYN_5` dotyczy kinezjologii walki, zadyszki i somatycznych okrzyków wysiłkowych, natomiast `DYN_9` dotyczy słownictwa uczuciowego, melancholii i czułości w scenach lirycznych.
8. **`R8` — Ryzyko wpływu zmiany `score` `DYN_5` (`120 → 82`) na istniejący test `T10.2_2`:**
   - **Mitygacja:** Wartość `82` umieszcza `DYN_5` powyżej `DYN_6` (`80`), dzięki czemu w scenie walki z powtórzeniem `DYN_5` ma pierwszeństwo przed `DYN_6` (weryfikowane przez `T10.3_2 (e)`), zachowując pełną kompatybilność z `T10.2_2`.
9. **`R9` — Ryzyko pominięcia `L-06` w backlogu 10.4:**
   - **Mitygacja:** `L-06` (szablony kontekstowe w `profiler.py`) jest jawnie wymienione w warunku ukończenia `(n)` oraz w Sekcji 7 szablonu raportu jako przeniesione do backlogu `10.4`.

### 7.2. Backlog 10.4 (poza zakresem 10.3)

**`L-06` (P2):** Rozbudowa generatora `EPISODE BRIEF` w `profiler.py` o automatyczną ekstrakcję adnotacji dla gier słownych i aluzji kulturowych na wzór szablonów STAW. Wymaga wpisu w backlogu `10.4`. **Nie jest to przedmiotem niniejszego promptu.**

---

## TEMPLATE RAPORTU WDROŻENIA (`Artefakty/Raport_wdrozenia_10.3.md`)

~~~markdown
# RAPORT WDROŻENIA STANDARDU 10.3 (DOPEŁNIENIE KATEGORII WYKONAWCZYCH AVT)

## 0. DIAGNOSTYKA WSTĘPNA (FAZA 0)
- **Surowe wyjścia 4 komend diagnostycznych (P0.2):** `<wklej surowe wyjścia>`
- **Potwierdzenie stanu wejściowego (`51dbe2d`):** `<opis>`

## 1. METADANE GIT
- **Commit bazowy:** `51dbe2d`
- **Commit docelowy (10.3):** `<HASH>`

## 2. TABELA REALIZACJI OPERACJI (2B.1 – 2B.6)
| Operacja | Luka (ID) | Status (`WDROŻONA`) | Lokalizacja (`plik:linie`) | Opis zmiany |
| :---: | :---: | :---: | :--- | :--- |
| `2B.1` | `L-01` | `WDROŻONA` | `rules.py:...` | ... |
| `2B.2` | `L-02` | `WDROŻONA` | `rules.py:...` | ... |
| `2B.3` | `L-03` | `WDROŻONA` | `rules.py:...` | ... |
| `2B.4` | `L-04` | `WDROŻONA` | `rules.py:...` | ... |
| `2B.5` | `L-05` | `WDROŻONA` | `rules.py:...` | ... |
| `2B.6` | `L-01..L-05` | `WDROŻONA` | `tests/test_profiler.py:...` | ... |

## 3. CYTATY KODU PO NAPRAWIE
- Zaktualizowane `R1.7` w `STANDARD_9_CORE_RULES_PROMPT`
- Zaktualizowana postać `get_focused_rules_for_batch` (`DYN_1` – `DYN_9`) w `rules.py` (100% czyste domeny bez przykładów i terminów obcych)
- Zaktualizowany `Anti-Smoothing Filter` (ochrona `DYN_1`, `DYN_2`, `DYN_9`)
- Nowe testy `T10.3_1` – `T10.3_4` w `tests/test_profiler.py`

## 4. WYNIKI 4 BRAMEK KWALIFIKACYJNYCH CI/CD (SUROWE WYJŚCIA)
- `verify_purity.py`: `<surowe wyjście>`
- `verify_12_fixes.py`: `<surowe wyjście>`
- `verify_ultimate_pipeline.py`: `<surowe wyjście>`
- `audit_diff.ps1`: `<surowe wyjście>`

## 5. WYNIKI PYTEST I POTWIERDZENIE NIENARUSZALNOŚCI Z16 ORAZ BIBLES
- `pytest tests/ -q`: `<surowe wyjście>`
- `pytest -q`: `<surowe wyjście>`
- `git diff 51dbe2d..HEAD --stat -- series_memory/ test_system.py avt_linter.py pytest.ini`: `<surowe wyjście>`

## 6. CHECKLISTA WARUNKÓW UKOŃCZENIA (a)–(n)
- [x] (a) ... [x] (n)
- **Werdykt końcowy:** `PASS`

## 7. BACKLOG 10.4
- **`L-06`** — rozbudowa `EPISODE BRIEF` w `profiler.py` o ekstrakcję adnotacji humoru/aluzji (szablony STAW). Wpis w backlogu 10.4: `ODNOTOWANO`.
~~~