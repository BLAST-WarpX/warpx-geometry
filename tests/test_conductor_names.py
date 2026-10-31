"""Tests for mistakes with conductor names."""

import pytest

from warpx_geometry import Box, Geometry


def box(name, x=0, voltage=1):
    return Box(x, x + 1, 0, 1, 0, 1, name=name, default_voltage=voltage)


def test_duplicate_names_raise():
    with pytest.raises(ValueError, match="'a'"):
        Geometry(box("a") + box("a", x=2))


def test_same_object_used_twice_is_fine():
    a = box("a")
    assert list(Geometry(a + a).conductors) == ["a"]


def test_unknown_voltage_name_raises():
    geo = Geometry(box("a"))
    with pytest.raises(ValueError, match="typo"):
        geo.to_potential_expr({"typo": 5})
