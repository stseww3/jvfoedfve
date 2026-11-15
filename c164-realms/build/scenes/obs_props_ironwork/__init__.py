"""Test scene of the work package props/ironwork: the family on a piece of the real wall.

The wall is not a stand-in: eight bays of the entrance front, laid by A3's elevation grammar
(main/_order) with the main building's own order (main/facade.order()) on a straight plan, looking
east like the front itself. In the middle the three arches of the entrance; the iron is put on by
the same two functions that dress the master scene (ironwork.windows, ironwork.doors), from tables
of the same form as main/_plan gives.

Seen from the court, left to right (south to north):

    bay 8   the control: a lit great window WITHOUT a frame; below it the grille as a model
    bay 7   the same window framed; below it the base window as A3 builds it, bars as blocks
    bay 6   a side arch of the entrance: the gate, shut
    bay 5   the entrance: frame and fanlight, the leaves open against the reveals, the canopy on
            the two pilasters and its lamp; the brightest window above it, framed
    bay 4   the other gate
    bay 3   a curtained window framed, the grille as a model
    bay 2   a dark window framed, the bars as blocks
    bay 1   an end pavilion's two-wide window with the two-wide frame and grille

South of the building a plain yard wall carries what has no place on the front: the west door's
glazed leaves in a flat-headed doorway and the inspection ladder; on the paving stand a run of
balustrade panels, the vent cowl and the floor grating.

The shots are written from the numbers below:  python -m scenes.obs_props_ironwork
"""
from artkit.blocks import st
from artkit.canvas import Canvas

from scenes.obs import materials, sky
from scenes.obs.common import blocks as B
from scenes.obs.common import skeleton as S
from scenes.obs.main import _order as O
from scenes.obs.main import facade
from scenes.obs.props import ironwork
from scenes.obs.site import _kit as site

BIOME = "obs_blue"
BIOME_MARGIN = 32
BIOME_MARGIN_Y = 32
TIME = 14000                    # light version A, the default (INTERFACE: 18000 is B, 12900 is C)

# ---- the plan: plan coordinates are scene coordinates, clear of the rotunda the order leaves out ----
WALL = 40                       # the wall line; the front's face is the plane x = WALL + 1
BACK = WALL - 6                 # the back of the body: a leaf either side of rooms three deep
Z0, BAYS = -18, 8               # the north corner; pilasters every S.BAY from it
Z1 = Z0 + S.BAY * BAYS
NARROW = 1                      # an end pavilion's bay: its first column belongs to the broad pier
GATES, DOOR = (4, 6), 5         # the three arches of the entrance, as bays 8 to 10 of the front
CONTROL = 8                     # the great window left without a frame
MODEL_GRILLES = (1, 3, 8)       # base windows that get the grille as a model; the others keep A3's bars
ARCH_TOP = S.BASE[1]            # the arches of the entrance are six high: y 0..5

# which glass stands in a bay (the light line's letters): main storey, base storey
MAIN = {1: "O", 2: "D", 3: "K", 4: "K", 5: "L", 6: "K", 7: "O", 8: "O"}
BASE = {1: "O", 2: "D", 3: "K", 7: "O", 8: "O"}
GLOW = {B.WINDOW_LIT.block: 10, B.WINDOW_FROSTED.block: 10, B.WINDOW_CURTAIN.block: 9}   # as materials/windows
HALL_LAMP = 12                  # the hall behind the entrance

# ---- the yard south of the building ----------------------------------------------------------------
YARD = (Z1 + 5, Z1 + 15)        # the yard wall's z, one block thick on the wall line, YARD_TOP high
YARD_TOP = 8
WEST_DOOR = YARD[0] + 3         # the middle column of the flat-headed doorway (three wide, y 0..3)
LADDER_Z = YARD[0] + 7          # the column the ladder climbs
FLOOR_X = WALL + 12             # the cowl and the grating stand out here, clear of the wall's shots
COWL_Z, GRATE_Z = YARD[0] + 6, YARD[0] + 2
RAIL_Z = YARD[1] + 3            # the balustrade run, looking south
RAIL_X = (WALL + 5, WALL + 7, WALL + 9)


def bay_z(bay):
    """The columns of a bay, north to south."""
    z = Z0 + S.BAY * (bay - 1)
    return list(range(z + (2 if bay == NARROW else 1), z + S.BAY))


def mid_z(bay):
    """The middle of a bay's opening, as a point."""
    zs = bay_z(bay)
    return S.mid(zs[0], zs[-1])


