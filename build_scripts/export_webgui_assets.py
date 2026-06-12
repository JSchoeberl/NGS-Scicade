#!/usr/bin/env python3
"""Export the WebGuiWidget anywidget ESM/CSS to standalone files.

The interactive ``Draw()`` output in the notebooks is an
``anywidget.AnyWidget`` whose front-end code lives in the ``_esm`` / ``_css``
class attributes of :class:`WebGuiWidget`.  MyST cannot render Jupyter widget
*outputs* statically (it needs a kernel), but it *can* render an authored
``{anywidget}`` directive that points at an ESM module.

This script writes that module (``webgui.mjs``) and stylesheet (``webgui.css``)
to disk so :mod:`widgets_to_directives` can reference them from the generated
directives.  The strings are extracted with :mod:`ast` straight from
``webgui.py`` so this runs without importing netgen/ngsolve.

Usage::

    python scripts/export_webgui_assets.py [--source webgui.py] --out-dir notebooks
"""
from __future__ import annotations

import argparse
import ast
import pathlib
import sys


def _extract_class_strings(source: str, class_name: str, attrs: list[str]) -> dict[str, str]:
    """Return ``{attr: string-literal}`` for top-level string assignments in a class."""
    tree = ast.parse(source)
    found: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            for stmt in node.body:
                if not isinstance(stmt, ast.Assign):
                    continue
                value = stmt.value
                if not (isinstance(value, ast.Constant) and isinstance(value.value, str)):
                    continue
                for target in stmt.targets:
                    if isinstance(target, ast.Name) and target.id in attrs:
                        found[target.id] = value.value
    return found


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", default="scripts/webgui.py", help="path to webgui.py")
    parser.add_argument("--out-dir", default="notebooks", help="where to write webgui.mjs/.css")
    parser.add_argument("--class-name", default="WebGuiWidget")
    args = parser.parse_args(argv)

    source = pathlib.Path(args.source).read_text(encoding="utf-8")
    strings = _extract_class_strings(source, args.class_name, ["_esm", "_css"])

    missing = [a for a in ("_esm", "_css") if a not in strings]
    if missing:
        print(
            f"error: could not find {missing} on class {args.class_name} in {args.source}",
            file=sys.stderr,
        )
        return 1

    out_dir = pathlib.Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "webgui.mjs").write_text(strings["_esm"], encoding="utf-8")
    (out_dir / "webgui.css").write_text(strings["_css"], encoding="utf-8")
    print(f"wrote {out_dir/'webgui.mjs'} and {out_dir/'webgui.css'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
