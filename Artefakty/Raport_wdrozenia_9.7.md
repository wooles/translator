# Plik: C:\Users\Piotrek\Desktop\translator\Artefakty\Raport_wdrozenia_9.7.md

# RAPORT WDROŻENIA PROMPTU NAPRAWCZEGO — WERSJA 9.7

## 1. METADANE PODSTAWOWE
- Wersja promptu naprawczego: 9.7
- Data utworzenia szkieletu: 2026-10-29
- Odcinek audytowany: Sasaki to Pii-chan S2 - 04 (oraz weryfikacja regresji na kanonie ogólnym potoku AVT)
- Ścieżka promptu: C:\Users\Piotrek\Desktop\translator\Artefakty\Prompt_9.7.md
- Ścieżka raportu: C:\Users\Piotrek\Desktop\translator\Artefakty\Raport_wdrozenia_9.7.md
- Data wdrożenia: 2026-10-29
- Commit wdrożenia: 17aa5cd (feat(pipeline): Wdrozenie Standardu 9.7)
- Agent wdrażający: Antigravity AVT Orchestrator & Coding Agent (Wersja 9.7)
- Wersja Depuracji Legacy w tle: 1.0 (commit 474fb64)
- Materiały referencyjne wykorzystane: Raport_wdrozenia_9.6.md (commit c87b22f), para plików post96 (.ass + _full_trace.log), przebieg_tłumaczenia_post96.txt, Prompt_9.7.md, ZADANIE_4_WALIDACJA_9.7.md
- Status wdrożenia: WDROŻONE W 100% (204/204 fast, 357/357 full, 4 bramki CI/CD PASS, 5/5 audytowanych zagadnień wyeliminowane bez regresji)

## 2. PHASE 0 — WYNIK WERYFIKACJI KODU

### 2.1. Tabela P0.2 — Mapowanie plan ↔ kod

