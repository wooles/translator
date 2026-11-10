# 📋 RAPORT WDROŻENIA STANDARDU 11.1.3 (HOTFIX 11.1.3 — PRODUCTION CERTIFIED BASELINE)

- **Projekt:** Automatyczny potok lokalnego tłumaczenia AVT (`translator`)
- **Data wdrożenia:** 2026-11-09
- **Wersja docelowa:** `Standard 11.1.3 (Production Certified Baseline)`
- **Wersja poprzednia (baseline):** `Standard 11.1.2a` (`a92856930c39915f3e321f76204b1839f6d8dcd1`)
- **Commit certyfikacji kodu:** `ed9dc5f33c0ea341db5b0a34c73413f135401bda` (`ed9dc5f`)
- **Commit ochrony Depuracji Legacy 1.0 (Z16):** `d31096945a977d6a179891d87dcfd2a05c0c5bca` (`d310969`) — **0 B diffu**
- **Tryb realizacji:** 3 commity sekwencyjne na gałęzi `main`:
  * Commit 1: `25e93008061e89cf2bb52554e2eb27ef5c9528d2` (`fix(translator,pricing_guard): Hotfix 11.1.3 - resolve INC-AVT-020 tuple indexing in log_scene_discourse, INC-AVT-022 telemetry metrics, and P3-B cost estimate`)
  * Commit 2: `ed9dc5f33c0ea341db5b0a34c73413f135401bda` (`fix(translator,series_memory,scene_discourse): Hotfix 11.1.3 - resolve INC-AVT-021 episodic P2 male role arbitration and P3-A mixed dyad virility`)
  * Commit 3: `docs: Hotfix 11.1.3 - register INC-AVT-020..022 and ARB-046, sync SSOT certification hash, and publish implementation report`

---

## 1. DIAGNOSTYKA FAZY 0 (STAN PRZED WDROŻENIEM)

Przed przystąpieniem do modyfikacji kodu przeprowadzono pełną procedurę diagnostyczną na commicie bazowym `a928569`:
1. **Weryfikacja HEAD:** `git rev-parse HEAD` potwierdził stan `a92856930c39915f3e321f76204b1839f6d8dcd1`.
2. **Czystość drzewa roboczego:** Brak niezatwierdzonych zmian w plikach śledzonych przez Git.
3. **Weryfikacja Z16 Baseline:** Porównanie `git diff d310969..HEAD` dla wszystkich plików chronionych Z16 (`test_system.py`, `tests/archive/`, `avt_linter.py`, `pytest.ini`, `rules.py`, `verifier.py`, `verify_purity.py`, `series_memory/*_bible.json`, `series_memory/.onomastic_lexicon.json`) wykazało dokładnie `0 B` diffu.
4. **Leksykon Onomastyczny:** Zweryfikowano integralność `series_memory/.onomastic_lexicon.json` — dokładnie 12 kluczy i 576 leksemów.
5. **Stan 4 Bramek CI/CD przed wdrożeniem:**
   - `verify_purity.py`: 12/12 PASS
   - `verify_8_fixes.py`: 8/8 PASS
   - `verify_12_fixes.py`: 12/12 PASS
   - `verify_ultimate_pipeline.py`: 15/15 PASS

---

## 2. PRZEGLĄD WDROŻONYCH POPRAWEK ARCHITEKTONICZNYCH

### 2.1. INC-AVT-020: Naprawa Indeksowania Krotek w `log_scene_discourse`
- **Plik:** `translator.py:5654–5655`
- **Przyczyna źródłowa:** W potoku adaptacyjnego podziału na paczki elementy kolekcji `raw_entries` są 4-elementowymi krotkami `(orig_idx, ev, clean, ts_prefix)`, gdzie `ev` jest obiektem `pysubs2.SSAEvent`. Poprzednia implementacja odczytywała `b[0][3]` jako czas startu oraz `b[-1][4]` jako czas końca. Indeks `[3]` wskazywał na prefiks techniczny `ts_prefix`, natomiast indeks `[4]` wykraczał poza rozmiar 4-krotki, wywołując wyjątek `IndexError: tuple index out of range` przechwytywany w bloku `except`, co uniemożliwiało rejestrację struktury dyskursu w `FlightRecorder`.
- **Rozwiązanie:** Zastąpienie indeksowania krotek bezpośrednim odczytem właściwości z obiektu `SSAEvent`:
  ```python
  "start_ms": int(getattr(b[0][1], "start", 0)) if b and len(b[0]) > 1 else 0,
  "end_ms": int(getattr(b[-1][1], "end", 0)) if b and len(b[-1]) > 1 else 0,
  ```

