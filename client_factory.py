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
    If GOOGLE_GENAI_USE_VERTEXAI is set to True and GOOGLE_CLOUD_PROJECT is configured,
    connects to the European Vertex AI enterprise cluster (e.g. europe-west1).
    Otherwise, connects via Google AI Studio API Key.
    """
    use_vertex = os.environ.get("GOOGLE_GENAI_USE_VERTEXAI", "").lower() in ["1", "true", "yes"]
    project_id = os.environ.get("GOOGLE_CLOUD_PROJECT", "").strip()
    location = os.environ.get("GOOGLE_CLOUD_LOCATION", "europe-west1").strip()
    key = api_key or os.environ.get("GEMINI_API_KEY", "").strip()

    http_opts = types.HttpOptions(timeout=timeout_ms)

    if use_vertex and project_id and not force_ai_studio:
        logger.info(f"Connecting to European Vertex AI Enterprise Cluster ({location}) in project '{project_id}'...")
        return genai.Client(
            vertexai=True,
            project=project_id,
            location=location,
            api_key=key if key else None,
            http_options=http_opts
        )
    elif key:
        return genai.Client(api_key=key, http_options=http_opts)
    else:
        return genai.Client(http_opts)
