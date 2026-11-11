# 📋 RAPORT WDROŻENIA — HOTFIX 11.1.4: OBSŁUGA CODE-SWITCHINGU (JA/EN), MOST IDIOLEKTÓW YAKUWARIGO I SEPARACJA SŁOWNA ASR

- **Data sporządzenia:** 2026-11-11
- **Autor:** Główny Inżynier Systemowy AVT (Antigravity System Architect)
- **Repozytorium:** `https://github.com/wooles/translator` (gałąź `main`)
- **Punkt startowy (`HEAD` pre-11.1.4):** `7011407cc7b47d2ffb223f402dc8366d40041b7e` (`7011407`)
- **Poprzedni baseline Z16 (Depuracja Legacy 1.0):** `d31096945a977d6a179891d87dcfd2a05c0c5bca` (`d310969`)
- **Nowy baseline Z16 (po `Z16-amendment #10`):** `a6d40bb09d60b2d986d919de98044c6e2d9c838b` (`a6d40bb` — Commit 1)
- **Nowy Commit Certyfikacji Kodu:** `38ad629ae1ec343d3dfeb9d4e57691339dc2ffb5` (`38ad629` — Commit 2)
- **Certyfikowany standard po wdrożeniu:** `Standard 11.1.4 (Sociolinguistic & Code-Switching Certified Baseline)`
- **Werdykt integracyjny:** **`VICTORY CONFIRMED` (100% PASS, 0 B diffu na chronionych bazach SeriesBible, brak wycieków nazw własnych)**

---

## 🎯 1. CEL OPERACYJNY I DIAGNOZA PUNKTÓW P1-1 .. P1-6

Audyt operacyjny (`Artefakty/Raport_audytu_operacyjnego_2026-11-11.md`) wykazał pełną stabilność morfosyntaktyczną Standardu 11.1.3a, identyfikując jednocześnie sześć precyzyjnych luk socjolingwistycznych i integracyjnych:

1. **P1-1 (Fałszywa detekcja dialektu na pospolitych czasownikach japońskich):**
   Obecność niezakotwiczonych znaków `"べ"` oraz `"おら"` w `jp_dialect_tokens` w `whisper_disambiguator.py` powodowała fałszywą kwalifikację każdego japońskiego zdania zawierającego popularne czasowniki (`述べた`, `比べれば`, `全て`, `直らない`) jako dialekt regionalny (`DIALECT_JP`), wyzwalając nadmierną stylizację potoczną w `rules.py:DYN_1`.
2. **P1-2 (Brak mostu idiolektów Yakuwarigo w Profilerze i SeriesBible):**
   Pole `CharacterDossier.speech_style_pl` oraz `idiolect_matrix` wygenerowane przez profiler nie były przekazywane do zwięzłego briefu `format_lean_episode_brief`, przez co model Fazy 1 nie otrzymywał zdefiniowanego stylu wypowiedzi postaci. Dodatkowo `SeriesBible` nie utrwalała pola `speech_register` przy rejestracji postaci.
3. **P1-3 (Niedostateczna rozdzielczość czasowa i sklejenia transkrypcji Whisper ASR):**
   Domyślna transkrypcja segmentowa Whisper ASR bez znaczników słownych (`word_timestamps=False`) oraz niski próg nakładania (>80 ms) powodowały przypisywanie całej wypowiedzi do pierwszego krótkiego napisu ASS i powtarzanie tekstu na kolejnej kwestii.
4. **P1-4 (Brak wsparcia dla Code-Switchingu JA/EN i zapożyczeń katakanowych):**
   Hybrydowe wtrącenia pojedynczych słów angielskich lub zwrotów katakanowych w japońskim audio seiyū nie posiadały dedykowanej kategorii dyskursywnej ani wytycznej stylistycznej w regułach Filaru XIII.
5. **P1-5 (Degeneracja wysokiego rejestru do żargonu gamingowego):**
   Kwestie postaci posługujących się dystyngowanym rejestrem arystokratycznym lub *ojou-sama* były w Fazie 2 narażone na trywializację słownictwa losowości i przedmiotów do kolokwializmów gamingowych.
6. **P1-6 (Normalizacja wielkich liter dla identyfikatorów z prefiksem `@` oraz pisownia frazeologizmu):**
   Etykiety postaci z prefiksem technicznym `@` gubiły pierwszą literę w normalizatorze wielkich liter, a zwrot `kopę lat` nie posiadał reguły ochronnej przed usterką ortograficzną.

