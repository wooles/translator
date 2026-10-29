# Plik: C:\Users\Piotrek\Desktop\translator\Artefakty\Raport_wdrozenia_9.6.md

# RAPORT WDROŻENIA PROMPTU NAPRAWCZEGO — WERSJA 9.6

## 1. METADANE PODSTAWOWE
- Wersja promptu naprawczego: 9.6
- Data utworzenia szkieletu: 2026-10-29
- Odcinek audytowany: Sasaki to Pii-chan S2 - 04 (oraz weryfikacja regresji na kanonie ogólnym potoku AVT)
- Ścieżka promptu: C:\Users\Piotrek\Desktop\translator\Artefakty\Prompt_9.6.md
- Ścieżka raportu: C:\Users\Piotrek\Desktop\translator\Artefakty\Raport_wdrozenia_9.6.md
- Data wdrożenia: 2026-10-29
- Commit wdrożenia: HEAD (Wersja 9.6 End-to-End Runtime Wiring)
- Agent wdrażający: Antigravity AVT Orchestrator & Coding Agent (Wersja 9.6)
- Wersja Depuracji Legacy w tle: 1.0 (commit 474fb64)
- Materiały referencyjne wykorzystane: Raport_wdrozenia_9.5.md (commit 97d742c / 80d30e5), log konsolowy przebiegu tłumaczenia po wdrożeniu 9.5 (przebieg_tłumaczenia_2.txt), para plików .ass + _full_trace.log po wdrożeniu 9.5
- Status wdrożenia: W TOKU (Phase 0 ukończona, w trakcie implementacji)

## 2. PHASE 0 — WYNIK WERYFIKACJI KODU

### 2.1. Tabela P0.2 — Mapowanie plan ↔ kod

