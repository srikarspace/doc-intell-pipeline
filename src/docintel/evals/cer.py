"""Character error rate: how far a parser's text is from CUAD's .txt."""

import re
import unicodedata

from rapidfuzz.distance import Levenshtein

MARKDOWN = re.compile(r"^#{1,6}\s+|\*\*|^\s*\|?[-:| ]+\|\s*$", re.MULTILINE)


def normalize(text: str, level: str = "marks") -> str:
    """Remove differences that are not reading errors. Each level adds to the one before."""
    if level == "raw":
        return text
    text = unicodedata.normalize("NFKC", text)
    if level == "marks":
        text = MARKDOWN.sub("", text)
    text = " ".join(text.split())
    if level in ("case", "marks"):
        text = text.casefold()
    return text


def cer(text: str, reference: str, level: str = "marks") -> float:
    """Character changes needed to turn `text` into `reference`, divided by its length."""
    ref = normalize(reference, level)
    return Levenshtein.distance(normalize(text, level), ref) / max(len(ref), 1)
