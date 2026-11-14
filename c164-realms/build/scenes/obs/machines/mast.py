"""machines/mast -- the radio mast (plan ART-PLAN 7.2; parts/A5-machines.md 2.8; card radiomast.md).

The tallest vertical of the "one bar, one dome, one upright" skyline: an iron lattice mast on the
north-east stone pad, 62 blocks high, with guy wires, porcelain insulators, a red top beacon and
the antenna that runs to the clock tower. It is the star of V1 (the arrival view, ~66 blocks off)
and of V12 (the bird's eye, beyond 100). The game sends a display entity only within TRACKED (160)
blocks of the camera and the client draws it within its own entity distance, so a mast made all of
display entities can thin out or drop away far off -- exactly what must not happen to the "upright".

Two ways are built and shot side by side (the card's call, carried by the parent), the pick made
once the pictures are in:

  a  all display models    legs, belts and diagonals are stacked segment models, the view range
                           cranked up. The card's own way; its weakness is that nothing of it is a
                           block, so the client may cull it far away.
  b  blocks and models     the four legs are iron blocks (oxidized_copper_bars, painted iron) and
                           the top needle a lightning rod; only belts, diagonals, insulators, the
                           beacon, the guys and the antenna are models. The legs never cull, so the
                           upright holds at any distance -- the robust way far off.

Guys, insulators, the beacon and the antenna are the same in both. The beacon is lit this round
(emit red, tagged c164_signal so A8 can blink it later); its blink axis is its own vertical. The
pad and the guy-anchor piers are c229's (site); the tower-side antenna bracket is c223's, on the
tower's north-east face at y 35..40. Coordinates come from the skeleton; nothing is hard-coded.
"""
import functools
import math

from artkit import models as M

from ..common import blocks as B
from ..common import palette as P
from ..common import skeleton as S

PREFIX = "mach_mast_"
DEFAULT = "b"           # provisional: blocks never cull, so the upright is sure to hold far away;
#                         switched to the version the A/B pictures pick (parent + review)

# --- where it stands (skeleton; nothing hard-coded) ---------------------------------------------
_FOOT = S.RADIO_MAST["foot"]                # (23, -40), cells
HEIGHT = int(S.RADIO_MAST["height"])        # 62
BASE_Y = float(S.MAST_PAD["feet"])          # 0.0, feet on the pad (level with the upper terrace)
CX = _FOOT[0] + 0.5                          # 23.5, the centre line in x
# one block north of the foot cell's own centre, so the 2x2 leg footprint (cells x 22/24, z -42/-40)
# sits clear of the pad's south edge row z = -39, which carries c221's kerb and railing
CZ = _FOOT[1] - 0.5                          # -40.5
LEG = 1.0                                    # a leg stands this far from the centre on x and on z

# --- the lattice, in display blocks -------------------------------------------------------------
SCALE = 2                                    # one segment is shown at this scale (px = scale)
SEG_BLOCKS = 6                               # the display height of one stacked segment
BAYS = 2                                     # X-brace bays in a segment: a brace every 3 blocks
N_SEG = 10                                   # 10 x 6 = 60 blocks of lattice
LATTICE_TOP = BASE_Y + SEG_BLOCKS * N_SEG    # 60.0
BEACON_Y = LATTICE_TOP + 1.0                 # the needle is 60..61, the beacon 61..62

# --- guys and antenna ---------------------------------------------------------------------------
GUY_Y = BASE_Y + 38.0                        # the guys leave the mast about two thirds up
ANT_Y = BASE_Y + 57.0                        # the antenna leaves the mast near the top
# three anchors on the pad (cells x 17..29, z -46..-39), biased north so no guy crosses the front
# court (z >= -30) or the V1/V2 sight lines to the main building, and none on the south edge row
GUY_ANCHORS = [
    (CX, BASE_Y, CZ - 5.0),                  # due north, (23.5, -45.5)
    (CX + 5.0, BASE_Y, CZ - 1.5),            # east-north-east, (28.5, -42.0)
    (CX - 5.0, BASE_Y, CZ - 1.5),            # west-north-west, (18.5, -42.0)
]
# the tower-side antenna bracket (c223: the tower's north-east face at y 35..40, facing the mast);
# just off the north-east corner of the clock-tower shaft. Provisional until c223 pins the height.
ANT_TOWER = (S.CLOCK_SHAFT_X[1] + 0.8, 38.0, S.CLOCK_SHAFT_Z[0] - 0.3)   # (16.8, 38, -33.3)

VIEW = 16.0             # view range of every mast entity: reach 1024, so the client never culls it
#                         for distance within the map; what remains far off is the 160-block server
#                         tracking limit, which is the whole reason version b keeps the legs as blocks
BEACON_LEVEL = 7        # the warning light handed to A2 (plan 3.2 third rank; a single point of red)

IRON = P.mat("iron")
IRON_D = P.mat("iron_dark")
PORCELAIN = P.mat("porcelain")


