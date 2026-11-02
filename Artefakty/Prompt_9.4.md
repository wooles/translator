# Plik: C:\Users\Piotrek\Desktop\translator\Artefakty\Prompt_9.4.md

# PROMPT NAPRAWCZY POTOKU AVT — WERSJA 9.4

## PREAMBUŁA

Dokument definiuje operacje kodowe, regułowe i walidacyjne rozszerzające potok AVT z wersji 9.3 (oraz respektujące stan infrastruktury po wdrożeniu Depuracji Legacy 1.0, commit `474fb64`) do wersji **9.4**. Cel operacji:
1. Domknięcie w kodzie produkcyjnym operacji z wersji 9.3, które w poprzedniej iteracji zostały wdrożone częściowo (spójność wewnętrzna i propagacja P0 do `relations`, populacja P1/P2 dla encji drugoplanowych z Kroku 3, detekcja `is_internal_monologue` w Fazie 1, strażnik `over_application_italics` oraz ochrona ciągłości zdań rozbitych i modalności 1. os. lp. w Fazie 2, integralność raportowania Kroku 11, ochrona członów dopełniaczowych w paradygmatach odmiany).
2. Wdrożenie nowych operacji wynikających z audytu empirycznego oraz zewnętrznych materiałów referencyjnych: uzgodnienie pre-passu scenicznego z rekordem P0 (`OPERACJA 2B.9`), rozszerzenie `sanitize_event_asr` o heurystykę halucynacji łacińskich i powtórzeniowych (`OPERACJA 2B.8.a`), ochrona przecinka po inicjalnym wołaczu `W` przed partykułą pytajną w `EpisodeQualityGate` (`OPERACJA 2B.10`) oraz wyeliminowanie pozornych uzasadnień `changes_made` przy braku zmiany tekstu w Fazie 2 (`OPERACJA 2B.11`).

Niniejszy dokument przestrzega czterech nadrzędnych zasad Standardu 9.0 oraz rozszerzeń Standardu 9.3/9.4:
1. **Zero-Literal** — wszystkie reguły, opisy operacji i kryteria operują wyłącznie na kategoriach językowych i metajęzykowych architektury.
2. **Pure Positive Domain Invariant** — każda reguła w Sekcji 1 i Sekcji 3 oraz każde kryterium akceptacji w Sekcji 2 i Sekcji 5 definiuje zbiór dopuszczalnych stanów docelowych w formie pozytywnej („prawidłowy stan = X", „zachowuje…", „obejmuje wyłącznie…", „ma pierwszeństwo wobec…").
3. **Primary LLM Translation Authority** — pierwotne tłumaczenie Fazy 1 (`phase1_text`) jest nadrzędnym autorytetem translacyjnym; każda zmiana w Fazie 2 lub post-processingu opiera się na twardym dowodzie z rekordu P0 (`p0_gender`, `has_verified_gender: true`) lub jednoznacznym sygnale źródłowym `en_text` / `pronouns_en`.
4. **Instance-Free Metalinguistic Architecture** — wszystkie interwencje operują na kategoriach modułów, funkcji, operatorów i struktur danych.
5. **Ochrona nienaruszalności Depuracji Legacy 1.0 (Zasada 16)** — wdrożenie wersji 9.4 zachowuje w 100% stan po Depuracji 1.0: wszystkie 116 testów `KEEP` pozostaje aktywnych w domyślnym przebiegu `pytest`, markery `@pytest.mark.slow` (153 testy) i `@pytest.mark.network` (12 testów) pozostają nienaruszone, katalog `tests/archive/` pozostaje nietknięty, a 3 chronione gałęzie `# DEFENSIVE_FALLBACK` w `avt_linter.py` (linie 7569, 7709, 11414) zachowują swoją postać i komentarze.

Numer wersji: **9.4**. Poprzednia wersja toru naprawczego: **9.3**. Wersja toru Depuracji Legacy w tle: **1.0** (commit `474fb64`).

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

Przed wprowadzeniem jakiejkolwiek zmiany w kodzie agent kodujący ma bezwzględny obowiązek wykonania Fazy 0 i udokumentowania jej wyników w sekcji `2. PHASE 0 — WYNIK WERYFIKACJI KODU` pliku `C:\Users\Piotrek\Desktop\translator\Artefakty\Raport_wdrozenia_9.4.md`.

### P0.1. Lista plików do przeczytania w całości i weryfikacji sygnatur
1. `profiler.py` — weryfikacja `EpisodeProfiler.profile_episode`, `EpisodeProfiler.sanitize_event_asr`, `_extract_f0_contour` oraz punktu emisji statystyk pre-passu scenicznego (Krok 5 / Krok 7).
2. `scene_discourse.py` — weryfikacja `SceneDiscourseGraph.build_discourse_topology` oraz `SceneDiscourseGraph.arbitrate_event_telemetry` (w szczególności propagacji `p0_gender` dla mówców zidentyfikowanych przy pustym polu `Name` w `[Events]`).
3. `series_memory.py` — weryfikacja `SeriesBible._sanitize_loaded_bible_in_ram`, `SeriesBible.sync_verified_profile_entity`, obecności `_validate_relation_entry_consistency` oraz generatora deklinacji `generate_polish_name_declension` dla wyrażeń dwuczłonowych z dopełniaczem.
4. `metadata.py` — weryfikacja funkcji normalizacji etykiet aktorów (Krok 3) i przekazywania słownika etykiet do Kroku 6.
5. `translator.py` — weryfikacja `build_phase1_prompt` (przekazywania flagi `is_internal_monologue` na podstawie stylu `Italics` / `Flashback_Italics` i tagów Kroku 4) oraz `synchronize_ass_event_metadata_and_styles`.
6. `verifier.py` — weryfikacja `DialogueVerifier.verify_batch`, obsługi pola `changes_made` oraz wszystkich kategorii strażnika `DialogueVerifier._guard_phase2_regressions`.
7. `avt_linter.py` — weryfikacja `EpisodeQualityGate.audit_and_fix_entire_episode`, `_run_phase_7_hygiene`, `normalize_ass_tags_and_sign_layout`, `get_all_fixes` oraz nienaruszalności 3 gałęzi `# DEFENSIVE_FALLBACK` (linie 7569, 7709, 11414).
8. `flight_recorder.py` — weryfikacja `EpisodeFlightRecorder.report_step_11_quality_gate`.
9. `rules.py` — weryfikacja liczby definicji filarów oraz reguł Standardu 9.x.

### P0.2. Tabela mapowania plan ↔ kod (obowiązkowa w `Raport_wdrozenia_9.4.md`)
Dla każdej operacji z Sekcji 2B i 2C wypełnij w `Raport_wdrozenia_9.4.md` wiersz tabeli:
`Operacja | Metoda/klasa w planie | Metoda/klasa w kodzie | Rzeczywista sygnatura w kodzie | Zgodność | Rozstrzygnięcie rozbieżności`.
Każdą rozbieżność „plan mówi X, kod ma Y" rozstrzygnij przed implementacją (rzeczywista sygnatura w kodzie jest autorytetem dla nazewnictwa wywołań, a plan jest autorytetem dla intencji architektonicznej).

### P0.3. Tabela mapowania danych testowych (obowiązkowa w `Raport_wdrozenia_9.4.md`)
Przed implementacją testów z Sekcji 5A wypełnij w `Raport_wdrozenia_9.4.md` tabelę mapowania wszystkich placeholderów `<RZECZYWISTY_*>` na autentyczne wartości pobrane z `SeriesBible` / `en_text` odcinka testowego (innego niż odcinek audytowany, zgodnie z Zasadą 9 i 13).

### P0.4. Weryfikacja flag Phase 0 z zewnętrznych materiałów referencyjnych (Zasada 17.d, 17.g)

#### FLAGA PHASE 0.A — Weryfikacja liczby filarów (171 vs 188)
- **Źródło:** materiał referencyjny 3 (na podstawie obserwacji z materiału referencyjnego 1). Status: wymaga weryfikacji — obserwacja wskazuje 188 filarów (`CLXXXVIII`), a `Raport_wdrozenia_Depuracja_1.0.md` raportuje 171 filarów `ACTIVE`. Rozbieżność 17.
- **Możliwe hipotezy (do rozstrzygnięcia w Phase 0):**
  - Hipoteza A: 171 to Filary AVT (`I–CLXXII`), 17 to Standard 9.x (`R1.1–R1.8` + dodatkowe reguły) — obserwacja drugiego modelu liczy sumę lub maksymalny numer rzymski.
  - Hipoteza B: Depuracja 1.0 pominęła część filarów (błąd w audycie Depuracji).
  - Hipoteza C: Obserwacja drugiego modelu liczy warianty filarów (te same filary, ale w F1 i F2 osobno).
- **Punkt weryfikacji Phase 0:**
  1. `grep -c "\[Filar "` w `rules.py` — liczba definicji filarów.
  2. `grep -c "R1\."` i `grep -c "R3\."` w `rules.py` — liczba reguł Standard 9.x.
  3. `grep -c "\[Filar "` w `translator.py` i `verifier.py` — liczba referencji do filarów w promptach F1/F2.
  4. Porównanie: liczba definicji + liczba reguł Standard 9.x vs. obserwacja z materiału referencyjnego (188) vs. `Raport_wdrozenia_Depuracja_1.0.md` (171).
