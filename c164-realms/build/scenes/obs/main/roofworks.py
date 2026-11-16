"""main/roofworks -- the machines on the roofs of the main building (the director's card
main/roof-works of the second round, plan/round2.md; plan/packages/main/roofworks.md).

The first round kept the roofs bare: nothing stood over the ridges, and from the court the house
was a plain stone outline with its machines indoors. The second round wants machines out of doors,
iron and rivets, and wants them to move. This package puts them on the wings' roofs, between the
great drum and the end pavilions.

What stands so far:

  the ventilators   two on each wing, on the east slope, three columns from the ridge walk and two
                    from the parapet, each over the window axis of a bay of the east front (the
                    fourth and the fifth bay from the middle; the north wing is the south wing
                    mirrored on the axis). A riveted sheet-iron shaft on a lead apron dressed over
                    the slates, a storm collar, and on its spindle a head the wind turns: eight
                    slanted vanes between two hoops under a low cone. The inner one of a wing is
                    the big one, the outer one a smaller make, and they turn at their own pace.
                    From the court only the heads stand over the parapet, dark against the sky;
                    from the ridge walk they are three steps away.

To come on this card: a flue with its steam, roof lights, the guard of the ridge walk, the
lightning conductors, and the pipes on the back and the wings' walls.

The limits (the main line's lead, c321): the parapets' columns and the two rows of barrier over
them are left alone; nothing solid stands on the ridge walk, the treads or the terraces; in V1 and
V2 the dome and the comet lead, so what stands here is small, dark and slow, lower than the drum's
cornice and far from the axis. The ventilators are display entities and nothing else: no block, no
barrier, no light, so nobody is stopped, nobody climbs them and no cell is darker than it was.

    python -m scenes.obs.main.roofworks check       (from c164-realms/build)

Coordinates are scene cells (x east, z south, y up), as everywhere in the main line.
"""
import functools
import math
import sys

from artkit import models as M
from artkit.canvas import Canvas
from artkit.pixelart import Sprite

from ..common import palette as P
from ..common import skeleton as S
from ..motion import _kit as MK
from ..props import _kit as K
from . import roof

ORDER = 75                      # after the roofs' own package (70): the ventilators stand on its slates

PREFIX = "bld_roof_"
VIEW = M.MID                    # drawn up to 64 blocks away: from the court, the terraces and the roofs (V2, V5, V11),
#                                 not from the station or the far lookout, whose views are full (the line of 600)

SHEET = K.IRON_D                # the shaft's sheet iron
BAND = K.IRON                   # its lap bands, the flange, the curb and the storm collar: what takes the light
LEAD = K.flat("iron", 2)        # the lead dressed over the slates round its foot
WELT = K.flat("iron", 3)        # the lead's rolled edges
VANES = (K.IRON, K.IRON_D)      # the head's vanes, light and dark by turns: a turning head is seen to turn
WORN = K.flat("iron", 5)        # an edge the weather and the hand have worn bright
STEEL = K.flat("iron", 6)       # the spindle, polished where the head rides on it
HOOP = K.IRON
HUB = K.IRON_D
CAP = P.mat("verdigris", base=1)                # the head's low cone: sheet copper gone green, as the domes it stands
#                                                 between, a tone darker than theirs
OILER = K.BRASS_D               # the oil cup over the head's bearing
GRIP = K.BRASS                  # the damper lever's grip: brass the hand keeps bright
ROD = K.flat("iron", 3)         # the stay rods

# what the weather and the fitter have left, as hand-drawn pictures on faces as thin as paper
OIL = {"o": P.RAMPS["iron"][0], "b": P.RAMPS["dark_wood"][2], "t": P.RAMPS["dark_wood"][4]}     # old oil: black, brown, tan
RUST = {"r": P.RAMPS["old_copper"][0], "d": P.RAMPS["dark_wood"][2], "l": P.RAMPS["old_copper"][1]}
CHALK = {"c": P.RAMPS["porcelain"][4], "g": P.RAMPS["porcelain"][2]}
OIL_RUN = Sprite(PREFIX + "oil_run", ["bot", "bob", "tob", ".ob", ".bt", ".ob", ".b.", ".tb", "..b", "..t", "..b"], OIL)
WEEP = Sprite(PREFIX + "rust_weep", ["r.l", ".r.", "..l"], RUST)                                    # under a lap band, on the lee side
RUST_FOOT = Sprite(PREFIX + "rust_foot", ["r.d.r", "rrdrl", ".rrr.", "l.r.."], RUST)                # on the lead, under the flange
RUST_RISER = Sprite(PREFIX + "rust_riser", [".rr", "rr.", ".r.", ".rl", "r..", ".r.", ".l.", "..."], RUST)   # down the slate's edge
RUST_RUN = Sprite(PREFIX + "rust_run", ["rr..l..", "rrrl...", "drr.l..", "r..l..."], RUST)         # and out over the next slate
TICK = Sprite(PREFIX + "chalk_tick", ["...c", "g.c.", ".c.."], CHALK)                              # the fitter's tick: looked at

