"""Loader tests on a tiny fake CUAD_v1/ folder: 2 contracts, built fresh in a temp dir."""

import json
import unicodedata

import pytest
from pypdf import PdfWriter

from docintel.evals.datasets import _key, _lookup, load_cuad
from docintel.evals.store import connect

ACME = "CO-BRANDING AGREEMENT between Acme Inc. and Beta LLC. Governed by the laws of Delaware."
BETA = "SUPPLY AGREEMENT. Nothing interesting here."


def _qa(stem, category, text, spans):
    answers = [{"text": s, "answer_start": text.index(s)} for s in spans]
    return {"id": f"{stem}__{category}", "answers": answers, "is_impossible": not answers}


@pytest.fixture
def cuad_dir(tmp_path):
    root = tmp_path / "CUAD_v1"
    (root / "full_contract_txt").mkdir(parents=True)
    (root / "full_contract_txt" / "Acme.txt").write_text(ACME)
    (root / "full_contract_txt" / "Beta.txt").write_text(BETA)

    # Beta's PDF copies a real CUAD quirk: trailing space + uppercase .PDF
    for ctype, filename, pages in [("Co_Branding", "Acme.pdf", 3), ("Supply", "Beta .PDF", 1)]:
        folder = root / "full_contract_pdf" / "Part_I" / ctype
        folder.mkdir(parents=True)
        writer = PdfWriter()
        for _ in range(pages):
            writer.add_blank_page(width=612, height=792)
        writer.write(folder / filename)

    acme_qas = [
        _qa("Acme", "Governing Law", ACME, ["laws of Delaware"]),
        _qa("Acme", "Parties", ACME, ["Acme Inc.", "Beta LLC"]),
    ]
    beta_qas = [_qa("Beta", "Governing Law", BETA, [])]
    data = {"data": [
        {"title": "Acme", "paragraphs": [{"context": ACME, "qas": acme_qas}]},
        {"title": "Beta", "paragraphs": [{"context": BETA, "qas": beta_qas}]},
    ]}  # fmt: skip
    (root / "CUAD_v1.json").write_text(json.dumps(data))
    (root / "master_clauses.csv").write_text(
        "Filename,Document Name-Answer\nAcme.pdf,CO-BRANDING AGREEMENT\nBeta.pdf,SUPPLY AGREEMENT\n"
    )
    return root


@pytest.fixture
def con(cuad_dir):
    with connect(":memory:") as c:
        assert load_cuad(c, cuad_dir) == (2, 4)  # 1 law + 2 parties + 1 absent
        yield c


def test_contract_rows(con):
    rows = con.execute(
        "SELECT doc_id, title, contract_type, n_pages, n_chars FROM contracts ORDER BY doc_id"
    ).fetchall()
    assert rows == [
        ("Acme", "CO-BRANDING AGREEMENT", "Co_Branding", 3, len(ACME)),
        ("Beta", "SUPPLY AGREEMENT", "Supply", 1, len(BETA)),  # messy PDF name still found
    ]


def test_offsets_point_at_span(con):
    rows = con.execute(
        "SELECT l.span_text, l.start_char, l.end_char, c.txt_path "
        "FROM labels l JOIN contracts c USING (doc_id) WHERE l.is_present"
    ).fetchall()
    for span, start, end, txt_path in rows:
        assert open(txt_path).read()[start:end] == span


def test_absent_label_is_a_row(con):
    row = con.execute(
        "SELECT span_text, start_char, is_present FROM labels WHERE doc_id = 'Beta'"
    ).fetchone()
    assert row == (None, None, False)


def test_messy_names_match():
    pdf_name = "LECLANCHÉ S.A. - A&R AGREEMENT "
    json_name = unicodedata.normalize("NFD", "LECLANCHÉ S.A. - A_R AGREEMENT")  # É -> E + accent
    assert pdf_name != json_name
    assert _key(pdf_name) == _key(json_name)
    table = {_key("Harpoon_Development Agreement_Option Agreement"): "hit"}
    assert _lookup(table, "Harpoon_Development Agreement") == "hit"
