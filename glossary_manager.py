# -*- coding: utf-8 -*-
"""
Moduł Słownika Deterministycznego i Nadpisywania Terminologii (Deterministic Glossary Manager).
Pozwala użytkownikowi na definiowanie żelaznych tłumaczeń pojęć, imion, ataków i tytułów,
które są wstrzykiwane do promptu oraz bezwzględnie wymuszane w post-processingu (100% determinizmu).
"""

import os
import re
import json
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional

GLOBAL_GLOSSARY_PATH = Path(__file__).parent / "global_glossary.json"

class GlossaryManager:
    """
    Zarządza globalnym oraz lokalnym słownikiem terminów z deterministycznym nadpisywaniem.
    """
    def __init__(self, global_path: Optional[Path] = None):
        self.global_path = global_path or GLOBAL_GLOSSARY_PATH
        self.global_terms: Dict[str, Dict[str, str]] = {}
        self.load()

    def load(self):
        """Wczytuje globalny słownik z pliku JSON."""
        if self.global_path.exists():
            try:
                with open(self.global_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        self.global_terms = data
            except Exception:
                self.global_terms = {}
        else:
            # Domyślne żelazne terminy globalne
            self.global_terms = {
                "Sensei": {"pl": "Sensei", "desc": "Tytuł mistrza/nauczyciela (bez 'Pani/Pan')"},
                "Senpai": {"pl": "Senpai", "desc": "Starszy kolega/koleżanka"},
                "Your Honor": {"pl": "Wysoki Sądzie", "desc": "Zwrot do sędziego w sądzie"},
                "Four Emperors": {"pl": "Czterej Cesarze", "desc": "Liczebnik męskoosobowy (nie: Czworo)"},
                "Three Musketeers": {"pl": "Trzej Muszkieterowie", "desc": "Liczebnik męskoosobowy"}
            }
            self.save()

    def save(self):
        """Zapisuje globalny słownik na dysku."""
        try:
            with open(self.global_path, "w", encoding="utf-8") as f:
                json.dump(self.global_terms, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def add_term(self, src: str, pl: str, desc: str = "") -> None:
        """Dodaje lub aktualizuje termin w słowniku globalnym."""
        if src.strip() and pl.strip():
            self.global_terms[src.strip()] = {
                "pl": pl.strip(),
                "desc": desc.strip()
            }
            self.save()

    def remove_term(self, src: str) -> bool:
        """Usuwa termin ze słownika globalnego."""
        if src.strip() in self.global_terms:
            del self.global_terms[src.strip()]
            self.save()
            return True
        return False

    def get_combined_glossary(self, series_glossary: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """
        Łączy słownik globalny ze słownikiem z Biblii Serialu (gdzie seria ma pierwszeństwo).
        Zwraca prostą mapę {angielski/japoński_termin: polskie_tłumaczenie}.
        """
        combined: Dict[str, str] = {}
        # 1. Globalne
        for k, v in self.global_terms.items():
            combined[k] = v.get("pl", "") if isinstance(v, dict) else str(v)
        # 2. Specyficzne dla serii (nadpisują globalne)
        if series_glossary:
            for k, v in series_glossary.items():
                if k and v:
                    combined[k] = v
        return combined

    def format_for_prompt(self, glossary_dict: Dict[str, str]) -> str:
        """
        Formatuje słownik do wstrzyknięcia do promptu LLM z najwyższym priorytetem.
        """
        if not glossary_dict:
            return ""

        lines = [
            "--- BEZWZGLĘDNY SŁOWNICZEK POJĘĆ I TERMINOLOGII (WYMÓG DETERMINISTYCZNY) ---",
            "Poniższe pojęcia MUSZĄ być przetłumaczone DOKŁADNIE tak, jak podano poniżej:"
        ]
        for src, trg in glossary_dict.items():
            lines.append(f" • '{src}' => '{trg}'")
        lines.append("----------------------------------------------------------------------------\n")
        return "\n".join(lines)

    @classmethod
    def clean_target_term(cls, trg: str) -> str:
        """Usuwa zbędne objaśnienia w nawiasach (np. 'Płomień Adolli (Adolla Burst)' -> 'Płomień Adolli')."""
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
        Bezwzględny filtr deterministyczny uruchamiany po tłumaczeniu.
        Jeśli w tekście pojawi się błędna/przestarzała wersja lub pominięty termin,
        filtr podmienia go na ustaloną polską formę BEZ dublowania i bez wstawek w nawiasach.
        """
        if not text or not glossary_dict:
            return text, []

        modified = text
        applied_fixes = []

        # Sortujemy słownik od najdłuższych fraz do najkrótszych (aby "Shinra Bansho Man" miał pierwszeństwo przed "Shinra Bansho")
        sorted_glossary = sorted(glossary_dict.items(), key=lambda kv: len(kv[0]), reverse=True)

        for src, raw_trg in sorted_glossary:
            if not src or not raw_trg:
                continue

            trg = cls.clean_target_term(raw_trg)
            if not trg or src.lower() == trg.lower():
                continue

            # Zabezpieczenie: jeśli termin docelowy już znajduje się w tekście w tej samej frazie, nie dublujemy
            if trg.lower() in modified.lower() and src.lower() in trg.lower():
                continue

            # Jeśli w przetłumaczonym tekście ostał się angielski termin (nieprzetłumaczony)
            pattern_src = re.compile(rf"\b{re.escape(src)}\b", re.IGNORECASE)
            if pattern_src.search(modified):
                modified = pattern_src.sub(trg, modified)
                applied_fixes.append(f"Wymuszenie słownika: '{src}' -> '{trg}'")

        # Czyszczenie ewentualnych zduplikowanych nawiasów (np. "(XYZ) (XYZ)" -> "")
        modified = re.sub(r"\(([^)]+)\)\s*\(\1\)", r"(\1)", modified)
        modified = re.sub(r"\s+", " ", modified).strip()

        return modified, applied_fixes