---

## 🛠️ 2. ZREALIZOWANE ZADANIA INŻYNIERSKIE (CHIRURGICZNE MODYFIKACJE KODU)

### Zadanie 1: Uszczelnienie detektora dialektów i kategoria `CODE_SWITCH_EN`
- Plik: `whisper_disambiguator.py`
- Usunięto niezakotwiczone pojedyncze znaki `"べ"` i `"おら"` z tablicy `jp_dialect_tokens`.
- Zaimplementowano zakotwiczony kompilowany wzorzec `jp_anchored_dialect_re` dopasowujący regionalne formy fleksyjne (`いくべ`, `行べ`, `行くべ`, `おらは`, `てるあるよ`, `何やるか`) wyłącznie przy granicach morfemów i interpunkcji.
- Rozszerzono `jp_dialect_tokens` o kompletne wykładniki socjolektów i *Yakuwarigo* (`ですわ`, `ますわ`, `ですこと`, `ありませんこと`, `ますのよ`, `ないっす`, `っすけど`, `っすね`, `っすよ`, `ったなの`, `だなの`, `くれたまえ`).
- Dodano kategorię 10: `CODE_SWITCH_EN` wykrywającą hybrydowe konstrukcje katakanowe z wykluczeniem powszechnych terminów systemowych (`クリア`, `装備`, `ガード`, `チェック`, `スタート`, `セーブ`, `ロード`, `スキップ`).

### Zadanie 2: Rozszerzenie Filaru XIII o Code-Switching i normy leksykalne
- Plik: `rules.py` (w ramach autoryzowanego `Z16-amendment #10`)
- W regule dynamicznej `DYN_1` uwzględniono znacznik `has_code_switch = "CODE_SWITCH_EN" in jp_categories`.
- Wprowadzono pozytywną wytyczną architektoniczną nakazującą zachowanie ładunku komicznego i charakterologicznego przy celowych wtrąceniach angielskich w audio seiyū.
- W `FILAR CLXIV` dodano kanoniczną formę `'kope lat' -> 'kopę lat'`.
- W `FILAR CLXIX` sformułowano zasadę ochrony zdrobnień rówieśniczych z przyrostkiem `-cchi`.

### Zadanie 3: Most idiolektów w Profilerze
- Plik: `profiler.py`
- Wyrównano wzorzec `RE_JP_DIALECT_MARKERS` z zakotwiczonymi formami kanji/hiragana.
- W funkcji `format_lean_episode_brief` zaimplementowano emisję bloku `Styl i idiolekt: {combined_style}` łączącego `speech_style_pl` oraz `idiolect_matrix`, zachowując informację o gwarze.

### Zadanie 4: Persystencja `speech_register` i samoleczenie relacji w `SeriesBible`
- Plik: `series_memory.py`
- Metody `register_character` oraz `sync_verified_profile_entity` przyjmują i utrwalają pole `speech_register`.
- W `sync_verified_profile_entity` zaimplementowano automatyczne czyszczenie notki relacyjnej (`wyodrębniono z relacji serii`) przy nadejściu zweryfikowanej tożsamości P0 (`MALE` lub `FEMALE`).
- W `format_scoped_for_batch` wprowadzono emisję tagu `[Rejestr: {speech_register}]` przy opisie postaci obecnych w scenie.

### Zadanie 5: Word-Level ASR Whisper i deduplikacja prefiksów
- Pliki: `whisper_engine.py`, `translator.py`
- W `whisper_engine.py:transcribe_batch_scene` włączono `word_timestamps=True`. Przy dostępności słów segmentu przypisywanie do zdarzeń ASS odbywa się na poziomie środków czasowych słów `[start, end]` (tolerancja ±120 ms lub nakładanie >= 50%). Przy braku słów zastosowano zaostrzony próg nakładania segmentu (>= 25% czasu zdarzenia lub >= 35% czasu segmentu).
- W `translator.py:_process_single_batch` zaimplementowano detekcję i odcinanie powtórzonego prefiksu ASR z poprzedniej linii (`len >= 4`), eliminując zjawisko sklejania wypowiedzi.

