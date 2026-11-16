"""props/pneumatic -- the pneumatic dispatch: glass tubes along the walls and under the beams, the
stations they end in, and the carriers that fly in them (plan/round2.md, section D; card
plan/packages/props/pneumatic.md; rec c356, 11-16).

The rooms of the observatory send each other paper: a time signal checked, the number of a plate,
a word from the dome. The slip is rolled into a carrier, a brass cartridge as long as a finger,
the carrier goes into the station on the wall, and the air takes it through a tube of glass to the
room it is for. On the night of the comet the tubes are never still for long.

What the family is made of. Every piece is drawn along its own +z, which is laid along the run;
its +y is the way the surface looks that the run is fixed to (a wall, a beam's flank):

    tube      a length of glass, never longer than PIECE. Nothing of the glass is drawn but its
              four edges: the two that stand off the wall in the sheen of clear glass, the two
              against it a step lower (K.pane: every family draws clear glass by its reflection),
              so what flies in it is seen. At its start a brass collar on a saddle screwed to the
              wall, and against the collar the green ring of the air lines (plan/fine.md 3 and
              plan/parts/pipes.md, c342: steam red, water blue, air green)
    bend      a brass elbow that takes a run into the surface it runs along, bolted to it
    flange    where a tube goes head-on into a ceiling, a wall or the shoe of a beam
    station   on a wall, at the height of the hand: a brass box with a door and a window in it,
              into whose top the tube comes down; under the box a wire basket with the carriers
              that have come and wait to be sent back; beside the tube a bell that the carrier
              strikes as it lands, and under it the push that calls the other end
    carrier   the cartridge: a sleeve of pale felt between two brass caps

Every line has a head and a foot (plan/fine.md 3: no pipe ends in the air): it leaves a station
and goes into stone or iron through a flange or a bend.

What moves. A straight length has a carrier of its own, which rests out of sight at the length's
near end, inside the station's box or inside the brass of a bend, flies to the far end and
is out of sight again there, inside a bend or the stone. One after the other they are one carrier
that goes the whole line, and later comes back: MK.slide, two moves a carrier in a LOOP of half a
minute, a command each. motion/travel (c322), which takes one entity round corners, is not in the
tree yet; a line laid with it would look the same from the room.

    line(canvas, key, origin)   lay one of LINES
    build(canvas, origin)       every line whose room has moved in (the master scene calls this)
    models()                    {name: Model}

All functions take scene coordinates plus `origin` and return the display entities they placed.
"""
import functools
import math

from artkit import models as M
from artkit.pixelart import Sprite

from ..common import palette as P
from ..common import skeleton as S
from . import _kit as K

try:
    from ..motion import _kit as MK
except ImportError:                     # the motion line is not in the tree: the carriers stay in their stations
    MK = None

PREFIX = "prop_pneu_"
PX = 1 / 16.0
VIEW = getattr(M, "NEAR", 0.5)          # everything of the family is indoors (the assembly's view bands, c318)

DIRS = {"east": (1, 0, 0), "west": (-1, 0, 0), "south": (0, 0, 1), "north": (0, 0, -1),
        "up": (0, 1, 0), "down": (0, -1, 0)}

# pixels
BORE = 1.5              # the glass: three pixels across
COLLAR = 2.0            # a collar's radius
STAND = 2.0             # the tube's axis off the surface it is fixed to: a collar lies against it
PIECE = 40.0            # a length of glass is no longer than this: a collar every two and a half blocks at the most
BEND = 3.6              # from a bend's corner to the end of its socket
SOCKET = 9.5            # the station's socket takes the tube this far above the station's anchor
BOX = (7.0, 8.0, 5.0)   # the station's box: across, its height above the anchor, how far it stands off the wall
CARRIER = (4.0, 0.9)    # the carrier: its length, its radius

# ticks
LOOP = 600              # a carrier goes out and comes back once in half a minute
SPEED = 0.3             # blocks a tick: six blocks a second, slow enough for the eye to follow it across a ceiling
OUT, BACK = 60, 360     # the ticks of the loop on which it leaves its station and on which it sets off home
HANDOVER = 2            # ticks between one length's carrier going out of sight and the next one's setting off

# the light the family is shown in (block light; no sky reaches it): brass under a room's lamps. The
# tubes run where the rooms are darkest, along the heads of the walls and under the beams, and glass
# that took its light from there would not be seen at all; the carrier is a step up, it is what moves
SHOWN = (0, 9)
SHOWN_CARRIER = (0, 12)

