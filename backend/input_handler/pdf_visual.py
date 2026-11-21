"""Find flowchart, diagram, pseudocode, and scanned pages inside a PDF."""

from __future__ import annotations

import io

# Pages with at least this much extracted text stay on the text path unless
# they also contain a real figure or a lot of vector drawing (a flowchart).
_TEXT_RICH_CHARS = 80
_DRAWING_HEAVY = 6
_MIN_FIGURE_PT = 48
_FULL_PAGE_COVERAGE = 0.85
_MAX_VISUALS = 4
MAX_PDF_PAGES = 50


class PdfVisualError(ValueError):
    """Raised when a PDF has no usable text and its visuals cannot be read."""


def visual_text_from_pdf(raw: bytes) -> str:
    """Transcribe visual PDF content. Returns '' when there is nothing to send."""
    from requirement_analysis.diagram_extractor import transcribe_visual_content

    images = collect_pdf_visuals(raw)
    if not images:
        return ""

    chunks: list[str] = []
    failures: list[str] = []
    for label, image_bytes, mime_type in images:
        try:
            text = transcribe_visual_content(image_bytes, mime_type).strip()
        except Exception as exc:  # noqa: BLE001 — collect page failures for the user
            failures.append(f"{label}: {str(exc)[:300]}")
            continue
        if text:
            chunks.append(f"{label}\n{text}")
        else:
            failures.append(f"{label}: the vision model returned no text.")

    if failures:
        raise PdfVisualError(
            "Could not analyze all visual PDF content: "
            + "; ".join(failures[:3])
        )
    if chunks:
        return "\n\n".join(chunks)
    return ""


def collect_pdf_visuals(raw: bytes) -> list[tuple[str, bytes, str]]:
    """Return (label, image_bytes, mime) for pages or figures worth a vision call.

    Text-only pages are skipped. A text page keeps an embedded figure when it
    does not cover the whole page. A scanned or drawing-heavy page is rendered
    once so arrows and pseudocode are not lost.
    """
    try:
        import pymupdf as fitz
    except ImportError:
        return _collect_with_pypdf(raw)

    try:
        document = fitz.open(stream=raw, filetype="pdf")
    except Exception:
        return _collect_with_pypdf(raw)
    if len(document) > MAX_PDF_PAGES:
        document.close()
        raise PdfVisualError(
            f"PDF has more than {MAX_PDF_PAGES} pages. Split it into smaller files."
        )
    if document.is_encrypted and not document.authenticate(""):
        document.close()
        return []

    selected: list[tuple[str, bytes, str]] = []
    seen_xrefs: set[int] = set()
    try:
        for index, page in enumerate(document, start=1):
            text = (page.get_text("text") or "").strip()
            text_rich = len(text) >= _TEXT_RICH_CHARS
            drawing_score = _drawing_score(page)
            drawing_heavy = drawing_score >= _DRAWING_HEAVY
            figures = _page_figures(document, page, seen_xrefs)
            full_page_figure = any(
                coverage >= _FULL_PAGE_COVERAGE
                for _xref, _image, _mime, coverage in figures
            )

            # Short written requirements stay on the text path. Render when the
            # page is a scan, contains a full-page image, or has vector drawing.
            if (
                drawing_heavy
                or full_page_figure
                or (not text_rich and figures)
                or (not text_rich and drawing_score > 0)
            ):
                if len(selected) >= _MAX_VISUALS:
                    raise PdfVisualError(
                        f"PDF contains more than {_MAX_VISUALS} visually complex pages. "
                        "Split the PDF and upload the relevant pages separately."
                    )
                try:
                    rendered = _render_page(page)
                except Exception as exc:
                    raise PdfVisualError(
                        f"Could not render visual content on PDF page {index}."
                    ) from exc
                selected.append((f"PDF page {index}", rendered, "image/png"))
                continue
            if not text_rich:
                continue

            for xref, image_bytes, mime_type, coverage in figures:
                if xref in seen_xrefs or coverage >= _FULL_PAGE_COVERAGE:
                    continue
                if len(selected) >= _MAX_VISUALS:
                    raise PdfVisualError(
                        f"PDF contains more than {_MAX_VISUALS} visual elements. "
                        "Split the PDF and upload the relevant pages separately."
                    )
                seen_xrefs.add(xref)
                selected.append((f"PDF page {index} figure", image_bytes, mime_type))
    finally:
        document.close()
    return selected


def _drawing_score(page) -> int:
    try:
        drawings = page.get_drawings()
    except Exception:
        return 0
    score = 0
    for drawing in drawings:
        items = drawing.get("items") if isinstance(drawing, dict) else None
        score += len(items) if items else 1
    return score


def _page_figures(document, page, seen_xrefs: set[int]):
    figures = []
    page_area = max(page.rect.width * page.rect.height, 1)
    try:
        info_list = page.get_image_info(xrefs=True)
    except Exception:
        info_list = []
    for info in info_list:
        xref = int(info.get("xref") or 0)
        if xref <= 0 or xref in seen_xrefs:
            continue
        bbox = info.get("bbox") or (0, 0, 0, 0)
        width = abs(bbox[2] - bbox[0])
        height = abs(bbox[3] - bbox[1])
        if width < _MIN_FIGURE_PT or height < _MIN_FIGURE_PT:
            continue
        coverage = (width * height) / page_area
        try:
            extracted = document.extract_image(xref)
        except Exception:
            continue
        image_bytes = extracted.get("image") or b""
        if not image_bytes:
            continue
        ext = str(extracted.get("ext") or "png").lower()
        mime = {
            "png": "image/png",
            "jpg": "image/jpeg",
            "jpeg": "image/jpeg",
            "webp": "image/webp",
            "gif": "image/gif",
        }.get(ext, "image/png")
        figures.append((xref, image_bytes, mime, coverage))
    return figures


def _render_page(page) -> bytes:
    import pymupdf as fitz

    max_edge = max(page.rect.width, page.rect.height)
    scale = min(1.5, 1536 / max_edge) if max_edge > 0 else 1.0
    pixmap = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
    return pixmap.tobytes("png")


def _collect_with_pypdf(raw: bytes) -> list[tuple[str, bytes, str]]:
    """Fallback when PyMuPDF is not installed: embedded raster images only."""
    try:
        from pypdf import PdfReader
    except ImportError:
        return []
    try:
        reader = PdfReader(io.BytesIO(raw))
    except Exception:
        return []
    if len(reader.pages) > MAX_PDF_PAGES:
        raise PdfVisualError(
            f"PDF has more than {MAX_PDF_PAGES} pages. Split it into smaller files."
        )
    selected: list[tuple[str, bytes, str]] = []
    for index, page in enumerate(reader.pages, start=1):
        images = getattr(page, "images", None)
        if not images:
            continue
        for image in images:
            data = getattr(image, "data", b"") or b""
            if len(data) < 2048:
                continue
            if len(selected) >= _MAX_VISUALS:
                raise PdfVisualError(
                    f"PDF contains more than {_MAX_VISUALS} embedded visual elements. "
                    "Split the PDF and upload the relevant pages separately."
                )
            name = str(getattr(image, "name", "") or "").lower()
            if name.endswith((".jpg", ".jpeg")):
                mime = "image/jpeg"
            elif name.endswith(".webp"):
                mime = "image/webp"
            elif name.endswith(".gif"):
                mime = "image/gif"
            else:
                mime = "image/png"
            selected.append((f"PDF page {index} figure", data, mime))
    return selected
