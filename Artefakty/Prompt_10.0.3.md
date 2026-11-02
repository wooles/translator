<USER_REQUEST>
# PROMPT WYKONAWCZY (STANDARD 10.0.3 / 10.1) — ELIMINACJA ROZSZCZEPIENIA TOŻSAMOŚCI P0/P2 W SERIESBIBLE I PRZECIEKU F0 MÓWCY NA ADRESATA W TELEMETRII

## PREAMBUŁA

Test generalizacji Standardu 10.0 na odcinku 30 nowej serii (`tensei_kizoku_kantei_skill_de_nariagaru`, 331 zdarzeń) ujawnił systematyczny flip płci gramatycznej w polu `Adresat:` telemetrii (oraz dla części niezweryfikowanych mówców epizodycznych):
1. Zweryfikowane postacie męskie `P0` (`gender: "MALE"`, `grammatical_gender: "MASCULINE"`, `has_verified_gender: true` w `SeriesBible`) występujące w roli adresata pod krótkim imieniem są oznaczane jako `(FEMININE)` w sąsiednich liniach tej samej sceny (np. `ID 61–62`: `MASCULINE` → `ID 63–70`: `FEMININE` → `ID 71–73`: `MASCULINE`).
2. Zweryfikowane postacie żeńskie `P0` (`gender: "FEMALE"`, `grammatical_gender: "FEMININE"`, `has_verified_gender: true` w `SeriesBible`) występujące w roli adresata pod krótkim imieniem są oznaczane jako `(MASCULINE)` (np. `ID 114–124, 200–201, 219–224, 237–238, 246, 315–316, 318, 320, 325–326, 328–329`).
3. Etykiety generyczne o jednoznacznym rodzaju męskim w języku polskim są oznaczane jako żeńskie zawsze wtedy, gdy mówcą jest kobieta (`ID 116, 117, 123, 129, 130`: `Adresat: Mężczyzna (FEMININE)`; `ID 125, 132, 280`: `Adresat: Grupa Mężczyzn (FEMININE)`).
4. W `ID 299` jawny aktor z kolumny `Name` pliku `.ass` (krótkie imię postaci `P0 FEMALE`) został nadpisany w polu `Mówca:` przez `Bandit F (FEMININE)`, ponieważ krótki tag widniał w `SeriesBible` jako niezweryfikowany duplikat `P2 UNKNOWN`.

Audyt źródłowy wykazał, że przyczyną jest **zespół 4 powiązanych defektów deterministycznych (`H1 + H7 + H2 + H8`)**:
- **Defekt 1 (`H7` — `series_memory.py`):** `SeriesBible.populate_secondary_actor_tags` (`series_memory.py:6673`) tworzy wpisy `P2` (`gender: "UNKNOWN"`, `has_verified_gender: false`) dla jednoczłonowych tagów z pliku `.ass`, nie sprawdzając, czy dany tag znajduje się już na liście `aliases` istniejącej postaci `P0` (lub `P1`). Z kolei `_sanitize_loaded_bible_in_ram` nie scala/nie usuwa takich duplikatów `P2` wczytanych z dysku.
- **Defekt 2 (`H1` — `series_memory.py` / `scene_discourse.py` / `translator.py`):** Bezpośredni odczyt `characters.get(clean_name)` oraz budowa słowników pomocniczych przez iterację `for k, v in characters.items()` (gdzie wpisy `P2` znajdują się na końcu słownika po wpisach `P0`) powodują, że dla krótkiego imienia (`clean_target_actor` lub `raw_actor`) zwracany jest wpis `P2 UNKNOWN` zamiast wpisu `P0` posiadającego to imię w `aliases`.
- **Defekt 3 (`H2` — `scene_discourse.py` / `translator.py`):** Gdy adresat nie ma twardej blokady `P0`, procedura rozwiązywania płci adresata (`target_gender` / `addressee_gender`) wykorzystuje akustykę F0 bieżącego segmentu audio (należącą do **mówcy**!) lub niezablokowany profil F0, a także nadpisuje `target_gender` przez `you_virility` (`Grupa_2os_lm: VIRILE` → `MASCULINE` dla pojedynczej adresatki!).
- **Defekt 4 (`H8` — `scene_discourse.py` / `series_memory.py`):** Generyczne polskie i angielskie deskryptory adresatów i mówców (`"Mężczyzna"`, `"Grupa Mężczyzn"`, `"Dwóch Mężczyzn"`, `"Kobieta"`, `"Grupa Kobiet"`, `"Strażnik ..."`, `"Mieszkaniec ..."`) nie mają twardej kotwicy leksykalnej przed uruchomieniem estymacji akustycznej F0.

---

## TWOJA ROLA I OGRANICZENIA

1. **Pełny dostęp wykonawczy:** Masz dostęp do repozytorium git, `python`, `pytest`, `grep` oraz `powershell`.
2. **Naprawa przyczyny źródłowej (Zero łat kazuistycznych):** Wprowadzasz wyłącznie rozwiązania architektoniczne i metajęzykowe zgodne z 5 zasadami Standardu 9.0/10.0 (`Z1 Zero-Literal`, `Z2 Pure Positive Domain`, `Z3 Primary LLM Translation Authority`, `Z4 Instance-Free`, `Z16 Ochrona Depuracji 1.0`).
3. **Dwa artefakty dokumentacyjne:** Zapisujesz na dysku:
   - `Artefakty/Raport_audytu_10.0.3_diagnoza_flip_plci.md` (pełny raport diagnostyczny H1–H8 z surowymi wyjściami z Fazy 0 — **UWAGA:** raport audytora został już wygenerowany przez agenta audytującego, patrz SEKCJA 7 U5 — nie odtwarzaj go, tylko potwierdź diagnozę w FAZIE 0),
   - `Artefakty/Raport_wdrozenia_10.0.3.md` (raport wdrożenia napraw 2B.1–2B.5 według szablonu z końca niniejszego promptu).

---

## FAZA 0 — DIAGNOSTYKA WSTĘPNA W KODZIE I BAZACH BIBLE (OBOWIĄZKOWA PRZED MODYFIKACJĄ)

