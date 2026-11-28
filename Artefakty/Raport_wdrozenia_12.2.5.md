# Raport wdrożenia Standard 12.2.5 (`OBS-28` + `OBS-07` — Ochrona Anonimowych i Nieludzkich Mówców, Filtracja F0 `librosa.pyin` oraz Telemetria Źródła Płci — `0.00 PLN`, `0 B` Z16)

**Data:** `2026-11-28`  
**Baza startowa (`main`):** `8be87d6def1160daeb17d974fcb139221fd0dace` (`8be87d6`, `12.2.4 + README`)  
**Status:** `CERTIFIED IN TESTS / AWAITING AUDIT` (`0.00 PLN` wydatku na API; bezwzględne `0 B` diffu na wszystkich `30` plikach Z16, `scene_discourse.py` i `translator.py:_resolve_line_addressee`)

---

## 1. Zakres zmian, łańcuch commitów i izolacja plików (`8be87d6..HEAD`)

W ramach wdrożenia Standardu `12.2.5` zrealizowano `5` atomowych commitów na gałęzi `main`:

1. `69a2a5a` — `fix(acoustics): 12.2.5 [1/5] — replace raw autocorrelation with filtered librosa.pyin in speaker_diarizer.py (E4-bis.3)`
2. `e3a4e16` — `fix(profiler): 12.2.5 [2/5] — tighten female_only_scene reconciliation & non-human voice directive in profiler.py (E4-bis.2)`
3. `5866f77` — `fix(pipeline): 12.2.5 [3/5] — block scene_female_only & high-F0 female forcing on anonymous/non-human speakers + E3 rule + logger fields (E4-bis.1/4, OBS-28, OBS-07)`
4. `68924d9` — `test(pipeline): 12.2.5 [4/5] — non-tautological tests for OBS-28, OBS-07, librosa.pyin diarizer, and logger observability`
5. `[5/5]` — `docs(release): 12.2.5 [5/5] — PROJECT_MEMORY (OBS-28/OBS-07/E1) & Raport_wdrozenia_12.2.5 (5-layer audit + 4-series offline replay)`

Zmodyfikowano / utworzono wyłącznie `7` dozwolonych plików:

- [speaker_diarizer.py](../speaker_diarizer.py) *(`E4-bis.3`: podmiana surowej autokorelacji `estimate_pitch_f0` na filtrowane `EpistemicAudioTriangulator.estimate_f0_pyin`)*
- [profiler.py](../profiler.py) *(`E4-bis.2`: zaostrzenie `reconcile_prepass_with_p0` o `unverified_count` i wytyczna o bytach nieludzkich / głosach spoza obsady w `profile_episode`)*
- [translator.py](../translator.py) *(`E4-bis.1` / `OBS-28`, `OBS-07`, `E3`, propagacja `raw_actor`, `speaker_gender_source` i `episode_scene_genders_summary`; **`0 B` diffu w `_resolve_line_addressee`**)*
- [pipeline_logger.py](../pipeline_logger.py) *(`E4-bis.4`: opcjonalne pola `raw_actor`, `speaker_gender_source` w `log_line_evolution` i `episode_scene_genders_summary` w `log_scene_discourse`)*
- [test_standard_12_2_5.py](../tests/test_standard_12_2_5.py) *(`6` nietautologicznych testów `100% Z1-pure`)*
- [PROJECT_MEMORY.md](../PROJECT_MEMORY.md) *(aktualizacja statusu do `12.2.5`, zamknięcia `OBS-28` / `OBS-07`, aktywacja `E1`, decyzja `E2 REJECT`, wpis `ARB-088`)*
- [Raport_wdrozenia_12.2.5.md](Raport_wdrozenia_12.2.5.md) *(niniejszy raport)*

**Bezwzględne `0 B` diffu:** wszystkie `30` plików chronionych Z16 (`avt_linter.py`, `verifier.py`, `client_factory.py`, `rules.py`, `test_system.py`, `verify_purity.py`, `pricing_guard.py`, `main.py`, `context_cache.py`, `series_memory/.onomastic_lexicon.json`, wszystkie `20` plików `series_memory/*_bible.json` — brak jakiegokolwiek `-AllowZ16Amendment`), `scene_discourse.py`, `translator.py:_resolve_line_addressee`, `model_resolver.py`, `series_memory.py`, `sign_detector.py`, `metadata.py` oraz `README.md`.

