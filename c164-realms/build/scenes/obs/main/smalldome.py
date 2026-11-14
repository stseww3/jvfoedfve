"""main/smalldome -- the small dome on the south end pavilion, above the parapet. A verdigris dome
a size down from the great dome: a short stone drum with a corbelled head, an iron skirt where the
track sits, copper plates, and an observing slit that looks west with its shutter slid aside. The
astrograph (machines) stands inside.

Card: plan/packages/main/smalldome.md. Design: plan/ART-PLAN.md 5.2 and 6.3, plan/parts/main.md 6.3.

Where it sits (skeleton SMALL_*): the pavilion is bays 16-17 (z 26..34), its east wall face x 16;
the dome is x 8..16, z 26..34, nine across, centred on cell (12, 30). It stands on the pavilion's
flat roof (deck y 17, feet y 18). Its east and south sides come out to the pavilion's wall faces,
so nothing of it may reach past x 16 or z 34, and nothing above the apex row y 25.

Rows, bottom to top:
    y 18..19  the stone body, seven across and one block thick: it stands one block inside the
              dome's foot, so the dome reads as the larger of the two. A small dark window over a
              sunk panel on the east, south and north axes; an iron door on the west, onto the
              pavilion's terrace.
    y 20      the head of the drum: a stone corbel (stairs hung upside down) that widens the body
              to the nine of the dome. Its lip is flush with the pavilion's wall faces.
    y 21      the iron skirt, the ring the dome turns on.
    y 22..25  the dome: copper plates only, whole blocks and slabs, one block at the apex.

What a dome nine blocks across can carry (c219 #23263, A0 #23752): no ribs -- eight ribs took half
its surface and read as patches, four would draw a cross on its top from above; the top row is one
cast block on the axis, the plates fall away from it by half blocks; a slit one block wide, from
the skirt up to the apex block, and beside it the shutter leaf slid open to the south, riveted
iron lying half a block proud of the plates; three darker plates in the first row over the skirt.

Not here: the pavilion walls and the deck under the drum (main/facade.py, c206); the astrograph
(machines, A5); the terrace paving, the flashing at the drum's foot and the ridge walkway that
leads here (main/roof.py, same card).

    python -m scenes.obs.main.smalldome          # text sections and a self-check
    python -m scenes.obs.main.smalldome check    # the self-check alone (exit code 1 on a finding)
"""
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

BODY_Y = (S.SMALL_DRUM_BASE, S.SMALL_DRUM_BASE + 1)      # 18..19: the stone body
WINDOW_Y = BODY_Y[1]                                     # 19
DOOR_Y = BODY_Y                                          # 18..19: the door onto the terrace
HEAD_Y = BODY_Y[1] + 1                                   # 20: the corbel
SKIRT_Y = HEAD_Y + 1                                     # 21: the iron skirt; the dome's curve starts at its foot
APEX = S.SMALL_DOME_APEX                                 # 25: the last row anything stands in
FOOT = R + 0.25                                          # the half-ellipse the plates follow: this wide at
RISE = APEX + 0.8 - SKIRT_Y                              # the skirt's foot, this high on the axis -- the
#                                                          apex block alone reaches the top of row 25
SLIT_X = (S.SMALL_DOME_X[0], CX - 1)                     # the slit: the west axis row, up to the apex block
LEAF_Z = CZ + 1                                          # the shutter leaf lies south of the slit
LEAF_PROUD = 0.5                                         # and this far over the plates
RUNS = ((CX + 4, CZ + 1), (CX - 1, CZ + 4), (CX + 3, CZ - 3))   # the darker plates, in the row over the skirt

PLATE, RUN, CAST = B.VERDIGRIS_CUT, B.VERDIGRIS_STREAK, B.VERDIGRIS_CAST
STONE, PANEL = B.ASHLAR_FINE, B.ASHLAR_PANEL
IRON = B.IRON_RIVETED
SKIRT = IRON.block
GLASS = B.WINDOW_DARK.pane                               # a pane: the glass stands back in a wall one block thick
FRONT = "sdome"                                          # the front's name in windows()
AXES = (O.EAST, O.SOUTH, O.WEST, O.NORTH)                # bay 0, 1, 2, 3
DOOR_BAY = AXES.index(O.WEST)

