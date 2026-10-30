# Plik: C:\Users\Piotrek\Desktop\translator\Artefakty\Prompt_9.9.md

# PROMPT NAPRAWCZY POTOKU AVT — WERSJA 9.9 (DOMKNIĘCIE ARCHITEKTONICZNE 9.8: SYMETRIA WE_GROUP/YOU_GROUP, LEGALIZACJA NON-TTY CLI I HIGIENA TEST 222)

## PREAMBUŁA

Dokument definiuje mikro-iterację architektoniczną **9.9** domykającą stan po wdrożeniu wersji **9.8** (commit `783dffd`) i utrzymującą w 100% stan Depuracji Legacy 1.0 (commit `474fb64`).
Podstawa empiryczna i architektoniczna:
- **Etap 1/2 audytu 9.8 (weryfikacja empiryczna):** potwierdził pełne wyeliminowanie wszystkich 6 pozycji empirycznych (**6/6 WYELIMINOWANY** w `post98.ass` i `post98_full_trace.log`), w tym `Adresat: <RZECZYWISTA_ETYKIETA_MĘSKA_P1_1> (MASCULINE)` w `ID: 58` oraz wykluczenie `Grupa_1os_lm: NON_VIRILE` na mówcach męskich w `ID: 36–60`. Ponowne tłumaczenie odcinka przez API LLM nie jest wymagane.
- **Etap 2/2 audytu 9.8 (audyt architektoniczny):** potwierdził spełnienie Zasad 1, 2, 3, 4 i 16, identyfikując 3 zadania domykające dla Zasady 8, symetrii Zasady 4 oraz Scope Deviation w `main.py`:
  1. **Operacja 2B.1 (Formalna legalizacja i otestowanie non-TTY CLI w `main.py` i `translator.py`):** dopisanie sparametryzowanego testu jednostkowego `T9.1` (`@pytest.mark.unit`) weryfikującego rezolucję `--subs` oraz `KEEP_HONORIFICS` przy `sys.stdin.isatty() == False` oraz udokumentowanie `main.py` w Tabeli P0.2.
  2. **Operacja 2C.1 (Symetria `MALE`/`FEMALE` w `_precompute_episode_scene_genders` oraz separacja `has_male_speaker_in_line` od płci adresata dla `Grupa_1os_lm` w `translator.py`):** zapewnienie, że pojedyncza kwestia jawnej postaci żeńskiej P0/P1 ma `scene_genders[orig_idx] = "kobieta"`, a `Grupa_1os_lm` (`We_Group`) dla mówczyni żeńskiej (`FEMININE`) w scenie kobiecej zachowuje `NON_VIRILE` nawet wtedy, gdy pojedynczym adresatem (`tgt_gram_tag`) jest mężczyzna (`MASCULINE`).
  3. **Operacja 2C.2 (Higiena `TEST 222` w `test_system.py`):** opatrzenie integracyjnego testu `test_standard_9_8_suite` (oraz `test_standard_9_9_suite`) w `test_system.py` odpowiednią strukturą i zaktualizowanie licznika końcowego w `__main__`.

Numer wersji: **9.9**. Poprzednia wersja: **9.8** (commit `783dffd`). Wersja Depuracji Legacy w tle: **1.0** (commit `474fb64`).

---

## FAZA 0 — CZYTANIE KODU (OBOWIĄZKOWA)

### P0.1. Lista plików do przeczytania w całości przed modyfikacją
1. `translator.py` — linie `1945-2038` (`_precompute_episode_scene_genders`), linie `3260-3282` (`_prepare_batch_prompt`), linie `4085-4125` (`_process_single_batch`) oraz linie `6170-6177` (`__main__`).
2. `main.py` — linie `340-395` (obsługa `args.input`, `args.subs`, `sys.stdin.isatty()`, `KEEP_HONORIFICS`).
3. `tests/test_discourse_and_translator.py` — linie `405-451` (`T8.1`).
4. `test_system.py` — linie `19500-19778` (`test_standard_9_8_suite` oraz licznik w `__main__`).

### P0.2. Tabela mapowania plan ↔ kod (do wypełnienia w `Raport_wdrozenia_9.9.md`)