- **Wynik Phase 0:** jedna liczba potwierdzona i wpisana w sekcji `2.4` pliku `Raport_wdrozenia_9.4.md`. Jeśli liczba definicji + reguł Standard 9.x > 171 — audyt filarów wobec Standardu 9.3/9.4 i klasyfikacja `OBSOLETE`/`SUPERSEDED`/`CONFLICT` zostają zarejestrowane jako kandydat do osobnego toru **Depuracji Legacy 1.1** (nie mieszamy toru 9.4 z torem Depuracji 1.1).

#### FLAGA PHASE 0.B — Attention dilution w Fazie 2 („pozorne edycje")
- **Źródło:** materiał referencyjny 3 (na podstawie obserwacji z materiału referencyjnego 1). Status: wymaga weryfikacji — obserwacja oraz log Kroku 9 wskazują, że Faza 2 generuje długie uzasadnienie `changes_made`, gdy Szkic == Szlif (lub gdy różnica sprowadza się wyłącznie do tagów formatujących `{\i1}`, `{\i0}` bądź podziału wiersza `\n`).
- **Możliwe hipotezy:**
  - Hipoteza A: F2 generuje uzasadnienia dla pozornych edycji z powodu przeciążenia prompta (attention dilution).
  - Hipoteza B: F2 ma guard, który przepuszcza identyczny tekst bez wyzerowania pola `changes_made`.
  - Hipoteza C: log konsolowy wyświetla identyczne wartości Szkic i Szlif po odfiltrowaniu tagów, podczas gdy w `refined_pl` dodano wyłącznie tagi `{\i1}`/`{\i0}` lub zmieniono znak nowej linii.
- **Punkt weryfikacji Phase 0:**
  1. Porównanie Szkic (`f1_pl`) vs. Szlif (`refined_pl`) w `DialogueVerifier.verify_batch` po odrzuceniu różnic whitespace i tagów formatujących.
  2. Sprawdzenie, czy F2 w `changes_made` zachowuje uzasadnienie dla przypadków `refined_pl == f1_pl`.
  3. Sprawdzenie, czy `DialogueVerifier.verify_batch` posiada deterministyczny warunek zerujący `changes_made = None` przy braku zmiany leksykalnej.
- **Wynik Phase 0:** potwierdzenie w sekcji `2.4` pliku `Raport_wdrozenia_9.4.md` i wdrożenie `OPERACJI 2B.11` (ustawienie `changes_made = None`, gdy `refined_pl == f1_pl` po normalizacji białych znaków).

#### FLAGA PHASE 0.C — Spójność pre-passu scenicznego z 2B.9
- **Źródło:** materiał referencyjny 3 (na podstawie obserwacji z materiału referencyjnego 1). Status: wymaga weryfikacji — obserwacja wskazuje, że pre-pass sceniczny deklaruje `131/0` (`0 żeńskich, 131 męskich`) w odcinku z dominującą obsadą kobiecą.
- **Punkt weryfikacji Phase 0:**
  1. Potwierdzić w kodzie, że pre-pass sceniczny (`EpisodeProfiler.profile_episode` lub pokrewna metoda w `profiler.py` / `scene_discourse.py`) emituje statystyki obsady bez konsultacji z rekordem P0 z `SeriesBible`.
  2. Zidentyfikować dokładną nazwę metody produkującej statystyki ciągłości obsady.
  3. Zmapować punkt w przepływie potoku (Krok 5 / Krok 7) i jego połączenie z `SceneDiscourseGraph.arbitrate_event_telemetry`.
- **Wynik Phase 0:** potwierdzenie w sekcji `2.4` pliku `Raport_wdrozenia_9.4.md`, że `OPERACJA 2B.9` (`EpisodeProfiler.reconcile_prepass_with_p0`) jest adekwatna i zmapowana na rzeczywistą metodę w kodzie.

---

## SEKCJA 1: REGUŁY DLA MODELI LLM (Faza 1 i Faza 2)

### Priorytet P0 (Reguły nienaruszalne — realizacja Primary LLM Translation Authority)

1. **R1.1 (P0):** Prawidłowy stan wypowiedzi dla mówcy o `p0_gender == "FEMALE"` w 1. os. lp. czasu przeszłego i trybu przypuszczającego = zachowanie form żeńskich; dla mówcy o `p0_gender == "MALE"` = zachowanie form męskich. Zwroty do adresata o `p0_gender == "FEMALE"` w 2. os. lp. zachowują formy żeńskie, a zwroty do grupy o `p0_gender == "FEMALE"` zachowują formy niemęskoosobowe (`NON_VIRILE`). Źródło stanu docelowego: rekord P0 (`SeriesBible` / `EpisodeProfiler`, `has_verified_gender: true`).
2. **R1.2 (P0):** Prawidłowy stan osoby i liczby orzeczenia w `phase1_text` i `phase2_text` = pełna zgodność z podmiotem w `en_text`. Podmiot 1. os. lp. w `en_text` zachowuje orzeczenie w 1. os. lp. niezależnie od liczby dopełnienia. Źródło stanu docelowego: `phase1_text` oraz jednoznaczny sygnał `en_text` / `pronouns_en`.
3. **R1.3 (P0):** Prawidłowy stan czasowników epistemicznych, wolitywnych i modalnych w 1. os. lp., form trybu przypuszczającego (`-bym`/`-łabym`/`-łbym`) oraz czasu przeszłego obecnych w `en_text` i `phase1_text` = pełne zachowanie ich kategorii modalnej i temporalnej w `refined_pl` wraz ze zdaniami podrzędnymi dopełnieniowymi identyfikującymi. Źródło stanu docelowego: `phase1_text` oraz `en_text`.
4. **R1.6 (P0):** Prawidłowy stan przekładu w `phase1_text` i `phase2_text` = bezwzględne pierwszeństwo semantyczne `en_text` oraz jawnego aktora z kolumny `Name` w `[Events]` i rekordu P0 z `SeriesBible` nad pomocniczą transkrypcją ASR i pomocniczymi tagami `telemetry`. Źródło stanu docelowego: `en_text` oraz rekord P0 (`SeriesBible`).
5. **R1.7 (P0):** Prawidłowy stan rodzaju gramatycznego 1. os. lp. czasu przeszłego (`-łem` / `-łam`) oraz trybu przypuszczającego = stuprocentowa zgodność ze zweryfikowanym `p0_gender` mówcy w `SeriesBible` / `EpisodeProfiler`. Źródło stanu docelowego: rekord P0 (`p0_gender`, `has_verified_gender: true`).
6. **R1.9 (P0):** Prawidłowy stan znaczników pochylenia w `phase1_text` i `phase2_text` = dla linii z `is_internal_monologue: true` parzyste znaczniki `{\i1}...{\i0}` obejmują cały tekst wypowiedzi; dla linii dialogowej z jawnym adresatem i `is_internal_monologue: false` tekst główny pozostaje prosty, a znaczniki `{\i1}...{\i0}` obejmują wyłącznie pojedynczy wyraz wyróżniony emfatycznie w `en_text`. Źródło stanu docelowego: `phase1_text`, atrybut `is_internal_monologue` oraz `en_text`.
7. **R1.10 (P0):** Prawidłowy stan zdań wielokrotnie złożonych rozbitych na dwa sąsiednie zdarzenia `Dialogue:` (gdzie pierwsze zdarzenie kończy się wielokropkiem `...`, a drugie w `phase1_text` rozpoczyna się wielokropkiem `...` i małą literą) = zachowanie w `refined_pl` wielokropka otwierającego, małej litery oraz pełnej ciągłości składniowej między podmiotem/dopełnieniem w pierwszym zdarzeniu a orzeczeniem w drugim zdarzeniu. Źródło stanu docelowego: `phase1_text` oraz `en_text`.

### Priorytet P1 (Reguły silne — spójność wielogłosu, wołacza i paradygmatów odmiany)

8. **R1.4 (P1):** Prawidłowy stan dwugłosu z powtórzonym wierszem z linii bezpośrednio poprzedzającej = zachowanie w `refined_pl` identycznego sformułowania w powtórzonym wierszu (niezależnie od użytego znaku dywizu lub półpauzy `-`, `–`, `—`). Źródło stanu docelowego: `phase1_text` oraz `en_text`.
9. **R1.8 (P1):** Prawidłowy stan deklinacji antroponimów i terminów kanonicznych w wołaczu `W` i przypadkach zależnych `D..Ms` = pełna zgodność z paradygmatem z `EpisodeProfiler` i `SeriesBible` oraz wydzielenie inicjalnego wołacza `W` przecinkiem od dalszej części zdania. Źródło stanu docelowego: rekord P0 (`EpisodeProfiler` / `SeriesBible`) oraz `phase1_text`.

### Priorytet P2 (Reguły jakościowe — odpowiedniość napisów `is_sign` i higiena raportowania Fazy 2)

10. **R1.5 (P2):** Prawidłowy stan krótkich napisów `is_sign: true` = ścisła odpowiedniość semantyczna i leksykalna 1:1 wobec `en_text` w poprawnej formie mianownika `M`. Źródło stanu docelowego: `en_text` oraz rekord P0 (`SeriesBible`).
11. **R1.11 (P2 — nowa):** Prawidłowy stan pola `changes_made` w odpowiedzi Fazy 2 (`DialogueVerifier`) = wartość `null` wszędzie tam, gdzie tekst merytoryczny `refined_pl` jest tożsamy z `f1_pl` (brak zmiany leksykalno-składniowej), oraz zwięzły opis rzeczywistej modyfikacji wyłącznie dla linii, w których `refined_pl` różni się leksykalnie lub składniowo od `f1_pl`. Źródło stanu docelowego: porównanie `f1_pl` i `refined_pl`.

