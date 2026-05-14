from pathlib import Path
from string import punctuation

from app.services.exporters import normalize_rows


class ExtractionError(Exception):
    def __init__(self, message: str, code: str = "extraction_failed") -> None:
        super().__init__(message)
        self.message = message
        self.code = code


def extract_tables_from_pdf(path: Path, max_pages: int) -> tuple[list[dict], list[str]]:
    try:
        import pdfplumber
    except ImportError as exc:
        raise ExtractionError("The PDF extraction engine is not installed on this server.", "engine_missing") from exc

    warnings: list[str] = []
    tables: list[dict] = []
    saw_text = False

    try:
        with pdfplumber.open(path) as pdf:
            if len(pdf.pages) > max_pages:
                raise ExtractionError(f"This PDF has {len(pdf.pages)} pages. The current limit is {max_pages} pages.", "too_many_pages")

            for page_number, page in enumerate(pdf.pages, start=1):
                text = (page.extract_text() or "").strip()
                saw_text = saw_text or bool(text)

                tables.extend(extract_page_tables(page, page_number))
    except ExtractionError:
        raise
    except Exception as exc:
        message = str(exc).lower()
        if "password" in message or "encrypted" in message:
            raise ExtractionError("This PDF appears to be password-protected. Please unlock it before uploading.", "encrypted_pdf") from exc
        raise ExtractionError("We could not read this PDF. Please try a text-based, unlocked PDF file.", "invalid_pdf") from exc

    if not tables and not saw_text:
        raise ExtractionError(
            "No selectable text was found. This looks like an image-based or scanned PDF. These files need OCR, which will be supported later.",
            "scanned_pdf",
        )

    if not tables:
        raise ExtractionError("No tables were detected in this PDF. Try a document with clearer table columns or borders.", "no_tables")

    tables = merge_continued_tables(tables)

    if len(tables) > 20:
        warnings.append("Only the first 20 detected tables are included to keep the download manageable.")
        tables = tables[:20]

    return tables, warnings


def extract_page_tables(page: object, page_number: int) -> list[dict]:
    page_height = float(getattr(page, "height", 0) or 0)
    found_tables = []

    try:
        found_tables = list(page.find_tables() or [])
    except Exception:
        found_tables = []

    if found_tables:
        tables = []
        for table_index, table in enumerate(found_tables, start=1):
            rows = normalize_rows(table.extract() or [])
            if rows:
                tables.append(make_table(page_number, table_index, rows, page_height, getattr(table, "bbox", None)))
        return tables

    return [
        make_table(page_number, table_index, rows, page_height, None)
        for table_index, raw_rows in enumerate(page.extract_tables() or [], start=1)
        if (rows := normalize_rows(raw_rows))
    ]


def make_table(page_number: int, table_index: int, rows: list[list[str]], page_height: float, bbox: tuple | None) -> dict:
    top = float(bbox[1]) if bbox else None
    bottom = float(bbox[3]) if bbox else None
    column_count = max((len(row) for row in rows), default=0)

    return {
        "name": f"Page {page_number} Table {table_index}",
        "page": page_number,
        "pages": [page_number],
        "index": table_index,
        "source_indexes": [table_index],
        "rows": rows,
        "row_count": len(rows),
        "column_count": column_count,
        "header": row_signature(rows[0] if rows else []),
        "top": top,
        "bottom": bottom,
        "page_height": page_height,
    }


def merge_continued_tables(tables: list[dict]) -> list[dict]:
    if not tables:
        return []

    ordered = sorted(tables, key=lambda table: (table["page"], table["index"]))
    merged: list[dict] = []
    consumed: set[int] = set()

    for start_position, table in enumerate(ordered):
        if start_position in consumed:
            continue

        current = copy_table(table)
        consumed.add(start_position)

        while True:
            next_position = find_next_page_candidate(ordered, consumed, current)
            if next_position is None:
                break

            candidate = copy_table(ordered[next_position])
            if not should_merge_tables(current, candidate):
                break

            append_rows = continuation_rows(current, candidate)
            current["rows"].extend(append_rows)
            current["pages"] = sorted(set(current["pages"] + candidate["pages"]))
            current["source_indexes"].extend(candidate["source_indexes"])
            current["row_count"] = len(current["rows"])
            current["bottom"] = candidate["bottom"]
            current["page_height"] = candidate["page_height"]
            current["name"] = merged_table_name(current)
            consumed.add(next_position)

        merged.append(finalize_table(current))

    return merged


