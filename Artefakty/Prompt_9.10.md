# Plik: C:\Users\Piotrek\Desktop\translator\Artefakty\Prompt_9.10.md

# PROMPT NAPRAWCZY POTOKU AVT — WERSJA 9.10 (GENERALIZACJA MIĘDZYSERYJNA: OCHRONA STRUKTURALNEGO P0_GENDER, HIGIENA ONOMASTYCZNA SERIESBIBLE, PARADYGMATY GLOSARIUSZA I CIĄGŁOŚĆ WIELOKROPKA W RUNTIME)

## PREAMBUŁA

Dokument definiuje operacje kodowe, regułowe i walidacyjne rozszerzające potok AVT z wersji **9.9** (commit `716aa0f`) do wersji **9.10** oraz utrzymujące w 100% stan po Depuracji Legacy 1.0 (commit `474fb64`).
Podstawa empiryczna i architektoniczna: audyt generalizacji międzyseryjnej (Etap 1/2 i Etap 2/2) przeprowadzony na nowym odcinku nowej serii, który potwierdził pełną generalizację 5 z 9 kategorii (ochrony `is_sign`, filtracji ASR, higieny kursywy i `\N`, sanitacji pseudotagów ASS oraz logowania Fazy 2 / Kroku 11), a jednocześnie zidentyfikował **4 zagadnienia wymagające uogólnienia architektonicznego**:
1. **Operacja 2B.1 (`metadata.py`, `series_memory.py`, `translator.py`):** Ochrona strukturalnego pola `gender` w `get_anime_context` (wyeliminowanie domyślnego przypisywania `"mężczyzna"` przy neutralnym opisie `"postać (Postać drugoplanowa)"`), dziedziczenie płci przez jednoczłonowe aliasy z dwuczłonowych rekordów P0 (`<IMIE>` z `<IMIE> <NAZWISKO>`) oraz nienaruszalność płci `FEMALE` dla imion i ról z `INHERENT_FEMALE_NOUNS`, `POLISH_FEMALE_NAMES`, `UNIVERSAL_FEMALE_NAMES_ON_A` i `FOREIGN_FEMALE_CONSONANT_NAMES`.
2. **Operacja 2B.2 (`metadata.py`, `series_memory.py`, `translator.py`):** Filtracja ontologiczna etykiet nieosobowych, zbiorowych i adnotowanych z kolumny `Name` (`Both`, `All`, wyrazy małoliterowe, sufiksy `?` oraz `Heart`) przed zapisem do `characters` i `declensions`, dodanie sufiksów `-ny/-na/-ne` do `is_polish_adjective` oraz blokada generowania paradygmatów męskożywotnych dla wielowyrazowych terminów apelatywnych i dopełniaczy l.mn. na `-ów` w glosariuszu.
3. **Operacja 2B.3 (`translator.py`, `verifier.py`):** Przekazywanie `prev_line_f1` i `prev_line_en` w słownikach `pass1_items` oraz w pętli `DialogueVerifier.verify_batch` w celu pełnej aktywacji Kategorii 12, 13 i 17 (`ellipsis_continuation_syntax`) w runtime.
4. **Operacja 2B.4 (`pytest.ini`, bramki CI/CD):** Dodanie katalogu `Artefakty` do `norecursedirs` w `pytest.ini` (eliminacja błędów kolekcji na archiwalnych paczkach audytowych) oraz pełne uzgodnienie bramek CI/CD.

Numer wersji: **9.10**. Poprzednia wersja: **9.9** (commit `716aa0f`). Wersja Depuracji Legacy w tle: **1.0** (commit `474fb64`).

---

## FAZA 0 — CZYTANIE KODU (OBOWIĄZKOWA)

