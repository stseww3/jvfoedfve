"""machines/mast -- the radio mast (plan/ART-PLAN.md 7.2, plan/parts/A5-machines.md 2.8, card
plan/packages/machines/radiomast.md).

The tallest upright of the skyline: an iron lattice mast on the stone foot north of the court
(site/mastbase, c229), the top of its lamp 62 blocks over the pad. It is seen from far more than
from near: the arrival view V1 stands 65 blocks from it, V2 53, V11 95 and the bird's eye V12 about
132, so what counts is that it is there at those distances, one unbroken dark line against the sky,
and reads as a lattice mast.

How it is made, from the seat up:

  foot    the four legs run together over one porcelain insulator on the iron seat: the mast
          stands on a point and is fed there (a copper lead to c229's lead-in post, a spark gap
          across the insulator). That is why it has guys, and why the guys are broken by eggs of
          porcelain.
  shaft   square and not tapered, the leg axes 2 blocks apart, a belt every 3 blocks, 16 bays of
          crossed diagonals with a plate at every joint and where the diagonals cross: y 8.5 to
          56.5. Four pieces of 12 blocks, shown four times their size (px = 4 keeps 16 texels to
          the block): 12 blocks are the 48 units a model may span.
  head    the legs gather to a pole that carries the lamp; an arm on the corner that looks at the
          clock tower holds the aerial. No yard and no gallery: nothing crosses the upright.
  lamp    one small red globe, lit steadily (A0 #36376: it does not blink, the comet is the one
          thing in the sky that may draw the eye). Its brightest tone is the signal ramp's third
          step, #e8402e, level with the orange windows; the lightest step (#ff8a6a) would read as
          one more star. A warning lamp, not a light. Its entity is
          tagged c164_signal and mach_mast_light_off is its dark twin, kept for the motion line.
          It throws no light: nothing stands near it to be lit, and a source up there would only
          pale the iron under it.
  guys    c229's four anchors stand on the diagonals, 4 blocks out, so the guys go four ways (the
          card said three), one from each anchor to the leg that looks at it, at belt 5 (y 23.5).
          The anchors are close to the foot: a guy to the top would run within 5 degrees of its
          leg and read from far as the mast seen double, so they stop low, where the four of them
          make a tent that stands clear of the shaft. At the anchor a clamp on the eye bolt, a
          bottle screw and an egg; at the leg a clamp on the corner of the joint; one more egg a
          third of the way down from there; the cable between is drawn out. All of it keeps north
          of z -35: nothing crosses the court or the sight lines of V1 and V2 to the main building.
  aerial  one wire from the arm at the head to an iron rod on the clock tower (main/tower, c223),
          a string of three porcelain discs at each end. The wire and the guys are two texels
          thick and of the darkest iron, so that they hold as lines against the sky; the discs
          aloft are grey porcelain: white ones would be brighter than the night sky and read as
          stars beside the comet. White porcelain is kept for the foot and the guys, low down.

All pieces are given one brightness, the open sky's: each would otherwise take the light of the
cell its anchor is in, and a lamp near the foot would show as a step where two pieces meet.

Two ways to build the shaft, to be compared on pictures from near and from far (the test scenes
obs_mach_radiomast and obs_mach_radiomast_b show them from the same cameras):

  a   all of it display models: legs 5 texels square, belts and diagonals 3. Inside each model leg
      stands a column of the thin iron pipe block (B.IRON_PIPE), hidden by it. The server sends a
      display entity to a player within 160 blocks at the most and never farther than its view
      distance; all cameras of the board are nearer than that, but should the models ever fall
      away, four thin legs still stand.
  b   legs and belts are that pipe block, 3 texels thick and partly open; the models carry the
      diagonals and the plates only.

a is the default until the pictures say otherwise: legs, belts and diagonals are drawn one way and
take the same light, and from V1 a leg of 5 texels is about two pixels wide in a 720p picture, the
pipe block little more than one.

What this module reads from its neighbours, each with the same numbers as a fallback while the
neighbour is not in the tree: site.mastbase.TOP, GUY_ANCHORS and ANTENNA_HOOK; main.tower.
ANTENNA_ANCHOR, the point where the aerial's lower string hooks on. What the clocks' test scenes
(c238) read from this one: build, models, BASE_Y, GUY_ANCHORS, LEAD_POST, TOWER_HOOK.
"""
import functools
import math

