# -*- coding: utf-8 -*-
"""
ASS Subtitle Typesetting & Auto-Color Matcher Module.
Analyzes video frame crops (Pillow) for on-screen signs/typesetting
and automatically generates aesthetic ASS color tags {\\1c&HBBGGRR&}.
"""

import os
import re
from typing import Optional, Tuple, Any, List
from PIL import Image
from pydantic import BaseModel, Field

def rgb_to_ass_hex(r: int, g: int, b: int) -> str:
    """Converts RGB color tuple to ASS BGR format (&HBBGGRR&)."""
    return f"&H{b:02X}{g:02X}{r:02X}&"

def hex_to_ass_hex(hex_str: str) -> Optional[str]:
    """Converts #RRGGBB or RRGGBB to ASS BGR format (&HBBGGRR&)."""
    if not hex_str:
        return None
    clean = str(hex_str).strip().lstrip("#")
    if len(clean) == 6:
        try:
            r = int(clean[0:2], 16)
            g = int(clean[2:4], 16)
            b = int(clean[4:6], 16)
            return rgb_to_ass_hex(r, g, b)
        except ValueError:
            return None
    return None

class VisualTypesettingData(BaseModel):
    detected_box_1000: Optional[List[int]] = Field(default=None, description="[ymin, xmin, ymax, xmax] w skali 0-1000 dla japońskiego tekstu/planszy na kadrze")
    placement: Optional[str] = Field(default="above", description="'above' (nad japońskim tekstem), 'below' (pod), 'overlay' (na tekście), 'beside_right' (obok po prawej), 'beside_left' (obok po lewej)")
    rotation_deg: Optional[int] = Field(default=0, description="Kąt obrotu w stopniach (-45 do 45) jeśli tekst na kadrze jest skośny/pod kątem, inaczej 0")
    primary_color_hex: Optional[str] = Field(default=None, description="Kolor wiodący napisu w formacie HEX '#RRGGBB' lub null")
    outline_color_hex: Optional[str] = Field(default=None, description="Kolor obrysu/cienia w formacie HEX '#RRGGBB' lub null")
    font_style_hint: Optional[str] = Field(default=None, description="'comic', 'handwritten', 'clean', 'serif', 'neon' lub null")

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
        Calculates optimal, resolution-independent ASS alignment tags (\\an1 - \\an9)
        to ensure on-screen signs are positioned safely in the vicinity of the original visual text (Typesetting Proximity)
        without clipping or rendering off-screen regardless of PlayResX/Y.
        """
        st = (sign_type or "").lower()
        reg = (region or "").lower().strip()

        # 1. Exact Quadrant Mapping (Typesetting Proximity - Resolution Independent)
        if reg in ["bottom_right", "right_bottom", "br", "dolny_prawy", "prawy_dolny"]:
            return r"{\an3}"
        elif reg in ["bottom_left", "left_bottom", "bl", "dolny_lewy", "lewy_dolny"]:
            return r"{\an1}"
        elif reg in ["top_right", "right_top", "tr", "gorny_prawy", "prawy_gorny"]:
            return r"{\an9}"
        elif reg in ["top_left", "left_top", "tl", "gorny_lewy", "lewy_gorny"]:
            return r"{\an7}"
        elif reg in ["center", "srodek", "middle"]:
            return r"{\an5}"
        elif reg in ["bottom_center", "bottom", "dol", "dolny"]:
            return r"{\an2}"
        elif reg in ["top_center", "top", "gora", "gorny"]:
            return r"{\an8}"

        # 2. Fallback based on semantic sign type
        if "bottom_right" in st:
            return r"{\an3}"
        elif "bottom_left" in st:
            return r"{\an1}"
        elif "left" in st:
            return r"{\an7}"
        elif "right" in st:
            return r"{\an9}"
        elif any(k in st for k in ["card", "phone", "sms", "letter", "list", "kartka", "notatka"]):
            return r"{\an5}"
        elif any(k in st for k in ["header", "title", "tytuł", "screen", "sign", "plansza"]):
            return r"{\an8}"
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

    @classmethod
    def parse_ass_color(cls, color_str: str) -> Optional[Tuple[int, int, int]]:
        """Parses ASS hex color (&HBBGGRR& or &HAABBGGRR&) into (R, G, B) tuple."""
        if not color_str:
            return None
        m = re.search(r"&H([0-9a-fA-F]{6,8})&?", color_str)
        if m:
            clean = m.group(1)
            if len(clean) == 8:
                clean = clean[2:]  # strip alpha
            if len(clean) == 6:
                b = int(clean[0:2], 16)
                g = int(clean[2:4], 16)
                r = int(clean[4:6], 16)
                return (r, g, b)
        return None

    @classmethod
    def calculate_luminance(cls, r: int, g: int, b: int) -> float:
        """Calculates perceived luminance (0.0 to 255.0)."""
        return 0.299 * r + 0.587 * g + 0.114 * b

    @classmethod
    def ensure_sign_contrast(cls, prefix: str, style: Optional[Any] = None) -> str:
        """
        Sign Contrast & Visibility Guard (Filar AVT Contrast Invariance):
        Prevents on-screen signs/tattoos from blending into dark artwork or bright backgrounds.
        1. Checks fill color (\\c or \\1c) and outline color (\\3c) and border width (\\bord).
        2. If fill is dark (luminance < 130) and outline is missing or also dark:
           Enforces high-contrast white outline {\\3c&HFFFFFF&\\bord3}.
        3. If outline is absent (\\bord0 or missing \\3c/\\bord):
           Enforces crisp contrast border (\\bord3 with contrasting outline).
        """
        if not prefix:
            prefix = ""

        # Extract primary fill color (\1c or \c)
        m_fill = re.search(r"\\(?:1c|c)(&H[0-9a-fA-F]+&?)", prefix)
        fill_rgb = cls.parse_ass_color(m_fill.group(1)) if m_fill else None

        # If not in prefix, fallback to style.primarycolor
        if fill_rgb is None and style is not None:
            p_color = getattr(style, "primarycolor", None) or getattr(style, "primary_color", None)
            if p_color is not None and hasattr(p_color, "r"):
                fill_rgb = (p_color.r, p_color.g, p_color.b)

        # Extract outline color (\3c)
        m_out = re.search(r"\\3c(&H[0-9a-fA-F]+&?)", prefix)
        out_rgb = cls.parse_ass_color(m_out.group(1)) if m_out else None

        # If not in prefix, fallback to style.outlinecolor
        if out_rgb is None and style is not None:
            o_color = getattr(style, "outlinecolor", None) or getattr(style, "outline_color", None)
            if o_color is not None and hasattr(o_color, "r"):
                out_rgb = (o_color.r, o_color.g, o_color.b)

        # Extract border width
        m_bord = re.search(r"\\bord(\d+(?:\.\d+)?)", prefix)
        if m_bord:
            border_width = float(m_bord.group(1))
        elif style is not None and hasattr(style, "outline"):
            border_width = float(style.outline)
        else:
            border_width = None

        # Case 1: Fill color is DARK (e.g. black tattoo, dark ink, luminance < 130)
        if fill_rgb is not None:
            fill_lum = cls.calculate_luminance(*fill_rgb)
            if fill_lum < 130:
                out_lum = cls.calculate_luminance(*out_rgb) if out_rgb else 0.0
                # If outline is missing, thin (<= 1.0) or also dark (low contrast)
                if out_rgb is None or border_width is None or border_width <= 1.0 or out_lum < 130:
                    clean_pref = re.sub(r"\\3c&H[0-9a-fA-F]+&?", "", prefix)
                    clean_pref = re.sub(r"\\bord\d+(?:\.\d+)?", "", clean_pref)
                    clean_pref = re.sub(r"\{\s*\}", "", clean_pref).strip()
                    return f"{{\\3c&HFFFFFF&\\bord3}}{clean_pref}"

        # Case 2: Sign has border 0 (\bord0)
        if border_width is not None and border_width == 0:
            clean_pref = re.sub(r"\\bord0(?:\.0+)?", "", prefix)
            clean_pref = re.sub(r"\{\s*\}", "", clean_pref).strip()
            if fill_rgb and cls.calculate_luminance(*fill_rgb) < 130:
                return f"{{\\3c&HFFFFFF&\\bord3}}{clean_pref}"
            else:
                return f"{{\\3c&H000000&\\bord3}}{clean_pref}"

        # Case 3: If no fill color AND no outline was specified at all, ensure safe contrast
        if not m_fill and not m_out and (border_width is None or border_width <= 0):
            if not (r"\3c" in prefix or r"\bord" in prefix):
                return f"{{\\3c&H000000&\\bord3}}{prefix}"

        return prefix

    @classmethod
    def generate_pixel_perfect_ass_tags(
        cls,
        typesetting_data: Any,
        playres_x: int = 1920,
        playres_y: int = 1080,
        prefix: str = "",
        existing_prefix: Optional[str] = None,
        image_path: Optional[str] = None,
        style: Optional[Any] = None
    ) -> str:
        """
        Generates Fansub-Quality Pixel-Perfect ASS tags (\\pos, \\frz, \\1c, \\3c, \\blur, \\bord)
        from Gemini 2D Spatial Grounding metadata (bounding box, placement, rotation, color).
        Preserves custom \\pos(X, Y) if already present in existing_prefix.
        """
        eff_prefix = existing_prefix if existing_prefix is not None else (prefix or "")

        if not typesetting_data:
            return cls.enhance_sign_typesetting(original_prefix=eff_prefix, style=style)

        # Extract typesetting metadata from Pydantic model or dict
        def _get(field: str, default=None):
            if hasattr(typesetting_data, field):
                val = getattr(typesetting_data, field)
                return val if val is not None else default
            elif isinstance(typesetting_data, dict):
                val = typesetting_data.get(field)
                return val if val is not None else default
            return default

        bbox = _get("detected_box_1000")
        placement = str(_get("placement", "above") or "above").lower().strip()
        rotation_deg = _get("rotation_deg", 0)
        primary_hex = _get("primary_color_hex")
        outline_hex = _get("outline_color_hex")
        font_hint = str(_get("font_style_hint", "") or "").lower().strip()
        screen_reg = _get("screen_region")

        tags = []

        # 2. Position Calculation (\pos) from Bounding Box [ymin, xmin, ymax, xmax] in 0..1000
        # If custom position is already defined in existing prefix, preserve it and do NOT calculate new \pos
        has_custom_pos = r"\pos" in eff_prefix
        has_valid_bbox = False

        if not has_custom_pos:
            if bbox and isinstance(bbox, (list, tuple)) and len(bbox) == 4:
                try:
                    ymin, xmin, ymax, xmax = [float(v) for v in bbox]
                    # Sanity check ranges
                    if 0 <= ymin <= 1000 and 0 <= xmin <= 1000 and ymin < ymax <= 1000 and xmin < xmax <= 1000:
                        has_valid_bbox = True
                        b_ymin = (ymin / 1000.0) * playres_y
                        b_xmin = (xmin / 1000.0) * playres_x
                        b_ymax = (ymax / 1000.0) * playres_y
                        b_xmax = (xmax / 1000.0) * playres_x
                        center_x = (b_xmin + b_xmax) / 2.0
                        center_y = (b_ymin + b_ymax) / 2.0

                        if placement == "above":
                            anchor = "an2"  # Bottom-center: sits directly above the Japanese text
                            pos_x = center_x
                            pos_y = max(25.0, b_ymin - 8.0)
                        elif placement == "below":
                            anchor = "an8"  # Top-center: sits directly below the Japanese text
                            pos_x = center_x
                            pos_y = min(float(playres_y) - 25.0, b_ymax + 8.0)
                        elif placement in ["beside_right", "right"]:
                            anchor = "an4"  # Middle-left: sits right of the Japanese text
                            pos_x = min(float(playres_x) - 30.0, b_xmax + 10.0)
                            pos_y = center_y
                        elif placement in ["beside_left", "left"]:
                            anchor = "an6"  # Middle-right: sits left of the Japanese text
                            pos_x = max(30.0, b_xmin - 10.0)
                            pos_y = center_y
                        else:  # overlay / center
                            anchor = "an5"  # Center
                            pos_x = center_x
                            pos_y = center_y

                        # Margin clamping
                        pos_x = max(20.0, min(float(playres_x) - 20.0, pos_x))
                        pos_y = max(20.0, min(float(playres_y) - 20.0, pos_y))

                        tags.append(f"\\{anchor}\\pos({int(round(pos_x))},{int(round(pos_y))})")
                except (ValueError, TypeError):
                    has_valid_bbox = False

            if not has_valid_bbox:
                # Fallback to quadrant alignment
                if screen_reg:
                    pos_tag = cls.calculate_optimal_sign_position(region=screen_reg)
                    tags.append(pos_tag.strip("{}"))
                elif not (r"\an" in eff_prefix or r"\pos" in eff_prefix):
                    tags.append(r"\an8")

        # 3. Rotation Angle (\frz)
        if rotation_deg and r"\frz" not in eff_prefix:
            try:
                rot_float = float(rotation_deg)
                if rot_float != 0:
                    clamped_rot = max(-60.0, min(60.0, rot_float))
                    tags.append(f"\\frz{int(round(clamped_rot))}")
            except (ValueError, TypeError):
                pass

        # 4. Color Matching (\1c and \3c)
        primary_ass = hex_to_ass_hex(primary_hex) if primary_hex else None
        outline_ass = hex_to_ass_hex(outline_hex) if outline_hex else None

        # Sample from image crop if primary color not specified by model
        if not primary_ass and image_path and has_valid_bbox:
            try:
                with Image.open(image_path) as img:
                    w, h = img.size
                    crop_box = (
                        int((xmin / 1000.0) * w),
                        int((ymin / 1000.0) * h),
                        int((xmax / 1000.0) * w),
                        int((ymax / 1000.0) * h)
                    )
                    crop_box = (
                        max(0, crop_box[0] - 5),
                        max(0, crop_box[1] - 5),
                        min(w, crop_box[2] + 5),
                        min(h, crop_box[3] + 5)
                    )
                    if crop_box[2] > crop_box[0] and crop_box[3] > crop_box[1]:
                        crop = img.crop(crop_box)
                        crop.thumbnail((64, 64), Image.Resampling.BOX)
                        q = crop.convert("P", palette=Image.ADAPTIVE, colors=8)
                        pal = q.getpalette()
                        cols = q.getcolors()
                        if cols and pal:
                            cols.sort(key=lambda x: x[0], reverse=True)
                            for cnt, idx in cols:
                                r, g, b = pal[idx*3], pal[idx*3+1], pal[idx*3+2]
                                if 40 < (r + g + b) / 3.0 < 245:
                                    primary_ass = rgb_to_ass_hex(r, g, b)
                                    break
            except Exception:
                pass

        if primary_ass and r"\1c" not in eff_prefix and r"\c&H" not in eff_prefix:
            tags.append(f"\\1c{primary_ass}")

        if outline_ass and r"\3c" not in eff_prefix:
            tags.append(f"\\3c{outline_ass}")

        # 5. Styling Effects (Border, Blur for neon/comic)
        if "comic" in font_hint or "neon" in font_hint or (rotation_deg and abs(float(rotation_deg)) >= 15):
            if r"\blur" not in eff_prefix:
                tags.append(r"\blur1.5")
            if r"\bord" not in eff_prefix and not outline_ass:
                tags.append(r"\bord3")
        elif "paper" in font_hint or "clean" in font_hint:
            if r"\bord" not in eff_prefix:
                tags.append(r"\bord0\shad1")

        new_tags_str = "".join(tags)
        if new_tags_str:
            clean_existing = eff_prefix
            if has_valid_bbox and not has_custom_pos:
                clean_existing = re.sub(r"\{\\an\d\}|\\an\d", "", clean_existing).strip()
            res_prefix = f"{{{new_tags_str}}}{clean_existing}"
        else:
            res_prefix = eff_prefix

        return cls.ensure_sign_contrast(res_prefix, style=style)

