"""Tests for RZBBox, BBox.expanded, bboxes_overlap, and rz_bbox properties."""

import math

import pytest

from warpx_geometry import (
    BBox,
    Box,
    Cone,
    Cylinder,
    CylinderZ,
    CylinderZ_hollow,
    Diff,
    Intersection,
    RZBBox,
    Rotate,
    RoundedCylinderZ,
    RoundedCylinderZ_hollow,
    Scale,
    Torus,
    Translate,
    Union,
    bboxes_overlap,
)


# ---------------------------------------------------------------------------
# RZBBox basics
# ---------------------------------------------------------------------------


class TestRZBBox:
    def test_fields(self):
        bb = RZBBox(0.01, 0.05, -0.1, 0.1)
        assert bb.rmin == pytest.approx(0.01)
        assert bb.rmax == pytest.approx(0.05)
        assert bb.zmin == pytest.approx(-0.1)
        assert bb.zmax == pytest.approx(0.1)

    def test_rmin_clamped_to_zero(self):
        bb = RZBBox(-0.5, 0.05, -0.1, 0.1)
        assert bb.rmin == 0.0

    def test_expanded(self):
        bb = RZBBox(0.01, 0.05, -0.1, 0.1)
        exp = bb.expanded(0.005)
        assert exp.rmin == pytest.approx(0.005)
        assert exp.rmax == pytest.approx(0.055)
        assert exp.zmin == pytest.approx(-0.105)
        assert exp.zmax == pytest.approx(0.105)

    def test_expanded_clamps_rmin(self):
        bb = RZBBox(0.003, 0.05, -0.1, 0.1)
        exp = bb.expanded(0.01)  # would push rmin negative
        assert exp.rmin == 0.0

    def test_expanded_does_not_mutate(self):
        bb = RZBBox(0.01, 0.05, -0.1, 0.1)
        _ = bb.expanded(0.005)
        assert bb.rmin == pytest.approx(0.01)
        assert bb.zmin == pytest.approx(-0.1)

    def test_repr(self):
        bb = RZBBox(0.01, 0.05, -0.1, 0.1)
        r = repr(bb)
        assert "RZBBox" in r
        assert "0.01" in r


# ---------------------------------------------------------------------------
# BBox.expanded
# ---------------------------------------------------------------------------


class TestBBoxExpanded:
    def test_expanded_enlarges_all_dims(self):
        bb = BBox(-0.1, 0.1, -0.2, 0.2, -0.3, 0.3)
        exp = bb.expanded(0.05)
        assert exp.xmin == pytest.approx(-0.15)
        assert exp.xmax == pytest.approx(0.15)
        assert exp.ymin == pytest.approx(-0.25)
        assert exp.ymax == pytest.approx(0.25)
        assert exp.zmin == pytest.approx(-0.35)
        assert exp.zmax == pytest.approx(0.35)

    def test_expanded_does_not_mutate(self):
        bb = BBox(-0.1, 0.1, -0.2, 0.2, -0.3, 0.3)
        _ = bb.expanded(0.05)
        assert bb.xmin == pytest.approx(-0.1)


# ---------------------------------------------------------------------------
# bboxes_overlap
# ---------------------------------------------------------------------------


