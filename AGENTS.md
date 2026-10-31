# Agent guide: working on warpx-geometry

This guide is for changing the package itself. To use the package, see
`skills/warpx-geometry/SKILL.md`. User documentation is in `docs/`.

## Project structure

```
src/warpx_geometry/
├── __init__.py           # Package exports and version
├── geometry.py           # Core geometry classes and primitives
├── complex_geometry.py   # Composite geometries (Einzellens)
├── plot.py               # Older matplotlib helpers (fields, particles, RZ masks, bboxes)
└── viz.py                # plot_2d / plot_3d / geometry_meshes, from the expression
docs/                     # Sphinx and MyST documentation
examples/                 # Scripts that generate docs/images/
skills/warpx-geometry/    # Skill for people using the package
```

## Core concepts

WarpX treats the implicit function as **> 0** inside a conductor, **< 0** outside and
**0** on its surface.

- Every shape builds a smooth function, where practical the signed distance.
- Shapes combine with `max` (union), `min` (intersection) and `min(a, -b)` (difference).
- Primitives must be strictly negative everywhere outside. A region of exact zeros
  would be treated as surface.
- `.build_expr(rz, x, y, z)` returns the string for WarpX. `.eval(x, y, z)` returns 0/1
  for tests, and `.signed_value(...)` evaluates the string with numpy.
- Transforms pass modified coordinate expressions down the tree. They never edit the
  finished string.
- In RZ, `x` is the radius and there is no `y`.

`Geometry.to_potential_expr` uses each conductor's own expression as its region, in an
`if` chain. WarpX also evaluates the potential inside conductors, so it has to be
constant there. A margin of 0 loses part of the surface, because WarpX evaluates the
potential on a piecewise linear surface.

## Adding a shape

1. Subclass `BaseObject`, or an operation such as `Union` or `Diff` for composites.
2. Validate the parameters with `_check_positive` and `_check_order`.
3. Implement `build_expr(rz, x="x", y="y", z="z")`. Use the arguments, never the literal
   names, so that transforms work. Combine conditions with `_min(...)`, because the
   WarpX parser's `min` and `max` take two arguments. Use `_shift` and `_between` for
   offsets and ranges.
4. Implement `eval`, `bbox` and `rz_bbox`.
5. Export it in `__init__.py`, and add it to `docs/usage/shapes.md` and `docs/api.md`.
6. Add tests in both coordinate systems. `tests/test_transform_expr.py` checks that the
   expression agrees with `eval`.

For composites, set `self.name` and `self.default_voltage` **after**
`super().__init__()`, because `BaseObject.__init__` resets them.

## Common pitfalls

- **Do not multiply indicator terms:** `(x>a)*(x<b)` is 0 across the whole outside
  region, which breaks the zero crossing. Use `_min(*_between(x, a, b))`.
- **`eval` must match `build_expr`:** they describe the same region.
- **RZ needs symmetry:** a transform that breaks it must raise a `ValueError`, not give
  a different shape.
- **Avoid `inf` in expressions:** the WarpX parser rejects it. `_between` skips infinite
  limits.

## Checks

```bash
uv run --extra dev --extra viz pytest
uv run --extra dev ruff format .
uv run --extra dev ruff check --fix .
uv run --extra docs sphinx-build -W -b html docs docs/_build/html
```

`tests/test_docs.py` runs every Python block in the docs. If a change affects users,
update the docs, the skill and `CHANGELOG.md`.

WarpX is not a dependency, and CI does not run it. For changes to the expressions, also
check a real run, for example with `examples/warpx_einzel_lens.py` and WarpX from
conda-forge.

## Releasing

The version comes from the git tag through hatch-vcs, so never set it by hand. Move the
`Unreleased` entries in `CHANGELOG.md` to a new version section, merge to `main`, then
tag the merged commit as `vX.Y.Z` and push the tag. That publishes to PyPI and creates
the GitHub release through `publish.yml`, and rebuilds the docs through `docs.yml`. Versions follow Semantic
Versioning, and the changelog follows Keep a Changelog.