from artkit import models as M
from artkit.blocks import st

from ..common import blocks as B
from ..common import palette as P
from ..common import skeleton as S

try:
    from ..site import mastbase as _base        # c229: the stone foot, the guy anchors, the lead-in post
except ImportError:
    _base = None
try:
    from ..main import tower as _tower          # c223: the rod on the clock tower that the aerial hooks on to
except ImportError:
    _tower = None

PREFIX = "mach_mast_"
VERSIONS = ("a", "b")
DEFAULT = "a"

# ---- where it stands -------------------------------------------------------------------------------
FX, FZ = S.RADIO_MAST["foot"]                   # (23, -40): the cell the mast's axis stands in
G = float(S.MAST_PAD["feet"])                   # 0.0: where feet stand on the pad
AX, AZ = FX + 0.5, FZ + 0.5                     # the axis, (23.5, -39.5): the middle of c229's seat
TIP_Y = G + float(S.RADIO_MAST["height"])       # 62.0: the top of the lamp

BASE_Y = float(getattr(_base, "TOP", G + 2.0))  # 2.0: the top face of the seat
GUY_ANCHORS = [tuple(float(v) for v in p) for p in getattr(
    _base, "GUY_ANCHORS", [(FX + sx * 4 + 0.5, G + 2.0, FZ + sz * 4 + 0.5) for sx in (-1, 1) for sz in (-1, 1)])]
LEAD_POST = tuple(float(v) for v in getattr(_base, "ANTENNA_HOOK", (FX - 1.5, G + 4.0, FZ + 2.5)))
# Where the aerial's lower string hooks on to the tower. The wire comes down steeply, 76 degrees from
# the level, so the point has to stand clear of the tower's cornices: a third of a block or more
# outside their outer edge. The fallback is c223's own number (#37220): the end of an iron rod that
# sticks two blocks north out of the tower's north-east corner, in the course under the cornice at
# y 31.
TOWER_HOOK = tuple(float(v) for v in getattr(
    _tower, "ANTENNA_ANCHOR", (S.CLOCK_SHAFT_X[1] + 0.5, 30.5, S.CLOCK_SHAFT_Z[0] - 2.0)))      # (16.5, 30.5, -35.0)

# ---- the lattice -----------------------------------------------------------------------------------
SCALE = 4                       # the lattice pieces are shown this large; px = SCALE keeps 16 texels to the block
U = SCALE / 16.0                # one unit of those models in blocks: 0.25
LEG = 1.0                       # the leg axes stand this far from the mast's axis in x and in z
BAY = 3.0                       # a belt every three blocks
BAYS = 16
SEG_BAYS = 4                    # bays to a piece: 12 blocks, the 48 units a model may span
SEGS = BAYS // SEG_BAYS
KNEE_Y = math.floor(BASE_Y) + 6.5       # 8.5: the lowest belt, where the tapered foot turns into the square shaft
TOP_Y = KNEE_Y + BAYS * BAY     # 56.5: the top belt
GUY_BELT = 5                    # the belt the guys leave from: y 23.5
GUY_OUT = 0.25                  # ... this far outside the leg's axis in x and in z: just off the joint's corner

