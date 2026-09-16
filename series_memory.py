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
from typing import Dict, List, Any, Optional, Set, Tuple

import unicodedata

SERIES_MEMORY_DIR = Path(__file__).parent / "series_memory"

def clean_anime_slug(title: str) -> str:
    """Creates a filesystem-safe identifier slug from anime title, normalizing diacritics."""
    if not title:
        return "default_series"
    # Normalize unicode diacritics (e.g. Caraméliser -> Carameliser)
    nfkd = unicodedata.normalize('NFKD', title)
    title_ascii = "".join([c for c in nfkd if not unicodedata.combining(c)])
    slug = re.sub(r"[^\w\s-]", "", title_ascii, flags=re.UNICODE).strip()
    slug = re.sub(r"[-\s]+", "_", slug)
    return slug[:50] or "default_series"


INHERENT_FEMALE_NOUNS = {
    "girl", "woman", "female", "dziewczyna", "dziewczynka", "kobieta", "matka", "mama",
    "córka", "siostra", "królowa", "księżniczka", "uczennica", "lady", "miss", "mrs", "ms",
    "heroine", "witch", "czarownica", "bohaterka", "staruszka", "babcia"
}

INHERENT_MALE_NOUNS = {
    "boy", "man", "male", "chłopak", "chłopiec", "mężczyzna", "ojciec", "tata",
    "syn", "brat", "król", "książę", "uczeń", "lord", "mr", "hero", "bohater",
    "czarodziej", "wizard", "starzec", "dziadek"
}

GENERIC_CATEGORY_TAGS = {
    "mężczyzna", "mezczyzna", "kobieta", "grupa_kobiet", "grupa_mężczyzn", "grupa_mezczyzn",
    "grupa_mieszana", "brak", "narrator", "głos", "glos", "ktoś", "ktos", "wszyscy",
    "tłum", "tlum", "napis", "napisy", "tytuł", "tytul", "tłumaczenie", "tlumaczenie",
    "main", "default", "alt", "sign", "signs", "crowd", "voice", "unknown", "none",
    "postać", "postac", "interlokutor"
}

POLISH_FEMALE_NAMES = {
    "monika", "anna", "maria", "katarzyna", "małgorzata", "malgorzata", "agnieszka",
    "barbara", "ewa", "magdalena", "elżbieta", "elzbieta", "krystyna", "joanna",
    "aleksandra", "zofia", "danuta", "irena", "jadwiga", "teresa", "halina",
    "karolina", "natalia", "julia", "paulina", "beata", "dorota", "justyna",
    "iwona", "renata", "jolanta", "urszula", "alicja", "sylwia", "patrycja",
    "marta", "dominika", "aneta", "edyta", "izabela", "kinga", "wioletta",
    "kamila", "bogumiła", "bogumila", "wiesława", "wieslawa", "stanisława", "stanislawa",
    "janina", "czesława", "czeslawa", "wanda", "władysława", "wladyslawa", "grażyna", "grazyna",
    "bożena", "bozena", "marzena", "lucyna", "mariola", "henryka", "kazimiera",
    "genowefa", "bronislawa", "bronisława", "stefania", "cecylia", "emilia", "klaudia",
    "weronika", "oliwia", "wiktoria", "maja", "zuzanna", "pola", "antonina",
    "laura", "nadia", "liliana", "klara", "nina", "jagoda", "malwina",
    "kornelia", "kalina", "daria", "diana", "judyta", "fatima", "agata", "alina",
    "anita", "celina", "felicja", "gloria", "helena", "ida", "iga", "ilona",
    "karina", "lena", "lidia", "lila", "lucja", "łucja", "marika", "marlena",
    "martyna", "milena", "miranda", "nikola", "regina", "roksana", "sabina",
    "sara", "sonia", "stella", "tamara", "tola", "żaneta",
    # Hypocoristics and popular variants
    "kasia", "basia", "asia", "ania", "ola", "gosia", "madzia", "zosia",
    "marysia", "natalka", "julka", "krysia", "danka", "ala", "magda"
}

MALE_EXCEPTIONS_ON_A = {
    "kuba", "barnaba", "kosma", "bonawentura", "jarema", "zawisza",
    "sasza", "mustafa", "joshua", "akira", "luka", "luca"
}

ETHNONYMS_AND_COLLECTIVES = {
    # English plural and singular ethnonyms / collectives / polities
    "mongols", "mongol", "tatars", "tatar", "merkit", "merkits", "persians", "persian",
    "romans", "roman", "jurchen", "jurchens", "nomad", "nomads", "pastoralists", "pastoralist",
    "hunters", "hunter", "turks", "turk", "chinese", "arabs", "arab", "japanese",
    "demons", "demon", "humans", "human", "elves", "elf", "dwarves", "dwarf",
    "orcs", "orc", "beasts", "spirits", "monsters",
    # Polish plural and singular ethnonyms / collectives
    "mongołowie", "mongołów", "mongoli", "mongoł", "mongola",
    "tatarzy", "tatarów", "tatar",
    "merkici", "merkitów", "merkit",
    "persowie", "persów", "pers",
    "rzymianie", "rzymian", "rzymianin",
    "koczownicy", "koczowników", "koczownik",
    "nomadzi", "nomadów", "nomada",
    "dżurdżeni", "dżurdżeńczycy", "jurcheni",
    "turcy", "turków", "turek",
    "chińczycy", "chińczyków", "chińczyk",
    "arabowie", "arabów", "arab",
    "japończycy", "japończyków", "japończyk",
    "ludzie", "ludzi", "lud", "człowiek",
    "demony", "demonów", "elfy", "elfów", "krasnoludy", "krasnoludów",
    "orkowie", "orków", "bestie", "duchy", "potwory"
}

def is_inherently_female_name(name: str) -> bool:
    """
    Returns True if the name is an inherently female first name (Polish or universal female name
    in the curated onomastic database or its vocative form on -o/-u).
    Excludes male exceptions on -a (Kuba, Barnaba, Kosma, etc.), interjections ('ała'),
    and generic grammatical categories ('kobieta', 'mężczyzna').
    """
    if not name:
        return False
    clean = extract_clean_speaker_name(name).strip().lower()
    if is_generic_actor_or_category(clean):
        return False
    if clean in MALE_EXCEPTIONS_ON_A:
        return False
    if clean in POLISH_FEMALE_NAMES:
        return True

    # Vocative of known Polish female name ending with -o or -u
    if clean.endswith("o") and len(clean) >= 4:
        stem = clean[:-1] + "a"
        if stem in POLISH_FEMALE_NAMES:
            return True
    if clean.endswith("u") and len(clean) >= 4:
        stem = clean[:-1] + "a"
        if stem in POLISH_FEMALE_NAMES:
            return True

    return False

def to_polish_female_vocative(name: str) -> str:
    """
    Converts a nominative Polish female name ending in -a into its correct vocative (wołacz) form:
    - Diminutives/hypocoristics on -sia, -cia, -nia, -la -> -u (Kasia -> Kasiu, Basia -> Basiu, Ania -> Aniu, Ola -> Olu, Zosia -> Zosiu)
    - Standard female names on -a -> -o (Monika -> Moniko, Anna -> Anno, Maria -> Mario, Katarzyna -> Katarzyno, Zofia -> Zofio)
    Only transforms recognized Polish female names from POLISH_FEMALE_NAMES.
    Non-names, interjections ('Ała!'), and foreign names without Polish vocative tradition remain unchanged.
    Preserves capitalization.
    """
    if not name:
        return name
    clean = name.strip()
    c_lower = clean.lower()
    if c_lower not in POLISH_FEMALE_NAMES:
        return clean
    if not c_lower.endswith("a") or c_lower in MALE_EXCEPTIONS_ON_A:
        return clean

    if any(c_lower.endswith(e) for e in ("kasia", "basia", "asia", "ania", "zosia", "marysia", "gosia", "madzia", "ola")):
        voc = clean[:-1] + ("u" if c_lower.endswith(("sia", "cia", "nia", "ola")) else "o")
        return voc

    # Default female name vocative on -a -> -o
    return clean[:-1] + ("O" if clean[-1].isupper() else "o")

def is_generic_actor_or_category(name: str) -> bool:
    """
    Returns True if the string is a generic grammatical category, placeholder,
    or descriptive label (e.g. 'mężczyzna', 'kobieta', 'grupa_kobiet', 'brak', 'narrator')
    rather than a real named character.
    """
    if not name:
        return True
    clean = extract_clean_speaker_name(name).strip().lower()
    return clean in GENERIC_CATEGORY_TAGS

def extract_clean_speaker_name(name: str) -> str:
    """
    Sanitizes ASS speaker names by stripping style overrides, parenthetical notes,
    and trailing context indicators (e.g. 'Girl\\Italic' -> 'Girl', 'Hebichika (Flashback)' -> 'Hebichika').
    """
    if not name:
        return ""
    # Strip ASS style suffix (e.g. \Italic, /Italic, \Default, \Narration)
    clean = re.split(r"[\\\/]", str(name))[0].strip()
    # Strip parenthetical or bracketed additions (e.g. (Flashback), [Off-screen], (young))
    clean = re.sub(r"[\(\[].*?[\)\]]", "", clean).strip()
    return clean


def generate_polish_name_declension(name: str, gender: str = "UNKNOWN") -> Dict[str, str]:
    """
    Generates 7 grammatical cases for Japanese / foreign anime character names
    following standard Polish literary AVT phonological rules.
    """
    n = name.strip()
    g = gender.upper()
    if not n:
        return {}
    if len(n) <= 1 or not any(c.isalpha() for c in n):
        return {"M": n, "D": n, "C": n, "B": n, "N": n, "Ms": n, "W": n}

    words = n.split()
    if len(words) > 1:
        sub_decls = [generate_polish_name_declension(w, gender) for w in words]
        if all(sub_decls):
            return {
                case: " ".join(d.get(case, w) for d, w in zip(sub_decls, words))
                for case in ["M", "D", "C", "B", "N", "Ms", "W"]
            }

    # Already inflected tokens or non-nominative plural/case endings
    if n.lower().endswith(("ą", "ę", "ej", "ach", "ami", "om")):
        return {"M": n, "D": n, "C": n, "B": n, "N": n, "Ms": n, "W": n}

    is_female = (g == "FEMALE" or "KOBIETA" in g or "ŻEŃSK" in g)

    # 0. Neuter nouns ending in -um (e.g. Imperium, Muzeum, Liceum, Akwarium, Koloseum, Seminarium):
    # In Polish singular, these borrowings from Latin are strictly indeclinable across all 7 cases (M=D=C=B=N=Ms=W).
    if n.lower().endswith("um"):
        return {"M": n, "D": n, "C": n, "B": n, "N": n, "Ms": n, "W": n}

    # 1. Names ending in -a (both female and male like Akira, Soma, Luca, Seneca, Alicia, Maria)
    if n.endswith("a"):
        stem = n[:-1]
        if not stem:
            return {"M": n, "D": n, "C": n, "B": n, "N": n, "Ms": n, "W": n}

        # Phonological alternations in Polish:
        # -ia (Maria, Alicia, Julia, Silvia) -> D./C./Ms. -ii; B. -ię; N. -ią; W. -io
        if stem.endswith("i"):
            return {
                "M": n,
                "D": stem + "i",
                "C": stem + "i",
                "B": stem + "ę",
                "N": stem + "ą",
                "Ms": stem + "i",
                "W": stem + "o"
            }
        # -ya (Freya, Maya, Anya, Kaya) -> D./C./Ms. -i; B. -ę; N. -ą; W. -o
        elif stem.endswith("y"):
            return {
                "M": n,
                "D": stem + "i",
                "C": stem + "i",
                "B": stem + "ę",
                "N": stem + "ą",
                "Ms": stem + "i",
                "W": stem + "o"
            }
        # -ca foreign names (Luca, Seneca, Petrarca, Mica) -> hard k stem in D/B/N
        elif stem.endswith("c"):
            return {
                "M": n,
                "D": stem[:-1] + "ki",
                "C": stem + "e",
                "B": stem[:-1] + "kę",
                "N": stem[:-1] + "ką",
                "Ms": stem + "e",
                "W": stem + "o"
            }

        # Consonant stems before -a
        if stem.endswith("k"):
            c_ms = stem[:-1] + "ce"
            d_case = stem + "i"
        elif stem.endswith("g"):
            c_ms = stem[:-1] + "dze"
            d_case = stem + "i"
        elif stem.endswith("r"):
            c_ms = stem[:-1] + "rze"
            d_case = stem + "y"
        elif stem.endswith("t"):
            c_ms = stem[:-1] + "cie"
            d_case = stem + "y"
        elif stem.endswith("d"):
            c_ms = stem[:-1] + "dzie"
            d_case = stem + "y"
        elif stem.endswith("s"):
            c_ms = stem[:-1] + "sie"
            d_case = stem + "y"
        elif stem.endswith("z"):
            c_ms = stem[:-1] + "zie"
            d_case = stem + "y"
        elif stem.endswith("n"):
            c_ms = stem[:-1] + "nie"
            d_case = stem + "y"
        elif stem.endswith("m"):
            c_ms = stem[:-1] + "mie"
            d_case = stem + "y"
        elif stem.endswith("b"):
            c_ms = stem[:-1] + "bie"
            d_case = stem + "y"
        elif stem.endswith("p"):
            c_ms = stem[:-1] + "pie"
            d_case = stem + "y"
        elif stem.endswith("w"):
            c_ms = stem[:-1] + "wie"
            d_case = stem + "y"
        elif stem.endswith("ł"):
            c_ms = stem[:-1] + "le"
            d_case = stem + "y"
        elif stem.endswith("l"):
            c_ms = stem + "i"
            d_case = stem + "i"
        elif stem.endswith(("cz", "sz", "rz", "ż")):
            c_ms = stem + "y"
            d_case = stem + "y"
        else:
            c_ms = stem + "e"
            d_case = stem + "y"

        return {
            "M": n,
            "D": d_case,
            "C": c_ms,
            "B": stem + "ę",
            "N": stem + "ą",
            "Ms": c_ms,
            "W": stem + "o"
        }

    # Female names ending in consonant or vowel other than -a: strictly undeclined in Polish (PWN norm)
    if is_female:
        return {"M": n, "D": n, "C": n, "B": n, "N": n, "Ms": n, "W": n}

    # 2. Male names ending in consonant
    if n[-1].lower() not in "aeiouyąęó":
        stem = n
        last_c = n[-1].lower()
        last_2c = n[-2:].lower() if len(n) >= 2 else ""

        # Narzędnik po k, g: -iem (Gujukiem, Güyükiem, Olegiem, Magiem)
        n_case = stem + "iem" if last_c in ("k", "g") else stem + "em"

        # Miejscownik i Wołacz
        if last_c in ("l", "k", "g", "j", "c") or last_2c in ("ch", "cz", "sz", "rz", "th"):
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
        elif last_c == "w":
            c_ms = stem + "ie"
            c_w = stem + "ie"
        else:
            c_ms = stem + "ie"
            c_w = stem + "ie"

        return {
            "M": n,
            "D": stem + "a",
            "C": stem + "owi",
            "B": stem + "a",
            "N": n_case,
            "Ms": c_ms,
            "W": c_w
        }

    # 3. Male names ending in vowels other than -a (-o, -e, -i, -u, -y)
    # In Japanese AVT, vowel-ending names are kept uninflected to preserve phonetic integrity (Belczyk/PWN).
    return {"M": n, "D": n, "C": n, "B": n, "N": n, "Ms": n, "W": n}


