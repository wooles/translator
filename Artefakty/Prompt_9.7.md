# Plik: C:\Users\Piotrek\Desktop\translator\Artefakty\Prompt_9.7.md

# PROMPT NAPRAWCZY POTOKU AVT — WERSJA 9.7

## PREAMBUŁA

Dokument definiuje operacje kodowe, regułowe i walidacyjne rozszerzające potok AVT z wersji 9.6 (commit `c87b22f`) oraz utrzymujące stan po Depuracji Legacy 1.0 (commit `474fb64`) do wersji **9.7**. Podstawa empiryczna: audyt weryfikacyjny przebiegu odcinka testowego po wdrożeniu wersji 9.6 (Etap 1/2 oraz Etap 2/2), który potwierdził pełne wyeliminowanie 4 z 5 błędów z audytu 9.5 (oczyszczenie `Adresat:` z nawiasów $F_0$ dla 100% encji P0, zdjęcie całoliniowej kursywy na głośnym dialogu z pojedynczym pochylonym słowem EN, normalizację `\n` $\rightarrow$ `\N` w 260/260 rekordach oraz wyzerowanie tokenów ASR o `cjk_count == 0` i osieroconych partykuł nagłosowych), a jednocześnie zidentyfikował **1 regresję krytyczną z operacji 2B.1 oraz 3 drobne luki brzegowe**:
1. **Kategoria Problemu 1 (Regresja kaskadowej duplikacji dwuczłonowych antroponimów P0 oraz globalne zanieczyszczenie list `aliases` w Kroku 6 — z operacji 2B.1 w 9.6):**
   - (a) funkcja `SeriesBible.map_bilingual_role_aliases` (`series_memory.py`) dopisała aliasy zdrobniałe z tytułu serii (`["<RZECZYWISTY_RDZEŃ_PO_ODCIĘCIU_1>", "<RZECZYWISTY_ALIAS_JAPOŃSKI_1>", "<RZECZYWISTY_ALIAS_JAPOŃSKI_2>"]`) do tablicy `aliases` **wszystkich 22 postaci P0** zamiast wyłącznie do odpowiadającej im fonetycznie encji kanonicznej `<RZECZYWISTY_ANTROPONIM_1>`;
   - (b) funkcja podmiany aliasów w `translator.py:5785-5800` (oraz przed zapisem do `D_pos`) uruchamiała zastępowanie pojedynczych członów składowych (`<IMIE>`, `<NAZWISKO>`) należących do `aliases` dwuczłonowego antroponimu `<IMIE> <NAZWISKO>` pełną nazwą dwuczłonową, przez co poprawnie przetłumaczone i odmienione przez LLM ciągi `"co z <IMIE_N> <NAZWISKO>."` oraz `"z opisem <IMIE_D> <NAZWISKO>."` zostały zdeformowane w `D_pos` do `"<IMIE_N> <IMIE> <NAZWISKO>."`, a w finalnym pliku `.ass` do `"<IMIE_N>\N<IMIE> <NAZWISKO> <IMIE> <NAZWISKO> <NAZWISKO>."` (naruszając Zasadę 3 Primary LLM Translation Authority oraz niezmiennik `ass_text == dpos_text`).
2. **Kategoria Problemu 2 (Brak inferencji płci leksykalnej dla angielskich etykiet drugoplanowych P2 w `populate_secondary_actor_tags` — z operacji 2C.1 / 2C.4 w 9.6):** etykiety drugoplanowe o jednoznacznym znaczeniu płciowym (`Boy`, `Girl`) otrzymywały w Kroku 6 `"gender": "UNKNOWN"`, co skutkowało emisją `Adresat: Boy (FEMININE)` w scenie z udziałem postaci żeńskiej.
3. **Kategoria Problemu 3 (Brak normalizacji podziału wiersza `\N` względem spacji `" "` przy porównywaniu `f1_pl` i `refined_pl` — z operacji 2C.5 w 9.6):** wypisywanie w logu konsolowym pustych wpisów `[Redaktor Dialogów]` bez etykiety powodu, gdy jedyną różnicą między `Szkic` a `Szlif` było zastąpienie spacji znacznikiem `\N`.
4. **Kategoria Problemu 4 (Pozostawienie artefaktowych klastrów znaków zapytania i cyfr `.? ??000` w japońskim segmencie ASR — z operacji 2C.3 w 9.6):** przepuszczenie przez `EpisodeProfiler.sanitize_event_asr` nielingwistycznego ciągu znaków zapytania i cyfr sklejonego z tekstem japońskim.

Niniejszy dokument przestrzega czterech nadrzędnych zasad Standardu 9.0 oraz rozszerzeń Standardu 9.3–9.7:
1. **Zero-Literal (Zasada 1)** — wszystkie reguły, opisy operacji, uzasadnienia systemowe i kryteria akceptacji operują wyłącznie na kategoriach językowych, semiotycznych i metajęzykowych architektury oraz placeholderach `<RZECZYWISTY_*>`.
2. **Pure Positive Domain Invariant (Zasada 2)** — każda reguła w Sekcji 1 i Sekcji 3 oraz każde kryterium akceptacji w Sekcji 2 i Sekcji 5 definiuje zbiór dopuszczalnych stanów docelowych w formie pozytywnej („prawidłowy stan = X", „zachowuje…", „obejmuje wyłącznie…", „ma pierwszeństwo wobec…").
3. **Primary LLM Translation Authority (Zasada 3)** — pierwotne tłumaczenie Fazy 1 (`phase1_text`) i weryfikacja Fazy 2 (`phase2_text`) są nadrzędnym autorytetem translacyjnym; post-processing po Fazie 2 nigdy nie modyfikuje ani nie rozwija pojedynczych członów dwuczłonowych antroponimów (`<IMIE> <NAZWISKO>`), gwarantując ścisłą tożsamość `ass_text == dpos_text` dla wszystkich linii niewymagających korekty technicznej EQG.
4. **Instance-Free Metalinguistic Architecture (Zasada 4)** — wszystkie operacje operują na kategoriach modułów, funkcji, operatorów i struktur danych.
5. **Ochrona nienaruszalności Depuracji Legacy 1.0 (Zasada 16)** — wdrożenie wersji 9.7 zachowuje w 100% stan po Depuracji 1.0 i wersji 9.6: wszystkie 195 testów domyślnych (`KEEP` + jednostkowe 9.4, 9.5 i 9.6) pozostaje aktywnych w przebiegu `pytest`, markery `@pytest.mark.slow` (153 testy) i `@pytest.mark.network` (12 testów) pozostają nienaruszone, katalog `tests/archive/` pozostaje nietknięty, a 3 chronione gałęzie `# DEFENSIVE_FALLBACK` w `avt_linter.py` zachowują swoją postać i komentarze.

Numer wersji: **9.7**. Poprzednia wersja toru naprawczego: **9.6**. Wersja toru Depuracji Legacy w tle: **1.0** (commit `474fb64`).

---

## IDENTYFIKATORY METAJĘZYKA ARCHITEKTURY

- **Nazwy modułów i klas:** `avt_linter.py`, `verifier.py`, `series_memory.py`, `profiler.py`, `rules.py`, `translator.py`, `scene_discourse.py`, `metadata.py`, `flight_recorder.py`, `pipeline_logger.py`, `sign_detector.py`, `AVTLinter`, `EpisodeQualityGate`, `EpisodeFlightRecorder`, `DialogueVerifier`, `SeriesBible`, `EpisodeProfiler`, `SceneDiscourseGraph`, `RuleDispatcher`, `VisualSignDetector`, `MultimodalTranslator`.
- **Nazwy funkcji i metod:** `lint_and_fix_line`, `audit_and_fix_entire_episode`, `_run_phase_7_hygiene`, `normalize_ass_tags_and_sign_layout`, `should_apply_top_alignment_on_collision`, `arbitrate_event_telemetry`, `build_discourse_topology`, `_guard_phase2_regressions`, `_is_whole_line_italic`, `normalize_phase2_line_and_reason`, `verify_batch`, `enforce_sign_nominative_orthography`, `_sanitize_loaded_bible_in_ram`, `sync_verified_profile_entity`, `parse_step5_declension_line`, `_validate_relation_entry_consistency`, `preserve_italics_for_upright_style`, `reconcile_prepass_with_p0`, `profile_episode`, `_extract_f0_contour`, `sanitize_event_asr`, `report_step_11_quality_gate`, `log_quality_gate_and_pricing`, `get_all_fixes`, `get_active_rules`, `detect_signs`, `synchronize_ass_event_metadata_and_styles`, `build_phase1_prompt`, `_prepare_batch_prompt`, `_translate_batch`, `_precompute_episode_scene_genders`, `populate_secondary_actor_tags`, `map_bilingual_role_aliases`, `align_vocative_orthography`, `generate_polish_name_declension`, `clean_anime_filename`, `normalize_anime_slug`.
- **Nazwy kroków i faz:** Krok 0–11, Faza 0 (higiena), Faza 0 (Phase 0 — czytanie kodu), Faza 1 (tłumaczenie), Faza 2 (weryfikacja), post-processing.
- **Enum values i pola schematu:** `MALE`, `FEMALE`, `UNKNOWN`, `NEUTRAL`, `MASCULINE`, `FEMININE`, `VIRILE`, `NON_VIRILE`, `POLYLOGUE`, `CHÓR`, `ANTHROPONYM`, `is_sign`, `is_internal_monologue`, `has_verified_gender`, `speaker_name`, `target_actor`, `target_gender`, `addressee_gender`, `p0_gender`, `en_text`, `dpos_text`, `phase1_text`, `phase2_text`, `ass_text`, `telemetry`, `prosody_tags`, `speaker_tags`, `pronouns_en`, `priority`, `confidence`, `P0`, `P1`, `P2`, `strict_positive_domain`, `changes_made`, `refined_pl`, `f1_pl`, `asr_text`, `keep_honorifics`, `aliases`, `M`, `D`, `C`, `B`, `N`, `Ms`, `W`.
- **Znaczniki formatu ASS:** `[Script Info]`, `[V4+ Styles]`, `[Events]`, `Dialogue:`, `\N`, `\n`, `{\...}`, `\an7`, `\an8`, `\an9`, `\pos(x,y)`, `\move(x1,y1,x2,y2)`, `\fad(t1,t2)`, `\3c`, `\1c`, `\bord`, `\shad`, `\i1`, `\i0`, `\blur`, `\fn`, `\fs`, `\frz`.
- **Placeholdery testowe i metajęzykowe:** `<RZECZYWISTY_ANTROPONIM_1>`, `<RZECZYWISTY_ANTROPONIM_2>`, `<RZECZYWISTY_ANTROPONIM_DWUCZŁONOWY_1>`, `<RZECZYWISTY_CZŁON_IMIENNY_N_1>`, `<RZECZYWISTY_CZŁON_IMIENNY_D_1>`, `<RZECZYWISTY_CZŁON_NAZWISKOWY_1>`, `<RZECZYWISTY_ANTROPONIM_MĘSKI_1>`, `<RZECZYWISTY_ANTROPONIM_ŻEŃSKI_1>`, `<RZECZYWISTY_ALIAS_JAPOŃSKI_1>`, `<RZECZYWISTY_RDZEŃ_PO_ODCIĘCIU_1>`, `<RZECZYWISTA_ETYKIETA_MĘSKA_P2_1>`, `<RZECZYWISTA_ETYKIETA_ŻEŃSKA_P2_1>`, `<RZECZYWISTY_ARTEFAKT_CYFROWY_ASR_1>`, `<RZECZYWISTY_CIĄG_PL_1>`, `<RZECZYWISTY_CIĄG_PL_2>`, `<RZECZYWISTY_CIĄG_EN_1>`, `<RZECZYWISTY_CIĄG_EN_2>`, `<RZECZYWISTY_PARADYGMAT_M_1>`, `<RZECZYWISTY_PARADYGMAT_D_1>`, `<RZECZYWISTY_PARADYGMAT_N_1>`, `<RZECZYWISTY_PARADYGMAT_W_1>`, `<WARTOŚĆ_ENUM_TECHNICZNA_1>`, `<WARTOŚĆ_ENUM_TECHNICZNA_2>`.

