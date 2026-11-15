"""Work package interiors/timeroom: the time-service room (plan ART-PLAN 8, view V10).
Card: plan/packages/interiors/timeroom.md.

The room is the north wing's main floor: 12 wide (x 2..13), 19 long (z -25..-7), 7 high (feet at 7,
the ceiling block on 14). The door is in the south wall on the room's long axis (x 7..8), so what
is seen first from it is the far end wall. That is where the one star piece stands, the instrument
wall; everything else keeps to the long walls and leaves the way to it open.

What stands where (plan cells; north is -z, the camera of V10 looks north):

  instrument wall   a rack of panel blocks against the north wall (z -25), x 3..12, six rows high
                    under an iron cornice and a hood. It is laid like a small front: four piers of
                    louvres on a foot of drawers, a bank of valves glowing at the head of each, and
                    between them three bays two panels wide. The flank bays hold the line gear
                    (relays, pilot lamps and a dial, switches, fuses and a jack field); the middle
                    bay holds what there is one of (the nameplate and the bell, the gauges and the
                    register, the oscilloscope and the recorder). A frieze of louvres runs under
                    the cornice and a course of drawers along the floor, as high as the wainscot.
                    rack_faults() says which rules the wall is laid by.
  standard clocks   the rack stops one cell short of each long wall, which leaves a recess one cell
                    wide and one deep at each of its ends (x 2 and x 13), with the north wall's
                    stone at its back. A regulator clock hangs in each, its foot on the sill line,
                    a lamp over it: the two clocks the service keeps. From the door both dials are
                    in full view (the rack's end hides a pixel and a half of each case), and the
                    pendulums move on either side of the rack; from the middle of the room the
                    rack's ends hide half of each clock, until one stands before a recess.
  console           a wooden shelf in front of the middle bay and the two piers beside it: the drum
                    recorder, the telegraph and its key stand on it, the operator sits in front of
                    it. One lamp hangs over it, the main light of the room.
  message desk      under bay 6 of the east wall; a lamp and the telephone on the pier north of it,
                    the pneumatic tube on the pier south of it
  rating bench      under bay 5 of the west wall; a lamp on the pier north of it, the barometer on
                    the pier south of it
  world clocks      five slave dials in a row on a dark board, on the blind stretch of the west wall
                    (the rotunda is behind it), over a low cabinet of drawers, a lamp over the
                    middle one. Their dials are level with the regulators'. They show the one time
                    every clock of the map is stopped at (the skeleton's CLOCK) in five places: the
                    hours differ, the minutes do not. These are the room's own models.
  south wall        card cabinets under a drawing west of the door, a coat stand east of it
  cable ducts       iron gratings in the floor: along the foot of the rack from wall to wall, and
                    from its two ends down the foot of the long walls to under the two desks
  ceiling           riveted beams across the room on the pilaster rows, where the piers carry them

The sill line (y 8) is the line the room hangs on: the wainscot and the rack's course of drawers
run under it, the console top, the top of the world clocks' cabinet and the feet of the two
regulators are on it, the desks stay below it.

Light: the room is lit by its lamps and by nothing else. A window is not a light of the room: the
ones the light line lights (sky/lights; bays 3 and 6 east, 3 and 5 west under the blue look) are
lined on the room side by materials/windows and are unlit glass from inside. Each of them has a
lamp of the room within two cells, so that a lit window is a lamp seen from outside: the lamps over
the two regulators for the end windows, the lamps beside the two desks for the others. Every source
is offered to the light line (sky/_lightkit); nothing is placed for good here. No block of the room
stands in the first cell behind the glass of a window (clear_cells()): the lining lies on the glass
there. The two recesses are such cells; what hangs in them is display entities.

The room dresses the shell main/shell.py (c231) leaves and lays no wall, floor slab or ceiling
slab. What other packages make is placed through them when they are in the tree (PIECES: the
furniture, the regulators and the barometer, the key and the telephone, the books and the drawing)
and is left out, or stood in for by a block, until then. SLOTS says where the machines of
machines/recorders go.

build() is what the master scene calls; it places nothing until MOVED_IN is set (the shell in the
master scene and the room past review). Until then the room lives in its box test scene,
build/scenes/obs_int_timeroom.
"""
import functools
import importlib
import math

