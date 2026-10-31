# WarpX Geometry

[![PyPI](https://img.shields.io/pypi/v/warpx-geometry.svg)](https://pypi.org/project/warpx-geometry/)
[![tests](https://github.com/BLAST-WarpX/warpx-geometry/actions/workflows/tests.yml/badge.svg)](https://github.com/BLAST-WarpX/warpx-geometry/actions/workflows/tests.yml)
[![docs](https://readthedocs.org/projects/warpx-geometry/badge/?version=stable)](https://warpx-geometry.readthedocs.io/en/stable/)
[![License](https://img.shields.io/badge/license-BSD--3--Clause--LBNL-blue.svg)](https://spdx.org/licenses/BSD-3-Clause-LBNL.html)

Simple geometry objects for [WarpX](https://warpx.readthedocs.io/) embedded boundaries.

Combine shapes in Python, and warpx-geometry writes the analytic expressions that
WarpX needs for the geometry and for the voltage on each conductor, in Cartesian
(XYZ) and cylindrical (RZ) coordinates.

**[Read the documentation](https://warpx-geometry.readthedocs.io/en/stable/)** for the guides, examples and API reference.

## Gallery

An einzel lens followed by a suppressor ring and a Faraday cup, built in RZ
([`einzel_lens_faraday_cup.py`](https://github.com/BLAST-WarpX/warpx-geometry/blob/main/examples/einzel_lens_faraday_cup.py)):

![Einzel lens and Faraday cup, 3D cutaway](https://raw.githubusercontent.com/BLAST-WarpX/warpx-geometry/main/docs/images/einzel_lens_faraday_cup_3d.png)

![Einzel lens and Faraday cup, r-z cuts](https://raw.githubusercontent.com/BLAST-WarpX/warpx-geometry/main/docs/images/einzel_lens_faraday_cup_rz.png)

The potential of an einzel lens, solved with WarpX
([`warpx_einzel_lens.py`](https://github.com/BLAST-WarpX/warpx-geometry/blob/main/examples/warpx_einzel_lens.py)):

![Potential of an einzel lens from WarpX](https://raw.githubusercontent.com/BLAST-WarpX/warpx-geometry/main/docs/images/warpx_einzel_lens_potential.png)

"warpX" built from boxes, rotated boxes and hollow cylinders
([`warpx_letters.py`](https://github.com/BLAST-WarpX/warpx-geometry/blob/main/examples/warpx_letters.py)):

![warpX spelled in 3D](https://raw.githubusercontent.com/BLAST-WarpX/warpx-geometry/main/docs/images/warpx_letters.png)

## Installation

With [uv](https://docs.astral.sh/uv/):

```bash
uv pip install warpx-geometry
uv pip install "warpx-geometry[viz]"  # for 3D plots
```

With pip:

```bash
pip install warpx-geometry
pip install "warpx-geometry[viz]"  # for 3D plots
```

## Example

```python
from warpx_geometry import CylinderZ_hollow, Geometry

# dimensions in m
lens = CylinderZ_hollow(0.011, 0.009, -0.005, 0.005, name="lens", default_voltage=5000)
tube = CylinderZ_hollow(0.030, 0.028, -0.05, 0.05, name="tube")

geometry = Geometry(lens + tube, rz=True)

eb_function = str(geometry)  # warpx.eb_implicit_function
potential = geometry.to_potential_expr()  # warpx.eb_potential(x,y,z,t)
```

## Using AI assistants

The repository includes a skill that teaches AI assistants how to use the package. See
[Using AI assistants](https://warpx-geometry.readthedocs.io/en/stable/usage/ai.html).

## Contributing

Contributions are welcome. See the
[development guide](https://warpx-geometry.readthedocs.io/en/stable/development.html), and
[open an issue](https://github.com/BLAST-WarpX/warpx-geometry/issues) for questions or
problems.

## Citation

If you use this package in your research, please cite:

```bibtex
@software{warpx_geometry,
  author = {Persaud, Arun},
  title = {WarpX Geometry: Simple geometry objects for WarpX},
  url = {https://github.com/BLAST-WarpX/warpx-geometry},
  year = {2026}
}
```

## License

WarpX Copyright (c) 2018, The Regents of the University of California,
through Lawrence Berkeley National Laboratory (subject to receipt of any
required approvals from the U.S. Dept. of Energy).  All rights reserved.

If you have questions about your rights to use or distribute this software,
please contact Berkeley Lab's Innovation & Partnerships Office at
IPO@lbl.gov.

Please see the full license agreement in [LICENSE.txt](https://github.com/BLAST-WarpX/warpx-geometry/blob/main/LICENSE.txt).
Please see the notices in [NOTICE.txt](https://github.com/BLAST-WarpX/warpx-geometry/blob/main/NOTICE.txt).
The SPDX license identifier is `BSD-3-Clause-LBNL`.