---

## FAZA 0 — CZYTANIE KODU (OBOWIĄZKOWA)

Przed wprowadzeniem jakiejkolwiek zmiany w kodzie agent kodujący ma bezwzględny obowiązek wykonania Fazy 0 i udokumentowania jej wyników w sekcji `2. PHASE 0 — WYNIK WERYFIKACJI KODU` pliku `C:\Users\Piotrek\Desktop\translator\Artefakty\Raport_wdrozenia_9.7.md`.

### P0.1. Lista plików do przeczytania w całości i weryfikacji ścieżek wywołań runtime
1. `translator.py` — pełna inspekcja:
   - linii `5785-5800` oraz miejsc przed zapisem `AVTLinter (D_pos):`, w których w wersji 9.6 dodano podmianę aliasów na kanoniczne nazwy z `SeriesBible` (dlaczego kod podmienił człon `<NAZWISKO>` w poprawnym dwuczłonowym antroponimie `<IMIE_N> <NAZWISKO>` na pełne `<IMIE> <NAZWISKO>`, uruchamiając się wielokrotnie i psując finalny plik `.ass`),
   - linii `4500` wypisującej `[Redaktor Dialogów]` w konsoli (dlaczego wypisuje blok zmiany przy `changes_made: null`, gdy różnicą jest wyłącznie spacja vs `\N`).
2. `series_memory.py` — pełna inspekcja:
   - metody `map_bilingual_role_aliases` (`linia ~6224`) oraz `_sanitize_loaded_bible_in_ram` (`linia ~5366`) — dlaczego aliasy z tytułu (`Pii`, `Pii-chan`, `Pii-kun`) zostały dopisane do tablicy `aliases` wszystkich 22 postaci P0 zamiast wyłącznie do postaci o wspólnym prefiksie fonetycznym (`Peeps`),
   - metody `populate_secondary_actor_tags` — w jaki sposób przypisywane są pola `gender` i `grammatical_gender` dla angielskich etykiet rodzajowych takich jak `Boy`, `Girl`, `Man`, `Woman`.
3. `verifier.py` — pełna inspekcja `DialogueVerifier.normalize_phase2_line_and_reason` (`linia ~455`) oraz `verify_batch` (`linia ~992`) pod kątem porównywania `f1_pl` i `refined_pl` różniących się wyłącznie podziałem wiersza `\N` vs spacja `" "`.
4. `profiler.py` — pełna inspekcja `EpisodeProfiler.sanitize_event_asr` (`linie 348-431`) pod kątem usuwania artefaktowych ciągów znaków zapytania i cyfr (`.? ??000`) wewnątrz i na końcu japońskiego segmentu.

### P0.2. Tabela mapowania plan ↔ kod (szablon obowiązkowy do wypełnienia w `Raport_wdrozenia_9.7.md`)

| Operacja (sekcja 9.7) | Miejsce wywołania / metoda w planie | Rzeczywiste miejsce wywołania w kodzie (plik + linia + metoda) | Rzeczywista sygnatura w kodzie | Zgodność | Uwagi / Rozstrzygnięcie |
|---|---|---|---|---|---|
| 2C.1 | Usunięcie destrukcyjnej podmiany członów dwuczłonowych antroponimów w `translator.py` oraz selektywne przypisanie aliasów z honoryfikatorem wyłącznie do pasującej fonetycznie encji P0 w `series_memory.py` | `<DO_WYPEŁNIENIA_PRZEZ_AGENTA_KODUJĄCEGO>` | `<DO_WYPEŁNIENIA_PRZEZ_AGENTA_KODUJĄCEGO>` | `<DO_WYPEŁNIENIA_PRZEZ_AGENTA_KODUJĄCEGO>` | `<DO_WYPEŁNIENIA_PRZEZ_AGENTA_KODUJĄCEGO>` |
| 2C.2 | Inferencja płci leksykalnej dla angielskich etykiet osobowych P2 (`Boy` $\rightarrow$ `MALE`, `Girl` $\rightarrow$ `FEMALE`) w `SeriesBible.populate_secondary_actor_tags` (`series_memory.py`) | `<DO_WYPEŁNIENIA_PRZEZ_AGENTA_KODUJĄCEGO>` | `<DO_WYPEŁNIENIA_PRZEZ_AGENTA_KODUJĄCEGO>` | `<DO_WYPEŁNIENIA_PRZEZ_AGENTA_KODUJĄCEGO>` | `<DO_WYPEŁNIENIA_PRZEZ_AGENTA_KODUJĄCEGO>` |
| 2C.3 | Ignorowanie różnic wyłącznie w łamaniu wiersza (`\N` vs spacja `" "`) przy `changes_made: null` w `normalize_phase2_line_and_reason` i loggerze `[Redaktor Dialogów]` (`verifier.py`, `translator.py`) | `<DO_WYPEŁNIENIA_PRZEZ_AGENTA_KODUJĄCEGO>` | `<DO_WYPEŁNIENIA_PRZEZ_AGENTA_KODUJĄCEGO>` | `<DO_WYPEŁNIENIA_PRZEZ_AGENTA_KODUJĄCEGO>` | `<DO_WYPEŁNIENIA_PRZEZ_AGENTA_KODUJĄCEGO>` |
| 2C.4 | Wycinanie artefaktowych ciągów znaków zapytania i cyfr (`.? ??000`) w `EpisodeProfiler.sanitize_event_asr` (`profiler.py`) | `<DO_WYPEŁNIENIA_PRZEZ_AGENTA_KODUJĄCEGO>` | `<DO_WYPEŁNIENIA_PRZEZ_AGENTA_KODUJĄCEGO>` | `<DO_WYPEŁNIENIA_PRZEZ_AGENTA_KODUJĄCEGO>` | `<DO_WYPEŁNIENIA_PRZEZ_AGENTA_KODUJĄCEGO>` |

### P0.3. Tabela mapowania danych testowych (szablon z placeholderami obowiązkowy w `Raport_wdrozenia_9.7.md`)

