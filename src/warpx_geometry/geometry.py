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

We make use of this having functions for shapes return either 0 and 1
with 1 inside the conductor. We can then easily add different shapes
together by just using a max(shape1, shape2) call.

We can also create differences between two objects by calculating
A-2*B and then mapping the result back to 0 or 1.

At the very end before handing the function over to warpX, we subtract
0.5 from the values to make sure we get positive and negative values
warpX needs.

TODO: color by voltage or by object number/group

shapes:

* UNION, DIFF, add intersection and perhaps clone or COPY (can we used deepcopy?)
* Cylinder with cuts in Z
* hollow cylinder
* cone
*
* ROTATION
* TRANSLATE (problem with replace and search is that x in max will also be
  replaced). Need to do TRANSLATE similar to eval, e.g. only on most basic
  structures and then with better regexp)
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
            f"bboxes_overlap requires two BBox or two RZBBox objects, got {type(a)} and {type(b)}"
        )


class BaseObject:
    """A BaseObject for geometries in warpX."""

    def __init__(self):
        self.shape = ""

    def __str__(self):
        return self.normalize()

    def __add__(self, other):
        return Union(self, other)

    def __sub__(self, other):
        return Diff(self, other)

    def normalize(self):
        return f"(if({self.shape} > 0, 1, 0))"

    def build_expr(self, rz: bool) -> str:
        """Return the WarpX expression string, optionally in RZ-optimized form."""
        return str(self)

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

    def __str__(self):
        return f"({self.a} * {self.b})"

    def build_expr(self, rz: bool) -> str:
        return f"({self.a.build_expr(rz)} * {self.b.build_expr(rz)})"

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

    def __str__(self):
        return f"(max({self.a}, {self.b}))"

    def build_expr(self, rz: bool) -> str:
        return f"(max({self.a.build_expr(rz)}, {self.b.build_expr(rz)}))"

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

    def __str__(self):
        return f"(if({self.a}-{self.b} > 0.5, 1, 0))"

    def build_expr(self, rz: bool) -> str:
        return f"(if({self.a.build_expr(rz)}-{self.b.build_expr(rz)} > 0.5, 1, 0))"

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


class Translate(BaseObject):
    def __init__(self, obj, x=0, y=0, z=0):
        super().__init__()
        self.obj = obj
        self.dx = x
        self.dy = y
        self.dz = z

    def __str__(self):
        s = str(self.obj)
        s = s.replace("x", f"(x-{self.dx})")
        s = s.replace("y", f"(y-{self.dy})")
        s = s.replace("z", f"(z-{self.dz})")
        return s

    def build_expr(self, rz: bool) -> str:
        s = self.obj.build_expr(rz)
        s = s.replace("x", f"(x-{self.dx})")
        s = s.replace("y", f"(y-{self.dy})")
        s = s.replace("z", f"(z-{self.dz})")
        return s

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

    def __str__(self):
        s = str(self.obj)
        s = s.replace("x", f"(x/{self.sx})")
        s = s.replace("y", f"(y/{self.sy})")
        s = s.replace("z", f"(z/{self.sz})")
        return s

    def build_expr(self, rz: bool) -> str:
        s = self.obj.build_expr(rz)
        if self.sx != 1:
            s = s.replace("x", f"(x/{self.sx})")
        if self.sy != 1:
            s = s.replace("y", f"(y/{self.sy})")
        if self.sz != 1:
            s = s.replace("z", f"(z/{self.sz})")
        return s

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

    def __str__(self):
        c = float(np.cos(self.angle))
        s = float(np.sin(self.angle))
        obj_str = str(self.obj)
        if self.axis == "z":
            # Simultaneous substitution via placeholders to prevent double-replacement
            # (replacing x first would put y into the expression; y replacement
            # would then also corrupt those newly introduced y terms)
            obj_str = obj_str.replace("x", "__X__").replace("y", "__Y__")
            obj_str = obj_str.replace("__X__", f"({c}*x+{s}*y)")
            obj_str = obj_str.replace("__Y__", f"({-s}*x+{c}*y)")
        elif self.axis == "y":
            obj_str = obj_str.replace("x", "__X__").replace("z", "__Z__")
            obj_str = obj_str.replace("__X__", f"({c}*x+{s}*z)")
            obj_str = obj_str.replace("__Z__", f"({-s}*x+{c}*z)")
        elif self.axis == "x":
            obj_str = obj_str.replace("y", "__Y__").replace("z", "__Z__")
            obj_str = obj_str.replace("__Y__", f"({c}*y+{s}*z)")
            obj_str = obj_str.replace("__Z__", f"({-s}*y+{c}*z)")
        else:
            raise ValueError(f"axis must be 'x', 'y', or 'z', got {self.axis!r}")
        return obj_str

    def build_expr(self, rz: bool) -> str:
        c = float(np.cos(self.angle))
        s = float(np.sin(self.angle))
        obj_str = self.obj.build_expr(rz)
        if self.axis == "z":
            obj_str = obj_str.replace("x", "__X__").replace("y", "__Y__")
            obj_str = obj_str.replace("__X__", f"({c}*x+{s}*y)")
            obj_str = obj_str.replace("__Y__", f"({-s}*x+{c}*y)")
        elif self.axis == "y":
            obj_str = obj_str.replace("x", "__X__").replace("z", "__Z__")
            obj_str = obj_str.replace("__X__", f"({c}*x+{s}*z)")
            obj_str = obj_str.replace("__Z__", f"({-s}*x+{c}*z)")
        elif self.axis == "x":
            obj_str = obj_str.replace("y", "__Y__").replace("z", "__Z__")
            obj_str = obj_str.replace("__Y__", f"({c}*y+{s}*z)")
            obj_str = obj_str.replace("__Z__", f"({-s}*y+{c}*z)")
        else:
            raise ValueError(f"axis must be 'x', 'y', or 'z', got {self.axis!r}")
        return obj_str

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
    def __init__(self, radius):
        super().__init__()
        self.radius = radius
        self.shape = f"({self.radius}**2 - (x**2 + y**2))"

    def eval(self, x, y, z):
        val = self.radius**2 - (x**2 + y**2)
        val = np.where(val > 0, 1, 0)
        return val

    @property
    def bbox(self):
        r = self.radius
        return BBox(-r, r, -r, r, -np.inf, np.inf)

    def build_expr(self, rz: bool) -> str:
        if rz:
            return f"(if({self.radius}**2 - x**2 > 0, 1, 0))"
        return str(self)

    @property
    def rz_bbox(self) -> RZBBox:
        return RZBBox(0, self.radius, -np.inf, np.inf)


