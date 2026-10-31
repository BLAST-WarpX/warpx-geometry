"""Sphinx configuration for the warpx-geometry documentation."""

from importlib.metadata import version as package_version

project = "warpx-geometry"
author = "Arun Persaud"
copyright = "2026, The Regents of the University of California"
release = package_version("warpx-geometry")
version = ".".join(release.split(".")[:2])

extensions = [
    "myst_parser",
    "sphinx.ext.autodoc",
    "sphinx.ext.mathjax",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "sphinx_copybutton",
    "sphinx_design",
]

source_suffix = {".md": "markdown"}
master_doc = "index"
exclude_patterns = ["_build"]

myst_enable_extensions = ["colon_fence", "dollarmath"]
myst_heading_anchors = 3

autodoc_member_order = "bysource"
napoleon_google_docstring = True
napoleon_numpy_docstring = True

html_theme = "sphinx_rtd_theme"
html_context = {
    "display_github": True,
    "github_user": "BLAST-WarpX",
    "github_repo": "warpx-geometry",
    "github_version": "main",
    "conf_py_path": "/docs/",
}
