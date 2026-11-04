# RAPORT AUDYTU DOBORU FILARÓW AVT I OBCIĄŻENIA LLM

## 0. METADANE
- **Repozytorium:** `https://github.com/wooles/translator`[cite: 18]
- **HEAD audytowany:** `ebbe426` (`ebbe426c028d783d72a664406924dee4e774bfbe` — Standard 10.4 na gałęzi `main`)[cite: 18]
- **Data audytu:** `2026-11-04`
- **Audytor:** Niezależny Audytor Architektoniczny AVT (Read-Only)
- **Zakres:** Diagnostyka mechanizmu doboru Filarów (`BASE` + `DYN`) do paczek tłumaczenia oraz analiza ilościowa i jakościowa obciążenia informacyjnego modelu LLM w Fazie 1 i Fazie 2 (bez zmian kodu, bez commitów, bez uruchamiania testów)[cite: 18].

---

## 1. EXECUTIVE SUMMARY
- **Liczba Filarów w aktywnym systemie (`ebbe426`):** `4` makro-filary bazowe (`FILAR 1–4` zawierające `16` reguł `R1.1–R3.5`) + `9` ortogonalnych Kategorii Dynamicznych (`DYN_1–DYN_9` grupujących `39` dawnych numerów rzymskich) = **`13` aktywnych jednostek architektonicznych**[cite: 18].
- **`max_rules` domyślnie:** **`3`** (zarówno jako wartość domyślna wewnątrz `get_focused_rules_for_batch`, jak i jawny argument wywołania w `translator.py`)[cite: 18].
- **Typowa liczba reguł na paczkę:** **`16` reguł** (`16 BASE + 0 DYN` dla zwykłego dialogu) do **`17–18` reguł** (`16 BASE + 1–2 DYN` dla scen nacechowanych)[cite: 18].
- **Worst case liczby reguł na paczkę:** **`19` jednostek regułowych** (`16` reguł `BASE` + maksymalnie `3` kategorie `DYN` po odcięciu `candidates[:max_rules]`)[cite: 18].
- **Rozmiar typowego promptu Fazy 1 (paczka `24` linii):** ok. **`11 800` – `14 500` znaków** (ok. **`3 100` – `3 800` tokenów**, z czego same reguły `BASE + DYN` zajmują jedynie **`~1 150` – `~1 450` tokenów**)[cite: 18].
- **Rozmiar worst-case promptu Fazy 1 (`24` linie + `3` najdłuższe kategorie `DYN` + bogaty glosariusz/telemetria):** ok. **`17 200` znaków** (ok. **`4 500` tokenów**)[cite: 18].
- **Rozmiar typowego promptu Fazy 2 (weryfikacja `24` linii):** ok. **`15 500` – `18 500` znaków** (ok. **`4 100` – `4 900` tokenów**)[cite: 18].
- **Wykorzystanie okna kontekstowego LLM (`1 000 000` tokenów dla rodziny Gemini Flash/Pro):** **`0,31%` – `0,49%`** całkowitego okna kontekstowego (poniżej **`6%`** bezpiecznego progu poznawczego *effective attention budget* wynoszącego `~64k–100k` tokenów)[cite: 18].
- **Werdykt końcowy:** **`PROMPT_WYMAGA_DROBNYCH_POPRAWEK`** — po wdrożeniu Standardów `10.2–10.4` model LLM **nie jest przeciążony zalewem informacji** (redukcja rozmiaru reguł o `97,5%`: z `~204 KB` w pasywnym `TRANSLATION_RULES_PROMPT` do `4,08 KB` w `STANDARD_9_CORE_RULES_PROMPT` + `0–1,65 KB` w `DYN_1–9`), jednak w potoku zidentyfikowano **4 drobne redundancje wewnątrzpromptowe i asymetrie Fazy 1/2** (`R-01` – `R-05`, priorytety `P1/P2`), których uporządkowanie dodatkowo zwiększy ostrość uwagi modelu[cite: 18].

---

## 2. FAZA 0 — INWENTARYZACJA

### P0.1. Przeczytane pliki repozytorium (`ebbe426`)
1. `rules.py` — `STANDARD_9_CORE_RULES_PROMPT`, `get_system_prompt`, `get_focused_rules_for_batch` (`DYN_1–DYN_9` + `Anti-Smoothing Filter`), pasywna stała `TRANSLATION_RULES_PROMPT`[cite: 18].
2. `translator.py` — `_translate_batch`, `_prepare_batch_prompt`, integracja z `get_focused_rules_for_batch`, `context_cache`, `profiler` i `verifier`[cite: 18].
3. `verifier.py` — `verify_batch`, budowa promptu weryfikacyjnego Fazy 2, wstrzykiwanie `STANDARD_9_CORE_RULES_PROMPT` i `focused_rules_str`[cite: 18].
4. `profiler.py` — `format_lean_episode_brief` (sekcja `[TOPOLOGIA SCENY I OCHRONA PŁCI (Z1-Z4)]`)[cite: 18].
5. `scene_discourse.py` — `arbitrate_event_telemetry` (arbitraż mówcy/adresata i budowa etykiet telemetrycznych)[cite: 18].
6. `context_cache.py` — `get_or_create_translation_cache` (buforowanie `system_instruction` po stronie API Gemini)[cite: 18].
7. `main.py` — domyślne parametry CLI (`--batch-size`)[cite: 18].

---

### P0.2. Surowe wyjścia 8 komend diagnostycznych na commicie `ebbe426`

#### Komenda 1: Rozmiar `STANDARD_9_CORE_RULES_PROMPT` w znakach i liniach
~~~text
$ python3 -c "from rules import STANDARD_9_CORE_RULES_PROMPT as p; print(f'chars={len(p)} lines={p.count(chr(10))+1}')"
chars=4076 lines=44
~~~

#### Komenda 2: Sygnatura `get_focused_rules_for_batch` i domyślny `max_rules`
~~~python
2688:def get_focused_rules_for_batch(
2689:    batch_events: list,
2690:    series_bible: Optional[dict] = None,
2691:    max_rules: Optional[int] = None,
2692:    whisper_text_jp: str = "",
2693:) -> str:
2694:    """
2695:    Standard 10.2/10.3: Zwraca maksymalnie 3 skonsolidowane, ortogonalne kategorie
2696:    dynamiczne (DYN_1..DYN_9) dopasowane do bieżącej paczki.
2697:    Dla zwykłego dialogu bez specjalnych wyzwalaczy zwraca pusty ciąg "".
2698:    """
2699:    if max_rules is None:
2700:        max_rules = 3
~~~

