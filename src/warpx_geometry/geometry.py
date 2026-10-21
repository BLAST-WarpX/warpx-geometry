"""Simple Geometry objects in warpX

A mechanism to provide simple geometries as an EmbeddedBoundary
object for warpX.

WarpX has the option to define complex shapes as analytical
functions. We use this ability to make it easy to place simple shapes
in the warpX universe and to translate and rotate them.

WarpX uses the following definition when given a function to define an
embedded object. Given x,y,z values to a function the point is either
inside or outside of a conducator depending on:

   > 0 inside the conductor
   < 0 outside of the conductor.

Every primitive returns a smooth function that is positive inside,
negative outside and exactly zero on its surface (where practical, an
approximate signed distance, e.g. r - sqrt(x**2 + y**2) for a cylinder).
Only the sign matters, so shapes are combined with min/max, which keep the
zero crossing exactly on the combined surface:

   union        A | B   ->  max(fA, fB)
   intersection A & B   ->  min(fA, fB)
   difference   A - B   ->  min(fA, -fB)

The result can be handed to warpX directly. Keeping the function smooth
(instead of a 0/1 step) lets AMReX's root finder locate the cut cells
quickly. Primitives must be strictly negative everywhere outside; a region
of exact zeros would be treated as surface.

eval() still returns 0/1 (inside/outside) for plotting and tests.

TODO: color by voltage or by object number/group

shapes:

* UNION, DIFF, add intersection and perhaps clone or COPY (can we used deepcopy?)
* Cylinder with cuts in Z
* hollow cylinder
* cone
*
* ROTATION
* Add tests

* plot 2d cuts? Add alpha regions for voltages

* plotting with higher resolution than real deal?

"""

import matplotlib.pyplot as plt
import numpy as np


class BBox:
    """Axis-aligned bounding box for a geometry object.

    All values in the same units as the geometry (SI, typically meters).
    Unbounded dimensions use +/-np.inf.
    """

    def __init__(self, xmin, xmax, ymin, ymax, zmin, zmax):
        self.xmin = xmin
        self.xmax = xmax
        self.ymin = ymin
        self.ymax = ymax
        self.zmin = zmin
        self.zmax = zmax

    @property
    def cx(self):
        return (self.xmin + self.xmax) / 2

    @property
    def cy(self):
        return (self.ymin + self.ymax) / 2

    @property
    def cz(self):
        return (self.zmin + self.zmax) / 2

    @property
    def center(self):
        return (self.cx, self.cy, self.cz)

    @property
    def size(self):
        return (
            self.xmax - self.xmin,
            self.ymax - self.ymin,
            self.zmax - self.zmin,
        )

    def expanded(self, margin: float) -> "BBox":
        """Return a new BBox enlarged by margin in every direction."""
        return BBox(
            self.xmin - margin,
            self.xmax + margin,
            self.ymin - margin,
            self.ymax + margin,
            self.zmin - margin,
            self.zmax + margin,
        )

    def __repr__(self):
        return (
            f"BBox(x=[{self.xmin}, {self.xmax}], "
            f"y=[{self.ymin}, {self.ymax}], "
            f"z=[{self.zmin}, {self.zmax}])"
        )


class RZBBox:
    """Bounding box in RZ (cylindrical) coordinates.

    Stores (rmin, rmax, zmin, zmax).  rmin >= 0 always.
    Used for potential-expression generation and overlap checks in RZ simulations.
    """

    def __init__(self, rmin: float, rmax: float, zmin: float, zmax: float):
        self.rmin = max(0.0, rmin)
        self.rmax = rmax
        self.zmin = zmin
        self.zmax = zmax

    def expanded(self, margin: float) -> "RZBBox":
        """Return a new RZBBox enlarged by margin in every direction."""
        return RZBBox(
            self.rmin - margin,  # constructor clamps to >= 0
            self.rmax + margin,
            self.zmin - margin,
            self.zmax + margin,
        )

    def __repr__(self):
        return f"RZBBox(r=[{self.rmin}, {self.rmax}], z=[{self.zmin}, {self.zmax}])"


