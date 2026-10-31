"""Tests for the matplotlib helpers in plot.py."""

from types import SimpleNamespace

import matplotlib

matplotlib.use("Agg")

import numpy as np
import pytest
from matplotlib import pyplot as plt

from warpx_geometry import (
    CylinderZ_hollow,
    create_rz_geometry_mask,
    plot_field2D,
    plot_particles2D,
    plot_rz_bboxes,
    plot_rz_geometry_components,
)

INFO = SimpleNamespace(xmin=0, xmax=1, ymin=2, ymax=4, zmin=5, zmax=8)


@pytest.fixture(autouse=True)
def close_figures():
    yield
    plt.close("all")


@pytest.mark.parametrize(
    "cut, extent, shape",
    [
        ("X", (2, 4, 5, 8), (4, 6)),
        ("Y", (0, 1, 5, 8), (4, 5)),
        ("Z", (2, 4, 0, 1), (5, 6)),
    ],
)
def test_plot_field2d_cuts(cut, extent, shape):
    ax = plot_field2D(np.zeros((4, 5, 6)), INFO, cut, 1)
    image = ax.get_images()[0]
    assert tuple(image.get_extent()) == extent
    assert image.get_array().shape == shape


def test_plot_field2d_fractional_cut():
    field = np.zeros((4, 5, 6))
    field[:, 2, :] = 1
    ax = plot_field2D(field, INFO, "X", 0.5)
    assert ax.get_images()[0].get_array().max() == 1


def test_plot_field2d_invalid_cut_raises():
    with pytest.raises(ValueError, match="cut_direction"):
        plot_field2D(np.zeros((4, 5, 6)), INFO, "W", 1)


def test_plot_field2d_saves(tmp_path):
    out = tmp_path / "field.png"
    plot_field2D(np.zeros((4, 5, 6)), INFO, "X", 1, filename=out)
    assert out.exists()


class Particles:
    def get_particle(self, names, iteration):
        return [1, 2], [iteration, -iteration], [iteration, iteration]


def test_plot_particles2d_has_one_line_per_particle():
    ax = plot_particles2D(Particles(), 3)
    assert len(ax.lines) == 2
    assert ax.lines[0].get_xdata().tolist() == [0, 1, 2]


def test_plot_particles2d_title_and_color():
    ax = plot_particles2D(Particles(), 2, title="Electrons", color="b")
    assert ax.get_title() == "Electrons"
    assert ax.lines[0].get_color() == "b"
    assert plot_particles2D(Particles(), 2).get_title() == ""


def test_plot_rz_bboxes_draws_each_component():
    fig, ax = plt.subplots()
    ax.set_xlim(-10, 60)
    ax.set_ylim(0, 30)
    ring = CylinderZ_hollow(0.02, 0.01, 0, 0.05)
    plot_rz_bboxes(ax, {"a": ring, "b": (ring, "red")}, margin=0.001)
    assert len(ax.patches) == 2


def test_plot_rz_geometry_components_with_bboxes():
    fig, ax = plt.subplots()
    ring = CylinderZ_hollow(0.02, 0.01, 0, 0.05)
    plot_rz_geometry_components(
        ax, {"ring": (ring, "blue")}, (-0.01, 0.06), (0, 0.03), bbox_margin=0.001
    )
    assert len(ax.patches) >= 1


def test_create_rz_geometry_mask():
    ring = CylinderZ_hollow(0.02, 0.01, 0, 0.05)
    Z, R, mask = create_rz_geometry_mask(ring, (-0.01, 0.06), (0, 0.03), 1)
    assert Z.shape == R.shape == mask.shape
    inside = (R > 0.01) & (R < 0.02) & (Z > 0) & (Z < 0.05)
    assert np.array_equal(mask > 0, inside)
