# PROMPT WYKONAWCZY (STANDARD 10.6) — HOTFIX „QUICK WINS”: HIGIENA REPOZYTORIUM, DOMKNIĘCIE CICHYCH WYJĄTKÓW I OPTYMALIZACJA WYWOŁAŃ API

- **Wersja docelowa:** `10.6`
- **Wersja poprzednia (baseline):** `10.5` (HEAD `b2095bb` — `b2095bb5b64abe39c1dd5fbcebfd999d40351b19`, gałąź `main`)
- **Baseline Depuracji Legacy 1.0 (Z16):** `474fb64`
- **Zakres:** 7 operacji naprawczych (`2B.1`–`2B.7`) + 6 testów regresyjnych (`T10.6_1`–`T10.6_6` w `tests/test_hygiene.py`) + raport `Artefakty/Raport_wdrozenia_10.6.md`.

**Cel:** Domknięcie 7 obserwacji `P1` z **pełnego audytu końcowego** `Artefakty/Raport_audytu_koncowego_10_5.md` (commit `b2095bb`):
- **`I-01`:** Aktualizacja dokumentacji `AGENTS.md` / `PROJECT.md` — rzeczywista lista 30 modułów runtime.
- **`I-02`:** Usunięcie zduplikowanego katalogu `Artefakty/_KONTYNUACJA_CZATU/` (10 starych `.py`, 4 bibles, kopia `pytest.ini`, manifest) + duplikat `Artefakty/Hyouken_no_Majutsushi_ga_Sekai_wo_Suberu_S2_bible.json`.
- **`I-05`:** Dodanie brakującego `Artefakty/Prompt_10.5.md` do repozytorium.
- **`I-06`:** Zamiana cichych `except Exception...: pass` → `logger.debug(..., exc_info=True)` w `translator.py`.
- **`I-07`:** Zamiana cichych `except Exception...: pass` → `logger.warning(..., exc_info=True)` w `series_memory.py`.
- **`I-08`:** Zamiana wszystkich gołych `except:` → `except Exception:` w aktywnych plikach `.py` (`avt_linter.py`, `manga_canon.py`, `typesetting_matcher.py`, `extract.py` oraz innych, jeśli wystąpią w Fazie 0).
- **`I-12`:** Warunek `if estimated_tokens < 4096: return None` w `context_cache.py` — eliminacja zbędnego wywołania API `caches.create` kończącego się błędem HTTP 400 dla zwięzłych promptów.

**Uwaga o obserwacjach `P1` NIE objętych 10.6:** Obserwacje `I-03`, `I-04` (napięcia z Z3 w `avt_linter.py`), `I-09` (pin wersji), `I-10` (glosariusz), `I-11` (pary `fansub_lexicons/`), `I-13` (testy modułów pomocniczych), `I-14` (`manga_canon`) oraz wszystkie pozostałe `P2` są świadomie odłożone do **backlogu 11.0** (zob. `PROJECT_MEMORY.md` §Backlog 11.0). Niniejszy hotfix obejmuje **wyłącznie quick wins** — bez zmian ryzykownych funkcjonalnie.

**Zasady nadrzędne Standardu 9.0 (obowiązujące w 100%):**
- **Z1 (Zero-Literal):** całkowity zakaz umieszczania w kodzie, regułach i testach jakichkolwiek nazw własnych z anime.
- **Z2 (Pure Positive Domain):** nowe sformułowania wyłącznie w formie pozytywnej.
- **Z3 (Primary LLM Authority):** żadna z operacji `2B.x` nie dotyka logiki deterministycznych korekt tekstu — wszystkie zmiany są **poza** ścieżką transformacji `phase1_text → phase2_text → dpos_text → ass_text`.
- **Z4 (Instance-Free):** żadna z operacji nie dodaje nowych regexów ani kategorii leksykalnych.
- **Z16 (Ochrona Depuracji Legacy 1.0):** całkowity zakaz modyfikacji `test_system.py`, `tests/archive/`, 3 gałęzi `# DEFENSIVE_FALLBACK` w `avt_linter.py`, `pytest.ini` oraz pasywnej stałej `TRANSLATION_RULES_PROMPT` w `rules.py`.

---

## FAZA 0 — CZYTANIE KODU I WERYFIKACJA STANU (OBOWIĄZKOWA PRZED EDYCJĄ)

Przed wykonaniem jakiejkolwiek edycji uruchom poniższe 9 komend diagnostycznych i wklej ich surowe wyjścia w Sekcji 0 raportu wdrożenia (`Artefakty/Raport_wdrozenia_10.6.md`):

~~~bash
# 1. Weryfikacja HEAD i czystości drzewa
git log --oneline -n 5
git status

# 2. Inwentaryzacja duplikatów w Artefakty/_KONTYNUACJA_CZATU/ oraz Artefakty/
ls -la Artefakty/_KONTYNUACJA_CZATU/ 2>/dev/null || echo "katalog nie istnieje"
find Artefakty/ -name "*.py"
find Artefakty/ -name "*_bible.json"

