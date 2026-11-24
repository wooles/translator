# 🏛️ RAPORT WDROŻENIOWY — STANDARD 11.2.27
## Certyfikacja Standardu 11.2.27 (Naprawa `DEF-05` w `enforce_locked_glossary_terms`, domknięcie case-variant `OBS-02` oraz rejestr `OBS-05`/`OBS-06`)

- **Repozytorium:** `https://github.com/wooles/translator` (gałąź `main`)
- **Punkt wyjścia (HEAD baseline 11.2.26):** `a5eee948a23150096926a8726e66f331117ca72e` (`a5eee94`)
- **Commit 1 (Kod produkcyjny):** `5b940f2` (`fix(pipeline): handle slash/semicolon glossary variants without separator injection in enforce_locked_glossary_terms (DEF-05) and deduplicate case-variant generic registry entries (OBS-02) (11.2.27)`)
- **Commit 2 (Testy regresyjne):** `ffa8bdb` (`test(pipeline): verify DEF-05 slash/semicolon glossary variant guard and OBS-02 case-variant registry deduplication (11.2.27)`)
- **Commit 3 (Dokumentacja i Zamknięcie Wydania):** `HEAD` (`docs(release): certify Standard 11.2.27 — DEF-05 glossary variant guard, OBS-02 case-variant dedup, OBS-05 closure and OBS-06 log`)
- **Baseline ochrony Z16 (`c197db7` + Z16-amendment #15 z `6852a5a`):** **bezwzględne 0 B diffu** na wszystkich 29 plikach chronionych Z16 oraz na `pipeline_logger.py`, `scene_discourse.py`, `series_memory.py` i `glossary_manager.py` względem `a5eee94`.
- **Data certyfikacji:** 2026-11-24
- **Koszt wykonania:** 0.00 PLN (testy jednostkowe i bramki AST w 100% lokalne)

---

## 1. CEL I PRZYCZYNY ŹRÓDŁOWE (`DEF-05` ORAZ CASE-VARIANT `OBS-02`)

1. **Krytyczny defekt `DEF-05` (`translator.py:enforce_locked_glossary_terms`):**
   - Wpisy glosariusza zawierające separator alternatywy `/` lub `;` (np. `"zakląć / wzmocnić"`) były dzielone przez `.split()` jak fraza 3-wyrazowa i dopasowywane w kroku 2 przez `three_word_pat`, co mogło wycinać sąsiednie słowa dialogu (przypadek `#313`/`#314` dla `<ODCINEK>` w `<SERIA>`) albo wstrzykiwać dosłowny separator `/` do wyjścia.
   - **Naprawa:** Wprowadzono detekcję `has_variant_sep` oraz listę czystych wariantów `pl_variants`. Krok 2 (regexy 2/3-wyrazowe) wykonuje się wyłącznie przy `not has_variant_sep`, a Krok 3 sprawdza obecność któregokolwiek wariantu z `pl_variants` (pozwalając F2 swobodnie przełączyć jeden poprawny wariant na drugi) oraz blokuje fallback do skażonego `phase1_pl` zawierającego `/` lub `;`.
2. **Domknięcie case-variant `OBS-02` (`translator.py:_prepare_batch_prompt`):**
   - `entry_meta` było indeksowane znormalizowanym kluczem `c_low`, przez co wersalikowy duplikat tła (np. `"BOHATERKA_A"`) nadpisywał lub zderzał się z bogatszym wpisem tej samej nazwy o innej wielkości liter (`"Bohaterka_A"`), a porównanie `o_low != name_low` uniemożliwiało usunięcie duplikatu.
   - **Naprawa:** `entry_meta` indeksuje się oryginalnym kluczem `c_name`, w `alias_owners` przechowuje się `(c_name, rank)`, a w pętli renderowania porównuje `o_raw != name and o_rank > my_rank`.

---

## 2. REJESTR OBSERWACJI I ROADMAP (`OBS-05`, `OBS-06`, `KNOWN GAP`)

- **`OBS-05` — `CLOSED`:** `(random LLM artifact, 1/71 @ \N, 0.09% all lines; reopen if recurs in 3 consecutive runs)` — bez modyfikacji chronionego Z16 `verifier.py`.
- **`OBS-06` — `OPEN (non-blocking observation)`:** potencjalny wyścig czasowej podmiany `_v_pool.report_error` w `_process_phase2_only` przy przyszłym zwiększeniu równoległości F2 do `max_workers_f2 >= 2` (obecnie na Hydrogen F2 pracuje sekwencyjnie `1:1`; rekomendacja na przyszłość: dispatch przez `threading.local()`, bez zmian w kodzie w `11.2.27`).
- **Status `KNOWN GAP` do kolejnego przebiegu kontrolnego:** `DEF-04` (przecinek przed `, czy (bez|nie|tak)` w pytaniach zależnych) oraz `OBS-01` (uzgadnianie płci rodzica w JSON); `DEF-01`, `DEF-02`, `DEF-03` potwierdzone jako zamknięte produkcyjnie.

---

## 3. METRYKI CI/CD I IZOLACJA Z16

- `tests/test_standard_11_2_27.py`: **2 / 2 PASSED**
- `tests/test_standard_11_2_23.py`: **5 / 5 PASSED**
- `tests/`: **452 / 452 PASSED**
- `test_system.py`: **70 PASSED, 154 DESELECTED**
- Bramki kwalifikacyjne: `verify_purity.py` (**11/11 PASS**), `verify_8_fixes.py` (**8/8 PASS**), `verify_12_fixes.py` (**12/12 PASS**), `verify_ultimate_pipeline.py` (**15/15 PASS**)
- Audyt śledczy: `audit_diff.ps1 -BaseRef "a5eee94"` -> **VICTORY CONFIRMED**
- Izolacja Z16 i nieobjętych modułów względem `a5eee94`: **0 B DIFF**
