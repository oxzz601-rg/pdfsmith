import pytest

pytest.importorskip("pypdf")
from pypdf import PdfReader, PdfWriter

from pdfsmith import ops
from pdfsmith.cli import main


def make_pdf(path, pages=3, title=None):
    writer = PdfWriter()
    for _ in range(pages):
        writer.add_blank_page(width=200, height=400)
    if title:
        writer.add_metadata({"/Title": title})
    with open(path, "wb") as handle:
        writer.write(handle)
    return path


def page_count(path):
    return len(PdfReader(str(path)).pages)


def test_parse_pages_understands_ranges():
    assert ops.parse_pages("1-3,7", 20) == [0, 1, 2, 6]
    assert ops.parse_pages("9-", 10) == [8, 9]
    assert ops.parse_pages(None, 3) == [0, 1, 2]
    assert ops.parse_pages("3,1,3", 5) == [2, 0]
    with pytest.raises(ValueError):
        ops.parse_pages("7-2", 10)
    with pytest.raises(ValueError):
        ops.parse_pages("11", 10)


def test_merge_concatenates_in_order(tmp_path):
    first = make_pdf(tmp_path / "a.pdf", 2)
    second = make_pdf(tmp_path / "b.pdf", 3)
    out = tmp_path / "merged.pdf"
    result = ops.merge([first, second], out)
    assert result["pages"] == 5
    assert page_count(out) == 5


def test_extract_keeps_selection_order(tmp_path):
    source = make_pdf(tmp_path / "in.pdf", 5)
    out = tmp_path / "out.pdf"
    result = ops.extract_pages(source, out, "4,1")
    assert result["pages"] == 2 and result["source_pages"] == 5
    assert page_count(out) == 2


def test_delete_refuses_to_remove_everything(tmp_path):
    source = make_pdf(tmp_path / "in.pdf", 2)
    out = tmp_path / "out.pdf"
    assert ops.delete_pages(source, out, "2")["pages"] == 1
    with pytest.raises(ValueError):
        ops.delete_pages(source, out, "1-2")


def test_split_writes_one_file_per_chunk(tmp_path):
    source = make_pdf(tmp_path / "in.pdf", 5)
    result = ops.split_every(source, tmp_path / "parts", every=2)
    assert result["count"] == 3
    assert page_count(result["files"][0]) == 2
    assert page_count(result["files"][-1]) == 1


def test_rotate_sets_page_rotation(tmp_path):
    source = make_pdf(tmp_path / "in.pdf", 2)
    out = tmp_path / "out.pdf"
    ops.rotate_pages(source, out, degrees=90, pages="1")
    reader = PdfReader(str(out))
    assert reader.pages[0].rotation == 90
    assert reader.pages[1].rotation == 0
    with pytest.raises(ValueError):
        ops.rotate_pages(source, out, degrees=45)


def test_metadata_can_be_read_set_and_stripped(tmp_path):
    source = make_pdf(tmp_path / "in.pdf", 1, title="Original")
    assert ops.info(source)["metadata"]["Title"] == "Original"

    tagged = tmp_path / "tagged.pdf"
    ops.set_metadata(source, tagged, title="Report", author="Ada")
    metadata = ops.info(tagged)["metadata"]
    assert metadata["Title"] == "Report" and metadata["Author"] == "Ada"

    stripped = tmp_path / "stripped.pdf"
    ops.strip_metadata(tagged, stripped)
    metadata = ops.info(stripped)["metadata"]
    # The original fields are gone; the new writer records itself as Producer.
    assert "Title" not in metadata and "Author" not in metadata
    assert metadata.get("Producer") == "pypdf"


def test_images_become_pages(tmp_path):
    pytest.importorskip("PIL")
    from PIL import Image

    images = []
    for index, colour in enumerate(["red", "blue", "green"]):
        path = tmp_path / "img{}.png".format(index)
        Image.new("RGB", (40, 60), colour).save(path)
        images.append(path)
    out = tmp_path / "album.pdf"
    result = ops.images_to_pdf(images, out)
    assert result["pages"] == 3
    assert page_count(out) == 3


def test_text_reports_pages_and_characters(tmp_path):
    source = make_pdf(tmp_path / "in.pdf", 2)
    result = ops.text(source)
    assert result["pages"] == 2
    assert "characters" in result and isinstance(result["text"], str)


def test_cli_round_trip(tmp_path, capsys):
    source = make_pdf(tmp_path / "in.pdf", 3)
    out = tmp_path / "out.pdf"
    assert main(["extract", str(source), str(out), "-p", "1-2"]) == 0
    assert "pages: 2" in capsys.readouterr().out
    assert page_count(out) == 2
    assert main(["info", str(out), "--json"]) == 0
    assert '"pages": 2' in capsys.readouterr().out
    assert main(["extract", str(source), str(out), "-p", "99"]) == 2