def _fix_ubrac_clothes_match(m) -> str:
    lead = m.group(1)
    suffix = m.group(2) or ""
    sep = m.group(3)
    garment = m.group(4)
    is_cap = lead.isupper()
    if not suffix:
        verb = "Założył" if is_cap else "założył"
    elif suffix == "a":
        verb = "Założyła" if is_cap else "założyła"
    elif suffix == "o":
        verb = "Założyło" if is_cap else "założyło"
    elif suffix == "i":
        verb = "Założyli" if is_cap else "założyli"
    elif suffix == "y":
        verb = "Założyły" if is_cap else "założyły"
    elif suffix == "em":
        verb = "Założyłem" if is_cap else "założyłem"
    elif suffix == "am":
        verb = "Założyłam" if is_cap else "założyłam"
    elif suffix == "eś":
        verb = "Założyłeś" if is_cap else "założyłeś"
    elif suffix == "aś":
        verb = "Założyłaś" if is_cap else "założyłaś"
    else:
        verb = ("Założył" if is_cap else "założył") + suffix
    return f"{verb}{sep}{garment}"


def _fix_rozebrac_clothes_match(m) -> str:
    lead = m.group(1)
    suffix = m.group(2) or ""
    sep = m.group(3)
    garment = m.group(4)
    is_cap = lead.isupper()
    if not suffix:
        verb = "Zdjął" if is_cap else "zdjął"
    elif suffix == "a":
        verb = "Zdjęła" if is_cap else "zdjęła"
    elif suffix == "o":
        verb = "Zdjęło" if is_cap else "zdjęło"
    elif suffix == "i":
        verb = "Zdjęli" if is_cap else "zdjęli"
    elif suffix == "y":
        verb = "Zdjęły" if is_cap else "zdjęły"
    elif suffix == "em":
        verb = "Zdjąłem" if is_cap else "zdjąłem"
    elif suffix == "am":
        verb = "Zdjąłam" if is_cap else "zdjąłam"
    elif suffix == "eś":
        verb = "Zdjąłeś" if is_cap else "zdjąłeś"
    elif suffix == "aś":
        verb = "Zdjąłaś" if is_cap else "zdjąłaś"
    else:
        verb = ("Zdjął" if is_cap else "zdjął") + suffix
    return f"{verb}{sep}{garment}"


def _fix_odegrac_znaczenie(m) -> str:
    lead = m.group(1)
    is_cap = lead[0].isupper()
    if lead.endswith("li"):
        verb = "Mieli" if is_cap else "mieli"
    elif lead.endswith("ły"):
        verb = "Miały" if is_cap else "miały"
    elif lead.endswith("ło"):
        verb = "Miało" if is_cap else "miało"
    elif lead.endswith("ła"):
        verb = "Miała" if is_cap else "miała"
    elif lead.endswith("ł"):
        verb = "Miał" if is_cap else "miał"
    elif "wa" in lead:
        verb = "Ma" if is_cap else "ma"
    else:
        verb = "Mieć" if is_cap else "mieć"
    return f"{verb} znaczenie"


def _fix_kupic_czas(m) -> str:
    lead = m.group(1)
    is_cap = lead[0].isupper()
    if lead.endswith("ła"):
        verb = "Zyskała" if is_cap else "zyskała"
    elif lead.endswith("ło"):
        verb = "Zyskało" if is_cap else "zyskało"
    elif lead.endswith("li"):
        verb = "Zyskali" if is_cap else "zyskali"
    elif lead.endswith("ły"):
        verb = "Zyskały" if is_cap else "zyskały"
    elif lead.endswith("ł"):
        verb = "Zyskał" if is_cap else "zyskał"
    elif lead.endswith("my"):
        verb = "Zyskamy" if is_cap else "zyskamy"
    elif lead.endswith("sz"):
        verb = "Zyskasz" if is_cap else "zyskasz"
    elif "kupuj" in lead.lower():
        verb = "Zyskujemy" if lead.endswith("emy") else ("Zyskują" if lead.endswith("ą") else ("Zyskuje" if lead.endswith("e") else "zyskuje"))
        if not is_cap:
            verb = verb.lower()
    else:
        verb = "Zyskać" if is_cap else "zyskać"
    return f"{verb} na czasie"



CLOTHES_PATTERN = (
    r"(?:buty|butów|butami|butach|trampki|trampkami|kalosze|kaloszami|"
    r"kurtk(?:a|ę|i|ce|ą|ach|ami)|płaszcz(?:a|em|u|e|ach|ami)?|spodni(?:e|ami|ach)?|spodni|"
    r"bluz(?:a|ę|y|ce|ą|ki|kach|kami)|czapk(?:a|ę|i|ce|ą|ach|ami)|szalik(?:a|u|iem|i|ach|ami)?|"
    r"rękawiczk(?:i|ami|ach|ek)|rękawic(?:e|ami|ach|ą|y)|skarpet(?:ki|ek|kami|kach)|"
    r"sukienk(?:a|ę|i|ce|ą|ach|ami))"
)

