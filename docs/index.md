# warpx-geometry

warpx-geometry builds [WarpX](https://warpx.readthedocs.io/) embedded boundaries from
simple geometry objects. You combine shapes in Python, and the package writes the
analytic expressions that WarpX needs for the geometry and for the voltage on each
conductor. It supports Cartesian (XYZ) and cylindrical (RZ) simulations.

```{figure} images/einzel_lens_faraday_cup_3d.png
:alt: Einzel lens and Faraday cup, 3D cutaway

An einzel lens, a suppressor ring and a Faraday cup, built in RZ and revolved.
```

Every plot shows the same expression that WarpX gets, so what you see is what you
simulate.

## Features

- **Shapes:** cylinders, hollow and rounded cylinders, boxes, cones, tori
- **Boolean operations:** union, difference and intersection
- **Transforms:** translate, scale and rotate
- **Conductors:** named conductors with fixed or time-dependent voltages
- **Plots:** smooth 2D cuts with matplotlib and 3D views with pyvista
- **Components:** a ready-made einzel lens

## Contact

The [GitHub repository](https://github.com/BLAST-WarpX/warpx-geometry) is the place
for [issues](https://github.com/BLAST-WarpX/warpx-geometry/issues) and questions.

```{toctree}
:hidden:
:caption: GETTING STARTED
:maxdepth: 1

install
quickstart
```

```{toctree}
:hidden:
:caption: USAGE
:maxdepth: 1

usage/shapes
usage/rz
usage/voltages
usage/visualization
usage/warpx
usage/examples
usage/ai
```

```{toctree}
:hidden:
:caption: REFERENCE
:maxdepth: 1

api
changelog
```

```{toctree}
:hidden:
:caption: DEVELOPMENT
:maxdepth: 1

development
```
