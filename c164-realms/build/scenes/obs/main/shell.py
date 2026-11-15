"""main/shell -- the inside of the main building: its plan, floors, stairs and empty rooms.
Card: plan/packages/main/shell.md. This module is the interior plan (A0 #20299: a file of its own;
main/_plan.py keeps the walls) and the package that builds it.

What it builds, inside the walls main/facade.py lays (it fills facade.shell().core and nothing of
the wall or its inner leaf):

  * the star hall and the apse as one room, two storeys high (feet 0, ceiling 14): a stone floor,
    the cross walls on z -6 and 6, the ceiling;
  * the west arcade (x 0..1): three arches as wide as the three of the entrance. The middle one
    leads under the mezzanine to the west door; a flight of the grand stair rises west through
    each of the others (seven steps, feet 0 -> 7) to a landing against the apse wall;
  * the main floor round the well: the mezzanine over the way to the west door, the cross gallery
    on the arcade, a gallery along each cross wall (z -5 and 5, its railing on z -4 and 4), a door
    from each gallery into its wing room;
  * the telescope pier: a shaft 3 x 3 from the ground, a cap 5 x 5 in the dome-room floor. Nothing
    of the building touches it: an iron grating round its foot, an open slot at the gallery, an
    open ring in the ceiling and in the dome-room floor;
  * the ring stair (A0 #20004; the steps are c206's count, #20483): 22 half-block steps on the
    outermost ring of the envelope, clockwise from the south gallery (a bridge at (7, 4)) to the
    east side of the cap, where one steps off onto the dome-room floor at (8, 0); a balustrade of
    iron panels on both sides, the inner one in the steps' own cells so the ring stays empty;
  * the wing rooms of the main floor (time-service room north, star-chart room south): floor,
    ceiling, the wall towards the rotunda, the wall towards the end pavilion;
  * the dome-room floor, with the envelope left open and a railing round it.

The ground floor of the wings, the end pavilions and the pockets of the apse beside the cross walls
stay closed. Furniture, wall panelling, beams, lamps, machines: the interiors, props and machines
lines. ROOMS below is what they read.

    python -m scenes.obs.main.shell            # the three plans, the stair tables, the self-check
    python -m scenes.obs.main.shell check      # the self-check alone (exit code 1 on a finding)
"""
import contextlib
import functools
import sys
import types

from artkit.canvas import Canvas

from ..common import blocks as B
from ..common import skeleton as S
from . import _order as O
from . import facade

ORDER = 60                      # after the walls (facade), before the rooms that move in (80)

CX, CZ = S.DOME_CENTRE
CROSS_Z = S.STAR_HALL_Z[1]                      # 6: the cross walls stand on z -6 and 6
HALL_Z = CROSS_Z - 1                            # 5: the hall is clear over z -5..5
PAVILION_Z = S.pilaster_z(15)                   # 26: the walls between the wings and the end pavilions
WING_Z = (CROSS_Z + 1, PAVILION_Z - 1)          # |z| 7..25: the wing rooms
DECK_Y = S.STRING                               # 6: the block of every deck of the main floor; feet at 7
CEIL_Y = S.STAR_HALL_CEIL                       # 14: the ceiling block of the hall and of the wing rooms
ROOF_Y = S.ROOF_FLOOR                           # 17: the block of the dome-room floor; feet at 18

# the grand stair: two flights, in the bays either side of the axis, rising west into the apse
FLIGHT_ROWS = {-1: (-5, -4, -3), 1: (3, 4, 5)}  # bay 8 and bay 10
FLIGHT_X = (1, -5)                              # the first and the last step
LANDING_X = FLIGHT_X[1] - 1                     # -6
CHEEK_Z = 2                                     # the cheeks stand on z -2 and 2, the pilaster lines
ARCADE_X = (0, 1)                               # the west arcade: where the west wall would cross the hall
ARCH_Y = S.BASE[1]                              # 5: the row of the arch heads, as in the entrance
ROOM_DOOR_X = (7, 8)                            # gallery -> wing room, through a cross wall
ROOM_DOOR_Y = (S.STAND, S.STAND + 2)
GALLERY_X = (S.ROOM_X[0], S.ROOM_X[1])          # 2..13: the side galleries
BRIDGE = (7, HALL_Z - 1)                        # (7, 4): the gap in the south railing where the ring stair starts
EXIT = (S.PIER_ENVELOPE[2] + 1, CZ)             # (8, 0): the dome-room floor one steps onto

