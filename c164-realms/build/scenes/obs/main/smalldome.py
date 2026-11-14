"""main/smalldome -- the small dome on the south end pavilion, above the parapet. A verdigris dome
a size down from the great dome (main/_dome.py): the same plates, ribs, darker runs and iron skirt
over a short stone drum, with an observing slit that looks west and is open through the apex. The
astrograph (machines) stands inside.

Card: plan/packages/main/smalldome.md. Design: plan/ART-PLAN.md 5.2 and 6.3, plan/parts/main.md 6.3.

Where it sits (skeleton SMALL_*): the pavilion is bays 16-17 (z 26..34), its east wall face x 16;
the dome is x 8..16, z 26..34, nine across, centred on cell (12, 30). The drum stands on the
pavilion's flat roof (deck y 17, feet y 18), flush with the pavilion's east and south wall faces,
so nothing of it may reach past x 16 or z 34, and nothing above the apex row y 25.

Rows: drum y 18..20 (dressed stone, a small window at y 19 on the east, south and north axes, an
iron door at y 18..19 on the west, onto the pavilion's terrace), iron skirt y 21, dome y 22..25.

The method follows main/_dome.py so the great dome (c222) and this one read as one family:
VERDIGRIS_CUT plates, a VERDIGRIS rib on each meridian running into a cast cap at the apex,
VERDIGRIS_STREAK runs beside the rib feet, an IRON_RIVETED skirt where the track would sit. A gore,
not a rib, lies on each of the four axes; the slit takes the west one. At nine blocks across a rib
cannot stand a whole block proud without leaving the footprint: here a rib is a column of its own
material whose top is always a whole block, so it rides half a block over the plates' slabs.
GORES can be changed: the great dome is still choosing between 20 fine ribs and 8 main ones.

Not here: the pavilion walls and the deck under the drum (main/facade.py, c206); the astrograph
and the slit's shutter (machines, A5); the terrace paving, the flashing at the drum's foot and the
ridge walkway that leads here (main/roof.py, same card).

    python -m scenes.obs.main.smalldome          # text sections and a self-check
    python -m scenes.obs.main.smalldome check    # the self-check alone (exit code 1 on a finding)
"""
import functools
import math
import sys

from artkit.canvas import Canvas

from ..common import blocks as B
from ..common import skeleton as S
from . import _order as O

ORDER = 50

CX = (S.SMALL_DOME_X[0] + S.SMALL_DOME_X[1]) // 2        # 12
CZ = (S.SMALL_DOME_Z[0] + S.SMALL_DOME_Z[1]) // 2        # 30
R = S.SMALL_DOME_R                                       # 4.5
GORES = 8                                                # ribs = gores; a multiple of four

DRUM = (S.SMALL_DRUM_BASE, S.SMALL_DRUM_BASE + 2)        # 18..20: the dressed-stone drum
WINDOW_Y = S.SMALL_DRUM_BASE + 1                         # 19
DOOR_Y = (S.SMALL_DRUM_BASE, S.SMALL_DRUM_BASE + 1)      # 18..19: the door onto the terrace
SKIRT_Y = DRUM[1] + 1                                    # 21: the iron skirt, the spring of the dome
APEX = S.SMALL_DOME_APEX                                 # 25: the last row anything stands in
CROWN = APEX + 1.0                                       # 26.0: the top face of the apex block
FOOT = R + 0.1                                           # the dome's radius at the spring: the last
#                                                          ring of columns closes, its corners stay low
RIB_FOOT = SKIRT_Y + 1                                   # 22: a rib stands at least this high
CAP = 1.5                                                # within this of the centre: the cast cap
SLIT_HALF = 1                                            # the slit is z CZ-1 .. CZ+1, three wide
SLIT_PAST = 0                                            # and ends this far past the apex column

PLATE, RIB, RUN, CAST = B.VERDIGRIS_CUT, B.VERDIGRIS, B.VERDIGRIS_STREAK, B.VERDIGRIS_CAST
SKIRT = B.IRON_RIVETED.block
FRONT = "sdome"                                          # the front's name in windows()
AXES = (O.EAST, O.SOUTH, O.WEST, O.NORTH)                # bay 0, 1, 2, 3
DOOR_BAY = AXES.index(O.WEST)