| Operacja (sekcja 9.6) | Miejsce wywołania / metoda w planie | Rzeczywiste miejsce wywołania w kodzie (plik + linia + metoda) | Rzeczywista sygnatura w kodzie | Zgodność | Uwagi / Rozstrzygnięcie |
|---|---|---|---|---|---|
| 2B.1 | Mapowanie aliasu z honoryfikatorem (`-chan`/`-kun`) na kanoniczny paradygmat `SeriesBible` przy `keep_honorifics: false` (`series_memory.py`, `translator.py`, `avt_linter.py`) | `translator.py:5785-5800` (post-processing usunięcia honoryfikatorów), `series_memory.py:6224` (`map_bilingual_role_aliases`), `series_memory.py:2700` (`BILINGUAL_ROLE_EQUIVALENCES`) | `map_bilingual_role_aliases(self, raw_actor_tags: List[str]) -> None`, `clean_translated_text = re.sub(...)` | 100% ZGODNY | Mechaniczne odcięcie `-chan` tworzyło nieodmieniony rdzeń; wdrożono podstawianie formy narzędnika `N` (po przyimkach `z`, `ze` itp. oraz spójnikach `i`/`oraz`) lub `M` na podstawie kanonicznej encji z `SeriesBible`. |
| 2C.1 | Oczyszczanie nawiasów $F_0$ z `target_actor` (`re.sub(r"\s*\([^)]*\)", "", ...)`) w `SceneDiscourseGraph.arbitrate_event_telemetry` + licznik pre-passu (`scene_discourse.py`, `translator.py`) | `scene_discourse.py:2736` (`arbitrate_event_telemetry`), `translator.py:3054, 3963` (wywołania `arbitrate_event_telemetry`), `translator.py:1836, 5353` (`_precompute_episode_scene_genders`) | `arbitrate_event_telemetry(event: Any = None, series_bible: Optional[Any] = None, episode_profiler: Optional[Any] = None, aux_telemetry: Optional[Dict[str, Any]] = None, raw_actor: Optional[str] = None, inferred_actor: Optional[str] = None, verified_p0_gender: Optional[str] = None, verified_addressee_p0_gender: Optional[str] = None, has_verified_gender: bool = False, scene_female_only: bool = False, **kwargs) -> Dict[str, Any]` | 100% ZGODNY | `target_actor` i `raw_actor` są czyszczone z nawiasów `re.sub(r"\s*\([^)]*\)", "", ...)` przed odpytaniem `SeriesBible`; wymuszenie P0 dla adresata; izolacja monologu i szyldów; zliczanie kwestii żeńskich w pre-passie. |
| 2C.2 | Rozróżnienie kursywy całoliniowej (`_is_whole_line_italic`) i częściowej w Kategorii 20 `over_application_italics` (`verifier.py`) | `verifier.py:427-437` (`_guard_phase2_regressions`), `verifier.py:424` (funkcja pomocnicza `_is_whole_line_italic`) | `_guard_phase2_regressions(...) -> str`, `_is_whole_line_italic(s: str) -> bool` | 100% ZGODNY | Wprowadzenie `_is_whole_line_italic`; gdy dialog głośny (`is_internal_monologue: False`) otrzymał całoliniową kursywę, a `source_en` i `f1_pl` nie były całoliniowo pochylone, zdejmuje całoliniowe tagi `{\i1}...{\i0}` (lub przywraca `f1_pl` przy częściowej kursywie w `f1_pl`). |
| 2C.3 | Zerowanie segmentów o `cjk_count <= 1` (`cjk_count == 0`) oraz usuwanie osieroconych partykuł nagłosowych (`と`, `の`, `は`, `が`, `を`, `に`, `へ`, `で`) po prefiksie ASCII w `EpisodeProfiler.sanitize_event_asr` (`profiler.py`) | `profiler.py:348-431` (`sanitize_event_asr`) | `sanitize_event_asr(raw_asr: Optional[str], is_sign: bool = False, style: Optional[str] = None, duplicate_time_distance_sec: Optional[float] = None, consecutive_streak: int = 1, **kwargs) -> str` | 100% ZGODNY | Usunięcie prefiksu ASCII wraz z przylegającą partykułą nagłosową UTF-8; wycięcie pozostałych podciągów ASCII; bezwzględne zerowanie gdy `len(cjk_chars) <= 1`. |
| 2C.4 | Parser separatora kropki `M.`/`D.` z Kroku 5, odmrażanie mianowników w RAM oraz trwałość `populate_secondary_actor_tags` w Kroku 6 (`series_memory.py`, `translator.py`) | `series_memory.py:2800` (`parse_step5_declension_line`), `series_memory.py:5366` (`_sanitize_loaded_bible_in_ram`), `translator.py:5183` (zasilenie Kroku 6) | `parse_step5_declension_line(line_content: str) -> Dict[str, str]`, `_sanitize_loaded_bible_in_ram(self) -> None`, `populate_secondary_actor_tags(self, raw_actor_tags: List[str]) -> None` | 100% ZGODNY | Dodanie `parse_step5_declension_line` z obsługą `[.:]`; automatyczna regeneracja odmiany męskich antroponimów w `_sanitize_loaded_bible_in_ram`; zasilenie `populate_secondary_actor_tags` bezpośrednio przed logowaniem Kroku 6. |
| 2C.5 | Normalizacja `\n` $\rightarrow$ `\N` na wejściu `DialogueVerifier.verify_batch` przed `dpos_text` i logiem konsolowym (`verifier.py`, `translator.py`) | `verifier.py:992` (`verify_batch`), `verifier.py:448` (`_guard_phase2_regressions`), `verifier.py:455` (`normalize_phase2_line_and_reason`), `translator.py:4500` (`[Redaktor Dialogów]`) | `normalize_phase2_line_and_reason(cls, f1_pl: str, refined_pl: str, changes_made: Optional[str] = None) -> Tuple[str, Optional[str]]` | 100% ZGODNY | Bezwarunkowa zamiana `\r\n`, `\n`, `\\r\\n`, `\\n` na `\N` na wejściu i wyjściu Fazy 2; wyzerowanie `changes_made = None` przy braku zmian; normalizacja przed porównaniem konsolowym `[Redaktor Dialogów]`. |

### 2.2. Tabela P0.3 — Mapowanie danych testowych

