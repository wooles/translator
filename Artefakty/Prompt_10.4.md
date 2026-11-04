# PROMPT WYKONAWCZY (STANDARD 10.4) — HOTFIX ELIMINACJI JAPOŃSKIEGO ZAPOŻYCZENIA `seiyū` Z AKTYWNEGO PROMPTU LLM

- **Wersja docelowa:** `10.4`
- **Wersja poprzednia (baseline):** `10.3` (HEAD `9f4df49` — `9f4df49fbeb399e8bed1af979ee8b2ba97f082a4` lub commit dokumentacyjny zamykający audyt 10.3)
- **Baseline przed 10.3:** `51dbe2d` (Standard 10.2)
- **Zakres:** 3 chirurgiczne zamiany `SEIYŪ` / `seiyū` → odpowiednik oparty na kategorii `[AKTOR_GŁOSOWY]` w aktywnej części `rules.py` (linie `2564`, `2573`, `2855`) + 1 test regresyjny `T10.4_1` w `tests/test_profiler.py` + raport `Artefakty/Raport_wdrozenia_10.4.md`.

**Cel:** Domknięcie obserwacji `N-01` (`P1`) z audytu Standardu 10.3 — usunięcie japońskiego zapożyczenia leksykalnego (loanwordu) `seiyū` z aktywnego promptu LLM (warstwa bazowa `FILAR 2` / `R1.8` oraz warstwa dynamiczna `DYN_5`) i zastąpienie go polskim terminem metajęzykowym (`aktor głosowy` / `aktora`), zgodnie z Zasadą 4 (`Instance-Free Metalinguistic Architecture`).

**Uwaga o N-05:** Niniejszy hotfix **NIE** adresuje obserwacji `N-05` (wewnętrzne wzorce regex w `get_focused_rules_for_batch`). Obserwacja `N-05` została przeklasyfikowana z `P1` na `P2` i przeniesiona do backlogu `11.0` (zob. `PROJECT_MEMORY.md` §Backlog 11.0).

---

## FAZA 0 — CZYTANIE KODU I WERYFIKACJA STANU (OBOWIĄZKOWA PRZED EDYCJĄ)

Przed wykonaniem jakiejkolwiek edycji uruchom poniższe 3 komendy diagnostyczne i wklej ich surowe wyjścia w Sekcji 0 raportu wdrożenia (`Artefakty/Raport_wdrozenia_10.4.md`):

```bash
# 1. Wszystkie wystąpienia seiyū / SEIYŪ w rules.py (przed edycją: 6 w liniach 25-2524 oraz 3 w liniach 2525+)
grep -n "seiyū\|seiyu\|SEIYŪ" rules.py

# 2. Wystąpienia wyłącznie w aktywnej części rules.py (od linii 2525 do końca pliku — przed edycją: 3 trafienia)
sed -n '2525,$p' rules.py | grep -inE "seiy[uū]"

# 3. Sprawdzenie braku testu T10.4_1 przed wdrożeniem (powinno zwrócić 0 trafień)
grep -n "def test_t10_4_1" tests/test_profiler.py
```

---

## SEKCJA 1 — OPERACJE IMPLEMENTACYJNE (2B.1 – 2B.4)

### Operacja 2B.1 — Zamiana nagłówka `FILAR 2` w `STANDARD_9_CORE_RULES_PROMPT` (`rules.py`)

- **Lokalizacja:** `rules.py`, linia `2564` (wewnątrz `STANDARD_9_CORE_RULES_PROMPT`).
- **Przed:**

```text
[FILAR 2 — ZWIĘZŁOŚĆ AVT, RYTM SEIYŪ I PARALINGWISTYKA (P1)]
```

- **Po:**

```text
[FILAR 2 — ZWIĘZŁOŚĆ AVT, RYTM AKTORA GŁOSOWEGO I PARALINGWISTYKA (P1)]
```

- **Wymóg:** Zachowaj numer filaru, myślnik, priorytet (P1) i pozostałą część nagłówka bez zmian.

