"""Test scene of the work package props/pipes: the pipework on a piece of the real wall.

The wall is not a stand-in. It is the south end of the main building's east front -- two bays of
the south wing, the end pavilion that stands a block forward of it with its broad corner pier, and
round the corner the first two bays of the south end wall -- laid by A3's elevation grammar
(main/_order) with the main building's own order (main/facade.order()) on the skeleton's own
columns. Plan coordinates are scene coordinates, so pipes.dress(), the function that dresses the
master scene, runs here unchanged and finds the same stones.

What it shows:

    the re-entrant corner (16, y, 25)   where the end pavilion stands forward of the wing: the copper
                                        downpipe from its hopper under the cornice, through the
                                        string course, into the plinth's coping; clipped to the
                                        pavilion's return
    the foot of the corner pier         the grating (17, 0, 33) where the power house's main goes
                                        into the building: the angle stop valve on the paving with
                                        its red handwheel to the court, the short length with the
                                        pressure gauge, the plate on the grating
    the plinth of the south end wall    a SAMPLE, which pipes.dress() does not place: the heating
                                        main in the smaller bore. It leaves the broad corner pier,
                                        lies on the plinth's coping under the base windows, goes
                                        through the pier between the two bays, passes a stop valve
                                        whose handwheel looks out from the wall, and turns into the
                                        wall before the next pier. It is here so that the pieces
                                        that have no place on the east front -- plates, flanges, a
                                        bracket, the straight valve, a bend -- are judged on the
                                        real stones and in a line that begins and ends

The two pieces for a main laid in whole blocks (bonnet, band) go on site/powerhouse's pipe bridge,
which is not in this scene; that package's test scenes show them there. gallery.py lays every model
out on its own (props.GALLERY).

The shots are written from the numbers below:  python -m scenes.obs_props_pipes
"""
from artkit.blocks import st
from artkit.canvas import Canvas

from scenes.obs import materials, sky
from scenes.obs.common import blocks as B
from scenes.obs.common import skeleton as S
from scenes.obs.main import _order as O
from scenes.obs.main import _plan as P
from scenes.obs.main import facade
from scenes.obs.props import pipes
from scenes.obs.site import _kit as site

BIOME = "obs_blue"
BIOME_MARGIN = 32
BIOME_MARGIN_Y = 32
TIME = 14000                    # light version A, the default (INTERFACE: 18000 is B, 12900 is C)

# ---- the plan: the skeleton's own columns ----------------------------------------------------------
Z0 = S.pilaster_z(13)           # 18: the stretch is cut on a pilaster line of the south wing
BACK = S.WALL_W + 2 * S.BAY     # 8: and on a pilaster line of the south end wall
PAVING = (BACK - 3, Z0 - 5, S.WALL_E + 27, S.Z_SOUTH + 24)      # x0, z0, x1, z1 of the terrace laid round it
GLOW = {B.WINDOW_LIT.block: 10, B.WINDOW_FROSTED.block: 10, B.WINDOW_CURTAIN.block: 9}   # as materials/windows

# ---- the sample line on the south end wall ---------------------------------------------------------
SIZE = "m"                                              # the heating main: the smaller of the two bores
LINE_Y = S.PLINTH[1] + 1 + pipes.STANDOFF[SIZE] / 16.0  # 2.25: its flanges stand on the plinth's coping
LINE_Z = S.Z_SOUTH + 1 + pipes.STANDOFF[SIZE] / 16.0    # 35.25: and touch the wall face
BEND_AT, CLIP_AT, VALVE_AT = 6.0, 17.0, 28.0            # texels east of the pier the stretch is cut on


def footprint():
    return {(x, z) for z in range(Z0, S.Z_SOUTH + 1) for x in range(BACK, P.east_face(z) + 1)}