FLOOR = B.ASHLAR_FINE.block                     # the hall's ground floor, until the star hall lays its own
DECK = B.ASHLAR_FINE.block                      # galleries, mezzanine, landings
ROOM_FLOOR = B.FLOOR_WOOD.block                 # wing rooms and the dome room
CEILING = B.DARK_WOOD.block
RAIL = B.IRON_BARS
GRATING = B.IRON_GRATE
TREAD = B.IRON_RIVETED
PANEL = B.IRON_HATCH                            # an iron hatch on edge: the thin balustrade panel
TRIM = B.IRON_RIVETED.block                     # the iron curb round the stair's opening, ceiling to floor

ROOMS = {
    # the clear inside of each room: box (x0, z0, x1, z1), where feet stand, the ceiling block's row
    "star hall": dict(box=(S.ROOM_X[0], -HALL_Z, 15, HALL_Z), feet=S.GROUND, ceiling=CEIL_Y,
                      note="open to the apse on the west; galleries at feet 7 on z -5 and 5"),
    "stair hall": dict(box=(-7, -HALL_Z, ARCADE_X[1], HALL_Z), feet=S.GROUND, ceiling=CEIL_Y,
                       note="the apse: the two flights, the way to the west door, the mezzanine over it"),
    "time room": dict(box=(S.ROOM_X[0], -WING_Z[1], S.ROOM_X[1], -WING_Z[0]), feet=S.STAND, ceiling=CEIL_Y,
                      note="north wing, main floor; door at x 7..8 in the wall on z -6"),
    "chart room": dict(box=(S.ROOM_X[0], WING_Z[0], S.ROOM_X[1], WING_Z[1]), feet=S.STAND, ceiling=CEIL_Y,
                       note="south wing, main floor; door at x 7..8 in the wall on z 6"),
    "dome room": dict(centre=S.DOME_CENTRE, radius=S.DOME_R - 2, feet=S.ROOF_STAND, ceiling=None,
                      note="inside the drum; the envelope x 1..7, z -3..3 is open, the stair comes up at (7, 0)"),
}


# --- the plan -------------------------------------------------------------------------------------
def wall_block(y):
    """The stone of an inside wall, in the bands of the fronts: plinth, base storey, a sunk course
    at the foot and at the head of the main storey."""
    if y <= S.PLINTH[1]:
        return B.SLATE_BRICK.block
    if y <= S.BASE[1]:
        return B.ASHLAR_ROUGH.block
    if y in (S.PANEL, S.WINDOW[1]):
        return B.ASHLAR_PANEL.block
    return B.ASHLAR_FINE.block


def pier_block(y):
    if y <= S.PLINTH[1]:
        return B.SLATE_BRICK.block
    return B.ASHLAR_ROUGH.block if y <= S.BASE[1] else B.ASHLAR_FINE.block


def grand_stair():
    """One flight: [(x, y of the stair block)], rising west from the hall floor; feet reach 7 on the
    landing at LANDING_X. Both flights are the same; FLIGHT_ROWS gives their rows."""
    return [(x, S.GROUND + i) for i, x in enumerate(range(FLIGHT_X[0], FLIGHT_X[1] - 1, -1))]


def ring_track():
    """The outermost ring of the envelope, clockwise from its south-east corner: south side going
    west, west side going north, north side going east, east side going south."""
    x0, z0, x1, z1 = S.PIER_ENVELOPE
    return ([(x, z1) for x in range(x1, x0 - 1, -1)] + [(x0, z) for z in range(z1 - 1, z0 - 1, -1)]
            + [(x, z0) for x in range(x0 + 1, x1 + 1)] + [(x1, z) for z in range(z0 + 1, z1)])


def ring_stair():
    """The ring stair: [(x, z, y, half, top)]. A step is a slab in cell y, in its lower or its
    upper half; top is the height of its tread. 22 steps of half a block from feet 7 to 18."""
    steps = 2 * (S.RING_STAIR["y1"] - S.RING_STAIR["y0"])
    out = []
    for i, (x, z) in enumerate(ring_track()[:steps]):
        y = S.RING_STAIR["y0"] + i // 2
        out.append((x, z, y, "top" if i % 2 else "bottom", y + (1.0 if i % 2 else 0.5)))
    return out