DOME = frozenset(O.disc(CX, CZ, R))                      # nine across: the foot of the dome
BODY = frozenset(O.disc(CX, CZ, R - 1))                  # seven across: the stone body
WALL = frozenset(c for c in BODY if any(O.step(c, d) not in BODY for d in O.SIDES))
ROOM = BODY - WALL                                       # the floor inside: five across
RING = frozenset(O.ring(BODY))                           # the columns of the corbel and the skirt


# --- the drum ---------------------------------------------------------------------------------------
def _axis_cell(d):
    """The body's wall column on an axis: the middle of that side's straight run."""
    n = max(k for k in range(int(R) + 2) if (CX + d[0] * k, CZ + d[1] * k) in BODY)
    return (CX + d[0] * n, CZ + d[1] * n)


def door_cells():
    """[(x, y, z)] of the door leaf: the wall column on the west axis, two rows."""
    x, z = _axis_cell(O.WEST)
    return [(x, y, z) for y in range(DOOR_Y[0], DOOR_Y[1] + 1)]


def windows():
    """Every window of the drum, in the form _order.build returns them, for whoever lights them.
    The front is "sdome", the bays 0 east, 1 south, 3 north; the glass is dark (an observing room)."""
    return [dict(front=FRONT, bay=bay, storey="drum", cells=[_axis_cell(d)], inward=(-d[0], -d[1]),
                 y=(WINDOW_Y, WINDOW_Y), blind=False, glass=GLASS)
            for bay, d in enumerate(AXES) if bay != DOOR_BAY]


def drum(canvas, origin=(0, 0, 0), glass=None):
    """The stone body with its three small windows and the iron door, the corbel and the skirt;
    returns the windows. glass(front, bay, storey) may name another window role for a bay."""
    ox, oy, oz = origin

    def put(x, y, z, state):
        canvas.set(ox + x, oy + y, oz + z, state)

    for x, z in WALL:
        for y in range(BODY_Y[0], BODY_Y[1] + 1):
            put(x, y, z, STONE.block)
    out = windows()
    for w in out:
        role = glass(w["front"], w["bay"], w["storey"]) if glass else None
        if role is not None:
            w["glass"] = role.pane if isinstance(role, B.Family) else role
        (x, z), = w["cells"]
        put(x, WINDOW_Y, z, w["glass"])
        put(x, WINDOW_Y - 1, z, PANEL.block)
    for (x, y, z), half in zip(door_cells(), ("lower", "upper")):
        put(x, y, z, f"{B.IRON_DOOR}[facing=east,half={half},hinge=left,open=false]")
    O.Laying(canvas, None, origin, None).mould(BODY, HEAD_Y, STONE.stairs, "top")
    for x, z in RING:
        put(x, SKIRT_Y, z, SKIRT)
    return out


# --- the dome ---------------------------------------------------------------------------------------
def _in_slit(x, z):
    return z == CZ and SLIT_X[0] <= x <= SLIT_X[1]


def _is_leaf(x, z):
    return z == LEAF_Z and SLIT_X[0] <= x <= SLIT_X[1]


def _skin():
    """{column: top face} of the dome in half blocks: a half-ellipse FOOT wide at the skirt's foot
    and RISE high, rounded to the nearer half; the shutter leaf lies LEAF_PROUD over it, but never
    as high as the apex block."""
    out = {}
    for x, z in DOME:
        d = math.hypot(x - CX, z - CZ)
        top = round(2 * (SKIRT_Y + RISE * math.sqrt(1.0 - (d / FOOT) ** 2))) / 2.0
        if _is_leaf(x, z):
            top = min(top + LEAF_PROUD, APEX + 0.5)
        out[(x, z)] = max(top, SKIRT_Y + 1.5)
    return out


def _foot(skin, col):
    """The lowest row a column of the shell must fill so that no gap opens under it: down to the
    top face of its lowest neighbour, and to the skirt where it stands on the dome's edge. The
    slit is no neighbour: its sides show the thickness of the shell."""
    low = APEX
    for d in O.SIDES:
        n = O.step(col, d)
        if n not in DOME:
            low = SKIRT_Y + 1
        elif n in skin:
            low = min(low, math.floor(skin[n]))
    return max(low, SKIRT_Y + 1)


