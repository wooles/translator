# 📋 RAPORT WDROŻENIA — HOTFIX 11.1.5: USZCZELNIENIE TELEMETRII DYSKURSU, WALIDACJI REJESTRU I IN-MEMORY SANITACJI SERIESBIBLE

---

## Sekcja 0 — Metadane Certyfikacji i Wdrożenia

| Parametr | Wartość |
| :--- | :--- |
| **Data wdrożenia** | `2026-11-11` |
| **Repozytorium referencyjne** | `https://github.com/wooles/translator` (gałąź `main`) |
| **Punkt wyjścia (`HEAD` bazowy)** | `dd950ba13e10e77d9888b30e8795922ef5299347` (`dd950ba` — Standard 11.1.4b) |
| **Commit 1 (`fix:`)** | `13afb4226d9c6ca1605ecf9116e107df4923f669` (`13afb42`) |
| **Commit 2 (`test:` — Certyfikacja Kodu)** | `3c70a557b77ce2b83bf9bcf5875bf6fe57f70db7` (`3c70a55`) |
| **Commit 3 (`docs:`)** | `HEAD` (aktualizacja SSOT w `AGENTS.md`, `PROJECT_MEMORY.md` oraz niniejszy raport) |
| **Certyfikowany standard produkcyjny** | **`Standard 11.1.5 (Discourse Telemetry & Sociolinguistic Gate Certified Baseline)`** |
| **Baseline ochrony Z16 (Depuracja Legacy 1.0)** | `a6d40bb09d60b2d986d919de98044c6e2d9c838b` (`a6d40bb` — **0 B diff na wszystkich plikach chronionych**) |
| **Podstawa wdrożenia** | `Artefakty/Raport_audytu_operacyjnego_2026-11-11.md` (Incydenty `INC-AVT-026`, `INC-AVT-027` oraz zdarzenia `E-01`..`E-11` z przebiegu `20261111_211338`) |
| **Koszt operacji** | **0.00 PLN** (100% lokalny determinizm logiczny, DSP i ASR) |

---

## Sekcja 1 — Podsumowanie Celów i Wyeliminowanych Wad Źródłowych

Hotfix 11.1.5 wyeliminował u przyczyn źródłowych siedem klas problemów zdiagnozowanych podczas operacyjnego audytu odcinka:

1. **P1-1 (INC-AVT-026 / E-04):** Sprzeczne z profilem mówcy dynamiczne etykiety `Rejestr:` generowane przez Whisper ASR i szum fonetyczny (np. rejestr dziewczęcy dla mężczyzn/seniorów, szorstki żołnierski dla arystokratów, feudalny poddańczy dla keigo biurowego).
2. **P1-2 (E-01 / E-02 / E-07):** Konflikt płci w zastałej bazie serii (postać kobieca zapisana jako `MALE`), toponimy omyłkowo figurujące w bazie jako `ANTHROPONYM` oraz zdegenerowane paradygmaty odmiany (`D=C=B=N=Ms=M`).
3. **P1-3 (E-03):** Fluktuacje płci aktora epizodycznego `UNKNOWN` z linii na linię mimo flagi `male_only_scene` w topologii aktu.
4. **P2-1 (INC-AVT-027 / E-06):** Fałszywa blokada `lock=True` postaci jako bezpośredniego adresata po wzmiankach w 3. osobie (`on behalf of Duke Alexis`, `under Prince Alexis's rule`, `Duke Alexis acknowledges`).
5. **P2-2 (E-05a / E-05b / E-10):** Skażenie dyskursu przez napisy ekranowe (`is_sign`), nadpisywanie nazwy aktora złożonego `Worker A/B` oraz surowe wartości `'None'` i `'AMBIGUOUS'` w `SpeakerTurn.__repr__`.
6. **P3-1 (E-09):** Generowanie tagów HTML `<i>...</i>` i nadmiarowych kodów ASS `{\i1}...{\i0}` na stylach z rodziny `Italics`.
7. **P3-2 (E-11):** Dryf synonimiczny Fazy 2 zastępujący zablokowaną terminologię z `episode_profile.glossary` wariantami alternatywnymi.

---

## Sekcja 2 — Szczegółowy Zakres Zaimplementowanych Zmian

### 1. Zadanie 1 (P1-1 / INC-AVT-026 / E-04): Bramkowanie tagów `Rejestr:` przez profil postaci
- **Moduły:** `whisper_disambiguator.py`, `scene_discourse.py`, `translator.py`.
- **Implementacja:**
  - Wdrożono metodę klasową `WhisperDisambiguator.validate_pragmatic_register_against_speaker` weryfikującą zgodność wykrytych etykiet pragmatycznych z `character_dossiers`, `character_registry` oraz cechami mówcy.
  - Etykieta `Rejestr dziewczęcy` jest akceptowana wyłącznie dla zweryfikowanych kobiet (`FEMALE`) w klasie wieku `CHILD`, `TEEN` lub młodych `ADULT`. Dla mówców o płci `MALE` lub klasie `ELDERLY` zaimek `watashi` w audio JP jest traktowany jako naturalny sygnał formalny i nie wyzwala rejestru dziewczęcego.
  - Etykieta `Szorstki żołnierski / Bojowy` jest pomijana dla postaci o profilu dworskim, arystokratycznym lub formalno-urzędowym, chyba że linia posiada w `prosody_tags` znacznik `krzyk bojowy / silne wzburzenie emocjonalne`.
  - Etykieta `Feudalny poddańczy / Wasal` dla standardowych formuł grzecznościowych (`ohayou gozaimasu`, `moushiwake arimasen`, `shitsurei shimasu`) wymaga obecności archaizmów feudalnych (`-dono`, `koushaku`, `danshaku`, `sessha`) w settingu historycznym/fantasy; dla standardowego keigo biurowego pozostaje neutralna.
  - Etykiety dialektu południowego/zachodniego są tłumione dla standardowej polszczyzny literackiej, o ile postać nie posiada dedykowanego idiolektu.