@functools.lru_cache(maxsize=1)
def layout():
    """Every set of columns the shell is built from, once."""
    L = types.SimpleNamespace()
    core = set(facade.shell().core)
    L.core = core
    L.hall = {c for c in core if abs(c[1]) <= HALL_Z}                    # star hall and apse, one room
    L.shaft = O.box(*S.PIER_SHAFT)
    L.cap = O.box(*S.PIER_CAP)
    L.envelope = O.box(*S.PIER_ENVELOPE)
    L.gap = L.cap - L.shaft                                               # the ring nothing stands in
    L.track = L.envelope - L.cap                                          # the ring the stair runs on
    L.curb = O.ring(L.envelope)                                           # one block outside the envelope
    # walls
    L.cross = {c for c in core if abs(c[1]) == CROSS_Z}
    L.doors = {(x, s * CROSS_Z) for x in ROOM_DOOR_X for s in (-1, 1)}
    L.partition = {c for c in core if abs(c[1]) == PAVILION_Z}
    L.west = {c for c in core if c[0] == S.GLASS_W and abs(c[1]) > CROSS_Z}   # the wings' wall to the rotunda
    L.rooms = {name: O.box(*ROOMS[name]["box"]) & core for name in ("time room", "chart room")}
    # the stair hall
    L.flights = {s: [(x, y, z) for x, y in grand_stair() for z in rows] for s, rows in FLIGHT_ROWS.items()}
    L.landing = {(LANDING_X, z) for rows in FLIGHT_ROWS.values() for z in rows if (LANDING_X, z) in core}
    L.cheek = {(x, s * CHEEK_Z) for x in range(LANDING_X, ARCADE_X[0]) for s in (-1, 1)}
    L.arcade = {(x, s * CHEEK_Z) for x in ARCADE_X for s in (-1, 1)}
    L.arches = [(-5, -3), (-1, 1), (3, 5)]                                # rows of the three openings
    # decks of the main floor
    L.mezzanine = {c for c in L.hall if c[0] < ARCADE_X[0] - 1 and abs(c[1]) < CHEEK_Z}
    L.cross_deck = O.box(ARCADE_X[0] - 1, -HALL_Z, ARCADE_X[1], HALL_Z)
    L.gallery = {(x, s * HALL_Z) for x in range(GALLERY_X[0], GALLERY_X[1] + 1) for s in (-1, 1)}
    L.gallery_edge = {(x, s * (HALL_Z - 1)) for x in range(GALLERY_X[0], GALLERY_X[1] + 1) for s in (-1, 1)}
    # the cross gallery's east railing steps back round the slot in front of the pier
    notch = [(2, 3), (2, 2), (1, 2), (1, 1), (1, 0)]
    L.notch = {(x, s * z) for x, z in notch for s in (-1, 1)}
    L.deck = (L.mezzanine | L.cross_deck | L.gallery | L.gallery_edge | L.landing | L.notch
              | {c for c in L.cheek})
    L.rail = ((L.gallery_edge - {BRIDGE}) | L.notch
              | {(ARCADE_X[0] - 1, z) for rows in FLIGHT_ROWS.values() for z in rows}       # over the flights
              | {c for c in L.cheek if LANDING_X < c[0] < ARCADE_X[0] - 1})                 # on the cheeks
    L.walk = L.deck - L.rail                                              # where feet stand at 7
    # above
    L.ceiling = L.hall - L.envelope
    L.dome_floor = O.shrink(O.shrink(O.disc(CX, CZ, S.DOME_R))) - L.envelope
    L.dome_rail = L.curb - {EXIT}
    return L


SIDE = {"north": (0, -1), "south": (0, 1), "west": (-1, 0), "east": (1, 0)}
OPPOSITE = {"north": "south", "south": "north", "west": "east", "east": "west"}


def panel(side):
    """An iron hatch standing on edge on that side of its cell."""
    return f"{PANEL}[facing={OPPOSITE[side]},half=bottom,open=true]"      # it stands on the side it turns its back to


