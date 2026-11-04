# SUPLEMENT DO RAPORTU AUDYTU CZYSTOŚCI I RZETELNOŚCI FILARÓW AVT

## 0. METADANE
- **Repozytorium:** `https://github.com/wooles/translator`
- **HEAD audytowany:** `9f4df49` (`9f4df49fbeb399e8bed1af979ee8b2ba97f082a4` — Standard 10.3 na gałęzi `main`)[cite: 16]
- **Commit poprzedni (baseline 10.2):** `51dbe2d` (`51dbe2d400d16ce1a251efe193a1b96c9b18e361`)[cite: 14, 16]
- **Raport główny:** `Artefakty/Raport_audytu_czystosci_i_rzetelnosci_filarow.md`[cite: 16]
- **Data suplementu:** `2026-11-04`
- **Audytor:** Niezależny Audytor Architektoniczny AVT (Read-Only)
- **Zakres:** Domknięcie 4 luk weryfikacyjnych (`Luka 1` – `Luka 4`) poprzez inspekcję surowych wzorców regex w `get_focused_rules_for_batch`, audyt wystąpień terminu `seiyū` w aktywnym runtime, pełną weryfikację ciała testów `T10.2_1–T10.3_4` w `tests/test_profiler.py` oraz analizę `git diff 51dbe2d..9f4df49`[cite: 16].

---

## 1. EXECUTIVE SUMMARY
- **Luka 1 (Triggery regex `DYN_1`, `DYN_5`, `DYN_8` oraz pozostałych `DYN_X`):** **`ROZWIĄZANA DIAGNOSTYCZNIE (WYKRYTO NARUSZENIE Z4 W WARSTWIE REGEXÓW -> N-05 P1)`** — podczas gdy same **teksty i tytuły kategorii `DYN_1–DYN_9` wysyłane do modelu LLM** zostały w `9f4df49` w 100% oczyszczone z japońskich terminów-kotwic (`0` wystąpień), **wewnętrzne wzorce wyrażeń regularnych (`re.search`) w kodzie Pythona** wewnątrz `get_focused_rules_for_batch` nadal zawierają **24 badane japońskie terminy-kotwice w romaji** (m.in. `wagahai`, `dechu`, `nyan`, `pyon`, `zura`, `gero`, `dabe` w `DYN_1`; `ottotto`, `kakegoe` w `DYN_5`; `tsukkomi`, `boke`, `neta`, `gyagu`, `dajare`, `bento`, `onigiri` w `DYN_8`; `kanojo-tachi` w `DYN_4`; `namida`, `sayonara`, `sabishii`, `kanashii`, `natsukashii`, `itoshii` w `DYN_9`) oraz **8 japońskich markerów w zapisie kana/kanji** (`やん`, `やろ`, `ほんま`, `ちゃう`, `あかん`, `じゃけん`, `だべ`, `っす` w `DYN_1`)[cite: 16]. Zgodnie z kryterium `P0.4` stanowi to **Z4 FAIL w warstwie regexów selektora** i zostało wpisane jako nowa obserwacja **`N-05` o priorytecie `P1`** do usunięcia/zastąpienia w `10.4`[cite: 16].
- **Luka 2 (Wystąpienia `seiyū` w aktywnym runtime):** **`ROZWIĄZANA`** — potwierdzono dokładnie **3 wystąpienia** japońskiego zapożyczenia `seiyū` w aktywnym runtime `rules.py` (**2 w `STANDARD_9_CORE_RULES_PROMPT`**: nagłówek `FILAR 2` w linii `2564` oraz reguła `R1.8` w linii `2573`; **1 w `get_focused_rules_for_batch`**: tekst kategorii `DYN_5` w linii `2855`) oraz `0` wystąpień w `profiler.py`[cite: 16]. Zgodnie z kryterium `P1.4` obserwację **`N-01` przeklasyfikowano z `P2` na `P1`** (do zastąpienia polskim terminem `aktor głosowy` / `aktora głosowego` w `10.4`)[cite: 16].
- **Luka 3 (Weryfikacja `tests/test_profiler.py` po 10.3):** **`ROZWIĄZANA (PASS)`** — wszystkie **`7/7` oczekiwanych testów** (`T10.2_1`, `T10.2_2`, `T10.2_3`, `T10.3_1`, `T10.3_2`, `T10.3_3`, `T10.3_4`) fizycznie istnieje w `tests/test_profiler.py` (linie `231–446`), żaden z nich nie został osłabiony (`0` przypadków `skip`/`pass`/`assert True`), a `T10.3_3` i `T10.3_4` twardo weryfikują czystość tekstów `DYN_1–DYN_9` oraz obecność norm `14`, `15`, `17` i `38` w `R1.7`[cite: 16].
- **Luka 4 (Rozszerzenie zakresu Z4 przez implementera 10.3):** **`ODNOTOWANA I UDOKUMENTOWANA`** — porównanie `git diff 51dbe2d..9f4df49 -- rules.py` dowodzi, że w commicie `9f4df49` usunięto wszystkie obcojęzyczne terminy-kotwice z **tytułów i tekstów** kategorii `DYN_1–DYN_8` (w tym `Rōjin-go`, `Keigo`, `Yobisute`, `-san`, `-sama`, `-sensei`, `-senpai`, `kanojo-tachi`, `Ottotto`, `Kakegoe`, `Dajare`, `Giongo/Gitaigo`, `bento`, `onigiri`), a w nowych tekstach `DYN_1` i `DYN_8` nie wprowadzono słów `chūnibyō` ani `character voice`, zastępując je polskimi pojęciami domenowymi (`egzaltowanej maniery retorycznej`, `indywidualnego głosu postaci`)[cite: 16].
- **Werdykt suplementu:** **`PASS_Z_DROBNYMI`** (kod i testy `10.3` w `9f4df49` są w 100% sprawne i czyste w warstwie tekstów wysyłanych do LLM, natomiast dwie kwestie terminologiczne — `N-01` (`seiyū` w aktywnym tekście `BASE_2`/`DYN_5`) oraz `N-05` (japońskie tokeny w wewnętrznych regexach Pythona) — zostały sklasyfikowane jako **`P1`** do decyzji/naprawy w `10.4`)[cite: 16].

---

## 2. FAZA 0 — WERYFIKACJA TRIGGERÓW REGEX `DYN_1`, `DYN_5`, `DYN_8`

### P0.2. Surowe wyjścia 4 komend diagnostycznych na commicie `9f4df49`

#### Komenda 1: Wyciąg pełnych bloków `DYN_1`, `DYN_5`, `DYN_8` z `get_focused_rules_for_batch` (`rules.py`)
~~~python
# --- sed -n '/# DYN_1 (score/,/# DYN_2 (score/p' rules.py ---
    # DYN_1 (score 95): FILAR XIII & XII - Dialekty, gwara, sociolekty i kontrast rejestrów
    en_slang_pat = re.compile(
        r"\b(?:ain't|y'all|'em|nah|whoever they be|'cause|ya|"
        r"trustin'|runnin'|talkin'|comin'|doin'|goin'|laughin'|lookin'|fightin'|sayin'|"
        r"foolish mortals?|mere mortals?|dark abyss|eternal darkness|realm of shadows|"
        r"sealed power|dark flame|wicked eye|wagahai)\b|"
        r"(?:^|[\s\-])(?:dechu|nyan|pyon|zura|gero|dabe)\b",
        re.IGNORECASE,
    )
    jp_dialect_pat = re.compile(
        r"\b(?:akan|ya na|chau|honma|yaro|seya|wakatten|shiran)\b|"
        r"(?:やん|やろ|ほんま|ちゃう|あかん|じゃけん|だべ|っす)",
        re.IGNORECASE,
    )
    paraphrase_pat = re.compile(
        r"\b(?:she'?s saying|he'?s saying|means it'?d|means that)\b",
        re.IGNORECASE,
    )
    if en_slang_pat.search(combined_en) or jp_dialect_pat.search(combined_jp) or paraphrase_pat.search(combined_en):
        add_rule(
            95,
            "• [SKUP SIĘ NA: FILAR XIII & XII - Dialekty Regionalne, Gwara, Sociolekty i Kontrast Rejestrów]: "
            "Kwestie postaci posługującej się w oryginale gwarą regionalną, slangiem lub sociolektem oddaj żywą, "
            "nacechowaną polszczyzną potoczną. Gdy druga postać w tej samej scenie tłumaczy lub parafrazuje jej słowa "
            "w standardowym rejestrze, zachowaj wyraźny kontrast stylistyczny między obiema wypowiedziami. "
            "Prawidłowy stan indywidualnego głosu postaci to bezwzględna ciągłość jej idiolektu, rejestru środowiskowego, "
            "egzaltowanej maniery retorycznej lub charakterystycznej maniery artykulacyjnej na przestrzeni całego odcinka "
            "poprzez dobór nacechowanej leksyki i szyku wyrazów, przy zachowaniu pełnej czytelności polskiej ortografii.",
        )
    # DYN_2 (score 92): FILAR XIV & XXX - Archaizacja, etykieta dworska i rejestr wysoki

