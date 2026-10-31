"""Plotting routines"""

from collections import defaultdict

import numpy as np
from matplotlib import pyplot as plt
from matplotlib.patches import Rectangle


def plot_field2D(
    field,
    info,
    cut_direction: str,
    cut_idx: float | int,
    filename: str | None = None,
):
    Nz, Nx, Ny = field.shape

    if isinstance(cut_idx, float):
        match cut_direction:
            case "X":
                cut_idx = int(Nx * cut_idx)
            case "Y":
                cut_idx = int(Ny * cut_idx)
            case "Z":
                cut_idx = int(Nz * cut_idx)
    match cut_direction:
        case "X":
            data = field[:, cut_idx, :]
            extent = [info.ymin, info.ymax, info.zmin, info.zmax]
        case "Y":
            data = field[:, :, cut_idx]
            extent = [info.xmin, info.xmax, info.zmin, info.zmax]
        case "Z":
            data = field[cut_idx, :, :]
            extent = [info.ymin, info.ymax, info.xmin, info.xmax]
        case _:
            raise ValueError(
                f"cut_direction must be 'X', 'Y', or 'Z', got {cut_direction!r}"
            )

    fig, ax = plt.subplots()
    ax.imshow(data, extent=extent)
    ax.set_title(f"Cut in {cut_direction}")
    if filename:
        plt.savefig(filename)
    return ax


def plot_particles2D(
    container,
    N,
    ax=None,
    filename: str | None = None,
    title: str | None = None,
    color: str = "r",
):
    if ax is None:
        fig, ax = plt.subplots()

    data = defaultdict(list)
    for i in range(N):
        id_, y, z = container.get_particle(["id", "y", "z"], iteration=i)
        for a, b, c in zip(id_, y, z, strict=False):
            data[a].append([b, c])
    for id_ in list(data.keys())[:100]:
        points = np.array(data[id_])
        ax.plot(points[:, 0], points[:, 1], "-", color=color)
    if title:
        ax.set_title(title)
    ax.set_xlabel("y")
    ax.set_ylabel("z")
    if filename:
        plt.savefig(filename)
    return ax


# ====================
# RZ Geometry Plotting
# ====================


def plot_rz_bboxes(ax, components_dict, margin=0, unit_scale=1000, bbox_kwargs=None):
    """Plot RZ bounding boxes as rectangles on an RZ axis.

    Each component's ``rz_bbox`` (optionally expanded by *margin*) is drawn as
    a dashed rectangle whose colour matches the component colour.

    Parameters:
    -----------
    ax : matplotlib axis
        Axis to draw on. The axis limits are used to clip infinite bounds.
    components_dict : dict
        Mapping of names to either ``(BaseObject, color)`` tuples (same format
        as :func:`plot_rz_geometry_components`) or plain ``BaseObject``
        instances (colour defaults to ``"black"``).
    margin : float
        Expand each bbox by this amount in meters before drawing (default 0).
    unit_scale : float
        Multiply all coordinates by this factor before drawing.  Default 1000
        converts metres to millimetres, matching the axis units used by
        :func:`plot_rz_geometry_components`.
    bbox_kwargs : dict or None
        Style overrides forwarded to :class:`matplotlib.patches.Rectangle`.
        Merged with defaults ``{'fill': False, 'linestyle': '--',
        'linewidth': 1.5, 'alpha': 0.8}``.

    Returns:
    --------
    ax : matplotlib axis

    Example:
    --------
    >>> components = {
    ...     "ring_0": (ring, "red"),
    ...     "tube": (tube, "gray"),
    ... }
    >>> # Non-expanded bboxes
    >>> plot_rz_bboxes(ax, components, margin=0)
    >>> # Bboxes expanded by 2mm
    >>> plot_rz_bboxes(
    ...     ax, components, margin=0.002, bbox_kwargs={"linestyle": ":", "linewidth": 2}
    ... )
    """
    default_kw = {"fill": False, "linestyle": "--", "linewidth": 1.5, "alpha": 0.8}
    kw = {**default_kw, **(bbox_kwargs or {})}

    xlim = ax.get_xlim()
    ylim = ax.get_ylim()

    for name, entry in components_dict.items():
        if isinstance(entry, tuple):
            obj, color = entry
        else:
            obj, color = entry, "black"

        try:
            bb = obj.rz_bbox.expanded(margin)
        except (NotImplementedError, AttributeError):
            continue

        # Clip infinite bounds to current axis limits
        z0 = xlim[0] if np.isinf(bb.zmin) else bb.zmin * unit_scale
        z1 = xlim[1] if np.isinf(bb.zmax) else bb.zmax * unit_scale
        r0 = ylim[0] if np.isinf(bb.rmin) else bb.rmin * unit_scale
        r1 = ylim[1] if np.isinf(bb.rmax) else bb.rmax * unit_scale

        z0 = max(z0, xlim[0])
        z1 = min(z1, xlim[1])
        r0 = max(r0, ylim[0])
        r1 = min(r1, ylim[1])

        width = z1 - z0
        height = r1 - r0
        if width <= 0 or height <= 0:
            continue

        rect = Rectangle((z0, r0), width, height, edgecolor=color, label=name, **kw)
        ax.add_patch(rect)

    return ax