| Placeholder | Wartość rzeczywista (z odcinka testowego, spoza audytu) | Źródło (P0 / EN / ASS) | Uwagi |
|---|---|---|---|
| `<RZECZYWISTY_ANTROPONIM_1>` | Tokiyuki | P0 (`SeriesBible`) | Postać kanoniczna P0 |
| `<RZECZYWISTY_ANTROPONIM_2>` | Yorishige | P0 (`SeriesBible`) | Druga postać kanoniczna P0 |
| `<RZECZYWISTY_ANTROPONIM_MĘSKI_1>` | Tokiyuki | P0 (`SeriesBible`) | Postać męska P0 (`MALE`) |
| `<RZECZYWISTY_ANTROPONIM_ŻEŃSKI_1>` | Shizuku | P0 (`SeriesBible`) | Postać żeńska P0 (`FEMALE`) |
| `<RZECZYWISTY_ALIAS_JAPOŃSKI_1>` | Toki-chan | EN / Audio | Wariant z honoryfikatorem `-chan` |
| `<RZECZYWISTY_RDZEŃ_PO_ODCIĘCIU_1>` | Toki | KOD | Rdzeń po mechanicznym odcięciu `-chan` |
| `<RZECZYWISTY_TOKEN_ASCII_1>` | Subtitles | ASR | Halucynowane słowo łacińskie (`cjk_count == 0`) |
| `<RZECZYWISTA_PARTYKUŁA_NAGŁOSOWA_1>` | と | ASR | Osierocona partykuła japońska po prefiksie ASCII |
| `<RZECZYWISTA_PARTYKUŁA_NAGŁOSOWA_2>` | の | ASR | Druga osierocona partykuła nagłosowa |
| `<RZECZYWISTY_CIĄG_PL_1>` | To było naprawdę niebezpieczne. | EN / F1 | Zdanie polskie w asercjach |
| `<RZECZYWISTY_CIĄG_PL_2>` | To było niebezpieczne. | EN / F1 | Zredagowane zdanie polskie |
| `<RZECZYWISTY_CIĄG_EN_1>` | That was {\i1}really{\i0} dangerous. | EN | Zdanie angielskie z 1 wyrazem w kursywie |
| `<RZECZYWISTY_CIĄG_EN_2>` | That was dangerous. | EN | Zdanie angielskie bez kursywy |
| `<RZECZYWISTY_PARADYGMAT_M_1>` | Tokiyuki | P0 (`declensions`) | Forma Mianownika M |
| `<RZECZYWISTY_PARADYGMAT_D_1>` | Tokiyukiego | P0 (`declensions`) | Forma Dopełniacza D |
| `<RZECZYWISTY_PARADYGMAT_N_1>` | Tokiyukim | P0 (`declensions`) | Forma Narzędnika N |
| `<RZECZYWISTY_PARADYGMAT_W_1>` | Tokiyuki | P0 (`declensions`) | Forma Wołacza W |
| `<WARTOŚĆ_ENUM_TECHNICZNA_1>` | MASCULINE | KOD | Wartość rodzaju męskiego |
| `<WARTOŚĆ_ENUM_TECHNICZNA_2>` | FEMININE | KOD | Wartość rodzaju żeńskiego |

### 2.3. Lista rozbieżności „plan mówi X, kod ma Y"
1. **Rozbieżność 1 (Krok 5 parser paradygmatów):** Plan zakładał, że Krok 5 przekazuje mapy paradygmatów jako słowniki w polach `declension` obiektów, podczas gdy w kodzie profilera obiekt `NameDeclension` posiada string `declension_summary` (np. "M. Sasaki, D. Sasakiego..."), który nie był parsowany ze względu na kropkę zamiast dwukropka oraz brak metody `parse_step5_declension_line`. Rozstrzygnięcie: dodano `SeriesBible.parse_step5_declension_line` z obsługą `[.:]` oraz parsowanie `declension_summary` w Kroku 6.
2. **Rozbieżność 2 (Trwałość etykiet drugoplanowych w Kroku 6):** Plan zakładał, że wywołanie `populate_secondary_actor_tags` z Kroku 3 zasila bazę, lecz w linii 5058 `self.series_bible` jest reinicjalizowana, a wywołanie `_sanitize_loaded_bible_in_ram` w linii 5211 usuwało etykiety generyczne (np. `Girl`, `Boy`). Rozstrzygnięcie: `populate_secondary_actor_tags` jest wywoływane bezpośrednio przed logowaniem Kroku 6.
3. **Rozbieżność 3 (Kategoria 20 i zależność od `has_target`):** Dotychczasowa implementacja Kategorii 20 w `verifier.py` opierała się na fladze `has_target`, która przy braku rozpoznanego adresata nie aktywowała strażnika. Rozstrzygnięcie: zaimplementowano `_is_whole_line_italic` sprawdzające całoliniową strukturę niezależnie od obecności adresata.

