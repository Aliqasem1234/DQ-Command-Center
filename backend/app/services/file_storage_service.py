"""
Storage for uploaded dataset files.

Security notes:
- The on-disk filename is always a generated UUID, never the client-supplied
  filename - this removes any path traversal risk from a crafted filename
  and avoids collisions. The original filename is kept only as metadata.
- Extension is validated against an explicit allowlist before anything is
  written to disk.
- Size is enforced by counting bytes as they're read, so an attacker can't
  bypass a Content-Length header check by lying about it.
"""
import os
import uuid
from pathlib import Path
from typing import BinaryIO

from fastapi import UploadFile

from app.config import settings

ALLOWED_EXTENSIONS = {".csv", ".xlsx", ".xls"}


class UploadValidationError(ValueError):
    pass


def _upload_root() -> Path:
    root = Path(settings.UPLOAD_DIR)
    root.mkdir(parents=True, exist_ok=True)
    return root


def safe_display_filename(filename: str | None) -> str | None:
    """Strip any directory components from a client-supplied filename before
    storing it as display metadata (shown in the UI and echoed back verbatim
    in the download response's Content-Disposition header). The on-disk
    storage path never uses this value - it's generated separately as a
    UUID - but a raw '../../etc/passwd.csv' style name should still never be
    persisted or handed back to a client as-is, rather than relying on
    browsers' own (inconsistent) filename sanitization."""
    if not filename:
        return filename
    return Path(filename).name


def validate_extension(filename: str) -> str:
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise UploadValidationError(
            f"Unsupported file type '{ext or '(none)'}'. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
        )
    return ext


async def save_upload(dataset_id: uuid.UUID, file: UploadFile) -> tuple[str, str, int]:
    """Stream an UploadFile to disk under a generated name.

    Returns (relative_file_path, file_format, size_bytes).
    Raises UploadValidationError if the extension or size is invalid.
    """
    ext = validate_extension(file.filename or "")
    file_format = ext.lstrip(".")

    dataset_dir = _upload_root() / str(dataset_id)
    dataset_dir.mkdir(parents=True, exist_ok=True)

    stored_name = f"{uuid.uuid4()}{ext}"
    dest_path = dataset_dir / stored_name

    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    size = 0
    chunk_size = 1024 * 1024

    try:
        with open(dest_path, "wb") as out:
            while True:
                chunk = await file.read(chunk_size)
                if not chunk:
                    break
                size += len(chunk)
                if size > max_bytes:
                    raise UploadValidationError(
                        f"File exceeds the {settings.MAX_UPLOAD_SIZE_MB}MB upload limit."
                    )
                out.write(chunk)
    except UploadValidationError:
        dest_path.unlink(missing_ok=True)
        raise
    except Exception:
        dest_path.unlink(missing_ok=True)
        raise

    relative_path = str(Path(str(dataset_id)) / stored_name)
    return relative_path, file_format, size


def resolve_path(relative_path: str) -> Path:
    """Resolve a stored relative path back to an absolute path, refusing to
    escape the upload root even if relative_path were somehow tampered with."""
    root = _upload_root().resolve()
    candidate = (root / relative_path).resolve()
    if root not in candidate.parents and candidate != root:
        raise UploadValidationError("Invalid file path.")
    return candidate


def delete_file(relative_path: str) -> None:
    path = resolve_path(relative_path)
    path.unlink(missing_ok=True)


def remove_dataset_dir(dataset_id) -> None:
    """Remove a dataset's (now empty) upload folder, if any."""
    root = _upload_root().resolve()
    folder = (root / str(dataset_id)).resolve()
    if folder.parent != root or not folder.is_dir():
        return
    try:
        folder.rmdir()  # only succeeds when empty - never deletes unknown files
    except OSError:
        pass
