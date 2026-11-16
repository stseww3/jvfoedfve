"""interiors/_starhall_meridian -- the two lines the star hall is set out by, and what is let in
beside each: the noon line in its floor, the plumb line on the east face of its pier.

A part of interiors/starhall (starhall.PARTS): starhall.dress() calls dress(canvas, origin, version)
last and starhall.models() takes models().

THE NOON LINE

The hall lays the line itself: thin trodden copper from pilaster to pilaster through the middle of
the emblem's ring (starhall._floor). This file makes a noon line of it, the kind an observatory
keeps in its floor. The sun's image crosses such a line at noon, far up the hall in winter and
near the south wall in summer, and what lies beside the line says when:

  months      Twelve tablets in six pairs, a pair to a slab, each pair a sleeve the line runs
              through. The year goes down the east side from the north wall, I to VI, and comes
              back up the west side, VII to XII, so the two months whose noon sun stands as high
              face each other across the line. The figures stand upright to who comes in by the
              door. No slab with a crossing carries a pair: not the ring's two, not the axis'.
  noon mark   Where the line crosses the hall's axis, under the orrery's sun: a lozenge on the
              line, long the way the line runs, the plumb point in its middle. The equinoxes fall
              here, between III|X and IV|IX.
  graduation  Short strokes off the bare line: in threes either side of each crossing with the
              ring, in twos either side of the noon mark.

  a  "academy"   dark brass rails, blue enamel between them, the figures left standing in brass
  b  "workshop"  cast iron: a dark ground, the rim and the figures raised and worn lighter, a
                 rivet in each outer corner; the noon mark's point is a copper stud

What the hall asked of it (hall #68330), and how it is kept:
  - inside the line's own column of slabs, flat, under a pixel high: one picture to a slab, drawn
    on the upper face of a box that has no other, LIFT over the floor (the line's own picture lies
    a quarter of a pixel up; the lozenge is the one thing that lies over it)
  - no light, no emblem: nothing here is a ring or a star
  - no brass that runs east and west: the sleeves' rails run with the line and turn in by one
    pixel at their ends, the strokes of the graduation are three pixels at most
  - the floor's middle stays darker than the pier's face in the first look: the metal is the
    line's own trodden copper and the dark steps of brass, the enamel is darker than the stone
  - one display entity to a slab of the line: nine

THE PIER'S PLUMB LINE

The east face of the telescope pier is what the door sees first after the clock's dial, and from
the clock's top to the orrery it was bare stone with the picture's axis running up its middle
(cr3 #74826). What is drawn on it is the vertical the pier is built to. It stands in the plane
of the hall's east-west axis, so it is no meridian: the hall's meridian is the line in the floor.

  plumb line  A strip of old brass two pixels wide on the axis, from the ceiling down to the bob
              that hangs over the mother clock. The bob's point stops BOB_CLEAR pixels over the
              clock's top, which is the skeleton's, as machines/clock reads it. A short stroke
              off the strip in every bed joint of the stone: three pixels to the north at a whole
              block, two to the south at a half. No stroke has another across the strip from it,
              so nothing here reads as a cross.
  star slabs  One on each side of the strip, three blocks high, standing where the dressed stone
              begins: a round-headed slab one step under the wall's stone, its figures cut in a
              step or two deeper. The two are one winter evening as the sky is seen, east to the
              left looking south and right ascension clockwise round the pole. On the north side
              the pole star in the middle of the slab's round head and the Little Bear hanging
              from it; on the south side Orion with the Hare under his feet. A star is a round
              hole, one pixel, or two by two for those of the second magnitude and brighter (the
              belt's three are single pixels: blocks would run together). No star has rays.

What the hall asked of it (hall #75451) and the machines' reviewer (cr3 #78722), and how it is kept:
  - display entities and nothing else: no block may stand against the shaft (main/shell), and
    there is no light and no emblem
  - nothing lighter than the pier's face. A picture on a wall is an item, and the engine leaves an
    item's face that looks east a half of its tone where it leaves a block's six tenths; these
    are drawn in a frame the engine lights as it lights the wall (_wall_frame), so the tones of
    the palette mean on the slab what they mean on the stone round it. The slab's ground is
    ashlar 2 under the wall's 3, the brass is the ramp's steps 2 and 3
  - a slab reads as a slab with something on it, not as a hole: one step under the wall and no
    more, its cut lines ashlar 1, its stars ashlar 0
  - an entity takes the light of one cell where the wall is lit smoothly: the strip is one entity
    to a block, so it darkens up the pier as the stone does; a slab is one entity and takes the
    light of its middle third (SLAB_CELL). From its upper third its stars fell under the hall's
    floor for a cut line
  - eleven display entities: nine lengths of the strip, two slabs
"""
import functools
import math

