# -*- coding: utf-8 -*-
"""
Unified Google GenAI Client Factory.
Handles automatic switching between standard Google AI Studio Developer API
and European Enterprise Vertex AI endpoints (europe-west1 / Belgia).
"""

import os
import logging
from typing import Optional, Dict, Any, Tuple, List
from google import genai
from google.genai import types

logger = logging.getLogger("client_factory")


def format_friendly_api_error(e: Exception) -> str:
    """
    Formats raw Google API / network error dumps into clean, human-friendly Polish messages.
    Eliminates cryptic JSON dictionaries and technical codes.
    """
    err_str = str(e).lower()
    if "additionalproperties" in err_str:
        return "Niezgodność schematu Google Developer API (additionalProperties)"
    elif "503" in err_str or "unavailable" in err_str or "high demand" in err_str:
        return "Chwilowe przeciążenie serwerów Google (503 High Demand)"
    elif "429" in err_str or "quota" in err_str or "resource_exhausted" in err_str or "rate" in err_str:
        return "Chwilowy limit zapytań na kluczu (429 Rate Limit)"
    elif "504" in err_str or "deadline" in err_str or "timeout" in err_str or "timed out" in err_str:
        return "Przekroczono limit czasu odpowiedzi serwera (504 Timeout)"
    elif "500" in err_str or "internal" in err_str:
        return "Chwilowy błąd wewnętrzny serwera Google (500 Internal Error)"
    elif "connection" in err_str or "network" in err_str or "failed to connect" in err_str:
        return "Chwilowe zakłócenie połączenia internetowego"
    else:
        # Strip ugly JSON braces / raw dict dumps
        raw = str(e)
        if "{" in raw:
            raw = raw.split("{")[0].strip().rstrip(".:")
        return raw if raw else "Oczekiwanie na odpowiedź serwera"


def patch_google_genai_schema_sanitizer() -> None:
    """
    Patches google.genai._transformers.process_schema to ensure that
    'additionalProperties' is strictly eliminated from all generated JSON schemas
    when operating in Gemini Developer API mode (Google AI Studio).
    This prevents 400 INVALID_ARGUMENT errors on any nested Pydantic models.
    """
    try:
        from google.genai import _transformers
        if getattr(_transformers, "_additional_props_sanitizer_active", False):
            return

        orig_process = _transformers.process_schema

        def safe_process_schema(schema, client, *args, **kwargs):
            orig_process(schema, client, *args, **kwargs)

            def _strip_recursive(s):
                if isinstance(s, dict):
                    s.pop("additionalProperties", None)
                    s.pop("additional_properties", None)
                    for v in s.values():
                        if isinstance(v, dict):
                            _strip_recursive(v)
                        elif isinstance(v, list):
                            for item in v:
                                if isinstance(item, dict):
                                    _strip_recursive(item)

            _strip_recursive(schema)

        _transformers.process_schema = safe_process_schema
        _transformers._additional_props_sanitizer_active = True
        logger.debug("Google GenAI schema sanitizer patched successfully.")
    except Exception as e:
        logger.warning(f"Could not patch google.genai schema sanitizer: {e}")

# Automatically activate schema sanitizer upon module import
patch_google_genai_schema_sanitizer()


DEFAULT_HTTP_TIMEOUT_SEC = float(os.getenv("GEMINI_HTTP_TIMEOUT_SEC", "90.0"))