| Placeholder | Wartość rzeczywista (z odcinka testowego, spoza audytu) | Źródło (P0 / EN / ASS) | Uwagi |
|---|---|---|---|
| `<RZECZYWISTY_ANTROPONIM_DWUCZŁONOWY_1>` | `<DO_WYPEŁNIENIA_MAPOWANIE_P0_3>` | P0 (`SeriesBible`) | Dwuczłonowe imię i nazwisko postaci P0 |
| `<RZECZYWISTY_CZŁON_IMIENNY_N_1>` | `<DO_WYPEŁNIENIA_MAPOWANIE_P0_3>` | P0 (`declensions`) | Narzędnik pierwszego członu imienia |
| `<RZECZYWISTY_CZŁON_IMIENNY_D_1>` | `<DO_WYPEŁNIENIA_MAPOWANIE_P0_3>` | P0 (`declensions`) | Dopełniacz pierwszego członu imienia |
| `<RZECZYWISTY_CZŁON_NAZWISKOWY_1>` | `<DO_WYPEŁNIENIA_MAPOWANIE_P0_3>` | P0 (`declensions`) | Drugi człon (nazwisko) znajdujący się w `aliases` |
| `<RZECZYWISTY_ANTROPONIM_1>` | `<DO_WYPEŁNIENIA_MAPOWANIE_P0_3>` | P0 (`SeriesBible`) | Jednoczłonowa encja kanoniczna posiadająca zdrobnienie `-chan` |
| `<RZECZYWISTY_ANTROPONIM_2>` | `<DO_WYPEŁNIENIA_MAPOWANIE_P0_3>` | P0 (`SeriesBible`) | Inna encja P0 (niepowiązana fonetycznie z aliasem `-chan`) |
| `<RZECZYWISTY_ALIAS_JAPOŃSKI_1>` | `<DO_WYPEŁNIENIA_MAPOWANIE_P0_3>` | EN / Audio | Wariant zdrobniały z `-chan` |
| `<RZECZYWISTY_PARADYGMAT_N_1>` | `<DO_WYPEŁNIENIA_MAPOWANIE_P0_3>` | P0 (`declensions`) | Forma narzędnika `N` dla `<RZECZYWISTY_ANTROPONIM_1>` |
| `<RZECZYWISTA_ETYKIETA_MĘSKA_P2_1>` | `<DO_WYPEŁNIENIA_MAPOWANIE_P0_3>` | `[Events]` | Angielska etykieta rodzajowa męska (np. `Boy`) |
| `<RZECZYWISTA_ETYKIETA_ŻEŃSKA_P2_1>` | `<DO_WYPEŁNIENIA_MAPOWANIE_P0_3>` | `[Events]` | Angielska etykieta rodzajowa żeńska (np. `Girl`) |
| `<RZECZYWISTY_ARTEFAKT_CYFROWY_ASR_1>` | `<DO_WYPEŁNIENIA_MAPOWANIE_P0_3>` | ASR | Ciąg znaków zapytania i cyfr (np. `.? ??000`) |
| `<RZECZYWISTY_CIĄG_PL_1>` | `<DO_WYPEŁNIENIA_MAPOWANIE_P0_3>` | F1 / PL | Pierwszy człon zdania polskiego |
| `<RZECZYWISTY_CIĄG_PL_2>` | `<DO_WYPEŁNIENIA_MAPOWANIE_P0_3>` | F1 / PL | Drugi człon zdania polskiego |
| `<RZECZYWISTY_CIĄG_EN_1>` | `<DO_WYPEŁNIENIA_MAPOWANIE_P0_3>` | EN | Zdanie angielskie |
| `<WARTOŚĆ_ENUM_TECHNICZNA_1>` | `<DO_WYPEŁNIENIA_MAPOWANIE_P0_3>` | KOD | `MASCULINE` |
| `<WARTOŚĆ_ENUM_TECHNICZNA_2>` | `<DO_WYPEŁNIENIA_MAPOWANIE_P0_3>` | KOD | `FEMININE` |

### P0.4. Weryfikacja flag Phase 0 (nowe flagi weryfikacyjne 0.L–0.O dla wersji 9.7)

Agent kodujący odpowiada w sekcji `2.4` pliku `Raport_wdrozenia_9.7.md` na cztery konkretne pytania weryfikacyjne:

1. **FLAGA PHASE 0.L (Przyczyna czterokrotnej duplikacji dwuczłonowego antroponimu w `ID: 48` i `ID: 52` oraz dopisania aliasów do wszystkich 22 postaci P0):**
   - *Pytanie weryfikacyjne:* W których dokładnie liniach `translator.py` (przed zapisem do `D_pos` oraz w `translator.py:5785-5800` przed zapisem `.ass`) wykonywana jest pętla podmieniająca aliasy na nazwę kanoniczną, dlaczego podmieniła ona nazwisko `<NAZWISKO>` w poprawnym ciągu `"<IMIE_N> <NAZWISKO>"` na `"<IMIE_N> <IMIE> <NAZWISKO>"`, a potem na `"<IMIE_N>\N<IMIE> <NAZWISKO> <IMIE> <NAZWISKO> <NAZWISKO>"`, oraz dlaczego w `series_memory.py` aliasy `["Pii", "Pii-chan", "Pii-kun"]` zostały dopisane do każdej z 22 postaci P0?
2. **FLAGA PHASE 0.M (Inferencja płci leksykalnej w `SeriesBible.populate_secondary_actor_tags`):**
   - *Pytanie weryfikacyjne:* Dlaczego `populate_secondary_actor_tags` w `series_memory.py` ustawiło `"gender": "UNKNOWN"` dla jednoznacznych płciowo etykiet angielskich `Boy` i `Girl`, co spowodowało emisję `Adresat: Boy (FEMININE)` w `ID: 58`?
3. **FLAGA PHASE 0.N (Porównywanie `Szkic` vs `Szlif` przy różnicy wyłącznie spacja vs `\N`):**
   - *Pytanie weryfikacyjne:* W której linii `verifier.py` / `translator.py` sprawdzany jest warunek wypisania bloku `[Redaktor Dialogów]` w konsoli i dlaczego przy `changes_made: null` wypisano pozycje różniące się wyłącznie wstawieniem `\N` w miejsce spacji?
4. **FLAGA PHASE 0.O (Artefakty `.? ??000` wewnątrz japońskiego segmentu ASR):**
   - *Pytanie weryfikacyjne:* Dlaczego regex w `EpisodeProfiler.sanitize_event_asr` (`profiler.py:348-431`) przepuścił podciąg `.? ??000` przed partykułą końcową `だよ` w `ID: 79`?

---

## SEKCJA 1: REGUŁY DLA MODELI LLM (Faza 1 i Faza 2)

Wszystkie poniższe reguły są sformułowane w pełnej formie pozytywnej (Pure Positive Domain Invariant — Zasada 2) i operują na kategoriach metajęzyka architektury (Zero-Literal — Zasada 1):

### Priorytet P0 (Reguły nienaruszalne — realizacja Primary LLM Translation Authority)

1. **R1.1 (P0) — Zgodność Rodzaju Gramatycznego Mówcy, Adresata i Grupy ze Zweryfikowanym Rekordem P0:**
   - **Definicja pozytywna:** Prawidłowy stan wypowiedzi dla mówcy o `p0_gender == "FEMALE"` w 1. os. lp. czasu przeszłego, czasu przyszłego złożonego i trybu przypuszczającego = zachowanie końcówek i form rodzaju żeńskiego (`-łam`, `-łabym`, przymiotniki i imiesłowy w rodzaju żeńskim); dla mówcy o `p0_gender == "MALE"` = zachowanie końcówek i form rodzaju męskiego (`-łem`, `-łbym`, przymiotniki i imiesłowy w rodzaju męskim). Prawidłowy stan zwrotów w 2. os. lp. do adresata o `p0_gender == "FEMALE"` = zachowanie form żeńskich (`-łaś`, `-łabyś`), a do adresata o `p0_gender == "MALE"` = zachowanie form męskich (`-łeś`, `-łbyś`). Prawidłowy stan form liczby mnogiej dla grupy złożonej wyłącznie z uczestniczek o `p0_gender == "FEMALE"` = zachowanie kategorii niemęskoosobowej (`NON_VIRILE`, końcówki `-łyśmy`, `-łyście`, `-ły`).
   - **Źródło stanu docelowego:** Rekord P0 w `SeriesBible` oraz `EpisodeProfiler` (`p0_gender`, `has_verified_gender: true`) oraz `pronouns_en`.

2. **R1.2 (P0) — Zachowanie Osoby i Liczby Gramatycznej Podmiotu oraz Dopełnienia z `phase1_text` i `en_text`:**
   - **Definicja pozytywna:** Prawidłowy stan kategorii osoby gramatycznej (1., 2. lub 3. osoby) oraz liczby (pojedynczej lub mnogiej) orzeczenia i zaimków dopełnienia w `phase1_text` i `phase2_text` = pełna zgodność z jawnymi zaimkami podmiotu i dopełnienia w `en_text`. Gdy podmiot w `en_text` występuje w 1. osobie liczby pojedynczej, orzeczenie w `phase1_text` i `phase2_text` zachowuje 1. osobę liczby pojedynczej niezależnie od liczby zaimka dzierżawczego przy dopełnieniu.
   - **Źródło stanu docelowego:** `phase1_text` oraz jednoznaczny sygnał `en_text` / `pronouns_en`.

3. **R1.3 (P0) — Zachowanie Modalności, Trybu Przypuszczającego, Czasu Przeszłego i Zdań Podrzędnych Identyfikujących:**
   - **Definicja pozytywna:** Prawidłowy stan czasowników epistemicznych, wolitywnych i modalnych w 1. os. lp., form trybu przypuszczającego (`-bym`, `-łbym`, `-łabym`) oraz form czasu przeszłego obecnych w `en_text` i `phase1_text` = pełne zachowanie ich kategorii modalnej i temporalnej w `refined_pl` wraz ze zdaniami podrzędnymi dopełnieniowymi identyfikującymi podmiot lub adresata.
   - **Źródło stanu docelowego:** `phase1_text` oraz jednoznaczny sygnał `en_text`.

4. **R1.6 (P0) — Bezwzględny Prymat Semantyczny `en_text`, Jawnego Aktora z `[Events]` i Rekordu P0 nad Transkrypcją Pomocniczą ASR:**
   - **Definicja pozytywna:** Prawidłowy stan przekładu w `phase1_text` i `phase2_text` = pełna wierność semantyczna, leksykalna i onomastyczna wobec tekstu źródłowego `en_text`, jawnego identyfikatora `speaker_name` w kolumnie `Name` sekcji `[Events]` oraz kanonicznych nazw własnych i paradygmatów z `SeriesBible`. Gdy tekst angielski `en_text` używa kanonicznego imienia postaci z `SeriesBible`, a transkrypcja pomocnicza ASR zawiera japoński wariant zdrobniały z honoryfikatorem (`-chan`, `-kun`), przekład w `phase1_text` i `phase2_text` stosuje kanoniczne imię z `en_text` i `SeriesBible` odmienione we właściwym przypadku gramatycznym (`M..W`).
   - **Źródło stanu docelowego:** Jednoznaczny sygnał `en_text`, sekcja `[Events]` oraz rekord P0 w `SeriesBible`.

5. **R1.7 (P0) — Nienaruszalność Rodzaju Gramatycznego 1. i 3. Osoby Czasu Przeszłego Wobec Tembru Głosu Seiyū:**
   - **Definicja pozytywna:** Prawidłowy stan form 1. os. lp. czasu przeszłego (`-łem` / `-łam`), trybu przypuszczającego oraz 3. os. lp. czasu przeszłego odnoszącej się do podmiotu o zweryfikowanym `p0_gender` = stuprocentowa zgodność ze zweryfikowanym `p0_gender` postaci w `SeriesBible` / `EpisodeProfiler`, z zachowaniem priorytetu rekordu ontologicznego P0 nad wysokością częstotliwości podstawowej głosu seiyū w `speaker_tags`.
   - **Źródło stanu docelowego:** Rekord P0 (`p0_gender`, `has_verified_gender: true`) w `SeriesBible` / `EpisodeProfiler`.

