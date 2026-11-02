# Plik: C:\Users\Piotrek\Desktop\translator\Artefakty\Prompt_9.5.md

# PROMPT NAPRAWCZY POTOKU AVT — WERSJA 9.5

## PREAMBUŁA

Dokument definiuje operacje kodowe, regułowe i walidacyjne rozszerzające potok AVT z wersji 9.4 (commit `85ecedd` / `473c15b`) oraz utrzymujące stan po Depuracji Legacy 1.0 (commit `474fb64`) do wersji **9.5**. Cel operacji:
1. Pełne podpięcie w głównym przepływie wykonawczym runtime (`translator.py`, `profiler.py`, `series_memory.py`, `verifier.py`) metod zaimplementowanych w wersji 9.4 (`arbitrate_event_telemetry`, `reconcile_prepass_with_p0`, `populate_secondary_actor_tags`, `sync_verified_profile_entity` z mapą odmiany z Kroku 5 oraz `sanitize_event_asr` z licznikiem `consecutive_streak` i `duplicate_time_distance_sec`), tak aby wektor `telemetry` w Kroku 10, rejestr postaci i paradygmatów w Kroku 6 oraz bufor ASR w Kroku 4 odzwierciedlały w 100% stan rekordu P0 w rzeczywistym przebiegu odcinka.
2. Domknięcie ochrony napisów ekranowych (`is_sign: true`, w tym zdarzeń z `Name == "sign"` i tagami `\pos(x,y)`) przed rozbijaniem na ułamkowe segmenty przez `split_oversized_ass_events`, domknięcie regexu sanitacji relacji w `_validate_relation_entry_consistency`, deterministyczne otaczanie `phase1_text` znacznikami `{\i1}...{\i0}` dla stylu `Italics` oraz ochrona ciągłości składniowej zdań rozbitych wielokropkiem i zgodności rodzajowej P0 na granicy Fazy 1 i Fazy 2.

Niniejszy dokument przestrzega czterech nadrzędnych zasad Standardu 9.0 oraz rozszerzeń Standardu 9.3–9.5:
1. **Zero-Literal** — wszystkie reguły, opisy operacji i kryteria operują wyłącznie na kategoriach językowych i metajęzykowych architektury.
2. **Pure Positive Domain Invariant** — każda reguła w Sekcji 1 i Sekcji 3 oraz każde kryterium akceptacji w Sekcji 2 i Sekcji 5 definiuje zbiór dopuszczalnych stanów docelowych w formie pozytywnej („prawidłowy stan = X", „zachowuje…", „obejmuje wyłącznie…", „ma pierwszeństwo wobec…").
3. **Primary LLM Translation Authority** — pierwotne tłumaczenie Fazy 1 (`phase1_text`) jest nadrzędnym autorytetem translacyjnym; każda zmiana w Fazie 2 lub post-processingu opiera się na twardym dowodzie z rekordu P0 (`p0_gender`, `has_verified_gender: true`) lub jednoznacznym sygnale źródłowym `en_text` / `pronouns_en`.
4. **Instance-Free Metalinguistic Architecture** — wszystkie interwencje operują na kategoriach modułów, funkcji, operatorów i struktur danych.
5. **Ochrona nienaruszalności Depuracji Legacy 1.0 (Zasada 16)** — wdrożenie wersji 9.5 zachowuje w 100% stan po Depuracji 1.0 i wersji 9.4: wszystkie 154 testy domyślne (`KEEP` + jednostkowe 9.4) pozostają aktywne w przebiegu `pytest`, markery `@pytest.mark.slow` (153 testy) i `@pytest.mark.network` (12 testów) pozostają nienaruszone, katalog `tests/archive/` pozostaje nietknięty, a 3 chronione gałęzie `# DEFENSIVE_FALLBACK` w `avt_linter.py` zachowują swoją postać i komentarze.

Numer wersji: **9.5**. Poprzednia wersja toru naprawczego: **9.4**. Wersja toru Depuracji Legacy w tle: **1.0** (commit `474fb64`).

---

## IDENTYFIKATORY METAJĘZYKA ARCHITEKTURY

- **Moduły i klasy:** `avt_linter.py`, `verifier.py`, `series_memory.py`, `profiler.py`, `rules.py`, `translator.py`, `scene_discourse.py`, `metadata.py`, `flight_recorder.py`, `sign_detector.py`, `AVTLinter`, `EpisodeQualityGate`, `EpisodeFlightRecorder`, `DialogueVerifier`, `SeriesBible`, `EpisodeProfiler`, `SceneDiscourseGraph`, `RuleDispatcher`, `VisualSignDetector`.
- **Funkcje i metody:** `lint_and_fix_line`, `audit_and_fix_entire_episode`, `_run_phase_7_hygiene`, `normalize_ass_tags_and_sign_layout`, `should_apply_top_alignment_on_collision`, `arbitrate_event_telemetry`, `build_discourse_topology`, `_guard_phase2_regressions`, `verify_batch`, `enforce_sign_nominative_orthography`, `_sanitize_loaded_bible_in_ram`, `sync_verified_profile_entity`, `_validate_relation_entry_consistency`, `preserve_italics_for_upright_style`, `reconcile_prepass_with_p0`, `profile_episode`, `_extract_f0_contour`, `sanitize_event_asr`, `report_step_11_quality_gate`, `get_all_fixes`, `get_active_rules`, `detect_signs`, `synchronize_ass_event_metadata_and_styles`, `build_phase1_prompt`, `clean_anime_filename`, `normalize_anime_slug`.
- **Kroki i fazy:** Krok 0–11, Faza 0 (higiena), Faza 0 (Phase 0 — czytanie kodu), Faza 1 (tłumaczenie), Faza 2 (weryfikacja), post-processing.
- **Enum values i pola schematu:** `MALE`, `FEMALE`, `UNKNOWN`, `MASCULINE`, `FEMININE`, `VIRILE`, `NON_VIRILE`, `POLYLOGUE`, `CHÓR`, `ANTHROPONYM`, `is_sign`, `is_internal_monologue`, `has_verified_gender`, `speaker_name`, `addressee_gender`, `p0_gender`, `en_text`, `dpos_text`, `phase1_text`, `phase2_text`, `ass_text`, `telemetry`, `prosody_tags`, `pronouns_en`, `priority`, `confidence`, `P0`, `P1`, `P2`, `strict_positive_domain`, `changes_made`, `refined_pl`, `f1_pl`, `asr_text`, `M`, `D`, `C`, `B`, `N`, `Ms`, `W`.
- **Znaczniki formatu ASS:** `[Script Info]`, `[V4+ Styles]`, `[Events]`, `Dialogue:`, `\N`, `\n`, `{\...}`, `\an7`, `\an8`, `\an9`, `\pos(x,y)`, `\3c`, `\1c`, `\bord`, `\shad`, `\i1`, `\i0`, `\blur`.
- **Placeholdery testowe:** `<RZECZYWISTY_ANTROPONIM_1>`, `<RZECZYWISTY_ANTROPONIM_2>`, `<RZECZYWISTY_ANTROPONIM_MĘSKI_1>`, `<RZECZYWISTY_ANTROPONIM_ŻEŃSKI_1>`, `<RZECZYWISTY_CIĄG_PL_1>`, `<RZECZYWISTY_CIĄG_PL_2>`, `<RZECZYWISTY_CIĄG_EN_1>`, `<RZECZYWISTY_CIĄG_EN_2>`, `<RZECZYWISTY_KOLOR_HEX_1>`, `<RZECZYWISTA_POZYCJA_POS_1>`, `<RZECZYWISTY_PARADYGMAT_M_1>`, `<RZECZYWISTY_PARADYGMAT_D_1>`, `<RZECZYWISTY_PARADYGMAT_W_1>`, `<WARTOŚĆ_ENUM_TECHNICZNA_1>`, `<WARTOŚĆ_ENUM_TECHNICZNA_2>`.

