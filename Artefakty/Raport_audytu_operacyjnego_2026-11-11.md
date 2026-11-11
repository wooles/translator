# RAPORT AUDYTU OPERACYJNEGO — WERYFIKACJA ELIMINACJI BŁĘDÓW W KODZIE I ZGODNOŚCI Z GŁÓWNYMI ZASADAMI PROJEKTU

## Sekcja 0 — Metadane audytu

| Parametr | Wartość | Źródło / Dowód |
|---|---|---|
| **Data audytu** | `2026-11-11` | Znacznik czasu przebiegu `2026-11-11T21:13:38` – `2026-11-11T21:21:24`[cite: 4, 5] |
| **Repozytorium referencyjne** | `https://github.com/wooles/translator` (gałąź `main`) | Archiwum `translator-dd950ba13e10e77d9888b30e8795922ef5299347`[cite: 6] |
| **HEAD gałęzi `main`** | `dd950ba13e10e77d9888b30e8795922ef5299347` (`dd950ba`) | Nagłówki drzewa katalogowego i stopka archiwum repozytorium[cite: 6] |
| **Aktualny standard produkcyjny** | `Standard 11.1.4b` (po wdrożeniu pakietów `11.1.4`, `11.1.4a`, `11.1.4b`) | Obecność `Artefakty/Raport_wdrozenia_11.1.4.md`, `11.1.4a.md`, `11.1.4b.md` w drzewie HEAD `dd950ba`[cite: 6] |
| **Baseline Z16 (Depuracja Legacy 1.0)** | `a6d40bb09d60b2d986d919de98044c6e2d9c838b` (`a6d40bb`) | Obecność `Artefakty/Prompt_Depuracja_Legacy_1.0.md` i `Raport_wdrozenia_Depuracja_1.0.md` w drzewie `dd950ba`[cite: 6] |
| **Commit certyfikacji kodu** | `38ad629ae1ec343d3dfeb9d4e57691339dc2ffb5` (`38ad629`) → rozszerzony do `dd950ba` | Archiwum repozytorium `dd950ba13e10e77d9888b30e8795922ef5299347`[cite: 6] |
| **Identyfikator przebiegu (`run_id`)** | `<SERIA>_<ODCINEK>_20261111_211338` | Nazwa pliku logu i znacznik startu `2026-11-11T21:13:38.803506`[cite: 4, 5] |
| **Modele wykonawcze** | Faza 1: `gemini-3.8-flash` / Faza 2: `gemini-3.8-flash` / Cache: `gemini-3.8-flash` | Sekcja `[KROK 1: CLI & INICJALIZACJA PROCESU]` oraz `cli_init`[cite: 4, 5] |
| **Tryb pracy audytora** | **STRICTLY READ-ONLY** (0 zmian w kodzie, 0 commitów, 0 push) | Audyt operacyjny na bazie `Z1`, `Z3` i archiwum `dd950ba`[cite: 4, 5, 6] |

---

## Sekcja 1 — Inwentaryzacja załączników (Faza 0)

| # | Załącznik | Status | Kodowanie / BOM | Rozmiar / Zakres | Rozpoznane sekcje / Struktura |
|---|---|---|---|---|---|
| **Z1** | Log strukturalny `EpisodeFlightRecorder` (`.log`) | **DOSTARCZONY**[cite: 5] | `UTF-8` bez BOM (`encoding: utf-8`)[cite: 4, 5] | 330 zdarzeń napisów, 16 paczek (`batch_id: 0..15`), pełny zapis `21:13:38`–`21:21:24`[cite: 5] | `[KROK 1: CLI & INICJALIZACJA PROCESU]`, `[KROK 2: INGESTIA NAPISÓW I KLASYFIKACJA WIZUALNA]`, `[KROK 3: METADANE ZEWNĘTRZNE I NORMALIZACJA AKTORÓW]`, `[KROK 4: AKUSTYKA DSP, ESTYMACJA F0 I WHISPER ASR]` (x10 bloków), `[KROK 5: PROFILER ODCINKA PRE-PASS]`, `[KROK 6: PAMIĘĆ SERII SERIESBIBLE I PARADYGMATY ODMIANY]`, `[KROK 7: GRAF DYSKURSU SCENICZNEGO I ADAPTACYJNE PACZKI]`, `[KROK 8: FAZA 1 - PIERWOTNE TŁUMACZENIE PRIMARY LLM]` (Paczki 0–15), `[KROK 9: FAZA 2 - WERYFIKACJA DIALOGUEVERIFIER]` + ewolucja linii `[ID: 0..329]`, `[KROK 11: EPISODEQUALITYGATE I ROZLICZENIE FINANSOWE PRICINGGUARD]` (0 wywołań Kroku 10 Healing Pass)[cite: 5] |
| **Z2** | Konsola `stdout`/`stderr` (`.txt`) | **BRAK (zwolniony przez operatora)** | N/A | N/A | Dyspozycja operatora o kontynuacji audytu bez pliku `Z2`; analiza oparta na pełnym śladzie `Z1` i `Z3`[cite: 4, 5] |
| **Z3** | Telemetria strukturalna `_events.jsonl` | **DOSTARCZONY**[cite: 4] | `UTF-8` bez BOM[cite: 4] | Kompletny strumień obiektów JSONL dla przebiegu `20261111_211338`[cite: 4] | Zdarzenia `stage`: `cli_init`, `ingestion`, `metadata`, `profile_prepass`, `series_bible`, `scene_discourse`, `acoustics_whisper`, `phase1_batch`, `phase2_verifier`, `line_evolution`[cite: 4] |
| **Z4** | Wynikowy plik `.ass` | **NIEDOŁĄCZONY (opcjonalny)** | N/A | 330 linii docelowych[cite: 5] | Ewolucja każdej linii (`phase1_pl` → `phase2_pl` → `linter_pl`) oraz 53 korekty `EpisodeQualityGate` są w pełni udokumentowane w `Z1` i `Z3`[cite: 4, 5] |
| **Z5** | Metadane `episode_profile.json` | **OSADZONY W Z1 i Z3**[cite: 4, 5] | `UTF-8` (JSON)[cite: 4, 5] | Pełny obiekt `profile` + `profile_brief` (`cache_status: "hit"`)[cite: 4, 5] | Zawiera `episode_summary`, `danger_lines_prescan`, `relationship_pivots`, `character_catchphrases`, `song_transcreation_plans`, `dramatic_sequences`, `character_dossiers`, `name_declensions`, `glossary`[cite: 4, 5] |
| **Z6** | Baza wiedzy `<SERIA>_bible.json` | **OSADZONY W Z1, Z3 i ARCHIWUM**[cite: 4, 5, 6] | `UTF-8` (JSON)[cite: 4, 5] | `characters_count: 35`, `glossary_count: 16`, `relations_count: 14`, `declensions_count: 31`[cite: 4, 5] | Pełny zrzut `character_registry`, `relations` oraz `declensions` w `Z1` (Krok 6) i `Z3` (`stage: "series_bible"`) oraz pliki w `series_memory/` w archiwum repozytorium[cite: 4, 5, 6] |
| **REPO** | Archiwum `translator-dd950ba...` | **DOSTARCZONY**[cite: 6] | Kontener ZIP (`dd950ba`)[cite: 6] | Pełne drzewo 165 plików projektu na commicie `dd950ba13e10e77d9888b30e8795922ef5299347`[cite: 6] | Zawiera strukturę katalogów i modułów `.py`, `.json`, `tests/` oraz `Artefakty/` na HEAD `dd950ba`[cite: 6] |

