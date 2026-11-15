"""machines/mast -- the radio mast (plan/ART-PLAN.md 7.2, plan/parts/A5-machines.md 2.8, card
plan/packages/machines/radiomast.md).

The tallest upright of the skyline: an iron lattice mast on the stone foot north of the court
(site/mastbase), the top of its lamp 62 blocks over the pad. It is seen from far more than from
near: the arrival view V1 stands 65 blocks from it, V2 53, V11 95 and the bird's eye V12 about 132,
so what counts is that it is there at those distances, one unbroken dark line against the sky, and
reads as a lattice mast.

How it is made, from the seat up:

  foot    the four legs come straight down to the four corners of the iron seat, and each stands
          on a porcelain pot of its own: the whole mast is the radiator and is insulated from the
          ground. It is fed at one shoe (a copper lead to the lead-in post of site/mastbase), and
          a spark gap bridges the pot of the next leg. That is why the guys are broken by eggs of
          porcelain. Two belts and two bays of diagonals tie the legs over the shoes: the shaft
          goes on to the seat, square. It does not run to a point over one base insulator: V1
          sees nothing under y 3 and would see the lattice thin out to nothing on the terrace's
          edge, and a lattice that is thin at both ends is the jib of a crane.
  shaft   square and not tapered, the leg axes 2 blocks apart, a belt every 3 blocks, 16 bays of
          crossed diagonals with a plate at every joint and where the diagonals cross: y 8.5 to
          56.5. Four pieces of 12 blocks, shown four times their size (px = 4 keeps 16 texels to
          the block): 12 blocks are the 48 units a model may span.
  head    the legs gather to a pole that carries the lamp. No yard, no gallery, no arm: nothing
          crosses the upright.
  lamp    one small red lantern, lit steadily (A0 #36376: it does not blink, the comet is the one
          thing in the sky that may draw the eye). Its brightest tone is the signal ramp's second
          lightest, level with the orange windows: a warning lamp, not one more star. Its entity is
          tagged c164_signal and mach_mast_light_off is its dark twin, kept for the motion line.
          It throws no light: nothing stands near it to be lit, and a source up there would only
          pale the iron under it. Its glass lies in a frame of its own, turned so that the game
          gives every one of its faces the same light from wherever it is seen (see LAMP_FRAME).
  guys    the four anchors of site/mastbase stand on the diagonals, 4 blocks out, so the guys go
          four ways (the card said three), one from each anchor to the leg that looks at it, at
          belt 5 (y 23.5). The anchors are close to the foot: a guy to the top would run within 5
          degrees of its leg and read from far as the mast seen double, so they stop low, where
          the four of them make a tent that stands clear of the shaft. At the anchor a clamp on
          the eye bolt, a bottle screw and an egg; at the leg a clamp on the corner of the joint;
          one more egg a third of the way down from there; the cable between is drawn out, two
          texels thick and of dark iron, so that it holds as a line against the sky. All of it
          keeps north of z -35: nothing crosses the court or the sight lines of V1 and V2 to the
          main building. White porcelain is kept for the foot and the guys, low down: the highest
          white piece is the guys' upper egg, at y 16.6. Aloft it would be brighter than the
          night sky and read as a star beside the comet.
  aerial  the mast itself. It hangs no wire: one from its head down to the clock tower was drawn
          and dropped. The board's wide views tilt the mast, and a thin line that hangs straight
          down from the tip of a tilted lattice is the hoist rope of a crane's jib; a cage of
          thin wires in its place breaks up into dashes at those distances.

All pieces are given one brightness, the open sky's: each would otherwise take the light of the
cell its anchor is in, and a lamp near the foot would show as a step where two pieces meet.

Two ways to build the foot and the shaft, to be compared on pictures from near and from far (the
test scenes obs_mach_radiomast and obs_mach_radiomast_b show them from the same cameras):

  a   all of it display models: legs 5 texels square, belts and diagonals 3. Inside each model leg
      stands a column of the thin iron pipe block (B.IRON_PIPE), hidden by it. The server sends a
      display entity to a player within 160 blocks at the most and never farther than its view
      distance; all cameras of the board are nearer than that, but should the models ever fall
      away, four thin legs still stand. The columns are also all of the mast that a player
      cannot walk through.
  b   legs and belts are that pipe block, 3 texels thick and partly open; the models carry the
      diagonals, the plates and the pots only.

a is the default: legs, belts and diagonals are drawn one way and take the same light, and from V1
a leg of 5 texels is about two pixels wide in a 720p picture, the pipe block little more than one.

What this module reads from its neighbour site.mastbase, with the same numbers as a fallback while
it is not in the tree: TOP, GUY_ANCHORS and ANTENNA_HOOK. What the clocks' test scenes read from
this one: build, models, BASE_Y, GUY_ANCHORS, LEAD_POST, and TOWER_HOOK, which is kept for them
alone (see there).
"""
import functools
import math