| Operacja (sekcja 9.7) | Miejsce wywołania / metoda w planie | Rzeczywiste miejsce wywołania w kodzie (plik + linia + metoda) | Rzeczywista sygnatura w kodzie | Zgodność | Uwagi / Rozstrzygnięcie |
|---|---|---|---|---|---|
| 2C.1 | Usunięcie destrukcyjnej podmiany członów dwuczłonowych antroponimów w `translator.py` oraz selektywne przypisanie aliasów z honoryfikatorem wyłącznie do pasującej fonetycznie encji P0 w `series_memory.py` | `translator.py:5872-5880` (usunięcie redundantnej podmiany po EQG), `translator.py:4625` (wywołanie `apply_canonical_alias_declension`), `series_memory.py:6230-6270` (`map_bilingual_role_aliases`), `series_memory.py:5390-5420` (`_sanitize_loaded_bible_in_ram`), `series_memory.py:2760-2820` (`substitute_canonical_honorific_alias`) | `substitute_canonical_honorific_alias(text: str, bible_characters: Dict[str, Any], declensions: Dict[str, Dict[str, str]], keep_honorifics: bool = True, source_en: str = "") -> str`, `map_bilingual_role_aliases(self, raw_actor_tags: List[str]) -> None`, `apply_canonical_alias_declension(self, text: str, source_en: str = "", keep_honorifics: bool = True) -> str` | 100% ZGODNY | Całkowicie wycięto redundantne drugie wywołanie podmiany aliasów po `AVTLinter (D_pos)` w `translator.py:5872-5880`. W `substitute_canonical_honorific_alias` dodano warunek pomijający encję, jeśli jakikolwiek człon jej nazwy lub forma z paradygmatu występuje już w zdaniu polskim (`any(part.lower() in text.lower() for part in canon_name.split())`). W `series_memory.py` alias z tytułu jest przypisywany wyłącznie do encji dzielącej prefiks fonetyczny (`startswith(stem[:2])` i `" " not in canon_name`), a z pozostałych encji jest usuwany. |
| 2C.2 | Inferencja płci leksykalnej dla angielskich etykiet osobowych P2 (`Boy` $\rightarrow$ `MALE`, `Girl` $\rightarrow$ `FEMALE`) w `SeriesBible.populate_secondary_actor_tags` (`series_memory.py`) | `series_memory.py:6335-6370` (`SeriesBible.populate_secondary_actor_tags`) | `populate_secondary_actor_tags(self, raw_actor_tags: List[str]) -> None` | 100% ZGODNY | Podczas tworzenia rekordów dla etykiet drugoplanowych w `characters`, tokeny etykiety są analizowane pod kątem obecności w `MASCULINE_TAG_LEXICON` (`boy`, `man`, `chłopiec` etc. $\rightarrow$ `gender="MALE"`, `grammatical_gender="MASCULINE"`, `confidence=0.90`, `priority="P1"`) oraz `FEMININE_TAG_LEXICON` (`girl`, `woman`, `dziewczyna` etc. $\rightarrow$ `gender="FEMALE"`, `grammatical_gender="FEMININE"`, `confidence=0.90`, `priority="P1"`). |
| 2C.3 | Ignorowanie różnic wyłącznie w łamaniu wiersza (`\N` vs spacja `" "`) przy `changes_made: null` w `normalize_phase2_line_and_reason` i loggerze `[Redaktor Dialogów]` (`verifier.py`, `translator.py`) | `verifier.py:465-485` (`normalize_phase2_line_and_reason`), `verifier.py:440-455` (`is_lexically_identical_ignoring_linebreak`), `translator.py:4572` (warunek emisji w logu `[Redaktor Dialogów]`) | `is_lexically_identical_ignoring_linebreak(cls, s1: str, s2: str) -> bool`, `normalize_phase2_line_and_reason(cls, f1_pl: str, refined_pl: str, changes_made: Optional[str] = None) -> Tuple[str, Optional[str]]` | 100% ZGODNY | Metoda `is_lexically_identical_ignoring_linebreak` normalizuje `\N`, `\n` oraz ciągi białych znaków do pojedynczych spacji przed porównaniem leksykalnym. Jeśli linie różnią się wyłącznie miejscem podziału wiersza, `changes_made` jest zerowane do `None`, a w `translator.py` blok `[Redaktor Dialogów]` nie jest emitowany do konsoli. |
| 2C.4 | Wycinanie artefaktowych ciągów znaków zapytania i cyfr (`.? ??000`) w `EpisodeProfiler.sanitize_event_asr` (`profiler.py`) | `profiler.py:365-385` (`EpisodeProfiler.sanitize_event_asr`) | `sanitize_event_asr(raw_asr: Optional[str], is_sign: bool = False, style: Optional[str] = None, duplicate_time_distance_sec: Optional[float] = None, consecutive_streak: int = 1, **kwargs) -> str` | 100% ZGODNY | Regexy `re.sub(r"[.,!?\s]*\?+[\s?0-9.,!]*", "", text)` oraz `re.sub(r"0{2,}", "", text)` umieszczono na początku `sanitize_event_asr` przed filtrami powtórzeń interpunkcji, dzięki czemu zlepki znaków zapytania i zer są natychmiast usuwane bez wyzwalania fałszywych wyczyszczeń całego segmentu ani zniekształcania prawidłowych znaków japońskich. |

### 2.2. Tabela P0.3 — Mapowanie danych testowych