Przed wykonaniem jakiejkolwiek edycji uruchom poniższe 6 komend diagnostycznych i zapisz ich surowe wyjścia do Sekcji 0 raportu:

1. **Weryfikacja duplikatów P0/P2 we wszystkich bazach `series_memory/*_bible.json`:**
   ```bash
   python -c "import glob, json; 
   for p in sorted(glob.glob('series_memory/*_bible.json')):
       d = json.load(open(p, encoding='utf-8'))
       chars = d.get('characters', {})
       p0_aliases = {a.lower(): k for k, v in chars.items() if v.get('has_verified_gender') or v.get('priority') == 'P0' for a in v.get('aliases', []) if a.lower() != k.lower()}
       dups = [(k, v.get('priority'), v.get('gender'), p0_aliases[k.lower()]) for k, v in chars.items() if k.lower() in p0_aliases and (not v.get('has_verified_gender') or v.get('gender') == 'UNKNOWN')]
       if dups: print(p, '-> DUPLICATES:', dups)"
   ```
2. **Reprodukcja błędu `H1` na bazie `Tensei_Kizoku_Kantei_Skill_de_Nariagaru`:**
   ```bash
   python -c "from series_memory import SeriesBible; from scene_discourse import SceneDiscourseGraph;
   b = SeriesBible('Tensei_Kizoku_Kantei_Skill_de_Nariagaru');
   for name in ['Ars', 'Shin', 'Rietz', 'Rosell', 'Maika', 'Rikuya', 'Takao', 'Licia', 'Charlotte', 'Grupa Mężczyzn', 'Mężczyzna']:
       t = SceneDiscourseGraph.arbitrate_event_telemetry(raw_actor='Shin Seymarrow', target_actor=name, series_bible=b);
       print(name, '-> target_gender:', t.get('target_gender'), 'addressee_gender:', t.get('addressee_gender'), 'p0_verified:', t.get('target_p0_verified'))"
   ```
3. **Lokalizacja wszystkich odczytów `characters.get` i budowy map aliasów w `series_memory.py`, `scene_discourse.py`, `translator.py`:**
   ```bash
   grep -n "characters\.get\|characters\[\|_lookup_p0\|populate_secondary_actor_tags" series_memory.py scene_discourse.py translator.py
   ```
4. **Lokalizacja wszystkich przypisań `addressee_gender` i `target_gender` w `scene_discourse.py` i `translator.py`:**
   ```bash
   grep -n "addressee_gender\|target_gender" scene_discourse.py translator.py profiler.py
   ```
5. **Lokalizacja użycia `f0_hz` / `f0_val` / `speaker_tags` przy estymacji adresata i mówcy w `scene_discourse.py` i `translator.py`:**
   ```bash
   grep -n "triangulate_epistemic_gender\|f0_hz\|f0_val\|speaker_tags" scene_discourse.py translator.py
   ```
6. **Sprawdzenie Bramki Z16 przed modyfikacją (`STOP_Z16`):**
   ```bash
   python -c "import pathlib, re; src = pathlib.Path('test_system.py').read_text(encoding='utf-8'); print('def test_:', len(re.findall(r'(?m)^def test_', src))); print('mark.slow:', len(re.findall(r'@pytest\.mark\.slow\b', src))); print('mark.network:', len(re.findall(r'@pytest\.mark\.network\b', src)))"
   grep -n "# DEFENSIVE_FALLBACK" avt_linter.py
   ```

**DODATKOWO — weryfikacja sygnatury `arbitrate_event_telemetry` (patrz SEKCJA 7 U1):**
```bash
grep -nA 10 "def arbitrate_event_telemetry" scene_discourse.py
```
Wklej pełną sygnaturę (wszystkie parametry) do Sekcji 0 raportu.

---

## SEKCJA 1 — REGUŁY DLA MODELI LLM I PIPELINE'U DANYCH (PURE POSITIVE DOMAIN)

Zachowaj w `rules.py` (`STANDARD_9_CORE_RULES_PROMPT`) wszystkie reguły `R1.1–R1.11` oraz `R3.1–R3.5` w czystej formie pozytywnej („Prawidłowy stan = X”), ze szczególnym egzekwowaniem w kodzie:
- **R1.9 (P0) — STRUKTURALNY PRYMAT REKORDU P0 W TELEMETRII I PRE-PASSIE SCENICZNYM:** Prawidłowy stan telemetrii mówcy i adresata oraz statystyk obsady sceny odzwierciedla płeć z rekordu P0 (`SeriesBible`), zachowując nadrzędność ponad estymacją akustyczną F0 dla postaci P0/P1.
- **R3.2 (P0) — NADRZĘDNOŚĆ REKORDU P0 W GRAFIE DYSKURSU I PRE-PASSIE (`SceneDiscourseGraph` & `EpisodeProfiler`):** Prawidłowy stan płci mówcy (`speaker_gender`), adresata (`target_gender` / `addressee_gender`) oraz flag scenicznych (`female_only_scene`, `male_only_scene`, `we_virility`, `you_virility`) bezwarunkowo odzwierciedla zweryfikowany rekord P0 z `SeriesBible` (rozwiązywany z priorytetem P0 po pełnej nazwie oraz po wszystkich aliasach P0) oraz inherentną płeć leksykalną polskich i angielskich deskryptorów ról.

---

## SEKCJA 2 — OPERACJE REWIZJI (2A / 2B / 2C)

### 2A — Operacje potwierdzone historycznie (1–15 z 10.0.2)
Zachowaj bez zmian wszystkie 15 operacji historycznych zweryfikowanych w `Raport_wdrozenia_10.0.2.md` (§ 4).

---

### 2B — Chirurgiczne operacje naprawcze (`2B.1` .. `2B.5`)

