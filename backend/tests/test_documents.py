import io

import pytest
from fastapi.testclient import TestClient

from input_handler.documents import (
    DocumentExtractError,
    DocumentVisionError,
    extract_requirements_text,
)
from tests.conftest import register_user


def _pdf_bytes(text: str) -> bytes:
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas

    buffer = io.BytesIO()
    page = canvas.Canvas(buffer, pagesize=letter)
    page.drawString(72, 720, text)
    page.save()
    return buffer.getvalue()


def _docx_bytes(text: str) -> bytes:
    from docx import Document

    document = Document()
    document.add_paragraph(text)
    buffer = io.BytesIO()
    document.save(buffer)
    return buffer.getvalue()


def test_extract_pdf_and_docx():
    pdf_text = extract_requirements_text("spec.pdf", _pdf_bytes("Members receive a 10% discount."))
    assert "Members receive" in pdf_text

    docx_text = extract_requirements_text(
        "spec.docx", _docx_bytes("Negative prices must be rejected.")
    )
    assert "Negative prices" in docx_text


def test_extract_plain_text_and_reject_unknown():
    text = extract_requirements_text("notes.txt", b"Empty carts should produce a total of 0.")
    assert "Empty carts" in text
    try:
        extract_requirements_text("spec.xlsx", b"not a document")
        raise AssertionError("expected failure")
    except DocumentExtractError:
        pass


def _png_bytes(width: int = 180, height: int = 100) -> bytes:
    from PIL import Image

    buffer = io.BytesIO()
    Image.new("RGB", (width, height), "white").save(buffer, format="PNG")
    return buffer.getvalue()


def _pdf_with_figure(text: str) -> bytes:
    import pymupdf as fitz

    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), text)
    page.insert_image(fitz.Rect(72, 120, 360, 280), stream=_png_bytes())
    raw = document.tobytes()
    document.close()
    return raw


def _scanned_pdf() -> bytes:
    import pymupdf as fitz

    document = fitz.open()
    page = document.new_page()
    page.insert_image(page.rect, stream=_png_bytes(400, 520))
    raw = document.tobytes()
    document.close()
    return raw


def _vector_flowchart_pdf() -> bytes:
    import pymupdf as fitz

    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), "Checkout")
    shape = page.new_shape()
    for top in range(120, 520, 40):
        shape.draw_rect(fitz.Rect(72, top, 240, top + 28))
        shape.draw_line(fitz.Point(156, top + 28), fitz.Point(156, top + 40))
    shape.finish(color=(0, 0, 0), width=1)
    shape.commit()
    raw = document.tobytes()
    document.close()
    return raw


def _many_page_pdf(page_count: int) -> bytes:
    import pymupdf

    document = pymupdf.open()
    for _ in range(page_count):
        document.new_page()
    raw = document.tobytes()
    document.close()
    return raw


def _many_visual_pages_pdf(page_count: int) -> bytes:
    import pymupdf

    document = pymupdf.open()
    for _ in range(page_count):
        page = document.new_page()
        shape = page.new_shape()
        for top in range(120, 240, 40):
            shape.draw_rect(pymupdf.Rect(72, top, 240, top + 28))
            shape.draw_line(
                pymupdf.Point(156, top + 28), pymupdf.Point(156, top + 40)
            )
        shape.finish(color=(0, 0, 0), width=1)
        shape.commit()
    raw = document.tobytes()
    document.close()
    return raw


def test_text_pdf_does_not_call_vision(monkeypatch):
    def _fail(*_args, **_kwargs):
        raise AssertionError("text PDF should not call the vision model")

    monkeypatch.setattr(
        "requirement_analysis.diagram_extractor.transcribe_visual_content", _fail
    )
    text = extract_requirements_text("spec.pdf", _pdf_bytes("Members receive a 10% discount."))
    assert "Members receive" in text


def test_pdf_figure_and_scan_use_vision(monkeypatch):
    seen: list[str] = []

    def _fake(image_bytes: bytes, mime_type: str) -> str:
        assert image_bytes
        assert mime_type.startswith("image/")
        seen.append(mime_type)
        return "If the member flag is set, then apply a 10 percent discount."

    monkeypatch.setattr(
        "requirement_analysis.diagram_extractor.transcribe_visual_content", _fake
    )

    prose = (
        "Members receive a 10% discount when the loyalty flag is set. "
        "Non-members pay the full listed price for every item in the cart."
    )
    mixed = extract_requirements_text("spec.pdf", _pdf_with_figure(prose))
    assert "Members receive" in mixed
    assert "member flag" in mixed

    scanned = extract_requirements_text("scan.pdf", _scanned_pdf())
    assert "member flag" in scanned

    flowchart = extract_requirements_text("flow.pdf", _vector_flowchart_pdf())
    assert "member flag" in flowchart
    assert seen


