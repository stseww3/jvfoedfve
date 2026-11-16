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
                    the big one, the outer one four fifths of it, and they turn at their own pace.
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
import sys

from artkit import models as M
from artkit.canvas import Canvas

from ..common import skeleton as S
from ..motion import _kit as MK
from ..props import _kit as K
from . import roof

ORDER = 75                      # after the roofs' own package (70): the ventilators stand on its slates

PREFIX = "bld_roof_"
STACK_MODEL = PREFIX + "cowl"
HEAD_MODEL = PREFIX + "cowl_head"
FAR = 4.0                       # view_range: part of the skyline, as the clock tower's mast

SHEET = K.IRON_D                # the shaft's sheet iron
BAND = K.IRON                   # its lap bands, the curb and the storm collar: what takes the light
APRON = K.flat("iron", 1)       # the lead dressed over the slates round its foot
VANES = (K.IRON, K.IRON_D)      # the head's vanes, light and dark by turns: a turning head is seen to turn
HOOP = K.IRON
CAP = K.IRON_D

# the shaft, in pixels from its foot
APRON_HALF, APRON_UP = 6.5, 1.0
CURB_R, CURB_UP = 5.0, 2.5
SHAFT_R = 3.5
SHAFT_TOP = 35.0
BANDS = (12.0, 24.0)            # the lap joints of its three sheets: where a band begins
BAND_R, BAND_UP = 4.0, 1.5
COLLAR_R, COLLAR_UP = 5.5, 2.0  # the storm collar: a cone that sheds the rain past the shaft's mouth
SPINDLE_R, SPINDLE_UP = 0.75, 4.0
HEAD_FOOT = SHAFT_TOP + COLLAR_UP + 1.5        # 38.5: where the head's lower hoop rides on the spindle

# the head, in pixels from its lower face; it turns about y through its anchor
VANE_N = 8
VANE = ((1.5, 1.5, 3.1), (6.8, 10.0, 3.9))     # one vane: a plate along a chord, so that it stands slanted to the wind
HOOP_R, HOOP_THICK = 6.5, 1.5
HOOP_LOW, HOOP_HIGH = (0.0, 1.5), (9.75, 10.75)
HUB_R = 1.25
CAP_R, CAP_TOP_R, CAP_Y = 7.75, 2.0, (10.75, 13.75)
FINIAL_R, FINIAL_TOP = 0.9, 15.5
HEAD_HIGH = FINIAL_TOP

COLUMN = S.WALL_E - 3           # 12: the column they stand in, the third of the east slope from the parapet
# (|z| of its row, scale, ticks of one turn, degrees it is placed turned): the wing's inner one and its outer one,
# on the window axes of two neighbouring bays (c321: never on the edge cell of a window).
# A turn in 128 and in 120 ticks: neither is a whole number of vanes further after two seconds, so
# two pictures taken two seconds apart are never the same, and the two of a wing drift out of step.
SET = ((20, 1.0, 128, 0.0), (24, 0.8, 120, 22.5))


def cowls():
    """The ventilators, as [dict]: `at` the foot's middle (x, y, z) in the building's coordinates,
    `scale`, `period` (ticks of one turn of the head), `yaw` (degrees the head is placed turned),
    `top` (the y of the finial's tip), `cell` (x, z) of the slate it stands on."""
    out = []
    for s in sorted(roof.WINGS.values()):
        for az, scale, period, yaw in SET:
            z = s * az
            foot = roof._slate_top(COLUMN, z)
            out.append({"at": (COLUMN + 0.5, foot, z + 0.5), "scale": scale, "period": period * (1 if s > 0 else -1),
                        "yaw": yaw, "top": foot + scale * (HEAD_FOOT + HEAD_HIGH) / 16.0, "cell": (COLUMN, z)})
    return out


@functools.lru_cache(maxsize=None)
def _models():
    on = (0.0, 0.0)
    m = M.Model(STACK_MODEL)
    m.box((-APRON_HALF, 0.0, -APRON_HALF), (APRON_HALF, APRON_UP, APRON_HALF), APRON, skip="d")
    m.tube("y", on, APRON_UP, CURB_UP, CURB_R, BAND)
    m.tube("y", on, CURB_UP, SHAFT_TOP, SHAFT_R, SHEET)
    for y in BANDS:
        m.tube("y", on, y, y + BAND_UP, BAND_R, BAND)
        for out, p in (("x", (BAND_R, 0.0)), ("-x", (-BAND_R, 0.0)), ("z", (0.0, BAND_R)), ("-z", (0.0, -BAND_R))):
            K.rivet(m, (p[0], y + BAND_UP / 2.0, p[1]), out=out)
    m.taper("y", on, SHAFT_TOP, SHAFT_TOP + COLLAR_UP, SHAFT_R, COLLAR_R, BAND, steps=2)
    m.tube("y", on, SHAFT_TOP + COLLAR_UP, SHAFT_TOP + COLLAR_UP + SPINDLE_UP, SPINDLE_R, SHEET, sides=4)

    h = M.Model(HEAD_MODEL)
    for y0, y1 in (HOOP_LOW, HOOP_HIGH):
        h.ring("y", (0.0, (y0 + y1) / 2.0, 0.0), HOOP_R, HOOP_THICK, y1 - y0, HOOP)
    h.tube("y", on, HOOP_LOW[0], CAP_Y[0], HUB_R, CAP, sides=4)
    for k in range(VANE_N):
        h.box(VANE[0], VANE[1], VANES[k % 2], rot=("y", 360.0 * k / VANE_N, (0.0, 0.0, 0.0)), grain="y")
    h.taper("y", on, CAP_Y[0], CAP_Y[1], CAP_R, CAP_TOP_R, CAP, steps=3)
    h.tube("y", on, CAP_Y[1], FINIAL_TOP, FINIAL_R, HOOP, sides=4)
    return {m.name: K.settle(m), h.name: K.settle(h)}


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
        canvas.add_entity(ox + x, oy + y, oz + z, M.display(kit[STACK_MODEL], scale=c["scale"], view=FAR))
        canvas.add_entity(ox + x, oy + y + c["scale"] * HEAD_FOOT / 16.0, oz + z,
                          M.display(kit[HEAD_MODEL], yaw=c["yaw"], scale=c["scale"], view=FAR))
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
    placed = [e for e in c.entities if str(e[3].get("item", {}).get("components", {}).get("minecraft:item_model", ""))
              .endswith((STACK_MODEL, HEAD_MODEL))]
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
