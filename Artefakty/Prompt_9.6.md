# Plik: C:\Users\Piotrek\Desktop\translator\Artefakty\Prompt_9.6.md

# PROMPT NAPRAWCZY POTOKU AVT — WERSJA 9.6

## PREAMBUŁA

Dokument definiuje operacje kodowe, regułowe i walidacyjne rozszerzające potok AVT z wersji 9.5 (commit `97d742c` / `80d30e5`[cite: 19]) oraz utrzymujące stan po Depuracji Legacy 1.0 (commit `474fb64`[cite: 12, 19]) do wersji **9.6**. Podstawa empiryczna: audyt weryfikacyjny przebiegu odcinka testowego po wdrożeniu wersji 9.5 (Etap 1/2), który potwierdził pełne wyeliminowanie błędów rodzaju gramatycznego mówców (`Mówca:` w `Telemetria:` = 100% zgodności z P0 w 259/259 liniach dialogowych), ochronę plansz ekranowych przed rozbijaniem (`events_count == total_lines == 260`), naprawę ciągłości wielokropka i pisowni wołacza `W`, a jednocześnie zidentyfikował **5 resztkowych kategorii błędów brzegowych**:
1. **Kategoria Błędu 1 (Skażenie pola `Adresat:` w `Telemetria:` przez nawiasowe sufiksy akustyczne $F_0$ oraz licznik pre-passu):** przekazywanie do `SceneDiscourseGraph.arbitrate_event_telemetry` parametru `target_actor` ze sklejonym w nawiasie opisem akustycznym $F_0$ (np. `"<RZECZYWISTY_ANTROPONIM_MĘSKI_1> (<OPIS_F0_ŻEŃSKI>)"`), co uniemożliwia odnalezienie czystego klucza `"<RZECZYWISTY_ANTROPONIM_MĘSKI_1>"` w `SeriesBible`, a także emisja pozornego adresata na liniach monologu wewnętrznego (`Style: Italics`), emisja płci osobowej dla etykiety technicznej `sign` oraz raportowanie `0` kwestii żeńskich w komunikacie `[Pre-pass Sceniczny Odcinka]`.
2. **Kategoria Błędu 2 (Rozszerzenie pojedynczego pochylonego wyrazu z `en_text` na całoliniową kursywę w Fazie 2):** brak rozróżnienia w Kategorii 20 (`over_application_italics`) w `DialogueVerifier._guard_phase2_regressions` między częściowym pochyleniem emfatycznym jednego wyrazu w `en_text` a całoliniową kursywą `{\i1}...{\i0}` nałożoną przez Fazę 2 na głośny dialog (`Style: Default`, `is_internal_monologue: false`) z jawnym adresatem.
3. **Kategoria Błędu 3 (Odcięcie honoryfikatora z japońskiego aliasu imienia do nieodmienionego rdzenia zamiast podstawienia kanonicznego paradygmatu z `SeriesBible`, separator kropki `M.` w Kroku 5 oraz populacja Kroku 3 $\rightarrow$ Krok 6):** (a) użycie w przekładzie japońskiego wariantu z honoryfikatorem (`<RZECZYWISTY_ALIAS_JAPOŃSKI_1>`) dla encji posiadającej w `en_text` i `SeriesBible` kanoniczny antroponim (`<RZECZYWISTY_ANTROPONIM_1>`), które po mechanicznym obcięciu sufiksu `-chan` przy `keep_honorifics: false` pozostawia w `.ass` nieodmieniony, obcięty rdzeń (`<RZECZYWISTY_RDZEŃ_PO_ODCIĘCIU_1>`) zamiast odmienionej formy narzędnika `N` (`<RZECZYWISTY_PARADYGMAT_N_1>`); (b) pominięcie przez parser Kroku 6 paradygmatów wygenerowanych w Kroku 5 z separatorem kropki (`M. <ANTROPONIM>, D. <FORMA_D>`), co pozostawia zamrożone mianowniki dla części antroponimów męskich w Kroku 6; (c) nadpisanie lub pominięcie encji drugoplanowych z `populate_secondary_actor_tags` przed logowaniem Kroku 6.
4. **Kategoria Błędu 4 (Brak normalizacji małego znaku nowej linii `\n` do `\N` na wyjściu Fazy 2 przed zapisem `dpos_text` i logowaniem konsolowym):** pozostawienie małego `\n` w `phase2_text` i `dpos_text` w części paczek Fazy 2, co generuje w konsoli puste wpisy `[Redaktor Dialogów]` dla linii identycznych leksykalnie (różniących się wyłącznie `\N` vs `\n`).
5. **Kategoria Błędu 5 (Przepuszczenie segmentu ASR o `0` znaków CJK oraz osieroconej partykuły nagłosowej po odcięciu prefiksu ASCII):** pozostawienie w `EpisodeProfiler.sanitize_event_asr` pojedynczego słowa łacińskiego ASCII bez żadnego znaku japońskiego (`cjk_count == 0`) oraz pozostawienie na samym początku japońskiego segmentu jednoznakowej partykuły enklitycznej (`と`, `の`, `は`, `が`, `を`, `に`, `へ`, `で`), która była sklejona z usuniętym jednoliterowym prefiksem ASCII.

Niniejszy dokument przestrzega czterech nadrzędnych zasad Standardu 9.0 oraz rozszerzeń Standardu 9.3–9.6:
1. **Zero-Literal (Zasada 1)** — wszystkie reguły, opisy operacji, uzasadnienia systemowe i kryteria akceptacji operują wyłącznie na kategoriach językowych, semiotycznych i metajęzykowych architektury oraz placeholderach `<RZECZYWISTY_*>`.
2. **Pure Positive Domain Invariant (Zasada 2)** — każda reguła w Sekcji 1 i Sekcji 3 oraz każde kryterium akceptacji w Sekcji 2 i Sekcji 5 definiuje zbiór dopuszczalnych stanów docelowych w formie pozytywnej („prawidłowy stan = X", „zachowuje…", „obejmuje wyłącznie…", „ma pierwszeństwo wobec…"). Stany spoza zdefiniowanego zbioru są niepoprawne z definicji.
3. **Primary LLM Translation Authority (Zasada 3)** — pierwotne tłumaczenie Fazy 1 (`phase1_text`) jest nadrzędnym autorytetem translacyjnym; etapy późniejsze (Faza 2, post-processing offline) wnoszą wartość wyłącznie przez weryfikację stylistyczną i higienę techniczną, a każda zmiana formy względem `phase1_text` opiera się na twardym dowodzie z rekordu P0 (`p0_gender`, `has_verified_gender: true`) lub jednoznacznym sygnale źródłowym `en_text` / `pronouns_en`.
4. **Instance-Free Metalinguistic Architecture (Zasada 4)** — architektura operuje na kategoriach modułów, funkcji, operatorów i operacji; opisy natury modułów są kategoriopochodne i uniwersalne.
5. **Ochrona nienaruszalności Depuracji Legacy 1.0 (Zasada 16)** — wdrożenie wersji 9.6 zachowuje w 100% stan po Depuracji 1.0 i wersji 9.5: wszystkie 182 testy domyślne (`KEEP` + jednostkowe 9.4 i 9.5) pozostają aktywne w przebiegu `pytest`, markery `@pytest.mark.slow` (153 testy) i `@pytest.mark.network` (12 testów) pozostają nienaruszone, katalog `tests/archive/` pozostaje nietknięty, a 3 chronione gałęzie `# DEFENSIVE_FALLBACK` w `avt_linter.py` zachowują swoją postać i komentarze.

Numer wersji: **9.6**. Poprzednia wersja toru naprawczego: **9.5**. Wersja toru Depuracji Legacy w tle: **1.0** (commit `474fb64`).

---

## IDENTYFIKATORY METAJĘZYKA ARCHITEKTURY

- **Nazwy modułów i klas:** `avt_linter.py`, `verifier.py`, `series_memory.py`, `profiler.py`, `rules.py`, `translator.py`, `scene_discourse.py`, `metadata.py`, `flight_recorder.py`, `pipeline_logger.py`, `sign_detector.py`, `AVTLinter`, `EpisodeQualityGate`, `EpisodeFlightRecorder`, `DialogueVerifier`, `SeriesBible`, `EpisodeProfiler`, `SceneDiscourseGraph`, `RuleDispatcher`, `VisualSignDetector`, `MultimodalTranslator`.
- **Nazwy funkcji i metod:** `lint_and_fix_line`, `audit_and_fix_entire_episode`, `_run_phase_7_hygiene`, `normalize_ass_tags_and_sign_layout`, `should_apply_top_alignment_on_collision`, `arbitrate_event_telemetry`, `build_discourse_topology`, `_guard_phase2_regressions`, `verify_batch`, `enforce_sign_nominative_orthography`, `_sanitize_loaded_bible_in_ram`, `sync_verified_profile_entity`, `_validate_relation_entry_consistency`, `preserve_italics_for_upright_style`, `reconcile_prepass_with_p0`, `profile_episode`, `_extract_f0_contour`, `sanitize_event_asr`, `report_step_11_quality_gate`, `log_quality_gate_and_pricing`, `get_all_fixes`, `get_active_rules`, `detect_signs`, `synchronize_ass_event_metadata_and_styles`, `build_phase1_prompt`, `_prepare_batch_prompt`, `_translate_batch`, `_precompute_episode_scene_genders`, `populate_secondary_actor_tags`, `map_bilingual_role_aliases`, `align_vocative_orthography`, `generate_polish_name_declension`, `clean_anime_filename`, `normalize_anime_slug`.
- **Nazwy kroków i faz:** Krok 0–11, Faza 0 (higiena), Faza 0 (Phase 0 — czytanie kodu), Faza 1 (tłumaczenie), Faza 2 (weryfikacja), post-processing.
- **Enum values i pola schematu:** `MALE`, `FEMALE`, `UNKNOWN`, `NEUTRAL`, `MASCULINE`, `FEMININE`, `VIRILE`, `NON_VIRILE`, `POLYLOGUE`, `CHÓR`, `ANTHROPONYM`, `is_sign`, `is_internal_monologue`, `has_verified_gender`, `speaker_name`, `target_actor`, `target_gender`, `addressee_gender`, `p0_gender`, `en_text`, `dpos_text`, `phase1_text`, `phase2_text`, `ass_text`, `telemetry`, `prosody_tags`, `speaker_tags`, `pronouns_en`, `priority`, `confidence`, `P0`, `P1`, `P2`, `strict_positive_domain`, `changes_made`, `refined_pl`, `f1_pl`, `asr_text`, `keep_honorifics`, `M`, `D`, `C`, `B`, `N`, `Ms`, `W`.
- **Znaczniki formatu ASS:** `[Script Info]`, `[V4+ Styles]`, `[Events]`, `Dialogue:`, `\N`, `\n`, `{\...}`, `\an7`, `\an8`, `\an9`, `\pos(x,y)`, `\move(x1,y1,x2,y2)`, `\fad(t1,t2)`, `\3c`, `\1c`, `\bord`, `\shad`, `\i1`, `\i0`, `\blur`, `\fn`, `\fs`, `\frz`.
- **Placeholdery testowe i metajęzykowe:** `<RZECZYWISTY_ANTROPONIM_1>`, `<RZECZYWISTY_ANTROPONIM_2>`, `<RZECZYWISTY_ANTROPONIM_MĘSKI_1>`, `<RZECZYWISTY_ANTROPONIM_ŻEŃSKI_1>`, `<RZECZYWISTY_ALIAS_JAPOŃSKI_1>`, `<RZECZYWISTY_RDZEŃ_PO_ODCIĘCIU_1>`, `<RZECZYWISTY_TOKEN_ASCII_1>`, `<RZECZYWISTA_PARTYKUŁA_NAGŁOSOWA_1>`, `<RZECZYWISTA_PARTYKUŁA_NAGŁOSOWA_2>`, `<RZECZYWISTY_CIĄG_PL_1>`, `<RZECZYWISTY_CIĄG_PL_2>`, `<RZECZYWISTY_CIĄG_EN_1>`, `<RZECZYWISTY_CIĄG_EN_2>`, `<RZECZYWISTY_KOLOR_HEX_1>`, `<RZECZYWISTA_POZYCJA_POS_1>`, `<RZECZYWISTY_PARADYGMAT_M_1>`, `<RZECZYWISTY_PARADYGMAT_D_1>`, `<RZECZYWISTY_PARADYGMAT_N_1>`, `<RZECZYWISTY_PARADYGMAT_W_1>`, `<WARTOŚĆ_ENUM_TECHNICZNA_1>`, `<WARTOŚĆ_ENUM_TECHNICZNA_2>`.

