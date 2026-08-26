# -*- coding: utf-8 -*-
"""
Japanese text conversion helper (Kanji / Kana to Romaji phonetic transcription).
Guarantees clean display of Japanese speech transcription in Windows console without missing font boxes.
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
    Converts Japanese text (Kanji / Hiragana / Katakana) into readable Latin alphabet transcription (Hepburn Romaji).
    """
    if not text:
        return ""
    
    if _PYKAKASI_AVAILABLE and _kks is not None:
        try:
            result = _kks.convert(text)
            romaji_parts = [item.get("hepburn", "") or item.get("orig", "") for item in result]
            clean_romaji = " ".join(romaji_parts).strip()
            # Collapse whitespace around punctuation marks
            clean_romaji = clean_romaji.replace(" .", ".").replace(" ,", ",").replace(" !", "!").replace(" ?", "?")
            return clean_romaji
        except Exception:
            pass

    return text
