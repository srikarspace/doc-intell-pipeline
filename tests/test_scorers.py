"""Scoring rules on tiny hand-made cases. No network, no CUAD files."""

import pytest

from docintel.domain.schema.fields import CUAD_CATEGORY, ContractFields, Names
from docintel.evals.scorers import jaccard, norm_date, outcome, score_doc
from docintel.evals.store import connect

LAW = "This Agreement shall be governed by the laws of the State of Michigan."


def test_jaccard():
    assert jaccard(LAW, LAW.upper()) == 1.0
    assert jaccard("Michigan", "Delaware") == 0.0
    assert jaccard("", LAW) == 0.0


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("11/14/17", "2017-11-14"),
        ("2017-11-14", "2017-11-14"),
        ("[]/[]/2020", "2020"),
        ("4/1/98", "1998-04-01"),
        ("[]/[]/[]", None),
        (None, None),
    ],
)
def test_norm_date(text, expected):
    assert norm_date(text) == expected


def test_outcome_table():
    assert outcome(gold_present=False, found=False, correct=True) == (0, 0, 0)  # true negative
    assert outcome(gold_present=False, found=True, correct=True) == (0, 1, 0)
    assert outcome(gold_present=True, found=False, correct=True) == (0, 0, 1)
    assert outcome(gold_present=True, found=True, correct=True) == (1, 0, 0)
    assert outcome(gold_present=True, found=True, correct=False) == (0, 1, 1)


def absent(cls) -> dict:
    """An empty answer for one field model."""
    data = {"quotes": [], "found": False}
    if "value" in cls.model_fields:
        data["value"] = [] if cls is Names else None
    return data


def test_score_doc_counts_absent_fields():
    """Gold: only Governing Law is present. The model finds it, and a non-compete that is absent."""
    pred = {f: absent(info.annotation) for f, info in ContractFields.model_fields.items()}
    pred["governing_law"] = {"quotes": [LAW], "value": "Michigan", "found": True}
    pred["non_compete"] = {"quotes": ["shall not compete"], "found": True}
    with connect(":memory:") as con:
        con.execute(
            "CREATE TABLE labels (doc_id TEXT, category TEXT, span_text TEXT, is_present BOOL)"
        )
        con.execute("CREATE TABLE answers (doc_id TEXT, category TEXT, answer TEXT)")
        for category in CUAD_CATEGORY.values():
            present = category == "Governing Law"
            span = LAW if present else None
            con.execute("INSERT INTO labels VALUES ('d1', ?, ?, ?)", [category, span, present])
        con.execute("INSERT INTO answers VALUES ('d1', 'Governing Law', 'Michigan')")
        rows = {r["field"]: r for r in score_doc(con, "d1", ContractFields.model_validate(pred))}
    assert (rows["governing_law"]["tp"], rows["governing_law"]["value_ok"]) == (1, True)
    assert rows["non_compete"]["fp"] == 1
    assert sum(r["tp"] + r["fp"] + r["fn"] for r in rows.values()) == 2  # 10 true negatives
