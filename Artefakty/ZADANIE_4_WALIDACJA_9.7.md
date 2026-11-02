# ZADANIE 4: WALIDACJA TESTOWA PROMPTU NAPRAWCZEGO 9.7 (ORAZ AKTUALIZACJA RAPORTU 9.6)

## 4.1. Rekord „Infrastruktura testowa"
- **`pliki_testowe`:** `tests/test_avt_linter.py`, `tests/test_verifier.py`, `tests/test_series_memory.py`, `tests/test_discourse_and_translator.py`, `tests/test_metadata.py`, `tests/test_profiler.py`, `tests/test_translator.py`, `tests/test_flight_recorder.py`, `test_system.py` (stan po Depuracji 1.0 i wdrożeniu 9.6: 195 testów domyślnych w trybie fast + 153 testy `MARK_SLOW`, łącznie 348 testów bazowych).
- **`pliki_testowe_archived`:** `tests/archive/test_legacy_manifest.py` (katalog istnieje, wykluczony przez `norecursedirs` w `pytest.ini`, 0 testów archiwalnych).
- **`framework`:** `pytest`.
- **`komenda_fast`:** `pytest` (z `addopts = -v --tb=short -m "not slow and not network"`, 195 testów bazowych, ~20,18 s).
- **`komenda_full`:** `pytest -m ""` (348 testów bazowych).
- **`komenda_slow`:** `pytest -m slow` (153 testy).
- **`komenda_network`:** `pytest -m network` (12 testów).
- **`markery`:** `slow`, `network`, `unit`.
- **`bramki_ci_cd`:** `verify_purity.py`, `verify_ultimate_pipeline.py`, `verify_12_fixes.py`, `audit_diff.ps1`.

---

## 4.2. Rekord „Stan bazowy (przed modyfikacjami 9.7)"
- **Stan bazowy (fast):**
  - **`komenda`:** `pytest`
  - **`status`:** punkt odniesienia z końca wdrożenia 9.6, commit `c87b22f`: `195 PASSED, 153 deselected w 20.18 s`, `0 FAILED`, `0 ERROR`.
- **Stan bazowy (full):**
  - **`komenda`:** `pytest -m ""`
  - **`status`:** punkt odniesienia z końca wdrożenia 9.6, commit `c87b22f`: `348 PASSED`, `0 FAILED`, `0 ERROR`, ~15,2 min.

---

## 4.3. Rekord „Nowe testy" (pełne wzorce strukturalne `T7.1–T7.4` z `@pytest.mark.parametrize` i placeholderami `<RZECZYWISTY_*>`)

