# -*- coding: utf-8 -*-
"""
Historical Feedback Extractor.
Parses the comprehensive 3-week project history (historia_ostatnich_dni.md)
and extracts structured translation rules, prohibitions, and golden examples
directly into user_feedback.json and UserFeedbackManager.
"""

import re
import sys
import json
import time
from pathlib import Path
from typing import List, Dict, Any, Set

from user_feedback import UserFeedbackManager

HISTORY_PATH = Path(__file__).parent / "historia_ostatnich_dni.md"


def extract_rules_from_history(history_file: Path = HISTORY_PATH) -> List[Dict[str, Any]]:
    """
    Parses historia_ostatnich_dni.md and identifies golden translation rules.
    """
    if not history_file.exists():
        return []

    with open(history_file, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()

    extracted_rules = []
    seen_bad = set()

    # Pattern 1: BŁĄD [X]: "..." -> POPRAWNIE [OK]: "..."
    pat_pairs = re.findall(
        r'BŁĄD\s*\[X\]:\s*["„\']([^"\'”]+)["\'”]\s*->\s*POPRAWNIE\s*\[OK\]:\s*["„\']([^"\'”]+)["\'”](?:.*?Wyjaśnienie zasady:\s*([^\n\r]+))?',
        content,
        re.IGNORECASE
    )
    for bad, good, reason in pat_pairs:
        bad_clean = bad.strip()
        good_clean = good.strip()
        if bad_clean.lower() in seen_bad:
            continue
        seen_bad.add(bad_clean.lower())
        extracted_rules.append({
            "original_en": "",
            "bad_pl": bad_clean,
            "good_pl": good_clean,
            "rule_reason": (reason or "Złota reguła z historii projektu").strip(),
            "scope": "global"
        })

    # Pattern 2: Explicit prohibitions: KATEGORYCZNY ZAKAZ / BEZWZGLĘDNY ZAKAZ
    # e.g. "KATEGORYCZNY ZAKAZ: 'duża przerwa'" or "ZAKAZ: 'robi sens'"
    pat_zakaz = re.findall(
        r'(?:KATEGORYCZNY ZAKAZ|BEZWZGLĘDNY ZAKAZ|ZAKAZ|ZAKAZ KALKI)[:\s]+(?:["„\']([^"\'”\n]+)["\'”]|([a-zA-ZąćęłńóśźżĄĆĘŁŃÓŚŹŻ\s\-–—]{3,50}))(?:\s*(?:—|-|->|zamieniamy na|nakaz|stosujemy|używamy)\s*["„\']?([^"\'”\n\.]+))?',
        content,
        re.IGNORECASE
    )
    for match in pat_zakaz:
        bad = (match[0] or match[1]).strip()
        good = (match[2] or "").strip()
        if not bad or len(bad) < 3 or len(bad) > 60:
            continue
        # Clean quotes
        bad = bad.strip("\"'„”")
        good = good.strip("\"'„”")
        if bad.lower() in seen_bad or bad.lower() in ["tego", "kalki", "używania", "zamiany na 1"]:
            continue
        seen_bad.add(bad.lower())
        # Disallow empty or meta placeholder substitutes (never substitute with 'Zgodnie z polskim kanonem AVT')
        if not good or any(m in good.lower() for m in ["kanon", "avt", "filar", "prompt", "zakaz", ">"]):
            continue
        extracted_rules.append({
            "original_en": "",
            "bad_pl": bad,
            "good_pl": good,
            "rule_reason": f"Kanon AVT ustalony w projekcie: zakaz '{bad}' na rzecz '{good}'.",
            "scope": "global"
        })

    return extracted_rules


def sync_history_to_user_feedback() -> int:
    """
    Extracts all rules from history and saves non-duplicate entries to user_feedback.json.
    """
    manager = UserFeedbackManager()
    existing_bads = {fb.get("bad_pl", "").lower().strip() for fb in manager.list_all()}
    
    new_rules = extract_rules_from_history()
    added_count = 0

    for rule in new_rules:
        bad_clean = rule["bad_pl"].lower().strip()
        if bad_clean and bad_clean not in existing_bads:
            manager.add_feedback(
                original_en=rule.get("original_en", ""),
                bad_pl=rule["bad_pl"],
                good_pl=rule["good_pl"],
                rule_reason=rule["rule_reason"],
                scope=rule.get("scope", "global")
            )
            existing_bads.add(bad_clean)
            added_count += 1

    return added_count


if __name__ == "__main__":
    count = sync_history_to_user_feedback()
    print(f"Pomyślnie zsynchronizowano {count} nowych reguł z 3-tygodniowej historii projektu do user_feedback.json!")
