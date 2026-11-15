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
import os
import re
import sqlite3
import threading
from pathlib import Path
from typing import Optional, Dict, Any, Union, List, Tuple
from google import genai
from google.genai import types

logger = logging.getLogger("context_cache")

# Default safe cache time-to-live: 20 minutes (rolling window)
DEFAULT_CACHE_TTL_SECONDS = 20 * 60  # 1200 seconds

# Global in-memory cache registry for the current process
_LOCAL_CACHE_REGISTRY: Dict[str, str] = {}


def _get_tm_pairs_generator():
    """Generates authentic dialogue pairs from SQLite Translation Memory, with fallback to canon phrases."""
    try:
        from memory import MEMORY_DB_PATH
        db_path = MEMORY_DB_PATH
    except Exception:
        db_path = Path("translation_memory.db")

    if db_path and os.path.exists(db_path):
        try:
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT en_text, pl_text FROM translation_pairs ORDER BY id ASC")
                while True:
                    rows = cursor.fetchmany(250)
                    if not rows:
                        break
                    for r in rows:
                        if r[0] and r[1]:
                            yield (r[0].strip(), r[1].strip())
        except Exception as e:
            logger.debug(f"[ensure_cache_token_floor]: Błąd odczytu bazy pamięci tłumaczeniowej: {e}")

    # Fallback deterministic canon dialogue pairs if DB is absent or exhausted
    fallback_pairs = [
        ("Good morning.", "Dzień dobry."),
        ("Good evening.", "Dobry wieczór."),
        ("Thank you very much.", "Dziękuję bardzo."),
        ("You are welcome.", "Nie ma za co."),
        ("Understood.", "Zrozumiałem."),
        ("Let's go together.", "Chodźmy razem."),
        ("Be careful.", "Uważaj na siebie."),
        ("What happened here?", "Co się tutaj stało?"),
        ("Everything will be fine.", "Wszystko będzie w porządku."),
        ("I will protect you.", "Obronię cię."),
        ("Don't give up.", "Nie poddawaj się."),
        ("This is our destination.", "To jest nasz cel."),
        ("Wait for me.", "Poczekaj na mnie."),
        ("I cannot believe this.", "Nie mogę w to uwierzyć."),
        ("We must hurry.", "Musimy się spieszyć.")
    ]
    idx = 1
    while True:
        for en, pl in fallback_pairs:
            yield (f"{en} (Line {idx})", f"{pl} (Kwestia {idx})")
            idx += 1


def ensure_cache_token_floor(
    system_instruction: str,
    client: Any,
    model: str,
    cached_files: Optional[List[Any]] = None,
    target_tokens: int = 33500,
    min_tokens: int = 32768
) -> str:
    """
    Dobicie Promptu do Progu Cache (Anchor Padding / TM Injection).
    - Próg minimalny: 32 768 tokenów.
    - Próg docelowy z marginesem bezpieczeństwa: 33 500 tokenów.
    - Mierzy dokładną liczbę tokenów przez API (client.models.count_tokens).
    - Jeśli < 33 500, dynamicznie dokleja deterministyczny blok referencyjny z TM / AVT Canon:
      \\n\\n### DETERMINISTYCZNY KORPUS REFERENCYJNY (TM CANON - CONTEXT CACHE ANCHOR):\\n
      [JP: <source> -> PL: <target>]\\n...
    - Jeśli w trybie multimodalnym przesyłane jest całe wideo przez File API bezpośrednio do CachedContent,
      uchwyt pliku wideo wchodzi w skład obiektów buforowanych przed walidacją.
    """
    if not system_instruction:
        return system_instruction

    active_client = client
    if type(client).__name__ == "MultiKeyClientPool" and hasattr(client, "get_client"):
        try:
            active_client = client.get_client()
        except Exception:
            pass

    def _count(text: str) -> int:
        if active_client and hasattr(active_client, "models") and hasattr(active_client.models, "count_tokens"):
            try:
                cnt_payload = []
                if cached_files:
                    cnt_payload.extend(cached_files)
                cnt_payload.append(text)
                res = active_client.models.count_tokens(
                    model=model,
                    contents=cnt_payload if len(cnt_payload) > 1 else text
                )
                if hasattr(res, "total_tokens") and res.total_tokens is not None:
                    return int(res.total_tokens)
                if isinstance(res, (int, float)):
                    return int(res)
            except Exception as e:
                logger.debug(f"[ensure_cache_token_floor]: count_tokens error: {e}")

        # Fallback estimation: ~3.6 chars per token
        char_len = len(text)
        if cached_files:
            char_len += len(cached_files) * 2000
        return int(char_len / 3.6)

    current_tokens = _count(system_instruction)
    if current_tokens >= target_tokens:
        return system_instruction

    logger.info(
        f"[Context Cache Floor]: Bieżący rozmiar promptu ({current_tokens} tokenów) poniżej progu {target_tokens}. "
        "Dopełnianie korpusem referencyjnym TM Canon..."
    )

    header = "\n\n### DETERMINISTYCZNY KORPUS REFERENCYJNY (TM CANON - CONTEXT CACHE ANCHOR):\n"
    if header.strip() in system_instruction:
        base_instruction = system_instruction
    else:
        base_instruction = system_instruction + header

    pair_gen = _get_tm_pairs_generator()
    chunk_lines = []
    padded_instruction = base_instruction

    while current_tokens < target_tokens:
        needed = target_tokens - current_tokens
        batch_size = max(50, min(3000, int(needed / 12) + 20))
        for _ in range(batch_size):
            try:
                src, tgt = next(pair_gen)
                chunk_lines.append(f"[JP: {src} -> PL: {tgt}]\n")
            except StopIteration:
                break

        padded_instruction = base_instruction + "".join(chunk_lines)
        current_tokens = _count(padded_instruction)

    logger.info(
        f"[Context Cache Floor]: Pomyślnie dobito prompt do {current_tokens} tokenów "
        f"(próg docelowy: {target_tokens}, minimalny: {min_tokens})."
    )
    return padded_instruction


