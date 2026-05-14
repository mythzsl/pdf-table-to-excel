from app.services.extractor import make_table, merge_continued_tables


def test_merges_continued_table_without_repeated_header():
    tables = [
        make_table(1, 1, [["Name", "Amount"], ["Alice", "42"]], 100, (10, 20, 90, 90)),
        make_table(2, 1, [["Bob", "19"], ["Carol", "33"]], 100, (10, 10, 90, 45)),
    ]

    merged = merge_continued_tables(tables)

    assert len(merged) == 1
    assert merged[0]["name"] == "Pages 1-2 Table 1"
    assert merged[0]["pages"] == [1, 2]
    assert merged[0]["rows"] == [["Name", "Amount"], ["Alice", "42"], ["Bob", "19"], ["Carol", "33"]]


def test_merges_continued_table_and_removes_repeated_header():
    tables = [
        make_table(1, 1, [["Name", "Amount"], ["Alice", "42"]], 100, (10, 20, 90, 90)),
        make_table(2, 1, [["Name", "Amount"], ["Bob", "19"]], 100, (10, 10, 90, 45)),
    ]

    merged = merge_continued_tables(tables)

    assert len(merged) == 1
    assert merged[0]["rows"] == [["Name", "Amount"], ["Alice", "42"], ["Bob", "19"]]


def test_does_not_merge_independent_tables_with_different_headers():
    tables = [
        make_table(1, 1, [["Name", "Amount"], ["Alice", "42"]], 100, (10, 20, 90, 90)),
        make_table(2, 1, [["Product", "Price"], ["Desk", "120"]], 100, (10, 10, 90, 45)),
    ]

    merged = merge_continued_tables(tables)

    assert len(merged) == 2
    assert merged[0]["pages"] == [1]
    assert merged[1]["pages"] == [2]


def test_merges_multiple_cross_page_tables_by_index():
    tables = [
        make_table(1, 1, [["Name", "Amount"], ["Alice", "42"]], 100, (10, 20, 90, 90)),
        make_table(1, 2, [["Item", "Qty"], ["Pen", "3"]], 100, (110, 20, 190, 90)),
        make_table(2, 1, [["Bob", "19"]], 100, (10, 10, 90, 45)),
        make_table(2, 2, [["Pencil", "5"]], 100, (110, 10, 190, 45)),
    ]

    merged = merge_continued_tables(tables)

    assert len(merged) == 2
    assert merged[0]["rows"] == [["Name", "Amount"], ["Alice", "42"], ["Bob", "19"]]
    assert merged[1]["rows"] == [["Item", "Qty"], ["Pen", "3"], ["Pencil", "5"]]