6. **R1.9 (P0) — Ścisła Separacja Kursywy Całoliniowej Monologu Wewnętrznego od Kursywy Emfatycznej Pojedynczego Wyrazu w Dialogu:**
   - **Definicja pozytywna:** Prawidłowy stan znaczników pochylenia w `phase1_text` i `phase2_text` = dla linii z `is_internal_monologue: true` (przypisanej do stylu pochyłego `Italics` / `Flashback_Italics` lub oznaczonej jako myśl wewnętrzna bez adresata) pojedyncza para znaczników `{\i1}...{\i0}` obejmuje cały tekst wypowiedzi; natomiast dla linii dialogu głośnego z jawnym adresatem i `is_internal_monologue: false` (styl prosty `Default`) tekst zdania pozostaje prosty (bez całoliniowego `{\i1}...{\i0}`), a znaczniki `{\i1}...{\i0}` obejmują wyłącznie pojedynczy wyraz emfatyczny, jeżeli był on wyróżniony tagiem `{\i1}...{\i0}` w `en_text`.
   - **Źródło stanu docelowego:** Sekcja `[Events]` / `[V4+ Styles]`, atrybut `is_internal_monologue`, `phase1_text` oraz `en_text`.

7. **R1.10 (P0) — Ciągłość Składniowa i Interpunkcyjna Zdań Wielokrotnie Złożonych Rozbitych na Sąsiednie Zdarzenia `Dialogue:`:**
   - **Definicja pozytywna:** Prawidłowy stan pary sąsiednich zdarzeń `Dialogue:` tego samego mówcy, w której pierwsze zdarzenie otwiera konstrukcję składniową zakończoną wielokropkiem `...` = pełne domknięcie składniowe w drugim zdarzeniu rozpoczynającym się od wielokropka otwierającego `...` i małej litery, z zachowaniem zgody przypadka gramatycznego i rządu czasownikowego między obiema częściami zdania.
   - **Źródło stanu docelowego:** `phase1_text` oraz jednoznaczny sygnał `en_text`.

### Priorytet P1 (Reguły silne — spójność wielogłosu, wołacza i paradygmatów odmiany)

8. **R1.4 (P1) — Tożsamość Tekstowa Kontynuowanego Wiersza w Dwugłosie (`Dialogue:`):**
   - **Definicja pozytywna:** Prawidłowy stan przekładu dla dwuwierszowego zdarzenia dwugłosu w `phase1_text` i `phase2_text`, w którym pierwszy lub drugi wiersz stanowi w `en_text` powtórzenie kwestii z linii bezpośrednio poprzedzającej = zachowanie w powtórzonym wierszu dwugłosu identycznego sformułowania docelowego jak w linii poprzedzającej (niezależnie od użytego znaku dywizu lub półpauzy `-`, `–`, `—`).
   - **Źródło stanu docelowego:** `phase1_text` oraz `en_text`.

9. **R1.8 (P1) — Pełna Deklinacja Antroponimów Jedno- i Dwuczłonowych w Wołaczu `W` i Przypadkach Zależnych `D..Ms` bez Duplikacji Członów:**
   - **Definicja pozytywna:** Prawidłowy stan antroponimów jedno- i dwuczłonowych (`<IMIE> <NAZWISKO>`) oraz terminów kanonicznych w wołaczu `W` i przypadkach zależnych (`D, C, B, N, Ms`) = pojedyncze, wolne od powtórzeń wystąpienie antroponimu w zdaniu, w pełnej zgodności ortograficznej rdzenia i końcówki fleksyjnej z paradygmatem w `EpisodeProfiler` i `SeriesBible`, wraz z wydzieleniem inicjalnego wołacza `W` przecinkiem od dalszej części zdania.
   - **Źródło stanu docelowego:** Rekord P0 (`EpisodeProfiler` / `SeriesBible`) oraz `phase1_text`.

### Priorytet P2 (Reguły jakościowe — odpowiedniość napisów `is_sign` i higiena raportowania Fazy 2)

10. **R1.5 (P2) — Odpowiedniość Leksykalna 1:1 i Kondensacja Nagłówkowa Napisów Ekranowych `is_sign: true`:**
    - **Definicja pozytywna:** Prawidłowy stan napisów ekranowych `is_sign: true` = ścisła odpowiedniość semantyczna i leksykalna 1:1 wobec `en_text` w poprawnej formie mianownika `M`, a dla krótkotrwałych plansz ($\le 2,5\text{ s}$) zawierających nagłówek z punktorem oraz wielozdaniowy tekst tła — zwięzły przekład samego nagłówka głównego mieszczący się w pojedynczym zdarzeniu czasowym.
    - **Źródło stanu docelowego:** `en_text` oraz rekord P0 (`SeriesBible`).

11. **R1.11 (P2) — Czystość Pola `changes_made` i Separatorów Wiersza `\N` w Odpowiedzi Fazy 2 (`DialogueVerifier`):**
    - **Definicja pozytywna:** Prawidłowy stan odpowiedzi modelu Fazy 2 (`DialogueVerifier`) = stosowanie wyłącznie standardowego separatora wiersza `\N` oraz wartość `changes_made: null` wszędzie tam, gdzie tekst `refined_pl` po znormalizowaniu białych znaków i podziałów wiersza (`\N` $\leftrightarrow$ `" "`) jest tożsamy leksykalnie ze szkicem `f1_pl`.
    - **Źródło stanu docelowego:** Porównanie znormalizowanego `f1_pl` i `refined_pl`.

---

## SEKCJA 2: OPERACJE (2A / 2B / 2C)

### 2A — Operacje potwierdzone z poprzedniego promptu 9.6 (bez nowych akcji)

1. **`2A.1` (z 9.3–9.6) — `DialogueVerifier.enforce_sign_nominative_orthography` (`verifier.py`) oraz ochrona `is_sign` przed dzieleniem w `split_oversized_ass_events` (`translator.py`):** potwierdzona empirycznie (`events_count == total_lines == 260`) — bez nowych akcji.
2. **`2A.2` (z 9.3–9.6) — `EpisodeQualityGate.should_apply_top_alignment_on_collision` (`avt_linter.py`):** potwierdzona empirycznie — bez nowych akcji.
3. **`2A.3` (z 9.5–9.6/2C.1 dla encji P0) — Oczyszczanie nawiasów $F_0$ z `target_actor` w `SceneDiscourseGraph.arbitrate_event_telemetry`, wymuszenie `p0_gender` dla `Mówca:` i `Adresat:` P0, izolacja `Italics`, `Mówca: sign (NEUTRAL)` oraz licznik pre-passu (`scene_discourse.py`, `translator.py`):** potwierdzona empirycznie w 100% dla wszystkich postaci P0 — bez nowych akcji dla encji P0 (doprecyzowanie płci leksykalnej etykiety P2 `Boy`/`Girl` ujęte w `2C.2`).
4. **`2A.4` (z 9.6/2C.2) — Rozróżnienie kursywy całoliniowej (`_is_whole_line_italic`) i częściowej w Kategorii 20 `over_application_italics` (`verifier.py`):** potwierdzona empirycznie w 100% (`ID: 187` i `ID: 26`) — bez nowych akcji.
5. **`2A.5` (z 9.6/2C.3 dla `cjk_count == 0` i partykuł nagłosowych) — Zerowanie segmentów ASR o `cjk_count == 0` oraz wycinanie osieroconych partykuł nagłosowych po prefiksie ASCII (`profiler.py`):** potwierdzona empirycznie w `ID: 3`, `ID: 181` i `ID: 201` — bez nowych akcji w tym zakresie (doprecyzowanie wycinania artefaktów `.? ??000` ujęte w `2C.4`).
6. **`2A.6` (z 9.6/2C.4) — Parser separatora kropki `M.`/`D.` z Kroku 5 (`parse_step5_declension_line`), odmrażanie mianowników męskich w RAM oraz obecność etykiet drugoplanowych w Kroku 6 (`series_memory.py`, `translator.py`):** potwierdzona empirycznie (`characters_count: 29`, 4 paradygmaty męskie P0 w pełni odmienione w Kroku 6) — bez nowych akcji.
7. **`2A.7` (z 9.6/2C.5 dla `\n` $\rightarrow$ `\N`) — Normalizacja małego `\n` do `\N` w `verify_batch` i `_guard_phase2_regressions` (`verifier.py`):** potwierdzona empirycznie (0 wystąpień `\n` w 260/260 rekordach `Faza 2`, `D_pos` i `.ass`) — bez nowych akcji w zakresie `\n` $\rightarrow$ `\N`.

---

### 2B — Nowe operacje

Brak nowych operacji spoza zakresu domknięcia regresji i warunków brzegowych z 9.6 (wszystkie korekty ujęte w Sekcji 2C jako empiryczne rozstrzygnięcia operacji z 9.6).

---

### 2C — Konflikty i regresje z poprzedniego promptu 9.6 (rozstrzygnięte empirycznie: dowód empiryczny > analiza teoretyczna)