def dome(canvas, origin=(0, 0, 0)):
    """The dome's shell, one block thick: plates, the cast block at the apex, the slit left open
    from the skirt to the apex block, the shutter leaf beside it and the three darker plates."""
    ox, oy, oz = origin
    skin = {c: top for c, top in _skin().items() if not _in_slit(*c)}
    for (x, z), top in skin.items():
        ytop = math.ceil(top) - 1                       # the cell the top face lies in
        whole = top == ytop + 1
        metal = IRON if _is_leaf(x, z) else PLATE
        for y in range(min(ytop, _foot(skin, (x, z))), ytop + 1):
            if (x, z) == (CX, CZ):
                state = CAST
            elif y == ytop and not whole:
                state = f"{metal.slab}[type=bottom]"
            elif (x, z) in RUNS and y == SKIRT_Y + 1:
                state = RUN.block
            else:
                state = metal.block
            canvas.set(ox + x, oy + y, oz + z, state)


# --- the package --------------------------------------------------------------------------------------
def build(canvas, origin=(0, 0, 0), glass=None):
    """The drum and the dome. No display entities (the astrograph is A5's)."""
    drum(canvas, origin, glass)
    dome(canvas, origin)
    return 0


# --- self-check and drawings ----------------------------------------------------------------------------
def check():
    """What can be told without a picture; returns the findings as lines (none is good)."""
    out = []
    c = Canvas()
    build(c)
    name = lambda x, y, z: (c.get(x, y, z) or "air").partition("[")[0]
    (x0, y0, z0), (x1, y1, z1) = c.bounds()
    skin = _skin()

    # 1. nothing leaves the footprint or stands above the apex row (the east and south sides come
    #    out to the pavilion's wall faces)
    if (x0, z0, x1, z1) != (S.SMALL_DOME_X[0], S.SMALL_DOME_Z[0], S.SMALL_DOME_X[1], S.SMALL_DOME_Z[1]):
        out.append(f"footprint: the blocks span x {x0}..{x1}, z {z0}..{z1}, not the skeleton's nine by nine")
    if (y0, y1) != (BODY_Y[0], APEX):
        out.append(f"rows: the blocks span y {y0}..{y1}, not {BODY_Y[0]}..{APEX}")
    if not RING <= DOME:
        out.append("drum: the corbel's ring is not inside the dome's foot")
    # 2. the top: one block on the axis, nothing else as high
    high = [col for col, top in skin.items() if top > APEX + 0.5 and not _in_slit(*col)]
    if high != [(CX, CZ)] or name(CX, APEX, CZ) != CAST:
        out.append(f"apex: the columns that reach the top of row {APEX} are {sorted(high)}, not the cast block alone")
    # 3. the slit is open from the skirt to the apex block, and the skirt runs on under it
    for x in range(SLIT_X[0], SLIT_X[1] + 1):
        if any(c.has(x, y, CZ) for y in range(SKIRT_Y + 1, APEX + 1)):
            out.append(f"slit: something stands in the slit at x {x}")
    # 4. the shell is closed everywhere else: seen from above no column is missing, and no step
    #    between two neighbours is higher than the blocks that stand under the upper one
    for col, top in skin.items():
        if _in_slit(*col):
            continue
        cells = [y for y in range(SKIRT_Y + 1, APEX + 1) if c.has(col[0], y, col[1])]
        if not cells or cells != list(range(cells[0], cells[-1] + 1)):
            out.append(f"shell: column {col} is missing or broken")
            continue
        for d in O.SIDES:
            n = O.step(col, d)
            if n not in DOME and cells[0] != SKIRT_Y + 1:
                out.append(f"shell: a gap between the skirt and column {col} on the dome's edge")
            if n in skin and not _in_slit(*n) and cells[0] > skin[n]:
                out.append(f"shell: a gap under column {col} over its neighbour {n}")
    # 5. the room is clear from the floor to under the plates
    for x, z in ROOM:
        for y in range(BODY_Y[0], SKIRT_Y + 1):
            if c.has(x, y, z):
                out.append(f"room: something stands inside at ({x}, {y}, {z})")
    for y in range(BODY_Y[0], APEX - 1):
        if c.has(CX, y, CZ):
            out.append(f"room: something stands on the axis at y {y}")
    # 6. the skirt is a closed iron ring, the corbel a closed stone one
    if any(name(x, SKIRT_Y, z) != SKIRT for x, z in RING):
        out.append(f"skirt: the ring at y {SKIRT_Y} is not riveted iron all round")
    if any(name(x, HEAD_Y, z) != STONE.stairs for x, z in RING):
        out.append(f"corbel: the ring at y {HEAD_Y} is not stone stairs all round")
    # 7. three dark windows and the door
    for w in windows():
        (x, z), = w["cells"]
        if name(x, WINDOW_Y, z) != GLASS:
            out.append(f"drum: no window in bay {w['bay']}")
    if any(name(*cell) != B.IRON_DOOR for cell in door_cells()):
        out.append("drum: no door leaf on the west axis")
    return out