class CylinderZ(Intersection):
    def __init__(self, radius, zmin, zmax):
        a = Cylinder(radius)
        b = Box(-2 * radius, 2 * radius, -2 * radius, 2 * radius, zmin, zmax)
        super().__init__(a, b)


class CylinderZ_hollow(Diff):
    def __init__(self, radius_outer, radius_inner, zmin, zmax):
        self._r_inner = radius_inner
        self._r_outer = radius_outer
        self._zmin = zmin
        self._zmax = zmax
        a = CylinderZ(radius_outer, zmin, zmax)
        dz = (zmax - zmin) * 0.75  # some extra space
        z_mid = (zmin + zmax) * 0.5
        b = CylinderZ(radius_inner, z_mid - dz, z_mid + dz)
        super().__init__(a, b)

    def build_expr(self, rz: bool) -> str:
        if rz:
            return (
                f"(x > {self._r_inner}) * (x < {self._r_outer})"
                f" * (z > {self._zmin}) * (z < {self._zmax})"
            )
        return str(self)

    @property
    def rz_bbox(self) -> RZBBox:
        return RZBBox(self._r_inner, self._r_outer, self._zmin, self._zmax)


class Box(BaseObject):
    def __init__(self, xmin, xmax, ymin, ymax, zmin, zmax):
        super().__init__()
        self.xmin = xmin
        self.xmax = xmax
        self.ymin = ymin
        self.ymax = ymax
        self.zmin = zmin
        self.zmax = zmax

        self.shape = (
            f"((x>{xmin})*(x<{xmax})*(y>{ymin})*(y<{ymax})*(z>{zmin})*(z<{zmax}))"
        )

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

    def build_expr(self, rz: bool) -> str:
        if rz:
            return (
                f"((x>{self.xmin})*(x<{self.xmax})"
                f"*(z>{self.zmin})*(z<{self.zmax}))"
            )
        return str(self)

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

    def __init__(self, major_radius, minor_radius, z_center=0):
        super().__init__()
        self.R = major_radius
        self.r = minor_radius
        self.z0 = z_center
        # Torus equation: (sqrt(x^2+y^2) - R)^2 + (z-z0)^2 < r^2
        self.shape = (
            f"({self.r}**2 - ((sqrt(x**2 + y**2) - {self.R})**2 + (z - {self.z0})**2))"
        )

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
        return RZBBox(self.R - self.r, self.R + self.r, self.z0 - self.r, self.z0 + self.r)


class Cone(BaseObject):
    """Cone along z-axis from z1 to z2, with radii r1 and r2.

    Parameters:
        z1, z2: Axial extent (z1 < z2)
        r1, r2: Radii at z1 and z2 respectively

    Example:
        # Cone from z=0 to z=0.1m, tapering from 10mm to 5mm radius
        cone = Cone(z1=0.0, z2=0.1, r1=0.010, r2=0.005)
    """

    def __init__(self, z1, z2, r1, r2):
        super().__init__()
        self.z1 = z1
        self.z2 = z2
        self.r1 = r1
        self.r2 = r2
        # Linear interpolation: r(z) = r1 + (r2-r1)*(z-z1)/(z2-z1)
        # Inside cone if: sqrt(x^2+y^2) < r(z) AND z1 < z < z2
        slope = (r2 - r1) / (z2 - z1)
        r_of_z = f"({r1} + {slope}*(z - {z1}))"
        # Note: multiply by (z>z1)*(z<z2) to constrain to axial range
        self.shape = f"(({r_of_z})**2 - (x**2 + y**2)) * (z > {z1}) * (z < {z2})"

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
        self, radius, zmin, zmax, fillet_radius, fillet_top=True, fillet_bottom=True
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

    @property
    def rz_bbox(self) -> RZBBox:
        bb = self.a.rz_bbox  # outer rounded cylinder's rz_bbox
        return RZBBox(self._r_inner, bb.rmax, bb.zmin, bb.zmax)


class Geometry:
    def __init__(self, obj, rz: bool = False):
        self.object = obj
        self.rz = rz

    def build_eb_expr(self) -> str:
        """Return the WarpX embedded-boundary expression string."""
        return f"({self.object.build_expr(rz=self.rz)}-0.5)"

    def __str__(self):
        return self.build_eb_expr()

    @property
    def rz_bbox(self):
        return self.object.rz_bbox

    def eval(self, x, y, z):
        return self.object.eval(x, y, z)

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
