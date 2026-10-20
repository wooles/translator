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

## 🛡️ 5. ARCHITEKTURA STANDARDU 9.0: WARIANT (D) — HYBRYDOWA STRAŻ DOWODOWA (HYBRID EVIDENCE GUARD & PIPELINE HARDENING)

Wdrożenie Architektury Wariantu (d) stanowi fundamentalne domknięcie ewolucji potoku AVT w Standardzie 9.0, łącząc absolutną nadrzędność wyborów Primary LLM z bezkompromisową, deterministyczną ochroną przed regresjami w oparciu o twarde dowody ontologiczne i źródłowe.

### Główne Filary Wariantu (d):

#### 1. Całkowite Odcięcie Mutatorów Morfosyntaktycznych w `AVTLinter` ($T(x) = x$)
- Wprowadzono flagę architektoniczną `VARIANT_D_PURE_LLM_MORPHOLOGY = True` w `avt_linter.py`.
- W trybie produkcyjnym (`is_production=True` / `strict_positive_domain=True`):
  * Metoda `apply_strict_positive_domain_pipeline` całkowicie omija wszelkie mutatory czasowników 1. i 2. osoby, orzeczników przymiotnikowych po łącznikach, par ról społecznych oraz virility grup.
  * Wybory leksykalne, deiktyczne, stylistyczne i syntaktyczne generowane przez Primary LLM podlegają ścisłej funkcji identycznościowej:
    $$\forall x \notin \mathcal{D}_{\text{pos}}, \quad T(x) = x$$
  * Wyeliminowano zjawisko wtórnego nadpisywania naturalnego szyku, elips i celowych konstrukcji stylistycznych przez sztywne wzorce regex.

#### 2. Wąska Siatka Bezpieczeństwa $P_0 \cap \text{EN}$ w `EpisodeQualityGate`
- Zaimplementowano metodę `EpisodeQualityGate.apply_narrow_safety_net_p0_en(...)`, działającą w trybie 100% deterministycznym wyłącznie przy spełnieniu koniunkcji twardych warunków dowodowych:
  * **1. Osoba (Mówca $P_0$):** Korekta rodzaju gramatycznego czasowników i orzeczników następuje wyłącznie wtedy, gdy mówca posiada zweryfikowany status $P_0$ (`confidence >= 0.95`, `has_verified_gender = True`) w `SeriesBible` ORAZ postać nie znajduje się pod przykrywką w scenie konspiracyjnej (`not is_incognito_scene`).
  * **2. Osoba (Adresat $P_0$ / Wołacz):** Korekta form 2. osoby następuje wyłącznie przy zweryfikowanym adresacie $P_0$ w relacji 1-na-1 lub po detekcji jednoznacznego zwrotu wołaczowego do zarejestrowanej postaci $P_0$ w bieżącej wypowiedzi (`addressee_name` z aliasów $P_0$).
  * **3. Osoba (Zaimki Źródłowe EN):** Korekta form przeszłych 3. osoby w polskim tekście następuje wyłącznie w obecności w pełni jednoznacznych zaimków w zdaniu angielskim (`he/him/his/himself` vs `she/her/hers/herself` przy braku zaimków przeciwnej płci) i pod warunkiem braku w zdaniu polskim rzeczownika podmiotowego o odmiennej płci naturalnej (ochrona zdań typu *"Królowa powiedziała, że on..."*).

#### 3. Pre-translacyjna Ingestia Bazy Postaci z Metadanych do `SeriesBible`
- W `translator.py` (`translate_file`), przed zainicjowaniem translacji pierwszego batcha (Etap 0b), potok automatycznie dokonuje pełnej ingestii postaci z `anime_meta["characters"]` do `self.series_bible.data["characters"]` oraz `self.character_registry`.
- Każda pobrana postać otrzymuje status $P_0$ (`priority = "P0"`, `confidence = 1.0`, `has_verified_gender = True`).
- Przed rozpoczęciem tłumaczenia generowane są deterministyczne paradygmaty odmiany nazw własnych dla wszystkich unikalnych aktorów w pliku napisów (`generate_polish_name_declension`).
- Wprowadzono zabezpieczenie przed ponownym nadpisaniem `self.series_bible` pustą instancją przy tworzeniu `SeriesBible` w Etapie 0b.

#### 4. Fonetyczna Normalizacja Aliasów w $O(1)$ (`ph <-> f`)
- W `series_memory.py` rozszerzono metodę `_rebuild_actor_aliases_index()`:
  * Indeksowane są pełne nazwy wieloczłonowe (`clean_c`), pojedyncze tokeny oraz formy złożone.
  * Dodano fonetyczną normalizację dwuznaków obcych (`ph <-> f`), np. `al_low.replace("ph", "f")` oraz `al_folded.replace("ph", "f")`.
  * W `get_character_gender()` Pass 1 i Pass 1.5 implementują automatyczną samonaprawę (przebudowę indeksu aliasów na żądanie przy braku trafienia, gdy baza zawiera zarejestrowane postaci).