---

## SEKCJA 2: OPERACJE (2A / 2B / 2C)

### 2A — Operacje potwierdzone z poprzedniego promptu (bez nowych akcji)

1. **`2A.1` (z 9.3/2A.1 i 9.3/2C.6) — `DialogueVerifier.enforce_sign_nominative_orthography` (`verifier.py`):**
   - **Status w audytowanym odcinku:** potwierdzony (0 naruszeń ortografii mianownika `M` i 100% odpowiedniości 1:1 na planszach `is_sign`).
   - **Nowa akcja w 9.4:** brak (decyzja 9.3 obowiązuje).
2. **`2A.2` (z 9.3/2A.3) — `SeriesBible._sanitize_loaded_bible_in_ram` w warstwie `gender` i `grammatical_gender` słownika `characters` (`series_memory.py`):**
   - **Status w audytowanym odcinku:** potwierdzony (wszystkie 23 encje w `characters` posiadają poprawne pola `gender: MALE/FEMALE` i `grammatical_gender: MASCULINE/FEMININE` zgodne z P0).
   - **Nowa akcja w 9.4:** brak w warstwie pól `gender`/`grammatical_gender` (oczyszczenie pola `description` i propagacja do `relations` ujęte w Sekcji 2C.5).
3. **`2A.3` (z 9.3/2C.3) — `EpisodeQualityGate.should_apply_top_alignment_on_collision` (`avt_linter.py`):**
   - **Status w audytowanym odcinku:** potwierdzony (0 fałszywych podniesień `\an8` na liniach ze stylem `Main - Top` w `ID: 55–56` i `ID: 196–197`).
   - **Nowa akcja w 9.4:** brak (decyzja 9.3 obowiązuje).
4. **`2A.4` (z 9.3/2B.7) — Dopasowanie pełnotokenowe w normalizacji etykiet aktorów (`metadata.py`):**
   - **Status w audytowanym odcinku:** potwierdzony (0 fałszywych dopasowań podciągowych `extracted_gender` w Kroku 3).
   - **Nowa akcja w 9.4:** brak (decyzja 9.3 obowiązuje).
5. **`2A.5` (z 9.3/2B.1) — `EpisodeQualityGate.preserve_italics_for_upright_style` (`avt_linter.py`, `translator.py`):**
   - **Status w audytowanym odcinku:** potwierdzony (znaczniki `{\i1}...{\i0}` na stylach o `Italic == 0` są zachowywane, a na stylu `Italics` o `Italic == -1` prawidłowo redukowane jako redundantne).
   - **Nowa akcja w 9.4:** brak (decyzja 9.3 obowiązuje).

---

### 2B — Nowe operacje (z materiałów referencyjnych oraz audytu 9.4)

#### OPERACJA 2B.9 — Pre-pass sceniczny z arbitrażem P0 (KRYTYCZNY)
- **Źródło:** materiał referencyjny 2 (potwierdzony empirycznie w `BŁĄD 1` audytowanego odcinka: pre-pass sceniczny zadeklarował `0 żeńskich, 131 męskich` mimo obecności głównych postaci kobiecych; wymaga Phase 0.C dla potwierdzenia dokładnej nazwy metody w kodzie).
- **Kategoria problemu:** pre-pass sceniczny (`EpisodeProfiler.profile_episode` lub pokrewna metoda budująca statystyki obsady per scena) produkuje fałszywe dane wejściowe do `SceneDiscourseGraph.arbitrate_event_telemetry` — nawet gdy arbitraż próbuje korzystać z kontekstu sceny, otrzymuje skażone statystyki z góry.
- **Punkt krytyczny w potoku:** Krok 5 / Krok 7 (pre-pass sceniczny), interakcja z `EpisodeProfiler`, `SeriesBible` i `SceneDiscourseGraph`.
- **Natura modułu:** deterministyczny z kontekstem.
- **Rozstrzygnięcie:** **NAPRAWIĆ**. Moduł `EpisodeProfiler` jest prawidłowy (estymacja $F_0$ ma sens dla postaci spoza P0), ale otrzymuje niewystarczający kontekst — nie konsultuje się z rekordem P0 z `SeriesBible`.
- **Wymóg Phase 0 (Flaga Phase 0.C):** potwierdzić w kodzie, że pre-pass sceniczny emituje statystyki obsady bez konsultacji z P0; zidentyfikować metodę produkującą statystyki; zmapować punkt w przepływie.
- **Implementacja:**
  1. Utworzyć / wyodrębnić metodę `EpisodeProfiler.reconcile_prepass_with_p0` (lub zintegrować bezpośrednio z metodą wyliczającą statystyki pre-passu scenicznego zidentyfikowaną w Phase 0).
  2. Dla każdej postaci obecnej w scenie (zarówno po jawnym polu `Name` z `[Events]`, jak i po przypisaniu z `EpisodeProfiler` / `SceneDiscourseGraph`) pre-pass pobiera `p0_gender` z `SeriesBible`.
  3. Priorytet bezwzględny: `p0_gender` z `SeriesBible` (`priority: P0`, `has_verified_gender: true`) ma pierwszeństwo wobec estymacji akustycznej $F_0$ z Kroku 4.
  4. Estymacja $F_0$ służy wyłącznie jako fallback dla postaci spoza P0 (`has_verified_gender: false` lub `UNKNOWN`).
  5. Wynik: statystyki obsady per scena oraz licznik ciągłości obsady odcinka są w 100% zgodne z `p0_gender` dla wszystkich postaci P0.
- **Kryterium akceptacji:** Prawidłowy stan pre-passu scenicznego dla każdej sceny zawierającej co najmniej jedną postać P0 (`MALE` lub `FEMALE`) = emisja statystyk obsady w 100% spójnych z `p0_gender` (0% rozbieżności między statystyką pre-passu a `p0_gender` dla postaci P0; źródło autorytetu: rekord P0 w `SeriesBible`).
- **Uwaga bezpieczeństwa:** Operacja `2B.9` działa komplementarnie z `2C.1` (`SceneDiscourseGraph.arbitrate_event_telemetry`): `2B.9` oczyszcza statystyki na poziomie sceny, a `2C.1` wymusza `p0_gender` na poziomie pojedynczej linii `Dialogue:`.

#### OPERACJA 2B.8.a — Rozszerzenie `sanitize_event_asr` o heurystykę halucynacji (KRYTYCZNY)
- **Źródło:** materiał referencyjny 2 (potwierdzony empirycznie w `BŁĄD 8` audytowanego odcinka: silnik Whisper generuje angielskie/łacińskie słowa i powtórzenia sylab w segmentach ciszy, muzyki lub efektów dźwiękowych w `ID: 24, 79, 83, 170, 181–182, 190, 200`).
- **Kategoria problemu:** halucynacje ASR — silnik rozpoznawania mowy generuje tokeny nieobecne w japońskim audio (łacińskie słowa ASCII lub ciągi powtórzeniowe typu `sss`, `aaasss`) w segmentach zakłóceń akustycznych. Kategoria odrębna od duplikacji międzyujęciowej (`2C.10`).
- **Punkt krytyczny w potoku:** Krok 4, `EpisodeProfiler.sanitize_event_asr` (`profiler.py`).
- **Natura modułu:** higieniczny / deterministyczny z kontekstem.
- **Rozstrzygnięcie:** **NAPRAWIĆ** (rozszerzenie metody `sanitize_event_asr` o filtr halucynacji).
- **Wymóg Phase 0:** potwierdzić w kodzie sygnaturę `EpisodeProfiler.sanitize_event_asr` oraz dostępność surowego tekstu japońskiego przed latynizacją romaji.
- **Implementacja:**
  1. Rozszerzyć `EpisodeProfiler.sanitize_event_asr` o trójstopniową heurystykę halucynacji wykonywaną na surowym segmencie transkrypcji japońskiej (przed dopisaniem transkrypcji romaji w nawiasach kwadratowych):
     - **(a) Detekcja łacińskich tokenów w japońskim audio:** jeśli surowy japoński segment ASR zawiera słowa złożone ze znaków ASCII łacińskich (`[a-zA-Z]{2,}`), wytnij tokeny łacińskie lub — jeśli stanowią cały segment — oznacz segment jako halucynację i wyzeruj (`""`).
     - **(b) Detekcja powtórzeń znakowych i tokenowych:** jeśli segment ASR zawiera powtórzenia tego samego znaku łacińskiego lub tokenu ($>2$ razy z rzędu w segmencie $\le 1\text{ s}$ lub pojedyncze izolowane znaki `.` / `k` / `n`), wyчиść artefakt lub oznacz segment jako halucynację.
     - **(c) Prymat nadrzędny `en_text`:** dla każdego segmentu oznaczonego jako halucynacja wyzeruj `asr_text` (`""`), zachowując `en_text` jako jedyny autorytet semantyczny (Zasada 3 Standardu 9.0).
  2. Dla segmentów prawidłowych (złożonych z pisma japońskiego Kana/Kanji bez artefaktów halucynacyjnych): zachowaj `asr_text` bez zmian.
- **Kryterium akceptacji:** Prawidłowy stan `asr_text` po wykonaniu `EpisodeProfiler.sanitize_event_asr` = całkowita wolność japońskiego tekstu transkrypcji od halucynowanych słów łacińskich ASCII i ciągów powtórzeniowych $>2$, przy zachowaniu `en_text` jako nadrzędnego autorytetu (źródło autorytetu: Zasada 3 Standardu 9.0 oraz `en_text`).

