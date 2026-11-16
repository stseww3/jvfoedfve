"""interiors/_timeroom_wiring -- the wiring one sees in the time room: a part of interiors/timeroom
(plan/packages/interiors/timeroom-helpers.md, section 2), written by the props/electrics line.

One level of wiring runs round the south-west corner of the room, at the height of the gap between
the clock board and the lamp over it (LINE_Y):

    the clock line   a pair of wires on porcelain knobs along the west wall, from the cased riser
                     to the northernmost slave clock. The five dials hang in series, as the dials
                     of an impulse system do: the upper wire runs straight through, the lower one
                     comes down into each clock at one terminal and leaves it at the other. At the
                     last clock both wires come down: the line ends in what it feeds.
    the outlet       where the line leaves the riser: a small cast-iron box on the riser's east
                     face, the flash on its label. The pair leaves its north side and goes round
                     the riser's corner to the west wall; the bell wire enters its south side.
    the bell         over the door, on a wooden board; its wire runs west along the south wall,
                     on the top of the door case, to the box on the riser.
    the phone feed   under the wall telephone on the pier north of the message desk: a small box,
                     a lead up into the telephone and a wire down the pier into the floor.

Nothing here throws light, and nothing is lighter than a dial: the porcelain is a step under the
dials' (porcelain 2), the label of the box a dim cream. Nothing reads as a cross: a wire ends where
it turns, a knob is as tall as the pair it holds, and the stems of a clock hang under the line
without standing through it (plan red line 8).

The models are the room's own (timeroom.PREFIX); every measure is read from timeroom's tables.
"""
import functools
import math

from artkit import models as M
from artkit.pixelart import Sprite

from ..common import palette as P
from ..common import skeleton as S
from ..props import _kit as K
from . import timeroom as T

PX = T.PX
IRON, IRON_D = K.IRON, K.IRON_D
BRASS, BRASS_D = K.BRASS, K.BRASS_D
PORC = P.mat("porcelain", base=2)       # a step under the dials (porcelain 3)
PORC_CAP = K.flat("porcelain", 2)
LINE = K.flat("old_copper", 3)          # the clock line: on the west wall a face that looks into the room is lit by half
WIRE = K.flat("old_copper", 2)          # the single wires, on walls that are lit better
COIL = P.mat("old_copper", base=1)
WOOD_D = P.mat("dark_wood", base=1)
SCREW = K.flat("brass", 3)
LABEL = K.flat("cream", 1)
FLASH = Sprite("int_timeroom_flash", ["wwrw", "wrww", "rrrr", "wwrw", "wrww"],
               {"w": P.RAMPS["cream"][1], "r": P.RAMPS["signal"][2]})

# ---- the measures (px = 1/16 block unless a name says otherwise) ----------------------------------------
BOARD_TOP = T.DIAL_Y + T.BOARD[1] * PX                  # 10.09: the top of the clock board
PLATE_FOOT = BOARD_TOP + T.OVER - 11.0 * PX             # 10.66: the foot of the wall plate of the lamp over the clocks (props/lamps' bracket_b)
LINE_Y = (BOARD_TOP + PLATE_FOOT) / 2.0                 # 10.375: the axis of the pair, midway between the two
OFF = 1.5               # a wire's axis off the face it runs along
GAUGE = 1.5             # each wire of the pair above and below the pair's axis
KNOB = 2.5              # the radius of a knob: it covers the pair and no more
DIAL = (LINE_Y - T.DIAL_Y) / PX                         # 13.5: the middle of a dial under the axis
TERMINAL = 2.0          # a clock's two terminals, either side of the middle of its case
CASE_TOP = -DIAL + math.sqrt(T.CASE_R ** 2 - TERMINAL ** 2)     # -7.84: the top of the case there
POST = (CASE_TOP - 0.4, CASE_TOP + 1.35)                # a terminal post: sunk a little into the case, so it sits on any facet of it
CELL = 8.0              # half a cell: a clock to a cell (timeroom.BOARD is as wide)

