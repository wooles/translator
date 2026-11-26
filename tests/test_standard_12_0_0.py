"""
Zestaw nienaruszalnych, nietautologicznych testów regresyjnych dla Standardu 12.0.0 + Hotfixu 12.0.0a:
- Commit 1 (5 testów): A-1, A-2, A-3, E-1, E-2
- Commit 2 (4 testy): B-1, B-2, B-3, D-1
- Commit 3 (4 testy): F-2/C-1, F-3, D-2
- Commit 4 (3 testy): F-1, H-3 (OBS-06)
- Commit 5 (3 testy): G-1, G-2
- Hotfix 12.0.0a (5 testów): BUG #1..#5
"""

import concurrent.futures
import json
import sys
import threading
import types
from pathlib import Path
import httpx
import pytest
import pysubs2
from google import genai
from google.genai import types as genai_types

from pipeline_logger import EpisodeFlightRecorder

from translator import (
    MultimodalTranslator,
    sanitize_sub_text,
    _filter_dialogue_audio_events,
    _resolve_active_dramatic_sequence,
    _build_ssot_lean_bible_str,
    _deduplicate_episode_signs,
    _build_clean_f2_character_registry,
    _uppercase_preserving_ass_tags,
    extract_typesetting_tags,
    sanitize_ts_prefix_for_translation,
)
from verifier import DialogueVerifier
from glossary_manager import GlossaryManager
import whisper_engine
from whisper_engine import JapaneseWhisperEngine
from style_matrix import StyleMatrixReport, EventRole
from series_memory import SeriesBible
from profiler import (
    EpisodeProfile,
    EpisodeProfiler,
    GlossaryTerm,
    CharacterRelationship,
    CharacterDossier,
    DramaticSequence,
    RelationshipPivot,
    format_lean_episode_brief,
    resolve_profile_alerts_to_events,
)


# =====================================================================
# COMMIT 1: Czyste sygnały wejściowe i higiena RAM (A-1, A-2, A-3, E-1, E-2)
# =====================================================================

@pytest.mark.unit
def test_a1_sign_and_song_events_excluded_from_prosody_and_f0():
    """
    A-1: Filtr wejścia dla AudioProsodyEngine / SpeakerVoiceClassifier wyklucza wyłącznie
    SIGN_OVERLAY, SIGN_LOCATIONAL, SONG_LYRICS i STAFF_METADATA,
    NIGDY nie wykluczając DIALOGUE_TOP ani DIALOGUE_BOTTOM.
    """
    subs = pysubs2.SSAFile()
    subs.styles["Default"] = pysubs2.SSAStyle()
    subs.styles["Main"] = pysubs2.SSAStyle(alignment=8)
    subs.styles["Sign"] = pysubs2.SSAStyle()
    subs.styles["OP"] = pysubs2.SSAStyle()

    ev_bottom = pysubs2.SSAEvent(start=1000, end=2500, style="Default", name="Bohater_A", text="Zaczynamy!")
    ev_top = pysubs2.SSAEvent(start=2600, end=4000, style="Main", name="Dialogue", text="{\\an8}Głos z oddali.")
    ev_sign_ovl = pysubs2.SSAEvent(start=4100, end=5000, style="Sign", name="Sign", text="SKLEP")
    ev_sign_loc = pysubs2.SSAEvent(start=5100, end=6000, style="Sign", name="Sign", text="{\\pos(200,150)}Szyld")
    ev_song = pysubs2.SSAEvent(start=6100, end=8000, style="OP", name="Singer", text="Opening song lyrics")
    ev_staff = pysubs2.SSAEvent(start=8100, end=9000, style="Sign", name="Sign", text="TRANSLATION: Ekipa_X")

    subs.events.extend([ev_bottom, ev_top, ev_sign_ovl, ev_sign_loc, ev_song, ev_staff])
    report = StyleMatrixReport(subs)

    assert report.classify_single_event(ev_bottom)[0] == EventRole.DIALOGUE_BOTTOM
    assert report.classify_single_event(ev_top)[0] == EventRole.DIALOGUE_TOP
    assert report.classify_single_event(ev_sign_ovl)[0] == EventRole.SIGN_OVERLAY
    assert report.classify_single_event(ev_sign_loc)[0] == EventRole.SIGN_LOCATIONAL
    assert report.classify_single_event(ev_song)[0] == EventRole.SONG_LYRICS
    assert report.classify_single_event(ev_staff)[0] == EventRole.STAFF_METADATA

    tuples = [
        (0, ev_bottom, "Zaczynamy!", ""),
        (1, ev_top, "Głos z oddali.", "{\\an8}"),
        (2, ev_sign_ovl, "SKLEP", ""),
        (3, ev_sign_loc, "Szyld", "{\\pos(200,150)}"),
        (4, ev_song, "Opening song lyrics", ""),
        (5, ev_staff, "TRANSLATION: Ekipa_X", ""),
    ]
    filtered = _filter_dialogue_audio_events(tuples, style_report=report)
    kept_indices = [item[0] for item in filtered]
    assert kept_indices == [0, 1]


@pytest.mark.unit
def test_a2_whisper_drops_high_no_speech_and_low_logprob_segments(tmp_path, monkeypatch):
    """
    A-2: Konserwatywny filtr pewności segmentów Whisper:
    - odrzuca nsp > 0.85,
    - odrzuca (nsp > 0.75 i alp < -1.2),
    - ZACHOWUJE cichy szept (nsp=0.78, alp=-0.4), (nsp=0.30, alp=-1.5) oraz segment bez atrybutów.
    """
    class _Seg:
        def __init__(self, text, start, end, no_speech_prob=None, avg_logprob=None):
            self.text = text
            self.start = start
            self.end = end
            self.words = None
            if no_speech_prob is not None:
                self.no_speech_prob = no_speech_prob
            if avg_logprob is not None:
                self.avg_logprob = avg_logprob

    segs = [
        _Seg("szum_wysoki_nsp", 0.1, 0.9, no_speech_prob=0.90, avg_logprob=-0.2),
        _Seg("belkot_kombo", 1.1, 1.9, no_speech_prob=0.78, avg_logprob=-1.35),
        _Seg("cichy_szept", 2.1, 2.9, no_speech_prob=0.78, avg_logprob=-0.4),
        _Seg("szybka_kwestia", 3.1, 3.9, no_speech_prob=0.30, avg_logprob=-1.5),
        _Seg("brak_pol", 4.1, 4.9),
    ]
    events = [
        (1, pysubs2.SSAEvent(start=0, end=1000, text="a")),
        (2, pysubs2.SSAEvent(start=1000, end=2000, text="b")),
        (3, pysubs2.SSAEvent(start=2000, end=3000, text="c")),
        (4, pysubs2.SSAEvent(start=3000, end=4000, text="d")),
        (5, pysubs2.SSAEvent(start=4000, end=5000, text="e")),
    ]

    wav_path = tmp_path / "dummy.wav"
    wav_path.write_bytes(b"RIFF")

    fake_model = types.SimpleNamespace(transcribe=lambda *a, **kw: (iter(segs), None))
    monkeypatch.setattr(whisper_engine, "FASTER_WHISPER_AVAILABLE", True)
    engine = JapaneseWhisperEngine(model_size="tiny")
    engine._initialize_model = lambda: None
    engine.model = fake_model

    res = engine.transcribe_batch_scene(str(wav_path), batch_start_ms=0, events=events)
    assert 1 not in res
    assert 2 not in res
    assert res[3] == "cichy_szept"
    assert res[4] == "szybka_kwestia"
    assert res[5] == "brak_pol"


@pytest.mark.unit
def test_a3_style_matrix_classifies_credits_as_staff_metadata():
    """
    A-3: Wersalikowe napisy ekipy fansuberskiej ('TRANSLATION: ...', 'FINAL QUALITY CONTROL: ...')
    są klasyfikowane jako STAFF_METADATA przed regułą ALL CAPS (SIGN_OVERLAY),
    a normalny dialog zawierający 'translation:' pozostaje DIALOGUE_BOTTOM.
    """
    subs = pysubs2.SSAFile()
    subs.styles["Default"] = pysubs2.SSAStyle()
    subs.styles["Top"] = pysubs2.SSAStyle(alignment=8)

    ev_tl = pysubs2.SSAEvent(start=0, end=2000, style="Top", name="sign", text="TRANSLATION: Ekipa_X")
    ev_qc = pysubs2.SSAEvent(start=2000, end=4000, style="Default", name="", text="FINAL QUALITY CONTROL: Korektor_Y")
    ev_dlg = pysubs2.SSAEvent(start=4000, end=6000, style="Default", name="Bohater_A", text="The translation: it was rough.")
    subs.events.extend([ev_tl, ev_qc, ev_dlg])

    report = StyleMatrixReport(subs)
    assert report.classify_single_event(ev_tl)[0] == EventRole.STAFF_METADATA
    assert report.classify_single_event(ev_qc)[0] == EventRole.STAFF_METADATA
    assert report.classify_single_event(ev_dlg)[0] == EventRole.DIALOGUE_BOTTOM


