# -*- coding: utf-8 -*-
"""
Series Bible & Cross-Episode Continuity Module.
Automatically accumulates knowledge, character profiles, honorific forms, and terminology
across consecutive episodes of the same anime, ensuring 100% consistency across the entire season.
"""

import os
import re
import json
from pathlib import Path
from typing import Dict, List, Any, Optional

SERIES_MEMORY_DIR = Path(__file__).parent / "series_memory"

def clean_anime_slug(title: str) -> str:
    """Creates a filesystem-safe identifier slug from anime title."""
    if not title:
        return "default_series"
    slug = re.sub(r"[^\w\s-]", "", title, flags=re.UNICODE).strip()
    slug = re.sub(r"[-\s]+", "_", slug)
    return slug[:50] or "default_series"

class SeriesBible:
    def __init__(self, anime_title: str, storage_dir: Optional[Path] = None):
        self.anime_title = anime_title.strip() if anime_title else "Nieznana Seria"
        self.slug = clean_anime_slug(self.anime_title)
        self.storage_dir = storage_dir or SERIES_MEMORY_DIR
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.file_path = self.storage_dir / f"{self.slug}_bible.json"
        
        self.data: Dict[str, Any] = {
            "anime_title": self.anime_title,
            "characters": {},          # { "Arata": {"gender": "męska", "role": "uczeń", "forms": "Arata"} }
            "glossary": {},            # { "Choushi": "czara na sake", "Dragon Slayer": "Pogromca Smoków" }
            "relationships": {},      # { "Kokoro->Arata": "po imieniu / na ty", "Uczniowie->Teshima": "pani Teshima" }
            "episodes_translated": []  # ["odcinek 1", "odcinek 2"]
        }
        self.load()

    def load(self):
        """Loads existing Series Bible from disk."""
        if self.file_path.exists():
            try:
                with open(self.file_path, "r", encoding="utf-8") as f:
                    saved_data = json.load(f)
                    if isinstance(saved_data, dict):
                        for k, v in saved_data.items():
                            if k in self.data and isinstance(v, dict):
                                self.data[k].update(v)
                            elif k in self.data and isinstance(v, list):
                                for item in v:
                                    if item not in self.data[k]:
                                        self.data[k].append(item)
            except Exception:
                pass

    def save(self):
        """Saves current Series Bible state to disk."""
        try:
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def update_from_episode_profile(self, episode_name: str, characters: Dict[str, str], glossary: Dict[str, str]):
        """Updates glossary and character registry based on Profiler output of a new episode."""
        if episode_name and episode_name not in self.data["episodes_translated"]:
            self.data["episodes_translated"].append(episode_name)

        if characters:
            for name, details in characters.items():
                if name not in self.data["characters"]:
                    self.data["characters"][name] = {"description": details}
                else:
                    self.data["characters"][name]["description"] = details

        if glossary:
            for k, v in glossary.items():
                # Store non-trivial terms only
                if k and v and len(k) > 1 and len(v) > 1:
                    self.data["glossary"][k] = v

        self.save()

    def format_for_prompt(self) -> str:
        """Formats Series Bible into a compact section for LLM prompt injection."""
        lines = []
        has_content = False

        if self.data["characters"] or self.data["glossary"]:
            lines.append("--- BIBLIA SERIALU (PAMIĘĆ MIĘDZYODCINKOWA SEZONU) ---")
            lines.append(f"Seria: '{self.anime_title}' (Przetłumaczono odcinków: {len(self.data['episodes_translated'])})")
            
            if self.data["characters"]:
                lines.append("• Kluczowe postacie z poprzednich odcinków:")
                for name, info in list(self.data["characters"].items())[:8]:
                    desc = info.get("description", "") if isinstance(info, dict) else str(info)
                    lines.append(f"  - {name}: {desc}")
                has_content = True

            if self.data["glossary"]:
                lines.append("• Ustalone nazwy i terminologia z poprzednich odcinków (ZACHOWAJ SPÓJNOŚĆ!):")
                for src, trg in list(self.data["glossary"].items())[:12]:
                    lines.append(f"  - '{src}' -> '{trg}'")
                has_content = True

            lines.append("-------------------------------------------------------\n")

        return "\n".join(lines) if has_content else ""
