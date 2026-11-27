# -*- coding: utf-8 -*-
"""
Gemini Model Auto-Discovery & Version Resolver Module.
Automatically queries Google API to discover and select the highest, latest model versions
(e.g., Gemini 3.7 Flash, Gemini 3.1 Pro, and future versions like 3.8, 4.0, etc.),
guaranteeing the translator always utilizes the most capable models without manual code changes.
"""

import os
import re
import logging
from typing import Dict, Optional, List, Tuple, Any
from google import genai

logger = logging.getLogger("model_resolver")


def resolve_service_tier(explicit_tier: Optional[str] = None) -> str:
    """Rozstrzyga tryb usługi Gemini (domyślnie 'standard'; opt-in 'flex' przez AVT_SERVICE_TIER)."""
    raw = explicit_tier if explicit_tier is not None else os.getenv("AVT_SERVICE_TIER", "standard")
    norm = str(raw or "").strip().lower()
    return "flex" if norm == "flex" else "standard"


def apply_service_tier_to_config(
    cfg_kwargs: Dict[str, Any],
    service_tier: Optional[str],
    model_name: str = "",
) -> Dict[str, Any]:
    """Stosuje opt-in Gemini Flex Inference w GenerateContentConfig bez wpływu na tryb standard."""
    out = dict(cfg_kwargs or {})
    if resolve_service_tier(service_tier) != "flex":
        return out
    try:
        from google.genai import types
        cfg_fields = getattr(types.GenerateContentConfig, "model_fields", {}) or {}
        if "service_tier" in cfg_fields:
            out["service_tier"] = "flex"
        if "http_options" in cfg_fields and hasattr(types, "HttpOptions"):
            existing_ho = out.get("http_options")
            merged_headers: Dict[str, str] = {}
            if existing_ho is not None:
                if isinstance(existing_ho, dict):
                    merged_headers.update(existing_ho.get("headers") or {})
                    merged_headers["X-Gemini-Service-Tier"] = "flex"
                    new_ho = dict(existing_ho)
                    new_ho["headers"] = merged_headers
                    out["http_options"] = types.HttpOptions(**new_ho)
                else:
                    ex_hdrs = getattr(existing_ho, "headers", None)
                    if isinstance(ex_hdrs, dict):
                        merged_headers.update(ex_hdrs)
                    merged_headers["X-Gemini-Service-Tier"] = "flex"
                    if hasattr(existing_ho, "model_copy"):
                        out["http_options"] = existing_ho.model_copy(update={"headers": merged_headers})
                    else:
                        out["http_options"] = types.HttpOptions(headers=merged_headers)
            else:
                out["http_options"] = types.HttpOptions(headers={"X-Gemini-Service-Tier": "flex"})
    except Exception as exc:
        logger.debug("Pominięto wstrzyknięcie konfiguracji Flex Inference (%s): %s", model_name or "-", exc)
    return out


def extract_response_service_tier_header(response: Any) -> Optional[str]:
    """Bezpiecznie odczytuje nagłówek X-Gemini-Service-Tier z odpowiedzi SDK."""
    if response is None:
        return None
    header_sources = []
    sdk_resp = getattr(response, "sdk_http_response", None)
    if sdk_resp is not None:
        header_sources.append(getattr(sdk_resp, "headers", None))
    header_sources.append(getattr(response, "headers", None))
    for hdrs in header_sources:
        if isinstance(hdrs, dict) or hasattr(hdrs, "items"):
            try:
                for k, v in hdrs.items():
                    if str(k).strip().lower() == "x-gemini-service-tier":
                        val = str(v or "").strip().lower()
                        if val:
                            return val
            except Exception as exc:
                logger.debug("Błąd odczytu nagłówków odpowiedzi HTTP: %s", exc)
    direct_tier = getattr(response, "service_tier", None)
    if direct_tier is not None:
        if hasattr(direct_tier, "value"):
            direct_tier = direct_tier.value
        val = str(direct_tier or "").strip().lower()
        if val:
            return val
    return None


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


def is_gemini_4_or_hydrogen_model(model_name: str) -> bool:
    """Rozpoznaje modele rodziny gemini-4 / hydrogen korzystające z thinking_level oraz Implicit Caching."""
    if not model_name:
        return False
    clean = str(model_name).replace("models/", "").lower().strip()
    if "hydrogen" in clean or "carbon" in clean or "argon" in clean:
        return True
    if re.search(r"gemini-4(?:\b|[-_.])", clean) and "flash" not in clean:
        return True
    return False