def get_genai_client(
    api_key: Optional[str] = None,
    timeout_sec: float = DEFAULT_HTTP_TIMEOUT_SEC,
    timeout_ms: Optional[int] = None,
    force_ai_studio: bool = False
) -> genai.Client:
    """
    Creates and returns a genai.Client instance with safe timeout in milliseconds.
    Accepts both timeout_sec (e.g. 45.0) and timeout_ms (e.g. 45000), smartly normalizing to milliseconds.
    If gcp_key.json exists (or GOOGLE_GENAI_USE_VERTEXAI is True),
    authenticates using European Vertex AI Enterprise credentials (europe-west1 / Belgia).
    Otherwise, connects via standard Google AI Studio API Key.
    """
    if timeout_ms is not None:
        final_timeout_ms = int(timeout_ms)
    else:
        final_timeout_ms = int(timeout_sec * 1000) if timeout_sec < 1000 else int(timeout_sec)
    
    # Enforce Google API minimum deadline requirement (min 10000ms = 10s)
    final_timeout_ms = max(10000, final_timeout_ms)

    # Vertex AI is strictly disabled by default to prevent unexpected Google Cloud enterprise billing.
    # The translator uses Google AI Studio API Keys (GEMINI_API_KEY) exclusively.
    use_vertex = os.environ.get("GOOGLE_GENAI_USE_VERTEXAI", "0").lower() in ["1", "true", "yes"]
    key_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "").strip()
    if not key_path and use_vertex:
        default_key = os.path.join(os.path.dirname(__file__), "gcp_key.json")
        if os.path.exists(default_key):
            key_path = default_key

    location = os.environ.get("GOOGLE_CLOUD_LOCATION", "europe-west1").strip()
    http_opts = types.HttpOptions(timeout=final_timeout_ms)

    if use_vertex and key_path and os.path.exists(key_path) and not force_ai_studio:
        try:
            from google.oauth2 import service_account
            creds = service_account.Credentials.from_service_account_file(
                key_path,
                scopes=["https://www.googleapis.com/auth/cloud-platform"]
            )
            project_id = creds.project_id or os.environ.get("GOOGLE_CLOUD_PROJECT", "").strip()
            logger.info(f"Connected to European Vertex AI Enterprise ({location}) in project '{project_id}' via Service Account.")
            return genai.Client(
                vertexai=True,
                project=project_id,
                location=location,
                credentials=creds,
                http_options=http_opts
            )
        except Exception as e:
            logger.warning(f"Vertex AI initialization failed ({e}). Falling back to Google AI Studio.")

    key = api_key or os.environ.get("GEMINI_API_KEY", "").strip()
    if key:
        # If multiple keys are provided, use the first key as default single client
        first_key = [k.strip() for k in key.replace(";", ",").split(",") if k.strip()][0]
        return genai.Client(api_key=first_key, http_options=http_opts)
    else:
        return genai.Client(http_options=http_opts)


