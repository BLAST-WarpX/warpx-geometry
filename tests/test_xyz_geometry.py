"""Tests for XYZ (Cartesian) geometry objects."""

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
    Rotate,
    RoundedCylinderZ,
    RoundedCylinderZ_hollow,
    Scale,
    Torus,
    Translate,
    Union,
    scale_around,
    scale_to_bbox_center,
)


class TestBasicShapes:
    """Test basic 3D shapes in Cartesian coordinates."""

    def test_cylinder_center(self):
        """Test that point at center of cylinder is inside."""
        cyl = Cylinder(radius=0.01)  # 10mm radius
        # Point on axis should be inside
        val = cyl.eval(x=0.0, y=0.0, z=0.0)
        assert val == 1.0

    def test_cylinder_outside(self):
        """Test that point outside cylinder is outside."""
        cyl = Cylinder(radius=0.01)
        # Point far from axis should be outside
        val = cyl.eval(x=0.02, y=0.0, z=0.0)
        assert val == 0.0

    def test_cylinder_edge(self):
        """Test cylinder boundary."""
        cyl = Cylinder(radius=0.01)
        # Point just inside radius
        r = 0.009
        val = cyl.eval(x=r, y=0.0, z=0.0)
        assert val == 1.0

    def test_cylinder_z(self):
        """Test finite cylinder along z-axis."""
        cyl = CylinderZ(radius=0.01, zmin=0.0, zmax=0.1)
        # Inside
        val = cyl.eval(x=0.005, y=0.0, z=0.05)
        assert val == 1.0
        # Outside in z
        val = cyl.eval(x=0.005, y=0.0, z=0.15)
        assert val == 0.0
        # Outside in r
        val = cyl.eval(x=0.02, y=0.0, z=0.05)
        assert val == 0.0

    def test_hollow_cylinder(self):
        """Test hollow cylinder."""
        cyl = CylinderZ_hollow(
            radius_outer=0.011, radius_inner=0.010, zmin=0.0, zmax=0.1
        )
        # Inside wall (between inner and outer radius)
        val = cyl.eval(x=0.0105, y=0.0, z=0.05)
        assert val == 1.0
        # Inside bore (should be empty)
        val = cyl.eval(x=0.005, y=0.0, z=0.05)
        assert val == 0.0
        # Outside
        val = cyl.eval(x=0.02, y=0.0, z=0.05)
        assert val == 0.0

    def test_box(self):
        """Test box geometry."""
        box = Box(xmin=-0.01, xmax=0.01, ymin=-0.01, ymax=0.01, zmin=0.0, zmax=0.1)
        # Inside
        val = box.eval(x=0.0, y=0.0, z=0.05)
        assert val == 1.0
        # Outside in x
        val = box.eval(x=0.02, y=0.0, z=0.05)
        assert val == 0.0
        # Outside in z
        val = box.eval(x=0.0, y=0.0, z=0.15)
        assert val == 0.0

    def test_torus(self):
        """Test torus geometry."""
        torus = Torus(major_radius=0.010, minor_radius=0.001, z_center=0.1)
        # Point on major circle, at tube center
        val = torus.eval(x=0.010, y=0.0, z=0.1)
        assert val == 1.0
        # Point at origin (center of torus) should be outside
        val = torus.eval(x=0.0, y=0.0, z=0.1)
        assert val == 0.0

    def test_cone(self):
        """Test cone geometry."""
        cone = Cone(z1=0.0, z2=0.1, r1=0.010, r2=0.005)
        # Point at wide end
        val = cone.eval(x=0.009, y=0.0, z=0.01)
        assert val == 1.0
        # Point at narrow end
        val = cone.eval(x=0.004, y=0.0, z=0.09)
        assert val == 1.0
        # Point outside cone at wide end
        val = cone.eval(x=0.012, y=0.0, z=0.01)
        assert val == 0.0
        # Point outside axial range
        val = cone.eval(x=0.005, y=0.0, z=0.15)
        assert val == 0.0


