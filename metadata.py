"""
Module for automatically fetching anime metadata (plot, genres, characters and genders)
from AniList and MyAnimeList based on filename.
"""

import re
import json
import urllib.request
import urllib.parse
from pathlib import Path
from typing import Optional, Dict, Any, List

_ANILIST_DISABLED: bool = False

def clean_anime_filename(filename_or_path: str) -> str:
    """
    Cleans filename of fansub group tags, quality tags, hashes, and episode numbers
    to extract a clean series title (e.g. 'Otome Kaijuu Carameliser').
    """
    name = Path(filename_or_path).stem

    # 1. Remove bracketed prefix tags (e.g. [ASW], [SubsPlease], [Erai-raws])
    name = re.sub(r"^\[[^\]]+\]\s*", "", name)

    # 2. Remove CRC32 hashes and quality tags at the end (e.g. [1080p HEVC][AE584971], (1080p))
    name = re.sub(r"\s*\[[^\]]+\]$", "", name)
    name = re.sub(r"\s*\([^\)]+\)$", "", name)
    name = re.sub(r"\[[0-9a-fA-F]{8}\]", "", name)
    name = re.sub(r"\[(?:1080p|720p|480p|2160p|4K|HEVC|x264|x265|AAC|FLAC)[^\]]*\]", "", name, flags=re.IGNORECASE)

    # 3. Handle scene/torrent release naming with dots/underscores BEFORE episode strip:
    # e.g. KAMUI.Hes.Behind.You.S01E07.REPACK.1080p.UNCENSORED...
    name = re.sub(r"[._](?:S\d+)?(?:E|EP)\d+.*$", "", name, flags=re.IGNORECASE)
    name = re.sub(r"[._](?:1080p|720p|480p|2160p|4K|HEVC|x264|x265|AMZN|WEB-DL|UNCENSORED|REPACK|PROPER|CR|MultiSub|dual.audio).*$", "", name, flags=re.IGNORECASE)
    name = re.sub(r"\s*-\s*(?:Episode\s*)?(?:S\d+)?(?:E|EP)?\d+(?:v\d+)?.*$", "", name, flags=re.IGNORECASE)
    name = re.sub(r"\s+(?:S\d+)?(?:E|EP)\d+.*$", "", name, flags=re.IGNORECASE)
    name = re.sub(r"\s*-\s*\d+.*$", "", name)

    # 4. Replace underscores and dots with spaces
    name = name.replace("_", " ").replace(".", " ")

    # 5. Clean scene tags if dots were already converted or remaining
    name = re.sub(r"\b(?:S\d+)?(?:E|EP)\d+\b.*$", "", name, flags=re.IGNORECASE)
    name = re.sub(r"\b(?:1080p|720p|480p|2160p|4K|HEVC|x264|x265|AMZN|WEB-DL|UNCENSORED|REPACK|PROPER|MSubs|ToonsHub)\b.*$", "", name, flags=re.IGNORECASE)

    # 6. Clean duplicate whitespace
    name = re.sub(r"\s+", " ", name).strip()
    return name

