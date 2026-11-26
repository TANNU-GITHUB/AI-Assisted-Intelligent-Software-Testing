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


class DocumentVisionError(DocumentExtractError):
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
        text = _with_pdf_visuals(raw, text)
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


def _with_pdf_visuals(raw: bytes, text: str) -> str:
    """Append flowchart, diagram, pseudocode, or scanned-page text from a PDF.

    Ordinary text extraction is unchanged when the PDF has no visual pages.
    A vision failure does not discard text that was already extracted.
    """
    from input_handler.pdf_visual import PdfVisualError, visual_text_from_pdf

    try:
        visual = visual_text_from_pdf(raw)
    except PdfVisualError as exc:
        detail = (
            "The PDF text was extracted, but its visual content could not be "
            f"analyzed: {exc}"
        )
        raise DocumentVisionError(detail) from exc
    visual = _normalize(visual)
    if not visual:
        return text
    if not text.strip():
        return visual
    return f"{text.rstrip()}\n\n{visual}"


def _suffix(filename: str) -> str:
    name = filename.replace("\\", "/").rsplit("/", 1)[-1].lower()
    if "." not in name:
        return ""
    return "." + name.rsplit(".", 1)[-1]


_STANDALONE_BULLET_RE = re.compile(
    r"^(?:[●•◦▪▫▸▹▻►◆◇★☆\-–—*]|(?:\d{1,3}|[a-zA-Z])[.)])$"
)
_BULLET_PREFIX_RE = re.compile(
    r"^(?:[●•◦▪▫▸▹▻►◆◇★☆\-–—*]\s+|(?:\d{1,3}[.)])\s+|REQ[-_]?\d+\s*[:.\-]\s*)",
    re.IGNORECASE,
)
_HEADER_LINE_RE = re.compile(
    r"^(?:pdf\s+page\s+\d+|(?:functional\s+|software\s+|system\s+|test\s+)?requirements?\s*[:-]*|flowchart\s*[:-]*|specifications?\s*[:-]*)$",
    re.IGNORECASE,
)
_DANGLING_END_WORDS = frozenset(
    {
        "a",
        "an",
        "the",
        "with",
        "of",
        "in",
        "on",
        "at",
        "by",
        "for",
        "from",
        "to",
        "into",
        "when",
        "if",
        "and",
        "or",
        "must",
        "should",
        "shall",
        "can",
        "will",
        "are",
        "is",
        "was",
        "pay",
        "pays",
        "get",
        "gets",
        "give",
        "gives",
        "apply",
        "applies",
        "raise",
        "raises",
        "return",
        "returns",
        "assign",
        "assigns",
        "set",
        "sets",
    }
)


_INLINE_LIST_SPLIT_RE = re.compile(
    r"(?<=[.!?;])\s+(?=(?:\d{1,3}[.)]|[●•◦▪▸▹▻►]|REQ[-_]?\d+\s*[:.\-])\s*[A-Za-z])"
    r"|\s+(?=(?:●|•|◦|▪|REQ[-_]?\d+\s*[:.\-])\s*[A-Za-z])",
    re.IGNORECASE,
)