from artkit import models as M
from artkit.blocks import st

from ..common import blocks as B
from ..common import palette as P
from ..common import skeleton as S

try:
    from ..site import mastbase as _base        # the stone foot, the guy anchors, the lead-in post
except ImportError:
    _base = None

PREFIX = "mach_mast_"
VERSIONS = ("a", "b")
DEFAULT = "a"

# ---- where it stands -------------------------------------------------------------------------------
FX, FZ = S.RADIO_MAST["foot"]                   # (23, -40): the cell the mast's axis stands in
G = float(S.MAST_PAD["feet"])                   # 0.0: where feet stand on the pad
AX, AZ = FX + 0.5, FZ + 0.5                     # the axis, (23.5, -39.5): the middle of the seat
TIP_Y = G + float(S.RADIO_MAST["height"])       # 62.0: the top of the lamp

BASE_Y = float(getattr(_base, "TOP", G + 2.0))  # 2.0: the top face of the seat
GUY_ANCHORS = [tuple(float(v) for v in p) for p in getattr(
    _base, "GUY_ANCHORS", [(FX + sx * 4 + 0.5, G + 2.0, FZ + sz * 4 + 0.5) for sx in (-1, 1) for sz in (-1, 1)])]
LEAD_POST = tuple(float(v) for v in getattr(_base, "ANTENNA_HOOK", (FX - 1.5, G + 4.0, FZ + 2.5)))
# Where the wire to the clock tower hooked on to it, two blocks north of the tower's north-east
# corner under the cornice at y 31. The mast hangs no wire any more and does not use the point; the
# name stays until the clocks' test scene has stopped reading it.
TOWER_HOOK = (S.CLOCK_SHAFT_X[1] + 0.5, 30.5, S.CLOCK_SHAFT_Z[0] - 2.0)         # (16.5, 30.5, -35.0)

# ---- the lattice -----------------------------------------------------------------------------------
SCALE = 4                       # the lattice pieces are shown this large; px = SCALE keeps 16 texels to the block
U = SCALE / 16.0                # one unit of those models in blocks: 0.25
LEG = 1.0                       # the leg axes stand this far from the mast's axis in x and in z
BAY = 3.0                       # a belt every three blocks
BAYS = 16
SEG_BAYS = 4                    # bays to a piece: 12 blocks, the 48 units a model may span
SEGS = BAYS // SEG_BAYS
KNEE_Y = math.floor(BASE_Y) + 6.5       # 8.5: the lowest belt of the shaft's pieces; the foot carries the shaft on below
TOP_Y = KNEE_Y + BAYS * BAY     # 56.5: the top belt
GUY_BELT = 5                    # the belt the guys leave from: y 23.5
GUY_OUT = 0.25                  # ... this far outside the leg's axis in x and in z: just off the joint's corner

# sizes of the members in units of the lattice models (a unit is 4 texels)
LEG_W = 1.25                    # a leg, 5 texels square
BELT = 0.75                     # a belt, 3 texels square
BRACE, BRACE_T = 0.75, 0.5      # a diagonal: 3 texels wide in the face, 2 thick
PLATE_H = 1.75                  # a joint plate: 7 texels high, 1 thick, half a texel proud of the leg
PLATE_REACH = {"a": 2.25, "b": 2.75}    # ... and this long from the leg's outer edge inwards; in b it reaches
#                                         the end of the belt block, which stops half a block short of the leg
PLATE_RIVET = 0.5               # its two rivets sit on the leg's middle line, this far over and under the belt's
KNOT, KNOT_T = 1.0, 0.25        # the plate where two diagonals cross: 4 texels square, 1 thick
RIVET = 0.25                    # ... and the head of the rivet through it: 1 texel
COLLAR = 0.875                  # half the width of the collars that close a leg's two ends
LEG_U, BAY_U = LEG / U, BAY / U         # 4 and 12 units
NODE = BELT / 2.0               # a piece starts this far under its lowest belt's middle: the belt lies wholly in it
SEG_Y = KNEE_Y - NODE * U       # 8.40625: the bottom of the lowest piece
HEAD_Y = SEG_Y + BAYS * BAY     # 56.40625: where the head takes over
FOOT_BELTS = (math.floor(BASE_Y) + 1.5, KNEE_Y - BAY)   # 3.5 and 5.5: the two belts of the foot, under the knee's
FOOT_POT = (0.5, 2.5, 3.0, 4.5)         # under each leg, in units over the seat: a base plate up to here, the
#                                         porcelain, its iron cap, the shoe that takes the leg
FOOT_LUG = (5.0, 3.5)           # the terminal of the feed lead on a shoe: distance from the axis in x and z, height
GAP_OUT, GAP_Y = 1.5, 2.0       # the spark gap: this far outside its leg's axis in x and z, its middle this high
GAP_BALL, GAP_AIR = 0.5, 0.5    # its two balls are 4 texels across and stand 2 texels apart
LAMP_H = 10                     # texels: the lamp from the foot of its holder on the pole to its top
LAMP_Y = TIP_Y - LAMP_H / 16.0  # 61.375
LAMP_HOLDER = 1.5               # texels of that which are the iron holder: a neck and a plate
GLASS_Y = LAMP_Y + LAMP_HOLDER / 16.0   # 61.46875: the foot of the glass

