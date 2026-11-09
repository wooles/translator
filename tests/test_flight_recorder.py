"""
Unit tests for pipeline_logger.py / flight_recorder.py covering Standard 9.4 operation 2C.8:
- T4.11 (2C.8): test_report_step_11_lists_all_fixes_and_emits_consistency_check_ok
"""
import pytest
from flight_recorder import EpisodeFlightRecorder
from avt_linter import EpisodeQualityGate


@pytest.mark.unit
def test_report_step_11_lists_all_fixes_and_emits_consistency_check_ok(tmp_path):
    """
    T4.11 (Operacja 2C.8): Weryfikacja integralności raportu Kroku 11 i pola consistency_check.
    """
    # Symulujemy 20 poprawek (powyżej dawnego limitu 15)
    mock_fixes = [f"[Filar {i}] Poprawka {i}" for i in range(1, 21)]
    EpisodeQualityGate._last_all_fixes = list(mock_fixes)

    rec = EpisodeFlightRecorder(
        anime_slug="test_anime",
        filename="test_episode",
        trace_dir=str(tmp_path),
        enabled=True
    )

    rec.report_step_11_quality_gate(
        quality_gate_fixes=mock_fixes,
        avt_metrics={"cps": 14.2, "cpl": 32},
        pricing_summary={"cost_pln": 0.05}
    )

    import json
    assert rec.jsonl_path.exists()
    with open(rec.jsonl_path, "r", encoding="utf-8") as f:
        fr_lines = [json.loads(l) for l in f if l.strip()]
    assert len(fr_lines) >= 1
    ev = fr_lines[-1]
    assert ev["stage"] == "quality_gate_pricing"
    payload = ev["payload"]
    # Weryfikacja braku ucięcia do 15
    assert len(payload["quality_gate_fixes"]) == 20
    assert payload["quality_gate_fixes"] == mock_fixes

    # Weryfikacja consistency_check
    cc = payload.get("consistency_check", {})
    assert cc.get("status") == "OK"
    assert cc.get("reported") == 20
    assert cc.get("collected") == 20


def test_t11_1_3_1_scene_discourse_batch_summary_from_4_tuples(tmp_path):
    """
    T11.1.3_1 (INC-AVT-020): Weryfikacja odpornosci log_scene_discourse i konstrukcji batches_sum
    na 4-elementowe krotki raw_entries (orig_idx, ev, clean, ts_prefix).
    """
    import pysubs2
    import json
    from flight_recorder import EpisodeFlightRecorder

    rec = EpisodeFlightRecorder(
        anime_slug="test_anime",
        filename="test_episode",
        trace_dir=str(tmp_path),
        enabled=True
    )

    ev1 = pysubs2.SSAEvent(start=1000, end=3500, text="Linia 1")
    ev2 = pysubs2.SSAEvent(start=4000, end=6200, text="Linia 2")
    raw_entries_sample = [
        (0, ev1, "Linia 1", ""),
        (1, ev2, "Linia 2", "")
    ]

    batches = [raw_entries_sample]
    batches_sum = [
        {
            "batch_id": b_idx,
            "line_count": len(b),
            "first_id": b[0][0] if b else None,
            "last_id": b[-1][0] if b else None,
            "start_ms": int(getattr(b[0][1], "start", 0)) if b and len(b[0]) > 1 else 0,
            "end_ms": int(getattr(b[-1][1], "end", 0)) if b and len(b[-1]) > 1 else 0
        }
        for b_idx, b in enumerate(batches)
    ]

    assert batches_sum[0]["start_ms"] == 1000
    assert batches_sum[0]["end_ms"] == 6200
    assert batches_sum[0]["line_count"] == 2
    assert batches_sum[0]["first_id"] == 0
    assert batches_sum[0]["last_id"] == 1

    rec.log_scene_discourse(
        scene_boundaries=[2000, 5000],
        turns=[{"speaker": "PostacAlfa", "lines": [0]}],
        batches_summary=batches_sum
    )

    assert rec.jsonl_path.exists()
    with open(rec.jsonl_path, "r", encoding="utf-8") as f:
        lines = [json.loads(l) for l in f if l.strip()]
    ev_logged = lines[-1]
    assert ev_logged["stage"] == "scene_discourse"
    assert ev_logged["payload"]["batches_summary"][0]["start_ms"] == 1000
    assert ev_logged["payload"]["batches_summary"][0]["end_ms"] == 6200


def test_t11_1_3_2_style_matrix_summary_and_phase1_telemetry(tmp_path):
    """
    T11.1.3_2 (INC-AVT-022): Weryfikacja telemetrii stylow (log_ingestion z get_summary())
    oraz czasu wykonania i zuzycia tokenow w log_phase1_batch.
    """
    import json
    from flight_recorder import EpisodeFlightRecorder

    rec = EpisodeFlightRecorder(
        anime_slug="test_anime",
        filename="test_episode",
        trace_dir=str(tmp_path),
        enabled=True
    )

    style_summary = {"dialogue": 42, "screen_sign": 5, "song": 2}
    rec.log_ingestion(
        encoding="utf-8",
        total_events=49,
        style_matrix=style_summary,
        events_classified=[{"id": 1, "style": "Default", "type_label": "DIALOG", "raw_actor_name": "PostacAlfa"}]
    )

    tok_usage = {"prompt": 12000, "cached": 9500, "output": 1800, "model": "gemini-2.5-flash"}
    rec.log_phase1_batch(
        batch_id=0,
        prompt_dump="[TEST PROMPT]",
        raw_response={"translations": []},
        response_time_sec=4.25,
        token_usage=tok_usage
    )

    assert rec.jsonl_path.exists()
    with open(rec.jsonl_path, "r", encoding="utf-8") as f:
        events = [json.loads(l) for l in f if l.strip()]

    ingest_ev = next(e for e in events if e["stage"] == "ingestion")
    assert ingest_ev["payload"]["style_matrix"] == style_summary
    assert ingest_ev["payload"]["total_events"] == 49

    p1_ev = next(e for e in events if e["stage"] == "phase1_batch")
    assert p1_ev["payload"]["response_time_sec"] == 4.25
    assert p1_ev["payload"]["token_usage"] == tok_usage
    assert p1_ev["payload"]["token_usage"]["model"] == "gemini-2.5-flash"
