# PROMPT WYKONAWCZY (STANDARD 10.6.1) — NAPRAWA SIŁOWEJ PODMIANY ALIASU KANONICZNEGO P0 PRZY KOLIZJACH TAGÓW WARIANTOWYCH ASS ORAZ OCHRONA ZAKRESU JEDNOCZŁONOWEGO (`series_memory.py`)

- **Wersja docelowa:** `10.6.1`
- **Wersja poprzednia (baseline):** `10.6` (HEAD `60bfa9d` — `60bfa9da98906d8471128831b94ae7dc64a27dc3`, gałąź `main`)
- **Baseline Depuracji Legacy 1.0 (Z16):** `474fb64`
- **Podstawa audytowa:** `Artefakty/Raport_audytu_cathy_cathysoul_i_guard_regresji.md` (Defekt A: `FIX-A.1`, `FIX-A.2`)
- **Zakres:** 3 operacje w `series_memory.py` (`2B.1`–`2B.3`) + 4 testy regresyjne w `tests/test_series_memory.py` (`T10.6.1_1`–`T10.6.1_4`) + raport `Artefakty/Raport_wdrozenia_10.6.1.md`.
- **Kolejność wdrażania:** Prompt 10.6.1 jest **pierwszym** z dwóch sekwencyjnych hotfixów. Po jego commicie i `git push origin main` nastąpi uruchomienie Prompt 10.6.2 (Defekt B — `verifier.py`). **Nie łącz obu hotfixów w jeden commit.**

**Cel:** Wyeliminowanie deterministycznego zniekształcania poprawnych antroponimów i toponimów wygenerowanych przez Fazy 1 i 2 w metodzie `apply_canonical_alias_declension` (`series_memory.py`):
1. Odcinanie technicznych przyrostków stanu/formy w tagach aktorów ASS (np. `<RZECZYWISTY_ANTROPONIM_SUFIKS_ARTYSTYCZNY_1>` typu `*Soul`, `*Spirit`, `*Ghost`, `*Voice`, `*Mind`, `*Shadow`, `*Clone`, `*like`, `*Mild`) w `populate_secondary_actor_tags` i scalanie ich z encją bazową `<RZECZYWISTY_ANTROPONIM_BAZOWY_1>`.
2. Deduplikacja kolizji aliasów `P0-vs-P0` w `_sanitize_loaded_bible_in_ram` oraz deterministyczny priorytet pełnych antroponimów głównych nad wpisami `"Postać epizodyczna / tło"` i technicznymi identyfikatorami `CamelCase` w `resolve_character_record` oraz `apply_canonical_alias_declension`.
3. Wprowadzenie ochrony **Single-Token Scope Parity** w `apply_canonical_alias_declension`: pojedynczy człon nazwy własnej użyty samodzielnie w tekście (`<RZECZYWISTY_ANTROPONIM_JEDNOCZŁONOWY_1>`) nie może być siłowo rozszerzany do wieloczłonowego pełnego imienia i nazwiska ani dłuższego klucza złożonego `CamelCase`.

**Zasady nadrzędne Standardu 9.0 (obowiązujące w 100%):**
- **Z1 (Zero-Literal):** całkowity zakaz umieszczania w kodzie, komentarzach i testach jakichkolwiek nazw własnych z anime. Używaj wyłącznie ogólnych kategorii metajęzykowych i syntetycznych nazw w testach (`Heroine`, `HeroineSoul`, `Heroine Royalhouse`, `PrincessAlpha`, `PrincessAlpha Royal`, `Lady Kingdom`).
- **Z2 (Pure Positive Domain):** komentarze i komunikaty wyłącznie w formie pozytywnej.
- **Z3 (Primary LLM Authority):** post-processing `apply_canonical_alias_declension` służy wyłącznie do korekty końcówki fleksyjnej błędnie odmienionego pojedynczego słowa, a nie do podmieniania poprawnego imienia na techniczny tag aktora lub doklejania imienia do nazwy własnej kraju/akademii.
- **Z4 (Instance-Free):** lista przyrostków technicznych tagów ASS (`Soul`, `Spirit`, `Ghost`, `Voice`, `Mind`, `Shadow`, `Echo`, `Clone`, `like`, `Mild`) definiuje ogólne angielskie rzeczowniki metadanych produkcyjnych w skryptach napisów, bez jakichkolwiek imion postaci.
- **Z16 (Ochrona Depuracji Legacy 1.0):** całkowity zakaz modyfikacji `test_system.py`, `tests/archive/`, 3 gałęzi `# DEFENSIVE_FALLBACK` w `avt_linter.py`, `pytest.ini` oraz `rules.py`.