#### OPERACJA 2B.10 — Ochrona przecinka po inicjalnym wołaczu `W` przed partykułą pytajną w `EpisodeQualityGate`
- **Źródło:** audyt empiryczny odcinka (`WYKRYTY BŁĄD 5`, `ID: 158`).
- **Lokalizacja:** `avt_linter.py` → `EpisodeQualityGate.audit_and_fix_entire_episode` / `_run_phase_7_hygiene` (operator `[Episode Quality Gate - Higiena Tekstu]` / `[Higiena Interpunkcji]`).
- **Natura modułu:** higieniczny / deterministyczny bez kontekstu.
- **Rozstrzygnięcie:** **NAPRAWIĆ** (zawężenie reguły interpunkcyjnej usuwającej przecinek przed partykułą pytajną `czy`).
- **Uzasadnienie systemowe:** Reguła higieny interpunkcyjnej usuwająca przecinek przed partykułą `czy` w zdaniach pojedynczych nie uwzględnia sytuacji, w której człon poprzedzający `, czy` jest inicjalnym wołaczem `W` (pojedynczym antroponimem lub zwrotem adresatywnym otwierającym wypowiedź), przez co usuwa poprawny przecinek wstawiony zgodnie przez Fazę 1 i Fazę 2 w `dpos_text`.
- **Implementacja:**
  1. W operatorze higieny interpunkcyjnej w `EpisodeQualityGate` zachowuj przecinek przed wyrazem `czy` wszędzie tam, gdzie:
     - przecinek był obecny w `dpos_text` (`phase1_text` / `phase2_text`), ORAZ
     - człon przed przecinkiem znajduje się na początku zdania (lub po myślniku dialogowym) i składa się z 1–2 wyrazów rozpoczynających się wielką literą (inicjalny wołacz `W` / antroponim ze słownika `declensions` lub `characters`).
- **Kryterium akceptacji:** Prawidłowy stan `ass_text` dla każdego zdania rozpoczynającego się od wołacza `W` wydzielonego przecinkiem w `dpos_text` (w tym przed partykułą `czy`) = stuprocentowe zachowanie przecinka po wołaczu zgodnie z `dpos_text` i `phase1_text` (źródło autorytetu: `phase1_text` oraz paradygmat `W` w `SeriesBible`).

#### OPERACJA 2B.11 — Eliminacja pozornych uzasadnień `changes_made` w Fazie 2 przy braku zmiany tekstu
- **Źródło:** materiał referencyjny 1 i 3 (`FLAGA PHASE 0.B`) oraz audyt empiryczny odcinka (`WYKRYTY BŁĄD 8`, Krok 9).
- **Lokalizacja:** `verifier.py` → `DialogueVerifier.verify_batch`.
- **Natura modułu:** deterministyczny z kontekstem (normalizacja wyjścia Fazy 2).
- **Rozstrzygnięcie:** **NAPRAWIĆ**.
- **Uzasadnienie systemowe:** Model Fazy 2 generuje wpisy w polu `changes_made` również dla linii, w których `refined_pl` po odfiltrowaniu różnic białych znaków (`\n` vs spacja) i tagów formatujących jest identyczny z `f1_pl`, co zaciemnia diagnostykę w logu i zużywa tokeny wyjściowe.
- **Implementacja:**
  1. W `DialogueVerifier.verify_batch` po odebraniu odpowiedzi modelu i po wykonaniu `_guard_phase2_regressions` porównaj znormalizowany tekst `f1_pl` (po usunięciu tagów `{\...}` i zamianie `\n`/`\N` na pojedynczą spację) ze znormalizowanym tekstem `refined_pl`.
  2. Jeśli znormalizowany tekst słowny `refined_pl` jest identyczny z `f1_pl` ORAZ nie nastąpiła zmiana znaczników `{\i1}...{\i0}`, ustaw deterministycznie `item["changes_made"] = None` (i nie wypisuj pozornego wpisu `[Redaktor Dialogów]` w konsoli).
- **Kryterium akceptacji:** Prawidłowy stan pola `changes_made` po wykonaniu `DialogueVerifier.verify_batch` = wartość `None` dla każdej linii, w której `refined_pl` i `f1_pl` są tożsame leksykalnie i znacznikowo, oraz niepuste uzasadnienie wyłącznie przy rzeczywistej zmianie tekstu lub tagów (źródło autorytetu: porównanie `phase1_text` i `phase2_text`).

---

### 2C — Konflikty z poprzednim promptem 9.3 (rozstrzygnięte: dowód empiryczny > analiza teoretyczna)

#### 2C.1 (z 9.3/2C.1) — `SceneDiscourseGraph.arbitrate_event_telemetry` — bezwzględny prymat `p0_gender` dla każdego zidentyfikowanego mówcy i adresata
- **Konflikt z 9.3:** W audytowanym odcinku (`WYKRYTY BŁĄD 1`) mimo obecności zweryfikowanych wpisów `p0_gender: MALE` (`has_verified_gender: true`) w Kroku 6 dla wszystkich głównych postaci męskich, w Kroku 10 wektor `telemetry` wyemitował dla nich `[Mówca: <Antroponim> (FEMININE)]` w ponad 130 liniach.
- **Rozstrzygnięcie (dowód empiryczny > analiza teoretyczna):** **ROZSZERZYĆ** implementację `SceneDiscourseGraph.arbitrate_event_telemetry` oraz `build_discourse_topology` (`scene_discourse.py`).
- **Implementacja:**
  1. Niezależnie od tego, czy `speaker_name` pochodzi bezpośrednio z kolumny `Name` w `[Events]`, czy został przypisany przez `build_discourse_topology` (dla linii z pustym `Name` w `[Events]`), przed sformatowaniem ciągu `telemetry` wykonaj bezwarunkowy odczyt `SeriesBible.get_character(speaker_name)`.
  2. Jeśli postać istnieje w `SeriesBible` (lub w profilu odcinka `EpisodeProfiler`) i posiada `gender == "MALE"` (`has_verified_gender: true` lub `priority in ("P0", "P1")`), wymuś w `telemetry` wartość `MASCULINE` (całkowicie ignorując estymację $F_0$ z Kroku 4 oraz domyślną płeć sceny). Symetrycznie dla `gender == "FEMALE"` wymuś `FEMININE`.
  3. Analogiczny bezwarunkowy odczyt `p0_gender` wykonaj dla wyznaczonego adresata (`addressee`): jeśli adresatem w scenie dialogowej jest postać o `p0_gender == "MALE"`, wymuś `Adresat: MASCULINE`; jeśli `p0_gender == "FEMALE"`, wymuś `Adresat: FEMININE`.
  4. Dla zdarzeń oznaczonych jako `is_sign: true` (lub posiadających w polu `Name` etykietę techniczną `sign`, `txt`, `title`) nie przypisuj płci osobowej mówcy (`Mówca: sign (NEUTRAL)` lub pomiń blok `Mówca:`).
- **Kryterium akceptacji:** Prawidłowy stan wektora `telemetry` w Kroku 10 dla każdej linii, w której `speaker_name` lub `addressee` wskazuje na encję o zweryfikowanym `p0_gender` w `SeriesBible` / `EpisodeProfiler` = stuprocentowa zgodność znacznika `MASCULINE` / `FEMININE` z `p0_gender` tej encji (0 przypadków `[Mówca: <Encja_MALE> (FEMININE)]`; źródło autorytetu: rekord P0 w `SeriesBible`).

#### 2C.2 (z 9.3/2C.2) — `DialogueVerifier._guard_phase2_regressions` — domknięcie ochrony modalności 1. os. lp., czasu przeszłego oraz ciągłości zdań rozbitych wielokropkiem
- **Konflikt z 9.3:** Zgodnie z `Raport_wdrozenia_9.3.md` (sekcja 12.3) oraz audytem odcinka (`WYKRYTY BŁĄD 3` w `ID: 84–85` i `WYKRYTY BŁĄD 6` w `ID: 190, 218`), strażnik Fazy 2 przepuścił: (a) usunięcie wielokropka otwierającego `...` i zmianę małej litery na wielką w drugim segmencie zdania rozbitego (`ID: 85`), co pozostawiło pierwszy segment (`ID: 84`) bez orzeczenia, (b) zamianę trybu przypuszczającego 1. os. lp. (`-bym`) na tryb oznajmujący czasu teraźniejszego (`ID: 190`) oraz (c) zamianę czasu przeszłego z `phase1_text` i `en_text` na czas teraźniejszy (`ID: 218`).
- **Rozstrzygnięcie:** **ROZSZERZYĆ** `DialogueVerifier._guard_phase2_regressions` (`verifier.py`) o pełną implementację kategorii z 9.3 oraz kategorię ciągłości zdań rozbitych.
- **Implementacja:**
  1. **Kategoria `ellipsis_continuation_syntax` (nowa — adresuje BŁĄD 3):** jeśli `prev_line_pl` kończy się wielokropkiem (`...`), a `f1_pl` (po pominięciu tagów `{\...}`) rozpoczyna się wielokropkiem i małą literą (`^\.\.\.\s*[a-ząćęłńóśźż]`), natomiast `refined_pl` usuwa inicjalny wielokropek i rozpoczyna zdanie wielką literą — przywróć `f1_pl` (z zachowaniem parzystych tagów `{\i1}...{\i0}` jeśli linia jest monologiem wewnętrznym).
  2. **Kategoria `first_person_modal_and_conditional_loss` (domknięcie 9.3/2C.2 — adresuje BŁĄD 6 `ID: 190`):** jeśli `f1_pl` zawiera formę 1. os. lp. trybu przypuszczającego (zakończoną na `-bym`, `-łbym`, `-łabym`) lub czasownik modalny/wolitywny 1. os. lp., a `refined_pl` zastępuje ją formą trybu oznajmującego bez `-bym` (lub usuwa czasownik modalny 1. os. lp.) — przywróć `f1_pl`.
  3. **Kategoria `past_to_present_tense_shift` (domknięcie 9.3/2C.2 — adresuje BŁĄD 6 `ID: 218`):** jeśli `source_en` oraz `f1_pl` używają czasu przeszłego (formy na `-łem`, `-łam`, `-ł`, `-ła`, `-ło`, `-li`, `-ły`), a `refined_pl` zamienia główne orzeczenie na czas teraźniejszy — przywróć `f1_pl` (z zachowaniem tagów `{\i1}...{\i0}` dla monologu wewnętrznego).
  4. Zachowaj wszystkie dotychczasowe kategorie strażnika (`dual_voice_sync` dla `-`/`–`/`—`, `italic_balance`, `subordinate_clause_loss` oraz 16 kategorii z 9.2).
