# -*- coding: utf-8 -*-
"""
Series Bible & Cross-Episode Continuity Module.
Automatically accumulates knowledge, character profiles, honorific forms, and terminology
across consecutive episodes of the same anime, ensuring 100% consistency across the entire season.
"""

import os
import re
import json
import threading
import contextlib
import copy
import shutil
import unicodedata
import functools
import logging
from pathlib import Path

logger = logging.getLogger(__name__)
from typing import Dict, List, Any, Optional, Set, Tuple, Union, Literal
from collections import Counter, defaultdict
from pydantic import BaseModel, Field, ConfigDict
from enum import Enum
from metadata import normalize_ascii_diacritics, normalize_actor_tag

class EntityCategory(str, Enum):
    ANTHROPONYM = "ANTHROPONYM"
    TOPONYM = "TOPONYM"
    CHREMATONYM = "CHREMATONYM"


# Sylabiczny profil japoński i fonotaktyka końcowego -e (Filar IV / Zasada 15 AGENTS.md)
ENGLISH_CONSONANT_CLUSTERS: Tuple[str, ...] = (
    "wh", "th", "gh", "ph", "cl", "st", "ld", "br", "cr"
)

JAPANESE_OPEN_E_MORAS: Tuple[str, ...] = (
    "ke", "te", "ne", "me", "re", "se", "ze", "be", "ge", "de", "he", "pe"
)

KNOWN_SILENT_E_NAMES: Set[str] = {
    "white", "wayne", "blade", "george", "locke", "moore", "clarke", "stone", "drake",
    "chase", "cole", "bruce", "luke", "mike", "pete", "steve", "dave", "dale"
}

JAPANESE_VOWEL_E_NAMES: Set[str] = {
    "daisuke", "ryunosuke", "shusuke", "sosuke", "akane", "kaede", "sanosuke", "kotone", "sakurae"
}

def is_japanese_cv_mora_e_name(name: str) -> bool:
    """
    Detektor CV-Mora dla wygłosu -e (Filar IV / Zasada 15 AGENTS.md):
    Jeśli nazwa własna ma sylabiczny profil japoński (brak angielskich zbitek spółgłoskowych
    wh, th, gh, ph, cl, st, ld, br, cr oraz wygłos na otwartą morę
    -ke, -te, -ne, -me, -re, -se, -ze, -be, -ge, -de, -he, -pe po samogłosce lub n),
    traktuje końcowe -e jako wymawianą samogłoskę fonetyczną i blokuje wstawianie apostrofu.
    Apostrof dozwolony wyłącznie dla niemego fonetycznie -e (White'a, Wayne'a, George'a).
    """
    if not name or len(name) < 3:
        return False
    w = name.strip().lower()
    if not w.endswith("e"):
        return False
    if w in KNOWN_SILENT_E_NAMES:
        return False
    if w in JAPANESE_VOWEL_E_NAMES:
        return True

    # 1. Brak angielskich zbitek spółgłoskowych
    if any(cluster in w for cluster in ENGLISH_CONSONANT_CLUSTERS):
        return False

    # 2. Wygłos na otwartą morę (-ke, -te, -ne, -me, -re, -se, -ze, -be, -ge, -de, -he, -pe)
    matched_mora = None
    for mora in JAPANESE_OPEN_E_MORAS:
        if w.endswith(mora):
            matched_mora = mora
            break
    if not matched_mora:
        return False

    # 3. Mora po samogłosce (a, e, i, o, u) lub n
    prefix = w[:-len(matched_mora)]
    if not prefix:
        return False
    preceding_char = prefix[-1]
    if preceding_char in "aeiou" or preceding_char == "n":
        return True

    return False


def _compute_vocative(name: str, gender: str = "MALE") -> str:
    """
    Zwraca formę wołacza (W) dla podanego imienia:
    - Dla odmiennych imion męskich na (tz, c, dz, cz, sz, rz, ż, sh, ch, k, g, j, y, l): wyłącznie końcówka -u.
    - Dla japońskich imion z sylabicznym wygłosem -e (CV-mora): bez apostrofu i bez zmian.
    - W pozostałych przypadkach: Wołacz wygenerowany przez generate_polish_name_declension.
    """
    if not name:
        return ""
    clean_name = str(name).strip()
    c_lower = clean_name.lower()
    # Harmonizacja wołaczy na -tzie -> -tzu w wygłosie afrykatywnym
    if c_lower.endswith("tzie"):
        return clean_name[:-4] + ("tzu" if clean_name[-4:].islower() else "TZU")
    if is_japanese_cv_mora_e_name(clean_name):
        return clean_fake_name_apostrophes(clean_name)
    gen_func = globals().get("generate_polish_name_declension")
    if callable(gen_func):
        decl = gen_func(clean_name, gender)
        if decl and "W" in decl:
            return decl["W"]
    return clean_name


ADJECTIVAL_OBLIQUE_SUFFIXES: Tuple[str, ...] = (
    "ego", "emu", "ych", "ich", "ymi", "imi", "ą", "ym", "im"
)

def is_adjectival_oblique_token(word: str) -> bool:
    """
    Sprawdza, czy wyraz kończy się na polski sufiks przymiotnikowy w przypadkach zależnych
    (-ym, -im, -ego, -emu, -ą, -ych, -ich, -ymi, -imi).
    """
    if not word or len(word) < 3:
        return False
    w_low = word.lower()
    if w_low.endswith(("ego", "emu", "ych", "ich", "ymi", "imi", "ą")):
        return True
    if w_low.endswith("ym") and len(w_low) >= 4:
        if w_low not in ("pielgrzym", "synonim", "anonim", "pseudonim", "reżim", "rezim", "maksym"):
            return True
    if w_low.endswith("im") and len(w_low) >= 4:
        if w_low not in ("jim", "tim", "kim", "sam", "tom", "maxim", "karim", "ibrahim", "selim", "hakim", "joachim"):
            return True
    return False


def is_complex_description(name: str) -> bool:
    """
    Sprawdza, czy ciąg jest złożoną deskrypcją fabularną/zdaniową, a nie pojedynczym antroponimem bazowym:
    - obecność nawiasów, znaczników ASS, interpunkcji zdaniowej (:, ;, !, ?), cudzysłowów lub relacji (->)
    - występowanie spójników/zaimków względnych (który, która, będący, czyli, oraz, jako)
    - frazy wielowyrazowe zawierające słowa funkcyjne lub predykatywne.
    """
    if not name or not isinstance(name, str):
        return True
    s = name.strip()
    if not s:
        return True
    if any(ch in s for ch in "()[]{}<>;:!?\"”„«»\n\r"):
        return True
    if "->" in s or "/" in s:
        return True
    words = s.split()
    SYNTAGMATIC_PREPOSITIONS = {"z", "ze", "do", "od", "w", "we", "o", "pod", "na", "dla", "nad", "przed", "za"}
    if len(words) >= 4 and not all(w[0].isupper() for w in words if w and w.lower() not in SYNTAGMATIC_PREPOSITIONS):
        return True
    if any(w.lower() in ("który", "która", "które", "będący", "będąca", "czyli", "albo", "oraz", "jako", "zwany", "zwana") for w in words):
        return True
    return False


def is_valid_anthroponymic_phonotactics(name: str) -> bool:
    """
    Sprawdza, czy nazwa spełnia podstawowe kryteria fonotaktyki antroponimicznej (imion osób):
    - Nie jest etykietą techniczną audio/akustyczną (SPK_, VOICE_, AUDIO_, SFX_, AMBIENT_, BGM_, itp.)
    - Długość od 2 do 40 znaków
    - Zawiera przynajmniej jedną samogłoskę (a, e, i, o, u, y, ą, ę, ó)
    - Nie składa się z samych cyfr ani kodów technicznych
    - Nie zawiera znaków technicznych ani znaczników planszy
    """
    if not name or not isinstance(name, str):
        return False
    clean = re.sub(r"[^\w\s-]", "", name).strip()
    if len(clean) < 2 or len(clean) > 40:
        return False
    cl_low = clean.lower()
    # Reject technical audio prefixes/labels
    if any(cl_low.startswith(p) for p in ("spk", "speaker", "voice", "audio", "sfx", "ambient", "bgm", "track", "line", "crowd", "chorus", "group")):
        return False
    if re.match(r"^[a-z]{1,4}[_-]?\d+$", cl_low):
        return False
    if clean.isdigit():
        return False
    # Must contain at least one vowel
    VOWELS = set("aeiouyąęóAEIOUYĄĘÓ")
    if not any(ch in VOWELS for ch in clean):
        return False
    return True


NON_PERSONAL_PLURAL_LEXEMES: Set[str] = {
    # Polish inanimate/object plurals
    "kroki", "drzwi", "odgłosy", "szmery", "szepty", "dźwięki", "strzały", "eksplozje",
    "brawa", "oklaski", "światła", "cienie", "ruiny", "mury", "domy", "drzewa",
    "chmury", "fale", "krople", "kamienie", "miecze", "tarcze", "zbroje", "pociski",
    "statki", "pojazdy", "maszyny", "światy", "krainy", "miasta", "wsie", "góry",
    "lasy", "morza", "jeziora", "księgi", "zwoje", "artefakty", "relikwie", "klejnoty",
    "kryształy", "zaklęcia", "czary", "rytuały", "pieczęcie", "dokumenty", "listy",
    "papiery", "notatki", "napisy", "szyldy", "tablice", "plakaty", "reklamy", "tytuły",
    "głosy", "efekty", "hałasy", "stuki", "pukania",
    # English inanimate/object plurals
    "footsteps", "steps", "doors", "sounds", "noises", "whispers", "screams", "cries",
    "explosions", "gunshots", "lights", "shadows", "ruins", "walls", "houses", "trees",
    "clouds", "waves", "drops", "stones", "swords", "shields", "armors", "projectiles",
    "ships", "vehicles", "machines", "worlds", "lands", "cities", "villages", "mountains",
    "forests", "seas", "lakes", "books", "scrolls", "artifacts", "relics", "gems",
    "crystals", "spells", "rituals", "seals", "documents", "letters", "papers", "notes",
    "subtitles", "signs", "boards", "posters", "ads", "titles", "voices", "effects"
}


class CharacterRegistryDict(dict):
    """
    Słownik bytów osobowych (EntityCategory.ANTHROPONYM) z transparentnym
    fallbackiem do dedykowanej struktury relations dla relacji skierowanych (X -> Y)
    w celu zachowania 100% kompatybilności wstecznej (Zero Regression Lock Standardu 7.0 / 7.1).
    """
    def __init__(self, *args, bible_data: Optional[Dict[str, Any]] = None, **kwargs):
        super().__init__(*args, **kwargs)
        self.bible_data = bible_data

    def __getitem__(self, key: str) -> Any:
        if super().__contains__(key):
            return super().__getitem__(key)
        if isinstance(key, str) and "->" in key and self.bible_data is not None:
            rels = self.bible_data.get("relations") or self.bible_data.get("relationships")
            if rels and key in rels:
                rel_val = rels[key]
                desc = rel_val.get("description", str(rel_val)) if isinstance(rel_val, dict) else str(rel_val)
                return {"description": desc}
        raise KeyError(key)

    def get(self, key: str, default: Any = None) -> Any:
        try:
            return self[key]
        except KeyError:
            return default

    def __contains__(self, key: object) -> bool:
        if super().__contains__(key):
            return True
        if isinstance(key, str) and "->" in key and self.bible_data is not None:
            rels = self.bible_data.get("relations") or self.bible_data.get("relationships")
            if rels and key in rels:
                return True
        return False

    def __delitem__(self, key: str) -> None:
        if super().__contains__(key):
            super().__delitem__(key)
            return
        if isinstance(key, str) and "->" in key and self.bible_data is not None:
            rels = self.bible_data.get("relations")
            if rels and key in rels:
                del rels[key]
            relationships = self.bible_data.get("relationships")
            if relationships and key in relationships:
                del relationships[key]
            return
        raise KeyError(key)


def sanitize_adjectival_double_declension(form: str, base_name: Optional[str] = None) -> str:
    """
    Ochrona przed podwójną deklinacją (Standard 5.0 / 7.0 / 7.1):
    Jeśli wyraz lub człon nazwy kończy się już na polski sufiks przymiotnikowy
    w przypadkach zależnych (-ym, -im, -ego, -emu, -ą, -ych, -ich, -ymi, -imi),
    blokuje doklejanie końcówek rzeczownikowych (-em, -a, -owi, -u, -ie itp.).
    Dla form bazowych będących formami zależnymi lub złożonymi deskrypcjami
    oraz dla rzeczowników antroponimicznych na -a zachowuje pełną identyczność T(x) = x.
    """
    if not form or not isinstance(form, str):
        return form

    # 1. Sprawdzenie form złożonych lub już odmienionych - pełna ochrona T(x) = x
    f_clean = form.strip()
    if not f_clean or is_complex_description(f_clean):
        return form

    if base_name:
        b_clean = base_name.strip()
        if not b_clean:
            return form
        if is_complex_description(b_clean):
            return form
        if is_adjectival_oblique_token(b_clean):
            return b_clean
        if b_clean.lower().endswith(("ą", "ę", "ej", "ach", "ami", "om", "ego", "emu", "ych", "ich", "ymi", "imi")):
            return form

        # Ochrona przed fałszywym obcinaniem form bazowych mianownika zakończonych na -a
        # Formy fleksyjne rzeczowników na -a są w 100% poprawne
        if b_clean.lower().endswith("a") and not b_clean.lower().endswith(("ska", "cka", "dzka", "owa", "na")):
            return form

        b_words = b_clean.split()
        f_words = f_clean.split()
        if b_words and f_words and len(b_words) == len(f_words):
            sanitized_words = []
            for b_w, f_w in zip(b_words, f_words):
                if is_adjectival_oblique_token(b_w):
                    f_w = b_w
                elif b_w.lower().endswith("a") and not b_w.lower().endswith(("ska", "cka", "dzka", "owa", "na")):
                    # Pojedynczy człon antroponimu kończący się na -a jest chroniony
                    pass
                else:
                    for bad_suf in ("owi", "wi", "em", "om", "ami", "ach"):
                        if f_w.lower().endswith(bad_suf) and len(f_w) > len(bad_suf):
                            stem_cand = f_w[:-len(bad_suf)]
                            if is_adjectival_oblique_token(stem_cand):
                                f_w = stem_cand
                                break
                sanitized_words.append(f_w)
            form = " ".join(sanitized_words)

    # 2. Wykrywanie doklejonych końcówek rzeczownikowych do sufiksów przymiotnikowych w wyrazie
    def _strip_double_suf(m: re.Match) -> str:
        stem = m.group(1)
        s_low = stem.lower()
        if s_low.endswith("ym") and s_low in ("pielgrzym", "synonim", "anonim", "pseudonim", "reżim", "rezim", "maksym"):
            return m.group(0)
        if s_low.endswith("im") and s_low in ("jim", "tim", "kim", "sam", "tom", "maxim", "karim", "ibrahim", "selim", "hakim", "joachim"):
            return m.group(0)
        return stem

    pat = re.compile(
        r"\b([A-ZĄĆĘŁŃÓŚŹŻa-ząćęłńóśźż]{2,}(?:ego|emu|ych|ich|ymi|imi|(?:ow|sk|ck|dzk|zk|aln|ist|yst)(?:ym|im)))(?:owi|wi|em|om|ami|ach)\b",
        re.IGNORECASE
    )
    return pat.sub(_strip_double_suf, form)


class DeclensionParadigm(BaseModel):
    nominative: str = Field(description="Mianownik (M)")
    genitive: str = Field(description="Dopełniacz (D)")
    dative: str = Field(description="Celownik (C)")
    accusative: str = Field(description="Biernik (B)")
    instrumental: str = Field(description="Narzędnik (N)")
    locative: str = Field(description="Miejscownik (Ms)")
    vocative: str = Field(description="Wołacz (W)")

    @property
    def M(self) -> str:
        return self.nominative

    @property
    def D(self) -> str:
        return self.genitive

    @property
    def C(self) -> str:
        return self.dative

    @property
    def B(self) -> str:
        return self.accusative

    @property
    def N(self) -> str:
        return self.instrumental

    @property
    def Ms(self) -> str:
        return self.locative

    @property
    def W(self) -> str:
        return self.vocative

    def to_dict(self) -> Dict[str, str]:
        return {
            "M": self.nominative,
            "D": self.genitive,
            "C": self.dative,
            "B": self.accusative,
            "N": self.instrumental,
            "Ms": self.locative,
            "W": self.vocative
        }

    def get(self, key: str, default: Any = None) -> Any:
        mapping = {
            "M": self.nominative,
            "D": self.genitive,
            "C": self.dative,
            "B": self.accusative,
            "N": self.instrumental,
            "Ms": self.locative,
            "W": self.vocative,
            "nominative": self.nominative,
            "genitive": self.genitive,
            "dative": self.dative,
            "accusative": self.accusative,
            "instrumental": self.instrumental,
            "locative": self.locative,
            "vocative": self.vocative,
        }
        return mapping.get(key, default)

    def __getitem__(self, key: str) -> str:
        val = self.get(key)
        if val is None:
            raise KeyError(key)
        return val

    @classmethod
    def build(cls, name: str, gender: str = "UNKNOWN") -> "DeclensionParadigm":
        d = generate_polish_name_declension(name, gender=gender)
        return cls.from_dict(d, entity_category=EntityCategory.ANTHROPONYM)

    @classmethod
    def sanitize_double_declension(cls, form: str, base_name: Optional[str] = None) -> str:
        """
        Ochrona przed podwójną deklinacją (Standard 5.0):
        Jeśli wyraz lub człon nazwy kończy się już na polski sufiks przymiotnikowy
        w przypadkach zależnych (-ym, -im, -ego, -emu, -ą, -ych, -ich, -ymi, -imi),
        blokuje doklejanie końcówek rzeczownikowych (-em, -a, -owi, -u, -ie).
        """
        return sanitize_adjectival_double_declension(form, base_name=base_name)

    @classmethod
    def from_dict(
        cls,
        d: Dict[str, str],
        entity_category: Optional[EntityCategory] = None
    ) -> "DeclensionParadigm":
        base_m = d.get("M", "")
        # Identity pass-through T(x) = x for complex descriptions, non-anthroponyms, or adjectival oblique tokens
        if (
            is_complex_description(base_m)
            or is_adjectival_oblique_token(base_m)
            or (entity_category is not None and entity_category != EntityCategory.ANTHROPONYM)
            or base_m.lower().endswith(("ą", "ę", "ej", "ach", "ami", "om", "ego", "emu", "ych", "ich", "ymi", "imi"))
        ):
            return cls(
                nominative=base_m,
                genitive=d.get("D", base_m),
                dative=d.get("C", base_m),
                accusative=d.get("B", base_m),
                instrumental=d.get("N", base_m),
                locative=d.get("Ms", base_m),
                vocative=d.get("W", base_m)
            )

        clean_d = {
            k: cls.sanitize_double_declension(v, base_name=base_m)
            for k, v in d.items()
        }
        return cls(
            nominative=clean_d.get("M", ""),
            genitive=clean_d.get("D", ""),
            dative=clean_d.get("C", ""),
            accusative=clean_d.get("B", ""),
            instrumental=clean_d.get("N", ""),
            locative=clean_d.get("Ms", ""),
            vocative=clean_d.get("W", "")
        )

    @classmethod
    def create_for_name(
        cls,
        name: str,
        gender: str = "UNKNOWN",
        entity_category: Optional[EntityCategory] = None
    ) -> "DeclensionParadigm":
        """
        Tworzy 7-przypadkowy paradygmat fleksyjny.
        Operuje wyłącznie na kanonicznych formach bazowych Mianownika pojedynczych antroponimów (EntityCategory.ANTHROPONYM).
        Dla wszystkich form już odmienionych oraz złożonych deskrypcji zachowuje pełną identyczność T(x) = x.
        """
        if not name or not isinstance(name, str):
            return cls.from_dict({"M": "", "D": "", "C": "", "B": "", "N": "", "Ms": "", "W": ""})
        clean_n = name.strip()
        if (
            is_complex_description(clean_n)
            or is_adjectival_oblique_token(clean_n)
            or clean_n.lower().endswith(("ą", "ę", "ej", "ach", "ami", "om", "ego", "emu", "ych", "ich", "ymi", "imi"))
            or (entity_category is not None and entity_category != EntityCategory.ANTHROPONYM)
        ):
            return cls.from_dict({"M": clean_n, "D": clean_n, "C": clean_n, "B": clean_n, "N": clean_n, "Ms": clean_n, "W": clean_n}, entity_category=entity_category)

        gen_func = globals().get("generate_polish_name_declension")
        if callable(gen_func):
            decl = gen_func(clean_n, gender)
            if decl and "M" in decl:
                return cls.from_dict(decl, entity_category=entity_category)
        return cls.from_dict({"M": clean_n, "D": clean_n, "C": clean_n, "B": clean_n, "N": clean_n, "Ms": clean_n, "W": clean_n}, entity_category=entity_category)

    @classmethod
    def get_vocative(cls, name: Optional[str] = None, gender: str = "MALE") -> str:
        """
        Zwraca formę wołacza (W) dla podanego imienia:
        - Dla odmiennych imion męskich na (tz, c, dz, cz, sz, rz, ż, sh, ch, k, g, j, y, l): wyłącznie końcówka -u.
        - Dla japońskich imion z sylabicznym wygłosem -e (CV-mora): bez apostrofu i bez zmian.
        - W pozostałych przypadkach: Wołacz wygenerowany przez generate_polish_name_declension.
        """
        if not name:
            return ""
        return _compute_vocative(name, gender)

    def to_reference_table(self, entity_name: Optional[str] = None) -> str:
        """
        Pasywna tablica referencyjna 7 przypadków dla encji (chroni przed nominative freezing,
        nie narzuca powtarzania nazwy własnej kosztem zaimka/elipsy).
        Format: Imię(M:..., D:..., C:..., B:..., N:..., Ms:..., W:...)
        """
        lbl = entity_name or self.nominative
        return f"{lbl}(M:{self.nominative}, D:{self.genitive}, C:{self.dative}, B:{self.accusative}, N:{self.instrumental}, Ms:{self.locative}, W:{self.vocative})"


MODIFIER_PREFIX_RE: re.Pattern = re.compile(
    r"^(?:Young|Child|Kid|Little|Baby|Teen|Old|Elder|Future|Past|Adult|Masked|True|Fake|Dark|Shadow|Młody|Młoda|Mały|Mała|Stary|Stara)\s+(.+)$",
    re.IGNORECASE
)

def extract_base_canonical_name(name: str) -> str:
    """
    Wyodrębnia rdzeń kanoniczny nazwy aktora usuwając prefiksy temporalne/wiekowe/stanowe
    (Young, Child, Kid, Little, Baby, Old, Future, Past, Masked itp.).
    """
    if not name:
        return ""
    current = name.strip()
    while True:
        m = MODIFIER_PREFIX_RE.match(current)
        if m:
            current = m.group(1).strip()
        else:
            break
    return current


def resolve_possessive_relation_gender(
    name: str,
    dialogue_context: Optional[str] = None,
    is_flashback: bool = False,
    series_bible: Optional[Any] = None
) -> Tuple[str, float]:
    """
    Wyznacza płeć dla aktorów w relacjach posesywnych ([Owner]'s Son/Daughter/Kid):
    - Człony jawnie męskie (Son, Boy, Brother, Father, Husband itp.) -> MALE (confidence=1.0)
    - Człony jawnie żeńskie (Daughter, Girl, Sister, Mother, Wife itp.) -> FEMALE (confidence=1.0)
    - Człony neutralne (Kid, Child, Apprentice itp.):
      analiza koreferencji dialogowej i blokada domyślnej feminizacji w retrospekcjach (Flashback -> MALE).
    """
    if not name:
        return ("UNKNOWN", 0.0)
    raw = name.strip()
    clean = extract_clean_speaker_name(raw).strip()

    in_flashback = is_flashback or any(fb in raw.lower() for fb in ("flashback", "retrospekcj", "past"))

    rel_m = re.match(
        r"^(.+?)(?:'s|s')\s+(Kid|Child|Son|Daughter|Boy|Girl|Brother|Sister|Bro|Sis|Father|Mother|Dad|Mom|Wife|Husband|Apprentice|Student|Subordinate)$",
        clean,
        re.IGNORECASE
    )
    if not rel_m:
        return ("UNKNOWN", 0.0)

    owner = rel_m.group(1).strip()
    rel = rel_m.group(2).strip().lower()

    male_rels = {"son", "boy", "brother", "bro", "father", "dad", "husband", "syn", "brat", "ojciec", "chłopak", "chłopiec"}
    female_rels = {"daughter", "girl", "sister", "sis", "mother", "mom", "wife", "córka", "siostra", "matka", "dziewczyna", "dziewczynka"}

    if rel in male_rels:
        return ("MALE", 1.0)
    if rel in female_rels:
        return ("FEMALE", 1.0)

    # Neutral relation (Kid, Child, Apprentice itp.)
    if dialogue_context:
        ctx_l = dialogue_context.lower()
        m_hits = len(re.findall(r"\b(?:son|my boy|our boy|the boy|he|his|him|musuko|boku|ore|syn|chłopak|on|jego|mu)\b", ctx_l))
        f_hits = len(re.findall(r"\b(?:daughter|my girl|our girl|the girl|she|her|hers|musume|atashi|córka|dziewczyna|ona|jej|ją)\b", ctx_l))
        if m_hits > f_hits:
            return ("MALE", 0.95)
        if f_hits > m_hits:
            return ("FEMALE", 0.95)

    if in_flashback:
        return ("MALE", 0.85)

    if series_bible and hasattr(series_bible, "get_character_gender"):
        owner_g = series_bible.get_character_gender(owner, allow_generic_nouns=False)
        if owner_g == "MALE" and in_flashback:
            return ("MALE", 0.90)

    return ("UNKNOWN", 0.0)


class PersonaInterval(BaseModel):
    apparent_gender: str
    valid_from_ep: int
    valid_to_ep: Optional[int] = None
    public_facade: bool = True


class CharacterIdentity(BaseModel):
    canonical_id: str
    true_gender: str
    discourse_states: List[PersonaInterval] = Field(default_factory=list)
    entity_category: EntityCategory = Field(default=EntityCategory.ANTHROPONYM)
    declension_paradigm: Optional[DeclensionParadigm] = Field(default=None)
    base_canonical_id: Optional[str] = Field(default=None)

    def get_effective_gender(
        self,
        episode_index: int,
        is_private_confidant: bool = False,
        in_multi_person_scene: bool = False,
        is_monologue: bool = False
    ) -> str:
        """
        Zwraca obowiązującą płeć gramatyczną w zależności od odcinka,
        statusu monologu, obecności powiernika tajemnicy i sceny wieloosobowej.
        """
        if is_monologue:
            return self.true_gender

        if is_private_confidant and not in_multi_person_scene:
            return self.true_gender

        for interval in self.discourse_states:
            if interval.valid_from_ep <= episode_index:
                if interval.valid_to_ep is None or episode_index <= interval.valid_to_ep:
                    if interval.public_facade:
                        return interval.apparent_gender
                    return self.true_gender

        return self.true_gender

    def register_epistemic_rupture(
        self,
        episode_index: int,
        new_gender: Optional[str] = None,
        anaphora_score: Optional[int] = None,
        prev_anaphora_score: Optional[int] = None,
        delta_score_en: Optional[int] = None,
        f0_hz: Optional[float] = None
    ) -> bool:
        """
        Zamyka poprzedni stan maski (valid_to_ep = episode_index - 1)
        i rejestruje dekonspirację (valid_from_ep = episode_index).
        Uwolnienie dekonspiracji (EP_RUPTURE) od basu:
        Wyzwalana na podstawie przejścia fazowego anaforyki (Delta Score_EN)
        lub silnego kontrastu anaforycznego (|Score_EN| >= 8) niezależnie od wysokości F0.
        """
        current_mask = self.get_effective_gender(episode_index=episode_index)
        resolved_gender = new_gender

        if delta_score_en is None and prev_anaphora_score is not None and anaphora_score is not None:
            delta_score_en = anaphora_score - prev_anaphora_score

        if resolved_gender is None:
            if anaphora_score is not None:
                if anaphora_score <= -8 or (delta_score_en is not None and delta_score_en <= -5 and anaphora_score < 0):
                    resolved_gender = "FEMININE"
                elif anaphora_score >= 8 or (delta_score_en is not None and delta_score_en >= 5 and anaphora_score > 0):
                    resolved_gender = "MASCULINE"
            elif delta_score_en is not None:
                if delta_score_en <= -5:
                    resolved_gender = "FEMININE"
                elif delta_score_en >= 5:
                    resolved_gender = "MASCULINE"

        if resolved_gender is None:
            resolved_gender = "FEMININE" if current_mask == "MASCULINE" else "MASCULINE"

        for interval in self.discourse_states:
            if interval.valid_to_ep is None or interval.valid_to_ep >= episode_index:
                interval.valid_to_ep = episode_index - 1

        self.discourse_states.append(
            PersonaInterval(
                apparent_gender=resolved_gender,
                valid_from_ep=episode_index,
                valid_to_ep=None,
                public_facade=False
            )
        )
        return True

    def evaluate_anaphora_rupture(
        self,
        anaphora_score: int,
        episode_index: int,
        prev_anaphora_score: Optional[int] = None,
        delta_score_en: Optional[int] = None,
        f0_hz: Optional[float] = None
    ) -> bool:
        """
        Uwolnienie dekonspiracji (EP_RUPTURE) od basu:
        Wyzwalanie dekonspiracji niezależnie od wysokości F0, gdy silny kontrast
        anaforyczny (|Score_EN| >= 8) lub przejście fazowe anaforyki (Delta Score_EN)
        przełamuje dotychczasową maskę apparent_gender.
        """
        if delta_score_en is None and prev_anaphora_score is not None:
            delta_score_en = anaphora_score - prev_anaphora_score

        current_mask = self.get_effective_gender(episode_index=episode_index)

        # 1. Silny kontrast anaforyczny (|Score_EN| >= 8) niezależnie od wysokości F0
        if current_mask == "MASCULINE" and anaphora_score <= -8:
            self.register_epistemic_rupture(episode_index, "FEMININE", anaphora_score=anaphora_score, delta_score_en=delta_score_en, f0_hz=f0_hz)
            return True
        elif current_mask == "FEMININE" and anaphora_score >= 8:
            self.register_epistemic_rupture(episode_index, "MASCULINE", anaphora_score=anaphora_score, delta_score_en=delta_score_en, f0_hz=f0_hz)
            return True

        # 2. Przejście fazowe anaforyki (Delta Score_EN) niezależnie od wysokości F0
        if delta_score_en is not None:
            if current_mask == "MASCULINE" and (delta_score_en <= -5 or (prev_anaphora_score is not None and prev_anaphora_score > 0 and anaphora_score < 0 and abs(delta_score_en) >= 6)):
                self.register_epistemic_rupture(episode_index, "FEMININE", anaphora_score=anaphora_score, delta_score_en=delta_score_en, f0_hz=f0_hz)
                return True
            elif current_mask == "FEMININE" and (delta_score_en >= 5 or (prev_anaphora_score is not None and prev_anaphora_score < 0 and anaphora_score > 0 and abs(delta_score_en) >= 6)):
                self.register_epistemic_rupture(episode_index, "MASCULINE", anaphora_score=anaphora_score, delta_score_en=delta_score_en, f0_hz=f0_hz)
                return True

        return False


GEOGRAPHIC_ORIGIN_PATTERNS: List[re.Pattern] = [
    # English: from [Name], people/soldiers/forces/kingdom/city/land of [Name], those [Name] guys/soldiers
    re.compile(r"\bfrom\s+([A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźżA-Z0-9'-]+(?:\s+[A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźżA-Z0-9'-]+)?)\b"),
    re.compile(r"\b(?:people|soldiers|forces|kingdom|city|land|troops|warriors|army|citizens|folk|residents|inhabitants|men|guards)\s+of\s+([A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźżA-Z0-9'-]+(?:\s+[A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźżA-Z0-9'-]+)?)\b", re.IGNORECASE),
    re.compile(r"\bthose\s+([A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźżA-Z0-9'-]+)\s+(?:guys|soldiers|troops|warriors|forces|people|men|knights)\b", re.IGNORECASE),
    re.compile(r"\b([A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźżA-Z0-9'-]+)\s+(?:domain|realm|kingdom|territory|province|city|castle|fortress)\b", re.IGNORECASE),
    # Motion and origin verbs in English (came from, escaped from, arrived from)
    re.compile(r"\b(?:came|comes|escaped|escape|fled|arrived|arrives|returned|journeyed|departed)\s+from\s+([A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźżA-Z0-9'-]+(?:\s+[A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźżA-Z0-9'-]+)?)\b", re.IGNORECASE),
    # Japanese: [Name] no mono/gun/hei/shou/kuni/tami
    re.compile(r"\b([A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźżA-Z0-9'-]+)\s*no\s*(?:mono|gun|hei|shou|kuni|tami)\b", re.IGNORECASE),
    re.compile(r"([A-Za-z\u3040-\u30ff\u4e00-\u9faf]+)(?:の者|の軍|の兵|の将|の国|の民)"),
    # Polish: ci z [Name], ludzie z [Name], żołnierze z [Name], oddział z [Name], etc.
    re.compile(r"\b(?:ci|tamci|ludzie|żołnierze|wojska|oddziały|armia|wojownicy)\s+z\s+([A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźżA-Z0-9'-]+)\b", re.IGNORECASE),
    re.compile(r"\b(?:królestwo|kraina|miasto|zamek|twierdza|prowincja)\s+([A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźżA-Z0-9'-]+)\b", re.IGNORECASE),
    re.compile(r"\b(?:dotarli|dotarł|dotarła|przybyli|przybył|przybyła|wrócili|wrócił|wróciła|przyszli|przyszedł|przyszła|wyszli|wyszedł|wyszła|pochodzą|pochodzi|pochodził|pochodziła|uciekli|uciekł|uciekła)\s+(?:z|ze)\s+([A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźżA-Z0-9'-]+)\b", re.IGNORECASE),
]

CHREMATONYM_PATTERNS: List[re.Pattern] = [
    re.compile(r"\b(?:księga|miecz|amulet|tarcza|lanca|zwój|korona|pierścień|relikwia|artefakt|topór|sztylet|berło)\s+([A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźżA-Z0-9'-]+)\b", re.IGNORECASE),
    re.compile(r"\b(?:book|sword|blade|amulet|shield|spear|scroll|crown|ring|relic|artifact|axe|dagger|scepter)\s+of\s+([A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźżA-Z0-9'-]+)\b", re.IGNORECASE),
]

@functools.lru_cache(maxsize=8192)
def normalize_name_nfkd(name: str) -> str:
    """
    Normalizuje znaki diakrytyczne Unicode (NFKD) w nazwach własnych:
    usuwa znaki łączone (combining characters), zachowując litery bazowe ASCII.
    """
    if not name:
        return ""
    nfkd = unicodedata.normalize('NFKD', str(name))
    return "".join(c for c in nfkd if not unicodedata.combining(c)).strip()


def normalize_negative_directive(text: str) -> str:
    """Normalizacja sformułowań negatywnych do formy czysto pozytywnej (Operacja 2B.8 / Standard 10.1)."""
    if not isinstance(text, str) or not text:
        return text
    res = text
    # 1. opóźnione otwarcie dialogu
    res = re.sub(
        r"(?:kateg[o]ryczn\w+|bezwzgl[ęe]dn\w+)?\s*z[a]kaz\s+opóźnionego\s+([^\->]+)\s*->\s*otwarcie\s+dialogu:\s*([^\]]+)",
        r"w otwarciu dialogu stosuj bezpośrednio: \2 (zamiast \1)",
        res,
        flags=re.IGNORECASE
    )
    # 2. 'nie zmieniaj na' / 'nie zmieniać na' / 'nie zmieniać słowa X na'
    res = re.sub(r"\bnie\s+zmienia(?:j|ć)(?:\s+słowa\s+\S+)?\s+na\b", "zachowaj ten wariant zamiast", res, flags=re.IGNORECASE)
    # 3. 'nie tłumaczyć jako'
    res = re.sub(r"\bnie\s+tłumaczyć\s+jako\b", "zachowaj ten wariant zamiast", res, flags=re.IGNORECASE)
    # 4. frazy restrykcyjne
    res = re.sub(r"\b(?:kateg[o]ryczn\w+|bezwzgl[ęe]dn\w+)?\s*z[a]kaz\s+opóźnionego\b", "wykluczenie opóźnionego", res, flags=re.IGNORECASE)
    res = re.sub(r"\b(?:kateg[o]ryczn\w+|bezwzgl[ęe]dn\w+)?\s*z[a]kaz\s+mieszania\b", "wykluczone mieszanie", res, flags=re.IGNORECASE)
    res = re.sub(r"\b(?:kateg[o]ryczn\w+|bezwzgl[ęe]dn\w+)?\s*z[a]kaz\s+hybryd\b", "wykluczone hybrydy", res, flags=re.IGNORECASE)
    res = re.sub(r"\b(?:kateg[o]ryczn\w+|bezwzgl[ęe]dn\w+)?\s*z[a]kaz\s+form\b", "wykluczone formy", res, flags=re.IGNORECASE)
    res = re.sub(r"\b(?:kateg[o]ryczn\w+|bezwzgl[ęe]dn\w+)?\s*z[a]kaz\s+używania\b", "stosuj wyłącznie formy kanoniczne (z pominięciem używania", res, flags=re.IGNORECASE)
    res = re.sub(r"\b(?:kateg[o]ryczn\w+|bezwzgl[ęe]dn\w+)?\s*z[a]kaz\s+innych\b", "stosuj wyłącznie formy kanoniczne (z pominięciem innych", res, flags=re.IGNORECASE)
    res = re.sub(r"\b(?:kateg[o]ryczn\w+|bezwzgl[ęe]dn\w+)?\s*z[a]kaz\s+", "wykluczono formę ", res, flags=re.IGNORECASE)
    # 5. 'unikaj'
    res = re.sub(r"\bunikaj\s+", "stosuj formę kanoniczną zamiast ", res, flags=re.IGNORECASE)
    return res

_normalize_negative_directive = normalize_negative_directive


def classify_entity_category(
    name: str,
    context: Optional[str] = None,
    is_speaking_actor: bool = False,
    series_bible: Optional[Any] = None
) -> EntityCategory:
    """
    Klasyfikacja ontologiczna EntityCategory (ANTHROPONYM | TOPONYM | CHREMATONYM):
    Nazwy własne występujące w konstrukcjach pochodzenia/geograficznych (from [Name],
    people/soldiers/forces/kingdom/city/land of [Name], those [Name] guys/soldiers,
    JA [Name] no mono/gun) i niebędące mówiącymi aktorami w polu event.name
    oznaczane są jako EntityCategory.TOPONYM (nieodmienne po przyimku z).
    """
    if not name:
        return EntityCategory.ANTHROPONYM

    clean_n = name.strip()
    clean_lower = clean_n.lower()

    # 1. Speaking actors in event.name default to ANTHROPONYM unless explicitly inanimate
    if is_speaking_actor:
        if series_bible and hasattr(series_bible, "is_non_character_entity") and series_bible.is_non_character_entity(clean_n):
            pass  # proceed to check if non-character
        else:
            return EntityCategory.ANTHROPONYM

    # 2. Check series_bible explicit registries
    if series_bible and hasattr(series_bible, "data") and series_bible.data:
        saved_cat = None
        categories = series_bible.data.get("entity_categories", {})
        clean_norm = normalize_name_nfkd(clean_n).lower()
        if clean_n in categories:
            saved_cat = categories[clean_n]
        else:
            for k, v in categories.items():
                if k.lower() == clean_lower or normalize_name_nfkd(k).lower() == clean_norm:
                    saved_cat = v
                    break
        if saved_cat:
            try:
                return EntityCategory(saved_cat)
            except Exception:
                logger.warning("Odczyt kategorii bytu zakończony wyjątkiem", exc_info=True)

    # 3. Contextual evaluation: origin / geographic constructions
    if context:
        for pat in GEOGRAPHIC_ORIGIN_PATTERNS:
            for match in pat.finditer(context):
                matched_val = match.group(1).strip()
                if matched_val.lower() == clean_lower:
                    if not is_speaking_actor:
                        if series_bible and hasattr(series_bible, "register_entity_category"):
                            series_bible.register_entity_category(clean_n, EntityCategory.TOPONYM)
                        return EntityCategory.TOPONYM

        for pat in CHREMATONYM_PATTERNS:
            for match in pat.finditer(context):
                matched_val = match.group(1).strip()
                if matched_val.lower() == clean_lower:
                    if not is_speaking_actor:
                        if series_bible and hasattr(series_bible, "register_entity_category"):
                            series_bible.register_entity_category(clean_n, EntityCategory.CHREMATONYM)
                        return EntityCategory.CHREMATONYM

    # 4. Known toponyms database & French indeclinable toponyms
    toponyms_set = globals().get("KNOWN_FANTASY_TOPONYMS", set())
    french_set = globals().get("INDECLINABLE_FRENCH_TOPONYMS", set())
    if clean_lower in toponyms_set or clean_lower in french_set:
        if not is_speaking_actor:
            if series_bible and hasattr(series_bible, "register_entity_category"):
                series_bible.register_entity_category(clean_n, EntityCategory.TOPONYM)
            return EntityCategory.TOPONYM

    # 5. Chrematonyms: artifacts, weapons, books, spells, relics
    head_nouns_set = globals().get("KNOWN_HEAD_NOUNS", set())
    if clean_lower in head_nouns_set or any(clean_lower.startswith(w + " ") for w in ("księga", "miecz", "amulet", "tarcza", "lanca", "zwój", "korona", "pierścień")):
        if series_bible and hasattr(series_bible, "register_entity_category"):
            series_bible.register_entity_category(clean_n, EntityCategory.CHREMATONYM)
        return EntityCategory.CHREMATONYM

    if series_bible and hasattr(series_bible, "is_non_character_entity") and series_bible.is_non_character_entity(clean_n):
        if hasattr(series_bible, "data") and series_bible.data:
            for sec in ("relics", "artifacts", "weapons"):
                if clean_n in series_bible.data.get(sec, {}):
                    series_bible.register_entity_category(clean_n, EntityCategory.CHREMATONYM)
                    return EntityCategory.CHREMATONYM
            for sec in ("realms", "locations", "places", "cities", "countries"):
                if clean_n in series_bible.data.get(sec, {}):
                    series_bible.register_entity_category(clean_n, EntityCategory.TOPONYM)
                    return EntityCategory.TOPONYM
        series_bible.register_entity_category(clean_n, EntityCategory.TOPONYM)
        return EntityCategory.TOPONYM

    return EntityCategory.ANTHROPONYM


def clean_fake_name_apostrophes(text: str) -> str:
    """
    Zasada poprawnego użycia apostrofu (Zero Fake Apostrophes - Standard PWN):
    Apostrof występuje WYŁĄCZNIE wtedy, gdy ostatnia litera obcego imienia/nazwiska jest niema
    fonetycznie w wygłosie obcym.
    Eliminacja apostrofu przy imionach czytanych fonetycznie.
    """
    if not text or "'" not in text:
        return text

    def _apostrophe_repl(m: re.Match) -> str:
        name = m.group(1)
        ending = m.group(2)
        n_low = name.lower()

        # 1. Japońskie imiona na samogłoskę lub żeńskie nieodmienne
        invariable_fem = globals().get("INVARIABLE_JAPANESE_FEMALE_NAMES", set())
        foreign_fem = globals().get("FOREIGN_FEMALE_CONSONANT_NAMES", set())
        if n_low in JAPANESE_VOWEL_E_NAMES or is_japanese_cv_mora_e_name(name) or n_low in invariable_fem or n_low in foreign_fem:
            return name

        # 2. Imiona męskie na samogłoskę + y -> fonetyczne połączenie bez apostrofu
        if len(name) >= 2 and name[-1].lower() == 'y' and name[-2].lower() in 'aeiou':
            return name + ending

        # 3. Nieme fonetycznie -e (spółgłoska + e w wygłosie obcym) -> apostrof poprawny
        if len(name) >= 3 and name[-1].lower() == 'e' and name[-2].lower() in 'bcdfghjklmnpqrstvwxz':
            if is_japanese_cv_mora_e_name(name) or n_low in JAPANESE_VOWEL_E_NAMES:
                return name
            return m.group(0)

        # 4. Imiona męskie na spółgłoskę czytaną fonetycznie -> bez apostrofu
        if name[-1].lower() not in 'aeiouyąęó':
            return name + ending

        # 5. Imiona na inne samogłoski fonetyczne
        if name[-1].lower() in 'aeiouy':
            return name[:-1] + ending

        return m.group(0)

    return re.sub(r"\b([A-Z][a-z]+)'([a-ząćęłńóśźż]+)\b", _apostrophe_repl, text)


def fix_undecorated_male_names(
    text: str,
    character_names: Optional[List[str]] = None,
    series_bible: Optional[Any] = None,
    custom_glossary: Optional[Dict[str, str]] = None
) -> str:
    """
    Koryguje błędy pozostawienia męskiego imienia w mianowniku w pozycji zależnej / po przyimkach.
    """
    if not text:
        return text

    gen_preps = r"(?:dla|do|od|bez|u|koło|obok|blisko|wokół|dookoła|spod|zza|znad|według|mimo|wobec|naprzeciw|wskutek)"
    dat_preps = r"(?:dzięki|przeciw|przeciwko|ku|wbrew|dałem\s+to|dałam\s+to|dał\s+to|dała\s+to|podarowałem|podarowałam|powiedziałem|powiedziałam)"
    ins_preps = r"(?:z|ze|przed|przede|nad|nade|pod|pode|między|pomiędzy|za)"

    if character_names is not None:
        names = list(character_names)
    elif series_bible and hasattr(series_bible, "characters") and isinstance(series_bible.characters, dict):
        names = []
        for c_name, c_rec in series_bible.characters.items():
            gen = getattr(c_rec, "gender", None) if not isinstance(c_rec, dict) else c_rec.get("gender")
            g_gen = getattr(c_rec, "grammatical_gender", None) if not isinstance(c_rec, dict) else c_rec.get("grammatical_gender")
            cat = getattr(c_rec, "category", None) if not isinstance(c_rec, dict) else c_rec.get("category")
            if (gen in ("MALE", "MASCULINE") or g_gen in ("MALE", "MASCULINE")) and cat != "TOPONYM":
                names.append(c_name)
    elif series_bible and hasattr(series_bible, "data") and "characters" in series_bible.data:
        names = [
            c_name for c_name, c_rec in series_bible.data["characters"].items()
            if isinstance(c_rec, dict) and (c_rec.get("gender") in ("MALE", "MASCULINE") or c_rec.get("grammatical_gender") in ("MALE", "MASCULINE"))
            and c_rec.get("category") != "TOPONYM"
        ]
    else:
        names = []

    # Dynamic identification of proper names following prepositions
    if not character_names:
        glossary_words = set()
        if custom_glossary:
            for g_k, g_v in custom_glossary.items():
                glossary_words.update(w.lower() for w in g_k.split())
                if isinstance(g_v, str):
                    glossary_words.update(w.lower() for w in g_v.split())
        if series_bible and hasattr(series_bible, "data") and "glossary" in series_bible.data:
            for g_k, g_v in series_bible.data["glossary"].items():
                glossary_words.update(w.lower() for w in g_k.split())
                if isinstance(g_v, str):
                    glossary_words.update(w.lower() for w in g_v.split())
        existing_name_forms = {n.lower() for n in names}
        for n in list(names):
            d_n = generate_polish_name_declension(n, "MALE")
            if d_n:
                existing_name_forms.update(val.lower() for val in d_n.values() if isinstance(val, str))
        if series_bible:
            all_chars = []
            if hasattr(series_bible, "characters") and isinstance(series_bible.characters, dict):
                all_chars = list(series_bible.characters.keys())
            elif hasattr(series_bible, "data") and "characters" in series_bible.data:
                all_chars = list(series_bible.data["characters"].keys())
            for ch in all_chars:
                existing_name_forms.add(ch.lower())
                d_m = generate_polish_name_declension(ch, "MALE")
                if d_m:
                    existing_name_forms.update(val.lower() for val in d_m.values() if isinstance(val, str))
                d_f = generate_polish_name_declension(ch, "FEMALE")
                if d_f:
                    existing_name_forms.update(val.lower() for val in d_f.values() if isinstance(val, str))
            if hasattr(series_bible, "declensions") and isinstance(series_bible.declensions, dict):
                for dec_val in series_bible.declensions.values():
                    if isinstance(dec_val, dict):
                        existing_name_forms.update(val.lower() for val in dec_val.values() if isinstance(val, str))

        cand_preps = rf"(?i:\b(?:{gen_preps}|{dat_preps}|{ins_preps})(?:\s+[a-ząćęłńóśźż]+)?\s+)([A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]+)\b"
        for m_cand in re.finditer(cand_preps, text):
            c_word = m_cand.group(1)
            if not c_word[0].isupper():
                continue
            if c_word.lower() in existing_name_forms:
                continue
            if c_word not in names and len(c_word) >= 2:
                if c_word.lower() in glossary_words:
                    continue
                if re.search(rf"\b{re.escape(c_word)}\s+(?:of|the|in|for|from|at|on|de|von|van|di|da)\b", text, re.I):
                    continue
                if not is_proper_noun_homonym(c_word) and not is_inherently_female_name(c_word, series_bible=series_bible):
                    names.append(c_word)
                    existing_name_forms.add(c_word.lower())
    result = text
    OBLIQUE_OR_ADJ_ENDINGS = ("ym", "im", "em", "ą", "owi", "ego", "emu", "ych", "ich", "ów", "om", "ami", "ach", "owie")
    for name in names:
        if not name or len(name) < 2:
            continue
        n_lower = name.lower()
        if any(n_lower.endswith(suf) for suf in OBLIQUE_OR_ADJ_ENDINGS):
            continue
        decl = generate_polish_name_declension(name, "MALE")
        if not decl or decl.get("M") != name:
            continue

        # 1. Genitive check: "dla Ray" -> "dla Raya"
        result = re.sub(
            rf"\b({gen_preps})\s+{re.escape(name)}\b",
            lambda m, c=decl.get("D", name): f"{m.group(1)} {c}",
            result,
            flags=re.IGNORECASE
        )

        # 2. Dative check: "ku Ray" -> "ku Rayowi", "dałem to Ray" -> "dałem to Rayowi", "podarowałem miecz Ray" -> "podarowałem miecz Rayowi"
        result = re.sub(
            rf"\b({dat_preps}(?:\s+[a-ząćęłńóśźż]+)?)\s+{re.escape(name)}\b",
            lambda m, c=decl.get("C", name): f"{m.group(1)} {c}",
            result,
            flags=re.IGNORECASE
        )

        # 3. Instrumental check: "z Ren" -> "z Renem", "przed Ray" -> "przed Rayem"
        def _ins_repl(m):
            prep = m.group(1)
            prep_lower = prep.lower()
            if prep_lower in ("z", "ze"):
                target_inst = decl.get('N', name)
                start_pos = m.start()
                preceding_text = result[max(0, start_pos - 60):start_pos]
                if target_inst.endswith("ą") or name.endswith("a"):
                    if series_bible and hasattr(series_bible, "can_inflect_feminine_instrumental_after_z"):
                        allowed = series_bible.can_inflect_feminine_instrumental_after_z(name, preceding_text=preceding_text)
                    else:
                        allowed = is_feminine_instrumental_after_z_allowed(name, preceding_text=preceding_text, series_bible=series_bible)
                    if not allowed:
                        return m.group(0)
                # Guard against toponyms and origin / ablative constructions
                is_toponym = (
                    classify_entity_category(name, context=result, series_bible=series_bible) == EntityCategory.TOPONYM
                    or (series_bible and (series_bible.is_non_character_entity(name) or series_bible.get_entity_category(name) == EntityCategory.TOPONYM))
                    or name.lower() in globals().get("KNOWN_FANTASY_TOPONYMS", set())
                    or name.lower() in globals().get("INDECLINABLE_FRENCH_TOPONYMS", set())
                )
                if is_toponym:
                    return m.group(0)
            elif prep_lower == "za":
                start_pos = m.start()
                preceding = result[:start_pos]
                if re.search(r"\b(?:wyjść|wyjdzie|wyjdą|wyjdziesz|wyszła|wyszedł|wyszli|walczyć|walczę|walczy|walczą|modlić\s+się|modlę\s+się|modli\s+się)\s*$", preceding, re.IGNORECASE):
                    c_acc = decl.get("B") or decl.get("D", name)
                    return f"{prep} {c_acc}"
            return f"{prep} {decl.get('N', name)}"

        result = re.sub(
            rf"\b({ins_preps})\s+{re.escape(name)}\b",
            _ins_repl,
            result,
            flags=re.IGNORECASE
        )

    return result

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


BILINGUAL_ROLE_EQUIVALENCES: Dict[str, str] = {
    "neighbor": "sąsiadka",
    "neighbour": "sąsiadka",
    "boy": "chłopiec",
    "girl": "dziewczynka",
    "teacher": "nauczyciel",
    "mother": "matka",
    "mom": "mama",
    "father": "ojciec",
    "dad": "tata",
    "boss": "szef",
    "president": "prezydent",
    "detective": "detektyw",
    "doctor": "doktor",
    "secretary": "sekretarka",
    "subordinate": "podwładny",
    "colleague": "kolega",
    "classmate": "kolega z klasy",
    "student": "uczeń",
    "police": "policjant",
    "policeman": "policjant",
    "officer": "funkcjonariusz",
    "magical girl": "magiczna dziewczyna",
    "hero": "bohater",
    "villain": "złoczyńca",
}


INHERENT_FEMALE_NOUNS = {
    # Basic / Family / Age
    "girl", "woman", "women", "lady", "female", "waitress", "miss", "mrs", "ms", "heroine", "witch", "princess", "sorceress", "queen", "empress", "duchess", "priestess",
    "dziewczyna", "dziewczynka", "kobieta", "matka", "mama", "mamusia", "mateczka", "mamunia", "macocha",
    "córka", "córeczka", "córunia", "siostra", "siostrzyczka", "siostrunia",
    "babcia", "babunia", "babka", "prababka", "staruszka", "starowinka", "starowina", "starucha", "seniorka", "matrona",
    "wnuczka", "prawnuczka", "ciotka", "ciocia", "ciotunia", "stryjenka", "wujenka", "wujna",
    "siostrzenica", "bratanica", "teściowa", "świekra", "synowa", "szwagierka", "bratowa", "jątrew",
    "kuzynka", "krewna", "pociotka", "sierota", "wdowa", "panna", "panienka", "panna młoda", "młodka", "niewiasta", "białogłowa",
    "pani", "pani domu", "oblubienica", "narzeczona", "wybranka", "ukochana", "małżonka", "żona", "żonka", "żonusia",
    # Nobility / Administration / Royalty
    "królowa", "królewna", "królowa-matka", "księżniczka", "księżna", "caryca", "cesarzowa", "cesarzówna", "carówna",
    "władczyni", "monarchini", "kniagini", "arcyksiężna", "arystokratka", "szlachcianka", "magnatka",
    "hrabina", "hrabianka", "margrabina", "baronowa", "baronówna", "wicehrabina", "markiza", "wielmożna", "suwerenka",
    "kasztelanka", "kasztelanowa", "wojewodzina", "wojewodzianka", "starościna", "starościanka", "podkomorzyna",
    "stolnikowa", "cześnikowa", "miecznikowa", "dziedziczka", "posesorka", "feudałka", "seniorka", "suzerenka",
    "protektorka", "patronka", "kuratorka", "sędzina", "sędzia", "jurorka", "notariuszka", "mecenaska", "rejentowa",
    "adwokatka", "prokuratorka", "trybunka", "prefektka", "rajczyni", "burmistrzyni", "prezydentka", "sołtyska", "wójtowa",
    "kanclerzowa", "kanclerka", "namiestniczka", "urzędniczka", "zarządczyni", "konsulka", "senatorka", "posłanka",
    "deputowana", "ambasadorka", "dyplomatka", "heroldzica",
    # Military / Guard / Combat
    "strażniczka", "wojowniczka", "żołnierka", "rycerka", "komendantka", "kapitanka", "generałowa",
    "łuczniczka", "szermierka", "zwiadowczyni", "najemniczka", "bohaterka", "oficerka", "rekrutka", "gladiatorka",
    "kuszniczka", "kanonierka", "partyzantka", "majorka", "pułkownikowa", "admirałowa", "hetmanka", "hetmanowa",
    "berserkerka", "amazonka", "tarczowniczka", "włóczniczka", "grenadierka", "sapera", "weteranka", "dezerterka", "cichociemna",
    # Religion / Magic / Science
    "czarownica", "czarodziejka", "kapłanka", "arcykapłanka", "miko", "westalka", "mniszka", "zakonnica", "opatka", "ksieni",
    "przeorysza", "siostrzyczka", "nowicjuszka", "postulantka", "misjonarka", "katechetka", "teolożka", "kaznodziejka",
    "prorokini", "wieszczka", "jasnowidzka", "wyrocznia", "wróżka", "wróżbiarka", "chiromantka", "zielarka", "guślarka",
    "szamanka", "druidka", "maga", "magini", "arcymaga", "czarnoksiężnica", "zaklinaczka", "nekromantka", "iluzjonistka",
    "alchemiczka", "astrologini", "mędrczyni", "uczona", "badaczka", "profesorka", "doktorka", "filozofka", "myślicielka",
    "astronomka", "matematyczka", "algebrzystka", "archeolożka", "historyczka", "kronikarka", "skrybka", "bibliotekarka", "archiwistka", "wiedźma", "wiedunka", "wiedunki",
    "demonica", "bogini", "wampirzyca", "wilkołaczka", "nimfa", "rusałka", "driada", "syrena", "harpia", "banshee", "sukuba", "sukub",
    "elfka", "krasnoludka", "orkini", "trollka", "diablica", "szatanka", "aniołica", "aniolica", "widmo", "zjawa",
    # Domestic / Service
    "służąca", "pokojówka", "gosposia", "kucharka", "kuchareczka", "szefowa kuchni", "ochmistrzyni", "panna służąca",
    "pomocnica", "posługaczka", "pomywaczka", "praczka", "garderobiana", "czesaczka", "fryzjerka", "kosmetyczka",
    "niańka", "piastunka", "mamka", "guwernantka", "bona", "opiekunka", "pensjonarka", "rezydentka", "odźwierna", "klucznica",
    "szafarka", "sprzątaczka", "dziewka",
    # Commoners / Trades / Crafts
    "wieśniaczka", "chłopka", "rolniczka", "kmiotka", "osadniczka", "kmieciowa", "zagrodniczka", "chałupniczka", "komornica",
    "pasterka", "owczarka", "dojarza", "gospodyni", "młynarka", "piekarzowa", "piekarka", "cukierniczka", "rzeźniczka", "masarka",
    "krawcowa", "szwaczka", "hafciarka", "prządka", "tkaczka", "bieliźniarka", "modystka", "kuśnierka", "garbarniczka",
    "szewcowa", "szewczyni", "kowalka", "kowalowa", "ślusarka", "stolarka", "garncarka", "bednarka", "cieślina", "murarka",
    "dekarzowa", "szklarzowa", "drukara", "zecerka", "introligatorka", "mydlarka", "świecarka", "bartniczka", "pszczelarka",
    "rybaczka", "marynarka", "flisaczka", "przewoźniczka", "woźniczka", "kupcowa", "handlarka", "kramarka", "straganiarka",
    "przekupka", "karczmarka", "szynkarka", "oberżystka", "szynkareczka", "barmanka", "kelnerka", "garkuchnica", "górniczka",
    # Underworld / Outsiders
    "bandytka", "rozbójniczka", "zbójniczka", "łotrzyca", "złodziejka", "złodziejaszka", "kasiarka", "kieszonkowniczka",
    "włamywaczka", "paserka", "szpieżka", "agentka", "wywiadowczyni", "skrytobójczyni", "zabójczyni", "morderczyni", "trucicielka",
    "piratka", "korsarka", "przemytniczka", "szmuglerka", "oszustka", "szulerka", "szantażystka", "kłusowniczka", "żebraczka",
    "nędzarka", "banitka", "wygnanka", "uchodźczyni", "tułaczka", "wędrowniczka", "uciekinierka", "zbieg", "renegatka",
    "apostatka", "heretyczka", "buntowniczka", "powstańczyni", "dywersantka", "partyzantka", "niewolnica", "branka",
    "więźniarka", "skazana", "potępiona",
    # School / Youth / Medicine
    "uczennica", "studentka", "słuchaczka", "wychowanka", "pensjonarka", "abiturientka", "absolwentka", "stażystka",
    "praktykantka", "asystentka", "nauczycielka", "bakałarzowa", "pedagożka", "lektorka", "korepetytorka", "instruktorka",
    "mentorka", "mistrzyni", "przewodniczka", "lekarka", "medyczka", "felczerka", "chirurżka", "internistka", "okulistka",
    "pediatrka", "psychiatra", "psycholożka", "terapeutka", "aptekarka", "farmaceutka", "uzdrowicielka", "znachorka",
    "sanitariuszka", "pielęgniarka", "siostra miłosierdzia", "salowa", "ratowniczka", "pacjentka", "chora", "ranna", "ozdrowieńcza"
}

INHERENT_MALE_NOUNS = {
    # Basic / Family / Age
    "boy", "man", "men", "guy", "male", "waiter", "lord", "mr", "hero", "wizard", "prince", "knight", "king", "emperor", "duke", "priest",
    "chłopak", "chłopiec", "mężczyzna", "ojciec", "tata", "tatuś", "ojczym", "syn", "synek", "synuś", "pasierb",
    "brat", "braciszek", "dziadek", "dziadziuś", "starzec", "staruszek", "senior", "nestor", "starowina",
    "pradziadek", "wnuk", "wnuczek", "prawnuk", "wuj", "wujek", "stryj", "stryjek", "siostrzeniec", "bratanek",
    "teść", "świekier", "zięć", "szwagier", "bratankowy", "kuzyn", "krewny", "pociotek", "sierota", "wdowiec",
    "kawaler", "młodzieniec", "młodzik", "podrostek", "gołowąs", "młodzian", "pan", "panicz", "bocchan",
    "oblubieniec", "pan młody", "mąż", "małżonek",
    # Nobility / Administration / Royalty
    "król", "królewicz", "król-ojciec", "książę", "książątko", "car", "carewicz", "cesarz", "cesarzewicz", "władca",
    "monarcha", "kniź", "diuk", "arcyksiążę", "arystokrata", "szlachcic", "magnat", "hrabia", "hrabicz", "margrabia",
    "markiz", "baron", "baronet", "wicehrabia", "wielmoża", "suweren", "kasztelan", "wojewoda", "starosta",
    "podkomorzy", "stolnik", "cześnik", "miecznik", "dziedzic", "posesor", "feudał", "senior", "suzeren", "wasal",
    "protektor", "patron", "kurator", "sędzia", "ławnik", "juror", "notariusz", "mecenas", "rejent", "adwokat",
    "prokurator", "trybun", "konsul", "senator", "poseł", "deputowany", "ambasador", "dyplomata", "legat", "herold",
    "woźny", "burmistrz", "prezydent", "rajca", "wójt", "sołtys", "kanclerz", "wicekanclerz", "namiestnik", "urzędnik",
    "poborca", "zarządca", "intendent", "dostojnik", "kuge", "buke",
    # Military / Guard / Combat
    "strażnik", "wartownik", "obrońca", "żołnierz", "rycerz", "generał", "dowódca", "kapitan", "komendant",
    "sierżant", "porucznik", "podporucznik", "pułkownik", "podpułkownik", "major", "rotmistrz", "kapral", "szeregowiec",
    "kadet", "rekrut", "brygadier", "feldmarszałek", "marszałek", "admirał", "komandor", "sternik", "nawigator",
    "marynarz", "majtek", "bosman", "fechmistrz", "giermek", "łucznik", "kusznik", "szermierz", "piechur",
    "zwiadowca", "kanonier", "artylerzysta", "saper", "szpica", "forpoczta", "wojownik", "najemnik", "kondotier",
    "hetman", "oficer", "samuraj", "bohater", "czempion", "berserker", "gladiator", "tarczownik", "włócznik",
    "halabardnik", "pikinier", "muszkieter", "dragon", "ułan", "husarz", "kirasjer", "lansjer", "kawalerzysta",
    "grenadier", "weteran", "inwalida", "dezerter", "partyzant", "powstaniec", "dywersant", "komandos", "snajper",
    # Religion / Magic / Science
    "czarodziej", "czarnoksiężnik", "mag", "arcymag", "wiedun", "wieduni", "wiedunowie", "kapłan", "arcykapłan", "mnich", "zakonnik", "brat zakonny",
    "nowicjusz", "kleryk", "seminarzysta", "opat", "przeor", "biskup", "arcybiskup", "patriarcha", "kardynał", "papież",
    "prałat", "kanonik", "proboszcz", "wikary", "wikariusz", "misjonarz", "kaznodzieja", "teolog", "katecheta",
    "prorok", "wieszcz", "jasnowidz", "wyrocznia", "wróżbita", "astrolog", "chiromanta", "guślarz", "szaman", "druid",
    "zielarz", "znachor", "czarownik", "zaklinacz", "nekromanta", "iluzjonista", "alchemik", "mędrzec", "uczony",
    "filozof", "myśliciel", "badacz", "profesor", "doktor", "astronom", "matematyk", "archeolog", "historyk",
    "kronikarz", "skryba", "kopista", "bibliotekarz", "archiwista",
    "demon", "bóg", "wampir", "wilkołak", "tryton", "centaur", "satyr", "inkub",
    "elf", "krasnolud", "ork", "troll", "anioł", "archanioł", "diabeł", "szatan", "czort",
    # Domestic / Service
    "służący", "lokaj", "kamerdyner", "majordomus", "ochmistrz", "stangret", "woźnica", "parobek", "parobczak",
    "pachołek", "stajenny", "masztalerz", "fornal", "ogrodnik", "stróż", "odźwierny", "cerber", "klucznik",
    "szafarz", "kucharz", "kuchcik", "szef kuchni", "piwniczny", "podczaszy", "kredencerz", "guwerner", "pedagog",
    "opiekun", "rezydent", "posłaniec", "goniec",
    # Commoners / Trades / Crafts
    "wieśniak", "chłop", "kmiotek", "rolnik", "oracz", "siewca", "żniwiarz", "kosiarz", "rataj", "włościanin", "osadnik",
    "kmieć", "zagrodnik", "chałupnik", "komornik", "pasterz", "owczarz", "pastuszek", "juhas", "gospodarz", "młynarz",
    "piekarz", "cukiernik", "masarz", "rzeźnik", "krawiec", "szewc", "garbarz", "kuśnierz", "kowal", "ślusarz",
    "stolarz", "cieśla", "bednarz", "kołodziej", "rymarz", "siodlarz", "garncarz", "zdun", "murarz", "dekarz",
    "szklarz", "malarz", "kamieniarz", "rzeźbiarz", "drukarz", "zecer", "introligator", "tkacz", "powroźnik",
    "mydlarz", "świecarz", "zielarz", "bartnik", "pszczelarz", "leśnik", "gajowy", "drwal", "smolarz", "węglarz",
    "rybak", "flisak", "marynarz", "żeglarz", "przewoźnik", "dorożkarz", "furman", "tragarz", "kurier", "listonosz",
    "kupiec", "handlarz", "kramarz", "straganiarz", "przekupień", "faktor", "lichwiarz", "bankier", "wekslarz",
    "karczmarz", "szynkarz", "oberżysta", "barman", "kelner", "garkuchnik", "górnik",
    # Underworld / Outsiders
    "bandyta", "zbój", "zbójnik", "rozbójnik", "łotr", "łotrzyk", "rzezimieszek", "złodziej", "złodziejaszek",
    "kasiarz", "doliniarz", "kieszonkowiec", "włamywacz", "paser", "szpieg", "agent", "wywiadowca", "donosiciel",
    "kapuś", "skrytobójca", "zabójca", "morderca", "truciciel", "pirat", "korsarz", "kaper", "przemytnik",
    "szmugler", "oszust", "szuler", "szantażysta", "kłusownik", "żebrak", "nędzarz", "dziad", "łachmaniarz",
    "banita", "wygnaniec", "uchodźca", "tułacz", "wędrowiec", "pielgrzym", "uciekinier", "zbieg", "renegat",
    "apostata", "heretyk", "buntownik", "powstaniec", "dywersant", "niewolnik", "jeniec", "więzień", "skazaniec", "potępieniec",
    # School / Youth / Medicine
    "uczeń", "student", "żak", "słuchacz", "wychowanek", "pensjonarz", "abiturient", "absolwent", "stażysta",
    "praktykant", "asystent", "nauczyciel", "profesor", "bakałarz", "pedagog", "lektor", "wychowawca", "korepetytor",
    "instruktor", "mentor", "mistrz", "przewodnik", "doktor", "lekarz", "medyk", "felczer", "chirurg", "internista",
    "okulista", "pediatra", "psychiatra", "psycholog", "terapeuta", "aptekarz", "farmaceuta", "uzdrowiciel", "znachor",
    "sanitariusz", "pielęgniarz", "ratownik", "pacjent", "chory", "ranny", "ozdrowieniec"
}

INHERENT_PLURAL_NOUNS = {
    # Polish
    "strażnicy", "wartownicy", "obrońcy", "żołnierze", "wojownicy", "rycerze", "szermierze", "łucznicy", "kusznicy",
    "kanonierzy", "saperzy", "zwiadowcy", "piechurzy", "gladiatorzy", "grenadierzy", "kadeci", "rekruci", "kaprale",
    "sierżanci", "oficerowie", "kapitanowie", "majorowie", "pułkownicy", "generałowie", "marszałkowie", "admirałowie",
    "marynarze", "weterani", "dezerterzy", "partyzanci", "powstańcy", "komandosi", "snajperzy", "najemnicy", "dowódcy",
    "berserkerzy", "amazonki", "wojowniczki", "strażniczki", "łuczniczki", "zwiadowczynie",
    "wieśniacy", "chłopi", "rolnicy", "osadnicy", "pasterze", "młynarze", "piekarze", "rzeźnicy", "krawcy", "szewcy",
    "kowale", "ślusarze", "stolarze", "cieśle", "murarze", "drukarze", "tkacze", "drwale", "rybacy", "flisacy",
    "marynarze", "żeglarze", "przewoźnicy", "woźnice", "tragarze", "kurierzy", "gońcy", "posłańcy", "handlarze",
    "kupcy", "kramarze", "szynkarze", "karczmarze", "barmanki", "kelnerzy", "kelnerki", "wieśniaczki", "chłopki",
    "krawcowe", "szwaczki", "mieszkańcy", "mieszczanie", "obywatele", "tubylcy", "tutejsi",
    "arystokraci", "szlachcice", "szlachta", "magnaci", "lordowie", "baronowie", "hrabiowie", "suwereni", "władcy",
    "władczynie", "królowie", "królowe", "cesarze", "cesarzowe", "książęta", "księżniczki", "sędziowie", "notariusze",
    "adwokaci", "senatorowie", "posłowie", "dyplomaci", "ambasadorzy",
    "kapłani", "kapłanki", "mnisi", "zakonnicy", "zakonnice", "mniszki", "biskupi", "druidzi", "szamani", "prorocy",
    "wieszcze", "czarodzieje", "magowie", "czarnoksiężnicy", "nekromanci", "alchemicy", "mędrcy", "uczeni",
    "profesorowie", "skrybowie",
    "słudzy", "służący", "służące", "lokaje", "kamerdynerzy", "pachołkowie", "parobkowie", "stajenni", "ogrodnicy",
    "stróże", "kucharze", "kucharki", "pokojówki", "niańki", "piastunki", "mamki", "opiekunki",
    "ludzie", "mężczyźni", "kobiety", "panowie", "panie", "młodzieńcy", "panny", "panny młode", "chłopcy",
    "dziewczęta", "dziewczyny", "dziewczynki", "dzieci", "maluchy", "berbecie", "dzieciaki", "rodzice", "ojcowie",
    "matki", "synowie", "córki", "bracia", "siostry", "dziadkowie", "babcie", "wnuki", "wujowie", "stryjowie", "ciotki",
    "krewni", "pociotkowie", "małżonkowie", "pary", "narzeczeni", "wdowy", "wdowcy", "starcy", "staruszkowie",
    "staruszki", "seniorzy", "przodkowie",
    "bandyci", "rozbójnicy", "zbóje", "zbójnicy", "rozbójnicy", "łotry", "rzezimieszki", "złodzieje", "włamywacze",
    "szpiedzy", "agenci", "skrytobójcy", "zabójcy", "mordercy", "piraci", "korsarze", "przemytnicy", "szulerzy",
    "żebracy", "nędzarze", "banici", "wygnańcy", "uchodźcy", "uchodźczynie", "tułacze", "uciekinierzy", "renegaci",
    "buntownicy", "powstańcy", "niewolnicy", "niewolnice", "jeńcy", "więźniowie", "skazańcy",
    "uczniowie", "uczennice", "studentki", "studenci", "słuchacze", "wychowankowie", "absolwenci", "nauczyciele",
    "nauczycielki", "lektorzy", "mentorzy", "lekarze", "lekarki", "medycy", "chirurdzy", "aptekarze", "uzdrowiciele",
    "pielęgniarki", "pielęgniarze", "sanitariusze", "ratownicy", "pacjenci", "pacjentki", "ranni", "chorzy",
    "tłum", "tłumy", "pospólstwo", "gawiedź", "czeladź", "rzesza", "rzesze", "starszyzna", "plemię", "klan", "ród",
    "załoga", "armia", "wojsko", "wojska", "oddział", "oddziały", "kompania", "kompanie", "warta", "straż", "patrol",
    "patrole", "pułk", "pułki", "batalion", "bataliony", "dywizja", "dywizje", "legia", "legie", "horda", "hordy",
    "wataha", "watahy", "zgraja", "banda", "bandy", "świta", "orszak", "zgromadzenie", "zebrani", "zebranie",
    "goście", "widzowie", "publiczność", "widownia", "obecni", "uczestnicy", "pasażerowie", "przechodnie", "gapie",
    "posłańcy", "gońcy",
    # English
    "guards", "soldiers", "warriors", "knights", "generals", "commanders", "officers", "mercenaries", "archers",
    "swordsmen", "spearmen", "scouts", "snipers", "captains", "marshals", "admirals", "sailors", "veterans", "rebels",
    "partisans", "commandos",
    "villagers", "peasants", "farmers", "citizens", "townspeople", "merchants", "traders", "people", "settlers",
    "shepherds", "bakers", "butchers", "smiths", "blacksmiths", "carpenters", "fishermen", "drivers", "couriers",
    "innkeepers", "bartenders", "waiters", "waitresses",
    "nobles", "aristocrats", "lords", "ladies", "barons", "dukes", "princes", "princesses", "kings", "queens",
    "judges", "senators", "diplomats",
    "priests", "priestesses", "monks", "nuns", "bishops", "shamans", "druids", "wizards", "mages", "sorcerers",
    "necromancers", "alchemists", "scholars", "scribes",
    "servants", "maids", "butlers",
    "men", "women", "boys", "girls", "children", "kids", "toddlers", "parents", "fathers", "mothers", "sons", "daughters",
    "brothers", "sisters", "grandparents", "ancestors",
    "bandits", "robbers", "thieves", "burglars", "rogues", "outlaws", "spies", "assassins", "killers", "murderers",
    "pirates", "smugglers", "beggars", "slaves", "captives", "prisoners", "convicts", "refugees", "exiles", "runaways",
    "students", "pupils", "teachers", "professors", "mentors", "doctors", "medics", "surgeons", "nurses", "patients",
    "crowd", "crowds", "mob", "mobs", "crew", "crews", "army", "armies", "patrol", "patrols", "squad", "squads",
    "company", "unit", "units", "troop", "troops", "bystanders", "guests", "spectators", "audience", "passengers"
}

CANONICAL_MALE_NAMES = {
    "shira", "akira", "gaara", "ashitaka", "kiba", "soma", "kenta",
    "ryoma", "hanza", "sinbad", "judar", "alibaba", "robert"
}


FEMALE_ROLE_KEYWORDS = [
    # General / Base
    "female", "kobieta", "dziewczyn", "żeńsk", "pani ", "panią", "paniom", "panieńskie",
    # Rodzina (18)
    "matk", "mamk", "córk", "siostr", "babk", "babci", "prababk", "prababci",
    "wnuczk", "prawnuczk", "ciotk", "wujenk", "stryjenk", "bratanic", "siostrzenic",
    "teściowa", "teściowej", "teściową", "świekr", "synowa", "synowej", "synową", "szwagierk", "kuzynk", "pasierbic", "macoch",
    # Monarchia & Władza (22)
    "królowa", "królowej", "królową", "królowo", "królewn", "księżniczk", "księżn", "cesarzowa", "cesarzowej", "cesarzową", "cesarzewn", "caryc", "carewn",
    "władczyn", "suwerenk", "monarchin", "arcyksiężn", "wielmożna", "wielmożnej", "wielmożną", "diuszes", "markiz", "margrabin",
    "hrabin", "hrabiank", "wicehrabin", "baronowa", "baronowej", "baronową", "baronówn", "szlachciank", "magnatk", "arystokratk",
    # Dwór & Służba (20)
    "panienk", "pann[ayęe]", "służąca", "służącej", "służącą", "pokojówk", "garderobiana", "garderobianej", "garderobianą", "ochmistrzyn", "woźniczk",
    "fornaliczk", "stajenna", "stajennej", "stajenną", "posługaczk", "ogrodniczk", "kuchark", "pomywaczk", "szafark",
    "klucznic", "zarządczyn", "dama dworu", "dwórk", "niańk",
    # Wojsko & Straż (35)
    "żołnierk", "wojowniczk", "rycerk", "strażniczk", "wartowniczk", "dowódczyn", "generałowa", "generałowej", "generałową", "generałk",
    "komendantk", "kapitank", "oficerk", "poruczniczk", "podporuczniczk", "pułkowniczk", "podpułkowniczk",
    "majork", "sierżantk", "kapralk", "szeregowa", "szeregowej", "szeregową", "kadetk", "rekrutk", "hetmanowa", "hetmanowej", "hetmanową",
    "fechmistrzyn", "szermierk", "łuczniczk", "kuszniczk", "włóczniczk", "tarczowniczk", "pikinierk",
    "zwiadowczyn", "kanonierk", "saperk", "piechurk", "najemniczk", "obrończyn", "przywódczyn",
    # Religia & Magia (25)
    "kapłank", "arcykapłank", "mniszk", "zakonnic", "opatk", "przeorysz", "biskupk", "czarodziejk",
    "czarownic", "magini", "arcymagini", "czarnoksiężnic", "nekromantk", "alchemiczk", "szamank",
    "druidk", "guślark", "wiedźm", "wróżk", "wieszczk", "prorokin", "zielark", "znachork",
    "zaklinaczk", "iluzjonistk", "egzorcystk",
    # Rzemiosło & Handel (30)
    "kowalk", "karczmark", "szynkark", "oberżystk", "kupcowa", "kupcowej", "kupcową", "kupczyn", "handlark", "kramark",
    "piekark", "cukierniczk", "rzeźniczk", "krawcowa", "krawcowej", "krawcową", "szewcowa", "szewcowej", "szewcową", "stolark", "cieślin", "garncark",
    "tkaczk", "garbark", "kuśnierk", "młynark", "rolniczk", "wieśniaczk", "chłopk", "pasterk",
    "drwalk", "leśniczk", "gajowa", "gajowej", "gajową", "rybaczk", "żeglark", "sterniczk",
    # Edukacja & Medycyna (15)
    "nauczycielk", "profesork", "uczennic", "studentk", "wychowawczyn", "lekark", "medyczk",
    "pielęgniark", "uzdrowicielk", "aptekark", "sędzin", "urzędniczk", "namiestniczk", "kanclerzowa", "kanclerzowej", "kanclerzową", "skrybk",
    # Dodatkowe
    "bohaterk", "chatun", "szpieżk", "girl", "woman", "lady"
]

MALE_ROLE_KEYWORDS = [
    # General / Base
    "male", "mężczyzna", "chłopak", "chłopiec", "boy", "młodzieniec", "męsk", "bocchan", "panie", "pan ", "man",
    # Rodzina (18)
    "ojciec", "syn", "brat", "dziadek", "pradziadek", "wnuk", "prawnuk", "wuj", "stryj",
    "bratanek", "siostrzeniec", "teść", "świekier", "zięć", "szwagier", "kuzyn", "pasierb", "ojczym",
    # Monarchia & Władza (22)
    "król", "królewicz", "książę", "cesarz", "cesarzewicz", "car ", "carewicz", "władca", "suweren",
    "monarcha", "arcyksiążę", "wielmoża", "wielmożny", "diuk", "markiz", "margrabia", "hrabi", "hrabicz",
    "wicehrabia", "baron", "szlachcic", "magnat", "arystokrata",
    # Dwór & Służba (20)
    "panicz", "służący", "lokaj", "kamerdyner", "majordomus", "ochmistrz", "stangret", "fornal",
    "stajenny", "pachołek", "parobek", "ogrodnik", "kucharz", "kuchcik", "szafarz", "klucznik",
    "zarządca", "giermek", "paź ", "samuraj",
    # Wojsko & Straż (35)
    "żołnierz", "wojownik", "rycerz", "strażnik", "wartownik", "dowódc", "generał", "komendant",
    "kapitan", "oficer", "porucznik", "podporucznik", "pułkownik", "podpułkownik", "major", "sierżant",
    "kapral", "szeregowiec", "szeregowy", "kadet", "rekrut", "hetman", "fechmistrz", "szermierz", "łucznik",
    "kusznik", "włócznik", "tarczownik", "pikinier", "zwiadowca", "kanonier", "saper", "piechur",
    "najemnik", "obrońca", "wódz ", "kat ",
    # Religia & Magia (25)
    "kapłan", "arcykapłan", "mnich", "zakonnik", "opat ", "przeor", "biskup", "czarodziej",
    "czarownik", "mag ", "arcymag", "czarnoksiężnik", "nekromanta", "alchemik", "szaman",
    "druid", "guślarz", "wróżbita", "wieszcz", "prorok", "zielarz", "znachor", "zaklinacz",
    "iluzjonista", "egzorcysta",
    # Rzemiosło & Handel (30)
    "kowal", "karczmarz", "szynkarz", "oberżysta", "kupiec", "handlarz", "kramarz", "piekarz",
    "cukiernik", "rzeźnik", "krawiec", "szewc", "stolarz", "cieśla", "garncarz", "tkacz",
    "garbarz", "kuśnierz", "młynarz", "rolnik", "wieśniak", "chłop ", "pasterz", "drwal",
    "leśnik", "gajowy", "rybak", "marynarz", "żeglarz", "sternik",
    # Edukacja & Medycyna (15)
    "nauczyciel", "profesor", "uczeń", "student", "wychowawca", "lekarz", "medyk", "pielęgniarz",
    "uzdrowiciel", "aptekarz", "sędzia", "urzędnik", "namiestnik", "kanclerz", "skryba",
    # Dodatkowe
    "lord", "kuge", "buke", "wasal"
]

POLISH_COMMON_NOUN_HOMONYMS: Set[str] = {
    # 1. Żywioły, astronomia, pory roku i czas (65 słów)
    "ogień", "woda", "ziemia", "wiatr", "powietrze", "płomień", "żar", "popiół", "iskra", "dym",
    "lód", "mróz", "śnieg", "szron", "grad", "deszcz", "ulewa", "burza", "grom", "piorun",
    "błyskawica", "chmura", "mgła", "rosa", "szadź", "fala", "przypływ", "odpływ", "wir", "prąd",
    "blask", "światło", "cień", "mrok", "ciemność", "zorza", "łuna", "tęcza", "promień", "słońce",
    "księżyc", "gwiazda", "kometa", "meteoryt", "świt", "brzask", "poranek", "dzień", "południe", "zmierzch",
    "zmrok", "wieczór", "noc", "północ", "czas", "chwila", "moment", "wieczność", "era", "wiek",
    "zima", "wiosna", "lato", "jesień",

    # 2. Minerały, metale i barwy (47 słów)
    "kamień", "skała", "głaz", "żwir", "piasek", "pył", "proch", "glina", "błoto", "kreda",
    "węgiel", "ruda", "kruszec", "żelazo", "stal", "miedź", "brąz", "mosiądz", "spiż", "złoto",
    "srebro", "ołów", "cyna", "rtęć", "kryształ", "diament", "rubin", "szafir", "szmaragd", "bursztyn",
    "perła", "koral", "agat", "jaspis", "ametyst", "onyks", "opal", "nefryt", "topaz", "biel",
    "czerń", "czerwień", "błękit", "zieleń", "żółć", "purpura", "szkarłat",

    # 3. Zwierzęta, ptaki, owady i bestie fantastyczne (104 słowa)
    "wilk", "wilczyca", "lis", "lisica", "niedźwiedź", "lew", "lwica", "tygrys", "pantera", "lampart",
    "ryś", "żbik", "kuna", "borsuk", "wydra", "soból", "gronostaj", "łasica", "jeleń", "sarna",
    "łoś", "daniel", "dzik", "żubr", "tur", "koń", "ogier", "klacz", "byk", "wół",
    "krowa", "baran", "owca", "kozioł", "koza", "pies", "wilczur", "ogar", "kot", "mysz",
    "szczur", "zając", "królik", "jeż", "kret", "bóbr", "wiewiórka", "nietoperz", "orzeł", "sokół",
    "jastrząb", "krogulec", "bielik", "myszołów", "sęp", "kruk", "wrona", "gawron", "kawka", "sroka",
    "sójka", "sowa", "puchacz", "puszczyk", "bocian", "żuraw", "czapla", "łabędź", "gęś", "kaczka",
    "kormoran", "mewa", "jaskółka", "gołąb", "słowik", "skowronek", "drozd", "kos", "dzięcioł", "dudek",
    "kogut", "kura", "kaczor", "bażant", "kuropatwa", "wąż", "żmija", "zaskroniec", "jaszczurka", "żółw",
    "krokodyl", "żaba", "ropucha", "salamandra", "smok", "żmij", "gryf", "bazyliszek", "wiwerna", "hydra",
    "feniks", "chimera", "jednorożec", "pegaz", "lewiatan", "kraken", "pająk", "skorpion", "osa", "pszczoła",
    "szerszeń", "mrówka", "ważka", "modliszka", "mucha", "komar", "motyl", "ćma", "żuk", "chrząszcz",

    # 4. Flora, drzewa i roślinność (55 słów)
    "drzewo", "las", "bór", "puszcza", "gaj", "dąb", "sosna", "świerk", "jodła", "modrzew",
    "brzoza", "buk", "grab", "jesion", "wiąz", "klon", "jawor", "lipa", "olcha", "topola",
    "wierzba", "cis", "jarząb", "głóg", "tarnina", "róża", "lilia", "mak", "fiołek", "wrzos",
    "mech", "paproć", "trawa", "trzcina", "sitowie", "bluszcz", "jemioła", "konwalia", "pokrzywa", "piołun",
    "liść", "gałąź", "konar", "pień", "kora", "korzeń", "pąk", "kwiat", "owoc", "jagoda",
    "nasiono", "ziarno", "szyszka", "cierń", "kolec",

    # 5. Topografia, krajobraz i architektura (98 słów)
    "góra", "szczyt", "grań", "turnia", "wierch", "przełęcz", "stok", "zbocze", "wzgórze", "pagórek",
    "kotlina", "dolina", "parów", "jar", "wąwóz", "rów", "przepaść", "urwisko", "otchłań", "jaskinia",
    "grota", "pieczara", "piekiełko", "wulkan", "krater", "pustynia", "step", "preria", "sawanna", "łąka",
    "pole", "równina", "polana", "bagno", "moczary", "bagnisko", "trzęsawisko", "rzeka", "potok", "strumień",
    "ruczaj", "źródło", "koryto", "brzeg", "mielizna", "wodospad", "kaskada", "jezioro", "staw", "sadzawka",
    "morze", "ocean", "zatoka", "zalew", "cieśnina", "fiord", "laguna", "wyspa", "wysepka", "archipelag",
    "półwysep", "przylądek", "rafa", "mierzeja", "droga", "trakt", "szlak", "ścieżka", "gościniec", "rozdroże",
    "skrzyżowanie", "most", "kładka", "grobla", "tama", "brama", "wrota", "furta", "baszta", "wieża",
    "mur", "mury", "zamek", "gród", "twierdza", "forteca", "szaniec", "bastion", "pałac", "dwór",
    "chata", "dom", "domostwo", "osada", "wieś", "miasto", "rynek", "plac", "uliczka", "zaułek",
    "świątynia", "klasztor", "kaplica", "ołtarz", "grobowiec", "grób", "mogiła", "kurhan", "cmentarz", "czeluść",
    "loch", "piwnica", "katakumby", "labirynt",

    # 6. Broń, rynsztunek i insygnia (73 słowa)
    "miecz", "szpada", "szabla", "rapier", "sztylet", "kord", "nóż", "puginał", "kindżał", "kosa",
    "sierp", "włócznia", "pika", "lanca", "dzida", "oszczep", "harpun", "halabarda", "berdysz", "glewia",
    "topór", "siekiera", "czekan", "nadziak", "obuch", "młot", "młotek", "buława", "buzdygan", "korbacz",
    "kiścień", "wekiera", "pałka", "maczuga", "kij", "kostur", "laska", "proca", "łuk", "kusza",
    "strzała", "bełt", "grot", "kołczan", "tarcza", "puklerz", "pawęż", "hełm", "przyłbica", "szyszak",
    "kolczuga", "pancerz", "zbroja", "kirys", "napierśnik", "naramiennik", "karwasz", "rękawica", "nagolennik", "nakolannik",
    "pas", "pochwa", "temblak", "korona", "diadem", "tiara", "tron", "berło", "jabłko", "pieczęć",
    "herb", "sztandar", "chorągiew", "flaga", "proporzec", "godło", "znak", "łańcuch", "powróz", "lina",
    "kajdany", "dyby", "klatka", "hak", "kotwica",

    # 7. Pojęcia abstrakcyjne, cnoty, afekt i magia (96 słów)
    "wola", "los", "dola", "niedola", "fatum", "przeznaczenie", "przypadek", "zbieg", "kres", "początek",
    "koniec", "życie", "śmierć", "duma", "honor", "chwała", "sława", "hańba", "wstyd", "męstwo",
    "odwaga", "śmiałość", "strach", "lęk", "trwoga", "groza", "zgroza", "panika", "ból", "cierpienie",
    "męka", "katusze", "rozpacz", "żal", "smutek", "tęsknota", "gniew", "złość", "szał", "wściekłość",
    "furia", "spokój", "pokój", "cisza", "milczenie", "prawda", "fałsz", "kłamstwo", "obłuda", "zdrada",
    "wierność", "wiara", "nadzieja", "miłość", "nienawiść", "łaska", "litość", "miłosierdzie", "zemsta", "odwet",
    "kara", "nagroda", "prawo", "bezprawie", "sprawiedliwość", "wolność", "swoboda", "niewola", "pęta", "więzy",
    "potęga", "siła", "moc", "niemoc", "słabość", "władza", "rządy", "panowanie", "ład", "porządek",
    "chaos", "bezład", "cud", "omen", "wróżba", "klątwa", "przekleństwo", "urok", "czar", "czary",
    "zaklęcie", "magia", "wiedza", "mądrość", "rozum", "spryt", "zmysł", "pamięć", "zapomnienie", "sen",
    "jawa", "mara", "widziadło", "zmora", "iluzja", "złudzenie", "tajemnica", "sekret", "zagadka", "krzyż",

    # 8. Części ciała, somatyka i percepcja (66 słów)
    "oko", "oczy", "ucho", "uszy", "nos", "usta", "wargi", "ząb", "zęby", "kły",
    "język", "broda", "wąsy", "włosy", "głowa", "czoło", "skroń", "szyja", "kark", "gardło",
    "ramię", "ramiona", "bark", "barki", "pierś", "piersi", "serce", "płuca", "brzuch", "bok",
    "boki", "plecy", "kręgosłup", "kość", "kości", "żebro", "żebra", "ręka", "ręce", "dłoń",
    "dłonie", "palec", "palce", "pięść", "pięści", "szpon", "szpony", "pazur", "pazury", "noga",
    "nogi", "udo", "uda", "kolano", "kolana", "łydka", "stopa", "stopy", "pięta", "krew",
    "posoka", "łza", "łzy", "pot", "ślina", "oddech", "tchnienie", "głos", "krzyk", "wrzask",
    "pisk", "szept", "uśmiech", "spojrzenie", "wzrok", "słuch", "węch", "dotyk", "smak", "ślad", "trop",

    # 9. Postacie pospolite, pokrewieństwo i status (48 słów)
    "człowiek", "lud", "naród", "tłum", "rzesza", "gromada", "zgraja", "wataha", "horda", "klan",
    "plemię", "ród", "rodzina", "ojciec", "matka", "brat", "siostra", "syn", "córka", "dziadek",
    "babka", "dziecko", "niemowlę", "starzec", "staruszka", "młodzieniec", "panna", "dziewczę", "chłopiec", "chłopak",
    "mąż", "żona", "pan", "pani", "król", "książę", "wódz", "wojownik", "rycerz", "strażnik",
    "wróg", "nieprzyjaciel", "druh", "przyjaciel", "towarzysz", "gość", "obcy", "cudzoziemiec", "tułacz", "wędrowiec",
    "pielgrzym", "jeniec", "niewolnik", "sługa", "panicz", "bękart", "podrzutek",

    # 10. Jednostki monetarne, miary i wagi historyczne (20 słów)
    "grosz", "dukat", "talar", "floren", "denar", "szeląg", "tynf", "złoty", "rubel", "marka",
    "łokieć", "sążeń", "mila", "wiorsta", "staja", "korzec", "kwarta", "pud", "funt", "cetnar",

    # 11. Kalendarz, pory i cykle kosmiczne (21 słów)
    "przedpołudnie", "popołudnie", "zmierzchanie", "nów", "pełnia", "kwadra", "zaćmienie", "przesilenie", "zrównanie",
    "styczeń", "luty", "marzec", "kwiecień", "maj", "czerwiec", "lipiec", "sierpień", "wrzesień", "październik", "listopad", "grudzień",

    # 12. Zjawiska meteorologiczne i wiatry (20 słów)
    "zawierucha", "zamieć", "kurniawa", "nawałnica", "szkwał", "orkan", "tajfun", "cyklon", "monsun", "tornado",
    "sztorm", "halny", "bryza", "zefir", "powiew", "zadymka", "chłód", "upał", "skwar", "spiekota",

    # 13. Formacje geologiczne i hydrologiczne (22 słowa)
    "rozpadlina", "zapadlisko", "grzęda", "żleb", "piarg", "usypisko", "osuwisko", "jastrzębica", "próg", "katarakta",
    "rozlewisko", "meander", "zakole", "dopływ", "starorzecze", "oparzelisko", "topiel", "topielisko", "grzęzawisko", "wydma", "ostęp", "uroczysko",

    # 14. Architektura obronna i militarna (19 słów)
    "palisada", "częstokół", "barbakan", "donżon", "fosa", "blanki", "strzelnica", "kurtyna", "rondel", "czatownia",
    "reduta", "kordegarda", "lazaret", "cekhauz", "arsenał", "mennica", "rogatka", "zamczysko", "strażnica"
}

def is_proper_noun_homonym(word: str) -> bool:
    """
    Determines whether a token is a common noun that frequently collides with proper names/titles.
    When matched, prevents aggressive capitalization or nominative freezing in dependent contexts.
    """
    if not word:
        return False
    return word.strip().lower() in POLISH_COMMON_NOUN_HOMONYMS

RE_FEMALE_ROLE = re.compile(
    r"\b(?:"
    # General / Base
    r"kobieta|kobiet[ayęieoó]|kobietami|kobietach|żeńsk[a-ząćęłńóśźż]*|female|dziewczyn[a-ząćęłńóśźż]*|"
    r"pani(?:ą|ej)?(?!\s*e\b)|bohaterk[a-ząćęłńóśźż]*|chatun|girl|woman|lady|sorceress|princess|heroine|priestess|witch|queen|empress|goddess|"
    # Rodzina (18) + Hipokorystyki i Oboczności (alternacje fonetyczne)
    r"matk[a-ząćęłńóśźż]*|mam[a-ząćęłńóśźż]*|mamusi[a-ząćęłńóśźż]*|mateńk[a-ząćęłńóśźż]*|córk[a-ząćęłńóśźż]*|córeczk[a-ząćęłńóśźż]*|córuni[a-ząćęłńóśźż]*|siostr[a-ząćęłńóśźż]*|siostrzyczk[a-ząćęłńóśźż]*|siostruni[a-ząćęłńóśźż]*|"
    r"bab(?:ka|ce|kę|ką|ki|ek|kom|kami|kach)|babci[a-ząćęłńóśźż]*|babuni[a-ząćęłńóśźż]*|prabab(?:ka|ce|kę|ką|ki|ek|kom|kami|kach)|prababci[a-ząćęłńóśźż]*|"
    r"wnuczk[a-ząćęłńóśźż]*|wnusi[a-ząćęłńóśźż]*|prawnuczk[a-ząćęłńóśźż]*|"
    r"ciot(?:ka|ce|kę|ką|ki|ek|kom|kami|kach)|wujenk[a-ząćęłńóśźż]*|stryjenk[a-ząćęłńóśźż]*|bratanic[a-ząćęłńóśźż]*|siostrzenic[a-ząćęłńóśźż]*|"
    r"teściow(?:a|ej|ą|o|e|ych|ym|ymi)\b|świekr[a-ząćęłńóśźż]*|synow(?:a|ej|ą|o|e|ych|ym|ymi)\b|szwagierk[a-ząćęłńóśźż]*|kuzynk[a-ząćęłńóśźż]*|"
    r"pasierbic[a-ząćęłńóśźż]*|macoch[a-ząćęłńóśźż]*|macosz[a-ząćęłńóśźż]*|"
    # Monarchia & Władza (22)
    r"królow(?:a|ej|ą|o|e|ych|ym|ymi)\b|królewn[a-ząćęłńóśźż]*|księżniczk[a-ząćęłńóśźż]*|księżn[a-ząćęłńóśźż]*|cesarzow(?:a|ej|ą|o|e|ych|ym|ymi)\b|"
    r"cesarzewn[a-ząćęłńóśźż]*|caryc[a-ząćęłńóśźż]*|carewn[a-ząćęłńóśźż]*|władczyn[a-ząćęłńóśźż]*|suwerenk[a-ząćęłńóśźż]*|"
    r"monarchin[a-ząćęłńóśźż]*|arcyksiężn[a-ząćęłńóśźż]*|wielmożn(?:a|ej|ą|e|ych|ym|ymi)\b|diuszes[a-ząćęłńóśźż]*|markiz[a-ząćęłńóśźż]*|"
    r"margrabin[a-ząćęłńóśźż]*|hrabin[a-ząćęłńóśźż]*|hrabiank[a-ząćęłńóśźż]*|wicehrabin[a-ząćęłńóśźż]*|baronow(?:a|ej|ą|o|e|ych|ym|ymi)\b|"
    r"baronówn[a-ząćęłńóśźż]*|szlachciank[a-ząćęłńóśźż]*|magnatk[a-ząćęłńóśźż]*|arystokratk[a-ząćęłńóśźż]*|"
    # Dwór & Służba (20)
    r"panienk[a-ząćęłńóśźż]*|pann[ayęe]|służąc(?:a|ej|ą|e|ych|ym|ymi)\b|pokojówk[a-ząćęłńóśźż]*|garderobian(?:a|ej|ą|e|ych|ym|ymi)\b|ochmistrzyn[a-ząćęłńóśźż]*|"
    r"woźniczk[a-ząćęłńóśźż]*|fornaliczk[a-ząćęłńóśźż]*|stajenn(?:a|ej|ą|e|ych|ym|ymi)\b|posługaczk[a-ząćęłńóśźż]*|ogrodniczk[a-ząćęłńóśźż]*|"
    r"kuchark[a-ząćęłńóśźż]*|pomywaczk[a-ząćęłńóśźż]*|szafark[a-ząćęłńóśźż]*|klucznic[a-ząćęłńóśźż]*|zarządczyn[a-ząćęłńóśźż]*|"
    r"dama\s+dworu|damy\s+dworu|damie\s+dworu|damą\s+dworu|dwórk[a-ząćęłńóśźż]*|niańk[a-ząćęłńóśźż]*|mamk[a-ząćęłńóśźż]*|"
    # Wojsko & Straż (35)
    r"żołnierk[a-ząćęłńóśźż]*|wojowniczk[a-ząćęłńóśźż]*|rycerk[a-ząćęłńóśźż]*|strażniczk[a-ząćęłńóśźż]*|wartowniczk[a-ząćęłńóśźż]*|"
    r"dowódczyn[a-ząćęłńóśźż]*|generałow(?:a|ej|ą|o|e|ych|ym|ymi)\b|generałk[a-ząćęłńóśźż]*|komendantk[a-ząćęłńóśźż]*|kapitank[a-ząćęłńóśźż]*|"
    r"oficerk[a-ząćęłńóśźż]*|poruczniczk[a-ząćęłńóśźż]*|podporuczniczk[a-ząćęłńóśźż]*|pułkowniczk[a-ząćęłńóśźż]*|podpułkowniczk[a-ząćęłńóśźż]*|"
    r"majork[a-ząćęłńóśźż]*|sierżantk[a-ząćęłńóśźż]*|kapralk[a-ząćęłńóśźż]*|szeregow(?:a|ej|ą|e|ych|ym|ymi)\b|kadetk[a-ząćęłńóśźż]*|rekrutk[a-ząćęłńóśźż]*|"
    r"hetmanow(?:a|ej|ą|o|e|ych|ym|ymi)\b|fechmistrzyn[a-ząćęłńóśźż]*|szermierk[a-ząćęłńóśźż]*|łuczniczk[a-ząćęłńóśźż]*|kuszniczk[a-ząćęłńóśźż]*|"
    r"włóczniczk[a-ząćęłńóśźż]*|tarczowniczk[a-ząćęłńóśźż]*|pikinierk[a-ząćęłńóśźż]*|zwiadowczyn[a-ząćęłńóśźż]*|kanonierk[a-ząćęłńóśźż]*|"
    r"saperk[a-ząćęłńóśźż]*|piechurk[a-ząćęłńóśźż]*|najemniczk[a-ząćęłńóśźż]*|obrończyn[a-ząćęłńóśźż]*|przywódczyn[a-ząćęłńóśźż]*|"
    # Religia & Magia (25)
    r"kapłank[a-ząćęłńóśźż]*|arcykapłank[a-ząćęłńóśźż]*|mniszk[a-ząćęłńóśźż]*|zakonnic[a-ząćęłńóśźż]*|opatk[a-ząćęłńóśźż]*|"
    r"przeorysz[a-ząćęłńóśźż]*|biskupk[a-ząćęłńóśźż]*|czarodziejk[a-ząćęłńóśźż]*|czarownic[a-ząćęłńóśźż]*|magini[a-ząćęłńóśźż]*|"
    r"arcymagini[a-ząćęłńóśźż]*|czarnoksiężnic[a-ząćęłńóśźż]*|nekromantk[a-ząćęłńóśźż]*|alchemiczk[a-ząćęłńóśźż]*|szamank[a-ząćęłńóśźż]*|"
    r"druidk[a-ząćęłńóśźż]*|guślark[a-ząćęłńóśźż]*|wiedźm[a-ząćęłńóśźż]*|wróżk[a-ząćęłńóśźż]*|wieszczk[a-ząćęłńóśźż]*|"
    r"prorokin[a-ząćęłńóśźż]*|zielark[a-ząćęłńóśźż]*|znachork[a-ząćęłńóśźż]*|zaklinaczk[a-ząćęłńóśźż]*|iluzjonistk[a-ząćęłńóśźż]*|egzorcystk[a-ząćęłńóśźż]*|"
    # Rzemiosło & Handel (30)
    r"kowalk[a-ząćęłńóśźż]*|karczmark[a-ząćęłńóśźż]*|szynkark[a-ząćęłńóśźż]*|oberżystk[a-ząćęłńóśźż]*|kupcow(?:a|ej|ą|o|e|ych|ym|ymi)\b|kupczyn[a-ząćęłńóśźż]*|"
    r"handlark[a-ząćęłńóśźż]*|kramark[a-ząćęłńóśźż]*|piekark[a-ząćęłńóśźż]*|cukierniczk[a-ząćęłńóśźż]*|rzeźniczk[a-ząćęłńóśźż]*|"
    r"krawcow(?:a|ej|ą|o|e|ych|ym|ymi)\b|szewcow(?:a|ej|ą|o|e|ych|ym|ymi)\b|stolark[a-ząćęłńóśźż]*|cieślin[a-ząćęłńóśźż]*|garncark[a-ząćęłńóśźż]*|"
    r"tkaczk[a-ząćęłńóśźż]*|garbark[a-ząćęłńóśźż]*|kuśnierk[a-ząćęłńóśźż]*|młynark[a-ząćęłńóśźż]*|rolniczk[a-ząćęłńóśźż]*|"
    r"wieśniaczk[a-ząćęłńóśźż]*|chłopk[a-ząćęłńóśźż]*|pasterk[a-ząćęłńóśźż]*|drwalk[a-ząćęłńóśźż]*|leśniczk[a-ząćęłńóśźż]*|"
    r"gajow(?:a|ej|ą|e|ych|ym|ymi)\b|rybaczk[a-ząćęłńóśźż]*|żeglark[a-ząćęłńóśźż]*|sterniczk[a-ząćęłńóśźż]*|"
    # Edukacja & Medycyna (15)
    r"nauczycielk[a-ząćęłńóśźż]*|profesork[a-ząćęłńóśźż]*|uczennic[a-ząćęłńóśźż]*|studentk[a-ząćęłńóśźż]*|wychowawczyn[a-ząćęłńóśźż]*|"
    r"lekark[a-ząćęłńóśźż]*|medyczk[a-ząćęłńóśźż]*|pielęgniark[a-ząćęłńóśźż]*|uzdrowicielk[a-ząćęłńóśźż]*|aptekark[a-ząćęłńóśźż]*|"
    r"sędzin[a-ząćęłńóśźż]*|urzędniczk[a-ząćęłńóśźż]*|namiestniczk[a-ząćęłńóśźż]*|kanclerzow(?:a|ej|ą|o|e|ych|ym|ymi)\b|skrybk[a-ząćęłńóśźż]*|"
    # Inne
    r"żon[a-ząćęłńóśźż]*|małżonk[a-ząćęłńóśźż]*|miko|szpieżk[a-ząćęłńóśźż]*"
    r")\b",
    re.IGNORECASE
)

RE_MALE_ROLE = re.compile(
    r"\b(?:"
    # General / Base
    r"mężczyzn[a-ząćęłńóśźż]*|męsk[a-ząćęłńóśźż]*|male|man|bocchan|hero|knight|prince|wizard|sorcerer|king|emperor|"
    r"chłop(?:ak[a-ząćęłńóśźż]*|iec|ca|cem|cu|cowi|cy|ców|om|ami|ach|a|em|u|i)?|boy|"
    r"młodzieniec|młodzieńc[a-ząćęłńóśźż]*|panie\b|pan(?:em|u|a|owie|ów)?\b|"
    # Rodzina (18) + Hipokorystyki i Oboczności
    r"ojc(?:iec|a|em|u|owi|owie|ów|om|ami|ach)|ojczulk[a-ząćęłńóśźż]*|tat[a-ząćęłńóśźż]*|tatk[a-ząćęłńóśźż]*|tatu(?:ś|si[a-ząćęłńóśźż]*)|"
    r"syn(?:[aeyu]|em|owi|owie|ów|om|ami|ach)?|synek\b|synk[a-ząćęłńóśźż]*|synu(?:ś|si[a-ząćęłńóśźż]*)|"
    r"brat(?:[aeyu]|em|owi|owie|ów|om|ami|ach)?|braci[a-ząćęłńóśźż]*|braciszk[a-ząćęłńóśźż]*|"
    r"dziad(?:ek|ka|kiem|kowi|kowie|ków|kom|kami|kach|[aeyu]|em|owi|owie|ów)?|dziadziu(?:ś|si[a-ząćęłńóśźż]*)|dziaduni[a-ząćęłńóśźż]*|"
    r"pradziad(?:ek|ka|kiem|kowi|kowie|ków|kom|kami|kach|[aeyu]|em|owi|owie|ów)?|"
    r"wnuk(?:[aeyu]|em|owi|owie|ów|om|ami|ach)?|wnuczk[a-ząćęłńóśźż]*|wnu(?:ś|si[a-ząćęłńóśźż]*)|prawnuk(?:[aeyu]|em|owi|owie|ów|om|ami|ach)?|"
    r"wuj(?:ek|ka|kiem|kowi|kowie|ków|kom|kami|kach|[aeyu]|em|owi|owie|ów)?|"
    r"stryj(?:ek|ka|kiem|kowi|kowie|ków|kom|kami|kach|[aeyu]|em|owi|owie|ów)?|bratan(?:ek|ka|kiem|kowi|kowie|ków|kom|kami|kach)|"
    r"siostrzeniec|siostrzeńc[a-ząćęłńóśźż]*|teść|teści(?:a|em|owi|owie|ów|om|ami|ach)|świekier(?:[aeyu]|em|owi|owie|ów)?|"
    r"zięć|zięci(?:a|em|owi|owie|ów|om|ami|ach)|szwagier|szwagr[a-ząćęłńóśźż]*|kuzyn(?:[aeyu]|em|owi|owie|ów|om|ami|ach)?|"
    r"pasierb(?:[aeyu]|em|owi|owie|ów|om|ami|ach)?|ojczym(?:[aeyu]|em|owi|owie|ów|om|ami|ach)?|"
    # Monarchia & Władza (22)
    r"król(?:a|em|owi|owie|ów)?(?!\s*ow[a-ząćęłńóśźż]*\b)|królewicz(?:[aeyu]|em|owi|owie|ów|om|ami|ach)?|"
    r"książ(?:ę|ęta|ąt)|księ(?:cia|ciem|ciu|ciom|ciami|ciach)|cesarz(?:[aeyu]|em|owi|owie|ów|om|ami|ach)?|cesarzewicz(?:[aeyu]|em|owi|owie|ów)?|"
    r"car(?:[aeyu]|em|owi|owie|ów|om|ami|ach)?(?!\s*(?:sk|yc|ew)[a-ząćęłńóśźż]*\b)|carewicz(?:[aeyu]|em|owi|owie|ów)?|władc(?:a|y|ę|ą|o|owie|ów|om|ami|ach)|suweren(?:[aeyu]|em|owi|owie|ów)?|"
    r"monarch[a-ząćęłńóśźż]*|arcyksiąż(?:ę|ęta|ąt)|arcyksię(?:cia|ciem|ciu|ciom|ciami|ciach)|wielmoż[a-ząćęłńóśźż]*|diuk(?:[aeyu]|em|owi|owie|ów)?|"
    r"markiz(?:[aeyu]|em|owi|owie|ów)?(?!\s*a\b)|margrabi[a-ząćęłńóśźż]*|hrabi[a-ząćęłńóśźż]*|hrabicz(?:[aeyu]|em|owi|owie|ów)?|"
    r"wicehrabi[a-ząćęłńóśźż]*|baron(?:[aeyu]|em|owi|owie|ów)?(?!\s*ow[a-ząćęłńóśźż]*\b)|szlachcic[a-ząćęłńóśźż]*|"
    r"magnat(?:[aeyu]|em|owi|owie|ów)?(?!\s*k[a-ząćęłńóśźż]*\b)|arystokrat[a-ząćęłńóśźż]*|"
    # Dwór & Służba (20)
    r"panicz[a-ząćęłńóśźż]*|służąc(?:y|ego|emu|ym|ych)|lokaj(?:[aeyu]|em|owi|owie|ów)?|kamerdyner[a-ząćęłńóśźż]*|majordomus[a-ząćęłńóśźż]*|"
    r"ochmistrz(?:[aeyu]|em|owi|owie|ów)?(?!\s*yn[a-ząćęłńóśźż]*\b)|stangret[a-ząćęłńóśźż]*|fornal(?:[aeyu]|em|owi|owie|ów)?(?!\s*iczk[a-ząćęłńóśźż]*\b)|stajenn(?:y|ego|emu|ym|ych)|pachoł(?:ek|ka|kiem|kowi|kowie|ków)|"
    r"parob(?:ek|ka|kiem|kowi|kowie|ków)|ogrodnik[a-ząćęłńóśźż]*|kucharz[a-ząćęłńóśźż]*|kuchcik[a-ząćęłńóśźż]*|szafarz[a-ząćęłńóśźż]*|"
    r"klucznik[a-ząćęłńóśźż]*|zarządc(?:a|y|ę|ą|o|owie|ów|om|ami|ach)|giermek[a-ząćęłńóśźż]*|pa(?:ź|zia|ziem|ziowi|ziom|ziowie|ziów|ziach|ziami)|samuraj[a-ząćęłńóśźż]*|"
    # Wojsko & Straż (35)
    r"żołnierz(?:[aeyu]|em|owi|owie|ów)?(?!\s*k[a-ząćęłńóśźż]*\b)|wojowni(?:k(?:a|em|owi|owie|ów)?(?!\s*czk[a-ząćęłńóśźż]*\b)|cy\b)|rycerz(?:[aeyu]|em|owi|owie|ów)?(?!\s*k[a-ząćęłńóśźż]*\b)|strażni(?:k(?:[aeyu]|em|owi|owie|ów)?(?!\s*czk[a-ząćęłńóśźż]*\b)|cy\b)|"
    r"wartowni(?:k(?:[aeyu]|em|owi|owie|ów)?(?!\s*czk[a-ząćęłńóśźż]*\b)|cy\b)|dowódc(?:a|y|ę|ą|o|owie|ów|om|ami|ach)|generał(?:[aeyu]|em|owi|owie|ów)?(?!\s*(?:k|ow)[a-ząćęłńóśźż]*\b)|komendant(?:[aeyu]|em|owi|owie|ów)?(?!\s*k[a-ząćęłńóśźż]*\b)|kapitan(?:[aeyu]|em|owi|owie|ów)?(?!\s*k[a-ząćęłńóśźż]*\b)|"
    r"oficer(?:[aeyu]|em|owi|owie|ów)?(?!\s*k[a-ząćęłńóśźż]*\b)|poruczni(?:k(?:[aeyu]|em|owi|owie|ów)?(?!\s*czk[a-ząćęłńóśźż]*\b)|cy\b)|podporuczni(?:k(?:[aeyu]|em|owi|owie|ów)?(?!\s*czk[a-ząćęłńóśźż]*\b)|cy\b)|pułkowni(?:k(?:[aeyu]|em|owi|owie|ów)?(?!\s*czk[a-ząćęłńóśźż]*\b)|cy\b)|podpułkowni(?:k(?:[aeyu]|em|owi|owie|ów)?(?!\s*czk[a-ząćęłńóśźż]*\b)|cy\b)|"
    r"major(?:[aeyu]|em|owi|owie|ów|om|ami|ach)?(?!\s*k[a-ząćęłńóśźż]*\b)|sierżant(?:[aeyu]|em|owi|owie|ów)?(?!\s*k[a-ząćęłńóśźż]*\b)|kapral(?:[aeyu]|em|owi|owie|ów)?(?!\s*k[a-ząćęłńóśźż]*\b)|szeregow(?:iec|ca|cem|cowi|cy|ców)|"
    r"kadet(?:[aeyu]|em|owi|owie|ów)?(?!\s*k[a-ząćęłńóśźż]*\b)|rekrut(?:[aeyu]|em|owi|owie|ów)?(?!\s*k[a-ząćęłńóśźż]*\b)|hetman(?:[aeyu]|em|owi|owie|ów)?(?!\s*ow[a-ząćęłńóśźż]*\b)|fechmistrz(?:[aeyu]|em|owi|owie|ów)?(?!\s*yn[a-ząćęłńóśźż]*\b)|szermierz(?:[aeyu]|em|owi|owie|ów)?(?!\s*k[a-ząćęłńóśźż]*\b)|"
    r"łuczni(?:k(?:[aeyu]|em|owi|owie|ów)?(?!\s*czk[a-ząćęłńóśźż]*\b)|cy\b)|kuszni(?:k(?:[aeyu]|em|owi|owie|ów)?(?!\s*czk[a-ząćęłńóśźż]*\b)|cy\b)|włóczni(?:k(?:[aeyu]|em|owi|owie|ów)?(?!\s*czk[a-ząćęłńóśźż]*\b)|cy\b)|tarczowni(?:k(?:[aeyu]|em|owi|owie|ów)?(?!\s*czk[a-ząćęłńóśźż]*\b)|cy\b)|pikinier(?:[aeyu]|em|owi|owie|ów)?(?!\s*k[a-ząćęłńóśźż]*\b)|"
    r"zwiadowc(?:a|y|ę|ą|o|owie|ów|om|ami|ach)|kanonier(?:[aeyu]|em|owi|owie|ów)?(?!\s*k[a-ząćęłńóśźż]*\b)|saper(?:[aeyu]|em|owi|owie|ów)?(?!\s*k[a-ząćęłńóśźż]*\b)|piechur(?:[aeyu]|em|owi|owie|ów)?(?!\s*k[a-ząćęłńóśźż]*\b)|najemni(?:k(?:[aeyu]|em|owi|owie|ów)?(?!\s*czk[a-ząćęłńóśźż]*\b)|cy\b)|"
    r"obrońc(?:a|y|ę|ą|o|owie|ów|om|ami|ach)|wódz|wodz(?:a|em|owi|owie|ów|om|ami|ach)|kat(?:[aeyu]|em|owi|owie|ów|om|ami|ach)?(?!\s*egor[a-ząćęłńóśźż]*\b)|kac(?:i|ie)|"
    # Religia & Magia (25)
    r"kapłan(?:[aeyu]|em|owi|owie|ów)?(?!\s*k[a-ząćęłńóśźż]*\b)|arcykapłan(?:[aeyu]|em|owi|owie|ów)?(?!\s*k[a-ząćęłńóśźż]*\b)|mnich[a-ząćęłńóśźż]*|mnisi\b|zakonnik(?:[aeyu]|em|owi|owie|ów)?(?!\s*k[a-ząćęłńóśźż]*\b)|"
    r"opat(?:[aeyu]|em|owi|owie|ów|om|ami|ach)?(?!\s*k[a-ząćęłńóśźż]*\b)|przeor(?:[aeyu]|em|owi|owie|ów)?(?!\s*ysz[a-ząćęłńóśźż]*\b)|biskup(?:[aeyu]|em|owi|owie|ów)?(?!\s*k[a-ząćęłńóśźż]*\b)|czarodziej(?:[aeyu]|em|owi|owie|ów)?(?!\s*k[a-ząćęłńóśźż]*\b)|"
    r"czarownik(?:[aeyu]|em|owi|owie|ów)?(?!\s*k[a-ząćęłńóśźż]*\b)|mag(?:[aeyu]|iem|owi|owie|ów|om|ami|ach)?(?!\s*in[a-ząćęłńóśźż]*\b)|madz(?:e|y)|arcymag(?:[aeyu]|iem|owi|owie|ów)?(?!\s*in[a-ząćęłńóśźż]*\b)|czarnoksiężnik(?:[aeyu]|em|owi|owie|ów)?(?!\s*k[a-ząćęłńóśźż]*\b)|"
    r"nekromant(?:a|y|ę|ą|o|ów|om|ami|ach)(?!\s*k[a-ząćęłńóśźż]*\b)|alchemik(?:[aeyu]|em|owi|owie|ów)?(?!\s*czk[a-ząćęłńóśźż]*\b)|szaman(?:[aeyu]|em|owi|owie|ów)?(?!\s*k[a-ząćęłńóśźż]*\b)|druid(?:[aeyu]|em|owi|owie|ów)?(?!\s*k[a-ząćęłńóśźż]*\b)|guślarz(?:[aeyu]|em|owi|owie|ów)?(?!\s*k[a-ząćęłńóśźż]*\b)|"
    r"wróżbit(?:a|y|ę|ą|o|ów|om|ami|ach)|wieszcz(?:[aeyu]|em|owi|owie|ów)?(?!\s*k[a-ząćęłńóśźż]*\b)|prorok(?:[aeyu]|em|owi|owie|ów)?(?!\s*in[a-ząćęłńóśźż]*\b)|zielarz(?:[aeyu]|em|owi|owie|ów)?(?!\s*k[a-ząćęłńóśźż]*\b)|znachor(?:[aeyu]|em|owi|owie|ów)?(?!\s*k[a-ząćęłńóśźż]*\b)|"
    r"zaklinacz(?:[aeyu]|em|owi|owie|ów)?(?!\s*k[a-ząćęłńóśźż]*\b)|iluzjonist(?:a|y|ę|ą|o|ów|om|ami|ach)(?!\s*k[a-ząćęłńóśźż]*\b)|egzorcyst(?:a|y|ę|ą|o|ów|om|ami|ach)(?!\s*k[a-ząćęłńóśźż]*\b)|"
    # Rzemiosło & Handel (30)
    r"kowal(?:[aeyu]|em|owi|owie|ów)?(?!\s*k[a-ząćęłńóśźż]*\b)|karczmarz(?:[aeyu]|em|owi|owie|ów)?(?!\s*k[a-ząćęłńóśźż]*\b)|szynkarz(?:[aeyu]|em|owi|owie|ów)?(?!\s*k[a-ząćęłńóśźż]*\b)|oberżyst(?:a|y|ę|ą|o|ów|om|ami|ach)(?!\s*k[a-ząćęłńóśźż]*\b)|kupiec|kupc(?:a|em|owi|owie|ów|om|ami|ach)(?!\s*k[a-ząćęłńóśźż]*\b)|"
    r"handlarz(?:[aeyu]|em|owi|owie|ów)?(?!\s*k[a-ząćęłńóśźż]*\b)|kramarz(?:[aeyu]|em|owi|owie|ów)?(?!\s*k[a-ząćęłńóśźż]*\b)|piekarz(?:[aeyu]|em|owi|owie|ów)?(?!\s*k[a-ząćęłńóśźż]*\b)|cukiernik(?:[aeyu]|em|owi|owie|ów)?(?!\s*czk[a-ząćęłńóśźż]*\b)|rzeźnik(?:[aeyu]|em|owi|owie|ów)?(?!\s*czk[a-ząćęłńóśźż]*\b)|"
    r"krawiec|krawc(?:a|em|u|owi|owie|ów|om|ami|ach)(?!\s*ow[a-ząćęłńóśźż]*\b)|szewc(?:[aeyu]|em|owi|owie|ów)?(?!\s*ow[a-ząćęłńóśźż]*\b)|stolarz(?:[aeyu]|em|owi|owie|ów)?(?!\s*k[a-ząćęłńóśźż]*\b)|cieśl(?:a|i|ę|ą|o|om|ami|ach)(?!\s*in[a-ząćęłńóśźż]*\b)|garncarz(?:[aeyu]|em|owi|owie|ów)?(?!\s*k[a-ząćęłńóśźż]*\b)|"
    r"tkacz(?:[aeyu]|em|owi|owie|ów)?(?!\s*k[a-ząćęłńóśźż]*\b)|garbarz(?:[aeyu]|em|owi|owie|ów)?(?!\s*k[a-ząćęłńóśźż]*\b)|kuśnierz(?:[aeyu]|em|owi|owie|ów)?(?!\s*k[a-ząćęłńóśźż]*\b)|młynarz(?:[aeyu]|em|owi|owie|ów)?(?!\s*k[a-ząćęłńóśźż]*\b)|rolnik(?:[aeyu]|em|owi|owie|ów)?(?!\s*czk[a-ząćęłńóśźż]*\b)|"
    r"wieśniak(?:[aeyu]|em|owi|owie|ów)?(?!\s*czk[a-ząćęłńóśźż]*\b)|pasterz(?:[aeyu]|em|owi|owie|ów)?(?!\s*k[a-ząćęłńóśźż]*\b)|drwal(?:[aeyu]|em|owi|owie|ów)?(?!\s*k[a-ząćęłńóśźż]*\b)|leśnik(?:[aeyu]|em|owi|owie|ów)?(?!\s*czk[a-ząćęłńóśźż]*\b)|gajow(?:y|ego|emu|ym|ych)(?!\s*a\b)|"
    r"rybak(?:[aeyu]|em|owi|owie|ów)?(?!\s*czk[a-ząćęłńóśźż]*\b)|marynarz(?:[aeyu]|em|owi|owie|ów)?(?!\s*k[a-ząćęłńóśźż]*\b)|żeglarz(?:[aeyu]|em|owi|owie|ów)?(?!\s*k[a-ząćęłńóśźż]*\b)|sternik(?:[aeyu]|em|owi|owie|ów)?(?!\s*czk[a-ząćęłńóśźż]*\b)|"
    # Edukacja & Medycyna (15)
    r"nauczyciel(?:[aeyu]|em|owi|owie|ów)?(?!\s*k[a-ząćęłńóśźż]*\b)|profesor(?:[aeyu]|em|owi|owie|ów)?(?!\s*k[a-ząćęłńóśźż]*\b)|uczeń|uczni(?:a|em|owi|owie|ów|om|ami|ach)|student(?:[aeyu]|em|owi|owie|ów)?(?!\s*k[a-ząćęłńóśźż]*\b)|wychowawc(?:a|y|ę|ą|o|owie|ów|om|ami|ach)|"
    r"lekarz(?:[aeyu]|em|owi|owie|ów)?(?!\s*k[a-ząćęłńóśźż]*\b)|medyk(?:[aeyu]|em|owi|owie|ów)?(?!\s*czk[a-ząćęłńóśźż]*\b)|pielęgniarz(?:[aeyu]|em|owi|owie|ów)?(?!\s*k[a-ząćęłńóśźż]*\b)|uzdrowiciel(?:[aeyu]|em|owi|owie|ów)?(?!\s*k[a-ząćęłńóśźż]*\b)|aptekarz(?:[aeyu]|em|owi|owie|ów)?(?!\s*k[a-ząćęłńóśźż]*\b)|"
    r"sędzi(?:a|ego|emu|ą|owie|ów|om|ami|ach)|urzędnik(?:[aeyu]|em|owi|owie|ów)?(?!\s*czk[a-ząćęłńóśźż]*\b)|namiestnik(?:[aeyu]|em|owi|owie|ów)?(?!\s*czk[a-ząćęłńóśźż]*\b)|kanclerz(?:[aeyu]|em|owi|owie|ów)?(?!\s*ow[a-ząćęłńóśźż]*\b)|skryb(?:a|y|ie|ę|ą|o|owie|ów|om|ami|ach)(?!\s*k[a-ząćęłńóśźż]*\b)|"
    # Inne & Posłowie, Karły, Aniołowie, Diabły
    r"lord[a-ząćęłńóśźż]*|wasal[a-ząćęłńóśźż]*|buke|kuge|dostojnik[a-ząćęłńóśźż]*|"
    r"poseł\b|posł(?:a|em|owi|owie|ów|om|ami|ach)\b|karzeł\b|karł(?:a|em|owi|owie|ów|om|ami|ach)\b|"
    r"diabeł\b|diabł(?:a|em|owi|owie|ów|om|ami|ach)\b|diabli\b|anioł(?:[aeyu]|em|owi|owie|ów)?\b|aniel(?:i|e)\b"
    r")\b",
    re.IGNORECASE
)

def is_female_role_text(text: str) -> bool:
    if not text:
        return False
    return bool(RE_FEMALE_ROLE.search(text))

def is_male_role_text(text: str) -> bool:
    if not text:
        return False
    return bool(RE_MALE_ROLE.search(text))

def is_plural_actor(name: str) -> bool:
    """
    Determines whether an actor/speaker represents a plural group or collective
    (e.g. 'Guards', 'Strażnicy', 'Villagers', 'Wieśniacy', 'Dziewczęta', 'Chłopcy').
    """
    if not name:
        return False
    clean = extract_clean_speaker_name(name).strip().lower()
    if not clean:
        return False
    tokens = set(re.findall(r"\b[a-ząćęłńóśźżA-ZĄĆĘŁŃÓŚŹŻ]+\b", clean))
    if any(t in INHERENT_PLURAL_NOUNS for t in tokens):
        return True
    if clean.startswith(("grupa", "oddział", "tłum", "kompania", "patrol", "banda", "crew", "squad")):
        return True
    return False

# -------------------------------------------------------------------------
# Klaster C & D: Heurystyki Onomastyczne, Bramka Instytucjonalna i Dwupoziomowa Blokada (0.00 PLN)
# -------------------------------------------------------------------------
INSTITUTION_NOUNS: Set[str] = {
    "biuro", "miasto", "królestwo", "cesarstwo", "księstwo", "imperium",
    "ministerstwo", "centrum", "laboratorium", "archiwum", "dowództwo"
}

INSTITUTIONAL_SUFFIXES: Tuple[str, ...] = ("stwo", "ctwo", "sko")

ORIGIN_GROUP_NOUNS_PATTERN: str = (
    r"(?:ludzie|ci|tamci|agenci|pracownicy|oddział|oddziały|goście|koledzy|szef|"
    r"żołnierze|żołnierz|rycerze|rycerz|wojska|posłowie|posłaniec|przybysze|wojownicy|armia|"
    r"zbieg|uciekinierzy|ucieczka|chłopak[a-ząćęłńóśźż]*|dziewczyn[a-ząćęłńóśźż]*|"
    r"ucze[ńn][a-ząćęłńóśźż]*|uczennic[a-ząćęłńóśźż]*|akademia|wieści|wieść)"
)

ABLATIVE_MOTION_VERBS_PATTERN: str = (
    r"(?:dotarli|dotarł|dotarła|docierają|"
    r"przybyli|przybył|przybyła|przybywa|przybywają|"
    r"wrócili|wrócił|wróciła|wraca|wracają|wracał|wracała|"
    r"przyszli|przyszedł|przyszła|przychodzą|"
    r"wyszli|wyszedł|wyszła|wychodzą|"
    r"pochodzą|pochodzi|pochodził|pochodziła|"
    r"dzwonią|dzwoni|dzwonił|dzwoniła|"
    r"uciekli|uciekł|uciekła|uciekają)"
)

JAPANESE_MALE_NAME_SUFFIXES: Tuple[str, ...] = (
    "nosuke", "shirou", "tarou", "jirou", "yoshi", "hiko",
    "suke", "maru", "zou", "hito", "masa", "nobu", "taka",
    "rou", "ichi", "aki", "taro", "jiro", "shiro", "zo"
)

OFFICIAL_COURT_CONSONANT_SUFFIXES: Tuple[str, ...] = (
    "er", "el", "on", "an", "ard", "olf"
)

OFFICIAL_COURT_TITLES_AND_ROLES: Set[str] = {
    "minister", "kanclerz", "sędzia", "prefekt", "hrabia", "baron", "margrabia",
    "wicehrabia", "książę", "radca", "namiestnik", "urzędnik", "dworzanin", "herold",
    "konsul", "komendant", "lord", "sir", "szambelan", "marszałek", "sekretarz",
    "prezes", "dyrektor", "oficer", "kapitan", "generał", "komisarz", "poseł",
    "ambasador", "trybun", "archont", "kanclerka", "magistrate", "chancellor",
    "judge", "count", "duke", "inspector", "courtier", "bureaucrat", "nobleman",
    "official", "governor", "premier", "prezydent", "burmistrz", "kasztelan"
}


def has_japanese_male_name_suffix(name: str) -> bool:
    """
    Wyprowadza heurystykę onomastyczną dla imion japońskich:
    imiona lub tokeny kończące się na:
    -yoshi, -hiko, -rou, -tarou, -jirou, -shirou, -ichi, -suke, -maru, -nosuke, -zou, -hito, -masa, -nobu, -taka, -aki
    otrzymują silny wektor MALE.
    """
    if not name:
        return False
    w = normalize_name_nfkd(name).lower()
    if w in INVARIABLE_JAPANESE_FEMALE_NAMES or w in UNIVERSAL_FEMALE_NAMES_ON_A or w in POLISH_FEMALE_NAMES:
        return False
    tokens = [t.strip("-") for t in re.split(r"[\s_/-]+", w) if t.strip("-")]
    for t in tokens:
        if len(t) < 4 or t in INVARIABLE_JAPANESE_FEMALE_NAMES:
            continue
        for suf in JAPANESE_MALE_NAME_SUFFIXES:
            if t.endswith(suf) and len(t) >= len(suf) + 2:
                return True
    return False


def is_official_or_court_consonant_name(name: str, context: Optional[str] = None, series_bible: Optional[Any] = None) -> bool:
    """
    Weryfikuje, czy postać posiada nazwisko spółgłoskowe na -er, -el, -on, -an, -ard, -olf
    w rejestrach urzędowych/dworskich (lub poprzedzona jest tytułem urzędowym/dworskim).
    Takie postacie nie mogą domyślnie otrzymywać płci żeńskiej.
    """
    if not name:
        return False
    clean = re.sub(r"[\(\[].*?[\)\]]", "", re.split(r"[\\\/]", str(name))[0])
    clean = re.sub(r"[\(\[].*$", "", clean).strip().lower()
    clean_norm = normalize_name_nfkd(clean).lower()
    tokens = [t for t in re.split(r"[\s_/-]+", clean_norm) if t]
    if not tokens:
        return False

    surname = tokens[-1]
    has_consonant_suffix = any(surname.endswith(suf) for suf in OFFICIAL_COURT_CONSONANT_SUFFIXES) and len(surname) >= 3
    if not has_consonant_suffix:
        return False

    if any(t in OFFICIAL_COURT_TITLES_AND_ROLES for t in tokens):
        return True

    if context:
        ctx_lower = context.lower()
        if any(role in ctx_lower for role in OFFICIAL_COURT_TITLES_AND_ROLES) or any(kw in ctx_lower for kw in ["urząd", "dwór", "rejestr", "court", "official", "magistrat", "pałac", "rada"]):
            return True

    if series_bible and hasattr(series_bible, "data") and isinstance(series_bible.data, dict):
        chars = series_bible.data.get("characters", {})
        for k, v in chars.items():
            k_norm = normalize_name_nfkd(k).lower()
            if k_norm == clean_norm or clean_norm in k_norm.split():
                desc = str(v.get("description", "") if isinstance(v, dict) else v).lower()
                if any(role in desc for role in OFFICIAL_COURT_TITLES_AND_ROLES) or any(kw in desc for kw in ["urząd", "dwór", "rejestr", "court", "official", "magistrat", "minister", "sędzia", "prefekt", "hrabia"]):
                    return True

    return False


def resolve_actor_gender(name: str, character_registry: Optional[Dict[str, Any]] = None, series_bible: Optional[Any] = None) -> str:
    """
    Determines actor gender ('MALE', 'FEMALE', 'PLURAL', or 'UNKNOWN') deterministically (0.00 PLN).
    Accurately processes named characters, generic/numbered actor tags, and plural collective actors.
    """
    if not name:
        return "UNKNOWN"
    clean = extract_clean_speaker_name(name).strip()
    if not clean:
        return "UNKNOWN"
    clean_lower = clean.lower()

    # 0. Check for plural/collective actors first
    if is_plural_actor(clean):
        return "PLURAL"

    # 0b. Canonical inheritance for age, temporal, and state prefixes
    base_char_name = extract_base_canonical_name(clean)
    if base_char_name and base_char_name.lower() != clean_lower:
        if series_bible and hasattr(series_bible, "get_character_identity"):
            base_ident = series_bible.get_character_identity(base_char_name)
            if base_ident:
                return "MALE" if base_ident.true_gender == "MASCULINE" else "FEMALE"
        bg = resolve_actor_gender(base_char_name, character_registry=character_registry, series_bible=series_bible)
        if bg in ("MALE", "FEMALE"):
            return bg

    # 0c. Relational resolving ([Owner]'s [Relation])
    rel_gender, rel_conf = resolve_possessive_relation_gender(
        name,
        is_flashback=any(fb in name.lower() for fb in ("flashback", "retrospekcj", "past")),
        series_bible=series_bible
    )
    if rel_gender in ("MALE", "FEMALE"):
        return rel_gender

    # 1. Direct character registry lookup if provided
    if character_registry:
        c_val = None
        if clean in character_registry:
            c_val = character_registry[clean]
        else:
            clean_norm = normalize_name_nfkd(clean).lower()
            for r_k, r_v in character_registry.items():
                if r_k.lower() == clean_lower or normalize_name_nfkd(r_k).lower() == clean_norm:
                    c_val = r_v
                    break
        if c_val is not None:
            c_desc = (c_val.get("gender", "") or c_val.get("description", "") or c_val.get("role", "")) if isinstance(c_val, dict) else str(c_val)
            c_desc_l = c_desc.lower()
            if "female" in c_desc_l or "kobieta" in c_desc_l or "żeńsk" in c_desc_l:
                return "FEMALE"
            if "male" in c_desc_l or "mężczyzna" in c_desc_l or "męsk" in c_desc_l:
                return "MALE"

    # 2. Series Bible lookup if provided
    if series_bible and hasattr(series_bible, "get_character_gender"):
        bg = series_bible.get_character_gender(clean, allow_generic_nouns=True)
        if bg in ("MALE", "FEMALE"):
            return bg

    # 3. Canonical name sets
    if clean_lower in CANONICAL_MALE_NAMES or clean_lower in MALE_EXCEPTIONS_ON_A:
        return "MALE"
    if clean_lower in POLISH_FEMALE_NAMES:
        return "FEMALE"

    # 4. Role & Lexical tokens with strict word boundaries
    tokens = set(re.findall(r"\b[a-ząćęłńóśźżA-ZĄĆĘŁŃÓŚŹŻ]+\b", clean_lower))
    if any(t in INHERENT_FEMALE_NOUNS for t in tokens) or is_female_role_text(clean):
        return "FEMALE"
    if any(t in INHERENT_MALE_NOUNS for t in tokens) or is_male_role_text(clean):
        return "MALE"

    # 4b. Japanese male name suffixes heuristic (Klaster D)
    if has_japanese_male_name_suffix(clean):
        return "MALE"

    # 4c. Consonant surnames in official/court registers cannot default to FEMALE (Klaster D)
    if is_official_or_court_consonant_name(clean, series_bible=series_bible):
        return "MALE"

    # 5. Onomastic heuristics
    if is_inherently_female_name(clean, series_bible=series_bible):
        return "FEMALE"

    return "UNKNOWN"


def _load_dynamic_boy_keywords() -> List[str]:
    keywords = [
        "chłopiec", "chłopak", "boy", "syn", "młodzieniec", "książę",
        "dziecko płci męskiej", "pax", "bocchan", "crossgender", "cross-gender", "seiyū żeński", "żeńskie seiyū",
        "uczeń", "schoolboy", "lad", "kid", "shōnen", "shonen", "brat", "brother", "wnuk", "grandson",
        "10 lat", "dziedzic", "panicz", "młody pan", "waka", "wakagimi", "waka-sama"
    ]
    try:
        bible_dir = Path(__file__).parent / "series_memory"
        if bible_dir.exists():
            for p in bible_dir.glob("*_bible.json"):
                try:
                    with open(p, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    for c_k, c_v in data.get("characters", {}).items():
                        if "->" in c_k:
                            continue
                        desc = c_v.get("description", "") if isinstance(c_v, dict) else str(c_v)
                        d_l = desc.lower()
                        g = c_v.get("gender", "") if isinstance(c_v, dict) else ""
                        is_male = (g == "MALE") or ("[mężczyzna" in d_l)
                        if is_male and any(w in d_l for w in ["chłopiec", "chłopak", "10 lat", "panicz", "chłopięc", "dziedzic"]):
                            for tok in re.findall(r"[a-zA-Z\u0100-\u017F]+", c_k.lower()):
                                if len(tok) >= 4 and tok not in keywords:
                                    keywords.append(tok)
                    for r_k, r_v in data.get("relationships", {}).items():
                        if "->" in r_k:
                            r_desc = r_v.get("description", "") if isinstance(r_v, dict) else str(r_v)
                            r_l = r_desc.lower()
                            if any(w in r_l for w in ["chłopiec", "chłopak", "10 lat", "panicz", "chłopięc", "dziedzic", "młody pan", "wakagimi"]):
                                for cand_p in r_k.split("->"):
                                    cand_clean = cand_p.split("(")[0].split("/")[0].strip().lower()
                                    if cand_clean and cand_clean in r_l:
                                        for tok in re.findall(r"[a-zA-Z\u0100-\u017F]+", cand_clean):
                                            if len(tok) >= 4 and tok not in keywords:
                                                keywords.append(tok)
                except Exception:
                    logger.warning("Ekstrakcja słów kluczowych encji zakończona wyjątkiem", exc_info=True)
    except Exception:
        logger.warning("Ekstrakcja słów kluczowych leksykonu zakończona wyjątkiem", exc_info=True)
    return keywords


BOY_ROLE_KEYWORDS = _load_dynamic_boy_keywords()
SECONDARY_LEXICAL_MALE_NOUNS: Set[str] = {
    "boy", "man", "men", "guy", "male", "father", "dad", "brother", "son",
    "uncle", "grandfather", "waiter", "king", "prince", "lord",
    "chłopiec", "mężczyzna", "chłopak", "ojciec", "brat"
}

SECONDARY_LEXICAL_FEMALE_NOUNS: Set[str] = {
    "girl", "woman", "women", "lady", "female", "mother", "mom", "sister",
    "daughter", "aunt", "grandmother", "waitress", "queen", "princess",
    "dziewczyna", "kobieta", "dziewczynka", "matka", "siostra"
}

def resolve_lexical_label_gender(label: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Deterministyczny resolver inherentnej płci leksykalnej dla etykiet ról i grup (Standard 10.0.3, 2B.4):
    Rozpoznaje polskie i angielskie leksemy męskie i żeńskie w etykietach mówców i adresatów,
    zarówno w liczbie pojedynczej, jak i mnogiej/zbiorowej w relacji do ról syntaktycznych.
    Zwraca: (gender, grammatical_gender), np. ('MALE', 'MASCULINE') lub ('FEMALE', 'FEMININE').
    """
    if not label:
        return (None, None)
    clean_lbl, explicit_g = normalize_actor_tag(str(label))
    clean_lbl = extract_clean_speaker_name(clean_lbl).strip()
    if not clean_lbl:
        return (None, None)
    if explicit_g in ("MALE", "FEMALE"):
        return (explicit_g, "MASCULINE" if explicit_g == "MALE" else "FEMININE")

    l_low = clean_lbl.lower()
    words = re.findall(r"\b[a-ząćęłńóśźżA-ZĄĆĘŁŃÓŚŹŻ0-9]+\b", l_low)
    if not words:
        return (None, None)

    # 1. Sprawdzenie grup i fraz wielowyrazowych
    MALE_GROUP_PHRASES = {
        "grupa mężczyzn", "grupa mezczyzn", "dwóch mężczyzn", "dwoch mezczyzn", "dwaj mężczyźni",
        "trzech mężczyzn", "czterech mężczyzn", "panowie", "mężczyźni", "mezczyzni", "mężczyzn", "mezczyzn",
        "men", "group of men", "two men", "boys", "group of boys"
    }
    FEMALE_GROUP_PHRASES = {
        "grupa kobiet", "dwie kobiety", "trzy kobiety", "cztery kobiety", "panie", "kobiety", "kobiet",
        "women", "group of women", "two women", "girls", "group of girls"
    }
    for mg in MALE_GROUP_PHRASES:
        if mg in l_low:
            return ("MALE", "MASCULINE")
    for fg in FEMALE_GROUP_PHRASES:
        if fg in l_low:
            return ("FEMALE", "FEMININE")

    # 2. Głowa składniowa wielowyrazowych ról syntaktycznych
    head_word = words[0]
    head_stems_male = {
        "mężczyzna", "mezczyzna", "chłopak", "chlopak", "chłopiec", "chlopiec", "facet", "pan", "ojciec",
        "syn", "brat", "dziadek", "wuj", "wujek", "strażnik", "straznik", "mieszkaniec", "żołnierz", "zolnierz",
        "wojownik", "rycerz", "bandyta", "zbój", "zboj", "złodziej", "zlodziej", "kupiec", "dowódca", "dowodca",
        "oficer", "kapitan", "generał", "general", "król", "krol", "książę", "ksiaze", "lord",
        "man", "boy", "guy", "father", "son", "brother", "guard", "soldier", "bandit", "warrior", "knight",
        "king", "prince", "citizen", "resident", "merchant"
    }
    head_stems_female = {
        "kobieta", "dziewczyna", "dziewczynka", "pani", "matka", "córka", "corka", "siostra", "babcia",
        "ciotka", "strażniczka", "strazniczka", "mieszkanka", "wojowniczka", "rycerka", "bandytka",
        "złodziejka", "zlodziejka", "kupcowa", "królowa", "kroloawa", "księżniczka", "ksiezniczka", "lady",
        "woman", "girl", "mother", "daughter", "sister", "queen", "princess"
    }

    if head_word in head_stems_male or head_word in INHERENT_MALE_NOUNS or head_word in SECONDARY_LEXICAL_MALE_NOUNS:
        return ("MALE", "MASCULINE")
    if head_word in head_stems_female or head_word in INHERENT_FEMALE_NOUNS or head_word in SECONDARY_LEXICAL_FEMALE_NOUNS:
        return ("FEMALE", "FEMININE")

    # 3. Sprawdzenie obecności tokenów w słownikach inherentnych
    words_set = set(words)
    if words_set & head_stems_male or words_set & INHERENT_MALE_NOUNS or words_set & SECONDARY_LEXICAL_MALE_NOUNS:
        return ("MALE", "MASCULINE")
    if words_set & head_stems_female or words_set & INHERENT_FEMALE_NOUNS or words_set & SECONDARY_LEXICAL_FEMALE_NOUNS:
        return ("FEMALE", "FEMININE")

    return (None, None)



GENERIC_CATEGORY_TAGS = {
    # Polish technical & crowd tags
    "mężczyzna", "mezczyzna", "kobieta", "grupa_kobiet", "grupa_mężczyzn", "grupa_mezczyzn",
    "grupa_mieszana", "brak", "narrator", "głos", "glos", "ktoś", "ktos", "nikt", "wszyscy",
    "tłum", "tlum", "napis", "napisy", "tytuł", "tytul", "tłumaczenie", "tlumaczenie",
    "postać", "postac", "interlokutor", "obcy", "nieznajomy", "grupa", "rozmówca", "tło", "tlo",
    # English technical & crowd tags
    "main", "default", "alt", "sign", "signs", "crowd", "voice", "voices", "unknown", "none",
    "all", "everyone", "somebody", "someone", "nobody", "narration", "caption", "captions",
    "title", "titles", "subtitle", "subtitles", "translation", "background", "mob", "people",
    "bystander", "bystanders", "audience", "spectators", "person", "character", "speaker",
    "caller", "announcer"
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
    "ada", "adriana", "anastazja", "apolonia", "aurelia", "bernadeta", "blanka",
    "dagmara", "dobrawa", "dobrochna", "eleonora", "eliza", "eugenia", "faustyna",
    "florentyna", "franciszka", "gabriela", "gaja", "gertruda", "gizela", "honorata",
    "hortensja", "inga", "irmina", "izolda", "jagienka", "klementyna", "konstancja",
    "kordelia", "krystiana", "leokadia", "lilianna", "liwia", "ludmiła", "luiza",
    "marcelina", "matylda", "melania", "michalina", "mirosława", "nadzieja", "noemi",
    "otylia", "pelagia", "petronela", "rozalia", "róża", "roza", "salomea", "seweryna",
    "sławomira", "slawomira", "sydonia", "sybilla", "tekla", "teodora", "waleria",
    "wiola", "wirginia",
    # Hypocoristics and popular variants (for vocative conversion)
    "kasia", "basia", "asia", "ania", "ola", "gosia", "madzia", "zosia",
    "marysia", "natalka", "julka", "krysia", "danka", "ala", "magda",
    "agatka", "agnisia", "agusia", "anetka", "andzia", "anitka", "anka", "anusia",
    "tosia", "tośka", "beatka", "bogusia", "celinka", "domisia", "dorotka", "edytka",
    "ela", "elka", "elunia", "emilka", "ewka", "ewunia", "halka", "halinka", "helka",
    "helenka", "iza", "izka", "jadzia", "jadźka", "joasia", "aśka", "juleczka",
    "justynka", "kamilka", "karolka", "kaśka", "kasiunia", "kingusia", "kryśka",
    "lucynka", "łucka", "lucka", "madźka", "gośka", "małgośka", "malgoska", "maryśka",
    "marychna", "martka", "martusia", "martynka", "marzenka", "monia", "moniczka",
    "natka", "oliwka", "paulinka", "renatka", "roksa", "sylwka", "terenia", "tesia",
    "ula", "ulka", "ulusia", "werka", "weronisia", "wika", "wikusia", "wiolka",
    "zośka", "zosieńka", "zuzia", "zuza", "zuźka", "zuzka",
    "tusia", "lusia", "dusia", "stasia", "frania", "mania", "danusia", "halszka"
}

MALE_EXCEPTIONS_ON_A = {
    "kuba", "barnaba", "kosma", "bonawentura", "jarema", "zawisza",
    "sasza", "mustafa", "joshua", "akira", "luka", "luca",
    "shira", "gaara", "kiba", "soma", "kenta", "ryoma", "hanza", "koba", "soya",
    "toma", "genga", "seneca", "kaligula", "sparta", "spinoza", "buddha", "budda",
    "dante", "petrarka", "torquemada", "zapata", "garcia", "elijah", "noah", "ezra",
    "micah", "hosea", "jeremiah", "jonah", "isaiah", "sasha", "misha", "ilja", "kolja",
    "wania", "alosza", "foma", "grisha", "toya", "shota", "souta", "kota", "shouta",
    "yuuta", "yuta", "renga", "hakuya", "byakuya", "genya", "katsura"
}

CANONICAL_MALE_NAMES_ON_A = MALE_EXCEPTIONS_ON_A

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

INDECLINABLE_FRENCH_TOPONYMS = {
    "bordeaux", "margaux", "calais", "meaux", "pau", "chamonix", "angers", "versailles", "reims", "brest", "nantes"
}

UNIVERSAL_FEMALE_NAMES_ON_A = {
    "asuka", "sakura", "elena", "fatima", "sonia", "hinata", "mikasa", "historia",
    "erza", "ayaka", "kaori", "yuka", "ayame", "kana", "chika", "rika",
    "akane", "haruka", "nanami", "hina", "marin", "kanna", "alya", "tanya",
    "alisa", "fiona", "eliza", "clara", "teresa", "selena", "vanessa",
    "melissa", "natasha", "tatiana", "olga", "sveta", "katrina", "sabrina", "sarah",
    "olivia", "bianca", "mia"
}

INVARIABLE_JAPANESE_FEMALE_NAMES = {
    "karin", "marin", "rin", "ran", "shion", "karen", "sion", "suzu",
    "yoruichi", "aoi", "shinobu", "nanami", "ayame", "kaori", "tsunade", "tomoyo",
    "hitomi", "homura", "madoka", "mami", "sayaka", "kyoko", "kohaku",
    "chiyo", "maki", "nobara", "mai", "kasumi", "miwa", "shoko", "utahime",
    "mei", "kanna", "koko", "sakurako", "hanako", "fumiko", "yukiko", "yoko",
    "naoko", "mariko", "keiko", "reiko", "aiko", "riko", "miko", "ririka",
    "kikyo", "kagome", "sango", "kushina", "mikoto", "kurenai", "anko",
    "temari", "tenten", "konan", "mito", "tsuchigumo", "suzumebachi", "nemu",
    "unohana", "isane", "kiyone", "soi-fon", "soifon", "mashiro", "hiyori",
    "himeko", "seele", "bronya", "raiden", "yae"
}

FOREIGN_FEMALE_CONSONANT_NAMES = {
    "carmen", "miriam", "ines", "rachel", "astrid", "judith", "helen", "karen",
    "gwen", "karin", "marin", "rin", "shion", "sion", "helen", "ellen", "karen", "vivian",
    "lyn", "lynn", "ann", "anne", "jean", "joan", "jill", "kim", "dawn", "megan", "beth"
}

FEMALE_LEXICON_NAMES: Set[str] = (
    INHERENT_FEMALE_NOUNS | SECONDARY_LEXICAL_FEMALE_NOUNS |
    POLISH_FEMALE_NAMES | UNIVERSAL_FEMALE_NAMES_ON_A |
    FOREIGN_FEMALE_CONSONANT_NAMES
)

def is_inherently_female_name(name: str, series_bible: Any = None) -> bool:
    """
    Returns True if the name is an inherently female first name (Polish or universal female name
    in the curated onomastic database or its vocative form on -o/-u).
    Excludes male exceptions on -a (Kuba, Barnaba, Kosma, etc.), interjections ('ała'),
    generic grammatical categories ('kobieta', 'mężczyzna'), and canonical male names.
    If series_bible is provided, epistemic precedence checks whether the character is registered as MALE.
    """
    if not name:
        return False
    clean = extract_clean_speaker_name(name).strip().lower()
    if is_generic_actor_or_category(clean):
        return False
    if clean in MALE_EXCEPTIONS_ON_A or clean in CANONICAL_MALE_NAMES:
        return False
    if series_bible and hasattr(series_bible, "data") and isinstance(series_bible.data, dict):
        chars = series_bible.data.get("characters", {})
        for k, v in chars.items():
            if "->" not in k:
                k_clean = extract_clean_speaker_name(k).strip().lower()
                if k_clean == clean or clean in k_clean.split():
                    val = v.get("gender") if isinstance(v, dict) else v
                    g = str(val or "").upper()
                    if "MALE" in g or "MĘSK" in g:
                        return False
                    if "FEM" in g or "ŻEŃSK" in g:
                        return True

    if clean in POLISH_FEMALE_NAMES or clean in UNIVERSAL_FEMALE_NAMES_ON_A or clean in INVARIABLE_JAPANESE_FEMALE_NAMES or clean in FOREIGN_FEMALE_CONSONANT_NAMES:
        return True

    # Fonotaktyka słowiańskich/uniwersalnych zdrobnień i imion żeńskich na -usia, -isia, -ysia (Lusia, Dusia, Danusia, itp.)
    if (clean.endswith("usia") or clean.endswith("isia") or clean.endswith("ysia")) and len(clean) >= 4 and not clean.startswith("nie"):
        return True

    # Fonotaktyka obcych imion żeńskich na -eren (>= 6 liter)
    if clean.endswith("eren") and len(clean) >= 6:
        return True

    clean_words = clean.split()
    if len(clean_words) >= 2 and is_inherently_female_name(clean_words[0], series_bible=series_bible):
        return True

    if has_japanese_male_name_suffix(clean):
        return False
    if is_official_or_court_consonant_name(clean, series_bible=series_bible):
        return False

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

COLLECTIVE_LABELS = {
    "both", "all", "everyone", "everybody", "together", "wszyscy", "oboje", "obie", "obaj",
    "animals", "creatures", "people", "humans", "students", "children", "men", "women",
    "boys", "girls", "soldiers", "guards", "crowd", "group", "zwierzęta", "stwory",
    "ludzie", "dzieci", "kobiety", "mężczyźni", "chłopcy", "dziewczęta", "żołnierze",
    "strażnicy", "tłum", "grupa"
}

def is_generic_actor_or_category(name: str) -> bool:
    """
    Returns True if the string is a generic grammatical category, placeholder,
    or descriptive label (e.g. 'mężczyzna', 'kobieta', 'grupa_kobiet', 'brak', 'narrator')
    rather than a real named character.
    """
    if not name:
        return True
    clean = extract_clean_speaker_name(name).strip().lower()
    if clean in COLLECTIVE_LABELS:
        return True
    if clean in GENERIC_CATEGORY_TAGS:
        return True
    generic_roles = (
        r"man|male|boy|guy|woman|female|girl|lady|child|kid|villager|soldier|guard|student|envoy|courier|messenger|emissary|posłaniec|wysłannik|"
        r"citizen|passenger|driver|doctor|nurse|waiter|waitress|officer|policeman|detective|"
        r"thug|bandit|disciple|escort|customer|guest|host|shopkeeper|clerk|bystander|passerby|"
        r"servant|knight|warrior|elder|chief|king|queen|prince|princess|lord|teacher|principal|"
        r"classmate|neighbor|crowd|voice|voices|narrator|announcer|caller|mob|"
        r"wojownik|uczeń|uczen|nauczyciel|strażnik|straznik|służący|sluzacy|wieśniak|wiesniak|"
        r"żołnierz|zolnierz|chłopiec|chlopiec|dziewczynka|przechodzień|przechodzien"
    )
    if re.match(rf"^(?:{generic_roles})(?:\s+[a-zA-Z]|\s+[0-9]+|\s*)$", clean, re.IGNORECASE):
        return True
    return False

def is_sign_entity(name: str) -> bool:
    """Sprawdza, czy nazwa odnosi się do napisu ekranowego, szyldu lub tytulu."""
    if not name:
        return False
    cl = extract_clean_speaker_name(name).strip().lower()
    if cl in ("sign", "signs", "napis", "napisy", "screen", "ekran", "title", "caption", "szyld", "szyldy", "txt", "text"):
        return True
    if any(cl.startswith(p) for p in ("sign", "signs", "napis", "szyld", "screen ", "ekran ", "title ", "caption ", "txt", "text")):
        return True
    return False

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
    clean = re.sub(r"[\(\[].*?[\)\]]", "", clean)
    clean = re.sub(r"[\(\[].*$", "", clean).strip()
    return clean


def is_feminine_instrumental_after_z_allowed(
    name: str,
    preceding_text: str = "",
    series_bible: Optional[Any] = None,
    context: Optional[str] = None
) -> bool:
    """
    Dwupoziomowa bramka bezpieczeństwa dla żeńskiego narzędnika -ą po przyimku pochodzenia z (Klaster C):
    a) Zamiana z [Nazwa]a -> z [Nazwa]ą może zajść WYŁĄCZNIE wtedy, gdy [Nazwa] jest zarejestrowanym w SeriesBible
       imieniem postaci ludzkiej (EntityCategory.ANTHROPONYM o gender == 'FEMALE'),
       ORAZ nie należy do polskich słów pospolitych/instytucji (POLISH_COMMON_NOUN_HOMONYMS, instytucje:
       biuro, miasto, królestwo, cesarstwo, księstwo, imperium, ministerstwo, centrum, laboratorium, archiwum, dowództwo
       ani sufiksy -stwo, -ctwo, -sko).
    b) Ochrona przed zamianą -a -> -ą po z, gdy przed z stoi rzeczownik grupy/pochodzenia
       (ludzie z, ci z, agenci z, pracownicy z, oddział z, goście z, koledzy z, szef z)
       lub czasownik ruchu/ablatywny (dotarli z, przybyli z, wrócili z, przyszli z, wyszli z, pochodzą z, dzwonią z).
    """
    if not name:
        return False
    clean_name = extract_clean_speaker_name(name).strip()
    c_lower = clean_name.lower()
    c_norm = normalize_name_nfkd(clean_name).lower()

    # 1. Poziom B: Ochrona przed zamianą, gdy przed 'z' stoi rzeczownik grupy/pochodzenia lub czasownik ruchu/ablatywny
    if preceding_text:
        prec_clean = preceding_text.strip()
        prec_pat = rf"(?:^|[\s,.\-!?;:\"'()\[\]\\])(?:{ORIGIN_GROUP_NOUNS_PATTERN}|{ABLATIVE_MOTION_VERBS_PATTERN})(?:\s+(?:[Zz]e|[Zz]))?\s*$"
        if re.search(prec_pat, prec_clean, re.IGNORECASE):
            return False

    # 2. Poziom A: Wykluczenie polskich słów pospolitych (POLISH_COMMON_NOUN_HOMONYMS)
    if is_proper_noun_homonym(clean_name) or c_lower in globals().get("POLISH_COMMON_NOUN_HOMONYMS", set()) or c_norm in globals().get("POLISH_COMMON_NOUN_HOMONYMS", set()):
        return False

    # 3. Poziom A: Wykluczenie instytucji i sufiksów instytucjonalnych (-stwo, -ctwo, -sko)
    if c_lower in INSTITUTION_NOUNS or c_norm in INSTITUTION_NOUNS:
        return False
    if any(c_lower.endswith(suf) or c_norm.endswith(suf) for suf in INSTITUTIONAL_SUFFIXES):
        return False
    if any(re.search(rf"(?:{re.escape(suf[:-1])}[a-ząćęłńóśźż]+)$", c_lower) for suf in ("stwie", "ctwie", "stwem", "ctwem", "stwu", "ctwu", "skiem", "skiej")):
        return False

    # 4. Poziom A: Wykluczenie toponimów i chrematonimów
    if c_lower in globals().get("KNOWN_FANTASY_TOPONYMS", set()) or c_lower in globals().get("INDECLINABLE_FRENCH_TOPONYMS", set()):
        return False

    # 5. Poziom A: Wymóg rejestracji w SeriesBible jako ludzka postać żeńska (EntityCategory.ANTHROPONYM o gender == 'FEMALE')
    if series_bible is not None:
        if hasattr(series_bible, "is_non_character_entity") and series_bible.is_non_character_entity(clean_name):
            return False
        cat = series_bible.get_entity_category(clean_name, context=context) if hasattr(series_bible, "get_entity_category") else classify_entity_category(clean_name, context=context, series_bible=series_bible)
        if cat != EntityCategory.ANTHROPONYM:
            return False
        bg = series_bible.get_character_gender(clean_name, allow_generic_nouns=False) if hasattr(series_bible, "get_character_gender") else "UNKNOWN"
        if bg != "FEMALE":
            return False
        return True
    else:
        cat = classify_entity_category(clean_name, context=context)
        if cat != EntityCategory.ANTHROPONYM:
            return False
        if not is_inherently_female_name(clean_name):
            return False
        return True


def fix_undecorated_female_names(
    text: str,
    character_names: Optional[List[str]] = None,
    series_bible: Optional[Any] = None
) -> str:
    """
    Koryguje błędy pozostawienia żeńskiego imienia w mianowniku po przyimkach,
    z pełną dwupoziomową blokadą po przyimku pochodzenia z (Klaster C).
    """
    if not text:
        return text

    gen_preps = r"(?:dla|do|od|bez|u|koło|obok|blisko|wokół|dookoła|spod|zza|znad|według|mimo|wobec|naprzeciw|wskutek)"
    dat_preps = r"(?:dzięki|przeciw|przeciwko|ku|wbrew|dałem\s+to|dałam\s+to|dał\s+to|dała\s+to|podarowałem|podarowałam|powiedziałem|powiedziałam)"
    ins_preps = r"(?:z|ze|przed|przede|nad|nade|pod|pode|między|pomiędzy|za)"

    names = character_names
    if not names:
        if series_bible and hasattr(series_bible, "data") and isinstance(series_bible.data, dict):
            names = [
                k for k in series_bible.data.get("characters", {}).keys()
                if "->" not in k and series_bible.get_character_gender(k, allow_generic_nouns=False) == "FEMALE"
            ]
        else:
            names = []

    result = text
    for name in names:
        if not name or len(name) < 2:
            continue
        decl = generate_polish_name_declension(name, "FEMALE")
        if not decl or decl.get("M") != name:
            continue

        # 1. Dopełniacz: "dla Asuka" -> "dla Asuki"
        result = re.sub(
            rf"\b({gen_preps})\s+{re.escape(name)}\b",
            lambda m, c=decl.get("D", name): f"{m.group(1)} {c}",
            result,
            flags=re.IGNORECASE
        )

        # 2. Celownik: "dzięki Asuka" -> "dzięki Asuce"
        result = re.sub(
            rf"\b({dat_preps}(?:\s+[a-ząćęłńóśźż]+)?)\s+{re.escape(name)}\b",
            lambda m, c=decl.get("C", name): f"{m.group(1)} {c}",
            result,
            flags=re.IGNORECASE
        )

        # 3. Narzędnik: "z Asuka" -> "z Asuką" z dwupoziomową blokadą
        def _ins_repl(m, n=name, d=decl):
            prep = m.group(1)
            prep_lower = prep.lower()
            if prep_lower in ("z", "ze"):
                start_pos = m.start()
                preceding_text = result[max(0, start_pos - 60):start_pos]
                if series_bible and hasattr(series_bible, "can_inflect_feminine_instrumental_after_z"):
                    allowed = series_bible.can_inflect_feminine_instrumental_after_z(n, preceding_text=preceding_text)
                else:
                    allowed = is_feminine_instrumental_after_z_allowed(n, preceding_text=preceding_text, series_bible=series_bible)
                if not allowed:
                    return m.group(0)
            return f"{prep} {d.get('N', n)}"

        result = re.sub(
            rf"\b({ins_preps})\s+{re.escape(name)}\b",
            _ins_repl,
            result,
            flags=re.IGNORECASE
        )

    return result


def fix_undecorated_names(
    text: str,
    character_names: Optional[List[str]] = None,
    series_bible: Optional[Any] = None
) -> str:
    """Koryguje brak fleksji imion męskich i żeńskich po przyimkach z dwupoziomową bramką Klastra C."""
    res = fix_undecorated_male_names(text, character_names=character_names, series_bible=series_bible)
    res = fix_undecorated_female_names(res, character_names=character_names, series_bible=series_bible)
    return res


def is_polish_adjective(word: str) -> bool:
    w = word.lower().strip()
    if len(w) < 4:
        return False

    # Explicit exclusion of common Japanese names ending in -ki, -gi, -na
    # (e.g. Suzuki, Takahashi, Kawasaki, Miyazaki, Todoroki, Tanuki, Tomoe, Shina, etc.)
    if any(w.endswith(jp_end) for jp_end in ("saki", "zuki", "zaki", "roki", "nuki", "buki", "muki", "tuki", "yuki", "yaki", "seki", "deki", "heki", "kiki", "giki")):
        return False

    # Polish feminine nouns ending in -yna, -ina, -anka, -arka, -anna (e.g. kurtyna, dziewczyna, maszyna, cytryna)
    if w.endswith(("yna", "ina", "anka", "arka", "anna", "otta", "etta")):
        return False

    # Exclusion of common nouns ending in -na, -ta, -ka, -ga and foreign names in -ite (e.g. White, Snowwhite)
    if w.endswith("white") or w in {"kobieta", "dziewczyna", "pani", "chata", "brama", "tarcza", "lanca", "rana", "scena", "wojna", "korona", "strona", "ochrona", "obrona", "wrona", "rzeka", "książka", "ręka", "nauka", "matka", "córka", "dróżka", "papuga", "waga", "droga", "flaga", "saga", "manga", "planeta", "rakieta", "flota", "armata", "herbata", "gazeta", "white", "elite", "site", "bite", "mite", "kite"}:
        return False

    # Exclusion of genitive forms of known head nouns ending in -a (e.g. miecza, demona, sztyleta, zamka)
    if w.endswith("a") and (w[:-1] in KNOWN_HEAD_NOUNS or w[:-1] in KNOWN_HEAD_NOUN_DECLENSIONS):
        return False

    # Polish base adjectives
    BASE_ADJECTIVES = {
        "czerwony", "czerwona", "czerwone", "biały", "biała", "białe", "czarny", "czarna", "czarne",
        "złoty", "złota", "złote", "srebrny", "srebrna", "srebrne", "zielony", "zielona", "zielone",
        "święty", "święta", "święte", "cichy", "cicha", "ciche", "krwawy", "krwawa", "krwawe",
        "mroczny", "mroczna", "mroczne", "jasny", "jasna", "jasne", "ciemny", "ciemna", "ciemne",
        "młody", "młoda", "młode", "stary", "stara", "stare", "nowy", "nowa", "nowe",
        "dobry", "dobra", "dobre", "zły", "zła", "złe", "szalony", "szalona", "szalone",
        "dziki", "dzika", "dzike", "wolny", "wolna", "wolne", "żywy", "żywa", "żywe",
        "martwy", "martwa", "martwe", "zimny", "zimna", "zimne", "gorący", "gorąca", "gorące",
        "prosty", "prosta", "proste", "gęsty", "gęsta", "gęste", "pusty", "pusta", "puste",
        "czysty", "czysta", "czyste", "nieśmiertelny", "nieśmiertelna", "nieśmiertelne"
    }
    if w in BASE_ADJECTIVES:
        return True

    # Polish adjective and adjectival participle endings
    ADJ_ENDINGS = (
        "ski", "ska", "skie", "cki", "cka", "ckie", "dzki", "dzka", "dzkie",
        "owy", "owa", "owe", "asty", "asta", "aste", "isty", "ista", "iste",
        "liwy", "liwa", "liwe", "szy", "sza", "sze", "czy", "cza", "cze",
        "alny", "alna", "alne", "elny", "elna", "elne", "olny", "olna", "olne",
        "arny", "arna", "arne", "erny", "erna", "erne", "yczny", "yczna", "yczne",
        "iczny", "iczna", "iczne", "owny", "owna", "owne", "tywny", "tywna", "tywne",
        "ienny", "ienna", "ienne", "enny", "enna", "enne",
        # Active adjectival participles (e.g. płonący, śpiący, latający, milczący)
        "ący", "ąca", "ące",
        # Qualitative, diminutive, and expressive adjective suffixes
        "aty", "ata", "ate", "ity", "ita", "ite",
        "utki", "utka", "utkie", "eńki", "eńka", "eńkie",
        "owaty", "owata", "owate", "iasty", "iasta", "iaste"
    )
    if any(w.endswith(end) for end in ADJ_ENDINGS):
        return True
    if len(w) >= 5:
        if w.endswith("ny"):
            return True
        if w.endswith("na"):
            vowels = {"a", "e", "i", "o", "u", "y", "ó", "ą", "ę"}
            if (
                w not in FEMALE_LEXICON_NAMES
                and w not in INHERENT_FEMALE_NOUNS
                and w not in POLISH_FEMALE_NAMES
                and w not in UNIVERSAL_FEMALE_NAMES_ON_A
                and len(w) >= 3
                and w[-3] not in vowels
            ):
                return True
        if w.endswith("ne"):
            consonants = {"r", "l", "d", "t", "z", "ł", "s", "c", "b", "p", "w", "m", "n", "k", "g", "h", "f"}
            if len(w) >= 3 and w[-3] in consonants:
                return True

    # Root adjectives ending in -ki, -gi
    ADJ_ROOTS_ON_KI_GI = {"wielk", "dzik", "krótk", "szyb", "lekk", "ciężk", "miękk", "gładk", "wąsk", "szerok", "wysok", "nisk", "dalek", "blisk", "głębok", "płytk", "gorzk", "słodk", "cienk", "drog", "ubog", "sroga", "tęga", "błoga"}
    if any(w.startswith(root) for root in ADJ_ROOTS_ON_KI_GI) and w.endswith(("i", "y", "a", "e")):
        return True

    return False



def generate_polish_adjective_declension(adj: str, gender: Optional[str] = None, is_animate: bool = True) -> Dict[str, str]:
    w = adj.strip()
    if not w:
        return {}
    w_l = w.lower()
    g_lower = (gender or "").strip().lower()

    # 1. Feminine adjective on -a
    if w_l.endswith("a") or g_lower == "female" or any(k in g_lower for k in ("kobiet", "żeńsk")):
        stem = w[:-1] if w_l.endswith("a") else w
        suffix_d = "iej" if stem.lower().endswith(("k", "g")) and not stem.lower().endswith("i") else "ej"
        return {
            "M": w,
            "D": stem + suffix_d,
            "C": stem + suffix_d,
            "B": stem + "ą",
            "N": stem + "ą",
            "Ms": stem + suffix_d,
            "W": w
        }

    # 2. Neuter adjective on -e
    if w_l.endswith("e") or g_lower in ("neuter", "nijaki"):
        stem = w[:-1] if w_l.endswith("e") else w
        n_ms = stem + "im" if stem.lower().endswith(("k", "g")) else (stem[:-1] + "im" if stem.lower().endswith("i") else stem + "ym")
        return {
            "M": w,
            "D": stem + "ego",
            "C": stem + "emu",
            "B": w,
            "N": n_ms,
            "Ms": n_ms,
            "W": w
        }

    # 3. Masculine adjective on -y / -i
    if w_l.endswith(("y", "i")) or g_lower == "male" or any(k in g_lower for k in ("mężczyzn", "męsk")):
        stem = w[:-1]
        last_c = stem[-1].lower() if stem else ""
        if w_l.endswith("i"):
            d_case = stem + "ego" if stem.lower().endswith("i") else stem + "iego"
            c_case = stem + "emu" if stem.lower().endswith("i") else stem + "iemu"
            n_ms = stem + "m" if stem.lower().endswith("i") else stem + "im"
        else:
            d_case = stem + "ego"
            c_case = stem + "emu"
            n_ms = stem + "im" if last_c in ("k", "g") else stem + "ym"
        b_case = d_case if is_animate else w
        return {
            "M": w,
            "D": d_case,
            "C": c_case,
            "B": b_case,
            "N": n_ms,
            "Ms": n_ms,
            "W": w
        }

    return {"M": w, "D": w, "C": w, "B": w, "N": w, "Ms": w, "W": w}


KNOWN_HEAD_NOUN_DECLENSIONS = {
    "kod": {"M": "Kod", "D": "Kodu", "C": "Kodowi", "B": "Kod", "N": "Kodem", "Ms": "Kodzie", "W": "Kodzie"},
    "system": {"M": "System", "D": "Systemu", "C": "Systemowi", "B": "System", "N": "Systemem", "Ms": "Systemie", "W": "Systemie"},
    "zakon": {"M": "Zakon", "D": "Zakonu", "C": "Zakonowi", "B": "Zakon", "N": "Zakonem", "Ms": "Zakonie", "W": "Zakonie"},
    "miecz": {"M": "Miecz", "D": "Miecza", "C": "Mieczowi", "B": "Miecz", "N": "Mieczem", "Ms": "Mieczu", "W": "Mieczu"},
    "księga": {"M": "Księga", "D": "Księgi", "C": "Księdze", "B": "Księgę", "N": "Księgą", "Ms": "Księdze", "W": "Księgo"},
    "dolina": {"M": "Dolina", "D": "Doliny", "C": "Dolinie", "B": "Dolinę", "N": "Doliną", "Ms": "Dolinie", "W": "Dolino"},
    "zamek": {"M": "Zamek", "D": "Zamku", "C": "Zamkowi", "B": "Zamek", "N": "Zamkiem", "Ms": "Zamku", "W": "Zamku"},
    "lanca": {"M": "Lanca", "D": "Lancy", "C": "Lancy", "B": "Lancę", "N": "Lancą", "Ms": "Lancy", "W": "Lanco"},
    "tarcza": {"M": "Tarcza", "D": "Tarczy", "C": "Tarczy", "B": "Tarczę", "N": "Tarczą", "Ms": "Tarczy", "W": "Tarczo"},
    "pakt": {"M": "Pakt", "D": "Paktu", "C": "Paktowi", "B": "Pakt", "N": "Paktem", "Ms": "Pakcie", "W": "Pakcie"},
    "przymierze": {"M": "Przymierze", "D": "Przymierza", "C": "Przymierzu", "B": "Przymierze", "N": "Przymierzem", "Ms": "Przymierzu", "W": "Przymierze"},
    "amulet": {"M": "Amulet", "D": "Amuletu", "C": "Amuletowi", "B": "Amulet", "N": "Amuletem", "Ms": "Amuletu", "W": "Amuletu"},
    "zwój": {"M": "Zwój", "D": "Zwoju", "C": "Zwojowi", "B": "Zwój", "N": "Zwojem", "Ms": "Zwoju", "W": "Zwoju"},
    "kamień": {"M": "Kamień", "D": "Kamienia", "C": "Kamieniowi", "B": "Kamień", "N": "Kamieniem", "Ms": "Kamieniu", "W": "Kamieniu"},
    "drzewo": {"M": "Drzewo", "D": "Drzewa", "C": "Drzewu", "B": "Drzewo", "N": "Drzewem", "Ms": "Drzewie", "W": "Drzewo"},
    "wieża": {"M": "Wieża", "D": "Wieży", "C": "Wieży", "B": "Wieżę", "N": "Wieżą", "Ms": "Wieży", "W": "Wieżo"},
    "brama": {"M": "Brama", "D": "Bramy", "C": "Bramie", "B": "Bramę", "N": "Bramą", "Ms": "Bramie", "W": "Bramo"},
    "tron": {"M": "Tron", "D": "Tronu", "C": "Tronowi", "B": "Tron", "N": "Tronem", "Ms": "Tronie", "W": "Tronie"},
    "sztylet": {"M": "Sztylet", "D": "Sztyletu", "C": "Sztyletowi", "B": "Sztylet", "N": "Sztyletem", "Ms": "Sztylecie", "W": "Sztylecie"},
    "młot": {"M": "Młot", "D": "Młota", "C": "Młotowi", "B": "Młot", "N": "Młotem", "Ms": "Młocie", "W": "Młocie"},
    "kosa": {"M": "Kosa", "D": "Kosy", "C": "Kosie", "B": "Kosę", "N": "Kosą", "Ms": "Kosie", "W": "Koso"},
    "hełm": {"M": "Hełm", "D": "Hełmu", "C": "Hełmowi", "B": "Hełm", "N": "Hełmem", "Ms": "Hełmie", "W": "Hełmie"},
    "zbroja": {"M": "Zbroja", "D": "Zbroi", "C": "Zbroi", "B": "Zbroję", "N": "Zbroją", "Ms": "Zbroi", "W": "Zbrojo"},
    "gniew": {"M": "Gniew", "D": "Gniewu", "C": "Gniewowi", "B": "Gniew", "N": "Gniewem", "Ms": "Gniewie", "W": "Gniewie"},
    # Epithets, Titles & Anime Classes (Manga Canon Supreme)
    "władca": {"M": "Władca", "D": "Władcy", "C": "Władcy", "B": "Władcę", "N": "Władcą", "Ms": "Władcy", "W": "Władco"},
    "władczyni": {"M": "Władczyni", "D": "Władczyni", "C": "Władczyni", "B": "Władczynię", "N": "Władczynią", "Ms": "Władczyni", "W": "Władczyni"},
    "demon": {"M": "Demon", "D": "Demona", "C": "Demonowi", "B": "Demona", "N": "Demonem", "Ms": "Demonie", "W": "Demonie"},
    "demonica": {"M": "Demonica", "D": "Demonicy", "C": "Demonicy", "B": "Demonicę", "N": "Demonicą", "Ms": "Demonicy", "W": "Demonico"},
    "mistrz": {"M": "Mistrz", "D": "Mistrza", "C": "Mistrzowi", "B": "Mistrza", "N": "Mistrzem", "Ms": "Mistrzu", "W": "Mistrzu"},
    "mistrzyni": {"M": "Mistrzyni", "D": "Mistrzyni", "C": "Mistrzyni", "B": "Mistrzynię", "N": "Mistrzynią", "Ms": "Mistrzyni", "W": "Mistrzyni"},
    "pani": {"M": "Pani", "D": "Pani", "C": "Pani", "B": "Panią", "N": "Panią", "Ms": "Pani", "W": "Pani"},
    "pan": {"M": "Pan", "D": "Pana", "C": "Panu", "B": "Pana", "N": "Panem", "Ms": "Panu", "W": "Panie"},
    "lord": {"M": "Lord", "D": "Lorda", "C": "Lordowi", "B": "Lorda", "N": "Lordem", "Ms": "Lordzie", "W": "Lordzie"},
    "bóg": {"M": "Bóg", "D": "Boga", "C": "Bogu", "B": "Boga", "N": "Bogiem", "Ms": "Bogu", "W": "Boże"},
    "bogini": {"M": "Bogini", "D": "Bogini", "C": "Bogini", "B": "Boginię", "N": "Boginią", "Ms": "Bogini", "W": "Bogini"},
    "rycerz": {"M": "Rycerz", "D": "Rycerza", "C": "Rycerzowi", "B": "Rycerza", "N": "Rycerzem", "Ms": "Rycerzu", "W": "Rycerzu"},
    "generał": {"M": "Generał", "D": "Generała", "C": "Generałowi", "B": "Generała", "N": "Generałem", "Ms": "Generale", "W": "Generale"},
    "dowódca": {"M": "Dowódca", "D": "Dowódcy", "C": "Dowódcy", "B": "Dowódcę", "N": "Dowódcą", "Ms": "Dowódcy", "W": "Dowódco"},
    "zabójca": {"M": "Zabójca", "D": "Zabójcy", "C": "Zabójcy", "B": "Zabójcę", "N": "Zabójcą", "Ms": "Zabójcy", "W": "Zabójco"},
    "obrońca": {"M": "Obrońca", "D": "Obrońcy", "C": "Obrońcy", "B": "Obrońcę", "N": "Obrońcą", "Ms": "Obrońcy", "W": "Obrońco"},
    "łowca": {"M": "Łowca", "D": "Łowcy", "C": "Łowcy", "B": "Łowcę", "N": "Łowcą", "Ms": "Łowcy", "W": "Łowco"},
    "strażnik": {"M": "Strażnik", "D": "Strażnika", "C": "Strażnikowi", "B": "Strażnika", "N": "Strażnikiem", "Ms": "Strażniku", "W": "Strażniku"},
    "król": {"M": "Król", "D": "Króla", "C": "Królowi", "B": "Króla", "N": "Królem", "Ms": "Królu", "W": "Królu"},
    "królowa": {"M": "Królowa", "D": "Królowej", "C": "Królowej", "B": "Królową", "N": "Królową", "Ms": "Królowej", "W": "Królowo"},
    "książę": {"M": "Książę", "D": "Księcia", "C": "Księciu", "B": "Księcia", "N": "Księciem", "Ms": "Księciu", "W": "Książę"},
    "księżniczka": {"M": "Księżniczka", "D": "Księżniczki", "C": "Księżniczce", "B": "Księżniczkę", "N": "Księżniczką", "Ms": "Księżniczce", "W": "Księżniczko"},
    "cesarz": {"M": "Cesarz", "D": "Cesarza", "C": "Cesarzowi", "B": "Cesarza", "N": "Cesarzem", "Ms": "Cesarzu", "W": "Cesarzu"},
    "cesarzowa": {"M": "Cesarzowa", "D": "Cesarzowej", "C": "Cesarzowej", "B": "Cesarzową", "N": "Cesarzową", "Ms": "Cesarzowej", "W": "Cesarzowo"},
    "mag": {"M": "Mag", "D": "Maga", "C": "Magowi", "B": "Maga", "N": "Magiem", "Ms": "Magu", "W": "Magu"},
    "czarnoksiężnik": {"M": "Czarnoksiężnik", "D": "Czarnoksiężnika", "C": "Czarnoksiężnikowi", "B": "Czarnoksiężnika", "N": "Czarnoksiężnikiem", "Ms": "Czarnoksiężniku", "W": "Czarnoksiężniku"},
    "kapłan": {"M": "Kapłan", "D": "Kapłana", "C": "Kapłanowi", "B": "Kapłana", "N": "Kapłanem", "Ms": "Kapłanie", "W": "Kapłanie"},
    "kapłanka": {"M": "Kapłanka", "D": "Kapłanki", "C": "Kapłance", "B": "Kapłankę", "N": "Kapłanką", "Ms": "Kapłance", "W": "Kapłanko"},
    "wojownik": {"M": "Wojownik", "D": "Wojownika", "C": "Wojownikowi", "B": "Wojownika", "N": "Wojownikiem", "Ms": "Wojowniku", "W": "Wojowniku"},
    "wojowniczka": {"M": "Wojowniczka", "D": "Wojowniczki", "C": "Wojowniczce", "B": "Wojowniczkę", "N": "Wojowniczką", "Ms": "Wojowniczce", "W": "Wojowniczko"},
    "bohater": {"M": "Bohater", "D": "Bohatera", "C": "Bohaterowi", "B": "Bohatera", "N": "Bohaterem", "Ms": "Bohaterze", "W": "Bohaterze"},
    "bohaterka": {"M": "Bohaterka", "D": "Bohaterki", "C": "Bohaterce", "B": "Bohaterkę", "N": "Bohaterką", "Ms": "Bohaterce", "W": "Bohaterko"},
    "cień": {"M": "Cień", "D": "Cienia", "C": "Cieniowi", "B": "Cień", "N": "Cieniem", "Ms": "Cieniu", "W": "Cieniu"},
    "płomień": {"M": "Płomień", "D": "Płomienia", "C": "Płomieniowi", "B": "Płomień", "N": "Płomieniem", "Ms": "Płomieniu", "W": "Płomieniu"},
    "krew": {"M": "Krew", "D": "Krwi", "C": "Krwi", "B": "Krew", "N": "Krwią", "Ms": "Krwi", "W": "Krwi"},
    "serce": {"M": "Serce", "D": "Serca", "C": "Sercu", "B": "Serce", "N": "Sercem", "Ms": "Sercu", "W": "Serce"},
    "oko": {"M": "Oko", "D": "Oka", "C": "Oku", "B": "Oko", "N": "Okiem", "Ms": "Oku", "W": "Oko"},
    "ręka": {"M": "Ręka", "D": "Ręki", "C": "Ręce", "B": "Rękę", "N": "Ręką", "Ms": "Ręce", "W": "Ręko"},
    "pierścień": {"M": "Pierścień", "D": "Pierścienia", "C": "Pierścieniowi", "B": "Pierścień", "N": "Pierścieniem", "Ms": "Pierścieniu", "W": "Pierścieniu"},
    "korona": {"M": "Korona", "D": "Korony", "C": "Koronie", "B": "Koronę", "N": "Koroną", "Ms": "Koronie", "W": "Korono"},
    "pieczęć": {"M": "Pieczęć", "D": "Pieczęci", "C": "Pieczęci", "B": "Pieczęć", "N": "Pieczęcią", "Ms": "Pieczęci", "W": "Pieczęci"},
    "zwierciadło": {"M": "Zwierciadło", "D": "Zwierciadła", "C": "Zwierciadłu", "B": "Zwierciadło", "N": "Zwierciadłem", "Ms": "Zwierciadle", "W": "Zwierciadło"},
    "kielich": {"M": "Kielich", "D": "Kielicha", "C": "Kielichowi", "B": "Kielich", "N": "Kielichem", "Ms": "Kielichu", "W": "Kielichu"},
    "światło": {"M": "Światło", "D": "Światła", "C": "Światłu", "B": "Światło", "N": "Światłem", "Ms": "Świetle", "W": "Światło"},
    "wrota": {"M": "Wrota", "D": "Wrót", "C": "Wrotom", "B": "Wrota", "N": "Wrotami", "Ms": "Wrotach", "W": "Wrota"},
    "twierdza": {"M": "Twierdza", "D": "Twierdzy", "C": "Twierdzy", "B": "Twierdzę", "N": "Twierdzą", "Ms": "Twierdzy", "W": "Twierdzo"},
    "świątynia": {"M": "Świątynia", "D": "Świątyni", "C": "Świątyni", "B": "Świątynię", "N": "Świątynią", "Ms": "Świątyni", "W": "Świątynio"},
    "duch": {"M": "Duch", "D": "Ducha", "C": "Duchowi", "B": "Ducha", "N": "Duchem", "Ms": "Duchu", "W": "Duchu"},
    "ród": {"M": "Ród", "D": "Rodu", "C": "Rodowi", "B": "Ród", "N": "Rodem", "Ms": "Rodzie", "W": "Rodzie"},
    "znak": {"M": "Znak", "D": "Znaku", "C": "Znakowi", "B": "Znak", "N": "Znakiem", "Ms": "Znaku", "W": "Znaku"},
    "łuk": {"M": "Łuk", "D": "Łuku", "C": "Łukowi", "B": "Łuk", "N": "Łukiem", "Ms": "Łuku", "W": "Łuku"},
    "strzała": {"M": "Strzała", "D": "Strzały", "C": "Strzale", "B": "Strzałę", "N": "Strzałą", "Ms": "Strzale", "W": "Strzało"},
    "różdżka": {"M": "Różdżka", "D": "Różdżki", "C": "Różdżce", "B": "Różdżkę", "N": "Różdżką", "Ms": "Różdżce", "W": "Różdżko"},
    "kodeks": {"M": "Kodeks", "D": "Kodeksu", "C": "Kodeksowi", "B": "Kodeks", "N": "Kodeksem", "Ms": "Kodeksie", "W": "Kodeksie"},
    "opowieść": {"M": "Opowieść", "D": "Opowieści", "C": "Opowieści", "B": "Opowieść", "N": "Opowieścią", "Ms": "Opowieści", "W": "Opowieści"},
    "legenda": {"M": "Legenda", "D": "Legendy", "C": "Legendzie", "B": "Legendę", "N": "Legendą", "Ms": "Legendzie", "W": "Legendo"},
    "pieśń": {"M": "Pieśń", "D": "Pieśni", "C": "Pieśni", "B": "Pieśń", "N": "Pieśnią", "Ms": "Pieśni", "W": "Pieśni"},
    "hymn": {"M": "Hymn", "D": "Hymnu", "C": "Hymnowi", "B": "Hymn", "N": "Hymnem", "Ms": "Hymnie", "W": "Hymnie"},
    "kronika": {"M": "Kronika", "D": "Kroniki", "C": "Kronice", "B": "Kronikę", "N": "Kroniką", "Ms": "Kronice", "W": "Kroniko"},
    "droga": {"M": "Droga", "D": "Drogi", "C": "Drodze", "B": "Drogę", "N": "Drogą", "Ms": "Drodze", "W": "Drogo"},
    "szlak": {"M": "Szlak", "D": "Szlaku", "C": "Szlakowi", "B": "Szlak", "N": "Szlakiem", "Ms": "Szlaku", "W": "Szlaku"},
    "most": {"M": "Most", "D": "Mostu", "C": "Mostowi", "B": "Most", "N": "Mostem", "Ms": "Moście", "W": "Moście"},
    "rzeka": {"M": "Rzeka", "D": "Rzeki", "C": "Rzece", "B": "Rzekę", "N": "Rzeką", "Ms": "Rzece", "W": "Rzeko"},
    "jezioro": {"M": "Jezioro", "D": "Jeziora", "C": "Jezioru", "B": "Jezioro", "N": "Jeziorem", "Ms": "Jeziorze", "W": "Jezioro"},
    "morze": {"M": "Morze", "D": "Morza", "C": "Morzu", "B": "Morze", "N": "Morzem", "Ms": "Morzu", "W": "Morze"},
    "góra": {"M": "Góra", "D": "Góry", "C": "Górze", "B": "Górę", "N": "Górą", "Ms": "Górze", "W": "Góro"},
    "pustynia": {"M": "Pustynia", "D": "Pustyni", "C": "Pustyni", "B": "Pustynię", "N": "Pustynią", "Ms": "Pustyni", "W": "Pustynio"},
    "zemsta": {"M": "Zemsta", "D": "Zemsty", "C": "Zemście", "B": "Zemstę", "N": "Zemstą", "Ms": "Zemście", "W": "Zemsto"},
    "klątwa": {"M": "Klątwa", "D": "Klątwy", "C": "Klątwie", "B": "Klątwę", "N": "Klątwą", "Ms": "Klątwie", "W": "Klątwo"},
    "bunt": {"M": "Bunt", "D": "Buntu", "C": "Buntowi", "B": "Bunt", "N": "Buntem", "Ms": "Buncie", "W": "Buncie"},
    "upadek": {"M": "Upadek", "D": "Upadku", "C": "Upadkowi", "B": "Upadek", "N": "Upadkiem", "Ms": "Upadku", "W": "Upadku"},
    "powrót": {"M": "Powrót", "D": "Powrotu", "C": "Powrotowi", "B": "Powrót", "N": "Powrotem", "Ms": "Powrocie", "W": "Powrocie"},
    "narodziny": {"M": "Narodziny", "D": "Narodzin", "C": "Narodzinom", "B": "Narodziny", "N": "Narodzinami", "Ms": "Narodzinach", "W": "Narodziny"},
    "koniec": {"M": "Koniec", "D": "Końca", "C": "Końcowi", "B": "Koniec", "N": "Końcem", "Ms": "Końcu", "W": "Końcu"},
    "początek": {"M": "Początek", "D": "Początku", "C": "Początkowi", "B": "Początek", "N": "Początkiem", "Ms": "Początku", "W": "Początku"},
    "córka": {"M": "Córka", "D": "Córki", "C": "Córce", "B": "Córkę", "N": "Córką", "Ms": "Córce", "W": "Córko"},
    "syn": {"M": "Syn", "D": "Syna", "C": "Synowi", "B": "Syna", "N": "Synem", "Ms": "Synu", "W": "Synu"},
    "matka": {"M": "Matka", "D": "Matki", "C": "Matce", "B": "Matkę", "N": "Matką", "Ms": "Matce", "W": "Matko"},
    "ojciec": {"M": "Ojciec", "D": "Ojca", "C": "Ojcu", "B": "Ojca", "N": "Ojcem", "Ms": "Ojcu", "W": "Ojcze"},
    "brat": {"M": "Brat", "D": "Brata", "C": "Bratu", "B": "Brata", "N": "Bratem", "Ms": "Bracie", "W": "Bracie"},
    "siostra": {"M": "Siostra", "D": "Siostry", "C": "Siostrze", "B": "Siostrę", "N": "Siostrą", "Ms": "Siostrze", "W": "Siostro"},
    "arcykapłan": {"M": "Arcykapłan", "D": "Arcykapłana", "C": "Arcykapłanowi", "B": "Arcykapłana", "N": "Arcykapłanem", "Ms": "Arcykapłanie", "W": "Arcykapłanie"},
    "arcymag": {"M": "Arcymag", "D": "Arcymaga", "C": "Arcymagowi", "B": "Arcymaga", "N": "Arcymagiem", "Ms": "Arcymagu", "W": "Arcymagu"},
    "szaman": {"M": "Szaman", "D": "Szamana", "C": "Szamanowi", "B": "Szamana", "N": "Szamanem", "Ms": "Szamanie", "W": "Szamanie"},
    "czarownik": {"M": "Czarownik", "D": "Czarownika", "C": "Czarownikowi", "B": "Czarownika", "N": "Czarownikiem", "Ms": "Czarowniku", "W": "Czarowniku"},
    "czarownica": {"M": "Czarownica", "D": "Czarownicy", "C": "Czarownicy", "B": "Czarownicę", "N": "Czarownicą", "Ms": "Czarownicy", "W": "Czarownico"},
    "bestia": {"M": "Bestia", "D": "Bestii", "C": "Bestii", "B": "Bestię", "N": "Bestią", "Ms": "Bestii", "W": "Bestio"},
    "potwór": {"M": "Potwór", "D": "Potwora", "C": "Potworowi", "B": "Potwora", "N": "Potworem", "Ms": "Potworze", "W": "Potworze"},
    "smok": {"M": "Smok", "D": "Smoka", "C": "Smokowi", "B": "Smoka", "N": "Smokiem", "Ms": "Smoku", "W": "Smoku"},
    "bóstwo": {"M": "Bóstwo", "D": "Bóstwa", "C": "Bóstwu", "B": "Bóstwo", "N": "Bóstwem", "Ms": "Bóstwie", "W": "Bóstwo"},
    "anioł": {"M": "Anioł", "D": "Anioła", "C": "Aniołowi", "B": "Anioła", "N": "Aniołem", "Ms": "Aniele", "W": "Aniele"},
    "wampir": {"M": "Wampir", "D": "Wampira", "C": "Wampirowi", "B": "Wampira", "N": "Wampirem", "Ms": "Wampirze", "W": "Wampirze"},
    "widmo": {"M": "Widmo", "D": "Widma", "C": "Widmu", "B": "Widmo", "N": "Widmem", "Ms": "Widmie", "W": "Widmo"},
    "zjawa": {"M": "Zjawa", "D": "Zjawy", "C": "Zjawie", "B": "Zjawę", "N": "Zjawą", "Ms": "Zjawie", "W": "Zjawo"},
    "kapitan": {'M': 'Kapitan', 'D': 'Kapitana', 'C': 'Kapitanowi', 'B': 'Kapitana', 'N': 'Kapitanem', 'Ms': 'Kapitanie', 'W': 'Kapitanie'},
    "major": {'M': 'Major', 'D': 'Majora', 'C': 'Majorowi', 'B': 'Majora', 'N': 'Majorem', 'Ms': 'Majorze', 'W': 'Majorze'},
    "pułkownik": {'M': 'Pułkownik', 'D': 'Pułkownika', 'C': 'Pułkownikowi', 'B': 'Pułkownika', 'N': 'Pułkownikiem', 'Ms': 'Pułkowniku', 'W': 'Pułkowniku'},
    "porucznik": {'M': 'Porucznik', 'D': 'Porucznika', 'C': 'Porucznikowi', 'B': 'Porucznika', 'N': 'Porucznikiem', 'Ms': 'Poruczniku', 'W': 'Poruczniku'},
    "sierżant": {'M': 'Sierżant', 'D': 'Sierżanta', 'C': 'Sierżantowi', 'B': 'Sierżanta', 'N': 'Sierżantem', 'Ms': 'Sierżancie', 'W': 'Sierżancie'},
    "kapral": {'M': 'Kapral', 'D': 'Kaprala', 'C': 'Kapralowi', 'B': 'Kaprala', 'N': 'Kapralem', 'Ms': 'Kapralu', 'W': 'Kapralu'},
    "admirał": {'M': 'Admirał', 'D': 'Admirała', 'C': 'Admirałowi', 'B': 'Admirała', 'N': 'Admirałem', 'Ms': 'Admirale', 'W': 'Admirale'},
    "hetman": {'M': 'Hetman', 'D': 'Hetmana', 'C': 'Hetmanowi', 'B': 'Hetmana', 'N': 'Hetmanem', 'Ms': 'Hetmanie', 'W': 'Hetmanie'},
    "przywódca": {'M': 'Przywódca', 'D': 'Przywódcy', 'C': 'Przywódcy', 'B': 'Przywódcę', 'N': 'Przywódcą', 'Ms': 'Przywódcy', 'W': 'Przywódco'},
    "przywódczyni": {'M': 'Przywódczyni', 'D': 'Przywódczyni', 'C': 'Przywódczyni', 'B': 'Przywódczynię', 'N': 'Przywódczynią', 'Ms': 'Przywódczyni', 'W': 'Przywódczyni'},
    "wódz": {'M': 'Wódz', 'D': 'Wodza', 'C': 'Wodzowi', 'B': 'Wodza', 'N': 'Wodzem', 'Ms': 'Wodzu', 'W': 'Wodzu'},
    "watażka": {'M': 'Watażka', 'D': 'Watażki', 'C': 'Watażce', 'B': 'Watażkę', 'N': 'Watażką', 'Ms': 'Watażce', 'W': 'Watażko'},
    "czempion": {'M': 'Czempion', 'D': 'Czempiona', 'C': 'Czempionowi', 'B': 'Czempiona', 'N': 'Czempionem', 'Ms': 'Czempionie', 'W': 'Czempionie'},
    "czempionka": {'M': 'Czempionka', 'D': 'Czempionki', 'C': 'Czempionce', 'B': 'Czempionkę', 'N': 'Czempionką', 'Ms': 'Czempionce', 'W': 'Czempionko'},
    "oficer": {'M': 'Oficer', 'D': 'Oficera', 'C': 'Oficerowi', 'B': 'Oficera', 'N': 'Oficerem', 'Ms': 'Oficerze', 'W': 'Oficerze'},
    "żołnierz": {'M': 'Żołnierz', 'D': 'Żołnierza', 'C': 'Żołnierzowi', 'B': 'Żołnierza', 'N': 'Żołnierzem', 'Ms': 'Żołnierzu', 'W': 'Żołnierzu'},
    "woj": {'M': 'Woj', 'D': 'Woja', 'C': 'Wojowi', 'B': 'Woja', 'N': 'Wojem', 'Ms': 'Woju', 'W': 'Woju'},
    "najemnik": {'M': 'Najemnik', 'D': 'Najemnika', 'C': 'Najemnikowi', 'B': 'Najemnika', 'N': 'Najemnikiem', 'Ms': 'Najemniku', 'W': 'Najemniku'},
    "paladyn": {'M': 'Paladyn', 'D': 'Paladyna', 'C': 'Paladynowi', 'B': 'Paladyna', 'N': 'Paladynem', 'Ms': 'Paladynie', 'W': 'Paladynie'},
    "krzyżowiec": {'M': 'Krzyżowiec', 'D': 'Krzyżowca', 'C': 'Krzyżowcowi', 'B': 'Krzyżowca', 'N': 'Krzyżowcem', 'Ms': 'Krzyżowcu', 'W': 'Krzyżowcu'},
    "straż": {'M': 'Straż', 'D': 'Straży', 'C': 'Straży', 'B': 'Straż', 'N': 'Strażą', 'Ms': 'Straży', 'W': 'Straży'},
    "strażniczka": {'M': 'Strażniczka', 'D': 'Strażniczki', 'C': 'Strażniczce', 'B': 'Strażniczkę', 'N': 'Strażniczką', 'Ms': 'Strażniczce', 'W': 'Strażniczko'},
    "obrończyni": {'M': 'Obrończyni', 'D': 'Obrończyni', 'C': 'Obrończyni', 'B': 'Obrończynię', 'N': 'Obrończynią', 'Ms': 'Obrończyni', 'W': 'Obrończyni'},
    "łowczyni": {'M': 'Łowczyni', 'D': 'Łowczyni', 'C': 'Łowczyni', 'B': 'Łowczynię', 'N': 'Łowczynią', 'Ms': 'Łowczyni', 'W': 'Łowczyni'},
    "zabójczyni": {'M': 'Zabójczyni', 'D': 'Zabójczyni', 'C': 'Zabójczyni', 'B': 'Zabójczynię', 'N': 'Zabójczynią', 'Ms': 'Zabójczyni', 'W': 'Zabójczyni'},
    "zwiadowca": {'M': 'Zwiadowca', 'D': 'Zwiadowcy', 'C': 'Zwiadowcy', 'B': 'Zwiadowcę', 'N': 'Zwiadowcą', 'Ms': 'Zwiadowcy', 'W': 'Zwiadowco'},
    "tropiciel": {'M': 'Tropiciel', 'D': 'Tropiciela', 'C': 'Tropicielowi', 'B': 'Tropiciela', 'N': 'Tropicielem', 'Ms': 'Tropicielu', 'W': 'Tropicielu'},
    "barbarzyńca": {'M': 'Barbarzyńca', 'D': 'Barbarzyńcy', 'C': 'Barbarzyńcy', 'B': 'Barbarzyńcę', 'N': 'Barbarzyńcą', 'Ms': 'Barbarzyńcy', 'W': 'Barbarzyńco'},
    "namiestnik": {'M': 'Namiestnik', 'D': 'Namiestnika', 'C': 'Namiestnikowi', 'B': 'Namiestnika', 'N': 'Namiestnikiem', 'Ms': 'Namiestniku', 'W': 'Namiestniku'},
    "gubernator": {'M': 'Gubernator', 'D': 'Gubernatora', 'C': 'Gubernatorowi', 'B': 'Gubernatora', 'N': 'Gubernatorem', 'Ms': 'Gubernatorze', 'W': 'Gubernatorze'},
    "kanclerz": {'M': 'Kanclerz', 'D': 'Kanclerza', 'C': 'Kanclerzowi', 'B': 'Kanclerza', 'N': 'Kanclerzem', 'Ms': 'Kanclerzu', 'W': 'Kanclerzu'},
    "hrabia": {'M': 'Hrabia', 'D': 'Hrabiego', 'C': 'Hrabiemu', 'B': 'Hrabiego', 'N': 'Hrabią', 'Ms': 'Hrabim', 'W': 'Hrabio'},
    "hrabina": {'M': 'Hrabina', 'D': 'Hrabiny', 'C': 'Hrabinie', 'B': 'Hrabinę', 'N': 'Hrabiną', 'Ms': 'Hrabinie', 'W': 'Hrabino'},
    "margrabia": {'M': 'Margrabia', 'D': 'Margrabiego', 'C': 'Margrabiemu', 'B': 'Margrabiego', 'N': 'Margrabią', 'Ms': 'Margrabim', 'W': 'Margrabio'},
    "baron": {'M': 'Baron', 'D': 'Barona', 'C': 'Baronowi', 'B': 'Barona', 'N': 'Baronem', 'Ms': 'Baronie', 'W': 'Baronie'},
    "baronowa": {'M': 'Baronowa', 'D': 'Baronowej', 'C': 'Baronowej', 'B': 'Baronową', 'N': 'Baronową', 'Ms': 'Baronowej', 'W': 'Baronowo'},
    "suweren": {'M': 'Suweren', 'D': 'Suwerena', 'C': 'Suwerenowi', 'B': 'Suwerena', 'N': 'Suwerenem', 'Ms': 'Suwerenie', 'W': 'Suwerenie'},
    "wasal": {'M': 'Wasal', 'D': 'Wasala', 'C': 'Wasalowi', 'B': 'Wasala', 'N': 'Wasalem', 'Ms': 'Wasalu', 'W': 'Wasalu'},
    "dziedzic": {'M': 'Dziedzic', 'D': 'Dziedzica', 'C': 'Dziedzicowi', 'B': 'Dziedzica', 'N': 'Dziedzicem', 'Ms': 'Dziedzicu', 'W': 'Dziedzicu'},
    "dziedziczka": {'M': 'Dziedziczka', 'D': 'Dziedziczki', 'C': 'Dziedziczce', 'B': 'Dziedziczkę', 'N': 'Dziedziczką', 'Ms': 'Dziedziczce', 'W': 'Dziedziczko'},
    "czarodziej": {'M': 'Czarodziej', 'D': 'Czarodzieja', 'C': 'Czarodziejowi', 'B': 'Czarodzieja', 'N': 'Czarodziejem', 'Ms': 'Czarodzieju', 'W': 'Czarodzieju'},
    "czarodziejka": {'M': 'Czarodziejka', 'D': 'Czarodziejki', 'C': 'Czarodziejce', 'B': 'Czarodziejkę', 'N': 'Czarodziejką', 'Ms': 'Czarodziejce', 'W': 'Czarodziejko'},
    "czarnoksiężnica": {'M': 'Czarnoksiężnica', 'D': 'Czarnoksiężnicy', 'C': 'Czarnoksiężnicy', 'B': 'Czarnoksiężnicę', 'N': 'Czarnoksiężnicą', 'Ms': 'Czarnoksiężnicy', 'W': 'Czarnoksiężnico'},
    "uzdrowiciel": {'M': 'Uzdrowiciel', 'D': 'Uzdrowiciela', 'C': 'Uzdrowicielowi', 'B': 'Uzdrowiciela', 'N': 'Uzdrowicielem', 'Ms': 'Uzdrowicielu', 'W': 'Uzdrowicielu'},
    "uzdrowicielka": {'M': 'Uzdrowicielka', 'D': 'Uzdrowicielki', 'C': 'Uzdrowicielce', 'B': 'Uzdrowicielkę', 'N': 'Uzdrowicielką', 'Ms': 'Uzdrowicielce', 'W': 'Uzdrowicielko'},
    "alchemik": {'M': 'Alchemik', 'D': 'Alchemika', 'C': 'Alchemikowi', 'B': 'Alchemika', 'N': 'Alchemikiem', 'Ms': 'Alchemiku', 'W': 'Alchemiku'},
    "aptekarz": {'M': 'Aptekarz', 'D': 'Aptekarza', 'C': 'Aptekarzowi', 'B': 'Aptekarza', 'N': 'Aptekarzem', 'Ms': 'Aptekarzu', 'W': 'Aptekarzu'},
    "zielarz": {'M': 'Zielarz', 'D': 'Zielarza', 'C': 'Zielarzowi', 'B': 'Zielarza', 'N': 'Zielarzem', 'Ms': 'Zielarzu', 'W': 'Zielarzu'},
    "zielarka": {'M': 'Zielarka', 'D': 'Zielarki', 'C': 'Zielarce', 'B': 'Zielarkę', 'N': 'Zielarką', 'Ms': 'Zielarce', 'W': 'Zielarko'},
    "kowal": {'M': 'Kowal', 'D': 'Kowala', 'C': 'Kowalowi', 'B': 'Kowala', 'N': 'Kowalem', 'Ms': 'Kowalu', 'W': 'Kowalu'},
    "płatnerz": {'M': 'Płatnerz', 'D': 'Płatnerza', 'C': 'Płatnerzowi', 'B': 'Płatnerza', 'N': 'Płatnerzem', 'Ms': 'Płatnerzu', 'W': 'Płatnerzu'},
    "kupiec": {'M': 'Kupiec', 'D': 'Kupca', 'C': 'Kupcowi', 'B': 'Kupca', 'N': 'Kupcem', 'Ms': 'Kupcu', 'W': 'Kupcu'},
    "złodziej": {'M': 'Złodziej', 'D': 'Złodzieja', 'C': 'Złodziejowi', 'B': 'Złodzieja', 'N': 'Złodziejem', 'Ms': 'Złodzieju', 'W': 'Złodzieju'},
    "złodziejka": {'M': 'Złodziejka', 'D': 'Złodziejki', 'C': 'Złodziejce', 'B': 'Złodziejkę', 'N': 'Złodziejką', 'Ms': 'Złodziejce', 'W': 'Złodziejko'},
    "szpieg": {'M': 'Szpieg', 'D': 'Szpiega', 'C': 'Szpiegowi', 'B': 'Szpiega', 'N': 'Szpiegiem', 'Ms': 'Szpiegu', 'W': 'Szpiegu'},
    "uczeń": {'M': 'Uczeń', 'D': 'Ucznia', 'C': 'Uczniowi', 'B': 'Ucznia', 'N': 'Uczniem', 'Ms': 'Uczniu', 'W': 'Uczniu'},
    "uczennica": {'M': 'Uczennica', 'D': 'Uczennicy', 'C': 'Uczennicy', 'B': 'Uczennicę', 'N': 'Uczennicą', 'Ms': 'Uczennicy', 'W': 'Uczennico'},
    "nauczyciel": {'M': 'Nauczyciel', 'D': 'Nauczyciela', 'C': 'Nauczycielowi', 'B': 'Nauczyciela', 'N': 'Nauczycielem', 'Ms': 'Nauczycielu', 'W': 'Nauczycielu'},
    "nauczycielka": {'M': 'Nauczycielka', 'D': 'Nauczycielki', 'C': 'Nauczycielce', 'B': 'Nauczycielkę', 'N': 'Nauczycielką', 'Ms': 'Nauczycielce', 'W': 'Nauczycielko'},
    "sługa": {'M': 'Sługa', 'D': 'Sługi', 'C': 'Słudze', 'B': 'Sługę', 'N': 'Sługą', 'Ms': 'Słudze', 'W': 'Sługo'},
    "służąca": {'M': 'Służąca', 'D': 'Służącej', 'C': 'Służącej', 'B': 'Służącą', 'N': 'Służącą', 'Ms': 'Służącej', 'W': 'Służąca'},
    "kamerdyner": {'M': 'Kamerdyner', 'D': 'Kamerdynera', 'C': 'Kamerdynerowi', 'B': 'Kamerdynera', 'N': 'Kamerdynerem', 'Ms': 'Kamerdynerze', 'W': 'Kamerdynerze'},
    "opiekun": {'M': 'Opiekun', 'D': 'Opiekuna', 'C': 'Opiekunowi', 'B': 'Opiekuna', 'N': 'Opiekunem', 'Ms': 'Opiekunie', 'W': 'Opiekunie'},
    "opiekunka": {'M': 'Opiekunka', 'D': 'Opiekunki', 'C': 'Opiekunce', 'B': 'Opiekunkę', 'N': 'Opiekunką', 'Ms': 'Opiekunce', 'W': 'Opiekunko'},
    "prorok": {'M': 'Prorok', 'D': 'Proroka', 'C': 'Prorokowi', 'B': 'Proroka', 'N': 'Prorokiem', 'Ms': 'Proroku', 'W': 'Proroku'},
    "prorokini": {'M': 'Prorokini', 'D': 'Prorokini', 'C': 'Prorokini', 'B': 'Prorokinię', 'N': 'Prorokinią', 'Ms': 'Prorokini', 'W': 'Prorokini'},
    "wyrocznia": {'M': 'Wyrocznia', 'D': 'Wyroczni', 'C': 'Wyroczni', 'B': 'Wyrocznię', 'N': 'Wyrocznią', 'Ms': 'Wyroczni', 'W': 'Wyrocznio'},
    "mnich": {'M': 'Mnich', 'D': 'Mnicha', 'C': 'Mnichowi', 'B': 'Mnicha', 'N': 'Mnichem', 'Ms': 'Mnichu', 'W': 'Mnichu'},
    "mniszka": {'M': 'Mniszka', 'D': 'Mniszki', 'C': 'Mniszce', 'B': 'Mniszkę', 'N': 'Mniszką', 'Ms': 'Mniszce', 'W': 'Mniszko'},
    "biskup": {'M': 'Biskup', 'D': 'Biskupa', 'C': 'Biskupowi', 'B': 'Biskupa', 'N': 'Biskupem', 'Ms': 'Biskupie', 'W': 'Biskupie'},
    "towarzysz": {'M': 'Towarzysz', 'D': 'Towarzysza', 'C': 'Towarzyszowi', 'B': 'Towarzysza', 'N': 'Towarzyszem', 'Ms': 'Towarzyszu', 'W': 'Towarzyszu'},
    "towarzyszka": {'M': 'Towarzyszka', 'D': 'Towarzyszki', 'C': 'Towarzyszce', 'B': 'Towarzyszkę', 'N': 'Towarzyszką', 'Ms': 'Towarzyszce', 'W': 'Towarzyszko'},
    "rywal": {'M': 'Rywal', 'D': 'Rywala', 'C': 'Rywalowi', 'B': 'Rywala', 'N': 'Rywalem', 'Ms': 'Rywalu', 'W': 'Rywalu'},
    "rywalka": {'M': 'Rywalka', 'D': 'Rywalki', 'C': 'Rywalce', 'B': 'Rywalkę', 'N': 'Rywalką', 'Ms': 'Rywalce', 'W': 'Rywalko'},
    "zdrajca": {'M': 'Zdrajca', 'D': 'Zdrajcy', 'C': 'Zdrajcy', 'B': 'Zdrajcę', 'N': 'Zdrajcą', 'Ms': 'Zdrajcy', 'W': 'Zdrajco'},
    "zdrajczyni": {'M': 'Zdrajczyni', 'D': 'Zdrajczyni', 'C': 'Zdrajczyni', 'B': 'Zdrajczynię', 'N': 'Zdrajczynią', 'Ms': 'Zdrajczyni', 'W': 'Zdrajczyni'},
    "wędrowiec": {'M': 'Wędrowiec', 'D': 'Wędrowca', 'C': 'Wędrowcowi', 'B': 'Wędrowca', 'N': 'Wędrowcem', 'Ms': 'Wędrowcu', 'W': 'Wędrowcu'},
    "przewodnik": {'M': 'Przewodnik', 'D': 'Przewodnika', 'C': 'Przewodnikowi', 'B': 'Przewodnika', 'N': 'Przewodnikiem', 'Ms': 'Przewodniku', 'W': 'Przewodniku'},
    "przewodniczka": {'M': 'Przewodniczka', 'D': 'Przewodniczki', 'C': 'Przewodniczce', 'B': 'Przewodniczkę', 'N': 'Przewodniczką', 'Ms': 'Przewodniczce', 'W': 'Przewodniczko'},
    "walkiria": {'M': 'Walkiria', 'D': 'Walkirii', 'C': 'Walkirii', 'B': 'Walkirię', 'N': 'Walkirią', 'Ms': 'Walkirii', 'W': 'Walkirio'},
    "nimfa": {'M': 'Nimfa', 'D': 'Nimfy', 'C': 'Nimfie', 'B': 'Nimfę', 'N': 'Nimfą', 'Ms': 'Nimfie', 'W': 'Nimfo'},
    "syrena": {'M': 'Syrena', 'D': 'Syreny', 'C': 'Syrenie', 'B': 'Syrenę', 'N': 'Syreną', 'Ms': 'Syrenie', 'W': 'Syreno'},
    "sukkub": {'M': 'Sukkub', 'D': 'Sukkuba', 'C': 'Sukkubowi', 'B': 'Sukkuba', 'N': 'Sukkubem', 'Ms': 'Sukkubie', 'W': 'Sukkubie'},
    "elf": {'M': 'Elf', 'D': 'Elfa', 'C': 'Elfowi', 'B': 'Elfa', 'N': 'Elfem', 'Ms': 'Elfie', 'W': 'Elfie'},
    "elfka": {'M': 'Elfka', 'D': 'Elfki', 'C': 'Elfce', 'B': 'Elfkę', 'N': 'Elfką', 'Ms': 'Elfce', 'W': 'Elfko'},
    "krasnolud": {'M': 'Krasnolud', 'D': 'Krasnoluda', 'C': 'Krasnoludowi', 'B': 'Krasnoluda', 'N': 'Krasnoludem', 'Ms': 'Krasnoludzie', 'W': 'Krasnoludzie'},
    "krasnoludka": {'M': 'Krasnoludka', 'D': 'Krasnoludki', 'C': 'Krasnoludce', 'B': 'Krasnoludkę', 'N': 'Krasnoludką', 'Ms': 'Krasnoludce', 'W': 'Krasnoludko'},
    "ork": {'M': 'Ork', 'D': 'Orka', 'C': 'Orkowi', 'B': 'Orka', 'N': 'Orkiem', 'Ms': 'Orku', 'W': 'Orku'},
    "goblin": {'M': 'Goblin', 'D': 'Goblina', 'C': 'Goblinowi', 'B': 'Goblina', 'N': 'Goblinem', 'Ms': 'Goblinie', 'W': 'Goblinie'},
    "olbrzym": {'M': 'Olbrzym', 'D': 'Olbrzyma', 'C': 'Olbrzymowi', 'B': 'Olbrzyma', 'N': 'Olbrzymem', 'Ms': 'Olbrzymie', 'W': 'Olbrzymie'},
    "tytan": {'M': 'Tytan', 'D': 'Tytana', 'C': 'Tytanowi', 'B': 'Tytana', 'N': 'Tytanem', 'Ms': 'Tytanie', 'W': 'Tytanie'},
    "golem": {'M': 'Golem', 'D': 'Golema', 'C': 'Golemowi', 'B': 'Golema', 'N': 'Golemem', 'Ms': 'Golemie', 'W': 'Golemie'},
    "upiór": {'M': 'Upiór', 'D': 'Upiora', 'C': 'Upiorowi', 'B': 'Upiora', 'N': 'Upiorem', 'Ms': 'Upiorze', 'W': 'Upiorze'},
    "wilkołak": {'M': 'Wilkołak', 'D': 'Wilkołaka', 'C': 'Wilkołakowi', 'B': 'Wilkołaka', 'N': 'Wilkołakiem', 'Ms': 'Wilkołaku', 'W': 'Wilkołaku'},
    "wiedźma": {'M': 'Wiedźma', 'D': 'Wiedźmy', 'C': 'Wiedźmie', 'B': 'Wiedźmę', 'N': 'Wiedźmą', 'Ms': 'Wiedźmie', 'W': 'Wiedźmo'},
    "gildia": {'M': 'Gildia', 'D': 'Gildii', 'C': 'Gildii', 'B': 'Gildię', 'N': 'Gildią', 'Ms': 'Gildii', 'W': 'Gildio'},
    "bractwo": {'M': 'Bractwo', 'D': 'Bractwa', 'C': 'Bractwu', 'B': 'Bractwo', 'N': 'Bractwem', 'Ms': 'Bractwie', 'W': 'Bractwo'},
    "sojusz": {'M': 'Sojusz', 'D': 'Sojuszu', 'C': 'Sojuszowi', 'B': 'Sojusz', 'N': 'Sojuszem', 'Ms': 'Sojuszu', 'W': 'Sojuszu'},
    "koalicja": {'M': 'Koalicja', 'D': 'Koalicji', 'C': 'Koalicji', 'B': 'Koalicję', 'N': 'Koalicją', 'Ms': 'Koalicji', 'W': 'Koalicjo'},
    "akademia": {'M': 'Akademia', 'D': 'Akademii', 'C': 'Akademii', 'B': 'Akademię', 'N': 'Akademią', 'Ms': 'Akademii', 'W': 'Akademio'},
    "senat": {'M': 'Senat', 'D': 'Senatu', 'C': 'Senatowi', 'B': 'Senat', 'N': 'Senatem', 'Ms': 'Senacie', 'W': 'Senacie'},
    "republika": {'M': 'Republika', 'D': 'Republiki', 'C': 'Republice', 'B': 'Republikę', 'N': 'Republiką', 'Ms': 'Republice', 'W': 'Republiko'},
    "imperium": {'M': 'Imperium', 'D': 'Imperium', 'C': 'Imperium', 'B': 'Imperium', 'N': 'Imperium', 'Ms': 'Imperium', 'W': 'Imperium'},
    "cesarstwo": {'M': 'Cesarstwo', 'D': 'Cesarstwa', 'C': 'Cesarstwu', 'B': 'Cesarstwo', 'N': 'Cesarstwem', 'Ms': 'Cesarstwie', 'W': 'Cesarstwo'},
    "królestwo": {'M': 'Królestwo', 'D': 'Królestwa', 'C': 'Królestwu', 'B': 'Królestwo', 'N': 'Królestwem', 'Ms': 'Królestwie', 'W': 'Królestwo'},
    "księstwo": {'M': 'Księstwo', 'D': 'Księstwa', 'C': 'Księstwu', 'B': 'Księstwo', 'N': 'Księstwem', 'Ms': 'Księstwie', 'W': 'Księstwo'},
    "domena": {'M': 'Domena', 'D': 'Domeny', 'C': 'Domenie', 'B': 'Domenę', 'N': 'Domeną', 'Ms': 'Domenie', 'W': 'Domeno'},
    "kraina": {'M': 'Kraina', 'D': 'Krainy', 'C': 'Krainie', 'B': 'Krainę', 'N': 'Krainą', 'Ms': 'Krainie', 'W': 'Kraino'},
    "armia": {'M': 'Armia', 'D': 'Armii', 'C': 'Armii', 'B': 'Armię', 'N': 'Armią', 'Ms': 'Armii', 'W': 'Armio'},
    "oddział": {'M': 'Oddział', 'D': 'Oddziału', 'C': 'Oddziałowi', 'B': 'Oddział', 'N': 'Oddziałem', 'Ms': 'Oddziale', 'W': 'Oddziale'},
    "legion": {'M': 'Legion', 'D': 'Legionu', 'C': 'Legionowi', 'B': 'Legion', 'N': 'Legionem', 'Ms': 'Legionie', 'W': 'Legionie'},
    "flota": {'M': 'Flota', 'D': 'Floty', 'C': 'Flocie', 'B': 'Flotę', 'N': 'Flotą', 'Ms': 'Flocie', 'W': 'Floto'},
    "cytadela": {'M': 'Cytadela', 'D': 'Cytadeli', 'C': 'Cytadeli', 'B': 'Cytadelę', 'N': 'Cytadelą', 'Ms': 'Cytadeli', 'W': 'Cytadelo'},
    "bastion": {'M': 'Bastion', 'D': 'Bastionu', 'C': 'Bastionowi', 'B': 'Bastion', 'N': 'Bastionem', 'Ms': 'Bastionie', 'W': 'Bastionie'},
    "forteca": {'M': 'Forteca', 'D': 'Fortecy', 'C': 'Fortecy', 'B': 'Fortecę', 'N': 'Fortecą', 'Ms': 'Fortecy', 'W': 'Forteco'},
    "pałac": {'M': 'Pałac', 'D': 'Pałacu', 'C': 'Pałacowi', 'B': 'Pałac', 'N': 'Pałacem', 'Ms': 'Pałacu', 'W': 'Pałacu'},
    "katedra": {'M': 'Katedra', 'D': 'Katedry', 'C': 'Katedrze', 'B': 'Katedrę', 'N': 'Katedrą', 'Ms': 'Katedrze', 'W': 'Katedro'},
    "sanktuarium": {'M': 'Sanktuarium', 'D': 'Sanktuarium', 'C': 'Sanktuarium', 'B': 'Sanktuarium', 'N': 'Sanktuarium', 'Ms': 'Sanktuarium', 'W': 'Sanktuarium'},
    "kaplica": {'M': 'Kaplica', 'D': 'Kaplicy', 'C': 'Kaplicy', 'B': 'Kaplicę', 'N': 'Kaplicą', 'Ms': 'Kaplicy', 'W': 'Kaplico'},
    "klasztor": {'M': 'Klasztor', 'D': 'Klasztoru', 'C': 'Klasztorowi', 'B': 'Klasztor', 'N': 'Klasztorem', 'Ms': 'Klasztorze', 'W': 'Klasztorze'},
    "krypta": {'M': 'Krypta', 'D': 'Krypty', 'C': 'Krypcie', 'B': 'Kryptę', 'N': 'Kryptą', 'Ms': 'Krypcie', 'W': 'Krypto'},
    "grobowiec": {'M': 'Grobowiec', 'D': 'Grobowca', 'C': 'Grobowcowi', 'B': 'Grobowiec', 'N': 'Grobowcem', 'Ms': 'Grobowcu', 'W': 'Grobowcu'},
    "katakumby": {'M': 'Katakumby', 'D': 'Katakumb', 'C': 'Katakumbom', 'B': 'Katakumby', 'N': 'Katakumbami', 'Ms': 'Katakumbach', 'W': 'Katakumby'},
    "labirynt": {'M': 'Labirynt', 'D': 'Labiryntu', 'C': 'Labiryntowi', 'B': 'Labirynt', 'N': 'Labiryntem', 'Ms': 'Labiryncie', 'W': 'Labiryncie'},
    "loch": {'M': 'Loch', 'D': 'Lochu', 'C': 'Lochowi', 'B': 'Loch', 'N': 'Lochem', 'Ms': 'Lochu', 'W': 'Lochu'},
    "miasto": {'M': 'Miasto', 'D': 'Miasta', 'C': 'Miastu', 'B': 'Miasto', 'N': 'Miastem', 'Ms': 'Mieście', 'W': 'Miasto'},
    "wioska": {'M': 'Wioska', 'D': 'Wioski', 'C': 'Wiosce', 'B': 'Wioskę', 'N': 'Wioską', 'Ms': 'Wiosce', 'W': 'Wiosko'},
    "wieś": {'M': 'Wieś', 'D': 'Wsi', 'C': 'Wsi', 'B': 'Wieś', 'N': 'Wsią', 'Ms': 'Wsi', 'W': 'Wsi'},
    "port": {'M': 'Port', 'D': 'Portu', 'C': 'Portowi', 'B': 'Port', 'N': 'Portem', 'Ms': 'Porcie', 'W': 'Porcie'},
    "przystań": {'M': 'Przystań', 'D': 'Przystani', 'C': 'Przystani', 'B': 'Przystań', 'N': 'Przystanią', 'Ms': 'Przystani', 'W': 'Przystani'},
    "plac": {'M': 'Plac', 'D': 'Placu', 'C': 'Placowi', 'B': 'Plac', 'N': 'Placem', 'Ms': 'Placu', 'W': 'Placu'},
    "ulica": {'M': 'Ulica', 'D': 'Ulicy', 'C': 'Ulicy', 'B': 'Ulicę', 'N': 'Ulicą', 'Ms': 'Ulicy', 'W': 'Ulico'},
    "zaułek": {'M': 'Zaułek', 'D': 'Zaułka', 'C': 'Zaułkowi', 'B': 'Zaułek', 'N': 'Zaułkiem', 'Ms': 'Zaułku', 'W': 'Zaułku'},
    "las": {'M': 'Las', 'D': 'Lasu', 'C': 'Lasowi', 'B': 'Las', 'N': 'Lasem', 'Ms': 'Lesie', 'W': 'Lesie'},
    "puszcza": {'M': 'Puszcza', 'D': 'Puszczy', 'C': 'Puszczy', 'B': 'Puszczę', 'N': 'Puszczą', 'Ms': 'Puszczy', 'W': 'Puszczo'},
    "bór": {'M': 'Bór', 'D': 'Boru', 'C': 'Borowi', 'B': 'Bór', 'N': 'Borem', 'Ms': 'Borze', 'W': 'Borze'},
    "gaj": {'M': 'Gaj', 'D': 'Gaju', 'C': 'Gajowi', 'B': 'Gaj', 'N': 'Gajem', 'Ms': 'Gaju', 'W': 'Gaju'},
    "szczyt": {'M': 'Szczyt', 'D': 'Szczytu', 'C': 'Szczytowi', 'B': 'Szczyt', 'N': 'Szczytem', 'Ms': 'Szczycie', 'W': 'Szczycie'},
    "wąwóz": {'M': 'Wąwóz', 'D': 'Wąwozu', 'C': 'Wąwozowi', 'B': 'Wąwóz', 'N': 'Wąwozem', 'Ms': 'Wąwozie', 'W': 'Wąwozie'},
    "polana": {'M': 'Polana', 'D': 'Polany', 'C': 'Polanie', 'B': 'Polanę', 'N': 'Polaną', 'Ms': 'Polanie', 'W': 'Polano'},
    "bagno": {'M': 'Bagno', 'D': 'Bagna', 'C': 'Bagnu', 'B': 'Bagno', 'N': 'Bagnem', 'Ms': 'Bagnie', 'W': 'Bagno'},
    "oaza": {'M': 'Oaza', 'D': 'Oazy', 'C': 'Oazie', 'B': 'Oazę', 'N': 'Oazą', 'Ms': 'Oazie', 'W': 'Oazo'},
    "ocean": {'M': 'Ocean', 'D': 'Oceanu', 'C': 'Oceanowi', 'B': 'Ocean', 'N': 'Oceanem', 'Ms': 'Oceanie', 'W': 'Oceanie'},
    "wyspa": {'M': 'Wyspa', 'D': 'Wyspy', 'C': 'Wyspie', 'B': 'Wyspę', 'N': 'Wyspą', 'Ms': 'Wyspie', 'W': 'Wyspo'},
    "archipelag": {'M': 'Archipelag', 'D': 'Archipelagu', 'C': 'Archipelagowi', 'B': 'Archipelag', 'N': 'Archipelagiem', 'Ms': 'Archipelagu', 'W': 'Archipelagu'},
    "półwysep": {'M': 'Półwysep', 'D': 'Półwyspu', 'C': 'Półwyspowi', 'B': 'Półwysep', 'N': 'Półwyspem', 'Ms': 'Półwyspie', 'W': 'Półwyspie'},
    "wybrzeże": {'M': 'Wybrzeże', 'D': 'Wybrzeża', 'C': 'Wybrzeżu', 'B': 'Wybrzeże', 'N': 'Wybrzeżem', 'Ms': 'Wybrzeżu', 'W': 'Wybrzeże'},
    "przepaść": {'M': 'Przepaść', 'D': 'Przepaści', 'C': 'Przepaści', 'B': 'Przepaść', 'N': 'Przepaścią', 'Ms': 'Przepaści', 'W': 'Przepaści'},
    "otchłań": {'M': 'Otchłań', 'D': 'Otchłani', 'C': 'Otchłani', 'B': 'Otchłań', 'N': 'Otchłanią', 'Ms': 'Otchłani', 'W': 'Otchłani'},
    "pustka": {'M': 'Pustka', 'D': 'Pustki', 'C': 'Pustce', 'B': 'Pustkę', 'N': 'Pustką', 'Ms': 'Pustce', 'W': 'Pustko'},
    "kryształ": {'M': 'Kryształ', 'D': 'Kryształu', 'C': 'Kryształowi', 'B': 'Kryształ', 'N': 'Kryształem', 'Ms': 'Krysztale', 'W': 'Krysztale'},
    "klejnot": {'M': 'Klejnot', 'D': 'Klejnotu', 'C': 'Klejnotowi', 'B': 'Klejnot', 'N': 'Klejnotem', 'Ms': 'Klejnocie', 'W': 'Klejnocie'},
    "diament": {'M': 'Diament', 'D': 'Diamentu', 'C': 'Diamentowi', 'B': 'Diament', 'N': 'Diamentem', 'Ms': 'Diamencie', 'W': 'Diamencie'},
    "perła": {'M': 'Perła', 'D': 'Perły', 'C': 'Perle', 'B': 'Perłę', 'N': 'Perłą', 'Ms': 'Perle', 'W': 'Perło'},
    "rubin": {'M': 'Rubin', 'D': 'Rubinu', 'C': 'Rubinowi', 'B': 'Rubin', 'N': 'Rubinem', 'Ms': 'Rubinie', 'W': 'Rubinie'},
    "szmaragd": {'M': 'Szmaragd', 'D': 'Szmaragdu', 'C': 'Szmaragdowi', 'B': 'Szmaragd', 'N': 'Szmaragdem', 'Ms': 'Szmaragdzie', 'W': 'Szmaragdzie'},
    "runa": {'M': 'Runa', 'D': 'Runy', 'C': 'Runie', 'B': 'Runę', 'N': 'Runą', 'Ms': 'Runie', 'W': 'Runo'},
    "talizman": {'M': 'Talizman', 'D': 'Talizmanu', 'C': 'Talizmanowi', 'B': 'Talizman', 'N': 'Talizmanem', 'Ms': 'Talizmanie', 'W': 'Talizmanie'},
    "relikwia": {'M': 'Relikwia', 'D': 'Relikwii', 'C': 'Relikwii', 'B': 'Relikwię', 'N': 'Relikwią', 'Ms': 'Relikwii', 'W': 'Relikwio'},
    "artefakt": {'M': 'Artefakt', 'D': 'Artefaktu', 'C': 'Artefaktowi', 'B': 'Artefakt', 'N': 'Artefaktem', 'Ms': 'Artefakcie', 'W': 'Artefakcie'},
    "laska": {'M': 'Laska', 'D': 'Laski', 'C': 'Lasce', 'B': 'Laskę', 'N': 'Laską', 'Ms': 'Lasce', 'W': 'Lasko'},
    "kostur": {'M': 'Kostur', 'D': 'Kostura', 'C': 'Kosturowi', 'B': 'Kostur', 'N': 'Kosturem', 'Ms': 'Kosturze', 'W': 'Kosturze'},
    "topór": {'M': 'Topór', 'D': 'Topora', 'C': 'Toporowi', 'B': 'Topór', 'N': 'Toporem', 'Ms': 'Toporze', 'W': 'Toporze'},
    "włócznia": {'M': 'Włócznia', 'D': 'Włóczni', 'C': 'Włóczni', 'B': 'Włócznię', 'N': 'Włócznią', 'Ms': 'Włóczni', 'W': 'Włócznio'},
    "pika": {'M': 'Pika', 'D': 'Piki', 'C': 'Pice', 'B': 'Pikę', 'N': 'Piką', 'Ms': 'Pice', 'W': 'Piko'},
    "halabarda": {'M': 'Halabarda', 'D': 'Halabardy', 'C': 'Halabardzie', 'B': 'Halabardę', 'N': 'Halabardą', 'Ms': 'Halabardzie', 'W': 'Halabardo'},
    "kusza": {'M': 'Kusza', 'D': 'Kuszy', 'C': 'Kuszy', 'B': 'Kuszę', 'N': 'Kuszą', 'Ms': 'Kuszy', 'W': 'Kuszo'},
    "szpada": {'M': 'Szpada', 'D': 'Szpady', 'C': 'Szpadzie', 'B': 'Szpadę', 'N': 'Szpadą', 'Ms': 'Szpadzie', 'W': 'Szpado'},
    "rapier": {'M': 'Rapier', 'D': 'Rapiera', 'C': 'Rapierowi', 'B': 'Rapier', 'N': 'Rapierem', 'Ms': 'Rapierze', 'W': 'Rapierze'},
    "szabla": {'M': 'Szabla', 'D': 'Szabli', 'C': 'Szabli', 'B': 'Szablę', 'N': 'Szablą', 'Ms': 'Szabli', 'W': 'Szablo'},
    "pancerz": {'M': 'Pancerz', 'D': 'Pancerza', 'C': 'Pancerzowi', 'B': 'Pancerz', 'N': 'Pancerzem', 'Ms': 'Pancerzu', 'W': 'Pancerzu'},
    "rękawica": {'M': 'Rękawica', 'D': 'Rękawicy', 'C': 'Rękawicy', 'B': 'Rękawicę', 'N': 'Rękawicą', 'Ms': 'Rękawicy', 'W': 'Rękawico'},
    "płaszcz": {'M': 'Płaszcz', 'D': 'Płaszcza', 'C': 'Płaszczowi', 'B': 'Płaszcz', 'N': 'Płaszczem', 'Ms': 'Płaszczu', 'W': 'Płaszczu'},
    "szata": {'M': 'Szata', 'D': 'Szaty', 'C': 'Szacie', 'B': 'Szatę', 'N': 'Szatą', 'Ms': 'Szacie', 'W': 'Szato'},
    "maska": {'M': 'Maska', 'D': 'Maski', 'C': 'Masce', 'B': 'Maskę', 'N': 'Maską', 'Ms': 'Masce', 'W': 'Masko'},
    "zegar": {'M': 'Zegar', 'D': 'Zegara', 'C': 'Zegarowi', 'B': 'Zegar', 'N': 'Zegarem', 'Ms': 'Zegarze', 'W': 'Zegarze'},
    "klepsydra": {'M': 'Klepsydra', 'D': 'Klepsydry', 'C': 'Klepsydrze', 'B': 'Klepsydrę', 'N': 'Klepsydrą', 'Ms': 'Klepsydrze', 'W': 'Klepsydro'},
    "książka": {'M': 'Książka', 'D': 'Książki', 'C': 'Książce', 'B': 'Książkę', 'N': 'Książką', 'Ms': 'Książce', 'W': 'Książko'},
    "sekret": {'M': 'Sekret', 'D': 'Sekretu', 'C': 'Sekretowi', 'B': 'Sekret', 'N': 'Sekretem', 'Ms': 'Sekrecie', 'W': 'Sekrecie'},
    "tajemnica": {'M': 'Tajemnica', 'D': 'Tajemnicy', 'C': 'Tajemnicy', 'B': 'Tajemnicę', 'N': 'Tajemnicą', 'Ms': 'Tajemnicy', 'W': 'Tajemnico'},
}

KNOWN_HEAD_NOUNS = {
    "księga", "księgi", "miecz", "miecze", "lanca", "tarcza", "zakon", "dolina", "pieczęć",
    "oko", "ręka", "pierścień", "amulet", "zwierciadło", "kielich", "zwój", "zwoje",
    "królowa", "król", "władca", "władczyni", "cesarz", "cesarzowa", "książę", "księżniczka",
    "mistrz", "mistrzyni", "demon", "demonica", "pani", "pan", "lord", "bóg", "bogini",
    "kamień", "drzewo", "kraj", "wyspa", "wieża", "zamek", "twierdza", "świątynia", "krew", "duch",
    "serce", "płomień", "brama", "wrota", "światło", "cień", "korona", "tron",
    "ród", "znak", "kosa", "młot", "sztylet", "łuk", "strzała", "zbroja", "hełm",
    "różdżka", "książka", "kodeks", "tajemnica", "tajemnice", "sekret", "sekrety",
    "opowieść", "legenda", "pieśń", "hymn", "kronika", "kroniki", "droga", "szlak",
    "most", "rzeka", "jezioro", "morze", "góra", "góry", "pustynia", "pakt",
    "przymierze", "zemsta", "klątwa", "gniew", "bunt", "upadek", "powrót",
    "narodziny", "koniec", "początek", "córka", "syn", "matka", "ojciec",
    "brat", "siostra", "bohater", "wojownik", "rycerz", "mag", "czarnoksiężnik", "kapłan",
    "dowódca", "zabójca", "obrońca", "łowca", "strażnik", "generał",
    "arcykapłan", "arcymag", "szaman", "czarownik", "czarownica", "bestia", "potwór",
    "smok", "bóstwo", "anioł", "wampir", "widmo", "zjawa", "wojowniczka", "bohaterka",
    "kapłanka"
}

TOPONYMIC_INSTITUTION_HEAD_NOUNS = {
    "miasto", "wieża", "gildia", "akademia", "cytadela", "las", "zamek", "twierdza",
    "dolina", "rzeka", "jezioro", "morze", "góra", "pałac", "katedra", "sanktuarium",
    "kaplica", "klasztor", "krypta", "grobowiec", "katakumby", "labirynt", "loch",
    "wioska", "wieś", "port", "przystań", "plac", "ulica", "zaułek", "puszcza",
    "bór", "gaj", "szczyt", "wąwóz", "polana", "bagno", "oaza", "ocean", "wyspa",
    "archipelag", "półwysep", "wybrzeże", "przepaść", "otchłań", "pustka", "bractwo",
    "zakon", "sojusz", "koalicja", "senat", "republika", "imperium", "cesarstwo",
    "królestwo", "księstwo", "domena", "kraina", "armia", "oddział", "legion", "flota",
    "bastion", "forteca", "brama", "wrota", "kościół"
}

_PREPS_GEN = {"do", "od", "z", "ze", "dla", "bez", "u", "koło", "obok", "blisko", "wokół", "dookoła", "pośród", "wśród", "spod", "zza", "znad", "wzdłuż", "podczas", "mimo", "według", "wskutek", "wobec", "naprzeciw"}
_PREPS_LOC = {"w", "we", "na", "po", "o", "przy"}
_PREPS_INST = {"za", "pod", "pode", "nad", "nade", "przed", "przede", "między", "pomiędzy", "poza"}
_PREPS_DAT = {"dzięki", "przeciw", "przeciwko", "ku", "wbrew"}
_ALL_TOPONYM_PREPS = _PREPS_GEN | _PREPS_LOC | _PREPS_INST | _PREPS_DAT
_PREP_PAT = "|".join(sorted(_ALL_TOPONYM_PREPS, key=len, reverse=True))
_HEAD_PAT = "|".join([k.capitalize() for k in TOPONYMIC_INSTITUTION_HEAD_NOUNS])
_RE_TOPONYMIC_PREP_GOV = re.compile(rf"\b({_PREP_PAT})\s+({_HEAD_PAT})\b(\s+[A-ZĄĆĘŁŃÓŚŹŻ0-9][a-ząćęłńóśźż0-9]*)", re.IGNORECASE)

def sanitize_toponymic_preposition_governance(text: str) -> str:
    """
    Sanitizes nominative freezing of toponym and institution head nouns governed by Polish prepositions
    (Filar CLXXXIV / Zasada 15 AGENTS.md / 0.00 PLN).
    Ensures that generic category head nouns (miasto, wieża, gildia, akademia, cytadela, las, etc.)
    inflect to the proper grammatical case governed by the preceding preposition (Dopełniacz, Miejscownik,
    Narzędnik, Celownik), while preserving proper names/genitive modifiers and lowercase orthography.
    """
    if not text:
        return ""

    def _repl_toponym_prep(m):
        prep = m.group(1)
        head = m.group(2)
        rest = m.group(3)
        prep_l = prep.lower()
        head_l = head.lower()
        d = KNOWN_HEAD_NOUN_DECLENSIONS.get(head_l)
        if not d:
            return m.group(0)
        if prep_l in _PREPS_GEN:
            case = "D"
        elif prep_l in _PREPS_LOC:
            case = "Ms"
        elif prep_l in _PREPS_INST:
            case = "N"
        elif prep_l in _PREPS_DAT:
            case = "C"
        else:
            case = "D"
        decl_head = d.get(case, head).lower()
        return f"{prep} {decl_head}{rest}"

    return _RE_TOPONYMIC_PREP_GOV.sub(_repl_toponym_prep, text)


def generate_polish_name_declension(name: str, gender: str = "UNKNOWN") -> Dict[str, str]:
    """
    Generates 7 grammatical cases for Japanese / foreign anime character names
    following standard Polish literary AVT phonological rules.
    """
    n = name.strip()
    g = gender.upper()
    is_male = (g == "MALE" or "MĘSK" in g)
    is_female = (g == "FEMALE" or "KOBIETA" in g or "ŻEŃSK" in g or g == "FEMININE" or g == "DZIEWCZYNA" or g == "DZIEWCZYNKA")
    if not is_female and not is_male:
        if has_japanese_male_name_suffix(n) or is_official_or_court_consonant_name(n):
            is_male = True
        elif (n.lower() in INVARIABLE_JAPANESE_FEMALE_NAMES or n.lower() in FOREIGN_FEMALE_CONSONANT_NAMES or n.lower() in FEMALE_LEXICON_NAMES or is_inherently_female_name(n)):
            is_female = True
    if not n:
        return {}
    if len(n) <= 1 or not any(c.isalpha() for c in n) or not is_valid_anthroponymic_phonotactics(n):
        return {"M": n, "D": n, "C": n, "B": n, "N": n, "Ms": n, "W": n}

    if n.lower() in KNOWN_HEAD_NOUN_DECLENSIONS:
        is_cap = n[0].isupper()
        return {
            c: (v.capitalize() if is_cap else v.lower())
            for c, v in KNOWN_HEAD_NOUN_DECLENSIONS[n.lower()].items()
        }

    # Ochrona przed podwójną deklinacją: formy odmienione oraz złożone deskrypcje (T(x) = x)
    if is_complex_description(n) or is_adjectival_oblique_token(n):
        return {"M": n, "D": n, "C": n, "B": n, "N": n, "Ms": n, "W": n}

    words = n.split()
    if len(words) > 1:
        # Check for Numeral + Plural Genitive Noun (e.g. Czterech Jeźdźców, Siedmiu Magów)
        NUMERAL_PREFIXES = {"dwóch", "trzech", "czterech", "pięciu", "sześciu", "siedmiu", "ośmiu", "dziewięciu", "dziesięciu", "dwunastu", "wielu"}
        if words[0].lower() in NUMERAL_PREFIXES and any(w.lower().endswith(("ów", "ow", "om", "ami", "ach")) for w in words[1:]):
            return {"M": n, "D": n, "C": n, "B": n, "N": n, "Ms": n, "W": n}

        # A. Check for prepositional complement: "X z Y", "X ze stali", "X do Y"
        # e.g. "Księga Wiedzy z Krainy", "Miecz z Północy"
        for prep_idx, w_p in enumerate(words):
            if prep_idx > 0 and w_p.lower() in ("z", "ze", "od", "do", "w", "we", "o", "pod") and prep_idx < len(words) - 1:
                head_part = " ".join(words[:prep_idx])
                prep_part = " ".join(words[prep_idx:])
                head_decl = generate_polish_name_declension(head_part, gender)
                if head_decl and head_decl.get("M"):
                    return {
                        case: f"{head_decl.get(case, head_part)} {prep_part}"
                        for case in ["M", "D", "C", "B", "N", "Ms", "W"]
                    }

        # B. Check for Noun + Genitive Attribute (Przydawka dopełniaczowa)
        # e.g. "Księga Magii", "Zakon Feniksa", "Dolina Rozpaczy", "Miecz Prawdy", "Władca Złudzeń", "Demon Krwi"
        first_lower = words[0].lower()
        if (first_lower in KNOWN_HEAD_NOUNS or first_lower in KNOWN_HEAD_NOUN_DECLENSIONS) and len(words) >= 2 and not (len(words) == 2 and is_polish_adjective(words[1])):
            if first_lower in KNOWN_HEAD_NOUN_DECLENSIONS:
                is_cap = words[0][0].isupper()
                head_decl = {
                    c: (v.capitalize() if is_cap else v.lower())
                    for c, v in KNOWN_HEAD_NOUN_DECLENSIONS[first_lower].items()
                }
            else:
                head_gender = "FEMALE" if (first_lower.endswith("a") or first_lower in ("pieczęć", "krew", "opowieść", "pieśń")) else (
                    "NEUTER" if first_lower.endswith(("o", "e")) else (
                        "MALE" if first_lower in ("syn", "ojciec", "brat", "bohater", "wojownik", "rycerz", "mag", "czarnoksiężnik", "kapłan", "król", "władca", "cesarz", "książę", "mistrz", "arcykapłan", "arcymag", "szaman", "czarownik", "anioł", "wampir", "smok", "potwór") else "MALE_INANIMATE"
                    )
                )
                head_decl = generate_polish_name_declension(words[0], "FEMALE" if head_gender == "FEMALE" else ("MALE" if head_gender == "MALE" else "UNKNOWN"))
            attr_phrase = " ".join(words[1:])
            return {
                case: f"{head_decl.get(case, words[0])} {attr_phrase}"
                for case in ["M", "D", "C", "B", "N", "Ms", "W"]
            }

        # B0. Check for Bipartite Female Name (Operacja H3, Standard 9.10.1)
        # e.g. [Imię 1] [Nazwisko 1] -> [Imię 1] [Nazwisko 1]; [Imię 2] [Nazwisko 2] -> [Imię 2 D] [Nazwisko 2]; [Imię 3] [Nazwisko 3] -> [Imię 3 D] [Nazwisko 3 D]
        if len(words) == 2 and is_female:
            w1, w2 = words[0], words[1]
            w1_l = w1.lower()
            if w1_l not in KNOWN_HEAD_NOUNS and w1_l not in KNOWN_HEAD_NOUN_DECLENSIONS and w1_l not in NUMERAL_PREFIXES:
                if w1.endswith(("a", "A")):
                    d1 = generate_polish_name_declension(w1, "FEMALE")
                else:
                    d1 = {c: w1 for c in ("M", "D", "C", "B", "N", "Ms", "W")}

                if w2.endswith(("a", "A")) and w2.lower() not in INDECLINABLE_FRENCH_TOPONYMS:
                    d2 = generate_polish_name_declension(w2, "FEMALE")
                else:
                    d2 = {c: w2 for c in ("M", "D", "C", "B", "N", "Ms", "W")}

                return {c: f"{d1[c]} {d2[c]}" for c in ("M", "D", "C", "B", "N", "Ms", "W")}

        # B2. Check for 2-word compound with genitive modifier (Operacja 2C.9, T4.12)
        # e.g. "Władca Ciemności", "Książę Piekieł", "Mistrz Miecza", "Rycerz Zakonu"
        if len(words) == 2:
            w1, w2 = words[0], words[1]
            w2_l = w2.lower()
            if not is_polish_adjective(w1) and not is_polish_adjective(w2):
                if not (w1.lower().endswith("a") and w2_l.endswith("a")) and not (is_female and w2_l.endswith("a")):
                    if w2_l.endswith(("a", "i", "y", "ów", "ow", "eń", "ek", "om", "ycy")):
                        head_decl = generate_polish_name_declension(w1, gender)
                        if head_decl and head_decl.get("M"):
                            return {
                                case: f"{head_decl.get(case, w1)} {w2}"
                                for case in ["M", "D", "C", "B", "N", "Ms", "W"]
                            }

        # C. Check for Adjective + Noun (or Noun + Adjective)
        if len(words) == 2:
            w1, w2 = words[0], words[1]
            if is_polish_adjective(w1) and not is_polish_adjective(w2):
                adj_g = "FEMALE" if w1.lower().endswith("a") else ("NEUTER" if w1.lower().endswith("e") else (gender if gender != "UNKNOWN" else ("FEMALE" if w2.lower().endswith("a") else "MALE")))
                adj_decl = generate_polish_adjective_declension(w1, adj_g, is_animate=True)
                noun_decl = generate_polish_name_declension(w2, adj_g)
                return {
                    case: f"{adj_decl.get(case, w1)} {noun_decl.get(case, w2)}"
                    for case in ["M", "D", "C", "B", "N", "Ms", "W"]
                }
            elif is_polish_adjective(w2) and not is_polish_adjective(w1):
                adj_g = "FEMALE" if w2.lower().endswith("a") else ("NEUTER" if w2.lower().endswith("e") else (gender if gender != "UNKNOWN" else ("FEMALE" if w1.lower().endswith("a") else "MALE")))
                is_anim = False if w1.lower() in KNOWN_HEAD_NOUN_DECLENSIONS else True
                noun_decl = generate_polish_name_declension(w1, adj_g)
                adj_decl = generate_polish_adjective_declension(w2, adj_g, is_animate=is_anim)
                return {
                    case: f"{noun_decl.get(case, w1)} {adj_decl.get(case, w2)}"
                    for case in ["M", "D", "C", "B", "N", "Ms", "W"]
                }

        # C2. Check for Modifier Prefix (Young Hero, Kid Knight, Dark Lord, etc.)
        if MODIFIER_PREFIX_RE.match(n):
            m_pref = MODIFIER_PREFIX_RE.match(n)
            base_word = m_pref.group(1).strip()
            prefix_word = n[:len(n) - len(base_word)].strip()
            base_decl = generate_polish_name_declension(base_word, gender)
            if base_decl and base_decl.get("M"):
                return {
                    case: f"{prefix_word} {base_decl.get(case, base_word)}"
                    for case in ["M", "D", "C", "B", "N", "Ms", "W"]
                }

        # D. Default multi-word: decline each word (e.g. Brandon Heat, John Smith)
        def _decline_sub_word(w):
            if is_adjectival_oblique_token(w):
                return {"M": w, "D": w, "C": w, "B": w, "N": w, "Ms": w, "W": w}
            if w.lower().endswith(("ów", "ow", "om", "ami", "ach")):
                return {"M": w, "D": w, "C": w, "B": w, "N": w, "Ms": w, "W": w}
            return generate_polish_name_declension(w, gender)
        sub_decls = [_decline_sub_word(w) for w in words]
        if all(sub_decls):
            raw_multi = {
                case: " ".join(d.get(case, w) for d, w in zip(sub_decls, words))
                for case in ["M", "D", "C", "B", "N", "Ms", "W"]
            }
            if words[-1].lower().endswith("tz"):
                title_words = {
                    "kapitan", "kapitanie", "pan", "panie", "mistrz", "mistrzu", "doktor", "doktorze",
                    "generał", "generale", "komandor", "komandorze", "major", "majorze",
                    "pułkownik", "pułkowniku", "porucznik", "poruczniku", "lord", "lordzie",
                    "ojciec", "ojcze", "brat", "bracie", "książę"
                }
                if any(w.lower() in title_words for w in words[:-1]):
                    raw_multi["W"] = " ".join(
                        (words[i] if i == len(words) - 1 else sub_decls[i].get("W", words[i]))
                        for i in range(len(words))
                    )
            return {case: sanitize_adjectival_double_declension(val, n) for case, val in raw_multi.items()}

    # Already inflected tokens or non-nominative plural/case endings
    if n.lower().endswith(("ą", "ę", "ej", "ach", "ami", "om", "ego", "emu", "ych", "ich", "ymi", "imi", "ów", "ow")):
        return {"M": n, "D": n, "C": n, "B": n, "N": n, "Ms": n, "W": n}

    is_male = (g == "MALE" or "MĘSK" in g)
    is_female = (g == "FEMALE" or "KOBIETA" in g or "ŻEŃSK" in g or g == "FEMININE" or g == "DZIEWCZYNA" or g == "DZIEWCZYNKA")
    if not is_female and not is_male:
        if has_japanese_male_name_suffix(n) or is_official_or_court_consonant_name(n):
            is_male = True
        elif (n.lower() in INVARIABLE_JAPANESE_FEMALE_NAMES or n.lower() in FOREIGN_FEMALE_CONSONANT_NAMES or n.lower() in FEMALE_LEXICON_NAMES or is_inherently_female_name(n)):
            is_female = True

    # H3(A) Single-word female names (Operacja H3, Standard 9.10.1)
    if is_female and not is_polish_adjective(n) and n.lower() not in KNOWN_HEAD_NOUN_DECLENSIONS:
        if not n.endswith(("a", "A")):
            return {"M": n, "D": n, "C": n, "B": n, "N": n, "Ms": n, "W": n}

    # 0a. Adjectives / adjectival names and titles (e.g. Wielka, Wielki, Czarna, Czarny, Nieśmiertelny, Sobieski)
    if is_polish_adjective(n):
        return generate_polish_adjective_declension(n, gender=g if g != "UNKNOWN" else None, is_animate=True)

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
        # vs Polish agent nouns in -ca (władca, dowódca, obrońca, zabójca, zdrajca, łowca, stwórca):
        elif stem.endswith("c"):
            if stem.lower() in ("władc", "dowódc", "dowodc", "obrońc", "obronc", "zabójc", "zabojc", "zdrajc", "łowc", "lowc", "stwórc", "stworc", "twórc", "tworc", "znawc", "morderc", "wykonawc") or len(stem) > 4:
                return {
                    "M": n,
                    "D": stem + "y",
                    "C": stem + "y",
                    "B": stem + "ę",
                    "N": stem + "ą",
                    "Ms": stem + "y",
                    "W": stem + "o"
                }
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

    # 2a. Male foreign names ending in silent -e with apostrophe declension (e.g. White, Wayne, Blade, Locke, Moore)
    if not is_female and n.endswith("e") and len(n) >= 3 and n[-2].lower() in "bcdfghjklmnpqrstvwxz":
        if is_japanese_cv_mora_e_name(n) or n.lower() in JAPANESE_VOWEL_E_NAMES:
            return {"M": n, "D": n, "C": n, "B": n, "N": n, "Ms": n, "W": n}
        if n.lower() in ("pole", "morze", "słońce", "serce", "miejsce", "życie", "powietrze", "światło"):
            base = n[:-1]
            return {
                "M": n,
                "D": base + "a",
                "C": base + "u",
                "B": n,
                "N": base + "em",
                "Ms": base + "u",
                "W": n
            }
        stem = n
        last_c = n[-2].lower()
        if last_c == "t":
            ms_form = stem + "'cie"
        elif last_c == "d":
            ms_form = stem + "'dzie"
        else:
            ms_form = stem + "'u"
        return {
            "M": n,
            "D": stem + "'a",
            "C": stem + "'owi",
            "B": stem + "'a",
            "N": stem + "'em",
            "Ms": ms_form,
            "W": n
        }

    # 2b. Male names ending in consonant or diphthong -y (pronounced /j/, e.g. Ray, Roy, Gray)
    is_diphthong_y = (not is_female and n.endswith("y") and len(n) >= 2 and n[-2].lower() in "aeiou")
    if (n[-1].lower() not in "aeiouyąęó") or is_diphthong_y:
        if n.lower() in ("przestrzeń", "pieśń", "otchłań", "przystań", "baśń", "dłoń", "zieleń", "czerwień", "jesień"):
            base = n[:-1] + "ni"
            return {
                "M": n,
                "D": base,
                "C": base,
                "B": n,
                "N": base + "ą",
                "Ms": base,
                "W": base
            }
        if n.lower() == "promień":
            return {
                "M": n,
                "D": "Promienia",
                "C": "Promieniowi",
                "B": n,
                "N": "Promieniem",
                "Ms": "Promieniu",
                "W": "Promieniu"
            }
        stem = n
        if stem.endswith("ń"):
            stem = stem[:-1] + "ni"
        last_c = "j" if is_diphthong_y else n[-1].lower()
        last_2c = n[-2:].lower() if len(n) >= 2 else ""

        # Mobile 'e' in Polish names ending in -ek (Marek -> Mark-, Jacek -> Jack-, Tomek -> Tomk-, etc.)
        if len(n) >= 4 and last_2c == "ek" and n.lower() in ("marek", "jacek", "tomek", "janek", "franek", "bartek", "wojtek", "maciek", "leszek", "radek", "przemek", "władek", "staszek", "wiesiek"):
            stem = n[:-2] + "k"

        # Narzędnik po k, g: -iem (Gujukiem, Güyükiem, Olegiem, Magiem)
        n_case = stem + "iem" if last_c in ("k", "g") else stem + "em"

        # Miejscownik i Wołacz (Dystrybucja końcówki -u wg Task 3 / Zasada 15 AGENTS.md):
        # Dla odmiennych imion męskich zakończonych na głoski stwardniałe, afrykaty, tylnojęzykowe i miękkie
        # (tz, c, dz, cz, sz, rz, ż, sh, ch, k, g, j, y, l) generuj w Miejscowniku i Wołaczu wyłącznie końcówkę -u
        # (temat na -tz -> -tzu, -c -> -cu; eliminacja form na -tzie / -cie dla tych tematów).
        if last_2c in ("tz", "dz", "cz", "sz", "rz", "sh", "ch", "th") or last_c in ("c", "ż", "k", "g", "j", "l") or last_c == "y" or is_diphthong_y:
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

    # 2b. Adjectives / adjectival names and titles ending in -y / -i (e.g. Nieśmiertelny, Wielki, Sobieski, Czarny)
    if is_polish_adjective(n):
        return generate_polish_adjective_declension(n, gender=g if g != "UNKNOWN" else None, is_animate=True)

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
    # Binary alternative comma eradication: 'w kapciach, czy bez' -> 'w kapciach czy bez' (Filar XCI / Standard 9.4 2B.10 - ochrona wołacza W)
    (r"\b([A-Za-ząćęłńóśźż0-9\-]+),\s+czy\s+(bez|nie|tak)\b",
     lambda m: m.group(0) if (m.group(1)[0].isupper() and m.group(1).lower() not in ("tak", "nie", "bez", "to") and (not re.sub(r"\{[^}]*\}", "", m.string[:m.start(1)]).strip() or re.sub(r"\{[^}]*\}", "", m.string[:m.start(1)]).strip() in ("-", "–", "—", '"', "„", "...", "…") or re.search(r"(?:\\N|\\n|[.?!…])\s*[-–—]?\s*$", re.sub(r"\{[^}]*\}", "", m.string[:m.start(1)]).strip()))) else f"{m.group(1)} czy {m.group(2)}"),
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
    (r"(?<!\bbas\s)(?<!\bperkusja\s)(?<!\bi\s)\b[Ii]\s+gitara[!]+", lambda m: "Doskonale!" if m.group(0)[0].isupper() else "doskonale!"),
    (r"\b[Ss]tul\s+pysk\b", lambda m: "Zamilcz" if m.group(0)[0].isupper() else "zamilcz"),
    (r"\b[Zz]mywajmy\s+się\s+stąd\b", lambda m: "Uciekajmy stąd" if m.group(0)[0].isupper() else "uciekajmy stąd"),
    (r"\b[Zz]mywamy\s+się\s+stąd\b", lambda m: "Uciekamy stąd" if m.group(0)[0].isupper() else "uciekamy stąd"),
    (r"\b[Zz]mywaj\s+się\s+stąd\b", lambda m: "Uciekaj stąd" if m.group(0)[0].isupper() else "uciekaj stąd"),
    (r"\b[Kk]łamstwo\s+jak\s+byk\b", lambda m: "Bezczelne kłamstwo" if m.group(0)[0].isupper() else "bezczelne kłamstwo"),
    (r"\b[Pp]rzejmuję\s+stery\b", lambda m: "Teraz ja mówię" if m.group(0)[0].isupper() else "teraz ja mówię"),
    (r"\b[Dd]la\s+zabicia\s+czasu\b", lambda m: "Dla rozrywki" if m.group(0)[0].isupper() else "dla rozrywki"),
    (r"\b[Ww]ylec(?:ieć|iał|iała|ieli)\s+ze\s+szkoły\b", "zostać wydalonym ze szkoły"),
    # Closed invariant PWN preposition-pronoun phonetic forms and idioms (0.00 PLN)
    (r"\b([Dd]la)\s+mię\b", lambda m: "Dla mnie" if m.group(1)[0].isupper() else "dla mnie"),
    (r"\b([Oo]de)\s+mie\b", lambda m: "Ode mnie" if m.group(1)[0].isupper() else "ode mnie"),
    (r"\b([Oo]d)\s+mnie\b", lambda m: "Ode mnie" if m.group(1)[0].isupper() else "ode mnie"),
    (r"\b([Zz])\s+mną\b", lambda m: "Ze mną" if m.group(1)[0].isupper() else "ze mną"),
    (r"\b([Pp]rzed)\s+mną\b", lambda m: "Przede mną" if m.group(1)[0].isupper() else "przede mną"),
    (r"\b([Ww])\s+każdym\s+bądź\s+razie\b", lambda m: "W każdym razie" if m.group(1)[0].isupper() else "w każdym razie"),
    (r"\b([Bb])ez\s+jaj[!]+", lambda m: "To jakieś kpiny!" if m.group(1)[0].isupper() else "to jakieś kpiny!"),
    (r"\b([Gg])uzik\s+mnie\s+to\s+obchodzi\b", lambda m: "Nic mnie to nie obchodzi" if m.group(1)[0].isupper() else "nic mnie to nie obchodzi"),
    (r"\b([Pp])omiędzy\s+tobą\s+i\s+mną\b", lambda m: "Między nami" if m.group(1)[0].isupper() else "między nami"),
    (r"\b([Pp])omiędzy\s+nami\b", lambda m: "Między nami" if m.group(1)[0].isupper() else "między nami"),
    (r"\b([Ww])\s+mrugnięciu\s+oka\b", lambda m: "W mgnieniu oka" if m.group(1)[0].isupper() else "w mgnieniu oka"),
]


def replace_with_case_preservation(pattern: str, replacement: str, text: str) -> str:
    """Replaces matches of pattern with replacement, preserving initial capitalization of matched token."""
    def _sub_cb(m):
        orig = m.group(0)
        if orig and orig[0].isupper():
            return replacement[0].upper() + replacement[1:]
        return replacement.lower()
    return re.sub(pattern, _sub_cb, text, flags=re.IGNORECASE)


VERB_PAT_MIEĆ = r"nie\s+(?:mam|masz|ma|mamy|macie|mają|miał(?:em|am|eś|aś|a|o)?|miel(?:i|iśmy|iście)|miały(?:śmy|ście)?|będ(?:ę|ziesz|zie|ziemy|ziecie|ą)\s+(?:mieć|miał(?:a)?))"
VERB_PAT_WIDZIEĆ = r"nie\s+(?:widz(?:ę|isz|i|imy|icie|ą)|widział(?:em|am|eś|aś|a|o)?|widziel(?:i|iśmy|iście)|widziały(?:śmy|ście)?|będ(?:ę|ziesz|zie|ziemy|ziecie|ą)\s+(?:widzieć|widział(?:a)?))"
VERB_PAT_CZUĆ = r"nie\s+(?:czuj(?:ę|esz|e|emy|ecie|ą)|czuł(?:em|am|eś|aś|a|o)?|czul(?:i|iśmy|iście)|czuły(?:śmy|ście)?|będ(?:ę|ziesz|zie|ziemy|ziecie|ą)\s+(?:czuć|czuł(?:a)?))"
VERB_PAT_ZNAĆ = r"nie\s+(?:zna(?:m|sz|my|cie|ją)?|znał(?:em|am|eś|aś|a|o)?|znal(?:i|iśmy|iście)|znały(?:śmy|ście)?|będ(?:ę|ziesz|zie|ziemy|ziecie|ą)\s+(?:znać|znał(?:a)?))"
VERB_PAT_PAMIĘTAĆ = r"nie\s+(?:pamięta(?:m|sz|my|cie|ją)?|pamiętał(?:em|am|eś|aś|a|o)?|pamiętal(?:i|iśmy|iście)|pamiętały(?:śmy|ście)?|będ(?:ę|ziesz|zie|ziemy|ziecie|ą)\s+(?:pamiętać|pamiętał(?:a)?))"
VERB_PAT_SŁYSZEĆ = r"nie\s+(?:słysz(?:ę|ysz|y|ymy|ycie|ą)|słyszał(?:em|am|eś|aś|a|o)?|słyszel(?:i|iśmy|iście)|słyszały(?:śmy|ście)?|będ(?:ę|ziesz|zie|ziemy|ziecie|ą)\s+(?:słyszeć|słyszał(?:a)?))"
VERB_PAT_SPRAWIAĆ = r"nie\s+(?:sprawia(?:m|sz|my|cie|ją)?|sprawiał(?:em|am|eś|aś|a|o)?|sprawi(?:ł|ła|ło|li|ły|ć)?)"

TRANSITIVE_NEGATION_BASE_COLLOCATIONS = [
    # (verb_pattern, direct_object_pattern, genitive_replacement)
    # mieć + B. -> D.
    (VERB_PAT_MIEĆ, r"czas", "czasu"),
    (VERB_PAT_MIEĆ, r"wybór", "wyboru"),
    (VERB_PAT_MIEĆ, r"ochotę", "ochoty"),
    (VERB_PAT_MIEĆ, r"nadzieję", "nadziei"),
    (VERB_PAT_MIEĆ, r"siłę", "siły"),
    (VERB_PAT_MIEĆ, r"pojęcie", "pojęcia"),
    (VERB_PAT_MIEĆ, r"powód", "powodu"),
    (VERB_PAT_MIEĆ, r"problem", "problemu"),
    (VERB_PAT_MIEĆ, r"wątpliwość", "wątpliwości"),
    # znać + B. -> D.
    (VERB_PAT_ZNAĆ, r"tę\s+prawdę", "tej prawdy"),
    (VERB_PAT_ZNAĆ, r"odpowiedź", "odpowiedzi"),
    (VERB_PAT_ZNAĆ, r"litość", "litości"),
    (VERB_PAT_ZNAĆ, r"granice", "granic"),
    # widzieć + B. -> D.
    (VERB_PAT_WIDZIEĆ, r"żaden\s+sens", "żadnego sensu"),
    (VERB_PAT_WIDZIEĆ, r"inny\s+sposób", "innego sposobu"),
    (VERB_PAT_WIDZIEĆ, r"sens", "sensu"),
    (VERB_PAT_WIDZIEĆ, r"przeszkody", "przeszkód"),
    (VERB_PAT_WIDZIEĆ, r"powód", "powodu"),
    (VERB_PAT_WIDZIEĆ, r"problem", "problemu"),
    # czuć + B. -> D.
    (VERB_PAT_CZUĆ, r"strach", "strachu"),
    (VERB_PAT_CZUĆ, r"ból", "bólu"),
    (VERB_PAT_CZUĆ, r"litość", "litości"),
    # pamiętać + B. -> D.
    (VERB_PAT_PAMIĘTAĆ, r"ten\s+dzień", "tego dnia"),
    (VERB_PAT_PAMIĘTAĆ, r"tę\s+chwilę", "tej chwili"),
    # słyszeć + B. -> D.
    (VERB_PAT_SŁYSZEĆ, r"żaden\s+głos", "żadnego głosu"),
    (VERB_PAT_SŁYSZEĆ, r"głos", "głosu"),
    # sprawiać + B. -> D.
    (VERB_PAT_SPRAWIAĆ, r"problem", "problemu"),
    (VERB_PAT_SPRAWIAĆ, r"ból", "bólu"),
]

# Safe conversational adverbs/particles (<= 2 words, strictly no commas)
NEGATION_ADVERBIAL_SPAN = r"(?:\s+(?:już|teraz|wcale|ani\s+trochę|tutaj|tu|tam|wciąż|nadal|przecież|nawet|zresztą|zbytnio|w\s+tym|chyba|naprawdę))?"

TRANSITIVE_NEGATION_REPLACEMENTS = [
    (r"\bnie\s+mam\s+czas\b", "nie mam czasu"),
    (r"\bnie\s+mam\s+wybór\b", "nie mam wyboru"),
    (r"\bnie\s+mam\s+ochotę\b", "nie mam ochoty"),
    (r"\bnie\s+mam\s+nadzieję\b", "nie mam nadziei"),
    (r"\bnie\s+mam\s+siłę\b", "nie mam siły"),
    (r"\bnie\s+znam\s+tę\s+prawdę\b", "nie znam tej prawdy"),
    (r"\bnie\s+znam\s+odpowiedź\b", "nie znam odpowiedzi"),
    (r"\bnie\s+zna\s+litość\b", "nie zna litości"),
    (r"\bnie\s+zna\s+granice\b", "nie zna granic"),
    (r"\bnie\s+widzę\s+żaden\s+sens\b", "nie widzę żadnego sensu"),
    (r"\bnie\s+widzę\s+inny\s+sposób\b", "nie widzę innego sposobu"),
    (r"\bnie\s+widzi\s+przeszkody\b", "nie widzi przeszkód"),
    (r"\bnie\s+pamiętam\s+ten\s+dzień\b", "nie pamiętam tego dnia"),
    (r"\bnie\s+czuję\s+strach\b", "nie czuję strachu"),
]


def sanitize_genitive_of_negation(text: str) -> str:
    """
    Enforces Genitive of Negation on closed high-certainty transitive verb collocations
    including optional conversational adverbial/particle insertions (<= 2 words, no commas) (Filar CLXXXVIII / 0.00 PLN).
    Preserves case capitalization.
    """
    if not text:
        return ""
    res = text
    for verb_pat, obj_pat, gen_target in TRANSITIVE_NEGATION_BASE_COLLOCATIONS:
        pat = rf"\b({verb_pat})({NEGATION_ADVERBIAL_SPAN})\s+({obj_pat})\b"
        def _sub_neg(m, tgt=gen_target):
            v_matched = m.group(1)
            adv_matched = m.group(2) or ""
            obj_matched = m.group(3)
            repl_tgt = tgt[0].upper() + tgt[1:] if obj_matched[0].isupper() else tgt
            return f"{v_matched}{adv_matched} {repl_tgt}"
        res = re.sub(pat, _sub_neg, res, flags=re.IGNORECASE)
    return res


CANON_OBLIQUE_CORRECTIONS = [
    # Narzędnik po z/ze/przed/nad/pod/za/między
    (r"\b([Zz]e?|[Pp]rzed|[Nn]ad|[Pp]od|[Zz]a|[Mm]iędzy)\s+(?:Król|Królem)\s+Demonów\b", r"\1 Królem Demonów"),
    (r"\b([Zz]e?|[Pp]rzed|[Nn]ad|[Pp]od|[Zz]a|[Mm]iędzy)\s+(?:Czarny\s+Rycerz|Czarnym\s+Rycerz|Czarny\s+Rycerzem)\b", r"\1 Czarnym Rycerzem"),

    # Dopełniacz po u/do/od/dla/bez/zza
    (r"\b([Dd]la|[Uu]|[Oo]d|[Dd]o|[Bb]ez|[Zz]za)\s+(?:Król|Króla)\s+Demonów\b", r"\1 Króla Demonów"),
    (r"\b([Dd]la|[Uu]|[Oo]d|[Dd]o|[Bb]ez|[Zz]za)\s+(?:Czarny\s+Rycerz|Czarnego\s+Rycerz|Czarny\s+Rycerza)\b", r"\1 Czarnego Rycerza"),

    # Celownik po przeciwko/ku/dzięki
    (r"\b([Pp]rzeciwko|[Kk]u|[Dd]zięki)\s+(?:Król|Królowi)\s+Demonów\b", r"\1 Królowi Demonów"),
    (r"\b([Pp]rzeciwko|[Kk]u|[Dd]zięki)\s+(?:Czarny\s+Rycerz|Czarnemu\s+Rycerz|Czarny\s+Rycerzowi)\b", r"\1 Czarnemu Rycerzowi"),

    # Biernik po przez
    (r"\b([Pp]rzez)\s+(?:Król|Króla)\s+Demonów\b", r"\1 Króla Demonów"),
    (r"\b([Pp]rzez)\s+(?:Czarny\s+Rycerz|Czarnego\s+Rycerz|Czarny\s+Rycerza)\b", r"\1 Czarnego Rycerza"),

    # Miejscownik po o/przy
    (r"\b([Oo]|[Pp]rzy)\s+(?:Król|Królu)\s+Demonów\b", r"\1 Królu Demonów"),
    (r"\b([Oo]|[Pp]rzy)\s+(?:Czarny\s+Rycerz|Czarnym\s+Rycerz|Czarny\s+Rycerzu)\b", r"\1 Czarnym Rycerzu"),
]

_DYNAMIC_CANON_OBLIQUE_CORRECTIONS: Optional[List[Tuple[str, str]]] = None
_DYNAMIC_CANON_ANTI_CALQUES: Optional[List[Tuple[str, str]]] = None


def _get_dynamic_canon_compound_oblique_corrections() -> List[Tuple[str, str]]:
    global _DYNAMIC_CANON_OBLIQUE_CORRECTIONS
    if _DYNAMIC_CANON_OBLIQUE_CORRECTIONS is not None:
        return _DYNAMIC_CANON_OBLIQUE_CORRECTIONS
    corrections: List[Tuple[str, str]] = []
    try:
        candidate_terms = []
        from manga_canon import manga_canon_registry
        if manga_canon_registry and hasattr(manga_canon_registry, "canon_db"):
            for entry in manga_canon_registry.canon_db.values():
                glossary = entry.get("glossary", {})
                for k, v in glossary.items():
                    if isinstance(v, str) and " " in v:
                        tokens = v.split()
                        if len(tokens) == 2 and tokens[0][0].isupper() and tokens[1][0].isupper():
                            candidate_terms.append(v)
        bible_dir = Path(__file__).parent / "series_memory"
        if bible_dir.exists():
            for bible_file in bible_dir.glob("*_bible.json"):
                try:
                    with open(bible_file, "r", encoding="utf-8") as bf:
                        bdata = json.load(bf)
                        for k, v in bdata.get("glossary", {}).items():
                            if isinstance(v, str) and " " in v:
                                tokens = v.split()
                                if len(tokens) == 2 and tokens[0][0].isupper() and tokens[1][0].isupper():
                                    candidate_terms.append(v)
                except Exception:
                    logger.warning("Ekstrakcja dwutokenowych nazw własnych zakończona wyjątkiem", exc_info=True)

        seen = set()
        for v in candidate_terms:
            if v in seen:
                continue
            seen.add(v)
            tokens = v.split()
            gen = "FEMALE" if (tokens[0].endswith("a") and tokens[1].endswith("a")) else "MALE"
            d = generate_polish_name_declension(v, gen)
            if d and "M" in d and "D" in d and "N" in d and "C" in d and "B" in d and "Ms" in d:
                m, d_c, c_c, b_c, n_c, ms_c = d["M"], d["D"], d["C"], d["B"], d["N"], d["Ms"]
                d0 = generate_polish_name_declension(tokens[0], gen)
                d1 = generate_polish_name_declension(tokens[1], gen)
                t0_m, t1_m = tokens[0], tokens[1]
                t0_n = d0["N"] if d0 and "N" in d0 else t0_m
                t1_n = d1["N"] if d1 and "N" in d1 else t1_m
                t0_d = d0["D"] if d0 and "D" in d0 else t0_m
                t1_d = d1["D"] if d1 and "D" in d1 else t1_m
                t0_c = d0["C"] if d0 and "C" in d0 else t0_m
                t1_c = d1["C"] if d1 and "C" in d1 else t1_m
                t0_b = d0["B"] if d0 and "B" in d0 else t0_m
                t1_b = d1["B"] if d1 and "B" in d1 else t1_m
                t0_ms = d0["Ms"] if d0 and "Ms" in d0 else t0_m
                t1_ms = d1["Ms"] if d1 and "Ms" in d1 else t1_m

                # Narzędnik po z/ze/przed/nad/pod/za/między
                pat_n = rf"\b([Zz]e?|[Pp]rzed|[Nn]ad|[Pp]od|[Zz]a|[Mm]iędzy)\s+(?:{m}|{t0_n}\s+{t1_m}|{t0_m}\s+{t1_n})\b"
                corrections.append((pat_n, rf"\1 {n_c}"))
                # Dopełniacz po u/do/od/dla/bez/zza
                pat_d = rf"\b([Dd]la|[Uu]|[Oo]d|[Dd]o|[Bb]ez|[Zz]za)\s+(?:{m}|{t0_d}\s+{t1_m}|{t0_m}\s+{t1_d})\b"
                corrections.append((pat_d, rf"\1 {d_c}"))
                # Celownik po przeciwko/ku/dzięki
                pat_c = rf"\b([Pp]rzeciwko|[Kk]u|[Dd]zięki)\s+(?:{m}|{t0_c}\s+{t1_m}|{t0_m}\s+{t1_c})\b"
                corrections.append((pat_c, rf"\1 {c_c}"))
                # Biernik po przez
                pat_b = rf"\b([Pp]rzez)\s+(?:{m}|{t0_b}\s+{t1_m}|{t0_m}\s+{t1_b})\b"
                corrections.append((pat_b, rf"\1 {b_c}"))
                # Miejscownik po o/przy
                pat_ms = rf"\b([Oo]|[Pp]rzy)\s+(?:{m}|{t0_ms}\s+{t1_m}|{t0_m}\s+{t1_ms})\b"
                corrections.append((pat_ms, rf"\1 {ms_c}"))
    except Exception:
        logger.warning("Generowanie dynamicznych korekt przypadków zależnych zakończone wyjątkiem", exc_info=True)
    _DYNAMIC_CANON_OBLIQUE_CORRECTIONS = corrections
    return _DYNAMIC_CANON_OBLIQUE_CORRECTIONS


def _get_dynamic_manga_canon_anti_calque_patterns() -> List[Tuple[str, str]]:
    global _DYNAMIC_CANON_ANTI_CALQUES
    if _DYNAMIC_CANON_ANTI_CALQUES is not None:
        return _DYNAMIC_CANON_ANTI_CALQUES
    patterns: List[Tuple[str, str]] = []
    try:
        from manga_canon import manga_canon_registry
        if manga_canon_registry and hasattr(manga_canon_registry, "canon_db"):
            for entry in manga_canon_registry.canon_db.values():
                glossary = entry.get("glossary", {})
                for en_k, pl_v in glossary.items():
                    if isinstance(pl_v, str) and " " in pl_v:
                        tokens = pl_v.split()
                        if len(tokens) == 2 and tokens[0][0].isupper() and tokens[1][0].isupper() and tokens[0].endswith("a") and tokens[1].endswith("a"):
                            t1, t2 = tokens[0], tokens[1]
                            d1 = generate_polish_name_declension(t1, "FEMALE")
                            d2 = generate_polish_name_declension(t2, "FEMALE")
                            if d1 and d2 and "D" in d2:
                                case_pairs = [
                                    (d1.get("M", t1), d2.get("D", t2), d1.get("M", t1), d2.get("M", t2)),
                                    (d1.get("D", t1), d2.get("D", t2), d1.get("D", t1), d2.get("D", t2)),
                                    (d1.get("C", t1), d2.get("D", t2), d1.get("C", t1), d2.get("C", t2)),
                                    (d1.get("B", t1), d2.get("D", t2), d1.get("B", t1), d2.get("B", t2)),
                                    (d1.get("N", t1), d2.get("D", t2), d1.get("N", t1), d2.get("N", t2)),
                                    (d1.get("Ms", t1), d2.get("D", t2), d1.get("Ms", t1), d2.get("Ms", t2)),
                                ]
                                for c1, c2_gen, out1, out2 in case_pairs:
                                    pat = rf"(^|[^\w]|\\[Nnh]){re.escape(c1)}\s+od\s+{re.escape(c2_gen)}\b"
                                    repl = rf"\g<1>{out1} {out2}"
                                    patterns.append((re.compile(pat), repl))
                                    if c2_gen.endswith("y") or c2_gen.endswith("i"):
                                        alt_c2 = c2_gen[:-1] + "ą"
                                        pat_alt = rf"(^|[^\w]|\\[Nnh]){re.escape(c1)}\s+od\s+{re.escape(alt_c2)}\b"
                                        patterns.append((re.compile(pat_alt), repl))
    except Exception:
        logger.warning("Generowanie dynamicznych wzorców antykalkowych zakończone wyjątkiem", exc_info=True)
    _DYNAMIC_CANON_ANTI_CALQUES = patterns
    return _DYNAMIC_CANON_ANTI_CALQUES


def sanitize_canon_compound_oblique_cases(text: str, series_bible: Optional[Any] = None) -> str:
    """
    Corrects frozen nominative compound canon syntagmas governed by prepositions (Filar CLXXXVIII / 0.00 PLN).
    'dla Wielki Chan' -> 'dla Wielkiego Chana', 'z Czarny Rycerz' -> 'z Czarnym Rycerzem'.
    """
    if not text:
        return ""
    res = text
    for pat, repl in CANON_OBLIQUE_CORRECTIONS:
        res = re.sub(pat, repl, res)
    for pat, repl in _get_dynamic_canon_compound_oblique_corrections():
        res = re.sub(pat, repl, res)
    return res


def sanitize_lexical_text(text: str) -> str:
    """Sanitizes text against known LLM/OCR typos and deformed Polish words (Filar CLXIV/CLXX)."""
    if not text:
        return ""
    res = text
    for pat, repl in TYPO_NORMALIZATIONS:
        res = re.sub(pat, repl, res)
    if "od" in res.lower():
        for pat, repl in _get_dynamic_manga_canon_anti_calque_patterns():
            if hasattr(pat, "sub"):
                res = pat.sub(repl, res)
            else:
                res = re.sub(pat, repl, res)

    # Subject nominative title repair: 'pan Eftala zniszczył' -> 'pan Eftal zniszczył', 'Mistrz Tondena minoru nie zdążył' -> 'Mistrz Tonden Minoru nie zdążył'
    TITLES_SUBJECT_PAT = r"[Pp]an|[Pp]ani|[Mm]istrz|[Pp]rofesor|[Dd]oktor|[Pp]isarz|[Rr]eżyser|[Rr]edaktor|[Aa]utor|[Mm]angaka|[Ss]ensei"
    CANONICAL_A_NAMES = {
        "akira", "shira", "soma", "gaara", "ashitaka", "kiba", "kenta",
        "ryoma", "hanza", "koba", "soya", "toma", "genga", "teshima",
        "yamada", "maeda", "takeda", "matsuda", "kuroda", "sanada",
        "shimada", "okada", "ishida", "kawada", "ueda", "baba", "honda", "oda", "aida"
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
        if full_surname in CANONICAL_A_NAMES or full_surname.endswith(("da", "ta", "ka", "ma", "ba")):
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
        if full_name in CANONICAL_A_NAMES or full_name.endswith(("da", "ta", "ka", "ma", "ba")):
            return m.group(0)
        return f"{prefix}{title}{sep1}{name_stem}{sep2}{verb}"

    res = re.sub(
        rf"(^|[^\w]|\\[Nnh])({TITLES_SUBJECT_PAT})(\s+|\\[Nnh]+)([A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]*[bcdfghjklmnprstvwxz])a(\s+|\\[Nnh]+)((?:nie\s+)?[a-ząćęłńóśźż]+(?:ł|łby|ła|ło|li|ły))\b",
        _fix_nominative_title_subject,
        res
    )
    res = sanitize_pronominal_somatic_possession(res)
    res = sanitize_deictic_motion_vector(res)
    res = sanitize_sensory_pleonasm(res)
    res = sanitize_closed_idioms_and_prepositions(res)
    return res


def sanitize_pronominal_somatic_possession(text: str) -> str:
    """
    Eliminates English possessive pronoun calques before body parts,
    personal belongings, and close relatives (Filar CLXXVII / Pronominal Decoupling).
    Deterministic offline 0.00 PLN enforcement.
    """
    if not text:
        return ""
    res = text

    # Prepositional somatic phrases: w moim sercu -> w sercu, w mojej głowie -> w głowie
    SOMATIC_PREPOSITIONS = [
        (r"\b([Ww])\s+(?:moim|twoim|swoim|jego|jej|naszym|waszym)\s+sercu\b", r"\1 sercu"),
        (r"\b([Ww])\s+(?:mojej|twojej|swojej|jego|jej|naszej|waszej)\s+głowie\b", r"\1 głowie"),
        (r"\b([Ww])\s+(?:moich|twoich|swoich|jego|jej|naszych|waszych)\s+myślach\b", r"\1 myślach"),
        (r"\b([Ww])\s+(?:moich|twoich|swoich|jego|jej|naszych|waszych)\s+oczach\b", r"\1 oczach"),
        (r"\b([Ww])\s+(?:moich|twoich|swoich|jego|jej|naszych|waszych)\s+żyłach\b", r"\1 żyłach"),
        (r"\b([Ww])\s+(?:moich|twoich|swoich|jego|jej|naszych|waszych)\s+ramionach\b", r"\1 ramionach"),
        (r"\b([Nn]a)\s+(?:moich|twoich|swoich|jego|jej|naszych|waszych)\s+plecach\b", r"\1 plecach"),
        (r"\b([Nn]a)\s+(?:moich|twoich|swoich|jego|jej|naszych|waszych)\s+ramionach\b", r"\1 ramionach"),
        (r"\b([Zz])\s+(?:moich|twoich|swoich|jego|jej|naszych|waszych)\s+ust\b", r"\1 ust"),
    ]
    for pat, repl in SOMATIC_PREPOSITIONS:
        res = re.sub(pat, repl, res)

    # Imperatives and somatic verbs:
    VERBAL_SOMATIC = [
        (r"\b(zamknij|zamknijcie|otwórz|otwórzcie|przymknij|przymknijcie)\s+(?:twoje|swoje|twoich|swoich)\s+(oczy)\b", r"\1 \2"),
        (r"\b(podnieś|podnieście|wznieś|wznieście|załóż|załóżcie|rozłóż|rozłóżcie|opuść|opuśćcie|umyj|umyjcie)\s+(?:twoje|swoje|twoich|swoich)\s+(ręce|dłonie|ramiona)\b", r"\1 \2"),
        (r"\b(zdejmij|zdejmijcie|włóż|włóżcie|załóż|załóżcie|ubierz|ubierzcie)\s+(?:twoje|swoje|twój|twą|twoją)\s+(buty|kurtkę|płaszcz|ubranie|czapkę)\b", r"\1 \2"),
    ]
    for pat, repl in VERBAL_SOMATIC:
        res = re.sub(pat, repl, res, flags=re.IGNORECASE)

    # Life saving: uratowałeś moje życie -> ocaliłeś mi życie / uratowałeś mi życie
    res = re.sub(r"\b(uratował|uratowała|uratowałeś|uratowałaś|ocalił|ocaliła|ocaliłeś|ocaliłaś|ratując|ocalając)\s+moje\s+życie\b", r"\1 mi życie", res, flags=re.IGNORECASE)
    res = re.sub(r"\b(uratował|uratowała|uratowałeś|uratowałaś|ocalił|ocaliła|ocaliłeś|ocaliłaś)\s+twoje\s+życie\b", r"\1 ci życie", res, flags=re.IGNORECASE)

    # Relational possession (family):
    RELATIONAL_PATTERNS = [
        (r"\b([Zz]|ze|dla|do|u|od)\s+moją\s+(matką|siostrą|córką|babcią)\b", r"\1 \2"),
        (r"\b([Zz]|ze|dla|do|u|od)\s+moim\s+(ojcem|bratem|synem|dziadkiem)\b", r"\1 \2"),
        (r"\b([Zz]|ze|dla|do|u|od)\s+moimi\s+(rodzicami|braćmi|siostrami)\b", r"\1 \2"),
        (r"\b([Zz]|ze|dla|do|u|od)\s+twoją\s+(matką|siostrą|córką|babcią)\b", r"\1 \2"),
        (r"\b([Zz]|ze|dla|do|u|od)\s+twoim\s+(ojcem|bratem|synem|dziadkiem)\b", r"\1 \2"),
        (r"\b([Zz]|ze|dla|do|u|od)\s+twoimi\s+(rodzicami|braćmi|siostrami)\b", r"\1 \2"),
    ]
    for pat, repl in RELATIONAL_PATTERNS:
        res = re.sub(r"(?<!a nie\s)(?<!niż\s)(?<!zamiast\s)" + pat, repl, res, flags=re.IGNORECASE)

    # Causal calque: z mojego powodu -> przeze mnie, z twojego powodu -> przez ciebie
    res = re.sub(
        r"\b([Zz])\s+mojego\s+powodu\b",
        lambda m: "Przeze mnie" if m.group(1) == "Z" else "przeze mnie",
        res
    )
    res = re.sub(
        r"\b([Zz])\s+twojego\s+powodu\b",
        lambda m: "Przez ciebie" if m.group(1) == "Z" else "przez ciebie",
        res
    )

    return res


def naturalize_adjacency_rejoinder(prior_q: str, resp: str) -> str:
    """
    Eliminates stiff 'Yes, I did' / 'No, I didn't' calques in adjacent conversational pairs (Filar CLXXIX).
    Transforms 'Tak, poszedłem' -> 'Poszedłem', 'Nie, nie widziałem' -> 'Nie widziałem'.
    """
    if not resp:
        return ""
    if not prior_q or not prior_q.strip().endswith("?"):
        return resp

    res = resp.strip()

    m_aff = re.match(r"^Tak,\s+([a-ząćęłńóśźż]+(?:łem|łam|liśmy|łyśmy|em|am|eś|aś|liście|łyście|ł|ła|ło|li|ły|bym|byś|by|byśmy|byście|ę|emy|imy|ymy))\b", res, re.IGNORECASE)
    if m_aff:
        verb = m_aff.group(1)
        rest = res[m_aff.end():]
        return f"{verb.capitalize()}{rest}"

    m_neg = re.match(r"^Nie,\s+nie\s+([a-ząćęłńóśźż]+)\b", res, re.IGNORECASE)
    if m_neg:
        verb = m_neg.group(1)
        rest = res[m_neg.end():]
        return f"Nie {verb}{rest}"

    return res


def sanitize_deictic_motion_vector(text: str) -> str:
    """
    Sanitizes false spatial deixis motion verbs (Filar CLXXX / Cinematic Deixis).
    Eliminates English/Japanese motion mismatch:
    'Już przychodzę!' -> 'Już idę!'
    'Oto przychodzę!' / 'Oto nadchodzę!' -> 'Już idę!' / 'Zaraz będę!'
    """
    if not text:
        return ""
    res = text
    DEICTIC_REPLACEMENTS = [
        (r"\bJuż\s+przychodzę\b", "Już idę"),
        (r"\bjuż\s+przychodzę\b", "już idę"),
        (r"\bZaraz\s+przychodzę\b", "Zaraz będę"),
        (r"\bzaraz\s+przychodzę\b", "zaraz będę"),
        (r"\bOto\s+przychodzę\b", "Już idę"),
        (r"\boto\s+przychodzę\b", "już idę"),
        (r"\bOto\s+nadchodzę\b", "Już idę"),
        (r"\boto\s+nadchodzę\b", "już idę"),
        (r"\bZaraz\s+tam\s+przyjdę\b", "Zaraz tam pójdę"),
        (r"\bzaraz\s+tam\s+przyjdę\b", "zaraz tam pójdę"),
    ]
    for pat, repl in DEICTIC_REPLACEMENTS:
        res = re.sub(pat, repl, res)
    return res


def sanitize_sensory_pleonasm(text: str) -> str:
    """
    Eliminates visual-auditory pleonasms and sensory tautologies (Filar CLXXXI).
    'pada deszcz na zewnątrz' -> 'pada deszcz' / 'na zewnątrz leje'
    'spada w dół' -> 'spada'
    'cofa się w tył' -> 'cofa się'
    'wspina się do góry' -> 'wspina się'
    'patrzeć moimi własnymi oczami' -> 'patrzeć na własne oczy'
    """
    if not text:
        return ""
    res = text
    PLEONASMS = [
        (r"\b(pada|padał|padający|leje|lał)\s+deszcz\s+na\s+zewnątrz\b", r"\1 deszcz"),
        (r"\bna\s+zewnątrz\s+pada\s+deszcz\b", "na zewnątrz leje"),
        (r"\b(spadać|spada|spadają|spadł|spadła|spadło|spadli|spadły|spadłem|spadłam|spadłeś|spadłaś)\s+w\s+dół\b", r"\1"),
        (r"\b(cofać|cofa|cofają|cofnął|cofnęła|cofnęło|cofnęli|cofnęły|cofam|cofasz|cofamy|cofacie)\s+się\s+w\s+tył\b", r"\1 się"),
        (r"\b(wspinać|wspina|wspinają|wspiął|wspięła|wspięło|wspinam|wspinasz|wspinamy)\s+się\s+do\s+góry\b", r"\1 się"),
        (r"\b(patrzeć|widzieć|zobaczyć)\s+(?:na\s+to\s+)?moimi\s+(?:własnymi\s+)?oczami\b", r"\1 na własne oczy"),
        (r"\b(widziałem|widziałam|widzieliśmy|widziałyśmy)\s+to\s+moimi\s+(?:własnymi\s+)?oczami\b", r"\1 to na własne oczy"),
    ]
    for pat, repl in PLEONASMS:
        res = re.sub(pat, repl, res, flags=re.IGNORECASE)
    return res


def sanitize_toponymic_pleonasms_and_stuttering(text: str) -> str:
    """
    Sanitizes toponymic, administrative, geographical, and chronicle pleonasms
    and identical token stuttering without destroying legitimate stylistic punctuation.
    (Filar CLXXXIV / 0.00 PLN)
    """
    if not text:
        return ""
    res = text

    # 1. Identical capitalized word stuttering without punctuation (e.g. 'Prowincja Prowincja' -> 'Prowincja')
    # Requires identical capitalized tokens of length >= 3 separated by whitespace or \N
    res = re.sub(
        r"\b([A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]{2,})(?:\s+|\\[Nnh]+)\1\b",
        r"\1",
        res
    )

    # 2. Repeated or multiple inflected/base category descriptors preceding a proper name
    # Accounts for Polish consonant alternations (k:c, k:cz, g:dz, r:rz, etc.):
    # - 'z prowincji Prowincja Prowincja Shimotsuke' -> 'z prowincji Shimotsuke'
    # - 'z prowincji Prowincja Shimotsuke' -> 'z prowincji Shimotsuke'
    # - 'w kronice Kronika Taiheiki' -> 'w kronice Taiheiki'
    # - 'na górze Góra Hiei' -> 'na górze Hiei'
    # - 'w rzece Rzeka Kamogawa' -> 'w rzece Kamogawa'
    # - 'w mieście Miasto Kioto' -> 'w mieście Kioto'
    # - 'w prefekturze Prefektura Nagano' -> 'w prefekturze Nagano'
    CATEGORY_STEM_GROUPS = [
        r"prowincj",
        r"prefektur",
        r"gór|górz",
        r"rzek|rzec",
        r"jezior",
        r"morz",
        r"dolin",
        r"wysp",
        r"zatok|zatoc",
        r"przełęcz",
        r"zamk|zame",
        r"twierdz",
        r"świątyn",
        r"chram",
        r"bram",
        r"miast|mieśc",
        r"dystrykt|dystrykc",
        r"ziem",
        r"księstw",
        r"królestw",
        r"cesarstw",
        r"państw",
        r"kraj",
        r"kronik|kronic",
        r"księg|księdz",
        r"traktat|traktac",
    ]

    for grp in CATEGORY_STEM_GROUPS:
        pat = re.compile(
            rf"\b([A-ZĄĆĘŁŃÓŚŹŻa-ząćęłńóśźż]*(?:{grp})[a-ząćęłńóśźż]*)"
            rf"(?:(?:\s+|\\[Nnh]+)+[A-ZĄĆĘŁŃÓŚŹŻa-ząćęłńóśźż]*(?:{grp})[a-ząćęłńóśźż]*)+"
            rf"((?:\s+|\\[Nnh]+)+[A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]+)\b",
            re.IGNORECASE
        )
        res = pat.sub(r"\1\2", res)

    return res


_BASE_KNOWN_FANTASY_TOPONYMS: Set[str] = {
    "samarkand", "karakorum", "bukhara", "nishapur", "baghdad", "tabriz", "herat",
    "kyoto", "yamato", "owari", "mikawa", "echigo", "kai",
    "otaru", "sapporo", "asahikawa", "abashiri", "karafuto", "nemuro", "yubari",
    "paryż", "tokio", "londyn", "warszawa", "rzym", "berlin"
}


def _load_dynamic_fantasy_toponyms() -> Set[str]:
    toponyms = set(_BASE_KNOWN_FANTASY_TOPONYMS)
    try:
        bible_dir = Path(__file__).parent / "series_memory"
        if bible_dir.exists():
            for p in bible_dir.glob("*_bible.json"):
                try:
                    with open(p, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    chars_dict = data.get("characters", {})
                    chars_set = set(chars_dict.keys())
                    chars_all_set = {c.lower() for c in chars_set}

                    rel_participants = set()
                    for rk in list(data.get("relationships", {}).keys()) + list(data.get("relations", {}).keys()):
                        if "->" in rk:
                            parts = [p.strip().lower() for p in rk.split("->")]
                            for part in parts:
                                rel_participants.add(part)
                                rel_participants.add(normalize_ascii_diacritics(part))
                                rel_participants.add(normalize_name_nfkd(part))
                                for sub_p in part.split("/"):
                                    sub_clean = sub_p.strip()
                                    rel_participants.add(sub_clean)
                                    rel_participants.add(normalize_ascii_diacritics(sub_clean))
                                    rel_participants.add(normalize_name_nfkd(sub_clean))

                    ROLE_SUFFIXES = {
                        "captain", "kapitan", "guard", "strażnik", "soldier", "żołnierz",
                        "recruit", "rekrut", "officer", "oficer", "general", "generał",
                        "kid", "bro", "brother", "mother", "father", "son", "daughter",
                        "lord", "lady", "king", "queen", "duke", "baron", "count",
                        "headman", "leader", "elder", "commander", "knight",
                        "a", "b", "c", "d", "e", "f", "1", "2", "3"
                    }
                    for c_name, c_data in chars_dict.items():
                        c_words = [w.lower() for w in c_name.split()]
                        if not any(w in ROLE_SUFFIXES for w in c_words):
                            chars_all_set.update(c_words)
                        if isinstance(c_data, dict):
                            for al in c_data.get("aliases", []):
                                al_words = [w.lower() for w in al.split()]
                                if not any(w in ROLE_SUFFIXES for w in al_words) and not any(w in ROLE_SUFFIXES for w in c_words):
                                    chars_all_set.add(al.lower())
                                    chars_all_set.update(al_words)

                    TOPONYM_KEYWORDS = ["toponim", "kraina", "miasto", "cesarstwo", "królestwo", "prowincja", "okręg", "lokacja", "zamek", "twierdza"]
                    for k, v in data.get("glossary", {}).items():
                        if isinstance(v, str):
                            k_l = k.lower()
                            k_norm = normalize_name_nfkd(k_l)
                            k_ascii = normalize_ascii_diacritics(k_l)
                            if any(kw in v.lower() for kw in TOPONYM_KEYWORDS):
                                if k not in chars_set and v.split()[0] not in chars_set and k_l not in rel_participants and k_norm not in rel_participants and k_ascii not in rel_participants:
                                    toponyms.add(k_l)
                                    toponyms.add(v.split()[0].lower())
                            elif k == v and len(k.split()) == 1 and k_l not in chars_all_set and k_l not in rel_participants and k_norm not in rel_participants and k_ascii not in rel_participants:
                                toponyms.add(k_l)
                    for k, v in data.get("custom_glossary", {}).items():
                        if isinstance(v, str):
                            k_l = k.lower()
                            k_norm = normalize_name_nfkd(k_l)
                            k_ascii = normalize_ascii_diacritics(k_l)
                            if any(kw in v.lower() for kw in TOPONYM_KEYWORDS):
                                if k not in chars_set and v.split()[0] not in chars_set and k_l not in rel_participants and k_norm not in rel_participants and k_ascii not in rel_participants:
                                    toponyms.add(k_l)
                                    toponyms.add(v.split()[0].lower())
                            elif k == v and len(k.split()) == 1 and k_l not in chars_all_set and k_l not in rel_participants and k_norm not in rel_participants and k_ascii not in rel_participants:
                                toponyms.add(k_l)
                    entity_cats = data.get("entity_categories") or data.get("entities") or {}
                    for k, cat in entity_cats.items():
                        if cat in ("TOPONYM", "CHREMATONYM"):
                            k_l = k.lower()
                            k_norm = normalize_name_nfkd(k_l)
                            k_ascii = normalize_ascii_diacritics(k_l)
                            if k not in chars_set and k_l not in rel_participants and k_norm not in rel_participants and k_ascii not in rel_participants:
                                toponyms.add(k_l)
                except Exception:
                    logger.warning("Klasyfikacja toponimu ze słownika zakończona wyjątkiem", exc_info=True)
    except Exception:
        logger.warning("Pozyskiwanie toponimów z bazy wiedzy zakończone wyjątkiem", exc_info=True)
    return toponyms


KNOWN_FANTASY_TOPONYMS: Set[str] = _load_dynamic_fantasy_toponyms()


def sanitize_toponymic_origin_and_companionship(text: str, custom_glossary: Optional[Dict[str, str]] = None) -> str:
    """
    Sanitizes toponymic origin vs animate companionship errors (Filar CLXXXIV / 0.00 PLN).
    When a toponym (realm, city, location) qualifies an artifact, object, or person of origin
    ('from Hiden', 'knight from realm', 'people from province'), Polish preposition 'z'
    strictly governs Genitive (Dopełniacz pochodzenia: 'z Hiden', 'z Kanyou', 'z Ridill'),
    NEVER Instrumental (Narzędnik towarzyszenia: '*z Hidenem', '*z Kanyouem').
    Also handles compound artifact title syntagmas and prevents modifier hyper-inflection,
    strictly adhering to the Single-Word Invariance Principle (W_i -> W'_i).
    """
    if not text:
        return ""
    res = text

    # 1. False Instrumental of origin for realms/toponyms ending in consonants across all series
    # Helper to fix preposition (z/ze) before toponyms with support for ASS line breaks (\N, \n, \h) and inline tags
    def _fix_toponym_companionship(src: str, inflected_names: str, target: str) -> str:
        pat = rf"(^|\\[Nnh]|[^\w])([Zz])(?:e)?((?:\s|\\[Nnh]|\{{[^}}]+\}})+)(?:{inflected_names})\b"
        return re.sub(pat, rf"\g<1>\g<2>\g<3>{target}", src)

    # Dynamic and baseline toponym normalization
    for top in sorted(KNOWN_FANTASY_TOPONYMS, key=len, reverse=True):
        if len(top) < 3:
            continue
        top_cap = top.capitalize()
        if top.endswith("e"):
            stem = top_cap[:-1]
            inf = f"{re.escape(top_cap)}m|{re.escape(stem)}em|{re.escape(top_cap)}em|{re.escape(top_cap)}rem|{re.escape(top_cap)}tem"
        else:
            inf = f"{re.escape(top_cap)}em"
        res = _fix_toponym_companionship(res, inf, top_cap)

    # 1b. False Instrumental of origin for feminine-like toponyms and entities in origin contexts
    def _repl_origin_feminine_inst(m):
        prefix_lead = m.group(1) or ""
        trigger = m.group(2)
        sep1 = m.group(3)
        prep = m.group(4)
        sep2 = m.group(5)
        noun_inst = m.group(6)
        stem = noun_inst[:-1]
        base_nom = stem + "a"
        if not is_feminine_instrumental_after_z_allowed(base_nom, preceding_text=f"{trigger} {prep}"):
            gen_ending = "i" if stem.endswith(("k", "g")) else "y"
            target_gen = stem + gen_ending
            return f"{prefix_lead}{trigger}{sep1}{prep}{sep2}{target_gen}"
        return m.group(0)

    pat_origin_fem = rf"(^|\\[Nnh]|[^\w])({ORIGIN_GROUP_NOUNS_PATTERN}|{ABLATIVE_MOTION_VERBS_PATTERN})((?:\s|\\[Nnh])+)([Zz])(?:e)?((?:\s|\\[Nnh])+)([A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]+ą)\b"
    res = re.sub(pat_origin_fem, _repl_origin_feminine_inst, res, flags=re.IGNORECASE)

    # 1b-2. False Instrumental of origin for institutional nouns after z
    INSTITUTION_GENITIVE_MAP = {
        "biurem": "biura",
        "miastem": "miasta",
        "królestwem": "królestwa",
        "cesarstwem": "cesarstwa",
        "księstwem": "księstwa",
        "ministerstwem": "ministerstwa",
        "dowództwem": "dowództwa",
    }
    for bad_inst, good_inst in INSTITUTION_GENITIVE_MAP.items():
        pat_inst = rf"(^|\\[Nnh]|[^\w])({ORIGIN_GROUP_NOUNS_PATTERN}|{ABLATIVE_MOTION_VERBS_PATTERN})((?:\s|\\[Nnh])+)([Zz])(?:e)?((?:\s|\\[Nnh])+){bad_inst}\b"
        res = re.sub(pat_inst, rf"\g<1>\g<2>\g<3>\g<4>\g<5>{good_inst}", res, flags=re.IGNORECASE)

    # 1c. False Instrumental of origin for realms preceded by origin / collective demonstratives
    DEMONSTRATIVE_ORIGIN_NOUNS = r"(ci|tamci|oni|ten|ta|to|ludzie|żołnierze|wojska|oddział|oddziały|armia|wojownicy|posłaniec|uciekinierzy|zbieg|pochodzi[a-ząćęłńóśźż]*|przybył[a-ząćęłńóśźż]*|wrócił[a-ząćęłńóśźż]*)"
    SEP = r"((?:\s|\\[Nnh]|\{{[^}}]+\}})+)"
    for top in sorted(KNOWN_FANTASY_TOPONYMS, key=len, reverse=True):
        if len(top) < 3:
            continue
        top_cap = top.capitalize()
        if top.endswith("e"):
            inf_pat = f"{re.escape(top_cap)}rem|{re.escape(top_cap)}tem|{re.escape(top_cap)}m|{re.escape(top_cap)}"
        else:
            inf_pat = f"{re.escape(top_cap)}em|{re.escape(top_cap)}u|{re.escape(top_cap)}"
        res = re.sub(rf"(^|\\[Nnh]|[^\w]){DEMONSTRATIVE_ORIGIN_NOUNS}{SEP}(?:[Zz]e|[Zz]){SEP}(?:{inf_pat})\b", rf"\g<1>\g<2>\g<3>z\g<4>{top_cap}", res, flags=re.IGNORECASE)

    # Dynamic integration of custom_glossary and fantasy toponyms
    if custom_glossary and isinstance(custom_glossary, dict):
        TOPONYM_KEYWORDS = {"kraina", "prowincja", "domena", "królestwo", "cesarstwo", "miasto", "zamek", "okręg", "district", "province", "domain", "kingdom", "empire", "realm", "toponim", "miejsce", "twierdza", "stolica"}
        for k, v in custom_glossary.items():
            k_clean = str(k).strip()
            v_clean = str(v).strip()
            k_lower = k_clean.lower()
            v_lower = v_clean.lower()
            is_toponym = (
                k_lower in KNOWN_FANTASY_TOPONYMS or
                v_lower in KNOWN_FANTASY_TOPONYMS or
                any(kw in v_lower for kw in TOPONYM_KEYWORDS) or
                any(kw in k_lower for kw in TOPONYM_KEYWORDS)
            )
            if is_toponym and len(v_clean) >= 3:
                v_words = [w for w in re.split(r"[\s();,]+", v_clean) if w and w[0].isupper() and w.lower() not in {"królestwo", "cesarstwo", "kraina", "księstwo", "miasto", "zamek"}]
                cand_target = v_words[0] if v_words else v_clean.split()[0]
                if cand_target:
                    targets = [cand_target]
                    if k_clean and len(k_clean) >= 3 and k_clean != cand_target:
                        k_words = [w for w in re.split(r"[\s();,]+", k_clean) if w and w[0].isupper() and w.lower() not in {"kingdom", "empire", "realm", "province", "city"}]
                        k_base = k_words[0] if k_words else k_clean
                        targets.append(k_base)
                    pats = []
                    for t in targets:
                        if t.endswith("e"):
                            stem = t[:-1]
                            pats.append(f"{re.escape(t)}m|{re.escape(stem)}em|{re.escape(t)}rem|{re.escape(t)}tem")
                        else:
                            pats.append(f"{re.escape(t)}em")
                    inf_pat = "|".join(pats)
                    res = _fix_toponym_companionship(res, inf_pat, cand_target)
                    for t in targets:
                        if t != cand_target:
                            res = re.sub(rf"\b([ZzWwOo]|do|dla|ku|przez|od)\s+{re.escape(t)}\b", rf"\g<1> {cand_target}", res)
                            res = re.sub(rf"\b([Kk]rólestw[a-ząćęłńóśźż]*|[Cc]esarstw[a-ząćęłńóśźż]*|[Kk]rain[a-ząćęłńóśźż]*)\s+{re.escape(t)}\b", rf"\g<1> {cand_target}", res)
                    relic_pat = "|".join([re.escape(t) for t in targets])
                    res = re.sub(rf"\b([Zz]\s+[A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]+ą)\s+([A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]+a)\s+([Zz]\s+)(?:{relic_pat})(?:em)?\b", rf"\g<1> \g<2> \g<3>{cand_target}", res)
    res = re.sub(
        r"\b([Zz]\s+)([Kk]sięga|[Tt]arcza|[Dd]olina|[Pp]ieczęć)\s+([A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]+a)\b",
        lambda m: f"{m.group(1)}{m.group(2)[:-1] + 'ą' if m.group(2).endswith('a') else m.group(2)} {m.group(3)}",
        res
    )
    res = re.sub(
        r"\b([Ss]zuka[a-ząćęłńóśźż]*|[Pp]ilnuje|[Pp]ilnowa[a-ząćęłńóśźż]*|[Uu]żywa[a-ząćęłńóśźż]*|[Ss]trzeż[a-ząćęłńóśźż]*)((?:\s|\\[Nnh])+)([Kk]sięga|[Tt]arcza)\s+([A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]+a)\b",
        lambda m: f"{m.group(1)}{m.group(2)}{m.group(3)[:-1] + 'i' if m.group(3).endswith('ga') else (m.group(3)[:-1] + 'y' if m.group(3).endswith('a') else m.group(3))} {m.group(4)}",
        res
    )

    return res


def _fix_ze_before_consonant_toponyms(m: re.Match) -> str:
    lead = m.group(1)
    prep = m.group(2)
    sep = m.group(3)
    word = m.group(4)
    if word.lower() in KNOWN_FANTASY_TOPONYMS or (word and word[0].isupper() and not word.lower().startswith(('s', 'z', 'ś', 'ź', 'ż', 'sz', 'rz', 'w'))):
        p_out = "Z" if prep.isupper() else "z"
        return f"{lead}{p_out}{sep}{word}"
    return m.group(0)


def sanitize_closed_idioms_and_prepositions(text: str) -> str:
    """
    Sanitizes closed, invariant register idioms and PWN prepositional-pronominal forms.
    Guaranteed 100% syntactically closed — zero inflectional risk, zero nominative freezing.
    """
    if not text:
        return ""
    res = text
    INVARIANT_RULES = [
        # PWN Preposition-Pronoun phonetic government
        (r"\b([Dd]la)\s+mię\b", lambda m: "Dla mnie" if m.group(1)[0].isupper() else "dla mnie"),
        (r"\b([Oo]de)\s+mie\b", lambda m: "Ode mnie" if m.group(1)[0].isupper() else "ode mnie"),
        (r"\b([Oo]d)\s+mnie\b", lambda m: "Ode mnie" if m.group(1)[0].isupper() else "ode mnie"),
        (r"\b([Zz])\s+mną\b", lambda m: "Ze mną" if m.group(1)[0].isupper() else "ze mną"),
        (r"\b([Pp]rzed)\s+mną\b", lambda m: "Przede mną" if m.group(1)[0].isupper() else "przede mną"),
        # PWN Preposition phonetic alternations: 'ze' before s/z/sz/ż/ś/ź + consonant, 'we' before w/f + consonant
        (r"\b([Zz])\s+(stali|złota|żelaza|szkła|srebra|strachu|szmaragdu|złości|zazdrości|związku|Szwecji|Szwajcarii)\b",
         lambda m: ("Ze " if m.group(1).isupper() else "ze ") + m.group(2)),
        (r"(^|\\[Nnh]|[^\w])([Zz])e((?:\s|\\[Nnh])+)([A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]+)\b", _fix_ze_before_consonant_toponyms),
        (r"\b([Ww])\s+(Francji|Florencji|Flandrii|Włoszech|wrześniu|wtorku|wpół)\b",
         lambda m: ("We " if m.group(1).isupper() else "we ") + m.group(2)),
        # Closed invariant register idioms
        (r"\b([Ww])\s+każdym\s+bądź\s+razie\b", lambda m: "W każdym razie" if m.group(1)[0].isupper() else "w każdym razie"),
        (r"\b([Bb])ez\s+jaj[!]+", lambda m: "To jakieś kpiny!" if m.group(1)[0].isupper() else "to jakieś kpiny!"),
        (r"\b([Gg])uzik\s+mnie\s+to\s+obchodzi\b", lambda m: "Nic mnie to nie obchodzi" if m.group(1)[0].isupper() else "nic mnie to nie obchodzi"),
        (r"\b([Pp])omiędzy\s+tobą\s+i\s+mną\b", lambda m: "Między nami" if m.group(1)[0].isupper() else "między nami"),
        (r"\b([Pp])omiędzy\s+nami\b", lambda m: "Między nami" if m.group(1)[0].isupper() else "między nami"),
        (r"\b([Ww])\s+mrugnięciu\s+oka\b", lambda m: "W mgnieniu oka" if m.group(1)[0].isupper() else "w mgnieniu oka"),
    ]
    for pat, repl in INVARIANT_RULES:
        res = re.sub(pat, repl, res)
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
    _lock = threading.RLock()

    def __new__(cls, *args, **kwargs):
        inst = super().__new__(cls)
        inst._lock = threading.RLock()
        return inst

    def __init__(self, anime_title: str = "Nieznana Seria", storage_dir: Optional[Path] = None, db_path: Optional[str] = None, **kwargs):
        self._lock = threading.RLock()
        self.db_path = db_path
        slug_arg = kwargs.get("slug")
        title_arg = kwargs.get("title") or kwargs.get("anime_title")
        if slug_arg and (not anime_title or anime_title == "Nieznana Seria"):
            self.anime_title = str(slug_arg).strip()
            self.slug = clean_anime_slug(slug_arg)
        else:
            self.anime_title = str(title_arg or anime_title).strip() if (title_arg or anime_title) else "Nieznana Seria"
            self.slug = clean_anime_slug(slug_arg or self.anime_title)
        self.storage_dir = storage_dir or SERIES_MEMORY_DIR
        if self.db_path != ":memory:":
            self.storage_dir.mkdir(parents=True, exist_ok=True)
            self.file_path = self._resolve_bible_path()
            repo_root = Path(__file__).resolve().parent
            artefakty_dir = repo_root / "Artefakty"
            if artefakty_dir.exists() and (storage_dir is None or storage_dir == SERIES_MEMORY_DIR):
                artefakty_file = artefakty_dir / self.file_path.name
                if artefakty_file.exists():
                    self.artefakty_path = artefakty_file
                else:
                    self.artefakty_path = None
            else:
                self.artefakty_path = None
        else:
            self.file_path = Path(":memory:")
            self.artefakty_path = None
        
        self.data: Dict[str, Any] = {
            "anime_title": self.anime_title,
            "characters": CharacterRegistryDict({}, bible_data=None),          # { "Arata": {"gender": "męska", "role": "uczeń", "forms": "Arata"} }
            "glossary": {},            # { "Choushi": "czara na sake", "Dragon Slayer": "Pogromca Smoków" }
            "relationships": {},      # { "Kokoro->Arata": "po imieniu / na ty", "Uczniowie->Teshima": "pani Teshima" }
            "relations": {},          # { "X -> Y": "..." }
            "declensions": {},        # { "Shira": {"M": "Shira", "D": "Shiry", "C": "Shirze", ...} }
            "hypocorisms": {},        # { "Ren": "Renko", "Rin": "Rinko" }
            "plot_anchors": {},        # { "kamień jada": "rytualny artefakt wywołujący deszcz", "zbieg z Samarkandy": "Shira" }
            "episodes_translated": [], # ["odcinek 1", "odcinek 2"]
            "batch_stats": {}          # { "odcinek 1": {"batches": 17, "dialogues": 374, "avg_batch_size": 22.0} }
        }
        self.data["characters"].bible_data = self.data
        if self.db_path != ":memory:":
            self.load()

    @property
    def characters(self) -> Dict[str, Any]:
        with self._lock:
            chars = self.data.get("characters")
            if chars is None:
                chars = CharacterRegistryDict({}, bible_data=self.data)
                self.data["characters"] = chars
            return chars

    @characters.setter
    def characters(self, val: Any) -> None:
        with self._lock:
            if isinstance(val, CharacterRegistryDict):
                val.bible_data = self.data
                self.data["characters"] = val
            else:
                self.data["characters"] = CharacterRegistryDict(val or {}, bible_data=self.data)

    @property
    def relations(self) -> Dict[str, Any]:
        with self._lock:
            return self.data.setdefault("relations", {})

    @relations.setter
    def relations(self, val: Any) -> None:
        with self._lock:
            self.data["relations"] = val or {}

    @property
    def declensions(self) -> Dict[str, Any]:
        with self._lock:
            return self.data.setdefault("declensions", {})

    @declensions.setter
    def declensions(self, val: Any) -> None:
        with self._lock:
            self.data["declensions"] = val or {}

    @property
    def glossary(self) -> Dict[str, Any]:
        with self._lock:
            return self.data.setdefault("glossary", {})

    @glossary.setter
    def glossary(self, val: Any) -> None:
        with self._lock:
            self.data["glossary"] = val or {}

    def register_character(
        self,
        name: str,
        gender: str = "UNKNOWN",
        description: str = "",
        has_verified_gender: bool = False,
        priority: str = "P1",
        **kwargs
    ) -> Dict[str, Any]:
        """
        Rejestruje postać w rejestrze postaci SeriesBible zgodnie z pozytywnym schematem
        CharacterRecord (Standard 9.0/9.1/9.2).
        """
        with self._lock:
            clean_name = str(name).strip()
            g_upper = str(gender).upper()
            if "MALE" in g_upper and "FEMALE" not in g_upper:
                norm_gender = "MALE"
                gram_gender = "MASCULINE"
            elif "FEMALE" in g_upper:
                norm_gender = "FEMALE"
                gram_gender = "FEMININE"
            else:
                norm_gender = "UNKNOWN"
                gram_gender = "UNKNOWN"
            
            p0 = (priority == "P0" or has_verified_gender or (norm_gender != "UNKNOWN" and priority == "P0"))
            eff_has_verified = has_verified_gender or (norm_gender != "UNKNOWN" and priority == "P0")
            eff_priority = "P0" if p0 else priority
            eff_conf = 0.95 if p0 else float(kwargs.get("confidence", 0.5))

            aliases = kwargs.get("aliases")
            if aliases is None:
                aliases = [clean_name] if clean_name else []
            elif clean_name and clean_name not in aliases:
                aliases.append(clean_name)

            record = {
                "name": clean_name,
                "gender": norm_gender,
                "grammatical_gender": gram_gender,
                "confidence": eff_conf,
                "priority": eff_priority,
                "has_verified_gender": eff_has_verified,
                "aliases": aliases,
                "description": description or kwargs.get("role", "postać"),
                "entity_category": kwargs.get("entity_category", "ANTHROPONYM")
            }
            self.data["characters"][clean_name] = record
            return record

    def sync_verified_profile_entity(
        self,
        name: str,
        gender: Optional[str] = None,
        has_verified_gender: bool = True,
        declension_map: Optional[Dict[str, str]] = None,
        description: Optional[str] = None,
        priority: str = "P0"
    ) -> Dict[str, Any]:
        """
        Synchronizuje zweryfikowaną postać P0 z profilera do SeriesBible
        wraz z pełną 7-przypadkową macierzą deklinacji (M, D, C, B, N, Ms, W).
        """
        with self._lock:
            clean_name = str(name).strip()
            existing_char = self.data.get("characters", {}).get(clean_name, {})
            if gender is None:
                norm_gender = existing_char.get("gender", "UNKNOWN") if isinstance(existing_char, dict) else "UNKNOWN"
                gram_gender = existing_char.get("grammatical_gender", "UNKNOWN") if isinstance(existing_char, dict) else "UNKNOWN"
            else:
                g_upper = str(gender).upper()
                if "MALE" in g_upper and "FEMALE" not in g_upper:
                    norm_gender = "MALE"
                    gram_gender = "MASCULINE"
                elif "FEMALE" in g_upper:
                    norm_gender = "FEMALE"
                    gram_gender = "FEMININE"
                else:
                    norm_gender = "UNKNOWN"
                    gram_gender = "UNKNOWN"

            existing_char = self.data.get("characters", {}).get(clean_name, {})
            existing_aliases = existing_char.get("aliases", []) if isinstance(existing_char, dict) else []
            combined_aliases = list(dict.fromkeys([clean_name] + existing_aliases))
            record = {
                "name": clean_name,
                "gender": norm_gender,
                "grammatical_gender": gram_gender,
                "confidence": 0.95,
                "priority": priority,
                "has_verified_gender": has_verified_gender,
                "aliases": combined_aliases,
                "description": description or existing_char.get("description") or f"Postać ({norm_gender.lower()})",
                "entity_category": "ANTHROPONYM"
            }
            self.data["characters"][clean_name] = record
            
            if declension_map:
                # 2C.9: Bezwarunkowy transfer pełnego 7-przypadkowego paradygmatu M..W
                self.data.setdefault("declensions", {})[clean_name] = dict(declension_map)
            else:
                existing_decl = self.data.setdefault("declensions", {}).get(clean_name)
                is_frozen_nominative = False
                if isinstance(existing_decl, dict):
                    m_val = existing_decl.get("M", clean_name)
                    cases_dep = [existing_decl.get(c) for c in ("D", "C", "B", "N", "Ms", "W")]
                    if all(c == m_val for c in cases_dep):
                        is_frozen_nominative = True
                if clean_name not in self.data["declensions"] or is_frozen_nominative:
                    gen_func = globals().get("generate_polish_name_declension")
                    if callable(gen_func):
                        self.data["declensions"][clean_name] = gen_func(clean_name, norm_gender)
            return record

    def get_declension(self, entity_key: str, case: str = "M") -> str:
        """
        Zwraca formę deklinacyjną bytu dla zadanego przypadku gramatycznego (M, D, C, B, N, Ms, W).
        W przypadku braku wpisu zwraca postać bazową entity_key (Identity Pass-Through).
        """
        with self._lock:
            clean_key = str(entity_key).strip()
            decl_map = self.data.get("declensions", {}).get(clean_key)
            if not decl_map or not isinstance(decl_map, dict):
                return clean_key
            return decl_map.get(case, clean_key)

    def synchronize_from_metadata_and_profile(
        self,
        anilist_meta: Optional[Dict[str, Any]] = None,
        episode_profile: Optional[Any] = None
    ) -> None:
        """
        Synchronizuje struktury SeriesBible (characters, relations, declensions)
        z danymi z metadanych serii (Krok 3) oraz profilera odcinka (Krok 5).
        Zapewnia pełne pokrycie postaci obecnych i wspominanych oraz priorytet P0.
        """
        with self._lock:
            # 1. Postacie z anilist_meta
            if anilist_meta and isinstance(anilist_meta.get("characters"), list):
                for c in anilist_meta["characters"]:
                    if not isinstance(c, dict):
                        continue
                    c_name = c.get("name")
                    if isinstance(c_name, dict):
                        c_name = c_name.get("full") or c_name.get("userPreferred") or ""
                    if not c_name or not is_valid_anthroponymic_phonotactics(c_name):
                        continue
                    c_gen = c.get("gender")
                    c_role = c.get("role", "postać")
                    c_desc = c.get("description", "")
                    
                    gen_norm = None
                    if c_gen:
                        c_gen_str = str(c_gen).upper()
                        if "MALE" in c_gen_str and "FEMALE" not in c_gen_str:
                            gen_norm = "MALE"
                        elif "FEMALE" in c_gen_str:
                            gen_norm = "FEMALE"
                    
                    existing = self.data["characters"].get(c_name)
                    if not existing or not isinstance(existing, dict):
                        self.register_character(
                            name=c_name,
                            gender=gen_norm or "UNKNOWN",
                            description=c_desc,
                            has_verified_gender=bool(gen_norm),
                            priority="P0" if gen_norm else "P1",
                            role=c_role
                        )
                    else:
                        if gen_norm and not existing.get("has_verified_gender"):
                            existing["gender"] = gen_norm
                            existing["grammatical_gender"] = "MASCULINE" if gen_norm == "MALE" else "FEMININE"
                            existing["has_verified_gender"] = True
                            existing["confidence"] = 0.95
                            existing["priority"] = "P0"

            # 2. Postacie z EpisodeProfile.character_dossiers
            if episode_profile and getattr(episode_profile, "character_dossiers", None):
                for cd in episode_profile.character_dossiers:
                    cd_name = getattr(cd, "name", None)
                    if not cd_name or not is_valid_anthroponymic_phonotactics(cd_name):
                        continue
                    cd_gen_raw = str(getattr(cd, "gender", "") or getattr(cd, "apparent_gender", "") or "").upper()
                    cd_pronouns = getattr(cd, "first_person_pronouns", []) or [getattr(cd, "first_person_pronoun", "")]
                    is_male_pronoun = any(str(p).lower() in ("ore", "boku", "oira", "washi") for p in cd_pronouns if p)
                    cd_is_male = ("MALE" in cd_gen_raw or "MASCULINE" in cd_gen_raw or is_male_pronoun) and "FEMALE" not in cd_gen_raw and "FEMININE" not in cd_gen_raw
                    cd_is_female = ("FEMALE" in cd_gen_raw or "FEMININE" in cd_gen_raw)
                    cd_gen = "MALE" if cd_is_male else ("FEMALE" if cd_is_female else None)
                    cd_role = getattr(cd, "age_and_role", "postać") or "postać"
                    
                    curr = self.data["characters"].get(cd_name)
                    if not curr or not isinstance(curr, dict):
                        self.sync_verified_profile_entity(
                            name=cd_name,
                            gender=cd_gen or "UNKNOWN",
                            has_verified_gender=bool(cd_gen),
                            description=cd_role,
                            priority="P0" if cd_gen else "P1"
                        )
                    else:
                        if cd_gen:
                            curr["gender"] = cd_gen
                            curr["grammatical_gender"] = "MASCULINE" if cd_gen == "MALE" else "FEMININE"
                            curr["has_verified_gender"] = True
                            curr["confidence"] = 0.95
                            curr["priority"] = "P0"

            # 3. Deklinacje i autoreferencja z EpisodeProfile.name_declensions
            if episode_profile and getattr(episode_profile, "name_declensions", None):
                for nd in episode_profile.name_declensions:
                    nd_name = getattr(nd, "character_name", None)
                    if not nd_name or not is_valid_anthroponymic_phonotactics(nd_name):
                        continue
                    paradigm = {
                        "M": getattr(nd, "mianownik", None) or nd_name,
                        "D": getattr(nd, "dopelniacz", None) or nd_name,
                        "C": getattr(nd, "celownik", None) or nd_name,
                        "B": getattr(nd, "biernik", None) or nd_name,
                        "N": getattr(nd, "narzednik", None) or nd_name,
                        "Ms": getattr(nd, "miejscownik", None) or nd_name,
                        "W": getattr(nd, "wolacz", None) or nd_name,
                    }
                    self.data.setdefault("declensions", {})[nd_name] = paradigm
                    
                    # Weryfikacja męskiego paradygmatu / zaimka autoreferencyjnego
                    nd_gen_raw = str(getattr(nd, "gender", "") or getattr(nd, "grammatical_gender", "") or "").upper()
                    is_masc_decl = (
                        (("MALE" in nd_gen_raw or "MASCULINE" in nd_gen_raw) and ("FEMALE" not in nd_gen_raw and "FEMININE" not in nd_gen_raw)) or
                        bool(paradigm["N"] and (paradigm["N"].endswith("em") or paradigm["N"].endswith("im") or paradigm["N"].endswith("ym"))) or
                        bool(paradigm["D"] and (paradigm["D"].endswith("a") or paradigm["D"].endswith("u") or paradigm["D"].endswith("ego") or paradigm["D"].endswith("emu")))
                    )
                    
                    char_entry = self.data["characters"].get(nd_name)
                    if not char_entry or not isinstance(char_entry, dict):
                        c_gen = "MALE" if is_masc_decl else ("FEMALE" if "FEMALE" in nd_gen_raw else None)
                        self.data["characters"][nd_name] = {
                            "name": nd_name,
                            "gender": c_gen,
                            "grammatical_gender": "MASCULINE" if c_gen == "MALE" else ("FEMININE" if c_gen == "FEMALE" else None),
                            "role": "postać",
                            "description": "postać",
                            "confidence": 0.95 if c_gen else 0.5,
                            "priority": "P0" if c_gen else "P1",
                            "has_verified_gender": bool(c_gen),
                            "aliases": []
                        }
                    else:
                        if is_masc_decl and (not char_entry.get("has_verified_gender") or not char_entry.get("gender")):
                            char_entry["gender"] = "MALE"
                            char_entry["grammatical_gender"] = "MASCULINE"
                            char_entry["confidence"] = 0.95
                            char_entry["priority"] = "P0"
                            char_entry["has_verified_gender"] = True

            # 4. Synchronizacja EpisodeProfile.continuity_bridge_alerts i rejestracja postaci wspominanych
            if episode_profile and getattr(episode_profile, "continuity_bridge_alerts", None):
                self.data.setdefault("continuity_bridge_alerts", {})
                for cba in episode_profile.continuity_bridge_alerts:
                    term = getattr(cba, "term_or_event", None)
                    guide = getattr(cba, "continuity_guidance", "") or ""
                    if term:
                        self.data["continuity_bridge_alerts"][term] = guide
                        if is_valid_anthroponymic_phonotactics(term):
                            guide_lower = guide.lower()
                            is_fem = any(w in guide_lower for w in ("kobieta", "żeńsk", "żeńska", "władczyni", "królowa", "księżniczka", "dziewczyna", "female"))
                            is_masc = any(w in guide_lower for w in ("mężczyzna", "męsk", "męska", "władca", "król", "książę", "chłopak", "male")) and not is_fem
                            if is_fem or is_masc or "postać" in guide_lower or "character" in guide_lower:
                                gen = "FEMALE" if is_fem else ("MALE" if is_masc else None)
                                if term not in self.data["characters"]:
                                    self.data["characters"][term] = {
                                        "name": term,
                                        "gender": gen,
                                        "grammatical_gender": "FEMININE" if gen == "FEMALE" else ("MASCULINE" if gen == "MALE" else None),
                                        "role": "postać wspominana",
                                        "description": guide,
                                        "confidence": 0.95 if gen else 0.5,
                                        "priority": "P0" if gen else "P1",
                                        "has_verified_gender": bool(gen),
                                        "aliases": []
                                    }

            # 5. Relacje z character_relationships
            if episode_profile and getattr(episode_profile, "character_relationships", None):
                for rel in episode_profile.character_relationships:
                    spk = getattr(rel, "speaker", None)
                    lis = getattr(rel, "listener", None)
                    if spk and lis:
                        rel_key = f"{spk}->{lis}"
                        rel_val = f"{getattr(rel, 'address_form', '')} ({getattr(rel, 'relationship_type', '')})".strip()
                        self.data.setdefault("relations", {})[rel_key] = rel_val
                        self.data.setdefault("relationships", {})[rel_key] = rel_val

            if hasattr(self, "_rebuild_actor_aliases_index"):
                try:
                    self._rebuild_actor_aliases_index()
                except Exception:
                    logger.warning("Odbudowa indeksu aliasów aktora zakończona wyjątkiem", exc_info=True)

    def get_characters_snapshot(self) -> Dict[str, Any]:
        with self._lock:
            return dict(self.data.get("characters", {}))

    def get_declensions_snapshot(self) -> Dict[str, Any]:
        with self._lock:
            return dict(self.data.get("declensions", {}))

    def get_relationships_snapshot(self) -> Dict[str, Any]:
        with self._lock:
            return dict(self.data.get("relationships", {}))

    def get_relations_snapshot(self) -> Dict[str, Any]:
        with self._lock:
            return dict(self.data.get("relations", {}))

    def get_glossary_snapshot(self) -> Dict[str, Any]:
        with self._lock:
            return dict(self.data.get("glossary", {}))

    def register_character_identity(self, identity: CharacterIdentity) -> None:
        """Rejestruje tożsamość diegetyczną postaci ze stanami dyskursu."""
        with self._lock:
            if "character_identities" not in self.data:
                self.data["character_identities"] = {}
            if identity.declension_paradigm is None:
                identity.declension_paradigm = self.get_declension_paradigm(identity.canonical_id)
            self.data["character_identities"][identity.canonical_id] = identity.model_dump()

    def get_character_identity(self, canonical_id: str) -> Optional[CharacterIdentity]:
        """Pobiera zarejestrowaną tożsamość diegetyczną postaci lub dziedziczy kanonicznie z bytu bazowego."""
        if not canonical_id:
            return None
        clean_id = canonical_id.strip()
        with self._lock:
            identities = self.data.get("character_identities", {})
            raw = identities.get(clean_id)
            if not raw:
                clean_norm = normalize_name_nfkd(clean_id).lower()
                for k, v in identities.items():
                    if k.lower() == clean_id.lower() or normalize_name_nfkd(k).lower() == clean_norm:
                        raw = v
                        break
            if raw:
                try:
                    return CharacterIdentity(**raw)
                except Exception:
                    logger.warning("Inicjalizacja tożsamości postaci zakończona wyjątkiem", exc_info=True)

            # Kanoniczne dziedziczenie dla prefiksów wiekowych, czasowych i stanowych
            base_name = extract_base_canonical_name(clean_id)
            if base_name and base_name.lower() != clean_id.lower():
                # 1. Base from character_identities
                base_id = None
                base_raw = identities.get(base_name)
                if not base_raw:
                    base_norm = normalize_name_nfkd(base_name).lower()
                    for k, v in identities.items():
                        if k.lower() == base_name.lower() or normalize_name_nfkd(k).lower() == base_norm:
                            base_raw = v
                            break
                if base_raw:
                    try:
                        base_id = CharacterIdentity(**base_raw)
                    except Exception:
                        logger.warning("Inicjalizacja bazowej tożsamości postaci zakończona wyjątkiem", exc_info=True)

                if base_id:
                    inherited_decl = self.get_declension_paradigm(clean_id)
                    return CharacterIdentity(
                        canonical_id=clean_id,
                        true_gender=base_id.true_gender,
                        discourse_states=copy.deepcopy(base_id.discourse_states),
                        entity_category=base_id.entity_category,
                        declension_paradigm=inherited_decl,
                        base_canonical_id=base_id.canonical_id
                    )

                # 2. Base from general characters in SeriesBible
                base_gender = self.get_character_gender(base_name, allow_generic_nouns=False)
                if base_gender in ("MALE", "FEMALE"):
                    t_g = "MASCULINE" if base_gender == "MALE" else "FEMININE"
                    return CharacterIdentity(
                        canonical_id=clean_id,
                        true_gender=t_g,
                        discourse_states=[],
                        entity_category=EntityCategory.ANTHROPONYM,
                        declension_paradigm=self.get_declension_paradigm(clean_id),
                        base_canonical_id=base_name
                    )

            # Relational resolving ([Owner]'s Son/Daughter/Kid)
            rel_gender, rel_conf = resolve_possessive_relation_gender(
                clean_id,
                is_flashback=any(fb in clean_id.lower() for fb in ("flashback", "retrospekcj", "past")),
                series_bible=self
            )
            if rel_gender in ("MALE", "FEMALE"):
                t_g = "MASCULINE" if rel_gender == "MALE" else "FEMININE"
                return CharacterIdentity(
                    canonical_id=clean_id,
                    true_gender=t_g,
                    discourse_states=[],
                    entity_category=EntityCategory.ANTHROPONYM,
                    declension_paradigm=self.get_declension_paradigm(clean_id),
                    base_canonical_id=clean_id
                )

            # Check if canonical_id itself exists in characters with confirmed gender
            c_gender = self.get_character_gender(clean_id, allow_generic_nouns=False)
            if c_gender in ("MALE", "FEMALE"):
                t_g = "MASCULINE" if c_gender == "MALE" else "FEMININE"
                return CharacterIdentity(
                    canonical_id=clean_id,
                    true_gender=t_g,
                    discourse_states=[],
                    entity_category=EntityCategory.ANTHROPONYM,
                    declension_paradigm=self.get_declension_paradigm(clean_id)
                )

            return None

    def get_declension_paradigm(self, character_name: str) -> Optional[DeclensionParadigm]:
        """Zwraca lub generuje 7-przypadkowy paradygmat fleksyjny dla postaci."""
        if not character_name:
            return None
        clean_name = character_name.strip()
        cat = self.get_entity_category(clean_name)

        with self._lock:
            # Canonical glossary definitions from EpisodeProfiler take absolute priority
            glossary_target = None
            if "glossary" in self.data and isinstance(self.data["glossary"], dict):
                glossary_target = self.data["glossary"].get(character_name)
                if not glossary_target:
                    c_norm = normalize_name_nfkd(character_name).lower()
                    for gk, gv in self.data["glossary"].items():
                        if gk.lower() == character_name.lower() or normalize_name_nfkd(gk).lower() == c_norm:
                            glossary_target = gv
                            break
            if glossary_target and isinstance(glossary_target, str) and glossary_target.strip():
                clean_target = re.sub(r"\s*[\(\[].*?[\)\]]", "", glossary_target)
                clean_target = sanitize_lexical_text(re.sub(r"\s*[\(\[].*$", "", clean_target).strip())
                if clean_target and clean_target != character_name:
                    g_decl = generate_polish_name_declension(clean_target, self.get_character_gender(character_name))
                    if g_decl and "M" in g_decl:
                        return DeclensionParadigm.from_dict(g_decl, entity_category=cat)

        if is_complex_description(clean_name) or cat != EntityCategory.ANTHROPONYM:
            return DeclensionParadigm.from_dict(
                {"M": clean_name, "D": clean_name, "C": clean_name, "B": clean_name, "N": clean_name, "Ms": clean_name, "W": clean_name},
                entity_category=cat
            )

        with self._lock:
            decl = self.data.get("declensions", {}).get(character_name)
            if not decl:
                c_norm = normalize_name_nfkd(character_name).lower()
                for k, v in self.data.get("declensions", {}).items():
                    if k.lower() == character_name.lower() or normalize_name_nfkd(k).lower() == c_norm:
                        decl = v
                        break
            if decl and isinstance(decl, dict) and "M" in decl:
                d_copy = dict(decl)
                c_name = character_name.strip()
                # Sanityzacja stwardniałych końcówek wołacza/miejscownika (-tzie -> -tzu, -cie -> -cu)
                c_low = c_name.lower()
                last_2 = c_low[-2:] if len(c_low) >= 2 else ""
                last_1 = c_low[-1:] if len(c_low) >= 1 else ""
                if last_2 in ("tz", "dz", "cz", "sz", "rz", "sh", "ch", "th") or last_1 in ("c", "ż", "k", "g", "j", "l", "y", "x"):
                    if d_copy.get("W", "").lower().endswith("ie") and not d_copy.get("W", "").lower().endswith("u"):
                        d_copy["W"] = c_name + "u" if not c_low.endswith(("tz", "c")) else (c_name[:-2] + "tzu" if c_low.endswith("tz") else c_name[:-1] + "cu")
                    if d_copy.get("Ms", "").lower().endswith("ie") and not d_copy.get("Ms", "").lower().endswith("u"):
                        d_copy["Ms"] = c_name + "u" if not c_low.endswith(("tz", "c")) else (c_name[:-2] + "tzu" if c_low.endswith("tz") else c_name[:-1] + "cu")
                elif c_low.endswith("tz"):
                    if d_copy.get("W", "").lower().endswith("tzie"):
                        d_copy["W"] = c_name[:-2] + "tzu"
                    if d_copy.get("Ms", "").lower().endswith("tzie"):
                        d_copy["Ms"] = c_name[:-2] + "tzu"
                elif c_low.endswith("c"):
                    if d_copy.get("W", "").lower().endswith("cie"):
                        d_copy["W"] = c_name[:-1] + "cu"
                    if d_copy.get("Ms", "").lower().endswith("cie"):
                        d_copy["Ms"] = c_name[:-1] + "cu"
                return DeclensionParadigm.from_dict(d_copy, entity_category=cat)

            gender = self.get_character_gender(character_name)
            generated = generate_polish_name_declension(character_name, gender)
            if generated and "M" in generated:
                return DeclensionParadigm.from_dict(generated, entity_category=cat)
            return None

    def register_epistemic_rupture(
        self,
        canonical_id: str,
        episode_index: int,
        new_gender: Optional[str] = None,
        anaphora_score: Optional[int] = None,
        prev_anaphora_score: Optional[int] = None,
        delta_score_en: Optional[int] = None,
        f0_hz: Optional[float] = None
    ) -> bool:
        """Rejestruje dekonspirację (EP_RUPTURE) w tożsamości postaci w SeriesBible."""
        ident = self.get_character_identity(canonical_id)
        if not ident:
            c_gen = self.get_character_gender(canonical_id, allow_generic_nouns=False)
            t_gen = "MASCULINE" if c_gen == "MALE" else ("FEMININE" if c_gen == "FEMALE" else "MASCULINE")
            ident = CharacterIdentity(
                canonical_id=canonical_id,
                true_gender=t_gen,
                discourse_states=[]
            )
        res = ident.register_epistemic_rupture(
            episode_index=episode_index,
            new_gender=new_gender,
            anaphora_score=anaphora_score,
            prev_anaphora_score=prev_anaphora_score,
            delta_score_en=delta_score_en,
            f0_hz=f0_hz
        )
        self.register_character_identity(ident)
        return res

    def evaluate_anaphora_rupture(
        self,
        canonical_id: str,
        anaphora_score: int,
        episode_index: int,
        prev_anaphora_score: Optional[int] = None,
        delta_score_en: Optional[int] = None,
        f0_hz: Optional[float] = None
    ) -> bool:
        """Wyzwalanie dekonspiracji postaci w SeriesBible na podstawie anaforyki (Delta Score_EN lub |Score| >= 8)."""
        ident = self.get_character_identity(canonical_id)
        if not ident:
            return False
        res = ident.evaluate_anaphora_rupture(
            anaphora_score=anaphora_score,
            episode_index=episode_index,
            prev_anaphora_score=prev_anaphora_score,
            delta_score_en=delta_score_en,
            f0_hz=f0_hz
        )
        if res:
            self.register_character_identity(ident)
        return res

    def classify_entity(
        self,
        name: str,
        context: Optional[str] = None,
        is_speaking_actor: bool = False
    ) -> EntityCategory:
        """Klasyfikuje encję do kategorii ontologicznej (ANTHROPONYM | TOPONYM | CHREMATONYM)."""
        cat = classify_entity_category(name, context=context, is_speaking_actor=is_speaking_actor, series_bible=self)
        if cat in (EntityCategory.TOPONYM, EntityCategory.CHREMATONYM) and not is_speaking_actor:
            self.register_entity_category(name, cat)
        return cat

    def get_entity_category(
        self,
        name: str,
        context: Optional[str] = None,
        is_speaking_actor: bool = False
    ) -> EntityCategory:
        """Pobiera kategorię ontologiczną encji."""
        return self.classify_entity(name, context=context, is_speaking_actor=is_speaking_actor)

    def register_entity_category(self, name: str, category: Union[EntityCategory, str]) -> None:
        """Rejestruje kategorię ontologiczną encji w bazie wiedzy."""
        cat_enum = EntityCategory(category) if isinstance(category, str) else category
        with self._lock:
            if "entity_categories" not in self.data:
                self.data["entity_categories"] = {}
            self.data["entity_categories"][name.strip()] = cat_enum.value

    def register_sparse_dialogue_character(
        self,
        character_name: str,
        line_count: int = 1,
        f0_hz: Optional[float] = None,
        has_anaphora: bool = False
    ) -> None:
        """
        Sparse-Dialogue Protocol:
        Postać epizodyczna (1-2 kwestie w tle) bez twardych dowodów anaforycznych i z F0 > 135 Hz
        otrzymuje status grammatical_gender = 'NEUTRAL', confidence = 0.50, is_transient = True.
        Brak blokady P0 otwiera postać na leniwą promocję w kolejnych odcinkach.
        """
        if not character_name:
            return
        with self._lock:
            if line_count <= 2 and not has_anaphora and (f0_hz is None or f0_hz > 135.0):
                entry = {
                    "gender": "NEUTRAL",
                    "confidence": 0.50,
                    "is_transient": True,
                    "has_verified_gender": False,
                    "description": "Postać epizodyczna (sparse dialogue / tło) - status NEUTRAL, brak blokady P0"
                }
                self.data.setdefault("characters", {})[character_name] = entry
                return entry
    def _resolve_bible_path(self) -> Path:
        exact = self.storage_dir / f"{self.slug}_bible.json"
        if exact.exists():
            return exact
        for f in self.storage_dir.glob("*_bible.json"):
            if f.name.lower() == f"{self.slug.lower()}_bible.json":
                return f
        from metadata import strip_season_suffix
        stripped_self = strip_season_suffix(self.anime_title)
        if stripped_self:
            stripped_slug = clean_anime_slug(stripped_self)
            stripped_exact = self.storage_dir / f"{stripped_slug}_bible.json"
            if stripped_exact.exists():
                return stripped_exact
            for f in self.storage_dir.glob("*_bible.json"):
                if f.name.lower() == f"{stripped_slug.lower()}_bible.json":
                    return f
        for f in self.storage_dir.glob("*_bible.json"):
            base_cand = f.stem[:-6] if f.stem.endswith("_bible") else f.stem
            cand_title = base_cand.replace("_", " ")
            cand_stripped = strip_season_suffix(cand_title)
            if cand_stripped and clean_anime_slug(cand_stripped).lower() == self.slug.lower():
                return f
        return exact

    def load(self):
        """Loads existing Series Bible from disk (Thread-Safe)."""
        with self._lock:
            if not self.file_path.exists():
                self.file_path = self._resolve_bible_path()
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
                    self._sanitize_loaded_bible_in_ram()
                except Exception:
                    logger.warning("Wczytanie i integracja bazy nadrzędnej zakończona wyjątkiem", exc_info=True)

            # Auto-integrate verified Fansub Canon Lexicon from fansub_miner (0.00 PLN)
            try:
                fansub_lex = None
                if self.anime_title and self.anime_title != "Nieznana Seria" and not self.anime_title.lower().startswith("test") and getattr(self, "db_path", None) != ":memory:":
                    from fansub_miner import load_fansub_lexicon
                    fansub_lex = load_fansub_lexicon(self.anime_title, base_dir=getattr(self, "storage_dir", None))
                if fansub_lex and "terms" in fansub_lex:
                    if "fansub_canon" not in self.data:
                        self.data["fansub_canon"] = {}
                    self.data["fansub_canon"].update(fansub_lex["terms"])
                    if "glossary" not in self.data:
                        self.data["glossary"] = {}
                    for t_key, t_val in fansub_lex["terms"].items():
                        if isinstance(t_val, dict) and "canonical_pl" in t_val:
                            en_keys = t_val.get("en", [t_key])
                            for ek in en_keys:
                                if ek not in self.data["glossary"]:
                                    self.data["glossary"][ek] = t_val["canonical_pl"]
            except Exception:
                logger.warning("Integracja leksykonu fansubberskiego zakończona wyjątkiem", exc_info=True)

            self._sanitize_loaded_bible_in_ram()

    def _sanitize_bible_integrity(self):
        """
        Self-healing relational and biological gender consistency audit.
        Guards against poisoned entries where female characters (empresses, daughters, wives)
        were accidentally marked as male or inflected with masculine endings.
        """
        if not hasattr(self, "data") or "characters" not in self.data:
            return

        FEMALE_TITLES = {"cesarzowa", "chatun", "małżonka", "żona", "córka", "matka", "księżniczka", "królowa", "lady", "kobieta", "dziewczyna", "dziewczynka", "kadetka", "siostra", "mistrzyni", "czarodziejka", "kapłanka"}

        # 1. Collect female names from relationships or explicit notes
        confirmed_females = set()
        for rel_name, rel_desc in list(self.data.get("relationships", {}).items()):
            r_lower = str(rel_desc).lower()
            if "->" in rel_name:
                parts = [p.strip() for p in rel_name.split("->")]
                spk = parts[0]
                rec = parts[1] if len(parts) > 1 else ""
                if any(w in r_lower for w in ["córka ->", "żona ->", "pasierbica ->", "cesarzowa ->", "kadetka ->", "mistrzyni ->"]):
                    confirmed_females.add(spk)
                if any(w in r_lower for w in ["-> córka", "-> żona", "-> matka", "-> macocha", "-> cesarzowa", "-> kadetka", "-> mistrzyni"]) or "[kobieta (adresat" in r_lower:
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
                    clean_desc = re.sub(r"\[MĘŻCZYZNA \(Adresat(?:ka|ce|ki|ek|om|ami|ach|em|owi)?\)[^\]]*\]", "[KOBIETA (Adresat) - W 2. os. lp. 'ty' wymóg form żeńskich: byłaś / zrobiłaś / jesteś pewna]", clean_desc, flags=re.IGNORECASE)
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

        # 2b. Check characters table for poisoned male characters (e.g. historical samurai, kuge, generals, lords)
        MALE_TITLES = {"samuraj", "generał", "buke", "kuge", "wasal", "lord", "pan ", "wojownik", "rycerz", "król", "książę", "cesarz", "wielki radca"}
        confirmed_males = set()
        for rel_name, rel_desc in list(self.data.get("relationships", {}).items()):
            r_str = str(rel_desc)
            r_lower = r_str.lower()
            if "->" in rel_name:
                parts = [p.strip() for p in rel_name.split("->")]
                spk = parts[0]
                rec = parts[1] if len(parts) > 1 else ""
                rec_is_female = (
                    "[kobieta (adresat" in r_lower
                    or rec in confirmed_females
                    or any(t in r_lower for t in FEMALE_TITLES)
                )
                if not rec_is_female:
                    if re.search(r"\bpanie\s+[A-ZĄĆĘŁŃÓŚŹŻ]", r_str) or any(w in r_lower for w in ["ojciec", "syn", "brat", "panicz", "bocchan"]) or "[mężczyzna (adresat" in r_lower:
                        confirmed_males.add(rec)
                if any(w in r_lower for w in ["syn ->", "ojciec ->", "brat ->", "pan ->"]):
                    if not (spk in confirmed_females or "[kobieta (adresat" in r_lower):
                        confirmed_males.add(spk)
                # Auto-repair poisoned [KOBIETA (Adresat)] in relationships if recipient is confirmed male or addressed with 'panie'
                rec_tokens = extract_clean_speaker_name(rec).lower().split()
                if (re.search(r"\bpanie\s+[A-ZĄĆĘŁŃÓŚŹŻ]", r_str) or (rec.lower() in CANONICAL_MALE_NAMES) or any(t in CANONICAL_MALE_NAMES for t in rec_tokens)) and not rec_is_female:
                    if "[KOBIETA (Adresat" in r_str or "[kobieta (adresat" in r_lower:
                        fixed_rel = re.sub(r"\[KOBIETA \(Adresat(?:ka|ce|ki|ek|om|ami|ach|em|owi)?\)[^\]]*\]", "[MĘŻCZYZNA (Adresat) - W 2. os. lp. 'ty' wymóg form męskich: byłeś / zrobiłeś / jesteś pewien]", r_str, flags=re.IGNORECASE)
                        self.data["relationships"][rel_name] = fixed_rel
                        if rel_name in self.data.get("characters", {}):
                            self.data["characters"][rel_name]["description"] = fixed_rel

        for char_name, c_val in list(self.data.get("characters", {}).items()):
            if "->" in char_name:
                continue
            desc = c_val.get("description", "") if isinstance(c_val, dict) else str(c_val)
            d_lower = desc.lower()
            c_tokens = extract_clean_speaker_name(char_name).lower().split()

            is_female_cand = (
                (char_name in confirmed_females)
                or any(t in d_lower for t in FEMALE_TITLES)
                or "[kobieta (adresat" in d_lower
                or (isinstance(c_val, dict) and str(c_val.get("gender", "")).upper() in ("FEMALE", "KOBIETA"))
            )
            is_confirmed_male = (
                (char_name in confirmed_males)
                or any(t in d_lower for t in MALE_TITLES)
                or (char_name.lower() in CANONICAL_MALE_NAMES)
                or any(t in CANONICAL_MALE_NAMES for t in c_tokens)
                or has_japanese_male_name_suffix(char_name)
                or any(has_japanese_male_name_suffix(t) for t in c_tokens)
                or is_official_or_court_consonant_name(char_name, series_bible=self)
                or any(is_official_or_court_consonant_name(t, series_bible=self) for t in c_tokens)
                or bool(re.search(r"(?:'s\s+|\b)(?:kid|son|boy|bro|brother|brat|syn|chłopak|chłopiec|captain|kapitan)\b|^young\s+", char_name.lower()))
            ) and not is_female_cand

            if is_confirmed_male:
                repaired_from_female = False
                # If marked as female due to past "pani" substring collision in "panie", auto-repair to male
                if any(f in d_lower for f in ["kobieta", "żeńsk", "female", "kobieta (adresat"]) and not any(f in d_lower for f in ["córka", "żona", "matka", "księżniczka", "kadetka", "dziewczyna", "dziewczynka", "siostra", "mistrzyni", "czarodziejka"]):
                    clean_desc = re.sub(r"\bkobieta\b", "MĘŻCZYZNA", desc, flags=re.IGNORECASE)
                    clean_desc = re.sub(r"\[KOBIETA \(Adresat(?:ka|ce|ki|ek|om|ami|ach|em|owi)?\)[^\]]*\]", "[MĘŻCZYZNA (Adresat) - W 2. os. lp. 'ty' wymóg form męskich: byłeś / zrobiłeś / jesteś pewien]", clean_desc, flags=re.IGNORECASE)
                    if isinstance(c_val, dict):
                        c_val["description"] = clean_desc
                    else:
                        self.data["characters"][char_name] = {"description": clean_desc}
                    repaired_from_female = True
                elif "postać" in d_lower and not any(m in d_lower for m in ["mężczyzna", "male", "chłopak"]):
                    clean_desc = f"{desc} [MĘŻCZYZNA]"
                    if isinstance(c_val, dict):
                        c_val["description"] = clean_desc
                    else:
                        self.data["characters"][char_name] = {"description": clean_desc}

                if isinstance(c_val, dict):
                    c_val["gender"] = "MALE"

                # Regenerate declensions for male character ONLY IF repaired from female
                if repaired_from_female and "declensions" in self.data:
                    if char_name in self.data["declensions"]:
                        self.data["declensions"][char_name] = generate_polish_name_declension(char_name, "MALE")
                        self.data["declensions"][char_name]["gender"] = "MALE"

        # Ensure any declension with a female or male character has gender aligned
        if "declensions" in self.data:
            for d_name, d_val in list(self.data["declensions"].items()):
                if isinstance(d_val, dict):
                    c_info = self.data.get("characters", {}).get(d_name)
                    if c_info:
                        c_desc = c_info.get("description", "") if isinstance(c_info, dict) else str(c_info)
                        cd_lower = c_desc.lower()
                        d_tokens = extract_clean_speaker_name(d_name).lower().split()
                        if any(t in cd_lower for t in FEMALE_TITLES) or "kobieta" in cd_lower or "female" in cd_lower:
                            d_val["gender"] = "FEMALE"
                        elif any(t in cd_lower for t in ["mężczyzna", "male", "chłopak"]) or (d_name.lower() in CANONICAL_MALE_NAMES) or any(t in CANONICAL_MALE_NAMES for t in d_tokens):
                            d_val["gender"] = "MALE"


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

        # 3b. Register verified characters into ontology category ANTHROPONYM
        for valid_char in list(self.data.get("characters", {}).keys()):
            if isinstance(valid_char, str) and "->" not in valid_char:
                self.register_entity_category(valid_char, EntityCategory.ANTHROPONYM)

        # 4. Enforce dual female forms for female-only relationships
        if "relationships" in self.data and isinstance(self.data["relationships"], dict):
            for rk, rv in list(self.data["relationships"].items()):
                rv_str = str(rv)
                # Auto-detect female-only relationships and enforce dual forms
                if "->" in rk:
                    parts = [p.strip() for p in rk.split("->")]
                    spk_name = parts[0]
                    rec_name = parts[1] if len(parts) > 1 else ""
                    if self.is_female_pair(spk_name, rec_name) or (spk_name in confirmed_females and rec_name in confirmed_females):
                        if "PARA DWÓCH KOBIET" not in rv_str:
                            rv_str += " [PARA DWÓCH KOBIET: w odniesieniu do obu kobiet stosuj wyłącznie formy żeńskie 'obie / dla was obu / was obie', wykluczona forma 'oboje' (Filar CLXXIII)]"

                self.data["relationships"][rk] = rv_str

    def _sanitize_loaded_bible_in_ram(self):
        """
        Samolecząca walidacja i sanitacja bazy wiedzy w RAM (0.00 PLN):
        a) Scala zduplikowane rekordy postaci różniące się wyłącznie znakami diakrytycznymi/umlautami
           (używając normalize_ascii_diacritics z metadata.py), zachowując najwyższy priorytet weryfikacji (P0).
        b) Odfiltrowuje ze słownika postaci ludzkich (characters) wszelkie wpisy zaklasyfikowane jako
           EntityCategory.TOPONYM, EntityCategory.CHREMATONYM lub pokrywające się z POLISH_COMMON_NOUN_HOMONYMS.
        c) Wycofuje niezweryfikowane etykiety FEMALE powstałe z niskiej pewności wektorów
           (formalne watakushi lub wysokie F0 w retrospekcjach).
        """
        with self._lock:
            if not hasattr(self, "data") or not isinstance(self.data, dict):
                return

            if "characters" not in self.data or not isinstance(self.data["characters"], dict):
                return

            if not isinstance(self.data["characters"], CharacterRegistryDict):
                self.data["characters"] = CharacterRegistryDict(self.data["characters"], bible_data=self.data)
            else:
                self.data["characters"].bible_data = self.data

            # -------------------------------------------------------------
            # b) Odseparowanie relacji skierowanych (X -> Y) do dedykowanej struktury relations
            # -------------------------------------------------------------
            self.data.setdefault("relations", {})
            self.data.setdefault("relationships", {})
            for char_k in list(self.data["characters"].keys()):
                if "->" in char_k:
                    rel_val = self.data["characters"][char_k]
                    desc_rel = rel_val.get("description", "") if isinstance(rel_val, dict) else str(rel_val)
                    clean_rel = self._sanitize_character_entry(char_k, desc_rel)
                    self.data["relations"][char_k] = clean_rel
                    self.data["relationships"][char_k] = clean_rel
                    del self.data["characters"][char_k]

            # -------------------------------------------------------------
            # 0-purge: Usuwanie nie-antroponimów i skażonych wpisów (Operacja H5)
            # -------------------------------------------------------------
            non_anthro_suffixes = ("heart", "thought", "thoughts", "voice", "internal", "sign")
            glossary_set = set()
            if "glossary" in self.data and isinstance(self.data["glossary"], dict):
                for gk, gv in self.data["glossary"].items():
                    glossary_set.add(str(gk).strip().lower())
                    if isinstance(gv, str):
                        glossary_set.add(gv.strip().lower())

            for d_name in list(self.data.get("declensions", {}).keys()):
                d_clean = extract_clean_speaker_name(str(d_name)).strip()
                d_low = d_clean.lower()
                is_invalid = (
                    d_low in COLLECTIVE_LABELS
                    or (len(d_clean.split()) == 1 and d_clean.islower())
                    or any(c in d_clean for c in ("?", "!"))
                    or any(d_low.endswith(suf) for suf in non_anthro_suffixes)
                )
                is_glossary_only = False
                if d_low in glossary_set:
                    c_entry = self.data.get("characters", {}).get(d_name) or self.data.get("characters", {}).get(d_clean)
                    if not c_entry:
                        is_glossary_only = True
                    elif isinstance(c_entry, dict) and c_entry.get("entity_category") in (EntityCategory.TOPONYM.value, EntityCategory.CHREMATONYM.value, "TOPONYM", "CHREMATONYM"):
                        is_glossary_only = True

                if is_invalid or is_glossary_only:
                    del self.data["declensions"][d_name]

            for c_name in list(self.data.get("characters", {}).keys()):
                if "->" in c_name:
                    continue
                c_clean = extract_clean_speaker_name(str(c_name)).strip()
                c_low = c_clean.lower()
                is_invalid = (
                    c_low in COLLECTIVE_LABELS
                    or (len(c_clean.split()) == 1 and c_clean.islower())
                    or any(c in c_clean for c in ("?", "!"))
                    or any(c_low.endswith(suf) for suf in non_anthro_suffixes)
                )
                if is_invalid:
                    del self.data["characters"][c_name]
                    if "declensions" in self.data and c_name in self.data["declensions"]:
                        del self.data["declensions"][c_name]
                    if "entity_categories" in self.data and c_name in self.data["entity_categories"]:
                        del self.data["entity_categories"][c_name]

            if "entity_categories" in self.data and isinstance(self.data["entity_categories"], dict):
                for e_name in list(self.data["entity_categories"].keys()):
                    e_clean = extract_clean_speaker_name(str(e_name)).strip()
                    e_low = e_clean.lower()
                    if e_low in COLLECTIVE_LABELS or (len(e_clean.split()) == 1 and e_clean.islower()) or any(c in e_clean for c in ("?", "!")):
                        del self.data["entity_categories"][e_name]

            # -------------------------------------------------------------
            # 0. Normalizacja tagów technicznych i ekstrakcja płci P0 (normalize_actor_tag)
            # -------------------------------------------------------------
            for char_k in list(self.data["characters"].keys()):
                if "->" in char_k:
                    continue
                c_val = self.data["characters"][char_k]
                clean_name, tag_gender = normalize_actor_tag(str(char_k))
                clean_name = clean_name.strip()
                target_key = char_k
                if clean_name and clean_name != char_k:
                    # Przeniesienie danych pod czyste imię (usunięcie nawiasów technicznych np. (S1E9), (M), (F))
                    existing = self.data["characters"].get(clean_name)
                    if existing and isinstance(existing, dict) and isinstance(c_val, dict):
                        target_val = copy.deepcopy(existing)
                        for k_sub, v_sub in c_val.items():
                            if k_sub not in target_val or not target_val[k_sub]:
                                target_val[k_sub] = v_sub
                    else:
                        target_val = c_val
                    del self.data["characters"][char_k]
                    self.data["characters"][clean_name] = target_val
                    if "declensions" in self.data and isinstance(self.data["declensions"], dict):
                        if char_k in self.data["declensions"]:
                            if clean_name not in self.data["declensions"]:
                                self.data["declensions"][clean_name] = self.data["declensions"][char_k]
                            del self.data["declensions"][char_k]
                    c_val = target_val
                    target_key = clean_name

                if tag_gender in ("MALE", "FEMALE"):
                    if isinstance(c_val, dict):
                        c_val["gender"] = tag_gender
                        c_val["grammatical_gender"] = "MASCULINE" if tag_gender == "MALE" else "FEMININE"
                        c_val["has_verified_gender"] = True
                        c_val["confidence"] = 1.0
                        c_val["priority"] = "P0"
                        desc = c_val.get("description", "")
                        if tag_gender == "MALE":
                            clean_desc = re.sub(r"\b(?:kobieta|żeńsk\w*|female)\b", "MĘŻCZYZNA", desc, flags=re.IGNORECASE)
                            clean_desc = re.sub(r"\[KOBIETA \(Adresat[^\]]*\]", "[MĘŻCZYZNA (Adresat) - W 2. os. lp. 'ty' wymóg form męskich: byłeś / zrobiłeś / jesteś pewien]", clean_desc, flags=re.IGNORECASE)
                        else:
                            clean_desc = re.sub(r"\b(?:mężczyzna|męsk\w*|male)\b", "KOBIETA", desc, flags=re.IGNORECASE)
                            clean_desc = re.sub(r"\[MĘŻCZYZNA \(Adresat[^\]]*\]", "[KOBIETA (Adresat) - W 2. os. lp. 'ty' wymóg form żeńskich: byłaś / zrobiłaś / jesteś pewna]", clean_desc, flags=re.IGNORECASE)
                        c_val["description"] = clean_desc
                    else:
                        desc_str = str(c_val)
                        if tag_gender == "MALE":
                            desc_str = re.sub(r"\b(?:kobieta|żeńsk\w*|female)\b", "MĘŻCZYZNA", desc_str, flags=re.IGNORECASE)
                        else:
                            desc_str = re.sub(r"\b(?:mężczyzna|męsk\w*|male)\b", "KOBIETA", desc_str, flags=re.IGNORECASE)
                        self.data["characters"][target_key] = {
                            "description": desc_str,
                            "gender": tag_gender,
                            "grammatical_gender": "MASCULINE" if tag_gender == "MALE" else "FEMININE",
                            "has_verified_gender": True,
                            "confidence": 1.0,
                            "priority": "P0"
                        }
                    if "declensions" in self.data and isinstance(self.data["declensions"], dict):
                        new_gen_decl = generate_polish_name_declension(target_key, tag_gender)
                        if new_gen_decl:
                            new_gen_decl["gender"] = tag_gender
                            self.data["declensions"][target_key] = new_gen_decl

            # Reconstruct missing ANTHROPONYM characters from declensions and entity_categories
            if "declensions" in self.data and isinstance(self.data["declensions"], dict):
                for d_name, d_val in list(self.data["declensions"].items()):
                    if "->" not in d_name and d_name not in self.data["characters"]:
                        cat = self.get_entity_category(d_name)
                        if cat == EntityCategory.ANTHROPONYM or (isinstance(d_val, dict) and d_val.get("gender") in ("MALE", "FEMALE")):
                            g = d_val.get("gender") if isinstance(d_val, dict) else None
                            if g in ("MALE", "FEMALE"):
                                self.data["characters"][d_name] = {
                                    "gender": g,
                                    "grammatical_gender": "MASCULINE" if g == "MALE" else "FEMININE",
                                    "description": f"{'kobieta' if g == 'FEMALE' else 'mężczyzna'} (postać)",
                                    "has_verified_gender": True,
                                    "confidence": 0.95,
                                    "priority": "P0"
                                }

            # Reconstruct missing ANTHROPONYM characters from relationships / relations
            rels = dict(self.data.get("relationships", {}))
            rels.update(self.data.get("relations", {}))
            for rel_k, rel_desc in rels.items():
                if "->" in rel_k:
                    parts = [p.strip() for p in rel_k.split("->")]
                    if len(parts) >= 2:
                        desc_str = str(rel_desc.get("description", "") if isinstance(rel_desc, dict) else rel_desc)
                        for idx_p, cand_part in enumerate(parts):
                            is_tgt = (idx_p == len(parts) - 1)
                            cand_clean = extract_clean_speaker_name(cand_part).strip()
                            if "/" not in cand_clean and cand_clean and cand_clean not in self.data["characters"]:
                                norm_cand = normalize_name_nfkd(cand_clean).lower()
                                already_known = False
                                for k, v in self.data["characters"].items():
                                    if "->" in k:
                                        continue
                                    k_low = k.lower()
                                    if k_low == cand_clean.lower() or normalize_name_nfkd(k).lower() == norm_cand:
                                        already_known = True
                                        break
                                    if isinstance(v, dict):
                                        aliases = [a.lower() for a in v.get("aliases", [])]
                                        if cand_clean.lower() in aliases or norm_cand in aliases:
                                            already_known = True
                                            break
                                    k_tokens = [tok.lower() for tok in k.split()]
                                    if len(k_tokens) > 1 and (cand_clean.lower() in k_tokens or norm_cand in k_tokens):
                                        already_known = True
                                        break
                                if already_known:
                                    continue

                                p_details = desc_str
                                m_role = re.search(r"\(([^)]+)\)", desc_str)
                                if m_role:
                                    rc = m_role.group(1).strip()
                                    for sep in ["->", "/", " i "]:
                                        if sep in rc:
                                            rc_parts = [r.strip() for r in rc.split(sep)]
                                            if len(rc_parts) == len(parts):
                                                p_details = rc_parts[idx_p]
                                                break
                                            elif len(rc_parts) >= 2 and idx_p == 0:
                                                p_details = rc_parts[0]
                                                break
                                            elif len(rc_parts) >= 2 and is_tgt:
                                                p_details = rc_parts[-1]
                                                break

                                if is_tgt:
                                    has_f = (re.search(r"\[KOBIETA\s+\(Adresat[^\]]*\]", desc_str, re.IGNORECASE) is not None) or is_female_role_text(cand_clean) or is_female_role_text(p_details) or any(w in desc_str.lower() for w in ["matka", "żona", "córka", "kobieta", "pani"])
                                    has_m = (re.search(r"\[MĘŻCZYZNA\s+\(Adresat[^\]]*\]", desc_str, re.IGNORECASE) is not None) or is_male_role_text(cand_clean) or is_male_role_text(p_details) or any(w in desc_str.lower() for w in ["ojciec", "mąż", "syn", "mężczyzna", "pan"])
                                else:
                                    spk_desc = re.sub(r"\[[^\]]*\bAdresat[^\]]*\]", "", p_details, flags=re.IGNORECASE)
                                    has_f = is_female_role_text(cand_clean) or is_female_role_text(spk_desc) or any(w in spk_desc.lower() for w in ["matka", "żona", "córka", "kobieta", "pani"])
                                    has_m = is_male_role_text(cand_clean) or is_male_role_text(spk_desc) or any(w in spk_desc.lower() for w in ["ojciec", "mąż", "syn", "mężczyzna", "pan"])

                                if has_f and not has_m:
                                    self.data["characters"][cand_clean] = {
                                        "gender": "FEMALE",
                                        "grammatical_gender": "FEMININE",
                                        "description": "kobieta (postać)",
                                        "has_verified_gender": True,
                                        "confidence": 0.95,
                                        "priority": "P0",
                                        "aliases": [cand_clean],
                                        "entity_category": EntityCategory.ANTHROPONYM.value
                                    }
                                elif has_m and not has_f:
                                    self.data["characters"][cand_clean] = {
                                        "gender": "MALE",
                                        "grammatical_gender": "MASCULINE",
                                        "description": "mężczyzna (postać)",
                                        "has_verified_gender": True,
                                        "confidence": 0.95,
                                        "priority": "P0",
                                        "aliases": [cand_clean],
                                        "entity_category": EntityCategory.ANTHROPONYM.value
                                    }

            # -------------------------------------------------------------
            # 0b. Promocja płci strukturalnej z description/declensions do pól P0 (Standard 7.1)
            # -------------------------------------------------------------
            for char_k in list(self.data["characters"].keys()):
                if "->" in char_k:
                    continue
                c_val = self.data["characters"][char_k]
                if isinstance(c_val, dict):
                    curr_g = str(c_val.get("gender") or "").strip().upper()
                    desc = str(c_val.get("description", ""))

                    # 1. Sprawdzenie jawnych znaczników i dyrektyw w description (nadrzędne wobec declensions)
                    if not curr_g or curr_g == "UNKNOWN":
                        m_tag = re.search(r"\[(KOBIETA|MĘŻCZYZNA)\s+\(Adresat(?:ka|ce|ki|ek|om|ami|ach|em|owi)?\)", desc, re.IGNORECASE)
                        if m_tag:
                            promoted = "FEMALE" if m_tag.group(1).upper() == "KOBIETA" else "MALE"
                            curr_g = promoted
                            c_val["gender"] = promoted
                            c_val["grammatical_gender"] = "FEMININE" if promoted == "FEMALE" else "MASCULINE"
                            c_val["has_verified_gender"] = True
                            c_val["confidence"] = 0.95
                            c_val["priority"] = "P0"
                        elif re.search(r"\b(?:kobieta|female)\b", desc, re.IGNORECASE) and not re.search(r"\b(?:mężczyzna|male)\b", desc, re.IGNORECASE):
                            curr_g = "FEMALE"
                            c_val["gender"] = "FEMALE"
                            c_val["grammatical_gender"] = "FEMININE"
                            c_val["has_verified_gender"] = True
                            c_val["confidence"] = 0.95
                            c_val["priority"] = "P0"
                        elif re.search(r"\b(?:mężczyzna|male)\b", desc, re.IGNORECASE) and not re.search(r"\b(?:kobieta|female)\b", desc, re.IGNORECASE):
                            curr_g = "MALE"
                            c_val["gender"] = "MALE"
                            c_val["grammatical_gender"] = "MASCULINE"
                            c_val["has_verified_gender"] = True
                            c_val["confidence"] = 0.95
                            c_val["priority"] = "P0"

                    # 2. Fallback do declensions tylko jeśli description nie rozstrzyga
                    if (not curr_g or curr_g == "UNKNOWN") and "declensions" in self.data and isinstance(self.data["declensions"], dict):
                        d_entry = self.data["declensions"].get(char_k)
                        if isinstance(d_entry, dict) and d_entry.get("gender"):
                            d_g = str(d_entry["gender"]).strip().upper()
                            if d_g in ("MALE", "FEMALE"):
                                curr_g = d_g
                                c_val["gender"] = d_g
                                c_val["grammatical_gender"] = "MASCULINE" if d_g == "MALE" else "FEMININE"
                                c_val["has_verified_gender"] = True
                                c_val["confidence"] = 0.95
                                c_val["priority"] = "P0"

                    if c_val.get("gender") == "FEMALE":
                        c_val["grammatical_gender"] = "FEMININE"
                        if "description" in c_val:
                            # Tylko jeśli w description nie ma jawnego nakazu form męskich
                            if not re.search(r"\b(?:nakaz form męskich|wymóg form męskich)\b", str(c_val["description"]), re.IGNORECASE):
                                c_val["description"] = re.sub(r"\bMĘŻCZYZNA\b", "KOBIETA", str(c_val["description"]))

            # -------------------------------------------------------------
            # 0c. Ochrona leksemów żeńskich i propagacja zweryfikowanej płci P0 (Operacje H2 i H5)
            # -------------------------------------------------------------
            for c_k, c_v in list(self.data["characters"].items()):
                if "->" in c_k or not isinstance(c_v, dict):
                    continue
                c_clean = extract_clean_speaker_name(c_k).strip()
                c_lower = c_clean.lower()
                first_tok = c_lower.split()[0] if c_lower.split() else ""
                is_fem = (
                    c_lower in FEMALE_LEXICON_NAMES
                    or (first_tok and first_tok in FEMALE_LEXICON_NAMES and first_tok not in CANONICAL_MALE_NAMES_ON_A)
                    or any(t.lower() in FEMALE_LEXICON_NAMES for t in c_clean.split() if t.lower() not in CANONICAL_MALE_NAMES_ON_A)
                )
                if is_fem:
                    c_v["gender"] = "FEMALE"
                    c_v["grammatical_gender"] = "FEMININE"
                    c_v["has_verified_gender"] = True
                    c_v["confidence"] = max(float(c_v.get("confidence", 0.0)), 0.95)
                    c_v["priority"] = "P0"
                    if "description" in c_v:
                        c_v["description"] = re.sub(r"\bMĘŻCZYZNA\b", "KOBIETA", str(c_v["description"]))
                        c_v["description"] = re.sub(r"\[MĘŻCZYZNA \(Adresat[^\]]*\]", "[KOBIETA (Adresat) - W 2. os. lp. 'ty' wymóg form żeńskich: byłaś / zrobiłaś / jesteś pewna]", str(c_v["description"]))
                    if "declensions" in self.data and isinstance(self.data["declensions"], dict) and c_k in self.data["declensions"]:
                        new_d = generate_polish_name_declension(c_k, "FEMALE")
                        new_d["gender"] = "FEMALE"
                        self.data["declensions"][c_k] = new_d

            # Budowa multi_token_p0 po zabezpieczeniu leksemów żeńskich
            multi_token_p0 = {}
            for c_k, c_v in list(self.data["characters"].items()):
                if "->" in c_k or not isinstance(c_v, dict):
                    continue
                c_clean = extract_clean_speaker_name(c_k).strip()
                tokens_c = c_clean.split()
                c_gen = str(c_v.get("gender") or "").upper()
                is_p0 = (c_v.get("priority") == "P0" or c_v.get("has_verified_gender") or c_v.get("confidence", 0) >= 0.90)
                if is_p0 and c_gen in ("MALE", "FEMALE"):
                    if len(tokens_c) >= 2:
                        first_name = tokens_c[0]
                        multi_token_p0[first_name.lower()] = (first_name, c_gen, c_v)
                    for al in c_v.get("aliases", []):
                        al_clean = extract_clean_speaker_name(str(al)).strip()
                        if len(al_clean.split()) == 1:
                            multi_token_p0[al_clean.lower()] = (al_clean, c_gen, c_v)

            # Dziedziczenie z rekordu dwuczłonowego P0
            for c_k, c_v in list(self.data["characters"].items()):
                if "->" in c_k or not isinstance(c_v, dict):
                    continue
                c_clean = extract_clean_speaker_name(c_k).strip()
                c_lower = c_clean.lower()
                if len(c_clean.split()) == 1 and c_lower in multi_token_p0:
                    _, parent_gen, parent_v = multi_token_p0[c_lower]
                    c_v["gender"] = parent_gen
                    c_v["grammatical_gender"] = "MASCULINE" if parent_gen == "MALE" else "FEMININE"
                    c_v["has_verified_gender"] = True
                    c_v["confidence"] = max(float(c_v.get("confidence", 0.0)), 0.95)
                    c_v["priority"] = "P0"
                    if "description" in c_v:
                        if parent_gen == "FEMALE":
                            c_v["description"] = re.sub(r"\bMĘŻCZYZNA\b", "KOBIETA", str(c_v["description"]))
                            c_v["description"] = re.sub(r"\[MĘŻCZYZNA \(Adresat[^\]]*\]", "[KOBIETA (Adresat) - W 2. os. lp. 'ty' wymóg form żeńskich: byłaś / zrobiłaś / jesteś pewna]", str(c_v["description"]))
                        else:
                            c_v["description"] = re.sub(r"\bKOBIETA\b", "MĘŻCZYZNA", str(c_v["description"]))
                            c_v["description"] = re.sub(r"\[KOBIETA \(Adresat[^\]]*\]", "[MĘŻCZYZNA (Adresat) - W 2. os. lp. 'ty' wymóg form męskich: byłeś / zrobiłeś / jesteś pewien]", str(c_v["description"]))
                    if "declensions" in self.data and isinstance(self.data["declensions"], dict) and c_k in self.data["declensions"]:
                        new_d = generate_polish_name_declension(c_k, parent_gen)
                        new_d["gender"] = parent_gen
                        self.data["declensions"][c_k] = new_d

            # -------------------------------------------------------------
            # 0d. Propagacja aliasów i płci z terminology i glossary (Operacja H2)
            # -------------------------------------------------------------
            combined_terms = {}
            if "terminology" in self.data and isinstance(self.data["terminology"], dict):
                combined_terms.update(self.data["terminology"])
            if "glossary" in self.data and isinstance(self.data["glossary"], dict):
                combined_terms.update(self.data["glossary"])

            title_female_markers = {"cesarzowa", "królowa", "księżniczka", "caryca", "pani"}
            title_male_markers = {"cesarz", "król", "książę", "car", "pan"}
            common_titles = {
                "cesarzowa", "cesarz", "królowa", "król", "księżniczka", "książę", "pani", "pan",
                "córka", "syn", "wielki", "wielka", "mistrz", "mistrzyni", "generał"
            }

            for t_key, t_val in combined_terms.items():
                val_str = str(t_val).strip()
                val_lower = val_str.lower()
                val_first_tok = val_lower.split()[0] if val_lower.split() else ""
                
                det_gender = None
                key_char = self.data["characters"].get(t_key)
                if isinstance(key_char, dict) and key_char.get("gender") in ("FEMALE", "MALE"):
                    det_gender = key_char["gender"]
                elif val_first_tok in title_female_markers:
                    det_gender = "FEMALE"
                elif val_first_tok in title_male_markers:
                    det_gender = "MALE"

                if det_gender:
                    cand_tokens = [
                        tok for tok in val_str.split()
                        if tok and tok[0].isupper()
                        and tok.lower() not in common_titles
                        and tok.lower() not in COLLECTIVE_LABELS
                        and tok.lower() not in INHERENT_FEMALE_NOUNS
                        and tok.lower() not in INHERENT_MALE_NOUNS
                    ]
                    for c_tok in cand_tokens:
                        is_pair_with_anthro = (
                            key_char is not None or val_first_tok in title_female_markers or val_first_tok in title_male_markers
                        )
                        if is_pair_with_anthro:
                            c_entry = self.data["characters"].get(c_tok)
                            aliases = list(set([c_tok, t_key]))
                            if isinstance(c_entry, dict):
                                c_entry["gender"] = det_gender
                                c_entry["grammatical_gender"] = "FEMININE" if det_gender == "FEMALE" else "MASCULINE"
                                c_entry["priority"] = "P0"
                                c_entry["has_verified_gender"] = True
                                c_entry["entity_category"] = EntityCategory.ANTHROPONYM.value
                                cur_als = set(c_entry.get("aliases", []))
                                cur_als.update(aliases)
                                c_entry["aliases"] = sorted(list(cur_als))
                            else:
                                self.data["characters"][c_tok] = {
                                    "description": f"{'kobieta' if det_gender == 'FEMALE' else 'mężczyzna'} (postać)",
                                    "gender": det_gender,
                                    "grammatical_gender": "FEMININE" if det_gender == "FEMALE" else "MASCULINE",
                                    "priority": "P0",
                                    "has_verified_gender": True,
                                    "aliases": sorted(aliases),
                                    "entity_category": EntityCategory.ANTHROPONYM.value
                                }
                            self.data.setdefault("declensions", {})
                            d_tok = generate_polish_name_declension(c_tok, det_gender)
                            d_tok["gender"] = det_gender
                            self.data["declensions"][c_tok] = d_tok

            # -------------------------------------------------------------
            # a) Scalanie zduplikowanych rekordów postaci (diakrytyki / umlauty)
            # -------------------------------------------------------------
            char_entries = list(self.data["characters"].items())
            groups: Dict[str, List[Tuple[str, Any]]] = {}
            for name, val in char_entries:
                if not name or "->" in name:
                    continue
                folded_key = normalize_ascii_diacritics(str(name)).strip().lower()
                groups.setdefault(folded_key, []).append((str(name).strip(), val))

            for folded_key, candidates in groups.items():
                if len(candidates) > 1:
                    def _score_entry(cand: Tuple[str, Any]) -> Tuple[int, float, int, int]:
                        c_name, c_val = cand
                        desc = c_val.get("description", "") if isinstance(c_val, dict) else str(c_val)
                        desc_l = desc.lower()
                        is_p0 = (
                            (isinstance(c_val, dict) and bool(c_val.get("has_verified_gender")))
                            or "zweryfikowan" in desc_l
                            or "anilist" in desc_l
                            or (isinstance(c_val, dict) and c_val.get("priority") == "P0")
                            or (isinstance(c_val, dict) and c_val.get("source") in ("anilist", "quality_gate"))
                        )
                        p0_score = 100 if is_p0 else 0
                        conf = float(c_val.get("confidence", 0.0)) if isinstance(c_val, dict) else 0.0
                        richness = len(desc)
                        has_diacritics = 1 if c_name != normalize_ascii_diacritics(c_name) else 0
                        return (p0_score, conf, richness, has_diacritics)

                    best_name, best_val = max(candidates, key=_score_entry)
                    for other_name, other_val in candidates:
                        if other_name != best_name:
                            # Merge details
                            if isinstance(best_val, dict) and isinstance(other_val, dict):
                                if not best_val.get("has_verified_gender") and other_val.get("has_verified_gender"):
                                    best_val["has_verified_gender"] = True
                                    best_val["gender"] = other_val.get("gender", best_val.get("gender"))
                                if "forms" in other_val and "forms" not in best_val:
                                    best_val["forms"] = other_val["forms"]
                            del self.data["characters"][other_name]
                            if "declensions" in self.data and isinstance(self.data["declensions"], dict):
                                if other_name in self.data["declensions"]:
                                    if best_name not in self.data["declensions"]:
                                        self.data["declensions"][best_name] = self.data["declensions"][other_name]
                                    del self.data["declensions"][other_name]

            # -------------------------------------------------------------
            # b) Odfiltrowanie TOPONYM, CHREMATONYM i POLISH_COMMON_NOUN_HOMONYMS
            # -------------------------------------------------------------
            CHREMATONYM_HEAD_WORDS: Set[str] = {
                "księga", "miecz", "ostrze", "amulet", "tarcza", "lanca", "zwój", "korona", "pierścień",
                "relikwia", "artefakt", "topór", "sztylet", "berło", "różdżka", "kostur", "łuk", "zbroja",
                "szata", "grymuar", "kryształ", "zaklęcie", "czar", "rytuał", "pieczęć", "tome",
                "sword", "blade", "amulet", "shield", "spear", "scroll", "crown", "ring", "relic",
                "artifact", "axe", "dagger", "scepter", "wand", "staff", "bow", "armor", "robe",
                "grimoire", "crystal", "spell", "seal"
            }

            # Rejestracja toponimów i chrematonimów ze słownika i plot_anchors oraz normalizacja pojedynczego wariantu (R3.4, Operacja 2B.6)
            chars_dict = self.data.get("characters", {})
            if "glossary" in self.data and isinstance(self.data["glossary"], dict):
                ent_cats = self.data.setdefault("entity_categories", {})
                for gk, gv in list(self.data["glossary"].items()):
                    if isinstance(gv, str) and "/" in gv:
                        gv = gv.split("/")[0].strip()
                        self.data["glossary"][gk] = gv
                    if gk not in chars_dict:
                        ent_cats.pop(gk, None)
                        cat_g = classify_entity_category(gk, context=str(gv), series_bible=self)
                        if cat_g == EntityCategory.ANTHROPONYM:
                            cat_g = EntityCategory.CHREMATONYM
                        ent_cats[gk] = cat_g.value
                    elif gk not in ent_cats:
                        cat_g = classify_entity_category(gk, context=str(gv), series_bible=self)
                        ent_cats[gk] = cat_g.value

            if "plot_anchors" in self.data and isinstance(self.data["plot_anchors"], dict):
                ent_cats = self.data.setdefault("entity_categories", {})
                for pk, pv in list(self.data["plot_anchors"].items()):
                    if pk not in chars_dict:
                        ent_cats.pop(pk, None)
                        cat_p = classify_entity_category(pk, context=str(pv), series_bible=self)
                        if cat_p == EntityCategory.ANTHROPONYM:
                            cat_p = EntityCategory.CHREMATONYM
                        ent_cats[pk] = cat_p.value
                    elif pk not in ent_cats:
                        cat_p = classify_entity_category(pk, context=str(pv), series_bible=self)
                        ent_cats[pk] = cat_p.value

            # Normalizacja relacji i kotwic do formy czysto pozytywnej (Operacja 2B.8 / Standard 10.1)
            for sec in ("plot_anchors", "relationships", "relations"):
                if sec in self.data and isinstance(self.data[sec], dict):
                    for k, v in list(self.data[sec].items()):
                        if isinstance(v, str):
                            self.data[sec][k] = _normalize_negative_directive(v)

            for char_k in list(self.data["characters"].keys()):
                if "->" in char_k:
                    continue
                c_val = self.data["characters"][char_k]
                clean_k = extract_clean_speaker_name(char_k).strip()
                k_lower = clean_k.lower()
                norm_lower = normalize_ascii_diacritics(clean_k).strip().lower()

                _COLLECTIVE_NUMBERS = {
                    "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten",
                    "jeden", "dwa", "trzy", "cztery", "pięć", "sześć", "siedem", "ośm", "dziewięć", "dziesięć"
                }
                _COLLECTIVE_PLURALS = {
                    "sorcerers", "knights", "witches", "magicians", "orders", "lords", "guardians",
                    "warriors", "spirits", "gods", "demons", "dragons", "magów", "rycerzy", "czarodziejów"
                }
                tokens_chk = k_lower.split()
                is_collective_head = (
                    (tokens_chk and tokens_chk[0] in _COLLECTIVE_NUMBERS)
                    or any(t in _COLLECTIVE_PLURALS for t in tokens_chk)
                )

                # P0 verified personal character fast-path (Zero-Overhead Invariance)
                is_p0_person = (
                    isinstance(c_val, dict)
                    and bool(c_val.get("has_verified_gender") or c_val.get("priority") == "P0")
                    and c_val.get("gender") in ("MALE", "FEMALE")
                    and k_lower not in COLLECTIVE_LABELS
                    and k_lower not in POLISH_COMMON_NOUN_HOMONYMS
                    and not is_generic_actor_or_category(clean_k)
                    and not is_collective_head
                )
                if is_p0_person:
                    continue

                # Badanie homonimii z polskimi rzeczownikami pospolitymi
                is_homonym = (
                    k_lower in POLISH_COMMON_NOUN_HOMONYMS
                    or norm_lower in POLISH_COMMON_NOUN_HOMONYMS
                    or is_proper_noun_homonym(clean_k)
                )

                # Badanie kategorii ontologicznej
                cat = self.get_entity_category(clean_k)
                is_toponym = (cat == EntityCategory.TOPONYM)
                is_chrematonym = (cat == EntityCategory.CHREMATONYM)
                is_non_char = self.is_non_character_entity(char_k)

                # Badanie szyldów, ról generycznych i powiadomień ciągłości (continuity_bridge_alerts)
                is_sign = is_sign_entity(char_k) or is_sign_entity(clean_k)
                is_in_relations = False
                if hasattr(self, "data") and isinstance(self.data, dict):
                    all_rels = list(self.data.get("relationships", {}).keys()) + list(self.data.get("relations", {}).keys())
                    for rk in all_rels:
                        if any(p.strip().lower() == clean_k.lower() for p in rk.split("->")):
                            is_in_relations = True
                            break

                is_generic = is_generic_actor_or_category(clean_k) or is_generic_actor_or_category(char_k)
                if not is_generic:
                    if clean_k.lower() in COLLECTIVE_LABELS or (len(clean_k.split()) == 1 and clean_k[0].islower()):
                        is_generic = True
                is_continuity = False
                if isinstance(c_val, dict):
                    if c_val.get("is_sign") or c_val.get("role") in ("sign", "napis"):
                        is_sign = True
                    if c_val.get("source") == "continuity_bridge_alerts" or c_val.get("role") == "continuity_bridge_alert" or c_val.get("is_continuity_alert"):
                        is_continuity = True
                else:
                    if is_sign_entity(char_k) or is_sign_entity(clean_k):
                        is_sign = True

                # Badanie chrematonimów i złożonych przydomków magicznych/tytularnych
                is_chrematonym_compound = bool(is_collective_head)
                tokens_k = k_lower.split()
                if any(pat.search(clean_k) for pat in CHREMATONYM_PATTERNS):
                    is_chrematonym_compound = True
                elif len(tokens_k) >= 2 and any(t in CHREMATONYM_HEAD_WORDS for t in tokens_k):
                    is_chrematonym_compound = True
                elif len(tokens_k) >= 2 and any(prep in tokens_k for prep in ("of", "z", "ze")):
                    head_first = tokens_k[0]
                    if head_first in KNOWN_HEAD_NOUNS or head_first in CHREMATONYM_HEAD_WORDS:
                        is_chrematonym_compound = True

                # Badanie niezweryfikowanych artefaktów akustycznych o niskiej pewności względem fonotaktyki antroponimicznej
                is_acoustic_artifact = False
                if isinstance(c_val, dict):
                    conf = float(c_val.get("confidence", 1.0))
                    is_trans = bool(c_val.get("is_transient", False))
                    has_ver = bool(c_val.get("has_verified_gender", False))
                    arch = str(c_val.get("archetype", ""))
                    src = str(c_val.get("source", ""))
                    if (is_trans or arch == "SPARSE_AMBI_BACKGROUND" or src == "acoustic_artifact") and not has_ver and conf < 0.60:
                        is_acoustic_artifact = True
                    elif conf < 0.55 and not has_ver and any(clean_k.lower().startswith(p) for p in ("speaker", "voice", "audio", "ambient", "sfx")):
                        is_acoustic_artifact = True
                    elif (src in ("acoustic", "audio", "pitch") or is_trans) and not has_ver and not is_valid_anthroponymic_phonotactics(clean_k):
                        is_acoustic_artifact = True

                # Badanie leksemów nieosobowych w liczbie mnogiej
                is_non_personal_plural = False
                tokens_k = k_lower.split()
                if (
                    k_lower in NON_PERSONAL_PLURAL_LEXEMES
                    or norm_lower in NON_PERSONAL_PLURAL_LEXEMES
                    or (tokens_k and tokens_k[0] in NON_PERSONAL_PLURAL_LEXEMES)
                ):
                    is_non_personal_plural = True

                if is_sign or is_generic or is_continuity:
                    del self.data["characters"][char_k]
                    if "declensions" in self.data and char_k in self.data["declensions"]:
                        del self.data["declensions"][char_k]
                elif is_toponym:
                    self.register_entity_category(char_k, EntityCategory.TOPONYM)
                    del self.data["characters"][char_k]
                    if "declensions" in self.data and char_k in self.data["declensions"]:
                        del self.data["declensions"][char_k]
                elif is_chrematonym or is_chrematonym_compound or is_non_personal_plural:
                    self.register_entity_category(char_k, EntityCategory.CHREMATONYM)
                    del self.data["characters"][char_k]
                    if "declensions" in self.data and char_k in self.data["declensions"]:
                        del self.data["declensions"][char_k]
                elif is_non_char or is_homonym or is_acoustic_artifact:
                    del self.data["characters"][char_k]
                    if "declensions" in self.data and char_k in self.data["declensions"]:
                        del self.data["declensions"][char_k]

            # -------------------------------------------------------------
            # c) Weryfikacja fonotaktyczna płci i wycofanie niezweryfikowanych etykiet FEMALE
            # -------------------------------------------------------------
            WESTERN_FEMALE_PHONOTACTIC_SUFFIXES: Tuple[str, ...] = (
                "ette", "otte", "tte", "elle", "anne", "inne", "ine", "ise", "ice"
            )
            NON_NAME_WORDS: Set[str] = {
                "prince", "police", "device", "service", "voice", "justice", "office", "notice", "practice", "choice", "line", "time"
            }

            for char_name, c_val in list(self.data["characters"].items()):
                if "->" in char_name:
                    continue
                desc = c_val.get("description", "") if isinstance(c_val, dict) else str(c_val)
                d_lower = desc.lower()
                clean_c = extract_clean_speaker_name(char_name).strip()
                c_tokens = clean_c.lower().split()

                is_verified_p0 = (
                    (isinstance(c_val, dict) and bool(c_val.get("has_verified_gender")) and c_val.get("priority") == "P0")
                    or "zweryfikowan" in d_lower
                    or (isinstance(c_val, dict) and c_val.get("source") in ("anilist", "quality_gate"))
                )

                # 1. Zachodnie imiona żeńskie wg fonotaktyki (-tte, -ette, -otte, -elle, -anne, -inne, -ise, -ice)
                is_western_female = False
                curr_gender = str(c_val.get("gender", "")).upper() if isinstance(c_val, dict) else ""
                if not curr_gender or curr_gender == "UNKNOWN":
                    for tok in (c_tokens[0], c_tokens[-1]) if c_tokens else ():
                        if len(tok) >= 4 and any(tok.endswith(suf) for suf in WESTERN_FEMALE_PHONOTACTIC_SUFFIXES) and not tok.endswith("mine"):
                            if tok not in NON_NAME_WORDS:
                                is_western_female = True
                                break

                if is_western_female:
                    if not (is_verified_p0 and curr_gender == "MALE"):
                        clean_desc = re.sub(r"\b(?:mężczyzna|męsk\w*|male)\b", "KOBIETA", desc, flags=re.IGNORECASE)
                        clean_desc = re.sub(r"\[MĘŻCZYZNA \(Adresat[^\]]*\]", "[KOBIETA (Adresat) - W 2. os. lp. 'ty' wymóg form żeńskich: byłaś / zrobiłaś / jesteś pewna]", clean_desc, flags=re.IGNORECASE)
                        if isinstance(c_val, dict):
                            c_val["gender"] = "FEMALE"
                            c_val["has_verified_gender"] = True
                            c_val["confidence"] = max(float(c_val.get("confidence", 0.0)), 0.95)
                            c_val["priority"] = "P0"
                            c_val["description"] = clean_desc
                        else:
                            self.data["characters"][char_name] = {
                                "description": clean_desc,
                                "gender": "FEMALE",
                                "has_verified_gender": True,
                                "confidence": 0.95,
                                "priority": "P0"
                            }
                        if "declensions" in self.data and isinstance(self.data["declensions"], dict):
                            self.data["declensions"][char_name] = generate_polish_name_declension(char_name, "FEMALE")
                        continue

                # 2. Blokada fałszywej etykiety FEMALE dla imion na -i / -y bez twardych dowodów
                ends_in_i_or_y = any(t.endswith(("i", "y")) for t in c_tokens) if c_tokens else False
                is_female_tagged = (
                    (isinstance(c_val, dict) and str(c_val.get("gender", "")).upper() in ("FEMALE", "KOBIETA"))
                    or "kobieta" in d_lower
                    or "żeńsk" in d_lower
                    or "female" in d_lower
                )

                if ends_in_i_or_y and is_female_tagged:
                    has_hard_female_evidence = (
                        is_verified_p0
                        or any(w in d_lower for w in ("anilist", "królowa", "księżniczka", "matka", "córka", "siostra", "dziewczyna", "atashi", "atai", "ojo-sama", "hime"))
                        or (isinstance(c_val, dict) and c_val.get("anaphora_score", 0) <= -4)
                        or (isinstance(c_val, dict) and bool(c_val.get("has_verified_gender")))
                        or (isinstance(c_val, dict) and float(c_val.get("confidence", 0.0)) >= 0.85)
                        or (isinstance(c_val, dict) and c_val.get("priority") == "P0")
                        or ("declensions" in self.data and isinstance(self.data["declensions"], dict) and self.data["declensions"].get(char_name, {}).get("gender") == "FEMALE")
                        or (re.search(r"\[KOBIETA\s+\(Adresat", desc, re.IGNORECASE) is not None)
                        or (char_name.lower() in FEMALE_LEXICON_NAMES or any(t in FEMALE_LEXICON_NAMES for t in c_tokens))
                    )
                    if not has_hard_female_evidence:
                        has_male_clues = (
                            char_name.lower() in CANONICAL_MALE_NAMES
                            or any(t in CANONICAL_MALE_NAMES for t in c_tokens)
                            or has_japanese_male_name_suffix(char_name)
                            or any(has_japanese_male_name_suffix(t) for t in c_tokens)
                            or is_official_or_court_consonant_name(char_name, series_bible=self)
                            or is_male_role_text(d_lower)
                            or any(w in d_lower for w in BOY_ROLE_KEYWORDS)
                            or bool(re.search(r"(?:'s\s+|\b)(?:kid|son|boy|brother|brat|syn|chłopak|chłopiec)\b", char_name.lower()))
                            or (isinstance(c_val, dict) and c_val.get("anaphora_score", 0) >= 3)
                        )
                        if has_male_clues:
                            clean_desc = re.sub(r"\b(?:kobieta|żeńsk\w*|female)\b", "MĘŻCZYZNA", desc, flags=re.IGNORECASE)
                            clean_desc = re.sub(r"\[KOBIETA \(Adresat[^\]]*\]", "[MĘŻCZYZNA (Adresat) - W 2. os. lp. 'ty' wymóg form męskich: byłeś / zrobiłeś / jesteś pewien]", clean_desc, flags=re.IGNORECASE)
                            if isinstance(c_val, dict):
                                c_val["gender"] = "MALE"
                                c_val["has_verified_gender"] = True
                                c_val["confidence"] = 0.90
                                c_val["description"] = clean_desc
                            else:
                                self.data["characters"][char_name] = {"description": clean_desc, "gender": "MALE", "has_verified_gender": True, "confidence": 0.90}
                            if "declensions" in self.data and char_name in self.data["declensions"]:
                                self.data["declensions"][char_name] = generate_polish_name_declension(char_name, "MALE")
                        else:
                            clean_desc = re.sub(r"\b(?:kobieta|żeńsk\w*|female)\b", "POSTAĆ", desc, flags=re.IGNORECASE)
                            clean_desc = re.sub(r"\[KOBIETA \(Adresat[^\]]*\]", "", clean_desc, flags=re.IGNORECASE)
                            if isinstance(c_val, dict):
                                c_val["gender"] = "UNKNOWN"
                                c_val["has_verified_gender"] = False
                                c_val["confidence"] = 0.50
                                c_val["description"] = clean_desc
                            else:
                                self.data["characters"][char_name] = {"description": clean_desc, "gender": "UNKNOWN", "has_verified_gender": False, "confidence": 0.50}
                            if "declensions" in self.data and char_name in self.data["declensions"]:
                                self.data["declensions"][char_name] = generate_polish_name_declension(char_name, "UNKNOWN")
                        continue

                # 3. Standardowa weryfikacja etykiet FEMALE (watakushi, retrospekcje, wysokie F0)
                is_verified = (
                    (isinstance(c_val, dict) and bool(c_val.get("has_verified_gender")))
                    or "zweryfikowan" in d_lower
                    or "anilist" in d_lower
                    or (isinstance(c_val, dict) and c_val.get("source") in ("anilist", "quality_gate"))
                )
                if is_verified:
                    continue
                if char_name.lower() in FEMALE_LEXICON_NAMES or any(t in FEMALE_LEXICON_NAMES for t in c_tokens):
                    continue

                is_female = (
                    (isinstance(c_val, dict) and str(c_val.get("gender", "")).upper() in ("FEMALE", "KOBIETA"))
                    or "kobieta" in d_lower
                    or "żeńsk" in d_lower
                    or "female" in d_lower
                )
                if not is_female:
                    continue

                has_watakushi = ("watakushi" in d_lower or "formalne" in d_lower)
                is_flashback = any(fb in d_lower or fb in char_name.lower() for fb in ("flashback", "retrospekcj", "past", "young", "child", "kid"))
                has_high_f0 = ("f0" in d_lower or "akustyk" in d_lower or "pitch" in d_lower or (isinstance(c_val, dict) and c_val.get("f0_hz", 0) > 170.0))
                low_conf = (isinstance(c_val, dict) and (c_val.get("confidence", 1.0) < 0.75 or c_val.get("is_transient", False)))

                has_male_clues = (
                    char_name.lower() in CANONICAL_MALE_NAMES
                    or any(t in CANONICAL_MALE_NAMES for t in c_tokens)
                    or has_japanese_male_name_suffix(char_name)
                    or any(has_japanese_male_name_suffix(t) for t in c_tokens)
                    or is_official_or_court_consonant_name(char_name, series_bible=self)
                    or is_male_role_text(d_lower)
                    or any(w in d_lower for w in BOY_ROLE_KEYWORDS)
                    or bool(re.search(r"(?:'s\s+|\b)(?:kid|son|boy|brother|brat|syn|chłopak|chłopiec)\b", char_name.lower()))
                )

                if has_watakushi or (is_flashback and has_high_f0) or (is_flashback and has_male_clues) or (low_conf and has_watakushi):
                    if has_male_clues or (is_flashback and not any(w in d_lower for w in FEMALE_ROLE_KEYWORDS)):
                        # Poprawa na MĘŻCZYZNA
                        clean_desc = re.sub(r"\b(?:kobieta|żeńsk\w*|female)\b", "MĘŻCZYZNA", desc, flags=re.IGNORECASE)
                        clean_desc = re.sub(r"\[KOBIETA \(Adresat[^\]]*\]", "[MĘŻCZYZNA (Adresat) - W 2. os. lp. 'ty' wymóg form męskich: byłeś / zrobiłeś / jesteś pewien]", clean_desc, flags=re.IGNORECASE)
                        if isinstance(c_val, dict):
                            c_val["gender"] = "MALE"
                            c_val["has_verified_gender"] = True
                            c_val["confidence"] = 1.0
                            c_val["description"] = clean_desc
                        else:
                            self.data["characters"][char_name] = {"description": clean_desc, "gender": "MALE", "has_verified_gender": True, "confidence": 1.0}
                        if "declensions" in self.data and char_name in self.data["declensions"]:
                            self.data["declensions"][char_name] = generate_polish_name_declension(char_name, "MALE")
                    else:
                        # Wycofanie niezweryfikowanej etykiety na neutralną
                        clean_desc = re.sub(r"\b(?:kobieta|żeńsk\w*|female)\b", "POSTAĆ", desc, flags=re.IGNORECASE)
                        clean_desc = re.sub(r"\[KOBIETA \(Adresat[^\]]*\]", "", clean_desc, flags=re.IGNORECASE)
                        if isinstance(c_val, dict):
                            c_val["gender"] = "UNKNOWN"
                            c_val["has_verified_gender"] = False
                            c_val["description"] = clean_desc
                        else:
                            self.data["characters"][char_name] = {"description": clean_desc, "gender": "UNKNOWN", "has_verified_gender": False}
                        if "declensions" in self.data and char_name in self.data["declensions"]:
                            self.data["declensions"][char_name] = generate_polish_name_declension(char_name, "UNKNOWN")

            # -------------------------------------------------------------
            # d) Pozytywny schemat rekordu postaci (CharacterRecord Positive Schema) & Indeks Aliases
            # -------------------------------------------------------------
            # Zliczanie częstotliwości pierwszych członów imion w serii dla jednoznacznej identyfikacji O(1)
            first_name_counts = Counter()
            # Zliczanie wystąpień nazwisk pod kątem konfliktów p0_gender
            surname_genders = defaultdict(set)
            for ch_k, c_ent in self.data["characters"].items():
                if "->" in ch_k:
                    continue
                cl_k = extract_clean_speaker_name(ch_k).strip()
                toks = cl_k.split()
                if toks:
                    fn = toks[0].lower()
                    if len(fn) >= 2 and fn not in ("von", "van", "de", "del", "di", "da", "the", "san", "sama", "kun", "chan", "senpai"):
                        first_name_counts[fn] += 1
                if len(toks) > 1:
                    last_tok = toks[-1].lower()
                    last_tok_norm = normalize_ascii_diacritics(last_tok)
                    char_g = str(c_ent.get("gender") or "").upper() if isinstance(c_ent, dict) else ""
                    if char_g in ("MALE", "FEMALE"):
                        surname_genders[last_tok].add(char_g)
                        surname_genders[last_tok_norm].add(char_g)

            conflicting_surnames = {s_tok for s_tok, g_set in surname_genders.items() if len(g_set) > 1}

            for char_name, c_val in list(self.data["characters"].items()):
                if "->" in char_name:
                    continue
                if not isinstance(c_val, dict):
                    c_val = {"description": str(c_val)}
                    self.data["characters"][char_name] = c_val

                desc = c_val.get("description", "")
                clean_c = extract_clean_speaker_name(char_name).strip()
                c_tokens = clean_c.split()

                # 1. Promocja informacji o płci do pól strukturalnych (P0 / confidence >= 0.95)
                curr_g = str(c_val.get("gender") or "").strip().upper()
                if curr_g not in ("MALE", "FEMALE"):
                    extracted_g = self.get_character_gender(char_name, allow_generic_nouns=False)
                    if extracted_g in ("MALE", "FEMALE"):
                        curr_g = extracted_g
                    else:
                        desc_l = desc.lower()
                        if re.search(r"\b(?:kobieta|żeńsk\w*|female|dziewczyn\w*|matka|córka|siostra)\b", desc_l):
                            curr_g = "FEMALE"
                        elif re.search(r"\b(?:mężczyzna|męsk\w*|male|chłopak|ojciec|syn|brat)\b", desc_l):
                            curr_g = "MALE"

                if curr_g in ("MALE", "FEMALE"):
                    c_val["gender"] = curr_g
                    c_val["grammatical_gender"] = "MASCULINE" if curr_g == "MALE" else "FEMININE"
                    c_val["has_verified_gender"] = True
                    c_val["confidence"] = max(float(c_val.get("confidence", 0.0)), 0.95)
                    c_val["priority"] = "P0"
                    # Sanitacja description pod kątem zgodności z gender (Operacja 2C.5)
                    if curr_g == "FEMALE" and "description" in c_val:
                        desc = re.sub(r"\bMĘŻCZYZNA\b", "KOBIETA", str(c_val["description"]), flags=re.IGNORECASE)
                        c_val["description"] = desc
                    elif curr_g == "MALE" and "description" in c_val:
                        desc = re.sub(r"\bKOBIETA\b", "MĘŻCZYZNA", str(c_val["description"]), flags=re.IGNORECASE)
                        c_val["description"] = desc
                else:
                    c_val.setdefault("gender", "UNKNOWN")
                    c_val.setdefault("grammatical_gender", "UNKNOWN")
                    c_val.setdefault("confidence", 0.50)
                    c_val.setdefault("priority", "P1")
                    c_val.setdefault("has_verified_gender", False)

                # 2. Oczyszczenie pola description z wszelkich instrukcji i dyrektyw gramatycznych
                clean_desc = desc
                if curr_g == "FEMALE":
                    clean_desc = re.sub(r"\bMĘŻCZYZNA\b", "KOBIETA", clean_desc, flags=re.IGNORECASE)
                elif curr_g == "MALE":
                    clean_desc = re.sub(r"\bKOBIETA\b", "MĘŻCZYZNA", clean_desc, flags=re.IGNORECASE)
                clean_desc = re.sub(r"\[[^\]]*\bAdresat(?:ka|ce|ki|ek|om|ami|ach|em|owi)?\b[^\]]*\]", "", clean_desc, flags=re.IGNORECASE)
                clean_desc = re.sub(r"\[(?!GRUPA\s+(?:KOBIET|MĘŻCZYZN))[^\]]*(?:wymóg form|nakaz form|eliminacja form|blokada form|rejestr|zwrot do adresata|tytułuj|pan/pani|filar clxv|ochrona przeskoków|dyskontinuitet|relacja hierarchiczna|para dwóch kobiet|t-v invariance)[^\]]*\]", "", clean_desc, flags=re.IGNORECASE)
                clean_desc = re.sub(r"\([^\)]*(?:wymóg form|nakaz form|eliminacja form|blokada form|rejestr|zwrot do adresata|w 2\.\s*os\.\s*lp\.)[^\)]*\)", "", clean_desc, flags=re.IGNORECASE)
                clean_desc = re.sub(r"-\s*W 2\.\s*os\.\s*lp\.\s*['\"]ty['\"][^.!?\n]*?(?:byłeś|byłaś|zrobiłeś|zrobiłaś|jesteś pewien|jesteś pewna)[^.!?\n]*", "", clean_desc, flags=re.IGNORECASE)
                clean_desc = re.sub(r"W 2\.\s*os\.\s*lp\.\s*['\"]ty['\"][^.!?\n]*?(?:byłeś|byłaś|zrobiłeś|zrobiłaś|jesteś pewien|jesteś pewna)[^.!?\n]*", "", clean_desc, flags=re.IGNORECASE)
                clean_desc = re.sub(r"-\s*w rozmowach na osobności[^.!?\n]*", "", clean_desc, flags=re.IGNORECASE)
                clean_desc = re.sub(r"\s+", " ", clean_desc).strip()
                if not clean_desc and curr_g in ("MALE", "FEMALE"):
                    clean_desc = "MĘŻCZYZNA" if curr_g == "MALE" else "KOBIETA"
                c_val["description"] = clean_desc

                # 3. Zbudowanie pełnego indeksu tożsamości w polu aliases
                aliases_set = set(c_val.get("aliases", []))
                aliases_set.add(char_name)
                aliases_set.add(clean_c)
                if len(c_tokens) > 1:
                    first_tok = c_tokens[0]
                    # Automatycznie dodaj pierwszy człon (FirstName) do aliases gdy jednoznacznie identyfikuje postać w serii
                    if (
                        len(first_tok) >= 2
                        and first_tok.lower() not in ("von", "van", "de", "del", "di", "da", "the", "san", "sama", "kun", "chan", "senpai")
                        and first_name_counts[first_tok.lower()] == 1
                    ):
                        aliases_set.add(first_tok)
                        ft_folded = normalize_ascii_diacritics(first_tok)
                        if ft_folded != first_tok:
                            aliases_set.add(ft_folded)

                    for tok in c_tokens[1:]:
                        if len(tok) >= 2 and tok.lower() not in ("von", "van", "de", "del", "di", "da", "the", "san", "sama", "kun", "chan", "senpai"):
                            tok_norm = normalize_ascii_diacritics(tok.lower())
                            if tok.lower() not in conflicting_surnames and tok_norm not in conflicting_surnames:
                                aliases_set.add(tok)
                                tok_folded = normalize_ascii_diacritics(tok)
                                if tok_folded != tok:
                                    aliases_set.add(tok_folded)

                # Oczyszczenie istniejacych aliasow z jednowyrazowych nazwisk kolidujacych plcia
                aliases_set = {
                    a for a in aliases_set
                    if len(a.split()) > 1 or (a.lower() not in conflicting_surnames and normalize_ascii_diacritics(a.lower()) not in conflicting_surnames)
                }
                aliases_set.add(char_name)
                aliases_set.add(clean_c)
                base_c = extract_base_canonical_name(clean_c)
                if base_c and base_c != clean_c:
                    aliases_set.add(base_c)
                c_val["aliases"] = sorted(list(aliases_set))
                c_val["entity_category"] = EntityCategory.ANTHROPONYM.value

            # Budowa globalnego indeksu aliasów O(1) w SeriesBible (z priorytetyzacją P0/verified)
            self._rebuild_actor_aliases_index()

            # Czyszczenie wpisów będących złożonymi deskrypcjami z declensions
            if "declensions" in self.data and isinstance(self.data["declensions"], dict):
                for d_k in list(self.data["declensions"].keys()):
                    if is_sign_entity(d_k) or is_generic_actor_or_category(d_k) or is_complex_description(d_k) or not is_valid_anthroponymic_phonotactics(d_k):
                        del self.data["declensions"][d_k]

            # -------------------------------------------------------------
            # e) Synchronizacja płci postaci i adresatów w relations z rekordami P0 (Standard 9.2, Zmiana 5)
            # -------------------------------------------------------------
            for rel_dict_name in ("relations", "relationships"):
                if rel_dict_name in self.data and isinstance(self.data[rel_dict_name], dict):
                    for rel_k, rel_desc in list(self.data[rel_dict_name].items()):
                        desc_val = rel_desc.get("description", "") if isinstance(rel_desc, dict) else str(rel_desc)
                        if "adresat" not in desc_val.lower():
                            continue
                        target_char = None
                        if "->" in rel_k:
                            target_char = rel_k.split("->")[-1].strip()
                        else:
                            for ch_name in self.data.get("characters", {}):
                                if "->" not in ch_name and ch_name in rel_k:
                                    target_char = ch_name
                                    break

                        if target_char:
                            ch_entry = self.data.get("characters", {}).get(target_char)
                            if not ch_entry:
                                ch_entry = self.get_character(target_char)
                            if ch_entry and isinstance(ch_entry, dict):
                                is_ver = bool(ch_entry.get("has_verified_gender", False) or ch_entry.get("priority") == "P0")
                                p0_g = str(ch_entry.get("gender", "")).upper()
                                if is_ver and p0_g in ("FEMALE", "MALE"):
                                    if p0_g == "FEMALE":
                                        new_desc = re.sub(
                                            r"\[MĘŻCZYZNA\s+\(Adresat[^\]]*\]",
                                            "[KOBIETA (Adresat) - W 2. os. lp. 'ty' wymóg form żeńskich: byłaś / zrobiłaś / jesteś pewna]",
                                            desc_val,
                                            flags=re.IGNORECASE
                                        )
                                        if new_desc != desc_val:
                                            if isinstance(rel_desc, dict):
                                                rel_desc["description"] = new_desc
                                            else:
                                                self.data[rel_dict_name][rel_k] = new_desc
                                    elif p0_g == "MALE":
                                        new_desc = re.sub(
                                            r"\[KOBIETA\s+\(Adresat[^\]]*\]",
                                            "[MĘŻCZYZNA (Adresat) - W 2. os. lp. 'ty' wymóg form męskich: byłeś / zrobiłeś / jesteś pewien]",
                                            desc_val,
                                            flags=re.IGNORECASE
                                        )
                                        if new_desc != desc_val:
                                            if isinstance(rel_desc, dict):
                                                rel_desc["description"] = new_desc
                                            else:
                                                self.data[rel_dict_name][rel_k] = new_desc

            # 4. Spójność relacji T/V i reżimu formalnego (Operacja 2C.5, R3.1)
            self._validate_relation_entry_consistency()

            # 5. Sanitacja i regeneracja paradygmatów odmiany w RAM (Standard 9.5, 2C.4, R3.1)
            decl_dict = self.data.get("declensions", {})
            if isinstance(decl_dict, dict):
                corrupt_indicators = ("ńa", "ńowi", "ńem", "ńie", "e'a", "e'owi", "e'em", "Promienii")
                for decl_k, decl_cases in list(decl_dict.items()):
                    if isinstance(decl_cases, dict):
                        has_corrupt = False
                        for case_k in ("D", "C", "B", "N", "Ms", "W"):
                            case_str = str(decl_cases.get(case_k, ""))
                            if any(ind in case_str for ind in corrupt_indicators):
                                has_corrupt = True
                                break
                        if has_corrupt:
                            ch_entry = self.get_character(decl_k)
                            g = ch_entry.get("gender", "UNKNOWN") if isinstance(ch_entry, dict) else "UNKNOWN"
                            regenerated = generate_polish_name_declension(decl_k, gender=g)
                            if regenerated and regenerated.get("M"):
                                decl_dict[decl_k] = regenerated

            # 6. Automatyczne odmrażanie zamrożonych mianowników męskich P0 (Standard 9.6, 2C.4)
            if isinstance(decl_dict, dict):
                chars_map = self.data.get("characters", {})
                for c_name, c_rec in list(chars_map.items()):
                    if "->" in c_name or not isinstance(c_rec, dict):
                        continue
                    g_val = str(c_rec.get("gender") or "").upper()
                    cat_val = c_rec.get("entity_category")
                    is_anthro = (cat_val in ("ANTHROPONYM", getattr(EntityCategory.ANTHROPONYM, "value", "ANTHROPONYM")) or not cat_val)
                    if g_val == "MALE" and is_anthro:
                        cur_decl = decl_dict.get(c_name)
                        if isinstance(cur_decl, dict):
                            frozen = all(cur_decl.get(k) == c_name for k in ("M", "D", "C", "B", "N", "Ms", "W") if k in cur_decl)
                            if frozen:
                                new_decl = generate_polish_name_declension(c_name, "MALE")
                                if new_decl and any(new_decl.get(k) != c_name for k in ("D", "C", "B", "N", "Ms", "W") if k in new_decl):
                                    new_decl["gender"] = "MALE"
                                    decl_dict[c_name] = new_decl

            # 7. Rejestracja aliasów zdrobniałych z honoryfikatorem i obciętym rdzeniem (Operacja 2B.1 / 2C.1)
            t_romaji = str(self.data.get("anime_title") or getattr(self, "anime_title", "") or "")
            anchor_text = " ".join([str(v) for v in self.data.get("plot_anchors", {}).values()])
            combined_corpus = f"{t_romaji} {anchor_text}"
            found_h_tokens = re.findall(r"\b([A-ZĄĆĘŁŃÓŚŹŻa-ząćęłńóśźż]+)-(?:chan|kun|san|sama|senpai|dono|tan|pyon)\b", combined_corpus, flags=re.IGNORECASE)
            chars_map = self.data.get("characters", {})
            for raw_stem in set(found_h_tokens):
                stem_lower = raw_stem.lower()
                prefix2 = stem_lower[:2]
                target_char_name = None
                for char_k, char_v in chars_map.items():
                    if not isinstance(char_v, dict) or "->" in char_k:
                        continue
                    c_name = str(char_v.get("name") or char_k).strip()
                    if " " not in c_name and c_name.lower().startswith(prefix2):
                        target_char_name = char_k
                        break

                for char_k, char_v in chars_map.items():
                    if not isinstance(char_v, dict) or "->" in char_k:
                        continue
                    c_aliases = char_v.setdefault("aliases", [])
                    stems_to_scrub = {f"{stem_lower}-chan", stem_lower, f"{stem_lower}-kun"}
                    if char_k == target_char_name:
                        for al in (f"{raw_stem}-chan", raw_stem, f"{raw_stem}-kun"):
                            if al not in c_aliases:
                                c_aliases.append(al)
                    else:
                        char_v["aliases"] = [a for a in c_aliases if str(a).lower() not in stems_to_scrub]

            # 8. Strukturalna unifikacja postaci, eliminacja kolizji aliasów i higiena relacji (Standard 10.0, H-Z4-04)
            bible_modified = False
            chars = self.data.get("characters", {})

            # 8a. Deduplikacja kolizji aliasów wspólnych nazwisk
            surname_map = {}
            for k, v in list(chars.items()):
                if "->" in k or not isinstance(v, dict):
                    continue
                toks = k.split()
                if len(toks) >= 2:
                    surn = toks[-1].lower()
                    surname_map.setdefault(surn, []).append((k, v))

            for surn, char_list in surname_map.items():
                if len(char_list) >= 2:
                    for k, v in char_list:
                        orig_aliases = list(v.get("aliases", []))
                        new_aliases = [a for a in orig_aliases if a.lower() != surn]
                        first_name = k.split()[0]
                        if first_name not in new_aliases:
                            new_aliases.append(first_name)
                        if new_aliases != orig_aliases:
                            v["aliases"] = sorted(list(set(new_aliases)))
                            bible_modified = True

            # 8b. Unifikacja rekordów jedno- i wieloczłonowych (skrócone miano -> pełny rekord)
            for k in list(chars.keys()):
                if "->" in k or not isinstance(chars[k], dict):
                    continue
                k_toks = k.split()
                if len(k_toks) == 1 and k in chars:
                    single_val = chars[k]
                    # poszukaj rekordu nadrzędnego
                    for full_k, full_val in list(chars.items()):
                        if full_k != k and "->" not in full_k and isinstance(full_val, dict):
                            full_toks = full_k.split()
                            first_tok = full_toks[0].lower()
                            match = (
                                (len(full_toks) >= 2 and first_tok == k.lower())
                                or (len(full_toks) >= 2 and first_tok.startswith(k.lower()) and len(k) >= 4)
                                or (len(full_toks) == 1 and full_k.lower().startswith(k.lower()) and len(k) >= 4 and len(full_k) > len(k))
                            )
                            if match:
                                if single_val.get("has_verified_gender") or single_val.get("priority") == "P0":
                                    if not full_val.get("has_verified_gender") or full_val.get("priority") != "P0":
                                        full_val["gender"] = single_val.get("gender", full_val.get("gender"))
                                        full_val["grammatical_gender"] = single_val.get("grammatical_gender", full_val.get("grammatical_gender"))
                                        full_val["has_verified_gender"] = True
                                        full_val["confidence"] = max(float(full_val.get("confidence", 0.0)), float(single_val.get("confidence", 0.0)))
                                        full_val["priority"] = "P0"
                                if "aliases" not in full_val:
                                    full_val["aliases"] = [full_k]
                                if k not in full_val["aliases"]:
                                    full_val["aliases"].append(k)
                                    full_val["aliases"] = sorted(list(set(full_val["aliases"])))
                                del chars[k]
                                if "declensions" in self.data and k in self.data["declensions"]:
                                    del self.data["declensions"][k]
                                bible_modified = True
                                break

                        # 8d. Deduplikacja P2 względem aliasów i imion P0/P1 (Operacja 2B.2, Hipoteza H7)
            p0_verified_aliases: Dict[str, str] = {}
            for k, v in list(chars.items()):
                if "->" in k or not isinstance(v, dict):
                    continue
                is_p0 = bool(v.get("has_verified_gender") or v.get("priority") in ("P0", "P1"))
                g = str(v.get("gender") or "").upper()
                if is_p0 and g in ("MALE", "FEMALE"):
                    p0_verified_aliases[k.lower()] = k
                    p0_verified_aliases[normalize_ascii_diacritics(k.lower())] = k
                    for al in v.get("aliases", []):
                        al_str = str(al).strip()
                        al_low = al_str.lower()
                        if len(al_str.split()) == 1 and (al_low in conflicting_surnames or normalize_ascii_diacritics(al_low) in conflicting_surnames):
                            continue
                        p0_verified_aliases[al_low] = k
                        p0_verified_aliases[normalize_ascii_diacritics(al_low)] = k
                    k_toks = extract_clean_speaker_name(k).split()
                    if len(k_toks) >= 2:
                        fn = k_toks[0].lower()
                        if len(fn) >= 2 and fn not in ("von", "van", "de", "del", "di", "da", "the", "san", "sama", "kun", "chan", "senpai") and first_name_counts[fn] == 1:
                            p0_verified_aliases[fn] = k
                            p0_verified_aliases[normalize_ascii_diacritics(fn)] = k

            for k in list(chars.keys()):
                if "->" in k or not isinstance(chars[k], dict):
                    continue
                v = chars[k]
                is_p2 = (v.get("priority") == "P2" or (not v.get("has_verified_gender") and v.get("gender") == "UNKNOWN"))
                if is_p2:
                    k_low = k.lower()
                    k_norm = normalize_ascii_diacritics(k_low)
                    matched_p0_key = p0_verified_aliases.get(k_low) or p0_verified_aliases.get(k_norm)
                    if matched_p0_key and matched_p0_key != k and matched_p0_key in chars:
                        p0_rec = chars[matched_p0_key]
                        p0_als = p0_rec.setdefault("aliases", [])
                        if k not in p0_als:
                            p0_als.append(k)
                            p0_rec["aliases"] = sorted(list(set(p0_als)))
                        del chars[k]
                        if "declensions" in self.data and k in self.data["declensions"]:
                            del self.data["declensions"][k]
                        bible_modified = True

# 8c. Higiena relacji - usuwanie przecieków promptów
            for rel_name in ("relations", "relationships"):
                if rel_name in self.data and isinstance(self.data[rel_name], dict):
                    rels = self.data[rel_name]
                    for rk, rv in list(rels.items()):
                        if isinstance(rv, str):
                            clean_v = re.sub(r"\\NRELACJA HIERARCHICZNA[^\]]*\]", "]", rv)
                            clean_v = re.sub(r"\[RELACJA HIERARCHICZNA[^\]]*\]\s*", "", clean_v)
                            clean_v = re.sub(r"\s{2,}", " ", clean_v).strip()
                            if clean_v != rv:
                                rels[rk] = clean_v
                                bible_modified = True

            if bible_modified:
                try:
                    self.save()
                except Exception:
                    logger.warning("Zapis zmodyfikowanej bazy serii zakończony wyjątkiem", exc_info=True)

            # 8. Bezwarunkowa synchronizacja klucza "gender" i regeneracja paradygmatów FEMALE w declensions (Operacje H2 i H5)
            decl_dict = self.data.setdefault("declensions", {})
            chars_dict = self.data.get("characters", {})
            for c_name, c_info in list(chars_dict.items()):
                if "->" in c_name or not isinstance(c_info, dict):
                    continue
                c_gen = str(c_info.get("gender") or "").upper()
                if c_gen == "FEMALE":
                    existing_d = decl_dict.get(c_name)
                    needs_regen = (
                        not isinstance(existing_d, dict)
                        or existing_d.get("gender") != "FEMALE"
                        or (not c_name.endswith(("a", "A")) and existing_d.get("M") != existing_d.get("D"))
                    )
                    if needs_regen:
                        new_f_decl = generate_polish_name_declension(c_name, "FEMALE")
                        new_f_decl["gender"] = "FEMALE"
                        decl_dict[c_name] = new_f_decl
                elif c_gen == "MALE":
                    if c_name in decl_dict and isinstance(decl_dict[c_name], dict):
                        decl_dict[c_name]["gender"] = "MALE"

    def populate_secondary_actor_tags(self, raw_actor_tags: List[str]) -> None:
        """
        Zasila SeriesBible encjami drugoplanowymi (P1) i epizodycznymi (P2) z Kroku 3 (Standard 9.4, 2C.7, R3.1):
        - Wyodrębnia czyste etykiety aktora (normalize_actor_tag), odrzuca etykiety nieosobowe i separatory.
        - Dla encji nieobecnych w SeriesBible tworzy wpisy:
          * P1 dla postaci z rozpoznaną płcią (MALE/FEMALE)
          * P2 dla postaci bez jednoznacznej płci (gender: UNKNOWN)
        """
        with self._lock:
            if not hasattr(self, "data") or not isinstance(self.data, dict):
                return
            chars = self.data.setdefault("characters", {})
            for raw_tag in raw_actor_tags:
                if not raw_tag or "/" in str(raw_tag) or "\\" in str(raw_tag):
                    continue
                clean_tag, explicit_g = normalize_actor_tag(str(raw_tag))
                clean_tag = clean_tag.strip()
                if not clean_tag or len(clean_tag) < 2 or is_sign_entity(clean_tag) or clean_tag.lower() in ("txt", "text", "sign", "title", "caption", "szyld", "napis"):
                    continue
                if clean_tag.lower() in COLLECTIVE_LABELS or (len(clean_tag.split()) == 1 and clean_tag[0].islower()):
                    continue
                if clean_tag in chars:
                    continue

                # Operacja 2B.2: Blokada tworzenia duplikatów P2 dla aliasów i nazw postaci P0/P1
                existing_rec = self.resolve_character_record(clean_tag)
                if existing_rec is not None and (existing_rec.get("has_verified_gender") or existing_rec.get("priority") in ("P0", "P1")):
                    continue

                clean_tag_low = clean_tag.lower()
                clean_tag_norm = normalize_ascii_diacritics(clean_tag_low)
                is_alias_of_existing = False
                for c_k, c_v in chars.items():
                    if "->" in c_k or not isinstance(c_v, dict):
                        continue
                    if c_k.lower() == clean_tag_low or normalize_ascii_diacritics(c_k.lower()) == clean_tag_norm:
                        is_alias_of_existing = True
                        break
                    for al in c_v.get("aliases", []):
                        al_low = str(al).lower()
                        if al_low == clean_tag_low or normalize_ascii_diacritics(al_low) == clean_tag_norm:
                            is_alias_of_existing = True
                            break
                    if is_alias_of_existing:
                        break
                if is_alias_of_existing:
                    continue

                masculine_lexicon = SECONDARY_LEXICAL_MALE_NOUNS
                feminine_lexicon = SECONDARY_LEXICAL_FEMALE_NOUNS
                tag_words = set(re.findall(r"\b\w+\b", clean_tag.lower()))

                if explicit_g in ("MALE", "FEMALE"):
                    chars[clean_tag] = {
                        "name": clean_tag,
                        "gender": explicit_g,
                        "grammatical_gender": "MASCULINE" if explicit_g == "MALE" else "FEMININE",
                        "confidence": 0.70,
                        "priority": "P1",
                        "has_verified_gender": False,
                        "aliases": [clean_tag],
                        "description": "Postać drugoplanowa",
                        "entity_category": "ANTHROPONYM"
                    }
                elif tag_words & masculine_lexicon:
                    chars[clean_tag] = {
                        "name": clean_tag,
                        "gender": "MALE",
                        "grammatical_gender": "MASCULINE",
                        "confidence": 0.95,
                        "priority": "P1",
                        "has_verified_gender": True,
                        "aliases": [clean_tag],
                        "description": "Postać drugoplanowa",
                        "entity_category": "ANTHROPONYM"
                    }
                elif tag_words & feminine_lexicon:
                    chars[clean_tag] = {
                        "name": clean_tag,
                        "gender": "FEMALE",
                        "grammatical_gender": "FEMININE",
                        "confidence": 0.95,
                        "priority": "P1",
                        "has_verified_gender": True,
                        "aliases": [clean_tag],
                        "description": "Postać drugoplanowa",
                        "entity_category": "ANTHROPONYM"
                    }
                else:
                    chars[clean_tag] = {
                        "name": clean_tag,
                        "gender": "UNKNOWN",
                        "grammatical_gender": "UNKNOWN",
                        "confidence": 0.50,
                        "priority": "P2",
                        "has_verified_gender": False,
                        "aliases": [clean_tag],
                        "description": "Postać epizodyczna / tło",
                        "entity_category": "ANTHROPONYM"
                    }

    def map_bilingual_role_aliases(self, raw_actor_tags: List[str]) -> None:
        """
        Automatyczne dwukierunkowe mapowanie znanych etykiet ról z sekcji [Events]
        na ich polskie odpowiedniki w SeriesBible.data['characters'] (Standard 9.0 Positive Domain, 2B.1, R3.1):
        Gdy w sekcji zdarzeń występuje rola w języku źródłowym, a w bazie wiedzy jej kanoniczny polski odpowiednik,
        dopisuje nazwę roli z sekcji zdarzeń do listy 'aliases' tej encji. I odwrotnie.
        """
        with self._lock:
            if not hasattr(self, "data") or not isinstance(self.data, dict):
                return
            chars = self.data.setdefault("characters", {})
            for raw_tag in raw_actor_tags:
                if not raw_tag:
                    continue
                clean_tag, _ = normalize_actor_tag(str(raw_tag))
                clean_tag = clean_tag.strip()
                if not clean_tag:
                    continue
                tag_l = clean_tag.lower()

                # Obsługa aliasów z honoryfikatorami (-chan/-kun)
                m_h = re.match(r"^([A-ZĄĆĘŁŃÓŚŹŻa-ząćęłńóśźż]+)-(?:chan|kun|san|sama|senpai|dono|tan|pyon)$", clean_tag, flags=re.IGNORECASE)
                if m_h:
                    stem = m_h.group(1)
                    stem_l = stem.lower()
                    prefix2 = stem_l[:2]
                    for char_k, char_v in chars.items():
                        if isinstance(char_v, dict):
                            c_name = str(char_v.get("name") or char_k).strip()
                            if " " not in c_name and c_name.lower().startswith(prefix2):
                                cur_aliases = char_v.setdefault("aliases", [])
                                for al in (clean_tag, stem, f"{stem}-kun", f"{stem}-chan"):
                                    if al not in cur_aliases:
                                        cur_aliases.append(al)
                            else:
                                if "aliases" in char_v:
                                    char_v["aliases"] = [a for a in char_v["aliases"] if str(a).lower() not in (clean_tag.lower(), stem_l, f"{stem_l}-kun", f"{stem_l}-chan")]
                    continue

                # Jeśli tag jest znany w BILINGUAL_ROLE_EQUIVALENCES (EN -> PL)
                if tag_l in BILINGUAL_ROLE_EQUIVALENCES:
                    pl_role = BILINGUAL_ROLE_EQUIVALENCES[tag_l]
                    for char_k, char_v in chars.items():
                        if isinstance(char_v, dict):
                            k_l = char_k.lower()
                            aliases = [str(a).lower() for a in char_v.get("aliases", [])]
                            if k_l == pl_role or pl_role in aliases:
                                cur_aliases = char_v.setdefault("aliases", [])
                                if clean_tag not in cur_aliases and tag_l not in [str(a).lower() for a in cur_aliases]:
                                    cur_aliases.append(clean_tag)

                # Odwrotnie: jeśli tag jest w języku polskim (PL -> EN)
                for en_role, pl_role in BILINGUAL_ROLE_EQUIVALENCES.items():
                    if pl_role == tag_l:
                        for char_k, char_v in chars.items():
                            if isinstance(char_v, dict):
                                k_l = char_k.lower()
                                aliases = [str(a).lower() for a in char_v.get("aliases", [])]
                                if k_l == en_role or en_role in aliases:
                                    cur_aliases = char_v.setdefault("aliases", [])
                                    if clean_tag not in cur_aliases and tag_l not in [str(a).lower() for a in cur_aliases]:
                                        cur_aliases.append(clean_tag)

    @staticmethod
    def _align_vocative_impl(text: str, declensions: Optional[Dict[str, Any]] = None) -> str:
        if not text or not declensions:
            return text

        canon_w_forms = set()
        decl_items = list(declensions.items()) if isinstance(declensions, dict) else []
        for _, decl in decl_items:
            if isinstance(decl, dict) and "W" in decl:
                w_val = str(decl["W"]).strip()
                if w_val and len(w_val) >= 4 and not w_val.isupper():
                    if any(c * 2 in w_val.lower() for c in "bcdfghjklmnprstvwz"):
                        canon_w_forms.add(w_val)

        if not canon_w_forms:
            return text

        def _lev(s1: str, s2: str) -> int:
            if s1 == s2:
                return 0
            if len(s1) < len(s2):
                return _lev(s2, s1)
            if len(s2) == 0:
                return len(s1)
            prev = range(len(s2) + 1)
            for i, c1 in enumerate(s1):
                cur = [i + 1]
                for j, c2 in enumerate(s2):
                    ins = prev[j + 1] + 1
                    dels = cur[j] + 1
                    subs = prev[j] + (c1 != c2)
                    cur.append(min(ins, dels, subs))
                prev = cur
            return prev[-1]

        tokens = re.finditer(r"\b([A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]+)\b", text)
        replacements = []
        for match in tokens:
            word = match.group(1)
            w_lower = word.lower()
            for canon_w in canon_w_forms:
                c_lower = canon_w.lower()
                if c_lower[0] != w_lower[0]:
                    continue
                if abs(len(c_lower) - len(w_lower)) == 1 and _lev(w_lower, c_lower) == 1:
                    has_double = any(c * 2 in c_lower for c in "bcdfghjklmnprstvwz")
                    if has_double:
                        repl_word = canon_w[0].upper() + canon_w[1:] if word[0].isupper() else canon_w.lower()
                        replacements.append((match.start(1), match.end(1), repl_word))
                        break

        if not replacements:
            return text

        res = list(text)
        for start, end, repl in sorted(replacements, key=lambda x: x[0], reverse=True):
            res[start:end] = list(repl)
        return "".join(res)

    def align_vocative_orthography(self_or_text: Any, text: Optional[str] = None, declensions: Optional[Dict[str, Any]] = None) -> str:
        """
        Ochrona ortograficzna rdzenia antroponimu w wołaczu W (Standard 9.5, 2C.4, R1.8):
        Wyrównuje pisownię rdzenia wołacza o uproszczonej spółgłosce podwójnej do formy kanonicznej W.
        """
        if isinstance(self_or_text, str):
            target_text = self_or_text
            target_decl = text if isinstance(text, dict) else declensions
            return SeriesBible._align_vocative_impl(target_text, target_decl)
        else:
            target_text = text or ""
            target_decl = declensions if declensions is not None else (self_or_text.data.get("declensions", {}) if hasattr(self_or_text, "data") and isinstance(self_or_text.data, dict) else {})
            return SeriesBible._align_vocative_impl(target_text, target_decl)

    @staticmethod
    def parse_step5_declension_line(line_content: str) -> Dict[str, str]:
        """
        Parsuje paradygmat odmiany z sekcji Odmiana Imion i Tytułów (Krok 5 / EpisodeProfiler)
        obsługując zarówno separator kropki (M., D.), jak i dwukropka (M:, D:) (Standard 9.6, 2C.4).
        """
        if not line_content:
            return {}
        case_matches = re.findall(
            r"\b(M|D|C|B|N|Ms|W)[.:]\s*([^,;\n(]+)",
            str(line_content),
        )
        res = {}
        for case_tag, val in case_matches:
            v = val.strip().strip("'\"")
            if v:
                res[case_tag] = v
        return res

    @staticmethod
    def substitute_canonical_honorific_alias(
        text: str,
        source_en: str,
        series_bible: Optional[Any] = None,
        declensions: Optional[Dict[str, Any]] = None,
        characters: Optional[Dict[str, Any]] = None,
        keep_honorifics: bool = False
    ) -> str:
        """
        Mapuje japońskie aliasy zdrobniałe z honoryfikatorami (-chan/-kun) lub obciętym rdzeniem
        na kanoniczny paradygmat fleksyjny z SeriesBible (Standard 9.6, 2B.1; Standard 9.7, 2C.1).
        """
        if not text or not source_en or keep_honorifics:
            return text

        decl_map = declensions
        if not decl_map and series_bible and hasattr(series_bible, "data") and isinstance(series_bible.data, dict):
            decl_map = series_bible.data.get("declensions", {})
        if not decl_map:
            return text

        char_map = characters
        if not char_map and series_bible and hasattr(series_bible, "data") and isinstance(series_bible.data, dict):
            char_map = series_bible.data.get("characters", {})
        char_map = char_map or {}

        res = text
        for canon_name, decl in decl_map.items():
            if not isinstance(decl, dict):
                continue
            char_rec = char_map.get(canon_name, {})
            aliases = char_rec.get("aliases", []) if isinstance(char_rec, dict) else []
            names_to_check = [canon_name] + [a for a in aliases if a]
            pattern_src = r"\b(?:" + "|".join(re.escape(n) for n in names_to_check) + r")\b"
            if not re.search(pattern_src, source_en, re.IGNORECASE):
                continue

            # Standard 9.7 (Operacja 2C.1): Poszanowanie Primary LLM Translation Authority
            # Jeśli w zdaniu polskim występuje już którykolwiek człon kanonicznej nazwy encji
            # lub którykolwiek z jej odmienionych przypadków, nie wykonujemy żadnej podmiany dla tej encji
            name_parts = [p.strip() for p in canon_name.split() if len(p.strip()) >= 2]
            decl_forms = [str(v).strip() for v in decl.values() if v and isinstance(v, str) and len(str(v).strip()) >= 2]
            text_lower = text.lower()
            if any(re.search(rf"\b{re.escape(p.lower())}\b", text_lower) for p in name_parts) or \
               any(re.search(rf"\b{re.escape(f.lower())}\b", text_lower) for f in decl_forms):
                continue

            is_multi_token = " " in canon_name
            for al in aliases:
                if not al or al.lower() == canon_name.lower():
                    continue
                stem = re.sub(r"-(?:senpai|kun|chan|san|sama|sensei|dono|tan|pyon)$", "", al, flags=re.IGNORECASE).strip()
                al_patterns = [re.escape(al)]
                # Dla encji wieloczłonowych pojedyncze człony nie mogą być podmieniane jako gołe tokeny bez honoryfikatora
                if not is_multi_token and stem and stem.lower() != al.lower():
                    al_patterns.append(re.escape(stem))
                al_re = "|".join(al_patterns)

                form_n = decl.get("N", canon_name)
                form_m = decl.get("M", canon_name)

                # Narzędnik ze spójnikiem i wcześniejszym rzeczownikiem (np. z Sasakim i Pii-chan)
                res = re.sub(
                    rf"\b(z|ze|przed|nad|pod|za|między)\s+([A-ZĄĆĘŁŃÓŚŹŻa-ząćęłńóśźż]+(?:\s+(?:i|oraz|ani)\s+))(?:{al_re})(?:-[a-zA-Z]+)?(?:em|iem)?\b",
                    rf"\g<1> \g<2>{form_n}",
                    res,
                    flags=re.IGNORECASE
                )
                # Narzędnik bezpośrednio po przyimku (np. z Pii-chan)
                res = re.sub(
                    rf"\b(z|ze|przed|nad|pod|za|między)\s+(?:{al_re})(?:-[a-zA-Z]+)?(?:em|iem)?\b",
                    rf"\g<1> {form_n}",
                    res,
                    flags=re.IGNORECASE
                )
                # Mianownik / ogólny kontekst ze wskazanym honoryfikatorem
                res = re.sub(
                    rf"\b(?:{al_re})(?:-(?:senpai|kun|chan|san|sama|sensei|dono|tan|pyon))\b",
                    form_m,
                    res,
                    flags=re.IGNORECASE
                )
                # Goły alias (wyłącznie dla encji jednoczłonowych)
                if not is_multi_token:
                    res = re.sub(
                        rf"\b(?:{al_re})\b",
                        form_m,
                        res,
                        flags=re.IGNORECASE
                    )
        return res

    def apply_canonical_alias_declension(
        self,
        text: str,
        source_en: str = "",
        keep_honorifics: bool = False
    ) -> str:
        """
        Wrapper instancyjny na substitute_canonical_honorific_alias (Standard 9.7, 2C.1).
        """
        return self.substitute_canonical_honorific_alias(
            text=text,
            source_en=source_en,
            series_bible=self,
            declensions=self.data.get("declensions") if hasattr(self, "data") and isinstance(self.data, dict) else None,
            characters=self.data.get("characters") if hasattr(self, "data") and isinstance(self.data, dict) else None,
            keep_honorifics=keep_honorifics,
        )

    def _validate_relation_entry_consistency(self) -> None:
        """
        Weryfikuje i sanityzuje spójność rejestru relacji skierowanych (X -> Y) pod kątem asymetrii T/V (Standard 9.4, 2C.5, R3.1):
        - Weryfikacja zwrotów poufałych i zażyłości relacji w rejestrze dyskursu, usunięcie fałszywego deskryptora hierarchicznego i oznaczenie jako 'reżim: POUFNY'.
        - Jeśli relacja jest oficjalna/formalna, oznacza jako 'reżim: FORMALNY'.
        - Zapewnia spójność rodzajową znacznika [KOBIETA/MĘŻCZYZNA (Adresat)] z rekordem P0 adresata.
        """
        if not hasattr(self, "data") or not isinstance(self.data, dict):
            return

        for rel_dict_name in ("relations", "relationships"):
            if rel_dict_name not in self.data or not isinstance(self.data[rel_dict_name], dict):
                continue
            for rel_k, rel_desc in list(self.data[rel_dict_name].items()):
                if "->" not in rel_k:
                    continue
                parts = rel_k.split("->")
                if len(parts) != 2:
                    continue
                source_char = parts[0].strip()
                target_char = parts[1].strip()

                desc_str = rel_desc.get("description", "") if isinstance(rel_desc, dict) else str(rel_desc)
                d_lower = desc_str.lower()

                is_informal = any(k in d_lower for k in ["per ty", "per-ty", "poufał", "koleżeńsk", "przyjaciel", "blisk", "nieformaln", "swobodn"])
                is_hierarchical = "relacja hierarchiczna" in d_lower or "hierarchiczn" in d_lower

                new_desc = desc_str
                # Czyszczenie ewentualnych osieroconych fragmentów po dawnych uszkodzeniach regexu
                if "-sama" in new_desc.lower():
                    new_desc = re.sub(r"',?\s*(?:eliminacja|z[a]kaz|wykluczon\w+)\s+hybryd.*?-sama\s*\]?\)?\]?", "", new_desc, flags=re.IGNORECASE).strip()
                new_desc = re.sub(r"',?\s*(?:eliminacja|z[a]kaz|wykluczon\w+)\s+hybryd[^]]*\]", "", new_desc, flags=re.IGNORECASE).strip()
                new_desc = re.sub(r",?\s*(?:eliminacja|z[a]kaz|wykluczon\w+)\s+hybryd[^]]*\]?", "", new_desc, flags=re.IGNORECASE).strip()
                new_desc = re.sub(r",?\s*wykluczona forma\s+'[^']*'\s*\([^)]*\)\s*\]?", "]", new_desc, flags=re.IGNORECASE).strip()
                new_desc = re.sub(r"\]\s*'", "]", new_desc).strip()
                new_desc = re.sub(r"'\s*,", ",", new_desc).strip()
                new_desc = re.sub(r"\s+", " ", new_desc).strip()
                if is_informal and is_hierarchical:
                    # Standard 9.5 (Operacja 2C.4): Dopasowanie pełnego bloku klauzuli hierarchicznej z zagnieżdżonym [Imię] aż do -sama]
                    if "-sama" in new_desc.lower():
                        new_desc = re.sub(r"(?:\\N|\s*\[)?RELACJA HIERARCHICZNA.*?-sama\s*\]?\)?\]?", "", new_desc, flags=re.IGNORECASE).strip()
                    new_desc = re.sub(r"(?:\\N|\s*\[)?RELACJA HIERARCHICZNA[^]]*\]?", "", new_desc, flags=re.IGNORECASE).strip()
                    new_desc = re.sub(r"\s+", " ", new_desc).strip()
                    if "reżim:" not in new_desc.lower():
                        new_desc = f"{new_desc} [reżim: POUFNY]".strip()
                    else:
                        new_desc = re.sub(r"reżim:\s*\w+", "reżim: POUFNY", new_desc, flags=re.IGNORECASE)
                elif is_informal:
                    if "reżim:" not in new_desc.lower():
                        new_desc = f"{new_desc} [reżim: POUFNY]".strip()
                    else:
                        new_desc = re.sub(r"reżim:\s*\w+", "reżim: POUFNY", new_desc, flags=re.IGNORECASE)
                elif any(k in d_lower for k in ["formaln", "oficjaln", "pan/pani", "dystans"]):
                    if "reżim:" not in new_desc.lower():
                        new_desc = f"{new_desc} [reżim: FORMALNY]".strip()

                ch_entry = self.get_character(target_char)
                if ch_entry and isinstance(ch_entry, dict):
                    p0_g = str(ch_entry.get("gender", "")).upper()
                    if p0_g == "FEMALE":
                        new_desc = re.sub(
                            r"\[MĘŻCZYZNA\s+\(Adresat[^\]]*\]",
                            "[KOBIETA (Adresat) - W 2. os. lp. 'ty' wymóg form żeńskich: byłaś / zrobiłaś / jesteś pewna]",
                            new_desc,
                            flags=re.IGNORECASE
                        )
                    elif p0_g == "MALE":
                        new_desc = re.sub(
                            r"\[KOBIETA\s+\(Adresat[^\]]*\]",
                            "[MĘŻCZYZNA (Adresat) - W 2. os. lp. 'ty' wymóg form męskich: byłeś / zrobiłeś / jesteś pewien]",
                            new_desc,
                            flags=re.IGNORECASE
                        )

                if new_desc != desc_str:
                    if isinstance(rel_desc, dict):
                        rel_desc["description"] = new_desc
                    else:
                        self.data[rel_dict_name][rel_k] = new_desc

            # Normalizacja relacji po oczyszczeniu przecieków promptów
            for sec in ("plot_anchors", "relationships", "relations"):
                if sec in self.data and isinstance(self.data[sec], dict):
                    for k, v in list(self.data[sec].items()):
                        if isinstance(v, str):
                            self.data[sec][k] = _normalize_negative_directive(v)

    def _rebuild_actor_aliases_index(self):
        """Buduje globalny indeks aliasów O(1) w SeriesBible z priorytetyzacją P0 i normalizacją fonetyczną."""
        self._actor_aliases_index = {}
        if not hasattr(self, "data") or not isinstance(self.data, dict) or "characters" not in self.data:
            return

        def _char_priority_key(item):
            name, entry = item
            if not isinstance(entry, dict):
                return (0, 0, 0)
            is_p0 = 1 if entry.get("priority") == "P0" else 0
            is_ver = 1 if entry.get("has_verified_gender") else 0
            conf = float(entry.get("confidence") or 0.0)
            return (is_p0, is_ver, conf)

        title_and_role_stopwords = {
            "lord", "lady", "prince", "princess", "king", "queen", "captain", "general",
            "commander", "doctor", "master", "saint", "sister", "brother", "father",
            "mother", "young", "kid", "old", "mr", "mrs", "ms", "książę", "księżniczka",
            "król", "królowa", "kapitan", "generał", "dowódca", "mistrz", "doktor",
            "święty", "święta", "siostra", "brat", "ojciec", "matka", "młody", "młoda",
            "stary", "stara", "pan", "pani"
        }

        # Identyfikacja kolizyjnych nazwisk z rozbieżnymi płciami
        surname_genders = defaultdict(set)
        for c_n, c_e in self.data["characters"].items():
            if "->" in c_n or not isinstance(c_e, dict):
                continue
            c_toks = extract_clean_speaker_name(c_n).split()
            if len(c_toks) > 1:
                s_tok = c_toks[-1].lower()
                s_norm = normalize_ascii_diacritics(s_tok)
                cg = str(c_e.get("gender") or "").upper()
                if cg in ("MALE", "FEMALE"):
                    surname_genders[s_tok].add(cg)
                    surname_genders[s_norm].add(cg)
        conflicting_surnames = {st for st, gs in surname_genders.items() if len(gs) > 1}

        sorted_chars = sorted(self.data["characters"].items(), key=_char_priority_key, reverse=True)
        for c_name, c_entry in sorted_chars:
            if "->" in c_name or not isinstance(c_entry, dict):
                continue
            candidates = list(c_entry.get("aliases", []))
            clean_c = extract_clean_speaker_name(c_name)
            if clean_c and clean_c not in candidates:
                candidates.append(clean_c)
            for tok in clean_c.split():
                tok_strip = tok.strip()
                if tok_strip and tok_strip.lower() not in conflicting_surnames and normalize_ascii_diacritics(tok_strip.lower()) not in conflicting_surnames:
                    if tok_strip not in candidates:
                        candidates.append(tok_strip)
            for al in candidates:
                al_low = al.lower().strip()
                al_folded = normalize_ascii_diacritics(al).lower().strip()
                if al_low in title_and_role_stopwords or al_folded in title_and_role_stopwords:
                    continue
                if len(al_low) < 2:
                    continue
                if len(al.split()) == 1 and (al_low in conflicting_surnames or al_folded in conflicting_surnames):
                    continue
                if al_low and al_low not in self._actor_aliases_index:
                    self._actor_aliases_index[al_low] = c_name
                if al_folded and al_folded not in self._actor_aliases_index:
                    self._actor_aliases_index[al_folded] = c_name
                al_low_f = al_low.replace("ph", "f")
                if al_low_f and al_low_f not in self._actor_aliases_index:
                    self._actor_aliases_index[al_low_f] = c_name
                    self._actor_aliases_index[al_low_f] = c_name
                al_folded_f = al_folded.replace("ph", "f")
                if al_folded_f and al_folded_f not in self._actor_aliases_index:
                    self._actor_aliases_index[al_folded_f] = c_name

    def save(self):
        """Saves current Series Bible state to disk (Thread-Safe)."""
        with self._lock:
            try:
                dump_data = copy.deepcopy(self.data)
                with open(self.file_path, "w", encoding="utf-8") as f:
                    json.dump(dump_data, f, ensure_ascii=False, indent=2)
                art_p = getattr(self, "artefakty_path", None)
                if art_p and art_p.parent.exists():
                    shutil.copy2(self.file_path, art_p)
            except Exception:
                logger.warning("Kopia bazy wiedzy do artefaktów zakończona wyjątkiem", exc_info=True)

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
        with self._lock:
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
        to the full canonical character name registered in the Series Bible.
        """
        if not name_or_stem:
            return ""
        s = name_or_stem.strip()
        s_lower = s.lower()
        norm_s = normalize_name_nfkd(s_lower)
        # 1. Direct lookup in registered hypocorisms
        with self._lock:
            hypo = dict(self.data.get("hypocorisms", {}))
            chars_keys = list(self.data.get("characters", {}).keys())
        if s in hypo:
            return hypo[s]
        for k, v in hypo.items():
            if k.lower() == s_lower or normalize_name_nfkd(k.lower()) == norm_s:
                return v
        # 2. Check if stem matches prefix of a confirmed character name
        for c in chars_keys:
            if "->" not in c:
                c_toks = c.split()
                if not c_toks:
                    continue
                c_first = c_toks[0]
                c_first_l = c_first.lower()
                norm_c_first = normalize_name_nfkd(c_first_l)
                if c_first_l == s_lower or norm_c_first == norm_s:
                    return c_first
                if (c_first_l.startswith(s_lower) or norm_c_first.startswith(norm_s)) and len(s_lower) >= 3:
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
        norm_clean = normalize_name_nfkd(clean)
        with self._lock:
            chars_keys = list(self.data.get("characters", {}).keys())
        for k in chars_keys:
            if "->" not in k:
                k_clean = extract_clean_speaker_name(k).strip().lower()
                if (
                    k.lower() == clean
                    or k_clean == clean
                    or normalize_name_nfkd(k.lower()) == norm_clean
                    or normalize_name_nfkd(k_clean) == norm_clean
                ):
                    return True
        return False

    def resolve_character_record(self, query_name: str) -> Optional[Dict[str, Any]]:
        """
        P0-First Canon Resolver (Standard 10.0.3, 2B.1, R1.9, R3.2):
        Rozwiązuje nazwę postaci lub adresata z bezwzględnym prymatem zweryfikowanych rekordów P0/P1.
        Krok 1: Przeszukuje characters pod kątem has_verified_gender=True lub priority in ('P0', 'P1')
                oraz gender in ('MALE', 'FEMALE'):
                - dopasowanie po kluczu głównym (i po normalizacji diakrytyków)
                - dopasowanie po liście aliases
                - dopasowanie po pierwszym tokenie (FirstName) jeśli nie koliduje z innymi postaciami.
        Krok 2: Fallback do niezweryfikowanych wpisów P2.
        """
        if not query_name:
            return None
        clean_q, explicit_g = normalize_actor_tag(str(query_name))
        clean_q = extract_clean_speaker_name(clean_q).strip()
        if not clean_q or is_sign_entity(clean_q) or clean_q.lower() in ("txt", "text", "sign", "title", "caption", "szyld", "napis"):
            return None

        TITLE_STOPWORDS = {
            "lord", "lady", "sir", "master", "pan", "pani", "książę", "ksiaze", "księżniczka", "ksiezniczka",
            "król", "krol", "królowa", "krolowa", "captain", "kapitan", "general", "generał",
            "commander", "dowódca", "dowodca", "doctor", "doktor", "mistrz", "mistrzyni",
            "saint", "święty", "swiety", "święta", "swieta", "sister", "brother", "father", "mother",
            "siostra", "brat", "ojciec", "matka", "young", "kid", "old", "mr", "mrs", "ms"
        }
        q_tokens = clean_q.split()
        if len(q_tokens) >= 2 and q_tokens[0].lower() in TITLE_STOPWORDS:
            clean_q = " ".join(q_tokens[1:]).strip()

        q_low = clean_q.lower()
        q_norm = normalize_ascii_diacritics(q_low)
        q_norm_f = q_norm.replace("ph", "f")

        ctx = getattr(self, "_lock", None)
        if ctx is None:
            ctx = contextlib.nullcontext()

        with ctx:
            chars = self.data.get("characters", {}) if hasattr(self, "data") and isinstance(self.data, dict) else {}
            if not chars:
                return None

            # Krok 1: Przeszukanie zweryfikowanych rekordów P0/P1
            p0_candidates = []
            for k, v in chars.items():
                if "->" in k or not isinstance(v, dict):
                    continue
                is_p0 = bool(v.get("has_verified_gender") or v.get("priority") in ("P0", "P1"))
                g = str(v.get("gender") or "").upper()
                if is_p0 and g in ("MALE", "FEMALE"):
                    p0_candidates.append((k, v))

            # 1a. Dokładne dopasowanie do klucza lub czystego klucza P0
            for k, v in p0_candidates:
                k_low = k.lower()
                k_clean = extract_clean_speaker_name(k).strip().lower()
                if q_low in (k_low, k_clean) or q_norm in (normalize_ascii_diacritics(k_low), normalize_ascii_diacritics(k_clean)):
                    res = dict(v)
                    res.setdefault("name", k)
                    return res

            # 1b. Dopasowanie do listy aliases P0
            for k, v in p0_candidates:
                aliases = v.get("aliases", [])
                for al in aliases:
                    al_s = str(al).strip().lower()
                    al_norm = normalize_ascii_diacritics(al_s)
                    if q_low == al_s or q_norm == al_norm or q_norm_f == al_norm.replace("ph", "f"):
                        res = dict(v)
                        res.setdefault("name", k)
                        return res

            # 1c. Dopasowanie pierwszego tokena (FirstName) do P0
            if len(clean_q.split()) == 1 and len(clean_q) >= 2:
                matching_p0_fn = []
                for k, v in p0_candidates:
                    k_toks = extract_clean_speaker_name(k).strip().split()
                    if k_toks:
                        fn = k_toks[0].lower()
                        if q_low == fn or q_norm == normalize_ascii_diacritics(fn):
                            matching_p0_fn.append((k, v))
                if len(matching_p0_fn) == 1:
                    k, v = matching_p0_fn[0]
                    res = dict(v)
                    res.setdefault("name", k)
                    return res
                elif len(matching_p0_fn) > 1:
                    g_set = {mv.get("gender") for mk, mv in matching_p0_fn}
                    if len(g_set) == 1:
                        k, v = matching_p0_fn[0]
                        res = dict(v)
                        res.setdefault("name", k)
                        return res

            # Krok 2: Fallback do niezweryfikowanych wpisów P2
            for k, v in chars.items():
                if "->" in k or not isinstance(v, dict):
                    continue
                if v.get("priority") == "P2" or not v.get("has_verified_gender"):
                    k_low = k.lower()
                    k_clean = extract_clean_speaker_name(k).strip().lower()
                    if q_low in (k_low, k_clean) or q_norm in (normalize_ascii_diacritics(k_low), normalize_ascii_diacritics(k_clean)):
                        res = dict(v)
                        res.setdefault("name", k)
                        return res
                    for al in v.get("aliases", []):
                        al_s = str(al).strip().lower()
                        if q_low == al_s or q_norm == normalize_ascii_diacritics(al_s):
                            res = dict(v)
                            res.setdefault("name", k)
                            return res

            return None

    def get_character(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Zwraca rekord postaci z self.data['characters'] dla podanego imienia lub aliasu.
        Używa P0-First Canon Resolver (resolve_character_record).
        """
        if not name:
            return None
        rec = self.resolve_character_record(name)
        if rec is not None:
            return rec
        lock = getattr(self, "_lock", None)
        ctx = lock if lock is not None else contextlib.nullcontext()
        with ctx:
            chars = self.data.get("characters", {})
            if name in chars and isinstance(chars[name], dict):
                return chars[name]
            name_l = name.strip().lower()
            char_items = list(chars.items())
            for k, v in char_items:
                if k.lower() == name_l and isinstance(v, dict):
                    return v
                if isinstance(v, dict):
                    aliases = [str(a).lower() for a in v.get("aliases", [])]
                    if name_l in aliases:
                        return v

            # Standard 9.5 (Operacja 2B.1): Sprawdzenie dwujęzycznych ekwiwalencji ról
            if name_l in BILINGUAL_ROLE_EQUIVALENCES:
                pl_equiv = BILINGUAL_ROLE_EQUIVALENCES[name_l]
                for k, v in char_items:
                    if k.lower() == pl_equiv and isinstance(v, dict):
                        return v
                    if isinstance(v, dict):
                        aliases = [str(a).lower() for a in v.get("aliases", [])]
                        if pl_equiv in aliases:
                            return v
            for en_role, pl_role in BILINGUAL_ROLE_EQUIVALENCES.items():
                if pl_role == name_l:
                    for k, v in char_items:
                        if k.lower() == en_role and isinstance(v, dict):
                            return v
                        if isinstance(v, dict):
                            aliases = [str(a).lower() for a in v.get("aliases", [])]
                            if en_role in aliases:
                                return v
            return None

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

        # Specific numbered/lettered boy/girl role tags are always gender-locked
        if re.match(r"^(?:boy|chłopiec|chłopak|man|mężczyzna)\s+[a-z0-9]+$", n_l):
            return "MALE"
        if re.match(r"^(?:girl|dziewczynka|dziewczyna|woman|kobieta)\s+[a-z0-9]+$", n_l):
            return "FEMALE"

        # Pass 0a: Canonical inheritance for age, temporal, and state prefixes
        base_char_name = extract_base_canonical_name(clean or name)
        if base_char_name and base_char_name.lower() != n_l:
            base_ident = self.get_character_identity(base_char_name)
            if base_ident:
                return "MALE" if base_ident.true_gender == "MASCULINE" else "FEMALE"
            base_gender = self.get_character_gender(base_char_name, allow_generic_nouns=allow_generic_nouns)
            if base_gender in ("MALE", "FEMALE"):
                return base_gender

                # Pass 0c: P0-First Canonical Character Resolution (Standard 10.0.3, 2B.1)
        rec = self.resolve_character_record(clean or name)
        if rec and isinstance(rec, dict):
            g = str(rec.get("gender") or "").upper()
            if g in ("MALE", "FEMALE"):
                return g

# Pass 0b: Kinship / possessive relation suffixes ([Owner]'s Son/Daughter/Kid)
        rel_gender, rel_conf = resolve_possessive_relation_gender(
            clean or name,
            is_flashback=any(fb in n_l for fb in ("flashback", "retrospekcj", "past")),
            series_bible=self
        )
        if rel_gender in ("MALE", "FEMALE"):
            return rel_gender

        if self.is_non_character_entity(name) or n_l in ETHNONYMS_AND_COLLECTIVES:
            return "UNKNOWN"

        # Inherent lexical gender check
        tokens = set(re.findall(r"\b[a-ząćęłńóśźżA-ZĄĆĘŁŃÓŚŹŻ]+\b", n_l))
        if allow_generic_nouns:
            if n_l in INHERENT_FEMALE_NOUNS or any(t in INHERENT_FEMALE_NOUNS for t in tokens):
                return "FEMALE"
            if n_l in INHERENT_MALE_NOUNS or any(t in INHERENT_MALE_NOUNS for t in tokens):
                return "MALE"

        with self._lock:
            chars_items = list(self.data.get("characters", {}).items())
            rels_keys_str = " ".join(list(self.data.get("relationships", {}).keys())).lower()

        def _extract_gender_from_val(v) -> Optional[str]:
            if isinstance(v, dict):
                raw_g = str(v.get("gender") or "").strip().lower()
                if raw_g in ("female", "kobieta", "female_group"):
                    return "FEMALE"
                if raw_g in ("male", "mężczyzna", "male_group"):
                    return "MALE"
                if raw_g in ("neutral", "bezpłciowy"):
                    return "NEUTRAL"

            desc_v = str(v.get("description", "") if isinstance(v, dict) else v).lower()
            # Strip negative prohibition clauses (e.g. 'eliminacja form żeńskich', 'eliminacja form męskich')
            desc_clean = re.sub(r"\b(?:eliminacja|blokada|nie|brak)\s+[^.!?\n]*?(?:żeńsk\w*|męsk\w*|kobiet\w*|mężczyzn\w*)", "", desc_v)

            raw_desc = str(v.get("description", "") if isinstance(v, dict) else v)
            # Check structured canonical tag first: [KOBIETA (Adresat)...] or [MĘŻCZYZNA (Adresat)...]
            m_tag = re.search(r"\[(KOBIETA|MĘŻCZYZNA)\s+\(Adresat(?:ka|ce|ki|ek|om|ami|ach|em|owi)?\)", raw_desc, re.IGNORECASE)
            if m_tag:
                return "FEMALE" if m_tag.group(1).upper() == "KOBIETA" else "MALE"

            # 1. Primary lead gender tag at start of description or in [TAG]
            m_lead = re.match(r"^\s*\[?(kobieta|mężczyzna|female|male)\b", desc_clean)
            if m_lead:
                lead_g = m_lead.group(1).lower()
                if lead_g in ("kobieta", "female"):
                    return "FEMALE"
                if lead_g in ("mężczyzna", "male"):
                    return "MALE"

            if re.search(r"\b\[kobieta\b", desc_clean) or re.search(r"\(kobieta\)", desc_clean):
                return "FEMALE"
            if re.search(r"\b\[mężczyzna\b", desc_clean) or re.search(r"\(mężczyzna\)", desc_clean):
                return "MALE"

            # 2. General keywords in cleaned description
            has_f = is_female_role_text(desc_clean) or any(w in desc_clean for w in FEMALE_ROLE_KEYWORDS)
            has_m = is_male_role_text(desc_clean) or any(w in desc_clean for w in MALE_ROLE_KEYWORDS)
            if has_f and not has_m:
                return "FEMALE"
            if has_m and not has_f:
                return "MALE"
            if has_f and has_m:
                f_pos = None
                m_pos = None
                m_f = RE_FEMALE_ROLE.search(desc_clean)
                if m_f:
                    f_pos = (m_f.start(), m_f.end() - m_f.start())
                else:
                    f_matches = [(desc_clean.find(w), len(w)) for w in FEMALE_ROLE_KEYWORDS if w in desc_clean]
                    if f_matches:
                        f_pos = min(f_matches, key=lambda x: (x[0], -x[1]))

                m_m = RE_MALE_ROLE.search(desc_clean)
                if m_m:
                    m_pos = (m_m.start(), m_m.end() - m_m.start())
                else:
                    m_matches = [(desc_clean.find(w), len(w)) for w in MALE_ROLE_KEYWORDS if w in desc_clean]
                    if m_matches:
                        m_pos = min(m_matches, key=lambda x: (x[0], -x[1]))

                if f_pos and not m_pos:
                    return "FEMALE"
                if m_pos and not f_pos:
                    return "MALE"
                if f_pos and m_pos:
                    if f_pos[0] < m_pos[0]:
                        return "FEMALE"
                    elif m_pos[0] < f_pos[0]:
                        return "MALE"
                    else:
                        return "FEMALE" if f_pos[1] >= m_pos[1] else "MALE"
            return None

        # Pass 1: Exact character names only (e.g. 'Tanaka', 'Kenji Tanaka')
        norm_nl = normalize_name_nfkd(n_l)
        tokens_set = set(n_l.split())
        tokens_set_f = set(t.replace("ph", "f") for t in tokens_set)
        for k, v in chars_items:
            if "->" not in k:
                k_l = k.lower()
                clean_k = extract_clean_speaker_name(k_l)
                clean_tokens_set = set(clean_k.split())
                clean_tokens_set_f = set(t.replace("ph", "f") for t in clean_tokens_set)
                if (
                    k_l == n_l
                    or clean_k == n_l
                    or normalize_name_nfkd(k_l) == norm_nl
                    or normalize_name_nfkd(clean_k) == norm_nl
                    or k_l.replace("ph", "f") == n_l.replace("ph", "f")
                    or clean_k.replace("ph", "f") == n_l.replace("ph", "f")
                    or (tokens_set and tokens_set == clean_tokens_set)
                    or (tokens_set_f and tokens_set_f == clean_tokens_set_f)
                ):
                    g = _extract_gender_from_val(v)
                    if g:
                        return g

        # Pass 1.5: O(1) Fast Direct Alias Matching
        if not hasattr(self, "_actor_aliases_index") or not self._actor_aliases_index:
            self._rebuild_actor_aliases_index()
        matched_c = None
        if hasattr(self, "_actor_aliases_index") and self._actor_aliases_index:
            matched_c = (
                self._actor_aliases_index.get(n_l)
                or self._actor_aliases_index.get(norm_nl)
                or self._actor_aliases_index.get(n_l.replace("ph", "f"))
                or self._actor_aliases_index.get(norm_nl.replace("ph", "f"))
            )
        if not matched_c and hasattr(self, "data") and isinstance(self.data, dict) and "characters" in self.data:
            self._rebuild_actor_aliases_index()
            matched_c = (
                self._actor_aliases_index.get(n_l)
                or self._actor_aliases_index.get(norm_nl)
                or self._actor_aliases_index.get(n_l.replace("ph", "f"))
                or self._actor_aliases_index.get(norm_nl.replace("ph", "f"))
            )
        if matched_c and matched_c in self.data.get("characters", {}):
            cand_g = _extract_gender_from_val(self.data["characters"][matched_c])
            if cand_g:
                return cand_g

        # Pass 2: Token / surname matches with collision detection (e.g. 'Tanaka' matching 'Kenji Tanaka' and 'Hanako Tanaka')
        token_matches = []
        for k, v in chars_items:
            if "->" not in k:
                k_l = k.lower()
                k_tokens = k_l.split()
                norm_tokens_k = [normalize_name_nfkd(tok) for tok in k_tokens]
                if n_l in k_tokens or norm_nl in norm_tokens_k:
                    g = _extract_gender_from_val(v)
                    if g:
                        token_matches.append((k, g))

        if token_matches:
            genders_found = set(g for _, g in token_matches)
            if len(genders_found) == 1:
                return next(iter(genders_found))
            # Collision: multiple characters share surname with different genders
            # Check P0 / verified priority: prioritize candidate with confirmed ontological status
            p0_candidates = [
                (cand_k, cand_g) for cand_k, cand_g in token_matches
                if isinstance(self.data.get("characters", {}).get(cand_k), dict)
                and (self.data["characters"][cand_k].get("priority") == "P0" or self.data["characters"][cand_k].get("has_verified_gender"))
            ]
            if len(p0_candidates) == 1:
                return p0_candidates[0][1]

            # Check relationships: prioritize candidate active as primary interpersonal entity
            for cand_k, cand_g in token_matches:
                if cand_k.lower() in rels_keys_str:
                    return cand_g
            return "UNKNOWN"

        # Onomastic female / male name check (for named characters when series records don't specify)
        if not is_generic_actor_or_category(n_l):
            if (
                n_l in CANONICAL_MALE_NAMES
                or any(t in CANONICAL_MALE_NAMES for t in tokens)
                or n_l in MALE_EXCEPTIONS_ON_A
                or any(t in MALE_EXCEPTIONS_ON_A for t in tokens)
                or has_japanese_male_name_suffix(n_l)
                or any(has_japanese_male_name_suffix(t) for t in tokens)
                or is_official_or_court_consonant_name(n_l, series_bible=self)
                or any(is_official_or_court_consonant_name(t, series_bible=self) for t in tokens)
            ):
                return "MALE"
            if is_inherently_female_name(n_l, series_bible=self) or any(is_inherently_female_name(t, series_bible=self) for t in tokens):
                return "FEMALE"

        return "UNKNOWN"

    def get_character_age_class(self, name: str) -> str:
        """
        Returns 'CHILD', 'ADULT', 'ELDERLY', or 'UNKNOWN' based on Series Bible records and lexical patterns.
        """
        if not name:
            return "UNKNOWN"
        clean = extract_clean_speaker_name(name)
        n_l = (clean or name).strip().lower()
        if any(w in n_l for w in ["dziewczynka", "chłopiec", "dziecko", "mała", "mały", "girl", "boy", "kid", "child", "bocchan", "bozu", "kozo"]):
            return "CHILD"
        if any(w in n_l for w in ["staruszek", "staruszka", "dziadek", "babcia", "elderly", "old man", "old woman"]):
            return "ELDERLY"
        chars = self.get_characters_snapshot() if hasattr(self, "get_characters_snapshot") else (self.data.get("characters", {}) if hasattr(self, "data") else {})
        for k, v in list(chars.items()):
            if "->" not in k:
                k_l = k.lower()
                clean_k = extract_clean_speaker_name(k_l)
                if k_l == n_l or clean_k == n_l or n_l in k_l.split():
                    desc_v = str(v.get("description", "") if isinstance(v, dict) else v).lower()
                    if any(w in desc_v for w in ["dziecko", "dziewczynka", "chłopiec", "child", "young girl", "little girl", "young boy", "little boy"]):
                        return "CHILD"
                    if any(w in desc_v for w in ["staruszek", "staruszka", "dziadek", "babcia", "elderly", "old man", "old woman", "senior"]):
                        return "ELDERLY"
                    if any(w in desc_v for w in ["dorosły", "kobieta", "mężczyzna", "adult"]):
                        return "ADULT"
        return "UNKNOWN"

    def is_all_female_cast(self, cast: Any, min_size: int = 2) -> bool:
        """
        Returns True if all characters in the given cast are confirmed FEMALE and cast has at least min_size members.
        Excludes generic background/actor nouns from false positive validation.
        """
        named = [str(c).strip() for c in cast if c and not is_generic_actor_or_category(str(c).strip())]
        if len(named) < min_size:
            return False
        return all(self.get_character_gender(c, allow_generic_nouns=False) == "FEMALE" for c in named)

    def is_all_male_cast(self, cast: Any, min_size: int = 2) -> bool:
        """
        Returns True if all characters in the given cast are confirmed MALE and cast has at least min_size members.
        Excludes generic background/actor nouns from false positive validation.
        """
        named = [str(c).strip() for c in cast if c and not is_generic_actor_or_category(str(c).strip())]
        if len(named) < min_size:
            return False
        return all(self.get_character_gender(c, allow_generic_nouns=False) == "MALE" for c in named)

    def get_dual_pair_gender_type(self, names: Any) -> str:
        """
        Returns 'DUAL_FEMALE', 'DUAL_MALE', 'DUAL_MIXED', or 'UNKNOWN' for a pair of characters.
        """
        if not names:
            return "UNKNOWN"
        named = [str(c).strip() for c in names if c and not is_generic_actor_or_category(str(c).strip())]
        clean_names = [extract_clean_speaker_name(n).strip() for n in named]
        # Deduplicate while preserving unique named characters
        unique_names = []
        for n in clean_names:
            if n and n.lower() not in [u.lower() for u in unique_names]:
                unique_names.append(n)
        if len(unique_names) != 2:
            return "UNKNOWN"
        g1 = self.get_character_gender(unique_names[0], allow_generic_nouns=False)
        g2 = self.get_character_gender(unique_names[1], allow_generic_nouns=False)
        if g1 == "FEMALE" and g2 == "FEMALE":
            return "DUAL_FEMALE"
        elif g1 == "MALE" and g2 == "MALE":
            return "DUAL_MALE"
        elif (g1 == "FEMALE" and g2 == "MALE") or (g1 == "MALE" and g2 == "FEMALE"):
            return "DUAL_MIXED"
        return "UNKNOWN"

    @staticmethod
    def sanitize_pronominal_somatic_possession(text: str) -> str:
        return sanitize_pronominal_somatic_possession(text)

    @staticmethod
    def naturalize_adjacency_rejoinder(prior_q: str, resp: str) -> str:
        return naturalize_adjacency_rejoinder(prior_q, resp)

    @staticmethod
    def sanitize_deictic_motion_vector(text: str) -> str:
        return sanitize_deictic_motion_vector(text)

    @staticmethod
    def sanitize_sensory_pleonasm(text: str) -> str:
        return sanitize_sensory_pleonasm(text)

    @staticmethod
    def sanitize_closed_idioms_and_prepositions(text: str) -> str:
        return sanitize_closed_idioms_and_prepositions(text)

    def can_inflect_feminine_instrumental_after_z(self, name: str, preceding_text: str = "", context: Optional[str] = None) -> bool:
        """Dwupoziomowa bramka bezpieczeństwa dla żeńskiego narzędnika -ą po przyimku pochodzenia z (Klaster C)."""
        return is_feminine_instrumental_after_z_allowed(name, preceding_text=preceding_text, series_bible=self, context=context)

    def fix_undecorated_names(self, text: str, character_names: Optional[List[str]] = None) -> str:
        """Koryguje brak fleksji imion męskich i żeńskich po przyimkach z dwupoziomową bramką Klastra C."""
        return fix_undecorated_names(text, character_names=character_names, series_bible=self)

    @staticmethod
    def sanitize_toponymic_origin_and_companionship(text: str, custom_glossary: Optional[Dict[str, str]] = None) -> str:
        """Dwupoziomowa sanitizacja narzędnika toponimów i antroponimów po przyimkach z/ze."""
        return sanitize_toponymic_origin_and_companionship(text, custom_glossary=custom_glossary)

    def is_female_group_speaker(self, speaker_name: str) -> bool:
        """
        Returns True if the speaker label or category represents a confirmed female group
        (e.g. 'grupa_kobiet', 'zakonnice', 'dziewczęta', 'uczennice', 'służące', 'kobiety', 'matki').
        """
        if not speaker_name:
            return False
        spk_clean = extract_clean_speaker_name(speaker_name).strip().lower()
        if any(w in spk_clean for w in [
            "grupa_kobiet", "grupa kobiet", "dziewczęta", "dziewczyny", "kobiety",
            "uczennice", "kapłanki", "zakonnice", "służące", "siostry", "matki", "damy dworu"
        ]):
            return True
        return False

    def register_speaker_entity_type(self, name: str, entity_type: str) -> None:
        """
        Registers speaker grammatical identity type in SeriesBible (Filar CLXXVI - 0.00 PLN).
        entity_type: 'COLLECTIVE_VIRILE' | 'COLLECTIVE_NONVIRILE' | 'MAJESTIC_FEMALE' | 'MAJESTIC_MALE' | 'INDIVIDUAL'
        """
        if not name:
            return
        if "speaker_entity_types" not in self.data:
            self.data["speaker_entity_types"] = {}
        cl_name = extract_clean_speaker_name(name).strip().lower()
        self.data["speaker_entity_types"][cl_name] = entity_type

    def get_speaker_entity_type(self, speaker_name: str) -> str:
        """
        Retrieves speaker grammatical identity type (Filar CLXXVI - 0.00 PLN).
        Recognizes canonical known entities (e.g. Louis Arneb -> COLLECTIVE_VIRILE).
        """
        if not speaker_name:
            return "INDIVIDUAL"
        cl_name = extract_clean_speaker_name(speaker_name).strip().lower()
        with self._lock:
            types_items = list(self.data.get("speaker_entity_types", {}).items())
            chars_items = list(self.data.get("characters", {}).items())
        for k, v in types_items:
            if k == cl_name or k in cl_name or cl_name in k:
                return v

        # Canonical known patterns across major anime / literature
        if any(w in cl_name for w in ["louis arneb", "rui arunebu", "rui arnebu", "arneb", "arunebu", "żarłoczność", "zarlocznosc"]):
            return "COLLECTIVE_VIRILE"
        char_desc = ""
        for k, v in chars_items:
            if "->" not in k:
                k_l = k.lower()
                clean_k = extract_clean_speaker_name(k_l)
                if k_l == cl_name or clean_k == cl_name or cl_name in k_l:
                    char_desc = str(v.get("description", "") if isinstance(v, dict) else v).lower()
                    break

        if any(w in cl_name for w in ["królowa", "krolowa", "cesarzowa", "queen", "empress"]) or "monarchini" in char_desc:
            if "pluralis" in char_desc or "majestat" in char_desc or "my" in char_desc or any(w in cl_name for w in ["królowa", "krolowa", "cesarzowa"]):
                return "MAJESTIC_FEMALE"
        if any(w in cl_name for w in ["cesarz", "król", "krol", "emperor", "king"]) or "monarcha" in char_desc:
            if "pluralis" in char_desc or "majestat" in char_desc or "my" in char_desc or any(w in cl_name for w in ["cesarz", "król", "krol"]):
                return "MAJESTIC_MALE"

        return "INDIVIDUAL"

    def is_collective_virile_speaker(self, speaker_name: str) -> bool:
        """
        Returns True if the speaker represents a mixed/virile collective entity
        (e.g. Louis Arneb in Re:Zero, speaking for Ley, Roy and herself).
        Requires 1st-person plural virile agreement (-liśmy, byliśmy), immune to female scene overrides!
        """
        return self.get_speaker_entity_type(speaker_name) == "COLLECTIVE_VIRILE"

    def is_collective_nonvirile_speaker(self, speaker_name: str) -> bool:
        """
        Returns True if the speaker represents an exclusively female collective entity.
        """
        return self.get_speaker_entity_type(speaker_name) == "COLLECTIVE_NONVIRILE"

    def is_majestic_female_speaker(self, speaker_name: str) -> bool:
        """
        Returns True if the speaker is a female monarch using Pluralis Maiestatis.
        Requires 1st-person plural non-virile agreement (-łyśmy, byłyśmy), even in mixed/neutral scenes!
        """
        return self.get_speaker_entity_type(speaker_name) == "MAJESTIC_FEMALE"

    def is_majestic_male_speaker(self, speaker_name: str) -> bool:
        """
        Returns True if the speaker is a male monarch using Pluralis Maiestatis.
        """
        return self.get_speaker_entity_type(speaker_name) == "MAJESTIC_MALE"

    def infer_scene_cast_from_text(self, scene_texts: List[str], whisper_texts: Optional[List[str]] = None) -> Tuple[Set[str], Optional[str]]:
        """
        Scans dialogue lines within an anonymous scene (where ev.name is blank) for character mentions,
        vocatives, and distinctive plot anchors to determine the scene cast and gender exclusivity (0.00 PLN).
        Universal across all 16 series via dynamic scanning of characters and relationships.
        Returns: (detected_cast_set, 'FEMALE' | 'MALE' | None)
        """
        if isinstance(scene_texts, str):
            scene_texts = [scene_texts]
        if not scene_texts and not whisper_texts:
            return set(), None

        combined_text = " ".join(scene_texts or [])
        combined_lower = combined_text.lower()
        detected_cast: Set[str] = set()

        with self._lock:
            chars_keys = list(self.data.get("characters", {}).keys())
        for k in chars_keys:
            if "->" in k:
                continue
            parts = [p.strip() for p in k.split("/") if len(p.strip()) >= 3]
            for p in parts:
                # Stem pre-filter: if stem of p (first 3 chars) is not in text, none of its forms can match
                p_stem = normalize_ascii_diacritics(p).lower()[:3]
                c_rec = self.data.get("characters", {}).get(k, {})
                if len(p_stem) >= 3 and p_stem not in combined_lower:
                    aliases = c_rec.get("aliases", []) if isinstance(c_rec, dict) else []
                    if not any(isinstance(al, str) and normalize_ascii_diacritics(al).lower()[:3] in combined_lower for al in aliases):
                        continue
                if is_generic_actor_or_category(p) or self.is_non_character_entity(p):
                    continue
                # Generate transliteration, aliases and phonetic variants dynamically
                target_tokens = {p, normalize_ascii_diacritics(p)}
                if isinstance(c_rec, dict):
                    for al in c_rec.get("aliases", []):
                        if isinstance(al, str) and len(al.strip()) >= 3:
                            target_tokens.add(al.strip())
                            target_tokens.add(normalize_ascii_diacritics(al.strip()))
                    decl_dict = c_rec.get("declension")
                    if isinstance(decl_dict, dict):
                        for form in decl_dict.values():
                            if isinstance(form, str) and len(form.strip()) >= 3:
                                target_tokens.add(form.strip())
                auto_decl = generate_polish_name_declension(p)
                if isinstance(auto_decl, dict):
                    for form in auto_decl.values():
                        if isinstance(form, str) and len(form.strip()) >= 3:
                            target_tokens.add(form.strip())

                matched_any = False
                for v in target_tokens:
                    v_esc = re.escape(v)
                    # Exclude 3rd-person genealogy, deceased houses or historical reference (e.g. Tolui's lineage / rodu Tołuja)
                    is_genealogy = bool(re.search(
                        rf"\b(?:houses?|lineages?|lineage|house|tomb|tombs|memory|death|grave|graves|ród|rodu|rody|rodów|grobu|grobów|pamięć|pamięci|wola|woli)\s+(?:of\s+|z\s+|wielkiego\s+chana\s+|grand\s+khan'?s?\s+)?[^.!?\n]*?\b{v_esc}\b|\b{v_esc}'s\s+(?:lineage|lineages|house|houses|memory|tomb|tombs|grave|graves|death|will)\b",
                        combined_text,
                        re.IGNORECASE
                    ))
                    if is_genealogy:
                        continue
                    if re.search(rf"\b{v_esc}\b", combined_text, re.IGNORECASE):
                        matched_any = True
                        break

                if matched_any:
                    detected_cast.add(p)

        # Dynamic relationship scanning across all series (e.g. A -> B where both are female/male)
        with self._lock:
            rels_keys = list(self.data.get("relationships", {}).keys()) if hasattr(self, "data") else []
        for rel_k in rels_keys:
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


        # Series-scoped plot anchors and context for anonymous historical scenes (0.00 PLN)
        if getattr(self, "anime_title", None) and "tenmaku" in str(self.anime_title).lower():
            if any(kw in combined_lower for kw in [
                "sorkaktani", "sorghaghtani", "cztery tysiące jurt", "four thousand tents"
            ]):
                detected_cast.add("Boraqchin")
                detected_cast.add("Möge")
                for m_male_kw in "ögedei ogedei tolui chagatai jochi temüge temuge".split():
                    for c in list(detected_cast):
                        if c.lower() == m_male_kw:
                            detected_cast.discard(c)

        # Audio Whisper Ground Truth integration (if available)
        combined_whisper = " ".join(whisper_texts or []).lower() if whisper_texts else ""
        has_female_audio = any(m in combined_whisper for m in ["warawa", "妾", "atashi", "あたし", "atai", "あたい", "wa yo", "わよ", "no yo", "のよ", "kashira", "かしら"])
        has_male_audio = any(m in combined_whisper for m in ["ore", "俺", "boku", "僕", "washi", "わし", "sessha", "拙者", "da zo", "だぞ", "da ze", "だぜ"])

        gender_exclusive = None
        if len(detected_cast) >= 2:
            if self.is_all_female_cast(detected_cast, min_size=2):
                gender_exclusive = "FEMALE"
            elif self.is_all_male_cast(detected_cast, min_size=2):
                gender_exclusive = "MALE"

        return detected_cast, gender_exclusive

    def audit_speaker_metadata_against_audio(
        self,
        actor_name: str,
        audio_gender: Optional[str] = None,
        f0_hz: Optional[float] = None,
        whisper_gender: Optional[str] = None,
        scene_gender: Optional[str] = None
    ) -> Tuple[str, bool]:
        """
        Audits untrusted actor tag from external fansub (.ass) against physical audio ground truth (0.00 PLN).
        Returns: (resolved_gender, is_contaminated)
        - If tag indicates MALE (e.g. 'Ögedei'), but audio F0 (>=185Hz / alt żeński), Whisper markers ('FEMALE'),
          or pre-pass scene exclusivity ('FEMALE') confirm female speaker, tag is demoted to 'UNTRUSTED_CONTRADICTION'
          and resolved_gender becomes 'FEMALE'.
        """
        if not actor_name:
            return (audio_gender or whisper_gender or scene_gender or "UNKNOWN"), False

        actor_clean = extract_clean_speaker_name(actor_name).strip()

        speaker_tokens = set(re.findall(r"\b\w+\b", actor_clean.lower()))
        if speaker_tokens & (SECONDARY_LEXICAL_MALE_NOUNS | SECONDARY_LEXICAL_FEMALE_NOUNS):
            canonical_gender = "MALE" if speaker_tokens & SECONDARY_LEXICAL_MALE_NOUNS else "FEMALE"
            return canonical_gender, False

        if is_generic_actor_or_category(actor_name):
            return (audio_gender or whisper_gender or scene_gender or "UNKNOWN"), False

        canon_gender = self.get_character_gender(actor_clean, allow_generic_nouns=False)

        # Contamination condition: Canonical tag contradicted by objective physical acoustic evidence
        has_female_audio = (audio_gender == "FEMALE") or (f0_hz is not None and f0_hz >= 185.0) or (whisper_gender == "FEMALE")
        has_male_audio = (audio_gender == "MALE") or (f0_hz is not None and f0_hz <= 140.0) or (whisper_gender == "MALE")

        # Check if character is marked as a young boy or cross-gender role (voiced by female seiyū)
        char_desc_lower = ""
        b_val = {}
        if hasattr(self, "data") and "characters" in self.data:
            chars_dict = self.data["characters"]
            b_val = chars_dict.get(actor_clean)
            if not b_val:
                norm_act = normalize_name_nfkd(actor_clean.lower())
                for ck, cv in chars_dict.items():
                    if ck.lower() == actor_clean.lower() or normalize_name_nfkd(ck.lower()) == norm_act:
                        b_val = cv
                        break
            if isinstance(b_val, dict):
                char_desc_lower = b_val.get("description", "").lower()
            elif b_val:
                char_desc_lower = str(b_val).lower()

        is_p0 = bool(isinstance(b_val, dict) and (b_val.get("priority") == "P0" or b_val.get("has_verified_gender") is True))
        is_boy_or_crossgender = any(k in char_desc_lower for k in BOY_ROLE_KEYWORDS) or \
                                any(k in actor_clean.lower() for k in BOY_ROLE_KEYWORDS) or \
                                any(k in actor_clean.lower() for k in ["chłopiec", "chłopak", "boy", "bocchan", "lad", "kid", "chojumaru"])

        is_female_space = (scene_gender == "FEMALE")
        is_male_space = (scene_gender == "MALE")

        if canon_gender == "MALE" and is_boy_or_crossgender:
            # Young boy voiced by female seiyū:
            # Physical acoustic F0 cannot override canonical male character.
            # Only override if the entire scene is proven to be an exclusively female narrative space.
            if not is_female_space:
                return "MALE", False

        # Low-pitch female protection (matron, elderly, or raspy female seiyū)
        is_low_pitch_fem = (hasattr(self, "is_low_pitch_female") and self.is_low_pitch_female(actor_clean)) or any(k in char_desc_lower for k in [
            "starsza", "dojrzała", "babcia", "matrona", "cesarzowa", "chatun", "wiedźma", "ochrypły alt", "alt starszej"
        ])
        if canon_gender == "FEMALE" and is_low_pitch_fem:
            # Mature / raspy female voice: low acoustic F0 is natural, canonical gender is FEMALE
            if not is_male_space:
                return "FEMALE", False

        if canon_gender == "MALE" and (has_female_audio or is_female_space):
            return "FEMALE", True
        elif canon_gender == "FEMALE" and (has_male_audio or is_male_space):
            return "MALE", True

        return (canon_gender if canon_gender != "UNKNOWN" else (audio_gender or whisper_gender or scene_gender or "UNKNOWN")), False

    def audit_speaker_metadata_with_details(
        self,
        actor_name: str,
        audio_gender: Optional[str] = None,
        f0_hz: Optional[float] = None,
        whisper_gender: Optional[str] = None,
        scene_gender: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Detailed version of audit_speaker_metadata_against_audio returning full epistemic metadata:
        - resolved_gender: str
        - is_contaminated: bool
        - applied_gender: str
        - gender_source: 'SERIES_BIBLE_P0' | 'SERIES_BIBLE' | 'ACOUSTIC'
        - acoustic_prior_rejected: bool
        """
        res_g, is_cont = self.audit_speaker_metadata_against_audio(
            actor_name, audio_gender=audio_gender, f0_hz=f0_hz, whisper_gender=whisper_gender, scene_gender=scene_gender
        )
        actor_clean = extract_clean_speaker_name(actor_name).strip() if actor_name else ""
        canon_g = self.get_character_gender(actor_clean, allow_generic_nouns=False)

        char_desc_lower = ""
        b_val = {}
        if hasattr(self, "data") and "characters" in self.data:
            chars_dict = self.data["characters"]
            b_val = chars_dict.get(actor_clean)
            if not b_val:
                norm_act = normalize_name_nfkd(actor_clean.lower())
                for ck, cv in chars_dict.items():
                    if ck.lower() == actor_clean.lower() or normalize_name_nfkd(ck.lower()) == norm_act:
                        b_val = cv
                        break
            if isinstance(b_val, dict):
                char_desc_lower = b_val.get("description", "").lower()
            elif b_val:
                char_desc_lower = str(b_val).lower()

        is_p0 = bool(isinstance(b_val, dict) and (b_val.get("priority") == "P0" or b_val.get("has_verified_gender") is True))
        is_boy_or_crossgender = any(k in char_desc_lower for k in BOY_ROLE_KEYWORDS) or \
                                any(k in actor_clean.lower() for k in BOY_ROLE_KEYWORDS) or \
                                any(k in actor_clean.lower() for k in ["chłopiec", "chłopak", "boy", "bocchan", "lad", "kid", "chojumaru"])

        has_female_audio = (audio_gender == "FEMALE") or (f0_hz is not None and f0_hz >= 185.0) or (whisper_gender == "FEMALE")
        acoustic_rejected = bool(has_female_audio and res_g == "MALE" and (is_p0 or is_boy_or_crossgender))
        gender_source = "SERIES_BIBLE_P0" if (canon_g == "MALE" and (is_p0 or is_boy_or_crossgender)) else ("SERIES_BIBLE" if canon_g != "UNKNOWN" else "ACOUSTIC")

        return {
            "resolved_gender": res_g,
            "is_contaminated": is_cont,
            "applied_gender": res_g,
            "gender_source": gender_source,
            "acoustic_prior_rejected": acoustic_rejected
        }

    def register_tv_transition(self, char_a: str, char_b: str, new_tv_state: str, ep_idx: int = 0) -> None:
        """
        Registers an authorized narrative T-V transition between two characters (e.g. from FORMAL to INFORMAL).
        Prevents linter and memory from treating emotional intimate agreements as accidental drift errors.
        """
        if not char_a or not char_b:
            return
        if not hasattr(self, "data") or self.data is None:
            self.data = {}
        if "tv_transitions" not in self.data:
            self.data["tv_transitions"] = {}
        pair_key = " <-> ".join(sorted([char_a.strip().lower(), char_b.strip().lower()]))
        self.data["tv_transitions"][pair_key] = {
            "state": new_tv_state.upper(),
            "ep_idx": ep_idx
        }

    def get_authorized_tv_state(self, char_a: str, char_b: str) -> Optional[str]:
        """
        Returns authorized T-V state if an intentional narrative transition was registered.
        """
        if not char_a or not char_b or not hasattr(self, "data") or not self.data:
            return None
        pair_key = " <-> ".join(sorted([char_a.strip().lower(), char_b.strip().lower()]))
        return self.data.get("tv_transitions", {}).get(pair_key, {}).get("state")

    def update_character_gender_from_audio(self, name: str, gender: str) -> bool:
        """
        Updates an unconfirmed character's gender in Series Bible using definitive Japanese
        first-person audio markers (ore/boku -> MALE, atashi/atai -> FEMALE).
        Protected by symmetrical locks: cannot downgrade or overwrite confirmed MALE with FEMALE or vice versa.
        Thread-safe under concurrent batch processing.
        """
        if not name or gender not in ("MALE", "FEMALE"):
            return False
        with self._lock:
            clean_name = name.strip()
            existing_entry = self.data.get("characters", {}).get(clean_name)
            desc_v = ""
            if isinstance(existing_entry, dict):
                desc_v = str(existing_entry.get("description", ""))
            elif existing_entry:
                desc_v = str(existing_entry)

            # Symmetrical lock: already confirmed definitively by audio, quality gate, or explicit gender field
            has_confirmed_audio = "zweryfikowano z audio" in desc_v
            has_confirmed_qg = "zweryfikowano przez EpisodeQualityGate" in desc_v
            has_canonical_tag = bool(re.search(r"\[(KOBIETA|MĘŻCZYZNA)\s+\(Adresat(?:ka|ce|ki|ek|om|ami|ach|em|owi)?\)", desc_v, re.IGNORECASE))
            has_explicit_gender = isinstance(existing_entry, dict) and existing_entry.get("gender") in ("MALE", "FEMALE")

            if has_confirmed_audio or has_confirmed_qg or has_canonical_tag or has_explicit_gender:
                return False

            existing_gender = self.get_character_gender(clean_name, allow_generic_nouns=False)
            if existing_gender in ("MALE", "FEMALE") and existing_gender != gender:
                # Symmetrical lock: cannot overwrite inferred gender with opposite audio gender
                return False

            if gender == "FEMALE":
                clean_name_l = clean_name.lower()
                m_pref = MODIFIER_PREFIX_RE.match(clean_name)
                is_pref_male = False
                if m_pref:
                    base_n = m_pref.group(1).strip()
                    is_pref_male = (self.get_character_gender(base_n, allow_generic_nouns=False) == "MALE")
                is_boy_or_male_role = (
                    any(k in clean_name_l for k in ["kid", "son", "boy", "young", "child", "little", "baby", "teen", "bro", "brother", "chłopiec", "chłopak", "syn", "brat", "captain", "kapitan"]) or
                    is_pref_male or
                    self.get_character_gender(clean_name, allow_generic_nouns=False) == "MALE"
                )
                if is_boy_or_male_role:
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

        chars = self.get_characters_snapshot() if hasattr(self, "get_characters_snapshot") else (self.data.get("characters", {}) if hasattr(self, "data") else {})
        for k, v in list(chars.items()):
            if "->" not in k:
                k_l = k.lower()
                clean_k = extract_clean_speaker_name(k_l)
                if k_l == n_l or clean_k == n_l or n_l in k_l.split() or k_l in n_l:
                    desc_v = str(v.get("description", "") if isinstance(v, dict) else v).lower()
                    is_female = any(w in desc_v for w in ["female", "kobieta", "dziewczyn", "żeńsk"])
                    if is_female and any(w in desc_v for w in MATRON_ROLE_KEYWORDS):
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

    def get_dual_pair_gender_type(self, names_or_name1: Union[List[str], Set[str], Tuple[str, ...], str], name2: Optional[str] = None) -> str:
        """
        Determines the gender type of a two-person group (dual pair):
        - 'DUAL_FEMALE': both members are confirmed female (requires 'obie / was obu / z wami obiema')
        - 'DUAL_MALE': both members are confirmed male (requires 'obaj / was obu / z wami oboma')
        - 'DUAL_MIXED': 1 female + 1 male (requires collective 'oboje / was obojga / wam obojgu / z wami obojgiem')
        - 'UNKNOWN': fewer than 2 valid characters or unknown genders
        """
        if name2 is not None:
            names = [str(names_or_name1), str(name2)]
        elif isinstance(names_or_name1, (list, set, tuple)):
            names = list(names_or_name1)
        else:
            names = [str(names_or_name1)]

        clean_names = [n.strip() for n in names if n and str(n).strip()]
        if len(clean_names) < 2:
            return "UNKNOWN"

        distinct = []
        for cn in clean_names:
            if cn not in distinct:
                distinct.append(cn)
            if len(distinct) == 2:
                break
        if len(distinct) < 2:
            return "UNKNOWN"

        g1 = self.get_character_gender(distinct[0])
        g2 = self.get_character_gender(distinct[1])

        if g1 == "FEMALE" and g2 == "FEMALE":
            return "DUAL_FEMALE"
        if g1 == "MALE" and g2 == "MALE":
            return "DUAL_MALE"
        if (g1 == "FEMALE" and g2 == "MALE") or (g1 == "MALE" and g2 == "FEMALE"):
            return "DUAL_MIXED"
        return "UNKNOWN"

    @staticmethod
    def is_generic_actor_or_category(name: str) -> bool:
        return is_generic_actor_or_category(name)

    def is_non_character_entity(self, name: str) -> bool:
        """
        Determines whether a name refers to an organization, realm, institution, faction, location,
        ethnonym, or collective group, preventing it from ever being treated as a masculine/feminine character in name declension engines.
        """
        if not name:
            return False
        n_l = name.strip().lower()
        norm_nl = normalize_name_nfkd(n_l)

        # If explicitly registered in characters as a living character, protect from false toponym classification
        with self._lock:
            chars_dict = self.data.get("characters", {})
            for c_k, c_v in chars_dict.items():
                if "->" not in c_k:
                    c_clean = c_k.strip().lower()
                    c_aliases = [a.lower() for a in c_v.get("aliases", [])] if isinstance(c_v, dict) else []
                    is_exact_name = (c_clean == n_l or normalize_name_nfkd(c_clean) == norm_nl)
                    is_alias_match = (n_l in c_aliases) and (n_l not in KNOWN_FANTASY_TOPONYMS and norm_nl not in KNOWN_FANTASY_TOPONYMS)
                    if is_exact_name or is_alias_match:
                        c_desc = (c_v.get("description", "") if isinstance(c_v, dict) else str(c_v)).lower()
                        c_gender = (c_v.get("gender") if isinstance(c_v, dict) else "") or ""
                        if c_gender in ("MALE", "FEMALE") or any(w in c_desc for w in ["mężczyzna", "kobieta", "król", "książę", "postać", "bohater", "rycerz", "uczeń", "uczennica", "chłopak", "dziewczyna", "człowiek"]):
                            if "nie-postać" not in c_desc and "toponim" not in c_desc:
                                return False
            entity_cats = self.data.get("entity_categories") or self.data.get("entities") or {}
            cat = entity_cats.get(name.strip())
            if cat in (EntityCategory.TOPONYM.value, EntityCategory.CHREMATONYM.value, "TOPONYM", "CHREMATONYM"):
                return True
            if cat in (EntityCategory.ANTHROPONYM.value, "ANTHROPONYM"):
                return False

        if n_l in KNOWN_FANTASY_TOPONYMS or norm_nl in KNOWN_FANTASY_TOPONYMS:
            return True
        if n_l in INDECLINABLE_FRENCH_TOPONYMS:
            return True
        if n_l.endswith("um"):
            return True
        if n_l in ETHNONYMS_AND_COLLECTIVES or any(n_l.startswith(eth) for eth in ["mongol", "tatar", "merkit", "persian", "roman", "nomad", "pastoralist"]):
            return True
        if n_l in INSTITUTION_NOUNS or norm_nl in INSTITUTION_NOUNS:
            return True
        if any(n_l.endswith(suf) or norm_nl.endswith(suf) for suf in INSTITUTIONAL_SUFFIXES):
            return True
        REALM_INSTITUTION_NOUNS = {
            "imperium", "królestwo", "cesarstwo", "senat", "republika", "zakon", "gildia", "rada",
            "armia", "muzeum", "liceum", "koloseum", "akwarium", "centrum", "forum", "archiwum",
            "kościół", "rząd", "dwór", "trybunał", "pałac", "państwo", "akademia", "uniwersytet"
        }
        if n_l in REALM_INSTITUTION_NOUNS:
            return True
        if n_l in KNOWN_FANTASY_TOPONYMS:
            return True
        for section in ["organizations", "factions", "realms", "locations", "places", "cities", "countries", "historical_context", "relics", "artifacts", "weapons"]:
            with self._lock:
                sec_dict = dict(self.data.get(section, {})) if isinstance(self.data.get(section, {}), dict) else {}
            if sec_dict:
                for k, v in list(sec_dict.items()):
                    if k.lower() == n_l:
                        return True
                    if isinstance(v, dict):
                        if v.get("canonical_name", "").lower() == n_l or v.get("short_name", "").lower() == n_l or v.get("name", "").lower() == n_l:
                            return True
        # Check glossary entries for realm/toponym/location designations
        with self._lock:
            glossary_dict = dict(self.data.get("glossary", {})) if isinstance(self.data.get("glossary", {}), dict) else {}
        if glossary_dict:
            TOPONYM_KWS = {"kraina", "królestwo", "cesarstwo", "toponim", "lokacja", "kopalnia", "stolica", "zamek", "twierdza", "akademia", "instytucja", "miasto", "prowincja", "prefektura", "rzeka", "góra", "relikt", "artefakt", "święty oręż"}
            for k, v in list(glossary_dict.items()):
                k_l = str(k).lower()
                v_str = str(v).lower()
                if any(kw in v_str for kw in TOPONYM_KWS):
                    if k_l == n_l or n_l in k_l.split():
                        return True
                    v_tokens = [w.lower() for w in re.findall(r"\b[A-Za-ząćęłńóśźżA-ZĄĆĘŁŃÓŚŹŻ]{3,}\b", v_str)]
                    if n_l in v_tokens:
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
        with self._lock:
            factions = dict(self.data.get("factions", {})) if isinstance(self.data.get("factions", {}), dict) else {}
        if factions:
            for f_key, f_val in list(factions.items()):
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

        with self._lock:
            bible_chars = list(self.data.get("characters", {}).items())
        for name, info in bible_chars:
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
            for name, info in bible_chars[:max_chars]:
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
            "ryoma", "hanza", "sinbad", "judar", "alibaba"
        }

        # Safely extract string description from details (supporting dict payloads)
        if isinstance(details, dict):
            raw_desc = (details.get("description", "") or details.get("gender", ""))
            if not raw_desc:
                g = details.get("gender", "")
                raw_desc = "MĘŻCZYZNA" if str(g).upper() in ("MALE", "MĘŻCZYZNA") else ("KOBIETA" if str(g).upper() in ("FEMALE", "KOBIETA") else str(g))
        else:
            raw_desc = str(details)

        clean_desc = sanitize_lexical_text(raw_desc.strip())
        name_lower = name.lower()

        # Distinguish standalone characters from relationships (Speaker -> Listener)
        is_rel = "->" in name
        speaker = ""
        listener = ""
        if is_rel:
            parts = [p.strip() for p in name.split("->")]
            speaker = parts[0]
            listener = parts[-1] if len(parts) > 1 else ""

        target_name = listener.lower() if is_rel else name_lower
        target_is_male = any(m == target_name or f" {m} " in f" {target_name} " for m in CANONICAL_MALE_NAMES)
        target_is_female = False

        # Determine if incoming entry is verified from AniList or explicit tag
        incoming_is_verified = (
            bool(isinstance(details, dict) and details.get("has_verified_gender"))
            or "zweryfikowan" in raw_desc.lower()
            or "anilist" in raw_desc.lower()
        )

        if incoming_is_verified:
            if isinstance(details, dict) and str(details.get("gender", "")).upper() in ("FEMALE", "KOBIETA"):
                target_is_female, target_is_male = True, False
            elif isinstance(details, dict) and str(details.get("gender", "")).upper() in ("MALE", "MĘŻCZYZNA"):
                target_is_male, target_is_female = True, False
            elif re.search(r"\b(?:kobieta|żeńsk\w*|female)\b", raw_desc.lower()):
                target_is_female, target_is_male = True, False
            elif re.search(r"\b(?:mężczyzna|męsk\w*|male|chłopak)\b", raw_desc.lower()):
                target_is_male, target_is_female = True, False
        else:
            # Look up confirmed target character gender in Series Bible ONLY if incoming is not verified
            if hasattr(self, "data") and "characters" in self.data:
                with self._lock:
                    chars_items = list(self.data["characters"].items())
                for k, v in chars_items:
                    if "->" not in k:
                        k_l = k.lower()
                        if k_l == target_name or (len(k_l) >= 3 and k_l in target_name) or (len(target_name) >= 3 and target_name in k_l):
                            desc_v = str(v.get("description", "") if isinstance(v, dict) else v).lower()
                            if any(w in desc_v for w in MALE_ROLE_KEYWORDS):
                                target_is_male = True
                            if is_male_role_text(desc_v):
                                target_is_male = True
                            if is_female_role_text(desc_v):
                                target_is_female = True

        # In relationships, extract recipient description part (after '->' in brackets e.g. '(koleżanka -> przyjaciel)', '(roleA / roleB)', '(roleA i roleB)')
        rel_target_desc = clean_desc.lower()
        if is_rel:
            m_role = re.search(r"\(([^)]+)\)", clean_desc)
            if m_role:
                rc = m_role.group(1).strip()
                for sep in ["->", "/", " i "]:
                    if sep in rc:
                        rel_target_desc = rc.split(sep)[-1].strip().lower()
                        break
            elif "->" in clean_desc:
                rel_target_desc = clean_desc.split("->")[-1].lower()

        if not incoming_is_verified:
            if "[kobieta (adresat" in clean_desc.lower():
                target_is_female = True
                target_is_male = False
            elif "[mężczyzna (adresat" in clean_desc.lower():
                target_is_male = True
                target_is_female = False
            else:
                if is_male_role_text(rel_target_desc) or re.search(r"\bpanie\s+[A-ZĄĆĘŁŃÓŚŹŻ]", clean_desc):
                    target_is_male = True
                if is_female_role_text(rel_target_desc) and not re.search(r"\bpanie\s+[A-ZĄĆĘŁŃÓŚŹŻ]", clean_desc):
                    target_is_female = True

                # Resolve conflict: target cannot be both male and female
                if target_is_male and target_is_female:
                    if is_male_role_text(rel_target_desc) or re.search(r"\bpanie\s+[A-ZĄĆĘŁŃÓŚŹŻ]", clean_desc):
                        target_is_female = False
                    elif is_female_role_text(rel_target_desc):
                        target_is_male = False

        # Clean existing poisoned tags if they contradict target gender (with full Polish inflection paradigm)
        if target_is_male:
            clean_desc = re.sub(r"\s*\[KOBIETA \(Adresat(?:ka|ce|ki|ek|om|ami|ach|em|owi)?\)[^\]]*\]", "", clean_desc, flags=re.IGNORECASE).strip()
        if target_is_female:
            clean_desc = re.sub(r"\s*\[MĘŻCZYZNA \(Adresat(?:ka|ce|ki|ek|om|ami|ach|em|owi)?\)[^\]]*\]", "", clean_desc, flags=re.IGNORECASE).strip()

        # Check if the relationship or character involves a confirmed male character
        involves_male = target_is_male or any(m in name_lower for m in CANONICAL_MALE_NAMES)
        if not involves_male and hasattr(self, "data") and "characters" in self.data:
            with self._lock:
                chars_items_male = list(self.data["characters"].items())
            for k, v in chars_items_male:
                if k.lower() in name_lower:
                    desc_v = str(v.get("description", "") if isinstance(v, dict) else v).lower()
                    if any(w in desc_v for w in MALE_ROLE_KEYWORDS):
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
            if "wymóg form męskich" not in clean_desc.lower() and "ostrzegał" not in clean_desc.lower():
                clean_desc = f"{clean_desc} [Wymóg form męskich w czasie przeszłym: mówił / ostrzegał / pomógł]".strip()

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
        is_single_female = (target_is_female or bool(re.search(r"\b(?:kobieta|female|dziewczyna|nauczycielka|uczennica|kapłanka)\b", rel_target_desc, re.IGNORECASE))) and not is_female_group and not target_is_male
        if is_single_female:
            if "2. os. lp." not in clean_desc.lower() and "-łaś" not in clean_desc.lower():
                clean_desc = f"{clean_desc} [KOBIETA (Adresat) - W 2. os. lp. 'ty' wymóg form żeńskich: byłaś / zrobiłaś / jesteś pewna]".strip()

        is_single_male = (target_is_male or bool(re.search(r"\b(?:mężczyzna|male|chłopak|żołnierz|pan|uczeń)\b", rel_target_desc, re.IGNORECASE))) and not is_male_group and not target_is_female
        if is_single_male:
            if "2. os. lp." not in clean_desc.lower() and "-łeś" not in clean_desc.lower():
                clean_desc = f"{clean_desc} [MĘŻCZYZNA (Adresat) - W 2. os. lp. 'ty' wymóg form męskich: byłeś / zrobiłeś / jesteś pewien]".strip()

        # Safeguard hierarchical honorific relationships and anti-hybrid vocatives (Filar C & CLVII)
        is_subordinate_or_disciple = any(w in clean_desc.lower() for w in ["uczeń", "uczennica", "służąca", "niewolnica", "adept", "podwładn"])
        is_master_or_superior = any(w in clean_desc.lower() for w in ["mistrz", "arcymag", "pan ", "mentor", "zwierzchnik", "lord"])
        if is_subordinate_or_disciple or is_master_or_superior:
            if "t-v invariance" not in clean_desc.lower() and "panie" not in clean_desc.lower():
                clean_desc = f"{clean_desc} [RELACJA HIERARCHICZNA (T-V Invariance): stały zwrot formalny 'Pan / Panie [Imię]', eliminacja hybryd 'Imię... ma pan' oraz odporność na opuszczanie -sama]".strip()

        # Safeguard temporal continuity & scene boundary protection (Filar CLXV)
        is_private_relationship = any(w in clean_desc.lower() for w in ["na osobności", "w cztery oczy", "prywatn", "zaufan", "sekret"])
        if is_private_relationship:
            if "filar clxv" not in clean_desc.lower() and "dyskontinuitet" not in clean_desc.lower():
                clean_desc = f"{clean_desc} [OCHRONA PRZESKOKÓW SCEN (Filar CLXV): w rozmowach na osobności po przejściu eliminacja opóźnionego 'Jasne, o co chodzi?' -> otwarcie dialogu: 'Więc o co chodzi?']".strip()

        return clean_desc

    def update_from_episode_profile(
        self,
        episode_name: str = "",
        characters: Optional[Dict[str, str]] = None,
        glossary: Optional[Dict[str, str]] = None,
        plot_anchors: Optional[Dict[str, str]] = None,
        relationships: Optional[Dict[str, str]] = None,
    ):
        """Updates glossary, character registry, relationships, and plot anchors based on Profiler output of a new episode (Thread-Safe)."""
        with self._lock:
            if episode_name and episode_name not in self.data["episodes_translated"]:
                self.data["episodes_translated"].append(episode_name)

            if characters:
                FEMALE_KEYWORDS = [
                    "kobieta", "żeńsk", "female", "dziewczyn", "nauczycielk", "czarodziejk",
                    "szpieżk", "wojowniczk", "kapłank", "służąc", "pani ", "panią", "bohaterk",
                    "arystokratk", "władczyn", "królow", "księżniczk", "matk", "córk", "siostr"
                ]
                if "declensions" not in self.data:
                    self.data["declensions"] = {}
                if "relationships" not in self.data:
                    self.data["relationships"] = {}

                for name, details in list(characters.items()):
                    if not name or not details:
                        continue
                    # Filtrowanie szyldów, ról generycznych i powiadomień ciągłości
                    if is_sign_entity(name) or is_generic_actor_or_category(name) or not is_valid_anthroponymic_phonotactics(name):
                        continue
                    if isinstance(details, dict):
                        if details.get("is_sign") or details.get("role") in ("sign", "napis"):
                            continue
                        if details.get("source") == "continuity_bridge_alerts" or details.get("role") == "continuity_bridge_alert" or details.get("is_continuity_alert"):
                            continue
                    clean_details = self._sanitize_character_entry(name, details)
                    if "->" in name:
                        self.data["relationships"][name] = clean_details
                        self.data.setdefault("relations", {})[name] = clean_details
                        self.data["characters"][name] = {"description": clean_details}
                        parts = [p.strip() for p in name.split("->")]
                        for idx, p in enumerate(parts):
                            clean_p = re.sub(r"-(?:sensei|kun|chan|san|sama|senpai)\b", "", p, flags=re.IGNORECASE).strip()
                            clean_p = re.sub(r"^(?:Pani|Pan|Kapitan|Dziekan|Kardynał|Generał|Doktor|Profesor)\s+", "", clean_p).strip()
                            if clean_p and len(clean_p) >= 2 and not any(ch in clean_p for ch in "{}[]():;") and is_valid_anthroponymic_phonotactics(clean_p):
                                if clean_p not in self.data["characters"]:
                                    p_details = clean_details
                                    is_terminal = (idx == len(parts) - 1)

                                    if "->" in clean_details:
                                        detail_parts = [d.strip() for d in clean_details.split("->")]
                                        if len(detail_parts) == len(parts):
                                            p_details = detail_parts[idx]
                                        elif len(detail_parts) >= 2 and idx == 0:
                                            p_details = detail_parts[0]
                                        elif len(detail_parts) >= 2 and is_terminal:
                                            p_details = detail_parts[-1]
                                    else:
                                        m_role = re.search(r"\(([^)]+)\)", clean_details)
                                        if m_role:
                                            rc = m_role.group(1).strip()
                                            for sep in ["->", "/", " i "]:
                                                if sep in rc:
                                                    rc_parts = [r.strip() for r in rc.split(sep)]
                                                    if len(rc_parts) == len(parts):
                                                        p_details = rc_parts[idx]
                                                        break
                                                    elif len(rc_parts) >= 2 and idx == 0:
                                                        p_details = rc_parts[0]
                                                        break
                                                    elif len(rc_parts) >= 2 and is_terminal:
                                                        p_details = rc_parts[-1]
                                                        break

                                    if not is_terminal:
                                        # Strict Non-Terminal / Speaker Slot Isolation (R3.2 & Anti-Bleed):
                                        # Non-terminal participants must NEVER inherit addressee traits or 2nd person markers!
                                        p_details = re.sub(r"\[[^\]]*\bAdresat(?:ka|ce|ki|ek|om|ami|ach|em|owi)?\b[^\]]*\]", "", p_details, flags=re.IGNORECASE)
                                        p_details = re.sub(r"\[RELACJA HIERARCHICZNA[^\]]*\]", "", p_details, flags=re.IGNORECASE)
                                        p_details = re.sub(r"\b(?:byłaś|zrobiłaś|jesteś pewna|byłeś|zrobiłeś|jesteś pewien|2\.\s*os\.\s*lp\.)\b", "", p_details, flags=re.IGNORECASE)
                                        p_details = re.sub(r"\b(?:jesteś\s+(?:moją|moim)\s+\w+)\b", "", p_details, flags=re.IGNORECASE)

                                    p_g = "UNKNOWN"
                                    if is_terminal and "[kobieta (adresat" in clean_details.lower():
                                        p_g = "FEMALE"
                                    elif is_terminal and "[mężczyzna (adresat" in clean_details.lower():
                                        p_g = "MALE"
                                    elif is_female_role_text(clean_p) or (is_female_role_text(p_details) and not is_male_role_text(p_details)):
                                        p_g = "FEMALE"
                                    elif is_male_role_text(clean_p) or (is_male_role_text(p_details) and not is_female_role_text(p_details)):
                                        p_g = "MALE"
                                    else:
                                        p_lower = clean_p.lower()
                                        p_tokens = p_lower.split()
                                        if p_lower in CANONICAL_MALE_NAMES or any(t in CANONICAL_MALE_NAMES for t in p_tokens):
                                            p_g = "MALE"
                                        elif (p_lower.endswith("a") or (p_tokens and p_tokens[0].endswith("a"))) and (p_lower not in CANONICAL_MALE_NAMES and not any(t in CANONICAL_MALE_NAMES for t in p_tokens)):
                                            p_g = "FEMALE"
                                        else:
                                            p_g = "MALE"

                                    g_str = "KOBIETA" if p_g == "FEMALE" else "MĘŻCZYZNA"
                                    self.data["characters"][clean_p] = {
                                        "description": f"{g_str} (wyodrębniono z relacji serii)",
                                        "gender": p_g,
                                        "grammatical_gender": "FEMININE" if p_g == "FEMALE" else "MASCULINE",
                                        "has_verified_gender": True,
                                        "confidence": 0.95,
                                        "priority": "P0",
                                        "aliases": [clean_p],
                                        "entity_category": EntityCategory.ANTHROPONYM.value
                                    }
                                    self.data["declensions"][clean_p] = generate_polish_name_declension(clean_p, p_g)
                        continue

                    if name not in self.data["characters"]:
                        if isinstance(details, dict):
                            entry_payload = copy.deepcopy(details)
                            entry_payload["description"] = clean_details
                            self.data["characters"][name] = entry_payload
                        else:
                            self.data["characters"][name] = {"description": clean_details}
                    else:
                        existing_entry = self.data["characters"][name]
                        existing_desc = existing_entry.get("description", "") if isinstance(existing_entry, dict) else str(existing_entry)
                        existing_lower = existing_desc.lower()

                        existing_is_verified = bool(isinstance(existing_entry, dict) and existing_entry.get("has_verified_gender")) or "zweryfikowan" in existing_lower or "anilist" in existing_lower
                        existing_is_heuristic = "(wyodrębniono z relacji" in existing_lower or "wyodrębniono z relacji" in existing_lower
                        incoming_is_verified = bool(isinstance(details, dict) and details.get("has_verified_gender")) or "zweryfikowan" in clean_details.lower() or "anilist" in clean_details.lower()

                        if existing_is_verified and not incoming_is_verified:
                            # P0 Priority (R3.3): verified AniList entry cannot be overridden by unverified text relation heuristic
                            continue

                        if not existing_is_heuristic:
                            # Protect confirmed gender against downgrading or overwriting (both male and female)
                            is_definite_female = any(w in clean_details.lower() for w in ["córka", "cesarzowa", "chatun", "żona", "małżonka", "matka", "księżniczka", "królowa"])
                            has_confirmed_male = any(w in existing_lower for w in ["mężczyzna", "męsk", "male", "nakaz form męskich", "wymóg form męskich"]) and not is_definite_female
                            is_incoming_female = any(w in clean_details.lower() for w in ["kobieta", "żeńsk", "female", "służąca", "nauczycielka", "dziewczyna", "cesarzowa", "chatun", "córka", "żona"])
                            if has_confirmed_male and is_incoming_female:
                                continue

                            has_confirmed_female = any(w in existing_lower for w in ["kobieta", "żeńsk", "female", "dziewczyna", "nakaz form żeńskich", "wymóg form żeńskich", "nauczycielka"])
                            is_incoming_male = any(w in clean_details.lower() for w in ["mężczyzna", "męsk", "male", "chłopak"])
                            if has_confirmed_female and is_incoming_male:
                                continue

                            # If existing entry has rich directives/seiyū, do not overwrite with bare string
                            has_rich_directives = any(w in existing_lower for w in ["nakaz", "seiyū", "wymóg form", "dyrektyw"])
                            if has_rich_directives and not any(w in clean_details.lower() for w in ["nakaz", "wymóg"]):
                                continue

                        if isinstance(details, dict):
                            entry_payload = copy.deepcopy(details)
                            entry_payload["description"] = clean_details
                            self.data["characters"][name] = entry_payload
                        else:
                            self.data["characters"][name] = {"description": clean_details}

                    # Generate and store 7-case Polish declension matrix
                    clean_details_sanitized = re.sub(r"(?:eliminacja|blokada)\s+form\s+(?:żeńsk|męsk)[a-ząćęłńóśźż]*", "", clean_details.lower())
                    if isinstance(details, dict) and str(details.get("gender", "")).upper() in ("MALE", "MĘŻCZYZNA"):
                        c_gender = "MALE"
                    elif isinstance(details, dict) and str(details.get("gender", "")).upper() in ("FEMALE", "KOBIETA"):
                        c_gender = "FEMALE"
                    elif is_male_role_text(clean_details_sanitized) and not is_female_role_text(clean_details_sanitized):
                        c_gender = "MALE"
                    elif is_female_role_text(clean_details_sanitized) and not is_male_role_text(clean_details_sanitized):
                        c_gender = "FEMALE"
                    elif any(w in clean_details_sanitized for w in ["mężczyzna", "męsk", "male", "chłopak"]):
                        c_gender = "MALE"
                    elif any(w in clean_details_sanitized for w in FEMALE_KEYWORDS):
                        c_gender = "FEMALE"
                    else:
                        c_gender = "UNKNOWN"

                    if "/" in name:
                        names_to_decline = [p.strip() for p in name.split("/")]
                    else:
                        names_to_decline = [name]

                    for single_n in names_to_decline:
                        if single_n and len(single_n) >= 3 and not any(ch in single_n for ch in "->/"):
                            self.data["declensions"][single_n] = generate_polish_name_declension(single_n, c_gender)

            if glossary:
                for k, v in list(glossary.items()):
                    # Store non-trivial terms only and sanitize parenthetical descriptions
                    if k and v and len(k) > 1 and len(v) > 1:
                        clean_k = str(k).strip()
                        clean_v = re.sub(r"\s*[\(\[].*?[\)\]]", "", v)
                        clean_v = sanitize_lexical_text(re.sub(r"\s*[\(\[].*$", "", clean_v).strip())
                        if "/" in clean_v:
                            clean_v = clean_v.split("/")[0].strip()
                        if clean_k and clean_v:
                            # Case-insensitive update to prevent duplicate collisions
                            norm_k = clean_k.lower()
                            for old_k in list(self.data["glossary"].keys()):
                                if old_k.lower() == norm_k and old_k != clean_k:
                                    del self.data["glossary"][old_k]
                            self.data["glossary"][clean_k] = clean_v
                            # Auto-generate 7-case declension for characters/anthroponyms in glossary
                            if len(clean_v) >= 3 and not any(ch in clean_v for ch in "{}[]():;"):
                                if "declensions" not in self.data:
                                    self.data["declensions"] = {}
                                is_char_entry = (
                                    clean_k in self.data.get("characters", {})
                                    or clean_v in self.data.get("characters", {})
                                    or self.get_entity_category(clean_k) == EntityCategory.ANTHROPONYM
                                    or self.get_entity_category(clean_v) == EntityCategory.ANTHROPONYM
                                )
                                if is_char_entry:
                                    self.data["declensions"][clean_k] = generate_polish_name_declension(clean_v, "UNKNOWN")
                                    if clean_v not in self.data["declensions"] and clean_v[0].isupper() and not self.is_non_character_entity(clean_v):
                                        self.data["declensions"][clean_v] = generate_polish_name_declension(clean_v, "UNKNOWN")

            if plot_anchors:
                if "plot_anchors" not in self.data:
                    self.data["plot_anchors"] = {}
                for k, v in list(plot_anchors.items()):
                    if k and v:
                        clean_k = str(k).strip()
                        clean_v = sanitize_lexical_text(str(v).strip())
                        if clean_k and clean_v:
                            self.data["plot_anchors"][clean_k] = clean_v

            if relationships:
                if "relationships" not in self.data:
                    self.data["relationships"] = {}
                if "relations" not in self.data:
                    self.data["relations"] = {}
                for rel_k, rel_v in list(relationships.items()):
                    if rel_k and rel_v:
                        clean_rel_v = sanitize_lexical_text(str(rel_v).strip())
                        self.data["relationships"][rel_k] = clean_rel_v
                        self.data["relations"][rel_k] = clean_rel_v
                        # Also extract names from relationships to decline them
                        for part in re.split(r"->|/|,", rel_k):
                            part_clean = part.strip()
                            if len(part_clean) >= 3 and not any(ch in part_clean for ch in "{}[]():;"):
                                if part_clean not in self.data["declensions"] and not self.is_non_character_entity(part_clean):
                                    self.data["declensions"][part_clean] = generate_polish_name_declension(part_clean, "UNKNOWN")

            self._sanitize_loaded_bible_in_ram()

    def assimilate_quality_gate_invariants(self, quality_gate_fixes: List[Any]):
        """
        Closed-loop learning engine (Layer 2).
        Ingests 100% confirmed invariants from EpisodeQualityGate post-pass
        (character gender, 7-case foreign name declensions, T-V address forms)
        and commits them permanently to the Series Bible.
        """
        if not quality_gate_fixes:
            return

        with self._lock:
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
                            self.register_entity_category(c_name, EntityCategory.ANTHROPONYM)
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
                        is_generic_actor = is_generic_actor_or_category(char_name) or bool(re.match(r"^(?:man|male|boy|guy|woman|female|girl|lady|mężczyzna|kobieta|chłopak|dziewczyna|facet|pan|pani)\s+[a-z0-9]+$", char_name, re.IGNORECASE))
                        if char_name and len(char_name) >= 3 and not is_generic_actor:
                            desc = f"{'MĘŻCZYZNA' if gender_str == 'MALE' else 'KOBIETA'} (zweryfikowano przez EpisodeQualityGate)"
                            self.data["characters"][char_name] = {"description": desc, "source": "quality_gate"}
                            self.data["declensions"][char_name] = generate_polish_name_declension(char_name, gender_str)
                            self.register_entity_category(char_name, EntityCategory.ANTHROPONYM)
                            has_updates = True

                    # 1st-person speaker gender confirmation:
                    m_spk = re.search(r"skorygowano 1\. os\. na rodzaj (męski|żeński) dla mówc(?:y|zyni) '([^']+)'", fix_item)
                    if m_spk:
                        gender_str = "MALE" if m_spk.group(1) == "męski" else "FEMALE"
                        char_name = m_spk.group(2).strip()
                        is_generic_actor = is_generic_actor_or_category(char_name) or bool(re.match(r"^(?:man|male|boy|guy|woman|female|girl|lady|mężczyzna|kobieta|chłopak|dziewczyna|facet|pan|pani)\s+[a-z0-9]+$", char_name, re.IGNORECASE))
                        if char_name and len(char_name) >= 3 and not is_generic_actor:
                            desc = f"{'MĘŻCZYZNA' if gender_str == 'MALE' else 'KOBIETA'} (zweryfikowano przez EpisodeQualityGate)"
                            self.data["characters"][char_name] = {"description": desc, "source": "quality_gate"}
                            self.data["declensions"][char_name] = generate_polish_name_declension(char_name, gender_str)
                            self.register_entity_category(char_name, EntityCategory.ANTHROPONYM)
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
        """Formats Series Bible into a compact section for LLM prompt injection (Thread-Safe)."""
        lines = []
        has_content = False

        with self._lock:
            chars_items = list(self.data.get("characters", {}).items())[:8]
            rels_items = list((self.get_relations_snapshot() or self.data.get("relationships", {})).items())[:8]
            decls_items = list(self.data.get("declensions", {}).items())[:6]
            gloss_items = list(self.data.get("glossary", {}).items())[:12]
            canon_items = list(self.data.get("fansub_canon", {}).items())[:8]
            anchors_items = list(self.data.get("plot_anchors", {}).items())[:8]
            ep_count = len(self.data.get("episodes_translated", []))

        if chars_items or gloss_items or anchors_items or decls_items or canon_items:
            lines.append("--- BIBLIA SERIALU (PAMIĘĆ MIĘDZYODCINKOWA SEZONU) ---")
            lines.append(f"Seria: '{self.anime_title}' (Przetłumaczono odcinków: {ep_count})")
            
            if chars_items:
                lines.append("• Kluczowe postacie z poprzednich odcinków:")
                for name, info in chars_items:
                    desc = info.get("description", "") if isinstance(info, dict) else str(info)
                    lines.append(f"  - {name}: {desc}")
                has_content = True

            if rels_items:
                lines.append("• Kluczowe relacje i formy zwrotu (T-V / Honoryfikatywność):")
                for rel_k, rel_v in rels_items:
                    lines.append(f"  - {rel_k}: {rel_v}")
                has_content = True

            if decls_items:
                decl_items_out = []
                for c_name, c_decl in decls_items:
                    if c_decl and isinstance(c_decl, dict) and c_decl.get("M") != c_decl.get("D"):
                        decl_items_out.append(f"    * {c_name}: D. {c_decl.get('D')}, C/Ms. {c_decl.get('C')}, B/N. {c_decl.get('B')}/z {c_decl.get('N')}, W. {c_decl.get('W')}!")
                if decl_items_out:
                    lines.append("• Wzorzec odmiany imion (Matryca 7 Przypadków fleksyjnych):")
                    lines.extend(decl_items_out)
                    has_content = True

            if gloss_items:
                lines.append("• Ustalone nazwy i terminologia z poprzednich odcinków (ZACHOWAJ SPÓJNOŚĆ!):")
                for src, trg in gloss_items:
                    lines.append(f"  - '{src}' -> '{trg}'")
                has_content = True

            if canon_items:
                lines.append("• Sprawdzony kanon fansuberski dla tej serii (ZACHOWAJ 100% SPÓJNOŚCI!):")
                for f_term, f_info in canon_items:
                    if isinstance(f_info, dict) and "instruction" in f_info:
                        lines.append(f"  - {f_info['instruction']}")
                    elif isinstance(f_info, dict) and "canonical_pl" in f_info:
                        lines.append(f"  - '{f_term}' -> '{f_info['canonical_pl']}'")
                has_content = True

            if anchors_items:
                lines.append("• Kluczowe rekwizyty i kotwice fabularne (PLOT ANCHORS - ZACHOWAJ CIĄGŁOŚĆ!):")
                for item_key, directive in anchors_items:
                    lines.append(f"  - [{item_key}]: {directive}")
                has_content = True

            lines.append("-------------------------------------------------------\n")

        return "\n".join(lines) if has_content else ""

    def format_scoped_for_batch(
        self,
        batch_text: str = "",
        active_speakers: Optional[Set[str]] = None,
        lookback_text: str = "",
        lookahead_text: str = ""
    ) -> str:
        """
        Formats a strictly scoped Series Bible snippet for a specific batch (Context Minimalism).
        Only includes characters, relationships, declensions, glossary terms, and plot anchors
        that are actually referenced in the current batch or its immediate context.
        Thread-safe under concurrent batch processing.
        """
        corpus = f"{batch_text} {lookback_text} {lookahead_text}".lower()
        active_spk_lower = {s.lower().strip() for s in (active_speakers or set()) if s and s.strip()}

        with self._lock:
            chars_items = list(self.data.get("characters", {}).items())
            rels_items = list((self.get_relations_snapshot() or self.data.get("relationships", {})).items())
            decls_items = list(self.data.get("declensions", {}).items())
            gloss_items = list(self.data.get("glossary", {}).items())
            anchors_items = list(self.data.get("plot_anchors", {}).items())
            canon_items = list(self.data.get("fansub_canon", {}).items())

        # 1. Filter characters
        scoped_chars = {}
        for name, info in chars_items:
            name_lower = name.lower()
            # Match if speaker or mentioned in corpus
            if name_lower in active_spk_lower or any(s in name_lower or name_lower in s for s in active_spk_lower if len(s) >= 3):
                scoped_chars[name] = info
            elif re.search(rf"\b{re.escape(name_lower)}\b", corpus):
                scoped_chars[name] = info

        # 2. Filter relationships
        scoped_rels = {}
        for rel_k, rel_v in rels_items:
            rel_k_lower = rel_k.lower()
            if any(name.lower() in rel_k_lower for name in scoped_chars) or any(s in rel_k_lower for s in active_spk_lower if len(s) >= 3):
                scoped_rels[rel_k] = rel_v

        # 3. Filter declensions
        scoped_decls = {}
        for c_name, c_decl in decls_items:
            if c_name in scoped_chars or c_name.lower() in active_spk_lower or re.search(rf"\b{re.escape(c_name.lower())}\b", corpus):
                scoped_decls[c_name] = c_decl

        # 4. Filter glossary
        scoped_gloss = {}
        for src, trg in gloss_items:
            if len(src) >= 3 and re.search(rf"\b{re.escape(src.lower())}\b", corpus):
                scoped_gloss[src] = trg

        # 5. Filter plot anchors
        scoped_anchors = {}
        for item_key, directive in anchors_items:
            if len(item_key) >= 3 and item_key.lower() in corpus:
                scoped_anchors[item_key] = directive

        # 6. Filter fansub canon
        scoped_canon = {}
        for f_term, f_info in canon_items:
            en_words = [f_term]
            pl_words = []
            if isinstance(f_info, dict):
                if "en" in f_info:
                    en_words.extend(f_info["en"])
                if "canonical_pl" in f_info:
                    pl_words.append(f_info["canonical_pl"])
            match_en = any(len(w) >= 3 and re.search(rf"\b{re.escape(w.lower())}\b", corpus) for w in en_words)
            match_pl = any(len(w) >= 3 and re.search(rf"\b{re.escape(w.lower())}\b", corpus) for w in pl_words)
            if match_en or match_pl or len(canon_items) <= 15:
                scoped_canon[f_term] = f_info

        lines = []
        has_content = False

        if scoped_chars or scoped_gloss or scoped_anchors or scoped_decls or scoped_rels or scoped_canon:
            lines.append("--- BIBLIA SERIALU (KONTEKST BIEŻĄCEJ SCENY) ---")
            if scoped_chars:
                lines.append("• Postacie obecne w scenie:")
                for name, info in scoped_chars.items():
                    desc = info.get("description", "") if isinstance(info, dict) else str(info)
                    lines.append(f"  - {name}: {desc}")
                has_content = True

            if scoped_rels:
                lines.append("• Relacje w scenie (T-V / Honoryfikatywność):")
                for rel_k, rel_v in scoped_rels.items():
                    lines.append(f"  - {rel_k}: {rel_v}")
                has_content = True

            if scoped_decls:
                decl_items = []
                for c_name, c_decl in scoped_decls.items():
                    if c_decl and isinstance(c_decl, dict) and c_decl.get("M") != c_decl.get("D"):
                        decl_items.append(f"    * {c_name}: D. {c_decl.get('D')}, C/Ms. {c_decl.get('C')}, B/N. {c_decl.get('B')}/z {c_decl.get('N')}, W. {c_decl.get('W')}!")
                if decl_items:
                    lines.append("• Wzorzec odmiany imion w scenie (Matryca 7 Przypadków fleksyjnych):")
                    lines.extend(decl_items)
                    has_content = True

            if scoped_canon:
                lines.append("• Sprawdzony kanon fansuberski dla tej serii:")
                for f_term, f_info in scoped_canon.items():
                    if isinstance(f_info, dict) and "instruction" in f_info:
                        lines.append(f"  - {f_info['instruction']}")
                    elif isinstance(f_info, dict) and "canonical_pl" in f_info:
                        lines.append(f"  - '{f_term}' -> '{f_info['canonical_pl']}'")
                has_content = True

            if scoped_gloss:
                lines.append("• Ustalone nazwy i pojęcia obecne w scenie:")
                for src, trg in scoped_gloss.items():
                    lines.append(f"  - '{src}' -> '{trg}'")
                has_content = True

            if scoped_anchors:
                lines.append("• Kluczowe rekwizyty i kotwice fabularne w scenie:")
                for item_key, directive in scoped_anchors.items():
                    lines.append(f"  - [{item_key}]: {directive}")
                has_content = True

            lines.append("--------------------------------------------------\n")
        elif not scoped_chars and not active_spk_lower.intersection({n.lower() for n in self.data.get("characters", {})}):
            # If the series has characters defined but NONE of them are in this scene (e.g. background character, mob, new scene)
            if self.data.get("characters"):
                lines.append("--- KONTEKST SCENY: Postacie epizodyczne / tło ---")
                lines.append("• W tej scenie nie występują główne postacie z bazy serii.")
                lines.append("• Dedukuj płeć, relacje i emocje bezpośrednio z dialogu, intonacji seiyū oraz kontekstu sytuacyjnego.")
                lines.append("--------------------------------------------------\n")
                has_content = True

        return "\n".join(lines) if has_content else ""

    def generate_html_report(self) -> str:
        """Generates a responsive modern dark-mode HTML continuity report of the Series Bible (Thread-Safe)."""
        with self._lock:
            chars_items = list(self.data.get("characters", {}).items())
            gloss_items = list(self.data.get("glossary", {}).items())
            rel_items = list((self.get_relations_snapshot() or self.data.get("relationships", {})).items())
            anchor_items = list(self.data.get("plot_anchors", {}).items())
            episodes_list = ", ".join(self.data.get("episodes_translated", [])) or "Brak przetłumaczonych odcinków"

        chars_rows = ""
        for name, info in chars_items:
            desc = info.get("description", "") if isinstance(info, dict) else str(info)
            chars_rows += f"<tr><td><strong>{name}</strong></td><td>{desc}</td></tr>"

        gloss_rows = ""
        for src, trg in gloss_items:
            gloss_rows += f"<tr><td><code>{src}</code></td><td><strong>{trg}</strong></td></tr>"

        rel_rows = ""
        for pair, rel in rel_items:
            rel_rows += f"<tr><td><strong>{pair}</strong></td><td>{rel}</td></tr>"

        anchor_rows = ""
        for p_item, p_dir in anchor_items:
            anchor_rows += f"<tr><td><strong>{p_item}</strong></td><td>{p_dir}</td></tr>"

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
            logger.warning("Inicjalizacja i zapis bazy serii zakończone wyjątkiem", exc_info=True)
    return count