# 3. Sprawdzenie obecności Artefakty/Prompt_10.5.md
ls -la Artefakty/Prompt_10.5.md 2>/dev/null || echo "brak Prompt_10.5.md"

# 4. Sprawdzenie cichych wyjątków (jedno- i wielolinijkowych) w translator.py
python3 -c 'import re, pathlib; src=pathlib.Path("translator.py").read_text("utf-8"); print([(m.start(), src[:m.start()].count("\n")+1, m.group(0)) for m in re.finditer(r"except\s+Exception(?:\s+as\s+\w+)?\s*:\s*(?:\n\s*)?pass\b", src)])'

# 5. Sprawdzenie cichych wyjątków (jedno- i wielolinijkowych) w series_memory.py
python3 -c 'import re, pathlib; src=pathlib.Path("series_memory.py").read_text("utf-8"); print([(m.start(), src[:m.start()].count("\n")+1, m.group(0)) for m in re.finditer(r"except\s+Exception(?:\s+as\s+\w+)?\s*:\s*(?:\n\s*)?pass\b", src)])'

# 6. Sprawdzenie wszystkich gołych except: w aktywnych plikach .py (poza Artefakty/ i tests/archive/)
grep -rnE "^\s*except\s*:" --include="*.py" . | grep -v "Artefakty/" | grep -v "tests/archive/"

# 7. Sprawdzenie pełnej zawartości context_cache.py
cat context_cache.py

# 8. Sprawdzenie sekcji modułów w AGENTS.md i PROJECT.md
grep -nC 15 -iE "moduł|modules|architektura|translator\.py" AGENTS.md | head -60
grep -nC 15 -iE "moduł|modules|architektura|translator\.py" PROJECT.md | head -60

# 9. Sprawdzenie liczby linii w plikach do modyfikacji oraz sprawdzenie R1-R3 w verify_*.py
wc -l translator.py series_memory.py avt_linter.py manga_canon.py typesetting_matcher.py extract.py context_cache.py AGENTS.md PROJECT.md
grep -rn "Artefakty\|_KONTYNUACJA_CZATU" verify_*.py test_system.py
~~~

### P0.1. Pytania flagowe

- **F0.1:** Jaki jest hash najnowszego commita na `main`? Czy to `b2095bb`, czy nowszy?
- **F0.2:** Czy katalog `Artefakty/_KONTYNUACJA_CZATU/` istnieje? Ile plików `.py` zawiera? Ile `*_bible.json`?
- **F0.3:** Czy `Artefakty/Prompt_10.5.md` istnieje?
- **F0.4:** Ile dokładnie wystąpień `except Exception...: pass` (jedno- lub wielolinijkowych) znajduje się w `translator.py`? W jakich liniach?
- **F0.5:** Ile dokładnie wystąpień `except Exception...: pass` znajduje się w `series_memory.py`? W jakich liniach?
- **F0.6:** Ile dokładnie gołych `except:` w aktywnych plikach `.py` (poza `Artefakty/` i `tests/archive/`)? W których plikach i liniach?
- **F0.7:** Jak wygląda dokładna sygnatura funkcji/metody tworzącej cache w `context_cache.py` i jak wywołuje `caches.create`?
- **F0.8:** Jak obecnie opisana jest lista modułów w `AGENTS.md` i `PROJECT.md`?
- **F0.9:** Czy którykolwiek ze skryptów `verify_*.py` lub `test_system.py` odwołuje się do `Artefakty/_KONTYNUACJA_CZATU/` lub `Artefakty/Hyouken..._bible.json`? (Oczekiwane: NIE).

---

## SEKCJA 1 — OPERACJE IMPLEMENTACYJNE (`2B.1` – `2B.7`)

### Operacja `2B.1` — Usunięcie zduplikowanego katalogu `Artefakty/_KONTYNUACJA_CZATU/` i duplikatu bible (`I-02`)

- **Finding:** `I-02` (P1) z `Raport_audytu_koncowego_10_5.md`.
- **Problem:** W `Artefakty/_KONTYNUACJA_CZATU/` przechowywane są stare kopie plików `.py` (10 sztuk: `translator.py`, `rules.py`, `verifier.py`, `avt_linter.py`, `profiler.py`, `scene_discourse.py`, `series_memory.py`, `main.py`, `metadata.py`, `test_system.py`), kopia `pytest.ini`, plik `MANIFEST_KONTYNUACJA.txt` oraz 4 kopie `*_bible.json`. Ponadto bezpośrednio w `Artefakty/` leży zduplikowany plik `Hyouken_no_Majutsushi_ga_Sekai_wo_Suberu_S2_bible.json`.

**Instrukcja:**
1. Usuń cały zduplikowany katalog roboczy poleceniem:
   ~~~bash
   git rm -r Artefakty/_KONTYNUACJA_CZATU/
   ~~~
2. Usuń zduplikowany plik bible z katalogu `Artefakty/`:
   ~~~bash
   git rm Artefakty/Hyouken_no_Majutsushi_ga_Sekai_wo_Suberu_S2_bible.json
   ~~~
   *(Uwaga: oryginał `series_memory/Hyouken_no_Majutsushi_ga_Sekai_wo_Suberu_S2_bible.json` w katalogu `series_memory/` pozostaje nietknięty — to jest właściwe źródło prawdy).*