#### Operacja `2B.1` (`BLOCKING` | Zasada: `Z3` / `Z4` | Hipoteza `H1`): Kanoniczny resolver encji `P0-First Alias Resolution` w `SeriesBible` i `SceneDiscourseGraph`
- **Problem w kodzie:** Bezpośrednie wywołania `characters.get(clean_name)` oraz niesortowane pętle po `characters.items()` w `series_memory.py`, `scene_discourse.py` i `translator.py` zwracają niezweryfikowany wpis `P2 UNKNOWN` (lub pozwalają mu nadpisać w mapie aliasów wcześniejszy wpis `P0`), gdy w bazie istnieje wpis `P0` pod pełnym imieniem i nazwiskiem mający `clean_name` na liście `aliases`.
- **Kierunek naprawy:**
  1. W klasie `SeriesBible` (`series_memory.py`) zaimplementuj (lub ujednolić istniejącą) deterministyczną metodę `resolve_character_record(self, query_name: str) -> Optional[Dict[str, Any]]`, która rozwiązuje nazwę aktora/adresata według ścisłej hierarchii priorytetów:
     - **Krok 1 (Exact & Alias P0/Verified Match):** Przeszukaj wszystkie rekordy w `self.data["characters"]`, które mają `has_verified_gender == True` lub `priority == "P0"` (a następnie `P1`) i `gender in ("MALE", "FEMALE")`. Jeśli `query_name` (po normalizacji case-insensitive i odcięciu tytułów grzecznościowych `Lord`, `Lady`, `Sir`, `Master`, `Pan`, `Pani`, `Książę`, `Król` itp.) pasuje do klucza głównego LUB do któregokolwiek elementu `aliases` dokładnie jednego zweryfikowanego rekordu P0/P1 (lub wszystkich dopasowanych o tej samej płci), zwróć ten rekord `P0` wraz z jego kanoniczną nazwą i zweryfikowaną płcią.
     - **Krok 2 (Unverified Fallback):** Dopiero gdy żaden zweryfikowany rekord `P0`/`P1` nie pasuje po kluczu ani po aliasie, sprawdź wpisy `P2`.
  2. W `SceneDiscourseGraph.arbitrate_event_telemetry` (`scene_discourse.py`), w `_lookup_p0` oraz we wszystkich miejscach w `translator.py` i `profiler.py`, gdzie budowany jest `character_registry` / `known_characters` lub rozwiązywany jest `raw_actor` i `target_actor` (`addressee`), użyj `resolve_character_record` (P0-first) zamiast surowego `characters.get(...)`.
  3. Przy budowie jakichkolwiek słowników `alias -> record` z `SeriesBible.data["characters"]`, sortuj wpisy tak, aby rekordy `P0` (`has_verified_gender: True`) miały absolutny priorytet i **nigdy nie mogły zostać nadpisane** przez rekord `P2` (`has_verified_gender: False`).

#### Operacja `2B.2` (`BLOCKING` | Zasada: `Z4` | Hipoteza `H7`): Blokada tworzenia duplikatów `P2` w `populate_secondary_actor_tags` i scalanie duplikatów `P0/P2` w `_sanitize_loaded_bible_in_ram`
- **Problem w kodzie:** `SeriesBible.populate_secondary_actor_tags` (`series_memory.py:6673`) tworzy nowe wpisy `P2 UNKNOWN` dla krótkich tagów z `.ass` (np. `"Ars"`, `"Shin"`, `"Maika"`, `"Licia"`), mimo że są one już zarejestrowane jako `aliases` postaci `P0` (`"Ars Louvent"`, `"Shin Seymarrow"`, `"Maika Fujimiya"`, `"Licia Plaid"`).
- **Kierunek naprawy:**
  1. W `SeriesBible.populate_secondary_actor_tags` (`series_memory.py`): przed utworzeniem nowego wpisu `P2` dla `clean_tag`, sprawdź za pomocą `resolve_character_record(clean_tag)` (oraz przeszukując `aliases` wszystkich istniejących encji w `self.data["characters"]`), czy `clean_tag` (case-insensitive) jest już nazwą lub jednoznacznym aliasem istniejącej encji. Jeśli tak — **nie twórz nowego wpisu `P2`**.
  2. W `SeriesBible._sanitize_loaded_bible_in_ram` (`series_memory.py`): dodaj krok **deduplikacji P2 względem aliasów P0/P1**:
     - Zbierz zbiór wszystkich nazw głównych i aliasów (case-insensitive) należących do zweryfikowanych rekordów `P0`/`P1` (`has_verified_gender == True` i `gender in ("MALE", "FEMALE")`), o ile dany alias nie jest współdzielonym nazwiskiem rodowym różnych płci (np. `Fujimiya` należy jednocześnie do `Maika Fujimiya` i `Rikuya Fujimiya`).
     - Każdy wpis w `self.data["characters"]` o `priority == "P2"` (lub `has_verified_gender == False` i `gender == "UNKNOWN"`), którego klucz pokrywa się z jednoznacznym aliasem zweryfikowanego rekordu `P0`/`P1`, **usuń ze słownika `self.data["characters"]`** (upewniając się uprzednio, że klucz ten znajduje się na liście `aliases` odpowiedniego rekordu `P0`).
  3. Uruchom `_sanitize_loaded_bible_in_ram()` i zapisz oczyszczone pliki `*_bible.json` w `series_memory/` (w szczególności `Tensei_Kizoku_Kantei_Skill_de_Nariagaru_bible.json`) oraz `Artefakty/`.

#### Operacja `2B.3` (`BLOCKING` | Zasada: `Z3` | Hipoteza `H2`): Całkowita separacja akustyki F0 mówcy od estymacji płci adresata i ochrona pojedynczej adresatki przed `you_virility`
- **Problem w kodzie:**
  1. Akustyczne F0 bieżącego zdarzenia (`f0_hz` / `speaker_tags`) należy fizycznie do **mówcy** wypowiadającego daną kwestię, a nie do **adresata** (który w tym czasie milczy!). Używanie F0 bieżącego segmentu (lub niezablokowanego F0 z cross-gender castingu) do zgadywania płci adresata powoduje, że gdy mówi kobieta, adresat staje się `FEMININE`, a gdy mówi mężczyzna, adresatka staje się `MASCULINE`.
  2. Dodatkowo, gdy `you_virility` (`Grupa_2os_lm`) ma wartość domyślną `VIRILE`, nie może ona nadpisywać `grammatical_gender` / `addressee_gender` pojedynczego adresata na `MASCULINE`!
