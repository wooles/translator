# 🏛️ PEŁNY TECHNICZNY RAPORT POTOKU AVT (CZĘŚĆ II — TELEMETRIA & REJESTRATOR PRZEBIEGU)
**Dokumentacja techniczna modułu `EpisodeFlightRecorder` (`pipeline_logger.py`), telemetrii potoku oraz ewolucji danych w Standardzie 9.0**

---

## 🛰️ 1. GENEZA I ARCHITEKTURA CZARNEJ SKRZYNKI POTOKU (`EpisodeFlightRecorder`)

W potokach tłumaczenia audiowizualnego (AVT) operujących na wielu asynchronicznych warstwach (akustyka F0, transkrypcja Whisper, grafy dyskursu, dwufazowe modele językowe LLM, deterministyczne lintery morfosyntaktyczne i bramki jakości), brak pełnej, chronologicznej obserwowalności uniemożliwia precyzyjną diagnostykę anomalii.

Klasa `EpisodeFlightRecorder` w module `pipeline_logger.py` stanowi kompletną, bezinwazyjną, wielowątkowo bezpieczną czarną skrzynkę wykonania potoku, dedykowaną dla każdego tłumaczonego odcinka.

### Główne Założenia Konstrukcyjne:
1. **Zero Overhead & Zero Crash (Primum Non Nocere):** Wszelkie operacje wejścia/wyjścia (I/O) rejestratora są izolowane w blokach odpornych na wyjątki (`try...except Exception:`). Awaria systemu plików, brak uprawnień zapisu lub zapełnienie dysku nigdy nie przerywa procesu tłumaczenia napisów.
2. **Bezpieczeństwo Wielowątkowe (`threading.Lock`):** Zabezpieczenie współbieżnego zapisu zdarzeń z wielu równoległych wątków przetwarzania paczek (`_process_single_batch`) za pomocą dedykowanej blokady reentrant/mutex.
3. **Format Dualny (Human-Readable + Machine-Readable):** Równoległe generowanie sformatowanego pliku czytelnego dla operatora (`.log`) oraz maszynowego strumienia obiektów JSON (`.jsonl`).

---

## 📂 2. SPECYFIKACJA PLIKÓW WYJŚCIOWYCH LOGÓW

Dla każdego przetwarzanego pliku rejestrator tworzy w katalogu logów (`logs/` lub ścieżce wskazanej przez parametr `--trace-dir`) dwa powiązane pliki z unikalnym znacznikiem czasu:

### A. Plik Czytelny dla Człowieka (`.log`)
- **Ścieżka:** `logs/{slug}_{nazwa_pliku}_{timestamp}_full_trace.log`
- **Kodowanie:** `UTF-8`
- **Zawartość:**
  * Nagłówek sesji (seria, nazwa pliku źródłowego, znacznik czasu rozpoczęcia).
  * 11 ponumerowanych sekcji odpowiadających kolejnym etapom cyklu życia translacji (`[KROK 1: CLI & INICJALIZACJA PROCESU]`, `[KROK 2: INGESTIA NAPISÓW I KLASYFIKACJA WIZUALNA]`, ..., `[KROK 11: EPISODEQUALITYGATE I ROZLICZENIE FINANSOWE PRICINGGUARD]`).
  * Raporty ewolucji pojedynczych linii dialogowych w formacie diffu wielowarstwowego.
  * Stopka podsumowująca czas zakończenia i ścieżki wygenerowanych plików.

### B. Plik Maszynowy Strumienia Zdarzeń (`.jsonl`)
- **Ścieżka:** `logs/{slug}_{nazwa_pliku}_{timestamp}_events.jsonl`
- **Kodowanie:** `UTF-8` (format JSON Lines, jeden obiekt JSON na wiersz).
- **Struktura Rekordu:**
```json
{
  "timestamp_iso": "2026-10-19T18:00:00.123456",
  "stage": "line_evolution",
  "batch_id": 0,
  "line_id": 1,
  "payload": {
    "start_ms": 1000,
    "end_ms": 3000,
    "actor": "Główny Bohater",
    "en_text": "I understand now.",
    "jp_audio": "Wakatta yo.",
    "whisper_tags": "K1",
    "telemetry_tag": "[Mówca: Główny Bohater | Adresat: Towarzysz]",
    "phase1_pl": "Teraz rozumiem.",
    "phase2_pl": "Już rozumiem.",
    "linter_pl": "Już rozumiem.",
    "fixes_applied": []
  }
}
```