def bboxes_overlap(a, b, tolerance: float = 0) -> bool:
    """Return True if two bounding boxes overlap.

    Works with both BBox and RZBBox objects.

    Args:
        a, b: BBox or RZBBox objects (must be the same type).
        tolerance: Positive value shrinks both boxes before the check
            (useful to verify separation survives a later expansion).
            Negative value is equivalent to an expansion.

    Returns:
        True if the boxes intersect after applying tolerance.
    """
    if isinstance(a, RZBBox) and isinstance(b, RZBBox):
        return (
            a.rmin + tolerance < b.rmax - tolerance
            and b.rmin + tolerance < a.rmax - tolerance
            and a.zmin + tolerance < b.zmax - tolerance
            and b.zmin + tolerance < a.zmax - tolerance
        )
    elif isinstance(a, BBox) and isinstance(b, BBox):
        return (
            a.xmin + tolerance < b.xmax - tolerance
            and b.xmin + tolerance < a.xmax - tolerance
            and a.ymin + tolerance < b.ymax - tolerance
            and b.ymin + tolerance < a.ymax - tolerance
            and a.zmin + tolerance < b.zmax - tolerance
            and b.zmin + tolerance < a.zmax - tolerance
        )
    else:
        raise TypeError(
            "bboxes_overlap requires two BBox or two RZBBox objects, "
            f"got {type(a)} and {type(b)}"
        )


class BaseObject:
    """A BaseObject for geometries in warpX."""

    def __init__(self):
        self.name: str | None = None
        self.default_voltage: float | str = 0

    def __str__(self):
        return self.build_expr(rz=False)

    def __add__(self, other):
        return Union(self, other)

    def __sub__(self, other):
        return Diff(self, other)

    def __mul__(self, other):
        return Intersection(self, other)

    @property
    def shape(self) -> str:
        return self.build_expr(rz=False)

    def build_expr(self, rz: bool, x="x", y="y", z="z") -> str:
        """Return the WarpX expression string, optionally in RZ-optimized form.

        The expression is > 0 inside, < 0 outside and 0 on the surface.
        x, y, z are the coordinate expressions to evaluate the shape at.
        Transforms (Translate, Scale, Rotate) pass modified coordinates down
        the tree instead of rewriting the finished string, mirroring eval().
        """
        raise NotImplementedError(f"{type(self).__name__} must implement build_expr")

    def named(self, name: str, default_voltage: float | str = 0):
        """Set name and default_voltage and return self.

        Works for any object, including unions and transforms, e.g.
        ``Translate(letter, x=0.1).named("w", default_voltage=100)``.
        """
        self.name = name
        self.default_voltage = default_voltage
        return self

    def _children(self) -> tuple:
        """Return the sub-objects this object is built from."""
        return ()

    def collect_named(self, registry: dict) -> None:
        """Populate registry with {name: obj} for all named conductors in this tree.

        A named object registers itself and hides any names below it.
        """
        if self.name is not None:
            registry[self.name] = self
            return
        for child in self._children():
            child.collect_named(registry)

    def signed_value(self, x, y, z, rz: bool = False):
        """Evaluate the WarpX expression numerically (> 0 inside, < 0 outside).

        This evaluates exactly the string WarpX gets. With rz=True, x is the
        radial coordinate.
        """
        return evaluate_expr(self.build_expr(rz), x, y, z)

    def to_potential_expr(self, voltage, rz: bool, margin: float = 0) -> str:
        """Return a WarpX potential expression assigning voltage to this region."""
        if rz:
            bb = self.rz_bbox.expanded(margin)
            return (
                f"(x > {bb.rmin}) * (x < {bb.rmax})"
                f" * (z > {bb.zmin}) * (z < {bb.zmax}) * ({voltage})"
            )
        bb = self.bbox.expanded(margin)
        return (
            f"(x > {bb.xmin}) * (x < {bb.xmax})"
            f" * (y > {bb.ymin}) * (y < {bb.ymax})"
            f" * (z > {bb.zmin}) * (z < {bb.zmax}) * ({voltage})"
        )

    @property
    def bbox(self):
        raise NotImplementedError(f"{type(self).__name__} must implement bbox")

    @property
    def rz_bbox(self) -> RZBBox:
        raise NotImplementedError(f"{type(self).__name__} must implement rz_bbox")


class Intersection(BaseObject):
    def __init__(self, a, b):
        super().__init__()
        self.a = a
        self.b = b

    def build_expr(self, rz: bool, x="x", y="y", z="z") -> str:
        terms = [o.build_expr(rz, x, y, z) for o in _flatten(self, Intersection)]
        return _nest("min", terms)

    def _children(self):
        return (self.a, self.b)

    def eval(self, x, y, z):
        a_eval = self.a.eval(x, y, z)
        b_eval = self.b.eval(x, y, z)

        return a_eval * b_eval

    @property
    def bbox(self):
        a, b = self.a.bbox, self.b.bbox
        return BBox(
            max(a.xmin, b.xmin),
            min(a.xmax, b.xmax),
            max(a.ymin, b.ymin),
            min(a.ymax, b.ymax),
            max(a.zmin, b.zmin),
            min(a.zmax, b.zmax),
        )

    @property
    def rz_bbox(self) -> RZBBox:
        a, b = self.a.rz_bbox, self.b.rz_bbox
        return RZBBox(
            max(a.rmin, b.rmin),
            min(a.rmax, b.rmax),
            max(a.zmin, b.zmin),
            min(a.zmax, b.zmax),
        )