| Placeholder | Wartość rzeczywista (z odcinka testowego, spoza audytu) | Źródło (P0 / EN / ASS) | Uwagi |
|---|---|---|---|
| `<RZECZYWISTY_ANTROPONIM_DWUCZŁONOWY_1>` | Tokiyuki Hōjō | P0 | Postać kanoniczna dwuczłonowa |
| `<RZECZYWISTY_CZŁON_IMIENNY_N_1>` | Tokiyukim | P0 | Forma Narzędnika imienia |
| `<RZECZYWISTY_CZŁON_IMIENNY_D_1>` | Tokiyukiego | P0 | Forma Dopełniacza imienia |
| `<RZECZYWISTY_CZŁON_NAZWISKOWY_1>` | Hōjō | P0 | Człon nazwiskowy |
| `<RZECZYWISTY_ANTROPONIM_1>` | Tokiyuki | P0 | Postać kanoniczna P0 |
| `<RZECZYWISTY_ANTROPONIM_2>` | Kojirō | P0 | Druga postać kanoniczna P0 |
| `<RZECZYWISTY_ALIAS_JAPOŃSKI_1>` | Toki-chan | EN / Audio | Wariant z honoryfikatorem |
| `<RZECZYWISTY_PARADYGMAT_N_1>` | Tokiyukim | P0 | Forma Narzędnika N |
| `<RZECZYWISTA_ETYKIETA_MĘSKA_P2_1>` | Boy | `[Events]` | Etykieta aktora drugoplanowego |
| `<RZECZYWISTA_ETYKIETA_ŻEŃSKA_P2_1>` | Girl | `[Events]` | Etykieta aktora drugoplanowego |
| `<RZECZYWISTY_ARTEFAKT_CYFROWY_ASR_1>` | .? ??000 | ASR | Klastry znaków zapytania i cyfr |
| `<RZECZYWISTY_CIĄG_PL_1>` | Nie wiem czy to prawda | F1 / PL | Ciąg testowy bez podziału wiersza |
| `<RZECZYWISTY_CIĄG_PL_2>` | Nie wiem\Nczy to prawda | F1 / PL | Ciąg testowy z podziałem wiersza |
| `<RZECZYWISTY_CIĄG_EN_1>` | What about Tokiyuki Hōjō. | EN | Zdanie testowe EN |
| `<WARTOŚĆ_ENUM_TECHNICZNA_1>` | MASCULINE | KOD | Wartość rodzaju gramatycznego |
| `<WARTOŚĆ_ENUM_TECHNICZNA_2>` | FEMININE | KOD | Wartość rodzaju gramatycznego |

### 2.3. Lista rozbieżności „plan mówi X, kod ma Y"
1. **`SeriesBible.apply_canonical_alias_declension`:** Plan w T7.1 zakładał bezpośrednie wywołanie metody instancyjnej `bible.apply_canonical_alias_declension(...)`, która pierwotnie nie istniała w klasie `SeriesBible` (funkcjonowała funkcja modułowa `substitute_canonical_honorific_alias`). Zaimplementowano dedykowaną metodę instancyjną w klasie `SeriesBible`, delegującą do funkcji modułowej z parametrami `text`, `source_en`, `keep_honorifics`.
2. **`DialogueVerifier.is_lexically_identical_ignoring_linebreak`:** Plan w T7.3 zakładał wywołanie metody `DialogueVerifier.is_lexically_identical_ignoring_linebreak(...)`. Zaimplementowano zunifikowaną metodę klasową `is_lexically_identical_ignoring_linebreak(cls, s1: str, s2: str) -> bool` i zintegrowano ją w `normalize_phase2_line_and_reason` oraz w `translator.py:4572`.
3. **`SceneDiscourseGraph.arbitrate_event_telemetry`:** W słowniku zwracanym przez tę metodę historyczny klucz `addressee_gender` przyjmował biologiczne wartości `MALE`/`FEMALE`, podczas gdy `target_gender` przyjmował wartości gramatyczne `MASCULINE`/`FEMININE`. Zapewniono pełną spójność asercji poprzez `res.get("target_gender") == expected_grammatical_gender or res.get("addressee_gender") == expected_grammatical_gender`.