# sizes of the members in units of the lattice models (a unit is 4 texels). Legs and belts keep the
# sizes cr2 asked for (5 and 3 texels: a leg has to survive as a line at 95 blocks); what is thinned is
# the web -- the diagonals and the joint and knot plates -- and the tone is lifted, because measured on
# the second draft's V11 picture the shaft covered 59 per cent of its own width at 57 per cent of the
# sky's brightness: from far it read as a solid black bar (A0: too black and too heavy).
LEG_W = 1.25                    # a leg, 5 texels square
BELT = 0.75                     # a belt, 3 texels square
BRACE, BRACE_T = 0.5, 0.375     # a diagonal: 2 texels wide in the face, 1.5 thick
PLATE_H = 1.25                  # a joint plate: 5 texels high, 1 thick, half a texel proud of the leg
PLATE_REACH = {"a": 1.75, "b": 2.25}    # ... and this long from the leg's outer edge inwards; in b it reaches
#                                         the end of the belt block, which stops half a block short of the leg
KNOT, KNOT_T = 0.75, 0.25       # the plate where two diagonals cross: 3 texels square, 1 thick
RIVET = 0.25                    # ... and the head of the rivet through it: 1 texel
COLLAR = 0.875                  # half the width of the collars that close a leg's two ends
LEG_U, BAY_U = LEG / U, BAY / U         # 4 and 12 units
NODE = BELT / 2.0               # a piece starts this far under its lowest belt's middle: the belt lies wholly in it
SEG_Y = KNEE_Y - NODE * U       # 8.40625: the bottom of the lowest piece
HEAD_Y = SEG_Y + BAYS * BAY     # 56.40625: where the head takes over
FOOT_TOE = 0.75                 # the legs meet the shoe this far from the axis ...
FOOT_TOE_Y = 8.75               # ... and this high over the seat (units of the foot model)
FOOT_RING_Y = 17.5              # the one belt of the tapered foot
FOOT_LUG = (1.75, 8.75)         # the terminal on the shoe's corner: distance from the axis in x and z, height
HEAD_EYE = (5.5, 2.5)           # the end of the aerial's arm: distance from the axis in x and z, height
LAMP_H = 10                     # texels: the lamp from its foot on the pole to its top
LAMP_Y = TIP_Y - LAMP_H / 16.0  # 61.375

LEG_CELLS = [(FX + sx, FZ + sz) for sx in (-1, 1) for sz in (-1, 1)]
BELT_CELLS = [(FX, FZ - 1, "x"), (FX, FZ + 1, "x"), (FX - 1, FZ, "z"), (FX + 1, FZ, "z")]

# ---- guys and aerial -------------------------------------------------------------------------------
STAY_CABLE = 13.0               # texels from the eye bolt to where the cable leaves the bottle screw's jaw
STAY_EGG = 19.0                 # ... and to the guy's lower egg
EGG_LEN = 7.0
EGG_DROP = 7.0                  # blocks from the leg down the guy to its upper egg: well clear of the shaft
GUY_CLAMP = 0.5                 # units of the guy's model, which is drawn out seven times: 3.5 texels of clamp
STRING_LEN = 20.0               # texels from the hook of a disc string to where the wire leaves its clamp

VIEW = 8.0                      # view range: 512 blocks at the client's normal setting, 256 at its lowest;
#                                 past the 160 the server sends, so the client never drops a piece first
BRIGHT = (15, 0)                # (sky, block): what a piece takes under the open sky with no lamp near

IRON = P.mat("iron")                            # fittings
# The lattice is drawn one ramp step lighter than the second draft's (#303844 instead of #252b34):
# measured against the sky in the V11 picture the second draft came out at 57 per cent of the sky's
# brightness, which is what read as a black bar. One step up keeps it darker than the sky -- it still
# holds as a silhouette -- without cutting a hole in the night (A0: not much darker than the sky).
IRON_D = P.mat("iron", noise=0.12, bevel=1, base=4)     # the lattice: legs, belts, plates
IRON_F = P.mat("iron", kind="flat", bevel=0, base=4)    # the diagonals: the lattice's tone without speckle or edge
PORCELAIN = P.mat("porcelain")                  # white: the foot, the guys
GREY = P.mat("porcelain", base=0, noise=0.0)    # the ramp's two darkest steps: the discs aloft
BRASS = P.mat("brass")


