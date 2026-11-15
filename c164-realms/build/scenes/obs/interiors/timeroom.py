"""Work package interiors/timeroom: the time-service room (plan ART-PLAN 8, view V10).
Card: plan/packages/interiors/timeroom.md.

The room is the north wing's main floor: 12 wide (x 2..13), 19 long (z -25..-7), 7 high (feet at 7,
the ceiling block on 14). The door is in the south wall on the room's long axis (x 7..8), so what
is seen first from it is the far end wall. That is where the one star piece stands, the instrument
wall; everything else keeps to the long walls and leaves the way to it open.

What stands where (plan cells; north is -z, the camera of V10 looks north):

  instrument wall   a rack of panel blocks against the north wall (z -25), x 3..12, six rows high
                    under an iron cornice and a hood. Three sections: two dark flanks of switch
                    gear, and a middle one that holds everything that is light or lit (valves,
                    dials, the two oscilloscopes between two recorders). The columns x 2 and x 13
                    stay empty: they are the cells behind the glass of the end windows.
  console           a wooden shelf in front of the middle section: the drum recorder and the
                    telegraph stand on it, the operator sits in front of it. One lamp hangs over it,
                    the main light of the room.
  message desk      under the lit window of the east wall (bay 6), a bracket lamp on the pier
  rating bench      under the lit window of the west wall (bay 5), a bracket lamp on the pier
  world clocks      a cabinet on the blind stretch of the west wall (the rotunda is behind it):
                    five dials over five registers that step together, a caged lamp over them
  cable ducts       iron gratings in the floor: along the foot of the rack and from its two ends
                    down the room to the desk and the bench, where they end under the furniture
  ceiling           riveted beams across the room on the pilaster rows, where the piers carry them

Light: the windows the light line lights (sky/lights; bays 3 and 6 east, 3 and 5 west under the
blue look) each have a lamp of the room beside them, so a lit window is a lamp seen from outside.
Everything is offered to the light line, nothing is placed for good here.

The room dresses the shell main/shell.py (c231) leaves and lays no wall, floor slab or ceiling
slab. The machines of machines/recorders and the furniture of props are stand-ins or left out
until those packages exist; SLOTS says where they go.

build() is what the master scene calls; it places nothing until MOVED_IN is set (the shell in the
master scene and the room past review). Until then the room lives in its box test scene,
build/scenes/obs_int_timeroom.
"""
from artkit.blocks import st

from ..common import blocks as B
from ..common import skeleton as S
from ..main import _plan as MP
from ..props import _kit as K
from ..props import lamps

MOVED_IN = False
NAME = "interiors/timeroom"

# ---- the room (main/shell.ROOMS["time room"], c231; written from the skeleton until the shell is in the tree)
X0, X1 = S.ROOM_X                                   # 2..13
Z0, Z1 = S.pilaster_z(2) + 1, S.STAR_HALL_Z[0] - 1  # -25..-7
FEET = S.STAND                                      # 7
TOP = S.STAR_HALL_CEIL - 1                          # 13: the last clear row
FLOOR_Y = FEET - 1                                  # 6: the floor block
CEIL_Y = S.STAR_HALL_CEIL                           # 14: the ceiling block
DOOR_X = (7, 8)                                     # the door, in the wall on z -6
AXIS_X = S.mid(*DOOR_X)                             # 8.0: the long axis, between two cells
PIER_Z = tuple(z for z in range(Z0, Z1 + 1) if MP.on_pilaster(z))               # -22, -18, -14, -10
EAST_BAYS = tuple(b for b in range(1, S.N_BAYS + 1) if set(MP.window_rows(b)) <= set(range(Z0, Z1 + 1)))
WEST_BAYS = tuple(b for b in EAST_BAYS if all(abs(z - S.DOME_CENTRE[1]) > MP.WEST_BLIND_Z for z in MP.window_rows(b)))
BLIND_Z = (S.pilaster_z(max(WEST_BAYS)) + 1, Z1)    # -13..-7: the west wall with the rotunda behind it

# ---- the instrument wall: top row first
RACK_Z = Z0                                         # -25
RACK_X = (X0 + 1, X1 - 1)                           # 3..12
FLANK = (                                           # outer, middle, inner column of a flank
    ("louvre", "nameplate", "louvre"),
    ("relays", "relays", "relays"),
    ("bell", "gauges", "pilot_lamps"),
    ("fuses", "fuses", "counter"),
    ("knife_switch", "knife_switch", "bus_switch"),
    ("drawers", "drawers", "drawers"),
)
MIDDLE = (
    ("louvre", "louvre", "louvre", "louvre"),
    ("tubes", "tubes", "tubes", "tubes"),
    ("dial", "dial", "dial", "dial"),
    ("recorder", "scope", "scope", "recorder"),
    ("patch_panel", "patch_panel", "patch_panel", "patch_panel"),
    ("louvre", "louvre", "louvre", "louvre"),
)
RACK = [flank + middle + flank[::-1] for flank, middle in zip(FLANK, MIDDLE)]
RACK_Y = FEET                                       # 7: the lowest row of panels stands on the floor
CORNICE_Y = RACK_Y + len(RACK)                      # 13
CONSOLE_X = (RACK_X[0] + len(FLANK[0]), RACK_X[1] - len(FLANK[0]))      # 6..9: in front of the middle section
CONSOLE_Z = RACK_Z + 1                              # -24

