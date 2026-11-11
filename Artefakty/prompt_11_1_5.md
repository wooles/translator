
# ROZKAZ WYKONAWCZY — HOTFIX 11.1.5 (USZCZELNIENIE TELEMETRII DYSKURSU, WALIDACJI REJESTRU I IN-MEMORY SANITACJI SERIESBIBLE)

- **Repozytorium:** `https://github.com/wooles/translator` (gałąź `main`)[cite: 6]
- **Punkt wyjścia (HEAD):** `dd950ba13e10e77d9888b30e8795922ef5299347` (`dd950ba`)[cite: 6]
- **Baseline Z16 (Depuracja Legacy 1.0):** `a6d40bb09d60b2d986d919de98044c6e2d9c838b` (`a6d40bb`) — **0 B diff na plikach chronionych**[cite: 6]
- **Podstawa wdrożenia:** `Artefakty/Raport_audytu_operacyjnego_2026-11-11.md` (Incydenty `INC-AVT-026`, `INC-AVT-027` oraz zdarzenia `E-01`..`E-11` z przebiegu `20261111_211338`)
- **Docelowy standard:** `Standard 11.1.5 (Discourse Telemetry & Sociolinguistic Gate Certified)`

---

## 0. RYGORY NADRZĘDNE (OBOWIĄZUJĄ PRZEZ CAŁY CZAS PRACY)

1. **Z1 Zero-Literal:** W kodzie `.py`, testach `tests/*.py`, komentarzach, docstringach i promptach zachowaj całkowitą abstrakcję od nazw własnych z jakichkolwiek serii anime/mang[cite: 6]. W testach jednostkowych stosuj wyłącznie generyczne identyfikatory syntetyczne (np. `Character_Alpha`, `Speaker_One`, `Northern_Kingdom`, `Artisan_Lead`).
2. **Z2 Pure Positive Domain:** Wszystkie docstringi, komentarze, komunikaty logowania i instrukcje formułuj w domenie pozytywnej (opisującej pożądany stan docelowy). Unikaj słów preskryptywnych sprawdzanych przez `verify_purity.py` (Bramka 5B)[cite: 6].
3. **Z3 Primary LLM Authority:** Zachowaj pasywność warstwy post-processingu (`VARIANT_D_PURE_LLM_MORPHOLOGY = True` w `avt_linter.py` pozostaje bez zmian)[cite: 4, 5, 6].
4. **Z4 Instance-Free:** Wszystkie reguły działają w oparciu o cechy strukturalne, gramatyczne i akustyczne, bez odwołań do konkretnych tytułów[cite: 6].
5. **Z16 Depuracja Legacy 1.0 (0 B DIFF):** Pliki `test_system.py`, `tests/archive/*`, `avt_linter.py`, `pytest.ini`, `rules.py`, `verifier.py`, `verify_purity.py`, `series_memory/*_bible.json` oraz `series_memory/.onomastic_lexicon.json` pozostają w stanie identycznym z baseline'em `a6d40bb` (`git diff a6d40bb..HEAD -- <pliki_Z16>` musi zwracać `0 B`)[cite: 6]. Wszelką korektę zastałych danych z `*_bible.json` wykonuj **w pamięci operacyjnej (`in-memory`)** podczas ładowania i scalania w `series_memory.py`[cite: 4, 5, 6].

---

## 1. ZADANIA INŻYNIERSKIE DO WDROŻENIA

### ZADANIE 1 (P1-1 / INC-AVT-026 / E-04): Bramkowanie tagów socjolingwistycznych `Rejestr:` przez profil postaci (`whisper_disambiguator.py` / `scene_discourse.py`)

**Problem z audytu:**
W przebiegu `20261111_211338` w 50 z 330 linii (`15,1%`) do pola `telemetry_tag` zostały wstrzyknięte dynamiczne etykiety rejestru sprzeczne z profilem mówcy z powodu przesunięć okien czasowych Whisper ASR i szumu fonetycznego[cite: 4, 5]:
- `Rejestr: Rejestr dziewczęcy` dla dorosłych i sędziwych mężczyzn (`[ID: 185, 186, 229, 232, 312]`)[cite: 4, 5],
- `Rejestr: Szorstki żołnierski / Bojowy` dla dziesięcioletniej arystokratki (`[ID: 15, 16]`) oraz uprzejmego urzędnika w dialogu dworskim (`[ID: 297, 298, 301]`)[cite: 4, 5],
- `Rejestr: Feudalny poddańczy / Wasal` dla porannego powitania `"おはようございます"` we współczesnym biurze (`[ID: 150, 151]`)[cite: 4, 5].