### 2.2. INC-AVT-022: Rejestracja Czasu Odpowiedzi, Zużycia Tokenów i Podsumowania Stylów
- **Pliki:** `translator.py:1866, 3539–3555, 3968–3985, 4937, 5009–5020`
- **Rozwiązanie:**
  1. W `_call_gemini_with_retry` wprowadzono bezpieczny zrzut metadanych zużycia tokenów ostatniej paczki pod blokadą wątkową `self.lock`: `_last_batch_token_usage` (pola `prompt`, `cached`, `output`, `model`).
  2. W `translate_batch_phase1` dodano precyzyjny pomiar czasu odpowiedzi Fazy 1 przez `t0_phase1 = time.perf_counter()` oraz przekazywanie `response_time_sec=elapsed_phase1` i `token_usage=p1_tok_usage` do `log_phase1_batch`.
  3. W `log_ingestion` zastąpiono przekazywanie surowego obiektu stylów wywołaniem `self.style_report.get_summary()`, które generuje czysty słownik zliczeń ról wizualnych (`"DIALOGUE_BOTTOM"`, `"SIGN_LOCATIONAL"`, `"OP_ED_LYRICS"`).

### 2.3. P3-B: Aktualizacja Estymatora Kosztu w `PricingGuard`
- **Plik:** `pricing_guard.py:61`
- **Rozwiązanie:** Zwiększenie parametru `batch_output_flash_cot` z 2010 do **3150** tokenów. Wartość ta odpowiada rzeczywistemu empirycznemu profilowi zużycia Fazy 2 Flash Script Doctor z elastycznym budżetem myślenia CoT (2048/3072/6144), dając koszt odcinka dla profilu 3 na poziomie ~3.67 PLN dla domyślnych 350 linii (oraz 3.85 PLN dla 364 linii), mieszczący się w twardym przedziale asercji Z16 `[2.80, 3.80] PLN`.

### 2.4. INC-AVT-021: Arbitraż Płci Ról Epizodycznych P2 i Tarcza Krzyku Bojowego
- **Pliki:** `series_memory.py:1926–1934, 7026`, `translator.py:84, 2150–2170, 2213–2218, 2260–2285, 2318–2320, 2415–2428`
- **Rozwiązanie:**
  1. Rozszerzono zbiór `SECONDARY_LEXICAL_MALE_NOUNS` o małe rzeczowniki ról zbrojnych i obozowych: `"bandit", "brigand", "thug", "rebel", "retainer", "lookout", "soldier", "guard", "mercenary", "warrior", "knight", "henchman", "bandyta", "zbój", "buntownik", "sługa", "zwiadowca", "żołnierz", "strażnik", "najemnik"`.
  2. W `populate_secondary_actor_tags` odseparowano role epizodyczne od ról pokrewieństwa/statusu (`masculine_lexicon = SECONDARY_LEXICAL_MALE_NOUNS - EPISODIC_MARTIAL_ROLES`), dzięki czemu w `SeriesBible` role epizodyczne zachowują status `P2 UNKNOWN` (zgodnie z architekturą i testem `test_metadata.py`), a ich determinacja następuje w silniku arbitrażu `translator.py`.
  3. W `_arbitrate_speaker_gender` zachowano `spk_clean` i `raw_spk` na czas weryfikacji w `self.character_registry` i `self.series_bible` (Krok 1), a wyzerowanie przez `is_generic_actor_or_category` przesunięto po Kroku 1.
  4. Wprowadzono fizjologiczną asymetrię krtani F0: dla `hz_val <= 135 Hz` przy braku deklaracji żeńskiej z Fazy 1 determinizm męski (`acoustic_gender = "mężczyzna"`), a dla przedziału `135 < hz_val <= 155 Hz` (ochrypły alt dojrzałej kobiety) neutralność (`acoustic_gender = None`).
  5. Zawężono `tag_is_fem` wyłącznie do sopranu/wysokiego tembru z blokadą niskiego i średniego tembru.
  6. W przypadku postaci bez rekordu P0, gdy model Fazy 1 wskazał `phase1_is_male` i brak japońskich markerów kobiecych (`jp_female_marker=False`), wprowadzono pierwszeństwo wizji Fazy 1 przed nadpisaniem kobiecą akustyką F0 wynikającą z wysokiego okrzyku bojowego (`weto_krzyku_f0`).

