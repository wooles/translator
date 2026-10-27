# PROMPT NAPRAWCZY POTOKU AVT — DEPURACJA LEGACY 1.0

## PREAMBUŁA

Dokument definiuje operację depuracji pakietu testowego i martwego kodu w potoku AVT po wdrożeniu 9.3. Cel operacji: skrócenie czasu wykonania `pytest` z 36 minut do < 60 sekund w trybie domyślnym, przy jednoczesnym zachowaniu pokrycia testowego dla wszystkich aktywnych invariantów architektury (Standard 7 → 9.3). Dokument przestrzega Standardu 9.0 (Zero-Literal, Pure Positive Domain, Primary LLM Translation Authority, Instance-Free Metalinguistic Architecture) i Standardu 9.3 (Phase 0, sekcja 2A/2B/2C, testy jako wzorce strukturalne).

**Zasada nadrzędna bezpieczeństwa:** usuwanie testów i kodu następuje wyłącznie na podstawie **dowodu empirycznego** (Phase 0 audyt per-test / per-branch / per-rule). Klasyfikacja „prawdopodobnie legacy" jest niewystarczająca. Brak pewności → ARCHIVE lub MANUAL_REVIEW, nie DELETE.

Numer wersji: Depuracja 1.0. Poprzednia wersja promptu operacyjnego: 9.3 (autorytet dla aktywnych invariantów — testy pilnujące invariantów 9.3 są chronione przed usunięciem).

## IDENTYFIKATORY METAJĘZYKA ARCHITEKTURY

**Nazwy modułów:** `avt_linter.py`, `verifier.py`, `translator.py`, `series_memory.py`, `scene_discourse.py`, `profiler.py`, `metadata.py`, `rules.py`, `flight_recorder.py`, `sign_detector.py`, `test_system.py`, `tests/`.

**Nazwy klas i funkcji:** `AVTLinter`, `EpisodeQualityGate`, `EpisodeFlightRecorder`, `DialogueVerifier`, `SeriesBible`, `EpisodeProfiler`, `SceneDiscourseGraph`, `RuleDispatcher`, `VisualSignDetector`, `lint_and_fix_line`, `audit_and_fix_entire_episode`, `_run_phase_7_hygiene`, `normalize_ass_tags_and_sign_layout`, `should_apply_top_alignment_on_collision`, `arbitrate_event_telemetry`, `_guard_phase2_regressions`, `verify_batch`, `enforce_sign_nominative_orthography`, `_sanitize_loaded_bible_in_ram`, `sync_verified_profile_entity`, `profile_episode`, `sanitize_event_asr`, `get_active_rules`.

**Enumy i flagi:** `strict_positive_domain`, `IDENTITY PASS-THROUGH`, `MALE`, `FEMALE`, `UNKNOWN`, `MASCULINE`, `FEMININE`, `VIRILE`, `NON_VIRILE`, `POLYLOGUE`, `is_sign`, `is_internal_monologue`, `has_verified_gender`, `priority`, `confidence`, `P0`, `P1`, `P2`, `slow`, `unit`, `integration`, `e2e`, `network`.

**Znaczniki formatu ASS:** `[Script Info]`, `[V4+ Styles]`, `[Events]`, `\N`, `\n`, `{\...}`, `\an7`, `\an8`, `\an9`, `\pos`, `\i1`, `\i0`, `\3c`, `\bord`, `\shad`, `\blur`.

**Kategorie klasyfikacji testów (nowe w Depuracji 1.0):** `KEEP` (test aktywny, szybki, chroni invariant — zostaje), `MARK_SLOW` (test aktywny, wolny — zostaje z adnotacją `@pytest.mark.slow`), `ARCHIVE` (test podejrzany o legacy — przenoszony do `tests/archive/` poza domyślnym `pytest.ini`, z zachowaniem pliku), `DELETE` (test udowodniony jako dead — usuwany), `MANUAL_REVIEW` (wymaga decyzji użytkownika — nie usuwany automatycznie).