@pytest.mark.unit
def test_e1_ram_honorific_strip_prevents_san_alias_leak_zero_disk_diff(tmp_path):
    """
    E-1: Przy keep_honorifics=False SeriesBible usuwa przyrostki honoryfikatywne (-san/-kun/-chan/-sama)
    z kluczy i aliasów postaci wyłącznie w RAM przy absolutnym 0 B diffu pliku na dysku.
    """
    bible_file = tmp_path / "e1_honorifics.json"
    payload = {
        "episodes_translated": ["EP01"],
        "characters": {
            "Postac_A-san": {
                "description": "Koledzy ze szkoły",
                "gender": "MALE",
                "grammatical_gender": "MASCULINE",
                "confidence": 0.99,
                "priority": "P0",
                "has_verified_gender": True,
                "aliases": ["Postac_A-san", "A-kun"],
            }
        },
        "relations": {},
        "glossary": {},
        "declensions": {},
        "plot_anchors": {},
    }
    raw_bytes = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
    bible_file.write_bytes(raw_bytes)

    bible = SeriesBible(bible_path=bible_file, storage_dir=tmp_path, keep_honorifics=False)

    assert bible_file.read_bytes() == raw_bytes
    assert "Postac_A-san" not in bible.data["characters"]
    assert "Postac_A" in bible.data["characters"]
    assert set(bible.data["characters"]["Postac_A"]["aliases"]) == {"Postac_A", "A"}


@pytest.mark.unit
def test_e2_all_homoglyph_short_polish_words_normalized_while_ru_preserved():
    """
    E-2: Krótkie 2-4 literowe słowa polskie złożone wyłącznie z cyrylickich homogliffów
    ('\\u0422\\u043e', '\\u0441\\u043e', '\\u043e\\u0441\\u0430') są normalizowane do łacinki,
    przy pełnym zachowaniu prawdziwych cytatów rosyjskich ('В Москве о нас', 'Привет, мир!', 'О, привет!').
    """
    assert sanitize_sub_text("\u0422\u043e jest nasz dom.", is_ass=True) == "To jest nasz dom."
    assert sanitize_sub_text("A \u0441\u043e z tym?", is_ass=True) == "A co z tym?"
    assert sanitize_sub_text("Wszystko \u041e\u041a, ruszamy.", is_ass=True) == "Wszystko OK, ruszamy."

    for ru_quote in (
        'Powiedział "В Москве о нас" do Bohatera_A.',
        'Szept: "Привет, мир!"',
        'Krzyknął "О, привет!" i wyszedł.',
    ):
        assert sanitize_sub_text(ru_quote, is_ass=True) == ru_quote


# =====================================================================
# COMMIT 2: Most stylistyczny Profilera, ton sekwencji i kanon glosariusza (B-1, B-2, B-3, D-1)
# =====================================================================

@pytest.mark.unit
def test_b1_lean_brief_includes_stylization_summary_domain_idioms_and_pivots_resolved():
    """
    B-1: format_lean_episode_brief() zawiera Fabuła odcinka, Stylizacja i Rejestry Frakcji,
    Dziedzina i Realia, Konwencje i Idiomy, nie ucina relacji na 8 (do 20) oraz wspiera include_glossary=False.
    resolve_profile_alerts_to_events() podpina relationship_pivots w oknie +-20000 ms.
    """
    rels = [
        CharacterRelationship(
            speaker=f"Postac_{i}",
            listener="Bohater_A",
            address_form="per ty",
            relationship_type="sojusznicy",
        )
        for i in range(1, 13)
    ]
    profile = EpisodeProfile(
        episode_summary="Bohater_A wyrusza na zwiad do Gildii Światła.",
        dialogue_stylization="Arystokracja mówi podniośle; najemnicy potocznie.",
        domain_expertise="Alchemia kryształów i sztuka oblężnicza.",
        key_conventions=["Zwięzłe riposty w scenach walki."],
        yojijukugo_and_idioms=[GlossaryTerm(term_en="once in a lifetime", translation_pl="raz na całe życie", explanation="idiom")],
        glossary=[GlossaryTerm(term_en="Radiant Guild", translation_pl="Gildia Światła", explanation="nazwa")],
        characters=rels,
        relationship_pivots=[
            RelationshipPivot(
                approx_time="00:01:00",
                characters_involved="Bohater_A -> Mistrzyni_B",
                nature_of_shift="Przełamanie dystansu",
                relational_guidance="Przejście z formy oficjalnej na ty po wspólnej walce.",
            )
        ],
    )

    brief_full = format_lean_episode_brief(profile, include_glossary=True)
    assert "• Fabuła odcinka:" in brief_full
    assert "• Stylizacja i Rejestry Frakcji:" in brief_full
    assert "• Dziedzina i Realia:" in brief_full
    assert "• Konwencje i Idiomy:" in brief_full
    assert "Idiom once in a lifetime = raz na całe życie" in brief_full
    assert "Postac_12 -> Bohater_A: per ty" in brief_full
    assert "• Zablokowana Terminologia:" in brief_full

    brief_no_gloss = format_lean_episode_brief(profile, include_glossary=False)
    assert "• Zablokowana Terminologia:" not in brief_no_gloss

    ev_pivot = pysubs2.SSAEvent(start=61000, end=63500, name="Bohater_A", text="Od teraz mów mi po imieniu.")
    ev_other = pysubs2.SSAEvent(start=5000, end=7000, name="Kupiec_C", text="Ładna pogoda.")
    alerts = resolve_profile_alerts_to_events(profile, [(10, ev_other, ev_other.text, ""), (42, ev_pivot, ev_pivot.text, "")])
    assert 42 in alerts
    assert any("PRZEŁOM RELACJI" in tag and "Przejście z formy oficjalnej" in tag for tag in alerts[42])


@pytest.mark.unit
def test_b2_active_dramatic_sequence_tone_injected_into_f1_batch_and_f2_context():
    """
    B-2: _resolve_active_dramatic_sequence dobiera sekwencję o największym pokryciu czasowym,
    a _prepare_batch_prompt wstrzykuje [AKTYWNA SEKWENCJA DRAMATURGICZNA] z dominant_tone.
    """
    profile = EpisodeProfile(
        dramatic_sequences=[
            DramaticSequence(
                sequence_name="Akt 1: Narada",
                time_range="00:00 - 01:00",
                dramatic_summary="Spokojna wymiana argumentów.",
                dominant_tone="chłodna powaga dworska",
            ),
            DramaticSequence(
                sequence_name="Akt 2: Pościg",
                time_range="01:00 - 02:00",
                dramatic_summary="Kłótnia przyjaciół podczas ucieczki.",
                dominant_tone="dynamiczny humor i akcja",
            ),
        ]
    )

    seq_str = _resolve_active_dramatic_sequence(profile, 65000, 95000)
    assert "Akt 2: Pościg" in seq_str
    assert "Ton: dynamiczny humor i akcja" in seq_str

    tr = MultimodalTranslator(api_key="mock_k0", model="gemini-4-hydrogen", enable_verifier=True)
    ev = pysubs2.SSAEvent(start=68000, end=71000, name="Bohater_A", text="Szybciej!")
    prompt = tr._prepare_batch_prompt(
        batch_events=[(0, ev, "Szybciej!", "")],
        history_context=[],
        episode_profile=profile,
    )
    assert "[AKTYWNA SEKWENCJA DRAMATURGICZNA]: Akt 2: Pościg | Ton: dynamiczny humor i akcja" in prompt


@pytest.mark.unit
def test_b3_profiler_receives_existing_series_bible_glossary():
    """
    B-3: EpisodeProfiler.profile_episode(..., existing_glossary=...) wstrzykuje utrwalone
    terminy z SeriesBible do promptu Profilera (limit do 40 terminów).
    """
    captured_prompts = []

    class _FakeModels:
        def generate_content(self, model=None, contents=None, config=None):
            captured_prompts.append(contents)
            return types.SimpleNamespace(text=EpisodeProfile().model_dump_json())

    fake_client = types.SimpleNamespace(models=_FakeModels(), clients=[1])
    fake_client.get_client = lambda: fake_client
    profiler = EpisodeProfiler(client=fake_client, model="gemini-4-hydrogen")
    glossary_seed = {"Radiant Beast": "Promienista Bestia"}
    for i in range(1, 50):
        glossary_seed[f"Term_{i:02d}"] = f"Termin_{i:02d}"

    profiler.profile_episode(
        subs_text_sample="Bohater_A: Look at the Radiant Beast!",
        existing_glossary=glossary_seed,
    )

    assert len(captured_prompts) == 1
    sent_prompt = captured_prompts[0]
    assert "UTRWALONY GLOSARIUSZ SEZONU" in sent_prompt
    assert "Radiant Beast => Promienista Bestia" in sent_prompt
    assert sent_prompt.count(" => ") <= 40


@pytest.mark.unit
def test_d1_genre_register_directive_adapts_to_comedy_drama_and_historical():
    """
    D-1: Dyrektywa rejestrowa w format_lean_episode_brief() dynamicznie dopasowuje się
    do gatunku: komedii, dramatu i historycznego puryzmu.
    """
    p_comedy = EpisodeProfile(tone_and_genre="Komedia / Slapstick", setting_and_era="Współczesne miasto")
    p_drama = EpisodeProfile(tone_and_genre="Dramat psychologiczny", setting_and_era="Szkoła średnia")
    p_hist = EpisodeProfile(tone_and_genre="Epopeja", setting_and_era="Feudalna epoka historyczna")

    b_comedy = format_lean_episode_brief(p_comedy)
    b_drama = format_lean_episode_brief(p_drama)
    b_hist = format_lean_episode_brief(p_hist)

    assert "Rejestr komediowy:" in b_comedy
    assert "historycznego" not in b_comedy
    assert "Rejestr dramatyczno-obyczajowy:" in b_drama
    assert "Puryzm rejestru historycznego:" in b_hist