def build_thinking_config(model_name: str, budget_tokens: int) -> Any:
    """Tworzy obiekt konfiguracji myślenia dostosowany do rodziny modelu."""
    from google.genai import types

    if is_gemini_4_or_hydrogen_model(model_name):
        budget = int(budget_tokens)
        if budget <= 2048:
            level_str = "LOW"
        elif budget <= 4500:
            level_str = "MEDIUM"
        elif budget <= 6144:
            level_str = "HIGH"
        else:
            level_str = "XHIGH"

        try:
            return types.ThinkingConfig(thinking_level=level_str)
        except Exception:
            cfg = types.ThinkingConfig()
            object.__setattr__(cfg, "thinking_level", level_str)
            return cfg

    return types.ThinkingConfig(thinking_budget=int(budget_tokens))


def resolve_best_models(client: Optional[genai.Client] = None) -> Dict[str, str]:
    """
    Automatically inspects available models in Google AI Studio for the provided API client
    and returns a dictionary with the newest versions for each tier:
    - 'hydrogen': Flagship Gemini 4 Hydrogen model
    - 'flash': Latest flagship Flash model (e.g. gemini-3.8-flash or gemini-3.7-flash)
    - 'flash_lite': Fastest lightweight Flash-Lite model (e.g. gemini-3.5-flash-lite)
    - 'pro': Flagship Pro class model (e.g. gemini-3.1-pro-preview)
    """
    # Default verified base models (highest quality baseline)
    defaults = {
        "hydrogen": "gemini-4-hydrogen",
        "flash": "gemini-3.8-flash",
        "flash_backup": "gemini-3.7-flash",
        "flash_lite": "gemini-3.5-flash-lite",
        "pro": "gemini-3.1-pro-preview"
    }

    if not client:
        return defaults

    try:
        raw_models = list(client.models.list())
        
        hydrogen_candidates = []
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

            if "gemini" not in name_lower and "hydrogen" not in name_lower and "carbon" not in name_lower:
                continue

            score = _extract_model_score(name)
            # Pomijanie wycofanych modeli generacji 1.x oraz 2.x (np. gemini-2.5-pro zwracających 404)
            if score[0] > 0 and score[0] < 3:
                continue

            # Classify into tier categories
            if "hydrogen" in name_lower and "argon" not in name_lower and "carbon" not in name_lower and "pro" not in name_lower:
                hydrogen_candidates.append(name)
            elif "flash-lite" in name_lower:
                flash_lite_candidates.append(name)
            elif "flash" in name_lower:
                flash_candidates.append(name)
            elif "pro" in name_lower or "argon" in name_lower or "carbon" in name_lower:
                if score >= (3, 1, 0) or "argon" in name_lower or "carbon" in name_lower:
                    pro_candidates.append(name)

        # Sort by highest version score
        hydrogen_sorted = sorted(
            hydrogen_candidates,
            key=lambda n: (_extract_model_score(n), 1 if n.lower() == "gemini-4-hydrogen" else 0),
            reverse=True
        )
        flash_sorted = sorted(flash_candidates, key=_extract_model_score, reverse=True)
        flash_lite_sorted = sorted(flash_lite_candidates, key=_extract_model_score, reverse=True)
        pro_sorted = sorted(
            pro_candidates,
            key=lambda n: (_extract_model_score(n), 1 if "pro" in n.lower() else 0),
            reverse=True
        )

        best_hydrogen = hydrogen_sorted[0] if hydrogen_sorted else defaults["hydrogen"]
        best_flash = flash_sorted[0] if flash_sorted else defaults["flash"]
        backup_flash = flash_sorted[1] if len(flash_sorted) > 1 else "gemini-3.6-flash"
        best_flash_lite = flash_lite_sorted[0] if flash_lite_sorted else defaults["flash_lite"]
        best_pro = pro_sorted[0] if pro_sorted else defaults["pro"]

        return {
            "hydrogen": best_hydrogen,
            "flash": best_flash,
            "flash_backup": backup_flash,
            "flash_lite": best_flash_lite,
            "pro": best_pro
        }

    except Exception as e:
        logger.warning(f"Could not dynamically list models ({e}). Using verified fallback defaults.")
        return {
            "hydrogen": defaults["hydrogen"],
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
        if is_gemini_4_or_hydrogen_model(model_name):
            cfg_kwargs["max_output_tokens"] = 64
            cfg_kwargs["thinking_config"] = build_thinking_config(model_name, 0)
        elif "pro" in model_name.lower() or "3.1" in model_name.lower():
            cfg_kwargs["max_output_tokens"] = 600
            cfg_kwargs["thinking_config"] = types.ThinkingConfig(thinking_budget=512)
        elif "lite" not in model_name.lower() and any(k in model_name.lower() for k in ["3.7", "3.8", "flash"]):
            cfg_kwargs["max_output_tokens"] = 10
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
    with concurrent.futures.ThreadPoolExecutor(max_workers=min(5, len(models_dict))) as executor:
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
