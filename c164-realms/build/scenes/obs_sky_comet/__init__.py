"""Test scene for the card sky/comet. The three versions sit in the three looks' moon slots
(a -> blue 14000, b -> deep 18000, c -> glow 12900), so changing the time in shots.json shows each
one; see comet.pack(compare=True).

White models only, in plain vanilla stone and verdigris, enough to judge where the comet sits and
what hides it:
    - the main building bar (one bar), so V1 and V2 read as the whole observatory;
    - the rotunda and great dome with the west observing slit cut, for the dome-room view (V8);
    - the clock tower and the time-ball mast (one spire), which the comet crowns in V1;
    - the small dome.

Offline the sky and the comet are not drawn (sky.md section 9): this scene is for position and for
what blocks the view. The comet itself is judged on the real-machine pictures (s1).
"""
import math

from artkit.canvas import Canvas
from scenes.obs.sky import comet
from scenes.obs.common import blocks as B
from scenes.obs.common import skeleton as S

BIOME = "obs_blue"
BIOME_MARGIN = 120          # the look has to reach the far cameras, not only the blocks
BIOME_MARGIN_Y = 150

STONE = B.TUFF_SMOOTH.block          # vanilla polished tuff: the plain white-model stone
DOME = B.VERDIGRIS                    # vanilla waxed oxidized copper: the dome shell
MAST = B.SLATE_SMOOTH.block          # vanilla polished deepslate: the time-ball mast


def write_pack(pack_dir):
    """Only the comet's pictures: the white model is plain vanilla blocks, nothing repainted."""
    return list(comet.pack(pack_dir, compare=True) or [])


def _walls(c, x0, z0, x1, z1, y0, y1, block):
    """A one-block-thick vertical wall around the rectangle's perimeter."""
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            c.set(x, y, z0, block)
            c.set(x, y, z1, block)
        for z in range(z0, z1 + 1):
            c.set(x0, y, z, block)
            c.set(x1, y, z, block)


def _slab(c, x0, z0, x1, z1, y, block):
    for x in range(x0, x1 + 1):
        for z in range(z0, z1 + 1):
            c.set(x, y, z, block)


def _ring(c, cx, cz, r, y0, y1, block):
    cells = set()
    for a in range(0, 360, 2):
        cells.add((int(round(cx + r * math.cos(math.radians(a)))),
                   int(round(cz + r * math.sin(math.radians(a))))))
    for y in range(y0, y1 + 1):
        for x, z in cells:
            c.set(x, y, z, block)


def _dome(c, cx, cz, y0, y1, radius_at, block):
    for y in range(y0, y1 + 1):
        r = radius_at(y)
        if r and r >= 0.5:
            _ring(c, cx, cz, r, y, y, block)


def _main_bar(c):
    _walls(c, S.WALL_W, S.Z_NORTH, S.WALL_E, S.Z_SOUTH, S.GROUND, S.CORNICE, STONE)
    for j in range(1, S.N_BAYS + 1):
        xe = S.east_wall_x(j)
        for z in range(S.pilaster_z(j - 1), S.pilaster_z(j) + 1):
            for y in range(S.GROUND, S.CORNICE + 1):
                c.set(xe, y, z, STONE)
    _slab(c, S.WALL_W, S.Z_NORTH, S.WALL_E, S.Z_SOUTH, S.ROOF_FLOOR, STONE)


def _rotunda_and_dome(c):
    cx, cz = S.DOME_CENTRE
    _ring(c, cx, cz, S.DOME_R, S.GROUND, S.DOME_SPRING - 1, STONE)
    _dome(c, cx, cz, S.DOME_SPRING, S.DOME_APEX, S.dome_profile, DOME)
    # the west observing slit, five wide on the axis, open from the drum top over the apex (+2 east)
    half = S.SLIT_W // 2
    z0, z1 = round(S.DOME_AXIS[1]) - half, round(S.DOME_AXIS[1]) + half
    c.carve(cx - S.DOME_R - 1, S.DRUM[1], z0, cx, S.DOME_APEX + 1, z1)
    c.carve(cx, S.DOME_APEX - 2, z0, cx + 2, S.DOME_APEX + 1, z1)


def _clock_tower(c):
    x0, x1 = S.CLOCK_SHAFT_X
    z0, z1 = S.CLOCK_SHAFT_Z
    _walls(c, x0, z0, x1, z1, S.GROUND, S.CLOCK_TOP, STONE)
    _slab(c, x0, z0, x1, z1, S.CLOCK_TOP, STONE)
    mx, mz = (x0 + x1) // 2, (z0 + z1) // 2       # the time-ball mast, which the comet crowns in V1
    for y in range(S.CLOCK_TOP + 1, S.CLOCK_BALL_MAST + 1):
        c.set(mx, y, mz, MAST)
    c.set(mx, S.CLOCK_BALL_MAST - 2, mz, DOME)     # the time ball
    c.box(mx - 1, S.CLOCK_BALL_MAST - 2, mz, mx + 1, S.CLOCK_BALL_MAST - 2, mz, DOME)


def _small_dome(c):
    cx = (S.SMALL_DOME_X[0] + S.SMALL_DOME_X[1]) / 2.0
    cz = (S.SMALL_DOME_Z[0] + S.SMALL_DOME_Z[1]) / 2.0

    def profile(y):
        t = (y - S.SMALL_DRUM_BASE) / float(S.SMALL_DOME_APEX - S.SMALL_DRUM_BASE)
        return S.SMALL_DOME_R * math.sqrt(max(0.0, 1.0 - t * t))

    _dome(c, cx, cz, S.SMALL_DRUM_BASE, S.SMALL_DOME_APEX, profile, DOME)


def build():
    c = Canvas()
    _main_bar(c)
    _rotunda_and_dome(c)
    _clock_tower(c)
    _small_dome(c)
    c.entity_counts = {}
    return c