**Wymagana implementacja (`whisper_disambiguator.py` i/lub `scene_discourse.py`):**
1. Przed dołączeniem dynamicznej etykiety `Rejestr: <nazwa_rejestru>` do `telemetry_tag` wprowadź deterministyczną funkcję weryfikującą zgodność wykrytego rejestru z metadanymi mówcy (`character_dossiers` z `episode_profile` oraz `character_registry` z `series_bible`)[cite: 4, 5, 6]:
   - Etykieta `Rejestr dziewczęcy` jest dopuszczalna wyłącznie wtedy, gdy zweryfikowana płeć mówcy to `FEMALE` (`FEMININE`), a klasa wieku to `CHILD`, `TEEN` lub młoda `ADULT`[cite: 4, 5]. Dla mówców o płci `MALE` (`MASCULINE`) lub klasie `ELDERLY` zaimek `watashi` w audio JP jest naturalnym sygnałem rejestru formalnego/dworskiego i nie aktywuje rejestru dziewczęcego[cite: 4, 5].
   - Etykieta `Szorstki żołnierski / Bojowy` jest pomijana dla mówców posiadających w `character_dossiers` (`dialect_category` / `speech_style_pl`) zdefiniowany rejestr wysoki, dworski, arystokratyczny lub formalno-urzędowy, chyba że dana linia posiada jednocześnie znacznik akustyczny `krzyk bojowy / silne wzburzenie emocjonalne` w `prosody_tags`[cite: 4, 5].
   - Etykieta `Feudalny poddańczy / Wasal` dla standardowych formuł grzecznościowych (`ohayou gozaimasu`, `moushiwake arimasen`, `shitsurei shimasu`) jest aktywowana wyłącznie wtedy, gdy w linii występują jednoznaczne archaizmy feudalne (np. sufiksy `-dono`, `koushaku`, `danshaku`) i rozmowa toczy się w domenie historycznej/fantasy, a dla standardowego keigo biurowego pozostaje neutralna[cite: 4, 5].
   - Etykiety `Rejestr gwarowy południowy` / `Rejestr gwarowy zachodni` wymagają potwierdzenia, że postać nie ma w `character_dossiers[].dialect_category` zdefiniowanej `"standardowa polszczyzna literacka"` lub `"archaizowana polszczyzna dworska"` (chyba że dialekt jest cechą idiolektu danej postaci, jak `douja` / `noja`)[cite: 4, 5].

---

### ZADANIE 2 (P1-2 / E-01 / E-02 / E-07): In-Memory Sanitacja `SeriesBible` przy ładowaniu i scalaniu z `EpisodeProfile` (`series_memory.py`)

**Problem z audytu:**
1. **Konflikt płci (`E-01`):** W zastałej bazie serii postacie żeńskie mają wpisane `"gender": "MALE"`, `"has_verified_gender": true`, `"confidence": 0.95`, `"priority": "P0"`[cite: 4, 5]. Nawet gdy `episode_profile` (`name_declensions`) oraz `series_bible.relations` jednoznacznie wskazują `FEMALE` (`[KOBIETA (Adresat)]`), `character_registry` zachowuje `MALE`, co wymusza błędny `MASCULINE` w `telemetry_tag` (`[ID: 150..179]`)[cite: 4, 5].
2. **Toponimy i nazwy pospolite jako `ANTHROPONYM` (`E-02`):** Nazwy geograficzne (np. królestwa, równiny) oraz angielskie rzeczowniki relacyjne (`Mother`, `Boyfriend`) widnieją w `character_registry` jako `entity_category: "ANTHROPONYM"` (`priority: "P0"`), przez co trafiają do sekcji `ZNANE POSTACIE W BIEŻĄCEJ SCENIE` i są blokowane jako adresaci dialogu (`lock=True`)[cite: 4, 5].
3. **Nieodmienne paradygmaty (`E-07`):** W `series_bible.declensions` główne nazwisko oraz tytuły książęce/hrabiowskie posiadają nieodmienne formy (`D./C./B. == M.`), podczas gdy `episode_profile.name_declensions` dostarcza prawidłowo odmieniony paradygmat[cite: 4, 5].

