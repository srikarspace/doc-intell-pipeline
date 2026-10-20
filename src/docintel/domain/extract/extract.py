"""Extract the 12 fields from one contract, with one LLM call and a versioned prompt."""

from pathlib import Path

import duckdb

from docintel.core.llm import LLMResult, call_llm
from docintel.domain.schema.fields import ContractFields

PROMPTS = Path(__file__).parent / "prompts"
PLACEHOLDER = "{contract}"


def load_prompt(version: str) -> tuple[str, str]:
    """(system, user) text of one prompt version, like "v1"."""
    folder = PROMPTS / version
    system = (folder / "system.md").read_text(encoding="utf-8")
    user = (folder / "user.md").read_text(encoding="utf-8")
    return system, user


def build_messages(text: str, version: str = "v1") -> list[dict]:
    """The messages for one contract. The contract text goes in unchanged."""
    system, user = load_prompt(version)
    if user.count(PLACEHOLDER) != 1:
        raise ValueError(f"prompt {version}: user.md must contain {PLACEHOLDER} exactly once")
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user.replace(PLACEHOLDER, text)},
    ]


def extract(
    text: str,
    model: str | None = None,
    *,
    prompt_version: str = "v1",
    con: duckdb.DuckDBPyConnection | None = None,
    run_id: str | None = None,
) -> LLMResult[ContractFields]:
    """All 12 fields for one contract text."""
    messages = build_messages(text, prompt_version)
    return call_llm(messages, ContractFields, con=con, run_id=run_id, model=model)
