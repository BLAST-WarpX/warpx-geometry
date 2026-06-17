"""Tests for XYZ (Cartesian) geometry objects."""

import numpy as np

from warpx_geometry import (
    Box,
    Cone,
    Cylinder,
    CylinderZ,
    CylinderZ_hollow,
    Diff,
    Geometry,
    Intersection,
    RoundedCylinderZ,
    RoundedCylinderZ_hollow,
    Torus,
    Translate,
    Union,
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
        # Note: Translate only works on basic shapes with simple .shape attribute
        # CylinderZ is a composite (Intersection), so use basic Cylinder
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
        # String should subtract 0.5 for WarpX convention
        geom_str = str(geom)
        assert "-0.5" in geom_str

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
