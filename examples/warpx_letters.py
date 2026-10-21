"""Spell "warpX" in 3D, every letter colored differently.

The letters lie in the x-y plane and are extruded along z. They are built
only from boxes, rotated boxes and hollow cylinders, combined with unions
and intersections. Run from the repository root:

    uv run --extra viz python examples/warpx_letters.py
"""

from math import atan2, hypot
from pathlib import Path

from warpx_geometry import Box, CylinderZ_hollow, Geometry, Rotate, Translate
from warpx_geometry.viz import plot_3d

OUT = Path(__file__).resolve().parent.parent / "docs" / "images"

H = 0.010  # x-height of the lower-case letters (m)
T = 0.16 * H  # stroke width
D = 0.30 * H  # extrusion depth along z
GAP = 0.25 * H  # space between letters


def box(x0, x1, y0, y1):
    return Box(x0, x1, y0, y1, -D / 2, D / 2)


def stroke(x0, y0, x1, y1):
    """Straight stroke of width T from (x0, y0) to (x1, y1), extended at both ends."""
    length = hypot(x1 - x0, y1 - y0) + 2 * T
    bar = box(-length / 2, length / 2, -T / 2, T / 2)
    bar = Rotate(bar, atan2(y1 - y0, x1 - x0), axis="z")
    return Translate(bar, x=(x0 + x1) / 2, y=(y0 + y1) / 2)


def ring(cx, cy, r_outer):
    ring = CylinderZ_hollow(r_outer, r_outer - T, -D / 2, D / 2)
    return Translate(ring, x=cx, y=cy)


def letter_w(x):
    w = 1.3 * H
    xs = [x + T / 2, x + 0.25 * w, x + 0.5 * w, x + 0.75 * w, x + w - T / 2]
    ys = [H, 0, H, 0, H]
    strokes = [stroke(xs[i], ys[i], xs[i + 1], ys[i + 1]) for i in range(4)]
    shape = strokes[0] + strokes[1] + strokes[2] + strokes[3]
    # trim the stroke ends flat at the baseline and x-height
    return shape * box(x - T, x + w + T, 0, H), w


def letter_a(x):
    r = H / 2
    bowl = ring(x + r, r, r)
    stem = box(x + 2 * r - T, x + 2 * r, 0, H)
    return bowl + stem, 2 * r


def letter_r(x):
    r = 0.42 * H
    stem = box(x, x + T, 0, H)
    # upper half of a ring, starting at the stem and ending to the right
    arc = ring(x + r, H - r, r) * box(x, x + 1.7 * r, H - r, H)
    return stem + arc, 1.7 * r


def letter_p(x):
    r = H / 2
    stem = box(x, x + T, -0.45 * H, H)
    bowl = ring(x + r, r, r)
    return stem + bowl, 2 * r


def letter_X(x):
    h, w = 1.4 * H, 1.0 * H
    shape = stroke(x, 0, x + w, h) + stroke(x, h, x + w, 0)
    return shape * box(x, x + w, 0, h), w


def build():
    letters = {}
    x = 0.0
    for name, make in zip(
        "warpX", [letter_w, letter_a, letter_r, letter_p, letter_X], strict=True
    ):
        shape, width = make(x)
        letters[name] = shape.named(name)
        x += width + GAP
    obj = letters["w"]
    for name in "arpX":
        obj = obj + letters[name]
    return Geometry(obj)


COLORS = {
    "w": "#4c72b0",
    "a": "#dd8452",
    "r": "#55a868",
    "p": "#c44e52",
    "X": "#8172b3",
}

if __name__ == "__main__":
    geo = build()
    print(f"EB function: {len(geo.build_eb_expr())} characters")
    OUT.mkdir(parents=True, exist_ok=True)
    plot_3d(
        geo,
        colors=COLORS,
        resolution=500,
        legend=False,
        show_axes=False,
        # camera in mm: in front of the letters (+z), slightly above and left
        camera_position=[(12, 28, 75), (31, 5, 0), (0, 1, 0)],
        window_size=(1600, 700),
        screenshot=OUT / "warpx_letters.png",
    )
