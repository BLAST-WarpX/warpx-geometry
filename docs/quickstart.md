# Quick start

All dimensions are in meters. Build a shape, then wrap it in a `Geometry`:

```python
from warpx_geometry import CylinderZ, Geometry

# radius 10 mm, from z=0 to z=100 mm
cylinder = CylinderZ(radius=0.010, zmin=0.0, zmax=0.1)
geometry = Geometry(cylinder)

print(geometry)
# min((0.01-sqrt(x**2 + y**2)), min(z, (0.1-z)))
```

That string is the implicit function for WarpX. It is positive inside the conductor,
negative outside and zero on the surface.

Shapes combine with operators, and naming a shape makes it a conductor with a voltage:

```python
from warpx_geometry import CylinderZ_hollow, Geometry

lens = CylinderZ_hollow(0.011, 0.009, -0.005, 0.005, name="lens", default_voltage=5000)
tube = CylinderZ_hollow(0.030, 0.028, -0.05, 0.05, name="tube")

geometry = Geometry(lens + tube, rz=True)

eb_function = str(geometry)
potential = geometry.to_potential_expr()
```

Hand both strings to WarpX:

```text
warpx.eb_implicit_function = "<eb_function>"
warpx.eb_potential(x,y,z,t) = "<potential>"
```

See [](usage/warpx.md) for a complete simulation.