def stair_panels():
    """The ring stair's balustrades: [((x, y, z), side, inner)] -- an iron hatch on edge (3 pixels
    thick) in that cell, standing on that side of it, in the row over the step's slab.

    Inner side: a block in the open ring would touch the pier, so the panel stands in the step's own
    cell, on its inner edge; where the stair turns, the two neighbours' panels meet at the corner.
    Outer side: in the cell beside the step, against it. build() leaves a panel out where the
    building already stands beside the step (the gallery's deck at the bridge, the ceiling, the
    curb, the dome-room floor and its railing, the pier's corbel and cap). The first step has an
    end panel two rows high on the east and one towards the unused part of the ring; a panel in
    that part closes the south side of the last step."""
    x0, z0, x1, z1 = S.PIER_ENVELOPE
    stair = ring_stair()
    cells = [(x, z) for x, z, _y, _half, _top in stair]
    out = []
    for i, (x, z, y, _half, _top) in enumerate(stair):
        for side, (dx, dz) in SIDE.items():
            n = (x + dx, z + dz)
            if n in cells[max(i - 1, 0):i + 2] or n == (BRIDGE if i == 0 else EXIT if i == len(stair) - 1 else None):
                continue
            if x0 <= n[0] <= x1 and z0 <= n[1] <= z1:               # towards the pier, or along the ring
                out.append(((x, y + 1, z), side, True))
            else:
                out.append(((n[0], y + 1, n[1]), OPPOSITE[side], False))
    (x, z, y, _half, _top), last = stair[0], stair[-1]
    out.append(((x + 1, y, z), "west", False))                      # the foot's end panel, down to the deck
    out = [p for p in out if p[0] != (last[0], last[2] + 1, last[1]) or p[1] != "south"]
    out.append(((last[0], last[2] + 1, last[1] + 1), "north", False))
    return out


@contextlib.contextmanager
def hall_open():
    """Build the main line inside this block to get the hall as it stands once the facade's
    stand-in behind the entrance is gone (facade.SCREEN: a pale wall across the hall at x 11, kept
    until the hall is fitted out and lit). The shell lays over what it shares with the stand-in
    and leaves the rest; test scenes that show the hall, and the self-check, build without it."""
    was = getattr(facade, "SCREEN", None)
    if was is not None:
        facade.SCREEN = False
    try:
        yield
    finally:
        if was is not None:
            facade.SCREEN = was