#### OPERACJA 2C.1 (z 9.6/2B.1) — Eliminacja kaskadowej duplikacji dwuczłonowych antroponimów P0 (`ID: 48`, `ID: 52`) oraz selektywne przypisywanie aliasów z honoryfikatorem wyłącznie do pasującej fonetycznie encji P0 (`translator.py` + `series_memory.py`)
- **Konflikt / Regresja z 9.6:** W przebiegu po wdrożeniu 9.6 (`BŁĄD 3` w Etapie 1/2):
  1. W `ID: 48` (`0:04:21.55`) i `ID: 52` (`0:04:35.43`) modele Fazy 1 i Fazy 2 zwróciły całkowicie poprawny tekst z odmienionym dwuczłonowym antroponimem (`"co z <RZECZYWISTY_CZŁON_IMIENNY_N_1> <RZECZYWISTY_CZŁON_NAZWISKOWY_1>."` oraz `"z opisem <RZECZYWISTY_CZŁON_IMIENNY_D_1> <RZECZYWISTY_CZŁON_NAZWISKOWY_1>."`), który post-processing z operacji `2B.1` (`translator.py:5785-5800` oraz przed zapisem do `D_pos`) zdeformował przez wielokrotne rozwinięcie aliasów członowych do postaci `"<RZECZYWISTY_CZŁON_IMIENNY_N_1>\N<RZECZYWISTY_ANTROPONIM_DWUCZŁONOWY_1> <RZECZYWISTY_ANTROPONIM_DWUCZŁONOWY_1> <RZECZYWISTY_CZŁON_NAZWISKOWY_1>."` w pliku `.ass`!
  2. W Kroku 6 (`series_memory.py:6224`) aliasy zdrobniałe z tytułu serii (`["<RZECZYWISTY_RDZEŃ_PO_ODCIĘCIU_1>", "<RZECZYWISTY_ALIAS_JAPOŃSKI_1>", "<RZECZYWISTY_ALIAS_JAPOŃSKI_2>"]`) zostały dopisane do tablicy `aliases` **wszystkich 22 postaci P0** zamiast wyłącznie do jedynej encji, której nazwa odpowiada temu zdrobnieniu (`<RZECZYWISTY_ANTROPONIM_1>`).
- **Rozstrzygnięcie (dowód empiryczny > analiza teoretyczna):** **NAPRAWIĆ** `translator.py` oraz `series_memory.py` (zgodnie z Zasadą 3 Primary LLM Translation Authority).
- **Wymóg Phase 0 (Flaga Phase 0.L):** zidentyfikować w `translator.py` wszystkie miejsca wykonujące podmianę aliasów na nazwy z `SeriesBible` oraz w `series_memory.py` miejsce dopisujące aliasy z `title_romaji`.
- **Implementacja:**
  1. **Selektywne dopasowanie aliasu z tytułu serii w `SeriesBible` (`series_memory.py`):**
     W `map_bilingual_role_aliases` / `_sanitize_loaded_bible_in_ram` (`series_memory.py`) **nigdy nie dopisuj** aliasu wyodrębnionego z `title_romaji` (np. `<RZECZYWISTY_ALIAS_JAPOŃSKI_1>` / `<RZECZYWISTY_RDZEŃ_PO_ODCIĘCIU_1>`) do wszystkich postaci w pętli! Przypisz go **wyłącznie** do tej pojedynczej encji w `self.data["characters"]`, której kanoniczna nazwa `char_name` (lub istniejący opis) dzieli z rdzeniem aliasu `<RZECZYWISTY_RDZEŃ_PO_ODCIĘCIU_1>` wspólny prefiks fonetyczny (np. `char_name.lower().startswith(stem.lower()[:2])` przy ` " " not in char_name`, co jednoznacznie wskazuje wyłącznie na `<RZECZYWISTY_ANTROPONIM_1>`). Oczyść w `_sanitize_loaded_bible_in_ram` tablice `aliases` pozostałych postaci P0 z omyłkowo dopisanych obcych aliasów.
  2. **Całkowita blokada rozwijania części składowych antroponimów wieloczłonowych (`translator.py`, `series_memory.py`):**
     - Usuń duplikujące wywołanie podmiany aliasów po `AVTLinter (D_pos)` w `translator.py:5785-5800` — po zakończeniu `AVTLinter` i `EpisodeQualityGate` żaden kod nie może już mutować nazw własnych poza kontrolą `dpos_text` (`ass_text` musi być w 100% zgodny z `dpos_text` po uwzględnieniu jawnie zalogowanych poprawek EQG).
     - W funkcji zamieniającej japoński alias z honoryfikatorem (`-chan` / `-kun`) na kanoniczny paradygmat przy `keep_honorifics: false`:
       - operacja może dotyczyć **wyłącznie** tokenów posiadających wprost sufiks honoryfikatywny (`-chan`, `-kun`, `-sama`, `-san`) lub obciętego rdzenia hipokorystycznego, który **nie jest** częścią składową (`char_name.split()`) żadnego wieloczłonowego antroponimu (`" " in char_name`);
       - jeśli w zdaniu polskim występuje już którykolwiek człon kanonicznej nazwy encji (`any(part.lower() in text.lower() for part in char_name.split())` lub którykolwiek przypadek z `declensions[char_name].values()`), **nigdy nie wykonuj żadnej podmiany** dla tej encji (pełne poszanowanie Primary LLM Translation Authority — w `ID: 48`, `ID: 52` i `ID: 94` modele Fazy 1 i Fazy 2 same wygenerowały bezbłędne formy `"co z <IMIE_N> <NAZWISKO>."`, `"z opisem <IMIE_D> <NAZWISKO>."` oraz `"z ... i <PARADYGMAT_N_1>?"`!).
- **Kryterium akceptacji:** Prawidłowy stan `dpos_text` i `ass_text` dla linii zawierających antroponimy jedno- i dwuczłonowe = pojedyncze, nienaruszone wystąpienie antroponimu zgodne z `phase2_text` (`"co z <IMIE_N> <NAZWISKO>."`, `"z opisem <IMIE_D> <NAZWISKO>."`, `"i <PARADYGMAT_N_1>?"`), stuprocentowa tożsamość tekstowa `ass_text == dpos_text` (po odjęciu tagów usuniętych jawnie przez EQG) oraz przypisanie aliasu hipokorystycznego w Kroku 6 wyłącznie do 1 odpowiadającej mu encji P0 (źródło autorytetu: Zasada 3 Primary LLM Translation Authority, `phase2_text` oraz `SeriesBible`).

#### OPERACJA 2C.2 (z 9.6/2C.1 i 9.6/2C.4) — Inferencja płci leksykalnej dla angielskich etykiet osobowych P2 (`Boy`, `Girl`, `Man`, `Woman`) w `SeriesBible.populate_secondary_actor_tags` (`series_memory.py`)
- **Konflikt z 9.6:** W przebiegu po wdrożeniu 9.6 (`BŁĄD 1` w Etapie 1/2, `ID: 58`) etykiety drugoplanowe dodane przez `populate_secondary_actor_tags` otrzymały w Kroku 6 `"gender": "UNKNOWN"`, przez co dla etykiety `"Boy"` w `ID: 58` (`0:05:02.16`) wyemitowano `Adresat: Boy (FEMININE)`.
- **Rozstrzygnięcie:** **ROZSZERZYĆ** `SeriesBible.populate_secondary_actor_tags` (`series_memory.py`).
- **Wymóg Phase 0 (Flaga Phase 0.M):** sprawdzić słownik leksykalny płci w `metadata.py` / `series_memory.py`.
- **Implementacja:**
  1. W `SeriesBible.populate_secondary_actor_tags` (`series_memory.py`) podczas tworzenia wpisu dla etykiety drugoplanowej sprawdź tokeny składowe nazwy etykiety (po `lower()`):
     - jeśli nazwa zawiera jednoznaczny angielski lub polski rzeczownik męski ze zbioru `{"boy", "man", "men", "guy", "male", "father", "dad", "brother", "son", "uncle", "grandfather", "waiter", "king", "prince", "lord", "chłopiec", "mężczyzna", "chłopak", "ojciec", "brat"}`, ustaw `"gender": "MALE"`, `"grammatical_gender": "MASCULINE"`, `"confidence": 0.90`, `"priority": "P1"`;
     - jeśli nazwa zawiera jednoznaczny rzeczownik żeński ze zbioru `{"girl", "woman", "women", "lady", "female", "mother", "mom", "sister", "daughter", "aunt", "grandmother", "waitress", "queen", "princess", "dziewczyna", "kobieta", "dziewczynka", "matka", "siostra"}`, ustaw `"gender": "FEMALE"`, `"grammatical_gender": "FEMININE"`, `"confidence": 0.90`, `"priority": "P1"`.
- **Kryterium akceptacji:** Prawidłowy stan wpisów drugoplanowych w Kroku 6 oraz w `Telemetria:` Kroku 10 = etykiety `Boy` i `Girl` posiadają w Kroku 6 odpowiednio `"gender": "MALE"` (`MASCULINE`) oraz `"gender": "FEMALE"` (`FEMININE`), a w `ID: 58` w `Telemetria:` widnieje `Adresat: Boy (MASCULINE)` (źródło autorytetu: semantyka leksykalna etykiety w kolumnie `Name` sekcji `[Events]`).

#### OPERACJA 2C.3 (z 9.6/2C.5) — Normalizacja podziału wiersza `\N` względem spacji `" "` przy porównywaniu `f1_pl` i `refined_pl` w `normalize_phase2_line_and_reason` i loggerze konsolowym (`verifier.py` + `translator.py`)
- **Konflikt z 9.6:** W przebiegu po wdrożeniu 9.6 (`BŁĄD 4` w Etapie 1/2) w `przebieg_tłumaczenia_post96.txt` wypisano 3 pozycje `[Redaktor Dialogów]` bez opisu powodu (`Paczka 3 #6`, `#16` oraz `Paczka 2 #13`), w których tekst słowny `Szkic` i `Szlif` był w 100% identyczny, a jedyną różnicą było zastąpienie spacji `" "` znacznikiem łamania wiersza `\N`.
- **Rozstrzygnięcie:** **ROZSZERZYĆ** `DialogueVerifier.normalize_phase2_line_and_reason` (`verifier.py:455`) oraz warunek wypisywania `[Redaktor Dialogów]` w `translator.py:4500`.
- **Wymóg Phase 0 (Flaga Phase 0.N):** sprawdzić funkcję porównującą `f1_pl` i `refined_pl` w `verifier.py` i `translator.py`.
- **Implementacja:**
  1. W funkcji porównującej `_norm_cmp(s)` w `DialogueVerifier.normalize_phase2_line_and_reason` (`verifier.py`) oprócz zdejmowania zewnętrznych tagów `{\i1}...{\i0}` zamieniaj każdy znacznik `\N` (wraz z otaczającymi spacjami `r"\s*\\N\s*"`) na pojedynczą spację `" "` i redukuj wielokrotne spacje `r"\s+"` do `" "`.
  2. Jeśli po takiej normalizacji `_norm_cmp(f1_pl) == _norm_cmp(refined_pl)` (co oznacza, że słowa i interpunkcja nie uległy żadnej zmianie, a zmieniło się co najwyżej miejsce łamania wiersza `\N`), ustaw `changes_made = None` i **pomiń wypisywanie pustego bloku `[Redaktor Dialogów]` w konsoli** w `translator.py`.
