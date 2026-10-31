# Development

Contributions are welcome. Fork the repository, make your changes on a branch, add
tests, and open a pull request.

## Setup

```bash
git clone https://github.com/BLAST-WarpX/warpx-geometry.git
cd warpx-geometry
uv sync --extra dev --extra viz
```

## Tests and code style

```bash
uv run pytest
uv run ruff format .
uv run ruff check --fix .
```

The tests also run every Python block in these docs.

## Documentation

The docs use [Sphinx](https://www.sphinx-doc.org/) with
[MyST](https://myst-parser.readthedocs.io/) Markdown, and the same theme as WarpX.

```bash
uv run --extra docs sphinx-build -W -b html docs docs/_build/html
```

## Releasing

Versions come from git tags through hatch-vcs and follow
[Semantic Versioning](https://semver.org/).

1. Move the `Unreleased` entries in `CHANGELOG.md` to a new version section.
2. Merge that to `main`.
3. Tag the merged commit and push the tag:

   ```bash
   git tag -a v0.4.0 -m "Release 0.4.0"
   git push origin v0.4.0
   ```

4. Approve the deployment in the Actions tab.

The tag publishes the package to PyPI and rebuilds the `stable` documentation.
