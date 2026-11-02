# Plik: C:\Users\Piotrek\Desktop\translator\Artefakty\ZADANIE_4_WALIDACJA_9.9.md

# ZADANIE 4: WALIDACJA TESTOWA PROMPTU NAPRAWCZEGO 9.9 (ORAZ AKTUALIZACJA RAPORTU 9.8)

## 4.1. Rekord „Infrastruktura testowa"
- **`pliki_testowe`:** `tests/test_avt_linter.py`, `tests/test_verifier.py`, `tests/test_series_memory.py`, `tests/test_discourse_and_translator.py`, `tests/test_metadata.py`, `tests/test_profiler.py`, `tests/test_translator.py`, `tests/test_flight_recorder.py`, `test_system.py` (stan po Depuracji 1.0 i wdrożeniu 9.8: 207 testów domyślnych w trybie fast + 153 testy `MARK_SLOW`, łącznie 360 testów bazowych).
- **`pliki_testowe_archived`:** `tests/archive/test_legacy_manifest.py` (katalog istnieje, wykluczony przez `norecursedirs` w `pytest.ini`, 0 testów archiwalnych).
- **`framework`:** `pytest`.
- **`komenda_fast`:** `pytest` (z `addopts = -v --tb=short -m "not slow and not network"`, 207 testów bazowych, ~15,65 s).
- **`komenda_full`:** `pytest -m ""` (360 testów bazowych).
- **`komenda_slow`:** `pytest -m slow` (153 testy).
- **`komenda_network`:** `pytest -m network` (12 testów).
- **`markery`:** `slow`, `network`, `unit`.
- **`bramki_ci_cd`:** `verify_purity.py`, `verify_ultimate_pipeline.py`, `verify_12_fixes.py`, `audit_diff.ps1`.

---

## 4.2. Rekord „Stan bazowy (przed modyfikacjami 9.9)"
- **Stan bazowy (fast):**
  - **`komenda`:** `pytest`
  - **`status`:** punkt odniesienia z końca wdrożenia 9.8, commit `783dffd`: `207 PASSED, 153 deselected w 15,65 s`, `0 FAILED`, `0 ERROR`.
- **Stan bazowy (full):**
  - **`komenda`:** `pytest -m ""`
  - **`status`:** punkt odniesienia z końca wdrożenia 9.8, commit `783dffd`: `360 PASSED`, `0 FAILED`, `0 ERROR`.

---

## 4.3. Rekord „Nowe testy"
Pełne szkielety testów `T9.1` i `T9.2` znajdują się w pliku `Prompt_9.9.md` → Sekcja 5 → Wykaz nowych testów `T9.1` i `T9.2` (marker: unit).

---

## 4.4. Rekord „Stan końcowy (po modyfikacjach 9.9)"
- **Stan końcowy (fast):**
  - **`komenda`:** `pytest` (oczekiwane: 207 bazowych instancji testowych + co najmniej 4 nowe instancje z `T9.1` (+2) i `T9.2` (+2) = ≥ 211 PASSED, `0 FAILED`, `0 ERROR`, czas < 60 s).
  - **`status`:** do wykonania w środowisku deweloperskim (`<DO_WYPEŁNIENIA_STAN_KOŃCOWY>`).
- **Stan końcowy (full):**
  - **`komenda`:** `pytest -m ""` (oczekiwane: 360 bazowych instancji testowych + co najmniej 4 nowe instancje z `T9.1` i `T9.2` = ≥ 364 PASSED, `0 FAILED`, `0 ERROR`).
  - **`status`:** do wykonania w środowisku deweloperskim (`<DO_WYPEŁNIENIA_STAN_KOŃCOWY>`).