- **Kryterium akceptacji:** Prawidłowy stan wyjścia `_guard_phase2_regressions` = pełne zachowanie `f1_pl` w przypadku naruszenia ciągłości wielokropka i małej litery po linii zakończonej `...`, utraty trybu przypuszczającego/modalności 1. os. lp. lub zmiany czasu przeszłego na teraźniejszy wbrew `en_text` (źródło autorytetu: `phase1_text` oraz `en_text`).

#### 2C.4 (z 9.3/2C.4) — `EpisodeQualityGate._run_phase_7_hygiene` — sanitacja nieznanych pseudotagów w blokach `{\...}` oraz spójność plansz tytułowych
- **Konflikt z 9.3:** W audytowanym odcinku (`WYKRYTY BŁĄD 2` w `ID: 47` oraz `WYKRYTY BŁĄD 7` w `ID: 238`) w bloku tagów `{\...}` w `ID: 238` pozostał nieprawidłowy składniowo pseudotag szablonowy ze spacjami (`\BLUE TEXT HEADER`), a w `ID: 47` nastąpiła niezaraportowana zamiana dwukropka z `dpos_text` na `\N` w `ass_text` oraz pozostawiono tag `\i0` na stylu o `Italic == 0`.
- **Rozstrzygnięcie:** **ROZSZERZYĆ** `EpisodeQualityGate._run_phase_7_hygiene` / `normalize_ass_tags_and_sign_layout` (`avt_linter.py`).
- **Implementacja:**
  1. W `normalize_ass_tags_and_sign_layout` podczas parsowania i scalania bloków `{\...}` odfiltrowuj (usuwaj) wszystkie nieznane pseudotagi zawierające spacje lub wielkie litery spoza specyfikacji ASS v4.00+ (akceptowalna biała lista prefiksów tagów ASS: `\an`, `\a`, `\pos`, `\move`, `\org`, `\fad`, `\fade`, `\clip`, `\iclip`, `\b`, `\i`, `\u`, `\s`, `\bord`, `\xbord`, `\ybord`, `\shad`, `\xshad`, `\yshad`, `\be`, `\blur`, `\fn`, `\fs`, `\fscx`, `\fscy`, `\fsp`, `\frx`, `\fry`, `\frz`, `\fr`, `\fax`, `\fay`, `\fe`, `\c`, `\1c`, `\2c`, `\3c`, `\4c`, `\alpha`, `\1a`, `\2a`, `\3a`, `\4a`, `\k`, `\K`, `\kf`, `\ko`, `\q`, `\r`, `\t`, `\p`, `\pbo`). Każdy token typu `\BLUE TEXT HEADER` niebędący argumentem `\fn` zostaje usunięty z bloku `{\...}`.
  2. Jeśli w `en_text` napisu tytułowego występują twarde spacje separujące numer odcinka od tytułu (`\h\h...`), zachowuj podział dwuwierszowy `\N` spójnie już w `dpos_text` i `ass_text` (lub zachowuj dwukropek z `dpos_text`, jeżeli napis jest jednowierszowy).
- **Kryterium akceptacji:** Prawidłowy stan bloków `{\...}` w `ass_text` = obecność wyłącznie poprawnych składniowo tagów specyfikacji ASS v4.00+ (0 nieznanych pseudotagów szablonowych) oraz spójność strukturalna napisów tytułowych między `dpos_text` a `ass_text` (źródło autorytetu: specyfikacja formatu `[Events]` ASS v4.00+ oraz `dpos_text`).

#### 2C.5 (z 9.3/2C.5 i 9.3/2B.3) — `SeriesBible._sanitize_loaded_bible_in_ram` i `_validate_relation_entry_consistency` — pełna sanitacja `description` i `relations`
- **Konflikt z 9.3:** W audytowanym odcinku (`WYKRYTY BŁĄD 1`, Krok 6) w `SeriesBible` postacie o `gender: FEMALE` posiadały w polu `description` pozostałość tekstową `"MĘŻCZYZNA (wyodrębniono z relacji serii)"`, w 3 relacjach skierowanych do kobiet widniał blok `[MĘŻCZYZNA (Adresat) - ... wymóg form męskich]`, a ostatnia relacja zawierała jednocześnie zwrot imienny i klauzulę `RELACJA HIERARCHICZNA: stały zwrot formalny 'Pan / Panie [Imię]'` (metoda `_validate_relation_entry_consistency` z 9.3/2B.3 nie została wdrożona wg `Raport_wdrozenia_9.3.md` sekcja 12.3).
- **Rozstrzygnięcie:** **ROZSZERZYĆ** i domknąć wdrożenie `SeriesBible._sanitize_loaded_bible_in_ram` oraz `_validate_relation_entry_consistency` (`series_memory.py`).
- **Implementacja:**
  1. W `_sanitize_loaded_bible_in_ram` dla każdego wpisu w `self.data["characters"]`: jeśli `gender == "FEMALE"`, a pole `description` zawiera słowo `"MĘŻCZYZNA"` lub `"mężczyzna"`, zastąp je w pamięci RAM słowem `"KOBIETA"` / `"kobieta"` (i symetrycznie dla `gender == "MALE"` zastąp `"KOBIETA"` / `"kobieta"` słowem `"MĘŻCZYZNA"` / `"mężczyzna"`).
  2. Dla każdego klucza `A -> B` w `self.data["relations"]` wyodrębnij nazwę adresata `B`, pobierz jego zweryfikowany `p0_gender` z `self.data["characters"]` (oraz z `EpisodeProfiler`) i bezwarunkowo zaktualizuj cały blok nawiasowy rodzaju adresata:
     - dla `p0_gender == "FEMALE"`: ustaw `[KOBIETA (Adresat) - W 2. os. lp. 'ty' wymóg form żeńskich: byłaś / zrobiłaś / jesteś pewna]`;
     - dla `p0_gender == "MALE"`: ustaw `[MĘŻCZYZNA (Adresat) - W 2. os. lp. 'ty' wymóg form męskich: byłeś / zrobiłeś / jesteś pewien]`.
  3. Zaimplementuj metodę `_validate_relation_entry_consistency` wywoływaną na końcu `_sanitize_loaded_bible_in_ram`: jeśli wpis relacji `A -> B` definiuje w sekcji `Zwrot:` formę poufną (samo imię lub `'ty'`), a jednocześnie zawiera doklejoną klauzulę `RELACJA HIERARCHICZNA (T-V Invariance): stały zwrot formalny 'Pan / Panie [Imię]'`, usuń sprzeczną klauzulę `RELACJA HIERARCHICZNA` z tego wpisu i oznacz wpis jawnym atrybutem `reżim: POUFNY` (natomiast dla wpisów zawierających w `Zwrot:` tytuł formalny `pan/pani/proszę pana/naczelniku/baronie/mędrcu` oznacz `reżim: FORMALNY`).
- **Kryterium akceptacji:** Prawidłowy stan `SeriesBible` w RAM w Kroku 6 = 100% zgodności pola `description` z `gender` w `characters`, 100% zgodności bloków `[KOBIETA/MĘŻCZYZNA (Adresat)]` w `relations` z `p0_gender` adresata `B` oraz brak wewnętrznie sprzecznych wpisów łączących zwrot imienny z klauzulą `Pan / Panie` (źródło autorytetu: rekord P0 w `SeriesBible` / `EpisodeProfiler`).

