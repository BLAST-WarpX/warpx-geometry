# Shapes and transforms

## Shapes

| Shape | Description |
|---|---|
| `Cylinder(radius)` | Infinite cylinder along z |
| `CylinderZ(radius, zmin, zmax)` | Finite cylinder |
| `CylinderZ_hollow(radius_outer, radius_inner, zmin, zmax)` | Tube |
| `Box(xmin, xmax, ymin, ymax, zmin, zmax)` | Rectangular box |
| `Torus(major_radius, minor_radius, z_center)` | Torus around the z axis |
| `Cone(z1, z2, r1, r2)` | Tapered cylinder with radii `r1` at `z1` and `r2` at `z2` |
| `RoundedCylinderZ(radius, zmin, zmax, fillet_radius)` | Cylinder with rounded edges |
| `RoundedCylinderZ_hollow(radius_outer, radius_inner, zmin, zmax, fillet_radius)` | Tube with rounded outer edges |
| `Einzellens(radius, thickness, length, gap)` | Three tubes that form a lens |

```python
from warpx_geometry import Cone, RoundedCylinderZ, Torus

rounded = RoundedCylinderZ(radius=0.010, zmin=0.0, zmax=0.05, fillet_radius=0.001)
cone = Cone(z1=0.0, z2=0.1, r1=0.010, r2=0.005)
torus = Torus(major_radius=0.010, minor_radius=0.001, z_center=0.1)
```

`RoundedCylinderZ` can leave one end sharp with `fillet_top=False` or
`fillet_bottom=False`. Invalid parameters, such as negative radii or swapped limits,
raise a `ValueError`.

## Boolean operations

| Operator | Class | Result | Expression |
|---|---|---|---|
| `a + b` | `Union(a, b)` | Both objects | `max(fa, fb)` |
| `a - b` | `Diff(a, b)` | `a` without `b` | `min(fa, -fb)` |
| `a * b` | `Intersection(a, b)` | Only the overlap | `min(fa, fb)` |

```python
from warpx_geometry import CylinderZ

outer = CylinderZ(radius=0.011, zmin=0.0, zmax=0.1)
inner = CylinderZ(radius=0.010, zmin=-0.01, zmax=0.11)
tube = outer - inner

electrodes = CylinderZ(0.01, 0.0, 0.02) + CylinderZ(0.01, 0.05, 0.07)
```

Long chains are written as balanced `min`/`max` trees, so systems with hundreds of
electrodes stay shallow for the WarpX parser.

## Transforms

```python
import numpy as np

from warpx_geometry import Box, Rotate, Scale, Translate, scale_around

box = Box(-0.01, 0.01, -0.01, 0.01, -0.02, 0.02)

moved = Translate(box, x=0.02, z=0.1)
stretched = Scale(box, sz=2)
turned = Rotate(box, angle=np.pi / 4, axis="y")
```

`Scale` works around the origin. `scale_around` uses another center, and
`scale_to_bbox_center` uses the center of the object's bounding box. `Rotate` turns
counter-clockwise around an axis through the origin, seen from the positive axis.

## Bounding boxes

Every object has a `bbox`, and `rz_bbox` for RZ. Unbounded directions are `inf`.

```python
from warpx_geometry import CylinderZ_hollow, Geometry, bboxes_overlap

a = CylinderZ_hollow(0.067, 0.051, 0.000, 0.010)
b = CylinderZ_hollow(0.067, 0.051, 0.010, 0.020)

print(a.rz_bbox)
# RZBBox(r=[0.051, 0.067], z=[0.0, 0.01])
print(Geometry(a + b).bbox.size)

# touching does not count as overlapping
assert not bboxes_overlap(a.rz_bbox, b.rz_bbox)
assert bboxes_overlap(a.rz_bbox.expanded(0.001), b.rz_bbox.expanded(0.001))
```