### Operacja 2B.2 — Zamiana w regule `R1.8` w `STANDARD_9_CORE_RULES_PROMPT` (`rules.py`)

- **Lokalizacja:** `rules.py`, linia `2573` (wewnątrz `STANDARD_9_CORE_RULES_PROMPT`).
- **Przed:**

```text
R1.8. Synchronizacja z Rytmem Wypowiedzi (Mouth-Pacing): Dopasuj liczbę sylab i rytm frazy do czasu trwania głosu seiyū oraz tempa mówienia postaci.
```

- **Po:**

```text
R1.8. Synchronizacja z Rytmem Wypowiedzi (Mouth-Pacing): Dopasuj liczbę sylab i rytm frazy do czasu trwania głosu aktora oraz tempa mówienia postaci.
```

- **Wymóg:** Zachowaj prefiks `R1.8. Synchronizacja z Rytmem Wypowiedzi (Mouth-Pacing):` bez zmian (wymagane przez `verify_12_fixes.py` i `verify_ultimate_pipeline.py`).

### Operacja 2B.3 — Zamiana w kategorii dynamicznej `DYN_5` w `get_focused_rules_for_batch` (`rules.py`)

- **Lokalizacja:** `rules.py`, linia `2855` (wewnątrz `get_focused_rules_for_batch`, blok `DYN_5` o `score = 82`).
- **Przed:**

```python
            "Aktorstwo i fizjologia emocji seiyū mają prymat nad dosłownością leksykalną. W scenach walki, zadyszki i szlochu "
```

- **Po:**

```python
            "Aktorstwo i fizjologia emocji aktora głosowego mają prymat nad dosłownością leksykalną. W scenach walki, zadyszki i szlochu "
```

- **Wymóg:** Zachowaj priorytet `82`, nagłówek `• [SKUP SIĘ NA: FILAR CLXXII, LXVI, LXXV, XVIII, XXXIII, XVI & XVII - Dynamiczny Prymat Afektu, Prozodia Oddechu i Somatyka]:` oraz pozostałe zdania `DYN_5` bez zmian.

### Operacja 2B.4 — Dodanie testu regresyjnego `T10.4_1` w `tests/test_profiler.py`

- **Lokalizacja:** `tests/test_profiler.py` (na końcu pliku, po `test_t10_3_4_r17_contains_polish_norm_14_15_and_cap_17`).
- **Kod testu do dodania:**

```python
@pytest.mark.unit
def test_t10_4_1_no_seiyu_in_active_runtime():
    """
    Weryfikuje, że w aktywnym runtime (STANDARD_9_CORE_RULES_PROMPT
    oraz wszystkie 9 kategorii get_focused_rules_for_batch) nie występuje
    japoński loanword `seiyū` / `seiyu` (niezależnie od wielkości liter).
    Zgodnie z Zasadą 4 (Instance-Free) — termin zastąpiony polskim `aktor głosowy` / `aktora`.
    """
    seiyu_pat = re.compile(r"\bseiy[uū]\b", re.IGNORECASE)
    assert not seiyu_pat.search(STANDARD_9_CORE_RULES_PROMPT), (
        "Wykryto 'seiyū'/'SEIYŪ' w STANDARD_9_CORE_RULES_PROMPT (powinno być 'aktor głosowy'/'aktora')"
    )
    assert "RYTM AKTORA GŁOSOWEGO" in STANDARD_9_CORE_RULES_PROMPT
    assert "czasu trwania głosu aktora" in STANDARD_9_CORE_RULES_PROMPT

    test_inputs = [
        ([{"text": "You ain't runnin' away, y'all!"}], ""),
        ([{"text": "Forgive me, milord, Your Majesty."}], ""),
        ([{"text": "The little boy and the old grandma are waiting with the girls."}], "kanojo-tachi"),
        ([{"text": "Thank you-san, my master."}], ""),
        ([{"text": "Attack! Dodge! Scream! Sob! Terrified! Ugh! Ottotto!"}], ""),
        ([{"text": "Wait, wait, wait! Listen to me!"}], ""),
        ([{"text": "Tears of sorrow and loneliness after our farewell."}], "namida"),
        ([{"text": "The tactical commander ordered a medical autopsy and diagnosis."}], ""),
        ([{"text": "That's a hilarious double meaning pun!"}], ""),
    ]
    for batch, jp_txt in test_inputs:
        out = get_focused_rules_for_batch(batch, max_rules=10, whisper_text_jp=jp_txt)
        assert out != ""
        assert not seiyu_pat.search(out), (
            f"Wykryto 'seiyū' w wyjściu get_focused_rules_for_batch: {out!r}"
        )
```

