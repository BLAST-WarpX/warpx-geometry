# Installation

warpx-geometry needs Python 3.11 or newer.

## With uv

[uv](https://docs.astral.sh/uv/) is a fast Python package manager:

```bash
uv pip install warpx-geometry
```

For 3D plots, add the `viz` extra, which installs [pyvista](https://pyvista.org):

```bash
uv pip install "warpx-geometry[viz]"
```

## With pip

```bash
pip install warpx-geometry
pip install "warpx-geometry[viz]"  # for 3D plots
```

```{note}
VTK has no wheels for Python 3.15 yet, so on 3.15 only the 2D plots are available.
```

## WarpX

WarpX itself is not a dependency. The package only writes strings, so you can build
and plot geometries without it. To run simulations, see the
[WarpX installation guide](https://warpx.readthedocs.io/en/latest/install/users.html).
For example, with conda:

```bash
conda install -c conda-forge warpx
```

## From source

```bash
git clone https://github.com/BLAST-WarpX/warpx-geometry.git
cd warpx-geometry
uv sync --extra dev --extra viz
```