**Wymagana implementacja (`series_memory.py` — operacje in-memory z poszanowaniem Z16):**
1. **Reconcyliacja płci w pamięci (`_reconcile_registry_gender_in_memory`):**
   - Podczas scalania danych z `episode_profile` (`character_dossiers`, `name_declensions`) oraz istniejących `relations` w `SeriesBible`, jeśli dla danej postaci `episode_profile` wskazuje `FEMALE` (lub `MALE`) ORAZ w `relations` dla tej postaci jako adresata widnieje spójny znacznik `[KOBIETA (Adresat)]` (lub odpowiednio `[MĘŻCZYZNA (Adresat)]`), zaktualizuj w pamięci rekord `character_registry[name]` (`gender` oraz `grammatical_gender`), niezależnie od wcześniejszej flagi `priority: "P0"` i `has_verified_gender: true`[cite: 4, 5].
2. **Rewalidacja kategorii encji w pamięci (`_sanitize_entity_categories_in_memory`):**
   - Jeśli nazwa encji lub jej alias zawiera słowa kluczowe wskazujące na toponim (np. człony geograficzne w języku polskim lub angielskim: `Równiny`, `Królestwo`, `Cesarstwo`, `Imperium`, `Góry`, `Las`, `Plains`, `Kingdom`, `Empire`, `Valley`, `City`) albo pokrywa się z toponimem wykrytym w `setting_and_era` / `episode_summary` (np. nazwa własna występująca bezpośrednio w frazie `Królestwo <Nazwa>` lub `<Nazwa> Kingdom`), ustaw w pamięci `entity_category = "TOPONYM"` i wyklucz ją z listy osobowych uczestników sceny oraz kandydatów na `target_speaker`[cite: 4, 5].
3. **Aktualizacja paradygmatów odmiany w pamięci (`_enrich_declensions_from_profile`):**
   - Jeśli istniejący wpis w `self.declensions[name]` jest zdegenerowany (wszystkie przypadki zależne `D, C, B, N, Ms` są identyczne z mianownikiem `M`), a `episode_profile.name_declensions` dostarcza dla tej samej postaci pełny paradygmat ze zróżnicowanymi końcówkami fleksyjnymi, zastąp w pamięci zdegenerowany paradygmat paradygmatem z `episode_profile`[cite: 4, 5].

---

### ZADANIE 3 (P1-3 / E-03): Stałość rodzaju gramatycznego aktora na przestrzeni sceny i egzekwowanie `male_only_scene` / `female_only_scene` (`scene_discourse.py`)

**Problem z audytu:**
Dla postaci epizodycznych o statusie `gender: "UNKNOWN"` w `series_bible` (`[ID: 218..257]`, `[ID: 268]`) `telemetry_tag` zmienia płeć mówcy i adresata z linii na linię (`MASCULINE` ↔ `FEMININE`) pod wpływem chwilowych wahań F0 w Kroku 4, mimo że scena w `dramatic_sequences` ma ustawioną flagę `male_only_scene: true`[cite: 4, 5].

**Wymagana implementacja (`scene_discourse.py`):**
1. **Ograniczenie z topologii aktu (`dramatic_sequences`):** Jeśli linia przypada w przedziale czasowym `time_range` sekwencji dramatycznej mającej `male_only_scene == True` (i `female_only_scene == False`), każdy aktor o niezweryfikowanej płci (`UNKNOWN` / `None`) w tej sekwencji otrzymuje deterministycznie rodzaj `MALE` (`MASCULINE`)[cite: 4, 5]. Analogicznie dla `female_only_scene == True` (i `male_only_scene == False`) otrzymuje `FEMALE` (`FEMININE`)[cite: 4, 5].
2. **Konsensus płci per aktor w odcinku (`Actor Gender Consensus`):** Dla każdego aktora o statusie `UNKNOWN`, który pojawia się w wielu liniach odcinka poza scenami jednorodnymi płciowo, wyznacz wypadkową płeć przed wygenerowaniem `telemetry_tag` na podstawie mediany F0 ze wszystkich jego kwestii w odcinku (zamiast pojedynczego wycinka obarczonego szumem tła) i zablokuj tę wartość jako stałą we wszystkich turach tego aktora w odcinku[cite: 4, 5].

