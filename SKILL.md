# Agent Guide: WarpX Geometry Package

This document provides guidance for AI agents working with the warpx-geometry codebase.

## Project Overview

**warpx-geometry** is a Python package that provides simple geometry objects for WarpX embedded boundaries. It allows users to easily define 3D geometries as analytical functions for particle-in-cell simulations in both Cartesian (XYZ) and cylindrical (RZ) coordinate systems.

## Core Concepts

### WarpX Embedded Boundary Convention

WarpX uses analytical functions to define conductor boundaries:
- Function returns **> 0** → point is **inside** the conductor
- Function returns **< 0** → point is **outside** the conductor

The package internally works with 0/1 values (0=outside, 1=inside) and converts to WarpX convention (subtracting 0.5) in the `Geometry` wrapper class.

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
└── plot.py              # Visualization functions
```

### Key Classes (geometry.py)

- **`BaseObject`**: Base class for all geometric objects
  - `.shape`: String representation of the analytical function
  - `.eval(x, y, z)`: Evaluate geometry at points, returns 0 or 1
  - `.normalize()`: Wraps shape in if-statement for WarpX
  - Supports operators: `+` (Union), `-` (Diff)

- **Operations**: `Union`, `Diff`, `Intersection`, `Translate`
  - Combine or transform geometries
  - Each has `.eval()` method for numerical evaluation

- **Basic Shapes**: `Cylinder`, `CylinderZ`, `Box`, `Torus`, `Cone`
  - Each defines `.shape` string and `.eval()` method
  - Shape string uses WarpX/yt syntax

- **Advanced Shapes**: `RoundedCylinderZ`, `CylinderZ_hollow`, etc.
  - Built from combinations of basic shapes
  - Implemented as subclasses of operations (Union, Diff)

- **`Geometry`**: Wrapper that converts to WarpX format
  - Subtracts 0.5 from values for WarpX convention
  - `str(Geometry(obj))` gives WarpX-ready function string

## Common Development Patterns

### Adding a New Basic Shape

1. Subclass `BaseObject`
2. Define `__init__` to set parameters
3. Set `self.shape` to the analytical function string
4. Implement `.eval(x, y, z)` method
5. Add tests in `tests/test_xyz_geometry.py` and `tests/test_rz_geometry.py`
6. Export in `__init__.py`

Example:
```python
class Sphere(BaseObject):
    def __init__(self, radius, center_x=0, center_y=0, center_z=0):
        super().__init__()
        self.r = radius
        self.cx, self.cy, self.cz = center_x, center_y, center_z
        self.shape = f"({self.r}**2 - ((x-{self.cx})**2 + (y-{self.cy})**2 + (z-{self.cz})**2))"
    
    def eval(self, x, y, z):
        val = self.r**2 - ((x - self.cx)**2 + (y - self.cy)**2 + (z - self.cz)**2)
        return np.where(val > 0, 1, 0)
```

### Adding a Complex Geometry

1. Subclass an operation (usually `Union` or `Diff`)
2. Build from existing shapes in `__init__`
3. Call `super().__init__()` with the composed geometry
4. Add to `complex_geometry.py`

### RZ-Specific Considerations

When working with RZ geometry:
- Evaluate at `y=0` with `x` representing radial coordinate `r`
- Only positive `r` values are meaningful
- Geometry must be symmetric around z-axis
- Test with `R, Z = np.meshgrid(r_vals, z_vals, indexing='ij')`
- Use `X = R, Y = np.zeros_like(R)` for evaluation

### Testing

Tests are organized by coordinate system:
- `test_xyz_geometry.py`: Full 3D Cartesian tests
- `test_rz_geometry.py`: RZ cylindrical coordinate tests

Each test file has sections:
- Basic shapes (individual primitives)
- Boolean operations (Union, Diff, Intersection)
- Transformations (Translate, etc.)
- Advanced shapes (composite objects)
- Complex geometries (Einzellens, etc.)
- Array/meshgrid evaluation

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

1. **Translate implementation**: Uses string replacement, be careful with variable names
   - `x` in `max(x, y)` will also be replaced!
   - TODO: Needs improvement to handle this case

2. **Type annotations**: Original code has minimal type hints
   - `z_center` in `Torus` should accept `float`, not just `int`
   - Some diagnostics show type mismatches

3. **eval() must match .shape**: Both must use same formula
   - `.shape` is the string for WarpX
   - `.eval()` is numerical evaluation for plotting/testing

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
4. **Boundary conditions**: The geometry defines conductor shape, user sets voltage separately

## Future Enhancements (TODO from code)

From `geometry.py` docstring:
- Rotation support (currently only Translation)
- Better Translate implementation (to avoid string replacement issues)
- Intersection operation (partially implemented)
- Clone/copy functionality
- Color by voltage or object group
- 2D cut plotting with alpha regions for voltages
- Higher resolution plotting options

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
4. Suggest visualization with `.plot()` method
5. Show how to use in WarpX

### "My geometry isn't showing up correctly in RZ"

1. Check if they're evaluating at y=0 with x=r
2. Verify geometry is axially symmetric
3. Check if shape is inside out (wrong sign)
4. Suggest using `plot_rz_geometry_components` for debugging
5. Verify z and r ranges match simulation domain

### "Add a new shape"

1. Understand the mathematical definition
2. Write both `.shape` string and `.eval()` method
3. Create tests for XYZ
4. Create tests for RZ if applicable
5. Add to `__init__.py` exports
6. Update README with example

## Contact and Resources

- **Documentation**: README.md in repository
- **WarpX Docs**: https://warpx.readthedocs.io/
- **Issues**: GitHub issues for bug reports
- **Examples**: See `README.md` for extensive examples