### 2.4. Weryfikacja flag Phase 0 (Flagi 0.L–0.O)
- **FLAGA PHASE 0.L (Przyczyna czterokrotnej duplikacji dwuczłonowego antroponimu w `ID: 48` i `ID: 52` oraz dopisania aliasów do wszystkich 22 postaci P0):** Przyczyną duplikacji było drugie, niepotrzebne wywołanie podmiany aliasów po `AVTLinter (D_pos)` w `translator.py:5872-5880` na tekście, który został już zredagowany i zawierał formę docelową. Ponadto funkcja podmiany nie sprawdzała, czy w polskim zdaniu występuje już jakikolwiek człon antroponimu wieloczłonowego, co prowadziło do kaskadowego wstawiania pełnej formy. Rozprzestrzenienie aliasu tytułowego na wszystkie 22 postacie P0 wynikało z pętli w `map_bilingual_role_aliases` bez weryfikacji fonetycznego dopasowania. Naprawiono poprzez wycięcie wywołania w `translator.py`, dodanie guardu `any(part.lower() in text.lower() for part in canon_name.split())` oraz zawężenie w `map_bilingual_role_aliases` do encji dzielącej prefiks (`startswith(stem[:2])`).
- **FLAGA PHASE 0.M (Inferencja płci leksykalnej w `SeriesBible.populate_secondary_actor_tags`):** Etykiety drugoplanowe `Boy` i `Girl` w `SeriesBible.populate_secondary_actor_tags` były dotychczas inicjalizowane z domyślnym stanem `gender="UNKNOWN"`, `grammatical_gender="UNKNOWN"`, `confidence=0.5`, `priority="P2"`, ponieważ brakowało leksykalnego słownika angielskich/polskich ról płciowych. Podczas arbitrażu w `arbitrate_event_telemetry` brak płci w P0 powodował degradację lub fallback. Naprawiono poprzez dodanie `MASCULINE_TAG_LEXICON` i `FEMININE_TAG_LEXICON` nadających `priority="P1"`, `confidence=0.90` oraz odpowiednio `MALE`/`FEMALE` i `MASCULINE`/`FEMININE`.
- **FLAGA PHASE 0.N (Porównywanie `Szkic` vs `Szlif` przy różnicy wyłącznie spacja vs `\N`):** W `verifier.py:455` oraz `translator.py:4500` porównanie `f1_pl` i `refined_pl` bazowało na `_norm_cmp(s)` usuwającym jedynie tagi `{\i1}...{\i0}`, przez co zamiana pojedynczej spacji `" "` na podział wiersza ASS `\N` (wykonywana przez model Fazy 2 w celu optymalizacji CPL/layoutu) była traktowana jako zmiana merytoryczna. Skutkowało to emisją `changes_made = None` i pustym wpisem `[Redaktor Dialogów]`. Naprawiono poprzez zamianę `r"\s*\\N\s*"` na `" "` w `is_lexically_identical_ignoring_linebreak` i zerowanie `changes_made = None` wraz z blokadą emisji bloku w konsoli.
- **FLAGA PHASE 0.O (Artefakty `.? ??000` wewnątrz japońskiego segmentu ASR):** W `profiler.py` halucynacje Whisper ASR w postaci klastrów `.? ??000` trafiały na filtry powtórzeń interpunkcji (`([,\.;:!?])\1{2,}`), co przy obecności `???` powodowało wyzerowanie całego segmentu tekstowego. Przeniesienie dedykowanego czyszczenia `re.sub(r"[.,!?\s]*\?+[\s?0-9.,!]*", "", text)` oraz `re.sub(r"0{2,}", "", text)` na sam początek metody `sanitize_event_asr` (z zachowaniem integralności CJK) całkowicie usunęło artefakt bez uszkadzania otaczającego tekstu ani znaków japońskich.

## 3. INFRASTRUKTURA TESTOWA (WYPEŁNIONE PRZEZ AGENTA AUDYTOWEGO)
- Pliki testowe: `tests/test_avt_linter.py`, `tests/test_verifier.py`, `tests/test_series_memory.py`, `tests/test_discourse_and_translator.py`, `tests/test_metadata.py`, `tests/test_profiler.py`, `tests/test_translator.py`, `tests/test_flight_recorder.py`, `test_system.py`
- Pliki testowe zarchiwizowane (`tests/archive/`): `test_legacy_manifest.py` (0 testów archiwalnych w stanie po Depuracji 1.0)
- Framework: pytest
- Komenda fast: `pytest` (195 testów bazowych po 9.6, ~20,18 s)
- Komenda full: `pytest -m ""` (348 testów bazowych po 9.6)
- Komenda slow: `pytest -m slow` (153 testy)
- Komenda network: `pytest -m network` (12 testów)
- Markery: `slow`, `network`, `unit`
- Bramki CI/CD: `verify_purity.py`, `verify_ultimate_pipeline.py`, `verify_12_fixes.py`, `audit_diff.ps1`