- **Kierunek naprawy:**
  1. W `scene_discourse.py` (`arbitrate_event_telemetry` oraz metodach grafu dyskursu) i `translator.py` (`_arbitrate_speaker_gender` / budowa telemetrii): **bezwzględnie odetnij przekazywanie F0 bieżącego segmentu audio (`f0_hz`, `speaker_tags` bieżącej linii) do wyznaczania płci adresata (`target_gender` / `addressee_gender`)**.
  2. Płeć adresata (`target_gender` / `addressee_gender`) może być wyznaczana wyłącznie z:
     - **(a)** Zweryfikowanego rekordu `P0`/`P1` w `SeriesBible` (przez `resolve_character_record` z `2B.1`, wliczając relacje skierowane `Speaker -> Target` w `SeriesBible.data["relations"]`),
     - **(b)** Jawnego znacznika `(M)`/`(F)` przy tagu adresata (`normalize_actor_tag`),
     - **(c)** Inherentnej płci leksykalnej rzeczownika roli/grupy adresata (`2B.4`),
     - **(d)** Jednoznacznych zaimków/tytułów 2. osoby w `source_en` (`Lord`, `Lady`, `Sir`, `Ma'am`, `Brother`, `Sister`, `little man`, `boy`, `girl`),
     - **(e)** Jeśli żaden z powyższych dowodów (a)–(d) nie rozstrzyga płci adresata, `target_gender` / `addressee_gender` musi pozostać `"UNKNOWN"` (a nie być zgadywane z F0 mówcy ani nadpisywane przez `Grupa_2os_lm: VIRILE`!).
  3. Upewnij się, że dla pojedynczego adresata o zweryfikowanej płci `FEMALE` (`addressee_gender == "FEMININE"`, `addressee_number == "SINGULAR"`), pole `you_virility` (`Grupa_2os_lm`) nie przyjmuje wartości `"VIRILE"` i nie nadpisuje nawiasu przy `Adresat: <Imię> (FEMININE)`.

#### Operacja `2B.4` (`BLOCKING` | Zasada: `Z4` | Hipoteza `H8`): Twarda kotwica leksykalna dla generycznych deskryptorów płci i ról (`Mężczyzna`, `Grupa Mężczyzn`, `Kobieta`, `Strażnik`, `Mieszkaniec`)
- **Problem w kodzie:** Etykiety takie jak `"Mężczyzna"`, `"Grupa Mężczyzn"`, `"Dwóch Mężczyzn"`, `"Kobieta"`, `"Grupa Kobiet"` (emitowane przez F1 w polu `addressee`) oraz polskie/angielskie role z prefiksem/sufiksem miejsca (`"Strażnik Canarre"`, `"Mieszkaniec Canarre"`, `"Soldier A"`, `"Bandit E"`) nie są rozpoznawane przez twardą regułę leksykalną przed fallbackiem akustycznym, co prowadzi do `Adresat: Mężczyzna (FEMININE)`, `Adresat: Grupa Mężczyzn (FEMININE)` oraz `Mówca: Strażnik Canarre (FEMININE)`.
- **Kierunek naprawy:**
  1. W `series_memory.py` / `scene_discourse.py` dodaj deterministyczną funkcję `resolve_lexical_label_gender(label: str) -> Tuple[Optional[str], Optional[str]]`, która analizuje tokeny etykiety (zarówno dla mówcy, jak i adresata):
     - Jeśli etykieta zawiera jednoznaczny polski lub angielski leksem męskoosobowy/męski (`mężczyzna`, `mężczyźni`, `mężczyzn`, `grupa mężczyzn`, `dwóch mężczyzn`, `chłopiec`, `chłopak`, `ojciec`, `brat`, `syn`, `król`, `książę`, `lord`, `pan`, `strażnik`, `żołnierz`, `bandyta`, `mieszkaniec`, `kupiec`, `man`, `men`, `boy`, `brother`, `father`, `king`, `lord`, `sir` — z `INHERENT_MALE_NOUNS`), zwraca `("MALE", "MASCULINE")` (oraz dla grup mnogich `you_virility = "VIRILE"`).
     - Jeśli etykieta zawiera jednoznaczny leksem żeński (`kobieta`, `kobiety`, `kobiet`, `grupa kobiet`, `dziewczyna`, `dziewczynka`, `matka`, `siostra`, `córka`, `królowa`, `księżniczka`, `lady`, `pani`, `strażniczka`, `mieszkanka`, `kelnerka`, `pokojówka`, `woman`, `women`, `girl`, `sister`, `mother`, `queen`, `lady`, `ma'am` — z `INHERENT_FEMALE_NOUNS`), zwraca `("FEMALE", "FEMININE")` (oraz dla grup mnogich `you_virility = "NON_VIRILE"`).
     - Dla wielowyrazowych ról z toponimem (np. `"Strażnik [Toponim]"`, `"Mieszkaniec [Toponim]"`), głową składniową jest pierwszy rzeczownik pospolity (`Strażnik`, `Mieszkaniec` -> `MALE`), który ma pierwszeństwo przed szumem akustycznym F0 (chyba że w `SeriesBible` istnieje jawny rekord P0 stanowiący inaczej).
  2. Ponadto dla ról generycznych mówców (`Soldier A..Z`, `Bandit A..Z`, `Guard A..Z`): jeżeli w bieżącej lub poprzedniej kwestii tej samej postaci w F1/F2 występują jednoznaczne formy męskie 1. osoby (`myślałem`, `miałem`, `zebrałem`, `usłyszałem`, `rozejrzałem się`, `zaszedłem`) lub zwrot adresatywny `aniki` / `bro` (`ID 257, 276, 279, 290`), zablokuj klasyfikację mówcy jako `FEMININE` na skutek wysokiego F0 krzyku bojowego.

#### Operacja `2B.5` (`MAJOR` | Zasada: `Z3` | Hipoteza `H3` + `ID 299`): Ochrona jawnego aktora z kolumny `Name` pliku `.ass` przed nadpisaniem w polu `Mówca:`
- **Problem w kodzie:** W `ID 299` plik `.ass` posiada jawnego aktora (`Aktor: Maika`), jednak w `Telemetria:` pojawia się `Mówca: Bandit F (FEMININE)`.
- **Kierunek naprawy:**
  Gdy zdarzenie `.ass` posiada jawnego, niepustego aktora w kolumnie `Name` (`raw_actor` niebędący pustym ciągiem ani znacznikiem technicznym `sign`/`Default`/`Brak`), który po rozwiązaniu przez `resolve_character_record` (`2B.1`) odpowiada postaci z `SeriesBible`, nazwa `speaker_name` w telemetrii musi bezwzględnie zachować tę postać i nie może zostać nadpisana przez inną postać z sąsiedniej linii ani z halucynacji diarizacji (`R1.6`).