- **Test regresyjny:** `T10.6_1` (`test_t10_6_1_no_duplicate_py_in_artefakty`).

---

### Operacja `2B.2` — Dodanie brakującego `Artefakty/Prompt_10.5.md` (`I-05`)

- **Finding:** `I-05` (P1) z `Raport_audytu_koncowego_10_5.md`.
- **Problem:** Podczas gdy dla `10.0.3`, `10.2`, `10.3`, `10.4` istnieją pliki `Artefakty/Prompt_*.md`, brakuje pliku `Artefakty/Prompt_10.5.md` dokumentującego specyfikację wdrożoną w commicie `b2095bb`.

**Instrukcja:**
1. Utwórz plik `Artefakty/Prompt_10.5.md` z poniższą treścią dokumentującą zakres Standardu 10.5:
   ~~~markdown
   # PROMPT WYKONAWCZY (STANDARD 10.5) — OPTYMALIZACJA TRIGGERA DYN_8 ORAZ SYNCHRONIZACJA NORMY CPS 14–15 W FAZIE 2

   ## METADANE
   - **Wersja docelowa:** `10.5`
   - **Wersja poprzednia (baseline):** `10.4` (`ebbe426`)
   - **Commit wdrożenia:** `b2095bb` (`b2095bb5b64abe39c1dd5fbcebfd999d40351b19`)
   - **Podstawa audytowa:** `Artefakty/Raport_audytu_doboru_filarow_i_obciazenia_llm.md` (rekomendacje P1: `R-01` i `R-02`)

   ## ZAKRES OPERACJI IMPLEMENTACYJNYCH
   1. **Operacja `2B.1` (`R-01`):** Zawężenie wyrażenia regularnego `culture_signs_pat` w kategorii `DYN_8` (`rules.py`) poprzez usunięcie wieloznacznych słów ogólnych (`sign`, `notice`, `warning`, `ep \d+`, `episode`), które powodowały fałszywe wzbudzanie kategorii kulturowo-humorystycznej w zwykłym dialogu. Wykrywanie napisów ekranowych realizowane jest przez flagę strukturalną `has_sign_flag`.
   2. **Operacja `2B.2` (`R-02`):** Synchronizacja opisu budżetu czytelniczego w szablonie Fazy 2 (`verifier.py`) z regułą bazową `R1.7` (celowanie w polskie optimum percepcyjne `14–15` znaków na sekundę przy zachowaniu maksymalnego pułapu `17` znaków na sekundę `CPS` i limitu `38` znaków w linii `CPL`) oraz deduplikacja checklisty weryfikatora względem `STANDARD_9_CORE_RULES_PROMPT`.
   3. **Operacja `2B.3` (Testy regresyjne):** Dodanie testów `T10.5_1` (`test_t10_5_1_no_false_positive_dyn8_verify_sign_notice_episode`), `T10.5_2` (`test_t10_5_2_verifier_cps_norm_aligned_with_r17`) oraz `T10.5_3` (`test_t10_5_3_verifier_checklist_deduplicated`) w `tests/test_profiler.py`.

   ## DOKUMENTACJA WDROŻENIA
   Pełny raport z realizacji i walidacji CI/CD znajduje się w pliku `Artefakty/Raport_wdrozenia_10.5.md`.
   ~~~
2. Dodaj plik do indeksu Git: `git add Artefakty/Prompt_10.5.md`.

- **Test regresyjny:** `T10.6_2` (`test_t10_6_2_prompt_files_present`).

---

### Operacja `2B.3` — Aktualizacja `AGENTS.md` i `PROJECT.md` o rzeczywistą listę 30 modułów runtime (`I-01`)

- **Finding:** `I-01` (P1) z `Raport_audytu_koncowego_10_5.md`.
- **Problem:** Dokumentacja architektoniczna nie wymieniała pełnej listy 30 aktywnych modułów runtime (w tym m.in. `memory.py`, `romaji_helper.py`, `speaker_diarizer.py`, `style_matrix.py`, `whisper_engine.py`).

**Instrukcja:**
1. W `AGENTS.md` oraz `PROJECT.md` zaktualizuj lub dodaj sekcję **Moduły Runtime Potoku (30 plików `.py`)**, wymieniając dokładnie wszystkie 30 modułów produkcyjnych z katalogu głównego:
   `avt_formatter.py`, `avt_linter.py`, `client_factory.py`, `context_cache.py`, `extract.py`, `fansub_miner.py`, `glossary_manager.py`, `main.py`, `manga_canon.py`, `memory.py`, `metadata.py`, `model_resolver.py`, `pipeline_logger.py` (zawiera również klasę `FlightRecorder`), `pricing_guard.py`, `profiler.py`, `prosody_engine.py`, `romaji_helper.py`, `rules.py`, `scene_discourse.py`, `scene_snapper.py`, `series_memory.py`, `sign_detector.py`, `speaker_diarizer.py`, `style_matrix.py`, `translator.py`, `typesetting_matcher.py`, `user_feedback.py`, `verifier.py`, `whisper_disambiguator.py`, `whisper_engine.py`.