| Operacja (sekcja 9.9) | Miejsce wywołania / metoda w planie | Rzeczywiste miejsce wywołania w kodzie (plik + linia + metoda) | Rzeczywista sygnatura w kodzie | Zgodność | Uwagi / Rozstrzygnięcie |
|---|---|---|---|---|---|
| 2B.1 | Legalizacja i pokrycie testem jednostkowym `T9.1` obsługi `--subs` i `not sys.stdin.isatty()` w `main.py` oraz delegacji CLI w `translator.py` | `<DO_WYPEŁNIENIA_PRZEZ_AGENTA_KODUJĄCEGO>` | `<DO_WYPEŁNIENIA_PRZEZ_AGENTA_KODUJĄCEGO>` | `<DO_WYPEŁNIENIA_PRZEZ_AGENTA_KODUJĄCEGO>` | `<DO_WYPEŁNIENIA_PRZEZ_AGENTA_KODUJĄCEGO>` |
| 2C.1 | Symetria `MALE`/`FEMALE` dla jawnego aktora w `_precompute_episode_scene_genders` oraz separacja płci mówcy (`has_male_speaker_in_line`) od płci adresata przy wyznaczaniu `Grupa_1os_lm` (`translator.py`) | `<DO_WYPEŁNIENIA_PRZEZ_AGENTA_KODUJĄCEGO>` | `<DO_WYPEŁNIENIA_PRZEZ_AGENTA_KODUJĄCEGO>` | `<DO_WYPEŁNIENIA_PRZEZ_AGENTA_KODUJĄCEGO>` | `<DO_WYPEŁNIENIA_PRZEZ_AGENTA_KODUJĄCEGO>` |
| 2C.2 | Aktualizacja licznika suite'ów w `test_system.py` i spójność puli testów `fast` / `full` | `<DO_WYPEŁNIENIA_PRZEZ_AGENTA_KODUJĄCEGO>` | `<DO_WYPEŁNIENIA_PRZEZ_AGENTA_KODUJĄCEGO>` | `<DO_WYPEŁNIENIA_PRZEZ_AGENTA_KODUJĄCEGO>` | `<DO_WYPEŁNIENIA_PRZEZ_AGENTA_KODUJĄCEGO>` |

### P0.3. Tabela mapowania danych testowych (do wypełnienia w `Raport_wdrozenia_9.9.md`)

| Placeholder | Wartość rzeczywista (spoza odcinka audytowanego) | Źródło (P0 / EN / ASS) | Uwagi |
|---|---|---|---|
| `<RZECZYWISTA_ETYKIETA_MĘSKA_P1_1>` | `<DO_WYPEŁNIENIA_MAPOWANIE_P0_3>` | `[Events]` | Jednoznaczna leksykalnie etykieta męska |
| `<RZECZYWISTA_ETYKIETA_ŻEŃSKA_P1_1>` | `<DO_WYPEŁNIENIA_MAPOWANIE_P0_3>` | `[Events]` | Jednoznaczna leksykalnie etykieta żeńska |
| `<RZECZYWISTY_ANTROPONIM_MĘSKI_1>` | `<DO_WYPEŁNIENIA_MAPOWANIE_P0_3>` | P0 (`SeriesBible`) | Mówca męski P0 |
| `<RZECZYWISTY_ANTROPONIM_ŻEŃSKI_1>` | `<DO_WYPEŁNIENIA_MAPOWANIE_P0_3>` | P0 (`SeriesBible`) | Mówczyni żeńska P0 |
| `<WARTOŚĆ_ENUM_TECHNICZNA_1>` | `<DO_WYPEŁNIENIA_MAPOWANIE_P0_3>` | KOD | `VIRILE` |
| `<WARTOŚĆ_ENUM_TECHNICZNA_2>` | `<DO_WYPEŁNIENIA_MAPOWANIE_P0_3>` | KOD | `NON_VIRILE` |

---

## SEKCJA 1: REGUŁY DLA MODELI LLM (Faza 1 i Faza 2)

Wszystkie reguły `R1.1–R1.11` z wersji 9.8 pozostają w 100% utrzymane w czystej formie pozytywnej.

---

## SEKCJA 2: OPERACJE (2A / 2B / 2C)

### 2A — Operacje potwierdzone z wersji 9.8 (bez nowych akcji)
1. **`2A.1` (z 9.8/2C.1 w `series_memory.py`):** Flaga `has_verified_gender: True` i `confidence: 0.95` dla etykiet z `INHERENT_MALE_NOUNS` i `INHERENT_FEMALE_NOUNS` w `populate_secondary_actor_tags` oraz ich ochrona w `audit_speaker_metadata_against_audio` — potwierdzona empirycznie (`ID: 58`).
2. **`2A.2` (z 9.7/2C.1, 2C.3, 2C.4 oraz 9.5–9.6):** Wszystkie operacje potwierdzone w Etapie 1/2 audytu 9.8 — utrzymane w 100%.

### 2B — Nowe operacje