LEG_CELLS = [(FX + sx, FZ + sz) for sx in (-1, 1) for sz in (-1, 1)]
BELT_CELLS = [(FX, FZ - 1, "x"), (FX, FZ + 1, "x"), (FX - 1, FZ, "z"), (FX + 1, FZ, "z")]

# ---- guys ------------------------------------------------------------------------------------------
STAY_CABLE = 13.0               # texels from the eye bolt to where the cable leaves the bottle screw's jaw
STAY_EGG = 19.0                 # ... and to the guy's lower egg
EGG_LEN = 7.0
EGG_DROP = 7.0                  # blocks from the leg down the guy to its upper egg: well clear of the shaft
GUY_CLAMP = 0.5                 # units of the guy's model, which is drawn out seven times: 3.5 texels of clamp

# ---- the lamp --------------------------------------------------------------------------------------
# How the game lights a face of an item model: by the one of the six axes its normal lies nearest to
# (in the model, each box turned as it is drawn), that axis turned with the display entity, under two
# fixed lamps that stand high in the north-east and in the south-west. A face filed under "up" is
# full bright, north and south 0.74, east and west 0.5, down 0.4. light_emission raises the light a
# face takes to full, and this shading still goes over it (VertexConsumer.putBakedQuad of 26.3 takes
# BakedQuad.direction(); the model's shade_direction_override is read for blocks only). A lit globe
# drawn upright therefore shows V1, which looks at it from due east and 44 degrees below, the faces
# filed under east and down: half its red and less.
#
# So the glass is drawn in a frame that stands on its corner. The entity is turned (LAMP_FRAME) until
# the model's +x, +y and +z all point 55 degrees off the zenith, 120 degrees apart, at the bearings
# LAMP_BEARINGS, where each takes 0.96 of full light; the glass is drawn turned back, so it stands
# upright; and it has no face that would be filed under one of the three axes that point down: only
# faces that look up, and upright walls within LAMP_SPLAY of one of the three bearings. Two walls to
# a bearing make an all but regular hexagon. The lamp is then one red from every side and from below.
LAMP_FRAME = (("z", 45.0), ("x", -math.degrees(math.atan(math.sqrt(0.5)))))
LAMP_UPRIGHT = tuple((axis, -deg) for axis, deg in reversed(LAMP_FRAME))        # the frame's turn undone
LAMP_BEARINGS = (60.0, 180.0, 300.0)    # where +x, +z and +y point then, degrees from north by east
LAMP_SPLAY = 27.0               # at 30 a wall would lie as near to an axis that points down as to its own
# the glass in courses, foot to top: (from, to, how far its walls stand from the axis), in texels
LAMP_COURSES = ((0.0, 1.0, 4.0), (1.0, 5.5, 4.0), (5.5, 7.0, 3.0), (7.0, LAMP_H - LAMP_HOLDER, 1.75))

VIEW = 8.0                      # view range: 512 blocks at the client's normal setting, 256 at its lowest;
#                                 past the 160 the server sends, so the client never drops a piece first
BRIGHT = (15, 0)                # (sky, block): what a piece takes under the open sky with no lamp near

IRON = P.mat("iron")                            # fittings
IRON_D = P.mat("iron_dark")                     # the lattice: legs, belts, plates
IRON_F = P.mat("iron_flat")                     # the diagonals: the lattice's tone without speckle or edge
PORCELAIN = P.mat("porcelain")                  # white: the four insulators the legs stand on, the guys' eggs
BRASS = P.mat("brass")


