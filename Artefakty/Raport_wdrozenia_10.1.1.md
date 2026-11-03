# RAPORT WDROŻENIA REWIZJI STANDARD 10.1.1 (HOTFIX 10.1.1)
## ELIMINACJA FAŁSZYWEGO MONOLOGU WEWNĘTRZNEGO (P1) I ZANIKU GWARY W DIALOGACH (P2)

---

## 0. STATUS WDROŻENIA I METRYKI KOŃCOWE

| Metryka | Wartość | Status |
|---|---|---|
| **Wersja docelowa** | Standard 10.1.1 (Hotfix 10.1.1) | **PEŁNA ZGODNOŚĆ** |
| **Commit bazowy (v10.1-certified)** | `01f9f3b` (`01f9f3ba92d3c907cf9f14068595fe62b08fa111`) | **ZWERYFIKOWANY** |
| **Status wdrożenia** | 6 operacji silnika (`2B.1`–`2B.6`) + 4 nowe testy jednostkowe (`T10.1.1_P1a`, `T10.1.1_P1b`, `T10.1.1_P2a`, `T10.1.1_P2b`) | **100% WDROŻONE** |
| **Pakiet szybkich testów (`pytest -q`)** | 319 passed, 153 deselected | **100% PASS (Zero Regression)** |
| **Pakiet testów jednostkowych (`pytest tests/ -q`)** | 248 passed (w tym T10.1.1_P1a, T10.1.1_P1b, T10.1.1_P2a, T10.1.1_P2b) | **100% PASS** |
| **Bramka 1: `verify_purity.py`** | 12/12 testów AST/metajęzyka | **PASS** |
| **Bramka 2: `verify_12_fixes.py`** | 12/12 punktów architektonicznych | **PASS** |
| **Bramka 3: `verify_ultimate_pipeline.py`** | 15/15 bramek runtime | **PASS** |
| **Bramka 4: `audit_diff.ps1`** | 4/4 bramek forensic diff | **VICTORY CONFIRMED** |
| **Zasada 16 (Z16 Lock)** | `test_system.py`, `tests/archive/`, `# DEFENSIVE_FALLBACK` | **100% NIENARUSZONE** |
| **Zasady Standardu 9.0 (Z1, Z2, Z3, Z4)** | Zero-Literal, Pure Positive Domain, Primary LLM Authority, Instance-Free | **100% ZACHOWANE** |

---

## 1. TABELA OPERACJI NAPRAWCZYCH (2B.1 – 2B.6)