def _classify(x, z, outs):
    if len(outs) != 1:
        return O.Pier()
    if outs[0] != "east":
        return None
    k, rest = divmod(z - Z0, S.BAY)
    if rest == 0:
        return O.Pier()
    if k + 1 == NARROW and rest == 1:
        return O.Pier(crest=False)
    return O.Bay("east", k + 1)


def _glass(front, bay, storey):
    return facade.GLASS.get({"main": MAIN, "base": BASE}[storey].get(bay))


def plan():
    p = O.Plan(O.box(BACK, Z0, WALL, Z1), _classify)
    for bay in GATES + (DOOR,):
        p.door("east", bay, S.GROUND, ARCH_TOP, arch=B.ASHLAR_ROUGH)
    return p


def door_table():
    """The doorways, in the form of main/_plan.doors(): the three arches and the yard's west door."""
    out = [dict(front="east", bay=bay, cells=[(WALL, z) for z in bay_z(bay)], inward=(-1, 0),
                y=(S.GROUND, ARCH_TOP), arch=True, kind="door" if bay == DOOR else "gate")
           for bay in sorted(GATES + (DOOR,))]
    out.append(dict(front="yard", bay=0, cells=[(WALL, WEST_DOOR + d) for d in (-1, 0, 1)], inward=(-1, 0),
                    y=(S.GROUND, 3), arch=False, kind="door"))
    return out