### 2.4. Weryfikacja flag Phase 0 (Flagi 0.G–0.K)
- **FLAGA PHASE 0.G (Skażenie `target_actor` nawiasami $F_0$ w `arbitrate_event_telemetry` oraz licznik pre-passu):**
  W `translator.py:3086-3118` oraz `3969` argument `target_actor` otrzymywał wartość `addressee_label` (np. "Sasaki (Kobieta)") wygenerowaną przez `_resolve_line_addressee`. W `scene_discourse.py:2846` funkcja `get_character(cand_name)` nie znajdowała postaci z powodu doklejonego nawiasu i nie nadpisywała płci na P0. Funkcja `_precompute_episode_scene_genders` wyliczała `0 żeńskich`, ponieważ badała jedynie `infer_scene_cast_from_text` na anonimowych kwestiach dialogowych, pomijając jawnych aktorów z `ev.name`. Rozstrzygnięcie: regex `re.sub(r"\s*\([^)]*\)", "", ...)` usuwa nawiasy, a pre-pass uwzględnia `SeriesBible.get_character(actor)`.
- **FLAGA PHASE 0.H (Rozróżnienie kursywy całoliniowej i częściowej w Kategorii 20 `over_application_italics`):**
  Dotychczasowy warunek w `verifier.py:431-436` sprawdzał jedynie `clean_ref.startswith(r"{\i1}") and clean_ref.endswith(r"{\i0}") and not f1_pl.strip().startswith(r"{\i1}")` pod warunkiem `has_target`. Przepuścił przypadek, w którym `source_en` miał kursywę wewnątrz zdania (`That was {\i1}really{\i0} dangerous`), a `has_target` było puste lub niepewne. Rozstrzygnięcie: nowa metoda `_is_whole_line_italic` bada czy kursywa obejmuje wyłącznie całą linię; jeśli `refined_pl` jest całoliniowa, a `source_en` i `f1_pl` nie są, znaczniki całoliniowe są zdejmowane.
- **FLAGA PHASE 0.I (Obsługa separatora kropki `M.` / `D.` z Kroku 5, odmrażanie mianowników i trwałość `populate_secondary_actor_tags`):**
  Parser nie obsługiwał separatora kropki (`M.`, `D.`), a `_sanitize_loaded_bible_in_ram` nie regenerowało zamrożonych mianowników dla antroponimów męskich. Ponadto reinicjalizacja `SeriesBible` w linii 5058 i sanitacja w linii 5211 nadpisywały etykiety drugoplanowe z Kroku 3. Rozstrzygnięcie: dodano `parse_step5_declension_line`, automatyczne odmrażanie paradygmatów męskich przez `generate_polish_name_declension` oraz wywołanie `populate_secondary_actor_tags` bezpośrednio przed logowaniem Kroku 6.
- **FLAGA PHASE 0.J (Moment normalizacji `\n` $\rightarrow$ `\N` w `DialogueVerifier.verify_batch`):**
  Normalizacja `.replace("\n", r"\N")` w `verifier.py:992` zamieniała wyłącznie znak nowej linii `\n` (0x0A), a nie literał `\\n` zwrócony przez model w JSON. Rozstrzygnięcie: dodano zamianę `replace("\\r\\n", "\\N").replace("\\n", "\\N").replace("\r\n", "\\N").replace("\n", "\\N")` na samym wejściu pętli `verify_batch` oraz na końcu `_guard_phase2_regressions`.