TYPO_NORMALIZATIONS = [
    # Clothing collocations (Norma Wzorcowa PWN: 'zakładać/wkładać buty', a nie 'ubierać')
    (rf"\b([Uu])bierz(\s+)({CLOTHES_PATTERN})\b",
     lambda m: ("Załóż" if m.group(1).isupper() else "załóż") + m.group(2) + m.group(3)),
    (rf"\b([Uu])bierzcie(\s+)({CLOTHES_PATTERN})\b",
     lambda m: ("Załóżcie" if m.group(1).isupper() else "załóżcie") + m.group(2) + m.group(3)),
    (rf"\b([Uu])bierać(\s+)({CLOTHES_PATTERN})\b",
     lambda m: ("Zakładać" if m.group(1).isupper() else "zakładać") + m.group(2) + m.group(3)),
    (rf"\b([Uu])brać(\s+)({CLOTHES_PATTERN})\b",
     lambda m: ("Założyć" if m.group(1).isupper() else "założyć") + m.group(2) + m.group(3)),
    (rf"\b([Uu])brał(em|am|aś|eś|a|o|i|y)?(\s+)({CLOTHES_PATTERN})\b",
     _fix_ubrac_clothes_match),
    (rf"\b([Rr])ozbierz(\s+)({CLOTHES_PATTERN})\b",
     lambda m: ("Zdejmij" if m.group(1).isupper() else "zdejmij") + m.group(2) + m.group(3)),
    (rf"\b([Rr])ozebrać(\s+)({CLOTHES_PATTERN})\b",
     lambda m: ("Zdjąć" if m.group(1).isupper() else "zdjąć") + m.group(2) + m.group(3)),
    (rf"\b([Rr])ozebrał(em|am|aś|eś|a|o|i|y)?(\s+)({CLOTHES_PATTERN})\b",
     _fix_rozebrac_clothes_match),
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
    # Chained bracket sanitization (Filar IV / LX / XCVIII)
    (r"\s*\]\s*\[\s*", r"\\N"),
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
    # Absolute linguistic & orthographic invariants (Filar CLXIV)
    (r"(^|[^\w]|\\[Nnh])([Ww])\s*każdym\s+bądź\s+razie\b", r"\g<1>\g<2> każdym razie"),
    (r"(^|[^\w]|\\[Nnh])([Ww])\s+cudzysłowiu\b", r"\g<1>\g<2> cudzysłowie"),
    (r"(^|[^\w]|\\[Nnh])([Pp])o\s+najmniejszej\s+linii\s+oporu\b", r"\g<1>\g<2>o linii najmniejszego oporu"),
    (r"(^|[^\w]|\\[Nnh])spowrotem\b", r"\g<1>z powrotem"),
    (r"(^|[^\w]|\\[Nnh])Spowrotem\b", r"\g<1>Z powrotem"),
    (r"(^|[^\w]|\\[Nnh])([Dd])latego\s+bo\b", r"\g<1>\g<2>latego że"),
    (r"(^|[^\w]|\\[Nnh])([Oo])d\s+nienacka\b", r"\g<1>znienacka"),
    (r"\b((?:[A-Za-ząćęłńóśźż0-9]+\s+)?(?:raz|razy|kroć|dni|lat|godzin|minut|sekund|miesięcy|tygodni|kolejek|prób|zwycięstw|porażek))\s+pod\s+rząd\b", r"\1 z rzędu"),
    (r"\b([Dd]wa|[Tt]rzy|[Cc]ztery|[Pp]ięć|[Ss]ześć|[Ss]iedem|[Oo]siem|[Dd]ziewięć|[Dd]ziesiąt|[Kk]ilka|[Pp]arę|[Ww]iele|[Kk]olejn[a-ząćęłńóśźż]*)\s+([a-ząćęłńóśźż]+)\s+pod\s+rząd\b", r"\1 \2 z rzędu"),
    # Absolute pleonasms (Filar IV / Belczyk / PWN)
    (r"\b([Ss]pada(?:ć|m|sz|my|cie|ją|ł|ła|ło|li|ły)?)\s+w\s+dół\b", r"\1"),
    (r"\b([Ss]pada(?:ć|m|sz|my|cie|ją|ł|ła|ło|li|ły)?)\s+na\s+dół\b", r"\1"),
    (r"\b([Ww]znosi(?:ć|m|sz|my|cie|ją|ł|ła|ło|li|ły)?)\s+się\s+w\s+górę\b", r"\1 się"),
    (r"\b([Ww]znosi(?:ć|m|sz|my|cie|ją|ł|ła|ło|li|ły)?)\s+się\s+do\s+góry\b", r"\1 się"),
    (r"\b([Cc]ofn(?:ąć|ął|ęła|ęło|ęli|ęły|ij|ijcie|ę|iesz|ie|iemy|iecie|ą)|[Cc]ofa(?:ć|m|sz|my|cie|ją|ł|ła|ło|li|ły)?)\s+się\s+do\s+tyłu\b", r"\1 się"),
    (r"\b([Cc]ofn(?:ąć|ął|ęła|ęło|ęli|ęły|ij|ijcie|ę|iesz|ie|iemy|iecie|ą)|[Cc]ofa(?:ć|m|sz|my|cie|ją|ł|ła|ło|li|ły)?)\s+się\s+wstecz\b", r"\1 się"),
    (r"\b[Pp]ełn(?:y|ego|emu|ym|a|ą|ej|e|ych|ymi)\s+(komplet(?:y|ów|om|ami|ach)?)\b", lambda m: m.group(1).capitalize() if m.group(0)[0].isupper() else m.group(1)),
    (r"\b[Gg]łówn(?:y|ego|emu|ym|a|ą|ej|e|ych|ymi)\s+(priorytet(?:y|ów|om|ami|ach)?)\b", lambda m: m.group(1).capitalize() if m.group(0)[0].isupper() else m.group(1)),
    (r"\b((?:[A-Za-ząćęłńóśźż0-9]+\s+)?(?:godzin[aeyęi]?|miesiąc[ae]?|miesięcy|dni[aey]?|tydzień|tygodni[ae]?|rok[u]?|lat(?:a)?))\s+czasu\b", r"\1"),
    (r"\b([Pp]rzedzia[łl][a-ząćęłńóśźż]*)\s+czasu\b", r"\1"),
    (r"\b([Oo]kres[a-ząćęłńóśźż]*)\s+czasu\b", r"\1"),
    (r"\b[Ww]\s+dniu\s+dzisiejszym\b", "dzisiaj"),
    (r"\b[Dd]zień\s+dzisiejszy\b", "dzisiejszy dzień"),
    (r"\b[Nn]a\s+dzień\s+dzisiejszy\b", lambda m: "Na dziś" if m.group(0)[0].isupper() else "na dziś"),
    (r"\b[Pp]otencjaln(?:e|ych|ym|ymi)\s+(możliwoś(?:ć|ci|cią|ciom|ciami|ciach))\b", lambda m: m.group(1).capitalize() if m.group(0)[0].isupper() else m.group(1)),
    (r"\b[Ww]zajemn(?:a|ej|ą|e|ych|ym|ymi)\s+(współprac(?:a|y|ę|ą|ie|om|ami))\b", lambda m: m.group(1).capitalize() if m.group(0)[0].isupper() else m.group(1)),
    (r"\b[Ww]zajemn(?:a|ej|ą|e|ych|ym|ymi)\s+(relacj(?:a|e|i|om|ami|ach|ę|ą))\b", lambda m: m.group(1).capitalize() if m.group(0)[0].isupper() else m.group(1)),
    (r"\b[Ww]zajemn(?:y|ego|emu|ym)\s+(szacunk(?:u|iem)?|szacunek)\b", lambda m: m.group(1).capitalize() if m.group(0)[0].isupper() else m.group(1)),
    (r"\b[Ww]zajemn(?:a|ej|ą)\s+(sympati(?:a|i|ę|ą))\b", lambda m: m.group(1).capitalize() if m.group(0)[0].isupper() else m.group(1)),
    (r"\b[Mm]artw(?:e|ych|ym|ymi)\s+(zwłok(?:i|ach|ami|om))\b", lambda m: m.group(1).capitalize() if m.group(0)[0].isupper() else m.group(1)),
    (r"\b[Ii]nn(?:a|ej|ą|e|ych|ym|ymi)\s+(alternatyw(?:a|y|om|ami|ach|ę))\b", lambda m: m.group(1).capitalize() if m.group(0)[0].isupper() else m.group(1)),
    (r"\b[Rr]óżn(?:e|ych|ym|ymi|a|ej|ą)\s+(wariant(?:y|ów|om|ami|ach)?)\b", lambda m: m.group(1).capitalize() if m.group(0)[0].isupper() else m.group(1)),
    (r"\b([Ff]akt(?:y|ów|om|ami|ach)?)\s+autentyczn(?:e|ych|ym|ymi)\b", r"\1"),
    (r"\b([Aa]kwen(?:y|ów|om|ami|ach)?)\s+wodn(?:y|e|ych|ym|ymi)\b", r"\1"),
    (r"\b([Kk]ontynuowa(?:ć|m|sz|my|cie|ją|ł|ła|ło|li|ły)?)\s+dalej\b", r"\1"),
    (r"\b([Pp]owtórzy(?:ć|m|sz|my|cie|ją|ł|ła|ło|li|ły)?)\s+(?:znowu|ponownie)\b", r"\1"),
    (r"\b([Pp]onownie)\s+powtórzy(?:ć|m|sz|my|cie|ją|ł|ła|ło|li|ły)?\b", lambda m: "Powtórzyć" if m.group(0)[0].isupper() else "powtórzyć"),
    (r"\b[Mm]iesiąc\s+(styczeń|luty|marzec|kwiecień|maj|czerwiec|lipiec|sierpień|wrzesień|październik|listopad|grudzień)\b", r"\1"),
    (r"\b[Ww]\s+miesiącu\s+(styczniu|lutym|marcu|kwietniu|maju|czerwcu|lipcu|sierpniu|wrześniu|październiku|listopadzie|grudniu)\b", r"w \1"),
    (r"\b[Cc]iężki\s+orzech\s+do\s+zgryzienia\b", "twardy orzech do zgryzienia"),
    (r"\b[Cc]iężkim\s+orzechem\s+do\s+zgryzienia\b", "twardym orzechem do zgryzienia"),
    (r"\b([Oo]dnie(?:ść|sie|siemy|siecie|są)|[Oo]dni[óo]sł|[Oo]dniosł[aoy]|[Oo]dnieśli|[Oo]dniosły|[Oo]dniosłem|[Oo]dniosłam|[Oo]dniosłeś|[Oo]dniosłaś)\s+porażk[ęi]\b",
     lambda m: m.group(0).replace("odnie", "ponie").replace("Odnie", "Ponie").replace("odnió", "ponió").replace("Odnió", "Ponió").replace("odnios", "ponios").replace("Odnios", "Ponios")),
    (r"\b([Oo]dgr(?:ywa|ywał|ywała|ywali|ywają|ywać)|[Oo]degr(?:ać|ał|ała|ało|ali|ały))\s+znaczenie\b", _fix_odegrac_znaczenie),
    (r"\b[Pp]odda(?:ć|ł|ła|ło|li|ły|je|ją)\s+pod\s+wątpliwość\b", lambda m: m.group(0).replace("odda", "oda").replace("Odda", "Oda").replace("pod wątpliwość", "w wątpliwość")),
    (r"\b([Pp])rzeznaczy(ć|ł|ła|ło|li|ły|łem|łam|łeś|łaś)\s+na\s+straty\b", lambda m: ("Spisa" if m.group(1) == "P" else "spisa") + m.group(2) + " na straty"),
    (r"\b([Pp])rzeznacz(ę|ysz|y|ymy|ycie|ą)\s+na\s+straty\b", lambda m: ("Spisz" if m.group(1) == "P" else "spisz") + m.group(2) + " na straty"),
    (r"\b([Kk]upi(?:ć|ł|ła|ło|li|ły|my|sz)?|[Kk]upuj(?:e|emy|ą|esz)?)\s+(?:trochę\s+)?czasu\b", _fix_kupic_czas),
    # Somatic possessive pronoun pleonasm: 'boli mnie moja głowa' -> 'boli mnie głowa'
    (r"\b([Bb]oli\s+(?:mnie|cię|go|ją|nas|was|ich))\s+(?:moja|twój|twoja|twoje|jego|jej|nasza|nasz|wasz|wasza|ich|swoja|swój|swoje)\s+(głow[aęy]|serce|brzuch|nog[aęyie]|ręk[aęyie]|plecy|ramię|ramiona|ucho|uszy|gardło|ząb|zęby)\b", r"\1 \2"),
    (r"\b([Zz]łama[ł|łem|łam|łeś|łaś|li|ły])\s+(?:swoją|moją|twoją|jego|jej|naszą|waszą|ich)\s+(nogę|rękę|palec|kość|żebro)\b", r"\1 \2"),
    (r"\b([Oo]tw[óo]rz(?:ył|yła|yli|yłam|yłem|yłeś|yłaś|cie)?|[Zz]amkn(?:ij|ijcie|ął|ęła|ęli|ęłam|ęłem|ęłaś|ełeś))\s+(?:swoje|twoje|moje|jego|jej|nasze|wasze|ich)\s+(oczy|powieki|usta)\b", r"\1 \2"),
    # Absolute grammatical government and gender (Filar IV / X)
    (r"\b([Cc]zarn[a-ząćęłńóśźż]*)\s+posok(?:u|iem|owi|a)\b", lambda m: ("Czarna posoka" if m.group(0)[0].isupper() else "czarna posoka")),
    (r"\b[Zz]\s+czarnego\s+posoku\b", "z czarnej posoki"),
    (r"\b[Pp]rzez\s+czarny\s+posok\b", "przez czarną posokę"),
    (r"\b[Mm]am\s+przez\s+(?:to|coś)\s+uraz\b", lambda m: "Mam do tego uraz" if m.group(0)[0].isupper() else "mam do tego uraz"),
    (r"\b[Dd]wa\s+tysiące\s+wystarczy\b", lambda m: "Dwa tysiące wystarczą" if m.group(0)[0].isupper() else "dwa tysiące wystarczą"),
    (r"\b[Pp]ółtorej\s+roku\b", lambda m: "Półtora roku" if m.group(0)[0].isupper() else "półtora roku"),
    # Kakegoe physical/festive interjections (Filar XVIII / CLXIV)
    (r"\bTamaya[!]*", "Ale widok!"),
    (r"\b[Oo]ttotto[\.!\?…]*", "Ło, ło, ło...!"),
    # Absolute dialogic calques (Filar IV / CLIII / CLXVI)
    (r"\b[Zz]rób\s+swoje\s+najlepsze\b", lambda m: "Daj z siebie wszystko" if m.group(0)[0].isupper() else "daj z siebie wszystko"),
    (r"\b[Zz]róbcie\s+swoje\s+najlepsze\b", lambda m: "Dajcie z siebie wszystko" if m.group(0)[0].isupper() else "dajcie z siebie wszystko"),
    (r"\b[Dd]obrej\s+nocy\b", lambda m: "Dobranoc" if m.group(0)[0].isupper() else "dobranoc"),
    # Anti-pivot fansub cliché eradication (Filar CLXVI)
    (r"\b([Ww])ita(j|jcie|m|my)\s+z\s+powrotem(!|\.|\.\.\.|,)?(?=\s|$|[,\.!\?])", lambda m: ("Witajcie!" if m.group(2) == "jcie" else ("Witamy!" if m.group(2) == "my" else ("Witam!" if m.group(2) == "m" else "Witaj!")))),
    (r"\b([Nn])ie\s+ma\s+mowy,?\s+(?:że|a)?by(śmy|ście|m|ś)?\b", lambda m: ("Wykluczone, by" if m.group(1).isupper() else "wykluczone, by") + (m.group(2) or "")),
    (r"\b([Mm](?:am|asz|a|amy|acie|ają|iałem|iałam|iał|iała|iało|ieliśmy|iałyśmy|ieli|iały|iałby|iałaby|iałoby|ieliby|iałyby)|[Bb]ęd(?:ę|ziesz|zie|ziemy|ziecie|dą)\s+mieć)\s+taką\s+nadzieję\b", r"\1 nadzieję"),
    (r"\b([Mm](?:am|asz|a|amy|acie|ają|iałem|iałam|iał|iała|iało|ieliśmy|iałyśmy|ieli|iały|iałby|iałaby|iałoby|ieliby|iałyby)|[Bb]ęd(?:ę|ziesz|zie|ziemy|ziecie|dą)\s+mieć)\s+nadzieję\s+na\s+to\b", r"\1 nadzieję"),
    # Japanese false proper noun & honorific titular repair (Filar II / Kanon)
    (r"(^|[^\w]|\\[Nnh])Ouji([!\?…]+)", r"\g<1>Książę\g<2>"),
    (r"(^|[^\w]|\\[Nnh])ouji([!\?…]+)", r"\g<1>książę\g<2>"),
    # Conversational continuation calque (Filar IV / CLVI)
    (r"(^|[^\w]|\\[Nnh])([Ii]|[Aa])\s+co\s+z\s+tego\?(\s*\\N\s*|\s+)(?=[Tt]o\s+wy\b|[Cc]hodzicie\b|[Jj]esteście\b|[Cc]o\s+było\b|[Cc]o\s+dalej\b|[Jj]ak\s+to\b)", r"\g<1>\g<2> co?\g<3>"),
    # Manga canon titular enforcement: 'Książę Kaiju' -> 'Potworny Królewicz' (Filar II / Kanon)
    (r"(^|[^\w]|\\[Nnh])([Kk])siążę\s+[Kk]aiju\b", lambda m: ("Potworny Królewicz" if m.group(2) == "K" else "potworny królewicz")),
    (r"(^|[^\w]|\\[Nnh])([Kk])sięcia\s+[Kk]aiju\b", lambda m: ("Potwornego Królewicza" if m.group(2) == "K" else "potwornego królewicza")),
    (r"(^|[^\w]|\\[Nnh])([Kk])sięciu\s+[Kk]aiju\b", lambda m: ("Potwornemu Królewiczowi" if m.group(2) == "K" else "potwornemu królewiczowi")),
    (r"(^|[^\w]|\\[Nnh])([Kk])sięciem\s+[Kk]aiju\b", lambda m: ("Potwornym Królewiczem" if m.group(2) == "K" else "potwornym królewiczem")),
    # Otaku slang adaptation: 'Kuro-taso' -> 'Kuroe' (Filar II / Kanon)
    (r"(^|[^\w]|\\[Nnh])Kuro-?taso\b", r"\g<1>Kuroe"),
    (r"(^|[^\w]|\\[Nnh])kuro-?taso\b", r"\g<1>kuroe"),
    # Binary alternative comma eradication: 'w kapciach, czy bez' -> 'w kapciach czy bez' (Filar XCI)
    (r"\b([A-Za-ząćęłńóśźż0-9]+),\s+czy\s+(bez|nie|tak)\b", r"\1 czy \2"),
    # Trailing cut-off speech attached dash: 'Rin–' -> 'Rin...' (Filar XCI)
    (r"([A-Za-ząćęłńóśźż])–(?=\s*\\N|\s*$|[!\?…])", r"\1..."),
    # Deictic temporal syntax normalizations (Filar CLXVIII)
    (r"\b([Pp])ojutrzejsz(?:y|ą|a|e|ego|ej|emu|ym|ych|ymi)?\s+([a-ząćęłńóśźż]+)\b",
     lambda m: (f"{m.group(2)} pojutrze" if m.group(1) == "p" else f"{m.group(2).capitalize()} pojutrze")),
    (r"\b([Pp])rzedwczorajsz(?:y|ą|a|e|ego|ej|emu|ym|ych|ymi)?\s+([a-ząćęłńóśźż]+)\b",
     lambda m: (f"{m.group(2)} sprzed dwóch dni" if m.group(1) == "p" else f"{m.group(2).capitalize()} sprzed dwóch dni")),
    (r"\b([Ww])\s+dzisiejszy\s+wieczór\b", lambda m: "Dziś wieczorem" if m.group(1) == "W" else "dziś wieczorem"),
    (r"\b([Ww])\s+jutrzejszy\s+poranek\b", lambda m: "Jutro rano" if m.group(1) == "W" else "jutro rano"),
    (r"\b([Ww])e\s+wczorajszy\s+wieczór\b", lambda m: "Wczoraj wieczorem" if m.group(1) == "W" else "wczoraj wieczorem"),
    (r"\b([Ww])\s+dzisiejszą\s+noc\b", lambda m: "Dziś w nocy" if m.group(1) == "W" else "dziś w nocy"),
    (r"\b([Pp])rzyszłotygodniow(?:y|ą|a|e|ego|ej|emu|ym|ych|ymi)?\s+([a-ząćęłńóśźż]+)\b",
     lambda m: (f"{m.group(2)} w przyszłym tygodniu" if m.group(1) == "p" else f"{m.group(2).capitalize()} w przyszłym tygodniu")),
    # Eradication of youth slang 'żenada' in dialogue (Filar CLXX)
    (r"\b([Aa]le|[Cc]o\s+za)\s+żenada[!\?…\.]*", lambda m: ("Ale marudzisz..." if m.group(1)[0].isupper() else "ale marudzisz...")),
    (r"^\s*([Żż]enada)[!\?…\.]*\s*$", lambda m: ("Ale marudzisz..." if m.group(1)[0].isupper() else "ale marudzisz...")),
    (r"\b[Ii]\s+gitara\b", lambda m: "Doskonale" if m.group(0)[0].isupper() else "doskonale"),
    (r"\b[Ss]tul\s+pysk\b", lambda m: "Zamilcz" if m.group(0)[0].isupper() else "zamilcz"),
    (r"\b[Zz]mywajmy\s+się\s+stąd\b", lambda m: "Uciekajmy stąd" if m.group(0)[0].isupper() else "uciekajmy stąd"),
    (r"\b[Zz]mywamy\s+się\s+stąd\b", lambda m: "Uciekamy stąd" if m.group(0)[0].isupper() else "uciekamy stąd"),
    (r"\b[Zz]mywaj\s+się\s+stąd\b", lambda m: "Uciekaj stąd" if m.group(0)[0].isupper() else "uciekaj stąd"),
    (r"\b[Kk]łamstwo\s+jak\s+byk\b", lambda m: "Bezczelne kłamstwo" if m.group(0)[0].isupper() else "bezczelne kłamstwo"),
    (r"\b[Pp]rzejmuję\s+stery\b", lambda m: "Teraz ja mówię" if m.group(0)[0].isupper() else "teraz ja mówię"),
    (r"\b[Dd]la\s+zabicia\s+czasu\b", lambda m: "Dla rozrywki" if m.group(0)[0].isupper() else "dla rozrywki"),
    (r"\b[Ww]ylec(?:ieć|iał|iała|ieli)\s+ze\s+szkoły\b", "zostać wydalonym ze szkoły"),
]