# The two sizes, in pixels (a display entity is never scaled: 16 pixels to the block everywhere).
#   shaft     its radius (over the flats) and its top, from the foot
#   bands     where a lap band begins: the joints of the shaft's sheets
#   damper    the height of the damper's spindle, in the middle of a sheet
#   hoop      the radius of the head's two hoops
#   vane      how high a vane is
#   cap       the cone's radius at its eaves and its height
SIZES = {
    "": dict(shaft=5.0, top=27.0, bands=(9.0, 18.0), damper=13.75, hoop=10.0, vane=10.0, cap=(11.5, 4.0)),
    "_small": dict(shaft=4.0, top=21.0, bands=(10.0,), damper=15.5, hoop=8.0, vane=8.0, cap=(9.25, 3.25)),
}
APRON_OUT, APRON_UP = 3.0, 1.0  # the apron: this far beyond the shaft, this thick
FLANGE_OUT, FLANGE_UP = 2.25, 0.75              # the foot's flange, bolted down through the lead
CURB_OUT, CURB_UP = 1.0, 2.0    # the curb the sheets stand in
BAND_OUT, BAND_UP = 0.5, 1.5
SEAM = (1.2, 0.35)              # the upright lap seam of the sheets, on the east flat: its width, how proud
SEAM_PITCH = 3.0                # a rivet every so far down it
COLLAR_OUT, COLLAR_UP = 2.0, 2.0                # the storm collar: a cone that sheds the rain past the shaft's mouth
STAY_UNDER = 3.0                # the stay band: this far under the shaft's top
STAY_R = 0.3
STAY_OUT = 14.0                 # where a stay's eye is bolted to the slates, from the axis
STEP = 8.0                      # the roof rises half a block a column: the slate west of the foot lies this much
#                                 higher, the one east of it this much lower (the self-check holds the roof to it)
SPINDLE_R, SPINDLE_UP = 0.6, 4.0
BEARING = 1.5                   # the gap between the collar and the head: the spindle is seen in it
HOOP_THICK, HOOP_UP = 1.5, 1.5
HUB_R = 1.25
VANE_N = 8
VANE_IN, VANE_THICK, VANE_OFF = 0.25, 0.8, 0.54 # a vane is a plate along a chord, this share of the hoop's radius off the
#                                                 axis, and begins this share of it from the chord's middle: it stands
#                                                 slanted to the wind, its outer edge trailing, and the head is hollow
VANE_PROUD = 0.5                # how far a vane's outer edge stands out of the hoops
BRIM_UP = 0.6                   # the cone's rolled eaves
CAP_TOP_R = 2.0
CAP_STEPS = 6
OILER_R, OILER_UP = 0.9, 1.75

COLUMN = S.WALL_E - 3           # 12: the column they stand in, the third of the east slope from the parapet
# (z of its row on the south wing, size, ticks of one turn, degrees it is placed turned): a wing's inner one and its
# outer one, over the window axes of two neighbouring bays of the east front (c321: on a window's axis or a
# pilaster's, never over the edge cell of a window). The north wing is the south wing mirrored on the axis.
# A turn in 128 and in 120 ticks: neither is a whole number of pairs of vanes further after two seconds, so two
# pictures taken two seconds apart are never the same, and the two of a wing drift out of step.
SET = ((20, "", 128, 0.0), (24, "_small", 120, 22.5))
TURN = -1                       # clockwise seen from above: the vanes' outer edges trail, as the wind turns such a head


def stack_model(size):
    return PREFIX + "cowl" + size


def head_model(size):
    return PREFIX + "cowl" + size + "_head"


def head_foot(size):
    """Where the head's lower face rides on the spindle, in pixels over the shaft's foot."""
    return SIZES[size]["top"] + COLLAR_UP + BEARING


