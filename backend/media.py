"""Image and document checks, seed files, and upload paths."""

from __future__ import annotations

import math
import re
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

from config import upload_dir

BACKEND_DIR = Path(__file__).resolve().parent
REPO_ROOT = BACKEND_DIR.parent
UPLOAD_DIR = upload_dir()
_UPLOAD_LOGICAL = "backend/uploads/"
MAX_IMAGE_BYTES = 8 * 1024 * 1024

RECOG_SLOTS: tuple[str, ...] = ("recog.0", "recog.1", "recog.2", "recog.3")
SLOTS: tuple[str, ...] = (
    "logo",
    "carousel.1",
    "carousel.2",
    "carousel.3",
    "carousel.4",
    *RECOG_SLOTS,
)
SLOT_SET = frozenset(SLOTS)

# path, original name, content type, slot
SEED_IMAGES: tuple[tuple[str, str, str, str], ...] = (
    ("images/kofc-logo.png", "kofc-logo.png", "image/png", "logo"),
    ("images/carousel1.jpg", "carousel1.jpg", "image/jpeg", "carousel.1"),
    ("images/carousel2.jpg", "carousel2.jpg", "image/jpeg", "carousel.2"),
    ("images/carousel3.jpg", "carousel3.jpg", "image/jpeg", "carousel.3"),
    ("images/carousel4.jpg", "carousel4.jpg", "image/jpeg", "carousel.4"),
)

ALLOWED_EXT = {
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "png": "image/png",
    "webp": "image/webp",
}
JPEG_DECLARED = {"image/jpeg", "image/jpg", "image/pjpeg"}

MAX_DOCUMENT_BYTES = 16 * 1024 * 1024
DOCUMENT_LIBRARIES = ("treasurer", "financial_secretary")
DOCUMENT_LIBRARY_SET = frozenset(DOCUMENT_LIBRARIES)
LIBRARY_FOLDERS = {
    "treasurer": "treasurer",
    "financial_secretary": "financial-secretary",
}
DOCUMENT_TYPES = {
    "pdf": "application/pdf",
    "doc": "application/msword",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "xls": "application/vnd.ms-excel",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}
DOCUMENT_CONTENT_TYPES = frozenset(DOCUMENT_TYPES.values())
DOCUMENT_DECLARED_OK = DOCUMENT_CONTENT_TYPES | {
    "",
    "application/octet-stream",
    "binary/octet-stream",
    "application/x-download",
    "application/x-pdf",
    "application/vnd.ms-word",
    "application/excel",
    "application/x-excel",
    "application/x-msexcel",
    "application/vnd.ms-office",
}
OLE_MAGIC = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"
ZIP_MAGIC = b"PK\x03\x04"

# Example library files. The API inserts these rows only when the documents
# table is first created. Memory fallback always starts from this list.
SEED_DOCUMENTS: tuple[dict[str, str], ...] = (
    {
        "library": "treasurer",
        "title": "September 2026 statement",
        "description": "Receipts and disbursements for September.",
        "uploaded_at": "2026-10-02T17:00:00+00:00",
        "file_path": "backend/uploads/treasurer/seed-september-2026.pdf",
        "original_name": "september-2026-statement.pdf",
        "content_type": "application/pdf",
        "uploaded_by": "1000000",
    },
    {
        "library": "treasurer",
        "title": "August 2026 statement",
        "description": "Receipts and disbursements for August.",
        "uploaded_at": "2026-09-04T17:00:00+00:00",
        "file_path": "backend/uploads/treasurer/seed-august-2026.pdf",
        "original_name": "august-2026-statement.pdf",
        "content_type": "application/pdf",
        "uploaded_by": "1000000",
    },
    {
        "library": "financial_secretary",
        "title": "September 2026 membership report",
        "description": "New members, transfers, and suspensions.",
        "uploaded_at": "2026-10-03T17:00:00+00:00",
        "file_path": "backend/uploads/financial-secretary/seed-membership-september-2026.pdf",
        "original_name": "september-2026-membership-report.pdf",
        "content_type": "application/pdf",
        "uploaded_by": "1000000",
    },
    {
        "library": "financial_secretary",
        "title": "Dues notes, September 2026",
        "description": "Brothers with dues still open this month.",
        "uploaded_at": "2026-09-15T17:00:00+00:00",
        "file_path": "backend/uploads/financial-secretary/seed-dues-notes-september-2026.pdf",
        "original_name": "dues-notes-september-2026.pdf",
        "content_type": "application/pdf",
        "uploaded_by": "1000000",
    },
)


class MediaError(ValueError):
    pass


def slot_check_sql() -> str:
    for slot in SLOTS:
        if not re.fullmatch(r"[a-z0-9.]+", slot):
            raise RuntimeError(f"Unexpected image slot: {slot}")
    choices = ", ".join(f"'{slot}'" for slot in SLOTS)
    return f"CHECK (slot IS NULL OR slot IN ({choices}))"


