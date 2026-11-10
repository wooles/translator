# RAPORT AUDYTU OPERACYJNEGO — PRZEBIEG TŁUMACZENIA ODCINKA

**Plik docelowy:** `Artefakty/Raport_audytu_operacyjnego_2026-11-09.md`
**Kodowanie:** UTF-8 bez BOM
**Zgodność:** Z1 Zero-Literal, Z2 Pure Positive Domain

---

## Sekcja 0 — Metadane audytu

- **Data audytu:** 2026-11-09
- **Repozytorium referencyjne:** `https://github.com/wooles/translator` (gałąź `main`)
- **HEAD gałęzi `main`:** `a92856930c39915f3e321f76204b1839f6d8dcd1` (`a928569`)
- **Commit certyfikacji kodu / Baseline Z16:** `d31096945a977d6a179891d87dcfd2a05c0c5bca` (`d310969`)
- **Aktualny certyfikowany standard produkcyjny:** `Standard 11.1.2a (Production Certified Baseline)`
- **Identyfikator przebiegu tłumaczenia:** `20261108_171551` (start: `2026-11-08T17:15:51.806306`, koniec: `2026-11-08T17:25:37.014587`, czas całkowity: `9 min 45.21 s`)
- **Nazwa serii i odcinka (Z1 Zero-Literal):** `<SERIA>` (`<SERIA_SLUG>`), `<ODCINEK>` (364 zdarzenia napisów `.ass`)
- **Tryb audytu:** STRICTLY READ-ONLY (0 zmian w kodzie, 0 commitów, 0 push)

---

## Sekcja 1 — Inwentaryzacja załączników (Faza 0)

Wszystkie wymagane załączniki operatora (`Z1` oraz `Z2`, wraz z towarzyszącym plikiem telemetrii strukturalnej `.jsonl` oraz drzewem repozytorium na `HEAD = a928569`) zostały dostarczone i zweryfikowane pod kątem integralności oraz kodowania.

| # | Załącznik / Plik | Rozmiar (B) | Liczba linii | Kodowanie | BOM | Rozpoznane sekcje EpisodeFlightRecorder / Zawartość |
|---|---|---|---|---|---|---|
| Z1a | `..._20261108_171551_full_trace.log` | 150 562 B | 1 131 | UTF-8 | Brak (False) | `[KROK 1: CLI & INICJALIZACJA PROCESU]`, `[KROK 2: INGESTIA NAPISÓW I KLASYFIKACJA WIZUALNA]`, `[KROK 3: METADANE ZEWNĘTRZNE I NORMALIZACJA AKTORÓW]`, `[KROK 5: PROFILER ODCINKA PRE-PASS]`, `[KROK 6: PAMIĘĆ SERII SERIESBIBLE I PARADYGMATY ODMIANY]`, `[KROK 4: AKUSTYKA DSP, ESTYMACJA F0 I WHISPER ASR]` (x17), `[KROK 8: FAZA 1 - PIERWOTNE TŁUMACZENIE PRIMARY LLM]` (x17, paczki 0–16), `[KROK 9: FAZA 2 - WERYFIKACJA DIALOGUEVERIFIER]` + ewolucja linii `[ID: 0..363]` (x17, paczki 0–16), `[KROK 11: EPISODEQUALITYGATE I ROZLICZENIE FINANSOWE PRICINGGUARD]`, `ZAKOŃCZENIE PRZEBIEGU POTOKU AVT`. **Uwaga:** brak sekcji `[KROK 7: GRAF DYSKURSU SCENICZNEGO]` — zdiagnozowano w `EV-02`. |
| Z1b | `..._20261108_171551_events.jsonl` | 485 210 B | 421 | UTF-8 | Brak (False) | `cli_init` (1), `ingestion` (1), `metadata` (1), `profile_prepass` (1), `series_bible` (1), `acoustics_whisper` (17), `phase1_batch` (17), `phase2_verifier` (17), `line_evolution` (364), `quality_gate_and_pricing` (1). **Uwaga:** 0 rekordów `scene_discourse`. |
| Z2 | `..._pelny_przebieg_tlumaczenia.txt` | 53 062 B | 495 | UTF-8 | Brak (False) | Pełny zrzut konsoli stdout/stderr: inicjalizacja UI, sonda API, `StyleMatrixEngine`, Baza AniList, Profiler Odcinka, `Context Cache`, Kotoba-Whisper, FFmpeg Scene Cuts/Black Fades, logi 17 paczek Fazy 1 i Fazy 2, komunikat `504 Timeout` i rotacji klucza (L356–L357), korekta AVT Linter/Słownik (L457), podsumowanie `PricingGuard` (L482–L490). |
| Repo | `translator-a928569...` (archiwum referencyjne) | Kompletne drzewo | Wszystkie moduły `.py` | UTF-8 | Brak (False) | Kod referencyjny na `HEAD = a92856930c39915f3e321f76204b1839f6d8dcd1`. |

### Wykryte poziomy komunikatów w konsoli (Z2) i logu (Z1)

- **W konsoli (Z2):** komunikaty strukturalne potoku (`[Status / Faza 2]`, `[OK / Faza 2]`, `[AVT Linter/Słownik]`, `[Sukces]`). Brak surowych prefiksów `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` ani zrzutów `Traceback` w stdout/stderr.
- **W logu (Z1):** znaleziono jednak ciche wyciszenie wyjątku `IndexError` w bloku `log_scene_discourse` (`translator.py:5644`), ostrzeżenie modelu o błędnych tagach telemetrycznych płci (Z1:L774, Z2:L354) oraz retry warstwy HTTP `504 Timeout` (Z2:L356).

---

## Sekcja 2 — Podsumowanie wykonawcze

**Werdykt ogólny:** `ZGODNY Z ZASTRZEŻENIAMI`

### Statystyka zdarzeń

- **Nieprzechwycone wyjątki (`Traceback` w konsoli):** 0
- **Ciche wyjątki przechwycone wewnątrz loggera (K-EXC / K-DISCOURSE):** 1 (`IndexError` w `translator.py:5635` podczas przygotowania `batches_sum` dla `log_scene_discourse`)
- **Błędy / retry warstwy API (K-API / K-HEALING):** 1 (`504 Timeout` w Fazie 2 przy 65% postępu, obsłużony bezstratnie przez rotację klucza w `MultiKeyClientPool`)
- **Ostrzeżenia i anomalie telemetrii płci/profilu (K-PROFILE / K-DISCOURSE):** 27 linii (6 postaci epizodycznych / zbiorowych: `<POSTAC_BANDYTA_A>`, `<POSTAC_BANDYTA_B>`, `<POSTAC_BANDYTA_C>`, `<POSTAC_BUNT>`, `<POSTAC_SLUGA_B>`, `<POSTAC_ZWIADOWCA>` oraz diada `<POSTAC_SIOSTRA>`/`<POSTAC_BRAT>` otrzymały tag `FEMININE` w `telemetry_tag`)
- **Interwencje AVTLinter (D_pos) (K-LINTER):** 1 (korekta wołacza afrykatowego w linii `ID 318`: `<POSTAC_WASAL>ie` → `<POSTAC_WASAL>u`)
- **Interwencje EpisodeQualityGate (K-CPS / formatowanie):** 20 (2 kolizje czasowe `\an8`, 12 usunięć redundantnych tagów `{\i1}` w stylu Italics, 5 korekt higieny tekstu, 1 formatowanie planszy ekranowej)
- **Odchylenia kosztowe i telemetryczne (K-PRICE / K-INNE):** 3 (koszt 4.03 PLN netto powyżej estymacji UI 3.33 PLN; puste `style_matrix: {}` w Kroku 2; wyzerowane `response_time_sec: 0.0` i `token_usage: {}` w logach Fazy 1)

