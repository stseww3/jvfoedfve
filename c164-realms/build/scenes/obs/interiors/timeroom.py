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
                    dials, the two oscilloscopes between two recorders).
  standard clocks   the rack leaves one column of the north wall's stone at each end (x 2, x 13).
                    A regulator clock hangs on each, its foot on the sill line, a lamp over it:
                    the two clocks the service keeps. Their pendulums move on either side of the
                    rack, and their dials are level with its oscilloscopes.
  console           a wooden shelf in front of the middle section: the drum recorder, the telegraph
                    and its key stand on it, the operator sits in front of it. One lamp hangs over
                    it, the main light of the room.
  message desk      under bay 6 of the east wall; a lamp and the telephone on the pier north of it,
                    the pneumatic tube on the pier south of it
  rating bench      under bay 5 of the west wall; a lamp on the pier north of it, the barometer on
                    the pier south of it
  world clocks      a cabinet on the blind stretch of the west wall (the rotunda is behind it):
                    five dials over five registers that step together, a lamp over them
  south wall        card cabinets under a blackboard west of the door, a coat stand east of it
  cable ducts       iron gratings in the floor: along the foot of the rack from wall to wall, and
                    from its two ends down the foot of the long walls to under the two desks
  ceiling           riveted beams across the room on the pilaster rows, where the piers carry them

The sill line (y 8) is the line the room hangs on: the wainscot runs under it, the console top and
the feet of the two clocks are on it, the desks stay below it.

Light: the room is lit by its lamps and by nothing else. A window is not a light of the room: the
ones the light line lights (sky/lights; bays 3 and 6 east, 3 and 5 west under the blue look) are
lined on the room side by materials/windows and are unlit glass from inside. Each of them has a
lamp of the room within two cells, so that a lit window is a lamp seen from outside: the lamps over
the two clocks for the end windows, the lamps beside the two desks for the others. Every source is
offered to the light line (sky/_lightkit); nothing is placed for good here. No block of the room
stands in the first cell behind the glass of a window (clear_cells()): the lining lies on the glass
there. The two clocks hang in such a column, on the north wall, half a pixel clear of it.

The room dresses the shell main/shell.py (c231) leaves and lays no wall, floor slab or ceiling
slab. What other packages make is placed through them when they are in the tree (PIECES: the
furniture, the clocks and the barometer, the key and the telephone, the books and the blackboard)
and is left out, or stood in for by a block, until then. SLOTS says where the machines of
machines/recorders go.

