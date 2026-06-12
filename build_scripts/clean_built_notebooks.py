#!/usr/bin/env python3
"""Strip the built downloadable notebooks back to clean source.

``myst build`` ships a downloadable copy of every executed notebook under
``public/build/*.ipynb``.  Those copies carry two things a reader downloading
the notebook should not get:

  * the executed cell *outputs* (large embedded images / arrays), and
  * the synthetic ``{anywidget}`` directive markdown cells that
    ``widgets_to_directives.py`` injected purely so MyST could render the
    webgui widgets statically — they are a build artifact, not notebook source.

This script reverses both, in place, so the downloadable notebooks match the
authored sources again:

  * every code cell loses its ``outputs`` and ``execution_count``, and
  * every markdown cell that is one of the injected ``{anywidget}`` directive
    cells is removed.

Usage::

    python scripts/clean_built_notebooks.py public/build/*.ipynb
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

# Must match the directive emitted by widgets_to_directives.py (MODULE_REF).
ANYWIDGET_DIRECTIVE_PREFIX = "```{anywidget} ./webgui.mjs"


def _is_injected_anywidget_cell(cell: dict) -> bool:
    """True for the dedicated markdown cells that widgets_to_directives.py adds."""
    if cell.get("cell_type") != "markdown":
        return False
    for line in cell.get("source", []):
        stripped = line.strip()
        if not stripped:
            continue
        # The cell's first non-empty line opens the {anywidget} directive.
        return stripped.startswith(ANYWIDGET_DIRECTIVE_PREFIX)
    return False


def clean_notebook(path: pathlib.Path) -> tuple[int, int]:
    """Clean one notebook in place. Returns (cells_removed, outputs_cleared)."""
    nb = json.loads(path.read_text(encoding="utf-8"))

    new_cells: list[dict] = []
    removed = 0
    cleared = 0
    for cell in nb.get("cells", []):
        if _is_injected_anywidget_cell(cell):
            removed += 1
            continue
        if cell.get("cell_type") == "code":
            if cell.get("outputs"):
                cleared += 1
            cell["outputs"] = []
            cell["execution_count"] = None
        new_cells.append(cell)

    nb["cells"] = new_cells

    # The widget-state blob is only meaningful alongside widget outputs.
    nb.get("metadata", {}).pop("widgets", None)

    path.write_text(json.dumps(nb, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return removed, cleared


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("notebooks", nargs="+", type=pathlib.Path)
    args = parser.parse_args(argv)

    for path in args.notebooks:
        if not path.exists():
            print(f"skip (missing): {path}", file=sys.stderr)
            continue
        removed, cleared = clean_notebook(path)
        print(f"{path}: removed {removed} anywidget cell(s), cleared {cleared} output(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
