# PROMPT WYKONAWCZY (STANDARD 10.6.2) — NAPRAWA STRAŻNIKA REGRESJI FAZY 2 (`_guard_phase2_regressions` W `verifier.py`): ELIMINACJA FABRYKOWANIA WIELOKROPKA INICJALNEGO I UTRATY WIELKIEJ LITERY

- **Wersja docelowa:** `10.6.2`
- **Wersja poprzednia (baseline):** `10.6.1` (musi być już zmergowany i wypchnięty na `origin/main` przed uruchomieniem tego promptu)
- **Baseline Depuracji Legacy 1.0 (Z16):** `474fb64`
- **Podstawa audytowa:** `Artefakty/Raport_audytu_cathy_cathysoul_i_guard_regresji.md` (Defekt B: `FIX-B.1`, `FIX-B.2`)
- **Zakres:** 2 operacje w `verifier.py` (`2B.1`–`2B.2`) + 4 testy regresyjne w `tests/test_verifier.py` (`T10.6.2_1`–`T10.6.2_4`) + raport `Artefakty/Raport_wdrozenia_10.6.2.md`.
- **Kolejność wdrażania:** Prompt 10.6.2 jest **drugim** z dwóch sekwencyjnych hotfixów. Uruchom go **dopiero po zmergowaniu i wypchnięciu 10.6.1**. Nie łącz obu hotfixów w jeden commit.

**Cel:** Naprawa błędu w funkcji `_guard_phase2_regressions` (`verifier.py`), która po każdej linii zakończonej wielokropkiem `"..."` deterministycznie wstrzykiwała na początku kolejnej linii ciąg `"... "` oraz zamieniała pierwszą literę na małą (`lower()`), oznaczając tę fabrykację jako `[Zabezpieczono przed regresją Fazy 2]` — nawet wtedy, gdy ani oryginał angielski (`source_en`), ani szkic Fazy 1 (`f1_text`) nie zaczynały się od wielokropka, gdy zmieniał się mówca, oraz gdy pierwsze słowo było imieniem własnym (`<RZECZYWISTA_REPLIKA_KRÓTKA_1>`).

**Zasady nadrzędne Standardu 9.0 (obowiązujące w 100%):**
- **Z1 (Zero-Literal):** całkowity zakaz umieszczania w kodzie, komentarzach i testach jakichkolwiek nazw własnych z anime. W testach używaj wyłącznie syntetycznych przykładów (`"Alpho?"`, `"Beta Bassett."`, `"Wiesz coś o tym?"`, `"Rozumiem."`, `"Wybacz, Anno."`).
- **Z2 (Pure Positive Domain):** komentarze wyłącznie w formie pozytywnej.
- **Z3 (Primary LLM Authority):** strażnik `_guard_phase2_regressions` może przywrócić wielokropek inicjalny **wyłącznie wtedy, gdy istniał on już w szkicu Fazy 1 (`f1_text`)**, a Faza 2 go usunęła. Strażnikowi nie wolno fabrykować nowego wielokropka inicjalnego, którego nie było w Fazie 1, ani zamieniać wielkiej litery na małą w imionach własnych.
- **Z4 (Instance-Free):** logika oparta wyłącznie na strukturze interpunkcyjnej i kapitalizacji między `source_en`, `f1_text` i `f2_text`.
- **Z16 (Ochrona Depuracji Legacy 1.0):** całkowity zakaz modyfikacji `test_system.py`, `tests/archive/`, 3 gałęzi `# DEFENSIVE_FALLBACK` w `avt_linter.py`, `pytest.ini`, `rules.py` oraz `series_memory/`.

---

## FAZA 0 — CZYTANIE KODU I WERYFIKACJA STANU (OBOWIĄZKOWA PRZED EDYCJĄ)

Przed wykonaniem edycji uruchom poniższe 7 komend diagnostycznych i wklej ich surowe wyjścia w Sekcji 0 raportu `Artefakty/Raport_wdrozenia_10.6.2.md`:

~~~bash
# 1. Weryfikacja HEAD i czystości drzewa (HEAD powinien być commitem 10.6.1)
git log --oneline -n 5
git status

# 2. Inspekcja całej funkcji _guard_phase2_regressions w verifier.py
grep -nA 120 "def _guard_phase2_regressions" verifier.py

# 3. Wyszukanie wszystkich miejsc użycia "[Zabezpieczono przed regresją Fazy 2]" w verifier.py
grep -nC 15 "Zabezpieczono przed regresją Fazy 2" verifier.py

# 4. Inspekcja wywołania _guard_phase2_regressions w verify_batch (verifier.py)
grep -nC 20 "_guard_phase2_regressions(" verifier.py

# 5. Sprawdzenie istniejących testów _guard_phase2_regressions w tests/test_verifier.py
grep -nC 25 "_guard_phase2_regressions" tests/test_verifier.py

# 6. Sygnatura funkcji _guard_phase2_regressions (kluczowe dla testów T10.6.2_*)
grep -nE "def _guard_phase2_regressions" verifier.py

# 7. Dokładne parametry i struktura wejścia _guard_phase2_regressions
grep -nA 30 "def _guard_phase2_regressions" verifier.py | head -40
~~~

### P0.1. Odpowiedzi na pytania flagowe (na podstawie powyższych komend)

- **F0.1:** Hash HEAD = commit 10.6.1 (potwierdź `git log -n 1 --format=%H`).
- **F0.2:** `_guard_phase2_regressions` jest wywoływana wewnątrz `verify_batch` po odebraniu JSON-a Fazy 2. Strażnik modyfikuje `refined_pl` i dopisuje `" [Zabezpieczono przed regresją Fazy 2]"` do `changes_made`.
- **F0.3:** Flaga `[Zabezpieczono...]` jest dodawana **wyłącznie** przez `verifier.py` (przed `translator.py` i `avt_linter.py`).
- **F0.4:** W bloku wielokropka strażnik sprawdza wyłącznie koniec poprzedniej linii w `f2_text`, pomijając warunek `f1_text.lstrip().startswith("...")` oraz sprawdzenie zmiany mówcy.
- **F0.5:** `.lower()` jest wywoływane na pierwszym znaku bez sprawdzenia, czy to imię własne.
- **F0.6 (nowe):** **Sygnatura `_guard_phase2_regressions`** odczytana z Komendy 6. Zapisz ją dosłownie w raporcie (lista parametrów, typy, wartość zwracana). **Kluczowe:** struktura `batch_items` i nazwy pól (np. `prev_f1`, `prev_f2`, `curr_en`, `curr_f1`, `curr_f2` lub `f1_text`, `f2_text`, `source_en`, `prev_text`) — od tego zależy, jak wywołać funkcję w testach `T10.6.2_1` – `T10.6.2_4`. Jeśli funkcja przyjmuje pojedyncze linie zamiast `batch_items`, dostosuj wywołanie w testach (asercje merytoryczne pozostają identyczne).
- **F0.7 (nowe):** Jeśli w `tests/test_verifier.py` istnieje już wcześniejszy test `_guard_phase2_regressions`, zapisz go w raporcie i sprawdź, czy nie testuje starego, błędnego zachowania (`f1_text` bez `...` → guard dopisuje `...`). Jeśli tak — zaktualizuj ten test razem z `T10.6.2_1` (patrz KNOWN RISK `R1`).

---

## SEKCJA 1 — OPERACJE IMPLEMENTACYJNE (`2B.1` – `2B.2` W `verifier.py`)

### Operacja `2B.1` — Warunek konieczny obecności wielokropka inicjalnego w `f1_text` przed jego przywróceniem (`FIX-B.1`)

