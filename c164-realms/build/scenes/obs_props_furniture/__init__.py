"""Test scene of the work package props/furniture: the whole furniture family on one stage.

A wall of dressed stone looks south and the cameras stand south of it. The west end is a piece of
terrace paving with two benches, one seen from the front and one end-on, so the slats and the cast
end frame are both judged. The rest is a room floor with the pieces set as a room uses them: a study
corner (coat stand, writing desk with a desk lamp, swivel chair, two card cabinets side by side and
an instrument cabinet), a trunk and crates, the drafting table with its stool, a bookcase with the
library ladder on its rail, a display case and a display table. Bracket lamps on the wall light the
stage as lamps light a room.

The shots are written from the numbers below:  python -m scenes.obs_props_furniture
"""
from artkit.canvas import Canvas

from scenes.obs import materials, sky
from scenes.obs.common import blocks as B
from scenes.obs.props import furniture, lamps

BIOME = "obs_blue"
BIOME_MARGIN = 32
BIOME_MARGIN_Y = 32

STONE, PAVING, FLOOR, SHELF = B.ASHLAR_FINE.block, B.TUFF_SMOOTH.block, B.FLOOR_WOOD.block, B.DARK_WOOD.block
WALL_Z = -1
FACE = WALL_Z + 1               # the air cell in front of the wall; a wall prop's anchor sits on the face
WALL_H = 6
WEST, ROOM, EAST = -3, 11, 40   # the terrace runs from WEST to ROOM, the room floor from ROOM to EAST
DEPTH = 12
TIME = 14000                    # light version A, the default (INTERFACE: 18000 is B, 12900 is C)

BENCH = (3.0, 0.0, 1.5)         # seen from the front
BENCH_END = (8.0, 0.0, 3.0)     # turned end-on to the cameras
COAT = (12.7, 0.0, 0.8)
DESK = (15.0, 0.0, 1.5)
CHAIR = (15.2, 0.0, 3.3)
CABINETS = ((17.6, 0.0, 0.5), (18.6, 0.0, 0.5))
INSTRUMENTS = (19.6, 0.0, 0.5)   # in one row with the card cabinets: same depth, plinth and cornice
TRUNK = (21.9, 0.0, 1.0)
CRATES = ((23.7, 0.0, 0.8), (24.5, 0.0, 2.2), (23.8, furniture.TOP["crate"], 0.9))
DRAFT = (27.2, 0.0, 1.8)
STOOL = (27.2, 0.0, 3.5)
CASE_X = (30, 33)               # the bookcase: these cells along x, three high, one deep
LADDER_X = 31.5
CASE = (35.5, 0.0, 2.0)
TABLE = (38.2, 0.0, 0.5)        # against the wall, as in the star hall
LAMPS = (6.0, 13.5, 20.8, 28.6, 34.3, 38.2)


def build():
    c = Canvas()
    c.box(WEST - 1, -1, WALL_Z, ROOM - 1, -1, DEPTH, PAVING)
    c.box(ROOM, -1, WALL_Z, EAST + 1, -1, DEPTH, FLOOR)
    c.box(WEST, 0, WALL_Z, EAST, WALL_H - 1, WALL_Z, STONE)
    c.box(CASE_X[0], 0, FACE, CASE_X[1], 2, FACE, SHELF)
    place = furniture.place
    n = place(c, "bench", BENCH)
    n += place(c, "bench", BENCH_END, facing="west")
    n += place(c, "coat_stand", COAT)
    n += place(c, "writing_desk", DESK)
    n += lamps.place(c, "desk_green", (DESK[0] - 0.6, furniture.TOP["writing_desk"], DESK[2] + 0.1))
    n += place(c, "swivel_chair", CHAIR, yaw=155.0)
    for pos in CABINETS:
        n += place(c, "card_cabinet", pos)
    n += place(c, "instrument_cabinet", INSTRUMENTS)
    n += place(c, "trunk", TRUNK, yaw=-12.0)
    for i, pos in enumerate(CRATES):
        n += place(c, "crate", pos, yaw=(0.0, 30.0, 8.0)[i])
    n += place(c, "drafting_table", DRAFT)
    n += place(c, "stool", STOOL)
    shelf_front = FACE + 1.0
    n += place(c, "library_ladder", (LADDER_X, 0.0, shelf_front))
    n += furniture.rail(c, (CASE_X[0] + 0.5, 0.0, shelf_front), CASE_X[1] - CASE_X[0] + 1)
    n += place(c, "display_case", CASE)
    n += place(c, "display_table", TABLE)
    for x in LAMPS:
        n += lamps.place(c, "bracket", (x, 3.5, float(FACE)))
    sky.build(c, (0, 0, 0))             # A2's light sources go in last, when every piece is in place
    c.entity_counts = {"props": n}
    return c


def write_pack(pack_dir):
    """The repainted stone, paving and wood the furniture is judged against."""
    return materials.pack(pack_dir)


def shots():
    """The cameras: the whole stage, the groups as a room shows them, and each piece from about
    three blocks."""
    out = []

    def shot(name, pos, look_at):
        out.append({"name": name, "pos": [round(v, 2) for v in pos],
                    "look_at": [round(v, 2) for v in look_at], "time": TIME})

    def near(name, at, height, back=3.0, side=1.2, up=1.0):
        shot(name, (at[0] + side, at[1] + height + up, at[2] + back), (at[0], at[1] + height, at[2]))

    mid = (WEST + EAST) / 2.0
    shot("far", (mid, 5.0, 26.0), (mid, 1.5, 0.0))
    shot("terrace", (5.5, 2.2, 8.5), (5.5, 0.8, 2.0))
    shot("study", (16.0, 2.4, 7.5), (16.0, 1.0, 1.0))
    shot("stores", (22.0, 2.4, 7.5), (22.0, 1.0, 1.0))
    shot("workroom", (29.0, 2.6, 8.5), (29.5, 1.2, 1.0))
    near("bench", BENCH, 0.5)
    near("bench_end", BENCH_END, 0.5, back=2.6, side=0.4)
    near("coat_stand", COAT, 1.2, back=3.2, side=-0.8, up=0.5)
    near("writing_desk", DESK, 0.7, back=3.4, side=1.6, up=1.2)
    near("swivel_chair", CHAIR, 0.5, back=2.4, side=1.8, up=0.9)
    near("card_cabinet", CABINETS[0], 1.0, back=3.2, side=1.6, up=0.6)
    near("instrument_cabinet", INSTRUMENTS, 1.0, back=3.2, side=1.4, up=0.6)
    near("trunk_crates", (23.2, 0.0, 1.2), 0.5, back=3.4, side=0.6, up=1.2)
    near("drafting_table", DRAFT, 1.0, back=3.4, side=1.8, up=0.9)
    near("drafting_side", DRAFT, 0.9, back=1.2, side=3.2, up=0.4)
    near("stool", STOOL, 0.4, back=2.2, side=-1.4, up=0.9)
    near("library_ladder", (LADDER_X, 0.0, 1.5), 1.5, back=4.2, side=1.8, up=0.3)
    near("display_case", CASE, 0.9, back=3.0, side=1.4, up=0.8)
    near("display_table", TABLE, 0.6, back=2.8, side=-1.2, up=1.3)
    return out