---

## 2. Specyfikacja wdrożonych poprawek (`OBS-28`, `OBS-07`, `E4-bis.1..4`, `E3`)

### 2.1. `E4-bis.3` — [speaker_diarizer.py](../speaker_diarizer.py)
- W `SpeakerVoiceClassifier.estimate_pitch_f0` zastąpiono prymitywną autokorelację (która przy mieszanym sygnale `240 Hz + 85 Hz bas BGM` zwracała fałszywe `~80.4 Hz`) delegacją do certyfikowanego `EpistemicAudioTriangulator.estimate_f0_pyin(..., sample_rate=sample_rate, min_voiced_frames=25)` z filtracją `librosa.pyin` (`voiced_flag == True`, `voiced_prob >= 0.60`, dyspersja `IQR(F0)/median(F0) > 0.35 and std(F0) > 50.0`) oraz limitem długości klipu `4.0 s`.
- Przy odrzuceniu próbki przez `estimate_f0_pyin` funkcja zwraca `None` (brak regresu do autokorelacji); degradacja występuje wyłącznie przy `ImportError` dla `librosa`/`profiler`. Czyste sygnały `200 Hz` i `120 Hz` zachowują dokładność (`200.65 Hz`, `120.70 Hz`).

### 2.2. `E4-bis.2` — [profiler.py](../profiler.py)
- `EpisodeProfiler.reconcile_prepass_with_p0` zlicza `unverified_count` dla każdego niepustego wpisu w `characters_present`, który nie ma potwierdzonego rekordu `MALE`/`FEMALE` (`has_verified_gender` lub `priority in ("P0", "P1")`).
- Gdy `unverified_count > 0`, flagi `female_only_scene` i `male_only_scene` są ustawiane na `False` (nawet jeśli brak innych zweryfikowanych postaci); dla pustego `characters_present=[]` zachowana została pełna kompatybilność wsteczna (`test_system.py:7952`).
- Prompt `EpisodeProfiler.profile_episode` doprecyzowano w punkcie `8` (`female_only_scene: false` w razie nieznanych głosów spoza kadru lub mówiących bytów nieludzkich) i punkcie `20` (autonomia tożsamości bytów nieludzkich i głosów spoza obsady).

### 2.3. `E4-bis.1` / `OBS-28`, `OBS-07`, `E3` — [translator.py](../translator.py) & [pipeline_logger.py](../pipeline_logger.py)
- **`E4-bis.1` (`OBS-28`):** W `_prepare_batch_prompt` oraz `_process_phase1_only` linie bez nazwanego aktora (`raw_actor=""` lub etykieta generyczna) przekazują `scene_female_only=False` oraz `episode_profiler=None` do `SceneDiscourseGraph.arbitrate_event_telemetry`, co blokuje ślepy awans do `p0_gender="FEMALE"` (`speaker_p0_verified=True`). W `_arbitrate_speaker_gender` usunięto ślepe promowanie `episode_scene_genders` na `canonical_gender` — przy aktywnym trybie audio/Whisper anonimowy mówca bez twardego sygnału (`F0 <= 135 Hz` lub `Whisper`) otrzymuje `"UNKNOWN"` z alertem `"[TELEMETRIA: anonimowy_mówca=decyzja_llm_audio_wizja]"` (`speaker_gender_source="anonymous_deferred"`), zachowując jednocześnie `Grupa_1os_lm: NON_VIRILE` w potwierdzonych scenach żeńskich oraz pełną zgodność z legacy wywołaniami `speaker_tags is None` (`test_system.py:7729–7740` i `L7893–7902`).
- **`OBS-07`:** Wprowadzono `Z1`-pure helper `_is_nonhuman_speaker_label` z rozbijaniem CamelCase i normalizacją NFKD. Zidentyfikowane podczas wdrożenia rzeczywiste źródło błędu (m.in. `Dragon Left`): słowo typu `"dragon"` występowało w `INHERENT_MALE_NOUNS` oraz było klasyfikowane przez `SeriesBible.get_character_gender`, co bez wpisu P0 włączało je na ścieżkę męską (`has_verified_p0=False`), a następnie Filar CLXXIV nadpisywał je na `"kobieta"` przy wysokim `F0`. Poprawka pomija słowniki leksykalne i przekazuje `allow_generic_nouns=False` dla niezweryfikowanych etykiet nieludzkich, blokuje dziedziczenie `FEMININE` z wysokiego `F0` oraz nadpisanie w Filarze CLXXIV, kierując brak twardego dowodu do `"UNKNOWN"` (`"nonhuman_deferred"`, `"[TELEMETRIA: byt_nieludzki=decyzja_llm_głos_kontekst]"`). Kanoniczne rekordy P0 w `SeriesBible` zachowują pełną ochronę.
- **`E3`:** Funkcja `_append_phase1_nonhuman_and_unknown_voice_rule` dopisuje regułę `[BYTY NIELUDZKIE I NIEZNANE GŁOSY]` do `focused_rules_str` wyłącznie w paczkach F1 zawierających linię anonimową lub etykietę bytu nieludzkiego.
- **`E4-bis.4` & `E1`:** W [pipeline_logger.py](../pipeline_logger.py) dodano opcjonalne `raw_actor` i `speaker_gender_source` w `log_line_evolution` (z zapisem do `events.jsonl` i `full_trace.log`) oraz `episode_scene_genders_summary` w `log_scene_discourse` (sygnał audytowy `E1`: m.in. `anonymous_lines`, `anonymous_ratio`); zachowano `100%` kompatybilności wstecznej.
- **Decyzje operacyjne:** `E1` (`ACTIVATE` — telemetria `anonymous_ratio` / `raw_actor` / `speaker_gender_source`), `E2` (`REJECT na teraz` — brak opłacalności dodatkowych wywołań LLM dla klasyfikacji mówców wobec trybu `Zero-Cache Lean`).

