# Plik: C:\Users\Piotrek\Desktop\translator\Artefakty\Raport_wdrozenia_9.9.md

# RAPORT WDROŻENIA PROMPTU NAPRAWCZEGO — WERSJA 9.9

## 1. METADANE PODSTAWOWE
- Wersja promptu naprawczego: 9.9
- Data utworzenia szkieletu: 2026-10-30
- Ścieżka promptu: C:\Users\Piotrek\Desktop\translator\Artefakty\Prompt_9.9.md
- Ścieżka raportu: C:\Users\Piotrek\Desktop\translator\Artefakty\Raport_wdrozenia_9.9.md
- Data wdrożenia: 2026-10-30
- Commit wdrożenia: ec39701 (feat(pipeline): Wdrozenie Standardu 9.9)
- Poprzedni commit (9.8): 783dffd
- Wersja Depuracji Legacy w tle: 1.0 (commit 474fb64)
- Status wdrożenia: WDROŻONE (212/212 fast, 365/365 full, 4 bramki PASS, VICTORY CONFIRMED)

## 2. PHASE 0 — WYNIK WERYFIKACJI KODU
### 2.1. Tabela P0.2 — Mapowanie plan ↔ kod

| Operacja (sekcja 9.9) | Miejsce wywołania / metoda w planie | Rzeczywiste miejsce wywołania w kodzie (plik + linia + metoda) | Rzeczywista sygnatura w kodzie | Zgodność | Uwagi / Rozstrzygnięcie |
|---|---|---|---|---|---|
| 2B.1 | Legalizacja i pokrycie testem jednostkowym `T9.1` obsługi `--subs` i `not sys.stdin.isatty()` w `main.py` oraz delegacji CLI w `translator.py` | `main.py:245-275` (`resolve_cli_inputs_and_honorifics`), `main.py:382-384, 414` (wywołanie w `main()`), `translator.py:6174-6176` (`__main__`) | `resolve_cli_inputs_and_honorifics(args: argparse.Namespace, is_tty: bool, env_keep_honorifics: str = "false") -> Tuple[List[str], Optional[bool]]` | 100% ZGODNY | Wydzielono czystą funkcję pomocniczą `resolve_cli_inputs_and_honorifics` w `main.py`, wywoływaną bezpośrednio w `main()`. Funkcja parsuje `args.input` lub przejmuje `args.subs`, a tryb honoryfikatorów rozwiązuje deterministycznie bez blokowania I/O przy `not is_tty`. Pokryto testem `T9.1` (`@pytest.mark.unit`, 2 przypadki). |
| 2C.1 | Symetria `MALE`/`FEMALE` dla jawnego aktora w `_precompute_episode_scene_genders` oraz separacja płci mówcy (`has_male_speaker_in_line`) od płci adresata przy wyznaczaniu `Grupa_1os_lm` (`translator.py`) | `translator.py:1955-1957, 2033-2035` (`_precompute_episode_scene_genders`), `translator.py:3266-3286` (`_prepare_batch_prompt`), `translator.py:4106-4126` (`_process_single_batch`) | `_precompute_episode_scene_genders(self, events: List[pysubs2.SSAEvent]) -> Dict[int, str]`, `_prepare_batch_prompt(self, batch_events: List[Tuple[int, pysubs2.SSAEvent, str, str]], ...) -> str`, `_process_single_batch(self, batch_events: List[Tuple[int, pysubs2.SSAEvent, str, str]], ...) -> None` | 100% ZGODNY | Wprowadzono pełną symetrię `FEMALE` w `_precompute_episode_scene_genders`: postać żeńska P0/P1 nadaje `scene_genders[orig_idx] = "kobieta"`. W `_prepare_batch_prompt` i `_process_single_batch` rozdzielono `has_male_speaker_in_line` od `has_male_addressee_in_line`. `Grupa_1os_lm` (`We_Group`) zależy wyłącznie od płci mówcy w scenie, zachowując `NON_VIRILE` dla mówczyni żeńskiej w scenie kobiecej nawet przy pojedynczym adresacie męskim (`tgt_gram_tag == "MASCULINE"`). |
| 2C.2 | Aktualizacja licznika suite'ów w `test_system.py` i spójność puli testów `fast` / `full` | `test_system.py:19506-19548` (`test_standard_9_8_suite`), `test_system.py:19777-19779` (`__main__`) | `test_standard_9_8_suite(target_tag: str, override_g: str, expected_aud_g: str, expected_telem_g: str)` | 100% ZGODNY | Dodano dekorator `@pytest.mark.parametrize` do `test_standard_9_8_suite` z 2 przypadkami, eliminując naruszenie D4. W bloku `__main__` dodano wywołanie obu wariantów i zaktualizowano licznik z `(221/221)` na `(222/222)`. Dodano test `T9.2` w `tests/test_discourse_and_translator.py`. |

### 2.2. Tabela P0.3 — Mapowanie danych testowych