# --- the drum ---------------------------------------------------------------------------------------
def _axis_cell(d):
    """The wall column on an axis: the middle of that side's straight run."""
    body = O.disc(CX, CZ, R)
    n = max(k for k in range(int(R) + 2) if (CX + d[0] * k, CZ + d[1] * k) in body)
    return (CX + d[0] * n, CZ + d[1] * n)


def plan():
    cells = {_axis_cell(d): bay for bay, d in enumerate(AXES)}
    p = O.Plan(O.disc(CX, CZ, R), lambda x, z, outs: O.Bay(FRONT, cells[(x, z)]) if (x, z) in cells else None)
    p.door(FRONT, DOOR_BAY, *DOOR_Y)
    return p


def order():
    # A plain stone drum: no eave, because its east and south faces stand on the pavilion's wall
    # line and may not oversail it; the iron skirt of the dome caps it.
    return [O.Storey(DRUM, "drum", wall=B.ASHLAR_FINE, window=O.Window((WINDOW_Y, WINDOW_Y)))]


def door_cells():
    """[(x, y, z)] of the door leaf: the wall column on the west axis, two rows."""
    x, z = _axis_cell(O.WEST)
    return [(x, y, z) for y in range(DOOR_Y[0], DOOR_Y[1] + 1)]


def drum(canvas, origin=(0, 0, 0), glass=None):
    """The stone drum with its three small windows and the iron door; returns the windows."""
    ox, oy, oz = origin
    windows = O.build(canvas, plan(), order(), origin, glass=glass)
    for (x, y, z), half in zip(door_cells(), ("lower", "upper")):
        canvas.set(ox + x, oy + y, oz + z, f"{B.IRON_DOOR}[facing=east,half={half},hinge=left,open=false]")
    return windows


# --- the dome ---------------------------------------------------------------------------------------
def rib_angles():
    """A rib on every meridian between two gores; a gore's middle lies on each axis (0 = east)."""
    return [(k + 0.5) * 360.0 / GORES for k in range(GORES)]


def _surface(d, r, top):
    """Height of a half-ellipse over the skirt's foot: r wide at the foot, `top` high at the centre."""
    return SKIRT_Y + (top - SKIRT_Y) * math.sqrt(max(0.0, 1.0 - (d / r) ** 2))


def _tops(r, top):
    """{column: (y of its top cell, whole block?)} of a dome r wide at the foot: whole blocks up to
    the surface, a slab where it passes through the middle of a cell."""
    out = {}
    n = int(r) + 1
    for x in range(CX - n, CX + n + 1):
        for z in range(CZ - n, CZ + n + 1):
            d = math.hypot(x - CX, z - CZ)
            if d >= r:
                continue
            h = _surface(d, r, top)
            fl = math.floor(h)
            frac = h - fl
            out[(x, z)] = (fl - 1, True) if frac < 0.25 else (fl, False) if frac < 0.75 else (fl, True)
    return out


def _in_slit(x, z):
    return abs(z - CZ) <= SLIT_HALF and x <= CX + SLIT_PAST


def _on_rib(x, z):
    """Does the column lie on one of the meridians of the ribs (a line one block wide)?"""
    dx, dz = x - CX, z - CZ
    for a in rib_angles():
        ux, uz = math.cos(math.radians(a)), math.sin(math.radians(a))
        if dx * ux + dz * uz > 0 and abs(dx * uz - dz * ux) <= 0.5:
            return True
    return False


def _kind(x, z):
    """What a column of the dome is made of: CAST (the cap the ribs run into, at the head of the
    slit), RIB (a rib, or the rail on either side of the slit) or None for plates."""
    if math.hypot(x - CX, z - CZ) < CAP:
        return CAST
    if abs(z - CZ) == SLIT_HALF + 1 and x <= CX + SLIT_PAST:
        return RIB
    return RIB if _on_rib(x, z) else None


