"""Tests that each conductor gets its own voltage from to_potential_expr."""

import numpy as np
import pytest

from warpx_geometry import (
    Box,
    Cylinder,
    CylinderZ_hollow,
    Geometry,
    Translate,
)
from warpx_geometry.geometry import evaluate_expr


def potential(expr, x, y=0.0, z=0.0):
    return float(
        evaluate_expr(expr, np.asarray(x), np.asarray(y), np.asarray(z)),
    )


def concentric(v_inner, v_outer, rz=False):
    inner = CylinderZ_hollow(0.02, 0.015, 0, 0.1, name="in", default_voltage=v_inner)
    outer = CylinderZ_hollow(0.05, 0.045, 0, 0.1, name="out", default_voltage=v_outer)
    return Geometry(inner + outer, rz=rz)


@pytest.mark.parametrize("rz", [False, True])
@pytest.mark.parametrize(
    "v_inner, v_outer",
    [(-1000, 500), (1000, 500), (500, 1000), (-500, -1000), (1000, -500)],
)
def test_concentric_conductors_keep_their_voltage(rz, v_inner, v_outer):
    expr = concentric(v_inner, v_outer, rz).to_potential_expr()
    assert potential(expr, 0.0175, z=0.05) == v_inner
    assert potential(expr, 0.0475, z=0.05) == v_outer


def test_grounded_conductor_inside_a_charged_one_stays_grounded():
    expr = concentric(0, 500).to_potential_expr()
    assert potential(expr, 0.0175, z=0.05) == 0
    assert potential(expr, 0.0475, z=0.05) == 500


def test_potential_is_zero_away_from_conductors():
    expr = concentric(-1000, 500).to_potential_expr(margin=0.001)
    assert potential(expr, 0.03, z=0.05) == 0


def test_surface_is_inside_the_region_by_default():
    # WarpX evaluates the potential on the surface, which it only approximates
    expr = concentric(-1000, 500).to_potential_expr()
    assert potential(expr, 0.02, z=0.05) == -1000
    assert potential(expr, 0.02 + 1e-5, z=0.05) == -1000
    assert potential(expr, 0.015, z=0.1) == -1000


def test_margin_sets_the_region_size():
    geo = concentric(-1000, 500)
    expr = geo.to_potential_expr(margin=0.002)
    assert potential(expr, 0.0215, z=0.05) == -1000
    assert potential(expr, 0.0225, z=0.05) == 0
    assert potential(geo.to_potential_expr(margin=0), 0.0205, z=0.05) == 0


def test_touching_conductors_do_not_add_up():
    a = Box(0, 1, 0, 1, 0, 1, name="a", default_voltage=100)
    b = Box(1, 2, 0, 1, 0, 1, name="b", default_voltage=100)
    expr = Geometry(a + b).to_potential_expr(margin=0.1)
    assert potential(expr, 1.0, 0.5, 0.5) == 100


def test_shifted_conductor_region_follows_the_shape():
    tube = Translate(CylinderZ_hollow(0.02, 0.015, 0, 0.1), z=0.2)
    expr = Geometry(tube.named("t", 7)).to_potential_expr()
    assert potential(expr, 0.0175, z=0.25) == 7
    assert potential(expr, 0.0175, z=0.05) == 0


def test_unbounded_conductor_has_no_infinite_values():
    expr = Geometry(Cylinder(0.01, name="c", default_voltage=5)).to_potential_expr()
    assert "inf" not in expr
    assert potential(expr, 0.0, z=100.0) == 5


def test_single_object_potential_expr():
    c = CylinderZ_hollow(0.02, 0.015, 0, 0.1)
    expr = c.to_potential_expr(9, rz=False)
    assert potential(expr, 0.0175, z=0.05) == 9
    assert potential(expr, 0.03, z=0.05) == 0
