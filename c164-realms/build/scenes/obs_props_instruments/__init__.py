"""Test scene of the work package props/instruments: the small instruments on one stage.

The cameras stand south and look north. From west to east:

    the terrace (open paving west of the wall, lit by the sky alone, the sky behind)
        a row of four, seven blocks from piece to piece: the telescope that is trained on the
        comet (placed by instruments.site(), as the one on the sunset terrace is), open sky to its
        west; the tripod telescope side-on, looking west; the louvre box; on a stone pedestal the
        sunshine recorder
    the hall (a wall of dressed stone that looks south, a wooden floor, bracket lamps high up)
        the celestial globe; on the wall the barometer, the regulator clock and, beside it, its
        pendulum once more by itself and swung out, to show the part that moves and its pivot; at
        the far end, on a counter, the table globe, the sextant and the calculating machine

A shot holds a piece whole or not at all: the pieces stand so far apart, and the cameras look so
squarely at the wall, that no neighbour and no lamp is cut off by the frame's edge (the game's
picture is 109 degrees wide). What a close view cuts is its own piece, and the stage's stone.

When props/furniture is in the tree a writing desk and a chair stand beside the celestial globe, so
the instruments are seen at the scale of the rooms, and the shot globe_desk is taken; until then
the wooden counter of blocks is the only table.

The shots are written from the numbers below:  python -m scenes.obs_props_instruments
"""
import math

from artkit.canvas import Canvas

from scenes.obs import materials, sky
from scenes.obs.common import blocks as B
from scenes.obs.props import _kit as K
from scenes.obs.props import instruments, lamps

try:                                    # the furniture family is another card: used once it is merged
    from scenes.obs.props import furniture
except ImportError:
    furniture = None

BIOME = "obs_blue"
BIOME_MARGIN = 32
BIOME_MARGIN_Y = 32

STONE, PAVING, FLOOR, WOOD = B.ASHLAR_FINE.block, B.TUFF_SMOOTH.block, B.FLOOR_WOOD.block, B.DARK_WOOD.block
WALL_H = 7
WALL_X0, WALL_X1 = -8, 36                       # the wall's first and last column
TERRACE_X0, TERRACE_Z1 = -44, 16                # the paving runs west and south to here
ROW_Z = 4.5                                     # the terrace's row, seven blocks from piece to piece
SCOPE_COMET = (-39.5, 0.0, ROW_Z)               # open sky to its west, a clear walk of five blocks to its east
SCOPE = (-32.5, 0.0, ROW_Z)
LOUVRE = (-25.5, 0.0, ROW_Z)
PEDESTAL = (-19, 4)                             # the cell of a one-block stone pedestal
SUNSHINE = (PEDESTAL[0] + 0.5, 1.0, PEDESTAL[1] + 0.5)
GLOBE = (0.0, 0.0, 2.0)
DESK = (2.5, 0.0, 2.2)                          # the writing desk beside the globe, when there is one
BAROMETER = (9.0, 1.0, 0.0)                     # wall pieces: the point on the wall behind their foot
CLOCK = (13.5, 0.5, 0.0)
PENDULUM = (15.75, 2.25, 0.0)                   # the spare pendulum: its pivot
PENDULUM_SWING = 12.0
COUNTER = (21, 28)                              # a counter of blocks, first and last column, its top at y 1
TABLE = {"globe": 22.0, "sextant": 25.0, "calc_machine": 28.0}
TABLE_Z = 1.5
HALL_LAMPS = tuple(-2.25 + 4.5 * i for i in range(8))   # the globe between the first two, the clock between two
LAMP_Y = 5.25                                   # over the frame of every close view
TIME = 14000                    # light version A, the default (INTERFACE: 18000 is B, 12900 is C)


def build():
    # no face of an instrument may stand between two axes: the game lights such a face one way on
    # one piece and the other way on its twin (_kit.settle sees to it where the models are built)
    loose = sorted(name for name, model in instruments.models().items() if K.unsettled(model))
    assert not loose, f"faces between two axes, not settled: {loose}"
    c = Canvas()
    c.box(TERRACE_X0, -1, -1, WALL_X1 + 2, -1, TERRACE_Z1, PAVING)
    c.box(WALL_X0 + 1, -1, 0, WALL_X1 - 1, -1, 6, FLOOR)
    c.box(WALL_X0, 0, -1, WALL_X1, WALL_H - 1, -1, STONE)
    c.box(COUNTER[0], 0, 1, COUNTER[1], 0, 1, WOOD)
    c.box(PEDESTAL[0], 0, PEDESTAL[1], PEDESTAL[0], 0, PEDESTAL[1], STONE)
    n = 0
    for x in HALL_LAMPS:
        n += lamps.place(c, "bracket", (x, LAMP_Y, 0.0))
    n += instruments.place(c, "tripod_scope", SCOPE, facing="west")
    # the comet's telescope is placed the way the master scene places it on the sunset terrace, through
    # site(): the stage's paving lies where that terrace's would if the scene's origin were moved
    point = next(p for group, _, p, _ in instruments.site_pieces() if group == "sunset")
    n += instruments.site(c, origin=tuple(a - b for a, b in zip(SCOPE_COMET, point)), groups=("sunset",))
    n += instruments.place(c, "louvre_box", LOUVRE)
    n += instruments.place(c, "sunshine_recorder", SUNSHINE)
    n += instruments.place(c, "celestial_globe", GLOBE)
    n += instruments.place(c, "barometer", BAROMETER)
    n += instruments.place(c, "regulator_clock", CLOCK)
    n += instruments.place(c, "regulator_pendulum", PENDULUM, turns=(("z", PENDULUM_SWING),))
    for kind, x in TABLE.items():
        n += instruments.place(c, kind, (x, 1.0, TABLE_Z))
    if furniture is not None:
        n += furniture.place(c, "writing_desk", DESK)
        n += furniture.place(c, "swivel_chair", (DESK[0], 0.0, DESK[2] + 1.1), facing="north")
    sky.build(c, (0, 0, 0))         # A2's light sources go in last, when every lamp is in place
    c.entity_counts = {"props": n}
    return c


