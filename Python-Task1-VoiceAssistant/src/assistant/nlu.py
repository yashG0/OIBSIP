"""Lightweight, local intent tokenization using NLTK's Porter stemmer.

No external corpus is downloaded. Intent phrases and command slots are matched
locally, so recognized speech is not sent to an NLP provider.
"""

from __future__ import annotations

import re

try:
    from nltk.stem import PorterStemmer
except ImportError:  # Keep basic command parsing usable before dependencies sync.
    PorterStemmer = None

_STEMMER = PorterStemmer() if PorterStemmer else None


def intent_tokens(text: str) -> set[str]:
    """Return normalized words and stems to recognize common word variations."""
    words = set(re.findall(r"[a-z0-9@.+-]+", text.casefold()))
    if _STEMMER is None:
        return words
    return words | {_STEMMER.stem(word) for word in words}
