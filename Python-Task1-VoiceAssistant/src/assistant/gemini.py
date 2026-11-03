"""Optional Gemini fallback for general questions missing from the local KB."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from google import genai

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MODEL_NAME = "gemini-3.5-flash-lite"


@lru_cache(maxsize=1)
def _client(api_key: str) -> genai.Client:
    return genai.Client(api_key=api_key)


def answer_with_gemini(question: str) -> str:
    """Answer one general question, without retaining server-side chat state."""
    load_dotenv(PROJECT_ROOT / ".env")
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    model_name = os.getenv("GEMINI_MODEL", MODEL_NAME).strip() or MODEL_NAME
    if not api_key:
        raise RuntimeError("Gemini isn't configured. Add GEMINI_API_KEY to your .env file.")

    try:
        interaction = _client(api_key).interactions.create(
            model=model_name,
            input=question,
            store=False,
            system_instruction=(
                "You are a concise voice assistant answering general knowledge questions. "
                "Reply in plain text, in at most three short sentences. If uncertain, say so. "
                "Do not claim to have performed actions or accessed live information."
            ),
            generation_config={
                "max_output_tokens": 180,
                "thinking_level": "minimal",
            },
        )
    except Exception as exc:
        raise RuntimeError("Gemini could not answer right now. Check the key, connection, and quota.") from exc

    answer = (interaction.output_text or "").strip()
    if not answer:
        raise RuntimeError("Gemini returned an empty answer. Please try asking another way.")
    return answer
