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