**Problem:** W `_guard_phase2_regressions` (`verifier.py`) blok odpowiedzialny za ciągłość zdań rozbitych sprawdza, czy poprzednia linia kończy się wielokropkiem (`"..."`), i jeśli tak, wymusza na bieżącej linii `f2_text` prefiks `"... "` oraz małą literę na pierwszym znaku — **nawet wtedy, gdy w `f1_text` (szkicu Fazy 1) bieżąca linia nie miała wielokropka inicjalnego i zaczynała się wielką literą**. Ponieważ w dialogach wielokropek na końcu kwestii najczęściej oznacza urwaną myśl, zawahanie lub pauzę przed wypowiedzią innej postaci, ślepe dopisywanie `"... "` do kolejnej kwestii psuje ~30 linii w każdym odcinku.

**Instrukcja:**
1. Znajdź w `_guard_phase2_regressions` (`verifier.py`) blok sprawdzający kontynuację po wielokropku z poprzedniej linii (miejsce, które dodaje `"... "` i zmniejsza pierwszą literę oraz dopisuje `[Zabezpieczono przed regresją Fazy 2]`).
2. Zmodyfikuj warunek wejścia do tego bloku tak, aby strażnik przywracał wielokropek inicjalny w linii `i` **wyłącznie wtedy, gdy spełnione są łącznie warunki prawdziwej regresji Fazy 2 względem Fazy 1**:
   - Poprzednia linia kończy się wielokropkiem (`...` lub `…`), **ORAZ**
   - **Szkic Fazy 1 (`f1_text` po pominięciu tagów ASS `{...}` i `<i>`) JUŻ zaczynał się od wielokropka (`...` lub `…`)**, a Faza 2 (`f2_text`) ten wielokropek usunęła.
   - Jeśli `f1_text` NIE zaczynał się od wielokropka — strażnikowi **nie wolno** dodawać `...` ani zmniejszać pierwszej litery w `f2_text`.
3. Dodatkowo: jeśli sam model LLM Fazy 2 dodał na początku `f2_text` wielokropek z małą literą (np. `"... słowo"`), podczas gdy **ani `source_en`, ani `f1_text` nie zaczynały się od wielokropka ani małej litery**, a pierwsze słowo w `f1_text` i `source_en` było jednowyrazowym wołaczem/imieniem własnym lub osobnym zdaniem innego mówcy — przywróć czysty brak wielokropka i wielką literę z `f1_text`.

---

### Operacja `2B.2` — Ochrona kapitalizacji imion własnych i formatu wielokropka (`FIX-B.2`)

**Problem:** Gdy `_guard_phase2_regressions` przywraca uzasadniony wielokropek inicjalny (który był obecny w `f1_text`), lub gdy weryfikuje kapitalizację pierwszego słowa:
1. Nie powinien zamieniać wielkiej litery na małą (`lower()`), jeśli w `f1_text` po wielokropku stała wielka litera (np. imię własne, tytuł grzecznościowy lub zaimek `I` w EN tłumaczony na nazwę własną).
2. Jeżeli `f1_text` i `f2_text` są identyczne (brak zmian), do `changes_made` nigdy nie może trafić flaga `[Zabezpieczono przed regresją Fazy 2]`.

**Instrukcja:**
1. W bloku przywracania utraconego wielokropka inicjalnego (gdy `f1_text` zaczynał się od `...`, a `f2_text` go utracił):
   - Sprawdź, czy pierwszy znak słowa po wielokropku w `f1_text` był wielką literą (`isupper()`). Jeśli w `f1_text` po wielokropku była wielka litera (np. imię własne), zachowaj wielką literę w `f2_text`. Zmniejszaj pierwszą literę tylko wtedy, gdy w `f1_text` po wielokropku również była mała litera (`islower()`).
2. Dodaj w `_guard_phase2_regressions` strażnika kapitalizacji tokenu inicjalnego:
   - Jeśli `f1_text` zaczyna się wielką literą (bez `...`), a `f2_text` zaczyna się od `...` + małej litery w tym samym słowie (np. `f1="Alpho?"`, `f2="... alpho?"`), a `source_en` nie zaczyna się od `...` ani małej litery — usuń błędny prefiks `...` i przywróć wielką literę z `f1_text`.

