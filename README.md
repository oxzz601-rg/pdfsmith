# pdfsmith

**Everyday PDF edits, offline.** Merge, split, pull out pages, delete pages, rotate, strip metadata and turn images into a PDF, from one command. Nothing is uploaded anywhere.

```bash
pdfsmith merge statement.pdf invoice.pdf receipt.pdf -o claim.pdf
pdfsmith extract thesis.pdf chapter2.pdf --pages 12-28
pdfsmith delete scan.pdf clean.pdf --pages 1,17-19
pdfsmith rotate sideways.pdf upright.pdf --degrees 90 --pages 2-4
pdfsmith strip contract.pdf contract-clean.pdf
pdfsmith images photo1.jpg photo2.png -o album.pdf
```

The workflows people actually search for, without a subscription or a twenty-tab website:

- joining a bank statement, invoice and receipt into one claim document;
- pulling a chapter out of a book-sized PDF for a reading assignment;
- removing the blank or duplicate pages a scanner added;
- fixing sideways scans;
- removing your name, software and original filename from a document before sending it on;
- turning phone photos of paper forms into a single PDF.

## Install

```bash
python -m pip install -e ".[dev]"     # pypdf, plus Pillow for the images command
```

Python 3.9+. The core commands need only `pypdf`; `images` needs Pillow. No network access at runtime.

## Commands

| command | what it does |
| --- | --- |
| `merge OUT IN...` | concatenate PDFs in the given order |
| `extract IN OUT -p 1-3,7` | keep only those pages, in that order |
| `delete IN OUT -p 2,5-6` | remove those pages |
| `split IN OUTDIR --every 10` | write chunks of N pages |
| `rotate IN OUT --degrees 90 -p 1-2` | rotate selected pages |
| `info IN` | page count, page size, metadata |
| `strip IN OUT` | drop document metadata |
| `metadata IN OUT --title --author` | set document metadata |
| `images OUT IMG...` | one image per page |
| `text IN -p 1-5` | extract the text layer |

Page selection always uses human numbers, so `1` is the first page. Ranges may be open-ended (`9-`), combined (`1-3,7,12-`), and are de-duplicated while keeping your order.

Every command writes a new file, never edits the input in place. `delete` refuses to remove every page, and encrypted inputs take `--password`.

## Examples with output

```console
$ pdfsmith merge claim.pdf statement.pdf invoice.pdf
output: claim.pdf
pages: 9
sources: 2

$ pdfsmith info claim.pdf
file: claim.pdf
pages: 9
encrypted: False
page size: 595.28 x 841.89 points
metadata:
  Producer: pypdf

$ pdfsmith strip claim.pdf claim-clean.pdf
output: claim-clean.pdf
pages: 9
metadata_removed: True
```

Add `--json` to any command for machine-readable output.

## In Python

```python
from pdfsmith import merge, extract_pages, parse_pages

merge(["a.pdf", "b.pdf"], "both.pdf")
extract_pages("both.pdf", "first-ten.pdf", "1-10")
print(parse_pages("1-3,7", page_count=20))   # [0, 1, 2, 6]
```

## Known limits

- `text` extracts an existing text layer. Scanned pages need OCR; `pdfsmith` deliberately does not bundle an OCR engine.
- `images` needs Pillow and re-encodes images into the PDF; it does not preserve EXIF orientation.
- Page-level crops and true content redaction are not implemented, and `strip` removes document metadata rather than text inside pages.

## Tests

```bash
python -m pytest
```

MIT licensed.
