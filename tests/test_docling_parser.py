"""The Docling wrapper, with a fake document. No models are loaded."""

import subprocess
import sys

from docintel.domain.parse.docling_parser import pages_of


class FakeDocument:
    def export_to_markdown(self, page_no):
        return {1: "first page", 3: "third page"}.get(page_no, "")


def test_every_page_keeps_its_place():
    assert pages_of(FakeDocument(), 3) == ["first page", "", "third page"]


def test_importing_the_parsers_does_not_load_torch():
    code = "import sys, docintel.domain.parse; sys.exit('torch' in sys.modules)"
    assert subprocess.run([sys.executable, "-c", code]).returncode == 0
