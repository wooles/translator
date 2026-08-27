# -*- coding: utf-8 -*-
"""
Unified Google GenAI Client Factory.
Handles automatic switching between standard Google AI Studio Developer API
and European Enterprise Vertex AI endpoints (europe-west1 / Belgia).
"""

import os
import logging
from typing import Optional
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
        return genai.Client(api_key=key, http_options=http_opts)
    else:
        return genai.Client(http_opts=http_opts)
