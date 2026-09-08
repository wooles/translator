# -*- coding: utf-8 -*-
"""
AVT Line Formatting & Segmentation Module (Netflix Timed Text & Szarkowska Style Guide).
Contains:
1. Syntactic line-breaking (Syntactic Cohesion & Pyramiding) with safe character limits per line.
2. Strict prohibition of three-line subtitles (maximum 2 lines per subtitle event).
3. Preservation of grammatical phrases and elimination of orphan words.
4. Reading speed monitoring (CPS - Characters Per Second).
"""

import re
from typing import Tuple, Optional

# Safe maximum number of characters per line in subtitle formatting
MAX_LINE_LENGTH = 38

# Safe reading speed ceiling (Netflix standard: 17 CPS for adult content)
SAFE_CPS_LIMIT = 17.0

# Prepositions and conjunctions after which a line break is strictly prohibited
NO_BREAK_AFTER = {
    "w", "z", "do", "na", "o", "od", "po", "ze", "za", "we", "ku", "bez", "dla",
    "i", "a", "że", "bo", "czy", "by", "jak", "gdy", "co", "nie", "lecz", "ale"
}

def clean_text_for_len(text: str) -> str:
    """Strips ASS/HTML formatting tags for accurate length and CPS measurement."""
    if not text:
        return ""
    # Strip ASS tags {...}
    cleaned = re.sub(r"\{[^}]*\}", "", text)
    # Strip HTML tags
    cleaned = re.sub(r"</?[^>]+>", "", cleaned)
    # Normalize line breaks
    cleaned = cleaned.replace("\\N", " ").replace("\\n", " ").replace("\n", " ")
    return re.sub(r"\s+", " ", cleaned).strip()

def calculate_cps(text: str, start_ms: int, end_ms: int) -> Tuple[float, bool]:
    """
    Calculates reading speed in Characters Per Second (CPS).
    Returns: (cps_value, exceeds_limit_flag)
    """
    duration_s = max(0.3, (end_ms - start_ms) / 1000.0)
    clean = clean_text_for_len(text)
    cps = len(clean) / duration_s
    is_fast = cps > SAFE_CPS_LIMIT
    return round(cps, 1), is_fast

