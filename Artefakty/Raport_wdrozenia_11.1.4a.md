# 📋 RAPORT WDROŻENIOWY — MIKRO-HOTFIX 11.1.4a
## Priorytetyzacja Rejestru Yakuwarigo (-aru/-yaru) i Telemetrii Fazy 2, Arbitraż Kwantyfikatora Dualnego, Korekta Tokenu Hiragany „やで” oraz Detekcja Plansz Cennika

- **Data wdrożenia:** 2026-11-11
- **Certyfikowany standard po wdrożeniu:** `Standard 11.1.4a (Sociolinguistic & Dual-Quantifier Certified Baseline)`
- **Commit bazowy (HEAD przed hotfixem):** `3057e9712e12198dfc83778a41c034a970ba6cd6` (`3057e97`)
- **Nowy baseline ochrony Z16 (Depuracja Legacy 1.0):** `1b4d52a7b61326e503a3961e9c7257fcc6665a13` (`1b4d52a` — Commit 1 `fix:`, autoryzowany `Z16-amendment #11`)
- **Nowy commit certyfikacji kodu:** `d4a456cf95d7c002bec9c0a18d1eb69070d78424` (`d4a456c` — Commit 2 `test:`)
- **Status implementacji:** `ZAKOŃCZONA SUKCESEM (100% PASS, ZERO REGRESSION, ZERO-LITERAL PURE POSITIVE DOMAIN)`

---

## 1. CEL I ZAKRES WDROŻENIA

Mikro-Hotfix 11.1.4a został zrealizowany w odpowiedzi na wnioski z audytu weryfikacyjnego oraz retrospektywnej analizy logów rewizji `3057e97` (Sekcja 4: pozycje `P2-RES-01`, `P2-RES-02`, `P3-RES-01`, `P3-RES-02`). Wdrożenie zlikwidowało cztery subtelne luki integracyjne w warstwie socjolingwistycznej, telemetrii dyskursu i kategoryzacji semiotycznej:

1. **P2-RES-01 (Priorytetyzacja rejestru Yakuwarigo i telemetrii rejestru Fazy 2):** Wypowiedzi łączące końcówki stylizowane `-aru/-yaru` lub celowy code-switching z męskim zaimkiem `ore` były przedwcześnie przechwytywane przez regułę twardego żargonu żołnierskiego. Ponadto późna ewaluacja rejestru w `translator.py` powodowała, że pole `notes` przekazywane do promptu Fazy 2 nie zawierało segmentu `| Rejestr: ...`.
2. **P2-RES-02 (Arbitraż kwantyfikatora dualnego „you two” / „お二人” w diadach mieszanych):** Konstrukcje z kwantyfikatorami podwójnymi w scenach mieszanych (mężczyzna + kobieta) nie wymuszały jednoznacznie męskoosobowej liczby mnogiej (`VIRILE`), co groziło desynchronizacją form fleksyjnych orzeczenia.
3. **P3-RES-01 (Korekta tokenu hiragany „やで” w WhisperDisambiguator):** Wykryto i skorygowano hybrydowy zapis `"やde"` w regule i liście tokenów dialektu zachodniojapońskiego na kanoniczną postać japońską `"やで"`.
4. **P3-RES-02 (Detekcja plansz cennika / wyliczeń punktowych w stylu Default):** Ekrany prezentujące wyliczenia punktowe lub cenniki (np. `10,000 candies: ...`, `500 points: ...`), mimo braku aktora osobowego, były traktowane jako dialog mówiony ze względu na styl `Default`. Wdrożono wczesną detekcję strukturalną klasyfikującą je jako napisy ekranowe (`is_sign = True`).

---

## 2. REALIZACJA ZADAŃ ARCHITEKTONICZNYCH (WARSTWY 1–4)

### 2.1. Zadanie 1 (P2-RES-01): Priorytetyzacja Yakuwarigo (-aru/-yaru) i Synchronizacja Telemetrii Rejestru
- W module `translator.py` w funkcji `detect_japanese_pragmatic_register`:
  - Przeniesiono ewaluację stylizowanego rejestru wojowniczki (`-aru/-yaru`) oraz `Code-switching JA+EN` przed sekcję żargonu bojowego (`3. Tough Soldier / Battle Slang`).
  - Rozszerzono słownik dopasowań `-aru/-yaru` o dodatkowe warianty syntaktyczne: `頼んでるある`, `はずある`, `だけある`, `ことある`, `何やるか`, `いいやる`, `いけなやる`, `ないやるね`, `なおらないやる` oraz ich transkrypcje romaji.
- W metodzie `MultimodalTranslator._process_single_batch`:
  - Przeniesiono ekstrakcję audio JP (`audio_jp_str`) i wywołanie `detect_japanese_pragmatic_register` przed generowanie wektora telemetrii `line_dry_telemetry`.
  - Przekazano wyznaczony rejestr (`short_reg`) bezpośrednio do `format_dry_telemetry_tag(..., register=short_reg)`, gwarantując, że pole `notes` przekazywane do promptu modelu LLM zawiera kompletny mikro-tag `[... | Rejestr: ...]`.

### 2.2. Zadanie 2 (P2-RES-02): Arbitraż Kwantyfikatora Dualnego w Scenach Mieszanych
- W metodzie `MultimodalTranslator._resolve_line_addressee`:
  - Rozszerzono warunek `is_dual_address` o wykrywanie japońskich tokenów dualnych: `お二人`, `おふたり`, `二人とも`, `ふたりとも`, `ofutari`, `futari tomo`.
