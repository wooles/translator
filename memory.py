"""
Moduł Pamięci Tłumaczeniowej (Translation Memory - TM) oraz analizy korpusu napisów anime.
Automatycznie paruje angielskie i polskie wersje odcinków, indeksuje tysiące autentycznych
linii dialogowych przetłumaczonych przez ludzi i podpowiada idealne zwroty w czasie rzeczywistym.
"""

import os
import re
import json
import sqlite3
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import pysubs2

MEMORY_DB_PATH = Path(__file__).parent / "translation_memory.db"
MEMORY_JSON_PATH = Path(__file__).parent / "translation_memory.json"

def clean_text_for_memory(text: str) -> str:
    """
    Czyści tekst ze znaczników formatowania ASS, rysunków wektorowych i normalizuje białe znaki.
    """
    if not text or text.startswith("m ") or "{\\p1}" in text:
        return ""
    # Usuwanie tagów {...}
    cleaned = re.sub(r"\{[^}]*\}?", "", text)
    cleaned = re.sub(r"\\(?:[a-zA-Z0-9&]+|\([^)]*\)?)?", "", cleaned)
    cleaned = cleaned.replace("\\N", " ").replace("\\n", " ")
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    if cleaned.startswith("m ") or len(cleaned) < 2:
        return ""
    return cleaned

def tokenize(text: str) -> List[str]:
    """
    Dzieli tekst na znormalizowane tokeny słowne do szybkiego wyszukiwania.
    """
    return [w.lower() for w in re.findall(r"\b\w{3,}\b", text.lower())]

