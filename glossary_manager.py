# -*- coding: utf-8 -*-
"""
Deterministic Glossary Manager & Terminology Override Module.
Allows defining rigid translations for concepts, character names, attacks, and titles,
which are injected into prompts and strictly enforced in post-processing (100% determinism).
"""

import os
import re
import json
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional

GLOBAL_GLOSSARY_PATH = Path(__file__).parent / "global_glossary.json"

class GlossaryManager:
    """
    Manages global and per-series term glossaries with deterministic overrides.
    """
    def __init__(self, global_path: Optional[Path] = None):
        self.global_path = global_path or GLOBAL_GLOSSARY_PATH
        self.global_terms: Dict[str, Dict[str, str]] = {}
        self.load()

    def load(self):
        """Loads global glossary from JSON file."""
        if self.global_path.exists():
            try:
                with open(self.global_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        self.global_terms = data
            except Exception:
                self.global_terms = {}
        else:
            # Default verified global terms
            self.global_terms = {
                "Your Honor": {"pl": "Wysoki Sądzie", "desc": "Courtroom judicial address"},
                "Four Emperors": {"pl": "Czterej Cesarze", "desc": "Virile numeral (not: Czworo)"},
                "Three Musketeers": {"pl": "Trzej Muszkieterowie", "desc": "Virile numeral"}
            }
            self.save()

    def save(self):
        """Saves global glossary to disk."""
        try:
            with open(self.global_path, "w", encoding="utf-8") as f:
                json.dump(self.global_terms, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def add_term(self, src: str, pl: str, desc: str = "") -> None:
        """Adds or updates a term in the global glossary."""
        if src.strip() and pl.strip():
            self.global_terms[src.strip()] = {
                "pl": pl.strip(),
                "desc": desc.strip()
            }
            self.save()

    def remove_term(self, src: str) -> bool:
        """Removes a term from the global glossary."""
        if src.strip() in self.global_terms:
            del self.global_terms[src.strip()]
            self.save()
            return True
        return False

    def get_combined_glossary(self, series_glossary: Optional[Dict[str, str]] = None, keep_honorifics: bool = True) -> Dict[str, str]:
        """
        Combines global glossary with Series Bible glossary (series takes precedence).
        Returns simple mapping {source_term: target_pl_translation}.
        """
        combined: Dict[str, str] = {}
        # 1. Global terms
        for k, v in self.global_terms.items():
            if not keep_honorifics and k.lower() in ("senpai", "sensei", "kun", "chan", "san", "sama"):
                continue
            combined[k] = v.get("pl", "") if isinstance(v, dict) else str(v)
        # 2. Series-specific terms (override global)
        if series_glossary:
            for k, v in series_glossary.items():
                if k and v:
                    if not keep_honorifics and k.lower() in ("senpai", "sensei", "kun", "chan", "san", "sama"):
                        continue
                    combined[k] = v
        return combined

    def format_for_prompt(self, glossary_dict: Dict[str, str]) -> str:
        """
        Formats glossary for high-priority LLM prompt injection.
        """
        if not glossary_dict:
            return ""

        lines = [
            "--- BEZWZGLĘDNY SŁOWNICZEK POJĘĆ I TERMINOLOGII (WYMÓG DETERMINISTYCZNY) ---",
            "Poniższe pojęcia MUSZĄ być przetłumaczone DOKŁADNIE tak, jak podano poniżej:"
        ]
        for src, raw_trg in glossary_dict.items():
            trg = self.clean_target_term(raw_trg)
            lines.append(f" • '{src}' => '{trg}'")
        lines.append("----------------------------------------------------------------------------\n")
        return "\n".join(lines)

    @classmethod
    def clean_target_term(cls, trg: str) -> str:
        """Removes parenthetical clarifications (e.g., 'Płomień Adolli (Adolla Burst)' -> 'Płomień Adolli')."""
        if not trg:
            return ""
        cleaned = re.sub(r"\s*\([^)]*\)$", "", trg).strip()
        return cleaned if cleaned else trg.strip()

    @classmethod
    def apply_deterministic_overrides(
        cls,
        text: str,
        glossary_dict: Dict[str, str]
    ) -> Tuple[str, List[str]]:
        """
        Post-processing deterministic filter.
        Substitutes untranslated or erroneous terms with the enforced Polish form
        without duplicates or brackets.
        """
        if not text or not glossary_dict:
            return text, []

        modified = text
        applied_fixes = []

        # Sort glossary by length descending so longer phrases match first
        sorted_glossary = sorted(glossary_dict.items(), key=lambda kv: len(kv[0]), reverse=True)

        for src, raw_trg in sorted_glossary:
            if not src or not raw_trg:
                continue

            trg = cls.clean_target_term(raw_trg)
            if not trg or src.lower() == trg.lower():
                continue

            # Prevent duplication if target already exists
            if trg.lower() in modified.lower() and src.lower() in trg.lower():
                continue

            # Check if source term remains untranslated
            pattern_src = re.compile(rf"\b{re.escape(src)}\b", re.IGNORECASE)
            if pattern_src.search(modified):
                modified = pattern_src.sub(trg, modified)
                applied_fixes.append(f"Wymuszenie słownika: '{src}' -> '{trg}'")

        # Clean duplicate parentheses
        modified = re.sub(r"\(([^)]+)\)\s*\(\1\)", r"(\1)", modified)
        modified = re.sub(r"\s+", " ", modified).strip()

        return modified, applied_fixes
