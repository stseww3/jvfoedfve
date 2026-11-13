"""Framework demo work package: the upper terrace and the lower platform, so the masses have a floor
to stand on in the first render. A4 replaces this with the real terrain, cloud line, retaining walls
and paving."""
from ..common import blocks as B
from ..common import skeleton as S

PAVING = B.TUFF_SMOOTH.block        # plan 6.2: the tuff family paves the terraces
LOWER = B.TUFF_BRICK.block


def _floor(c, o, x0, z0, x1, z1, y, block):
    ox, oy, oz = o
    for x in range(int(x0), int(x1) + 1):
        for z in range(int(z0), int(z1) + 1):
            c.set(ox + x, oy + y, oz + z, block)


def build(canvas, origin=(0, 0, 0)):
    c, o = canvas, origin
    fx0, fz0, fx1, fz1 = S.FRONT_COURT
    _floor(c, o, S.WALL_W - 10, S.Z_NORTH - 4, fx1, S.Z_SOUTH + 4, S.PAVING_Y, PAVING)
    lx0, lz0, lx1, lz1 = S.LOWER_PLATFORM
    _floor(c, o, lx0, lz0, lx1, lz1, S.PAVING_Y - S.LOWER_DROP, LOWER)
    return 0