---

## 🔄 3. MATRYCA 11 ETAPÓW POTOKU OBJĘTYCH REJESTRACJĄ

| Etap | Identyfikator `stage` | Wywoływana Metoda | Rejestrowany Zakres Danych |
| :--- | :--- | :--- | :--- |
| **Krok 1** | `cli_init` | `log_cli_init` | Sparsowane argumenty CLI, ścieżki do plików, modele Fazy 1 i 2, stan `ContextCacheManager` oraz `ClientPool`. |
| **Krok 2** | `ingestion` | `log_ingestion` | Wykryte kodowanie pliku napisów, liczba zdarzeń `SSAEvent`, zestawienie stylów ASS oraz próbka klasyfikacji wizualnej (`detect_event_visual_type`). |
| **Krok 3** | `metadata` | `log_metadata` | Znormalizowany slug serii, metadane pobrane z AniList GraphQL API oraz tabela mapowania etykiet aktorów z `normalize_actor_tag`. |
| **Krok 4** | `acoustics_whisper` | `log_acoustics_and_whisper` | Metryki estymacji akustycznej F0 (`librosa.pyin`), wagi epistemiczne płci, wykryte tagi K1–K8 oraz transkrypcje japońskiego audio z Faster-Whisper. |
| **Krok 5** | `profile_prepass` | `log_profile_prepass` | Informacja o źródle profilu (kesz dyskowy vs generacja LLM), obiekt `EpisodeProfile` oraz podsumowanie założeń świata serii. |
| **Krok 6** | `series_bible` | `log_series_bible` | Stan bazy wiedzy `SeriesBible`, zbiór postaci w schemacie `CharacterRecord Positive Schema`, relacje skierowane oraz paradygmaty deklinacji `DeclensionParadigm`. |
| **Krok 7** | `scene_discourse` | `log_scene_discourse` | Wykryte granice scen, tury dialogowe `SpeakerTurn` i pod-tury `SubTurn`, stan virility grup `We_Group` i `You_Group` oraz podział na paczki adaptacyjne `create_adaptive_batches`. |
| **Krok 8** | `phase1_batch` | `log_phase1_batch` | Dokładny prompt wysłany do Primary LLM, czas odpowiedzi API, zużycie tokenów oraz surowa odpowiedź JSON (`BatchTranslationResponse`). |
| **Krok 9** | `phase2_verifier` | `log_phase2_verifier` | Obliczony budżet myślenia CoT, prompt wysłany do Script Doctora oraz surowa odpowiedź `RefinedBatchResponse` z uzasadnieniem modyfikacji. |
| **Krok 10** | `line_evolution` | `log_line_evolution` | Pełna 6-stopniowa ewolucja każdej linii dialogowej (`EN -> Audio JP -> Telemetria -> Faza 1 PL -> Faza 2 PL -> AVTLinter D_pos PL`) wraz z listą zastosowanych napraw fleksyjnych. |
| **Krok 11** | `quality_gate_pricing` | `log_quality_gate_and_pricing` | Audyt końcowy `EpisodeQualityGate` (Faza 0 + Faza 7), lista poprawek integralności oraz pełny bilans finansowy tokenów i kosztów z `PricingGuard`. |

---

## 🛠️ 4. INTEGRACJA W KODZIE ŹRÓDŁOWYM

1. **`main.py`:**
   - Dodano argumenty CLI: `--trace-log` (domyślnie `True`), `--no-trace-log` (`action="store_false"`), `--trace-dir` (domyślnie `"logs"`).
   - Przekazano parametry `trace_log` i `trace_dir` do konstruktora `MultimodalTranslator`.
2. **`translator.py`:**
   - Zainicjalizowano `self.flight_recorder = EpisodeFlightRecorder(...)` w `MultimodalTranslator.__init__`.
   - Wpięto rejestrator we wszystkich kluczowych węzłach cyklu życia w `translate_file` oraz `_process_single_batch`.
3. **`test_system.py`:**
   - Zaimplementowano dedykowany Test 182 (`test_episode_flight_recorder_full_pipeline_trace`), weryfikujący tworzenie plików, kompletność etapów, integralność JSONL oraz bezpieczeństwo współbieżnego zapisu.
   - Zaktualizowano licznik suity do 182/182 PASSED.

---
**KONIEC RAPORTU TECHNICZNEGO POTOKU AVT (CZĘŚĆ II) — TRANSLATOR STANDARD 9.0**