2. **KRYTYCZNA UWAGA DLA TESTU `T10.6_3`:** Jeśli w `AGENTS.md` lub `PROJECT.md` występowały jakiekolwiek wzmianki o nieistniejących plikach `flight_recorder.py`, `text_utils.py`, `llm_retry.py`, `quality_metrics.py` lub `pipeline_config.py` — **usuń te nazwy całkowicie** (nie zostawiaj ich nawet w nawiasie czy komentarzu historycznym, ponieważ test `T10.6_3` weryfikuje `assert m not in agents_md`!). Napisz po prostu: *„Klasa `FlightRecorder` znajduje się w module `pipeline_logger.py`.”*
3. **NIE modyfikuj** pozostałych sekcji tych dokumentów (zasad Z1–Z16, historii wdrożeń).

- **Test regresyjny:** `T10.6_3` (`test_t10_6_3_docs_list_30_runtime_modules`).

---

### Operacja `2B.4` — Zamiana wszystkich cichych `except Exception...: pass` na `logger.debug(..., exc_info=True)` w `translator.py` (`I-06`)

- **Finding:** `I-06` (P1) z `Raport_audytu_koncowego_10_5.md`.
- **Lokalizacje:** Wszystkie miejsca w `translator.py` zwrócone przez Komendę 4 z Fazy 0 (zarówno wielolinijkowe `except Exception:\n pass`, jak i ewentualne jednolinijkowe `except Exception: pass` lub `except Exception as e: pass`).

**Instrukcja:**
1. Sprawdź, czy w `translator.py` jest zainicjowany obiekt `logger` (`import logging` oraz `logger = logging.getLogger(__name__)` lub istniejący logger modułowy). Jeśli nie ma, dodaj `logger = logging.getLogger(__name__)` na górze pliku.
2. W każdym miejscu w `translator.py`, gdzie blok `except Exception` (lub `except Exception as ...`) zawiera wyłącznie `pass`, zastąp `pass` wywołaniem:
   ~~~python
   except Exception:
       logger.debug("Pomocnicza operacja kontekstowa translatora zakończona wyjątkiem", exc_info=True)
   ~~~
   *(Dostosuj treść komunikatu `logger.debug` merytorycznie do danego bloku `try`, używając wyłącznie pozytywnych polskich sformułowań zgodnych z Z2).*

- **Test regresyjny:** `T10.6_4` (`test_t10_6_4_no_silent_except_pass_in_critical_modules`).

---

### Operacja `2B.5` — Zamiana wszystkich cichych `except Exception...: pass` na `logger.warning(..., exc_info=True)` w `series_memory.py` (`I-07`)

- **Finding:** `I-07` (P1) z `Raport_audytu_koncowego_10_5.md`.
- **Lokalizacje:** Wszystkie miejsca w `series_memory.py` zwrócone przez Komendę 5 z Fazy 0.

**Instrukcja:**
1. Sprawdź, czy w `series_memory.py` jest dostępny `logger = logging.getLogger(__name__)` (jeśli nie, dodaj `import logging` i `logger = logging.getLogger(__name__)` na górze pliku).
2. W każdym miejscu w `series_memory.py`, gdzie blok `except Exception` (lub `except Exception as ...`) zawiera wyłącznie `pass`, zastąp `pass` wywołaniem `logger.warning` z opisem dopasowanym do danego bloku:
   ~~~python
   except Exception:
       logger.warning("Operacja pomocnicza pamięci serii zakończona wyjątkiem", exc_info=True)
   ~~~

- **Test regresyjny:** `T10.6_4` (`test_t10_6_4_no_silent_except_pass_in_critical_modules`).

---

### Operacja `2B.6` — Zamiana wszystkich gołych `except:` na `except Exception:` w aktywnych plikach `.py` (`I-08`)

- **Finding:** `I-08` (P1) z `Raport_audytu_koncowego_10_5.md`.
- **Pliki:** Wszystkie aktywne pliki `.py` wskazane przez Komendę 6 w Fazie 0 (m.in. `avt_linter.py`, `manga_canon.py`, `typesetting_matcher.py`, `extract.py` — z bezwzględnym wyłączeniem plików chronionych Z16: `test_system.py` oraz `tests/archive/`).

**Instrukcja:**
1. W każdym aktywnym pliku `.py` (poza `test_system.py` i `tests/archive/`) zamień każde wystąpienie gołego `except:` na `except Exception:`.
2. **NIE zmieniaj** ciał bloków `except` ani żadnej innej logiki (w szczególności w `avt_linter.py` nie dotykaj 3 gałęzi `# DEFENSIVE_FALLBACK`).
3. Po edycji upewnij się, że komenda:
   ~~~bash
   grep -rnE "^\s*except\s*:" --include="*.py" . | grep -v "Artefakty/" | grep -v "tests/archive/" | grep -v "test_system.py"
   ~~~
   zwraca **`0` trafień**.

- **Test regresyjny:** `T10.6_5` (`test_t10_6_5_no_bare_except_in_active_py`).

---