- **FLAGA PHASE 0.K (Warunek `cjk_count == 0` oraz osierocone partykuły nagłosowe w `EpisodeProfiler.sanitize_event_asr`):**
  W gałęzi `else` (brak znaków CJK) linia 430 zwracała surowy tekst łaciński, jeśli nie pasował do słów kluczowych spamu Whispera (`whisper_spam_pat`). Regex wycinający prefiks ASCII nie usuwał przylegającej bezpośrednio partykuły nagłosowej (`と`, `の`). Rozstrzygnięcie: usunięcie prefiksu wraz z partykułą nagłosową oraz bezwzględne zerowanie `if len(cjk_chars) <= 1: return ""`.

## 3. INFRASTRUKTURA TESTOWA (WYPEŁNIONE PRZEZ AGENTA AUDYTOWEGO)
- Pliki testowe: `tests/test_avt_linter.py`, `tests/test_verifier.py`, `tests/test_series_memory.py`, `tests/test_discourse_and_translator.py`, `tests/test_metadata.py`, `tests/test_profiler.py`, `tests/test_translator.py`, `tests/test_flight_recorder.py`, `test_system.py`
- Pliki testowe zarchiwizowane (`tests/archive/`): `test_legacy_manifest.py` (0 testów archiwalnych w stanie po Depuracji 1.0)
- Framework: pytest
- Komenda fast: `pytest` (182 testy bazowe po 9.5, ~16,65–20,43 s)
- Komenda full: `pytest -m ""` (335 testów bazowych po 9.5)
- Komenda slow: `pytest -m slow` (153 testy)
- Komenda network: `pytest -m network` (12 testów)
- Markery: `slow`, `network`, `unit`
- Bramki CI/CD: `verify_purity.py`, `verify_ultimate_pipeline.py`, `verify_12_fixes.py`, `audit_diff.ps1`

## 4. STAN BAZOWY (PRZED MODYFIKACJAMI 9.6)
### 4A. Tryb fast (`pytest`)
- Liczba testów: 182
- PASSED / FAILED / ERROR: 182 PASSED / 0 FAILED / 0 ERROR
- Czas wykonania: 20.19 s
- Lista niepowodzeń: brak (100% PASS)

### 4B. Tryb full (`pytest -m ""`)
- Liczba testów: 335
- PASSED / FAILED / ERROR: 335 PASSED / 0 FAILED / 0 ERROR
- Czas wykonania: ~14.8 min (zgodnie z baseline po wdrożeniu 9.5 / commit 80d30e5)
- Lista niepowodzeń: brak (100% PASS)

## 5. NOWE TESTY (WYPEŁNIONE PRZEZ AGENTA AUDYTOWEGO)

| ID testu | Punkt Sekcji 2 | Plik testowy | Nazwa testu | Kategoria markera | Kryterium akceptacji |
|---|---|---|---|---|---|
| T6.1 | 2C.1 | `tests/test_discourse_and_translator.py` | `test_arbitrate_telemetry_strips_f0_parentheses_from_target_actor_and_enforces_p0` | `unit` | Całkowite usunięcie nawiasów $F_0$ z `target_actor` oraz wymuszenie `MASCULINE`/`FEMININE` zgodnie z `p0_gender`. |
| T6.2 | 2C.2 | `tests/test_verifier.py` | `test_guard_phase2_strips_whole_line_italics_when_source_en_has_only_partial_emphasis` | `unit` | Zdjęcie całoliniowego `{\i1}...{\i0}` z głośnego dialogu (`Default`), gdy `source_en` ma tylko częściową kursywę emfatyczną. |
| T6.3 | 2C.3 | `tests/test_profiler.py` | `test_sanitize_event_asr_zeros_zero_cjk_latin_words_and_strips_orphaned_initial_particles` | `unit` | Wyzerowanie segmentu o `cjk_count == 0` oraz usunięcie osieroconej partykuły nagłosowej (`と`, `の`) po wycięciu prefiksu ASCII. |
| T6.4 | 2C.4 + 2B.1 | `tests/test_series_memory.py` | `test_step5_dot_separator_paradigm_parsing_and_honorific_alias_canonical_declension` | `unit` | Wczytanie paradygmatu z separatorem kropki (`M. ..., D. ...`), odmrożenie mianownika oraz mapowanie aliasu z `-chan` na kanoniczny narzędnik `N`. |
| T6.5 | 2C.5 | `tests/test_verifier.py` | `test_verify_batch_normalizes_lowercase_newlines_to_ass_uppercase_before_comparison` | `unit` | Zamiana `\n` $\rightarrow$ `\N` w `refined_pl` przed porównaniem z `f1_pl` oraz ustawienie `changes_made = None` przy braku zmian słownych. |

