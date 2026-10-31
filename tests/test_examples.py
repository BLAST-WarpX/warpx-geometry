"""Tests that the example scripts build a valid geometry."""

import runpy
from pathlib import Path

import pytest

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"


def test_einzel_lens_faraday_cup():
    pytest.importorskip("pyvista")
    example = runpy.run_path(EXAMPLES / "einzel_lens_faraday_cup.py")
    geo = example["geo"]
    assert str(geo)
    assert "-300" in geo.to_potential_expr(margin=0.0005)


def test_warpx_letters():
    pytest.importorskip("pyvista")
    example = runpy.run_path(EXAMPLES / "warpx_letters.py")
    assert str(example["build"]())


def test_warpx_einzel_lens():
    pytest.importorskip("pywarpx")
    example = runpy.run_path(EXAMPLES / "warpx_einzel_lens.py")
    assert "5000" in example["geo"].to_potential_expr()