---

### 2C — Konflikty z historią
- **Brak konfliktu z Z16:** Wszystkie 5 operacji (`2B.1`–`2B.5`) uszczelnia prymat rekordów `P0` (`R1.9`, `R3.2`) oraz eliminuje duplikaty `P2 UNKNOWN` w `SeriesBible`, nie naruszając żadnego z testów `KEEP` w `test_system.py` (w tym `test_system.py:13301`).

---

## SEKCJA 3 — WALIDACJA TESTOWA (D1–D6, ZERO-LITERAL)

W katalogu `tests/` (`tests/test_series_memory.py` oraz `tests/test_discourse_and_translator.py`) dodaj sparametryzowane testy jednostkowe używające **wyłącznie syntetycznych identyfikatorów** (`HeroAlpha`, `HeroineBeta`, `CommanderGamma`, `StrategistDelta` — zgodnie z Zasadą 1 Zero-Literal):

```python
# Wzorzec 1 (dla 2B.1 i 2B.2: P0-first alias resolution i deduplikacja P2 w SeriesBible)
@pytest.mark.unit
@pytest.mark.parametrize(
    "short_name,full_name,p0_gender,expected_gram_gender",
    [
        ("HeroAlpha", "HeroAlpha Louventis", "MALE", "MASCULINE"),
        ("InventorBeta", "InventorBeta Seymarrowis", "MALE", "MASCULINE"),
        ("CommanderGamma", "CommanderGamma Musesis", "MALE", "MASCULINE"),
        ("TacticianDelta", "TacticianDelta Fujimiyas", "FEMALE", "FEMININE"),
        ("NobleEpsilon", "NobleEpsilon Plaidis", "FEMALE", "FEMININE"),
    ],
)
def test_addressee_and_speaker_gender_use_p0_alias_priority_over_p2_duplicate(
    short_name, full_name, p0_gender, expected_gram_gender
):
    from series_memory import SeriesBible
    from scene_discourse import SceneDiscourseGraph

    bible = SeriesBible(slug="test_p0_alias_priority", db_path=":memory:")
    bible.sync_verified_profile_entity(
        full_name,
        p0_gender,
        has_verified_gender=True,
    )
    # Symulacja duplikatu P2 UNKNOWN powstałego z krótkiego tagu .ass
    bible.data["characters"][short_name] = {
        "name": short_name,
        "gender": "UNKNOWN",
        "grammatical_gender": "UNKNOWN",
        "priority": "P2",
        "has_verified_gender": False,
        "confidence": 0.5,
        "aliases": [short_name],
    }
    bible._sanitize_loaded_bible_in_ram()

    # 1. Duplikat P2 musi zostać scalony/usunięty z characters na rzecz P0
    # (patrz SEKCJA 7 U2 — użyj jednego wariantu asercji, nie OR)
    assert short_name not in bible.data["characters"] or bible.data["characters"][short_name]["gender"] == p0_gender

    # 2. Arbitraż telemetrii dla krótkiego imienia w roli adresata musi zwrócić płeć P0
    telem = SceneDiscourseGraph.arbitrate_event_telemetry(
        raw_actor="OtherSpeaker",
        target_actor=short_name,
        series_bible=bible,
        f0_hz=310.0 if p0_gender == "MALE" else 115.0,  # Kontr-F0 mówcy (test odporności na H2!)
    )
    assert telem["target_gender"] == p0_gender
    assert telem["addressee_gender"] in (p0_gender, expected_gram_gender)
    assert telem["target_p0_verified"] is True


# Wzorzec 2 (dla 2B.3 i 2B.4: Odporność etykiet generycznych adresata na kontr-F0 mówcy)
@pytest.mark.unit
@pytest.mark.parametrize(
    "speaker_gender,f0_val,generic_addressee,expected_target_gender,expected_gram_gender",
    [
        ("FEMALE", 295.0, "Mężczyzna", "MALE", "MASCULINE"),
        ("FEMALE", 285.0, "Grupa Mężczyzn", "MALE", "MASCULINE"),
        ("FEMALE", 270.0, "Dwóch Mężczyzn", "MALE", "MASCULINE"),
        ("MALE", 115.0, "Kobieta", "FEMALE", "FEMININE"),
        ("MALE", 120.0, "Grupa Kobiet", "FEMALE", "FEMININE"),
        ("MALE", 280.0, "Strażnik Zamkowy", "MALE", "MASCULINE"),
        ("MALE", 265.0, "Mieszkaniec Miasta", "MALE", "MASCULINE"),
    ],
)
def test_generic_addressee_and_role_labels_immune_to_speaker_f0_contamination(
    speaker_gender, f0_val, generic_addressee, expected_target_gender, expected_gram_gender
):
    from scene_discourse import SceneDiscourseGraph

    telem = SceneDiscourseGraph.arbitrate_event_telemetry(
        raw_actor="SpeakerAlpha",
        speaker_p0_gender=speaker_gender,
        target_actor=generic_addressee,
        f0_hz=f0_val,
    )
    assert telem["target_gender"] == expected_target_gender
    assert telem.get("target_grammatical_gender", expected_gram_gender) == expected_gram_gender
```

**UWAGA:** Testy powyżej są **szkieletem** — przed wklejeniem dostosuj je zgodnie z SEKCJĄ 7 U1–U4 (sygnatura `arbitrate_event_telemetry`, naprawa słabych asercji, naprawa tautologii, dodatkowe testy dla `2B.5` i `2B.4` pkt 2).

---

## SEKCJA 4 — KOLEJNOŚĆ WDROŻENIA

