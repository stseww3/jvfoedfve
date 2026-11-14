"""Test scene of the card sky/lights: the entrance front under its lights, once for each look.

Not the real front: a placeholder of plain blocks at the skeleton's numbers (seventeen bays in five
parts, plinth, base storey with small windows, string course, great windows, frieze, cornice,
parapet), so that what is judged is the light and nothing else. Windows are blocks and do not
change with the time, so every look has a front of its own, glazed by _lightkit.window_lit() for
that look and shot at that look's time. The fronts stand one behind the other, 100 blocks apart,
each hidden by the one before it:

    blue    x 0       the blue hour: the most windows lit
    deep    x -100    deep night: the foot of the tower, the entrance, the foot of the small dome
    glow    x -200    the afterglow: fewer than blue
    levels  x -300    a flat run of eleven bays, every second one lit: frosted glass with 9, 10 and 12
                      behind it, the amber glass with 10, the curtain with 8

Each front has what throws light at the entrance: the open doorway with a lit hall behind it, an
iron canopy with a string of bulbs, the two bracket lamps and the two street lamps of props/lamps.
Nothing here places a light source: the lamps offer theirs, the windows are registered with
_lightkit.glazed(), and sky.build() (sky/lights.py) places all of them, the source in the doorway
and the wall wash. The terrace ends where the map's does (x 60), with the lower platform six blocks
under it, so that V1 (skeleton) sees each front as the arriving visitor will.

    python -m scenes.obs_sky_lights      writes shots.json; prints the light report, the lighting
                                         maps of the three looks and the levels on the stone
"""
from artkit.canvas import Canvas

from scenes.obs import materials, sky
from scenes.obs.common import blocks as B
from scenes.obs.common import skeleton as S
from scenes.obs.props import lamps
from scenes.obs.sky import _lightkit as L
from scenes.obs.sky import mood as look

BIOME = "obs_blue"
BIOME_MARGIN = 80           # the look has to reach every camera position, not only the blocks
BIOME_MARGIN_Y = 120


def write_pack(pack_dir):
    """The sky's pictures and the repainted blocks the fronts are built of."""
    return list(sky.pack(pack_dir) or []) + list(materials.pack(pack_dir) or [])


STONE, ROUGH, PANEL, EMBLEM = B.ASHLAR_FINE.block, B.ASHLAR_ROUGH.block, B.ASHLAR_PANEL.block, B.ASHLAR_EMBLEM
PLINTH = B.SLATE_BRICK.block
FIELD, WALK = B.SLATE_SMOOTH.block, B.TUFF_SMOOTH.block       # the court's floor: dark slate, the walk a tone lighter
CANOPY = B.IRON_RIVETED.slab + "[type=bottom]"

SPACING = 100
STATIONS = {name: (-SPACING * i, 0, 0) for i, name in enumerate(look.LOOKS)}
BOARD = (-SPACING * len(STATIONS), 0, 0)
BOARD_BAYS = range(1, 12)                   # eleven bays of the wing's kind, no pavilion among them
BOARD_GLASS = {                             # bay -> (its glass, the level behind it); the bays between are dark
    2: (B.WINDOW_FROSTED, 9), 4: (B.WINDOW_FROSTED, 10), 6: (B.WINDOW_FROSTED, 12),
    8: (B.WINDOW_LIT, 10), 10: (B.WINDOW_CURTAIN, 8),
}
BOARD_LEVELS = {bay: level for bay, (role, level) in BOARD_GLASS.items() if role is B.WINDOW_FROSTED}
WING_X = S.east_wall_x(5)                   # the wall face of a wing: the board is flat at this x

