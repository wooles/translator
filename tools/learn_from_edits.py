# -*- coding: utf-8 -*-
"""
Standard 12.0.0 (G-2): Samodzielne narzędzie CLI do uczenia systemu z ręcznych poprawek użytkownika.

Porównuje surowy plik wyjściowy AI (--raw) z ręcznie poprawionym plikiem napisów (--edited),
wyciąga różnice przez UserFeedbackManager.ingest_diff_from_subtitles(...) i opcjonalnie (z --en)
zapisuje poprawione pary EN -> PL do TranslationMemory z najwyższym autorytetem quality_tier=1.
"""

from __future__ import annotations

import argparse
import bisect
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import pysubs2

from memory import TranslationMemory, clean_text_for_memory
from user_feedback import UserFeedbackManager

_SKIP_STYLE_RE = re.compile(
    r"(?:^|[\W_])(sign|signs|title|titles|typeset|typesetting|caption|captions|ep_title|op|ed|kara|song|staff|credit)(?:$|[\W_])",
    re.IGNORECASE,
)


def _load_subs_safe(path: Path) -> pysubs2.SSAFile:
    try:
        return pysubs2.load(str(path), encoding="utf-8")
    except Exception:
        return pysubs2.load(str(path), encoding="latin2")


def _strip_ass_overrides(text: str) -> str:
    cleaned = re.sub(r"\{\\?i[01]?\}", "", text or "")
    return cleaned.replace("\\N", " ").replace("\\n", " ").strip()


def _is_non_dialogue_style(style_name: str) -> bool:
    return bool(_SKIP_STYLE_RE.search(str(style_name or "")))


def _resolve_optional_en_path(raw_path: Path, explicit_en: Optional[str]) -> Optional[Path]:
    if explicit_en:
        p = Path(explicit_en)
        return p if p.exists() else None
    stem = raw_path.stem
    base_stem = stem[:-3] if stem.lower().endswith((".pl", ".en")) else stem
    for cand_name in (f"{base_stem}.en.ass", f"{base_stem}.en.srt", f"{stem}.en.ass", f"{stem}.en.srt"):
        cand = raw_path.parent / cand_name
        if cand.exists() and cand.resolve() != raw_path.resolve():
            return cand
    return None


def _build_tier1_pairs_from_diff(
    raw_path: Path,
    edited_path: Path,
    en_path: Path,
    tolerance_ms: int = 350,
) -> List[Dict[str, Any]]:
    subs_raw = _load_subs_safe(raw_path)
    subs_edited = _load_subs_safe(edited_path)
    subs_en = _load_subs_safe(en_path)

    raw_events = sorted(
        [ev for ev in subs_raw.events if not getattr(ev, "is_comment", False)],
        key=lambda ev: ev.start,
    )
    raw_starts = [ev.start for ev in raw_events]

    en_events = sorted(
        [ev for ev in subs_en.events if not getattr(ev, "is_comment", False)],
        key=lambda ev: ev.start,
    )
    en_starts = [ev.start for ev in en_events]

    pairs: List[Dict[str, Any]] = []
    for ev_ed in subs_edited.events:
        if getattr(ev_ed, "is_comment", False):
            continue
        style_ed = str(getattr(ev_ed, "style", "") or "")
        is_non_dlg = _is_non_dialogue_style(style_ed)
        ed_plain = clean_text_for_memory(_strip_ass_overrides(ev_ed.text or ""))
        if not ed_plain:
            continue

        # Locate closest raw event within +-tolerance_ms
        left = bisect.bisect_left(raw_starts, ev_ed.start - tolerance_ms)
        right = bisect.bisect_right(raw_starts, ev_ed.start + tolerance_ms)
        best_raw = None
        best_diff = tolerance_ms + 1
        for i in range(left, right):
            d = abs(raw_events[i].start - ev_ed.start)
            if d < best_diff:
                best_diff = d
                best_raw = raw_events[i]

        if best_raw is None:
            continue
        raw_plain = clean_text_for_memory(_strip_ass_overrides(best_raw.text or ""))
        if not raw_plain or raw_plain == ed_plain:
            continue

        # Locate matching English source event within +-tolerance_ms
        en_left = bisect.bisect_left(en_starts, ev_ed.start - tolerance_ms)
        en_right = bisect.bisect_right(en_starts, ev_ed.start + tolerance_ms)
        best_en = None
        best_en_diff = tolerance_ms + 1
        for i in range(en_left, en_right):
            d = abs(en_events[i].start - ev_ed.start)
            if d < best_en_diff:
                best_en_diff = d
                best_en = en_events[i]

        if best_en is None:
            continue
        en_plain = clean_text_for_memory(_strip_ass_overrides(best_en.text or ""))
        if not en_plain:
            continue

        pairs.append(
            {
                "en": en_plain,
                "pl": ed_plain,
                "is_sign": is_non_dlg,
                "is_song": False,
                "is_staff": False,
                "has_critical_qg_error": False,
            }
        )
    return pairs