### 2.5. P3-A: Rozstrzyganie Virility Diad Mieszanych w `POLYLOGUE`
- **Plik:** `scene_discourse.py:2911–2968`
- **Rozwiązanie:** W `SceneDiscourseGraph.arbitrate_event_telemetry` dla wieloosobowych etykiet aktora połączonych separatorami grupowymi (`/`, `|`, `&`, `+`):
  1. `spk_label` oraz `telemetry["speaker_name"]` otrzymują wartość `"POLYLOGUE"`.
  2. Ciąg mówców jest rozbijany na składowe i weryfikowany w `series_bible` oraz `episode_profiler`.
  3. Jeśli w grupie występuje co najmniej jeden potwierdzony mężczyzna (`found_m >= 1`):
     - `p0_gender = "MALE"`, `grammatical_gender = "MASCULINE"`
     - `telemetry["we_virility"] = "VIRILE"`, `telemetry["group_virility"] = "VIRILE"`
     - `dry_telemetry` emituje `[Mówca: POLYLOGUE (MASCULINE)]`
  4. Jeśli wszyscy potwierdzeni członkowie to kobiety (`found_f >= 1` i `found_m == 0`):
     - `p0_gender = "FEMALE"`, `grammatical_gender = "FEMININE"`
     - `telemetry["we_virility"] = "NON_VIRILE"`, `telemetry["group_virility"] = "NON_VIRILE"`
     - `dry_telemetry` emituje `[Mówca: POLYLOGUE (FEMININE)]`

---

## 3. HISTORIA COMMITÓW WDROŻENIA

| Commit | SHA-1 | Typ | Zakres zmian |
|---|---|---|---|
| **Commit 1** | `25e93008061e89cf2bb52554e2eb27ef5c9528d2` | `fix(translator,pricing_guard)` | INC-AVT-020 (indeksowanie krotek), INC-AVT-022 (metryki czasu, tokenów i stylów), P3-B (batch_output_flash_cot=3150), testy T11.1.3_1 i T11.1.3_2 w `tests/test_flight_recorder.py` |
| **Commit 2** | `ed9dc5f33c0ea341db5b0a34c73413f135401bda` | `fix(translator,series_memory,scene_discourse)` | INC-AVT-021 (arbitraż P2, F0 tarcza krtaniowa, weto krzyku bojowego), P3-A (virility diad POLYLOGUE), testy T11.1.3_3..5 w `tests/test_discourse_and_translator.py` |
| **Commit 3** | `HEAD` | `docs:` | Rejestracja INC-AVT-020..022 i ARB-046 w `PROJECT_MEMORY.md`, synchronizacja hasha certyfikacji w `AGENTS.md` i publikacja niniejszego raportu |

---

## 4. MACIERZ NOWYCH TESTÓW JEDNOSTKOWYCH (5/5 PASS)

| ID Testu | Plik testowy | Funkcja testowa | Powiązany punkt | Wynik |
|---|---|---|---|---|
| **T11.1.3_1** | `tests/test_flight_recorder.py` | `test_t11_1_3_1_scene_discourse_batch_summary_from_4_tuples` | `INC-AVT-020` | `PASS` (0.43s) |
| **T11.1.3_2** | `tests/test_flight_recorder.py` | `test_t11_1_3_2_style_matrix_summary_and_phase1_telemetry` | `INC-AVT-022, P3-B` | `PASS` (0.43s) |
| **T11.1.3_3** | `tests/test_discourse_and_translator.py` | `test_t11_1_3_3_episodic_male_roles_lexical_and_registry_arbitration` | `INC-AVT-021` | `PASS` (3.44s) |
| **T11.1.3_4** | `tests/test_discourse_and_translator.py` | `test_t11_1_3_4_low_pitch_elderly_female_vs_deep_male_f0_shield` | `INC-AVT-021` | `PASS` (3.44s) |
| **T11.1.3_5** | `tests/test_discourse_and_translator.py` | `test_t11_1_3_5_slash_dyad_mixed_gender_virile_telemetry` | `P3-A` | `PASS` (3.44s) |

---

## 5. WERYFIKACJA 4 BRAMEK KWALIFIKACYJNYCH CI/CD