#### 2C.6 (z 9.3/2B.1 i 9.3/2B.2) — Detekcja `is_internal_monologue` w Fazie 1 oraz strażnik `over_application_italics` w Fazie 2
- **Konflikt z 9.3:** Zgodnie z `Raport_wdrozenia_9.3.md` (sekcja 12.3) oraz `WYKRYTY BŁĄD 4`, Faza 1 nie otrzymała flagi `is_internal_monologue: true` dla 29 linii o stylu `Italics` w `[Events]`, a Faza 2 w `ID: 187` rozszerzyła kursywę z pojedynczego zaimka w `en_text` na całą linię dialogu głośnego z jawnym adresatem (brak strażnika `over_application_italics` z 9.3/2B.2).
- **Rozstrzygnięcie:** **ROZSZERZYĆ** i domknąć wdrożenie `2B.1` (`translator.py`) oraz `2B.2` (`verifier.py`).
- **Implementacja:**
  1. W `translator.py` (`build_phase1_prompt` oraz post-processing Fazy 1): wyliczaj dla każdej linii flagę `is_internal_monologue: bool`, która przyjmuje wartość `True`, gdy: (a) styl linii w `[Events]` ma nazwę `Italics`, `Italics - Top`, `Flashback_Italics` lub posiada `Italic in (1, -1)` w `[V4+ Styles]`, LUB (b) linia posiada w Kroku 4 tag `"cichy szept / monolog wewnętrzny"` przy braku bezpośredniego adresata dialogowego. Dla każdej linii z `is_internal_monologue: true` zapewnij obecność parzystych znaczników `{\i1}...{\i0}` już w `phase1_text` (a przy zapisie do `.ass` na stylu `Italics` o `Italic == -1` usuń zewnętrzne `{\i1}...{\i0}`, natomiast na stylu `Default` o `Italic == 0` — jeśli cała sekwencja sąsiednich myśli tego samego mówcy ma styl `Italics` jak w `ID: 145–148` — ujednolić styl linii `ID: 144` do `Italics` lub zachować spójne formatowanie).
  2. W `DialogueVerifier._guard_phase2_regressions` (`verifier.py`) dodaj kategorię `over_application_italics`:
     - jeśli `is_internal_monologue` jest `False` (styl `Default` o `Italic == 0`, głośny dialog z adresatem w scenie), `f1_pl` nie jest otoczone w całości `{\i1}...{\i0}`, a `refined_pl` otacza całą linię znacznikami `{\i1}...{\i0}` (mimo że `source_en` nie jest w całości pochylone lub pochyla wyłącznie pojedynczy wyraz emfatyczny) — usuń całoliniowe znaczniki `{\i1}...{\i0}` z `refined_pl` (lub przywróć `f1_pl`).
- **Kryterium akceptacji:** Prawidłowy stan znaczników kursywy w `phase1_text`, `phase2_text` i `ass_text` = obecność `{\i1}...{\i0}` w `phase1_text` dla wszystkich linii z `is_internal_monologue: true` oraz brak całoliniowych znaczników `{\i1}...{\i0}` na głośnych liniach dialogowych ze stylem `Default` i jawnym adresatem (źródło autorytetu: sekcja `[Events]` / `[V4+ Styles]`, `phase1_text` oraz `en_text`).

#### 2C.7 (z 9.3/2B.4) — Populacja P1/P2 dla encji drugoplanowych z Kroku 3 (`metadata.py` + `series_memory.py`)
- **Konflikt z 9.3:** Zgodnie z `Raport_wdrozenia_9.3.md` (sekcja 12.3) oraz `WYKRYTY BŁĄD 1` (Krok 3 vs Krok 6), 7 etykiet aktorów drugoplanowych obecnych w `Normalizacja etykiet aktorów` (Krok 3) nie zostało zarejestrowanych w `SeriesBible.data["characters"]` w Kroku 6.
- **Rozstrzygnięcie:** **NAPRAWIĆ** (wdrożyć w pełni operację 2B.4 z `Prompt_9.3.md` w `metadata.py` i `series_memory.py`).
- **Implementacja:**
  1. W `SeriesBible.sync_verified_profile_entity` (lub metodzie synchronizującej Krok 3 z Krokiem 6) wykonaj iterację po wszystkich kluczach `clean_name` ze słownika `Normalizacja etykiet aktorów` (z wyłączeniem etykiet czysto technicznych `sign`, `txt`, `title`).
  2. Dla każdej encji nieobecnej jeszcze w `self.data["characters"]` utwórz wpis w pamięci RAM z priorytetem źródeł:
     - (a) jeśli nazwa etykiety jest jednoznacznym rzeczownikiem płciowym w języku źródłowym (np. oznacza chłopca/mężczyznę → `gender: "MALE"`, `priority: "P1"`, `confidence: 0.85`; oznacza dziewczynę/kobietę → `gender: "FEMALE"`, `priority: "P1"`, `confidence: 0.85`), przypisz odpowiednią płeć `P1`;
     - (b) dla pozostałych etykiet zbiorczych/numerowanych bez zweryfikowanej płci w `EpisodeProfiler` przypisz `gender: "UNKNOWN"`, `grammatical_gender: "UNKNOWN"`, `priority: "P2"`, `confidence: 0.50`, `has_verified_gender: false`.
- **Kryterium akceptacji:** Prawidłowy stan `SeriesBible.data["characters"]` w Kroku 6 = każda etykieta osobowa z `Normalizacja etykiet aktorów` (Krok 3) posiada wpis w `characters` z jawnym `gender` (`MALE` / `FEMALE` / `UNKNOWN`) i `priority` (`P0` / `P1` / `P2`; źródło autorytetu: Krok 3 i Krok 5).

#### 2C.8 (z 9.3/2B.5) — Integralność raportu Kroku 11 (`flight_recorder.py` + `avt_linter.py`)
- **Konflikt z 9.3:** Zgodnie z `Raport_wdrozenia_9.3.md` (sekcja 12.3) oraz `WYKRYTY BŁĄD 8` (Krok 11), rejestrator lotu zadeklarował `Łączna liczba poprawek bramki jakości: 81`, lecz wypisał tylko 15 wybranych pozycji bez pola `consistency_check`.
- **Rozstrzygnięcie:** **NAPRAWIĆ** (wdrożyć w pełni operację 2B.5 z `Prompt_9.3.md` w `avt_linter.py` i `flight_recorder.py`).
- **Implementacja:**
  1. W `EpisodeQualityGate` udostępnij metodę `get_all_fixes()` zwracającą kompletną listę wszystkich zaaplikowanych poprawek z unikalnym `fix_id`.
  2. W `EpisodeFlightRecorder.report_step_11_quality_gate` (`flight_recorder.py`) wypisuj wszystkie pozycje z `get_all_fixes()` (zdejmując limit przycinający listę do 15 wpisów) oraz dodaj podsumowanie `consistency_check: {"reported": N, "collected": M, "status": "OK" if N == M else "MISMATCH"}`.
- **Kryterium akceptacji:** Prawidłowy stan raportu Kroku 11 w pliku `*_full_trace.log` = `consistency_check.status == "OK"`, gdzie liczba wylistowanych pozycji `M` jest w 100% równa łącznej liczbie poprawek `N` (źródło autorytetu: rejestr `EpisodeQualityGate.get_all_fixes()`).

#### 2C.9 (z 9.3/2B.6) — Ochrona członu dopełniaczowego w paradygmatach odmiany wyrażeń dwuczłonowych (`series_memory.py`)
- **Konflikt z 9.3:** W audytowanym odcinku (`WYKRYTY BŁĄD 7`, Krok 6 `Paradygmaty odmiany`) dla dwuczłonowych terminów kanonicznych o strukturze `[Rzeczownik nadrzędny w M] + [Rzeczownik podrzędny w D]` (gdzie drugi człon kończy się w dopełniaczu na `-a` lub `-i`/`-y`) generator deklinacji potraktował drugi człon jak przymiotnik/rzeczownik rodzaju żeńskiego w mianowniku i nadał mu błędne końcówki fleksyjne w przypadkach `D..W`, a dla części jednoczłonowych antroponimów z Kroku 5 pozostawił w Kroku 6 zamrożony mianownik.
- **Rozstrzygnięcie:** **ROZSZERZYĆ** `generate_polish_name_declension` oraz `SeriesBible.sync_verified_profile_entity` (`series_memory.py`).
- **Implementacja:**
  1. W `SeriesBible.sync_verified_profile_entity`: dla każdej encji (zarówno jedno-, jak i wieloczłonowej), dla której `EpisodeProfiler` (Krok 5) dostarczył pełny paradygmat 7 przypadków `M, D, C, B, N, Ms, W` różniący się od zamrożonego mianownika, bezwarunkowo nadpisz `self.data["declensions"][name]` paradygmatem z Kroku 5.
  2. W generatorze deklinacji wyrażeń dwuczłonowych (`[Człon_1] [Człon_2]`) dla pospolitych terminów kanonicznych (niebędących imieniem i nazwiskiem osoby `ANTHROPONYM`): jeśli `Człon_1` jest rzeczownikiem (np. zakończonym na `-e`, `-a`, `-ń`), a `Człon_2` jest rzeczownikiem w dopełniaczu (związek rządu, a nie związek zgody przymiotnika z rzeczownikiem), w przypadkach zależnych `D..W` odmieniaj wyłącznie `Człon_1`, zachowując `Człon_2` w niezmienionej formie dopełniacza z `M`.
- **Kryterium akceptacji:** Prawidłowy stan `SeriesBible.data["declensions"]` w Kroku 6 = 100% transferu odmienionych paradygmatów z Kroku 5 (brak zamrożonych mianowników dla antroponimów obecnych w Kroku 5) oraz niezmienność członu dopełniaczowego w związkach rządu `[Rzeczownik w M] + [Rzeczownik w D]` we wszystkich przypadkach `M..W` (źródło autorytetu: `EpisodeProfiler` Krok 5 oraz reguły polskiej składni rządu).

