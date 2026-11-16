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

from ..common import skeleton as S
from ..motion import _kit as MK
from ..props import _kit as K
from . import roof

ORDER = 75                      # after the roofs' own package (70): the ventilators stand on its slates

PREFIX = "bld_roof_"
VIEW = M.MID                    # drawn up to 64 blocks away: from the court, the terraces and the roofs (V2, V5, V11),
#                                 not from the station or the far lookout, whose views are full (the line of 600)

SHEET = K.IRON_D                # the shaft's sheet iron
BAND = K.IRON                   # its lap bands, the curb and the storm collar: what takes the light
APRON = K.flat("iron", 1)       # the lead dressed over the slates round its foot
VANES = (K.IRON, K.IRON_D)      # the head's vanes, light and dark by turns: a turning head is seen to turn
HOOP = K.IRON
HUB = K.IRON_D
CAP = K.COPPER_D                # the head's low cone: copper gone green, as the domes it stands between
OILER = K.BRASS_D               # the oil cup over the head's bearing

# The two sizes, in pixels (a display entity is never scaled: 16 pixels to the block everywhere).
#   shaft     its radius (over the flats) and its top, from the foot
#   bands     where a lap band begins: the joints of the shaft's sheets
#   hoop      the radius of the head's two hoops
#   vane      how high a vane is
#   cap       the cone's radius at its eaves and its height
SIZES = {
    "": dict(shaft=5.0, top=27.0, bands=(9.0, 18.0), hoop=10.0, vane=10.0, cap=(11.5, 4.0)),
    "_small": dict(shaft=4.0, top=21.0, bands=(10.5,), hoop=8.0, vane=8.0, cap=(9.25, 3.25)),
}
APRON_OUT, APRON_UP = 3.0, 1.0  # the apron: this far beyond the shaft, this thick
CURB_OUT, CURB_UP = 1.5, 2.5    # the curb the shaft stands in
BAND_OUT, BAND_UP = 0.5, 1.5
COLLAR_OUT, COLLAR_UP = 2.0, 2.0                # the storm collar: a cone that sheds the rain past the shaft's mouth
SPINDLE_R, SPINDLE_UP = 0.75, 4.0
BEARING = 1.5                   # the gap between the collar and the head: the spindle is seen in it
HOOP_THICK, HOOP_UP = 1.5, 1.5
HUB_R = 1.25
VANE_N = 8
VANE_IN, VANE_THICK, VANE_OFF = 0.25, 0.8, 0.54 # a vane is a plate along a chord, this share of the hoop's radius off the
#                                                 axis, and begins this share of it from the chord's middle: it stands
#                                                 slanted to the wind, its outer edge trailing, and the head is hollow
VANE_PROUD = 0.5                # how far a vane's outer edge stands out of the hoops
CAP_TOP_R = 2.0
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
    return HOOP_UP + k["vane"] + 0.75 + k["cap"][1] + OILER_UP


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


def _stack(size):
    k = SIZES[size]
    on, r, top = (0.0, 0.0), k["shaft"], k["top"]
    m = M.Model(stack_model(size))
    m.box((-r - APRON_OUT, 0.0, -r - APRON_OUT), (r + APRON_OUT, APRON_UP, r + APRON_OUT), APRON, skip="d")
    m.tube("y", on, APRON_UP, CURB_UP, r + CURB_OUT, BAND)
    m.tube("y", on, CURB_UP, top, r, SHEET)
    for y in k["bands"]:
        m.tube("y", on, y, y + BAND_UP, r + BAND_OUT, BAND)
        for out, p in (("x", (r + BAND_OUT, 0.0)), ("-x", (-r - BAND_OUT, 0.0)), ("z", (0.0, r + BAND_OUT)),
                       ("-z", (0.0, -r - BAND_OUT))):
            K.rivet(m, (p[0], y + BAND_UP / 2.0, p[1]), out=out)
    m.taper("y", on, top, top + COLLAR_UP, r, r + COLLAR_OUT, BAND, steps=2)
    m.tube("y", on, top + COLLAR_UP, top + COLLAR_UP + SPINDLE_UP, SPINDLE_R, SHEET, sides=4)
    return K.settle(m)


def _head(size):
    k = SIZES[size]
    on, hoop, high = (0.0, 0.0), k["hoop"], HOOP_UP + k["vane"]
    eaves = high + 0.75                                     # the upper hoop's top, the cone's eaves
    h = M.Model(head_model(size))
    for y0, y1 in ((0.0, HOOP_UP), (high - 0.25, eaves)):
        h.ring("y", (0.0, (y0 + y1) / 2.0, 0.0), hoop, HOOP_THICK, y1 - y0, HOOP)
    h.tube("y", on, 0.0, eaves, HUB_R, HUB, sides=4)
    off = VANE_OFF * hoop
    tip = math.sqrt((hoop + HOOP_THICK / 2.0 + VANE_PROUD) ** 2 - off ** 2)
    for n in range(VANE_N):
        h.box((VANE_IN * hoop, HOOP_UP, off - VANE_THICK / 2.0), (tip, high, off + VANE_THICK / 2.0), VANES[n % 2],
              rot=("y", 360.0 * n / VANE_N, (0.0, 0.0, 0.0)), grain="y")
    h.taper("y", on, eaves, eaves + k["cap"][1], k["cap"][0], CAP_TOP_R, CAP, steps=3)
    h.tube("y", on, eaves + k["cap"][1], eaves + k["cap"][1] + OILER_UP, OILER_R, OILER, sides=4)
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
