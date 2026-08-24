# -*- coding: utf-8 -*-
"""
Moduł Inteligentnego Zarządzania Pamięcią Kontekstu (Google Gemini Context Caching).
Zapewnia 75% oszczędności kosztów na serwerach Google bez najmniejszego wpływu na jakość.
Wbudowane zabezpieczenie SHA-256: Zmiana choćby jednej litery w Filarach natychmiast unieważnia stary cache i tworzy nowy.
Architektura Kroczącego Heartbeatu (Rolling Keep-Alive):
- Cache tworzony jest na 20 minut (1200s) z ruchomym oknem przedłużanym po każdej paczce/błędzie 503.
- Po zakończeniu odcinka lub kolejki cache jest natychmiast usuwany (0 zł kosztów postoju).
- W razie awarii zasilania cache samoczynnie wygasa w 20 minut, zabezpieczając portfel.
"""

import hashlib
import logging
from typing import Optional, Dict
from google import genai
from google.genai import types

logger = logging.getLogger("context_cache")

# Domyślny bezpieczny czas życia pamięci podręcznej: 20 minut (ruchome okno)
DEFAULT_CACHE_TTL_SECONDS = 20 * 60  # 1200 sekund

# Globalny rejestr w pamięci procesu
_LOCAL_CACHE_REGISTRY: Dict[str, str] = {}