def head_high(size):
    """The head's height, in pixels: hoops, vanes, cone and oil cup."""
    k = SIZES[size]
    return HOOP_UP + k["vane"] + 0.75 + BRIM_UP + k["cap"][1] + OILER_UP + 0.4


def mirror(z):
    """The row of the north wing that answers row z of the south wing: the building's axis is z 0.5."""
    return -z


def cowls():
    """The ventilators, as [dict]: `at` the foot's middle (x, y, z) in the building's coordinates,
    `size` ("" the big one, "_small"), `period` (ticks of one turn of the head, negative: clockwise
    seen from above), `yaw` (degrees the head is placed turned), `head` (the y its head begins at),
    `top` (the y of its tip), `cell` (x, z) of the slate it stands on."""
    out = []
    for s in sorted(roof.WINGS.values()):
        for row, size, period, yaw in SET:
            z = row if s > 0 else mirror(row)
            foot = roof._slate_top(COLUMN, z)
            head = foot + head_foot(size) / 16.0
            out.append({"at": (COLUMN + 0.5, foot, z + 0.5), "size": size, "period": TURN * period, "yaw": yaw,
                        "head": head, "top": head + head_high(size) / 16.0, "cell": (COLUMN, z)})
    return out


def _decal(m, face, lo, hi, sprite):
    """A picture on a face as thin as paper: the box lo..hi shows `sprite` on `face` and nothing else."""
    m.box(lo, hi, sprite, skip="".join(f for f in "nsewud" if f != face), seed=0, shade=False)


def _stack(size):
    k = SIZES[size]
    on, r, top, damper = (0.0, 0.0), k["shaft"], k["top"], k["damper"]
    m = M.Model(stack_model(size))
    # the foot: the lead apron with its rolled edges, the flange bolted down through it, the curb
    out = r + APRON_OUT
    m.box((-out, 0.0, -out), (out, APRON_UP, out), LEAD, skip="d")
    for s in (-1.0, 1.0):
        m.box((-out, APRON_UP, s * out), (out, APRON_UP + 0.3, s * (out - 0.6)), WELT)
        m.box((s * out, APRON_UP, -out + 0.6), (s * (out - 0.6), APRON_UP + 0.3, out - 0.6), WELT)
    flange = APRON_UP + FLANGE_UP
    m.tube("y", on, APRON_UP, flange, r + FLANGE_OUT, BAND)
    m.tube("y", on, flange, flange + CURB_UP, r + CURB_OUT, BAND)
    for n in range(8):
        with m.turned(("y", 45.0 * n)):
            m.box((r + CURB_OUT + 0.15, flange, -0.5), (r + FLANGE_OUT - 0.1, flange + 0.5, 0.5), K.RIVET)
    # the shaft: its sheets, a lap band on each joint with a rivet on every flat, the stay band
    m.tube("y", on, flange + CURB_UP, top, r, SHEET)
    stay = top - STAY_UNDER
    for y in tuple(k["bands"]) + (stay,):
        m.tube("y", on, y, y + BAND_UP, r + BAND_OUT, BAND)
        for n in range(8):
            with m.turned(("y", 45.0 * n)):
                K.rivet(m, (r + BAND_OUT, y + BAND_UP / 2.0, 0.0), out="x")
    # the upright seam on the east flat, riveted down its length, clear of the bands
    m.box((r, flange + CURB_UP, -SEAM[0] / 2.0), (r + SEAM[1], top, SEAM[0] / 2.0), SHEET, skip="w")
    y = flange + CURB_UP + SEAM_PITCH / 2.0
    while y < top - 0.5:
        if not any(b - 1.0 < y < b + BAND_UP + 1.0 for b in tuple(k["bands"]) + (stay,)) and abs(y - damper) > 1.2:
            K.rivet(m, (r + SEAM[1], y, 0.0), out="x", proud=0.35)
        y += SEAM_PITCH
    # the damper: its spindle through the shaft, a quadrant on the west flat, the lever and its grip
    m.box((-r - 0.9, damper - 0.5, -0.5), (r + 0.9, damper + 0.5, 0.5), STEEL, skip="")
    m.box((-r - 0.4, damper - 2.25, -2.0), (-r, damper + 2.25, 2.0), BAND, skip="e")
    for dy in (-1.6, 1.6):
        K.rivet(m, (-r - 0.4, damper + dy, -1.25), out="-x", proud=0.3)
    m.beam((-r - 0.75, damper, 0.0), (-r - 0.75, damper - 3.4, 2.3), 0.5, 0.8, K.IRON_D)
    m.box((-r - 1.25, damper - 4.4, 1.9), (-r - 0.25, damper - 3.1, 2.9), GRIP)
    # the storm collar and its wired edge; the spindle the head rides on
    m.taper("y", on, top, top + COLLAR_UP, r, r + COLLAR_OUT, BAND, steps=2)
    m.ring("y", (0.0, top + COLLAR_UP - 0.25, 0.0), r + COLLAR_OUT - 0.1, 0.6, 0.5, WELT)
    m.tube("y", on, top + COLLAR_UP - 0.5, top + COLLAR_UP + SPINDLE_UP, SPINDLE_R, STEEL, sides=4)
    # four stays from the stay band to eyes bolted through the slates: the roof steps up to the west and down to the east
    ring = stay + BAND_UP / 2.0
    for (dx, dz), drop in (((0.0, -1.0), 0.0), ((0.0, 1.0), 0.0), ((1.0, 0.0), -STEP), ((-1.0, 0.0), STEP)):
        far = STAY_OUT if drop <= 0.0 else STAY_OUT - 2.0
        a = (dx * (r + BAND_OUT), ring, dz * (r + BAND_OUT))
        b = (dx * far, drop + 0.5, dz * far)
        m.rod(a, b, STAY_R, ROD, sides=4)
        m.box((b[0] - 1.0, drop, b[2] - 1.0), (b[0] + 1.0, drop + 0.4, b[2] + 1.0), BAND, skip="d")
        K.rivet(m, (b[0] + 0.6 * dz, drop + 0.4, b[2] + 0.6 * dx), out="y", proud=0.4)
    # what the years have left: oil run down the lee side from the bearing, rust washed off the flange over the
    # lead, down the slate's edge and out over the next slate, and the fitter's chalk tick over the damper
    _decal(m, "s", (-1.5, top - 11.0, r + 0.05), (1.5, top, r + 0.3), OIL_RUN)
    _decal(m, "u", (r + FLANGE_OUT - 0.2, APRON_UP + 0.05, -2.5), (out - 0.2, APRON_UP + 0.3, 2.5), RUST_FOOT)
    _decal(m, "e", (out + 0.02, -STEP, -1.5), (out + 0.27, 0.0, 1.5), RUST_RISER)
    _decal(m, "u", (out, -STEP + 0.05, -2.0), (out + 7.0, -STEP + 0.3, 2.0), RUST_RUN)
    for y in k["bands"]:
        _decal(m, "s", (-1.5, y - 3.0, r + 0.05), (1.5, y, r + 0.3), WEEP)
    with m.turned(("y", 45.0)):                             # on the flat next to the damper's
        _decal(m, "w", (-r - 0.3, damper - 1.5, -2.0), (-r - 0.05, damper + 1.5, 2.0), TICK)
    return K.settle(m)