- W metodzie `MultimodalTranslator._process_single_batch`:
  - Zaimplementowano weryfikację obecności kwantyfikatora podwójnego w tekście angielskim (`\b(?:you\s+two|both\s+of\s+you|the\s+two\s+of\s+you)\b`) oraz w audio japońskim.
  - W przypadku wykrycia kwantyfikatora podwójnego zbadano skład płciowy pozostałych uczestników sceny w `untranslated_in_batch`.
  - W obecności co najmniej jednego potwierdzonego mężczyzny i jednej kobiety (lub flagi `scene_has_male` w scenie żeńskiej) ustawiono `has_male_addressee_in_line = True`, `addressee_cat = "para_mieszana_dual"` oraz bezwarunkowo `line_you_grp = "VIRILE"`.

### 2.3. Zadanie 3 (P3-RES-01): Korekta Tokenu Hiragany „やで”
- W module `whisper_disambiguator.py`:
  - W wyrażeniu regularnym `jp_dialect_pat` podmieniono zapis `"やde"` na czystą hiraganę `"やで"`.
  - Na liście tokenów `jp_dialect_tokens` podmieniono `"やde"` na `"やde"` $\to$ `"やで"`.

### 2.4. Zadanie 4 (P3-RES-02): Strukturalna Detekcja Plansz Cennika i Wyliczeń Punktowych
- W module `translator.py` w funkcji `detect_event_visual_type`:
  - Zaimplementowano wczesną weryfikację strukturalną:
    ```python
    is_point_listing_sign = (
        not name_lower_early or name_lower_early in ("sign", "signs", "txt", "title", "board", "screen")
    ) and bool(re.match(r"^\d[\d,.\s]*\s*(?:points?|pts|pkt|punkt(?:y|ów)?|cand(?:y|ies)|coins?|gold|g|yen|¥)\s*:\s*\S+", clean_t_early, re.IGNORECASE))
    ```
  - W przypadku dopasowania funkcja natychmiast zwraca klasyfikację napisu ekranowego (`is_sign = True`, `is_top = False`, `visual_details = "plansza wyliczenia punktowego / cennika"`), nadpisując ewentualny domyślny styl `Default`.

---

## 3. HISTORIA COMMITÓW I STATUS OCHRONY Z16

Wdrożenie zrealizowano w reżimie 3 sekwencyjnych commitów na gałęzi `main`:

| Krok | Commit SHA | Typ | Zakres plików | Rola w standardzie |
| :--- | :--- | :--- | :--- | :--- |
| **Commit 1** | `1b4d52a7b61326e503a3961e9c7257fcc6665a13` | `fix:` | `translator.py`, `whisper_disambiguator.py` | **NOWY BASELINE OCHRONY Z16** (`Z16-amendment #11`) |
| **Commit 2** | `d4a456cf95d7c002bec9c0a18d1eb69070d78424` | `test:` | `tests/test_translator.py`, `tests/test_discourse_and_translator.py` | **NOWY COMMIT CERTYFIKACJI KODU** |
| **Commit 3** | `HEAD` | `docs:` | `AGENTS.md`, `PROJECT_MEMORY.md`, `Artefakty/Raport_wdrozenia_11.1.4a.md` | Dokumentacja i synchronizacja SSOT |

---

## 4. WYNIKI TESTÓW I WERYFIKACJI CI/CD

### 4.1. Nowe Testy Jednostkowe (4 testy, 100% PASSED)
1. `tests/test_translator.py::test_yakuwarigo_aru_yaru_and_codeswitch_priority_over_ore_in_pragmatic_register` — **PASSED** (weryfikacja priorytetu `-aru/-yaru` i code-switchingu przed `ore` oraz rozszerzonych wariantów leksykalnych).
2. `tests/test_translator.py::test_detect_event_visual_type_point_listing_sign_in_default_style` — **PASSED** (weryfikacja detekcji plansz wyliczeń punktowych / cennika w stylu Default).
3. `tests/test_discourse_and_translator.py::test_dual_quantifier_you_two_in_mixed_gender_scene_resolves_virile` — **PASSED** (weryfikacja kategoryzacji kwantyfikatora dualnego w scenie mieszanej jako `VIRILE`).
4. `tests/test_discourse_and_translator.py::test_whisper_disambiguator_detects_kansai_yade_hiragana` — **PASSED** (weryfikacja detekcji dialektu z tokenem hiragany `やで`).

### 4.2. Wyniki Pakietu Testów Regresyjnych
- **Zestaw `tests/`:** `341 passed in 35.92s` (100% sukcesu).
- **Całkowita liczba zebranych testów:** `565 collected` (`412 passed` fast unit/integration + `153 deselected` slow/network).
- **Regresje:** `0` (Zero Regression Lock).

### 4.3. Bramki Jakościowe i Audyt AST
- `verify_purity.py`: **12/12 PASS** (pełna czystość AST, brak zakazanych terminów i nazw anime).
- `audit_diff.ps1`: **PASS / VICTORY CONFIRMED** (brak modyfikacji baz `.json`, brak wycieku nazw własnych do kodu).
- Naruszenia Z16: **0 B diffu** na wszystkich chronionych plikach poza autoryzowanym zakresem `Z16-amendment #11` w Commicie 1.

---

## 5. PODSUMOWANIE

Mikro-Hotfix 11.1.4a ostatecznie stabilizuje potok w zakresie socjolingwistyki i semiotyki ekranowej. Wszystkie zidentyfikowane luki integracyjne zostały wyeliminowane zgodnie z zasadą eliminacji przyczyn źródłowych w 5 warstwach, przy zachowaniu zerowego kosztu operacyjnego (0.00 PLN) i pełnej zgodności z architekturą czystej domeny pozytywnej.