def _flat(name, step):
    """One flat tone of a ramp: cables, which are drawn out, and glass, whose shading is painted."""
    return P.mat(name, kind="flat", base=step, bevel=0)


CABLE = _flat("iron", 1)                        # the guys: the iron ramp's second step. On a face that looks
#                                                 down or away from the game's two lamps the darkest step
#                                                 comes out all but black
LEAD = _flat("old_copper", 2)                   # the feed lead at the foot, seen from near only: a darker
#                                                 step reads as a strip of wood at night
STUD = _flat("iron", 4)                         # rivet heads
RED = [_flat("signal_glow", i) for i in range(len(P.RAMPS["signal"]))]

# members of one kind share one picture: the sheet of a piece stays small
LEG_SEED, BELT_SEED, BRACE_SEED, PLATE_SEED, STRUT_SEED, KNOT_SEED, STUD_SEED = 1001, 1002, 1003, 1005, 1006, 1007, 1008


# ---- geometry --------------------------------------------------------------------------------------
def _corner(p):
    """The corner of the square shaft that looks at the point p, as signs in x and z."""
    return (1 if p[0] >= AX else -1), (1 if p[2] >= AZ else -1)


# The foot is drawn with its one-sided parts (the terminal, the spark gap) for the corner -x, +z;
# this turns that corner to another.
_CORNER_YAW = {(-1, 1): 0.0, (-1, -1): 90.0, (1, -1): 180.0, (1, 1): 270.0}


def _along(a, b, blocks):
    """The point `blocks` from a on the way to b."""
    d = math.dist(a, b)
    return tuple(a[i] + (b[i] - a[i]) * blocks / d for i in range(3))


def guy_end(anchor):
    """Where the guy of an anchor meets the mast: at the joint of belt GUY_BELT, on the outer corner
    of the leg that looks at the anchor. The guy's clamp sits there against the two plates of the
    joint, and the cable comes down outside the leg, not through it."""
    sx, sz = _corner(anchor)
    return AX + sx * (LEG + GUY_OUT), KNEE_Y + GUY_BELT * BAY, AZ + sz * (LEG + GUY_OUT)


def lead_lug():
    """The terminal on a shoe of the foot, where the lead to the lead-in post starts."""
    sx, sz = _corner(LEAD_POST)
    return AX + sx * FOOT_LUG[0] * U, BASE_Y + FOOT_LUG[1] * U, AZ + sz * FOOT_LUG[0] * U


# ---- the lattice pieces ----------------------------------------------------------------------------
def _legs(m, y0, y1):
    for sx in (-1, 1):
        for sz in (-1, 1):
            x, z = sx * LEG_U, sz * LEG_U
            m.box((x - LEG_W / 2.0, y0, z - LEG_W / 2.0), (x + LEG_W / 2.0, y1, z + LEG_W / 2.0), IRON_D,
                  skip="ud", grain="y", seed=LEG_SEED)


def _belts(m, y, out=LEG_U):
    """A square belt at height y between four legs whose axes stand `out` from the middle."""
    h = BELT / 2.0
    for s in (-1, 1):
        m.box((-out, y - h, s * out - h), (out, y + h, s * out + h), IRON_D, skip="ew", grain="x", seed=BELT_SEED)
        m.box((s * out - h, y - h, -out), (s * out + h, y + h, out), IRON_D, skip="ns", grain="z", seed=BELT_SEED)


def _braces(m, y0, y1, out0=LEG_U, out1=LEG_U, flip=1):
    """The two diagonals of a bay on each of the four faces, from the joints at y0 (the leg axes
    `out0` from the middle) to those at y1 (`out1`). Each is a flat bar of one tone; one lies just
    outside the plane of the leg axes and one just inside, so that where they cross no two faces fall
    together. flip = -1 swaps which of the two is the outer one."""
    for s in (-1, 1):
        for d in (-1, 1):
            e = d * flip * BRACE_T / 2.0
            seed = BRACE_SEED + (1 if d > 0 else 0)
            m.beam((-d * out0, y0, s * (out0 + e)), (d * out1, y1, s * (out1 + e)), BRACE_T, BRACE, IRON_F, seed=seed)
            m.beam((s * (out0 + e), y0, -d * out0), (s * (out1 + e), y1, d * out1), BRACE_T, BRACE, IRON_F, seed=seed)


