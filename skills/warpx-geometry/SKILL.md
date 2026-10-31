---
name: warpx-geometry
description: Build WarpX embedded boundaries and electrode voltages with the warpx-geometry Python package. Use when defining conductor geometries, implicit functions, eb_potential expressions, electrodes or einzel lenses for WarpX simulations, or when plotting and debugging them.
---

# warpx-geometry

warpx-geometry writes the analytic expressions that WarpX needs for embedded boundaries
and their voltages. Docs: https://warpx-geometry.readthedocs.io/en/stable/

Install with `pip install warpx-geometry`, or `pip install "warpx-geometry[viz]"` for
3D plots. WarpX is a separate install.

## Workflow

1. Ask for anything missing: XYZ or RZ, dimensions, voltages, and the grid spacing.
2. Build the shapes in **meters**, and name every conductor that needs a voltage.
3. Wrap them in `Geometry(obj, rz=...)`, matching the simulation.
4. Plot with `plot_2d` or `plot_3d`, and have the user check the result.
5. Give the user both strings for WarpX.

```python
from warpx_geometry import CylinderZ_hollow, Einzellens, Geometry
from warpx_geometry.viz import plot_2d

lens = Einzellens(
    radius=0.01, thickness=0.002, length=0.01, gap=0.004, voltages=(0, 5000, 0)
)
tube = CylinderZ_hollow(0.030, 0.028, -0.05, 0.05, name="tube")

geometry = Geometry(lens + tube, rz=True)
plot_2d(geometry, color_by="voltage")

eb_function = str(geometry)
potential = geometry.to_potential_expr()
```

| warpx-geometry | Inputs file | PICMI `EmbeddedBoundary` |
|---|---|---|
| `str(geometry)` | `warpx.eb_implicit_function` | `implicit_function` |
| `geometry.to_potential_expr()` | `warpx.eb_potential(x,y,z,t)` | `potential` |

## Shapes

- `Cylinder(radius)`: infinite, along z
- `CylinderZ(radius, zmin, zmax)`
- `CylinderZ_hollow(radius_outer, radius_inner, zmin, zmax)`
- `Box(xmin, xmax, ymin, ymax, zmin, zmax)`
- `Torus(major_radius, minor_radius, z_center=0)`
- `Cone(z1, z2, r1, r2)`
- `RoundedCylinderZ(radius, zmin, zmax, fillet_radius, fillet_top=True, fillet_bottom=True)`
- `RoundedCylinderZ_hollow(radius_outer, radius_inner, zmin, zmax, fillet_radius, ...)`
- `Einzellens(radius, thickness, length, gap, voltages=(v1, v2, v3))`

Combine with `a + b` (union), `a - b` (difference) and `a * b` (intersection). Transform
with `Translate(obj, x, y, z)`, `Scale(obj, sx, sy, sz)`, `Rotate(obj, angle, axis)`,
`scale_around` and `scale_to_bbox_center`. Angles are in radians.

## Voltages

- Pass `name=` and `default_voltage=` to a shape, or call `.named(name, default_voltage)`
  on anything, including unions and transforms.
- A named object hides names below it, and names must be unique.
- Override with `geometry.to_potential_expr({"name": 2000})`. Strings are used as is, so
  they can depend on `t`, such as `"1600*sin(1e6*t)"`.
- A voltage covers the conductor's own shape and `margin` around its surface. The
  default margin is 1% of the smallest conductor size. Keep it above 0, and below half
  of the smallest gap between conductors.

## RZ rules

- `x` is the radius, and shapes must be symmetric around the z axis.
- `Translate` in z is fine. `Translate` in x only moves rings that stay off the axis.
  `Translate` in y raises.
- `Rotate` around z has no effect, and half turns around x or y flip z. Other rotations
  raise.
- `Scale` needs `sx == sy`.
- A `Box` is a ring from `xmin` to `xmax`.

If one of these raises, build the shape at its final position instead.

## Troubleshooting

- **Shape looks wrong:** plot it with `plot_2d(geometry)`, and check for mm used instead
  of m.
- **`unknown symbol` in WarpX:** a voltage string uses a name WarpX does not know. Define
  it as a WarpX parameter, or pass it to `EmbeddedBoundary` as a keyword argument.
- **Conductor has the wrong voltage:** check that it is named, that `margin` is smaller
  than the gaps, and that the walls are a few cells thick.
- **`MLMG failed`:** use a finer grid, or a looser `required_precision`.
- **`domain size not divisible by blocking_factor`:** use cell counts divisible by 8.
- **Unbounded plot error:** pass `bounds=` or `extent=` for shapes such as `Cylinder`.
