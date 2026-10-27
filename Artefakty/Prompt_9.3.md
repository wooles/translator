# PROMPT NAPRAWCZY 9.3 — WDROŻENIE W POTOKU AVT

## PREAMBUŁA

Dokument definiuje operacje kodowe i regułowe rozszerzające potok AVT w wersji 9.2 (commit 88b7327). Podstawa empiryczna: weryfikacja regresji EP01_post po wdrożeniu 9.2 oraz audyt nowego odcinka EP02 (seria inna niż EP01). Cel: domknięcie operacji z 9.2 w warstwie propagacji P0 i guardów Fazy 2; rozszerzenie zakresu o spójność rejestru relacji, populację P0 dla encji drugoplanowych, integralność raportowania bramki jakości.

Dokument przestrzega Standardu 9.0 (Zero-Literal, Pure Positive Domain, Primary LLM Translation Authority, Instance-Free Metalinguistic Architecture) i Standardu 9.3 (Phase 0 obowiązkowa, sekcja 2 w podziale 2A/2B/2C, testy jako wzorce strukturalne z placeholderami, Zasada 8 niedegradacyjności).

Numer wersji: 9.3. Poprzednia wersja: 9.2 (autorytet dla operacji testowych objętych 2A).

## IDENTYFIKATORY

**Moduły:** `avt_linter.py`, `verifier.py`, `translator.py`, `series_memory.py`, `scene_discourse.py`, `profiler.py`, `metadata.py`, `rules.py`, `flight_recorder.py`, `sign_detector.py`.

**Klasy i funkcje:** `AVTLinter.lint_and_fix_line`, `EpisodeQualityGate.audit_and_fix_entire_episode`, `EpisodeQualityGate.should_apply_top_alignment_on_collision`, `EpisodeQualityGate._run_phase_7_hygiene`, `EpisodeQualityGate.normalize_ass_tags_and_sign_layout`, `DialogueVerifier.verify_batch`, `DialogueVerifier._guard_phase2_regressions`, `DialogueVerifier.enforce_sign_nominative_orthography`, `SeriesBible._sanitize_loaded_bible_in_ram`, `SeriesBible.sync_verified_profile_entity`, `SeriesBible.relations`, `SceneDiscourseGraph.arbitrate_event_telemetry`, `SceneDiscourseGraph.build_discourse_topology`, `EpisodeProfiler.sanitize_event_asr`, `EpisodeProfiler.profile_episode`, `EpisodeProfiler._extract_f0_contour`, `EpisodeFlightRecorder.report_step_11_quality_gate`, `RuleDispatcher.get_active_rules`, `VisualSignDetector.detect_signs`.

**Enumeracje i znaczniki architektury:** `MALE`, `FEMALE`, `MASCULINE`, `FEMININE`, `NON_VIRILE`, `VIRILE`, `POLYLOGUE`, `ANTHROPONYM`, `LABEL`, `TITLE`, `DIALOGUE`, `is_sign`, `Italic`, `Alignment`, `prima materia`, `P0`, `has_verified_gender`, `confidence`, `priority`, `M`, `D`, `C`, `B`, `N`, `Ms`, `W`.

**Placeholdery testowe (do wypełnienia rzeczywistymi wartościami z `SeriesBible` / `en_text` odcinka testowego):** `<RZECZYWISTY_ANTROPONIM_1>`, `<RZECZYWISTY_ANTROPONIM_2>`, `<RZECZYWISTY_ANTROPONIM_MĘSKI_1>`, `<RZECZYWISTY_ANTROPONIM_ŻEŃSKI_1>`, `<RZECZYWISTY_CIĄG_PL_1>`, `<RZECZYWISTY_CIĄG_PL_2>`, `<RZECZYWISTY_CIĄG_EN_1>`, `<RZECZYWISTY_CIĄG_EN_2>`, `<RZECZYWISTY_KOLOR_HEX_1>`, `<RZECZYWISTA_POZYCJA_POS_1>`, `<RZECZYWISTY_PARADYGMAT_M_1>`, `<RZECZYWISTY_PARADYGMAT_D_1>`, `<RZECZYWISTY_PARADYGMAT_W_1>`, `<WARTOŚĆ_ENUM_TECHNICZNA_1>`, `<WARTOŚĆ_ENUM_TECHNICZNA_2>`.

---

## SEKCJA 1 — ZAKRES I CEL

Operacje 9.3 obejmują:

1. **Utrwalenie operacji potwierdzonych z 9.2** (sekcja 2A) — trzy operacje zwalidowane empirycznie w EP01_post i EP02, bez nowych akcji.

2. **Nowe operacje** (sekcja 2B) — osiem operacji adresujących luki zidentyfikowane w EP01_post (N-3, N-4, N-5) i EP02 (B-4, B-5, B-6, B-7, B-9).

3. **Konflikty z 9.2** (sekcja 2C) — pięć operacji z 9.2, których wdrożenie w EP01_post i EP02 okazało się niepełne w warstwie propagacji i guardów.

