"""Parser 3: send a picture of each page to a vision LLM. Paid, per page."""

import base64
import io
import time
from pathlib import Path

import pypdfium2 as pdfium

from docintel.core.llm import call_llm
from docintel.domain.parse.base import ParsedDoc, Parser, from_pages
from docintel.domain.schema.fields import Strict
from docintel.evals.store import connect

MODELS = {
    "deepseek_vl": "deepseek/deepseek-v4.1-flash-1017",
    "kimi_vl": "moonshotai/kimi-k2.6",
}
MAX_PAGES = 20
DPI = 150
MAX_OUTPUT_TOKENS = 12_000  # hidden thinking counts; one call without a limit cost $0.46
PROMPT = (
    "Copy all the text on this page, exactly as written, in reading order. "
    "Do not fix mistakes. Do not add a summary or comments. "
    "If a word cannot be read, write [unclear]. If the page is blank, return an empty string."
)


class PageText(Strict):
    text: str


class TooManyPages(ValueError):
    pass


class BudgetExceeded(RuntimeError):
    pass


class Budget:
    """A spending limit shared by all calls of one run."""

    def __init__(self, limit_usd: float):
        self.limit_usd = limit_usd
        self.spent = 0.0

    def check(self, worst_case_usd: float) -> None:
        """Stop before a call that could pass the limit."""
        if self.spent + worst_case_usd > self.limit_usd:
            raise BudgetExceeded(
                f"spent ${self.spent:.4f}, next page could cost ${worst_case_usd:.4f}, "
                f"limit ${self.limit_usd:.2f}"
            )

    def add(self, cost_usd: float) -> None:
        self.spent += cost_usd

def page_images(pdf_path: Path, dpi: int = DPI) -> list[str]:
    """One PNG data URL per page. Refuses a document over MAX_PAGES."""
    pdf = pdfium.PdfDocument(pdf_path)
    if len(pdf) > MAX_PAGES:
        raise TooManyPages(f"{len(pdf)} pages, the cap is {MAX_PAGES}")
    urls = []
    for page in pdf:
        buffer = io.BytesIO()
        page.render(scale=dpi / 72).to_pil().convert("L").save(buffer, format="PNG")
        encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
        urls.append(f"data:image/png;base64,{encoded}")
    return urls


def page_messages(image_url: str) -> list[dict]:
    content = [
        {"type": "text", "text": PROMPT},
        {"type": "image_url", "image_url": {"url": image_url}},
    ]
    return [{"role": "user", "content": content}]

def make_vision_parser(
    parser_name: str,
    run_id: str | None = None,
    client=None,
    budget: Budget | None = None,
    worst_page_usd: float = 0.0,
) -> Parser:
    """A parser for one model. `run_id` tags its rows in `llm_calls`."""
    budget = budget or Budget(float("inf"))

    def parse(pdf_path: Path) -> ParsedDoc:
        start = time.perf_counter()
        pages, cost = [], 0.0
        with connect() as con:
            for url in page_images(pdf_path):
                budget.check(worst_page_usd)
                result = call_llm(
                    page_messages(url),
                    PageText,
                    con=con,
                    run_id=run_id,
                    model=MODELS[parser_name],
                    client=client,
                    max_tokens=MAX_OUTPUT_TOKENS,
                )
                budget.add(result.cost_usd or 0.0)  # a failed call is still paid for
                if result.parsed is None:  # raise, so a bad page never reaches the cache
                    raise ValueError(f"{parser_name}: bad answer: {result.error}")
                pages.append(result.parsed.text)
                cost += result.cost_usd or 0.0
        latency_ms = round((time.perf_counter() - start) * 1000)
        return from_pages(pages, cost_usd=cost, latency_ms=latency_ms, parser_name=parser_name)

    return parse