# =====================================================================
# COMMIT 3: Zero-Cache SSOT Promptu, Deduplikacja SIGN i Wagi F2 (F-2/C-1, F-3, D-2)
# =====================================================================

@pytest.mark.unit
def test_f2_c1_zero_cache_ssot_preserves_all_context_without_duplication_or_raw_dicts(tmp_path):
    """
    F-2/C-1 (WARUNEK TWARDY §4.2):
    W trybie Zero-Cache Lean:
    1) wszystkie postacie obecne dokładnie 1x w pełnym prompcie F1 i F2,
    2) relacje obecne 1x,
    3) glosariusz kanoniczny obecny 1x,
    4) idiolekt per postać obecny 1x,
    5) zero surowych słowników Pythona ('gender':) w prompcie F2,
    6) spadek rozmiaru promptu o >= 20% względem wersji zduplikowanej.
    """
    bible_file = tmp_path / "f2_c1_bible.json"
    bible = SeriesBible(anime_title="Kronika Światła", bible_path=bible_file, storage_dir=tmp_path)
    bible.data["characters"] = {
        "Bohater_A": {
            "description": "Młody zwiadowca gildii.",
            "gender": "MALE",
            "grammatical_gender": "MASCULINE",
            "priority": "P0",
            "has_verified_gender": True,
            "aliases": [],
        },
        "Mistrzyni_B": {
            "description": "Dowódczyni straży miejskiej.",
            "gender": "FEMALE",
            "grammatical_gender": "FEMININE",
            "priority": "P0",
            "has_verified_gender": True,
            "aliases": [],
        },
        "Kupiec_C": {
            "description": "Sprzedawca relikwii na targu.",
            "gender": "MALE",
            "grammatical_gender": "MASCULINE",
            "priority": "P0",
            "has_verified_gender": True,
            "aliases": [],
        },
    }
    bible.data["relations"] = {
        "Bohater_A -> Mistrzyni_B": "Mówią sobie per ty po bitwie nad rzeką.",
    }
    bible.data["glossary"] = {
        "Radiant Beast": "Promienista Bestia",
        "Star Crest": "Gwiezdny Herb",
        "Iron Oath": "Żelazna Przysięga",
        "Crystal Gate": "Kryształowa Brama",
    }

    profile = EpisodeProfile(
        episode_summary="Wyprawa zwiadowcza przez Kryształową Bramę.",
        character_dossiers=[
            CharacterDossier(
                name="Bohater_A",
                gender="MALE",
                age_and_role="Zwiadowca gildii",
                speech_style_pl="krótkie cięte zdania",
                idiolect_matrix="unika ozdobników",
            ),
            CharacterDossier(
                name="Mistrzyni_B",
                gender="FEMALE",
                age_and_role="Dowódczyni straży",
                speech_style_pl="dostojna artykulacja",
                idiolect_matrix="zawsze opanowana",
            ),
        ],
        characters=[
            CharacterRelationship(
                speaker="Bohater_A",
                listener="Mistrzyni_B",
                address_form="per ty",
                relationship_type="sojusznicy",
            )
        ],
        glossary=[
            GlossaryTerm(term_en="Radiant Beast", translation_pl="Promienista Bestia", explanation="potwór"),
            GlossaryTerm(term_en="Star Crest", translation_pl="Gwiezdny Herb", explanation="symbol"),
            GlossaryTerm(term_en="Iron Oath", translation_pl="Żelazna Przysięga", explanation="rytuał"),
            GlossaryTerm(term_en="Crystal Gate", translation_pl="Kryształowa Brama", explanation="portal"),
        ],
    )

    glossary_str = GlossaryManager().format_for_prompt(bible.data["glossary"])
    legacy_bible_str = bible.format_for_prompt()
    legacy_brief_str = format_lean_episode_brief(profile, include_glossary=True)

    ssot_bible_str = _build_ssot_lean_bible_str(bible, episode_profile=profile)
    ssot_brief_str = format_lean_episode_brief(profile, include_glossary=False)

    tr = MultimodalTranslator(api_key="mock_k0", model="gemini-4-hydrogen", enable_verifier=True)
    raw_dict_registry = {
        "Bohater_A": bible.data["characters"]["Bohater_A"],
        "Mistrzyni_B": bible.data["characters"]["Mistrzyni_B"],
        "Kupiec_C": bible.data["characters"]["Kupiec_C"],
    }
    tr.character_registry = {
        "Bohater_A": bible.data["characters"]["Bohater_A"]["description"],
        "Mistrzyni_B": bible.data["characters"]["Mistrzyni_B"]["description"],
        "Kupiec_C": bible.data["characters"]["Kupiec_C"]["description"],
    }

    ev1 = pysubs2.SSAEvent(start=1000, end=3000, name="Bohater_A", text="The Radiant Beast is near the Crystal Gate.")
    ev2 = pysubs2.SSAEvent(start=3100, end=5000, name="Kupiec_C", text="Mistrzyni_B, guard the Star Crest.")
    batch = [(0, ev1, ev1.text, ""), (1, ev2, ev2.text, "")]

    # Zduplikowany (legacy) pełny prompt F1
    tr._episode_knowledge_cached = False
    f1_legacy_prompt = tr._prepare_batch_prompt(
        batch_events=batch,
        history_context=[],
        episode_profile_str=legacy_brief_str,
        episode_profile=None,  # brak dedup dossier
        series_bible_str=legacy_bible_str,
        glossary_str=glossary_str,
    )

    # Zero-Cache SSOT pełny prompt F1 (symulacja wiedzy jednorazowej w system_prompt + batch prompt)
    f1_ssot_system = "\n\n".join([glossary_str, ssot_bible_str, ssot_brief_str])
    tr._episode_knowledge_cached = True
    f1_ssot_batch = tr._prepare_batch_prompt(
        batch_events=batch,
        history_context=[],
        episode_profile_str=ssot_brief_str,
        episode_profile=profile,
        series_bible_str=ssot_bible_str,
        glossary_str=glossary_str,
    )
    f1_ssot_full = f1_ssot_system + "\n" + f1_ssot_batch

    # F2 prompt (clean_f2_registry vs surowy)
    verifier = tr.verifier
    f2_items = [
        {"id": 1, "en": ev1.text, "pl": "Promienista Bestia jest blisko Kryształowej Bramy.", "speaker_name": "Bohater_A", "visual_type": "DIALOG"},
        {"id": 2, "en": ev2.text, "pl": "Mistrzyni_B, strzeż Gwiezdnego Herbu.", "speaker_name": "Kupiec_C", "visual_type": "DIALOG"},
    ]
    f2_legacy_prompt = verifier._prepare_verification_prompt(
        batch_items=f2_items,
        episode_profile_str=legacy_brief_str,
        series_bible_str=legacy_bible_str,
        glossary_str=glossary_str,
        character_registry=raw_dict_registry,
    )
    clean_f2_reg = _build_clean_f2_character_registry(
        raw_dict_registry,
        episode_profile=profile,
        dedup_dossiers=True,
    )
    verifier._episode_knowledge_cached = True
    f2_ssot_user = verifier._prepare_verification_prompt(
        batch_items=f2_items,
        episode_profile_str=ssot_brief_str,
        series_bible_str=ssot_bible_str,
        glossary_str=glossary_str,
        character_registry=clean_f2_reg,
    )
    f2_ssot_full = f1_ssot_system + "\n" + f2_ssot_user

    # Asercje 1–6 (§4.2)
    # 1) Wszystkie postacie obecne w F1 i F2, postacie z dossier dokładnie 1x jako nagłówek definicji
    for full_p in (f1_ssot_full, f2_ssot_full):
        assert "Bohater_A" in full_p
        assert "Mistrzyni_B" in full_p
        assert "Kupiec_C" in full_p
    assert f1_ssot_full.count("- Bohater_A:") + f1_ssot_full.count("• Bohater_A:") == 1
    assert f1_ssot_full.count("- Mistrzyni_B:") + f1_ssot_full.count("• Mistrzyni_B:") == 1
    assert f2_ssot_full.count("- Bohater_A:") + f2_ssot_full.count("• Bohater_A:") == 1
    assert f2_ssot_full.count("- Mistrzyni_B:") + f2_ssot_full.count("• Mistrzyni_B:") == 1
    assert "Kupiec_C" in f2_ssot_user and "• Kupiec_C:" in f2_ssot_user

    # 2) Relacja mówca-adresat obecna 1x
    assert f1_ssot_full.count("Bohater_A -> Mistrzyni_B") >= 1
    assert f1_ssot_full.count("Mówią sobie per ty po bitwie nad rzeką.") == 1

    # 3) Glosariusz kanoniczny obecny dokładnie 1x (brak powtórzeń w system i brak duplikatu w user_prompt)
    assert f1_ssot_full.count("Żelazna Przysięga") == 1
    assert f2_ssot_full.count("Żelazna Przysięga") == 1
    assert f1_ssot_system.count("Promienista Bestia") == 1
    assert "BEZWZGLĘDNY SŁOWNICZEK" not in f2_ssot_user
    assert "• Zablokowana Terminologia:" not in f1_ssot_system

    # 4) Idiolekt per postać obecny dokładnie 1x
    assert f1_ssot_full.count("krótkie cięte zdania") == 1
    assert f1_ssot_full.count("dostojna artykulacja") == 1

    # 5) Brak surowych stringów dict Pythona w prompcie F2 SSOT (w odróżnieniu od legacy)
    assert "'gender':" in f2_legacy_prompt
    assert "'gender':" not in f2_ssot_user
    assert "'description':" not in f2_ssot_user

    # 6) Redukcja rozmiaru >= 20% względem wersji zduplikowanej
    total_legacy = len(f1_legacy_prompt) + len(f2_legacy_prompt)
    total_ssot = len(f1_ssot_full) + len(f2_ssot_user)
    assert total_ssot <= 0.80 * total_legacy