BRASS, BRASS_D = K.BRASS, K.BRASS_D
BRASS_L = P.mat("brass", base=4)
IRON_D = K.IRON_D
WOOD = P.mat("dark_wood")
RING = K.flat("verdigris", 1)           # the air lines' ring (c342's table, plan/parts/pipes.md)
SCREW = K.flat("iron", 5)
FELT = K.flat("cream", 2)
WIRE = K.flat("brass", 2)
PUSH = K.flat("porcelain", 3)
EDGE, EDGE_LOW = K.SHEEN, K.SHEEN_DIM


# ---- directions -----------------------------------------------------------------------------------
@functools.lru_cache(maxsize=None)
def _turns(along, out):
    """The turns (for artkit.models.display) that lay a model's +z along `along` and its +y along
    `out`, two directions at right angles: found by trying the quarter turns, with the same
    quaternions display() multiplies."""
    want_z, want_y = DIRS[along], DIRS[out]
    if sum(a * b for a, b in zip(want_z, want_y)):
        raise ValueError(f"{along!r} and {out!r} are not at right angles")
    for a in (0.0, 90.0, 180.0, 270.0):
        for b in (0.0, 90.0, 180.0, 270.0):
            for c in (0.0, 90.0, 180.0, 270.0):
                q = M.IDENT
                for axis, deg in (("x", a), ("y", b), ("z", c)):
                    q = M._qmul(M.quat(axis, deg), q)
                z, y = M._qrot(q, (0.0, 0.0, 1.0)), M._qrot(q, (0.0, 1.0, 0.0))
                if all(abs(z[i] - want_z[i]) < 1e-6 and abs(y[i] - want_y[i]) < 1e-6 for i in range(3)):
                    return tuple((axis, deg) for axis, deg in (("x", a), ("y", b), ("z", c)) if deg)
    raise ValueError(f"no turn lays +z along {along!r} and +y along {out!r}")


def _along(a, b):
    """The name of the direction from a to b, two points on a line along an axis, and how far."""
    d = [b[i] - a[i] for i in range(3)]
    length = math.sqrt(sum(v * v for v in d))
    for name, way in DIRS.items():
        if length > 1e-9 and all(abs(d[i] / length - way[i]) < 1e-6 for i in range(3)):
            return name, length
    raise ValueError(f"a tube runs along an axis: {a} to {b} does not")


def _step(p, way, blocks):
    return tuple(p[i] + DIRS[way][i] * blocks for i in range(3))


# ---- the models -----------------------------------------------------------------------------------
def _saddle(m, z):
    """A collar at z on the axis, on its saddle on the wall (the plane y = -STAND), the air lines'
    ring against it."""
    m.box((-3.0, -STAND, z), (3.0, -STAND + 0.4, z + 1.5), BRASS_D)
    for x in (-2.85, 2.35):
        m.box((x, -STAND + 0.4, z + 0.5), (x + 0.5, -STAND + 0.65, z + 1.0), SCREW)
    m.tube("z", (0.0, 0.0), z, z + 1.5, COLLAR, BRASS, sides=8)
    m.tube("z", (0.0, 0.0), z + 1.5, z + 2.5, COLLAR - 0.25, RING, sides=8)


def _tube(length):
    """A length of glass, `length` pixels of it (a whole number), from the anchor along +z."""
    n = int(length)
    m = M.Model(f"{PREFIX}tube_{n}")
    side = Sprite(f"{PREFIX}glass_side_{n}", ["g" * n, "." * n, "d" * n], dict(g=EDGE, d=EDGE_LOW))
    front = Sprite(f"{PREFIX}glass_front_{n}", ["g.g"] * n, dict(g=EDGE))
    back = Sprite(f"{PREFIX}glass_back_{n}", ["d.d"] * n, dict(d=EDGE_LOW))
    m.box((-BORE, -BORE, 0.0), (BORE, BORE, float(n)), BRASS, skip="ns",
          faces={"e": side, "w": side, "u": front, "d": back})
    _saddle(m, 0.0)
    return m