---

## SEKCJA 2 — WALIDACJA TESTOWA (`tests/test_verifier.py`)

Dopisz na końcu `tests/test_verifier.py` **4 testy jednostkowe** (`T10.6.2_1` – `T10.6.2_4`) w 100% zgodne z Zero-Literal.

**UWAGA 1 (sygnatura):** Poniższe ciała testów zakładają, że `_guard_phase2_regressions` przyjmuje `batch_items: list[dict]` z polami `prev_f1`, `prev_f2`, `curr_en`, `curr_f1`, `curr_f2`. **Odczytaj rzeczywistą sygnaturę i strukturę z Fazy 0 (Komendy 2, 6, 7) i dostosuj wywołanie.** Jeśli funkcja przyjmuje pojedyncze argumenty (`f1_text`, `f2_text`, `source_en`, `prev_text`) — wywołuj ją dla każdej pary osobno i porównuj wynik pojedynczej linii.

**UWAGA 2 (Z1):** Wszystkie dane testowe w 100% syntetyczne. `"Wybacz, Anno."` używa polskiego imienia `Anno` (nie anime). Nie używaj żadnych imion z seriali anime.

~~~python
import pytest


@pytest.mark.unit
@pytest.mark.parametrize(
    "prev_f1,prev_f2,curr_en,curr_f1,curr_f2,expected_out",
    [
        # Wariant 1: imię własne na początku, poprzednia linia z wielokropkiem
        ("Ale...", "Ale...", "Alpha?", "Alpho?", "Alpho?", "Alpho?"),
        # Wariant 2: normalne zdanie pytające
        ("Anno...", "Anno...", "Do you know something about this?", "Wiesz coś o tym?", "Wiesz coś o tym?", "Wiesz coś o tym?"),
        # Wariant 3: krótkie potwierdzenie
        ("Nie przyszłyśmy tu razem...", "Nie przyszłyśmy tu razem...", "I see.", "Rozumiem.", "Rozumiem.", "Rozumiem."),
        # Wariant 4: pełne imię i nazwisko
        ("Tak. A pan to...", "Tak. A pan to...?", "Beta Bassett.", "Beta Bassett.", "Beta Bassett.", "Beta Bassett."),
        # Wariant 5: pojedyncze imię
        ("To...", "To...", "Gamma?", "Gamma?", "Gamma?", "Gamma?"),
    ],
)
def test_t10_6_2_1_guard_never_injects_ellipsis_when_f1_has_no_leading_ellipsis(
    prev_f1, prev_f2, curr_en, curr_f1, curr_f2, expected_out
):
    """
    Standard 10.6.2 (FIX-B.1): Weryfikuje, że _guard_phase2_regressions NIE wstrzykuje
    '... ' ani małej litery na początku linii po linii zakończonej '...', jeśli szkic
    Fazy 1 (curr_f1) nie zaczynał się od wielokropka.

    UWAGA: dostosuj wywołanie do rzeczywistej sygnatury z Fazy 0.
    """
    from verifier import _guard_phase2_regressions

    batch_items = [
        {
            "prev_f1": prev_f1,
            "prev_f2": prev_f2,
            "curr_en": curr_en,
            "curr_f1": curr_f1,
            "curr_f2": curr_f2,
        }
    ]
    result = _guard_phase2_regressions(batch_items)
    # UWAGA: dostosuj ekstrakcję wyniku do rzeczywistej struktury zwracanej
    # (może być lista dict, może być dict, może być tuple — sprawdź w Fazie 0)
    out_text = result[0]["curr_f2"] if isinstance(result, list) else result["curr_f2"]
    changes_made = result[0].get("changes_made", "") if isinstance(result, list) else result.get("changes_made", "")
    assert out_text == expected_out
    assert "Zabezpieczono przed regresją Fazy 2" not in changes_made