def _knots(m, y0, y1, out0=LEG_U, out1=LEG_U):
    """Where the two diagonals of a bay cross, on each of the four faces: a small plate on the
    outside of both bars and the head of the rivet that goes through the three."""
    t = out0 / (out0 + out1)
    y, out = y0 + t * (y1 - y0), out0 + t * (out1 - out0)
    a = out + BRACE_T
    b, c = a + KNOT_T, a + KNOT_T + RIVET
    k, r = KNOT / 2.0, RIVET / 2.0
    for s in (-1, 1):
        m.box((-k, y - k, s * a), (k, y + k, s * b), IRON_D, grain="y", seed=KNOT_SEED)
        m.box((-r, y - r, s * b), (r, y + r, s * c), STUD, seed=STUD_SEED)
        m.box((s * a, y - k, -k), (s * b, y + k, k), IRON_D, grain="y", seed=KNOT_SEED)
        m.box((s * b, y - r, -r), (s * c, y + r, r), STUD, seed=STUD_SEED)


def _plates(m, node, reach, lo=None, hi=None):
    """The plates that tie a belt and the diagonals to the legs at one joint: on the outside of every
    face, at both its legs. Kept between lo and hi, the ends of the piece: what is cut off there is
    drawn by the piece below or above."""
    y0 = node - PLATE_H / 2.0 if lo is None else max(lo, node - PLATE_H / 2.0)
    y1 = node + PLATE_H / 2.0 if hi is None else min(hi, node + PLATE_H / 2.0)
    if y1 - y0 < 0.2:
        return
    a, b = LEG_U + LEG_W / 2.0 - reach, LEG_U + LEG_W / 2.0
    p0, p1 = LEG_U + 0.5, LEG_U + 0.75
    for s in (-1, 1):
        for t in (-1, 1):
            m.box((t * a, y0, s * p0), (t * b, y1, s * p1), IRON_D, grain="x", seed=PLATE_SEED)
            m.box((s * p0, y0, t * a), (s * p1, y1, t * b), IRON_D, grain="z", seed=PLATE_SEED)
    # two rivets through each plate into its leg, one over the belt and one under it; where a piece
    # ends between the two, each piece draws the one on its side
    r, p2 = RIVET / 2.0, p1 + RIVET
    for y in (node - PLATE_RIVET, node + PLATE_RIVET):
        if (lo is not None and y - r < lo) or (hi is not None and y + r > hi):
            continue
        for s in (-1, 1):
            for t in (-1, 1):
                m.box((t * LEG_U - r, y - r, s * p1), (t * LEG_U + r, y + r, s * p2), STUD, seed=STUD_SEED)
                m.box((s * p1, y - r, t * LEG_U - r), (s * p2, y + r, t * LEG_U + r), STUD, seed=STUD_SEED)


def _collars(m, y0, y1):
    """A short sleeve round each leg: it closes the leg's end, and under it the model legs, the pipe
    blocks and the foot's or the head's own members meet out of sight."""
    for sx in (-1, 1):
        for sz in (-1, 1):
            x, z = sx * LEG_U, sz * LEG_U
            m.box((x - COLLAR, y0, z - COLLAR), (x + COLLAR, y1, z + COLLAR), IRON_D)


def _lattice(name, legs, belts, reach):
    """One piece of the shaft: SEG_BAYS bays. It starts NODE under its lowest belt's middle and
    carries that belt; the belt at its top is the next piece's, or the head's. With legs and belts
    it is version a's piece; without them it is the web that version b hangs between its blocks."""
    m = M.Model(name, px=float(SCALE))
    top = SEG_BAYS * BAY_U
    if legs:
        _legs(m, 0.0, top)
    for k in range(SEG_BAYS):
        node = NODE + k * BAY_U
        if belts:
            _belts(m, node)
        _braces(m, node, node + BAY_U, flip=1 if k % 2 == 0 else -1)
        _knots(m, node, node + BAY_U)
    for k in range(SEG_BAYS + 1):
        _plates(m, NODE + k * BAY_U, reach, 0.0, top)
    return m