- **Kryterium akceptacji:** Prawidłowy stan logu konsolowego w Kroku 9 = `0` wpisów `[Redaktor Dialogów]` pozbawionych uzasadnienia `changes_made`, w tym `0` wpisów dla linii różniących się wyłącznie zamianą spacji `" "` na `\N` (źródło autorytetu: `phase1_text` oraz reguła `R1.11`).

#### OPERACJA 2C.4 (z 9.6/2C.3) — Wycinanie artefaktowych klastrów znaków zapytania i cyfr (`.? ??000`) z japońskiego segmentu w `EpisodeProfiler.sanitize_event_asr` (`profiler.py`)
- **Konflikt z 9.6:** W przebiegu po wdrożeniu 9.6 (`BŁĄD 5` w Etapie 1/2, `ID: 79`) wewnątrz japońskiego segmentu ASR pozostał sklejony nielingwistyczny ciąg `.? ??000` przed partykułą końcową `だよ`.
- **Rozstrzygnięcie:** **ROZSZERZYĆ** wyrażenie regularne w `EpisodeProfiler.sanitize_event_asr` (`profiler.py`).
- **Wymóg Phase 0 (Flaga Phase 0.O):** sprawdzić w `profiler.py:348-431` kolejność czyszczenia `jp_part` przed konwersją do `[romaji]`.
- **Implementacja:**
  1. W `EpisodeProfiler.sanitize_event_asr` (`profiler.py`) na części japońskiej `jp_part` (przed wygenerowaniem `[romaji]`) dodaj wycinanie artefaktowych klastrów złożonych z wielokrotnych znaków zapytania/interpunkcji i zer/cyfr:
     ```python
     jp_part = re.sub(r"[.,!?\s]*\?+[\s?0-9.,!]*", "", jp_part)
     jp_part = re.sub(r"0{2,}", "", jp_part)
     ```
- **Kryterium akceptacji:** Prawidłowy stan pola `JP Audio (Whisper):` w Krokach 4 i 10 = całkowity brak artefaktowych ciągów typu `.? ??000` lub `???000` zarówno w części japońskiej, jak i w sekcji `[romaji]` (źródło autorytetu: Zasada 3 Standardu 9.0).

---

## SEKCJA 3: REGUŁY DLA PIPELINE'U DANYCH

Wszystkie reguły dla pipeline'u danych mają priorytet P0 i są zdefiniowane w pełnej formie pozytywnej (Zasada 2):

1. **R3.1 (P0) — Selektywna Izolacja Aliasów i Pełna Inferencja Płci Etykiet w `SeriesBible` (Kroki 3, 5 i 6):**
   - **Definicja pozytywna:** Prawidłowy stan obiektu `SeriesBible` w pamięci RAM w momencie logowania Kroku 6 = jednoczesne spełnienie pięciu warunków pozytywnych: (a) przypisanie aliasów hipokorystycznych z tytułu serii wyłącznie do pojedynczej encji P0 dzielącej z nimi rdzeń fonetyczny (brak obcych aliasów na listach `aliases` pozostałych postaci), (b) przypisanie jednoznacznej płci `MALE` (`MASCULINE`) lub `FEMALE` (`FEMININE`) angielskim i polskim etykietom rodzajowym (`Boy`, `Girl`, `Man`, `Woman`) w `populate_secondary_actor_tags`, (c) przejęcie wszystkich 7-przypadkowych paradygmatów odmiany z Kroku 5 (`M:` i `M.`), (d) odmrożenie mianowników dla zweryfikowanych antroponimów męskich oraz (e) spójność kierunkowa i rodzajowa każdego wpisu w `relations`.
   - **Źródło stanu docelowego:** Rekord P0 (`EpisodeProfiler` Krok 5), słownik Kroku 3 oraz `SeriesBible`.

2. **R3.2 (P0) — Czystość Nazw i Bezwzględny Prymat Płci P0/P1 w Polach `Mówca:` i `Adresat:` Wektora `Telemetria:` (Kroki 7 i 10):**
   - **Definicja pozytywna:** Prawidłowy stan wektora `Telemetria:` w Kroku 10 = oczyszczenie `raw_actor` i `target_actor` z nawiasowych adnotacji akustycznych $F_0$ (`\s*\([^)]*\)`), stuprocentowa zgodność znaczników `(MASCULINE)` / `(FEMININE)` z płcią encji w `SeriesBible` zarówno dla postaci P0, jak i dla etykiet P1/P2 (`Boy` $\rightarrow$ `MASCULINE`, `Girl` $\rightarrow$ `FEMININE`), brak zewnętrznego adresata na liniach `is_internal_monologue: true` oraz znacznik `(NEUTRAL)` dla `Mówca: sign`.
   - **Źródło stanu docelowego:** Sekcja `[Events]` oraz rekord P0/P1 w `SeriesBible`.

3. **R3.3 (P0) — Ochrona Formatowania `\N`, Kursywy i Spójności Porównań na Granicy Fazy 1 i Fazy 2 (Kroki 8, 9 i 10):**
   - **Definicja pozytywna:** Prawidłowy stan wyjścia `DialogueVerifier.verify_batch` i loggera konsolowego = zamiana wszystkich znaków nowej linii na `\N`, traktowanie linii różniących się wyłącznie zamianą spacji `" "` na `\N` jako tożsamych leksykalnie (`changes_made = None`, brak pustego wpisu w `[Redaktor Dialogów]`) oraz zdjęcie całoliniowej kursywy `{\i1}...{\i0}` z głośnego dialogu (`is_internal_monologue: false`) gdy `source_en` nie jest w całości pochylone.
   - **Źródło stanu docelowego:** Rekord P0, `phase1_text`, `en_text` oraz sekcja `[V4+ Styles]`.

4. **R3.4 (P0) — Nienaruszalność Wieloczłonowych Antroponimów P0 i Tożsamość `ass_text == dpos_text` (Krok 11):**
   - **Definicja pozytywna:** Prawidłowy stan wyjściowego strumienia `[Events]` po zakończeniu Kroku 11 = całkowity brak duplikacji członów jedno- i wieloczłonowych antroponimów (`<IMIE> <NAZWISKO>`), ścisła tożsamość treści słownej `ass_text == dpos_text` we wszystkich 260 rekordach odcinka, zachowanie każdego napisu ekranowego `is_sign` jako pojedynczego zdarzenia (`events_count == total_lines`) oraz pełne wylistowanie poprawek EQG z `consistency_check: OK`.
   - **Źródło stanu docelowego:** Zasada 3 Primary LLM Translation Authority, `dpos_text` oraz `SeriesBible`.

5. **R3.5 (P0) — Czystość Bufora ASR od Tokenów Bez CJK, Osieroconych Partykuł i Artefaktów Cyfrowo-Interpunkcyjnych (Krok 4):**
   - **Definicja pozytywna:** Prawidłowy stan bufora `asr_text` po wykonaniu `EpisodeProfiler.sanitize_event_asr` = wyzerowanie (`""`) każdego segmentu o `len(cjk_chars) <= 1`, wycięcie prefiksów ASCII wraz z osieroconą partykułą nagłosową (`と`, `の`, `は`, `が`, `を`, `に`, `へ`, `で`), wycięcie artefaktowych klastrów znaków zapytania i cyfr (`.? ??000`) oraz deduplikacja czasowa i seryjna.
   - **Źródło stanu docelowego:** Zasada 3 Standardu 9.0 (`en_text` jako autorytet) oraz alfabet japoński CJK.

---

## SEKCJA 4: KOLEJNOŚĆ WDROŻENIA

1. **ETAP WDROŻENIOWY 1 (Faza 0 — Weryfikacja kodu i flag 0.L–0.O):**
   - Przeczytanie plików z listy P0.1, zlokalizowanie dokładnych linii dla flag `Phase 0.L–0.O` i wypełnienie tabel P0.2 oraz P0.3 w `Raport_wdrozenia_9.7.md`.
2. **ETAP WDROŻENIOWY 2 (Operacja `2C.1` — Naprawa duplikacji dwuczłonowego antroponimu w `translator.py` i selektywne przypisanie aliasów w `series_memory.py`):**
   - Usunięcie destrukcyjnej podmiany pojedynczych członów wieloczłonowych antroponimów przed `D_pos` i w `translator.py:5785-5800` oraz ograniczenie dopisywania aliasów z tytułu serii w `series_memory.py` wyłącznie do pasującej fonetycznie encji jednoczłonowej.
3. **ETAP WDROŻENIOWY 3 (Operacja `2C.2` — Inferencja płci leksykalnej etykiet P2 `Boy` / `Girl` w `populate_secondary_actor_tags`):**
   - Rozszerzenie `SeriesBible.populate_secondary_actor_tags` o rozpoznawanie płci z angielskich i polskich rzeczowników osobowych.
4. **ETAP WDROŻENIOWY 4 (Operacje `2C.3` i `2C.4` — Normalizacja `\N` vs spacja w `normalize_phase2_line_and_reason` i wycinanie `.? ??000` w `sanitize_event_asr`):**
   - Wdrożenie normalizacji `r"\s*\\N\s*"` $\rightarrow$ `" "` przy porównywaniu `f1_pl` i `refined_pl` oraz dodanie regexu wycinającego `.? ??000` w `profiler.py`.
