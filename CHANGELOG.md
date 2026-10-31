# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.3.0] - 2026-10-31

First release on PyPI.

### Added

- Automatic publishing to PyPI when a `v*` tag is pushed.
- `LICENSE.txt`, `NOTICE.txt` and `LEGAL.txt`.
- This changelog.

### Changed

- The license identifier is now `BSD-3-Clause-LBNL` instead of `BSD-3-Clause`.
- The repository moved to
  [BLAST-WarpX/warpx-geometry](https://github.com/BLAST-WarpX/warpx-geometry).
- The package version now comes from the git tag, using `hatchling` and `hatch-vcs`
  instead of `uv_build`.
- README images and links are absolute, so they also work on PyPI.

### Fixed

- Numbers in generated expressions are rounded to 12 significant digits, which
  removes round-off noise such as `0.009000000000000001`. `Rotate` also gets exact
  right angles and drops zero terms and unit factors.

## [0.2.0] - 2026-10-21

### Added

- `warpx_geometry.viz` module with `plot_2d` for smooth matplotlib cuts and
  `plot_3d` for pyvista surfaces, including a closed cutaway, revolved RZ geometries
  and screenshots. Named conductors can be colored by name or by voltage. 3D plots
  need the optional `viz` extra.
- `obj.named(name, default_voltage)` for any object, including unions and transforms.
- `a * b` to build an intersection.
- `name` and `default_voltage` on shapes, and `to_potential_expr` for voltage
  assignment.
- `rz` support in `Geometry` through `build_expr(rz)` on all geometry classes.
- `BBox`, `RZBBox` and `bbox_margin`, with `bbox` and `rz_bbox` on all geometry
  classes and `plot_rz_bboxes` to plot them.
- `Scale` and `Rotate` transforms, with the `scale_around` and
  `scale_to_bbox_center` helpers.
- Example scripts for an einzel lens with a Faraday cup and for "warpX" in 3D.
- CI that runs lint and the tests on Python 3.11 to 3.15.

### Changed

- **Breaking:** the EB expression is now a smooth signed function, positive inside,
  negative outside and zero on the surface, instead of a shifted 0/1 step. Shapes are
  combined with `min` and `max`. The sign and zero surface are unchanged, but the
  expression strings look different.
- Python 3.11 to 3.15 are supported.
- Long chains of unions and intersections are emitted as balanced `min`/`max` trees.
- `__version__` now comes from the package metadata.

### Removed

- **Breaking:** `BaseObject.normalize()` and `shape_expr()`. `.shape` and `str(obj)`
  still work.
- **Breaking:** support for Python 3.10.

### Fixed

- `Translate`, `Scale` and `Rotate` no longer corrupt composed expressions, and
  negative values are written as `x+0.5` instead of `x--0.5`.
- `Translate` no longer crashes on composite shapes.
- Swapped Z-cut extent axes and the `NameError` on an invalid `cut_direction` in
  `plot_field2D`.
- `plot_particles2D` now returns `ax` instead of `None`.
