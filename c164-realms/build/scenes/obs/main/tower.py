"""main/tower -- the clock tower that rises from the north end pavilion (plan/ART-PLAN.md 5.3,
plan/parts/main.md 6.2, card plan/packages/main/tower.md).

The pavilion walls (y 0..17) and their parapet are main/facade.py (c206); the pavilion's flat roof
deck at y 17 is c224. This package is everything above the roof: the stone shaft with its quoins,
string courses and four clock faces, the louvred belfry, the spire (two versions to choose from),
and the time-ball mast with its anemometer, lightning rod and the anchor for the radio-mast antenna.
Materials and mouldings follow the main order (ASHLAR_FINE walls, ASHLAR_ROUGH quoins/base, the
cornice a stair turned to the wall with an OLD_COPPER_CUT gutter on top), so the tower reads as one
family with the building below. The shaft stands on the skeleton footprint CLOCK_SHAFT_X/Z and the
heights CLOCK_SHAFT_TOP / CLOCK_TOP / CLOCK_BALL_MAST.

Pure occupancy-table blocks (build returns 0): the time ball, the anemometer cups and the clock
hands are display entities of the machines line (A5); here they are placeholders and anchor cells,
so the silhouette the arrival view (V1) and the up-view (V5) are about already reads. The dark glass
of the dial is a placeholder for the lit clock face the materials line paints.

ORDER 50 covers the white-model tower in massing.py (ORDER 10); on delivery those two lines of
massing.py go (A0 #19280 / c206 #19792: the real shell deletes its own segment).

    python -m scenes.obs.main.tower            # text plan, elevation and sections of both versions
"""
import math
import sys

from artkit.blocks import st
from artkit.canvas import Canvas

from ..common import blocks as B
from ..common import skeleton as S
from . import _order as O

# footprint (skeleton, LOCKED): the 7 x 7 shaft, its east face flush with the pavilion wall at x 16
X0, X1 = S.CLOCK_SHAFT_X             # 10 .. 16
Z0, Z1 = S.CLOCK_SHAFT_Z            # -33 .. -27
CX = (X0 + X1) // 2                 # 13, the central column
CZ = (Z0 + Z1) // 2                 # -30
BODY = O.box(X0, Z0, X1, Z1)        # the shaft columns

# heights
FOOT = S.ROOF_STAND                 # 18, the shaft stands on the pavilion deck
BASE_TOP = 20                       # the rusticated base
STRING = 23                         # a string course breaks the shaft in two
DIAL_Y = (25, 29)                   # the clock faces
SHAFT_TOP = S.CLOCK_SHAFT_TOP       # 31, the cornice that caps the stone shaft
BELFRY = (32, 36)                   # the louvred bell chamber
BELFRY_TOP = 37                     # its cornice
SPIRE = (38, S.CLOCK_TOP)           # 38 .. 41, the two-version top
MAST_TOP = S.CLOCK_BALL_MAST        # 52

# materials: the main order, so the tower is of a piece with the building below
WALL = B.ASHLAR_FINE
QUOIN = B.ASHLAR_ROUGH              # rusticated corner stones and base
PANEL = B.ASHLAR_PANEL
EMBLEM = B.ASHLAR_EMBLEM           # keystones and the cut corners of the dial frame
GUTTER = B.OLD_COPPER_CUT
DIAL = B.WINDOW_LIT                # placeholder lit clock face (A1 paints it, A5 hangs the hands)
LOUVRE = B.IRON_HATCH
BARS = B.IRON_BARS
GRATE = B.IRON_GRATE
IRON = B.IRON_RIVETED
ROD = B.IRON_ROD
DOME = B.VERDIGRIS_CUT
DOME_RIB = B.VERDIGRIS
DOME_STREAK = B.VERDIGRIS_STREAK
DOME_CAP = B.VERDIGRIS_CAST
MAST = B.BRASS_COLUMN
BALL = B.BRASS_PLATE              # placeholder time ball (A5 makes the real ball that drops)

FACES = ("north", "south", "east", "west")
OUT = {"north": "north", "south": "south", "east": "east", "west": "west"}


# --- small builders ---------------------------------------------------------------------------------
def _set(c, o, x, y, z, state):
    c.set(o[0] + x, o[1] + y, o[2] + z, state)


def _ring(x0, z0, x1, z1):
    """The perimeter columns of a rectangle."""
    out = set()
    for x in range(x0, x1 + 1):
        out.add((x, z0))
        out.add((x, z1))
    for z in range(z0, z1 + 1):
        out.add((x0, z))
        out.add((x1, z))
    return out


def _walls(c, o, x0, z0, x1, z1, y0, y1, fam, quoin=None):
    """One-block-thick perimeter walls; the four corner columns in `quoin` if given."""
    corners = {(x0, z0), (x1, z0), (x0, z1), (x1, z1)}
    for x, z in _ring(x0, z0, x1, z1):
        block = (quoin or fam).block if (x, z) in corners and quoin else fam.block
        for y in range(y0, y1 + 1):
            _set(c, o, x, y, z, block)


