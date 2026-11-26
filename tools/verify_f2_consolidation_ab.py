"""
Narzędzie A/B weryfikacji konsolidacji paczek Fazy 2 (Standard 12.0.0 F-1 / Bramka §4.1).
Wczytuje plik *_events.jsonl (bez FFmpeg/Whisper/Profilera/F1), rekonstruuje kandydatów F2
oraz porównuje wariant A (mikropaczki 1:1) vs wariant B (skonsolidowane paczki <= 48 linii).

Użycie:
    python tools/verify_f2_consolidation_ab.py --events logs/..._events.jsonl [--live]
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pricing_guard import PricingGuard
from translator import MultimodalTranslator


def load_phase2_items_from_events(events_path: Path) -> Dict[int, Dict[str, Any]]:
    """Extracts reconstructed F2 candidate batches from a saved FlightRecorder events.jsonl."""
    p1_outputs: Dict[int, Dict[str, Any]] = {}
    if not events_path.exists():
        raise FileNotFoundError(f"Brak pliku zdarzeń: {events_path}")

    raw_lines = events_path.read_text(encoding="utf-8").splitlines()
    for line in raw_lines:
        if not line.strip():
            continue
        ev = json.loads(line)
        if ev.get("stage") == "phase1_batch":
            b_idx = int(ev.get("batch_id", 0))
            payload = ev.get("payload") or {}
            items = payload.get("items") or payload.get("pass1_items") or []
            if items:
                p1_outputs[b_idx] = {
                    "b_idx": b_idx,
                    "pass1_items": items,
                    "scene_desc": str(payload.get("scene_desc") or f"Paczka {b_idx}"),
                    "batch_response": None,
                    "episode_profile_str": "",
                    "user_feedback_str": "",
                    "glossary_str": "",
                    "scoped_series_bible_str": "",
                    "manga_canon_str": "",
                    "episode_profile": None,
                    "lookback_history": [],
                    "lookahead_events": [],
                }
        elif ev.get("stage") == "phase2_verifier" and int(ev.get("batch_id", -1)) not in p1_outputs:
            b_idx = int(ev.get("batch_id", 0))
            payload = ev.get("payload") or {}
            raw_resp = payload.get("raw_response") or []
            if isinstance(raw_resp, list) and raw_resp:
                recon_items = []
                for idx_r, r in enumerate(raw_resp, start=1):
                    if isinstance(r, dict):
                        recon_items.append({
                            "id": int(r.get("id", idx_r)),
                            "en": str(r.get("en") or f"Line {idx_r} placeholder text."),
                            "pl": str(r.get("refined_pl") or r.get("pl") or ""),
                            "notes": str(r.get("changes_made") or ""),
                            "calque_score": 0.35,
                        })
                if recon_items:
                    p1_outputs[b_idx] = {
                        "b_idx": b_idx,
                        "pass1_items": recon_items,
                        "scene_desc": f"Paczka {b_idx}",
                        "batch_response": None,
                        "episode_profile_str": "",
                        "user_feedback_str": "",
                        "glossary_str": "",
                        "scoped_series_bible_str": "",
                        "manga_canon_str": "",
                        "episode_profile": None,
                        "lookback_history": [],
                        "lookahead_events": [],
                    }
    return p1_outputs


def run_ab_comparison(events_path: Path, live: bool = False) -> int:
    p1_outputs = load_phase2_items_from_events(events_path)
    if not p1_outputs:
        print(f"[AB Harness]: Brak danych F1/F2 w pliku {events_path}")
        return 1

    tr = MultimodalTranslator(api_key=os.getenv("GEMINI_API_KEY") or "mock_k0", model="gemini-4-hydrogen", enable_verifier=True)
    total_b = max(1, len(p1_outputs))
    variant_a_batches = [
        (b_idx, tr._select_hydrogen_phase2_candidates(p1_outputs[b_idx]["pass1_items"], total_batches=total_b))
        for b_idx in sorted(p1_outputs.keys())
    ]
    variant_b_groups = tr._consolidate_phase2_batches(p1_outputs, max_lines_per_f2_call=48)

    lines_a = sum(len(items) for _, items in variant_a_batches)
    lines_b = sum(len(g["verifier_items"]) for g in variant_b_groups)
    calls_a = sum(1 for _, items in variant_a_batches if items)
    calls_b = len(variant_b_groups)

    print(f"=== WERYFIKACJA A/B KONSOLIDACJI F2 (F-1) — {events_path.name} ===")
    print(f"Wariant A (1:1 mikropaczki):   {calls_a} wywołań F2, {lines_a} linii")
    print(f"Wariant B (konsolidacja <=48): {calls_b} wywołań F2, {lines_b} linii")

    if not live or not os.getenv("GEMINI_API_KEY"):
        est_prompt_tokens_saved = max(0, calls_a - calls_b) * 14200
        zero_f1 = {"model": "gemini-4-hydrogen", "prompt": 0, "cached": 0, "output": 0, "thinking": 0}
        est_pln_saved = round(
            PricingGuard.calculate_actual_cost_pln(
                zero_f1,
                {"model": "gemini-4-hydrogen", "prompt": est_prompt_tokens_saved, "cached": 0, "output": 0, "thinking": 0},
            ),
            4,
        )
        print(f"Tryb offline / dry-run (brak --live lub GEMINI_API_KEY): szacowany spadek kosztu promptu F2 = ~{est_pln_saved:.4f} PLN")
        return 0

    results_a: Dict[tuple, Dict[str, str]] = {}
    results_b: Dict[tuple, Dict[str, str]] = {}
    zero_f1 = {"model": "gemini-4-hydrogen", "prompt": 0, "cached": 0, "output": 0, "thinking": 0}
    tok_a = {"model": "gemini-4-hydrogen", "prompt": 0, "cached": 0, "output": 0, "thinking": 0}
    tok_b = {"model": "gemini-4-hydrogen", "prompt": 0, "cached": 0, "output": 0, "thinking": 0}

    for b_idx, cands in variant_a_batches:
        if not cands:
            continue
        p1_d = p1_outputs[b_idx]
        refined = tr.verifier.verify_batch(batch_items=cands, scene_summary=p1_d.get("scene_desc", ""), batch_idx=b_idx)
        for r in refined:
            results_a[(b_idx, r.id)] = {"pl": r.refined_pl, "changes": getattr(r, "changes_made", "") or ""}

    for grp in variant_b_groups:
        refined = tr.verifier.verify_batch(
            batch_items=grp["verifier_items"],
            scene_summary=grp.get("scene_desc", ""),
            scene_diagnosis=grp.get("scene_diagnosis"),
            batch_idx=grp["consolidated_idx"],
        )
        id_map = grp["id_map"]
        for r in refined:
            if r.id in id_map:
                results_b[id_map[r.id]] = {"pl": r.refined_pl, "changes": getattr(r, "changes_made", "") or ""}

    cost_a = PricingGuard.calculate_actual_cost_pln(zero_f1, tok_a)
    cost_b = PricingGuard.calculate_actual_cost_pln(zero_f1, tok_b)
    changes_a = sum(1 for v in results_a.values() if v["changes"] and v["changes"].lower() != "null")
    changes_b = sum(1 for v in results_b.values() if v["changes"] and v["changes"].lower() != "null")
    print(f"Koszt F2 PLN netto: A={cost_a:.4f} vs B={cost_b:.4f} (różnica={cost_a - cost_b:.4f} PLN)")
    print(f"changes_made != null: A={changes_a} vs B={changes_b}")
    for key in sorted(set(results_a.keys()) | set(results_b.keys())):
        pa = results_a.get(key, {}).get("pl", "")
        pb = results_b.get(key, {}).get("pl", "")
        if pa != pb:
            print(f"Różnica {key}: A='{pa}' | B='{pb}'")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="A/B harness dla konsolidacji paczek F2 (Standard 12.0.0 F-1)")
    parser.add_argument("--events", required=True, help="Ścieżka do pliku *_events.jsonl")
    parser.add_argument("--live", action="store_true", help="Uruchamia realne wywołania API (wymaga GEMINI_API_KEY)")
    args = parser.parse_args()
    return run_ab_comparison(Path(args.events), live=args.live)


if __name__ == "__main__":
    raise SystemExit(main())