class Union(BaseObject):
    def __init__(self, a, b):
        super().__init__()
        self.a = a
        self.b = b

    def build_expr(self, rz: bool, x="x", y="y", z="z") -> str:
        terms = [o.build_expr(rz, x, y, z) for o in _flatten(self, Union)]
        return _nest("max", terms)

    def _children(self):
        return (self.a, self.b)

    def eval(self, x, y, z):
        a_eval = self.a.eval(x, y, z)
        b_eval = self.b.eval(x, y, z)

        return np.maximum(a_eval, b_eval)

    @property
    def bbox(self):
        a, b = self.a.bbox, self.b.bbox
        return BBox(
            min(a.xmin, b.xmin),
            max(a.xmax, b.xmax),
            min(a.ymin, b.ymin),
            max(a.ymax, b.ymax),
            min(a.zmin, b.zmin),
            max(a.zmax, b.zmax),
        )

    @property
    def rz_bbox(self) -> RZBBox:
        a, b = self.a.rz_bbox, self.b.rz_bbox
        return RZBBox(
            min(a.rmin, b.rmin),
            max(a.rmax, b.rmax),
            min(a.zmin, b.zmin),
            max(a.zmax, b.zmax),
        )


class Diff(BaseObject):
    def __init__(self, a, b):
        super().__init__()
        self.a = a
        self.b = b

    def build_expr(self, rz: bool, x="x", y="y", z="z") -> str:
        a = self.a.build_expr(rz, x, y, z)
        b = self.b.build_expr(rz, x, y, z)
        return f"min({a}, -{b})"

    def _children(self):
        return (self.a, self.b)

    def eval(self, x, y, z):
        a_eval = self.a.eval(x, y, z)
        b_eval = self.b.eval(x, y, z)

        return np.where((a_eval - b_eval) > 0.5, 1, 0)

    @property
    def bbox(self):
        return self.a.bbox

    @property
    def rz_bbox(self) -> RZBBox:
        # Conservative: the subtracted region is interior, overall extent stays a's.
        # Subclasses that know the inner radius (e.g. CylinderZ_hollow) override this.
        return self.a.rz_bbox


def _shift(coord: str, offset) -> str:
    """Return the expression for coord - offset, avoiding a double minus."""
    if offset == 0:
        return coord
    if offset < 0:
        return f"({coord}+{-offset})"
    return f"({coord}-{offset})"


def _lincomb(a, u: str, b, v: str) -> str:
    """Return the expression for a*u + b*v, writing a negative b as a subtraction."""
    op = "-" if b < 0 else "+"
    return f"({a}*{u}{op}{abs(b)}*{v})"


def _nest(func: str, args) -> str:
    """Return func(...) over args as a balanced tree of two-argument calls.

    The WarpX parser's min/max take two arguments; a balanced tree keeps the
    nesting depth at log2(len(args)) even for hundreds of electrodes.
    """
    if len(args) == 1:
        return args[0]
    mid = len(args) // 2
    return f"{func}({_nest(func, args[:mid])}, {_nest(func, args[mid:])})"


def _min(*args: str) -> str:
    return _nest("min", args)


def _flatten(obj, cls) -> list:
    """Return the operands of a chain of cls (e.g. a + b + c) as a flat list."""
    # iterative, so that long chains do not hit the recursion limit
    leaves, stack = [], [obj]
    while stack:
        node = stack.pop()
        if type(node).build_expr is cls.build_expr:
            stack.extend(reversed(node._children()))
        else:
            leaves.append(node)
    return leaves


def evaluate_expr(expr: str, x, y, z):
    """Evaluate a WarpX expression string generated by this package with numpy."""
    namespace = {
        "max": np.maximum,
        "min": np.minimum,
        "sqrt": np.sqrt,
        "x": x,
        "y": y,
        "z": z,
    }
    return eval(expr, {"__builtins__": {}}, namespace)


def _rho(rz: bool, x: str, y: str) -> str:
    """Return the radial distance from the z-axis (x is r in RZ)."""
    return x if rz else f"sqrt({x}**2 + {y}**2)"