### P0.1. Lista plików do przeczytania przed modyfikacją
1. `metadata.py` — linie `25-68` (`normalize_actor_tag`) oraz linie `405-465` (`get_anime_context`).
2. `series_memory.py` — linie `499-955` (słowniki ról i imion, `is_polish_adjective`, `generate_polish_name_declension`), linie `1340-1780` (`_sanitize_bible_integrity`, `_sanitize_loaded_bible_in_ram`, `populate_secondary_actor_tags`, `assimilate_quality_gate_invariants`).
3. `translator.py` — linie `1395-1460` (`pass1_items` w `_process_single_batch`), linie `1705-1750` (reset bufora deduplikacji ASR), linie `2580-2615` (`actor_map` i generowanie `declensions`).
4. `verifier.py` — linie `840-895` (`verify_batch` i wywołanie `_guard_phase2_regressions`).
5. `pytest.ini` — linie `1-9` (`norecursedirs`).

### P0.2. Tabela mapowania plan ↔ kod (do wypełnienia w `Raport_wdrozenia_9.10.md`)

| Operacja (sekcja 9.10) | Miejsce wywołania / metoda w planie | Rzeczywiste miejsce wywołania w kodzie (plik + linia + metoda) | Rzeczywista sygnatura w kodzie | Zgodność | Uwagi / Rozstrzygnięcie |
|---|---|---|---|---|---|
| 2B.1 | Odczyt strukturalnego `gender` w `get_anime_context` (`metadata.py`) oraz dziedziczenie płci jednoczłonowych aliasów P0 i ochrona ról/imion żeńskich (`series_memory.py`, `translator.py`) | `<DO_WYPEŁNIENIA_PRZEZ_AGENTA_KODUJĄCEGO>` | `<DO_WYPEŁNIENIA_PRZEZ_AGENTA_KODUJĄCEGO>` | `<DO_WYPEŁNIENIA_PRZEZ_AGENTA_KODUJĄCEGO>` | `<DO_WYPEŁNIENIA_PRZEZ_AGENTA_KODUJĄCEGO>` |
| 2B.2 | Filtracja etykiet zbiorowych/małoliterowych/adnotowanych (`metadata.py`, `series_memory.py`) oraz ochrona przymiotników na `-ny` i dopełniaczy l.mn. na `-ów` w `generate_polish_name_declension` | `<DO_WYPEŁNIENIA_PRZEZ_AGENTA_KODUJĄCEGO>` | `<DO_WYPEŁNIENIA_PRZEZ_AGENTA_KODUJĄCEGO>` | `<DO_WYPEŁNIENIA_PRZEZ_AGENTA_KODUJĄCEGO>` | `<DO_WYPEŁNIENIA_PRZEZ_AGENTA_KODUJĄCEGO>` |
| 2B.3 | Podłączenie `prev_line_f1` i `prev_line_en` w `pass1_items` (`translator.py`) i `verify_batch` (`verifier.py`) | `<DO_WYPEŁNIENIA_PRZEZ_AGENTA_KODUJĄCEGO>` | `<DO_WYPEŁNIENIA_PRZEZ_AGENTA_KODUJĄCEGO>` | `<DO_WYPEŁNIENIA_PRZEZ_AGENTA_KODUJĄCEGO>` | `<DO_WYPEŁNIENIA_PRZEZ_AGENTA_KODUJĄCEGO>` |
| 2B.4 | Wykluczenie `Artefakty` w `pytest.ini` (`norecursedirs`) | `<DO_WYPEŁNIENIA_PRZEZ_AGENTA_KODUJĄCEGO>` | `<DO_WYPEŁNIENIA_PRZEZ_AGENTA_KODUJĄCEGO>` | `<DO_WYPEŁNIENIA_PRZEZ_AGENTA_KODUJĄCEGO>` | `<DO_WYPEŁNIENIA_PRZEZ_AGENTA_KODUJĄCEGO>` |

### P0.3. Tabela mapowania danych testowych (do wypełnienia w `Raport_wdrozenia_9.10.md`)

