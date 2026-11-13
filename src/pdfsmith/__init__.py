"""pdfsmith: everyday PDF edits, offline."""

from .ops import (
    delete_pages,
    extract_pages,
    images_to_pdf,
    info,
    merge,
    parse_pages,
    rotate_pages,
    set_metadata,
    split_every,
    strip_metadata,
    text,
)

__version__ = "0.1.0"

__all__ = [
    "delete_pages",
    "extract_pages",
    "images_to_pdf",
    "info",
    "merge",
    "parse_pages",
    "rotate_pages",
    "set_metadata",
    "split_every",
    "strip_metadata",
    "text",
]