---

## SEKCJA 2 — WALIDACJA TESTOWA I BRAMKI CI/CD

Po wdrożeniu operacji `2B.1–2B.4` uruchom pełną walidację:

### 2.1. Weryfikacja braku `seiyū` w aktywnym `rules.py` (2525+) oraz nienaruszalności archiwum Z16 (1–2524)

```bash
sed -n '2525,$p' rules.py | grep -inE "seiy[uū]" | wc -l   # oczekiwane: 0
sed -n '1,2524p' rules.py | grep -inE "seiy[uū]" | wc -l   # oczekiwane: 6 (Z16-locked)
```

### 2.2. Suity pytest

- `pytest tests/test_profiler.py -q` → `19 passed` (poprzednio `18`, `+1` nowy test `T10.4_1`)
- `pytest tests/ -q` → `258 passed` (poprzednio `257`, `+1`)
- `pytest -q` → `329 passed, 153 deselected` (poprzednio `328`, `+1`)
- `pytest -m slow -q` → `153 passed`
- `pytest -m network -q` → `12 passed`

### 2.3. 4 bramki weryfikacyjne CI/CD

- `python verify_purity.py` → `12/12 PASS`
- `python verify_8_fixes.py` → `12/12 PASS`
- `python verify_12_fixes.py` → `15/15 PASS`
- `python verify_ultimate_pipeline.py` → `4/4 PASS`

### 2.4. Asercja ochrony Z16

```bash
git diff 9f4df49..HEAD -- test_system.py tests/archive/ avt_linter.py pytest.ini
```

Wyjście musi być **całkowicie puste** (`0` zmienionych linii).

---

## SEKCJA 3 — WARUNKI UKOŃCZENIA (a)–(i)

- **(a)** Wykonano komendy diagnostyczne z Fazy 0, a ich surowe wyjścia wklejono w Sekcji 0 raportu wdrożenia.
- **(b)** Wdrożono 3 zamiany `SEIYŪ` / `seiyū` → `AKTORA GŁOSOWEGO` / `aktora` / `aktora głosowego` (`2B.1`, `2B.2`, `2B.3`).
- **(c)** Dodano test regresyjny `T10.4_1` (`test_t10_4_1_no_seiyu_in_active_runtime`) w `tests/test_profiler.py` (`2B.4`).
- **(d)** `sed -n '2525,$p' rules.py | grep -inE "seiy[uū]"` zwraca `0` trafień, a w pasywnym `TRANSLATION_RULES_PROMPT` (`1–2524`) pozostaje dokładnie `6` nienaruszonych wystąpień (Z16-locked).
- **(e)** `pytest tests/ -q` → `258 passed, 0 failed`.
- **(f)** `pytest -q` → `329 passed, 153 deselected, 0 failed` (oraz `153 passed` w `-m slow` i `12 passed` w `-m network`).
- **(g)** Wszystkie 4 bramki CI/CD (`verify_purity.py`, `verify_8_fixes.py`, `verify_12_fixes.py`, `verify_ultimate_pipeline.py`) zwracają `PASS`.
- **(h)** Zasada 16 nienaruszona (`git diff` na `test_system.py`, `tests/archive/`, `avt_linter.py`, `pytest.ini` oraz liniach `1–2524` w `rules.py` jest pusty).
- **(i)** Zapisano `Artefakty/Raport_wdrozenia_10.4.md`, `git status` jest czysty (`nothing to commit, working tree clean`), zmiany wypchnięto w **1 commicie** z komunikatem: `fix(pipeline): Hotfix 10.4 - eliminate seiyu Japanese loanword from active runtime`.