BOX = 4.0               # half the outlet box, square
BOX_Z = (T.RISER[1] + T.PANEL_S) / 2.0                  # -6.59: the middle of what is seen of the riser's east face
FACE = (T.PANEL_S - T.RISER[1]) / 2.0 / PX              # 6.5: from there to the riser's corner, and to the south wall's panelling
ROUND = (T.RISER[0] + 1.0 - T.PANEL_W) / PX             # 13: the riser's north face, from its corner to the west wall's panelling

BELL = (4.0, 8.0)       # half the bell's board, across and up
BELL_Y = LINE_Y + (1.0 + BELL[1]) * PX                  # 10.94: its middle; the board stands a pixel over the wire
CLIP_X = (T.X0 + 1.75, T.DOOR_X[0] - 0.75)              # 3.75, 6.25: either side of the blueprint over the card cabinets

TAP, TAP_END = T.PREFIX + "wire_tap", T.PREFIX + "wire_tap_end"
OUTLET, BELL_NAME = T.PREFIX + "wire_outlet", T.PREFIX + "bell"
DRAWN, CLIP, FEED = T.PREFIX + "wire", T.PREFIX + "wire_clip", T.PREFIX + "phone_feed"

assert T.CLOCK_Z[1] + 1 == T.RISER[1], "the clock line starts on the riser's face: the southernmost clock's cell borders the riser"
assert KNOB + 0.5 <= (PLATE_FOOT - BOARD_TOP) / PX / 2.0, "the line no longer fits between the clock board and the lamp over it"


def _phone():
    """The room's wall telephone (a piece of props/electrics in timeroom.PIECES), or None."""
    for p in T.PIECES:
        if p["package"] == "electrics" and p["kind"] == "wall_phone":
            return p
    return None


# ---- the models ----------------------------------------------------------------------------------------
def _knob(m, x):
    """A porcelain knob on the wall behind the pair, a brass screw through its middle."""
    m.tube("z", (x, 0.0), 0.0, 3.0, KNOB, PORC, sides=8, cap=PORC_CAP)
    K.rivet(m, (x, 0.0, 3.0), mat=SCREW)


def _posts(m):
    for x in (-TERMINAL, TERMINAL):
        m.box((x - 1.0, POST[0], 0.5), (x + 1.0, POST[1], 2.5), BRASS)


def _tap(last):
    """The clock line over one clock, a cell long. The upper wire runs through; the lower wire
    comes down to the terminal on the south of the case and goes on from the one on the north, with
    a knob where the cell ends. Over the last clock the line ends: the lower wire comes down to
    the first terminal, the upper one to the second. Anchor: on the wall, on the axis of the pair
    over the middle of the dial; +x is north, the way the line runs."""
    m = M.Model(TAP_END if last else TAP)
    hi, lo = (GAUGE - 0.5, GAUGE + 0.5), (-GAUGE - 0.5, -GAUGE + 0.5)
    a, b = -TERMINAL, TERMINAL
    _posts(m)
    m.box((-CELL, lo[0], 1.0), (a + 0.5, lo[1], 2.0), LINE, grain="x")              # the lower wire, in
    m.box((a - 0.5, POST[1], 1.0), (a + 0.5, lo[1], 2.0), LINE, grain="y")          # ... and down
    if last:
        m.box((-CELL, hi[0], 1.0), (b + 0.5, hi[1], 2.0), LINE, grain="x")          # the upper wire ends here
        m.box((b - 0.5, POST[1], 1.0), (b + 0.5, hi[1], 2.0), LINE, grain="y")
        return m
    m.box((-CELL, hi[0], 1.0), (CELL, hi[1], 2.0), LINE, grain="x")                 # the upper wire, through
    m.box((b - 0.5, POST[1], 1.0), (b + 0.5, lo[1], 2.0), LINE, grain="y")          # the lower wire, up again
    m.box((b - 0.5, lo[0], 1.0), (CELL, lo[1], 2.0), LINE, grain="x")               # ... and on
    _knob(m, CELL)
    return m