---

### ZADANIE 4 (P2-1 / INC-AVT-027 / E-05 / E-06 / E-10): Uszczelnienie heurystyk adresata i reprezentacji tur w `scene_discourse.py`

**Problem z audytu:**
1. **Fałszywy `lock=True` dla postaci w 3. osobie (`E-06`):** Wspomnienie postaci `P0` w konstrukcji 3. osoby (`"here on behalf of Duke <Nazwa>"`, `"worthy of Duke <Nazwa>'s attention"`, `"under Prince <Nazwa>'s reign"`) powoduje zablokowanie tej nieobecnej w scenie postaci jako bezpośredniego adresata (`target`, `lock=True`, `conf=0.98`) przez 7 kolejnych tur (`[ID: 274..312]`)[cite: 4, 5].
2. **Adresaci dla napisów ekranowych (`E-05a`):** Tury z `speaker == 'sign'` (`is_sign=True`) dziedziczą osobowych adresatów z sąsiednich linii dialogowych[cite: 4].
3. **Nadpisanie nazwy mówcy `Worker A/B` (`E-05b`):** W `[ID: 244]` dla aktora `Worker A/B` w `telemetry_tag` jako nazwa mówcy pojawia się `[Mówca: POLYLOGUE (MASCULINE)]`[cite: 4, 5].
4. **Surowe wartości w `SpeakerTurn.__repr__` (`E-10`):** Reprezentacja tekstowa `<SpeakerTurn ...>` w logach zawiera `target='None'`, `gender='None'` i `you_group='AMBIGUOUS'`[cite: 4].

**Wymagana implementacja (`scene_discourse.py`):**
1. **Filtr składniowy 3. osoby i obecności w scenie:**
   - Wyklucz nadawanie `target` z `lock=True` na podstawie dopasowania nazwy własnej w tekście angielskim, jeśli przed nazwą (lub przed poprzedzającym ją tytułem `Duke`, `Prince`, `Count`, `Lord`, `Lady`, `Baron`, `Viscount`) stoi przyimek lub konstrukcja 3. osoby: `of`, `on behalf of`, `for`, `from`, `under`, `about`, `with`, `by`, `to <Title> <Name>'s`, lub gdy nazwa posiada dopełniacz saksoński `'s` (`<Name>'s`) albo jest podmiotem zdania w 3. osobie (`<Title> <Name> acknowledges / hopes / is`)[cite: 4, 5].
   - Dodatkowo, jeśli dla bieżącego przedziału czasowego w `dramatic_sequences` zdefiniowano niepustą listę `characters_present`, kandydat na `target_speaker` spoza tej listy (i spoza zbioru aktywnych mówców `raw_actor_name` w danej scenie) nie może otrzymać blokady `lock=True` jako adresat bezpośredni[cite: 4, 5].
2. **Izolacja napisów ekranowych (`is_sign`):** Dla zdarzeń i tur, w których `is_sign == True` lub `speaker.lower() == 'sign'`, ustawiaj bezwarunkowo brak adresata i nie uwzględniaj ich w łańcuchu dziedziczenia rozmówców[cite: 4, 5].
3. **Zachowanie etykiety aktora złożonego:** Dla aktorów zawierających ukośnik lub spójnik grupowy (np. `Worker A/B`), w polu `Mówca:` w `telemetry_tag` zachowaj czystą nazwę aktora (`Worker A/B (MASCULINE)`), rezerwując słowo `POLYLOGUE` wyłącznie dla pola `Scena:`[cite: 4, 5].
4. **Czysta reprezentacja `SpeakerTurn`:** W metodzie formatującej obiekt `SpeakerTurn` zastąp puste/nieokreślone wartości czytelnymi etykietami domenowymi (np. `target='UNSPECIFIED'`, `gender='UNSPECIFIED'`, `you_group='VIRILE'` przy `male_in_scene=True`), eliminując literały `'None'` i `'AMBIGUOUS'` ze zrzutu `turns` w JSONL[cite: 4].