def _head(size):
    k = SIZES[size]
    on, hoop, high = (0.0, 0.0), k["hoop"], HOOP_UP + k["vane"]
    eaves = high + 0.75                                     # the upper hoop's top, the cone's eaves
    cap_r, cap_up = k["cap"]
    h = M.Model(head_model(size))
    for y0, y1 in ((0.0, HOOP_UP), (high - 0.25, eaves)):
        h.ring("y", (0.0, (y0 + y1) / 2.0, 0.0), hoop, HOOP_THICK, y1 - y0, HOOP)
    # the hub on the spindle and the two arms that carry the lower hoop
    h.tube("y", on, 0.0, eaves, HUB_R, HUB, sides=4)
    h.box((-hoop, 0.0, -0.6), (hoop, 0.6, 0.6), HUB)
    h.box((-0.6, 0.0, -hoop), (0.6, 0.6, hoop), HUB)
    # the vanes: their outer edges, which meet the wind, are worn bright
    off = VANE_OFF * hoop
    tip = math.sqrt((hoop + HOOP_THICK / 2.0 + VANE_PROUD) ** 2 - off ** 2)
    for n in range(VANE_N):
        h.box((VANE_IN * hoop, HOOP_UP, off - VANE_THICK / 2.0), (tip, high, off + VANE_THICK / 2.0), VANES[n % 2],
              rot=("y", 360.0 * n / VANE_N, (0.0, 0.0, 0.0)), grain="y", faces={"e": WORN})
    # the cone: its rolled eaves, eight gores, a standing seam over each joint, the oil cup on top
    h.tube("y", on, eaves, eaves + BRIM_UP, cap_r, CAP)
    h.taper("y", on, eaves + BRIM_UP, eaves + BRIM_UP + cap_up, cap_r, CAP_TOP_R, CAP, steps=CAP_STEPS)
    rise = cap_up / CAP_STEPS
    for n in range(8):
        with h.turned(("y", 22.5 + 45.0 * n)):
            h.beam((cap_r * 1.05, eaves + BRIM_UP + 0.2, 0.0), (CAP_TOP_R + 0.4, eaves + BRIM_UP + cap_up + rise * 0.6, 0.0),
                   0.5, 0.5, CAP)
    top = eaves + BRIM_UP + cap_up
    h.tube("y", on, top, top + OILER_UP, OILER_R, OILER, sides=4)
    h.box((-OILER_R - 0.3, top + OILER_UP, -OILER_R - 0.3), (OILER_R + 0.3, top + OILER_UP + 0.4, OILER_R + 0.3), GRIP)
    return K.settle(h)


