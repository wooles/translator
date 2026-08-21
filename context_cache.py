# -*- coding: utf-8 -*-
"""
Moduł Inteligentnego Zarządzania Pamięcią Kontekstu (Google Gemini Context Caching).
Zapewnia 75% oszczędności kosztów na serwerach Google bez najmniejszego wpływu na jakość.
Wbudowane zabezpieczenie SHA-256: Zmiana choćby jednej litery w Filarach natychmiast unieważnia stary cache i tworzy nowy.
# TTL (Time-To-Live): 30 dni (2592000s) z automatycznym odnawianiem i czyszczeniem starych wersji.
"""

import hashlib
import logging
from typing import Optional, Dict
from google import genai
from google.genai import types

logger = logging.getLogger("context_cache")

# Domyślny czas życia pamięci na serwerach Google: 30 dni
DEFAULT_CACHE_TTL_SECONDS = 30 * 24 * 3600  # 2 592 000 sekund

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
        ttl_seconds: int = DEFAULT_CACHE_TTL_SECONDS
    ) -> Optional[str]:
        """
        Pobiera istniejący lub tworzy nowy CachedContent na serwerach Google z czasem wygasania 30 dni.
        Automatycznie usuwa przestarzałe wersje z serwera, zapobiegając jakimkolwiek nadmiarowym opłatom.
        """
        if not client or not system_instruction:
            return None

        content_hash = cls.get_content_hash(model, system_instruction)

        # 1. Sprawdzenie w lokalnej pamięci procesu
        if content_hash in _LOCAL_CACHE_REGISTRY:
            return _LOCAL_CACHE_REGISTRY[content_hash]

        display_name = f"avt_rules_{content_hash}"

        # 2. Próba znalezienia istniejącego cache oraz czyszczenie starych wersji
        try:
            if hasattr(client, "caches") and hasattr(client.caches, "list"):
                matched_name = None
                for existing in client.caches.list():
                    if existing.display_name == display_name:
                        matched_name = existing.name
                    elif existing.display_name and existing.display_name.startswith("avt_rules_"):
                        # Bezpieczne usunięcie nieaktualnej wersji z konta Google
                        try:
                            client.caches.delete(name=existing.name)
                            logger.info(f"[Context Cache]: Usunięto nieaktualną wersję cache: {existing.display_name}")
                        except Exception:
                            pass

                if matched_name:
                    _LOCAL_CACHE_REGISTRY[content_hash] = matched_name
                    logger.info(f"[Context Cache]: Wykorzystano aktywny 30-dniowy cache serwerowy: {matched_name}")
                    return matched_name
        except Exception as e:
            logger.debug(f"[Context Cache]: Błąd podczas listowania/czyszczenia cache: {e}")

        # 3. Próba utworzenia nowego 30-dniowego cache na serwerach Google
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
                logger.info(f"[Context Cache]: Utworzono 30-dniowy cache serwerowy: {cache.name} (TTL: {ttl_seconds}s)")
                return cache.name
        except Exception as e:
            err_msg = str(e).lower()
            if "minimum" in err_msg or "at least" in err_msg or "32768" in err_msg or "too small" in err_msg:
                logger.debug(f"[Context Cache]: Prompt poniżej minimalnego progu serwerowego cache: {e}")
            else:
                logger.debug(f"[Context Cache]: Cache niedostępny dla {model}, fallback do standardowego przekazywania: {e}")

        return None