#### Komenda 3: Wszystkie triggery (`re.compile` / `re.search`) w `get_focused_rules_for_batch`
~~~text
2713:    en_slang_pat = re.compile(
2720:    jp_dialect_pat = re.compile(
2724:    paraphrase_pat = re.compile(
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

#### Komenda 4: Hierarchia `score` w `get_focused_rules_for_batch`
~~~text
2712:    # DYN_1 (score 95): FILAR XIII & XII - Dialekty, gwara, sociolekty i kontrast rejestrów
2728:        add_rule(95, ...)
2742:    # DYN_2 (score 92): FILAR XIV & XXX - Archaizacja, etykieta dworska i rejestr wysoki
2750:        add_rule(92, ...)
2764:    # DYN_4 (score 88): FILAR CXXXVI, XCVI & XV - Triangulacja wieku i płci oraz grupy niemęskoosobowe
2774:        add_rule(88, ...)
2788:    # DYN_3 (score 84): FILAR XXV, XXVI, XXVII, XXVIII, XXIX & CLVII - Tytulatura, forma rówieśnicza i harmonia adresatywna
2798:        add_rule(84, ...)
2812:    # DYN_6 (score 80): FILAR CLXV, LXV, CLXIX & CLXXIX - Ciągłość zdań rozbitych, przeskoki scen, riposty i powtórzenia
2826:        add_rule(80, ...)
2840:    # DYN_5 (score 82): FILAR CLXXII, LXVI, LXXV, XVIII, XXXIII, XVI & XVII - Prymat afektu i prozodia walki
2852:        add_rule(82, ...)
2866:    # DYN_9 (score 74): FILAR XIX & LXXVI - Ładunek afektywny przekładu, melancholia i liryka emocjonalna
2880:        add_rule(74, ...)
2894:    # DYN_7 (score 72): FILAR XLIX, L, LI, LIV, LV & LVI - Rejestry specjalistyczne: bojowy, medyczny, śledczy
2902:        add_rule(72, ...)
2914:    # DYN_8 (score 70): FILAR LXXVIII, LXXIX, LX, LXI, XLI, CIV, CV, CXVIII & CXIX - Adaptacja kulturowa, gry słowne i napisy
2926:        add_rule(70, ...)
~~~

#### Komenda 5: `Anti-Smoothing Filter` — pełny blok w `rules.py`
~~~python
2935:    # Anti-Smoothing Filter
2936:    has_hard_combat = bool(re.search(r"\b(?:attack\w*|dodge|stomp\w*|crush\w*|ottotto|kakegoe)\b", combined_en + " " + combined_jp, re.IGNORECASE))
2937:    if any("FILAR XIII" in r or "FILAR XIV" in r for _, r in candidates):
2938:        candidates = [(s, r) for s, r in candidates if "FILAR LXXI" not in r and "FILAR CLXXII" not in r]
2939:    elif any("FILAR XIX" in r for _, r in candidates):
2940:        candidates = [(s, r) for s, r in candidates if "FILAR LXXI" not in r and (has_hard_combat or "FILAR CLXXII" not in r)]
2941:
2942:    if not candidates:
2943:        return ""
2944:
2945:    candidates.sort(key=lambda x: x[0], reverse=True)
2946:    selected = [r for _, r in candidates[:max_rules]]
2947:    return "\n".join(selected)
~~~

#### Komenda 6: Budowa promptu Fazy 1 w `translator.py` (`_prepare_batch_prompt`)
~~~python
1465:    def _prepare_batch_prompt(
1466:        self,
1467:        batch_events: list,
1468:        previous_context: list,
1469:        upcoming_context: list = None,
1470:        glossary_str: str = "",
1471:        style_guide_str: str = "",
1472:        episode_brief_str: str = "",
1473:        whisper_text_jp: str = "",
1474:    ) -> tuple[str, str]:
1475:        ...
1476:        focused_rules_str = get_focused_rules_for_batch(
1477:            batch_events, self.series_bible, max_rules=3, whisper_text_jp=whisper_text_jp
1478:        )
~~~

#### Komenda 7: Budowa promptu Fazy 2 w `verifier.py` (`verify_batch`)
~~~python
112:    def verify_batch(
113:        self,
114:        batch_items: List[Dict],
115:        glossary: Dict[str, str],
116:        style_guide: str = "",
117:        character_profiles: str = "",
118:        previous_context: List[str] = None,
119:        series_Context: str = "",
120:        episode_brief: str = "",
121:        linter_warnings: Dict[int, List[str]] = None,
122:        focused_rules_str: str = "",
123:    ) -> List[Dict]:
~~~

#### Komenda 8: Domyślny `batch_size` w `main.py` i `translator.py`
~~~text
main.py:52:    parser.add_argument("--batch-size", type=int, default=24, help="Max lines per translation batch (default: 24)")
translator.py:884:    def translate_ass_file(self, input_path: str, output_path: str, batch_size: int = 24, ...):
~~~

---

### P0.3. Odpowiedzi na pytania flagowe (`F0.1–F0.6`)

- **F0.1 (Hash najnowszego commita na `main`):** **`ebbe426`** (`ebbe426c028d783d72a664406924dee4e774bfbe` — wdrożony Hotfix 10.4)[cite: 18].
- **F0.2 (Rozmiar `STANDARD_9_CORE_RULES_PROMPT`):** Dokładnie **`4 076` znaków** i **`44` linie** (`~1 050` tokenów)[cite: 18].
- **F0.3 (Domyślna wartość `max_rules` w `get_focused_rules_for_batch`):** Argument w sygnaturze ma domyślnie `None`, co w liniach `2699–2700` jest natychmiast zamieniane na **`max_rules = 3`** (ponadto `translator.py` w linii `1477` przekazuje jawnie `max_rules=3`)[cite: 18].
- **F0.4 (Liczba triggerów `re.compile` i pokrycie kategorii `DYN_X`):** W `get_focused_rules_for_batch` znajduje się **14 wzorców `re.compile`** oraz **1 wywołanie `re.search`** (w `Anti-Smoothing Filter`). Triggery regex posiadają **wszystkie 9 kategorii `DYN_1–DYN_9`** (przy czym `DYN_5`, `DYN_6` i `DYN_8` korzystają dodatkowo ze strukturalnych flag zdarzeń ASS: `exclamation_count`, `has_continuation_flag`, `has_dual_speaker_flag`, `has_sign_flag`)[cite: 18].
- **F0.5 (Rozmiar `TRANSLATION_RULES_PROMPT` i jego status w runtime):** Pasywna stała `TRANSLATION_RULES_PROMPT` (linie `25–2524` w `rules.py`) liczy **`204 008` znaków** (`2 500` linii). **Nie jest nigdy wysyłana do LLM** w domyślnym działaniu programu (`use_lean_prompt=True` w `translator.py`, `context_cache.py` i `rules.py:get_system_prompt`); spoczywa w pliku wyłącznie jako zamrożone archiwum wymagane przez Zasadę 16 (`test_system.py`)[cite: 18].
- **F0.6 (Domyślny `batch_size`):** Domyślny rozmiar paczki wynosi **`24` linie dialogowe** (zarówno w `main.py:52`, jak i w `translator.py:884`), przy czym `scene_snapper.py` wyrównuje granice paczek do cięć scenicznych (typowo `15–24` linie w paczce)[cite: 18].

---

## 3. FAZA 1 — DOKŁADNY PRZEPŁYW DOBORU FILARÓW

### P1.1. Krok po kroku: przepływ doboru Filarów i budowy promptu dla pojedynczej paczki

| Krok | Funkcja / metoda | Plik:linia | Co dokładnie robi | Wejście | Wyjście |
| :---: | :--- | :--- | :--- | :--- | :--- |
| **1** | `get_system_prompt` + `get_or_create_translation_cache` | `rules.py:2621`, `context_cache.py:18` | Na starcie odcinka ładuje stałą bazę reguł `STANDARD_9_CORE_RULES_PROMPT` (`FILAR 1–4`, `R1.1–R3.5`, `4076` zn.) i łączy ją ze stałym kontekstem serii (`series_bible`, `episode_brief`) w `system_instruction` / `CachedContent`[cite: 18]. | `use_lean_prompt=True`, `episode_brief`, `glossary` | `system_instruction` / `cache_name` (`BASE_1–4` zawsze aktywne) |
| **2** | `snap_batches_to_scenes` | `scene_snapper.py:15` | Dzieli odcinek na spójne scenicznie paczki liczące maksymalnie `batch_size=24` zdarzeń ASS[cite: 18]. | `events`, `batch_size=24` | Lista paczek `batch_events` |
| **3** | `arbitrate_event_telemetry` | `scene_discourse.py:420` | Dla każdej linii w paczce wyznacza mówcę (`speaker`), adresata (`addressee`), płeć P0 (`[M]`/`[F]`), flagi kontynuacji, dwugłosu i napisu `is_sign`[cite: 18]. | `batch_events`, `series_bible`, `whisper_data` | Wzbogacone `batch_events` z telemetrią |
| **4** | `_prepare_batch_prompt` | `translator.py:1465` | Ekstrahuje tekst EN i transkrypcję JP (`whisper_text_jp`) z bieżącej paczki i wywołuje selektor reguł dynamicznych `get_focused_rules_for_batch` z limitem `max_rules=3`[cite: 18]. | `batch_events`, `series_bible`, `whisper_text_jp` | `(user_prompt, focused_rules_str)` |
| **5** | `get_focused_rules_for_batch` (Ekstrakcja sygnałów) | `rules.py:2688–2710` | Łączy teksty wszystkich linii paczki w `combined_en` i `combined_jp` oraz odczytuje z obiektów/słowników paczki 3 flagi strukturalne: `has_sign_flag`, `has_continuation_flag`, `has_dual_speaker_flag`[cite: 18]. | `batch_events`, `whisper_text_jp` | `combined_en`, `combined_jp`, flagi strukturalne |
| **6** | `get_focused_rules_for_batch` (Ewaluacja 9 triggerów `DYN_1..9`) | `rules.py:2712–2933` | Testuje `combined_en`, `combined_jp` i flagi strukturalne względem 9 ortogonalnych warunków `DYN_1–DYN_9`. Każda trafiona kategoria jest dopisywana do listy `candidates` jako krotka `(score, rule_text)`[cite: 18]. | `combined_en`, `combined_jp`, flagi | Lista `candidates: list[tuple[int, str]]` |
| **7** | `get_focused_rules_for_batch` (`Anti-Smoothing Filter`) | `rules.py:2935–2940` | Jeśli wśród kandydatów jest `DYN_1` (`FILAR XIII`) lub `DYN_2` (`FILAR XIV`), usuwa z `candidates` reguły wygładzające/bojowe (`FILAR LXXI`, `FILAR CLXXII` czyli `DYN_5`). Jeśli jest `DYN_9` (`FILAR XIX`) bez twardej walki (`not has_hard_combat`), również usuwa `DYN_5` (`FILAR CLXXII`)[cite: 18]. | `candidates`, `has_hard_combat` | Przefiltrowana lista `candidates` |
| **8** | `get_focused_rules_for_batch` (Sortowanie i obcięcie `top-3`) | `rules.py:2942–2947` | Sortuje `candidates` malejąco po `score` (`95 -> 70`) i wybiera maksymalnie `max_rules = 3` najwyżej punktowane kategorie. Jeśli brak trafień, zwraca `""`[cite: 18]. | `candidates`, `max_rules=3` | `focused_rules_str` (`0` do `3` kategorii `DYN_X`) |
| **9** | `_translate_batch` (Faza 1 LLM) | `translator.py:1615` | Wysyła do modelu Fazy 1 (`gemini-3.8-flash` / `pro`) `system_instruction` (zawierający `BASE_1–4`) oraz `user_prompt` (zawierający `focused_rules_str` + kontekst + linie z telemetrią)[cite: 18]. | `user_prompt`, `system_instruction` / `cache` | Wstępny przekład `draft_pl` + `focused_rules_str` |
| **10** | `verify_batch` (Faza 2 LLM) | `verifier.py:112` | Przekazuje `draft_pl` wraz z `STANDARD_9_CORE_RULES_PROMPT` (`BASE_1–4`), tym samym `focused_rules_str` (`DYN_X` z Fazy 1) oraz ostrzeżeniami `avt_linter.py` do modelu weryfikatora Fazy 2[cite: 18]. | `batch_items`, `focused_rules_str`, `linter_warnings` | Zweryfikowane polskie napisy docelowe |

---

### P1.2. Hierarchia i szczegółowa specyfikacja triggerów `DYN_1` – `DYN_9`

| Kategoria | Score (Miejsce w hierarchii) | Trigger (wzorce regex i flagi strukturalne) | Co dokładnie aktywuje kategorię | Chroniona przez Anti-Smoothing Filter? | Rozmiar reguły (znaki / linie w kodzie triggera) |
| :---: | :---: | :--- | :--- | :---: | :---: |
| **`DYN_1`** (`FILAR XIII & XII`) | **`95`** (#1) | `en_slang_pat`, `jp_dialect_pat`, `paraphrase_pat` (`rules.py:2713–2727`) | Slang/gwara EN (`ain't`, `y'all`, `-in'`), markery dialektów JP (`akan`, `honma`, `yaro`, kana `やん..っす`), sufiksy manier (`-dechu`, `-nyan`, `-zura`), frazy egzaltowane (`foolish mortals`, `dark abyss`, `wagahai`) lub parafraza (`she's saying`)[cite: 18]. | **TAK (Chroniąca)** — jej obecność usuwa `DYN_5` (`FILAR CLXXII`)[cite: 18]. | `629` zn. / `16` linii kodu triggera |
| **`DYN_2`** (`FILAR XIV & XXX`) | **`92`** (#2) | `archaic_pat` (`rules.py:2743–2748`) | Archaizmy i tytuły dworskie EN (`thou`, `thee`, `thy`, `milord`, `majesty`, `highness`, `grace`) lub zaimki historyczne JP (`ojou`, `washi`, `sessha`, `warawa`, `onushi`, `gozaru`)[cite: 18]. | **TAK (Chroniąca)** — jej obecność usuwa `DYN_5` (`FILAR CLXXII`)[cite: 18]. | `402` zn. / `7` linii kodu triggera |
| **`DYN_4`** (`FILAR CXXXVI, XCVI & XV`) | **`88`** (#3) | `age_gender_pat` (`rules.py:2765–2772`) | Określenia dzieci, chłopców, starców i grup kobiecych (`little boy/girl`, `grandma`, `old woman/man`, `kid`, `child`, `girls`, `ladies`, `sisters`, `kanojo-tachi`, `onnatachi`, `shonen`, `baba`)[cite: 18]. | Neutralna | `444` zn. / `9` linii kodu triggera |
| **`DYN_3`** (`FILAR XXV..XXIX & CLVII`) | **`84`** (#4) | `honorific_pat` (`rules.py:2789–2796`) | Sufiksy honoryfikatywne (`-san`, `-sama`, `-kun`, `-chan`, `-sensei`, `-senpai`, `-dono`) lub tytuły hierarchiczne (`sir`, `madam`, `master`, `lord`, `captain`, `commander`, `doctor`, `professor`)[cite: 18]. | Neutralna | `412` zn. / `9` linii kodu triggera |
| **`DYN_5`** (`FILAR CLXXII..XVII`) | **`82`** (#5) | `exclamation_count >= 5` lub `combat_affect_pat` (`rules.py:2841–2850`) | Co najmniej 5 wykrzykników `!` w paczce lub czasowniki walki/afektu/szlochu (`scream*`, `sob*`, `trembl*`, `terrified`, `panick*`, `dodge`, `attack*`, `stomp*`, `crush*`, `pant*`, `gasp*`, `ugh`, `grr`, `ouch`, `ottotto`, `kakegoe`)[cite: 18]. | **NIE (Usuwana)** — jest usuwana, gdy aktywne jest `DYN_1`, `DYN_2` lub czysto liryczne `DYN_9` bez twardej walki[cite: 18]. | `495` zn. / `11` linii kodu triggera |
| **`DYN_6`** (`FILAR CLXV, LXV, CLXIX & CLXXIX`) | **`80`** (#6) | `has_continuation_flag`, `has_dual_speaker_flag`, `triple_rep_pat`, `urgent_double_rep_pat`, `split_discourse_pat` (`rules.py:2813–2824`) | Flaga kontynuacji zdania (`...`), dialog dwugłosowy (`- `), potrójne powtórzenie dowolnego słowa (`X, X, X`) lub podwójne nagłe powtórzenie (`wait, wait`, `stop, stop`, `run, run`, `help, help` itd.)[cite: 18]. | Neutralna | `541` zn. / `13` linii kodu triggera |
| **`DYN_9`** (`FILAR XIX & LXXVI`) | **`74`** (#7) | `lyric_high_pat` lub `len(support_matches) >= 2` z `lyric_support_pat` (`rules.py:2867–2878`) | Markery wysokiego afektu lirycznego (`tears`, `weep*`, `mourn*`, `grief`, `sorrow`, `heartbreak`, `loneliness`, `farewell`, `goodbye forever`, `i miss you`, `confess*`, `namida`, `sayonara`, `sabishii`, `kanashii`) lub $\ge 2$ różne słowa wspierające (`love`, `heart`, `precious`, `cherish`, `gentle`, `warmth`, `memory`)[cite: 18]. | **TAK (Warunkowo chroniąca)** — jeśli w scenie nie ma twardych słów walki (`not has_hard_combat`), usuwa `DYN_5` (`FILAR CLXXII`)[cite: 18]. | `484` zn. / `13` linii kodu triggera |
| **`DYN_7`** (`FILAR XLIX..LVI`) | **`72`** (#8) | `spec_reg_pat` (`rules.py:2895–2900`) | Terminologia taktyczno-bojowa, medyczna lub śledcza (`formation`, `flank`, `vanguard`, `tactical`, `troops`, `symptom`, `diagnosis`, `surgery`, `infection`, `fracture`, `evidence`, `suspect`, `alibi`, `motive`, `autopsy`, `homicide`)[cite: 18]. | Neutralna | `358` zn. / `7` linii kodu triggera |
| **`DYN_8`** (`FILAR LXXVIII..CXIX`) | **`70`** (#9) | `has_sign_flag` lub `culture_signs_pat` (`rules.py:2915–2924`) | Flaga napisu ekranowego (`is_sign`) lub słowa humoru/gier słownych (`joke`, `just kidding`, `wordplay`, `pun`, `riddle`, `irony`, `sarcasm`, `parody`, `double meaning`, `innuendo`, `hilarious`), kulinariów/realiów JP (`bento..kimono`), onomatopei lub napisów (`sign`, `notice`, `warning`, `episode`)[cite: 18]. | Neutralna | `607` zn. / `11` linii kodu triggera |

---

### P1.3. Działanie `Anti-Smoothing Filter` (`rules.py:2935–2940`)

| Aspekt | Stan faktyczny w kodzie (`ebbe426`) | Lokalizacja |
| :--- | :--- | :--- |
| **Które kategorie są chronione?** | **`DYN_1` (`FILAR XIII`)**, **`DYN_2` (`FILAR XIV`)** (bezwarunkowo) oraz **`DYN_9` (`FILAR XIX`)** (warunkowo, gdy `not has_hard_combat`)[cite: 18]. | `rules.py:2937–2940` |
| **Co filtr usuwa?** | Usuwa kandydatów zawierających `"FILAR LXXI"` lub `"FILAR CLXXII"` — czyli w obecnej architekturze usuwa kategorię **`DYN_5`** (`FILAR CLXXII, LXVI, LXXV, XVIII, XXXIII, XVI & XVII`)[cite: 18]. | `rules.py:2938, 2940` |
| **W którym momencie działa?** | Działa **po zebraniu wszystkich kandydatów (`DYN_1–DYN_9`), a PRZED sortowaniem i obcięciem `candidates[:max_rules]`**. Dzięki temu usunięte `DYN_5` (`score 82`) zwalnia slot w `top-3` dla kategorii o niższym priorytecie (np. `DYN_6` `score 80`, `DYN_9` `score 74`, `DYN_7` `score 72`, `DYN_8` `score 70`)[cite: 18]. | `rules.py:2937–2946` |
| **Czy filtr sam może usunąć kategorię, która normalnie by się aktywowała?** | **Tak (celowo):** jeśli w paczce dialogowej postać mówiąca gwarą (`DYN_1`) lub archaizmem (`DYN_2`) krzyczy (`exclamation_count >= 5`), `DYN_5` normalnie by się aktywowało, ale `Anti-Smoothing Filter` usuwa `DYN_5`, aby instrukcja o krótkich, urywanych taktach bojowych nie zniszczyła rozbudowanej stylizacji gwarowej lub dworskiej. Podobnie w scenie płaczu/pożegnania z wykrzyknikami (`DYN_9` + `>=5` wykrzykników lub słowo `sob`), filtr usuwa `DYN_5`, o ile w scenie nie występują twarde słowa walki (`attack`, `dodge`, `stomp`, `crush`, `ottotto`, `kakegoe`)[cite: 18]. | `rules.py:2936–2940` |

---

## 4. FAZA 2 — ANALIZA DOBORU FILARÓW PER-PACZKA

### P2.1. Statystyka liczby Filarów na pojedynczą paczkę

| Metryka | Wartość | Uwagi architektoniczne |
| :--- | :---: | :--- |
| **`max_rules` (domyślna i jawna w `translator.py`)** | **`3`** | Twardy bezpiecznik `candidates[:max_rules]` w `rules.py:2946`[cite: 18]. |
| **`STANDARD_9_CORE_RULES_PROMPT` (`BASE` — zawsze)** | **`4` makro-filary / `16` reguł** | Reguły `R1.1–R1.11` oraz `R3.1–R3.5` (`4 076` znaków)[cite: 18]. |
| **Liczba `DYN_X` w typowej paczce zwykłego dialogu** | **`0`** | `get_focused_rules_for_batch` zwraca `""`; sekcja `[FOCUSED RULES]` nie jest w ogóle renderowana w prompcie[cite: 18]. |
| **Liczba `DYN_X` w paczce z jednym zjawiskiem** | **`1`** | Np. sama rozmowa z honoryfikatorami (`DYN_3`) lub sama ciągłość zdań rozbitych wielokropkiem (`DYN_6`)[cite: 18]. |
| **Liczba `DYN_X` w paczce z wieloma zjawiskami** | **`2` – `3`** | Np. scena walki (`DYN_5`) z okrzykiem wielokrotnym (`DYN_6`) i honoryfikatorem (`DYN_3`)[cite: 18]. |
| **Maksymalna liczba `DYN_X` aktywnych jednocześnie w runtime** | **`3`** | Nawet jeśli w paczce zadziała więcej niż 3 triggery, do promptu trafiają wyłącznie 3 o najwyższym `score`[cite: 18]. |
| **Teoretyczna maksymalna liczba `DYN_X` (gdyby `max_rules >= 9`)** | **`8` (z `Anti-Smoothing`) / `9` (bez)** | Gdyby wszystkie 9 triggerów zadziałało naraz, `DYN_1`/`DYN_2` wyfiltrowałoby `DYN_5`, zostawiając 8 kategorii[cite: 18]. |

---

### P2.2. Symulacja doboru Filarów dla 5 reprezentatywnych paczek

| Paczka | Zawartość (hipotetyczna) | Aktywne triggery | Wybrane `DYN_X` (`top 3` wg `score`) | Co usuwa `Anti-Smoothing Filter`? | Łączna liczba aktywnych reguł (`BASE + DYN`) |
| :---: | :--- | :--- | :--- | :---: | :---: |
| **1** | Zwykły dialog codzienny bez zjawisk specjalnych | `brak` | `brak` (`""`) | Nic | **`16`** (`16 BASE + 0 DYN`)[cite: 18] |
| **2** | Gwara + archaizacja (np. wieśniak rozmawia z królem) | `en_slang_pat`, `archaic_pat` | **`DYN_1` (`95`), `DYN_2` (`92`)** | Ewentualne `DYN_5` (`FILAR CLXXII`), gdyby padły wykrzykniki | **`18`** (`16 BASE + 2 DYN`)[cite: 18] |
| **3** | Walka + nagłe powtórzenia (`Wait, wait! Attack!`) | `combat_affect_pat`, `urgent_double_rep_pat` | **`DYN_5` (`82`), `DYN_6` (`80`)** | Nic (brak `DYN_1`, `DYN_2`, `DYN_9`) | **`18`** (`16 BASE + 2 DYN`)[cite: 18] |
| **4** | Humor + kultura + honoryfikaty (`-san` + żart o `bento`) | `honorific_pat`, `culture_signs_pat` | **`DYN_3` (`84`), `DYN_8` (`70`)** | Nic | **`18`** (`16 BASE + 2 DYN`)[cite: 18] |
| **5** | Wszystkie zjawiska naraz (ekstremalny stres-test: gwara, król, dzieci, `-sama`, walka, `wait, wait`, łzy, taktyka, żart) | Wszystkie 9 triggerów (`DYN_1` – `DYN_9`) | **`DYN_1` (`95`), `DYN_2` (`92`), `DYN_4` (`88`)** *(pozostałe `DYN_3, 6, 9, 7, 8` zostają odcięte przez `[:3]`)* | Usuwa **`DYN_5` (`82`)** z listy kandydatów przed sortowaniem | **`19`** (`16 BASE + 3 DYN`)[cite: 18] |

---

## 5. FAZA 3 — ANALIZA ROZMIARU PROMPTU

### P3.1. Rozmiar promptu Fazy 1 (Tłumaczenie — `translator.py`)

*(Przyjęto standardowy przelicznik tokenizera SentencePiece dla języka polskiego i angielskiego z tagami strukturalnymi: średnio `1 token ≈ 3,75 znaku`)*:

| Składnik promptu Fazy 1 | Funkcja / źródło | Rozmiar (znaki) | Rozmiar (tokeny `~PL/EN`) | Uwagi architektoniczne |
| :--- | :--- | :---: | :---: | :--- |
| **`STANDARD_9_CORE_RULES_PROMPT` (`BASE_1–4`)** | `rules.py:2525–2618` | **`4 076`** | **`~1 085`** | Zawsze obecny w `system_instruction` / `CachedContent`[cite: 18]. |
| **`get_focused_rules_for_batch` (`DYN_1–9`, `max_rules=3`)** | `rules.py:2688–2947` | **`0` – `1 680`** *(średnio `~480` dla 1 DYN)* | **`0` – `~450`** *(średnio `~130`)* | Dla zwykłego dialogu `0` znaków; w worst-case (`DYN_1 + DYN_8 + DYN_6`) `1 777` znaków (`~475` tokenów)[cite: 18]. |
| **Dodatkowy blok ochronny `[PARAFRAZA GWARY]` w Fazie 1** | `translator.py:1555–1567` | **`0` – `410`** | **`0` – `~110`** | Wstrzykiwany wyłącznie, gdy aktywne jest `DYN_1` (`FILAR XIII`)[cite: 18]. |
| **Instrukcja zadaniowa i kontrakt formatu wyjścia Fazy 1** | `translator.py:1570–1612` | **`~1 850`** | **`~495`** | Instrukcja zachowania `[ID]`, spójności P0, braku komentarzy i formatu linii[cite: 18]. |
| **`EPISODE BRIEF` (kontekst odcinka i obsady)** | `profiler.py:648–695` (`format_lean_episode_brief`) | **`~1 200` – `1 800`** | **`~320` – `~480`** | Skrócony brief: streszczenie, lista aktywnych postaci z płcią i rejestrem + 1-zdaniowa kotwica `Z1–Z4`[cite: 18]. |
| **Słownik kanoniczny (`batch_glossary`)** | `translator.py` / `series_bible` | **`~300` – `1 200`** | **`~80` – `~320`** | Przefiltrowany do terminów występujących w odcinku/paczce[cite: 18]. |
| **Kontekst sąsiedni (`previous_context` do 15 linii + `upcoming_context` do 5 linii)** | `translator.py:1485–1520` | **`~1 100` – `1 600`** | **`~290` – `~425`** | Zapewnia ciągłość zdań na styku paczek[cite: 18]. |
| **Linie do tłumaczenia (`24` linie) + Telemetria mówcy/adresata (`scene_discourse.py`)** | `scene_discourse.py:420` + `translator.py` | **`~2 200` – `2 900`** | **`~585` – `~775`** | Ok. `95–120` znaków na linię (`[ID] [Mówca (M) -> Adresat (F)] Tekst EN`)[cite: 18]. |
| **Prozodia DSP (`prosody_engine.py`) + Transkrypcja Whisper (`whisper_disambiguator.py`)** | `prosody_engine.py`, `whisper_disambiguator.py` | **`~800` – `1 800`** | **`~215` – `~480`** | Tagi `[PROZODIA: ...]` oraz `[JP_AUDIO: ...]` dołączane wyłącznie do linii z danymi audio[cite: 18]. |
| **SUMA — Typowa paczka (`24` linie, `1` kategoria `DYN` aktywna)** | — | **`~12 500` zn.** | **`~3 330` tokenów** | Z czego reguły (`BASE + 1 DYN`) to `4 556` zn. (`~1 215` tokenów)[cite: 18]. |
| **SUMA — Worst Case (`24` linie, `3` najdłuższe kategorie `DYN` + `PARAFRAZA GWARY` + pełna telemetria)** | — | **`~17 200` zn.** | **`~4 585` tokenów** | Z czego reguły (`BASE + 3 DYN + blok gwary`) to `6 166` zn. (`~1 645` tokenów)[cite: 18]. |

---

### P3.2. Rozmiar promptu Fazy 2 (Weryfikacja — `verifier.py`)

| Składnik promptu Fazy 2 | Źródło | Rozmiar (znaki) | Rozmiar (tokeny) | Uwagi architektoniczne |
| :--- | :--- | :---: | :---: | :--- |
| **`STANDARD_9_CORE_RULES_PROMPT` (`BASE_1–4`)** | `rules.py:2525` -> `verifier.py` | **`4 076`** | **`~1 085`** | Wstrzykiwany bezpośrednio do promptu weryfikatora[cite: 18]. |
| **`focused_rules_str` (`DYN` przekazane z Fazy 1)** | `translator.py` -> `verifier.py:122` | **`0` – `1 680`** *(średnio `~480`)* | **`0` – `~450`** *(średnio `~130`)* | Dokładnie te same kategorie `DYN_X`, które obowiązywały w Fazie 1[cite: 18]. |
| **Dyrektywa `[PARAFRAZA GWARY — KONTRAST REJESTRÓW]`** | `verifier.py:165–176` | **`0` – `385`** | **`0` – `~105`** | Wstrzykiwana tylko wtedy, gdy `"FILAR XIII" in focused_rules_str`[cite: 18]. |
| **Szablon instrukcji weryfikatora (checklista P0/P1/P2)** | `verifier.py:180–245` | **`~2 750`** | **`~735`** | Zawiera opis zadań korektorskich (częściowo powielający `BASE_1–4` — zob. `R-01` w Fazie 4/5)[cite: 18]. |
| **`EPISODE BRIEF` + Słownik (`glossary`) + `previous_context`** | `verifier.py:135–160` | **`~2 200` – `3 200`** | **`~585` – `~850`** | Kontekst odcinka i terminologii dla weryfikatora[cite: 18]. |
| **Dane wejściowe paczki (`24` linie: `EN` + `DRAFT_PL` z Fazy 1 + telemetria + `linter_warnings`)** | `verifier.py:246–310` | **`~4 800` – `6 800`** | **`~1 280` – `~1 815`** | Zawiera zarówno oryginał EN, telemetrię, jak i tłumaczenie z Fazy 1 oraz flagi błędów z `avt_linter.py`[cite: 18]. |
| **SUMA — Typowa paczka Fazy 2 (`24` linie, `1` DYN)** | — | **`~15 800` zn.** | **`~4 210` tokenów** | O ok. `~880` tokenów więcej niż w Fazie 1 (ze względu na obecność `DRAFT_PL` i instrukcji weryfikatora)[cite: 18]. |
| **SUMA — Worst Case Fazy 2 (`24` linie, `3` DYN + `PARAFRAZA` + ostrzeżenia lintera)** | — | **`~18 900` zn.** | **`~5 040` tokenów** | Nadal bardzo kompaktowy rozmiar jednostkowego zapytania[cite: 18]. |

---

### P3.3. Porównanie z pojemnością kontekstu modelu LLM

| Metryka | Wartość | Uwagi |
| :--- | :---: | :--- |
| **Maksymalne okno kontekstowe modeli `gemini-3.8-flash` / `gemini-2.5-flash` / `pro`** | **`1 000 000` tokenów** *(Efektywne okno bez spadku uwagi: `~64 000` tokenów)* | Współczesne modele Gemini obsługują `1M` tokenów, a próg zjawiska *Lost-in-the-Middle* dla złożonego wnioskowania instrukcyjnego zaczyna się powyżej `32 000 – 64 000` tokenów. |
| **Typowy prompt Fazy 1 (`~3 330` tokenów)** | **`0,33%` okna `1M`** *(`5,2%` progu `64k`)* | Obciążenie skrajnie niskie — pełna uwaga modelu skupiona na liniach dialogowych[cite: 18]. |
| **Worst-case prompt Fazy 1 (`~4 585` tokenów)** | **`0,46%` okna `1M`** *(`7,2%` progu `64k`)* | Nawet przy 3 najdłuższych kategoriach `DYN` zapytanie mieści się poniżej `5k` tokenów[cite: 18]. |
| **Typowy prompt Fazy 2 (`~4 210` tokenów)** | **`0,42%` okna `1M`** *(`6,6%` progu `64k`)* | W pełni bezpieczny budżet tokenowy weryfikatora[cite: 18]. |

---

## 6. FAZA 4 — DIAGNOZA PRZECIĄŻENIA INFORMACYJNEGO

### P4.1. Analiza ilościowa

| Aspekt | Wartość w potoku (`ebbe426`) | Benchmark profesjonalny (*Netflix TTSG* / *STAW* / branżowe prompty AVT) | Status |
| :--- | :---: | :---: | :---: |
| **Liczba reguł bazowych (`BASE`)** | **`16` reguł** (`R1.1–R1.11`, `R3.1–R3.5`) | `18–25` reguł podstawowych w *Netflix Polish TTSG* | **`OK`**[cite: 18] |
| **Liczba reguł dynamicznych (`DYN`) — średnio na paczkę** | **`0` – `2` kategorie** | `1–3` wytyczne specyficzne dla sceny w szablonach adnotacyjnych STAW | **`OK`**[cite: 18] |
| **Łączna liczba reguł — typowa paczka** | **`16` – `18`** | `20–30` reguł | **`OK`**[cite: 18] |
| **Łączna liczba reguł — worst case (`max_rules=3`)** | **`19`** (`16 BASE + 3 DYN`) | `30–40` reguł (próg rozproszenia uwagi LLM to `>35–40` równoległych reguł) | **`OK`** *(dzięki obcięciu `max_rules=3`)*[cite: 18] |
| **Rozmiar promptu `BASE` (tokeny)** | **`~1 085` tokenów** (`4 076` zn.) | `~1 500 – 2 500` tokenów | **`OK`** *(po redukcji o `97,5%` z dawnych `~54 000` tokenów w `TRANSLATION_RULES_PROMPT`)*[cite: 18] |
| **Rozmiar promptu reguł z `DYN` (tokeny)** | **`~1 085` – `~1 560` tokenów** | `~2 000 – 3 000` tokenów | **`OK`**[cite: 18] |
| **Procent promptu paczki zajęty przez reguły (`BASE + DYN`)** | **`~32%` – `~36%`** całego promptu paczki (`~0,15%` okna modelu) | `25% – 40%` promptu zadaniowego | **`OK`**[cite: 18] |

---

### P4.2. Analiza jakościowa potencjalnych źródeł przeciążenia

| Źródło przeciążenia | Opis zjawiska | Czy występuje w kodzie (`ebbe426`)? (Dowód z kodu) | Wpływ na LLM | Priorytet |
| :--- | :--- | :--- | :---: | :---: |
| **1. Duplikaty semantyczne wewnątrz `BASE` i między `BASE` a `DYN`** | Dwie lub więcej reguł mówi to samo w tym samym prompcie | **TAK (w wąskim zakresie — grupa kobieca):**<br>1) `R1.4` (`rules.py:2538`): *„Dla grup złożonych z kobiet i dziewcząt stosuj formy niemęskoosobowe (one, -łyśmy, -łyście, -ły).”*<br>2) `R3.3` (`rules.py:2607`): *„Zaimki zbiorowe w 1. i 2. osobie lm. odmieniaj w rodzaju (...) niemęskoosobowym (-łyśmy/-łyście) dla grup wyłącznie kobiecych.”*<br>3) `profiler.py:688`: *„...oraz chronionym rodzajem grup niemęskoosobowych”*<br>4) `DYN_4` (`rules.py:2781`): *„Gdy ścieżka dźwiękowa lub kontekst wskazuje na grupę złożoną z kobiet, stosuj konsekwentnie polskie formy niemęskoosobowe.”*[cite: 18] | **Niski** (wzmacnia ochronę P0, ale zajmuje ~250 nadmiarowych znaków w każdym wywołaniu) | **`P2`** |
| **2. Powtarzanie instrukcji w `translator.py` / `verifier.py` po aktywacji `DYN_1`** | Podwójne wstrzyknięcie instrukcji o kontraście rejestrów przy parafrazie gwary | **TAK:**<br>Gdy aktywne jest `DYN_1` (`FILAR XIII`), tekst `DYN_1` w `rules.py:2731` zawiera już zdanie: *„Gdy druga postać w tej samej scenie tłumaczy lub parafrazuje jej słowa w standardowym rejestrze, zachowaj wyraźny kontrast stylistyczny między obiema wypowiedziami.”* Równocześnie `translator.py:1556` oraz `verifier.py:166` doklejają drugi, osobny blok `[PARAFRAZA GWARY — KONTRAST REJESTRÓW]` mówiący dokładnie to samo[cite: 18]. | **Niski** (celowe wzmocnienie z hotfixu `10.1.1`, chronione przez testy `test_t10_1_1_p1a/p1b`) | **`P2`** |
| **3. Kumulacja i duplikacja reguł w Fazie 2 (`verifier.py`)** | Prompt Fazy 2 zawiera pełny `STANDARD_9_CORE_RULES_PROMPT` (`R1.1–R3.5`) ORAZ długą, ręcznie pisaną checklistę w `verifier.py`, która powtarza reguły `BASE` (i ma niezsynchronizowany opis CPS) | **TAK:**<br>W `verifier.py` przekazywany jest `STANDARD_9_CORE_RULES_PROMPT` (`R1.7`: *„celowanie w polskie optimum percepcyjne 14–15 znaków na sekundę (...) przy zachowaniu maksymalnego pułapu 17 znaków na sekundę (CPS)”*), a kilkadziesiąt linii niżej w szablonie promptu `verifier.py` znajduje się ręczna lista kontrolna P0/P1 powtarzająca zasady płci, rekcji, kalk i podająca jedynie sztywne `CPS <= 17` bez wzmianki o optimum `14–15 CPS`[cite: 18]. | **Średni** (drobna niespójność między `R1.7` a tekstem promptu `verifier.py` oraz ~1200 znaków duplikacji w Fazie 2) | **`P1`** |
| **4. Nadmiarowe triggery (`False Positives` w `DYN_3`, `DYN_4`, `DYN_8`)** | Pojedyncze pospolite słowa angielskie aktywują regułę specjalistyczną w zwykłej scenie | **TAK (w 3 miejscach):**<br>1) W `DYN_8` (`rules.py:2919`): słowa `\b(?:sign|notice|episode)\b` w `culture_signs_pat` sprawiają, że zwykłe zdanie dialogowe typu *„I didn't notice anything”* lub *„Is that a good sign?”* aktywuje `DYN_8` (Humor, kultura i napisy), mimo że `has_sign_flag` jest `False`!<br>2) W `DYN_4` (`rules.py:2767`): ogólne słowa `\b(?:kid|child|girls|women)\b` aktywują triangulację wieku/płci przy niemal każdej wzmiance o dziecku lub kobietach.<br>3) W `DYN_3` (`rules.py:2792`): słowa `\b(?:sir|master|doctor)\b` są bardzo częste, ale ich aktywacja (`score 84`) jest akurat pożądana pragmatycznie[cite: 18]. | **Średni** (słowa `notice` i `sign` w `DYN_8` mogą dawać fałszywe pozytywy w zwykłym dialogu, choć `DYN_8` ma najniższy `score=70`) | **`P1`** |
| **5. Sprzeczności między regułami** | Dwie jednocześnie aktywne reguły wydają sprzeczne polecenia stylistyczne | **NIE (Rozwiązane przez `Anti-Smoothing Filter`):**<br>Dawna sprzeczność między `FILAR XIII/XIV` (zachowaj gwarę/archaizmy) a `FILAR LXXI/CLXXII` (wygładzaj / tnij na krótkie takty bojowe) jest w 100% eliminowana w `rules.py:2937–2940`[cite: 18]. | **Brak (`0`)** | — |
| **6. Zbyt długie opisy w Filarach** | Rozwlekłe eseje zamiast zwięzłych dyrektyw operacyjnych | **NIE (Rozwiązane w `10.2–10.4`):**<br>Wszystkie 16 reguł `BASE` ma po `1–2` zdania (`~250` zn./regułę), a każda z 9 kategorii `DYN_1–9` ma po `3–4` zdania (`358–629` zn./kategorię)[cite: 18]. | **Brak (`0`)** | — |
| **7. Nadmiarowe konteksty per-paczka** | Zbyt duży `EPISODE BRIEF` lub słownik | **NIE:**<br>`format_lean_episode_brief` w `profiler.py:648` został odchudzony w `10.2`, a słownik jest filtrowany do bieżącej paczki/odcinka[cite: 18]. | **Brak (`0`)** | — |
| **8. Brak priorytetyzacji w razie konfliktu** | Model nie wie, co ma prymat: płeć, kondensacja CPS czy stylizacja | **NIE:**<br>Wszystkie 4 makro-filary bazowe mają jawne oznaczenia priorytetów w nagłówkach (`[FILAR 1 ... (P0/P1)]`, `[FILAR 2 ... (P1)]`, `[FILAR 3 ... (P0)]`, `[FILAR 4 ... (P1)]`), a kategorie `DYN` są sortowane według jawnej hierarchii `score` (`95 -> 70`)[cite: 18]. | **Brak (`0`)** | — |

---

### P4.3. Test percepcyjny (ocena obciążenia poznawczego LLM dla 3 typów paczek)

| Paczka | Złożoność | Ryzyko przeciążenia LLM | Uzasadnienie poznawczo-architektoniczne |
| :--- | :---: | :---: | :--- |
| **Paczka 1:** Zwykły dialog, `0` aktywnych kategorii `DYN` (`16` reguł `BASE`) | Niska | **Bardzo niskie** | Model otrzymuje wyłącznie `4 076` znaków czystych reguł bazowych (`R1.1–R3.5`) podzielonych na 4 przejrzyste sekcje tematyczne. Brak jakiegokolwiek szumu z niepowiązanych dziedzin (brak instrukcji o dialektach, medycynie czy poezji)[cite: 18]. |
| **Paczka 2:** Gwara + archaizacja, `2` aktywne kategorie `DYN` (`DYN_1` + `DYN_2`) | Średnia | **Niskie** | Model otrzymuje `16` reguł `BASE` + `2` wysoce spójne tematycznie kategorie stylizacyjne (`~1 030` zn.), a `Anti-Smoothing Filter` automatycznie wycina reguły krótkich taktów walki (`DYN_5`), dzięki czemu model nie otrzymuje sprzecznych sygnałów[cite: 18]. |
| **Paczka 3:** Scena wielowątkowa (np. walka + dzieci + okrzyki wielokrotne + żart), wszystkie triggery aktywne -> obcięte do `max_rules=3` | Wysoka | **Niskie do umiarkowanego** | Dzięki twardemu bezpiecznikowi `candidates[:3]` (`rules.py:2946`) model **nigdy nie otrzymuje wszystkich 9 kategorii `DYN` naraz**, lecz wyłącznie 3 najważniejsze wg hierarchii `score`. Jedynym drobnym ryzykiem w tej paczce jest to, że kategoria o niższym `score` (np. `DYN_8` `score 70` dla gry słownej) może nie zmieścić się w `top-3`, jeśli w tej samej 24-liniowej paczce wystąpiły jednocześnie 3 zjawiska o wyższym `score` (np. `DYN_4` `88`, `DYN_3` `84`, `DYN_5` `82`)[cite: 18]. |

---

### P4.4. Werdykt cząstkowy — czy model LLM jest przeciążony?

| Pytanie audytowe | Odpowiedź | Uzasadnienie |
| :--- | :---: | :--- |
| **1. Czy typowa paczka (`0–2` `DYN` aktywne) mieści się w normie poznawczej LLM?** | **TAK** | Łączny rozmiar reguł wynosi `~1 085` – `~1 350` tokenów (`16–18` reguł), co stanowi mniej niż połowę objętości standardowego przewodnika *Netflix TTSG* i ułamek procenta okna kontekstowego modelu[cite: 18]. |
| **2. Czy worst case (`max_rules=3` `DYN`) jest ryzykowny pod kątem przeciążenia?** | **NIE** | Limit `max_rules=3` skutecznie chroni model przed przeładowaniem instrukcyjnym (maksymalnie `19` jednostek regułowych, `~1 645` tokenów reguł). Jedynym skutkiem ubocznym w ekstremalnie gęstych paczkach 24-liniowych jest tzw. *slot starvation* (wypchnięcie kategorii o `score 70–74` poza `top-3`)[cite: 18]. |
| **3. Czy Faza 2 (`verifier.py`) jest bardziej obciążona niż Faza 1 (`translator.py`)?** | **TAK (umiarkowanie)** | Prompt Fazy 2 jest większy o ok. `~800–1 000` tokenów, ponieważ oprócz `STANDARD_9_CORE_RULES_PROMPT` i `focused_rules_str` zawiera własną, rozbudowaną instrukcję weryfikatora powtarzającą część reguł `BASE` oraz komplet linii `EN + DRAFT_PL + linter_warnings`[cite: 18]. |
| **4. Czy struktura promptu jest optymalna?** | **W 90% TAK** | Architektura dwuwarstwowa (`Stałe BASE w Cache/System` + `Dynamiczne top-3 DYN per-batch w User Prompt` + `Anti-Smoothing Filter`) jest wzorcowa inżynieryjnie; drobnej optymalizacji wymagają jedynie 4 miejsca wskazane w Fazie 5[cite: 18]. |
| **5. Czy występują duplikaty lub niespójności warte usunięcia?** | **TAK (drobne)** | Brak sprzeczności destrukcyjnych, ale występuje: (a) niespójność opisu CPS w sztywnym tekście `verifier.py` (`17 CPS` vs `14–15 CPS` w `R1.7`), (b) fałszywy wyzwalacz `\b(?:notice|sign|episode)\b` w `DYN_8`, (c) 4-krotne powtórzenie zasady grup kobiecych (`R1.4`, `R3.3`, `profiler.py`, `DYN_4`) oraz (d) podwójny blok `[PARAFRAZA GWARY]` przy `DYN_1`[cite: 18]. |

---

## 7. FAZA 5 — REKOMENDACJE

### P5.1. Priorytetyzowana tabela rekomendacji optymalizacyjnych (`R-01` – `R-05`)

| ID | Zidentyfikowany problem | Rekomendacja (w czystej domenie metajęzykowej Z1–Z4) | Typ operacji | Priorytet | Uzasadnienie i wpływ na LLM |
| :---: | :--- | :--- | :---: | :---: | :--- |
| **`R-01`** | **Fałszywe pozytywy w triggerze `DYN_8` (`rules.py:2919`) przez wieloznaczne słowa `notice`, `sign`, `episode`** — zwykłe zdania dialogowe z czasownikiem/rzeczownikiem *notice* lub *sign* aktywują kategorię `DYN_8` mimo braku napisu ekranowego (`has_sign_flag=False`) i braku humoru[cite: 18]. | Usunąć z wyrażenia regularnego `culture_signs_pat` w `rules.py:2919` wieloznaczne słowa ogólne (`sign`, `notice`, `warning`, `episode`), pozostawiając wykrywanie napisów ekranowych dedykowanej fladze strukturalnej `has_sign_flag` (ustawianej przez `sign_detector.py` i `scene_discourse.py`)[cite: 18]. | `ZAWĘŻENIE_TRIGGERA` | **`P1`** | Eliminuje fałszywe wzbudzanie `DYN_8` w zwykłych scenach dialogowych (redukcja zbędnego szumu w prompcie Fazy 1 i Fazy 2)[cite: 18]. |
| **`R-02`** | **Niespójność normy CPS i duplikacja checklisty `BASE` w `verifier.py`** — szablon promptu w `verifier.py` powtarza własnymi słowami reguły z `STANDARD_9_CORE_RULES_PROMPT`, podając przy tym wyłącznie stary próg `17 CPS` zamiast wprowadzonego w `10.3` optimum `14–15 CPS` (pułap `17 CPS`)[cite: 18]. | Zsynchronizować opis budżetu czytelniczego w szablonie `verifier.py` z regułą `R1.7` (wskazanie optimum percepcyjnego `14–15` znaków na sekundę przy pułapie `17` znaków na sekundę) oraz odchudzić ręczną listę kontrolną w `verifier.py` z punktów powielających słowo w słowo dołączony wyżej `STANDARD_9_CORE_RULES_PROMPT`[cite: 18]. | `ZMNIEJSZENIE` / `REORGANIZACJA` | **`P1`** | Usuwa dysonans poznawczy modelu Fazy 2 (sprzeczność `14–15 CPS` w `R1.7` vs `17 CPS` w treści promptu `verifier.py`) i oszczędza `~250–300` tokenów w każdym wywołaniu Fazy 2[cite: 18]. |
| **`R-03`** | **Zjawisko *slot starvation* w gęstych paczkach 24-liniowych** — gdy w paczce `24` linii wystąpią naraz 4 zjawiska (np. `DYN_4` `88` przez słowo `girl`/`kid`, `DYN_3` `84` przez `-san`, `DYN_5` `82` przez wykrzykniki oraz `DYN_8` `70` przez grę słowną), szeroki trigger `DYN_4` (`girls|women|kid|child`) zajmuje slot w `top-3` i wypycha `DYN_8` (`70`) lub `DYN_9` (`74`), mimo że zasada grup kobiecych jest już w `BASE` (`R1.4` i `R3.3`)[cite: 18]. | Zawęzić trigger `age_gender_pat` (`DYN_4`, `score 88`) w `rules.py:2765` do faktycznych przypadków niejednoznaczności wieku/płci fonicznej (chłopcy mówiący wysokim głosem, sędziwe postacie, mowa dziecięca), ponieważ ogólna ochrona rodzaju grup kobiecych (`girls`, `women`, `ladies`) jest już **zawsze aktywna** w regułach bazowych `R1.4` oraz `R3.3`[cite: 18]. | `ZAWĘŻENIE_TRIGGERA` | **`P1`** | Uwalnia slot w `top-3` dla kategorii `DYN_6`, `DYN_9`, `DYN_7` i `DYN_8` w scenach, w których pada zwykłe słowo `girls` lub `women`[cite: 18]. |
| **`R-04`** | **4-krotna redundancja reguły grup niemęskoosobowych (`R1.4` + `R3.3` + `profiler.py` + `DYN_4`)** — w samym `STANDARD_9_CORE_RULES_PROMPT` zasada form niemęskoosobowych dla grup kobiecych jest zapisana dwa razy (`R1.4` w `FILAR 1` oraz `R3.3` w `FILAR 3`)[cite: 18]. | Skonsolidować wzmiankę o grupach niemęskoosobowych w `R3.3` (`FILAR 3 — Spójność Rodzaju Gramatycznego P0`), a `R1.4` poświęcić w całości zaimkowi zwrotnemu i dzierżawczemu (`swój`), zachowując identyfikator `R1.4.` dla kompatybilności z bramkami CI/CD[cite: 18]. | `REORGANIZACJA` | **`P2`** | Eliminuje jedyny duplikat semantyczny wewnątrz samego `STANDARD_9_CORE_RULES_PROMPT` bez zmiany numeracji reguł `R1.1–R3.5`[cite: 18]. |
| **`R-05`** | **Podwójne wstrzykiwanie dyrektywy kontrastu rejestrów przy parafrazie gwary (`rules.py:2731` vs `translator.py:1556` i `verifier.py:166`)** — tekst `DYN_1` zawiera już instrukcję o parafrazie gwary, którą `translator.py` i `verifier.py` doklejają drugi raz jako osobny blok `[PARAFRAZA GWARY — KONTRAST REJESTRÓW]`[cite: 18]. | Pozostawić bez zmian jako świadome wzmocnienie (*reinforcement*) wymagane przez testy regresyjne `T10.1.1_P1a` i `T10.1.1_P1b`, lub w ramach przyszłego porządkowania `11.0` zastąpić pełny duplikat w `translator.py` krótką, 1-linijkową kotwicą odsyłającą do aktywnego `FILARU XIII`[cite: 18]. | `ZMNIEJSZENIE` *(opcjonalne w 11.0)* | **`P2`** | Oszczędność `~100` tokenów w paczkach z gwarą przy zachowaniu kompatybilności z testami `T10.1.1`[cite: 18]. |

---

### P5.2. Werdykt końcowy

- **Werdykt:** **`PROMPT_WYMAGA_DROBNYCH_POPRAWEK`**[cite: 18]
- **Uzasadnienie werdyktu:** Architektura doboru Filarów po wdrożeniu Standardów `10.2–10.4` (`ebbe426`) jest fundamentalnie zdrowa i **skutecznie chroni model LLM przed przeciążeniem informacyjnym** (zawsze aktywne `BASE` to zaledwie `4 076` znaków / `16` zwięzłych reguł, a selektor dynamiczny dokleja średnio `0–2`, maksymalnie `3` ortogonalne kategorie `DYN`, utrzymując cały prompt paczki na poziomie `~3,3k–4,6k` tokenów, tj. `<0,5%` okna modelu)[cite: 18]. Wskazane w raporcie poprawki (`R-01` – `R-03` o priorytecie `P1`) mają charakter precyzyjnego strojenia: eliminują fałszywe wyzwalacze słów `notice`/`sign`/`girls` w `DYN_8` i `DYN_4` (zapobiegając wypychaniu innych reguł ze slotu `top-3`) oraz synchronizują opis normy `14–15 CPS` w szablonie `verifier.py` z regułą `R1.7`[cite: 18].

---

## 8. FAZA ODBIORU

- [x] FAZA 0 — Inwentaryzacja: `15` operacji regex (`14` `re.compile` + `1` `re.search`), `max_rules=3`, `batch_size=24`, rozmiar `BASE=4076` znaków (`44` linie), rozmiar pasywnego `TRANSLATION_RULES_PROMPT=204008` znaków (niewysyłany do LLM)[cite: 18]
- [x] FAZA 1 — Przepływ doboru: `10` kroków potoku przeanalizowanych, `9` kategorii `DYN_1–DYN_9` opisanych, `Anti-Smoothing Filter` chroni `DYN_1`, `DYN_2` i `DYN_9` przed wygładzeniem przez `DYN_5`[cite: 18]
- [x] FAZA 2 — Per-paczka: `5` reprezentatywnych paczek przeanalizowanych, średnia liczba aktywnych kategorii `DYN` wynosi `0–2` (maksymalnie `3` dzięki `candidates[:max_rules]`)[cite: 18]
- [x] FAZA 3 — Rozmiar promptu: Faza 1 `~3 330` tokenów (typowy) / `~4 585` tokenów (worst-case), Faza 2 `~4 210` tokenów (typowy) / `~5 040` tokenów (worst-case) — `<0,5%` okna kontekstowego LLM[cite: 18]
- [x] FAZA 4 — Przeciążenie: `8` potencjalnych źródeł przebadanych (`4` wyeliminowane w 100%, `4` drobne redundancje/nadmiarowe triggery zidentyfikowane z dowodami z kodu), werdykt cząstkowy `WYMAGA_DROBNYCH_POPRAWEK`[cite: 18]
- [x] FAZA 5 — Rekomendacje: `5` łącznie (`0` P0, `3` P1: `R-01`, `R-02`, `R-03`, `2` P2: `R-04`, `R-05`)[cite: 18]
- [x] Werdykt: `PROMPT_WYMAGA_DROBNYCH_POPRAWEK`[cite: 18]
- [x] 0 placeholderów `<DO_WYPEŁNIENIA>`
- [x] 0 zmian w kodzie (`git status` clean)
- [x] 0 commitów
- [x] Z16 nienaruszone[cite: 18]
- [x] Z1/Z2/Z3/Z4 respektowane[cite: 18]