| Operacja | Moduł / Plik | Defekt / Przyczyna źródłowa | Zastosowana operacja naprawcza | Status |
|---|---|---|---|---|
| **2B.1** | `prosody_engine.py` | Etykieta `"cichy szept / monolog wewnętrzny"` w analizie RMS powodowała fałszywe klasyfikowanie cichych wypowiedzi jako myśli. | Zastąpienie etykiety czystą deskrypcją akustyczną `"cichy głos / obniżona energia głosu (szept lub spokojna replika)"`. Dodanie metody `@staticmethod def _classify_rms_label(rms_val: float, median_rms: float) -> str` oraz aktywne wywołanie w pętli zdarzeń. `grep -c "monolog wewnętrzny"` = 0. | **ZREALIZOWANE** |
| **2B.2** | `translator.py` | Brak rozróżnienia krótkich replik dialogowych od myśli w Phase 1 (`format_phase1_candidate_text`, `build_phase1_prompt`, `_process_single_batch`). | Wdrożenie `is_short_spoken_reply(text, prev_text, same_speaker_neighbor_unitalicized)`. Zabezpieczenie przed wymuszaniem `is_internal_monologue = True` na krótkich replikach, liniach z ustalonym adresatem lub o stylu mówionym (`Default`, `Normal`) bez nawiasów myśli. | **ZREALIZOWANE** |
| **2B.3** | `verifier.py` | `_guard_phase2_regressions` oraz pętla weryfikatora w `verify_batch` wymuszały ponowne doklejenie kursywy `{\i1}...{\i0}`, gdy Faza 1 miała fałszywą kursywę. | Wdrożenie `_has_contiguous_non_italic_neighbor(pass1_items, idx)`. Wykrycie `is_f1_false_italic`: jeśli Faza 1 miała kursywę, ale `source_en` jej nie ma, styl ASS to nie monolog i linia ma sąsiada bez kursywy, weryfikator Phase 2 nie dokleja kursywy i zachowuje czysty tekst mówiony. | **ZREALIZOWANE** |
| **2B.4** | `rules.py` | `get_focused_rules_for_batch` nigdy nie wybierał `FILAR XIII` (brak triggerów slangu/gwary), a reguły wygładzające (`FILAR LXXI` i `FILAR CLXXII`) neutralizowały gwarę. | Dodanie triggerów `en_slang_pat`, `jp_dialect_pat`, `paraphrase_pat` w `get_focused_rules_for_batch`. Dołączenie w 100% pozytywnej treści `FILAR XIII`. Wdrożenie filtru przeciw-wygładzającego (Anti-Smoothing Filter) usuwającego `FILAR LXXI ` i `FILAR CLXXII `, gdy `FILAR XIII` jest aktywny. Zachowanie domyślnego `max_rules: Optional[int] = None`. | **ZREALIZOWANE** |
| **2B.5** | `profiler.py` | Brak pozytywnej wskazówki rejestru gwarowego w `format_lean_episode_brief` dla postaci posługujących się dialektem. | Dodanie opcjonalnego pola `audio_transcription` w `CharacterDossier` oraz parametru `character_audio_transcriptions` w `format_lean_episode_brief`. Przy wykryciu cech dialektalnych (`RE_JP_DIALECT_MARKERS` lub pole stylu/dossier) generowanie: `Rejestr: wyrazista gwara / stylizacja środowiskowa`. | **ZREALIZOWANE** |
| **2B.6** | `verifier.py` & `translator.py` | Phase 2 weryfikatora nie otrzymywał dyrektywy kontrastu rejestrów przy scenach parafrazy gwary. | W `verifier.py:verify_batch` wstrzyknięcie sekcji `• [PARAFRAZA GWARY: Gdy postać A mówi gwarą/slangiem, a postać B tłumaczy lub parafrazuje jej słowa reszcie grupy, zachowaj wyrazisty kontrast stylistyczny — postać A ma brzmieć szorstko i potocznie, a postać B gładko w polszczyźnie ogólnej]`, gdy `focused_rules_str` zawiera `FILAR XIII`. W `translator.py` jawne przekazywanie `focused_rules_str=phase2_focused_rules`. | **ZREALIZOWANE** |

---

## 2. DIAGNOSTYKA FAZY 0 (ODPOWIEDZI NA PYTANIA F0.1 – F0.6)

- **F0.1 (`prosody_engine.py`): W których liniach `prosody_engine.py` występował ciąg `"monolog wewnętrzny"` i jak został zastąpiony?**
  - **Odpowiedź:** Ciąg występował wyłącznie w linii 152: `tags.append("cichy szept / monolog wewnętrzny")`. Został zastąpiony przez deskrypcję: `tags.append(low_energy_lbl or "cichy głos / obniżona energia głosu (szept lub spokojna replika)")` zintegrowaną z nową metodą statyczną `AudioProsodyEngine._classify_rms_label(rms_val, median_rms)`. Aktualny wynik `grep -c "monolog wewnętrzny" prosody_engine.py` wynosi dokładnie `0`.

