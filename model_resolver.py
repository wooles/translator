# -*- coding: utf-8 -*-
"""
Gemini Model Auto-Discovery & Version Resolver Module.
Automatically queries Google API to discover and select the highest, latest model versions
(e.g., Gemini 3.7 Flash, Gemini 3.1 Pro, and future versions like 3.8, 4.0, etc.),
guaranteeing the translator always utilizes the most capable models without manual code changes.
"""

import re
import logging
from typing import Dict, Optional, List, Tuple, Any
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
        "flash_backup": "gemini-3.6-flash",
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


def probe_model_health(client: Optional[genai.Client], model_name: str) -> Dict[str, Any]:
    """
    Sends a 1-token micro-probe to Google API to measure real-time latency and server cluster health.
    """
    if not client or not model_name:
        return {"status": "unknown", "tag": "⚪ Gotowy", "latency_s": 0.0, "is_available": True, "error_msg": ""}

    import time
    from google.genai import types

    t0 = time.time()
    try:
        cfg_kwargs = {
            "max_output_tokens": 10,
            "http_options": types.HttpOptions(timeout=25000)
        }
        if "pro" in model_name.lower() or "3.1" in model_name.lower():
            cfg_kwargs["thinking_config"] = types.ThinkingConfig(thinking_budget=512)
        elif "3.7" in model_name.lower():
            cfg_kwargs["thinking_config"] = types.ThinkingConfig(thinking_budget=0)

        cfg = types.GenerateContentConfig(**cfg_kwargs)
        client.models.generate_content(
            model=model_name,
            contents="1",
            config=cfg
        )
        lat = time.time() - t0
        if lat < 1.5:
            tag = f"🟢 PŁYNNY ({lat:.1f}s)"
            status = "fast"
        elif lat < 4.0:
            tag = f"🟡 UMIARKOWANY ({lat:.1f}s)"
            status = "normal"
        else:
            tag = f"🟠 WOLNY ({lat:.1f}s)"
            status = "slow"

        return {
            "status": status,
            "tag": tag,
            "latency_s": round(lat, 2),
            "is_available": True,
            "error_msg": ""
        }
    except Exception as e:
        lat = time.time() - t0
        err_str = str(e)
        if "503" in err_str or "UNAVAILABLE" in err_str or "high demand" in err_str.lower():
            tag = "🔴 PRZECIĄŻONY (Błąd 503 / Wysoki popyt)"
            status = "overloaded"
        elif "429" in err_str or "ResourceExhausted" in err_str:
            tag = "🔴 LIMIT ZAPYTAŃ (Błąd 429)"
            status = "rate_limited"
        elif "504" in err_str or "DEADLINE" in err_str:
            tag = f"🔴 TIMEOUT ({lat:.1f}s / Błąd 504)"
            status = "timeout"
        else:
            tag = f"⚠️ BŁĄD ({err_str[:25]})"
            status = "error"

        return {
            "status": status,
            "tag": tag,
            "latency_s": round(lat, 2),
            "is_available": False,
            "error_msg": err_str
        }


def probe_all_models_health(client: Optional[genai.Client], models_dict: Dict[str, str]) -> Dict[str, Dict[str, Any]]:
    """
    Probes all candidate models concurrently in parallel (completes in ~1-2 seconds).
    """
    if not client:
        return {k: {"status": "unknown", "tag": "⚪ Gotowy", "latency_s": 0.0, "is_available": True, "error_msg": ""} for k in models_dict}

    import concurrent.futures

    results = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=min(4, len(models_dict))) as executor:
        future_to_key = {
            executor.submit(probe_model_health, client, model_name): key
            for key, model_name in models_dict.items()
        }
        for future in concurrent.futures.as_completed(future_to_key):
            key = future_to_key[future]
            try:
                results[key] = future.result()
            except Exception as e:
                results[key] = {"status": "error", "tag": "⚠️ Błąd", "latency_s": 0.0, "is_available": False, "error_msg": str(e)}

    return results