### Operacja `2B.7` — Warunek progu minimalnego tokenów (`< 4096`) w `context_cache.py` (`I-12`)

- **Finding:** `I-12` (P1) z `Raport_audytu_koncowego_10_5.md`.
- **Problem:** Gemini API Context Caching wymaga minimum `4 096` tokenów (dla modeli Gemini 3.x). Ponieważ odchudzony w Standardzie 10.2 prompt bazowy (`STANDARD_9_CORE_RULES_PROMPT` + `EPISODE BRIEF`) liczy ok. `1 800` tokenów, wywołanie `caches.create` na starcie odcinka kończy się błędem HTTP 400 i przejściem do fallbacku, tracąc 1 wywołanie sieciowe na odcinek.

**Instrukcja:**
1. Przeczytaj dokładnie `context_cache.py` (wynik Komendy 7 z Fazy 0) i sprawdź dokładną sygnaturę funkcji/metody tworzącej cache (np. `get_or_create_translation_cache` lub metody w klasie managera cache).
2. Przed wywołaniem `caches.create` oblicz łączny rozmiar tekstu przekazywanego do cache (np. `system_instruction` / `system_prompt` + ewentualne `contents`), oszacuj liczbę tokenów (`estimated_tokens = len(total_text) // 4`) i jeśli `estimated_tokens < 4096`, zaloguj informację przez `logger.debug` (lub `print` / `logger`, zależnie od tego, czego używa `context_cache.py`) i zwróć `None` **bez wywoływania `caches.create`**:
   ~~~python
   estimated_tokens = len(total_cache_text) // 4
   if estimated_tokens < 4096:
       logger.debug(
           "Pominięto tworzenie cache Gemini: oszacowany rozmiar (%d tokenów) poniżej progu 4096 tokenów",
           estimated_tokens,
       )
       return None
   ~~~
3. Sprawdź, czy w `tests/` istnieją testy jednostkowe testujące `context_cache.py` — jeśli któryś z istniejących testów przekazuje krótki tekst i oczekuje wywołania `caches.create`, upewnij się, że nie zepsujesz istniejącego testu (np. dostosowując próg lub sprawdzając istniejące testy w `tests/`).

- **Test regresyjny:** `T10.6_6` (`test_t10_6_6_context_cache_skips_small_prompts`).

---

## SEKCJA 2 — WALIDACJA TESTOWA (NOWY PLIK `tests/test_hygiene.py`)

Utwórz nowy plik testowy **`tests/test_hygiene.py`** zawierający poniższe 6 testów regresyjnych (`T10.6_1`–`T10.6_6`, co daje 10 wykonań pytest dzięki parametryzacji):

~~~python
import re
from pathlib import Path
from unittest.mock import MagicMock
import pytest


@pytest.mark.unit
def test_t10_6_1_no_duplicate_py_in_artefakty():
    """
    Standard 10.6 (I-02): Weryfikuje, że w katalogu Artefakty/ nie ma zduplikowanych
    plików .py ani katalogu _KONTYNUACJA_CZATU/ czy zduplikowanego pliku *_bible.json.
    """
    artefakty_dir = Path("Artefakty")
    artefakty_py = list(artefakty_dir.rglob("*.py"))
    assert len(artefakty_py) == 0, (
        f"Znaleziono {len(artefakty_py)} plików .py w Artefakty/: {[str(p) for p in artefakty_py]}"
    )

    kontynuacja_dir = artefakty_dir / "_KONTYNUACJA_CZATU"
    assert not kontynuacja_dir.exists(), (
        f"Katalog {kontynuacja_dir} nadal istnieje — powinien zostać usunięty w 10.6"
    )

    artefakty_bibles = list(artefakty_dir.rglob("*_bible.json"))
    assert len(artefakty_bibles) == 0, (
        f"Znaleziono zduplikowane pliki *_bible.json w Artefakty/: {[str(p) for p in artefakty_bibles]}"
    )


@pytest.mark.unit
@pytest.mark.parametrize(
    "prompt_file",
    [
        "Artefakty/Prompt_10.2_minimalizacja_filarow.md",
        "Artefakty/Prompt_10.3_dopelnienie_filarow.md",
        "Artefakty/Prompt_10.4.md",
        "Artefakty/Prompt_10.5.md",
    ],
)
def test_t10_6_2_prompt_files_present(prompt_file):
    """
    Standard 10.6 (I-05): Weryfikuje kompletność promptów wykonawczych 10.2–10.5 w Artefakty/.
    """
    p = Path(prompt_file)
    assert p.exists(), f"Brak pliku {prompt_file}"
    assert p.stat().st_size > 100, (
        f"Plik {prompt_file} ma podejrzanie mały rozmiar ({p.stat().st_size} B)"
    )