def _course(c, o, body, y, fam, half="top", gutter=None):
    """A string course / cornice: the wall row, with a stair turned to the wall hung round it
    (the main order's moulding, O.mould), and a gutter slab on top when asked."""
    plan = O.Plan(body)
    s = O.Laying(c, plan, o, None)
    for x, z in body:
        _set(c, o, x, y, z, fam.block)
    top = s.mould(body, y, fam.stairs, half)
    if gutter is not None:
        for x, z in top:
            _set(c, o, x, y + 1, z, st(gutter.slab, type="bottom"))


def _face_mid(face, n=5):
    """The middle n columns of a face, as (along, fixed) cells in scene coordinates."""
    if face in ("north", "south"):
        z = Z0 if face == "north" else Z1
        lo = CX - n // 2
        return [(x, z) for x in range(lo, lo + n)]
    x = X0 if face == "west" else X1
    lo = CZ - n // 2
    return [(x, z) for z in range(lo, lo + n)]


# --- the stone shaft and the clock faces ------------------------------------------------------------
def _shaft(c, o):
    # rusticated base, capped with a projecting weather course
    _walls(c, o, X0, Z0, X1, Z1, FOOT, BASE_TOP, QUOIN)
    _course(c, o, BODY, BASE_TOP, QUOIN, half="top")
    # the dressed-stone body with rusticated quoins
    _walls(c, o, X0, Z0, X1, Z1, BASE_TOP + 1, SHAFT_TOP - 1, WALL, quoin=QUOIN)
    _course(c, o, BODY, STRING, WALL, half="top")
    _clock_faces(c, o)
    # the shaft cornice with its copper gutter (CLOCK_SHAFT_TOP)
    _course(c, o, BODY, SHAFT_TOP, WALL, half="top", gutter=GUTTER)


def _clock_faces(c, o):
    """A round lit dial in a stone frame on each of the four faces, centred in DIAL_Y, with an
    emblem keystone above it; the five-wide face keeps a stone jamb either side."""
    y0, y1 = DIAL_Y
    cy = (y0 + y1) / 2.0
    for face in FACES:
        cells = _face_mid(face, 5)                       # five columns across the face
        along = [a for a, _ in cells] if face in ("north", "south") else [b for _, b in cells]
        mid_a = sum(along) / float(len(along))
        for (x, z), a in zip(cells, along):
            for y in range(y0, y1 + 1):
                r = math.hypot(a - mid_a, y - cy)
                if r <= 2.4:
                    _set(c, o, x, y, z, DIAL.block)      # the glowing dial
                elif r <= 2.9:
                    _set(c, o, x, y, z, EMBLEM)          # the cut corners of the frame
            if a == round(mid_a):
                _set(c, o, x, y1 + 1, z, EMBLEM)         # keystone above the dial


# --- the louvred belfry -----------------------------------------------------------------------------
def _belfry(c, o):
    y0, y1 = BELFRY
    # stone corner piers
    for x, z in ((X0, Z0), (X1, Z0), (X0, Z1), (X1, Z1)):
        for y in range(y0, y1 + 1):
            _set(c, o, x, y, z, QUOIN.block)
    # louvred openings between the piers, on every face
    for face in FACES:
        out = OUT[face]
        cells = _face_mid(face, 5)
        for x, z in cells:
            for y in range(y0, y1 + 1):
                _set(c, o, x, y, z, st(LOUVRE, facing=out, half="bottom", open="false"))
    _course(c, o, BODY, BELFRY_TOP, WALL, half="top", gutter=GUTTER)
    _antenna_anchor(c, o)


def _ridge_door(c, o):
    """A door opening in the south base of the shaft (z = Z1), where c224's ridge walkway from the
    wings and the small dome reaches the tower (A0 #20319). The leaf is props/ironwork; here the
    opening only."""
    for y in range(FOOT, FOOT + 2):
        c.clear(o[0] + CX, o[1] + y, o[2] + Z1)


def _antenna_anchor(c, o):
    """An iron bracket on the north-east corner of the belfry, reaching out towards the radio mast
    (skeleton RADIO_MAST foot (23, -40), north-east of the tower); the antenna line itself is the
    machines line's (c229)."""
    y = BELFRY[1] - 1
    _set(c, o, X1 + 1, y, Z0, st(ROD, facing="up"))
    _set(c, o, X1 + 1, y + 1, Z0 - 1, BARS)
    _set(c, o, X1, y + 1, Z0 - 1, BARS)