---

## FAZA 0 — CZYTANIE KODU I WERYFIKACJA STANU (OBOWIĄZKOWA PRZED EDYCJĄ)

Przed wykonaniem edycji uruchom poniższe 7 komend diagnostycznych i wklej ich surowe wyjścia w Sekcji 0 raportu `Artefakty/Raport_wdrozenia_10.6.1.md`:

~~~bash
# 1. Weryfikacja HEAD i czystości drzewa
git log --oneline -n 5
git status

# 2. Inspekcja populate_secondary_actor_tags w series_memory.py
grep -nA 55 "def populate_secondary_actor_tags" series_memory.py

# 3. Inspekcja _sanitize_loaded_bible_in_ram w series_memory.py
grep -nA 75 "def _sanitize_loaded_bible_in_ram" series_memory.py

# 4. Inspekcja resolve_character_record w series_memory.py
grep -nA 55 "def resolve_character_record" series_memory.py

# 5. Inspekcja apply_canonical_alias_declension w series_memory.py
grep -nA 110 "def apply_canonical_alias_declension" series_memory.py

# 6. Sprawdzenie wywołania apply_canonical_alias_declension w translator.py
grep -nC 15 "apply_canonical_alias_declension" translator.py

# 7. Sygnatura konstruktora SeriesMemoryManager (kluczowe dla testów T10.6.1_*)
grep -nA 15 "def __init__" series_memory.py
~~~

### P0.1. Odpowiedzi na pytania flagowe (na podstawie powyższych komend)

- **F0.1:** Hash HEAD = `60bfa9d` (potwierdź `git log -n 1 --format=%H`).
- **F0.2:** `apply_canonical_alias_declension` iteruje po `self.data["characters"]` w kolejności wstawienia kluczy do JSON. **Brak sortowania** faworyzującego encje pełne. **Brak filtrowania sufiksów `CamelCase`** i `"Postać epizodyczna / tło"`.
- **F0.3:** Wywołanie w `translator.py` (post-processing po Fazie 2, przed `AVTLinter.lint_and_fix_line`), przekazuje `text`, `source_en`, `keep_honorifics`.
- **F0.4:** `populate_secondary_actor_tags` traktuje tagi typu `<Imię>Soul` / `<Imię>like` jako osobne postacie `ANTHROPONYM`, bez scalania z encją bazową.
- **F0.5:** `_sanitize_loaded_bible_in_ram` obsługuje deduplikację `P0-vs-P2`, ale **nie obsługuje kolizji `P0-vs-P0`** przy współdzielonym krótkim aliasie.
- **F0.6:** `resolve_character_record` zwraca **pierwszy napotkany** wynik (nie sortuje kandydatów deterministycznie).
- **F0.7 (nowe):** **Sygnatura `SeriesMemoryManager.__init__`** odczytana z Komendy 7. Zapisz ją dosłownie w raporcie (nazwy parametrów, czy `memory_dir` / `bible_dir` / `base_dir`, czy przyjmuje `Path` czy `str`). **Kluczowe:** w testach `T10.6.1_1` – `T10.6.1_4` (SEKCJA 2) wywołanie konstruktora `SeriesMemoryManager(...)` musi odpowiadać dokładnie tej sygnaturze. Jeśli parametr nazywa się `bible_dir` zamiast `memory_dir`, użyj `bible_dir`. Jeśli przyjmuje `Path`, użyj `Path(tmp_path)`.

---

## SEKCJA 1 — OPERACJE IMPLEMENTACYJNE (`2B.1` – `2B.3` W `series_memory.py`)

### Operacja `2B.1` — Normalizacja technicznych sufiksów stanu/formy w `populate_secondary_actor_tags` (`FIX-A.1a`)

