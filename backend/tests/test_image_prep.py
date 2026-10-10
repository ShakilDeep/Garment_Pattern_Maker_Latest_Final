"""T132: images are checked, downscaled and re-encoded before they leave the app (doc 124 privacy risk)."""
from io import BytesIO

import pytest
from conftest import REFERENCE_PATTERNS, needs_tech_packs
from PIL import Image
from reportlab.pdfgen import canvas

from app.infrastructure.image_prep import MAX_SIDE, prepare_image


def _jpeg(width, height):
    buffer, exif = BytesIO(), Image.Exif()
    exif[0x010F] = "Camera maker"
    Image.new("RGB", (width, height), "white").save(buffer, "JPEG", exif=exif)
    return buffer.getvalue()


def test_a_large_photo_is_downscaled_to_png_without_metadata():
    image = prepare_image(_jpeg(4000, 3000))
    decoded = Image.open(BytesIO(image.data))
    assert (image.mime, decoded.format, decoded.size) == ("image/png", "PNG", (MAX_SIDE, 1152))
    assert not decoded.getexif()


def test_a_small_image_keeps_its_size():
    assert Image.open(BytesIO(prepare_image(_jpeg(800, 600)).data)).size == (800, 600)


@needs_tech_packs
def test_a_tech_pack_page_renders_to_an_image():
    image = prepare_image((REFERENCE_PATTERNS / "1078375.pdf").read_bytes(), page=1)
    assert max(Image.open(BytesIO(image.data)).size) == MAX_SIDE


@pytest.mark.parametrize(("data", "page", "message"), [
    (b"GIF89a....", 1, "PNG, JPEG, WebP or PDF"),
    (b"", 1, "PNG, JPEG, WebP or PDF"),
    (b"\x89PNG\r\n\x1a\nbroken", 1, "could not be read"),
])
def test_unreadable_input_is_rejected(data, page, message):
    with pytest.raises(ValueError, match=message):
        prepare_image(data, page=page)


@pytest.mark.parametrize("page", [0, 2])
def test_a_missing_pdf_page_is_rejected(page):
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer)
    pdf.showPage()
    pdf.save()
    with pytest.raises(ValueError, match="no page"):
        prepare_image(buffer.getvalue(), page=page)


def test_a_zero_size_pdf_page_is_unreadable_not_a_crash():
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=(0, 0))
    pdf.showPage()
    pdf.save()
    with pytest.raises(ValueError, match="PDF file could not be read"):
        prepare_image(buffer.getvalue())
