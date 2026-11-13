"""PDF operations, built on pypdf plus Pillow for the images command.

Every function takes paths and returns a small summary dictionary, which is
what the CLI prints. Nothing here talks to the network.
"""

from __future__ import annotations

import pathlib


def _reader(path, password=None):
    from pypdf import PdfReader

    reader = PdfReader(str(path))
    if reader.is_encrypted:
        if not password:
            raise ValueError("{} is encrypted; pass --password".format(path))
        if reader.decrypt(password) == 0:
            raise ValueError("could not decrypt {} with that password".format(path))
    return reader


def _writer():
    from pypdf import PdfWriter

    return PdfWriter()


def parse_pages(spec, page_count):
    """Translate ``"1-3,7,9-"`` into zero-based page indices, in order, deduplicated."""
    if spec is None or str(spec).strip().lower() in ("", "all"):
        return list(range(page_count))
    pages = []
    for chunk in str(spec).split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        if "-" in chunk:
            start, _, end = chunk.partition("-")
            first = int(start) if start.strip() else 1
            last = int(end) if end.strip() else page_count
        else:
            first = last = int(chunk)
        if first < 1 or last > page_count or first > last:
            raise ValueError("page range {!r} is outside 1-{}".format(chunk, page_count))
        pages.extend(range(first - 1, last))
    ordered, seen = [], set()
    for page in pages:
        if page not in seen:
            seen.add(page)
            ordered.append(page)
    return ordered


def _write(writer, out, compress=False):
    if compress:
        for page in writer.pages:
            page.compress_content_streams()
    out = pathlib.Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "wb") as handle:
        writer.write(handle)
    writer.close()
    return str(out)


def merge(sources, out, password=None, compress=False):
    """Concatenate PDFs in the order given."""
    if not sources:
        raise ValueError("merge needs at least one input PDF")
    writer = _writer()
    total = 0
    for source in sources:
        reader = _reader(source, password)
        for page in reader.pages:
            writer.add_page(page)
            total += 1
    return {"output": _write(writer, out, compress), "pages": total, "sources": len(sources)}


def extract_pages(source, out, pages, password=None):
    """Keep only the selected pages."""
    reader = _reader(source, password)
    selected = parse_pages(pages, len(reader.pages))
    if not selected:
        raise ValueError("no pages selected")
    writer = _writer()
    for index in selected:
        writer.add_page(reader.pages[index])
    return {"output": _write(writer, out), "pages": len(selected), "source_pages": len(reader.pages)}


def delete_pages(source, out, pages, password=None):
    """Remove the selected pages and keep the rest."""
    reader = _reader(source, password)
    total = len(reader.pages)
    drop = set(parse_pages(pages, total))
    keep = [index for index in range(total) if index not in drop]
    if not keep:
        raise ValueError("refusing to delete every page")
    writer = _writer()
    for index in keep:
        writer.add_page(reader.pages[index])
    return {"output": _write(writer, out), "pages": len(keep), "removed": len(drop)}


def split_every(source, out_dir, every=1, password=None):
    """Write chunks of ``every`` pages as separate files."""
    if every < 1:
        raise ValueError("chunk size must be at least 1")
    reader = _reader(source, password)
    out_dir = pathlib.Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = pathlib.Path(source).stem
    written = []
    for start in range(0, len(reader.pages), every):
        writer = _writer()
        for page in reader.pages[start : start + every]:
            writer.add_page(page)
        name = out_dir / "{}-{:03d}.pdf".format(stem, start // every + 1)
        written.append(_write(writer, name))
    return {"output": str(out_dir), "files": written, "count": len(written)}


def rotate_pages(source, out, degrees=90, pages=None, password=None):
    """Rotate selected pages clockwise by ``degrees`` (a multiple of 90)."""
    if degrees % 90 != 0:
        raise ValueError("degrees must be a multiple of 90")
    reader = _reader(source, password)
    selected = set(parse_pages(pages, len(reader.pages)))
    writer = _writer()
    for index, page in enumerate(reader.pages):
        writer.add_page(page)
        if index in selected:
            writer.pages[-1].rotate(degrees)
    return {"output": _write(writer, out), "rotated": len(selected), "degrees": degrees}


def info(source, password=None):
    """Page count, page size and document metadata."""
    reader = _reader(source, password)
    first = reader.pages[0].mediabox if len(reader.pages) else None
    metadata = {}
    if reader.metadata:
        for key, value in reader.metadata.items():
            metadata[str(key).lstrip("/")] = str(value)
    return {
        "path": str(source),
        "pages": len(reader.pages),
        "encrypted": reader.is_encrypted,
        "size_points": [round(float(first.width), 2), round(float(first.height), 2)] if first else None,
        "metadata": metadata,
    }


def strip_metadata(source, out, password=None):
    """Rewrite the document with only its pages, dropping document info."""
    reader = _reader(source, password)
    writer = _writer()
    for page in reader.pages:
        writer.add_page(page)
    return {"output": _write(writer, out), "pages": len(reader.pages), "metadata_removed": bool(reader.metadata)}


def set_metadata(source, out, password=None, **fields):
    """Set document info fields such as title, author or subject."""
    reader = _reader(source, password)
    writer = _writer()
    for page in reader.pages:
        writer.add_page(page)
    payload = {"/" + key.strip("/").capitalize(): str(value) for key, value in fields.items() if value is not None}
    if payload:
        writer.add_metadata(payload)
    return {"output": _write(writer, out), "pages": len(reader.pages), "set": sorted(payload)}


def images_to_pdf(images, out, resolution=150):
    """Combine images into one PDF, one image per page."""
    try:
        from PIL import Image
    except ImportError as exc:  # pragma: no cover - depends on optional extra
        raise RuntimeError("images_to_pdf needs Pillow: pip install 'pdfsmith[images]'") from exc
    if not images:
        raise ValueError("images_to_pdf needs at least one image")
    frames = []
    for path in images:
        with Image.open(path) as image:
            frames.append(image.convert("RGB"))
    out = pathlib.Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    frames[0].save(str(out), "PDF", save_all=True, append_images=frames[1:], resolution=resolution)
    return {"output": str(out), "pages": len(frames), "resolution": resolution}


def text(source, pages=None, password=None):
    """Extract text from the selected pages."""
    reader = _reader(source, password)
    selected = parse_pages(pages, len(reader.pages))
    chunks = []
    for index in selected:
        extracted = reader.pages[index].extract_text() or ""
        chunks.append("\n--- page {} ---\n{}".format(index + 1, extracted.strip()))
    return {"pages": len(selected), "characters": sum(len(chunk) for chunk in chunks), "text": "\n".join(chunks).strip()}
