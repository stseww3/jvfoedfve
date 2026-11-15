"""Test scene of the work package props/instruments: the small instruments on one stage.

The cameras stand south and look north. From west to east:

    the terrace (open paving west of the wall, one street lamp, the sky behind)
        the tripod telescope side-on, looking west (placed by instruments.site(), as the one on
        the sunset terrace is), the louvre box, and on a stone pedestal the sunshine recorder
    the hall (a wall of dressed stone that looks south, a wooden floor, bracket lamps)
        the celestial globe; on the wall the barometer, the regulator clock and, beside it, its
        pendulum once more by itself and swung out, to show the part that moves and its pivot; on
        a counter the table globe, the sextant and the calculating machine

When props/furniture is in the tree a writing desk and a chair stand beside the celestial globe, so
the instruments are seen at the scale of the rooms; until then the wooden counter of blocks does.

The shots are written from the numbers below:  python -m scenes.obs_props_instruments
"""
import math

from artkit.canvas import Canvas

from scenes.obs import materials, sky
from scenes.obs.common import blocks as B
from scenes.obs.props import instruments, lamps

try:                                    # the furniture family is another card: used once it is merged
    from scenes.obs.props import furniture
except ImportError:
    furniture = None

BIOME = "obs_blue"
BIOME_MARGIN = 32
BIOME_MARGIN_Y = 32

STONE, PAVING, FLOOR, WOOD = B.ASHLAR_FINE.block, B.TUFF_SMOOTH.block, B.FLOOR_WOOD.block, B.DARK_WOOD.block
WALL_H = 6
WALL_X0, WALL_X1 = -1, 17                       # the wall's first and last column
TERRACE_X0 = -17                                # the paving runs west to here
SCOPE = (-12.5, 0.0, 4.5)
STREET = (-10.5, 0.0, 4.5)                      # 8.5 blocks clear of the wall's end (lamps.STREET_CLEARANCE)
LOUVRE = (-8.5, 0.0, 4.5)
PEDESTAL = (-6, 4)                              # the cell of a one-block stone pedestal
SUNSHINE = (PEDESTAL[0] + 0.5, 1.0, PEDESTAL[1] + 0.5)
GLOBE = (2.5, 0.0, 2.0)
DESK = (5.0, 0.0, 2.2)                          # the writing desk beside the globe, when there is one
BAROMETER = (7.0, 1.0, 0.0)                     # wall pieces: the point on the wall behind their foot
CLOCK = (9.0, 0.5, 0.0)
PENDULUM = (11.0, 2.25, 0.0)                    # the spare pendulum: its pivot
PENDULUM_SWING = 12.0
COUNTER_X = 12                                  # a counter of four blocks, its top at y 1
TABLE = {"globe": COUNTER_X + 0.6, "sextant": COUNTER_X + 2.0, "calc_machine": COUNTER_X + 3.3}
TABLE_Z = 1.5
HALL_LAMPS = (2.5, 6.0, 8.0, 10.0, 14.0)
LAMP_Y = 3.0
TIME = 14000                    # light version A, the default (INTERFACE: 18000 is B, 12900 is C)


def build():
    c = Canvas()
    c.box(TERRACE_X0, -1, -1, WALL_X1 + 2, -1, 16, PAVING)
    c.box(WALL_X0 + 1, -1, 0, WALL_X1 - 1, -1, 6, FLOOR)
    c.box(WALL_X0, 0, -1, WALL_X1, WALL_H - 1, -1, STONE)
    c.box(COUNTER_X, 0, 1, COUNTER_X + 3, 0, 1, WOOD)
    c.box(PEDESTAL[0], 0, PEDESTAL[1], PEDESTAL[0], 0, PEDESTAL[1], STONE)
    n = lamps.place(c, "street", STREET)
    for x in HALL_LAMPS:
        n += lamps.place(c, "bracket", (x, LAMP_Y, 0.0))
    # the telescope is placed the way the master scene places the one of the sunset terrace, through
    # site(): the stage's paving lies where that terrace's would if the scene's origin were moved
    point = next(p for group, _, p, _ in instruments.site_pieces() if group == "sunset")
    n += instruments.site(c, origin=tuple(a - b for a, b in zip(SCOPE, point)), groups=("sunset",))
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
    """The repainted stone the instruments are judged against."""
    return materials.pack(pack_dir)


