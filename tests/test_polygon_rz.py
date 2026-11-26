"""Tests for PolygonRZ: bodies of revolution with a polygonal (z, r) cross-section."""

import numpy as np
import pytest

from warpx_geometry import Geometry, PolygonRZ

# An extraction electrode: entrance bore, wider cavity, exit bore, conical nose
# (non-convex, with a reflex vertex on every step)
ELECTRODE = [
    (0.0, 4.75e-3),
    (3.0e-3, 4.75e-3),
    (3.0e-3, 9.0e-3),
    (11.0e-3, 9.0e-3),
    (11.0e-3, 7.0e-3),
    (20.9e-3, 7.0e-3),
    (20.9e-3, 17.0e-3),
    (4.0e-3, 17.0e-3),
    (4.0e-3, 12.0e-3),
    (0.0, 6.5e-3),
]


def _random_rz(n, seed=0):
    rng = np.random.default_rng(seed)
    return rng.uniform(-1e-3, 22e-3, n), rng.uniform(0.0, 18e-3, n)


@pytest.mark.parametrize("rz", [True, False])
def test_sign_matches_inside(rz):
    obj = PolygonRZ(ELECTRODE)
    z, r = _random_rz(2000)
    theta = np.random.default_rng(1).uniform(0, 2 * np.pi, r.size)
    x, y = (r, 0 * r) if rz else (r * np.cos(theta), r * np.sin(theta))
    inside = obj.eval(x, y, z) > 0.5
    value = obj.signed_value(x, y, z, rz=rz)
    assert np.array_equal(value > 0, inside)
    assert 0.1 < inside.mean() < 0.9


def test_zero_on_outline_and_orientation():
    for pts in (ELECTRODE, ELECTRODE[::-1]):
        obj = PolygonRZ(pts)
        p = np.asarray(pts)
        q = np.roll(p, -1, axis=0)
        for t in (0.1, 0.5, 0.9):
            m = p + t * (q - p)
            v = obj.signed_value(m[:, 1], 0 * m[:, 1], m[:, 0], rz=True)
            assert np.abs(v).max() < 1e-15


def test_distance_near_an_edge():
    # 0.1 mm inside the flat upstream face of the nose
    obj = PolygonRZ(ELECTRODE)
    assert obj.signed_value(15e-3, 0.0, 4.1e-3, rz=True) == pytest.approx(
        1e-4, rel=1e-9
    )


def test_on_axis_and_geometry_voltage():
    # a disc touching the axis, and its potential expression
    disc = PolygonRZ(
        [(0.0, 0.0), (1e-3, 0.0), (1e-3, 5e-3), (0.0, 5e-3)],
        name="disc",
        default_voltage=100,
    )
    assert disc.signed_value(0.0, 0.0, 0.5e-3, rz=True) > 0
    assert disc.signed_value(0.0, 0.0, 2e-3, rz=True) < 0
    assert "100" in Geometry(disc, rz=True).to_potential_expr()


def test_bbox():
    obj = PolygonRZ(ELECTRODE)
    bb = obj.rz_bbox
    assert (bb.rmin, bb.rmax, bb.zmin, bb.zmax) == (4.75e-3, 17e-3, 0.0, 20.9e-3)
    assert obj.bbox.xmax == 17e-3 and obj.bbox.zmax == 20.9e-3


def test_invalid():
    with pytest.raises(ValueError):
        PolygonRZ([(0, 0), (1, 1)])
    with pytest.raises(ValueError):
        PolygonRZ([(0, -1), (1, 1), (1, 2)])
    with pytest.raises(ValueError):  # a bow tie
        PolygonRZ([(0, 0), (1, 1), (1, 0), (0, 1)])


def test_shallow_expression():
    # one min per triangle inside a balanced max tree: the nesting stays shallow
    z = np.linspace(0, 1, 40)
    zigzag = [(zz, 1.0 + 0.2 * (k % 2)) for k, zz in enumerate(z)] + [
        (1.0, 0.0),
        (0.0, 0.0),
    ]
    expr = PolygonRZ(zigzag).build_expr(rz=True)
    depth = deepest = 0
    for ch in expr:
        depth += ch == "("
        depth -= ch == ")"
        deepest = max(deepest, depth)
    assert deepest <= 14