class TestBooleanOperations:
    """Test boolean operations on geometries."""

    def test_union(self):
        """Test union of two cylinders."""
        cyl1 = CylinderZ(radius=0.01, zmin=0.0, zmax=0.05)
        cyl2 = CylinderZ(radius=0.01, zmin=0.045, zmax=0.10)
        combined = Union(cyl1, cyl2)
        # Point in first cylinder
        val = combined.eval(x=0.005, y=0.0, z=0.02)
        assert val == 1.0
        # Point in second cylinder
        val = combined.eval(x=0.005, y=0.0, z=0.07)
        assert val == 1.0
        # Point in overlap
        val = combined.eval(x=0.005, y=0.0, z=0.047)
        assert val == 1.0
        # Point outside both
        val = combined.eval(x=0.02, y=0.0, z=0.05)
        assert val == 0.0

    def test_union_operator(self):
        """Test union using + operator."""
        cyl1 = CylinderZ(radius=0.01, zmin=0.0, zmax=0.05)
        cyl2 = CylinderZ(radius=0.01, zmin=0.045, zmax=0.10)
        combined = cyl1 + cyl2
        # Should behave like Union
        val = combined.eval(x=0.005, y=0.0, z=0.02)
        assert val == 1.0

    def test_difference(self):
        """Test difference operation."""
        outer = CylinderZ(radius=0.011, zmin=0.0, zmax=0.1)
        inner = CylinderZ(radius=0.010, zmin=-0.1, zmax=0.2)
        hollow = Diff(outer, inner)
        # Point in wall
        val = hollow.eval(x=0.0105, y=0.0, z=0.05)
        assert val == 1.0
        # Point in bore (removed)
        val = hollow.eval(x=0.005, y=0.0, z=0.05)
        assert val == 0.0

    def test_difference_operator(self):
        """Test difference using - operator."""
        outer = CylinderZ(radius=0.011, zmin=0.0, zmax=0.1)
        inner = CylinderZ(radius=0.010, zmin=-0.1, zmax=0.2)
        hollow = outer - inner
        # Should behave like Diff
        val = hollow.eval(x=0.0105, y=0.0, z=0.05)
        assert val == 1.0

    def test_intersection(self):
        """Test intersection operation."""
        cyl = Cylinder(radius=0.01)
        box = Box(xmin=-0.005, xmax=0.005, ymin=-0.02, ymax=0.02, zmin=0.0, zmax=0.1)
        combined = Intersection(cyl, box)
        # Point inside both
        val = combined.eval(x=0.004, y=0.0, z=0.05)
        assert val == 1.0
        # Point inside cylinder but outside box
        val = combined.eval(x=0.008, y=0.0, z=0.05)
        assert val == 0.0


class TestTransformations:
    """Test geometric transformations."""

    def test_translate_x(self):
        """Test translation in x direction."""
        cyl = Cylinder(radius=0.01)
        # Translate 0.02m in x
        cyl_trans = Translate(cyl, x=0.02)
        # Original center should now be outside
        val = cyl_trans.eval(x=0.0, y=0.0, z=0.0)
        assert val == 0.0
        # New center should be inside
        val = cyl_trans.eval(x=0.02, y=0.0, z=0.0)
        assert val == 1.0

    def test_translate_xyz(self):
        """Test translation in all directions."""
        cyl = Cylinder(radius=0.01)
        cyl_trans = Translate(cyl, x=0.01, y=0.02, z=0.0)
        # Check translated position
        val = cyl_trans.eval(x=0.01, y=0.02, z=0.0)
        assert val == 1.0
        # Original center should be outside
        val = cyl_trans.eval(x=0.0, y=0.0, z=0.0)
        assert val == 0.0


class TestAdvancedShapes:
    """Test advanced composite shapes."""

    def test_rounded_cylinder(self):
        """Test rounded cylinder with fillets."""
        cyl = RoundedCylinderZ(radius=0.010, zmin=0.0, zmax=0.05, fillet_radius=0.001)
        # Center should be inside
        val = cyl.eval(x=0.005, y=0.0, z=0.025)
        assert val == 1.0
        # Point at edge of fillet should be inside
        # The fillet is a torus, so we need a point that's in the rounded part
        val = cyl.eval(x=0.009, y=0.0, z=0.001)
        assert val == 1.0

    def test_rounded_hollow_cylinder(self):
        """Test hollow cylinder with fillets."""
        cyl = RoundedCylinderZ_hollow(
            radius_outer=0.011,
            radius_inner=0.010,
            zmin=0.0,
            zmax=0.05,
            fillet_radius=0.0005,
        )
        # Point in wall
        val = cyl.eval(x=0.0105, y=0.0, z=0.025)
        assert val == 1.0
        # Point in bore should be empty
        val = cyl.eval(x=0.005, y=0.0, z=0.025)
        assert val == 0.0


