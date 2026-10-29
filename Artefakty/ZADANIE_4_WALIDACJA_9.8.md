# Plik: C:\Users\Piotrek\Desktop\translator\Artefakty\ZADANIE_4_WALIDACJA_9.8.md

# ZADANIE 4: WALIDACJA TESTOWA PROMPTU NAPRAWCZEGO 9.8 (ORAZ AKTUALIZACJA RAPORTU 9.7)

## 4.1. Rekord „Infrastruktura testowa"
- **`pliki_testowe`:** `tests/test_avt_linter.py`, `tests/test_verifier.py`, `tests/test_series_memory.py`, `tests/test_discourse_and_translator.py`, `tests/test_metadata.py`, `tests/test_profiler.py`, `tests/test_translator.py`, `tests/test_flight_recorder.py`, `test_system.py` (stan po Depuracji 1.0 i wdrożeniu 9.7: 204 testy domyślne w trybie fast + 153 testy `MARK_SLOW`, łącznie 357 testów bazowych).
- **`pliki_testowe_archived`:** `tests/archive/test_legacy_manifest.py` (katalog istnieje, wykluczony przez `norecursedirs` w `pytest.ini`, 0 testów archiwalnych).
- **`framework`:** `pytest`.
- **`komenda_fast`:** `pytest` (z `addopts = -v --tb=short -m "not slow and not network"`, 204 testy bazowe, ~22,84 s).
- **`komenda_full`:** `pytest -m ""` (357 testów bazowych).
- **`komenda_slow`:** `pytest -m slow` (153 testy).
- **`komenda_network`:** `pytest -m network` (12 testów).
- **`markery`:** `slow`, `network`, `unit`.
- **`bramki_ci_cd`:** `verify_purity.py`, `verify_ultimate_pipeline.py`, `verify_12_fixes.py`, `audit_diff.ps1`.

---

## 4.2. Rekord „Stan bazowy (przed modyfikacjami 9.8)"
- **Stan bazowy (fast):**
  - **`komenda`:** `pytest`
  - **`status`:** punkt odniesienia z końca wdrożenia 9.7, commit `1e27a17`: `204 PASSED, 153 deselected w 22.84 s`, `0 FAILED`, `0 ERROR`.
- **Stan bazowy (full):**
  - **`komenda`:** `pytest -m ""`
  - **`status`:** punkt odniesienia z końca wdrożenia 9.7, commit `1e27a17`: `357 PASSED`, `0 FAILED`, `0 ERROR`.

---

## 4.3. Rekord „Nowe testy"
Pełny szkielet testu T8.1 znajduje się w pliku `Prompt_9.8.md` → Sekcja 5 → Wykaz nowego testu T8.1 (marker: unit).

---

## 4.4. Rekord „Stan końcowy (po modyfikacjach 9.8)"
- **Stan końcowy (fast):**
  - **`komenda`:** `pytest` (oczekiwane: 204 bazowe instancje testowe + $\ge 2$ nowe instancje z `T8.1` = $\ge 206$ PASSED, `0 FAILED`, `0 ERROR`, czas $< 60\text{ s}$).
  - **`status`:** do wykonania w środowisku deweloperskim (`<DO_WYPEŁNIENIA_STAN_KOŃCOWY>`).
- **Stan końcowy (full):**
  - **`komenda`:** `pytest -m ""` (oczekiwane: 357 bazowych instancji testowych + $\ge 2$ nowe instancje z `T8.1` = $\ge 359$ PASSED, `0 FAILED`, `0 ERROR`).
  - **`status`:** do wykonania w środowisku deweloperskim (`<DO_WYPEŁNIENIA_STAN_KOŃCOWY>`).

---

## 4.5. Raport z walidacji (dwie tabele mapowania: fast + full)

### Tabela 4.5.A — Mapowanie walidacji w trybie `komenda_fast` (`pytest`)
| ID testu | Punkt Sekcji 2 | Plik testowy | Nazwa testu | Kategoria markera | Wynik w `komenda_fast` |
|---|---|---|---|---|---|
| **T8.1** | `2C.1` | `tests/test_discourse_and_translator.py` | `test_secondary_lexical_gender_immunity_against_scene_gender_override_and_male_speaker_non_virile_ban` | `unit` | do wykonania w środowisku deweloperskim |

