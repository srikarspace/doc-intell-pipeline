"""P/R/F1 and the group sums. No network, no CUAD files."""

import pytest

from docintel.domain.schema.fields import CUAD_CATEGORY
from docintel.evals.runner import TABLES
from docintel.evals.scorers import metrics, prf
from docintel.evals.store import connect

ROW = "INSERT INTO scores (run_id, doc_id, field, tp, fp, fn) VALUES ('r1', 'd1', ?, ?, 0, ?)"


def test_prf():
    assert prf(8, 2, 8) == {"precision": 0.8, "recall": 0.5, "f1": pytest.approx(16 / 26)}
    assert prf(0, 0, 10) == {"precision": None, "recall": 0.0, "f1": 0.0}  # the lazy model
    assert prf(0, 0, 0) == {"precision": None, "recall": None, "f1": None}  # only TNs


def test_groups_add_up_counts():
    with connect(":memory:") as con:
        con.execute(TABLES)
        for field in CUAD_CATEGORY:
            tp, fn = (1, 1) if field in ("parties", "agreement_date") else (0, 0)
            con.execute(ROW, [field, tp, fn])
        rows = {r["name"]: r for r in metrics(con, "r1")}
    assert len(rows) == 12 + 4 + 1
    assert (rows["basic facts"]["tp"], rows["basic facts"]["fn"]) == (2, 2)
    assert rows["basic facts"]["recall"] == rows["all"]["recall"] == 0.5
    assert rows["cap_on_liability"]["f1"] is None
