"""Tests for build_expr(rz) and Geometry(rz=False/True)."""

import numpy as np
import pytest

from warpx_geometry import (
    Box,
    Cone,
    Cylinder,
    CylinderZ,
    CylinderZ_hollow,
    Diff,
    Geometry,
    Intersection,
    Torus,
    Translate,
    Union,
)


# ---------------------------------------------------------------------------
# Regression: build_expr(rz=False) must match __str__
# ---------------------------------------------------------------------------


class TestBuildExprFalseMatchesStr:
    """build_expr(rz=False) must produce exactly the same string as str()."""

    def test_cylinder(self):
        c = Cylinder(radius=0.01)
        assert c.build_expr(rz=False) == str(c)

    def test_cylinderz(self):
        c = CylinderZ(radius=0.01, zmin=-0.05, zmax=0.05)
        assert c.build_expr(rz=False) == str(c)

    def test_cylinderz_hollow(self):
        c = CylinderZ_hollow(radius_outer=0.011, radius_inner=0.010, zmin=0.0, zmax=0.1)
        assert c.build_expr(rz=False) == str(c)

    def test_box(self):
        b = Box(xmin=-0.01, xmax=0.01, ymin=-0.01, ymax=0.01, zmin=-0.05, zmax=0.05)
        assert b.build_expr(rz=False) == str(b)

    def test_torus(self):
        t = Torus(major_radius=0.01, minor_radius=0.001, z_center=0.1)
        assert t.build_expr(rz=False) == str(t)

    def test_cone(self):
        c = Cone(z1=0.0, z2=0.1, r1=0.01, r2=0.005)
        assert c.build_expr(rz=False) == str(c)

    def test_union(self):
        a = CylinderZ(radius=0.01, zmin=-0.05, zmax=0.0)
        b = CylinderZ(radius=0.008, zmin=0.0, zmax=0.05)
        u = Union(a, b)
        assert u.build_expr(rz=False) == str(u)

    def test_diff(self):
        a = CylinderZ(radius=0.05, zmin=-0.1, zmax=0.1)
        b = CylinderZ(radius=0.04, zmin=-0.1, zmax=0.1)
        d = Diff(a, b)
        assert d.build_expr(rz=False) == str(d)

    def test_intersection(self):
        a = Cylinder(radius=0.05)
        b = Box(xmin=-0.03, xmax=0.03, ymin=-0.03, ymax=0.03, zmin=-0.1, zmax=0.1)
        i = Intersection(a, b)
        assert i.build_expr(rz=False) == str(i)

    def test_translate(self):
        c = CylinderZ(radius=0.01, zmin=-0.05, zmax=0.05)
        t = Translate(c, x=0, y=0, z=0.1)
        assert t.build_expr(rz=False) == str(t)

    def test_geometry_str_unchanged(self):
        cyl = Cylinder(radius=0.01)
        geo = Geometry(cyl)  # rz=False by default
        assert str(geo) == geo.build_eb_expr()
        assert "-0.5" in str(geo)


# ---------------------------------------------------------------------------
# RZ-optimized expressions: no y**2, no y bounds
# ---------------------------------------------------------------------------


class TestBuildExprRZ:
    def test_cylinder_drops_y2(self):
        c = Cylinder(radius=0.01)
        expr = c.build_expr(rz=True)
        assert "y" not in expr
        assert "x**2" in expr

    def test_box_drops_y_bounds(self):
        b = Box(xmin=-0.01, xmax=0.01, ymin=-0.01, ymax=0.01, zmin=-0.05, zmax=0.05)
        expr = b.build_expr(rz=True)
        assert "y" not in expr
        assert "z" in expr
        assert "x" in expr

    def test_cylinderz_hollow_flat_expr(self):
        c = CylinderZ_hollow(radius_outer=0.011, radius_inner=0.010, zmin=0.0, zmax=0.1)
        expr = c.build_expr(rz=True)
        # No nesting through Diff/CylinderZ; direct annular region
        assert "if(" not in expr
        assert "0.01" in expr
        assert "0.011" in expr
        assert "0.0" in expr
        assert "0.1" in expr
        assert "y" not in expr

    def test_cylinderz_hollow_is_annular_ring(self):
        """Verify the RZ expression evaluates correctly via Geometry."""
        c = CylinderZ_hollow(radius_outer=0.011, radius_inner=0.010, zmin=0.0, zmax=0.1)
        geo = Geometry(c, rz=True)
        # Point in annular wall
        val = geo.eval(x=0.0105, y=0.0, z=0.05)
        assert val == 1.0
        # Point on axis (inside bore)
        val = geo.eval(x=0.0, y=0.0, z=0.05)
        assert val == 0.0

    def test_union_recurses_rz(self):
        a = Cylinder(radius=0.01)
        b = Cylinder(radius=0.02)
        u = Union(a, b)
        expr_rz = u.build_expr(rz=True)
        expr_3d = u.build_expr(rz=False)
        # RZ form should be shorter (no y**2)
        assert "y" not in expr_rz
        assert "y" in expr_3d

    def test_translate_recurses_rz(self):
        c = CylinderZ_hollow(radius_outer=0.011, radius_inner=0.010, zmin=0.0, zmax=0.01)
        t = Translate(c, x=0, y=0, z=0.05)
        expr = t.build_expr(rz=True)
        # Should use the hollow's direct RZ expression, not the Diff nesting
        assert "if(" not in expr
        assert "y" not in expr


# ---------------------------------------------------------------------------
# Geometry(rz=True) EB expression
# ---------------------------------------------------------------------------


class TestGeometryRZ:
    def test_geometry_rz_false_default(self):
        cyl = Cylinder(radius=0.01)
        geo = Geometry(cyl)
        assert geo.rz is False

    def test_geometry_rz_true(self):
        cyl = Cylinder(radius=0.01)
        geo = Geometry(cyl, rz=True)
        assert geo.rz is True
        expr = str(geo)
        assert "-0.5" in expr
        assert "y" not in expr

    def test_geometry_rz_eb_string(self):
        c = CylinderZ_hollow(radius_outer=0.067, radius_inner=0.051, zmin=-0.01, zmax=0.01)
        geo = Geometry(c, rz=True)
        expr = geo.build_eb_expr()
        assert "-0.5" in expr
        assert "0.051" in expr
        assert "0.067" in expr
        assert "y" not in expr

    def test_geometry_rz_bbox(self):
        c = CylinderZ_hollow(radius_outer=0.011, radius_inner=0.010, zmin=0.0, zmax=0.1)
        geo = Geometry(c, rz=True)
        bb = geo.rz_bbox
        assert bb.rmin == pytest.approx(0.010)
        assert bb.rmax == pytest.approx(0.011)
