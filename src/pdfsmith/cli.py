"""The ``pdfsmith`` command line."""

from __future__ import annotations

import argparse
import json
import sys

from . import __version__, ops


def _report(result, as_json, skip=()):
    if as_json:
        print(json.dumps({key: value for key, value in result.items() if key not in skip}, indent=2))
        return
    for key, value in result.items():
        if key in skip:
            continue
        if isinstance(value, list):
            print("{}:".format(key))
            for item in value:
                print("  {}".format(item))
        else:
            print("{}: {}".format(key, value))


def _common(parser):
    parser.add_argument("--password", help="password for an encrypted input")
    parser.add_argument("--json", action="store_true", help="print a JSON summary")


def cmd_merge(args):
    _report(ops.merge(args.inputs, args.output, password=args.password, compress=args.compress), args.json)
    return 0


def cmd_extract(args):
    _report(ops.extract_pages(args.input, args.output, args.pages, password=args.password), args.json)
    return 0


def cmd_delete(args):
    _report(ops.delete_pages(args.input, args.output, args.pages, password=args.password), args.json)
    return 0


def cmd_split(args):
    _report(ops.split_every(args.input, args.output_dir, every=args.every, password=args.password), args.json, skip=("files",))
    if not args.json:
        for path in ops.split_every(args.input, args.output_dir, every=args.every, password=args.password)["files"]:
            print("  {}".format(path))
    return 0


def cmd_rotate(args):
    _report(ops.rotate_pages(args.input, args.output, degrees=args.degrees, pages=args.pages, password=args.password), args.json)
    return 0


def cmd_info(args):
    result = ops.info(args.input, password=args.password)
    if args.json:
        print(json.dumps(result, indent=2))
        return 0
    print("file: {}".format(result["path"]))
    print("pages: {}".format(result["pages"]))
    print("encrypted: {}".format(result["encrypted"]))
    if result["size_points"]:
        print("page size: {} x {} points".format(*result["size_points"]))
    if result["metadata"]:
        print("metadata:")
        for key, value in sorted(result["metadata"].items()):
            print("  {}: {}".format(key, value))
    else:
        print("metadata: (none)")
    return 0


def cmd_strip(args):
    _report(ops.strip_metadata(args.input, args.output, password=args.password), args.json)
    return 0


def cmd_metadata(args):
    fields = {
        "title": args.title,
        "author": args.author,
        "subject": args.subject,
        "keywords": args.keywords,
    }
    if not any(value is not None for value in fields.values()):
        print("pdfsmith: give at least one of --title/--author/--subject/--keywords", file=sys.stderr)
        return 2
    _report(ops.set_metadata(args.input, args.output, password=args.password, **fields), args.json)
    return 0


def cmd_images(args):
    try:
        result = ops.images_to_pdf(args.images, args.output, resolution=args.resolution)
    except RuntimeError as exc:
        print("pdfsmith: {}".format(exc), file=sys.stderr)
        return 2
    _report(result, args.json)
    return 0


def cmd_text(args):
    result = ops.text(args.input, pages=args.pages, password=args.password)
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(result["text"])
        print("\n{} page(s), {} characters".format(result["pages"], result["characters"]), file=sys.stderr)
    return 0


def build_parser():
    parser = argparse.ArgumentParser(prog="pdfsmith", description="Everyday PDF edits, offline.")
    parser.add_argument("--version", action="version", version="pdfsmith {}".format(__version__))
    sub = parser.add_subparsers(dest="command", required=True)

    merge = sub.add_parser("merge", help="join PDFs into one file")
    merge.add_argument("output")
    merge.add_argument("inputs", nargs="+")
    merge.add_argument("--compress", action="store_true", help="compress page content streams")
    _common(merge)
    merge.set_defaults(func=cmd_merge)

    extract = sub.add_parser("extract", help="keep only some pages")
    extract.add_argument("input")
    extract.add_argument("output")
    extract.add_argument("-p", "--pages", default="all", help='page selection, e.g. "1-3,7"')
    _common(extract)
    extract.set_defaults(func=cmd_extract)

    delete = sub.add_parser("delete", help="remove some pages")
    delete.add_argument("input")
    delete.add_argument("output")
    delete.add_argument("-p", "--pages", required=True, help='page selection, e.g. "2,5-6"')
    _common(delete)
    delete.set_defaults(func=cmd_delete)

    split = sub.add_parser("split", help="split into chunks of N pages")
    split.add_argument("input")
    split.add_argument("output_dir")
    split.add_argument("--every", type=int, default=1)
    _common(split)
    split.set_defaults(func=cmd_split)

    rotate = sub.add_parser("rotate", help="rotate pages")
    rotate.add_argument("input")
    rotate.add_argument("output")
    rotate.add_argument("--degrees", type=int, default=90)
    rotate.add_argument("-p", "--pages", default="all")
    _common(rotate)
    rotate.set_defaults(func=cmd_rotate)

    info_parser = sub.add_parser("info", help="page count, size and metadata")
    info_parser.add_argument("input")
    _common(info_parser)
    info_parser.set_defaults(func=cmd_info)

    strip = sub.add_parser("strip", help="remove document metadata")
    strip.add_argument("input")
    strip.add_argument("output")
    _common(strip)
    strip.set_defaults(func=cmd_strip)

    metadata = sub.add_parser("metadata", help="set document metadata")
    metadata.add_argument("input")
    metadata.add_argument("output")
    metadata.add_argument("--title")
    metadata.add_argument("--author")
    metadata.add_argument("--subject")
    metadata.add_argument("--keywords")
    _common(metadata)
    metadata.set_defaults(func=cmd_metadata)

    images = sub.add_parser("images", help="build a PDF from images")
    images.add_argument("output")
    images.add_argument("images", nargs="+")
    images.add_argument("--resolution", type=int, default=150)
    images.add_argument("--json", action="store_true")
    images.set_defaults(func=cmd_images)

    text_parser = sub.add_parser("text", help="extract text")
    text_parser.add_argument("input")
    text_parser.add_argument("-p", "--pages", default="all")
    _common(text_parser)
    text_parser.set_defaults(func=cmd_text)
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except (ValueError, OSError) as exc:
        print("pdfsmith: {}".format(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