---

### ZADANIE 5 (P3-1 / P3-2 / E-09 / E-11): Normalizacja znaczników `<i>` w parserze Fazy 1 i ochrona zablokowanego glosariusza w `translator.py`

**Problem z audytu:**
1. Model Fazy 1 generuje znaczniki HTML `<i>...</i>` na liniach o stylu `Italics`, co wymaga aż 47 korekt `Redundancja Kursywy` w `EpisodeQualityGate` na końcu potoku[cite: 4, 5].
2. W `[ID: 23]` Faza 2 zmieniła zablokowany w `episode_profile.glossary` termin z formy zdefiniowanej w `Zablokowana Terminologia` na wariant synonimiczny[cite: 4, 5].

**Wymagana implementacja (`translator.py` — bez modyfikacji chronionego `verifier.py`):**
1. Bezpośrednio po odebraniu odpowiedzi Fazy 1 (oraz przed przekazaniem wyniku Fazy 2 do lintera), jeśli styl docelowego zdarzenia ASS należy do rodziny `Italics` (np. `Italics`, `Italics - Top`), usuń ze stringa zewnętrzne znaczniki `<i>...</i>` oraz `{\i1}...{\i0}` już na etapie `translator.py`, a podwójne backslashe w tagach ASS (`\\i1`, `\\N`) znormalizuj do pojedynczych (`\i1`, `\N`)[cite: 4, 5].
2. W `translator.py` po otrzymaniu `refined_pl` z Fazy 2 sprawdź, czy dla linii, w której `en_text` zawiera termin źródłowy z `episode_profile.glossary` (`Zablokowana Terminologia`), a `phase1_pl` zawierała dokładny kanoniczny odpowiednik `translation_pl` (w dowolnej formie fleksyjnej rdzenia), tekst `refined_pl` nie utracił tego terminu na rzecz innego synonimu — w przypadku utraty przywróć termin z glosariusza lub zachowaj bezpieczną wersję z Fazy 1[cite: 4, 5].

---

## 2. TESTY JEDNOSTKOWE I WERYFIKACJA KOŃCOWA

1. Dodaj testy regresyjne dla Zadań 1–5 w odblokowanych plikach testowych w katalogu `tests/` (`tests/test_series_memory.py`, `tests/test_discourse_and_translator.py`, `tests/test_hygiene.py`)[cite: 6]:
   - `test_T11_1_5_sociolinguistic_register_gated_by_character_dossier` (weryfikacja Zadania 1)[cite: 4, 5],
   - `test_T11_1_5_in_memory_gender_reconciliation_and_toponym_filtering` (weryfikacja Zadania 2)[cite: 4, 5],
   - `test_T11_1_5_unknown_actor_scene_gender_stability_and_male_only_constraint` (weryfikacja Zadania 3)[cite: 4, 5],
   - `test_T11_1_5_third_person_title_mention_not_locked_as_addressee_and_sign_isolation` (weryfikacja Zadania 4)[cite: 4, 5],
   - `test_T11_1_5_italics_style_tag_normalization_and_glossary_preservation` (weryfikacja Zadania 5)[cite: 4, 5].
2. Uruchom weryfikację czystości i testy celowane:
   - `python verify_purity.py` → wymagany wynik **12/12 PASS**[cite: 6].
   - `pytest tests/test_series_memory.py tests/test_discourse_and_translator.py tests/test_hygiene.py` → wymagane **100% PASS**[cite: 6].
   - `git diff a6d40bb09d60b2d986d919de98044c6e2d9c838b..HEAD -- test_system.py tests/archive/ avt_linter.py pytest.ini rules.py verifier.py verify_purity.py "series_memory/*_bible.json" series_memory/.onomastic_lexicon.json` → wymagane **0 B**[cite: 6].
3. Wygeneruj raport wdrożenia `Artefakty/Raport_wdrozenia_11.1.5.md`.
