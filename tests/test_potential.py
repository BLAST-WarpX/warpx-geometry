"""Tests for name/default_voltage, collect_named, and to_potential_expr."""

from warpx_geometry import (
    CylinderZ_hollow,
    Geometry,
    Translate,
    Union,
)
from warpx_geometry.complex_geometry import Einzellens

# ---------------------------------------------------------------------------
# name and default_voltage on shape classes
# ---------------------------------------------------------------------------


class TestNameDefaultVoltage:
    def test_unnamed_by_default(self):
        c = CylinderZ_hollow(
            radius_outer=0.011, radius_inner=0.010, zmin=0.0, zmax=0.01
        )
        assert c.name is None
        assert c.default_voltage == 0

    def test_named_conductor(self):
        c = CylinderZ_hollow(
            radius_outer=0.011,
            radius_inner=0.010,
            zmin=0.0,
            zmax=0.01,
            name="ring_0",
            default_voltage=1600,
        )
        assert c.name == "ring_0"
        assert c.default_voltage == 1600

    def test_string_default_voltage(self):
        c = CylinderZ_hollow(
            radius_outer=0.011,
            radius_inner=0.010,
            zmin=0.0,
            zmax=0.01,
            name="ring_0",
            default_voltage="1600*pulse(t)",
        )
        assert c.default_voltage == "1600*pulse(t)"


# ---------------------------------------------------------------------------
# collect_named traversal
# ---------------------------------------------------------------------------


class TestCollectNamed:
    def test_unnamed_not_collected(self):
        c = CylinderZ_hollow(
            radius_outer=0.011, radius_inner=0.010, zmin=0.0, zmax=0.01
        )
        reg = {}
        c.collect_named(reg)
        assert reg == {}

    def test_named_collected(self):
        c = CylinderZ_hollow(
            radius_outer=0.011, radius_inner=0.010, zmin=0.0, zmax=0.01, name="ring_0"
        )
        reg = {}
        c.collect_named(reg)
        assert "ring_0" in reg
        assert reg["ring_0"] is c

    def test_union_recurses(self):
        a = CylinderZ_hollow(
            radius_outer=0.011, radius_inner=0.010, zmin=0.0, zmax=0.01, name="a"
        )
        b = CylinderZ_hollow(
            radius_outer=0.011, radius_inner=0.010, zmin=0.02, zmax=0.03, name="b"
        )
        u = Union(a, b)
        reg = {}
        u.collect_named(reg)
        assert "a" in reg
        assert "b" in reg

    def test_unnamed_inside_union_skipped(self):
        named = CylinderZ_hollow(
            radius_outer=0.011, radius_inner=0.010, zmin=0.0, zmax=0.01, name="r"
        )
        unnamed = CylinderZ_hollow(
            radius_outer=0.011, radius_inner=0.010, zmin=0.02, zmax=0.03
        )
        u = Union(named, unnamed)
        reg = {}
        u.collect_named(reg)
        assert list(reg.keys()) == ["r"]

    def test_translate_recurses(self):
        c = CylinderZ_hollow(
            radius_outer=0.011, radius_inner=0.010, zmin=0.0, zmax=0.01, name="c"
        )
        tr = Translate(c, x=0, y=0, z=0.1)
        reg = {}
        tr.collect_named(reg)
        assert "c" in reg

    def test_einzellens_named(self):
        lens = Einzellens(
            radius=0.015, thickness=0.002, length=0.02, gap=0.01, name="lens"
        )
        reg = {}
        lens.collect_named(reg)
        assert "lens" in reg
        assert reg["lens"] is lens


# ---------------------------------------------------------------------------
# Geometry.conductors dict
# ---------------------------------------------------------------------------


class TestGeometryConductors:
    def test_conductors_populated(self):
        a = CylinderZ_hollow(
            radius_outer=0.011, radius_inner=0.010, zmin=0.0, zmax=0.01, name="ring_0"
        )
        b = CylinderZ_hollow(
            radius_outer=0.011, radius_inner=0.010, zmin=0.05, zmax=0.06, name="ring_1"
        )
        geo = Geometry(Union(a, b), rz=True)
        assert "ring_0" in geo.conductors
        assert "ring_1" in geo.conductors

    def test_unnamed_not_in_conductors(self):
        a = CylinderZ_hollow(
            radius_outer=0.011, radius_inner=0.010, zmin=0.0, zmax=0.01, name="ring_0"
        )
        b = CylinderZ_hollow(
            radius_outer=0.011, radius_inner=0.010, zmin=0.05, zmax=0.06
        )
        geo = Geometry(Union(a, b), rz=True)
        assert list(geo.conductors.keys()) == ["ring_0"]


