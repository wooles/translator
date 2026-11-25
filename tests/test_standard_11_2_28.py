"""
Zestaw nienaruszalnych, nietautologicznych testów regresyjnych dla Standardu 11.2.28:
- OBS-12 (3 testy): Normalizacja cyrylickich homogliffów wizualnych w tekście łacińskim/polskim z ochroną cytatów CYR i JP/EN
- OBS-14 (3 testy): Ochrona sąsiedniej kwestii dolnej przed sztucznym nakładaniem przy wydłużaniu krótkich kwestii do 700 ms (z izolacją znaków/top)
- OBS-15a/b/c (4 testy): Ochrona glosariusza Tier 1 przed nadpisaniem przez Profiler Tier 3, deduplikacja opisów gender-only, higiena <Imię> i RAM-only czyszczenie ogonów RELACJA HIERARCHICZNA przy 0 B diffu na dysku
- OBS-09 (2 testy): Emisja wskazówek rodzaju WUJ/CIOTKA w format_compact_ssot_tag i zachowanie po filtrze K1/K3
- OBS-11 (2 testy): Redukcja pustych \\N\\N i warunkowa reguła higieny łamania linii ASS w Fazie 2
"""

import json
import re
import pytest
import pysubs2

from translator import (
    MultimodalTranslator,
    sanitize_sub_text,
    _append_phase2_linebreak_hygiene_rule,
)
from scene_snapper import SceneShotSnapper
from series_memory import SeriesBible
from glossary_manager import GlossaryManager
from whisper_disambiguator import WhisperDisambiguator


# =====================================================================
# OBS-12: Cyrylickie homogliffy wizualne
# =====================================================================

@pytest.mark.unit
def test_obs12_cyrillic_homoglyph_mixed_tokens_normalized():
    """
    OBS-12: Tokeny mieszane (łacińsko-cyrylickie homogliffy typu 'wуdawaj', 'Тo', 'pоmоc')
    są deterministycznie normalizowane do czystej łacinki z zachowaniem idempotentności.
    """
    mixed = "w\u0443dawaj \u0422o p\u043em\u043ec i z\u0430cz\u0430\u0142 \u0441zyt\u0430\u0107."
    out = sanitize_sub_text(mixed, is_ass=True)
    assert out == "wydawaj To pomoc i zacza\u0142 czyta\u0107."
    assert not any("\u0400" <= ch <= "\u04ff" for ch in out)
    # Idempotence
    assert sanitize_sub_text(out, is_ass=True) == out


@pytest.mark.unit
def test_obs12_cyrillic_homoglyph_single_letter_and_linebreak():
    """
    OBS-12: Samotne jednoliterowe homogliffy cyrylickie ('А', 'о', 'а') w polskim zdaniu
    oraz tuż po separatorze ASS \\N są konwertowane na znaki łacińskie bez utraty \\N.
    """
    raw_input = "C\u043e?\\N{\\i1}\u0410 jak?\\NTo jest \u043e nim!"
    out = sanitize_sub_text(raw_input, is_ass=True)
    assert out == "Co?\\N{\\i1}A jak?\\NTo jest o nim!"
    assert not any("\u0400" <= ch <= "\u04ff" for ch in out)
    assert sanitize_sub_text(out, is_ass=True) == out


@pytest.mark.unit
def test_obs12_preserves_genuine_cyrillic_quotes_and_jp_en():
    """
    OBS-12: Prawdziwe słowa i cytaty cyrylickie ('Привет, мир!', 'Москва', 'Київ', 'В Москве о нас')
    oraz zapisy JP/EN pozostają nietknięte.
    """
    quote_ru = 'Powiedział: "Привет, мир!" oraz "Москва" i "Київ".'
    assert sanitize_sub_text(quote_ru, is_ass=True) == quote_ru

    ru_with_o = 'Powiedział "В Москве о нас" do Bohatera.'
    assert sanitize_sub_text(ru_with_o, is_ass=True) == ru_with_o

    jp_en = "「おはよう」 Good morning!"
    assert sanitize_sub_text(jp_en, is_ass=True) == jp_en