- **F0.2 (`verifier.py`): Gdzie w `verifier.py` znajdował się mechanizm wymuszania kursywy z Fazy 1 i dlaczego korygował poprawne dialogi Fazy 2?**
  - **Odpowiedź:** Mechanizm znajdował się w liniach 1068–1071 (dawna numeracja przed dodaniem helpera):
    ```python
    is_monologue_it = bool(orig_it.get("is_internal_monologue") or has_im_style or _is_whole_line_italic(src_en) or _is_whole_line_italic(f1_text))
    if is_monologue_it and not _is_whole_line_italic(r.refined_pl):
        r.refined_pl = r"{\i1}" + r.refined_pl + ...
    ```
    Warunek `_is_whole_line_italic(f1_text)` traktował błędnie nałożoną w Fazie 1 kursywę jako dowód monologu i bezwarunkowo doklejał znaczniki `{\i1}...{\i0}` do czystego tekstu dialogowego zwróconego przez model Phase 2. Podobnie w linii 1098 flaga `is_monologue_guard` otrzymywała wartość `True`, paraliżując działanie KATEGORII 20 w `_guard_phase2_regressions`.

- **F0.3 (`rules.py`): Dlaczego `FILAR XIII` nie był wybierany w `get_focused_rules_for_batch` i jak to naprawiono?**
  - **Odpowiedź:** W `rules.py` `FILAR XIII` był zdefiniowany w bloku ogólnym (linie 150–159), ale w dyspozytorze `get_focused_rules_for_batch` nie istniał żaden blok regułowy ani warunek dopasowujący slang angielski lub dialekty japońskie dla Filaru XIII. Dodano dedykowany blok triggerów sprawdzający wzorce `en_slang_pat`, `jp_dialect_pat` oraz `paraphrase_pat`, dodający `FILAR XIII` z wagą `TIER_ACTIVE_CRAFT + 5` (score 85).

- **F0.4 (`verifier.py`): Czy sygnatura `verify_batch` przyjmowała `focused_rules_str` i jak zareagowano na obecność Filaru XIII?**
  - **Odpowiedź:** Sygnatura `verify_batch` w `verifier.py:630` przyjmowała `focused_rules_str: str = ""`, lecz prompt ograniczał się do dołączenia tekstu. Dodano dedykowaną logikę sprawdzającą obecność `"FILAR XIII"` lub słów kluczowych `"gwara"`, `"dialekt"`, `"slang"`, która wstrzykuje wytyczną redakcyjną:
    `"• [PARAFRAZA GWARY: Gdy postać A mówi gwarą/slangiem, a postać B tłumaczy lub parafrazuje jej słowa reszcie grupy, zachowaj wyrazisty kontrast stylistyczny — postać A ma brzmieć szorstko i potocznie, a postać B gładko w polszczyźnie ogólnej]."`

- **F0.5 (`rules.py`): Jak zagwarantowano czystość metajęzykową (Pure Positive Domain) dla Filaru XIII?**
  - **Odpowiedź:** Treść wstrzykiwanej reguły została zredagowana zgodnie z żelaznymi regułami Standardu 9.0:
    `"• [SKUP SIĘ NA: FILAR XIII - Dialekty Regionalne, Gwara i Kontrast Rejestrów]: Kwestie postaci posługującej się w oryginale gwarą, slangiem lub dialektem regionalnym oddawaj poprzez wyrazistą, szorstką polszczyznę potoczną i składnię środowiskową. W scenach, w których kolejna postać parafrazuje i wyjaśnia te słowa reszcie grupy w języku ogólnym, utrzymuj wyraźny kontrast stylistyczny pomiędzy surowym idiolektem mówcy a gładką polszczyzną tłumacza wewnątrzscenicznego."`
    Tekst jest w 100% wolny od skrótów (`np.`), cudzysłowów (`"..."`), wielkich liter ALL-CAPS w treści oraz słów preskryptywnych/zakazów (`nie`, `zakaz`, `błąd`, `musi`, `zawsze`, `nigdy`, `unikaj`, `zamiast`), co potwierdza czysty werdykt `verify_purity.py`.

- **F0.6 (`rules.py`): W jaki sposób filtr przeciw-wygładzający (Anti-Smoothing Filter) eliminuje konflikt reguł?**
  - **Odpowiedź:** Gdy `FILAR XIII` zostaje zakwalifikowany do zestawu reguł, z listy kandydatów `unique_rules` oraz z `final_rules` bezwzględnie usuwane są Filar LXXI (wygładzanie składni / eliminacja tarcia) oraz Filar CLXXII (eliminacja archaizmów i stylizacji), uniemożliwiając modelowi neutralizację socjolektu do uniwersalnego języka literackiego.

