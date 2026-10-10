"""T132: check, downscale and re-encode an image before it goes to a vision provider (doc 124 privacy risk).

Takes a PNG, JPEG or WebP image, or one page of a PDF tech pack, and returns a PNG whose longest side is at
most ``MAX_SIDE`` px. Re-encoding drops EXIF and every other metadata block.
"""
from io import BytesIO

import pdfplumber
from pdfplumber.utils.exceptions import PdfminerException
from PIL import Image

from app.ports.style_detector import StyleImage

MAX_SIDE = 1536
MAX_BYTES = 10_000_000
POINTS_PER_INCH = 72
_SIGNATURES = {b"\x89PNG\r\n\x1a\n": "PNG", b"\xff\xd8\xff": "JPEG", b"%PDF-": "PDF"}
_UNREADABLE = (OSError, Image.DecompressionBombError, PdfminerException, ZeroDivisionError)  # 0-size page


class UnsupportedImage(ValueError):
    """The bytes are not one of the accepted formats (the API answers 415)."""


def _kind(data: bytes) -> str | None:
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "WEBP"
    return next((kind for signature, kind in _SIGNATURES.items() if data.startswith(signature)), None)


def _bitmap(data: bytes, kind: str) -> Image.Image:
    with Image.open(BytesIO(data), formats=[kind]) as image:
        image.load()
        return image.convert("RGB")


def _pdf_page(data: bytes, page: int) -> Image.Image:
    with pdfplumber.open(BytesIO(data)) as pdf:
        if not 1 <= page <= len(pdf.pages):
            raise LookupError(f"The PDF has no page {page}; it has {len(pdf.pages)}")
        sheet = pdf.pages[page - 1]
        resolution = POINTS_PER_INCH * MAX_SIDE / max(sheet.width, sheet.height)
        return sheet.to_image(resolution=resolution).original.convert("RGB")


def prepare_image(data: bytes, page: int = 1) -> StyleImage:
    """Raises ValueError naming what is wrong with the upload; never returns the original bytes."""
    if len(data) > MAX_BYTES:
        raise ValueError("Maximum image size is 10 MB")
    kind = _kind(data)
    if kind is None:
        raise UnsupportedImage("Upload a PNG, JPEG, WebP or PDF image")
    try:
        image = _pdf_page(data, page) if kind == "PDF" else _bitmap(data, kind)
    except LookupError as missing:
        raise ValueError(str(missing)) from None
    except _UNREADABLE:
        raise ValueError(f"The {kind} file could not be read") from None
    image.thumbnail((MAX_SIDE, MAX_SIDE))
    encoded = BytesIO()
    image.save(encoded, "PNG", optimize=True)
    return StyleImage("image/png", encoded.getvalue())
