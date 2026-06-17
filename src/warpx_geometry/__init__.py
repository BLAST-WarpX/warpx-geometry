"""WarpX Geometry - Simple geometry objects for WarpX embedded boundaries.

This package provides an easy way to define simple and complex 3D geometries
as analytical functions for WarpX particle-in-cell simulations.
"""

__version__ = "0.1.0"

from .geometry import *
from .complex_geometry import Einzellens
from .plot import plot_field2D, plot_particles2D, plot_rz_geometry_components, create_rz_geometry_mask

__all__ = [
    # Base classes
    "BaseObject",
    "Geometry",
    # Operations
    "Union",
    "Diff",
    "Intersection",
    "Translate",
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