---

## 3. DOWODY WYKONANIA OPERACJI W KODZIE (NUMERY LINII I CYTATY)

### 2B.1: `prosody_engine.py` (L19–27 oraz L138–176)
```python
# prosody_engine.py:19-27
@staticmethod
def _classify_rms_label(rms_val: float, median_rms: float) -> str:
    """
    Klasyfikuje obniżony poziom energii RMS jako cichy głos/szept lub spokojną replikę,
    zabezpieczając przed błędną interpretacją cichej mowy jako monologu wewnętrznego (Hotfix 10.1.1, 2B.1).
    """
    if median_rms > 0 and rms_val < median_rms * 0.45:
        return "cichy głos / obniżona energia głosu (szept lub spokojna replika)"
    return ""

# prosody_engine.py:173-176
tags = []
low_energy_lbl = cls._classify_rms_label(rms, median_rms)
if dbfs < -34.0 or low_energy_lbl:
    tags.append(low_energy_lbl or "cichy głos / obniżona energia głosu (szept lub spokojna replika)")
```

### 2B.2: `translator.py` (L1705–1745, L1760–1767, L3223–3235, L4040–4045, L4394–4400)
```python
# translator.py:1705-1745
def is_short_spoken_reply(text: str, prev_text: str = "", same_speaker_neighbor_unitalicized: bool = False) -> bool:
    """
    Sprawdza, czy linia jest krótką repliką mówioną w dialogu (<= 4 słowa lub typowe potoczne potwierdzenie/negacja/reakcja),
    która NIE powinna być oznaczana jako monolog wewnętrzny tylko ze względu na cichą prozodię (niski RMS).
    """
    if not text:
        return False
    clean_txt = re.sub(r"\{.*?\}", "", text)
    clean_txt = re.sub(r"\\[nN]|\r?\n", " ", clean_txt).strip()
    if (clean_txt.startswith("(") and clean_txt.endswith(")")) or (clean_txt.startswith("（") and clean_txt.endswith("）")):
        return False

    words = re.findall(r"\b[A-Za-z0-9ąćęłńóśźżĄĆĘŁŃÓŚŹŻ'-]+\b", clean_txt)
    word_count = len(words)
    ...
```

### 2B.3: `verifier.py` (L63–105 oraz L1115–1135)
```python
# verifier.py:63-105
def _has_contiguous_non_italic_neighbor(pass1_items: List[Dict[str, Any]], idx: int) -> bool:
    """
    Sprawdza, czy linia o indeksie idx w paczce pass1_items sąsiaduje z nienaruszoną kwestią
    dialogową bez kursywy (tego samego mówcy lub w tej samej turze dialogowej).
    Chroni przed fałszywym monologiem wewnętrznym na krótkich replikach (Hotfix 10.1.1, 2B.3).
    """
    ...

# verifier.py:1115-1135
orig_idx_in_batch = next((i for i, b_it in enumerate(batch_items) if b_it.get("id") == r.id), -1)
has_non_italic_neighbor = _has_contiguous_non_italic_neighbor(batch_items, orig_idx_in_batch)
is_f1_false_italic = (
    _is_whole_line_italic(f1_text)
    and not _is_whole_line_italic(src_en)
    and not has_im_style
    and has_non_italic_neighbor
)
is_monologue_it = bool(
    orig_it.get("is_internal_monologue")
    or has_im_style
    or _is_whole_line_italic(src_en)
    or (_is_whole_line_italic(f1_text) and not is_f1_false_italic)
)
if is_f1_false_italic and not _is_whole_line_italic(r.refined_pl):
    pass
elif is_monologue_it and not _is_whole_line_italic(r.refined_pl):
    if not r.refined_pl.startswith(r"{\i1}"):
        r.refined_pl = r"{\i1}" + r.refined_pl + (r"{\i0}" if not r.refined_pl.endswith(r"{\i0}") else "")
```