---

## FAZA 0 — CZYTANIE KODU (OBOWIĄZKOWA)

Przed wprowadzeniem jakiejkolwiek zmiany w kodzie agent kodujący ma bezwzględny obowiązek wykonania Fazy 0 i udokumentowania jej wyników w sekcji `2. PHASE 0 — WYNIK WERYFIKACJI KODU` pliku `C:\Users\Piotrek\Desktop\translator\Artefakty\Raport_wdrozenia_9.6.md`. Brak wypełnionej Fazy 0 stanowi naruszenie Standardu 9.3–9.6.

### P0.1. Lista plików do przeczytania w całości i weryfikacji ścieżek wywołań runtime
1. `scene_discourse.py` — pełna inspekcja metody `SceneDiscourseGraph.arbitrate_event_telemetry` (w szczególności sposobu odbierania i przetwarzania argumentów `target_actor`, `target_gender`, `is_internal_monologue`, `is_sign` oraz formatowania bloku `Adresat:` w zwracanym słowniku i ciągu `dry_telemetry`).
2. `translator.py` — pełna inspekcja:
   - miejsc wywołania `arbitrate_event_telemetry` w `_prepare_batch_prompt` i `_translate_batch` (skąd pochodzi wartość przekazywana jako `target_actor` i dlaczego zawiera doklejony w nawiasie opis akustyczny $F_0$),
   - funkcji `_precompute_episode_scene_genders` (w którym momencie wypisywany jest komunikat `[Pre-pass Sceniczny Odcinka]: Wykryto ciągłość obsady dla ... kwestii (... żeńskich, ... męskich)` i dlaczego zlicza `0 żeńskich`),
   - funkcji parsującej sekcję `Odmiana Imion i Tytułów` z wyjścia Kroku 5 (`EpisodeProfiler`) i przekazującej mapy odmiany do `SeriesBible.sync_verified_profile_entity` w Kroku 6 (dlaczego pomija wpisy ze skrótami przypadków zakończonymi kropką `M.`, `D.`, `C.`, `B.`, `N.`, `Ms.`, `W.`),
   - miejsca wywołania `populate_secondary_actor_tags` pomiędzy Krokiem 3 a Krokiem 6 (dlaczego dodane etykiety drugoplanowe znikają przed logowaniem `Rejestr postaci` w Kroku 6),
   - logiki usuwania honoryfikatorów (`keep_honorifics: false`) w post-processingu oraz mapowania aliasów japońskich na kanoniczne paradygmaty w `SeriesBible`,
   - logiki wyświetlania zmian `[Redaktor Dialogów]` w konsoli podczas Kroku 9.
3. `verifier.py` — pełna inspekcja `DialogueVerifier.verify_batch` (moment normalizacji znaków nowej linii `\n` $\rightarrow$ `\N` w `r.refined_pl`) oraz `DialogueVerifier._guard_phase2_regressions` (Kategoria 20 `over_application_italics` — zachowanie w sytuacji, gdy `source_en` ma kursywę tylko wokół pojedynczego słowa emfatycznego, a `refined_pl` otacza kursywą całe zdanie).
4. `profiler.py` — pełna inspekcja `EpisodeProfiler.sanitize_event_asr` (warunek zerowania segmentu przy `cjk_count == 0` oraz usuwanie osieroconych jednoznakowych partykuł japońskich na samym początku segmentu po wycięciu sklejonego prefiksu ASCII).
5. `series_memory.py` — pełna inspekcja `SeriesBible._sanitize_loaded_bible_in_ram`, `SeriesBible.sync_verified_profile_entity`, `SeriesBible.populate_secondary_actor_tags`, `SeriesBible.get_character` oraz słowników aliasów.
6. `avt_linter.py` — weryfikacja higieny końcowej i nienaruszalności 3 chronionych gałęzi `# DEFENSIVE_FALLBACK`.

### P0.2. Tabela mapowania plan ↔ kod (szablon obowiązkowy do wypełnienia w `Raport_wdrozenia_9.6.md`)

Dla każdej operacji z Sekcji 2B i 2C agent kodujący wypełnia w `Raport_wdrozenia_9.6.md` poniższą tabelę:

| Operacja (sekcja 9.6) | Miejsce wywołania / metoda w planie | Rzeczywiste miejsce wywołania w kodzie (plik + linia + metoda) | Rzeczywista sygnatura w kodzie | Zgodność | Uwagi / Rozstrzygnięcie |
|---|---|---|---|---|---|
| 2B.1 | Mapowanie aliasu z honoryfikatorem na kanoniczny paradygmat `SeriesBible` przy `keep_honorifics: false` (`series_memory.py`, `translator.py`, `avt_linter.py`) | `<DO_WYPEŁNIENIA_PRZEZ_AGENTA_KODUJĄCEGO>` | `<DO_WYPEŁNIENIA_PRZEZ_AGENTA_KODUJĄCEGO>` | `<DO_WYPEŁNIENIA_PRZEZ_AGENTA_KODUJĄCEGO>` | `<DO_WYPEŁNIENIA_PRZEZ_AGENTA_KODUJĄCEGO>` |
| 2C.1 | Oczyszczanie nawiasów $F_0$ z `target_actor` w `SceneDiscourseGraph.arbitrate_event_telemetry` + licznik pre-passu (`scene_discourse.py`, `translator.py`) | `<DO_WYPEŁNIENIA_PRZEZ_AGENTA_KODUJĄCEGO>` | `<DO_WYPEŁNIENIA_PRZEZ_AGENTA_KODUJĄCEGO>` | `<DO_WYPEŁNIENIA_PRZEZ_AGENTA_KODUJĄCEGO>` | `<DO_WYPEŁNIENIA_PRZEZ_AGENTA_KODUJĄCEGO>` |
| 2C.2 | Rozróżnienie kursywy całoliniowej i częściowej w Kategorii 20 `over_application_italics` (`verifier.py`) | `<DO_WYPEŁNIENIA_PRZEZ_AGENTA_KODUJĄCEGO>` | `<DO_WYPEŁNIENIA_PRZEZ_AGENTA_KODUJĄCEGO>` | `<DO_WYPEŁNIENIA_PRZEZ_AGENTA_KODUJĄCEGO>` | `<DO_WYPEŁNIENIA_PRZEZ_AGENTA_KODUJĄCEGO>` |
| 2C.3 | Zerowanie segmentów o `cjk_count == 0` oraz usuwanie osieroconych partykuł nagłosowych po prefiksie ASCII w `EpisodeProfiler.sanitize_event_asr` (`profiler.py`) | `<DO_WYPEŁNIENIA_PRZEZ_AGENTA_KODUJĄCEGO>` | `<DO_WYPEŁNIENIA_PRZEZ_AGENTA_KODUJĄCEGO>` | `<DO_WYPEŁNIENIA_PRZEZ_AGENTA_KODUJĄCEGO>` | `<DO_WYPEŁNIENIA_PRZEZ_AGENTA_KODUJĄCEGO>` |
| 2C.4 | Parser separatora kropki `M.`/`D.` z Kroku 5, odmrażanie mianowników w RAM oraz trwałość `populate_secondary_actor_tags` w Kroku 6 (`series_memory.py`, `translator.py`) | `<DO_WYPEŁNIENIA_PRZEZ_AGENTA_KODUJĄCEGO>` | `<DO_WYPEŁNIENIA_PRZEZ_AGENTA_KODUJĄCEGO>` | `<DO_WYPEŁNIENIA_PRZEZ_AGENTA_KODUJĄCEGO>` | `<DO_WYPEŁNIENIA_PRZEZ_AGENTA_KODUJĄCEGO>` |
| 2C.5 | Normalizacja `\n` $\rightarrow$ `\N` na wejściu `DialogueVerifier.verify_batch` przed `dpos_text` i logiem konsolowym (`verifier.py`, `translator.py`) | `<DO_WYPEŁNIENIA_PRZEZ_AGENTA_KODUJĄCEGO>` | `<DO_WYPEŁNIENIA_PRZEZ_AGENTA_KODUJĄCEGO>` | `<DO_WYPEŁNIENIA_PRZEZ_AGENTA_KODUJĄCEGO>` | `<DO_WYPEŁNIENIA_PRZEZ_AGENTA_KODUJĄCEGO>` |

### P0.3. Tabela mapowania danych testowych (szablon z placeholderami obowiązkowy w `Raport_wdrozenia_9.6.md`)

Przed implementacją testów `T6.1–T6.5` agent kodujący wypełnia w `Raport_wdrozenia_9.6.md` tabelę mapowania wszystkich placeholderów na wartości z odcinka testowego (innego niż odcinek audytowany, zgodnie z Zasadą 9 i 13):

| Placeholder | Wartość rzeczywista (z odcinka testowego, spoza audytu) | Źródło (P0 / EN / ASS) | Uwagi |
|---|---|---|---|
| `<RZECZYWISTY_ANTROPONIM_1>` | `<DO_WYPEŁNIENIA_MAPOWANIE_P0_3>` | P0 (`SeriesBible`) | Encja kanoniczna posiadająca alias z honoryfikatorem |
| `<RZECZYWISTY_ANTROPONIM_2>` | `<DO_WYPEŁNIENIA_MAPOWANIE_P0_3>` | P0 (`SeriesBible`) | Druga encja kanoniczna |
| `<RZECZYWISTY_ANTROPONIM_MĘSKI_1>` | `<DO_WYPEŁNIENIA_MAPOWANIE_P0_3>` | P0 (`SeriesBible`) | Postać męska P0 (`MALE`) |
| `<RZECZYWISTY_ANTROPONIM_ŻEŃSKI_1>` | `<DO_WYPEŁNIENIA_MAPOWANIE_P0_3>` | P0 (`SeriesBible`) | Postać żeńska P0 (`FEMALE`) |
| `<RZECZYWISTY_ALIAS_JAPOŃSKI_1>` | `<DO_WYPEŁNIENIA_MAPOWANIE_P0_3>` | EN / Audio | Wariant zdrobniały z honoryfikatorem `-chan`/`-kun` |
| `<RZECZYWISTY_RDZEŃ_PO_ODCIĘCIU_1>` | `<DO_WYPEŁNIENIA_MAPOWANIE_P0_3>` | KOD | Rdzeń powstały po odcięciu sufiksu `-chan` |
| `<RZECZYWISTY_TOKEN_ASCII_1>` | `<DO_WYPEŁNIENIA_MAPOWANIE_P0_3>` | ASR | Halucynowany pojedynczy wyraz angielski (`cjk_count == 0`) |
| `<RZECZYWISTA_PARTYKUŁA_NAGŁOSOWA_1>` | `<DO_WYPEŁNIENIA_MAPOWANIE_P0_3>` | ASR | Osierocona partykuła japońska (`と` / `の`) po prefiksie ASCII |
| `<RZECZYWISTY_CIĄG_PL_1>` | `<DO_WYPEŁNIENIA_MAPOWANIE_P0_3>` | F1 / PL | Pierwszy ciąg polski w asercjach |
| `<RZECZYWISTY_CIĄG_PL_2>` | `<DO_WYPEŁNIENIA_MAPOWANIE_P0_3>` | F1 / PL | Drugi ciąg polski w asercjach |
| `<RZECZYWISTY_CIĄG_EN_1>` | `<DO_WYPEŁNIENIA_MAPOWANIE_P0_3>` | EN | Zdanie angielskie z pojedynczym słowem w `{\i1}...{\i0}` |
| `<RZECZYWISTY_CIĄG_EN_2>` | `<DO_WYPEŁNIENIA_MAPOWANIE_P0_3>` | EN | Drugie zdanie angielskie |
| `<RZECZYWISTY_PARADYGMAT_M_1>` | `<DO_WYPEŁNIENIA_MAPOWANIE_P0_3>` | P0 (`declensions`) | Forma mianownika `M` |
| `<RZECZYWISTY_PARADYGMAT_D_1>` | `<DO_WYPEŁNIENIA_MAPOWANIE_P0_3>` | P0 (`declensions`) | Forma dopełniacza `D` |
| `<RZECZYWISTY_PARADYGMAT_N_1>` | `<DO_WYPEŁNIENIA_MAPOWANIE_P0_3>` | P0 (`declensions`) | Forma narzędnika `N` |
| `<RZECZYWISTY_PARADYGMAT_W_1>` | `<DO_WYPEŁNIENIA_MAPOWANIE_P0_3>` | P0 (`declensions`) | Forma wołacza `W` |
| `<WARTOŚĆ_ENUM_TECHNICZNA_1>` | `<DO_WYPEŁNIENIA_MAPOWANIE_P0_3>` | KOD | Wartość techniczna (`MASCULINE` / `FEMININE`) |
| `<WARTOŚĆ_ENUM_TECHNICZNA_2>` | `<DO_WYPEŁNIENIA_MAPOWANIE_P0_3>` | KOD | Druga wartość techniczna |