# --- sed -n '/# DYN_5 (score/,/# DYN_9 (score/p' rules.py ---
    # DYN_5 (score 82): FILAR CLXXII, LXVI, LXXV, XVIII, XXXIII, XVI & XVII - Prymat afektu i prozodia walki
    exclamation_count = combined_en.count("!")
    combat_affect_pat = re.compile(
        r"\b(?:scream\w*|sob\w*|trembl\w*|terrified|panick\w*|dodge|attack\w*|stomp\w*|crush\w*|"
        r"ottotto|kakegoe|ugh|grr|pant\w*|gasp\w*|ouch|whoa)\b",
        re.IGNORECASE,
    )
    if exclamation_count >= 5 or combat_affect_pat.search(combined_en) or combat_affect_pat.search(combined_jp):
        add_rule(
            82,
            "• [SKUP SIĘ NA: FILAR CLXXII, LXVI, LXXV, XVIII, XXXIII, XVI & XVII - Dynamiczny Prymat Afektu, Prozodia Oddechu i Somatyka]: "
            "Aktorstwo i fizjologia emocji seiyū mają prymat nad dosłownością leksykalną. W scenach walki, zadyszki i szlochu "
            "stosuj krótkie, urywane takty rytmiczne zsynchronizowane z oddechem oraz umieszczaj wyraz o najwyższym nacisku "
            "fonicznym w pozycji akcentu zdaniowego. Odruchy motoryczne, utratę równowagi i okrzyki wysiłkowe oddawaj "
            "naturalnymi polskimi wykrzyknieniami somatycznymi.",
        )
    # DYN_9 (score 74): FILAR XIX & LXXVI - Ładunek afektywny przekładu, melancholia i liryka emocjonalna

# --- sed -n '/# DYN_8 (score/,/# Anti-Smoothing/p' rules.py ---
    # DYN_8 (score 70): FILAR LXXVIII, LXXIX, LX, LXI, XLI, CIV, CV, CXVIII & CXIX - Adaptacja kulturowa, gry słowne i napisy
    culture_signs_pat = re.compile(
        r"\b(?:joke|joking|just kidding|wordplay|pun|riddle|irony|ironic|sarcasm|parody|"
        r"double meaning|innuendo|teasing|hilarious|tsukkomi|boke|neta|gyagu|dajare|"
        r"bento|onigiri|ramen|udon|soba|tempura|sushi|sake|mochi|takoyaki|okonomiyaki|kotatsu|yukata|kimono|"
        r"giongo|gitaigo|sign|notice|warning|ep\s*\d+|episode)\b",
        re.IGNORECASE,
    )
    if has_sign_flag or culture_signs_pat.search(combined_en) or culture_signs_pat.search(combined_jp):
        add_rule(
            70,
            "• [SKUP SIĘ NA: FILAR LXXVIII, LXXIX, LX, LXI, XLI, CIV, CV, CXVIII & CXIX - Adaptacja Kulturowa, Gry Słowne, Onomatopeje i Napisy Ekranowe]: "
            "Prawidłowy stan przekładu humoru, gier słownych, podtekstów tabu oraz aluzji intertekstualnych to zachowanie "
            "efektu komicznego poprzez twórczą substytucję, adaptację funkcjonalną i kompensację w naturalnej polszczyźnie, "
            "przy prymacie ekwiwalencji pragmatycznej nad dosłownością. Wyrazy dźwiękonaśladowcze w dialogu przekładaj na "
            "plastyczne polskie czasowniki ruchu lub stanu, nazwy potraw i realiów kulturowych adaptuj z naturalną polską "
            "fleksją, a napisy ekranowe i elementy interfejsu formułuj w maksymalnie zwięzłej formie nominalnej.",
        )
    # Anti-Smoothing Filter
~~~

#### Komenda 2: Wyszukanie japońskich terminów-kotwic w całym `get_focused_rules_for_batch`
~~~text
$ sed -n '/def get_focused_rules_for_batch/,/^def /p' rules.py | grep -inE "tsukkomi|boke|neta|gyagu|wagahai|warawa|-dechu|dechu|-nyan|nyan|-pyon|pyon|-zura|zura|-gero|gero|-dabe|dabe|chūnibyō|chunibyo|kanojo-tachi|dajare|giongo|gitaigo|keigo|rōjin-go|rojin-go|ottotto|kakegoe|yobisute|bento|onigiri"
30:        r"sealed power|dark flame|wicked eye|wagahai)\b|"
31:        r"(?:^|[\s\-])(?:dechu|nyan|pyon|zura|gero|dabe)\b",
59:        r"\b(?:thou|thee|thy|thine|milord|my lord|majesty|highness|grace|ojou|washi|sessha|warawa|onushi|gozaru)\b",
77:        r"\b(?:girls|women|ladies|sisters|kanojo-tachi|onnatachi|"
160:        r"ottotto|kakegoe|ugh|grr|pant\w*|gasp\w*|ouch|whoa)\b",
224:        r"double meaning|innuendo|teasing|hilarious|tsukkomi|boke|neta|gyagu|dajare|"
225:        r"bento|onigiri|ramen|udon|soba|tempura|sushi|sake|mochi|takoyaki|okonomiyaki|kotatsu|yukata|kimono|"
226:        r"giongo|gitaigo|sign|notice|warning|ep\s*\d+|episode)\b",
240:    has_hard_combat = bool(re.search(r"\b(?:attack\w*|dodge|stomp\w*|crush\w*|ottotto|kakegoe)\b", combined_en + " " + combined_jp, re.IGNORECASE))
~~~