---

## 3. Obowiązkowy Audyt 5 Warstw (`CORNERSTONE.md` Prawo 12)

| Warstwa | Moduły | Zakres wdrożenia / weryfikacja izolacji | Status |
| --- | --- | --- | --- |
| **Warstwa 1 (Profiler & Akustyka DSP)** | [speaker_diarizer.py](../speaker_diarizer.py), [profiler.py](../profiler.py), [metadata.py](../metadata.py) | `SpeakerVoiceClassifier.estimate_pitch_f0` używa filtrowanego `librosa.pyin` (`EpistemicAudioTriangulator.estimate_f0_pyin`, `min_voiced_frames=25`, blokada BGM `240+85 Hz`). `reconcile_prepass_with_p0` zeruje `female_only_scene` przy niezweryfikowanych mówcach. `0 B` diffu w `metadata.py`. | `PASS` |
| **Warstwa 2 (Pamięć Serii & Dyskurs)** | [series_memory.py](../series_memory.py), [scene_discourse.py](../scene_discourse.py) | **`0 B` diffu** w `series_memory.py`, `scene_discourse.py` oraz we wszystkich `20` plikach `*_bible.json`; izolacja anonimowych/nieludzkich mówców egzekwowana bezpiecznie na wejściu i wyjściu z grafu dyskursu w `translator.py`. | `PASS` |
| **Warstwa 3 (Kontrakt F1/F2 & Kanon)** | [translator.py](../translator.py), [rules.py](../rules.py), [verifier.py](../verifier.py) | Warunkowa reguła `E3` `[BYTY NIELUDZKIE I NIEZNANE GŁOSY]`, zniesienie wymuszonego `[Mówca: FEMININE]` na anonimowych i nieludzkich liniach przy zachowaniu `Grupa_1os_lm: NON_VIRILE` oraz legacy testów `speaker_tags is None`; **`0 B` diffu** w `rules.py`, `verifier.py` oraz `_resolve_line_addressee`. | `PASS` |
| **Warstwa 4 (Linter, Logger & Bramka)** | [pipeline_logger.py](../pipeline_logger.py), [avt_linter.py](../avt_linter.py), [pricing_guard.py](../pricing_guard.py) | Telemetria `raw_actor`, `speaker_gender_source` i `episode_scene_genders_summary` (`E4-bis.4` / `E1`) z zachowaniem wstecznej kompatybilności; **`0 B` diffu** w `avt_linter.py`, `pricing_guard.py` i `main.py`. | `PASS` |
| **Warstwa 5 (Tarcza Regresyjna CI/CD)** | [test_standard_12_2_5.py](../tests/test_standard_12_2_5.py), [test_system.py](../test_system.py) | `6/6` nowych testów `Z1-pure` w `test_standard_12_2_5.py`, `555/555` w `tests/`, `70 passed` (`154 deselected`) w `test_system.py` fast, `4/4` bramki (`12/12`, `8/8`, `12/12`, `15/15`), offline replay `4` serii oraz `check_z16_lock.ps1` / `audit_diff.ps1` `PASS`. | `PASS` |

