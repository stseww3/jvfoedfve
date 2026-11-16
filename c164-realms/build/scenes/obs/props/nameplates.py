"""Props, the nameplates: one plate, the same on every machine of the station (plan/fine.md, section 4).

A machine carries an oblong of brass with round ends: the emblem in its left end, `No.` and two
figures after it, cut in and filled dark. The numbers are one table for the whole station -- NUMBERS
here, plan/parts/numbers.md for people; a machine that has none yet asks props for one. Its owner
hangs the plate in one line:

    from scenes.obs.props import nameplates
    n += nameplates.plate(canvas, 31, pos, facing="east", origin=origin)

pos is the middle of the plate, on the face it is fixed to; facing is the way that face looks. A
face that is no wall takes yaw= and turns= as artkit.models.display does (turns=(("x", -90),) lays
the plate on its back, reading from the south). The plate is WIDE by HIGH texels of a sixth of a
pixel, 0.54 by 0.18 of a block, and a capital on it 0.07 high: read from two or three blocks, drawn
within sixteen (M.SMALL), lit by the cell it is in.

The writing is the station's typeface (props/_kit.letters). The emblem is the standard figure made
small by its own rule (props/signs: the ring, the meridian upright through it and out of it at
both ends, the star a dot inside the ring on the upper right that touches neither).
"""
import functools

from artkit import models as M
from artkit.pixelart import Sprite

from ..common import palette as P
from . import _kit as K

PREFIX = "prop_nameplate_"
PX = 6.0                        # texels to a model pixel: 96 to the block
WIDE, HIGH = 52, 17             # the plate in texels
THICK = 0.25                    # model pixels the plate stands off the face it is fixed to
VIEW = M.SMALL
EMBLEM = 13                     # the emblem is this many texels across, a clear texel off the rim all round
RING = 5.0                      # its ring's radius, to the middle of the line
WORD = 19                       # the column the writing starts in: four clear texels after the emblem

FIELD = P.RAMPS["brass"][3]
FIELD_LIT, FIELD_LOW = P.RAMPS["brass"][4], P.RAMPS["brass"][2]     # the upper edge catches the light, the lower is in its own shade
RIM = P.RAMPS["brass"][1]
CUT = P.RAMPS["iron"][0]        # what is cut in is filled with black wax

# The station's machines by number (plan/parts/numbers.md says who has which and why; the two are
# kept alike). Tens: 0 the line and the station, 1 the power house, 2 its workshop, 3 water and
# hydraulics, 4 the time service, 5 the telescopes and the domes, 6 computing and recording,
# 7 wireless and signals, 8 the battery room, 9 spare.
NUMBERS = {
    1: "locomotive", 2: "carriage", 3: "station winch", 4: "water crane", 5: "turntable", 6: "coal stage hoist",
    11: "boiler", 12: "boiler", 13: "steam engine", 14: "dynamo", 15: "switchboard", 16: "feed pump",
    21: "line shaft", 22: "lathe", 23: "drill", 24: "grinder",
    31: "wind pump", 32: "hydraulic accumulator", 33: "goods lift", 34: "jib crane",
    41: "master clock", 42: "tower clock", 43: "time ball", 44: "telegraph", 45: "chronograph", 46: "station clock",
    51: "great refractor", 52: "driving clock", 53: "dome gear", 54: "shutter winch", 55: "transit circle",
    56: "astrograph", 57: "comet seeker",
    61: "difference engine", 62: "orrery", 63: "seismograph", 64: "barograph", 65: "sunshine recorder",
    66: "dispatch blower", 67: "wind recorder",
    71: "mast winch", 72: "transmitter", 73: "home signal",
    81: "battery board", 82: "battery",
}


def words(number):
    """What the plate of a machine says."""
    return f"No. {int(number):02d}"


