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
* TRANSLATE (problem with replace and search is that x in max will also be replaced).
  need to do TRANSLATE similar to eval, e.g. only on most basic structures and then with better regexp)
* Add tests

* plot 2d cuts? Add alpha regions for voltages

* plotting with higher resolution than real deal?

"""

import numpy as np
import matplotlib.pyplot as plt


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

    def eval(self, x, y, z):
        val = eval(self.shape, {"x": x, "y": y, "z": z})
        # in case of Box we get booleans, so we need to convert back
        # Handle both scalar and array inputs
        val = np.asarray(val, dtype=float)
        val = np.where(val > 0, 1, 0)
        return val


class Intersection(BaseObject):
    def __init__(self, a, b):
        self.a = a
        self.b = b

    def __str__(self):
        return f"({self.a} * {self.b})"

    def eval(self, x, y, z):
        a_eval = self.a.eval(x, y, z)
        b_eval = self.b.eval(x, y, z)

        return a_eval * b_eval


class Union(BaseObject):
    def __init__(self, a, b):
        self.a = a
        self.b = b

    def __str__(self):
        return f"(max({self.a}, {self.b}))"

    def eval(self, x, y, z):
        a_eval = self.a.eval(x, y, z)
        b_eval = self.b.eval(x, y, z)

        return np.maximum(a_eval, b_eval)


class Diff(BaseObject):
    def __init__(self, a, b):
        self.a = a
        self.b = b

    def __str__(self):
        return f"(if({self.a}-{self.b} > 0.5, 1, 0))"

    def eval(self, x, y, z):
        a_eval = self.a.eval(x, y, z)
        b_eval = self.b.eval(x, y, z)

        return np.where((a_eval - b_eval) > 0.5, 1, 0)


class Translate(BaseObject):
    def __init__(self, obj, x=0, y=0, z=0):
        self.shape = obj.shape
        self.shape = self.shape.replace("x", f"(x-{x})")
        self.shape = self.shape.replace("y", f"(y-{y})")
        self.shape = self.shape.replace("z", f"(z-{z})")


class Cylinder(BaseObject):
    def __init__(self, radius):
        super().__init__()
        self.radius = radius
        self.shape = f"({self.radius}**2 - (x**2 + y**2))"

    def eval(self, x, y, z):
        val = self.radius**2 - (x**2 + y**2)
        val = np.where(val > 0, 1, 0)
        return val


class CylinderZ(Intersection):
    def __init__(self, radius, zmin, zmax):
        a = Cylinder(radius)
        b = Box(-2 * radius, 2 * radius, -2 * radius, 2 * radius, zmin, zmax)
        super().__init__(a, b)


class CylinderZ_hollow(Diff):
    def __init__(self, radius_outer, radius_inner, zmin, zmax):
        a = CylinderZ(radius_outer, zmin, zmax)
        dz = (zmax - zmin) * 0.75  # some extra space
        z_mid = (zmin + zmax) * 0.5
        b = CylinderZ(radius_inner, z_mid - dz, z_mid + dz)
        super().__init__(a, b)


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
        self.shape = f"({self.r}**2 - ((sqrt(x**2 + y**2) - {self.R})**2 + (z - {self.z0})**2))"

    def eval(self, x, y, z):
        r_xy = np.sqrt(x**2 + y**2)
        val = self.r**2 - ((r_xy - self.R)**2 + (z - self.z0)**2)
        val = np.where(val > 0, 1, 0)
        return val


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
    def __init__(self, radius, zmin, zmax, fillet_radius, fillet_top=True, fillet_bottom=True):
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
                z_center=zmin + fillet_radius
            )
            parts.append(bottom_fillet)

        # Top fillet (torus)
        if fillet_top:
            top_fillet = Torus(
                major_radius=radius - fillet_radius,
                minor_radius=fillet_radius,
                z_center=zmax - fillet_radius
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
    def __init__(self, radius_outer, radius_inner, zmin, zmax, fillet_radius,
                 fillet_top=True, fillet_bottom=True):
        # Outer rounded cylinder
        outer = RoundedCylinderZ(radius_outer, zmin, zmax, fillet_radius, fillet_top, fillet_bottom)

        # Inner cylinder to subtract (make it taller to ensure clean subtraction)
        dz = (zmax - zmin) * 0.75
        z_mid = (zmin + zmax) * 0.5
        inner = CylinderZ(radius_inner, z_mid - dz, z_mid + dz)

        super().__init__(outer, inner)


class Geometry:
    def __init__(self, obj):
        self.object = obj

    def __str__(self):
        return f"({self.object}-0.5)"

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