### P0.4. Weryfikacja flag Phase 0 (nowe flagi weryfikacyjne 0.G–0.K dla wersji 9.6)

Agent kodujący odpowiada w sekcji `2.4` pliku `Raport_wdrozenia_9.6.md` na pięć konkretnych pytań weryfikacyjnych:

1. **FLAGA PHASE 0.G (Skażenie `target_actor` nawiasami $F_0$ w `arbitrate_event_telemetry` oraz licznik pre-passu):**
   - *Pytanie weryfikacyjne:* W których liniach `translator.py` i `scene_discourse.py` konstruowany jest ciąg `target_actor` przekazywany do `SceneDiscourseGraph.arbitrate_event_telemetry` (np. `"<ANTROPONIM> (Kobieta)"` lub `"<ANTROPONIM> (Mężczyzna - Scena Wyłącznie Męska)"`), dlaczego `series_bible.get_character(target_actor)` otrzymywał nieoczyszczony ciąg z nawiasem oraz dlaczego funkcja `_precompute_episode_scene_genders` wypisywała `(0 żeńskich, 96 męskich)` mimo obecności zweryfikowanych postaci żeńskich P0?
2. **FLAGA PHASE 0.H (Rozróżnienie kursywy całoliniowej i częściowej w Kategorii 20 `over_application_italics`):**
   - *Pytanie weryfikacyjne:* Jak dokładnie brzmi obecny warunek Kategorii 20 w `DialogueVerifier._guard_phase2_regressions` (`verifier.py`) i dlaczego przepuścił przypadek, w którym `source_en` ma kursywę tylko wokół pojedynczego zaimka wewnątrz zdania, `f1_pl` nie ma żadnej kursywy, a `refined_pl` otacza znacznikami `{\i1}...{\i0}` całą wypowiedź na stylu `Default` (`is_internal_monologue: false`)?
3. **FLAGA PHASE 0.I (Obsługa separatora kropki `M.` / `D.` z Kroku 5, odmrażanie mianowników i trwałość `populate_secondary_actor_tags`):**
   - *Pytanie weryfikacyjne:* Jakiego wyrażenia regularnego używa parser wyciągający sekcję `Odmiana Imion i Tytułów` z tekstu profilu Kroku 5 (`EpisodeProfiler`), dlaczego pominął wpisy ze skrótami przypadków zakończonymi kropką (`M. ..., D. ...`), dlaczego wywołanie `populate_secondary_actor_tags` z Kroku 3 nie zachowało swoich wpisów w słowniku `characters` logowanym w Kroku 6 oraz jak post-processing przy `keep_honorifics: false` obsługuje japońskie aliasy z honoryfikatorem (`-chan`) odpowiadające encjom z `SeriesBible`?
4. **FLAGA PHASE 0.J (Moment normalizacji `\n` $\rightarrow$ `\N` w `DialogueVerifier.verify_batch`):**
   - *Pytanie weryfikacyjne:* W której linii `verifier.py` / `translator.py` wykonywana jest normalizacja znaków nowej linii na `r.refined_pl` i dlaczego w części paczek Fazy 2 do `dpos_text` oraz do porównania konsolowego `[Redaktor Dialogów]` trafił surowy znak `\n` zamiast `\N`?
5. **FLAGA PHASE 0.K (Warunek `cjk_count == 0` oraz osierocone partykuły nagłosowe w `EpisodeProfiler.sanitize_event_asr`):**
   - *Pytanie weryfikacyjne:* Dlaczego warunek sprawdzający liczbę znaków CJK w `EpisodeProfiler.sanitize_event_asr` (`profiler.py`) przepuścił pojedynczy token czysto łaciński (`cjk_count == 0`) oraz w jaki sposób wycięcie jednoliterowego prefiksu ASCII na początku segmentu pozostawiło osieroconą japońską partykułę łączącą (`と`, `の`) na pozycji pierwszego znaku zdania?

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

6. **R1.9 (P0) — ŚcisłaSeparacja Kursywy Całoliniowej Monologu Wewnętrznego od Kursywy Emfatycznej Pojedynczego Wyrazu w Dialogu:**
   - **Definicja pozytywna:** Prawidłowy stan znaczników pochylenia w `phase1_text` i `phase2_text` = dla linii z `is_internal_monologue: true` (przypisanej do stylu pochyłego `Italics` / `Flashback_Italics` lub oznaczonej jako myśl wewnętrzna bez adresata) pojedyncza para znaczników `{\i1}...{\i0}` obejmuje cały tekst wypowiedzi; natomiast dla linii dialogu głośnego z jawnym adresatem i `is_internal_monologue: false` (styl prosty `Default`) tekst zdania pozostaje prosty (bez całoliniowego `{\i1}...{\i0}`), a znaczniki `{\i1}...{\i0}` obejmują wyłącznie pojedynczy wyraz emfatyczny, jeżeli był on wyróżniony tagiem `{\i1}...{\i0}` w `en_text`.
   - **Źródło stanu docelowego:** Sekcja `[Events]` / `[V4+ Styles]`, atrybut `is_internal_monologue`, `phase1_text` oraz `en_text`.

7. **R1.10 (P0) — Ciągłość Składniowa i Interpunkcyjna Zdań Wielokrotnie Złożonych Rozbitych na Sąsiednie Zdarzenia `Dialogue:`:**
   - **Definicja pozytywna:** Prawidłowy stan pary sąsiednich zdarzeń `Dialogue:` tego samego mówcy, w której pierwsze zdarzenie otwiera konstrukcję składniową zakończoną wielokropkiem `...` = pełne domknięcie składniowe w drugim zdarzeniu rozpoczynającym się od wielokropka otwierającego `...` i małej litery, z zachowaniem zgody przypadka gramatycznego i rządu czasownikowego między obiema częściami zdania.
   - **Źródło stanu docelowego:** `phase1_text` oraz jednoznaczny sygnał `en_text`.

### Priorytet P1 (Reguły silne — spójność wielogłosu, wołacza i paradygmatów odmiany)

8. **R1.4 (P1) — Tożsamość Tekstowa Kontynuowanego Wiersza w Dwugłosie (`Dialogue:`):**
   - **Definicja pozytywna:** Prawidłowy stan przekładu dla dwuwierszowego zdarzenia dwugłosu w `phase1_text` i `phase2_text`, w którym pierwszy lub drugi wiersz stanowi w `en_text` powtórzenie kwestii z linii bezpośrednio poprzedzającej = zachowanie w powtórzonym wierszu dwugłosu identycznego sformułowania docelowego jak w linii poprzedzającej (niezależnie od użytego znaku dywizu lub półpauzy `-`, `–`, `—`).
   - **Źródło stanu docelowego:** `phase1_text` oraz `en_text`.

9. **R1.8 (P1) — Pełna Deklinacja Antroponimów i Terminów Kanonicznych w Wołaczu `W` i Przypadkach Zależnych `D..Ms`:**
   - **Definicja pozytywna:** Prawidłowy stan antroponimów i terminów kanonicznych w wołaczu `W` oraz w przypadkach zależnych (`D, C, B, N, Ms`) = pełna zgodność ortograficzna rdzenia (w tym podwojonych spółgłosek) oraz końcówki fleksyjnej z paradygmatem w `EpisodeProfiler` i `SeriesBible`, wraz z wydzieleniem inicjalnego wołacza `W` przecinkiem od dalszej części zdania.
   - **Źródło stanu docelowego:** Rekord P0 (`EpisodeProfiler` / `SeriesBible`) oraz `phase1_text`.

### Priorytet P2 (Reguły jakościowe — odpowiedniość napisów `is_sign` i higiena raportowania Fazy 2)

10. **R1.5 (P2) — Odpowiedniość Leksykalna 1:1 i Kondensacja Nagłówkowa Napisów Ekranowych `is_sign: true`:**
    - **Definicja pozytywna:** Prawidłowy stan napisów ekranowych `is_sign: true` = ścisła odpowiedniość semantyczna i leksykalna 1:1 wobec `en_text` w poprawnej formie mianownika `M`, a dla krótkotrwałych plansz ($\le 2,5\text{ s}$) zawierających nagłówek z punktorem oraz wielozdaniowy tekst tła — zwięzły przekład samego nagłówka głównego mieszczący się w pojedynczym zdarzeniu czasowym.
    - **Źródło stanu docelowego:** `en_text` oraz rekord P0 (`SeriesBible`).

11. **R1.11 (P2) — Czystość Pola `changes_made` i Separatorów Wiersza `\N` w Odpowiedzi Fazy 2 (`DialogueVerifier`):**
    - **Definicja pozytywna:** Prawidłowy stan odpowiedzi modelu Fazy 2 (`DialogueVerifier`) = stosowanie wyłącznie standardowego separatora wiersza `\N` oraz wartość `changes_made: null` wszędzie tam, gdzie znormalizowany tekst `refined_pl` jest tożsamy leksykalnie i znacznikowo z `f1_pl`.
    - **Źródło stanu docelowego:** Porównanie znormalizowanego `f1_pl` i `refined_pl`.

---

## SEKCJA 2: OPERACJE (2A / 2B / 2C)

### 2A — Operacje potwierdzone z poprzedniego promptu 9.5 (bez nowych akcji)

1. **`2A.1` (z 9.3–9.5) — `DialogueVerifier.enforce_sign_nominative_orthography` (`verifier.py`):** potwierdzona empirycznie w `.ass` i `.log` — bez nowych akcji.
2. **`2A.2` (z 9.3–9.5) — `EpisodeQualityGate.should_apply_top_alignment_on_collision` (`avt_linter.py`):** potwierdzona empirycznie (0 fałszywych podniesień `\an8` na liniach ze stylem `Main - Top`) — bez nowych akcji.
3. **`2A.3` (z 9.3–9.5) — Dopasowanie pełnotokenowe w normalizacji etykiet aktorów (`metadata.py`):** potwierdzona empirycznie — bez nowych akcji.
4. **`2A.4` (z 9.3–9.5) — `EpisodeQualityGate.preserve_italics_for_upright_style` (`avt_linter.py`, `translator.py`):** potwierdzona empirycznie — bez nowych akcji.
5. **`2A.5` (z 9.4–9.5) — Ochrona przecinka po inicjalnym wołaczu `W` przed partykułą pytajną `czy` (`avt_linter.py`, `series_memory.py`):** potwierdzona empirycznie w `.ass` — bez nowych akcji.
6. **`2A.6` (z 9.4–9.5) — Sanitacja nieznanych pseudotagów szablonowych w blokach `{\...}` (`avt_linter.py`):** potwierdzona empirycznie w `.ass` — bez nowych akcji.
7. **`2A.7` (z 9.4–9.5) — Pełna lista poprawek `get_all_fixes()` i spójność raportu Kroku 11 (`flight_recorder.py`, `avt_linter.py`):** potwierdzona empirycznie w `.log` (`77/77`, `spójność: OK`) — bez nowych akcji.
8. **`2A.8` (z 9.5/2B.2, 9.5/2C.1 dla `Mówca:`, 9.5/2C.2, 9.5/2C.5, 9.5/2C.6 dla Fazy 1):** prymat `p0_gender` w polu `Mówca:` (259/259 linii zgodnych z P0), ochrona napisów `Name: sign` i `\pos()` przed dzieleniem w `split_oversized_ass_events` (`events_count == total_lines == 260`), mostkowanie wielokropka po grupie imiennej, wyrównanie pisowni podwojonych spółgłosek w wołaczu `W` (`align_vocative_orthography`) oraz deterministyczne otaczanie `phase1_text` parą `{\i1}...{\i0}` dla stylu `Italics` — potwierdzone empirycznie w `.ass` i `.log`, bez nowych akcji w tym zakresie.