@pytest.mark.unit
def test_f3_episode_sign_dedup_preserves_per_event_timing_alignment_and_all_caps():
    """
    F-3 (WARUNEK TWARDY §4.3):
    10 identycznych napisów ALL CAPS 'KRZYK_X!!' z różnymi timestampami, warstwami i tagami
    \\an7/\\an8/\\an9 redukuje się do 1 wywołania API, a na zapisie odtwarza wszystkie 10 eventów
    z własnym start/end/layer/alignment i wymuszonym ALL CAPS.
    """
    subs = pysubs2.SSAFile()
    subs.styles["Default"] = pysubs2.SSAStyle()
    subs.styles["Signs"] = pysubs2.SSAStyle()

    alignments = [r"{\an7}", r"{\an8}", r"{\an9}"]
    raw_all_entries = []
    for idx in range(10):
        align_tag = alignments[idx % 3]
        ev = pysubs2.SSAEvent(
            start=1000 + idx * 1200,
            end=1800 + idx * 1200,
            layer=idx % 4,
            style="Signs",
            name="Sign",
            text=f"{align_tag}KRZYK_X!!",
        )
        subs.events.append(ev)
        ts_pref, clean_txt = extract_typesetting_tags(ev.text)
        raw_all_entries.append((idx, ev, clean_txt, ts_pref))

    dlg_ev = pysubs2.SSAEvent(start=15000, end=17000, style="Default", name="Bohater_A", text="Idziemy dalej.")
    subs.events.append(dlg_ev)
    raw_all_entries.append((10, dlg_ev, "Idziemy dalej.", ""))

    report = StyleMatrixReport(subs)
    raw_entries, sub_to_master, all_caps_masters = _deduplicate_episode_signs(raw_all_entries, style_report=report)

    assert len(raw_entries) == 2  # 1 master sign + 1 dialogue (9 API calls saved)
    sign_master_id = raw_entries[0][0]
    assert sign_master_id in all_caps_masters

    # Symulacja zapisu z mieszaną wielkością liter zwróconą przez LLM
    translated_results = {sign_master_id: "krzyk_x!!", 10: "Idziemy dalej."}
    rebuilt_events = []
    for orig_idx, orig_ev, _, ts_prefix in raw_all_entries:
        master_id = sub_to_master[orig_idx]
        text_pl = sanitize_sub_text(translated_results[master_id])
        if master_id in all_caps_masters or orig_idx in all_caps_masters:
            text_pl = text_pl.upper()
        prefix_clean = sanitize_ts_prefix_for_translation(ts_prefix)
        out_ev = orig_ev.copy()
        out_ev.text = f"{prefix_clean}{text_pl}"
        rebuilt_events.append(out_ev)

    assert len(rebuilt_events) == 11
    for idx in range(10):
        expected_align = alignments[idx % 3]
        assert rebuilt_events[idx].start == 1000 + idx * 1200
        assert rebuilt_events[idx].end == 1800 + idx * 1200
        assert rebuilt_events[idx].layer == idx % 4
        assert rebuilt_events[idx].text.startswith(expected_align)
        assert "KRZYK_X!!" in rebuilt_events[idx].text


@pytest.mark.unit
def test_d2_f2_selector_prioritizes_stylistic_pivots_over_trivial_short_replies():
    """
    D-2: Krótka 1-słowna replika w oknie przełomu relacji nie otrzymuje premii +25,
    natomiast rozbudowana kwestia w przełomie / z grą słowną / w scenie komediowej
    systematycznie przewyższa trywialne repliki <= 3 słów.
    """
    short_trivial_in_pivot = {
        "en": "Yes.",
        "pl": "Tak.",
        "notes": "[🔄 PRZEŁOM RELACJI]",
        "active_scene_tone": "komedia",
        "calque_score": 0.0,
    }
    long_pivot_line = {
        "en": "From this moment on, drop the formalities and call me by name.",
        "pl": "Od tej chwili daruj sobie formalności i mów mi po imieniu.",
        "notes": "[🔄 PRZEŁOM RELACJI (Bohater_A -> Mistrzyni_B)]",
        "active_scene_tone": "komedia i wzruszenie",
        "calque_score": 0.0,
    }
    pun_profiler_line = {
        "en": "Watch that pun land cleanly.",
        "pl": "Patrz, jak ta gra słów ładnie trafia.",
        "notes": "[🃏 GRA SŁOWNA: trafny żart]",
        "active_scene_tone": "komedia",
        "calque_score": 0.0,
    }

    s_short, _ = MultimodalTranslator._score_phase2_editorial_risk(short_trivial_in_pivot)
    s_pivot, _ = MultimodalTranslator._score_phase2_editorial_risk(long_pivot_line)
    s_pun, _ = MultimodalTranslator._score_phase2_editorial_risk(pun_profiler_line)

    assert s_short == 0
    assert s_pivot >= 40
    assert s_pun >= 50
    assert s_pivot > s_short
    assert s_pun > s_short


@pytest.mark.unit
def test_d2_offline_recall_on_representative_edited_vs_null_lines():
    """
    D-2 (WARUNEK TWARDY §4.6): Offline'owy test przypomnienia (recall >= 0.85 na 47 edytowanych liniach,
    100% pokrycia DEF-03 i danger_lines, redukcja trywialnych replik <= 3 słów w null o >= 40%).
    """
    tr = MultimodalTranslator(api_key="mock_k0", model="gemini-4-hydrogen", enable_verifier=True)

    trivial_null_items = [
        {
            "en": "Right." if idx % 2 == 0 else "Wait up.",
            "pl": "Jasne." if idx % 2 == 0 else "Zaczekaj.",
            "speaker_name": f"Postac_{idx % 4}",
            "calque_score": 0.0,
            "notes": "",
            "active_scene_tone": "spokojna rozmowa" if idx % 2 == 0 else "komedia",
            "_group": "trivial_null",
        }
        for idx in range(90)
    ]
    medium_null_items = [
        {
            "en": "We should prepare the camp before nightfall settles in the valley.",
            "pl": "Musimy przygotować obóz, zanim w dolinie zapadnie noc.",
            "speaker_name": f"Postac_{idx % 4}",
            "calque_score": 0.0,
            "notes": "",
            "active_scene_tone": "spokojna rozmowa",
            "_group": "medium_null",
        }
        for idx in range(90)
    ]

    edited_groups = []
    # 8 danger_lines_prescan
    for _ in range(8):
        edited_groups.append([{
            "en": "He could not care less about the rumor spreading across the capital.",
            "pl": "Wcielono w życie plotkę w stolicy zupełnie bez sensu.",
            "speaker_name": "Bohater_A",
            "calque_score": 0.15,
            "notes": "[TELEMETRIA: pułapka_profilera: idiom | wskazówka: naturalna odmowa]",
            "active_scene_tone": "dramat",
            "_group": "danger",
        }])
    # 7 DEF-03 (pary: poprzednik + wejście nowego mówcy małą literą)
    for _ in range(7):
        edited_groups.append([
            {
                "en": "Wait here...",
                "pl": "Zaczekaj...",
                "speaker_name": "Bohater_A",
                "calque_score": 0.0,
                "notes": "",
                "_group": "def03_prev",
            },
            {
                "en": "until we return.",
                "pl": "aż wrócimy.",
                "speaker_name": "Mistrzyni_B",
                "calque_score": 0.0,
                "notes": "",
                "_group": "def03",
            },
        ])
    # 12 linii z przełomem relacji + tonem dramatycznym/komediowym
    for _ in range(12):
        edited_groups.append([{
            "en": "Do not speak like that when everyone from our squad is listening.",
            "pl": "Nie mów tak, skoro wszyscy z oddziału nas teraz słuchają.",
            "speaker_name": "Mistrzyni_B",
            "calque_score": 0.0,
            "notes": "[🔄 PRZEŁOM RELACJI (Bohater_A -> Mistrzyni_B): przejście na ty]",
            "active_scene_tone": "dramatyczne napięcie",
            "_group": "edited",
        }])
    # 20 linii z wysoką kalką lub ostrzeżeniem CPS
    for i in range(20):
        edited_groups.append([{
            "en": "I guess we might as well make up our minds before the bell rings.",
            "pl": "Zgaduję że moglibyśmy równie dobrze zdecydować przed dzwonkiem.",
            "speaker_name": "Kupiec_C",
            "calque_score": 0.55 if i % 2 == 0 else 0.1,
            "cps_warning": "CPS > 17" if i % 2 == 1 else "",
            "notes": "",
            "_group": "edited",
        }])

    # Rozkład chronologiczny na 6 paczek (symulacja realnego odcinka)
    batches = [[] for _ in range(6)]
    for idx, it in enumerate(trivial_null_items):
        batches[idx % 6].append(it)
    for idx, it in enumerate(medium_null_items):
        batches[idx % 6].append(it)
    for idx, grp in enumerate(edited_groups):
        batches[idx % 6].extend(grp)

    items = []
    edited_ids = set()
    danger_ids = set()
    def03_ids = set()
    trivial_null_ids = set()

    for b in batches:
        for it in b:
            lid = len(items) + 1
            it["id"] = lid
            it["orig_idx"] = lid - 1
            grp = it.pop("_group")
            items.append(it)
            if grp == "trivial_null":
                trivial_null_ids.add(lid)
            elif grp == "danger":
                edited_ids.add(lid)
                danger_ids.add(lid)
            elif grp == "def03":
                edited_ids.add(lid)
                def03_ids.add(lid)
            elif grp == "edited":
                edited_ids.add(lid)

    selected_all = []
    for batch in batches:
        selected_all.extend(tr._select_hydrogen_phase2_candidates(batch, total_batches=6, episode_line_cap=115))

    selected_ids = {it["id"] for it in selected_all}
    recalled_edited = len(edited_ids & selected_ids) / float(len(edited_ids))

    assert len(edited_ids) == 47
    assert recalled_edited >= 0.85
    assert danger_ids.issubset(selected_ids)
    assert def03_ids.issubset(selected_ids)

    trivial_selected = len(trivial_null_ids & selected_ids)
    assert trivial_selected <= 0.60 * len(trivial_null_ids)