# =====================================================================
# OBS-14: Ochrona przed sztucznym nakładaniem na sąsiednią kwestię dolną
# =====================================================================

@pytest.mark.unit
def test_obs14_short_reply_extension_clamped_before_next_same_layer():
    """
    OBS-14: Krótka replika dolna (< 700 ms) dosuwana do cięcia nie może wydłużyć się
    poza start następnej niepokrywającej się kwestii dolnej.
    """
    ev1 = pysubs2.SSAEvent(start=1000, end=1400, text="Tak!", style="Default")
    ev2 = pysubs2.SSAEvent(start=1400, end=2800, text="Rozumiem.", style="Default")

    events, _ = SceneShotSnapper.snap_subtitles_to_cuts(
        events=[ev1, ev2],
        scene_cuts_ms=[1500],
        snap_window_ms=250,
        min_duration_ms=700,
    )
    assert events[0].end <= events[1].start
    assert events[0].end == 1400


@pytest.mark.unit
def test_obs14_short_reply_extends_normally_when_gap_is_wide():
    """
    OBS-14 (kontrprzykład): Gdy odstęp do kolejnej kwestii dolnej jest duży,
    krótka replika nadal wydłuża się normalnie do min_duration_ms = 700 ms.
    """
    ev1 = pysubs2.SSAEvent(start=1000, end=1400, text="Tak!", style="Default")
    ev2 = pysubs2.SSAEvent(start=3000, end=4200, text="Idziemy dalej.", style="Default")

    events, snapped = SceneShotSnapper.snap_subtitles_to_cuts(
        events=[ev1, ev2],
        scene_cuts_ms=[1500],
        snap_window_ms=250,
        min_duration_ms=700,
    )
    assert snapped >= 1
    assert events[0].end == 1700


@pytest.mark.unit
def test_obs14_signs_and_top_events_isolated_from_bottom_dialogue():
    """
    OBS-14: Napisy ekranowe (styl Signs) oraz kwestie górne ({\\an8} / \\pos)
    należą do odrębnej warstwy i nie blokują wydłużania dolnego dialogu.
    """
    ev_diag_1 = pysubs2.SSAEvent(start=1000, end=1400, text="Dobrze!", style="Default")
    ev_sign = pysubs2.SSAEvent(start=1400, end=2500, text="ROZDZIAŁ 1", style="Signs")
    ev_top = pysubs2.SSAEvent(start=1400, end=2500, text="{\\an8}Notatka górna", style="Default")

    events, snapped = SceneShotSnapper.snap_subtitles_to_cuts(
        events=[ev_diag_1, ev_sign, ev_top],
        scene_cuts_ms=[1500],
        snap_window_ms=250,
        min_duration_ms=700,
    )
    assert snapped >= 1
    assert events[0].end == 1700


# =====================================================================
# OBS-15a / 15b / 15c: Pamięć serii, prompt i higiena metadanych
# =====================================================================

@pytest.mark.unit
def test_obs15a_profiler_never_overwrites_existing_series_glossary_or_canon(tmp_path):
    """
    OBS-15a: Aktualizacja z Profilera (Tier 3, overwrite_existing_glossary=False)
    nie nadpisuje istniejących haseł z Kanonu Mangi (Tier 1) ani ręcznego glosariusza,
    lecz swobodnie dopisuje nowe nieistniejące hasła.
    """
    bible = SeriesBible(bible_path=tmp_path / "obs15a_bible.json", storage_dir=tmp_path)
    bible.update_from_episode_profile(
        episode_name="Kanon Mangi",
        characters={},
        glossary={"Guardian Guild": "Gildia Strażników"},
        overwrite_existing_glossary=True,
    )
    bible.update_from_episode_profile(
        episode_name="EP01",
        characters={},
        glossary={
            "Guardian Guild": "Bractwo Obrońców",
            "guardian guild": "Inna Nazwa",
            "New Relic": "Nowy Relikt",
        },
        overwrite_existing_glossary=False,
    )

    assert bible.data["glossary"]["Guardian Guild"] == "Gildia Strażników"
    assert bible.data["glossary"]["New Relic"] == "Nowy Relikt"

    combined = GlossaryManager().get_combined_glossary(
        series_glossary=bible.data["glossary"],
        manga_canon_glossary={"Guardian Guild": "Gildia Strażników"},
        profiler_glossary={"Guardian Guild": "Bractwo Obrońców"},
    )
    assert combined["Guardian Guild"] == "Gildia Strażników"


