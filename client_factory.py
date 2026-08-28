# -*- coding: utf-8 -*-
"""
Unified Google GenAI Client Factory.
Handles automatic switching between standard Google AI Studio Developer API
and European Enterprise Vertex AI endpoints (europe-west1 / Belgia).
"""

import os
import logging
from typing import Optional, Dict, Any
from google import genai
from google.genai import types

logger = logging.getLogger("client_factory")


def get_genai_client(
    api_key: Optional[str] = None,
    timeout_ms: int = 120000,
    force_ai_studio: bool = False
) -> genai.Client:
    """
    Creates and returns a genai.Client instance.
    If gcp_key.json exists (or GOOGLE_GENAI_USE_VERTEXAI is True),
    authenticates using European Vertex AI Enterprise credentials (europe-west1 / Belgia).
    Otherwise, connects via standard Google AI Studio API Key.
    """
    use_vertex = os.environ.get("GOOGLE_GENAI_USE_VERTEXAI", "1").lower() in ["1", "true", "yes"]
    key_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "").strip()
    if not key_path:
        default_key = os.path.join(os.path.dirname(__file__), "gcp_key.json")
        if os.path.exists(default_key):
            key_path = default_key

    location = os.environ.get("GOOGLE_CLOUD_LOCATION", "europe-west1").strip()
    http_opts = types.HttpOptions(timeout=timeout_ms)

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
                http_opts=http_opts if hasattr(types, "HttpOptions") else None
            )
        except Exception as e:
            logger.warning(f"Vertex AI initialization failed ({e}). Falling back to Google AI Studio.")

    key = api_key or os.environ.get("GEMINI_API_KEY", "").strip()
    if key:
        # If multiple keys are provided, use the first key as default single client
        first_key = [k.strip() for k in key.replace(";", ",").split(",") if k.strip()][0]
        return genai.Client(api_key=first_key, http_options=http_opts)
    else:
        return genai.Client(http_opts=http_opts)


class MultiKeyClientPool:
    """
    Thread-safe Round-Robin Client Pool across multiple Google AI Studio API Keys.
    Allows concurrent batches to distribute requests across independent gateway queues.
    """
    _SHARED_POOLS: Dict[str, Any] = {}

    def __init__(self, raw_keys: Optional[str] = None, timeout_ms: int = 120000):
        import threading
        import concurrent.futures
        self._lock = threading.Lock()
        self._idx = 0
        raw = raw_keys or os.environ.get("GEMINI_API_KEY", "").strip()
        keys_list = [k.strip() for k in raw.replace(";", ",").split(",") if k.strip()]
        if not keys_list:
            keys_list = [""]

        http_opts = types.HttpOptions(timeout=timeout_ms)
        
        def _make_client(k: str) -> genai.Client:
            if k:
                return genai.Client(api_key=k, http_options=http_opts)
            else:
                return genai.Client(http_options=http_opts)

        # Initialize all clients in parallel for sub-second startup
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(32, max(4, len(keys_list)))) as executor:
            self.clients = list(executor.map(_make_client, keys_list))

        logger.info(f"[MultiKey Pool]: Active gateway pool with {len(self.clients)} API channel(s).")

    def get_client(self) -> genai.Client:
        """Returns next client in round-robin sequence."""
        with self._lock:
            client = self.clients[self._idx % len(self.clients)]
            self._idx += 1
            return client


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


