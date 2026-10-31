# API reference

## Geometry

```{eval-rst}
.. autoclass:: warpx_geometry.Geometry
   :members:
```

## Shapes

```{eval-rst}
.. autoclass:: warpx_geometry.Cylinder
```

```{eval-rst}
.. autoclass:: warpx_geometry.CylinderZ
```

```{eval-rst}
.. autoclass:: warpx_geometry.CylinderZ_hollow
```

```{eval-rst}
.. autoclass:: warpx_geometry.Box
```

```{eval-rst}
.. autoclass:: warpx_geometry.Torus
```

```{eval-rst}
.. autoclass:: warpx_geometry.Cone
```

```{eval-rst}
.. autoclass:: warpx_geometry.RoundedCylinderZ
```

```{eval-rst}
.. autoclass:: warpx_geometry.RoundedCylinderZ_hollow
```

```{eval-rst}
.. autoclass:: warpx_geometry.Einzellens
```

## Operations

```{eval-rst}
.. autoclass:: warpx_geometry.Union
```

```{eval-rst}
.. autoclass:: warpx_geometry.Diff
```

```{eval-rst}
.. autoclass:: warpx_geometry.Intersection
```

## Transforms

```{eval-rst}
.. autoclass:: warpx_geometry.Translate
```

```{eval-rst}
.. autoclass:: warpx_geometry.Scale
```

```{eval-rst}
.. autoclass:: warpx_geometry.Rotate
```

```{eval-rst}
.. autofunction:: warpx_geometry.scale_around
```

```{eval-rst}
.. autofunction:: warpx_geometry.scale_to_bbox_center
```

## Base class

```{eval-rst}
.. autoclass:: warpx_geometry.BaseObject
   :members:
```

## Bounding boxes

```{eval-rst}
.. autoclass:: warpx_geometry.BBox
   :members:
```

```{eval-rst}
.. autoclass:: warpx_geometry.RZBBox
   :members:
```

```{eval-rst}
.. autofunction:: warpx_geometry.bboxes_overlap
```

## Plotting

```{eval-rst}
.. autofunction:: warpx_geometry.viz.plot_2d
```

```{eval-rst}
.. autofunction:: warpx_geometry.viz.plot_3d
```

```{eval-rst}
.. autofunction:: warpx_geometry.viz.geometry_meshes
```

```{eval-rst}
.. autofunction:: warpx_geometry.plot_field2D
```

```{eval-rst}
.. autofunction:: warpx_geometry.plot_particles2D
```

```{eval-rst}
.. autofunction:: warpx_geometry.plot_rz_bboxes
```

```{eval-rst}
.. autofunction:: warpx_geometry.plot_rz_geometry_components
```

```{eval-rst}
.. autofunction:: warpx_geometry.create_rz_geometry_mask
```