### 2. Zadanie 2 (P1-2 / E-01 / E-02 / E-07): In-Memory Sanitacja `SeriesBible`
- **Moduł:** `series_memory.py` (0 B diff na dysku — pełna ochrona Z16).
- **Implementacja:**
  - `_reconcile_registry_gender_in_memory`: Podczas ładowania bazy i scalania z `episode_profile`, jeśli `episode_profile` i relacje serii wskazują `FEMALE` (lub `MALE`), rekord w pamięci `character_registry` zostaje zaktualizowany niezależnie od wcześniejszej flagi `has_verified_gender` i `P0`.
  - `_sanitize_entity_categories_in_memory`: Encje zawierające słowa kluczowe toponimów (np. `Równiny`, `Królestwo`, `Cesarstwo`, `Góry`, `Las`, `Plains`, `Kingdom`, `Empire`, `City`) lub pokrywające się z toponimami settingu są oznaczane jako `TOPONYM` i wykluczane ze zbioru uczestników sceny oraz kandydatów na adresata.
  - `_enrich_declensions_from_profile`: Zdegenerowane wpisy w `self.declensions` (`D=C=B=N=Ms=M`) są zastępowane w pamięci pełnymi paradygmatami z `episode_profile.name_declensions`.

### 3. Zadanie 3 (P1-3 / E-03): Stałość rodzaju aktora i egzekwowanie `male_only_scene`
- **Moduł:** `scene_discourse.py`.
- **Implementacja:**
  - Wdrożono `SceneDiscourseGraph.compute_actor_gender_consensus`: dla aktorów epizodycznych o statusie `UNKNOWN` wyznaczana jest jednolita płeć na podstawie mediany F0 ze wszystkich ich kwestii w odcinku.
  - W `arbitrate_event_telemetry`: jeśli zdarzenie przypada w przedziale czasowym sekwencji dramatycznej mającej `male_only_scene == True`, każdy aktor `UNKNOWN` otrzymuje rodzaj `MALE` (`MASCULINE`). Analogicznie dla `female_only_scene == True` otrzymuje `FEMALE` (`FEMININE`).

### 4. Zadanie 4 (P2-1 / INC-AVT-027 / E-05 / E-06 / E-10): Filtr składniowy 3. osoby i higiena dyskursu
- **Moduł:** `scene_discourse.py`.
- **Implementacja:**
  - Wdrożono `_is_third_person_syntactic_context`: wyklucza nadawanie `target` z `lock=True` po konstrukcjach referencyjnych 3. osoby (`on behalf of`, `under`, `worthy of`, `of`, `to`, dopełniacz saksoński `'s`, orzeczenia w 3. os. `acknowledges`, `hopes`, `is`, `was`).
  - Weryfikacja obecności w scenie: kandydaci spoza `characters_present` z `dramatic_sequences` (i spoza aktywnych mówców) nie mogą otrzymać blokady `lock=True`.
  - Izolacja napisów ekranowych: tury i zdarzenia `is_sign == True` lub `speaker == 'sign'` mają bezwarunkowo czyszczonego adresata i nie dziedziczą partnerów dyskursu.
  - Etykieta aktora złożonego: dla aktorów typu `Worker A/B` w polu `Mówca:` zachowywana jest pełna nazwa, a znacznik `POLYLOGUE` przypisywany jest wyłącznie do pola `Scena:`.
  - Czysty `SpeakerTurn.__repr__`: literały `'None'` i `'AMBIGUOUS'` zostały zastąpione czytelnymi etykietami domenowymi `UNSPECIFIED` / `VIRILE`.

### 5. Zadanie 5 (P3-1 / P3-2 / E-09 / E-11): Normalizacja kursywy i ochrona glosariusza
- **Moduł:** `translator.py`.
- **Implementacja:**
  - W `format_phase1_candidate_text` oraz w pętli pre-lintera: dla zdarzeń o stylu z rodziny `Italics` znaczniki HTML `<i>...</i>` oraz nadmiarowe tagi ASS `{\i1}...{\i0}` są usuwane na wczesnym etapie, a podwójne backslashe (`\\N`, `\\i1`) normalizowane do pojedynczych.
  - Po odebraniu wyniku z Fazy 2: wprowadzono weryfikację zachowania terminów z `episode_profile.glossary` (`Zablokowana Terminologia`). Jeśli Faza 2 zastąpiła kanoniczny termin synonimem, automatycznie przywracany jest kanon z Fazy 1.