| Placeholder | Wartość rzeczywista (spoza odcinka audytowanego) | Źródło (P0 / EN / ASS) | Uwagi |
|---|---|---|---|
| `<RZECZYWISTY_ANTROPONIM_ŻEŃSKI_DWUCZŁONOWY_1>` | `<DO_WYPEŁNIENIA_MAPOWANIE_P0_3>` | P0 (`SeriesBible`) | Dwuczłonowa postać żeńska z imieniem na spółgłoskę |
| `<RZECZYWISTY_CZŁON_IMIENNY_ŻEŃSKI_SPÓŁGŁOSKOWY_1>` | `<DO_WYPEŁNIENIA_MAPOWANIE_P0_3>` | `[Events]` | Pierwszy człon imienia żeńskiego na spółgłoskę |
| `<RZECZYWISTA_ROLA_ŻEŃSKA_1>` | `<DO_WYPEŁNIENIA_MAPOWANIE_P0_3>` | `[Events]` | Rola żeńska z `INHERENT_FEMALE_NOUNS` |
| `<RZECZYWISTA_ETYKIETA_ZBIOROWA_1>` | `<DO_WYPEŁNIENIA_MAPOWANIE_P0_3>` | `[Events]` | Etykieta zbiorowa wieloosobowa |
| `<RZECZYWISTA_ETYKIETA_MAŁOLITEROWA_1>` | `<DO_WYPEŁNIENIA_MAPOWANIE_P0_3>` | `[Events]` | Wyraz pospolity pisany małą literą |
| `<RZECZYWISTY_TERMIN_LICZEBNIKOWY_1>` | `<DO_WYPEŁNIENIA_MAPOWANIE_P0_3>` | Glosariusz | Fraza z liczebnikiem i dopełniaczem l.mn. na `-ów` |
| `<RZECZYWISTY_TERMIN_PRZYMIOTNIKOWY_1>` | `<DO_WYPEŁNIENIA_MAPOWANIE_P0_3>` | Glosariusz | Rzeczownik + przymiotnik na `-ny` |

---

## SEKCJA 1: REGUŁY DLA MODELI LLM (Faza 1 i Faza 2)

Wszystkie reguły `R1.1–R1.11` z wersji 9.7–9.9 pozostają utrzymane w czystej formie pozytywnej.

---

## SEKCJA 2: OPERACJE (2A / 2B / 2C)

### 2A — Operacje potwierdzone z wersji 9.7–9.9 (bez nowych akcji)
1. **`2A.1` (z 9.9/2B.1):** Nieinteraktywne rozwiązywanie CLI `resolve_cli_inputs_and_honorifics` w `main.py` — potwierdzone.
2. **`2A.2` (z 9.4–9.8):** Ochrona `is_sign` przed dzieleniem, sanitacja bufora ASR, higiena kursywy i `\N`, czyszczenie pseudotagów ASS oraz blokada pustych wpisów `[Redaktor Dialogów]` dla `\N` vs spacja — potwierdzone na nowym odcinku.

### 2B — Nowe operacje uogólniające

