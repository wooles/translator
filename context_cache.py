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
from typing import Optional, Dict, Any, Union
from google import genai
from google.genai import types

logger = logging.getLogger("context_cache")

# Default safe cache time-to-live: 20 minutes (rolling window)
DEFAULT_CACHE_TTL_SECONDS = 20 * 60  # 1200 seconds

# Global in-memory cache registry for the current process
_LOCAL_CACHE_REGISTRY: Dict[str, str] = {}


class ContextCacheManager:
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
    def get_content_hash(cls, model: str, system_instruction: str, client: Optional[Any] = None) -> str:
        """Generates a unique SHA-256 hash from client key, model name and full system instruction text."""
        client_id = cls._get_client_id(client)
        content = f"{client_id}::{model}::{system_instruction}"
        return hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]

    @classmethod
    def invalidate_cache(cls, model: str, system_instruction: str, client: Optional[Any] = None):
        """Removes an entry from the local registry upon 403 or invalidation."""
        content_hash = cls.get_content_hash(model, system_instruction, client=client)
        _LOCAL_CACHE_REGISTRY.pop(content_hash, None)

    @classmethod
    def get_or_create_cache(
        cls,
        client: genai.Client,
        model: str,
        system_instruction: str,
        ttl_seconds: int = DEFAULT_CACHE_TTL_SECONDS
    ) -> Optional[str]:
        """
        Retrieves existing or creates new CachedContent on Google servers with safe 20-minute expiration.
        Strictly isolates cache per Google Cloud Project / API key and per model.
        """
        if not client or not system_instruction:
            return None

        content_hash = cls.get_content_hash(model, system_instruction, client=client)

        # 1. Check in-process local memory
        if content_hash in _LOCAL_CACHE_REGISTRY:
            matched_name = _LOCAL_CACHE_REGISTRY[content_hash]
            # Refresh active cache lifetime (Rolling Keep-Alive)
            cls.touch_cache(client, matched_name, ttl_seconds)
            return matched_name

        model_clean = cls._clean_model_name(model)
        display_name = f"avt_{model_clean}_{content_hash}"
        model_prefix = f"avt_{model_clean}_"

        # 2. Try to find existing cache and clean outdated versions of the SAME model
        try:
            if hasattr(client, "caches") and hasattr(client.caches, "list"):
                matched_name = None
                for existing in client.caches.list():
                    if existing.display_name == display_name:
                        matched_name = existing.name
                    elif existing.display_name and existing.display_name.startswith(model_prefix):
                        # Only delete outdated version of the SAME model (without touching other models)
                        try:
                            client.caches.delete(name=existing.name)
                            logger.info(f"[Context Cache]: Removed outdated version {existing.display_name}")
                        except Exception:
                            pass

                if matched_name:
                    _LOCAL_CACHE_REGISTRY[content_hash] = matched_name
                    cls.touch_cache(client, matched_name, ttl_seconds)
                    logger.info(f"[Context Cache]: Reused active server cache: {matched_name} (Refreshed for +{ttl_seconds}s)")
                    return matched_name
        except Exception as e:
            logger.debug(f"[Context Cache]: Error listing/cleaning cache: {e}")

        # 3. Create a new cache on Google servers - retry with backoff for 503/429
        create_attempt = 0
        while True:
            create_attempt += 1
            try:
                if hasattr(client, "caches") and hasattr(client.caches, "create"):
                    ttl_str = f"{ttl_seconds}s"
                    cache = client.caches.create(
                        model=model,
                        config=types.CreateCachedContentConfig(
                            system_instruction=system_instruction,
                            ttl=ttl_str,
                            display_name=display_name,
                        )
                    )
                    _LOCAL_CACHE_REGISTRY[content_hash] = cache.name
                    logger.info(f"[Context Cache]: Created safe cache for {model}: {cache.name} (Rolling window: {ttl_seconds}s)")
                    return cache.name
            except Exception as e:
                err_msg = str(e).lower()
                # 1. Permanent inability to cache (e.g. prompt below 32,768 token threshold)
                if "minimum" in err_msg or "at least" in err_msg or "32768" in err_msg or "too small" in err_msg:
                    logger.debug(f"[Context Cache]: Prompt below minimum server cache threshold: {e}")
                    return None

                # 2. Account / API key error (insufficient funds, bad key)
                if "prepayment" in err_msg or "depleted" in err_msg or "api_key" in err_msg or "permission" in err_msg:
                    logger.error(f"[Context Cache]: Permission or account error: {e}")
                    return None

                # 3. Transient server error (503 / 429 / socket / timeout) -> retry with backoff
                import time
                wait_sec = min(3 + create_attempt * 2, 25)
                print(f"  [Context Cache]: Google servers busy (503/429 for {model}). Waiting {wait_sec}s for free cache slot (attempt #{create_attempt})...")
                time.sleep(wait_sec)

    @classmethod
    def ensure_cache_ready(
        cls,
        client: Any,
        model: str,
        system_instruction: str,
        verbose: bool = True
    ) -> Optional[str]:
        """
        Guarantees that server cache is active and locked before translation begins,
        protecting against unauthorized full-rate billing.
        If a MultiKeyClientPool is provided, warms caches across all keys in the pool.
        """
        if not client or not system_instruction:
            return None

        if hasattr(client, "clients") and client.clients:
            primary_name = None
            for c in client.clients:
                res = cls.get_or_create_cache(c, model, system_instruction)
                if not primary_name:
                    primary_name = res
            if primary_name and verbose:
                print(f"  [Context Cache]: Locked -75% server discount for {model} (Active across {len(client.clients)} API channel(s)).")
            return primary_name
        else:
            cache_name = cls.get_or_create_cache(client, model, system_instruction)
            if cache_name:
                if verbose:
                    print(f"  [Context Cache]: Locked -75% server discount for {model}.")
                return cache_name
            else:
                if verbose:
                    print(f"  [Context Cache / WARNING]: Cache unavailable for {model} - requests may be billed at standard rate.")
                return None

    @classmethod
    def touch_cache(cls, client: genai.Client, cache_name: str, ttl_seconds: int = DEFAULT_CACHE_TTL_SECONDS):
        """Extends rolling TTL window by 20 minutes from current second (Rolling Heartbeat)."""
        if not client or not cache_name:
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