---

## Sekcja 3 — Wyniki Testów Regresyjnych i Bramek Jakości

### 1. Testy Jednostkowe Hotfixu 11.1.5 (100% PASS)
- `tests/test_discourse_and_translator.py::test_T11_1_5_sociolinguistic_register_gated_by_character_dossier` — **PASSED** (0.01 s)
- `tests/test_discourse_and_translator.py::test_T11_1_5_unknown_actor_scene_gender_stability_and_male_only_constraint` — **PASSED** (0.01 s)
- `tests/test_discourse_and_translator.py::test_T11_1_5_third_person_title_mention_not_locked_as_addressee_and_sign_isolation` — **PASSED** (0.01 s)
- `tests/test_series_memory.py::test_T11_1_5_in_memory_gender_reconciliation_and_toponym_filtering` — **PASSED** (0.02 s)
- `tests/test_hygiene.py::test_T11_1_5_italics_style_tag_normalization_and_glossary_preservation` — **PASSED** (0.01 s)

Łączny czas wykonania 5 testów: **1.35 s**.

### 2. Wyniki 4 Bramek Kwalifikacyjnych Potoku
1. **`python verify_purity.py`:** **12/12 PASS**
   - AST, brak instancji onomastycznych, brak cytowanych zdań w regułach, brak alarmów w promptach, brak zakazanych slugów, domyślny `strict_positive_domain=True`.
2. **`python verify_8_fixes.py`:** **8/8 PASS**
   - Brak cyklicznego virility, brak narzucania angielskiej składni, deklaratywny profiler, brak zanieczyszczania bazy P0.
3. **`python verify_12_fixes.py`:** **12/12 PASS**
   - Rozdzielenie We/You, twarde progi confidence >= 0.95, separacja P0/P1, determinizm F0 <= 135 Hz.
4. **`python verify_ultimate_pipeline.py`:** **15/15 PASS**
   - Immunitet narzędnika, granice słów przy tagach ASS, czas przyszły złożony, bariera CopulaAdj, izolacja vocative lock.

### 3. Audyt Śledczy Diffu (`audit_diff.ps1`)
- **Bramka 1/4 (Zero-Cosmetic Gate):** `PASS` (modyfikacja rdzenia silnika: `scene_discourse.py`, `series_memory.py`, `translator.py`, `whisper_disambiguator.py`)
- **Bramka 2/4 (Zero-Onomastic Gate):** `PASS` (brak nazw własnych ze zgłoszeń w kodzie)
- **Bramka 3/4 (End-to-End Wiring Gate):** `PASS` (brak martwego kodu, pełna integracja `compute_actor_gender_consensus` w potoku)
- **Bramka 4/4 (Test Integrity Gate):** `PASS` (brak mockowania logiki domenowej)
- **Werdykt końcowy audytora:** **`[VICTORY CONFIRMED -- KOD CZYSTY I UOGOLNIONY]`**

### 4. Weryfikacja Nienaruszalności Baseline'u Z16
Polecenie:
```powershell
git diff a6d40bb09d60b2d986d919de98044c6e2d9c838b..HEAD -- test_system.py tests/archive/ avt_linter.py pytest.ini rules.py verifier.py verify_purity.py "series_memory/*_bible.json" series_memory/.onomastic_lexicon.json
```
Zwróciło dokładnie **0 B** diffu na wszystkich chronionych plikach. Wszelkie korekty baz wiedzy zrealizowano w 100% in-memory w pamięci operacyjnej RAM.

---

## Sekcja 4 — Zgodność z Pryncypiami Architektonicznymi

1. **Z1 Zero-Literal:** Pełna onomastyczna czystość kodu produkcyjnego i testów (użyto wyłącznie syntetycznych identyfikatorów `Speaker_Alpha`, `Speaker_Beta`, `Speaker_Gamma`, `Target_Hero`, `Protagonist_Girl`, `Leader_Alpha`).
2. **Z2 Pure Positive Domain:** Wszystkie nowe docstringi, komentarze i asercje sformułowano w domenie pozytywnej docelowego stanu pożądanego (brak słów preskryptywnych, 12/12 w `verify_purity.py`).
3. **Z3 Primary LLM Authority:** Warstwy post-processingu i lintera działają pasywnie; wyeliminowano fałszywe ingerencje w styl i fleksję modelu.
4. **Z4 Instance-Free:** Wszystkie reguły opierają się na topologii, składni i relacjach, a nie konkretnych tytułach czy nazwach własnych.
5. **Z16 Depuracja Legacy 1.0:** 0 B diffu na dysku dla plików objętych ochroną.

---

## Sekcja 5 — Certyfikat Gotowości Produkcyjnej

Potok w rewizji commitu kodu `3c70a557b77ce2b83bf9bcf5875bf6fe57f70db7` spełnia 100% rygorów architektonicznych i jakościowych, uzyskując status **`Standard 11.1.5 (Discourse Telemetry & Sociolinguistic Gate Certified Baseline)`**.