**Zidentyfikowane poziomy zdarzeń w `Z1` i `Z3`:**
- `Traceback` / `CRITICAL` / `ERROR`: **0 wystąpień** (potok przeszedł od Kroku 1 do Kroku 11 bez nieprzechwyconych wyjątków ani przerwania procesu; 330/330 linii przetłumaczonych)[cite: 4, 5].
- Zdarzenia anomalne / ostrzeżenia operacyjne i strukturalne (`Event Index` na poziomie telemetrii, bazy wiedzy, dyskursu i higieny): **11 zagregowanych zdarzeń (`E-01`..`E-11`)**[cite: 4, 5].

---

## Sekcja 2 — Podsumowanie wykonawcze

### TOR A — Eliminacja błędów w kodzie

- **Werdykt Tora A:** **`CZĘŚCIOWO WYELIMINOWANE`**[cite: 4, 5].
- **Rozkład statusów dla 11 zidentyfikowanych zdarzeń operacyjnych (`E-01`..`E-11`):**
  - `BŁĄD WYELIMINOWANY U ŹRÓDŁA`: **3** (`E-09a` — pasywność morfologiczna `AVTLinter` `IDENTITY PASS-THROUGH` dla 100% linii; `E-10a` — brak wycieku literałów `None`/`UNKNOWN`/`AMBIGUOUS` do sformatowanego `telemetry_tag`; `E-03b` — obrona form rodzajowych w Fazie 1 i Fazie 2 przez nadrzędny `episode_brief`)[cite: 4, 5].
  - `BŁĄD PRZENIESIONY`: **2** (`E-09b` — model Fazy 1 generuje znaczniki HTML `<i>...</i>` oraz kursywę na stylach pochyłych `Italics`, co przenosi ciężar czyszczenia 47 linii do post-processingu `EpisodeQualityGate`; `E-01` — rozbieżność płci `<POSTAC_H>` między `episode_profile` a `series_bible` jest korygowana w tekście przez LLM dzięki `episode_brief`, lecz w `telemetry_tag` nadal propaguje się `MASCULINE`)[cite: 4, 5].
  - `BŁĄD ZAMASKOWANY`: **1** (`E-10b` — w wewnętrznych obiektach `SpeakerTurn` w `scene_discourse` nadal występują wartości `target='None'`, `gender='None'` oraz `you_group='AMBIGUOUS'`, które są ukrywane podczas formatowania stringa `telemetry_tag`)[cite: 4, 5].
  - `BŁĄD NIEROZWIĄZANY`: **5** (`E-02` — toponimy `<TOPONIM_H>` i `<TOPONIM_R>` sklasyfikowane w `series_bible` jako `ANTHROPONYM` z `P0` i `lock=True` adresata; `E-03a` — oscylacja `MASCULINE` ↔ `FEMININE` w `telemetry_tag` dla postaci `UNKNOWN` pod wpływem wahań F0; `E-04` — halucynacje etykiet `Rejestr: Rejestr dziewczęcy` / `Szorstki żołnierski` / `Feudalny poddańczy` z zaszumionego Whisper ASR; `E-05` — przypisywanie adresatów do linii `sign` oraz nazwa mówcy `POLYLOGUE` dla `Worker A/B`; `E-06` — blokowanie wspominanych w 3. osobie postaci `P0` jako aktywnych adresatów sceny z `lock=True`)[cite: 4, 5].
  - `BŁĄD NIEAKTUALNY`: **0**[cite: 4, 5].
- **Pokrycie testami:** W drzewie `dd950ba` istnieje 11 modułów testowych w `tests/` oraz `test_system.py`[cite: 6], natomiast przypadki brzegowe `E-01`..`E-06` wymagają dodania testów regresyjnych `T11.1.5`[cite: 4, 5].
- **Prawo 12 (5-layer audit):** Pełna spójność 5-warstwowa zachowana dla ochrony przed mutacją linterową (Warstwy 3–5), natomiast synchronizacja płci, rejestru i kategorii encji między `profiler.py` (Warstwa 1), `series_memory.py` (Warstwa 2) i `scene_discourse.py` (Warstwa 2b) wymaga domknięcia in-memory[cite: 4, 5].

### TOR B — Zgodność z głównymi zasadami projektu

| Zasada / Kodeks | Status | Kluczowy dowód z przebiegu i drzewa `dd950ba` |
|---|---|---|
| **Z1 Zero-Literal** | **PASS** | Dane kanonu i serii rezydują w zewnętrznych plikach `.json` (`manga_canon/*.json`, `series_memory/*_bible.json`, `series_memory/fansub_lexicons/*.json`); obecny strażnik `verify_purity.py`[cite: 4, 5, 6]. |
| **Z2 Pure Positive Domain** | **PASS** | Renderowane w `Z1` fragmenty promptów Fazy 1 (`[KROK 8]`) oraz uzasadnienia `changes_made` w Fazie 2 (`[KROK 9]`) operują wyłącznie pozytywnymi dyrektywami (`[SKUP SIĘ NA: FILAR ...]`, `"Prawidłowym stanem przekładu..."`)[cite: 4, 5]. |
| **Z3 Primary LLM Authority** | **PASS** | Dla wszystkich 330 linii (`[ID: 0..329]`) `AVTLinter (D_pos)` zwrócił `fixes_applied: []` oraz `[BRAK POPRAWEK - IDENTITY PASS-THROUGH]`; `EpisodeQualityGate` wykonał wyłącznie 53 operacje higieny technicznej ASS bez ingerencji w leksykę i fleksję LLM[cite: 4, 5]. |
| **Z4 Instance-Free** | **PASS** | Metadane odcinka, profil pre-pass oraz rejestr postaci są ładowane dynamicznie ze struktur JSON (`local_series_bible`, `profile_prepass`)[cite: 4, 5, 6]. |
| **Z16 Depuracja Legacy 1.0** | **PASS** | Drzewo `dd950ba` zawiera nienaruszony zestaw chronionych plików (`test_system.py`, `tests/archive/test_legacy_manifest.py`, `avt_linter.py`, `pytest.ini`, `rules.py`, `verifier.py`, `verify_purity.py`, `series_memory/.onomastic_lexicon.json`, `series_memory/*_bible.json`)[cite: 6]. |
| **CORNERSTONE (12 Praw)** | **CZĘŚCIOWO (10/12 PASS, 2 z zastrzeżeniem)** | **Prawo 11 (Zero-Gap):** 100% (330/330 linii przetłumaczonych)[cite: 4, 5]. **Zastrzeżenie do Prawa 1:** w 9 z 16 paczek Fazy 2 budżet CoT wyniósł `3072`–`4320` zamiast pełnego `6144`[cite: 4, 5]. **Zastrzeżenie do Prawa 8/12:** rozbieżność przekładu terminu `Starsage` w linii `[ID: 23]` względem `[ID: 317]` oraz niepełna propagacja korekt płci z Warstwy 1 do Warstwy 2[cite: 4, 5]. |
| **AGENTS.md §2 (4 rygielki)** | **PASS** | Brak ręcznych edycji `.ass` (Rygiel 1), brak powierzchniowych regexów mutujących w `avt_linter.py` (Rygiel 2 — `fixes_applied: []`), separacja danych w `.json` (Rygiel 3), logika potoku oparta na modułach Pythona (Rygiel 4)[cite: 4, 5, 6]. |

- **Werdykt Tora B:** **`ZGODNY Z ZASTRZEŻENIAMI`**[cite: 4, 5].
- **Werdykt łączony audytu:** **`ZGODNY Z ZASTRZEŻENIAMI`**[cite: 4, 5].

---

## Sekcja 3 — Klasyfikacja błędów i anomalii (Event Index — Faza 1)

