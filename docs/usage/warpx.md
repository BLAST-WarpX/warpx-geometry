# Using with WarpX

## The two expressions

| warpx-geometry | Inputs file | PICMI `EmbeddedBoundary` |
|---|---|---|
| `str(geometry)` | `warpx.eb_implicit_function` | `implicit_function` |
| `geometry.to_potential_expr()` | `warpx.eb_potential(x,y,z,t)` | `potential` |

WarpX treats the area where the function is negative as the simulation domain, and the
area where it is positive as the inside of the boundary. See the
[WarpX parameters](https://warpx.readthedocs.io/en/latest/usage/parameters.html) for
details.

Use the same coordinate system in both places: `Geometry(obj, rz=True)` for an RZ
simulation and `Geometry(obj)` for 3D.

## Complete example

This example solves the field of an einzel lens with the middle tube at 5 kV. It is in
the repository as
[`examples/warpx_einzel_lens.py`](https://github.com/BLAST-WarpX/warpx-geometry/blob/main/examples/warpx_einzel_lens.py).

```{literalinclude} ../../examples/warpx_einzel_lens.py
:language: python
:start-at: import matplotlib
:end-before: if __name__
```

The plot it creates shows the potential around the electrodes:

```{figure} ../images/warpx_einzel_lens_potential.png
:alt: Potential of an einzel lens from WarpX

Potential from WarpX, with the electrode outlines in white.
```

## Grid and solver

- Walls should be a few cells thick, so the grid resolves them.
- The cell counts have to be divisible by the blocking factor, which is 8 by default.
- If the multigrid solver stops with `MLMG failed`, use a finer grid or a looser
  `required_precision`. In PICMI this is an argument of `ElectrostaticSolver`, and in
  an inputs file it is `warpx.self_fields_required_precision`.
