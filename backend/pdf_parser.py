import re

import pymupdf


MAX_PDF_SIZE = 10 * 1024 * 1024
MIN_TEXT_CHARACTERS_PER_PAGE = 25


class PdfParsingError(Exception):
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.status_code = status_code


def _block_text(block: dict) -> str:
    lines = []
    for line in block.get("lines", []):
        text = "".join(
            str(span.get("text") or "")
            for span in line.get("spans", [])
        ).strip()
        if text:
            lines.append(text)
    return "\n".join(lines)


def _extract_blocks(page, text_page=None) -> list[dict]:
    raw = page.get_text("dict", textpage=text_page, sort=False)
    blocks = []

    for block in raw.get("blocks", []):
        if block.get("type") != 0:
            continue
        text = _block_text(block)
        if not text:
            continue

        styled_lines = []
        for line in block.get("lines", []):
            spans = line.get("spans", [])
            line_text = "".join(
                str(span.get("text") or "") for span in spans
            ).strip()
            if not line_text:
                continue
            max_size = max(
                (float(span.get("size") or 0) for span in spans),
                default=0,
            )
            bold = any(
                "bold" in str(span.get("font") or "").lower()
                for span in spans
            )
            styled_lines.append(
                {
                    "text": line_text,
                    "font_size": round(max_size, 2),
                    "bold": bold,
                }
            )

        blocks.append(
            {
                "bbox": tuple(float(value) for value in block["bbox"]),
                "text": text,
                "lines": styled_lines,
            }
        )
    return blocks


def _overlap_ratio(first: tuple, second: tuple) -> float:
    x0 = max(first[0], second[0])
    y0 = max(first[1], second[1])
    x1 = min(first[2], second[2])
    y1 = min(first[3], second[3])
    intersection = max(0.0, x1 - x0) * max(0.0, y1 - y0)
    first_area = max(1.0, (first[2] - first[0]) * (first[3] - first[1]))
    return intersection / first_area


def _extract_table_blocks(page) -> list[dict]:
    table_blocks = []

    try:
        tables = page.find_tables().tables
    except Exception:
        return []

    for table in tables:
        rows = []
        for row in table.extract():
            cells = [
                re.sub(r"\s+", " ", str(cell or "")).strip()
                for cell in row
            ]
            if any(cells):
                rows.append(" | ".join(cells))

        if not rows:
            continue

        table_blocks.append(
            {
                "bbox": tuple(float(value) for value in table.bbox),
                "text": "\n".join(rows),
                "lines": [
                    {"text": row, "font_size": 0, "bold": False}
                    for row in rows
                ],
            }
        )

    return table_blocks


def merge_table_blocks(
    text_blocks: list[dict],
    table_blocks: list[dict],
) -> list[dict]:
    if not table_blocks:
        return text_blocks

    outside_tables = [
        block
        for block in text_blocks
        if not any(
            _overlap_ratio(block["bbox"], table["bbox"]) >= 0.5
            for table in table_blocks
        )
    ]
    return outside_tables + table_blocks


def order_page_blocks(
    blocks: list[dict],
    page_width: float,
) -> list[dict]:
    """Return reading order for ordinary and two-column resumes."""
    if not blocks:
        return []

    narrow_blocks = [
        block
        for block in blocks
        if block["bbox"][2] - block["bbox"][0] < page_width * 0.7
    ]
    left_count = sum(
        (block["bbox"][0] + block["bbox"][2]) / 2
        < page_width * 0.47
        for block in narrow_blocks
    )
    right_count = sum(
        (block["bbox"][0] + block["bbox"][2]) / 2
        > page_width * 0.53
        for block in narrow_blocks
    )

    if left_count < 2 or right_count < 2:
        return sorted(
            blocks,
            key=lambda block: (block["bbox"][1], block["bbox"][0]),
        )

    full_width = sorted(
        (
            block
            for block in blocks
            if block["bbox"][2] - block["bbox"][0]
            >= page_width * 0.7
        ),
        key=lambda block: block["bbox"][1],
    )
    remaining = [block for block in blocks if block not in full_width]
    ordered = []

    def order_column_band(band: list[dict]) -> list[dict]:
        left = []
        right = []
        for block in band:
            x0, _, x1, _ = block["bbox"]
            target = left if (x0 + x1) / 2 < page_width / 2 else right
            target.append(block)
        return sorted(left, key=lambda block: block["bbox"][1]) + sorted(
            right,
            key=lambda block: block["bbox"][1],
        )

    # Full-width headings split the page into vertical bands. Within each
    # band, finish the left column before starting the right column.
    for anchor in full_width:
        before_anchor = [
            block
            for block in remaining
            if block["bbox"][1] < anchor["bbox"][1]
        ]
        ordered.extend(order_column_band(before_anchor))
        ordered.append(anchor)
        remaining = [
            block for block in remaining if block not in before_anchor
        ]

    ordered.extend(order_column_band(remaining))
    return ordered