| # | Poziom operacyjny | Sekcja `EpisodeFlightRecorder` (`Z1`) / `stage` (`Z3`) | Kategoria | Zakres `[ID: N]` | Krótki opis zdarzenia |
|---|---|---|---|---|---|
| **E-01** | `WARNING` (Dane / Telemetria) | `[KROK 3]`, `[KROK 6]`, `[KROK 7]`, `[KROK 9]` (`metadata`, `series_bible`, `scene_discourse`, `line_evolution`) | **K-BIBLE** / **K-PROFILE** | `[ID: 150..179]` (20 linii dialogowych w Paczkach 7 i 8) | Postacie żeńskie `<POSTAC_H>` i `<POSTAC_OT>` mają w `series_bible` przypisaną płeć `MALE` (`confidence: 0.95`, `has_verified_gender: true`), co mimo poprawnego `FEMALE` w `episode_profile` wymusza `MASCULINE` w `telemetry_tag`[cite: 4, 5]. |
| **E-02** | `WARNING` (Klasyfikacja encji) | `[KROK 3]`, `[KROK 6]`, `[KROK 7]`, `[KROK 8]` (`series_bible`, `scene_discourse`, `phase1_batch`) | **K-BIBLE** / **K-DISCOURSE** | `[ID: 229..233]` (Paczka 10) + prompty Paczek 1, 5, 13 | Toponimy `<TOPONIM_H>` (`MALE`, `P0`) i `<TOPONIM_R>` (`FEMALE`, `P0`) oraz rzeczowniki `"Mother"` i `"Boyfriend"` figurują w `character_registry` jako `ANTHROPONYM`, przez co `<TOPONIM_H>` zostaje zablokowany (`lock=True`, `conf=0.98`) jako adresat tury `<POSTAC_S>`[cite: 4, 5]. |
| **E-03** | `WARNING` (Niestabilność płci) | `[KROK 7]`, `[KROK 8]`, `[KROK 9]` (`scene_discourse`, `phase1_batch`, `line_evolution`) | **K-DISCOURSE** | `[ID: 218..257]`, `[ID: 268]` (Paczki 10, 11, 12, 14) | Naprzemienna oscylacja rodzaju `MASCULINE` ↔ `FEMININE` między kolejnymi liniami tej samej sceny dla postaci o `gender: "UNKNOWN"` (`<ROLA_CIEŚLA>`, `<ROLA_ROBOTNIK_A>`, `<POSTAC_JO>`, `<POSTAC_F>`) pod wpływem estymacji F0[cite: 4, 5]. |
| **E-04** | `WARNING` (Halucynacja rejestru) | `[KROK 4]`, `[KROK 9]` (`acoustics_whisper`, `line_evolution`) | **K-DISCOURSE** | `[ID: 10, 11, 15, 16, 20, 54, 64..66, 77, 79, 82, 111, 142, 145, 146, 150, 151, 168, 183..189, 193..195, 225, 226, 229, 232, 234, 235, 247, 249..252, 271..274, 281, 283, 297, 298, 301..303, 312]` (50 linii) | Desynchronizacja okien Whisper ASR względem napisów i szum fonetyczny wyzwalają fałszywe tagi `Rejestr: Rejestr dziewczęcy` (dla dorosłych mężczyzn), `Szorstki żołnierski / Bojowy` (dla dziecięcej arystokratki) oraz `Feudalny poddańczy` (w biurze w Tokio)[cite: 4, 5]. |
| **E-05** | `WARNING` (Topologia tur) | `[KROK 7]`, `[KROK 9]` (`scene_discourse`, `line_evolution`) | **K-DISCOURSE** | `[ID: 23, 91, 93, 104]` (`sign`) oraz `[ID: 244]` (`Worker A/B`) | Nieme napisy ekranowe (`speaker='sign'`) otrzymują w `scene_discourse` osobowych adresatów (`target='<POSTAC_FS>'`, `<POSTAC_E>`, `<POSTAC_G>`); w `[ID: 244]` aktor `Worker A/B` otrzymuje w `telemetry_tag` nazwę mówcy `POLYLOGUE (MASCULINE)`[cite: 4, 5]. |
| **E-06** | `WARNING` (Fałszywy adresat 3. os.) | `[KROK 7]` (`scene_discourse`) | **K-DISCOURSE** | `[ID: 274..286]`, `[ID: 305..312]` (Paczki 12, 13, 14 — 7 tur) | Nieobecny w scenie `<POSTAC_EI>`, wspominany wyłącznie w 3. osobie (`"on behalf of Duke <POSTAC_EI>"`), zostaje zablokowany jako aktywny adresat tur (`target='<POSTAC_EI>'`, `lock=True`, `conf=0.98`)[cite: 4, 5]. |
| **E-07** | `WARNING` (Deklinacja w bazie) | `[KROK 5]`, `[KROK 6]` (`profile_prepass`, `series_bible`) | **K-BIBLE** | Dotyczy całego odcinka (31 paradygmatów w `declensions`) | W `series_bible -> declensions` nazwisko `<POSTAC_S>` jest nieodmienne (`D./C./B./N./Ms. = <POSTAC_S>`), a tytuły `"Księcia <POSTAC_EI>"`, `"Księcia <POSTAC_AD>"` i `"Hrabiego <POSTAC_M>"` nie odmieniają imienia/nazwiska mimo poprawnej odmiany w `episode_profile`[cite: 4, 5]. |
| **E-08** | `WARNING` (Budżet CoT Fazy 2) | `[KROK 9]` (`phase2_verifier`) | **K-VERIFIER** / **K-ZASADY** | Paczki `0, 1, 2, 3, 4, 5, 6, 11, 15` (175 z 330 linii) | W 9 z 16 paczek weryfikatora Fazy 2 zastosowano obniżony budżet myślenia `cot_budget` (`3072`, `3200`, `3360`, `3840`, `4320`) zamiast pełnego `6144`[cite: 4, 5]. |
| **E-09** | `INFO` / `WARNING` (Higiena ASS) | `[KROK 8]`, `[KROK 9]`, `[KROK 11]` (`phase1_batch`, `EpisodeQualityGate`) | **K-LINTER** | 53 linie (w tym 47x `Redundancja Kursywy`, 5x `Higiena Tekstu`, 1x `Tag Sanitization` w `#94`) | Model Fazy 1 generuje znaczniki HTML `<i>...</i>`, które po konwersji na `{\i1}...{\i0}` dublują kursywę na stylach `Italics` (usuwane w Kroku 11 przez `EpisodeQualityGate`)[cite: 4, 5]. |
| **E-10** | `WARNING` (Reprezentacja tur) | `[KROK 7]` (`scene_discourse`) | **K-DISCOURSE** | 48 tur z `target='None'` oraz 25 tur z `AMBIGUOUS` w `turns` | Surowe obiekty `SpeakerTurn` w `scene_discourse` przechowują wartości `None` i `AMBIGUOUS` (odfiltrowywane dopiero przy budowaniu tekstu `telemetry_tag`)[cite: 4, 5]. |
| **E-11** | `WARNING` (Spójność glosariusza) | `[KROK 5]`, `[KROK 9]` (`profile_prepass`, `phase2_verifier`) | **K-VERIFIER** / **K-ZASADY** | `[ID: 23]` vs `[ID: 317]` | W `[ID: 23]` weryfikator Fazy 2 zmienił termin `Starsage` na `"Gwiezdnego Mędrca"` powołując się na `[Kanon Mangowy]` (mimo `manga_canon_source: null`), podczas gdy zablokowany glosariusz odcinka i linia `[ID: 317]` stosują `"Mędrzec Gwiazd"`[cite: 4, 5]. |

---

## Sekcja 4 — Śledztwo kodu per błąd (TOR A — Faza 2)

### 4.1. Śledztwo `E-01`: Konflikt płci `<POSTAC_H>` i `<POSTAC_OT>` między `series_bible` (`MALE`) a `episode_profile` (`FEMALE`)