def _flat(name, step):
    """One flat tone of a ramp: cables, which are drawn out, and glass, whose shading is painted."""
    return P.mat(name, kind="flat", base=step, bevel=0)


CABLE = _flat("iron", 0)                        # the guys
WIRE = _flat("iron", 0)                         # the aerial
LEAD = _flat("old_copper", 1)                   # the feed lead at the foot, seen from near only
STUD = _flat("iron", 4)                         # rivet heads
RED = [_flat("signal_glow", i) for i in range(len(P.RAMPS["signal"]))]

# members of one kind share one picture: the sheet of a piece stays small
LEG_SEED, BELT_SEED, BRACE_SEED, PLATE_SEED, STRUT_SEED, KNOT_SEED, STUD_SEED = 1001, 1002, 1003, 1005, 1006, 1007, 1008


# ---- geometry --------------------------------------------------------------------------------------
def _corner(p):
    """The corner of the square shaft that looks at the point p, as signs in x and z."""
    return (1 if p[0] >= AX else -1), (1 if p[2] >= AZ else -1)


# The foot and the head are drawn with their one-sided part (the terminal, the aerial's arm) on the
# corner -x, +z; this turns that corner to another.
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


def aerial_eye():
    """The end of the arm at the head, where the aerial's upper string hooks on."""
    sx, sz = _corner(TOWER_HOOK)
    return AX + sx * HEAD_EYE[0] * U, HEAD_Y + HEAD_EYE[1] * U, AZ + sz * HEAD_EYE[0] * U


def lead_lug():
    """The terminal on the foot's shoe, where the lead to c229's post starts."""
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


def _foot():
    """The tapered foot, from the seat to the lowest belt. Anchor: the middle of the seat's top."""
    m = M.Model(PREFIX + "foot", px=float(SCALE))
    knee = (KNEE_Y - BASE_Y) / U                                    # 26 units up: the lowest belt's middle

    def out(y):
        """How far a leg's axis stands from the mast's at height y."""
        return FOOT_TOE + (LEG_U - FOOT_TOE) * (y - FOOT_TOE_Y) / (knee - FOOT_TOE_Y)

    # the bed plate on the seat and the pedestal
    m.box((-2.5, 0.0, -2.5), (2.5, 0.5, 2.5), IRON_D)
    m.tube("y", (0.0, 0.0), 0.5, 1.5, 1.5, IRON)
    # the base insulator: a porcelain column with three sheds; the whole mast stands on it
    m.tube("y", (0.0, 0.0), 1.5, 6.75, 1.0, PORCELAIN)
    for y in (1.75, 3.5, 5.25):
        m.tube("y", (0.0, 0.0), y, y + 1.0, 2.0, PORCELAIN)
    # its iron cap, the pivot and the shoe the four legs run into
    m.tube("y", (0.0, 0.0), 6.75, 7.5, 1.25, IRON)
    m.tube("y", (0.0, 0.0), 7.5, 8.0, 0.5, IRON_D)
    m.box((-1.5, 8.0, -1.5), (1.5, 9.5, 1.5), IRON_D)
    for sx in (-1, 1):
        for sz in (-1, 1):
            m.rod((sx * FOOT_TOE, FOOT_TOE_Y, sz * FOOT_TOE), (sx * LEG_U, knee, sz * LEG_U), LEG_W / 2.0, IRON_D,
                  sides=4, seed=LEG_SEED)
    # one belt half way up, crossed diagonals from it to the knees
    _belts(m, FOOT_RING_Y, out(FOOT_RING_Y))
    _braces(m, FOOT_RING_Y, knee, out(FOOT_RING_Y), LEG_U)
    _knots(m, FOOT_RING_Y, knee, out(FOOT_RING_Y), LEG_U)
    _collars(m, knee - 2.25, knee + 0.5)
    # the terminal of the lead to the lead-in post, on the shoe's corner -x, +z
    lx, ly = FOOT_LUG
    m.box((-lx - 0.5, ly - 0.5, lx - 0.5), (-lx + 0.5, ly + 0.5, lx + 0.5), BRASS)
    # the spark gap across the insulator, on the next corner (+x, +z; both look at the court): a horn
    # down from the shoe, one up from the bed plate, a brass ball on each, three texels of air between
    m.rod((1.25, 8.5, 1.25), (2.75, 6.25, 2.75), 0.25, IRON_D, sides=4)
    m.rod((2.0, 0.5, 2.0), (2.75, 4.0, 2.75), 0.25, IRON_D, sides=4)
    m.box((2.25, 5.5, 2.25), (3.25, 6.5, 3.25), BRASS)
    m.box((2.25, 3.75, 2.25), (3.25, 4.75, 3.25), BRASS)
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
    m.tube("y", (0.0, 0.0), apex + 0.5, (LAMP_Y - HEAD_Y) / U, 0.5, IRON_D)
    # the arm of the aerial, on the corner -x, +z: out and a little up from the collar
    ex, ey = HEAD_EYE
    m.beam((-LEG_U, 1.0, LEG_U), (-ex, ey, ex), 0.75, 0.75, IRON_D)
    return m


