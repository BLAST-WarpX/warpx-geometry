"""Generated WarpX expressions must agree with eval().

Translate/Scale/Rotate used to do plain string replacement on the finished
expression, which also rewrote the 'x' inside 'max(' (issue #1). The
expressions are now smooth signed functions combined with min/max (also
issue #1). These tests evaluate the generated expression strings numerically
and check that they are strictly positive inside and strictly negative
outside, matching eval().
"""

import re

import numpy as np
import pytest

from warpx_geometry import (
    Box,
    Cone,
    Cylinder,
    CylinderZ,
    CylinderZ_hollow,
    Intersection,
    Rotate,
    RoundedCylinderZ_hollow,
    Scale,
    Torus,
    Translate,
    scale_around,
)
from warpx_geometry.complex_geometry import Einzellens


def eval_expr(expr, x, y, z):
    """Evaluate a WarpX parser expression string with numpy."""
    py = re.sub(r"\bif\(", "_if(", expr)
    namespace = {
        "_if": lambda c, a, b: np.where(c, a, b),
        "max": np.maximum,
        "min": np.minimum,
        "sqrt": np.sqrt,
        "x": x,
        "y": y,
        "z": z,
    }
    return eval(py, {"__builtins__": {}}, namespace)


def random_points(bbox_obj, n=2000, seed=0):
    rng = np.random.default_rng(seed)
    bb = bbox_obj.bbox
    lo = np.array([bb.xmin, bb.ymin, bb.zmin]) - 0.01
    hi = np.array([bb.xmax, bb.ymax, bb.zmax]) + 0.01
    pts = rng.uniform(lo, hi, size=(n, 3))
    return pts[:, 0], pts[:, 1], pts[:, 2]


def union_of_boxes():
    return Box(0, 0.01, 0, 0.01, 0, 0.01) + Box(0.02, 0.03, 0, 0.01, 0, 0.01)


CASES = {
    "translate_union": lambda: Translate(union_of_boxes(), x=0.005, y=-0.002, z=0.01),
    "translate_diff": lambda: Translate(
        CylinderZ_hollow(0.011, 0.010, 0.0, 0.02), x=0.003, z=-0.01
    ),
    "translate_einzellens": lambda: Translate(
        Einzellens(radius=0.01, thickness=0.002, length=0.01, gap=0.005), z=0.05
    ),
    "scale_union": lambda: Scale(union_of_boxes(), sx=2, sy=0.5, sz=3),
    "rotate_union": lambda: Rotate(union_of_boxes(), angle=0.3, axis="z"),
    "rotate_y_union": lambda: Rotate(union_of_boxes(), angle=0.7, axis="y"),
    "rotate_x_cone": lambda: Rotate(Cone(0.0, 0.02, 0.01, 0.005), angle=0.4, axis="x"),
    "nested_transforms": lambda: Translate(
        Rotate(
            Translate(Torus(0.01, 0.002) + CylinderZ(0.005, -0.01, 0.01), x=0.01),
            angle=1.1,
            axis="z",
        ),
        y=0.02,
    ),
    "rotate_negative_union": lambda: Rotate(union_of_boxes(), angle=-2.0, axis="z"),
    "torus_negative_z": lambda: Translate(Torus(0.01, 0.002, z_center=-0.05), x=0.001),
    "cone_negative": lambda: Rotate(
        Cone(z1=-0.02, z2=0.02, r1=0.01, r2=0.005), angle=-0.2, axis="x"
    ),
    "scale_around_rounded": lambda: scale_around(
        RoundedCylinderZ_hollow(0.011, 0.009, 0.0, 0.03, 0.0005), sz=2, cz=0.015
    ),
}


@pytest.mark.parametrize("name", CASES)
def test_expression_matches_eval(name):
    obj = CASES[name]()
    x, y, z = random_points(obj)
    expected = obj.eval(x, y, z)
    got = eval_expr(str(obj), x, y, z)
    inside = np.asarray(expected) > 0
    assert np.all(got[inside] > 0)
    assert np.all(got[~inside] < 0)
    # make sure the test actually probes both inside and outside
    assert 0 < np.count_nonzero(expected) < len(x)


def test_translate_does_not_corrupt_max():
    expr = str(Translate(union_of_boxes(), x=0.5))
    assert "max(" in expr
    assert "ma(" not in expr


