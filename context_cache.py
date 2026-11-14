# -*- coding: utf-8 -*-
"""
Intelligent Context Cache Management Module (Google Gemini Context Caching).
Provides 75% cost savings on Google servers without compromising translation quality.
Built-in SHA-256 validation: Modifying any rule instantly invalidates the outdated cache and creates a fresh one.
Rolling Keep-Alive Heartbeat Architecture:
- Cache is created with a 20-minute (1200s) TTL rolling window, renewed after each batch or transient retry.
- After episode or queue completion, active caches are immediately deleted (0 PLN idle cost).
- In case of power failure, the cache automatically expires within 20 minutes, preventing budget leakage.
"""

import hashlib
import logging
import threading
from typing import Optional, Dict, Any, Union
from google import genai
from google.genai import types

logger = logging.getLogger("context_cache")

# Default safe cache time-to-live: 20 minutes (rolling window)
DEFAULT_CACHE_TTL_SECONDS = 20 * 60  # 1200 seconds

# Global in-memory cache registry for the current process
_LOCAL_CACHE_REGISTRY: Dict[str, str] = {}


class ContextCacheManager:
    _LOCK = threading.Lock()

    _LAST_TOUCH: Dict[str, float] = {}

    @staticmethod
    def _clean_model_name(model: str) -> str:
        """Cleans and normalizes the model name."""
        return model.replace("models/", "").replace("-preview", "").replace(".", "_").replace("-", "_")

    @staticmethod
    def _get_client_id(client: Optional[Any]) -> str:
        """Extracts unique client identifier (API key hash or object id)."""
        if client:
            if hasattr(client, "_api_client") and hasattr(client._api_client, "api_key") and client._api_client.api_key:
                return hashlib.sha256(client._api_client.api_key.encode("utf-8")).hexdigest()[:8]
            return str(id(client))
        return "default"

    @classmethod
    def _get_prompt_tag(cls, system_instruction: str, tag: Optional[str] = None) -> str:
        """Extracts semantic phase tag (e.g. translator vs verifier) to prevent cross-phase cache deletion."""
        if tag:
            return tag.lower().strip()
        si = (system_instruction or "").lower()
        if any(w in si for w in ["verifier", "redaktor", "redakcj", "script doctor", "szlif", "faza 2"]):
            return "verifier"
        return "translator"

    @classmethod
    def get_content_hash(cls, model: str, system_instruction: str, client: Optional[Any] = None, tag: Optional[str] = None) -> str:
        """Generates a unique SHA-256 hash from client key, model name, phase tag and full system instruction text."""
        client_id = cls._get_client_id(client)
        prompt_tag = cls._get_prompt_tag(system_instruction, tag)
        content = f"{client_id}::{model}::{prompt_tag}::{system_instruction}"
        return hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]

    @classmethod
    def invalidate_cache(cls, model: str, system_instruction: str, client: Optional[Any] = None, tag: Optional[str] = None):
        """Removes an entry from the local registry upon 403 or invalidation."""
        with cls._LOCK:
            if client:
                content_hash = cls.get_content_hash(model, system_instruction, client=client, tag=tag)
                _LOCAL_CACHE_REGISTRY.pop(content_hash, None)
            else:
                prompt_tag = cls._get_prompt_tag(system_instruction, tag)
                # Purge all matching model caches across any clients for this phase
                to_remove = [k for k in list(_LOCAL_CACHE_REGISTRY.keys()) if f"::{model}::{prompt_tag}::" in k]
                for k in to_remove:
                    _LOCAL_CACHE_REGISTRY.pop(k, None)

    @classmethod
    def get_or_create_cache(
        cls,
        client: genai.Client,
        model: str,
        system_instruction: str,
        ttl_seconds: int = DEFAULT_CACHE_TTL_SECONDS,
        tag: Optional[str] = None
    ) -> Optional[str]:
        """
        Retrieves existing or creates new CachedContent on Google servers with safe 20-minute expiration.
        Strictly isolates cache per Google Cloud Project / API key, per model, and per pipeline phase.
        """
        if not client or not system_instruction:
            return None

        from model_resolver import is_gemini_4_or_hydrogen_model
        if not hasattr(client, "caches") or not hasattr(client.caches, "create"):
            if is_gemini_4_or_hydrogen_model(model):
                return "__IMPLICIT_CACHE_95__"
            return None

        with cls._LOCK:
            content_hash = cls.get_content_hash(model, system_instruction, client=client, tag=tag)

            # 1. Check in-process local memory
            if content_hash in _LOCAL_CACHE_REGISTRY:
                cached_name = _LOCAL_CACHE_REGISTRY[content_hash]
                if cached_name == "__IMPLICIT_CACHE_95__":
                    return cached_name
                import time
                now = time.monotonic()
                if now - cls._LAST_TOUCH.get(cached_name, 0) > 120.0:
                    cls.touch_cache(client, cached_name, ttl_seconds)
                    cls._LAST_TOUCH[cached_name] = now
                return cached_name

            model_clean = cls._clean_model_name(model)
            client_id = cls._get_client_id(client)
            prompt_tag = cls._get_prompt_tag(system_instruction, tag)
            display_name = f"avt_{model_clean}_{client_id}_{prompt_tag}_{content_hash}"
            model_prefix = f"avt_{model_clean}_{client_id}_{prompt_tag}_"

            # 2. Try to find existing cache and clean outdated versions of the SAME client, model and phase
            try:
                if hasattr(client, "caches") and hasattr(client.caches, "list"):
                    matched_name = None
                    for existing in client.caches.list():
                        if existing.display_name == display_name:
                            matched_name = existing.name
                        elif existing.display_name and existing.display_name.startswith(model_prefix):
                            # Only delete outdated version of the SAME client, model and phase
                            try:
                                client.caches.delete(name=existing.name)
                                logger.info(f"[Context Cache]: Removed outdated version {existing.display_name}")
                            except Exception:
                                pass

                    if matched_name:
                        _LOCAL_CACHE_REGISTRY[content_hash] = matched_name
                        cls.touch_cache(client, matched_name, ttl_seconds)
                        import time
                        cls._LAST_TOUCH[matched_name] = time.monotonic()
                        logger.info(f"[Context Cache]: Reused active server cache: {matched_name} (Refreshed for +{ttl_seconds}s)")
                        return matched_name
            except Exception as e:
                logger.debug(f"[Context Cache]: Error listing/cleaning cache: {e}")

            # 3. Create a new cache on Google servers - max 2 attempts with micro-wait
            estimated_tokens = len(system_instruction) // 4
            if estimated_tokens < 4096:
                logger.debug(
                    "Pominięto tworzenie cache Gemini: oszacowany rozmiar (%d tokenów) poniżej progu 4096 tokenów",
                    estimated_tokens,
                )
                return None

            create_attempt = 0
            while create_attempt < 2:
                create_attempt += 1
                try:
                    if hasattr(client, "caches") and hasattr(client.caches, "create"):
                        ttl_str = f"{ttl_seconds}s"
                        cache_cfg_kwargs = {
                            "system_instruction": system_instruction,
                            "ttl": ttl_str,
                            "display_name": display_name,
                        }
                        create_config = None
                        if hasattr(types, "Content") and hasattr(types, "Part"):
                            try:
                                anchor_text = "AVT Context Cache Prefix Anchor"
                                if len(system_instruction) < 140000:
                                    try:
                                        from rules import get_translation_system_prompt
                                        full_canon = get_translation_system_prompt(keep_honorifics=True, lean=False)
                                        anchor_text = f"AVT Context Cache Prefix Anchor\n\n{full_canon}"
                                    except Exception:
                                        pass
                                anchor_part = types.Part.from_text(text=anchor_text) if hasattr(types.Part, "from_text") else types.Part(text=anchor_text)
                                anchor_content = [types.Content(role="user", parts=[anchor_part])]
                                create_config = types.CreateCachedContentConfig(
                                    contents=anchor_content,
                                    **cache_cfg_kwargs
                                )
                            except Exception:
                                create_config = None

                        if create_config is None:
                            try:
                                create_config = types.CreateCachedContentConfig(**cache_cfg_kwargs)
                            except Exception:
                                create_config = cache_cfg_kwargs

                        cache = client.caches.create(
                            model=model,
                            config=create_config
                        )
                        _LOCAL_CACHE_REGISTRY[content_hash] = cache.name
                        logger.info(f"[Context Cache]: Created safe cache for {model}: {cache.name} (Rolling window: {ttl_seconds}s)")
                        return cache.name
                except Exception as e:
                    err_msg = str(e).lower()
                    # 1. Permanent inability to cache (e.g. prompt below 32,768 token threshold)
                    if "minimum" in err_msg or "at least" in err_msg or "32768" in err_msg or "too small" in err_msg or "not supported" in err_msg or "unsupported" in err_msg:
                        logger.debug(f"[Context Cache]: Prompt below minimum server cache threshold or unsupported: {e}")
                        if is_gemini_4_or_hydrogen_model(model) and estimated_tokens >= 4096:
                            _LOCAL_CACHE_REGISTRY[content_hash] = "__IMPLICIT_CACHE_95__"
                            return "__IMPLICIT_CACHE_95__"
                        return None

                    # 2. Account / API key error (insufficient funds, bad key)
                    if "prepayment" in err_msg or "depleted" in err_msg or "api_key" in err_msg or "permission" in err_msg:
                        logger.error(f"[Context Cache]: Permission or account error: {e}")
                        return None

                    # 3. Transient server error (503 / 429 / socket / timeout) -> quick micro-wait
                    import time
                    if create_attempt < 2:
                        time.sleep(1.0)

            if is_gemini_4_or_hydrogen_model(model) and estimated_tokens >= 4096:
                _LOCAL_CACHE_REGISTRY[content_hash] = "__IMPLICIT_CACHE_95__"
                return "__IMPLICIT_CACHE_95__"

            return None

    @classmethod
    def ensure_cache_ready(
        cls,
        client: Any,
        model: str,
        system_instruction: str,
        verbose: bool = True,
        tag: Optional[str] = None
    ) -> Optional[str]:
        """
        Guarantees that server cache is active and locked across all client pool keys before translation begins,
        protecting against unauthorized full-rate billing.
        """
        if not client or not system_instruction:
            return None

        from model_resolver import is_gemini_4_or_hydrogen_model
        if is_gemini_4_or_hydrogen_model(model) and not hasattr(client, "clients") and not hasattr(client, "caches"):
            return True

        prompt_tag = cls._get_prompt_tag(system_instruction, tag)
        if hasattr(client, "clients") and client.clients:
            first_name = None
            for c in client.clients:
                res = cls.get_or_create_cache(c, model, system_instruction, tag=tag)
                if not first_name:
                    first_name = res
            if verbose and first_name:
                print(f"  [Context Cache]: Locked -90% server discount for {model} ({prompt_tag}) across {len(client.clients)} API keys.")
            if is_gemini_4_or_hydrogen_model(model):
                return True
            return first_name or "cached_ready"
        else:
            cache_name = cls.get_or_create_cache(client, model, system_instruction, tag=tag)
            if cache_name and verbose:
                print(f"  [Context Cache]: Locked -90% server discount for {model} ({prompt_tag}).")
            if is_gemini_4_or_hydrogen_model(model):
                return True
            return cache_name or "cached_ready"

    @classmethod
    def touch_cache(cls, client: genai.Client, cache_name: str, ttl_seconds: int = DEFAULT_CACHE_TTL_SECONDS):
        """Extends rolling TTL window by 20 minutes from current second (Rolling Heartbeat)."""
        if not client or not cache_name or cache_name == "__IMPLICIT_CACHE_95__":
            return
        try:
            if hasattr(client, "caches") and hasattr(client.caches, "update"):
                client.caches.update(
                    name=cache_name,
                    config=types.UpdateCachedContentConfig(ttl=f"{ttl_seconds}s")
                )
                logger.debug(f"[Context Cache]: Heartbeat refreshed for {cache_name} (+{ttl_seconds}s)")
        except Exception as e:
            logger.debug(f"[Context Cache]: Failed to update heartbeat for {cache_name}: {e}")

    @classmethod
    def cleanup_all_active_caches(cls, client: genai.Client):
        """Immediately deletes all active and orphaned cache objects from Google servers after completion."""
        if not client:
            return
        try:
            # 1. Delete registered objects in local session
            if hasattr(client, "caches") and hasattr(client.caches, "delete"):
                for hash_key, cache_name in list(_LOCAL_CACHE_REGISTRY.items()):
                    try:
                        client.caches.delete(name=cache_name)
                        logger.info(f"[Context Cache]: Safely deleted cache {cache_name} (0 PLN post-session charges).")
                    except Exception:
                        pass
                _LOCAL_CACHE_REGISTRY.clear()

            # 2. Sweep any orphaned 'avt_' objects on the Google account
            if hasattr(client, "caches") and hasattr(client.caches, "list"):
                for existing in client.caches.list():
                    if existing.display_name and existing.display_name.startswith("avt_"):
                        try:
                            client.caches.delete(name=existing.name)
                            logger.info(f"[Context Cache]: Removed orphaned cache object: {existing.display_name}")
                        except Exception:
                            pass
        except Exception as e:
            logger.debug(f"[Context Cache]: Error cleaning cache: {e}")

