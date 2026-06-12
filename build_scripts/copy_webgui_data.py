#!/usr/bin/env python3
"""Copy webgui render-data sidecar files into the built pages that need them.

``widgets_to_directives.py`` offloads each webgui scene's render data to a
hash-named ``webgui_data_<hash>.json`` file next to the notebook and references
it from the ``{anywidget}`` directive as a relative URL (``./webgui_data_*.json``).

MyST inlines the directive's module/CSS at build time but treats that URL as an
opaque string — it never copies the file into the output.  At runtime the page
served from ``…/notebooks/<slug>/`` fetches ``./webgui_data_<hash>.json``, which
resolves to that page's own directory.  So after ``myst build`` we must drop each
referenced data file next to the ``index.html`` that references it.

We discover the references by scanning the built ``index.html`` files rather than
re-deriving MyST's page slugs, so this stays correct regardless of slug rules.

Usage::

    python scripts/copy_webgui_data.py --source notebooks --site public
"""
from __future__ import annotations

import argparse
import pathlib
import re
import shutil
import sys

DATA_RE = re.compile(r"webgui_data_[0-9a-f]+\.json")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source",
        type=pathlib.Path,
        default=pathlib.Path("notebooks"),
        help="directory holding the webgui_data_*.json files (default: notebooks)",
    )
    parser.add_argument(
        "--site",
        type=pathlib.Path,
        default=pathlib.Path("public"),
        help="built site root to scan for pages (default: public)",
    )
    args = parser.parse_args(argv)

    copied = 0
    missing = 0
    for page in args.site.rglob("index.html"):
        names = set(DATA_RE.findall(page.read_text(encoding="utf-8")))
        for name in names:
            src = args.source / name
            if not src.exists():
                print(f"missing source for {name} (referenced by {page})", file=sys.stderr)
                missing += 1
                continue
            shutil.copy2(src, page.parent / name)
            copied += 1

    print(f"copied {copied} webgui data file(s); {missing} missing")
    return 1 if missing else 0


if __name__ == "__main__":
    raise SystemExit(main())
