# -*- coding: utf-8 -*-
"""
Gemini Model Auto-Discovery & Version Resolver Module.
Automatically queries Google API to discover and select the highest, latest model versions
(e.g., Gemini 3.7 Flash, Gemini 3.1 Pro, and future versions like 3.8, 4.0, etc.),
guaranteeing the translator always utilizes the most capable models without manual code changes.
"""

import re
import logging
from typing import Dict, Optional, List, Tuple
from google import genai

logger = logging.getLogger("model_resolver")


def _extract_model_score(model_name: str) -> Tuple[int, int, int]:
    """
    Extracts version numbers from model name for accurate semantic sorting.
    e.g. 'models/gemini-3.7-flash' -> (3, 7, 0)
        'models/gemini-2.5-pro'   -> (2, 5, 0)
        'models/gemini-3.1-pro-preview' -> (3, 1, 0)
    """
    clean_name = model_name.replace("models/", "").lower()
    
    # Detect version numbers e.g. 3.7, 3.6, 3.5, 4.0, 2.5
    match = re.search(r"gemini-(\d+)(?:\.(\d+))?(?:\.(\d+))?", clean_name)
    if match:
        major = int(match.group(1))
        minor = int(match.group(2)) if match.group(2) else 0
        patch = int(match.group(3)) if match.group(3) else 0
        return (major, minor, patch)
        
    return (0, 0, 0)


def resolve_best_models(client: Optional[genai.Client] = None) -> Dict[str, str]:
    """
    Automatically inspects available models in Google AI Studio for the provided API client
    and returns a dictionary with the newest versions for each tier:
    - 'flash': Latest flagship Flash model (e.g. gemini-3.7-flash or gemini-3.6-flash)
    - 'flash_lite': Fastest lightweight Flash-Lite model (e.g. gemini-3.5-flash-lite)
    - 'pro': Flagship Pro class model (e.g. gemini-3.1-pro-preview)
    """
    # Default verified base models (highest quality baseline)
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

        # Filter out specialized models and unversioned aliases
        excluded_keywords = ["image", "tts", "audio", "live", "robotics", "embedding", "customtools", "latest"]

        for m in raw_models:
            name = m.name.replace("models/", "")
            name_lower = name.lower()

            # Skip specialized models (audio-only, vision-only, tts)
            if any(k in name_lower for k in excluded_keywords):
                continue

            if "gemini" not in name_lower:
                continue

            # Classify into tier categories
            if "flash-lite" in name_lower:
                flash_lite_candidates.append(name)
            elif "flash" in name_lower:
                flash_candidates.append(name)
            elif "pro" in name_lower:
                pro_candidates.append(name)

        # Sort by highest version score
        flash_sorted = sorted(flash_candidates, key=_extract_model_score, reverse=True)
        flash_lite_sorted = sorted(flash_lite_candidates, key=_extract_model_score, reverse=True)
        pro_sorted = sorted(pro_candidates, key=_extract_model_score, reverse=True)

        best_flash = flash_sorted[0] if flash_sorted else defaults["flash"]
        backup_flash = flash_sorted[1] if len(flash_sorted) > 1 else "gemini-3.6-flash"
        best_flash_lite = flash_lite_sorted[0] if flash_lite_sorted else defaults["flash_lite"]
        best_pro = pro_sorted[0] if pro_sorted else defaults["pro"]

        return {
            "flash": best_flash,
            "flash_backup": backup_flash,
            "flash_lite": best_flash_lite,
            "pro": best_pro
        }

    except Exception as e:
        logger.warning(f"Could not dynamically list models ({e}). Using verified fallback defaults.")
        return {
            "flash": defaults["flash"],
            "flash_backup": "gemini-3.6-flash",
            "flash_lite": defaults["flash_lite"],
            "pro": defaults["pro"]
        }
