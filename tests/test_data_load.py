"""Loader tests on a tiny fake CUAD_v1/ folder (2 contracts) built in a temp dir."""

import json

import pytest
from pypdf import PdfWriter

from docintel.data.load import load_cuad
from docintel.store import connect

TEXT_A = "CO-BRANDING AGREEMENT between Acme Inc. and Beta LLC. Governed by the laws of Delaware."
TEXT_B = "SUPPLY AGREEMENT. Nothing interesting here."


def _qa(stem, category, answers):
    return {
        "id": f"{stem}__{category}",
        "question": f'... "{category}" ...',
        "answers": answers,
        "is_impossible": not answers,
    }


@pytest.fixture
def cuad_dir(tmp_path):
    root = tmp_path / "CUAD_v1"
    (root / "full_contract_txt").mkdir(parents=True)

    docs = {"AcmeCorp_CoBranding": TEXT_A, "BetaCo_Supply": TEXT_B}
    for stem, text in docs.items():
        (root / "full_contract_txt" / f"{stem}.txt").write_text(text)

    # PDFs live under Part_*/<Contract Type>/ — type comes from the folder name
    for stem, ctype, pages in [
        ("AcmeCorp_CoBranding", "Co_Branding", 3),
        ("BetaCo_Supply", "Supply", 1),
    ]:
        d = root / "full_contract_pdf" / "Part_I" / ctype
        d.mkdir(parents=True)
        w = PdfWriter()
        for _ in range(pages):
            w.add_blank_page(width=612, height=792)
        # mimic real CUAD drift: BetaCo's PDF has a trailing space + uppercase .PDF
        fname = f"{stem}.pdf" if stem.startswith("Acme") else f"{stem} .PDF"
        w.write(d / fname)

    law = "laws of Delaware"
    parties = ["Acme Inc.", "Beta LLC"]
    data = {
        "version": "aok_v1.0",
        "data": [
            {
                "title": "AcmeCorp_CoBranding",
                "paragraphs": [
                    {
                        "context": TEXT_A,
                        "qas": [
                            _qa(
                                "AcmeCorp_CoBranding",
                                "Governing Law",
                                [{"text": law, "answer_start": TEXT_A.index(law)}],
                            ),
                            _qa(
                                "AcmeCorp_CoBranding",
                                "Parties",
                                [{"text": p, "answer_start": TEXT_A.index(p)} for p in parties],
                            ),
                        ],
                    }
                ],
            },
            {
                "title": "BetaCo_Supply",
                "paragraphs": [
                    {
                        "context": TEXT_B,
                        "qas": [
                            _qa("BetaCo_Supply", "Governing Law", []),
                        ],
                    }
                ],
            },
        ],
    }
    (root / "CUAD_v1.json").write_text(json.dumps(data))
    (root / "master_clauses.csv").write_text(
        "Filename,Document Name-Answer\n"
        "AcmeCorp_CoBranding.pdf,CO-BRANDING AGREEMENT\n"
        "BetaCo_Supply.pdf,SUPPLY AGREEMENT\n"
    )
    return root


@pytest.fixture
def con(cuad_dir):
    c = connect(":memory:")
    load_cuad(c, cuad_dir)
    yield c
    c.close()


def test_counts(cuad_dir):
    with connect(":memory:") as c:
        assert load_cuad(c, cuad_dir) == (2, 4)  # 1 law + 2 parties + 1 absent


def test_contract_row(con):
    row = con.execute(
        "SELECT title, contract_type, n_pages, n_chars FROM contracts "
        "WHERE doc_id = 'AcmeCorp_CoBranding'"
    ).fetchone()
    assert row == ("CO-BRANDING AGREEMENT", "Co_Branding", 3, len(TEXT_A))


def test_offsets_point_at_span(con):
    rows = con.execute(
        "SELECT l.span_text, l.start_char, l.end_char, c.txt_path FROM labels l "
        "JOIN contracts c USING (doc_id) WHERE l.is_present"
    ).fetchall()
    for span, start, end, txt_path in rows:
        assert open(txt_path).read()[start:end] == span


def test_absent_label_is_explicit(con):
    row = con.execute(
        "SELECT span_text, start_char, is_present FROM labels "
        "WHERE doc_id = 'BetaCo_Supply' AND category = 'Governing Law'"
    ).fetchone()
    assert row == (None, None, False)


def test_reload_is_idempotent(con, cuad_dir):
    load_cuad(con, cuad_dir)
    assert con.execute("SELECT count(*) FROM contracts").fetchone()[0] == 2


def test_messy_filenames_still_match():
    from docintel.data.load import _key, _lookup

    assert _key("LECLANCHÉ S.A. - A&R AGREEMENT ") == _key("LECLANCHÉ S.A. - A_R AGREEMENT")
    table = {_key("Harpoon_Development Agreement_Option Agreement"): "hit"}
    assert _lookup(table, "Harpoon_Development Agreement") == "hit"


def test_pdf_with_trailing_space_found(con):
    row = con.execute(
        "SELECT contract_type, n_pages FROM contracts WHERE doc_id = 'BetaCo_Supply'"
    ).fetchone()
    assert row == ("Supply", 1)
