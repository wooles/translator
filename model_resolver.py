# -*- coding: utf-8 -*-
"""
Moduł Automatycznego Wykrywania Najnowszych Modeli Gemini (Model Auto-Discovery & Version Resolver).
Automatycznie odpytuje API Google i wybiera najwyższe, najnowsze wersje modeli Flash i Pro
(np. Gemini 3.7 Flash, Gemini 3.1 Pro, a w przyszłości 3.8, 4.0 itd.), gwarantując, że tłumacz
zawsze korzysta z absolutnie najświeższych i najinteligentniejszych wersji bez zmian w kodzie.
"""

import re
import logging
from typing import Dict, Optional, List, Tuple
from google import genai

logger = logging.getLogger("model_resolver")


def _extract_model_score(model_name: str) -> Tuple[int, int, int]:
    """
    Ekstraktuje wersję liczbową z nazwy modelu do precyzyjnego sortowania.
    np. 'models/gemini-3.7-flash' -> (3, 7, 0)
        'models/gemini-2.5-pro'   -> (2, 5, 0)
        'models/gemini-3.1-pro-preview' -> (3, 1, 0)
    """
    clean_name = model_name.replace("models/", "").lower()
    
    # Wykrywanie numerów wersji np. 3.7, 3.6, 3.5, 4.0, 2.5
    match = re.search(r"gemini-(\d+)(?:\.(\d+))?(?:\.(\d+))?", clean_name)
    if match:
        major = int(match.group(1))
        minor = int(match.group(2)) if match.group(2) else 0
        patch = int(match.group(3)) if match.group(3) else 0
        return (major, minor, patch)
        
    return (0, 0, 0)


def resolve_best_models(client: Optional[genai.Client] = None) -> Dict[str, str]:
    """
    Automatycznie analizuje dostępne modele w Google AI Studio dla danego klucza API
    i zwraca słownik z najnowszymi wersjami dla każdej klasy:
    - 'flash': Najnowszy, najpotężniejszy model Flash (np. gemini-3.7-flash lub gemini-3.6-flash)
    - 'flash_lite': Najszybszy, lekki model Flash-Lite (np. gemini-3.5-flash-lite)
    - 'pro': Flagowy model klasy Pro (np. gemini-3.1-pro-preview)
    """
    # Domyślne sprawdzone modele bazowe (zawsze najwyższa jakość)
    defaults = {
        "flash": "gemini-3.7-flash",
        "flash_lite": "gemini-3.5-flash-lite",
        "pro": "gemini-3.1-pro-preview"
    }

    if not client:
        return defaults

    try:
        raw_models = list(client.models.list())
        
        flash_candidates = []
        flash_lite_candidates = []
        pro_candidates = []

        # Odrzucamy modele specjalizowane oraz niestabilne, nieoznaczone wersją aliasy -latest
        excluded_keywords = ["image", "tts", "audio", "live", "robotics", "embedding", "customtools", "latest"]

        for m in raw_models:
            name = m.name.replace("models/", "")
            name_lower = name.lower()

            # Odrzucamy modele specjalizowane (same audio, sam obraz, tts)
            if any(k in name_lower for k in excluded_keywords):
                continue

            if "gemini" not in name_lower:
                continue

            # Klasyfikacja do kategorii
            if "flash-lite" in name_lower:
                flash_lite_candidates.append(name)
            elif "flash" in name_lower:
                flash_candidates.append(name)
            elif "pro" in name_lower:
                pro_candidates.append(name)

        # Sortowanie po najwyższej wersji
        flash_sorted = sorted(flash_candidates, key=_extract_model_score, reverse=True)
        flash_lite_sorted = sorted(flash_lite_candidates, key=_extract_model_score, reverse=True)
        pro_sorted = sorted(pro_candidates, key=_extract_model_score, reverse=True)

        best_flash = flash_sorted[0] if flash_sorted else defaults["flash"]
        best_flash_lite = flash_lite_sorted[0] if flash_lite_sorted else defaults["flash_lite"]
        best_pro = pro_sorted[0] if pro_sorted else defaults["pro"]

        return {
            "flash": best_flash,
            "flash_lite": best_flash_lite,
            "pro": best_pro
        }

    except Exception as e:
        logger.warning(f"Nie udało się dynamicznie pobrać listy modeli ({e}). Użyto wersji stabilnych.")
        return defaults
