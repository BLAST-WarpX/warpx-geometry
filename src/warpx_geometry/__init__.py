"""WarpX Geometry - Simple geometry objects for WarpX embedded boundaries.

This package provides an easy way to define simple and complex 3D geometries
as analytical functions for WarpX particle-in-cell simulations.
"""

__version__ = "0.1.0"

from .complex_geometry import Einzellens
from .geometry import (
    BaseObject,
    BBox,
    Box,
    Cone,
    Cylinder,
    CylinderZ,
    CylinderZ_hollow,
    Diff,
    Geometry,
    Intersection,
    Rotate,
    RoundedCylinderZ,
    RoundedCylinderZ_hollow,
    Scale,
    Torus,
    Translate,
    Union,
    scale_around,
    scale_to_bbox_center,
)
from .plot import (
    create_rz_geometry_mask,
    plot_field2D,
    plot_particles2D,
    plot_rz_geometry_components,
)

__all__ = [
    # Bounding box
    "BBox",
    # Base classes
    "BaseObject",
    "Geometry",
    # Operations
    "Union",
    "Diff",
    "Intersection",
    "Translate",
    "Scale",
    "Rotate",
    "scale_around",
    "scale_to_bbox_center",
    # Basic shapes
    "Cylinder",
    "CylinderZ",
    "CylinderZ_hollow",
    "Box",
    "Torus",
    "Cone",
    # Advanced shapes
    "RoundedCylinderZ",
    "RoundedCylinderZ_hollow",
    # Complex geometries
    "Einzellens",
    # Plotting
    "plot_field2D",
    "plot_particles2D",
    "plot_rz_geometry_components",
    "create_rz_geometry_mask",
]
