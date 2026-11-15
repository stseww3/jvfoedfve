"""Test scene of the work package props/paper: the whole paper family in one room corner.

A wall looks south and the cameras stand south of it, under a wooden ceiling with a row of pendant
lamps, so the pieces are seen in lamp light as they will be indoors. The west part of the wall is
dressed stone and the east part dark wood, the two grounds the rooms have: every sheet and plate
hangs on both, the pairs side by side. At the west end hang the pair of great charts, side by side
as they never will in the hall (there they face each other across it), and the blackboard. In
front of the stone stands a desk with the log books and a blueprint laid flat; in front of the
wood a light table (a stand-in of this scene: the chart room builds the real one) with the glass
negatives spread on its lit pane.

The shots are written from the numbers below:  python -m scenes.obs_props_paper
"""
from artkit.canvas import Canvas

from scenes.obs import materials, sky
from scenes.obs.common import blocks as B
from scenes.obs.props import _kit as K
from scenes.obs.props import lamps, paper

from . import props

BIOME = "obs_blue"
BIOME_MARGIN = 32
BIOME_MARGIN_Y = 32

STONE, WOOD, FLOOR = B.ASHLAR_FINE.block, B.DARK_WOOD.block, B.FLOOR_WOOD.block
DESK = B.DARK_WOOD.slab + "[type=top]"
WALL_Z = -1
FACE = WALL_Z + 1.0             # the wall face: a wall piece's anchor lies on it
WALL_H = 5
STONE_X = (-12, 11)             # the two parts of the wall, first and last block
WOOD_X = (12, 25)
EYE = 2.5                       # the height the wall pieces are centred on
# the middle of each wall piece along the wall, on stone and on wood; the pairs hang side by side
HANG = {"star_chart": (1.0, 14.0), "star_chart_b": (3.5, 16.5), "blueprint": (6.0, 19.25),
        "blueprint_b": (8.0, 21.25), "moon_map": (10.25, 23.75)}
BOARD_X = -2.0                  # the blackboard hangs on stone only
GREAT = {"sky_map": -9.5, "sky_map_b": -5.5}    # the pair of great charts, on stone
DESK_X, DESK_Z = (4, 8), (2, 3)
TABLE = (18.0, 2.75)            # the middle of the light table's foot
TOP = 1.0                       # the top of the desk and of the light table
LAMPS = tuple((x, 2.5) for x in (-8.0, -0.5, 7.0, 14.5, 22.0))
TIME = 14000                    # light version A, the default (INTERFACE: 18000 is B, 12900 is C)

ON_DESK = (("logbook", (5.0, 2.8), 12.0, {}), ("logbook_shut", (6.2, 3.3), -24.0, {}),
           ("logbook_shut", (6.4, 2.5), 70.0, {}), ("blueprint_b", (7.9, 3.0), 8.0, {"lie": True}))
ON_TABLE = (("photo_plate", (17.05, 2.6), 8.0, {}), ("photo_plate_b", (17.85, 3.0), -12.0, {}),
            ("photo_plate_c", (18.5, 2.5), 18.0, {}), ("photo_plate_b", (19.0, 3.0), 100.0, {}))


def build():
    c = Canvas()
    c.box(STONE_X[0] - 1, -1, WALL_Z, WOOD_X[1] + 1, -1, 9, FLOOR)
    c.box(STONE_X[0], 0, WALL_Z, STONE_X[1], WALL_H - 1, WALL_Z, STONE)
    c.box(WOOD_X[0], 0, WALL_Z, WOOD_X[1], WALL_H - 1, WALL_Z, WOOD)
    c.box(STONE_X[0], WALL_H, WALL_Z, WOOD_X[1], WALL_H, 4, WOOD)                # the ceiling
    c.box(DESK_X[0], 0, DESK_Z[0], DESK_X[1], 0, DESK_Z[1], DESK)
    n = K.put(c, props.table(), (TABLE[0], 0.0, TABLE[1]))
    for kind, xs in HANG.items():
        for x in xs:
            n += paper.place(c, kind, (x, EYE, FACE))
    n += paper.place(c, "blackboard", (BOARD_X, EYE - 0.25, FACE))
    for kind, x in GREAT.items():
        n += paper.place(c, kind, (x, EYE, FACE))
    for kind, (x, z), yaw, how in ON_DESK + ON_TABLE:
        n += paper.place(c, kind, (x, TOP, z), yaw=yaw, **how)
    for x, z in LAMPS:
        n += lamps.place(c, "pendant", (x, float(WALL_H), z), level=12)
    sky.build(c, (0, 0, 0))         # A2's light sources go in last, when every lamp is in place
    c.entity_counts = {"props": n}
    return c