def test_translate_rz_keeps_coordinates():
    c = CylinderZ_hollow(radius_outer=0.011, radius_inner=0.010, zmin=0.0, zmax=0.01)
    expr = Translate(c + Translate(c, z=0.02), z=0.05).build_expr(rz=True)
    assert "max(" in expr
    assert "y" not in expr
    # outer offset is applied to the coordinates first
    assert "((z-0.05)-0.02)" in expr
    assert "(x-0)" not in expr


def test_translate_negative_offset_has_no_double_minus():
    expr = str(Translate(Box(0, 1, 0, 1, 0, 1), x=-0.5, y=0.25, z=-2))
    assert "--" not in expr
    assert "(x+0.5)" in expr
    assert "(y-0.25)" in expr
    assert "(z+2)" in expr


@pytest.mark.parametrize(
    "obj",
    [
        Rotate(Box(0, 1, 0, 1, 0, 1), angle=-0.3, axis="z"),
        Rotate(Box(0, 1, 0, 1, 0, 1), angle=2.5, axis="y"),
        Rotate(Box(0, 1, 0, 1, 0, 1), angle=-2.5, axis="x"),
        Torus(0.01, 0.002, z_center=-0.05),
        Cone(z1=-0.02, z2=0.02, r1=0.01, r2=0.005),
    ],
)
def test_no_plus_minus_or_double_minus(obj):
    expr = str(obj)
    assert "+-" not in expr
    assert "--" not in expr
    assert "- -" not in expr
    assert "+ -" not in expr


@pytest.mark.parametrize("name", CASES)
def test_expression_is_smooth(name):
    """No 0/1 step functions: no if() and no boolean comparisons."""
    expr = str(CASES[name]())
    assert "if(" not in expr
    assert ">" not in expr
    assert "<" not in expr


@pytest.mark.parametrize("rz", [False, True])
def test_primitive_values_are_signed_distances(rz):
    """Cylinder, box and torus values equal the distance to the surface."""
    y = 0.0
    cyl = Cylinder(radius=0.01)
    assert eval_expr(cyl.build_expr(rz), 0.004, y, 0.0) == pytest.approx(0.006)
    assert eval_expr(cyl.build_expr(rz), 0.013, y, 0.0) == pytest.approx(-0.003)
    box = Box(-0.01, 0.01, -0.01, 0.01, 0.0, 0.1)
    assert eval_expr(box.build_expr(rz), 0.007, y, 0.05) == pytest.approx(0.003)
    torus = Torus(0.02, 0.005, z_center=0.1)
    assert eval_expr(torus.build_expr(rz), 0.02, y, 0.102) == pytest.approx(0.003)


def test_rz_hollow_cylinder_matches_3d_at_y0():
    c = CylinderZ_hollow(radius_outer=0.011, radius_inner=0.010, zmin=0.0, zmax=0.01)
    r = np.linspace(0, 0.02, 101)
    z = np.linspace(-0.005, 0.015, 101)
    R, Z = np.meshgrid(r, z, indexing="ij")
    rz_vals = eval_expr(c.build_expr(rz=True), R, 0.0, Z)
    xyz_vals = eval_expr(c.build_expr(rz=False), R, np.zeros_like(R), Z)
    assert np.allclose(rz_vals, xyz_vals)


def test_intersection_operator():
    a, b = Box(0, 2, 0, 1, 0, 1), Box(1, 3, 0, 1, 0, 1)
    assert str(a * b) == str(Intersection(a, b))


def test_long_unions_are_balanced():
    """Hundreds of electrodes must not create deeply nested expressions."""
    stack = CylinderZ_hollow(0.02, 0.01, 0.0, 0.003)
    for i in range(1, 500):
        stack = stack + CylinderZ_hollow(0.02, 0.01, i * 0.01, i * 0.01 + 0.003)
    depth = max_depth = 0
    for char in str(stack):
        depth += {"(": 1, ")": -1}.get(char, 0)
        max_depth = max(max_depth, depth)
    assert max_depth < 30
    assert stack.signed_value(0.015, 0.0, 4.9915) == pytest.approx(0.0015)
    assert stack.signed_value(0.015, 0.0, 4.995) < 0
