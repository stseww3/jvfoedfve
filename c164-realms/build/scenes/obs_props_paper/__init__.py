"""Test scene of the work package props/paper: the whole paper family in one room corner.

A wall looks south and the cameras stand south of it, under a wooden ceiling with two pendant
lamps, so the pieces are seen in lamp light as they will be indoors. The west half of the wall is
dressed stone and the east half dark wood, the two grounds the rooms have: the wall pieces hang on
both. In front of the stone stands a desk with the log books and a blueprint laid flat; in front of
the wood a light table (a stand-in: lit frosted glass) with the glass negatives spread on it.

The shots are written from the numbers below:  python -m scenes.obs_props_paper
"""
from artkit.canvas import Canvas

from scenes.obs import materials, sky
from scenes.obs.common import blocks as B
from scenes.obs.props import lamps, paper

BIOME = "obs_blue"
BIOME_MARGIN = 32
BIOME_MARGIN_Y = 32

STONE, WOOD, FLOOR = B.ASHLAR_FINE.block, B.DARK_WOOD.block, B.FLOOR_WOOD.block
DESK = B.DARK_WOOD.slab + "[type=top]"
GLASS = B.WINDOW_FROSTED.block
WALL_Z = -1
FACE = WALL_Z + 1.0             # the wall face: a wall piece's anchor lies on it
WALL_H = 5
STONE_X = (-2, 9)               # the two halves of the wall, first and last block
WOOD_X = (10, 21)
EYE = 2.5                       # the height the wall pieces are centred on
# the middle of each wall piece along the wall; every piece hangs once on stone and once on wood
HANG = {"star_chart": (1.0, 16.0), "blueprint": (4.25, 19.25), "moon_map": (7.25, 12.75)}
BOARD_X = (-1.0, None)          # the blackboard hangs on stone only
DESK_X, DESK_Z = (2, 6), (2, 3)
TABLE_X, TABLE_Z = (14, 17), (2, 3)
TOP = 1.0                       # the top of the desk and of the light table
LAMPS = ((4.5, 2.5), (15.5, 2.5))
TIME = 14000                    # light version A, the default (INTERFACE: 18000 is B, 12900 is C)

ON_DESK = (("logbook", (3.0, 2.8), 12.0, {}), ("logbook_shut", (4.2, 3.3), -24.0, {}),
           ("logbook_shut", (4.4, 2.5), 70.0, {}), ("blueprint", (5.75, 3.0), 8.0, {"lie": True}))
ON_TABLE = (("photo_plate", (14.6, 2.7), 6.0, {}), ("photo_plate_b", (15.6, 3.3), -14.0, {}),
            ("photo_plate_c", (16.5, 2.5), 20.0, {}), ("photo_plate", (17.3, 3.3), 84.0, {}),
            ("photo_plate_b", (15.5, 2.4), 0.0, {}))


def build():
    c = Canvas()
    c.box(STONE_X[0] - 1, -1, WALL_Z, WOOD_X[1] + 1, -1, 9, FLOOR)
    c.box(STONE_X[0], 0, WALL_Z, STONE_X[1], WALL_H - 1, WALL_Z, STONE)
    c.box(WOOD_X[0], 0, WALL_Z, WOOD_X[1], WALL_H - 1, WALL_Z, WOOD)
    c.box(STONE_X[0], WALL_H, WALL_Z, WOOD_X[1], WALL_H, 4, WOOD)                # the ceiling
    c.box(DESK_X[0], 0, DESK_Z[0], DESK_X[1], 0, DESK_Z[1], DESK)
    c.box(TABLE_X[0], 0, TABLE_Z[0], TABLE_X[1], 0, TABLE_Z[1], GLASS)
    n = 0
    for kind, xs in HANG.items():
        for x in xs:
            n += paper.place(c, kind, (x, EYE, FACE))
    n += paper.place(c, "blackboard", (BOARD_X[0], EYE - 0.25, FACE))
    for kind, (x, z), yaw, how in ON_DESK + ON_TABLE:
        n += paper.place(c, kind, (x, TOP, z), yaw=yaw, **how)
    for x, z in LAMPS:
        n += lamps.place(c, "pendant", (x, float(WALL_H), z), level=12)
    sky.build(c, (0, 0, 0))         # A2's light sources go in last, when every lamp is in place
    c.entity_counts = {"props": n}
    return c


def write_pack(pack_dir):
    """The repainted stone and frosted glass the papers are judged against."""
    return materials.pack(pack_dir)


def shots():
    """The cameras: the whole corner from afar, each half of the wall, every piece from about three
    blocks and closer, the desk and the light table from where a player stands over them."""
    out = []

    def shot(name, pos, look_at):
        out.append({"name": name, "pos": [round(v, 2) for v in pos], "look_at": [round(v, 2) for v in look_at],
                    "time": TIME})

    mid = (STONE_X[0] + WOOD_X[1] + 1) / 2.0
    shot("far", (mid, 3.2, 15.0), (mid, 2.2, 0.0))
    shot("wall_stone", (4.0, 2.6, 7.5), (4.0, 2.3, 0.0))
    shot("wall_wood", (15.5, 2.6, 7.5), (15.5, 2.3, 0.0))
    for kind, (x, _) in HANG.items():
        shot(f"{kind}_near", (x + 0.9, EYE + 0.1, 2.6), (x, EYE, 0.0))
    x = HANG["star_chart"][1]
    shot("star_chart_wood", (x - 0.9, EYE + 0.1, 2.6), (x, EYE, 0.0))
    shot("blackboard_near", (BOARD_X[0] + 1.2, EYE, 3.0), (BOARD_X[0], EYE - 0.25, 0.0))
    shot("blackboard_side", (BOARD_X[0] + 2.4, EYE - 0.6, 1.3), (BOARD_X[0], EYE - 0.6, 0.0))
    shot("desk", (4.5, 2.9, 5.6), (4.5, TOP, 2.9))
    shot("logbook_near", (3.4, 2.1, 4.4), (3.5, TOP, 2.9))
    shot("blueprint_flat", (6.1, 2.4, 4.6), (5.75, TOP, 3.0))
    shot("light_table", (16.0, 2.9, 5.6), (16.0, TOP, 2.9))
    shot("plates_near", (15.2, 2.1, 4.3), (15.6, TOP, 2.9))
    return out