DOOR_BAY = 9
BACK = 12                                   # the placeholder is solid from this x to the wall face
BASE_WINDOW = (S.BASE[0] + 1, S.BASE[0] + 2)                # y 3..4, as in main's table
END_PIER = (S.Z_NORTH + 1, S.pilaster_z(2) - 1, S.pilaster_z(15) + 1, S.Z_SOUTH - 1)
DOOR_TOP = S.STRING                         # the doorway is open from the ground to here
HALL_X = (9, S.east_wall_x(DOOR_BAY) - 2)   # the hall behind the three middle bays, clear inside
HALL_Z = (S.pilaster_z(7) + 1, S.pilaster_z(10) - 1)
HALL_TOP = S.WINDOW[1]
CANOPY_X = (S.east_wall_x(DOOR_BAY) + 1, S.east_wall_x(DOOR_BAY) + 4)
CANOPY_Z = (S.pilaster_z(8) - 1, S.pilaster_z(9) + 1)
CANOPY_Y = S.PANEL
CANOPY_LEVEL = 13                           # the bulbs under the canopy: rank 1
GROUND_X = (6, S.EAST_EDGE_X)               # the upper terrace, to its east edge
GROUND_Z = (-60, 60)
LOWER_X = S.EAST_EDGE_X + 39                # the lower platform reaches this far east (V1 stands at 88.5)


def rows(bay, flat=False):
    """Rows of the window of a bay: three, or two next to a corner pier of an end pavilion."""
    return [z for z in range(S.pilaster_z(bay - 1) + 1, S.pilaster_z(bay)) if flat or z not in END_PIER]


def table(bays=range(1, S.N_BAYS + 1), flat=False):
    """The windows of the entrance front, as main's table lists them (main._plan.windows()). flat:
    every bay is a wing's bay, for the levels board."""
    out = []
    for bay in bays:
        cells = [((WING_X if flat else S.east_wall_x(bay)) + S.DEPTH_GLASS, z) for z in rows(bay, flat)]
        for storey, y in (("base", BASE_WINDOW), ("main", S.WINDOW)):
            if storey == "main" or flat or bay != DOOR_BAY:
                out.append(dict(front="east", bay=bay, storey=storey, cells=cells, inward=(-1, 0), y=y))
    return out


TABLE = table()


def face(z, flat=False):
    """x of the east wall face of a row; a pilaster's row takes the face that stands further out."""
    if flat:
        return WING_X
    k, r = divmod(z - S.PIL_Z0, S.BAY)
    bays = [b for b in ((k, k + 1) if r == 0 else (k + 1,)) if 1 <= b <= S.N_BAYS]
    return max(S.east_wall_x(b) for b in bays)


def _front(c, o, windows, glass, flat=False):
    """The placeholder front for the bays of `windows`. glass(window) -> the block of its glass."""
    ox, oy, oz = o

    def put(x, y, z, state):
        c.set(ox + x, oy + y, oz + z, state)

    bays = sorted({w["bay"] for w in windows})
    for z in range(S.pilaster_z(bays[0] - 1), S.pilaster_z(bays[-1]) + 1):
        f = face(z, flat)
        pilaster = (z - S.PIL_Z0) % S.BAY == 0
        for x in range(BACK, f + 1):
            for y in range(S.PLINTH[0], S.PARAPET[1] + 1):
                put(x, y, z, STONE)
        for y in range(S.PLINTH[0], S.PLINTH[1] + 1):       # the plinth is solid to the pilaster plane
            put(f, y, z, PLINTH)
            put(f + S.DEPTH_PILASTER, y, z, PLINTH)
        for y in range(S.BASE[0], S.BASE[1] + 1):
            put(f, y, z, ROUGH)
        put(f + S.DEPTH_PILASTER, S.STRING, z, STONE)
        put(f, S.PANEL, z, STONE if pilaster else PANEL)
        for x in range(f + 1, f + S.DEPTH_CORNICE + 1):
            put(x, S.CORNICE, z, STONE)
        if pilaster:
            for y in range(S.BASE[0], S.BASE[1] + 1):
                put(f + S.DEPTH_PILASTER, y, z, ROUGH)
            for y in range(S.PANEL, S.WINDOW[1] + 1):
                put(f + S.DEPTH_PILASTER, y, z, STONE)
            put(f + S.DEPTH_PILASTER, S.FRIEZE, z, EMBLEM)
    for w in windows:
        block = glass(w)
        y0, y1 = w["y"]
        zs = [z for _, z in w["cells"]]
        for x, z in w["cells"]:
            for y in range(y0, y1 + 1):
                c.clear(ox + x - S.DEPTH_GLASS, oy + y, oz + z)             # the opening in the wall
                put(x, y, z, block)                                         # the glass, one cell back
                c.clear(ox + x + w["inward"][0], oy + y, oz + z + w["inward"][1])   # the room behind it
        if w["storey"] == "main":                           # the two top corners: a hint of the arch
            x = w["cells"][0][0] - S.DEPTH_GLASS
            put(x, y1, zs[0], B.ASHLAR_FINE.stairs + "[half=top,facing=north]")
            put(x, y1, zs[-1], B.ASHLAR_FINE.stairs + "[half=top,facing=south]")