def _foot(name, legs, belts, reach):
    """The foot, from the seat to the lowest piece of the shaft. The four legs come straight down to
    the seat's four corners and each stands on an insulator of its own: a base plate, a porcelain pot
    with two sheds, an iron cap and the shoe that takes the leg. Over the shoes the shaft goes on as
    above: a belt at each of FOOT_BELTS, crossed diagonals from belt to belt and to the knee, plates
    at the joints. Anchor: the middle of the seat's top. With legs and belts it is version a's foot;
    without them it is the web that version b hangs between its blocks, and the pots under them."""
    m = M.Model(name, px=float(SCALE))
    knee = (KNEE_Y - BASE_Y) / U                                    # 26 units up: the lowest belt of the piece above
    top = knee - NODE                                               # ... which starts here
    plate, pot, cap, shoe = FOOT_POT
    for sx in (-1, 1):
        for sz in (-1, 1):
            x, z = sx * LEG_U, sz * LEG_U
            m.box((x - 1.25, 0.0, z - 1.25), (x + 1.25, plate, z + 1.25), IRON_D)
            m.tube("y", (x, z), plate, pot, 0.75, PORCELAIN)
            for y in (plate + 0.25, plate + 1.25):
                m.tube("y", (x, z), y, y + 0.5, 1.25, PORCELAIN)
            m.tube("y", (x, z), pot, cap, 1.0, IRON)
    _collars(m, cap, shoe)
    if legs:
        _legs(m, shoe - 0.5, top)
    nodes = [(y - BASE_Y) / U for y in FOOT_BELTS] + [knee]
    for i, node in enumerate(nodes[:-1]):
        if belts:
            _belts(m, node)
        _plates(m, node, reach)
        # the piece above starts with flip = 1: the bays go on taking turns downwards
        _braces(m, node, nodes[i + 1], flip=1 if (len(nodes) - i) % 2 else -1)
        _knots(m, node, nodes[i + 1])
    _plates(m, knee, reach, None, top)          # the lower part of the knee's plates: the piece above cuts them off
    # the terminal of the lead to the lead-in post, on the outer corner of the shoe -x, +z
    lx, ly = FOOT_LUG
    m.box((-lx - 0.5, ly - 0.5, lx - 0.5), (-lx + 0.5, ly + 0.5, lx + 0.5), BRASS)
    # the spark gap across the insulator of the next leg (+x, +z; both corners look at the court): two
    # brass balls one over the other, two texels of air between them, the lower one on a pin that
    # stands on the seat, the upper one on a horn that comes down from the shoe
    g = LEG_U + GAP_OUT
    low, high = GAP_Y - GAP_AIR / 2.0 - GAP_BALL, GAP_Y + GAP_AIR / 2.0 + GAP_BALL
    m.box((g - 0.25, 0.0, g - 0.25), (g + 0.25, 0.25, g + 0.25), IRON_D)
    m.rod((g, 0.25, g), (g, low - GAP_BALL + 0.1, g), 0.125, IRON_D, sides=4)
    m.rod((LEG_U + COLLAR - 0.1, shoe - 0.5, LEG_U + COLLAR - 0.1), (g, high + GAP_BALL - 0.1, g), 0.125, IRON_D, sides=4)
    for y in (low, high):
        m.ball((g, y, g), GAP_BALL, BRASS, sides=8, layers=4)
    return m


def _head():
    """The head, from the top belt to the foot of the lamp. Anchor: on the axis, NODE under the top
    belt's middle, where the uppermost piece of the shaft ends."""
    m = M.Model(PREFIX + "head", px=float(SCALE))
    _belts(m, NODE)
    _plates(m, NODE, PLATE_REACH["a"], 0.0, None)
    _collars(m, -1.75, 1.5)
    # four struts gather to the casting that carries the pole
    apex = 11.0
    for sx in (-1, 1):
        for sz in (-1, 1):
            m.rod((sx * LEG_U, 1.0, sz * LEG_U), (sx * 0.5, apex, sz * 0.5), 0.5, IRON_D, sides=4, seed=STRUT_SEED)
    m.box((-1.25, apex - 1.0, -1.25), (1.25, apex + 0.5, 1.25), IRON_D)
    top = (LAMP_Y - HEAD_Y) / U
    m.tube("y", (0.0, 0.0), apex + 0.5, top, 0.5, IRON_D)
    # the lamp's holder on the pole's top: a neck and the plate the glass stands on. It is drawn here
    # and not with the glass, which lies in a frame of its own (LAMP_FRAME) that would light the iron
    # in patches
    m.tube("y", (0.0, 0.0), top, top + 0.25, 0.625, IRON_D)
    m.tube("y", (0.0, 0.0), top + 0.25, top + LAMP_HOLDER / SCALE, 1.125, IRON)
    return m


def _glass(m, y0, y1, r, mat, emit, inner=None):
    """One course of the lamp's glass, from y0 to y1: six upright walls r from the axis, two to each
    bearing of the lamp's frame, each as far to its two sides as where it meets its neighbours. With
    `inner`, the course is closed on top from its walls in to that distance from the axis (0 closes
    it wholly; the course that stands on it covers the rest)."""
    near = r * math.tan(math.radians(LAMP_SPLAY))
    far = r * math.tan(math.radians(60.0 - LAMP_SPLAY))
    depth = r if inner is None else r - inner
    for bearing in LAMP_BEARINGS:
        for side in (-1, 1):
            # drawn as the wall that looks north, then swung round: a turn about y takes north to the west
            a, b = (-far, near) if side < 0 else (-near, far)
            with m.turned(("y", -(bearing + side * LAMP_SPLAY))):
                m.box((a, y0, -r), (b, y1, depth - r), mat, skip="sewd" if inner is not None else "sewud", emit=emit)