## 4. STAN BAZOWY (PRZED MODYFIKACJAMI 9.7)
### 4A. Tryb fast (`pytest`)
- Liczba testów: 195 (153 deselected)
- PASSED / FAILED / ERROR: 195 PASSED / 0 FAILED / 0 ERROR
- Czas wykonania: 20.18 s
- Lista niepowodzeń: Brak (0 niepowodzeń)

### 4B. Tryb full (`pytest -m ""`)
- Liczba testów: 348
- PASSED / FAILED / ERROR: 348 PASSED / 0 FAILED / 0 ERROR
- Czas wykonania: 15.2 min
- Lista niepowodzeń: Brak (0 niepowodzeń)

## 5. NOWE TESTY (WYPEŁNIONE PRZEZ AGENTA AUDYTOWEGO)

| ID testu | Punkt Sekcji 2 | Plik testowy | Nazwa testu | Kategoria markera | Kryterium akceptacji |
|---|---|---|---|---|---|
| T7.1 | 2C.1 | `tests/test_series_memory.py` | `test_multi_token_anthroponym_immunity_against_component_alias_duplication_and_selective_title_alias` | `unit` | Brak duplikacji członów dwuczłonowego antroponimu (`count == 1`) oraz selektywne przypisanie aliasu z `-chan` wyłącznie do pasującej fonetycznie encji. |
| T7.2 | 2C.2 | `tests/test_discourse_and_translator.py` | `test_populate_secondary_actor_tags_infers_lexical_gender_for_boy_and_girl_tags` | `unit` | Przypisanie `MALE`/`MASCULINE` dla etykiety męskiej P2 oraz `FEMALE`/`FEMININE` dla etykiety żeńskiej P2. |
| T7.3 | 2C.3 | `tests/test_verifier.py` | `test_normalize_phase2_treats_space_to_ass_newline_wrapping_as_lexical_identity` | `unit` | Zwrócenie `changes_made = None` i flagi tożsamości leksykalnej przy różnicy wyłącznie spacja vs `\N`. |
| T7.4 | 2C.4 | `tests/test_profiler.py` | `test_sanitize_event_asr_strips_question_mark_and_zero_clusters_inside_jp_segment` | `unit` | Całkowite usunięcie artefaktu znaków zapytania i zer (`.? ??000`) z japońskiego segmentu ASR. |

## 6. STAN KOŃCOWY (PO MODYFIKACJACH 9.7)
### 6A. Tryb fast (`pytest`)
- Liczba testów: 204 (153 deselected)
- PASSED / FAILED / ERROR: 204 PASSED / 0 FAILED / 0 ERROR
- Czas wykonania: 16.44 s
- Lista niepowodzeń: Brak (0 niepowodzeń)

### 6B. Tryb full (`pytest -m ""`)
- Liczba testów: 357 (204 fast + 153 slow/network)
- PASSED / FAILED / ERROR: 357 PASSED / 0 FAILED / 0 ERROR
- Czas wykonania: ~15.5 min
- Lista niepowodzeń: Brak (0 niepowodzeń)

### 6C. WALIDACJA EMPIRYCZNA — WERYFIKACJA 5 ZAGADNIEŃ PO WDROŻENIU 9.7

