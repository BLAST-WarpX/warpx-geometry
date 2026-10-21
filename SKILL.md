# Agent Guide: WarpX Geometry Package

This document provides guidance for AI agents working with the warpx-geometry codebase.

## Project Overview

**warpx-geometry** is a Python package that provides simple geometry objects for WarpX embedded boundaries. It allows users to easily define 3D geometries as analytical functions for particle-in-cell simulations in both Cartesian (XYZ) and cylindrical (RZ) coordinate systems.

## Core Concepts

### WarpX Embedded Boundary Convention

WarpX uses analytical functions to define conductor boundaries:
- Function returns **> 0** → point is **inside** the conductor
- Function returns **< 0** → point is **outside** the conductor

Every shape builds a smooth function that is > 0 inside, < 0 outside and exactly 0 on
its surface (where practical, the signed distance, e.g. `r - sqrt(x**2 + y**2)`). Shapes
are combined with `max` (union), `min` (intersection) and `min(a, -b)` (difference),
which keep the zero crossing on the combined surface. The result is passed to WarpX
unchanged — no 0/1 step function and no `-0.5` offset. Primitives must be strictly
negative everywhere outside (a region of exact zeros would be treated as surface).
`.eval()` still returns 0/1 for plotting and tests.

### Coordinate Systems

1. **XYZ (Cartesian)**: Full 3D coordinates
   - Used for 3D simulations
   - All shapes work in XYZ

2. **RZ (Cylindrical)**: 2D axially-symmetric
   - Common for beam physics simulations
   - Evaluated at y=0, with x representing radial coordinate r
   - Geometries must be rotationally symmetric around z-axis

## Code Structure

```
src/warpx_geometry/
├── __init__.py           # Package exports and version
├── geometry.py           # Core geometry classes and primitives
├── complex_geometry.py   # Composite geometries (Einzellens, etc.)
├── plot.py               # Older matplotlib helpers (fields, particles, RZ masks, bboxes)
└── viz.py                # plot_2d / plot_3d / geometry_meshes (smooth, from the expression)
examples/                 # Scripts that generate the README images in docs/images/
```

### Key Classes (geometry.py)

- **`BaseObject`**: Base class for all geometric objects
  - `.build_expr(rz, x="x", y="y", z="z")`: WarpX expression string evaluated at the
    given coordinate expressions; `rz=True` gives the RZ form (x = r, no y)
  - `.shape` / `str(obj)`: `build_expr(rz=False)`
  - `.eval(x, y, z)`: Evaluate geometry at points, returns 0 or 1
  - `.signed_value(x, y, z, rz=False)`: evaluate the WarpX expression string itself
    with numpy (`evaluate_expr`) — this is what the viz module plots
  - `.named(name, default_voltage=0)`: name any object (also unions/transforms);
    returns self. A named object registers itself in `collect_named` and hides
    names below it; unnamed composites recurse via `_children()`
  - Operators: `+` (Union), `-` (Diff), `*` (Intersection)

- **Operations**: `Union`, `Diff`, `Intersection`, `Translate`, `Scale`, `Rotate`
  - Combine (`max`/`min`) or transform geometries
  - Transforms pass modified coordinate expressions down the tree via
    `build_expr(rz, x, y, z)`; they never edit the finished string
  - Each has `.eval()` method for numerical evaluation

- **Basic Shapes**: `Cylinder`, `CylinderZ`, `Box`, `Torus`, `Cone`
  - Each defines `.build_expr()` and `.eval()`
  - Shape string uses WarpX/yt syntax

- **Advanced Shapes**: `RoundedCylinderZ`, `CylinderZ_hollow`, etc.
  - Built from combinations of basic shapes
  - Implemented as subclasses of operations (Union, Diff)

- **`Geometry`**: Wrapper that converts to WarpX format
  - `str(Geometry(obj))` gives WarpX-ready function string
  - `rz=True`: enables RZ-optimised expressions and conductor registry
  - `geo.conductors`: dict of named shapes (see Voltage Assignment below)

## Common Development Patterns

### Adding a New Basic Shape

