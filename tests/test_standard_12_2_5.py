# -*- coding: utf-8 -*-
"""
Standard 12.2.5 Regression Suite (OBS-28, OBS-07, librosa.pyin diarizer, E3, E4-bis — 0.00 PLN, 0 B diff Z16).
100% Z1-pure synthetic test suite operating on real production classes & methods.
"""

import json
from pathlib import Path
from typing import Any, List, Optional

import httpx
import numpy as np
import pysubs2
import pytest
from google import genai
from google.genai import types as genai_types

from pipeline_logger import EpisodeFlightRecorder
from profiler import DramaticSequence, EpisodeProfiler
from series_memory import SeriesBible
from speaker_diarizer import SpeakerVoiceClassifier
from translator import (
    BatchTranslationResponse,
    LineTranslation,
    MultimodalTranslator,
    SceneDiagnosis,
    _append_phase1_nonhuman_and_unknown_voice_rule,
    _is_nonhuman_speaker_label,
)


def _make_mock_genai_client(handler) -> genai.Client:
    http_client = httpx.Client(transport=httpx.MockTransport(handler))
    client = genai.Client(
        api_key="mock_k0",
        http_options=genai_types.HttpOptions(httpx_client=http_client),
    )
    if getattr(client._api_client, "_httpx_client", None) is not http_client:
        client._api_client._httpx_client = http_client
    return client


class _DummyPbar:
    def write(self, msg: str) -> None:
        pass

    def set_postfix_str(self, s: str) -> None:
        pass

    def update(self, n: int = 1) -> None:
        pass

    def refresh(self) -> None:
        pass


def _build_synthetic_bible(tmp_path: Path, include_male_bird: bool = False) -> SeriesBible:
    bible_file = tmp_path / "synthetic_1225_bible.json"
    sb = SeriesBible(bible_path=bible_file, storage_dir=tmp_path)
    chars = {
        "PostacAlfa": {
            "name": "PostacAlfa",
            "gender": "FEMALE",
            "grammatical_gender": "FEMININE",
            "confidence": 1.0,
            "priority": "P0",
            "has_verified_gender": True,
            "aliases": ["PostacAlfa"],
        },
        "PostacBeta": {
            "name": "PostacBeta",
            "gender": "FEMALE",
            "grammatical_gender": "FEMININE",
            "confidence": 1.0,
            "priority": "P0",
            "has_verified_gender": True,
            "aliases": ["PostacBeta"],
        },
        "BytNieludzkiAlfa": {
            "name": "BytNieludzkiAlfa",
            "gender": "UNKNOWN",
            "grammatical_gender": "UNKNOWN",
            "confidence": 0.0,
            "priority": "P2",
            "has_verified_gender": False,
            "aliases": ["BytNieludzkiAlfa"],
        },
    }
    if include_male_bird:
        chars["PtakKanoniczny"] = {
            "name": "PtakKanoniczny",
            "gender": "MALE",
            "grammatical_gender": "MASCULINE",
            "confidence": 1.0,
            "priority": "P0",
            "has_verified_gender": True,
            "aliases": ["PtakKanoniczny"],
        }
    sb.data["characters"] = chars
    sb._rebuild_actor_aliases_index()
    return sb


def _read_jsonl(path: Path) -> List[Any]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


