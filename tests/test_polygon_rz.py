"""Tests for PolygonRZ: bodies of revolution with a polygonal (z, r) cross-section."""

import numpy as np
import pytest

from warpx_geometry import (
    CylinderZ,
    Geometry,
    PolygonRZ,
    Scale,
    Translate,
    parser_stack_size,
)
from warpx_geometry.geometry import evaluate_expr

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

# An L-shaped body on the axis
L_SHAPE = [(0, 0), (2e-3, 0), (2e-3, 1e-3), (1e-3, 1e-3), (1e-3, 2e-3), (0, 2e-3)]


def _random_rz(n, seed=0):
    rng = np.random.default_rng(seed)
    return rng.uniform(-1e-3, 22e-3, n), rng.uniform(0.0, 18e-3, n)


def _distance_to_outline(pts, z, r):
    """Brute-force distance from (z, r) to the edges of pts that are not on the axis."""
    pts = np.asarray(pts, dtype=float)
    best = np.full(np.shape(z), np.inf)
    for a, b in zip(pts, np.roll(pts, -1, axis=0), strict=True):
        if a[1] == 0 and b[1] == 0:
            continue
        d = b - a
        t = np.clip(((z - a[0]) * d[0] + (r - a[1]) * d[1]) / (d @ d), 0.0, 1.0)
        best = np.minimum(best, np.hypot(z - a[0] - t * d[0], r - a[1] - t * d[1]))
    return best


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


@pytest.mark.parametrize("pts", [ELECTRODE, L_SHAPE])
def test_signed_distance(pts):
    # the value is the exact signed distance, inside and outside, also in 3D
    obj = PolygonRZ(pts)
    p = np.asarray(pts)
    rng = np.random.default_rng(2)
    span = p.max(axis=0) - p.min(axis=0)
    z = rng.uniform(p[:, 0].min() - span[0], p[:, 0].max() + span[0], 3000)
    r = rng.uniform(0.0, p[:, 1].max() + span[1], 3000)
    dist = _distance_to_outline(pts, z, r)
    sign = np.where(obj.eval(r, 0 * r, z) > 0.5, 1.0, -1.0)
    expected = sign * dist
    assert np.allclose(
        obj.signed_value(r, 0 * r, z, rz=True), expected, rtol=1e-9, atol=1e-18
    )
    theta = rng.uniform(0, 2 * np.pi, r.size)
    value_3d = obj.signed_value(r * np.cos(theta), r * np.sin(theta), z, rz=False)
    assert np.allclose(value_3d, expected, rtol=1e-9, atol=1e-18)


def test_zero_on_outline_and_orientation():
    # zero up to the 12 significant digits of the numbers in the expression
    size = 21e-3
    for pts in (ELECTRODE, ELECTRODE[::-1]):
        obj = PolygonRZ(pts)
        p = np.asarray(pts)
        q = np.roll(p, -1, axis=0)
        for t in (0.1, 0.5, 0.9):
            m = p + t * (q - p)
            v = obj.signed_value(m[:, 1], 0 * m[:, 1], m[:, 0], rz=True)
            assert np.abs(v).max() < 1e-12 * size


def test_no_zeros_inside_or_outside():
    # on a grid with nodes on the outline, only those nodes are zero, so neither
    # the body nor a difference with it has spurious surfaces
    obj = PolygonRZ(L_SHAPE)
    grid = np.meshgrid(np.arange(21) * 1e-4, np.arange(21) * 1e-4, indexing="ij")
    z, r = (g.ravel() for g in grid)
    value = obj.signed_value(r, 0 * r, z, rz=True)
    off = _distance_to_outline(L_SHAPE, z, r) > 1e-12 * 2e-3  # not on the outline
    assert np.all(np.abs(value[off]) >= 1e-4 * (1 - 1e-9))
    assert np.array_equal(value[off] > 0, obj.eval(r, 0 * r, z)[off] > 0.5)
    vacuum = (CylinderZ(3e-3, -1e-3, 3e-3) - obj).signed_value(r, 0 * r, z, rz=True)
    assert np.all(vacuum[(value > 0) & off] < 0)


def test_x_below_zero_is_the_axis():
    # in RZ, x < 0 is inside a body on the axis and outside a ring, and the
    # value keeps growing with the distance (no plateau)
    disc = PolygonRZ([(0.0, 0.0), (1e-3, 0.0), (1e-3, 5e-3), (0.0, 5e-3)])
    ring = PolygonRZ([(0, 1e-3), (1e-3, 1e-3), (1e-3, 2e-3), (0, 2e-3)])
    x, z = -np.array([1e-4, 1.5e-3, 6e-3]), np.full(3, 0.5e-3)
    assert np.all(disc.signed_value(x, 0 * x, z, rz=True) > 0)
    v = ring.signed_value(x, 0 * x, z, rz=True)
    assert np.all(v < 0) and np.all(np.diff(v) < 0)


