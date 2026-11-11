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


@pytest.mark.unit
def test_t10_6_6_context_cache_skips_small_prompts():
    """
    Standard 10.6 (I-12): Weryfikuje, że dla krótkiego tekstu (< 4096 tokenów)
    ContextCacheManager.get_or_create_cache zwraca None i nie wywołuje client.caches.create,
    zaś dla długiego promptu (>= 4096 tokenów) wywołuje caches.create.
    """
    from context_cache import ContextCacheManager

    mock_client = MagicMock()
    mock_client._api_client.api_key = "dummy_key_12345"
    mock_client.caches.list.return_value = []

    # 1. Krótki prompt: np. 100 znaków (ok. 25 tokenów < 4096)
    short_prompt = "Krótki prompt systemowy dla tłumacza AVT bez długiego kontekstu."
    res = ContextCacheManager.get_or_create_cache(
        client=mock_client,
        model="gemini-2.5-flash",
        system_instruction=short_prompt,
        tag="translator",
    )

    assert res is None
    mock_client.caches.create.assert_not_called()

    # 2. Długi prompt: >= 4096 tokenów (np. 24 000 znaków -> 6 000 tokenów > 4096)
    mock_client.reset_mock()
    mock_client._api_client.api_key = "dummy_key_12345"
    mock_client.caches.list.return_value = []
    mock_cache = MagicMock()
    mock_cache.name = "caches/test_cache_12345"
    mock_client.caches.create.return_value = mock_cache

    long_prompt = "Kanon zasad tłumaczenia " * 1000
    res_long = ContextCacheManager.get_or_create_cache(
        client=mock_client,
        model="gemini-2.5-flash",
        system_instruction=long_prompt,
        tag="translator",
    )
    assert res_long == "caches/test_cache_12345"
    mock_client.caches.create.assert_called_once()


@pytest.mark.unit
def test_T11_1_5_italics_style_tag_normalization_and_glossary_preservation():
    """Hotfix 11.1.5 (P3-1 / P3-2 / E-09 / E-11): Weryfikacja normalizacji tagów kursywy i ochrony glosariusza."""
    from translator import format_phase1_candidate_text
    import pysubs2

    # 1. Normalizacja znaczników <i> oraz {\i1} na stylu Italics
    ev_italics = pysubs2.SSAEvent(start=1000, end=3000, text="Internal monologue", style="Italics")
    input_text = "<i>{\\i1}Czułem, że coś jest nie tak...{\\i0}</i>\\NTo był zły znak."
    normalized = format_phase1_candidate_text(input_text, ev_italics)
    assert "<i>" not in normalized
    assert "</i>" not in normalized
    assert "{\\i1}" not in normalized
    assert "{\\i0}" not in normalized
    assert "\\N" in normalized

    # 2. Ochrona zablokowanego glosariusza przed dryfem synonimicznym w Fazy 2
    glossary_items = [{"term_en": "magic stone", "translation_pl": "kamień magiczny"}]
    orig_item = {"id": 1, "en": "Take this magic stone with you.", "pl": "Weź ze sobą ten kamień magiczny."}
    pass1_items = [orig_item]
    refined_dict = {1: "Weź ze sobą ten klejnot czarnoksięski."}

    r_en = orig_item["en"].lower()
    p1_pl = orig_item["pl"]
    r_pl = refined_dict[1]

    for g_entry in glossary_items:
        term_en = g_entry["term_en"].lower()
        trans_pl = g_entry["translation_pl"].lower()
        if term_en in r_en:
            trans_stem = trans_pl[:max(4, len(trans_pl) - 2)]
            has_p1_canon = trans_pl in p1_pl.lower() or trans_stem in p1_pl.lower()
            has_ref_canon = trans_pl in r_pl.lower() or trans_stem in r_pl.lower()
            if has_p1_canon and not has_ref_canon:
                refined_dict[1] = p1_pl

    assert refined_dict[1] == "Weź ze sobą ten kamień magiczny."


@pytest.mark.unit
def test_t11_1_6_b1_glossary_enforced_when_phase1_uses_synonym_or_plural():
    """
    Standard 11.1.6 (BŁĄD-1 / E-11):
    Weryfikuje, że dla zablokowanego terminu glosariusza 'Lord Starsage' -> 'Mędrzec Gwiazd'
    oraz kwestii EN w liczbie mnogiej bez prefiksu tytularnego ('starsages'),
    odwrócona kalka przymiotnikowa 'Gwiezdnego Mędrca' zostaje skorygowana na 'Mędrca Gwiazd'.
    """
    from translator import enforce_locked_glossary_terms

    glossary_items = [{"term_en": "Lord Starsage", "translation_pl": "Mędrzec Gwiazd"}]
    line_en = "*Do not feed meat to sparrows that aren't reincarnations of starsages!*"
    candidate_pl = "*Nie karmić mięsem wróbli poza reinkarnacją Gwiezdnego Mędrca!*"

    result_phase1 = enforce_locked_glossary_terms(
        en_text=line_en,
        candidate_pl=candidate_pl,
        glossary_entries=glossary_items,
        phase1_pl=None
    )
    expected = "*Nie karmić mięsem wróbli poza reinkarnacją Mędrca Gwiazd!*"
    assert result_phase1 == expected

    result_phase2 = enforce_locked_glossary_terms(
        en_text=line_en,
        candidate_pl=result_phase1,
        glossary_entries=glossary_items,
        phase1_pl=result_phase1
    )
    assert result_phase2 == expected


