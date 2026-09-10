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


def generate_polish_name_declension(name: str, gender: str = "UNKNOWN") -> Dict[str, str]:
    """
    Generates 7 grammatical cases for Japanese / foreign anime character names
    following standard Polish literary AVT phonological rules.
    """
    n = name.strip()
    g = gender.upper()
    if not n:
        return {}

    words = n.split()
    if len(words) > 1:
        sub_decls = [generate_polish_name_declension(w, gender) for w in words]
        if all(sub_decls):
            return {
                case: " ".join(d.get(case, w) for d, w in zip(sub_decls, words))
                for case in ["M", "D", "C", "B", "N", "Ms", "W"]
            }

    # Female names ending in consonant or vowel other than -a: strictly undeclined in Polish
    if g == "FEMALE" or "KOBIETA" in g or "ŻEŃSK" in g:
        if n.endswith("a"):
            stem = n[:-1]
            c_ms = stem + "e"
            if stem.endswith("k"):
                c_ms = stem[:-1] + "ce"
            elif stem.endswith("g"):
                c_ms = stem[:-1] + "dze"
            elif stem.endswith("r"):
                c_ms = stem[:-1] + "rze"
            elif stem.endswith("t"):
                c_ms = stem[:-1] + "cie"
            elif stem.endswith("d"):
                c_ms = stem[:-1] + "dzie"
            elif stem.endswith("s"):
                c_ms = stem[:-1] + "sie"
            elif stem.endswith("n"):
                c_ms = stem[:-1] + "nie"
            elif stem.endswith("m"):
                c_ms = stem[:-1] + "mie"
            return {
                "M": n,
                "D": stem + ("i" if stem[-1] in "kg" else "y"),
                "C": c_ms,
                "B": stem + "ę",
                "N": stem + "ą",
                "Ms": c_ms,
                "W": stem + "o"
            }
        else:
            return {"M": n, "D": n, "C": n, "B": n, "N": n, "Ms": n, "W": n}
    else:
        # Male / neutral
        if n.endswith("a"):
            stem = n[:-1]
            c_ms = stem + "e"
            if stem.endswith("k"):
                c_ms = stem[:-1] + "ce"
            elif stem.endswith("g"):
                c_ms = stem[:-1] + "dze"
            elif stem.endswith("r"):
                c_ms = stem[:-1] + "rze"
            elif stem.endswith("t"):
                c_ms = stem[:-1] + "cie"
            elif stem.endswith("d"):
                c_ms = stem[:-1] + "dzie"
            elif stem.endswith("s"):
                c_ms = stem[:-1] + "sie"
            elif stem.endswith("n"):
                c_ms = stem[:-1] + "nie"
            elif stem.endswith("m"):
                c_ms = stem[:-1] + "mie"
            return {
                "M": n,
                "D": stem + ("i" if stem[-1] in "kg" else "y"),
                "C": c_ms,
                "B": stem + "ę",
                "N": stem + "ą",
                "Ms": c_ms,
                "W": stem + "o"
            }
        elif n[-1].lower() not in "aeiouy":
            stem = n
            last_c = n[-1].lower()
            last_2c = n[-2:].lower() if len(n) >= 2 else ""
            if last_c in ("l", "k", "g", "j", "c") or last_2c in ("ch", "cz", "sz", "rz"):
                c_ms = stem + "u"
                c_w = stem + "u"
            elif last_c == "r":
                c_ms = stem[:-1] + "rze"
                c_w = stem[:-1] + "rze"
            elif last_c == "t":
                c_ms = stem[:-1] + "cie"
                c_w = stem[:-1] + "cie"
            elif last_c == "d":
                c_ms = stem[:-1] + "dzie"
                c_w = stem[:-1] + "dzie"
            else:
                c_ms = stem + "ie"
                c_w = stem + "ie"

            return {
                "M": n,
                "D": stem + "a",
                "C": stem + "owi",
                "B": stem + "a",
                "N": stem + "em",
                "Ms": c_ms,
                "W": c_w
            }
        else:
            return {"M": n, "D": n, "C": n, "B": n, "N": n, "Ms": n, "W": n}