@pytest.mark.unit
def test_t10_6_3_docs_list_30_runtime_modules():
    """
    Standard 10.6 (I-01): Weryfikuje, że AGENTS.md wymienia wszystkie 5 wcześniej
    pominiętych modułów runtime i nie wymienia 5 nieistniejących nazw plików.
    """
    agents_md = Path("AGENTS.md").read_text(encoding="utf-8")
    required = [
        "memory.py",
        "romaji_helper.py",
        "speaker_diarizer.py",
        "style_matrix.py",
        "whisper_engine.py",
    ]
    missing = [m for m in required if m not in agents_md]
    assert not missing, f"AGENTS.md nie wymienia modułów: {missing}"

    forbidden = [
        "flight_recorder.py",
        "text_utils.py",
        "llm_retry.py",
        "quality_metrics.py",
        "pipeline_config.py",
    ]
    present = [m for m in forbidden if m in agents_md]
    assert not present, f"AGENTS.md nadal wymienia nieistniejące moduły: {present}"


@pytest.mark.unit
@pytest.mark.parametrize(
    "module_file",
    [
        "translator.py",
        "series_memory.py",
    ],
)
def test_t10_6_4_no_silent_except_pass_in_critical_modules(module_file):
    """
    Standard 10.6 (I-06, I-07): Weryfikuje brak cichych 'except Exception...: pass'
    (jedno- i wielolinijkowych) w translator.py oraz series_memory.py.
    """
    src = Path(module_file).read_text(encoding="utf-8")
    silent_pattern = re.compile(
        r"except\s+Exception(?:\s+as\s+\w+)?\s*:\s*(?:\n\s*)?pass\b",
        re.MULTILINE,
    )
    matches = silent_pattern.findall(src)
    assert not matches, (
        f"Znaleziono {len(matches)} cichych 'except Exception: pass' w {module_file}"
    )


@pytest.mark.unit
def test_t10_6_5_no_bare_except_in_active_py():
    """
    Standard 10.6 (I-08): Weryfikuje brak gołego 'except:' w aktywnych plikach .py
    (poza Artefakty/, tests/archive/ oraz zamrożonym Z16 test_system.py).
    """
    bare_pattern = re.compile(r"^\s*except\s*:", re.MULTILINE)
    offenders = []
    for py in Path(".").rglob("*.py"):
        if any(part in py.parts for part in ("Artefakty", ".venv", "venv", "__pycache__")):
            continue
        if "tests/archive" in py.as_posix() or py.name == "test_system.py":
            continue
        src = py.read_text(encoding="utf-8")
        if bare_pattern.search(src):
            offenders.append(py.as_posix())

    assert not offenders, f"Znaleziono goły 'except:' w plikach: {offenders}"
~~~

Dodatkowo w `tests/test_hygiene.py` dopisz test **`test_t10_6_6_context_cache_skips_small_prompts`** dopasowany do rzeczywistej sygnatury funkcji/klasy w `context_cache.py` (odczytanej w Komendzie 7 Fazy 0), weryfikujący za pomocą `MagicMock`, że dla krótkiego tekstu (`< 4096` tokenów) funkcja zwraca `None` i `mock_client.caches.create.assert_not_called()`.

---

## SEKCJA 3 — WALIDACJA BRAMEK CI/CD I Z16

Po wdrożeniu operacji `2B.1`–`2B.7` oraz `tests/test_hygiene.py` uruchom pełną walidację:

### 3.1. Weryfikacja usunięcia duplikatów (`2B.1`, `2B.2`)
~~~bash
find Artefakty/ -name "*.py" | wc -l          # oczekiwane: 0
find Artefakty/ -name "*_bible.json" | wc -l  # oczekiwane: 0
ls -la Artefakty/Prompt_10.5.md               # oczekiwane: plik istnieje (> 100 B)
~~~

### 3.2. Weryfikacja braku cichych wyjątków i gołego `except:` (`2B.4`, `2B.5`, `2B.6`)
~~~bash
grep -rnE "^\s*except\s*:" --include="*.py" . | grep -v "Artefakty/" | grep -v "tests/archive/" | grep -v "test_system.py" | wc -l
# oczekiwane: 0
~~~

### 3.3. Suity `pytest`
- `pytest tests/test_hygiene.py -q` → `10 passed` (`6` funkcji testowych, z parametryzacją `10` przypadków)
- `pytest tests/ -q` → `274 passed, 0 failed` (`264` z baseline `10.5` + `10` nowych przypadków z `test_hygiene.py`)
- `pytest -q` → `345 passed, 153 deselected, 0 failed` (`335` z baseline `10.5` + `10` nowych)
- `pytest -m slow -q` → `153 passed`
- `pytest -m network -q` → `12 passed`

### 3.4. 4 Bramki CI/CD
- `python verify_purity.py` → `12/12 PASS`
- `python verify_8_fixes.py` → `12/12 PASS`
- `python verify_12_fixes.py` → `15/15 PASS`
- `python verify_ultimate_pipeline.py` → `4/4 PASS`

### 3.5. Asercja ochrony Z16 oraz nienaruszalności `series_memory/`
~~~bash
# 1. Pliki całkowicie zamrożone przez Z16 (wyjście musi być w 100% puste):
git diff b2095bb..HEAD -- test_system.py tests/archive/ pytest.ini

# 2. Pasywna stała TRANSLATION_RULES_PROMPT w rules.py (wyjście musi być w 100% puste):
git diff b2095bb..HEAD -- rules.py