# ---------------------------------------------------------------------------
# to_potential_expr on a single conductor
# ---------------------------------------------------------------------------


class TestToPotentialExprSingle:
    def test_rz_region_contains_voltage(self):
        c = CylinderZ_hollow(
            radius_outer=0.067,
            radius_inner=0.051,
            zmin=-0.001,
            zmax=0.001,
            name="ring_0",
        )
        geo = Geometry(c, rz=True)
        expr = geo.to_potential_expr({"ring_0": 1600})
        assert "1600" in expr
        assert "0.051" in expr
        assert "0.067" in expr

    def test_zero_voltage_returns_zero(self):
        c = CylinderZ_hollow(
            radius_outer=0.067,
            radius_inner=0.051,
            zmin=-0.001,
            zmax=0.001,
            name="ring_0",
        )
        geo = Geometry(c, rz=True)
        expr = geo.to_potential_expr({"ring_0": 0})
        assert expr == "0"

    def test_default_voltage_used_when_missing(self):
        c = CylinderZ_hollow(
            radius_outer=0.067,
            radius_inner=0.051,
            zmin=-0.001,
            zmax=0.001,
            name="ring_0",
            default_voltage=800,
        )
        geo = Geometry(c, rz=True)
        expr = geo.to_potential_expr({})  # no override
        assert "800" in expr

    def test_string_voltage_passes_through(self):
        c = CylinderZ_hollow(
            radius_outer=0.067,
            radius_inner=0.051,
            zmin=-0.001,
            zmax=0.001,
            name="ring_0",
        )
        geo = Geometry(c, rz=True)
        expr = geo.to_potential_expr({"ring_0": "1600*pulse(t)"})
        assert "1600*pulse(t)" in expr

    def test_empty_conductors_returns_zero(self):
        c = CylinderZ_hollow(
            radius_outer=0.067, radius_inner=0.051, zmin=-0.001, zmax=0.001
        )
        geo = Geometry(c, rz=True)
        expr = geo.to_potential_expr({"ring_0": 1600})  # name doesn't exist
        assert expr == "0"


# ---------------------------------------------------------------------------
# Two non-overlapping conductors → "+" combination
# ---------------------------------------------------------------------------


class TestToPotentialExprNonOverlapping:
    def test_plus_combination(self):
        a = CylinderZ_hollow(
            radius_outer=0.067,
            radius_inner=0.051,
            zmin=-0.001,
            zmax=0.001,
            name="ring_0",
        )
        b = CylinderZ_hollow(
            radius_outer=0.067, radius_inner=0.051, zmin=0.05, zmax=0.06, name="ring_1"
        )
        geo = Geometry(Union(a, b), rz=True)
        expr = geo.to_potential_expr({"ring_0": 1600, "ring_1": 800})
        # Non-overlapping z ranges → use + not max()
        assert " + " in expr
        assert "max(" not in expr
        assert "1600" in expr
        assert "800" in expr


# ---------------------------------------------------------------------------
# Two overlapping conductors → max() combination
# ---------------------------------------------------------------------------


class TestToPotentialExprOverlapping:
    def test_max_combination(self):
        a = CylinderZ_hollow(
            radius_outer=0.067, radius_inner=0.051, zmin=-0.005, zmax=0.005, name="a"
        )
        b = CylinderZ_hollow(
            radius_outer=0.090, radius_inner=0.068, zmin=-0.005, zmax=0.005, name="b"
        )
        # These share the same z range; with margin the bboxes overlap in z
        geo = Geometry(Union(a, b), rz=True)
        expr = geo.to_potential_expr({"a": 1000, "b": 500}, margin=0.001)
        assert "max(" in expr


# ---------------------------------------------------------------------------
# Margin expands the region
# ---------------------------------------------------------------------------


class TestToPotentialExprMargin:
    def test_margin_expands_region(self):
        c = CylinderZ_hollow(
            radius_outer=0.067, radius_inner=0.051, zmin=0.0, zmax=0.001, name="r"
        )
        geo = Geometry(c, rz=True)
        expr_no_margin = geo.to_potential_expr({"r": 1600}, margin=0)
        expr_margin = geo.to_potential_expr({"r": 1600}, margin=0.002)
        # The z bounds should differ
        assert expr_no_margin != expr_margin
        # The margin expression should have larger z extent
        assert "0.003" in expr_margin  # zmax + margin = 0.001 + 0.002
