import pymupdf

from pdf_parser import parse_pdf


def test_parses_searchable_pdf_with_line_metadata():
    document = pymupdf.open()
    page = document.new_page()
    page.insert_text((72, 72), "Technical Skills")
    page.insert_text((72, 92), "Python, PyTorch, OpenCV")
    content = document.tobytes()
    document.close()

    parsed = parse_pdf("resume.pdf", content)

    assert parsed["extraction_method"] == "text_layer"
    assert "Technical Skills" in parsed["text"]
    assert parsed["pages"][0]["lines"][0]["font_size"] > 0