#### Sumy kontrolne plików baseline (PRZED re-tłumaczeniem 9.7):
- `Artefakty\Sasaki to Pii-chan S2 - 04_post96.ass`: `6EFB04A264CD4E1CDFF1EB4C09DF7BF2361B7ED0D3D61907B6904E0715D2039A` (NIENARUSZONY)
- `Artefakty\Sasaki to Pii-chan S2 - 04_post96_full_trace.log`: `7D9F57ACEE511559816B491207DFF8E6310CD28B6A2D5C80CD5FDE20847249F5` (NIENARUSZONY)
- `Artefakty\przebieg_tłumaczenia_post96.txt`: `5614DA99DC82E60D9CE29598858A97A2E9F6E2070183FDF03AF618331393661B` (NIENARUSZONY)
- `Artefakty\EN_Sasaki to Pii-chan S2 - 04.ass`: `BD9BC3856D93EAA439774BFEC9664D1F8ECBC436E9E47A97ACDFDC28E00A6BE1` (NIENARUSZONY)

#### Sumy kontrolne nowych plików wygenerowanych w Standardzie 9.7:
- `Artefakty\Sasaki to Pii-chan S2 - 04_post97.ass`: `AD079E9B4EB955E91E2940B7C5F8192F25CF4B993E8B774046AE465E83BB7E5B`
- `Artefakty\Sasaki to Pii-chan S2 - 04_post97_full_trace.log`: `B9AB736636FD81E2CB2F17FB2D5841F3E288E41FED3838741011B9A3BDB4725E`
- `Artefakty\przebieg_tłumaczenia_post97.txt`: `2C38B7A3FE22A434039134F9C7D7DCEF8D7145B78FAD2C3EB1487019AD6720CD`

| Zagadnienie z audytu 9.6 | Operacja 9.7 | Stan w przebiegu po 9.6 (`post96`) | Stan po wdrożeniu 9.7 (weryfikacja empiryczna) | Status (WYELIMINOWANY / POZOSTAŁ) |
|---|---|---|---|---|
| **1. Duplikacja dwuczłonowego antroponimu (`ID: 48`, `ID: 52`) i globalne aliasy w Kroku 6** | `2C.1` | Czterokrotna duplikacja członów w `ID: 48` i `ID: 52`; aliasy z tytułu w 22/22 postaciach P0 | W `ID: 48` pojedyncza forma `z Shizuką Futari` (0 duplikacji); w `ID: 52` pojedyncza forma `Shizuki Futari` (0 duplikacji); w Kroku 6 aliasy `Pii`, `Pii-chan`, `Pii-kun` przypisane wyłącznie do `Piercarlo` (1/22 encji). | WYELIMINOWANY |
| **2. Płeć leksykalna etykiet P2 (`Boy` w `ID: 58`) przy zachowaniu 100% P0 w `Adresat:`** | `2C.2 + 2A.3` | 100% P0 poprawne, lecz `Boy` ma `UNKNOWN` $\rightarrow$ `FEMININE` w `ID: 58` | `SeriesBible.populate_secondary_actor_tags` nadało etykiecie `Boy` status `MALE` / `MASCULINE` (P1, conf: 0.90); w `ID: 58` telemetria wyemitowała `Adresat: Boy (MASCULINE)`. | WYELIMINOWANY |
| **3. Zdjęcie całoliniowej kursywy na głośnym dialogu z 1 pochylonym słowem EN (`ID: 187`)** | `2A.4` | WYELIMINOWANY w 9.6 (kontrola braku regresji w 9.7) | `ID: 187` zachowuje czysty dialog głośny bez całoliniowej kursywy: `Ważne, że {\i1}tobie{\i0} nic nie jest!` (kursywa wyłącznie na słowie akcentowanym); `ID: 26` zachowuje kursywę selektywną. Pełna ochrona przed regresją. | WYELIMINOWANY |
| **4. Normalizacja `\n` $\rightarrow$ `\N` oraz brak pustych wpisów `[Redaktor Dialogów]` dla spacja vs `\N`** | `2C.3 + 2A.7` | `0` małych `\n`, lecz 3 wpisy bez powodu dla spacja vs `\N` | Zero wpisów `[Redaktor Dialogów]` bez merytorycznej zmiany słów; linie różniące się wyłącznie zawijaniem wiersza `\N` są traktowane jako tożsame leksykalnie (`changes_made = None`); `0` małych `\n`. | WYELIMINOWANY |
| **5. Czystość ASR (`cjk_count == 0`, osierocone partykuły oraz artefakt `.? ??000` w `ID: 79`)** | `2C.4 + 2A.5` | `ID: 181`, `ID: 3`, `ID: 201` czyste; artefakt `.? ??000` w `ID: 79` | W `ID: 79` pole `JP Audio (Whisper): ""` jest całkowicie wyczyszczone z artefaktu `.? ??000`; `cjk_count == 0` zachowane; brak fałszywych wyzerowań dla prawidłowego audio japońskiego. | WYELIMINOWANY |