def shots():
    """The cameras: each half of the stage, then every piece from about three blocks and from close
    by; the celestial globe also from the side (its rings from another angle) and from above (the
    scale on the horizon ring)."""
    out = []

    def shot(name, pos, look_at):
        out.append({"name": name, "pos": [round(v, 2) for v in pos], "look_at": [round(v, 2) for v in look_at],
                    "time": TIME})

    sx, _, sz = SCOPE
    lx, _, lz = LOUVRE
    shot("terrace", ((sx + lx) / 2.0, 1.9, sz + 7.0), ((sx + lx) / 2.0, 1.6, sz))
    shot("scope", (sx, 1.62, sz + 3.5), (sx, 1.3, sz))
    shot("scope_near", (sx - 1.4, 1.9, sz + 1.6), (sx - 0.2, 1.6, sz))
    shot("scope_behind", (sx + 2.4, 1.8, sz + 0.9), (sx - 0.4, 1.6, sz))
    shot("louvre", (lx + 0.9, 1.62, lz + 3.2), (lx, 1.2, lz))
    shot("louvre_near", (lx + 1.3, 1.8, lz + 1.5), (lx, 1.35, lz))
    px, py, pz = SUNSHINE
    shot("sunshine", (px + 0.6, py + 0.9, pz + 2.2), (px, py + 0.35, pz))
    shot("sunshine_near", (px - 0.7, py + 0.75, pz + 1.0), (px, py + 0.4, pz))
    mid = (WALL_X0 + WALL_X1 + 1) / 2.0
    shot("hall", (mid, 2.2, 11.0), (mid, 1.4, 0.5))
    gx, _, gz = GLOBE
    shot("globe", (gx, 1.62, gz + 3.5), (gx, 1.1, gz))
    shot("globe_near", (gx + 1.3, 1.9, gz + 1.7), (gx, 1.2, gz))
    shot("globe_side", (gx - 2.6, 1.62, gz + 0.3), (gx, 1.1, gz))
    shot("globe_top", (gx + 0.5, 3.4, gz + 1.1), (gx, 1.2, gz))
    # in the plane of the meridian ring, from the east, the evening sky behind: the ring is one upright
    # line there and the horizon ring one level band (red line 8: a globe in its stand, or a cross?);
    # the same view against a plain backdrop, near and far, is in the gallery (props.GALLERY)
    a = math.radians(instruments.GLOBE_YAW)
    shot("globe_edge", (gx + 3.0 * math.cos(a), 1.62, gz - 3.0 * math.sin(a)), (gx, 1.1, gz))
    shot("globe_desk", (gx + 1.4, 1.62, gz + 4.2), (gx + 1.3, 0.9, gz))
    bx, by, _ = BAROMETER
    shot("barometer", (bx + 0.5, by + 1.0, 2.6), (bx, by + 1.0, 0.0))
    shot("barometer_dial", (bx + 0.3, by + 0.6, 1.1), (bx, by + 0.45, 0.0))
    cx, cy, _ = CLOCK
    shot("clock", (cx - 0.5, cy + 1.1, 2.7), (cx, cy + 1.0, 0.0))
    shot("clock_dial", (cx + 0.35, cy + 1.75, 1.2), (cx, cy + 1.6, 0.2))
    shot("pendulum", (cx + 1.0, cy + 1.0, 2.6), ((cx + PENDULUM[0]) / 2.0, cy + 0.9, 0.1))
    tx = TABLE["sextant"]
    shot("table", (tx, 2.0, TABLE_Z + 3.0), (tx, 1.4, TABLE_Z))
    shot("table_globe_near", (TABLE["globe"] + 0.6, 1.9, TABLE_Z + 1.3), (TABLE["globe"], 1.55, TABLE_Z))
    shot("sextant_near", (tx + 0.5, 1.8, TABLE_Z + 1.3), (tx, 1.5, TABLE_Z))
    shot("calc_near", (TABLE["calc_machine"] + 0.5, 1.9, TABLE_Z + 1.3), (TABLE["calc_machine"], 1.3, TABLE_Z))
    return out