# ---- along the long walls
DESK = dict(x=(X1 - 1, X1), z=tuple(MP.window_rows(6)[i] for i in (0, -1)))    # x 12..13, z -13..-11
BENCH = dict(x=(X0, X0 + 1), z=tuple(MP.window_rows(5)[i] for i in (0, -1)))   # x 2..3, z -17..-15
CLOCK_Z = (BLIND_Z[0] + 1, BLIND_Z[1] - 1)          # -12..-8: five clocks
CLOCKS = ("drawers", "counter", "dial")             # the cabinet, bottom row first
DUCTS = (                                           # runs of grating in the floor, cell to cell
    ((RACK_X[0], CONSOLE_Z), (RACK_X[1], CONSOLE_Z)),
    ((DESK["x"][0], CONSOLE_Z), (DESK["x"][0], DESK["z"][0])),
    ((BENCH["x"][1], CONSOLE_Z), (BENCH["x"][1], BENCH["z"][0])),
)

# ---- light: what the room asks of the light line (level, rank); the lamps are props/lamps models
CONSOLE_LAMP = (11, 2)      # the pendant over the console: the main light, on the instrument wall
DESK_LAMP = (10, 2)         # the bracket lamps beside the two lit windows of the long walls
CLOCK_LAMP = (7, 3)         # the caged lamp over the world clocks
LAMP_Y = 10.5               # where a bracket is fixed on its pier

# ---- where the things of other packages go (scene coordinates; facing is the way the thing looks)
SLOTS = {
    # machines/recorders
    "drum": dict(pos=(CONSOLE_X[1] + 0.5, FEET + 1.0, CONSOLE_Z + 0.5), facing="south",
                 note="the drum recorder, on the console's east end; its drum turns"),
    "telegraph": dict(pos=(CONSOLE_X[0] + 1.5, FEET + 1.0, CONSOLE_Z + 0.5), facing="south",
                      note="key, sounder and tape reel, on the console west of the drum; the tape runs east"),
    "clock_rims": [dict(pos=(X0 + 1.0, FEET + 2.5, z + 0.5), facing="east") for z in range(CLOCK_Z[0], CLOCK_Z[1] + 1)],
    "tube": dict(pos=(X1 + 1.0, FEET + 1.0, PIER_Z[2] + 0.5), facing="west",
                 note="the pneumatic tube: down the pier beside the message desk, from the ceiling to a terminal"),
    # props
    "stools": [dict(pos=(AXIS_X - 0.5, FEET, CONSOLE_Z + 1.5)), dict(pos=(DESK["x"][0] - 0.5, FEET, S.mid(*DESK["z"]))),
               dict(pos=(BENCH["x"][1] + 1.5, FEET, S.mid(*BENCH["z"])))],
}


def cells(run):
    """The cells of a straight run of the plan, both ends included."""
    (xa, za), (xb, zb) = run
    return [(x, z) for x in range(min(xa, xb), max(xa, xb) + 1) for z in range(min(za, zb), max(za, zb) + 1)]


def duct_cells():
    return sorted({c for run in DUCTS for c in cells(run)})


def clear_cells():
    """The cells the room keeps empty for the light line: the first cell behind the glass of every
    window of the long walls, [(x, y, z)]."""
    out = []
    for bays, x in ((EAST_BAYS, X1), (WEST_BAYS, X0)):
        for bay in bays:
            out += [(x, y, z) for z in MP.window_rows(bay) for y in range(S.WINDOW[0], S.WINDOW[1] + 1)]
    return out


def panel(side):
    """A panel of the wainscot standing on that side of its cell."""
    back = {"north": "south", "south": "north", "west": "east", "east": "west"}[side]
    return st(B.WAINSCOT, facing=back, half="bottom", open="true")     # it stands on the side it turns its back to


