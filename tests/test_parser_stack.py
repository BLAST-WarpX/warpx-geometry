"""Tests for the WarpX/AMReX parser stack size and the warnings that use it."""

import warnings

import numpy as np
import pytest

import warpx_geometry
from warpx_geometry import (
    CylinderZ,
    Geometry,
    PolygonRZ,
    Torus,
    Translate,
    parser_stack_size,
)
from warpx_geometry.parser_stack import AMREX_PARSER_STACK_SIZE


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


# expression and the stack sizes that AMReX 26.08 and 26.11 report
# (Parser::maxStackSize); 26.11 fuses functions of two variables or numbers,
# so it may need one entry less; chain(16) makes AMReX abort
AMREX_STACK = [
    ("x", 1, 1),
    ("x + 1", 1, 1),
    ("min(x, y)", 2, 1),
    ("min(x + 1, y + 2)", 2, 2),
    # AMReX regroups 0.5 + z - x into 0.5 + (z - x), which is deeper than the
    # second operand, so it is evaluated first
    ("min((0.5 + 1*z-x), min(z, (1-z)))", 3, 3),
    # divisions by numbers, as from Scale
    (
        "(x / 0.566734349349 + 0.952190383314) ** 2 + (-0.875897703711 * "
        "(y / 1.21550708703) + 0.482496852459 * (z / 1.48258587934)) ** 2",
        3,
        3,
    ),
    ("if(x > 0, 1, if(y > 0, 2, 0))", 2, 1),
    ("if(min(x, y) + max(x, z) > 0, sqrt(x**2 + y**2), 0)", 3, 2),
    (chain(3), 4, 4),
    (chain(15), 16, 16),
    (chain(16), 17, 17),
    # the grammar: ^ and ** are right associative and bind before a sign,
    # comparisons and and/or have their own levels
    ("2000^2*z", 1, 1),
    ("-x^2", 1, 1),
    ("2^-x", 2, 2),
    ("x**y**z", 2, 2),
    ("x < 1 and y > 2 or z == 3", 3, 2),
    ("pow(x, 3) + atan2(y, x)", 3, 2),
    ("fmod(z, 2) - fabs(x)", 3, 2),
    ("1./(x - 2.e-3) + .5", 1, 1),
    # AMReX rewrites (2*x)/(3*y) as (2/3)*(x/y), which is shallower
    ("2*x/(3*y) + if(x > 0 and y > 0, sqrt(x*y), -1)", 3, 2),
    ("sqrt(x)**2 + (x**2)**3 + x**-1 + y**0 + sin(0.5)*z", 2, 2),
    # deeper than Python's parser allows
    ("(" * 300 + "x" + ")" * 300, 1, 1),
]


@pytest.mark.parametrize(("expr", "stack_2608", "stack_2611"), AMREX_STACK)
def test_matches_amrex(expr, stack_2608, stack_2611):
    # the count of AMReX up to 26.10, an upper bound for 26.11
    assert parser_stack_size(expr) == stack_2608 >= stack_2611


def test_parenthesized_comparison():
    # not a chain since AMReX 26.10 (26.10 and 26.11 need 2; 26.08 chains it)
    assert parser_stack_size("(x < y) < z") == 2


@pytest.mark.parametrize(
    "expr",
    ["myfunc(x)", "x < y < z", "a = 2; a*x", "x +", "x\ny", "sqrt", "x $ y", ""],
)
def test_unsupported_syntax_gives_none(expr):
    assert parser_stack_size(expr) is None


def test_numbers_like_amrex():
    # IEEE results, as in AMReX, instead of Python's exceptions
    assert parser_stack_size("1/(2-2)*x") == 1
    assert parser_stack_size("1" + "0" * 400 + "*x") == 1
    assert parser_stack_size("sqrt(-1) + log(0)*x") == 1


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
    with pytest.warns(UserWarning, match="needs 8 entries.*for the voltage"):
        small.to_potential_expr({"t": deep})


def test_potential_with_many_conductors():
    # Each condition and voltage of the if() chain is checked on its own,
    # which gives the same as the whole chain.
    parts = [Translate(Torus(2, 0.3), z=i).named(f"t{i}", i + 1) for i in range(250)]
    u = parts[0]
    for q in parts[1:]:
        u = u + q
    geo = Geometry(u, rz=True)
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        pot = geo.to_potential_expr()
    assert parser_stack_size(pot) == 2  # also as a whole


@pytest.mark.parametrize(("rz", "stack"), [(True, 3), (False, 4)])
def test_deep_difference_chain(rz, stack):
    # Subtracting one hole at a time nests 300 levels deep, more than Python's
    # parser allows; AMReX reports these stack sizes.
    vac = CylinderZ(5, -1, 65)
    for i in range(300):
        vac = vac - CylinderZ(0.01, 0.1 * i, 0.1 * i + 0.05)
    assert parser_stack_size(vac.build_expr(rz)) == stack


def test_warnings_point_at_the_caller(monkeypatch):
    monkeypatch.setattr(warpx_geometry.parser_stack, "AMREX_PARSER_STACK_SIZE", 7)
    geo = Geometry(CylinderZ(5, -1, 9) - electrodes(4, 8), rz=True)
    for call in (geo.build_eb_expr, lambda: str(geo), geo.to_potential_expr):
        with pytest.warns(UserWarning, match="needs") as record:
            call()
        assert record[0].filename == __file__


def test_unchecked_parts_warn():
    geo = Geometry(Torus(2, 0.5).named("t", "myfunc(t)"), rz=True)
    with pytest.warns(UserWarning, match="could not check"):
        geo.to_potential_expr()


def test_str_uses_build_eb_expr():
    class Clipped(Geometry):
        def build_eb_expr(self):
            return f"min({super().build_eb_expr()}, 1)"

    geo = Clipped(Torus(2, 0.5), rz=True)
    assert str(geo) == geo.build_eb_expr() and str(geo).startswith("min(")


def test_cached():
    expr = chain(5)
    assert parser_stack_size(expr) == parser_stack_size(expr) == 6
