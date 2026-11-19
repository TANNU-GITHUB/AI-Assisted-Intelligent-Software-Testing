import io

from fastapi.testclient import TestClient

from input_handler.documents import DocumentExtractError, extract_requirements_text
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
