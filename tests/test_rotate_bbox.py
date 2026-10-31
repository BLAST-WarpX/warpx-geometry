"""Tests for the bounding box of rotated objects."""

import numpy as np
import pytest

from warpx_geometry import Box, Cylinder, Rotate

R = 0.01


def extents(bb):
    return [bb.xmin, bb.xmax, bb.ymin, bb.ymax, bb.zmin, bb.zmax]


@pytest.mark.parametrize("axis", ["x", "y", "z"])
@pytest.mark.parametrize("angle", [0, 0.3, np.pi / 4, np.pi / 2, np.pi, 2.5])
def test_infinite_shape_has_no_nan(axis, angle):
    assert not np.any(np.isnan(extents(Rotate(Cylinder(R), angle, axis).bbox)))


@pytest.mark.parametrize("axis", ["x", "y"])
def test_no_rotation_keeps_the_box(axis):
    bb = Rotate(Cylinder(R), 0, axis).bbox
    assert extents(bb) == [-R, R, -R, R, -np.inf, np.inf]


def test_right_angle_moves_the_infinite_axis():
    bb = Rotate(Cylinder(R), np.pi / 2, "x").bbox
    assert (bb.xmin, bb.xmax, bb.zmin, bb.zmax) == (-R, R, -R, R)
    assert (bb.ymin, bb.ymax) == (-np.inf, np.inf)


def test_tilted_infinite_shape_is_unbounded_in_both_axes():
    bb = Rotate(Cylinder(R), 0.3, "x").bbox
    assert (bb.ymin, bb.ymax, bb.zmin, bb.zmax) == (-np.inf, np.inf, -np.inf, np.inf)


@pytest.mark.parametrize("axis", ["x", "y", "z"])
def test_finite_box_contains_every_inside_point(axis):
    rotated = Rotate(Box(0.1, 0.3, -0.2, 0.1, 0.0, 0.4), 0.7, axis)
    bb = rotated.bbox
    pts = np.random.default_rng(0).uniform(-0.7, 0.7, (3, 20000))
    x, y, z = pts[:, rotated.signed_value(*pts) > 0]
    assert len(x) > 0
    assert x.min() >= bb.xmin and x.max() <= bb.xmax
    assert y.min() >= bb.ymin and y.max() <= bb.ymax
    assert z.min() >= bb.zmin and z.max() <= bb.zmax