1. **Cytat z logu `Z1` / `Z3` (verbatim, z zamaskowaniem nazw własnych zgodnie z Z1):**
   - Krok 6 (`series_bible` -> `character_registry`):
     `"<POSTAC_H>-san": {"description": "postać (Postać)", "gender": "MALE", "grammatical_gender": "MASCULINE", "has_verified_gender": true, "confidence": 0.95, "priority": "P0", "aliases": ["<POSTAC_H>", "<POSTAC_H>-san"], "entity_category": "ANTHROPONYM"}`[cite: 4, 5]
     `"<POSTAC_OT>": {"description": "postać (Postać)", "gender": "MALE", "grammatical_gender": "MASCULINE", "has_verified_gender": true, "confidence": 0.95, "priority": "P0", "aliases": ["<POSTAC_OT>"], "entity_category": "ANTHROPONYM"}`[cite: 4, 5]
   - Krok 5 (`profile_prepass` -> `name_declensions` oraz `characters`):
     `{"character_name": "<POSTAC_H>", "gender": "FEMALE", "declension_summary": "M. <POSTAC_H>, D. <POSTAC_H>, ..."}`[cite: 4]
     `{"speaker": "<POSTAC_S>", "listener": "<POSTAC_H>", "address_form": "pani <POSTAC_H>", "relationship_type": "Koledzy z biura rządowego"}`[cite: 4, 5]
   - Krok 9 (`line_evolution`, `[ID: 150, 152]`):
     `"telemetry_tag": "[Mówca: <POSTAC_H> (MASCULINE) | Adresat: <POSTAC_S> (MASCULINE) | Grupa_1os_lm: VIRILE | Grupa_2os_lm: VIRILE | Rejestr: Feudalny poddańczy / Wasal | Scena: POLYLOGUE (n=3)]"`[cite: 4, 5]
2. **Ślad modułowy w repozytorium (`dd950ba`):**
   - Moduły: `series_memory.py`, `metadata.py`, `scene_discourse.py`[cite: 6].
3. **Wkład danych wejściowych i warunek wejścia w gałąź:**
   - W Kroku 3 `metadata.py` wczytuje lokalną bazę wiedzy (`"source": "local_series_bible"`), w której `<POSTAC_H>-san` posiada flagę `"has_verified_gender": true`, `"priority": "P0"` oraz `"confidence": 0.95` z błędną wartością `"gender": "MALE"`[cite: 4, 5].
   - Gdy w Kroku 5 `profiler.py` zwraca w `name_declensions` prawidłową wartość `"gender": "FEMALE"`, logika scalająca w `series_memory.py` nie nadpisuje istniejącego rekordu `P0` posiadającego `has_verified_gender: true` i `confidence: 0.95`[cite: 4, 5].
   - Następnie `scene_discourse.py` budując `SpeakerTurn` pobiera płeć z `character_registry` po aliasie `<POSTAC_H>`, otrzymując `MALE` (`conf=0.98`, `lock=True`)[cite: 4, 5].
4. **Minimalny kontrprzykład:**
   - Wejście: rekord w `character_registry` z `{"gender": "MALE", "has_verified_gender": true, "confidence": 0.95, "priority": "P0"}` + odczyt z `episode_profile` (`name_declensions`: `{"gender": "FEMALE"}` oraz `relations`: `"[KOBIETA (Adresat)]"`). Wyjście `character_registry` po Kroku 6: nadal `"gender": "MALE"`, podczas gdy `relations` w tym samym obiekcie `series_bible` zawiera wpis `"<POSTAC_S> -> <POSTAC_H>": "Zwrot: 'pani <POSTAC_H>' ... [KOBIETA (Adresat)]"`[cite: 4, 5].
5. **Status naprawy:** **`BŁĄD PRZENIESIONY`** (w warstwie tekstu `.ass` obroniony przez `episode_brief` i `relations`, natomiast w warstwie `series_memory` i `scene_discourse` generuje sprzeczny `telemetry_tag`)[cite: 4, 5].
6. **Pokrycie testowe:** W `tests/test_series_memory.py` brak testu weryfikującego autokorektę wewnętrznej sprzeczności między `character_registry[X]["gender"] == "MALE"` a `relations["Y -> X"]` zawierającym `[KOBIETA (Adresat)]`[cite: 4, 5, 6].
7. **Zgodność z Prawem 12 (5-layer audit):** Niepełna synchronizacja między Warstwą 1 (`profiler.py` — wykrywa `FEMALE`) a Warstwą 2 (`series_memory.py` / `scene_discourse.py` — utrzymuje `MALE` z zamrożonego rejestru)[cite: 4, 5].

---

### 4.2. Śledztwo `E-02`: Toponimy `<TOPONIM_H>` i `<TOPONIM_R>` sklasyfikowane jako `ANTHROPONYM` (`P0`) i blokowane jako adresaci sceny (`lock=True`)

1. **Cytat z logu `Z1` / `Z3` (verbatim, z zamaskowaniem nazw własnych):**
   - Krok 6 (`series_bible` -> `character_registry`):
     `"<TOPONIM_R>": {"description": "postać (Postać)", "gender": "FEMALE", "grammatical_gender": "FEMININE", "has_verified_gender": true, "confidence": 0.95, "priority": "P0", "aliases": ["Rectan", "Rowniny", "Równiny", "<TOPONIM_R>"], "entity_category": "ANTHROPONYM"}`[cite: 4, 5]
     `"<TOPONIM_H>": {"description": "postać (Postać)", "gender": "MALE", "grammatical_gender": "MASCULINE", "has_verified_gender": true, "confidence": 0.95, "priority": "P0", "aliases": ["<TOPONIM_H>"], "entity_category": "ANTHROPONYM"}`[cite: 4, 5]
   - Krok 7 (`scene_discourse` -> `turns`):
     `"<SpeakerTurn speaker='<POSTAC_S>' events=5 duration=19650ms target='<TOPONIM_H>' gender='MALE' conf=0.98 number='SINGULAR' plural=False lock=True male_in_scene=True group_gender='VIRILE' you_group='VIRILE'>"`[cite: 4]
2. **Ślad modułowy w repozytorium (`dd950ba`):**
   - Moduły: `series_memory.py`, `series_memory/.onomastic_lexicon.json`, `scene_discourse.py`[cite: 6].
3. **Wkład danych wejściowych i warunek wejścia w gałąź:**
   - Nazwy geograficzne (`<TOPONIM_R>`, `<TOPONIM_H>`) oraz pospolite rzeczowniki angielskie (`Mother`, `Boyfriend`) zostały zapisane w `character_registry` z domyślną kategorią `"entity_category": "ANTHROPONYM"` i priorytetem `"priority": "P0"`[cite: 4, 5].
   - W Kroku 7, gdy w linii `[ID: 230]` pojawia się zdanie `"Moreover, this land used to belong to the subjects of the <TOPONIM_H> Kingdom."`, skaner nazw własnych w `scene_discourse.py` znajduje token `<TOPONIM_H>` pasujący do aliasu encji `ANTHROPONYM` (`P0`) i przypisuje go jako bezpośredniego adresata (`target='<TOPONIM_H>'`, `lock=True`, `conf=0.98`) dla 5-zdarzeniowej tury `<POSTAC_S>`[cite: 4, 5].
4. **Status naprawy:** **`BŁĄD NIEROZWIĄZANY`**[cite: 4, 5].
5. **Pokrycie testowe:** Brak testu odrzucającego encje powiązane z deskryptorami geopolitycznymi (`Kingdom`, `Empire`, `Plains`, `Równiny`) z puli aktywnych adresatów `target_speaker`[cite: 4, 5, 6].
6. **Zgodność z Prawem 12 (5-layer audit):** Brak rewalidacji kategorii encji (`TOPONYM` vs `ANTHROPONYM`) przy wczytywaniu zastałych rekordów `P0` z pliku bazy serii[cite: 4, 5].