---

## FAZA 0 — CZYTANIE KODU (OBOWIĄZKOWA)

Przed wprowadzeniem jakiejkolwiek zmiany w kodzie agent kodujący ma bezwzględny obowiązek wykonania Fazy 0 i udokumentowania jej wyników w sekcji `2. PHASE 0 — WYNIK WERYFIKACJI KODU` pliku `C:\Users\Piotrek\Desktop\translator\Artefakty\Raport_wdrozenia_9.5.md`.

### P0.1. Lista plików do przeczytania w całości i weryfikacji ścieżek wywołań runtime
1. `translator.py` — dokładne prześledzenie metody głównej tłumaczącej odcinek:
   - gdzie budowany jest ciąg `Telemetria: [Mówca: ... | Adresat: ...]` zapisywany w Kroku 10 i przekazywany do Fazy 1/2 (dlaczego pomija `SceneDiscourseGraph.arbitrate_event_telemetry`),
   - gdzie w Kroku 3/6 wywoływana jest synchronizacja z `SeriesBible` (dlaczego pomija `populate_secondary_actor_tags` oraz przekazanie słownika odmiany z Kroku 5 do `sync_verified_profile_entity`),
   - gdzie w Kroku 4 pobierane i formatowane są segmenty `JP Audio (Whisper):` (dlaczego pomijają `EpisodeProfiler.sanitize_event_asr` z `duplicate_time_distance_sec` i `consecutive_streak`),
   - gdzie po Fazie 1 następuje przekazanie `phase1_text` do Fazy 2 (brak deterministycznego otoczenia `{\i1}...{\i0}` dla linii o stylu `Italics`),
   - gdzie wywoływane jest `split_oversized_ass_events` (dlaczego rozbija zdarzenie o `Name == "sign"` i tagu `\pos()`).
2. `scene_discourse.py` — weryfikacja `SceneDiscourseGraph.build_discourse_topology` oraz `SceneDiscourseGraph.arbitrate_event_telemetry`.
3. `series_memory.py` — weryfikacja `SeriesBible.get_character` (mapowanie dwujęzycznych aliasów etykiet z `[Events]` na klucze w `characters`), `_sanitize_loaded_bible_in_ram` (regeneracja uszkodzonych paradygmatów z dysku w `declensions`), `_validate_relation_entry_consistency` (regex wycinający klauzulę hierarchiczną z zagnieżdżonymi nawiasami kwadratowymi) oraz `sync_verified_profile_entity`.
4. `profiler.py` — weryfikacja `EpisodeProfiler.sanitize_event_asr` (obsługa sklejonych tokenów ASCII+Kana/Kanji) oraz `reconcile_prepass_with_p0`.
5. `verifier.py` — weryfikacja `DialogueVerifier.verify_batch` oraz `_guard_phase2_regressions` (ochrona zgodności rodzajowej z `p0_gender`, ochrona pisowni wołacza `W` i ciągłości wielokropka).
6. `sign_detector.py` i `avt_linter.py` — weryfikacja `VisualSignDetector.detect_signs` oraz zachowania 3 gałęzi `# DEFENSIVE_FALLBACK`.

### P0.2. Tabela mapowania plan ↔ kod (obowiązkowa w `Raport_wdrozenia_9.5.md`)
Dla każdej operacji z Sekcji 2B i 2C wypełnij w `Raport_wdrozenia_9.5.md` wiersz tabeli:
`Operacja | Miejsce wywołania w planie | Rzeczywiste miejsce wywołania w kodzie (plik + linia + metoda) | Zgodność | Rozstrzygnięcie`.

### P0.3. Tabela mapowania danych testowych (obowiązkowa w `Raport_wdrozenia_9.5.md`)
Wypełnij w `Raport_wdrozenia_9.5.md` tabelę mapowania wszystkich placeholderów `<RZECZYWISTY_*>` na autentyczne wartości pobrane z `SeriesBible` / `en_text` odcinka testowego (innego niż odcinek audytowany, zgodnie z Zasadą 9 i 13).

### P0.4. Weryfikacja flag Phase 0 (Inspekcja wpięcia runtime — End-to-End Runtime Wiring)
- **FLAGA PHASE 0.D (Wpięcie `arbitrate_event_telemetry` w `translator.py`):** Zidentyfikować w `translator.py` dokładną linię kodu konstruującą napis `[Mówca: ... (...)]` i potwierdzić, dlaczego dla postaci o `p0_gender == "MALE"` w Kroku 6 wyemitowano `(FEMININE)` w Kroku 10.
- **FLAGA PHASE 0.E (Wpięcie `sanitize_event_asr` w pętli Kroku 4):** Zidentyfikować w `translator.py` / `profiler.py` dokładne miejsce przypisywania transkrypcji Whispera do linii dialogowych (zarówno przy świeżej transkrypcji, jak i przy odczycie z pamięci podręcznej) i potwierdzić przekazanie `duplicate_time_distance_sec` oraz `consecutive_streak`.
- **FLAGA PHASE 0.F (Ochrona zdarzeń `Name: sign` i `\pos()` przed `split_oversized_ass_events`):** Zidentyfikować w `translator.py` miejsce wywołania `split_oversized_ass_events` i potwierdzić warunek wykluczający zdarzenia `is_sign` oraz zdarzenia z `Name.lower() in ("sign", "signs", "txt", "title")` lub z tagiem `\pos(` / `\move(`.

---

## SEKCJA 1: REGUŁY DLA MODELI LLM (Faza 1 i Faza 2)

### Priorytet P0 (Reguły nienaruszalne — realizacja Primary LLM Translation Authority)