### 2B.4: `rules.py` (L2508–2514, L2570–2595, L3945–3955, L4005–4012)
```python
# rules.py:2508-2514
def get_focused_rules_for_batch(
    batch_items_or_text: Any,
    max_rules: Optional[int] = None,
    batch_text_en: Optional[str] = None,
    whisper_text_jp: str = ""
) -> str:

# rules.py:2570-2595
    # Filar XIII - Dialekty Regionalne, Gwara i Kontrast Rejestrów (Hotfix 10.1.1, 2B.4)
    en_slang_pat = re.compile(r"\b(?:gonna|wanna|gotta|ain't|dunno|lemme|gimme|y'all|reckon|howdy|bloody|mate|innit|blimey|lads|folks|fella|heck|darn|ain'tcha|nowise|nohow|shucks)\b", re.IGNORECASE)
    jp_dialect_pat = re.compile(r"\b(?:ya|yan|yade|yaro|nen|seya|akan|honma|dappe|dabe|ora|washi|atai|wai|wagahai|jaken|koraa|suitoo|nankurunaisa|haisai|namara|shibareru|べ|だべ|じゃけん|やん|やで|やろ|ねん|せや|あかん|ほんま|おら|わし|あたい|わい|吾輩)\b", re.IGNORECASE)
    paraphrase_pat = re.compile(r"\b(?:he means|she means|they mean|meaning|what (?:he|she|they) (?:said|meant)|in other words|he's trying to say|she's trying to say|znaczy|ma na myśli|innymi słowy|chodzi mu o|chodzi jej o)\b", re.IGNORECASE)
    ...
    if has_slang_en or has_dialect_jp or has_paraphrase:
        focused_pillars.append(
            (TIER_ACTIVE_CRAFT + 5,
            "• [SKUP SIĘ NA: FILAR XIII - Dialekty Regionalne, Gwara i Kontrast Rejestrów]: Kwestie postaci posługującej się w oryginale gwarą, slangiem lub dialektem regionalnym oddawaj poprzez wyrazistą, szorstką polszczyznę potoczną i składnię środowiskową. W scenach, w których kolejna postać parafrazuje i wyjaśnia te słowa reszcie grupy w języku ogólnym, utrzymuj wyraźny kontrast stylistyczny pomiędzy surowym idiolektem mówcy a gładką polszczyzną tłumacza wewnątrzscenicznego.")
        )

# rules.py:3945-3955 & 4005-4012 (Anti-Smoothing Filter)
    if any("FILAR XIII" in r[1] for r in sorted_scored):
        sorted_scored = [r for r in sorted_scored if "FILAR LXXI " not in r[1] and "FILAR CLXXII " not in r[1]]
    ...
    if any("FILAR XIII" in r for r in final_rules):
        final_rules = [r for r in final_rules if "FILAR LXXI " not in r and "FILAR CLXXII " not in r]
```

### 2B.5: `profiler.py` (L118–125, L253, L299–315, L325–330)
```python
# profiler.py:118-125
class CharacterDossier(BaseModel):
    ...
    audio_transcription: Optional[str] = Field(default="", description="Próbka transkrypcji kwestii postaci w audio seiyū")

RE_JP_DIALECT_MARKERS = re.compile(
    r"\b(?:ya|yan|yade|yaro|nen|seya|akan|honma|dappe|dabe|ora|washi|atai|wai|wagahai|jaken|koraa|suitoo|nankurunaisa|haisai|namara|shibareru)\b|べ|だべ|じゃけん|やん|やで|やろ|ねん|せや|あかん|ほんま|おら|わし|あたい|わい|吾輩",
    re.IGNORECASE
)

# profiler.py:253 & 299-315
def format_lean_episode_brief(profile: Any, character_audio_transcriptions: Optional[Dict[str, str]] = None, **kwargs) -> str:
    ...
    if has_dialect_indicator:
        lines.append("    Rejestr: wyrazista gwara / stylizacja środowiskowa")
```