def _bend():
    """An elbow from a run into the surface behind it. Anchor: the corner, on the run's axis; the
    run leaves along +z, the other leg goes into the surface along -y."""
    m = M.Model(PREFIX + "bend")
    m.ball((0.0, 0.0, 0.0), 2.3, BRASS_D, sides=8, layers=4)
    m.tube("z", (0.0, 0.0), 1.0, BEND - 0.6, 2.2, BRASS, sides=8)
    m.tube("z", (0.0, 0.0), BEND - 0.6, BEND, 2.6, BRASS_D, sides=8)
    m.tube("y", (0.0, 0.0), -STAND + 0.5, -1.0, 2.2, BRASS, sides=8)
    m.tube("y", (0.0, 0.0), -STAND, -STAND + 0.5, 3.1, BRASS_D, sides=8)            # its flange on the surface
    for x, z in ((-2.4, -2.4), (2.0, -2.4), (-2.4, 2.0), (2.0, 2.0)):
        m.box((x, -STAND + 0.5, z), (x + 0.4, -STAND + 0.8, z + 0.4), SCREW)
    m.tube("y", (0.0, 0.0), 2.0, 2.7, 1.2, BRASS, sides=6)                          # the plug it is cleared through
    m.box((-0.4, 2.7, -0.4), (0.4, 3.2, 0.4), BRASS_L)
    return m


def _flange():
    """Where a tube goes head-on into a surface. Anchor: the point of the surface on the tube's
    axis; +z comes out of the surface, towards the tube."""
    m = M.Model(PREFIX + "flange")
    m.tube("z", (0.0, 0.0), 0.0, 0.5, 3.0, BRASS_D, sides=8)
    m.tube("z", (0.0, 0.0), 0.5, 2.0, 2.2, BRASS, sides=8)
    m.tube("z", (0.0, 0.0), 2.0, 3.0, COLLAR - 0.25, RING, sides=8)
    for x, y in ((-2.3, -0.2), (1.9, -0.2), (-0.2, -2.3), (-0.2, 1.9)):
        m.box((x, y, 0.5), (x + 0.4, y + 0.4, 0.8), SCREW)
    return m


DOOR = (                # the station's door, seven by eight: its frame, the round window, the hinges (h), the knob (k)
    "bbbbbbb",
    "hdgggdb",
    "bgnnngb",
    "bgnsngk",
    "bgnnngb",
    "hdgggdb",
    "bdddddb",
    "bbbbbbb",
)
CARD = (                # the card of the places the line serves: a green spot for the line, pencil lines for the names
    "ccccc",
    "cvlll",
    "ccccc",
    "cllll",
    "ccccc",
    "clllc",
    "ccccc",
)
MESH = ("w.w.w.w", ".w.w.w.", "w.w.w.w", ".w.w.w.", "w.w.w.w", "wwwwwww")      # the basket's wire, seven by six


def _station():
    """A station. Wall-mounted: the wall is the plane z = 0, the anchor the point of it under the
    tube's axis at the foot of the box. The tube's axis stands STAND off the wall."""
    name = PREFIX + "station"
    m = M.Model(name)
    w, h, d = BOX
    brass = P.RAMPS["brass"]
    m.box((-5.0, -9.0, 0.0), (5.0, 12.0, 0.5), WOOD, skip="n", grain="y")                       # the board on the wall
    for x in (-4.6, 4.1):
        for y in (-8.6, 11.1):
            m.box((x, y, 0.5), (x + 0.5, y + 0.5, 0.7), SCREW)
    door = Sprite(name + "_door", list(DOOR), dict(b=brass[2], d=brass[3], g=brass[4], h=brass[1], k=brass[5],
                                                   n=P.RAMPS["night_glass"][1], s=K.SHEEN))
    m.box((-w / 2.0, 0.0, 0.5), (w / 2.0, h, d), BRASS, faces={"s": door})                      # the box and its door
    m.box((w / 2.0, 3.0, d - 0.25), (w / 2.0 + 0.5, 5.0, d + 0.5), BRASS_L)                     # the latch, worn bright
    m.box((-w / 2.0 + 0.25, h, 0.5), (w / 2.0 - 0.25, h + 0.5, d - 0.25), BRASS_D)              # its top plate
    m.tube("y", (0.0, STAND), h + 0.5, SOCKET + 0.5, 2.3, BRASS, sides=8)                       # the socket the tube stands in
    m.tube("y", (0.0, STAND), SOCKET + 0.5, SOCKET + 1.5, COLLAR - 0.25, RING, sides=8)
    # the basket under the box: what has come lies in it
    mesh = Sprite(name + "_mesh", list(MESH), dict(w=brass[2]))
    m.box((-w / 2.0, -7.0, 0.5), (w / 2.0, -1.0, d - 0.5), WIRE, skip="un", faces={"s": mesh, "e": mesh, "w": mesh})
    m.box((-w / 2.0, -1.25, 0.5), (w / 2.0, -0.75, d - 0.5), BRASS_D, skip="ud")                # its rim
    m.box((-2.5, -1.0, 0.5), (2.5, 0.0, 3.5), BRASS_D)                                          # the throat between box and basket
    for x0, y, turn in ((-2.6, -6.1, 0.0), (-1.4, -5.0, 14.0)):                                 # two carriers in it
        rot = ("z", turn, (x0 + 2.0, y, 2.4)) if turn else None
        m.box((x0, y - 0.8, 1.6), (x0 + 4.0, y + 0.8, 3.2), FELT, rot=rot)
        for x in (x0 - 0.4, x0 + 4.0):
            m.box((x, y - 0.9, 1.5), (x + 0.4, y + 0.9, 3.3), BRASS_L, rot=rot)
    # the bell the carrier strikes, right of the tube, and the push under it
    m.tube("z", (3.4, 10.0), 0.5, 1.0, 0.5, IRON_D, sides=6)
    m.tube("z", (3.4, 10.0), 1.0, 1.75, 1.4, BRASS_L, sides=8)
    m.box((3.2, 8.3, 0.5), (3.6, 9.2, 1.2), IRON_D)                                             # its striker
    m.box((2.6, -4.0, 0.5), (4.4, -2.2, 0.9), BRASS_D)
    m.tube("z", (3.5, -3.1), 0.9, 1.5, 0.6, PUSH, sides=6)
    # left of the tube: the card of the places the line serves, in its brass frame
    card = Sprite(name + "_card", list(CARD), dict(c=P.RAMPS["cream"][3], l=P.RAMPS["iron"][4], v=P.RAMPS["verdigris"][1]))
    m.box((-4.75, 8.75, 0.5), (-2.25, 11.75, 0.75), BRASS_D)
    m.box((-4.5, 9.0, 0.6), (-2.5, 11.5, 0.9), K.CREAM, skip="nudew", faces={"s": card})
    return m


