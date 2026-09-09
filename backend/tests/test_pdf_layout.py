from pdf_parser import merge_table_blocks, order_page_blocks


def _block(x0: float, y0: float, x1: float, text: str) -> dict:
    return {
        "bbox": (x0, y0, x1, y0 + 20),
        "text": text,
        "lines": [],
    }


def test_orders_two_column_blocks_column_by_column():
    blocks = [
        _block(320, 40, 560, "right one"),
        _block(40, 80, 280, "left two"),
        _block(320, 80, 560, "right two"),
        _block(40, 40, 280, "left one"),
    ]

    ordered = order_page_blocks(blocks, page_width=600)

    assert [block["text"] for block in ordered] == [
        "left one",
        "left two",
        "right one",
        "right two",
    ]


def test_keeps_full_width_heading_between_column_bands():
    blocks = [
        _block(40, 20, 560, "summary heading"),
        _block(40, 50, 280, "left summary"),
        _block(320, 50, 560, "right summary"),
        _block(40, 100, 560, "experience heading"),
        _block(40, 130, 280, "left experience"),
        _block(320, 130, 560, "right experience"),
    ]

    ordered = order_page_blocks(blocks, page_width=600)

    assert [block["text"] for block in ordered] == [
        "summary heading",
        "left summary",
        "right summary",
        "experience heading",
        "left experience",
        "right experience",
    ]


def test_replaces_overlapping_text_with_structured_table_rows():
    ordinary = [_block(40, 40, 280, "duplicated cell text")]
    table = [_block(30, 30, 290, "Skill | Evidence")]

    merged = merge_table_blocks(ordinary, table)

    assert [block["text"] for block in merged] == ["Skill | Evidence"]
