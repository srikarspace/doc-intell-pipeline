"""Where is a quote on the page? Line boxes from the text layer, so the UI can highlight it."""

import re
from pathlib import Path

import pypdfium2 as pdfium
from pydantic import BaseModel

WORD = re.compile(r"[a-z0-9]+")  # the same word rule as `citations.words`


Rect = tuple[float, float, float, float]  # x0, y0, x1, y1 in PDF points; (0, 0) is bottom left


class Highlight(BaseModel):
    quote_index: int
    page: int  # from 1
    page_size: tuple[float, float]
    rects: list[Rect]


def find_span(quote: list[str], words: list[str]) -> tuple[int, int] | None:
    """The first and last word index of `quote` inside `words`, side by side. None if absent."""
    n = len(quote)
    for start in range(len(words) - n + 1):
        if words[start : start + n] == quote:
            return start, start + n - 1
    return None


def same_line(line: list[float], box: Rect) -> bool:
    """A box is on the current line if it is to the right and overlaps it from top to bottom."""
    x0, y0, _, y1 = box
    return x0 >= line[2] - 1 and y0 < line[3] and y1 > line[1]


def line_rects(boxes: list[Rect]) -> list[Rect]:
    """Join char boxes into one box per line, in reading order."""
    lines: list[list[float]] = []
    for box in boxes:
        if lines and same_line(lines[-1], box):
            line = lines[-1]
            line[1], line[2], line[3] = min(line[1], box[1]), box[2], max(line[3], box[3])
        else:
            lines.append(list(box))
    return [tuple(round(v, 1) for v in line) for line in lines]


def locate(pdf_path: Path, quotes: list[str]) -> list[Highlight]:
    """One Highlight per quote found in the text layer. A quote that is not found is skipped."""
    wanted = [(i, WORD.findall(q.lower())) for i, q in enumerate(quotes)]
    found = []
    pdf = pdfium.PdfDocument(pdf_path)
    for page_no, page in enumerate(pdf, start=1):
        text_page = page.get_textpage()
        text = text_page.get_text_range()
        spans = [(m.start(), m.end()) for m in WORD.finditer(text.lower())]
        words = [text[a:b].lower() for a, b in spans]
        for i, quote in wanted:
            span = find_span(quote, words) if quote else None
            if span is None:
                continue
            first, last = spans[span[0]][0], spans[span[1]][1]
            boxes = [text_page.get_charbox(k) for k in range(first, last) if not text[k].isspace()]
            found.append(
                Highlight(
                    quote_index=i, page=page_no, page_size=page.get_size(), rects=line_rects(boxes)
                )
            )
        wanted = [(i, q) for i, q in wanted if i not in {h.quote_index for h in found}]
    pdf.close()
    return sorted(found, key=lambda h: h.quote_index)


def line_around(text: str, words: str) -> str:
    """The whole line of `text` that holds `words`. A short rule match becomes a line to show."""
    at = text.find(words)
    if at < 0:
        return words
    start = text.rfind("\n", 0, at) + 1
    end = text.find("\n", at + len(words))
    return text[start : end if end >= 0 else len(text)].strip()