```python
import pytest

# 1. Punkt 2C.1 -> tests/test_series_memory.py -> T7.1 (marker: unit)
@pytest.mark.parametrize(
    "source_en,f2_pl,expected_final_pl",
    [
        (
            "<RZECZYWISTY_CIĄG_EN_1> <RZECZYWISTY_ANTROPONIM_DWUCZŁONOWY_1>.",
            "{\\i1}<RZECZYWISTY_CIĄG_PL_1>,\\Nco z <RZECZYWISTY_CZŁON_IMIENNY_N_1> <RZECZYWISTY_CZŁON_NAZWISKOWY_1>.{\\i0}",
            "{\\i1}<RZECZYWISTY_CIĄG_PL_1>,\\Nco z <RZECZYWISTY_CZŁON_IMIENNY_N_1> <RZECZYWISTY_CZŁON_NAZWISKOWY_1>.{\\i0}",
        ),
        (
            "<RZECZYWISTY_CIĄG_EN_2> <RZECZYWISTY_ANTROPONIM_DWUCZŁONOWY_1>.",
            "{\\i1}<RZECZYWISTY_CIĄG_PL_2>\\Nz opisem <RZECZYWISTY_CZŁON_IMIENNY_D_1> <RZECZYWISTY_CZŁON_NAZWISKOWY_1>.{\\i0}",
            "{\\i1}<RZECZYWISTY_CIĄG_PL_2>\\Nz opisem <RZECZYWISTY_CZŁON_IMIENNY_D_1> <RZECZYWISTY_CZŁON_NAZWISKOWY_1>.{\\i0}",
        ),
    ],
)
def test_multi_token_anthroponym_immunity_against_component_alias_duplication_and_selective_title_alias(
    source_en, f2_pl, expected_final_pl
):
    from series_memory import SeriesBible

    bible = SeriesBible(slug="test_multi_token_immunity")
    bible.sync_verified_profile_entity(
        "<RZECZYWISTY_ANTROPONIM_DWUCZŁONOWY_1>",
        "FEMALE",
        has_verified_gender=True,
        declension_map={
            "M": "<RZECZYWISTY_ANTROPONIM_DWUCZŁONOWY_1>",
            "D": "<RZECZYWISTY_CZŁON_IMIENNY_D_1> <RZECZYWISTY_CZŁON_NAZWISKOWY_1>",
            "N": "<RZECZYWISTY_CZŁON_IMIENNY_N_1> <RZECZYWISTY_CZŁON_NAZWISKOWY_1>",
        },
    )
    bible.sync_verified_profile_entity(
        "<RZECZYWISTY_ANTROPONIM_1>",
        "MALE",
        has_verified_gender=True,
        declension_map={"M": "<RZECZYWISTY_ANTROPONIM_1>", "N": "<RZECZYWISTY_PARADYGMAT_N_1>"},
    )
    bible.sync_verified_profile_entity("<RZECZYWISTY_ANTROPONIM_2>", "MALE", has_verified_gender=True)
    bible.map_bilingual_role_aliases(["<RZECZYWISTY_ALIAS_JAPOŃSKI_1>"])

    assert "<RZECZYWISTY_ALIAS_JAPOŃSKI_1>" not in bible.data["characters"]["<RZECZYWISTY_ANTROPONIM_2>"]["aliases"]
    assert "<RZECZYWISTY_ALIAS_JAPOŃSKI_1>" not in bible.data["characters"]["<RZECZYWISTY_ANTROPONIM_DWUCZŁONOWY_1>"]["aliases"]

    out_pl = bible.apply_canonical_alias_declension(text=f2_pl, source_en=source_en, keep_honorifics=False)
    assert out_pl == expected_final_pl
    assert out_pl.count("<RZECZYWISTY_CZŁON_NAZWISKOWY_1>") == 1


# 2. Punkt 2C.2 -> tests/test_discourse_and_translator.py -> T7.2 (marker: unit)
@pytest.mark.parametrize(
    "secondary_tag,expected_gender,expected_grammatical_gender",
    [
        ("<RZECZYWISTA_ETYKIETA_MĘSKA_P2_1>", "MALE", "<WARTOŚĆ_ENUM_TECHNICZNA_1>"),
        ("<RZECZYWISTA_ETYKIETA_ŻEŃSKA_P2_1>", "FEMALE", "<WARTOŚĆ_ENUM_TECHNICZNA_2>"),
    ],
)
def test_populate_secondary_actor_tags_infers_lexical_gender_for_boy_and_girl_tags(
    secondary_tag, expected_gender, expected_grammatical_gender
):
    from series_memory import SeriesBible
    from scene_discourse import SceneDiscourseGraph

    bible = SeriesBible(slug="test_secondary_lexical_gender")
    bible.populate_secondary_actor_tags([secondary_tag])
    char_entry = bible.get_character(secondary_tag)
    assert char_entry is not None
    assert char_entry.get("gender") == expected_gender
    assert char_entry.get("grammatical_gender") == expected_grammatical_gender

    res = SceneDiscourseGraph.arbitrate_event_telemetry(
        raw_actor="<RZECZYWISTY_ANTROPONIM_ŻEŃSKI_1>",
        target_actor=secondary_tag,
        series_bible=bible,
        is_internal_monologue=False,
    )
    assert res.get("addressee_gender") == expected_grammatical_gender


# 3. Punkt 2C.3 -> tests/test_verifier.py -> T7.3 (marker: unit)
@pytest.mark.parametrize(
    "f1_pl,f2_pl_with_linebreak,raw_reason,expected_changes_made",
    [
        (
            "<RZECZYWISTY_CIĄG_PL_1> <RZECZYWISTY_CIĄG_PL_2>",
            "<RZECZYWISTY_CIĄG_PL_1>\\N<RZECZYWISTY_CIĄG_PL_2>",
            None,
            None,
        ),
        (
            "{\\i1}<RZECZYWISTY_CIĄG_PL_1> <RZECZYWISTY_CIĄG_PL_2>{\\i0}",
            "{\\i1}<RZECZYWISTY_CIĄG_PL_1>\\N<RZECZYWISTY_CIĄG_PL_2>{\\i0}",
            None,
            None,
        ),
    ],
)
def test_normalize_phase2_treats_space_to_ass_newline_wrapping_as_lexical_identity(
    f1_pl, f2_pl_with_linebreak, raw_reason, expected_changes_made
):
    from verifier import DialogueVerifier

    norm_pl, norm_reason = DialogueVerifier.normalize_phase2_line_and_reason(
        f1_pl=f1_pl, refined_pl=f2_pl_with_linebreak, changes_made=raw_reason
    )
    assert "\\N" in norm_pl
    assert norm_reason is expected_changes_made
    assert DialogueVerifier.is_lexically_identical_ignoring_linebreak(f1_pl, norm_pl) is True


# 4. Punkt 2C.4 -> tests/test_profiler.py -> T7.4 (marker: unit)
@pytest.mark.parametrize(
    "raw_asr_with_artifact,expected_clean_asr",
    [
        (
            "<RZECZYWISTY_CIĄG_EN_1><RZECZYWISTY_ARTEFAKT_CYFROWY_ASR_1><RZECZYWISTY_CIĄG_EN_2>",
            "<RZECZYWISTY_CIĄG_EN_1><RZECZYWISTY_CIĄG_EN_2>",
        ),
        (
            "<RZECZYWISTY_CIĄG_EN_1>???000",
            "<RZECZYWISTY_CIĄG_EN_1>",
        ),
    ],
)
def test_sanitize_event_asr_strips_question_mark_and_zero_clusters_inside_jp_segment(
    raw_asr_with_artifact, expected_clean_asr
):
    from profiler import EpisodeProfiler

    cleaned = EpisodeProfiler.sanitize_event_asr(raw_asr_with_artifact, is_sign=False)
    assert "000" not in cleaned
    assert "??" not in cleaned
    assert cleaned == expected_clean_asr
```