#### OPERACJA 2B.1 — Ochrona strukturalnego `p0_gender` w `metadata.py` oraz dziedziczenie płci jednoczłonowych aliasów z rekordów dwuczłonowych P0 (`metadata.py` + `series_memory.py` + `translator.py`)
- **Implementacja:**
  1. W `metadata.py` (`get_anime_context`, linie 432–448): podczas budowania `characters_list` z lokalnego `SeriesBible` odczytaj w pierwszej kolejności pole strukturalne `raw_g = str(c_val.get("gender") or "").upper() if isinstance(c_val, dict) else ""`. Jeśli `raw_g == "FEMALE"`, ustaw `gender_str = "kobieta"`, `gender_raw = "FEMALE"`; jeśli `raw_g == "MALE"`, ustaw `gender_str = "mężczyzna"`, `gender_raw = "MALE"`; jeśli `raw_g in ("UNKNOWN", "")` i opis nie zawiera jawnych słów kluczowych płci, zachowaj `gender_str = None` i `gender_raw = None` (nigdy nie przypisuj domyślnie `"mężczyzna"`!).
  2. W `series_memory.py` (`_sanitize_bible_integrity`, `_sanitize_loaded_bible_in_ram`, `resolve_actor_gender`, `get_character_gender`, `assimilate_quality_gate_invariants`) oraz w `translator.py` (budowa `actor_map`, linie 2595–2605):
     - jeśli jednoczłonowa nazwa `clean_name` występuje jako pierwszy człon lub alias istniejącego dwuczłonowego rekordu P0 (`<IMIE> <NAZWISKO>`) o zweryfikowanej płci `FEMALE` lub `MALE`, bezwarunkowo dziedziczy płeć tego rekordu P0 (`FEMALE` $\rightarrow$ nieodmienny paradygmat dla imienia żeńskiego na spółgłoskę);
     - jeśli nazwa należy do `INHERENT_FEMALE_NOUNS`, `SECONDARY_LEXICAL_FEMALE_NOUNS`, `POLISH_FEMALE_NAMES`, `UNIVERSAL_FEMALE_NAMES_ON_A` lub `FOREIGN_FEMALE_CONSONANT_NAMES` (np. `"Waitress"`, `"Olivia"`, `"Maria"`, `"Bianca"`, `"Mia"`, `"Francoise"`, `"Carol"`, `"Claris"`, `"Helena"`, `"Wanda"`), jej `gender` ma wartość `"FEMALE"` (`FEMININE`) i jest chroniony przed nadpisaniem na `"MALE"`.
- **Kryterium akceptacji:** Prawidłowy stan `SeriesBible` po wczytaniu i aktualizacji odcinka = 100% zachowania `FEMALE` dla wszystkich bohaterek P0/P1 o neutralnym opisie `description`, dla jednoczłonowych imion żeńskich na spółgłoskę oraz dla żeńskich ról z `INHERENT_FEMALE_NOUNS`.

#### OPERACJA 2B.2 — Filtracja ontologiczna etykiet zbiorowych, małoliterowych i adnotowanych oraz higiena deklinacji glosariusza (`metadata.py` + `series_memory.py`)
- **Implementacja:**
  1. W `normalize_actor_tag` (`metadata.py`) usuwaj końcowe znaki zapytania i wykrzykniki (`re.sub(r"[?!]+$", "", clean_name).strip()`) oraz doklejone w CamelCase sufiksy techniczne (`re.sub(r"(?<=[a-z])(?:Heart|Thought|Thoughts|Voice|Internal|Sign)$", "", clean_name)`).
  2. W `is_generic_actor_or_category` i `populate_secondary_actor_tags` (`series_memory.py`) odrzucaj etykiety zbiorowe (`"both"`, `"all"`, `"everyone"`, `"together"`, `"wszyscy"`, `"oboje"`, `"obie"`, `"obaj"`) oraz pojedyncze wyrazy pisane od małej litery (`clean_tag[0].islower()`), wykluczając ich dodawanie do `characters` i `declensions`. W `_sanitize_loaded_bible_in_ram` usuń takie klucze z `characters` i `declensions`.
  3. W `is_polish_adjective` (`series_memory.py:725`) dodaj `"ny", "na", "ne"` do krotki `ADJ_ENDINGS` (przy `len(w) >= 5`), a w `generate_polish_name_declension` zachowaj nieodmienność członów zakończonych na `-ów`, `-om`, `-ami`, `-ach` oraz wyłącz automatyczne generowanie paradygmatów antroponimicznych dla pospolitych haseł glosariusza (`glossary`) niebędących postaciami z `characters`.