5. **ETAP WDROŻENIOWY 5 (Implementacja testów `T7.1–T7.4`, walidacja CI/CD oraz weryfikacja empiryczna 6C):**
   - Dodanie testów `T7.1–T7.4`, uruchomienie `pytest` (fast + full) i 4 bramek CI/CD oraz weryfikacja empiryczna na odcinku audytowanym potwierdzająca naprawę `ID: 48` i `ID: 52` przy zachowaniu 100% napraw z wersji 9.5 i 9.6.

---

## SEKCJA 5: WALIDACJA TESTOWA I WARUNEK UKOŃCZENIA

### 5A — Walidacja testowa

#### 1. Infrastruktura testowa (stan bazowy po Depuracji Legacy 1.0 i wersji 9.6, commit `c87b22f`)
- **Pliki testowe jednostkowe (domyślne):** `tests/test_avt_linter.py`, `tests/test_verifier.py`, `tests/test_series_memory.py`, `tests/test_discourse_and_translator.py`, `tests/test_metadata.py`, `tests/test_profiler.py`, `tests/test_translator.py`, `tests/test_flight_recorder.py` oraz testy `KEEP` w `test_system.py` (łącznie **195 testów bazowych** w trybie `komenda_fast`, wykonywanych w ~20,18 s).
- **Pliki testowe zarchiwizowane:** `tests/archive/test_legacy_manifest.py` (wykluczone przez `norecursedirs` w `pytest.ini` — pozostają nietknięte).
- **Komendy testowe:**
  - `komenda_fast` = `pytest` (uruchamia testy z `addopts = -v --tb=short -m "not slow and not network"`, czas wykonania $< 60\text{ s}$)
  - `komenda_full` = `pytest -m ""` (uruchamia wszystkie testy jednostkowe, `slow` i `network` — 348 testów bazowych + nowe testy 9.7)
  - `komenda_slow` = `pytest -m slow` (153 testy)
  - `komenda_network` = `pytest -m network` (12 testów)
- **Bramki CI/CD:** `verify_purity.py`, `verify_ultimate_pipeline.py`, `verify_12_fixes.py`, `audit_diff.ps1`.

#### 2. Wykaz nowych testów `T7.1–T7.4` jako wzorce strukturalne z `@pytest.mark.parametrize` i placeholderami `<RZECZYWISTY_*>`

Wszystkie 4 testy mają kategorię markera `unit` (wchodzą do domyślnego przebiegu `komenda_fast`):

| ID testu | Punkt Sekcji 2 | Plik testowy | Nazwa testu | Kategoria markera | Kryterium akceptacji (forma pozytywna + źródło autorytetu) |
|---|---|---|---|---|---|
| **T7.1** | **2C.1** | `tests/test_series_memory.py` | `test_multi_token_anthroponym_immunity_against_component_alias_duplication_and_selective_title_alias` | `unit` | Prawidłowy stan tekstu z dwuczłonowym antroponimem `<IMIE_N/D> <NAZWISKO>` = brak duplikacji członów (100% zachowania formy z Fazy 2) oraz przypisanie aliasu z `-chan` wyłącznie do pasującej fonetycznie encji jednoczłonowej. |
| **T7.2** | **2C.2** | `tests/test_discourse_and_translator.py` | `test_populate_secondary_actor_tags_infers_lexical_gender_for_boy_and_girl_tags` | `unit` | Prawidłowy stan `populate_secondary_actor_tags` i `arbitrate_event_telemetry` = przypisanie `MALE`/`MASCULINE` dla etykiety `<RZECZYWISTA_ETYKIETA_MĘSKA_P2_1>` oraz `FEMALE`/`FEMININE` dla `<RZECZYWISTA_ETYKIETA_ŻEŃSKA_P2_1>`. |
| **T7.3** | **2C.3** | `tests/test_verifier.py` | `test_normalize_phase2_treats_space_to_ass_newline_wrapping_as_lexical_identity` | `unit` | Prawidłowy stan `normalize_phase2_line_and_reason` = zachowanie `\N` w `refined_pl` przy jednoczesnym zwróceniu flagi braku zmiany leksykalnej (`changes_made is None`), gdy `f1_pl` i `refined_pl` różnią się wyłącznie spacją vs `\N`. |
| **T7.4** | **2C.4** | `tests/test_profiler.py` | `test_sanitize_event_asr_strips_question_mark_and_zero_clusters_inside_jp_segment` | `unit` | Prawidłowy stan `sanitize_event_asr` = całkowite wycięcie artefaktu `<RZECZYWISTY_ARTEFAKT_CYFROWY_ASR_1>` sklejonego ze zdaniem japońskim przy zachowaniu znaków CJK. |

##### Wzorce strukturalne testów `T7.1–T7.4` (do adaptacji po Phase 0):

```python
import pytest

# WZORZEC T7.1 (Operacja 2C.1) -> tests/test_series_memory.py
@pytest.mark.parametrize(
    "source_en,f2_pl,expected_final_pl",
    [
        (
            "<RZECZYWISTY_CIĄG_EN_1> <RZECZYWISTY_ANTROPONIM_DWUCZŁONOWY_1>.",
            "{\\i1}<RZECZYWISTY_CIĄG_PL_1>,\\Nco z <RZECZYWISTY_CZŁON_IMIENNY_N_1> <RZECZYWISTY_CZŁON_NAZWISKOWY_1>.{\\i0}",
            "{\\i1}<RZECZYWISTY_CIĄG_PL_1>,\\Nco z <RZECZYWISTY_CZŁON_IMIENNY_N_1> <RZECZYWISTY_CZŁON_NAZWISKOWY_1>.{\\i0}",
        ),
        (
            "<RZECZYWISTY_CIĄG_EN_2> <RZECZYWISTY_ANTROPONIM_DWUCZŁONOWY_1>.",
            "{\\i1}<RZECZYWISTY_CIĄG_PL_2>\\Nz opisem <RZECZYWISTY_CZŁON_IMIENNY_D_1> <RZECZYWISTY_CZŁON_NAZWISKOWY_1>.{\\i0}",
            "{\\i1}<RZECZYWISTY_CIĄG_PL_2>\\Nz opisem <RZECZYWISTY_CZŁON_IMIENNY_D_1> <RZECZYWISTY_CZŁON_NAZWISKOWY_1>.{\\i0}",
        ),
    ],
)
def test_multi_token_anthroponym_immunity_against_component_alias_duplication_and_selective_title_alias(
    source_en, f2_pl, expected_final_pl
):
    from series_memory import SeriesBible

    bible = SeriesBible(slug="test_multi_token_immunity")
    bible.sync_verified_profile_entity(
        "<RZECZYWISTY_ANTROPONIM_DWUCZŁONOWY_1>",
        "FEMALE",
        has_verified_gender=True,
        declension_map={
            "M": "<RZECZYWISTY_ANTROPONIM_DWUCZŁONOWY_1>",
            "D": "<RZECZYWISTY_CZŁON_IMIENNY_D_1> <RZECZYWISTY_CZŁON_NAZWISKOWY_1>",
            "N": "<RZECZYWISTY_CZŁON_IMIENNY_N_1> <RZECZYWISTY_CZŁON_NAZWISKOWY_1>",
        },
    )
    bible.sync_verified_profile_entity(
        "<RZECZYWISTY_ANTROPONIM_1>",
        "MALE",
        has_verified_gender=True,
        declension_map={"M": "<RZECZYWISTY_ANTROPONIM_1>", "N": "<RZECZYWISTY_PARADYGMAT_N_1>"},
    )
    bible.sync_verified_profile_entity("<RZECZYWISTY_ANTROPONIM_2>", "MALE", has_verified_gender=True)
    bible.map_bilingual_role_aliases(["<RZECZYWISTY_ALIAS_JAPOŃSKI_1>"])

    assert "<RZECZYWISTY_ALIAS_JAPOŃSKI_1>" not in bible.data["characters"]["<RZECZYWISTY_ANTROPONIM_2>"]["aliases"]
    assert "<RZECZYWISTY_ALIAS_JAPOŃSKI_1>" not in bible.data["characters"]["<RZECZYWISTY_ANTROPONIM_DWUCZŁONOWY_1>"]["aliases"]

    out_pl = bible.apply_canonical_alias_declension(text=f2_pl, source_en=source_en, keep_honorifics=False)
    assert out_pl == expected_final_pl
    assert out_pl.count("<RZECZYWISTY_CZŁON_NAZWISKOWY_1>") == 1


# WZORZEC T7.2 (Operacja 2C.2) -> tests/test_discourse_and_translator.py
@pytest.mark.parametrize(
    "secondary_tag,expected_gender,expected_grammatical_gender",
    [
        ("<RZECZYWISTA_ETYKIETA_MĘSKA_P2_1>", "MALE", "<WARTOŚĆ_ENUM_TECHNICZNA_1>"),
        ("<RZECZYWISTA_ETYKIETA_ŻEŃSKA_P2_1>", "FEMALE", "<WARTOŚĆ_ENUM_TECHNICZNA_2>"),
    ],
)
def test_populate_secondary_actor_tags_infers_lexical_gender_for_boy_and_girl_tags(
    secondary_tag, expected_gender, expected_grammatical_gender
):
    from series_memory import SeriesBible
    from scene_discourse import SceneDiscourseGraph

    bible = SeriesBible(slug="test_secondary_lexical_gender")
    bible.populate_secondary_actor_tags([secondary_tag])
    char_entry = bible.get_character(secondary_tag)
    assert char_entry is not None
    assert char_entry.get("gender") == expected_gender
    assert char_entry.get("grammatical_gender") == expected_grammatical_gender

    res = SceneDiscourseGraph.arbitrate_event_telemetry(
        raw_actor="<RZECZYWISTY_ANTROPONIM_ŻEŃSKI_1>",
        target_actor=secondary_tag,
        series_bible=bible,
        is_internal_monologue=False,
    )
    assert res.get("addressee_gender") == expected_grammatical_gender


# WZORZEC T7.3 (Operacja 2C.3) -> tests/test_verifier.py
@pytest.mark.parametrize(
    "f1_pl,f2_pl_with_linebreak,raw_reason,expected_changes_made",
    [
        (
            "<RZECZYWISTY_CIĄG_PL_1> <RZECZYWISTY_CIĄG_PL_2>",
            "<RZECZYWISTY_CIĄG_PL_1>\\N<RZECZYWISTY_CIĄG_PL_2>",
            None,
            None,
        ),
        (
            "{\\i1}<RZECZYWISTY_CIĄG_PL_1> <RZECZYWISTY_CIĄG_PL_2>{\\i0}",
            "{\\i1}<RZECZYWISTY_CIĄG_PL_1>\\N<RZECZYWISTY_CIĄG_PL_2>{\\i0}",
            None,
            None,
        ),
    ],
)
def test_normalize_phase2_treats_space_to_ass_newline_wrapping_as_lexical_identity(
    f1_pl, f2_pl_with_linebreak, raw_reason, expected_changes_made
):
    from verifier import DialogueVerifier

    norm_pl, norm_reason = DialogueVerifier.normalize_phase2_line_and_reason(
        f1_pl=f1_pl, refined_pl=f2_pl_with_linebreak, changes_made=raw_reason
    )
    assert "\\N" in norm_pl
    assert norm_reason is expected_changes_made
    assert DialogueVerifier.is_lexically_identical_ignoring_linebreak(f1_pl, norm_pl) is True


# WZORZEC T7.4 (Operacja 2C.4) -> tests/test_profiler.py
@pytest.mark.parametrize(
    "raw_asr_with_artifact,expected_clean_asr",
    [
        (
            "<RZECZYWISTY_CIĄG_EN_1><RZECZYWISTY_ARTEFAKT_CYFROWY_ASR_1><RZECZYWISTY_CIĄG_EN_2>",
            "<RZECZYWISTY_CIĄG_EN_1><RZECZYWISTY_CIĄG_EN_2>",
        ),
        (
            "<RZECZYWISTY_CIĄG_EN_1>???000",
            "<RZECZYWISTY_CIĄG_EN_1>",
        ),
    ],
)
def test_sanitize_event_asr_strips_question_mark_and_zero_clusters_inside_jp_segment(
    raw_asr_with_artifact, expected_clean_asr
):
    from profiler import EpisodeProfiler

    cleaned = EpisodeProfiler.sanitize_event_asr(raw_asr_with_artifact, is_sign=False)
    assert "000" not in cleaned
    assert "??" not in cleaned
    assert cleaned == expected_clean_asr
```