def _glass_ball(m, centre, radius, bands, emit):
    """A glass ball in bands of flat tone, [(from, to, material)] with -1 the bottom and 1 the top:
    every face of a band has the one tone, so the ball looks the same from all sides. Lit, it is
    full bright with no face shading: its light and dark is what is painted."""
    for t0, t1, mat in bands:
        m.ball(centre, radius, mat, sides=8, layers=1, part=(t0, t1),
               faces={"n": mat, "s": mat, "u": mat, "d": mat}, emit=emit, shade=not emit)


def _light(name, lit):
    """The lamp: a red globe half a block across in an iron holder. Anchor: its foot, on the pole's
    top. Lit, its belly is the signal ramp's third step (0.440, #e8402e) and its two ends the second
    (0.276, #a3201a). The ramp's top step (0.664, #ff8a6a) is not used: an orange pink as bright as a
    golden window would read as one more star beside the comet. A warning lamp, not a light."""
    m = M.Model(name)
    m.tube("y", (0.0, 0.0), 0.0, 1.5, 2.5, IRON_D)
    m.tube("y", (0.0, 0.0), 1.5, 2.5, 1.5, IRON)
    end, belly = (RED[1], RED[2]) if lit else (RED[0], RED[1])
    _glass_ball(m, (0.0, 6.0, 0.0), 4.0,
                [(-1.0, -0.45, end), (-0.45, 0.1, belly), (0.1, 0.4, belly), (0.4, 0.75, belly), (0.75, 1.0, end)],
                emit=15 if lit else 0)
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


def _string():
    """The string of three porcelain discs at each end of the aerial. Anchor: its hook, a shackle
    that takes in the end of the arm or of the tower's rod; +z runs along the wire, which leaves the
    clamp at STRING_LEN. Grey porcelain: the upper string hangs against the sky, beside the comet;
    the lower one, by the tower's wall, is the same model."""
    m = M.Model(PREFIX + "string")
    m.box((-2.5, -2.5, -1.5), (2.5, 2.5, 1.5), IRON_D)
    m.tube("z", (0.0, 0.0), 1.5, STRING_LEN - 2.0, 0.75, IRON_D, sides=4)
    for z in (6.0, 11.0, 16.0):                 # the first one far enough down to hang clear of the arm
        m.tube("z", (0.0, 0.0), z - 1.0, z + 1.0, 3.5, GREY)
        m.tube("z", (0.0, 0.0), z + 1.0, z + 2.0, 1.75, GREY)
    m.box((-1.5, -1.5, STRING_LEN - 2.0), (1.5, 1.5, STRING_LEN + 1.0), IRON_D)
    return m