@pytest.mark.unit
def test_obs15b_generic_gender_only_duplicate_dropped_in_batch_prompt():
    """
    OBS-15b: Wpisy rejestru będące wyłącznie generycznym placeholderem płci
    ('mężczyzna (postać)', 'kobieta (postać)') są pomijane, gdy bogatszy wpis P0/alias
    już występuje, przy pełnym zachowaniu właściwych opisów ról ('mężczyzna - kupiec').
    """
    tr = MultimodalTranslator(
        api_key="mock_k0",
        model="gemini-4-hydrogen",
        enable_verifier=False,
    )
    tr.character_registry = {
        "BOHATER_A": "mężczyzna (postać)",
        "Bohater_A Nazwisko": {
            "description": "Młody rycerz straży miejskiej",
            "priority": "P0",
            "has_verified_gender": True,
            "aliases": ["BOHATER_A", "Bohater_A"],
        },
        "SOJUSZNICZKA_B": "kobieta (postać)",
        "Sojuszniczka_B Nazwisko": {
            "description": "Królewska alchemiczka",
            "priority": "P0",
            "has_verified_gender": True,
            "aliases": ["SOJUSZNICZKA_B", "Sojuszniczka_B"],
        },
        "Handlarz_C": "mężczyzna - tajemniczy kupiec z portu",
    }

    ev = pysubs2.SSAEvent(start=1000, end=2000, text="Test dialogue.", name="Bohater_A")
    prompt = tr._prepare_batch_prompt(
        batch_events=[(0, ev, "Test dialogue.", "")],
        history_context=[],
    )

    assert "• BOHATER_A:" not in prompt
    assert "• SOJUSZNICZKA_B:" not in prompt
    assert "• Bohater_A Nazwisko:" in prompt
    assert "• Sojuszniczka_B Nazwisko:" in prompt
    assert "• Handlarz_C:" in prompt


@pytest.mark.unit
def test_obs15c_sanitize_character_entry_avoids_nested_imie_brackets(tmp_path):
    """
    OBS-15c: _sanitize_character_entry generuje placeholder <Imię> zamiast zagnieżdżonego [Imię],
    eliminując przyczynę źródłową ucinania klauzul przez regexy oparte na [^\\]]*.
    """
    bible = SeriesBible(bible_path=tmp_path / "obs15c_entry.json", storage_dir=tmp_path)
    out = bible._sanitize_character_entry("Mentor_X", "mistrz i mentor akademii")
    assert "Pan / Panie <Imię>" in out
    assert "Pan / Panie [Imię]" not in out