def _page_payload(page, page_number: int) -> tuple[dict, list[str]]:
    warnings: list[str] = []
    extraction_method = "text_layer"
    blocks = _extract_blocks(page)
    blocks = merge_table_blocks(blocks, _extract_table_blocks(page))
    text = "\n".join(block["text"] for block in blocks)

    if len(re.sub(r"\s+", "", text)) < MIN_TEXT_CHARACTERS_PER_PAGE:
        try:
            text_page = page.get_textpage_ocr(
                language="eng",
                dpi=200,
                full=True,
            )
            blocks = _extract_blocks(page, text_page=text_page)
            blocks = merge_table_blocks(blocks, _extract_table_blocks(page))
            extraction_method = "ocr"
            warnings.append(
                f"Page {page_number} used OCR because its text layer was empty."
            )
        except Exception as error:
            warnings.append(
                f"Page {page_number} appears scanned, but OCR was unavailable: "
                f"{error}"
            )

    ordered_blocks = order_page_blocks(blocks, float(page.rect.width))
    lines = [
        line for block in ordered_blocks for line in block["lines"]
    ]
    page_text = "\n".join(line["text"] for line in lines).strip()
    return (
        {
            "page_number": page_number,
            "text": page_text,
            "lines": lines,
            "extraction_method": extraction_method,
        },
        warnings,
    )


def parse_pdf(filename: str, file_content: bytes) -> dict:
    if not filename.lower().endswith(".pdf"):
        raise PdfParsingError("Only PDF files are supported.")
    if len(file_content) > MAX_PDF_SIZE:
        raise PdfParsingError(
            "File is too large. Maximum size is 10 MB.", status_code=413
        )
    if not file_content.startswith(b"%PDF"):
        raise PdfParsingError(
            "The uploaded file does not appear to be a valid PDF."
        )

    try:
        with pymupdf.open(stream=file_content, filetype="pdf") as document:
            pages = []
            warnings = []
            for page_index in range(document.page_count):
                page, page_warnings = _page_payload(
                    document[page_index], page_index + 1
                )
                pages.append(page)
                warnings.extend(page_warnings)
            page_count = document.page_count
    except Exception as error:
        raise PdfParsingError(f"Could not parse PDF: {error}") from error

    full_text = "\n\n".join(
        page["text"] for page in pages if page["text"]
    )
    if not full_text:
        raise PdfParsingError(
            "No resume text could be extracted. For a scanned PDF, "
            "install Tesseract OCR or upload a searchable PDF.",
            status_code=422,
        )

    ocr_pages = [
        page["page_number"]
        for page in pages
        if page["extraction_method"] == "ocr"
    ]
    if ocr_pages and len(ocr_pages) < page_count:
        extraction_method = "mixed_text_and_ocr"
    elif ocr_pages:
        extraction_method = "ocr"
    else:
        extraction_method = "text_layer"

    return {
        "filename": filename,
        "page_count": page_count,
        "character_count": len(full_text),
        "text": full_text,
        "pages": pages,
        "extraction_method": extraction_method,
        "ocr_page_numbers": ocr_pages,
        "extraction_warnings": warnings,
    }