---

### 2B — Nowe operacje (ochrona kanonicznego paradygmatu przy usuwaniu honoryfikatorów z aliasów japońskich)

#### OPERACJA 2B.1 — Mapowanie japońskich aliasów zdrobniałych z honoryfikatorem (`-chan`/`-kun`) na kanoniczny paradygmat fleksyjny `SeriesBible` przy `keep_honorifics: false`
- **Źródło:** audyt empiryczny odcinka po wdrożeniu 9.5 (`WYKRYTY BŁĄD 3`).
- **Lokalizacja:** `series_memory.py` (`SeriesBible.map_bilingual_role_aliases`, `SeriesBible._sanitize_loaded_bible_in_ram`), `translator.py` (usuwanie honoryfikatorów przy `keep_honorifics: false` oraz post-processing Fazy 1/2) oraz `avt_linter.py`.
- **Natura modułu:** deterministyczny z kontekstem (ochrona spójności onomastycznej P0).
- **Rozstrzygnięcie:** **NAPRAWIĆ**.
- **Wymóg Phase 0 (Flaga Phase 0.I):** zidentyfikować w `translator.py` / `avt_linter.py` funkcję usuwającą sufiksy `-chan`, `-kun`, `-san`, `-sama` przy fladze `keep_honorifics: false`, która przekształciła w `dpos_text` $\rightarrow$ `ass_text` formę `<RZECZYWISTY_ALIAS_JAPOŃSKI_1>` na nieodmieniony rdzeń `<RZECZYWISTY_RDZEŃ_PO_ODCIĘCIU_1>`, podczas gdy w `en_text` występował kanoniczny antroponim `<RZECZYWISTY_ANTROPONIM_1>` posiadający w `SeriesBible.data["declensions"]` pełny paradygmat `M..W` (w tym narzędnik `N: <RZECZYWISTY_PARADYGMAT_N_1>`).
- **Uzasadnienie systemowe:** Gdy w `en_text` występuje kanoniczna nazwa własna encji (`<RZECZYWISTY_ANTROPONIM_1>`), a w japońskim audio pada jej fonetyczny odpowiednik z honoryfikatorem (`<RZECZYWISTY_ALIAS_JAPOŃSKI_1>`), mechaniczne odcięcie sufiksu `-chan` w post-processingu tworzy niekanoniczny, urwany rdzeń (`<RZECZYWISTY_RDZEŃ_PO_ODCIĘCIU_1>`), który łamie spójność nazewniczą odcinka i powoduje rozjazd `ass_text != dpos_text`.
- **Implementacja:**
  1. W `SeriesBible` (`series_memory.py`): gdy w `self.data["characters"]` i `self.data["declensions"]` istnieje kanoniczna encja P0 (np. `<RZECZYWISTY_ANTROPONIM_1>`), a w tytule serii (`title_romaji`) lub w transkrypcji występuje jej japoński wariant z honoryfikatorem (`<RZECZYWISTY_ALIAS_JAPOŃSKI_1>`), zarejestruj `<RZECZYWISTY_ALIAS_JAPOŃSKI_1>` oraz obcięty rdzeń `<RZECZYWISTY_RDZEŃ_PO_ODCIĘCIU_1>` jako aliasy wskazujące na kanoniczną encję `<RZECZYWISTY_ANTROPONIM_1>`.
  2. W `translator.py` / `verifier.py`: przed przekazaniem tekstu z Fazy 1/2 do `dpos_text` (oraz w funkcji usuwającej honoryfikatory przy `keep_honorifics: false`), jeśli `source_en` zawiera kanoniczną nazwę `<RZECZYWISTY_ANTROPONIM_1>`, a tekst polski zawiera alias `<RZECZYWISTY_ALIAS_JAPOŃSKI_1>` lub obcięty rdzeń `<RZECZYWISTY_RDZEŃ_PO_ODCIĘCIU_1>`:
     - po przyimkach rządzących narzędnikiem (`z`, `ze`, `przed`, `nad`, `pod`, `za`, `między`) oraz po spójniku współrzędnym (`i`, `oraz`, `ani`) łączącym ten antroponim z poprzedzającym rzeczownikiem w narzędniku (np. `z <RZECZYWISTY_CIĄG_PL_1> i <ALIAS>`), podstaw formę narzędnika `N` (`<RZECZYWISTY_PARADYGMAT_N_1>`) ze słownika `SeriesBible.data["declensions"][<RZECZYWISTY_ANTROPONIM_1>]`;
     - w pozycji mianownika podstaw kanoniczną formę `M` (`<RZECZYWISTY_PARADYGMAT_M_1>`), zapewniając pełną tożsamość `ass_text == dpos_text`.
- **Kryterium akceptacji:** Prawidłowy stan `phase1_text`, `phase2_text`, `dpos_text` i `ass_text` dla każdej linii zawierającej w `en_text` kanoniczny antroponim z `SeriesBible` przy `keep_honorifics: false` = użycie wyłącznie kanonicznego paradygmatu fleksyjnego `M..W` z `SeriesBible.data["declensions"]` oraz pełna tożsamość `ass_text == dpos_text` (źródło autorytetu: `en_text` oraz rekord P0 w `SeriesBible`).

---

### 2C — Konflikty z poprzednim promptem 9.5 (rozstrzygnięte empirycznie: dowód empiryczny > analiza teoretyczna)

#### OPERACJA 2C.1 (z 9.5/2B.1 i 9.5/2C.1) — Oczyszczanie nawiasowych sufiksów $F_0$ z `target_actor` w `SceneDiscourseGraph.arbitrate_event_telemetry`, higiena `Adresat:` na monologach i szyldach oraz uzgodnienie licznika pre-passu (`scene_discourse.py` + `translator.py`)
- **Konflikt z 9.5:** W przebiegu po wdrożeniu 9.5 (`WYKRYTY BŁĄD 1`) pole `Mówca:` osiągnęło 100% zgodności z P0, lecz pole `Adresat:` w ponad 120 liniach wyemitowało fałszywą płeć typu `Adresat: <RZECZYWISTY_ANTROPONIM_MĘSKI_1> (Kobieta) (FEMININE)` oraz `Adresat: <RZECZYWISTY_ANTROPONIM_ŻEŃSKI_1> (Mężczyzna) (MASCULINE)`, ponieważ `target_actor` przekazywany do `arbitrate_event_telemetry` zawierał już doklejony w nawiasie opis akustyczny $F_0$ (`"<ANTROPONIM> (Kobieta)"`).
- **Rozstrzygnięcie (dowód empiryczny > analiza teoretyczna):** **ROZSZERZYĆ** `SceneDiscourseGraph.arbitrate_event_telemetry` (`scene_discourse.py`) oraz `_precompute_episode_scene_genders` (`translator.py`).
- **Wymóg Phase 0 (Flaga Phase 0.G):** potwierdzić w `scene_discourse.py:530` oraz `translator.py:3045, 3954` dokładny kształt stringa przekazywanego w argumencie `target_actor`.
- **Implementacja:**
  1. **Oczyszczanie `target_actor` i `raw_actor` z adnotacji nawiasowych za pomocą poprawnego wyrażenia regularnego:**
     Na samym początku `SceneDiscourseGraph.arbitrate_event_telemetry` (przed jakimkolwiek wywołaniem `series_bible.get_character(...)` lub sprawdzeniem słowników P0) oczyść `target_actor` (oraz `raw_actor`) ze wszystkich segmentów nawiasowych za pomocą wyrażenia dopasowującego dosłowny nawias otwierający `\(`, dowolny ciąg znaków niebędących nawiasem zamykającym `[^)]*` oraz dosłowny nawias zamykający `\)`:
     ```python
     clean_target_actor = re.sub(r"\s*\([^)]*\)", "", str(target_actor or "")).strip()
     clean_target_actor = re.sub(r"\s{2,}", " ", clean_target_actor)
     ```
     *Uzasadnienie wyrażenia regularnego:* konstrukcja `\s*\([^)]*\)` gwarantuje dopasowanie pełnego nawiasu okrągłego wraz z całą jego zawartością (w tym słów ze spacjami i myślnikami wewnątrz nawiasu), a globalne zastąpienie `re.sub` usuwa zarówno pojedyncze, jak i wielokrotne nawiasy na końcu oraz w środku ciągu.
  2. **Weryfikacja na 4 przypadkach brzegowych (obowiązkowa):**
     - Przypadek 1 (nawias końcowy prosty): `"<RZECZYWISTY_ANTROPONIM_MĘSKI_1> (Kobieta)"` $\rightarrow$ `"<RZECZYWISTY_ANTROPONIM_MĘSKI_1>"`.
     - Przypadek 2 (nawias końcowy złożony z myślnikiem): `"<RZECZYWISTY_ANTROPONIM_MĘSKI_1> (Mężczyzna - Scena Wyłącznie Męska)"` $\rightarrow$ `"<RZECZYWISTY_ANTROPONIM_MĘSKI_1>"`.
     - Przypadek 3 (nawias w środku ciągu): `"<RZECZYWISTY_ANTROPONIM_1> (<ALIAS>) <RZECZYWISTY_ANTROPONIM_2>"` $\rightarrow$ `"<RZECZYWISTY_ANTROPONIM_1> <RZECZYWISTY_ANTROPONIM_2>"`.
     - Przypadek 4 (wielokrotne nawiasy): `"<RZECZYWISTY_ANTROPONIM_ŻEŃSKI_1> (Mężczyzna) (MASCULINE)"` $\rightarrow$ `"<RZECZYWISTY_ANTROPONIM_ŻEŃSKI_1>"`.
  3. **Bezwzględne nadpisanie płci adresata z rekordu P0 po oczyszczeniu nazwy:**
     Dla niepustego `clean_target_actor` pobierz encję przez `series_bible.get_character(clean_target_actor)` (z uwzględnieniem dwujęzycznych aliasów oraz `episode_profiler`):
     - jeśli encja posiada zweryfikowane `gender == "MALE"`, ustaw bezwarunkowo `target_gender = "MASCULINE"` i sformatuj człon telemetrii jako `Adresat: {clean_target_actor} (Mężczyzna) (MASCULINE)` (lub `Adresat: {clean_target_actor} (MASCULINE)` — całkowicie zastępując jakikolwiek wcześniejszy sufiks `(Kobieta)` / `(FEMININE)`);
     - jeśli encja posiada zweryfikowane `gender == "FEMALE"`, ustaw bezwarunkowo `target_gender = "FEMININE"` i sformatuj człon telemetrii jako `Adresat: {clean_target_actor} (Kobieta) (FEMININE)` (lub `Adresat: {clean_target_actor} (FEMININE)` — całkowicie zastępując jakikolwiek wcześniejszy sufiks `(Mężczyzna)` / `(MASCULINE)`).
     - jeśli `clean_target_actor == clean_speaker_name` (błędne wskazanie mówcy jako własnego adresata w dialogu), wyznacz jako adresata drugiego aktywnego rozmówcę w bieżącej scenie.
  4. **Izolacja monologów wewnętrznych i napisów `is_sign` w `Telemetria:`:**
     - Gdy zdarzenie ma `is_internal_monologue == True` (w tym każde zdarzenie o stylu `Italics`, `Italics - Top`, `Flashback_Italics`, `Flashback_Italics - Top`), w `Telemetria:` nie emituj fałszywego adresata zewnętrznego (ustaw `target_actor = None`, `target_gender = None` i pomiń człon `Adresat:` lub wyemituj `Adresat: brak (MONOLOG WEWNĘTRZNY)`).
     - Gdy zdarzenie ma `is_sign == True` lub `raw_actor.strip().lower() in ("sign", "signs", "txt", "title", "board", "screen")`, wyemituj `Mówca: sign (NEUTRAL)` bez przypisywania płci `FEMININE`/`MASCULINE`.
  5. **Uzgodnienie licznika `[Pre-pass Sceniczny Odcinka]` w `translator.py`:**
     W `_precompute_episode_scene_genders` (`translator.py`) wyliczaj liczby kwestii żeńskich i męskich do komunikatu `[Pre-pass Sceniczny Odcinka]: Wykryto ciągłość obsady dla N kwestii (F żeńskich, M męskich)` **po** wykonaniu `reconcile_prepass_with_p0` oraz z uwzględnieniem `series_bible.get_character(actor)` (wraz z aliasami ról z `BILINGUAL_ROLE_EQUIVALENCES`), tak aby kwestie postaci żeńskich P0 były wliczane do licznika `F żeńskich`.