# --- the package ------------------------------------------------------------------------------------
def build(canvas, origin=(0, 0, 0)):
    ox, oy, oz = origin
    L = layout()

    def put(c, y, state):
        canvas.set(ox + c[0], oy + y, oz + c[1], state)

    def clear(c, y):
        canvas.clear(ox + c[0], oy + y, oz + c[1])

    # the ground floor of the hall; a grating keeps it off the pier's foot
    for c in L.hall:
        put(c, S.PAVING_Y, GRATING if c in L.gap else FLOOR)

    # walls: the cross walls with the doors of the wing rooms, the walls that close the wing rooms
    # (up to the cornice row: the drum's stone and the gables stand on the row above)
    for c in L.cross | L.west | L.partition:
        for y in range(S.GROUND, S.DRUM_BASE):
            put(c, y, wall_block(y))
    for c in L.doors:
        for y in range(ROOM_DOOR_Y[0], ROOM_DOOR_Y[1] + 1):
            clear(c, y)

    # the wing rooms
    for cells in L.rooms.values():
        for c in cells:
            put(c, DECK_Y, ROOM_FLOOR)
            put(c, CEIL_Y, CEILING)

    # the west arcade and the cheeks of the flights
    for c in L.cheek | L.arcade:
        for y in range(S.GROUND, DECK_Y):
            put(c, y, wall_block(y))
    for z0, z1 in L.arches:
        for x in ARCADE_X:
            put((x, z0), ARCH_Y, f"{B.ASHLAR_ROUGH.stairs}[facing=north,half=top]")
            put((x, z1), ARCH_Y, f"{B.ASHLAR_ROUGH.stairs}[facing=south,half=top]")

    # the grand stair: solid under the steps and under the landings
    for cells in L.flights.values():
        for x, y, z in cells:
            for yy in range(S.GROUND, y):
                put((x, z), yy, wall_block(yy))
            put((x, z), y, f"{B.ASHLAR_FINE.stairs}[facing=west,half=bottom]")
    for c in L.landing:
        for y in range(S.GROUND, DECK_Y):
            put(c, y, wall_block(y))

    # the decks of the main floor and their railings; a cove carries the side galleries
    for c in L.deck:
        put(c, DECK_Y, DECK)
    for c in L.rail:
        put(c, S.STAND, RAIL)
    for c in L.gallery:
        put(c, DECK_Y - 1, f"{B.ASHLAR_FINE.stairs}[facing={'north' if c[1] < 0 else 'south'},half=top]")

    # the ceiling of the hall, and the curb round the stair's opening up to the dome-room floor
    for c in L.ceiling:
        put(c, CEIL_Y, CEILING)
    for c in L.curb:
        for y in range(CEIL_Y + 1, ROOF_Y):
            put(c, y, TRIM)

    # the dome-room floor (it lays over the facade's stand-in deck) and the railing round the opening
    for c in L.envelope:
        clear(c, ROOF_Y)
    for c in L.dome_floor:
        put(c, ROOF_Y, ROOM_FLOOR)
    for c in L.dome_rail:
        put(c, S.ROOF_STAND, RAIL)

    # the telescope pier: the shaft, a corbel course, the cap in the course of the dome-room floor
    for c in L.shaft:
        for y in range(S.GROUND, ROOF_Y):
            put(c, y, pier_block(y))
    O.Laying(canvas, None, origin, None).mould(L.shaft, ROOF_Y - 1, B.ASHLAR_FINE.stairs, "top")
    for c in L.cap:
        put(c, ROOF_Y, B.ASHLAR_FINE.block)

    # the ring stair: the steps and the panels on both sides of them
    for x, z, y, half, _top in ring_stair():
        put((x, z), y, f"{TREAD.slab}[type={half}]")
    for (x, y, z), side, inner in stair_panels():
        dx, dz = SIDE[side]
        if canvas.has(ox + x, oy + y, oz + z) or (inner and canvas.has(ox + x + dx, oy + y, oz + z + dz)):
            continue
        put((x, z), y, panel(side))
    return 0


# --- the plans as text ------------------------------------------------------------------------------
LEGEND = [
    ("#", "outer wall (main/facade.py)"), (":", "its inner leaf, with the glass"),
    ("W", "wall of the shell, solid through this storey"), ("D", "door opening"),
    (".", "floor or deck"), ("o", "open to the level below"), ("x", "closed space"),
    ("r", "railing on the edge of a deck"), ("T", "telescope pier (the cap, at the dome room)"),
    ("=", "iron grating round the pier's foot"), ("<", "grand stair, rising west"),
    ("s", "ring stair"), ("S", "ring stair passing three blocks over a deck or its railing"),
    ("b", "the bridge onto the ring stair"), ("e", "where the ring stair lets one off"),
]


def drawing(level):
    """One of the three plans as text, north up: "ground" (feet 0), "main" (feet 7), "dome" (feet 18)."""
    L = layout()
    f = facade.shell()
    g = {}
    for c in f.wall:
        g[c] = "#"
    for c in f.leaf:
        g[c] = ":"
    for c in L.core:
        g[c] = "x"
    if level == "ground":
        for c in L.hall:
            g[c] = "=" if c in L.gap else "."
        for c in L.cross | L.partition | L.west | L.cheek | L.arcade | L.landing:
            g[c] = "W"
        for cells in L.flights.values():
            for x, _y, z in cells:
                g[(x, z)] = "<"
    elif level == "main":
        for cells in L.rooms.values():
            for c in cells:
                g[c] = "."
        for c in L.hall:
            g[c] = "o"
        for cells in L.flights.values():
            for x, _y, z in cells:
                g[(x, z)] = "<"
        for c in L.walk:
            g[c] = "."
        for c in L.rail:
            g[c] = "r"
        for c in L.cross | L.partition | L.west:
            g[c] = "W"
        for c in L.doors:
            g[c] = "D"
        for x, z, y, _half, _top in ring_stair():
            if y < CEIL_Y:
                g[(x, z)] = "S" if (x, z) in L.deck else "s"
        g[BRIDGE] = "b"
    else:
        d = O.disc(CX, CZ, S.DOME_R)
        g = {c: "#" for c in d}
        for c in L.dome_floor:
            g[c] = "."
        for c in L.envelope:
            g[c] = "o"
        for c in L.dome_rail:
            g[c] = "r"
        for x, z, y, _half, top in ring_stair():
            if top > ROOF_Y:
                g[(x, z)] = "s"
        g[EXIT] = "e"
    if level != "ground":
        for c in (L.cap if level == "dome" else L.shaft):
            g[c] = "T"
    else:
        for c in L.shaft:
            g[c] = "T"
    xs = [c[0] for c in g]
    zs = [c[1] for c in g]
    x0, x1 = min(xs), max(xs)
    lines = ["      x " + "".join("%d" % (abs(x) % 10) for x in range(x0, x1 + 1))]
    for z in range(min(zs), max(zs) + 1):
        lines.append("z %4d  %s" % (z, "".join(g.get((x, z), " ") for x in range(x0, x1 + 1)).rstrip()))
    return "\n".join(lines)