@pytest.mark.unit
def test_obs15c_ram_sanitization_strips_orphaned_tail_with_zero_disk_diff(tmp_path):
    """
    OBS-15c: Ładowanie bazy serii z dysku zawierającej zagnieżdżoną klauzulę [Imię]
    lub osierocony ogon ', eliminacja hybryd ... -sama]' czyści je w RAM
    z zachowaniem absolutnego 0 B diffu na dysku, a prompt nie przepuszcza przecieku.
    """
    bible_file = tmp_path / "obs15c_disk_zero_diff.json"
    orphaned_tail = "uczennica', eliminacja hybryd 'Imię... ma pan' oraz odporność na opuszczanie -sama]"
    nested_clause = (
        "uczeń [RELACJA HIERARCHICZNA (T-V Invariance): stały zwrot formalny 'Pan / Panie [Imię]', "
        "eliminacja hybryd 'Imię... ma pan' oraz odporność na opuszczanie -sama] lojalny adept"
    )
    payload = {
        "episodes_translated": ["EP01"],
        "characters": {
            "Adept_A": {
                "description": nested_clause,
                "gender": "MALE",
                "grammatical_gender": "MASCULINE",
                "confidence": 0.99,
                "priority": "P0",
                "has_verified_gender": True,
                "aliases": [],
            },
            "Uczennica_B": {
                "description": orphaned_tail,
                "gender": "FEMALE",
                "grammatical_gender": "FEMININE",
                "confidence": 0.99,
                "priority": "P0",
                "has_verified_gender": True,
                "aliases": [],
            },
        },
        "relations": {
            "Adept_A -> Mentor_X": nested_clause,
            "Uczennica_B -> Mentor_X": "poufna relacja" + orphaned_tail,
        },
        "glossary": {},
        "declensions": {},
        "plot_anchors": {},
    }
    raw_bytes = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
    bible_file.write_bytes(raw_bytes)

    bible = SeriesBible(bible_path=bible_file, storage_dir=tmp_path)

    # 1. Bezwzględne 0 B diffu na pliku na dysku po załadowaniu
    assert bible_file.read_bytes() == raw_bytes

    # 2. Czysty stan w RAM
    adept_desc = bible.data["characters"]["Adept_A"]["description"]
    uczennica_desc = bible.data["characters"]["Uczennica_B"]["description"]
    rel_1 = bible.data["relations"]["Adept_A -> Mentor_X"]
    rel_2 = bible.data["relations"]["Uczennica_B -> Mentor_X"]

    for txt in (adept_desc, uczennica_desc, rel_1, rel_2):
        assert "eliminacja hybryd" not in txt
        assert "-sama]" not in txt
    assert "lojalny adept" in adept_desc
    assert "uczennica" in uczennica_desc

    # 3. Dodatkowo _prepare_batch_prompt czyści osierocony ogon przy bezpośrednim podaniu do rejestru
    tr = MultimodalTranslator(api_key="mock_k0", model="gemini-4-hydrogen", enable_verifier=False)
    tr.character_registry = {"Uczennica_Raw": {"description": orphaned_tail}}
    ev = pysubs2.SSAEvent(start=1000, end=2000, text="Hello.", name="Uczennica_Raw")
    prompt = tr._prepare_batch_prompt(batch_events=[(0, ev, "Hello.", "")], history_context=[])
    assert "eliminacja hybryd" not in prompt
    assert "-sama]" not in prompt


# =====================================================================
# OBS-09: Obsługa ról pokrewieństwa WUJ / CIOTKA w WhisperDisambiguator
# =====================================================================

@pytest.mark.unit
def test_obs09_compact_ssot_tag_emits_wuj_and_ciotka_gender_hints():
    """
    OBS-09: WhisperDisambiguator.format_compact_ssot_tag emituje jawne wskazówki
    płci/relacji dla kinship_role == 'WUJ' (ojisan) oraz 'CIOTKA' (obasan).
    """
    tag_wuj = WhisperDisambiguator.disambiguate_line(
        clean_en="Thank you, mister!",
        jp_audio="おじさん、ありがとう",
    )
    tag_ciotka = WhisperDisambiguator.disambiguate_line(
        clean_en="Excuse me, ma'am.",
        jp_audio="おばさん、すみません",
    )

    assert tag_wuj.kinship_role == "WUJ"
    assert tag_ciotka.kinship_role == "CIOTKA"

    compact_wuj = WhisperDisambiguator.format_compact_ssot_tag(tag_wuj)
    compact_ciotka = WhisperDisambiguator.format_compact_ssot_tag(tag_ciotka)

    assert "Wuj/starszy mężczyzna (MĘŻCZYZNA)" in compact_wuj
    assert "Ciotka/starsza kobieta (KOBIETA)" in compact_ciotka