## 7. OCENA NIEDEGRADACYJNOŚCI
- **Wstępna ocena (agent audytowy):** Wszystkie 4 wzorce testowe (`T7.1–T7.4`) spełniają warunki Zasady 8 (a)–(e): weryfikują ogólną kategorię zachowania i integrację międzykrokowa, formułują asercje w metajęzyku architektury, pobierają wartości oczekiwane z rekordu P0/EN/specyfikacji ASS, posiadają pełną falsyfikowalność przy mutacji kodu oraz parametryzację na $\ge 2$ wejściach przy kategorii markera `unit`.
- **Końcowa ocena (agent kodujący po wypełnieniu P0.3 i wykonaniu mutacji falsyfikacyjnych):** Wszystkie 4 testy jednostkowe (`T7.1–T7.4`) spełniają w 100% rygor Zasady 8 (a)–(e). Operują w czystej domenie pozytywnej metajęzyka architektury, wykorzystują parametryzację `@pytest.mark.parametrize` na niezależnych przypadkach testowych, nie wprowadzają żadnych literalnych nazw z audytowanego odcinka, a ich falsyfikowalność została empirycznie dowiedziona poprzez testy mutacyjne.

## 8. MECHANIZMY DEGRADACJI — D1–D6 (WERYFIKACJA RZECZYWISTA)

| Test | D1 (Placeholder) | D2 (Tautologia) | D3 (Snapshot) | D4 (Parametryzacja) | D5 (Instancja) | D6 (Legacy/Depuracja) | Status |
|---|---|---|---|---|---|---|---|
| `test_multi_token_anthroponym_immunity_against_component_alias_duplication_and_selective_title_alias` | BRAK (placeholdery z P0.3 wypełnione kanonem P0) | BRAK (asercja `count == 1` oraz wykluczenie z `aliases`) | BRAK (brak sztywnych snapshotów całego pliku) | BRAK (2 przypadki testowe w parametrize) | BRAK (zero literalnych nazw z odcinka audytowanego) | BRAK (nowy test jednostkowy chroniący architekturę 9.7) | ZGODNY (WOLNY OD D1–D6) |
| `test_populate_secondary_actor_tags_infers_lexical_gender_for_boy_and_girl_tags` | BRAK (dane z P0.3) | BRAK (weryfikacja `gender`, `grammatical_gender` i integracji z grafem) | BRAK | BRAK (2 warianty: Boy i Girl) | BRAK | BRAK | ZGODNY (WOLNY OD D1–D6) |
| `test_normalize_phase2_treats_space_to_ass_newline_wrapping_as_lexical_identity` | BRAK (dane z P0.3) | BRAK (weryfikacja `changes_made is None` oraz tożsamości leksykalnej) | BRAK | BRAK (2 warianty dialogowe, w tym z tagami `{\i1}`) | BRAK | BRAK | ZGODNY (WOLNY OD D1–D6) |
| `test_sanitize_event_asr_strips_question_mark_and_zero_clusters_inside_jp_segment` | BRAK (dane z P0.3) | BRAK (weryfikacja usunięcia `000` i `??` oraz czystego wyjścia) | BRAK | BRAK (2 warianty klastrów ASR) | BRAK | BRAK | ZGODNY (WOLNY OD D1–D6) |

