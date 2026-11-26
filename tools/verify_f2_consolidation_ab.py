"""
Narzędzie A/B weryfikacji konsolidacji paczek Fazy 2 (Standard 12.0.0 F-1 / Bramka §4.1).
Wczytuje plik *_events.jsonl (bez FFmpeg/Whisper/Profilera/F1), rekonstruuje pełne paczki F1
oraz porównuje wariant A (mikropaczki 1:1) vs wariant B (skonsolidowane paczki <= 48 linii).

Użycie:
    python tools/verify_f2_consolidation_ab.py --events logs/..._events.jsonl [--live]
"""

import argparse
import json
import os
import sys
import types
from pathlib import Path
from typing import Any, Dict, List

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pricing_guard import PricingGuard
from translator import MultimodalTranslator


def load_phase2_items_from_events(events_path: Path) -> Dict[int, Dict[str, Any]]:
    """
    Reconstructs F1 batches and Phase 2 candidate pools from FlightRecorder events.jsonl.
    Prefers real scene_discourse (batches_summary) + line_evolution + phase1_batch.scene_diagnosis
    schema, falling back to phase1_batch.items or minimal phase2_verifier logs when absent.
    """
    p1_outputs: Dict[int, Dict[str, Any]] = {}
    if not events_path.exists():
        raise FileNotFoundError(f"Brak pliku zdarzeń: {events_path}")

    batches_summary: List[Dict[str, Any]] = []
    by_line_id: Dict[int, Dict[str, Any]] = {}
    p1_by_batch: Dict[int, Dict[str, Any]] = {}
    p2_by_batch: Dict[int, Dict[str, Any]] = {}

    raw_lines = events_path.read_text(encoding="utf-8").splitlines()
    for line in raw_lines:
        if not line.strip():
            continue
        ev = json.loads(line)
        stage = ev.get("stage")
        payload = ev.get("payload") or {}
        if stage == "scene_discourse":
            bs = payload.get("batches_summary") or []
            if isinstance(bs, list) and bs:
                batches_summary = bs
        elif stage == "line_evolution":
            lid = payload.get("line_id") if payload.get("line_id") is not None else ev.get("line_id")
            if lid is not None:
                by_line_id[int(lid)] = payload
        elif stage == "phase1_batch":
            b_idx = int(ev.get("batch_id", payload.get("batch_id", 0)))
            p1_by_batch[b_idx] = payload
        elif stage == "phase2_verifier":
            b_idx = int(ev.get("batch_id", payload.get("batch_id", 0)))
            p2_by_batch[b_idx] = payload

    # Ścieżka główna: rzeczywisty schemat produkcyjny scene_discourse + line_evolution + phase1_batch
    if batches_summary and by_line_id:
        for b_entry in sorted(batches_summary, key=lambda x: int(x.get("batch_id", 0))):
            b_idx = int(b_entry.get("batch_id", 0))
            first_id = int(b_entry.get("first_id", 0))
            last_id = int(b_entry.get("last_id", first_id - 1))

            items: List[Dict[str, Any]] = []
            for lid in range(first_id, last_id + 1):
                le = by_line_id.get(lid)
                if not le:
                    continue
                start_ms = int(le.get("start_ms", 0) or 0)
                end_ms = int(le.get("end_ms", start_ms) or start_ms)
                t_tag = str(le.get("telemetry_tag") or "")
                actor = str(le.get("actor") or "")
                is_sign = ("[mówca: sign" in t_tag.lower()) or (actor.strip().lower() == "sign")
                items.append({
                    "id": (lid - first_id) + 1,
                    "orig_idx": lid,
                    "en": str(le.get("en_text") or ""),
                    "pl": str(le.get("phase1_pl") or ""),
                    "speaker_name": actor,
                    "audio_jp": str(le.get("jp_audio") or ""),
                    "telemetry_tag": t_tag,
                    "duration_s": max(0.2, (end_ms - start_ms) / 1000.0),
                    "start_ms": start_ms,
                    "end_ms": end_ms,
                    "is_sign": is_sign,
                    "is_song": False,
                    "calque_score": 0.5,
                    "notes": "",
                })

            if not items:
                continue

            p1_payload = p1_by_batch.get(b_idx) or {}
            raw_resp = p1_payload.get("raw_response") or {}
            s_diag = raw_resp.get("scene_diagnosis") if isinstance(raw_resp, dict) else None
            scene_desc = (
                str(s_diag.get("dramatic_context") or f"Paczka {b_idx}")
                if isinstance(s_diag, dict)
                else str(p1_payload.get("scene_desc") or f"Paczka {b_idx}")
            )
            p2_resp = (p2_by_batch.get(b_idx) or {}).get("raw_response") or []
            orig_selected_ids = sorted(
                {int(r.get("id")) for r in p2_resp if isinstance(r, dict) and r.get("id") is not None}
            ) if isinstance(p2_resp, list) else []

            p1_outputs[b_idx] = {
                "b_idx": b_idx,
                "pass1_items": items,
                "scene_desc": scene_desc,
                "scene_diagnosis": s_diag,
                "batch_response": types.SimpleNamespace(scene_diagnosis=s_diag) if s_diag else None,
                "episode_profile_str": "",
                "user_feedback_str": "",
                "glossary_str": "",
                "scoped_series_bible_str": "",
                "manga_canon_str": "",
                "episode_profile": None,
                "lookback_history": [],
                "lookahead_events": [],
                "orig_selected_ids": orig_selected_ids,
                "_reconstructed_full_f1": True,
                "_already_selected": False,
            }
        if p1_outputs:
            return p1_outputs

    # Ścieżka pośrednia: jawne payload["items"] / payload["pass1_items"] w phase1_batch
    for b_idx in sorted(p1_by_batch.keys()):
        payload = p1_by_batch[b_idx]
        items = payload.get("items") or payload.get("pass1_items") or []
        if not items:
            continue
        raw_resp = payload.get("raw_response") or {}
        s_diag = raw_resp.get("scene_diagnosis") if isinstance(raw_resp, dict) else None
        p1_outputs[b_idx] = {
            "b_idx": b_idx,
            "pass1_items": items,
            "scene_desc": str(payload.get("scene_desc") or f"Paczka {b_idx}"),
            "scene_diagnosis": s_diag,
            "batch_response": types.SimpleNamespace(scene_diagnosis=s_diag) if s_diag else None,
            "episode_profile_str": "",
            "user_feedback_str": "",
            "glossary_str": "",
            "scoped_series_bible_str": "",
            "manga_canon_str": "",
            "episode_profile": None,
            "lookback_history": [],
            "lookahead_events": [],
            "_reconstructed_full_f1": True,
            "_already_selected": False,
        }
    if p1_outputs:
        return p1_outputs

    # Fallback dla uproszczonych logów zawierających wyłącznie phase2_verifier (już wyselekcjonowane linie)
    for b_idx in sorted(p2_by_batch.keys()):
        payload = p2_by_batch[b_idx]
        raw_resp = payload.get("raw_response") or []
        if isinstance(raw_resp, list) and raw_resp:
            recon_items = []
            for idx_r, r in enumerate(raw_resp, start=1):
                if isinstance(r, dict):
                    recon_items.append({
                        "id": int(r.get("id", idx_r)),
                        "en": str(r.get("en") or f"Line {idx_r} source."),
                        "pl": str(r.get("pl") or r.get("refined_pl") or ""),
                        "notes": str(r.get("changes_made") or ""),
                        "calque_score": 0.35,
                    })
            if recon_items:
                p1_outputs[b_idx] = {
                    "b_idx": b_idx,
                    "pass1_items": recon_items,
                    "scene_desc": f"Paczka {b_idx}",
                    "scene_diagnosis": None,
                    "batch_response": None,
                    "episode_profile_str": "",
                    "user_feedback_str": "",
                    "glossary_str": "",
                    "scoped_series_bible_str": "",
                    "manga_canon_str": "",
                    "episode_profile": None,
                    "lookback_history": [],
                    "lookahead_events": [],
                    "_reconstructed_full_f1": False,
                    "_already_selected": True,
                }
    return p1_outputs


