"""Test scene of the work package props/instruments: the small instruments on one stage.

A wall of dressed stone looks south and the cameras stand south of it. From west to east: the
terrace bay (stone paving) with the tripod telescope side-on, then the hall bay (wooden floor, a
writing table for scale) with the celestial globe. Bracket lamps on the wall light both, as the
terraces and the rooms will.

The shots are written from the numbers below:  python -m scenes.obs_props_instruments
"""
from artkit.canvas import Canvas

from scenes.obs import materials, sky
from scenes.obs.common import blocks as B
from scenes.obs.props import instruments, lamps

BIOME = "obs_blue"
BIOME_MARGIN = 32
BIOME_MARGIN_Y = 32

STONE, PAVING, FLOOR, WOOD = B.ASHLAR_FINE.block, B.TUFF_SMOOTH.block, B.FLOOR_WOOD.block, B.DARK_WOOD.block
WALL_H = 6
TERRACE_X, HALL_X, WALL_END = 0, 10, 21         # the terrace bay, the hall bay, the last column of the wall
SCOPE = (TERRACE_X + 4.5, 0.0, 3.5)
GLOBE = (HALL_X + 4.0, 0.0, 3.0)
TABLE = (HALL_X + 7, 0, 2)                      # the cell of a one-block writing table
LAMP_Y = 4.0
TIME = 14000                    # light version A, the default (INTERFACE: 18000 is B, 12900 is C)


def build():
    c = Canvas()
    c.box(TERRACE_X - 3, -1, -1, WALL_END + 3, -1, 16, PAVING)
    c.box(HALL_X, -1, 0, WALL_END, -1, 7, FLOOR)
    c.box(TERRACE_X - 2, 0, -1, WALL_END + 2, WALL_H - 1, -1, STONE)
    c.box(TABLE[0], 0, TABLE[2], TABLE[0] + 1, 0, TABLE[2], WOOD)
    n = 0
    for x in (TERRACE_X + 1.5, TERRACE_X + 7.5, HALL_X + 1.5, HALL_X + 7.5):
        n += lamps.place(c, "bracket", (x, LAMP_Y, 0.0))
    n += instruments.place(c, "tripod_scope", SCOPE, facing="east")
    n += instruments.place(c, "celestial_globe", GLOBE)
    sky.build(c, (0, 0, 0))         # A2's light sources go in last, when every lamp is in place
    c.entity_counts = {"props": n}
    return c


def write_pack(pack_dir):
    """The repainted stone the instruments are judged against."""
    return materials.pack(pack_dir)


def shots():
    """The cameras: the whole stage, then every piece from about three blocks and from close by."""
    out = []

    def shot(name, pos, look_at):
        out.append({"name": name, "pos": [round(v, 2) for v in pos], "look_at": [round(v, 2) for v in look_at],
                    "time": TIME})

    mid = (TERRACE_X + WALL_END) / 2.0
    shot("far", (mid, 4.0, 17.0), (mid, 1.8, 0.0))
    sx, _, sz = SCOPE
    shot("scope", (sx, 1.62, sz + 3.5), (sx, 1.3, sz))
    shot("scope_near", (sx + 1.3, 1.9, sz + 1.5), (sx + 0.2, 1.7, sz))
    shot("scope_behind", (sx - 2.2, 1.9, sz + 1.2), (sx + 0.4, 1.6, sz))
    gx, _, gz = GLOBE
    shot("globe", (gx, 1.62, gz + 3.5), (gx, 1.1, gz))
    shot("globe_near", (gx + 1.2, 1.9, gz + 1.6), (gx, 1.2, gz))
    shot("hall", (gx + 1.5, 1.62, gz + 5.0), (gx + 1.5, 1.0, gz - 1.0))
    return out
