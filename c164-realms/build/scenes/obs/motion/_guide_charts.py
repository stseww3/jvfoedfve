"""Work package motion/guide, part C, the charts themselves (c329): six star charts to be found.
Card: plan/packages/motion/guide.md.

Six small star charts lie about the observatory, one to a place, where somebody would have left
one: on the engineer's desk in the power house, on the rating bench of the time room, on the glass
of the chart room's light table, on the register desk of the plate vault, by the door of the
battery room, on a bench of the sunset terrace beside the tripod telescope. They are an easter egg
and not a task: nothing says they are there. A small glint over each, once in two seconds, is all
that asks one to come nearer; what happens when one does is motion/guide's (c357), which reads
CHARTS and calls build() here once.

The chart is the enamel star chart of props/paper, not a new model: its two kinds by turns (the
sky round the pole, the Hunter). It is shown at a quarter of its size (SCALE), a card of half a
block by a quarter: the plate itself is two blocks long and no desk of the map, dressed as they
are, has that much free top. Five lie flat, face up; the one of the battery room, where nothing
has a free top, hangs on the wall as the plate was made to.

Where each lies is worked out from its room's own constants, so that a card follows its desk; what
else lies on that desk is written beside each row, with the room that left the place free.

The glint: one wax_off particle, GLINT_UP over the middle of the card's face, no spread and no
speed, every GLINT_EVERY ticks; the six on six different ticks of the cycle. Six commands in 40
ticks: 0.15 a tick on average, one in any one tick (budget agreed with a2 and c357, 11-16).

Interface (agreed with c357): CHARTS, in the order of the tags c164.c1 .. c164.c6, one row
(name, (x, y, z), feet_y) to a chart: the middle of the card's face in scene coordinates, and the
y of the floor one stands on beside it. One is "at" a chart within REACH of (x, feet_y, z), feet
to point; STAND gives, for each, a point of that floor where one can stand and read it.
"""
import math

from ..common import skeleton as S
from ..interiors import batteryroom, chartroom, platevault, powerhouse, timeroom
from ..props import _kit as K
from ..props import furniture, paper
from . import _kit as MK

PX = 1 / 16.0
SCALE = 0.25                        # of the plate of props/paper (32 x 16 texels, 2 proud)
LONG, SHORT = 32.0 * PX * SCALE, 16.0 * PX * SCALE      # 0.5 by 0.25 blocks
PROUD = 2.0 * PX * SCALE            # the face of the card over what it lies or hangs on
KINDS = ("star_chart", "star_chart_b")
REACH = 1.6                         # blocks: the card's reach (the card of the package)
GLINT = "wax_off"
GLINT_UP = 0.3                      # blocks over the middle of the face
GLINT_EVERY = 2 * MK.SECOND         # ticks
GLINT_AT = tuple(3 + 6 * i for i in range(6))           # 3, 9 .. 33: no two in one tick

DESK_TOP = furniture.TOP["writing_desk"]
DESK_LONG, DESK_DEEP = 30.0 * PX, 14.0 * PX             # a writing desk's top


def _power():
    """The engineer's desk in the north-west corner, its back to the west wall (the room places it
    at WEST + 0.4375, DESK_Z[1]): the green lamp at its north end, the log before the chair. The
    card on the south end, clear of the log by a texel."""
    desk = (powerhouse.WEST + DESK_DEEP / 2.0, powerhouse.DESK_Z[1] + 0.0)
    at = (desk[0], powerhouse.FEET + DESK_TOP, desk[1] + DESK_LONG / 2.0 - SHORT / 2.0 - 0.5 * PX)
    stand = (desk[0] + DESK_DEEP / 2.0 + 0.5, powerhouse.FEET, at[2])
    return dict(name="power", at=at, lie=True, yaw=K.FACING["south"] + 3.0, feet=powerhouse.FEET, stand=stand)


def _time():
    """The rating bench under the west windows, the sitter on its east: the two chronometers on its
    south half, the open log before the chair. The card on the north end."""
    at = (timeroom.BENCH_X + 1.5 * PX, timeroom.FEET + DESK_TOP,
          timeroom.BENCH_Z - DESK_LONG / 2.0 + SHORT / 2.0 + 1.25 * PX)
    stand = (timeroom.BENCH_X + DESK_DEEP / 2.0 + 0.5, timeroom.FEET, at[2])
    return dict(name="time", at=at, lie=True, yaw=K.FACING["north"] - 4.0, feet=timeroom.FEET, stand=stand)