# ------------------------------------------------------------------------------
# Test 1 (E4-bis.1 / OBS-28): Anonymous lines in female-only scene
# ------------------------------------------------------------------------------
@pytest.mark.unit
def test_e4bis1_anonymous_line_in_female_only_scene_does_not_force_p0_feminine(tmp_path: Path, monkeypatch):
    monkeypatch.setattr("time.sleep", lambda s: None)
    monkeypatch.setattr("client_factory.global_rate_limiter.acquire", lambda: None)
    monkeypatch.setattr("context_cache.ContextCacheManager.get_or_create_cache", lambda *a, **kw: "__IMPLICIT_CACHE_95__")

    sb = _build_synthetic_bible(tmp_path)

    resp_obj = BatchTranslationResponse(
        scene_diagnosis=SceneDiagnosis(
            dramatic_context="Syntetyczna scena z anonimowymi głosami",
            dialogue_flow="Dwóch nieznanych mówców",
            audio_intent_check="Rozdzielenie F0 i wizji",
            dominant_tone="Neutralny",
        ),
        translations=[
            LineTranslation(
                id=1,
                polish_text="Razem dotarliśmy na miejsce.",
                speaker_gender="UNKNOWN",
                speaker_name="",
                addressee=None,
            ),
            LineTranslation(
                id=2,
                polish_text="Zająłem się zabezpieczeniem drzwi.",
                speaker_gender="mężczyzna",
                speaker_name="",
                addressee=None,
            ),
        ],
    )
    payload_text = resp_obj.model_dump_json()

    def _handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "candidates": [{"content": {"role": "model", "parts": [{"text": payload_text}]}}],
                "usageMetadata": {
                    "promptTokenCount": 600,
                    "cachedContentTokenCount": 0,
                    "candidatesTokenCount": 90,
                    "thoughtsTokenCount": 0,
                },
            },
        )

    tr = MultimodalTranslator(api_key="mock_k0", model="gemini-4-hydrogen", enable_verifier=False)
    mock_c = _make_mock_genai_client(_handler)
    tr.client_pool_f1.clients = [mock_c]
    tr.client_pool.clients = [mock_c]
    tr.client = mock_c
    tr.series_bible = sb
    tr.character_registry = {"PostacAlfa": "kobieta (P0)", "PostacBeta": "kobieta (P0)"}
    tr.episode_scene_genders = {0: "kobieta", 1: "kobieta"}
    tr.scene_is_female_only = True
    tr.profiler = type(
        "_ProfStub",
        (),
        {
            "dramatic_sequences": [
                DramaticSequence(
                    sequence_name="Sekwencja 1",
                    time_range="00:00 - 01:00",
                    dramatic_summary="Rozmowa w korytarzu",
                    dominant_tone="Napięcie",
                    characters_present=["PostacAlfa", "PostacBeta"],
                    female_only_scene=True,
                    male_only_scene=False,
                )
            ]
        },
    )()

    ev1 = pysubs2.SSAEvent(start=1000, end=3000, name="", text="We arrived together.")
    ev2 = pysubs2.SSAEvent(start=3500, end=5500, name="", text="I secured the lock.")
    batch_events = [(0, ev1, ev1.text, ""), (1, ev2, ev2.text, "")]
    speaker_tags = {
        1: "średni tembr (~158Hz: tenor męski / alt żeński)",
        2: "niski tembr (~115Hz: bas/baryton lub ochrypły alt starszej kobiety)",
    }

    prompt = tr._prepare_batch_prompt(
        batch_events=batch_events,
        history_context=[],
        speaker_tags=speaker_tags,
    )
    block1 = prompt.split("Kwestia [ID: 1]")[1].split("Kwestia [ID: 2]")[0]
    assert "Mówca: FEMININE" not in block1
    assert "(FEMININE)" not in block1
    assert "[MÓWCA: Kobieta" not in block1
    assert "Grupa_1os_lm: NON_VIRILE" in block1

    g1, a1 = tr._arbitrate_speaker_gender(
        event=ev1,
        raw_phase1_gender=None,
        batch_id=1,
        speaker_tags=speaker_tags,
        pl_candidate="",
        raw_speaker_name="",
        event_idx=0,
    )
    assert g1 == "UNKNOWN"
    assert any("anonimowy_mówca=" in x for x in a1)

    g2, a2 = tr._arbitrate_speaker_gender(
        event=ev2,
        raw_phase1_gender=None,
        batch_id=2,
        speaker_tags=speaker_tags,
        pl_candidate="",
        raw_speaker_name="",
        event_idx=1,
    )
    assert g2 == "mężczyzna"
    assert any("f0_audio" in x or "odsłuch_f0_whisper" in x for x in a2)

    p1 = tr._process_phase1_only(
        b_idx=0,
        batch=batch_events,
        untranslated_in_batch=batch_events,
        batches=[batch_events],
        video_path=None,
        is_ass=True,
        anime_meta=None,
        episode_profile=None,
        anime_context_str="",
        episode_profile_str="",
        series_bible_str="",
        manga_canon_str="",
        combined_glossary={},
        all_user_rules=[],
        translated_results={},
        history=[],
        pbar=_DummyPbar(),
    )
    items = p1["pass1_items"]
    assert items[0]["raw_actor"] == ""
    assert items[0]["speaker_gender"] is None
    assert items[0]["speaker_confidence"] == 0.0
    assert items[0]["speaker_gender_source"] == "anonymous_deferred"
    assert items[0]["plural_group_gender"] == "NON_VIRILE"
    assert "Mówca: FEMININE" not in items[0]["telemetry_tag"]