def build_timeroom(c, origin=(0, 0, 0), roles=B, *, version="a"):
    """Dress the room standing at `origin`. Returns dict(entities=<display entities placed>,
    lights=[((x, y, z), level, why)]): the light sources it has offered to the light line."""
    ox, oy, oz = origin
    lights, n = [], 0

    def put(x, y, z, state):
        c.set(ox + x, oy + y, oz + z, state)

    def lamp(kind, pos, ask, why, **how):
        level, rank = ask
        name = f"{kind}_{lamps.VERSION}" if kind in lamps.VERSIONED else kind
        cell = K.light_cell(pos, K.FACING[how.get("facing", "south")], lamps.SPEC[name]["light"], origin)
        lights.append((cell, level, f"{NAME}:{why}"))
        _offer(c, cell, level, f"{NAME}:{why}", rank)
        return lamps.place(c, kind, pos, origin=origin, light=False, **how)

    # ---- the instrument wall: six rows of panels, the cornice, the hood over the faces
    for j, row in enumerate(RACK[::-1]):
        for i, name in enumerate(row):
            put(RACK_X[0] + i, RACK_Y + j, RACK_Z, st(roles.PANELS[name], facing="south"))
    for x in range(RACK_X[0], RACK_X[1] + 1):
        put(x, CORNICE_Y, RACK_Z, roles.IRON_RIVETED.block)
        put(x, CORNICE_Y, CONSOLE_Z, st(roles.IRON_RIVETED.slab, type="top"))

    # ---- the console, and what stands on it until machines/recorders brings the real things
    for x in range(CONSOLE_X[0], CONSOLE_X[1] + 1):
        put(x, FEET, CONSOLE_Z, st(roles.DARK_WOOD.slab, type="top"))
    put(CONSOLE_X[1], FEET + 1, CONSOLE_Z, st(roles.BRASS_COLUMN, axis="x"))                    # the drum
    put(CONSOLE_X[0] + 1, FEET + 1, CONSOLE_Z, st(roles.BRASS_BUTTON, face="floor", facing="north"))   # the key
    n += lamp("pendant", (AXIS_X, CORNICE_Y + 0.5, CONSOLE_Z + 0.5), CONSOLE_LAMP, "console")

    # ---- the cable ducts: a grating in the floor, an iron bed under it
    for x, z in duct_cells():
        put(x, FLOOR_Y, z, roles.IRON_GRATE)
        put(x, FLOOR_Y - 1, z, roles.IRON_PLATE)

    # ---- beams on the pilaster rows
    for z in PIER_Z:
        for x in range(X0, X1 + 1):
            put(x, TOP, z, st(roles.IRON_RIVETED.slab, type="top"))

    # ---- the message desk and the rating bench under their windows, a bracket lamp beside each
    for piece in (DESK, BENCH):
        for x, z in cells(((piece["x"][0], piece["z"][0]), (piece["x"][1], piece["z"][1]))):
            put(x, FEET, z, st(roles.DARK_WOOD.slab, type="top"))
    n += lamp("bracket", (X1 + 1.0, LAMP_Y, DESK["z"][0] - 0.5), DESK_LAMP, "desk", facing="west")
    n += lamp("bracket", (float(X0), LAMP_Y, BENCH["z"][0] - 0.5), DESK_LAMP, "bench", facing="east")

    # ---- the world clocks, and the lamp over them
    for z in range(CLOCK_Z[0], CLOCK_Z[1] + 1):
        for j, name in enumerate(CLOCKS):
            put(X0, FEET + j, z, st(roles.PANELS[name], facing="east"))
    n += lamp("cage", (float(X0), FEET + len(CLOCKS) + 0.6, S.mid(*CLOCK_Z)), CLOCK_LAMP, "clocks", facing="east")

    # ---- the wainscot: one course under the sills, round the room, where nothing stands
    def free(x, z):
        return not c.has(ox + x, oy + FEET, oz + z)

    for z in range(Z0, Z1 + 1):
        for x, side in ((X1, "east"), (X0, "west")):
            if free(x, z):
                put(x, FEET, z, panel(side))
    for x in range(X0 + 1, X1):
        if not DOOR_X[0] <= x <= DOOR_X[1] and free(x, Z1):
            put(x, FEET, Z1, panel("south"))
    return {"entities": n, "lights": lights}


def _offer(canvas, cell, level, why, rank):
    """Register a light source with the light line (sky/_lightkit). While that kit is not in the
    tree the block is put down here, never over a block that is there, so a test scene is lit."""
    try:
        from ..sky import _lightkit
    except ImportError:
        canvas.set(*cell, st(B.LIGHT, level=level), keep=True)
    else:
        _lightkit.suggest(canvas, cell, level, why, rank=rank)


def build(canvas, origin=(0, 0, 0)):
    """The master scene's call: nothing until the room has moved in."""
    if not MOVED_IN:
        return 0
    return build_timeroom(canvas, origin)["entities"]


def models():
    """The room has no model of its own; its lamps are props/lamps', its machines machines/recorders'."""
    return {}