from artkit import models as M
from artkit.blocks import st
from artkit.pixelart import Sprite

from ..common import blocks as B
from ..common import palette as P
from ..common import skeleton as S
from ..main import _plan as MP
from ..materials import panels
from ..props import _kit as K
from ..props import lamps

MOVED_IN = False
NAME = "interiors/timeroom"
PREFIX = "int_timeroom_"
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
PIER = ("tubes", "louvre", "louvre", "louvre", "drawers", "drawers")    # a pier: valves at its head, drawers at its foot
FLANK = (                                           # a flank bay: its outer column, its inner one
    ("louvre", "louvre"),
    ("relays", "dial"),
    ("pilot_lamps", "relays"),
    ("knife_switch", "bus_switch"),
    ("fuses", "patch_panel"),
    ("drawers", "drawers"),
)
MIDDLE = (                                          # the middle bay: what there is one of
    ("louvre", "louvre"),
    ("nameplate", "bell"),
    ("gauges", "counter"),
    ("scope", "recorder"),
    ("louvre", "louvre"),
    ("drawers", "drawers"),
)
# pier, flank bay, pier, middle bay, pier, the other flank bay as the first one's mirror image, pier
RACK = [(p,) + f + (p,) + m + (p,) + f[::-1] + (p,) for p, f, m in zip(PIER, FLANK, MIDDLE)]
QUIET = ("louvre", "drawers")                       # faces with nothing to read on them: where the eye rests
REACH = 2                                           # an instrument has a quiet face within so many steps along its row
RACK_Y = FEET                                       # 7: the lowest row of panels stands on the floor
CORNICE_Y = RACK_Y + len(RACK)                      # 13
CONSOLE_X = (RACK_X[0] + 1 + len(FLANK[0]), RACK_X[1] - 1 - len(FLANK[0]))      # 6..9: the middle bay and the piers beside it
CONSOLE_Z = RACK_Z + 1                              # -24
KEY_X = CONSOLE_X[0] + 1                            # 7: the telegraph key's cell; the operator sits in front of it
DRUM_X = CONSOLE_X[1]                               # 9: the drum recorder's

# ---- the standard clocks, in the recesses the rack leaves at its two ends
REGULATOR_X = (S.mid(X0), S.mid(X1))                # 2.5 and 13.5
REGULATOR_FOOT = float(SILL)                        # 8.0; the clock is two blocks tall
REGULATOR_TOP = REGULATOR_FOOT + 2.0
DIAL_Y = REGULATOR_FOOT + 25.5 * PX                 # 9.59: the middle of a regulator's dial (props/instruments), and of every dial of the room

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
DUCTS = (                                           # runs of grating in the floor, cell to cell
    ((X0, CONSOLE_Z), (X1, CONSOLE_Z)),                         # along the foot of the rack, wall to wall
    ((X1, CONSOLE_Z), (X1, MP.window_rows(DESK_BAY)[1])),       # down the east wall to under the message desk
    ((X0, CONSOLE_Z), (X0, MP.window_rows(BENCH_BAY)[1])),      # down the west wall to under the rating bench
)

# ---- the world clocks: a row of slave dials on one board, on the blind stretch of the west wall, one to a cell
CLOCK = getattr(S, "CLOCK", (7, 55))                # the time every clock of the map is stopped at (A0, g2 #34136)
CLOCK_Z = (BLIND_Z[0] + 1, BLIND_Z[1] - 1)          # -12..-8
WORLD = (5, 2, 0, -3, -5)                           # hours off the station's time, from the north end of the row: seen from the room the west is on the left
CASE_R = 6.0                                        # px: the radius of a world clock's case
BOARD = (16.0, 9.0, 11.0)                           # px: the length of board behind one dial: as wide as a cell, so far above the dial's middle, so far below it
INK = P.RAMPS["iron"][1]
DIAL = (                                            # nine pixels across: twelve marks and the hub; the face of
    "..kckck..",                                    # props/instruments' regulator without its luminous quarters
    ".ccccccc.",
    "kccccccck",
    "ccccccccc",
    "kcccbccck",
    "ccccccccc",
    "kccccccck",
    ".dcccccd.",
    "..kdkdk..",
)
DIAL_COLOURS = dict(c=P.RAMPS["porcelain"][3], d=P.RAMPS["porcelain"][2], k=INK, h=P.RAMPS["iron"][0], b=P.RAMPS["brass"][3])