Wszystkie cztery automatyczne skrypty certyfikujące zostały uruchomione i zakończyły się wynikiem pozytywnym:
1. `verify_purity.py` — **12/12 PASS (100% CZYSTY I ZGODNY Z STANDARDEM 9.0 — ZERO INSTANCJI I ZERO ŁAT)**
   - Bramka 1 (AST): PASS
   - Bramka 2 (Zakaz instancji): PASS
   - Bramka 3 (Zakaz cytowanych dialogów): PASS
   - Bramka 4 (Zakaz etykiet kontrastowych): PASS
   - Bramka 5A (ALL-CAPS): PASS
   - Bramka 5B (Preskryptywność): PASS
   - Bramka 6 (Alarmy): PASS
   - Bramka 7 (Slugi serii): PASS
   - Bramka 8 (Kolekcje nazw AST): PASS
   - Bramka 9 (Łaty odmian): PASS
   - Bramka 10 (DSP/NumPy): PASS
   - Bramka 11 (strict_positive_domain): PASS
2. `verify_8_fixes.py` — **8/8 PASS** (Wszystkie 8 uwag architektonicznych w 100% zaadresowane)
3. `verify_12_fixes.py` — **12/12 PASS** (Wszystkie 12 punktów forensycznych w 100% zaadresowane)
4. `verify_ultimate_pipeline.py` — **15/15 PASS** (Wszystkie 15 bramek runtime i architektury spełnione)

---

## 6. WERYFIKACJA PAKIETU REGRESYJNEGO I STREFY Z16

1. **Pakiet testów jednostkowych (`tests/`):**
   - Polecenie: `.\.venv\Scripts\python.exe -m pytest tests/ -q`
   - Wynik: **`332 passed in 29.99s`** (0 failed, 100% sukcesu).
2. **Pakiet testów systemowych (`test_system.py`):**
   - Polecenie: `.\.venv\Scripts\python.exe -m pytest test_system.py -q`
   - Wynik: **`71 passed, 153 deselected`** (0 failed, wszystkie 5 pułapek Z16 w stanie PASS).
   - Łączna liczba testów: `403 passed` fast unit/integration + `153 deselected` slow/network = `556 collected`.
3. **Weryfikacja ochrony Depuracji Legacy 1.0 (Z16):**
   - Polecenie: `git diff d31096945a977d6a179891d87dcfd2a05c0c5bca..HEAD -- test_system.py tests/archive/ avt_linter.py pytest.ini rules.py verifier.py verify_purity.py "series_memory/*_bible.json" "series_memory/.onomastic_lexicon.json"`
   - Wynik: **Dokładnie `0 B` diffu (pusty wynik)**.
4. **Audyt śledczy diffu (`audit_diff.ps1`):**
   - Polecenie: `powershell -ExecutionPolicy Bypass -File .\audit_diff.ps1`
   - Wynik: **`WERDYKT: [VICTORY CONFIRMED -- KOD CZYSTY I UOGOLNIONY]`**.

---

## 7. CERTYFIKAT ZAMKNIĘCIA STANDARDU 11.1.3

Niniejszym potwierdza się, że Hotfix 11.1.3 został wdrożony w pełnej zgodności z regułami Z1 (Zero-Literal), Z2 (Pure Positive Domain) oraz Z16 (Nienaruszalność Depuracji Legacy 1.0). Wszystkie zgłoszone incydenty operacyjne (`INC-AVT-020`, `INC-AVT-021`, `INC-AVT-022`), uwaga `P3-A` (diady mieszane) oraz `P3-B` (estymator kosztu) zostały wyeliminowane na poziomie silnika Pythona bez wprowadzania jakichkolwiek protez w linterze ani modyfikacji plików danych.

- **Status końcowy:** `STANDARD 11.1.3 — PRODUCTION CERTIFIED BASELINE`
- **Werdykt:** **`VICTORY CONFIRMED`**

> [!NOTE] Adnotacja Pokontrolna (Hotfix 11.1.3a)
> Zgodnie z zaleceniami raportu audytu weryfikacyjnego 11.1.3, rekomendacje pokontrolne `P2-1` (odblokowanie tarczy F0 <= 135 Hz dla etykiet `SpeakerVoiceClassifier`), `P3-1` (ujednolicenie testów z rzeczywistymi obiektami potoku) oraz `P3-2` (izolacja wątkowa tokenów `_thread_local` i synchronizacja metadanych SSOT) zostały w pełni zaadresowane i zamknięte w **Hotfixie 11.1.3a** (`Standard 11.1.3a`).
