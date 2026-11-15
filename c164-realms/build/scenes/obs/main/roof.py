"""main/roof -- the flat roofs of the main building and the way over the wings' roofs: gutters, a
roof light on each end terrace, the leaves of the dome room's doors, and an iron walkway on each
wing's ridge, so that one walks from the dome room to the small dome and to the clock tower.

Card: plan/packages/main/smalldome.md (the same card as main/smalldome.py). Design: plan/ART-PLAN.md
section 4 ("the roofs can be walked") and 5.1. The director's rulings: the doors and the walkways,
plan/STATUS.md (A0 #20299); no railing on the parapets, no guard on the walkways, no cowls or flues
in this version, and whoever falls off a roof lands unhurt in the court -- the finished map switches
fall damage off (A0 #34510, in the card).

main/facade.py closes the top of the shell: slates over the wings, and on the three flat roofs a
deck of dark slate flags at y 17 whose columns it hands out as terraces(). This package runs after
the shell, the tower and the domes. The flags stay as the facade lays them; what is added:

  on every terrace      a copper channel half a block down along the parapets (copper is the
                        gutters' metal here and nothing else's), and an iron plate in the flags
                        before each door.
  the corner terraces   the two pockets between the great drum, a wing's gable and the east
                        parapet. The dome room's doors open onto them; the leaves hang here, set
                        back in the wall.
  the end terraces      the flat roofs of the two end pavilions, west of the clock tower and of
                        the small dome. A roof light leans against the gable: six blocks of glass
                        level with the flags, an iron kerb on its three open sides, a ceiling light
                        one block under the glass. The doors' row and all that lies beyond it stay
                        open: the small dome's slit looks out to the west over its terrace, so
                        nothing stands there and nothing is lit.
  the walkways          one to each wing, the two alike, and laid into the roof: nothing of them
                        stands above the ridge, so the fronts keep their outline (from the court
                        the ridge is just hidden behind the parapet; a guard one block high on it
                        would show from the arrival view as a dark band on either wing). From
                        the corner terrace the way crosses the inner gable at its east end, where
                        the gable's top is level with the terrace; climbs to the ridge beside the
                        gable, on the roof's own steps turned to iron; follows the ridge as a
                        grating two blocks wide, with a caged lamp under it at either end and in
                        the middle, so that the way is lit from below and nothing shines into an
                        observer's eyes; comes down the west slope beside the end gable, crosses
                        that at its west end and reaches the end terrace in the corner by the
                        west parapet. From there the door (the small dome's to the south, the
                        tower's to the north) is straight ahead on the terrace's axis. No step is
                        higher than half a block, and to either side of the grating the slates
                        are half a block down: the way needs no guard.

Light: the caged lamps are blocks of this package (their own light is 4); over each the light kit
is asked for a walkway's level (sky.md 6; agreed with the lights line, c220 #34654), where the kit
is in the tree. The ceiling lights under the two roof lights are dark glass until the lights line
says otherwise. None of this may show in V1, V2 or V11: scenes/obs_main_smalldome/hidden.py casts
the sight lines.

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

ORDER = 70                      # after the walls and slates (facade, 20), the tower and the small dome (50), the
#                                 great dome and the floors (60); before the rooms that move in (80)

DECK_Y = S.ROOF_FLOOR                                   # 17: the block of every flat roof
STAND = S.ROOF_STAND                                    # 18: where feet stand on it
WINGS = {"north": -1, "south": 1}                       # a wing and its end pavilion: the sign of their z
CORNER = "middle"                                       # main/facade.py's name for the two corner terraces
GABLE_IN, GABLE_OUT = P.GABLE_Z                         # |z| 14 and 26: the gables at a wing's two ends
ROOF_IN, ROOF_OUT = P.ROOF_Z                            # |z| 15..25: the slates between them
RIDGE = tuple(x for x in range(S.WALL_W + 1, S.WALL_E)
              if P.roof_steps(x, ROOF_IN) == P.ROOF_RIDGE_STEPS - 1)       # (7, 8): the ridge columns
RIDGE_TOP = int(P.ROOF_RIDGE_TOP)                       # 20: the ridge's top face

# the walkway: up the east slope on the first row of slates, down the west slope on the last
UP_X = S.WALL_E - 2                                     # 13: where it crosses the inner gable. The gable's top is
#                                                         level with the terrace there, and the dome's gallery
#                                                         hangs over the gable only from x 11 westwards
DOWN_X = S.WALL_W + 2                                   # 2: where it crosses the end gable, as far from the west
#                                                         wall as UP_X is from the east one
LAMP_X = RIDGE[1]                                       # the lamps stand in one file under the east half
LAMP_Z = (ROOF_IN, (ROOF_IN + ROOF_OUT) // 2, ROOF_OUT)     # |z| 15, 20, 25: where the way turns, and half way
LAMP_LEVEL = 6                                          # asked of the light kit over each lamp (walkways 5-7)

# the doors on the end terraces: the small drum's on its west axis, the tower's in the middle of its west face
END_DOOR = {1: smalldome.door_cells()[0][::2],
            -1: (S.CLOCK_SHAFT_X[0], (S.CLOCK_SHAFT_Z[0] + S.CLOCK_SHAFT_Z[1]) // 2)}       # (9, 30), (10, -30)
DOOR_Z = smalldome.CZ                                   # |z| 30: the row of both, the axis of an end terrace

# the roof light of an end terrace: it leans against the gable, between where the way comes in and the drum
LIGHT_X = (DOWN_X + 2, DOWN_X + 4)                      # 4..6: the glass
LIGHT_DEEP = 2                                          # |z| 27..28: two rows of glass; the kerb's row is 29

GUTTER = f"{B.OLD_COPPER_CUT.slab}[type=bottom]"        # the channel along a parapet, half a block down
PLATE = B.IRON_RIVETED.block                            # the plate in the flags before a door
GRATING = B.IRON_GRATE
BED = B.SLATE_TILE.block                                # the ridge under the grating
LAMP = f"{B.IRON_BULB}[lit=true,powered=false]"
TREAD = B.IRON_RIVETED
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


def _slate_top(x, z):
    """The top face of that slab."""
    y, half = _slate(x, z)
    return y + (1.0 if half == "top" else 0.5)


def terraces():
    """{name: columns} of the flat roofs as far as they lie open: main/facade.py's three, without
    the columns the clock tower and the small drum stand on."""
    t = facade.terraces()
    return {"north": frozenset(t["north"]) - SHAFT, "south": frozenset(t["south"]) - smalldome.BODY,
            CORNER: frozenset(t[CORNER])}


def gutters():
    """The columns of the channel: every open column of a terrace that touches the parapet's line."""
    wall = facade.shell().wall
    return frozenset(c for cells in terraces().values() for c in cells
                     if any(O.step(c, d) in wall for d in O.SIDES))