- **Kryterium akceptacji:** Prawidłowy stan pola `Telemetria:` w Kroku 10 oraz komunikatu pre-passu = 100% zgodności zarówno pola `Mówca:`, jak i pola `Adresat:` ze zweryfikowanym `p0_gender` encji w `SeriesBible` (0 wystąpień `<Antroponim_Męski> (Kobieta) (FEMININE)` i 0 wystąpień `<Antroponim_Żeński> (Mężczyzna) (MASCULINE)`), brak pozornego adresata na liniach o stylu `Italics`, znacznik `(NEUTRAL)` dla `Mówca: sign` oraz niezerowy, zgodny z P0 licznik kwestii żeńskich w `[Pre-pass Sceniczny Odcinka]` (źródło autorytetu: rekord P0 w `SeriesBible`).

#### OPERACJA 2C.2 (z 9.4/2C.6 i 9.5/2C.6) — Rozróżnienie kursywy całoliniowej od częściowej kursywy emfatycznej w Kategorii 20 (`over_application_italics`) w `DialogueVerifier._guard_phase2_regressions` (`verifier.py`)
- **Konflikt z 9.5:** W przebiegu po wdrożeniu 9.5 (`WYKRYTY BŁĄD 2`) w głośnej linii dialogowej na stylu `Default` (`is_internal_monologue: false`) skierowanej do jawnego adresata, w której `en_text` zawierał kursywę wyłącznie wokół pojedynczego zaimka emfatycznego (`"<RZECZYWISTY_CIĄG_EN_1>"`), a `f1_pl` był tekstem prostym bez tagów `{\i1}`, Faza 2 otoczyła znacznikami `{\i1}...{\i0}` całe zdanie, a Kategoria 20 w `_guard_phase2_regressions` przepuściła tę zmianę, ponieważ sprawdzała jedynie ogólny warunek obecności podciągu `"{\\i1}"` w `source_en`.
- **Rozstrzygnięcie:** **ROZSZERZYĆ** Kategorię 20 (`over_application_italics`) w `DialogueVerifier._guard_phase2_regressions` (`verifier.py`).
- **Wymóg Phase 0 (Flaga Phase 0.H):** zweryfikować dokładny kod Kategorii 20 w `verifier.py`.
- **Implementacja:**
  1. Zdefiniuj w `DialogueVerifier` pomocniczą funkcję sprawdzającą, czy dany ciąg jest w całości otoczony pojedynczym blokiem kursywy (całoliniowa kursywa monologowa):
     ```python
     def _is_whole_line_italic(s: str) -> bool:
         st = (s or "").strip()
         if not (st.startswith("{\\i1}") and st.endswith("{\\i0}")):
             return False
         inner = st[5:-5]
         return "{\\i0}" not in inner and "{\\i1}" not in inner
     ```
  2. W Kategorii 20 (`over_application_italics`) w `_guard_phase2_regressions`:
     - gdy `is_internal_monologue == False` (linia nie ma stylu pochyłego `Italics`/`Flashback_Italics` i nie jest oznaczona jako myśl wewnętrzna), a `_is_whole_line_italic(refined_pl)` zwraca `True`, podczas gdy `_is_whole_line_italic(source_en)` jest `False` ORAZ `_is_whole_line_italic(f1_pl)` jest `False`:
       - jeśli `f1_pl` zawiera częściową kursywę emfatyczną wokół pojedynczego wyrazu (`"{\\i1}" in f1_pl`), przywróć `f1_pl`;
       - jeśli `f1_pl` nie zawiera tagów `{\i1}`, zdejmij zewnętrzne całoliniowe znaczniki `{\i1}` i `{\i0}` z `refined_pl` (`refined_pl = refined_pl.strip()[5:-5].strip()`), zachowując zredagowany tekst w czcionce prostej zgodnej ze stylem `Default`.
- **Kryterium akceptacji:** Prawidłowy stan wyjścia `_guard_phase2_regressions` dla każdej linii dialogu głośnego (`is_internal_monologue: false`, styl `Default`), w której `source_en` nie jest w całości pochylone (w tym gdy `source_en` pochyla wyłącznie pojedynczy wyraz emfatyczny) = całkowity brak całoliniowych znaczników `{\i1}...{\i0}` obejmujących pełne zdanie (źródło autorytetu: `phase1_text`, `en_text` oraz sekcja `[Events]`).

#### OPERACJA 2C.3 (z 9.5/2C.3) — Bezwzględne zerowanie segmentów ASR o `cjk_count == 0` oraz usuwanie osieroconych jednoznakowych partykuł nagłosowych po odcięciu prefiksu ASCII w `EpisodeProfiler.sanitize_event_asr` (`profiler.py`)
- **Konflikt z 9.5:** W przebiegu po wdrożeniu 9.5 (`WYKRYTY BŁĄD 5`) w polu `JP Audio (Whisper):` pozostał pojedynczy angielski wyraz `"<RZECZYWISTY_TOKEN_ASCII_1>"` niezawierający ani jednego znaku japońskiego (`cjk_count == 0`), a w dwóch liniach po odcięciu jednoliterowego prefiksu ASCII sklejonego z początkiem zdania (`"Cと..."` $\rightarrow$ `"と..."`, `"kの..."` $\rightarrow$ `"の..."`) na pierwszej pozycji zdania pozostała osierocona japońska partykuła łącząca (`と`, `の`).
- **Rozstrzygnięcie:** **ROZSZERZYĆ** `EpisodeProfiler.sanitize_event_asr` (`profiler.py`) oraz upewnić się, że każdy segment ASR w Kroku 4 i Kroku 10 przechodzi przez tę metodę.
- **Wymóg Phase 0 (Flaga Phase 0.K):** sprawdzić w `profiler.py:215-285`, dlaczego ciąg o `0` znaków CJK nie został wyzerowany oraz jak działa regex wycinający prefiks ASCII.
- **Implementacja:**
  1. **Usuwanie sklejonego prefiksu ASCII wraz z bezpośrednio przylegającą osieroconą partykułą nagłosową:**
     Gdy surowy segment japoński (przed sekcją `[romaji]`) rozpoczyna się od jednego lub więcej znaków łacińskich ASCII `[A-Za-z]+`, po których bezpośrednio (bez spacji lub po spacji/interpunkcji) występuje pojedyncza japońska partykuła enklityczna z zamkniętego zbioru UTF-8 `と`, `の`, `は`, `が`, `を`, `に`, `へ`, `で` (`[\u3068\u306e\u306f\u304c\u3092\u306b\u3078\u3067]`), a za nią właściwy wyraz japoński, usuń prefiks ASCII razem z tą osieroconą partykułą nagłosową:
     ```python
     jp_part = re.sub(
         r"^\s*[A-Za-z0-9_,\s.;:!?-]+[とのがはをにへで](?=[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF])",
         "",
         jp_part,
     )
     ```
  2. **Usuwanie wszystkich pozostałych podciągów ASCII z części japońskiej:**
     Usuń wszystkie pozostałe tokeny i litery ASCII `[A-Za-z]+` z części japońskiej `jp_part = re.sub(r"[A-Za-z]+[,.;:!?\s]*", "", jp_part).strip()`.
  3. **Bezwzględny warunek `cjk_count <= 1` (obejmujący `cjk_count == 0`):**
     Policz znaki japońskie CJK (Hiragana `\u3040-\u309F`, Katakana `\u30A0-\u30FF`, Kanji `\u4E00-\u9FFF`) w oczyszczonym `jp_part`:
     ```python
     cjk_chars = re.findall(r"[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF]", jp_part)
     if len(cjk_chars) <= 1:
         return ""
     ```
     Dzięki temu każdy czysto angielski token (np. `"<RZECZYWISTY_TOKEN_ASCII_1>"`, gdzie `len(cjk_chars) == 0`) oraz każdy pojedynczy znak resztkowy (`len(cjk_chars) == 1`) zostaje bezwarunkowo wyzerowany do `""`.
- **Kryterium akceptacji:** Prawidłowy stan pola `JP Audio (Whisper):` w Krokach 4 i 10 = `0` segmentów złożonych wyłącznie ze znaków ASCII (`cjk_count == 0`), `0` liter łacińskich ASCII w japońskiej części transkrypcji oraz `0` osieroconych partykuł enklitycznych (`と`, `の`, `は`, `が`, `を`, `に`, `へ`, `で`) na pozycji pierwszego znaku po usuniętym prefiksie ASCII (źródło autorytetu: Zasada 3 Standardu 9.0 oraz alfabet japoński CJK).

#### OPERACJA 2C.4 (z 9.5/2B.1 i 9.5/2C.4) — Obsługa separatora kropki `M.` / `D.` przy parsowaniu paradygmatów z Kroku 5, odmrażanie mianowników w Kroku 6 oraz trwałość `populate_secondary_actor_tags` (`series_memory.py` + `translator.py`)
- **Konflikt z 9.5:** W przebiegu po wdrożeniu 9.5 (`WYKRYTY BŁĄD 3`, Krok 5 vs Krok 6) `EpisodeProfiler` w Kroku 5 wygenerował pełną odmianę z kropką po skrócie przypadku (`M. <ANTROPONIM>, D. <FORMA_D>, C. <FORMA_C>...`), natomiast w Kroku 6 w `Paradygmaty odmiany` 4 antroponimy męskie zachowały zamrożony mianownik (`D..W == M`), a `characters_count` w Kroku 6 wyniosło `22` (brak 7 etykiet drugoplanowych z Kroku 3).
- **Rozstrzygnięcie:** **ROZSZERZYĆ** parser paradygmatów Kroku 5 oraz kolejność wywołań w Kroku 6 (`translator.py`, `series_memory.py`).
- **Wymóg Phase 0 (Flaga Phase 0.I):** sprawdzić w `translator.py:5169-5203` i `series_memory.py:1875`, jak paradygmaty z Kroku 5 są przekazywane do `SeriesBible` i dlaczego `populate_secondary_actor_tags` nie zwiększyło `characters_count` w Kroku 6.
- **Implementacja:**
  1. **Obsługa zarówno kropki, jak i dwukropka w parserze paradygmatów Kroku 5 (`translator.py` / `profiler.py`):**
     W funkcji parsującej sekcję `Odmiana Imion i Tytułów` z podsumowania `EpisodeProfiler` dopasowuj skróty przypadków zarówno z dwukropkiem (`M:`), jak i z kropką (`M.`):
     ```python
     case_matches = re.findall(
         r"\b(M|D|C|B|N|Ms|W)[.:]\s*([^,;\n(]+)",
         line_content,
     )
     ```
     Dla każdego wyodrębnionego słownika przypadków (posiadającego co najmniej 2 formy różne od mianownika `M`) bezwarunkowo nadpisz `self.series_bible.data["declensions"][entity_name]`.
  2. **Automatyczna regeneracja zamrożonych mianowników dla zweryfikowanych antroponimów męskich w `_sanitize_loaded_bible_in_ram` (`series_memory.py`):**
     W `SeriesBible._sanitize_loaded_bible_in_ram` przeiteruj po wszystkich encjach w `self.data["characters"]` posiadających `gender == "MALE"` i `entity_category == "ANTHROPONYM"`: jeśli w `self.data["declensions"]` dana encja ma zamrożony mianownik (`all(v == name for k, v in paradigm.items() if k in ("M","D","C","B","N","Ms","W"))`), a `generate_polish_name_declension(name, "MALE")` zwraca zróżnicowany paradygmat fleksyjny (np. dla imion zakończonych na spółgłoskę lub `-i`), zaktualizuj wpis w `self.data["declensions"][name]` w pamięci RAM wygenerowanym paradygmatem.
  3. **Trwałość `populate_secondary_actor_tags` w Kroku 6 (`translator.py`):**
     Wywołaj `self.series_bible.populate_secondary_actor_tags(list(normalized_actors.keys()))` bezpośrednio przed wywołaniem `EpisodeFlightRecorder` logującym Krok 6 (po wszelkich operacjach wczytywania/inicjalizacji `self.series_bible`), tak aby wszystkie osobowe etykiety z Kroku 3 (takie jak `Girl`, `Boy`, `Disciple A..E`) były widoczne w `Rejestr postaci` w Kroku 6.
