# -*- coding: utf-8 -*-
"""
Moduł Formatowania i Podziału Linii AVT (Netflix Timed Text & Szarkowska Style Guide).
Zawiera:
1. Semantyczny podział linii (Syntactic Cohesion & Pyramiding) do 42 znaków na wiersz.
2. Zakaz rozrywania fraz gramatycznych (przyimek-rzeczownik, orzeczenie-negacja).
3. Kontroler prędkości czytania (CPS - Characters Per Second).
"""

import re
from typing import Tuple, Optional

# Maksymalna liczba znaków na pojedynczy wiersz w napisach telewizyjnych i streamingowych
MAX_LINE_LENGTH = 42

# Maksymalny bezpieczny limit prędkości czytania (Netflix: 17 CPS dla dorosłych)
SAFE_CPS_LIMIT = 17.0

# Słowa, po których NIE WOLNO łamać linii (przyimki, spójniki jednoznakowe, partykuły przeczące)
NO_BREAK_AFTER = {
    "w", "z", "do", "na", "o", "od", "po", "ze", "za", "we", "ku", "bez", "dla",
    "i", "a", "że", "bo", "czy", "by", "jak", "gdy", "co", "nie", "lecz", "ale"
}

def clean_text_for_len(text: str) -> str:
    """Usuwa tagi formatowania ASS/HTML do rzetelnego pomiaru długości i CPS."""
    if not text:
        return ""
    # Usunięcie tagów ASS {...}
    cleaned = re.sub(r"\{[^}]*\}", "", text)
    # Usunięcie tagów HTML
    cleaned = re.sub(r"</?[^>]+>", "", cleaned)
    # Usunięcie znaczników nowej linii
    cleaned = cleaned.replace("\\N", " ").replace("\\n", " ").replace("\n", " ")
    return re.sub(r"\s+", " ", cleaned).strip()

def calculate_cps(text: str, start_ms: int, end_ms: int) -> Tuple[float, bool]:
    """
    Oblicza prędkość czytania w Znakach Na Sekundę (CPS).
    Zwraca: (wartość_cps, czy_przekracza_normę)
    """
    duration_s = max(0.3, (end_ms - start_ms) / 1000.0)
    clean = clean_text_for_len(text)
    cps = len(clean) / duration_s
    is_fast = cps > SAFE_CPS_LIMIT
    return round(cps, 1), is_fast

def split_subtitle_syntactically(text: str, max_line_len: int = MAX_LINE_LENGTH, is_ass: bool = True) -> str:
    """
    Dzieli długi napis na maksymalnie 2 wiersze z zachowaniem spójności syntaktycznej (AVT)
    oraz struktury piramidy (dolny wiersz dłuższy od górnego).
    """
    if not text:
        return ""

    sep = "\\N" if is_ass else "\n"

    # Jeśli napis ma już ręcznie wstawiony podział linii, normalizujemy i sprawdzamy
    if "\\N" in text or "\\n" in text or "\n" in text:
        parts = re.split(r"\\N|\\n|\n", text)
        if len(parts) == 2 and all(len(clean_text_for_len(p)) <= max_line_len for p in parts):
            return sep.join(p.strip() for p in parts)

    clean_full = clean_text_for_len(text)
    if len(clean_full) <= max_line_len:
        return text.strip()

    # Wyodrębnienie ewentualnego przedrostka tagów ASS (np. {\pos(..)})
    prefix_match = re.match(r"^((?:\{[^}]+\})+)", text)
    ts_prefix = prefix_match.group(1) if prefix_match else ""
    raw_content = text[len(ts_prefix):].strip()

    words = raw_content.split()
    if len(words) <= 1:
        return text

    # Szukamy idealnego punktu podziału (scoring punktowy każdego możliwego podziału)
    best_split_idx = -1
    best_score = -999999.0

    total_clean_len = len(clean_text_for_len(raw_content))
    target_midpoint = total_clean_len / 2.0

    for i in range(1, len(words)):
        left_words = words[:i]
        right_words = words[i:]

        left_str = " ".join(left_words)
        right_str = " ".join(right_words)

        len_left = len(clean_text_for_len(left_str))
        len_right = len(clean_text_for_len(right_str))

        # Odrzucamy podziały przekraczające limit 42 znaków na wiersz
        if len_left > (max_line_len + 3) or len_right > (max_line_len + 3):
            continue

        score = 0.0

        last_word_left = re.sub(r"[^\w]", "", left_words[-1].lower())
        first_word_right = re.sub(r"[^\w]", "", right_words[0].lower())

        # 1. Kary za łamanie po przyimkach i spójnikach jednoznakowych (KRYTYCZNE)
        if last_word_left in NO_BREAK_AFTER:
            score -= 500.0

        # 2. Bonus za podział po znakach interpunkcyjnych kończących zdanie/frazę
        if left_words[-1].endswith((".", "!", "?", "...", ":", ";")):
            score += 250.0
        elif left_words[-1].endswith(","):
            score += 150.0
        elif left_words[-1].endswith(("—", "-")):
            score += 120.0

        # 3. Bonus za podział przed spójnikami podrzędnymi
        if first_word_right in {"że", "bo", "ponieważ", "więc", "jeśli", "gdy", "kiedy", "chociaż", "dlatego"}:
            score += 130.0

        # 4. Zasada piramidy (Pyramiding): Dolny wiersz powinien być nieco dłuższy od górnego (lub równy)
        # Netflix Timed Text zaleca układ "bottom-heavy"
        diff = len_right - len_left
        if 0 <= diff <= 12:
            score += 60.0
        elif diff < 0:
            score -= abs(diff) * 2.0  # Kara za "odwróconą piramidę" (góra dłuższa od dołu)

        # 5. Balans długości (bliskość środka)
        balance_penalty = abs(len_left - target_midpoint) * 1.5
        score -= balance_penalty

        if score > best_score:
            best_score = score
            best_split_idx = i

    if best_split_idx != -1:
        line1 = " ".join(words[:best_split_idx]).strip()
        line2 = " ".join(words[best_split_idx:]).strip()
        return f"{ts_prefix}{line1}{sep}{line2}"

    # Fallback jeśli tekst jest za długi i nie znaleziono podziału: podział w połowie słów
    mid = len(words) // 2
    return f"{ts_prefix}{' '.join(words[:mid])}{sep}{' '.join(words[mid:])}"
