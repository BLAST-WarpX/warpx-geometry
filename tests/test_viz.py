"""Tests for the 2D (matplotlib) and 3D (pyvista) visualization."""

import matplotlib

matplotlib.use("Agg")

import importlib.util

import numpy as np
import pytest
from matplotlib import colors as mcolors
from matplotlib import pyplot as plt

from warpx_geometry import Box, Cylinder, CylinderZ, CylinderZ_hollow, Geometry
from warpx_geometry.viz import plot_2d


@pytest.fixture(autouse=True)
def close_figures():
    yield
    plt.close("all")


def beamline():
    a = CylinderZ_hollow(0.011, 0.009, 0.0, 0.01, name="a", default_voltage=100)
    b = CylinderZ_hollow(0.011, 0.009, 0.02, 0.03, name="b", default_voltage=-50)
    plate = Box(-0.02, 0.02, -0.02, 0.02, 0.04, 0.042)  # unnamed
    return a + b + plate


def legend_colors(ax):
    legend = ax.get_legend()
    return {
        t.get_text(): mcolors.to_hex(h.get_facecolor())
        for t, h in zip(legend.get_texts(), legend.legend_handles, strict=True)
    }


class TestPlot2D:
    def test_named_components_and_rest(self):
        ax = plot_2d(beamline(), colors={"a": "red", None: "black"})
        cols = legend_colors(ax)
        assert set(cols) == {"a", "b", "other"}
        assert cols["a"] == "#ff0000"
        assert cols["other"] == "#000000"
        assert ax.get_xlabel() == "z (mm)"

    def test_single_color(self):
        ax = plot_2d(beamline(), colors="green")
        assert set(legend_colors(ax).values()) == {"#008000"}

    def test_rz_geometry_defaults_to_rz_plane(self):
        geo = Geometry(beamline(), rz=True)
        ax = plot_2d(geo, units="cm")
        assert ax.get_ylabel() == "r (cm)"
        assert ax.get_ylim()[0] == 0
        ax = plot_2d(geo, mirror=True)
        assert ax.get_ylim()[0] < 0

    def test_color_by_voltage_adds_colorbar(self):
        ax = plot_2d(Geometry(beamline()), color_by="voltage", volt_dict={"b": -200})
        assert len(ax.figure.axes) == 2  # plot + colorbar
        assert ax.figure.axes[1].get_ylim() == pytest.approx((-200, 200))

    @pytest.mark.parametrize("plane", ["xz", "yz", "xy"])
    def test_planes(self, plane):
        ax = plot_2d(beamline(), plane=plane, position=0.005)
        assert len(ax.collections) > 0

    def test_dict_input(self):
        ax = plot_2d(
            {"one": CylinderZ(0.01, 0, 0.01), "two": Box(0, 1, 0, 1, 0, 1)},
            plane="xy",
            position=0.005,
            extent=(-0.02, 0.02, -0.02, 0.02),
        )
        assert set(legend_colors(ax)) == {"one", "two"}

    def test_unbounded_needs_extent(self):
        with pytest.raises(ValueError, match="unbounded"):
            plot_2d(Cylinder(0.01))
        ax = plot_2d(Cylinder(0.01), extent=(-0.1, 0.1, -0.02, 0.02))
        assert ax.get_legend() is None  # nothing named, nothing to label

    def test_invalid_arguments(self):
        with pytest.raises(ValueError, match="plane"):
            plot_2d(beamline(), plane="ab")
        with pytest.raises(ValueError, match="color_by"):
            plot_2d(beamline(), color_by="size")
        with pytest.raises(TypeError):
            plot_2d("not a geometry")


needs_pyvista = pytest.mark.skipif(
    importlib.util.find_spec("pyvista") is None, reason="pyvista not installed"
)


@needs_pyvista
class TestMeshes:
    def meshes(self, geometry, **kwargs):
        from warpx_geometry.viz import geometry_meshes

        return geometry_meshes(geometry, **kwargs)

    def test_cylinder_volume_and_area(self):
        ((part, mesh),) = self.meshes(CylinderZ(0.01, 0.0, 0.05), resolution=150)
        assert part.label is None
        r, length = 10.0, 50.0  # mm
        assert mesh.volume == pytest.approx(np.pi * r**2 * length, rel=0.01)
        area = 2 * np.pi * r * length + 2 * np.pi * r**2
        assert mesh.area == pytest.approx(area, rel=0.02)

    def test_clip_halves_the_volume(self):
        cyl = CylinderZ(0.01, 0.0, 0.05)
        full = self.meshes(cyl, resolution=120)[0][1].volume
        half = self.meshes(cyl, resolution=120, clip="y")[0][1].volume
        other = self.meshes(cyl, resolution=120, clip="-x")[0][1].volume
        assert half == pytest.approx(full / 2, rel=0.01)
        assert other == pytest.approx(full / 2, rel=0.01)

    def test_rz_geometry_is_revolved(self):
        geo = Geometry(CylinderZ_hollow(0.011, 0.009, 0.0, 0.01), rz=True)
        ((_, mesh),) = self.meshes(geo, resolution=150, units="m")
        expected = np.pi * (0.011**2 - 0.009**2) * 0.01
        assert mesh.volume == pytest.approx(expected, rel=0.03)

    def test_named_components(self):
        labels = [p.label for p, _ in self.meshes(beamline(), resolution=80)]
        assert labels == ["a", "b", None]


@needs_pyvista
def test_plot_3d_screenshot(tmp_path):
    from warpx_geometry.viz import plot_3d

    out = tmp_path / "geo.png"
    plotter = plot_3d(
        Geometry(beamline(), rz=True),
        clip="y",
        resolution=60,
        screenshot=out,
        window_size=(300, 200),
    )
    plotter.close()
    assert out.stat().st_size > 1000
