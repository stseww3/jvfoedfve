"""main/roof -- the flat roofs of the main building and the way over the wings' roofs: paving,
gutters, the two roof lights, the leaves of the dome room's doors, and an iron walkway on each
wing's ridge, so that one walks from the dome room to the small dome and to the clock tower.

DRAFT: written while the machine was closed to Python, not run yet. The underscore keeps the module
out of the category's auto-discovery; it becomes main/roof.py when its self-check has passed.

Card: plan/packages/main/smalldome.md (the same card as main/smalldome.py). Design: plan/ART-PLAN.md
section 4 ("the roofs can be walked") and 5.1; the director's ruling on the doors and the walkways
is in plan/STATUS.md (A0 #20299).

main/facade.py closes the top of the shell: slates over the wings, and on the three flat roofs a
plain deck at y 17 whose columns it hands out as terraces(). This package runs after the shell,
the tower and the domes, and lays over that deck:

  the corner terraces   the two pockets between the great drum, a wing's gable and the east
                        parapet: flats of sheet copper, as a roof too small and too crooked for
                        slates is covered. The dome room's doors open onto them; the leaves hang
                        here, set back in the wall.
  the end terraces      the flat roofs of the two end pavilions, west of the clock tower and of
                        the small dome: dark slate flags in a frame of copper, one flush course at
                        the foot of whatever rises from the terrace (the gable, the small drum, the
                        tower). Each has a roof light on the axis of what stands beside it: nine
                        blocks of glass level with the flags, an iron kerb round them, a ceiling
                        light one block under the glass.
  on all three          a copper channel half a block down along every parapet.
  the walkways          one to each wing, the two alike. From the corner terrace the way crosses
                        the inner gable where its top is level with the terrace (x 13), climbs the
                        slates beside the gable on iron treads, and turns onto the ridge under the
                        edge of the dome's gallery. On the ridge it is a grating two blocks wide
                        between two low guards of iron panels, whose tops are level with the
                        gables; under the grating a caged lamp every third block, so that the way
                        is lit from below and nothing shines into an observer's eyes. One step
                        takes it onto the end gable, a flight of three down to the end terrace,
                        where the small dome's door (south) and the tower's door (north) are two
                        blocks to the east.

Nothing here stands higher than the gables (y 21) except the guards at the head of each flight, and
nothing stands on a parapet: the outline of the fronts stays the facade's.

Light: the caged lamps are blocks of this package (their own light is 4); over each the light kit
is asked for a walkway's level (sky.md 6), where the kit is in the tree. The ceiling lights under
the two roof lights are dark glass until the lights line says otherwise.

No display entities. Vent cowls, ladders and railing panels are the props line's (props/ironwork).

    python -m scenes.obs.main.roof            # text plans, sections and the self-check
    python -m scenes.obs.main.roof check      # the self-check alone (exit code 1 on a finding)
"""
import math
import sys

from artkit.canvas import Canvas

from ..common import blocks as B
from ..common import skeleton as S
from . import _order as O
from . import _plan as P
from . import facade
from . import smalldome

ORDER = 70                      # after the shell (20), the tower and the small dome (50), the great dome (60)

DECK_Y = S.ROOF_FLOOR                                   # 17: the block of every flat roof
STAND = S.ROOF_STAND                                    # 18: where feet stand on it
WINGS = {"north": -1, "south": 1}                       # a wing and its end pavilion: the sign of their z
CORNER = "middle"                                       # main/facade.py's name for the two corner terraces
GABLE_IN, GABLE_OUT = P.GABLE_Z                         # |z| 14 and 26: the gables at a wing's two ends
ROOF_IN, ROOF_OUT = P.ROOF_Z                            # |z| 15..25: the slates between them
RIDGE = tuple(x for x in range(S.WALL_W + 1, S.WALL_E)
              if P.roof_steps(x, ROOF_IN) == P.ROOF_RIDGE_STEPS - 1)       # (7, 8): the ridge columns
RIDGE_TOP = int(P.ROOF_RIDGE_TOP)                       # 20: the ridge's top face
APEX_TOP = STAND + (P.ROOF_RIDGE_STEPS - 1) // 2        # 21: the top face of a gable on the ridge columns