def _flat(name, step):
    """One flat tone of a ramp, for cables and the lit lens where shading is painted, not beveled."""
    return P.mat(name, kind="flat", base=step, bevel=0)


def _u(blocks):
    """Display blocks to model units at SCALE (16 units is one block at scale 1; SCALE blocks here)."""
    return blocks * 16.0 / SCALE


# ---- the lattice segment -----------------------------------------------------------------------
def _belt(m, y, legu):
    """A square belt of flat iron around the four legs at height y (model units), kept inside the
    segment so stacked segments meet without their belts running over the join."""
    t, seg_u = 1.0, _u(SEG_BLOCKS)
    lo, hi = max(0.0, y - t), min(seg_u, y + t)
    for sz in (-legu, legu):
        m.box((-legu, lo, sz - 1.0), (legu, hi, sz + 1.0), IRON_D, grain="x")
    for sx in (-legu, legu):
        m.box((sx - 1.0, lo, -legu), (sx + 1.0, hi, legu), IRON_D, grain="z")


def _bay_braces(m, y0, y1, legu):
    """The crossed diagonals of one bay on all four faces (model units)."""
    dw = 1.6
    for sz in (-legu, legu):                                 # north and south faces: diagonals in x-y
        m.beam((-legu, y0, sz), (legu, y1, sz), dw, dw, IRON)
        m.beam((legu, y0, sz), (-legu, y1, sz), dw, dw, IRON)
    for sx in (-legu, legu):                                 # east and west faces: diagonals in z-y
        m.beam((sx, y0, -legu), (sx, y1, legu), dw, dw, IRON)
        m.beam((sx, y0, legu), (sx, y1, -legu), dw, dw, IRON)


def _segment(name, legs):
    """One stacked lattice segment (card: lattice(seg)). legs=True bakes the four corner legs into
    the model (version a); legs=False leaves them to the iron blocks (version b). px = SCALE keeps
    16 texels to the block whatever the scale."""
    m = M.Model(name, px=float(SCALE))
    legu, seg_u, bay_u = _u(LEG), _u(SEG_BLOCKS), _u(SEG_BLOCKS) / BAYS
    if legs:
        for sx in (-legu, legu):
            for sz in (-legu, legu):
                m.box((sx - 1.5, 0.0, sz - 1.5), (sx + 1.5, seg_u, sz + 1.5), IRON, grain="y")
    for b in range(BAYS + 1):
        _belt(m, bay_u * b, legu)
    for b in range(BAYS):
        _bay_braces(m, bay_u * b, bay_u * (b + 1), legu)
    return m


def _head():
    """The top needle of version a: a tapering spike of iron (version b uses a lightning-rod block).
    One block tall, anchored at its foot."""
    m = M.Model(PREFIX + "head", px=1.0)
    m.taper("y", (0, 0), 0.0, 12.0, 2.0, 0.6, IRON, steps=3)
    m.tube("y", (0, 0), 12.0, 16.0, 0.4, IRON_D, sides=4)
    return m


def _light(name, lit):
    """The red top beacon (card: mach_mast_light, ~0.5 block). Lit now (emit red); the dark twin is
    for A8 to swap to when it makes it blink. Anchored at its foot; the blink axis is its vertical."""
    m = M.Model(name, px=1.0)
    m.tube("y", (0, 0), 0.0, 2.0, 2.2, IRON_D, sides=8)                      # mounting base
    m.tube("y", (0, 0), 2.0, 2.6, 2.8, IRON, sides=8)                        # gallery rim
    tone = _flat("signal", 3) if lit else _flat("signal", 0)
    m.tube("y", (0, 0), 2.6, 7.0, 4.0, tone, sides=10, emit=15 if lit else 0, shade=not lit)
    m.tube("y", (0, 0), 7.0, 8.0, 1.4, IRON_D, sides=6)                      # cap
    return m


def _insulator():
    """A porcelain strain insulator (card: mach_mast_insulator): a short stack of three skirts on an
    iron pin, for the guy ends and the antenna feed. Anchored at its middle."""
    m = M.Model(PREFIX + "insulator", px=1.0)
    m.tube("y", (0, 0), -5.0, 5.0, 0.7, IRON_D, sides=6)                     # the pin through it
    for yc in (-3.0, 0.0, 3.0):
        m.tube("y", (0, 0), yc, yc + 1.6, 2.6, PORCELAIN, sides=8)          # a skirt
        m.tube("y", (0, 0), yc + 1.6, yc + 2.2, 1.4, PORCELAIN, sides=8)
    return m


def _cable(name, step):
    """A thin cable that runs along +z from its anchor, 48 units long, one flat tone so a stretch
    (models.between) smears nothing: the guys and the antenna feeder."""
    m = M.Model(name, px=1.0)
    m.box((-0.5, -0.5, 0.0), (0.5, 0.5, 48.0), _flat("iron", step), grain="z")
    return m


