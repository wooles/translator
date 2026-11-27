# Raport wdrożenia Standard 12.2.3 + 12.2.3a (`Q1 + Q3 + Q4 + Q2 Faza 1 Opt-In Flex` — `0.00 PLN`, `0 B` diff Z16)

**Data:** `2026-11-28`  
**Baza startowa (`main`):** `21d64c3273ee6284d99580d4bdc2608f575e2477` (`21d64c3`, `12.2.2 + 12.2.2a CLOSED`)  
**Status:** `VICTORY CONFIRMED` (`0.00 PLN` wydatku na API; `0 B` diffu w plikach chronionych Z16 oraz `DEF-02`)

---

## 1. Zakres plików i twarda izolacja (`21d64c3..HEAD`)

W ramach wdrożenia zmodyfikowano/utworzono wyłącznie `7` dozwolonych plików:

1. [translator.py](../translator.py) — adaptacyjny sufit F2 (`Q1`), priorytet ekstremalnego CPS i gęstych plansz (`Q3` + `12.2.3a`), strażnik cięcia sceny bez aktora (`Q4`) oraz opt-in Gemini Flex Inference F1 z fallbackiem `2x 503/timeout -> standard` na modelu Hydrogen (`Q2`).
2. [model_resolver.py](../model_resolver.py) — `resolve_service_tier`, `apply_service_tier_to_config` oraz `extract_response_service_tier_header`.
3. [profiler.py](../profiler.py) — obsługa opt-in `AVT_SERVICE_TIER` i fallback `2x 503/timeout -> standard` w `EpisodeProfiler.profile_episode`.
4. [sign_detector.py](../sign_detector.py) — obsługa opt-in `AVT_SERVICE_TIER` i bezbłędny fallback `2x 503/timeout -> standard` w `VisualSignDetector.detect_signs_in_gaps`.
5. [test_standard_12_2_3.py](../tests/test_standard_12_2_3.py) — `6` nietautologicznych testów regresyjnych opartych o realny `genai.Client` + `httpx.MockTransport`.
6. [PROJECT_MEMORY.md](../PROJECT_MEMORY.md) — synchronizacja statusu operacyjnego oraz wpis `ARB-086 / INC-AVT-084`.
7. [Raport_wdrozenia_12.2.3.md](Raport_wdrozenia_12.2.3.md) — niniejszy raport końcowy.

**Bezwzględne `0 B` diffu:** wszystkie `30` plików chronionych Z16 (w tym `verifier.py`, `pricing_guard.py`, `avt_linter.py`, `client_factory.py`, `rules.py`, `test_system.py`, `verify_purity.py`), `scene_discourse.py`, `pipeline_logger.py`, `series_memory.py`, `tools/verify_f2_consolidation_ab.py` oraz `translator.py:_resolve_line_addressee`.

---

## 2. Łańcuch commitów na `main`

- `58ef381` — `fix(pipeline): 12.2.3 [1/5] — adaptive F2 cap (Q1)`
- `90edb34` — `fix(pipeline): 12.2.3 [2/5] — CPS>25 priority boost (Q3) + OBS-18 scene-cut uppercase guard (Q4)`
- `1229bb9` — `feat(pipeline): 12.2.3 [3/5] — opt-in Gemini Flex Inference for F1 (Q2 Phase 1)`
- `fc61e5e` — `test(pipeline): 12.2.3 [4/5] — non-tautological tests for Q1/Q3/Q4/Q2`
- `0f2c60b` — `fix(pipeline): 12.2.3a — preserve complex long visual sign priority alongside CPS>25 boost`
- `[5/5]` — `docs(release): 12.2.3 [5/5] — PROJECT_MEMORY & Raport_wdrozenia_12.2.3`

---

## 3. Wdrożone mechanizmy (`Q1`, `Q3 + 12.2.3a`, `Q4`, `Q2 Faza 1`)

