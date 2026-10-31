"""Tests that run the Python blocks in the documentation."""

import re
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import pytest
from matplotlib import pyplot as plt

DOCS = Path(__file__).resolve().parent.parent / "docs"
PAGES = sorted(DOCS.rglob("*.md"))


@pytest.mark.parametrize("page", PAGES, ids=lambda p: str(p.relative_to(DOCS)))
def test_python_blocks_run(page, tmp_path, monkeypatch):
    blocks = re.findall(r"^```python\n(.*?)^```", page.read_text(), re.S | re.M)
    if any("plot_3d" in block for block in blocks):
        pytest.importorskip("pyvista")
    monkeypatch.chdir(tmp_path)  # blocks may save figures
    namespace = {}  # blocks on a page build on each other
    for block in blocks:
        exec(compile(block, str(page), "exec"), namespace)
    plt.close("all")
