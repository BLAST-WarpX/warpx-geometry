"""Electrostatic field of an einzel lens, solved with WarpX in RZ.

Builds the lens with warpx-geometry, hands the embedded boundary and its voltages
to WarpX through PICMI, and plots the resulting potential. WarpX is not a dependency
of this package; install it as described in the WarpX documentation, for example:

    conda install -c conda-forge warpx
    pip install warpx-geometry
    python examples/warpx_einzel_lens.py
"""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from pywarpx import fields, picmi

from warpx_geometry import Einzellens, Geometry

OUT = Path(__file__).resolve().parent.parent / "docs" / "images"

# all dimensions in m, voltages in V
lens = Einzellens(
    radius=0.01,
    thickness=0.002,
    length=0.01,
    gap=0.004,
    voltages=(0, 5000, 0),
)
geo = Geometry(lens, rz=True)

# the expressions are plain strings: use them directly in PICMI or in an inputs file
#   warpx.eb_implicit_function = "..."
#   warpx.eb_potential(x,y,z,t) = "..."
embedded_boundary = picmi.EmbeddedBoundary(
    implicit_function=str(geo),
    potential=geo.to_potential_expr(),
)

grid = picmi.CylindricalGrid(
    number_of_cells=[64, 208],
    lower_bound=[0.0, -0.05],
    upper_bound=[0.03, 0.05],
    lower_boundary_conditions=["none", "dirichlet"],
    upper_boundary_conditions=["dirichlet", "dirichlet"],
    lower_boundary_conditions_particles=["none", "absorbing"],
    upper_boundary_conditions_particles=["absorbing", "absorbing"],
    warpx_max_grid_size=208,
)
solver = picmi.ElectrostaticSolver(
    grid=grid, method="Multigrid", required_precision=1e-3
)
sim = picmi.Simulation(
    solver=solver,
    time_step_size=1e-10,
    max_steps=1,
    warpx_embedded_boundary=embedded_boundary,
)

if __name__ == "__main__":
    sim.step(1)

    phi = fields.PhiFPWrapper()[:, :]
    r = np.linspace(0, 0.03, phi.shape[0])
    z = np.linspace(-0.05, 0.05, phi.shape[1])

    fig, ax = plt.subplots(figsize=(8, 3), layout="constrained")
    mesh = ax.pcolormesh(z * 1e3, r * 1e3, phi, cmap="viridis")
    ax.contour(
        z * 1e3,
        r * 1e3,
        lens.signed_value(r[:, None], 0.0, z[None, :], rz=True),
        levels=[0],
        colors="white",
    )
    ax.set_xlabel("z (mm)")
    ax.set_ylabel("r (mm)")
    fig.colorbar(mesh, label="potential (V)")
    OUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT / "warpx_einzel_lens_potential.png", dpi=150)

    print(f"potential from {phi.min():.0f} V to {phi.max():.0f} V")