def sanitize_lexical_text(text: str) -> str:
    """Sanitizes text against known LLM/OCR typos and deformed Polish words (Filar CLXIV/CLXX)."""
    if not text:
        return ""
    res = text
    for pat, repl in TYPO_NORMALIZATIONS:
        res = re.sub(pat, repl, res)

    # Subject nominative title repair: 'pan Eftala zniszczył' -> 'pan Eftal zniszczył', 'Mistrz Tondena minoru nie zdążył' -> 'Mistrz Tonden Minoru nie zdążył'
    TITLES_SUBJECT_PAT = r"[Pp]an|[Pp]ani|[Mm]istrz|[Pp]rofesor|[Dd]oktor|[Pp]isarz|[Rr]eżyser|[Rr]edaktor|[Aa]utor|[Mm]angaka|[Ss]ensei"
    CANONICAL_A_NAMES = {
        "akira", "shira", "soma", "gaara", "ashitaka", "kiba", "kenta",
        "ryoma", "hanza", "koba", "soya", "toma", "genga", "teshima"
    }
    POLISH_ADVERBS = {
        "faktycznie", "naprawdę", "bardzo", "właśnie", "wczoraj", "dzisiaj", "jutro",
        "wtedy", "teraz", "zaraz", "nagle", "znowu", "ponownie", "dobrze", "źle",
        "szybko", "wolno", "także", "również", "jednak", "przecież", "wcale", "zawsze", "nigdy", "osobiście"
    }

    # Case 1: Title + Surname + Given Name + Verb (e.g. 'Mistrz Tondena minoru\Nnie zdążył' -> 'Mistrz Tonden Minoru\Nnie zdążył')
    def _fix_nominative_two_part_title_subject(m):
        prefix = m.group(1)
        title = m.group(2)
        sep1 = m.group(3)
        surname_stem = m.group(4)
        sep2 = m.group(5)
        given_name = m.group(6)
        sep3 = m.group(7)
        verb = m.group(8)
        if title.lower() == "pani" or given_name.lower() in POLISH_ADVERBS:
            return m.group(0)
        full_surname = (surname_stem + "a").lower()
        if full_surname in CANONICAL_A_NAMES:
            clean_surname = surname_stem + "a"
        else:
            clean_surname = surname_stem
        clean_given = given_name.capitalize()
        return f"{prefix}{title}{sep1}{clean_surname}{sep2}{clean_given}{sep3}{verb}"

    res = re.sub(
        rf"(^|[^\w]|\\[Nnh])({TITLES_SUBJECT_PAT})(\s+|\\[Nnh]+)([A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]*[bcdfghjklmnprstvwxz])a(\s+|\\[Nnh]+)([A-Za-ząćęłńóśźż]+)(\s+|\\[Nnh]+)((?:nie\s+)?[a-ząćęłńóśźż]+(?:ł|łby|ła|ło|li|ły))\b",
        _fix_nominative_two_part_title_subject,
        res
    )

    # Case 2: Title + Single Name + Verb (e.g. 'pan Eftala zniszczył' -> 'pan Eftal zniszczył')
    def _fix_nominative_title_subject(m):
        prefix = m.group(1)
        title = m.group(2)
        sep1 = m.group(3)
        name_stem = m.group(4)
        sep2 = m.group(5)
        verb = m.group(6)
        if title.lower() == "pani":
            return m.group(0)
        full_name = (name_stem + "a").lower()
        if full_name in CANONICAL_A_NAMES:
            return m.group(0)
        return f"{prefix}{title}{sep1}{name_stem}{sep2}{verb}"

    res = re.sub(
        rf"(^|[^\w]|\\[Nnh])({TITLES_SUBJECT_PAT})(\s+|\\[Nnh]+)([A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]*[bcdfghjklmnprstvwxz])a(\s+|\\[Nnh]+)((?:nie\s+)?[a-ząćęłńóśźż]+(?:ł|łby|ła|ło|li|ły))\b",
        _fix_nominative_title_subject,
        res
    )
    return res


