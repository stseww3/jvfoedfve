"""TRIAL resolution of the tower/smalldome conflict: both white volumes are gone, the module builds nothing."""
from ..common import blocks as B
from ..common import skeleton as S

WALL = B.ASHLAR_FINE.block
ROOF = B.SLATE_TILE.block
IRON = B.IRON_PLATE


def _wall(c, o, x0, z0, x1, z1, y0, y1, block):
    """A one-block-thick vertical wall along the rectangle's perimeter (massing shell)."""
    ox, oy, oz = o
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            c.set(ox + x, oy + y, oz + z0, block)
            c.set(ox + x, oy + y, oz + z1, block)
        for z in range(z0, z1 + 1):
            c.set(ox + x0, oy + y, oz + z, block)
            c.set(ox + x1, oy + y, oz + z, block)


def _slab(c, o, x0, z0, x1, z1, y, block):
    ox, oy, oz = o
    for x in range(x0, x1 + 1):
        for z in range(z0, z1 + 1):
            c.set(ox + x, oy + y, oz + z, block)


def build(canvas, origin=(0, 0, 0)):
    c, o = canvas, origin

    return 0