**Problem:** W skryptach `.ass` twórcy napisów często oznaczają warianty stanu postaci (np. ulatującą duszę, głos wewnętrzny, sobowtóra) poprzez doklejenie angielskiego przyrostka w `CamelCase` (np. `<Imię>Soul`, `<Imię>Spirit`, `<Imię>Ghost`, `<Imię>Voice`, `<Imię>Mind`, `<Imię>Shadow`, `<Imię>Clone`, `<Imię>like`, `<Imię>Mild`). Obecnie `populate_secondary_actor_tags` traktuje taki tag jako zupełnie nową postać, a po przypisaniu jej skróconego aliasu `<Imię>` powstaje duplikat kolidujący z właściwą postacią główną.

**Instrukcja:**
1. W `series_memory.py` zdefiniuj stałą krotkę technicznych przyrostków stanu aktora ASS:
   ~~~python
   _ACTOR_VARIANT_SUFFIXES = (
       "Soul", "Spirit", "Ghost", "Voice", "Mind", "Shadow", "Echo", "Clone",
       "Projection", "Illusion", "Form", "Mode", "like", "Mild",
   )
   ~~~
2. W `populate_secondary_actor_tags` (oraz w pomocniczej funkcji czyszczącej nazwę aktora ASS):
   - Jeśli surowy tag aktora pasuje do wzorca `^([A-Z][a-z]{2,})(Soul|Spirit|Ghost|Voice|Mind|Shadow|Echo|Clone|Projection|Illusion|Form|Mode|like|Mild)$` (rdzeń o długości co najmniej 3 znaków zaczynający się wielką literą + jeden z sufiksów):
   - Wyodrębnij rdzeń bazowy `base_stem = match.group(1)`.
   - Jeśli `base_stem` rozwiązuje się przez `self.resolve_character_record(base_stem)` do istniejącej postaci w `self.data["characters"]` **LUB** jeśli `base_stem` występuje wśród pozostałych czystych tagów aktorów w `actor_mappings`:
   - **Nie twórz osobnego rekordu postaci dla wariantu z sufiksem.** Alternatywnie dopisz pełny tag z sufiksem wyłącznie jako drugorzędny alias techniczny do istniejącego rekordu bazowego (bez tworzenia osobnego klucza w `characters` i `declensions`).

---

### Operacja `2B.2` — Deduplikacja kolizji aliasów `P0-vs-P0` w `_sanitize_loaded_bible_in_ram` i deterministyczny ranking w `resolve_character_record` (`FIX-A.1b`)

**Problem:** W już zapisanych plikach `*_bible.json` (lub w pamięci RAM po scaleniu danych z Profilera) mogą istnieć jednocześnie dwa wpisy `P0`: techniczny wpis jednowyrazowy z opisem `"Postać epizodyczna / tło"` (lub sufiksem z `_ACTOR_VARIANT_SUFFIXES`) oraz właściwy wpis pełnej postaci (np. dwuczłonowe imię i nazwisko).

**Instrukcja:**
1. W `_sanitize_loaded_bible_in_ram` (`series_memory.py`) dodaj krok rozwiązywania kolizji pomiędzy wpisami w `self.data["characters"]`:
   - Jeśli klucz `char_key` w `characters` pasuje do wzorca `^([A-Z][a-z]{2,})(Soul|Spirit|Ghost|Voice|Mind|Shadow|Echo|Clone|Projection|Illusion|Form|Mode)$`, a w `characters` istnieje inna encja (np. pełne imię i nazwisko `P0`), która posiada `base_stem` jako pierwszy człon nazwy lub alias:
   - Usuń `base_stem` z listy `aliases` encji wariantowej (`char_key`) i obniż jej `priority` do `"P2"` (lub scal ją z encją bazową i usuń jej nadmiarowy wpis z `declensions`), tak aby jednowyrazowy alias `base_stem` należał wyłącznie do właściwej postaci bazowej.
2. W `resolve_character_record` (oraz przy budowaniu mapy aliasów w `apply_canonical_alias_declension`), gdy więcej niż jedna encja o tym samym priorytecie (`P0`) pasuje do szukanego aliasu, zastosuj **deterministyczny klucz sortowania faworyzujący właściwą postać główną**:
   - Wyższy priorytet ma encja, której `description` **nie** zawiera `"Postać epizodyczna / tło"`.
   - Wyższy priorytet ma encja, której klucz główny **nie** kończy się sufiksem z `_ACTOR_VARIANT_SUFFIXES`.
   - Wyższy priorytet ma encja posiadająca pełne imię i nazwisko (spację w kluczu głównym, np. `"Imię Nazwisko"`), przed jednowyrazowym kluczem technicznym `CamelCase`.