@pytest.mark.unit
def test_obs09_translator_k1_k3_filter_preserves_wuj_ciotka_hint():
    """
    OBS-09: Filtr usuwający markery K1/K3 w translator.py nie wycina wskazówki
    rodzaju Wuj/Ciotka generowanej przez WhisperDisambiguator.format_compact_ssot_tag.
    """
    tag_wuj = WhisperDisambiguator.disambiguate_line(clean_en="Hey old man!", jp_audio="おじさん！")
    tag_ciotka = WhisperDisambiguator.disambiguate_line(clean_en="Wait auntie!", jp_audio="おばさん！")

    for tag, expected in (
        (tag_wuj, "Wuj/starszy mężczyzna (MĘŻCZYZNA)"),
        (tag_ciotka, "Ciotka/starsza kobieta (KOBIETA)"),
    ):
        compact_tag = WhisperDisambiguator.format_compact_ssot_tag(tag)
        filtered = re.sub(r"\bK[13]\b", "", compact_tag).replace("  ", " ").strip()
        assert expected in filtered


# =====================================================================
# OBS-11: Higiena łamania linii ASS (\N\N -> \N i reguła Fazy 2)
# =====================================================================

@pytest.mark.unit
def test_obs11_sanitize_sub_text_collapses_empty_double_linebreaks():
    """
    OBS-11: sanitize_sub_text zwija puste podwójne lub potrójne łamania linii ASS
    (\\N\\N, \\N \\N\\N) do pojedynczego \\N, zachowując zwykłe pojedyncze \\N.
    """
    assert sanitize_sub_text("Pierwsza linia.\\N\\NDruga linia.", is_ass=True) == "Pierwsza linia.\\NDruga linia."
    assert sanitize_sub_text("Pierwsza linia.\\N \\N\\NDruga linia.", is_ass=True) == "Pierwsza linia.\\NDruga linia."
    single = "Pierwsza linia.\\NDruga linia."
    assert sanitize_sub_text(single, is_ass=True) == single
    assert sanitize_sub_text(sanitize_sub_text("A\\N\\NB", is_ass=True), is_ass=True) == "A\\NB"


@pytest.mark.unit
def test_obs11_phase2_linebreak_hygiene_rule_injected_only_when_needed():
    """
    OBS-11: Pomocnik _append_phase2_linebreak_hygiene_rule wstrzykuje wytyczną
    o unikaniu sierot i pustych \\N\\N wyłącznie wtedy, gdy paczka Fazy 2 zawiera \\N.
    """
    no_breaks = [{"id": 1, "pl": "Krótka kwestia bez łamania."}]
    res_no = _append_phase2_linebreak_hygiene_rule("BAZOWE_REGULY", no_breaks)
    assert res_no == "BAZOWE_REGULY"
    assert "HIGIENA ŁAMANIA LINII ASS" not in res_no

    with_breaks = [
        {"id": 1, "pl": "Krótka linia."},
        {"id": 2, "pl": "Pierwsza część\\NDruga część"},
    ]
    res_yes = _append_phase2_linebreak_hygiene_rule("BAZOWE_REGULY", with_breaks)
    assert res_yes.startswith("BAZOWE_REGULY\n")
    assert "HIGIENA ŁAMANIA LINII ASS (\\N)" in res_yes


# =====================================================================
# Hotfix 11.2.28a: BUG #1, BUG #2, LUKA #4 (OBS-09 negatyw) & ev.name
# =====================================================================