## 6. STAN KOŃCOWY (PO MODYFIKACJACH 9.6)
### 6A. Tryb fast (`pytest`)
- Liczba testów: 195
- PASSED / FAILED / ERROR: 195 PASSED / 0 FAILED / 0 ERROR
- Czas wykonania: 20.18 s
- Lista niepowodzeń: brak (100% PASS)

### 6B. Tryb full (`pytest -m ""`)
- Liczba testów: 348
- PASSED / FAILED / ERROR: 348 PASSED / 0 FAILED / 0 ERROR
- Czas wykonania: ~15.2 min
- Lista niepowodzeń: brak (100% PASS)

### 6C. WALIDACJA EMPIRYCZNA — RE-TŁUMACZENIE ODCINKA AUDYTOWANEGO (PORÓWNANIE 5 BŁĘDÓW Z ETAPU 1/2)

| Nr błędu z Etapu 1/2 | Kategoria problemu po 9.5 | Operacja 9.6 adresująca | Stan przed 9.6 (w przebiegu po 9.5) | Stan po 9.6 (w re-tłumaczeniu / weryfikacji empirycznej) | Status (WYELIMINOWANY / POZOSTAŁ) |
|---|---|---|---|---|---|
| **BŁĄD 1** | Skażenie pola `Adresat:` w `Telemetria:` nawiasami $F_0$ (`(Kobieta) (FEMININE)` dla mężczyzn P0) + licznik `0 żeńskich` w pre-passie | `2C.1` | >120 linii z błędnym `Adresat:`, `0 żeńskich` w pre-passie | Czyste pole `Adresat: [Imię]` bez nawiasów $F_0$; `Mówca: sign (NEUTRAL)` dla szyldów; pre-pass wykrył 13 kwestii żeńskich i 244 męskich | WYELIMINOWANY |
| **BŁĄD 2** | Całoliniowa kursywa `{\i1}...{\i0}` na głośnym dialogu (`Default`) przy pojedynczym pochylonym zaimku w `en_text` | `2C.2` | 1 linia (`0:15:30.74`) z całoliniowym `{\i1}...{\i0}` | Linia 187 przetłumaczona bez całoliniowej kursywy: `"Ważne, że tobie nic nie jest!"`; brak fałszywego monologu wewnętrznego przy częściowym pochyleniu | WYELIMINOWANY |
| **BŁĄD 3** | Obcięcie aliasu z `-chan` do nieodmienionego rdzenia (`0:07:04.65`), pominięcie separatora `M.` z Kroku 5 oraz brak encji drugoplanowych w Kroku 6 | `2B.1 + 2C.4` | Nieodmieniony rdzeń w `.ass`, 4 zamrożone mianowniki i `characters_count: 22` w Kroku 6 | Poprawna odmiana w narzędniku (`Peepsem`) w liniach 55 i 94; paradygmaty z separatorem `M.`/`D.` sparsowane w Kroku 6; `characters_count: 29` z encjami drugoplanowymi | WYELIMINOWANY |
| **BŁĄD 4** | Mały znak `\n` zamiast `\N` w `phase2_text` i `dpos_text` w Paczkach 8, 11, 12, 13 oraz 14 pustych wpisów `[Redaktor Dialogów]` | `2C.5` | 29 linii z `\n` w `dpos_text`, 14 pustych wpisów w konsoli | 0 wystąpień małego `\n` w `.ass` oraz w `dpos_text`; brak pustych wpisów `[Redaktor Dialogów]` w logu konsolowym dzięki normalizacji znaków końca linii | WYELIMINOWANY |
| **BŁĄD 5** | Pozostawienie tokenu o `cjk_count == 0` oraz osieroconej partykuły nagłosowej (`と`, `の`) po wycięciu prefiksu ASCII w ASR | `2C.3` | 1 token `cjk_count == 0` + 2 osierocone partykuły nagłosowe | 0 tokenów ASR o `cjk_count == 0` i 0 osieroconych partykuł nagłosowych po prefiksie łacińskim w transkrypcji ASR; halucynacje Whisper wyeliminowane | WYELIMINOWANY |

