# 📋 RAPORT WDROŻENIOWY — MIKRO-HOTFIX 11.2.2: ŚCISŁA IZOLACJA MODELU GEMINI-4-HYDROGEN OD GEMINI-4-ARGON ORAZ BLOKADA WYCOFANYCH MODELI 2.X (404) W MODEL_RESOLVER.PY

- **Repozytorium:** `https://github.com/wooles/translator` (gałąź `main`)
- **Data wdrożenia:** `2026-11-13`
- **Wersja standardu przed wdrożeniem:** `Standard 11.2.1 (WhisperDisambiguator Scope Fix & Live Hydrogen Server Probe Menu Restoration Baseline)`
- **Wersja standardu docelowa:** `Standard 11.2.2 (Strict Hydrogen Tier Isolation & Retired 2.x Model Guard Baseline)`
- **Punkt wyjścia (HEAD przed wdrożeniem):** `208388cf6073609f4e02311b3c85c67921750145` (`208388c`)
- **Commit 1 (fix):** `bacb2d9` (`bacb2d9`)
- **Commit 2 (test — Nowy Commit Certyfikacji Kodu):** `1c18bef29e64f06867d66303e35e04752ae3db60` (`1c18bef`)
- **Commit 3 (docs — Release):** `HEAD` (Bieżący commit dokumentacyjny)
- **Baseline Ochrony Z16 (Depuracja Legacy 1.0):** `c197db73c3dabf887dddbf2337dc3a1d8cff598c` (`c197db7` — nienaruszony, bezwzględne 0 B diffu na wszystkich plikach chronionych Z16, brak potrzeby Z16-amendment)

---

## 1. PODSUMOWANIE WYKONAWCZE I CELE MIKRO-HOTFIXU 11.2.2 (INC-AVT-037)

Mikro-Hotfix 11.2.2 usuwa dwa krytyczne defekty w mechanizmie automatycznego rozwiązywania wersji modeli Google Gemini (`model_resolver.py`) oraz uzgadnia taryfikację w `pricing_guard.py`:
1. **Kolizja Alfabetyczna i Podmiana `gemini-4-hydrogen` na `gemini-4-argon` (INC-AVT-037):**
   W funkcji `resolve_best_models` warunek kwalifikacji do `hydrogen_candidates` obejmował wyrażenie regularne `re.search(r"gemini-4(?:\b|[-_.])", name_lower) and "flash" not in name_lower`. Ponieważ model `gemini-4-argon` spełniał ten warunek i otrzymywał identyczny wynik wersji `(4, 0, 0)` co `gemini-4-hydrogen`, a lista z `client.models.list()` zwraca modele w porządku alfabetycznym (`argon` < `hydrogen`), stabilne sortowanie Timsort wybierało `gemini-4-argon` jako `best_hydrogen`. Skutkowało to kierowaniem zapytań Profilu 3 (Mistrzowski) do modelu Argon zamiast dedykowanego i zoptymalizowanego kosztowo modelu Hydrogen.
2. **Blokada Wycofanych Modeli Generacji 1.x oraz 2.x (Błędy 404):**
   API Google AI Studio wciąż zwraca na liście modeli wycofane wersje (np. `gemini-2.5-pro`, `gemini-2.0-flash`). Wcześniejszy kod dopuszczał je do `pro_candidates`, w efekcie czego wycofany `gemini-2.5-pro` nadpisywał sprawdzony model bazowy `defaults["pro"]` (`gemini-3.1-pro-preview`), co prowadziło do błędów HTTP 404 Not Found podczas prób inferencji.
3. **Uzgadnienie Stawek w `pricing_guard.py`:**
   W module monitora finansowego zaktualizowano przypisywanie stawek: wyłącznie modele zawierające token `hydrogen` podlegają taryfie `GOOGLE_API_RATES["hydrogen"]`, natomiast modele klasy ciężkiej/pro (`pro`, `argon`, `carbon`) rozliczane są według oficjalnej taryfy `GOOGLE_API_RATES["pro"]`.

---

## 2. SZCZEGÓŁOWA ANALIZA IMPLEMENTACJI W KODZIE ŹRÓDŁOWYM

### 2.1. Odfiltrowanie Modeli Wycofanych i Ścisła Izolacja Tierów w `model_resolver.py`
- Wewnątrz pętli po surowych modelach (`raw_models`) dodano twardy filtr wykluczający wersje generacji 1.x oraz 2.x:
  ```python
  score = _extract_model_score(name)
  # Pomijanie wycofanych modeli generacji 1.x oraz 2.x (np. gemini-2.5-pro zwracających 404)
  if score[0] > 0 and score[0] < 3:
      continue
  ```