#### 5. Eliminacja Pętli Rewersji Napisów w translator.py (Krok 18)
- Zidentyfikowano i trwale usunięto ukrytą pętlę rewersji w `translate_file`:
  * Dotychczasowy kod w Kroku 18 nadpisywał tekst zdarzeń w `self.subs.events` danymi ze słownika `authoritative_dialogue[i]`.
  * W efekcie wszelkie naprawy wykonane przez `EpisodeQualityGate.audit_and_fix_entire_episode` (Faza 0, Faza 7, Siatka $P_0 \cap \text{EN}$) były cofane tuż przed fizycznym zapisem pliku `.ass` na dysku.
  * Usunięcie słownika `authoritative_dialogue` i oparcie zapisu bezpośrednio na wyjściu z Bramki Jakości zagwarantowało 100% trwałość wszystkich korekt integralnościowych.

#### 6. Tytularna Reguła Wołacza dla Nazw Obcych na `-tz`
- W `series_memory.py` (`generate_polish_name_declension`) oraz `avt_linter.py` (`fix_masculine_vocative_tz`):
  * Wyrazy obce zakończone na afrykatę `-tz` zachowują formę bazową mianownika po odmienionych tytułach i formach grzecznościowych w wołaczu:
    $$\text{Tytuł}_{W} + \text{Nazwa}_{M} \implies \text{„Kapitanie [Name]!”, „Panie [Name]!”}$$
  * Zapobiega to hiperpoprawnym, nienaturalnym deformacjom fleksyjnym po wyrazach takich jak *panie, kapitanie, generale, doktorze, komandorze*.

#### 7. Programowa Bariera Regresji Fazy 2 w `DialogueVerifier`
- W `verifier.py` zaimplementowano metodę `_guard_phase2_regressions(f1_pl, refined_pl, source_en, speaker_p0_gender)`:
  * Blokuje podmianę rodzaju gramatycznego czasowników w Fazie 2 (Script Doctor CoT) przeciwko zweryfikowanemu rodzajowi mówcy $P_0$ z Fazy 1.
  * Eliminuje kalki konstrukcji ciągłych języka angielskiego w formie imiesłowów przymiotnikowych czynnych po łączniku (`być + -ący`, np. *byłem czekający -> czekałem*).
  * Zapewnia pełną zgodność wyjścia z Fazy 2 z kontraktem ontologicznym Fazy 1.

#### 8. Rygorystyczna Higiena ASS i Stabilna Identyfikacja Zdarzeń
- W `EpisodeQualityGate._run_phase_7_hygiene`:
  * Usuwanie zbędnych spacji wewnątrz tagów ASS: `{\\([^}]*?)\s+\}` $\implies$ `{\\\1}` (np. `{\an8  ...}` $\implies$ `{\an8...}`).
  * Przenoszenie wiszących spójników i przyimków (`i, a, o, u, w, z` oraz `że, bo, czy`) stojących bezpośrednio przed znacznikiem łamania wiersza `\N` na początek nowej linii (`\N\1 `).
  * Zamiana niestabilnych indeksów pozycji `Linia #{i+1}` na jednoznaczne, stabilne identyfikatory zdarzeń `[ID: {event_id}]` we wszystkich wpisach audytowych Bramki Jakości w trybie `strict_positive_domain=True`.

---

## 🏆 6. CERTYFIKACJA INTEGRALNOŚCI I TARCZA REGRESYJNA CI/CD

Wdrożenie Architektury Wariantu (d) zostało poddane pełnemu protokołowi weryfikacji 5 warstw:

1. **Test Jednostkowy 183 w `test_system.py` (`test_variant_d_hybrid_evidence_guard_and_pipeline_hardening`):**
   - 8 sekcji asercji sprawdzających pełen zakres funkcjonalności Wariantu (d).
   - Wynik: **1/1 PASSED** (< 5.0 s).
   - Łączny licznik suity: **183/183 PASSED (100% Zero Regression Lock)**.
2. **Certyfikacja Czystości Ontologicznej (`verify_purity.py`):**
   - Wszystkie 11 rygorystycznych bramek AST Standardu 9.0: **11/11 PASS**.
   - Zero instancji, zero preskryptywności, brak zahardkodowanych słowników wyjątków.
3. **Kryminalistyczny Audyt Kodu i Diffu (`audit_diff.ps1`):**
   - Bramka 1/4 (Zero-Cosmetic Gate): **PASS** (modyfikacja rdzenia silnika w Warstwach 1–4).
   - Bramka 2/4 (Zero-Onomastic & Stem Leakage Gate): **PASS** (41 zweryfikowanych nazw i rdzeni, 0 wycieków).
   - Bramka 3/4 (End-to-End Wiring / Dead Code Gate): **PASS** (pełne ożyłkowanie nowych symboli).
   - Bramka 4/4 (Test Integrity Gate): **PASS** (brak nielegalnych mocków domenowych).
   - Werdykt końcowy: **`[VICTORY CONFIRMED -- KOD CZYSTY I UOGÓLNIONY]`**.

---
**KONIEC RAPORTU TECHNICZNEGO POTOKU AVT (CZĘŚĆ II) — TRANSLATOR STANDARD 9.0**