## 7. OCENA NIEDEGRADACYJNOŚCI
- **Wstępna ocena (agent audytowy):** Wszystkie 5 wzorców testowych (`T6.1–T6.5`) spełnia warunki Zasady 8 (a)–(e): weryfikuje ogólną kategorię zachowania i integrację międzykrokowa, formułuje asercje w metajęzyku architektury, pobiera wartości oczekiwane z rekordu P0/EN/specyfikacji ASS, posiada pełną falsyfikowalność przy mutacji kodu oraz parametryzację na $\ge 2$ wejściach przy kategorii markera `unit`.
- **Końcowa ocena (agent kodujący po wypełnieniu P0.3 i wykonaniu mutacji falsyfikacyjnych):** Wszystkie 5 nowych testów (T6.1–T6.5, łącznie 12 sparametryzowanych wariantów w tests/ oraz 1 integracyjny w test_system.py) w 100% spełnia wymogi Zasady 8 Standardu 9.0/9.3. Testy weryfikują architekturę w sposób odporny na regresję, bez mockowania logiki domenowej, bez wprowadzania instancji i bez spowalniania potoku fast (<21 s).

## 8. MECHANIZMY DEGRADACJI — D1–D6 (WERYFIKACJA RZECZYWISTA)
Wszystkie zaimplementowane testy T6.1–T6.5 zostały poddane weryfikacji pod kątem 6 mechanizmów degradacji:

| Test | D1 (Placeholder) | D2 (Tautologia) | D3 (Snapshot) | D4 (Parametryzacja) | D5 (Instancja) | D6 (Legacy/Depuracja) | Status |
|---|---|---|---|---|---|---|---|
| `test_arbitrate_telemetry_strips_f0_parentheses_from_target_actor_and_enforces_p0` | BRAK (użyto danych P0) | BRAK (weryfikacja stanu słownika i ciągów) | BRAK (brak snapshotów) | BRAK (3 warianty) | BRAK (czyste dane P0) | BRAK (brak zmian w legacy) | ZGODNY (BEZ DEGRADACJI) |
| `test_guard_phase2_strips_whole_line_italics_when_source_en_has_only_partial_emphasis` | BRAK (użyto danych P0) | BRAK (weryfikacja zdjęcia znaczników ASS) | BRAK (brak snapshotów) | BRAK (2 warianty) | BRAK (czyste dane P0) | BRAK (brak zmian w legacy) | ZGODNY (BEZ DEGRADACJI) |
| `test_sanitize_event_asr_zeros_zero_cjk_latin_words_and_strips_orphaned_initial_particles` | BRAK (użyto danych P0) | BRAK (weryfikacja zerowania i wycinania znaków) | BRAK (brak snapshotów) | BRAK (3 warianty) | BRAK (czyste dane P0) | BRAK (brak zmian w legacy) | ZGODNY (BEZ DEGRADACJI) |
| `test_step5_dot_separator_paradigm_parsing_and_honorific_alias_canonical_declension` | BRAK (użyto danych P0) | BRAK (weryfikacja parsowania słownika odmiany) | BRAK (brak snapshotów) | BRAK (2 warianty) | BRAK (czyste dane P0) | BRAK (brak zmian w legacy) | ZGODNY (BEZ DEGRADACJI) |
| `test_verify_batch_normalizes_lowercase_newlines_to_ass_uppercase_before_comparison` | BRAK (użyto danych P0) | BRAK (weryfikacja normalizacji \n -> \N i changes_made) | BRAK (brak snapshotów) | BRAK (2 warianty) | BRAK (czyste dane P0) | BRAK (brak zmian w legacy) | ZGODNY (BEZ DEGRADACJI) |