import numpy as np

from artkit import models as M
from artkit.pixelart import Sprite

from ..common import palette as P
from ..common import skeleton as S
from ..machines import _relit as RL
from ..props import _kit as K
from . import starhall as H

PREFIX = H.PREFIX + "meridian_"
TILE = 16
LIFT = 0.25                 # pixels over the anchor, which K.NUDGE keeps in the cell over the floor
ROMAN = ("I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI", "XII")
FIGURES = {"I": ("#", "#", "#"), "V": ("#.#", "#.#", ".#."), "X": ("#.#", ".#.", "#.#")}   # three pixels tall
TABLET = (2, 13)            # the rows of a slab a tablet lies on, first and last: two pixels clear of each joint
SIDES = {"west": (0, 1), "east": (TILE - 1, -1)}    # the column of a tablet's rail, and the way to the line
LOZENGE = (2, 4, 6, 6, 6, 6, 4, 2)                  # the noon mark's width, row by row, about the slab's middle
STROKES = {"noon": {0: 3, 2: 2, 13: 2, 15: 3},      # row of the slab -> the stroke's length, off the line's joint
           "ring": {0: 2, 2: 3, 4: 2, 11: 2, 13: 3, 15: 2}}
JOINT = (6, 9)              # the columns of the hairline of shadow either side of the line (materials/brass_oldcopper_small)

_C, _R, _E, _I = (P.RAMPS[name] for name in ("old_copper", "brass", "enamel", "iron"))
# what a letter of the drawing is painted with. The graduation is the line's own metal in both versions.
TONES = {
    "a": {"l": _C[0], "m": _C[1], "g": _R[1],                   # a stroke: as the line is mixed
          "R": _R[1], "r": _R[0], "h": _R[2], "c": _R[1],       # a rail, its dark and light pixels, its turned-in end
          "e": _E[2], "d": _E[1], "s": _E[3],                   # the ground between rail and line
          "N": _R[2],                                           # a figure
          "B": _R[1], "H": _R[2], "D": _R[0], "p": _E[3]},      # the noon mark, its lit and shaded edges, its point
    "b": {"l": _C[0], "m": _C[1], "g": _R[1],
          "R": _I[4], "r": _I[3], "h": _I[5], "c": _I[5],
          "e": _I[2], "d": _I[1], "s": _I[3],
          "N": _I[5],
          "B": _I[3], "H": _I[4], "D": _I[2], "p": _C[1]},
}


def _dice(i, j, seed):
    """A number from 0 to 1 that depends on nothing but the pixel and the seed."""
    h = (i * 374761393 + j * 668265263 + seed * 2147483647) & 0xFFFFFFFF
    h = ((h ^ (h >> 13)) * 1274126177) & 0xFFFFFFFF
    return ((h ^ (h >> 16)) & 0xFFFF) / 65536.0


def cells():
    """The slabs the line lies on, from north to south: [(z, what lies on it)], what being "noon"
    (the slab on the hall's axis), "ring" (the line crosses the emblem's ring) or the month of
    its east tablet."""
    crossings = {z for x, z in H.roundel()[0] if x == H.CX}
    out, month = [], 0
    for z in range(H.Z0 + 1, H.Z1):
        if z == H.CZ:
            out.append((z, "noon"))
        elif z in crossings:
            out.append((z, "ring"))
        else:
            month += 1
            out.append((z, month))
    if month != 6:
        raise ValueError(f"the meridian has {month} free slabs; the twelve months want six")
    return out


def _figure(month):
    """A month's figure as it is read: three rows of pixels, a clear column between two letters."""
    return ["".join(row) for row in zip(*[col for letter in ROMAN[month - 1]
                                          for col in list(zip(*FIGURES[letter])) + [(".",) * 3]][:-1])]


