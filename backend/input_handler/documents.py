"""Extract plain-text requirements from PDF and Word uploads."""

from __future__ import annotations

import io
import re
import zipfile
from xml.etree import ElementTree

MAX_REQUIREMENT_FILE_BYTES = 8 * 1024 * 1024
MAX_EXTRACTED_CHARS = 50_000
ALLOWED_EXTENSIONS = {".pdf", ".doc", ".docx", ".txt", ".md"}


class DocumentExtractError(ValueError):
    pass


def extract_requirements_text(filename: str, raw: bytes) -> str:
    if not filename:
        raise DocumentExtractError("Upload a named PDF or Word document.")
    if not raw:
        raise DocumentExtractError("The uploaded requirements file is empty.")
    if len(raw) > MAX_REQUIREMENT_FILE_BYTES:
        raise DocumentExtractError("Requirements file is too large (max 8 MB).")

    suffix = _suffix(filename)
    if suffix not in ALLOWED_EXTENSIONS:
        raise DocumentExtractError("Use a PDF, Word (.doc / .docx), or text file.")

    if suffix == ".pdf":
        text = _from_pdf(raw)
    elif suffix == ".docx":
        text = _from_docx(raw)
    elif suffix == ".doc":
        text = _from_doc(raw)
    else:
        text = _from_plain(raw)

    cleaned = _normalize(text)
    if not cleaned:
        raise DocumentExtractError(
            "No readable text was found in that file. Export as PDF or .docx and try again."
        )
    if len(cleaned) > MAX_EXTRACTED_CHARS:
        cleaned = cleaned[:MAX_EXTRACTED_CHARS] + "\n\n# …truncated…"
    return cleaned


def _suffix(filename: str) -> str:
    name = filename.replace("\\", "/").rsplit("/", 1)[-1].lower()
    if "." not in name:
        return ""
    return "." + name.rsplit(".", 1)[-1]


def _normalize(text: str) -> str:
    text = text.replace("\x00", " ")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _from_plain(raw: bytes) -> str:
    for encoding in ("utf-8", "utf-16", "latin-1"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def _from_pdf(raw: bytes) -> str:
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise DocumentExtractError(
            "PDF support is not installed. Run: pip install pypdf"
        ) from exc
    try:
        reader = PdfReader(io.BytesIO(raw))
    except Exception as exc:  # noqa: BLE001
        raise DocumentExtractError("Could not read that PDF.") from exc
    pages: list[str] = []
    for page in reader.pages:
        try:
            pages.append(page.extract_text() or "")
        except Exception:
            continue
    return "\n".join(pages)


def _from_docx(raw: bytes) -> str:
    try:
        from docx import Document
    except ImportError as exc:
        raise DocumentExtractError(
            "Word support is not installed. Run: pip install python-docx"
        ) from exc
    try:
        document = Document(io.BytesIO(raw))
    except Exception as exc:  # noqa: BLE001
        raise DocumentExtractError("Could not read that Word document.") from exc
    parts: list[str] = []
    for paragraph in document.paragraphs:
        if paragraph.text.strip():
            parts.append(paragraph.text)
    for table in document.tables:
        for row in table.rows:
            cells = [cell.text.strip() for cell in row.cells if cell.text.strip()]
            if cells:
                parts.append(" | ".join(cells))
    return "\n".join(parts)


def _from_doc(raw: bytes) -> str:
    if raw[:2] == b"PK":
        try:
            return _from_docx(raw)
        except DocumentExtractError:
            return _from_docx_xml(raw)
    text = _ole_word_text(raw)
    if text.strip():
        return text
    raise DocumentExtractError(
        "Could not read that .doc file. Save it as .docx or PDF and upload again."
    )


def _from_docx_xml(raw: bytes) -> str:
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            xml = archive.read("word/document.xml")
    except Exception as exc:  # noqa: BLE001
        raise DocumentExtractError("Could not read that Word document.") from exc
    tree = ElementTree.fromstring(xml)
    texts = [
        node.text
        for node in tree.iter()
        if node.tag.endswith("}t") and node.text
    ]
    return "\n".join(texts)


def _ole_word_text(raw: bytes) -> str:
    try:
        import olefile
    except ImportError:
        olefile = None
    if olefile is not None:
        try:
            ole = olefile.OleFileIO(io.BytesIO(raw))
            if ole.exists("WordDocument"):
                stream = ole.openstream("WordDocument").read()
            else:
                stream = raw
            ole.close()
        except Exception:
            stream = raw
    else:
        stream = raw
    utf16 = _extract_utf16_strings(stream)
    if len(utf16) > 40:
        return utf16
    ascii_text = re.sub(r"[^\x09\x0a\x0d\x20-\x7e]+", "\n", stream.decode("latin-1", errors="ignore"))
    ascii_text = re.sub(r"\n{2,}", "\n", ascii_text)
    return ascii_text


def _extract_utf16_strings(data: bytes) -> str:
    chunks: list[str] = []
    current = bytearray()
    i = 0
    while i + 1 < len(data):
        code = int.from_bytes(data[i : i + 2], "little")
        if 32 <= code <= 126 or code in {9, 10, 13}:
            current.extend(data[i : i + 2])
            i += 2
            continue
        if len(current) >= 16:
            chunks.append(current.decode("utf-16le", errors="ignore"))
        current = bytearray()
        i += 2
    if len(current) >= 16:
        chunks.append(current.decode("utf-16le", errors="ignore"))
    joined = "\n".join(chunk.strip() for chunk in chunks if chunk.strip())
    return re.sub(r"\n{3,}", "\n\n", joined)