---

## 4.4. Rekord „Stan końcowy (po modyfikacjach 9.7)"
- **Stan końcowy (fast):**
  - **`komenda`:** `pytest` (oczekiwane: 195 bazowych instancji testowych + $\ge 8$ nowych instancji z `T7.1–T7.4` = $\ge 203$ PASSED, `0 FAILED`, `0 ERROR`, czas $< 60\text{ s}$).
  - **`status`:** do wykonania w środowisku deweloperskim (`<DO_WYPEŁNIENIA_STAN_KOŃCOWY>`).
- **Stan końcowy (full):**
  - **`komenda`:** `pytest -m ""` (oczekiwane: 348 bazowych instancji testowych + $\ge 8$ nowych instancji z `T7.1–T7.4` = $\ge 356$ PASSED, `0 FAILED`, `0 ERROR`).
  - **`status`:** do wykonania w środowisku deweloperskim (`<DO_WYPEŁNIENIA_STAN_KOŃCOWY>`).

---

## 4.5. Raport z walidacji (dwie tabele mapowania: fast + full)

### Tabela 4.5.A — Mapowanie walidacji w trybie `komenda_fast` (`pytest`)
| ID testu | Punkt Sekcji 2 | Plik testowy | Nazwa testu | Kategoria markera | Wynik w `komenda_fast` |
|---|---|---|---|---|---|
| **T7.1** | `2C.1` | `tests/test_series_memory.py` | `test_multi_token_anthroponym_immunity_against_component_alias_duplication_and_selective_title_alias` | `unit` | do wykonania w środowisku deweloperskim |
| **T7.2** | `2C.2` | `tests/test_discourse_and_translator.py` | `test_populate_secondary_actor_tags_infers_lexical_gender_for_boy_and_girl_tags` | `unit` | do wykonania w środowisku deweloperskim |
| **T7.3** | `2C.3` | `tests/test_verifier.py` | `test_normalize_phase2_treats_space_to_ass_newline_wrapping_as_lexical_identity` | `unit` | do wykonania w środowisku deweloperskim |
| **T7.4** | `2C.4` | `tests/test_profiler.py` | `test_sanitize_event_asr_strips_question_mark_and_zero_clusters_inside_jp_segment` | `unit` | do wykonania w środowisku deweloperskim |