# 3. 3 gałęzie # DEFENSIVE_FALLBACK w avt_linter.py (musi zwrócić dokładnie 3):
grep -c "# DEFENSIVE_FALLBACK" avt_linter.py

# 4. Nienaruszalność 20 bibles w series_memory/ (wyjście musi być w 100% puste):
git diff b2095bb..HEAD -- series_memory/
~~~

---

## SEKCJA 4 — WARUNKI UKOŃCZENIA `(a)`–`(j)`

- **(a)** Wykonano 9 komend diagnostycznych z Fazy 0, a ich surowe wyjścia oraz odpowiedzi `F0.1–F0.9` wklejono w Sekcji 0 raportu `Artefakty/Raport_wdrozenia_10.6.md`.
- **(b)** Usunięto katalog `Artefakty/_KONTYNUACJA_CZATU/` oraz duplikat `Artefakty/Hyouken_no_Majutsushi_ga_Sekai_wo_Suberu_S2_bible.json` (`2B.1`).
- **(c)** Dodano plik `Artefakty/Prompt_10.5.md` (`2B.2`).
- **(d)** Zaktualizowano `AGENTS.md` i `PROJECT.md` o kompletną listę 30 modułów runtime, bez używania 5 nieistniejących nazw plików (`2B.3`).
- **(e)** Zamieniono ciche `except Exception...: pass` w `translator.py` na `logger.debug(..., exc_info=True)` (`2B.4`).
- **(f)** Zamieniono ciche `except Exception...: pass` w `series_memory.py` na `logger.warning(..., exc_info=True)` (`2B.5`).
- **(g)** Zamieniono wszystkie gołe `except:` w aktywnych plikach `.py` na `except Exception:` (`2B.6`).
- **(h)** Dodano warunek progu minimalnego tokenów (`< 4096`) przed `caches.create` w `context_cache.py` (`2B.7`).
- **(i)** Dodano plik `tests/test_hygiene.py` z testami `T10.6_1`–`T10.6_6` i wszystkie przechodzą (`10 passed`).
- **(j)** `pytest tests/ -q` → `274 passed, 0 failed`; `pytest -q` → `345 passed, 153 deselected, 0 failed`; 4 bramki CI/CD → `PASS`; Z16 nienaruszone; `series_memory/` nienaruszone; raport `Artefakty/Raport_wdrozenia_10.6.md` zapisany; `git status` clean; zmiany wypchnięte w **1 commicie**:
  `chore(hygiene): Hotfix 10.6 - cleanup duplicates, log suppressed exceptions, optimize context cache`

---

## SEKCJA 5 — ZAKAZY

1. **ZAKAZ 1 (Z16):** Nie modyfikuj `test_system.py`, `tests/archive/`, 3 gałęzi `# DEFENSIVE_FALLBACK` w `avt_linter.py`, `pytest.ini` ani `rules.py`.
2. **ZAKAZ 2 (Poza zakresem 10.6):** Nie modyfikuj logiki biznesowej `translator.py`, `verifier.py`, `avt_linter.py` (poza zamianą gołego `except:` na `except Exception:`), `glossary_manager.py`, `manga_canon.py` (poza zamianą gołego `except:` na `except Exception:`), `fansub_miner.py` ani `requirements.txt`.
3. **ZAKAZ 3 (Z1/Z2/Z4):** W komunikatach `logger.debug` / `logger.warning` używaj wyłącznie pozytywnych polskich zdań opisowych.
4. **ZAKAZ 4 (Pułapka `T10.6_3` w `AGENTS.md`):** W `AGENTS.md` nie wpisuj ciągów `"flight_recorder.py"`, `"text_utils.py"`, `"llm_retry.py"`, `"quality_metrics.py"`, `"pipeline_config.py"` nawet w komentarzu wyjaśniającym, bo złamie to asercję `forbidden` w `T10.6_3`.
5. **ZAKAZ 5 (Higiena Git):** Jeden czysty commit wdrożeniowy na `main`, `0` plików śmieciowych, `git status` clean.
6. **ZAKAZ 6 (Brak placeholderów):** `0` placeholderów `<DO_WYPEŁNIENIA>` w gotowym raporcie `Artefakty/Raport_wdrozenia_10.6.md`.

---

## SEKCJA 6 — KNOWN RISKS

1. **`R1` (Ochrona 3 gałęzi `# DEFENSIVE_FALLBACK` w `avt_linter.py`):** Podczas zamiany gołego `except:` na `except Exception:` w `avt_linter.py` (`2B.6`) nie zmieniaj ani jednego znaku w 3 gałęziach `# DEFENSIVE_FALLBACK`.
2. **`R2` (Sygnatura w `context_cache.py` dla `2B.7` i `T10.6_6`):** Przed napisaniem `T10.6_6` sprawdź w Fazie 0 (Komenda 7), czy `context_cache.py` eksportuje funkcję `get_or_create_translation_cache` czy klasę, i jakich dokładnie nazw argumentów używa. Dopasuj test `T10.6_6` do faktycznej sygnatury z `context_cache.py`.
3. **`R3` (Jedno- vs wielolinijkowe `except`):** Zarówno w `translator.py`/`series_memory.py` (`2B.4`, `2B.5`), jak i przy szukaniu gołego `except:` (`2B.6`), używaj wyrażeń regularnych z Fazy 0, które wykrywają także warianty jednolinijkowe i ze zmienną `as e`.