class TestGeometryWrapper:
    """Test the Geometry wrapper class."""

    def test_geometry_string(self):
        """Test that Geometry produces proper WarpX format."""
        cyl = Cylinder(radius=0.01)
        geom = Geometry(cyl)
        # String is a signed function: > 0 inside, < 0 outside
        geom_str = str(geom)
        assert geom_str == "(0.01-sqrt(x**2 + y**2))"

    def test_geometry_eval(self):
        """Test that Geometry eval works correctly."""
        cyl = Cylinder(radius=0.01)
        geom = Geometry(cyl)
        # Inside
        val = geom.eval(x=0.005, y=0.0, z=0.0)
        assert val == 1.0
        # Outside
        val = geom.eval(x=0.02, y=0.0, z=0.0)
        assert val == 0.0


class TestBBox:
    """Test bounding box property."""

    def test_cylinder_bbox_infinite_z(self):
        cyl = Cylinder(radius=0.01)
        bb = cyl.bbox
        assert bb.xmin == -0.01 and bb.xmax == 0.01
        assert bb.ymin == -0.01 and bb.ymax == 0.01
        assert bb.zmin == -np.inf and bb.zmax == np.inf

    def test_cylinderz_bbox(self):
        cyl = CylinderZ(radius=0.01, zmin=0.0, zmax=0.1)
        bb = cyl.bbox
        assert bb.xmin == pytest.approx(-0.01)
        assert bb.xmax == pytest.approx(0.01)
        assert bb.zmin == pytest.approx(0.0)
        assert bb.zmax == pytest.approx(0.1)

    def test_box_bbox(self):
        box = Box(xmin=-0.05, xmax=0.05, ymin=-0.03, ymax=0.03, zmin=0.0, zmax=0.2)
        bb = box.bbox
        assert bb.xmin == -0.05 and bb.xmax == 0.05
        assert bb.ymin == -0.03 and bb.ymax == 0.03
        assert bb.zmin == 0.0 and bb.zmax == 0.2

    def test_bbox_center(self):
        cyl = CylinderZ(radius=0.01, zmin=0.0, zmax=0.1)
        bb = cyl.bbox
        assert bb.cx == pytest.approx(0.0)
        assert bb.cy == pytest.approx(0.0)
        assert bb.cz == pytest.approx(0.05)

    def test_bbox_size(self):
        box = Box(xmin=-0.01, xmax=0.01, ymin=-0.02, ymax=0.02, zmin=0.0, zmax=0.1)
        sz = box.bbox.size
        assert sz == pytest.approx((0.02, 0.04, 0.1))

    def test_translate_bbox(self):
        cyl = CylinderZ(radius=0.01, zmin=0.0, zmax=0.1)
        moved = Translate(cyl, z=0.05)
        bb = moved.bbox
        assert bb.zmin == pytest.approx(0.05)
        assert bb.zmax == pytest.approx(0.15)

    def test_union_bbox(self):
        cyl1 = CylinderZ(radius=0.01, zmin=0.0, zmax=0.05)
        cyl2 = CylinderZ(radius=0.01, zmin=0.06, zmax=0.1)
        combined = Union(cyl1, cyl2)
        bb = combined.bbox
        assert bb.zmin == pytest.approx(0.0)
        assert bb.zmax == pytest.approx(0.1)

    def test_torus_bbox(self):
        torus = Torus(major_radius=0.01, minor_radius=0.001, z_center=0.05)
        bb = torus.bbox
        assert bb.xmin == pytest.approx(-0.011)
        assert bb.zmin == pytest.approx(0.049)
        assert bb.zmax == pytest.approx(0.051)

    def test_cone_bbox(self):
        cone = Cone(z1=0.0, z2=0.1, r1=0.01, r2=0.005)
        bb = cone.bbox
        assert bb.xmin == pytest.approx(-0.01)
        assert bb.xmax == pytest.approx(0.01)
        assert bb.zmin == pytest.approx(0.0)
        assert bb.zmax == pytest.approx(0.1)