# the walkway
CROSS_X = 13                                            # where it crosses the inner gable: the gable's top is
#                                                         level with the terrace there, and the dome's gallery
#                                                         hangs over the gable from x 11 westwards
DECK_Z = (ROOF_IN, ROOF_OUT - 1)                        # |z| 15..24: the grating on the ridge
STEP_Z = ROOF_OUT                                       # |z| 25: the step up onto the end gable
FLIGHT_X = RIDGE[0]                                     # 7: the flight down; the small dome's corbel hangs over 8
FLIGHT = APEX_TOP - STAND                               # 3 steps
LAMP_X = RIDGE[1]                                       # the lamps stand in one file under the east half
LAMP_EVERY = 3                                          # |z| 15, 18, 21, 24
LAMP_LEVEL = 6                                          # asked of the light kit over each lamp (walkways 5-7)

# the roof light of an end terrace: its glass, as columns of the south one; the kerb is the ring round it
LIGHT_X = (S.WALL_W + 3, FLIGHT_X - 2)                  # 3..5
LIGHT_Z = (smalldome.CZ - 1, smalldome.CZ + 1)          # |z| 29..31: on the axis of the small dome and of the tower

PAVING = B.SLATE_SMOOTH.block
GUTTER = f"{B.OLD_COPPER_CUT.slab}[type=bottom]"        # the channel along a parapet, half a block down
FLASHING = B.OLD_COPPER_CUT.block                       # sheet copper: the corner flats, the course at a wall's foot
GRATING = B.IRON_GRATE
BED = B.SLATE_TILE.block                                # the ridge under the grating
LAMP = f"{B.IRON_BULB}[lit=true,powered=false]"
TREAD = B.IRON_RIVETED
PANEL = B.IRON_HATCH                                    # an iron hatch on edge: the guard beside the way
GLASS = B.SKYLIGHT.block
LAYLIGHT = B.WINDOW_DARK.block                          # the ceiling light of the room under a roof light
KERB = f"{B.IRON_RIVETED.slab}[type=bottom]"
LEAF = B.IRON_DOOR

SHAFT = frozenset(O.box(S.CLOCK_SHAFT_X[0], S.CLOCK_SHAFT_Z[0], S.CLOCK_SHAFT_X[1], S.CLOCK_SHAFT_Z[1]))


# --- the plan -----------------------------------------------------------------------------------------
def _on_gable(x, z):
    """A column of a gable wall, as main/facade.py builds them between the slates and the flat roofs."""
    return abs(z) in P.GABLE_Z and S.WALL_W < x < S.WALL_E