### Tabela 4.5.B — Mapowanie walidacji w trybie `komenda_full` (`pytest -m ""`)
| Zakres pakietu | Liczba testów | Kategoria markerów | Kryterium akceptacji | Wynik w `komenda_full` |
|---|---:|---|---|---|
| Istniejące testy `KEEP` z Depuracji 1.0 + testy wersji 9.4–9.7 (`tests/` + `test_system.py`) | 204 | `unit` | 100% PASSED, 0 usuniętych testów (brak D6.e) | do wykonania w środowisku deweloperskim |
| Istniejące testy `MARK_SLOW` z Depuracji 1.0 (`test_system.py`) | 153 (w tym 12 `network`) | `slow` / `network` | 100% PASSED, markery zachowane (brak D6.d) | do wykonania w środowisku deweloperskim |
| Nowy test wersji 9.8 (`T8.1`) | $\ge 2$ instancje (1 funkcja) | `unit` | 100% PASSED, 100% falsyfikowalności, wolny od D1–D6 | do wykonania w środowisku deweloperskim |
| **RAZEM (`komenda_full`)** | **$\ge 359$** | `unit` + `slow` + `network` | **100% PASSED, 0 FAILED, 0 ERROR** | do wykonania w środowisku deweloperskim |

---

## 4.6. Rekord „Ocena niedegradacyjności"
Wzorzec testowy `T8.1` spełnia jednocześnie pięć warunków Zasady 8 (a)–(e) oraz jest wolny od anty-wzorców D1–D6:
- **`test`:** `T8.1`.
- **`kategoria`:** ogólna kategoria zachowania architektonicznego (niezmienność płci leksykalnej etykiet osobowych P1 `Boy`/`Girl` wobec arbitrażu akustyczno-scenicznego `audit_speaker_metadata_against_audio` oraz blokada kategorii `NON_VIRILE` w obecności mówcy męskiego).
- **`źródło_oczekiwanej_wartości`:** wyłącznie semantyka leksykalna etykiety w sekcji `[Events]` oraz rekord P0/P1 w `SeriesBible`.
- **`falsyfikowalność`:** 100% (przywrócenie kodu z 9.7 powoduje `FAILED` na `T8.1`).
- **`parametryzacja`:** dekorator `@pytest.mark.parametrize` z $\ge 2$ przypadkami wejściowymi.
- **`status_D1_D6`:** wolny od D1–D6 (w tym D6.a–D6.e).
- **`kategoria_markera`:** `unit`.

---

## 4.7. Rekord „Mechanizmy degradacji w nowych testach (D1–D6)"
- **D1 (Placeholder leakage):** ZABEZPIECZONY — test używa placeholderów `<RZECZYWISTA_*>`, których wypełnienie danymi spoza odcinka audytowanego wymusza Tabela P0.3.
- **D2 (Tautologia):** WYELIMINOWANY — test wywołuje rzeczywiste metody produkcyjne `SeriesBible.populate_secondary_actor_tags`, `SeriesBible.audit_speaker_metadata_against_audio` oraz `SceneDiscourseGraph.arbitrate_event_telemetry`.
- **D3 (Snapshot regression):** WYELIMINOWANY — asercje oparte na niezmiennikach kategorycznych (`has_verified_gender is True`, `is_cont is False`, `target_gender == expected_telemetry_gender`).
- **D4 (Brak parametryzacji):** WYELIMINOWANY — test `T8.1` posiada `@pytest.mark.parametrize` z 2 wariantami.
- **D5 (Instance verification):** WYELIMINOWANY — test weryfikuje ogólne prawa strukturalne.
- **D6 (Restore of legacy — D6.a do D6.e):** WYELIMINOWANY — pełne zachowanie stanu Depuracji 1.0 (`204 fast`, `153 slow`, `12 network`, `tests/archive/` nietknięty, 3 gałęzie `# DEFENSIVE_FALLBACK` nietknięte).

---

## 4.8. Rekord „Mechanizmy degradacji w istniejącym pakiecie"
- Pakiet 204 testów fast i 357 testów full po wersji 9.7 jest w 100% stabilny (`22.84 s`).
- Test `T7.2` w wersji 9.7 weryfikował `populate_secondary_actor_tags` i `arbitrate_event_telemetry` w izolacji, lecz nie wywoływał pośredniczącej metody `SeriesBible.audit_speaker_metadata_against_audio(..., scene_gender="FEMALE")` używanej w runtime przez `_resolve_line_addressee`. Nowy test `T8.1` bezpośrednio zamyka tę lukę.