def _between(coord: str, lo, hi) -> list[str]:
    """Return terms that are positive for lo < coord < hi (skips infinite bounds)."""
    terms = []
    if np.isfinite(lo):
        terms.append(_shift(coord, lo))
    if np.isfinite(hi):
        terms.append(f"({hi}-{coord})")
    return terms


class Translate(BaseObject):
    def __init__(self, obj, x=0, y=0, z=0):
        super().__init__()
        self.obj = obj
        self.dx = x
        self.dy = y
        self.dz = z

    def build_expr(self, rz: bool, x="x", y="y", z="z") -> str:
        return self.obj.build_expr(
            rz, _shift(x, self.dx), _shift(y, self.dy), _shift(z, self.dz)
        )

    def _children(self):
        return (self.obj,)

    def eval(self, x, y, z):
        return self.obj.eval(x - self.dx, y - self.dy, z - self.dz)

    @property
    def bbox(self):
        b = self.obj.bbox
        return BBox(
            b.xmin + self.dx,
            b.xmax + self.dx,
            b.ymin + self.dy,
            b.ymax + self.dy,
            b.zmin + self.dz,
            b.zmax + self.dz,
        )

    @property
    def rz_bbox(self) -> RZBBox:
        b = self.obj.rz_bbox
        # In RZ, x is the radial coordinate; dx shifts the r-extent.
        return RZBBox(
            b.rmin + self.dx,  # RZBBox constructor clamps to >= 0
            b.rmax + self.dx,
            b.zmin + self.dz,
            b.zmax + self.dz,
        )


class Scale(BaseObject):
    """Scale a geometry object around the origin.

    Parameters:
        obj: Geometry object to scale
        sx, sy, sz: Scale factors per axis (must be > 0)

    Example:
        # Double the radius of a cylinder
        big = Scale(Cylinder(radius=0.01), sx=2, sy=2)
        # Stretch a box in z only
        tall = Scale(box, sz=3)
    """

    def __init__(self, obj, sx=1, sy=1, sz=1):
        super().__init__()
        self.obj = obj
        self.sx = sx
        self.sy = sy
        self.sz = sz

    def build_expr(self, rz: bool, x="x", y="y", z="z") -> str:
        if self.sx != 1:
            x = f"({x}/{self.sx})"
        if self.sy != 1:
            y = f"({y}/{self.sy})"
        if self.sz != 1:
            z = f"({z}/{self.sz})"
        return self.obj.build_expr(rz, x, y, z)

    def _children(self):
        return (self.obj,)

    def eval(self, x, y, z):
        return self.obj.eval(x / self.sx, y / self.sy, z / self.sz)

    @property
    def bbox(self):
        b = self.obj.bbox
        return BBox(
            b.xmin * self.sx,
            b.xmax * self.sx,
            b.ymin * self.sy,
            b.ymax * self.sy,
            b.zmin * self.sz,
            b.zmax * self.sz,
        )

    @property
    def rz_bbox(self) -> RZBBox:
        b = self.obj.rz_bbox
        return RZBBox(
            b.rmin * self.sx,
            b.rmax * self.sx,
            b.zmin * self.sz,
            b.zmax * self.sz,
        )


def scale_around(obj, sx=1, sy=1, sz=1, cx=0, cy=0, cz=0):
    """Scale obj by (sx, sy, sz) around an arbitrary center point.

    Equivalent to: translate to origin, scale, translate back.

    Example:
        # Scale cylinder by 2x in z around its base (z=0)
        scaled = scale_around(cyl, sz=2, cz=0)
    """
    return Translate(
        Scale(Translate(obj, x=-cx, y=-cy, z=-cz), sx, sy, sz),
        x=cx,
        y=cy,
        z=cz,
    )


def scale_to_bbox_center(obj, sx=1, sy=1, sz=1):
    """Scale obj around its own bounding box center.

    Example:
        # Double the size of an electrode around its own center
        big = scale_to_bbox_center(electrode, sx=2, sy=2, sz=2)
    """
    bb = obj.bbox
    return scale_around(obj, sx, sy, sz, bb.cx, bb.cy, bb.cz)