# ------------------------------------------------------------------------------
# Test 2 (OBS-07): Non-human speakers with high F0 vs P0 canonical creature
# ------------------------------------------------------------------------------
@pytest.mark.unit
def test_obs07_nonhuman_speaker_with_high_f0_never_inherits_feminine(tmp_path: Path):
    sb = _build_synthetic_bible(tmp_path, include_male_bird=True)
    tr = MultimodalTranslator(api_key="mock_k0", model="gemini-4-hydrogen", enable_verifier=False)
    tr.series_bible = sb
    tr.character_registry = {}

    for label in ("SmokLewy", "Dragon Left", "Talking Wall", "ScianaAlfa"):
        assert _is_nonhuman_speaker_label(label) is True
        ev = pysubs2.SSAEvent(start=1000, end=3000, name=label, text="Hear my roar!")
        g_res, alerts = tr._arbitrate_speaker_gender(
            event=ev,
            raw_phase1_gender=None,
            batch_id=1,
            speaker_tags={1: "wysoki tembr (~268Hz: sopran żeński / głos dziecięcy)"},
            pl_candidate="",
            raw_speaker_name=label,
            event_idx=0,
        )
        assert g_res == "UNKNOWN", f"Non-human {label} inherited {g_res} instead of UNKNOWN!"
        assert any("byt_nieludzki=" in a for a in alerts)

        prompt = tr._prepare_batch_prompt(
            batch_events=[(0, ev, ev.text, "")],
            history_context=[],
            speaker_tags={1: "wysoki tembr (~268Hz: sopran żeński / głos dziecięcy)"},
        )
        assert "(FEMININE)" not in prompt
        assert "(Kobieta)" not in prompt

        g_low, _ = tr._arbitrate_speaker_gender(
            event=ev,
            raw_phase1_gender=None,
            batch_id=1,
            speaker_tags={1: "niski tembr (~112Hz: bas/baryton lub ochrypły alt starszej kobiety)"},
            pl_candidate="",
            raw_speaker_name=label,
            event_idx=0,
        )
        assert g_low == "mężczyzna"

    # Canonical P0 animal/bird MUST preserve MALE despite high pitch
    ev_bird = pysubs2.SSAEvent(start=4000, end=6000, name="PtakKanoniczny", text="Stay calm!")
    g_bird, alerts_bird = tr._arbitrate_speaker_gender(
        event=ev_bird,
        raw_phase1_gender=None,
        batch_id=1,
        speaker_tags={1: "wysoki tembr (~250Hz: sopran żeński / głos dziecięcy)"},
        pl_candidate="",
        raw_speaker_name="PtakKanoniczny",
        event_idx=0,
    )
    assert g_bird == "mężczyzna"
    assert any("rekord_p0" in a for a in alerts_bird)