# =====================================================================
# COMMIT 4: Konsolidacja F2 (F-1) i Thread-Safe Obserwator F2 (H-3 / OBS-06)
# =====================================================================

class _DummyPbarF2:
    def write(self, msg: str) -> None:
        pass

    def set_postfix_str(self, s: str) -> None:
        pass

    def refresh(self) -> None:
        pass

    def update(self, n: int = 1) -> None:
        pass


def _make_mock_genai_client(handler) -> genai.Client:
    http_client = httpx.Client(transport=httpx.MockTransport(handler))
    c = genai.Client(api_key="test_k0", http_options=genai_types.HttpOptions(httpx_client=http_client))
    if getattr(c._api_client, "_httpx_client", None) is not http_client:
        c._api_client._httpx_client = http_client
    return c


@pytest.mark.unit
def test_f1_phase2_consolidation_merges_batches_and_maps_results_back_losslessly(monkeypatch):
    """
    F-1: 8 paczek F1 (po 14 kandydatów F2 = 112 linii) konsoliduje się w <= 3 wywołania F2
    (<= 48 linii każde), a _execute_consolidated_phase2_group + _process_phase2_only bezstratnie
    odtwarza wszystkie 112 wyników do oryginalnych paczek i oryginalnych ID linii.
    """
    monkeypatch.setenv("AVT_CONSOLIDATE_F2", "1")
    monkeypatch.setattr("time.sleep", lambda s: None)
    monkeypatch.setattr("client_factory.global_rate_limiter.acquire", lambda: None)

    def handler(request: httpx.Request) -> httpx.Response:
        raw_req = json.loads(request.content.decode("utf-8"))
        prompt_txt = str(raw_req)
        import re as _re
        ids_found = sorted({int(m) for m in _re.findall(r"\[LINIA #(\d+)\]", prompt_txt)})
        if not ids_found:
            ids_found = list(range(1, 49))
        lines_out = [
            {"id": lid, "refined_pl": f"Szlif_cons_{lid}", "changes_made": "Redakcja"}
            for lid in ids_found
        ]
        body = {
            "candidates": [{"content": {"role": "model", "parts": [{"text": json.dumps({"lines": lines_out})}]}}],
            "usageMetadata": {"promptTokenCount": 14000, "cachedContentTokenCount": 0, "candidatesTokenCount": 400, "thoughtsTokenCount": 80},
        }
        return httpx.Response(200, json=body)

    tr = MultimodalTranslator(api_key="mock_k0", model="gemini-4-hydrogen", enable_verifier=True)
    mock_c = _make_mock_genai_client(handler)
    tr.verifier.client_pool.clients = [mock_c]
    tr.verifier.client = mock_c

    phase1_outputs = {}
    for b_idx in range(8):
        p1_items = []
        untranslated = []
        for local_i in range(1, 29):
            orig_i = b_idx * 28 + (local_i - 1)
            ev = pysubs2.SSAEvent(start=orig_i * 1000, end=orig_i * 1000 + 800, text=f"Source sentence {orig_i}.", name="Bohater_A")
            untranslated.append((orig_i, ev, ev.text, ""))
            p1_items.append({
                "id": local_i,
                "orig_idx": orig_i,
                "event": ev,
                "style": "Default",
                "en": f"We might as well test line {orig_i} right now.",
                "pl": f"Draft_b{b_idx}_id{local_i}",
                "speaker": "Bohater_A",
                "speaker_name": "Bohater_A",
                "calque_score": 0.65 if local_i <= 14 else 0.0,
                "notes": "",
                "is_sign": False,
                "is_song": False,
            })
        phase1_outputs[b_idx] = {
            "b_idx": b_idx,
            "pass1_items": p1_items,
            "untranslated_in_batch": untranslated,
            "scene_desc": f"Scena {b_idx}",
            "batch_response": types.SimpleNamespace(scene_diagnosis=f"Diagnoza sceny {b_idx}"),
            "lookback_history": [],
            "lookahead_events": [],
            "scoped_series_bible_str": "",
            "user_feedback_str": "",
            "glossary_str": "",
            "episode_profile_str": "",
            "manga_canon_str": "",
            "batch_glossary_items": [],
            "speakers_on_ty": set(),
            "scene_has_first_name_vocative": False,
            "is_ass": True,
            "pbar": _DummyPbarF2(),
            "combined_glossary": {},
            "all_user_rules": [],
            "episode_profile": None,
            "total_batches": 8,
        }

    groups = tr._consolidate_phase2_batches(phase1_outputs, max_lines_per_f2_call=48)
    assert 2 <= len(groups) <= 3
    total_cons_lines = sum(len(g["verifier_items"]) for g in groups)
    assert total_cons_lines == 112
    assert all(len(g["verifier_items"]) <= 48 for g in groups)
    assert all(g.get("scene_diagnosis") is None or isinstance(g.get("scene_diagnosis"), dict) for g in groups)
    assert any(
        isinstance(g.get("scene_diagnosis"), dict)
        and "--- ZMIANA SCENY ---" in (g["scene_diagnosis"].get("dramatic_context") or "")
        for g in groups
    )

    mapped_all = {}
    for g in groups:
        res_map = tr._execute_consolidated_phase2_group(g)
        for ob, rlist in res_map.items():
            mapped_all.setdefault(ob, []).extend(rlist)

    restored_count = 0
    for b_idx in range(8):
        b_out = tr._process_phase2_only(
            phase1_outputs[b_idx],
            preverified_refined_lines=mapped_all.get(b_idx, []),
            skip_verifier_call=True,
        )
        res_dict = b_out[1]
        assert len(res_dict) == 28
        for local_i in range(1, 15):
            orig_i = b_idx * 28 + (local_i - 1)
            assert res_dict[orig_i].startswith("Szlif_cons_")
            restored_count += 1
    assert restored_count == 112


@pytest.mark.unit
def test_f1_consolidation_respects_rollback_env_flag_and_non_hydrogen_path(monkeypatch):
    """
    F-1: AVT_CONSOLIDATE_F2=0 wyłącza konsolidację F2 (bezstratny powrót do trybu 1:1),
    a model spoza rodziny Hydrogen nie uruchamia konsolidacji.
    """
    dummy_outputs = {
        i: {
            "b_idx": i,
            "pass1_items": [{"id": 1, "en": "Long test sentence here.", "pl": "Długie zdanie testowe.", "calque_score": 0.6}],
        }
        for i in range(4)
    }

    tr_h = MultimodalTranslator(api_key="mock_k0", model="gemini-4-hydrogen", enable_verifier=True)
    monkeypatch.setenv("AVT_CONSOLIDATE_F2", "0")
    assert tr_h._consolidate_phase2_batches(dummy_outputs) == []

    monkeypatch.setenv("AVT_CONSOLIDATE_F2", "1")
    tr_flash = MultimodalTranslator(api_key="mock_k0", model="gemini-3.8-flash", enable_verifier=True)
    assert tr_flash._consolidate_phase2_batches(dummy_outputs) == []


