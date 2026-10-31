# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- The release workflow creates a GitHub release with the changelog entry and the built
  files, and stops before publishing if the changelog has no entry for the version.

## [0.4.0] - 2026-10-31

### Added

- `Einzellens(..., voltages=(v1, v2, v3))` names the three tubes and sets their
  voltages.
- `Geometry.bbox` and a readable `repr` for shapes and `Geometry`.
- `examples/warpx_einzel_lens.py`, a complete WarpX run through PICMI.
- `title` and `color` arguments for `plot_particles2D`.
- Documentation on Read the Docs, written in Markdown with Sphinx and MyST.
- A skill for AI assistants in `skills/warpx-geometry/`, and `AGENTS.md` for working on
  the package, which replaces `SKILL.md`.
- A workflow that builds the docs and rebuilds them for each release.

### Changed

- **Breaking:** `to_potential_expr` now uses each conductor's own shape as its
  region instead of its bounding box, and `margin` is the distance from the surface.
  The default `margin` is 1% of the smallest conductor size. Conductors are combined
  with an `if` chain, so the expression strings look different.
- **Breaking:** transforms that RZ geometry cannot represent now raise a `ValueError`:
  `Translate` in y, `Translate` in x of a shape on the axis, `Rotate` that tilts the
  z axis, and `Scale` with `sx != sy`.
- **Breaking:** invalid shape parameters now raise a `ValueError`, such as negative
  radii, swapped limits, a `Scale` of 0 or fillets that do not fit. A hollow cylinder
  needs an inner radius larger than 0.
- **Breaking:** duplicate conductor names and unknown names in `volt_dict` now raise
  a `ValueError`.
- **Breaking:** `plot_particles2D` no longer sets a "Protons" title by default.

- The README is shorter, and its guides moved to the documentation. The instructions
  for WarpX now use the correct parameter names.

### Fixed

- Conductors in `to_potential_expr` kept the wrong voltage when bounding boxes
  overlapped: negative voltages were lost, and concentric conductors in XYZ got the
  voltage of the outer one.
- Named infinite shapes wrote `inf` into the potential, which WarpX rejects.
- `RoundedCylinderZ` and `RoundedCylinderZ_hollow` no longer have a dish in their end
  caps, and `RoundedCylinderZ` with both fillets off is a finite cylinder.
- `Rotate.bbox` no longer returns `nan` for infinite shapes, and is exact at right
  angles.

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