#### OPERACJA 2B.1 — Formalna legalizacja i otestowanie jednostkowe nieinteraktywnego CLI (`main.py` + `tests/test_discourse_and_translator.py`)
- **Cel:** Objęcie sparametryzowanym testem jednostkowym `T9.1` (`@pytest.mark.unit`) zmian wprowadzonych w `main.py:349-350, 384-385` (obsługa aliasu `--subs` oraz zmiennej `KEEP_HONORIFICS` przy `sys.stdin.isatty() == False`), tak aby spełniały Zasadę 8 (100% falsyfikowalności).
- **Implementacja:**
  1. W `main.py` wydziel czystą funkcję pomocniczą `resolve_cli_inputs_and_honorifics(args, is_tty: bool, env_keep_honorifics: str) -> Tuple[List[str], Optional[bool]]` (lub równoważną metodę wywoływaną w `main()`), zwracającą parę `(raw_inputs, keep_honorifics)` dla zadanych argumentów `args`, stanu `sys.stdin.isatty()` oraz wartości `os.getenv("KEEP_HONORIFICS", "false")`.
  2. W `tests/test_discourse_and_translator.py` dodaj sparametryzowany test `T9.1` weryfikujący działanie funkcji dla $\ge 2$ zestawów parametrów (`--subs` + non-TTY `KEEP_HONORIFICS="true"` vs `"false"`).
- **Kryterium akceptacji:** Prawidłowy stan rezolucji CLI w trybie nieinteraktywnym (`is_tty=False`) = przejęcie ścieżki z `args.subs` do `raw_inputs` oraz deterministyczne wyznaczenie `keep_honorifics` ze zmiennej środowiskowej bez wywoływania blokującego `input()`.

### 2C — Domknięcie symetrii operacji z promptu 9.8

#### OPERACJA 2C.1 (z 9.8/2C.1 w `translator.py`) — Symetria `MALE`/`FEMALE` w `_precompute_episode_scene_genders` oraz separacja płci mówcy (`We_Group`) od płci adresata (`You_Group`) przy wyznaczaniu `Grupa_1os_lm` (`translator.py`)
- **Rozstrzygnięcie:** **DOPRECYZOWAĆ** `_precompute_episode_scene_genders`, `_prepare_batch_prompt` oraz `_process_single_batch` w `translator.py`.
- **Implementacja:**
  1. W `_precompute_episode_scene_genders` (`translator.py:1948-1956` oraz `2019-2034`): zapewnij pełną symetrię dla jawnego aktora o zweryfikowanej płci `MALE` oraz `FEMALE` — jeśli `act_gender == "MALE"`, ustaw `scene_genders[orig_idx] = "mężczyzna"`, a jeśli `act_gender == "FEMALE"`, ustaw `scene_genders[orig_idx] = "kobieta"`.
  2. W `_prepare_batch_prompt` (`translator.py:3265-3277`) oraz `_process_single_batch` (`translator.py:4099-4116`):
     - zdefiniuj oddzielnie `has_male_speaker_in_line = (spk_gram_tag == "MASCULINE") or (line_spk_gender == "mężczyzna")` oraz `has_male_addressee_in_line = (tgt_gram_tag == "MASCULINE") or (line_addr_cat in ["mężczyzna", "mężczyzna_dual", "grupa_mężczyzn"])`;
     - jeśli `has_male_speaker_in_line` jest `True`, ustaw `is_fem_scene = False` oraz wyklucz `NON_VIRILE` na `Grupa_1os_lm` (`pl_grp_val` / `line_pl_grp = "VIRILE"`);
     - jeśli mówcą jest kobieta (`spk_gram_tag == "FEMININE"`) w scenie kobiecej (`episode_scene_genders.get(orig_idx) == "kobieta"`), pojedynczy adresat męski (`tgt_gram_tag == "MASCULINE"`) ustawia rodzaj męski wyłącznie dla adresata, zachowując `Grupa_1os_lm: NON_VIRILE` dla kobiecej grupy mówiącej (`We_Group`), chyba że `scene_has_male` dla grupy mówiącej jest `True` lub `addressee_cat in ["grupa_mieszana", "para_mieszana_dual"]`.
- **Kryterium akceptacji:** Prawidłowy stan `Grupa_1os_lm` = `VIRILE` dla każdego mówcy męskiego (`MASCULINE`) oraz zachowanie `NON_VIRILE` dla mówczyni żeńskiej (`FEMININE`) reprezentującej grupę kobiecą nawet przy pojedynczym adresacie męskim (źródło autorytetu: Punkt 01 `verify_12_fixes.py` — separacja `We_Group` i `You_Group`).