def find_next_page_candidate(tables: list[dict], consumed: set[int], current: dict) -> int | None:
    next_page = current["pages"][-1] + 1
    for position, table in enumerate(tables):
        if position in consumed:
            continue
        if table["page"] == next_page and table["index"] == current["index"]:
            return position
    return None


def should_merge_tables(previous: dict, next_table: dict) -> bool:
    if next_table["page"] != previous["pages"][-1] + 1:
        return False
    if previous["column_count"] != next_table["column_count"] or previous["column_count"] == 0:
        return False
    if previous["index"] != next_table["index"]:
        return False

    same_header = rows_have_same_header(previous, next_table)
    if same_header:
        return has_continuation_position(previous, next_table) or not has_position_data(previous, next_table)

    if row_looks_like_header(next_table["rows"][0] if next_table["rows"] else []):
        return False

    return has_continuation_position(previous, next_table)


def continuation_rows(previous: dict, next_table: dict) -> list[list[str]]:
    if rows_have_same_header(previous, next_table):
        return next_table["rows"][1:]
    return next_table["rows"]


def rows_have_same_header(previous: dict, next_table: dict) -> bool:
    return bool(previous["header"]) and previous["header"] == next_table["header"]


def has_position_data(previous: dict, next_table: dict) -> bool:
    return previous.get("bottom") is not None and next_table.get("top") is not None and previous.get("page_height") and next_table.get("page_height")


def has_continuation_position(previous: dict, next_table: dict) -> bool:
    if not has_position_data(previous, next_table):
        return False

    previous_height = float(previous["page_height"])
    next_height = float(next_table["page_height"])
    previous_reaches_lower_page = float(previous["bottom"]) >= previous_height * 0.62
    next_starts_upper_page = float(next_table["top"]) <= next_height * 0.38
    return previous_reaches_lower_page and next_starts_upper_page


def row_signature(row: list[str]) -> tuple[str, ...]:
    return tuple(normalize_header_cell(cell) for cell in row)


def normalize_header_cell(cell: str) -> str:
    normalized = " ".join(str(cell or "").lower().split())
    return normalized.strip(punctuation + " ")


def row_looks_like_header(row: list[str]) -> bool:
    cells = [str(cell or "").strip() for cell in row if str(cell or "").strip()]
    if not cells:
        return False

    alpha_cells = sum(any(character.isalpha() for character in cell) for cell in cells)
    numeric_cells = sum(cell.replace(",", "").replace(".", "").replace("-", "").isdigit() for cell in cells)
    return alpha_cells > 0 and numeric_cells == 0


def merged_table_name(table: dict) -> str:
    pages = table["pages"]
    if len(pages) == 1:
        return f"Page {pages[0]} Table {table['index']}"
    return f"Pages {pages[0]}-{pages[-1]} Table {table['index']}"


def finalize_table(table: dict) -> dict:
    table["name"] = merged_table_name(table)
    table["page"] = table["pages"][0]
    table["row_count"] = len(table["rows"])
    table["column_count"] = max((len(row) for row in table["rows"]), default=0)
    for internal_key in ["header", "source_indexes", "top", "bottom", "page_height"]:
        table.pop(internal_key, None)
    return table


def copy_table(table: dict) -> dict:
    copied = dict(table)
    copied["pages"] = list(table["pages"])
    copied["source_indexes"] = list(table["source_indexes"])
    copied["rows"] = [list(row) for row in table["rows"]]
    return copied
