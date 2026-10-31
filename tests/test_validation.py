"""Tests that invalid shapes are rejected instead of giving a silently wrong result."""

import numpy as np
import pytest

from warpx_geometry import (
    Box,
    Cone,
    Cylinder,
    CylinderZ,
    CylinderZ_hollow,
    Einzellens,
    Rotate,
    RoundedCylinderZ,
    RoundedCylinderZ_hollow,
    Scale,
    Torus,
)

box = Box(0, 1, 0, 1, 0, 1)


@pytest.mark.parametrize(
    "build",
    [
        lambda: Cylinder(0),
        lambda: Cylinder(-1),
        lambda: CylinderZ(-1, 0, 1),
        lambda: CylinderZ(1, 2, 1),
        lambda: CylinderZ(1, 1, 1),
        lambda: CylinderZ_hollow(0.01, 0.02, 0, 1),
        lambda: CylinderZ_hollow(0.02, 0.02, 0, 1),
        lambda: CylinderZ_hollow(0.02, -0.01, 0, 1),
        lambda: CylinderZ_hollow(0.02, 0, 0, 1),
        lambda: CylinderZ_hollow(0.02, 0.01, 1, 0),
        lambda: Box(1, 0, 0, 1, 0, 1),
        lambda: Box(0, 1, 1, 0, 0, 1),
        lambda: Box(0, 1, 0, 1, 1, 0),
        lambda: Torus(1, 0),
        lambda: Torus(-1, 0.1),
        lambda: Cone(0.1, 0, 0.01, 0.02),
        lambda: Cone(0, 0, 0.01, 0.02),
        lambda: Cone(0, 0.1, -0.01, 0.02),
        lambda: Cone(0, 0.1, 0, 0),
        lambda: RoundedCylinderZ(0.01, 0, 0.05, 0),
        lambda: RoundedCylinderZ(0.01, 0, 0.05, 0.02),
        lambda: RoundedCylinderZ(0.01, 0, 0.002, 0.002),
        lambda: RoundedCylinderZ_hollow(0.01, 0.02, 0, 0.05, 0.001),
        lambda: Einzellens(0.01, 0.03, 0.01, 0.001),
        lambda: Einzellens(0.03, 0.01, -0.01, 0.001),
        lambda: Einzellens(0.03, 0.01, 0.01, -0.001),
        lambda: Scale(box, sx=0),
        lambda: Scale(box, sy=-1),
        lambda: Rotate(box, 0.1, axis="w"),
    ],
)
def test_invalid_input_raises(build):
    with pytest.raises(ValueError):
        build()


def test_infinite_box_is_valid():
    assert "x" in str(Box(0, 1, -np.inf, np.inf, -np.inf, np.inf))


def test_touching_lens_electrodes_are_valid():
    assert Einzellens(0.03, 0.01, 0.01, 0)


def test_cone_with_a_tip_is_valid():
    assert Cone(0, 0.1, 0.01, 0)