def _slate(x, z):
    """(row, half) of the slate slab on a roof column, as main/facade.py lays it."""
    steps = P.roof_steps(x, z)
    return (DECK_Y + steps // 2, "bottom") if steps % 2 else (DECK_Y - 1 + steps // 2, "top")


def terraces():
    """{name: columns} of the flat roofs as far as they lie open: main/facade.py's three, without
    the columns the clock tower and the small drum stand on."""
    t = facade.terraces()
    return {"north": frozenset(t["north"]) - SHAFT, "south": frozenset(t["south"]) - smalldome.BODY,
            CORNER: frozenset(t[CORNER])}


def bodies():
    """The columns of what rises from the terraces: the great drum, the small drum, the tower."""
    return frozenset(facade.terraces()["dome room"]) | smalldome.BODY | SHAFT


def roof_lights():
    """{wing: (glass columns, kerb columns)} of the two roof lights."""
    out = {}
    for name, s in WINGS.items():
        glass = frozenset(O.box(LIGHT_X[0], s * LIGHT_Z[0], LIGHT_X[1], s * LIGHT_Z[1]))
        out[name] = (glass, frozenset(O.ring(glass)))
    return out


def _panel(edge):
    """An iron panel on the `edge` side of its cell: a hatch on edge turns its back to that side."""
    return f"{PANEL}[facing={O.NAME[(-edge[0], -edge[1])]},half=bottom,open=true]"


def lamps(s):
    """The cells of one walkway's lamps, under the grating; s as in walkway()."""
    return [(LAMP_X, RIDGE_TOP - 2, s * az) for az in range(DECK_Z[0], DECK_Z[1] + 1, LAMP_EVERY)]


def walkway(s):
    """One wing's walkway as ({cell: state} that takes the place of the roof, {cell: state} of the
    guards, which give way to whatever stands in their cell); s is -1 for the north wing, 1 for
    the south one.

    A guard is a panel in the cell beside what one walks on, on the edge towards it: the cells one
    walks through stay empty (a light source can stand in them), and the guards of the ridge and of
    the flight are one plane."""
    laid, guards = {}, {}
    out, back = O.NAME[(0, s)], O.NAME[(0, -s)]         # towards the end pavilion, towards the dome
    west, east = RIDGE[0] - 1, RIDGE[1] + 1             # the columns beside the ridge
    # the treads beside the inner gable, from the crossing up to the ridge: the roof's own steps in
    # iron, the first one raised to the level of the terrace
    z = s * ROOF_IN
    laid[(CROSS_X, DECK_Y, z)] = TREAD.block
    for x in range(CROSS_X - 1, RIDGE[1], -1):
        y, half = _slate(x, z)
        laid[(x, y, z)] = f"{TREAD.slab}[type={half}]"
    # the grating on the ridge, on a bed of slate with the lamps in it
    for az in range(DECK_Z[0], DECK_Z[1] + 1):
        for x in RIDGE:
            laid[(x, RIDGE_TOP - 1, s * az)] = GRATING
            laid[(x, RIDGE_TOP - 2, s * az)] = BED
    for cell in lamps(s):
        laid[cell] = LAMP
    # one step up onto the end gable
    for x in RIDGE:
        laid[(x, RIDGE_TOP, s * STEP_Z)] = f"{TREAD.stairs}[facing={out},half=bottom]"
    # the guards of the ridge; the first row is open to the east, where the treads come in
    for az in range(DECK_Z[0], STEP_Z + 1):
        guards[(west, RIDGE_TOP, s * az)] = _panel(O.EAST)
        if az > DECK_Z[0]:
            guards[(east, RIDGE_TOP, s * az)] = _panel(O.WEST)
    # the head of the flight on the end gable: guards on both sides, and on the far edge of the
    # half the flight does not leave by (that one stands in the gable's own cell: the cell beyond
    # holds the flight's guard)
    guards[(west, APEX_TOP, s * GABLE_OUT)] = _panel(O.EAST)
    guards[(east, APEX_TOP, s * GABLE_OUT)] = _panel(O.WEST)
    guards[(RIDGE[1], APEX_TOP, s * GABLE_OUT)] = _panel((0, s))
    # the flight down to the end terrace: under every step but the last a tread turned over, so the
    # flight is one slab of iron from the gable to the flags; a guard beside every step
    for i in range(FLIGHT):
        y, z = APEX_TOP - 1 - i, s * (GABLE_OUT + 1 + i)
        laid[(FLIGHT_X, y, z)] = f"{TREAD.stairs}[facing={back},half=bottom]"
        if y - 1 >= STAND:
            laid[(FLIGHT_X, y - 1, z)] = f"{TREAD.stairs}[facing={out},half=top]"
        guards[(FLIGHT_X - 1, y + 1, z)] = _panel(O.EAST)
        guards[(FLIGHT_X + 1, y + 1, z)] = _panel(O.WEST)
    return laid, guards


def doors():
    """[(x, y, z, state)] of the leaves in the dome room's two doors (skeleton DOME_ROOM_DOORS; the
    drum opens them, main/dome.py). A leaf stands on the inner edge of the outer wall's block, so
    the doorway shows its depth from the terrace; both are hinged on the east jamb."""
    y0, y1 = S.DOME_ROOM_DOORS["y"]
    out = []
    for x, z in S.DOME_ROOM_DOORS["cells"]:
        outward, hinge = ("south", "left") if z > 0 else ("north", "right")
        for y, half in zip(range(y0, y1 + 1), ("lower", "upper")):
            out.append((x, y, z, f"{LEAF}[facing={outward},half={half},hinge={hinge},open=false]"))
    return out


def route(s):
    """The way from a door of the dome room to the door on the end terrace, as [(x, z, feet)]: every
    cell one walks through and where the feet are in it (a stair gives two heights). check() walks
    it; s as in walkway()."""
    x0, z0 = next(c for c in S.DOME_ROOM_DOORS["cells"] if c[1] * s > 0)
    way = [(x0, z0, STAND)]
    way += [(x0, s * az, STAND) for az in range(abs(z0) + 1, GABLE_IN)]             # across the corner terrace
    way += [(x, s * (GABLE_IN - 1), STAND) for x in range(x0 + 1, CROSS_X + 1)]
    way += [(CROSS_X, s * GABLE_IN, STAND), (CROSS_X, s * ROOF_IN, STAND)]          # over the gable
    for x in range(CROSS_X - 1, RIDGE[1], -1):                                      # up the treads
        y, half = _slate(x, s * ROOF_IN)
        way.append((x, s * ROOF_IN, y + (1.0 if half == "top" else 0.5)))
    way += [(RIDGE[1], s * az, RIDGE_TOP) for az in range(DECK_Z[0], DECK_Z[1] + 1)]     # along the ridge
    way += [(RIDGE[1], s * STEP_Z, RIDGE_TOP + 0.5), (RIDGE[1], s * STEP_Z, APEX_TOP)]
    way += [(RIDGE[1], s * GABLE_OUT, APEX_TOP), (FLIGHT_X, s * GABLE_OUT, APEX_TOP)]    # on the end gable
    for i in range(FLIGHT):                                                         # down the flight
        z = s * (GABLE_OUT + 1 + i)
        way += [(FLIGHT_X, z, APEX_TOP - i), (FLIGHT_X, z, APEX_TOP - i - 0.5)]
    z = s * (GABLE_OUT + 1 + FLIGHT)
    way += [(x, z, STAND) for x in range(FLIGHT_X, FLIGHT_X + 3)]                    # the landing, the threshold
    return way


# --- the package --------------------------------------------------------------------------------------
def _ask_light(canvas, cell, level, why):
    """Register a light source with the light kit (sky/_lightkit), where the kit is in the tree."""
    try:
        from ..sky import _lightkit
    except ImportError:
        return
    _lightkit.suggest(canvas, cell, level, why, rank=3)


def build(canvas, origin=(0, 0, 0)):
    """Lay the terraces, the roof lights, the walkways and the door leaves over what stands there.
    No display entities."""
    ox, oy, oz = origin

    def put(x, y, z, state):
        canvas.set(ox + x, oy + y, oz + z, state)

    def has(x, y, z):
        return canvas.has(ox + x, oy + y, oz + z)

    wall = facade.shell().wall
    rises = bodies()
    lights = roof_lights()
    for name, cells in terraces().items():
        stands = {c for c in cells if has(c[0], STAND, c[1])}       # a pilaster of the drum keeps its foot
        for c in cells - stands:
            near = [O.step(c, d) for d in O.SIDES]
            if any(n in wall for n in near):
                state = GUTTER
            elif name == CORNER or any(n in rises or n in stands or _on_gable(*n) for n in near):
                state = FLASHING
            else:
                state = PAVING
            put(c[0], DECK_Y, c[1], state)
        glass, kerb = lights.get(name, ((), ()))
        for x, z in glass:
            put(x, DECK_Y, z, GLASS)
            put(x, DECK_Y - 1, z, LAYLIGHT)
        for x, z in kerb:
            put(x, STAND, z, KERB)
    for s in WINGS.values():
        laid, guards = walkway(s)
        for (x, y, z), state in laid.items():
            put(x, y, z, state)
        for (x, y, z), state in guards.items():
            if not has(x, y, z):
                put(x, y, z, state)
        for x, y, z in lamps(s):
            _ask_light(canvas, (ox + x, oy + RIDGE_TOP, oz + z), LAMP_LEVEL, "main/roof:walkway")
    for x, y, z, state in doors():
        put(x, y, z, state)
    return 0


# --- self-check and drawings ----------------------------------------------------------------------------
def _scene():
    """The main line as the master scene builds it: the roofs lie on what the other packages stand."""
    from scenes.obs import main
    c = Canvas()
    main.build(c)
    return c


def _span(state, y):
    """(bottom, top) of what a block fills of its cell, or None where one walks past it: a guard on
    the cell's edge, a door leaf, a light source."""
    name = state.partition("[")[0]
    if name in (PANEL, LEAF, B.LIGHT):
        return None
    if "type=bottom" in state:
        return (y, y + 0.5)
    if "type=top" in state:
        return (y + 0.5, y + 1.0)
    return (y, y + 1.0)


def check(c=None):
    """What can be told without a picture; returns the findings as lines (none is good)."""
    c = c or _scene()
    out = []

    def name(x, y, z):
        return (c.get(x, y, z) or "air").partition("[")[0]

    # 1. every open column of a terrace is closed at the deck, by one of the terrace's own blocks
    floor = {b.partition("[")[0] for b in (PAVING, GUTTER, FLASHING, GLASS)}
    for where, cells in terraces().items():
        for x, z in sorted(cells):
            if not c.has(x, STAND, z) and name(x, DECK_Y, z) not in floor:
                out.append(f"{where} terrace: ({x}, {z}) is not laid ({name(x, DECK_Y, z)})")
    # 2. a parapet's channel is a closed run: no gutter column stands alone
    for where, cells in terraces().items():
        gutter = {col for col in cells if name(col[0], DECK_Y, col[1]) == B.OLD_COPPER_CUT.slab}
        for col in sorted(gutter):
            if not any(O.step(col, d) in gutter for d in O.SIDES):
                out.append(f"{where} terrace: the gutter at {col} joins no other")
    # 3. the roof lights: glass over the ceiling light, the kerb a closed ring, nothing on the glass
    for where, (glass, kerb) in roof_lights().items():
        for x, z in sorted(glass):
            if name(x, DECK_Y, z) != GLASS or name(x, DECK_Y - 1, z) != LAYLIGHT or c.has(x, STAND, z):
                out.append(f"{where} roof light: the glass at ({x}, {z}) is not as laid")
        for x, z in sorted(kerb):
            if name(x, STAND, z) != B.IRON_RIVETED.slab or name(x, DECK_Y, z) != PAVING:
                out.append(f"{where} roof light: the kerb at ({x}, {z}) is not as laid")
    # 4. the way can be walked, both wings: every step half a block at most, the surface under the
    #    feet where the route says, a body's height of air over it
    for where, s in WINGS.items():
        way = route(s)
        for (x0, z0, f0), (x1, z1, f1) in zip(way, way[1:]):
            if abs(x1 - x0) + abs(z1 - z0) > 1 or abs(f1 - f0) > 0.5:
                out.append(f"{where} walkway: no step from ({x0}, {z0}) at {f0} to ({x1}, {z1}) at {f1}")
        for x, z, feet in way:
            row = math.ceil(feet) - 1                       # the row of the block the feet stand on
            under = c.get(x, row, z)
            span = _span(under, row) if under else None
            stair = bool(under) and under.partition("[")[0] == TREAD.stairs
            if span is None or (span[1] != feet and not (stair and span[1] - 0.5 == feet)):
                out.append(f"{where} walkway: nothing to stand on at ({x}, {z}) at {feet} ({under})")
            for y in range(math.floor(feet), math.floor(feet + 1.79) + 1):
                over = c.get(x, y, z)
                span = _span(over, y) if over else None
                clear = feet + (0.5 if stair and y == row else 0.0)     # the tall half of the stair one stands on
                if span and span[1] > clear and span[0] < feet + 1.8:
                    out.append(f"{where} walkway: no headroom at ({x}, {z}) at {feet}: {over} at y {y}")
    # 5. the two walkways are one design, mirrored
    north, south = ({**laid, **guards} for laid, guards in (walkway(-1), walkway(1)))
    if len(north) != len(south):
        out.append(f"walkways: {len(north)} blocks to the north, {len(south)} to the south")
    for (x, y, z), state in south.items():
        mirrored = state.replace("facing=north", "facing=#").replace("facing=south", "facing=north")
        if north.get((x, y, -z)) != mirrored.replace("facing=#", "facing=south"):
            out.append(f"walkways: ({x}, {y}, {z}) is not the mirror of the north wing's")
    # 6. the walkway's blocks lie as laid; of the guards one at the most gave way (to the small
    #    dome's corbel beside the south flight)
    for where, s in WINGS.items():
        laid, guards = walkway(s)
        for cell, state in laid.items():
            if c.get(*cell) != state:
                out.append(f"{where} walkway: {cell} is {c.get(*cell)}, not {state}")
        missing = [cell for cell, state in guards.items() if c.get(*cell) != state]
        if len(missing) > 1:
            out.append(f"{where} walkway: {len(missing)} guards gave way: {sorted(missing)}")
    # 7. the leaves hang in the doors, on a threshold
    for x, y, z, state in doors():
        if c.get(x, y, z) != state:
            out.append(f"door: no leaf at ({x}, {y}, {z})")
    for x, z in S.DOME_ROOM_DOORS["cells"]:
        if not c.has(x, S.DOME_ROOM_DOORS["y"][0] - 1, z):
            out.append(f"door: the leaf at ({x}, {z}) stands on nothing")
    # 8. nothing of this package stands on a parapet or outside the walls
    plan = facade.shell()
    inside = plan.leaf | plan.core
    scratch = Canvas()
    build(scratch)
    for x, y, z in sorted(scratch.b):
        if (x, z) not in inside:
            out.append(f"outline: ({x}, {y}, {z}) lies outside the parapets")
    return out


_MARKS = {PANEL: "|", LEAF: "J", B.IRON_BULB: "@", B.VERDIGRIS_CAST: "A", B.IRON_CAST: "K"}


def _top_plan(c, zs, y_hi=22, y_lo=16):
    """The roofs from above (north up): the letter of the highest block of every column."""
    xs = range(S.WALL_W - 2, S.WALL_E + 4)
    lines = ["        " + "".join("%d" % (abs(x) % 10) for x in xs)]
    for z in range(zs[0], zs[1] + 1):
        row = []
        for x in xs:
            y = next((y for y in range(y_hi, y_lo - 1, -1) if c.has(x, y, z)), None)
            row.append("." if y is None else O.mark(c.get(x, y, z)))
        lines.append("z %4d  %s" % (z, "".join(row)))
    return "\n".join(lines)


def _drawings(c):
    for block, letter in _MARKS.items():
        O.MARKS.setdefault(block, letter)
    z_end = S.Z_SOUTH + 1
    print("FROM ABOVE, the south half (north up; the highest block of every column up to y 22):\n")
    print(_top_plan(c, (GABLE_IN - 5, z_end)))
    print("\nFROM ABOVE, the north half:\n")
    print(_top_plan(c, (-z_end, -(GABLE_IN - 5))))
    ys = (DECK_Y - 2, APEX_TOP + 2)
    print(f"\nSECTION along the ridge, x = {RIDGE[1]} (north on the left):\n")
    print(O.section(c, "x", RIDGE[1], (-z_end, z_end), ys))
    print(f"\nSECTION along the flights, x = {FLIGHT_X} (north on the left):\n")
    print(O.section(c, "x", FLIGHT_X, (-z_end, z_end), ys))
    print(f"\nSECTION up the treads, z = {ROOF_IN} (west on the left):\n")
    print(O.section(c, "z", ROOF_IN, (S.WALL_W - 2, S.WALL_E + 3), ys))
    print(f"\nSECTION through the south terrace on its axis, z = {smalldome.CZ} (west on the left):\n")
    print(O.section(c, "z", smalldome.CZ, (S.WALL_W - 2, S.WALL_E + 3), (DECK_Y - 2, STAND + 4)))
    print("\nLetters: M slate flags, C sheet copper, c copper channel, Y roof light, D its ceiling light,")
    print("i iron kerb, treads and steps, I iron block, % grating, @ caged lamp, | guard panel, J door")
    print("leaf, T t slates, F stone. Small letters are slabs and stairs.")
    for where, s in WINGS.items():
        way = route(s)
        print(f"\nthe way, {where} wing: {len(way)} steps from the dome room's door {way[0][:2]} to "
              f"{way[-1][:2]}, feet {way[0][2]} .. {max(f for _, _, f in way)} .. {way[-1][2]}")


if __name__ == "__main__":
    scene = _scene()
    if "check" not in sys.argv[1:]:
        _drawings(scene)
        print()
    found = check(scene)
    print("\n".join(found) if found else
          "self-check: terraces laid, gutters joined, roof lights, both ways walkable and alike, "
          "door leaves, nothing on the parapets -- all good")
    sys.exit(1 if found else 0)