class TestRepr:
    def test_shape(self):
        assert repr(Cylinder(0.01)) == "Cylinder(radius=0.01)"

    def test_name_and_voltage_are_shown_when_set(self):
        r = repr(Cylinder(0.01, name="c", default_voltage=5))
        assert r == "Cylinder(name='c', default_voltage=5, radius=0.01)"

    def test_composite_shows_its_parts(self):
        assert "Box(" in repr(Translate(Box(0, 1, 0, 1, 0, 1), x=1))

    def test_geometry(self):
        assert repr(Geometry(Cylinder(1), rz=True)) == (
            "Geometry(Cylinder(radius=1), rz=True)"
        )


class TestGeometryBBox:
    def test_bbox_is_the_object_bbox(self):
        bb = Geometry(Box(0, 1, 2, 3, 4, 5)).bbox
        assert (bb.xmin, bb.ymax, bb.zmax) == (0, 3, 5)


class TestScale:
    """Test Scale transform and factory functions."""

    def test_scale_doubles_radius(self):
        cyl = Cylinder(radius=0.01)
        big = Scale(cyl, sx=2, sy=2)
        # Point at r=0.015 should now be inside (was outside original)
        assert big.eval(x=0.015, y=0.0, z=0.0) == 1.0
        # Point at r=0.025 should be outside (beyond 2x radius)
        assert big.eval(x=0.025, y=0.0, z=0.0) == 0.0

    def test_scale_z_only(self):
        cyl = CylinderZ(radius=0.01, zmin=0.0, zmax=0.1)
        tall = Scale(cyl, sz=2)
        # Original zmax was 0.1, now 0.2
        assert tall.eval(x=0.0, y=0.0, z=0.15) == 1.0
        assert tall.eval(x=0.0, y=0.0, z=0.25) == 0.0

    def test_scale_str_contains_division(self):
        cyl = Cylinder(radius=0.01)
        s = str(Scale(cyl, sx=2))
        assert "(x/2)" in s

    def test_scale_bbox(self):
        cyl = CylinderZ(radius=0.01, zmin=0.0, zmax=0.1)
        big = Scale(cyl, sx=2, sy=2, sz=3)
        bb = big.bbox
        assert bb.xmax == pytest.approx(0.02)
        assert bb.zmax == pytest.approx(0.3)

    def test_scale_around_z_axis(self):
        cyl = CylinderZ(radius=0.01, zmin=0.0, zmax=0.1)
        # Scale 2x in z around z=0.05 (center) — should expand symmetrically
        scaled = scale_around(cyl, sz=2, cz=0.05)
        bb = scaled.bbox
        assert bb.zmin == pytest.approx(-0.05)
        assert bb.zmax == pytest.approx(0.15)

    def test_scale_to_bbox_center(self):
        cyl = CylinderZ(radius=0.01, zmin=0.0, zmax=0.1)
        scaled = scale_to_bbox_center(cyl, sz=2)
        bb = scaled.bbox
        # Center at z=0.05, scaling by 2 → zmin=-0.05, zmax=0.15
        assert bb.zmin == pytest.approx(-0.05)
        assert bb.zmax == pytest.approx(0.15)

    def test_scale_to_bbox_center_eval(self):
        cyl = CylinderZ(radius=0.01, zmin=0.0, zmax=0.1)
        scaled = scale_to_bbox_center(cyl, sz=2)
        # Center stays at z=0.05
        assert scaled.eval(x=0.0, y=0.0, z=0.05) == 1.0
        # Endpoints expanded to z=-0.05 and z=0.15
        assert scaled.eval(x=0.0, y=0.0, z=-0.04) == 1.0
        assert scaled.eval(x=0.0, y=0.0, z=-0.06) == 0.0


