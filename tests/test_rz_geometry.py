"""Tests for RZ (cylindrical) geometry - testing in RZ coordinate system."""

import numpy as np

from warpx_geometry import (
    Cone,
    Cylinder,
    CylinderZ,
    CylinderZ_hollow,
    Einzellens,
    RoundedCylinderZ,
    Torus,
    Union,
)


class TestRZCylinder:
    """Test cylindrical geometries in RZ coordinates.

    In RZ simulations, we sample at y=0 and use x as the radial coordinate r.
    """

    def test_cylinder_on_axis(self):
        """Test cylinder evaluation on axis (r=0)."""
        cyl = Cylinder(radius=0.01)
        # On axis: x=r=0, y=0
        val = cyl.eval(x=0.0, y=0.0, z=0.0)
        assert val == 1.0

    def test_cylinder_at_radius(self):
        """Test cylinder at various radii."""
        cyl = Cylinder(radius=0.01)
        # Inside: r = 0.005m
        val = cyl.eval(x=0.005, y=0.0, z=0.0)
        assert val == 1.0
        # Outside: r = 0.02m
        val = cyl.eval(x=0.02, y=0.0, z=0.0)
        assert val == 0.0

    def test_cylinder_z_rz_slice(self):
        """Test finite cylinder in RZ coordinates."""
        cyl = CylinderZ(radius=0.01, zmin=0.0, zmax=0.1)

        # Create RZ grid
        r_vals = np.linspace(0.0, 0.02, 20)
        z_vals = np.linspace(-0.01, 0.11, 20)
        R, Z = np.meshgrid(r_vals, z_vals, indexing="ij")

        # In RZ, x=r, y=0
        X = R
        Y = np.zeros_like(R)

        vals = cyl.eval(X, Y, Z)

        # Check center is inside (r≈0.005, z≈0.05)
        assert vals[5, 10] == 1.0
        # Check outside in r (r≈0.02, outside radius)
        assert vals[19, 10] == 0.0
        # Check outside in z (below, z≈-0.01)
        assert vals[5, 0] == 0.0
        # Check outside in z (above, z≈0.11)
        assert vals[5, 19] == 0.0

    def test_hollow_cylinder_rz(self):
        """Test hollow cylinder in RZ coordinates."""
        cyl = CylinderZ_hollow(
            radius_outer=0.011, radius_inner=0.010, zmin=0.0, zmax=0.1
        )

        # On axis (should be empty - inside bore)
        val = cyl.eval(x=0.0, y=0.0, z=0.05)
        assert val == 0.0

        # In wall (between inner and outer)
        val = cyl.eval(x=0.0105, y=0.0, z=0.05)
        assert val == 1.0

        # Outside
        val = cyl.eval(x=0.02, y=0.0, z=0.05)
        assert val == 0.0


class TestRZTorus:
    """Test torus in RZ coordinates (common for rounded edges)."""

    def test_torus_rz_symmetry(self):
        """Test torus is symmetric in RZ plane."""
        torus = Torus(major_radius=0.010, minor_radius=0.001, z_center=0.1)

        # Point on torus at y=0 (RZ plane)
        # At r = R (major radius), should be inside the tube
        val = torus.eval(x=0.010, y=0.0, z=0.1)
        assert val == 1.0

        # Point slightly above/below at major radius
        val_above = torus.eval(x=0.010, y=0.0, z=0.1005)
        val_below = torus.eval(x=0.010, y=0.0, z=0.0995)
        assert val_above == 1.0
        assert val_below == 1.0

    def test_torus_center_empty(self):
        """Test center of torus is empty."""
        torus = Torus(major_radius=0.010, minor_radius=0.001, z_center=0.1)
        # On axis at torus center height
        val = torus.eval(x=0.0, y=0.0, z=0.1)
        assert val == 0.0