1. **R1.1 (P0):** Prawidłowy stan wypowiedzi dla mówcy o `p0_gender == "FEMALE"` w 1. os. lp. czasu przeszłego i trybu przypuszczającego = zachowanie form żeńskich; dla mówcy o `p0_gender == "MALE"` = zachowanie form męskich. Zwroty do adresata o `p0_gender == "FEMALE"` w 2. os. lp. zachowują formy żeńskie, a zwroty do grupy o `p0_gender == "FEMALE"` zachowują formy niemęskoosobowe (`NON_VIRILE`). Źródło stanu docelowego: rekord P0 (`SeriesBible` / `EpisodeProfiler`, `has_verified_gender: true`).
2. **R1.2 (P0):** Prawidłowy stan osoby i liczby orzeczenia w `phase1_text` i `phase2_text` = pełna zgodność z podmiotem w `en_text`. Podmiot 1. os. lp. w `en_text` zachowuje orzeczenie w 1. os. lp. niezależnie od liczby dopełnienia. Źródło stanu docelowego: `phase1_text` oraz jednoznaczny sygnał `en_text` / `pronouns_en`.
3. **R1.3 (P0):** Prawidłowy stan czasowników epistemicznych, wolitywnych i modalnych w 1. os. lp., form trybu przypuszczającego (`-bym`/`-łabym`/`-łbym`) oraz czasu przeszłego obecnych w `en_text` i `phase1_text` = pełne zachowanie ich kategorii modalnej i temporalnej w `refined_pl` wraz ze zdaniami podrzędnymi dopełnieniowymi identyfikującymi. Źródło stanu docelowego: `phase1_text` oraz `en_text`.
4. **R1.6 (P0):** Prawidłowy stan przekładu w `phase1_text` i `phase2_text` = bezwzględne pierwszeństwo semantyczne `en_text` oraz jawnego aktora z kolumny `Name` w `[Events]` i rekordu P0 z `SeriesBible` nad pomocniczą transkrypcją ASR i pomocniczymi tagami `telemetry`. Źródło stanu docelowego: `en_text` oraz rekord P0 (`SeriesBible`).
5. **R1.7 (P0):** Prawidłowy stan rodzaju gramatycznego 1. os. lp. czasu przeszłego (`-łem` / `-łam`), trybu przypuszczającego oraz 3. os. lp. czasu przeszłego odnoszącej się do podmiotu o zweryfikowanym `p0_gender` = stuprocentowa zgodność ze zweryfikowanym `p0_gender` postaci w `SeriesBible` / `EpisodeProfiler` (niezależnie od wysokości tembru głosu seiyū w `speaker_tags`). Źródło stanu docelowego: rekord P0 (`p0_gender`, `has_verified_gender: true`).
6. **R1.9 (P0):** Prawidłowy stan znaczników pochylenia w `phase1_text` i `phase2_text` = dla linii z `is_internal_monologue: true` (styl `Italics` / `Flashback_Italics`) pojedyncza para znaczników `{\i1}...{\i0}` obejmuje cały tekst wypowiedzi; dla linii dialogowej z jawnym adresatem i `is_internal_monologue: false` tekst główny pozostaje prosty, a znaczniki `{\i1}...{\i0}` obejmują wyłącznie pojedynczy wyraz wyróżniony emfatycznie w `en_text`. Źródło stanu docelowego: `phase1_text`, atrybut `is_internal_monologue` oraz `en_text`.
7. **R1.10 (P0):** Prawidłowy stan zdań wielokrotnie złożonych rozbitych na dwa sąsiednie zdarzenia `Dialogue:` tego samego mówcy (gdzie pierwsze zdarzenie kończy się wielokropkiem `...`) = pełne powiązanie składniowe obu zdarzeń: albo drugie zdarzenie rozpoczyna się wielokropkiem otwierającym `...` i małą literą jako bezpośrednie dopełnienie/orzeczenie pierwszego zdarzenia, albo pierwsze zdarzenie posiada własne orzeczenie. Źródło stanu docelowego: `phase1_text` oraz `en_text`.

### Priorytet P1 (Reguły silne — spójność wielogłosu, wołacza i paradygmatów odmiany)

8. **R1.4 (P1):** Prawidłowy stan dwugłosu z powtórzonym wierszem z linii bezpośrednio poprzedzającej = zachowanie w `refined_pl` identycznego sformułowania w powtórzonym wierszu (niezależnie od użytego znaku dywizu lub półpauzy `-`, `–`, `—`). Źródło stanu docelowego: `phase1_text` oraz `en_text`.
9. **R1.8 (P1):** Prawidłowy stan deklinacji antroponimów i terminów kanonicznych w wołaczu `W` i przypadkach zależnych `D..Ms` = pełna zgodność ortograficzna rdzenia (w tym podwojonych spółgłosek) i końcówki fleksyjnej z paradygmatem z `EpisodeProfiler` i `SeriesBible` oraz wydzielenie inicjalnego wołacza `W` przecinkiem od dalszej części zdania. Źródło stanu docelowego: rekord P0 (`EpisodeProfiler` / `SeriesBible`) oraz `phase1_text`.

### Priorytet P2 (Reguły jakościowe — odpowiedniość napisów `is_sign` i higiena raportowania Fazy 2)

10. **R1.5 (P2):** Prawidłowy stan napisów ekranowych `is_sign: true` = ścisła odpowiedniość semantyczna i leksykalna 1:1 wobec `en_text` w poprawnej formie mianownika `M`, a dla krótkotrwałych plansz ($\le 2,5\text{ s}$) zawierających nagłówek z punktorem `•`/`●` oraz wielozdaniowy tekst tła — zwięzły przekład samego nagłówka głównego mieszczący się w pojedynczym zdarzeniu czasowym. Źródło stanu docelowego: `en_text` oraz rekord P0 (`SeriesBible`).
11. **R1.11 (P2):** Prawidłowy stan pola `changes_made` w odpowiedzi Fazy 2 (`DialogueVerifier`) = wartość `null` wszędzie tam, gdzie tekst merytoryczny `refined_pl` jest tożsamy z `f1_pl`. Źródło stanu docelowego: porównanie `f1_pl` i `refined_pl`.

---

## SEKCJA 2: OPERACJE (2A / 2B / 2C)

### 2A — Operacje potwierdzone z poprzedniego promptu 9.4 (bez nowych akcji)

1. **`2A.1` (z 9.3/9.4) — `DialogueVerifier.enforce_sign_nominative_orthography` (`verifier.py`):** potwierdzona — bez nowych akcji.
2. **`2A.2` (z 9.3/9.4) — `EpisodeQualityGate.should_apply_top_alignment_on_collision` (`avt_linter.py`):** potwierdzona (0 fałszywych podniesień `\an8`) — bez nowych akcji.
3. **`2A.3` (z 9.3/9.4) — Dopasowanie pełnotokenowe w normalizacji etykiet aktorów (`metadata.py`):** potwierdzona — bez nowych akcji.
4. **`2A.4` (z 9.3/9.4) — `EpisodeQualityGate.preserve_italics_for_upright_style` (`avt_linter.py`, `translator.py`):** potwierdzona — bez nowych akcji.
5. **`2A.5` (z 9.4/2B.10) — Ochrona przecinka po inicjalnym wołaczu `W` przed partykułą pytajną `czy` (`avt_linter.py`, `series_memory.py`):** potwierdzona empirycznie w `.ass` (`ID: 158`) — bez nowych akcji.
6. **`2A.6` (z 9.4/2B.11) — Eliminacja pozornych uzasadnień `changes_made` przy braku zmiany tekstu i tagów (`verifier.py`):** potwierdzona — bez nowych akcji (dalsza redukcja przez wyrównanie tagów `{\i1}` w Fazie 1 ujęta w `2C.6`).
7. **`2A.7` (z 9.4/2C.4) — Sanitacja nieznanych pseudotagów szablonowych w blokach `{\...}` (`avt_linter.py`):** potwierdzona empirycznie w `.ass` (`ID: 238`) — bez nowych akcji.
8. **`2A.8` (z 9.4/2C.8) — Pełna lista poprawek `get_all_fixes()` i spójność raportu Kroku 11 (`flight_recorder.py`, `avt_linter.py`):** potwierdzona empirycznie w `.log` (wylistowano 79/79 poprawek ze statusem `spójność: OK`) — bez nowych akcji.

---

### 2B — Nowe operacje (weryfikacja i podpięcie runtime oraz ochrona fleksji P0)

