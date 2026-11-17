"""The sample contracts that ship with the app: CUAD dev PDFs (CC BY 4.0) and one fake scan."""

import json
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel

SAMPLES_DIR = Path(__file__).parent / "samples"


class Sample(BaseModel):
    id: str
    title: str
    contract_type: str
    pages: int
    scan: bool
    doc_id: str  # the CUAD id, so a result can be traced back to its labels


@lru_cache
def load_samples() -> dict[str, Sample]:
    rows = json.loads((SAMPLES_DIR / "samples.json").read_text(encoding="utf-8"))
    return {row["id"]: Sample(**row) for row in rows}


def sample_pdf(sample_id: str) -> Path | None:
    """The PDF of one sample, or None if there is no such sample."""
    if sample_id not in load_samples():  # never build a path from an unknown id
        return None
    return SAMPLES_DIR / f"{sample_id}.pdf"
