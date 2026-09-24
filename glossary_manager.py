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

DANGEROUS_POLISH_HOMOGRAPHS = {
    "to", "no", "do", "on", "i", "a", "ja", "ze", "ma", "te", "ta", "co",
    "ten", "pan", "tam", "dla", "bez", "jak", "sie", "się", "ale", "lub", "czy"
}

class GlossaryManager:
    """
    Manages global and per-series term glossaries with deterministic overrides
    and strict 4-tier authority hierarchy (Manga Canon > Series Bible > Profiler > User Glossary).
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

    def get_combined_glossary(
        self,
        series_glossary: Optional[Dict[str, str]] = None,
        keep_honorifics: bool = True,
        manga_canon_glossary: Optional[Dict[str, str]] = None,
        profiler_glossary: Optional[Dict[str, str]] = None,
        user_glossary: Optional[Dict[str, str]] = None
    ) -> Dict[str, str]:
        """
        Combines glossaries strictly according to the 4-tier authority hierarchy:
        Tier 1 (Highest): Manga Canon (100% official Polish licensed publications)
        Tier 2 (Very High): Series Bible (cross-episode continuity of the season)
        Tier 3 (High): Episode Profile (pre-pass context from current episode & AniList)
        Tier 4 (Lowest - Fallback only): User / Global Glossary (user_glossary or self.global_terms)

        Any collision is resolved in favor of higher tiers, completely preventing
        unintended or low-quality user entries from overriding canon, series continuity, or episode context.
        """
        combined: Dict[str, str] = {}

        def _normalize_key(k: str) -> str:
            return k.strip().lower()

        # Helper to safely put entries into combined dictionary with case-insensitive collision purge
        def _merge_layer(source_dict: Optional[Dict[str, str]], is_user_fallback: bool = False):
            if not source_dict:
                return
            for k, raw_v in source_dict.items():
                if not k or not raw_v:
                    continue
                k_clean = k.strip()
                v_clean = raw_v.get("pl", "") if isinstance(raw_v, dict) else str(raw_v).strip()
                if not k_clean or not v_clean:
                    continue

                if not keep_honorifics and k_clean.lower() in ("senpai", "sensei", "kun", "chan", "san", "sama"):
                    continue

                # Layer 4 (User Glossary) Safety Gates:
                if is_user_fallback:
                    # Guard 1: Filter out dangerous short words / Polish homographs (e.g. 'to', 'no', 'do', 'on')
                    if " " not in k_clean and (len(k_clean) < 3 or k_clean.lower() in DANGEROUS_POLISH_HOMOGRAPHS):
                        continue
                    # Guard 2: Reject identical src == trg
                    if k_clean.lower() == v_clean.lower():
                        continue

                # Remove any existing collision (case-insensitive)
                norm_k = _normalize_key(k_clean)
                keys_to_remove = [existing_k for existing_k in combined.keys() if _normalize_key(existing_k) == norm_k]
                for old_k in keys_to_remove:
                    del combined[old_k]

                combined[k_clean] = v_clean

        # 1. Tier 4 (Lowest): User / Global Glossary
        user_terms = user_glossary if user_glossary is not None else self.global_terms
        _merge_layer(user_terms, is_user_fallback=True)

        # 2. Tier 3 (High): Episode Profile
        _merge_layer(profiler_glossary, is_user_fallback=False)

        # 3. Tier 2 (Very High): Series Bible
        _merge_layer(series_glossary, is_user_fallback=False)

        # 4. Tier 1 (Highest - Absolute): Manga Canon
        _merge_layer(manga_canon_glossary, is_user_fallback=False)

        return combined

    def format_for_prompt(
        self,
        glossary_dict: Dict[str, str],
        user_fallback_dict: Optional[Dict[str, str]] = None
    ) -> str:
        """
        Formats glossary for high-priority LLM prompt injection with strict hierarchy transparency.
        """
        if not glossary_dict and not user_fallback_dict:
            return ""

        lines = [
            "--- BEZWZGLĘDNY SŁOWNICZEK POJĘĆ I TERMINOLOGII (BAZA KANONICZNA W MIANOWNIKU) ---",
            "Poniższe pojęcia to kanoniczne polskie odpowiedniki (podane w mianowniku jako forma bazowa).",
            "W zdaniach BEZWZGLĘDNIE ODMIENIAJ JE PRZEZ PRZYPADKI zgodnie z polską gramatyką i przyimkami (np. 'Twierdza Goryōkaku' -> 'w twierdzy Goryōkaku', 'do twierdzy Goryōkaku', 'Więzienie Akō' -> 'w więzieniu Akō', 'z więzienia Akō'; ZAKAZ sztywnego mianownika po przyimkach typu 'w Twierdza'!).",
            "ZAKAZ PLEONAZMÓW DESKRYPTORÓW: jeśli w zdaniu występuje już deskryptor ('z prowincji', 'w twierdzy', 'na górze', 'w rzece', 'w kronice'), NIE DOKLEJAJ go powtórnie z bazy (napisz 'z prowincji Shimotsuke', a KATEGORYCZNIE NIE 'z prowincji Prowincja Shimotsuke'; 'na górze Hiei', a NIE 'na górze Góra Hiei')! ZAKAZ mechanicznego powtarzania tego samego słowa."
        ]
        for src, raw_trg in (glossary_dict or {}).items():
            trg = self.clean_target_term(raw_trg)
            lines.append(f" • '{src}' => '{trg}'")

        if user_fallback_dict:
            lines.append("\n--- POMOCNICZE SUGESTIE SŁOWNIKOWE (NISKI PRIORYTET) ---")
            lines.append("Poniższe propozycje użytkownika stosuj WYŁĄCZNIE wtedy, gdy nie naruszają powyższego kanonu, kontekstu sceny ani naturalnej polszczyzny:")
            for src, raw_trg in user_fallback_dict.items():
                trg = self.clean_target_term(raw_trg)
                lines.append(f" • [Sugestia pomocnicza] '{src}' => '{trg}'")

        lines.append("----------------------------------------------------------------------------\n")
        return "\n".join(lines)

    @classmethod
    def clean_target_term(cls, trg: str) -> str:
        """Removes parenthetical clarifications (e.g., 'Tus (Miasto w Persji)' -> 'Tus', 'Płomień Adolli (Adolla Burst)' -> 'Płomień Adolli')."""
        if not trg:
            return ""
        cleaned = re.sub(r"\s*[\(\[].*?[\)\]]", "", trg).strip()
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

        DESCRIPTOR_STEM_GROUPS = [
            r"prowincj",
            r"prefektur",
            r"gór|górz",
            r"rzek|rzec",
            r"jezior",
            r"morz",
            r"dolin",
            r"wysp",
            r"zatok|zatoc",
            r"przełęcz",
            r"zamk|zame",
            r"twierdz",
            r"świątyn",
            r"chram",
            r"bram",
            r"miast|mieśc",
            r"dystrykt|dystrykc",
            r"ziem",
            r"księstw",
            r"królestw",
            r"cesarstw",
            r"państw",
            r"kraj",
            r"kronik|kronic",
            r"księg|księdz",
            r"traktat|traktac",
        ]

        # Sort glossary by length descending so longer phrases match first
        sorted_glossary = sorted(glossary_dict.items(), key=lambda kv: len(kv[0]), reverse=True)

        for src, raw_trg in sorted_glossary:
            if not src or not raw_trg:
                continue

            # Stopword & safety protection: do not substitute single short words that collide with Polish
            if " " not in src and (len(src) < 3 or src.lower() in DANGEROUS_POLISH_HOMOGRAPHS):
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
                # Anti-Pleonasm Descriptor Guard:
                # If target term starts with a descriptor (e.g. 'Prowincja Shimotsuke', 'Góra Hiei')
                # and the word preceding the match in 'modified' is ALREADY that descriptor in any case
                # (e.g. 'z prowincji Shimotsuke'), substitute only the core name to avoid 'z prowincji Prowincja Shimotsuke'.
                trg_parts = trg.split(" ", 1)
                has_desc = False
                desc_word = ""
                core_name = trg
                matched_grp = None
                if len(trg_parts) == 2:
                    desc_word = trg_parts[0]
                    core_name = trg_parts[1]
                    for grp in DESCRIPTOR_STEM_GROUPS:
                        if re.match(rf"^(?:{grp})", desc_word, re.IGNORECASE):
                            has_desc = True
                            matched_grp = grp
                            break

                def _sub_target(m):
                    if has_desc and matched_grp:
                        before = modified[:m.start()].rstrip()
                        prev_word_match = re.search(r"\b([A-ZĄĆĘŁŃÓŚŹŻa-ząćęłńóśźż]+)$", before)
                        if prev_word_match:
                            prev_w = prev_word_match.group(1).lower()
                            if re.match(rf"^(?:{matched_grp})", prev_w, re.IGNORECASE):
                                return core_name
                    return trg

                new_mod = pattern_src.sub(_sub_target, modified)
                if new_mod != modified:
                    modified = new_mod
                    applied_fixes.append(f"Wymuszenie słownika: '{src}' -> '{trg}'")

        # Sanitize toponymic and descriptor pleonasms & stuttering (Filar CLXXXIV - 0.00 PLN)
        from series_memory import sanitize_toponymic_pleonasms_and_stuttering
        modified = sanitize_toponymic_pleonasms_and_stuttering(modified)

        # Clean duplicate parentheses
        modified = re.sub(r"\(([^)]+)\)\s*\(\1\)", r"(\1)", modified)
        modified = re.sub(r"\s+", " ", modified).strip()

        return modified, applied_fixes
