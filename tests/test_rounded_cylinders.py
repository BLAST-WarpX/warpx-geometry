"""Tests that the rounded cylinders are solid up to their fillets."""

import numpy as np
import pytest

from warpx_geometry import RoundedCylinderZ, RoundedCylinderZ_hollow


def inside(obj, x, y, z):
    x, y, z = np.asarray(x), np.asarray(y), np.asarray(z)
    return bool(obj.signed_value(x, y, z) > 0)


@pytest.mark.parametrize("z", [0.0005, 0.0495])
def test_end_caps_are_filled(z):
    c = RoundedCylinderZ(0.01, 0, 0.05, 0.001)
    for x in (0.0, 0.004, 0.0085):
        assert inside(c, x, 0.0, z)
        assert c.eval(np.asarray(x), np.asarray(0.0), np.asarray(z)) > 0


def test_corner_is_rounded():
    c = RoundedCylinderZ(0.01, 0, 0.05, 0.002)
    # just inside the sharp corner, but outside the rounded one
    assert not inside(c, 0.0098, 0.0, 0.0002)
    assert not inside(c, 0.0098, 0.0, 0.0498)


def test_extent_is_unchanged():
    c = RoundedCylinderZ(0.01, 0, 0.05, 0.001)
    assert not inside(c, 0.0, 0.0, -0.0001)
    assert not inside(c, 0.0, 0.0, 0.0501)
    assert not inside(c, 0.0101, 0.0, 0.025)


@pytest.mark.parametrize("top, bottom", [(True, False), (False, True)])
def test_one_fillet_keeps_the_other_end_sharp(top, bottom):
    c = RoundedCylinderZ(0.01, 0, 0.05, 0.002, fillet_top=top, fillet_bottom=bottom)
    assert inside(c, 0.0, 0.0, 0.0005)
    assert inside(c, 0.0, 0.0, 0.0495)
    sharp_z, round_z = (0.0002, 0.0498) if top else (0.0498, 0.0002)
    assert inside(c, 0.0098, 0.0, sharp_z)
    assert not inside(c, 0.0098, 0.0, round_z)


def test_no_fillets_is_a_plain_finite_cylinder():
    c = RoundedCylinderZ(0.01, 0, 0.05, 0.001, fillet_top=False, fillet_bottom=False)
    assert inside(c, 0.0099, 0.0, 0.0001)
    assert not inside(c, 0.0, 0.0, 1.0)
    assert not inside(c, 1.0, 0.0, 0.02)
    bb = c.bbox
    assert (bb.xmin, bb.xmax, bb.zmin, bb.zmax) == (-0.01, 0.01, 0, 0.05)


def test_thick_hollow_wall_is_filled():
    c = RoundedCylinderZ_hollow(0.02, 0.005, 0, 0.05, 0.002)
    assert inside(c, 0.0125, 0.0, 0.001)
    assert inside(c, 0.0125, 0.0, 0.049)
    assert not inside(c, 0.003, 0.0, 0.001)
