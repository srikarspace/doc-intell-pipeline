"""Split tests on a tiny fake `contracts` table: 3 types, 2 families with 2 docs each."""

import pytest

from docintel.evals.datasets import family, make_splits, pick_side
from docintel.evals.store import connect

DOCS = [(f"CO{i}_2020-EX-10-AGREEMENT", ["Supply", "Service", "Hosting"][i % 3]) for i in range(30)]
DOCS += [
    ("CO0_2020-EX-10-AGREEMENT_AMENDMENT", "Supply"),  # same family as CO0
    ("Beta Corp. - Supply Agreement", "Supply"),
    ("Beta Corp. - First Amendment", "Joint Venture _ Filing"),  # family crosses types
]


@pytest.fixture
def con():
    with connect(":memory:") as c:
        c.execute("CREATE TABLE contracts (doc_id VARCHAR, contract_type VARCHAR)")
        c.executemany("INSERT INTO contracts VALUES (?, ?)", DOCS)
        yield c


def _splits(con):
    return con.execute("SELECT doc_id, split FROM splits ORDER BY doc_id").fetchall()


def test_family_key():
    assert family("CO0_2020-EX-10-AGREEMENT_AMENDMENT") == "co0"
    assert family("Monsanto Company - SECOND A_R AGREEMENT") == "monsanto company"


def test_pick_side():
    assert pick_side({"dev": 0, "test": 0}, {"dev": 3, "test": 1}, 0.5) == "test"
    assert pick_side({"dev": 1, "test": 0}, {"dev": 0, "test": 9}, 0.5) == "test"


def test_same_seed_same_splits(con):
    make_splits(con, seed=7, n_docs=12)
    first = _splits(con)
    make_splits(con, seed=7, n_docs=12)
    assert _splits(con) == first


def test_family_on_one_side(con):
    for seed in range(20):
        make_splits(con, seed=seed, n_docs=12)
        sides = {}
        for doc_id, split in _splits(con):
            sides.setdefault(family(doc_id), set()).add(split)
        assert all(len(s) == 1 for s in sides.values()), f"seed {seed}"


def test_only_dev_and_test(con):
    counts = make_splits(con, seed=0, n_docs=12)
    rows = _splits(con)
    assert {split for _, split in rows} == {"dev", "test"}
    assert counts["dev"] + counts["test"] == len(rows)