#### OPERACJA 2B.1 — Pełna integracja wywołań runtime w `MultimodalTranslator` (`translator.py`) oraz dwujęzyczne mapowanie aliasów w `SeriesBible` (`series_memory.py`)
- **Lokalizacja:** `translator.py` (główna pętla potoku wykonawczego Kroków 3, 4, 6, 7, 8, 10) oraz `series_memory.py` (`SeriesBible.get_character`, `SeriesBible.get_character_gender`).
- **Natura modułu:** deterministyczny z kontekstem (orkiestracja potoku danych).
- **Rozstrzygnięcie:** **NAPRAWIĆ**.
- **Uzasadnienie systemowe:** Metody naprawcze utworzone w wersji 9.4 (`arbitrate_event_telemetry`, `reconcile_prepass_with_p0`, `populate_secondary_actor_tags`, `sync_verified_profile_entity` z mapą odmiany oraz `sanitize_event_asr` z historią czasów) były wywoływane w testach jednostkowych, lecz główny przebieg w `translator.py` korzystał z wcześniejszych zmiennych lokalnych, a ponadto etykiety angielskie z kolumny `Name` w `[Events]` nie były zmapowane jako aliasy na polskie nazwy ról wygenerowane w `EpisodeProfiler`.
- **Implementacja:**
  1. W `SeriesBible` (`series_memory.py`): dodaj automatyczne dwukierunkowe mapowanie znanych angielskich etykiet ról z sekcji `[Events]` na ich polskie odpowiedniki obecne w `EpisodeProfiler` / `SeriesBible.data["characters"]` (np. gdy w `[Events]` występuje angielska nazwa roli, a w `EpisodeProfiler` jej polski odpowiednik, dopisz angielską nazwę z `[Events]` do listy `aliases` tej encji w `self.data["characters"]`).
  2. W `translator.py`:
     - przed logowaniem Kroku 6 wywołaj `self.series_bible.populate_secondary_actor_tags(list(normalized_actors.keys()))` oraz przekaż wszystkie paradygmaty odmiany wygenerowane w Kroku 5 (`EpisodeProfiler`) do `self.series_bible.sync_verified_profile_entity(..., declension_map=...)`, a następnie wywołaj `self.series_bible._sanitize_loaded_bible_in_ram()`;
     - w Kroku 7 / Kroku 10 podczas budowania stringa `Telemetria:` dla każdego zdarzenia wywołuj bezpośrednio `SceneDiscourseGraph.arbitrate_event_telemetry(event=..., series_bible=self.series_bible, episode_profiler=self.profiler, ...)` i używaj zwróconych z niej pól `speaker_name`, `grammatical_gender` oraz `addressee_gender` jako jedynego źródła dla `Telemetria:`.
- **Kryterium akceptacji:** Prawidłowy stan wykonania runtime w `translator.py` = każde zdarzenie w Kroku 10 posiada wektor `Telemetria:` wygenerowany przez `SceneDiscourseGraph.arbitrate_event_telemetry`, a `SeriesBible` w Kroku 6 zawiera wszystkie encje z Kroku 3 wraz z aliasami i pełnymi paradygmatami z Kroku 5 (źródło autorytetu: rekord P0 w `SeriesBible` i `EpisodeProfiler`).

#### OPERACJA 2B.2 — Strażnik zgodności rodzaju gramatycznego z `p0_gender` na granicy Fazy 1 i Fazy 2 (`verifier.py`)
- **Lokalizacja:** `verifier.py` → `DialogueVerifier._guard_phase2_regressions` (oraz post-check Fazy 1).
- **Natura modułu:** deterministyczny z kontekstem (ochrona rekordu P0).
- **Rozstrzygnięcie:** **NAPRAWIĆ**.
- **Uzasadnienie systemowe:** Gdy mówca lub podmiot wypowiedzi posiada w rekordzie P0 zweryfikowaną płeć męską (`p0_gender == "MALE"`, `has_verified_gender: true`), a Faza 2 zamienia formę męską lub bezosobową z `phase1_text` na formę żeńską 1. os. lp. czasu przeszłego (`-łam`, `-łabym`) lub 3. os. lp. (`-ła`), strażnik regresji musi przywrócić formę zgodną z `p0_gender`.
- **Implementacja:**
  1. W `DialogueVerifier._guard_phase2_regressions` dodaj kategorię `p0_speaker_gender_concordance`:
     - jeśli mówca linii posiada zweryfikowane `p0_gender == "MALE"` (`has_verified_gender: true`), `f1_pl` nie zawiera końcówki 1. os. lp. rodzaju żeńskiego (`-łam`, `-łabym`), a `refined_pl` wprowadza końcówkę `-łam` lub `-łabym` (poza cytatem w cudzysłowie) — zamień końcówkę na męską (`-łem` / `-łbym`) lub przywróć `f1_pl`;
     - symetrycznie, jeśli mówca posiada zweryfikowane `p0_gender == "FEMALE"` (`has_verified_gender: true`), `f1_pl` nie zawiera `-łem`/`-łbym`, a `refined_pl` wprowadza `-łem`/`-łbym` — przywróć formę żeńską (`-łam`/`-łabym`) lub `f1_pl`.
- **Kryterium akceptacji:** Prawidłowy stan wyjścia `_guard_phase2_regressions` dla mówcy o zweryfikowanym `p0_gender` (`has_verified_gender: true`) = stuprocentowa zgodność końcówek 1. os. lp. czasu przeszłego i trybu przypuszczającego z `p0_gender` mówcy (źródło autorytetu: rekord P0 `p0_gender` oraz `phase1_text`).

---

### 2C — Konflikty z poprzednim promptem 9.4 (rozstrzygnięte: dowód empiryczny > analiza teoretyczna)

#### 2C.1 (z 9.4/2B.9 i 9.4/2C.1) — Bezwarunkowe wymuszenie `p0_gender` i jawnego `Name` w `Telemetria:` w runtime (`translator.py` + `scene_discourse.py`)
- **Konflikt z 9.4:** W przebiegu odcinka po wdrożeniu 9.4 (`WYKRYTY BŁĄD 1`) wszystkie główne postacie męskie P0 nadal otrzymały w Kroku 10 `Telemetria: [Mówca: <Antroponim> (FEMININE)]`, w `ID: 218` jawny aktor z `[Events]` został nadpisany inną postacią, a w `ID: 37, 43, 134, 136, 167, 192, 196, 223` postać żeńska otrzymała `(MASCULINE)`.
- **Rozstrzygnięcie (dowód empiryczny > analiza teoretyczna):** **ROZSZERZYĆ** i podpiąć `SceneDiscourseGraph.arbitrate_event_telemetry` bezpośrednio w miejscu formatowania ciągu `Telemetria:` w `translator.py`.
- **Implementacja:**
  1. W `translator.py` zlokalizuj miejsce budujące słownik/ciąg `Telemetria:` dla każdej linii przekazywanej do Fazy 1, Fazy 2 i `EpisodeFlightRecorder`.
  2. Jeśli kolumna `Name` w `[Events]` jest niepusta i nie jest etykietą techniczną (`sign`, `signs`, `txt`, `title`), `speaker_name` w `Telemetria:` jest **zawsze równy jawnemu aktorowi z `[Events]`** (nigdy nie nadpisuj niepustego `Name` z `[Events]` aktorem wywnioskowanym z `build_discourse_topology`, jak miało to miejsce w `ID: 218`).
  3. Dla wyznaczonego `speaker_name` (zarówno jawnego z `[Events]`, jak i wywnioskowanego przy pustym `Name`) odczytaj postać przez `SeriesBible.get_character(speaker_name)` (z uwzględnieniem dwujęzycznych aliasów z `2B.1` oraz `EpisodeProfiler`):
     - gdy `gender == "MALE"`, ustaw bezwarunkowo `(MASCULINE)` (całkowicie ignorując tagi akustyczne $F_0$ z Kroku 4 oraz flagi `female_only_scene`);
     - gdy `gender == "FEMALE"`, ustaw bezwarunkowo `(FEMININE)`.
  4. Analogicznie dla adresata (`Adresat:`): wyznacz adresata z drugiej postaci aktywnej w bieżącej wymianie zdań w scenie i przypisz mu płeć z `SeriesBible.get_character(addressee_name)` (`MALE -> MASCULINE`, `FEMALE -> FEMININE`).