- **Kryterium akceptacji:** Prawidłowy stan Kroku 6 w pliku `.log` = wszystkie odmienione w Kroku 5 antroponimy posiadają w `Paradygmaty odmiany` pełne, zróżnicowane formy przypadków `M..W` (niezależnie od tego, czy Krok 5 użył `M:` czy `M.`), a wszystkie osobowe etykiety aktorów z Kroku 3 znajdują się w `Rejestr postaci` Kroku 6 z priorytetem `P1` lub `P2` (źródło autorytetu: Krok 3 i Krok 5 w `.log`).

#### OPERACJA 2C.5 (z 9.5/2C.6) — Bezwzględna normalizacja małego `\n` do `\N` na wejściu `DialogueVerifier.verify_batch` przed zapisem `dpos_text` i logowaniem konsolowym (`verifier.py` + `translator.py`)
- **Konflikt z 9.5:** W przebiegu po wdrożeniu 9.5 (`WYKRYTY BŁĄD 4`) w Paczkach 8, 11, 12 i 13 model Fazy 2 zwrócił małe `\n`, które pozostało w `Faza 2 (Verifier):` i `AVTLinter (D_pos):` w Kroku 10 oraz spowodowało wypisanie w konsoli 14 pustych bloków `[Redaktor Dialogów]` różniących się wyłącznie `\N` vs `\n`.
- **Rozstrzygnięcie:** **NAPRAWIĆ** kolejność normalizacji znaków nowej linii w `DialogueVerifier.verify_batch` (`verifier.py`) oraz w `_translate_batch` (`translator.py`).
- **Wymóg Phase 0 (Flaga Phase 0.J):** zlokalizować w `verifier.py:110-125` oraz `translator.py` wszystkie miejsca, w których `r.refined_pl` jest odczytywany po odpowiedzi modelu Fazy 2.
- **Implementacja:**
  1. W `DialogueVerifier.verify_batch` (`verifier.py`) w pierwszym kroku pętli przetwarzającej każdy element `r` zwrócony przez model Fazy 2 (przed wywołaniem `_guard_phase2_regressions`, przed sprawdzeniem `_norm_cmp(f1_text) == _norm_cmp(r.refined_pl)` i przed zwróceniem listy z `verify_batch`) wykonaj bezwarunkową zamianę:
     ```python
     if r.refined_pl:
         r.refined_pl = (
             r.refined_pl.replace("\\r\\n", "\\N")
             .replace("\\n", "\\N")
             .replace("\r\n", "\\N")
             .replace("\n", "\\N")
         )
     ```
  2. Symetryczną normalizację wykonaj również na końcu `_guard_phase2_regressions` (przed `return`), tak aby nawet w przypadku modyfikacji tekstu przez którąkolwiek kategorię strażnika zwracany ciąg zawsze zawierał wyłącznie wielkie `\N`.
  3. W `translator.py` przed wypisaniem wpisu `[Redaktor Dialogów]` w konsoli upewnij się, że porównywane ciągi `Szkic` i `Szlif` mają znormalizowane `\N`, a blok `[Redaktor Dialogów]` jest wypisywany wyłącznie wtedy, gdy po normalizacji `\N` i odjęciu zewnętrznych tagów `{\i1}...{\i0}` na stylu `Italics` zachodzi `szlif_clean != szkic_clean`.
- **Kryterium akceptacji:** Prawidłowy stan `Faza 2 (Verifier):` i `AVTLinter (D_pos):` w Kroku 10 oraz logu konsolowego = `0` wystąpień małego znaku `\n` w `phase2_text` i `dpos_text` we wszystkich 260 rekordach odcinka oraz `0` pustych wpisów `[Redaktor Dialogów]` dla linii o identycznej treści słownej (źródło autorytetu: konwencja formatu ASS `\N` oraz `phase1_text`).

---

## SEKCJA 3: REGUŁY DLA PIPELINE'U DANYCH

Wszystkie reguły dla pipeline'u danych mają priorytet P0 i są zdefiniowane w pełnej formie pozytywnej (Zasada 2):

1. **R3.1 (P0) — Kompletność Synchronizacji `SeriesBible` w Pamięci RAM (Kroki 3, 5 i 6):**
   - **Definicja pozytywna:** Prawidłowy stan obiektu `SeriesBible` w pamięci RAM w momencie logowania Kroku 6 = jednoczesne spełnienie pięciu warunków pozytywnych: (a) obecność wszystkich osobowych etykiet aktorów z Kroku 3 (`populate_secondary_actor_tags`) z priorytetem `P1` lub `P2`, (b) dwukierunkowe zmapowanie angielskich etykiet ról z `[Events]` oraz japońskich aliasów z honoryfikatorem na kanoniczne encje P0, (c) przejęcie wszystkich 7-przypadkowych paradygmatów odmiany wygenerowanych w Kroku 5 zarówno z separatorem dwukropka (`M:`), jak i kropki (`M.`), (d) zastąpienie w RAM wszelkich zamrożonych mianowników dla zweryfikowanych antroponimów męskich pełnymi paradygmatami odmiany oraz (e) spójność kierunkowa i rodzajowa każdego wpisu w `relations` potwierdzona przez `_validate_relation_entry_consistency`.
   - **Źródło stanu docelowego:** Rekord P0 (`EpisodeProfiler` Krok 5), słownik Kroku 3 oraz `SeriesBible`.

2. **R3.2 (P0) — Czystość Nazw i Bezwzględny Prymat `p0_gender` w Polach `Mówca:` i `Adresat:` Wektora `Telemetria:` (Kroki 7 i 10):**
   - **Definicja pozytywna:** Prawidłowy stan wektora `Telemetria:` w Kroku 10 oraz statystyk pre-passu scenicznego w Kroku 7 = oczyszczenie zarówno identyfikatora mówcy (`raw_actor`), jak i identyfikatora adresata (`target_actor`) ze wszelkich nawiasowych adnotacji akustycznych $F_0$ (`\s*\([^)]*\)`) przed odczytem z `SeriesBible`, stuprocentowa zgodność znaczników `(MASCULINE)` / `(FEMININE)` z `p0_gender` encji zarówno dla `Mówca:`, jak i dla `Adresat:`, brak zewnętrznego adresata na liniach z `is_internal_monologue: true`, znacznik `(NEUTRAL)` dla `Mówca: sign` oraz zliczanie kwestii postaci żeńskich P0 w liczniku `[Pre-pass Sceniczny Odcinka]`.
   - **Źródło stanu docelowego:** Sekcja `[Events]` oraz rekord P0 w `SeriesBible`.

3. **R3.3 (P0) — Ochrona Formatowania, Modalności, Fleksji P0 i Ciągłości Składniowej na Granicy Fazy 1 i Fazy 2 (Kroki 8, 9 i 10):**
   - **Definicja pozytywna:** Prawidłowy stan wyjścia `DialogueVerifier.verify_batch` i `_guard_phase2_regressions` = bezwzględna normalizacja wszystkich znaków nowej linii do `\N` przed zapisem `dpos_text` i przed logowaniem konsolowym, wyzerowanie `changes_made = None` przy braku zmiany leksykalnej, zdjęcie całoliniowych znaczników `{\i1}...{\i0}` z linii dialogu głośnego (`is_internal_monologue: false`) gdy `source_en` nie jest w całości pochylone (w tym gdy `source_en` pochyla wyłącznie pojedynczy wyraz emfatyczny), zachowanie końcówek rodzajowych zgodnych z `p0_gender` mówcy oraz zachowanie ciągłości wielokropka między zdaniami rozbitymi.
   - **Źródło stanu docelowego:** Rekord P0, `phase1_text`, `en_text` oraz sekcja `[V4+ Styles]`.

4. **R3.4 (P0) — Nienaruszalność Napisów Ekranowych `is_sign` i Spójność Kanonicznych Antroponimów po Usunięciu Honoryfikatorów (Krok 11):**
   - **Definicja pozytywna:** Prawidłowy stan wyjściowego strumienia `[Events]` po zakończeniu Kroku 11 = zachowanie każdego napisu ekranowego (`is_sign: true`, `Name: sign`, `\pos()`) jako pojedynczego zdarzenia `Dialogue:` (`events_count == total_lines`), zastępowanie japońskich aliasów z honoryfikatorem (`-chan`/`-kun`) przy `keep_honorifics: false` odpowiednią formą fleksyjną `M..W` kanonicznego antroponimu z `SeriesBible` (`ass_text == dpos_text`) oraz pełne wylistowanie poprawek EQG z `consistency_check: OK`.
   - **Źródło stanu docelowego:** Sekcja `[Events]`, `dpos_text` oraz rekord P0 w `SeriesBible`.

5. **R3.5 (P0) — Wolność Bufora ASR od Segmentów Bez Znaków CJK, Sklejonych Prefiksów ASCII i Osieroconych Partykuł Nagłosowych (Krok 4):**
   - **Definicja pozytywna:** Prawidłowy stan bufora `asr_text` po wykonaniu `EpisodeProfiler.sanitize_event_asr` = wyzerowanie (`""`) każdego segmentu posiadającego $\le 1$ znak japoński CJK (w tym `0` znaków CJK dla czysto angielskich słów halucynowanych w ciszy/szumie), wycięcie wszystkich podciągów ASCII wraz z bezpośrednio przylegającą do prefiksu ASCII osieroconą jednoznakową partykułą japońską (`と`, `の`, `は`, `が`, `を`, `に`, `へ`, `で`) na początku zdania oraz wyzerowanie duplikatów oddalonych o $> 1,5\text{ s}$ lub tworzących serie $> 2$ identycznych segmentów.
   - **Źródło stanu docelowego:** Zasada 3 Standardu 9.0 (`en_text` jako autorytet) oraz alfabet japoński CJK.

---

## SEKCJA 4: KOLEJNOŚĆ WDROŻENIA

Kolejność wdrożenia wynika z rozkładu procentowego błędów (60,0% OFFLINE + 40,0% HYBRYDA = 100% udziału ogniw deterministycznych) oraz zależności danych od Kroku 3 do Kroku 11:

1. **ETAP WDROŻENIOWY 1 (Faza 0 — Weryfikacja kodu i flag 0.G–0.K):**
   - Przeczytanie w całości plików z listy P0.1, zlokalizowanie dokładnych linii dla flag `Phase 0.G–0.K` i wypełnienie tabel P0.2 oraz P0.3 w `Raport_wdrozenia_9.6.md`.
2. **ETAP WDROŻENIOWY 2 (Operacja `2C.1` — Oczyszczenie `target_actor` z nawiasów $F_0$ w `arbitrate_event_telemetry` i licznik pre-passu):**
   - Wdrożenie regexu `re.sub(r"\s*\([^)]*\)", "", str(target_actor or "")).strip()` w `scene_discourse.py`, izolacja `Adresat:` na liniach `is_internal_monologue` i `is_sign` oraz aktualizacja licznika `[Pre-pass Sceniczny Odcinka]` w `translator.py`.