- **Kryterium akceptacji:** Prawidłowy stan `characters` i `declensions` w `SeriesBible` = obecność wyłącznie poprawnych antroponimów osobowych (brak `Both`, `All`, `pants`, `Carol?`, `ElisaHeart`) oraz poprawne formy przymiotnikowe i dopełniaczowe (`kod wewnętrzny` $\rightarrow$ D: `<RZECZYWISTY_TERMIN_PRZYMIOTNIKOWY_D_1>`, `Siedmiu Wielkich Magów` $\rightarrow$ bez doklejania `-a/-owi/-em`).

#### OPERACJA 2B.3 — Podłączenie `prev_line_f1` i `prev_line_en` w runtime pomiędzy `translator.py` a `DialogueVerifier` (`translator.py` + `verifier.py`)
- **Implementacja:**
  1. W `translator.py` (`_process_single_batch`, przy budowie `pass1_items`) dodaj do każdego słownika elementu klucze `"prev_line_f1"` oraz `"prev_line_en"` pobierane z poprzedniego elementu paczki `pass1_items[idx - 1]` (lub z `lookback_history[-1]` dla `idx == 0`).
  2. W `verifier.py` (`verify_batch`, linie 860–875) podczas iteracji po `result_lines` dodaj fallback: jeśli `orig_it.get("prev_line_f1")` jest puste, pobierz tekst z poprzedniego elementu `batch_items` (lub `history_context[-1]`).
- **Kryterium akceptacji:** Prawidłowy stan wywołania `_guard_phase2_regressions` podczas `verify_batch` = niepusty parametr `prev_line_f1` / `prev_line_pl` dla każdej linii poprzedzonej inną linią w paczce lub w historii sceny.

#### OPERACJA 2B.4 — Izolacja katalogu `Artefakty` w `pytest.ini` (`pytest.ini`)
- **Implementacja:**
  1. W `pytest.ini` zaktualizuj linię `norecursedirs`:
     ```ini
     norecursedirs = .agents tests/archive .git .venv node_modules Artefakty
     ```
- **Kryterium akceptacji:** Prawidłowy stan kolekcji `pytest` w obecności katalogu `Artefakty/` = `0 errors` podczas kolekcji i 100% PASSED na całym pakiecie testowym.

---

## SEKCJA 3: REGUŁY DLA PIPELINE'U DANYCH

Wszystkie reguły `R3.1–R3.5` zachowują pełną formę pozytywną, z doprecyzowaniem `R3.1`:
- **R3.1 (P0) — Strukturalna Integralność `p0_gender` i Czystość Ontologiczna `SeriesBible`:**
  - **Definicja pozytywna:** Prawidłowy stan `SeriesBible` = zachowanie pola strukturalnego `gender` podczas odczytu w `get_anime_context`, dziedziczenie płci przez jednoczłonowe aliasy z rekordów dwuczłonowych P0, wykluczenie etykiet zbiorowych i małoliterowych z `characters` oraz poprawne paradygmaty przymiotnikowe i liczebnikowe.

---

## SEKCJA 4: KOLEJNOŚĆ WDROŻENIA

1. **ETAP 1:** Wykonanie Phase 0 i wypełnienie Tabel P0.2 i P0.3 w `Raport_wdrozenia_9.10.md`.
2. **ETAP 2:** Wdrożenie Operacji `2B.1` i `2B.2` w `metadata.py`, `series_memory.py` i `translator.py` oraz oczyszczenie `Hyouken_no_Majutsushi_ga_Sekai_wo_Suberu_S2_bible.json` przez `_sanitize_loaded_bible_in_ram`.
3. **ETAP 3:** Wdrożenie Operacji `2B.3` i `2B.4` w `translator.py`, `verifier.py` i `pytest.ini`.
4. **ETAP 4:** Dodanie testów jednostkowych `T10.1–T10.4`, uruchomienie `pytest` (fast + full) oraz bramek CI/CD i wypełnienie `Raport_wdrozenia_9.10.md`.

---

## SEKCJA 5: WALIDACJA TESTOWA I WARUNEK UKOŃCZENIA