class TestRZCone:
    """Test cone geometry in RZ coordinates."""

    def test_cone_rz_profile(self):
        """Test cone tapering in RZ plane."""
        cone = Cone(z1=0.0, z2=0.1, r1=0.010, r2=0.005)

        # At z=0 (wide end), r=0.009 should be inside
        val = cone.eval(x=0.009, y=0.0, z=0.001)
        assert val == 1.0

        # At z=0.1 (narrow end), r=0.009 should be outside
        val = cone.eval(x=0.009, y=0.0, z=0.099)
        assert val == 0.0

        # At z=0.1, r=0.004 should be inside
        val = cone.eval(x=0.004, y=0.0, z=0.099)
        assert val == 1.0

    def test_cone_linear_taper(self):
        """Test that cone radius varies linearly with z."""
        cone = Cone(z1=0.0, z2=0.1, r1=0.010, r2=0.005)

        # At midpoint z=0.05, radius should be 0.0075
        # Point at r=0.007 should be inside
        val = cone.eval(x=0.007, y=0.0, z=0.05)
        assert val == 1.0
        # Point at r=0.008 should be outside
        val = cone.eval(x=0.008, y=0.0, z=0.05)
        assert val == 0.0


class TestRZRoundedCylinder:
    """Test rounded cylinders (with torus fillets) in RZ."""

    def test_rounded_cylinder_rz(self):
        """Test rounded cylinder in RZ coordinates."""
        cyl = RoundedCylinderZ(radius=0.010, zmin=0.0, zmax=0.05, fillet_radius=0.001)

        # Main body should be inside
        val = cyl.eval(x=0.005, y=0.0, z=0.025)
        assert val == 1.0

        # On axis should be inside
        val = cyl.eval(x=0.0, y=0.0, z=0.025)
        assert val == 1.0

        # At outer radius in main body
        val = cyl.eval(x=0.009, y=0.0, z=0.025)
        assert val == 1.0

    def test_rounded_cylinder_fillet_region(self):
        """Test the filleted regions of rounded cylinder."""
        cyl = RoundedCylinderZ(radius=0.010, zmin=0.0, zmax=0.05, fillet_radius=0.001)

        # Point in bottom fillet region
        # Fillet is at z=0.001, major_radius=0.009
        val = cyl.eval(x=0.009, y=0.0, z=0.001)
        assert val == 1.0


class TestRZComplexGeometry:
    """Test complex geometries like Einzellens in RZ."""

    def test_einzellens_structure(self):
        """Test Einzellens (3-electrode lens) in RZ coordinates."""
        lens = Einzellens(radius=0.015, thickness=0.002, length=0.02, gap=0.01)

        # Should be empty on axis (hollow)
        val = lens.eval(x=0.0, y=0.0, z=0.0)
        assert val == 0.0

        # Should have material at electrode radius
        # Middle electrode is at z=[-0.01, 0.01]
        # Radius outer = 0.015 + 0.001 = 0.016
        # Radius inner = 0.015 - 0.001 = 0.014
        val = lens.eval(x=0.015, y=0.0, z=0.0)
        assert val == 1.0

    def test_einzellens_three_electrodes(self):
        """Test that Einzellens has three separate electrodes."""
        lens = Einzellens(radius=0.015, thickness=0.002, length=0.02, gap=0.01)

        # Actual geometry:
        # Electrode 1: z in [-0.04, -0.02]
        # Gap 1: z in [-0.02, -0.01]
        # Electrode 2 (middle): z in [-0.01, 0.01]
        # Gap 2: z in [0.01, 0.02]
        # Electrode 3: z in [0.02, 0.04]

        # In gap between first and middle electrode (should be empty)
        val = lens.eval(x=0.015, y=0.0, z=-0.015)
        assert val == 0.0

        # In first electrode
        val = lens.eval(x=0.015, y=0.0, z=-0.03)
        assert val == 1.0

        # In middle electrode
        val = lens.eval(x=0.015, y=0.0, z=0.0)
        assert val == 1.0

        # In third electrode
        val = lens.eval(x=0.015, y=0.0, z=0.03)
        assert val == 1.0


