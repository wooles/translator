"""
Zestaw nienaruszalnych, nietautologicznych testów regresyjnych dla Standardu 12.0.0:
- Commit 1 (5 testów): A-1, A-2, A-3, E-1, E-2
"""

import json
import types
import pytest
import pysubs2

from translator import (
    MultimodalTranslator,
    sanitize_sub_text,
    _filter_dialogue_audio_events,
)
import whisper_engine
from whisper_engine import JapaneseWhisperEngine
from style_matrix import StyleMatrixReport, EventRole
from series_memory import SeriesBible


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