class Rotate(BaseObject):
    """Rotate a geometry object around the x, y, or z axis through the origin.

    Parameters:
        obj: Geometry object to rotate
        angle: Rotation angle in radians (counter-clockwise when viewed from +axis)
        axis: Rotation axis — 'x', 'y', or 'z' (default 'z')

    Example:
        # Rotate a box 45 degrees around the z-axis
        rotated = Rotate(box, angle=np.pi / 4, axis="z")
    """

    def __init__(self, obj, angle, axis="z"):
        super().__init__()
        self.obj = obj
        self.angle = angle
        self.axis = axis

    def build_expr(self, rz: bool, x="x", y="y", z="z") -> str:
        c = float(np.cos(self.angle))
        s = float(np.sin(self.angle))
        if self.axis == "z":
            x, y = _lincomb(c, x, s, y), _lincomb(-s, x, c, y)
        elif self.axis == "y":
            x, z = _lincomb(c, x, s, z), _lincomb(-s, x, c, z)
        elif self.axis == "x":
            y, z = _lincomb(c, y, s, z), _lincomb(-s, y, c, z)
        else:
            raise ValueError(f"axis must be 'x', 'y', or 'z', got {self.axis!r}")
        return self.obj.build_expr(rz, x, y, z)

    def _children(self):
        return (self.obj,)

    def eval(self, x, y, z):
        c, s = np.cos(self.angle), np.sin(self.angle)
        if self.axis == "z":
            return self.obj.eval(c * x + s * y, -s * x + c * y, z)
        elif self.axis == "y":
            return self.obj.eval(c * x + s * z, y, -s * x + c * z)
        elif self.axis == "x":
            return self.obj.eval(x, c * y + s * z, -s * y + c * z)
        else:
            raise ValueError(f"axis must be 'x', 'y', or 'z', got {self.axis!r}")

    @property
    def bbox(self):
        b = self.obj.bbox
        c, s = np.cos(self.angle), np.sin(self.angle)
        if self.axis == "z":
            xs = [b.xmin, b.xmin, b.xmax, b.xmax]
            ys = [b.ymin, b.ymax, b.ymin, b.ymax]
            cx = [c * xi - s * yi for xi, yi in zip(xs, ys, strict=False)]
            cy = [s * xi + c * yi for xi, yi in zip(xs, ys, strict=False)]
            return BBox(min(cx), max(cx), min(cy), max(cy), b.zmin, b.zmax)
        elif self.axis == "y":
            xs = [b.xmin, b.xmin, b.xmax, b.xmax]
            zs = [b.zmin, b.zmax, b.zmin, b.zmax]
            cx = [c * xi - s * zi for xi, zi in zip(xs, zs, strict=False)]
            cz = [s * xi + c * zi for xi, zi in zip(xs, zs, strict=False)]
            return BBox(min(cx), max(cx), b.ymin, b.ymax, min(cz), max(cz))
        else:  # axis == "x"
            ys = [b.ymin, b.ymin, b.ymax, b.ymax]
            zs = [b.zmin, b.zmax, b.zmin, b.zmax]
            cy = [c * yi - s * zi for yi, zi in zip(ys, zs, strict=False)]
            cz = [s * yi + c * zi for yi, zi in zip(ys, zs, strict=False)]
            return BBox(b.xmin, b.xmax, min(cy), max(cy), min(cz), max(cz))

    @property
    def rz_bbox(self) -> RZBBox:
        # Conservative: derive max radial extent from the 3D bbox corners.
        b = self.bbox
        rmax = max(abs(b.xmin), abs(b.xmax), abs(b.ymin), abs(b.ymax))
        return RZBBox(0, rmax, b.zmin, b.zmax)


class Cylinder(BaseObject):
    def __init__(self, radius, name=None, default_voltage=0):
        super().__init__()
        self.radius = radius
        self.name = name
        self.default_voltage = default_voltage

    def eval(self, x, y, z):
        val = self.radius**2 - (x**2 + y**2)
        val = np.where(val > 0, 1, 0)
        return val

    @property
    def bbox(self):
        r = self.radius
        return BBox(-r, r, -r, r, -np.inf, np.inf)

    def build_expr(self, rz: bool, x="x", y="y", z="z") -> str:
        return f"({self.radius}-{_rho(rz, x, y)})"

    @property
    def rz_bbox(self) -> RZBBox:
        return RZBBox(0, self.radius, -np.inf, np.inf)


class CylinderZ(Intersection):
    def __init__(self, radius, zmin, zmax, name=None, default_voltage=0):
        a = Cylinder(radius)
        b = SlabZ(zmin, zmax)
        super().__init__(a, b)
        self.name = name
        self.default_voltage = default_voltage