def _ground(c, o, x0, x1, z0, z1, walk=False, lower=None):
    """The floor before a front. walk: the lighter walk to the door. lower: the terrace ends at x1
    with a retaining wall, and the lower platform runs on from there to this x."""
    ox, oy, oz = o
    c.box(ox + x0, oy + S.PAVING_Y, oz + z0, ox + x1, oy + S.PAVING_Y, oz + z1, FIELD)
    if walk:                                                # the walk to the door: the door bay and its pilasters
        c.box(ox + BACK, oy + S.PAVING_Y, oz + S.pilaster_z(8), ox + x1, oy + S.PAVING_Y, oz + S.pilaster_z(9), WALK)
    if lower is not None:
        c.box(ox + x1, oy + S.LOWER_PAVING_Y, oz + z0, ox + x1, oy + S.PAVING_Y - 1, oz + z1, PLINTH)
        c.box(ox + x1 + 1, oy + S.LOWER_PAVING_Y, oz + z0, ox + lower, oy + S.LOWER_PAVING_Y, oz + z1, FIELD)


def _entrance(c, o):
    """The open doorway, the hall behind the three middle bays with two lamps on its back wall, the
    canopy and its string of bulbs. Returns the number of display entities."""
    ox, oy, oz = o
    wall = S.east_wall_x(DOOR_BAY)
    (x0, x1), (z0, z1) = HALL_X, HALL_Z
    c.box(ox + x0 - 1, oy + S.PAVING_Y, oz + z0 - 1, ox + BACK - 1, oy + HALL_TOP + 1, oz + z1 + 1, STONE)
    c.carve(ox + x0, oy, oz + z0, ox + x1, oy + HALL_TOP, oz + z1)
    c.box(ox + x0, oy + S.PAVING_Y, oz + z0, ox + x1, oy + S.PAVING_Y, oz + z1, WALK)
    for z in rows(DOOR_BAY):
        c.carve(ox + wall + S.DEPTH_GLASS, oy, oz + z, ox + wall + S.DEPTH_CORNICE, oy + DOOR_TOP, oz + z)
    n = 0
    for z in (S.AXIS_Z - 3.0, S.AXIS_Z + 3.0):
        n += lamps.place(c, "bracket", (float(x0), 4.0, z), facing="east", origin=o)
    c.box(ox + CANOPY_X[0], oy + CANOPY_Y, oz + CANOPY_Z[0], ox + CANOPY_X[1], oy + CANOPY_Y, oz + CANOPY_Z[1],
          CANOPY, keep=True)
    y = CANOPY_Y - lamps.HANG
    n += lamps.festoon(c, (CANOPY_X[1] + 0.5, y, CANOPY_Z[0] + 0.2), (CANOPY_X[1] + 0.5, y, CANOPY_Z[1] + 0.8),
                       origin=o, level=CANOPY_LEVEL)
    return n


def _station(c, name, o):
    """One whole front for one look. Returns the display entities placed: (the lamps, sky's own)."""
    _ground(c, o, GROUND_X[0], GROUND_X[1], GROUND_Z[0], GROUND_Z[1], walk=True, lower=LOWER_X)
    _front(c, o, TABLE, lambda w: L.window_lit(w["front"], w["bay"], w["storey"], look=name, table=TABLE)[1].block)
    n = _entrance(c, o)
    n += lamps.build(c, o)                  # the bracket lamps beside the door, the two street lamps
    L.glazed(c, TABLE, origin=o, group=name, look=name)
    return n, sky.build(c, o)


def board_windows():
    """The windows of the levels board; a lit one carries its glass and the level asked for behind it."""
    out = []
    for w in table(BOARD_BAYS, flat=True):
        role, level = BOARD_GLASS.get(w["bay"], (B.WINDOW_DARK, None))
        out.append(dict(w, role=role, level=level))
    return out