---

## SEKCJA 4 — ZAKAZY

1. **ZAKAZ 1 (Z16):** Nie modyfikuj `test_system.py`, `tests/archive/`, 3 gałęzi `# DEFENSIVE_FALLBACK` w `avt_linter.py` ani `pytest.ini`.
2. **ZAKAZ 2 (Z16-locked `TRANSLATION_RULES_PROMPT`):** Nie modyfikuj pasywnej stałej `TRANSLATION_RULES_PROMPT` (linie `25–2524` w `rules.py`) — 6 wystąpień `seiyū` w martwym archiwum musi pozostać nietkniętych.
3. **ZAKAZ 3 (Pominięcie N-05):** Nie modyfikuj żadnych wzorców regex (`en_slang_pat`, `jp_dialect_pat`, `archaic_pat`, `honorific_pat`, `age_gender_pat`, `combat_affect_pat`, `lyric_high_pat`, `lyric_support_pat`, `culture_signs_pat`) w `get_focused_rules_for_batch` — obserwacja `N-05` należy do backlogu `11.0`.
4. **ZAKAZ 4 (Z1/Z2/Z4):** W nowych sformułowaniach używaj wyłącznie pozytywnych polskich kategorii metajęzykowych (bez słów z czarnej listy `T10.2_3` / `T10.3_3`).
5. **ZAKAZ 5 (Wąski zakres):** Nie rozszerzaj zakresu poza 4 operacje (`2B.1–2B.4`) oraz raport `Artefakty/Raport_wdrozenia_10.4.md`. Dotknij wyłącznie 2 plików kodu (`rules.py`, `tests/test_profiler.py`) i 1 pliku raportu.
6. **ZAKAZ 6 (Higiena Git):** Jeden czysty commit wdrożeniowy na `main`, `0` plików śmieciowych, `git status` clean.

---

## SEKCJA 5 — KNOWN RISKS

1. **`R1` (`verify_12_fixes.py` / `verify_ultimate_pipeline.py`):** Skrypty te weryfikują obecność prefiksu `R1.8. Synchronizacja z Rytmem Wypowiedzi (Mouth-Pacing):` oraz nagłówków `[FILAR 1..4]`. Zachowaj dokładny prefiks `R1.8.` oraz strukturę nawiasów `[FILAR 2 — ... (P1)]`.
2. **`R2` (Inwariant rozmiaru i czystości `T10.2_3` oraz `T10.3_3` w `tests/test_profiler.py`):** Zamiana `SEIYŪ`/`seiyū` na `AKTORA GŁOSOWEGO`/`aktora` zwiększa rozmiar `STANDARD_9_CORE_RULES_PROMPT` o 12 znaków (`4064 -> 4076`), co bezpiecznie mieści się poniżej twardego limitu `< 4200` znaków w `T10.3_3`. Nowe słowa (`aktora`, `głosowego`) nie kolidują z listą słów zakazanych `forbidden_neg`.
3. **`R3` (Pasywne archiwum `TRANSLATION_RULES_PROMPT`):** Przypadkowe użycie globalnego `replace_all("seiyū", ...)` w całym pliku `rules.py` zmodyfikowałoby 6 wystąpień w liniach `25–2524`, naruszając ZAKAZ 2. Wykonuj zamiany wyłącznie w liniach `2564`, `2573` i `2855`.

---

## SEKCJA 6 — SZABLON RAPORTU WDROŻENIA (`Artefakty/Raport_wdrozenia_10.4.md`)

Zapisz raport w pliku `Artefakty/Raport_wdrozenia_10.4.md` według poniższej struktury:

1. **Diagnostyka wstępna (FAZA 0):** surowe wyjścia 3 komend przed edycją.
2. **Metadane git:** hash commita bazowego, hash commita 10.4, `git status`, `git diff --stat`.
3. **Tabela realizacji operacji (`2B.1 – 2B.4`):** status i numery linii.
4. **Cytaty kodu po naprawie:** dokładne linie `2564`, `2573`, `2855` z `rules.py` oraz `test_t10_4_1_no_seiyu_in_active_runtime` z `tests/test_profiler.py`.
5. **Wyniki 4 bramek CI/CD:** surowe wyjścia `verify_purity.py`, `verify_8_fixes.py`, `verify_12_fixes.py`, `verify_ultimate_pipeline.py`.
6. **Wyniki pytest oraz weryfikacja Z16:** surowe wyjścia `pytest` oraz pusty `git diff` dla plików chronionych Z16.
7. **Checklista ukończenia (a)–(i).**
8. **Werdykt końcowy:** `PASS`.

---

## FAZA 5 — KOMENDY COMMITU DOKUMENTACYJNEGO

Po zapisaniu powyższych 4 plików dokumentacyjnych w lokalnym klonie repozytorium wykonaj poniższą sekwencję w terminalu, aby sfinalizować commit dokumentacyjny przed uruchomieniem agenta kodującego na `Prompt_10.4.md`:

```bash
git add Artefakty/Raport_audytu_czystosci_i_rzetelnosci_filarow.md
git add Artefakty/Raport_audytu_czystosci_i_rzetelnosci_filarow_SUPLEMENT.md
git add Artefakty/Raport_wdrozenia_10.3.md
git add PROJECT_MEMORY.md
git add Artefakty/Prompt_10.4.md
git commit -m "docs: Zamknięcie audytu 10.3 — reklasyfikacja N-05 (P1→P2), dokumentacja rozszerzenia zakresu, przygotowanie Prompt_10.4"
git push origin main
```

---

## FAZA ODBIORU

- [x] FAZA 0 — Weryfikacja HEAD: `9f4df49` (`9f4df49fbeb399e8bed1af979ee8b2ba97f082a4`), `seiyū` w `rules.py`: `Y` (linie `2564`, `2573`, `2855` w aktywnym runtime + 6 w pasywnym Z16), `N-05`: `Y` (wewnętrzne regexy `DYN_1–5`, `8–9`), `PROJECT_MEMORY.md`: istnieje
- [x] FAZA 1 — Raport audytu (`Artefakty/Raport_audytu_czystosci_i_rzetelnosci_filarow.md`) zaktualizowany: `N-01 → P1`, `N-05 → P2`, werdykt `PASS_Z_DROBNYMI`
- [x] FAZA 2 — `Artefakty/Raport_wdrozenia_10.3.md` uzupełniony o sekcję `## 8. ROZSZERZENIE ZAKRESU PRZEZ IMPLEMENTERA 10.3 (ODNOTOWANE PO AUDYCIE)`
- [x] FAZA 3 — `PROJECT_MEMORY.md` uzupełniony o wpis `N-05` (`## Backlog 11.0 — N-05: Oczyszczenie regexów w get_focused_rules_for_batch z japońskich tokenów leksykalnych`)
- [x] FAZA 4 — `Artefakty/Prompt_10.4.md` utworzony i ulepszony technicznie: 4 operacje (`2B.1–2B.4`), 6 sekcji, 6 zakazów, 3 known risks, case-insensitive regex `r"\bseiy[uū]\b"` dla `SEIYŪ`/`seiyū` na wszystkich 9 kategoriach `DYN_1–DYN_9`
- [x] FAZA 5 — Przygotowano kompletną sekwencję commita dokumentacyjnego (`docs: Zamknięcie audytu 10.3...`)
- [x] Nie zmodyfikowano kodu produkcyjnego (`rules.py`, `tests/*.py`, `profiler.py`, etc. — bez zmian)
- [x] Nie uruchomiono testów
- [x] Z16 nienaruszone
- [x] Z1/Z2/Z3/Z4 w pełni respektowane w `Prompt_10.4.md`