class SlabZ(BaseObject):
    """Infinite slab zmin < z < zmax (unbounded in x and y)."""

    def __init__(self, zmin, zmax):
        super().__init__()
        self.zmin = zmin
        self.zmax = zmax

    def build_expr(self, rz: bool, x="x", y="y", z="z") -> str:
        return _min(*_between(z, self.zmin, self.zmax))

    def eval(self, x, y, z):
        val = (z > self.zmin) * (z < self.zmax) * np.ones_like(x)
        return np.asarray(val, dtype=float)

    @property
    def bbox(self):
        return BBox(-np.inf, np.inf, -np.inf, np.inf, self.zmin, self.zmax)

    @property
    def rz_bbox(self) -> RZBBox:
        return RZBBox(0, np.inf, self.zmin, self.zmax)


class CylinderZ_hollow(Diff):
    def __init__(
        self, radius_outer, radius_inner, zmin, zmax, name=None, default_voltage=0
    ):
        self._r_inner = radius_inner
        self._r_outer = radius_outer
        self._zmin = zmin
        self._zmax = zmax
        a = CylinderZ(radius_outer, zmin, zmax)
        dz = (zmax - zmin) * 0.75  # some extra space
        z_mid = (zmin + zmax) * 0.5
        b = CylinderZ(radius_inner, z_mid - dz, z_mid + dz)
        super().__init__(a, b)
        self.name = name
        self.default_voltage = default_voltage

    def build_expr(self, rz: bool, x="x", y="y", z="z") -> str:
        rho = _rho(rz, x, y)
        return _min(
            *_between(rho, self._r_inner, self._r_outer),
            *_between(z, self._zmin, self._zmax),
        )

    @property
    def rz_bbox(self) -> RZBBox:
        return RZBBox(self._r_inner, self._r_outer, self._zmin, self._zmax)


class Box(BaseObject):
    def __init__(
        self, xmin, xmax, ymin, ymax, zmin, zmax, name=None, default_voltage=0
    ):
        super().__init__()
        self.name = name
        self.default_voltage = default_voltage
        self.xmin = xmin
        self.xmax = xmax
        self.ymin = ymin
        self.ymax = ymax
        self.zmin = zmin
        self.zmax = zmax

    def eval(self, x, y, z):
        val = (
            (x > self.xmin)
            * (x < self.xmax)
            * (y > self.ymin)
            * (y < self.ymax)
            * (z > self.zmin)
            * (z < self.zmax)
        )
        # Convert to float, handling both scalar and array inputs
        val = np.asarray(val, dtype=float)
        return val

    def build_expr(self, rz: bool, x="x", y="y", z="z") -> str:
        terms = _between(x, self.xmin, self.xmax)
        if not rz:
            terms += _between(y, self.ymin, self.ymax)
        terms += _between(z, self.zmin, self.zmax)
        return _min(*terms)

    @property
    def bbox(self):
        return BBox(self.xmin, self.xmax, self.ymin, self.ymax, self.zmin, self.zmax)

    @property
    def rz_bbox(self) -> RZBBox:
        return RZBBox(max(0.0, self.xmin), self.xmax, self.zmin, self.zmax)


class Torus(BaseObject):
    """Torus with major radius R (distance from z-axis to tube center)
    and minor radius r (tube radius). Axis aligned with z-axis.

    Parameters:
        major_radius: Distance from z-axis to center of tube
        minor_radius: Radius of the tube itself
        z_center: Z-position of the torus center (default 0)

    Example:
        # Torus at z=0.1m with 10mm major radius and 1mm minor radius
        torus = Torus(major_radius=0.010, minor_radius=0.001, z_center=0.1)
    """

    def __init__(
        self, major_radius, minor_radius, z_center=0, name=None, default_voltage=0
    ):
        super().__init__()
        self.name = name
        self.default_voltage = default_voltage
        self.R = major_radius
        self.r = minor_radius
        self.z0 = z_center

    def build_expr(self, rz: bool, x="x", y="y", z="z") -> str:
        # Signed distance to the tube: r - sqrt((rho - R)^2 + (z - z0)^2)
        rho = _rho(rz, x, y)
        return f"({self.r}-sqrt(({rho}-{self.R})**2 + {_shift(z, self.z0)}**2))"

    def eval(self, x, y, z):
        r_xy = np.sqrt(x**2 + y**2)
        val = self.r**2 - ((r_xy - self.R) ** 2 + (z - self.z0) ** 2)
        val = np.where(val > 0, 1, 0)
        return val

    @property
    def bbox(self):
        extent = self.R + self.r
        return BBox(
            -extent, extent, -extent, extent, self.z0 - self.r, self.z0 + self.r
        )

    @property
    def rz_bbox(self) -> RZBBox:
        return RZBBox(
            self.R - self.r, self.R + self.r, self.z0 - self.r, self.z0 + self.r
        )