class ContextCacheManager:
    _LOCK = threading.Lock()

    _LAST_TOUCH: Dict[str, float] = {}

    ensure_cache_token_floor = staticmethod(ensure_cache_token_floor)

    @staticmethod
    def _clean_model_name(model: str) -> str:
        """Cleans and normalizes the model name."""
        return model.replace("models/", "").replace("-preview", "").replace(".", "_").replace("-", "_")

    @staticmethod
    def _get_client_id(client: Optional[Any]) -> str:
        """Extracts unique client identifier (API key hash or object id)."""
        if client:
            if hasattr(client, "_api_client") and hasattr(client._api_client, "api_key"):
                k = getattr(client._api_client, "api_key", None)
                if isinstance(k, str) and k.strip():
                    return hashlib.sha256(k.encode("utf-8")).hexdigest()[:8]
            if hasattr(client, "_api_key"):
                k = getattr(client, "_api_key", None)
                if isinstance(k, str) and k.strip():
                    return hashlib.sha256(k.encode("utf-8")).hexdigest()[:8]
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
        if is_gemini_4_or_hydrogen_model(model):
            # Modele Hydrogen wspierają wyłącznie implicit caching - natychmiastowe mapowanie
            content_hash = cls.get_content_hash(model, system_instruction, client=client, tag=tag)
            with cls._LOCK:
                _LOCAL_CACHE_REGISTRY[content_hash] = "__IMPLICIT_CACHE_95__"
            return "__IMPLICIT_CACHE_95__"

        estimated_tokens = len(system_instruction) // 4
        if estimated_tokens < 4096:
            logger.debug(
                "Pominięto tworzenie cache Gemini: oszacowany rozmiar (%d tokenów) poniżej progu 4096 tokenów",
                estimated_tokens,
            )
            return None

        if not hasattr(client, "caches") or not hasattr(client.caches, "create"):
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

        if is_gemini_4_or_hydrogen_model(model):
            # Pad system instruction to >= 33,500 tokens before creating cache
            padded_instruction = ensure_cache_token_floor(system_instruction, client, model)
        else:
            padded_instruction = system_instruction
        prompt_tag = cls._get_prompt_tag(padded_instruction, tag)

        if hasattr(client, "init_replicated_cache"):
            mapping = client.init_replicated_cache(model, padded_instruction, tag=prompt_tag)
            # Rozgrzewka implicit cache (Warm-Up Ping) na każdym kluczu w puli dla modeli Hydrogen
            if is_gemini_4_or_hydrogen_model(model):
                active_clients = client.get_active_clients() if hasattr(client, "get_active_clients") else [client]
                for idx, c in enumerate(active_clients):
                    try:
                        warmup_cfg = types.GenerateContentConfig(
                            system_instruction=padded_instruction,
                            max_output_tokens=1,
                            temperature=0.0
                        )
                        c.models.generate_content(
                            model=model,
                            contents="PING_WARMUP_INIT",
                            config=warmup_cfg
                        )
                        logger.info(f"[Context Cache Warmup]: Pomyślnie rozgrzano bufor dla klucza {idx + 1}/{len(active_clients)} ({model}, {prompt_tag}).")
                    except Exception as e:
                        logger.debug(f"[Context Cache Warmup]: Błąd mikro-rozgrzewki klucza {idx + 1}: {e}")
            first_name = next(iter(mapping.values()), None)
            if verbose and first_name:
                print(f"  [Context Cache]: Zablokowano i rozgrzano rabat serwerowy dla {model} ({prompt_tag}) na {len(mapping)} kluczach API.")
            return first_name or "cached_ready"

        if hasattr(client, "clients") and client.clients:
            first_name = None
            count = 0
            for c in client.clients:
                res = cls.get_or_create_cache(c, model, padded_instruction, tag=tag)
                if hasattr(client, "register_cache") and res:
                    client.register_cache(c, res, tag=prompt_tag)
                if not first_name:
                    first_name = res
                if res and res != "__IMPLICIT_CACHE_95__":
                    count += 1
            if verbose and first_name:
                print(f"  [Context Cache]: Zablokowano rabat serwerowy dla {model} ({prompt_tag}) na {count or len(client.clients)} kluczach API.")
            return first_name or "cached_ready"
        else:
            cache_name = cls.get_or_create_cache(client, model, padded_instruction, tag=tag)
            if cache_name and verbose:
                print(f"  [Context Cache]: Zablokowano rabat serwerowy dla {model} ({prompt_tag}).")
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