- **Kryterium akceptacji:** Prawidłowy stan pola `Telemetria:` w Kroku 10 pliku `.log` = 100% zachowania jawnego `Name` z `[Events]` oraz 100% zgodności `(MASCULINE)` / `(FEMININE)` z `p0_gender` z Kroku 6 dla każdej postaci P0/P1 (0 wystąpień `(FEMININE)` dla postaci o `gender: MALE` i 0 wystąpień `(MASCULINE)` dla postaci o `gender: FEMALE`; źródło autorytetu: sekcja `[Events]` oraz rekord P0 w `SeriesBible`).

#### 2C.2 (z 9.4/2A i `split_oversized_ass_events`) — Ochrona napisów ekranowych `Name: sign` i `\pos()` przed rozbijaniem na ułamkowe zdarzenia (`translator.py` + `sign_detector.py`)
- **Konflikt z 9.4:** W przebiegu odcinka po wdrożeniu 9.4 (`WYKRYTY BŁĄD 2`, `ID: 238`) zdarzenie o `Name: sign` z tagiem `\pos(337,228)` trwające `1,43 s` zostało rozbite przez `split_oversized_ass_events` na 6 osobnych zdarzeń `Dialogue:` po `0,24 s` każde (`events_count: 265` przy `total_lines: 260`), gubiąc tagi pozycjonowania w częściach 2–6.
- **Rozstrzygnięcie:** **NAPRAWIĆ** klasyfikację `is_sign` oraz warunek strażnika w `split_oversized_ass_events` (`translator.py`).
- **Implementacja:**
  1. W `VisualSignDetector.detect_signs` (`sign_detector.py`) oraz w `translator.py` każde zdarzenie posiadające `event.name.strip().lower() in ("sign", "signs", "txt", "title", "board", "screen")` LUB zawierające w tekście tag `\pos(` / `\move(` przy braku osobowego aktora w `Name` otrzymuje bezwarunkowo flagę `is_sign = True`.
  2. Dla zdarzenia z `is_sign = True`, którego czas trwania wynosi $\le 2,5\text{ s}$, a `en_text` rozpoczyna się od nagłówka z punktorem (`•` lub `●`) i zawiera po `\N` wielozdaniowy tekst dekoracyjny (> 120 znaków), przed wysłaniem do Fazy 1/2 (lub w post-processingu napisu `is_sign`) wyodrębnij wyłącznie pierwszą linię nagłówkową (`• [Nazwa]`), tak aby napis na ekranie był czytelny w czasie `1,43 s`.
  3. W `split_oversized_ass_events` (`translator.py`) dodaj na samym początku bezwzględną blokadę: funkcja **nigdy nie dzieli** zdarzenia, które ma `is_sign == True`, `event.name.strip().lower() in ("sign", "signs", "txt", "title")` lub zawiera w `event.text` tag `\pos(`, `\move(`, `\fad(`, `\an5`, `\an7`, `\an8`, `\an9`.
- **Kryterium akceptacji:** Prawidłowy stan strumienia wyjściowego `[Events]` w `.ass` i Kroku 11 = zachowanie każdego napisu ekranowego (`is_sign: true` / `Name: sign` / `\pos()`) jako pojedynczego, nierozbitego zdarzenia `Dialogue:` z pełnym zachowaniem tagów pozycjonowania oraz równość `events_count == total_lines` (źródło autorytetu: sekcja `[Events]` oraz Zasada 2 Standardu 9.0).

#### 2C.3 (z 9.4/2B.8.a i 9.4/2C.10) — Pełne podpięcie `sanitize_event_asr` w Kroku 4 oraz usuwanie sklejonych tokenów ASCII (`profiler.py` + `translator.py`)
- **Konflikt z 9.4:** W przebiegu odcinka po wdrożeniu 9.4 (`WYKRYTY BŁĄD 3`) w polu `JP Audio (Whisper):` pozostały sklejone tokeny łacińskie (`"Youおじま"`, `"You youI,"`, `"just,,,"`, `"Cと"`, `"Kアクマ"`, `"b僕"`, `"kの"`, `"a相手"`, `"sss"`, `"aaa."`) oraz duplikaty między liniami oddalonymi o `27,75 s` (`ID: 133–134`) i serie 4–6 identycznych segmentów (`ID: 123–126`, `ID: 174–179`, `ID: 202–205`).
- **Rozstrzygnięcie:** **ROZSZERZYĆ** regexy w `EpisodeProfiler.sanitize_event_asr` i podpiąć pętlę deduplikacji czasowej bezpośrednio przed zapisem `asr_text` w Kroku 4 i Kroku 10 (`profiler.py`, `translator.py`).
- **Implementacja:**
  1. W `EpisodeProfiler.sanitize_event_asr` (`profiler.py`) na japońskiej części transkrypcji (przed nawiasem `[romaji]`):
     - usuwaj wszystkie podciągi liter łacińskich ASCII `[A-Za-z]+` wraz z przylegającą do nich powtórzoną interpunkcją `[,.;:!?\s]*` (niezależnie od tego, czy stoją osobno, czy są sklejone bezpośrednio ze znakami japońskimi Kana/Kanji, np. na początku lub w środku ciągu);
     - jeśli po usunięciu znaków ASCII i interpunkcji w japońskim segmencie pozostaje $\le 1$ znak japoński (np. pojedyncza partykuła `と` po usunięciu `C` lub pojedyncza głoska `ん`), wyzeruj cały segment (`""`).
  2. W miejscu budowania słownika transkrypcji w Kroku 4 (oraz przed wstrzyknięciem `JP Audio (Whisper):` do promptów i logu Kroku 10 w `translator.py`) przepuść całą listę zdarzeń odcinka przez sekwencyjny filtr śledzący `last_seen_end_sec[norm_jp_text]` oraz `consecutive_streak`:
     - jeśli ten sam niepusty `norm_jp_text` wystąpił wcześniej w odcinku, a `current_start_sec - last_seen_end_sec[norm_jp_text] > 1.5`, wyzeruj segment (`""`);
     - jeśli ten sam `norm_jp_text` powtarza się w kolejnych sąsiednich liniach (`consecutive_streak > 2`), wyzeruj go we wszystkich liniach powyżej drugiej (`""`).
- **Kryterium akceptacji:** Prawidłowy stan pola `JP Audio (Whisper):` w Krokach 4 i 10 = całkowity brak liter łacińskich ASCII w japońskiej części transkrypcji (poza sekcją `[romaji]`), brak duplikatów oddalonych o $> 1,5\text{ s}$ oraz maksymalnie 2 wystąpienia tego samego segmentu z rzędu (źródło autorytetu: ramy czasowe `[Events]` oraz `en_text`).

