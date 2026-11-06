"""Is a quote really in the contract? Compares words, in order, and never scores "how close"."""

import re

MAX_GAP = 60


def words(text: str) -> list[str]:
    """Lowercase words and numbers, in order. Spaces, case and punctuation are gone."""
    return re.findall(r"[a-z0-9]+", text.lower())


def same_words(quote_words: list[str], source_words: list[str]) -> bool:
    """True if the quote's words appear in the source side by side, with nothing between."""
    return f" {' '.join(quote_words)} " in f" {' '.join(source_words)} "


def follows_from(quote_words: list[str], source_words: list[str], start: int) -> bool:
    """True if the other quote words follow `start` in order, each within MAX_GAP extra words."""
    pos = start
    for word in quote_words[1:]:
        window = source_words[pos + 1 : pos + 2 + MAX_GAP]
        if word not in window:
            return False
        pos += 1 + window.index(word)
    return True


def in_order(quote_words: list[str], source_words: list[str]) -> bool:
    """True if the quote's words appear in order somewhere, with small gaps allowed."""
    return any(
        word == quote_words[0] and follows_from(quote_words, source_words, start)
        for start, word in enumerate(source_words)
    )


def quote_status(quote: str, source_words: list[str]) -> str:
    """One of: no_words, same_words, gap, missing."""
    quote_words = words(quote)
    if not quote_words:
        return "no_words"
    if same_words(quote_words, source_words):
        return "same_words"
    if in_order(quote_words, source_words):
        return "gap"
    return "missing"