Operacje 9.3 realizują Zasadę 3 Standardu 9.0 (Primary LLM Translation Authority) przez interwencję w źródło przyczyny: naprawa Fazy 1 (detekcja monologu wewnętrznego) i Fazy 2 (guard over-application), rozszerzenie arbitrażu telemetrii o P0, synchronizacja rejestru relacji. Operacje 9.3 realizują Zasadę 2 (Pure Positive Domain) przez definiowanie docelowych stanów („zachowuje", „przywraca", „utrzymuje") zamiast stanów zakazanych.

**Faza 0 — czytanie kodu (OBOWIĄZKOWA przed jakąkolwiek zmianą):**

Przed wdrożeniem operacji 2B.1–2B.8 i 2C.1–2C.5 przeczytaj w całości następujące pliki i zweryfikuj sygnatury metod oraz aktualne zachowanie:

- `avt_linter.py` — weryfikacja `EpisodeQualityGate.audit_and_fix_entire_episode`, `should_apply_top_alignment_on_collision`, `_run_phase_7_hygiene`, `normalize_ass_tags_and_sign_layout`, `preserve_italics_for_upright_style` (jeśli istnieje; w przeciwnym razie operacja 2C.4 przyjmuje formę modyfikacji `_run_phase_7_hygiene`).
- `verifier.py` — weryfikacja `DialogueVerifier.verify_batch`, `_guard_phase2_regressions` (16 kategorii z 9.2), `enforce_sign_nominative_orthography`.
- `translator.py` — weryfikacja `synchronize_ass_event_metadata_and_styles` oraz miejsca budowania prompta Fazy 1 (`build_phase1_prompt` lub odpowiednik).
- `series_memory.py` — weryfikacja `SeriesBible._sanitize_loaded_bible_in_ram`, `sync_verified_profile_entity`, `get_character_gender`, struktury `self.data["characters"]` i `self.data["relations"]`.
- `scene_discourse.py` — weryfikacja `SceneDiscourseGraph.arbitrate_event_telemetry`, `build_discourse_topology`.
- `profiler.py` — weryfikacja `EpisodeProfiler.sanitize_event_asr`, `profile_episode`, `_extract_f0_contour`.
- `metadata.py` — weryfikacja funkcji normalizacji etykiet aktorów (KROK 3).
- `flight_recorder.py` — weryfikacja `EpisodeFlightRecorder.report_step_11_quality_gate` oraz formatu raportu.

**Mapowanie P0.2 (plan ↔ kod):** dla każdej operacji z sekcji 2B/2C zapisz w raporcie tabelę: `nazwa_operacji | nazwa_metody_w_planie | nazwa_metody_w_kodzie | zgodność_sygnatury | uwagi`.

**Mapowanie P0.3 (dane testowe):** zweryfikuj dostępność rzeczywistych `SeriesBible` i `en_text` dla odcinka testowego. Placeholdery `<RZECZYWISTY_*>` wypełnij rzeczywistymi wartościami przed uruchomieniem `pytest`.

**Rozbieżności:** każdą rozbieżność „plan mówi X, kod ma Y" zapisz w raporcie i rozstrzygnij przed implementacją (kod staje się autorytetem po weryfikacji Phase 0, plan — punktem odniesienia dla intencji).

---

## SEKCJA 2 — OPERACJE

### 2A — OPERACJE POTWIERDZONE Z 9.2 (BEZ NOWYCH AKCJI)

#### 2A.1 — `enforce_sign_nominative_orthography`

- **Status w EP01_post i EP02:** 0 naruszeń.
- **Wniosek:** operacja 9.2/2B.1 działa w pełni. Walidacja ortograficzna formy M dla `is_sign: true` zachowuje poprawny stan. **Bez nowych akcji.**

#### 2A.2 — higiena tagów `is_sign` w `_run_phase_7_hygiene`

- **Status w EP01_post i EP02:** wszystkie linie `is_sign` mają pojedynczy blok tagów, parzysta równowaga `{\i1}` / `{\i0}` na planszach, separacja pasmowa poprawna.
- **Wniosek:** operacja 9.2/2C.5 (w zakresie higieny `is_sign`) działa w pełni. **Bez nowych akcji.**

#### 2A.3 — `SeriesBible._sanitize_loaded_bible_in_ram` (storage characters)

- **Status w EP01_post i EP02:** storage `characters` w RAM jest zgodny z P0 (`MALE` → `MASCULINE`, `FEMALE` → `FEMININE`), brak historycznych flag `MALE` z adnotacjami bramki.
- **Wniosek:** sanitacja warstwy `characters` w RAM działa w pełni. **Bez nowych akcji.**
- **Uwaga:** warstwa `relations` wymaga rozszerzenia w 2C.5 (patrz niżej).

---

### 2B — NOWE OPERACJE

#### 2B.1 — Detekcja monologu wewnętrznego w Fazie 1 (`translator.py`)

- **Lokalizacja:** budowanie prompta Fazy 1 (`translator.py`, funkcja `build_phase1_prompt` lub odpowiednik); kontekst wejściowy Fazy 1 zawiera metadane prozodyczne z Kroku 4.
- **Kategoria empiryczna:** brak kursywy w monologu wewnętrznym (EP01_post `[LOG:ID_147]`, EP02 `[LOG:ID_265]`).
- **Decyzja:** NAPRAWIĆ (moduł prawidłowy, ale otrzymuje niewystarczający kontekst).
- **Implementacja:**
  1. W kontekście Fazy 1 dla każdej linii przekazuj jawny znacznik `is_internal_monologue: bool`, wyliczony z metadanych Kroku 4: (a) obecność znacznika prozodycznego „cichy szept / monolog wewnętrzny" w `prosody_tags` dla danego ID, (b) pusty lub nieobecny adresat w `telemetry` przy jednoczesnym `speaker_name` obecnym, (c) brak adresata w `en_text` (heurystyka zaimkowa: brak zaimków 2. os. lp./lm. skierowanych do rozmówcy).
  2. W prompcie Fazy 1 dla linii z `is_internal_monologue: true` umieść instrukcję R1.3 (patrz Sekcja 3): „sformułuj wypowiedź jako monolog wewnętrzny; znaczniki `{\i1}...{\i0}` obejmują całą linię".
  3. W kroku post-processingu Fazy 1 (przed `phase1_text` → `dpos_text`) weryfikuj: dla linii z `is_internal_monologue: true` obecne są parzyste `{\i1}` i `{\i0}`. W przypadku braku — dodaj otaczające znaczniki w `phase1_text` (to jedyna mutacja Fazy 1 w warstwie kursywy, dopuszczona przez Zasadę 3 jako uzupełnienie niedoboru kontekstu).
- **Kryterium akceptacji:** dla każdej linii z `is_internal_monologue: true` w `phase1_text` obecne są parzyste znaczniki `{\i1}...{\i0}` obejmujące pełny tekst. Dla linii z `is_internal_monologue: false` znaczniki `{\i1}...{\i0}` obejmują wyłącznie fragmenty, które Faza 1 jawnie oznaczyła jako cytat wewnętrzny (np. przytoczona myśl).

#### 2B.2 — Guard Fazy 2 na over-application kursywy (`verifier.py`)

- **Lokalizacja:** `DialogueVerifier._guard_phase2_regressions` (nowa kategoria strażnika).
- **Kategoria empiryczna:** nadmiarowe `{\i1}` w komentarzu/dialogu z jawnym adresatem (EP02 `[LOG:ID_411]`, `[LOG:ID_412]` — komentarz spikerski; EP01_post `[LOG:ID_266]`, `[LOG:ID_267]` — pytanie do konkretnej postaci w scenie).
- **Decyzja:** NAPRAWIĆ (guard nie obejmuje kategorii „over-application kursywy na linii dialogowej z jawnym adresatem").
- **Implementacja:**
  1. W `_guard_phase2_regressions` dodaj kategorię guardu `over_application_italics`: jeśli `f1_pl` nie zawiera `{\i1}`, `refined_pl` zawiera `{\i1}`, a linia ma w `telemetry` jawnego adresata (`target_gender in (MASCULINE, FEMININE)`) oraz `is_internal_monologue: false`, przywróć `f1_pl`.
  2. Jeśli `f1_pl` zawiera `{\i1}` obejmujące fragment A, a `refined_pl` rozszerza zasięg `{\i1}` na fragment B poza A (over-extend), przywróć `f1_pl`.
- **Kryterium akceptacji:** stan wyjścia `_guard_phase2_regressions` dla linii z jawnym adresatem = brak `{\i1}...{\i0}` obejmujących pełny tekst; dla linii z `is_internal_monologue: true` = `{\i1}...{\i0}` obejmują pełny tekst.

#### 2B.3 — Spójność wewnętrzna wpisów `relations` (`series_memory.py`)

- **Lokalizacja:** `SeriesBible._sanitize_loaded_bible_in_ram` (rozszerzenie), nowa metoda pomocnicza `_validate_relation_entry_consistency`.
- **Kategoria empiryczna:** wpis relacji `[nazwa_encji_A] -> [nazwa_encji_B]` wymaga jednocześnie formy poufałej (`ty` + wołacz imienny) i formalnej (`Pan/Panie [Imię]`) — sprzeczność wewnętrzna (EP02 log KROK 6, relacja mentorka↔uczennica).
- **Decyzja:** NAPRAWIĆ (rejestr otrzymuje sprzeczne dane wejściowe z `EpisodeProfiler`).
- **Implementacja:**
  1. Nowa metoda `_validate_relation_entry_consistency` wywoływana w `_sanitize_loaded_bible_in_ram` po sanitacji `characters`.
  2. Dla każdego klucza `[nazwa_encji_A] -> [nazwa_encji_B]` w `self.data["relations"]`:
     - Wyodrębnij fragment definiujący formę adresatywną (sekcja „Zwrot: ...").
     - Wyodrębnij fragment definiujący reżim hierarchiczny (sekcja „RELACJA HIERARCHICZNA").
     - Jeśli występuje jednocześnie (a) forma poufna (jawny imienny wołacz lub konstrukcja `per ty`) i (b) reżim formalny `Pan/Panie`, rozstrzygnij sprzeczność na rzecz **asymetrii kierunkowej** zgodnie z P0: forma od mówcy o niższym `priority` do mówcy o wyższym `priority` → formalna (`Pan/Panie [Imię]`); forma odwrotna → poufna (imienny wołacz + `per ty`).
     - Zapisz rozstrzygnięcie w polu `relations` w nowym formacie: dwa kierunki jako oddzielne klucze `[A] -> [B]` (poufna) i `[B] -> [A]` (formalna), z jawnym oznaczeniem `reżim: POUFNY` lub `reżim: FORMALNY`.
  3. Wpisy bez asymetrii (obie strony `priority` równe) → forma symetryczna `per ty` po obu stronach, z wpisem pojedynczym `[A] <-> [B]`.
  4. Wszystkie modyfikacje wyłącznie w RAM, bez zapisu na dysk.
- **Kryterium akceptacji:** stan `SeriesBible.data["relations"]` w RAM po `_sanitize_loaded_bible_in_ram` = każdy wpis ma jawny `reżim: POUFNY` lub `reżim: FORMALNY`; każdy kierunek `[A] -> [B]` definiuje jedną, spójną formę adresatywną; brak wpisów zawierających jednocześnie formy poufne i formalne w jednym kluczu.

#### 2B.4 — Populacja P0 dla encji drugoplanowych z Kroku 3 (`metadata.py` + `series_memory.py`)

- **Lokalizacja:** `metadata.py` (funkcja normalizacji etykiet aktorów, KROK 3) + `SeriesBible.sync_verified_profile_entity` (KROK 6, rozszerzenie).
- **Kategoria empiryczna:** główne postacie drugoplanowe obecne w `Normalizacja etykiet aktorów` (KROK 3) i mówiące w scenach (KROK 7) nie mają wpisów P0 w `Rejestr postaci` (KROK 6). W EP02: 9 postaci drugoplanowych bez P0 (matka, przyjaciółka, strażniczka, druhny, księżniczka, maskotka itp.).
- **Decyzja:** NAPRAWIĆ (moduł `SeriesBible` prawidłowy, ale nie otrzymuje encji z Kroku 3 — `metadata.py` dostarcza, `series_memory.py` zachowuje).
- **Implementacja:**
  1. W `metadata.py` funkcja normalizacji etykiet zwraca rozszerzoną strukturę: `{clean_name: {gender_hint, source: KROK_3, confidence_hint}}` dla każdej etykiety, która pojawiła się w KROK 3.
  2. W `SeriesBible.sync_verified_profile_entity` (KROK 6) po synchronizacji encji z `EpisodeProfiler` wykonaj iterację po wszystkich `clean_name` z KROK 3: encje bez wpisu P0 (`has_verified_gender: false` lub brak w `characters`) otrzymują wpis z następującym priorytetem źródeł płci:
     - (a) `EpisodeProfiler` (P0 pełny) — jeśli dostępny.
     - (b) `gender_hint` z KROKU 3 (metadane zewnętrzne, AniList) — jeśli nie ma (a), z `priority: "P1"`, `confidence: 0.80`, `has_verified_gender: false`.
     - (c) heurystyka imienna (`-a` końcówka → FEMALE, inne → UNKNOWN) — jeśli nie ma (a) ani (b), z `priority: "P2"`, `confidence: 0.50`, `has_verified_gender: false`.
  3. Encje z `has_verified_gender: false` i `priority: "P2"` otrzymują oznaczenie `gender: "UNKNOWN"`, `grammatical_gender: "UNKNOWN"` — **nie wchodzą** do arbitrażu telemetrii jako autorytet (patrz 2C.1 pkt 4).
- **Kryterium akceptacji:** stan `SeriesBible.data["characters"]` po Kroku 6 = dla każdej etykiety z `Normalizacja etykiet aktorów` (KROK 3) istnieje wpis w `characters` z jawnym `gender` (MALE / FEMALE / UNKNOWN) i `priority` (P0 / P1 / P2).

#### 2B.5 — Integralność raportu KROKU 11 (`flight_recorder.py`)

- **Lokalizacja:** `EpisodeFlightRecorder.report_step_11_quality_gate` (nowa metoda pomocnicza `_validate_report_consistency`).
- **Kategoria empiryczna:** raport KROKU 11 deklaruje „łączna liczba poprawek: N", wylicza M < N pozycji; brak informacji o pozostałych N − M.
- **Decyzja:** NAPRAWIĆ (rejestrator otrzymuje niepełne dane wejściowe z `EpisodeQualityGate`).
- **Implementacja:**
  1. W `EpisodeQualityGate.audit_and_fix_entire_episode` zmień kontrakt zwrotny: lista poprawek jest pełna, każdy element ma unikalny `fix_id` (int). Nowa metoda `get_all_fixes()` zwraca pełną listę.
  2. W `EpisodeFlightRecorder.report_step_11_quality_gate`:
     - Wywołaj `get_all_fixes()` i zapisz pełną listę.
     - Weryfikuj `len(reported_fixes) == len(all_fixes)`. Jeśli nie — dopisz brakujące pozycje na końcu raportu z jawnym oznaczeniem `[ODZYSKANE_Z_REJESTRU]`.
     - Dodaj pole `consistency_check: {reported: N, collected: M, status: OK|MISMATCH}`.
  3. W pliku wyjściowym `.txt` dla każdej poprawki z listy `get_all_fixes()`: zweryfikuj obecność efektu w finalnym pliku (snapshot po EQG). Dla każdej poprawki, której efekt jest nieobecny w finalnym `.txt` — dodaj pozycję `[FIX_NIE_ZAAPLIKOWANY_W_PLIKU]` do raportu z jawnym wskazaniem `fix_id`.
- **Kryterium akceptacji:** stan raportu KROKU 11 = `consistency_check.status: OK` (N == M), pełna lista poprawek z efektami potwierdzonymi w finalnym `.txt`; dla każdego `fix_id` z listy `get_all_fixes()` — obecność potwierdzonego efektu w snapshot pliku wyjściowego.

#### 2B.6 — Synchronizacja pełnego paradygmatu deklinacji (`series_memory.py`)

- **Lokalizacja:** `SeriesBible.sync_verified_profile_entity`.
- **Kategoria empiryczna:** KROK 6 rejestruje paradygmat deklinacji z KROKU 5 (`EpisodeProfiler`); dla części encji paradygmat w `SeriesBible` jest zamrożony (wszystkie przypadki == M) mimo dostępności pełnej odmiany w `EpisodeProfiler`.
- **Decyzja:** NAPRAWIĆ (moduł `EpisodeProfiler` dostarcza pełne dane, `SeriesBible` ich nie przejmuje).
- **Implementacja:**
  1. W `sync_verified_profile_entity` jeśli `EpisodeProfiler` dostarcza mapę deklinacji 7 przypadków (`M, D, C, B, N, Ms, W`) i co najmniej 2 przypadki zależne (`D..W`) różnią się od `M`, nadpisz `self.data["declensions"][name]` pełnym paradygmatem z `EpisodeProfiler`.
  2. Jeśli istniejący paradygmat ma wszystkie przypadki `D..W` identyczne z `M` (zamrożony mianownik), nadpisz pełnym paradygmatem z `EpisodeProfiler` niezależnie od liczby różniących się przypadków.
  3. Dla dwuczłonowych antroponimów (`[Człon1] [Człon2]`) z deklinacją tylko drugiego członu — generuj deklinację obu członów z zachowaniem `p0_gender` (dla `MALE` — formy męskoosobowe; dla `FEMALE` — formy żeńskie).
- **Kryterium akceptacji:** stan `SeriesBible.data["declensions"][<encja>]` po Kroku 6 = pełna tożsamość z paradygmatem `EpisodeProfiler` dla wszystkich 7 przypadków dla każdej encji obecnej w `EpisodeProfiler` z dostarczoną mapą deklinacji.

#### 2B.7 — Normalizacja etykiet aktora z Kroku 3 — dopasowanie pełnotokenowe (`metadata.py`)

- **Lokalizacja:** `metadata.py`, funkcja normalizacji etykiet (KROK 3).
- **Kategoria empiryczna:** etykiety ze znacznikiem `(<M>)` / `(<F>)` propagują płcie podciągowo (`<Imię>` dopasowuje `<Imię>_rozszerzone`).
- **Decyzja:** NAPRAWIĆ.
- **Implementacja:**
  1. W normalizacji etykiet ze znacznikiem `(M)` / `(F)` porównuj `clean_name == target_clean_name` (pełnotokenowo), bez `startswith`, `in` ani regex podciągowych.
  2. Wynik normalizacji (`extracted_gender`) zawsze podporządkowany rekordowi P0 (`has_verified_gender: true`) — jeśli P0 istnieje, wynik normalizacji jest `None` (P0 autorytet).
- **Kryterium akceptacji:** stan `Normalizacja etykiet aktorów` = każda etykieta ma `extracted_gender` wyłącznie przy pełnotokenowym dopasowaniu; przy istniejącym P0 — `extracted_gender: None` i `source: P0`.

#### 2B.8 — Izolacja okna czasowego ASR (`profiler.py`)

- **Lokalizacja:** `EpisodeProfiler.sanitize_event_asr`.
- **Kategoria empiryczna:** ten sam ciąg transkrypcji ASR przypisany do dwóch zdarzeń oddalonych czasowo o > 1.5 s (przeciek bufora Whispera na sąsiednie ujęcie; EP02 ma liczne replikacje jednolitych fragmentów w kolejnych liniach).
- **Decyzja:** NAPRAWIĆ.
- **Implementacja:**
  1. Sygnatura `sanitize_event_asr(raw_asr: str, event_start: float, event_end: float, all_asr_segments: List[Tuple[float, float, str]]) -> str` — dodaj argumenty czasu i listę wszystkich segmentów ASR w odcinku.
  2. Filtruj `all_asr_segments` do tych, których przedział `[seg_start, seg_end]` mieści się w `[event_start, event_end]` (z tolerancją ±0.3 s).
  3. Jeśli w wyniku filtracji zostaje > 1 segmentu z identycznym `text` i segmenty pochodzą z różnych zdarzeń oddalonych o > 1.5 s — zachowaj tylko segment z najdłuższym pokryciem `[event_start, event_end]`, pozostałe zeruj (`""`).
  4. `en_text` pozostaje autorytetem nadrzędnym — `sanitize_event_asr` nie modyfikuje `en_text`.
- **Kryterium akceptacji:** stan `Transkrypcja japońskiego audio` w Kroku 4 = brak duplikatów identycznego tekstu między segmentami z różnych zdarzeń oddalonych o > 1.5 s; segmenty w obrębie jednego zdarzenia zachowują oryginalny tekst.

---

### 2C — KONFLIKTY Z 9.2

#### 2C.1 — `SceneDiscourseGraph.arbitrate_event_telemetry` — P0 jako autorytet nadrzędny

- **Konflikt z 9.2/2C.2:** w EP01_post i EP02 arbitraż nie respektuje P0 jako autorytetu nadrzędnego — mówcy MALE oznaczeni jako `FEMININE` w ~70% linii męskich bohaterów, adresaci w scenach F→M oznaczeni jako `FEMININE`, adresaci w scenach female-only jako `MASCULINE`. 9.2/2C.2 definiuje P0 jako autorytet, ale implementacja propaguje płeć kontekstową (default sceniczny), gdy `p0_gender` mówcy/adresata nie jest dostępne w bieżącej strukturze.
- **Rozstrzygnięcie (dowód empiryczny > analiza teoretyczna):** P0 z `SeriesBible` / `EpisodeProfiler` jest jedynym autorytetem nadrzędnym dla `Mówca:` i `Adresat:`. Default sceniczny aktywuje się wyłącznie przy `has_verified_gender: false` (P1/P2 z 2B.4), i tylko wtedy gdy 2B.4 nie dostarczy jawnie `UNKNOWN` (wtedy `telemetry` przyjmuje `UNKNOWN` i nie wymusza ani `MASCULINE`, ani `FEMININE`).
- **Implementacja:**
  1. **Jawny aktor z `[Events]`:** gdy `Name` w `[Events]` jest niepusty, niepustym `clean_name` i identyfikatorem `ANTHROPONYM` (nie enum `LABEL`/`TITLE`, nie pusty ciąg), `build_discourse_topology` zachowuje go jako `speaker_name`. Heurystyka sąsiedztwa aktywuje się wyłącznie dla pustego `Name`.
  2. **Bezpośrednie mapowanie `p0_gender`:** dla `speaker_name` i adresata odczytaj `p0_gender` z `SeriesBible`; `MALE` → `MASCULINE`, `FEMALE` → `FEMININE`. Priorytet P0 (`has_verified_gender: true`) przed P1/P2.
  3. **P1/P2 fallback:** przy `has_verified_gender: false` i `priority in (P1, P2)` z jawnym `gender` (`MALE`/`FEMALE` z 2B.4) → mapuj zgodnie z `gender`. Przy `gender: "UNKNOWN"` → `telemetry` przyjmuje `UNKNOWN`, arbitraż sąsiedztwa aktywny.
  4. **Sanitacja separatorów i grup:** niealfanumeryczny identyfikator aktora (w szczególności `/`) → `POLYLOGUE`. `All` / `Both` → `POLYLOGUE` **przy kolizji czasowej dwóch różnych `speaker_name`** w tej samej scenie (dwugłos); `All` / `Both` przy braku kolizji (spiker zbiorczy) → `speaker_name: CHÓR` z `telemetry` `Mówca: CHÓR (UNKNOWN)` i adresatem z kontekstu scenicznego.
  5. **Grupy żeńskie:** w scenie złożonej z uczestniczek o `p0_gender == "FEMALE"` emitowane są `Adresat: FEMININE`, `Grupa_1os_lm: NON_VIRILE`, `Grupa_2os_lm: NON_VIRILE`.
- **Kryterium akceptacji:** stan `telemetry` dla każdej linii = `speaker_name` identyczne z jawnym aktorem z `[Events]` (lub `POLYLOGUE`/`CHÓR` przy etykietach zbiorczych); `MASCULINE`/`FEMININE` zgodne z `p0_gender`; `UNKNOWN` wyłącznie przy `has_verified_gender: false` i `priority: P1/P2` bez dostarczonego `gender`; `NON_VIRILE` obecne w scenach żeńskich.

#### 2C.2 — `DialogueVerifier._guard_phase2_regressions` — rozszerzenie o kategorię utraty modalności 1sg

- **Konflikt z 9.2/2C.3:** guard 9.2 nie obejmuje kategorii „utrata predykatu epistemicznego/wolitywnego/modalnego 1sg na granicy F1↔F2". W EP01_post `[LOG:ID_348]` (F2 zmienia całe zdanie: „Ktoś się jeszcze spóźni" → „Czwarta zaraz do nas dołączy"), EP02 `[LOG:ID_48]` (F2 dodaje „już"), `[LOG:ID_177]` (F2 zmienia „jak poszła" → „co ustalili"), `[LOG:ID_183]` (F2 usuwa „chcę"). Skala: 4 przypadki w 2 odcinkach.
- **Rozstrzygnięcie:** guard 2C.3 z 9.2 **rozszerzony o 3 nowe kategorie**: (a) utrata 1sg czasownika wolitywnego (`chcę`, `pragnę`), (b) utrata 1sg czasownika epistemicznego (`wiem`, `sądzę`), (c) utrata 1sg czasownika modalnego (`muszę`, `mogę`, `powinnam`/`powinienem`). Kategoria (c) częściowo istnieje w 9.2 — rozszerzenie o `powinnam`/`powinienem` i o paradygmat żeński.
- **Implementacja:**
  1. W `_guard_phase2_regressions` dodaj kategorię `first_person_modal_loss`: jeśli `f1_pl` zawiera 1sg formę czasownika z listy {`chcę`, `pragnę`, `wiem`, `sądzę`, `muszę`, `mogę`, `powinnam`, `powinienem`, `mogłabym`, `mogłbym`, `chciałabym`, `chciałbym`}, a `refined_pl` nie zawiera żadnej 1sg formy (ani z tej listy, ani innej 1sg), przywróć `f1_pl`.
  2. Kategoria `predicate_shift`: jeśli `f1_pl` zawiera czasownik aspektowy dokonany (`poszła`, `zrobiła`, `ustaliła`) a `refined_pl` zawiera czasownik o innej modalności (`ustalili` — zmiana podmiotu z 3sg na 3pl), przywróć `f1_pl`.
  3. Kategoria `modal_add`: jeśli `refined_pl` zawiera partykułę modalną (`już`, `przecież`, `właśnie`) nieobecną w `f1_pl` i nieobecną w `en_text`, przywróć `f1_pl`.
  4. Kategoria `dual_voice_sync`: w logice synchronizacji dwugłosu obsługuj wszystkie warianty prefiksów dialogowych (`-`, `–`, `—` na początku wiersza). Gdy pierwszy lub drugi wiersz `source_en` (po odcięciu prefiksu) jest identyczny z `prev_line_en`, wymuś w odpowiadającym wierszu `refined_pl` tekst identyczny z `prev_line_pl` (z zachowaniem prefiksu).
  5. Kategoria `italic_balance`: jeśli `refined_pl.count("{\\i1}") != refined_pl.count("{\\i0}")` a `f1_pl.count("{\\i1}") == f1_pl.count("{\\i0}")`, przywróć `f1_pl`.
  6. Kategoria `subordinate_clause_loss`: jeśli `source_en` zawiera czasownik epistemiczny ze zdaniem dopełnieniowym identyfikującym, `f1_pl` zawiera to zdanie podrzędne, a `refined_pl` je wycina — przywróć `f1_pl`.
- **Kryterium akceptacji:** stan wyjścia `_guard_phase2_regressions` dla każdej z kategorii (a)–(f) = zachowanie `f1_pl` przy naruszeniu; zachowanie `refined_pl` przy braku naruszenia. Kategorie 9.2 (16 kategorii) zachowane.

#### 2C.3 — `EpisodeQualityGate.should_apply_top_alignment_on_collision` — test tożsamości mówcy + test zajętości pasma

- **Konflikt z 9.2/2C.4:** w EP01_post `[LOG:ID_169–171]` gate podniósł drugą połowę zdania tego samego mówcy na `\an8`, tworząc kolizję z tytułem `OBSZAR TRAWIASTY` na `\an8` (inwersja kolejności czytania). 9.2/2C.4 rozwiązuje kolizję przez podniesienie do `\an8`, nie sprawdzając (a) tożsamości mówcy między kolidującymi eventami, (b) zajętości pasma docelowego.
- **Rozstrzygnięcie:** gate aktywuje podniesienie `\an8` **wyłącznie** gdy jednocześnie spełnione są warunki: (i) dwa eventy mają różnych `speaker_name` (odrębne wypowiedzi), (ii) oba mają `Alignment == 2`, (iii) w tym samym przedziale czasowym żaden inny event (w tym `is_sign`) nie ma `Alignment in (7, 8, 9)` ani inline `\an7`/`\an8`/`\an9`, (iv) drugi event nie rozpoczyna się wielokropkiem ani małą literą (kontynuacja).
- **Implementacja:**
  1. W pętli kolizji w `audit_and_fix_entire_episode` dla pary nakładających się eventów (A, B):
     - Odczytaj `Alignment` A i B z tabeli `[V4+ Styles]` (w tym po nazwie stylu `Main - Top`, `Italics - Top`, `Flashback - Top`, `ep title`).
     - Odczytaj tagi inline `\an7`, `\an8`, `\an9` z pola `Text` A i B oraz wszystkich innych eventów aktywnych w tym samym przedziale czasowym (w tym `is_sign`).
     - Jeśli `Alignment_A in (7, 8, 9)` lub `Alignment_B in (7, 8, 9)` lub jakikolwiek inline `\an7/\an8/\an9` aktywny w tym przedziale → `should_apply_top_alignment_on_collision` zwraca `False`.
     - Jeśli `speaker_name_A == speaker_name_B` (lub oba puste i tekst B zaczyna się od wielokropka lub małej litery) → `should_apply_top_alignment_on_collision` zwraca `False` (kontynuacja zdania → scal w jednym evencie w paśmie dolnym przez `\N`, zachowaj kolejność czytania).
     - W przeciwnym razie → `True`.
  2. Rozstrzygnięcie kolizji zachowuje 100% treści z `dpos_text` (w tym powtórzone okrzyki imion, przerywniki, wykrzykniki).
- **Kryterium akceptacji:** stan pozycjonowania kolizji w EQG = `\an8` przypisane wyłącznie przy parze różnych mówców, oba `Alignment == 2`, wolne pasmo górne, brak kontynuacji (wielokropek/mała litera na początku B). Treść `dpos_text` zachowana w 100%.

#### 2C.4 — `EpisodeQualityGate._run_phase_7_hygiene` — rekurencyjne scalanie tagów + separacja `is_sign` + ciągłość kursywy

- **Konflikt z 9.2/2C.5:** higiena 9.2 działa w zakresie `is_sign`, ale nie obsługuje: (a) rekurencyjnego scalania > 2 bloków `{\...}`, (b) osieroconych `{\i0}` po domkniętym `{\i1}...{\i0}`, (c) separacji `is_sign` z dolnym `\pos()` w dolnych 20% ekranu od dwuwierszowego dialogu dolnego.
- **Rozstrzygnięcie:** rozszerzenie `_run_phase_7_hygiene` o 3 nowe pod-operacje, z zachowaniem istniejących.
- **Implementacja:**
  1. **Scalanie rekurencyjne:** pętla dopóki `re.search(r'\{\\[^{}]+\}\{\\[^{}]+\}', text)`: scal dwa sąsiadujące bloki na początku linii w jeden blok `{\tag1\tag2...}` z zachowaniem kolejności atrybutów. Przy duplikacji (`\3c` wielokrotny, `\1c`, `\bord`, `\shad`) zachowaj wartość specyficzną z oryginalnego bloku napisu (np. `\shad0`, niestandardowy `\3c`) ponad domyślnym `{\3c&H000000&\bord3\shad1}`.
  2. **Osierocone `{\i0}`:** skanuj każdą linię. Dla każdego domknięcia `{\i0}` bez poprzedzającego otwarcia `{\i1}` — usuń. Dla nadmiarowego `{\i0}` po poprawnie domkniętym `{\i1}...{\i0}` — usuń.
  3. **Separacja `is_sign`:** gdy event `is_sign: true` (bez aktora dialogowego) nakłada się czasowo z dialogiem dolnym (`Alignment == 2`), a ma `Alignment in (1, 2, 3)` lub `\pos(x,y)` z `y >= 0.80 * PlayResY`, zmień `Alignment` na górne (`\an8`).
  4. **Ciągłość kursywy monologu:** dla linii z `is_internal_monologue: true` (z 2B.1) — obecność parzystych `{\i1}...{\i0}`. Dla linii sąsiadującej z linią kursywą tego samego mówcy, rozpoczynającej się od `...` — parzyste `{\i1}...{\i0}`. Dla linii z jawnym adresatem (komentarz, dialog) — brak `{\i1}...{\i0}` obejmujących pełny tekst (zgodnie z 2B.2).
- **Kryterium akceptacji:** stan `ass_text` po `_run_phase_7_hygiene` = pojedynczy blok `{\...}` na każdej linii, parzysta równowaga `{\i1}` i `{\i0}`, `is_sign` w górnym paśmie przy kolizji z dialogiem, kursywa zgodna z `is_internal_monologue` i brakiem jawnego adresata.

#### 2C.5 — `SeriesBible._sanitize_loaded_bible_in_ram` — propagacja do `relations`

- **Konflikt z 9.2/2C.1:** 9.2/2C.1 sanitizuje `characters` (potwierdzone w 2A.3), ale nie propaguje zweryfikowanego `p0_gender` do tekstu wpisów `relations`. Wpisy relacji zachowują historyczne flagi męskie dla adresatów żeńskich.
- **Rozstrzygnięcie:** rozszerzenie sanitacji o iterację po `relations` z aktualizacją fragmentów adresatywnych na podstawie `p0_gender` adresata.
- **Implementacja:**
  1. Po sanitacji `characters` (2A.3) iteruj po `self.data["relations"]`. Dla każdego klucza `[A] -> [B]` (lub `[A] <-> [B]`):
     - Odczytaj `p0_gender` adresata `B` z oczyszczonego `characters`.
     - W tekście relacji znajdź fragmenty definiujące formy adresatywne w 2. os. lp. (końcówki `-aś`, `-ałaś`, `-eś`, `-łeś`, zaimki `ty`, `ciebie`, formy `jesteś pewna`/`jesteś pewien`).
     - Zaktualizuj te fragmenty zgodnie z `p0_gender[B]`: `FEMALE` → formy żeńskie, `MALE` → formy męskie, `UNKNOWN` → formy neutralne lub zachowaj oryginalne z jawnym oznaczeniem `[DO_WERYFIKACJI]`.
  2. Jeśli wpis zawiera nagłówek `[KOBIETA (Adresat)]` a `p0_gender[B] == "MALE"` — zamień na `[MĘŻCZYZNA (Adresat)]`; odwrotnie — zamień `[MĘŻCZYZNA (Adresat)]` na `[KOBIETA (Adresat)]` przy `p0_gender[B] == "FEMALE"`.
  3. Wywołaj `_validate_relation_entry_consistency` z 2B.3 po aktualizacji.
  4. Wszystkie modyfikacje wyłącznie w RAM.
- **Kryterium akceptacji:** stan `SeriesBible.data["relations"]` w RAM po `_sanitize_loaded_bible_in_ram` = każdy wpis ma formy adresatywne zgodne z `p0_gender` adresata; brak wpisów z niespójnością form żeńskich/męskich wobec `p0_gender`; wpisy z `p0_gender == "UNKNOWN"` jawnie oznaczone `[DO_WERYFIKACJI]`.

---

## SEKCJA 3 — REGUŁY PIPELINE

### Reguły LLM (Faza 1, Faza 2)

**R1.1 (P0):** Wypowiedzi o mówcy `p0_gender == "FEMALE"` w 1. os. lp. czasu przeszłego zachowują formy żeńskie. Zwroty do adresata `p0_gender == "FEMALE"` w 2. os. lp. zachowują formy żeńskie. Zwroty do grupy `p0_gender == "FEMALE"` zachowują formy niemęskoosobowe (`NON_VIRILE`).

**R1.2 (P0):** Osoba i liczba orzeczenia w `phase1_text` są zgodne z podmiotem `en_text`. Podmiot 1. os. lp. w `en_text` zachowuje orzeczenie w 1. os. lp. niezależnie od liczby dopełnienia.

**R1.3 (P0):** Czasowniki epistemiczne, wolitywne i modalne (1. os. lp.) obecne w `en_text` i `phase1_text` zachowują się w `refined_pl`. Zdania podrzędne dopełnieniowe identyfikujące (`że to ty`, `że to [nazwa]`) zachowują się w `refined_pl`.

**R1.4 (P1):** Dwugłos z powtórzonym wierszem z poprzedniej linii zachowuje identyczne sformułowanie w `refined_pl` (w obu wierszach).

**R1.5 (P2):** Krótkie napisy `is_sign: true` zachowują semantyczną i leksykalną odpowiedniość 1:1 wobec `en_text` w formie mianownika `M`.

**R1.6 (P0):** `en_text` oraz jawny aktor z kolumny `Name` w `[Events]` mają pierwszeństwo nad transkrypcją ASR. Mówca i adresat są zgodni z `p0_gender` z `SeriesBible`.

**R1.7 (P0):** Rodzaj 1. os. czasu przeszłego (`-łem` / `-łam`) jest zgodny z `p0_gender` mówcy.

**R1.8 (P1):** Pełna deklinacja obu członów antroponimów dwuczłonowych w wołaczu `W` i przypadkach `D..Ms` jest zgodna z paradygmatem z `EpisodeProfiler`.

**R1.9 (P0 — nowa, 2B.1/2B.2):** Linia z `is_internal_monologue: true` zachowuje parzyste znaczniki `{\i1}...{\i0}` obejmujące pełny tekst. Linia z jawnym adresatem i `is_internal_monologue: false` zachowuje brak `{\i1}` obejmującego pełny tekst.

**R1.10 (P0 — nowa, 2C.2):** Linia z 1. os. czasownika wolitywnego/epistemicznego/modalnego w `phase1_text` zachowuje 1. os. czasownika w `refined_pl`. Linia bez partykuły modalnej w `phase1_text` i `en_text` zachowuje brak partykuły w `refined_pl`.

### Reguły pipeline

**R3.1 (P0):** `SeriesBible.data["characters"]` i `SeriesBible.data["relations"]` w RAM zachowują zgodność `p0_gender` ze źródłem (P0 z `EpisodeProfiler`, P1/P2 z KROKU 3). Wpisy `relations` zachowują spójność form adresatywnych zgodnie z `_validate_relation_entry_consistency`.

**R3.2 (P0):** `telemetry` w Kroku 7 zachowuje `speaker_name` zgodne z jawnym aktorem z `[Events]`, `MASCULINE`/`FEMININE` zgodne z `p0_gender`, `POLYLOGUE` dla etykiet zbiorczych `All`/`Both` przy kolizji czasowej, `CHÓR` przy braku kolizji, `NON_VIRILE` w scenach female-only.

**R3.3 (P0):** `_guard_phase2_regressions` zachowuje `refined_pl` przy braku naruszenia i `phase1_text` przy naruszeniu w kategoriach: `first_person_modal_loss`, `predicate_shift`, `modal_add`, `dual_voice_sync`, `italic_balance`, `subordinate_clause_loss` oraz 16 kategoriach z 9.2.

**R3.4 (P0):** `EpisodeQualityGate.should_apply_top_alignment_on_collision` zwraca `True` wyłącznie przy parze różnych mówców, oba `Alignment == 2`, wolnym paśmie górnym, braku kontynuacji (wielokropek/mała litera). Treść `dpos_text` zachowana w 100%.

**R3.5 (P0):** Raport KROKU 11 zachowuje spójność `consistency_check.status: OK` przy `N == M`; efekt każdego `fix_id` z `get_all_fixes()` potwierdzony w snapshot pliku wyjściowego.

---

## SEKCJA 4 — WALIDACJA TESTOWA

**Zasada 8 (niedegradacyjność) — stosowana do wszystkich testów 4.1–4.15:** (a) weryfikacja kategorii, nie instancji; (b) asercja w kategoriach metajęzyka architektury; (c) oczekiwana wartość z P0/EN; (d) falsyfikowalny (mutacja w kodzie → FAILED); (e) parametryzowany na ≥2 różnych wejściach. Placeholdery `<RZECZYWISTY_*>` wypełniane rzeczywistymi wartościami z `SeriesBible` / `en_text` odcinka testowego przed uruchomieniem.

Testy 4.1–4.15 są **wzorcami strukturalnymi**. Nazwy metod, sygnatury i dane testowe wymagają adaptacji do rzeczywistego kodu po Phase 0.

### 4.1 — `test_phase1_adds_internal_monologue_italics` (2B.1)

- **Plik:** `tests/test_translator.py`
- **Sygnatura:** `test_phase1_adds_internal_monologue_italics(is_internal_monologue, expected_has_italics)`
- **Parametryzacja:** dwa przypadki — `(True, True)` z `<RZECZYWISTY_CIĄG_PL_1>` wewnętrznym; `(False, False)` z `<RZECZYWISTY_CIĄG_PL_2>` dialogiem.
- **Weryfikacja:** linia z `is_internal_monologue: true` ma parzyste `{\i1}` / `{\i0}`; linia z `false` ma brak `{\i1}` obejmującego pełny tekst.
- **Falsyfikowalność:** usunięcie detekcji w 2B.1 pkt 3 → FAILED dla przypadku 1.

### 4.2 — `test_guard_removes_italics_on_addressed_dialogue` (2B.2)

- **Plik:** `tests/test_verifier.py`
- **Sygnatura:** `test_guard_removes_italics_on_addressed_dialogue(f1_without_italics, f2_with_italics, addressee_gender, expected_pl)`
- **Parametryzacja:** dwa przypadki — `<RZECZYWISTY_CIĄG_PL_1>` (F1 bez `{\i1}`, F2 z `{\i1}`, adresat `FEMININE`) → `expected` = F1; `<RZECZYWISTY_CIĄG_PL_2>` (F1 z `{\i1}` na fragmencie, F2 z `{\i1}` na pełnym) → `expected` = F1.
- **Falsyfikowalność:** wyłączenie kategorii `over_application_italics` → FAILED obu przypadków.

### 4.3 — `test_relation_entry_consistency_resolves_asymmetry` (2B.3)

- **Plik:** `tests/test_series_memory.py`
- **Sygnatura:** `test_relation_entry_consistency_resolves_asymmetry(source_priority, target_priority, target_p0_gender, expected_reżim)`
- **Parametryzacja:** `(P0, P2, FEMALE, FORMALNY)`, `(P2, P0, MALE, FORMALNY)`, `(P1, P1, FEMALE, POUFNY)`.
- **Weryfikacja:** wynik `_validate_relation_entry_consistency` = reżim zgodny z asymetrią `priority`; brak jednocześnie `POUFNY` i `FORMALNY` w jednym wpisie.
- **Falsyfikowalność:** wyłączenie `_validate_relation_entry_consistency` → FAILED dla pierwszego przypadku (pozostaje sprzeczność).

### 4.4 — `test_secondary_characters_receive_p1_p2_entries` (2B.4)

- **Plik:** `tests/test_metadata.py`
- **Sygnatura:** `test_secondary_characters_receive_p1_p2_entries(actor_label, gender_hint, expected_priority, expected_gender)`
- **Parametryzacja:** `(<RZECZYWISTY_ANTROPONIM_1>, FEMALE, P1, FEMALE)`, `(<RZECZYWISTY_ANTROPONIM_2>, None, P2, UNKNOWN)`.
- **Weryfikacja:** po Kroku 6 encja ma wpis w `characters` z `priority` zgodnym z hierarchią źródeł, `gender` zgodnym z `gender_hint` (P1) lub `UNKNOWN` (P2).
- **Falsyfikowalność:** pominięcie iteracji w 2B.4 pkt 2 → FAILED (encja nieobecna).

### 4.5 — `test_flight_report_consistency_check` (2B.5)

- **Plik:** `tests/test_flight_recorder.py`
- **Sygnatura:** `test_flight_report_consistency_check(all_fixes, reported_fixes, expected_status)`
- **Parametryzacja:** `([f1, f2, f3], [f1, f2], "MISMATCH")`, `([f1, f2], [f1, f2], "OK")`.
- **Weryfikacja:** raport zawiera `consistency_check: {reported: N, collected: M, status: OK|MISMATCH}` oraz brakujące pozycje oznaczone `[ODZYSKANE_Z_REJESTRU]` przy MISMATCH.
- **Falsyfikowalność:** pominięcie weryfikacji w `report_step_11_quality_gate` → FAILED dla MISMATCH.

### 4.6 — `test_sync_profile_entity_transfers_full_paradigm` (2B.6)

- **Plik:** `tests/test_series_memory.py`
- **Sygnatura:** `test_sync_profile_entity_transfers_full_paradigm(entity_name, profiler_paradigm, expected_W)`
- **Parametryzacja:** `<RZECZYWISTY_ANTROPONIM_MĘSKI_1>` z pełnym paradygmatem `M/D/C/B/N/Ms/W` i oczekiwanym `W = <RZECZYWISTY_PARADYGMAT_W_1>`; `<RZECZYWISTY_ANTROPONIM_ŻEŃSKI_1>` z oczekiwanym `W = <RZECZYWISTY_PARADYGMAT_W_2>`.
- **Weryfikacja:** `SeriesBible.data["declensions"][entity_name]["W"]` = oczekiwany `W` z `EpisodeProfiler`; wszystkie przypadki `M..W` zgodne z paradygmatem.
- **Falsyfikowalność:** pominięcie nadpisania w `sync_verified_profile_entity` → FAILED (pozostaje zamrożony mianownik).

### 4.7 — `test_actor_normalization_exact_token` (2B.7)

- **Plik:** `tests/test_metadata.py`
- **Sygnatura:** `test_actor_normalization_exact_token(actor_label, p0_gender, expected_extracted_gender)`
- **Parametryzacja:** `(<RZECZYWISTY_ANTROPONIM_1>_rozszerzone z (F), FEMALE, None)`, `(<RZECZYWISTY_ANTROPONIM_2> bez P0 z (M), None, MALE)`.
- **Weryfikacja:** etykieta rozszerzona nie dopasowuje `(F)` z krótszej etykiety; etykieta bez P0 zachowuje `extracted_gender`.
- **Falsyfikowalność:** pozostawienie dopasowania podciągowego → FAILED dla przypadku 1 (błędnie `extracted_gender: FEMALE`).

### 4.8 — `test_sanitize_event_asr_isolates_duplicate_out_of_window` (2B.8)

- **Plik:** `tests/test_profiler.py`
- **Sygnatura:** `test_sanitize_event_asr_isolates_duplicate_out_of_window(event_window, all_segments, expected_asr)`
- **Parametryzacja:** `((10.0, 15.0), [(10.5, 12.0, "<RZECZYWISTY_CIĄG_EN_1>"), (20.0, 22.0, "<RZECZYWISTY_CIĄG_EN_1>")], "<RZECZYWISTY_CIĄG_EN_1>")`, `((10.0, 15.0), [(10.5, 12.0, "<RZECZYWISTY_CIĄG_EN_1>"), (11.0, 13.0, "<RZECZYWISTY_CIĄG_EN_1>")], "<RZECZYWISTY_CIĄG_EN_1>")`.
- **Weryfikacja:** duplikat oddalony o > 1.5 s (przypadek 1) jest odfiltrowany; duplikat w oknie (przypadek 2) zachowany (wewnątrz okna).
- **Falsyfikowalność:** pominięcie filtracji `[seg_start, seg_end] ⊂ [event_start, event_end]` → FAILED dla przypadku 1 (dwa segmenty).

### 4.9 — `test_arbitrate_telemetry_respects_p0_over_scene_default` (2C.1)

- **Plik:** `tests/test_discourse_and_translator.py`
- **Sygnatura:** `test_arbitrate_telemetry_respects_p0_over_scene_default(explicit_actor, p0_gender, scene_default_gender, expected_gram_gender)`
- **Parametryzacja:** `(<RZECZYWISTY_ANTROPONIM_MĘSKI_1>, MALE, FEMININE, MASCULINE)` (P0 wygrywa nad defaultem scenicznym), `(<RZECZYWISTY_ANTROPONIM_ŻEŃSKI_1>, FEMALE, MASCULINE, FEMININE)`.
- **Weryfikacja:** `telemetry.grammatical_gender` zgodne z `p0_gender`, ignorując `scene_default_gender`.
- **Falsyfikowalność:** pozostawienie defaultu scenicznego jako nadrzędnego → FAILED obu przypadków.

### 4.10 — `test_guard_phase2_preserves_first_person_modal` (2C.2)

- **Plik:** `tests/test_verifier.py`
- **Sygnatura:** `test_guard_phase2_preserves_first_person_modal(f1_pl, f2_pl, expected_pl)`
- **Parametryzacja:** `("...- <forma 1sg wolitywna> odejść...\n- ...", "...- odejdę...\n- ...", "...- <forma 1sg wolitywna> odejść...\n- ...")` (guard przywraca F1); `("<RZECZYWISTY_CIĄG_PL_1>", "<RZECZYWISTY_CIĄG_PL_1>", "<RZECZYWISTY_CIĄG_PL_1>")` (brak naruszenia, F2 zachowane).
- **Weryfikacja:** utrata 1sg wolitywnego → guard przywraca `phase1_text`; brak naruszenia → `refined_pl` zachowane.
- **Falsyfikowalność:** wyłączenie kategorii `first_person_modal_loss` → FAILED dla przypadku 1.

### 4.11 — `test_collision_respects_top_band_and_speaker_identity` (2C.3)

- **Plik:** `tests/test_avt_linter.py`
- **Sygnatura:** `test_collision_respects_top_band_and_speaker_identity(alignment_a, alignment_b, speaker_a, speaker_b, text_b_starts_with, has_top_active, expected_lift)`
- **Parametryzacja:** `(2, 2, "", "", "...", True, False)`, `(2, 2, "<RZECZYWISTY_ANTROPONIM_1>", "<RZECZYWISTY_ANTROPONIM_2>", "Wielka litera", False, True)`.
- **Weryfikacja:** kolizja z kontynuacją (wielokropek) → `False`; odrębni mówcy, wolne pasmo, wielka litera → `True`.
- **Falsyfikowalność:** pominięcie testu `has_top_active` lub `text_b_starts_with` → FAILED dla przypadku 1 (błędnie `True`).

### 4.12 — `test_phase7_recursive_tag_merge_and_orphan_i0_strip` (2C.4)

- **Plik:** `tests/test_avt_linter.py`
- **Sygnatura:** `test_phase7_recursive_tag_merge_and_orphan_i0_strip(raw_text, expected_text)`
- **Parametryzacja:** `("{\\tagA}{\\tagB}{\\tagC}<RZECZYWISTY_CIĄG_PL_1>", "{\\tagA\\tagB\\tagC}<RZECZYWISTY_CIĄG_PL_1>")`, `("{\\i1}<RZECZYWISTY_CIĄG_PL_2>{\\i0} dalszy{\\i0}", "{\\i1}<RZECZYWISTY_CIĄG_PL_2>{\\i0} dalszy")`.
- **Weryfikacja:** 3 bloki scalone w 1; osierocony `{\i0}` usunięty.
- **Falsyfikowalność:** pominięcie pętli rekurencyjnej (scalanie tylko 2 bloków) → FAILED dla przypadku 1.

### 4.13 — `test_sanitize_relations_propagates_p0_gender` (2C.5)

- **Plik:** `tests/test_series_memory.py`
- **Sygnatura:** `test_sanitize_relations_propagates_p0_gender(target_entity, target_p0_gender, relation_text_with_male, expected_relation_text_fragment)`
- **Parametryzacja:** `(<RZECZYWISTY_ANTROPONIM_ŻEŃSKI_1>, FEMALE, "[MĘŻCZYZNA (Adresat)]", "[KOBIETA (Adresat)]")`, `(<RZECZYWISTY_ANTROPONIM_MĘSKI_1>, MALE, "[KOBIETA (Adresat)]", "[MĘŻCZYZNA (Adresat)]")`.
- **Weryfikacja:** po `_sanitize_loaded_bible_in_ram` wpis relacji ma fragment adresatywny zgodny z `p0_gender`.
- **Falsyfikowalność:** pominięcie iteracji po `relations` w 2C.5 → FAILED obu przypadków.

### 4.14 — `test_regression_B4_semantic_drift_guard` (regresja B-4)

- **Plik:** `tests/test_verifier.py`
- **Sygnatura:** `test_regression_B4_semantic_drift_guard(f1_pl, f2_pl, en_src, expected_pl)`
- **Parametryzacja:** `(<RZECZYWISTY_CIĄG_PL_1 z 1sg epistemicznym>, <RZECZYWISTY_CIĄG_PL_2 bez 1sg>, <RZECZYWISTY_CIĄG_EN_1>, <RZECZYWISTY_CIĄG_PL_1>)`, `(<RZECZYWISTY_CIĄG_PL_3 z partykułą X>, <RZECZYWISTY_CIĄG_PL_4 z partykułą Y>, <RZECZYWISTY_CIĄG_EN_2>, <RZECZYWISTY_CIĄG_PL_3>)`.
- **Weryfikacja:** guard wykrywa drift i przywraca F1 w obu przypadkach (utrata 1sg epistemicznego, dodanie partykuły nieobecnej w EN).
- **Falsyfikowalność:** wyłączenie kategorii `first_person_modal_loss` lub `modal_add` → FAILED odpowiednio.

### 4.15 — `test_regression_B5_italics_over_application` (regresja B-5)

- **Plik:** `tests/test_verifier.py`
- **Sygnatura:** `test_regression_B5_italics_over_application(f1_pl, f2_pl, addressee_present, expected_pl)`
- **Parametryzacja:** `(<RZECZYWISTY_CIĄG_PL_1>, "{\\i1}<RZECZYWISTY_CIĄG_PL_1>{\\i0}", True, <RZECZYWISTY_CIĄG_PL_1>)` (adresat obecny → F1); `(<RZECZYWISTY_CIĄG_PL_2>, "{\\i1}<RZECZYWISTY_CIĄG_PL_2>{\\i0}", False, "{\\i1}<RZECZYWISTY_CIĄG_PL_2>{\\i0}")` (brak adresata → F2 zachowane).
- **Weryfikacja:** over-application na linii z adresatem → F1 przywrócone; bez adresata → F2 zachowane.
- **Falsyfikowalność:** wyłączenie kategorii `over_application_italics` w 2B.2 → FAILED dla przypadku 1.

---

## SEKCJA 5 — WARUNKI UKOŃCZENIA

Wdrożenie uznaje się za zakończone wyłącznie przy jednoczesnym spełnieniu warunków (a)–(h):

- (a) Wszystkie operacje z sekcji 2B.1–2B.8 i 2C.1–2C.5 wdrożone w kodzie produkcyjnym.
- (b) Wszystkie reguły z sekcji 3 (R1.1–R1.10, R3.1–R3.5) zaaplikowane w promptach Fazy 1 / Fazy 2 / pipeline.
- (c) Wszystkie testy z sekcji 4 (4.1–4.15) zaimplementowane z adaptacją sygnatur i placeholderów `<RZECZYWISTY_*>` wypełnionych rzeczywistymi wartościami.
- (d) `pytest -v --tb=short` zwraca 100% PASSED (`0 FAILED`, `0 ERROR`).
- (e) `verify_purity.py`, `verify_ultimate_pipeline.py`, `verify_12_fixes.py` — PASS 100%.
- (f) `audit_diff.ps1` — VICTORY CONFIRMED; `git status` na plikach `.ass`, `.srt`, `.json` (bazy wiedzy) — czysty.
- (g) Każdy test z sekcji 4 zweryfikowany pod kątem falsyfikowalności: mutacja w kodzie (wyłączenie kategorii guardu, pominięcie iteracji, usunięcie detekcji) → test FAILED.
- (h) Raport ukończenia zawiera: tabelę mapowania P0.2 (plan ↔ kod), tabelę P0.3 (dane testowe), wynik `pytest`, wynik bramek, listę rozbieżności „plan mówi X, kod ma Y", potwierdzenie falsyfikowalności każdego testu.

**Uwaga o 2A:** operacje 2A.1, 2A.2, 2A.3 są potwierdzone z 9.2 i nie wymagają nowych testów. Ich utrzymanie weryfikuje się przez pełny zestaw testów 9.2 (31 + 13 z `test_standard_9_2`), który pozostaje w mocy.