@pytest.mark.unit
def test_bug1_preserves_apostrophes_in_clean_description(tmp_path):
    """
    BUG #1 (11.2.28a): Czysty opis postaci/relacji bez wycieków RELACJA HIERARCHICZNA /
    eliminacja hybryd zachowuje w RAM nienaruszone pojedyncze apostrofy przed przecinkiem
    (np. "'Kronika Gwiazd',"), a plik na dysku pozostaje nietknięty (0 B diff).
    """
    bible_file = tmp_path / "bug1_clean_apostrophes.json"
    clean_desc = "mężczyzna (postać), twórca, autor 'Kronika Gwiazd', tytulatura: 'mistrz Autor_X'"
    clean_rel = "twórca 'Kronika Gwiazd', serdeczna współpraca"
    payload = {
        "episodes_translated": ["EP01"],
        "characters": {
            "Autor_X": {
                "description": clean_desc,
                "gender": "MALE",
                "grammatical_gender": "MASCULINE",
                "confidence": 0.99,
                "priority": "P0",
                "has_verified_gender": True,
                "aliases": [],
            }
        },
        "relations": {"Autor_X -> Uczennica_B": clean_rel},
        "glossary": {},
        "declensions": {},
        "plot_anchors": {},
    }
    raw_bytes = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
    bible_file.write_bytes(raw_bytes)

    bible = SeriesBible(bible_path=bible_file, storage_dir=tmp_path)

    assert bible_file.read_bytes() == raw_bytes
    assert bible.data["characters"]["Autor_X"]["description"] == clean_desc
    assert "'Kronika Gwiazd'," in bible.data["characters"]["Autor_X"]["description"]
    assert bible.data["relations"]["Autor_X -> Uczennica_B"] == clean_rel


@pytest.mark.unit
def test_bug1_removes_orphan_tail_with_apostrophe(tmp_path):
    """
    BUG #1 (11.2.28a): Gdy wpis zawiera jednocześnie poprawny cytat z apostrofem przed
    przecinkiem ORAZ wyciek / osierocony ogon ', eliminacja hybryd ... -sama]',
    ogon zostaje usunięty w RAM przy 100% zachowaniu poprawnego cytatu i 0 B diffu na dysku.
    """
    bible_file = tmp_path / "bug1_mixed_tail_apostrophes.json"
    mixed_desc = (
        "autor 'Kronika Gwiazd', uczennica', "
        "eliminacja hybryd 'Imię... ma pan' oraz odporność na opuszczanie -sama]"
    )
    payload = {
        "episodes_translated": ["EP01"],
        "characters": {
            "Uczennica_B": {
                "description": mixed_desc,
                "gender": "FEMALE",
                "grammatical_gender": "FEMININE",
                "confidence": 0.99,
                "priority": "P0",
                "has_verified_gender": True,
                "aliases": [],
            }
        },
        "relations": {"Uczennica_B -> Autor_X": mixed_desc},
        "glossary": {},
        "declensions": {},
        "plot_anchors": {},
    }
    raw_bytes = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
    bible_file.write_bytes(raw_bytes)

    bible = SeriesBible(bible_path=bible_file, storage_dir=tmp_path)

    assert bible_file.read_bytes() == raw_bytes
    for val in (
        bible.data["characters"]["Uczennica_B"]["description"],
        bible.data["relations"]["Uczennica_B -> Autor_X"],
    ):
        assert "eliminacja hybryd" not in val
        assert "-sama]" not in val
        assert "autor 'Kronika Gwiazd', uczennica" in val


@pytest.mark.unit
def test_bug2_rich_description_starting_with_mezczyzna_postac_is_not_generic():
    """
    BUG #2 (11.2.28a): Bogaty opis postaci zaczynający się od 'mężczyzna (postać), ...'
    (np. rola, zawód, autorstwo) nie jest klasyfikowany jako generyczny i pozostaje w prompcie.
    """
    tr = MultimodalTranslator(
        api_key="mock_k0",
        model="gemini-4-hydrogen",
        enable_verifier=False,
    )
    rich_desc = "mężczyzna (postać), twórca, autor 'Kronika Gwiazd', tytulatura: 'mistrz'"
    tr.character_registry = {
        "Autor_X": {
            "description": rich_desc,
            "priority": "P0",
            "has_verified_gender": True,
            "aliases": ["Autor_X"],
        },
        "Autor_X Nazwisko": {
            "description": "Twórca z gildii pisarzy",
            "priority": "P0",
            "has_verified_gender": True,
            "aliases": ["Autor_X", "Autor_X Nazwisko"],
        },
    }

    ev = pysubs2.SSAEvent(start=1000, end=2000, text="Test line.", name="Autor_X")
    prompt = tr._prepare_batch_prompt(
        batch_events=[(0, ev, "Test line.", "")],
        history_context=[],
    )

    assert "• Autor_X:" in prompt
    assert "'Kronika Gwiazd'" in prompt