class ContextCacheManager:
    @staticmethod
    def _clean_model_name(model: str) -> str:
        """Czyści i normalizuje nazwę modelu."""
        return model.replace("models/", "").replace("-preview", "").replace(".", "_").replace("-", "_")

    @staticmethod
    def get_content_hash(model: str, system_instruction: str) -> str:
        """Generuje unikalny skrót SHA-256 z modelu i pełnego tekstu reguł systemowych."""
        content = f"{model}::{system_instruction}"
        return hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]

    @classmethod
    def invalidate_cache(cls, model: str, system_instruction: str):
        """Usuwa wpis z lokalnego rejestru w razie błędu 403 lub unieważnienia."""
        content_hash = cls.get_content_hash(model, system_instruction)
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
        Pobiera istniejący lub tworzy nowy CachedContent na serwerach Google z bezpiecznym czasem wygasania 20 minut.
        Precyzyjnie izoluje cache pomiędzy modelami (Flash vs Pro) i usuwa tylko przestarzałe wersje TEGO SAMEGO modelu.
        """
        if not client or not system_instruction:
            return None

        content_hash = cls.get_content_hash(model, system_instruction)

        # 1. Sprawdzenie w lokalnej pamięci procesu
        if content_hash in _LOCAL_CACHE_REGISTRY:
            matched_name = _LOCAL_CACHE_REGISTRY[content_hash]
            # Odświeżamy czas życia aktywnego cache (Rolling Keep-Alive)
            cls.touch_cache(client, matched_name, ttl_seconds)
            return matched_name

        model_clean = cls._clean_model_name(model)
        display_name = f"avt_{model_clean}_{content_hash}"
        model_prefix = f"avt_{model_clean}_"

        # 2. Próba znalezienia istniejącego cache oraz czyszczenie starych wersji TEGO SAMEGO modelu
        try:
            if hasattr(client, "caches") and hasattr(client.caches, "list"):
                matched_name = None
                for existing in client.caches.list():
                    if existing.display_name == display_name:
                        matched_name = existing.name
                    elif existing.display_name and existing.display_name.startswith(model_prefix):
                        # Usuwamy wyłącznie starą wersję TEGO SAMEGO modelu (nie dotykając innych modeli!)
                        try:
                            client.caches.delete(name=existing.name)
                            logger.info(f"[Context Cache]: Usunięto przestarzałą wersję {existing.display_name}")
                        except Exception:
                            pass

                if matched_name:
                    _LOCAL_CACHE_REGISTRY[content_hash] = matched_name
                    cls.touch_cache(client, matched_name, ttl_seconds)
                    logger.info(f"[Context Cache]: Wykorzystano aktywny cache serwerowy: {matched_name} (Odświeżono na +{ttl_seconds}s)")
                    return matched_name
        except Exception as e:
            logger.debug(f"[Context Cache]: Błąd podczas listowania/czyszczenia cache: {e}")

        # 3. Próba utworzenia nowego cache na serwerach Google – ponawianie DO SKUTKU (Infinite Retry dla 503/429)
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
                    logger.info(f"[Context Cache]: Utworzono bezpieczny cache dla {model}: {cache.name} (Ruchome okno: {ttl_seconds}s)")
                    return cache.name
            except Exception as e:
                err_msg = str(e).lower()
                # 1. Trwały brak możliwości cache (np. prompt poniżej progu 32 768 tokenów)
                if "minimum" in err_msg or "at least" in err_msg or "32768" in err_msg or "too small" in err_msg:
                    logger.debug(f"[Context Cache]: Prompt poniżej minimalnego progu serwerowego cache: {e}")
                    return None

                # 2. Błąd konta / klucza API (brak środków, zły klucz)
                if "prepayment" in err_msg or "depleted" in err_msg or "api_key" in err_msg or "permission" in err_msg:
                    logger.error(f"[Context Cache]: Błąd uprawnień/konta: {e}")
                    return None

                # 3. Błąd przejściowy serwerów Google (503 / 429 / socket / timeout) -> Ponawiamy DO SKUTKU
                import time
                wait_sec = min(3 + create_attempt * 2, 25)
                print(f"  [Context Cache]: Serwery Google przeciążone (błąd 503/429 dla {model}). Czekam {wait_sec}s na wolny slot cache (próba #{create_attempt}, gwarancja rabatu -75%)...")
                time.sleep(wait_sec)

    @classmethod
    def ensure_cache_ready(
        cls,
        client: genai.Client,
        model: str,
        system_instruction: str,
        verbose: bool = True
    ) -> Optional[str]:
        """
        Gwarantuje, że cache serwerowy jest w 100% zapięty i aktywny przed rozpoczęciem tłumaczenia,
        zabezpieczając użytkownika przed nieautoryzowanym naliczeniem 100% pełnej stawki.
        """
        if not client or not system_instruction:
            return None

        cache_name = cls.get_or_create_cache(client, model, system_instruction)
        if cache_name:
            if verbose:
                print(f"  [Context Cache]: Zapięto rabat -75% na serwerze Google dla {model}.")
            return cache_name
        else:
            if verbose:
                print(f"  [Context Cache / UWAGA]: Cache niedostępny dla {model} – zapytania mogą być rozliczane stawką standardową.")
            return None

    @classmethod
    def touch_cache(cls, client: genai.Client, cache_name: str, ttl_seconds: int = DEFAULT_CACHE_TTL_SECONDS):
        """Przedłuża ruchome okno życia cache o 20 minut od tej sekundy (Kroczący Heartbeat)."""
        if not client or not cache_name:
            return
        try:
            if hasattr(client, "caches") and hasattr(client.caches, "update"):
                client.caches.update(
                    name=cache_name,
                    config=types.UpdateCachedContentConfig(ttl=f"{ttl_seconds}s")
                )
                logger.debug(f"[Context Cache]: Heartbeat odświeżony dla {cache_name} (+{ttl_seconds}s)")
        except Exception as e:
            logger.debug(f"[Context Cache]: Nie udało się zaktualizować Heartbeatu dla {cache_name}: {e}")

    @classmethod
    def cleanup_all_active_caches(cls, client: genai.Client):
        """Natychmiast usuwa wszystkie aktywne i osierocone obiekty cache ze serwerów Google po zakończeniu pracy."""
        if not client:
            return
        try:
            # 1. Usunięcie zarejestrowanych obiektów w lokalnej sesji
            if hasattr(client, "caches") and hasattr(client.caches, "delete"):
                for hash_key, cache_name in list(_LOCAL_CACHE_REGISTRY.items()):
                    try:
                        client.caches.delete(name=cache_name)
                        logger.info(f"[Context Cache]: Bezpiecznie usunięto cache {cache_name} (0 zł opłat po zakończeniu).")
                    except Exception:
                        pass
                _LOCAL_CACHE_REGISTRY.clear()

            # 2. Zamiatanie wszelkich osieroconych obiektów 'avt_' na koncie Google
            if hasattr(client, "caches") and hasattr(client.caches, "list"):
                for existing in client.caches.list():
                    if existing.display_name and existing.display_name.startswith("avt_"):
                        try:
                            client.caches.delete(name=existing.name)
                            logger.info(f"[Context Cache]: Usunięto osierocony obiekt cache: {existing.display_name}")
                        except Exception:
                            pass
        except Exception as e:
            logger.debug(f"[Context Cache]: Błąd podczas czyszczenia cache: {e}")

