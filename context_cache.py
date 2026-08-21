# -*- coding: utf-8 -*-
"""
Moduł Inteligentnego Zarządzania Pamięcią Kontekstu (Google Gemini Context Caching).
Zapewnia 75% oszczędności kosztów na serwerach Google bez najmniejszego wpływu na jakość.
Wbudowane zabezpieczenie SHA-256: Zmiana choćby jednej litery w Filarach natychmiast unieważnia stary cache i tworzy nowy.
TTL (Time-To-Live): 24 godziny (86400s) z automatycznym wygasaniem.
"""

import hashlib
import logging
from typing import Optional, Dict
from google import genai
from google.genai import types

logger = logging.getLogger("context_cache")

# Globalny rejestr w pamięci procesu
_LOCAL_CACHE_REGISTRY: Dict[str, str] = {}


class ContextCacheManager:
    @staticmethod
    def get_content_hash(model: str, system_instruction: str) -> str:
        """Generuje unikalny skrót SHA-256 z modelu i pełnego tekstu reguł systemowych."""
        content = f"{model}::{system_instruction}"
        return hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]

    @classmethod
    def get_or_create_cache(
        cls,
        client: genai.Client,
        model: str,
        system_instruction: str,
        ttl_seconds: int = 86400
    ) -> Optional[str]:
        """
        Pobiera istniejący lub tworzy nowy CachedContent na serwerach Google z czasem wygasania 24h (86400s).
        Zwraca nazwę zasobu cache (np. 'cachedContents/12345') lub None w razie braku wsparcia.
        """
        if not client or not system_instruction:
            return None

        content_hash = cls.get_content_hash(model, system_instruction)

        # 1. Sprawdzenie w lokalnej pamięci procesu
        if content_hash in _LOCAL_CACHE_REGISTRY:
            return _LOCAL_CACHE_REGISTRY[content_hash]

        display_name = f"avt_rules_{content_hash}"

        # 2. Próba znalezienia istniejącego cache o tym samym hashu na koncie Google
        try:
            if hasattr(client, "caches") and hasattr(client.caches, "list"):
                for existing in client.caches.list():
                    if existing.display_name == display_name:
                        _LOCAL_CACHE_REGISTRY[content_hash] = existing.name
                        logger.info(f"[Context Cache]: Wykorzystano istniejący cache serwerowy: {existing.name} (wersja: {content_hash})")
                        return existing.name
        except Exception as e:
            logger.debug(f"[Context Cache]: Nie można wylistować cache: {e}")

        # 3. Próba utworzenia nowego cache na serwerach Google
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
                logger.info(f"[Context Cache]: Utworzono cache serwerowy: {cache.name} (TTL: {ttl_seconds}s)")
                return cache.name
        except Exception as e:
            err_msg = str(e).lower()
            if "minimum" in err_msg or "at least" in err_msg or "32768" in err_msg or "too small" in err_msg:
                logger.debug(f"[Context Cache]: Prompt poniżej minimalnego progu serwerowego cache: {e}")
            else:
                logger.debug(f"[Context Cache]: Cache niedostępny dla {model}, fallback do standardowego przekazywania: {e}")

        return None