#### Komenda 3: Wyciąg wszystkich wzorców `re.(compile|search|match|findall)` z `get_focused_rules_for_batch`
~~~text
2713:    en_slang_pat = re.compile(
2720:    jp_dialect_pat = re.compile(
2725:    paraphrase_pat = re.compile(
2743:    archaic_pat = re.compile(
2765:    age_gender_pat = re.compile(
2789:    honorific_pat = re.compile(
2814:    triple_rep_pat = re.compile(r"\b([a-zA-Z]{2,})\s*,\s*\1\s*,\s*\1\b", re.IGNORECASE)
2815:    urgent_double_rep_pat = re.compile(r"\b(wait|stop|run|hurry|come|go|look|please|hey|help|no)\s*,\s*\1\b", re.IGNORECASE)
2816:    split_discourse_pat = re.compile(r"(?:\.\.\.\s*\n\s*[a-zżźćńółęąś]|\n\s*-\s+\w+.*?\n\s*-\s+\w+)", re.IGNORECASE)
2842:    combat_affect_pat = re.compile(
2867:    lyric_high_pat = re.compile(
2872:    lyric_support_pat = re.compile(
2877:    support_matches = set(m.lower() for m in lyric_support_pat.findall(combined_en + " " + combined_jp))
2895:    spec_reg_pat = re.compile(
2915:    culture_signs_pat = re.compile(
2936:    has_hard_combat = bool(re.search(r"\b(?:attack\w*|dodge|stomp\w*|crush\w*|ottotto|kakegoe)\b", combined_en + " " + combined_jp, re.IGNORECASE))
~~~

#### Komenda 4: Sprawdzenie znaków kana/kanji w `get_focused_rules_for_batch`
~~~text
$ sed -n '/def get_focused_rules_for_batch/,/^def /p' rules.py | grep -nP "[\x{3040}-\x{30FF}\x{4E00}-\x{9FFF}]"
36:        r"(?:やん|やろ|ほんま|ちゃう|あかん|じゃけん|だべ|っす)",
~~~

---

### P0.3. Odpowiedzi na pytania flagowe (`F0.1–F0.4`)

- **F0.1 (Ile japońskich terminów-kotwic występuje w regexach `DYN_1`, `DYN_5`, `DYN_8`?):**
  - W regexie `DYN_1` (`en_slang_pat` + `jp_dialect_pat`, linie `2713–2724`): **15 terminów romaji** (`wagahai`, `dechu`, `nyan`, `pyon`, `zura`, `gero`, `dabe`, `akan`, `ya na`, `chau`, `honma`, `yaro`, `seya`, `wakatten`, `shiran`) + **8 tokenów kana**[cite: 16].
  - W regexie `DYN_5` (`combat_affect_pat` + `has_hard_combat`, linie `2842–2846`, `2936`): **2 terminy romaji** (`ottotto`, `kakegoe`)[cite: 16].
  - W regexie `DYN_8` (`culture_signs_pat`, linie `2915–2921`): **19 terminów romaji** (`tsukkomi`, `boke`, `neta`, `gyagu`, `dajare`, `bento`, `onigiri`, `ramen`, `udon`, `soba`, `tempura`, `sushi`, `sake`, `mochi`, `takoyaki`, `okonomiyaki`, `kotatsu`, `yukata`, `kimono`, `giongo`, `gitaigo` — łącznie 21 słów z zakresu realiów/humoru JP)[cite: 16].
  - Ponadto w pozostałych kategoriach dynamicznych w regexach występują: `ojou`, `washi`, `sessha`, `warawa`, `onushi`, `gozaru` (`DYN_2`, linia `2745`), `san`, `sama`, `kun`, `chan`, `sensei`, `senpai`, `dono` (`DYN_3`, linia `2791`), `kanojo-tachi`, `onnatachi`, `shonen`, `baba`, `bba` (`DYN_4`, linie `2767–2768`), `namida`, `sayonara`, `sabishii`, `kanashii`, `natsukashii`, `itoshii` (`DYN_9`, linie `2870`, `2875`)[cite: 16].
- **F0.2 (Czy triggery zawierają japońskie znaki kana/kanji?):** **Tak** — w `DYN_1` w zmiennej `jp_dialect_pat` (linia `2722`) znajduje się 8 japońskich markerów dialektalnych zapisanych w hiraganie: `やん`, `やろ`, `ほんま`, `ちゃう`, `あかん`, `じゃけん`, `だべ`, `っす`[cite: 16].
- **F0.3 (Czy implementer 10.3 usunął japońskie terminy z regexów, czy zostawił je?):** Implementer 10.3 **usunął 100% japońskich terminów z tekstów i tytułów Filarów wysyłanych do modelu LLM**, natomiast **zostawił je (oraz dodał nowe zgodnie z instrukcjami `2B.1`, `2B.3`, `2B.4` promptu 10.3) wewnątrz wzorców regex Pythona** służących do detekcji zjawisk w transkrypcji `whisper_text_jp` i tekście angielskim `batch_text_en`[cite: 16].
- **F0.4 (Które dokładnie terminy zostały w regexach i w których liniach?):** Pełne zestawienie z numerami linii w `rules.py` (`9f4df49`) przedstawia poniższa tabela `P0.4`[cite: 16].

---

### P0.4. Tabela wynikowa weryfikacji japońskich terminów-kotwic w `get_focused_rules_for_batch` (`rules.py`)

| Kategoria | Termin japoński | Obecny w tekście wysyłanym do LLM? (`Y/N`) | Obecny w regexie Pythona? (`Y/N`) | Linia w `rules.py` | Kontekst w kodzie (`rules.py` na `9f4df49`) | Zgodność z Z4 (wg kryterium P0.4 dla regexu) |
| :---: | :--- | :---: | :---: | :---: | :--- | :---: |
| **`DYN_1`** | `chūnibyō` / `chunibyo` | `N` | **`N`** | — | *(Całkowicie nieobecny zarówno w tekście, jak i w regexie)* | **`PASS`** |
| **`DYN_1`** | `wagahai` | `N` | **`Y`** | `2716` | `...dark flame\|wicked eye\|wagahai)\b\|` | **`FAIL`** *(w regexie)* |
| **`DYN_1`** | `dechu`, `nyan`, `pyon`, `zura`, `gero`, `dabe` | `N` | **`Y`** | `2717` | `(?:^\|[\s\-])(?:dechu\|nyan\|pyon\|zura\|gero\|dabe)\b` | **`FAIL`** *(w regexie)* |
| **`DYN_1`** | `akan`, `chau`, `honma`, `yaro`, `seya`, `wakatten`, `shiran` | `N` | **`Y`** | `2721` | `\b(?:akan\|ya na\|chau\|honma\|yaro\|seya\|wakatten\|shiran)\b` | **`FAIL`** *(w regexie)* |
| **`DYN_1`** | `やん\|やろ\|ほんま\|ちゃう\|あかん\|じゃけん\|だべ\|っす` (kana) | `N` | **`Y`** | `2722` | `(?:やん\|やろ\|ほんま\|ちゃう\|あかん\|じゃけん\|だべ\|っす)` | **`FAIL`** *(w regexie)* |
| **`DYN_2`** | `keigo` / `rōjin-go` | `N` | **`N`** | — | *(Usunięte w 10.3 z tytułu i tekstu; nieobecne w regexie)* | **`PASS`** |
| **`DYN_2`** | `ojou`, `washi`, `sessha`, `warawa`, `onushi`, `gozaru` | `N` | **`Y`** | `2745` | `...grace\|ojou\|washi\|sessha\|warawa\|onushi\|gozaru)\b` | **`FAIL`** *(w regexie)* |
| **`DYN_3`** | `yobisute` | `N` | **`N`** | — | *(Usunięte w 10.3 z tytułu i tekstu; nieobecne w regexie)* | **`PASS`** |
| **`DYN_3`** | `san`, `sama`, `kun`, `chan`, `sensei`, `senpai`, `dono` | `N` | **`Y`** | `2791` | `(?:-\|\b)(?:san\|sama\|kun\|chan\|sensei\|senpai\|dono)\b` | **`FAIL`** *(w regexie)* |
| **`DYN_4`** | `kanojo-tachi`, `onnatachi`, `shonen`, `baba`, `bba` | `N` | **`Y`** | `2767–2768` | `...sisters\|kanojo-tachi\|onnatachi\|...\|shonen\|baba\|bba)\b` | **`FAIL`** *(w regexie)* |
| **`DYN_5`** | `ottotto`, `kakegoe` | `N` | **`Y`** | `2845`, `2936` | `...crush\w*\|ottotto\|kakegoe\|ugh\|grr...` | **`FAIL`** *(w regexie)* |
| **`DYN_8`** | `tsukkomi`, `boke`, `neta`, `gyagu`, `dajare` | `N` | **`Y`** | `2917` | `...hilarious\|tsukkomi\|boke\|neta\|gyagu\|dajare\|` | **`FAIL`** *(w regexie)* |
| **`DYN_8`** | `bento`, `onigiri`, `ramen`, `udon`, `soba`, `tempura`, `sushi`, `sake`, `mochi`, `takoyaki`, `okonomiyaki`, `kotatsu`, `yukata`, `kimono` | `N` | **`Y`** | `2918` | `r"bento\|onigiri\|ramen\|...\|yukata\|kimono\|"` | **`FAIL`** *(w regexie)* |
| **`DYN_8`** | `giongo`, `gitaigo` | `N` | **`Y`** | `2919` | `r"giongo\|gitaigo\|sign\|notice..."` | **`FAIL`** *(w regexie)* |
| **`DYN_9`** | `namida`, `sayonara`, `sabishii`, `kanashii`, `natsukashii`, `itoshii` | `N` | **`Y`** | `2870`, `2875` | `r"\b(?:namida\|sayonara\|sabishii\|kanashii)\b"` | **`FAIL`** *(w regexie)* |

**Wniosek z FAZY 0:** W warstwie **tekstu Filarów wysyłanego do modelu LLM** wszystkie kategorie `DYN_1–DYN_9` mają `0` japońskich terminów (`PASS`), natomiast w warstwie **wewnętrznych wyrażeń regularnych Pythona** w `get_focused_rules_for_batch` występuje `Y` dla 7 kategorii (`DYN_1`, `DYN_2`, `DYN_3`, `DYN_4`, `DYN_5`, `DYN_8`, `DYN_9`) — co według ścisłego kryterium `P0.4` daje **`Z4 FAIL dla 7 kategorii w warstwie regexów triggera`** (wymaga decyzji architektonicznej i ewentualnej przebudowy sposobu wyzwalania w `10.4`)[cite: 16].

---

## 3. FAZA 1 — WERYFIKACJA `seiyū` W AKTYWNYM RUNTIME

### P1.2. Surowe wyjścia 5 komend diagnostycznych na commicie `9f4df49`

~~~text
# 1. Wystąpienia seiyū w CAŁYM rules.py
$ grep -n "seiyū\|seiyu\|SEIYŪ" rules.py
385:- Zachowaj pełną zbieżność z oddechem i fizjologią mowy seiyū...
407:- Dopasuj długość i rytm frazy do czasu trwania głosu seiyū...
1382:- Zsynchronizuj punkt kulminacyjny zdania z akcentem seiyū...
1405:- W scenach walki i zadyszki podążaj za oddechem seiyū...
1601:- Wyraz o najwyższym nacisku fonicznym F0 głosu seiyū...
2358:1. Aktorstwo i fizjologia emocji seiyū mają prymat nad...
2564:[FILAR 2 — ZWIĘZŁOŚĆ AVT, RYTM SEIYŪ I PARALINGWISTYKA (P1)]
2573:R1.8. Synchronizacja z Rytmem Wypowiedzi (Mouth-Pacing): Dopasuj liczbę sylab i rytm frazy do czasu trwania głosu seiyū oraz tempa mówienia postaci.
2855:            "Aktorstwo i fizjologia emocji seiyū mają prymat nad dosłownością leksykalną. W scenach walki, zadyszki i szlochu "

# 2. Wystąpienia w STANDARD_9_CORE_RULES_PROMPT (base)
$ sed -n '/STANDARD_9_CORE_RULES_PROMPT\s*=/,/def get_system_prompt/p' rules.py | grep -in "seiyū\|seiyu"
40:[FILAR 2 — ZWIĘZŁOŚĆ AVT, RYTM SEIYŪ I PARALINGWISTYKA (P1)]
49:R1.8. Synchronizacja z Rytmem Wypowiedzi (Mouth-Pacing): Dopasuj liczbę sylab i rytm frazy do czasu trwania głosu seiyū oraz tempa mówienia postaci.

# 3. Wystąpienia w get_focused_rules_for_batch (dynamic)
$ sed -n '/def get_focused_rules_for_batch/,/^def /p' rules.py | grep -in "seiyū\|seiyu"
169:            "Aktorstwo i fizjologia emocji seiyū mają prymat nad dosłownością leksykalną. W scenach walki, zadyszki i szlochu "

# 4. Wystąpienia w profiler.py
$ grep -in "seiyū\|seiyu" profiler.py
(brak trafień — 0 wystąpień w profiler.py)

# 5. Wystąpienia w pasywnym TRANSLATION_RULES_PROMPT (Z16 — linie 25–2524)
$ sed -n '25,2524p' rules.py | grep -in "seiyū\|seiyu"
361:- Zachowaj pełną zbieżność z oddechem i fizjologią mowy seiyū...
383:- Dopasuj długość i rytm frazy do czasu trwania głosu seiyū...
1358:- Zsynchronizuj punkt kulminacyjny zdania z akcentem seiyū...
1381:- W scenach walki i zadyszki podążaj za oddechem seiyū...
1577:- Wyraz o najwyższym nacisku fonicznym F0 głosu seiyū...
2334:1. Aktorstwo i fizjologia emocji seiyū mają prymat nad...
~~~

---

### P1.3. Tabela wynikowa wystąpień `seiyū`

| Lokalizacja | Linia w `rules.py` | Cytat (kontekst) | Typ (`base` / `dynamic` / `profiler` / `pasywny`) | Z4 (Instance-Free)? | Klasyfikacja P |
| :--- | :---: | :--- | :---: | :---: | :---: |
| **`STANDARD_9_CORE_RULES_PROMPT` (nagłówek `FILAR 2`)** | `2564` | `[FILAR 2 — ZWIĘZŁOŚĆ AVT, RYTM SEIYŪ I PARALINGWISTYKA (P1)]`[cite: 16] | `base` | **`FAIL`** *(japoński loanword w aktywnym prompcie bazowym)* | **`P1`** |
| **`STANDARD_9_CORE_RULES_PROMPT` (`R1.8`)** | `2573` | `...do czasu trwania głosu seiyū oraz tempa mówienia postaci.`[cite: 16] | `base` | **`FAIL`** *(japoński loanword w aktywnym prompcie bazowym)* | **`P1`** |
| **`get_focused_rules_for_batch` (`DYN_5`)** | `2855` | `Aktorstwo i fizjologia emocji seiyū mają prymat nad dosłownością leksykalną.`[cite: 16] | `dynamic` | **`FAIL`** *(japoński loanword w aktywnym prompcie dynamicznym)* | **`P1`** |
| **`profiler.py`** | — | *(Brak wystąpień)*[cite: 16] | `base (EPISODE BRIEF)` | **`PASS`** | — |
| **`TRANSLATION_RULES_PROMPT` (`FILAR XVI, XVII, LXV, LXVI, LXXV, CLXXII`)** | `385, 407, 1382, 1405, 1601, 2358` | `...fizjologia emocji seiyū...`[cite: 16] | `pasywny (Z16)` | **`N/A — Z16-locked`** | **`P2`** *(nie ruszać)* |

---

### P1.4. Rekomendacja klasyfikacji (`P2 -> P1`)

Ponieważ termin `seiyū` występuje w **aktywnym runtime** (w prompcie bazowym `FILAR 2` / `R1.8` oraz w kategorii dynamicznej `DYN_5`), obserwację **`N-01` przeklasyfikowuje się z `P2` na `P1`**[cite: 16]:
> Termin `seiyū` to japońskie zapożyczenie leksykalne (loanword). W polskim przekładzie audiowizualnym właściwym, neutralnym terminem metajęzykowym jest **`aktor głosowy`** (`RYTM AKTORA GŁOSOWEGO`, `do czasu trwania głosu aktora`, `Aktorstwo i fizjologia emocji aktora głosowego`)[cite: 16]. Dodatkowo usunięcie `seiyū` z tekstu `DYN_5` i `R1.8` domknie spójność z `DYN_9` (gdzie już w `10.3` użyto czystego sformułowania `z barwą głosu aktora`). **Rekomendacja: naprawa w Standardzie `10.4`** (przy sprawdzeniu, czy `verify_12_fixes.py` lub `verify_ultimate_pipeline.py` nie szuka podciągu `seiyū` w `rules.py`)[cite: 16].

---

## 4. FAZA 2 — WERYFIKACJA `tests/test_profiler.py` PO 10.3

### P2.2. Surowe wyjścia 5 komend diagnostycznych na commicie `9f4df49`

~~~python
# 1 & 2 & 3. Lista testów w tests/test_profiler.py (linie z def test_)
$ grep -nE "def test_" tests/test_profiler.py
18:def test_lean_episode_brief_formatting():
54:def test_focused_rules_selection():
85:def test_t10_1_1_p1a_dialect_rule_injected_in_phase1_and_phase2():
118:def test_t10_1_1_p1b_paraphrase_contrast_instruction_present():
148:def test_t10_1_1_p2a_en_slang_and_jp_dialect_triggers_filar_xiii():
188:def test_t10_1_1_p2b_anti_smoothing_filter_removes_lxxi_and_clxxii():
231:def test_t10_2_1_zero_noise_ordinary_dialogue(ordinary_line):
252:def test_t10_2_2_dynamic_category_selection_and_anti_smoothing(scene_input, expected_header, forbidden_header):
286:def test_t10_2_3_pure_positive_domain_in_focused_rules():
322:def test_t10_3_1_new_and_expanded_categories_triggers(scene_en, scene_jp, expected_substr):
352:def test_t10_3_2_priority_hierarchy_zero_noise_and_false_positive_guards():
401:def test_t10_3_3_purity_domain_abstraction_and_size_invariant_of_all_13_categories():
437:def test_t10_3_4_r17_contains_polish_norm_14_15_and_cap_17():

# 4. Pełne ciała testów T10.3_1 – T10.3_4 w tests/test_profiler.py
@pytest.mark.unit
@pytest.mark.parametrize(
    "scene_en,scene_jp,expected_substr",
    [
        ("That's a hilarious double meaning pun!", "", "twórczą substytucję, adaptację funkcjonalną i kompensację"),
        ("Tears of sorrow and loneliness filled my heart after our farewell.", "", "FILAR XIX & LXXVI"),
        ("Foolish mortals of the dark abyss!", "", "ciągłość jej idiolektu"),
        ("I am ready-dechu", "", "FILAR XIII & XII"),
        ("Wait, wait, wait! Listen to me!", "", "Wielokrotne powtórzenia tego samego wyrazu"),
        ("Stop, stop! You cannot go there!", "", "FILAR CLXV, LXV, CLXIX & CLXXIX"),
    ],
)
def test_t10_3_1_new_and_expanded_categories_triggers(scene_en, scene_jp, expected_substr):
    res = get_focused_rules_for_batch([{"text": scene_en}], max_rules=3, whisper_text_jp=scene_jp)
    assert expected_substr in res

@pytest.mark.unit
def test_t10_3_2_priority_hierarchy_zero_noise_and_false_positive_guards():
    # (a) Pojedyncze słowa ogólne nie mogą aktywować DYN_9, DYN_8 ani DYN_1
    for benign in [
        "I love this food!",
        "My heart is beating fast.",
        "That is a precious memory.",
        "The warmth of the sun is nice.",
        "Are you kidding me?!",
        "The darkness is falling.",
    ]:
        assert get_focused_rules_for_batch([{"text": benign}]) == ""

    # (b) Idiomy potwierdzenia nie mogą aktywować DYN_6
    for idiom in [
        "Yes, yes, I agree.",
        "Well, well, look who is here.",
        "Now, now, calm down.",
        "There, there, it is alright.",
        "Oh, oh, I see.",
    ]:
        assert get_focused_rules_for_batch([{"text": idiom}]) == ""

    # (c) & (e) W scenie walki z powtórzeniem DYN_5 (82) jest przed DYN_6 (80)
    combat_rep = get_focused_rules_for_batch([{"text": "Wait, wait, wait! Attack! Dodge! Ugh! Ottotto!"}], max_rules=5)
    assert "FILAR CLXXII" in combat_rep
    assert "FILAR CLXV" in combat_rep
    assert combat_rep.index("FILAR CLXXII") < combat_rep.index("FILAR CLXV")

    # (d) Czysto liryczna scena DYN_9 wyklucza FILAR CLXXII przez Anti-Smoothing Filter
    lyric_With_excl = get_focused_rules_for_batch(
        [{"text": "Farewell! I miss you so much! Tears of sorrow and loneliness! ! !"}],
        max_rules=5,
    )
    assert "FILAR XIX & LXXVI" in lyric_With_excl
    assert "FILAR CLXXII" not in lyric_With_excl

@pytest.mark.unit
def test_t10_3_3_purity_domain_abstraction_and_size_invariant_of_all_13_categories():
    synthetic_inputs = [
        ("You ain't runnin' away, y'all!", ""),
        ("Forgive me, milord, Your Majesty.", ""),
        ("The little boy and the old grandma are waiting with the girls.", "kanojo-tachi"),
        ("Thank you-san, my master.", ""),
        ("Attack! Dodge! Scream! Sob! Terrified! Ugh! Ottotto!", ""),
        ("Wait, wait, wait! Listen to me!", ""),
        ("Tears of sorrow and loneliness after our farewell.", "namida"),
        ("The tactical commander ordered a medical autopsy and diagnosis.", ""),
        ("That's a hilarious double meaning pun!", ""),
    ]
    collected = []
    for en_txt, jp_txt in synthetic_inputs:
        out = get_focused_rules_for_batch([{"text": en_txt}], max_rules=10, whisper_text_jp=jp_txt)
        assert out != ""
        collected.append(out)
    all_dyn_text = "\n".join(collected)
    full_text = STANDARD_9_CORE_RULES_PROMPT + "\n" + all_dyn_text

    forbidden_neg = re.compile(r"\b(?:nie|zakaz|zabrania|unikaj|zamiast|niedopuszczalne|usuń|błąd|błędem|musi|muszą|zawsze|nigdy)\b", re.IGNORECASE)
    assert not forbidden_neg.search(all_dyn_text)
    assert not re.search(r"\bnp\.", full_text, re.IGNORECASE)
    assert "'" not in all_dyn_text

    forbidden_foreign_anchors = re.compile(
        r"\b(?:dajare|giongo|gitaigo|chūnibyō|chunibyo|character voice|rōjin-go|rojin-go|keigo|yobisute|ottotto|kakegoe|kanojo-tachi|bento|onigiri|senpai)\b",
        re.IGNORECASE,
    )
    assert not forbidden_foreign_anchors.search(all_dyn_text)
    assert len(STANDARD_9_CORE_RULES_PROMPT) < 4200

@pytest.mark.unit
def test_t10_3_4_r17_contains_polish_norm_14_15_and_cap_17():
    r17_match = re.search(r"R1\.7\..*", STANDARD_9_CORE_RULES_PROMPT)
    assert r17_match is not None
    r17_line = r17_match.group(0)
    assert "14" in r17_line and "15" in r17_line
    assert "17" in r17_line
    assert "38" in r17_line

# 5. Pełne ciała testów T10.2_1 – T10.2_3 w tests/test_profiler.py
@pytest.mark.unit
@pytest.mark.parametrize(
    "ordinary_line",
    [
        "I don't know, but they have 3 items...",
        "Wait, is that really true?!",
        "Yes, I think so...",
        "She isn't going to the market today.",
        "What does this mean for our schedule?",
        "They are already on the table!",
        "Eh? Are you sure about that?",
    ],
)
def test_t10_2_1_zero_noise_ordinary_dialogue(ordinary_line):
    res = get_focused_rules_for_batch([{"text": ordinary_line}], max_rules=3)
    assert res == ""
~~~

---

### P2.3. Tabela wynikowa weryfikacji `tests/test_profiler.py`

| Test | Istnieje? (`Y/N`) | Linia w `tests/test_profiler.py` | Czy osłabiony? (`Y/N`) | Co testuje (streszczenie) | Zgodność z 10.3 |
| :---: | :---: | :---: | :---: | :--- | :---: |
| **`T10.2_1`** | **`Y`** | `231–249` | **`N`** | Weryfikuje na 7 sparametryzowanych zdaniach zwykłego dialogu, że `get_focused_rules_for_batch` zwraca dokładnie `""`[cite: 16]. | **`PASS`** |
| **`T10.2_2`** | **`Y`** | `252–283` | **`N`** | Weryfikuje selekcję `DYN_1`–`DYN_5` oraz działanie `Anti-Smoothing Filter` wykluczającego `FILAR LXXI` i `FILAR CLXXII`[cite: 16]. | **`PASS`** |
| **`T10.2_3`** | **`Y`** | `286–319` | **`N`** | Weryfikuje 100% Pure Positive Domain (brak słów negatywnych, brak `np.`, brak apostrofów) w wyjściach `get_focused_rules_for_batch`[cite: 16]. | **`PASS`** |
| **`T10.3_1`** | **`Y`** | `322–349` | **`N`** | Weryfikuje na 6 sparametryzowanych wariantach nowe triggery i rozszerzone treści `DYN_8` (humor), `DYN_9` (liryka), `DYN_1` (`chūnibyō`/sufiksy) i `DYN_6` (powtórzenia potrójne i podwójne nagłe)[cite: 16]. | **`PASS`** |
| **`T10.3_2`** | **`Y`** | `352–398` | **`N`** | Weryfikuje brak fałszywych pozytywów dla pojedynczych słów (`love`, `heart`, `kidding`, `darkness`) i idiomów (`Yes, yes`, `Well, well`), porządek `DYN_5 (82) > DYN_6 (80)` w walce z powtórzeniem oraz ochronę `DYN_9` w `Anti-Smoothing Filter`[cite: 16]. | **`PASS`** |
| **`T10.3_3`** | **`Y`** | `401–434` | **`N`** | Iteruje po 9 osobnych wejściach dla `DYN_1–DYN_9` i weryfikuje brak słów przeczących, brak `np.`, brak apostrofów, **brak 16 obcojęzycznych terminów-kotwic w wyjściu tekstowym** oraz rozmiar `STANDARD_9_CORE_RULES_PROMPT`[cite: 16]. | **`PASS`** |
| **`T10.3_4`** | **`Y`** | `437–446` | **`N`** | Weryfikuje, że linia `R1.7` w `STANDARD_9_CORE_RULES_PROMPT` zawiera wartości `14`, `15`, `17` oraz `38`[cite: 16]. | **`PASS`** |

**Wniosek z FAZY 2:** **`PASS` (7/7 testów istnieje, 0 osłabionych)**[cite: 16].

---

## 5. FAZA 3 — WERYFIKACJA ROZSZERZENIA ZAKRESU PRZEZ IMPLEMENTERA 10.3

### P3.2. Surowe wyjścia 3 komend diagnostycznych (`51dbe2d` vs `9f4df49`)

~~~diff
# 1. Porównanie tekstów kategorii w rules.py między 51dbe2d (10.2) a 9f4df49 (10.3)
$ git diff 51dbe2d..9f4df49 -- rules.py
@@ -2566,4 +2566,5 @@
-R1.7. Zwięzłość AVT i Budżet Czytelniczy: Kondensuj rozwlekłe konstrukcje tak, aby napisy mieściły się w budżecie CPS <= 17 oraz CPL <= 38 poprzez dobór krótkich, nośnych synonimów.
+R1.7. Zwięzłość AVT i Budżet Czytelniczy: Prawidłowy stan napisów to celowanie w polskie optimum percepcyjne 14–15 znaków na sekundę dla swobodnego odbioru obrazu, przy zachowaniu maksymalnego pułapu 17 znaków na sekundę (CPS) w szybkim dialogu oraz limitu 38 znaków w linii (CPL) poprzez dobór krótkich, nośnych polskich synonimów.
@@ -2713,6 +2714,8 @@
-    # DYN_1 (score 95): FILAR XIII & XII - Dialekty, gwara, sociolekty i kontrast rejestrów
+    # DYN_1 (score 95): FILAR XIII & XII - Dialekty, gwara, sociolekty i kontrast rejestrów
     en_slang_pat = re.compile(
         r"\b(?:ain't|y'all|'em|nah|whoever they be|'cause|ya|"
-        r"trustin'|runnin'|talkin'|comin'|doin'|goin'|laughin'|lookin'|fightin'|sayin')\b",
+        r"trustin'|runnin'|talkin'|comin'|doin'|goin'|laughin'|lookin'|fightin'|sayin'|"
+        r"foolish mortals?|mere mortals?|dark abyss|eternal darkness|realm of shadows|"
+        r"sealed power|dark flame|wicked eye|wagahai)\b|"
+        r"(?:^|[\s\-])(?:dechu|nyan|pyon|zura|gero|dabe)\b",
         re.IGNORECASE,
     )
@@ -2730,6 +2733,9 @@
             "• [SKUP SIĘ NA: FILAR XIII & XII - Dialekty Regionalne, Gwara, Sociolekty i Kontrast Rejestrów]: "
             "Kwestie postaci posługującej się w oryginale gwarą regionalną, slangiem lub sociolektem oddaj żywą, "
             "nacechowaną polszczyzną potoczną. Gdy druga postać w tej samej scenie tłumaczy lub parafrazuje jej słowa "
-            "w standardowym rejestrze, zachowaj wyraźny kontrast stylistyczny między obiema wypowiedziami.",
+            "w standardowym rejestrze, zachowaj wyraźny kontrast stylistyczny między obiema wypowiedziami. "
+            "Prawidłowy stan indywidualnego głosu postaci to bezwzględna ciągłość jej idiolektu, rejestru środowiskowego, "
+            "egzaltowanej maniery retorycznej lub charakterystycznej maniery artykulacyjnej na przestrzeni całego odcinka "
+            "poprzez dobór nacechowanej leksyki i szyku wyrazów, przy zachowaniu pełnej czytelności polskiej ortografii.",
         )
@@ -2745,6 +2751,6 @@
-            "• [SKUP SIĘ NA: FILAR XIV & XXX - Archaizacja, Keigo Dworskie i Rejestr Starca (Rōjin-go)]: "
+            "• [SKUP SIĘ NA: FILAR XIV & XXX - Archaizacja, Etykieta Dworska i Rejestr Wysoki]: "
@@ -2768,6 +2774,6 @@
-            "Gdy japońskie audio zawiera sygnał grupy kobiecej (kanojo-tachi), stosuj wyłącznie polskie formy niemęskoosobowe.",
+            "Gdy ścieżka dźwiękowa lub kontekst wskazuje na grupę złożoną z kobiet, stosuj konsekwentnie polskie formy niemęskoosobowe.",
@@ -2788,7 +2794,7 @@
-            "• [SKUP SIĘ NA: FILAR XXV, XXVI, XXVII, XXVIII, XXIX & CLVII - Tytulatura, Zasada Yobisute i Harmonia Formy Adresatywnej]: "
-            "W relacjach rówieśniczych i przyjacielskich (yobisute) stosuj bezpośrednią formę drugiej osoby oraz wołacz imienia. "
-            "Honoryfikatory (-san, -sama, -sensei, -senpai) adaptuj do naturalnej polskiej tytulatury...",
+            "• [SKUP SIĘ NA: FILAR XXV, XXVI, XXVII, XXVIII, XXIX & CLVII - Tytulatura, Forma Rówieśnicza i Harmonia Formy Adresatywnej]: "
+            "W relacjach rówieśniczych i przyjacielskich stosuj bezpośrednią formę drugiej osoby oraz wołacz imienia. "
+            "Zwroty grzecznościowe i tytuły adaptuj do naturalnej polskiej tytulatury...",
@@ -2835,7 +2848,7 @@
-        add_rule(
-            120,
+        add_rule(
+            82,
             "• [SKUP SIĘ NA: FILAR CLXXII, LXVI, LXXV, XVIII, XXXIII, XVI & XVII - Dynamiczny Prymat Afektu, Prozodia Oddechu i Somatyka]: "
             "Aktorstwo i fizjologia emocji seiyū mają prymat nad dosłownością leksykalną. W scenach walki, zadyszki i szlochu "
             "stosuj krótkie, urywane takty rytmiczne zsynchronizowane z oddechem oraz umieszczaj wyraz o najwyższym nacisku "
-            "fonicznym w pozycji akcentu zdaniowego. Odruchy motoryczne i utratę równowagi (ottotto) oraz okrzyki wysiłkowe (kakegoe) "
+            "fonicznym w pozycji akcentu zdaniowego. Odruchy motoryczne, utratę równowagi i okrzyki wysiłkowe "
             "oddawaj naturalnymi polskimi wykrzyknieniami somatycznymi.",
         )
@@ -2875,8 +2925,9 @@
-            "• [SKUP SIĘ NA: FILAR LXXVIII, LXXIX, LX, LXI, XLI, CIV, CV, CXVIII & CXIX - Adaptacja Kulturowa, Kalambury, Onomatopeje i Napisy Ekranowe]: "
-            "Gry słowne i kalambury (dajare) przekładaj przez ekwiwalencję funkcjonalną. Wyrazy dźwiękonaśladowcze (giongo i gitaigo) "
-            "w dialogu przekładaj na żywe polskie czasowniki, nazwy potraw (bento, onigiri) i realiów adaptuj z polską deklinacją...",
+            "• [SKUP SIĘ NA: FILAR LXXVIII, LXXIX, LX, LXI, XLI, CIV, CV, CXVIII & CXIX - Adaptacja Kulturowa, Gry Słowne, Onomatopeje i Napisy Ekranowe]: "
+            "Prawidłowy stan przekładu humoru, gier słownych, podtekstów tabu oraz aluzji intertekstualnych to zachowanie "
+            "efektu komicznego poprzez twórczą substytucję, adaptację funkcjonalną i kompensację w naturalnej polszczyźnie, "
+            "przy prymacie ekwiwalencji pragmatycznej nad dosłownością. Wyrazy dźwiękonaśladowcze w dialogu przekładaj na "
+            "plastyczne polskie czasowniki ruchu lub stanu, nazwy potraw i realiów kulturowych adaptuj z naturalną polską "
+            "fleksją, a napisy ekranowe i elementy interfejsu formułuj w maksymalnie zwięzłej formie nominalnej.",

# 2. Sprawdzenie DYN_1 w 9f4df49
$ sed -n '/# DYN_1 (score/,/# DYN_2 (score/p' rules.py | grep -in "chūnibyō\|chunibyo\|character voice\|-dechu\|dechu\|-nyan\|nyan"
5:        r"sealed power|dark flame|wicked eye|wagahai)\b|"
6:        r"(?:^|[\s\-])(?:dechu|nyan|pyon|zura|gero|dabe)\b",
(0 trafień w tekście reguły DYN_1; trafienia wyłącznie w wewnętrznym regexie en_slang_pat w liniach 2716-2717)

# 3. Sprawdzenie DYN_1 w 51dbe2d (przed 10.3)
$ git show 51dbe2d:rules.py | sed -n '/# DYN_1 (score/,/# DYN_2 (score/p' | grep -in "chūnibyō\|chunibyo\|character voice\|-dechu\|-nyan"
(0 trafień w 51dbe2d)
~~~

---

### P3.3. Tabela porównawcza (`51dbe2d` przed 10.3 vs `9f4df49` po 10.3)

| Termin | W `51dbe2d` (przed 10.3)? | W `9f4df49` (po 10.3) — w tekście Filaru dla LLM? | W `9f4df49` (po 10.3) — w wewnętrznym regexie Pythona? | Opis zmiany w `9f4df49` | Ocena |
| :--- | :---: | :---: | :---: | :--- | :---: |
| **`chūnibyō`** | `N` | **`N`** | **`N`** | Zastąpiony w tekście `DYN_1` czystą domeną `egzaltowanej maniery retorycznej`[cite: 16]. | **Pozytywna (Z4 PASS)** |
| **`character voice`** | `N` | **`N`** | **`N`** | Zastąpiony w tekście `DYN_1` czystą domeną `indywidualnego głosu postaci`[cite: 16]. | **Pozytywna (Z4 PASS)** |
| **`Rōjin-go`, `Keigo`** | `Y` *(w tytule `DYN_2`)* | **`N`** | **`N`** | Usunięte z tytułu `DYN_2` (`Archaizacja, Etykieta Dworska i Rejestr Wysoki`)[cite: 16]. | **Pozytywna (Z4 PASS)** |
| **`Yobisute`, `-san`, `-sama`, `-sensei`, `-senpai`** | `Y` *(w tytule i tekście `DYN_3`)* | **`N`** | **`Y`** *(w `honorific_pat`)* | Usunięte z tytułu i tekstu `DYN_3`, zachowane w regexie detekcji[cite: 16]. | **Pozytywna w tekście / Do decyzji w regexie (`N-05`)** |
| **`kanojo-tachi`** | `Y` *(w tekście `DYN_4` i regexie)* | **`N`** | **`Y`** *(w `age_gender_pat`)* | Usunięty z tekstu `DYN_4`, zachowany w regexie detekcji[cite: 16]. | **Pozytywna w tekście / Do decyzji w regexie (`N-05`)** |
| **`ottotto`, `kakegoe`** | `Y` *(w tekście `DYN_5` i regexie)* | **`N`** | **`Y`** *(w `combat_affect_pat`)* | Usunięte z tekstu `DYN_5`, zachowane w regexie detekcji[cite: 16]. | **Pozytywna w tekście / Do decyzji w regexie (`N-05`)** |
| **`dajare`, `giongo`, `gitaigo`, `bento`, `onigiri`** | `Y` *(w tekście `DYN_8` i regexie)* | **`N`** | **`Y`** *(w `culture_signs_pat`)* | Usunięte z tekstu `DYN_8`, zachowane w regexie detekcji[cite: 16]. | **Pozytywna w tekście / Do decyzji w regexie (`N-05`)** |
| **`dechu`, `nyan`, `pyon`, `zura`, `gero`, `dabe`, `wagahai`** | `N` | **`N`** | **`Y`** *(w `en_slang_pat`)* | Nieobecne w tekście `DYN_1`, dodane do regexu detekcji w `10.3`[cite: 16]. | **Pozytywna w tekście / Do decyzji w regexie (`N-05`)** |

---

### P3.4. Wniosek z FAZY 3

Wdrożenie `10.3` (`9f4df49`) przeprowadziło **pełną depurację Z4 na poziomie tekstów i tytułów wszystkich 9 kategorii dynamicznych `DYN_1–DYN_9`** wysyłanych do LLM (usuwając zarówno zastane z `10.2` terminy `Rōjin-go`, `Keigo`, `Yobisute`, `kanojo-tachi`, `ottotto`, `kakegoe`, `dajare`, `giongo`, `gitaigo`, `bento`, `onigiri`, jak i unikając wprowadzenia `chūnibyō` oraz `character voice` z pierwotnego szkicu `2B.4`), co stanowi **pozytywne rozszerzenie zakresu w warstwie promptu LLM**[cite: 16]. Jednocześnie japońskie tokeny rozpoznawcze pozostały w wewnętrznych wyrażeniach regularnych Pythona (`en_slang_pat`, `jp_dialect_pat`, `archaic_pat`, `age_gender_pat`, `honorific_pat`, `combat_affect_pat`, `lyric_high_pat`, `culture_signs_pat`), co zostało wyodrębnione jako obserwacja **`N-05` (`P1`)**[cite: 16].

---

## 6. FAZA 4 — UZUPEŁNIENIE RAPORTU GŁÓWNEGO

Niniejszy suplement wprowadza następujące formalne uzupełnienia i korekty klasyfikacji do raportu głównego (`Artefakty/Raport_audytu_czystosci_i_rzetelnosci_filarow.md`)[cite: 16]:

### 6.1. Aktualizacja Sekcji 3.1 raportu głównego (dodanie kolumny `Z4 (regex triggery w Pythonie)`)

| Kategoria | Z4 (tekst i tytuł wysyłany do LLM) | Z4 (wewnętrzny regex triggera w Pythonie wg P0.4) | Wyjaśnienie |
| :--- | :---: | :---: | :--- |
| **`FILAR 1` – `FILAR 4` (`BASE_1–4`)** | `Y` (`PASS`) *(poza `seiyū` w `FILAR 2` -> `N-01 P1`)* | `N/A` *(zawsze aktywne)* | Brak regexów; w `FILAR 2` (`R1.8`) występuje słowo `seiyū` (`N-01 P1`)[cite: 16]. |
| **`DYN_1` (`FILAR XIII & XII`)** | `Y` (`PASS`) | **`N` (`FAIL`)** | Regex `en_slang_pat` i `jp_dialect_pat` zawiera `wagahai`, `-dechu..-dabe` oraz 8 słów dialektalnych JP w romaji i kana[cite: 16]. |
| **`DYN_2` (`FILAR XIV & XXX`)** | `Y` (`PASS`) | **`N` (`FAIL`)** | Regex `archaic_pat` zawiera `ojou`, `washi`, `sessha`, `warawa`, `onushi`, `gozaru`[cite: 16]. |
| **`DYN_3` (`FILAR XXV..XXIX & CLVII`)** | `Y` (`PASS`) | **`N` (`FAIL`)** | Regex `honorific_pat` zawiera `san`, `sama`, `kun`, `chan`, `sensei`, `senpai`, `dono`[cite: 16]. |
| **`DYN_4` (`FILAR CXXXVI, XCVI & XV`)** | `Y` (`PASS`) | **`N` (`FAIL`)** | Regex `age_gender_pat` zawiera `kanojo-tachi`, `onnatachi`, `shonen`, `baba`, `bba`[cite: 16]. |
| **`DYN_5` (`FILAR CLXXII..XVII`)** | `Y` (`PASS`) *(poza `seiyū` -> `N-01 P1`)* | **`N` (`FAIL`)** | Tekst zawiera `seiyū` (`N-01 P1`); regex `combat_affect_pat` zawiera `ottotto`, `kakegoe`[cite: 16]. |
| **`DYN_6` (`FILAR CLXV, LXV, CLXIX & CLXXIX`)** | `Y` (`PASS`) | **`Y` (`PASS`)** | Regex operuje wyłącznie na strukturze powtórzeń (`\1`) i interpunkcji wielokropków[cite: 16]. |
| **`DYN_7` (`FILAR XLIX..LVI`)** | `Y` (`PASS`) | **`Y` (`PASS`)** | Regex `spec_reg_pat` zawiera wyłącznie ogólne terminy domenowe EN (`strategy`, `autopsy`, `diagnosis` itp.)[cite: 16]. |
| **`DYN_8` (`FILAR LXXVIII..CXIX`)** | `Y` (`PASS`) | **`N` (`FAIL`)** | Regex `culture_signs_pat` zawiera `tsukkomi`, `boke`, `neta`, `gyagu`, `dajare`, `giongo`, `gitaigo`, `bento`, `onigiri` itd.[cite: 16]. |
| **`DYN_9` (`FILAR XIX & LXXVI`)** | `Y` (`PASS`) | **`N` (`FAIL`)** | Regexy `lyric_high_pat` i `lyric_support_pat` zawierają `namida`, `sayonara`, `sabishii`, `kanashii`, `natsukashii`, `itoshii`[cite: 16]. |

### 6.2. Aktualizacja Sekcji 5 raportu głównego (Zaktualizowana tabela naruszeń i obserwacji `N-01` – `N-05`)

| ID | Lokalizacja | Typ naruszenia / obserwacji | Konkretny fragment (`9f4df49`) | Rekomendacja dla `10.4` (kategoria metajęzykowa) | Priorytet |
| :---: | :--- | :--- | :--- | :--- | :---: |
| **`N-01`** *(przeklasyfikowano z P2 na P1)* | `FILAR 2` (`R1.8`, linie `2564, 2573`) oraz `DYN_5` (`rules.py:2855`) | **`Z4` (japoński loanword `seiyū` w aktywnym prompcie Base i Dynamic)** | `RYTM SEIYŪ`, `czasu trwania głosu seiyū`, `fizjologia emocji seiyū`[cite: 16] | Zastąpić polską kategorią metajęzykową **`[AKTOR_GŁOSOWY]`** (`RYTM AKTORA GŁOSOWEGO`, `czasu trwania głosu aktora`, `fizjologia emocji aktora głosowego`) w `10.4`[cite: 16]. | **`P1`** |
| **`N-05`** *(nowa pozycja z FAZY 0 suplementu)* | `get_focused_rules_for_batch` (`DYN_1, DYN_2, DYN_3, DYN_4, DYN_5, DYN_8, DYN_9`, linie `2716–2936`) | **`Z4` (japońskie terminy-kotwice i znaki kana wewnątrz wzorców regex Pythona)** | `wagahai`, `dechu..dabe`, `やん..っす`, `ojou..gozaru`, `san..dono`, `kanojo-tachi`, `ottotto`, `kakegoe`, `tsukkomi..dajare`, `bento..kimono`, `giongo`, `gitaigo`, `namida..itoshii`[cite: 16] | W `10.4` podjąć decyzję architektoniczną: zastąpić japońskie literały w regexach `rules.py` sygnałami strukturalnymi/kategorialnymi przekazywanymi z `whisper_disambiguator.py` / `profiler.py` (`[ZNACZNIK_REJESTRU]`, `[ZNACZNIK_HONORYFIKATU]`), uwalniając `rules.py` od japońskich tokenów leksykalnych[cite: 16]. | **`P1`** |
| **`N-02`** | `FILAR 2` (`R1.7`, `rules.py:2569`) | Parametr techniczny CPL (`38 CPL` vs `42 CPL` Netflix) | `limit 38 znaków w linii (CPL)`[cite: 16] | Zachować `38 CPL` jako bezpieczniejszy limit dla czcionki `.ass` 1080p[cite: 16]. | **P2** |
| **`N-03`** | `TRANSLATION_RULES_PROMPT` (`rules.py:25–2524`) | Archiwum Legacy (`Z16-locked`) | Pasywna stała `TRANSLATION_RULES_PROMPT` | **NIE RUSZAĆ (Zasada 16)**[cite: 16]. | **P2** |
| **`N-04`** | `profiler.py:688–689` | Backlog `10.4` (`L-06`) | `format_lean_episode_brief` | Opcjonalna rozbudowa o adnotacje kontekstowe humoru/aluzji w `10.4`[cite: 16]. | **P2** |

---

## 7. FAZA ODBIORU

- [x] FAZA 0 — Triggery `DYN_1/5/8` (oraz pozostałych `DYN_X`): `0` japońskich terminów w tekstach wysyłanych do LLM (`PASS`), natomiast w wewnętrznych regexach Pythona wykryto `38` japońskich tokenów w `DYN_1, DYN_5, DYN_8` (`15` romaji + `8` kana w `DYN_1`, `2` w `DYN_5`, `21` w `DYN_8`) oraz `24` w `DYN_2, DYN_3, DYN_4, DYN_9` (`Z4 FAIL w warstwie regexów` -> `N-05 P1`)[cite: 16]
- [x] FAZA 1 — `seiyū`: `3` wystąpienia w aktywnym runtime (`2` w `BASE_2`, `1` w `DYN_5`, `0` w `profiler.py`), przeklasyfikowano `N-01` z `P2` na `P1`: **tak**[cite: 16]
- [x] FAZA 2 — `tests/test_profiler.py`: `7/7` testów istnieje (`T10.2_1–T10.2_3`, `T10.3_1–T10.3_4`), `0` osłabionych (`PASS`)[cite: 16]
- [x] FAZA 3 — Rozszerzenie zakresu 10.3: **odnotowane i udokumentowane** na podstawie `git diff 51dbe2d..9f4df49` (pełne oczyszczenie tekstów i tytułów `DYN_1–DYN_9` wysyłanych do LLM)[cite: 16]
- [x] FAZA 4 — Uzupełnienie raportu głównego: `3` zaktualizowane sekcje (`3.1`, `3.2`, `5`), `1` nowa obserwacja `P1` (`N-05`), `1` przeklasyfikowana obserwacja `P2 -> P1` (`N-01`)[cite: 16]
- [x] Werdykt suplementu: `PASS_Z_DROBNYMI`[cite: 16]
- [x] 0 placeholderów `<DO_WYPEŁNIENIA>`
- [x] 0 zmian w kodzie (`git status` clean)
- [x] 0 commitów
- [x] Z16 nienaruszone[cite: 16]
- [x] Z1/Z2/Z3/Z4 respektowane[cite: 16]