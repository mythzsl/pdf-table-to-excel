from pathlib import Path
from tempfile import NamedTemporaryFile

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.rate_limit import InMemoryRateLimiter
from app.services.exporters import make_csv_base64, make_xlsx_base64
from app.services.extractor import ExtractionError, extract_tables_from_pdf

settings = get_settings()
rate_limiter = InMemoryRateLimiter(limit=settings.rate_limit_per_hour)

app = FastAPI(title=settings.app_name, version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origin_list,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict:
    return {"ok": True}


@app.post("/api/extract")
async def extract(request: Request, file: UploadFile = File(...)) -> dict:
    forwarded_for = request.headers.get("x-forwarded-for", "").split(",")[0].strip()
    client_ip = forwarded_for or (request.client.host if request.client else "unknown")
    if not rate_limiter.allow(client_ip):
        raise HTTPException(status_code=429, detail="Rate limit reached. Please try again later.")

    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Please upload a PDF file.")

    data = await file.read(settings.max_upload_bytes + 1)
    if len(data) > settings.max_upload_bytes:
        raise HTTPException(status_code=413, detail=f"PDFs are limited to {settings.max_upload_mb} MB.")

    temp_path: Path | None = None
    try:
        with NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
            temp_file.write(data)
            temp_path = Path(temp_file.name)

        tables, warnings = extract_tables_from_pdf(temp_path, settings.max_pages)
        filename_stem = safe_filename_stem(file.filename)

        return {
            "success": True,
            "tables": [
                {
                    "name": table["name"],
                    "page": table["page"],
                    "pages": table["pages"],
                    "index": table["index"],
                    "rowCount": table["row_count"],
                    "columnCount": table["column_count"],
                    "previewRows": table["rows"][:25],
                    "rows": table["rows"],
                }
                for table in tables
            ],
            "files": {
                "xlsx": {
                    "filename": f"{filename_stem}-tables.xlsx",
                    "mime": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    "base64": make_xlsx_base64(tables),
                },
                "csv": {
                    "filename": f"{filename_stem}-tables.csv",
                    "mime": "text/csv;charset=utf-8",
                    "base64": make_csv_base64(tables),
                },
            },
            "warnings": warnings,
        }
    except ExtractionError as exc:
        raise HTTPException(status_code=422, detail={"code": exc.code, "message": exc.message}) from exc
    finally:
        if temp_path and temp_path.exists():
            temp_path.unlink(missing_ok=True)


def safe_filename_stem(filename: str) -> str:
    stem = Path(filename).stem.lower()
    cleaned = "".join(character if character.isalnum() else "-" for character in stem)
    cleaned = "-".join(part for part in cleaned.split("-") if part)
    return cleaned[:60] or "pdf"