def normalize_crop(x: float, y: float, scale: float) -> tuple[float, float, float]:
    try:
        scale_n = float(scale)
        x_n = float(x)
        y_n = float(y)
    except (TypeError, ValueError) as exc:
        raise MediaError("Viewing angle is not valid.") from exc
    if not math.isfinite(scale_n) or not math.isfinite(x_n) or not math.isfinite(y_n):
        raise MediaError("Viewing angle is not valid.")
    if scale_n < 1 or scale_n > 3:
        raise MediaError("Zoom must stay between 1 and 3.")
    limit = max(0.0, (scale_n - 1) / 2)
    x_n = min(limit, max(-limit, x_n))
    y_n = min(limit, max(-limit, y_n))
    return (round(x_n, 4), round(y_n, 4), round(scale_n, 4))


def normalize_slot(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = str(value).strip()
    if not cleaned:
        return None
    if cleaned not in SLOT_SET:
        raise MediaError("Unknown image slot.")
    return cleaned


def detect_image(data: bytes) -> str | None:
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return None


def validate_image(filename: str, declared: str | None, data: bytes) -> tuple[str, str]:
    ext = ""
    if filename and "." in filename:
        ext = filename.rsplit(".", 1)[-1].lower()
    if ext not in ALLOWED_EXT:
        raise MediaError("Only JPG, PNG, and WebP images are accepted.")
    if not data:
        raise MediaError("The image file is empty.")
    if len(data) > MAX_IMAGE_BYTES:
        raise MediaError("Image must be 8 MB or smaller.")
    detected = detect_image(data)
    if detected is None or detected != ALLOWED_EXT[ext]:
        raise MediaError("Only JPG, PNG, and WebP images are accepted.")
    declared_type = (declared or "").split(";")[0].strip().lower()
    if declared_type and declared_type not in {"application/octet-stream", "binary/octet-stream"}:
        if not (detected == "image/jpeg" and declared_type in JPEG_DECLARED) and declared_type != detected:
            raise MediaError("Only JPG, PNG, and WebP images are accepted.")
    stored_ext = "jpg" if detected == "image/jpeg" else "png" if detected == "image/png" else "webp"
    return detected, stored_ext


def safe_original_name(filename: str, ext: str) -> str:
    base = Path(filename or "").name
    base = re.sub(r"[^A-Za-z0-9._ -]", "", base).strip().strip(".")
    if not base:
        base = f"image.{ext}"
    lower = base.lower()
    if not (lower.endswith(f".{ext}") or (ext == "jpg" and lower.endswith(".jpeg"))):
        stem = base.rsplit(".", 1)[0] if "." in base else base
        base = f"{stem}.{ext}"
    return base[:120]


def absolute_path(relative: str) -> Path:
    normalized = relative.replace("\\", "/").lstrip("/")
    if not normalized or normalized.startswith("../") or "/../" in f"/{normalized}/":
        raise MediaError("Image path is not allowed.")
    if normalized == "backend/uploads" or normalized.startswith(_UPLOAD_LOGICAL):
        rest = normalized[len(_UPLOAD_LOGICAL):] if normalized.startswith(_UPLOAD_LOGICAL) else ""
        if rest.startswith("/") or ".." in rest.split("/"):
            raise MediaError("Image path is not allowed.")
        root = UPLOAD_DIR.resolve()
        full = (root / rest).resolve() if rest else root
        try:
            full.relative_to(root)
        except ValueError as exc:
            raise MediaError("Image path is not allowed.") from exc
        return full
    full = (REPO_ROOT / normalized).resolve()
    try:
        full.relative_to(REPO_ROOT.resolve())
    except ValueError as exc:
        raise MediaError("Image path is not allowed.") from exc
    return full


def public_url(image_id: int, path: str) -> str:
    normalized = path.replace("\\", "/")
    if normalized.startswith("images/"):
        return "/" + normalized
    filename = normalized.rsplit("/", 1)[-1]
    return f"/api/media/files/{image_id}?v={filename}"


def write_upload(data: bytes, ext: str) -> str:
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    name = f"{uuid4().hex}.{ext}"
    target = UPLOAD_DIR / name
    target.write_bytes(data)
    return f"backend/uploads/{name}"


def delete_stored_file(path: str) -> None:
    normalized = path.replace("\\", "/")
    if not normalized.startswith("backend/uploads/"):
        return
    try:
        absolute_path(normalized).unlink(missing_ok=True)
    except Exception:
        return


def _collapse(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def normalize_library(value: str) -> str:
    cleaned = str(value or "").strip()
    if cleaned not in DOCUMENT_LIBRARY_SET:
        raise MediaError("Unknown library.")
    return cleaned


def clean_document_title(value: str) -> str:
    title = _collapse(value)
    if not title:
        raise MediaError("Enter a title.")
    if len(title) > 120:
        raise MediaError("Title must be 120 characters or fewer.")
    return title


def clean_document_description(value: str) -> str:
    description = _collapse(value)
    if len(description) > 280:
        raise MediaError("Description must be 280 characters or fewer.")
    return description


def library_prefix(library: str) -> str:
    cleaned = normalize_library(library)
    return f"backend/uploads/{LIBRARY_FOLDERS[cleaned]}/"


def document_path_allowed(library: str, path: str) -> bool:
    try:
        prefix = library_prefix(library)
    except MediaError:
        return False
    normalized = str(path or "").replace("\\", "/")
    if not normalized.startswith(prefix):
        return False
    return ".." not in normalized.split("/")


def detect_document(ext: str, data: bytes) -> bool:
    if ext == "pdf":
        return data.startswith(b"%PDF")
    if ext in {"docx", "xlsx"}:
        return data.startswith(ZIP_MAGIC)
    if ext in {"doc", "xls"}:
        return data.startswith(OLE_MAGIC)
    return False


def validate_document(filename: str, declared: str | None, data: bytes) -> tuple[str, str]:
    ext = ""
    if filename and "." in filename:
        ext = filename.rsplit(".", 1)[-1].lower()
    if ext not in DOCUMENT_TYPES:
        raise MediaError("Only PDF, DOC, DOCX, XLS, and XLSX files are accepted.")
    if not data:
        raise MediaError("The document file is empty.")
    if len(data) > MAX_DOCUMENT_BYTES:
        raise MediaError("Document must be 16 MB or smaller.")
    if not detect_document(ext, data):
        raise MediaError("Only PDF, DOC, DOCX, XLS, and XLSX files are accepted.")
    declared_type = (declared or "").split(";")[0].strip().lower()
    if declared_type not in DOCUMENT_DECLARED_OK:
        raise MediaError("Only PDF, DOC, DOCX, XLS, and XLSX files are accepted.")
    return DOCUMENT_TYPES[ext], ext


def safe_document_name(filename: str, ext: str) -> str:
    base = Path(filename or "").name
    base = re.sub(r"[^A-Za-z0-9._ -]", "", base).strip().strip(".")
    if not base:
        base = f"document.{ext}"
    if not base.lower().endswith(f".{ext}"):
        stem = base.rsplit(".", 1)[0] if "." in base else base
        base = f"{stem}.{ext}"
    return base[:120]


def write_library_file(library: str, data: bytes, ext: str) -> str:
    cleaned = normalize_library(library)
    if ext not in DOCUMENT_TYPES:
        raise MediaError("Only PDF, DOC, DOCX, XLS, and XLSX files are accepted.")
    folder = UPLOAD_DIR / LIBRARY_FOLDERS[cleaned]
    folder.mkdir(parents=True, exist_ok=True)
    name = f"{uuid4().hex}.{ext}"
    target = folder / name
    target.write_bytes(data)
    return f"backend/uploads/{LIBRARY_FOLDERS[cleaned]}/{name}"


def _as_utc(value: datetime | str) -> datetime:
    if isinstance(value, datetime):
        moment = value
    else:
        moment = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(timezone.utc)


def _nth_sunday(year: int, month: int, n: int) -> date:
    first = date(year, month, 1)
    offset = (6 - first.weekday()) % 7
    return date(year, month, 1 + offset + 7 * (n - 1))


def _chicago_date(moment: datetime) -> date:
    """Calendar date in America/Chicago. Falls back if the zone database is missing."""
    utc = _as_utc(moment)
    try:
        from zoneinfo import ZoneInfo

        return utc.astimezone(ZoneInfo("America/Chicago")).date()
    except Exception:
        start_day = _nth_sunday(utc.year, 3, 2)
        end_day = _nth_sunday(utc.year, 11, 1)
        start = datetime(start_day.year, start_day.month, start_day.day, 8, 0, tzinfo=timezone.utc)
        end = datetime(end_day.year, end_day.month, end_day.day, 7, 0, tzinfo=timezone.utc)
        hours = -5 if start <= utc < end else -6
        return (utc + timedelta(hours=hours)).date()


def uploaded_on(value: datetime | str) -> str:
    return _chicago_date(value).isoformat()


def minimal_pdf(message: str) -> bytes:
    """A one-page PDF whose text is the document title. Used for example files."""
    safe = "".join(
        ch if 32 <= ord(ch) < 127 and ch not in "()\\" else " " for ch in message
    ).strip() or "Council 10930"
    safe = safe[:90]
    stream = f"BT /F1 14 Tf 72 720 Td ({safe}) Tj ET".encode("ascii")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Count 1 /Kids [3 0 R] >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length " + str(len(stream)).encode("ascii") + b" >>\nstream\n" + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    parts: list[bytes] = [b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n"]
    offsets = [0]
    for index, body in enumerate(objects, start=1):
        offsets.append(sum(len(part) for part in parts))
        parts.append(f"{index} 0 obj\n".encode("ascii") + body + b"\nendobj\n")
    xref_at = sum(len(part) for part in parts)
    lines = [f"xref\n0 {len(objects) + 1}\n", "0000000000 65535 f \n"]
    for offset in offsets[1:]:
        lines.append(f"{offset:010d} 00000 n \n")
    lines.append(
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_at}\n%%EOF\n"
    )
    parts.append("".join(lines).encode("ascii"))
    return b"".join(parts)


def ensure_seed_documents() -> None:
    """Write the example PDFs when they are missing. Does not insert database rows."""
    for item in SEED_DOCUMENTS:
        target = absolute_path(item["file_path"])
        if target.is_file():
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(minimal_pdf(item["title"]))