def split_subtitle_syntactically(text: str, max_line_len: int = MAX_LINE_LENGTH, is_ass: bool = True, is_sign: bool = False) -> str:
    """
    Splits subtitle into MAXIMUM 2 lines preserving syntactic cohesion (AVT)
    and pyramiding structure (bottom line longer than or equal to top line).
    For on-screen signs and title cards (is_sign=True) applies narrower limit (max 24 chars/line).
    Eliminates 3-line stairs and hanging single words.
    """
    if not text:
        return ""

    sep = "\\N" if is_ass else "\n"

    # Extract ASS tag prefix (e.g. {\pos(..)})
    prefix_match = re.match(r"^((?:\{[^}]+\})+)", text)
    ts_prefix = prefix_match.group(1) if prefix_match else ""
    raw_content = text[len(ts_prefix):].strip()

    # If event has explicit \pos(x,y) coordinates or side alignment, enforce narrow line limit (max 18 chars)
    is_tight_pos = (r"\pos" in ts_prefix) or (r"\an" in ts_prefix and "an8" not in ts_prefix and "an2" not in ts_prefix)
    is_positioned_sign = is_tight_pos or is_sign

    if is_tight_pos:
        max_line_len = min(max_line_len, 18)
    elif is_sign:
        max_line_len = min(max_line_len, 34)

    # 1. PRESERVE EXPLICIT 2-LINE DIVISION & DUAL-SPEAKER DIALOGUES (Filar LVII / Netflix AVT)
    if ("\\N" in raw_content or "\\n" in raw_content or "\n" in raw_content):
        existing_parts = [p.strip() for p in re.split(r"\\N|\\n|\n", raw_content) if p.strip()]
        if len(existing_parts) == 2:
            is_dual_speaker = (
                existing_parts[0].startswith(("-", "–", "—")) or
                existing_parts[1].startswith(("-", "–", "—"))
            )
            if is_dual_speaker:
                clean_p0 = re.sub(r"^[-–—]\s*", "", existing_parts[0]).strip()
                clean_p1 = re.sub(r"^[-–—]\s*", "", existing_parts[1]).strip()
                return f"{ts_prefix}- {clean_p0}{sep}- {clean_p1}"

            len_p0 = len(clean_text_for_len(existing_parts[0]))
            len_p1 = len(clean_text_for_len(existing_parts[1]))
            target_limit = 22 if is_tight_pos else (36 if is_sign else 42)
            if len_p0 <= target_limit and len_p1 <= target_limit:
                return f"{ts_prefix}{existing_parts[0]}{sep}{existing_parts[1]}"

    # 1b. DETECT IN-LINE DUAL-SPEAKER DIALOGUE TURNS (Filar LVII)
    # E.g. "Gratulacje... - Rozpacz po przegranej..." -> "- Gratulacje...\N- Rozpacz po przegranej..."
    # E.g. "...i utracie wszystkiego... - Dziękuję..." -> "- ...i utracie wszystkiego...\N- Dziękuję..."
    dual_turn_match = re.match(r"^[-–—]?\s*(.+?(?:[.!?…]+|\]|\))\s*)[-–—]\s*([A-ZĄĆĘŁŃÓŚŹŻa-ząćęłńóśźż…\[].+)$", raw_content)
    if dual_turn_match and not is_positioned_sign:
        p1 = re.sub(r"^[-–—]\s*", "", dual_turn_match.group(1)).strip()
        p2 = re.sub(r"^[-–—]\s*", "", dual_turn_match.group(2)).strip()
        return f"{ts_prefix}- {p1}{sep}- {p2}"

    # Normalize existing line breaks into single space to reconstruct clean 2-line break
    normalized_content = re.sub(r"\\N|\\n|\n", " ", raw_content)
    normalized_content = re.sub(r"\s+", " ", normalized_content).strip()

    # 2. AUTOMATIC 2-LINE FORMATTING FOR EPISODE/CHAPTER TITLE CARDS (Filar XCVIII)
    # E.g. "ODCINEK 53 STWORZYĆ OJCZYZNĘ" -> "ODCINEK 53\NSTWORZYĆ OJCZYZNĘ"
    # E.g. "ODCINEK 53: STWORZYĆ OJCZYZNĘ" -> "ODCINEK 53\NSTWORZYĆ OJCZYZNĘ"
    # E.g. "ROZDZIAŁ 12 NOWY POCZĄTEK" -> "ROZDZIAŁ 12\NNOWY POCZĄTEK"
    ep_match = re.match(r"^(ODCINEK|Odcinek|ROZDZIAŁ|Rozdział|AKT|Akt|CZĘŚĆ|Część|EPIZOD|Epizod)\s+(\d+|[IVXLCDM]+)(?:\s*[:–-]\s*|\s+)(.+)$", normalized_content)
    if ep_match:
        ep_prefix = f"{ep_match.group(1)} {ep_match.group(2)}"
        ep_title = ep_match.group(3).strip()
        if ep_title:
            return f"{ts_prefix}{ep_prefix}{sep}{ep_title}"

    clean_full = clean_text_for_len(normalized_content)
    if len(clean_full) <= max_line_len:
        return f"{ts_prefix}{normalized_content}"

    words = normalized_content.split()
    if len(words) <= 1:
        return f"{ts_prefix}{normalized_content}"

    # For long texts (written letters, notes, manifestos, documents > 120 chars, or long signs > 68 chars)
    # wrap into balanced lines of max_line_len to prevent horizontal screen overflow.
    # Spoken dialogue (<= 115 chars) is strictly limited to MAXIMUM 2 LINES.
    should_wrap_multi = (is_positioned_sign and len(clean_full) > max_line_len * 2) or (len(clean_full) > 120)
    if should_wrap_multi:
        wrapped_lines = []
        current_words = []
        current_len = 0
        for w in words:
            w_len = len(clean_text_for_len(w))
            # Split if line exceeds max_line_len or at clause punctuation with sufficient length
            should_break = False
            if current_words:
                if current_len + 1 + w_len > max_line_len:
                    should_break = True
                elif is_positioned_sign and current_words[-1] in ["–", "-", "—", ":"]:
                    should_break = True
                elif current_words[-1].endswith(("!", "?", ".")) and current_len >= 28:
                    should_break = True

            if should_break:
                last_w = re.sub(r"[^\w]", "", current_words[-1].lower())
                # Avoid breaking right after prepositions if possible
                if last_w not in NO_BREAK_AFTER or len(current_words) > 1:
                    wrapped_lines.append(" ".join(current_words))
                    current_words = [w]
                    current_len = w_len
                    continue

            current_words.append(w)
            current_len += (1 + w_len) if current_len > 0 else w_len

        if current_words:
            wrapped_lines.append(" ".join(current_words))
        return f"{ts_prefix}{sep.join(wrapped_lines)}"

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

        # Penalties for exceeding max line length
        if len_left > max_line_len:
            score -= (len_left - max_line_len) * (200.0 if is_positioned_sign else 35.0)
        if len_right > max_line_len:
            score -= (len_right - max_line_len) * (200.0 if is_positioned_sign else 35.0)

        last_word_left = re.sub(r"[^\w]", "", left_words[-1].lower())
        first_word_right = re.sub(r"[^\w]", "", right_words[0].lower())

        # 1. Strict penalty for breaking after prepositions/conjunctions
        if last_word_left in NO_BREAK_AFTER:
            score -= 1000.0

        # 2. Penalty for single hanging word at start or end (disabled for signs where single name at end is normal)
        if not is_positioned_sign:
            if len(left_words) == 1:
                score -= 300.0
            if len(right_words) == 1:
                score -= 300.0

        # 3. Bonus for punctuation breaks at clause boundary & title separators
        if left_words[-1] in ["–", "-", "—", ":"] or left_words[-1].endswith(("–", "-", "—", ":")):
            score += 400.0
        elif left_words[-1].endswith((".", "!", "?", "...", ";")):
            score += 250.0
        elif left_words[-1].endswith(","):
            score += 180.0

        # 4. Bonus for breaking before subordinate conjunctions
        if first_word_right in {"że", "bo", "ponieważ", "więc", "jeśli", "gdy", "kiedy", "chociaż", "dlatego", "który", "która", "które", "by", "aby", "żeby", "jak"}:
            score += 160.0

        # 5. Pyramiding rule (Netflix AVT): bottom line should be longer than or equal to top line (dialogue only)
        if not is_positioned_sign:
            diff = len_right - len_left
            if 0 <= diff <= 16:
                score += 200.0  # High bonus for proper pyramiding
            elif diff < 0:
                score -= abs(diff) * 15.0  # Penalty for inverted pyramid

        # 6. Center balance penalty
        balance_penalty = abs(len_left - target_midpoint) * 2.0
        score -= balance_penalty

        if score > best_score:
            best_score = score
            best_split_idx = i

    if best_split_idx != -1:
        line1 = " ".join(words[:best_split_idx]).strip()
        line2 = " ".join(words[best_split_idx:]).strip()
        return f"{ts_prefix}{line1}{sep}{line2}"

    # Safe midpoint fallback
    mid = len(words) // 2
    return f"{ts_prefix}{' '.join(words[:mid])}{sep}{' '.join(words[mid:])}"


