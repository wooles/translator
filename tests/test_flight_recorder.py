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

    events_recorded = []
    rec.record_event = lambda event_type, payload, **kwargs: events_recorded.append((event_type, payload))

    rec.report_step_11_quality_gate(
        quality_gate_fixes=mock_fixes,
        avt_metrics={"cps": 14.2, "cpl": 32},
        pricing_summary={"cost_pln": 0.05}
    )

    assert len(events_recorded) == 1
    ev_type, payload = events_recorded[0]
    assert ev_type == "quality_gate_pricing"

    # Weryfikacja braku ucięcia do 15
    assert len(payload["quality_gate_fixes"]) == 20
    assert payload["quality_gate_fixes"] == mock_fixes

    # Weryfikacja consistency_check
    cc = payload.get("consistency_check", {})
    assert cc.get("status") == "OK"
    assert cc.get("reported") == 20
    assert cc.get("collected") == 20