def _heights(c):
    """The dome from above: the top face of every column, in half blocks (. the open slit)."""
    lines = []
    for z in range(S.SMALL_DOME_Z[0], S.SMALL_DOME_Z[1] + 1):
        row = []
        for x in range(S.SMALL_DOME_X[0], S.SMALL_DOME_X[1] + 1):
            top = max((y for y in range(SKIRT_Y + 1, APEX + 1) if c.has(x, y, z)), default=None)
            if top is None:
                row.append("  .  " if (x, z) in DOME else "     ")
                continue
            state = c.get(x, top, z)
            face = top + (0.5 if "slab" in state else 1.0)
            row.append(f"{face:4.1f}{O.mark(state)}")
        lines.append(f"z {z}  " + " ".join(row))
    return "\n".join(lines)


def _plan(c, y):
    """One row of the drum from above (north up)."""
    lines = []
    for z in range(S.SMALL_DOME_Z[0], S.SMALL_DOME_Z[1] + 1):
        lines.append(f"z {z}  " + " ".join(O.mark(c.get(x, y, z)) if c.has(x, y, z) else "."
                                         for x in range(S.SMALL_DOME_X[0], S.SMALL_DOME_X[1] + 1)))
    return "\n".join(lines)


def _drawings():
    O.MARKS.setdefault(CAST, "A")
    O.MARKS.setdefault(B.IRON_DOOR, "J")
    c = Canvas()
    build(c)
    xs = (S.SMALL_DOME_X[0] - 2, S.SMALL_DOME_X[1] + 2)
    zs = (S.SMALL_DOME_Z[0] - 2, S.SMALL_DOME_Z[1] + 2)
    ys = (BODY_Y[0] - 1, APEX + 1)
    for y, what in ((WINDOW_Y, "the body at the windows"), (HEAD_Y, "the corbel")):
        print(f"PLAN at y {y}, {what} (north up, x {S.SMALL_DOME_X[0]}..{S.SMALL_DOME_X[1]}):\n")
        print(_plan(c, y))
        print()
    print("FROM ABOVE: top face and material of every column of the dome\n")
    print(_heights(c))
    print(f"\nSECTION through the slit (z = {CZ}, west on the left):\n")
    print(O.section(c, "z", CZ, xs, ys))
    print(f"\nSECTION across the slit (x = {CX - 2}, north on the left):\n")
    print(O.section(c, "x", CX - 2, zs, ys))
    print("\nEAST ELEVATION, from the court (south on the left):\n")
    print(O.elevation(c, "east", zs, ys, xs[1], xs[0]))
    print("\nSOUTH ELEVATION (west on the left):\n")
    print(O.elevation(c, "south", xs, ys, zs[1], zs[0]))
    print("\nWEST ELEVATION, the slit and the door (north on the left):\n")
    print(O.elevation(c, "west", zs, ys, xs[0], xs[1]))
    print("\nLetters: F dressed ashlar, P sunk panel, D dark window, J iron door, I riveted iron,")
    print("V verdigris plate, A cast block, X darker plate. Small letters are slabs and stairs.")


if __name__ == "__main__":
    if "check" not in sys.argv[1:]:
        _drawings()
        print()
    found = check()
    print("\n".join(found) if found else
          "self-check: footprint, apex, slit, shell, room, skirt and corbel, windows and door -- all good")
    sys.exit(1 if found else 0)
