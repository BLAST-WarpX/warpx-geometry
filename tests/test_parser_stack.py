"""Tests for the WarpX/AMReX parser stack size and the warnings that use it."""

import warnings

import numpy as np
import pytest

import warpx_geometry
from warpx_geometry import (
    AMREX_PARSER_STACK_SIZE,
    CylinderZ,
    Geometry,
    PolygonRZ,
    Torus,
    Translate,
    parser_stack_size,
)


def chain(k):
    """min(sqrt(...(y)), ...) whose stack grows by one per level.

    AMReX evaluates the deeper operand first, here the long sqrt chain, which
    needs one entry, and then the shallower one, which needs one more.
    """
    t = "x"
    for i in range(1, k + 1):
        m = 2 * i - 1
        t = f"min({'sqrt(' * m}y{')' * m}, {t})"
    return t


# expression and the stack size that AMReX 26.08 and 26.11 report
# (Parser::maxStackSize); chain(16) makes AMReX abort
AMREX_STACK = [
    ("x", 1),
    ("x + 1", 1),
    ("min(x, y)", 1),
    ("min(x + 1, y + 2)", 2),
    # AMReX regroups 0.5 + z - x into 0.5 + (z - x), which is deeper than the
    # second operand, so it is evaluated first
    ("min((0.5 + 1*z-x), min(z, (1-z)))", 3),
    # divisions by numbers, as from Scale
    (
        "(x / 0.566734349349 + 0.952190383314) ** 2 + (-0.875897703711 * "
        "(y / 1.21550708703) + 0.482496852459 * (z / 1.48258587934)) ** 2",
        3,
    ),
    ("if(x > 0, 1, if(y > 0, 2, 0))", 1),
    ("if(min(x, y) + max(x, z) > 0, sqrt(x**2 + y**2), 0)", 2),
    (chain(3), 4),
    (chain(15), 16),
    (chain(16), 17),
]


@pytest.mark.parametrize(("expr", "stack"), AMREX_STACK)
def test_matches_amrex(expr, stack):
    assert parser_stack_size(expr) == stack


def test_unsupported_syntax_gives_none():
    assert parser_stack_size("x^2") is None  # another precedence in Python
    assert parser_stack_size("x > 0 and y > 0") is None
    assert parser_stack_size("myfunc(x)") is None
    assert parser_stack_size("(" * 300 + "x" + ")" * 300) is None  # too deep for Python
    assert parser_stack_size("x +") is None


def test_limit():
    assert AMREX_PARSER_STACK_SIZE == 16


def zigzag(n):
    z = np.linspace(0, 1, n)
    top = [(zz, 1.0 + 0.2 * (k % 2)) for k, zz in enumerate(z)]
    return PolygonRZ(top + [(1.0, 0.0), (0.0, 0.0)])


def electrodes(k, n):
    """k named copies of an outline with n + 2 edges, along z."""
    parts = [
        Translate(zigzag(n), z=2 * i).named(f"e{i}", 10 * (i + 1)) for i in range(k)
    ]
    u = parts[0]
    for q in parts[1:]:
        u = u + q
    return u


@pytest.mark.parametrize("rz", [True, False])
def test_geometry_within_the_limit_does_not_warn(rz):
    geo = Geometry(CylinderZ(5, -1, 9) - electrodes(4, 8), rz=rz)
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        geo.build_eb_expr()
        geo.to_potential_expr()
        str(geo)


def test_geometry_above_the_limit_warns():
    # 32 electrodes with 130 edges need 17 entries (measured with AMReX)
    geo = Geometry(CylinderZ(5, -1, 65) - electrodes(32, 128), rz=True)
    with pytest.warns(UserWarning, match="needs 17 entries"):
        geo.build_eb_expr()
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        geo.to_potential_expr()  # one electrode at a time: 12


@pytest.mark.parametrize("rz", [True, False])
def test_warnings_use_the_limit(monkeypatch, rz):
    monkeypatch.setattr(warpx_geometry.parser_stack, "AMREX_PARSER_STACK_SIZE", 7)
    small = Geometry(Torus(2, 0.5).named("t", 100), rz=rz)
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        small.build_eb_expr()
        small.to_potential_expr()
    geo = Geometry(CylinderZ(5, -1, 9) - electrodes(4, 8), rz=rz)
    with pytest.warns(UserWarning, match="embedded-boundary expression needs"):
        geo.build_eb_expr()
    with pytest.warns(UserWarning, match="potential expression needs 8 entries"):
        geo.to_potential_expr()
    with pytest.warns(UserWarning, match="potential expression needs 8 entries"):
        zigzag(8).to_potential_expr(100, rz)
    # the voltages count too
    deep = chain(7)  # 8 entries
    with pytest.warns(UserWarning, match="potential expression needs 8 entries"):
        small.to_potential_expr({"t": deep})


def test_potential_with_many_conductors():
    # The if() chain of 250 conductors is too deep for Python's parser, so
    # each condition and voltage is checked on its own.
    parts = [Translate(Torus(2, 0.3), z=i).named(f"t{i}", i + 1) for i in range(250)]
    u = parts[0]
    for q in parts[1:]:
        u = u + q
    geo = Geometry(u, rz=True)
    pot = geo.to_potential_expr()
    assert parser_stack_size(pot) is None
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        geo.to_potential_expr()