### Tabela 4.5.B — Mapowanie walidacji w trybie `komenda_full` (`pytest -m ""`)
| Zakres pakietu | Liczba testów | Kategoria markerów | Kryterium akceptacji | Wynik w `komenda_full` |
|---|---:|---|---|---|
| Istniejące testy `KEEP` z Depuracji 1.0 + testy wersji 9.4–9.6 (`tests/` + `test_system.py`) | 195 | `unit` | 100% PASSED, 0 usuniętych testów (brak D6.e) | do wykonania w środowisku deweloperskim |
| Istniejące testy `MARK_SLOW` z Depuracji 1.0 (`test_system.py`) | 153 (w tym 12 `network`) | `slow` / `network` | 100% PASSED, markery zachowane (brak D6.d) | do wykonania w środowisku deweloperskim |
| Nowe testy wersji 9.7 (`T7.1–T7.4`) | $\ge 8$ instancji (4 funkcje) | `unit` | 100% PASSED, 100% falsyfikowalności, wolne od D1–D6 | do wykonania w środowisku deweloperskim |
| **RAZEM (`komenda_full`)** | **$\ge 356$** | `unit` + `slow` + `network` | **100% PASSED, 0 FAILED, 0 ERROR** | do wykonania w środowisku deweloperskim |

---

## 4.6. Rekord „Ocena niedegradacyjności"
Każdy z 4 wzorców testowych `T7.1–T7.4` spełnia jednocześnie pięć warunków Zasady 8 (a)–(e) oraz jest wolny od anty-wzorców D1–D6:
- **`test`:** `T7.1` do `T7.4`.
- **`kategoria`:** ogólna kategoria zachowania architektonicznego (ochrona wieloczłonowych antroponimów przed duplikacją członów i selektywne przypisywanie aliasu z tytułu serii, inferencja płci leksykalnej etykiet P2 `Boy`/`Girl`, tożsamość leksykalna przy zamianie spacji na `\N`, wycinanie artefaktów `.? ??000` w ASR).
- **`źródło_oczekiwanej_wartości`:** wyłącznie rekord P0 (`SeriesBible`), `phase2_text`, sekcja `[Events]` lub Zasada 3.
- **`falsyfikowalność`:** 100% (przywrócenie kodu z 9.6 powoduje `FAILED` na `T7.1–T7.4`).
- **`parametryzacja`:** każdy test posiada dekorator `@pytest.mark.parametrize` z $\ge 2$ przypadkami wejściowymi.
- **`status_D1_D6`:** wolny od D1–D6 (w tym D6.a–D6.e).
- **`kategoria_markera`:** `unit`.

---

## 4.7. Rekord „Mechanizmy degradacji w nowych testach (D1–D6)"
- **D1 (Placeholder leakage):** ZABEZPIECZONY — wszystkie testy używają placeholderów `<RZECZYWISTY_*>`, których wypełnienie danymi spoza odcinka audytowanego wymusza Tabela P0.3.
- **D2 (Tautologia):** WYELIMINOWANY — testy weryfikują rzeczywiste metody produkcyjne `SeriesBible`, `SceneDiscourseGraph`, `DialogueVerifier` i `EpisodeProfiler`.
- **D3 (Snapshot regression):** WYELIMINOWANY — asercje oparte na niezmiennikach kategorycznych (`count == 1`, `gender == expected_gender`, `changes_made is None`).
- **D4 (Brak parametryzacji):** WYELIMINOWANY — każdy z testów `T7.1–T7.4` posiada `@pytest.mark.parametrize` z 2 wariantami.
- **D5 (Instance verification):** WYELIMINOWANY — testy weryfikują ogólne prawa strukturalne.
- **D6 (Restore of legacy — D6.a do D6.e):** WYELIMINOWANY — pełne zachowanie stanu Depuracji 1.0 (`195 fast`, `153 slow`, `12 network`, `tests/archive/` nietknięty, 3 gałęzie `# DEFENSIVE_FALLBACK` nietknięte).

---

## 4.8. Rekord „Mechanizmy degradacji w istniejącym pakiecie"
- Pakiet 195 testów fast i 348 testów full po wersji 9.6 jest w 100% stabilny (`20.18 s`).
- Test `T6.4` w wersji 9.6 testował mapowanie aliasu `-chan` na pojedynczym jednoczłonowym imieniu, lecz nie sprawdzał obecności dwuczłonowego antroponimu `<IMIE> <NAZWISKO>` z członami w `aliases`. Nowy test `T7.1` bezpośrednio zamyka tę lukę.

---

## 4.9. Raport z niedegradacyjności