#### 2C.10 (z 9.3/2B.8) — Izolacja okna czasowego ASR dla wszystkich segmentów w odcinku (`profiler.py`)
- **Konflikt z 9.3:** W audytowanym odcinku (`WYKRYTY BŁĄD 8`, Krok 4 i Krok 10) mimo obecności parametru `duplicate_time_distance_sec > 1.5` w `sanitize_event_asr`, w rzeczywistym przebiegu odcinka identyczne ciągi transkrypcji ASR pojawiły się w liniach oddalonych o ponad `1,5` s (np. między `ID: 133` a `ID: 134` oddalonymi o `30,8` s oraz w serii `ID: 174–179`), ponieważ pętla budująca transkrypcje w `EpisodeProfiler` nie przekazała globalnego słownika czasów ostatniego użycia danego segmentu ASR.
- **Rozstrzygnięcie:** **ROZSZERZYĆ** wywołanie `EpisodeProfiler.sanitize_event_asr` w potoku głównym Kroku 4 (`profiler.py`).
- **Implementacja:**
  1. W pętli przypisującej segmenty Whisper ASR do kolejnych zdarzeń `Dialogue:` w Kroku 4 utrzymuj rejestr `seen_asr_timestamps: Dict[str, float]` mapujący znormalizowany tekst segmentu ASR na czas `end_sec` zdarzenia, w którym wystąpił po raz pierwszy/ostatni.
  2. Dla każdego zdarzenia wyliczaj rzeczywistą odległość czasową `duplicate_time_distance_sec = current_start_sec - seen_asr_timestamps[norm_asr]` i przekazuj ją do `EpisodeProfiler.sanitize_event_asr`. Ponadto dla każdego powtórzenia identycznego segmentu ASR w $\ge 3$ kolejnych liniach dialogowych zachowuj segment wyłącznie w linii o największym pokryciu czasowym, a w pozostałych zeruj (`""`).
- **Kryterium akceptacji:** Prawidłowy stan transkrypcji ASR w Kroku 4 i Kroku 10 = unikalność segmentów ASR między ujęciami oddalonymi o $> 1,5\text{ s}$ oraz brak seryjnego powielania tego samego zdania ASR w $> 2$ kolejnych liniach (źródło autorytetu: przedziały czasowe `[start, end]` w sekcji `[Events]`).

---

## SEKCJA 3: REGUŁY DLA PIPELINE'U DANYCH

1. **R3.1 (P0):** Prawidłowy stan `SeriesBible.data["characters"]` i `SeriesBible.data["relations"]` w pamięci RAM po Kroku 6 = pełna zgodność pól `gender`, `grammatical_gender` oraz `description` ze zweryfikowanym rekordem P0 (`EpisodeProfiler`), obecność wpisów `P1`/`P2` dla wszystkich osobowych etykiet aktorów z Kroku 3 oraz pełna spójność kierunkowa i rodzajowa każdego wpisu w `relations` potwierdzona przez `_validate_relation_entry_consistency`. Źródło stanu docelowego: rekord P0 (`EpisodeProfiler`) oraz Krok 3.
2. **R3.2 (P0):** Prawidłowy stan pre-passu scenicznego (`reconcile_prepass_with_p0`) oraz wektora `telemetry` (`arbitrate_event_telemetry`) w Krokach 7 i 10 = stuprocentowa zgodność statystyk obsady oraz tagów `MASCULINE`/`FEMININE` mówcy i adresata ze zweryfikowanym `p0_gender` z `SeriesBible` (z użyciem estymacji $F_0$ wyłącznie jako fallbacku dla encji spoza P0 o `gender == "UNKNOWN"`). Źródło stanu docelowego: rekord P0 (`SeriesBible`).
3. **R3.3 (P0):** Prawidłowy stan przepływu między Fazą 1 a Fazą 2 (`DialogueVerifier.verify_batch` i `_guard_phase2_regressions`) = przekazanie jawnego atrybutu `is_internal_monologue` do Fazy 1, wyzerowanie `changes_made = None` przy braku zmiany tekstu merytorycznego oraz przywrócenie `phase1_text` w przypadku: (a) nałożenia całoliniowej kursywy na dialog z jawnym adresatem (`over_application_italics`), (b) zerwania ciągłości wielokropka i małej litery w zdaniu rozbitym (`ellipsis_continuation_syntax`), (c) utraty trybu przypuszczającego lub modalności 1. os. lp. (`first_person_modal_and_conditional_loss`), (d) zmiany czasu przeszłego na teraźniejszy wbrew `en_text` (`past_to_present_tense_shift`) oraz wszystkich 16 kategorii z wersji 9.2/9.3. Źródło stanu docelowego: `phase1_text` oraz `en_text`.
4. **R3.4 (P0):** Prawidłowy stan higieny post-processingu (`EpisodeQualityGate._run_phase_7_hygiene` i `normalize_ass_tags_and_sign_layout`) = usunięcie nieznanych pseudotagów szablonowych z bloków `{\...}`, zachowanie przecinka po inicjalnym wołaczu `W` (w tym przed partykułą `czy`) oraz spójność formatowania plansz `is_sign` między `dpos_text` a `ass_text`. Źródło stanu docelowego: `dpos_text` (`phase1_text`) oraz specyfikacja ASS v4.00+.
5. **R3.5 (P0):** Prawidłowy stan raportu Kroku 11 (`EpisodeFlightRecorder.report_step_11_quality_gate`) = wylistowanie pełnej listy poprawek z `EpisodeQualityGate.get_all_fixes()` oraz obecność pola `consistency_check` ze statusem `"OK"` (`reported == collected`). Źródło stanu docelowego: rejestr `EpisodeQualityGate`.
6. **R3.6 (P0):** Prawidłowy stan bufora ASR w Kroku 4 (`EpisodeProfiler.sanitize_event_asr`) = wyzerowanie segmentów zawierających halucynacje łacińskie ASCII w japońskim audio lub ciągi powtórzeniowe (`2B.8.a`) oraz wyzerowanie duplikatów między zdarzeniami oddalonymi o $> 1,5\text{ s}$ (`2C.10`), przy nadrzędnym autorytecie `en_text`. Źródło stanu docelowego: `en_text` oraz ramy czasowe `[Events]`.

---

## SEKCJA 4: KOLEJNOŚĆ WDROŻENIA

Kolejność wdrożenia wynika bezpośrednio z rozkładu procentowego błędów (62,5% OFFLINE + 37,5% HYBRYDA = 100% udziału ogniw offline) oraz zależności danych od Kroku 3 do Kroku 11:

1. **ETAP WDROŻENIOWY 0 — Wykonanie Fazy 0 (Obowiązkowe czytanie kodu i weryfikacja flag Phase 0.A, 0.B, 0.C):**
   - Przeczytanie plików z listy P0.1, rozstrzygnięcie flag `Phase 0.A`, `Phase 0.B`, `Phase 0.C` i wypełnienie tabel P0.2 oraz P0.3 w `Raport_wdrozenia_9.4.md`.
2. **ETAP WDROŻENIOWY 1 — Naprawa wejścia i propagacji P0 w Krokach 3–7 (`2B.8.a`, `2C.10`, `2C.7`, `2C.5`, `2C.9`, `2B.9`, `2C.1`):**
   - Najpierw izolacja i oczyszczenie bufora ASR z halucynacji i duplikatów w Kroku 4 (`2B.8.a`, `2C.10`).
   - Następnie populacja encji drugoplanowych z Kroku 3 (`2C.7`), pełna sanitacja `description` i `relations` z `_validate_relation_entry_consistency` (`2C.5`) oraz ochrona paradygmatów odmiany w Kroku 6 (`2C.9`).
   - Następnie uzgodnienie pre-passu scenicznego z rekordem P0 (`2B.9`) i bezwarunkowe wymuszenie `p0_gender` w `SceneDiscourseGraph.arbitrate_event_telemetry` (`2C.1`).
3. **ETAP WDROŻENIOWY 2 — Domknięcie barier Fazy 1 i Fazy 2 w Krokach 8–9 (`2C.6`, `2C.2`, `2B.11`):**
   - Przekazanie `is_internal_monologue` do Fazy 1 i blokada `over_application_italics` w Fazie 2 (`2C.6`).
   - Rozszerzenie `_guard_phase2_regressions` o ochronę ciągłości wielokropka i małej litery (`ellipsis_continuation_syntax`), trybu przypuszczającego 1. os. lp. i czasu przeszłego (`2C.2`).
   - Wyzerowanie pozornych uzasadnień `changes_made = None` przy braku zmiany tekstu w `verify_batch` (`2B.11`).
4. **ETAP WDROŻENIOWY 3 — Higiena post-processingu i raportowania w Kroku 11 oraz aktualizacja reguł (`2B.10`, `2C.4`, `2C.8` + Sekcja 1 i 3):**
   - Ochrona przecinka po wołaczu `W` przed `czy` (`2B.10`) i sanitacja nieznanych pseudotagów w `{\...}` (`2C.4`).
   - Wdrożenie `get_all_fixes()` i `consistency_check` w `report_step_11_quality_gate` (`2C.8`).
   - Aktualizacja reguł `R1.1–R1.11` i `R3.1–R3.6`.

---

## SEKCJA 5: WALIDACJA TESTOWA I WARUNEK UKOŃCZENIA

### 5A — Walidacja testowa

#### 1. Infrastruktura testowa (stan po Depuracji Legacy 1.0, commit `474fb64`)
- **Pliki testowe jednostkowe (domyślne KEEP):** `tests/test_avt_linter.py`, `tests/test_verifier.py`, `tests/test_series_memory.py`, `tests/test_discourse_and_translator.py`, `tests/test_metadata.py`, `tests/test_profiler.py`, `tests/test_translator.py`, `tests/test_flight_recorder.py` oraz 64 testy `KEEP` w `test_system.py` (łącznie 116 testów bazowych w trybie domyślnym).
- **Pliki testowe zarchiwizowane:** `tests/archive/test_legacy_manifest.py` (wykluczone przez `norecursedirs` w `pytest.ini` — pozostają nietknięte).
- **Komendy testowe:**
  - `komenda_fast` = `pytest` (uruchamia testy z `addopts = -v --tb=short -m "not slow and not network"`, czas wykonania $< 60\text{ s}$)
  - `komenda_full` = `pytest -m ""` (uruchamia wszystkie testy jednostkowe, `slow` i `network`)
  - `komenda_slow` = `pytest -m slow`
  - `komenda_network` = `pytest -m network`