---

### Operacja `2B.3` — Zasada `Single-Token Scope Parity` i ochrona przed rozszerzaniem pojedynczego członu w `apply_canonical_alias_declension` (`FIX-A.2`)

**Problem:** Gdy w dialogu pada wyłącznie pojedynczy człon nazwy własnej (np. samo imię `"Jestem <Imię>, trzecia księżniczka"` albo nazwa królestwa/akademii `"relacje z <Nazwa>em"`, która przypadkowo pokrywa się z nazwiskiem jednej z postaci `"<Imię> <Nazwa>"`), `apply_canonical_alias_declension`:
1. W pierwszym przypadku podmienia `"<Imię>"` na techniczny klucz `"<Imię>Soul"`, nawet wewnątrz pełnego imienia i nazwiska (`"Oto ja, <Imię> <Nazwisko>"` → `"Oto ja, <Imię>Soul <Nazwisko>"`).
2. W drugim przypadku podmienia jednowyrazowe `"z <Nazwa>em"` (`EN: "relations with <Nazwa>"`) na dwuczłonowe imię i nazwisko postaci `"z <Imię_N> <Nazwa>"`.

**Instrukcja:**
W metodzie `apply_canonical_alias_declension` (`series_memory.py`) wprowadź trzy twarde zabezpieczenia zgodne z Z3:

1. **Zakaz ekspansji liczby słów i długości rdzenia (`Single-Token Scope Parity`):**
   - Jeśli dopasowany w tekście token jest **jednowyrazowy** (`matched_word`), a docelowa forma z paradygmatu `declensions` składa się z **wielu wyrazów** (zawiera spację, np. `"<Imię> <Nazwisko>"`):
   - Jeżeli w `source_en` występuje wyłącznie ten pojedynczy człon (a nie pełne imię i nazwisko), **NIE rozszerzaj** pojedynczego wyrazu do pełnego imienia i nazwiska! Zamiast tego użyj wyłącznie odpowiedniego pojedynczego członu z paradygmatu (np. pierwszego członu dla imienia, drugiego członu dla nazwiska), **pod warunkiem**, że sam ten człon nie jest topograficzną nazwą miejsca/kraju poprzedzoną w `source_en` frazą relacyjną/przestrzenną (`in <Token>`, `from <Token>`, `to <Token>`, `relations with <Token>`, `kingdom of <Token>`, `academy of <Token>`). Gdy w `source_en` jednowyrazowy człon pełni funkcję toponimu/instytucji lub jest drugim członem (nazwiskiem) użytym po przyimku w znaczeniu kraju/akademii — **pomiń podmianę** i zachowaj tekst z LLM.

2. **Zakaz podmiany prostego imienia na dłuższy identyfikator `CamelCase`:**
   - Jeśli dopasowany w tekście token (lub alias w `source_en`) to proste jednowyrazowe imię (`^[A-Z][a-z]+$`), a kandydat docelowy z `declensions` jest dłuższym identyfikatorem `CamelCase` (posiada wewnątrz wielką literę, np. `r"[a-z][A-Z]"` jak `<Imię>Soul`) — **całkowicie zablokuj taką podmianę**.

3. **Ochrona pełnego antroponimu wieloczłonowego (*Multi-Token Anthroponym Immunity*):**
   - Jeśli po dopasowanym w tekście imieniu `matched_word` bezpośrednio następuje drugi człon zaczynający się wielką literą należący do tej samej postaci (np. nazwisko z listy `aliases` lub klucza postaci), nie wykonuj podmiany izolowanego pierwszego członu na inny klucz.

---

## SEKCJA 2 — WALIDACJA TESTOWA (`tests/test_series_memory.py`)

Dopisz na końcu `tests/test_series_memory.py` **4 testy jednostkowe** (`T10.6.1_1` – `T10.6.1_4`) używające wyłącznie syntetycznych danych testowych (100% Zero-Literal).

**UWAGA:** Poniższe ciała testów zakładają, że konstruktor `SeriesMemoryManager` przyjmuje `memory_dir` jako keyword. **Odczytaj rzeczywistą sygnaturę z Fazy 0 (Komenda 7) i dostosuj wywołanie** — jeśli parametr nazywa się `bible_dir`, `base_dir` lub jest pozycyjny, użyj odpowiedniej nazwy/pozycji. Jeśli przyjmuje `Path`, użyj `Path(tmp_path)`. **Asercje merytoryczne pozostają identyczne.**

