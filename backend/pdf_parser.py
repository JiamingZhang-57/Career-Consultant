import pymupdf


MAX_PDF_SIZE = 10 * 1024 * 1024


class PdfParsingError(Exception):
    def __init__(
        self,
        message: str,
        status_code: int = 400,
    ):
        super().__init__(message)
        self.status_code = status_code


def parse_pdf(
    filename: str,
    file_content: bytes,
) -> dict:
    if not filename.lower().endswith(".pdf"):
        raise PdfParsingError(
            "Only PDF files are supported."
        )

    if len(file_content) > MAX_PDF_SIZE:
        raise PdfParsingError(
            "File is too large. Maximum size is 10 MB.",
            status_code=413,
        )

    if not file_content.startswith(b"%PDF"):
        raise PdfParsingError(
            "The uploaded file does not appear to be a valid PDF."
        )

    try:
        with pymupdf.open(
            stream=file_content,
            filetype="pdf",
        ) as document:
            pages = [
                {
                    "page_number": page_index + 1,
                    "text": document[page_index]
                    .get_text("text")
                    .strip(),
                }
                for page_index in range(document.page_count)
            ]

            page_count = document.page_count

    except Exception as error:
        raise PdfParsingError(
            f"Could not parse PDF: {error}"
        ) from error

    full_text = "\n\n".join(
        page["text"]
        for page in pages
        if page["text"]
    )

    if not full_text:
        raise PdfParsingError(
            "No selectable text was found. "
            "Scanned PDFs are not currently supported.",
            status_code=422,
        )

    return {
        "filename": filename,
        "page_count": page_count,
        "character_count": len(full_text),
        "text": full_text,
        "pages": pages,
    }