def dome(canvas, origin=(0, 0, 0)):
    """The dome's shell: one block thick, the slit left open from the skirt through the apex, a
    rail on either side of it, the ribs and the cast cap, the darker runs beside the rib feet."""
    ox, oy, oz = origin
    skin = _tops(FOOT, CROWN)

    def put(x, y, z, state):
        canvas.set(ox + x, oy + y, oz + z, state)

    for (x, z), (ytop, whole) in skin.items():
        if _in_slit(x, z):
            continue
        lows = [skin[n][0] if n in skin else SKIRT_Y - 1 for n in (O.step((x, z), d) for d in O.SIDES)]
        first = max(SKIRT_Y, min(ytop, min(lows) + 1))
        metal = _kind(x, z)
        if metal:
            ytop, whole = min(APEX, max(ytop, RIB_FOOT)), True      # a rib's top is a whole block
        for y in range(first, ytop + 1):
            if y == SKIRT_Y:
                put(x, y, z, SKIRT)
            elif metal:
                put(x, y, z, metal)
            elif y == ytop and not whole:
                put(x, y, z, f"{PLATE.slab}[type=bottom]")
            else:
                put(x, y, z, PLATE.block)

    for (x, z), (ytop, _whole) in skin.items():         # the darker runs: beside a rib's foot
        d = math.hypot(x - CX, z - CZ)
        if d < R - 1.5 or _in_slit(x, z) or _kind(x, z):
            continue
        if not any(_kind(*O.step((x, z), s)) == RIB for s in O.SIDES):
            continue
        length = (x * 7 + z * 13) % 3                   # 0..2 rows, the same every time it is built
        for y in range(RIB_FOOT, min(RIB_FOOT + length, ytop + 1)):
            if canvas.get(ox + x, oy + y, oz + z) == PLATE.block:
                put(x, y, z, RUN.block)


# --- the package --------------------------------------------------------------------------------------
def build(canvas, origin=(0, 0, 0), glass=None):
    """The drum and the dome. No display entities (the astrograph and the shutter are A5)."""
    drum(canvas, origin, glass)
    dome(canvas, origin)
    return 0


@functools.lru_cache(maxsize=1)
def _windows():
    return tuple(drum(Canvas()))


def windows():
    """Every window of the drum, as _order.build returns them, for whoever lights them. The front
    is "sdome", the bays 0 east, 1 south, 3 north; the glass is dark (an observing room)."""
    return [{k: v for k, v in w.items() if k != "blind"} for w in _windows() if not w["blind"]]


# --- self-check and drawings ----------------------------------------------------------------------------
def check():
    """What can be told without a picture; returns the findings as lines (none is good)."""
    out = []
    c = Canvas()
    build(c)
    name = lambda x, y, z: (c.get(x, y, z) or "air").partition("[")[0]
    (x0, y0, z0), (x1, y1, z1) = c.bounds()

    # 1. nothing leaves the footprint or stands above the apex row (the east and south faces are
    #    the pavilion's wall faces)
    if (x0, z0, x1, z1) != (S.SMALL_DOME_X[0], S.SMALL_DOME_Z[0], S.SMALL_DOME_X[1], S.SMALL_DOME_Z[1]):
        out.append(f"footprint: the blocks span x {x0}..{x1}, z {z0}..{z1}, not the skeleton's nine by nine")
    if (y0, y1) != (DRUM[0], APEX):
        out.append(f"rows: the blocks span y {y0}..{y1}, not {DRUM[0]}..{APEX}")
    # 2. the slit is open from the skirt through the apex on the west, the cap closes its head
    for x in range(S.SMALL_DOME_X[0], CX + SLIT_PAST + 1):
        for z in range(CZ - SLIT_HALF, CZ + SLIT_HALF + 1):
            if any(c.has(x, y, z) for y in range(SKIRT_Y, APEX + 1)):
                out.append(f"slit: something stands in the slit at x {x}, z {z}")
    if name(CX + SLIT_PAST + 1, APEX, CZ) != CAST:
        out.append("apex: no cast cap at the head of the slit")
    # 3. the room is clear from the floor to under the plates
    for y in range(DRUM[0], APEX):
        if c.has(CX, y, CZ) or c.has(CX + 1, y, CZ):
            out.append(f"room: something stands inside at y {y}")
    # 4. the skirt is a closed iron ring outside the slit
    ring = [c for c, outs in plan().outs.items() if outs]
    if any(name(x, SKIRT_Y, z) != SKIRT for x, z in ring if not _in_slit(x, z)):
        out.append(f"skirt: the ring at y {SKIRT_Y} is not riveted iron all round")
    # 5. three dark windows and the door
    if sorted(w["bay"] for w in windows()) != [b for b in range(len(AXES)) if b != DOOR_BAY]:
        out.append(f"drum: windows in bays {sorted(w['bay'] for w in windows())}")
    if any(name(*cell) != B.IRON_DOOR for cell in door_cells()):
        out.append("drum: no door leaf on the west axis")
    # 6. a rib on every meridian reaches from the skirt to the cap
    for a in rib_angles():
        x = CX + int(round(math.cos(math.radians(a)) * (R - 0.4)))
        z = CZ + int(round(math.sin(math.radians(a)) * (R - 0.4)))
        if name(x, RIB_FOOT, z) != RIB:
            out.append(f"rib at {a:.1f} degrees: no foot on the skirt at ({x}, {z})")
    return out