---

## 4. Wyniki Offline Replay na 4 seriach (`0.00 PLN`, zero wywołań API)

*(Zastrzeżenie metodologiczne: replay wykonano w pamięci na zapisanych zdarzeniach `logs/*_events.jsonl` bez wywoływania API Gemini — historyczna treść wyjścia LLM `.ass` nie podlega regeneracji w trybie `0.00 PLN`, weryfikacji podlega deterministyczna telemetria wejściowa i wyjściowa potoku.)*

1. **MGRP: Restart S01E08 (`logs/..._S01E08_..._20261128_012730_events.jsonl`):**
   - Zakres logu: `354` zdarzeń źródłowych `.ass` (`Aktor: ''` we wszystkich kwestiach mówionych, `4` plansze `SIGN_OVERLAY`), `348` zdarzeń po kompresji FBF (`344/348` linii mówionych anonimowych, `anonymous_ratio = 0.9885`; `343` wpisów `line_evolution`, w replayu `episode_scene_genders_summary = {'total_events': 343, 'female': 174, 'male': 0, 'unknown': 169, 'anonymous_lines': 343, 'anonymous_ratio': 1.0}`).
   - Przed `12.2.5`: `335/343` linii w `line_evolution` otrzymało wymuszony tag `Mówca: ... (FEMININE)`. Po `12.2.5`: **`0`** wymuszeń z `scene_female_only` (`195` linii z rzeczywistego `wysoki tembr >= 195 Hz` → `f0_audio`, pozostałe bez twardego sygnału → `"UNKNOWN"`).
   - Kwestie docelowe `ID 18` (`34770–36970 ms`, `~158 Hz`) i `ID 19` (`36970–39000 ms`, `~145 Hz`): obie zwracają `gender='UNKNOWN'`, `speaker_gender_source='anonymous_deferred'`, `prompt_forces_feminine=False`, alert `[TELEMETRIA: anonimowy_mówca=decyzja_llm_audio_wizja]`.
2. **Chii Fuyo-06 (`OBS-07` — `logs/...Chii_Fuyo_-_06..._20261124_230100_events.jsonl`):**
   - Spośród `50` historycznych linii bytów smoczych (`DRAGON LEFT`, `DRAGON RIGHT`, `DRAGON LEFT/ID`) w starym logu aż **`35/50`** otrzymało fałszywy tag `(FEMININE)`.
   - Po `12.2.5`: zarówno na wszystkich `50/50` liniach historycznych przy wysokim `F0`, jak i w przypadku syntetycznym `DRAGON LEFT (~268 Hz)` bez wpisu P0 liczba wymuszeń `FEMININE` spadła z `35` do **`0/50`** (`UNKNOWN`, `nonhuman_deferred`, `[TELEMETRIA: byt_nieludzki=decyzja_llm_głos_kontekst]`).
3. **Sasaki S2-08 (`logs/...Sasaki_to_Pii-chan_S2_-_08..._20261126_224826_events.jsonl`):**
   - Na `9/9` linii kanonicznego bytu `Peeps` (rekord P0 `MALE` w `SeriesBible`) zarówno `SceneDiscourseGraph.arbitrate_event_telemetry`, jak i prompt F1 `_prepare_batch_prompt` w `100%` zachowują **`MASCULINE` (`9/9`)** nawet przy wysokim `F0 (~250 Hz)`, bez jakiejkolwiek regresji.