def calculate_condensation_directive(text: str, start_ms: int, end_ms: int) -> Optional[str]:
    """
    Computes reading speed and exposure duration, generating an AVT condensation directive
    for rapid dialogue, panic scenes, and sub-second micro-hesitations.
    """
    duration_s = max(0.2, (end_ms - start_ms) / 1000.0)
    clean = clean_text_for_len(text)
    cps = len(clean) / duration_s
    word_count = len(clean.split())

    if duration_s <= 0.6:
        return f"[⏱️ RYGOR CZASOWY: MIKRO-KWESTIA (<0.6s, czas {duration_s:.1f}s, tempo {cps:.1f} CPS)] -> Kwestia trwa ułamek sekundy! Zredukuj do MAX 1-2 słów (max 6-8 znaków, np. 'Znaczy...', 'Ech...', 'Cóż...'). KATEGORYCZNY ZAKAZ wielowyrazowych zdań!"
    elif duration_s < 1.4 and (cps > 18.0 or word_count > 6):
        return f"[⏱️ RYGOR CZASOWY: EKSTREMALNY (czas {duration_s:.1f}s, tempo {cps:.1f} CPS)] -> Wymóg maksymalnej kondensacji: zredukuj wypowiedź do max 2-3 zwięzłych słów (zetnij zaimki i łączniki, bezwzględnie zachowaj emocję i podtekst)!"
    elif duration_s < 2.5 and cps > 16.0:
        return f"[⏱️ RYGOR CZASOWY: WYSOKI (czas {duration_s:.1f}s, tempo {cps:.1f} CPS)] -> Skondensuj frazę: zetnij zaimki (ja/ty) i watę słowną; bezwzględnie zachowaj emocję i podtekst!"
    elif cps > 20.0:
        return f"[⏱️ RYGOR CZASOWY: WYSOKIE TEMPO ({cps:.1f} CPS)] -> Skróć kwestię: usuń zaimki i łączniki; zachowaj emocję, aby widz zdążył przeczytać bez pauzowania!"

    return None