3. **ETAP WDROŻENIOWY 3 (Operacja `2C.3` — Domknięcie `sanitize_event_asr` dla `cjk_count == 0` i osieroconych partykuł nagłosowych):**
   - Wdrożenie w `profiler.py` wycinania prefiksu ASCII wraz z osieroconą partykułą nagłosową (`と`, `の`, `は`, `が`, `を`, `に`, `へ`, `で`) oraz bezwzględnego warunku `if len(cjk_chars) <= 1: return ""`.
4. **ETAP WDROŻENIOWY 4 (Operacje `2C.4` i `2B.1` — Parser kropki `M.` z Kroku 5, trwałość `populate_secondary_actor_tags` i mapowanie aliasu z `-chan` na kanoniczny paradygmat P0):**
   - Rozszerzenie regexu paradygmatów z Kroku 5 o separator kropki `[.:]`, regeneracja zamrożonych mianowników w RAM, wywołanie `populate_secondary_actor_tags` bezpośrednio przed logowaniem Kroku 6 oraz mapowanie aliasu z honoryfikatorem na kanoniczny paradygmat `SeriesBible`.
5. **ETAP WDROŻENIOWY 5 (Operacje `2C.2` i `2C.5` — Rozróżnienie kursywy całoliniowej i częściowej w Kategorii 20 oraz normalizacja `\n` $\rightarrow$ `\N` w `verify_batch`):**
   - Wdrożenie `_is_whole_line_italic` w Kategorii 20 w `verifier.py` oraz bezwarunkowej zamiany `\n` $\rightarrow$ `\N` na początku `verify_batch` i na końcu `_guard_phase2_regressions`.
6. **ETAP WDROŻENIOWY 6 (Implementacja testów `T6.1–T6.5`, walidacja CI/CD oraz walidacja empiryczna re-tłumaczenia odcinka):**
   - Dodanie testów `T6.1–T6.5`, uruchomienie `pytest` (fast + full) i 4 bramek CI/CD oraz wykonanie kontrolnego re-tłumaczenia odcinka w celu potwierdzenia eliminacji wszystkich 5 błędów w sekcji 6C raportu.

---

## SEKCJA 5: WALIDACJA TESTOWA I WARUNEK UKOŃCZENIA

### 5A — Walidacja testowa

#### 1. Infrastruktura testowa (stan bazowy po Depuracji Legacy 1.0 i wersji 9.5, commit `80d30e5`)
- **Pliki testowe jednostkowe (domyślne):** `tests/test_avt_linter.py`, `tests/test_verifier.py`, `tests/test_series_memory.py`, `tests/test_discourse_and_translator.py`, `tests/test_metadata.py`, `tests/test_profiler.py`, `tests/test_translator.py`, `tests/test_flight_recorder.py` oraz testy `KEEP` w `test_system.py` (łącznie **182 testy bazowe** w trybie `komenda_fast`, wykonywane w ~16,65–20,43 s[cite: 19]).
- **Pliki testowe zarchiwizowane:** `tests/archive/test_legacy_manifest.py` (wykluczone przez `norecursedirs` w `pytest.ini` — pozostają nietknięte[cite: 19]).
- **Komendy testowe:**
  - `komenda_fast` = `pytest` (uruchamia testy z `addopts = -v --tb=short -m "not slow and not network"`, czas wykonania $< 60\text{ s}$)
  - `komenda_full` = `pytest -m ""` (uruchamia wszystkie testy jednostkowe, `slow` i `network` — 335 testów bazowych + nowe testy 9.6)
  - `komenda_slow` = `pytest -m slow` (153 testy)
  - `komenda_network` = `pytest -m network` (12 testów)
- **Bramki CI/CD:** `verify_purity.py`, `verify_ultimate_pipeline.py`, `verify_12_fixes.py`, `audit_diff.ps1`.

#### 2. Wykaz nowych testów `T6.1–T6.5` jako wzorce strukturalne z `@pytest.mark.parametrize` i placeholderami `<RZECZYWISTY_*>`

Wszystkie 5 testów ma kategorię markera `unit` (wchodzą do domyślnego przebiegu `komenda_fast`). Placeholdery `<RZECZYWISTY_*>` agent kodujący wypełnia w Phase 0 (tabela P0.3) autentycznymi danymi z `SeriesBible` / `en_text` odcinka testowego (innego niż odcinek audytowany):

| ID testu | Punkt Sekcji 2 | Plik testowy | Nazwa testu | Kategoria markera | Kryterium akceptacji (forma pozytywna + źródło autorytetu) |
|---|---|---|---|---|---|
| **T6.1** | **2C.1** | `tests/test_discourse_and_translator.py` | `test_arbitrate_telemetry_strips_f0_parentheses_from_target_actor_and_enforces_p0` | `unit` | Prawidłowy stan `target_actor` i `target_gender` w `arbitrate_event_telemetry` = całkowite usunięcie nawiasów $F_0$ `(...)` z nazwy adresata oraz wymuszenie `MASCULINE`/`FEMININE` zgodnie z `p0_gender` z `SeriesBible`. |
| **T6.2** | **2C.2** | `tests/test_verifier.py` | `test_guard_phase2_strips_whole_line_italics_when_source_en_has_only_partial_emphasis` | `unit` | Prawidłowy stan wyjścia `_guard_phase2_regressions` dla `is_internal_monologue: False` = zdjęcie całoliniowego `{\i1}...{\i0}` z `refined_pl`, gdy `source_en` ma pochylony tylko pojedynczy wyraz, a `f1_pl` jest tekstem prostym. |
| **T6.3** | **2C.3** | `tests/test_profiler.py` | `test_sanitize_event_asr_zeros_zero_cjk_latin_words_and_strips_orphaned_initial_particles` | `unit` | Prawidłowy stan `sanitize_event_asr` = zwrócenie `""` dla czysto łacińskiego słowa o `cjk_count == 0` oraz usunięcie osieroconej partykuły nagłosowej (`と`, `の`) po wycięciu prefiksu ASCII. |
| **T6.4** | **2C.4 + 2B.1** | `tests/test_series_memory.py` | `test_step5_dot_separator_paradigm_parsing_and_honorific_alias_canonical_declension` | `unit` | Prawidłowy stan `SeriesBible.data["declensions"]` = poprawne wczytanie odmiany z separatorem kropki (`M. ..., D. ...`), odmrożenie mianownika oraz mapowanie aliasu z `-chan` na kanoniczny narzędnik `N`. |
| **T6.5** | **2C.5** | `tests/test_verifier.py` | `test_verify_batch_normalizes_lowercase_newlines_to_ass_uppercase_before_comparison` | `unit` | Prawidłowy stan `refined_pl` i `changes_made` w `verify_batch` = zamiana wszystkich `\n` na `\N` oraz `changes_made is None`, gdy `refined_pl` różnił się od `f1_pl` wyłącznie wielkością znaku `\n` vs `\N`. |

##### Wzorce strukturalne testów `T6.1–T6.5` (do adaptacji po Phase 0):

```python
import pytest

# WZORZEC T6.1 (Operacja 2C.1) -> tests/test_discourse_and_translator.py
@pytest.mark.parametrize(
    "raw_actor,polluted_target_actor,speaker_p0,target_p0,is_monologue,expected_clean_target,expected_target_gender",
    [
        (
            "<RZECZYWISTY_ANTROPONIM_ŻEŃSKI_1>",
            "<RZECZYWISTY_ANTROPONIM_MĘSKI_1> (Kobieta)",
            "FEMALE",
            "MALE",
            False,
            "<RZECZYWISTY_ANTROPONIM_MĘSKI_1>",
            "<WARTOŚĆ_ENUM_TECHNICZNA_1>",
        ),
        (
            "<RZECZYWISTY_ANTROPONIM_MĘSKI_1>",
            "<RZECZYWISTY_ANTROPONIM_ŻEŃSKI_1> (Mężczyzna - Scena Wyłącznie Męska)",
            "MALE",
            "FEMALE",
            False,
            "<RZECZYWISTY_ANTROPONIM_ŻEŃSKI_1>",
            "<WARTOŚĆ_ENUM_TECHNICZNA_2>",
        ),
        (
            "<RZECZYWISTY_ANTROPONIM_MĘSKI_1>",
            "<RZECZYWISTY_ANTROPONIM_MĘSKI_1> (Mężczyzna - Scena Wyłącznie Męska)",
            "MALE",
            "MALE",
            True,
            "",
            None,
        ),
    ],
)
def test_arbitrate_telemetry_strips_f0_parentheses_from_target_actor_and_enforces_p0(
    raw_actor,
    polluted_target_actor,
    speaker_p0,
    target_p0,
    is_monologue,
    expected_clean_target,
    expected_target_gender,
):
    from series_memory import SeriesBible
    from scene_discourse import SceneDiscourseGraph

    bible = SeriesBible(slug="test_target_actor_clean_p0")
    bible.sync_verified_profile_entity("<RZECZYWISTY_ANTROPONIM_MĘSKI_1>", "MALE", has_verified_gender=True)
    bible.sync_verified_profile_entity("<RZECZYWISTY_ANTROPONIM_ŻEŃSKI_1>", "FEMALE", has_verified_gender=True)

    res = SceneDiscourseGraph.arbitrate_event_telemetry(
        raw_actor=raw_actor,
        target_actor=polluted_target_actor,
        series_bible=bible,
        is_internal_monologue=is_monologue,
    )
    assert res.get("target_actor", "") == expected_clean_target
    assert res.get("addressee_gender") == expected_target_gender
    assert "(Kobieta) (MASCULINE)" not in res.get("dry_telemetry", "")
    assert "(Mężczyzna) (FEMININE)" not in res.get("dry_telemetry", "")


# WZORZEC T6.2 (Operacja 2C.2) -> tests/test_verifier.py
@pytest.mark.parametrize(
    "source_en,f1_pl,refined_pl,is_internal_monologue,expected_pl",
    [
        (
            "<RZECZYWISTY_CIĄG_EN_1>",
            "<RZECZYWISTY_CIĄG_PL_1>",
            "{\\i1}<RZECZYWISTY_CIĄG_PL_2>{\\i0}",
            False,
            "<RZECZYWISTY_CIĄG_PL_2>",
        ),
        (
            "{\\i1}<RZECZYWISTY_CIĄG_EN_2>{\\i0}",
            "{\\i1}<RZECZYWISTY_CIĄG_PL_1>{\\i0}",
            "{\\i1}<RZECZYWISTY_CIĄG_PL_2>{\\i0}",
            True,
            "{\\i1}<RZECZYWISTY_CIĄG_PL_2>{\\i0}",
        ),
    ],
)
def test_guard_phase2_strips_whole_line_italics_when_source_en_has_only_partial_emphasis(
    source_en, f1_pl, refined_pl, is_internal_monologue, expected_pl
):
    from verifier import DialogueVerifier

    out = DialogueVerifier._guard_phase2_regressions(
        f1_pl=f1_pl,
        refined_pl=refined_pl,
        source_en=source_en,
        is_internal_monologue=is_internal_monologue,
        target_gender="<WARTOŚĆ_ENUM_TECHNICZNA_2>",
    )
    assert out == expected_pl


# WZORZEC T6.3 (Operacja 2C.3) -> tests/test_profiler.py
@pytest.mark.parametrize(
    "raw_asr_input,expected_sanitized_output",
    [
        ("<RZECZYWISTY_TOKEN_ASCII_1>", ""),
        (
            "<RZECZYWISTY_TOKEN_ASCII_1><RZECZYWISTA_PARTYKUŁA_NAGŁOSOWA_1><RZECZYWISTY_CIĄG_EN_1>",
            "<RZECZYWISTY_CIĄG_EN_1>",
        ),
        (
            "<RZECZYWISTY_TOKEN_ASCII_1><RZECZYWISTA_PARTYKUŁA_NAGŁOSOWA_2><RZECZYWISTY_CIĄG_EN_2>",
            "<RZECZYWISTY_CIĄG_EN_2>",
        ),
    ],
)
def test_sanitize_event_asr_zeros_zero_cjk_latin_words_and_strips_orphaned_initial_particles(
    raw_asr_input, expected_sanitized_output
):
    from profiler import EpisodeProfiler

    cleaned = EpisodeProfiler.sanitize_event_asr(raw_asr_input, is_sign=False)
    assert cleaned == expected_sanitized_output


# WZORZEC T6.4 (Operacje 2C.4 + 2B.1) -> tests/test_series_memory.py
@pytest.mark.parametrize(
    "step5_line,entity_name,expected_d,expected_n,expected_w",
    [
        (
            "<RZECZYWISTY_ANTROPONIM_1>: M. <RZECZYWISTY_PARADYGMAT_M_1>, D. <RZECZYWISTY_PARADYGMAT_D_1>, C. <RZECZYWISTY_ANTROPONIM_1>owi, B. <RZECZYWISTY_PARADYGMAT_D_1>, N. <RZECZYWISTY_PARADYGMAT_N_1>, Ms. <RZECZYWISTY_PARADYGMAT_W_1>, W. <RZECZYWISTY_PARADYGMAT_W_1>",
            "<RZECZYWISTY_ANTROPONIM_1>",
            "<RZECZYWISTY_PARADYGMAT_D_1>",
            "<RZECZYWISTY_PARADYGMAT_N_1>",
            "<RZECZYWISTY_PARADYGMAT_W_1>",
        ),
        (
            "<RZECZYWISTY_ANTROPONIM_2>: M: <RZECZYWISTY_ANTROPONIM_2>, D: <RZECZYWISTY_ANTROPONIM_2>a, C: <RZECZYWISTY_ANTROPONIM_2>owi, B: <RZECZYWISTY_ANTROPONIM_2>a, N: <RZECZYWISTY_ANTROPONIM_2>em, Ms: <RZECZYWISTY_ANTROPONIM_2>ie, W: <RZECZYWISTY_ANTROPONIM_2>ie",
            "<RZECZYWISTY_ANTROPONIM_2>",
            "<RZECZYWISTY_ANTROPONIM_2>a",
            "<RZECZYWISTY_ANTROPONIM_2>em",
            "<RZECZYWISTY_ANTROPONIM_2>ie",
        ),
    ],
)
def test_step5_dot_separator_paradigm_parsing_and_honorific_alias_canonical_declension(
    step5_line, entity_name, expected_d, expected_n, expected_w
):
    from series_memory import SeriesBible

    bible = SeriesBible(slug="test_dot_paradigm_and_alias")
    bible.data["declensions"][entity_name] = {k: entity_name for k in ("M", "D", "C", "B", "N", "Ms", "W")}
    parsed_map = SeriesBible.parse_step5_declension_line(step5_line)
    bible.sync_verified_profile_entity(entity_name, "MALE", has_verified_gender=True, declension_map=parsed_map)
    assert bible.data["declensions"][entity_name]["D"] == expected_d
    assert bible.data["declensions"][entity_name]["N"] == expected_n
    assert bible.data["declensions"][entity_name]["W"] == expected_w


# WZORZEC T6.5 (Operacja 2C.5) -> tests/test_verifier.py
@pytest.mark.parametrize(
    "f1_pl,raw_f2_pl,raw_reason,expected_refined_pl,expected_changes_made",
    [
        (
            "{\\i1}<RZECZYWISTY_CIĄG_PL_1>\\N<RZECZYWISTY_CIĄG_PL_2>{\\i0}",
            "{\\i1}<RZECZYWISTY_CIĄG_PL_1>\n<RZECZYWISTY_CIĄG_PL_2>{\\i0}",
            "[Filar I] Zmiana podziału wiersza.",
            "{\\i1}<RZECZYWISTY_CIĄG_PL_1>\\N<RZECZYWISTY_CIĄG_PL_2>{\\i0}",
            None,
        ),
        (
            "<RZECZYWISTY_CIĄG_PL_1>\\N<RZECZYWISTY_CIĄG_PL_2>",
            "<RZECZYWISTY_CIĄG_PL_1>\\n<RZECZYWISTY_CIĄG_PL_2>",
            "[Filar II] Korekta.",
            "<RZECZYWISTY_CIĄG_PL_1>\\N<RZECZYWISTY_CIĄG_PL_2>",
            None,
        ),
    ],
)
def test_verify_batch_normalizes_lowercase_newlines_to_ass_uppercase_before_comparison(
    f1_pl, raw_f2_pl, raw_reason, expected_refined_pl, expected_changes_made
):
    from verifier import DialogueVerifier

    norm_pl, norm_reason = DialogueVerifier.normalize_phase2_line_and_reason(
        f1_pl=f1_pl, refined_pl=raw_f2_pl, changes_made=raw_reason
    )
    assert norm_pl == expected_refined_pl
    assert "\n" not in norm_pl
    assert norm_reason is expected_changes_made
```