def _heights(c):
    """The dome from above: the top face of every column, in half blocks (. the open slit)."""
    lines = []
    for z in range(S.SMALL_DOME_Z[0], S.SMALL_DOME_Z[1] + 1):
        row = []
        for x in range(S.SMALL_DOME_X[0], S.SMALL_DOME_X[1] + 1):
            top = max((y for y in range(SKIRT_Y, APEX + 1) if c.has(x, y, z)), default=None)
            if top is None:
                row.append("  .  " if (x, z) in O.disc(CX, CZ, R) else "     ")
                continue
            state = c.get(x, top, z)
            face = top + (0.5 if "slab" in state else 1.0)
            row.append(f"{face:4.1f}{O.mark(state)}")
        lines.append(f"z {z}  " + " ".join(row))
    return "\n".join(lines)


def _drawings():
    O.MARKS.setdefault(CAST, "A")
    O.MARKS.setdefault(B.IRON_DOOR, "J")
    c = Canvas()
    build(c)
    xs = (S.SMALL_DOME_X[0] - 2, S.SMALL_DOME_X[1] + 2)
    zs = (S.SMALL_DOME_Z[0] - 2, S.SMALL_DOME_Z[1] + 2)
    ys = (DRUM[0] - 1, APEX + 1)
    print("PLAN of the drum (north up; # wall, : inner leaf, w window, D door, + not built):\n")
    print(O.drawing(plan()))
    print(f"\nFROM ABOVE (north up, x {S.SMALL_DOME_X[0]}..{S.SMALL_DOME_X[1]}): top face and material of every column\n")
    print(_heights(c))
    print(f"\nSECTION through the slit (z = {CZ}, west on the left); the west half is open:\n")
    print(O.section(c, "z", CZ, xs, ys))
    print(f"\nSECTION across the slit (x = {CX - 1}, north on the left):\n")
    print(O.section(c, "x", CX - 1, zs, ys))
    print("\nEAST ELEVATION, from the court (south on the left):\n")
    print(O.elevation(c, "east", zs, ys, xs[1], xs[0]))
    print("\nSOUTH ELEVATION (west on the left):\n")
    print(O.elevation(c, "south", xs, ys, zs[1], zs[0]))
    print("\nWEST ELEVATION, the slit and the door (north on the left):\n")
    print(O.elevation(c, "west", zs, ys, xs[0], xs[1]))
    print("\nLetters: F dressed ashlar, D dark window, J iron door, I riveted iron, V verdigris plate,")
    print("G rib, A cast cap, X darker run. Small letters are slabs.")


if __name__ == "__main__":
    if "check" not in sys.argv[1:]:
        _drawings()
        print()
    found = check()
    print("\n".join(found) if found else "self-check: footprint, slit, room, skirt, windows and door, ribs -- all good")
    sys.exit(1 if found else 0)
