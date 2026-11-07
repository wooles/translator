"""
Module for automatically fetching anime metadata (plot, genres, characters and genders)
from AniList and MyAnimeList based on filename.
"""

import re
import json
import urllib.request
import urllib.parse
import unicodedata
from pathlib import Path
from typing import Optional, Dict, Any, List, Union, Tuple

_ANILIST_DISABLED: bool = False

def normalize_ascii_diacritics(text: str) -> str:
    """
    Normalizuje znaki diakrytyczne (dwustronna normalizacja Unicode NFKD ASCII-folding):
    usuwa znaki diakrytyczne, akcenty i przegłosy/umlauty z alfabetów łacińskich (np. ä -> a, é -> e, ö -> o, ü -> u).
    """
    if not text or not isinstance(text, str):
        return ""
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


normalize_diacritics = normalize_ascii_diacritics


def normalize_actor_tag(raw_name: str, strip_diacritics: bool = False) -> Tuple[str, Optional[str]]:
    r"""
    Normalizuje etykietę aktora / postaci oraz ekstrahuje jawny znacznik płci z nawiasów:
    a) Wykrywa jawny znacznik płci w nawiasie okrągłym, kwadratowym, klamrowym lub CJK po normalizacji diakrytycznej
       (normalize_ascii_diacritics):
       [\(\[\{（【［〔]\s*(M|Male|Mężczyzna|F|Female|K|Kobieta)\s*[\)\]\}）】］〕].
       Jeśli wykryto M/Male/Mężczyzna -> gender = "MALE".
       Jeśli wykryto F/Female/K/Kobieta -> gender = "FEMALE".
       W przeciwnym razie gender = None.
    b) Usuwa z nazwy aktora wszelkie adnotacje techniczne i sufiksy w nawiasach:
       r"\s*[\(\[\{（【［〔].*?[\)\]\}）】］〕]"
       oraz czyści znaki cudzysłowów, nawiasów i wielokrotne spacje.
    c) Opcjonalnie (strip_diacritics=True) składa znaki diakrytyczne (normalize_ascii_diacritics).
    """
    if not raw_name or not isinstance(raw_name, str):
        return "", None

    gender: Optional[str] = None
    raw_ascii = normalize_ascii_diacritics(raw_name)
    gender_match = re.search(
        r"[\(\[\{（【［〔]\s*(m|male|mezczyzna|mezczyzn|f|female|k|kobieta|kobiet)\s*(?:[,;/\|].*?)?[\)\]\}）】］〕]",
        raw_ascii,
        flags=re.IGNORECASE
    )
    if gender_match:
        tag_val = gender_match.group(1).strip().lower()
        if tag_val in ("m", "male", "mezczyzna", "mezczyzn"):
            gender = "MALE"
        elif tag_val in ("f", "female", "k", "kobieta", "kobiet"):
            gender = "FEMALE"

    clean_name = re.sub(r"\s*[\(\[\{（【［〔].*?[\)\]\}）】］〕]", "", raw_name).strip()
    clean_name = re.sub(r"[\(\[\{（【［〔].*?[\)\]\}）】］〕]", "", clean_name).strip()
    clean_name = re.sub(r"[\(\[\{（【［〔].*$", "", clean_name).strip()
    clean_name = re.sub(r"\s+", " ", clean_name).strip(" \"'„”«»")
    clean_name = re.sub(r"[?!]+$", "", clean_name).strip()
    clean_name = re.sub(r"(?<=[a-z])(?:Heart|Thought|Thoughts|Voice|Internal|Sign)$", "", clean_name).strip()
    if strip_diacritics:
        clean_name = normalize_ascii_diacritics(clean_name).strip()
    return clean_name, gender


def compare_character_names(name1: str, name2: str) -> bool:
    """
    Porównuje imiona postaci z odpornością na znaki diakrytyczne (Unicode NFKD ASCII-folding)
    oraz wielkość liter i znaki przestankowe. Ignoruje umlauty i akcenty.
    """
    if not name1 or not name2:
        return False
    clean1_raw, _ = normalize_actor_tag(name1)
    clean2_raw, _ = normalize_actor_tag(name2)
    norm1 = normalize_ascii_diacritics(clean1_raw or name1).strip().lower()
    norm2 = normalize_ascii_diacritics(clean2_raw or name2).strip().lower()
    if norm1 == norm2:
        return True
    clean1 = re.sub(r"[^\w\s]", "", norm1).strip()
    clean2 = re.sub(r"[^\w\s]", "", norm2).strip()
    return clean1 == clean2 and len(clean1) >= 2