@pytest.mark.unit
def test_h3_obs06_phase2_retry_observer_is_thread_safe_under_parallel_workers(tmp_path, monkeypatch):
    """
    H-3 (OBS-06): Równoległe wątki F2 korzystające ze wspólnej puli client_pool raportują błędy
    przez dispatcher threading.local() bez wzajemnego nadpisywania batch_id i z czystym przywróceniem hooka.
    """
    monkeypatch.setattr("time.sleep", lambda s: None)
    monkeypatch.setattr("client_factory.global_rate_limiter.acquire", lambda: None)
    monkeypatch.setattr("context_cache.ContextCacheManager.get_or_create_cache", lambda *a, **kw: "__IMPLICIT_CACHE_95__")

    barrier = threading.Barrier(2, timeout=5)
    thread_attempts = {}
    tlock = threading.Lock()

    def handler(request: httpx.Request) -> httpx.Response:
        prompt_txt = request.content.decode("utf-8", errors="ignore")
        b_tag = 1 if "Line from batch 1." in prompt_txt else 2
        with tlock:
            cnt = thread_attempts.get(b_tag, 0) + 1
            thread_attempts[b_tag] = cnt
        if cnt == 1:
            barrier.wait()
            return httpx.Response(
                503,
                json={"error": {"code": 503, "message": "Overloaded.", "status": "UNAVAILABLE"}},
            )
        return httpx.Response(
            200,
            json={
                "candidates": [{"content": {"role": "model", "parts": [{"text": json.dumps({"lines": [{"id": 1, "refined_pl": f"Po szlifie {b_tag}.", "changes_made": "Styl"}]})}]}}],
                "usageMetadata": {"promptTokenCount": 800, "cachedContentTokenCount": 0, "candidatesTokenCount": 80, "thoughtsTokenCount": 20},
            },
        )

    tr = MultimodalTranslator(api_key="mock_k0", model="gemini-4-hydrogen", enable_verifier=True)
    mock_c = _make_mock_genai_client(handler)
    tr.verifier.client_pool.clients = [mock_c]
    tr.verifier.client = mock_c
    orig_report = tr.verifier.client_pool.report_error

    rec = EpisodeFlightRecorder(anime_slug="obs06_series", filename="ep01", trace_dir=tmp_path, enabled=True)
    tr.flight_recorder = rec

    def _run_worker(b_idx: int):
        ev = pysubs2.SSAEvent(start=1000, end=2500, text=f"Line from batch {b_idx}.", name="Bohater_A")
        p1_data = {
            "b_idx": b_idx,
            "pass1_items": [{
                "id": 1, "orig_idx": b_idx, "event": ev, "style": "Default",
                "en": f"Line from batch {b_idx}.", "pl": f"Szkic {b_idx}.",
                "speaker": "Bohater_A", "speaker_name": "Bohater_A",
                "is_sign": False, "is_song": False, "calque_score": 0.5, "notes": "",
            }],
            "untranslated_in_batch": [(b_idx, ev, ev.text, "")],
            "scene_desc": f"Scene {b_idx}", "batch_response": None,
            "lookback_history": [], "lookahead_events": [],
            "scoped_series_bible_str": "", "user_feedback_str": "", "glossary_str": "",
            "episode_profile_str": "", "manga_canon_str": "", "batch_glossary_items": [],
            "speakers_on_ty": set(), "scene_has_first_name_vocative": False,
            "is_ass": True, "pbar": _DummyPbarF2(), "combined_glossary": {},
            "all_user_rules": [], "episode_profile": None, "total_batches": 2,
        }
        return tr._process_phase2_only(p1_data)

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        futs = [pool.submit(_run_worker, 1), pool.submit(_run_worker, 2)]
        for f in concurrent.futures.as_completed(futs):
            f.result()

    assert tr.verifier.client_pool.report_error == orig_report
    events = [json.loads(line) for line in rec.jsonl_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    retry_batches = sorted(ev["batch_id"] for ev in events if ev.get("stage") == "retry")
    assert retry_batches == [1, 2]


@pytest.mark.unit
def test_g1_tm_quality_tier_migration_and_priority_ranking(tmp_path):
    """
    G-1: Idempotentna migracja starej tabeli translation_pairs do schematu z kolumną quality_tier
    oraz hierarchia autorytetu: tier=1 (human edit) > tier=2 (legacy) > tier=3 (AI auto-ingest).
    """
    import sqlite3
    from memory import TranslationMemory

    db_path = tmp_path / "legacy_tm.db"
    # Utwórz starszy schemat bez kolumny quality_tier
    with sqlite3.connect(db_path) as conn:
        conn.execute("""
            CREATE TABLE translation_pairs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                en_text TEXT NOT NULL,
                pl_text TEXT NOT NULL,
                en_clean TEXT NOT NULL,
                anime_title TEXT,
                word_count INTEGER
            )
        """)
        conn.execute(
            "INSERT INTO translation_pairs (en_text, pl_text, en_clean, anime_title, word_count) VALUES (?, ?, ?, ?, ?)",
            ("We must reach the northern fortress today.", "Musimy dziś dotrzeć do północnej twierdzy.", "we must reach the northern fortress today.", "LegacySeries", 7),
        )
        conn.commit()

    tm = TranslationMemory(db_path=db_path)
    with sqlite3.connect(db_path) as conn:
        cols = {row[1] for row in conn.execute("PRAGMA table_info(translation_pairs)").fetchall()}
        assert "quality_tier" in cols
        legacy_tier = conn.execute("SELECT quality_tier FROM translation_pairs WHERE anime_title = 'LegacySeries'").fetchone()[0]
        assert legacy_tier == 2

    # Wpis AI (tier=3) nie może nadpisać starszego wpisu tier=2 ani nowego tier=1
    changed_downgrade = tm.ingest_episode_pairs(
        [{"en": "We must reach the northern fortress today.", "pl": "Słabszy automatyczny przekład twierdzy."}],
        series_title="LegacySeries",
        quality_tier=3,
    )
    assert changed_downgrade == 0

    # Dodaj ten sam tekst EN w innej serii jako tier=3 i jako tier=1, aby porównać ranking
    tm.ingest_episode_pairs(
        [{"en": "Please guard the eastern gate tonight.", "pl": "Proszę pilnować wschodniej bramy dziś w nocy."}],
        series_title="SeriesBeta",
        quality_tier=3,
    )
    tm.ingest_episode_pairs(
        [{"en": "Please guard the eastern gate tonight.", "pl": "Strzeż wschodniej bramy dzisiejszej nocy."}],
        series_title="SeriesAlpha",
        quality_tier=1,
    )
    results = tm.find_relevant_examples(["Please guard the eastern gate tonight."], max_examples=5)
    assert len(results) >= 2
    assert results[0]["anime"] == "SeriesAlpha"
    assert results[0]["quality_tier"] == 1
    assert results[0]["score"] > results[1]["score"]

    # Korekta ludzka (tier=1) promuje i aktualizuje istniejący wpis tier=3
    promoted = tm.ingest_episode_pairs(
        [{"en": "Please guard the eastern gate tonight.", "pl": "Przypilnuj proszę wschodniej bramy tej nocy."}],
        series_title="SeriesBeta",
        quality_tier=1,
    )
    assert promoted == 1
    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            "SELECT pl_text, quality_tier FROM translation_pairs WHERE anime_title = 'SeriesBeta'"
        ).fetchone()
        assert row[0] == "Przypilnuj proszę wschodniej bramy tej nocy."
        assert row[1] == 1


@pytest.mark.unit
def test_g1_auto_ingest_skips_signs_songs_and_short_lines(tmp_path, monkeypatch):
    """
    G-1: ingest_episode_pairs oraz MultimodalTranslator._auto_ingest_episode_to_tm
    odfiltrowują plansze (is_sign), piosenki (is_song), staff, surowe tagi ASS/HTML i krótkie kwestie (< 3 słowa),
    a flaga AVT_TM_AUTO_INGEST=0 całkowicie wyłącza zapis automatyczny.
    """
    from memory import TranslationMemory

    db_path = tmp_path / "auto_ingest.db"
    tm = TranslationMemory(db_path=db_path)

    tr = MultimodalTranslator(api_key="mock_k0", model="gemini-4-hydrogen", enable_verifier=False)
    tr.tm = tm

    subs = pysubs2.SSAFile()
    subs.styles["Sign"] = pysubs2.SSAStyle()
    subs.styles["Karaoke"] = pysubs2.SSAStyle()

    ev_ok = pysubs2.SSAEvent(start=1000, end=3000, text=r"{\i1}Ten miecz pamięta dawne czasy.{\i0}", style="Default")
    ev_ok.source_en = "This sword remembers old times."
    ev_short = pysubs2.SSAEvent(start=3500, end=4500, text="Tak, rozumiem.", style="Default")
    ev_short.source_en = "Yes, okay."
    ev_sign = pysubs2.SSAEvent(start=5000, end=7000, text=r"{\an8}KRÓLEWSKA AKADEMIA MAGII", style="Sign")
    ev_sign.source_en = "ROYAL ACADEMY OF MAGIC"
    ev_song = pysubs2.SSAEvent(start=8000, end=10000, text="Singing under the silver moon tonight.", style="Karaoke")
    ev_song.source_en = "Singing under the silver moon tonight."
    ev_uncleaned = pysubs2.SSAEvent(start=11000, end=13000, text="<i>Uncleaned html remains inside line.</i>", style="Default")
    ev_uncleaned.source_en = "Clean English source sentence here."
    ev_qg_bad = pysubs2.SSAEvent(start=14000, end=16000, text="Tego problemu nie wykryto wcześniej tutaj.", style="Default")
    ev_qg_bad.source_en = "Unresolved English sentence warning marker."

    subs.events = [ev_ok, ev_short, ev_sign, ev_song, ev_uncleaned, ev_qg_bad]

    # Najpierw z AVT_TM_AUTO_INGEST=0 -> 0 zapisanych par
    monkeypatch.setenv("AVT_TM_AUTO_INGEST", "0")
    assert tr._auto_ingest_episode_to_tm(subs, qg_fixes=["Linia: nieprzetłumaczony angielski: Unresolved English sentence"], subs_file=Path("SyntheticEp01.ass")) == 0

    # Teraz z włączonym auto-ingestem -> wyłącznie czysta linia dialogowa ev_ok
    monkeypatch.setenv("AVT_TM_AUTO_INGEST", "1")
    ingested = tr._auto_ingest_episode_to_tm(
        subs,
        qg_fixes=["Linia: nieprzetłumaczony angielski: Unresolved English sentence warning marker."],
        subs_file=Path("SyntheticEp01.ass"),
    )
    assert ingested == 1

    import sqlite3
    with sqlite3.connect(db_path) as conn:
        rows = conn.execute("SELECT en_text, pl_text, quality_tier FROM translation_pairs").fetchall()
        assert len(rows) == 1
        assert rows[0][0] == "This sword remembers old times."
        assert rows[0][1] == "Ten miecz pamięta dawne czasy."
        assert rows[0][2] == 3