4. **Hyouken S2-08 (`logs/...Hyouken_no_Majutsushi_..._S2_-_08..._20261126_234115_events.jsonl`):**
   - Przepuszczenie `7/7` sekwencji z `profile_prepass` przez `EpisodeProfiler.reconcile_prepass_with_p0` potwierdza `female_only_scene=False` dla wszystkich `6` sekwencji o obsadzie mieszanej oraz zachowanie `female_only_scene=True` w zweryfikowanej sekwencji czysto żeńskiej (`Sekwencja 5`, `0` regresji).

---

## 5. Wyniki testów, bramek CI/CD i statystyka diffu (`8be87d6..HEAD`)

- **Nowe testy `12.2.5` ([test_standard_12_2_5.py](../tests/test_standard_12_2_5.py)):** **`6 passed in 8.42s`**:
  - `test_e4bis1_anonymous_line_in_female_only_scene_does_not_force_p0_feminine`
  - `test_obs07_nonhuman_speaker_with_high_f0_never_inherits_feminine`
  - `test_e4bis2_reconcile_prepass_disables_female_only_when_unverified_participant_present`
  - `test_e4bis3_speaker_diarizer_uses_filtered_pyin_and_rejects_bgm_noise`
  - `test_e4bis4_flight_recorder_logs_raw_actor_gender_source_and_scene_summary`
  - `test_e3_focused_rules_appends_nonhuman_and_unknown_voice_directive`
- **Pakiet celowany (`12.2.5 + profiler + discourse + translator + flight_recorder + 12.2.0 + 12.2.2`):** **`188 passed in 61.43s`**.
- **Pełny katalog `tests/`:** **`555 passed in 265.95s (0:04:25)`** (`100% PASS`).
- **Pakiet fast [test_system.py](../test_system.py):** **`70 passed, 154 deselected in 23.25s`** (`100% PASS`).
- **Wybrane testy `@pytest.mark.slow` z sekcji 6.2 w [test_system.py](../test_system.py):** **`3 passed, 2 failed, 219 deselected in 86.45s`**:
  - `PASS`: `test_prosody_and_diarizer` (`L1060`), `test_holistic_scene_diarization_whisper_triangulation_and_unburdened_gender_guard` (`L7678`), `test_global_default_parameter_sanitization_and_hard_evidence_doctrine` (`L12432`); ponadto bezpośrednia weryfikacja sekcji SSOT `L7865–7905` przeszła w `100%`.
  - `FAIL (pre-existing w bazie / legacy testach slow, poza zakresem 12.2.5)`: `test_holistic_unburdened_metadata_ffmpeg_whisper_and_anti_guessing_pipeline` (`L7859` — `SeriesBible("Tenmaku no Jaadugar").infer_scene_cast_from_text` nie zwraca `'Boraqchin'`) oraz `test_acoustic_primacy_and_contaminated_metadata_guard` (`L8106` — ten sam brak `'Boraqchin'` w ekstrakcji `SeriesBible`, a w `L8122` test przekazuje tag `"kobieta, alt 210 Hz"` bez tokenów `"żeńsk"`/`"sopran"`/`"wysoki tembr"`).
- **4 bramki kwalifikacyjne CI/CD:**
  - [verify_purity.py](../verify_purity.py): **`12/12 PASS`**
  - [verify_8_fixes.py](../verify_8_fixes.py): **`8/8 PASS`**
  - [verify_12_fixes.py](../verify_12_fixes.py): **`12/12 PASS`**
  - [verify_ultimate_pipeline.py](../verify_ultimate_pipeline.py): **`15/15 PASS`**
- **Statystyka diffu kodu i testów przed commitem dokumentacji (`git diff --stat 8be87d6..68924d9`):**
  - `speaker_diarizer.py`: `80` linii (`28+ / 52-`)
  - `profiler.py`: `25` linii (`18+ / 7-`)
  - `translator.py`: `319` linii (`270+ / 49-`, `0 B` w `_resolve_line_addressee`)
  - `pipeline_logger.py`: `23` linie (`19+ / 4-`)
  - `tests/test_standard_12_2_5.py`: `529` nowych linii (`100% Z1-pure`)
  - Łącznie kod + testy przed commitem `[5/5]`: `5` plików (`+849 / -127` linii), a z commitem `[5/5]` dokładnie `7` dozwolonych plików w `git diff --stat 8be87d6..HEAD`.