### 3.1. `Q1`: Adaptacyjny sufit selektora F2 ([translator.py](../translator.py))
- Dodano funkcję `_compute_adaptive_f2_episode_cap(total_lines, base_cap=115, max_cap=170, target_ratio=0.32)`:
  - Dla krótkich i nieznanych odcinków (`None`, `<= 0`, `<= 360` linii) wynik wynosi niezmiennie **`115`** (`base_cap`).
  - Dla dłuższych odcinków próg skaluje się liniowo (`int(0.32 * total_lines)`, np. `450 -> 144`, `489 -> 156`) aż do sufitu **`170`** (`>= 532` linii).
- `_process_phase1_only` zapisuje `total_lines` w `phase1_data`; `_process_phase2_only` oraz `_consolidate_phase2_batches` wyliczają adaptacyjny sufit i przekazują go do `_select_hydrogen_phase2_candidates(..., episode_line_cap=...)`, przy zachowaniu domyślnego `episode_line_cap: int = 115`.

### 3.2. `Q3 + 12.2.3a`: Priorytet ekstremalnego CPS > 25 i ochrona gęstych plansz ([translator.py](../translator.py))
- W `_score_phase2_editorial_risk` (współdzielonym z `_score_phase2_editorial_risk_detailed`) wyliczane jest `cps_val` z jawnego pola `cps` lub `len(vis_cps) / max(0.2, dur_s)`.
- Dialogi niebędące planszami z `cps_val > 25.0` otrzymują priorytet **`cps_extreme:+60`** oraz pomijają karę tłumiącą `trivial_short`. Krótkie plansze ekranowe (`is_sign=True`) pozostają neutralne (`0` pkt).
- **Korekta `12.2.3a` (`0f2c60b`):** regresja w `test_bug3` ujawniła, że przy sztucznie krótkim oknie `1.8s` gęste wielowyrazowe plansze/chroniki (`is_sign=True`, `>= 10` słów i `>= 75` znaków angielskich) przegrywały konkurencję o limit `10` miejsc na paczkę z szybkimi dialogami `> 25 CPS`. Dodano wagę **`long_sign_banner:+60`** wyłącznie dla długich wielowyrazowych plansz (`0–2` obiekty na odcinek produkcyjny; krótkie plansze nadal otrzymują `0` pkt).

### 3.3. `Q4`: Strażnik małej litery na cięciu sceny bez aktora ([translator.py](../translator.py))
- `_is_speaker_change_lowercase` rozpoznaje etykiety nieznanego/brakującego aktora (`{"", "unknown", "/", "postać"}`).
- Przy braku pary znanych mówców funkcja wymaga wyraźnej pauzy międzyscenowej (`gap_ms >= 3500`, z `time_gap_ms` lub różnicy `start_ms - prev.end_ms`), wyzwalając ochronę wielkiej litery F2 wyłącznie po cięciu montażowym i chroniąc legalne kontynuacje `< 3500 ms`, tagi ASS `{...}` oraz wielokropek.

### 3.4. `Q2` Faza 1: Opt-In Gemini Flex Inference (`AVT_SERVICE_TIER`)
- **[model_resolver.py](../model_resolver.py):**
  - `resolve_service_tier(explicit_tier=None)` zwraca `"flex"` wyłącznie po jawnym opt-in (`AVT_SERVICE_TIER=flex`), a dla wartości domyślnych, pustych i nieznanych bezpiecznie utrzymuje **`"standard"`**.
  - `apply_service_tier_to_config(cfg_kwargs, service_tier, model_name="")` dla `"flex"` wstrzykuje zarówno `service_tier="flex"`, jak i nagłówek `X-Gemini-Service-Tier: flex` w `types.HttpOptions` (zachowując kompatybilność z zainstalowanym `google-genai`), nie dotykając konfiguracji przy `"standard"`.
  - `extract_response_service_tier_header(response)` odczytuje opcjonalny nagłówek odpowiedzi niezależnie od wielkości liter.