@functools.lru_cache(maxsize=None)
def _models():
    built = [
        _lattice(PREFIX + "segment", True, True, PLATE_REACH["a"]),
        _lattice(PREFIX + "web", False, False, PLATE_REACH["b"]),
        _foot(),
        _head(),
        _light(PREFIX + "light", True),
        _light(PREFIX + "light_off", False),
        _cable(PREFIX + "guy", CABLE, clamp=GUY_CLAMP),
        _cable(PREFIX + "antenna", WIRE),
        _cable(PREFIX + "lead", LEAD),
        _insulator(),
        _stay(),
        _string(),
    ]
    return {m.name: m for m in built}


def models():
    return dict(_models())


# ---- placing ---------------------------------------------------------------------------------------
def _world(p, origin):
    return tuple(p[i] + origin[i] for i in range(3))


def _place(canvas, name, pos, origin, scale=1.0, yaw=0.0):
    """One model upright with its anchor on pos."""
    x, y, z = _world(pos, origin)
    canvas.add_entity(x, y, z, M.display(_models()[PREFIX + name], yaw=yaw, scale=scale, brightness=BRIGHT, view=VIEW))
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
    """The pipe blocks: a column in each of the four leg cells from the lowest belt to the top one,
    and for version b a belt of them in the cells between the legs at every joint but the top one,
    which the head carries."""
    ox, oy, oz = (int(round(v)) for v in origin)
    rows = range(int(math.floor(KNEE_Y)), int(math.floor(TOP_Y)))
    for x, z in LEG_CELLS:
        for y in rows:
            canvas.set(ox + x, oy + y, oz + z, st(B.IRON_PIPE, axis="y"))
    if belts:
        for y in rows[::int(BAY)]:
            for x, z, axis in BELT_CELLS:
                canvas.set(ox + x, oy + y, oz + z, st(B.IRON_PIPE, axis=axis))


def _shaft(canvas, origin, version):
    _pipes(canvas, origin, belts=version == "b")
    piece = "segment" if version == "a" else "web"
    n = 0
    for i in range(SEGS):
        n += _place(canvas, piece, (AX, SEG_Y + i * SEG_BAYS * BAY, AZ), origin, scale=float(SCALE))
    return n


def _lamp(canvas, origin):
    n = _place(canvas, "light", (AX, LAMP_Y, AZ), origin)
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


def _aerial(canvas, origin):
    """The wire from the arm at the head to the tower's rod, a disc string at each end."""
    eye = aerial_eye()
    n = _lay(canvas, "string", eye, TOWER_HOOK, origin)
    n += _lay(canvas, "string", TOWER_HOOK, eye, origin)
    n += _stretch(canvas, "antenna", _along(eye, TOWER_HOOK, STRING_LEN / 16.0),
                  _along(TOWER_HOOK, eye, STRING_LEN / 16.0), origin)
    return n


def build(canvas, origin=(0, 0, 0), version=None):
    """Place the radio mast; returns the number of display entities (23). version "a" or "b" picks
    how the shaft is made (see the top of the module); left out it is DEFAULT."""
    version = version or DEFAULT
    if version not in VERSIONS:
        raise ValueError(f"machines/mast has versions {', '.join(VERSIONS)}, not {version!r}")
    n = _shaft(canvas, origin, version)
    n += _place(canvas, "foot", (AX, BASE_Y, AZ), origin, scale=float(SCALE), yaw=_CORNER_YAW[_corner(LEAD_POST)])
    n += _place(canvas, "head", (AX, HEAD_Y, AZ), origin, scale=float(SCALE), yaw=_CORNER_YAW[_corner(TOWER_HOOK)])
    n += _lamp(canvas, origin)
    n += _guys(canvas, origin)
    n += _aerial(canvas, origin)
    n += _stretch(canvas, "lead", lead_lug(), LEAD_POST, origin)        # the feed lead from the shoe to the post
    return n