@pytest.mark.unit
def test_g2_learn_from_edits_cli_ingests_user_diff_to_feedback_and_tm_tier1(tmp_path):
    """
    G-2: Samodzielne narzędzie CLI tools/learn_from_edits.py wyciąga różnice między --raw i --edited
    do UserFeedbackManager oraz promuje poprawione pary do TranslationMemory z quality_tier=1.
    """
    import sqlite3
    import subprocess
    from memory import TranslationMemory

    en_path = tmp_path / "ep01.en.ass"
    raw_path = tmp_path / "ep01_raw.ass"
    edited_path = tmp_path / "ep01_edited.ass"
    fb_path = tmp_path / "feedback.json"
    tm_path = tmp_path / "tm_cli.db"

    subs_en = pysubs2.SSAFile()
    subs_raw = pysubs2.SSAFile()
    subs_edited = pysubs2.SSAFile()

    for subs_obj, lines in (
        (
            subs_en,
            [
                (1000, 3000, "That idea makes total sense to me."),
                (4000, 6000, "We will depart at dawn tomorrow."),
            ],
        ),
        (
            subs_raw,
            [
                (1000, 3000, "Ten pomysł robi kompletny sens dla mnie."),
                (4000, 6000, "Wyruszymy jutro o samym świcie."),
            ],
        ),
        (
            subs_edited,
            [
                (1000, 3000, "Ten pomysł ma dla mnie całkowity sens."),
                (4000, 6000, "Wyruszymy jutro o samym świcie."),
            ],
        ),
    ):
        for s_ms, e_ms, txt in lines:
            subs_obj.events.append(pysubs2.SSAEvent(start=s_ms, end=e_ms, text=txt, style="Default"))

    subs_en.save(str(en_path), encoding="utf-8")
    subs_raw.save(str(raw_path), encoding="utf-8")
    subs_edited.save(str(edited_path), encoding="utf-8")

    # Pre-seed TM wpisami tier=3
    tm = TranslationMemory(db_path=tm_path)
    tm.ingest_episode_pairs(
        [
            {"en": "That idea makes total sense to me.", "pl": "Ten pomysł robi kompletny sens dla mnie."},
            {"en": "We will depart at dawn tomorrow.", "pl": "Wyruszymy jutro o samym świcie."},
        ],
        series_title="Synthetic Chronicle",
        quality_tier=3,
    )

    cmd = [
        sys.executable,
        str(Path(__file__).resolve().parent.parent / "tools" / "learn_from_edits.py"),
        "--raw", str(raw_path),
        "--edited", str(edited_path),
        "--en", str(en_path),
        "--series", "Synthetic Chronicle",
        "--scope", "series",
        "--feedback-file", str(fb_path),
        "--tm-db", str(tm_path),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    assert proc.returncode == 0, f"CLI failed: {proc.stderr}\n{proc.stdout}"
    assert "quality_tier=1" in proc.stdout

    fb_data = json.loads(fb_path.read_text(encoding="utf-8"))
    matched_fb = [e for e in fb_data if e.get("bad_pl") == "Ten pomysł robi kompletny sens dla mnie."]
    assert len(matched_fb) == 1
    assert matched_fb[0]["good_pl"] == "Ten pomysł ma dla mnie całkowity sens."
    assert matched_fb[0]["scope"] == "series"

    with sqlite3.connect(tm_path) as conn:
        row_edited = conn.execute(
            "SELECT pl_text, quality_tier FROM translation_pairs WHERE en_clean = ?",
            ("that idea makes total sense to me.",),
        ).fetchone()
        row_unchanged = conn.execute(
            "SELECT pl_text, quality_tier FROM translation_pairs WHERE en_clean = ?",
            ("we will depart at dawn tomorrow.",),
        ).fetchone()
        assert row_edited == ("Ten pomysł ma dla mnie całkowity sens.", 1)
        assert row_unchanged == ("Wyruszymy jutro o samym świcie.", 3)


# =====================================================================
# HOTFIX 12.0.0a: Testy regresyjne BUG #1 .. BUG #5
# =====================================================================

@pytest.mark.unit
def test_bug1_a1_filter_handles_production_2_tuples_without_index_error():
    """
    BUG #1 (A-1): Produkcyjny translator.py:4990 przekazuje listę 2-krotek (b_id, SSAEvent)
    do _filter_dialogue_audio_events. Filtr nie może rzucać IndexError, zwraca 2-krotki
    i zachowuje wyłącznie DIALOGUE_BOTTOM oraz DIALOGUE_TOP.
    """
    subs = pysubs2.SSAFile()
    subs.styles["Default"] = pysubs2.SSAStyle()
    subs.styles["Main"] = pysubs2.SSAStyle(alignment=8)
    subs.styles["Sign"] = pysubs2.SSAStyle()
    subs.styles["OP"] = pysubs2.SSAStyle()

    ev_diag = pysubs2.SSAEvent(start=1000, end=2500, style="Default", name="Bohater_A", text="Idziemy na północ.")
    ev_top = pysubs2.SSAEvent(start=2600, end=4000, style="Main", name="Dialogue", text="{\\an8}Uwaga na patrol.")
    ev_sign = pysubs2.SSAEvent(start=4100, end=5000, style="Sign", name="Sign", text="WEJŚCIE")
    ev_song = pysubs2.SSAEvent(start=5100, end=7000, style="OP", name="Singer", text="Running into the bright horizon")
    ev_staff = pysubs2.SSAEvent(start=7100, end=8500, style="Sign", name="Sign", text="TYPESETTING: Zespół_Y")

    subs.events.extend([ev_diag, ev_top, ev_sign, ev_song, ev_staff])
    report = StyleMatrixReport(subs)

    prod_2_tuples = [(1, ev_diag), (2, ev_top), (3, ev_sign), (4, ev_song), (5, ev_staff)]
    filtered = _filter_dialogue_audio_events(prod_2_tuples, style_report=report)

    assert len(filtered) == 2
    assert all(isinstance(x, tuple) and len(x) == 2 for x in filtered)
    assert [x[0] for x in filtered] == [1, 2]
    assert filtered[0][1] is ev_diag
    assert filtered[1][1] is ev_top


@pytest.mark.unit
def test_bug2_f1_consolidated_scene_diagnosis_renders_in_verifier_prompt():
    """
    BUG #2 (F-1): _consolidate_phase2_batches przekazuje scene_diagnosis jako strukturalny dict
    oraz dołącza aktywny ton sekwencji (B-2) tak, aby chroniony verifier.py wyrenderował zarówno
    sekcję DIAGNOZA DRAMATURGICZNA I KOGNITYWNA SCENY z separatorem '--- ZMIANA SCENY ---',
    jak i aktywny ton sekwencji z Profilera.
    """
    tr = MultimodalTranslator(api_key="mock_k0", model="gemini-4-hydrogen", enable_verifier=True)
    ep_profile = EpisodeProfile(
        episode_summary="Odcinek testowy o negocjacjach w gildii.",
        dramatic_sequences=[
            DramaticSequence(
                sequence_name="Konfrontacja w Sali Rady",
                time_range="00:00 - 00:25",
                dramatic_summary="Bohater_A i Bohater_B ścierają się słownie przy stole obrad.",
                dominant_tone="chłodne napięcie dworskie",
            ),
        ],
    )

    phase1_outputs = {}
    for b_idx in range(3):
        start_base = b_idx * 4000 + 1000
        ev = pysubs2.SSAEvent(start=start_base, end=start_base + 2000, text=f"Proposal sentence {b_idx} must be reviewed.", name="Bohater_A")
        p1_items = [{
            "id": 1,
            "orig_idx": b_idx,
            "event": ev,
            "start_ms": ev.start,
            "end_ms": ev.end,
            "style": "Default",
            "en": ev.text,
            "pl": f"Propozycja {b_idx} wymaga rozważenia.",
            "speaker": "Bohater_A",
            "speaker_name": "Bohater_A",
            "calque_score": 0.70,
            "notes": "",
            "is_sign": False,
            "is_song": False,
        }]
        diag_obj = types.SimpleNamespace(
            dramatic_context=f"Rozmowa przy stole nr {b_idx}",
            dominant_tone="stanowczy i powściągliwy" if b_idx == 0 else "narastający sprzeciw",
            dialogue_flow=f"Replika {b_idx} prowadzi do impasu.",
            power_dynamic="Bohater_A dominuje",
        )
        phase1_outputs[b_idx] = {
            "b_idx": b_idx,
            "pass1_items": p1_items,
            "untranslated_in_batch": [(b_idx, ev, ev.text, "")],
            "scene_desc": f"Scena obrad {b_idx}",
            "batch_response": types.SimpleNamespace(scene_diagnosis=diag_obj),
            "episode_profile_str": "Brief odcinka.",
            "user_feedback_str": "",
            "glossary_str": "",
            "scoped_series_bible_str": "",
            "manga_canon_str": "",
            "episode_profile": ep_profile,
            "lookback_history": [],
            "lookahead_events": [],
            "pbar": _DummyPbarF2(),
        }

    groups = tr._consolidate_phase2_batches(phase1_outputs, max_lines_per_f2_call=48)
    assert len(groups) == 1
    cons_group = groups[0]
    assert isinstance(cons_group["scene_diagnosis"], dict)

    rendered_prompt = tr.verifier.verify_batch(
        batch_items=cons_group["verifier_items"],
        scene_summary=cons_group["scene_desc"],
        scene_diagnosis=cons_group["scene_diagnosis"],
        episode_profile_str=cons_group["episode_profile_str"],
        return_prompt=True,
    )
    assert "DIAGNOZA DRAMATURGICZNA I KOGNITYWNA SCENY" in rendered_prompt
    assert "--- ZMIANA SCENY ---" in rendered_prompt
    assert "chłodne napięcie dworskie" in rendered_prompt


@pytest.mark.unit
def test_bug3_ab_harness_reconstructs_full_events_jsonl_and_accumulates_live_tokens(tmp_path, monkeypatch, capsys):
    """
    BUG #3 (verify_f2_consolidation_ab.py): Rekonstrukcja pełnych paczek F1 z rzeczywistego schematu
    events.jsonl (scene_discourse + line_evolution + phase1_batch + phase2_verifier) bez placeholderów
    oraz poprawne sumowanie tokenów i dodatniej różnicy PLN w trybie --live.
    """
    import re as _re
    from tools.verify_f2_consolidation_ab import load_phase2_items_from_events, run_ab_comparison

    events_path = tmp_path / "synthetic_ep07_events.jsonl"
    records = []
    batches_summary = []
    for b_idx in range(4):
        first_id = b_idx * 20
        last_id = first_id + 19
        batches_summary.append({
            "batch_id": b_idx,
            "line_count": 20,
            "first_id": first_id,
            "last_id": last_id,
            "start_ms": first_id * 2000,
            "end_ms": (last_id + 1) * 2000,
        })
    records.append({
        "stage": "profile_prepass",
        "batch_id": None,
        "line_id": None,
        "payload": {"profile_brief": "Brief testowy: Bohater_A (mężczyzna)."},
    })
    records.append({"stage": "scene_discourse", "batch_id": None, "line_id": None, "payload": {"batches_summary": batches_summary}})

    for b_idx in range(4):
        records.append({
            "stage": "phase1_batch",
            "batch_id": b_idx,
            "line_id": None,
            "payload": {
                "batch_id": b_idx,
                "raw_response": {
                    "scene_diagnosis": {
                        "dramatic_context": f"Kontekst dramatyczny paczki {b_idx}",
                        "dominant_tone": "napięcie taktyczne",
                    }
                },
            },
        })
        p2_resp = []
        for local_i in range(1, 21):
            lid = b_idx * 20 + (local_i - 1)
            is_sign_row = (local_i == 1 and b_idx in (0, 1))
            records.append({
                "stage": "line_evolution",
                "batch_id": None,
                "line_id": lid,
                "payload": {
                    "line_id": lid,
                    "start_ms": lid * 2000,
                    "end_ms": lid * 2000 + 1800,
                    "actor": "sign" if is_sign_row else "Bohater_A",
                    "en_text": (
                        f"Northern academy grand hall ancient arcane emblem royal charter inscription banner archive board {lid}"
                        if is_sign_row
                        else f"We really might as well check gate sector {lid} carefully now."
                    ),
                    "jp_audio": "" if is_sign_row else f"JP audio {lid}",
                    "telemetry_tag": "[Mówca: sign (NEUTRAL)]" if is_sign_row else "[Mówca: Bohater_A (M)]",
                    "phase1_pl": (
                        f"[WIELKA SALA PÓŁNOCNEJ AKADEMII ARCHIWUM {lid}]"
                        if is_sign_row
                        else f"Naprawdę możemy teraz uważnie sprawdzić sektor {lid}."
                    ),
                    "phase2_pl": f"PO_F2_REFINED_{lid}",
                },
            })
            if local_i <= 6:
                p2_resp.append({"id": local_i, "refined_pl": f"PO_F2_REFINED_{lid}", "changes_made": "Styl"})
        records.append({
            "stage": "phase2_verifier",
            "batch_id": b_idx,
            "line_id": None,
            "payload": {"batch_id": b_idx, "raw_response": p2_resp},
        })

    events_path.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in records), encoding="utf-8")

    p1_outputs = load_phase2_items_from_events(events_path)
    assert len(p1_outputs) == 4
    assert "Brief testowy" in p1_outputs[0]["episode_profile_str"]
    reconstructed_lines = [it for b in sorted(p1_outputs) for it in p1_outputs[b]["pass1_items"]]
    assert len(reconstructed_lines) == 80
    assert all("placeholder text" not in it["en"].lower() for it in reconstructed_lines)
    assert all(not it["pl"].startswith("PO_F2_REFINED_") for it in reconstructed_lines)
    sign_lines = [it for it in reconstructed_lines if it.get("is_sign")]
    assert len(sign_lines) == 2
    assert all(it.get("visual_type") == "Napis ekranowy" for it in sign_lines)
    assert all(it.get("visual_type") == "Dialog" for it in reconstructed_lines if not it.get("is_sign"))

    monkeypatch.setenv("AVT_CONSOLIDATE_F2", "1")
    monkeypatch.setenv("GEMINI_API_KEY", "mock_live_key")
    monkeypatch.setattr("time.sleep", lambda s: None)
    monkeypatch.setattr("client_factory.global_rate_limiter.acquire", lambda: None)

    seen_prompt_markers = {"brief": False, "sign_tag": False}

    def handler(request: httpx.Request) -> httpx.Response:
        prompt_txt = str(json.loads(request.content.decode("utf-8")))
        if "Brief testowy: Bohater_A" in prompt_txt:
            seen_prompt_markers["brief"] = True
        if "[[Napis] Napis ekranowy]" in prompt_txt:
            seen_prompt_markers["sign_tag"] = True
        ids_found = sorted({int(m) for m in _re.findall(r"\[KWESTIA #(\d+)\]", prompt_txt)})
        if not ids_found:
            ids_found = [1]
        lines_out = [{"id": lid, "refined_pl": f"Szlif_{lid}.", "changes_made": "Styl"} for lid in ids_found]
        return httpx.Response(
            200,
            json={
                "candidates": [{"content": {"role": "model", "parts": [{"text": json.dumps({"lines": lines_out})}]}}],
                "usageMetadata": {"promptTokenCount": 14500, "cachedContentTokenCount": 0, "candidatesTokenCount": 420, "thoughtsTokenCount": 50},
            },
        )

    tr = MultimodalTranslator(api_key="mock_live_key", model="gemini-4-hydrogen", enable_verifier=True)
    mock_c = _make_mock_genai_client(handler)
    tr.verifier.client_pool.clients = [mock_c]
    tr.verifier.client = mock_c

    rc = run_ab_comparison(events_path, live=True, translator_obj=tr)
    assert rc == 0
    assert seen_prompt_markers["brief"] is True
    assert seen_prompt_markers["sign_tag"] is True
    out = capsys.readouterr().out
    m_cost = _re.search(r"Koszt F2 PLN netto: A=([0-9.]+) vs B=([0-9.]+) \(różnica=([0-9.-]+) PLN\)", out)
    assert m_cost is not None, f"Unexpected A/B output:\n{out}"
    cost_a = float(m_cost.group(1))
    cost_b = float(m_cost.group(2))
    assert cost_a > cost_b > 0.0