**Uwaga:** Dokładna liczba instancji zależy od sposobu parametryzacji `T9.2` (2 przypadki zgodnie z `Prompt_9.9.md` Sekcja 5) oraz ewentualnej parametryzacji `TEST 222` (rozszerzenie higieniczne — bez zmiany liczby instancji lub z +2, jeśli audytor dopuści parametryzację suite'u). Bilans minimalny: **+4 instancje** (T9.1 ×2 + T9.2 ×2).

---

## 4.5. Raport z walidacji (dwie tabele mapowania: fast + full)

### Tabela 4.5.A — Mapowanie walidacji w trybie `komenda_fast` (`pytest`)
| ID testu | Punkt Sekcji 2 | Plik testowy | Nazwa testu | Kategoria markera | Wynik w `komenda_fast` |
|---|---|---|---|---|---|
| **T9.1** | `2B.1` | `tests/test_discourse_and_translator.py` | `test_non_tty_cli_resolves_subs_argument_and_honorifics_env_without_stdin_prompt` | `unit` | do wykonania w środowisku deweloperskim |
| **T9.2** | `2C.1` | `tests/test_discourse_and_translator.py` | `test_we_group_virility_depends_on_speaker_gender_and_preserves_female_we_group_with_male_target` | `unit` | do wykonania w środowisku deweloperskim |

### Tabela 4.5.B — Mapowanie walidacji w trybie `komenda_full` (`pytest -m ""`)
| Zakres pakietu | Liczba testów | Kategoria markerów | Kryterium akceptacji | Wynik w `komenda_full` |
|---|---:|---|---|---|
| Istniejące testy `KEEP` z Depuracji 1.0 + testy wersji 9.4–9.8 (`tests/` + `test_system.py`) | 207 | `unit` | 100% PASSED, 0 usuniętych testów (brak D6.e) | do wykonania w środowisku deweloperskim |
| Istniejące testy `MARK_SLOW` z Depuracji 1.0 (`test_system.py`) | 153 (w tym 12 `network`) | `slow` / `network` | 100% PASSED, markery zachowane (brak D6.d) | do wykonania w środowisku deweloperskim |
| Nowe testy wersji 9.9 (`T9.1`, `T9.2`) | ≥ 4 instancje (2 funkcje × 2 przypadki) | `unit` | 100% PASSED, 100% falsyfikowalności, wolne od D1–D6 | do wykonania w środowisku deweloperskim |
| **RAZEM (`komenda_full`)** | **≥ 364** | `unit` + `slow` + `network` | **100% PASSED, 0 FAILED, 0 ERROR** | do wykonania w środowisku deweloperskim |

---

## 4.6. Rekord „Ocena niedegradacyjności"
Wzorce testowe `T9.1` i `T9.2` spełniają jednocześnie pięć warunków Zasady 8 (a)–(e) oraz są wolne od anty-wzorców D1–D6:
- **`test`:** `T9.1`, `T9.2`.
- **`kategoria`:** ogólna kategoria zachowania architektonicznego:
  - `T9.1`: rezolucja CLI w trybie nieinteraktywnym (`--subs`, `KEEP_HONORIFICS`, `!sys.stdin.isatty()`).
  - `T9.2`: separacja `has_male_speaker_in_line` (sterującej `Grupa_1os_lm`) od płci adresata (sterującej wyłącznie `Grupa_2os_lm`).
- **`źródło_oczekiwanej_wartości`:** wyłącznie kategorie metajęzyka architektury (`VIRILE`, `NON_VIRILE`, `args.subs`, `env.KEEP_HONORIFICS`, `is_tty`) oraz specyfikacja `Prompt_9.9.md` Sekcja 2 → 2B.1 i 2C.1.
- **`falsyfikowalność`:** 100% (przywrócenie kodu z 9.8 powoduje `FAILED` na `T9.1` lub `T9.2`).
- **`parametryzacja`:** dekorator `@pytest.mark.parametrize` z ≥ 2 przypadkami wejściowymi każdy.
- **`status_D1_D6`:** wolne od D1–D6 (w tym D6.a–D6.e).
- **`kategoria_markera`:** `unit`.

---

## 4.7. Rekord „Mechanizmy degradacji w nowych testach (D1–D6)"
- **D1 (Placeholder leakage):** ZABEZPIECZONY — oba testy używają placeholderów `<RZECZYWISTA_*>`, `<RZECZYWISTY_*>`, `<WARTOŚĆ_ENUM_TECHNICZNA_*>`, których wypełnienie danymi spoza odcinka audytowanego wymusza Tabela P0.3.
- **D2 (Tautologia):** WYELIMINOWANY — `T9.1` wywołuje rzeczywistą funkcję `main.resolve_cli_inputs_and_honorifics`; `T9.2` weryfikuje niezmiennik kategoryczny `We_Group vs You_Group`.
- **D3 (Snapshot regression):** WYELIMINOWANY — asercje oparte na niezmiennikach kategorycznych (`keep_hon is expected_keep_honorifics`, `we_group == expected_we_group`).
- **D4 (Brak parametryzacji):** WYELIMINOWANY — oba testy posiadają `@pytest.mark.parametrize` z 2 wariantami.
- **D5 (Instance verification):** WYELIMINOWANY — testy weryfikują ogólne prawa strukturalne.
- **D6 (Restore of legacy — D6.a do D6.e):** WYELIMINOWANY — pełne zachowanie stanu Depuracji 1.0 (`207 fast`, `153 slow`, `12 network`, `tests/archive/` nietknięty, 3 gałęzie `# DEFENSIVE_FALLBACK` nietknięte).

---

## 4.8. Rekord „Mechanizmy degradacji w istniejącym pakiecie"
- Pakiet 207 testów fast i 360 testów full po wersji 9.8 jest w 100% stabilny (`15,65 s`).
- Test `T8.1` w wersji 9.8 weryfikował jedynie `populate_secondary_actor_tags` i `arbitrate_event_telemetry` w izolacji, lecz nie sprawdzał:
  - (a) rezolucji CLI `--subs` i `KEEP_HONORIFICS` w trybie `not sys.stdin.isatty()` (nowe `T9.1`);
  - (b) separacji `has_male_speaker_in_line` od płci adresata w kontekście `We_Group` (nowe `T9.2`).
- Nowe testy `T9.1` i `T9.2` bezpośrednio zamykają te luki.

---

## 4.9. Raport z niedegradacyjności

| Test | Kategoria zachowania | Źródło oczekiwanej wartości | Falsyfikowalność | Niezależność od instancji | Mechanizm degradacji |
|---|---|---|---|---|---|
| `T9.1` (`test_non_tty_cli_resolves_subs_argument_and_honorifics_env_without_stdin_prompt`) | Rezolucja CLI w trybie nieinteraktywnym (`--subs`, `KEEP_HONORIFICS`, `!sys.stdin.isatty()`) | Specyfikacja `Prompt_9.9.md` Sekcja 2 → 2B.1 | tak | tak (≥ 2 wejścia, placeholdery) | brak (wolny od D1–D6) |
| `T9.2` (`test_we_group_virility_depends_on_speaker_gender_and_preserves_female_we_group_with_male_target`) | Separacja `We_Group` (`Grupa_1os_lm`) od płci pojedynczego adresata | `Prompt_9.9.md` Sekcja 2 → 2C.1 + Punkt 01 `verify_12_fixes.py` | tak | tak (≥ 2 wejścia, placeholdery) | brak (wolny od D1–D6) |

---

## 4.10. Aktualizacja statusu i Sekcji 12 w `Raport_wdrozenia_9.8.md`

W pliku `C:\Users\Piotrek\Desktop\translator\Artefakty\Raport_wdrozenia_9.8.md`:

1. **W Sekcji 1 (`METADANE PODSTAWOWE`) zaktualizuj pola:**
   - `Commit wdrożenia: 783dffd (feat(pipeline): Wdrozenie Standardu 9.8)`
   - `Status wdrożenia: FORMALNIE WDROŻONE (207/207 fast, 360/360 full, 4 bramki PASS), 6/6 ZAGADNIEŃ WYELIMINOWANYCH EMPIRYCZNIE, 2/7 ZASAD ARCHITEKTONICZNYCH CZĘŚCIOWO (Zasada 8, MAIN.PY Scope Deviation) — domknięcie w 9.9`

2. **W Sekcji 7 (`OCENA NIEDEGRADACYJNOŚCI`) dodaj podpunkt:**
   - `Zasada 8 — CZĘŚCIOWO: TEST 222 (test_system.py:19506) bez @pytest.mark.parametrize (naruszenie D4), brak testu jednostkowego dla main.py:349-350, 384-385 i translator.py:6174-6176.`

3. **Na końcu `Raport_wdrozenia_9.8.md` wklej 1:1 poniższą Sekcję 12 (`UWAGI AUDYTOWE PO WERYFIKACJI EMPIRYCZNEJ 9.8`):**

```markdown
## 12. UWAGI AUDYTOWE PO WERYFIKACJI EMPIRYCZNEJ 9.8

Audyt empiryczny pary plików `post98.ass` + `post98_full_trace.log` oraz logu konsolowego `przebieg_tłumaczenia_post98.txt` (Etap 1/2) potwierdził **6/6 WYELIMINOWANY** — pełne domknięcie mikro-luki 2C.2 z 9.7 (`Adresat: <RZECZYWISTA_ETYKIETA_MĘSKA_P1_1> (MASCULINE)` w `ID: 58`, `0` wystąpień `Boy (FEMININE)`, `0` wystąpień `Grupa_1os_lm: NON_VIRILE` na mówcach męskich w `ID: 36–60`) oraz utrzymanie 5 regresji 9.5/9.6/9.7 (`2C.1`, `2C.3`, `2C.4`, `2A.1–2A.7`, higiena kursywy `ID: 187` i `ID: 26`).

Audyt architektoniczny Etapu 2/2 potwierdził spełnienie Zasad 1, 2, 3, 4 i 16 oraz zidentyfikował **3 zadania domykające dla wersji 9.9** (`Prompt_9.9.md`):
1. **Zasada 8 — CZĘŚCIOWO:** `TEST 222` (`test_standard_9_8_suite` w `test_system.py:19506-19550`) nie posiada `@pytest.mark.parametrize` (naruszenie D4), a licznik końcowy w `test_system.py:19777` wypisuje `(221/221)` zamiast `(222/222)`.
2. **Zasada 8 + MAIN.PY Scope Deviation — CZĘŚCIOWO:** `main.py:349-350` (`--subs`), `main.py:384-385` (`KEEP_HONORIFICS` przy `!sys.stdin.isatty()`) oraz `translator.py:6174-6176` (`if __name__ == "__main__": from main import main; main()`) nie mają testu jednostkowego ani wpisu w Tabeli P0.2 (scope deviation poza `Prompt_9.8.md`).
3. **Zasada 4 — ryzyka brzegowe w `translator.py`:** (a) brak symetrii `FEMALE` w `_precompute_episode_scene_genders` (`translator.py:1948-1956`, `2019-2034`) — pojedyncza kwestia jawnej postaci żeńskiej P0/P1 mówiącej w sekwencji oznaczonej jako `male_only_scene: True` otrzyma `scene_genders[orig_idx] == "mężczyzna"`; (b) `has_male_participant_in_line` w `translator.py:3265-3277` i `4099-4116` łączy płeć mówcy z płcią adresata, przez co mówczyni żeńska reprezentująca grupę kobiecą (`We_Group`) do pojedynczego adresata męskiego otrzymuje `Grupa_1os_lm: VIRILE` zamiast `NON_VIRILE`.
```