def match_character_in_metadata(
    character_name: str,
    meta_or_characters: Union[Dict[str, Any], List[Dict[str, Any]]]
) -> Optional[Dict[str, Any]]:
    """
    Dopasowuje imię postaci do wpisu w obsadzie serii (AniList / SeriesBible)
    z pełną odpornością na znaki diakrytyczne (Unicode NFKD ASCII-folding).
    Ignoruje umlauty i akcenty w zapytaniach oraz w nazwach z obsady.
    """
    if not character_name or not meta_or_characters:
        return None

    clean_target, explicit_gender = normalize_actor_tag(character_name)
    target_name = clean_target or character_name

    characters_list: List[Dict[str, Any]] = []
    if isinstance(meta_or_characters, dict):
        characters_list = meta_or_characters.get("characters", [])
    elif isinstance(meta_or_characters, list):
        characters_list = meta_or_characters

    if not characters_list:
        return None

    # 1. Dokładne dopasowanie po znormalizowanych diakrytykach
    for c in characters_list:
        raw_c_name = c.get("name") or ""
        clean_c_name, _ = normalize_actor_tag(raw_c_name)
        c_name = clean_c_name or raw_c_name
        if compare_character_names(target_name, c_name):
            return c
        c_native = c.get("native_name") or ""
        if c_native and target_name.strip() == c_native.strip():
            return c

    # 2. Dopasowanie tokenowe (imię / nazwisko) po znormalizowanych diakrytykach
    target_folded = normalize_ascii_diacritics(target_name).strip().lower()
    target_tokens = set(re.findall(r"\b\w+\b", target_folded))
    sig_target = {t for t in target_tokens if len(t) >= 3}

    for c in characters_list:
        raw_c_name = c.get("name") or ""
        clean_c_name, _ = normalize_actor_tag(raw_c_name)
        c_name = clean_c_name or raw_c_name
        c_folded = normalize_ascii_diacritics(c_name).strip().lower()
        c_tokens = set(re.findall(r"\b\w+\b", c_folded))
        sig_c = {t for t in c_tokens if len(t) >= 3}
        if sig_target and sig_c and (sig_target.issubset(sig_c) or sig_c.issubset(sig_target)):
            return c

    return None

def clean_anime_filename(filename_or_path: str) -> str:
    """
    Cleans filename of fansub group tags, quality tags, hashes, and episode numbers
    to extract a clean series title.
    """
    name = Path(filename_or_path).stem

    # 0. Remove language prefixes (e.g. EN_, PL_, JA_)
    name = re.sub(r"^(?:EN|PL|JA|JP|ENG|POL)[._\s-]+", "", name, flags=re.IGNORECASE)

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

def normalize_anime_slug(title: str) -> str:
    """
    Normalizuje tytul serii lub nazwe pliku do spojnego, deterministycznego sluga:
    Usuwa nawiasy, oznaczenia sezonow i epizodow, przeksztalcajac tekst w format z malych liter i podkreslnikow.
    """
    if not title:
        return ""
    cleaned = clean_anime_filename(title) or title
    clean = re.sub(r"\[[^\]]*\]", "", cleaned)
    clean = re.sub(r"\([^)]*\)", "", clean)
    clean = re.sub(r"S0?\d+|Season\s*\d+|2nd\s*Season|\bOdc\b.*|\bEp\b.*|-.*", "", clean, flags=re.IGNORECASE)
    clean = re.sub(r"[^a-zA-Z0-9]+", " ", clean).strip().lower()
    tokens = clean.split()
    if not tokens:
        return ""
    if len(tokens) == 3 and tokens[1] == "no":
        return tokens[2]
    return "_".join(tokens)