1. **Etap 0 — Diagnostyka (`FAZA 0`):** Wykonaj 6 komend diagnostycznych + komendę weryfikacji sygnatury `arbitrate_event_telemetry` (7. komenda) i zapisz surowe wyjścia do Sekcji 0 raportu wdrożenia.
2. **Etap 1 — Naprawa `SeriesBible` (`2B.1` + `2B.2`):** Wdróż `resolve_character_record` (P0-first), zablokuj duplikaty w `populate_secondary_actor_tags`, dodaj deduplikację P2 względem aliasów P0 w `_sanitize_loaded_bible_in_ram` i oczyść wszystkie pliki `series_memory/*_bible.json` (w tym `Tensei_Kizoku_Kantei_Skill_de_Nariagaru_bible.json`).
3. **Etap 2 — Naprawa `SceneDiscourseGraph` i `MultimodalTranslator` (`2B.3` + `2B.4` + `2B.5`):** Odetnij F0 mówcy od estymacji płci adresata, wdróż `resolve_lexical_label_gender` dla etykiet generycznych i ról oraz zabezpiecz jawnego aktora z `.ass` przed nadpisaniem.
4. **Etap 3 — Testy jednostkowe i 4 bramki:** Dodaj testy z Sekcji 3 (z uwzględnieniem SEKCJI 7 U1–U4), uruchom `pytest` (fast, network, unit) oraz 4 bramki (`verify_purity.py`, `verify_12_fixes.py`, `verify_ultimate_pipeline.py`, `audit_diff.ps1`).
5. **Etap 4 — Walidacja empiryczna na danych odcinka 30 (`Tensei Kizoku`):** Wykonaj skrypt weryfikacji empirycznej (oraz jeśli dostępne środowisko — re-run telemetrii odcinka 30) potwierdzający `0` wystąpień wszystkich 10 kategorii błędów z listy kontrolnej (patrz warunek (f)).
6. **Etap 5 — Raport końcowy i commit:** Zapisz `Artefakty/Raport_wdrozenia_10.0.3.md` i zatwierdź zmiany w czystym drzewie git.

---

## SEKCJA 5 — WARUNKI UKOŃCZENIA (a)–(k) ORAZ WALIDACJA EMPIRYCZNA ODCINKA 30

Wdrożenie jest ukończone, gdy spełnione są wszystkie poniższe warunki:
- **(a)** Wykonano wszystkie 7 komend Fazy 0 i zapisano surowe wyjścia w Sekcji 0 raportu wdrożenia (raport audytu jest już wygenerowany przez agenta audytującego — patrz SEKCJA 7 U5, nie odtwarzaj go).
- **(b)** W pliku `series_memory/Tensei_Kizoku_Kantei_Skill_de_Nariagaru_bible.json` (oraz we wszystkich pozostałych `*_bible.json`) nie istnieje ani jeden duplikat `P2 UNKNOWN` dla imion będących aliasami postaci `P0` (`0` duplikatów w skrypcie nr 1 z Fazy 0).
- **(c)** `SeriesBible.populate_secondary_actor_tags` nie tworzy wpisów `P2` dla tagów będących aliasami istniejących postaci `P0`/`P1`.
- **(d)** `SceneDiscourseGraph.arbitrate_event_telemetry` rozwiązuje krótkie imiona adresatów i mówców przez `resolve_character_record` (P0-first) i nigdy nie używa akustyki F0 mówcy do zgadywania płci adresata.
- **(e)** Etykiety generyczne (`Mężczyzna`, `Grupa Mężczyzn`, `Dwóch Mężczyzn`, `Kobieta`, `Grupa Kobiet`, `Strażnik ...`, `Mieszkaniec ...`) mają deterministyczną płeć leksykalną niezależną od F0 mówcy.
- **(f)** **Walidacja empiryczna telemetrii odcinka 30 (`Tensei Kizoku`) wykazuje dokładnie:**
  - `0` wystąpień `Adresat: Ars (FEMININE)`
  - `0` wystąpień `Adresat: Shin (FEMININE)`
  - `0` wystąpień `Adresat: Rietz (FEMININE)`
  - `0` wystąpień `Adresat: Rosell (FEMININE)`
  - `0` wystąpień `Adresat: Rikuya (FEMININE)`
  - `0` wystąpień `Adresat: Takao (FEMININE)`
  - `0` wystąpień `Adresat: Maika (MASCULINE)`
  - `0` wystąpień `Adresat: Licia (MASCULINE)` i `Adresat: Charlotte (MASCULINE)`
  - `0` wystąpień `Adresat: Grupa Mężczyzn (FEMININE)`
  - `0` wystąpień `Adresat: Mężczyzna (FEMININE)`
- **(g)** Nowe testy jednostkowe (Wzorzec 1 i Wzorzec 2 oraz testy dodatkowe z SEKCJI 7 U4) przechodzą w 100% (`PASSED`) i nie zawierają żadnych nazw własnych z anime (Zero-Literal).
- **(h)** Suita `pytest` (fast, unit, network) przechodzi w 100% (`0 failed`).
- **(i)** Wszystkie 4 bramki (`verify_purity.py`, `verify_12_fixes.py`, `verify_ultimate_pipeline.py`, `audit_diff.ps1`) zwracają `PASS`.
- **(j)** Zasada 16 jest w 100% zachowana (`test_system.py` nienaruszony, 3 gałęzie `# DEFENSIVE_FALLBACK` w `avt_linter.py` zachowane).
- **(k)** Zapisano kompletny plik `Artefakty/Raport_wdrozenia_10.0.3.md` bez placeholderów, a `git status` wskazuje `working tree clean`.

---

## SEKCJA 6 — ZAKAZY