# ------------------------------------------------------------------------------
# Test 3 (E4-bis.2): EpisodeProfiler.reconcile_prepass_with_p0 unverified guard
# ------------------------------------------------------------------------------
@pytest.mark.unit
def test_e4bis2_reconcile_prepass_disables_female_only_when_unverified_participant_present(tmp_path: Path):
    sb = _build_synthetic_bible(tmp_path)

    seq_pure_fem = DramaticSequence(
        sequence_name="Sekwencja A: Wyłącznie potwierdzone kobiety",
        time_range="00:00 - 01:00",
        dramatic_summary="Rozmowa dwóch bohaterek",
        dominant_tone="Spokój",
        characters_present=["PostacAlfa", "PostacBeta"],
        female_only_scene=False,
        male_only_scene=True,
    )
    seq_mixed_missing = DramaticSequence(
        sequence_name="Sekwencja B: Nieznany głos spoza bazy",
        time_range="01:00 - 02:00",
        dramatic_summary="Wtrącenie nieznanego głosu",
        dominant_tone="Napięcie",
        characters_present=["PostacAlfa", "NieznanyGlosAlfa"],
        female_only_scene=True,
        male_only_scene=False,
    )
    seq_mixed_unknown_entry = DramaticSequence(
        sequence_name="Sekwencja C: Byt z UNKNOWN w SeriesBible",
        time_range="02:00 - 03:00",
        dramatic_summary="Dialog z niezweryfikowanym bytem",
        dominant_tone="Niepokój",
        characters_present=["PostacAlfa", "BytNieludzkiAlfa"],
        female_only_scene=True,
        male_only_scene=False,
    )
    seq_all_unverified = DramaticSequence(
        sequence_name="Sekwencja D: Wyłącznie nieznane głosy",
        time_range="03:00 - 04:00",
        dramatic_summary="Scena samych niezweryfikowanych mówców",
        dominant_tone="Zagadka",
        characters_present=["SmokLewy"],
        female_only_scene=True,
        male_only_scene=False,
    )
    seq_empty_legacy = DramaticSequence(
        sequence_name="Sekwencja E: Pusta lista legacy",
        time_range="04:00 - 05:00",
        dramatic_summary="Zgodność testowa",
        dominant_tone="Neutralny",
        characters_present=[],
        female_only_scene=True,
        male_only_scene=False,
    )

    reconciled = EpisodeProfiler.reconcile_prepass_with_p0(
        [seq_pure_fem, seq_mixed_missing, seq_mixed_unknown_entry, seq_all_unverified, seq_empty_legacy],
        series_bible=sb,
    )
    assert reconciled[0].female_only_scene is True and reconciled[0].male_only_scene is False
    assert reconciled[1].female_only_scene is False and reconciled[1].male_only_scene is False
    assert reconciled[2].female_only_scene is False and reconciled[2].male_only_scene is False
    assert reconciled[3].female_only_scene is False and reconciled[3].male_only_scene is False
    assert reconciled[4].female_only_scene is True


# ------------------------------------------------------------------------------
# Test 4 (E4-bis.3): Filtered librosa.pyin in SpeakerVoiceClassifier
# ------------------------------------------------------------------------------
@pytest.mark.unit
def test_e4bis3_speaker_diarizer_uses_filtered_pyin_and_rejects_bgm_noise():
    sr = 16000
    t = np.linspace(0, 1.0, sr, endpoint=False)

    sine_200 = (np.sin(2 * np.pi * 200 * t) * 15000).astype(np.float32)
    f0_200 = SpeakerVoiceClassifier.estimate_pitch_f0(sine_200, sample_rate=sr)
    assert f0_200 is not None and 190.0 <= f0_200 <= 210.0

    sine_120 = (np.sin(2 * np.pi * 120 * t) * 15000).astype(np.float32)
    f0_120 = SpeakerVoiceClassifier.estimate_pitch_f0(sine_120, sample_rate=sr)
    assert f0_120 is not None and 110.0 <= f0_120 <= 130.0

    rng = np.random.default_rng(1225)
    white_noise = rng.normal(0.0, 5000.0, sr).astype(np.float32)
    assert SpeakerVoiceClassifier.estimate_pitch_f0(white_noise, sample_rate=sr) is None

    # Chaotic BGM chirp + noise
    chirp = (np.sin(2 * np.pi * (80.0 + 300.0 * t) * t) * 8000.0 + rng.normal(0.0, 3000.0, sr)).astype(np.float32)
    f0_chirp = SpeakerVoiceClassifier.estimate_pitch_f0(chirp, sample_rate=sr)
    assert f0_chirp is None or f0_chirp > 135.0

    # High female voice 240 Hz mixed with strong 85 Hz BGM bass (previously caused false ~80Hz male tag!)
    bgm_mix = (
        np.sin(2 * np.pi * 240 * t) * 12000.0
        + np.sin(2 * np.pi * 85 * t) * 6000.0
        + rng.normal(0.0, 1500.0, sr)
    ).astype(np.float32)
    f0_mix = SpeakerVoiceClassifier.estimate_pitch_f0(bgm_mix, sample_rate=sr)
    assert f0_mix is None or f0_mix > 135.0


