"""What the boilers and the switchboard of the power house share (machines/switchboard-boiler):
drawing a model in blocks, and placing it.

The name starts with an underscore: the category does not take it for a package.
"""
from artkit import models as M

VIEW = 3.0          # view range of a piece: 192 blocks at the client's normal setting


class Draw:
    """A model drawn in blocks round the point `at`, where its entity stands, and shown at `scale`.

    artkit's unit is 1/16 block of a model shown at scale 1. A model shown at scale s is drawn s
    times smaller and gets s texels to the unit (px = scale): 16 texels to the block whatever the
    scale. A model may span 48 units: three blocks at scale 1, six at scale 2.
    """

    def __init__(self, name, at=(0.0, 0.0, 0.0), scale=2.0):
        self.at = tuple(float(v) for v in at)
        self.scale = float(scale)
        self.u = 16.0 / self.scale
        self.m = M.Model(name, px=self.scale)

    def p(self, v):
        return tuple((v[i] - self.at[i]) * self.u for i in range(3))

    def _across(self, axis, c):
        k = M.AXES.index(axis)
        o1, o2 = [i for i in range(3) if i != k]
        return k, ((c[0] - self.at[o1]) * self.u, (c[1] - self.at[o2]) * self.u)

    def box(self, a, b, mat, rot=None, **kw):
        if rot is not None:
            rot = (rot[0], rot[1], self.p(rot[2]))
        self.m.box(self.p(a), self.p(b), mat, rot=rot, **kw)

    def tube(self, axis, c, a0, a1, radius, mat, **kw):
        """c: the two other coordinates of the centre line, in the order of the axes."""
        k, c = self._across(axis, c)
        self.m.tube(axis, c, (a0 - self.at[k]) * self.u, (a1 - self.at[k]) * self.u, radius * self.u, mat, **kw)

    def taper(self, axis, c, a0, a1, r0, r1, mat, **kw):
        k, c = self._across(axis, c)
        self.m.taper(axis, c, (a0 - self.at[k]) * self.u, (a1 - self.at[k]) * self.u, r0 * self.u, r1 * self.u,
                     mat, **kw)

    def ring(self, axis, centre, radius, thick, width, mat, **kw):
        self.m.ring(axis, self.p(centre), radius * self.u, thick * self.u, width * self.u, mat, **kw)

    def ball(self, centre, radius, mat, **kw):
        self.m.ball(self.p(centre), radius * self.u, mat, **kw)

    def rod(self, a, b, radius, mat, **kw):
        self.m.rod(self.p(a), self.p(b), radius * self.u, mat, **kw)

    def beam(self, a, b, width, height, mat, **kw):
        self.m.beam(self.p(a), self.p(b), width * self.u, height * self.u, mat, **kw)


def place(canvas, drawn, pos, origin, yaw=0.0, turns=(), brightness=None):
    """One drawn model with its point `at` on pos; returns 1, the entity it takes."""
    x, y, z = (pos[i] + origin[i] for i in range(3))
    canvas.add_entity(x, y, z, M.display(drawn.m, yaw=yaw, scale=drawn.scale, turns=turns, brightness=brightness,
                                         view=VIEW))
    return 1