1. **ZAKAZ 1 (Zero-Literal Z1):** Bezwzględny zakaz wpisywania nazw własnych z serii `Tensei Kizoku` (`Ars`, `Shin`, `Rietz`, `Rosell`, `Maika`, `Rikuya`, `Takao`, `Licia`, `Charlotte`, `Canarre`, `Missian`, `Yoh`) do kodu produkcyjnego `.py`, `rules.py`, `profiler.py` oraz do treści testów jednostkowych w `tests/test_*.py`! Wszystkie reguły w kodzie muszą być w 100% metajęzykowe (`Z4`).
2. **ZAKAZ 2 (Z16):** Zakaz modyfikacji `test_system.py`, `tests/archive/` oraz 3 gałęzi `# DEFENSIVE_FALLBACK` w `avt_linter.py`.
3. **ZAKAZ 3 (Z2):** Zakaz używania sformułowań negatywnych w regułach `rules.py` oraz zakaz pisania testów tautologicznych (D2) lub mockujących logikę domenową (D1).
4. **ZAKAZ 4 (Z3):** Zakaz zgadywania płci adresata z częstotliwości podstawowej głosu mówcy (`f0_hz`).
5. **ZAKAZ 5 (Wiarygodność sygnatur):** Zakaz wklejania do testów wywołań z parametrami, których `arbitrate_event_telemetry` nie przyjmuje (`TypeError`). Przed wklejeniem testów wykonaj 7. komendę FAZY 0 (`grep -nA 10 "def arbitrate_event_telemetry"`) i dostosuj sygnaturę testów.
6. **ZAKAZ 6 (Anty-D2/D4):** Zakaz używania `.get(key, default=expected)` w asercjach (D2 — tautologia) oraz zakaz używania `in (a, b)` w asercjach wartości (D4 — osłabiona asercja). Używaj wyłącznie `== expected` z jednoznaczną wartością oczekiwaną.

---

## SEKCJA 7 — UWAGI KRYTYCZNE DLA AGENTA KODUJĄCEGO (UZUPEŁNIENIE OPERATORA)

Przed wykonaniem Sekcji 3 (testy jednostkowe) uwzględnij poniższe 5 uwag krytycznych — bez nich testy nie spełnią Standardu 9.0 (Z2/D2/D4) lub wywalą się z `TypeError`:

### U1. Weryfikacja sygnatury `arbitrate_event_telemetry` przed użyciem w testach

W Sekcji 3 (Wzorce 1 i 2) testy wywołują:
```python
SceneDiscourseGraph.arbitrate_event_telemetry(..., f0_hz=..., speaker_p0_gender=...)
```

**Przed wklejeniem testów** wykonaj (patrz FAZA 0, komenda 7):
```bash
grep -nA 10 "def arbitrate_event_telemetry" scene_discourse.py
```

Sprawdź pełną listę parametrów. Jeśli `f0_hz` lub `speaker_p0_gender` **nie są** parametrami tej metody:
- **NIE** dodawaj ich do sygnatury (to naruszyłoby `2B.3` — zakaz przekazywania F0 do estymacji adresata).
- Dostosuj testy, aby F0 było przekazywane przez `aux_telemetry` (jeśli metoda to przyjmuje) lub przez `event.speaker_tags` / `event.f0_hz` (jeśli `arbitrate_event_telemetry` czyta je z obiektu `event`).
- Jeśli żaden mechanizm nie pozwala przekazać F0 — **pomiń test kontr-F0** i udokumentuj w raporcie: „Test odporności na kontr-F0 niemożliwy do wykonania przez sygnaturę `arbitrate_event_telemetry`; odporność na H2 weryfikowana wyłącznie przez test integracyjny z pełnym obiektem `event`."

### U2. Naprawa słabych asercji w Wzorcu 1 (D4)

W Wzorcu 1 zamień:
```python
assert short_name not in bible.data["characters"] or bible.data["characters"][short_name]["gender"] == p0_gender
```
na jednoznaczną asercję z dwóch wariantów (do wyboru przez Ciebie, zależnie od implementacji `2B.2`):
```python
# Wariant A: deduplikacja usuwa duplikat całkowicie
assert short_name not in bible.data["characters"], \
    f"Duplikat P2 '{short_name}' nie został usunięty z characters po _sanitize_loaded_bible_in_ram"

# Wariant B: deduplikacja scala duplikat w P0 (jeśli implementacja 2B.2 wybiera scalenie)
assert bible.data["characters"][short_name]["gender"] == p0_gender
assert bible.data["characters"][short_name]["has_verified_gender"] is True
```

Wybierz wariant zgodny z implementacją `2B.2` i użyj **jednego** z nich.

Zamień:
```python
assert telem["addressee_gender"] in (p0_gender, expected_gram_gender)
```
na:
```python
assert telem["addressee_gender"] == p0_gender, \
    f"addressee_gender={telem['addressee_gender']!r}, oczekiwano {p0_gender!r} (płeć P0)"
```

(`grammatical_gender` to osobne pole — `addressee_gender` przyjmuje wartości `"MALE"`/`"FEMALE"`, a `grammatical_gender` przyjmuje `"MASCULINE"`/`"FEMININE"`. Nie mieszaj ich w jednej asercji `in`.)

### U3. Naprawa tautologii w Wzorcu 2 (D2)

W Wzorcu 2 zamień:
```python
assert telem.get("target_grammatical_gender", expected_gram_gender) == expected_gram_gender
```
na:
```python
assert "target_grammatical_gender" in telem, \
    f"Brak klucza 'target_grammatical_gender' w telemetrii: {list(telem.keys())}"
assert telem["target_grammatical_gender"] == expected_gram_gender, \
    f"target_grammatical_gender={telem['target_grammatical_gender']!r}, oczekiwano {expected_gram_gender!r}"
```

Jeśli implementacja `arbitrate_event_telemetry` **nie zwraca** `target_grammatical_gender` — sprawdź, jaki klucz zwraca (`target_gender`? `addressee_gender`?) i użyj właściwego. **NIE używaj `.get(default=...)`** — to D2.

### U4. Dodatkowe testy wymagane przez warunki ukończenia (d)–(e)

Sekcja 3 zawiera tylko Wzorce 1 i 2. Warunki (d)–(e) wymagają pokrycia także:

**Test dla `2B.5` (ochrona jawnego aktora `.ass` z ID 299):**
```python
@pytest.mark.unit
@pytest.mark.parametrize("explicit_actor,p0_gender,expected_speaker_name", [
    ("HeroAlpha", "MALE", "HeroAlpha"),
    ("HeroineBeta", "FEMALE", "HeroineBeta"),
])
def test_explicit_ass_actor_not_overwritten_by_hallucinated_diarization(
    explicit_actor, p0_gender, expected_speaker_name
):
    from series_memory import SeriesBible
    from scene_discourse import SceneDiscourseGraph
    bible = SeriesBible(slug="test_explicit_actor", db_path=":memory:")
    bible.sync_verified_profile_entity(explicit_actor, p0_gender, has_verified_gender=True)
    telem = SceneDiscourseGraph.arbitrate_event_telemetry(
        raw_actor=explicit_actor,
        target_actor="OtherSpeaker",
        series_bible=bible,
    )
    assert telem["speaker_name"] == expected_speaker_name
    assert telem["speaker_p0_verified"] is True
```

