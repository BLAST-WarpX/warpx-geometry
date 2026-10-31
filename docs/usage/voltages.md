# Voltages

Name a shape to make it a conductor. `Geometry` finds all named shapes, and
`to_potential_expr` writes the potential for them.

```python
from warpx_geometry import CylinderZ_hollow, Geometry

ring_0 = CylinderZ_hollow(
    0.067, 0.051, -0.001, 0.001, name="ring_0", default_voltage=1600
)
ring_1 = CylinderZ_hollow(
    0.067, 0.051, 0.010, 0.012, name="ring_1", default_voltage=800
)
tube = CylinderZ_hollow(0.100, 0.080, -0.1, 0.2, name="tube")

geometry = Geometry(ring_0 + ring_1 + tube, rz=True)

print(list(geometry.conductors))
# ['ring_0', 'ring_1', 'tube']

potential = geometry.to_potential_expr()
```

You can also name anything after building it, including unions and transforms. A named
object hides any names below it:

```python
from warpx_geometry import CylinderZ, CylinderZ_hollow, Geometry

cup = CylinderZ_hollow(0.013, 0.011, 0.045, 0.075) + CylinderZ(0.013, 0.074, 0.077)
cup = cup.named("faraday cup", default_voltage=-300)
```

## Overriding voltages

Pass a dict to override voltages when you write the expression. A string is used as
is, so it can depend on time. Names that do not exist raise a `ValueError`.

```python
potential = geometry.to_potential_expr({"ring_0": 2000})
potential = geometry.to_potential_expr({"ring_0": "1600*sin(1e6*t)"})
```

## Regions and the margin

Each conductor's voltage applies inside its own shape and within `margin` of its
surface. Conductors are written as an `if` chain:

```text
if(f_a > -margin, V_a, if(f_b > -margin, V_b, 0))
```

- Concentric conductors and negative voltages work, because the regions follow the
  shapes.
- If regions overlap, the first conductor wins.
- Conductors at 0 V are left out, and the result is `"0"` if all of them are at 0 V.
- WarpX also evaluates the potential inside conductors. It is constant there, as WarpX
  requires.

WarpX evaluates the potential on a piecewise linear version of the surface, so a
margin of 0 loses part of the surface. By default, `margin` is 1% of the smallest
conductor size, which covers that error when the grid resolves the conductors. Set it
yourself if conductors are close together, and keep it below half of the smallest gap:

```python
potential = geometry.to_potential_expr(margin=0.0002)
```

`margin` is a distance in meters. For transformed shapes it is approximate, since a
`Scale` also scales the signed function.