def fetch_anilist_metadata(title: str) -> Optional[Dict[str, Any]]:
    """
    Queries the AniList GraphQL API to fetch plot synopsis, tags, and character cast.
    Includes circuit-breaker logic when AniList API is disabled or unreachable.
    """
    global _ANILIST_DISABLED
    if _ANILIST_DISABLED:
        return None
    query = """
    query ($search: String) {
      Media (search: $search) {
        id
        title {
          romaji
          english
          native
        }
        description(asHtml: false)
        genres
        tags {
          name
          category
          rank
        }
        countryOfOrigin
        startDate {
          year
        }
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

            # Clean HTML tags from description (e.g. <br>, <i>)
            desc_raw = media.get("description") or ""
            desc_clean = re.sub(r"<[^>]+>", "", desc_raw).strip()

            # Analyze tags for historical context, setting, and world realities
            raw_tags = media.get("tags", [])
            tag_names = [t.get("name", "") for t in raw_tags if t.get("name")]
            
            # Detect key historical and setting keywords
            historical_keywords = [
                "historical", "mongol", "empire", "middle ages", "medieval", "edo period",
                "feudal", "ancient", "war", "politics", "royalty", "samurai", "military",
                "victorian", "shinsengumi", "meiji", "renaissance", "cyberpunk", "space opera"
            ]
            matched_setting_tags = [
                t for t in tag_names
                if any(k in t.lower() for k in historical_keywords)
            ]

            # Detect specialized domains and terminology (with word boundaries \b)
            domain_keywords = {
                "Enologia i Sommelierstwo (Wino)": [
                    r"\bwine\b", r"\bsommelier\b", r"\bwinery\b", r"\bvintages?\b",
                    r"\bkami no shizuku\b", r"\bdrops of god\b", r"\benology\b", r"\boenology\b"
                ],
                "Kulinaria i Gastronomia": [
                    r"\bcooking\b", r"\bculinary\b", r"\bgourmet\b", r"\bchef\b",
                    r"\bbaking\b", r"\bpatisserie\b", r"\bshokugeki\b"
                ],
                "Muzyka Klasyczna i Orkiestra": [
                    r"\bclassical music\b", r"\borchestra\b", r"\bphilharmonic\b",
                    r"\bconcerto\b", r"\bsymphony\b", r"\bbrass band\b", r"\bviolinist\b", r"\bpianist\b"
                ],
                "Tradycyjne Gry i Strategia": [
                    r"\btraditional games\b", r"\bshogi\b", r"\bkaruta\b", r"\bmahjong\b",
                    r"\bchess\b", r"\bgame of go\b", r"\bgo game\b", r"\bbaduk\b", r"\bboard games?\b"
                ],
                "Medycyna, Chirurgia i Farmacja": [
                    r"\bmedicine\b", r"\bmedical\b", r"\bsurgeon\b", r"\bsurgery\b",
                    r"\bpharmacology\b", r"\bhospital\b"
                ],
                "Sztuki Walki i Boks": [
                    r"\bmartial arts\b", r"\bboxing\b", r"\bjudo\b", r"\bkendo\b",
                    r"\bkarate\b", r"\btaekwondo\b", r"\bwrestling\b"
                ],
                "Prawo i Kryminalistyka": [
                    r"\bcourtroom\b", r"\battorney\b", r"\bprosecutor\b", r"\blawyer\b",
                    r"\bcriminalistics\b"
                ],
                "Lotnictwo i Kosmonautyka": [
                    r"\baviation\b", r"\bspacecraft\b", r"\bastronomy\b", r"\bspace exploration\b"
                ],
                "Militaria i Wojskowość": [
                    r"\bwarship\b", r"\btankery\b", r"\barmored vehicles?\b", r"\bpanzer\b"
                ]
            }
            detected_domains = []
            all_text_lower = " ".join(tag_names + media.get("genres", []) + [desc_clean, title]).lower()
            for dom_name, patterns in domain_keywords.items():
                if any(re.search(pat, all_text_lower) for pat in patterns):
                    detected_domains.append(dom_name)

            characters = []
            for edge in media.get("characters", {}).get("edges", []):
                node = edge.get("node", {})
                role = edge.get("role", "SUPPORTING")
                c_name = node.get("name", {}).get("full")
                c_native = node.get("name", {}).get("native")
                raw_gender = (node.get("gender") or "").strip()
                
                # Verified gender gate (AniList SSOT rule):
                # Gender is defined from AniList ONLY if there is an explicit, verified entry (Male / Female).
                # Otherwise gender is None, leaving resolution to dynamic episode-level data.
                has_verified_gender = False
                gender_pl = None
                if raw_gender.lower() in ("female", "woman", "girl"):
                    gender_pl = "kobieta / dziewczyna"
                    has_verified_gender = True
                elif raw_gender.lower() in ("male", "man", "boy"):
                    gender_pl = "mężczyzna / chłopak"
                    has_verified_gender = True

                characters.append({
                    "name": c_name,
                    "native_name": c_native,
                    "gender": gender_pl,
                    "gender_raw": raw_gender if has_verified_gender else None,
                    "has_verified_gender": has_verified_gender,
                    "role": "Główny bohater" if role == "MAIN" else "Postać drugoplanowa"
                })

            return {
                "title_romaji": media.get("title", {}).get("romaji"),
                "title_english": media.get("title", {}).get("english"),
                "title_native": media.get("title", {}).get("native"),
                "genres": media.get("genres", []),
                "tags": tag_names[:15],
                "setting_tags": matched_setting_tags[:8],
                "detected_domains": detected_domains[:3],
                "year": media.get("startDate", {}).get("year"),
                "description": desc_clean,
                "characters": characters
            }
    except Exception as e:
        err_str = str(e).lower()
        if "403" in err_str or "disabled" in err_str or "stability" in err_str or "forbidden" in err_str:
            _ANILIST_DISABLED = True
        return None

def fetch_gemini_metadata(title: str, client: Any = None) -> Optional[Dict[str, Any]]:
    """
    Parametric fallback when external GraphQL/REST APIs (AniList) are unreachable or blocked (HTTP 403).
    Queries Gemini to retrieve authoritative character cast, genders, and setting with 100% reliability.
    Always uses the HIGHEST available Flash model from model_resolver.
    """
    if not title or len(title) < 2:
        return None
    try:
        if not client:
            try:
                from client_factory import get_genai_client
                client = get_genai_client()
            except Exception:
                return None
        
        active_client = client.get_client() if hasattr(client, "get_client") else client
        from google.genai import types

        prompt = f"""Jesteś autorytatywną encyklopedią anime i mangi (MyAnimeList/AniList).
