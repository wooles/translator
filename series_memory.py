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
            import re
            for k, v in glossary.items():
                # Store non-trivial terms only and sanitize parenthetical descriptions
                if k and v and len(k) > 1 and len(v) > 1:
                    clean_v = re.sub(r"\s*[\(\[].*?[\)\]]", "", v).strip()
                    self.data["glossary"][k] = clean_v if clean_v else v.strip()

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

    def generate_html_report(self) -> str:
        """Generates a responsive modern dark-mode HTML continuity report of the Series Bible."""
        chars_rows = ""
        for name, info in self.data.get("characters", {}).items():
            desc = info.get("description", "") if isinstance(info, dict) else str(info)
            chars_rows += f"<tr><td><strong>{name}</strong></td><td>{desc}</td></tr>"

        gloss_rows = ""
        for src, trg in self.data.get("glossary", {}).items():
            gloss_rows += f"<tr><td><code>{src}</code></td><td><strong>{trg}</strong></td></tr>"

        rel_rows = ""
        for pair, rel in self.data.get("relationships", {}).items():
            rel_rows += f"<tr><td><strong>{pair}</strong></td><td>{rel}</td></tr>"

        episodes_list = ", ".join(self.data.get("episodes_translated", [])) or "Brak przetłumaczonych odcinków"

        html = f"""<!DOCTYPE html>
<html lang="pl">
<head>
<meta charset="UTF-8">
<title>Biblia Serialu: {self.anime_title}</title>
<style>
  body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #0f172a; color: #f8fafc; margin: 0; padding: 30px; }}
  .container {{ max-width: 900px; margin: 0 auto; background: #1e293b; padding: 30px; border-radius: 12px; box-shadow: 0 10px 25px rgba(0,0,0,0.5); }}
  h1 {{ color: #38bdf8; border-bottom: 2px solid #334155; padding-bottom: 12px; }}
  h2 {{ color: #a855f7; margin-top: 30px; }}
  .badge {{ background: #0284c7; color: white; padding: 4px 10px; border-radius: 6px; font-size: 13px; font-weight: bold; }}
  table {{ width: 100%; border-collapse: collapse; margin-top: 10px; background: #0f172a; border-radius: 8px; overflow: hidden; }}
  th, td {{ padding: 12px 15px; text-align: left; border-bottom: 1px solid #334155; }}
  th {{ background: #1e293b; color: #94a3b8; text-transform: uppercase; font-size: 12px; }}
  tr:hover {{ background: #1e293b; }}
  code {{ background: #334155; padding: 2px 6px; border-radius: 4px; color: #f472b6; }}
  .meta {{ color: #94a3b8; font-size: 14px; margin-bottom: 20px; }}
</style>
</head>
<body>
<div class="container">
  <h1>📖 Biblia Serialu: {self.anime_title}</h1>
  <div class="meta">
    <p>📺 <strong>Przetłumaczone odcinki:</strong> {episodes_list}</p>
    <p>🛡️ <strong>Liczba wpisów w pamięci ciągłości:</strong> {len(self.data.get('characters', {}))} postaci | {len(self.data.get('glossary', {}))} terminów</p>
  </div>

  <h2>👥 Rejestr Postaci i Idiolekty</h2>
  <table>
    <thead><tr><th>Postać</th><th>Opis / Idiolekt / Forma zwracania się</th></tr></thead>
    <tbody>{chars_rows or '<tr><td colspan="2">Brak zarejestrowanych postaci</td></tr>'}</tbody>
  </table>

  <h2>🤝 Matryca Relacji i Honoryfikatorów</h2>
  <table>
    <thead><tr><th>Relacja</th><th>Zasada zwracania się</th></tr></thead>
    <tbody>{rel_rows or '<tr><td colspan="2">Brak zarejestrowanych relacji</td></tr>'}</tbody>
  </table>

  <h2>📚 Słownik Nazw Własnych i Pojęć</h2>
  <table>
    <thead><tr><th>Termin Źródłowy</th><th>Ustalony Przekład Polski</th></tr></thead>
    <tbody>{gloss_rows or '<tr><td colspan="2">Brak ustalonych terminów</td></tr>'}</tbody>
  </table>
</div>
</body>
</html>"""
        return html
