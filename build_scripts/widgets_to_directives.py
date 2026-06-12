#!/usr/bin/env python3
"""Rewrite webgui widget *outputs* into static ``{anywidget}`` directives.

MyST renders Jupyter widget outputs (``application/vnd.jupyter.widget-view+json``)
only through a live kernel, so in a static site they collapse to the
"a Jupyter kernel connection is required" placeholder.  MyST *does* render the
authored ``{anywidget}`` directive without a kernel, but a directive only takes
effect when it lives in notebook *source* (a markdown cell) — cell outputs are
never re-parsed as MyST markdown.

This script runs after ``jupyter nbconvert --execute`` and before ``myst build``.
For every code cell that displays a webgui ``anywidget`` it:

  * looks up the model's ``value`` / ``width`` / ``height`` in the notebook's
    stored ``widget-state`` metadata,
  * removes the widget output (so no placeholder is rendered), and
  * inserts a markdown cell right after the code cell holding an
    ``{anywidget} ./webgui.mjs`` directive whose JSON body is the model state.

The ``webgui.mjs`` / ``webgui.css`` referenced by the directives are produced by
``export_webgui_assets.py`` and must sit next to the notebooks.

Usage::

    python scripts/widgets_to_directives.py notebooks/*.ipynb
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import sys

WIDGET_VIEW_MIME = "application/vnd.jupyter.widget-view+json"
WIDGET_STATE_MIME = "application/vnd.jupyter.widget-state+json"

MODULE_REF = "./webgui.mjs"
CSS_REF = "./webgui.css"

# Prefix for the sidecar render-data files written next to each notebook.
DATA_PREFIX = "webgui_data_"


def _state_map(nb: dict) -> dict:
    """Return ``{model_id: state-dict}`` from the notebook's widget-state metadata."""
    widgets = nb.get("metadata", {}).get("widgets", {})
    state = widgets.get(WIDGET_STATE_MIME, {}).get("state", {})
    return state


def _is_webgui_model(model_entry: dict) -> bool:
    inner = model_entry.get("state", {})
    return model_entry.get("model_name") == "AnyModel" or "_anywidget_id" in inner


def _directive_source(bodies: list[dict]) -> list[str]:
    """Build markdown-cell source (list of lines) holding one directive per body."""
    blocks = []
    for body in bodies:
        payload = json.dumps(body, separators=(",", ":"))
        blocks.append(
            f"```{{anywidget}} {MODULE_REF}\n"
            f":css: {CSS_REF}\n"
            f"\n"
            f"{payload}\n"
            f"```"
        )
    text = "\n\n".join(blocks) + "\n"
    # nbformat stores source as a list of lines, each retaining its trailing "\n".
    return text.splitlines(keepends=True)


def _markdown_cell(source_lines: list[str]) -> dict:
    return {"cell_type": "markdown", "metadata": {}, "source": source_lines}


def _externalize_value(value: dict, out_dir: pathlib.Path) -> str:
    """Write the render-data *value* to a hash-named JSON file in *out_dir* and
    return a relative URL referencing it.

    Embedding the (large) render data inline in every ``{anywidget}`` directive
    bloats the notebooks and pages and makes ``myst build`` crawl.  Instead we
    drop it into a sidecar file next to the notebook — alongside webgui.mjs /
    webgui.css — and keep only the URL in the directive's ``value``; the widget
    JS fetches it at render time.  The file is content-addressed, so identical
    scenes share one file and names stay stable across rebuilds.
    """
    payload = json.dumps(value, separators=(",", ":"))
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]
    filename = f"{DATA_PREFIX}{digest}.json"
    (out_dir / filename).write_text(payload, encoding="utf-8")
    return f"../{filename}"


def convert_notebook(path: pathlib.Path) -> int:
    """Convert one notebook in place. Returns the number of widgets converted."""
    nb = json.loads(path.read_text(encoding="utf-8"))
    state = _state_map(nb)

    new_cells: list[dict] = []
    converted = 0
    leftover_widget_view = False

    for cell in nb.get("cells", []):
        new_cells.append(cell)
        if cell.get("cell_type") != "code":
            continue

        bodies: list[dict] = []
        kept_outputs: list[dict] = []
        for output in cell.get("outputs", []):
            data = output.get("data", {})
            if WIDGET_VIEW_MIME not in data:
                kept_outputs.append(output)
                continue

            model_id = data[WIDGET_VIEW_MIME].get("model_id")
            entry = state.get(model_id, {})
            if not entry or not _is_webgui_model(entry):
                # Unknown / non-webgui widget: leave it untouched.
                kept_outputs.append(output)
                leftover_widget_view = True
                continue

            inner = entry.get("state", {})
            bodies.append(
                {
                    "value": _externalize_value(inner.get("value", {}), path.parent),
                    "width": inner.get("width", "100%"),
                    "height": inner.get("height", "50vh"),
                }
            )
            converted += 1

        if bodies:
            cell["outputs"] = kept_outputs
            new_cells.append(_markdown_cell(_directive_source(bodies)))

    nb["cells"] = new_cells

    # Drop the now-unused widget-state blob (it bloats the built page) unless a
    # non-webgui widget still relies on it.
    if not leftover_widget_view:
        nb.get("metadata", {}).pop("widgets", None)

    path.write_text(json.dumps(nb, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return converted


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("notebooks", nargs="+", type=pathlib.Path)
    args = parser.parse_args(argv)

    total = 0
    for path in args.notebooks:
        if not path.exists():
            print(f"skip (missing): {path}", file=sys.stderr)
            continue
        n = convert_notebook(path)
        total += n
        print(f"{path}: converted {n} webgui widget(s)")
    print(f"total converted: {total}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