def _light(name, lit):
    """The lamp's glass: a red lantern half a block across with a stepped crown, six sides, all but
    regular. Anchor: the middle of its foot, on the holder's plate; it is to be shown turned by
    LAMP_FRAME. Lit, its body is the signal ramp's second lightest tone, its foot and its crown the
    third; the lightest, an orange pink as bright as a golden window, is not used."""
    m = M.Model(name)
    end, belly = (RED[1], RED[2]) if lit else (RED[0], RED[1])
    emit = 15 if lit else 0
    last = len(LAMP_COURSES) - 1
    with m.turned(*LAMP_UPRIGHT):
        for i, (y0, y1, r) in enumerate(LAMP_COURSES):
            above = LAMP_COURSES[i + 1][2] if i < last else 0.0
            # a course under one of its own width needs no top; the others are closed a texel in under
            # the course above, the crown wholly
            inner = None if above >= r else max(0.0, above - 1.0)
            _glass(m, y0, y1, r, end if i in (0, last) else belly, emit, inner)
    return m


def _cable(name, mat, clamp=0.0):
    """A cable two texels thick along +z from its anchor, 48 units long and of one flat tone, so
    that drawing it out (M.between) smears nothing. clamp = the length in units of a thicker piece
    at its far end, flat as well: drawn out with the cable, it is the clamp that holds the cable's
    end."""
    m = M.Model(name)
    m.box((-1.0, -1.0, 0.0), (1.0, 1.0, 48.0 - clamp), mat, grain="z")
    if clamp:
        m.box((-1.5, -1.5, 48.0 - clamp), (1.5, 1.5, 48.0), IRON_F, grain="z")
    return m


def _egg(m, z):
    """A porcelain egg in a guy: EGG_LEN texels along z from z on, an iron thimble at each end. All
    of it is thicker than the cable, which runs through it."""
    m.tube("z", (0.0, 0.0), z, z + 1.0, 1.5, IRON_D)
    m.tube("z", (0.0, 0.0), z + 1.0, z + 2.0, 2.25, PORCELAIN)
    m.tube("z", (0.0, 0.0), z + 2.0, z + 5.0, 3.0, PORCELAIN)
    m.tube("z", (0.0, 0.0), z + 5.0, z + 6.0, 2.25, PORCELAIN)
    m.tube("z", (0.0, 0.0), z + 6.0, z + EGG_LEN, 1.5, IRON_D)


def _insulator():
    """One egg by itself, for a guy's upper end. Anchor: its middle; it lies along z."""
    m = M.Model(PREFIX + "insulator")
    _egg(m, -EGG_LEN / 2.0)
    return m


def _stay():
    """What a guy ends in at its anchor. Anchor: the top of the eye bolt; +z runs up the guy. A clamp
    on the bolt's head, a link, a bottle screw between its two jaws and the guy's lower egg. The
    cable starts in the upper jaw, at STAY_CABLE, and runs through the egg."""
    m = M.Model(PREFIX + "stay")
    m.box((-2.5, -2.5, -3.0), (2.5, 2.5, 0.5), IRON_D)
    m.box((-1.0, -1.0, 0.5), (1.0, 1.0, 3.0), IRON)
    m.box((-1.5, -1.5, 3.0), (1.5, 1.5, 4.5), IRON_D)
    m.box((-1.0, -1.0, 4.5), (1.0, 1.0, 6.0), IRON)
    m.tube("z", (0.0, 0.0), 6.0, 11.0, 2.0, IRON)
    m.box((-1.0, -1.0, 11.0), (1.0, 1.0, 12.5), IRON)
    m.box((-1.5, -1.5, 12.5), (1.5, 1.5, STAY_CABLE + 1.0), IRON_D)
    _egg(m, STAY_EGG)
    return m


@functools.lru_cache(maxsize=None)
def _models():
    built = [
        _lattice(PREFIX + "segment", True, True, PLATE_REACH["a"]),
        _lattice(PREFIX + "web", False, False, PLATE_REACH["b"]),
        _foot(PREFIX + "foot", True, True, PLATE_REACH["a"]),
        _foot(PREFIX + "foot_web", False, False, PLATE_REACH["b"]),
        _head(),
        _light(PREFIX + "light", True),
        _light(PREFIX + "light_off", False),
        _cable(PREFIX + "guy", CABLE, clamp=GUY_CLAMP),
        _cable(PREFIX + "lead", LEAD),
        _insulator(),
        _stay(),
    ]
    return {m.name: m for m in built}