@functools.lru_cache(maxsize=None)
def _models():
    return {
        PREFIX + "seg_a": _segment(PREFIX + "seg_a", legs=True),
        PREFIX + "seg_b": _segment(PREFIX + "seg_b", legs=False),
        PREFIX + "head": _head(),
        PREFIX + "light": _light(PREFIX + "light", True),
        PREFIX + "light_off": _light(PREFIX + "light_off", False),
        PREFIX + "insulator": _insulator(),
        PREFIX + "guy": _cable(PREFIX + "guy", 1),
        PREFIX + "antenna": _cable(PREFIX + "antenna", 0),
    }


def models():
    return dict(_models())


# ---- placing -----------------------------------------------------------------------------------
def _place(canvas, name, pos, origin, scale=1.0, yaw=0.0, view=VIEW, **opts):
    x, y, z = (pos[i] + origin[i] for i in range(3))
    canvas.add_entity(x, y, z, M.display(_models()[name], yaw=yaw, scale=scale, view=view, **opts))
    return 1


def _stretch(canvas, name, a, b, origin, thick=1.0, view=VIEW):
    aw = tuple(a[i] + origin[i] for i in range(3))
    bw = tuple(b[i] + origin[i] for i in range(3))
    canvas.add_entity(aw[0], aw[1], aw[2], M.between(_models()[name], aw, bw, thick=thick, view=view))
    return 1


def _leg_cells():
    return [(int(math.floor(CX + sx)), int(math.floor(CZ + sz))) for sx in (-LEG, LEG) for sz in (-LEG, LEG)]


def _block_legs(canvas, origin):
    """Version b: the four legs as iron bars and the needle as a lightning rod -- blocks, so the
    upright is drawn at any distance."""
    ox, oy, oz = (int(round(v)) for v in origin)
    for lx, lz in _leg_cells():
        for y in range(int(BASE_Y), int(LATTICE_TOP)):
            canvas.set(ox + lx, oy + y, oz + lz, B.IRON_BARS, keep=True)
    tx, tz = int(math.floor(CX)), int(math.floor(CZ))
    canvas.set(ox + tx, oy + int(LATTICE_TOP), oz + tz, f"{B.IRON_ROD}[facing=up]", keep=True)


def _beacon(canvas, origin):
    _place(canvas, PREFIX + "light", (CX, BEACON_Y, CZ), origin)
    canvas.entities[-1][3]["Tags"].append("c164_signal")
    cell = (int(math.floor(CX + origin[0])), int(math.floor(BEACON_Y + origin[1])), int(math.floor(CZ + origin[2])))
    _offer_lights(canvas, [(cell, BEACON_LEVEL)], "machines/mast:beacon")
    return 1


def _guys(canvas, origin):
    n = 0
    for ax, ay, az in GUY_ANCHORS:
        dx, dz = ax - CX, az - CZ
        d = math.hypot(dx, dz) or 1.0
        top = (CX + dx / d * LEG, GUY_Y, CZ + dz / d * LEG)
        n += _stretch(canvas, PREFIX + "guy", top, (ax, ay, az), origin)
        n += _place(canvas, PREFIX + "insulator", top, origin)
    return n


def _antenna(canvas, origin):
    dx, dz = ANT_TOWER[0] - CX, ANT_TOWER[2] - CZ
    d = math.hypot(dx, dz) or 1.0
    top = (CX + dx / d * LEG, ANT_Y, CZ + dz / d * LEG)
    n = _stretch(canvas, PREFIX + "antenna", top, ANT_TOWER, origin)
    n += _place(canvas, PREFIX + "insulator", top, origin)              # feed insulator at the mast
    n += _place(canvas, PREFIX + "insulator", ANT_TOWER, origin)        # at the tower bracket (c223)
    return n


def build(canvas, origin=(0, 0, 0), version=DEFAULT):
    """Place the radio mast. version "a" is all display models, "b" is iron-block legs plus models
    (see the module docstring). Returns the number of display entities placed."""
    n = 0
    if version == "b":
        _block_legs(canvas, origin)
    seg = PREFIX + ("seg_a" if version == "a" else "seg_b")
    for i in range(N_SEG):
        n += _place(canvas, seg, (CX, BASE_Y + i * SEG_BLOCKS, CZ), origin, scale=SCALE)
    if version == "a":
        n += _place(canvas, PREFIX + "head", (CX, LATTICE_TOP, CZ), origin)
    n += _beacon(canvas, origin)
    n += _guys(canvas, origin)
    n += _antenna(canvas, origin)
    return n


def _offer_lights(canvas, lights, why):
    """Hand the beacon's light source to A2's tool (sky/_lightkit); until it is in the tree, put the
    light block down so a test scene is lit. Mirrors props/_kit.offer_lights, kept local so machines
    does not lean on the props category."""
    lights = [((int(x), int(y), int(z)), int(level)) for (x, y, z), level in lights]
    if not lights:
        return
    try:
        from ..sky import _lightkit
        take = getattr(_lightkit, "take", None)
    except ImportError:
        take = None
    if take is not None:
        take(canvas, lights, why)
        return
    for (x, y, z), level in lights:
        canvas.set(x, y, z, f"{B.LIGHT}[level={level}]", keep=True)