class TestRotate:
    """Test Rotate transform."""

    def test_rotate_cylinder_unchanged(self):
        """Cylinder is rotationally symmetric — rotation should not change eval."""
        cyl = Cylinder(radius=0.01)
        rotated = Rotate(cyl, angle=np.pi / 4, axis="z")
        # Inside at r=0.005
        assert rotated.eval(x=0.005, y=0.0, z=0.0) == 1.0
        # Outside at r=0.02
        assert rotated.eval(x=0.02, y=0.0, z=0.0) == 0.0

    def test_rotate_box_z_90deg(self):
        """90-degree z rotation swaps x and y extents of a box."""
        # Box along x: x in [0.01, 0.02], y in [-0.001, 0.001]
        box = Box(xmin=0.01, xmax=0.02, ymin=-0.001, ymax=0.001, zmin=-1, zmax=1)
        rotated = Rotate(box, angle=np.pi / 2, axis="z")
        # After 90° rotation: box lies along y axis
        assert rotated.eval(x=0.0, y=0.015, z=0.0) == 1.0
        assert rotated.eval(x=0.015, y=0.0, z=0.0) == 0.0

    def test_rotate_str_contains_cos_sin(self):
        box = Box(xmin=-0.01, xmax=0.01, ymin=-0.01, ymax=0.01, zmin=0, zmax=0.1)
        s = str(Rotate(box, angle=np.pi / 4, axis="z"))
        assert "cos" not in s  # we embed numeric values, not 'cos'
        # numeric cos(pi/4) ≈ 0.707 should appear
        assert "0.7071" in s or "0.707" in s

    def test_rotate_no_double_substitution(self):
        """Placeholder approach must prevent y-terms in x-sub from being re-replaced."""
        box = Box(xmin=-0.01, xmax=0.01, ymin=-0.01, ymax=0.01, zmin=0, zmax=0.1)
        rotated = Rotate(box, angle=np.pi / 4, axis="z")
        # Verify eval is consistent with str (both give same result)
        pt = dict(x=0.005, y=0.005, z=0.05)
        assert rotated.eval(**pt) == 1.0

    def test_rotate_bbox_z(self):
        """Rotated box bbox should be larger (conservative AABB)."""
        box = Box(xmin=-0.01, xmax=0.01, ymin=-0.01, ymax=0.01, zmin=0, zmax=0.1)
        rotated = Rotate(box, angle=np.pi / 4, axis="z")
        bb = rotated.bbox
        # At 45° a [-0.01,0.01]^2 square has AABB extent sqrt(2)*0.01 ≈ 0.01414
        assert bb.xmax == pytest.approx(np.sqrt(2) * 0.01, rel=1e-5)
        assert bb.zmin == pytest.approx(0.0)
        assert bb.zmax == pytest.approx(0.1)

    def test_rotate_invalid_axis(self):
        cyl = Cylinder(radius=0.01)
        with pytest.raises(ValueError, match="axis"):
            Rotate(cyl, angle=0.1, axis="w").eval(0, 0, 0)


class TestArrayInputs:
    """Test that geometry works with numpy arrays."""

    def test_cylinder_array(self):
        """Test cylinder with array inputs."""
        cyl = Cylinder(radius=0.01)
        x = np.array([0.0, 0.005, 0.02])
        y = np.array([0.0, 0.0, 0.0])
        z = np.array([0.0, 0.0, 0.0])
        vals = cyl.eval(x, y, z)
        # First two should be inside, last outside
        np.testing.assert_array_equal(vals, [1.0, 1.0, 0.0])

    def test_meshgrid(self):
        """Test with meshgrid (common use case)."""
        cyl = CylinderZ(radius=0.01, zmin=0.0, zmax=0.1)
        x = np.linspace(-0.02, 0.02, 10)
        y = np.linspace(-0.02, 0.02, 10)
        z = np.linspace(0.0, 0.1, 10)
        X, Y, Z = np.meshgrid(x, y, z, indexing="ij")
        vals = cyl.eval(X, Y, Z)
        # Should return array of same shape
        assert vals.shape == X.shape
        # Center point should be inside
        assert vals[5, 5, 5] == 1.0