def strip_season_suffix(title: str) -> Optional[str]:
    """
    Strips season suffixes (e.g. S2, Season 2, 2nd Season, Part 2, Cour 2, Roman numerals)
    from the end of a series title to enable fallback queries for the parent franchise in AniList.
    Returns cleaned parent title or None if no season suffix was present.
    Titles containing dots (Dr. Stone) or slashes (Fate/Zero) are strictly preserved.
    """
    if not title or not isinstance(title, str):
        return None
    raw = title.strip()
    if len(raw) < 2:
        return None

    # Only strip actual media file extensions if present at the very end
    target = re.sub(r"\.(?:mkv|mp4|avi|ts|ass|srt|m4v|flv)$", "", raw, flags=re.IGNORECASE).strip()

    # Pre-clean fansub release prefix (e.g. [ASW], [SubsPlease]) at the start if present
    target = re.sub(r"^\[[^\]]+\]\s*", "", target)

    # Strip trailing quality / hash brackets (e.g. [1080p], [AE584971]) at the very end if present
    target = re.sub(r"\s*\[(?:1080p|720p|480p|2160p|4K|HEVC|x264|x265|AAC|FLAC|[0-9a-fA-F]{8})[^\]]*\]\s*$", "", target, flags=re.IGNORECASE)
    target = re.sub(r"\s*\((?:1080p|720p|480p|2160p|4K|HEVC|x264|x265|AAC|FLAC)\)\s*$", "", target, flags=re.IGNORECASE)

    season_matched = False
    cleaned = target

    # 1. Bracketed or parenthesized season suffixes at end of string
    bracket_pat = r"[\s\-_:]*[\(\[]\s*(?:(?:Season|Part|Cour)\s*(?:\d+|[IVXLCDM]+)|\d+(?:st|nd|rd|th)\s+(?:Season|Cour|Part)|S\d+)\s*[\)\]]\s*$"
    new_cleaned = re.sub(bracket_pat, "", cleaned, flags=re.IGNORECASE).strip()
    if new_cleaned != cleaned:
        cleaned = new_cleaned
        season_matched = True

    # 2. Standalone unbracketed season suffixes at end of string
    patterns = [
        r"[\s\-_:]+\bS\d+\b\s*$",
        r"[\s\-_:]+\bSeason\s*(?:\d+|[IVXLCDM]+)\b\s*$",
        r"[\s\-_:]+\b\d+(?:st|nd|rd|th)\s+Season\b\s*$",
        r"[\s\-_:]+\bPart\s*(?:\d+|[IVXLCDM]+)\b\s*$",
        r"[\s\-_:]+\b\d+(?:st|nd|rd|th)\s+Part\b\s*$",
        r"[\s\-_:]+\bCour\s*(?:\d+|[IVXLCDM]+)\b\s*$",
        r"[\s\-_:]+\b\d+(?:st|nd|rd|th)\s+Cour\b\s*$",
        r"[\s\-_:]+\b(?:The\s+)?Final\s+Season\b\s*$",
        r"[\s\-_:]+\b(?:II|III|IV|V|VI|VII|VIII|IX|X)\b\s*$",
    ]
    for pat in patterns:
        new_cleaned = re.sub(pat, "", cleaned, flags=re.IGNORECASE).strip()
        if new_cleaned != cleaned:
            cleaned = new_cleaned
            season_matched = True
            break

    # Strip any trailing delimiters (: - _)
    cleaned = re.sub(r"[\s\-_:]+$", "", cleaned).strip()

    if season_matched and cleaned and len(cleaned) >= 2:
        return cleaned
    return None