#### 2C.4 (z 9.4/2C.5, 9.4/2C.7 i 9.4/2C.9) — Transfer paradygmatów z Kroku 5 do Kroku 6, naprawa regexu w `_validate_relation_entry_consistency` oraz sanitacja `declensions` z dysku (`series_memory.py` + `translator.py` + `verifier.py`)
- **Konflikt z 9.4:** W przebiegu odcinka po wdrożeniu 9.4 (`WYKRYTY BŁĄD 4`) w Kroku 6 główne antroponimy męskie odmienione w Kroku 5 miały zamrożony mianownik (`D..W == M`), w `ID: 192` przeszła do `.ass` literówka w wołaczu (`Abadonie` zamiast `Abaddonie`), stare paradygmaty wczytane z dysku zachowały błędne formy pierwszego członu (`Przestrzeńa`, `Pole'a`, `Promieńa`), a w ostatnim wpisie `relations` pozostał niedomknięty fragment tekstu `', eliminacja hybryd 'Imię... ma pan' oraz odporność na opuszczanie -sama]`.
- **Rozstrzygnięcie:** **ROZSZERZYĆ** `_sanitize_loaded_bible_in_ram`, `_validate_relation_entry_consistency` oraz synchronizację Kroku 5 z Krokiem 6 (`series_memory.py`, `translator.py`, `verifier.py`).
- **Implementacja:**
  1. **Naprawa regexu w `_validate_relation_entry_consistency` (`series_memory.py`):** podczas usuwania sprzecznej klauzuli `RELACJA HIERARCHICZNA` z wpisu o reżimie poufnym używaj wyrażenia dopasowującego pełny blok aż do końcowego nawiasu zamykającego za słowem `-sama]` (uwzględniającego wewnętrzny nawias `[Imię]`, np. `r"(\\N|\s*\[)?RELACJA HIERARCHICZNA[^]]*(\[Imię\][^]]*)?\]?"`), a także oczyszczaj ewentualne osierocone fragmenty `r"',?\s*eliminacja hybryd[^]]*\]"` w istniejących wpisach w RAM.
  2. **Sanitacja i regeneracja `declensions` w RAM (`_sanitize_loaded_bible_in_ram` w `series_memory.py`):**
     - dla każdego klucza w `self.data["declensions"]`, którego wartości w przypadkach zależnych `D..W` zawierają błędne sufiksy męskoosobowe na rzeczownikach nieosobowych zakończonych na spółgłoskę miękką lub `-e` (np. podciągi `ńa`, `ńowi`, `ńem`, `ńie`, `e'a`, `e'owi`, `e'em`, `Promienii`), zregeneruj paradygmat w pamięci RAM za pomocą poprawionej funkcji `generate_polish_name_declension`;
     - dla każdego antroponimu obecnego w Kroku 5 (`EpisodeProfiler`), bezwarunkowo skopiuj jego 7-przypadkowy paradygmat `M..W` z Kroku 5 do `self.data["declensions"]` przed zapisaniem logu Kroku 6.
  3. **Ochrona ortograficzna rdzenia antroponimu w wołaczu `W` (`verifier.py` / `avt_linter.py`):** gdy w `phase1_text` lub `phase2_text` występuje forma wołacza różniąca się od kanonicznego wołacza `W` w `SeriesBible.data["declensions"]` pojedynczą uproszczoną spółgłoską podwójną (odległość edycyjna Levenshteina == 1 w rdzeniu przy zachowaniu tej samej końcówki fleksyjnej `-ie`/`-o`/`-u`), wyrównaj pisownię rdzenia do kanonicznej formy `W` z `SeriesBible`.
- **Kryterium akceptacji:** Prawidłowy stan Kroku 6 w `.log` oraz tekstu `.ass` = pełne paradygmaty `M..W` dla wszystkich antroponimów z Kroku 5 w `declensions`, brak uszkodzonych form (`ńa`, `e'a`) i urwanych ogonów w `relations` oraz 100% poprawności ortograficznej rdzenia antroponimów w wołaczu `W` (źródło autorytetu: Krok 5 `EpisodeProfiler` oraz `SeriesBible`).

#### 2C.5 (z 9.4/2C.2) — Domknięcie ciągłości składniowej zdań rozbitych wielokropkiem między Fazą 1 a Fazą 2 (`verifier.py` + `translator.py`)
- **Konflikt z 9.4:** W `ID: 84–85` (`WYKRYTY BŁĄD 5`) `ID: 84` kończy się wielokropkiem `...` jako zawieszona grupa imienna bez czasownika, natomiast `ID: 85` już w `phase1_text` rozpoczęło się wielką literą bez wielokropka otwierającego, przez co Kategoria 17 w `_guard_phase2_regressions` (porównująca tylko `refined_pl` z `f1_pl`) nie skorygowała braku wiązania.
- **Rozstrzygnięcie:** **ROZSZERZYĆ** obsługę ciągłości zdań rozbitych w `DialogueVerifier._guard_phase2_regressions` (`verifier.py`).
- **Implementacja:**
  1. W `_guard_phase2_regressions` (Kategoria 17 `ellipsis_continuation_syntax`):
     - zachowaj dotychczasową regułę przywracającą `...` i małą literę z `f1_pl`, gdy `refined_pl` je usuwa;
     - dodaj warunek komplementarny: jeśli `prev_line_pl` (należące do tego samego mówcy i tego samego stylu) kończy się wielokropkiem `...`, a w `prev_line_en` zdanie nie jest zakończone kropką/pytajnikiem/wykrzyknikiem (lub zaczyna się w kolejnej linii od kontynuacji składniowej), zaś `refined_pl` w linii bieżącej nie zaczyna się od `...`, dodaj na początku `refined_pl` (wewnątrz ewentualnego tagu `{\i1}`) wielokropek `...`(lub zamień wielokropek końcowy w linii poprzedzającej na dwukropek/myślnik, zachowując spójność składniową pary linii).
- **Kryterium akceptacji:** Prawidłowy stan każdej pary sąsiednich linii tego samego mówcy, w której pierwsza linia kończy się wielokropkiem otwierającym zawieszoną konstrukcję = obecność symetrycznego wielokropka otwierającego `...` na początku drugiej linii (źródło autorytetu: `en_text` oraz reguła `R1.10`).

#### 2C.6 (z 9.4/2C.6) — Deterministyczne domknięcie `{\i1}...{\i0}` po Fazie 1 dla stylu `Italics` oraz czystość separatorów `\N` w `dpos_text` (`translator.py` + `verifier.py`)
- **Konflikt z 9.4:** W przebiegu odcinka po wdrożeniu 9.4 (`WYKRYTY BŁĄD 6`) w 26 liniach o stylu `Italics` Faza 1 zwróciła `phase1_text` bez tagów `{\i1}...{\i0}`, przez co Faza 2 musiała je dodawać i wygenerowała dla nich wpisy w `changes_made`, a w `ID: 177, 228, 231` w `dpos_text` pozostał mały znak `\n` lub podwójny blok `{\i1}...{\i0}\N{\i1}...{\i0}`.
- **Rozstrzygnięcie:** **ROZSZERZYĆ** post-processing Fazy 1 i Fazy 2 (`translator.py`, `verifier.py`).
- **Implementacja:**
  1. W `translator.py` bezpośrednio po odebraniu odpowiedzi Fazy 1: dla każdej linii, która posiada `is_internal_monologue == True` (w tym dla każdej linii o stylu `Italics`, `Italics - Top`, `Flashback_Italics`, `Flashback_Italics - Top` w `[Events]`), jeśli `phase1_text` nie jest otoczony `{\i1}...{\i0}`, deterministycznie otocz cały `phase1_text` pojedynczą parą `{\i1}...{\i0}` (usuwając ewentualne wewnętrzne duplikaty `{\i0}\n{\i1}`) jeszcze przed zapisem `Faza 1 (Draft PL):` i przed przekazaniem do Fazy 2 (`DialogueVerifier.verify_batch`).
  2. W `DialogueVerifier.verify_batch` (`verifier.py`) oraz przed przekazaniem do `AVTLinter`: zamieniaj każdy znak nowej linii `\n` wewnątrz tekstu na standardowy znacznik ASS `\N` oraz scalaj podwójne bloki kursywy w dwóch wierszach (`{\i1}Wiersz 1{\i0}\N{\i1}Wiersz 2{\i0}` $\rightarrow$ `{\i1}Wiersz 1\NWiersz 2{\i0}`).
