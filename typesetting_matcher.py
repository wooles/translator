# -*- coding: utf-8 -*-
"""
ASS Subtitle Typesetting & Auto-Color Matcher Module.
Analyzes video frame crops (Pillow) for on-screen signs/typesetting
and automatically generates aesthetic ASS color tags {\\1c&HBBGGRR&}.
"""

import os
import re
from typing import Optional, Tuple
from PIL import Image

def rgb_to_ass_hex(r: int, g: int, b: int) -> str:
    """Converts RGB color tuple to ASS BGR format (&HBBGGRR&)."""
    return f"&H{b:02X}{g:02X}{r:02X}&"

class TypesettingColorMatcher:
    def __init__(self):
        pass

    @classmethod
    def extract_dominant_accent_color(cls, image_path: str, region: str = "top") -> Optional[str]:
        """
        Extracts video frame crop and identifies dominant, saturated accent color (e.g. sign text color).
        Returns ASS BGR color string: '&HBBGGRR&' or None.
        """
        if not image_path or not os.path.exists(image_path):
            return None

        try:
            with Image.open(image_path) as img:
                img = img.convert("RGB")
                w, h = img.size

                # Select region for color extraction
                if region == "top":
                    box = (0, 0, w, int(h * 0.4))
                elif region == "bottom":
                    box = (0, int(h * 0.6), w, h)
                else:
                    box = (int(w * 0.15), int(h * 0.2), int(w * 0.85), int(h * 0.8))

                crop = img.crop(box)
                # Downscale for performance
                crop.thumbnail((120, 120), Image.Resampling.BOX)

                # Quantize to 16 adaptive colors
                quantized = crop.convert("P", palette=Image.ADAPTIVE, colors=16)
                palette = quantized.getpalette()  # [R, G, B, R, G, B, ...]
                color_counts = quantized.getcolors()

                if not color_counts or not palette:
                    return None

                best_color = None
                best_score = -1.0

                for count, idx in color_counts:
                    r = palette[idx * 3]
                    g = palette[idx * 3 + 1]
                    b = palette[idx * 3 + 2]

                    # Calculate color saturation
                    max_c = max(r, g, b)
                    min_c = min(r, g, b)
                    delta = max_c - min_c
                    sat = delta / (max_c + 1e-5)
                    brightness = (r + g + b) / 3.0

                    # Filter out dark/murky colors, dull grays, and pure blacks (AVT Contrast Guard)
                    # Subtitle text MUST have high luminance (brightness >= 160) to ensure readability
                    if brightness < 160 or brightness > 252 or sat < 0.20:
                        continue

                    # Score: balance between saturation and color area
                    score = (sat * 1.5) * (count ** 0.5)
                    if score > best_score:
                        best_score = score
                        best_color = (r, g, b)

                if best_color:
                    return rgb_to_ass_hex(*best_color)

        except Exception:
            pass

        return None

    @classmethod
    def calculate_optimal_sign_position(cls, sign_type: str = "sign", region: Optional[str] = None) -> str:
        """
        Calculates optimal ASS positioning tags (\\anX / \\pos) to ensure on-screen signs
        are positioned in the vicinity of the original visual text (Typesetting Proximity).
        """
        st = (sign_type or "").lower()
        reg = (region or "").lower().strip()

        # 1. Exact Quadrant Mapping (Typesetting Proximity)
        if reg in ["bottom_right", "right_bottom", "br", "dolny_prawy", "prawy_dolny"]:
            return r"{\an3\pos(1750,920)}"
        elif reg in ["bottom_left", "left_bottom", "bl", "dolny_lewy", "lewy_dolny"]:
            return r"{\an1\pos(170,920)}"
        elif reg in ["top_right", "right_top", "tr", "gorny_prawy", "prawy_gorny"]:
            return r"{\an9\pos(1750,150)}"
        elif reg in ["top_left", "left_top", "tl", "gorny_lewy", "lewy_gorny"]:
            return r"{\an7\pos(170,150)}"
        elif reg in ["center", "srodek", "middle"]:
            return r"{\an5\pos(960,540)}"
        elif reg in ["bottom_center", "bottom", "dol", "dolny"]:
            return r"{\an2\pos(960,920)}"
        elif reg in ["top_center", "top", "gora", "gorny"]:
            return r"{\an8\pos(960,100)}"

        # 2. Fallback based on semantic sign type
        if "bottom_right" in st:
            return r"{\an3\pos(1750,920)}"
        elif "bottom_left" in st:
            return r"{\an1\pos(170,920)}"
        elif "left" in st:
            return r"{\an7\pos(150,150)}"
        elif "right" in st:
            return r"{\an9\pos(1770,150)}"
        elif any(k in st for k in ["card", "phone", "sms", "letter", "list", "kartka", "notatka"]):
            return r"{\an5\pos(960,540)}"
        elif any(k in st for k in ["header", "title", "tytuł", "screen", "sign", "plansza"]):
            return r"{\an8\pos(960,100)}"
        else:
            return r"{\an8}"

    @classmethod
    def enhance_typesetting_prefix(cls, original_prefix: str, image_path: Optional[str] = None) -> str:
        """
        Enriches ASS tag prefix with high-contrast color tag {\\1c&H...&\\3c&H000000&\\bord3}
        sampled from the image if color is not already defined in the tags.
        Guarantees white fill fallback {\\1c&HFFFFFF&} if scene is dark.
        """
        if not original_prefix:
            original_prefix = ""

        # If color is already explicitly defined, preserve it
        if r"\c&H" in original_prefix or r"\1c&H" in original_prefix:
            return original_prefix

        ass_color = None
        if image_path:
            region = "top" if (r"\an8" in original_prefix or r"\an7" in original_prefix) else "center"
            ass_color = cls.extract_dominant_accent_color(image_path, region=region)

        # High-contrast fill (sampled bright color or crisp white) with thick black outline (AVT standard)
        fill_color = ass_color if ass_color else "&HFFFFFF&"
        color_tag = f"{{\\1c{fill_color}\\3c&H000000&\\bord3}}"
        return f"{color_tag}{original_prefix}"

    @classmethod
    def enhance_sign_typesetting(
        cls,
        original_prefix: str = "",
        sign_type: str = "sign",
        image_path: Optional[str] = None,
        region: Optional[str] = None
    ) -> str:
        """
        Comprehensive Typesetting 2.0 styling:
        1. Assigns collision-safe position (e.g. top \\an8 or center \\an5) if missing.
        2. Samples adaptive high-contrast accent color from video frame crop (or white fallback).
        3. Adds clean thick black outline (\\bord3) for guaranteed readability.
        """
        prefix = original_prefix or ""

        # 1. Positioning tag: apply quadrant positioning if specific region given or missing
        if region and region.strip():
            pos_tag = cls.calculate_optimal_sign_position(sign_type=sign_type, region=region)
            if r"\pos" not in prefix:
                prefix = re.sub(r"\{\\an\d\}|\\an\d", "", prefix).strip()
            prefix = f"{pos_tag}{prefix}"
        elif not (r"\an" in prefix or r"\pos" in prefix):
            pos_tag = cls.calculate_optimal_sign_position(sign_type=sign_type, region=region)
            prefix = f"{pos_tag}{prefix}"

        # 2. Adaptive high-contrast color matching from image (or white fallback)
        prefix = cls.enhance_typesetting_prefix(prefix, image_path=image_path)

        # 3. Ensure outline tag if missing
        if r"\3c&H" not in prefix:
            prefix = f"{{\\3c&H000000&\\bord3}}{prefix}"

        return prefix