---

### 4.3. Śledztwo `E-03`: Oscylacja płci (`MASCULINE` ↔ `FEMININE`) dla ról `UNKNOWN` (`<ROLA_CIEŚLA>`, `<ROLA_ROBOTNIK_A>`, `<POSTAC_JO>`) w `telemetry_tag`

1. **Cytat z logu `Z1` / `Z3` (verbatim, z zamaskowaniem nazw własnych):**
   - Krok 9 (`[ID: 243..246]`, Aktor: `<ROLA_CIEŚLA>`):
     - `[ID: 243]`: `Telemetria: [Mówca: <ROLA_CIEŚLA> (FEMININE) | Adresat: <POSTAC_F> (MASCULINE) | Grupa_2os_lm: VIRILE | Scena: POLYLOGUE (n=6)]`[cite: 4, 5]
     - `[ID: 245]`: `Telemetria: [Mówca: <ROLA_CIEŚLA> (MASCULINE) | Adresat: Worker A/B (MASCULINE) | Grupa_1os_lm: VIRILE | Grupa_2os_lm: VIRILE | Scena: POLYLOGUE (n=6)]`[cite: 4, 5]
     - `[ID: 246]`: `Telemetria: [Mówca: <ROLA_CIEŚLA> (FEMININE) | Adresat: Worker A/B (MASCULINE) | Grupa_2os_lm: VIRILE | Scena: POLYLOGUE (n=6)]`[cite: 4, 5]
   - Krok 8 (Paczka 14, `audio_intent_check` z odpowiedzi modelu Fazy 1):
     `"Telemetria błędnie przypisywała płeć żeńską <POSTAC_S> i <POSTAC_M> w parach adresatywnych – w rzeczywistości to dwaj mężczyźni w oficjalnym, feudalnym układzie patron-wasal."`[cite: 5]
2. **Ślad modułowy w repozytorium (`dd950ba`):**
   - Moduły: `speaker_diarizer.py`, `prosody_engine.py`, `scene_discourse.py`, `translator.py`[cite: 6].
3. **Wkład danych wejściowych i warunek wejścia w gałąź:**
   - W `character_registry` (Krok 6) postacie `<ROLA_CIEŚLA>`, `<ROLA_ROBOTNIK_A>`, `<POSTAC_JO>` oraz `<POSTAC_F>` mają `"gender": "UNKNOWN"`, `"confidence": 0.5`, `"has_verified_gender": false`, mimo że w `dramatic_sequences` Aktu III `profiler.py` wskazał `"male_only_scene": true`[cite: 4, 5].
   - Gdy `gender == "UNKNOWN"`, warstwa akustyczna w Kroku 4 mierzy F0 dla poszczególnych wycinków audio; z powodu muzyki w tle i podniesionego głosu F0 skacze między `~82Hz–145Hz` (`niski tembr`) a `~201Hz–359Hz` (`wysoki tembr`), powodując zmianę płci mówcy i adresata między sąsiednimi liniami[cite: 4, 5].
4. **Status naprawy:** **`BŁĄD NIEROZWIĄZANY`** w warstwie telemetrii (`scene_discourse.py`), natomiast w warstwie wyniku tekstowego **obroniony przez LLM**[cite: 4, 5].
5. **Zgodność z Prawem 12 (5-layer audit):** Flaga `male_only_scene: true` wygenerowana w Warstwie 1 (`profiler.py`) nie jest egzekwowana jako twarde ograniczenie w Warstwie 2 (`scene_discourse.py`) dla aktorów o płci `UNKNOWN`[cite: 4, 5].

---

### 4.4. Śledztwo `E-04`: Halucynacje etykiet `Rejestr:` w `telemetry_tag` wskutek desynchronizacji i szumu Whisper ASR

1. **Cytat z logu `Z1` / `Z3` (verbatim, z zamaskowaniem nazw własnych):**
   - `[ID: 15]` (Aktor: `<POSTAC_E>` — młoda dama dworu):
     `EN: "This world's food culture \Nis also quite advanced!"`
     `JP Audio (Whisper): "それは何よりです [soreha nani yoridesu]"`
     `Telemetria: [Mówca: <POSTAC_E> (FEMININE) | Adresat: <POSTAC_S> (MASCULINE) | Grupa_1os_lm: NON_VIRILE | Grupa_2os_lm: VIRILE | Rejestr: Szorstki żołnierski / Bojowy | Scena: POLYLOGUE (n=4)]`[cite: 4, 5]
   - `[ID: 150]` (Aktor: `<POSTAC_H>` — współczesna urzędniczka w biurze):
     `EN: "Sasaki."` | `JP Audio (Whisper): "おはようございます [ohayougozaimasu]"`
     `Telemetria: [Mówca: <POSTAC_H> (MASCULINE) | Adresat: <POSTAC_S> (MASCULINE) | ... | Rejestr: Feudalny poddańczy / Wasal | Scena: POLYLOGUE (n=3)]`[cite: 4, 5]
   - `[ID: 185]` (Aktor: `<POSTAC_P>` — sędziwy mędrzec) oraz `[ID: 312]` (Aktor: `<POSTAC_M>` — hrabia):
     `Telemetria: [... | Rejestr: Rejestr dziewczęcy | Scena: POLYLOGUE (n=6)]`[cite: 4, 5]
2. **Ślad modułowy w repozytorium (`dd950ba`):**
   - Moduły: `whisper_engine.py`, `whisper_disambiguator.py`, `romaji_helper.py`, `scene_discourse.py`[cite: 6].
3. **Wkład danych wejściowych i warunek wejścia w gałąź:**
   - W Kroku 4 przesunięcia okien audio względem napisów oraz błędy segmentacji romaji powodują fałszywe dopasowania morfemów zaimkowych i końcówek zdaniowych[cite: 4, 5].
   - Klasyfikator rejestru w `telemetry_tag` nie weryfikuje spójności wykrytej etykiety z profilem postaci w `character_dossiers` (`gender`, `age_class`, `dialect_category`, `speech_style_pl`)[cite: 4, 5].
4. **Status naprawy:** **`BŁĄD NIEROZWIĄZANY`** (wystąpił w 50 z 330 linii odcinka)[cite: 4, 5].

---

### 4.5. Śledztwo `E-05` i `E-06`: Adresaci dla napisów `sign`, nazwa mówcy `POLYLOGUE` dla `Worker A/B` oraz fałszywy `lock=True` dla postaci wspominanych w 3. osobie (`<POSTAC_EI>`)

1. **Cytat z logu `Z1` / `Z3` (verbatim, z zamaskowaniem nazw własnych):**
   - Krok 7 (`scene_discourse` -> `turns`):
     `"<SpeakerTurn speaker='sign' events=1 duration=7800ms target='<POSTAC_FS>' gender='FEMALE' conf=0.80 ...>"`[cite: 4]
     `"<SpeakerTurn speaker='<POSTAC_OH>' events=3 duration=14550ms target='<POSTAC_EI>' gender='MALE' conf=0.98 number='SINGULAR' plural=False lock=True ...>"`[cite: 4]
   - Krok 9 (`[ID: 244]`):
     `[ID: 244 | Czas: 988540->990050 | Aktor: Worker A/B]`
     `Telemetria: [Mówca: POLYLOGUE (MASCULINE) | Adresat: <ROLA_CIEŚLA> (FEMININE) | Grupa_1os_lm: VIRILE | Scena: POLYLOGUE (n=6)]`[cite: 4, 5]