~~~python
import pytest
from pathlib import Path


@pytest.mark.unit
def test_t10_6_1_1_variant_actor_suffix_soul_does_not_hijack_base_character(tmp_path):
    """
    Standard 10.6.1 (FIX-A.1): Weryfikuje, że techniczny tag aktora z sufiksem stanu
    (np. HeroineSoul) nie przejmuje krótkiego aliasu ('Heroine') od głównej postaci P0
    ('Heroine Royalhouse').
    """
    from series_memory import SeriesMemoryManager

    sm = SeriesMemoryManager("test_series_10_6_1_1", memory_dir=str(tmp_path))
    sm.data["characters"] = {
        "HeroineSoul": {
            "description": "Postać epizodyczna / tło",
            "gender": "FEMALE",
            "grammatical_gender": "FEMININE",
            "has_verified_gender": True,
            "confidence": 0.95,
            "priority": "P0",
            "aliases": ["Heroine", "HeroineSoul"],
            "entity_category": "ANTHROPONYM",
        },
        "Heroine Royalhouse": {
            "name": "Heroine Royalhouse",
            "description": "KOBIETA (wyodrębniono z relacji serii)",
            "gender": "FEMALE",
            "grammatical_gender": "FEMININE",
            "has_verified_gender": True,
            "confidence": 0.95,
            "priority": "P0",
            "aliases": ["Royalhouse", "Heroine", "Heroine Royalhouse"],
            "entity_category": "ANTHROPONYM",
        },
    }
    sm.data["declensions"] = {
        "HeroineSoul": {k: "HeroineSoul" for k in ("M", "D", "C", "B", "N", "Ms", "W")},
        "Heroine Royalhouse": {k: "Heroine Royalhouse" for k in ("M", "D", "C", "B", "N", "Ms", "W")},
    }
    sm._sanitize_loaded_bible_in_ram()

    rec = sm.resolve_character_record("Heroine")
    assert rec is not None
    assert rec.get("name") == "Heroine Royalhouse" or "Royalhouse" in rec.get("aliases", [])


@pytest.mark.unit
def test_t10_6_1_2_populate_secondary_actor_tags_strips_soul_suffix(tmp_path):
    """
    Standard 10.6.1 (FIX-A.1a): Weryfikuje, że populate_secondary_actor_tags nie tworzy
    osobnej encji P0 dla tagu 'PrincessAlphaSoul', gdy istnieje 'PrincessAlpha Royal'.
    """
    from series_memory import SeriesMemoryManager

    sm = SeriesMemoryManager("test_series_10_6_1_2", memory_dir=str(tmp_path))
    sm.data["characters"] = {
        "PrincessAlpha Royal": {
            "name": "PrincessAlpha Royal",
            "gender": "FEMALE",
            "grammatical_gender": "FEMININE",
            "priority": "P0",
            "has_verified_gender": True,
            "aliases": ["PrincessAlpha", "PrincessAlpha Royal"],
            "entity_category": "ANTHROPONYM",
        }
    }
    actor_mappings = {
        "PrincessAlpha": {"clean_name": "PrincessAlpha", "extracted_gender": None},
        "PrincessAlphaSoul": {"clean_name": "PrincessAlphaSoul", "extracted_gender": None},
    }
    sm.populate_secondary_actor_tags(actor_mappings)
    assert "PrincessAlphaSoul" not in sm.data["characters"]