def _tablet(grid, side, month, north, seed):
    """One tablet of a pair: the rail along the slab's edge, turned in by a pixel at both ends, the
    ground from there to the line's joint, and the month in it, its head to the west. The figure
    is an odd number of pixels long in an even ground: it leans towards the hall's middle."""
    rail, to_line = SIDES[side]
    first, last = TABLET
    for j in range(first, last + 1):
        roll = _dice(rail, j, seed)
        grid[j][rail] = "r" if roll < 0.2 else "h" if roll > 0.92 else "R"
        for k in range(1, 6):
            i = rail + k * to_line
            roll = _dice(i, j, seed)
            grid[j][i] = "d" if j in (first, last) or roll < 0.05 else "s" if roll > 0.97 else "e"
        if j in (first, last):
            grid[j][rail + to_line] = "c"
    rows = _figure(month)
    length = len(rows[0])
    free = last - first - 1 - length
    start = first + 1 + ((free + 1) // 2 if north else free // 2)
    head = 2 if side == "west" else TILE - 5            # the figure's upper row, as a column of the slab
    for g, row in enumerate(rows):
        for c, ch in enumerate(row):
            if ch == "#":
                grid[start + length - 1 - c][head + g] = "N"


def _strokes(grid, rows, seed):
    """The graduation: a stroke off each side of the line, from its joint outwards."""
    for j, length in rows.items():
        for k in range(length):
            for i in (JOINT[0] - 1 - k, JOINT[1] + 1 + k):
                roll = _dice(i, j, seed)
                grid[j][i] = "m" if roll < 0.25 else "g" if roll > 0.94 else "l"


def _lozenge(grid):
    """The noon mark: its edges that look north and west a step lighter, south and east a step
    darker, as every bevel of the floor is drawn; two by two pixels in the middle are its point."""
    top = (TILE - len(LOZENGE)) // 2
    inside = {(TILE // 2 - w // 2 + k, top + j) for j, w in enumerate(LOZENGE) for k in range(w)}
    for i, j in inside:
        if (i - 1, j) not in inside or (i, j - 1) not in inside:
            grid[j][i] = "H"
        elif (i + 1, j) not in inside or (i, j + 1) not in inside:
            grid[j][i] = "D"
        else:
            grid[j][i] = "B"
    for i in (TILE // 2 - 1, TILE // 2):
        for j in (TILE // 2 - 1, TILE // 2):
            grid[j][i] = "p"


def picture(what, north=False):
    """The drawing on one slab as sixteen rows of sixteen letters, north at the top and west at the
    left, as a picture lies on the ground; "." is where the floor and the line show."""
    grid = [["."] * TILE for _ in range(TILE)]
    if what == "noon":
        _strokes(grid, STROKES["noon"], 3)
        _lozenge(grid)
    elif what == "ring":
        _strokes(grid, STROKES["ring"], 5)
    else:
        _tablet(grid, "east", what, north, 10 + what)
        _tablet(grid, "west", 13 - what, north, 30 + what)
    return ["".join(row) for row in grid]


@functools.lru_cache(maxsize=None)
def _models():
    out = {}
    for version in H.VERSIONS:
        for z, what in cells():
            name = f"{PREFIX}{version}_{what}"
            if name in out:
                continue
            m = M.Model(name)
            sprite = Sprite(name, picture(what, north=z < H.CZ), TONES[version])
            m.box((-TILE / 2.0, 0.0, -TILE / 2.0), (TILE / 2.0, LIFT, TILE / 2.0), K.BRASS_D, skip="nsewd",
                  faces={"u": sprite})
            out[name] = m
    return out


# ---- the pier's east face: its plumb line and the two star slabs ------------------------------------------------
PIER = H.PREFIX + "pier_"
FACE_X = float(S.PIER_SHAFT[2] + 1)                     # 6.0: the plane of the pier's east face
FACE_Z = (S.PIER_SHAFT[1], S.PIER_SHAFT[3] + 1)         # -1, 2: its north arris and its south one
AXIS = S.AXIS_Z                                         # 0.5: the plumb line hangs on the hall's axis
CLOCK_TOP = S.MOTHER_CLOCK["y"][1]                      # 5.0: where machines/clock ends its case
BOB_CLEAR = 2                                           # pixels between the bob's point and the clock's top
SLAB_FOOT = S.STRING                                    # 6: the slabs stand where the dressed stone begins
SLAB_CELL = 1                                           # the cell, counted up from that, a slab takes its light from
STRIP = 14                                              # pixels of bare stone between the slabs, the line in the middle
WALL_SHADE = 0.6                                        # what the game leaves a block's face that looks east
EAST, NORTH = (1.0, 0.0, 0.0), (0.0, 0.0, -1.0)

_A = P.RAMPS["ashlar"]
# A slab's joint, its ground, a cut line, a star. In a slab's drawing "." is the ground and a blank
# is where the wall shows; in the strip's "." is the wall.
STONE = {"J": _A[1], ".": _A[2], "l": _A[1], "s": _A[0]}
BRASS = {"h": _R[3], "m": _R[2], "d": _R[1]}               # the strip's lit side, its body, the bob's far side

# One length of the strip, a block of it, as the door sees it: the south to the left. The stroke at
# a whole block lies in the wall's bed joint and points north, the one at half a block points south.
LENGTH = ("...hm...",) * 7 + (".mmhm...",) + ("...hm...",) * 7 + ("...hmmmm",)
BOB = (
    "..hmmm..",
    ".hhmmmd.",
    ".hmmmmd.",
    ".hmmmdd.",
    "..hmmd..",
    "..hmmd..",
    "...hd...",
    "...hd...",
    "...md...",
)
# The north slab: the pole star in the middle of the round head, as the sky turns about it, and the
# Little Bear hanging from it (delta, epsilon, zeta down the handle; eta, gamma and Kochab round
# the bowl). 1.5 pixels to the degree, the hour circle of 15 h 36 m straight down.
DIPPER = (
    "     JJJJJ     ",
    "   JJ.....JJ   ",
    "  J.........J  ",
    " J...........J ",
    " J...........J ",
    "J.............J",
    "J.............J",
    "J.....ss......J",
    "J.....ss......J",
    "J.....l.......J",
    "J....l........J",
    "J....l........J",
    "J...l.........J",
    "J...s.........J",
    "J...l.........J",
    "J...l.........J",
    "J...l.........J",
    "J..l..........J",
    "J..l..........J",
    "J..l..........J",
    "J..s..........J",
    "J..l..........J",
    "J...l.........J",
    "J...l.........J",
    "J....l........J",
    "J....l........J",
    "J.....l.......J",
    "J.....s.......J",
    "J....l.l......J",
    "J...l...ll....J",
    "J..s......l...J",
    "J...l......ss.J",
    "J....l.....ss.J",
    "J.....l....l..J",
    "J......l..l...J",
    "J.......l.l...J",
    "J........s....J",
    "J.............J",
    "J.............J",
    "J.............J",
    "J.............J",
    "J.............J",
    "J.............J",
    "J.............J",
    "J.............J",
    "J.............J",
    "J.............J",
    "JJJJJJJJJJJJJJJ",
)
# The south slab: Orion (Meissa; Betelgeuse and Bellatrix; the belt and the sword under it; Saiph
# and Rigel) and the Hare under his feet (the ears; eta, zeta, alpha, mu along the back; delta,
# gamma, beta along the belly). 0.9 pixels to the degree, north up.
ORION = (
    "     JJJJJ     ",
    "   JJ.....JJ   ",
    "  J.........J  ",
    " J...........J ",
    " J...........J ",
    "J.............J",
    "J.............J",
    "J.............J",
    "J.............J",
    "J.............J",
    "J.............J",
    "J......s......J",
    "J....ll.l.....J",
    "J.ssl...l.....J",
    "J.ss.....ss...J",
    "J..l.....ss...J",
    "J...l....l....J",
    "J...l....l....J",
    "J...l....l....J",
    "J....l..l.....J",
    "J....l..s.....J",
    "J....l.s.l....J",
    "J.....s..l....J",
    "J....l...l....J",
    "J....l.s..l...J",
    "J....l.s..l...J",
    "J....l.....l..J",
    "J....l.....ss.J",
    "J...ss.....ss.J",
    "J...ss........J",
    "J.............J",
    "J.............J",
    "J.........s.s.J",
    "J.sls......l..J",
    "J....l.....l..J",
    "J.....ll....s.J",
    "J.......slll..J",
    "J.......l.....J",
    "J.......l.....J",
    "J...s..ls.....J",
    "J....sl.......J",
    "J.............J",
    "J.............J",
    "J.............J",
    "J.............J",
    "J.............J",
    "J.............J",
    "JJJJJJJJJJJJJJJ",
)
SLABS = {"north": DIPPER, "south": ORION}


def _leant(rise):
    """The frame of a model turned about its z axis until its y axis looks east, `rise` degrees
    over the level: an upright face that looks east is the top of a box in it."""
    c, s = math.cos(math.radians(rise)), math.sin(math.radians(rise))
    return np.array([(s, c, 0.0), (-c, s, 0.0), (0.0, 0.0, 1.0)])


@functools.lru_cache(maxsize=None)
def _wall_frame():
    """The frame in which a face that looks east keeps as much of its tone as the stone behind it.
    The engine leaves a block's east face WALL_SHADE of its tone and an item's east face a half
    (machines/_relit), so a picture laid on the pier in a plain model is a sixth darker than the
    wall it is let into. The y axis of this frame is raised until the engine's two lamps give
    it what a wall gets: stone drawn in the wall's tones is then the wall's stone."""
    lo, hi = 0.0, 38.0
    for _ in range(60):
        rise = (lo + hi) / 2.0
        if RL.brightness(_leant(rise), EAST) < WALL_SHADE:
            lo = rise
        else:
            hi = rise
    return _leant((lo + hi) / 2.0)


def _upright(name, rows, tones, centre, lap=RL.LAP):
    """A picture that stands on the pier's face, drawn as the door sees it (its first column the
    southernmost), a pixel to the pixel: `centre` is its middle, in blocks from its entity. `lap`
    is how far it runs past its edges, to close the seam with the next one."""
    part = RL.Faces(name, frame=_wall_frame())
    part.face(centre, EAST, NORTH, len(rows[0]) / 16.0, len(rows) / 16.0, K.BRASS_D, lap=lap,
              faces={"u": Sprite(name, list(rows), tones)})
    return part


def _line():
    """The plumb line from its bob upwards as [(what, the height of its foot, its rows)]: the bob
    with the strip over it as far as the next whole block, then a LENGTH to a block up to the
    ceiling."""
    foot = CLOCK_TOP + BOB_CLEAR / 16.0
    first = math.ceil(foot + len(BOB) / 16.0 - 1e-9)
    lead = (first - foot) * 16.0 - len(BOB)
    if abs(lead - round(lead)) > 1e-6:
        raise ValueError(f"the clock's top, {CLOCK_TOP}, is not on a pixel: the bob cannot hang {BOB_CLEAR} over it")
    out = [("bob", foot, (LENGTH[0],) * int(round(lead)) + BOB)]
    return out + [("length", float(y), LENGTH) for y in range(first, H.CEIL)]


def _slab_z(side):
    """The middle of a slab along the face."""
    return AXIS + (-1.0 if side == "north" else 1.0) * (STRIP + len(SLABS[side][0])) / 32.0


@functools.lru_cache(maxsize=None)
def _pier():
    """The pieces on the pier's face as [(the Faces, where its entity stands)]. An entity takes the
    light of the cell it stands in, so each stands in the middle of a cell of the face: a length
    of the line in its own block, the bob in the block under the first length, a slab in the
    cell SLAB_CELL over its foot."""
    out, made = [], {}
    x, lift = FACE_X + 0.5, K.NUDGE - 0.5
    for what, foot, rows in _line():
        top = foot + len(rows) / 16.0
        at = (x, math.ceil(top - 1e-9) - 0.5, AXIS)
        if what not in made:
            made[what] = _upright(PIER + "plumb_" + what, rows, BRASS, (lift, (foot + top) / 2.0 - at[1], 0.0))
        out.append((made[what], at))
    for side, rows in SLABS.items():
        z, half = _slab_z(side), len(rows[0]) / 32.0
        if z - half <= FACE_Z[0] or z + half >= FACE_Z[1]:
            raise ValueError(f"the {side} slab does not lie inside the pier's face")
        at = (x, SLAB_FOOT + SLAB_CELL + 0.5, math.floor(z) + 0.5)
        # three blocks are as long as an element of a model may be: a slab has no lap, and no neighbour
        part = _upright(PIER + "slab_" + side, rows, STONE,
                        (lift, SLAB_FOOT + len(rows) / 32.0 - at[1], z - at[2]), lap=0.0)
        out.append((part, at))
    ok, line = lit([part for part, _at in out])
    if not ok:
        raise ValueError("the pier's face: " + line)
    return tuple(out)


def lit(parts=None):
    """Are the pictures on the pier lit as the wall is, filed surely, and where they belong?
    (ok, a line to print)."""
    parts = list({p.m.name: p for p in (parts if parts is not None else [part for part, _at in _pier()])}.values())
    tones = [v[0] for p in parts for v in p.lit]
    sure = min(v[1] for p in parts for v in p.lit)
    off = max(p.off() for p in parts)
    line = (f"{len(parts)} pictures on the pier: the engine leaves them {min(tones):.3f} to {max(tones):.3f} of "
            f"their tone (a wall that looks east: {WALL_SHADE}), the axis they are filed under wins by {sure:.2f} "
            f"(limit {RL.SURE}), the displays are off by {off:.1e} blocks at most")
    return all(abs(t - WALL_SHADE) < 1e-6 for t in tones) and sure >= RL.SURE and off < 1e-6, line


def models():
    out = dict(_models())
    out.update({part.m.name: part.m for part, _at in _pier()})
    return out


def dress(canvas, origin=(0, 0, 0), version=None):
    """Lay the floor's inlay and hang the pier's line and slabs; returns the display entities
    placed: one to a slab of the noon line, one to a block of the plumb line, one to a star slab."""
    version = version or H.VERSION
    n = 0
    for z, what in cells():
        n += K.put(canvas, _models()[f"{PREFIX}{version}_{what}"], (H.CX + 0.5, H.FEET + K.NUDGE, z + 0.5),
                   origin=origin)
    for part, at in _pier():
        canvas.add_entity(at[0] + origin[0], at[1] + origin[1], at[2] + origin[2], part.display())
        n += 1
    return n


# ---- a look at the drawing without the hall ---------------------------------------------------------------------
def sheet(path, zoom=10):
    """Both versions as they lie in the plan (west at the top, north at the right), `zoom` times
    enlarged on a flat grey for the stone, the line and the ring's two crossings drawn in."""
    import numpy as np
    from PIL import Image

    def rgb(colour):
        return [int(colour[k:k + 2], 16) for k in (1, 3, 5)]

    line, joint, stone = rgb(_C[0]), rgb(P.RAMPS["slate"][2]), (104, 108, 100)
    bands = []
    for version in H.VERSIONS:
        strip = np.zeros((TILE * len(cells()), TILE, 3), np.uint8)
        strip[:] = stone
        for n, (z, what) in enumerate(cells()):
            tile = strip[n * TILE:(n + 1) * TILE]
            tile[0, :] = tile[:, 0] = [v + 10 for v in stone]           # a slab's lit edges, to show the joints
            tile[:, JOINT[0]] = tile[:, JOINT[1]] = joint
            tile[:, JOINT[0] + 1:JOINT[1]] = line
            if what == "ring":
                tile[JOINT[0], :] = tile[JOINT[1], :] = joint
                tile[JOINT[0] + 1:JOINT[1], :] = line
            for j, row in enumerate(picture(what, north=z < H.CZ)):
                for i, ch in enumerate(row):
                    if ch != ".":
                        tile[j, i] = rgb(TONES[version][ch])
        bands.append(np.rot90(strip, k=-1))              # rows run west to east, columns south to north
    gap = np.zeros((TILE // 2, bands[0].shape[1], 3), np.uint8)
    whole = np.concatenate([bands[0], gap, bands[1]])
    Image.fromarray(whole.repeat(zoom, axis=0).repeat(zoom, axis=1), "RGB").save(path)
    return path


if __name__ == "__main__":
    import sys
    for z, what in cells():
        print(z, what)
        print("\n".join(picture(what, north=z < H.CZ)))
    for part, at in _pier():
        print(part.m.name, at)
    ok, line = lit()
    print(line)
    if len(sys.argv) > 1:
        print(sheet(sys.argv[1]))
    raise SystemExit(0 if ok else 1)