def sanitize_lexical_text(text: str) -> str:
    """Sanitizes text against known LLM/OCR typos and deformed Polish words (Filar CLXIV)."""
    if not text:
        return ""
    TYPO_NORMALIZATIONS = [
        (r"(^|[^\w]|\\[Nnh])([Ss])pyh(am|asz|a|amy|acie|ają|ać|ał|ała|ało|ali|ały|ano)\b", r"\g<1>\g<2>pyt\g<3>"),
        (r"(^|[^\w]|\\[Nnh])([Ww])ziąść\b", r"\g<1>\g<2>ziąć"),
        (r"(^|[^\w]|\\[Nnh])([Pp])oszłem\b", r"\g<1>\g<2>oszedłem"),
        (r"(^|[^\w]|\\[Nnh])([Ww])łancza(ć|m|sz|my|cie|ją|ł|ła|ło|li|ły|no|nie|nia|niem)?\b", r"\g<1>\g<2>łącza\g<3>"),
        (r"(^|[^\w]|\\[Nnh])([Ww])yłancza(ć|m|sz|my|cie|ją|ł|ła|ło|li|ły|no|nie|nia|niem)?\b", r"\g<1>\g<2>yłącza\g<3>"),
        (r"(^|[^\w]|\\[Nnh])([Nn])a\s+codzień\b", r"\g<1>\g<2>a co dzień"),
        (r"(^|[^\w]|\\[Nnh])([Cc])onajmniej\b", r"\g<1>\g<2>o najmniej"),
        (r"(^|[^\w]|\\[Nnh])([Nn])arazie\b", r"\g<1>\g<2>a razie"),
        (r"(^|[^\w]|\\[Nnh])([Zz])\s+przed\b", r"\g<1>sprzed"),
        (r"(^|[^\w]|\\[Nnh])([Zz])\s+poza\b", r"\g<1>spoza"),
        # Anti-calque titular normalizations: 'Aura od Gilotyny' -> 'Aura Gilotyna' (Filar XCVIII/CLXV)
        (r"(^|[^\w]|\\[Nnh])([Aa])ura\s+od\s+[Gg]ilotyny\b", r"\g<1>\g<2>ura Gilotyna"),
        (r"(^|[^\w]|\\[Nnh])([Aa])ury\s+od\s+[Gg]ilotyny\b", r"\g<1>\g<2>ury Gilotyny"),
        (r"(^|[^\w]|\\[Nnh])([Aa])urze\s+od\s+[Gg]ilotyny\b", r"\g<1>\g<2>urze Gilotynie"),
        (r"(^|[^\w]|\\[Nnh])([Aa])urę\s+od\s+[Gg]ilotyny\b", r"\g<1>\g<2>urę Gilotynę"),
        (r"(^|[^\w]|\\[Nnh])([Aa])urą\s+od\s+[Gg]ilotyn(?:ą|y)\b", r"\g<1>\g<2>urą Gilotyną"),
        # Deformed adjective comparatives / superlatives (e.g. 'najdobrejsze' -> 'najlepsze')
        (r"(^|[^\w]|\\[Nnh])([Nn])ajdobrejsz(y|ego|emu|ym|a|ej|ą|e|ych|ymi)?\b", r"\g<1>\g<2>ajlepsz\g<3>"),
        (r"(^|[^\w]|\\[Nnh])dobrejsz(y|ego|emu|ym|a|ej|ą|e|ych|ymi)?\b", r"\g<1>lepsz\g<2>"),
        (r"(^|[^\w]|\\[Nnh])Dobrejsz(y|ego|emu|ym|a|ej|ą|e|ych|ymi)?\b", r"\g<1>Lepsz\g<2>"),
    ]
    res = text
    for pat, repl in TYPO_NORMALIZATIONS:
        res = re.sub(pat, repl, res)

    # Subject nominative repair: 'pan Eftala zniszczył' -> 'pan Eftal zniszczył' (consonant-ending male names following nominative 'pan')
    def _fix_nominative_title_subject(m):
        prefix = m.group(1)
        pan = m.group(2)
        sep = m.group(3)
        name_stem = m.group(4)
        verb = m.group(5)
        full_name = name_stem + "a"
        if full_name.lower() in {
            "akira", "shira", "soma", "gaara", "ashitaka", "kiba", "kenta",
            "ryoma", "hanza", "koba", "soya", "toma", "genga"
        }:
            return m.group(0)
        return f"{prefix}{pan}{sep}{name_stem} {verb}"

    res = re.sub(
        r"(^|[^\w]|\\[Nnh])([Pp]an)(\s+|\\[Nnh]+)([A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]*[bcdfghjklmnprstvwxz])a\s+([a-ząćęłńóśźż]+(?:ł|łby|ła|ło|li|ły))\b",
        _fix_nominative_title_subject,
        res
    )
    return res


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
            "declensions": {},        # { "Shira": {"M": "Shira", "D": "Shiry", "C": "Shirze", ...} }
            "plot_anchors": {},        # { "kamień jada": "rytualny artefakt wywołujący deszcz", "zbieg z Samarkandy": "Shira" }
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

    def _sanitize_character_entry(self, name: str, details: str) -> str:
        """
        Guards Series Bible against gender poisoning and ambiguous descriptions (Layer 5).
        - Filters out collective feminine nouns (e.g. 'służące w obozie', 'koleżanki')
          when applied to male or mixed characters.
        - Ensures explicit gender clarity for canonical oriental names on '-a'.
        """
        if not details:
            return ""

        CANONICAL_MALE_NAMES = {
            "shira", "akira", "gaara", "ashitaka", "kiba", "soma", "kenta",
            "ryoma", "hanza", "koba", "soya", "toma", "genga", "sinbad", "judar", "alibaba"
        }

        clean_desc = sanitize_lexical_text(details.strip())
        name_lower = name.lower()

        # Check if the relationship or character involves a confirmed male character
        involves_male = any(m in name_lower for m in CANONICAL_MALE_NAMES)
        if not involves_male and hasattr(self, "data") and "characters" in self.data:
            for k, v in self.data["characters"].items():
                if k.lower() in name_lower:
                    desc_v = str(v.get("description", "") if isinstance(v, dict) else v).lower()
                    if any(w in desc_v for w in ["male", "mężczyzna", "chłopak", "męsk"]):
                        involves_male = True
                        break

        # If a relationship or entry involves a male character, forbid collective feminine nouns
        if involves_male:
            # Replace ambiguous "służące" with "służba / podwładni"
            clean_desc = re.sub(r"\bsłużące\b", "służba", clean_desc, flags=re.IGNORECASE)
            clean_desc = re.sub(r"\bkoleżanki\b", "znajomi", clean_desc, flags=re.IGNORECASE)
            clean_desc = re.sub(r"\bprzyjaciółki\b", "przyjaciele", clean_desc, flags=re.IGNORECASE)

        # For standalone male names ending in '-a', enforce explicit gender and directive
        is_standalone_male_a = any(name_lower == m for m in CANONICAL_MALE_NAMES)
        if is_standalone_male_a:
            if "mężczyzna" not in clean_desc.lower() and "male" not in clean_desc.lower():
                clean_desc = f"MĘŻCZYZNA (postać) - {clean_desc}".strip()
            if "kategoryczny nakaz form męskich" not in clean_desc.lower() and "ostrzegał" not in clean_desc.lower():
                clean_desc = f"{clean_desc} [KATEGORYCZNY NAKAZ form męskich w czasie przeszłym: mówił / ostrzegał / pomógł]".strip()

        # Safeguard plural groups morphology in Series Bible (Filar CLXIII)
        is_female_group = any(w in name_lower or w in clean_desc.lower() for w in ["grupa kobiet", "grupa dziewcząt", "uczennice", "kapłanki", "dziewczęta", "wojowniczki"])
        if is_female_group and not involves_male:
            if "niemęskoosobow" not in clean_desc.lower() and "-łyście" not in clean_desc.lower():
                clean_desc = f"{clean_desc} [GRUPA KOBIET - Wymóg form niemęskoosobowych: -łyście / byłyście gotowe]".strip()

        is_male_group = any(w in name_lower or w in clean_desc.lower() for w in ["grupa mężczyzn", "grupa chłopaków", "żołnierze", "panowie", "wojownicy"])
        if is_male_group:
            if "męskoosobow" not in clean_desc.lower() and "-liście" not in clean_desc.lower():
                clean_desc = f"{clean_desc} [GRUPA MĘŻCZYZN - Wymóg rodzaju męskoosobowego: -liście / byliście gotowi]".strip()

        # Safeguard singular addressee morphology in Series Bible (Filar CLXIII)
        is_single_female = any(w in clean_desc.lower() for w in ["kobieta", "female", "dziewczyna", "nauczycielka", "uczennica", "kapłanka", "pani"]) and not is_female_group and not involves_male
        if is_single_female:
            if "2. os. lp." not in clean_desc.lower() and "-łaś" not in clean_desc.lower():
                clean_desc = f"{clean_desc} [KOBIETA (Adresat) - W 2. os. lp. 'ty' wymóg form żeńskich: byłaś / zrobiłaś / jesteś pewna]".strip()

        is_single_male = any(w in clean_desc.lower() for w in ["mężczyzna", "male", "chłopak", "żołnierz", "pan", "uczeń"]) and not is_male_group
        if is_single_male:
            if "2. os. lp." not in clean_desc.lower() and "-łeś" not in clean_desc.lower():
                clean_desc = f"{clean_desc} [MĘŻCZYZNA (Adresat) - W 2. os. lp. 'ty' wymóg form męskich: byłeś / zrobiłeś / jesteś pewien]".strip()

        # Safeguard hierarchical honorific relationships and anti-hybrid vocatives (Filar C & CLVII)
        is_subordinate_or_disciple = any(w in clean_desc.lower() for w in ["uczeń", "uczennica", "służąca", "niewolnica", "adept", "podwładn"])
        is_master_or_superior = any(w in clean_desc.lower() for w in ["mistrz", "arcymag", "pan ", "mentor", "zwierzchnik", "lord"])
        if is_subordinate_or_disciple or is_master_or_superior:
            if "t-v invariance" not in clean_desc.lower() and "panie" not in clean_desc.lower():
                clean_desc = f"{clean_desc} [RELACJA HIERARCHICZNA (T-V Invariance): stały zwrot formalny 'Pan / Panie [Imię]', zakaz hybryd 'Imię... ma pan' oraz odporność na opuszczanie -sama]".strip()

        return clean_desc

    def update_from_episode_profile(
        self,
        episode_name: str = "",
        characters: Optional[Dict[str, str]] = None,
        glossary: Optional[Dict[str, str]] = None,
        plot_anchors: Optional[Dict[str, str]] = None,
        relationships: Optional[Dict[str, str]] = None,
    ):
        """Updates glossary, character registry, relationships, and plot anchors based on Profiler output of a new episode."""
        if episode_name and episode_name not in self.data["episodes_translated"]:
            self.data["episodes_translated"].append(episode_name)

        if characters:
            for name, details in characters.items():
                if not name or not details:
                    continue
                clean_details = self._sanitize_character_entry(name, details)
                if name not in self.data["characters"]:
                    self.data["characters"][name] = {"description": clean_details}
                else:
                    existing_entry = self.data["characters"][name]
                    existing_desc = existing_entry.get("description", "") if isinstance(existing_entry, dict) else str(existing_entry)
                    existing_lower = existing_desc.lower()

                    # Protect confirmed gender against downgrading or overwriting (both male and female)
                    has_confirmed_male = any(w in existing_lower for w in ["mężczyzna", "męsk", "male", "kategoryczny nakaz form męskich"])
                    is_incoming_female = any(w in clean_details.lower() for w in ["kobieta", "żeńsk", "female", "służąca", "nauczycielka", "dziewczyna"])
                    if has_confirmed_male and is_incoming_female:
                        continue

                    has_confirmed_female = any(w in existing_lower for w in ["kobieta", "żeńsk", "female", "dziewczyna", "kategoryczny nakaz form żeńskich", "nauczycielka"])
                    is_incoming_male = any(w in clean_details.lower() for w in ["mężczyzna", "męsk", "male", "chłopak"])
                    if has_confirmed_female and is_incoming_male:
                        continue

                    # If existing entry has rich directives/seiyū, do not overwrite with bare string
                    has_rich_directives = any(w in existing_lower for w in ["kategoryczny", "nakaz", "seiyū", "bezwzględnie formy"])
                    if has_rich_directives and not any(w in clean_details.lower() for w in ["kategoryczny", "nakaz"]):
                        continue

                    self.data["characters"][name] = {"description": clean_details}

                # Generate and store 7-case Polish declension matrix
                FEMALE_KEYWORDS = [
                    "kobieta", "żeńsk", "female", "dziewczyn", "nauczycielk", "czarodziejk",
                    "szpieżk", "wojowniczk", "kapłank", "służąc", "pani", "bohaterk",
                    "arystokratk", "władczyn", "królow", "księżniczk", "matk", "córk", "siostr"
                ]
                c_gender = "MALE" if (any(w in clean_details.lower() for w in ["mężczyzna", "męsk", "male", "chłopak"]) and not any(w in clean_details.lower() for w in FEMALE_KEYWORDS)) else ("FEMALE" if any(w in clean_details.lower() for w in FEMALE_KEYWORDS) else "UNKNOWN")
                if "declensions" not in self.data:
                    self.data["declensions"] = {}

                names_to_decline = [name]
                if "->" in name:
                    names_to_decline.extend([p.strip() for p in name.split("->")])
                elif "/" in name:
                    names_to_decline.extend([p.strip() for p in name.split("/")])

                for single_n in names_to_decline:
                    if single_n and len(single_n) >= 3 and not any(ch in single_n for ch in "->/"):
                        self.data["declensions"][single_n] = generate_polish_name_declension(single_n, c_gender)

        if glossary:
            import re
            for k, v in glossary.items():
                # Store non-trivial terms only and sanitize parenthetical descriptions
                if k and v and len(k) > 1 and len(v) > 1:
                    clean_k = str(k).strip()
                    clean_v = sanitize_lexical_text(re.sub(r"\s*[\(\[].*?[\)\]]", "", v).strip())
                    if clean_k and clean_v:
                        # Case-insensitive update to prevent duplicate collisions
                        norm_k = clean_k.lower()
                        for old_k in list(self.data["glossary"].keys()):
                            if old_k.lower() == norm_k and old_k != clean_k:
                                del self.data["glossary"][old_k]
                        self.data["glossary"][clean_k] = clean_v

        if plot_anchors:
            if "plot_anchors" not in self.data:
                self.data["plot_anchors"] = {}
            for k, v in plot_anchors.items():
                if k and v:
                    clean_k = str(k).strip()
                    clean_v = sanitize_lexical_text(str(v).strip())
                    if clean_k and clean_v:
                        self.data["plot_anchors"][clean_k] = clean_v

        if relationships:
            if "relationships" not in self.data:
                self.data["relationships"] = {}
            for rel_k, rel_v in relationships.items():
                if rel_k and rel_v:
                    self.data["relationships"][rel_k] = sanitize_lexical_text(str(rel_v).strip())
                    # Also extract names from relationships to decline them
                    import re
                    for part in re.split(r"->|/|,", rel_k):
                        part_clean = part.strip()
                        if len(part_clean) >= 3 and not any(ch in part_clean for ch in "{}[]():;"):
                            if part_clean not in self.data["declensions"]:
                                self.data["declensions"][part_clean] = generate_polish_name_declension(part_clean, "UNKNOWN")

        self.save()

    def format_for_prompt(self) -> str:
        """Formats Series Bible into a compact section for LLM prompt injection."""
        lines = []
        has_content = False

        if self.data["characters"] or self.data["glossary"] or self.data.get("plot_anchors") or self.data.get("declensions"):
            lines.append("--- BIBLIA SERIALU (PAMIĘĆ MIĘDZYODCINKOWA SEZONU) ---")
            lines.append(f"Seria: '{self.anime_title}' (Przetłumaczono odcinków: {len(self.data['episodes_translated'])})")
            
            if self.data["characters"]:
                lines.append("• Kluczowe postacie z poprzednich odcinków:")
                for name, info in list(self.data["characters"].items())[:8]:
                    desc = info.get("description", "") if isinstance(info, dict) else str(info)
                    lines.append(f"  - {name}: {desc}")
                has_content = True

            if self.data.get("declensions"):
                decl_items = []
                for c_name, c_decl in list(self.data["declensions"].items())[:6]:
                    if c_decl.get("M") != c_decl.get("D"):
                        decl_items.append(f"    * {c_name}: D. {c_decl.get('D')}, C/Ms. {c_decl.get('C')}, B/N. {c_decl.get('B')}/z {c_decl.get('N')}, W. {c_decl.get('W')}!")
                if decl_items:
                    lines.append("• Wzorzec odmiany imion (Matryca 7 Przypadków - KATEGORYCZNY NAKAZ FLEKSJI):")
                    lines.extend(decl_items)
                    has_content = True

            if self.data["glossary"]:
                lines.append("• Ustalone nazwy i terminologia z poprzednich odcinków (ZACHOWAJ SPÓJNOŚĆ!):")
                for src, trg in list(self.data["glossary"].items())[:12]:
                    lines.append(f"  - '{src}' -> '{trg}'")
                has_content = True

            if self.data.get("plot_anchors"):
                lines.append("• Kluczowe rekwizyty i kotwice fabularne (PLOT ANCHORS - ZACHOWAJ CIĄGŁOŚĆ!):")
                for item_key, directive in list(self.data["plot_anchors"].items())[:8]:
                    lines.append(f"  - [{item_key}]: {directive}")
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

        anchor_rows = ""
        for p_item, p_dir in self.data.get("plot_anchors", {}).items():
            anchor_rows += f"<tr><td><strong>{p_item}</strong></td><td>{p_dir}</td></tr>"

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
    <p>🛡️ <strong>Liczba wpisów w pamięci ciągłości:</strong> {len(self.data.get('characters', {}))} postaci | {len(self.data.get('glossary', {}))} terminów | {len(self.data.get('plot_anchors', {}))} kotwic fabularnych</p>
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

  <h2>⚓ Rekwizyty i Kotwice Fabularne (Plot Anchors)</h2>
  <table>
    <thead><tr><th>Rekwizyt / Zdarzenie</th><th>Wymóg Ciągłości i Kontekst</th></tr></thead>
    <tbody>{anchor_rows or '<tr><td colspan="2">Brak zarejestrowanych kotwic fabularnych</td></tr>'}</tbody>
  </table>
</div>
</body>
</html>"""
        return html
        return html
