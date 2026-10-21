"""Smooth 2D and 3D visualization of geometry objects.

Both plots evaluate exactly the expression string that is handed to WarpX
(``BaseObject.build_expr``) on a grid. Because the expressions are smooth
signed functions (> 0 inside, < 0 outside), contouring them at zero gives
smooth outlines (2D, matplotlib) and smooth surfaces (3D, pyvista), and what
you see is what WarpX gets.

Named conductors (``name=...`` or ``.named(...)``) are drawn as separate
components that can be colored individually, either by name or by voltage.
Anything that is not part of a named conductor is drawn in ``default_color``.

``plot_2d`` only needs matplotlib. ``plot_3d`` and ``geometry_meshes`` need
pyvista: ``pip install "warpx-geometry[viz]"``.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from matplotlib import colors as mcolors
from matplotlib import pyplot as plt
from matplotlib.cm import ScalarMappable
from matplotlib.patches import Patch

from .geometry import BaseObject, Geometry, Union

UNITS = {"m": 1.0, "cm": 1e2, "mm": 1e3, "um": 1e6}
PALETTE = plt.get_cmap("tab10").colors

# plane -> (horizontal axis, vertical axis); z is horizontal (beam axis)
PLANES = {"xz": ("z", "x"), "yz": ("z", "y"), "xy": ("x", "y"), "rz": ("z", "r")}


@dataclass
class Component:
    """One separately colored part of a geometry."""

    label: str | None  # None for the unnamed remainder
    voltage: float | str | None
    field: np.ndarray  # signed function on the grid


def _resolve(geometry, rz):
    """Return (whole object, rz, {label: object}) for any supported input."""
    if isinstance(geometry, Geometry):
        whole, default_rz, named = geometry.object, geometry.rz, geometry.conductors
    elif isinstance(geometry, BaseObject):
        whole, default_rz, named = geometry, False, {}
        geometry.collect_named(named)
    elif isinstance(geometry, dict):
        objs = list(geometry.values())
        whole = objs[0]
        for obj in objs[1:]:
            whole = Union(whole, obj)
        default_rz, named = False, geometry
    else:
        raise TypeError(
            "expected a geometry object, a Geometry or a dict {label: object}, "
            f"got {type(geometry).__name__}"
        )
    return whole, default_rz if rz is None else rz, dict(named)


def _field(obj, rz, X, Y, Z):
    if rz:
        # revolve the RZ expression around the z-axis
        f = obj.signed_value(np.sqrt(X**2 + Y**2), Y, Z, rz=True)
    else:
        f = obj.signed_value(X, Y, Z)
    return np.broadcast_to(f, np.broadcast_shapes(X.shape, Y.shape, Z.shape))


def _components(geometry, rz, X, Y, Z, volt_dict=None, clip_field=None):
    """Evaluate the geometry on the grid, split into named components."""
    whole, rz, named = _resolve(geometry, rz)
    volt_dict = volt_dict or {}
    f_all = _field(whole, rz, X, Y, Z)
    if clip_field is not None:
        f_all = np.minimum(f_all, clip_field)
    if not named:
        return [Component(None, None, f_all)]

    parts = []
    f_named = None
    for label, obj in named.items():
        f = _field(obj, rz, X, Y, Z)
        f_named = f if f_named is None else np.maximum(f_named, f)
        voltage = volt_dict.get(label, obj.default_voltage)
        # intersect with the whole geometry so differences are respected
        parts.append(Component(label, voltage, np.minimum(f_all, f)))
    rest = np.minimum(f_all, -f_named)
    if np.any(rest > 0):
        parts.append(Component(None, None, rest))
    return parts


def _bounds(geometry, rz, margin=0.05):
    """Return (xmin, xmax, ymin, ymax, zmin, zmax) from the bounding box."""
    whole, rz, _ = _resolve(geometry, rz)
    if rz:
        bb = whole.rz_bbox
        b = [-bb.rmax, bb.rmax, -bb.rmax, bb.rmax, bb.zmin, bb.zmax]
    else:
        bb = whole.bbox
        b = [bb.xmin, bb.xmax, bb.ymin, bb.ymax, bb.zmin, bb.zmax]
    if not np.all(np.isfinite(b)):
        raise ValueError(
            f"the geometry is unbounded ({b}); pass bounds=(xmin, xmax, ymin, "
            "ymax, zmin, zmax) (or extent=... for plot_2d)"
        )
    pad = margin * max(b[1] - b[0], b[3] - b[2], b[5] - b[4])
    return (b[0] - pad, b[1] + pad, b[2] - pad, b[3] + pad, b[4] - pad, b[5] + pad)


def _voltage_range(parts):
    values = [float(p.voltage) for p in parts if _is_number(p.voltage)]
    if not values:
        return -1.0, 1.0
    vmin, vmax = min(values), max(values)
    if vmin < 0 < vmax:
        a = max(-vmin, vmax)
        return -a, a
    if vmin == vmax:
        return vmin - 1, vmax + 1
    return vmin, vmax


def _is_number(value):
    try:
        float(value)
    except (TypeError, ValueError):
        return False
    return True


def _assign_colors(parts, colors, color_by, cmap, default_color):
    """Return one color per component."""
    if color_by == "voltage":
        cmap = plt.get_cmap(cmap)
        norm = mcolors.Normalize(*_voltage_range(parts))
        return [
            cmap(norm(float(p.voltage))) if _is_number(p.voltage) else default_color
            for p in parts
        ]
    if color_by != "name":
        raise ValueError(f"color_by must be 'name' or 'voltage', got {color_by!r}")
    if isinstance(colors, str) or isinstance(colors, tuple):
        return [colors] * len(parts)
    colors = colors or {}
    result = []
    n_named = 0
    for p in parts:
        if p.label is None:
            result.append(colors.get(None, default_color))
        else:
            result.append(colors.get(p.label, PALETTE[n_named % len(PALETTE)]))
            n_named += 1
    return result


def plot_2d(
    geometry,
    plane: str | None = None,
    position: float = 0.0,
    *,
    extent=None,
    resolution: int = 800,
    colors=None,
    color_by: str = "name",
    volt_dict: dict | None = None,
    cmap="coolwarm",
    default_color="0.6",
    outline: bool = True,
    outline_color="k",
    linewidth: float = 0.8,
    legend: bool = True,
    units: str = "mm",
    mirror: bool = False,
    rz: bool | None = None,
    ax=None,
):
    """Plot a smooth 2D cut through a geometry with matplotlib.

    Args:
        geometry: a geometry object, a ``Geometry`` (uses its ``rz`` setting
            and named conductors) or a dict ``{label: object}``.
        plane: "xz", "yz", "xy" or "rz". z is the horizontal axis for planes
            containing it. Defaults to "rz" for RZ geometries, else "xz".
        position: coordinate of the cut along the remaining axis (m), e.g. y
            for the "xz" plane.
        extent: (hmin, hmax, vmin, vmax) in m; defaults to the bounding box.
        resolution: grid points along the longer axis.
        colors: {name: color} for named conductors (use the key None for the
            unnamed remainder), or one color for everything. Unlisted names
            get colors from the tab10 palette.
        color_by: "name" or "voltage" (colors from ``cmap`` by voltage, with
            a colorbar; voltages from ``volt_dict`` or ``default_voltage``).
        default_color: color for unnamed parts and non-numeric voltages.
        outline: draw the zero contour (the surface WarpX sees).
        units: axis units, one of "m", "cm", "mm", "um".
        mirror: for the "rz" plane, also show negative r.
        rz: override the RZ setting of a ``Geometry``.
        ax: matplotlib axes to draw into.

    Returns:
        The matplotlib axes.
    """
    _, is_rz, _ = _resolve(geometry, rz)
    plane = plane or ("rz" if is_rz else "xz")
    if plane not in PLANES:
        raise ValueError(f"plane must be one of {list(PLANES)}, got {plane!r}")
    h_axis, v_axis = PLANES[plane]
    scale = UNITS[units]

    if extent is None:
        b = _bounds(geometry, rz)
        lims = {"x": b[0:2], "y": b[2:4], "z": b[4:6], "r": (0.0, b[1])}
        if plane == "rz" and mirror:
            lims["r"] = (-b[1], b[1])
        extent = (*lims[h_axis], *lims[v_axis])
    hmin, hmax, vmin, vmax = extent

    n_h = n_v = resolution
    if hmax - hmin > vmax - vmin:
        n_v = max(2, int(resolution * (vmax - vmin) / (hmax - hmin)))
    else:
        n_h = max(2, int(resolution * (hmax - hmin) / (vmax - vmin)))
    H, V = np.meshgrid(np.linspace(hmin, hmax, n_h), np.linspace(vmin, vmax, n_v))

    coords = {h_axis: H, v_axis: V}
    if plane == "rz":
        coords["x"], coords["y"] = np.abs(V), np.zeros_like(V)
    else:
        (missing,) = {"x", "y", "z"} - {h_axis, v_axis}
        coords[missing] = np.full_like(H, position)
    parts = _components(
        geometry, rz, coords["x"], coords["y"], coords["z"], volt_dict=volt_dict
    )
    part_colors = _assign_colors(parts, colors, color_by, cmap, default_color)

    if ax is None:
        _, ax = plt.subplots()
    handles = []
    for part, color in zip(parts, part_colors, strict=True):
        fmax = float(np.max(part.field))
        if fmax <= 0:
            continue
        ax.contourf(
            H * scale,
            V * scale,
            part.field,
            levels=[0, fmax * (1 + 1e-9)],
            colors=[color],
        )
        if outline:
            ax.contour(
                H * scale,
                V * scale,
                part.field,
                levels=[0],
                colors=[outline_color],
                linewidths=linewidth,
            )
        label = part.label if part.label is not None else "other"
        handles.append(Patch(facecolor=color, edgecolor=outline_color, label=label))

    if color_by == "voltage":
        norm = mcolors.Normalize(*_voltage_range(parts))
        plt.colorbar(ScalarMappable(norm=norm, cmap=cmap), ax=ax, label="Voltage (V)")
    elif legend and (len(handles) > 1 or (handles and parts[0].label is not None)):
        ax.legend(
            handles=handles,
            loc="upper left",
            bbox_to_anchor=(1.01, 1),
            fontsize="small",
            frameon=False,
        )

    ax.set_aspect("equal")
    ax.set_xlim(hmin * scale, hmax * scale)
    ax.set_ylim(vmin * scale, vmax * scale)
    ax.set_xlabel(f"{h_axis} ({units})")
    ax.set_ylabel(f"{v_axis} ({units})")
    return ax


def _require_pyvista():
    try:
        import pyvista
    except ImportError as err:  # pragma: no cover - depends on the environment
        raise ImportError(
            "3D plotting needs pyvista: pip install 'warpx-geometry[viz]' "
            "(VTK has no wheels for Python 3.15 yet; plot_2d works everywhere)"
        ) from err
    return pyvista


_CLIP_AXES = {"x": 0, "y": 1, "z": 2}


def geometry_meshes(
    geometry,
    *,
    bounds=None,
    resolution: int = 150,
    clip: str | None = None,
    clip_origin=None,
    volt_dict: dict | None = None,
    units: str = "mm",
    rz: bool | None = None,
):
    """Return smooth surface meshes for the components of a geometry.

    The signed function is sampled on a regular grid and contoured at zero
    (marching cubes), so surfaces are smooth and sharp edges stay sharp up
    to the grid spacing. See ``plot_3d`` for the arguments.

    Returns:
        A list of (Component, pyvista.PolyData) tuples, with mesh coordinates
        in ``units``. Component.field is the sampled signed function.
    """
    pv = _require_pyvista()
    b = bounds if bounds is not None else _bounds(geometry, rz)
    lo, hi = np.array(b[0::2], dtype=float), np.array(b[1::2], dtype=float)
    spacing = np.max(hi - lo) / resolution
    dims = np.maximum(2, np.ceil((hi - lo) / spacing).astype(int) + 1)
    axes = [lo[i] + spacing * np.arange(dims[i]) for i in range(3)]
    X, Y, Z = np.meshgrid(*axes, indexing="ij")

    clip_field = None
    if clip is not None:
        sign = -1.0 if clip.startswith("-") else 1.0
        axis = _CLIP_AXES[clip.lstrip("+-")]
        origin = clip_origin
        if origin is None:
            origin = 0.5 * (lo[axis] + hi[axis])
        # keep the side opposite to the clip direction
        clip_field = sign * (origin - (X, Y, Z)[axis])

    parts = _components(geometry, rz, X, Y, Z, volt_dict, clip_field)

    scale = UNITS[units]
    grid = pv.ImageData(
        dimensions=dims, spacing=(spacing * scale,) * 3, origin=lo * scale
    )
    result = []
    for part in parts:
        grid.point_data["f"] = part.field.ravel(order="F").astype(np.float32)
        mesh = grid.contour([0.0], scalars="f")
        if mesh.n_points:
            result.append((part, mesh))
    return result


def plot_3d(
    geometry,
    *,
    bounds=None,
    resolution: int = 150,
    clip: str | None = None,
    clip_origin=None,
    colors=None,
    color_by: str = "name",
    volt_dict: dict | None = None,
    cmap="coolwarm",
    default_color="lightgray",
    units: str = "mm",
    legend: bool = True,
    show_axes: bool = True,
    show_bounds: bool = False,
    view: str = "iso",
    camera_position=None,
    zoom: float = 1.0,
    background="white",
    window_size=(1200, 900),
    mesh_kwargs: dict | None = None,
    rz: bool | None = None,
    plotter=None,
    screenshot=None,
    transparent: bool = False,
    show: bool | None = None,
):
    """Render a smooth 3D view of a geometry with pyvista.

    Args:
        geometry: a geometry object, a ``Geometry`` (RZ geometries are
            revolved around the z-axis) or a dict ``{label: object}``.
        bounds: (xmin, xmax, ymin, ymax, zmin, zmax) in m; defaults to the
            bounding box plus a 5% margin. Needed for unbounded shapes.
        resolution: grid points along the longest axis. ~100 is quick for
            checks, 300+ gives publication quality (memory grows as N^3).
        clip: cut away half of the geometry to look inside: "x", "y" or "z"
            removes the half on the + side of ``clip_origin``, "-x" etc. the
            half on the - side. The cut face is closed (solid).
        clip_origin: position of the cut plane (m); defaults to the center.
        colors, color_by, volt_dict, cmap, default_color: as in ``plot_2d``.
        units: units of the displayed coordinates.
        legend: show a legend of the named components.
        show_axes: show the orientation axes widget.
        show_bounds: show labelled bounds (a grid with tick labels).
        view: "iso", "xy", "xz", "yz", "yx", "zx" or "zy".
        camera_position, zoom: passed to the pyvista camera.
        mesh_kwargs: extra keyword arguments for ``Plotter.add_mesh``.
        rz: override the RZ setting of a ``Geometry``.
        plotter: existing pyvista Plotter to draw into.
        screenshot: file name to save a PNG (renders off screen).
        transparent: transparent background for the screenshot.
        show: open an interactive window; defaults to True unless a plotter
            or screenshot is given.

    Returns:
        The pyvista Plotter (use e.g. ``plotter.save_graphic("fig.pdf")``
        for vector output).
    """
    pv = _require_pyvista()
    meshes = geometry_meshes(
        geometry,
        bounds=bounds,
        resolution=resolution,
        clip=clip,
        clip_origin=clip_origin,
        volt_dict=volt_dict,
        units=units,
        rz=rz,
    )
    parts = [part for part, _ in meshes]
    part_colors = _assign_colors(parts, colors, color_by, cmap, default_color)

    if show is None:
        show = plotter is None and screenshot is None
    if plotter is None:
        plotter = pv.Plotter(
            off_screen=screenshot is not None and not show, window_size=window_size
        )
    plotter.set_background(background)

    kwargs = dict(
        smooth_shading=True, split_sharp_edges=True, specular=0.3, specular_power=20
    )
    kwargs.update(mesh_kwargs or {})
    labels = []
    for (part, mesh), color in zip(meshes, part_colors, strict=True):
        label = part.label if part.label is not None else "other"
        plotter.add_mesh(mesh, color=color, **kwargs)
        labels.append([label, color])

    if color_by == "voltage":
        vmin, vmax = _voltage_range(parts)
        # invisible actor that only provides the scalar bar
        dummy = pv.PolyData(np.zeros((2, 3)))
        dummy.point_data["Voltage (V)"] = [vmin, vmax]
        plotter.add_mesh(
            dummy,
            scalars="Voltage (V)",
            cmap=cmap,
            opacity=0.0,
            clim=(vmin, vmax),
            show_scalar_bar=True,
        )
    elif legend and (len(parts) > 1 or (parts and parts[0].label is not None)):
        size = (0.14, min(0.035 * len(labels), 0.5))
        plotter.add_legend(labels, bcolor=background, face="rectangle", size=size)

    if show_axes:
        plotter.add_axes()
    if show_bounds:
        plotter.show_bounds(
            xtitle=f"x ({units})",
            ytitle=f"y ({units})",
            ztitle=f"z ({units})",
            color="black",
        )
    if camera_position is not None:
        plotter.camera_position = camera_position
    elif view == "iso":
        plotter.view_isometric()
    else:
        getattr(plotter, f"view_{view}")()
    if zoom != 1.0:
        plotter.camera.zoom(zoom)
    plotter.enable_anti_aliasing("ssaa")

    if screenshot is not None:
        plotter.screenshot(screenshot, transparent_background=transparent)
    if show:
        plotter.show()
    return plotter