# ---- light: what the room asks of the light line (level, rank); the lamps are props/lamps models
CONSOLE_LAMP = (11, 2)      # the pendant over the console: the main light, on the instrument wall
DESK_LAMP = (10, 2)         # the bracket lamps on the piers beside the message desk and the rating bench
REGULATOR_LAMP = (9, 2)     # the bracket lamps over the two standard clocks
CLOCK_LAMP = (7, 3)         # the bracket lamp over the world clocks
LAMP_Y = 10.5               # where a bracket is fixed on a pier
OVER = 12 * PX              # a bracket's arm above the top of what it hangs over: 11 px of wall plate, one of air


def rack_faults(rows=None):
    """What a wall of panels breaks of the rules the instrument wall is laid by: sentences, none
    when it keeps them. `rows` is the wall, top row first; left out, the rack.

    The rules are the ones the review of the panels' own test wall left (materials/panels keeps
    them for its bay in obs_mat_panels.faults):
      - every kind of panel is on the wall, the nameplate once;
      - a quiet face, a louvre or a drawer front, at most REACH steps from every instrument along
        its row, so no row is one unbroken run of instruments;
      - no instrument beside or above another of its kind: two white rounds side by side are a
        pair of eyes;
      - of the light faces (dial, gauges, recorder) no two beside or above each other, and of the
        lit ones (valves, oscilloscope, pilot lamps) none beside or above another lit face."""
    rows = RACK if rows is None else rows
    light, lit = panels.RANKS["light"], panels.RANKS["lit"]
    wrong = [f"no {name} on the wall" for name in sorted(set(B.PANELS) - {name for row in rows for name in row})]
    plates = sum(row.count("nameplate") for row in rows)
    if plates != 1:
        wrong.append(f"{plates} nameplates on the wall")
    for j, row in enumerate(rows):
        for i, name in enumerate(row):
            if name in QUIET:
                continue
            if not any(near in QUIET for near in row[max(0, i - REACH):i + REACH + 1]):
                wrong.append(f"row {j}, column {i}: no quiet face within {REACH} steps of the {name}")
            beside = [(row[i + 1], "beside")] if i + 1 < len(row) else []
            under = [(rows[j + 1][i], "above")] if j + 1 < len(rows) else []
            for other, how in beside + under:
                if name == other or (name in light and other in light) or (name in lit and other in lit):
                    wrong.append(f"row {j}, column {i}: {name} {how} {other}")
    return wrong


assert not rack_faults(), "the instrument wall breaks the rules it is laid by:\n  " + "\n  ".join(rack_faults())
assert len(WORLD) == CLOCK_Z[1] - CLOCK_Z[0] + 1, "one world clock to a cell"


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
    piece("paper", "blueprint", (X0 + 3.0, FEET + 2.625, SOUTH), facing="north"),                 # pinned over the card cabinets
)

# ---- where the machines of machines/recorders go (scene coordinates; facing is the way the thing looks)
SLOTS = {
    "drum": dict(pos=(S.mid(DRUM_X), float(SILL), S.mid(CONSOLE_Z)), facing="south",
                 note="the drum recorder, on the console's east end; its drum turns"),
    "telegraph": dict(pos=(S.mid(CONSOLE_X[0]), float(SILL), S.mid(CONSOLE_Z)), facing="south",
                      note="sounder and tape reel, on the console west of the key; the tape runs east, to the drum"),
    "tube": dict(pos=(EAST, float(SILL), pier(DESK_BAY, 1)), facing="west",
                 note="the pneumatic tube: down the pier south of the message desk, from the ceiling to a terminal"),
}