build() is what the master scene calls; it places nothing until MOVED_IN is set (the shell in the
master scene and the room past review). Until then the room lives in its box test scene,
build/scenes/obs_int_timeroom.
"""
import functools
import importlib

from artkit.blocks import st

from ..common import blocks as B
from ..common import skeleton as S
from ..main import _plan as MP
from ..props import _kit as K
from ..props import lamps

MOVED_IN = False
NAME = "interiors/timeroom"
PX = 1 / 16.0

# ---- the room (main/shell.ROOMS["time room"], c231; written from the skeleton until the shell is in the tree)
X0, X1 = S.ROOM_X                                   # 2..13
Z0, Z1 = S.pilaster_z(2) + 1, S.STAR_HALL_Z[0] - 1  # -25..-7
FEET = S.STAND                                      # 7
TOP = S.STAR_HALL_CEIL - 1                          # 13: the last clear row
FLOOR_Y = FEET - 1                                  # 6: the floor block
CEIL_Y = S.STAR_HALL_CEIL                           # 14: the ceiling block
SILL = S.WINDOW[0]                                  # 8: the sill line
DOOR_X = (7, 8)                                     # the door, in the wall on z -6
AXIS_X = S.mid(*DOOR_X)                             # 8.0: the long axis, between two cells
PIER_Z = tuple(z for z in range(Z0, Z1 + 1) if MP.on_pilaster(z))               # -22, -18, -14, -10
EAST_BAYS = tuple(b for b in range(1, S.N_BAYS + 1) if set(MP.window_rows(b)) <= set(range(Z0, Z1 + 1)))
WEST_BAYS = tuple(b for b in EAST_BAYS if all(abs(z - S.DOME_CENTRE[1]) > MP.WEST_BLIND_Z for z in MP.window_rows(b)))
BLIND_Z = (S.pilaster_z(max(WEST_BAYS)) + 1, Z1)    # -13..-7: the west wall with the rotunda behind it
NORTH, SOUTH, WEST, EAST = float(Z0), Z1 + 1.0, float(X0), X1 + 1.0     # the four wall faces: -25, -6, 2, 14

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
KEY_X = CONSOLE_X[0] + 1                            # 7: the telegraph key's cell; the operator sits in front of it
DRUM_X = CONSOLE_X[1]                               # 9: the drum recorder's

# ---- the standard clocks, on the stone the rack leaves at its two ends
REGULATOR_X = (S.mid(X0), S.mid(X1))                # 2.5 and 13.5
REGULATOR_FOOT = float(SILL)                        # 8.0; the clock is two blocks tall
REGULATOR_TOP = REGULATOR_FOOT + 2.0

# ---- along the long walls
DESK_BAY, BENCH_BAY = 6, 5                          # the message desk's window (east), the rating bench's (west)
WAINSCOT_T = 3 * PX                                 # a panel of the wainscot, off its wall
DESK_DEEP = 14 * PX                                 # props/furniture's writing desk, back to front
DESK_X = EAST - WAINSCOT_T - DESK_DEEP / 2          # 13.375: its back against the wainscot
BENCH_X = WEST + WAINSCOT_T + DESK_DEEP / 2         # 2.625
DESK_Z = S.mid(MP.window_rows(DESK_BAY)[0], MP.window_rows(DESK_BAY)[-1])       # -11.5: under the middle of its window
BENCH_Z = S.mid(MP.window_rows(BENCH_BAY)[0], MP.window_rows(BENCH_BAY)[-1])    # -15.5
SEAT = 1.075                                        # from the middle of a desk to the middle of its chair
CABINET_Z = SOUTH - 0.6                             # -6.6: where a cabinet stands with its back to the south wall
CLOCK_Z = (BLIND_Z[0] + 1, BLIND_Z[1] - 1)          # -12..-8: five world clocks
CLOCKS = ("drawers", "counter", "dial")             # their cabinet, bottom row first
DUCTS = (                                           # runs of grating in the floor, cell to cell
    ((X0, CONSOLE_Z), (X1, CONSOLE_Z)),                         # along the foot of the rack, wall to wall
    ((X1, CONSOLE_Z), (X1, MP.window_rows(DESK_BAY)[1])),       # down the east wall to under the message desk
    ((X0, CONSOLE_Z), (X0, MP.window_rows(BENCH_BAY)[1])),      # down the west wall to under the rating bench
)

# ---- light: what the room asks of the light line (level, rank); the lamps are props/lamps models
CONSOLE_LAMP = (11, 2)      # the pendant over the console: the main light, on the instrument wall
DESK_LAMP = (10, 2)         # the bracket lamps on the piers beside the message desk and the rating bench
REGULATOR_LAMP = (9, 2)     # the bracket lamps over the two standard clocks
CLOCK_LAMP = (7, 3)         # the bracket lamp over the world clocks
LAMP_Y = 10.5               # where a bracket is fixed on a pier
OVER = 12 * PX              # a bracket's arm above the top of what it hangs over: 11 px of wall plate, one of air


def pier(bay, end):
    """The middle, along z, of the pier at the north (end -1) or the south (end 1) of a bay."""
    return S.mid(S.pilaster_z(bay - 1 if end < 0 else bay))


def piece(package, kind, where, on=None, **how):
    """One thing of another package: scenes.obs.props.<package>.place(canvas, kind, where, **how).
    `on` names (package, kind) of the piece it stands on: it is placed only with that one, and the
    height of that one's top (its package's TOP) is added to where."""
    return dict(package=package, kind=kind, where=where, on=on, how=how)


# ---- what the room takes from other packages. `where` is what their place() asks for: the middle of
# the foot of a standing piece, the point on the wall face behind the foot of a hanging one, the
# middle of a picture; facing is the way the piece's front, or the wall face it hangs on, looks.
ON_DESK = ("furniture", "writing_desk")
PIECES = (
    # props/furniture (c179)
    piece("furniture", "stool", (S.mid(KEY_X), FEET, CONSOLE_Z + 1.5), facing="north"),
    piece("furniture", "writing_desk", (DESK_X, FEET, DESK_Z), facing="west"),
    piece("furniture", "swivel_chair", (DESK_X - SEAT, FEET, DESK_Z), yaw=K.FACING["east"] + 25.0),   # pushed back, half turned
    piece("furniture", "writing_desk", (BENCH_X, FEET, BENCH_Z), facing="east"),
    piece("furniture", "swivel_chair", (BENCH_X + SEAT, FEET, BENCH_Z), facing="west"),
    piece("furniture", "card_cabinet", (X0 + 2.5, FEET, CABINET_Z), facing="north"),
    piece("furniture", "card_cabinet", (X0 + 3.5, FEET, CABINET_Z), facing="north"),
    piece("furniture", "coat_stand", (DOOR_X[1] + 1.6, FEET, CABINET_Z), facing="north"),
    # props/instruments (c199)
    piece("instruments", "regulator_clock", (REGULATOR_X[0], REGULATOR_FOOT, NORTH), facing="south"),
    piece("instruments", "regulator_clock", (REGULATOR_X[1], REGULATOR_FOOT, NORTH), facing="south"),
    piece("instruments", "barometer", (WEST, SILL + 0.25, pier(BENCH_BAY, 1)), facing="east"),
    # props/electrics (c242)
    piece("electrics", "telegraph_key", (S.mid(KEY_X), float(SILL), CONSOLE_Z + 0.65), facing="south"),
    piece("electrics", "wall_phone", (EAST, SILL + 0.2, pier(DESK_BAY, -1)), facing="west"),      # under the desk's lamp
    # props/paper (c197)
    piece("paper", "logbook", (BENCH_X + 0.125, FEET, BENCH_Z - 0.2), on=ON_DESK, yaw=K.FACING["east"] + 8.0),
    piece("paper", "logbook_shut", (DESK_X - 0.09375, FEET, DESK_Z - 0.2), on=ON_DESK, yaw=K.FACING["west"] - 15.0),
    piece("paper", "blackboard", (X0 + 3.0, FEET + 3.0, SOUTH), facing="north"),                  # over the card cabinets
)

# ---- where the machines of machines/recorders go (scene coordinates; facing is the way the thing looks)
SLOTS = {
    "drum": dict(pos=(S.mid(DRUM_X), float(SILL), S.mid(CONSOLE_Z)), facing="south",
                 note="the drum recorder, on the console's east end; its drum turns"),
    "telegraph": dict(pos=(S.mid(CONSOLE_X[0]), float(SILL), S.mid(CONSOLE_Z)), facing="south",
                      note="sounder and tape reel, on the console west of the key; the tape runs east, to the drum"),
    "clock_rims": [dict(pos=(X0 + 1.0, FEET + 2.5, S.mid(z)), facing="east") for z in range(CLOCK_Z[0], CLOCK_Z[1] + 1)],
    "tube": dict(pos=(EAST, float(SILL), pier(DESK_BAY, 1)), facing="west",
                 note="the pneumatic tube: down the pier south of the message desk, from the ceiling to a terminal"),
}


@functools.lru_cache(maxsize=None)
def theirs(package):
    """The package scenes.obs.props.<package> of another line, or None while it is not in the tree."""
    full = f"{__package__.rsplit('.', 1)[0]}.props.{package}"
    try:
        return importlib.import_module(full)
    except ModuleNotFoundError as missing:
        if missing.name != full:
            raise
        return None


def their_models():
    """The models of the pieces of other packages the room places: what a test scene packs besides
    the lamps (the master scene collects every package's models itself)."""
    out = {}
    for package in sorted({p["package"] for p in PIECES}):
        module = theirs(package)
        if module is not None:
            out.update(module.models())
    return out


def cells(run):
    """The cells of a straight run of the plan, both ends included."""
    (xa, za), (xb, zb) = run
    return [(x, z) for x in range(min(xa, xb), max(xa, xb) + 1) for z in range(min(za, zb), max(za, zb) + 1)]


def duct_cells():
    return sorted({c for run in DUCTS for c in cells(run)})


def clear_cells():
    """The cells no block of the room stands in: the first cell behind the glass of every window of
    the long walls, [(x, y, z)]. The lining of a lit window lies on its glass there."""
    out = []
    for bays, x in ((EAST_BAYS, X1), (WEST_BAYS, X0)):
        for bay in bays:
            out += [(x, y, z) for z in MP.window_rows(bay) for y in range(S.WINDOW[0], S.WINDOW[1] + 1)]
    return out


def panel(side):
    """A panel of the wainscot standing on that side of its cell."""
    back = {"north": "south", "south": "north", "west": "east", "east": "west"}[side]
    return st(B.WAINSCOT, facing=back, half="bottom", open="true")     # it stands on the side it turns its back to


def build_timeroom(c, origin=(0, 0, 0), roles=B):
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

    # ---- the console, and what stands on it until machines/recorders and props/electrics bring the real things
    for x in range(CONSOLE_X[0], CONSOLE_X[1] + 1):
        put(x, FEET, CONSOLE_Z, st(roles.DARK_WOOD.slab, type="top"))
    put(DRUM_X, SILL, CONSOLE_Z, st(roles.BRASS_COLUMN, axis="x"))                          # the drum
    if theirs("electrics") is None:
        put(KEY_X, SILL, CONSOLE_Z, st(roles.BRASS_BUTTON, face="floor", facing="north"))   # the key
    n += lamp("pendant", (AXIS_X, CORNICE_Y + 0.5, S.mid(CONSOLE_Z)), CONSOLE_LAMP, "console")

    # ---- a lamp over each of the two standard clocks
    for x, side in zip(REGULATOR_X, ("west", "east")):
        n += lamp("bracket", (x, REGULATOR_TOP + OVER, NORTH), REGULATOR_LAMP, f"clock {side}", facing="south")

    # ---- the cable ducts: a grating in the floor, an iron bed under it
    for x, z in duct_cells():
        put(x, FLOOR_Y, z, roles.IRON_GRATE)
        put(x, FLOOR_Y - 1, z, roles.IRON_PLATE)

    # ---- beams on the pilaster rows
    for z in PIER_Z:
        for x in range(X0, X1 + 1):
            put(x, TOP, z, st(roles.IRON_RIVETED.slab, type="top"))

    # ---- the message desk and the rating bench: a lamp on the pier north of each; a board under the
    # window stands in for the desk while props/furniture is not in the tree
    if theirs("furniture") is None:
        for x, bay in ((X1, DESK_BAY), (X0, BENCH_BAY)):
            for z in MP.window_rows(bay):
                put(x, FEET, z, st(roles.DARK_WOOD.slab, type="top"))
    n += lamp("bracket", (EAST, LAMP_Y, pier(DESK_BAY, -1)), DESK_LAMP, "message desk", facing="west")
    n += lamp("bracket", (WEST, LAMP_Y, pier(BENCH_BAY, -1)), DESK_LAMP, "rating bench", facing="east")

    # ---- the world clocks, and the lamp over them
    for z in range(CLOCK_Z[0], CLOCK_Z[1] + 1):
        for j, name in enumerate(CLOCKS):
            put(X0, FEET + j, z, st(roles.PANELS[name], facing="east"))
    n += lamp("bracket", (WEST, FEET + len(CLOCKS) + OVER, S.mid(*CLOCK_Z)), CLOCK_LAMP, "world clocks", facing="east")

    # ---- the wainscot: one course under the sill line, round the room, where no block stands
    def free(x, z):
        return not c.has(ox + x, oy + FEET, oz + z)

    for z in range(Z0, Z1 + 1):
        for x, side in ((X1, "east"), (X0, "west")):
            if free(x, z):
                put(x, FEET, z, panel(side))
    for x in range(X0 + 1, X1):
        if not DOOR_X[0] <= x <= DOOR_X[1] and free(x, Z1):
            put(x, FEET, Z1, panel("south"))

    # ---- the pieces of the other packages that are in the tree
    for p in PIECES:
        module = theirs(p["package"])
        if module is None:
            continue
        x, y, z = p["where"]
        if p["on"] is not None:
            under = theirs(p["on"][0])
            if under is None:
                continue
            y += under.TOP[p["on"][1]]
        n += module.place(c, p["kind"], (x, y, z), origin=origin, **p["how"])
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
    """The room has no model of its own: its lamps are props/lamps', its machines machines/recorders',
    the rest the packages' named in PIECES."""
    return {}