def test_word_upload_skips_vision(monkeypatch):
    def _fail(*_args, **_kwargs):
        raise AssertionError("Word extraction should stay on the text path")

    monkeypatch.setattr(
        "requirement_analysis.diagram_extractor.transcribe_visual_content", _fail
    )
    text = extract_requirements_text(
        "spec.docx", _docx_bytes("Negative prices must be rejected.")
    )
    assert "Negative prices" in text


def test_pdf_vision_failure_is_not_silently_ignored(monkeypatch):
    def _fail(*_args, **_kwargs):
        raise RuntimeError("vision endpoint unavailable")

    monkeypatch.setattr(
        "requirement_analysis.diagram_extractor.transcribe_visual_content", _fail
    )
    with pytest.raises(DocumentVisionError, match="visual content could not be analyzed"):
        extract_requirements_text(
            "spec.pdf",
            _pdf_with_figure("Members receive a discount when eligible."),
        )


def test_pdf_page_and_visual_limits_are_reported():
    from input_handler.pdf_visual import PdfVisualError, collect_pdf_visuals

    with pytest.raises(DocumentExtractError, match="more than 50 pages"):
        extract_requirements_text("large.pdf", _many_page_pdf(51))

    with pytest.raises(PdfVisualError, match="more than 4 visually complex pages"):
        collect_pdf_visuals(_many_visual_pages_pdf(5))


def test_extract_endpoint(client: TestClient):
    headers = register_user(client)
    res = client.post(
        "/api/requirements/extract",
        headers=headers,
        files={
            "requirements_file": (
                "spec.pdf",
                _pdf_bytes("Non-members pay the full price."),
                "application/pdf",
            )
        },
    )
    assert res.status_code == 200, res.text
    assert "Non-members pay" in res.json()["requirements_text"]


def test_pdf_visual_failure_is_reported_as_upstream_error(client, monkeypatch):
    def _fail(*_args, **_kwargs):
        raise DocumentVisionError("Vision service unavailable.")

    monkeypatch.setattr("app.extract_requirements_text", _fail)
    response = client.post(
        "/api/requirements/extract",
        headers=register_user(client),
        files={"requirements_file": ("flow.pdf", b"pdf", "application/pdf")},
    )

    assert response.status_code == 502
    assert response.json()["detail"] == "Vision service unavailable."


def test_diagram_vision_failure_is_reported_as_upstream_error(
    client, monkeypatch, caplog
):
    from requirement_analysis.diagram_extractor import DiagramExtractionError

    def _fail(*_args, **_kwargs):
        raise DiagramExtractionError("Vision service unavailable.")

    monkeypatch.setattr("app.extract_requirements_from_diagram", _fail)
    response = client.post(
        "/api/requirements/extract-diagram",
        files={"diagram_file": ("flow.png", b"image", "image/png")},
    )

    assert response.status_code == 502
    assert response.json()["detail"] == "Vision service unavailable."
    assert "Diagram requirements extraction failed: Vision service unavailable." in caplog.text


def test_reflow_joins_pdf_wrapped_single_words_and_preserves_bullets():
    from input_handler.documents import reflow_requirement_text

    messy = (
        "Requirements:-\n\n●\n\nReject\n\nnegative\n\nprices\n\nwith\n\nValueError.\n\n"
        "●\n\nNon-\nmembers\n\npay\n\na\n\n$5\n\ndelivery\n\nfee."
    )
    reflowed = reflow_requirement_text(messy)
    assert reflowed.splitlines() == [
        "Requirements:-",
        "• Reject negative prices with ValueError.",
        "• Non-members pay a $5 delivery fee.",
    ]

    inline_zwsp = (
        "1.\u200bReject negative prices with ValueError. "
        "2.\u200bMembers get 10% off. "
        "3.\u200bNon-members pay a $5 delivery fee."
    )
    assert reflow_requirement_text(inline_zwsp).splitlines() == [
        "1. Reject negative prices with ValueError.",
        "2. Members get 10% off.",
        "3. Non-members pay a $5 delivery fee.",
    ]

    # Verify a real multi-line PDF block preserves separate numbered lines instead of flattening them to 1 line.
    import pymupdf as fitz

    doc = fitz.open()
    page = doc.new_page()
    page.insert_text(
        (72, 72),
        "1. Reject negative prices with ValueError.\n"
        "2. Members get 10% off.\n"
        "3. Non-members pay a $5 delivery fee.",
    )
    pdf_raw = doc.tobytes()
    doc.close()
    extracted = extract_requirements_text("points.pdf", pdf_raw)
    assert len(extracted.splitlines()) == 3

    # Distinct requirement lines starting with lowercase snake_case function names must stay separate.
    fn_prefixed = (
        "calculate_electricity_bill must raise ValueError when units < 0.\n"
        "calculate_electricity_bill returns 550.0 when units == 100 and is_commercial is False.\n"
        "calculate_water_bill must raise ValueError when liters < 0.\n"
        "calculate_water_bill must raise ValueError when liters > 10000.\n"
    )
    assert len(reflow_requirement_text(fn_prefixed).splitlines()) == 4
