# -*- coding: utf-8 -*-
"""
User Feedback & Few-Shot Memory Module.
Stores user-submitted corrections and flawed patterns,
and injects them as Golden Examples into the AI prompt
as well as supplying the dynamic AVT rule linter.
"""

import os
import re
import json
import time
from pathlib import Path
from typing import List, Dict, Any, Optional

FEEDBACK_FILE_PATH = Path(__file__).parent / "user_feedback.json"

class UserFeedbackManager:
    """
    Manager for persistent user corrections and few-shot rules.
    """
    def __init__(self, storage_path: Optional[Path] = None):
        self.storage_path = storage_path or FEEDBACK_FILE_PATH
        self.feedback_list: List[Dict[str, Any]] = []
        self.load()

    def load(self):
        """Loads feedback database from JSON file."""
        if self.storage_path.exists():
            try:
                with open(self.storage_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        self.feedback_list = data
            except Exception:
                self.feedback_list = []
        else:
            # Default initial golden rules based on common user guidelines
            self.feedback_list = [
                {
                    "id": "init_1",
                    "original_en": "I hope so / I have hope",
                    "bad_pl": "Mam taką nadzieję / Mam nadzieję na to",
                    "good_pl": "Oby! / Mam nadzieję!",
                    "rule_reason": "W mowie potocznej unikamy sztucznego 'Mam taką nadzieję', stosujemy naturalne 'Oby!' lub zwięzłe 'Mam nadzieję'.",
                    "scope": "global",
                    "created_at": time.strftime("%Y-%m-%d %H:%M:%S")
                },
                {
                    "id": "init_2",
                    "original_en": "It makes sense / That makes sense",
                    "bad_pl": "To robi sens / Robi to sens",
                    "good_pl": "To ma sens / Ma to sens / Zrozumiałe",
                    "rule_reason": "Bezwzględny zakaz kalki 'robi sens'. Po polsku rzeczownik 'sens' łączy się wyłącznie z czasownikiem 'mieć'.",
                    "scope": "global",
                    "created_at": time.strftime("%Y-%m-%d %H:%M:%S")
                },
                {
                    "id": "init_3",
                    "original_en": "Welcome back",
                    "bad_pl": "Witaj z powrotem",
                    "good_pl": "Witaj! / Dobrze cię widzieć! / Wróciłeś!",
                    "rule_reason": "Zakaz amerykanizmu 'Witaj z powrotem'. Po polsku witamy osobę słowem 'Witaj!' lub 'Wróciłeś!'.",
                    "scope": "global",
                    "created_at": time.strftime("%Y-%m-%d %H:%M:%S")
                },
                {
                    "id": "init_4",
                    "original_en": "It's you, Young Lord",
                    "bad_pl": "To pan, Młody Panie.",
                    "good_pl": "To ty, młody panie.",
                    "rule_reason": "Tautologia 'pan... Panie' jest błędem. Używamy zaimka 'ty' i małej litery w wołaczu tytularnym.",
                    "scope": "global",
                    "created_at": time.strftime("%Y-%m-%d %H:%M:%S")
                },
                {
                    "id": "init_5",
                    "original_en": "Sensei, I'm done!",
                    "bad_pl": "Pani Sensei, skończyłam!",
                    "good_pl": "Sensei, skończyłam! / Pani Teshimo, skończyłam!",
                    "rule_reason": "Zakaz hybryd honoryfikatywnych 'Pani Sensei'. Albo sam japoński tytuł 'Sensei', albo polska forma 'Pani [Nazwisko]'.",
                    "scope": "global",
                    "created_at": time.strftime("%Y-%m-%d %H:%M:%S")
                }
            ]
            self.save()

    def save(self):
        """Saves feedback database to disk."""
        try:
            with open(self.storage_path, "w", encoding="utf-8") as f:
                json.dump(self.feedback_list, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def add_feedback(
        self,
        original_en: str,
        bad_pl: str,
        good_pl: str,
        rule_reason: str = "",
        scope: str = "global"
    ) -> Dict[str, Any]:
        """Adds a new correction entry to the database."""
        new_entry = {
            "id": f"fb_{int(time.time()*1000)}",
            "original_en": original_en.strip(),
            "bad_pl": bad_pl.strip(),
            "good_pl": good_pl.strip(),
            "rule_reason": rule_reason.strip() or "Poprawka jakościowa użytkownika",
            "scope": scope.strip() or "global",
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        # Prevent duplicates with the same bad_pl and good_pl
        self.feedback_list = [
            f for f in self.feedback_list
            if not (f.get("bad_pl", "").lower() == new_entry["bad_pl"].lower() and
                    f.get("good_pl", "").lower() == new_entry["good_pl"].lower())
        ]
        self.feedback_list.append(new_entry)
        self.save()
        return new_entry

    def remove_feedback(self, feedback_id: str) -> bool:
        """Removes a correction by its ID."""
        initial_len = len(self.feedback_list)
        self.feedback_list = [f for f in self.feedback_list if f.get("id") != feedback_id]
        if len(self.feedback_list) < initial_len:
            self.save()
            return True
        return False

    def list_all(self, scope: Optional[str] = None) -> List[Dict[str, Any]]:
        """Returns list of all rules, optionally filtered by scope."""
        if not scope or scope == "all":
            return list(self.feedback_list)
        return [f for f in self.feedback_list if f.get("scope") in ["global", scope]]

    def find_relevant_feedback(
        self,
        query_texts: List[str],
        anime_title: str = "",
        max_examples: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Searches for the most relevant corrections for given dialogue lines.
        """
        if not self.feedback_list or not query_texts:
            return []

        relevant: List[Dict[str, Any]] = []
        seen_ids = set()

        # 1. Check direct phrase matching
        for q in query_texts:
            q_clean = q.strip().lower()
            if len(q_clean) < 3:
                continue

            for fb in self.feedback_list:
                fb_id = fb.get("id")
                if fb_id in seen_ids:
                    continue

                fb_scope = fb.get("scope", "global")
                if fb_scope != "global" and anime_title and fb_scope.lower() not in anime_title.lower():
                    continue

                orig_en = fb.get("original_en", "").lower()
                bad_pl = fb.get("bad_pl", "").lower()

                # Match by English original or Polish calque
                if orig_en and (orig_en in q_clean or q_clean in orig_en):
                    relevant.append(fb)
                    seen_ids.add(fb_id)
                elif bad_pl and bad_pl in q_clean:
                    relevant.append(fb)
                    seen_ids.add(fb_id)

        # 2. Append general global rules up to max_examples if specific matches are few
        if len(relevant) < max_examples:
            for fb in self.feedback_list:
                fb_id = fb.get("id")
                if fb_id not in seen_ids and fb.get("scope") == "global":
                    relevant.append(fb)
                    seen_ids.add(fb_id)
                    if len(relevant) >= max_examples:
                        break

        return relevant[:max_examples]

    def format_for_prompt(self, relevant_entries: List[Dict[str, Any]]) -> str:
        """
        Formats selected corrections as a Golden Examples section for LLM prompt.
        """
        if not relevant_entries:
            return ""

        lines = [
            "--- ZŁOTE WZORCE I OSOBISTE WYTYCZNE UŻYTKOWNIKA (FEW-SHOT EXAMPLES) ---",
            "BEZWZGLĘDNIE zastosuj poniższe wzorce i unikaj wskazanych błędów z poprzednich wydań:"
        ]
        for fb in relevant_entries:
            en_str = f" [Oryginał EN: \"{fb['original_en']}\"]" if fb.get("original_en") else ""
            lines.append(
                f" • BŁĄD [X]: \"{fb['bad_pl']}\" -> POPRAWNIE [OK]: \"{fb['good_pl']}\"{en_str}\n"
                f"   Wyjaśnienie zasady: {fb['rule_reason']}"
            )
        lines.append("-------------------------------------------------------------------------\n")
        return "\n".join(lines)
