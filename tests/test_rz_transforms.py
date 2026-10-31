"""Tests for transforms that an axisymmetric (RZ) geometry can and cannot follow."""

import numpy as np
import pytest

from warpx_geometry import (
    Box,
    Cylinder,
    CylinderZ,
    CylinderZ_hollow,
    Geometry,
    Rotate,
    Scale,
    Torus,
    Translate,
)


def test_translate_along_z_is_allowed():
    c = Translate(CylinderZ(0.01, 0, 0.05), z=0.1)
    assert "z-0.1" in str(Geometry(c, rz=True))


def test_translate_y_raises():
    t = Translate(CylinderZ_hollow(0.02, 0.01, 0, 0.05), y=0.02)
    with pytest.raises(ValueError, match="RZ"):
        str(Geometry(t, rz=True))


def test_translate_x_of_shape_on_the_axis_raises():
    t = Translate(CylinderZ(0.01, 0, 0.05), x=0.02)
    with pytest.raises(ValueError, match="RZ"):
        str(Geometry(t, rz=True))


@pytest.mark.parametrize(
    "ring",
    [
        CylinderZ_hollow(0.02, 0.01, 0, 0.05),
        Box(0.01, 0.02, -1, 1, 0, 0.05),
        Torus(0.03, 0.01),
    ],
)
def test_translate_x_of_ring_moves_it_radially(ring):
    t = Translate(ring, x=0.05)
    r = np.asarray((ring.rz_bbox.rmin + ring.rz_bbox.rmax) / 2 + 0.05)
    z = np.asarray((ring.rz_bbox.zmin + ring.rz_bbox.zmax) / 2)
    assert t.signed_value(r, np.asarray(0.0), z, rz=True) > 0
    assert t.signed_value(r - 0.05, np.asarray(0.0), z, rz=True) < 0


def test_translate_x_of_ring_cannot_cross_the_axis():
    t = Translate(CylinderZ_hollow(0.02, 0.01, 0, 0.05), x=-0.015)
    with pytest.raises(ValueError, match="RZ"):
        str(Geometry(t, rz=True))


def test_xyz_translation_is_unaffected():
    t = Translate(CylinderZ(0.01, 0, 0.05), x=0.02, y=0.01)
    assert "x-0.02" in str(Geometry(t))


def test_rotation_around_z_leaves_the_profile_unchanged():
    c = CylinderZ(0.01, 0, 0.05)
    rotated = Geometry(Rotate(c, 0.3, "z"), rz=True)
    assert str(rotated) == str(Geometry(c, rz=True))


@pytest.mark.parametrize("axis", ["x", "y"])
def test_half_turn_flips_z(axis):
    c = CylinderZ(0.01, 0, 0.05)
    r = Rotate(c, np.pi, axis)
    zero = np.asarray(0.0)
    assert r.signed_value(np.asarray(0.005), zero, np.asarray(-0.02), rz=True) > 0
    assert r.signed_value(np.asarray(0.005), zero, np.asarray(0.02), rz=True) < 0


@pytest.mark.parametrize("axis", ["x", "y"])
@pytest.mark.parametrize("angle", [0.3, np.pi / 2])
def test_tilt_raises(axis, angle):
    r = Rotate(CylinderZ(0.01, 0, 0.05), angle, axis)
    with pytest.raises(ValueError, match="RZ"):
        str(Geometry(r, rz=True))


def test_uneven_radial_scale_raises():
    s = Scale(Cylinder(0.01), sx=2, sy=3)
    with pytest.raises(ValueError, match="RZ"):
        str(Geometry(s, rz=True))


def test_even_radial_scale_is_allowed():
    s = Scale(Cylinder(0.01), sx=2, sy=2, sz=3)
    assert (
        s.signed_value(np.asarray(0.015), np.asarray(0.0), np.asarray(0.0), rz=True) > 0
    )