**Kategorie klasyfikacji dead code (nowe w Depuracji 1.0):** `DEAD_TRULY` (nigdy nieosiągalny w produkcyjnym CLI/API/testach — usunąć), `DEAD_ORPHANED` (osiągalny tylko przez testy DELETE — usunąć razem z testami), `DEFENSIVE_FALLBACK` (osiągalny w scenariuszu awaryjnym — zostawić), `RUNTIME_ALTERNATE` (osiągalny w trybie CLI alternatywnym — zostawić, chyba że tryb jest wycofany).

**Kategorie klasyfikacji reguł (nowe w Depuracji 1.0):** `ACTIVE` (reguła aktywna w bieżącym prompcie F1/F2 — zostawić), `OBSOLETE` (reguła nieaktualna wobec Standardu 9.3 — usunąć z rules.py i z testów), `SUPERSEDED` (reguła zastąpiona nowszą — usunąć starszą), `CONFLICT` (reguła sprzeczna z nowszą — usunąć starszą, zachować nowszą).

**Elementy infrastruktury testowej:** `pytest`, `pytest.ini`, `pyproject.toml`, `@pytest.mark.slow`, `@pytest.mark.network`, `-m "not slow and not network"`, `--durations`, `--collect-only`, `pytest-xdist`, `-n auto`.

**Konkretne artefakty testowe:** `tests/test_avt_linter.py`, `tests/test_verifier.py`, `tests/test_series_memory.py`, `tests/test_discourse_and_translator.py`, `tests/test_metadata.py`, `tests/test_profiler.py`, `tests/test_translator.py`, `tests/test_flight_recorder.py`, `test_system.py`, `verify_purity.py`, `verify_ultimate_pipeline.py`, `verify_12_fixes.py`, `audit_diff.ps1`.