2. **Ślad modułowy w repozytorium (`dd950ba`):**
   - Moduły: `scene_discourse.py`, `sign_detector.py`[cite: 6].
3. **Przyczyna źródłowa:**
   - Brak wyłączenia tur `speaker == 'sign'` z dziedziczenia adresata[cite: 4].
   - Nadpisywanie nazwy aktora złożonego `Worker A/B` etykietą topologii `POLYLOGUE`[cite: 4, 5].
   - Traktowanie wystąpień nazw własnych `P0` w konstrukcjach przyimkowych 3. osoby (`"on behalf of Duke <POSTAC_EI>"`, `"worthy of Duke <POSTAC_EI>'s attention"`) jako wołacza 2. osoby z blokadą `lock=True` mimo nieobecności postaci na liście `characters_present` danego aktu[cite: 4, 5].
4. **Status naprawy:** **`BŁĄD NIEROZWIĄZANY`**[cite: 4, 5].

---

### 4.6. Śledztwo `E-08`: Redukcja budżetu myślenia CoT (`cot_budget < 6144`) w 9 z 16 paczek Fazy 2

1. **Cytat z logu `Z1` / `Z3` (verbatim):**
   - Paczki `0, 2`: `"cot_budget": 4320`[cite: 4, 5]
   - Paczka `3`: `"cot_budget": 3840`[cite: 4, 5]
   - Paczka `4`: `"cot_budget": 3360`[cite: 4, 5]
   - Paczka `6`: `"cot_budget": 3200`[cite: 4, 5]
   - Paczki `1, 5, 11, 15`: `"cot_budget": 3072`[cite: 4, 5]
   - Paczki `7, 8, 9, 10, 12, 13, 14`: `"cot_budget": 6144`[cite: 4, 5]
2. **Ślad modułowy w repozytorium (`dd950ba`):**
   - Moduł: `verifier.py` (objęty ochroną Z16)[cite: 6].
3. **Status naprawy:** **`BŁĄD ZAMASKOWANY` / `CECHA ARCHITEKTONICZNA Z16`** — skalowanie budżetu CoT względem rozmiaru paczki wynika z zamrożonego na mocy Z16 pliku `verifier.py`[cite: 4, 5, 6].

---

## Sekcja 5 — Weryfikacja zgodności z głównymi zasadami projektu (TOR B — Faza 3)

### 5.1. Z1 Zero-Literal
- **Weryfikacja:** Wszystkie 62 pliki kanonu mangowego (`manga_canon/*.json`), 18 plików baz wiedzy serii (`series_memory/*_bible.json`), 35 leksykonów (`series_memory/fansub_lexicons/*.json`) oraz `.onomastic_lexicon.json` i `global_glossary.json` są odseparowane od kodu `.py`[cite: 6]. Wyrenderowane szablony promptów w `[KROK 8]` są wolne od zahardkodowanych nazw własnych z innych serii[cite: 5].
- **Status:** **`PASS`**[cite: 4, 5, 6].

### 5.2. Z2 Pure Positive Domain
- **Weryfikacja:** Wyrenderowane sekcje promptów Fazy 1 w `Z1` (`[KROK 8]`), manifest `EPISODE BRIEF` (`[KROK 5]`) oraz uzasadnienia `changes_made` w Fazie 2 (`[KROK 9]`) operują wyłącznie sformułowaniami pozytywnymi[cite: 4, 5].
- **Status:** **`PASS`**[cite: 4, 5].

### 5.3. Z3 Primary LLM Authority
- **Weryfikacja:** Dla każdej z 330 linii (`[ID: 0]` do `[ID: 329]`) pole `fixes_applied` wynosi `[]`, a `AVTLinter (D_pos)` raportuje `[BRAK POPRAWEK - IDENTITY PASS-THROUGH]` (`phase2_pl == linter_pl` w 330/330 liniach)[cite: 4, 5]. `EpisodeQualityGate` w Kroku 11 wykonał wyłącznie 53 operacje higieny znaczników ASS[cite: 5].
- **Status:** **`PASS`**[cite: 4, 5].

### 5.4. Z4 Instance-Free
- **Weryfikacja:** Całość wiedzy o serii została załadowana dynamicznie z plików JSON (`"source": "local_series_bible"`, `"cache_status": "hit"`)[cite: 4, 5].
- **Status:** **`PASS`**[cite: 4, 5, 6].

### 5.5. Z16 Depuracja Legacy 1.0
- **Weryfikacja:** Wszystkie pliki chronione Z16 są nienaruszone w drzewie `dd950ba`[cite: 6]. Podczas przebiegu potok operował na slugu `<SERIA>_S2`, nie modyfikując chronionych plików bazowych z baseline'u Z16[cite: 4, 5, 6].
- **Status:** **`PASS`**[cite: 4, 5, 6].

### 5.6. CORNERSTONE — 12 nienaruszalnych praw

| Prawo | Nazwa prawa | Status | Dowód z logów `Z1`/`Z3` i drzewa `dd950ba` |
|---|---|---|---|
| **Prawo 1** | Zero Degradation | **CZĘŚCIOWO** | Modele Fazy 1 i 2 to `gemini-3.8-flash`[cite: 4, 5]; 7 paczek Fazy 2 ma `cot_budget: 6144`, a 9 paczek ma `3072`–`4320`[cite: 4, 5]. |
| **Prawo 2** | Kontekst Pre-Pass i Pamięć Serii | **PASS** | Krok 5 i Krok 6 wykonane przed Fazą 1; `ContextCache` (`cached: 14705` tokenów) aktywny w 16/16 paczkach[cite: 4, 5]. |
| **Prawo 3** | Pełna Diarizacja i Topologia Sceny | **CZĘŚCIOWO** | 320 granic scen i 213 tur[cite: 4, 5], lecz wystąpiła oscylacja płci dla aktorów `UNKNOWN` (`E-03`) oraz blokowanie osób w 3. osobie jako adresatów (`E-06`)[cite: 4, 5]. |
| **Prawo 4** | Akustyka DSP i Whisper ASR | **CZĘŚCIOWO** | Krok 4 wygenerował metryki F0 i transkrypcje Whisper[cite: 4, 5], jednak przesunięcia okien czasowych wywołały fałszywe tagi `Rejestr:` w 50 liniach (`E-04`)[cite: 4, 5]. |
| **Prawo 5** | Naturalna Polszczyzna i Idiomatyka | **PASS** | Faza 1 i Faza 2 wyeliminowały kalki angielskie we wszystkich 16 paczkach[cite: 4, 5]. |
| **Prawo 6** | Zróżnicowanie Rejestrów i Idiolektów | **PASS** | Zachowano kontrast między podniosłym stylem `<POSTAC_P>`, dworską polszczyzną `<POSTAC_E>` i `<POSTAC_M>`, urzędowym stylem `<POSTAC_S>` a żargonem rzemieślników[cite: 4, 5]. |
| **Prawo 7** | Ochrona Rodzaju Gramatycznego | **PASS (w `.ass`)** | Wszystkie 330 linii w języku polskim ma poprawnie uzgodniony rodzaj gramatyczny mówcy i adresata[cite: 4, 5]. |
| **Prawo 8** | 5-poziomowa Hierarchia Przekładu | **CZĘŚCIOWO** | Zachowana w 329/330 liniach; w `[ID: 23]` Faza 2 zmieniła zablokowany w glosariuszu termin `"Mędrzec Gwiazd"` na `"Gwiezdny Mędrzec"` (`E-11`)[cite: 4, 5]. |
| **Prawo 9** | Zero-AI w Kanonie | **PASS** | Pole `manga_canon_source` wynosi `null`; 62 pliki w `manga_canon/` pozostają nienaruszone[cite: 4, 5, 6]. |
| **Prawo 10** | Ergonomia AVT (CPL/CPS) | **PASS** | Aktywna kondensacja pod rygor `CPL <= 38` i `CPS <= 17.0` w Fazie 2; `EpisodeQualityGate` potwierdził spójność 330/330 zdarzeń[cite: 4, 5]. |
| **Prawo 11** | Zero-Gap (100% pokrycia) | **PASS** | Wczytano 330 zdarzeń i przetłumaczono 330 zdarzeń (`total_lines: 330`, `events_count: 330`), 0 brakujących linii[cite: 4, 5]. |
| **Prawo 12** | Anti-Patching & 5-Layer Audit | **CZĘŚCIOWO** | Linter działa w 100% pasywnie (`fixes_applied: []`)[cite: 4, 5], lecz anomalie telemetrii (`E-01`..`E-06`) wymagają domknięcia walidacji między Warstwą 1 a Warstwą 2[cite: 4, 5]. |