def emblem(n=EMBLEM, radius=RING):
    """The emblem on n by n texels as (x, y) pairs, y running down: the ring `radius` about the
    middle texel, the meridian the middle column over the whole height (a texel out of the ring at
    either end), the star one texel 0.4 of the radius right of the middle and as far above it."""
    c = n // 2
    ring = {(x, y) for x in range(n) for y in range(n)
            if radius - 0.5 <= ((x - c) ** 2 + (y - c) ** 2) ** 0.5 < radius + 0.5}
    star = (c + int(round(0.4 * radius)), c - int(round(0.4 * radius)))
    near = {(star[0] + dx, star[1] + dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1)}
    if near & ring or any(x == c for x, _ in near):
        raise ValueError(f"an emblem of {n} texels has no room for its star")
    return ring | {(c, y) for y in range(n)} | {star}


def _inside(i, j):
    """The texel (i, j) is on the plate: an oblong whose ends are half circles."""
    r = HIGH / 2.0
    x, y = i + 0.5, j + 0.5
    x = min(max(x, r), WIDE - r)                # the nearest point of the line between the two ends' middles
    return (i + 0.5 - x) ** 2 + (y - r) ** 2 <= r * r


def picture(number):
    """The plate's face as rows of characters: '.' off the plate, r the rim, h, f, l the brass from
    the lit upper edge down, k what is cut in."""
    rows = []
    for j in range(HIGH):
        row = ""
        for i in range(WIDE):
            if not _inside(i, j):
                row += "."
            elif not all(0 <= a < WIDE and 0 <= b < HIGH and _inside(a, b)
                         for a, b in ((i - 1, j), (i + 1, j), (i, j - 1), (i, j + 1))):
                row += "r"
            else:
                row += "h" if j < 4 else "l" if j > HIGH - 5 else "f"
        rows.append(row)
    off = (HIGH - EMBLEM) // 2
    cells = [list(row) for row in rows]
    for x, y in emblem():
        if cells[off + y][off + x] not in "hfl":
            raise ValueError("the emblem does not stand clear of the plate's rim")
        cells[off + y][off + x] = "k"
    rows = K.inscribe(["".join(row) for row in cells], words(number), WORD, (HIGH - 7) // 2, ink="k")
    for j, row in enumerate(rows):
        for i, ch in enumerate(row):
            if ch == "k" and any(rows[b][a] in ".r" for a, b in ((i - 1, j), (i + 1, j), (i, j - 1), (i, j + 1))):
                raise ValueError(f"{words(number)!r} does not stand clear of the plate's rim")
    return rows


def _plate(number):
    """The plate No. `number`: a sheet THICK off the face it is fixed to, its picture on the side that
    looks out; the anchor is the middle of its back."""
    m = M.Model(f"{PREFIX}{int(number):02d}", px=PX)
    w, h = WIDE / PX, HIGH / PX
    face = Sprite(f"{PREFIX}{int(number):02d}", picture(number),
                  {"r": RIM, "h": FIELD_LIT, "f": FIELD, "l": FIELD_LOW, "k": CUT})
    m.box((-w / 2.0, -h / 2.0, 0.0), (w / 2.0, h / 2.0, THICK), K.BRASS, skip="newud", faces={"s": face})
    return m


@functools.lru_cache(maxsize=None)
def _models():
    return {f"{PREFIX}{number:02d}": _plate(number) for number in NUMBERS}


def models():
    return dict(_models())


SCALE = {f"{PREFIX}{number:02d}": 1.0 for number in NUMBERS}


def plate(canvas, number, pos, facing="south", origin=(0, 0, 0), yaw=None, **opts):
    """Fix the plate of machine No. `number` with its middle at pos, on a face that looks `facing`
    (or turned by yaw= and turns=). A number that is not in NUMBERS has not been given out: ask
    props (plan/parts/numbers.md). opts as for props/_kit.put. Returns 1."""
    if int(number) not in NUMBERS:
        raise KeyError(f"No. {number} is not in the station's table of machines (props/nameplates.NUMBERS, "
                       f"plan/parts/numbers.md): ask props for a number")
    opts.setdefault("view", VIEW)
    return K.put(canvas, _models()[f"{PREFIX}{int(number):02d}"], pos, mount="wall", facing=facing, yaw=yaw,
                 origin=origin, **opts)