@pytest.mark.unit
@pytest.mark.parametrize(
    "pl_in,en_in,expected_pl",
    [
        (
            "Jestem Heroine, trzecia księżniczka.",
            "I'm Heroine, the third princess.",
            "Jestem Heroine, trzecia księżniczka.",
        ),
        (
            "Księżniczko Heroine, to nie przystoi.",
            "Princess Heroine, that expression is unbecoming.",
            "Księżniczko Heroine, to nie przystoi.",
        ),
        (
            "Oto ja, Heroine Royalhouse, urocza starsza siostra!",
            "I am Heroine Royalhouse, adorable older sister.",
            "Oto ja, Heroine Royalhouse, urocza starsza siostra!",
        ),
    ],
)
def test_t10_6_1_3_apply_canonical_alias_declension_never_injects_camel_case_soul(
    tmp_path, pl_in, en_in, expected_pl
):
    """
    Standard 10.6.1 (FIX-A.2): Weryfikuje, że apply_canonical_alias_declension nigdy nie
    podmienia imienia 'Heroine' na techniczny klucz 'HeroineSoul'.
    """
    from series_memory import SeriesMemoryManager

    sm = SeriesMemoryManager("test_series_10_6_1_3", memory_dir=str(tmp_path))
    sm.data["characters"] = {
        "HeroineSoul": {
            "description": "Postać epizodyczna / tło",
            "gender": "FEMALE",
            "grammatical_gender": "FEMININE",
            "has_verified_gender": True,
            "confidence": 0.95,
            "priority": "P0",
            "aliases": ["Heroine", "HeroineSoul"],
            "entity_category": "ANTHROPONYM",
        },
        "Heroine Royalhouse": {
            "name": "Heroine Royalhouse",
            "description": "KOBIETA",
            "gender": "FEMALE",
            "grammatical_gender": "FEMININE",
            "has_verified_gender": True,
            "confidence": 0.95,
            "priority": "P0",
            "aliases": ["Royalhouse", "Heroine", "Heroine Royalhouse"],
            "entity_category": "ANTHROPONYM",
        },
    }
    sm.data["declensions"] = {
        "HeroineSoul": {k: "HeroineSoul" for k in ("M", "D", "C", "B", "N", "Ms", "W")},
        "Heroine Royalhouse": {k: "Heroine Royalhouse" for k in ("M", "D", "C", "B", "N", "Ms", "W")},
    }
    sm._sanitize_loaded_bible_in_ram()

    out_pl, fixes = sm.apply_canonical_alias_declension(pl_in, source_en=en_in, keep_honorifics=False)
    assert out_pl == expected_pl
    assert "HeroineSoul" not in out_pl


@pytest.mark.unit
def test_t10_6_1_4_single_token_surname_toponym_not_expanded_to_full_person_name(tmp_path):
    """
    Standard 10.6.1 (FIX-A.2): Weryfikuje, że jednowyrazowa nazwa własna w narzędniku
    ('przyjazne relacje z Kingdomem', EN: 'friendly relations with Kingdom') nie zostaje
    rozszerzona do pełnego imienia i nazwiska postaci ('z Lady Kingdom') posiadającej
    alias 'Kingdom'.

    Dane testowe są w 100% syntetyczne (rdzeń 'Kingdom' oznacza tu fikcyjne państwo/
    akademię; 'Lady Kingdom' to fikcyjna postać używająca tego samego członu jako
    nazwiska). Forma narzędnika 'Kingdomem' jest celowo niepoprawna fleksyjnie i służy
    wyłącznie jako wejście do testowanego modułu.
    """
    from series_memory import SeriesMemoryManager

    sm = SeriesMemoryManager("test_series_10_6_1_4", memory_dir=str(tmp_path))
    sm.data["characters"] = {
        "Lady Kingdom": {
            "name": "Lady Kingdom",
            "gender": "FEMALE",
            "grammatical_gender": "FEMININE",
            "has_verified_gender": True,
            "confidence": 1.0,
            "priority": "P0",
            "aliases": ["Kingdom", "Lady", "Lady Kingdom"],
            "entity_category": "ANTHROPONYM",
        }
    }
    sm.data["declensions"] = {
        "Lady Kingdom": {
            "M": "Lady Kingdom",
            "D": "Lady Kingdom",
            "C": "Lady Kingdom",
            "B": "Lady Kingdom",
            "N": "Lady Kingdom",
            "Ms": "Lady Kingdom",
            "W": "Lady Kingdom",
            "gender": "FEMALE",
        }
    }

    pl_in = "To święto ma zacieśnić przyjazne relacje z Kingdomem,"
    en_in = "This event is also supposed to deepen friendly relations with Kingdom,"
    out_pl, _ = sm.apply_canonical_alias_declension(pl_in, source_en=en_in, keep_honorifics=False)
    assert out_pl == pl_in
~~~

---

## SEKCJA 3 — WALIDACJA BRAMEK CI/CD I Z16

Po wdrożeniu operacji `2B.1`–`2B.3` oraz testów `T10.6.1_1`–`T10.6.1_4` uruchom:

1. **Testy jednostkowe:**
   - `pytest tests/test_series_memory.py -q` → wszystkie przechodzą (`+6` nowych przypadków z parametryzacją)
   - `pytest tests/ -q` → `287+ passed, 0 failed`
   - `pytest -q` → `358+ passed, 153 deselected, 0 failed`

2. **4 Bramki CI/CD:**
   - `python verify_purity.py` → `12/12 PASS`
   - `python verify_8_fixes.py` → `8/8 PASS`
   - `python verify_12_fixes.py` → `12/12 PASS`
   - `python verify_ultimate_pipeline.py` → `15/15 PASS`

3. **Weryfikacja Z16:**
   ~~~bash
   git diff 60bfa9d..HEAD -- test_system.py tests/archive/ avt_linter.py pytest.ini rules.py
   # Wyjście musi być w 100% puste (0 B)
   ~~~

---

## SEKCJA 4 — WARUNKI UKOŃCZENIA `(a)`–`(h)`

- **(a)** Wykonano 7 komend diagnostycznych z Fazy 0 i wklejono ich wyjścia w `Artefakty/Raport_wdrozenia_10.6.1.md`.
- **(b)** Wdrożono `2B.1` (`_ACTOR_VARIANT_SUFFIXES` w `populate_secondary_actor_tags`).
- **(c)** Wdrożono `2B.2` (deduplikacja P0-vs-P0 w `_sanitize_loaded_bible_in_ram` i ranking w `resolve_character_record`).
- **(d)** Wdrożono `2B.3` (`Single-Token Scope Parity` i blokada ekspansji `CamelCase` w `apply_canonical_alias_declension`).
- **(e)** Dodano testy `T10.6.1_1`–`T10.6.1_4` w `tests/test_series_memory.py` (100% Zero-Literal) i wszystkie przechodzą.
- **(f)** Wszystkie 4 bramki CI/CD oraz suity `pytest` przechodzą (`0 failed`), Z16 w 100% nienaruszone.
- **(g)** Zapisano raport `Artefakty/Raport_wdrozenia_10.6.1.md` (`0` placeholderów).
- **(h)** Wykonano **dokładnie 1 commit** i **1 push** na `origin/main`:
  `fix(series_memory): Hotfix 10.6.1 - prevent variant actor tag hijacking and single-token alias expansion`
  Po pushu **zatrzymaj się** — kolejny krok (Prompt 10.6.2) jest uruchamiany jako osobny hotfix.

---

## SEKCJA 5 — ZAKAZY I KNOWN RISKS

1. **ZAKAZ 1 (Z16):** Nie dotykaj `test_system.py`, `tests/archive/`, `avt_linter.py`, `pytest.ini`, `rules.py`.
2. **ZAKAZ 2 (Z1 Zero-Literal):** W kodzie `series_memory.py`, `tests/test_series_memory.py` oraz w raporcie nie używaj żadnych nazw własnych z anime.
3. **ZAKAZ 3 (Wąski zakres):** Modyfikuj wyłącznie `series_memory.py`, `tests/test_series_memory.py` oraz dodaj `Artefakty/Raport_wdrozenia_10.6.1.md` (i opcjonalnie `Artefakty/Prompt_10.6.1.md`).
4. **ZAKAZ 4 (Brak łączenia z 10.6.2):** Nie implementuj w tym prompcie żadnych zmian w `verifier.py`. Hotfix 10.6.2 jest osobnym, kolejnym zadaniem.
5. **KNOWN RISK `R1`:** Istniejące testy w `tests/test_series_memory.py` oraz `test_system.py` testują `apply_canonical_alias_declension` dla odmiany pojedynczych imion (np. zmiana błędnego przypadka lub utrzymanie nieodmiennego aliasu). Upewnij się, że odmiana tego samego pojedynczego słowa (1 token → 1 token o tym samym rdzeniu bez `CamelCase`) nadal działa dokładnie tak jak dotychczas.
6. **KNOWN RISK `R2`:** Jeżeli w `series_memory/*_bible.json` (20 plików jiż zapisanych na dysku) znajdują się już duplikaty P0-vs-P0 z sufiksem (`*Soul`, `*like`, itp.), `_sanitize_loaded_bible_in_ram` zacznie je usuwać przy pierwszym odczycie. **Nie modyfikuj plików `series_memory/*_bible.json` ręcznie** — sanitacja dzieje się w RAM i zapis następuje automatycznie przez `save()`.

**Koniec promptu wykonawczego 10.6.1.**