# --- the spire: two versions ------------------------------------------------------------------------
def _spire_a(c, o):
    """Verdigris cupola: a short drum, a copper half-dome on it with raised ribs and dark runs, a
    cast finial. The rounded top for the comet to crown (A0 #19544)."""
    y0, y1 = SPIRE
    dx0, dz0, dx1, dz1 = X0 + 1, Z0 + 1, X1 - 1, Z1 - 1          # steps in to 5 x 5
    drum = O.box(dx0, dz0, dx1, dz1)
    _walls(c, o, dx0, dz0, dx1, dz1, y0, y0, DOME)
    for y in range(y0 + 1, y1 + 1):
        t = (y - (y0 + 1)) / float(y1 - (y0 + 1)) if y1 > y0 + 1 else 1.0
        r = 2.6 * math.sqrt(max(0.0, 1.0 - t * t))
        for x in range(dx0, dx1 + 1):
            for z in range(dz0, dz1 + 1):
                if math.hypot(x - CX, z - CZ) <= r + 0.001:
                    on_rib = (x == CX or z == CZ)
                    _set(c, o, x, y, z, (DOME_RIB if on_rib else DOME.block) if r >= 1.0 else DOME_CAP)
    _set(c, o, CX, y1, CZ, DOME_CAP)                              # the finial under the mast
    # a dark run below each rib (two oxidations mixed), on the drum
    for x, z in ((CX, dz0), (CX, dz1), (dx0, CZ), (dx1, CZ)):
        _set(c, o, x, y0, z, DOME_STREAK.block)


def _spire_b(c, o):
    """Iron lookout platform: a riveted-and-grate deck on the belfry, a railing, four corner posts
    and an open frame of struts gathering to the mast foot. The electric-age, exposed-iron reading."""
    y0, y1 = SPIRE
    dx0, dz0, dx1, dz1 = X0 + 1, Z0 + 1, X1 - 1, Z1 - 1          # 5 x 5 platform
    for x in range(dx0, dx1 + 1):
        for z in range(dz0, dz1 + 1):
            _set(c, o, x, y0, z, GRATE)                          # the walkway deck
    # a riveted kerb and a bar railing round the deck edge
    for x, z in _ring(dx0, dz0, dx1, dz1):
        _set(c, o, x, y0, z, IRON.block)
        _set(c, o, x, y0 + 1, z, BARS)
    posts = ((dx0, dz0), (dx1, dz0), (dx0, dz1), (dx1, dz1))
    for x, z in posts:
        for y in range(y0, y1):
            _set(c, o, x, y, z, IRON.block)
    for x, z in posts:                                           # struts gather to the mast foot
        c.line((o[0] + x, o[1] + y1 - 1, o[2] + z), (o[0] + CX, o[1] + y1, o[2] + CZ), st(ROD, facing="up"))
    _set(c, o, CX, y1, CZ, IRON.block)                          # the mast seat


SPIRES = {"a": _spire_a, "b": _spire_b}


# --- the time-ball mast -----------------------------------------------------------------------------
def _ball(c, o, cy, r, block):
    for x in range(CX - 2, CX + 3):
        for z in range(CZ - 2, CZ + 3):
            for y in range(int(cy - r) - 1, int(cy + r) + 2):
                if math.hypot(x - CX, y - cy, z - CZ) <= r + 0.25:
                    _set(c, o, x, y, z, block)


def _mast(c, o):
    """The brass mast from the spire top, the time ball placeholder on it, the anemometer and the
    lightning rod that tips it at CLOCK_BALL_MAST -- the clean apex the comet sits above (V1/V5)."""
    top = SPIRE[1]
    for y in range(top + 1, MAST_TOP - 2):
        _set(c, o, CX, y, CZ, st(MAST, axis="y"))
    _ball(c, o, top + 5, 1.4, BALL.block)                        # placeholder brass ball (A5 drops it)
    ay = MAST_TOP - 2                                            # anemometer cups (placeholder, A5 spins)
    _set(c, o, CX, ay, CZ, st(MAST, axis="y"))
    for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        _set(c, o, CX + dx, ay, CZ + dz, st(ROD, facing=OUT[{(1, 0): "east", (-1, 0): "west", (0, 1): "south", (0, -1): "north"}[(dx, dz)]]))
    _set(c, o, CX, MAST_TOP - 1, CZ, st(ROD, facing="up"))       # lightning rod, tip at the mast top


# --- the package ------------------------------------------------------------------------------------
def build(canvas, origin=(0, 0, 0), version="a"):
    """Place the clock tower above the north pavilion. `version` picks the spire (a: verdigris
    cupola, b: iron platform); the shaft, clock faces, belfry and mast are shared."""
    _shaft(canvas, origin)
    _ridge_door(canvas, origin)
    _belfry(canvas, origin)
    SPIRES[version](canvas, origin)
    _mast(canvas, origin)
    return 0


def _drawings():
    for version in ("a", "b"):
        c = Canvas()
        build(c, version=version)
        print(f"\n=== clock tower, spire {version} ===")
        print("\nEAST ELEVATION (seen from the court; south on the left):\n")
        print(O.elevation(c, "east", (Z0 - 2, Z1 + 2), (FOOT, MAST_TOP), X1 + 4, X0 - 1))
        print("\nSECTION through the middle (z = %d; west on the left):\n" % CZ)
        print(O.section(c, "z", CZ, (X0 - 2, X1 + 2), (FOOT, MAST_TOP)))


if __name__ == "__main__":
    _drawings()
    sys.exit(0)