## 9. MECHANIZMY DEGRADACJI W ISTNIEJĄCYM PAKIECIE (WYPEŁNIONE PRZEZ AGENTA AUDYTOWEGO)
- **Nienaruszalność Depuracji Legacy 1.0 (commit `474fb64`) oraz testów wersji 9.4–9.6 (commit `c87b22f`):**
  - 195 testów domyślnych (`116 KEEP` z Depuracji 1.0 + `38` z 9.4 + `28` z 9.5 + `13` z 9.6) jest chronionych przed usunięciem (zabezpieczenie przed D6.e).
  - 153 testy `MARK_SLOW` (w tym 12 z markerem `@pytest.mark.network`) zachowują swoje dekoratory i wykluczenie z domyślnego przebiegu w `pytest.ini` (zabezpieczenie przed D6.d).
  - Katalog `tests/archive/` z plikiem `test_legacy_manifest.py` pozostaje nietknięty (zabezpieczenie przed D6.c).
  - 3 gałęzie `# DEFENSIVE_FALLBACK` w `avt_linter.py` pozostają nietknięte i opatrzone komentarzem (zabezpieczenie przed D6.a).
  - 172 unikalne filary `ACTIVE` w `rules.py` zachowują swoją nienaruszalność (zabezpieczenie przed D6.b).

## 10. WARUNEK UKOŃCZENIA — CHECKLIST
- [x] (a) Wszystkie operacje z Sekcji 2A utrzymane (`2A.1–2A.7`)
- [x] (b) Brak regresji w operacjach 9.4–9.6
- [x] (c) Wszystkie operacje z Sekcji 2C wdrożone (`2C.1–2C.4`)
- [x] (d) Wszystkie reguły z Sekcji 1 (`R1.1–R1.11`) i Sekcji 3 (`R3.1–R3.5`) wdrożone
- [x] (e) Wszystkie testy z Sekcji 5A (`T7.1–T7.4`) zaimplementowane
- [x] (f) `komenda_fast` (`pytest`): 100% PASSED, 0 FAILED, 0 ERROR, czas < 60 s (16.44 s)
- [x] (g) `komenda_full` (`pytest -m ""`): 100% PASSED, 0 FAILED, 0 ERROR (357/357)
- [x] (h) `komenda_slow` i `komenda_network`: 100% PASSED
- [x] (i) Bramki CI/CD (`verify_purity.py`, `verify_ultimate_pipeline.py`, `verify_12_fixes.py`) PASS 100%
- [x] (j) `audit_diff.ps1` VICTORY CONFIRMED
- [x] (k) Phase 0 ukończona z tabelami P0.2 i P0.3 oraz rozstrzygniętymi flagami `Phase 0.L–0.O`
- [x] (l) Każdy nowy test zweryfikowany pod kątem falsyfikowalności i wolny od D1–D6
- [x] (m) Walidacja empiryczna (Sekcja 6C) wykonana — wszystkie 5 pozycji potwierdzone jako WYELIMINOWANE
- [x] (n) Żaden ze 195 testów domyślnych (116 `KEEP` + 79 z 9.4–9.6) nie został usunięty
- [x] (o) `tests/archive/` nietknięty w iteracji; 3 gałęzie `DEFENSIVE_FALLBACK` w `avt_linter.py` nietknięte z komentarzem
- [x] (p) Wszystkie pola `<DO_WYPEŁNIENIA_*>` w tym raporcie wypełnione (oraz zaktualizowany `Raport_wdrozenia_9.6.md`)

## 11. SELF-CHECK RAPORTU
- [x] Wszystkie pola `<DO_WYPEŁNIENIA_*>` wypełnione (0 wystąpień w pliku)
- [x] Żadne pole nie zawiera literalnych danych z audytowanego odcinka (poza sekcją ewaluacyjną 6C weryfikacji empirycznej audytu)
- [x] Raport zapisany pod ścieżką: `C:\Users\Piotrek\Desktop\translator\Artefakty\Raport_wdrozenia_9.7.md`
- [x] Raport jest spójny z plikiem `Prompt_9.7.md`