def thresholds():
    """The columns before the four doors that open onto the terraces."""
    out = [(x, z + (1 if z > 0 else -1)) for x, z in S.DOME_ROOM_DOORS["cells"]]
    return out + [(x - 1, z) for x, z in END_DOOR.values()]


def roof_lights():
    """{wing: (glass columns, kerb columns)} of the two roof lights. The glass lies against the
    gable; the kerb is the ring round it without the gable's own columns."""
    out = {}
    for name, s in WINGS.items():
        glass = frozenset(O.box(LIGHT_X[0], s * (GABLE_OUT + 1), LIGHT_X[1], s * (GABLE_OUT + LIGHT_DEEP)))
        out[name] = (glass, frozenset(c for c in O.ring(glass) if not _on_gable(*c)))
    return out


def lamps(s):
    """The cells of one walkway's lamps, under the grating; s as in walkway()."""
    return [(LAMP_X, RIDGE_TOP - 2, s * az) for az in LAMP_Z]


def walkway(s):
    """One wing's walkway as {cell: state}: what takes the place of the roof's slates; s is -1 for
    the north wing, 1 for the south one."""
    laid = {}
    # the two runs of treads: the roof's own steps in iron, from the ridge down to the column where
    # the gable is crossed; the last one there is a whole block, level with the gable's top
    for az, landing in ((ROOF_IN, UP_X), (ROOF_OUT, DOWN_X)):
        z = s * az
        laid[(landing, DECK_Y, z)] = TREAD.block
        for x in (range(landing - 1, RIDGE[1], -1) if landing > RIDGE[1] else range(landing + 1, RIDGE[0])):
            y, half = _slate(x, z)
            laid[(x, y, z)] = f"{TREAD.slab}[type={half}]"
    # the grating on the ridge, from gable to gable, on a bed of slate with the lamps in it
    for az in range(ROOF_IN, ROOF_OUT + 1):
        for x in RIDGE:
            laid[(x, RIDGE_TOP - 1, s * az)] = GRATING
            laid[(x, RIDGE_TOP - 2, s * az)] = BED
    for cell in lamps(s):
        laid[cell] = LAMP
    return laid


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
    column one walks over and where the feet stand on it. check() walks it; s as in walkway()."""
    x0, z0 = next(c for c in S.DOME_ROOM_DOORS["cells"] if c[1] * s > 0)
    way = [(x0, s * az, STAND) for az in range(abs(z0), GABLE_IN)]                  # the door, the corner terrace
    way += [(x, s * (GABLE_IN - 1), STAND) for x in range(x0 + 1, UP_X + 1)]
    way += [(UP_X, s * GABLE_IN, STAND), (UP_X, s * ROOF_IN, STAND)]                # over the inner gable
    way += [(x, s * ROOF_IN, _slate_top(x, s * ROOF_IN)) for x in range(UP_X - 1, RIDGE[1], -1)]
    way += [(RIDGE[1], s * az, RIDGE_TOP) for az in range(ROOF_IN, ROOF_OUT + 1)]   # along the ridge
    way += [(RIDGE[0], s * ROOF_OUT, RIDGE_TOP)]
    way += [(x, s * ROOF_OUT, _slate_top(x, s * ROOF_OUT)) for x in range(RIDGE[0] - 1, DOWN_X, -1)]
    way += [(DOWN_X, s * ROOF_OUT, STAND), (DOWN_X, s * GABLE_OUT, STAND)]          # over the end gable
    way += [(DOWN_X, s * az, STAND) for az in range(GABLE_OUT + 1, DOOR_Z + 1)]     # the end terrace
    way += [(x, s * DOOR_Z, STAND) for x in range(DOWN_X + 1, END_DOOR[s][0])]      # along its axis to the plate
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
    """Lay the channels, the plates, the roof lights, the walkways and the door leaves over what
    stands there. No display entities."""
    ox, oy, oz = origin

    def put(x, y, z, state):
        canvas.set(ox + x, oy + y, oz + z, state)

    for x, z in gutters():
        if not canvas.has(ox + x, oy + STAND, oz + z):  # what stands on the deck keeps its foot
            put(x, DECK_Y, z, GUTTER)
    for x, z in thresholds():
        put(x, DECK_Y, z, PLATE)
    for glass, kerb in roof_lights().values():
        for x, z in glass:
            put(x, DECK_Y, z, GLASS)
            put(x, DECK_Y - 1, z, LAYLIGHT)
        for x, z in kerb:
            put(x, STAND, z, KERB)
    for s in WINGS.values():
        for (x, y, z), state in walkway(s).items():
            put(x, y, z, state)
        for x, y, z in lamps(s):
            _ask_light(canvas, (ox + x, oy + RIDGE_TOP, oz + z), LAMP_LEVEL, "main/roof:walk")
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
    """(bottom, top) of what a block fills of its cell, or None where one walks past it: a door
    leaf, a light source."""
    name = state.partition("[")[0]
    if name in (LEAF, B.LIGHT):
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

    # 1. every open column of a terrace is closed at the deck
    for where, cells in terraces().items():
        for x, z in sorted(cells):
            if not c.has(x, DECK_Y, z):
                out.append(f"{where} terrace: ({x}, {z}) has no deck")
    # 2. the channel is a closed run along the parapets: no gutter column stands alone, and none
    #    lies where the way goes
    gutter = gutters()
    for col in sorted(gutter):
        if not any(O.step(col, d) in gutter for d in O.SIDES):
            out.append(f"gutter: the one at {col} joins no other")
    for where, s in WINGS.items():
        for x, z, _ in route(s):
            if (x, z) in gutter:
                out.append(f"gutter: the {where} way steps into the channel at ({x}, {z})")
    # 3. the roof lights: glass over the ceiling light and nothing on it; the kerb on the flags,
    #    closed but for the gable's side; clear of the channel and of the way
    for where, (glass, kerb) in roof_lights().items():
        for x, z in sorted(glass):
            if name(x, DECK_Y, z) != GLASS or name(x, DECK_Y - 1, z) != LAYLIGHT or c.has(x, STAND, z):
                out.append(f"{where} roof light: the glass at ({x}, {z}) is not as laid")
        for x, z in sorted(kerb):
            if c.get(x, STAND, z) != KERB or not c.has(x, DECK_Y, z):
                out.append(f"{where} roof light: the kerb at ({x}, {z}) is not as laid")
        if (glass | kerb) & gutter or not (glass | kerb) <= terraces()[where]:
            out.append(f"{where} roof light: it lies in the channel or off the terrace")
        if (glass | kerb) & {(x, z) for x, z, _ in route(WINGS[where])}:
            out.append(f"{where} roof light: it lies in the way")
    # 4. the way can be walked, both wings: every step half a block at most, the surface under the
    #    feet where the route says, a body's height of air over it; it ends before the door
    for where, s in WINGS.items():
        way = route(s)
        if way[-1][:2] != (END_DOOR[s][0] - 1, END_DOOR[s][1]) or END_DOOR[s][1] != s * DOOR_Z:
            out.append(f"{where} walkway: the way ends at {way[-1][:2]}, the door is at {END_DOOR[s]}")
        for (x0, z0, f0), (x1, z1, f1) in zip(way, way[1:]):
            if abs(x1 - x0) + abs(z1 - z0) != 1 or abs(f1 - f0) > 0.5:
                out.append(f"{where} walkway: no step from ({x0}, {z0}) at {f0} to ({x1}, {z1}) at {f1}")
        for x, z, feet in way:
            row = math.ceil(feet) - 1                       # the row of the block the feet stand on
            under = c.get(x, row, z)
            span = _span(under, row) if under else None
            if span is None or span[1] != feet:
                out.append(f"{where} walkway: nothing to stand on at ({x}, {z}) at {feet} ({under})")
            for y in range(math.floor(feet), math.floor(feet + 1.79) + 1):
                over = c.get(x, y, z)
                span = _span(over, y) if over else None
                if span and span[1] > feet and span[0] < feet + 1.8:
                    out.append(f"{where} walkway: no headroom at ({x}, {z}) at {feet}: {over} at y {y}")
    # 5. the two walkways are one design, mirrored, and lie as laid; nothing of them stands above
    #    the ridge
    north, south = walkway(-1), walkway(1)
    if {(x, y, -z): state for (x, y, z), state in north.items()} != south:
        out.append("walkways: the north one is not the mirror of the south one")
    for where, laid in (("north", north), ("south", south)):
        for cell, state in laid.items():
            if c.get(*cell) != state:
                out.append(f"{where} walkway: {cell} is {c.get(*cell)}, not {state}")
        if max(y for _, y, _ in laid) >= RIDGE_TOP:
            out.append(f"{where} walkway: it stands above the ridge")
    # 6. the leaves hang in the doors, on a floor; a plate lies before each of the four doors
    for x, y, z, state in doors():
        if c.get(x, y, z) != state:
            out.append(f"door: no leaf at ({x}, {y}, {z})")
    for x, z in S.DOME_ROOM_DOORS["cells"]:
        if not c.has(x, S.DOME_ROOM_DOORS["y"][0] - 1, z):
            out.append(f"door: the leaf at ({x}, {z}) stands on nothing")
    for x, z in thresholds():
        if c.get(x, DECK_Y, z) != PLATE or c.has(x, STAND, z):
            out.append(f"door: the plate at ({x}, {z}) is not as laid")
    # 7. nothing of this package stands on a parapet or outside the walls, and nothing higher than
    #    the kerbs and the door leaves
    plan = facade.shell()
    inside = plan.leaf | plan.core
    scratch = Canvas()
    build(scratch)
    for x, y, z in sorted(scratch.b):
        if (x, z) not in inside:
            out.append(f"outline: ({x}, {y}, {z}) lies outside the parapets")
        if y >= RIDGE_TOP:
            out.append(f"outline: ({x}, {y}, {z}) stands above the ridge")
    return out


_MARKS = {LEAF: "J", B.IRON_BULB: "@", B.VERDIGRIS_CAST: "A", B.IRON_CAST: "K", B.IRON_HATCH: "|"}


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
    xs = (S.WALL_W - 2, S.WALL_E + 3)
    print("FROM ABOVE, the south half (north up; the highest block of every column up to y 22):\n")
    print(_top_plan(c, (GABLE_IN - 5, z_end)))
    print("\nFROM ABOVE, the north half:\n")
    print(_top_plan(c, (-z_end, -(GABLE_IN - 5))))
    ys = (DECK_Y - 2, RIDGE_TOP + 3)
    print(f"\nSECTION along the ridge, x = {RIDGE[1]} (north on the left):\n")
    print(O.section(c, "x", RIDGE[1], (-z_end, z_end), ys))
    print(f"\nSECTION up the treads, z = {ROOF_IN} (west on the left):\n")
    print(O.section(c, "z", ROOF_IN, xs, ys))
    print(f"\nSECTION down the treads, z = {ROOF_OUT} (west on the left):\n")
    print(O.section(c, "z", ROOF_OUT, xs, ys))
    print(f"\nSECTION through the south roof light, z = {GABLE_OUT + 1} (west on the left):\n")
    print(O.section(c, "z", GABLE_OUT + 1, xs, ys))
    print(f"\nSECTION through the south terrace on the doors' row, z = {DOOR_Z} (west on the left):\n")
    print(O.section(c, "z", DOOR_Z, xs, (DECK_Y - 2, STAND + 4)))
    print("\nLetters: M slate flags, c copper channel, Y roof light, D its ceiling light, i iron kerb")
    print("and treads, I iron plate and block, % grating, @ caged lamp, J door leaf, T t slates, F stone.")
    print("Small letters are slabs and stairs.")
    for where, s in WINGS.items():
        way = route(s)
        print(f"\nthe way, {where} wing: {len(way)} columns from the dome room's door {way[0][:2]} to "
              f"{way[-1][:2]} before the door at {END_DOOR[s]}, feet {way[0][2]} .. "
              f"{max(f for _, _, f in way)} .. {way[-1][2]}")


if __name__ == "__main__":
    scene = _scene()
    if "check" not in sys.argv[1:]:
        _drawings(scene)
        print()
    found = check(scene)
    print("\n".join(found) if found else
          "self-check: terraces closed, channels joined, roof lights, both ways walkable and alike, "
          "nothing above the ridge, door leaves and plates, nothing on the parapets -- all good")
    sys.exit(1 if found else 0)