@pytest.mark.unit
def test_t10_6_2_2_guard_restores_genuine_split_sentence_ellipsis_from_f1():
    """
    Standard 10.6.2 (FIX-B.1): Weryfikuje, że gdy linia 1 kończy się na '...', ORAZ
    linia 2 w f1 ZACZYNAŁA SIĘ od wielokropka i małej litery, a f2 omyłkowo usunęło
    wielokropek — tego typu prawdziwa regresja Fazy 2 jest nadal poprawnie przywracana
    przez strażnika.
    """
    from verifier import _guard_phase2_regressions

    batch_items = [
        {
            "prev_f1": "Dlatego...",
            "prev_f2": "Dlatego...",
            "curr_en": "So I don't need any friends.",
            "curr_f1": "...nie potrzebuję przyjaciół.",
            "curr_f2": "Nie potrzebuję przyjaciół.",  # F2 zgubiło wiodący wielokropek
        }
    ]
    result = _guard_phase2_regressions(batch_items)
    out_text = result[0]["curr_f2"] if isinstance(result, list) else result["curr_f2"]
    assert out_text.startswith("...")
    assert out_text.lower().lstrip(".").lstrip() == "nie potrzebuję przyjaciół."


@pytest.mark.unit
def test_t10_6_2_3_guard_preserves_proper_noun_capitalization_after_ellipsis():
    """
    Standard 10.6.2 (FIX-B.2): Weryfikuje, że nawet gdy f1 zaczyna się od wielokropka
    przed nazwą własną pisaną wielką literą, strażnik nigdy nie zamienia wielkiej
    litery A na małą a.
    """
    from verifier import _guard_phase2_regressions

    batch_items = [
        {
            "prev_f1": "Poczekaj...",
            "prev_f2": "Poczekaj...",
            "curr_en": "Alpho?",
            "curr_f1": "...Alpho?",
            "curr_f2": "Alpho?",  # F2 zgubiło wielokropek, ale zachowało wielką literę
        }
    ]
    result = _guard_phase2_regressions(batch_items)
    out_text = result[0]["curr_f2"] if isinstance(result, list) else result["curr_f2"]
    assert out_text.startswith("...")
    assert "Alpho" in out_text  # wielka litera A ZACHOWANA
    assert "alpho" not in out_text  # mała litera a NIEDOZWOLONA


@pytest.mark.unit
def test_t10_6_2_4_unchanged_line_has_no_regression_guard_flag():
    """
    Standard 10.6.2 (FIX-B.2): Weryfikuje, że gdy f1 == f2, wynik po
    _guard_phase2_regressions zachowuje pusty powód zmiany (changes_made nie zawiera
    '[Zabezpieczono przed regresją Fazy 2]').
    """
    from verifier import _guard_phase2_regressions

    batch_items = [
        {
            "prev_f1": "Wybacz...",
            "prev_f2": "Wybacz...",
            "curr_en": "Sorry, Anna.",
            "curr_f1": "Wybacz, Anno.",
            "curr_f2": "Wybacz, Anno.",
        }
    ]
    result = _guard_phase2_regressions(batch_items)
    out_text = result[0]["curr_f2"] if isinstance(result, list) else result["curr_f2"]
    changes_made = result[0].get("changes_made", "") if isinstance(result, list) else result.get("changes_made", "")
    assert out_text == "Wybacz, Anno."
    assert "Zabezpieczono przed regresją Fazy 2" not in changes_made
~~~

---

## SEKCJA 3 — WALIDACJA BRAMEK CI/CD I Z16

Po wdrożeniu operacji `2B.1`–`2B.2` oraz testów `T10.6.2_1`–`T10.6.2_4` uruchom:

1. **Testy jednostkowe:**
   - `pytest tests/test_verifier.py -q` → wszystkie przechodzą (`+8` nowych przypadków z parametryzacją)
   - `pytest tests/ -q` → `295+ passed, 0 failed`
   - `pytest -q` → `366+ passed, 153 deselected, 0 failed`