# ---- the room's own models: the world clocks ----------------------------------------------------------
def hands(rows, hour, minute):
    """A dial with its hands drawn in from the middle, the way props/instruments draws its clock's:
    the hour hand two pixels long, the minute hand three, a pixel to each step along the way the
    hand leans most."""
    grid = [list(row) for row in rows]
    mid = len(rows) // 2
    for turn, length in (((hour % 12 + minute / 60.0) / 12.0, 2), (minute / 60.0, 3)):
        dx, dy = math.sin(2.0 * math.pi * turn), -math.cos(2.0 * math.pi * turn)
        for i in range(1, length + 1):
            if abs(dx) > abs(dy):
                x, y = mid + (i if dx > 0 else -i), int(round(mid + i * dy / abs(dx)))
            else:
                x, y = int(round(mid + i * dx / abs(dy))), mid + (i if dy > 0 else -i)
            grid[y][x] = "h"
    return ["".join(row) for row in grid]


def clock_name(offset):
    """The model of the world clock that is `offset` hours off the station's time: ahead of it to
    the east, behind it to the west."""
    return PREFIX + ("clock_home" if not offset else f"clock_{'e' if offset > 0 else 'w'}{abs(offset)}")


def _world_clock(offset):
    """A world clock: a round slave dial on its length of the clock board. The dial is made like the
    head of props/instruments' barometer (a turned wooden case, a brass bezel, the nine-pixel
    dial). The board is as wide as a cell, so the clocks of a row stand on one board: the stone of
    the wall is as light as the porcelain, and it is the dark board that shows the dials. Under
    the dial a brass label for the place whose time it keeps. The hands stand at the map's one
    time, `offset` hours on. Anchor: the point on the wall behind the middle of the dial."""
    name = clock_name(offset)
    wide, up, down = BOARD
    m = M.Model(name)
    m.box((-wide / 2.0, -down, 0.0), (wide / 2.0, up, 1.0), P.mat("dark_wood", base=1), skip="n", grain="x")   # the board
    m.tube("z", (0, 0), 0.0, 3.0, CASE_R, P.mat("dark_wood"), sides=16, cap=K.flat("dark_wood", 3))            # the case
    m.ring("z", (0, 0, 3.5), 5.0, 1.5, 1.0, K.BRASS, sides=16)                                                # the bezel
    half = len(DIAL) / 2.0
    face = Sprite(name + "_dial", hands(DIAL, CLOCK[0] + offset, CLOCK[1]), DIAL_COLOURS)
    m.box((-half, -half, 3.25), (half, half, 3.5), K.flat("porcelain", 3), skip="nudew", faces={"s": face})
    m.box((-2.5, -CASE_R - 3.5, 1.0), (2.5, -CASE_R - 1.5, 1.5), K.BRASS_D, grain="x")                        # the label
    return m


@functools.lru_cache(maxsize=None)
def _models():
    return {clock_name(offset): _world_clock(offset) for offset in WORLD}


def models():
    """The room's own models: the five world clocks. Its lamps are props/lamps', its machines
    machines/recorders', the rest the packages' named in PIECES."""
    return dict(_models())


# ---- the other lines' pieces --------------------------------------------------------------------------
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
    the lamps and the room's own (the master scene collects every package's models itself)."""
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

    # ---- the world clocks on their board over a cabinet of drawers, and the lamp over the middle one
    own = _models()
    for z, offset in zip(range(CLOCK_Z[0], CLOCK_Z[1] + 1), WORLD):
        put(X0, FEET, z, st(roles.PANELS["drawers"], facing="east"))
        n += K.put(c, own[clock_name(offset)], (WEST, DIAL_Y, S.mid(z)), mount="wall", facing="east", origin=origin)
    n += lamp("bracket", (WEST, DIAL_Y + BOARD[1] * PX + OVER, S.mid(*CLOCK_Z)), CLOCK_LAMP, "world clocks", facing="east")

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