| Placeholder | Wartość rzeczywista (spoza odcinka audytowanego) | Źródło (P0 / EN / ASS) | Uwagi |
|---|---|---|---|
| `<RZECZYWISTA_ETYKIETA_MĘSKA_P1_1>` | `Boy` | `[Events]` | Jednoznaczna leksykalnie etykieta męska |
| `<RZECZYWISTA_ETYKIETA_ŻEŃSKA_P1_1>` | `Girl` | `[Events]` | Jednoznaczna leksykalnie etykieta żeńska |
| `<RZECZYWISTY_ANTROPONIM_MĘSKI_1>` | `Tokiyuki` | P0 (`SeriesBible`) | Mówca męski P0 |
| `<RZECZYWISTY_ANTROPONIM_ŻEŃSKI_1>` | `Ayako` | P0 (`SeriesBible`) | Mówczyni żeńska P0 |
| `<WARTOŚĆ_ENUM_TECHNICZNA_1>` | `VIRILE` | KOD | Wartość rodzaju męskoosobowego (`VIRILE`) |
| `<WARTOŚĆ_ENUM_TECHNICZNA_2>` | `NON_VIRILE` | KOD | Wartość rodzaju niemęskoosobowego (`NON_VIRILE`) |

## 3. STAN BAZOWY (PRZED MODYFIKACJAMI 9.9)
- Tryb fast (`pytest`): 207 PASSED, 153 deselected, 0 FAILED, 0 ERROR (15.65 s)
- Tryb full (`pytest -m ""`): 360 PASSED, 0 FAILED, 0 ERROR (~15.5 min)

## 4. NOWE TESTY (`T9.1`, `T9.2`)

| ID testu | Punkt Sekcji 2 | Plik testowy | Nazwa testu | Kategoria markera | Kryterium akceptacji |
|---|---|---|---|---|---|
| **T9.1** | `2B.1` | `tests/test_discourse_and_translator.py` | `test_non_tty_cli_resolves_subs_argument_and_honorifics_env_without_stdin_prompt` | `unit` | Rezolucja `--subs` do `raw_inputs` i `KEEP_HONORIFICS` przy `is_tty=False` bez blokującego wejścia stdin |
| **T9.2** | `2C.1` | `tests/test_discourse_and_translator.py` | `test_we_group_virility_depends_on_speaker_gender_and_preserves_female_we_group_with_male_target` | `unit` | Separacja `We_Group` (`Grupa_1os_lm`) od płci pojedynczego adresata, zachowanie `NON_VIRILE` dla mówczyni w scenie kobiecej z męskim adresatem |

## 5. STAN KOŃCOWY (PO MODYFIKACJACH 9.9)
- Tryb fast (`pytest`): 212 PASSED, 153 deselected w 17.06 s, 0 FAILED, 0 ERROR
- Tryb full (`pytest -m ""`): 365 PASSED, 0 FAILED, 0 ERROR (~15.5 min)
- Bramki CI/CD:
  * `verify_purity.py`: 11/11 PASS (100% CZYSTY I ZGODNY ZE STANDARDEM 9.0)
  * `verify_ultimate_pipeline.py`: 15/15 PASS
  * `verify_12_fixes.py`: 12/12 PASS
  * `audit_diff.ps1`: WERDYKT: [VICTORY CONFIRMED -- KOD CZYSTY I UOGOLNIONY]

## 6. MECHANIZMY DEGRADACJI — D1–D6 (WERYFIKACJA RZECZYWISTA)

| Test | D1 (Placeholder) | D2 (Tautologia) | D3 (Snapshot) | D4 (Parametryzacja) | D5 (Instancja) | D6 (Legacy/Depuracja) | Status |
|---|---|---|---|---|---|---|---|
| `T9.1` (`test_non_tty_cli_resolves_subs_argument_and_honorifics_env_without_stdin_prompt`) | Czysty (brak placeholderów) | Czysty (rzeczywiste wywołanie `resolve_cli_inputs_and_honorifics`) | Czysty (asercje semantyczne na bool/list) | Czysty (`@pytest.mark.parametrize` na 2 wariantach) | Czysty (syntetyczne nazwy plików) | Czysty (zgodny z Depuracją 1.0) | ZAAKCEPTOWANY |
| `T9.2` (`test_we_group_virility_depends_on_speaker_gender_and_preserves_female_we_group_with_male_target`) | Czysty (wypełniony z P0.3) | Czysty (weryfikacja reguły podziału grup) | Czysty (asercje wartości kategorii) | Czysty (`@pytest.mark.parametrize` na 2 wariantach) | Czysty (brak instancji z odcinka audytowanego) | Czysty (zgodny z Depuracją 1.0) | ZAAKCEPTOWANY |
| `test_standard_9_8_suite` (TEST 222) | Czysty (brak placeholderów) | Czysty (integracja Warstw 2 i 3) | Czysty (brak snapshotów) | Czysty (`@pytest.mark.parametrize` na 2 wariantach Boy/Girl) | Czysty (postacie kanoniczne P0/P1) | Czysty (zgodny z Depuracją 1.0) | ZAAKCEPTOWANY |

## 7. SELF-CHECK RAPORTU
- [x] Wszystkie pola `<DO_WYPEŁNIENIA_*>` wypełnione (0 wystąpień w pliku)
- [x] Brak literalnych danych z audytowanego odcinka w kodzie, testach i sekcjach architektonicznych
- [x] 4 bramki CI/CD zwracają 100% PASS
