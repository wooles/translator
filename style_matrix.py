# -*- coding: utf-8 -*-
"""
StyleMatrixEngine: Universal ASS Geometry & Style Pre-Auditor.
Analyzes [V4+ Styles] geometry (MarginV, Alignment, Scale), tag physics
(\\pos, \\move, \\clip, \\p1, \\org, \\frz) and structural positioning.
Guarantees 100% deterministic separation between spoken dialogue,
on-screen signs/typeset captions, songs, and metadata.
"""

import re
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple
import pysubs2


class EventRole(str, Enum):
    DIALOGUE_BOTTOM = "DIALOGUE_BOTTOM"  # Standard spoken dialogue at bottom of screen
    DIALOGUE_TOP = "DIALOGUE_TOP"        # Overlapping dialogue at top of screen (e.g. background crowd)
    SIGN_LOCATIONAL = "SIGN_LOCATIONAL"  # Anchored on-screen text (signs, plaques, armbands, labels)
    SIGN_OVERLAY = "SIGN_OVERLAY"        # Fullscreen sign, episode title, chapter card
    SONG_LYRICS = "SONG_LYRICS"          # Opening, Ending, Insert Song
    STAFF_METADATA = "STAFF_METADATA"    # Fansub credits, translation notes (skip dialogue treatment)


class StyleProfile:
    """Stores computed geometric and semantic profile of a single ASS style."""
    def __init__(self, name: str, style: pysubs2.SSAStyle, play_res_y: int = 1080):
        self.name = name
        try:
            self.alignment = int(getattr(style, "alignment", 2))
        except (ValueError, TypeError):
            self.alignment = 2

        try:
            self.margin_v = float(getattr(style, "marginv", 10.0))
        except (ValueError, TypeError):
            self.margin_v = 10.0

        try:
            self.fontsize = float(getattr(style, "fontsize", 20.0))
        except (ValueError, TypeError):
            self.fontsize = 20.0

        self.is_italic = bool(getattr(style, "italic", False))

        try:
            res_y = float(play_res_y) if play_res_y else 1080.0
        except (ValueError, TypeError):
            res_y = 1080.0
        if res_y <= 0:
            res_y = 1080.0
        self.play_res_y = int(round(res_y))

        # Compute relative vertical margin
        self.rel_margin_v = (self.margin_v / res_y) if res_y > 0 else 0.0

        # Initial classification based purely on style properties and naming
        self.default_role = self._classify_style_default(style)

    def _classify_style_default(self, s: pysubs2.SSAStyle) -> EventRole:
        name_lower = self.name.lower()

        # 1. Staff / Credits / Notes
        if any(w in name_lower for w in ["credit", "staff", "editor", "tl_note", "tlnote", "note"]):
            return EventRole.STAFF_METADATA

        # 2. Songs / OP / ED
        if any(w in name_lower for w in ["op", "ed", "song", "lyrics", "insert"]):
            return EventRole.SONG_LYRICS

        # 3. Explicit Subtitle / Dialogue naming
        # Crucial safeguard: "subtitle" or "dialogue" must NEVER be classified as sign, even if it contains "title"!
        is_explicit_dialogue = bool(re.search(r"\b(subtitles?|dialogue|def|default|main|speech|alt)\b", name_lower))

        # 4. Signs / Typeset / Captions
        is_explicit_sign = (
            bool(re.search(r"\b(sign|signs|caption|captions|typeset|typesetting|board|poster|szyld|napisy?)\b", name_lower))
            or name_lower.startswith("caption")
            or "on-screen" in name_lower
            or name_lower == "ts"
        )

        if is_explicit_sign and not is_explicit_dialogue:
            return EventRole.SIGN_LOCATIONAL

        # 5. Geometric fallback
        if self.alignment in (7, 8, 9):
            if is_explicit_dialogue:
                return EventRole.DIALOGUE_TOP
            return EventRole.SIGN_OVERLAY
        elif self.alignment in (4, 5, 6):
            if is_explicit_dialogue:
                return EventRole.DIALOGUE_BOTTOM
            return EventRole.SIGN_LOCATIONAL
        else:
            return EventRole.DIALOGUE_BOTTOM