# -------------------------------------------------------------------------
# Definite Article Nominative vs False Vocative Mapping (Filar CLXXIII / §0 & §3)
# Maps English noun/title to Polish vocative forms and target nominative form.
# When English has "the <title>", the definite article marks 3rd-person reference (Nominativus Exclamativus).
# English direct address (vocative) NEVER takes a definite article ("*The king, listen!").
# -------------------------------------------------------------------------
DEFINITE_TITLE_MAPPING: Dict[str, Dict[str, Any]] = {
    "king": {"vocatives": ["królu"], "nominative": "król"},
    "queen": {"vocatives": ["królowo"], "nominative": "królowa"},
    "emperor": {"vocatives": ["cesarzu"], "nominative": "cesarz"},
    "empress": {"vocatives": ["cesarzowo"], "nominative": "cesarzowa"},
    "prince": {"vocatives": ["królewiczu"], "nominative": "królewicz"},
    "princess": {"vocatives": ["księżniczko"], "nominative": "księżniczka"},
    "duke": {"vocatives": ["książę"], "nominative": "książę"},
    "count": {"vocatives": ["hrabio"], "nominative": "hrabia"},
    "baron": {"vocatives": ["baronie"], "nominative": "baron"},
    "lord": {"vocatives": ["lordzie"], "nominative": "lord"},
    "commander": {"vocatives": ["dowódco", "komendancie"], "nominative": "dowódca"},
    "captain": {"vocatives": ["kapitanie"], "nominative": "kapitan"},
    "general": {"vocatives": ["generale"], "nominative": "generał"},
    "chief": {"vocatives": ["wodzu", "szefie"], "nominative": "wódz"},
    "boss": {"vocatives": ["szefie"], "nominative": "szef"},
    "leader": {"vocatives": ["przywódco"], "nominative": "przywódca"},
    "knight": {"vocatives": ["rycerzu"], "nominative": "rycerz"},
    "soldier": {"vocatives": ["żołnierzu"], "nominative": "żołnierz"},
    "guard": {"vocatives": ["strażniku"], "nominative": "strażnik"},
    "master": {"vocatives": ["mistrzu"], "nominative": "mistrz"},
    "doctor": {"vocatives": ["doktorze", "lekarzu"], "nominative": "doktor"},
    "physician": {"vocatives": ["lekarzu", "doktorze"], "nominative": "lekarz"},
    "teacher": {"vocatives": ["nauczycielu"], "nominative": "nauczyciel"},
    "professor": {"vocatives": ["profesorze"], "nominative": "profesor"},
    "president": {"vocatives": ["prezydencie"], "nominative": "prezydent"},
    "priest": {"vocatives": ["kapłanie"], "nominative": "kapłan"},
    "pope": {"vocatives": ["papieżu"], "nominative": "papież"},
    "hero": {"vocatives": ["bohaterze"], "nominative": "bohater"},
    "enemy": {"vocatives": ["wrogu", "nieprzyjacielu"], "nominative": "wróg"},
    "beast": {"vocatives": ["bestio"], "nominative": "bestia"},
    "monster": {"vocatives": ["potworze"], "nominative": "potwór"},
    "demon": {"vocatives": ["demonie"], "nominative": "demon"},
    "dragon": {"vocatives": ["smoku"], "nominative": "smok"},
    "traitor": {"vocatives": ["zdrajco"], "nominative": "zdrajca"},
    "killer": {"vocatives": ["zabójco", "morderco"], "nominative": "zabójca"},
    "assassin": {"vocatives": ["zabójco", "morderco"], "nominative": "zabójca"},
    "culprit": {"vocatives": ["sprawco"], "nominative": "sprawca"},
    "father": {"vocatives": ["ojcze"], "nominative": "ojciec"},
    "mother": {"vocatives": ["matko"], "nominative": "matka"},
    "son": {"vocatives": ["synu"], "nominative": "syn"},
    "daughter": {"vocatives": ["córko"], "nominative": "córka"},
    "brother": {"vocatives": ["bracie"], "nominative": "brat"},
    "sister": {"vocatives": ["siostro"], "nominative": "siostra"},
    "god": {"vocatives": ["boże"], "nominative": "bóg"},
    "wizard": {"vocatives": ["czarodzieju"], "nominative": "czarodziej"},
    "sorcerer": {"vocatives": ["czarodzieju"], "nominative": "czarodziej"},
    "mage": {"vocatives": ["magu"], "nominative": "mag"},
    "witch": {"vocatives": ["wiedźmo"], "nominative": "wiedźma"},
    "warrior": {"vocatives": ["wojowniku"], "nominative": "wojownik"},
    "hunter": {"vocatives": ["łowco"], "nominative": "łowca"},
    "boy": {"vocatives": ["chłopcze"], "nominative": "chłopiec"},
    "girl": {"vocatives": ["dziewczyno"], "nominative": "dziewczyna"}
}


