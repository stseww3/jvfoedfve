"""Framework demo work package: the M3 white-model massing. The plain volumes of the main building,
rotunda, dome, clock tower and small dome in the dressed-stone / dome materials on the skeleton
grid, so the silhouette ("one bar, one circle, one spire") and proportions can be judged in the
first render. A3 replaces this with the real shells (elevation grammar, three-depth section)."""
import math

from ..common import blocks as B
from ..common import skeleton as S

WALL = B.ASHLAR_FINE.block
ROOF = B.SLATE_TILE.block
DOME = B.VERDIGRIS
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


def _cylinder(c, o, cx, cz, r, y0, y1, block):
    """A one-block-thick ring (hollow cylinder) of radius r."""
    ox, oy, oz = o
    ring = set()
    for a in range(0, 360, 2):
        x = int(round(cx + r * math.cos(math.radians(a))))
        z = int(round(cz + r * math.sin(math.radians(a))))
        ring.add((x, z))
    for y in range(y0, y1 + 1):
        for x, z in ring:
            c.set(ox + x, oy + y, oz + z, block)


def _dome(c, o, cx, cz, y0, y1, radius_at, block):
    for y in range(y0, y1 + 1):
        r = radius_at(y)
        if r and r >= 0.5:
            _cylinder(c, o, cx, cz, r, y, y, block)


def build(canvas, origin=(0, 0, 0)):
    c, o = canvas, origin

    # the long main building: perimeter walls and a roof slab. The east (front) wall steps with the
    # five-part projection; the west wall and the two ends are plain.
    _wall(c, o, S.WALL_W, S.Z_NORTH, S.WALL_E, S.Z_SOUTH, S.GROUND, S.CORNICE, WALL)
    for j in range(1, S.N_BAYS + 1):
        za, zb = S.pilaster_z(j - 1), S.pilaster_z(j)
        xe = S.east_wall_x(j)
        for z in range(za, zb + 1):
            for y in range(S.GROUND, S.CORNICE + 1):
                c.set(o[0] + xe, o[1] + y, o[2] + z, WALL)
    _slab(c, o, S.WALL_W, S.Z_NORTH, S.WALL_E, S.Z_SOUTH, S.ROOF_FLOOR, ROOF)

    # the rotunda and great dome: a grounded drum ring, then the verdigris shell
    cx, cz = S.DOME_CENTRE
    _cylinder(c, o, cx, cz, S.DOME_R, S.GROUND, S.DOME_SPRING - 1, WALL)
    _dome(c, o, cx, cz, S.DOME_SPRING, S.DOME_APEX, S.dome_profile, DOME)

    # the clock tower (north) and small dome (south)
    _wall(c, o, S.CLOCK_SHAFT_X[0], S.CLOCK_SHAFT_Z[0], S.CLOCK_SHAFT_X[1], S.CLOCK_SHAFT_Z[1],
          S.GROUND, S.CLOCK_SHAFT_TOP, WALL)
    _wall(c, o, S.CLOCK_SHAFT_X[0], S.CLOCK_SHAFT_Z[0], S.CLOCK_SHAFT_X[1], S.CLOCK_SHAFT_Z[1],
          S.CLOCK_SHAFT_TOP + 1, S.CLOCK_TOP, IRON)
    scx = (S.SMALL_DOME_X[0] + S.SMALL_DOME_X[1]) / 2.0
    scz = (S.SMALL_DOME_Z[0] + S.SMALL_DOME_Z[1]) / 2.0

    def small_profile(y):
        t = (y - S.SMALL_DRUM_BASE) / float(S.SMALL_DOME_APEX - S.SMALL_DRUM_BASE)
        return S.SMALL_DOME_R * math.sqrt(max(0.0, 1.0 - t * t))

    _dome(c, o, scx, scz, S.SMALL_DRUM_BASE, S.SMALL_DOME_APEX, small_profile, DOME)
    return 0