def _outlet():
    """Where the line leaves the riser: a cast-iron box on the riser's east face, the flash on its
    label. The pair leaves its north side through a porcelain block, turns round the riser's
    corner and runs along its north face, over a knob, to where the first tap takes it up on the
    west wall. On the south side a porcelain bush, in the corner with the south wall: the bell
    wire ends in it. Anchor: on the riser's east face, the middle of the box; +x is north."""
    m = M.Model(OUTLET)
    m.box((-BOX, -BOX, 0.0), (BOX, BOX, 3.5), IRON, grain="y")                      # the box
    m.box((-BOX + 0.5, -BOX + 0.5, 3.5), (BOX - 0.5, BOX - 0.5, 4.25), IRON_D, grain="y")
    m.box((-2.0, -2.5, 4.25), (2.0, 2.5, 4.5), LABEL, faces={"s": FLASH}, skip="n")
    m.box((BOX, -KNOB, 0.5), (BOX + 1.0, KNOB, 2.5), PORC)                          # the block the pair comes out of
    m.box((-FACE, -1.5, 0.0), (-BOX, 1.5, 3.5), PORC)                               # the bush of the bell wire
    turn = FACE + OFF                                                               # the pair's axis on the north face
    far = -(ROUND - OFF - 0.5)                                                      # where the tap's wires stand, on the west wall
    for y in (GAUGE, -GAUGE):
        m.box((BOX + 1.0, y - 0.5, 1.0), (turn + 0.5, y + 0.5, 2.0), LINE, grain="x")
        m.box((turn - 0.5, y - 0.5, far), (turn + 0.5, y + 0.5, 2.0), LINE, grain="z")
    z = (far + 2.0) / 2.0
    m.tube("x", (0.0, z), FACE, FACE + 3.0, KNOB, PORC, sides=8, cap=PORC_CAP)      # the knob on the north face
    K.rivet(m, (FACE + 3.0, 0.0, z), out="x", mat=SCREW)
    return m


def _bell():
    """The door bell, props/electrics' bell on a wooden board: two coils side by side under their
    yoke, the armature across their feet with the hammer at its end, the brass gong under them.
    No conduit: its wire comes along the wall under the board and ends in the porcelain block
    under the board's west corner. Anchor: on the wall, the middle of the board; +x is west."""
    w, h = BELL
    m = M.Model(BELL_NAME)
    m.box((-w, -h, 0.0), (w, h, 1.0), WOOD_D, grain="y")                            # the board
    for x in (-w + 1.0, w - 1.0):
        for y in (-h + 1.0, h - 1.0):
            K.rivet(m, (x, y, 1.0), mat=SCREW)
    g = (0.0, -3.5, 1.0)
    with m.turned(("x", 90.0), about=g):                                            # the gong bulges out of the wall
        m.ball(g, 3.5, BRASS, sides=12, layers=3, squash=0.6, part=(0.0, 1.0))
    m.tube("z", (0.0, -3.5), 2.9, 3.6, 0.75, BRASS_D)                               # the nut that holds it
    m.box((-3.0, 0.5, 1.75), (3.0, 1.25, 3.25), IRON, grain="x")                    # the armature
    m.box((2.5, -0.25, 2.25), (3.0, 0.5, 2.75), IRON_D)                             # the hammer's stem
    m.tube("z", (2.75, -0.6), 1.9, 3.1, 0.75, IRON)                                 # the hammer, at the gong's rim
    for x in (-1.75, 1.75):                                                         # the coils
        m.tube("y", (x, 2.5), 1.25, 1.75, 1.5, BRASS_D)
        m.tube("y", (x, 2.5), 1.75, 4.75, 1.25, COIL)
        m.tube("y", (x, 2.5), 4.75, 5.25, 1.5, BRASS_D)
    m.box((-3.25, 5.25, 1.0), (3.25, 6.0, 3.5), IRON, grain="x")                    # the yoke
    m.box((w - 2.5, -h - 2.0, 0.0), (w, -h, 2.5), PORC)                             # the block the wire ends in
    return m