- **Bramki CI/CD:** `verify_purity.py`, `verify_ultimate_pipeline.py`, `verify_12_fixes.py`, `audit_diff.ps1`.

#### 2. Wykaz nowych testów (wzorce strukturalne z placeholderami `<RZECZYWISTY_*>`)
Wszystkie nowe testy mają kategorię markera `unit` (brak markerów `slow`/`network` — wchodzą do domyślnego przebiegu `komenda_fast`). Placeholdery `<RZECZYWISTY_*>` agent kodujący wypełnia w Phase 0 (tabela P0.3) autentycznymi danymi z `SeriesBible` / `en_text` odcinka testowego (innego niż odcinek audytowany):

| ID testu | Punkt Sekcji 2 | Plik testowy | Nazwa testu | Kategoria markera | Kryterium akceptacji (forma pozytywna + źródło autorytetu) |
|---|---|---|---|---|---|
| **T4.1** | **2B.9** | `tests/test_profiler.py` | `test_reconcile_prepass_with_p0_enforces_verified_cast_gender` | `unit` | Prawidłowy stan statystyk obsady pre-passu scenicznego = 100% zgodności z `p0_gender` (`MALE`/`FEMALE`) z `SeriesBible` ponad estymacją $F_0$. |
| **T4.2** | **2B.8.a** | `tests/test_profiler.py` | `test_sanitize_event_asr_strips_latin_and_repetition_hallucinations` | `unit` | Prawidłowy stan `asr_text` = wyzerowanie/oczyszczenie segmentów zawierających łacińskie słowa ASCII lub powtórzenia $>2$ przy zachowaniu czystego japońskiego ASR i `en_text`. |
| **T4.3** | **2B.10** | `tests/test_avt_linter.py` | `test_eqg_preserves_comma_after_initial_vocative_before_interrogative` | `unit` | Prawidłowy stan `ass_text` = zachowanie przecinka po inicjalnym wołaczu `W` przed partykułą pytajną `czy` zgodnie z `dpos_text`. |
| **T4.4** | **2B.11** | `tests/test_verifier.py` | `test_verify_batch_nullifies_changes_made_when_text_unchanged` | `unit` | Prawidłowy stan `changes_made` = wartość `None`, gdy `refined_pl` po normalizacji białych znaków jest tożsamy z `f1_pl`. |
| **T4.5** | **2C.1** | `tests/test_discourse_and_translator.py` | `test_arbitrate_telemetry_enforces_p0_gender_for_inferred_and_explicit_speakers` | `unit` | Prawidłowy stan `telemetry` = emisja `MASCULINE` dla mówcy i adresata o `p0_gender: MALE` oraz `FEMININE` dla `p0_gender: FEMALE` niezależnie od pustego `Name` lub defaultu sceny. |
| **T4.6** | **2C.2** | `tests/test_verifier.py` | `test_guard_phase2_preserves_ellipsis_continuation_conditional_and_past_tense` | `unit` | Prawidłowy stan wyjścia `_guard_phase2_regressions` = przywrócenie `f1_pl` przy usunięciu `...` i małej litery po linii z `...`, przy utracie `-bym` 1. os. lp. oraz przy zmianie czasu przeszłego na teraźniejszy. |
| **T4.7** | **2C.4** | `tests/test_avt_linter.py` | `test_phase7_strips_invalid_template_tags_and_preserves_valid_ass_directives` | `unit` | Prawidłowy stan bloku `{\...}` = usunięcie nieznanych pseudotagów ze spacjami przy zachowaniu wszystkich poprawnych tagów ASS (`\an`, `\pos`, `\c`, `\3c`, `\shad`, `\blur`, `\fn`, `\fs`, `\frz`). |
| **T4.8** | **2C.5** | `tests/test_series_memory.py` | `test_sanitize_ram_cleans_character_descriptions_and_resolves_relation_tv_asymmetry` | `unit` | Prawidłowy stan `SeriesBible` w RAM = zgodność `description` z `gender`, zgodność `[KOBIETA/MĘŻCZYZNA (Adresat)]` z `p0_gender` adresata oraz spójny reżim `POUFNY`/`FORMALNY` bez sprzeczności. |
| **T4.9** | **2C.6** | `tests/test_translator.py` | `test_phase1_monologue_detection_and_phase2_over_application_italics_guard` | `unit` | Prawidłowy stan kursywy = obecność `{\i1}...{\i0}` dla `is_internal_monologue: true` (styl `Italics`) oraz odrzucenie całoliniowego `{\i1}...{\i0}` na głośnym dialogu z adresatem. |
| **T4.10** | **2C.7** | `tests/test_metadata.py` | `test_step3_secondary_actors_populate_p1_and_p2_entries_in_series_bible` | `unit` | Prawidłowy stan `SeriesBible.data["characters"]` po Kroku 6 = obecność wpisów `P1` (`MALE`/`FEMALE`) i `P2` (`UNKNOWN`) dla wszystkich osobowych etykiet z Kroku 3. |
| **T4.11** | **2C.8** | `tests/test_flight_recorder.py` | `test_report_step_11_lists_all_fixes_and_emits_consistency_check_ok` | `unit` | Prawidłowy stan raportu Kroku 11 = pełne wylistowanie wszystkich pozycji z `get_all_fixes()` oraz `consistency_check.status == "OK"` przy `reported == collected`. |
| **T4.12** | **2C.9** | `tests/test_series_memory.py` | `test_declension_preserves_genitive_modifier_in_compound_terms_and_transfers_p0_paradigm` | `unit` | Prawidłowy stan `declensions` = odmiana wyłącznie członu nadrzędnego w wyrażeniu `[Rzeczownik w M] + [Rzeczownik w D]` oraz pełny transfer odmiany `M..W` z Kroku 5. |
| **T4.13** | **2C.10** | `tests/test_profiler.py` | `test_step4_asr_deduplication_across_distant_events_and_consecutive_streaks` | `unit` | Prawidłowy stan bufora ASR w Kroku 4 = wyzerowanie identycznego segmentu ASR powtórzonego w zdarzeniu oddalonym o $> 1,5\text{ s}$ lub w serii $> 2$ kolejnych linii. |

#### 3. Warunek ukończenia wdrożenia (definicja pozytywna)
Prawidłowy stan ukończenia wdrożenia wersji **9.4** = jednoczesne spełnienie jedenastu warunków pozytywnych (a)–(k):
- **(a)** `komenda_fast` (`pytest`): 100% PASSED, `0 FAILED`, `0 ERROR`, czas wykonania $< 60\text{ s}$;
- **(b)** `komenda_full` (`pytest -m ""`): 100% PASSED, `0 FAILED`, `0 ERROR`;
- **(c)** `komenda_slow` (`pytest -m slow`): 100% PASSED;
- **(d)** `komenda_network` (`pytest -m network`): 100% PASSED;
- **(e)** pełne pokrycie testowe każdej zmiany z Sekcji 2A (przez testy istniejące), 2B (`T4.1–T4.4`) oraz 2C (`T4.5–T4.13`);
- **(f)** Phase 0 ukończona z wypełnionymi tabelami P0.2 i P0.3 oraz rozstrzygniętymi flagami `Phase 0.A`, `Phase 0.B` i `Phase 0.C` w `Raport_wdrozenia_9.4.md`;
- **(g)** każdy nowy test `T4.1–T4.13` spełnia wszystkie pięć warunków Zasady 8 (a)–(e);
- **(h)** każdy nowy test `T4.1–T4.13` jest w 100% wolny od anty-wzorców degradacji `D1–D6` (w tym `D6.a–D6.e`);
- **(i)** żaden z 116 testów `KEEP` z Depuracji Legacy 1.0 nie został usunięty ani osłabiony;
- **(j)** wszystkie nowe testy jednostkowe wykonują się w przebiegu domyślnym, a ewentualne testy ciężkie posiadają `@pytest.mark.slow` / `@pytest.mark.network`;
- **(k)** katalog `tests/archive/` pozostaje nietknięty w iteracji, 3 gałęzie `# DEFENSIVE_FALLBACK` w `avt_linter.py` (linie 7569, 7709, 11414) pozostają nietknięte z komentarzem, a wszystkie 4 bramki CI/CD (`verify_purity.py`, `verify_ultimate_pipeline.py`, `verify_12_fixes.py`, `audit_diff.ps1`) zwracają status PASS / VICTORY CONFIRMED.

### 5B — Obowiązek wypełnienia Raportu Wdrożenia (DELIVERABLE)

Po zakończeniu implementacji i uruchomieniu pełnej walidacji testowej agent kodujący ma bezwzględny obowiązek wypełnienia wszystkich pól oznaczonych placeholderami `<DO_WYPEŁNIENIA_*>` (w szczególności tabel P0.2 i P0.3, weryfikacji flag Phase 0.A–0.C, stanu bazowego fast+full, stanu końcowego fast+full, mapowania testów, weryfikacji D1–D6, hash commita oraz daty wdrożenia) w pliku:
`C:\Users\Piotrek\Desktop\translator\Artefakty\Raport_wdrozenia_9.4.md`
i zapisania kompletnego raportu pod tą ścieżką.