class Cone(BaseObject):
    """Cone along z-axis from z1 to z2, with radii r1 and r2.

    Parameters:
        z1, z2: Axial extent (z1 < z2)
        r1, r2: Radii at z1 and z2 respectively

    Example:
        # Cone from z=0 to z=0.1m, tapering from 10mm to 5mm radius
        cone = Cone(z1=0.0, z2=0.1, r1=0.010, r2=0.005)
    """

    def __init__(self, z1, z2, r1, r2, name=None, default_voltage=0):
        super().__init__()
        self.name = name
        self.default_voltage = default_voltage
        self.z1 = z1
        self.z2 = z2
        self.r1 = r1
        self.r2 = r2

    def build_expr(self, rz: bool, x="x", y="y", z="z") -> str:
        # Linear interpolation: r(z) = r1 + (r2-r1)*(z-z1)/(z2-z1)
        # Inside cone if: rho < r(z) AND z1 < z < z2
        z1, z2 = self.z1, self.z2
        slope = (self.r2 - self.r1) / (z2 - z1)
        op = "-" if slope < 0 else "+"
        r_of_z = f"{self.r1} {op} {abs(slope)}*{_shift(z, z1)}"
        return _min(f"({r_of_z}-{_rho(rz, x, y)})", *_between(z, z1, z2))

    def eval(self, x, y, z):
        # Linear interpolation of radius
        slope = (self.r2 - self.r1) / (self.z2 - self.z1)
        r_z = self.r1 + slope * (z - self.z1)

        # Inside cone if r_xy < r(z) and z in range
        r_xy = np.sqrt(x**2 + y**2)
        inside_cone = (r_xy < r_z) * (z > self.z1) * (z < self.z2)
        val = inside_cone.astype(float)
        return val

    @property
    def bbox(self):
        rmax = max(self.r1, self.r2)
        return BBox(-rmax, rmax, -rmax, rmax, self.z1, self.z2)

    @property
    def rz_bbox(self) -> RZBBox:
        return RZBBox(0, max(self.r1, self.r2), self.z1, self.z2)


class RoundedCylinderZ(Union):
    """Cylinder with filleted (rounded) edges at top and/or bottom.

    Parameters:
        radius: Cylinder outer radius
        zmin, zmax: Axial extent
        fillet_radius: Radius of the fillet (rounding) at edges
        fillet_top: Add fillet at top (default True)
        fillet_bottom: Add fillet at bottom (default True)

    Example:
        # 10mm radius cylinder from z=0 to z=0.05m with 1mm fillets
        cyl = RoundedCylinderZ(radius=0.010, zmin=0.0, zmax=0.05, fillet_radius=0.001)
    """

    def __init__(
        self,
        radius,
        zmin,
        zmax,
        fillet_radius,
        fillet_top=True,
        fillet_bottom=True,
        name=None,
        default_voltage=0,
    ):
        # Main cylinder body (reduced height to accommodate fillets)
        z_body_min = zmin + (fillet_radius if fillet_bottom else 0)
        z_body_max = zmax - (fillet_radius if fillet_top else 0)
        body = CylinderZ(radius, z_body_min, z_body_max)

        parts = [body]

        # Bottom fillet (torus)
        if fillet_bottom:
            bottom_fillet = Torus(
                major_radius=radius - fillet_radius,
                minor_radius=fillet_radius,
                z_center=zmin + fillet_radius,
            )
            parts.append(bottom_fillet)

        # Top fillet (torus)
        if fillet_top:
            top_fillet = Torus(
                major_radius=radius - fillet_radius,
                minor_radius=fillet_radius,
                z_center=zmax - fillet_radius,
            )
            parts.append(top_fillet)

        # Union all parts
        result = parts[0]
        for part in parts[1:]:
            result = Union(result, part)

        super().__init__(result.a, result.b)
        self.name = name
        self.default_voltage = default_voltage