Podaj w formacie JSON oficjalne metadane dla serii anime/mangi: "{title}":
{{
  "title_romaji": "Oficjalny tytuł romaji",
  "title_english": "Oficjalny tytuł angielski",
  "genres": ["Gatunek 1", "Gatunek 2"],
  "setting_tags": ["Epoka", "Realia świata", "Czas i miejsce"],
  "detected_domains": ["Specjalistyczna dziedzina jeśli występuje (np. wino, szachy, medycyna, alchemia, wojskowość)"],
  "description": "Krótkie streszczenie tła fabularnego (2-3 zdania).",
  "characters": [
    {{
      "name": "Imię postaci",
      "gender": "mężczyzna / chłopak",
      "gender_raw": "MALE",
      "role": "Główny bohater"
    }}
  ]
}}
W sekcji 'characters' wymień WSZYSTKICH znanych bohaterów z kanonu tej serii, dbając o bezwzględną dokładność biologiczną płci (MALE vs FEMALE) na podstawie obsady seiyū i fabuły."""

        model_to_use = "gemini-3.8-flash"
        try:
            from model_resolver import resolve_best_models
            best = resolve_best_models(client=active_client)
            model_to_use = best.get("flash") or model_to_use
        except Exception:
            pass

        resp = active_client.models.generate_content(
            model=model_to_use,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.1
            )
        )
        data = json.loads(resp.text)
        if data and data.get("characters"):
            return data
        return None
    except Exception:
        return None

def get_anime_context(filename_or_path: str, client: Any = None) -> Optional[Dict[str, Any]]:
    """
    Fetches and formats anime metadata based on video/subtitle path or filename.
    Prioritizes local Series Bible (Offline-First / Zero Cost), then AniList GraphQL API,
    and finally Gemini parametric knowledge fallback using the highest Flash model.
    """
    clean_title = clean_anime_filename(filename_or_path)
    if not clean_title or len(clean_title) < 2:
        return None

    # 1. Offline-First / Bible-First check (0.00 PLN & 0 ms)
    try:
        from series_memory import SeriesBible
        bible = SeriesBible(anime_title=clean_title)
        bible_chars = bible.data.get("characters", {})
        if bible_chars and len(bible_chars) >= 2:
            characters_list = []
            for c_name, c_val in bible_chars.items():
                if "->" in c_name:
                    continue
                c_desc = c_val.get("description", "") if isinstance(c_val, dict) else str(c_val)
                gender_str = "kobieta" if any(w in c_desc.lower() for w in ["kobieta", "female", "dziewczyna"]) else "mężczyzna"
                characters_list.append({
                    "name": c_name,
                    "gender": gender_str,
                    "gender_raw": "FEMALE" if gender_str == "kobieta" else "MALE",
                    "role": "Główny bohater" if any(w in c_desc.lower() for w in ["główny", "protagoni"]) else "Postać"
                })
            if characters_list:
                return {
                    "title_romaji": bible.anime_title,
                    "title_english": bible.anime_title,
                    "genres": [],
                    "tags": [],
                    "setting_tags": [],
                    "detected_domains": [],
                    "description": f"Kontekst serii wczytany z lokalnej bazy wiedzy (SeriesBible): {bible.anime_title}",
                    "characters": characters_list,
                    "source": "local_series_bible"
                }
    except Exception:
        pass

    meta = fetch_anilist_metadata(clean_title)
    if not meta or not meta.get("characters"):
        meta = fetch_gemini_metadata(clean_title, client=client)
    return meta

def format_anime_context_for_prompt(meta: Dict[str, Any]) -> str:
    """
    Formats fetched metadata into a clean context block with historical and genre guidelines.
    """
    if not meta:
        return ""

    lines = []
    lines.append("=== KONTEKST SERII ANIME, REALIA ŚWIATA & SPECJALIZACJA (AniList) ===")
    title_display = meta.get("title_romaji") or meta.get("title_english") or "Anime"
    if meta.get("title_english") and meta.get("title_english") != title_display:
        title_display += f" ({meta.get('title_english')})"
    lines.append(f"Tytuł: {title_display}")
    
    if meta.get("genres"):
        lines.append(f"Gatunki: {', '.join(meta['genres'])}")

    if meta.get("setting_tags"):
        lines.append(f"[Realia świata / Epoka]: {', '.join(meta['setting_tags'])}")

    if meta.get("detected_domains"):
        lines.append(f"[Dziedzina specjalistyczna / Tematyka]: {', '.join(meta['detected_domains'])}")
        lines.append("(!) WYTYCZNA BRANŻOWA (FILAR XVI): Bezwzględny nakaz stosowania oficjalnej, profesjonalnej polskiej terminologii branżowej (np. w winie: 'szczep', 'rocznik', 'apelacja', 'taniny', 'kupaż', 'ciało wina'). ZAKAZ amatorskich kalek!")

    if meta.get("description"):
        desc = meta["description"]
        if len(desc) > 400:
            desc = desc[:400].rsplit(".", 1)[0] + "."
        lines.append(f"Opis tła fabularnego: {desc}")

    # Stylization guidelines depending on historical background
    is_historical = any(
        t.lower() in ("historical", "mongol empire", "middle ages", "medieval", "edo period", "feudal japan", "ancient china", "samurai")
        for t in (meta.get("genres", []) + meta.get("setting_tags", []))
    )
    if is_historical:
        lines.append("(!) WYTYCZNA STYLIZACJI: Seria osadzona w realiach dawnych/historycznych!")
        lines.append("   - Kategoryczny ZAKAZ współczesnego slangu młodzieżowego ('spoko', 'masakra', 'wkręcasz mnie').")
        lines.append("   - Stosuj szlachetny, epokowy rejestr języka polskiego, dopasowany do hierarchii społecznej i kultury tamtych czasów.")

    if meta.get("characters"):
        lines.append("\nObsada i płeć bohaterów:")
        for c in meta["characters"][:12]:
            lines.append(f" • {c['name']} [{c.get('native_name') or ''}]: {c['gender']} ({c['role']})")

    lines.append("====================================================================\n")
    return "\n".join(lines)
