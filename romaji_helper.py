# -*- coding: utf-8 -*-
"""
Pomocnik konwersji tekstu japońskiego (Kanji / Kana) na zapis fonetyczny alfabetem łacińskim (Romaji).
Gwarantuje czytelne wyświetlanie transkrypcji mowy w konsoli Windows bez pustych kwadratów (font boxes).
"""

from typing import Optional

try:
    import pykakasi
    _kks = pykakasi.kakasi()
    _PYKAKASI_AVAILABLE = True
except Exception:
    _kks = None
    _PYKAKASI_AVAILABLE = False


def to_romaji(text: str) -> str:
    """
    Konwertuje japoński tekst (Kanji / Hiragana / Katakana) na czytelny zapis w alfabecie łacińskim (Romaji).
    """
    if not text:
        return ""
    
    if _PYKAKASI_AVAILABLE and _kks is not None:
        try:
            result = _kks.convert(text)
            romaji_parts = [item.get("hepburn", "") or item.get("orig", "") for item in result]
            clean_romaji = " ".join(romaji_parts).strip()
            # Łączenie zbędnych spacji wokół znaków interpunkcyjnych
            clean_romaji = clean_romaji.replace(" .", ".").replace(" ,", ",").replace(" !", "!").replace(" ?", "?")
            return clean_romaji
        except Exception:
            pass

    return text
