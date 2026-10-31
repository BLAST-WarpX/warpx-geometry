# Examples

The scripts are in the
[`examples`](https://github.com/BLAST-WarpX/warpx-geometry/tree/main/examples) folder.

## Einzel lens in WarpX

`warpx_einzel_lens.py` is a complete simulation. See [](warpx.md).

```{image} ../images/warpx_einzel_lens_potential.png
:alt: Potential of an einzel lens from WarpX
```

## Einzel lens and Faraday cup

`einzel_lens_faraday_cup.py` builds an einzel lens, a suppressor ring and a Faraday cup
in RZ, and plots them.

```{image} ../images/einzel_lens_faraday_cup_3d.png
:alt: Einzel lens and Faraday cup, 3D cutaway
```

```{image} ../images/einzel_lens_faraday_cup_rz.png
:alt: Einzel lens and Faraday cup, r-z cuts
```

## warpX letters

`warpx_letters.py` spells "warpX" from boxes, rotated boxes and hollow cylinders, with
one named conductor per letter.

```{image} ../images/warpx_letters.png
:alt: warpX spelled in 3D
```

Run them with:

```bash
uv run --extra viz python examples/einzel_lens_faraday_cup.py
```