@functools.lru_cache(maxsize=None)
def _models():
    out = {}
    for size in SIZES:
        for m in (_stack(size), _head(size)):
            out[m.name] = m
    return out


def models():
    return dict(_models())


def build(canvas, origin=(0, 0, 0)):
    """Stand the ventilators on the slates and hand their heads to the motion line. Returns the
    display entities placed."""
    kit = _models()
    ox, oy, oz = origin
    n = 0
    for c in cowls():
        x, y, z = c["at"]
        canvas.add_entity(ox + x, oy + y, oz + z, M.display(kit[stack_model(c["size"])], view=VIEW))
        canvas.add_entity(ox + x, oy + c["head"], oz + z, M.display(kit[head_model(c["size"])], yaw=c["yaw"], view=VIEW))
        MK.spin(canvas, "y", c["period"])
        n += 2
    return n


# --- the self-check -------------------------------------------------------------------------------------
def check(c=None):
    """What the package promises, read off the built main line; a list of what is wrong."""
    from .. import main

    if c is None:
        c = Canvas()
        main.build(c)
    out = []
    way = {(x, z) for s in roof.WINGS.values() for x, z, _feet in roof.route(s)}
    guard = {(x, z) for x, _y, z in roof.guard()}
    terraces = {col for cols in roof.terraces().values() for col in cols}
    for k in cowls():
        x, z = k["cell"]
        _fx, foot, _fz = k["at"]
        what = f"the ventilator at ({x}, {z})"
        if not roof.ROOF_IN < abs(z) <= roof.ROOF_OUT or x in roof.RIDGE:
            out.append(f"{what} does not stand on a wing's slates")
        if (x, z) in way or (x, z) in terraces:
            out.append(f"{what} stands on the visitors' way")
        if (x, z) in guard or any((x + dx, z) in guard for dx in (-1, 1)):
            out.append(f"{what} stands on or against the parapet")
        if not c.has(x, int(foot) - 1, z) or any(c.has(x, y, z) for y in range(int(foot), int(k["top"]) + 2)):
            out.append(f"{what}: no slate under it at {foot:g}, or a block where it stands")
        for (dx, dz), want in (((-1, 0), STEP), ((1, 0), -STEP), ((0, -1), 0.0), ((0, 1), 0.0)):
            if abs((roof._slate_top(x + dx, z + dz) - foot) * 16.0 - want) > 1e-6:
                out.append(f"{what}: the slate at ({x + dx}, {z + dz}) does not lie {want:+g} pixels from its foot: "
                           f"a stay's eye or the rust's run is off the roof")
        if k["top"] > S.DRUM[1] - 1:
            out.append(f"{what} reaches {k['top']:.2f}, over the drum's cornice")
    for name, m in _models().items():
        if K.unsettled(m):
            out.append(f"{name}: {len(K.unsettled(m))} faces lie between two axes")
    placed = [e for e in c.entities if M.shown_model(e[3]) in _models()]
    if len(placed) != 2 * len(cowls()):
        out.append(f"{len(placed)} display entities of the ventilators stand, not {2 * len(cowls())}")
    return out


if __name__ == "__main__":
    if sys.argv[1:] == ["check"]:
        problems = check()
        for line in problems:
            print("FAIL " + line)
        print("self-check: " + ("%d wrong" % len(problems) if problems else
                                "%d ventilators on the slates, off the way and the parapets, under the drum's cornice"
                                % len(cowls())))
        sys.exit(1 if problems else 0)
    for k in cowls():
        print(k)