**Test dla `2B.4` pkt 2 (mówca z formami męskimi 1. os. nie może być `FEMININE` mimo wysokiego F0 krzyku):**
```python
@pytest.mark.unit
@pytest.mark.parametrize("first_person_form,expected_gender", [
    ("myślałem, że to koniec", "MALE"),
    ("miałem go na oku", "MALE"),
    ("zebrałem ludzi", "MALE"),
    ("usłyszałem hałas", "MALE"),
])
def test_male_first_person_forms_override_acoustic_f0_feminine(
    first_person_form, expected_gender
):
    from scene_discourse import SceneDiscourseGraph
    telem = SceneDiscourseGraph.arbitrate_event_telemetry(
        raw_actor="SoldierAlpha",
        polish_text=first_person_form,
        # F0 wysokie (krzyk bojowy) — nie może nadpisać form męskich
    )
    assert telem["speaker_gender"] == expected_gender, \
        f"Forma 1. os. '{first_person_form}' powinna dać {expected_gender}, otrzymano {telem['speaker_gender']}"
```

Jeśli `arbitrate_event_telemetry` nie przyjmuje `polish_text` — sprawdź sygnaturę (patrz U1) i użyj właściwego mechanizmu (np. `event.text`).

### U5. Raport audytu vs raport wdrożenia

PREAMBUŁA mówi o dwóch plikach: `Artefakty/Raport_audytu_10.0.3_diagnoza_flip_plci.md` i `Artefakty/Raport_wdrozenia_10.0.3.md`. **Raport audytu jest już wygenerowany przez agenta audytującego** — kodujący nie musi go odtwarzać. Kodujący powinien:
- **NIE** generować ponownie `Raport_audytu_10.0.3_diagnoza_flip_plci.md` (to produkt audytora).
- **WYGENEROWAĆ** `Artefakty/Raport_wdrozenia_10.0.3.md` (template w Sekcji 6 poniżej).
- W Sekcji 0 raportu wdrożenia wkleić surowe wyjścia z FAZY 0 — jako **dowód potwierdzenia** diagnozy audytora w kodzie.

---

## TEMPLATE RAPORTU WDROŻENIA (`Artefakty/Raport_wdrozenia_10.0.3.md`)

```markdown
# RAPORT WDROŻENIA REWIZJI 10.0.3 / 10.1 (NAPRAWA FLIPU PŁCI ADRESATA P0/P2 I PRZECIEKU F0)

## 0. WYNIKI DIAGNOSTYKI WSTĘPNEJ (FAZA 0 — KOMENDY 1–7)
- **1. Duplikaty P0/P2 w `series_memory/*_bible.json` (PRZED i PO naprawie):** `<surowe wyjście>`
- **2. Reprodukcja `arbitrate_event_telemetry` dla krótkich nazw i etykiet generycznych (PRZED i PO naprawie):** `<surowe wyjście>`
- **3–6. Wyjścia `grep` oraz weryfikacja `STOP_Z16`:** `<surowe wyjścia>`
- **7. Sygnatura `arbitrate_event_telemetry` (`grep -nA 10 "def arbitrate_event_telemetry"`):** `<surowe wyjście + wniosek: parametry f0_hz / speaker_p0_gender istnieją / nie istnieją + sposób przekazania F0 w testach (U1)>`

## 1. METADANE GIT
- **Bazowy commit wejściowy:** `<HASH>`
- **Commit wyjściowy:** `<HASH>`

## 2. WERYFIKACJA HIPOTEZ AUDYTOWYCH (H1, H7, H2, H8, H3)
| Hipoteza | Status (`POTWIERDZONA` / `CZĘŚCIOWO` / `ODRZUCONA`) | Lokalizacja `file:line` i cytat z kodu | Wyjaśnienie mechanizmu |
| :--- | :--- | :--- | :--- |
| `H1` | ... | ... | ... |
| `H7` | ... | ... | ... |
| `H2` | ... | ... | ... |
| `H8` | ... | ... | ... |
| `H3` | ... | ... | ... |

## 3. WDROŻONE OPERACJE NAPRAWCZE (2B.1 .. 2B.5)
| Operacja | Plik:linia | Cytat z kodu po naprawie (min. 6 linii) | Test regresyjny (`plik::nazwa_testu`) |
| :--- | :--- | :--- | :--- |
| `2B.1` | ... | ... | ... |
| `2B.2` | ... | ... | ... |
| `2B.3` | ... | ... | ... |
| `2B.4` | ... | ... | ... |
| `2B.5` | ... | ... | ... |

## 4. WALIDACJA EMPIRYCZNA NA DANYCH ODCINKA 30 (`Tensei Kizoku`)
- **Wynik weryfikacji 10 klas błędów telemetrii (`Ars`, `Shin`, `Rietz`, `Rosell`, `Rikuya`, `Takao`, `Maika`, `Licia/Charlotte`, `Grupa Mężczyzn`, `Mężczyzna`):** `<surowe wyjście skryptu / logu: 0 błędów>`
- **Sposób wykonania:** `<re-run telemetrii odcinka 30 / skrypt weryfikacji offline>`

## 5. WYNIKI PYTEST I 4 BRAMEK WALIDACYJNYCH
- **Pytest Fast / Unit / Network:** `<surowe wyjścia>`
- **4 Bramki (`verify_purity.py`, `verify_12_fixes.py`, `verify_ultimate_pipeline.py`, `audit_diff.ps1`):** `<surowe wyjścia>`

## 6. WARUNKI UKOŃCZENIA (a)–(k) I DECYZJA KOŃCOWA
- `<lista [x] (a)–(k) + werdykt>`
```
</USER_REQUEST>
<ADDITIONAL_METADATA>
The current local time is: 2026-11-02T20:00:49+01:00.
</ADDITIONAL_METADATA>