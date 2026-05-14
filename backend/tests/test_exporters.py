import base64
import csv
from io import BytesIO, StringIO

from openpyxl import load_workbook

from app.services.exporters import make_csv_base64, make_xlsx_base64, normalize_rows


def test_normalize_rows_pads_and_removes_empty_rows():
    rows = normalize_rows([[" Name ", None, "Amount"], [" Alice\nLee ", " ", " 42 "], ["", "", ""]])

    assert rows == [["Name", "", "Amount"], ["Alice Lee", "", "42"]]


def test_make_xlsx_base64_creates_workbook():
    payload = make_xlsx_base64([{"name": "Page 1 Table 1", "rows": [["Name", "Amount"], ["Alice", "42"]]}])
    workbook = load_workbook(BytesIO(base64.b64decode(payload)))

    sheet = workbook["Page 1 Table 1"]
    assert sheet["A1"].value == "Name"
    assert sheet["B2"].value == "42"


def test_make_csv_base64_includes_table_title_and_rows():
    payload = make_csv_base64([{"name": "Page 1 Table 1", "rows": [["Name", "Amount"], ["Alice", "42"]]}])
    decoded = base64.b64decode(payload).decode("utf-8-sig")
    rows = list(csv.reader(StringIO(decoded)))

    assert rows[0] == ["Page 1 Table 1"]
    assert rows[1] == ["Name", "Amount"]
    assert rows[2] == ["Alice", "42"]