- **Kryterium akceptacji:** Prawidłowy stan `phase1_text`, `phase2_text` i `dpos_text` dla wszystkich linii o stylu pochyłym (`Italics` / `Flashback_Italics`) = 100% obecności pojedynczej pary otaczających tagów `{\i1}...{\i0}` już w `phase1_text`, brak małych znaków `\n` w `dpos_text` oraz `changes_made == None` dla linii, w których Faza 2 nie zmieniła słów (źródło autorytetu: sekcja `[Events]` / `[V4+ Styles]` oraz `phase1_text`).

---

## SEKCJA 3: REGUŁY DLA PIPELINE'U DANYCH

1. **R3.1 (P0):** Prawidłowy stan `SeriesBible` w pamięci RAM w Kroku 6 = wykonanie w głównym potoku `translator.py` sekwencji: (a) `populate_secondary_actor_tags` dla wszystkich etykiet z Kroku 3, (b) dwukierunkowego zmapowania aliasów angielskich z `[Events]` na polskie nazwy ról z Kroku 5, (c) `sync_verified_profile_entity` z pełnymi paradygmatami odmiany `M..W` z Kroku 5, (d) `_sanitize_loaded_bible_in_ram` regenerującej uszkodzone paradygmaty z dysku oraz (e) `_validate_relation_entry_consistency` z pełnym wycięciem sprzecznych klauzul hierarchicznych. Źródło stanu docelowego: rekord P0 (`EpisodeProfiler` Krok 5) oraz Krok 3.
2. **R3.2 (P0):** Prawidłowy stan wektora `Telemetria:` w Kroku 10 (`translator.py` + `scene_discourse.py`) = bezpośrednie wywołanie `SceneDiscourseGraph.arbitrate_event_telemetry` dla każdego zdarzenia w odcinku, gwarantujące: (a) zachowanie jawnego `Name` z `[Events]`, (b) stuprocentowe wymuszenie `(MASCULINE)` dla każdej encji o `p0_gender == "MALE"` oraz `(FEMININE)` dla każdej encji o `p0_gender == "FEMALE"` ponad tagami $F_0$ z Kroku 4. Źródło stanu docelowego: sekcja `[Events]` oraz rekord P0 (`SeriesBible`).
3. **R3.3 (P0):** Prawidłowy stan przepływu między Fazą 1 a Fazą 2 (`translator.py` + `verifier.py`) = deterministyczne otoczenie `phase1_text` pojedynczą parą `{\i1}...{\i0}` dla wszystkich linii o stylu `Italics`/`Flashback_Italics`, normalizacja `\n` do `\N`, ochrona końcówek rodzajowych zgodnych z `p0_gender` mówcy (`2B.2`), ochrona pisowni rdzenia wołacza `W` (`2C.4`) oraz ochrona ciągłości wielokropka między zdaniami rozbitymi (`2C.5`). Źródło stanu docelowego: rekord P0, `phase1_text` oraz `en_text`.
4. **R3.4 (P0):** Prawidłowy stan obsługi napisów ekranowych `is_sign` (`sign_detector.py` + `translator.py`) = klasyfikacja każdego zdarzenia o `Name.lower() in ("sign", "signs", "txt", "title")` lub z tagiem `\pos(` / `\move(` jako `is_sign: true`, kondensacja krótkotrwałych ($\le 2,5\text{ s}$) wielozdaniowych plansz z punktorem do linii nagłówkowej oraz całkowite wykluczenie zdarzeń `is_sign: true` i `\pos()` z funkcji `split_oversized_ass_events` (`events_count == total_lines`). Źródło stanu docelowego: sekcja `[Events]` oraz Zasada 2 Standardu 9.0.
5. **R3.5 (P0):** Prawidłowy stan bufora ASR w Kroku 4 i Kroku 10 (`profiler.py` + `translator.py`) = wywołanie `EpisodeProfiler.sanitize_event_asr` w pętli produkcyjnej z śledzeniem `duplicate_time_distance_sec` i `consecutive_streak` oraz wycięcie wszelkich sklejonych podciągów ASCII `[A-Za-z]+` z japońskiej części transkrypcji przed konwersją do romaji. Źródło stanu docelowego: ramy czasowe `[Events]` oraz `en_text`.

---

## SEKCJA 4: KOLEJNOŚĆ WDROŻENIA

Kolejność wdrożenia wynika z rozkładu procentowego błędów (33,3% OFFLINE + 66,7% HYBRYDA = 100% udziału ogniw integracji offline) oraz zależności przepływu od Kroku 2 do Kroku 11:

1. **ETAP WDROŻENIOWY 0 — Wykonanie Fazy 0 (Inspekcja ścieżek wywołań runtime w `translator.py` i weryfikacja flag Phase 0.D, 0.E, 0.F):**
   - Przeczytanie plików z listy P0.1, zlokalizowanie miejsc w `translator.py` pomijających metody z 9.4 oraz wypełnienie tabel P0.2, P0.3 i sekcji 2.4 w `Raport_wdrozenia_9.5.md`.
2. **ETAP WDROŻENIOWY 1 — Pełne podpięcie runtime w Krokach 2–7 (`2B.1`, `2C.1`, `2C.2`, `2C.3`, `2C.4`):**
   - Wpięcie w `translator.py` wywołań `populate_secondary_actor_tags`, dwujęzycznych aliasów ról, transferu paradygmatów z Kroku 5 do `sync_verified_profile_entity`, naprawy regexu w `_validate_relation_entry_consistency` oraz regeneracji uszkodzonych paradygmatów z dysku w `_sanitize_loaded_bible_in_ram` (`2B.1`, `2C.4`).
   - Wpięcie w Kroku 4 pętli deduplikacji czasowej i rozszerzonego filtra sklejonych tokenów ASCII w `sanitize_event_asr` (`2C.3`).
   - Wpięcie w `translator.py` wywołania `SceneDiscourseGraph.arbitrate_event_telemetry` jako wyłącznego źródła dla ciągu `Telemetria:` z zachowaniem jawnego `Name` z `[Events]` (`2C.1`).
   - Zabezpieczenie zdarzeń `Name: sign` i `\pos()` przed `split_oversized_ass_events` oraz kondensacja krótkotrwałych szyldów z punktorem (`2C.2`).
3. **ETAP WDROŻENIOWY 2 — Domknięcie barier Fazy 1 i Fazy 2 w Krokach 8–10 (`2B.2`, `2C.5`, `2C.6` + Sekcja 1 i 3):**
   - Deterministyczne otoczenie `phase1_text` pojedynczą parą `{\i1}...{\i0}` dla stylu `Italics` po Fazie 1 i normalizacja `\n` $\rightarrow$ `\N` (`2C.6`).
   - Dodanie kategorii `p0_speaker_gender_concordance` (`2B.2`), wyrównania ortograficznego rdzenia wołacza `W` (`2C.4`) oraz rozszerzonej ciągłości wielokropka (`2C.5`) w `DialogueVerifier._guard_phase2_regressions`.

---

## SEKCJA 5: WALIDACJA TESTOWA I WARUNEK UKOŃCZENIA

### 5A — Walidacja testowa

