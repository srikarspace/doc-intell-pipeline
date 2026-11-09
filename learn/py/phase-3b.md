# Python for Phase 3b

This file explains the new Python in Part 3b. Read one section when the main doc links to it.

<a id="py-1"></a>
## PY-1. A frozen dataclass

```python
@dataclass(frozen=True)
class ScanConfig:
    dpi: int
    blur: float
```

1. `@dataclass` writes the `__init__` for you. You create one with `ScanConfig(dpi=150, blur=0.5)`.
2. `frozen=True` makes the object read-only. `cfg.dpi = 200` raises an error.

In JS, it is like `Object.freeze({ dpi: 150, blur: 0.5 })`, plus the field names and types are checked by your editor.

<a id="py-2"></a>
## PY-2. Numbers from a list seed

```python
np.random.default_rng([seed, zlib.crc32(doc_id.encode()), page_no])
```

1. `default_rng` makes a generator of random numbers. JS has no seeded random built in.
2. It accepts a list of whole numbers. All of them together decide the sequence.
3. `doc_id.encode()` turns the text into bytes. `zlib.crc32` turns those bytes into one number.
4. `crc32` always gives the same number for the same bytes, in every Python process.

<a id="py-3"></a>
## PY-3. Maths on a whole image

```python
pixels = np.asarray(image, dtype=np.float32)
noisy = pixels + rng.normal(0, cfg.noise, pixels.shape)
Image.fromarray(noisy.clip(0, 255).astype(np.uint8))
```

1. `np.asarray` turns the image into a grid of numbers, one per pixel.
2. `rng.normal(...)` makes a grid of random numbers with the same shape.
3. `+` adds the two grids, cell by cell. There is no loop to write. In JS, you would loop over every pixel.
4. `clip(0, 255)` keeps values in range. `astype(np.uint8)` makes them whole numbers again.

`float32` matters. In `uint8`, 250 + 10 wraps around and becomes 4, a black dot on a white page.

<a id="py-4"></a>
## PY-4. `first, *rest`

```python
first, *rest = scan_pages(pdf_path, doc_id, condition, seed)
```

`first` gets the first item. `rest` gets a list of all the others. In JS: `const [first, ...rest] = pages`.

<a id="py-5"></a>
## PY-5. A regular expression with `re.MULTILINE`

```python
MARKDOWN = re.compile(r"^#{1,6}\s+|\*\*|^\s*\|?[-:| ]+\|\s*$", re.MULTILINE)
```

1. `|` at the top level means "or". There are three patterns here.
2. `^#{1,6}\s+` is a Markdown heading mark, at the start of a line.
3. `\*\*` is a bold mark.
4. The last one is a table's divider row, like `| --- | --- |`.
5. `re.MULTILINE` makes `^` and `$` match at each line, not just the whole text. It is the `m` flag in JS: `/^#/m`.

`r"..."` is a raw string. Backslashes stay as they are.

<a id="py-6"></a>
## PY-6. `pytest.mark.parametrize`

```python
@pytest.mark.parametrize("text, expected", [("abc", 0.0), ("abd", 1 / 3)])
def test_cer_known_cases(text, expected):
    assert cer(text, "abc") == pytest.approx(expected)
```

The test runs once per pair. Each one is reported as its own test. In Jest, it is `test.each`.