### 2B.6: `verifier.py` (L746–752)
```python
# verifier.py:746-752
if focused_rules_str:
    prompt_lines.append(f"\n{focused_rules_str}\n")
    if "FILAR XIII" in focused_rules_str or any(k in focused_rules_str.lower() for k in ["gwara", "dialekt", "slang"]):
        prompt_lines.append(
            "• [PARAFRAZA GWARY: Gdy postać A mówi gwarą/slangiem, a postać B tłumaczy lub parafrazuje jej słowa reszcie grupy, zachowaj wyrazisty kontrast stylistyczny — postać A ma brzmieć szorstko i potocznie, a postać B gładko w polszczyźnie ogólnej]."
        )
```

---

## 4. PEŁNE WYNIKI 4 BRAMEK KWALIFIKACYJNYCH CI/CD

### Bramka 1: `verify_purity.py`
```
============================================================================================
🛡️  CERTYFIKACJA ARCHITEKTURY: ZERO-LITERAL & INSTANCE-FREE METALINGUISTIC (STANDARD 9.0)
============================================================================================
[PASS] Czysto                    | Bramka 1: Składnia i integralność AST
[PASS] Czysto                    | Bramka 2: Zakaz instancji (np. [Nazwa])
[PASS] Czysto                    | Bramka 3: Zakaz cytowanych dialogów w regułach
[PASS] Czysto                    | Bramka 4: Zakaz etykiet kontrastowych i '[OK]'
[PASS] Czysto                    | Bramka 5A: Zakaz słów ALL-CAPS w tekście
[PASS] Czysto                    | Bramka 5B: Zakaz preskryptywności i zakazów
[PASS] Czysto                    | Bramka 6: Zakaz alarmów w promptach i kodzie
[PASS] Czysto                    | Bramka 7: Zakaz zahardkodowanych slugów serii
[PASS] Czysto                    | Bramka 8: Zakaz statycznych kolekcji nazw w AST
[PASS] Czysto                    | Bramka 9: Zakaz ręcznych łat odmian (variants.update)
[PASS] Czysto                    | Bramka 10: Czystość kodu DSP/NumPy (brak _np.)
[PASS] Czysto                    | Bramka 11: Wymóg default strict_positive_domain=True

============================================================================================
🏆 WERDYKT: [100% CZYSTY I ZGODNY Z STANDARDEM 9.0 — ZERO INSTANCJI I ZERO ŁAT]
```

### Bramka 2: `verify_12_fixes.py`
```
==============================================================================================
🛡️  RAPORT FORENSYCZNY: WERYFIKACJA 12 PUNKTÓW ARCHITEKTONICZNYCH POTOKU AVT
==============================================================================================
[PASS]   | Punkt 01: Rozdzielenie grup We_Group i You_Group w sygnaturze lintera
         └─ Sygnatura AVTLinter przyjmuje niezależne plural_group_gender i you_group_gender
[PASS]   | Punkt 02: Twarde bramki pewności (confidence >= 0.95) w linterze
         └─ Operatory D_pos wymagają twardego progu confidence >= 0.95
[PASS]   | Punkt 03: Separacja epistemiczna P0 vs P1 dla hipotez Profilera
         └─ Hipotezy tekstowe Profilera mają status P1 (confidence=0.85), nie blokując F0
[PASS]   | Punkt 04: Bezpieczna promocja płci z początku opisu i ochrona diakrytyków
         └─ Promocja z description kotwiczona na początku wyrazu; normalize_actor_tag chroni znaki diakrytyczne
[PASS]   | Punkt 05: Ochrona linii wieloadresatowych (SubTurn Pivot Partitioning)
         └─ Pod-segmenty SubTurn chronione przed kolizją sprzecznych adresatów w pojedynczej linii
[PASS]   | Punkt 06: Bariera granicy klauzuli w CopulaAdj i RolePair_Instrumental
         └─ Orzeczniki łącznikowe odizolowane barierą składniową (nie mutują zdań podrzędnych 3. os.)
[PASS]   | Punkt 07: Kapowanie pewności Lookaheadu w scenach wieloosobowych do 0.85
         └─ Stopień 3 (Lookahead) w scenach wieloosobowych ma limit target_confidence <= 0.85
[PASS]   | Punkt 08: Nieprzełamywalność męskiego F0 <= 135Hz przez zaimki EN (Score_EN)
         └─ Determinizm męski F0 <= 135Hz nie jest przełamywany przez zaimki z tekstu angielskiego
[PASS]   | Punkt 09: Pełna tożsamość w TELEMETRIA i brak preskryptywnego nakazu 'ty'
         └─ Usunięto sztywne 'ty'; wektor telemetrii przekazuje tożsamość mówcy, adresata i rejestr
[PASS]   | Punkt 10: Przekazywanie audio_jp i semantic_anchor do Fazy 2 (DialogueVerifier)
         └─ Faza 2 otrzymuje transkrypcję audio_jp i kotwicę semantyczną seiyū do weryfikacji
[PASS]   | Punkt 11: Brak usuwania słów w Fazie 7 i czysta rekcja PrepDeclension
         └─ Faza 7 wykonuje wyłącznie geometrię i interpunkcję; brak łat leksykalnych w linterze
[PASS]   | Punkt 12: Czystość metajęzykowa dokumentacji i kodu (Standard 9.0)
         └─ Raport w 100% wolny od instancji onomastycznych, kamuflaży i słów preskryptywnych
==============================================================================================
🏆 WERDYKT: [12/12 PASS] WSZYSTKIE PUNKTY ARCHITEKTONICZNE W 100% ZAADRESOWANE!
   Potok AVT jest w pełni stabilny, wolny od wycieków epistemicznych i zgodny ze Standardem 9.0.
```

