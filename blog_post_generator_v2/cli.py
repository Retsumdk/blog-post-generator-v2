"""Command-line interface: `bpgen outline.json --notes notes.md --out post.md`."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .generate import (Notes, OutlineError, build_audit_report, build_post,
                       load_notes, load_outline)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="bpgen",
        description="Generate an SEO-optimized blog post draft from an outline "
                    "and research notes. Deterministic; zero dependencies.",
    )
    parser.add_argument("outline", help="path to the outline JSON file")
    parser.add_argument("--notes", help="path to a markdown research-notes file")
    parser.add_argument("--out", help="write the post markdown here (default: stdout)")
    parser.add_argument("--audit", help="write an SEO audit report here ('-' = stdout)")
    parser.add_argument("--date", help="publication date to record in the front matter")
    args = parser.parse_args(argv)

    try:
        outline = load_outline(args.outline)
        notes = load_notes(args.notes) if args.notes else Notes()
    except OutlineError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2

    post = build_post(outline, notes, date=args.date)

    if args.out:
        Path(args.out).write_text(post.markdown, encoding="utf-8")
    else:
        sys.stdout.write(post.markdown)

    if args.audit:
        report = build_audit_report(post)
        if args.audit == "-":
            sys.stdout.write("\n" + report)
        else:
            Path(args.audit).write_text(report, encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