class MultiKeyClientPool:
    """
    Thread-safe Smart Round-Robin Client Pool with Circuit Breaker and Auto-Banning of Exhausted Keys.
    Distributes requests only across active, healthy API keys, immediately cooling down keys that hit 429 quota.
    """
    def __init__(
        self,
        raw_keys: Optional[str] = None,
        timeout_sec: float = DEFAULT_HTTP_TIMEOUT_SEC,
        timeout_ms: Optional[int] = None
    ):
        import threading
        import time
        import concurrent.futures
        self._lock = threading.Lock()
        self._idx = 0
        self._cooldowns: Dict[int, float] = {}  # client index -> expiry monotonic time
        raw = raw_keys or os.environ.get("GEMINI_API_KEY", "").strip()
        keys_list = [k.strip() for k in raw.replace(";", ",").split(",") if k.strip()]
        if not keys_list:
            keys_list = [""]

        if timeout_ms is not None:
            final_timeout_ms = int(timeout_ms)
        else:
            final_timeout_ms = int(timeout_sec * 1000) if timeout_sec < 1000 else int(timeout_sec)

        final_timeout_ms = max(10000, final_timeout_ms)
        http_opts = types.HttpOptions(timeout=final_timeout_ms)
        
        def _make_client(k: str) -> genai.Client:
            if k:
                return genai.Client(api_key=k, http_options=http_opts)
            else:
                return genai.Client(http_options=http_opts)

        # Initialize all clients in parallel for sub-second startup
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(32, max(4, len(keys_list)))) as executor:
            self.clients = list(executor.map(_make_client, keys_list))

        # Fast parallel health probe on startup (only if multiple keys exist)
        if len(self.clients) > 1:
            def _probe_client(idx_c: Tuple[int, genai.Client]) -> Tuple[int, bool]:
                idx, c = idx_c
                try:
                    c.models.generate_content(
                        model="gemini-3.6-flash",
                        contents="ping",
                        config=types.GenerateContentConfig(max_output_tokens=1)
                    )
                    return idx, True
                except Exception as e:
                    err = str(e).lower()
                    if "429" in err or "quota" in err or "resource_exhausted" in err or "prepayment" in err:
                        return idx, False
                    return idx, True

            with concurrent.futures.ThreadPoolExecutor(max_workers=min(32, len(self.clients))) as executor:
                probe_results = list(executor.map(_probe_client, enumerate(self.clients)))

            now = time.monotonic()
            healthy_count = 0
            for idx, is_healthy in probe_results:
                if not is_healthy:
                    self._cooldowns[idx] = now + 300.0  # 5 min cooldown for exhausted keys
                else:
                    healthy_count += 1

            if healthy_count > 0:
                print(f"  [MultiKey Pool]: Gotowe {healthy_count}/{len(self.clients)} aktywnych kluczy API ({len(self.clients) - healthy_count} w trybie cooldown).")
            else:
                self._cooldowns.clear()  # Fallback: keep all if none passed

    def report_error(self, client: genai.Client, error_str: str):
        """Immediately puts client into cooldown upon 429 quota or account error."""
        import time
        err = error_str.lower()
        if "429" in err or "quota" in err or "resource_exhausted" in err or "prepayment" in err or "depleted" in err:
            with self._lock:
                for idx, c in enumerate(self.clients):
                    if c is client:
                        self._cooldowns[idx] = time.monotonic() + 180.0
                        break

    def get_client(self) -> genai.Client:
        """Returns next healthy client in round-robin sequence."""
        import time
        with self._lock:
            now = time.monotonic()
            # Clean expired cooldowns
            expired = [idx for idx, exp in self._cooldowns.items() if exp <= now]
            for idx in expired:
                del self._cooldowns[idx]

            available_indices = [i for i in range(len(self.clients)) if i not in self._cooldowns]
            if available_indices:
                chosen_idx = available_indices[self._idx % len(available_indices)]
                self._idx += 1
                return self.clients[chosen_idx]

            # If all are cooling down, pick the one expiring soonest
            soonest_idx = min(self._cooldowns.keys(), key=lambda k: self._cooldowns[k])
            return self.clients[soonest_idx]

    def get_active_clients(self) -> List[genai.Client]:
        """Returns list of currently active (non-cooling down) clients."""
        import time
        with self._lock:
            now = time.monotonic()
            active = [c for idx, c in enumerate(self.clients) if self._cooldowns.get(idx, 0) <= now]
            return active if active else self.clients


class TokenBucketLimiter:
    """
    High-frequency Token Bucket / Leaky Bucket Rate Limiter.
    Enforces a smooth pacing interval and smooth burst distribution
    to completely eliminate 429 rate limit spikes.
    """
    def __init__(self, rate_per_second: float = 18.0, burst_capacity: int = 4):
        import threading, time
        self.rate = rate_per_second
        self.capacity = burst_capacity
        self.tokens = float(burst_capacity)
        self.last_time = time.monotonic()
        self.lock = threading.Lock()

    def acquire(self):
        """Acquires a token, sleeping if rate limit burst window is reached."""
        import time, random
        with self.lock:
            while True:
                now = time.monotonic()
                elapsed = now - self.last_time
                self.last_time = now
                self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
                if self.tokens >= 1.0:
                    self.tokens -= 1.0
                    return
                wait = (1.0 - self.tokens) / self.rate
                time.sleep(max(0.005, wait + random.uniform(0.002, 0.008)))


# Global singleton instance for the entire translator process (Tier 2 High Throughput)
global_rate_limiter = TokenBucketLimiter(rate_per_second=float(os.getenv("RATE_LIMIT_PER_SEC", "35.0")), burst_capacity=8)


