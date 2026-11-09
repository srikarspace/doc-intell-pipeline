# Phase 3b: fake scans and CER

In this part, you build a tool that damages a clean PDF until it looks like a bad scan. Then you build a number
that says how far a parser's text is from the true text. Each piece has a checkpoint.

This is part 1 of 3 for Phase 3b. It makes **no paid calls**. 3b2 designs the experiment. 3b3 runs it.

## Words used in this part

Read these first. Parser, cache and OCR are from 3a and 3a2.

- **Text layer**: the letters stored inside a PDF, which a program can copy. Example: pypdf reads 4,498 characters.
- **Scan**: a PDF that holds only pictures of pages. It has no text layer.
- **Fake scan**: a scan we make ourselves, from a clean PDF.
- **Condition**: one level of damage. Example: `mild` or `heavy`. Clean text is also a condition.
- **Blur**: letter edges become soft. Example: a scanner that is a little out of focus.
- **Noise**: random grey specks across the page. Example: a dirty photocopy.
- **Pixel**: one dot of an image. In a grey image, 0 is black and 255 is white.
- **Seed**: a number that fixes what "random" gives. Same seed, same numbers.
- **Edit distance**: how many single-character changes turn one text into another. Example: `name` to `nane` is 1.
- **CER (character error rate)**: edit distance divided by the length of the true text. Example: 1 / 4 = 0.25.
- **Reference**: the text we treat as correct. Here it is CUAD's `.txt` file.
- **Normalizing**: removing differences that are not real errors. Example: extra spaces.

## Objectives

By the end of this part you should be able to:

1. Turn a clean PDF into a PDF of damaged page pictures, the same way every time.
2. Prove that a fake scan has no text layer.
3. Explain why the seed uses `crc32` and not Python's `hash()`.
4. Compute CER against CUAD's text, and say what you normalize and why.
5. Give a real case where CER looks bad and the text is still useful.

## Dependencies

New libraries:

- `pillow`: opens, changes and saves images. It is like `sharp` in Node.
- `numpy`: fast maths on big grids of numbers. We use it to add noise to every pixel.
- `rapidfuzz`: a fast edit distance. Contracts are long, so plain Python is too slow.

Docling already brings `pillow` and `numpy`. We use them directly, so we list them, as with `pypdfium2` in 3a3.

This part needs:

- 3a: `ParsedDoc` and the cache.
- 3a3: `pypdfium2`, and the cached `deepseek_vl` text for one contract.
- 3a2: the cached `docling` text for one contract.

## The big picture

Before this part, the parsers had only read clean PDFs. A clean PDF is the easy case.

After this part:

```text
clean PDF -> page pictures -> turn, blur, grain -> fake scan PDF (no text layer)
                                                       |
                       any parser -> text -> CER against CUAD's .txt
```

- **3b2** runs this on the chosen contracts, and builds the experiment around it.
- **3b3** answers the question in the README: does paying for a vision LLM help on scans?
- **Phase 4** must accept real scans from users. This part shows what happens to them.

## Remember this

> A real scan has no answer key. We do not know what its text should be. A fake scan does: we damage a PDF whose
> correct text we already have. So any error we measure comes from the reading.
>
> **Damage what you can already read.**

## Why

**Real scans cannot be scored.** CUAD's lawyer labels point at CUAD's text. A fake scan keeps the same words and the
same labels, so the F1 from Phase 2 still works.

**CER looks at the text alone.** F1 mixes the parser and the extraction model. CER tells you if the text was read
correctly, before any model touches it.

**The two numbers can disagree.** That is the lesson of Round 3. You need both to explain a result.

## Design decisions

- **Fake scans, made from CUAD PDFs.** We keep the gold labels. Other option: find real scanned contracts. They have
  no labels, so nothing could be scored.
- **The output is a normal PDF.** Every parser already takes a PDF path, so no parser changes. Other option: save PNG
  files. Each parser would then need a second way in.