2. **4 Bramki CI/CD:**
   - `python verify_purity.py` → `12/12 PASS`
   - `python verify_8_fixes.py` → `8/8 PASS`
   - `python verify_12_fixes.py` → `12/12 PASS`
   - `python verify_ultimate_pipeline.py` → `15/15 PASS`

3. **Weryfikacja Z16 i nienaruszalności `series_memory/` (po 10.6.1):**
   ~~~bash
   git diff <hash_10.6.1_baseline>..HEAD -- test_system.py tests/archive/ avt_linter.py pytest.ini rules.py series_memory/
   # Wyjście musi być w 100% puste (0 B)
   ~~~

---

## SEKCJA 4 — WARUNKI UKOŃCZENIA `(a)`–`(g)`

- **(a)** Wykonano 7 komend diagnostycznych z Fazy 0 i wklejono ich wyjścia w `Artefakty/Raport_wdrozenia_10.6.2.md`.
- **(b)** Wdrożono `2B.1` w `verifier.py` (blokada fabrykowania `...` na początku linii, gdy `f1_text` nie zaczynał się od `...`).
- **(c)** Wdrożono `2B.2` w `verifier.py` (ochrona kapitalizacji nazw własnych i brak fałszywych flag `[Zabezpieczono przed regresją Fazy 2]`).
- **(d)** Dodano testy `T10.6.2_1`–`T10.6.2_4` w `tests/test_verifier.py` (100% Zero-Literal) i wszystkie przechodzą.
- **(e)** Wszystkie istniejące testy w `tests/` oraz 4 bramki CI/CD przechodzą (`0 failed`), Z16 nienaruszone.
- **(f)** Zapisano raport `Artefakty/Raport_wdrozenia_10.6.2.md` (`0` placeholderów).
- **(g)** Wykonano **dokładnie 1 commit** i **1 push** na `origin/main`:
  `fix(verifier): Hotfix 10.6.2 - prevent false-positive ellipsis injection and lowercase corruption in regression guard`

---

## SEKCJA 5 — ZAKAZY I KNOWN RISKS

1. **ZAKAZ 1 (Z16):** Nie modyfikuj `test_system.py`, `tests/archive/`, `avt_linter.py`, `pytest.ini`, `rules.py`, `series_memory/`.
2. **ZAKAZ 2 (Z1 Zero-Literal):** W kodzie `verifier.py`, `tests/test_verifier.py` oraz w raporcie nie używaj żadnych nazw własnych z anime.
3. **ZAKAZ 3 (Wąski zakres):** Modyfikuj wyłącznie `verifier.py`, `tests/test_verifier.py` oraz dodaj `Artefakty/Raport_wdrozenia_10.6.2.md` (i opcjonalnie `Artefakty/Prompt_10.6.2.md`).
4. **ZAKAZ 4 (Brak cofania 10.6.1):** Nie modyfikuj `series_memory.py` ani `tests/test_series_memory.py`. Jeśli 10.6.1 został już zmergowany, jego zmiany są nienaruszalne.
5. **KNOWN RISK `R1`:** Sprawdź w Fazie 0 (Komenda 5), czy w `tests/test_verifier.py` istnieje wcześniej napisany test jednostkowy dla `_guard_phase2_regressions`, który testował doklejanie `...` przy `f1_text` bez `...`. Jeśli taki test istnieje i testował stare, błędne zachowanie — **zaktualizuj dane wejściowe `f1_text` w tym teście**, aby zawierały inicjalne `...` (testując rzeczywistą ochronę przed utratą wielokropka z Fazy 1 w Fazie 2). Zapisz tę aktualizację jawnie w raporcie wdrożenia.
6. **KNOWN RISK `R2`:** Jeżeli `_guard_phase2_regressions` jest wywoływana w innych miejscach niż `verify_batch` (sprawdź Komendą 4), upewnij się, że zmiana warunku nie psuje tych wywołań. W razie wątpliwości zapisz w raporcie listę wszystkich miejsc wywołania.

**Koniec promptu wykonawczego 10.6.2.**