class RoundedCylinderZ_hollow(Diff):
    """Hollow cylinder with filleted edges.

    Parameters:
        radius_outer: Outer radius
        radius_inner: Inner radius (hollow bore)
        zmin, zmax: Axial extent
        fillet_radius: Radius of fillets
        fillet_top, fillet_bottom: Enable fillets at top/bottom

    Example:
        # Hollow cylinder (tube) with rounded edges
        tube = RoundedCylinderZ_hollow(
            radius_outer=0.011, radius_inner=0.010,
            zmin=0.0, zmax=0.05, fillet_radius=0.001
        )
    """

    def __init__(
        self,
        radius_outer,
        radius_inner,
        zmin,
        zmax,
        fillet_radius,
        fillet_top=True,
        fillet_bottom=True,
        name=None,
        default_voltage=0,
    ):
        self._r_inner = radius_inner
        # Outer rounded cylinder
        outer = RoundedCylinderZ(
            radius_outer, zmin, zmax, fillet_radius, fillet_top, fillet_bottom
        )

        # Inner cylinder to subtract (make it taller to ensure clean subtraction)
        dz = (zmax - zmin) * 0.75
        z_mid = (zmin + zmax) * 0.5
        inner = CylinderZ(radius_inner, z_mid - dz, z_mid + dz)

        super().__init__(outer, inner)
        self.name = name
        self.default_voltage = default_voltage

    @property
    def rz_bbox(self) -> RZBBox:
        bb = self.a.rz_bbox  # outer rounded cylinder's rz_bbox
        return RZBBox(self._r_inner, bb.rmax, bb.zmin, bb.zmax)


class Geometry:
    def __init__(self, obj, rz: bool = False):
        self.object = obj
        self.rz = rz
        self.conductors: dict = {}
        self.object.collect_named(self.conductors)

    def build_eb_expr(self) -> str:
        """Return the WarpX embedded-boundary expression string."""
        return self.object.build_expr(rz=self.rz)

    def __str__(self):
        return self.build_eb_expr()

    @property
    def rz_bbox(self):
        return self.object.rz_bbox

    def eval(self, x, y, z):
        return self.object.eval(x, y, z)

    def to_potential_expr(self, volt_dict=None, margin: float = 0) -> str:
        """Return a combined WarpX potential expression for all named conductors.

        Args:
            volt_dict: mapping of conductor name → voltage (number or string).
                Missing names use the conductor's default_voltage.
            margin: expand each bbox by this amount (m) before generating the
                region mask. Helps ensure grid points overlap the conductor.

        Returns:
            Combined potential expression string, or "0" if all voltages are zero.
        """
        if volt_dict is None:
            volt_dict = {}

        parts = []
        bboxes = []
        for name, obj in self.conductors.items():
            voltage = volt_dict.get(name, obj.default_voltage)
            # Skip purely numeric zeros
            try:
                if float(voltage) == 0.0:
                    continue
            except (TypeError, ValueError):
                pass  # string voltages are never skipped
            parts.append(obj.to_potential_expr(voltage, rz=self.rz, margin=margin))
            bboxes.append(
                obj.rz_bbox.expanded(margin) if self.rz else obj.bbox.expanded(margin)
            )

        if not parts:
            return "0"

        # If any pair of expanded bboxes overlaps, use max() to avoid double-counting
        use_max = any(
            bboxes_overlap(bboxes[i], bboxes[j])
            for i in range(len(bboxes))
            for j in range(i + 1, len(bboxes))
        )

        if use_max:
            result = parts[0]
            for p in parts[1:]:
                result = f"max({result}, {p})"
            return result
        return " + ".join(parts)

    def plot(self, xmin, xmax, Nx, ymin, ymax, Ny, zmin, zmax, Nz):
        x = np.linspace(xmin, xmax, Nx)
        y = np.linspace(ymin, ymax, Ny)
        z = np.linspace(zmin, zmax, Nz)

        X, Y, Z = np.meshgrid(x, y, z, indexing="ij")

        x_edges = np.linspace(xmin, xmax, Nx + 1)
        y_edges = np.linspace(ymin, ymax, Ny + 1)
        z_edges = np.linspace(zmin, zmax, Nz + 1)

        X_edges, Y_edges, Z_edges = np.meshgrid(
            x_edges, y_edges, z_edges, indexing="ij"
        )

        values = self.eval(X, Y, Z)

        fig = plt.figure(figsize=(10, 10))
        ax = fig.add_subplot(111, projection="3d")

        filled = values > 0

        colors = np.empty(filled.shape, dtype=object)
        colors[filled] = "blue"

        ax.voxels(X_edges, Y_edges, Z_edges, filled, facecolors=colors, edgecolor="k")

        ax.set_xlim(xmin, xmax)
        ax.set_ylim(ymin, ymax)
        ax.set_zlim(zmin, zmax)

        ax.set_xlabel("X Axis")
        ax.set_ylabel("Y Axis")
        ax.set_zlabel("Z Axis")

        ax.view_init(elev=10, azim=45, roll=-90)

        plt.show()