# ------------------------------------------------------------------------------
# Test 5 (E4-bis.4): EpisodeFlightRecorder raw_actor & speaker_gender_source & summary
# ------------------------------------------------------------------------------
@pytest.mark.unit
def test_e4bis4_flight_recorder_logs_raw_actor_gender_source_and_scene_summary(tmp_path: Path):
    rec = EpisodeFlightRecorder(
        anime_slug="test_seria_1225",
        filename="test_ep",
        trace_dir=str(tmp_path),
        enabled=True,
    )

    # Backwards-compatible call without new fields
    rec.log_line_evolution(1, 0, 1000, "PostacAlfa", "Hello", "もしもし", "", "", "Cześć", "Cześć", "Cześć")

    summary = {
        "total_events": 100,
        "female": 90,
        "male": 0,
        "unknown": 10,
        "anonymous_lines": 98,
        "anonymous_ratio": 0.98,
    }
    rec.log_scene_discourse(
        scene_boundaries=[1000, 5000],
        turns=[{"speaker": "PostacAlfa", "lines": [1]}],
        batches_summary=[{"batch_id": 0, "line_count": 2}],
        episode_scene_genders_summary=summary,
    )
    rec.log_line_evolution(
        line_id=18,
        start_ms=34770,
        end_ms=36970,
        actor="PostacAlfa",
        en_text="Yes, there is no mistake.",
        jp_audio="",
        whisper_tags="",
        telemetry_tag="[Grupa_1os_lm: NON_VIRILE]",
        phase1_pl="Tak, bez pomyłki.",
        phase2_pl="Tak, bez pomyłki.",
        linter_pl="Tak, bez pomyłki.",
        raw_actor="",
        speaker_gender_source="anonymous_deferred",
    )
    rec.log_line_evolution(
        line_id=19,
        start_ms=37000,
        end_ms=39000,
        actor="SmokLewy",
        en_text="Listen carefully.",
        jp_audio="",
        whisper_tags="wysoki tembr (~268Hz)",
        telemetry_tag="",
        phase1_pl="Słuchaj uważnie.",
        phase2_pl="Słuchaj uważnie.",
        linter_pl="Słuchaj uważnie.",
        raw_actor="SmokLewy",
        speaker_gender_source="nonhuman_deferred",
    )

    events = _read_jsonl(rec.jsonl_path)
    sd_ev = [e for e in events if e["stage"] == "scene_discourse"][-1]
    assert sd_ev["payload"]["episode_scene_genders_summary"] == summary

    le_evs = [e["payload"] for e in events if e["stage"] == "line_evolution"]
    assert "raw_actor" not in le_evs[0]
    assert "speaker_gender_source" not in le_evs[0]
    assert le_evs[1]["raw_actor"] == ""
    assert le_evs[1]["speaker_gender_source"] == "anonymous_deferred"
    assert le_evs[2]["raw_actor"] == "SmokLewy"
    assert le_evs[2]["speaker_gender_source"] == "nonhuman_deferred"

    trace_txt = rec.log_path.read_text(encoding="utf-8")
    assert "anonymous_deferred" in trace_txt
    assert "nonhuman_deferred" in trace_txt
    assert "anonymous_ratio" in trace_txt


# ------------------------------------------------------------------------------
# Test 6 (E3): Focused rule for non-human speakers and unknown voices
# ------------------------------------------------------------------------------
@pytest.mark.unit
def test_e3_focused_rules_appends_nonhuman_and_unknown_voice_directive():
    base_rules = "• [ZASADA BAZOWA]: Zachowuj zwięzłość."

    # 1. Anonymous line triggers directive cleanly & idempotently
    out_anon = _append_phase1_nonhuman_and_unknown_voice_rule(
        base_rules,
        [{"en": "Who goes there?", "speaker": "", "is_sign": False}],
    )
    assert "[BYTY NIELUDZKIE I NIEZNANE GŁOSY]" in out_anon
    assert _append_phase1_nonhuman_and_unknown_voice_rule(
        out_anon,
        [{"en": "Who goes there?", "speaker": "", "is_sign": False}],
    ) == out_anon

    # 2. Non-human speaker triggers directive
    out_nonhuman = _append_phase1_nonhuman_and_unknown_voice_rule(
        "",
        [{"en": "You shall not pass.", "speaker": "Talking Wall", "is_sign": False}],
    )
    assert "[BYTY NIELUDZKIE I NIEZNANE GŁOSY]" in out_nonhuman

    # 3. Sign-only or known human speaker batch does NOT append directive
    out_sign = _append_phase1_nonhuman_and_unknown_voice_rule(
        base_rules,
        [{"en": "CHAPTER 1", "speaker": "", "is_sign": True}],
    )
    assert out_sign == base_rules

    out_known_human = _append_phase1_nonhuman_and_unknown_voice_rule(
        base_rules,
        [{"en": "Let us head back.", "speaker": "PostacAlfa", "is_sign": False}],
    )
    assert out_known_human == base_rules
