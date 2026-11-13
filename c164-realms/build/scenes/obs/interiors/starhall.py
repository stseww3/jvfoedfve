"""Work package interiors/starhall: the entrance hall ("star hall"), plan ART-PLAN 8.

The star piece is the great orrery hung in the full-height well. Round it: the black-and-white stone
floor with the brass meridian, the master clock, the switchboard, star charts, the gallery. The room
is written in the skeleton's scene coordinates and dresses whatever shell stands there: it lays the
floor and ceiling finish, and only fills cells the shell left empty.

Two versions for the director to choose between (plan/packages/interiors/starhall.md):
  a  "the well"          ceremonial and symmetric. Twin stone stairs frame the well, the orrery hangs
                         on the door axis, the clock closes the axis on the telescope pier.
  b  "the working hall"  asymmetric. One iron stair along the south wall, the north wall left
                         full-height for the switchboard, the orrery hung off the axis towards it.

Light (plan 3.2, one pool to a view): the orrery's sun is a lamp and the only first-rank light in the
room; the clock dial and the switchboard glow at third rank, every other lamp is a caged bulb (level
4). The ceiling carries small caged bulbs as stars: a ring in a, the Plough in b, its two pointers
aimed north.

Stand-ins until the deliveries arrive (see _stubs): the orrery and clock (A5), lamps, furniture,
charts, globes (A6). The room places no display entity of its own yet.

build() is what the master scene calls. It places nothing until MOVED_IN is set, which waits for A3's
shell and the director's choice of version; until then the room lives in the box test scene
(build/scenes/obs_int_starhall), which calls build_box().
"""
from ..common import blocks as B
from ..common import skeleton as S
from . import _shell as H
from . import _stubs as T

MOVED_IN = False            # set once A3's shell is in the master scene and a version is chosen
VERSION = "a"

HERO = 13                   # the one first-rank pool, under the orrery's sun
GLOW = 6                    # third rank: a dial, a row of pilot lamps
BULB = 4                    # what a caged bulb gives off

ORRERY_Y = 5                # the orbit's level: over a visitor's head, under the gallery's eye line
PANEL = 3                   # the chequer panel reaches this far from the point under the orrery
CLOCK = (H.PIER[0] + 4, H.PIER[1])              # against the pier's east face, on the door axis
BEAMS = (S.pilaster_z(8), S.pilaster_z(9))      # ceiling beams on the pilaster lines

BOARD_LOW = (("knife_switch", "fuses", "gauges", "fuses", "knife_switch"),
             ("pilot_lamps", "dial", "gauges", "dial", "pilot_lamps"))
BOARD_HIGH = BOARD_LOW + (("relays", "pilot_lamps", "nameplate", "pilot_lamps", "relays"),)

LAYOUT = {
    "a": dict(
        stairs="twin", orrery=(12, 0),
        board=dict(cells=[(x, H.Z0) for x in range(3, 8)], rows=BOARD_LOW),
        charts=[dict(cells=[(3, H.Z1), (4, H.Z1), (6, H.Z1), (7, H.Z1)], y=3, wall="south")],
        benches=[dict(cells=[(x, H.Z1) for x in range(3, 8)], wall="south")],
        globes=[(14, -3, B.VERDIGRIS), (14, 3, B.IRON_CAST)],
        lamps=[("north", 13, 4), ("north", 10, 7), ("south", 13, 4), ("south", 10, 7),
               ("north", 5, 4), ("south", 5, 4), ("north", 7, 9), ("south", 7, 9)],
        stars=[(9, 0), (15, 0), (12, -4), (12, 4), (10, -3), (14, -3), (10, 3), (14, 3)],
    ),
    "b": dict(
        stairs="south", orrery=(12, -2),
        board=dict(cells=[(x, H.Z0) for x in range(10, 15)], rows=BOARD_HIGH),
        charts=[dict(cells=[(11, H.Z0), (12, H.Z0), (13, H.Z0)], y=5, wall="north"),
                dict(cells=[(3, H.Z1), (4, H.Z1), (6, H.Z1), (7, H.Z1)], y=3, wall="south")],
        benches=[dict(cells=[(x, H.Z1) for x in range(3, 8)], wall="south"),
                 dict(cells=[(x, H.Z0) for x in range(4, 7)], wall="north")],
        globes=[(14, 3, B.VERDIGRIS)],
        lamps=[("south", 13, 4), ("south", 10, 7), ("north", 10, 5), ("north", 14, 5),
               ("north", 5, 4), ("south", 5, 4), ("north", 7, 9), ("south", 7, 9)],
        # the Plough: bowl, then handle; the pointers (first two) aim north
        stars=[(15, -3), (15, -5), (13, -5), (13, -3), (11, -4), (9, -3), (8, -1)],
    ),
}
WALL_CELL = {"north": lambda x: (x, H.Z0 - 1), "south": lambda x: (x, H.Z1 + 1)}
ROOM_CELL = {"north": lambda x: (x, H.Z0), "south": lambda x: (x, H.Z1)}