### Bramka 3: `verify_ultimate_pipeline.py`
```
===============================================================================================
🛡️  OSTATECZNY AUDYTOR POTOKU AVT: 15 BRAMEK RUNTIME I ARCHITEKTURY (STANDARD 9.0)
===============================================================================================
[PASS]   | 1. Immunitet rzeczowników w Narzędniku (-łem) i rozkaźników (-łam)
[PASS]   | 2. Granice słów \b przy przyklejonych tagach ASS i \N
[PASS]   | 3. Czas przyszły złożony (będę + -ł/-ła) i szyk inwersyjny (Gotowy jesteś?)
[PASS]   | 4. Bariera granicy klauzuli w CopulaAdj (ochrona 3. os. po przecinku/że)
[PASS]   | 5. Twarda bramka pewności (confidence 0.85 < 0.95 -> T(x) = x)
[PASS]   | 6. Rozdzielenie We_Group i You_Group (mężczyzna do grupy kobiet -> -łyście)
[PASS]   | 7. Ochrona drugiego mówcy w linii dwugłosowej (- ...\N- ...)
[PASS]   | 8. Ochrona polskich znaków diakrytycznych w normalize_actor_tag
[PASS]   | 9. Paradygmat deklinacji żeńskiej w generate_polish_name_declension
[PASS]   | 10. Separacja P0 vs P1 dla Profilera i brak Score_EN <= -8
[PASS]   | 11. Kapowanie Lookaheadu (0.85) i izolacja Vocative Lock (tylko 2. os.)
[PASS]   | 12. Limit AniList perPage: 50 i blokada tytułów w indeksie aliasów
[PASS]   | 13. Bramka anty-halucynacyjna Whispera i audio_jp w Fazie 2
[PASS]   | 14. Brak sztywnego nakazu ('ty') i pełna telemetria mówcy/adresata
[PASS]   | 15. Czystość metajęzykowa raportu technicznego (Standard 9.0)
===============================================================================================
WYNIK KOŃCOWY: 15/15 PASS
```

### Bramka 4: `audit_diff.ps1`
```
=== FORENSIC DIFF & AST AUDITOR (STANDARD 4.1) ===
[PASS] 1/4 Zero-Cosmetic Gate (zmodyfikowano rdzen silnika: profiler.py, prosody_engine.py, rules.py, translator.py, verifier.py)
[PASS] 2/4 Zero-Onomastic Gate (brak nazw wlasnych na liscie)
[PASS] 3/4 End-to-End Wiring Gate
[PASS] 4/4 Test Integrity Gate
WERDYKT: [VICTORY CONFIRMED -- KOD CZYSTY I UOGOLNIONY]
```