def test_translated_ring_potential():
    # a ring drawn next to the axis and moved out: its voltage stays at the ring
    ring = PolygonRZ([(0, 5e-6), (1e-3, 5e-6), (1e-3, 1e-3), (0, 1e-3)])
    moved = Translate(ring, x=0.02).named("ring", default_voltage=100)
    potential = Geometry(moved, rz=True).to_potential_expr()
    r = np.array([0.0, 0.005, 0.01, 0.019, 0.0205])
    v = evaluate_expr(potential, r, 0 * r, np.full(r.size, 0.5e-3))
    assert np.array_equal(v, [0, 0, 0, 0, 100])


def test_rounding_noise_on_the_axis():
    # an arc from sin/cos: its ends are within rounding of the axis
    th = np.linspace(0, np.pi, 33)
    sphere = PolygonRZ(list(zip(5e-3 * np.cos(th), 5e-3 * np.sin(th), strict=True)))
    assert sphere.signed_value(0.0, 0.0, 0.0, rz=True) == pytest.approx(5e-3, rel=1e-2)
    assert sphere.signed_value(1e-5, 0.0, 0.0, rz=True) > 4.9e-3
    # a closing vertex that repeats the first one up to rounding
    square = [(0, 1e-3), (1e-3, 1e-3), (1e-3, 2e-3), (0, 2e-3)]
    assert len(PolygonRZ(square + [(1e-19, 1e-3)]).points) == 4


def test_touching_with_rounding():
    # a vertex on a slanted edge, at a position that is not exact in binary
    a, b = np.array([3e-3, 4.75e-3]), np.array([8e-3, 6.3e-3])
    rng = np.random.default_rng(6)
    for t in rng.uniform(0.2, 0.8, 50):
        v = a + t * (b - a)
        pts = [(0, 4.75e-3), tuple(a), tuple(b), (8e-3, 9e-3), tuple(v), (0, 9e-3)]
        with pytest.raises(ValueError, match="touch or cross"):
            PolygonRZ(pts)


def test_on_axis_and_geometry_voltage():
    # a disc touching the axis, and its potential expression
    disc = PolygonRZ(
        [(0.0, 0.0), (1e-3, 0.0), (1e-3, 5e-3), (0.0, 5e-3)],
        name="disc",
        default_voltage=100,
    )
    assert disc.signed_value(0.0, 0.0, 0.5e-3, rz=True) == pytest.approx(0.5e-3)
    assert disc.signed_value(0.0, 0.0, 2e-3, rz=True) == pytest.approx(-1e-3)
    potential = Geometry(disc, rz=True).to_potential_expr()
    r, z = np.array([0.0, 2e-3, 4e-3, 6e-3]), np.array([0.5e-3, 0.5e-3, 3e-3, 0.5e-3])
    assert np.array_equal(evaluate_expr(potential, r, 0 * r, z), [100, 100, 0, 0])


@pytest.mark.parametrize("rz", [True, False])
def test_transforms(rz):
    # transformed coordinates are pasted into the distance and the sign terms
    obj = PolygonRZ(ELECTRODE)
    for t in (Translate(obj, z=0.05), Scale(obj, sx=2, sy=2, sz=0.5)):
        z, r = _random_rz(2000, seed=3)
        z = (z + 0.05) if isinstance(t, Translate) else z * 0.5
        r = r if isinstance(t, Translate) else 2 * r
        theta = np.random.default_rng(4).uniform(0, 2 * np.pi, r.size)
        x, y = (r, 0 * r) if rz else (r * np.cos(theta), r * np.sin(theta))
        value = t.signed_value(x, y, z, rz=rz)
        inside = t.eval(x, y, z) > 0.5
        assert np.array_equal(value > 0, inside) and 0.1 < inside.mean() < 0.9


def test_bbox():
    obj = PolygonRZ(ELECTRODE)
    bb = obj.rz_bbox
    assert (bb.rmin, bb.rmax, bb.zmin, bb.zmax) == (4.75e-3, 17e-3, 0.0, 20.9e-3)
    assert obj.bbox.xmax == 17e-3 and obj.bbox.zmax == 20.9e-3