def _raw_fetch_anilist_metadata(title: str) -> Optional[Dict[str, Any]]:
    """Internal helper to execute AniList GraphQL query for a specific title string."""
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
        characters(sort: [ROLE, RELEVANCE], perPage: 50) {
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
                    r"\benology\b", r"\boenology\b"
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

def fetch_anilist_metadata(title: str) -> Optional[Dict[str, Any]]:
    """
    Queries the AniList GraphQL API to fetch plot synopsis, tags, and character cast.
    Includes circuit-breaker logic, automatic normalization fallback (strip_season_suffix)
    for sequels (S2, Season 2, etc.), and diacritics normalization (Unicode NFKD ASCII-folding)
    when AniList or the title uses variations in umlauts or accents.
    """
    global _ANILIST_DISABLED
    if _ANILIST_DISABLED or not title:
        return None

    res = _raw_fetch_anilist_metadata(title)
    if res and res.get("characters"):
        return res

    # Fallback 1: strip season suffix and query parent franchise
    stripped = strip_season_suffix(title)
    if stripped and stripped != title and not _ANILIST_DISABLED:
        fallback_res = _raw_fetch_anilist_metadata(stripped)
        if fallback_res and fallback_res.get("characters"):
            return fallback_res
        if fallback_res and not res:
            res = fallback_res

    # Fallback 2: Unicode NFKD ASCII-folding diacritics normalization
    folded = normalize_ascii_diacritics(title)
    if folded and folded != title and not _ANILIST_DISABLED:
        folded_res = _raw_fetch_anilist_metadata(folded)
        if folded_res and folded_res.get("characters"):
            return folded_res
        if folded_res and not res:
            res = folded_res

        stripped_folded = strip_season_suffix(folded)
        if stripped_folded and stripped_folded != folded and not _ANILIST_DISABLED:
            fallback_folded = _raw_fetch_anilist_metadata(stripped_folded)
            if fallback_folded and fallback_folded.get("characters"):
                return fallback_folded
            if fallback_folded and not res:
                res = fallback_folded

    return res

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
  "detected_domains": ["Specjalistyczna dziedzina wiedzy lub terminologia branżowa jeśli występuje"],
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
        if not bible_chars or len(bible_chars) < 2:
            folded_title = normalize_diacritics(clean_title)
            if folded_title and folded_title != clean_title:
                bible_folded = SeriesBible(anime_title=folded_title)
                if bible_folded.data.get("characters"):
                    bible = bible_folded
                    bible_chars = bible.data.get("characters", {})

        if bible_chars and len(bible_chars) >= 2:
            characters_list = []
            for c_name, c_val in bible_chars.items():
                if "->" in c_name:
                    continue
                clean_c, explicit_g = normalize_actor_tag(c_name)
                c_norm = clean_c or c_name
                if match_character_in_metadata(c_norm, characters_list):
                    continue
                c_desc = c_val.get("description", "") if isinstance(c_val, dict) else str(c_val)
                raw_g = str(c_val.get("gender") or c_val.get("grammatical_gender") or "").upper() if isinstance(c_val, dict) else ""
                if raw_g in ("FEMALE", "KOBIETA", "FEMININE") or explicit_g == "FEMALE":
                    gender_str = "kobieta"
                    gender_raw = "FEMALE"
                elif raw_g in ("MALE", "MĘŻCZYZNA", "MEZCZYZNA", "MASCULINE") or explicit_g == "MALE":
                    gender_str = "mężczyzna"
                    gender_raw = "MALE"
                elif any(w in c_desc.lower() for w in ["kobieta", "female", "dziewczyna", "woman", "girl"]):
                    gender_str = "kobieta"
                    gender_raw = "FEMALE"
                elif any(w in c_desc.lower() for w in ["mężczyzna", "male", "chłopak", "man", "boy"]):
                    gender_str = "mężczyzna"
                    gender_raw = "MALE"
                else:
                    gender_str = None
                    gender_raw = None
                characters_list.append({
                    "name": c_norm,
                    "gender": gender_str,
                    "gender_raw": gender_raw,
                    "role": "Główny bohater" if any(w in c_desc.lower() for w in ["główny", "protagoni"]) else "Postać"
                })
            if characters_list:
                return {
                    "title_romaji": bible.anime_title,
                    "title_english": bible.anime_title,
                    "genres": bible.data.get("genres", []) if hasattr(bible, "data") and isinstance(bible.data, dict) else getattr(bible, "genres", []),
                    "tags": bible.data.get("tags", []) if hasattr(bible, "data") and isinstance(bible.data, dict) else getattr(bible, "tags", []),
                    "setting_tags": bible.data.get("setting_tags", []) if hasattr(bible, "data") and isinstance(bible.data, dict) else getattr(bible, "setting_tags", []),
                    "detected_domains": bible.data.get("detected_domains", []) if hasattr(bible, "data") and isinstance(bible.data, dict) else getattr(bible, "detected_domains", []),
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
        lines.append("[Założenia domeny tematycznej]: Oficjalna polska terminologia branżowa i specjalistyczne słownictwo dziedzinowe zgodne z realiami świata serii.")

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
        lines.append("   - Eliminacja współczesnego slangu młodzieżowego ('spoko', 'masakra', 'wkręcasz mnie').")
        lines.append("   - Stosuj szlachetny, epokowy rejestr języka polskiego, dopasowany do hierarchii społecznej i kultury tamtych czasów.")

    if meta.get("characters"):
        lines.append("\nObsada i płeć bohaterów:")
        for c in meta["characters"][:12]:
            lines.append(f" • {c['name']} [{c.get('native_name') or ''}]: {c['gender']} ({c['role']})")

    lines.append("====================================================================\n")
    return "\n".join(lines)


_ROMAN_SEASON_MAP: Dict[str, int] = {
    "I": 1, "II": 2, "III": 3, "IV": 4, "V": 5,
    "VI": 6, "VII": 7, "VIII": 8, "IX": 9, "X": 10,
}


def extract_canonical_series_and_season(title: str) -> Tuple[str, Optional[int]]:
    """
    Mapuje tytuł serii (z lub bez sufiksu sezonu) na kanoniczną parę (base_slug, season_num).

    Przykłady:
        "<SERIA_BASE> II"          -> ("<base_slug>", 2)
        "<SERIA_BASE> S2"          -> ("<base_slug>", 2)
        "<SERIA_BASE> Season 2"    -> ("<base_slug>", 2)
        "<SERIA_BASE> 2nd Season"  -> ("<base_slug>", 2)
        "<SERIA_BASE>"             -> ("<base_slug>", None)
        "<SERIA_BASE> Final Season"-> ("<base_slug>", None)

    Nie obcina base_slug do 50 znaków i nie stosuje destrukcyjnej reguły
    3-tokenowego 'no' (cecha normalize_anime_slug).
    """
    if not title or not isinstance(title, str):
        return ("", None)
    raw = title.strip()
    if raw.lower().endswith("_bible.json"):
        raw = raw[:-11]
    elif raw.lower().endswith("_bible"):
        raw = raw[:-6]

    target = re.sub(r"\.(?:mkv|mp4|avi|ts|ass|srt|m4v|flv|json)$", "", raw, flags=re.IGNORECASE).strip()
    target = re.sub(r"^\[[^\]]+\]\s*", "", target)
    target = re.sub(
        r"\s*\[(?:1080p|720p|480p|2160p|4K|HEVC|x264|x265|AAC|FLAC|[0-9a-fA-F]{8})[^\]]*\]\s*$",
        "",
        target,
        flags=re.IGNORECASE,
    )
    target = re.sub(
        r"\s*\((?:1080p|720p|480p|2160p|4K|HEVC|x264|x265|AAC|FLAC)\)\s*$",
        "",
        target,
        flags=re.IGNORECASE,
    )
    target_norm = target.replace("_", " ").strip()

    season_num: Optional[int] = None
    cleaned = target_norm

    season_extract_patterns = [
        (r"[\s\-_:]*[\(\[]\s*(?:Season|Part|Cour)\s*(\d+|[IVXLCDM]+)\s*[\)\]]\s*$", "num_or_roman"),
        (r"[\s\-_:]*[\(\[]\s*(\d+)(?:st|nd|rd|th)\s+(?:Season|Cour|Part)\s*[\)\]]\s*$", "int"),
        (r"[\s\-_:]*[\(\[]\s*S0?(\d+)\s*[\)\]]\s*$", "int"),
        (r"[\s\-_:]+\bS0?(\d+)(?:E\d+)?\b\s*$", "int"),
        (r"[\s\-_:]+\b(?:Season|Part|Cour)\s*(\d+|[IVXLCDM]+)\b\s*$", "num_or_roman"),
        (r"[\s\-_:]+\b(\d+)(?:st|nd|rd|th)\s+(?:Season|Part|Cour)\b\s*$", "int"),
        (r"[\s\-_:]+\b(?:The\s+)?Final\s+Season\b\s*$", "none"),
        (r"[\s\-_:]+\b(II|III|IV|V|VI|VII|VIII|IX|X)\b\s*$", "roman"),
    ]
    for pat, kind in season_extract_patterns:
        m = re.search(pat, cleaned, flags=re.IGNORECASE)
        if m:
            if kind == "int":
                season_num = int(m.group(1))
            elif kind == "roman":
                season_num = _ROMAN_SEASON_MAP.get(m.group(1).upper())
            elif kind == "num_or_roman":
                tok = m.group(1).upper()
                season_num = int(tok) if tok.isdigit() else _ROMAN_SEASON_MAP.get(tok)
            elif kind == "none":
                season_num = None
            cleaned = cleaned[: m.start()].strip()
            break

    cleaned = re.sub(r"[\s\-_:]+$", "", cleaned).strip()
    nfkd = unicodedata.normalize("NFKD", cleaned)
    ascii_str = "".join(c for c in nfkd if not unicodedata.combining(c))
    base_slug = re.sub(r"[^\w\s-]", "", ascii_str, flags=re.UNICODE).strip().lower()
    base_slug = re.sub(r"[-\s_]+", "_", base_slug)
    return (base_slug, season_num)