class TestBBoxesOverlap:
    def test_rz_overlapping(self):
        a = RZBBox(0.0, 0.05, -0.1, 0.1)
        b = RZBBox(0.03, 0.08, 0.0, 0.2)
        assert bboxes_overlap(a, b) is True

    def test_rz_non_overlapping_r(self):
        a = RZBBox(0.0, 0.03, -0.1, 0.1)
        b = RZBBox(0.05, 0.10, -0.1, 0.1)
        assert bboxes_overlap(a, b) is False

    def test_rz_non_overlapping_z(self):
        a = RZBBox(0.0, 0.05, -0.2, -0.1)
        b = RZBBox(0.0, 0.05, 0.1, 0.2)
        assert bboxes_overlap(a, b) is False

    def test_rz_touching_is_not_overlap(self):
        # Touching at r=0.05 — strict inequality means touching = not overlapping
        a = RZBBox(0.0, 0.05, -0.1, 0.1)
        b = RZBBox(0.05, 0.10, -0.1, 0.1)
        assert bboxes_overlap(a, b) is False

    def test_rz_tolerance_shrinks_boxes(self):
        # With positive tolerance, boxes must overlap by more than tol
        a = RZBBox(0.0, 0.050, -0.1, 0.1)
        b = RZBBox(0.049, 0.10, -0.1, 0.1)  # 1mm overlap
        assert bboxes_overlap(a, b, tolerance=0.0) is True
        assert bboxes_overlap(a, b, tolerance=0.002) is False  # overlap < tol

    def test_3d_overlapping(self):
        a = BBox(-0.1, 0.1, -0.1, 0.1, -0.1, 0.1)
        b = BBox(0.0, 0.2, 0.0, 0.2, 0.0, 0.2)
        assert bboxes_overlap(a, b) is True

    def test_3d_non_overlapping(self):
        a = BBox(-0.1, 0.0, -0.1, 0.1, -0.1, 0.1)
        b = BBox(0.05, 0.2, -0.1, 0.1, -0.1, 0.1)
        assert bboxes_overlap(a, b) is False

    def test_type_mismatch_raises(self):
        a = RZBBox(0.0, 0.05, -0.1, 0.1)
        b = BBox(-0.1, 0.1, -0.1, 0.1, -0.1, 0.1)
        with pytest.raises(TypeError):
            bboxes_overlap(a, b)


# ---------------------------------------------------------------------------
# rz_bbox on leaf shape classes
# ---------------------------------------------------------------------------


class TestRZBBoxCylinder:
    def test_cylinder_rz_bbox(self):
        cyl = Cylinder(radius=0.01)
        bb = cyl.rz_bbox
        assert bb.rmin == 0.0
        assert bb.rmax == pytest.approx(0.01)
        assert bb.zmin == -math.inf
        assert bb.zmax == math.inf


class TestRZBBoxCylinderZ:
    def test_cylinderz_rz_bbox(self):
        cyl = CylinderZ(radius=0.01, zmin=-0.05, zmax=0.05)
        bb = cyl.rz_bbox
        assert bb.rmin == 0.0
        assert bb.rmax == pytest.approx(0.01)
        assert bb.zmin == pytest.approx(-0.05)
        assert bb.zmax == pytest.approx(0.05)


class TestRZBBoxCylinderZHollow:
    def test_hollow_rz_bbox(self):
        cyl = CylinderZ_hollow(radius_outer=0.011, radius_inner=0.010, zmin=0.0, zmax=0.1)
        bb = cyl.rz_bbox
        assert bb.rmin == pytest.approx(0.010)
        assert bb.rmax == pytest.approx(0.011)
        assert bb.zmin == pytest.approx(0.0)
        assert bb.zmax == pytest.approx(0.1)


class TestRZBBoxBox:
    def test_box_rz_bbox(self):
        box = Box(xmin=0.01, xmax=0.05, ymin=-0.05, ymax=0.05, zmin=-0.1, zmax=0.1)
        bb = box.rz_bbox
        assert bb.rmin == pytest.approx(0.01)
        assert bb.rmax == pytest.approx(0.05)
        assert bb.zmin == pytest.approx(-0.1)
        assert bb.zmax == pytest.approx(0.1)

    def test_box_negative_xmin_clamped(self):
        box = Box(xmin=-0.05, xmax=0.05, ymin=-0.05, ymax=0.05, zmin=-0.1, zmax=0.1)
        bb = box.rz_bbox
        assert bb.rmin == 0.0
        assert bb.rmax == pytest.approx(0.05)


class TestRZBBoxTorus:
    def test_torus_rz_bbox(self):
        t = Torus(major_radius=0.010, minor_radius=0.001, z_center=0.1)
        bb = t.rz_bbox
        assert bb.rmin == pytest.approx(0.009)
        assert bb.rmax == pytest.approx(0.011)
        assert bb.zmin == pytest.approx(0.099)
        assert bb.zmax == pytest.approx(0.101)