---

## 4.9. Raport z niedegradacyjności

| Test | Kategoria zachowania | Źródło oczekiwanej wartości | Falsyfikowalność | Niezależność od instancji | Mechanizm degradacji |
|---|---|---|---|---|---|
| `T8.1` (`test_secondary_lexical_gender_immunity_against_scene_gender_override_and_male_speaker_non_virile_ban`) | Nienaruszalność płci leksykalnej etykiet drugoplanowych P1 (`Boy`/`Girl`) wobec `audit_speaker_metadata_against_audio` i `scene_female_only=True` | Sekcja `[Events]` + `SeriesBible` | tak | tak ($\ge 2$ wejścia, placeholdery) | brak (wolny od D1–D6) |

---

## 4.10. Aktualizacja statusu i Sekcji 12 w `Raport_wdrozenia_9.7.md`

W pliku `C:\Users\Piotrek\Desktop\translator\Artefakty\Raport_wdrozenia_9.7.md`:

1. **W Sekcji 1 (`METADANE PODSTAWOWE`) zaktualizuj pola:**
   - `Commit wdrożenia: 1e27a17 (feat(pipeline): Wdrozenie Standardu 9.7)`
   - `Status wdrożenia: FORMALNIE WDROŻONE (204/204 fast, 357/357 full, 4 bramki PASS), 3/4 KATEGORII WYELIMINOWANE W 100%, 1 MIKRO-LUKA W 2C.2 (ID: 58) — domknięcie w 9.8`

2. **W Sekcji 6C w wierszu `Kategoria Problemu 2` (`2C.2`) zaktualizuj status na:**
   `CZĘŚCIOWO (poprawne MALE/FEMALE w Kroku 6 i ID: 59–60, lecz w ID: 58 audit_speaker_metadata_against_audio nadpisało płeć Boy przez brak has_verified_gender: True)`

3. **Na końcu `Raport_wdrozenia_9.7.md` wklej 1:1 poniższą Sekcję 12 (`UWAGI AUDYTOWE PO WERYFIKACJI EMPIRYCZNEJ 9.7`):**

```markdown
## 12. UWAGI AUDYTOWE PO WERYFIKACJI EMPIRYCZNEJ 9.7

Audyt empiryczny pary plików `post97.ass` + `post97_full_trace.log` oraz logu konsolowego `przebieg_tłumaczenia_post97.txt` (Etap 1/2 i Etap 2/2) potwierdził stuprocentowe wyeliminowanie regresji krytycznej z operacji `2C.1` (`0` duplikacji członów dwuczłonowych antroponimów P0 w `ID: 48` i `ID: 52`, tożsamość `ass_text == dpos_text` oraz selektywne przypisanie aliasów z tytułu wyłącznie do 1 pasującej fonetycznie encji P0 w Kroku 6), a także pełne wyeliminowanie problemów `2C.3` (`0` pustych wpisów `[Redaktor Dialogów]` dla linii różniących się wyłącznie zamianą spacji na `\N`) oraz `2C.4` (`0` artefaktów `.? ??000` w segmencie ASR w `ID: 79`). Jednocześnie zidentyfikowano **1 mikro-lukę w runtime w operacji `2C.2`**, przekazaną do domknięcia w wersji **9.8** (`Prompt_9.8.md`):

1. **Nadpisanie płci leksykalnej etykiety `Boy` w `ID: 58` oraz wymuszenie `NON_VIRILE` na liniach mówców męskich (`2C.1` w 9.8):** W `SeriesBible.populate_secondary_actor_tags` etykiety o jednoznacznym znaczeniu płciowym (`Boy`, `Girl`) otrzymały `"has_verified_gender": False`, przez co wywołana w `_resolve_line_addressee` metoda `audit_speaker_metadata_against_audio("Boy", ..., scene_gender="FEMALE")` nadpisała w pamięci RAM płeć `"Boy"` na `"FEMALE"` (emitując `Adresat: Boy (FEMININE)` w `ID: 58`), natomiast flaga `female_only_scene: True` z pre-passu sekwencji wymusiła `Grupa_1os_lm: NON_VIRILE` na liniach `ID: 36–60` wypowiadanych przez mówców męskich (`MASCULINE`).
```