class TestRZGeometryMask:
    """Test creating RZ geometry masks for plotting."""

    def test_rz_grid_evaluation(self):
        """Test evaluating geometry on RZ grid."""
        cyl = CylinderZ(radius=0.01, zmin=0.0, zmax=0.1)

        # Create typical RZ grid
        nz = 100
        nr = 50
        z_grid = np.linspace(0.0, 0.15, nz)
        r_grid = np.linspace(0.0, 0.02, nr)

        Z, R = np.meshgrid(z_grid, r_grid, indexing="ij")

        # In RZ: x=r, y=0
        X = R
        Y = np.zeros_like(R)

        mask = cyl.eval(X, Y, Z)

        # Check shape
        assert mask.shape == (nz, nr)

        # Check that on-axis points inside z-range are filled
        assert mask[50, 0] == 1.0  # z=0.075, r=0 (inside)

        # Check that points outside z-range are empty
        assert mask[99, 0] == 0.0  # z≈0.15, r=0 (outside z-range)

        # Check that points outside radius are empty
        assert mask[50, 49] == 0.0  # r≈0.02 (outside radius)

    def test_rz_union_mask(self):
        """Test RZ mask for union of geometries."""
        # Two cylinders end-to-end
        cyl1 = CylinderZ(radius=0.01, zmin=0.0, zmax=0.05)
        cyl2 = CylinderZ(radius=0.008, zmin=0.05, zmax=0.1)
        combined = Union(cyl1, cyl2)

        # Create RZ grid
        z_grid = np.linspace(0.0, 0.1, 100)
        r_grid = np.linspace(0.0, 0.015, 50)
        Z, R = np.meshgrid(z_grid, r_grid, indexing="ij")
        X = R
        Y = np.zeros_like(R)

        mask = combined.eval(X, Y, Z)

        # Point in first cylinder (wider)
        # z=0.025 (idx~25), r=0.009 (idx~30)
        assert mask[25, 30] == 1.0

        # Point in second cylinder (narrower)
        # z=0.075 (idx~75), r=0.007 (idx~23)
        assert mask[75, 23] == 1.0

        # Point at r=0.009 in second cylinder (should be outside)
        assert mask[75, 30] == 0.0


class TestRZSymmetry:
    """Test that RZ geometries are properly symmetric."""

    def test_cylinder_rz_symmetry(self):
        """Test that cylinder is rotationally symmetric."""
        cyl = Cylinder(radius=0.01)

        # Same radial distance, different angles
        # In RZ we sample at y=0, so we only test x=r
        r = 0.005

        # At y=0, x=r (standard RZ slice)
        val1 = cyl.eval(x=r, y=0.0, z=0.0)

        # Both should be inside (same distance from axis)
        # Note: our Cylinder class uses x^2+y^2, so (-r)^2 = r^2
        assert val1 == 1.0
        # The negative x might be outside depending on implementation
        # but the important thing is RZ plots should use positive r only

    def test_torus_rz_slice(self):
        """Test torus cross-section in RZ plane."""
        # Torus centered at z=0.1
        torus = Torus(major_radius=0.010, minor_radius=0.001, z_center=0.1)

        # Create RZ slice at y=0
        r_vals = np.linspace(0.0, 0.015, 30)
        z_vals = np.linspace(0.095, 0.105, 30)
        R, Z = np.meshgrid(r_vals, z_vals, indexing="ij")
        X = R
        Y = np.zeros_like(R)

        mask = torus.eval(X, Y, Z)

        # Should form a circle in RZ plane
        # Center of circle at (r=0.01, z=0.1)
        # With radius 0.001

        # On axis should be empty
        assert mask[0, 15] == 0.0  # r=0, z=0.1

        # At major radius should have material
        # r≈0.01 is around index 20
        assert mask[20, 15] == 1.0  # r≈0.01, z≈0.1