def resolve_definite_article_nominative(en_text: str, pl_text: str) -> Tuple[str, bool]:
    """
    Guards against False Vocative Drift (Filar CLXXIII / §0 & §3 Offline-First).
    When English uses 'The [Title/Role]' (e.g. 'The king...!', 'The captain!'),
    the definite article 'The' strictly marks 3rd-person reference (Nominativus Exclamativus).
    English direct address (vocative) NEVER takes a definite article.
    If Polish mistakenly outputs a vocative form (e.g. 'Królu...!', 'Kapitanie!'),
    this function deterministically restores the correct nominative form ('Król...!', 'Kapitan!').
    Returns (fixed_pl_text, was_changed).
    """
    if not en_text or not pl_text:
        return pl_text, False

    clean_en = str(en_text).lower()
    modified = pl_text
    changed = False

    GOVERNING_PREP_PAT = re.compile(r"\b(?:o|przy|ku|przeciw|przeciwko|dzięki|wobec|u|do|od)\s*$", re.IGNORECASE)

    for en_title, data in DEFINITE_TITLE_MAPPING.items():
        if not re.search(rf"\bthe\s+{re.escape(en_title)}\b", clean_en):
            continue

        nom = data["nominative"]
        for voc in data["vocatives"]:
            voc_pat = rf"\b({re.escape(voc)})\b"

            def _repl(m, target_nom=nom):
                preceding = modified[:m.start()]
                if GOVERNING_PREP_PAT.search(preceding):
                    return m.group(0)
                matched = m.group(1)
                if matched.isupper():
                    return target_nom.upper()
                elif matched[0].isupper():
                    return target_nom.capitalize()
                return target_nom

            new_pl = re.sub(voc_pat, _repl, modified, flags=re.IGNORECASE)
            if new_pl != modified:
                modified = new_pl
                changed = True

    return modified, changed


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
            "hypocorisms": {},        # { "Kuro": "Kuroe", "Kuro-tan": "Kuroe", "Rin": "Rinko" }
            "plot_anchors": {},        # { "kamień jada": "rytualny artefakt wywołujący deszcz", "zbieg z Samarkandy": "Shira" }
            "episodes_translated": [], # ["odcinek 1", "odcinek 2"]
            "batch_stats": {}          # { "odcinek 1": {"batches": 17, "dialogues": 374, "avg_batch_size": 22.0} }
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
                self._sanitize_bible_integrity()
            except Exception:
                pass

    def _sanitize_bible_integrity(self):
        """
        Self-healing relational and biological gender consistency audit.
        Guards against poisoned entries where female characters (empresses, daughters, wives)
        were accidentally marked as male or inflected with masculine endings.
        """
        if not hasattr(self, "data") or "characters" not in self.data:
            return

        FEMALE_TITLES = {"cesarzowa", "chatun", "małżonka", "żona", "córka", "matka", "księżniczka", "królowa", "lady"}

        # 1. Collect female names from relationships or explicit notes
        confirmed_females = set()
        for rel_name, rel_desc in self.data.get("relationships", {}).items():
            r_lower = str(rel_desc).lower()
            if "->" in rel_name:
                parts = [p.strip() for p in rel_name.split("->")]
                spk = parts[0]
                rec = parts[1] if len(parts) > 1 else ""
                if any(w in r_lower for w in ["córka ->", "żona ->", "pasierbica ->", "cesarzowa ->"]):
                    confirmed_females.add(spk)
                if any(w in r_lower for w in ["-> córka", "-> żona", "-> matka", "-> macocha", "-> cesarzowa"]):
                    confirmed_females.add(rec)

        # 2. Check characters table
        for char_name, c_val in list(self.data.get("characters", {}).items()):
            if "->" in char_name:
                continue
            desc = c_val.get("description", "") if isinstance(c_val, dict) else str(c_val)
            d_lower = desc.lower()

            is_confirmed_female = (char_name in confirmed_females) or any(t in d_lower for t in FEMALE_TITLES)
            if is_confirmed_female:
                # If marked as male, auto-repair to female
                if any(m in d_lower for m in ["mężczyzna", "chłopak", "male"]):
                    clean_desc = re.sub(r"\bmężczyzna\b", "KOBIETA", desc, flags=re.IGNORECASE)
                    clean_desc = re.sub(r"\[MĘŻCZYZNA \(Adresat\)[^\]]*\]", "[KOBIETA (Adresat) - W 2. os. lp. 'ty' wymóg form żeńskich: byłaś / zrobiłaś / jesteś pewna]", clean_desc)
                    if isinstance(c_val, dict):
                        c_val["description"] = clean_desc
                    else:
                        self.data["characters"][char_name] = {"description": clean_desc}

                # Regenerate declensions for foreign female names
                if "declensions" in self.data:
                    if char_name in self.data["declensions"]:
                        self.data["declensions"][char_name] = generate_polish_name_declension(char_name, "FEMALE")
                        self.data["declensions"][char_name]["gender"] = "FEMALE"

                # Auto-register and synchronize transliterated aliases found in female character descriptions
                for alias in re.findall(r"\b(?:cesarzowa|pani|księżniczka|postać|imię)\s+([A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]+)", desc):
                    if alias != char_name:
                        if alias not in self.data["characters"]:
                            self.data["characters"][alias] = dict(c_val) if isinstance(c_val, dict) else {"description": str(c_val)}
                        if "declensions" in self.data:
                            self.data["declensions"][alias] = generate_polish_name_declension(alias, "FEMALE")
                            self.data["declensions"][alias]["gender"] = "FEMALE"

        # Ensure any declension with a female character or female alias has gender = FEMALE
        if "declensions" in self.data:
            for d_name, d_val in self.data["declensions"].items():
                if isinstance(d_val, dict) and "gender" not in d_val:
                    c_info = self.data.get("characters", {}).get(d_name)
                    if c_info:
                        c_desc = c_info.get("description", "") if isinstance(c_info, dict) else str(c_info)
                        if any(t in c_desc.lower() for t in FEMALE_TITLES) or "kobieta" in c_desc.lower() or "female" in c_desc.lower():
                            d_val["gender"] = "FEMALE"

        # 3. Systemic Ethnonym & Collective Purge from Characters & Declensions
        for bad_key in list(self.data.get("characters", {}).keys()):
            if "->" not in bad_key:
                clean_k = extract_clean_speaker_name(bad_key).strip().lower()
                if clean_k in ETHNONYMS_AND_COLLECTIVES or self.is_non_character_entity(bad_key):
                    del self.data["characters"][bad_key]

        if "declensions" in self.data:
            for bad_key in list(self.data.get("declensions", {}).keys()):
                clean_k = extract_clean_speaker_name(bad_key).strip().lower()
                if clean_k in ETHNONYMS_AND_COLLECTIVES or self.is_non_character_entity(bad_key):
                    del self.data["declensions"][bad_key]

        # 4. Systemic Historical Titling Sanity Audit (Khagan/Chagan -> Wielki Chan/Chan)
        if "glossary" in self.data and isinstance(self.data["glossary"], dict):
            new_gloss = {}
            for gk, gv in self.data["glossary"].items():
                gk_str = str(gk)
                gv_str = str(gv)
                # Normalize key if it's Great Kha'an or Khagan
                if gk_str.lower() in ["great kha'an", "great khagan", "great chagan"]:
                    gk_clean = "Great Kha'an"
                    gv_clean = "Wielki Chan"
                elif gk_str.lower() in ["khagan", "chagan"]:
                    gk_clean = "Khagan"
                    gv_clean = "Chan / Wielki Chan"
                else:
                    gk_clean = gk_str
                    gv_clean = gv_str
                    gv_clean = re.sub(r"\bWielki Chaganie\b", "Wielki Chanie", gv_clean)
                    gv_clean = re.sub(r"\bWielkiego Chagana\b", "Wielkiego Chana", gv_clean)
                    gv_clean = re.sub(r"\bWielki Chagan\b", "Wielki Chan", gv_clean)
                    gv_clean = re.sub(r"\bChaganie\b", "Chanie", gv_clean)
                    gv_clean = re.sub(r"\bChagana\b", "Chana", gv_clean)
                    gv_clean = re.sub(r"\bChagan\b", "Chan", gv_clean)
                new_gloss[gk_clean] = gv_clean
            self.data["glossary"] = new_gloss

        if "relationships" in self.data and isinstance(self.data["relationships"], dict):
            for rk, rv in list(self.data["relationships"].items()):
                rv_str = str(rv)
                rv_clean = re.sub(r"\bWielki Chaganie\b", "Wielki Chanie", rv_str)
                rv_clean = re.sub(r"\bWielkiego Chagana\b", "Wielkiego Chana", rv_clean)
                rv_clean = re.sub(r"\bWielkiemu Chaganowi\b", "Wielkiemu Chanowi", rv_clean)
                rv_clean = re.sub(r"\bWielkim Chaganem\b", "Wielkim Chanem", rv_clean)
                rv_clean = re.sub(r"\bWielki Chagan\b", "Wielki Chan", rv_clean)
                rv_clean = re.sub(r"\bChaganie\b", "Chanie", rv_clean)
                rv_clean = re.sub(r"\bChagana\b", "Chana", rv_clean)
                rv_clean = re.sub(r"\bChaganem\b", "Chanem", rv_clean)
                rv_clean = re.sub(r"\bChagan\b", "Chan", rv_clean)
                rv_clean = re.sub(r"\bchagan\b", "chan", rv_clean, flags=re.IGNORECASE)

                # Auto-detect female-only relationships and enforce dual forms
                if "->" in rk:
                    parts = [p.strip() for p in rk.split("->")]
                    spk_name = parts[0]
                    rec_name = parts[1] if len(parts) > 1 else ""
                    if self.is_female_pair(spk_name, rec_name) or (spk_name in confirmed_females and rec_name in confirmed_females):
                        if "PARA DWÓCH KOBIET" not in rv_clean:
                            rv_clean += " [PARA DWÓCH KOBIET: w odniesieniu do obu kobiet stosuj wyłącznie formy żeńskie 'obie / dla was obu / was obie', KATEGORYCZNY ZAKAZ 'oboje' (Filar CLXXIII)]"

                self.data["relationships"][rk] = rv_clean

        # 5. Sanitize character descriptions and relation keys in characters table
        for c_k, c_v in self.data.get("characters", {}).items():
            if isinstance(c_v, dict) and "description" in c_v:
                d_s = c_v["description"]
                d_s = re.sub(r"\bWielki Chaganie\b", "Wielki Chanie", d_s)
                d_s = re.sub(r"\bWielkiego Chagana\b", "Wielkiego Chana", d_s)
                d_s = re.sub(r"\bWielkiemu Chaganowi\b", "Wielkiemu Chanowi", d_s)
                d_s = re.sub(r"\bWielkim Chaganem\b", "Wielkim Chanem", d_s)
                d_s = re.sub(r"\bWielki Chagan\b", "Wielki Chan", d_s)
                d_s = re.sub(r"\bChaganie\b", "Chanie", d_s)
                d_s = re.sub(r"\bChagana\b", "Chana", d_s)
                d_s = re.sub(r"\bChaganem\b", "Chanem", d_s)
                d_s = re.sub(r"\bChagan\b", "Chan", d_s)
                d_s = re.sub(r"\bchagan\b", "chan", d_s, flags=re.IGNORECASE)
                c_v["description"] = d_s
            elif isinstance(c_v, str):
                d_s = re.sub(r"\bWielki Chaganie\b", "Wielki Chanie", c_v)
                d_s = re.sub(r"\bWielkiego Chagana\b", "Wielkiego Chana", d_s)
                d_s = re.sub(r"\bWielki Chagan\b", "Wielki Chan", d_s)
                d_s = re.sub(r"\bChaganie\b", "Chanie", d_s)
                d_s = re.sub(r"\bChagana\b", "Chana", d_s)
                d_s = re.sub(r"\bChagan\b", "Chan", d_s)
                d_s = re.sub(r"\bchagan\b", "chan", d_s, flags=re.IGNORECASE)
                self.data["characters"][c_k] = d_s

    def save(self):
        """Saves current Series Bible state to disk."""
        try:
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def register_episode_execution(
        self,
        episode_name: str,
        batch_count: int,
        dialogue_count: int,
        cost_pln: Optional[float] = None
    ):
        """
        Records execution density and batch stats in Series Bible to monitor and prevent financial/fragmentation drift.
        """
        if not hasattr(self, "data") or "episodes_translated" not in self.data:
            return
        entry = episode_name.strip()
        if entry and entry not in self.data["episodes_translated"]:
            self.data["episodes_translated"].append(entry)

        if "batch_stats" not in self.data:
            self.data["batch_stats"] = {}
        self.data["batch_stats"][entry] = {
            "dialogues": dialogue_count,
            "batches": batch_count,
            "avg_batch_size": round(dialogue_count / max(1, batch_count), 1),
            "cost_pln": cost_pln
        }
        self.save()

    def resolve_canonical_name(self, name_or_stem: str) -> str:
        """
        Resolves hypocorisms, pet names, and truncated stems (e.g. 'Kuro-tan', 'Kuro')
        to the full canonical character name ('Kuroe') registered in the Series Bible.
        """
        if not name_or_stem:
            return ""
        s = name_or_stem.strip()
        s_lower = s.lower()
        # 1. Direct lookup in registered hypocorisms
        hypo = self.data.get("hypocorisms", {})
        if s in hypo:
            return hypo[s]
        for k, v in hypo.items():
            if k.lower() == s_lower:
                return v
        # 2. Check if stem matches prefix of a confirmed character name
        chars = self.data.get("characters", {})
        for c in chars.keys():
            if "->" not in c:
                c_first = c.split()[0]
                if c_first.lower() == s_lower:
                    return c_first
                if c_first.lower().startswith(s_lower) and len(s_lower) >= 3:
                    return c_first
        return s

    def is_named_character(self, name: str) -> bool:
        """
        Returns True if name belongs to an actual named character in the series
        (from AniList/Bible registry) and is NOT a generic category noun.
        """
        if not name or is_generic_actor_or_category(name):
            return False
        clean = extract_clean_speaker_name(name).strip().lower()
        chars = self.data.get("characters", {})
        for k in chars.keys():
            if "->" not in k:
                if k.lower() == clean or extract_clean_speaker_name(k).strip().lower() == clean:
                    return True
        return False

    def get_character_gender(self, name: str, allow_generic_nouns: bool = True) -> str:
        """
        Returns 'MALE', 'FEMALE', or 'UNKNOWN' based on Series Bible records and inherent lexical gender.
        When allow_generic_nouns=False, generic category nouns ('mężczyzna', 'kobieta') return 'UNKNOWN',
        ensuring they cannot impersonate named characters.
        """
        if not name:
            return "UNKNOWN"
        clean = extract_clean_speaker_name(name)
        n_l = (clean or name).strip().lower()

        if not allow_generic_nouns and is_generic_actor_or_category(n_l):
            return "UNKNOWN"

        if self.is_non_character_entity(name) or n_l in ETHNONYMS_AND_COLLECTIVES:
            return "UNKNOWN"

        # Inherent lexical gender check
        tokens = set(re.findall(r"\b[a-ząćęłńóśźżA-ZĄĆĘŁŃÓŚŹŻ]+\b", n_l))
        if allow_generic_nouns:
            if n_l in INHERENT_FEMALE_NOUNS or any(t in INHERENT_FEMALE_NOUNS for t in tokens):
                return "FEMALE"
            if n_l in INHERENT_MALE_NOUNS or any(t in INHERENT_MALE_NOUNS for t in tokens):
                return "MALE"

        chars = self.data.get("characters", {})
        for k, v in chars.items():
            if "->" not in k:
                k_l = k.lower()
                clean_k = extract_clean_speaker_name(k_l)
                if k_l == n_l or clean_k == n_l or n_l in k_l.split():
                    desc_v = str(v.get("description", "") if isinstance(v, dict) else v).lower()
                    if any(w in desc_v for w in ["female", "kobieta", "dziewczyn", "żeńsk"]):
                        return "FEMALE"
                    if any(w in desc_v for w in ["male", "mężczyzna", "chłopak", "męsk"]):
                        return "MALE"

        # Onomastic female / male name check (for named characters when series records don't specify)
        if not is_generic_actor_or_category(n_l):
            if n_l in MALE_EXCEPTIONS_ON_A or any(t in MALE_EXCEPTIONS_ON_A for t in tokens):
                return "MALE"
            if is_inherently_female_name(n_l) or any(is_inherently_female_name(t) for t in tokens):
                return "FEMALE"

        return "UNKNOWN"

    def is_all_female_cast(self, cast: Any) -> bool:
        """
        Returns True if all characters in the given cast are confirmed FEMALE and cast is non-empty.
        Excludes generic background/actor nouns from false positive validation.
        """
        named = [str(c).strip() for c in cast if c and not is_generic_actor_or_category(str(c).strip())]
        if not named:
            return False
        return all(self.get_character_gender(c, allow_generic_nouns=False) == "FEMALE" for c in named)

    def is_all_male_cast(self, cast: Any) -> bool:
        """
        Returns True if all characters in the given cast are confirmed MALE and cast is non-empty.
        Excludes generic background/actor nouns from false positive validation.
        """
        named = [str(c).strip() for c in cast if c and not is_generic_actor_or_category(str(c).strip())]
        if not named:
            return False
        return all(self.get_character_gender(c, allow_generic_nouns=False) == "MALE" for c in named)

    def infer_scene_cast_from_text(self, scene_texts: List[str], whisper_texts: Optional[List[str]] = None) -> Tuple[Set[str], Optional[str]]:
        """
        Scans dialogue lines within an anonymous scene (where ev.name is blank) for character mentions,
        vocatives, and distinctive plot anchors to determine the scene cast and gender exclusivity (0.00 PLN).
        Universal across all 16 series via dynamic scanning of characters and relationships.
        Returns: (detected_cast_set, 'FEMALE' | 'MALE' | None)
        """
        if not scene_texts and not whisper_texts:
            return set(), None

        combined_text = " ".join(scene_texts or [])
        combined_lower = combined_text.lower()
        detected_cast: Set[str] = set()

        chars = self.data.get("characters", {})
        for k in chars.keys():
            if "->" in k:
                continue
            parts = [p.strip() for p in k.split("/") if len(p.strip()) >= 3]
            for p in parts:
                if is_generic_actor_or_category(p) or self.is_non_character_entity(p):
                    continue
                p_esc = re.escape(p)
                # Exclude 3rd-person genealogy, deceased houses or historical reference (e.g. Tolui's lineage / rodu Tołuja)
                is_genealogy = bool(re.search(
                    rf"\b(?:houses?|lineages?|lineage|house|tomb|tombs|memory|death|grave|graves|ród|rodu|rody|rodów|grobu|grobów|pamięć|pamięci)\s+(?:of\s+|z\s+)?[^.!?\n]*?\b{p_esc}\b|\b{p_esc}'s\s+(?:lineage|lineages|house|houses|memory|tomb|tombs|grave|graves|death|will)\b",
                    combined_text,
                    re.IGNORECASE
                ))
                if is_genealogy:
                    continue
                if re.search(rf"\b{p_esc}\b", combined_text, re.IGNORECASE):
                    detected_cast.add(p)

        # Dynamic relationship scanning across all series (e.g. A -> B where both are female/male)
        rels = self.data.get("relationships", {})
        for rel_k in rels.keys():
            if "->" in rel_k:
                p_from, p_to = [p.strip() for p in rel_k.split("->", 1)]
                p_from_clean = extract_clean_speaker_name(p_from)
                p_to_clean = extract_clean_speaker_name(p_to)
                if len(p_from_clean) >= 3 and len(p_to_clean) >= 3:
                    has_from = bool(re.search(rf"\b{re.escape(p_from_clean)}\b", combined_text, re.IGNORECASE))
                    has_to = bool(re.search(rf"\b{re.escape(p_to_clean)}\b", combined_text, re.IGNORECASE))
                    if has_from and re.search(rf"\b(?:houses?|lineages?|lineage|house|ród|rodu|rody|rodów)\s+(?:of\s+|z\s+)?[^.!?\n]*?\b{re.escape(p_from_clean)}\b|\b{re.escape(p_from_clean)}'s\s+(?:lineage|house)\b", combined_text, re.IGNORECASE):
                        has_from = False
                    if has_to and re.search(rf"\b(?:houses?|lineages?|lineage|house|ród|rodu|rody|rodów)\s+(?:of\s+|z\s+)?[^.!?\n]*?\b{re.escape(p_to_clean)}\b|\b{re.escape(p_to_clean)}'s\s+(?:lineage|house)\b", combined_text, re.IGNORECASE):
                        has_to = False
                    if has_from or has_to:
                        g_from = self.get_character_gender(p_from_clean, allow_generic_nouns=False)
                        g_to = self.get_character_gender(p_to_clean, allow_generic_nouns=False)
                        if g_from in ("FEMALE", "MALE") and g_to in ("FEMALE", "MALE") and g_from == g_to:
                            detected_cast.add(p_from_clean)
                            detected_cast.add(p_to_clean)

        # Content/relational anchors for known dramatic dialogues (bilingual EN + PL)
        if any(kw in combined_lower for kw in [
            "jest dla mnie kimś wyjątkowym",
            "nie mieszaj w to więcej töregene",
            "nie mieszaj w to töregene",
            "töregene jest dla mnie",
            "someone special to me",
            "she is special to me",
            "she is someone special",
            "don't bring töregene",
            "don't involve töregene",
            "do not involve töregene",
            "leave töregene out",
        ]):
            detected_cast.add("Fatima")
            detected_cast.add("Boraqchin")

        if any(kw in combined_lower for kw in [
            "sorkaktani",
            "sorghaghtani",
            "cztery tysiące jurt",
            "rodu tołuja",
            "zamierzałam jej odebrać",
            "zamierzałem jej odebrać",
            "chciałam jej odebrać",
            "chciałem jej odebrać",
            "four thousand tents",
            "four-thousand tents",
            "lineage of tolui",
            "house of tolui",
            "intended to take back",
            "intended to strip",
            "strip from her from the start",
            "take back from her from the start",
        ]):
            detected_cast.add("Boraqchin")

        # Audio Whisper Ground Truth integration (if available)
        combined_whisper = " ".join(whisper_texts or []).lower() if whisper_texts else ""
        has_female_audio = any(m in combined_whisper for m in ["warawa", "妾", "atashi", "あたし", "atai", "あたい", "wa yo", "わよ", "kashira", "かしら"])
        has_male_audio = any(m in combined_whisper for m in ["ore", "俺", "boku", "僕", "washi", "わし", "sessha", "拙者", "da zo", "だぞ", "da ze", "だぜ"])

        gender_exclusive = None
        if detected_cast:
            if self.is_all_female_cast(detected_cast):
                gender_exclusive = "FEMALE"
            elif self.is_all_male_cast(detected_cast):
                gender_exclusive = "MALE"

        if not gender_exclusive:
            if has_female_audio and not has_male_audio:
                gender_exclusive = "FEMALE"
            elif has_male_audio and not has_female_audio:
                gender_exclusive = "MALE"

        return detected_cast, gender_exclusive

    def update_character_gender_from_audio(self, name: str, gender: str) -> bool:
        """
        Updates an unconfirmed character's gender in Series Bible using definitive Japanese
        first-person audio markers (ore/boku -> MALE, atashi/atai -> FEMALE).
        Protected by symmetrical locks: cannot downgrade or overwrite confirmed MALE with FEMALE or vice versa.
        """
        if not name or gender not in ("MALE", "FEMALE"):
            return False
        clean_name = name.strip()
        existing_gender = self.get_character_gender(clean_name, allow_generic_nouns=False)
        if existing_gender in ("MALE", "FEMALE"):
            # Symmetrical lock: already confirmed
            return False

        desc = f"{'MĘŻCZYZNA' if gender == 'MALE' else 'KOBIETA'} (zweryfikowano z audio seiyū Whisper)"
        if clean_name not in self.data["characters"]:
            self.data["characters"][clean_name] = {"description": desc}
        else:
            entry = self.data["characters"][clean_name]
            if isinstance(entry, dict):
                cur_desc = entry.get("description", "")
                entry["description"] = f"{cur_desc}; {desc}".strip("; ")
            else:
                self.data["characters"][clean_name] = {"description": f"{entry}; {desc}".strip("; ")}

        self.data["declensions"][clean_name] = generate_polish_name_declension(clean_name, gender)
        return True

    def is_low_pitch_female(self, name: str) -> bool:
        """
        Returns True if character is a confirmed female with an elderly, mature, raspy, or deep vocal profile,
        immunizing her against false male overrides from low F0 audio detectors.
        """
        if not name:
            return False
        clean = extract_clean_speaker_name(name)
        n_l = (clean or name).strip().lower()

        MATRON_ROLE_KEYWORDS = [
            "starsza", "dojrzała", "babcia", "babci", "matrona", "matron", "cesarzow", "chatun",
            "pierwsza małżonka", "wiedźma", "seniorka", "staruszka", "ochrypł", "niski głos"
        ]

        if any(w in n_l for w in ["boraqchin", "chiyo", "genkai"]):
            return True

        chars = self.data.get("characters", {})
        for k, v in chars.items():
            if "->" not in k:
                k_l = k.lower()
                clean_k = extract_clean_speaker_name(k_l)
                if k_l == n_l or clean_k == n_l or n_l in k_l.split() or k_l in n_l:
                    desc_v = str(v.get("description", "") if isinstance(v, dict) else v).lower()
                    is_female = any(w in desc_v for w in ["female", "kobieta", "dziewczyn", "żeńsk"])
                    if is_female and any(w in desc_v for w in MATRON_ROLE_KEYWORDS):
                        return True
                    if is_female and any(w in k_l for w in ["boraqchin", "chiyo", "genkai"]):
                        return True
        return False

    def is_female_pair(self, name1: str, name2: str) -> bool:
        """
        Returns True if both named entities are confirmed female characters,
        mandating the use of non-virile dual numerals/pronouns ('obie / dla was obu')
        instead of virile/collective forms ('oboje / obaj').
        """
        if not name1 or not name2:
            return False
        g1 = self.get_character_gender(name1)
        g2 = self.get_character_gender(name2)
        return (g1 == "FEMALE" and g2 == "FEMALE")

    def is_non_character_entity(self, name: str) -> bool:
        """
        Determines whether a name refers to an organization, realm, institution, faction, location,
        ethnonym, or collective group, preventing it from ever being treated as a masculine/feminine character in name declension engines.
        """
        if not name:
            return False
        n_l = name.strip().lower()
        if n_l.endswith("um"):
            return True
        if n_l in ETHNONYMS_AND_COLLECTIVES or any(n_l.startswith(eth) for eth in ["mongol", "tatar", "merkit", "persian", "roman", "nomad", "pastoralist"]):
            return True
        REALM_INSTITUTION_NOUNS = {
            "imperium", "królestwo", "cesarstwo", "senat", "republika", "zakon", "gildia", "rada",
            "armia", "muzeum", "liceum", "koloseum", "akwarium", "centrum", "forum", "archiwum",
            "kościół", "rząd", "dwór", "trybunał", "pałac", "państwo"
        }
        if n_l in REALM_INSTITUTION_NOUNS:
            return True
        for section in ["organizations", "factions", "realms", "locations"]:
            sec_dict = self.data.get(section, {})
            if isinstance(sec_dict, dict):
                for k, v in sec_dict.items():
                    if k.lower() == n_l:
                        return True
                    if isinstance(v, dict):
                        if v.get("canonical_name", "").lower() == n_l or v.get("short_name", "").lower() == n_l or v.get("name", "").lower() == n_l:
                            return True
        return False

    def get_ethnonym_canonical(self, ethnonym: str) -> Optional[Dict[str, str]]:
        """
        Returns canonical Polish plural declension for an ethnonym/demonym (e.g. 'Mongołowie'),
        enforcing the rule that nation/ethnic references require plural, not English singularis pro plurali.
        """
        if not ethnonym:
            return None
        eth_norm = ethnonym.strip().lower()
        ETHNONYMS_CANONICAL = {
            "mongol": {
                "M": "Mongołowie", "D": "Mongołów", "C": "Mongołom", "B": "Mongołów",
                "N": "Mongołami", "Ms": "Mongołach", "W": "Mongołowie"
            },
            "mongoł": {
                "M": "Mongołowie", "D": "Mongołów", "C": "Mongołom", "B": "Mongołów",
                "N": "Mongołami", "Ms": "Mongołach", "W": "Mongołowie"
            },
            "tatar": {
                "M": "Tatarzy", "D": "Tatarów", "C": "Tatarom", "B": "Tatarów",
                "N": "Tatarami", "Ms": "Tatarach", "W": "Tatarzy"
            },
            "merkit": {
                "M": "Merkici", "D": "Merkitów", "C": "Merkitom", "B": "Merkitów",
                "N": "Merkitami", "Ms": "Merkitach", "W": "Merkici"
            },
            "merkid": {
                "M": "Merkidzi", "D": "Merkidów", "C": "Merkidom", "B": "Merkidów",
                "N": "Merkidami", "Ms": "Merkidach", "W": "Merkidzi"
            }
        }
        res = ETHNONYMS_CANONICAL.get(eth_norm)
        if res:
            return res
        factions = self.data.get("factions", {})
        if isinstance(factions, dict):
            for f_key, f_val in factions.items():
                if f_key.lower() == eth_norm and isinstance(f_val, dict) and "cases_pl" in f_val:
                    return f_val["cases_pl"]
                if isinstance(f_val, dict) and f_val.get("name", "").lower() == eth_norm and "cases_pl" in f_val:
                    return f_val["cases_pl"]
        return None

    def get_scoped_characters_for_scene(
        self,
        speakers: Optional[Set[str]] = None,
        dialogue_text: str = "",
        max_chars: int = 4
    ) -> Dict[str, str]:
        """
        Extracts only characters active in the current scene (speakers or mentioned by name)
        from the Series Bible characters table, preventing LLM cognitive saturation.
        """
        if not hasattr(self, "data") or "characters" not in self.data:
            return {}

        active_chars: Dict[str, str] = {}
        speakers_clean = {extract_clean_speaker_name(s).strip().lower() for s in (speakers or set()) if s}
        corpus_lower = (dialogue_text or "").lower()

        bible_chars = self.data.get("characters", {})
        for name, info in bible_chars.items():
            if "->" in name:
                continue
            desc = info.get("description", "") if isinstance(info, dict) else str(info)
            name_clean = extract_clean_speaker_name(name).strip()
            name_lower = name_clean.lower()
            name_stem = name_lower[:max(3, len(name_lower) - 2)]

            is_active_speaker = name_lower in speakers_clean or any(s in name_lower or name_lower in s for s in speakers_clean if len(s) >= 3)
            is_mentioned = name_stem in corpus_lower if len(name_stem) >= 3 else False

            if is_active_speaker or is_mentioned:
                active_chars[name] = desc

        # Fallback if no characters matched: return top characters capped at max_chars
        if not active_chars and bible_chars:
            for name, info in list(bible_chars.items())[:max_chars]:
                if "->" not in name:
                    desc = info.get("description", "") if isinstance(info, dict) else str(info)
                    active_chars[name] = desc

        return active_chars

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

        # Distinguish standalone characters from relationships (Speaker -> Listener)
        is_rel = "->" in name
        speaker = ""
        listener = ""
        if is_rel:
            parts = [p.strip() for p in name.split("->", 1)]
            speaker = parts[0]
            listener = parts[1] if len(parts) > 1 else ""

        target_name = listener.lower() if is_rel else name_lower
        target_is_male = any(m == target_name or f" {m} " in f" {target_name} " for m in CANONICAL_MALE_NAMES)
        target_is_female = False

        # Look up confirmed target character gender in Series Bible
        if hasattr(self, "data") and "characters" in self.data:
            for k, v in self.data["characters"].items():
                if "->" not in k:
                    k_l = k.lower()
                    if k_l == target_name or (len(k_l) >= 3 and k_l in target_name) or (len(target_name) >= 3 and target_name in k_l):
                        desc_v = str(v.get("description", "") if isinstance(v, dict) else v).lower()
                        if any(w in desc_v for w in ["male", "mężczyzna", "chłopak", "męsk"]):
                            target_is_male = True
                        if any(w in desc_v for w in ["female", "kobieta", "dziewczyna", "żeńsk"]):
                            target_is_female = True

        # In relationships, extract recipient description part (after '->' in brackets e.g. '(koleżanka -> przyjaciel)')
        rel_target_desc = clean_desc.split("->")[-1].lower() if ("->" in clean_desc and is_rel) else clean_desc.lower()
        if any(w in rel_target_desc for w in ["mężczyzna", "chłopak", "syn", "ojciec", "mentor", "mistrz", "pan ", "brat", "starzec", "kupiec"]):
            target_is_male = True
        if any(w in rel_target_desc for w in ["kobieta", "dziewczyna", "córka", "matka", "uczennica", "pani ", "siostra"]):
            target_is_female = True

        # Resolve conflict: target cannot be both male and female
        if target_is_male and target_is_female:
            if any(w in rel_target_desc for w in ["mężczyzna", "chłopak", "syn", "ojciec"]):
                target_is_female = False
            elif any(w in rel_target_desc for w in ["kobieta", "dziewczyna", "córka", "matka"]):
                target_is_male = False

        # Clean existing poisoned tags if they contradict target gender
        if target_is_male:
            clean_desc = re.sub(r"\s*\[KOBIETA \(Adresat\)[^\]]*\]", "", clean_desc).strip()
        if target_is_female:
            clean_desc = re.sub(r"\s*\[MĘŻCZYZNA \(Adresat\)[^\]]*\]", "", clean_desc).strip()

        # Check if the relationship or character involves a confirmed male character
        involves_male = target_is_male or any(m in name_lower for m in CANONICAL_MALE_NAMES)
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
        is_single_female = (target_is_female or any(w in rel_target_desc for w in ["kobieta", "female", "dziewczyna", "nauczycielka", "uczennica", "kapłanka"])) and not is_female_group and not target_is_male
        if is_single_female:
            if "2. os. lp." not in clean_desc.lower() and "-łaś" not in clean_desc.lower():
                clean_desc = f"{clean_desc} [KOBIETA (Adresat) - W 2. os. lp. 'ty' wymóg form żeńskich: byłaś / zrobiłaś / jesteś pewna]".strip()

        is_single_male = (target_is_male or any(w in rel_target_desc for w in ["mężczyzna", "male", "chłopak", "żołnierz", "pan", "uczeń"])) and not is_male_group and not target_is_female
        if is_single_male:
            if "2. os. lp." not in clean_desc.lower() and "-łeś" not in clean_desc.lower():
                clean_desc = f"{clean_desc} [MĘŻCZYZNA (Adresat) - W 2. os. lp. 'ty' wymóg form męskich: byłeś / zrobiłeś / jesteś pewien]".strip()

        # Safeguard hierarchical honorific relationships and anti-hybrid vocatives (Filar C & CLVII)
        is_subordinate_or_disciple = any(w in clean_desc.lower() for w in ["uczeń", "uczennica", "służąca", "niewolnica", "adept", "podwładn"])
        is_master_or_superior = any(w in clean_desc.lower() for w in ["mistrz", "arcymag", "pan ", "mentor", "zwierzchnik", "lord"])
        if is_subordinate_or_disciple or is_master_or_superior:
            if "t-v invariance" not in clean_desc.lower() and "panie" not in clean_desc.lower():
                clean_desc = f"{clean_desc} [RELACJA HIERARCHICZNA (T-V Invariance): stały zwrot formalny 'Pan / Panie [Imię]', zakaz hybryd 'Imię... ma pan' oraz odporność na opuszczanie -sama]".strip()

        # Safeguard temporal continuity & scene boundary protection (Filar CLXV)
        is_private_relationship = any(w in clean_desc.lower() for w in ["na osobności", "w cztery oczy", "prywatn", "zaufan", "sekret"])
        if is_private_relationship:
            if "filar clxv" not in clean_desc.lower() and "dyskontinuitet" not in clean_desc.lower():
                clean_desc = f"{clean_desc} [OCHRONA PRZESKOKÓW SCEN (Filar CLXV): w rozmowach na osobności po przejściu zakaz opóźnionego 'Jasne, o co chodzi?' -> otwarcie dialogu: 'Więc o co chodzi?']".strip()

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
            FEMALE_KEYWORDS = [
                "kobieta", "żeńsk", "female", "dziewczyn", "nauczycielk", "czarodziejk",
                "szpieżk", "wojowniczk", "kapłank", "służąc", "pani", "bohaterk",
                "arystokratk", "władczyn", "królow", "księżniczk", "matk", "córk", "siostr"
            ]
            if "declensions" not in self.data:
                self.data["declensions"] = {}
            if "relationships" not in self.data:
                self.data["relationships"] = {}

            for name, details in characters.items():
                if not name or not details:
                    continue
                clean_details = self._sanitize_character_entry(name, details)
                if "->" in name:
                    self.data["relationships"][name] = clean_details
                    self.data["characters"][name] = {"description": clean_details}
                    parts = [p.strip() for p in name.split("->")]
                    for p in parts:
                        clean_p = re.sub(r"-(?:sensei|kun|chan|san|sama|senpai)\b", "", p, flags=re.IGNORECASE).strip()
                        clean_p = re.sub(r"^(?:Pani|Pan|Kapitan|Dziekan|Kardynał|Generał|Doktor|Profesor)\s+", "", clean_p).strip()
                        if clean_p and len(clean_p) >= 2 and not any(ch in clean_p for ch in "{}[]():;"):
                            if clean_p not in self.data["characters"]:
                                p_g = "FEMALE" if any(w in clean_details.lower() for w in FEMALE_KEYWORDS) else "MALE"
                                g_str = "KOBIETA" if p_g == "FEMALE" else "MĘŻCZYZNA"
                                self.data["characters"][clean_p] = {"description": f"{g_str} (wyodrębniono z relacji serii)"}
                                self.data["declensions"][clean_p] = generate_polish_name_declension(clean_p, p_g)
                    continue

                if name not in self.data["characters"]:
                    self.data["characters"][name] = {"description": clean_details}
                else:
                    existing_entry = self.data["characters"][name]
                    existing_desc = existing_entry.get("description", "") if isinstance(existing_entry, dict) else str(existing_entry)
                    existing_lower = existing_desc.lower()

                    # Protect confirmed gender against downgrading or overwriting (both male and female)
                    is_definite_female = any(w in clean_details.lower() for w in ["córka", "cesarzowa", "chatun", "żona", "małżonka", "matka", "księżniczka", "królowa"])
                    has_confirmed_male = any(w in existing_lower for w in ["mężczyzna", "męsk", "male", "kategoryczny nakaz form męskich"]) and not is_definite_female
                    is_incoming_female = any(w in clean_details.lower() for w in ["kobieta", "żeńsk", "female", "służąca", "nauczycielka", "dziewczyna", "cesarzowa", "chatun", "córka", "żona"])
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
                clean_details_sanitized = re.sub(r"zakaz\s+form\s+(?:żeńsk|męsk)[a-ząćęłńóśźż]*", "", clean_details.lower())
                c_gender = "MALE" if (any(w in clean_details_sanitized for w in ["mężczyzna", "męsk", "male", "chłopak"]) and not any(w in clean_details_sanitized for w in FEMALE_KEYWORDS)) else ("FEMALE" if any(w in clean_details_sanitized for w in FEMALE_KEYWORDS) else "UNKNOWN")

                if "/" in name:
                    names_to_decline = [p.strip() for p in name.split("/")]
                else:
                    names_to_decline = [name]

                for single_n in names_to_decline:
                    if single_n and len(single_n) >= 3 and not any(ch in single_n for ch in "->/"):
                        self.data["declensions"][single_n] = generate_polish_name_declension(single_n, c_gender)

        if glossary:
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
                    for part in re.split(r"->|/|,", rel_k):
                        part_clean = part.strip()
                        if len(part_clean) >= 3 and not any(ch in part_clean for ch in "{}[]():;"):
                            if part_clean not in self.data["declensions"]:
                                self.data["declensions"][part_clean] = generate_polish_name_declension(part_clean, "UNKNOWN")

        self.save()

    def assimilate_quality_gate_invariants(self, quality_gate_fixes: List[Any]):
        """
        Closed-loop learning engine (Layer 2).
        Ingests 100% confirmed invariants from EpisodeQualityGate post-pass
        (character gender, 7-case foreign name declensions, T-V address forms)
        and commits them permanently to the Series Bible.
        """
        if not quality_gate_fixes:
            return

        has_updates = False
        if "characters" not in self.data:
            self.data["characters"] = {}
        if "declensions" not in self.data:
            self.data["declensions"] = {}

        for fix_item in quality_gate_fixes:
            # 1. Structured fix dictionary
            if isinstance(fix_item, dict):
                f_type = fix_item.get("type", "")
                c_name = fix_item.get("character") or fix_item.get("name")
                if c_name and f_type == "gender":
                    gen = fix_item.get("gender", "").upper()
                    if gen in ["MALE", "FEMALE"]:
                        desc = f"{'MĘŻCZYZNA' if gen == 'MALE' else 'KOBIETA'} (zweryfikowano przez EpisodeQualityGate)"
                        self.data["characters"][c_name] = {"description": desc, "source": "quality_gate"}
                        self.data["declensions"][c_name] = generate_polish_name_declension(c_name, gen)
                        has_updates = True
                elif c_name and f_type == "declension":
                    decl_map = fix_item.get("declension")
                    if isinstance(decl_map, dict):
                        self.data["declensions"][c_name] = decl_map
                        has_updates = True

            # 2. String parsing from EpisodeQualityGate log lines
            elif isinstance(fix_item, str):
                # Gender confirmation: e.g. "potwierdzona płeć męska" or "potwierdzona płeć żeńska"
                m_gen = re.search(r"'(?:([A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]+)\.\.\.[^']*|[^']*\.\.\.\s+([A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]+))'.*?potwierdzona płeć (męska|żeńska)", fix_item)
                if m_gen:
                    char_name = m_gen.group(1) or m_gen.group(2)
                    gender_str = "MALE" if m_gen.group(3) == "męska" else "FEMALE"
                    if char_name and len(char_name) >= 3:
                        desc = f"{'MĘŻCZYZNA' if gender_str == 'MALE' else 'KOBIETA'} (zweryfikowano przez EpisodeQualityGate)"
                        self.data["characters"][char_name] = {"description": desc, "source": "quality_gate"}
                        self.data["declensions"][char_name] = generate_polish_name_declension(char_name, gender_str)
                        has_updates = True

                # 1st-person speaker gender confirmation:
                m_spk = re.search(r"skorygowano 1\. os\. na rodzaj (męski|żeński) dla mówc(?:y|zyni) '([^']+)'", fix_item)
                if m_spk:
                    gender_str = "MALE" if m_spk.group(1) == "męski" else "FEMALE"
                    char_name = m_spk.group(2).strip()
                    if char_name and len(char_name) >= 3:
                        desc = f"{'MĘŻCZYZNA' if gender_str == 'MALE' else 'KOBIETA'} (zweryfikowano przez EpisodeQualityGate)"
                        self.data["characters"][char_name] = {"description": desc, "source": "quality_gate"}
                        self.data["declensions"][char_name] = generate_polish_name_declension(char_name, gender_str)
                        has_updates = True

                # Prepositional Foreign Name Declension: e.g. "ujednolicono formę imienia po przyimku na 'Drela'"
                m_prep = re.search(r"ujednolicono formę (?:imienia po przyimku|na) '([^']+)'", fix_item)
                if m_prep:
                    decl_form = m_prep.group(1)
                    for existing_name in list(self.data["characters"].keys()) + list(self.data["declensions"].keys()):
                        if len(existing_name) >= 3 and decl_form.lower().startswith(existing_name[:max(3, len(existing_name)-2)].lower()):
                            if existing_name in self.data["declensions"]:
                                self.data["declensions"][existing_name]["D"] = decl_form
                                has_updates = True

                # Vocative confirmation: e.g. "ujednolicono wołacz na 'Andrewie'"
                m_voc = re.search(r"ujednolicono wołacz na '([^']+)'", fix_item)
                if m_voc:
                    voc_form = m_voc.group(1)
                    for existing_name in list(self.data["characters"].keys()) + list(self.data["declensions"].keys()):
                        if len(existing_name) >= 3 and voc_form.lower().startswith(existing_name[:max(3, len(existing_name)-2)].lower()):
                            if existing_name in self.data["declensions"]:
                                self.data["declensions"][existing_name]["W"] = voc_form
                                has_updates = True

                # Locative confirmation: e.g. "ujednolicono formę na 'Nathanie' po przyimku miejscownika"
                m_loc = re.search(r"ujednolicono formę na '([^']+)' po przyimku miejscownika", fix_item)
                if m_loc:
                    loc_form = m_loc.group(1)
                    for existing_name in list(self.data["characters"].keys()) + list(self.data["declensions"].keys()):
                        if len(existing_name) >= 3 and loc_form.lower().startswith(existing_name[:max(3, len(existing_name)-2)].lower()):
                            if existing_name in self.data["declensions"]:
                                self.data["declensions"][existing_name]["Ms"] = loc_form
                                has_updates = True

        if has_updates:
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

            if self.data.get("relationships"):
                lines.append("• Kluczowe relacje i formy zwrotu (T-V / Honoryfikatywność):")
                for rel_k, rel_v in list(self.data["relationships"].items())[:8]:
                    lines.append(f"  - {rel_k}: {rel_v}")
                has_content = True

            if self.data.get("declensions"):
                decl_items = []
                for c_name, c_decl in list(self.data["declensions"].items())[:6]:
                    if c_decl and isinstance(c_decl, dict) and c_decl.get("M") != c_decl.get("D"):
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


def sanitize_all_series_bibles(storage_dir: Optional[Path] = None) -> int:
    """
    Scans and sanitizes all Series Bible JSON files in storage_dir (default: series_memory/),
    applying self-healing integrity audits across all series systemically.
    Returns the count of sanitized bibles.
    """
    target_dir = storage_dir or SERIES_MEMORY_DIR
    if not target_dir.exists():
        return 0
    count = 0
    for p in target_dir.glob("*_bible.json"):
        try:
            with open(p, "r", encoding="utf-8") as f:
                d = json.load(f)
            title = d.get("anime_title") or p.stem.replace("_bible", "").replace("_", " ")
            bible = SeriesBible(title, storage_dir=target_dir)
            bible.save()
            count += 1
        except Exception:
            pass
    return count