@pytest.mark.unit
def test_bug4_g1_auto_ingest_uses_series_bible_anime_title_for_same_series_lookup(tmp_path):
    """
    BUG #4 (G-1): _auto_ingest_episode_to_tm pobiera self.series_bible.anime_title zamiast nazwy pliku wideo,
    dzięki czemu odczyt w kolejnym odcinku z require_same_series=True zwraca trafienia.
    """
    from memory import TranslationMemory

    sb = SeriesBible(anime_title="Kronika Gwiazd S2", storage_dir=tmp_path)
    tm = TranslationMemory(db_path=tmp_path / "tm_bug4.db")

    tr = MultimodalTranslator(api_key="mock_k0", model="gemini-4-hydrogen", enable_verifier=False)
    tr.series_bible = sb
    tr.tm = tm

    subs = pysubs2.SSAFile()
    ev = pysubs2.SSAEvent(start=1000, end=3500, text="Musimy dziś w nocy strzec północnej bramy.", style="Default")
    ev.source_en = "We must protect the northern gate tonight."
    subs.events.append(ev)

    ingested = tr._auto_ingest_episode_to_tm(subs, video_path="[GROUP] Kodowy_Plik_07.mkv")
    assert ingested == 1

    hits = tm.find_relevant_examples(
        ["We must protect the northern gate tonight."],
        series_title=tr.series_bible.anime_title,
        require_same_series=True,
    )
    assert len(hits) >= 1
    assert hits[0]["anime"] == "Kronika Gwiazd S2"


@pytest.mark.unit
def test_bug5_f3_uppercase_preserving_ass_tags_keeps_inline_italics_and_newlines():
    """
    BUG #5 (F-3): _uppercase_preserving_ass_tags zamienia na wielkie litery wyłącznie widoczny tekst
    (w tym polskie znaki diakrytyczne), nie naruszając bloków {...} ani sekwencji \\N, \\n, \\h.
    """
    raw = r"{\i1}Gildia{\i0}\N{\b1}światła zaćmienia: ąćęłńóśźż{\b0}\nNowy\hwiersz"
    expected = r"{\i1}GILDIA{\i0}\N{\b1}ŚWIATŁA ZAĆMIENIA: ĄĆĘŁŃÓŚŹŻ{\b0}\nNOWY\hWIERSZ"
    assert _uppercase_preserving_ass_tags(raw) == expected