@pytest.mark.unit
def test_bug2_exact_generic_mezczyzna_postac_is_generic():
    """
    BUG #2 (11.2.28a): Ścisłe generyczne placeholdery 'mężczyzna (postać)' oraz
    'mężczyzna (postać drugoplanowa)' nadal są wycinane z promptu obok bogatszego aliasu P0.
    """
    tr = MultimodalTranslator(
        api_key="mock_k0",
        model="gemini-4-hydrogen",
        enable_verifier=False,
    )
    tr.character_registry = {
        "MENTOR_Y": "mężczyzna (postać)",
        "MENTOR_Z": "mężczyzna (postać drugoplanowa)",
        "Mentor_Y Nazwisko": {
            "description": "Główny mentor akademii rycerskiej",
            "priority": "P0",
            "has_verified_gender": True,
            "aliases": ["MENTOR_Y", "MENTOR_Z", "Mentor_Y Nazwisko"],
        },
    }

    ev = pysubs2.SSAEvent(start=1000, end=2000, text="Test line.", name="MENTOR_Y")
    prompt = tr._prepare_batch_prompt(
        batch_events=[(0, ev, "Test line.", "")],
        history_context=[],
    )

    assert "• MENTOR_Y:" not in prompt
    assert "• MENTOR_Z:" not in prompt
    assert "• Mentor_Y Nazwisko:" in prompt


@pytest.mark.unit
def test_obs09_no_annotation_without_ojisan_obasan():
    """
    LUKA #4 (11.2.28a): Neutralna kwestia bez 'ojisan'/'obasan' i markerów płci/rejestru
    nie uruchamia fałszywej anotacji kinship_role i zwraca pusty compact SSOT tag (0 tokenów).
    """
    for en_line, jp_line in (
        ("It is raining today.", "今日は雨だ"),
        ("Wait a moment.", "ちょっと待って"),
    ):
        tag = WhisperDisambiguator.disambiguate_line(
            clean_en=en_line,
            jp_audio=jp_line,
        )
        assert tag.kinship_role is None
        assert WhisperDisambiguator.format_compact_ssot_tag(tag) == ""


@pytest.mark.unit
def test_scene_snapper_ev_name_sign_eptitle_not_blocked():
    """
    Zadanie 3 (11.2.28a): Napisy z aktorem SIGN / SIGN BIG / EPTITLE przy stylu Default
    są izolowane od warstwy dolnego dialogu i nie blokują wydłużania repliki do 700 ms.
    """
    ev_sign_name = pysubs2.SSAEvent(start=1400, end=2500, style="Default", name="SIGN", text="SKLEP")
    ev_eptitle_name = pysubs2.SSAEvent(start=1400, end=2500, style="Default", name="EPTITLE", text="TYTUŁ")
    assert SceneShotSnapper._is_top_or_sign_event(ev_sign_name) is True
    assert SceneShotSnapper._is_top_or_sign_event(ev_eptitle_name) is True

    ev_diag_1 = pysubs2.SSAEvent(start=1000, end=1400, style="Default", name="Bohater", text="Dobrze!")
    events, snapped = SceneShotSnapper.snap_subtitles_to_cuts(
        events=[ev_diag_1, ev_sign_name],
        scene_cuts_ms=[1500],
        snap_window_ms=250,
        min_duration_ms=700,
    )
    assert snapped >= 1
    assert events[0].end == 1700
