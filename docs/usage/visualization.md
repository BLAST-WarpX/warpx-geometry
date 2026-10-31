# Visualization

`plot_2d` (matplotlib) and `plot_3d` (pyvista) evaluate the WarpX expression on a grid
and contour it at zero, so the outlines are smooth. Both accept a shape, a `Geometry`
or a dict `{label: object}`. Named conductors are separate components.

## 2D cuts

```python
import matplotlib.pyplot as plt

from warpx_geometry import CylinderZ, CylinderZ_hollow, Geometry
from warpx_geometry.viz import plot_2d

lens = CylinderZ_hollow(0.011, 0.009, -0.005, 0.005, name="lens", default_voltage=5000)
cup = CylinderZ_hollow(0.013, 0.011, 0.02, 0.05) + CylinderZ(0.013, 0.049, 0.052)
geometry = Geometry(lens + cup.named("cup"), rz=True)

# r-z cut by default for RZ; mirror also shows negative r
ax = plot_2d(geometry, mirror=True, colors={"lens": "tab:blue", "cup": "tab:orange"})

# colorbar from the conductor voltages
ax = plot_2d(geometry, color_by="voltage")

plt.savefig("geometry.pdf")  # vector output
```

Other planes are `"xz"`, `"yz"` and `"xy"`, with `position=` for the location of the
cut.

```{figure} ../images/einzel_lens_faraday_cup_rz.png
:alt: r-z cuts colored by name and by voltage

Cuts colored by name and by voltage.
```

## 3D views

3D plots need the `viz` extra. `clip="y"` cuts away one half to look inside, and RZ
geometries are revolved around the axis.

```python
from warpx_geometry.viz import plot_3d

plot_3d(geometry, clip="y", resolution=100, screenshot="geometry.png")
```

Without `screenshot`, this opens an interactive window.

## Options

- `resolution`: grid points along the longest axis. About 100 is enough for a quick
  check and 300 or more for figures.
- `bounds`, or `extent` for `plot_2d`: required for unbounded shapes such as `Cylinder`.
- `units`: `"mm"` by default.
- `camera_position`, `view` and `zoom`: set the 3D view.
- `plotter`: adds to an existing pyvista scene.

`geometry_meshes` returns the surface meshes for custom rendering or export.

## Older RZ helpers

`plot_rz_geometry_components` fills components on an existing axis, for example on top
of a field map. `plot_rz_bboxes` draws their bounding boxes. Axis units are mm.

```python
import matplotlib.pyplot as plt

from warpx_geometry import CylinderZ_hollow, plot_rz_geometry_components

tube = CylinderZ_hollow(0.020, 0.018, 0.0, 0.2)
electrode = CylinderZ_hollow(0.016, 0.014, 0.08, 0.12)

fig, ax = plt.subplots()
plot_rz_geometry_components(
    ax,
    {"tube": (tube, "lightgray"), "electrode": (electrode, "red")},
    z_range=(0.0, 0.2),
    r_range=(0.0, 0.025),
    bbox_margin=0,
)
```