def _carrier():
    """The carrier, along +z, its middle on the anchor."""
    m = M.Model(PREFIX + "carrier")
    length, r = CARRIER
    m.tube("z", (0.0, 0.0), -length / 2.0 + 0.5, length / 2.0 - 0.5, r, FELT, sides=8)
    for z in (-length / 2.0, length / 2.0 - 0.5):
        m.tube("z", (0.0, 0.0), z, z + 0.5, r + 0.1, BRASS_L, sides=8, cap=BRASS_L)
    return m


FIXED = dict(bend=_bend, flange=_flange, station=_station, carrier=_carrier)


# ---- the lines ------------------------------------------------------------------------------------
def _room(name):
    try:
        import importlib
        return importlib.import_module(f"{__package__.rsplit('.', 1)[0]}.interiors.{name}")
    except ImportError:
        return None


def _time_room():
    """A 1, the time room's (c351 and c347, 11-16: not on the west wall south of z -13, where the
    map of the time zones hangs; across the ceiling, where a carrier is seen to fly).

    The station hangs on the pier north of the rating bench, on the west wall. Its tube goes up the
    pier into the shoe of the beam over it, comes out of the shoe's south flank through a bend and
    runs along that flank of the beam across the whole room, to the bend that takes it into the
    east shoe and the front wall. The room's open wiring crosses under that beam at y 13.4 (c351);
    the tube lies on the beam's flank, its saddles from 13.56 up."""
    t = _room("timeroom")
    if t is None or not getattr(t, "MOVED_IN", False):
        return None
    row = t.PIER_LAMP_Z                                     # -18: the pier and the beam
    z = S.mid(row)
    west, east = t.PANEL_W + STAND * PX, t.PANEL_E - STAND * PX
    flank = (row + 1.0) + STAND * PX                        # the tube's axis on the beam's south flank
    level = t.TOP + 0.75                                    # the middle of the beam's flank: its slabs are the row's upper half
    return dict(
        number="A 1",
        station=dict(pos=(t.PANEL_W, float(t.SILL), z), facing="east"),
        runs=[
            dict(a=(west, t.SILL + SOCKET * PX, z), b=(west, float(t.TOP), z), out="east",
                 rest=(west, t.SILL + BOX[1] / 2.0 * PX, z), far=(west, t.TOP + 0.3, z), end="flange"),
            dict(a=(west, level, flank), b=(east, level, flank), out="south", start="bend", end="bend"),
        ],
        sound=(t.PANEL_W + 0.2, t.SILL + 0.25, z),
    )


LINES = {"time_room": _time_room}