---

## 5. WYNIKI WYKONANIA TESTÓW JEDNOSTKOWYCH

### Pakiet `pytest tests/ -q`
```
============================= test session starts =============================
platform win32 -- Python 3.13.1, pytest-9.1.1, pluggy-1.6.0
rootdir: C:\Users\Piotrek\Desktop\translator
configfile: pytest.ini
plugins: anyio-4.14.2, platformdirs-4.13.0
collected 248 items

........................................................................ [ 29%]
........................................................................ [ 58%]
........................................................................ [ 87%]
................................                                         [100%]

============================ 248 passed in 10.99s =============================
```

### Pakiet `pytest -q` (Pełny pakiet produkcyjny)
```
============================= test session starts =============================
platform win32 -- Python 3.13.1, pytest-9.1.1, pluggy-1.6.0
rootdir: C:\Users\Piotrek\Desktop\translator
configfile: pytest.ini
testpaths: test_system.py, tests
plugins: anyio-4.14.2, platformdirs-4.13.0
collected 472 items / 153 deselected / 319 selected

........................................................................ [ 22%]
........................................................................ [ 45%]
........................................................................ [ 67%]
........................................................................ [ 90%]
...............................                                          [100%]

==================== 319 passed, 153 deselected in 27.02s =====================
```

---

## 6. PODSUMOWANIE ELIMINACJI PRZYCZYN ŹRÓDŁOWYCH W 5 WARSTWACH

- **Warstwa 1 (Akustyka i Profiler):**
  Eliminacja etykiety `"cichy szept / monolog wewnętrzny"` w `prosody_engine.py` i wprowadzenie czystej, obiektywnej deskrypcji akustycznej energii RMS (`_classify_rms_label`). Dodanie pozytywnej deskrypcji idiolektu gwary w `format_lean_episode_brief` na podstawie wykładników `RE_JP_DIALECT_MARKERS`.

- **Warstwa 2 (Stan Świata i Semiotyka):**
  Zawężenie logiki wyznaczania `is_internal_monologue` w `translator.py`. Krótkie repliki mówione (`is_short_spoken_reply`) oraz kwestie w turze dialogowej z ustalonym adresatem nie mogą przyjmować flagi monologu wewnętrznego na podstawie sygnałów akustycznych.

- **Warstwa 3 (Kanon i Kontrakt LLM):**
  Aktywacja `FILAR XIII` w `rules.py:get_focused_rules_for_batch` przy wystąpieniu slangu, gwary lub parafrazy w dialogu. Zabezpieczenie przed spłaszczaniem stylu przez Anti-Smoothing Filter (wykluczenie Filaru LXXI i CLXXII przy aktywacji Filaru XIII). Wstrzyknięcie dyrektywy kontrastu rejestrów parafrazy gwary do promptu Phase 2.

- **Warstwa 4 (Deterministyczna Bramka Jakości):**
  Zabezpieczenie `verifier.py` przed fałszywym powrotem kursywy. Jeśli linia w Fazie 1 miała kursywę, ale `source_en` jej nie ma, styl to nie monolog, a kwestia sąsiaduje z dialogiem mówionym (`_has_contiguous_non_italic_neighbor`), Faza 2 nie dokleja sztucznie tagów `{\i1}...{\i0}` i zachowuje czysty, naturalny tekst.

- **Warstwa 5 (Tarcza Regresyjna CI/CD):**
  Wdrożenie 4 precyzyjnych testów regresyjnych (`T10.1.1_P1a`, `T10.1.1_P1b`, `T10.1.1_P2a`, `T10.1.1_P2b`) sprawdzających zachowanie silnika w warunkach brzegowych. Wszystkie 4 bramki walidacyjne CI/CD zwracają stan `PASS`, a bilans regresji wynosi dokładnie 0.