**Ścieżka artefaktów:** `C:\Users\Piotrek\Desktop\translator\Artefakty\`.

## FAZA 0 — AUDYT PRZED JAKĄKOLWIEK ZMIANĄ (OBOWIĄZKOWA)

### 0.1. Pliki do przeczytania w całości

- `test_system.py` — wszystkie 217 testów.
- `avt_linter.py` — wszystkie gałęzie `if not strict_positive_domain` (grep `strict_positive_domain`).
- `rules.py` — wszystkie definicje filarów (grep `[Filar `).
- `pytest.ini`, `pyproject.toml` — konfiguracja testów.
- `tests/test_*.py` — czy są już markery `slow` / `network`.

### 0.2. Tabela P0.A — Audyt per-test (obowiązkowy)

Dla każdego z 217 testów w `test_system.py` wypełnij wiersz:

| ID | Nazwa testu | Co testuje (metoda/klasa) | Czy testowana metoda jest aktywna w `strict_positive_domain=True` | Czy test uruchamia: (a) model Whisper, (b) ffmpeg, (c) DSP, (d) API Gemini/network, (e) inny zasób ciężki | Chroni invariant P0 z 9.3 (tak/nie — który) | Klasyfikacja KEEP / MARK_SLOW / ARCHIVE / DELETE / MANUAL_REVIEW | Uzasadnienie |
|---|---|---|---|---|---|---|---|---|

### 0.3. Tabela P0.B — Audyt per-branch dead code (obowiązkowy)

Dla każdej gałęzi `if not strict_positive_domain` w `avt_linter.py` (grep) wypełnij wiersz:

| ID | Plik | Linia | Gałąź / funkcja | Osiągalna w produkcyjnym CLI/API? | Osiągalna w testach? Których? | Klasyfikacja DEAD_TRULY / DEAD_ORPHANED / DEFENSIVE_FALLBACK / RUNTIME_ALTERNATE | Uzasadnienie |
|---|---|---|---|---|---|---|---|

### 0.4. Tabela P0.C — Audyt per-rule rules.py (obowiązkowy)

Dla każdego filaru w `rules.py` (grep `[Filar `) wypełnij wiersz:

| ID | Numer filaru | Nazwa filaru | Aktywny w prompcie F1/F2? (grep w `build_phase1_prompt`, `_build_phase2_prompt`) | Zgodny z Pure Positive Domain? | Zgodny ze Standardem 9.3? | Klasyfikacja ACTIVE / OBSOLETE / SUPERSEDED / CONFLICT | Uzasadnienie |
|---|---|---|---|---|---|---|---|

### 0.5. Tabela P0.D — Mapowanie plan ↔ kod

Dla każdej operacji z sekcji 2A/2B/2C wypełnij wiersz:

| Operacja | Metoda w planie | Metoda w kodzie | Zgodność sygnatury | Uwagi |
|---|---|---|---|---|

### 0.6. Wynik Phase 0

Raport z Phase 0 zawiera:
- Tabela P0.A (217 wierszy — audyt per-test).
- Tabela P0.B (wszystkie gałęzie `if not strict_positive_domain`).
- Tabela P0.C (wszystkie filary w rules.py).
- Tabela P0.D (mapowanie plan ↔ kod dla operacji 2A/2B/2C).
- Lista rozbieżności „plan mówi X, kod ma Y".
- **Podsumowanie klasyfikacji:** liczba testów KEEP / MARK_SLOW / ARCHIVE / DELETE / MANUAL_REVIEW; liczba gałęzi DEAD_TRULY / DEAD_ORPHANED / DEFENSIVE_FALLBACK / RUNTIME_ALTERNATE; liczba filarów ACTIVE / OBSOLETE / SUPERSEDED / CONFLICT.

**Bez wypełnionej Phase 0 nie wolno przejść do Sekcji 1.**

## SEKCJA 1 — OPERACJE (2A / 2B / 2C)

### 2A — Testy KEEP (bez nowych akcji)

Testy sklasyfikowane jako `KEEP` w Phase 0 tabeli P0.A pozostają w `test_system.py` lub `tests/` bez zmian. Ich walidacja pozostaje w mocy.

### 2B — Nowe operacje (Depuracja 1.0)

#### 2B.1 — Markowanie testów slow (`@pytest.mark.slow`)

- **Lokalizacja:** `test_system.py` (dla testów sklasyfikowanych jako `MARK_SLOW`), `pytest.ini` (konfiguracja markerów).
- **Decyzja:** NAPRAWIĆ.
- **Implementacja:**
  1. W `pytest.ini` dodaj sekcję `markers` z definicjami: `slow: wolne testy (Whisper/ffmpeg/DSP/network > 1s)`, `network: testy wymagające połączenia z API zewnętrznym`.
  2. W `test_system.py` dla każdego testu z klasyfikacją `MARK_SLOW` dodaj dekorator `@pytest.mark.slow` (i `@pytest.mark.network` jeśli test wywołuje API Gemini/AniList).
  3. W `pytest.ini` ustaw domyślne wykluczenie: `addopts = -m "not slow and not network"`.
- **Kryterium akceptacji:** `pytest` domyślnie uruchamia wyłącznie testy szybkie (< 60 s łącznie). `pytest -m slow` uruchamia wyłącznie testy slow. `pytest -m "slow or network"` uruchamia testy ciężkie.

#### 2B.2 — Archiwizacja testów ARCHIVE

- **Lokalizacja:** `tests/archive/` (nowy katalog), `pytest.ini` (wykluczenie `tests/archive/` z domyślnego runu).
- **Decyzja:** PRZENIEŚĆ (nie usuwać — archiwizacja z możliwością przywrócenia).
- **Implementacja:**
  1. Utwórz `tests/archive/`.
  2. Dla każdego testu z klasyfikacją `ARCHIVE` przenieś ciało testu do `tests/archive/test_legacy_<kategoria>.py` z jawnym komentarzem `# ARCHIVED in Depuracja 1.0 — reason: <uzasadnienie z Phase 0>`.
  3. W `pytest.ini` dodaj `norecursedirs = tests/archive` (lub równoważne).
- **Kryterium akceptacji:** `pytest` nie uruchamia testów z `tests/archive/`. Plik `tests/archive/test_legacy_*.py` istnieje i jest kompletny (można go przywrócić jedną komendą `cp`).

#### 2B.3 — Usunięcie testów DELETE

- **Lokalizacja:** `test_system.py` (dla testów sklasyfikowanych jako `DELETE` w Phase 0).
- **Decyzja:** USUNĄĆ.
- **Implementacja:**
  1. Dla każdego testu z klasyfikacją `DELETE` usuń ciało testu.
  2. W commit message wyraźnie: `DELETE: <nazwa testu> — reason: <uzasadnienie z Phase 0 tabeli P0.A>`.
- **Kryterium akceptacji:** testy `DELETE` nie istnieją w kodzie. Testy `KEEP`, `MARK_SLOW` i `ARCHIVE` pozostają.

#### 2B.4 — Usunięcie dead code DEAD_TRULY i DEAD_ORPHANED

- **Lokalizacja:** `avt_linter.py` (gałęzie `if not strict_positive_domain` sklasyfikowane jako `DEAD_TRULY` lub `DEAD_ORPHANED`).
- **Decyzja:** USUNĄĆ.
- **Implementacja:**
  1. Dla każdej gałęzi `DEAD_TRULY` usuń cały blok `if not strict_positive_domain: ...` (wraz z pustym `else` jeśli istnieje).
  2. Dla każdej gałęzi `DEAD_ORPHANED` usuń blok razem z odpowiadającym testem sklasyfikowanym jako `DELETE`.
  3. Gałęzie `DEFENSIVE_FALLBACK` i `RUNTIME_ALTERNATE` **pozostają** — nie modyfikować.
- **Kryterium akceptacji:** `grep -n "strict_positive_domain" avt_linter.py` pokazuje wyłącznie wystąpienia w kontekstach `DEFENSIVE_FALLBACK` i `RUNTIME_ALTERNATE` (z komentarzem `# DEFENSIVE` lub `# RUNTIME`). Każde usunięcie ma dowód w Phase 0 tabeli P0.B.

#### 2B.5 — Odchudzenie rules.py (filar OBSOLETE / SUPERSEDED / CONFLICT)

- **Lokalizacja:** `rules.py` (definicje filarów sklasyfikowanych jako `OBSOLETE`, `SUPERSEDED`, `CONFLICT` w Phase 0 tabeli P0.C).
- **Decyzja:** USUNĄĆ (starsze), ZACHOWAĆ (nowsze).
- **Implementacja:**
  1. Dla każdego filaru `OBSOLETE` lub `SUPERSEDED` lub `CONFLICT` (starsza wersja) usuń definicję z `rules.py`.
  2. Usuń lub zaktualizuj testy pilnujące obecności usuniętych filarów (`test_*_pillars` z odpowiednimi asercjami).
  3. Zachowaj filary `ACTIVE` w całości.
- **Kryterium akceptacji:** w `rules.py` pozostają wyłącznie filary sklasyfikowane jako `ACTIVE`. Prompty F1/F2 (`build_phase1_prompt`, `_build_phase2_prompt`) nie odwołują się do usuniętych filarów. Testy `test_*_pillars` nie sprawdzają obecności usuniętych filarów.

### 2C — Konflikty z 9.3 (rozstrzygnięte)

Depuracja 1.0 jest operacją porządkową po 9.3, a nie modyfikacją architektury. **Żadna operacja z sekcji 2B nie modyfikuje zachowania potoku AVT** — testy `KEEP` i filary `ACTIVE` zachowują niezmienione działanie. Brak konfliktów z 9.3.

**Uwaga bezpieczeństwa:** jeżeli Phase 0 wykaże, że jakikolwiek test sklasyfikowany jako `KEEP` chroni invariant 9.3, ale jego treść jest sprzeczna z 9.3 (np. test oczekuje starego zachowania mutatora, który 9.3 wyłączył), to taki test przechodzi do klasyfikacji `MANUAL_REVIEW` — **nie jest usuwany automatycznie** — i wymaga decyzji użytkownika.

## SEKCJA 3 — REGUŁY PIPELINE'U DANYCH

Depuracja 1.0 nie modyfikuje pipeline'u danych (Kroki 0–11). Reguły R3.1–R3.5 z 9.3 pozostają niezmienione.

## SEKCJA 4 — KOLEJNOŚĆ WDROŻENIA

Kolejność wynika z zależności przyczynowych — audyt przed usunięciem, markowanie przed usuwaniem, testy przed kodem:

1. **Phase 0 — pełny audyt (tabele P0.A, P0.B, P0.C, P0.D).** Bez ukończonej Phase 0 nie wolno przejść dalej.
2. **2B.1 — markowanie `@pytest.mark.slow`.** Najpierw markujemy, potem usuwamy — żeby nie stracić pokrycia dla testów, które ostatecznie zostaną `KEEP`.
3. **2B.2 — archiwizacja `ARCHIVE`.** Odwracalna operacja — plik zostaje, przenoszony poza domyślny pytest.
4. **2B.5 — odchudzenie rules.py (filar `OBSOLETE`/`SUPERSEDED`/`CONFLICT`).** Przed usunięciem testów `DELETE`, bo część testów `DELETE` może pilnować usuniętych filarów.
5. **2B.4 — usunięcie dead code `DEAD_TRULY`/`DEAD_ORPHANED`.** Po 2B.5 — żeby usunięcie gałęzi `if not strict_positive_domain` nie uszkodziło filarów, które dopiero co usuwamy z rules.py.
6. **2B.3 — usunięcie testów `DELETE`.** Ostatni krok — dopiero po pełnym audycie i po usunięciu kodu, który te testy pilnowały.

**Ryzyko regresji przy każdej zmianie:** jeżeli po którymkolwiek kroku `pytest -m "not slow and not network"` zwraca FAILED, krok jest wycofywany i wracamy do Phase 0.

## SEKCJA 5 — WALIDACJA TESTOWA I WARUNEK UKOŃCZENIA

### 5A — Walidacja testowa

**Cel:** domyślny `pytest` < 60 s; pełny `pytest -m ""` (wszystkie testy) nadal 100% PASSED.

**Kryteria akceptacji:**
- (a) `pytest` (domyślnie, z `pytest.ini` wykluczającym `slow` i `network`) — < 60 s łącznie, 100% PASSED, 0 FAILED, 0 ERROR.
- (b) `pytest -m "not slow and not network"` — to samo co (a).
- (c) `pytest -m slow` — uruchamia wyłącznie testy `MARK_SLOW`, 100% PASSED.
- (d) `pytest -m network` — uruchamia wyłącznie testy sieciowe, 100% PASSED.
- (e) `pytest -m ""` (wszystkie) — 100% PASSED, 0 FAILED, 0 ERROR.
- (f) `git diff --stat` potwierdza: brak zmian w `.ass`, `.srt`, `*_bible.json`.
- (g) `verify_purity.py`, `verify_ultimate_pipeline.py`, `verify_12_fixes.py` — PASS 100%.
- (h) `audit_diff.ps1` — VICTORY CONFIRMED.
- (i) Każdy test usunięty (`DELETE`) ma dowód w Phase 0 tabeli P0.A.
- (j) Każda gałąź usunięta (`DEAD_TRULY`/`DEAD_ORPHANED`) ma dowód w Phase 0 tabeli P0.B.
- (k) Każdy filar usunięty (`OBSOLETE`/`SUPERSEDED`/`CONFLICT`) ma dowód w Phase 0 tabeli P0.C.
- (l) Testy `KEEP` chroniące invarianty P0 z 9.3 pozostają w kodzie (grep).

### 5B — Obowiązek wypełnienia Raportu Wdrożenia

Agent kodujący po zakończeniu zmian wypełnia wszystkie pola `<DO_WYPEŁNIENIA_PRZEZ_AGENTA_KODUJĄCEGO>` w `C:\Users\Piotrek\Desktop\translator\Artefakty\Raport_wdrozenia_Depuracja_1.0.md` i zapisuje pod tą samą ścieżką.

## SEKCJA 6 — ŚCIEŻKA ARTEFAKTÓW

- Prompt: `C:\Users\Piotrek\Desktop\translator\Artefakty\Prompt_Depuracja_Legacy_1.0.md`
- Raport: `C:\Users\Piotrek\Desktop\translator\Artefakty\Raport_wdrozenia_Depuracja_1.0.md`