def tables():
    out = ["grand stair, each flight (x: feet after the step): "
           + "  ".join("x%d:%d" % (x, y + 1) for x, y in grand_stair())
           + "; rows z %d..%d and %d..%d; landing at x %d" % (FLIGHT_ROWS[-1][0], FLIGHT_ROWS[-1][-1],
                                                           FLIGHT_ROWS[1][0], FLIGHT_ROWS[1][-1], LANDING_X),
           "ring stair, from the bridge at %s to the dome-room floor at %s ((x,z) tread height):" % (BRIDGE, EXIT),
           "  " + "  ".join("(%d,%d)%.1f" % (x, z, top) for x, z, _y, _half, top in ring_stair()),
           "rooms:"]
    for name, r in ROOMS.items():
        where = "x %d..%d z %d..%d" % (r["box"][0], r["box"][2], r["box"][1], r["box"][3]) if "box" in r \
            else "round %s, radius %d" % (r["centre"], r["radius"])
        out.append("  %-10s %s, feet %d%s -- %s" % (name, where, r["feet"],
                                                   "" if r["ceiling"] is None else ", ceiling %d" % r["ceiling"], r["note"]))
    return "\n".join(out)


# --- self-check -------------------------------------------------------------------------------------
def check():
    """What can be told without a picture; returns the findings as lines (none is good)."""
    out = []
    L = layout()
    walls = Canvas()
    c = Canvas()
    with hall_open():
        facade.build(walls)
        facade.build(c)
    build(c)
    solid = lambda x, y, z: c.has(x, y, z)

    # 1. the shell stands inside the walls: it changes no block of the facade below the dome-room floor
    for (x, y, z), state in walls.b.items():
        if y < ROOF_Y and c.get(x, y, z) != state:
            out.append(f"the shell changes the facade's block at ({x}, {y}, {z})")
    # 2. nothing but the grating at the foot, the corbel and the cap touches the pier: no block
    #    stands face to face with the shaft
    for x, z in L.gap:
        if any(O.step((x, z), d) in L.shaft for d in O.SIDES):
            for y in range(S.GROUND, ROOF_Y - 1):
                if solid(x, y, z):
                    out.append(f"something touches the pier at ({x}, {y}, {z})")
    # 3. the ring stair: each step is half a block above the last, has head room, and nothing of
    #    the building is in the way; it starts level with the bridge and ends level with the floor
    stair = ring_stair()
    if stair[0][4] != S.STAND + 0.5 or stair[-1][4] != float(S.ROOF_STAND):
        out.append("the ring stair does not run from feet 7 to feet 18")
    for (x, z, y, _half, top), nxt in zip(stair, stair[1:] + [None]):
        feet = top if nxt is None else nxt[4]
        for yy in range(y + 1, int(feet + 2.3) + 1):
            if solid(x, yy, z) and c.name(x, yy, z) != PANEL:
                out.append(f"ring stair: no head room over ({x}, {z}) at y {yy}")
    if not solid(BRIDGE[0], DECK_Y, BRIDGE[1]) or solid(BRIDGE[0], S.STAND, BRIDGE[1]):
        out.append("ring stair: the bridge is not an open deck")
    if c.name(EXIT[0], ROOF_Y, EXIT[1]) != ROOM_FLOOR or solid(EXIT[0], S.ROOF_STAND, EXIT[1]):
        out.append("ring stair: no floor to step onto at the top")
    #    and nobody walks off it: beside every step stands the next step, a railing, a panel or a wall
    cells = [(x, z) for x, z, _y, _half, _top in stair]
    for i, (x, z, y, _half, _top) in enumerate(stair):
        for side, (dx, dz) in SIDE.items():
            n = (x + dx, z + dz)
            if n in cells[max(i - 1, 0):i + 2] or (i == 0 and n == BRIDGE) or (i == len(stair) - 1 and n == EXIT):
                continue
            if not solid(n[0], y + 1, n[1]) and c.get(x, y + 1, z) != panel(side):
                out.append(f"ring stair: step ({x}, {z}) is open to the {side}")
    # 4. the grand stair: three blocks of air over every step
    for cells in L.flights.values():
        for x, y, z in cells:
            for yy in range(y + 1, y + 4):
                if solid(x, yy, z):
                    out.append(f"grand stair: no head room over ({x}, {z}) at y {yy}")
    # 5. one can walk from the entrance to every room: the ground floor, then the main floor
    def reach(cells, start):
        seen, todo = {start}, [start]
        while todo:
            x, z = todo.pop()
            for d in O.SIDES:
                n = (x + d[0], z + d[1])
                if n in cells and n not in seen:
                    seen.add(n)
                    todo.append(n)
        return seen

    ground = {cell for cell in L.hall if not solid(cell[0], S.GROUND, cell[1]) and not solid(cell[0], S.GROUND + 1, cell[1])}
    ground |= {(x, z) for cells in L.flights.values() for x, _y, z in cells}
    from_door = reach(ground, (15, CZ))
    for what, cell in (("the west door", (-7, CZ)), ("the north flight", (FLIGHT_X[0], -4)), ("the south flight", (FLIGHT_X[0], 4))):
        if cell not in from_door:
            out.append(f"ground floor: no way from the entrance to {what}")
    upper = set(L.walk) | L.doors | L.rooms["time room"] | L.rooms["chart room"]
    upper |= {(FLIGHT_X[1], z) for rows in FLIGHT_ROWS.values() for z in rows}
    from_stair = reach(upper, (FLIGHT_X[1], -4))
    for what, cell in (("the south flight", (FLIGHT_X[1], 4)), ("the time room", (ROOM_DOOR_X[0], -CROSS_Z - 1)),
                       ("the chart room", (ROOM_DOOR_X[0], CROSS_Z + 1)), ("the bridge of the ring stair", BRIDGE),
                       ("the mezzanine under the west window", (-7, CZ))):
        if cell not in from_stair:
            out.append(f"main floor: no way from the top of the north flight to {what}")
    for x, z in L.walk:                                     # nobody walks off a deck
        for d in O.SIDES:
            n = (x + d[0], z + d[1])
            if n in L.hall and n not in L.deck and not solid(n[0], S.STAND, n[1]) and not solid(n[0], DECK_Y, n[1]):
                if n == (BRIDGE[0], BRIDGE[1] - 1) or (n[0], n[1]) in {(fx, fz) for cells in L.flights.values() for fx, fy, fz in cells if fy == DECK_Y}:
                    continue                                # the first step of the ring stair; the top step of a flight
                out.append(f"main floor: deck ({x}, {z}) is open to the drop at {n}")
    # 6. the dome-room floor is closed but for the envelope
    for x, z in L.dome_floor:
        if c.name(x, ROOF_Y, z) != ROOM_FLOOR:
            out.append(f"dome room: no floor at ({x}, {z})")
    for x, z in L.track:
        if solid(x, ROOF_Y, z) and (x, z, ROOF_Y) not in {(sx, sz, sy) for sx, sz, sy, _h, _t in stair}:
            out.append(f"dome room: the envelope is not open at ({x}, {z})")
    return out


if __name__ == "__main__":
    if "check" not in sys.argv[1:]:
        for level in ("ground", "main", "dome"):
            print(f"--- {level} ---")
            print(drawing(level))
            print()
        print("\n".join("%-3s %s" % item for item in LEGEND))
        print()
        print(tables())
        print()
    found = check()
    print("\n".join(found) if found else "self-check: inside the walls, the pier untouched, both stairs walkable, every room reached")
    sys.exit(1 if found else 0)