def write_pack(pack_dir):
    """The repainted stone the papers are judged against, and the map's own sky: without it the
    game's sun stands in the open west of this corner."""
    return list(materials.pack(pack_dir) or []) + list(sky.pack(pack_dir) or [])


def shots():
    """The cameras: the whole corner from afar, the wall in three parts, every piece from about three
    blocks and closer, the desk and the light table from where a player stands over them."""
    out = []

    def shot(name, pos, look_at):
        out.append({"name": name, "pos": [round(v, 2) for v in pos], "look_at": [round(v, 2) for v in look_at],
                    "time": TIME})

    def near(name, x, dx, dy=0.1, back=2.4):
        """One wall piece from a little to one side, the way a player comes up to it."""
        shot(name, (x + dx, EYE + dy, back), (x, EYE, 0.0))

    def pair(a, b, ground):
        return (HANG[a][ground] + HANG[b][ground]) / 2.0

    mid = (STONE_X[0] + WOOD_X[1] + 1) / 2.0
    shot("far", (mid, 3.2, 17.5), (mid, 2.2, 0.0))
    great = sum(GREAT.values()) / 2.0
    shot("wall_great", (great + 1.5, 2.6, 7.0), (great + 1.5, 2.4, 0.0))
    shot("wall_stone", (5.5, 2.6, 7.0), (5.5, 2.4, 0.0))
    shot("wall_wood", (19.0, 2.6, 7.0), (19.0, 2.4, 0.0))
    for ground, tag in ((0, ""), (1, "_wood")):
        x = pair("star_chart", "star_chart_b", ground)
        shot("star_charts" + tag, (x, EYE + 0.1, 3.4), (x, EYE, 0.0))
        x = pair("blueprint", "blueprint_b", ground)
        shot("blueprints" + tag, (x, EYE + 0.1, 3.0), (x, EYE, 0.0))
    near("star_chart_near", HANG["star_chart"][0], 0.7)
    near("star_chart_b_near", HANG["star_chart_b"][0], -0.7)
    near("blueprint_near", HANG["blueprint"][0], 0.8, dy=-0.3, back=2.0)
    near("blueprint_b_near", HANG["blueprint_b"][0], -0.8, back=2.0)
    near("moon_map_near", HANG["moon_map"][0], 0.9, dy=-0.3, back=2.2)
    near("moon_map_wood", HANG["moon_map"][1], -0.8)
    shot("blackboard_near", (BOARD_X + 1.2, EYE, 3.0), (BOARD_X, EYE - 0.25, 0.0))
    shot("blackboard_side", (BOARD_X + 2.4, EYE - 0.6, 1.3), (BOARD_X, EYE - 0.6, 0.0))
    shot("sky_maps", (great, 2.2, 5.0), (great, EYE, 0.0))
    for kind, x in GREAT.items():
        near(f"{kind}_near", x, 1.2, back=3.4)
    shot("sky_map_below", (GREAT["sky_map"] + 0.5, 0.4, 2.2), (GREAT["sky_map"], EYE, 0.0))
    desk = (DESK_X[0] + DESK_X[1] + 1) / 2.0
    shot("desk", (desk, 2.9, 5.6), (desk, TOP, 2.9))
    shot("logbook_near", (5.4, 2.1, 4.4), (5.5, TOP, 2.9))
    shot("blueprint_flat", (8.25, 2.4, 4.6), (7.9, TOP, 3.0))
    shot("light_table", (TABLE[0], 2.9, 5.6), (TABLE[0], TOP, 2.9))
    shot("plates_near", (TABLE[0] - 0.6, 2.0, 4.2), (TABLE[0] - 0.2, TOP, 2.8))
    return out