def clamp_sub_second_cps(text: str, start_ms: int, end_ms: int) -> str:
    """
    Safely clamps sub-second dialogue lines (duration <= 0.6s) to prevent unreadable text walls (Filar CXXXIV).
    If a 0.4s line contains a multi-phrase split with ellipsis (e.g. 'Znaczy... musimy powoli...'),
    retains only the initial hesitation fragment ('Znaczy...').
    """
    if not text or not text.strip():
        return text
    duration_s = (end_ms - start_ms) / 1000.0
    if duration_s > 0.6:
        return text

    clean = clean_text_for_len(text)
    if len(clean) <= 10:
        return text

    # If text contains ellipsis separating thoughts (e.g. 'Znaczy... musimy powoli...')
    if "..." in text:
        parts = text.split("...")
        first_part = parts[0].strip()
        if first_part:
            return f"{first_part}..."
    elif "…" in text:
        parts = text.split("…")
        first_part = parts[0].strip()
        if first_part:
            return f"{first_part}…"

    # If no ellipsis, but length > 10 chars in <= 0.6s, keep max 1-2 words with ellipsis
    words = text.strip().split()
    if len(words) > 1:
        return f"{words[0]}..."

    return text


def snap_subtitles_to_shot_cuts(events: list, shot_cuts_ms: list, max_snap_gap_ms: int = 350) -> list:
    """
    Snaps subtitle event boundaries (start_ms, end_ms) to video shot cuts (Netflix & Belczyk AVT standard).
    Eliminates subtitle flashes when dialogue finishes slightly before or right after a camera cut.
    """
    if not shot_cuts_ms or not events:
        return events

    # Ensure sorted cuts
    sorted_cuts = sorted(shot_cuts_ms)

    for ev in events:
        start = getattr(ev, 'start', 0)
        end = getattr(ev, 'end', 0)

        # Snap start to cut if cut is within [start - max_snap_gap_ms, start]
        for cut in sorted_cuts:
            if 0 <= start - cut <= max_snap_gap_ms:
                ev.start = cut
                break
            elif 0 < cut - start <= 150:
                ev.start = cut
                break

        # Snap end to cut if cut is right after dialogue end within [end, end + max_snap_gap_ms]
        for cut in sorted_cuts:
            if 0 <= cut - end <= max_snap_gap_ms:
                # Snap 40ms before the cut so subtitle clears before camera switches
                ev.end = max(ev.start + 300, cut - 40)
                break
            elif 0 < end - cut <= 150:
                ev.end = max(ev.start + 300, cut - 40)
                break

    return events


def format_diegetic_sound_wall(text: str, is_announcement: bool = False, is_radio_tv: bool = False) -> str:
    """
    Formats secondary background diegetic audio (PA announcements, loudspeakers, TV/radio news)
    to the top of the screen {\\an8}[ KOMUNIKAT: ... ] preventing collision with foreground dialogue.
    """
    if not text:
        return ""

    clean = clean_text_for_len(text)
    if is_announcement:
        return f"{{\\an8}}[ KOMUNIKAT: {clean} ]"
    elif is_radio_tv:
        return f"{{\\an8}}[ WIADOMOŚCI: {clean} ]"

    return text