def _rooms(c, windows):
    """What stands behind the wall: a room to each bay, so a lit window lights its own frame and
    not its neighbour's; the hall behind the three arches; a floor under the main storey and a
    deck over it. The lamps behind lit glass are the ones materials/windows sets, until the light
    line places its own."""
    fine, rough = B.ASHLAR_FINE.block, B.ASHLAR_ROUGH.block
    hall = (Z0 + S.BAY * (min(GATES) - 1), Z0 + S.BAY * max(GATES))         # the pilaster lines that bound it
    c.box(BACK + 2, S.STRING, Z0 + 2, WALL - 2, S.STRING, Z1 - 2, fine)
    c.box(BACK + 1, S.ROOF_FLOOR, Z0 + 1, WALL - 1, S.ROOF_FLOOR, Z1 - 1, facade.DECK)
    for z in range(Z0 + S.BAY, Z1, S.BAY):
        inside = hall[0] < z < hall[1]
        c.box(BACK + 2, S.STRING if inside else S.GROUND, z, WALL - 2, S.ROOF_FLOOR - 1, z, rough if not inside else fine)
    for w in windows:
        level = GLOW.get(w["glass"])
        if level:
            x, z = w["cells"][len(w["cells"]) // 2]
            y0, y1 = w["y"]
            for y in ((y0 + 1, y1 - 1) if y1 - y0 > 2 else (y0,)):
                c.set(x + w["inward"][0], y, z + w["inward"][1], st(B.LIGHT, level=level))
    c.set(WALL - 3, 3, 0, st(B.LIGHT, level=HALL_LAMP))
    for y, name in ((1, "fuses"), (2, "gauges")):       # two of materials/panels behind the open door: one iron
        c.set(BACK + 1, y, 0, st(B.PANELS[name], facing="east"))


def _yard(c):
    """The yard wall with its flat-headed doorway, and the pieces that stand on the paving."""
    c.box(WALL, S.GROUND, YARD[0], WALL, YARD_TOP, YARD[1], B.ASHLAR_FINE.block)
    c.carve(WALL, S.GROUND, WEST_DOOR - 1, WALL, 3, WEST_DOOR + 1)
    n = ironwork.ladder(c, (WALL + 1.0, float(S.GROUND), LADDER_Z + 0.5), 3, facing="east")
    for x in RAIL_X:
        n += ironwork.place(c, "railing_panel", (float(x), float(S.GROUND), RAIL_Z + 0.5), facing="south")
    n += ironwork.place(c, "vent_cowl", (FLOOR_X + 0.5, float(S.GROUND), COWL_Z + 0.5), facing="east")
    n += ironwork.place(c, "grate_hatch", (FLOOR_X + 0.5, float(S.GROUND), GRATE_Z + 0.5))
    return n


def build():
    c = Canvas()
    c.box(BACK - 2, S.GROUND - 1, Z0 - 6, WALL + 30, S.GROUND - 1, RAIL_Z + 5, site.FIELD)
    c.box(WALL + 3, S.GROUND - 1, Z0 - 6, WALL + 3, S.GROUND - 1, RAIL_Z + 5, site.STRIP)
    p = plan()
    windows = O.build(c, p, facade.order(), glass=_glass)
    for bay in GATES + (DOOR,):                         # A3's B entrance: a whole stone in the course over each arch
        c.set(WALL + 1, S.STRING, bay_z(bay)[1], B.ASHLAR_FINE.block)
    _rooms(c, windows)
    framed = [w for w in windows if not (w["storey"] == "main" and w["bay"] == CONTROL)]
    n = ironwork.windows(c, framed, grilles=lambda w: w["bay"] in MODEL_GRILLES)
    n += ironwork.doors(c, door_table())
    n += _yard(c)
    sky.build(c, (0, 0, 0))             # A2's light sources go in last, when every piece is in place
    c.entity_counts = {"props": n}
    return c


def write_pack(pack_dir):
    """The repainted stone and glass the ironwork is judged against."""
    return materials.pack(pack_dir)


def shots():
    """The cameras. The wall's own shots stand east of it and look west, as the court sees the front."""
    out = []

    def shot(name, pos, look_at):
        out.append({"name": name, "pos": [round(v, 2) for v in pos],
                    "look_at": [round(v, 2) for v in look_at], "time": TIME})

    face = WALL + 1.0                                   # the plane of the wall's face
    pair = S.mid(Z0 + S.BAY * (CONTROL - 1))            # the pilaster between the framed and the bare window
    win = S.mid(*S.WINDOW)                              # the middle height of a great window
    f, d, g, e = mid_z(7), mid_z(2), mid_z(max(GATES)), mid_z(DOOR)
    shot("front", (face + 27.0, 6.0, e - 2.0), (face, 6.5, e - 2.0))
    shot("bays_front", (face + 20.0, win - 2.0, pair), (face, win - 2.0, pair))
    shot("bays_near", (face + 6.0, win, pair), (face - 1.0, win, pair))
    shot("bays_oblique", (face + 6.5, win - 1.0, pair - 7.0), (face - 1.0, win, pair + 0.5))
    shot("frame_head", (face + 3.5, S.WINDOW[1] - 0.5, f), (face - 1.0, S.WINDOW[1] - 0.6, f))
    shot("frame_foot", (face + 2.6, S.WINDOW[0] + 1.6, f - 2.0), (face - 1.0, S.WINDOW[0] + 0.8, f + 0.6))
    shot("frame_dark", (face + 6.0, win, d), (face - 1.0, win, d))
    shot("narrow", (face + 7.0, 7.0, mid_z(NARROW)), (face - 1.0, 7.0, mid_z(NARROW)))
    shot("grilles", (face + 6.0, 3.6, pair), (face - 1.0, 4.0, pair))
    shot("grille_near", (face + 2.6, 4.3, pair - 0.5), (face - 1.0, 4.0, mid_z(CONTROL)))
    shot("entrance", (face + 15.0, 3.2, e), (face, 4.4, e))
    shot("entrance_oblique", (face + 9.0, 1.7, e + 9.0), (face, 3.8, e))
    shot("leaf_near", (face + 3.0, 2.0, e + 1.0), (face + 0.2, 2.2, e - 1.3))
    shot("fanlight_near", (face + 3.6, 4.2, e), (face - 1.0, 5.0, e))
    shot("canopy_below", (face + 5.6, 1.7, e + 3.2), (face + 2.2, 6.9, e - 0.4))
    shot("canopy_side", (face + 2.6, 5.2, e + 8.5), (face + 2.6, 5.6, e))
    shot("gate_near", (face + 4.6, 2.4, g + 1.6), (face - 1.0, 2.8, g))
    shot("west_door", (face + 5.5, 2.2, WEST_DOOR + 0.5), (face - 1.0, 2.0, WEST_DOOR + 0.5))
    shot("ladder", (face + 8.0, 4.6, LADDER_Z + 0.5), (face, 4.6, LADDER_Z + 0.5))
    shot("ladder_up", (face + 2.4, 1.7, LADDER_Z + 2.6), (face + 0.4, 6.2, LADDER_Z + 0.5))
    shot("railing", (RAIL_X[1], 1.6, RAIL_Z + 4.5), (RAIL_X[1], 0.8, RAIL_Z + 0.5))
    shot("vent", (FLOOR_X + 3.0, 1.5, COWL_Z + 2.4), (FLOOR_X + 0.5, 0.9, COWL_Z + 0.5))
    shot("grate", (FLOOR_X + 2.2, 1.9, GRATE_Z + 2.2), (FLOOR_X + 0.5, 0.1, GRATE_Z + 0.5))
    return out