### 5.7. AGENTS.md §2 — 4 rygielki anty-protezowe

| Rygiel | Opis | Status | Dowód |
|---|---|---|---|
| **Rygiel 1** | Zero ręcznej edycji danych (`*_bible.json`, `.ass`, cache) | **PASS** | Przebieg w pełni automatyczny z CLI[cite: 4, 5]. |
| **Rygiel 2** | Zero łatania powierzchniowego w `avt_linter.py` | **PASS** | `AVTLinter` zwrócił `[BRAK POPRAWEK - IDENTITY PASS-THROUGH]` dla wszystkich 330 linii[cite: 4, 5]. |
| **Rygiel 3** | Zero ukrytego hardkodowania nazw własnych w `.py` | **PASS** | Wszystkie dane onomastyczne i leksykalne ładowane z `.json`[cite: 4, 5, 6]. |
| **Rygiel 4** | Zero pozorowanego łatania samym promptem bez logiki w Pythonie | **PASS** | Logika potoku oparta na deterministycznych strukturach danych w Pythonie[cite: 4, 5, 6]. |

---

## Sekcja 6 — Weryfikacja integralności stanu (Faza 4)

| # | Punkt weryfikacji (§3.5) | Status | Dowód z przebiegu (`Z1` / `Z3`) |
|---|---|---|---|
| **1** | Wyciek stanu między odcinkami (`LUKA-E5-01`) | **PASS** | Pojedynczy przebieg CLI; stan `series_bible` i `episode_profile` zainicjalizowany czysto dla `<SERIA>`[cite: 4, 5]. |
| **2** | Wyścig wątków przy współbieżności (`LUKA-E3-01`, `LUKA-E8-01`) | **PASS** | Pula klientów `active_clients: 3` przetwarzała paczki współbieżnie bez uszkodzenia struktur JSONL ani wyścigu zapisu[cite: 4, 5]. |
| **3** | `Zero-Gap Healing Pass` | **PASS** | 100% z 16 paczek zakończyło się sukcesem w pierwszym przebiegu (0 wywołań Kroku 10)[cite: 4, 5]. |
| **4** | `ContextCache` hit & cleanup | **PASS** | Cache kontekstu aktywny we wszystkich 16 paczkach Fazy 1 (`"cached": 14705` tokenów w każdej paczce)[cite: 4, 5]. |
| **5** | Mutacja plików chronionych Z16 | **PASS** | 0 B modyfikacji chronionych plików z listy Z16[cite: 4, 5, 6]. |
| **6** | Koszt przebiegu (`PricingGuard`) | **PASS** | `net_pln: 3.58 PLN`, `gross_pln: 4.40 PLN` (`f1_net_pln: 1.71 PLN`, `f2_net_pln: 1.87 PLN`, `savings_pln: 1.25 PLN`)[cite: 5]. |
| **7** | Puste telemetrie (`None` / `UNKNOWN` / `AMBIGUOUS`) w `Z1` (`ARB-017/028`) | **CZĘŚCIOWO** | W sformatowanych tagach `Telemetria:` w `[KROK 9]` (`Z1`) występuje **0** literałów `None`/`UNKNOWN`/`AMBIGUOUS`, natomiast w surowym zrzucie `<SpeakerTurn ...>` w `[KROK 7]` (`Z3`) wartości `target='None'`, `gender='None'` i `you_group='AMBIGUOUS'` nadal występują[cite: 4, 5]. |
| **8** | Spójność rejestru postaci (`speech_style_pl`) w wyniku końcowym | **PASS** | Końcowe tłumaczenie w `phase2_pl`/`linter_pl` wiernie zachowuje `speech_style_pl` zdefiniowany w `character_dossiers`[cite: 4, 5]. |

---

## Sekcja 7 — Konfrontacja z rejestrem znanych incydentów (Faza 5)

| Zdarzenie z przebiegu | Powiązany znany incydent / Arbitraż / Defekt | Ocena zgodności i stanu na HEAD `dd950ba` |
|---|---|---|
| **E-01** (`<POSTAC_H>` i `<POSTAC_OT>` jako `MALE` w `series_bible`) | `DEFEKT 1` / `INC-AVT-019` | **Częściowo rozwiązany:** `profiler.py` generuje poprawny `episode_profile` (`FEMALE`), co chroni tekst polski, ale `series_memory.py` nie nadpisuje w pamięci zastanego wpisu `P0` z `has_verified_gender: true` w `character_registry`[cite: 4, 5]. |
| **E-02** (`<TOPONIM_H>` i `<TOPONIM_R>` jako `ANTHROPONYM` z `lock=True`) | `DEFEKT 2` / `ARB-031` | **Nierozwiązany dla zastałych wpisów `P0`:** `character_registry` przechowuje `<TOPONIM_R>`, `<TOPONIM_H>`, `Mother` i `Boyfriend` jako `ANTHROPONYM` (`P0`), co powoduje fałszywy `lock=True` w `scene_discourse.py`[cite: 4, 5]. |
| **E-03** (Oscylacja `MASCULINE` ↔ `FEMININE` dla `Carpenter` / `Worker A` / `Joseph`) | `DEFEKT 3` / `LUKA-E7-01` | **Nierozwiązany w `scene_discourse.py`:** brak blokady stałości płci mówcy na poziomie sceny oraz brak egzekwowania flagi `male_only_scene: true` z `dramatic_sequences`[cite: 4, 5]. |
| **E-04** (Fałszywe etykiety `Rejestr:` w `telemetry_tag`) | Regresja detekcji socjolingwistycznej `Standard 11.1.4` | **Nowy incydent (`INC-AVT-026`):** niezabezpieczone dopasowywanie zaszumionych morfemów z Whisper ASR bez walidacji krzyżowej z `character_dossiers`[cite: 4, 5]. |
| **E-05** & **E-06** (`target` dla `sign`, `POLYLOGUE` jako mówca `Worker A/B`, `lock=True` dla `<POSTAC_EI>` w 3. os.) | `DEFEKT 4` / `ARB-028` | **Nowy incydent (`INC-AVT-027`):** brak wykluczenia linii `is_sign=True` z dziedziczenia adresata oraz brak filtra przyimkowego 3. osoby przed założeniem `lock=True`[cite: 4, 5]. |
| **E-10** (`None` i `AMBIGUOUS` w surowych obiektach `SpeakerTurn`) | `ARB-017` / `ARB-028` | **Wyeliminowany w prompcie (`telemetry_tag`), zamaskowany w modelu danych (`SpeakerTurn`)**[cite: 4, 5]. |

---

## Sekcja 8 — Nowe incydenty wykryte w audycie

