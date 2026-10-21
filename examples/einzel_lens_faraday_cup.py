"""Einzel lens followed by a Faraday cup, in RZ.

Builds the geometry, prints the WarpX expressions and renders a 2D r-z cut
and a 3D cutaway view. Run from the repository root:

    uv run --extra viz python examples/einzel_lens_faraday_cup.py
"""

from pathlib import Path

import matplotlib.pyplot as plt

from warpx_geometry import CylinderZ, CylinderZ_hollow, Geometry
from warpx_geometry.viz import plot_2d, plot_3d

OUT = Path(__file__).resolve().parent.parent / "docs" / "images"

# all dimensions in m
# einzel lens: three tubes, the outer two grounded, the middle one at high voltage
# (warpx_geometry.Einzellens builds the same shape as a single object)
lens = (
    CylinderZ_hollow(0.011, 0.009, -0.019, -0.009, name="lens 1")
    + CylinderZ_hollow(0.011, 0.009, -0.005, 0.005, name="lens 2", default_voltage=5000)
    + CylinderZ_hollow(0.011, 0.009, 0.009, 0.019, name="lens 3")
)

# Faraday cup: tube with a closed back plate (overlapping so there is no seam)
# and a suppressor ring in front of it
cup = CylinderZ_hollow(0.013, 0.011, 0.045, 0.075) + CylinderZ(0.013, 0.074, 0.077)
cup = cup.named("Faraday cup", default_voltage=0)
suppressor = CylinderZ_hollow(
    0.013, 0.007, 0.038, 0.040, name="suppressor", default_voltage=-300
)

geo = Geometry(lens + suppressor + cup, rz=True)
colors = {
    "lens 1": "#4c72b0",
    "lens 2": "#55a868",
    "lens 3": "#4c72b0",
    "suppressor": "#c44e52",
    "Faraday cup": "#dd8452",
}

if __name__ == "__main__":
    print("EB function:", geo.build_eb_expr())
    print("potential:  ", geo.to_potential_expr(margin=0.0005))

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(8, 5.5), layout="constrained")
    plot_2d(geo, mirror=True, colors=colors, ax=ax1)
    ax1.set_title("r-z cut, colored by name")
    plot_2d(geo, mirror=True, color_by="voltage", ax=ax2)
    ax2.set_title("colored by voltage")
    OUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT / "einzel_lens_faraday_cup_rz.png", dpi=150)

    plot_3d(
        geo,
        colors=colors,
        clip="y",
        resolution=500,
        # camera in mm: looking at the cut face (y = 0) with z to the right
        camera_position=[(120, 160, -95), (0, 0, 28), (1, 0, 0)],
        zoom=1.6,
        window_size=(1600, 900),
        screenshot=OUT / "einzel_lens_faraday_cup_3d.png",
    )