### Zadanie 6: Rozszerzenie detektora rejestrów pragmatycznych, telemetrii i weryfikatora
- Pliki: `translator.py`, `verifier.py`, `avt_linter.py`
- W `detect_japanese_pragmatic_register` dodano wykładniki Ojou-sama (`ますわ`, `ですこと`, `ありませんこと`, `ますのよ`), rejestru dziewczęcego (`-nano`) oraz nowe pozycje: 15 (stylizowany rejestr wojowniczki `-aru/-yaru`) i 16 (code-switching JA+EN).
- W `translator.py` zaktualizowano `line_dry_telemetry` o rejestr pragmatyczny `[... | Rejestr: ...]`.
- W `translator.py:detect_event_visual_type` zabezpieczono krótkie zawołania dialogowe w stylach mowy przed fałszywym flagowaniem jako szyld (ALL CAPS sign).
- W normalizatorze wielkich liter encji dopuszczono nazwy zaczynające się od prefiksu `@`.
- W promptcie weryfikatora (`verifier.py`) dodano wytyczną ochrony wysokiego rejestru ojou-sama/arystokratycznego przed terminologią gamingową.
- W `avt_linter.py` zarejestrowano deterministyczne reguły zamiany `Kope lat` -> `Kopę lat` oraz `kope lat` -> `kopę lat`.

---

## 📊 3. METRYKI TESTÓW I WYNIKI BRAMEK KWALIFIKACYJNYCH

### A. Nowe testy regresyjne (5/5 PASSED w Commicie 2):
1. `tests/test_discourse_and_translator.py::test_whisper_disambiguator_no_false_positive_dialect_on_common_verbs` — **PASSED** (brak fałszywego DIALECT_JP dla czasowników pospolitych z べ i おら)
2. `tests/test_discourse_and_translator.py::test_whisper_disambiguator_detects_yakuwarigo_aru_yaru_desuwa_ssu_nano` — **PASSED** (poprawna detekcja Yakuwarigo -aru/-yaru, -desu wa, -ssu, -nano)
3. `tests/test_translator.py::test_code_switching_detection_and_prompt_guidance` — **PASSED** (detekcja code-switchingu katakanowego i emisja wytycznej DYN_1)
4. `tests/test_profiler.py::test_format_lean_episode_brief_includes_character_speech_style_and_idiolect` — **PASSED** (formatowanie stylu i idiolektu postaci w zwięzłym briefie)
5. `tests/test_series_memory.py::test_series_bible_character_record_persists_speech_register` — **PASSED** (persystencja speech_register w SeriesBible, emisja w kontekście i nadpisanie relacji)

### B. Wyniki całego pakietu `tests/`:
```
collected 337 items
337 passed in 29.52s (100% PASSED)
```

### C. Wyniki 4 bramek kwalifikacyjnych:
- `verify_purity.py`: **12/12 PASS** (pełna zgodność z regułami Z1, Z2, Z3, Z4)
- `verify_8_fixes.py`: **8/8 PASS**
- `verify_12_fixes.py`: **12/12 PASS**
- `verify_ultimate_pipeline.py`: **15/15 PASS**
- `audit_diff.ps1`: **PASS / VICTORY CONFIRMED**

---

## 🔒 4. STATUS OCHRONY Z16 I DIFF PLIKÓW CHRONIONYCH

- Zgodnie z autoryzacją Operatora (`Z16-amendment #10`), chirurgiczne zmiany w `rules.py`, `verifier.py` oraz `avt_linter.py` zostały zrealizowane wyłącznie w Commicie 1 (`fix:`).
- Nowy baseline ochrony Z16 został ustalony na hash Commita 1: `a6d40bb09d60b2d986d919de98044c6e2d9c838b` (`a6d40bb`).
- Diff na plikach chronionych Z16 (`test_system.py`, `rules.py`, `verifier.py`, `avt_linter.py`, `verify_purity.py`, `pytest.ini`, `series_memory/*_bible.json`, `series_memory/.onomastic_lexicon.json`) względem nowego baseline'u wynosi dokładnie **0 B**.

---

## 🏁 5. PODSUMOWANIE I REKOMENDACJA WDROŻENIOWA

Wdrożenie **Hotfixu 11.1.4** zlikwidowało wszystkie zdiagnozowane anomalie socjolingwistyczne z przebiegu testowego, zapewniając pełną wierność idiolektu postaci seiyū, właściwą dynamikę dialogów dwujęzycznych oraz precyzyjne dopasowanie czasowe transkrypcji ASR. Repozytorium jest w pełni certyfikowane i gotowe do wdrożenia produkcyjnego.