#### 1. Infrastruktura testowa (stan bazowy po Depuracji Legacy 1.0 i wersji 9.4, commit `85ecedd`)
- **Pliki testowe jednostkowe (domyślne):** `tests/test_avt_linter.py`, `tests/test_verifier.py`, `tests/test_series_memory.py`, `tests/test_discourse_and_translator.py`, `tests/test_metadata.py`, `tests/test_profiler.py`, `tests/test_translator.py`, `tests/test_flight_recorder.py` oraz testy `KEEP` w `test_system.py` (łącznie **154 testy bazowe** w trybie `komenda_fast`, wykonywane w ~18,18 s).
- **Pliki testowe zarchiwizowane:** `tests/archive/test_legacy_manifest.py` (wykluczone przez `norecursedirs` w `pytest.ini` — pozostają nietknięte).
- **Komendy testowe:**
  - `komenda_fast` = `pytest` (uruchamia testy z `addopts = -v --tb=short -m "not slow and not network"`, czas wykonania $< 60\text{ s}$)
  - `komenda_full` = `pytest -m ""` (uruchamia wszystkie testy jednostkowe, `slow` i `network` — 307 testów bazowych + nowe testy 9.5)
  - `komenda_slow` = `pytest -m slow` (153 testy)
  - `komenda_network` = `pytest -m network` (12 testów)
- **Bramki CI/CD:** `verify_purity.py`, `verify_ultimate_pipeline.py`, `verify_12_fixes.py`, `audit_diff.ps1`.

#### 2. Wykaz nowych testów (wzorce strukturalne z placeholderami `<RZECZYWISTY_*>`)
Wszystkie nowe testy mają kategorię markera `unit` (wchodzą do domyślnego przebiegu `komenda_fast`). Placeholdery `<RZECZYWISTY_*>` agent kodujący wypełnia w Phase 0 (tabela P0.3) autentycznymi danymi z `SeriesBible` / `en_text` odcinka testowego (innego niż odcinek audytowany):

| ID testu | Punkt Sekcji 2 | Plik testowy | Nazwa testu | Kategoria markera | Kryterium akceptacji (forma pozytywna + źródło autorytetu) |
|---|---|---|---|---|---|
| **T5.1** | **2B.1 + 2C.1** | `tests/test_discourse_and_translator.py` | `test_translator_runtime_telemetry_uses_arbitrate_p0_and_bilingual_aliases` | `unit` | Prawidłowy stan ciągu `Telemetria:` w `translator.py` = 100% zgodności `MASCULINE`/`FEMININE` z `p0_gender` (w tym przez dwujęzyczny alias roli) oraz zachowanie jawnego `Name` z `[Events]` ponad tagiem $F_0$. |
| **T5.2** | **2B.2** | `tests/test_verifier.py` | `test_guard_phase2_enforces_p0_speaker_gender_on_past_tense_shift` | `unit` | Prawidłowy stan wyjścia `_guard_phase2_regressions` dla mówcy o `p0_gender: MALE` (`has_verified_gender: true`) = zachowanie formy męskiej/bezosobowej z `f1_pl` przy próbie wprowadzenia końcówki `-łam` w `refined_pl`. |
| **T5.3** | **2C.2** | `tests/test_translator.py` | `test_split_oversized_events_skips_sign_actor_and_pos_tagged_events` | `unit` | Prawidłowy stan `split_oversized_ass_events` = zachowanie zdarzenia o `Name == "sign"` lub zawierającego `\pos(x,y)` jako pojedynczego rekordu (`len(events) == 1`) z nienaruszonym blokiem tagów. |
| **T5.4** | **2C.3** | `tests/test_profiler.py` | `test_sanitize_event_asr_strips_glued_ascii_prefixes_and_enforces_episode_loop_dedup` | `unit` | Prawidłowy stan `asr_text` = wycięcie prefiksów/wtrąceń ASCII sklejonych ze znakami japońskimi oraz wyzerowanie pojedynczych znaków resztkowych i serii $> 2$ identycznych segmentów. |
| **T5.5** | **2C.4** | `tests/test_series_memory.py` | `test_validate_relation_strips_nested_bracket_clause_and_sanitizes_legacy_declensions` | `unit` | Prawidłowy stan `SeriesBible` w RAM = czyste usunięcie pełnej klauzuli `RELACJA HIERARCHICZNA (... [Imię] ... -sama]` we wpisie poufnym, regeneracja uszkodzonych paradygmatów z dysku oraz korekta ortograficzna rdzenia wołacza `W`. |
| **T5.6** | **2C.5** | `tests/test_verifier.py` | `test_guard_phase2_bridges_ellipsis_continuation_across_nominal_opening_line` | `unit` | Prawidłowy stan drugiej linii po linii zakończonej `...` tego samego mówcy = obecność inicjalnego wielokropka `...` zapewniającego ciągłość składniową. |
| **T5.7** | **2C.6** | `tests/test_translator.py` | `test_phase1_postprocess_wraps_italics_style_and_normalizes_single_italic_block` | `unit` | Prawidłowy stan `phase1_text` i `dpos_text` dla linii o stylu `Italics` = pojedyncza para `{\i1}...{\i0}` obejmująca cały tekst już na wyjściu Fazy 1, separator `\N` zamiast `\n` oraz `changes_made == None` przy braku zmian słownych w Fazie 2. |

#### 3. Warunek ukończenia wdrożenia (definicja pozytywna)
Prawidłowy stan ukończenia wdrożenia wersji **9.5** = jednoczesne spełnienie jedenastu warunków pozytywnych (a)–(k):
- **(a)** `komenda_fast` (`pytest`): 100% PASSED, `0 FAILED`, `0 ERROR`, czas wykonania $< 60\text{ s}$;
- **(b)** `komenda_full` (`pytest -m ""`): 100% PASSED, `0 FAILED`, `0 ERROR`;
- **(c)** `komenda_slow` (`pytest -m slow`): 100% PASSED;
- **(d)** `komenda_network` (`pytest -m network`): 100% PASSED;
- **(e)** pełne pokrycie testowe każdej zmiany z Sekcji 2A (przez testy istniejące), 2B (`T5.1–T5.2`) oraz 2C (`T5.1, T5.3–T5.7`);
- **(f)** Phase 0 ukończona z wypełnionymi tabelami P0.2 i P0.3 oraz rozstrzygniętymi flagami `Phase 0.D`, `Phase 0.E` i `Phase 0.F` w `Raport_wdrozenia_9.5.md`;
- **(g)** każdy nowy test `T5.1–T5.7` spełnia wszystkie pięć warunków Zasady 8 (a)–(e);
- **(h)** każdy nowy test `T5.1–T5.7` jest w 100% wolny od anty-wzorców degradacji `D1–D6` (w tym `D6.a–D6.e`);
- **(i)** żaden z testów `KEEP` z Depuracji Legacy 1.0 i wersji 9.4 nie został usunięty ani osłabiony;
- **(j)** wszystkie nowe testy jednostkowe wykonują się w przebiegu domyślnym, a ewentualne testy ciężkie posiadają `@pytest.mark.slow` / `@pytest.mark.network`;
- **(k)** katalog `tests/archive/` pozostaje nietknięty w iteracji, 3 gałęzie `# DEFENSIVE_FALLBACK` w `avt_linter.py` pozostają nietknięte z komentarzem, a wszystkie 4 bramki CI/CD (`verify_purity.py`, `verify_ultimate_pipeline.py`, `verify_12_fixes.py`, `audit_diff.ps1`) zwracają status PASS / VICTORY CONFIRMED.

### 5B — Obowiązek wypełnienia Raportu Wdrożenia (DELIVERABLE)

Po zakończeniu implementacji i uruchomieniu pełnej walidacji testowej agent kodujący ma bezwzględny obowiązek wypełnienia wszystkich pól oznaczonych placeholderami `<DO_WYPEŁNIENIA_*>` w pliku:
`C:\Users\Piotrek\Desktop\translator\Artefakty\Raport_wdrozenia_9.5.md`
i zapisania kompletnego raportu pod tą ścieżką.