### Wykaz nowych testów `T10.1–T10.4` (marker: `unit`)

```python
import pytest

# WZORZEC T10.1 (Operacja 2B.1) -> tests/test_series_memory.py
@pytest.mark.unit
@pytest.mark.parametrize(
    "full_name,short_name,gender,desc,expected_short_gender,expected_genitive",
    [
        (
            "<RZECZYWISTY_ANTROPONIM_ŻEŃSKI_DWUCZŁONOWY_1>",
            "<RZECZYWISTY_CZŁON_IMIENNY_ŻEŃSKI_SPÓŁGŁOSKOWY_1>",
            "FEMALE",
            "postać (Postać drugoplanowa)",
            "FEMALE",
            "<RZECZYWISTY_CZŁON_IMIENNY_ŻEŃSKI_SPÓŁGŁOSKOWY_1>",
        ),
        (
            "<RZECZYWISTA_ROLA_ŻEŃSKA_1>",
            "<RZECZYWISTA_ROLA_ŻEŃSKA_1>",
            "FEMALE",
            "postać drugoplanowa",
            "FEMALE",
            "<RZECZYWISTA_ROLA_ŻEŃSKA_1>",
        ),
    ],
)
def test_structural_gender_preservation_and_short_alias_female_consonant_indeclinability(
    full_name, short_name, gender, desc, expected_short_gender, expected_genitive
):
    from series_memory import SeriesBible, generate_polish_name_declension

    bible = SeriesBible(slug="test_9_10_structural_gender", db_path=":memory:")
    bible.data["characters"][full_name] = {
        "name": full_name,
        "gender": gender,
        "grammatical_gender": "FEMININE",
        "confidence": 0.95,
        "priority": "P0",
        "has_verified_gender": True,
        "aliases": [full_name, short_name],
        "description": desc,
    }
    bible._sanitize_loaded_bible_in_ram()
    assert bible.get_character_gender(full_name) == expected_short_gender
    assert bible.get_character_gender(short_name) == expected_short_gender
    decl = generate_polish_name_declension(short_name, bible.get_character_gender(short_name))
    assert decl["D"] == expected_genitive


# WZORZEC T10.2 (Operacja 2B.2) -> tests/test_series_memory.py
@pytest.mark.unit
@pytest.mark.parametrize(
    "raw_tag,expected_clean,should_be_filtered",
    [
        ("<RZECZYWISTA_ETYKIETA_ZBIOROWA_1>", "<RZECZYWISTA_ETYKIETA_ZBIOROWA_1>", True),
        ("<RZECZYWISTA_ETYKIETA_MAŁOLITEROWA_1>", "<RZECZYWISTA_ETYKIETA_MAŁOLITEROWA_1>", True),
        ("<RZECZYWISTY_CZŁON_IMIENNY_ŻEŃSKI_SPÓŁGŁOSKOWY_1>?", "<RZECZYWISTY_CZŁON_IMIENNY_ŻEŃSKI_SPÓŁGŁOSKOWY_1>", False),
    ],
)
def test_actor_tag_ontological_filtering_strips_punctuation_and_rejects_non_personal_tags(
    raw_tag, expected_clean, should_be_filtered
):
    from metadata import normalize_actor_tag
    from series_memory import SeriesBible

    clean_t, _ = normalize_actor_tag(raw_tag)
    assert clean_t == expected_clean
    bible = SeriesBible(slug="test_9_10_filtering", db_path=":memory:")
    bible.populate_secondary_actor_tags([raw_tag])
    if should_be_filtered:
        assert raw_tag not in bible.data["characters"]
        assert clean_t not in bible.data["characters"]
    else:
        assert clean_t in bible.data["characters"]


# WZORZEC T10.3 (Operacja 2B.2) -> tests/test_series_memory.py
@pytest.mark.unit
@pytest.mark.parametrize(
    "phrase,expected_d,expected_n",
    [
        ("<RZECZYWISTY_TERMIN_LICZEBNIKOWY_1>", "<RZECZYWISTY_TERMIN_LICZEBNIKOWY_1>", "<RZECZYWISTY_TERMIN_LICZEBNIKOWY_1>"),
        ("<RZECZYWISTY_TERMIN_PRZYMIOTNIKOWY_1>", "<RZECZYWISTY_TERMIN_PRZYMIOTNIKOWY_D_1>", "<RZECZYWISTY_TERMIN_PRZYMIOTNIKOWY_N_1>"),
    ],
)
def test_declension_generator_handles_ny_adjectives_and_plural_genitive_phrases(
    phrase, expected_d, expected_n
):
    from series_memory import generate_polish_name_declension

    decl = generate_polish_name_declension(phrase, "MALE")
    assert decl["D"] == expected_d
    assert decl["N"] == expected_n


# WZORZEC T10.4 (Operacja 2B.3) -> tests/test_verifier.py
@pytest.mark.unit
@pytest.mark.parametrize(
    "line1_pl,line2_f1,line2_f2_mutated,expected_line2",
    [
        (
            "<RZECZYWISTY_CIAG_PL_1>...",
            "...<RZECZYWISTY_CIAG_PL_2>.",
            "<RZECZYWISTY_CIAG_PL_2>.",
            "...<RZECZYWISTY_CIAG_PL_2>.",
        ),
        (
            "<RZECZYWISTY_CIAG_PL_2>...",
            "...<RZECZYWISTY_CIAG_PL_1>.",
            "<RZECZYWISTY_CIAG_PL_1>.",
            "...<RZECZYWISTY_CIAG_PL_1>.",
        ),
    ],
)
def test_verify_batch_passes_adjacent_prev_line_to_ellipsis_continuation_guard(
    monkeypatch, line1_pl, line2_f1, line2_f2_mutated, expected_line2
):
    from unittest.mock import MagicMock
    from verifier import DialogueVerifier, RefinedBatchResponse, RefinedLine
    from context_cache import ContextCacheManager

    monkeypatch.setattr(ContextCacheManager, "get_or_create_cache", lambda *a, **kw: "mock_cache")
    mock_pool = MagicMock()
    mock_client = MagicMock()
    mock_pool.get_client.return_value = mock_client
    mock_pool.clients = [mock_client]
    mock_resp = MagicMock()
    mock_resp.text = "{}"
    mock_resp.parsed = RefinedBatchResponse(
        lines=[
            RefinedLine(id=1, refined_pl=line1_pl, changes_made=None),
            RefinedLine(id=2, refined_pl=line2_f2_mutated, changes_made="[Filar I] Korekta"),
        ]
    )
    mock_client.models.generate_content.return_value = mock_resp

    verifier = DialogueVerifier(client=mock_pool)
    batch_items = [
        {"id": 1, "en": "If only we knew...", "pl": line1_pl},
        {"id": 2, "en": "...we would have avoided this ambush.", "pl": line2_f1},
    ]
    res = verifier.verify_batch(batch_items=batch_items)
    assert res[1].refined_pl == expected_line2

### 5A.3. Warunek ukończenia wdrożenia (definicja pozytywna — punkty (a)–(p))

Prawidłowy stan ukończenia wdrożenia 9.10 = jednoczesne spełnienie szesnastu warunków pozytywnych:

- **(a)** Wszystkie operacje z Sekcji 2A (`2A.1–2A.2`) utrzymane w stanie nienaruszonym.
- **(b)** Brak regresji w operacjach wdrożonych w wersjach 9.4–9.9.
- **(c)** Wszystkie operacje z Sekcji 2B (`2B.1–2B.4`) w pełni wdrożone w runtime.
- **(d)** Wszystkie reguły z Sekcji 1 (`R1.1–R1.11`) i Sekcji 3 (`R3.1–R3.5`) zachowane w czystej formie pozytywnej.
- **(e)** Wszystkie 4 nowe testy jednostkowe (`T10.1–T10.4`) zaimplementowane i sparametryzowane (≥ 2 warianty każdy).
- **(f)** `komenda_fast` (`pytest`): 100% PASSED (≥ 216 instancji), `0 FAILED`, `0 ERROR`, czas wykonania < 60 s.
- **(g)** `komenda_full` (`pytest -m ""` lub `pytest -m "slow or not slow"`): 100% PASSED (≥ 369 instancji), `0 FAILED`, `0 ERROR`.
- **(h)** `komenda_slow` (`pytest -m slow`) oraz `komenda_network` (`pytest -m network`): 100% PASSED.
- **(i)** Bramki CI/CD (`verify_purity.py`, `verify_ultimate_pipeline.py`, `verify_12_fixes.py`) zwracają 100% PASS lub FAIL z jawnym uzasadnieniem (patrz 2B.4 + KROK 3A).
- **(j)** `audit_diff.ps1` zwraca status VICTORY CONFIRMED.
- **(k)** Phase 0 ukończona z wypełnionymi tabelami P0.2 i P0.3 w `Raport_wdrozenia_9.10.md`.
- **(l)** Każdy nowy test `T10.1–T10.4` zweryfikowany empirycznie pod kątem falsyfikowalności i wolny od anty-wzorców `D1–D6`.
- **(m)** **Walidacja empiryczna (obowiązkowa):** re-tłumaczenie Hyouken S2-04 potwierdza 5/5 wyeliminowanych kategorii w Sekcji 6C raportu.
- **(n)** Żaden z 212 testów domyślnych (116 `KEEP` + 96 z 9.4–9.9) nie został usunięty ani osłabiony.
- **(o)** Katalog `tests/archive/` oraz 3 gałęzie `# DEFENSIVE_FALLBACK` w `avt_linter.py` nietknięte.
- **(p)** Wszystkie pola `<DO_WYPEŁNIENIA_*>` w `Raport_wdrozenia_9.10.md` wypełnione (0 placeholderów).