def _pieces(length):
    """The whole pixels of each piece of a run `length` blocks long: equal lengths, none over PIECE."""
    total = int(round(length * 16.0))
    n = max(1, int(math.ceil(total / PIECE)))
    return [total // n + (1 if i < total % n else 0) for i in range(n)]


def _spans(run):
    """A run's glass: where it starts and ends between its fittings, and the way it runs."""
    way, _ = _along(run["a"], run["b"])
    a = _step(run["a"], way, BEND * PX) if run.get("start") == "bend" else run["a"]
    b = _step(run["b"], way, -BEND * PX) if run.get("end") == "bend" else run["b"]
    return a, b, way


@functools.lru_cache(maxsize=None)
def _models():
    made = {PREFIX + name: build() for name, build in FIXED.items()}
    for key in LINES:
        spec = LINES[key]()
        for run in (spec or {}).get("runs", ()):
            a, b, _ = _spans(run)
            for n in _pieces(_along(a, b)[1]):
                made.setdefault(f"{PREFIX}tube_{n}", _tube(n))
    return {name: K.settle(m) for name, m in made.items()}


def models():
    return dict(_models())


# ---- placing --------------------------------------------------------------------------------------
def _put(canvas, name, pos, along, out, origin, shown=SHOWN):
    return K.put(canvas, _models()[PREFIX + name], pos, yaw=0.0, turns=_turns(along, out), origin=origin,
                 brightness=shown, view=VIEW)


def carrier(canvas, pos, way="east", origin=(0, 0, 0)):
    """One carrier that stands still, its middle at pos, lying along `way`: one left on a desk; one
    in the glass for a picture, which cannot show the ones that fly. Returns 1."""
    return _put(canvas, "carrier", pos, way, "up" if way not in ("up", "down") else "east", origin, shown=SHOWN_CARRIER)


def _fly(canvas, rest, far, leaves, returns, origin):
    """A carrier that rests at `rest`, out of sight, flies to `far` on the tick `leaves` and home
    again on the tick `returns`; returns (1, the ticks one flight takes)."""
    way, length = _along(rest, far)
    n = carrier(canvas, rest, way, origin)
    ticks = max(1, int(round(length / SPEED)))
    if MK is not None:
        MK.slide(canvas, DIRS[way], [(leaves, length, ticks), (returns, 0.0, ticks)], LOOP)
    return n, ticks


def line(canvas, key, origin=(0, 0, 0)):
    """Lay the line `key` of LINES: its station, its glass, its fittings and its carriers. Returns
    the display entities placed, 0 while the line's room is not in the tree."""
    spec = LINES[key]()
    if spec is None:
        return 0
    n = K.put(canvas, _models()[PREFIX + "station"], spec["station"]["pos"], mount="wall",
              facing=spec["station"]["facing"], origin=origin, brightness=SHOWN, view=VIEW)
    flights = []
    for run in spec["runs"]:
        a, b, way = _spans(run)
        out = run["out"]
        at = a
        for length in _pieces(_along(a, b)[1]):
            n += _put(canvas, f"tube_{length}", at, way, out, origin)
            at = _step(at, way, length * PX)
        back = next(name for name, d in DIRS.items() if all(d[i] == -DIRS[way][i] for i in range(3)))
        if run.get("start") == "bend":
            n += _put(canvas, "bend", run["a"], way, out, origin)
        if run.get("end") == "bend":
            n += _put(canvas, "bend", run["b"], back, out, origin)
        elif run.get("end") == "flange":
            n += _put(canvas, "flange", run["b"], back, out, origin)
        flights.append((run.get("rest", run["a"]), run.get("far", run["b"])))
    # the carriers: out along the line one after the other, home in the opposite order
    spans = [max(1, int(round(_along(rest, far)[1] / SPEED))) for rest, far in flights]
    for i, (rest, far) in enumerate(flights):
        leaves = OUT + sum(spans[:i]) + HANDOVER * i
        returns = BACK + sum(spans[i + 1:]) + HANDOVER * (len(flights) - 1 - i)
        n += _fly(canvas, rest, far, leaves, returns, origin)[0]
    return n


def lands(key):
    """The tick of LOOP on which the carrier of the line `key` is home in its station, and the place
    (scene coordinates) it lands at: for the sound line (motion/sound), which has the thud."""
    spec = LINES[key]()
    if spec is None:
        return None
    spans = [max(1, int(round(_along(run.get("rest", run["a"]), run.get("far", run["b"]))[1] / SPEED)))
             for run in spec["runs"]]
    return BACK + sum(spans) + HANDOVER * (len(spans) - 1), spec["sound"]


def build(canvas, origin=(0, 0, 0)):
    return sum(line(canvas, key, origin) for key in LINES)
