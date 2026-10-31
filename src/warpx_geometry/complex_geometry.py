from . import geometry as g


class Einzellens(g.Union):
    """Three tubes along z, centered at z=0.

    Parameters:
        radius: Mean radius of the tube walls
        thickness: Wall thickness
        length: Length of each tube
        gap: Distance between tubes
        name, default_voltage: Name the lens as one conductor
        voltages: Voltages of the three tubes. This names them "<name>_1" to
            "<name>_3" (name defaults to "lens"), instead of naming the lens.

    Example:
        # Outer tubes grounded, middle tube at 5 kV
        lens = Einzellens(0.01, 0.002, 0.01, 0.004, voltages=(0, 5000, 0))
    """

    def __init__(
        self,
        radius,
        thickness,
        length,
        gap,
        name=None,
        default_voltage=0,
        voltages=None,
    ):
        g._check_positive("thickness", thickness)
        g._check_positive("length", length)
        if gap < 0:
            raise ValueError(f"gap must not be negative, got {gap}")

        radius_inner = radius - thickness / 2
        radius_outer = radius + thickness / 2

        # z-values for the 3 cylinders
        a_min = -length / 2 - gap - length
        a_max = -length / 2 - gap
        b_min = -length / 2
        b_max = +length / 2
        c_min = +length / 2 + gap
        c_max = +length / 2 + gap + length

        a = g.CylinderZ_hollow(radius_outer, radius_inner, a_min, a_max)
        b = g.CylinderZ_hollow(radius_outer, radius_inner, b_min, b_max)
        c = g.CylinderZ_hollow(radius_outer, radius_inner, c_min, c_max)

        if voltages is not None:
            if len(voltages) != 3:
                raise ValueError(f"need 3 voltages, got {len(voltages)}")
            prefix = name or "lens"
            name = None
            for i, tube in enumerate((a, b, c)):
                tube.named(f"{prefix}_{i + 1}", voltages[i])

        tmp = g.Union(a, b)
        super().__init__(tmp, c)
        self.name = name
        self.default_voltage = default_voltage