def models():
    return dict(_models())


# ---- placing ---------------------------------------------------------------------------------------
def _world(p, origin):
    return tuple(p[i] + origin[i] for i in range(3))


def _place(canvas, name, pos, origin, scale=1.0, yaw=0.0, turns=()):
    """One model with its anchor on pos: upright, or turned by `turns` first."""
    x, y, z = _world(pos, origin)
    canvas.add_entity(x, y, z, M.display(_models()[PREFIX + name], yaw=yaw, scale=scale, turns=turns,
                                         brightness=BRIGHT, view=VIEW))
    return 1


def _stretch(canvas, name, a, b, origin):
    """A cable drawn out from a to b."""
    a, b = _world(a, origin), _world(b, origin)
    canvas.add_entity(a[0], a[1], a[2], M.between(_models()[PREFIX + name], a, b, brightness=BRIGHT, view=VIEW))
    return 1


def _lay(canvas, name, a, b, origin):
    """One model at its own size with its anchor on a and its +z towards b."""
    a, b = _world(a, origin), _world(b, origin)
    canvas.add_entity(a[0], a[1], a[2], M.between(_models()[PREFIX + name], a, b, length=16.0 * math.dist(a, b),
                                                  brightness=BRIGHT, view=VIEW))
    return 1


def _pipes(canvas, origin, belts):
    """The pipe blocks: a column in each of the four leg cells from the seat to the top belt, and for
    version b a belt of them in the cells between the legs at every joint but the top one, which the
    head carries. On the seat the columns stand inside the insulators."""
    ox, oy, oz = (int(round(v)) for v in origin)
    knee, top = int(math.floor(KNEE_Y)), int(math.floor(TOP_Y))
    for x, z in LEG_CELLS:
        for y in range(int(math.floor(BASE_Y)), top):
            canvas.set(ox + x, oy + y, oz + z, st(B.IRON_PIPE, axis="y"))
    if belts:
        for y in [int(math.floor(v)) for v in FOOT_BELTS] + list(range(knee, top, int(BAY))):
            for x, z, axis in BELT_CELLS:
                canvas.set(ox + x, oy + y, oz + z, st(B.IRON_PIPE, axis=axis))


def _shaft(canvas, origin, version):
    """The pipe blocks, the foot and the pieces over it. The foot is drawn with its one-sided parts
    for the corner that looks at the lead-in post."""
    _pipes(canvas, origin, belts=version == "b")
    foot, piece = ("foot", "segment") if version == "a" else ("foot_web", "web")
    n = _place(canvas, foot, (AX, BASE_Y, AZ), origin, scale=float(SCALE), yaw=_CORNER_YAW[_corner(LEAD_POST)])
    for i in range(SEGS):
        n += _place(canvas, piece, (AX, SEG_Y + i * SEG_BAYS * BAY, AZ), origin, scale=float(SCALE))
    return n


def _lamp(canvas, origin):
    n = _place(canvas, "light", (AX, GLASS_Y, AZ), origin, turns=LAMP_FRAME)
    canvas.entities[-1][3]["Tags"].append("c164_signal")
    return n


def _guys(canvas, origin):
    """At each anchor its piece, the cable from the bottle screw to the leg, and an egg in the cable
    EGG_DROP below the leg."""
    n = 0
    for anchor in GUY_ANCHORS:
        end = guy_end(anchor)
        n += _lay(canvas, "stay", anchor, end, origin)
        n += _stretch(canvas, "guy", _along(anchor, end, STAY_CABLE / 16.0), end, origin)
        n += _lay(canvas, "insulator", _along(end, anchor, EGG_DROP), end, origin)
    return n


def build(canvas, origin=(0, 0, 0), version=None):
    """Place the radio mast; returns the number of display entities (20). version "a" or "b" picks
    how the shaft is made (see the top of the module); left out it is DEFAULT."""
    version = version or DEFAULT
    if version not in VERSIONS:
        raise ValueError(f"machines/mast has versions {', '.join(VERSIONS)}, not {version!r}")
    n = _shaft(canvas, origin, version)
    n += _place(canvas, "head", (AX, HEAD_Y, AZ), origin, scale=float(SCALE))
    n += _lamp(canvas, origin)
    n += _guys(canvas, origin)
    n += _stretch(canvas, "lead", lead_lug(), LEAD_POST, origin)        # the feed lead from the shoe to the post
    return n
