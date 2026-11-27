# -*- coding: utf-8 -*-
"""
Standard 12.2.2 Regression Suite (Observability U1–U8, 0.00 PLN, 0 B diff Z16).
100% Z1-pure synthetic test suite operating on real production classes & methods.
"""

import builtins
import json
import logging
import os
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import httpx
import pysubs2
import pytest
from google import genai
from google.genai import types as genai_types

import series_memory
from avt_linter import EpisodeQualityGate
from pipeline_logger import EpisodeFlightRecorder
from series_memory import SeriesBible
from sign_detector import VisualSignDetector
from tools.verify_f2_consolidation_ab import load_phase2_items_from_events
from translator import (
    BatchTranslationResponse,
    LineTranslation,
    MultimodalTranslator,
    SceneDiagnosis,
    _write_json_atomic,
)
from verifier import RefinedLine


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


def _make_translator(
    tmp_path: Path,
    batch_translations=None,
    thoughts_tokens: int = 0,
    enable_verifier: bool = True,
) -> MultimodalTranslator:
    resp_obj = BatchTranslationResponse(
        scene_diagnosis=SceneDiagnosis(
            dramatic_context="Syntetyczna scena dialogowa",
            dialogue_flow="Naturalna wymiana zdań",
            audio_intent_check="Spójna intonacja",
            dominant_tone="Neutralny",
        ),
        translations=batch_translations
        or [
            LineTranslation(
                id=1,
                polish_text="Razem teraz!",
                speaker_gender="UNKNOWN",
                speaker_name="",
                addressee=None,
            )
        ],
    )
    payload_text = resp_obj.model_dump_json()

    def _handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "candidates": [{"content": {"role": "model", "parts": [{"text": payload_text}]}}],
                "usageMetadata": {
                    "promptTokenCount": 520,
                    "cachedContentTokenCount": 0,
                    "candidatesTokenCount": 64,
                    "thoughtsTokenCount": thoughts_tokens,
                },
            },
        )

    tr = MultimodalTranslator(api_key="mock_k0", model="gemini-4-hydrogen", enable_verifier=enable_verifier)
    if not hasattr(tr, "verifier"):
        tr.verifier = None
    mock_c = _make_mock_genai_client(_handler)
    tr.client_pool_f1.clients = [mock_c]
    tr.client_pool.clients = [mock_c]
    tr.client = mock_c
    tr.trace_dir = str(tmp_path)
    tr.series_bible = SeriesBible("SyntheticSeries1222", storage_dir=tmp_path)
    if hasattr(tr, "verifier") and tr.verifier is not None:
        tr.verifier.client_pool.clients = [mock_c]
        tr.verifier.client = mock_c
    return tr