#### 3. Warunek ukończenia wdrożenia (definicja pozytywna — punkty (a)–(p))
Prawidłowy stan ukończenia wdrożenia wersji **9.6** = jednoczesne spełnienie szesnastu warunków pozytywnych (a)–(p):
- **(a)** Wszystkie operacje z Sekcji 2A (`2A.1–2A.8`) utrzymane w stanie nienaruszonym;
- **(b)** Operacja z Sekcji 2B (`2B.1`) w pełni wdrożona w runtime;
- **(c)** Wszystkie operacje z Sekcji 2C (`2C.1–2C.5`) w pełni wdrożone w runtime;
- **(d)** Wszystkie reguły z Sekcji 1 (`R1.1–R1.11`) i Sekcji 3 (`R3.1–R3.5`) zachowane w czystej formie pozytywnej;
- **(e)** Wszystkie 5 nowych testów jednostkowych (`T6.1–T6.5`) zaimplementowane i sparametryzowane ($\ge 2$ warianty każdy);
- **(f)** `komenda_fast` (`pytest`): 100% PASSED, `0 FAILED`, `0 ERROR`, czas wykonania $< 60\text{ s}$;
- **(g)** `komenda_full` (`pytest -m ""`): 100% PASSED, `0 FAILED`, `0 ERROR`;
- **(h)** `komenda_slow` (`pytest -m slow`) oraz `komenda_network` (`pytest -m network`): 100% PASSED;
- **(i)** Bramki CI/CD (`verify_purity.py`, `verify_ultimate_pipeline.py`, `verify_12_fixes.py`) zwracają 100% PASS;
- **(j)** `audit_diff.ps1` zwraca status VICTORY CONFIRMED;
- **(k)** Phase 0 ukończona z wypełnionymi tabelami P0.2 i P0.3 oraz rozstrzygniętymi flagami `Phase 0.G–0.K` w `Raport_wdrozenia_9.6.md`;
- **(l)** Każdy nowy test `T6.1–T6.5` zweryfikowany empirycznie pod kątem falsyfikowalności i wolny od anty-wzorców `D1–D6` (w tym `D6.a–D6.e`);
- **(m)** **Walidacja empiryczna (obowiązkowa):** po wdrożeniu zmian wykonano weryfikację na przebiegu odcinka audytowanego i potwierdzono w Sekcji 6C pliku `Raport_wdrozenia_9.6.md` wyeliminowanie wszystkich 5 błędów z Etapu 1/2 (100% zgodności `Adresat:` z P0 bez fałszywych nawiasów $F_0$, brak całoliniowej kursywy na głośnym dialogu z 1 pochylonym słowem EN, kanoniczna odmiana `N` zamiast obciętego rdzenia po `-chan` i pełny transfer odmiany z kropką `M.` z Kroku 5 do Kroku 6, `0` małych `\n` w `dpos_text`, `0` tokenów o `cjk_count == 0` i `0` osieroconych partykuł nagłosowych w ASR);
- **(n)** Żaden z 182 testów domyślnych (116 `KEEP` z Depuracji 1.0 + 66 instancji z 9.4 i 9.5) nie został usunięty ani osłabiony;
- **(o)** Katalog `tests/archive/` oraz 3 gałęzie `# DEFENSIVE_FALLBACK` w `avt_linter.py` pozostają nietknięte;
- **(p)** Wszystkie pola `<DO_WYPEŁNIENIA_*>` w pliku `Raport_wdrozenia_9.6.md` zostały wypełnione (`0` niewypełnionych placeholderów).

### 5B — Obowiązek wypełnienia Raportu Wdrożenia (DELIVERABLE)

Po zakończeniu implementacji, walidacji testowej i walidacji empirycznej agent kodujący ma bezwzględny obowiązek wypełnienia wszystkich pól `<DO_WYPEŁNIENIA_*>` (w tym Sekcji 2, 4, 6, 6C, 7, 8, 10 i 11) w pliku:
`C:\Users\Piotrek\Desktop\translator\Artefakty\Raport_wdrozenia_9.6.md`
oraz zaktualizowania statusu i Sekcji 12 w pliku `Raport_wdrozenia_9.5.md`.

---

## SEKCJA 6: ZAKAZY ARCHITEKTONICZNE (RYGORY WDROŻENIOWE 9.6)

1. **ZAKAZ 1 (Zakaz Test-Only Wiring):** Niedopuszczalne jest implementowanie logiki wyłącznie w pomocniczych metodach wywoływanych przez `pytest` z pominięciem głównej ścieżki wykonawczej w `translator.py`, `scene_discourse.py`, `profiler.py`, `series_memory.py` i `verifier.py`.
2. **ZAKAZ 2 (Zakaz Mockowania Testów Domenowych):** Testy `T6.1–T6.5` muszą wywoływać rzeczywiste metody produkcyjne klas silnika AVT, bez podmiany testowanej logiki przez `unittest.mock.patch`.
3. **ZAKAZ 3 (Zakaz Pomijania Phase 0):** Niedopuszczalne jest rozpoczęcie edycji kodu przed przeczytaniem plików z listy P0.1 i rozstrzygnięciem flag `Phase 0.G–0.K`.
4. **ZAKAZ 4 (Zakaz Pomijania Walidacji Empirycznej 6C):** Niedopuszczalne jest zamknięcie wdrożenia bez weryfikacji 5 błędów z Etapu 1/2 i wypełnienia tabeli w Sekcji 6C pliku `Raport_wdrozenia_9.6.md`.
5. **ZAKAZ 5 (Zakaz Naruszania Testów KEEP z Depuracji 1.0):** Żaden z 116 testów `KEEP` z Depuracji Legacy 1.0 ani testów z wersji 9.4 i 9.5 nie może zostać usunięty, zakomentowany ani osłabiony (anty-wzorzec `D6.e`).
6. **ZAKAZ 6 (Zakaz Modyfikacji Gałęzi DEFENSIVE_FALLBACK):** 3 chronione gałęzie `if not strict_positive_domain` opatrzone komentarzem `# DEFENSIVE_FALLBACK` w `avt_linter.py` są całkowicie nienaruszalne.
7. **ZAKAZ 7 (Zakaz Modyfikacji `tests/archive/` i Markerów `pytest.ini`):** Katalog `tests/archive/` oraz konfiguracja markerów `slow` / `network` w `pytest.ini` pozostają nietknięte (anty-wzorce `D6.c`, `D6.d`).
8. **ZAKAZ 8 (Zakaz Pozostawiania Placeholderów w Raporcie):** W zapisanym pliku `Raport_wdrozenia_9.6.md` liczba wystąpień ciągu `DO_WYPEŁNIENIA` musi wynosić dokładnie `0`.
9. **ZAKAZ 9 (Zakaz Modyfikacji Plików Danych i Napisów w Repozytorium — Zero-Cosmetic Gate):** Pliki baz wiedzy (`*_bible.json`) oraz pliki napisów (`.ass`, `.srt`) śledzone przez `git` nie mogą być ręcznie edytowane jako substytut naprawy kodu w Pythonie.
10. **ZAKAZ 10 (Zakaz Wycieku Literalnego — Zero-Literal Gate):** W kodzie produkcyjnym `.py`, w `rules.py` oraz w testach `tests/test_*.py` obowiązuje całkowity zakaz umieszczania cytatów zdań i nazw własnych z audytowanego odcinka (`verify_purity.py` i `audit_diff.ps1` muszą zwrócić 100% PASS).