def _chart():
    """The light table: on its third pane from the door, in the south-east corner of the glass,
    which the two loose plates of that pane leave free; the viewer stands on the fourth."""
    x, z = 7.5, 22.5                # texels from the middle of the table's foot, as the room's PLATES
    table = chartroom.TABLE_AT
    at = (table[0] + x * PX, table[1] + chartroom.GLASS * PX, table[2] + z * PX)
    stand = (table[0] + chartroom.TABLE_W / 2.0 * PX + 0.5, chartroom.FEET, at[2])
    return dict(name="chart", at=at, lie=True, yaw=K.FACING["east"] + 5.0, feet=chartroom.FEET, stand=stand)


def _vault():
    """The register desk beside the lift, the clerk on its south (the room places it at X0 + 2.5,
    Z0 + 0.5): the log in the middle, the green lamp to the east. The card on the west end."""
    desk = (platevault.X0 + 2.5, platevault.Z0 + 0.5)
    at = (desk[0] - DESK_LONG / 2.0 + SHORT / 2.0 + 1.5 * PX, platevault.FEET + DESK_TOP, desk[1] + 0.5 * PX)
    stand = (at[0], platevault.FEET, desk[1] + DESK_DEEP / 2.0 + 0.5)
    return dict(name="vault", at=at, lie=True, yaw=K.FACING["west"] - 4.0, feet=platevault.FEET, stand=stand)


def _battery():
    """The battery room has no free top: the card hangs on the south wall west of the door, at the
    height of the hand, under the cable that runs along the top of the dado (CABLE_Y); the record
    board and the apron hang east of the door, the carboys stand in the corner."""
    at = (batteryroom.HALL_DOOR[0] - 1.75, batteryroom.FEET + 1.5, batteryroom.SOUTH)
    stand = (at[0], batteryroom.FEET, batteryroom.SOUTH - 0.6)
    return dict(name="battery", at=at, lie=False, facing="north", feet=batteryroom.FEET, stand=stand)


def _sunset():
    """The sunset terrace: on the seat of the bench next north of the tripod telescope, at the end
    towards it (props/furniture puts a pair of benches SUNSET_BENCHES[0] off the terrace's middle,
    props/instruments the telescope on its axis)."""
    (cx, cz), (west, off) = S.SUNSET_PLATFORM["centre"], furniture.SUNSET_BENCHES[0]
    bench = (S.mid(cx) - west, S.mid(cz) - off)
    at = (bench[0], S.GROUND + furniture.TOP["bench"], bench[1] + 15.0 * PX - LONG / 2.0 - 2.0 * PX)
    stand = (bench[0] - 0.25 - 0.5, S.GROUND, at[2])
    return dict(name="sunset", at=at, lie=True, yaw=K.FACING["west"], feet=S.GROUND, stand=stand)


def _face(row):
    """The middle of the card's face."""
    x, y, z = row["at"]
    if row["lie"]:
        return (x, y + PROUD, z)
    dx, _, dz = K.turn(K.FACING[row["facing"]], (0.0, 0.0, PROUD))
    return (x + dx, y, z + dz)


def _r(point):
    return tuple(round(float(v), 4) for v in point)


ROWS = (_power(), _time(), _chart(), _vault(), _battery(), _sunset())
CHARTS = tuple((row["name"], _r(_face(row)), int(row["feet"])) for row in ROWS)
STAND = tuple(_r(row["stand"]) for row in ROWS)


def reach(i):
    """How far the feet of somebody who stands at STAND[i] are from the point chart i is measured
    at, (x, feet_y, z): the card's reach wants it under REACH."""
    (x, _, z), feet = CHARTS[i][1], CHARTS[i][2]
    sx, sy, sz = STAND[i]
    return math.sqrt((sx - x) ** 2 + (sy - feet) ** 2 + (sz - z) ** 2)


def build(canvas, origin=(0, 0, 0)):
    """Place the six cards and register their glints with motion/_kit; returns the number of
    display entities (6). Called once by motion/guide."""
    n = 0
    for i, row in enumerate(ROWS):
        kind = KINDS[i % len(KINDS)]
        if row["lie"]:
            n += paper.place(canvas, kind, row["at"], lie=True, yaw=row["yaw"], origin=origin, scale=SCALE)
        else:
            n += paper.place(canvas, kind, row["at"], facing=row["facing"], origin=origin, scale=SCALE)
        x, y, z = CHARTS[i][1]
        MK.puff(canvas, (x, y + GLINT_UP, z), GLINT, GLINT_EVERY, at=(GLINT_AT[i],), count=1, origin=origin)
    return n