def dress(c, origin=(0, 0, 0), version="a", standin=False):
    """Dress the hall standing at `origin`. standin: also let the wall lamps into the walls, which is
    only right in the box test scene; in the real shell they are A6 lamp models and a light beside
    each. Returns dict(entities=<display entities placed>)."""
    lay = LAYOUT[version]
    ox, oy, oz = origin
    pier = H.pier_cells()
    deck = H.deck_cells(lay["stairs"])
    ocx, ocz = lay["orrery"]

    def put(x, y, z, state):
        c.set(ox + x, oy + y, oz + z, state)

    def free(x, y, z):
        return not c.has(ox + x, oy + y, oz + z)

    def glow(x, y, z, level):
        if free(x, y, z):
            put(x, y, z, f"{B.LIGHT}[level={level}]")

    def wainscot(x, y, z, wall):
        if (x, z) not in pier and free(x, y, z):
            put(x, y, z, T.panel(B.WAINSCOT, wall))

    # floor: slate, with a chequer panel under the orrery only, so the pattern gathers at the star
    # piece and the aisles fall back; a brass roundel under the sun, the brass meridian through it
    for x in range(H.X0, H.X1 + 1):
        for z in range(H.Z0, H.Z1 + 1):
            if (x, z) in pier:
                continue
            in_panel = abs(x - ocx) <= PANEL and abs(z - ocz) <= PANEL
            pale = in_panel and (x - ocx + z - ocz) % 2 == 0
            put(x, H.FLOOR, z, B.ASHLAR_FINE.block if pale else B.SLATE_SMOOTH.block)
    put(ocx, H.FLOOR, ocz, B.BRASS_PATTERN.block)
    _, z0, _, z1 = H.well(lay["stairs"])
    for z in range(z0, z1 + 1):
        if z != ocz and free(ocx, H.Y0, z):
            put(ocx, H.Y0, z, B.BRASS_INLAY)

    # ceiling: dark boards between iron beams on the pilaster lines, a brass boss the orrery hangs
    # from, caged bulbs as stars
    for x in range(H.X0, H.X1 + 1):
        for z in range(H.Z0, H.Z1 + 1):
            if (x, z) not in pier:
                put(x, H.CEIL, z, B.IRON_RIVETED.block if z in BEAMS else B.DARK_WOOD.block)
    put(ocx, H.CEIL, ocz, B.BRASS_PATTERN.block)
    for x, z in lay["stars"]:
        put(x, H.CEIL, z, f"{B.IRON_BULB}[lit=true]")

    # walls: a dark dado two panels high, at the ground and again on the deck
    for base, cells in ((H.Y0, None), (S.STAND, deck)):
        for y in (base, base + 1):
            for x in range(H.X0, H.X1 + 1):
                for z, wall in ((H.Z0, "north"), (H.Z1, "south")):
                    doorway = cells is not None and x in (4, 5)
                    if (cells is None or (x, z) in cells) and not doorway:
                        wainscot(x, y, z, wall)
            for z in range(H.Z0, H.Z1 + 1):
                if cells is None or (H.X0, z) in cells:
                    wainscot(H.X0, y, z, "west")
                if cells is None and not H.DOOR_Z[0] <= z <= H.DOOR_Z[1]:
                    wainscot(H.X1, y, z, "east")

    # the star piece, hung from the boss, and the master clock on the pier
    T.orrery(put, ocx, ORRERY_Y, ocz)
    T.hanger(put, ocx, ORRERY_Y + 2, H.Y1, ocz)
    T.mother_clock(put, CLOCK[0], H.Y0, CLOCK[1], "east")

    # the three layers of small pieces: wall (switchboard, charts), surface (benches), floor (globes)
    board = lay["board"]
    T.switchboard(put, board["cells"], H.Y0, "south", board["rows"])
    for group in lay["charts"]:
        T.charts(put, group["cells"], group["y"], group["wall"])
    for group in lay["benches"]:
        T.bench(put, group["cells"], H.Y0, group["wall"])
    for x, z, block in lay["globes"]:
        T.globe(put, x, H.Y0, z, block)

    # light: the one pool under the sun, a glow at the dial and at the board, a bulb at each lamp
    glow(ocx, ORRERY_Y - 1, ocz, HERO)
    glow(CLOCK[0] + 1, H.Y0 + 2, CLOCK[1], GLOW)
    bx = board["cells"][len(board["cells"]) // 2][0]
    glow(bx, H.Y0 + 2, H.Z0 + 1, GLOW)
    for side, x, y in lay["lamps"]:
        if standin:
            wx, wz = WALL_CELL[side](x)
            T.wall_lamp(put, wx, y, wz)
        else:
            rx, rz = ROOM_CELL[side](x)
            glow(rx, y, rz, BULB)
    return {"entities": 0}


def build_box(c, origin=(0, 0, 0), version="a"):
    """The box test scene's room: the stand-in shell, dressed."""
    H.star_hall(c, origin, stairs=LAYOUT[version]["stairs"])
    return dress(c, origin, version, standin=True)


def build(canvas, origin=(0, 0, 0)):
    if not MOVED_IN:
        return 0
    return dress(canvas, origin, VERSION)["entities"]
