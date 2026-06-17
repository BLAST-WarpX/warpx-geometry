"""Plotting routines"""

from collections import defaultdict

from matplotlib import pyplot as plt
import numpy as np


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
            extent = [info.xmin, info.xmax, info.ymin, info.ymax]

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
):
    if ax is None:
        fig, ax = plt.subplots()

    data = defaultdict(list)
    for i in range(N):
        id_, y, z = container.get_particle(["id", "y", "z"], iteration=i)
        for a, b, c in zip(id_, y, z):
            data[a].append([b, c])
    for id_ in list(data.keys())[:100]:
        points = np.array(data[id_])
        ax.plot(points[:, 0], points[:, 1], "r-")
    plt.title("Protons")
    plt.xlabel("y")
    plt.ylabel("z")
    if filename:
        plt.savefig(filename)


# ====================
# RZ Geometry Plotting
# ====================

def plot_rz_geometry_components(ax, components_dict, z_range, r_range,
                                resolution_factor=10, alpha=None, fill=True):
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
        If True, fill geometry regions with color. If False, only draw outlines (default: True)

    Example:
    --------
    >>> components = {
    ...     'tube': (vacuum_tube, 'lightgray'),
    ...     'electrode': (electrode, 'red'),
    ... }
    >>> plot_rz_geometry_components(ax, components, z_range=(0, 0.2),
    ...                             r_range=(0, 0.03))
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
    Z, R = np.meshgrid(z_grid, r_grid, indexing='ij')

    # In RZ, we sample at y=0, so x = r (taking positive side)
    X = R
    Y = np.zeros_like(R)

    # Plot each component
    for name, (geom_obj, color) in components_dict.items():
        # Evaluate geometry on grid
        mask = geom_obj.eval(X, Y, Z)

        # Plot filled region where mask > 0 (inside geometry)
        if fill:
            # Use contourf with two levels: background (white/transparent) and filled (color)
            if alpha is None:
                # Opaque geometry (for phi plots)
                ax.contourf(Z * 1000, R * 1000, mask,
                           levels=[0.5, 1.5],  # Only show inside region
                           colors=[color],
                           antialiased=True)
            else:
                # Transparent geometry (for overlays)
                ax.contourf(Z * 1000, R * 1000, mask,
                           levels=[0.5, 1.5],
                           colors=[color],
                           alpha=alpha,
                           antialiased=True)

        # Add edge outline
        ax.contour(Z * 1000, R * 1000, mask,
                  levels=[0.5],
                  colors=[color],
                  linewidths=1.5,
                  alpha=1.0 if alpha is None else min(alpha * 2, 1.0))

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

    Z, R = np.meshgrid(z_grid, r_grid, indexing='ij')
    X = R
    Y = np.zeros_like(R)

    mask = geom_obj.eval(X, Y, Z)

    return Z, R, mask
