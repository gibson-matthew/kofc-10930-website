"""Image checks, seed files, and upload paths."""

from __future__ import annotations

import math
import re
from pathlib import Path
from uuid import uuid4

BACKEND_DIR = Path(__file__).resolve().parent
REPO_ROOT = BACKEND_DIR.parent
UPLOAD_DIR = BACKEND_DIR / "uploads"
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