class TestRZBBoxCone:
    def test_cone_rz_bbox(self):
        cone = Cone(z1=0.0, z2=0.1, r1=0.010, r2=0.005)
        bb = cone.rz_bbox
        assert bb.rmin == 0.0
        assert bb.rmax == pytest.approx(0.010)
        assert bb.zmin == pytest.approx(0.0)
        assert bb.zmax == pytest.approx(0.1)

    def test_cone_wider_at_end(self):
        cone = Cone(z1=0.0, z2=0.1, r1=0.005, r2=0.020)
        bb = cone.rz_bbox
        assert bb.rmax == pytest.approx(0.020)


# ---------------------------------------------------------------------------
# rz_bbox on compound/structural classes
# ---------------------------------------------------------------------------


class TestRZBBoxUnion:
    def test_union_spans_both(self):
        a = CylinderZ(radius=0.01, zmin=-0.05, zmax=0.0)
        b = CylinderZ(radius=0.008, zmin=0.0, zmax=0.05)
        u = Union(a, b)
        bb = u.rz_bbox
        assert bb.rmin == 0.0
        assert bb.rmax == pytest.approx(0.01)
        assert bb.zmin == pytest.approx(-0.05)
        assert bb.zmax == pytest.approx(0.05)


class TestRZBBoxDiff:
    def test_diff_is_conservative(self):
        # Diff.rz_bbox is the minuend's bbox (conservative)
        a = CylinderZ_hollow(radius_outer=0.011, radius_inner=0.010, zmin=0.0, zmax=0.1)
        b = CylinderZ(radius=0.005, zmin=0.0, zmax=0.1)
        d = Diff(a, b)
        bb = d.rz_bbox
        # Should be a's rz_bbox
        assert bb.rmin == pytest.approx(a.rz_bbox.rmin)
        assert bb.rmax == pytest.approx(a.rz_bbox.rmax)


class TestRZBBoxIntersection:
    def test_intersection_rz_bbox(self):
        a = CylinderZ(radius=0.05, zmin=-0.1, zmax=0.1)
        b = Box(xmin=0.0, xmax=0.03, ymin=-0.03, ymax=0.03, zmin=-0.05, zmax=0.05)
        i = Intersection(a, b)
        bb = i.rz_bbox
        assert bb.rmin == pytest.approx(0.0)
        assert bb.rmax == pytest.approx(0.03)
        assert bb.zmin == pytest.approx(-0.05)
        assert bb.zmax == pytest.approx(0.05)


class TestRZBBoxTranslate:
    def test_translate_shifts_z(self):
        cyl = CylinderZ_hollow(radius_outer=0.011, radius_inner=0.010, zmin=0.0, zmax=0.01)
        tr = Translate(cyl, x=0, y=0, z=0.05)
        bb = tr.rz_bbox
        assert bb.zmin == pytest.approx(0.05)
        assert bb.zmax == pytest.approx(0.06)
        assert bb.rmin == pytest.approx(0.010)
        assert bb.rmax == pytest.approx(0.011)


class TestRZBBoxRoundedCylinderZ:
    def test_rounded_cyl_rz_bbox(self):
        cyl = RoundedCylinderZ(radius=0.010, zmin=0.0, zmax=0.05, fillet_radius=0.001)
        bb = cyl.rz_bbox
        assert bb.rmin == 0.0
        assert bb.rmax == pytest.approx(0.010)
        assert bb.zmin == pytest.approx(0.0)
        assert bb.zmax == pytest.approx(0.05)


class TestRZBBoxRoundedCylinderZHollow:
    def test_rounded_hollow_cyl_rz_bbox(self):
        cyl = RoundedCylinderZ_hollow(
            radius_outer=0.011, radius_inner=0.010,
            zmin=0.0, zmax=0.05, fillet_radius=0.0005
        )
        bb = cyl.rz_bbox
        assert bb.rmin == pytest.approx(0.010)
        assert bb.rmax == pytest.approx(0.011)
        assert bb.zmin == pytest.approx(0.0)
        assert bb.zmax == pytest.approx(0.05)