def _board(c, o):
    _ground(c, o, GROUND_X[0], 44, S.pilaster_z(BOARD_BAYS[0] - 1) - 8, S.pilaster_z(BOARD_BAYS[-1]) + 8)
    windows = board_windows()
    _front(c, o, windows, lambda w: w["role"].block, flat=True)
    L.glazed(c, windows, origin=o, group="levels")      # lit by the first sky.build() that follows


def build():
    c = Canvas()
    L.dress(c)                              # this scene shows the building's own lights, whatever the switch says
    _board(c, BOARD)
    counts = {"props": 0, "sky": 0}
    for name, o in STATIONS.items():
        n_props, n_sky = _station(c, name, o)
        counts["props"] += n_props
        counts["sky"] += n_sky
    c.entity_counts = counts
    return c


# ---- the shots -------------------------------------------------------------------------------------------
EYE = 1.7
FRONT_X = S.east_wall_x(DOOR_BAY) + S.DEPTH_PILASTER        # the plane the distances are counted from
AXIS = S.AXIS_Z


def near(bay, flat=False):
    """A close look at the surround of a bay's great window: the jamb, the sill, the pilaster's side."""
    wall, z = (WING_X if flat else S.east_wall_x(bay)), S.bay_center_z(bay)
    return (wall + 4.5, 9.5, z + 4.0), (wall + 0.0, 10.5, z + 0.0)


def surround_bay():
    """A bay in the middle of a wing whose great window is lit under every look."""
    for bay in (4, 5, 6, 12, 13, 14):
        if all(L.window_lit("east", bay, "main", look=name, table=TABLE)[0] >= L.LIT for name in STATIONS):
            return bay
    return next(bay for bay in (4, 5, 6, 12, 13, 14)
                if L.window_lit("east", bay, "main", look="blue", table=TABLE)[0] >= L.LIT)


SURROUND_BAY = surround_bay()
VIEWS = {   # name: (eye, looks at), from a front's origin
    "front": ((FRONT_X + 20.5, EYE, AXIS), (FRONT_X - 1.0, 8.5, AXIS)),            # 20 blocks, head on
    "axis": ((FRONT_X + 40.5, EYE, AXIS), (FRONT_X - 1.0, 11.0, AXIS)),            # the court's V2
    "v1": (S.V1["pos"], S.V1["look_at"]),                                          # the arrival view, 80 blocks
    "slant": ((S.WALL_E + 13.5, EYE, -10.5), (S.WALL_E + 1.0, 8.5, -23.0)),        # 45 degrees, 12 blocks off
    "surround": near(SURROUND_BAY),
    "door": ((FRONT_X + 9.5, EYE, AXIS + 4.0), (FRONT_X - 1.0, 4.5, AXIS)),
    "wash": ((S.WALL_E + 9.5, EYE, -16.5), (S.WALL_E + 1.0, 2.0, -10.0)),
}
EVERY_LOOK = ("front", "axis", "v1", "slant", "surround")
TWO_LOOKS = {"blue": ("door", "wash"), "deep": ("door", "wash")}
BOARD_MID = (S.pilaster_z(BOARD_BAYS[0] - 1) + S.pilaster_z(BOARD_BAYS[-1])) / 2.0 + 0.5


def shots():
    out = []

    def add(name, view, o, at):
        eye, target = view
        out.append({"name": name, "pos": [round(eye[i] + o[i], 2) for i in range(3)],
                    "look_at": [round(target[i] + o[i], 2) for i in range(3)], "time": at})

    for name, o in STATIONS.items():
        for view in EVERY_LOOK + TWO_LOOKS.get(name, ()):
            add(f"{name}_{view}", VIEWS[view], o, look.tick(name))
    board = ((WING_X + 20.5, EYE, BOARD_MID), (WING_X + 0.0, 8.0, BOARD_MID))
    add("levels_front", board, BOARD, look.tick("blue"))
    add("levels_front_deep", board, BOARD, look.tick("deep"))
    for bay, level in BOARD_LEVELS.items():
        add(f"levels_{level}", near(bay, flat=True), BOARD, look.tick("blue"))
    return out