def _classify(x, z, outs):
    """The east front and the south end wall as main/facade classifies them; the two sides where the
    stretch is cut out of the building are plain wall."""
    if "east" in outs:
        if z == S.Z_SOUTH:
            return O.Pier()                             # the corner: both ways, and the block between
        if P.on_pilaster(z):
            return O.Pier(out=("east",))                # also where the front steps: the return stays plain
        if z in P.END_PIER_ROWS:
            return O.Pier(out=("east",), crest=False)   # the end pavilion's broad corner pier
        return O.Bay("east", P.bays_at(z)[0])
    if z == S.Z_SOUTH and "south" in outs:
        if (x - S.WALL_W) % S.BAY == 0:
            return O.Pier(out=("south",))
        if x == P.east_face(z) - 1:
            return O.Pier(out=("south",), crest=False)
        return O.Bay("south", (x - S.WALL_W) // S.BAY + 1, out="south")
    return None


def plan():
    return O.Plan(footprint(), _classify)


def _rooms(c, windows):
    """What stands behind the wall: a room to each bay of the east front, so a lit window lights its
    own reveal and not its neighbour's; a floor under the main storey and a deck over it. The lamps
    behind lit glass are the ones materials/windows sets, until the light line places its own."""
    fine, rough = B.ASHLAR_FINE.block, B.ASHLAR_ROUGH.block
    for z in range(Z0 + 1, S.Z_SOUTH):
        for x in range(BACK + 1, P.east_face(z)):
            c.set(x, S.ROOF_FLOOR, z, facade.DECK)
    for z in range(Z0 + 2, S.Z_SOUTH - 1):
        cross = P.on_pilaster(z)
        for x in range(BACK + 2, P.east_face(z) - 1):
            c.set(x, S.STRING, z, fine)
            if cross:
                for y in range(S.GROUND, S.ROOF_FLOOR):
                    c.set(x, y, z, rough)
    for w in windows:
        level = GLOW.get(w["glass"])
        if level:
            x, z = w["cells"][len(w["cells"]) // 2]
            y0, y1 = w["y"]
            for y in ((y0 + 1, y1 - 1) if y1 - y0 > 2 else (y0,)):
                c.set(x + w["inward"][0], y, z + w["inward"][1], st(B.LIGHT, level=level))


def _heating(c):
    """The sample line on the south end wall (see the top of the file), east to west; returns the
    number of display entities. The piers it meets: the broad corner pier, whose west face is at
    x 15; the pier between the two bays, x 12..13; the pier the stretch is cut on, east face x 9."""
    y, z, wall = LINE_Y, LINE_Z, S.Z_SOUTH + 1.0
    west, mid, east = BACK + 1.0, float(BACK + S.BAY), P.east_face(S.Z_SOUTH) - 1.0
    main, plate = "main_" + SIZE, "plate_" + SIZE
    neck = (pipes.PLATE_NECK - 1.0) / 16.0              # a run starts this far inside a plate's neck,
    port = (pipes.VALVE[SIZE] - 1.0) / 16.0             # stops this far from the middle of a valve
    leg = (pipes.ELBOW[SIZE] - 1.0) / 16.0              # and from the corner of a bend: inside their flanges
    valve, bend = west + VALVE_AT / 16.0, west + BEND_AT / 16.0
    # the bay next to the corner: pier to pier, two lengths bolted together half way
    n = pipes.mount(c, plate, (east, y, z), out="west")
    n += pipes.run(c, (east - neck, y, z), (mid + 1.0 + neck, y, z), main)
    n += pipes.place(c, "flange_" + SIZE, ((east + mid + 1.0) / 2.0, y, z), along="west", out="up")
    n += pipes.mount(c, plate, (mid + 1.0, y, z), out="east")
    # the next bay: out of the pier, the stop valve, a bracket, the bend into the wall
    n += pipes.mount(c, plate, (mid, y, z), out="west")
    n += pipes.run(c, (mid - neck, y, z), (valve + port, y, z), main)
    n += pipes.place(c, "valve_" + SIZE, (valve, y, z), along="west", out="south")
    n += pipes.run(c, (valve - port, y, z), (bend + leg, y, z), main)
    n += pipes.mount(c, "clip_" + SIZE, (west + CLIP_AT / 16.0, y, wall), out="south")
    n += pipes.place(c, "elbow_" + SIZE, (bend, y, z), along="east", out="north")
    n += pipes.mount(c, plate, (bend, y, wall), out="south")
    return n


def build():
    c = Canvas()
    x0, z0, x1, z1 = PAVING
    c.box(x0, S.GROUND - 1, z0, x1, S.GROUND - 1, z1, site.FIELD)
    c.box(site.FOOT_STRIP_X, S.GROUND - 1, z0, site.FOOT_STRIP_X, S.GROUND - 1, z1, site.STRIP)
    windows = O.build(c, plan(), facade.order(), glass=facade.glass)
    x, y, z = pipes.INLET
    c.set(x, y, z, B.IRON_GRATE)        # main/facade sets this grating in the building (c206: PIPE_INLET)
    _rooms(c, windows)
    n = pipes.dress(c) + _heating(c)
    sky.build(c, (0, 0, 0))             # A2's light sources go in last, when every piece is in place
    c.entity_counts = {"props": n}
    return c


def write_pack(pack_dir):
    """The repainted stone, copper and glass the pipes are judged against, and the map's sky: the
    scene stands in the map's hour, and without the sky's pack the game's own sun stands in it."""
    return list(materials.pack(pack_dir) or []) + list(sky.pack(pack_dir) or [])


def shots():
    """The cameras. They stand east and south of the front, where the court and the terrace's south
    walk see it."""
    out = []

    def shot(name, pos, look_at):
        out.append({"name": name, "pos": [round(float(v), 2) for v in pos],
                    "look_at": [round(float(v), 2) for v in look_at], "time": TIME})

    (cx, cz), side = pipes.corners()[-1]                # the corner between the wing and the south end pavilion
    reach = (pipes.GAP + pipes.DOWN_R) / 16.0
    px, pz = cx + reach, cz + side * reach              # the downpipe's axis
    top, foot = float(S.CORNICE), S.PLINTH[1] + 1.0     # the soffit its hopper hangs under; the coping it enters
    ix, iy, iz = pipes.INLET
    sx, sy, sz = ix + 1.0 + pipes.INLET_VALVE / 16.0, iy + pipes.ANGLE / 16.0, iz + 0.5     # the angle valve's corner
    face = float(cx)                                    # the plane of the wing's wall face
    mid = S.mid(Z0, S.Z_SOUTH)                          # the middle of the stretch

    shot("front", (face + 20.0, 8.5, mid), (face, 8.5, mid))
    shot("front_foot", (face + 20.0, S.EYE, mid + 2.0), (face, 3.0, mid + 2.0))
    shot("oblique", (px + 5.0, 6.0, pz - 5.0), (px, 6.5, pz))
    shot("hopper_up", (px + 2.2, S.EYE, pz - 2.2), (px, top - 1.0, pz))
    shot("hopper_near", (px + 1.2, top - 2.2, pz - 2.4), (px + 0.1, top - 0.7, pz - 0.1))
    shot("string_above", (px + 1.9, S.STRING + 2.0, pz - 1.7), (px, S.STRING + 1.0, pz))
    shot("string_below", (px + 1.9, S.STRING - 0.8, pz - 1.7), (px, S.STRING - 0.1, pz))
    shot("clip_near", (px + 1.6, 8.9, pz - 1.5), (px, 8.75, pz))
    shot("foot", (px + 2.1, foot + 0.6, pz - 1.9), (px, foot + 0.1, pz))
    shot("inlet", (sx + 2.0, 1.5, sz + 2.2), (sx - 0.1, sy + 0.15, sz))
    shot("inlet_east", (sx + 3.2, 1.3, sz - 0.5), (sx, sy + 0.1, sz))
    shot("inlet_south", (sx - 0.3, 1.3, sz + 3.0), (sx - 0.3, sy + 0.15, sz))
    shot("inlet_walk", (sx + 2.5, S.EYE, sz - 3.4), (sx - 0.2, sy + 0.1, sz))
    shot("corner_far", (face + 15.0, S.EYE, S.Z_SOUTH + 10.0), (face + 1.0, 5.0, S.Z_SOUTH - 3.0))

    hy, hz, wall = LINE_Y, LINE_Z, S.Z_SOUTH + 1.0      # the sample line's axis; the south wall's face
    pier = BACK + S.BAY + 0.5                           # the middle of the pier between the two bays
    vx, bx = BACK + 1.0 + VALVE_AT / 16.0, BACK + 1.5   # the valve; the cell the bend stands in
    shot("heating_front", (pier - 0.5, S.EYE, wall + 20.0), (pier - 0.5, 3.0, wall))
    shot("heating_oblique", (vx + 3.2, 3.1, hz + 3.2), (vx - 0.4, hy, hz))
    shot("heating_along", (pier + 1.1, 2.7, wall + 2.3), (bx, hy, hz - 0.05))
    shot("heating_valve", (vx + 0.9, 2.7, hz + 2.9), (vx - 0.1, hy + 0.05, hz))
    shot("heating_bend", (bx + 0.7, 2.9, hz + 1.6), (bx - 0.05, hy, hz - 0.1))
    shot("heating_pier", (pier + 2.0, 2.8, wall + 1.9), (pier + 0.5, hy, hz))
    return out