- Wprowadzono ścisły warunek dla koszyka `hydrogen_candidates` wykluczający nazwy z `argon`, `carbon` oraz `pro`:
  ```python
  if "hydrogen" in name_lower and "argon" not in name_lower and "carbon" not in name_lower and "pro" not in name_lower:
      hydrogen_candidates.append(name)
  elif "flash-lite" in name_lower:
      flash_lite_candidates.append(name)
  elif "flash" in name_lower:
      flash_candidates.append(name)
  elif "pro" in name_lower or "argon" in name_lower or "carbon" in name_lower:
      if score >= (3, 1, 0) or "argon" in name_lower or "carbon" in name_lower:
          pro_candidates.append(name)
  ```
- Dodano deterministyczne rozstrzyganie remisów (tie-breaker) podczas sortowania:
  ```python
  hydrogen_sorted = sorted(
      hydrogen_candidates,
      key=lambda n: (_extract_model_score(n), 1 if n.lower() == "gemini-4-hydrogen" else 0),
      reverse=True
  )
  pro_sorted = sorted(
      pro_candidates,
      key=lambda n: (_extract_model_score(n), 1 if "pro" in n.lower() else 0),
      reverse=True
  )
  ```

### 2.2. Precyzyjna Kategoryzacja Kosztowa w `pricing_guard.py`
- W metodzie `PricingGuard.calculate_actual_cost_breakdown` (zarówno dla Fazy 1, jak i Fazy 2) przypisano stawki:
  ```python
  if "hydrogen" in str(m1).lower():
      rate1 = GOOGLE_API_RATES["hydrogen"]
  elif "pro" in str(m1).lower() or "argon" in str(m1).lower() or "carbon" in str(m1).lower():
      rate1 = GOOGLE_API_RATES["pro"]
  elif "lite" in str(m1).lower():
      rate1 = GOOGLE_API_RATES["flash_lite"]
  ```

---

## 3. PAKIET TESTÓW REGRESYJNYCH I METRYKI CI/CD

W Commicie 2 (`1c18bef29e64f06867d66303e35e04752ae3db60`) wdrożono dedykowany test:
`tests/test_translator.py::test_t11_2_2_strict_hydrogen_vs_argon_isolation_and_retired_2x_model_guard`

Test weryfikuje w 100% offline (0.00 PLN):
1. **Scenariusz alfabetyczny z modelem Argon:** Gdy API zwraca listę zawierającą `gemini-4-argon` przed `gemini-4-hydrogen`, `resolve_best_models` bezbłędnie izoluje `resolved["hydrogen"] == "gemini-4-hydrogen"`, a `gemini-4-argon` trafia do `resolved["pro"]`.
2. **Scenariusz wycofanych modeli 2.x:** Gdy na liście API obecne są wycofane modele `gemini-2.5-pro` i `gemini-2.0-flash` (bez modeli pro >= 3.1), zostają one odfiltrowane, a `resolved["pro"]` bezpiecznie wskazuje na domyślny `gemini-3.1-pro-preview`.
3. **Kalkulacja kosztów:** Koszt sesji dla `gemini-4-argon` i `gemini-4-carbon` poprawnie odzwierciedla stawki klasy Pro, przewyższając taryfę zoptymalizowanego `gemini-4-hydrogen`.

### Stan końcowy metryk:
- **Pakiet testów jednostkowych i integracyjnych:** `430 passed, 153 deselected in 51.84s` (100% PASS, 0 błędów, 0 ostrzeżeń).
- **verify_purity.py:** `12/12 PASS` (100% Czysty, zero instancji, zero łatek onomastycznych).
- **verify_8_fixes.py:** `8/8 PASS` (Pełna zgodność architektoniczna potoku).
- **verify_12_fixes.py:** `12/12 PASS` (Pełna integralność 12 punktów potoku).
- **verify_ultimate_pipeline.py:** `15/15 PASS` (15 bramek runtime i architektury).
- **audit_diff.ps1:** `4/4 PASS` — `[VICTORY CONFIRMED -- KOD CZYSTY I UOGOLNIONY]`.
- **Baseline Z16 (Depuracja Legacy 1.0):** `c197db73c3dabf887dddbf2337dc3a1d8cff598c` — bezwzględne **`0 B diffu`** na wszystkich plikach chronionych.

---

## 4. CERTYFIKAT ZGODNOŚCI ARCHITEKTONICZNEJ

Potok AVT w rewizji `Standard 11.2.2 Baseline` spełnia wszystkie wymogi nienaruszalnych zasad architektonicznych: Zero-Literal Invariant (`Z1`), Pure Positive Domain Invariant (`Z2`), Primary LLM Translation Authority (`Z3`), 5-Layer Protocol (`Z4`) oraz Depuracji Legacy 1.0 (`Z16`). Wszystkie operacje wykonano w środowisku lokalnym przy koszcie dokładnie **0.00 PLN**.
