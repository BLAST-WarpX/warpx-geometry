from . import geometry as g


class Einzellens(g.Union):
    def __init__(self, radius, thickness, length, gap, name=None, default_voltage=0):
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

        tmp = g.Union(a, b)
        super().__init__(tmp, c)
        self.name = name
        self.default_voltage = default_voltage
