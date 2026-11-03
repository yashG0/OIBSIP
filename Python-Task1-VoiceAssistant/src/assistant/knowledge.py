"""Offline question answering backed by a small editable JSON knowledge base."""

from __future__ import annotations

import json
import re
from pathlib import Path

from assistant.nlu import intent_tokens

KNOWLEDGE_PATH = Path(__file__).resolve().parents[2] / "config" / "knowledge.json"
STOP_WORDS = {
    "a", "an", "and", "are", "be", "by", "can", "could", "do", "does",
    "for", "from", "give", "how", "i", "in", "is", "it", "me", "of",
    "please", "tell", "the", "to", "was", "what", "when", "where", "which",
    "who", "why", "would", "you",
}


def answer_question(question: str) -> str | None:
    """Find the closest matching fact without sending the question online."""
    try:
        with KNOWLEDGE_PATH.open(encoding="utf-8") as knowledge_file:
            facts = json.load(knowledge_file).get("facts", [])
    except (OSError, json.JSONDecodeError, AttributeError):
        return None

    question_terms = {
        token for token in intent_tokens(question)
        if token not in STOP_WORDS and len(token) > 1
    }
    if not question_terms:
        return None

    best: tuple[float, int, str] | None = None
    for fact in facts:
        if not isinstance(fact, dict) or not isinstance(fact.get("answer"), str):
            continue
        aliases = fact.get("aliases", [])
        if not isinstance(aliases, list):
            continue
        for alias in aliases:
            if not isinstance(alias, str) or not alias.strip():
                continue
            alias_terms = {
                token for token in intent_tokens(alias)
                if token not in STOP_WORDS and len(token) > 1
            }
            if not alias_terms:
                continue
            exact = bool(re.search(rf"\b{re.escape(alias.casefold())}\b", question.casefold()))
            overlap = len(question_terms & alias_terms)
            score = 1.0 if exact else overlap / len(alias_terms)
            if overlap == 0 or (not exact and score < 0.75):
                continue
            candidate = (score, len(alias_terms), fact["answer"])
            if best is None or candidate[:2] > best[:2]:
                best = candidate

    return best[2] if best else None