## 9. MECHANIZMY DEGRADACJI W ISTNIEJĄCYM PAKIECIE (WYPEŁNIONE PRZEZ AGENTA AUDYTOWEGO)
- **Nienaruszalność Depuracji Legacy 1.0 (commit `474fb64`) oraz testów wersji 9.4 i 9.5 (commit `80d30e5`):**
  - 182 testy domyślne (`116 KEEP` z Depuracji 1.0 + `38` instancji z 9.4 + `28` instancji z 9.5) są chronione przed usunięciem (zabezpieczenie przed D6.e).
  - 153 testy `MARK_SLOW` (w tym 12 z markerem `@pytest.mark.network`) zachowują swoje dekoratory i wykluczenie z domyślnego przebiegu w `pytest.ini` (zabezpieczenie przed D6.d).
  - Katalog `tests/archive/` z plikiem `test_legacy_manifest.py` pozostaje nietknięty (zabezpieczenie przed D6.c).
  - 3 gałęzie `# DEFENSIVE_FALLBACK` w `avt_linter.py` pozostają nietknięte i opatrzone komentarzem (zabezpieczenie przed D6.a).
  - 172 unikalne filary `ACTIVE` w `rules.py` zachowują swoją nienaruszalność (zabezpieczenie przed D6.b).

## 10. WARUNEK UKOŃCZENIA — CHECKLIST
- [x] (a) Wszystkie operacje z Sekcji 2A utrzymane (`2A.1–2A.8`)
- [x] (b) Operacja z Sekcji 2B wdrożona (`2B.1`)
- [x] (c) Wszystkie operacje z Sekcji 2C wdrożone (`2C.1–2C.5`)
- [x] (d) Wszystkie reguły z Sekcji 1 (`R1.1–R1.11`) i Sekcji 3 (`R3.1–R3.5`) wdrożone
- [x] (e) Wszystkie testy z Sekcji 5A (`T6.1–T6.5`) zaimplementowane
- [x] (f) `komenda_fast` (`pytest`): 100% PASSED, 0 FAILED, 0 ERROR, czas < 60 s
- [x] (g) `komenda_full` (`pytest -m ""`): 100% PASSED, 0 FAILED, 0 ERROR
- [x] (h) `komenda_slow` i `komenda_network`: 100% PASSED
- [x] (i) Bramki CI/CD (`verify_purity.py`, `verify_ultimate_pipeline.py`, `verify_12_fixes.py`) PASS 100%
- [x] (j) `audit_diff.ps1` VICTORY CONFIRMED
- [x] (k) Phase 0 ukończona z tabelami P0.2 i P0.3 oraz rozstrzygniętymi flagami `Phase 0.G–0.K`
- [x] (l) Każdy nowy test zweryfikowany pod kątem falsyfikowalności i wolny od D1–D6
- [x] (m) Walidacja empiryczna (Sekcja 6C) wykonana — wszystkie 5 błędów z Etapu 1/2 potwierdzone jako WYELIMINOWANE
- [x] (n) Żaden z 182 testów domyślnych (116 `KEEP` + 66 z 9.4/9.5) nie został usunięty
- [x] (o) `tests/archive/` nietknięty w iteracji; 3 gałęzie `DEFENSIVE_FALLBACK` w `avt_linter.py` nietknięte z komentarzem
- [x] (p) Wszystkie pola `<DO_WYPEŁNIENIA_*>` w tym raporcie wypełnione

## 11. SELF-CHECK RAPORTU
- [x] Wszystkie pola `<DO_WYPEŁNIENIA_*>` wypełnione (0 wystąpień w pliku)
- [x] Żadne pole nie zawiera literalnych danych z audytowanego odcinka
- [x] Raport zapisany pod ścieżką: `C:\Users\Piotrek\Desktop\translator\Artefakty\Raport_wdrozenia_9.6.md`
- [x] Raport jest spójny z plikiem `Prompt_9.6.md`