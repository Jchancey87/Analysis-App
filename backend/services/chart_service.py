import os
import uuid
from config import Config

VALID_TAGS = [
    'gap-and-hold',
    'gap-and-fade',
    'breakout-clean',
    'breakout-whipsaw',
    'multi-day-runner',
    'sector-sympathy',
    'news-fresh',
    'news-stale',
    'halt-triggered',
    'failed-follow-through',
]


def validate_tags(tags: list) -> list:
    """Return list of any tags not in the allowlist."""
    return [t for t in tags if t not in VALID_TAGS]


def save_chart_image(file, ticker: str = None, capture_date: str = None,
                     subfolder: str = None) -> str:
    """
    Validate and save an uploaded image file.
    Returns the full filesystem path where the file was saved.
    Raises ValueError on bad MIME type or oversized file.
    """
    if file.mimetype not in Config.ALLOWED_MIME_TYPES:
        raise ValueError(
            f"Invalid file type '{file.mimetype}'. "
            f"Allowed: {sorted(Config.ALLOWED_MIME_TYPES)}"
        )

    # Check size without fully reading into RAM
    file.seek(0, 2)
    size = file.tell()
    file.seek(0)
    if size > Config.MAX_UPLOAD_BYTES:
        raise ValueError("File exceeds 10 MB limit.")

    ext = 'png'
    if file.filename and '.' in file.filename:
        raw_ext = file.filename.rsplit('.', 1)[-1].lower()
        if raw_ext in Config.ALLOWED_EXTENSIONS:
            ext = raw_ext

    parts = [p for p in [ticker, capture_date, str(uuid.uuid4())[:8]] if p]
    filename = '_'.join(parts) + f'.{ext}'

    save_dir = Config.STORAGE_PATH
    if subfolder:
        save_dir = os.path.join(save_dir, subfolder)
    os.makedirs(save_dir, exist_ok=True)

    full_path = os.path.join(save_dir, filename)
    file.save(full_path)
    return full_path