#### OPERACJA 2C.2 — Higiena `TEST 222` i licznika końcowego w `test_system.py`
- **Implementacja:**
  1. W `test_system.py:19777` zaktualizuj tekstowy komunikat podsumowujący w bloku `if __name__ == "__main__":` tak, aby odzwierciedlał rzeczywistą liczbę wywoływanych funkcji testowych (`222/222`).
  2. Rozszerz test `T8.1` (lub dodaj `T9.2`) w `tests/test_discourse_and_translator.py` o sprawdzenie separacji `has_male_speaker_in_line` vs `has_male_addressee_in_line`.

---

## SEKCJA 3: REGUŁY DLA PIPELINE'U DANYCH

Wszystkie reguły `R3.1–R3.5` z wersji 9.8 pozostają utrzymane, z doprecyzowaniem `R3.2`:
- **R3.2 (P0) — Symetria Płci Mówcy i Separacja `We_Group` (`Grupa_1os_lm`) od `You_Group` (`Grupa_2os_lm`) w `Telemetria:`:**
  - **Definicja pozytywna:** Prawidłowy stan wektora `Telemetria:` w Kroku 10 = zachowanie `MASCULINE` dla `<RZECZYWISTA_ETYKIETA_MĘSKA_P1_1>` i `FEMININE` dla `<RZECZYWISTA_ETYKIETA_ŻEŃSKA_P1_1>`, przypisanie `Grupa_1os_lm: VIRILE` dla każdego mówcy o rodzaju `MASCULINE` oraz zachowanie `Grupa_1os_lm: NON_VIRILE` dla mówczyni o rodzaju `FEMININE` w scenie kobiecej niezależnie od płci pojedynczego adresata.

---

## SEKCJA 4: KOLEJNOŚĆ WDROŻENIA

1. **ETAP 1:** Wykonanie Phase 0 i wypełnienie Tabel P0.2 oraz P0.3 w `Raport_wdrozenia_9.9.md`.
2. **ETAP 2:** Wdrożenie Operacji `2B.1`, `2C.1` i `2C.2` w `main.py`, `translator.py` oraz `test_system.py`.
3. **ETAP 3:** Dodanie testów jednostkowych `T9.1` i `T9.2` w `tests/test_discourse_and_translator.py`, uruchomienie `pytest` (fast + full) oraz 4 bramek CI/CD i wypełnienie `Raport_wdrozenia_9.9.md`.

---

## SEKCJA 5: WALIDACJA TESTOWA I WARUNEK UKOŃCZENIA

### Wykaz nowych testów `T9.1` i `T9.2` (marker: `unit`)

```python
import argparse
import pytest

# WZORZEC T9.1 (Operacja 2B.1) -> tests/test_discourse_and_translator.py
@pytest.mark.unit
@pytest.mark.parametrize(
    "subs_arg,env_honorifics,expected_inputs,expected_keep_honorifics",
    [
        ("episode_input_a.ass", "true", ["episode_input_a.ass"], True),
        ("episode_input_b.ass", "false", ["episode_input_b.ass"], False),
    ],
)
def test_non_tty_cli_resolves_subs_argument_and_honorifics_env_without_stdin_prompt(
    subs_arg, env_honorifics, expected_inputs, expected_keep_honorifics
):
    from main import resolve_cli_inputs_and_honorifics

    ns = argparse.Namespace(input=None, subs=subs_arg, no_honorifics=False, honorifics=False)
    raw_inputs, keep_hon = resolve_cli_inputs_and_honorifics(
        ns, is_tty=False, env_keep_honorifics=env_honorifics
    )
    assert raw_inputs == expected_inputs
    assert keep_hon is expected_keep_honorifics


# WZORZEC T9.2 (Operacja 2C.1) -> tests/test_discourse_and_translator.py
@pytest.mark.unit
@pytest.mark.parametrize(
    "spk_gram,tgt_gram,is_fem_scene_init,expected_we_group",
    [
        ("MASCULINE", "FEMININE", True, "<WARTOŚĆ_ENUM_TECHNICZNA_1>"),
        ("FEMININE", "MASCULINE", True, "<WARTOŚĆ_ENUM_TECHNICZNA_2>"),
    ],
)
def test_we_group_virility_depends_on_speaker_gender_and_preserves_female_we_group_with_male_target(
    spk_gram, tgt_gram, is_fem_scene_init, expected_we_group
):
    has_male_speaker = spk_gram == "MASCULINE"
    is_fem_scene = False if has_male_speaker else is_fem_scene_init
    we_group = "<WARTOŚĆ_ENUM_TECHNICZNA_2>" if is_fem_scene else "<WARTOŚĆ_ENUM_TECHNICZNA_1>"
    assert we_group == expected_we_group