## SEKCJA 6: ZAKAZY ARCHITEKTONICZNE (DZIEDZICZONE Z 9.7 + ROZSZERZENIA 9.10)

1. **ZAKAZ 1** (mutacji tekstu poza `AVTLinter` i `EpisodeQualityGate`).
2. **ZAKAZ 2** (podmiany członów antroponimów wieloczłonowych).
3. **ZAKAZ 3** (globalnego dopisywania aliasów tytułowych).
4. **ZAKAZ 4** (Test-Only Wiring i mockowania logiki domenowej w testach).
5. **ZAKAZ 5** (pomijania Phase 0 i walidacji empirycznej).
6. **ZAKAZ 6** (naruszania 212 testów domyślnych i 153 `MARK_SLOW`).
7. **ZAKAZ 7** (modyfikacji `DEFENSIVE_FALLBACK` i `tests/archive/`).
8. **ZAKAZ 8** (pozostawiania placeholderów w raporcie).
9. **ZAKAZ 9** (modyfikacji `.ass`/`.json` — Zero-Cosmetic; wyjątek: `Hyouken_..._bible.json` wymaga regeneracji przez `_sanitize_loaded_bible_in_ram`, nie ręcznej edycji).
10. **ZAKAZ 10** (wycieku Zero-Literal — konkretne wartości w kodzie, testach i `rules.py`).
11. **ZAKAZ 11** (generowania sztucznych `.ass`/`.log` w `Artefakty/` — walidacja empiryczna tylko przez rzeczywiste re-tłumaczenie).
12. **ZAKAZ 12** (manipulacji bramkami `verify_*.py` przez osłabianie asercji — dopuszczalna wyłącznie aktualizacja patternu do aktualnej implementacji, jeśli kod jest poprawny i widać to w diff).

---

**Koniec Prompt_9.10.md.**