def _read_jsonl(path: Path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


# ------------------------------------------------------------------------------
# U1: F2 score breakdown & selection metadata in line_evolution / phase2_verifier
# ------------------------------------------------------------------------------
@pytest.mark.unit
def test_u1_f2_score_breakdown_and_selection_metadata(tmp_path: Path):
    # 1. Verify _score_phase2_editorial_risk_detailed vs _score_phase2_editorial_risk parity
    sample_id85 = {
        "id": 85,
        "orig_idx": 85,
        "en": "Next up, we'll hear from the representative of the new students.",
        "pl": "Teraz wysłuchamy przedstawiciela nowych uczniów.",
        "is_sign": False,
        "speaker_confidence": 1.0,
        "target_confidence": 1.0,
    }
    sc_85, crit_85, reasons_85 = MultimodalTranslator._score_phase2_editorial_risk_detailed(sample_id85)
    assert (sc_85, crit_85) == MultimodalTranslator._score_phase2_editorial_risk(sample_id85)
    assert sc_85 >= 30 and crit_85 is False
    assert "official_announcement:+30" in reasons_85

    sample_id93 = {
        "id": 93,
        "orig_idx": 93,
        "en": "That was fair.",
        "pl": "To było najibardziej sprawiedliwe.",
        "is_sign": False,
        "speaker_confidence": 1.0,
        "target_confidence": 1.0,
    }
    sc_93, crit_93, reasons_93 = MultimodalTranslator._score_phase2_editorial_risk_detailed(sample_id93)
    assert (sc_93, crit_93) == MultimodalTranslator._score_phase2_editorial_risk(sample_id93)
    assert sc_93 >= 40
    assert "pl_typo:+40" in reasons_93

    # Trivial short penalty delta (-20 on relation_tag=20, -25 on low_confidence=30)
    sc_triv20, _, reasons_triv20 = MultimodalTranslator._score_phase2_editorial_risk_detailed(
        {
            "en": "Yes.",
            "pl": "Tak.",
            "relation_tag": "friend",
            "speaker_confidence": 1.0,
            "target_confidence": 1.0,
        }
    )
    assert sc_triv20 == 0
    assert "trivial_short:-20" in reasons_triv20

    sc_triv25, _, reasons_triv25 = MultimodalTranslator._score_phase2_editorial_risk_detailed(
        {
            "en": "Wait.",
            "pl": "Czekaj.",
            "speaker_confidence": 0.7,
            "target_confidence": 1.0,
        }
    )
    assert sc_triv25 == 5
    assert "trivial_short:-25" in reasons_triv25

    # 2. Build a 14-item batch exercising selected, score_zero, below_batch_cap & evicted_for_a1_pair
    tr = _make_translator(tmp_path)
    tr.flight_recorder = EpisodeFlightRecorder(anime_slug="syn_u1", filename="ep01", trace_dir=tmp_path)
    items = []
    # Positions 0..5: score 65 (speaker_confidence < 0.95 + ambiguity_note = 30+35=65)
    for i in range(1, 7):
        items.append({
            "id": i,
            "orig_idx": i,
            "start_ms": i * 3000,
            "end_ms": i * 3000 + 900,
            "speaker": f"spk_{i}",
            "en": "We need to talk now.",
            "pl": "Musimy porozmawiać teraz.",
            "speaker_confidence": 0.80,
            "target_confidence": 1.0,
            "ambiguity_note": "check",
        })
    # Position 6 (id=7): score 30 (official announcement, < 9 words) -> lowest in top 8 -> eviction victim!
    items.append({
        "id": 7,
        "orig_idx": 7,
        "start_ms": 21000,
        "end_ms": 22000,
        "speaker": "spk_7",
        "en": "Next up, the new student representative.",
        "pl": "Teraz wysłuchamy przedstawiciela uczniów.",
        "speaker_confidence": 1.0,
        "target_confidence": 1.0,
    })
    # Position 7 (id=8): anchor score 100 (blind draft), split sentence without end punctuation
    items.append({
        "id": 8,
        "orig_idx": 8,
        "start_ms": 25000,
        "end_ms": 26000,
        "speaker": "mowca_a",
        "en": "Because we must act",
        "pl": "Ponieważ musimy działać",
        "is_blind_draft": True,
        "speaker_confidence": 1.0,
        "target_confidence": 1.0,
    })
    # Position 8 (id=9): A-1 split partner, low score 20 -> outside initial top 8, pulled as partner
    items.append({
        "id": 9,
        "orig_idx": 9,
        "start_ms": 26100,
        "end_ms": 27000,
        "speaker": "mowca_a",
        "en": "before the sunset arrives today.",
        "pl": "zanim zajdzie dzisiejsze słońce.",
        "relation_tag": "ally",
        "speaker_confidence": 1.0,
        "target_confidence": 1.0,
    })
    # Position 9 (id=10): typo line id=10 -> wait, make id=93 below or give score 20 > 0 outside cap
    # Give pos 9 (id=10) score 20 -> below_batch_cap
    items.append({
        "id": 10,
        "orig_idx": 10,
        "start_ms": 30000,
        "end_ms": 31000,
        "speaker": "spk_10",
        "en": "I understand the plan.",
        "pl": "Rozumiem cały ten plan.",
        "relation_tag": "ally",
        "speaker_confidence": 1.0,
        "target_confidence": 1.0,
    })
    # Position 10 (id=93): high typo score 40 (replaces position 6 or keep pos 6 lower? wait!)
    # Replace pos 6 above? No, we want id=7 (score 30) to be evicted and id=93 ALSO selected if score > 30!
    # Wait: if pos 10 has score 40 (pl_typo), pos 10 enters top 8 and pushes score 30 out of top 8!
    # Keep pos 1..5 at score 65 (5 items), pos 5 (id=6) at 40 (pl_typo), pos 6 (id=7) at 30, pos 7 (id=8) at 100 -> 8 items!
    # Then put id=93 as pos 4 (score 40+30=70)! Let's adjust item 5 to carry typo so ID 93 label works!
    items[4]["orig_idx"] = 93
    items[4]["pl"] = "To było najibardziej złożone zadanie."
    items[4]["speaker_confidence"] = 0.80
    items[4]["ambiguity_note"] = ""
    items[4]["en"] = "That was complex."
    # Positions 10..13 (4 lines): score_zero
    for j in range(11, 15):
        items.append({
            "id": j,
            "orig_idx": j,
            "start_ms": j * 3000,
            "end_ms": j * 3000 + 800,
            "speaker": f"spk_{j}",
            "en": "Okay.",
            "pl": "Dobrze.",
            "speaker_confidence": 1.0,
            "target_confidence": 1.0,
        })

    def _fake_verify_batch(**kwargs):
        return [
            RefinedLine(id=it["id"], refined_pl=it["pl"], changes_made="Zweryfikowano.")
            for it in kwargs["batch_items"]
        ]

    tr.verifier.system_prompt = "lean"
    tr.verifier.model = "gemini-4-hydrogen"
    tr.verifier.verify_batch = _fake_verify_batch
    tr._audit_batch_context_cache = lambda *a, **kw: None

    phase1_data = {
        "b_idx": 0,
        "pass1_items": items,
        "untranslated_in_batch": [],
        "scene_desc": "Scena testowa",
        "batch_response": None,
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
        "pbar": _DummyPbar(),
        "combined_glossary": {},
        "all_user_rules": [],
        "episode_profile": None,
        "total_batches": 6,
    }
    tr._process_phase2_only(phase1_data)
    events = _read_jsonl(tr.flight_recorder.jsonl_path)

    p2_events = [e for e in events if e["stage"] == "phase2_verifier"]
    assert len(p2_events) == 1
    sel_summary = p2_events[0]["payload"]["f2_selection_summary"]
    assert sel_summary["batch_cap"] == 8
    assert sel_summary["total_lines"] == 14
    assert sel_summary["selected_count"] == 8
    assert isinstance(sel_summary["batch_p90"], int) and sel_summary["batch_p90"] >= 40
    assert 9 in sel_summary["selected_ids"]

    line_evts = {e["line_id"]: e["payload"] for e in events if e["stage"] == "line_evolution"}
    assert len(line_evts) == 14
    assert line_evts[93]["f2_selected"] is True
    assert "pl_typo:+40" in line_evts[93]["f2_score_reasons"]
    assert line_evts[93]["f2_not_selected_reason"] is None
    assert line_evts[9]["f2_selected"] is True
    assert "a1_pair_partner" in line_evts[9]["f2_score_reasons"]
    assert line_evts[7]["f2_selected"] is False
    assert line_evts[7]["f2_not_selected_reason"] == "evicted_for_a1_pair"
    assert "official_announcement:+30" in line_evts[7]["f2_score_reasons"]
    assert line_evts[10]["f2_selected"] is False
    assert line_evts[10]["f2_not_selected_reason"] == "below_batch_cap"
    assert line_evts[11]["f2_selected"] is False
    assert line_evts[11]["f2_not_selected_reason"] == "score_zero"

    # Also verify <= 10 branch preserves f2_* fields and sets batch_cap == len(pass1_items)
    small_items = [dict(it) for it in items[:4]]
    small_sel = tr._select_hydrogen_phase2_candidates(small_items, total_batches=1)
    assert len(small_sel) == 4
    assert all(it["f2_selected"] is True and it["f2_batch_cap"] == 4 for it in small_items)


# ------------------------------------------------------------------------------
# U2: Batch line_ids (with FBF gap), focused_rules, rendered_characters, notes_meta
# ------------------------------------------------------------------------------
@pytest.mark.unit
def test_u2_batch_line_ids_rules_and_line_observability_meta(tmp_path: Path):
    f1_ids = [58, 59, 60, 70, 72, 73]  # explicit FBF compression gap skipping 61..69 & 71
    f1_trans = [
        LineTranslation(
            id=idx,
            polish_text=f"Kwestia testowa numer {orig}.",
            speaker_gender="FEMALE" if idx % 2 else "MALE",
            speaker_name="osoba_a" if idx % 2 else "osoba_b",
            addressee=None,
        )
        for idx, orig in enumerate(f1_ids, 1)
    ]
    tr = _make_translator(tmp_path, batch_translations=f1_trans)
    tr.flight_recorder = EpisodeFlightRecorder(anime_slug="syn_u2", filename="ep02", trace_dir=tmp_path)
    tr.character_registry = {
        "osoba_a": "Kobieta, pierwszoroczna uczennica akademii.",
        "osoba_b": "Mężczyzna, instruktor szermierki.",
    }
    tr.whisper = None

    batch_events = []
    for orig in f1_ids:
        ev = pysubs2.SSAEvent(start=orig * 1000, end=orig * 1000 + 900, text=f"Line number {orig}?")
        ev.name = "osoba_a" if orig % 2 else "osoba_b"
        batch_events.append((orig, ev, ev.text, ""))

    p1_data = tr._process_phase1_only(
        b_idx=2,
        batch=batch_events,
        untranslated_in_batch=batch_events,
        batches=[batch_events],
        video_path=None,
        is_ass=True,
        anime_meta={},
        episode_profile=None,
        anime_context_str="",
        episode_profile_str="",
        series_bible_str="",
        manga_canon_str="",
        combined_glossary={"crest": "herb", "guild": "gildia"},
        all_user_rules=[],
        history=[],
        pbar=_DummyPbar(),
        translated_results={},
    )

    # Inject realistic U2 metadata into pass1_items[3] (orig_idx=70)
    target_it = p1_data["pass1_items"][3]
    target_it["notes"] = (
        "[Para spójności z #5: ciągłość] "
        "[Zwrot T-V: Twój / Szanowny Panie] "
        "[Kontekst sąsiedni (-1/+1): spójność]"
    )
    target_it["target_confidence"] = 0.80
    target_it["raw_addressee_hypothesis"] = "osoba_b"
    target_it["addressee"] = None
    target_it["active_scene_tone"] = "Napięcie"

    tr.verifier.system_prompt = "x" * 70000  # force full F2 mode (all items sent)
    tr.verifier.verify_batch = lambda **kw: [
        RefinedLine(id=it["id"], refined_pl=it["pl"], changes_made="Zweryfikowano.")
        for it in kw["batch_items"]
    ]
    tr._audit_batch_context_cache = lambda *a, **kw: None
    tr._process_phase2_only(p1_data)

    events = _read_jsonl(tr.flight_recorder.jsonl_path)
    p1_ev = [e for e in events if e["stage"] == "phase1_batch"][0]["payload"]
    assert p1_ev["line_ids"] == [58, 59, 60, 70, 72, 73]
    assert isinstance(p1_ev["focused_rules"], str)
    assert p1_ev["locked_glossary_count"] == 2
    assert "osoba_a" in p1_ev["rendered_characters"]
    assert "osoba_b" in p1_ev["rendered_characters"]

    p2_ev = [e for e in events if e["stage"] == "phase2_verifier"][0]["payload"]
    assert p2_ev["line_ids"] == {"1": 58, "2": 59, "3": 60, "4": 70, "5": 72, "6": 73}
    assert p2_ev["locked_glossary_count"] == 2
    assert "osoba_a" in p2_ev["rendered_characters"]

    le_70 = next(e["payload"] for e in events if e["stage"] == "line_evolution" and e["line_id"] == 70)
    assert le_70["batch_id"] == 2
    assert le_70["local_id"] == 4
    assert le_70["style"] == "Default"
    assert le_70["is_sign"] is False
    assert le_70["is_song"] is False
    assert le_70["is_internal_monologue"] is False
    meta = le_70["notes_meta"]
    assert meta["a1_pair_tag"] == "[Para spójności z #5: ciągłość]"
    assert meta["a3_tv_hint"] == "Twój / Szanowny Panie"
    assert meta["c1_neighbors"] == "[Kontekst sąsiedni (-1/+1): spójność]"
    assert meta["obs13c_target_conf"] == 0.80
    assert meta["obs13c_suppressed"] is True
    assert meta["scene_tone"] == "Napięcie"


# ------------------------------------------------------------------------------
# U3: Post-F2 chain (f2_raw_pl, post_f2_fixes) & EQG / SignDetector end-to-end
# ------------------------------------------------------------------------------
@pytest.mark.unit
def test_u3_post_f2_chain_and_eqg_diffs(tmp_path: Path, monkeypatch):
    tr = _make_translator(tmp_path)
    tr.flight_recorder = EpisodeFlightRecorder(anime_slug="syn_u3", filename="ep03", trace_dir=tmp_path)
    tr.character_registry = {"postac_f": "FEMALE"}

    p1_items = [
        {
            "id": 1,
            "orig_idx": 1,
            "start_ms": 1000,
            "end_ms": 2500,
            "speaker": "postac_f",
            "speaker_name": "postac_f",
            "en": "Five million for the guild.",
            "pl": r"{\i1}To 5 mln dla gildii.{\i0}",
            "style": "Thoughts_Italic",
            "is_sign": False,
            "is_song": False,
            "is_internal_monologue": True,
            "speaker_confidence": 1.0,
            "target_confidence": 1.0,
        },
        {
            "id": 2,
            "orig_idx": 2,
            "start_ms": 3000,
            "end_ms": 4000,
            "speaker": "postac_f",
            "speaker_name": "postac_f",
            "en": "Roger.",
            "pl": "Przyjęłam.",
            "style": "Default",
            "is_sign": False,
            "is_song": False,
            "is_internal_monologue": False,
            "speaker_confidence": 1.0,
            "target_confidence": 1.0,
        },
        {
            "id": 3,
            "orig_idx": 3,
            "start_ms": 5000,
            "end_ms": 6000,
            "speaker": "postac_f",
            "speaker_name": "postac_f",
            "en": "We must move",
            "pl": "Musimy ruszać",
            "style": "Default",
            "is_sign": False,
            "is_song": False,
            "is_internal_monologue": False,
            "speaker_confidence": 1.0,
            "target_confidence": 1.0,
        },
        {
            "id": 4,
            "orig_idx": 4,
            "start_ms": 6200,
            "end_ms": 7200,
            "speaker": "postac_f",
            "speaker_name": "postac_f",
            "en": "right now!",
            "pl": "właśnie teraz!",
            "style": "Default",
            "is_sign": False,
            "is_song": False,
            "is_internal_monologue": False,
            "speaker_confidence": 1.0,
            "target_confidence": 1.0,
        },
    ]
    # Raw F2 drops dot + uses '{\i1}...' on Thoughts_Italic + keeps '5 mln' + drops locked term 'gildii' -> 'stowarzyszenia'
    raw_f2_1 = r"{\i1}To 5 mln dla stowarzyszenia{\i0}"
    raw_f2_2 = "Przyjąłem."  # female speaker on radio -> Przyjęłam.
    raw_f2_3 = "Musimy ruszać."  # illegal modal period on split pair first part -> stripped by A-1 guard
    raw_f2_4 = "właśnie teraz!"

    tr.verifier.system_prompt = "x" * 70000
    tr.verifier.verify_batch = lambda **kw: [
        RefinedLine(id=1, refined_pl=raw_f2_1, changes_made="Korekta rejestru"),
        RefinedLine(id=2, refined_pl=raw_f2_2, changes_made="Meldunek"),
        RefinedLine(id=3, refined_pl=raw_f2_3, changes_made="Interpunkcja"),
    ]
    tr._audit_batch_context_cache = lambda *a, **kw: None

    phase1_data = {
        "b_idx": 0,
        "pass1_items": p1_items,
        "untranslated_in_batch": [],
        "scene_desc": "Scena post-F2",
        "batch_response": None,
        "lookback_history": [],
        "lookahead_events": [],
        "scoped_series_bible_str": "",
        "user_feedback_str": "",
        "glossary_str": "",
        "episode_profile_str": "",
        "manga_canon_str": "",
        "batch_glossary_items": [{"term_en": "guild", "translation_pl": "gildii"}],
        "speakers_on_ty": set(),
        "scene_has_first_name_vocative": False,
        "is_ass": True,
        "pbar": _DummyPbar(),
        "combined_glossary": {"guild": "gildii"},
        "all_user_rules": [],
        "episode_profile": None,
        "total_batches": 1,
    }
    tr._process_phase2_only(phase1_data)
    events = _read_jsonl(tr.flight_recorder.jsonl_path)
    le1 = next(e["payload"] for e in events if e["stage"] == "line_evolution" and e["line_id"] == 1)
    assert le1["f2_raw_pl"] == raw_f2_1
    assert le1["f2_changes_made"] == "Korekta rejestru"
    assert le1["phase2_pl"] != raw_f2_1
    assert "post_f2:italic_style_strip" in le1["post_f2_fixes"]
    assert "post_f2:obs19_trailing_period" in le1["post_f2_fixes"]
    assert "post_f2:a5_numeric_expansion" in le1["post_f2_fixes"]
    assert "post_f2:locked_glossary_enforce" in le1["post_f2_fixes"]

    le2 = next(e["payload"] for e in events if e["stage"] == "line_evolution" and e["line_id"] == 2)
    assert "post_f2:radio_impersonal" in le2["post_f2_fixes"]

    le3 = next(e["payload"] for e in events if e["stage"] == "line_evolution" and e["line_id"] == 3)
    assert "post_f2:a1_split_pair_guard" in le3["post_f2_fixes"]

    # Part B: End-to-end translate_file capturing real SignDetector + pre/post EQG diff snapshot
    ass_in = tmp_path / "syn_u3_ep01.ass"
    subs = pysubs2.SSAFile()
    subs.events.append(pysubs2.SSAEvent(start=500, end=2000, name="postac_f", text="Hello there."))
    subs.events.append(pysubs2.SSAEvent(start=10000, end=11500, name="postac_f", text="Let us begin."))
    subs.save(str(ass_in))
    fake_vid = tmp_path / "syn_u3_ep01.mkv"
    fake_vid.write_bytes(b"")
    out_ass = tmp_path / "syn_u3_ep01_pl.ass"

    tr2 = _make_translator(
        tmp_path,
        batch_translations=[
            LineTranslation(id=1, polish_text="Cześć wszystkim.", speaker_gender="FEMALE", speaker_name="postac_f"),
            LineTranslation(id=2, polish_text="Zaczynajmy teraz.", speaker_gender="FEMALE", speaker_name="postac_f"),
        ],
        enable_verifier=False,
    )
    monkeypatch.setattr("translator.get_anime_context", lambda *a, **kw: {})
    monkeypatch.setattr(tr2.manga_canon, "get_or_discover_canon", lambda *a, **kw: None)
    monkeypatch.setattr(tr2.profiler, "profile_episode", lambda *a, **kw: None)
    monkeypatch.setattr(
        series_memory,
        "SeriesBible",
        lambda *a, **kw: SeriesBible(*a, storage_dir=tmp_path, **kw),
    )
    monkeypatch.setattr(VisualSignDetector, "find_subtitle_gaps", lambda *a, **kw: [(3000, 8500)])
    monkeypatch.setattr(
        VisualSignDetector,
        "detect_signs_in_gaps",
        lambda *a, **kw: [pysubs2.SSAEvent(start=4000, end=7000, style="Sign", text=r"{\an8}AKADEMIA")],
    )
    monkeypatch.setattr("scene_snapper.SceneShotSnapper.detect_scene_cuts_ffmpeg", lambda *a, **kw: [])

    def _fake_eqg(sub_file, **kw):
        sub_file.events[0].text = "Cześć wszystkim!"
        return sub_file, ["Test EQG punctuation adjustment"]

    monkeypatch.setattr(EpisodeQualityGate, "audit_and_fix_entire_episode", _fake_eqg)

    tr2.translate_file(str(ass_in), video_path=str(fake_vid), output_path=str(out_ass))
    events_e2e = _read_jsonl(tr2.flight_recorder.jsonl_path)
    qg_ev = [e for e in events_e2e if e["stage"] == "quality_gate_pricing"][0]["payload"]
    assert qg_ev["avt_metrics"]["ass_events_count"] == 3
    assert len(qg_ev["sign_detector_events"]) == 1
    assert qg_ev["sign_detector_events"][0]["text"] == r"{\an8}AKADEMIA"
    assert any(
        d["before"] == "Cześć wszystkim." and d["after"] == "Cześć wszystkim!"
        for d in qg_ev["eqg_diffs"]
    )


# ------------------------------------------------------------------------------
# U4: acoustics_whisper batch_id & live whisper_tags composition
# ------------------------------------------------------------------------------
@pytest.mark.unit
def test_u4_acoustics_batch_id_and_real_whisper_tags(tmp_path: Path):
    tr = _make_translator(tmp_path)
    tr.flight_recorder = EpisodeFlightRecorder(anime_slug="syn_u4", filename="ep04", trace_dir=tmp_path)
    tr.whisper = None

    ev = pysubs2.SSAEvent(start=1000, end=2500, name="mowca_1", text="Listen carefully.")
    batch = [(1, ev, "Listen carefully.", "")]
    p1_data = tr._process_phase1_only(
        b_idx=4,
        batch=batch,
        untranslated_in_batch=batch,
        batches=[batch] * 5,
        video_path=None,
        is_ass=True,
        anime_meta={},
        episode_profile=None,
        anime_context_str="",
        episode_profile_str="",
        series_bible_str="",
        manga_canon_str="",
        combined_glossary={},
        all_user_rules=[],
        history=[],
        pbar=_DummyPbar(),
        translated_results={},
    )
    p1_data["pass1_items"][0]["speaker_voice"] = "MĘSKI GŁOS (baryton)"
    p1_data["pass1_items"][0]["prosody"] = "stanowczy"
    p1_data["pass1_items"][0]["pragmatic_register"] = "formalny"
    tr.verifier.verify_batch = lambda **kw: [
        RefinedLine(id=1, refined_pl="Posłuchaj uważnie.", changes_made="Zweryfikowano.")
    ]
    tr._audit_batch_context_cache = lambda *a, **kw: None
    tr._process_phase2_only(p1_data)

    events = _read_jsonl(tr.flight_recorder.jsonl_path)
    ac_ev = [e for e in events if e["stage"] == "acoustics_whisper"][0]
    assert ac_ev["batch_id"] == 4
    assert ac_ev["payload"]["batch_id"] == 4
    trace_txt = tr.flight_recorder.log_path.read_text(encoding="utf-8")
    assert "(PACZKA 4)" in trace_txt

    le_ev = [e for e in events if e["stage"] == "line_evolution"][0]["payload"]
    assert le_ev["whisper_tags"] == "MĘSKI GŁOS (baryton) | stanowczy | formalny"


# ------------------------------------------------------------------------------
# U5: F1 thoughts token count, git_head/consolidate_f2, budget_audit & atomic cp
# ------------------------------------------------------------------------------
@pytest.mark.unit
def test_u5_f1_thoughts_git_head_budget_audit_and_atomic_checkpoint(tmp_path: Path, monkeypatch):
    tr = _make_translator(tmp_path, thoughts_tokens=42, enable_verifier=False)
    tr.flight_recorder = EpisodeFlightRecorder(anime_slug="syn_u5", filename="ep05", trace_dir=tmp_path)

    ev = pysubs2.SSAEvent(start=0, end=1000, name="a", text="Let's go.")
    tr._process_phase1_only(
        b_idx=0,
        batch=[(1, ev, "Let's go.", "")],
        untranslated_in_batch=[(1, ev, "Let's go.", "")],
        batches=[[(1, ev, "Let's go.", "")]],
        video_path=None,
        is_ass=True,
        anime_meta={},
        episode_profile=None,
        anime_context_str="",
        episode_profile_str="",
        series_bible_str="",
        manga_canon_str="",
        combined_glossary={},
        all_user_rules=[],
        history=[],
        pbar=_DummyPbar(),
        translated_results={},
    )

    # _process_phase1_only(b_idx=0) already emits INIT; exercise ACTIVE, BYPASS & HALT budget_audit events
    tr.system_prompt = "lean"
    monkeypatch.delenv("AVT_ALLOW_UNCACHED_BILLING", raising=False)
    tr._audit_batch_context_cache(b_idx=1, cached_tokens=40000, phase="phase1")
    monkeypatch.setenv("AVT_ALLOW_UNCACHED_BILLING", "1")
    tr._audit_batch_context_cache(b_idx=2, cached_tokens=0, phase="phase1")
    monkeypatch.delenv("AVT_ALLOW_UNCACHED_BILLING", raising=False)

    tr.current_episode_tokens = {
        "prompt": 50000,
        "cached": 0,
        "output": 5000000,
        "model": "gemini-4-hydrogen",
    }
    tr._checkpoint_baseline_f1 = {}
    monkeypatch.setattr(os, "_exit", lambda code: (_ for _ in ()).throw(SystemExit(code)))
    with pytest.raises(SystemExit):
        tr._audit_batch_context_cache(b_idx=3, cached_tokens=0, phase="phase1")

    events = _read_jsonl(tr.flight_recorder.jsonl_path)
    p1_tu = [e for e in events if e["stage"] == "phase1_batch"][0]["payload"]["token_usage"]
    assert p1_tu["thoughts"] == 42
    assert p1_tu["output"] == 106  # 64 candidates + 42 thoughts preserved

    audit_kinds = [e["payload"]["event_kind"] for e in events if e["stage"] == "budget_audit"]
    assert audit_kinds == ["INIT", "ACTIVE", "BYPASS", "HALT"]

    # cli_init runtime_meta via real translate_file (with pre-existing checkpoint)
    ass_in = tmp_path / "syn_u5_ep01.ass"
    subs = pysubs2.SSAFile()
    subs.events.append(pysubs2.SSAEvent(start=0, end=1000, name="a", text="Hi."))
    subs.save(str(ass_in))
    cp_path = ass_in.with_suffix(".checkpoint.json")
    _write_json_atomic(cp_path, {"translated_results": {"0": "Cześć."}})

    monkeypatch.setattr("translator.get_anime_context", lambda *a, **kw: {})
    monkeypatch.setattr(tr.manga_canon, "get_or_discover_canon", lambda *a, **kw: None)
    monkeypatch.setattr(tr.profiler, "profile_episode", lambda *a, **kw: None)
    monkeypatch.setattr(
        series_memory,
        "SeriesBible",
        lambda *a, **kw: SeriesBible(*a, storage_dir=tmp_path, **kw),
    )
    monkeypatch.setenv("AVT_CONSOLIDATE_F2", "0")
    tr.translate_file(str(ass_in), output_path=str(tmp_path / "out.ass"))

    e2e_events = _read_jsonl(tr.flight_recorder.jsonl_path)
    cli_ev = [e for e in e2e_events if e["stage"] == "cli_init"][0]["payload"]
    rm = cli_ev["runtime_meta"]
    assert rm["git_head"] and rm["git_head"] != ""
    assert rm["consolidate_f2"] == "0"
    assert rm["resumed_from_checkpoint"] is True
    assert any(
        e["stage"] == "budget_audit" and e["payload"]["event_kind"] == "CHECKPOINT_RESUME"
        for e in e2e_events
    )

    # Atomic checkpoint failure safety: simulated json.dump error preserves valid file & leaves 0 .tmp
    _write_json_atomic(cp_path, {"translated_results": {"0": "Cześć."}})

    def _boom_dump(*a, **kw):
        raise OSError("simulated mid-write disk error")

    monkeypatch.setattr(json, "dump", _boom_dump)
    with pytest.raises(OSError):
        _write_json_atomic(cp_path, {"translated_results": {"corrupted": True}})
    assert json.loads(cp_path.read_text(encoding="utf-8")) == {"translated_results": {"0": "Cześć."}}
    assert list(tmp_path.glob("*.tmp")) == []


# ------------------------------------------------------------------------------
# U6: log_series_bible records locked_glossary (>= 7 terms) & ram_sanitization_notes
# ------------------------------------------------------------------------------
@pytest.mark.unit
def test_u6_series_bible_locked_glossary_and_sanitization_notes(tmp_path: Path, monkeypatch):
    tr = _make_translator(tmp_path, enable_verifier=False)
    ass_in = tmp_path / "syn_u6_ep01.ass"
    subs = pysubs2.SSAFile()
    subs.events.append(pysubs2.SSAEvent(start=0, end=1200, name="mowca_1", text="Enter the guild."))
    subs.save(str(ass_in))

    sb_tmp = SeriesBible("syn_u6_ep01", storage_dir=tmp_path)
    sb_tmp.data["glossary"] = {
        "academy": "akademia",
        "guild": "gildia",
        "council": "rada",
        "crest": "herb",
        "mana": "mana",
        "knight": "rycerz",
        "barrier": "bariera",
    }
    sb_tmp.data["characters"]["mowca_1"] = {
        "gender": "MALE",
        "priority": "P0",
        "has_verified_gender": True,
        "confidence": 0.99,
        "description": "Rycerz zakonu",
    }
    sb_tmp._ram_sanitization_notes = ["normalized_alias:mowca_1"]

    monkeypatch.setattr("translator.get_anime_context", lambda *a, **kw: {})
    monkeypatch.setattr(tr.manga_canon, "get_or_discover_canon", lambda *a, **kw: None)
    monkeypatch.setattr(tr.profiler, "profile_episode", lambda *a, **kw: None)
    monkeypatch.setattr(series_memory, "SeriesBible", lambda *a, **kw: sb_tmp)

    tr.translate_file(str(ass_in), output_path=str(tmp_path / "out_u6.ass"))
    events = _read_jsonl(tr.flight_recorder.jsonl_path)
    sb_ev = [e for e in events if e["stage"] == "series_bible"][0]["payload"]
    assert len(sb_ev["locked_glossary"]) >= 7
    assert sb_ev["locked_glossary"]["guild"] == "gildia"
    assert "normalized_alias:mowca_1" in sb_ev["ram_sanitization_notes"]
    assert any(n.startswith("characters_total:") for n in sb_ev["ram_sanitization_notes"])


# ------------------------------------------------------------------------------
# U7: exclude_none=True in phase1_batch + single I/O warning + backward compat
# ------------------------------------------------------------------------------
@pytest.mark.unit
def test_u7_phase1_exclude_none_and_io_error_warning(tmp_path: Path, monkeypatch, caplog):
    tr = _make_translator(tmp_path, enable_verifier=False)
    tr.flight_recorder = EpisodeFlightRecorder(anime_slug="syn_u7", filename="ep07", trace_dir=tmp_path)
    ev = pysubs2.SSAEvent(start=0, end=1000, name="a", text="Hello.")
    tr._process_phase1_only(
        b_idx=0,
        batch=[(1, ev, "Hello.", "")],
        untranslated_in_batch=[(1, ev, "Hello.", "")],
        batches=[[(1, ev, "Hello.", "")]],
        video_path=None,
        is_ass=True,
        anime_meta={},
        episode_profile=None,
        anime_context_str="",
        episode_profile_str="",
        series_bible_str="",
        manga_canon_str="",
        combined_glossary={},
        all_user_rules=[],
        history=[],
        pbar=_DummyPbar(),
        translated_results={},
    )
    p1_raw = [e for e in _read_jsonl(tr.flight_recorder.jsonl_path) if e["stage"] == "phase1_batch"][0]["payload"]["raw_response"]

    def _has_none(obj):
        if obj is None:
            return True
        if isinstance(obj, dict):
            return any(k is None or _has_none(v) for k, v in obj.items())
        if isinstance(obj, list):
            return any(_has_none(v) for v in obj)
        return False

    assert _has_none(p1_raw) is False

    # Fail-safe I/O error counter & single warning
    rec = EpisodeFlightRecorder(anime_slug="io_test", filename="ep", trace_dir=tmp_path, enabled=True)
    real_open = builtins.open

    def _failing_open(file, *args, **kwargs):
        if Path(str(file)) in (rec.jsonl_path, rec.log_path):
            raise PermissionError("simulated write lock")
        return real_open(file, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", _failing_open)
    with caplog.at_level(logging.WARNING, logger="pipeline_logger"):
        rec.record_event("test_stage", {"k": "v"})
        rec.write_log_section("[TEST]", "body")
        rec.finalize()

    assert rec._io_error_count == 3
    warn_msgs = [r for r in caplog.records if r.name == "pipeline_logger" and r.levelno == logging.WARNING]
    assert len(warn_msgs) == 1

    # Backward compatibility with legacy positional signatures
    rec_ok = EpisodeFlightRecorder(anime_slug="compat", filename="ep", trace_dir=tmp_path / "ok")
    rec_ok.log_cli_init({}, {}, {})
    rec_ok.log_acoustics_and_whisper({}, {})
    rec_ok.log_series_bible()
    rec_ok.log_phase1_batch(0, "p", {})
    rec_ok.log_phase2_verifier(0, 2048, "p", [])
    rec_ok.log_line_evolution(1, 0, 500, "a", "E", "J", "", "", "P1", "P2", "L")
    rec_ok.log_quality_gate_and_pricing([], {}, {})
    rec_ok.finalize()


# ------------------------------------------------------------------------------
# U8: verify_f2_consolidation_ab offline mapping without off-by-one on FBF gap
# ------------------------------------------------------------------------------
@pytest.mark.unit
def test_u8_verify_f2_consolidation_ab_no_off_by_one_on_fbf_gap(tmp_path: Path):
    line_ids = [i for i in range(58, 113) if i != 71]  # 54 lines (missing ID 71)
    assert len(line_ids) == 54
    assert line_ids.index(72) + 1 == 14

    def _write_events(target: Path, include_line_ids: bool):
        rows = [
            {
                "stage": "scene_discourse",
                "payload": {
                    "batches_summary": [{"batch_id": 1, "first_id": 58, "last_id": 112}]
                },
            },
            {
                "stage": "phase1_batch",
                "batch_id": 1,
                "payload": {
                    "batch_id": 1,
                    "raw_response": {"scene_diagnosis": {"dramatic_context": "Paczka z luką FBF"}},
                    **({"line_ids": line_ids} if include_line_ids else {}),
                },
            },
            {
                "stage": "phase2_verifier",
                "batch_id": 1,
                "payload": {
                    "batch_id": 1,
                    "raw_response": [{"id": 14, "refined_pl": "Linia 72 po F2."}],
                },
            },
        ]
        for local_id, lid in enumerate(line_ids, 1):
            rows.append({
                "stage": "line_evolution",
                "line_id": lid,
                "payload": {
                    "line_id": lid,
                    "start_ms": lid * 1000,
                    "end_ms": lid * 1000 + 800,
                    "actor": "postac_x",
                    "en_text": f"Source line {lid}",
                    "phase1_pl": f"Linia {lid} po F1.",
                    **({"local_id": local_id, "is_sign": False, "is_song": False} if include_line_ids else {}),
                },
            })
        target.write_text("\n".join(json.dumps(r) for r in rows), encoding="utf-8")

    # Mode A: Modern logs (12.2.2+) with explicit line_ids
    ev_modern = tmp_path / "modern_events.jsonl"
    _write_events(ev_modern, include_line_ids=True)
    out_modern = load_phase2_items_from_events(ev_modern)
    items_m = out_modern[1]["pass1_items"]
    assert len(items_m) == 54
    assert next(it["id"] for it in items_m if it["orig_idx"] == 70) == 13
    assert next(it["id"] for it in items_m if it["orig_idx"] == 72) == 14
    assert next(it["id"] for it in items_m if it["orig_idx"] == 112) == 54
    assert 14 in out_modern[1]["orig_selected_ids"]

    # Mode B: Legacy logs (12.0.0–12.2.1a) without line_ids, relying on present_lids enumeration
    ev_legacy = tmp_path / "legacy_events.jsonl"
    _write_events(ev_legacy, include_line_ids=False)
    out_legacy = load_phase2_items_from_events(ev_legacy)
    items_l = out_legacy[1]["pass1_items"]
    assert len(items_l) == 54
    assert next(it["id"] for it in items_l if it["orig_idx"] == 70) == 13
    assert next(it["id"] for it in items_l if it["orig_idx"] == 72) == 14
    assert next(it["id"] for it in items_l if it["orig_idx"] == 112) == 54
    assert 14 in out_legacy[1]["orig_selected_ids"]
