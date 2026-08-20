# -*- coding: utf-8 -*-
"""
Moduł Automatycznego Kolorowania i Dopasowywania Stylów ASS (Typesetting Auto-Color Matcher).
Analizuje wycinki klatek wideo (Pillow) dla napisów ekranowych (Signs / Typesetting)
i automatycznie generuje estetyczne tagi kolorystyczne ASS {\\1c&HBBGGRR&}.
"""

import os
from typing import Optional, Tuple
from PIL import Image

def rgb_to_ass_hex(r: int, g: int, b: int) -> str:
    """Konwertuje kolor RGB na format ASS BGR (&HBBGGRR&)."""
    return f"&H{b:02X}{g:02X}{r:02X}&"

class TypesettingColorMatcher:
    def __init__(self):
        pass

    @classmethod
    def extract_dominant_accent_color(cls, image_path: str, region: str = "top") -> Optional[str]:
        """
        Pobiera wycinek klatki wideo i znajduje dominujący, nasycony kolor akcentu (np. kolor napisu/szyldu).
        Zwraca string koloru w formacie ASS BGR: '&HBBGGRR&' lub None.
        """
        if not image_path or not os.path.exists(image_path):
            return None

        try:
            with Image.open(image_path) as img:
                img = img.convert("RGB")
                w, h = img.size

                # Wybór regionu analizy
                if region == "top":
                    box = (0, 0, w, int(h * 0.4))
                elif region == "bottom":
                    box = (0, int(h * 0.6), w, h)
                else:
                    box = (int(w * 0.15), int(h * 0.2), int(w * 0.85), int(h * 0.8))

                crop = img.crop(box)
                # Zmniejszenie próbki dla szybkości
                crop.thumbnail((120, 120), Image.Resampling.BOX)

                # Kwantyzacja do 16 dominujących kolorów
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

                    # Obliczanie nasycenia (Saturation)
                    max_c = max(r, g, b)
                    min_c = min(r, g, b)
                    delta = max_c - min_c
                    sat = delta / (max_c + 1e-5)
                    brightness = (r + g + b) / 3.0

                    # Odrzucamy mdłe szarości, czyste czernie i czyste biele
                    if brightness < 35 or brightness > 245 or sat < 0.25:
                        continue

                    # Punktacja: kompromis między nasyceniem a popularnością koloru
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
    def enhance_typesetting_prefix(cls, original_prefix: str, image_path: Optional[str] = None) -> str:
        """
        Wzbogaca prefiks tagów ASS o kolor {\1c&H...&} pobrany z obrazu,
        jeśli w tagach nie ma jeszcze zdefiniowanego koloru.
        """
        if not original_prefix:
            original_prefix = ""

        # Jeśli kolor jest już zdefiniowany ręcznie, zachowaj
        if r"\c&H" in original_prefix or r"\1c&H" in original_prefix:
            return original_prefix

        if image_path:
            region = "top" if (r"\an8" in original_prefix or r"\an7" in original_prefix) else "center"
            ass_color = cls.extract_dominant_accent_color(image_path, region=region)
            if ass_color:
                # Wstawienie koloru z delikatnym czarnym obrysem
                color_tag = f"{{\\1c{ass_color}\\3c&H000000&}}"
                return f"{color_tag}{original_prefix}"

        return original_prefix