#### 3. Warunek ukończenia wdrożenia (definicja pozytywna — punkty (a)–(p))
Prawidłowy stan ukończenia wdrożenia wersji **9.7** = jednoczesne spełnienie szesnastu warunków pozytywnych (a)–(p):
- **(a)** Wszystkie operacje z Sekcji 2A (`2A.1–2A.7`) utrzymane w stanie nienaruszonym;
- **(b)** Brak regresji w operacjach wdrożonych w wersjach 9.4–9.6;
- **(c)** Wszystkie operacje z Sekcji 2C (`2C.1–2C.4`) w pełni wdrożone w runtime;
- **(d)** Wszystkie reguły z Sekcji 1 (`R1.1–R1.11`) i Sekcji 3 (`R3.1–R3.5`) zachowane w czystej formie pozytywnej;
- **(e)** Wszystkie 4 nowe testy jednostkowe (`T7.1–T7.4`) zaimplementowane i sparametryzowane ($\ge 2$ warianty każdy);
- **(f)** `komenda_fast` (`pytest`): 100% PASSED ($\ge 203$ instancje testowe), `0 FAILED`, `0 ERROR`, czas wykonania $< 60\text{ s}$;
- **(g)** `komenda_full` (`pytest -m ""`): 100% PASSED ($\ge 356$ instancji testowych), `0 FAILED`, `0 ERROR`;
- **(h)** `komenda_slow` (`pytest -m slow`) oraz `komenda_network` (`pytest -m network`): 100% PASSED;
- **(i)** Bramki CI/CD (`verify_purity.py`, `verify_ultimate_pipeline.py`, `verify_12_fixes.py`) zwracają 100% PASS;
- **(j)** `audit_diff.ps1` zwraca status VICTORY CONFIRMED;
- **(k)** Phase 0 ukończona z wypełnionymi tabelami P0.2 i P0.3 oraz rozstrzygniętymi flagami `Phase 0.L–0.O` w `Raport_wdrozenia_9.7.md`;
- **(l)** Każdy nowy test `T7.1–T7.4` zweryfikowany empirycznie pod kątem falsyfikowalności i wolny od anty-wzorców `D1–D6` (w tym `D6.a–D6.e`);
- **(m)** **Walidacja empiryczna (obowiązkowa):** po wdrożeniu zmian wykonano weryfikację na odcinku audytowanym i potwierdzono w Sekcji 6C pliku `Raport_wdrozenia_9.7.md` utrzymanie 4 wyeliminowanych błędów z 9.6 oraz pełne wyeliminowanie regresji w `ID: 48` i `ID: 52` (`0` duplikacji członów antroponimu dwuczłonowego, selektywne przypisanie aliasu hipokorystycznego wyłącznie do 1 encji P0, `Adresat: Boy (MASCULINE)` w `ID: 58`, `0` pustych wpisów `[Redaktor Dialogów]` dla `\N` vs spacja oraz `0` artefaktów `.? ??000` w `ID: 79`);
- **(n)** Żaden ze 195 testów domyślnych (116 `KEEP` z Depuracji 1.0 + 79 instancji z 9.4, 9.5 i 9.6) nie został usunięty ani osłabiony;
- **(o)** Katalog `tests/archive/` oraz 3 gałęzie `# DEFENSIVE_FALLBACK` w `avt_linter.py` pozostają nietknięte;
- **(p)** Wszystkie pola `<DO_WYPEŁNIENIA_*>` w pliku `Raport_wdrozenia_9.7.md` zostały wypełnione (`0` niewypełnionych placeholderów), a plik `Raport_wdrozenia_9.6.md` został zaktualizowany o rzeczywisty hash commita `c87b22f`, status audytowy i Sekcję 12.

### 5B — Obowiązek wypełnienia Raportu Wdrożenia (DELIVERABLE)

Po zakończeniu implementacji, walidacji testowej i walidacji empirycznej agent kodujący ma bezwzględny obowiązek wypełnienia wszystkich pól `<DO_WYPEŁNIENIA_*>` w pliku:
`C:\Users\Piotrek\Desktop\translator\Artefakty\Raport_wdrozenia_9.7.md`
oraz zaktualizowania statusu i Sekcji 12 w pliku `Raport_wdrozenia_9.6.md`.

---

## SEKCJA 6: ZAKAZY ARCHITEKTONICZNE (RYGORY WDROŻENIOWE 9.7)

1. **ZAKAZ 1 (Zakaz Mutacji Tekstu Poza `AVTLinter` i `EpisodeQualityGate`):** Niedopuszczalne jest modyfikowanie tekstu `dpos_text` w drodze do zapisu `.ass` przez jakiekolwiek dodatkowe pętle regexowe nieodnotowane w `dpos_text` i raporcie Kroku 11 (`ass_text` musi wynikać wyłącznie z `dpos_text` i jawnych operacji EQG).
2. **ZAKAZ 2 (Zakaz Podmiany Członów Antroponimów Wieloczłonowych):** Niedopuszczalne jest zastępowanie pojedynczego imienia lub nazwiska będącego członem składowym dwuczłonowego antroponimu (`<IMIE> <NAZWISKO>`) pełną nazwą dwuczłonową.
3. **ZAKAZ 3 (Zakaz Globalnego Dopisywania Aliasów Tytułowych do Wszystkich Postaci):** Niedopuszczalne jest dopisywanie aliasów wyodrębnionych z tytułu serii do postaci, których nazwa kanoniczna nie dzieli rdzenia fonetycznego z tym aliasem.
4. **ZAKAZ 4 (Zakaz Test-Only Wiring i Mockowania Logiki Domenowej):** Testy `T7.1–T7.4` muszą wywoływać rzeczywiste metody produkcyjne bez użycia `unittest.mock.patch` na logice domenowej.
5. **ZAKAZ 5 (Zakaz Pomijania Phase 0 i Walidacji Empirycznej 6C):** Niedopuszczalne jest zamknięcie wdrożenia bez rozstrzygnięcia flag `Phase 0.L–0.O` i bez potwierdzenia naprawy `ID: 48` i `ID: 52` w Sekcji 6C raportu.
6. **ZAKAZ 6 (Zakaz Naruszania Testów KEEP z Depuracji 1.0 i 9.4–9.6):** Żaden ze 195 testów domyślnych ani 153 testów `MARK_SLOW` nie może zostać usunięty lub osłabiony (`D6.d`, `D6.e`).
7. **ZAKAZ 7 (Zakaz Modyfikacji Gałęzi DEFENSIVE_FALLBACK i `tests/archive/`):** 3 gałęzie `# DEFENSIVE_FALLBACK` w `avt_linter.py` oraz katalog `tests/archive/` pozostają całkowicie nietknięte (`D6.a`, `D6.c`).
8. **ZAKAZ 8 (Zakaz Pozostawiania Placeholderów w Raporcie):** W zapisanym pliku `Raport_wdrozenia_9.7.md` liczba wystąpień ciągu `DO_WYPEŁNIENIA` musi wynosić dokładnie `0`, a pola `Commit wdrożenia` i `Status wdrożenia` muszą zawierać finalny commit hash i status (zakaz pozostawiania `HEAD` / `W TOKU`).
9. **ZAKAZ 9 (Zakaz Modyfikacji Plików Danych i Napisów — Zero-Cosmetic Gate):** Pliki `*_bible.json` oraz pliki `.ass`/`.log` z baseline nie mogą być ręcznie modyfikowane jako substytut naprawy kodu w Pythonie.
10. **ZAKAZ 10 (Zakaz Wycieku Literalnego — Zero-Literal Gate):** Zarówno kod `.py`, testy `tests/test_*.py`, jak i treść raportu `Raport_wdrozenia_9.7.md` muszą być w 100% wolne od literalnych cytatów i nazw własnych z audytowanego odcinka.