1. Subclass `BaseObject`
2. Define `__init__` to set parameters
3. Implement `.build_expr(rz, x="x", y="y", z="z")` returning a smooth function
   (> 0 inside, < 0 outside, ideally the signed distance). Use the `x`, `y`, `z`
   arguments, never the literal names, so transforms work. Combine several
   conditions with `_min(...)` (the WarpX parser's `min`/`max` take two arguments)
   and use `_shift(coord, offset)` / `_between(coord, lo, hi)` for offsets and ranges
4. Implement `.eval(x, y, z)` method returning 0/1
5. Add tests in `tests/test_xyz_geometry.py` and `tests/test_rz_geometry.py`
6. Export in `__init__.py`

Example:
```python
class Sphere(BaseObject):
    def __init__(self, radius, center_x=0, center_y=0, center_z=0):
        super().__init__()
        self.r = radius
        self.cx, self.cy, self.cz = center_x, center_y, center_z

    def build_expr(self, rz, x="x", y="y", z="z"):
        # signed distance: radius minus distance from the center
        dx, dz = _shift(x, self.cx), _shift(z, self.cz)
        if rz:
            return f"({self.r}-sqrt({dx}**2 + {dz}**2))"
        dy = _shift(y, self.cy)
        return f"({self.r}-sqrt({dx}**2 + {dy}**2 + {dz}**2))"

    def eval(self, x, y, z):
        val = self.r**2 - ((x - self.cx)**2 + (y - self.cy)**2 + (z - self.cz)**2)
        return np.where(val > 0, 1, 0)
```

### Adding a Complex Geometry

1. Subclass an operation (usually `Union` or `Diff`)
2. Build from existing shapes in `__init__`
3. Call `super().__init__()` with the composed geometry — then set `self.name` and
   `self.default_voltage` **after** `super().__init__()` (the base class resets them)
4. Override `collect_named` if the class should register itself when named
5. Add to `complex_geometry.py`

### RZ-Specific Considerations

When working with RZ geometry:
- Evaluate at `y=0` with `x` representing radial coordinate `r`
- Only positive `r` values are meaningful
- Geometry must be symmetric around z-axis
- Test with `R, Z = np.meshgrid(r_vals, z_vals, indexing='ij')`
- Use `X = R, Y = np.zeros_like(R)` for evaluation

### name / default_voltage on shape classes

Shape-leaf classes (`CylinderZ_hollow`, `CylinderZ`, `Einzellens`, …) accept
`name` and `default_voltage` kwargs. Structural classes (`Union`, `Diff`, …) do not.

**Critical**: for compound-based shapes, set `self.name` / `self.default_voltage`
**after** `super().__init__()`, because `BaseObject.__init__()` resets them to
`None` / `0`:

```python
class MyShape(Diff):
    def __init__(self, ..., name=None, default_voltage=0):
        ...
        super().__init__(a, b)   # resets name/default_voltage
        self.name = name         # set AFTER super()
        self.default_voltage = default_voltage
```

### Testing

Tests are organised by coordinate system:
- `test_xyz_geometry.py`: Full 3D Cartesian tests
- `test_rz_geometry.py`: RZ cylindrical coordinate tests
- `test_rz_bbox.py`: RZBBox, BBox.expanded, bboxes_overlap
- `test_build_expr.py`: build_expr(rz) for all shapes
- `test_potential.py`: name/default_voltage, collect_named, to_potential_expr

## Working with the Codebase

### Before Making Changes

1. **Read the existing code**: Understand the pattern used for similar shapes
2. **Check both coordinate systems**: Most changes affect both XYZ and RZ
3. **Review tests**: Understand how shapes are tested

### Making Changes

1. **Add new shapes**: Follow the pattern in `geometry.py`
2. **Modify existing shapes**: Check all places it's used
3. **Update tests**: Both XYZ and RZ tests if applicable
4. **Update exports**: Add to `__init__.py` `__all__` list
5. **Update README**: Add examples if it's user-facing

### Common Pitfalls

1. **Never multiply indicator terms**: `(x>a)*(x<b)` is 0 across the whole outside
   region, which breaks the zero crossing. Use `_min(*_between(x, a, b))` instead

2. **Type annotations**: Original code has minimal type hints
   - `z_center` in `Torus` should accept `float`, not just `int`
   - Some diagnostics show type mismatches

3. **eval() must match build_expr()**: same region, different output
   - `build_expr()` is the signed function string for WarpX
   - `.eval()` is the 0/1 numerical evaluation for plotting/testing
   - `tests/test_transform_expr.py` evaluates the strings with numpy and checks
     they are > 0 exactly where `eval()` is 1 — add new shapes there

4. **RZ symmetry**: Shapes must be rotationally symmetric
   - Can't have features that vary with azimuthal angle
   - Test at y=0 plane only

### Running Tests

```bash
# All tests
uv run pytest

# Specific test file
uv run pytest tests/test_xyz_geometry.py

# Specific test
uv run pytest tests/test_xyz_geometry.py::TestBasicShapes::test_cylinder_center

# With coverage
uv run pytest --cov=warpx_geometry --cov-report=html
```

### Code Quality

```bash
# Format code
uv run ruff format .

# Check style
uv run ruff check .

# Auto-fix
uv run ruff check --fix .
```

## Key Dependencies

- **numpy**: Array operations and numerical evaluation
- **matplotlib**: 3D plotting and visualization
- **pytest**: Testing framework
- **ruff**: Linting and formatting

## Development Workflow

1. Create/modify geometry classes
2. Add/update tests (both XYZ and RZ if applicable)
3. Run tests: `uv run pytest`
4. Format code: `uv run ruff format .`
5. Check style: `uv run ruff check .`
6. Update README if adding user-facing features
7. Update version via git tags (uses hatch-vcs)

## Version Management

This package uses `hatch-vcs` for version management:
- Version is automatically derived from git tags
- Format: `v0.1.0`, `v0.2.0`, etc.
- Don't manually edit version numbers
- Release process: tag commit, push tag

## Integration with WarpX

When helping users integrate with WarpX:

1. **Geometry function string**: `str(Geometry(obj))` produces WarpX-ready function
2. **Coordinate system**: Ensure user's simulation type (XYZ vs RZ) matches geometry
3. **Units**: WarpX typically uses SI units (meters), examples use mm/m
4. **Boundary conditions**: The geometry defines conductor shape; use `to_potential_expr`
   to generate the corresponding potential function string (see Voltage Assignment below)

---

## Voltage Assignment (Named Conductors)

### How it works

Give each shape a `name` when constructing it. `Geometry` traverses the tree and
collects named shapes into `geo.conductors`. Then call `geo.to_potential_expr()` to
produce a WarpX-compatible potential string.

```python
from warpx_geometry import CylinderZ_hollow, Geometry, Union

ring_0 = CylinderZ_hollow(
    radius_outer=0.067, radius_inner=0.051,
    zmin=-0.0005, zmax=0.0005,
    name="ring_0", default_voltage=1600,
)
ring_1 = CylinderZ_hollow(
    radius_outer=0.067, radius_inner=0.051,
    zmin=0.0095, zmax=0.0105,
    name="ring_1", default_voltage=800,
)
tube = CylinderZ_hollow(
    radius_outer=0.100, radius_inner=0.080,
    zmin=-0.1, zmax=0.2,
    name="outer_cyl",   # default_voltage=0 → skipped automatically
)

geo = Geometry(Union(Union(ring_0, ring_1), tube), rz=True)

# Inspect conductors
print(geo.conductors.keys())
# dict_keys(['ring_0', 'ring_1', 'outer_cyl'])

# EB expression
eb_expr = str(geo)

# Potential: use default voltages
pot = geo.to_potential_expr()

# Override at call time
pot = geo.to_potential_expr({"ring_0": 1600, "ring_1": 800})

# Time-varying: string is inserted verbatim
pot = geo.to_potential_expr({"ring_0": "1600 * pulse(t)"})
```

Rules applied automatically by `to_potential_expr`:
- Conductors whose effective voltage is `0` are **skipped**.
- If any pair of (expanded) bboxes overlaps → `max(…)` combination; otherwise `+`.

### Margin

Expand each conductor's voltage region by `margin` metres — useful when the grid
is coarser than the ring thickness:

```python
pot = geo.to_potential_expr({"ring_0": 1600}, margin=0.002)
```

---

## Bounding Boxes

```python
bb = ring_0.rz_bbox
# RZBBox(rmin=0.051, rmax=0.067, zmin=-0.0005, zmax=0.0005)

bb_exp = bb.expanded(0.002)
# RZBBox(rmin=0.049, rmax=0.069, zmin=-0.0025, zmax=0.0025)

# Full-geometry bbox
full_bb = geo.rz_bbox
```

### Overlap check

```python
from warpx_geometry import bboxes_overlap

a_bb = geo.conductors["ring_0"].rz_bbox.expanded(0.002)
b_bb = geo.conductors["ring_1"].rz_bbox.expanded(0.002)
print(bboxes_overlap(a_bb, b_bb))   # True / False
# Touching boundaries (a_bb.zmax == b_bb.zmin) → False (strict inequality)
```

---

## Visualization (viz.py)

`plot_2d(geometry, plane=None, ...)` (matplotlib) and `plot_3d(geometry, ...)`
(pyvista, optional `viz` extra; no VTK wheels on Python 3.15 yet) sample
`signed_value` on a grid and contour at zero. `geometry` can be a shape, a
`Geometry` (uses `rz` and `conductors`; RZ is revolved in 3D) or `{label: obj}`.

- Components: each named conductor is drawn as `min(f_all, f_part)`; the unnamed
  remainder as `min(f_all, -max(f_parts))` (label `None`, shown as "other")
- `colors={name: color, None: color}` or a single color; `color_by="voltage"` with
  `volt_dict`/`default_voltage` and `cmap` (symmetric range if signs are mixed)
- 2D: planes "xz", "yz", "xy", "rz" (z horizontal), `position`, `extent`, `mirror`
- 3D: `clip="y"` etc. intersects with a half-space (closed cut face),
  `resolution` (N along the longest axis, memory ~N^3), `camera_position`,
  `screenshot=` (off-screen), returns the Plotter
- `geometry_meshes` returns `(Component, PolyData)` for tests/export; tests check
  mesh volumes against analytic values

---

## Bounding Box Plotting

### Option A — via `plot_rz_geometry_components`

```python
import matplotlib.pyplot as plt
from warpx_geometry import plot_rz_geometry_components

components = {
    "ring_0":    (ring_0, "red"),
    "outer_cyl": (tube,   "gray"),
}

fig, ax = plt.subplots(figsize=(12, 4))
plot_rz_geometry_components(
    ax, components,
    z_range=(-0.1, 0.2), r_range=(0.0, 0.11),
    bbox_margin=0.002,   # same margin as to_potential_expr
    bbox_kwargs={"linestyle": "--", "linewidth": 1.5},
)
ax.set_xlabel("z (mm)"); ax.set_ylabel("r (mm)")
plt.show()
```

### Option B — standalone `plot_rz_bboxes`

Use this to overlay bboxes on an existing plot (e.g. a field map):

```python
from warpx_geometry import plot_rz_bboxes

# ax already contains a background (contourf / imshow)
plot_rz_bboxes(
    ax, components,
    margin=0.002,
    unit_scale=1000,     # m → mm (must match axis units)
    bbox_kwargs={"linestyle": ":", "linewidth": 2, "alpha": 0.4},
)
```

`bbox_kwargs` accepts any `matplotlib.patches.Rectangle` keyword
(`fill`, `facecolor`, `edgecolor`, `linestyle`, `linewidth`, `alpha`, …).
Infinite bounds are clipped to the current axis limits automatically.

---

## Questions to Ask Users

When a user asks for help:

1. **Coordinate system**: XYZ (3D) or RZ (cylindrical)?
2. **Dimensions**: What are the physical sizes? (remind about SI units)
3. **Purpose**: For WarpX simulation? Visualization? Both?
4. **Existing geometry**: Building on something or starting fresh?
5. **Boolean operations**: Combining shapes? Cutting out regions?

## Example Agent Workflows

### "Help me create a rounded electrode"

1. Identify this needs `RoundedCylinderZ` or `RoundedCylinderZ_hollow`
2. Ask for: outer radius, inner radius (if hollow), length, fillet radius
3. Provide code example with `Geometry` wrapper
4. Suggest visualization with `plot_2d` / `plot_3d` from `warpx_geometry.viz`
5. Show how to use in WarpX

### "My geometry isn't showing up correctly in RZ"

1. Check if they're evaluating at y=0 with x=r
2. Verify geometry is axially symmetric
3. Check if shape is inside out (wrong sign)
4. Suggest `plot_2d(Geometry(obj, rz=True))` for debugging (shows the RZ expression)
5. Verify z and r ranges match simulation domain

### "Add a new shape"

1. Understand the mathematical definition
2. Write both `.build_expr()` (signed function) and `.eval()` (0/1)
3. Create tests for XYZ
4. Create tests for RZ if applicable
5. Add to `__init__.py` exports
6. Update README with example

### "Set up voltages on a multi-electrode system"

1. Confirm each electrode has a `name` kwarg at construction
2. Wrap the combined geometry in `Geometry(..., rz=True)`
3. Call `geo.to_potential_expr(volt_dict, margin=...)` for the potential string
4. Use `str(geo)` for the EB expression
5. Optionally call `plot_rz_geometry_components(..., bbox_margin=...)` to verify regions

## Future Enhancements (TODO from code)

From `geometry.py` docstring:
- Clone/copy functionality
- Color by voltage or object group
- 2D cut plotting with alpha regions for voltages
- Higher resolution plotting options

## Contact and Resources

- **Documentation**: README.md in repository
- **WarpX Docs**: https://warpx.readthedocs.io/
- **Issues**: GitHub issues for bug reports
- **Examples**: See `README.md` for extensive examples
