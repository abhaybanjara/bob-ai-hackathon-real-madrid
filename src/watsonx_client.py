"""
watsonx_client.py — optional IBM watsonx.ai integration.

When USE_WATSONX=false (or credentials are absent) this module creates a
no-op stub so the rest of the application never needs to check for None.

Usage
-----
    from watsonx_client import get_watsonx_client
    client = get_watsonx_client()   # may return None if disabled/unconfigured
"""
from __future__ import annotations

import os
from typing import Optional

from constants import EvidenceCategory


# ── Prompt template ───────────────────────────────────────────────────────────

_CLASSIFY_PROMPT = """\
You are a forensic evidence classification assistant.
Classify the following evidence description into exactly one of these categories:
Biological, Digital, Document, Trace, Impression, Video.

Evidence description: "{description}"

Respond with only the category name, nothing else.
"""

_VALID_CATEGORIES = {c.value.lower(): c for c in EvidenceCategory}


def _parse_category(raw: str) -> Optional[EvidenceCategory]:
    cleaned = raw.strip().lower().rstrip(".")
    return _VALID_CATEGORIES.get(cleaned)


class WatsonxClient:
    """Thin wrapper around ibm-watsonx-ai ModelInference."""

    def __init__(self, api_key: str, project_id: str, url: str) -> None:
        from ibm_watsonx_ai import Credentials
        from ibm_watsonx_ai.foundation_models import ModelInference

        credentials = Credentials(api_key=api_key, url=url)
        self._model = ModelInference(
            model_id="ibm/granite-13b-instruct-v2",
            credentials=credentials,
            project_id=project_id,
            params={"max_new_tokens": 10, "temperature": 0.0},
        )

    def classify(self, description: str) -> tuple[Optional[EvidenceCategory], float]:
        """
        Return (category, confidence) or (None, 0.0) on failure.
        Confidence for watsonx responses is fixed at 0.90 (model is trusted).
        """
        prompt = _CLASSIFY_PROMPT.format(description=description)
        try:
            response = self._model.generate_text(prompt=prompt)
            category = _parse_category(response or "")
            if category is not None:
                return category, 0.90
        except Exception:
            pass
        return None, 0.0


def get_watsonx_client() -> Optional[WatsonxClient]:
    """
    Return a WatsonxClient if credentials are present and USE_WATSONX=true,
    otherwise return None (offline mode).
    """
    use_wx = os.getenv("USE_WATSONX", "false").strip().lower()
    if use_wx != "true":
        return None

    api_key = os.getenv("WATSONX_API_KEY", "").strip()
    project_id = os.getenv("WATSONX_PROJECT_ID", "").strip()
    url = os.getenv("WATSONX_URL", "https://us-south.ml.cloud.ibm.com").strip()

    placeholder_values = {"your_api_key_here", "", "none"}
    if api_key.lower() in placeholder_values or project_id.lower() in placeholder_values:
        return None

    try:
        return WatsonxClient(api_key=api_key, project_id=project_id, url=url)
    except Exception:
        return None
