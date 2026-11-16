"""interiors/_starhall_meridian -- what is let into the star hall's floor along its meridian.

A part of interiors/starhall (starhall.PARTS): starhall.dress() calls dress(canvas, origin, version)
last and starhall.models() takes models().

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
"""
import functools

from artkit import models as M
from artkit.pixelart import Sprite

from ..common import palette as P
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


def models():
    return dict(_models())


def dress(canvas, origin=(0, 0, 0), version=None):
    """Lay the inlay; returns the display entities placed, one to a slab of the line."""
    version = version or H.VERSION
    n = 0
    for z, what in cells():
        n += K.put(canvas, _models()[f"{PREFIX}{version}_{what}"], (H.CX + 0.5, H.FEET + K.NUDGE, z + 0.5),
                   origin=origin)
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
    if len(sys.argv) > 1:
        print(sheet(sys.argv[1]))