def reflow_requirement_text(text: str) -> str:
    """Rejoin word-wrapped PDF/Word fragments into whole requirement lines while preserving bullets and sentences."""
    cleaned = (text or "").replace("\ufeff", "").replace("\x00", " ")
    # Replace zero-width spaces (common in Docs/PDF numbered lists like "1.\u200bReject") with a space.
    cleaned = re.sub(r"[\u200b\u200c\u200d]+", " ", cleaned)
    cleaned = cleaned.replace("\r\n", "\n").replace("\r", "\n")
    # Split inline numbered/bulleted items onto separate lines before reflowing fragments.
    cleaned = _INLINE_LIST_SPLIT_RE.sub("\n", cleaned)
    raw_lines = [re.sub(r"[ \t]{2,}", " ", line).strip() for line in cleaned.splitlines() if line.strip()]
    if not raw_lines:
        return ""

    merged: list[str] = []
    pending_bullet = False

    for line in raw_lines:
        if _STANDALONE_BULLET_RE.match(line):
            pending_bullet = True
            continue
        if pending_bullet:
            merged.append(f"• {line}")
            pending_bullet = False
            continue
        if line.startswith("#") or _HEADER_LINE_RE.match(line) or line.endswith(":-"):
            merged.append(line)
            continue
        if _BULLET_PREFIX_RE.match(line) or not merged:
            merged.append(line)
            continue

        prev = merged[-1]
        prev_body = _BULLET_PREFIX_RE.sub("", prev).strip()
        if (
            prev.startswith("#")
            or _HEADER_LINE_RE.match(prev_body)
            or prev_body.endswith((":-", ":"))
        ):
            merged.append(line)
            continue

        prev_ends_sentence = prev_body.endswith((".", "!", "?"))
        prev_last_word = prev_body.split()[-1].rstrip(",;").lower() if prev_body.split() else ""
        is_hyphen_wrap = prev.endswith("-") and line[:1].islower()
        starts_with_fn_ident = bool(re.match(r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)+\b", line))
        starts_continuation = line[0] in ",.;:)]}%" or (
            not prev_ends_sentence
            and (
                (line[0].islower() and not starts_with_fn_ident)
                or bool(re.match(r"^(?:\d+%|\$\d+|\d+\b)", line))
            )
        )
        short_fragment = not prev_ends_sentence and (
            (len(prev_body.split()) <= 2 and not starts_with_fn_ident)
            or (len(line.split()) <= 2 and not starts_with_fn_ident)
            or prev_last_word in _DANGLING_END_WORDS
        )

        if is_hyphen_wrap or starts_continuation or short_fragment:
            sep = "" if is_hyphen_wrap or line[0] in ",.;:)]}" else " "
            merged[-1] = f"{prev}{sep}{line}"
        else:
            merged.append(line)

    return "\n".join(merged)


def clean_requirement_lines(text: str) -> list[str]:
    """Return non-header, non-empty, bullet-stripped requirement lines after reflowing wrapped fragments."""
    reflowed = reflow_requirement_text(text)
    cleaned_lines: list[str] = []
    fallback_single_words: list[str] = []
    for raw in reflowed.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if _STANDALONE_BULLET_RE.match(line) or _HEADER_LINE_RE.match(line):
            continue
        body = _BULLET_PREFIX_RE.sub("", line).strip()
        if not body or _STANDALONE_BULLET_RE.match(body) or _HEADER_LINE_RE.match(body):
            continue
        words = body.split()
        # Drop short trailing-colon labels (e.g. "Requirements:", "Edge cases:") with no rule symbols
        if body.endswith((":", ":-")) and len(words) <= 4 and not re.search(r"[<>=0-9]", body):
            continue
        if len(words) < 2 and not re.search(r"[<>=]", body):
            fallback_single_words.append(body)
            continue
        if len(words) > 6 and re.search(r"[.!?]\s+[A-Za-z]", body):
            sub_sentences = [
                s.strip()
                for s in re.split(r"(?<=[.!?])\s+(?=[A-Za-z])", body)
                if s.strip() and len(s.split()) >= 2
            ]
            if len(sub_sentences) > 1:
                cleaned_lines.extend(sub_sentences)
                continue
        cleaned_lines.append(body)
    return cleaned_lines or fallback_single_words


def _normalize(text: str) -> str:
    text = reflow_requirement_text(text)
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
    from input_handler.pdf_visual import MAX_PDF_PAGES

    # Prefer PyMuPDF's layout-aware block extractor so narrow PDF columns don't emit one word per line.
    try:
        import pymupdf as fitz
    except ImportError:
        fitz = None

    if fitz is not None:
        try:
            document = fitz.open(stream=raw, filetype="pdf")
        except Exception:
            document = None
        if document is not None:
            try:
                if len(document) > MAX_PDF_PAGES:
                    raise DocumentExtractError(
                        f"PDF has more than {MAX_PDF_PAGES} pages. Split it into smaller files."
                    )
                if not document.is_encrypted or document.authenticate(""):
                    pages: list[str] = []
                    for page in document:
                        try:
                            blocks = page.get_text("blocks", sort=True)
                            if blocks:
                                block_texts = [
                                    str(b[4]).strip()
                                    for b in blocks
                                    if len(b) > 4 and str(b[4]).strip()
                                ]
                                pages.append("\n".join(block_texts))
                            else:
                                pages.append(page.get_text("text") or "")
                        except Exception:
                            continue
                    return "\n".join(pages)
            finally:
                document.close()

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

    if len(reader.pages) > MAX_PDF_PAGES:
        raise DocumentExtractError(
            f"PDF has more than {MAX_PDF_PAGES} pages. Split it into smaller files."
        )
    pages = []
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