def _wire():
    """A single wire: runs along +z from the anchor, 48 long, and is drawn out between two points.
    One flat tone, so drawing it out smears nothing."""
    m = M.Model(DRAWN)
    m.box((-0.5, -0.5, 0.0), (0.5, 0.5, 48.0), WIRE, grain="z")
    return m


def _clip():
    """What holds the single wire to the wall: a porcelain button the wire runs through. Anchor: on
    the wall behind the wire's axis."""
    m = M.Model(CLIP)
    m.tube("z", (0.0, 0.0), 0.0, 2.5, 1.5, PORC, sides=8, cap=PORC_CAP)
    return m


def _feed(drop):
    """The telephone's feed: a small iron box under the telephone, a lead from it up into the
    battery box, a wire down the pier that goes into the floor through an iron collar, `drop`
    under the telephone's foot. Anchor: the telephone's own, on the wall behind the middle of its
    foot."""
    m = M.Model(FEED)
    m.box((-0.5, -3.0, 1.0), (0.5, 2.0, 2.0), WIRE, grain="y")                      # the lead, into the battery box
    m.box((-3.0, -9.0, 0.0), (3.0, -3.0, 3.0), IRON, grain="y")                     # the box
    m.box((-2.5, -8.5, 3.0), (2.5, -3.5, 3.5), IRON_D, grain="y")
    K.rivet(m, (0.0, -6.0, 3.5), mat=SCREW)
    m.box((-0.5, -drop, 1.0), (0.5, -9.0, 2.0), WIRE, grain="y")                    # the wire down the pier
    m.tube("y", (0.0, 1.5), -drop, -drop + 1.0, 1.25, IRON)                         # the collar in the floor
    return m


@functools.lru_cache(maxsize=None)
def _models():
    out = {TAP: _tap(False), TAP_END: _tap(True), OUTLET: _outlet(), BELL_NAME: _bell(), DRAWN: _wire(), CLIP: _clip()}
    phone = _phone()
    if phone is not None:
        out[FEED] = _feed((phone["where"][1] - T.FEET) / PX)
    return out


def models():
    return dict(_models())


# ---- placing ---------------------------------------------------------------------------------------------
def dress(canvas, origin=(0, 0, 0)):
    """Hang the room's wiring; returns the number of display entities placed. The telephone's feed
    is hung only with the telephone, a piece of props/electrics."""
    own = _models()
    n = 0
    for z in range(T.CLOCK_Z[1], T.CLOCK_Z[0] - 1, -1):                             # from the riser northwards
        name = TAP_END if z == T.CLOCK_Z[0] else TAP
        n += K.put(canvas, own[name], (T.PANEL_W, LINE_Y, S.mid(z)), mount="wall", facing="east", origin=origin)
    n += K.put(canvas, own[OUTLET], (T.RISER[0] + 1.0, LINE_Y, BOX_Z), mount="wall", facing="east", origin=origin)

    n += K.put(canvas, own[BELL_NAME], (T.AXIS_X, BELL_Y, T.PANEL_S), mount="wall", facing="north", origin=origin)
    z = T.PANEL_S - OFF * PX
    a = (T.RISER[0] + 1.0 + 3.5 * PX, LINE_Y, z)                                    # the bush on the box
    b = (T.AXIS_X - BELL[0] * PX, LINE_Y, z)                                        # the block under the bell
    a, b = (tuple(p[i] + origin[i] for i in range(3)) for p in (a, b))
    canvas.add_entity(*a, M.between(own[DRAWN], a, b))
    n += 1
    for x in CLIP_X:
        n += K.put(canvas, own[CLIP], (x, LINE_Y, T.PANEL_S), mount="wall", facing="north", origin=origin)

    phone = _phone()
    if phone is not None and T.theirs("electrics") is not None:
        n += K.put(canvas, own[FEED], phone["where"], mount="wall", facing=phone["how"]["facing"], origin=origin)
    return n