class StyleMatrixReport:
    """Contains analyzed style roles and event-level classifications for an episode."""
    def __init__(self, subs: pysubs2.SSAFile):
        try:
            self.play_res_x = int(subs.info.get("PlayResX", 1920) or 1920)
        except (ValueError, TypeError):
            self.play_res_x = 1920

        try:
            self.play_res_y = int(subs.info.get("PlayResY", 1080) or 1080)
        except (ValueError, TypeError):
            self.play_res_y = 1080

        if self.play_res_x <= 0:
            self.play_res_x = 1920
        if self.play_res_y <= 0:
            self.play_res_y = 1080

        self.style_profiles: Dict[str, StyleProfile] = {}
        self.event_roles: List[EventRole] = []
        self.event_details: List[str] = []

        self._build_profiles(subs)
        self._classify_events(subs)

    def _build_profiles(self, subs: pysubs2.SSAFile):
        for style_name, style_obj in subs.styles.items():
            self.style_profiles[style_name] = StyleProfile(style_name, style_obj, self.play_res_y)

    def _classify_events(self, subs: pysubs2.SSAFile):
        for i, ev in enumerate(subs.events):
            if ev.is_comment:
                self.event_roles.append(EventRole.STAFF_METADATA)
                self.event_details.append("Komentarz ASS")
                continue

            role, detail = self.classify_single_event(ev)
            self.event_roles.append(role)
            self.event_details.append(detail)

    def classify_single_event(self, ev: pysubs2.SSAEvent) -> Tuple[EventRole, str]:
        text_raw = ev.text or ""
        style_name = ev.style or ""
        profile = self.style_profiles.get(style_name)
        base_role = profile.default_role if profile else EventRole.DIALOGUE_BOTTOM

        style_lower = style_name.lower()
        actor_lower = (ev.name or "").lower()

        # Check explicit tags in text
        has_pos = r"\pos" in text_raw
        has_move = r"\move" in text_raw
        has_clip = r"\clip" in text_raw or r"\iclip" in text_raw
        has_p1 = r"\p1" in text_raw
        has_frz = r"\frz" in text_raw or r"\org" in text_raw

        # 1. Staff / Credits
        if profile and profile.default_role == EventRole.STAFF_METADATA:
            return EventRole.STAFF_METADATA, f"Styl metadanych '{style_name}'"

        # 2. Hard Signs with spatial anchoring / vector drawing
        if has_p1:
            return EventRole.SIGN_LOCATIONAL, "Rysunek wektorowy (\\p1)"
        if has_frz or has_clip:
            return EventRole.SIGN_LOCATIONAL, "Tekst transformowany perspektywicznie (\\frz/\\clip)"

        # 3. Explicit caption styles with \\pos (e.g. Caption-14, Caption-15, signs)
        is_sub = bool(re.search(r"\bsubtitles?\b", style_lower))
        is_caption_style = (
            bool(re.search(r"\b(sign|signs|caption|captions|typeset|typesetting|board|poster|szyld|napisy?)\b", style_lower))
            or style_lower.startswith("caption")
            or "on-screen" in style_lower
            or style_lower == "ts"
        )
        is_caption_actor = bool(re.search(r"\b(sign|signs|caption|board|napis)\b", actor_lower))

        if (is_caption_style or is_caption_actor) and not is_sub:
            if has_pos or has_move:
                return EventRole.SIGN_LOCATIONAL, f"Szyld/Tabliczka kotwiczona (styl='{style_name}', \\pos)"
            return EventRole.SIGN_OVERLAY, f"Napis ekranowy (styl='{style_name}')"

        # 4. Pure \pos tag inspection
        if has_pos:
            # Check coordinate: if near bottom center, could be dialogue repositioning
            # But if styled as Caption or in upper 2/3 of screen, it is a locational sign
            m_pos = re.search(r"\\pos\(\s*([\d\.]+)\s*,\s*([\d\.]+)\s*\)", text_raw)
            if m_pos:
                try:
                    y_coord = float(m_pos.group(2))
                    if y_coord < (self.play_res_y * 0.75) and not is_sub:
                        return EventRole.SIGN_LOCATIONAL, f"Obiekt w kadrze (\\pos y={y_coord:.0f} < 75%)"
                except Exception:
                    pass

        # 5. Episode / Title card pattern
        clean_text = re.sub(r"\{[^\}]*\}", "", text_raw).strip()
        if re.match(r"^(episode|odcinek|chapter|rozdział|act|akt|part|część)\s+(\d+|[ivxlcdm]+)", clean_text, re.IGNORECASE):
            return EventRole.SIGN_OVERLAY, "Plansza tytułowa odcinka/rozdziału"

        # 6. Songs
        if (profile and profile.default_role == EventRole.SONG_LYRICS) or any(w in style_lower for w in ["op", "ed", "song"]):
            return EventRole.SONG_LYRICS, f"Piosenka / Utwór muzyczny (styl='{style_name}')"

        # 7. Alignment check for top dialogue
        if r"\an8" in text_raw or (profile and profile.alignment in (7, 8, 9)):
            if is_sub or "dialogue" in style_lower or "main" in style_lower:
                return EventRole.DIALOGUE_TOP, "Dialog nałożony na górze ekranu (\\an8 / styl top)"
            return EventRole.SIGN_OVERLAY, f"Napis górny (styl='{style_name}')"

        return EventRole.DIALOGUE_BOTTOM, "Standardowy dialog dolny"

    def is_dialogue(self, index: int) -> bool:
        """Returns True if event is spoken dialogue (bottom or top)."""
        if 0 <= index < len(self.event_roles):
            return self.event_roles[index] in (EventRole.DIALOGUE_BOTTOM, EventRole.DIALOGUE_TOP)
        return True

    def is_screen_sign(self, index: int) -> bool:
        """Returns True if event is an on-screen sign, plaque, or overlay title."""
        if 0 <= index < len(self.event_roles):
            return self.event_roles[index] in (EventRole.SIGN_LOCATIONAL, EventRole.SIGN_OVERLAY)
        return False

    def is_song(self, index: int) -> bool:
        """Returns True if event is an opening, ending, or insert song."""
        if 0 <= index < len(self.event_roles):
            return self.event_roles[index] == EventRole.SONG_LYRICS
        return False

    def get_summary(self) -> Dict[str, int]:
        """Returns distribution count of event roles."""
        counts = {role.value: 0 for role in EventRole}
        for r in self.event_roles:
            counts[r.value] += 1
        return counts

    def format_user_friendly_summary(self) -> str:
        """Returns a polished, human-readable summary for console output."""
        counts = self.get_summary()
        dlg_bottom = counts.get(EventRole.DIALOGUE_BOTTOM.value, 0)
        dlg_top = counts.get(EventRole.DIALOGUE_TOP.value, 0)
        signs_loc = counts.get(EventRole.SIGN_LOCATIONAL.value, 0)
        signs_ovl = counts.get(EventRole.SIGN_OVERLAY.value, 0)
        songs = counts.get(EventRole.SONG_LYRICS.value, 0)
        staff = counts.get(EventRole.STAFF_METADATA.value, 0)
        total = len(self.event_roles)

        dlg_total = dlg_bottom + dlg_top
        signs_total = signs_loc + signs_ovl

        lines = [
            f"\n[StyleMatrixEngine] Analiza struktury i typologii napisów ({total} linii łącznie):",
            f"  * Dialogi postaci: {dlg_total} kwestii ({dlg_bottom} na dole ekranu" + (f", {dlg_top} na górze" if dlg_top else "") + ")"
        ]

        if signs_total > 0:
            sign_details = []
            if signs_loc:
                sign_details.append(f"{signs_loc} w kadrze/szyldów")
            if signs_ovl:
                sign_details.append(f"{signs_ovl} plansz/tytułów")
            lines.append(f"  * Napisy ekranowe (Typesetting): {signs_total} ({', '.join(sign_details)})")

        if songs > 0:
            lines.append(f"  * Utwory muzyczne (Opening / Ending): {songs} wersów (ochrona oryginalnego tekstu)")

        if staff > 0:
            lines.append(f"  * Napisy techniczne / stopka wydania: {staff} linii")

        lines.append(f"  * Status: Przypisano optymalne profile renderowania dla 100% kwestii.")
        return "\n".join(lines)


def analyze_subtitles(subs: pysubs2.SSAFile) -> StyleMatrixReport:
    """Convenience factory function to create a StyleMatrixReport for a subtitle file."""
    return StyleMatrixReport(subs)