- **[translator.py](../translator.py), [profiler.py](../profiler.py), [sign_detector.py](../sign_detector.py):**
  - `_call_gemini_with_retry`, `EpisodeProfiler.profile_episode` oraz `VisualSignDetector.detect_signs_in_gaps` utrzymują domyślny tryb `"standard"`; przy opt-in `"flex"` po **`2` kolejnych błędach `503/timeout`** przełączają się najpierw na `"standard"` **na tym samym modelu `gemini-4-hydrogen`** przed jakimkolwiek fallbackiem do modelu Flash.
  - `log_cli_init` zapisuje `runtime_meta["service_tier"]`, a `last_batch_token_usage` rejestruje `service_tier` oraz opcjonalny `response_service_tier_header`. Zero zmian modelu i `0 B` diffu po stronie F2 (`verifier.py`).

---

## 4. Replay offline na logach produkcyjnych w `logs/` (`0.00 PLN`)

Zweryfikowano działanie operatorów `Q1`, `Q3`, `Q4` i filtru `long_signs` na najnowszych produkcyjnych plikach `*_events.jsonl` z katalogu `logs/`:

| Próba produkcyjna (`logs/`) | `total_lines` | `Q1` `adaptive_cap` | `Q3` linie `CPS > 25` (`phase1_pl`) | `Q4` trafienia bezaktorskiego cięcia (`>= 3.5s`) | `12.2.3a` długie plansze (`>=10w & >=75c`) |
| --- | ---: | ---: | ---: | ---: | ---: |
| Długi odcinek A (`489` linii) | `489` | **`156`** (`+41`) | `3` (max `33.2 CPS`) | `1` | `0 / 3` |
| Średni odcinek B (`386` linii) | `386` | **`123`** (`+8`) | `0` | `0` | `1 / 57` |
| Średni odcinek C (`361` linii) | `361` | `115` | `0` | `0` | `2 / 45` |
| Średni odcinek D (`358` linii) | `358` | `115` | `0` | `0` | `1 / 49` |
| Krótki odcinek E (`326` linii) | `326` | `115` | `0` | `0` | `0 / 16` |

Analiza potwierdziła również `14 / 16` trafień `cps > 25` ze znacznym przyrostem długości tekstu w F1 (`ratio >= 1.06`) w szerszej próbie logów oraz ściśle punktowy udział złożonych plansz ekranowych (`0–2` na cały odcinek).

---

## 5. Wyniki testów i bramek kwalifikacyjnych (`0.00 PLN`, po ostatniej edycji kodu `0f2c60b`)

- **[test_standard_12_2_3.py](../tests/test_standard_12_2_3.py):** **`6 passed`** (realny `genai.Client` + `httpx.MockTransport` na granicy sieciowej HTTP, zero mockowania logiki domenowej):
  - `test_q1_adaptive_f2_episode_cap_scaling_and_short_episode_invariance`
  - `test_q3_extreme_cps_above_25_gets_plus60_and_bypasses_trivial_short`
  - `test_q4_obs18_actorless_scene_cut_lowercase_guard`
  - `test_q2_flex_opt_in_default_standard_and_config_application`
  - `test_q2_flex_f1_two_503_fallback_to_standard_same_hydrogen_model_and_cli_meta`
  - `test_q2_flex_profiler_and_sign_detector_respect_opt_in_and_503_fallback`
- **Regresja `12.x + translator + profiler`:** **`165 passed in 73.92s (0:01:13)`**.
- **Pełny pakiet `tests/`:** **`544 passed in 246.25s (0:04:06)`**.
- **Szybki pakiet systemowy `test_system.py` (`-m "not slow and not network" -k "not test_batch_coalescence_ssot_prompt_and_cot_streamlining_guard"`):** **`70 passed, 154 deselected in 22.49s`** (łącznie `614 passed`).
- **4 bramki kwalifikacyjne CI/CD:**
  - `verify_purity.py`: **`12/12 PASS`**
  - `verify_8_fixes.py`: **`8/8 PASS`**
  - `verify_12_fixes.py`: **`12/12 PASS`**
  - `verify_ultimate_pipeline.py`: **`15/15 PASS`**
- **Audyt śledczy i blokada Z16/DEF-02:** `tools/check_z16_lock.ps1 -BaseRef "21d64c3..HEAD"` (`PASS`) oraz `audit_diff.ps1 -BaseRef "21d64c3"` (`VICTORY CONFIRMED`).