def _reset_verifier_usage(verifier_obj: Any) -> None:
    tl = getattr(verifier_obj, "_thread_local", None)
    if tl is not None:
        tl.last_batch_token_usage = {}


def _accumulate_verifier_usage(tok_acc: Dict[str, Any], verifier_obj: Any) -> None:
    """Safely accumulates per-call token usage recorded by DialogueVerifier._thread_local."""
    tl = getattr(verifier_obj, "_thread_local", None)
    usage = getattr(tl, "last_batch_token_usage", None) if tl is not None else None
    if not isinstance(usage, dict):
        return
    tok_acc["prompt"] += int(usage.get("prompt", 0) or 0)
    tok_acc["cached"] += int(usage.get("cached", 0) or 0)
    tok_acc["output"] += int(usage.get("output", 0) or 0)
    tok_acc["thinking"] = tok_acc.get("thinking", 0) + int(usage.get("thinking", 0) or 0)


def run_ab_comparison(events_path: Path, live: bool = False, translator_obj: Any = None) -> int:
    p1_outputs = load_phase2_items_from_events(events_path)
    if not p1_outputs:
        print(f"[AB Harness]: Brak danych F1/F2 w pliku {events_path}")
        return 1

    tr = translator_obj or MultimodalTranslator(
        api_key=os.getenv("GEMINI_API_KEY") or "mock_k0",
        model="gemini-4-hydrogen",
        enable_verifier=True,
    )
    sorted_bidxs = sorted(p1_outputs.keys())
    total_b = max(1, len(sorted_bidxs))
    only_already_selected = all(p1_outputs[b].get("_already_selected", False) for b in sorted_bidxs)

    if only_already_selected:
        variant_a_batches = [(b_idx, list(p1_outputs[b_idx]["pass1_items"])) for b_idx in sorted_bidxs]
        selected_stream = [
            (b_idx, it, p1_outputs[b_idx])
            for b_idx, cands in variant_a_batches
            for it in cands
        ]
        variant_b_groups = []
        for start_i in range(0, len(selected_stream), 48):
            chunk = selected_stream[start_i : start_i + 48]
            chunk_items = []
            id_map = {}
            source_bidxs = []
            scene_descs = []
            for c_pos, (orig_bidx, orig_item, p1_d) in enumerate(chunk, start=1):
                it_c = dict(orig_item)
                orig_lid = int(it_c.get("id", c_pos))
                it_c["id"] = c_pos
                id_map[c_pos] = (orig_bidx, orig_lid)
                chunk_items.append(it_c)
                if orig_bidx not in source_bidxs:
                    source_bidxs.append(orig_bidx)
                    sd = str(p1_d.get("scene_desc") or "").strip()
                    if sd and sd not in scene_descs:
                        scene_descs.append(sd)
            variant_b_groups.append({
                "consolidated_idx": len(variant_b_groups),
                "verifier_items": chunk_items,
                "id_map": id_map,
                "source_bidxs": source_bidxs,
                "scene_desc": "\n--- ZMIANA SCENY ---\n".join(scene_descs),
                "scene_diagnosis": None,
            })
    else:
        episode_remaining = 115
        variant_a_batches = []
        for b_idx in sorted_bidxs:
            cands = tr._select_hydrogen_phase2_candidates(
                p1_outputs[b_idx]["pass1_items"],
                total_batches=total_b,
                episode_line_cap=115,
            )
            if episode_remaining <= 0:
                cands = []
            elif len(cands) > episode_remaining:
                cands = cands[:episode_remaining]
            episode_remaining -= len(cands)
            variant_a_batches.append((b_idx, cands))
        variant_b_groups = tr._consolidate_phase2_batches(p1_outputs, max_lines_per_f2_call=48)

    lines_a = sum(len(items) for _, items in variant_a_batches)
    lines_b = sum(len(g["verifier_items"]) for g in variant_b_groups)
    calls_a = sum(1 for _, items in variant_a_batches if items)
    calls_b = len(variant_b_groups)

    print(f"=== WERYFIKACJA A/B KONSOLIDACJI F2 (F-1) — {events_path.name} ===")
    print(f"Wariant A (1:1 mikropaczki):   {calls_a} wywołań F2, {lines_a} linii")
    print(f"Wariant B (konsolidacja <=48): {calls_b} wywołań F2, {lines_b} linii")

    if not live or (translator_obj is None and not os.getenv("GEMINI_API_KEY")):
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
        _reset_verifier_usage(tr.verifier)
        refined = tr.verifier.verify_batch(
            batch_items=cands,
            scene_summary=p1_d.get("scene_desc", ""),
            scene_diagnosis=p1_d.get("scene_diagnosis"),
            batch_idx=b_idx,
        )
        _accumulate_verifier_usage(tok_a, tr.verifier)
        for r in refined:
            results_a[(b_idx, r.id)] = {"pl": r.refined_pl, "changes": getattr(r, "changes_made", "") or ""}

    for grp in variant_b_groups:
        _reset_verifier_usage(tr.verifier)
        refined = tr.verifier.verify_batch(
            batch_items=grp["verifier_items"],
            scene_summary=grp.get("scene_desc", ""),
            scene_diagnosis=grp.get("scene_diagnosis"),
            batch_idx=grp["consolidated_idx"],
        )
        _accumulate_verifier_usage(tok_b, tr.verifier)
        id_map = grp["id_map"]
        for r in refined:
            if r.id in id_map:
                results_b[id_map[r.id]] = {"pl": r.refined_pl, "changes": getattr(r, "changes_made", "") or ""}

    cost_a = PricingGuard.calculate_actual_cost_pln(zero_f1, tok_a)
    cost_b = PricingGuard.calculate_actual_cost_pln(zero_f1, tok_b)
    diff_pln = cost_a - cost_b
    changes_a = sum(1 for v in results_a.values() if v["changes"] and v["changes"].lower() != "null")
    changes_b = sum(1 for v in results_b.values() if v["changes"] and v["changes"].lower() != "null")
    print(f"Tokeny F2 (in/out/cached): A=({tok_a['prompt']}/{tok_a['output']}/{tok_a['cached']}) vs B=({tok_b['prompt']}/{tok_b['output']}/{tok_b['cached']})")
    print(f"Koszt F2 PLN netto: A={cost_a:.4f} vs B={cost_b:.4f} (różnica={diff_pln:.4f} PLN)")
    print(f"Werdykt bramki §4.1 (spadek >= 0.50 PLN): {'PASS' if diff_pln >= 0.50 else 'BELOW_THRESHOLD'}")
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