---

## SEKCJA 7 — SZABLON RAPORTU WDROŻENIA (`Artefakty/Raport_wdrozenia_10.6.md`)

Zapisz raport w pliku `Artefakty/Raport_wdrozenia_10.6.md` według poniższej struktury:
1. **Diagnostyka wstępna (FAZA 0):** surowe wyjścia 9 komend przed edycją oraz odpowiedzi na pytania `F0.1–F0.9`.
2. **Metadane git:** hash commita bazowego (`b2095bb`), hash commita `10.6`, `git status`, `git diff --stat`.
3. **Tabela realizacji operacji (`2B.1 – 2B.7`):** status, lokalizacje, opis każdej zmiany.
4. **Cytaty kodu po naprawie:**
   - zamiany `logger.debug` w `translator.py`,
   - zamiany `logger.warning` w `series_memory.py`,
   - lista zamian `except:` → `except Exception:` z numerami linii,
   - warunek `estimated_tokens < 4096` w `context_cache.py`,
   - zaktualizowana sekcja 30 modułów w `AGENTS.md` i `PROJECT.md`.
5. **Wyniki 4 bramek CI/CD:** surowe wyjścia `verify_purity.py`, `verify_8_fixes.py`, `verify_12_fixes.py`, `verify_ultimate_pipeline.py`.
6. **Wyniki `pytest` oraz weryfikacja Z16 i `series_memory/`:** surowe wyjścia `pytest` oraz potwierdzenie nienaruszalności Z16.
7. **Checklista ukończenia `(a)`–`(j)`.**
8. **Werdykt końcowy:** `PASS`.
9. **Backlog 11.0:** potwierdzenie pozostawienia zadań refaktoryzacyjnych (`I-03`, `I-04`, `I-09`–`I-11`, `I-13`–`I-60`, `N-05`, `R-03`–`R-05`, `L-06`) w backlogu `11.0`.

---

## SEKCJA 8 — KOMENDY COMMITU

Po przejściu wszystkich testów i zapisaniu raportu wdrożenia wykonaj:

~~~bash
# 1. Stage zmodyfikowanych i nowych plików
git add translator.py series_memory.py avt_linter.py manga_canon.py typesetting_matcher.py extract.py context_cache.py
git add AGENTS.md PROJECT.md
git add tests/test_hygiene.py
git add Artefakty/Prompt_10.5.md Artefakty/Raport_wdrozenia_10.6.md

# 2. Upewnij się, że usunięte duplikaty są zarejestrowane w indeksie Git
git rm -r --ignore-unmatch Artefakty/_KONTYNUACJA_CZATU/
git rm --ignore-unmatch Artefakty/Hyouken_no_Majutsushi_ga_Sekai_wo_Suberu_S2_bible.json

# 3. Commit i Push
git commit -m "chore(hygiene): Hotfix 10.6 - cleanup duplicates, log suppressed exceptions, optimize context cache"
git push origin main
~~~

---

## FAZA ODBIORU

Na końcu raportu wdrożenia potwierdź:

- [x] FAZA 0 — Weryfikacja HEAD (`b2095bb`); 9 komend diagnostycznych wykonanych; `F0.1–F0.9` odpowiedziane
- [x] SEKCJA 1 — Operacje `2B.1`–`2B.7` wdrożone w całości
- [x] SEKCJA 2 — Plik `tests/test_hygiene.py` (`T10.6_1`–`T10.6_6`, `10 passed`) dodany
- [x] SEKCJA 3 — 4 bramki CI/CD: `PASS` (`12/12`, `12/12`, `15/15`, `4/4`)
- [x] SEKCJA 4 — Warunki ukończenia `(a)`–`(j)` spełnione
- [x] SEKCJA 5 — Zakazy: `0` naruszeń (Z16, Z1–Z4, wąski zakres, brak zmian funkcjonalnych)
- [x] SEKCJA 6 — Known risks `R1`–`R3` zweryfikowane
- [x] SEKCJA 7 — Raport `Artefakty/Raport_wdrozenia_10.6.md` zapisany (`0` placeholderów)
- [x] SEKCJA 8 — Commit wypchnięty na `origin/main`
- [x] `pytest tests/ -q` → `274 passed, 0 failed`
- [x] `pytest -q` → `345 passed, 153 deselected, 0 failed`
- [x] `pytest -m slow -q` → `153 passed`
- [x] `pytest -m network -q` → `12 passed`
- [x] Z16 nienaruszone (`git diff b2095bb..HEAD -- test_system.py tests/archive/ pytest.ini rules.py` pusty, `grep -c "# DEFENSIVE_FALLBACK" avt_linter.py` == `3`)
- [x] `series_memory/` nienaruszone (`git diff b2095bb..HEAD -- series_memory/` pusty)
- [x] `git status` clean

**Koniec promptu wykonawczego 10.6.**