@pytest.mark.parametrize(
    ("pts", "message"),
    [
        ([(0, 0), (1, 1)], "at least 3 vertices"),
        ([(0, -1), (1, 1), (1, 2)], "r >= 0"),
        ([(0, 0), (1, 1), (1, 0), (0, 1)], "touch or cross"),  # a bow tie
        (  # pinched: a vertex used twice
            [(0, 1), (1, 1), (1, 2), (2, 2), (2, 3), (1, 3), (1, 2), (0, 2)],
            "touch or cross",
        ),
        ([(0, 1), (2, 1), (2, 3), (1, 1.5), (1, 1)], "touch or cross"),  # on an edge
        # folds back onto a neighbour (and so touches another edge)
        ([(0, 1), (2, 1), (1, 1), (1, 2)], "overlap|touch or cross"),
        ([(0, 0), (1, 1), (2, 2)], "overlap"),  # collinear: no area
        ([(0, 1), (1, 1), (1, float("nan"))], "finite"),
        ([(0, 1), (1, 1), (1, float("inf")), (0, 2)], "finite"),
        ([0, 1, 1, 1, 1, 2, 0, 2], "pairs"),
        ([(0, 1, 1, 1), (1, 2, 0, 2)], "pairs"),
        ([(0, 1), (1, 1, 2), (0, 2)], "pairs"),  # ragged
        ([(0, 1), (1, 1j), (0, 2)], "pairs"),  # complex
        (5, "pairs"),
        (np.empty((0, 2)), "at least 3 vertices"),
    ],
)
def test_invalid(pts, message):
    with pytest.raises(ValueError, match=message):
        PolygonRZ(pts)


def test_points_from_an_iterator():
    z, r = [0, 1e-3, 1e-3, 0], [1e-3, 1e-3, 2e-3, 2e-3]
    assert PolygonRZ(zip(z, r, strict=True)).build_expr(rz=True) == PolygonRZ(
        list(zip(z, r, strict=True))
    ).build_expr(rz=True)


@pytest.mark.parametrize("scale", [1.0, 1e-6, 1e6])
def test_validation_does_not_depend_on_edge_lengths(scale):
    # The rounding tolerance is 1e-12 of the outline size as a distance, also
    # next to short edges: a 10 nm tip (53 degrees) in a 20 mm outline is fine,
    # and so is the same outline at other scales.
    tip = [
        (0, 1e-3),
        (20e-3, 1e-3),
        (20e-3, 5e-3),
        (10e-3, 5e-3),
        (10e-3 - 5e-9, 5e-3 + 1e-8),
        (10e-3 - 1e-8, 5e-3),
        (0, 5e-3),
    ]
    PolygonRZ([(scale * zz, scale * rr) for zz, rr in tip])
    # a fold back onto a neighbour stays an overlap at any scale
    fold = [(0, 1), (2, 1), (2, 2), (1, 2), (1.5, 2), (0, 3)]
    with pytest.raises(ValueError, match="overlap|touch or cross"):
        PolygonRZ([(scale * zz, scale * rr) for zz, rr in fold])


def test_large_outline_warns():
    z = np.linspace(0, 1, 300)
    pts = [(zz, 1.0 + 0.2 * (k % 2)) for k, zz in enumerate(z)] + [
        (1.0, 0.0),
        (0.0, 0.0),
    ]
    with pytest.warns(UserWarning, match="compile"):
        PolygonRZ(pts)


def test_repeated_vertices_are_dropped():
    square = [(0, 1), (1, 1), (1, 2), (0, 2)]
    doubled = [(0, 1), (1, 1), (1, 1), (1, 2), (0, 2), (0, 1)]
    expr = PolygonRZ(doubled).build_expr(rz=True)
    assert expr == PolygonRZ(square).build_expr(rz=True)


def test_points_are_copied():
    outline = np.array(ELECTRODE)
    obj = PolygonRZ(outline)
    outline[:, 0] += 10e-3
    assert obj.rz_bbox.zmin == 0.0
    assert not np.shares_memory(obj.points, outline)
    with pytest.raises(ValueError):
        obj.points[0, 0] = 1.0


def test_repr():
    obj = PolygonRZ(ELECTRODE, name="ee", default_voltage=-30e3)
    text = repr(obj)
    assert "name='ee'" in text and "default_voltage=-30000.0" in text
    again = eval(text, {"PolygonRZ": PolygonRZ})
    assert np.array_equal(again.points, obj.points)
    assert "name" not in repr(PolygonRZ(ELECTRODE))


def test_shallow_expression():
    # Balanced min and product trees: the AMReX parser's stack (its limit is
    # 16) grows with log2 of the number of edges.  The numbers are those that
    # AMReX 26.08 and 26.11 report (Parser::maxStackSize).
    def zigzag(n):
        z = np.linspace(0, 1, n)
        top = [(zz, 1.0 + 0.2 * (k % 2)) for k, zz in enumerate(z)]
        return PolygonRZ(top + [(1.0, 0.0), (0.0, 0.0)])

    with pytest.warns(UserWarning, match="compile"):
        zigzag(300)  # above 256 edges
    with pytest.warns(UserWarning, match="compile"):
        long_outline = zigzag(512)
    for rz in (True, False):
        assert parser_stack_size(PolygonRZ(ELECTRODE).build_expr(rz=rz)) == 6
        stacks = [
            parser_stack_size(p.build_expr(rz=rz)) for p in (zigzag(8), zigzag(128))
        ]
        assert stacks + [parser_stack_size(long_outline.build_expr(rz=rz))] == [
            8,
            12,
            14,
        ]