def plot_rz_geometry_components(
    ax,
    components_dict,
    z_range,
    r_range,
    resolution_factor=10,
    alpha=None,
    fill=True,
    bbox_margin=None,
    bbox_kwargs=None,
):
    """
    Plot RZ geometry components with different colors using alpha masks.

    Parameters:
    -----------
    ax : matplotlib axis
        Axis to plot on (should already have background, e.g., phi field)
    components_dict : dict
        Dictionary mapping names to (geometry_object, color) tuples
        Example: {'tube': (vacuum_tube, 'gray'), 'electrode': (elec, 'red')}
    z_range : tuple
        (z_min, z_max) in meters
    r_range : tuple
        (r_min, r_max) in meters
    resolution_factor : int
        Multiply base resolution by this factor for smoother edges (default: 10)
    alpha : float or None
        Transparency of geometry overlay. If None, makes geometry opaque (default: None)
    fill : bool
        If True, fill geometry regions with color. If False, only draw
        outlines (default: True)
    bbox_margin : float or None
        If not None, overlay each component's RZ bounding box as a dashed
        rectangle, expanded by this margin in meters (0 = unexpanded bbox).
    bbox_kwargs : dict or None
        Style overrides forwarded to matplotlib.patches.Rectangle for the bbox
        rectangles. Merged with defaults {'fill': False, 'linestyle': '--',
        'linewidth': 1.5, 'alpha': 0.8}. Ignored when bbox_margin is None.

    Example:
    --------
    >>> components = {
    ...     "tube": (vacuum_tube, "lightgray"),
    ...     "electrode": (electrode, "red"),
    ... }
    >>> plot_rz_geometry_components(ax, components, z_range=(0, 0.2), r_range=(0, 0.03))
    >>> # Also show expanded bounding boxes:
    >>> plot_rz_geometry_components(
    ...     ax,
    ...     components,
    ...     z_range=(0, 0.2),
    ...     r_range=(0, 0.03),
    ...     bbox_margin=0.002,
    ...     bbox_kwargs={"linestyle": ":"},
    ... )
    """
    z_min, z_max = z_range
    r_min, r_max = r_range

    # Create high-resolution grid for geometry
    # Default base resolution: 100 points, multiply by resolution_factor
    nz = 100 * resolution_factor
    nr = 50 * resolution_factor  # Typically narrower in r

    z_grid = np.linspace(z_min, z_max, nz)
    r_grid = np.linspace(r_min, r_max, nr)

    # Create meshgrids
    Z, R = np.meshgrid(z_grid, r_grid, indexing="ij")

    # In RZ, we sample at y=0, so x = r (taking positive side)
    X = R
    Y = np.zeros_like(R)

    # Plot each component
    for _name, (geom_obj, color) in components_dict.items():
        # Evaluate geometry on grid
        mask = geom_obj.eval(X, Y, Z)

        # Plot filled region where mask > 0 (inside geometry)
        if fill:
            # Use contourf with two levels: background (white/transparent)
            # and filled (color)
            if alpha is None:
                # Opaque geometry (for phi plots)
                ax.contourf(
                    Z * 1000,
                    R * 1000,
                    mask,
                    levels=[0.5, 1.5],  # Only show inside region
                    colors=[color],
                    antialiased=True,
                )
            else:
                # Transparent geometry (for overlays)
                ax.contourf(
                    Z * 1000,
                    R * 1000,
                    mask,
                    levels=[0.5, 1.5],
                    colors=[color],
                    alpha=alpha,
                    antialiased=True,
                )

        # Add edge outline
        ax.contour(
            Z * 1000,
            R * 1000,
            mask,
            levels=[0.5],
            colors=[color],
            linewidths=1.5,
            alpha=1.0 if alpha is None else min(alpha * 2, 1.0),
        )

    if bbox_margin is not None:
        plot_rz_bboxes(ax, components_dict, margin=bbox_margin, bbox_kwargs=bbox_kwargs)

    return ax


def create_rz_geometry_mask(geom_obj, z_range, r_range, resolution_factor=10):
    """
    Create high-resolution binary mask for RZ geometry.

    Useful for custom plotting or further processing.

    Parameters:
    -----------
    geom_obj : BaseObject
        Geometry object (or combined geometry)
    z_range, r_range : tuple
        (min, max) in meters
    resolution_factor : int
        Resolution multiplier (default: 10)

    Returns:
    --------
    Z, R, mask : numpy arrays
        Meshgrids and binary mask (>0 inside geometry)
    """
    z_min, z_max = z_range
    r_min, r_max = r_range

    nz = 100 * resolution_factor
    nr = 50 * resolution_factor

    z_grid = np.linspace(z_min, z_max, nz)
    r_grid = np.linspace(r_min, r_max, nr)

    Z, R = np.meshgrid(z_grid, r_grid, indexing="ij")
    X = R
    Y = np.zeros_like(R)

    mask = geom_obj.eval(X, Y, Z)

    return Z, R, mask