def learn_from_edits(
    raw_path: Path,
    edited_path: Path,
    en_path: Optional[Path] = None,
    series_title: str = "",
    scope: str = "global",
    feedback_storage_path: Optional[Path] = None,
    tm_db_path: Optional[Path] = None,
) -> Dict[str, int]:
    """
    Runs diff-based learning: writes feedback entries and, when EN subtitles are available,
    ingests human-corrected EN -> PL pairs into TranslationMemory with quality_tier=1.
    """
    fb_manager = UserFeedbackManager(storage_path=feedback_storage_path)
    ingested_feedback = fb_manager.ingest_diff_from_subtitles(
        raw_pl_subs_path=raw_path,
        corrected_pl_subs_path=edited_path,
        scope=scope,
    )

    tm_ingested = 0
    resolved_en = _resolve_optional_en_path(raw_path, str(en_path) if en_path else None)
    if resolved_en is not None:
        tier1_pairs = _build_tier1_pairs_from_diff(raw_path, edited_path, resolved_en)
        if tier1_pairs:
            tm = TranslationMemory(db_path=tm_db_path) if tm_db_path is not None else TranslationMemory()
            tm_ingested = tm.ingest_episode_pairs(
                tier1_pairs,
                series_title=series_title or raw_path.stem,
                quality_tier=1,
            )

    return {
        "feedback_entries": len(ingested_feedback),
        "tm_tier1_pairs": tm_ingested,
    }


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Uczenie pamięci AVT z ręcznych korekt napisów użytkownika (Standard 12.0.0, G-2)."
    )
    parser.add_argument("--raw", required=True, help="Ścieżka do surowego pliku napisów wygenerowanego przez AI.")
    parser.add_argument("--edited", required=True, help="Ścieżka do pliku napisów poprawionego przez Operatora.")
    parser.add_argument("--en", default=None, help="Opcjonalna ścieżka do oryginalnych napisów angielskich (.en.ass/.en.srt).")
    parser.add_argument("--series", default="", help="Nazwa serii dla wpisów TranslationMemory (quality_tier=1).")
    parser.add_argument("--scope", choices=["global", "series"], default="global", help="Zakres reguł w UserFeedbackManager.")
    parser.add_argument("--feedback-file", default=None, help="Opcjonalna ścieżka do pliku JSON feedbacku.")
    parser.add_argument("--tm-db", default=None, help="Opcjonalna ścieżka do bazy SQLite TranslationMemory.")
    args = parser.parse_args(argv)

    raw_p = Path(args.raw)
    edited_p = Path(args.edited)
    if not raw_p.exists():
        print(f"[BŁĄD] Brak pliku --raw: {raw_p}", file=sys.stderr)
        return 2
    if not edited_p.exists():
        print(f"[BŁĄD] Brak pliku --edited: {edited_p}", file=sys.stderr)
        return 2

    en_p = Path(args.en) if args.en else None
    fb_p = Path(args.feedback_file) if args.feedback_file else None
    tm_p = Path(args.tm_db) if args.tm_db else None

    result = learn_from_edits(
        raw_path=raw_p,
        edited_path=edited_p,
        en_path=en_p,
        series_title=args.series,
        scope=args.scope,
        feedback_storage_path=fb_p,
        tm_db_path=tm_p,
    )
    print(
        f"[learn_from_edits G-2] Zapisano poprawek feedbacku: {result['feedback_entries']} | "
        f"Par TM (quality_tier=1): {result['tm_tier1_pairs']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
