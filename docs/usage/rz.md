# RZ and XYZ

`Geometry(obj)` writes a 3D expression in `x`, `y` and `z`. `Geometry(obj, rz=True)`
writes the shorter RZ form, where `x` is the radius and there is no `y`.

```python
from warpx_geometry import CylinderZ, Geometry

cylinder = CylinderZ(0.01, 0.0, 0.1)

print(Geometry(cylinder))
# min((0.01-sqrt(x**2 + y**2)), min(z, (0.1-z)))
print(Geometry(cylinder, rz=True))
# min((0.01-x), min(z, (0.1-z)))
```

## What RZ allows

An RZ geometry has to be symmetric around the z axis. Transforms that would break
that raise a `ValueError` instead of giving a wrong shape:

| Transform | In RZ |
|---|---|
| `Translate(obj, z=...)` | Allowed |
| `Translate(obj, x=...)` | Moves a ring radially. Raises if the object touches the axis or would reach it |
| `Translate(obj, y=...)` | Raises |
| `Rotate(obj, angle, "z")` | Allowed, has no effect |
| `Rotate(obj, np.pi, "x")` or `"y"` | Allowed, flips z |
| Other rotations around x or y | Raises |
| `Scale(obj, sx=a, sy=a, sz=b)` | Allowed |
| `Scale` with `sx != sy` | Raises |

In RZ, a `Box` is a ring: `xmin` and `xmax` are its radii, and `ymin` and `ymax` are
ignored.

## Evaluating on a grid

`signed_value` evaluates the string that WarpX gets, with `x` as the radius in RZ:

```python
import numpy as np

from warpx_geometry import CylinderZ_hollow

ring = CylinderZ_hollow(0.02, 0.01, 0.0, 0.05)

r = np.linspace(0, 0.03, 50)
z = np.linspace(-0.01, 0.06, 100)
R, Z = np.meshgrid(r, z, indexing="ij")

inside = ring.signed_value(R, 0.0, Z, rz=True) > 0
```