def write_pack(pack_dir):
    """The repainted stone the instruments are judged against, and the map's sky: the terrace looks
    west, where the comet stands that one telescope is trained on, and the game's own sun must not."""
    return list(materials.pack(pack_dir) or []) + list(sky.pack(pack_dir) or [])


def shots():
    """The cameras: each half of the stage, then every piece square on from about three blocks and
    from close by; the celestial globe also from the side (its rings from another angle), from above
    (the scale on the horizon ring) and in the plane of its half meridian."""
    out = []

    def shot(name, pos, look_at):
        out.append({"name": name, "pos": [round(v, 2) for v in pos], "look_at": [round(v, 2) for v in look_at],
                    "time": TIME})

    sx, _, sz = SCOPE
    lx, _, lz = LOUVRE
    kx, _, kz = SCOPE_COMET
    px, py, pz = SUNSHINE
    mid = (kx - 1.0 + px + 0.4) / 2.0
    shot("terrace", (mid, 2.3, ROW_Z + 9.5), (mid, 1.3, ROW_Z))
    shot("scope", (sx, 1.62, sz + 3.2), (sx, 1.25, sz))
    shot("scope_near", (sx + 0.4, 1.75, sz + 1.5), (sx + 0.1, 1.45, sz))
    # from where the observer comes up to the eyepiece, between the two rear legs
    shot("scope_behind", (sx + 1.3, 1.85, sz + 1.9), (sx - 0.1, 1.5, sz))
    # the comet's telescope: side-on, its eyepiece end, and from five blocks behind it as one comes up
    # the walk, looking west and up: the tube is seen along its length there and has to run into the
    # comet's head, which stands in the upper third of the picture (and a tube standing over a fork
    # must not read as a cross: red line 8)
    shot("scope_comet", (kx + 0.4, 1.62, kz + 3.4), (kx, 1.45, kz))
    shot("scope_comet_near", (kx + 1.3, 1.8, kz + 1.2), (kx, 1.5, kz))
    up = math.radians(16.0)
    shot("scope_comet_aim", (kx + 5.0, 1.62, kz), (kx + 5.0 - 10.0 * math.cos(up), 1.62 + 10.0 * math.sin(up), kz))
    shot("louvre", (lx - 0.4, 1.62, lz + 3.0), (lx, 1.1, lz))
    shot("louvre_near", (lx - 0.5, 1.75, lz + 1.6), (lx, 1.35, lz))
    shot("sunshine", (px + 0.2, py + 0.75, pz + 1.9), (px, py + 0.3, pz))
    shot("sunshine_near", (px + 0.15, py + 0.7, pz + 1.0), (px, py + 0.35, pz))
    mid = (GLOBE[0] - 0.9 + TABLE["calc_machine"] + 0.6) / 2.0
    shot("hall", (mid, 2.3, 14.0), (mid, 1.4, 0.5))
    gx, _, gz = GLOBE
    shot("globe", (gx, 1.62, gz + 3.0), (gx, 1.05, gz))
    shot("globe_near", (gx + 0.8, 1.8, gz + 1.9), (gx, 1.15, gz))
    shot("globe_top", (gx + 0.5, 3.4, gz + 1.1), (gx, 1.2, gz))
    # in the plane of the half meridian, from the west (the desk, when there is one, stands east of
    # the globe): the meridian is one upright line there, under the level band of the horizon ring
    # and not above it (red line 8: no bar across a bar); the same view against a plain backdrop,
    # near and far, is in the gallery (props.GALLERY)
    a = math.radians(instruments.GLOBE_YAW)
    shot("globe_edge", (gx - 3.0 * math.cos(a), 1.62, gz + 3.0 * math.sin(a)), (gx, 1.0, gz))
    if furniture is not None:
        shot("globe_desk", (gx + 1.4, 1.62, gz + 4.2), (gx + 1.3, 0.9, gz))
    bx, by, _ = BAROMETER
    shot("barometer", (bx + 0.3, by + 1.0, 2.2), (bx, by + 1.0, 0.0))
    shot("barometer_dial", (bx + 0.25, by + 0.6, 1.1), (bx, by + 0.45, 0.0))
    cx, cy, _ = CLOCK
    shot("clock", (cx - 0.3, cy + 1.1, 2.4), (cx, cy + 1.0, 0.0))
    shot("clock_dial", (cx + 0.25, cy + 1.7, 1.25), (cx, cy + 1.6, 0.2))
    between = (cx + PENDULUM[0]) / 2.0
    shot("pendulum", (between, cy + 1.0, 2.0), (between, cy + 0.9, 0.1))
    # the counter: looked down on, as one stands at a table, and square on
    tx = TABLE["sextant"]
    shot("table", (tx, 2.3, TABLE_Z + 3.3), (tx, 1.35, TABLE_Z))
    shot("table_globe_near", (TABLE["globe"] + 0.1, 2.05, TABLE_Z + 1.2), (TABLE["globe"], 1.5, TABLE_Z))
    shot("sextant_near", (tx, 2.0, TABLE_Z + 1.2), (tx, 1.45, TABLE_Z))
    shot("calc_near", (TABLE["calc_machine"] - 0.1, 2.0, TABLE_Z + 1.25), (TABLE["calc_machine"] + 0.05, 1.3, TABLE_Z))
    return out
