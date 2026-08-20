"""
Moduł automatycznego pobierania metadanych anime (fabuła, gatunki, postacie i ich płeć)
z serwisów AniList i MyAnimeList na podstawie nazwy pliku.
"""

import re
import json
import urllib.request
import urllib.parse
from pathlib import Path
from typing import Optional, Dict, Any, List

def clean_anime_filename(filename_or_path: str) -> str:
    """
    Oczyszcza nazwę pliku z tagów grup fansuberskich, jakości, hashy i numeru odcinka,
    aby uzyskać czysty tytuł serii (np. 'Otome Kaijuu Carameliser').
    """
    name = Path(filename_or_path).stem

    # 1. Usuwanie tagów w nawiasach kwadratowych na początku (np. [ASW], [SubsPlease], [Erai-raws])
    name = re.sub(r"^\[[^\]]+\]\s*", "", name)

    # 2. Usuwanie hashy CRC32 i jakości na końcu (np. [1080p HEVC][AE584971], (1080p))
    name = re.sub(r"\s*\[[^\]]+\]$", "", name)
    name = re.sub(r"\s*\([^\)]+\)$", "", name)
    name = re.sub(r"\[[0-9a-fA-F]{8}\]", "", name)
    name = re.sub(r"\[(?:1080p|720p|480p|2160p|4K|HEVC|x264|x265|AAC|FLAC)[^\]]*\]", "", name, flags=re.IGNORECASE)

    # 3. Usuwanie numeru odcinka (np. - 07, _07, EP07, S01E07, Episode 7)
    name = re.sub(r"\s*-\s*(?:Episode\s*)?(?:S\d+)?(?:E|EP)?\d+(?:v\d+)?.*$", "", name, flags=re.IGNORECASE)
    name = re.sub(r"\s+(?:S\d+)?(?:E|EP)\d+.*$", "", name, flags=re.IGNORECASE)
    name = re.sub(r"\s*-\s*\d+.*$", "", name)

    # 4. Zamiana podkreśleń i kropek na spacje
    name = name.replace("_", " ").replace(".", " ")

    # 5. Usunięcie podwójnych spacji
    name = re.sub(r"\s+", " ", name).strip()
    return name

def fetch_anilist_metadata(title: str) -> Optional[Dict[str, Any]]:
    """
    Wysyła zapytanie do AniList GraphQL API w celu pobrania opisu fabuły i obsady postaci.
    """
    query = """
    query ($search: String) {
      Media (search: $search, type: ANIME) {
        id
        title {
          romaji
          english
          native
        }
        description(asHtml: false)
        genres
        characters(sort: [ROLE, RELEVANCE], perPage: 16) {
          edges {
            role
            node {
              name {
                full
                native
              }
              gender
              description
            }
          }
        }
      }
    }
    """
    url = "https://graphql.anilist.co"
    payload = json.dumps({"query": query, "variables": {"search": title}}).encode("utf-8")
    
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "MultimodalAnimeTranslator/1.0"
    }

    req = urllib.request.Request(url, data=payload, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=6) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            media = data.get("data", {}).get("Media")
            if not media:
                return None

            # Czyścimy opis z ewentualnych znaczników HTML (np. <br>, <i>)
            desc_raw = media.get("description") or ""
            desc_clean = re.sub(r"<[^>]+>", "", desc_raw).strip()

            characters = []
            for edge in media.get("characters", {}).get("edges", []):
                node = edge.get("node", {})
                role = edge.get("role", "SUPPORTING")
                c_name = node.get("name", {}).get("full")
                c_native = node.get("name", {}).get("native")
                c_gender = node.get("gender") or "nieznana"
                
                # Ustalenie polskiego określenia płci
                gender_pl = "postać"
                if c_gender.lower() in ("female", "woman", "girl"):
                    gender_pl = "kobieta / dziewczyna"
                elif c_gender.lower() in ("male", "man", "boy"):
                    gender_pl = "mężczyzna / chłopak"

                characters.append({
                    "name": c_name,
                    "native_name": c_native,
                    "gender": gender_pl,
                    "gender_raw": c_gender,
                    "role": "Główny bohater" if role == "MAIN" else "Postać drugoplanowa"
                })

            return {
                "title_romaji": media.get("title", {}).get("romaji"),
                "title_english": media.get("title", {}).get("english"),
                "title_native": media.get("title", {}).get("native"),
                "genres": media.get("genres", []),
                "description": desc_clean,
                "characters": characters
            }
    except Exception as e:
        return None

def get_anime_context(filename_or_path: str) -> Optional[Dict[str, Any]]:
    """
    Pobiera i formatuje pełne metadane anime na podstawie ścieżki lub nazwy pliku.
    """
    clean_title = clean_anime_filename(filename_or_path)
    if not clean_title or len(clean_title) < 2:
        return None

    meta = fetch_anilist_metadata(clean_title)
    return meta

def format_anime_context_for_prompt(meta: Dict[str, Any]) -> str:
    """
    Formatuje pobrane metadane w czytelny blok tekstu do wstrzyknięcia do promptu LLM.
    """
    if not meta:
        return ""

    lines = []
    lines.append("=== KONTEKST SERII ANIME (Baza Wiedzy AniList) ===")
    title_display = meta.get("title_romaji") or meta.get("title_english") or "Anime"
    if meta.get("title_english") and meta.get("title_english") != title_display:
        title_display += f" ({meta.get('title_english')})"
    lines.append(f"Tytuł: {title_display}")
    
    if meta.get("genres"):
        lines.append(f"Gatunki: {', '.join(meta['genres'])}")

    if meta.get("description"):
        # Skracamy opis do 2-3 zdań dla oszczędności tokenów
        desc = meta["description"]
        if len(desc) > 350:
            desc = desc[:350].rsplit(".", 1)[0] + "."
        lines.append(f"Opis fabuły: {desc}")

    if meta.get("characters"):
        lines.append("\nObsada i płeć bohaterów:")
        for c in meta["characters"][:12]:
            lines.append(f" • {c['name']} [{c.get('native_name') or ''}]: {c['gender']} ({c['role']})")

    lines.append("==================================================\n")
    return "\n".join(lines)