### Czy wystąpił jakikolwiek błąd wpływający na wyjściowy plik `.ass`?

**NIE.** Wszystkie 364 linie zostały przetłumaczone, zweryfikowane w Fazie 2 i zapisane do pliku wynikowego `.ass` (0 luk, 0 surowych linii EN). Mimo że 27 linii postaci epizodycznych otrzymało w `telemetry_tag` błędny znacznik (`FEMININE`), zarówno model Fazy 1, jak i weryfikator Fazy 2 prawidłowo rozpoznały płeć męską z obrazu i audio (zachowując w 100% męskie formy fleksyjne, np. „Robiłem u niego", „Wybacz, że zwątpiłem", „Tylko blefowałem").

### Czy wystąpiła jakakolwiek mutacja plików Z16?

**NIE.** Plik bazy wiedzy `series_memory/<SERIA>_bible.json` oraz pozostałe pliki chronione Z16 (`avt_linter.py`, `rules.py`, `verifier.py`, `verify_purity.py`, `test_system.py`, `tests/archive/`, `pytest.ini`) zachowały pełną integralność (0 B nieautoryzowanych modyfikacji).

---

## Sekcja 3 — Rejestr zdarzeń (Event Index — Faza 1)

Poniższa tabela obejmuje 100% zidentyfikowanych zdarzeń operacyjnych, ostrzeżeń, retry API, korekt lintera oraz anomalii telemetrycznych z logu `EpisodeFlightRecorder` (Z1a/Z1b) i konsoli (Z2).

| # | Poziom | Sekcja EpisodeFlightRecorder | Linia w Z1 (.log) | Linia w Z2 (.txt) | Kategoria | Krótki opis zdarzenia |
|---|---|---|---|---|---|---|
| EV-01 | WARNING (API Retry) | `log_phase2_verifier` (Paczka 12/14) | Brak (tylko konsola) | L356–L357 | K-API / K-HEALING | `504 Timeout` w Fazie 2 przy 237/364 linii (65%) → automatyczna rotacja klucza API i pomyślne przywrócenie połączenia. |
| EV-02 | ERROR (Swallowed Exc) | `log_scene_discourse` (Krok 7) | Pominięty blok po L86 | Po L54 | K-EXC / K-DISCOURSE | Brak sekcji `[KROK 7: GRAF DYSKURSU SCENICZNEGO]` w `.log` i `.jsonl` wskutek `IndexError: tuple index out of range` na `b[-1][4]` w `translator.py:5635`. |
| EV-03 | WARNING (Telemetria) | `log_line_evolution` (Paczki 6, 7, 11, 13) | L524–L628, L698–L762, L856–L864, L964 | L354 | K-PROFILE / K-DISCOURSE | Przypisanie rodzaju (`FEMININE`) w `telemetry_tag` dla 26 kwestii męskich ról epizodycznych (`<POSTAC_BANDYTA_A/B/C>`, `<POSTAC_BUNT>`, `<POSTAC_SLUGA_B>`, `<POSTAC_ZWIADOWCA>`) oraz utrata nazwy aktora (`Aktor: Brak`) dla `<POSTAC_BANDYTA_A/B/C>`. |
| EV-04 | WARNING (Telemetria) | `log_line_evolution` (Paczka 9, ID 204) | L806–L810 | L290 | K-DISCOURSE | Linia dualna `Aktor: <POSTAC_SIOSTRA>/<POSTAC_BRAT>` (kobieta + mężczyzna) otrzymała `[Mówca: POLYLOGUE (FEMININE)` zamiast `VIRILE`. |
| EV-05 | INFO / WARNING | `log_line_evolution` (Paczka 9, 12, 8) | L791, L868, L1041 | L287, L370, L464 | K-VERIFIER | Znacznik `[Zabezpieczono przed regresją Fazy 2]` wyemitowany przez `_guard_phase2_regressions` dla 3 linii (`ID 200`, `ID 280`, `ID 185`). |
| EV-06 | INFO (Mutacja D_pos) | `log_line_evolution` (Paczka 14, ID 318) | L1002–L1009 | L457 | K-LINTER | Korekta fleksyjna AVTLinter: `[Wołacz Afrykat -tzu]` Skorygowano błędną końcówkę: `'<POSTAC_WASAL>ie' -> '<POSTAC_WASAL>u'`. |
| EV-07 | INFO (Bramka jakości) | `log_quality_gate_and_pricing` (Krok 11) | L1090–L1112 | L480 | K-CPS / K-INNE | 20 poprawek EpisodeQualityGate: 2x kolizja czasowa (`\an8`), 12x redundancja kursywy w stylu Italics, 5x higiena tekstu, 1x formatowanie planszy. |
| EV-08 | WARNING (Koszt) | `log_quality_gate_and_pricing` (Krok 11) | L1114–L1123 | L19, L483–L490 | K-PRICE | Rzeczywisty koszt odcinka 4.03 PLN netto (4.96 PLN brutto) przekracza szacunek UI (~3.33 PLN) oraz wartość referencyjną `CORNERSTONE.md` (~2.30–2.66 PLN). |
| EV-09 | WARNING (Telemetria) | `log_ingestion` (Krok 2) i `log_batch_phase1` (Krok 8) | L22, L177–L178 (i kolejne paczki) | Brak | K-INNE | Puste `Zestawienie stylów: {}` w Kroku 2 (`translator.py:4994`) oraz stałe `Czas odpowiedzi modelu: 0.00 s` / `Zużycie tokenów: {}` w Kroku 8 (`translator.py:4940`). |

### Podsumowanie liczbowe per kategoria

- **K-API:** 1 zdarzenie (EV-01, konsola L356–L357)
- **K-EXC:** 1 ukryty wyjątek (EV-02, `translator.py:5635`)
- **K-PROFILE / K-DISCOURSE:** 27 linii dotkniętych anomalią telemetrii płci/grupy (EV-03, EV-04, log L524–L964, konsola L354)
- **K-VERIFIER:** 3 zdarzenia strażnika regresji Fazy 2 (EV-05, log L791, L868, L1041, konsola L287, L370, L464)
- **K-LINTER:** 1 zdarzenie (EV-06, log L1009, konsola L457)
- **K-CPS:** 20 poprawek bramki jakości (EV-07, log L1090–L1112)
- **K-PRICE:** 1 odchylenie budżetowe (EV-08, log L1114–L1123, konsola L483–L490)
- **K-INNE:** 2 defekty telemetrii strukturalnej (EV-09, log L22, L177–L178)
- **Pozostałe kategorie (K-MODEL, K-CACHE, K-METADATA, K-BIBLE, K-DISK, K-CONFIG):** 0 błędów/ostrzeżeń.

---

## Sekcja 4 — Śledztwo per zdarzenie (dla ERROR/CRITICAL/Traceback oraz K-API/K-EXC)

### 4.1. Zdarzenie EV-01 (K-API / K-HEALING): Przekroczenie czasu odpowiedzi `504 Timeout` w Fazie 2 i automatyczna rotacja klucza API

**Cytat z konsoli (Z2:L355–L357):**

```text
Tłumaczenie dialogów:  65%|███████████      | 237/364 [03:09<01:24,  1.50linii/s, Faza 2 (Redakcja Flash CoT: 6144)...]
[Status / Faza 2]: Przekroczono limit czasu odpowiedzi serwera (504 Timeout) -> oczekiwanie na serwery Google i automatyczna rotacja kluczy...
  └─ [OK / Faza 2]: Połączenie z Google API przywrócone.
```

**Ślad kodu (`HEAD = a928569`) — `verifier.py:1298–1318` oraz `client_factory.py:198–218`:**

```python
# verifier.py:1298-1315
def _report_api_retry_status(phase_label: str, err: Exception) -> None:
    friendly = format_friendly_api_error(err)
    with MultimodalTranslator._STATUS_LOCK:
        MultimodalTranslator._STATUS_ACTIVE = True
        MultimodalTranslator._LAST_STATUS_TIME = time.time()
    tqdm.write(f"\n[Status / {phase_label}]: {friendly}")

def _clear_api_retry_status(phase_label: str) -> None:
    with MultimodalTranslator._STATUS_LOCK:
        if MultimodalTranslator._STATUS_ACTIVE:
            MultimodalTranslator._STATUS_ACTIVE = False
            tqdm.write(f"  └─ [OK / {phase_label}]: Połączenie z Google API przywrócone.")
```

```python
# client_factory.py:198-212
def format_friendly_api_error(err: Exception) -> str:
    msg = str(err).lower()
    if "504" in msg or "deadline" in msg or "timeout" in msg or "timed out" in msg:
        return "Przekroczono limit czasu odpowiedzi serwera (504 Timeout) -> oczekiwanie na serwery Google i automatyczna rotacja kluczy..."
```

- **Funkcja/metoda wywołująca:** `DialogueVerifier.verify_batch()` (`verifier.py:1520`) → pętla retry wywołania `client.models.generate_content()` z obsługą `self.client_pool.rotate_key()` oraz `_report_api_retry_status("Faza 2", e)` i `_clear_api_retry_status("Faza 2")` po udanym ponowieniu.
- **Warunek wejścia w gałąź:** Przekroczenie 90-sekundowego limitu `GEMINI_HTTP_TIMEOUT_SEC` (`translator.py:1800`) lub błąd brzegowy `504 Deadline Exceeded` po stronie klastra Google dla zapytania `gemini-3.8-flash` z wysokim budżetem myślenia `thinking_budget = 6144` (paczki 12–16 wykonywane współbieżnie w puli 3 kluczy API).
- **Przyczyna źródłowa (Root Cause):** Środowiskowa (warstwa API Google) połączona z wysokim obciążeniem pojedynczego żądania Fazy 2 (`CoT: 6144` przy równoległym przetwarzaniu 6 paczek na 3 kluczach API). Mechanizm obronny zadziałał dokładnie zgodnie z projektem.
- **Wpływ na wynik:** Zerowy wpływ na `.ass`, `SeriesBible` oraz `PricingGuard`. Paczka została pomyślnie przetworzona w kolejnej próbie po rotacji klucza.
- **Konfrontacja z rejestrem incydentów:** Oczekiwane działanie mechanizmu odpornościowego `MultiKeyClientPool` (brak nowego incydentu błędu).
- **Rekomendacja (w domenie pozytywnej Z2):** Zachowanie obecnej architektury rotacji kluczy `MultiKeyClientPool` z możliwością dodania telemetrii zdarzenia retry (`stage="api_retry"`) bezpośrednio do `EpisodeFlightRecorder`, aby historia chwilowych błędów `504`/`503` była widoczna również w pliku `.jsonl` obok konsoli.

### 4.2. Zdarzenie EV-02 (K-EXC / K-DISCOURSE): Cichy wyjątek `IndexError` blokujący zapis `[KROK 7: GRAF DYSKURSU SCENICZNEGO]`

**Cytat z logu/konsoli (Z1a / Z1b):**
W pliku Z1a (`.log`) po `[KROK 6: PAMIĘĆ SERII SERIESBIBLE I PARADYGMATY ODMIANY]` (L81–L86) i blokach `[KROK 4]` następuje od razu `[KROK 8: FAZA 1]` (L174). Sekcja `[KROK 7: GRAF DYSKURSU SCENICZNEGO I ADAPTACYJNE PACZKI]` (`stage="scene_discourse"`) nie występuje ani razu w `.log`, ani w `.jsonl`.

**Ślad kodu (`HEAD = a928569`) — `translator.py:5625–5646` oraz `translator.py:5115–5118`:**

```python
# translator.py:5115-5118 (konstrukcja raw_entries — 4-krotka!)
            clean = re.sub(r"\{[^}]*\}", "", ev.text).strip()
            if clean:
                raw_entries.append((orig_idx, ev, clean, ts_prefix))
```

```python
# translator.py:5625-5645 (próba logowania Kroku 7)
        discourse_turns = SceneDiscourseGraph.build_discourse_topology([item[1] for item in raw_entries], series_bible=self.series_bible)
        if self.flight_recorder:
            try:
                batches_sum = [
                    {
                        "batch_id": b_idx,
                        "line_count": len(b),
                        "first_id": b[0][0] if b else None,
                        "last_id": b[-1][0] if b else None,
                        "start_ms": b[0][3] if b else 0,
                        "end_ms": b[-1][4] if b else 0
                    }
                    for b_idx, b in enumerate(batches)
                ]
                self.flight_recorder.log_scene_discourse(
                    scene_boundaries=getattr(self, "scene_cuts_ms", []),
                    turns=discourse_turns,
                    batches_summary=batches_sum
                )
            except Exception:
                logger.debug("Rejestracja struktury dyskursu zakończona wyjątkiem", exc_info=True)
```

- **Funkcja/metoda wywołująca:** `MultimodalTranslator.translate_ass_file(self, subs_path, output_path, video_path)` (`translator.py:4953`).
- **Warunek wejścia w gałąź:** Zawsze, gdy `self.flight_recorder` jest aktywny i lista `batches` zawiera co najmniej jedną niepustą paczkę (`len(b) > 0`). Każdy element paczki `b` pochodzi z `raw_entries` i jest 4-elementową krotką `(orig_idx, ev, clean, ts_prefix)` o indeksach `0..3`. Wyrażenie `b[0][3]` pobiera string `ts_prefix` (zamiast `start_ms`), natomiast wyrażenie `b[-1][4]` odwołuje się do piątego elementu krotki (indeks `4`), co bezwarunkowo rzuca `IndexError: tuple index out of range`. Wyjątek jest natychmiast łapany przez `except Exception:` w linii `5644` i wyciszany na poziomie `logger.debug`.
- **Minimalny kontrprzykład:** Dowolny niepusty plik `.ass` (nawet z 1 linią dialogową) uruchomiony z `trace_log=True`.
- **Przyczyna źródłowa (Root Cause):** Błąd w kodzie (regresja indeksowania krotki przy telemetrii) — autor kodu budującego `batches_sum` założył strukturę 5-krotki `(orig_idx, ev, clean, start_ms, end_ms)`, podczas gdy `raw_entries` przechowuje 4-krotkę `(orig_idx, ev, clean, ts_prefix)`, a czasy znajdują się w atrybutach obiektu `SSAEvent`: `b[0][1].start` oraz `b[-1][1].end`.
- **Wpływ na wynik:**
  - **Wpływ na `.ass`:** Brak (`discourse_turns` wylicza się poprawnie w linii `5625`, przed blokiem `try`).
  - **Wpływ na telemetrię `EpisodeFlightRecorder`:** Wysoki — całkowity brak sekcji `[KROK 7: GRAF DYSKURSU SCENICZNEGO I ADAPTACYJNE PACZKI]` w raportach `.log` i `.jsonl`.
- **Konfrontacja z rejestrem incydentów:** Nowy incydent telemetrii — zaproponowano identyfikator `INC-AVT-020` w Sekcji 8.
- **Rekomendacja (w domenie pozytywnej Z2):** W `translator.py:5634–5635` odczytywać znaczniki czasu bezpośrednio z obiektu zdarzenia `SSAEvent` znajdującego się pod indeksem `1` krotki: `"start_ms": b[0][1].start if b else 0` oraz `"end_ms": b[-1][1].end if b else 0`.

---

## Sekcja 5 — Śledztwo per zdarzenie (dla WARNING i anomalii z kategorii K-PROFILE, K-DISCOURSE, K-VERIFIER, K-LINTER, K-PRICE, K-INNE)

### 5.1. Zdarzenie EV-03 (K-PROFILE / K-DISCOURSE): Fałszywa płeć (`FEMININE`) w `telemetry_tag` dla 26 kwestii męskich postaci epizodycznych oraz wyczyszczenie pola aktora dla `<POSTAC_BANDYTA_A/B/C>`

**Cytat z logu i konsoli:**

Konsola (Z2:L354, diagnoza sceny z Paczki 14):
```text
Pomimo błędnych tagów telemetrycznych przypisujących żeński rodzaj, wszyscy uczestnicy tej sceny to mężczyźni.
```

Log Z1a (L711–L716, L856–L864, L964):
```text
[ID: 158 | Czas: 570480->574760 | Aktor: Brak]
EN:                 "I've worked for <POSTAC_HERSZT_2>, \Nand he never mentioned you."
Telemetria:         [Mówca: <POSTAC_BANDYTA_B> (FEMININE) | Adresat: <POSTAC_BANDYTA_A> (MASCULINE) | Grupa_2os_lm: VIRILE]
Faza 1 (Draft PL):  "Robiłem u niego i nigdy\No tobie nie wspominał."
...
[ID: 259 | Czas: 924940->927070 | Aktor: <POSTAC_BUNT>]
Telemetria:         [Mówca: <POSTAC_BUNT> (FEMININE) | Adresat: Grupa Mężczyzn (MASCULINE) | Grupa_1os_lm: VIRILE | Grupa_2os_lm: VIRILE | Scena: POLYLOGUE (n=4)]
...
[ID: 295 | Czas: 1091100->1093440 | Aktor: <POSTAC_ZWIADOWCA>]
Telemetria:         [Mówca: <POSTAC_ZWIADOWCA> (FEMININE) | Adresat: <POSTAC_GLOWNA> (MASCULINE) | Grupa_2os_lm: VIRILE | Scena: POLYLOGUE (n=4)]
```

**Ślad kodu (`HEAD = a928569`):**

`speaker_diarizer.py:159–164` (`SpeakerVoiceClassifier.classify_pitch`):
```python
if f0 < 155.0:
    return f"niski tembr (~{int(f0)}Hz: bas/baryton lub ochrypły alt starszej kobiety)"
elif f0 <= 192.0:
    return f"średni tembr (~{int(f0)}Hz: tenor męski / alt żeński)"
else:
    return f"wysoki tembr (~{int(f0)}Hz: sopran żeński / głos dziecięcy)"
```

`translator.py:2260–2284` (`MultimodalTranslator._arbitrate_speaker_gender`):
```python
        v_tag = speaker_tags[batch_id].lower()
        if "dziecięcy" in v_tag:
            if not is_boy_actor:
                acoustic_gender = "kobieta"
        elif "sopran" in v_tag or "wysoki tembr" in v_tag:
            if not is_boy_actor:
                acoustic_gender = "kobieta"
        elif "alt starszej" in v_tag or "ochrypły alt" in v_tag or "alt żeński" in v_tag:
            # Raspy or mature female alto / contralto voice - ambiguous pitch, NOT male
            acoustic_gender = None
        ...
        elif "baryton" in v_tag or "bas" in v_tag:
            acoustic_gender = "mężczyzna"
```

`translator.py:2154–2159` oraz `translator.py:2415–2428`:
```python
# translator.py:2154-2159
if is_generic_actor_or_category(spk_clean):
    if not canonical_gender:
        spk_clean = ""
```

```python
# translator.py:2415-2428
if jp_female_marker or (acoustic_gender == "kobieta" and not is_boy_actor):
    alerts.append("[TELEMETRIA: odsłuch_f0_whisper=kobieta, weto_akustyczne]")
    return "kobieta", alerts
if acoustic_gender == "mężczyzna":
    alerts.append("[TELEMETRIA: odsłuch_f0_whisper=mężczyzna, weto_akustyczne]")
    return "mężczyzna", alerts
# Phase 1 fallback when no acoustic contradiction
if phase1_is_female: ...
elif phase1_is_male: ...
```

- **Przyczyna źródłowa (Root Cause):** Złożony defekt logiki warunkowej w kodzie (`translator.py:2154–2420` + `series_memory.py:1926`) składający się z trzech sprzężonych czynników:
  1. **Brak angielskich rzeczowników ról zbrojnych w `SECONDARY_LEXICAL_MALE_NOUNS` (`series_memory.py:1926`):** Etykiety `<POSTAC_BANDYTA_A/B/C>`, `<POSTAC_BUNT>`, `<POSTAC_SLUGA_B>`, `<POSTAC_ZWIADOWCA>` otrzymują w Kroku 6 status P2 z `gender: "UNKNOWN"` (`series_memory.py:7060`), ponieważ zbiór `SECONDARY_LEXICAL_MALE_NOUNS` zawiera jedynie `{"boy", "man", "men", "guy", "male", "father", "dad", "brother", "son", "uncle", "grandfather", "waiter", "king", "prince", "lord"}`.
  2. **Martwy kod dla głosów basowych/barytonowych (`translator.py:2268` vs `2281`):** Ponieważ `SpeakerVoiceClassifier` (`speaker_diarizer.py:160`) dla każdego niskiego głosu (`<155 Hz`, np. 92 Hz lub 145 Hz) zwraca tekst `"niski tembr (~...Hz: bas/baryton lub ochrypły alt starszej kobiety)"`, warunek `elif "alt starszej" in v_tag or "ochrypły alt" in v_tag:` w linii `2268` jest zawsze prawdziwy dla niskich głosów i ustawia `acoustic_gender = None`, przez co linia `2281` (`elif "baryton" in v_tag or "bas" in v_tag: acoustic_gender = "mężczyzna"`) jest całkowicie nieosiągalna.
  3. **Weto akustyczne dla krzyku (`>192 Hz`) i wyczyszczenie `spk_clean` dla `Bandit *`:** Dla ról P2 krzyczących powyżej 192 Hz (`v_tag` zawiera `"dziecięcy"` i `"sopran"`), linia `2264` ustawia `acoustic_gender = "kobieta"`, co w linii `2415` wyprzedza deklarację modelu Fazy 1 (`phase1_is_male` w linii `2426`) i wymusza `speaker_gender = "kobieta"`. Z kolei dla `<POSTAC_BANDYTA_A/B/C>` funkcja `is_generic_actor_or_category("Bandit A")` zwraca `True`, co w linii `2156` zeruje `spk_clean = ""` przed sprawdzeniem `self.character_registry` (gdzie Faza 1 zarejestrowała ich jako mężczyzn w `translator.py:3981`), a w `synchronize_ass_event_metadata_and_styles` (`translator.py:237`) pomija zapis nazwy aktora.
- **Wpływ na wynik:** Zerowy wpływ na tekst `.ass` (wszystkie kwestie tych postaci zachowały 100% męskich form czasownikowych i przymiotnikowych w polszczyźnie). Defekt dotyczy wyłącznie wektora `telemetry_tag` oraz wyczyszczenia kolumny `Actor` dla `Bandit A/B/C`.
- **Rekomendacja (w domenie pozytywnej Z2):**
  1. W `translator.py:2268–2284` rozpoznawać niski tembr (`hz_val <= 155` lub obecność `"bas/baryton"`) przed klauzulą neutralizującą `"alt"`, a przy wysokim F0 (`>192 Hz`) dla postaci epizodycznych P2 dawać pierwszeństwo wizualnej klasyfikacji modelu Fazy 1 (`phase1_is_male`).
  2. W `translator.py:2154` zachowywać `spk_clean` do czasu sprawdzenia `self.character_registry`.

### 5.2. Zdarzenie EV-04 (K-DISCOURSE): Kwestia dualna `<POSTAC_SIOSTRA>/<POSTAC_BRAT>` (ID 204) z tagiem `NON_VIRILE`

**Cytat z logu (Z1a:L806–L810):**
```text
[ID: 204 | Czas: 746670->748890 | Aktor: <POSTAC_SIOSTRA>/<POSTAC_BRAT>]
EN:                 "I-It was our idea!"
Telemetria:         [Mówca: POLYLOGUE (FEMININE) | Adresat: Grupa Kobiet (FEMININE) | Grupa_1os_lm: NON_VIRILE | Grupa_2os_lm: NON_VIRILE | Scena: POLYLOGUE (n=4)]
Faza 1 (Draft PL):  "T-To był nasz pomysł!"
```

**Ślad kodu (`HEAD = a928569`):**
- `scene_discourse.py:2911–2914` (`if any(sep in clean_actor for sep in ("/", "|")): spk_label = "POLYLOGUE"`)
- `translator.py:4073` (w Fazie 1 model zwrócił dla tej linii tylko pierwszego mówcę z pary: `speaker_name="<POSTAC_SIOSTRA>"`, `speaker_gender="kobieta"`, co przy braku `has_male_speaker_in_line` ustawiło `line_pl_grp = "NON_VIRILE"` w `translator.py:4181`)

- **Przyczyna źródłowa:** Dla etykiety łączonej zawierającej ukośnik (`A/B`), `arbitrate_event_telemetry` zamienia `clean_actor` na `"POLYLOGUE"` przed sprawdzeniem płci składowych imion (`<POSTAC_SIOSTRA>` = FEMALE, `<POSTAC_BRAT>` = MALE), zamiast wyznaczyć iloczyn logiczny grupy mieszanej (`VIRILE`).
- **Wpływ na wynik:** Brak wpływu na `.ass` („T-To był nasz pomysł!" nie zawiera czasownika w 1. os. lm. czasu przeszłego).
- **Rekomendacja:** Dla etykiet ze znakiem `/` lub `&` w `scene_discourse.py:2911` rozbijać etykietę na składowe postacie i w przypadku obecności choć jednego mówcy MALE ustawiać `we_virility = "VIRILE"`.

### 5.3. Zdarzenie EV-05 (K-VERIFIER): Aktywacja `_guard_phase2_regressions` na 3 liniach (ID 185, 200, 280)

**Cytat z konsoli (Z2:L287, L370, L464):**
```text
└─ [Redaktor Dialogów] #2 [Filar II - Kondensacja i Afekt] ... [Zabezpieczono przed regresją Fazy 2]
└─ [Redaktor Dialogów] #20 [Filar II - Zwięzłość AVT] ... [Zabezpieczono przed regresją Fazy 2]
└─ [Redaktor Dialogów] #11 [Filar I - Szyk Zdania] ... [Zabezpieczono przed regresją Fazy 2]
```

**Ślad kodu (`HEAD = a928569`) — `verifier.py:2092–2285` (`_guard_phase2_regressions`):**
Funkcja porównuje `p1_text` (Draft PL) oraz `p2_text` (Verifier) pod kątem zachowania tagów wielokropków kontynuacyjnych (`...`), zaimków, wołaczy oraz form rodzajowo-osobowych i dołącza notatkę `[Zabezpieczono przed regresją Fazy 2]` do `changes_made`, gdy przywraca lub koryguje element ze szkicu Fazy 1 (np. wielokropek otwierający `...` w ID 185 i ID 280 oraz wielokropek zamykający w ID 200).

- **Przyczyna źródłowa:** Zamierzone działanie obronne potoku chroniące spójność interpunkcyjną zdań rozbitych na dwie linie (Filar CLXIX).
- **Wpływ na wynik:** Pozytywny — zachowano pełną spójność wielokropków w zdaniach dwuczęściowych.

### 5.4. Zdarzenie EV-06 (K-LINTER): Korekta fleksyjna wołacza afrykatowego w AVTLinter (ID 318)

**Cytat z logu (Z1a:L1002–L1009) i konsoli (Z2:L457):**
```text
Faza 1 (Draft PL):  "Twoją też, <POSTAC_WASAL>ie <NAZWISKO_WASALA>ie."
Faza 2 (Verifier):  "Twoją też, <POSTAC_WASAL>ie <NAZWISKO_WASALA>ie."
AVTLinter (D_pos):  "Twoją też, <POSTAC_WASAL>u <NAZWISKO_WASALA>ie."
Lista poprawek D_pos: [[Wołacz Afrykat -tzu] Skorygowano błędną końcówkę: '<POSTAC_WASAL>ie' -> '<POSTAC_WASAL>u']
```

**Ślad kodu (`HEAD = a928569`) — `avt_linter.py:4245–4275`:**
Reguła domeny pozytywnej D_pos dla imion męskich zakończonych na afrykat `-tz` / `-c` / `-dz` wymusza końcówkę wołacza `-u` zgodnie z paradygmatem w `SeriesBible` (`W: <POSTAC_WASAL>u <NAZWISKO_WASALA>ie`, Z1a:L85).

- **Przyczyna źródłowa:** W `episode_profile.json` (Z1b:L4) LLM wygenerował w relacji `<POSTAC_GLOWNA>` → `<POSTAC_WASAL>` wariant `address_form: "<POSTAC_WASAL>ie"`, podczas gdy w `name_declensions` oraz w `SeriesBible` (`declensions`) figurowała poprawna forma `W: <POSTAC_WASAL>u <NAZWISKO_WASALA>ie`. Deterministyczny AVTLinter przechwycił i skorygował tę niespójność do formy kanonicznej P0.
- **Wpływ na wynik:** Pozytywny — 100% zgodności fleksyjnej wyjściowego pliku `.ass` z `SeriesBible`.

### 5.5. Zdarzenie EV-08 (K-PRICE): Przekroczenie szacowanego kosztu odcinka (4.03 PLN netto vs ~3.33 PLN UI / ~2.30–2.66 PLN Cornerstone)

**Cytat z logu (Z1a:L1114–L1123) i konsoli (Z2:L19, L483–L490):**
```text
💡 Szacowany koszt: ~1.94 zł (Studyjny) | ~3.33 zł (Mistrzowski) | ~6.48 zł (Kinowy)
...
💰 RZECZYWISTY KOSZT ODCINKA: 4.03 PLN netto (~4.96 PLN brutto z VAT 23%)
├─ Faza 1 (Szkic & OCR Sparse): 1.93 PLN netto
│   └─ Wejście: 494,913 tok (Cached: 248,081) | Wyjście: 74,567 tok
├─ Faza 2 (Reżyseria & Elastic CoT): 2.09 PLN netto
│   └─ Wejście: 533,831 tok (Cached: 241,604) | Wyjście+CoT: 76,264 tok
```

**Ślad kodu (`HEAD = a928569`) — `pricing_guard.py:180–245` oraz `main.py:115–145`:**
Kalkulator rzeczywisty `PricingGuard` zlicza wszystkie tokeny wejściowe (w tym niebuforowane klatki obrazu Sparse OCR / Scene Cuts i wycinki audio w 17 paczkach: ~246k niebuforowanych tokenów w Fazie 1 i ~292k w Fazie 2) oraz pełny strumień wyjściowy wraz z tokenami myślenia Elastic CoT (76 264 tokenów w Fazie 2 przy budżetach 3072–6144 na paczkę).

- **Przyczyna źródłowa:** Odcinek o dużej gęstości dialogowej (364 linie podzielone na 17 paczek) i wysokim udziale scen dramatycznych wymusił maksymalny pułap `Elastic CoT = 6144` w 6 z 17 paczek Fazy 2 (Paczki 1, 7, 13, 14, 15, 16), co zwiększyło zużycie tokenów wyjściowych o ~21% względem statycznej estymacji UI (3.33 PLN).
- **Wpływ na wynik:** Brak wpływu na `.ass`. Rozliczenie finansowe jest matematycznie dokładne, a rabat `ContextCache` (-90%) zaoszczędził 1.32 PLN netto.

### 5.6. Zdarzenie EV-09 (K-INNE): Puste `style_matrix: {}` w Kroku 2 oraz `response_time_sec: 0.0` / `token_usage: {}` w Kroku 8

**Cytat z logu (Z1a:L22, L177–L178):**
```text
Zestawienie stylów: {}
...
Paczka ID: 0
Czas odpowiedzi modelu: 0.00 s
Zużycie tokenów: {}
```

**Ślad kodu (`HEAD = a928569`):**

`translator.py:4992–4998`:
```python
self.flight_recorder.log_ingestion(
    encoding=detected_enc,
    total_events=len(subs),
    style_matrix=getattr(self.style_report, "styles", {}) if hasattr(self, "style_report") else {},
    sample_events=sample_evs
)
```

W klasie `StyleMatrixReport` (`style_matrix.py:233`) słownik stylów nazywa się `self.style_profiles`, a podsumowanie ról zwraca metoda `self.style_report.get_summary()` (`style_matrix.py:469`). Atrybut `.styles` nie istnieje, więc `getattr(self.style_report, "styles", {})` zawsze zwraca `{}`.

`translator.py:4939–4945`:
```python
self.flight_recorder.log_batch_phase1(
    batch_id=b_idx,
    prompt_text=p1_prompt_str,
    raw_response=p1_raw_dict,
    response_time_sec=0.0,
    token_usage={}
)
```

Wartości `response_time_sec=0.0` oraz `token_usage={}` są zahardkodowane jako stałe w miejscu wywołania loggera po zakończeniu paczki.

- **Wpływ na wynik:** Brak wpływu na `.ass` i `PricingGuard` (tokeny są zliczane osobno w `PricingGuard`), natomiast w logu `EpisodeFlightRecorder` brakuje szczegółów per-paczka.

---

## Sekcja 6 — Weryfikacja integralności stanu (Faza 3 — §2.4)

| # | Punkt weryfikacji (§2.4) | Werdykt | Uzasadnienie i dowód z logów / kodu (`HEAD = a928569`) |
|---|---|---|---|
| 1 | Wyciek stanu między odcinkami | PASS | Przebieg obejmował 1 odcinek (`[Sukces odcinka 1/1]`, Z2:L493). W `translator.py:5015–5045` na starcie `translate_ass_file` struktury odcinkowe (`episode_scene_genders`, `episode_scene_polylogues`, `profile_line_alerts`) są inicjalizowane na nowo dla bieżącego pliku. |
| 2 | Wyścig wątków (`concurrent_batches > 1`) | PASS | Tłumaczenie szło równolegle (6 paczek w locie / 3 aktywnych kluczy API, Z2:L57). Kolejność ukończenia paczek w Z1b była asynchroniczna (0, 2, 3, 5, 1, 4, 6, 7, 8, 9, 11, 10, 12, 13, 15, 14, 16), jednak zapis do `self.character_registry` jest chroniony przez `with self.lock:` (`translator.py:3977`), a składanie wyników następuje deterministycznie po indeksach linii (0..363). |
| 3 | Kompletność `Zero-Gap Healing Pass` | PASS | Wszystkie 17 paczek (364/364 linii) zakończyło się pełnym sukcesem w pierwszym przebiegu (po automatycznym retry `504 Timeout` w Fazie 2). Zero luk tłumaczeniowych (`is_missing_tr = False` dla wszystkich 364 linii). |
| 4 | Czyszczenie `ContextCache` | PASS | Utworzono bufory dla 3 kluczy API (`Locked -90% server discount for gemini-3.8-flash (translator/verifier) across 3 API keys`, Z2:L49–L50), a na końcu przebiegu wywołano blok `finally:` z `cleanup_all_active_caches` (`translator.py:5895`). |
| 5 | Brak mutacji plików Z16 | PASS | Plik `series_memory/<SERIA>_bible.json` oraz pliki kodu Z16 (`avt_linter.py`, `rules.py`, `verifier.py`, `verify_purity.py`, `test_system.py`) nie uległy żadnej modyfikacji (0 B zmian). |
| 6 | Koszt `PricingGuard` (~2.30–2.66 PLN) | WARN | Koszt wyniósł 4.03 PLN netto (4.96 PLN brutto). Przekroczenie przedziału referencyjnego `CORNERSTONE.md` wynika z wyboru profilu `[3] MISTRZOWSKI` z pełnym multimodalnym wsadem wideo/audio (17 paczek) oraz wysokim `Elastic CoT` (do 6144 tokenów) w Fazie 2. |
| 7 | Czystość telemetrii (`ARB-017`/`ARB-028`) | PASS | W 364 wygenerowanych tagach `telemetry_tag` w Z1a/Z1b wystąpiło 0 wartości `None`, `UNKNOWN` lub `AMBIGUOUS` (funkcja `_is_valid_telemetry_val` w `translator.py:166–172` skutecznie odfiltrowuje nieokreślone pola). Wykryto natomiast odwrócenie znaku płci (`FEMININE` zamiast `MASCULINE`) dla ról epizodycznych P2 opisane w EV-03. |

---

## Sekcja 7 — Konfrontacja z rejestrem znanych incydentów (Faza 4 — §2.5)

| Zdarzenie z audytu | Powiązany znany incydent / reguła (`PROJECT_MEMORY.md` / Audyty 11.0–11.1) | Status konfrontacji i ocena zgodności |
|---|---|---|
| EV-02 (`IndexError` w `log_scene_discourse`) | `LUKA-E12-01` (Telemetria `EpisodeFlightRecorder` — `pipeline_logger.py`) | **NOWY WARIANT (`INC-AVT-020`)** — sama metoda `EpisodeFlightRecorder.log_scene_discourse` w `pipeline_logger.py:194` jest poprawna, lecz wywołanie w `translator.py:5635` rzuca `IndexError` na `b[-1][4]` przed wejściem do loggera. |
| EV-03 (`FEMININE` w telemetrii dla `Bandit A/B/C`, `Rebel`, `Retainer B`, `Lookout`) | `ARB-017` / `ARB-028` / `INC-AVT-009` (Prymat P0 i ochrona przed kontaminacją płci z F0 akustyki) | **CZĘŚCIOWA REGRESJA TELEMETRII (`INC-AVT-021`)** — dla postaci P0 z `SeriesBible` ochrona działa w 100%, lecz dla ról epizodycznych P2 (`gender: UNKNOWN`) brak angielskich leksemów w `SECONDARY_LEXICAL_MALE_NOUNS` oraz martwa gałąź `bas/baryton` w `translator.py:2268–2281` powodują nadpisanie płci męskiej z Fazy 1 przez F0 krzyku (`>192 Hz`). |
| EV-04 (`POLYLOGUE (FEMININE)` dla `<POSTAC_SIOSTRA>/<POSTAC_BRAT>`) | `ARB-031` (Rozwiązywanie grup mieszanych i diad ze znakiem `/`) | **DROBNA LUKA TELEMETRII** — zamiana etykiety z `/` na `"POLYLOGUE"` w `scene_discourse.py:2912` przed sprawdzeniem płci obu członów diady. |
| EV-06 (`<POSTAC_WASAL>ie` → `<POSTAC_WASAL>u`) | `ARB-041` / Filar CLXIII (Wołacz imion obcych na afrykat `-tz`) | **PEŁNA ZGODNOŚĆ (PASS)** — deterministyczna korekta AVTLinter (D_pos) zadziałała wzorcowo. |
| EV-09 (`style_matrix: {}` oraz `0.00 s` w Kroku 8) | `LUKA-E12-02` (Kompletność pól payloadu w `EpisodeFlightRecorder`) | **NOWY INCYDENT TELEMETRII (`INC-AVT-022`)** — rozjazd nazwy atrybutu `.styles` vs `.style_profiles` oraz zahardkodowane `0.0` w `translator.py:4940`. |

---

## Sekcja 8 — Nowe incydenty wykryte w audycie

### 8.1. INC-AVT-020 — Cichy wyjątek `IndexError` na `b[-1][4]` całkowicie pomijający zapis Kroku 7 (`log_scene_discourse`)

- **Lokalizacja:** `translator.py:5628–5645` (`HEAD = a928569`).
- **Opis i mechanizm:** Podczas budowania `batches_sum` dla `self.flight_recorder.log_scene_discourse()` kod odwołuje się do `b[0][3]` (`ts_prefix`) i `b[-1][4]` (nieistniejący 5. element 4-krotki `(orig_idx, ev, clean, ts_prefix)` utworzonej w `translator.py:5117`). Wywołanie rzuca `IndexError: tuple index out of range`, który jest po cichu tłumiony przez `except Exception: logger.debug(...)`.
- **Reprodukcja:** 100% przebiegów tłumaczenia z włączonym `EpisodeFlightRecorder`.
- **Wpływ:** Brak sekcji `[KROK 7: GRAF DYSKURSU SCENICZNEGO I ADAPTACYJNE PACZKI]` w plikach `.log` oraz `.jsonl` (0 wpływu na `.ass`).
- **Rekomendacja:** Zastąpienie `b[0][3]` przez `b[0][1].start` oraz `b[-1][4]` przez `b[-1][1].end` w `translator.py:5634–5635`.

### 8.2. INC-AVT-021 — Martwa gałąź F0 dla głosów basowych/barytonowych (`translator.py:2281`) i fałszywa płeć `FEMININE` w telemetrii ról epizodycznych P2

- **Lokalizacja:** `translator.py:2154–2159`, `translator.py:2261–2284`, `translator.py:2415–2428` oraz `speaker_diarizer.py:160` (`HEAD = a928569`).
- **Opis i mechanizm:**
  - `SpeakerVoiceClassifier.classify_pitch` (`speaker_diarizer.py:160`) dla niskich głosów męskich (`<155 Hz`) zwraca tekst `"niski tembr (~...Hz: bas/baryton lub ochrypły alt starszej kobiety)"`. W `translator.py:2268` warunek `elif "alt starszej" in v_tag or "ochrypły alt" in v_tag:` przechwytuje każdy taki głos i ustawia `acoustic_gender = None`, przez co warunek `elif "baryton" in v_tag or "bas" in v_tag:` w linii `2281` nigdy się nie wykonuje.
  - Dla ról epizodycznych (`Bandit A/B/C`, `Rebel`, `Retainer B`, `Lookout`) o wysokim F0 w scenach krzyku (`>192 Hz`), `translator.py:2261` przypisuje `acoustic_gender = "kobieta"`, a `translator.py:2415` nadpisuje tym wynikiem rozpoznanie `speaker_gender = "mężczyzna"` z Fazy 1.
- **Wpływ:** Błędny znacznik (`FEMININE`) w `telemetry_tag` dla 26 kwestii męskich postaci pobocznych (model Fazy 1 i Fazy 2 obronił polski tekst `.ass` dzięki multimodalnej weryfikacji obrazu i audio).
- **Rekomendacja:** Uporządkowanie warunków `v_tag` w `translator.py:2268–2284`, zachowanie `spk_clean` dla `self.character_registry` przed wyczyszczeniem w `translator.py:2154` oraz rozszerzenie `SECONDARY_LEXICAL_MALE_NOUNS` (`series_memory.py:1926`) o angielskie rzeczowniki ról zbrojnych (`bandit`, `rebel`, `retainer`, `soldier`, `guard`, `mercenary`).

### 8.3. INC-AVT-022 — Niespójność nazwy atrybutu `style_report.styles` w Kroku 2 oraz puste metryki czasu/tokenów w Kroku 8

- **Lokalizacja:** `translator.py:4994` oraz `translator.py:3960` / `4940` (`HEAD = a928569`).
- **Opis i mechanizm:** Wywołanie `getattr(self.style_report, "styles", {})` w `translator.py:4994` zwraca `{}` (w `StyleMatrixReport` pole nazywa się `style_profiles`, a podsumowanie daje `get_summary()`). Z kolei w `translator.py:4940` do `log_batch_phase1` przekazywane są stałe `response_time_sec=0.0` i `token_usage={}`.
- **Wpływ:** Kosmetyczny brak statystyk stylów w Kroku 2 i czasu odpowiedzi per paczka w Kroku 8 pliku `.log`/`.jsonl`.
- **Rekomendacja:** Użycie `self.style_report.get_summary()` w `translator.py:4994` oraz przekazanie rzeczywistego czasu wykonania `time.time() - t0` i metadanych tokenów z odpowiedzi API do `log_batch_phase1`.

---

## Sekcja 9 — Werdykt końcowy i rekomendacje

### Priorytetyzowana lista rekomendacji (bez wdrażania — Read-Only)

- **[P1 — Telemetria Dyskursu / Krok 7]** W `translator.py:5634–5635` zastąpić odwołania `b[0][3]` oraz `b[-1][4]` odwołaniami do właściwości obiektu `SSAEvent`: `b[0][1].start` oraz `b[-1][1].end`, przywracając pełne logowanie sekcji `[KROK 7: GRAF DYSKURSU SCENICZNEGO I ADAPTACYJNE PACZKI]` (`INC-AVT-020`).
- **[P1 — Arbitraż Płci Postaci Epizodycznych P2]** W `translator.py:2268–2284` odblokować gałąź `bas/baryton` dla niskich częstotliwości F0 (`<155 Hz`), w `translator.py:2154` wykonywać sprawdzenie `self.character_registry` przed wyczyszczeniem `spk_clean` dla etykiet `Bandit *`, a dla ról P2 bez rekordu P0 przy wysokim F0 krzyku respektować wizualno-kontekstową klasyfikację modelu Fazy 1 (`phase1_is_male`) (`INC-AVT-021`).
- **[P2 — Kompletność Telemetrii Kroków 2 i 8]** W `translator.py:4994` przekazywać `self.style_report.get_summary()` do `log_ingestion`, a w `translator.py:4940` przekazywać zmierzony czas odpowiedzi i strukturę `usage_metadata` do `log_batch_phase1` (`INC-AVT-022`).
- **[P3 — Rozwiązywanie Diad z Ukośnikiem i Estymator Kosztu UI]** W `scene_discourse.py:2911` rozbijać etykiety typu `<POSTAC_A>/<POSTAC_B>` na składowe postacie w celu wyznaczenia `we_virility = "VIRILE"` dla grup mieszanych, a w `main.py` zaktualizować szacunkowy mnożnik tokenów profilu `[3] MISTRZOWSKI` dla odcinków z pełnym wsadem multimodalnym.

### Werdykt końcowy

Przebieg tłumaczenia odcinka `<ODCINEK>` serii `<SERIA>` na certyfikowanym standardzie `Standard 11.1.2a` (`HEAD = a928569`) otrzymuje werdykt **`ZGODNY Z ZASTRZEŻENIAMI`**. Potok wykazał pełną odporność produkcyjną na błędy środowiskowe (`504 Timeout` w Fazie 2) oraz błędy pomocniczej telemetrii F0 dla ról epizodycznych, generując w 100% kompletny, spójny stylistycznie i fleksyjnie plik `.ass` przy zerowej mutacji plików chronionych Z16.

---

## Sekcja 10 — Checklista odbioru (§5)

- [x] **(a)** Potwierdzono obecność załączników `Z1` (`.log` + `.jsonl`) i `Z2` (`.txt`).
- [x] **(b)** Wykonano Fazę 0 (§2.1) i udokumentowano inwentaryzację w Sekcji 1.
- [x] **(c)** Wykonano Fazę 1 (§2.2) i udokumentowano klasyfikację w Sekcji 3.
- [x] **(d)** Wykonano Fazę 2 (§2.3) dla wszystkich zdarzeń `ERROR`/`CRITICAL`/`Traceback` oraz wymaganych `WARNING` — z pełnym śladem kodu (plik:linia + kontekst + funkcja + warunek + root cause + wpływ + rekomendacja) w Sekcjach 4 i 5.
- [x] **(e)** Wykonano Fazę 3 (§2.4) i udokumentowano 7 punktów integralności w Sekcji 6.
- [x] **(f)** Wykonano Fazę 4 (§2.5) i udokumentowano konfrontację z rejestrem w Sekcji 7.
- [x] **(g)** Zidentyfikowano nowe incydenty (`INC-AVT-020`, `INC-AVT-021`, `INC-AVT-022`) i opisano je w Sekcji 8.
- [x] **(h)** Wystawiono werdykt końcowy (`ZGODNY Z ZASTRZEŻENIAMI`) i priorytetyzowane rekomendacje (`P1`/`P2`/`P3`) w Sekcji 9.
- [x] **(i)** Raport sformatowany zgodnie ze specyfikacją `Artefakty/Raport_audytu_operacyjnego_2026-11-09.md`, UTF-8 bez BOM, 0 placeholderów `<DO_WYPEŁNIENIA>`.
- [x] **(j)** Każde twierdzenie poparte cytatem z logu + cytatem z kodu (plik:linia) + hash `HEAD = a928569`.

---

**KONIEC RAPORTU AUDYTU OPERACYJNEGO**