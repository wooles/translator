# -*- coding: utf-8 -*-
"""
Moduł Formatowania i Podziału Linii AVT (Netflix Timed Text & Szarkowska Style Guide).
Zawiera:
1. Semantyczny podział linii (Syntactic Cohesion & Pyramiding) z bezpiecznym limitem znaków na wiersz.
2. Bezwzględny zakaz potrójnych wierszy (maksymalnie 2 linie w dialogu).
3. Zakaz rozrywania fraz gramatycznych i pozostawiania sierotek (wiszących wyrazów).
4. Kontroler prędkości czytania (CPS - Characters Per Second).
"""

import re
from typing import Tuple, Optional

# Bezpieczna maksymalna liczba znaków na pojedynczy wiersz w napisach filmowych
MAX_LINE_LENGTH = 38

# Maksymalny bezpieczny limit prędkości czytania (Netflix: 17 CPS dla dorosłych)
SAFE_CPS_LIMIT = 17.0

# Słowa, po których KATEGORYCZNIE NIE WOLNO łamać linii (przyimki, spójniki, partykuły)
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
    Dzieli napis na MAKSYMALNIE 2 wiersze z zachowaniem spójności syntaktycznej (AVT)
    oraz struktury piramidy (dolny wiersz dłuższy lub równy górnemu).
    Kategorycznie eliminuje 3-wierszowe schodki i wiszące sierotki.
    """
    if not text:
        return ""

    sep = "\\N" if is_ass else "\n"

    # Wyodrębnienie ewentualnego przedrostka tagów ASS (np. {\pos(..)})
    prefix_match = re.match(r"^((?:\{[^}]+\})+)", text)
    ts_prefix = prefix_match.group(1) if prefix_match else ""
    raw_content = text[len(ts_prefix):].strip()

    # Zastępujemy wszystkie istniejące łamania pojedynczą spacją, aby zrekonstruować idealny 2-liniowy podział
    normalized_content = re.sub(r"\\N|\\n|\n", " ", raw_content)
    normalized_content = re.sub(r"\s+", " ", normalized_content).strip()

    clean_full = clean_text_for_len(normalized_content)
    if len(clean_full) <= max_line_len:
        return f"{ts_prefix}{normalized_content}"

    words = normalized_content.split()
    if len(words) <= 1:
        return f"{ts_prefix}{normalized_content}"

    best_split_idx = -1
    best_score = -999999.0

    total_clean_len = len(clean_full)
    target_midpoint = total_clean_len / 2.0

    for i in range(1, len(words)):
        left_words = words[:i]
        right_words = words[i:]

        left_str = " ".join(left_words)
        right_str = " ".join(right_words)

        len_left = len(clean_text_for_len(left_str))
        len_right = len(clean_text_for_len(right_str))

        score = 0.0

        # Kary za przekroczenie docelowej długości linii
        if len_left > max_line_len:
            score -= (len_left - max_line_len) * 300.0
        if len_right > max_line_len:
            score -= (len_right - max_line_len) * 300.0

        last_word_left = re.sub(r"[^\w]", "", left_words[-1].lower())
        first_word_right = re.sub(r"[^\w]", "", right_words[0].lower())

        # 1. Bezwzględna kara za łamanie po przyimkach i spójnikach (sierotki)
        if last_word_left in NO_BREAK_AFTER:
            score -= 1000.0

        # 2. Kara za pojedyncze wiszące słowo na początku lub końcu (mniej niż 2 słowa)
        if len(left_words) == 1:
            score -= 300.0
        if len(right_words) == 1:
            score -= 300.0

        # 3. Bonus za podział po znakach interpunkcyjnych kończących zdanie/frazę
        if left_words[-1].endswith((".", "!", "?", "...", ":", ";")):
            score += 250.0
        elif left_words[-1].endswith(","):
            score += 150.0
        elif left_words[-1].endswith(("—", "-")):
            score += 120.0

        # 4. Bonus za podział przed spójnikami podrzędnymi
        if first_word_right in {"że", "bo", "ponieważ", "więc", "jeśli", "gdy", "kiedy", "chociaż", "dlatego", "który", "która", "które"}:
            score += 140.0

        # 5. Zasada piramidy (Pyramiding - Netflix AVT): Dolny wiersz powinien być dłuższy od górnego (lub zbliżony)
        diff = len_right - len_left
        if 0 <= diff <= 16:
            score += 250.0  # Bardzo wysoki bonus za prawidłową piramidę (dół dłuższy lub równy)
        elif diff < 0:
            score -= abs(diff) * 25.0  # Surowa kara za odwróconą piramidę (góra dłuższa od dołu)

        # 6. Balans długości względem środka
        balance_penalty = abs(len_left - target_midpoint) * 2.0
        score -= balance_penalty

        if score > best_score:
            best_score = score
            best_split_idx = i

    if best_split_idx != -1:
        line1 = " ".join(words[:best_split_idx]).strip()
        line2 = " ".join(words[best_split_idx:]).strip()
        return f"{ts_prefix}{line1}{sep}{line2}"

    # Bezpieczny podział w połowie słów
    mid = len(words) // 2
    return f"{ts_prefix}{' '.join(words[:mid])}{sep}{' '.join(words[mid:])}"