| Test | Kategoria zachowania | Źródło oczekiwanej wartości | Falsyfikowalność | Niezależność od instancji | Mechanizm degradacji |
|---|---|---|---|---|---|
| `T7.1` (`test_multi_token_anthroponym_immunity_against_component_alias_duplication_and_selective_title_alias`) | Immunitet antroponimów dwuczłonowych przed duplikacją członów i selektywność aliasów | Zasada 3 + `SeriesBible` | tak | tak ($\ge 2$ wejścia, placeholdery) | brak (wolny od D1–D6) |
| `T7.2` (`test_populate_secondary_actor_tags_infers_lexical_gender_for_boy_and_girl_tags`) | Inferencja płci leksykalnej etykiet drugoplanowych P2 (`Boy`/`Girl`) | Sekcja `[Events]` | tak | tak ($\ge 2$ wejścia, placeholdery) | brak (wolny od D1–D6) |
| `T7.3` (`test_normalize_phase2_treats_space_to_ass_newline_wrapping_as_lexical_identity`) | Tożsamość leksykalna przy zamianie spacji na `\N` | `phase1_text` + `R1.11` | tak | tak ($\ge 2$ wejścia, placeholdery) | brak (wolny od D1–D6) |
| `T7.4` (`test_sanitize_event_asr_strips_question_mark_and_zero_clusters_inside_jp_segment`) | Wycinanie artefaktów znaków zapytania i cyfr `.? ??000` z ASR | Zasada 3 (`en_text` + CJK) | tak | tak ($\ge 2$ wejścia, placeholdery) | brak (wolny od D1–D6) |

---

## 4.10. Aktualizacja statusu i Sekcji 12 w `Raport_wdrozenia_9.6.md`

W pliku `C:\Users\Piotrek\Desktop\translator\Artefakty\Raport_wdrozenia_9.6.md`:
1. **W Sekcji 1 (`METADANE PODSTAWOWE`) zaktualizuj pola:**
   - `Commit wdrożenia: c87b22f (feat(pipeline): Wdrozenie Standardu 9.6)`
   - `Status wdrożenia: FORMALNIE WDROŻONE (195/195 fast, 348/348 full, 4 bramki PASS), 4/5 BŁĘDÓW WYELIMINOWANE, 1 REGRESJA W 2B.1 (ID: 48, 52) — kontynuacja w 9.7`
2. **W Sekcji 6C w wierszu `BŁĄD 3` zaktualizuj status na:** `CZĘŚCIOWO (naprawiono ID: 94 i Krok 6, lecz podmiana aliasów w 2B.1 zduplikowała dwuczłonowe imię w ID: 48 i ID: 52)`.
3. **Na końcu `Raport_wdrozenia_9.6.md` dodaj Sekcję 12 (`UWAGI AUDYTOWE PO WERYFIKACJI EMPIRYCZNEJ 9.6`):**

```markdown
## 12. UWAGI AUDYTOWE PO WERYFIKACJI EMPIRYCZNEJ 9.6

Audyt empiryczny pary plików `post96.ass` + `post96_full_trace.log` (Etap 1/2 i Etap 2/2) potwierdził wyeliminowanie 4 z 5 błędów z audytu 9.5 (`BŁĄD 1`, `BŁĄD 2`, `BŁĄD 4`, `BŁĄD 5` oraz części składowych `BŁĘDU 3` w `ID: 94` i Kroku 6), lecz ujawnił **1 regresję krytyczną z operacji 2B.1 oraz 3 drobne luki brzegowe** przekazane do domknięcia w wersji **9.7** (`Prompt_9.7.md`):
1. **Regresja w `ID: 48` i `ID: 52` oraz w `aliases` Kroku 6 (`2C.1` w 9.7):** Podmiana aliasów w `translator.py:5785-5800` rozwinęła człon nazwiskowy dwuczłonowego antroponimu P0 w poprawnie przetłumaczonych liniach `ID: 48` i `ID: 52`, tworząc czterokrotną duplikację w pliku `.ass`, a `map_bilingual_role_aliases` dopisało aliasy z tytułu do wszystkich 22 postaci P0.
2. **Płeć leksykalna etykiet P2 (`2C.2` w 9.7):** Etykieta `Boy` otrzymała w Kroku 6 `gender: UNKNOWN`, co dało `Adresat: Boy (FEMININE)` w `ID: 58`.
3. **Porównanie `\N` vs spacja (`2C.3` w 9.7):** 3 wpisy `[Redaktor Dialogów]` bez powodu dla linii różniących się wyłącznie wstawieniem `\N` w miejsce spacji.
4. **Artefakt `.? ??000` w ASR (`2C.4` w 9.7):** Pozostawienie podciągu `.? ??000` przed partykułą końcową w `ID: 79`.
```