- **Damage in scanner order: turn, blur, grain.** Paper turns first, the lens blurs next, and the sensor adds grain
  last. Other option: grain before blur. The blur would then wipe out most of the grain.
- **A small frozen settings object per condition.** A condition is a name you can log, not four loose numbers. Other
  option: pass four arguments everywhere. A typo would make a new condition without anyone seeing it.
- **One random generator per page, from `(seed, crc32(doc_id), page_no)`.** A change on page 3 cannot change page 4.
  Other option: one generator for the whole run. Adding a contract would change every later page.
- **The test compares pixels, not file bytes.** Pillow writes the current time into each PDF, so the bytes always
  differ. Other option: compare files. That test would fail on correct code.
- **CER on the whole contract.** CUAD's `.txt` has no page breaks. We checked: 0 form feeds. Other option: CER per
  page. There is no true text per page to compare with.
- **The reference is CUAD's `.txt`, not pypdf.** The labels were made on it, so it is the fair standard. Other option:
  pypdf output. pypdf would then get a perfect score by definition.

## Worked example

All numbers are real. The contract is Kubient's Master Services Agreement, Part 2: 2 pages, 7,600 characters. Guess
before you open each box.

### Round 1: what can pypdf read from a scan?

The clean PDF gives pypdf 4,498 characters on page 1, and 3,090 on page 2. Guess the numbers for the mild fake scan.

<details><summary>Guess, then open</summary>

```text
clean: [4498, 3090]
mild:  [0, 0]
```

Zero. The text layer is gone, so there is nothing to copy. The page still looks fine to a person. This is why a text
parser fails on a scan without any error message.
</details>

### Round 2: is Docling really worse at reading?

CER on clean text, with no normalizing: pypdf 0.015, Docling 0.073. Guess: did Docling misread 7% of the characters?

<details><summary>Guess, then open</summary>

No. Docling writes Markdown, like `## Heading` and `**bold**`. Those marks count as errors in a raw comparison. After
removing them, Docling's CER is **0.001**, and pypdf's is **0.002**. A number is only useful after you remove what is
not an error. Step 7 is your decision on this.
</details>

### Round 3: can high CER still be good text?

Docling with OCR read the two damaged versions:

| Text | CER | Label quotes found |
|---|---|---|
| Docling OCR, mild | 0.121 | 12 of 13 |
| Docling OCR, heavy | 0.323 | 5 of 13 |

For the mild scan, guess: are 12% of the letters wrong?

<details><summary>Guess, then open</summary>

No. On the first 3,000 characters, CER is **0.001**. Nearly every letter is right. The error comes from the table on
page 2. OCR read its cells in a different order, so edit distance counts many changes. The words are correct, but
they moved.

Heavy is different. Here is its first line, as read: `Ths Esiba B is entered inte aa of the 2nth dey of March`. The
letters are really wrong, and quotes are lost. CER alone cannot tell you which case you have.
</details>

## Project setup

```sh
uv add pillow numpy rapidfuzz
touch src/docintel/domain/parse/scan.py
touch src/docintel/evals/cer.py
touch tests/test_scan.py
```

You should now have:

```text
src/docintel/
├── domain/parse/
│   └── scan.py          # new
└── evals/
    └── cer.py           # new
tests/
└── test_scan.py         # new
```

Fake scans go to `data/scans/`. The `data/` folder is in `.gitignore`.

## Step 1: draw a page

**Why.** Everything that follows starts from a picture of the page.

Put this in `src/docintel/domain/parse/scan.py`:

```python
"""Fake scans: pictures of pages with no text layer, made the same way every time."""

import zlib
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pypdfium2 as pdfium
from PIL import Image, ImageFilter

SCANS_DIR = Path("data/scans")
SEED = 0


@dataclass(frozen=True)
class ScanConfig:
    dpi: int  # how sharp the page picture is
    max_rotate: float  # the page turns at random, up to this many degrees either way
    blur: float  # radius of the blur, in pixels
    noise: float  # how strong the random grain is, 0 to 255


def render_pages(pdf_path: Path, dpi: int) -> list[Image.Image]:
    """One grey picture per page."""
    pdf = pdfium.PdfDocument(pdf_path)
    return [page.render(scale=dpi / 72).to_pil().convert("L") for page in pdf]
```

*Python here: [a frozen dataclass](./py/phase-3b.md#py-1).*

Here, we:

1. Describe a condition with four numbers. `frozen=True` means nobody can change one by accident.
2. Draw each page at a chosen DPI, and make it grey. This is the same drawing call as `page_images` in 3a3.

## Step 2: choose the damage (your decision)

**Why.** These numbers decide how hard the test is. Too easy and all parsers tie. Too hard and all parsers fail.

Decide two things. Write them in `EXPERIMENTS.md`, under a new `## E3` heading.

**How many conditions.** Each extra condition adds a vision bill, about $0.22 on 69 pages (3b2 shows the estimate).

**How much damage.** Here is the evidence, for the Kubient contract:

| Setting | DPI | Turn | Blur | Noise | Page 1 picture | Docling OCR CER | Quotes |
|---|---|---|---|---|---|---|---|
| Light damage | 150 | 0.5 | 0.5 | 8 | sharp, grainy | 0.121 | 12/13 |
| Strong damage | 100 | 1.5 | 0.8 | 20 | soft, very grainy | 0.323 | 5/13 |

What to look at: you want a condition where free OCR still works, and a condition where it starts to break. If both
of yours give the same CER, change one. Step 5 lets you see your own values.

<details><summary>Reference (open after you write yours)</summary>

Two conditions, named `mild` and `heavy`. Mild is a decent office scan. Heavy is a poor photocopy that a person can
still read. Free OCR gets hurt by heavy, so vision has a chance to show its worth.

Add to the bottom of `src/docintel/domain/parse/scan.py`:

```python
CONDITIONS = {
    "mild": ScanConfig(dpi=150, max_rotate=0.5, blur=0.5, noise=8),
    "heavy": ScanConfig(dpi=100, max_rotate=1.5, blur=0.8, noise=20),
}
```
</details>

The steps below use the reference values. Use your own.

## Step 3: damage one page

**Why.** This is the core of the degrader.

Add to the bottom of `src/docintel/domain/parse/scan.py`:

```python
def page_rng(seed: int, doc_id: str, page_no: int) -> np.random.Generator:
    """A random generator for one page. The same three inputs always give the same numbers."""
    return np.random.default_rng([seed, zlib.crc32(doc_id.encode()), page_no])


def degrade(image: Image.Image, cfg: ScanConfig, rng: np.random.Generator) -> Image.Image:
    """Damage one grey page in the order a scanner does: turn, blur, then grain."""
    angle = rng.uniform(-cfg.max_rotate, cfg.max_rotate)
    image = image.rotate(angle, resample=Image.Resampling.BICUBIC, fillcolor=255)
    image = image.filter(ImageFilter.GaussianBlur(cfg.blur))
    pixels = np.asarray(image, dtype=np.float32)
    noisy = pixels + rng.normal(0, cfg.noise, pixels.shape)
    return Image.fromarray(noisy.clip(0, 255).astype(np.uint8))
```

*Python here: [numbers from a list seed](./py/phase-3b.md#py-2) · [maths on a whole image](./py/phase-3b.md#py-3).*

Here, for one page, in order:

1. Pick a small random angle, and turn the page. White fills the corners.
2. Blur it.
3. Turn the image into a grid of numbers, and add random grain to every pixel.
4. Keep every value between 0 and 255, and turn the grid back into an image.

Checkpoint (free):

```sh
uv run python - <<'EOF'
from pathlib import Path

import numpy as np

from docintel.domain.parse.scan import CONDITIONS, degrade, page_rng, render_pages
from docintel.evals.store import connect

with connect() as con:
    doc_id, path = con.execute(
        "SELECT doc_id, pdf_path FROM contracts WHERE doc_id LIKE 'KUBIENT,INC_07_02_2020-EX-10.14%'"
    ).fetchone()
clean = render_pages(Path(path), 150)[0]
damaged = degrade(clean, CONDITIONS["mild"], page_rng(0, doc_id, 1))
print("clean:  ", clean.size, clean.mode, "average", round(float(np.asarray(clean).mean()), 1))
print("damaged:", damaged.size, damaged.mode, "average", round(float(np.asarray(damaged).mean()), 1))
EOF
```

```text
clean:   (1240, 1755) L average 243.7
damaged: (1240, 1755) L average 240.2
```

The size stays the same. The average gets a little darker, because the grain reaches pure white and can only go down.

## Step 4: write the fake scan as a PDF

**Why.** Every parser takes a PDF path, so a fake scan must be a PDF.

Add to the bottom of `src/docintel/domain/parse/scan.py`:

```python
def scan_pages(pdf_path: Path, doc_id: str, condition: str, seed: int = SEED) -> list[Image.Image]:
    """The damaged pictures of every page of one contract."""
    cfg = CONDITIONS[condition]
    clean = render_pages(pdf_path, cfg.dpi)
    return [degrade(im, cfg, page_rng(seed, doc_id, n)) for n, im in enumerate(clean, start=1)]


def scan_path(doc_id: str, condition: str, scans_dir: Path = SCANS_DIR) -> Path:
    return scans_dir / condition / f"{doc_id}.pdf"


def make_scan(
    pdf_path: Path, out_path: Path, doc_id: str, condition: str, seed: int = SEED
) -> Path:
    """Write the fake scan as a PDF that holds only pictures."""
    first, *rest = scan_pages(pdf_path, doc_id, condition, seed)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    first.save(
        out_path,
        format="PDF",
        save_all=True,
        append_images=rest,
        resolution=CONDITIONS[condition].dpi,
    )
    return out_path
```

*Python here: [`first, *rest`](./py/phase-3b.md#py-4).*

Here, we:

1. Number pages from 1, so each page has its own random generator.
2. Save the first image as a PDF, and add the others as more pages.
3. Tell Pillow the DPI, so the PDF page has its real size. Without it, a 100 DPI page would come out too large.

Checkpoint:

```sh
uv run python - <<'EOF'
from pathlib import Path

from pypdf import PdfReader

from docintel.domain.parse.scan import CONDITIONS, make_scan, scan_path
from docintel.evals.store import connect

with connect() as con:
    doc_id, path = con.execute(
        "SELECT doc_id, pdf_path FROM contracts WHERE doc_id LIKE 'KUBIENT,INC_07_02_2020-EX-10.14%'"
    ).fetchone()
print("clean:", [len(p.extract_text()) for p in PdfReader(path).pages], Path(path).stat().st_size // 1024, "KB")
for condition in CONDITIONS:
    out = make_scan(Path(path), scan_path(doc_id, condition), doc_id, condition)
    print(f"{condition}:", [len(p.extract_text() or "") for p in PdfReader(out).pages], out.stat().st_size // 1024, "KB")
EOF
```

```text
clean: [4498, 3090] 115 KB
mild: [0, 0] 675 KB
heavy: [0, 0] 493 KB
```

Zero characters on every page. That proves there is no text layer. The files are larger, because they hold pictures.

## Step 5: before and after

**Why.** A number cannot tell you if a page looks like a real scan. Your eyes can.

Run this (it writes one PNG, and needs no new file):

```sh
uv run python - <<'EOF'
from pathlib import Path

from PIL import Image

from docintel.domain.parse.scan import render_pages, scan_pages
from docintel.evals.store import connect

with connect() as con:
    doc_id, path = con.execute(
        "SELECT doc_id, pdf_path FROM contracts WHERE doc_id LIKE 'KUBIENT,INC_07_02_2020-EX-10.14%'"
    ).fetchone()
clean = render_pages(Path(path), 150)[0]
mild = scan_pages(Path(path), doc_id, "mild")[0]
heavy = scan_pages(Path(path), doc_id, "heavy")[0].resize(clean.size)
box = (100, 120, 1200, 420)
h = box[3] - box[1]
sheet = Image.new("L", (box[2] - box[0], 3 * h + 20), 128)
for row, image in enumerate([clean, mild, heavy]):
    sheet.paste(image.crop(box), (0, row * (h + 10)))
out = Path("data/scans/before_after.png")
sheet.save(out)
print(out, sheet.size)
EOF
open data/scans/before_after.png
```

```text
data/scans/before_after.png (1100, 920)
```

You should see three strips of the same text. The top is sharp. The middle is sharp with light grain. The bottom is
soft and grainy, but a person can still read it. If the bottom is not readable, your damage is too strong.

## Step 6: same seed, same pixels

**Why.** If a fake scan changes between runs, two runs are not comparing the same thing.

Checkpoint:

```sh
uv run python - <<'EOF'
import hashlib
from pathlib import Path

from docintel.domain.parse.scan import scan_pages
from docintel.evals.store import connect

with connect() as con:
    doc_id, path = con.execute(
        "SELECT doc_id, pdf_path FROM contracts WHERE doc_id LIKE 'KUBIENT,INC_07_02_2020-EX-10.14%'"
    ).fetchone()
def md5(b): return hashlib.md5(b).hexdigest()[:8]
print("pixels seed 0:", md5(scan_pages(Path(path), doc_id, "mild")[0].tobytes()))
print("pixels seed 0:", md5(scan_pages(Path(path), doc_id, "mild")[0].tobytes()))
print("pixels seed 1:", md5(scan_pages(Path(path), doc_id, "mild", seed=1)[0].tobytes()))
EOF
```

```text
pixels seed 0: 57e375b1
pixels seed 0: 57e375b1
pixels seed 1: fa1de2ae
```

The first two lines must match. Your hashes match these only if your settings are the reference values.

## Step 7: CER (your decision)

**Why.** This is the number that says how well the text was read, before extraction.

You decide what counts as an error. Here is the real evidence, on the Kubient contract:

| Level | What it removes | pypdf | Docling | Vision LLM |
|---|---|---|---|---|
| `raw` | nothing | 0.015 | 0.073 | 0.026 |
| `spaces` | extra spaces, odd Unicode forms | 0.002 | 0.056 | 0.011 |
| `case` | + capital letters | 0.002 | 0.056 | 0.011 |
| `marks` | + Markdown marks | 0.002 | 0.001 | 0.011 |

Things to weigh:

- Extraction reads words. Spaces and capitals rarely change a meaning for it.
- Markdown marks are a format, and the words are still there.
- A stricter level is more honest about what the file holds. It also punishes Docling for its format.

Write your level in `EXPERIMENTS.md`, under `## E3`, with one reason.

<details><summary>Reference (open after you write yours)</summary>

Level `marks`. CER should measure reading mistakes. A format choice is not a reading mistake.

Put this in `src/docintel/evals/cer.py`:

```python
"""Character error rate: how far a parser's text is from CUAD's .txt."""

import re
import unicodedata

from rapidfuzz.distance import Levenshtein

MARKDOWN = re.compile(r"^#{1,6}\s+|\*\*|^\s*\|?[-:| ]+\|\s*$", re.MULTILINE)


def normalize(text: str, level: str = "marks") -> str:
    """Remove differences that are not reading errors. Each level adds to the one before."""
    if level == "raw":
        return text
    text = unicodedata.normalize("NFKC", text)
    if level == "marks":
        text = MARKDOWN.sub("", text)
    text = " ".join(text.split())
    if level in ("case", "marks"):
        text = text.casefold()
    return text


def cer(text: str, reference: str, level: str = "marks") -> float:
    """Character changes needed to turn `text` into `reference`, divided by its length."""
    ref = normalize(reference, level)
    return Levenshtein.distance(normalize(text, level), ref) / max(len(ref), 1)
```
</details>

*Python here: [a regular expression with `re.MULTILINE`](./py/phase-3b.md#py-5).*

Here, we:

1. Fix odd Unicode forms with NFKC, so `ﬁ` (one character) becomes `fi` (two).
2. Remove Markdown marks.
3. Put one space between all words, then lowercase everything.
4. Count the edits and divide by the length of the true text.

CER can be above 1. A very long wrong text needs more edits than the true text has characters.

Checkpoint (free; this uses the cached text):

```sh
uv run python - <<'EOF'
import json
from pathlib import Path

from docintel.domain.validate.citations import quote_status, words
from docintel.evals.cer import cer
from docintel.evals.store import connect

with connect() as con:
    doc_id, txt = con.execute(
        "SELECT doc_id, txt_path FROM contracts WHERE doc_id LIKE 'KUBIENT,INC_07_02_2020-EX-10.14%'"
    ).fetchone()
    spans = [s for (s,) in con.execute(
        "SELECT span_text FROM labels WHERE doc_id = ? AND is_present AND span_text IS NOT NULL", [doc_id]
    ).fetchall()]
ref = Path(txt).read_text(encoding="utf-8")
def cached(p): return json.loads(Path(f"data/parse_cache/{p}/{doc_id}.json").read_text())["text"]
texts = {"pypdf clean": cached("pypdf"), "docling clean": cached("docling"),
         "deepseek_vl clean": cached("deepseek_vl"), "pypdf mild": ""}
print(f"{'':20} {'raw':>6} {'spaces':>6} {'case':>6} {'marks':>6}  quotes")
for name, text in texts.items():
    source = words(text)
    status = [quote_status(s, source) for s in spans]
    found = sum(x in ("same_words", "gap") for x in status)
    levels = " ".join(f"{cer(text, ref, level):6.3f}" for level in ("raw", "spaces", "case", "marks"))
    print(f"{name:20} {levels}  {found}/{len(status)}")
EOF
```

```text
                        raw spaces   case  marks  quotes
pypdf clean           0.015  0.002  0.002  0.002  13/13
docling clean         0.073  0.056  0.056  0.001  13/13
deepseek_vl clean     0.026  0.011  0.011  0.011  11/13
pypdf mild            1.000  1.000  1.000  1.000  0/13
```

Look at the vision row. Its CER is low, and it still lost 2 quotes of 13. A small error can land on a place that
matters.

## Step 8: a small test

**Why.** If a scan stops being repeatable, or CER stops counting correctly, nothing warns you. The results just change.

The test names say what is protected: same seed gives same pixels, another seed or doc gives other pixels, a scan has
no text layer, and CER counts correctly on small known cases.

<details><summary>Put this in <code>tests/test_scan.py</code></summary>

```python
"""Fake scans and CER: the rules that must never break without a warning."""

import pytest
from pypdf import PdfReader, PdfWriter

from docintel.domain.parse.scan import make_scan, scan_pages
from docintel.evals.cer import cer, normalize


@pytest.fixture
def pdf(tmp_path):
    writer = PdfWriter()
    for _ in range(2):
        writer.add_blank_page(width=200, height=200)
    path = tmp_path / "clean.pdf"
    writer.write(path)
    return path


def pixels(pdf, seed=0, doc_id="doc-1"):
    return [im.tobytes() for im in scan_pages(pdf, doc_id, "mild", seed)]


def test_same_seed_gives_the_same_pixels(pdf):
    assert pixels(pdf) == pixels(pdf)


def test_another_seed_or_doc_gives_other_pixels(pdf):
    assert pixels(pdf) != pixels(pdf, seed=1)
    assert pixels(pdf) != pixels(pdf, doc_id="doc-2")


def test_pages_of_one_doc_differ(pdf):
    first, second = pixels(pdf)
    assert first != second


def test_a_scan_has_no_text_layer_and_keeps_its_pages(pdf, tmp_path):
    reader = PdfReader(make_scan(pdf, tmp_path / "scan.pdf", "doc-1", "mild"))
    assert len(reader.pages) == 2
    assert all(not page.extract_text() for page in reader.pages)


@pytest.mark.parametrize(
    "text, expected",
    [("abc", 0.0), ("abd", 1 / 3), ("", 1.0), ("abcabcabc", 2.0)],
)
def test_cer_known_cases(text, expected):
    assert cer(text, "abc") == pytest.approx(expected)


def test_normalize_removes_only_what_is_not_an_error():
    assert normalize("## The  Party\n**Name**") == "the party name"
    assert normalize("a b", "raw") == "a b"
    assert cer("## Name", "name") == 0.0
    assert cer("Nane", "name") == pytest.approx(0.25)
```
</details>

*Python here: [`pytest.mark.parametrize`](./py/phase-3b.md#py-6).*

Here, we use blank pages, so the test needs no contract and no network. The grain alone makes the pixels differ.

Checkpoint:

```sh
uv run pytest tests/test_scan.py -q
make lint
```

```text
.........                                                                [100%]
9 passed in 0.46s
```

Your project structure should now look like this:

```text
src/docintel/
├── domain/parse/
│   ├── base.py
│   ├── cache.py
│   ├── docling_parser.py
│   ├── pypdf_parser.py
│   ├── scan.py              # ScanConfig, CONDITIONS, degrade, make_scan
│   └── vision.py
└── evals/
    └── cer.py               # normalize, cer
tests/
└── test_scan.py
data/scans/                  # mild/, heavy/, before_after.png (not in git)
```

<details><summary>Complete <code>src/docintel/domain/parse/scan.py</code></summary>

```python
"""Fake scans: pictures of pages with no text layer, made the same way every time."""

import zlib
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pypdfium2 as pdfium
from PIL import Image, ImageFilter

SCANS_DIR = Path("data/scans")
SEED = 0


@dataclass(frozen=True)
class ScanConfig:
    dpi: int  # how sharp the page picture is
    max_rotate: float  # the page turns at random, up to this many degrees either way
    blur: float  # radius of the blur, in pixels
    noise: float  # how strong the random grain is, 0 to 255


CONDITIONS = {
    "mild": ScanConfig(dpi=150, max_rotate=0.5, blur=0.5, noise=8),
    "heavy": ScanConfig(dpi=100, max_rotate=1.5, blur=0.8, noise=20),
}


def page_rng(seed: int, doc_id: str, page_no: int) -> np.random.Generator:
    """A random generator for one page. The same three inputs always give the same numbers."""
    return np.random.default_rng([seed, zlib.crc32(doc_id.encode()), page_no])


def degrade(image: Image.Image, cfg: ScanConfig, rng: np.random.Generator) -> Image.Image:
    """Damage one grey page in the order a scanner does: turn, blur, then grain."""
    angle = rng.uniform(-cfg.max_rotate, cfg.max_rotate)
    image = image.rotate(angle, resample=Image.Resampling.BICUBIC, fillcolor=255)
    image = image.filter(ImageFilter.GaussianBlur(cfg.blur))
    pixels = np.asarray(image, dtype=np.float32)
    noisy = pixels + rng.normal(0, cfg.noise, pixels.shape)
    return Image.fromarray(noisy.clip(0, 255).astype(np.uint8))


def render_pages(pdf_path: Path, dpi: int) -> list[Image.Image]:
    """One grey picture per page."""
    pdf = pdfium.PdfDocument(pdf_path)
    return [page.render(scale=dpi / 72).to_pil().convert("L") for page in pdf]


def scan_pages(pdf_path: Path, doc_id: str, condition: str, seed: int = SEED) -> list[Image.Image]:
    """The damaged pictures of every page of one contract."""
    cfg = CONDITIONS[condition]
    clean = render_pages(pdf_path, cfg.dpi)
    return [degrade(im, cfg, page_rng(seed, doc_id, n)) for n, im in enumerate(clean, start=1)]


def scan_path(doc_id: str, condition: str, scans_dir: Path = SCANS_DIR) -> Path:
    return scans_dir / condition / f"{doc_id}.pdf"


def make_scan(
    pdf_path: Path, out_path: Path, doc_id: str, condition: str, seed: int = SEED
) -> Path:
    """Write the fake scan as a PDF that holds only pictures."""
    first, *rest = scan_pages(pdf_path, doc_id, condition, seed)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    first.save(
        out_path,
        format="PDF",
        save_all=True,
        append_images=rest,
        resolution=CONDITIONS[condition].dpi,
    )
    return out_path
```
</details>

## Break it on purpose

Both breaks are free. Put the code back after each one.

**Break 1: use Python's `hash()`.** In `page_rng`, replace `zlib.crc32(doc_id.encode())` with `abs(hash(doc_id))`. Run
the tests. Then run the Step 6 checkpoint twice. Guess: does a test notice?

<details><summary>What you see</summary>

```text
9 passed
```

All tests pass. But the Step 6 hash changes between the two runs of the command:

```text
pixels seed 0: e4064e47
pixels seed 0: 685bb557
```

Python changes `hash()` for strings each time it starts, as a safety feature. The tests run in one process, so they
cannot see it. Your fake scans would change on every run, and nothing would tell you. That is why we use `crc32`.
</details>

**Break 2: stop removing Markdown.** In `normalize`, replace the line `text = MARKDOWN.sub("", text)` with `pass`.
Guess: which test fails?

<details><summary>What you see</summary>

```text
FAILED tests/test_scan.py::test_normalize_removes_only_what_is_not_an_error
1 failed, 8 passed
```

Good. Without it, Docling would look seven times worse for a format choice.
</details>

## Gotchas

- **Scan files differ, but pixels do not.** Pillow writes the time into each PDF. Compare pixels, never files.
- **Do not use `hash()` for a seed.** Break 1 shows why.
- **Two contracts start with `KUBIENT`.** The checkpoints use the full name, so they find the right one.
- **Close the notebook first.** DuckDB allows one writer at a time.

## Explain back, then commit

Explain to Claude in a few sentences:

- `scan.py`: the order of the damage, and why it is in that order. What `seed`, `doc_id` and `page_no` each do.
- Why a fake scan has gold labels and a real scan does not.
- `cer.py`: what each level of `normalize` removes, and your choice of level.
- One real case where CER and quotes disagree, and why.
- `test_scan.py`: why Break 1 passes the tests.

Then:

```sh
git status
git add pyproject.toml uv.lock src/docintel/domain/parse/scan.py src/docintel/evals/cer.py tests/test_scan.py EXPERIMENTS.md
git commit -m "phase 3b: fake scans and CER"
```

## Conclusion

You can now make a fake scan with a known answer, and measure how well any parser reads it. Go back through the
objectives and check each one without notes. Then answer:

1. A parser has CER 0.12, and it found 12 of 13 quotes. What would you check before you call it bad?
2. Why does the seed need the document name and the page number, and not just one number?

Looking for more challenges? Try these (optional):

1. Add JPEG compression as a fourth effect, and see if it changes CER.
2. Compute a word-level error rate, and see if the table problem from Round 3 becomes smaller.

Checklist (`../PLAN.md`): **Parsers: text layer vs layout vs multimodal; CER** (the CER part). Next: 3b2.