class TranslationMemory:
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = str(db_path or MEMORY_DB_PATH)
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS translation_pairs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    en_text TEXT NOT NULL,
                    pl_text TEXT NOT NULL,
                    en_clean TEXT NOT NULL,
                    anime_title TEXT,
                    word_count INTEGER
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_en_clean ON translation_pairs(en_clean)")

    def index_database_directory(self, base_dir: Path) -> int:
        """
        Skanuje podany katalog (np. 'baza napisów'), paruje pliki .en.ass/.en.srt z .ass/.srt
        z wykorzystaniem szybkiego wyszukiwania binarnego (O(N log M)) i zapisuje pary dialogowe do bazy danych.
        """
        import bisect
        from tqdm import tqdm

        if not base_dir.exists():
            return 0

        # Wyszukiwanie angielskich plików
        en_files = sorted(
            list(base_dir.glob("*.en.ass")) +
            list(base_dir.glob("*.en.srt")) +
            list(base_dir.glob("*.ang.ass")) +
            list(base_dir.glob("*.ang.srt")) +
            list(base_dir.glob("*.ang"))
        )

        pairs_to_insert = []
        seen_pairs = set()

        print(f"[Pamięć Tłumaczeniowa] Błyskawiczne indeksowanie bazy: {len(en_files)} plików...")

        for en_path in tqdm(en_files, desc="Indeksowanie par dialogowych", unit="plik"):
            # Ustalenie nazwy pliku polskiego
            pl_name = en_path.name
            for suffix in [".en.ass", ".ang.ass", ".en.srt", ".ang.srt", ".ang"]:
                if pl_name.endswith(suffix):
                    pl_name = pl_name[:-len(suffix)] + (".ass" if "ass" in suffix or suffix == ".ang" else ".srt")
                    break

            pl_path = en_path.parent / pl_name
            if not pl_path.exists():
                # Próba znalezienia pliku z samym .ass / .srt
                base_stem = en_path.stem.split(".")[0]
                pl_path_ass = en_path.parent / f"{base_stem}.ass"
                pl_path_srt = en_path.parent / f"{base_stem}.srt"
                pl_path = pl_path_ass if pl_path_ass.exists() else pl_path_srt

            if not pl_path.exists():
                continue

            try:
                subs_en = pysubs2.load(str(en_path), encoding="utf-8")
            except Exception:
                try:
                    subs_en = pysubs2.load(str(en_path), encoding="latin2")
                except Exception:
                    continue

            try:
                subs_pl = pysubs2.load(str(pl_path), encoding="utf-8")
            except Exception:
                try:
                    subs_pl = pysubs2.load(str(pl_path), encoding="latin2")
                except Exception:
                    continue

            # Przygotowanie posortowanej listy zdarzeń polskich do wyszukiwania binarnego
            pl_events = []
            for ev in subs_pl.events:
                if ev.is_comment:
                    continue
                c_pl = clean_text_for_memory(ev.text)
                if c_pl:
                    pl_events.append((ev.start, c_pl))
            pl_events.sort(key=lambda x: x[0])
            pl_starts = [x[0] for x in pl_events]

            if not pl_events:
                continue

            anime_name = en_path.stem.split(" - ")[0].replace("[ASW]", "").replace("[Erai-raws]", "").strip()

            for ev_en in subs_en.events:
                if ev_en.is_comment:
                    continue
                clean_en = clean_text_for_memory(ev_en.text)
                if not clean_en or len(clean_en) < 3 or len(clean_en) > 250:
                    continue

                # Wyszukiwanie binarne w oknie czasowym [-300ms, +300ms]
                left = bisect.bisect_left(pl_starts, ev_en.start - 300)
                right = bisect.bisect_right(pl_starts, ev_en.start + 300)

                for k in range(left, right):
                    clean_pl = pl_events[k][1]
                    if len(clean_pl) > 2 and clean_pl.lower() != clean_en.lower():
                        pair_key = (clean_en.lower(), clean_pl.lower())
                        if pair_key not in seen_pairs:
                            seen_pairs.add(pair_key)
                            pairs_to_insert.append((
                                clean_en,
                                clean_pl,
                                clean_en.lower(),
                                anime_name,
                                len(clean_en.split())
                            ))
                        break

        # Zapis do bazy SQLite
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM translation_pairs")
            conn.executemany(
                "INSERT INTO translation_pairs (en_text, pl_text, en_clean, anime_title, word_count) VALUES (?, ?, ?, ?, ?)",
                pairs_to_insert
            )

        print(f"[Pamięć Tłumaczeniowa] Zaindeksowano pomyślnie {len(pairs_to_insert)} autentycznych par dialogowych!")
        return len(pairs_to_insert)

    def find_relevant_examples(self, query_texts: List[str], max_examples: int = 5) -> List[Dict[str, str]]:
        """
        Wyszukuje w bazie najbardziej trafne, ludzkie przykłady tłumaczeń dla podanych kwestii dialogowych.
        """
        if not os.path.exists(self.db_path):
            return []

        candidates: Dict[str, Dict[str, Any]] = {}

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            for q in query_texts:
                clean_q = clean_text_for_memory(q).lower()
                if len(clean_q) < 3:
                    continue

                # 1. Dokładne dopasowanie całej frazy (Exact Match)
                cursor.execute(
                    "SELECT en_text, pl_text, anime_title FROM translation_pairs WHERE en_clean = ? LIMIT 2",
                    (clean_q,)
                )
                for row in cursor.fetchall():
                    key = row[0]
                    if key not in candidates:
                        candidates[key] = {"en": row[0], "pl": row[1], "anime": row[2], "score": 100}

                # 2. Dopasowanie fragmentu frazowego (Sub-phrase match) dla idiomów i zwrotów
                words = tokenize(clean_q)
                if len(words) >= 2:
                    # Szukamy par zawierających kluczowe zwroty
                    bigram_query = f"%{words[0]} {words[1]}%"
                    cursor.execute(
                        "SELECT en_text, pl_text, anime_title FROM translation_pairs WHERE en_clean LIKE ? AND word_count <= 14 LIMIT 2",
                        (bigram_query,)
                    )
                    for row in cursor.fetchall():
                        key = row[0]
                        if key not in candidates:
                            candidates[key] = {"en": row[0], "pl": row[1], "anime": row[2], "score": 60}

        # Sortowanie po trafności
        sorted_results = sorted(candidates.values(), key=lambda x: x["score"], reverse=True)
        return sorted_results[:max_examples]

def format_translation_memory_for_prompt(examples: List[Dict[str, str]]) -> str:
    """
    Formatuje wyciągnięte przykłady w czytelny blok do wstrzyknięcia do promptu LLM.
    """
    if not examples:
        return ""

    lines = []
    lines.append("--- SPRAWDZONE PRZYKŁADY Z BAZY ANIME (PAMIĘĆ TŁUMACZENIOWA) ---")
    lines.append("Wzoruj się na poniższych autentycznych, naturalnych tłumaczeniach ludzkich:")
    for ex in examples:
        anime_tag = f"[{ex['anime']}] " if ex.get("anime") else ""
        lines.append(f" • {anime_tag}EN: \"{ex['en']}\" -> PL: \"{ex['pl']}\"")
    lines.append("-----------------------------------------------------------------\n")
    return "\n".join(lines)
