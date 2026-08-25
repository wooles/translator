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
    def calculate_optimal_sign_position(cls, sign_type: str = "sign", region: Optional[str] = None) -> str:
        """
        Wylicza optymalne tagi pozycjonowania ASS (\\anX / \\pos), aby napis ekranowy (szyld, tablica, list, SMS)
        nie kolidował z głównym dialogiem na dole ekranu.
        """
        st = (sign_type or "").lower()
        reg = (region or "").lower()

        if "header" in st or "title" in st or "tytuł" in st or reg == "top":
            return r"{\an8\pos(960,100)}"
        elif "left" in st or reg == "top_left":
            return r"{\an7\pos(150,150)}"
        elif "right" in st or reg == "top_right":
            return r"{\an9\pos(1770,150)}"
        elif "center" in st or "card" in st or "phone" in st or "sms" in st or "letter" in st or "list" in st:
            return r"{\an5\pos(960,540)}"
        elif "screen" in st or "sign" in st or "plansza" in st:
            return r"{\an8\pos(960,120)}"
        else:
            return r"{\an8}"

    @classmethod
    def enhance_typesetting_prefix(cls, original_prefix: str, image_path: Optional[str] = None) -> str:
        """
        Wzbogaca prefiks tagów ASS o kolor {\\1c&H...&} pobrany z obrazu,
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

    @classmethod
    def enhance_sign_typesetting(
        cls,
        original_prefix: str = "",
        sign_type: str = "sign",
        image_path: Optional[str] = None,
        region: Optional[str] = None
    ) -> str:
        """
        Kompleksowe formatowanie Typesetting 2.0:
        1. Nadaje bezpieczną pozycję (np. góra ekranu \\an8 lub środek \\an5), jeśli brak pozycji.
        2. Pobiera adaptacyjny kolor z wycinka klatki wideo.
        3. Dodaje czytelny obrys i pogrubienie.
        """
        prefix = original_prefix or ""

        # 1. Pozycjonowanie, jeśli brak tagu wyrównania / pozycji
        if not (r"\an" in prefix or r"\pos" in prefix):
            pos_tag = cls.calculate_optimal_sign_position(sign_type=sign_type, region=region)
            prefix = f"{pos_tag}{prefix}"

        # 2. Kolorowanie z obrazu
        prefix = cls.enhance_typesetting_prefix(prefix, image_path=image_path)

        # 3. Zapewnienie obrysu, jeśli brak
        if r"\3c&H" not in prefix:
            prefix = f"{{\\3c&H000000&\\bord2}}{prefix}"

        return prefix