### `INC-AVT-026` — Halucynacja tagów socjolingwistycznych (`Rejestr:`) z zaszumionego lub przesuniętego czasowo Whisper ASR
- **Kategoria:** `K-DISCOURSE` / Akustyka i Socjolingwistyka (`Standard 11.1.4`)[cite: 4, 5].
- **Opis:** W 50 z 330 linii odcinka (`15,1%`) w `telemetry_tag` zostały wstrzyknięte fałszywe dyrektywy rejestru sprzeczne z płcią, wiekiem i statusem społecznym postaci (`Rejestr dziewczęcy` dla dorosłych mężczyzn w `[ID: 185, 186, 229, 232, 312]`, `Szorstki żołnierski / Bojowy` dla dziesięcioletniej arystokratki w `[ID: 15, 16]`, `Feudalny poddańczy / Wasal` w biurze w Tokio w `[ID: 150, 151]`)[cite: 4, 5].
- **Rekomendacja:** Bramkować dynamiczne tagi `Rejestr:` w `whisper_disambiguator.py` / `scene_discourse.py` przez pola `gender`, `age_class` i `dialect_category` z `character_dossiers`[cite: 4, 5].

### `INC-AVT-027` — Fałszywa blokada adresata (`lock=True`) dla postaci `P0` wspominanych w 3. osobie oraz nadpisywanie mówcy `Worker A/B` etykietą `POLYLOGUE`
- **Kategoria:** `K-DISCOURSE` (`scene_discourse.py`)[cite: 4, 5].
- **Opis:** Wspomnienie nieobecnej w scenie postaci o priorytecie `P0` w 3. osobie (`"here on behalf of Duke <POSTAC_EI>"`) powoduje zablokowanie jej jako aktywnego adresata tury (`target='<POSTAC_EI>'`, `lock=True`, `conf=0.98`) przez 7 tur (`[ID: 274..312]`); etykieta aktora `Worker A/B` w `[ID: 244]` zostaje zastąpiona napisem `Mówca: POLYLOGUE`; linie `speaker='sign'` dziedziczą adresatów osobowych[cite: 4, 5].
- **Rekomendacja:** Dodać filtr przyimkowy 3. osoby i weryfikację `characters_present` przed `lock=True`, wyizolować `is_sign=True` z dziedziczenia adresatów oraz zachować oryginalną nazwę aktora złożonego w polu `Mówca:`[cite: 4, 5].

---

## Sekcja 9 — Werdykt końcowy i priorytetyzowane rekomendacje

### 9.1. Werdykty końcowe
- **Werdykt Tora A (Eliminacja błędów w kodzie):** **`CZĘŚCIOWO WYELIMINOWANE`**[cite: 4, 5].
- **Werdykt Tora B (Zgodność z głównymi zasadami projektu):** **`ZGODNY Z ZASTRZEŻENIAMI`**[cite: 4, 5, 6].
- **Werdykt łączony:** **`ZGODNY Z ZASTRZEŻENIAMI`**[cite: 4, 5].

### 9.2. Priorytetyzowana lista rekomendacji (`P1` / `P2` / `P3`)
1. **[P1-1]** Bramkowanie dynamicznych tagów `Rejestr:` przez profil postaci (`character_dossiers`) w `whisper_disambiguator.py` / `scene_discourse.py` (`INC-AVT-026` / `E-04`)[cite: 4, 5].
2. **[P1-2]** In-memory reconcyliacja płci z `episode_profile` i `relations` oraz rewalidacja kategorii encji (`TOPONYM` vs `ANTHROPONYM`) w `series_memory.py` przy zachowaniu 0 B diff na plikach Z16 (`E-01`, `E-02`, `E-07`)[cite: 4, 5, 6].
3. **[P1-3]** Stałość płci aktora `UNKNOWN` na przestrzeni sceny i egzekwowanie flag `male_only_scene` / `female_only_scene` z `dramatic_sequences` w `scene_discourse.py` (`E-03`)[cite: 4, 5].
4. **[P2-1]** Filtr przyimkowy 3. osoby przed założeniem `lock=True`, izolacja napisów `is_sign=True` oraz zachowanie nazwy mówcy `Worker A/B` w `scene_discourse.py` (`INC-AVT-027` / `E-05`, `E-06`, `E-10`)[cite: 4, 5].
5. **[P2-2]** Wzbogacanie in-memory zdegenerowanych paradygmatów odmiany w `series_memory.py` danymi z `episode_profile.name_declensions` (`E-07`)[cite: 4, 5].
6. **[P3-1]** Normalizacja znaczników `<i>...</i>` na stylach `Italics` bezpośrednio w `translator.py` (`E-09`)[cite: 4, 5].
7. **[P3-2]** Ochrona terminów z sekcji `Zablokowana Terminologia` w `translator.py` po odebraniu wyniku z Fazy 2 (`E-11`)[cite: 4, 5].

---

## Sekcja 10 — Checklista odbioru `(a)`–`(m)` (§6)

- [x] **(a)** Potwierdzono obecność załączników `Z1` i `Z3` oraz przyjęto dyspozycję operatora o kontynuacji bez załącznika `Z2`[cite: 4, 5, 6].
- [x] **(b)** Wykonano Fazę 0 (§3.1) i udokumentowano inwentaryzację w Sekcji 1[cite: 4, 5, 6].
- [x] **(c)** Wykonano Fazę 1 (§3.2) i udokumentowano klasyfikację 11 zdarzeń operacyjnych w Sekcji 3[cite: 4, 5].
- [x] **(d)** Wykonano Fazę 2 (§3.3) dla wszystkich wykrytych anomalii i ostrzeżeń operacyjnych z pełnym śladem danych i modułów w Sekcji 4[cite: 4, 5, 6].
- [x] **(e)** Wykonano Fazę 3 (§3.4) i udokumentowano zgodność z zasadami Z1–Z4, Z16, CORNERSTONE, AGENTS.md §2 w Sekcji 5[cite: 4, 5, 6].
- [x] **(f)** Wykonano Fazę 4 (§3.5) i udokumentowano integralność stanu w Sekcji 6[cite: 4, 5].
- [x] **(g)** Wykonano Fazę 5 (§3.6) i udokumentowano konfrontację z rejestrem w Sekcji 7[cite: 4, 5].
- [x] **(h)** Zidentyfikowano i opisano nowe incydenty (`INC-AVT-026`, `INC-AVT-027`) w Sekcji 8[cite: 4, 5].
- [x] **(i)** Dla każdego błędu rozróżniono status `WYELIMINOWANY U ŹRÓDŁA` od `ZAMASKOWANY` / `PRZENIESIONY` / `NIEROZWIĄZANY` / `NIEAKTUALNY`[cite: 4, 5].
- [x] **(j)** Wystawiono werdykt Tora A (`CZĘŚCIOWO WYELIMINOWANE`), Tora B (`ZGODNY Z ZASTRZEŻENIAMI`) i werdykt łączony (`ZGODNY Z ZASTRZEŻENIAMI`) w Sekcji 2 i Sekcji 9[cite: 4, 5].
- [x] **(k)** Sformułowano priorytetyzowane rekomendacje `P1`/`P2`/`P3` (bez wdrażania) w Sekcji 9[cite: 4, 5].
- [x] **(l)** Raport wygenerowany w strukturze `Artefakty/Raport_audytu_operacyjnego_2026-11-11.md`, UTF-8 bez BOM, 0 placeholderów `<DO_WYPEŁNIENIA>`, z pełnym maskowaniem nazw własnych zgodnie z Z1[cite: 4, 5, 6].
- [x] **(m)** Każde twierdzenie poparte cytatem z logu (`Z1`/`Z3`), odniesieniem do modułu i hashem HEAD `dd950ba13e10e77d9888b30e8795922ef5299347`[cite: 4, 5, 6].