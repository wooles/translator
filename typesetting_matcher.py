# -*- coding: utf-8 -*-
"""
ASS Subtitle Typesetting & Auto-Color Matcher Module.
Analyzes video frame crops (Pillow) for on-screen signs/typesetting
and automatically generates aesthetic ASS color tags {\\1c&HBBGGRR&}.
"""

import os
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
        do not collide with dialogue at the bottom of the screen.
        """
        st = (sign_type or "").lower()
        reg = (region or "").lower()

        if "header" in st or "title" in st or "tytuł" in st or reg == "top":
            return r"{\an8\pos(960,100)}"
        elif "left" in st or reg == "top_left":
            return r"{\an7\pos(150,150)}"
        elif "right" in st or reg == "top_right":
            return r"{\an9\pos(1770,150)}"
        elif "center" in st or "card" in st or "phone" in st or "sms" in st or "letter" in st or "list" in st or "kartka" in st or "notatka" in st:
            return r"{\an5\pos(960,540)}"
        elif "screen" in st or "sign" in st or "plansza" in st:
            return r"{\an8\pos(960,120)}"
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

        # 1. Positioning tag if missing
        if not (r"\an" in prefix or r"\pos" in prefix):
            pos_tag = cls.calculate_optimal_sign_position(sign_type=sign_type, region=region)
            prefix = f"{pos_tag}{prefix}"

        # 2. Adaptive high-contrast color matching from image (or white fallback)
        prefix = cls.enhance_typesetting_prefix(prefix, image_path=image_path)

        # 3. Ensure outline tag if missing
        if r"\3c&H" not in prefix:
            prefix = f"{{\\3c&H000000&\\bord3}}{prefix}"

        return prefix
