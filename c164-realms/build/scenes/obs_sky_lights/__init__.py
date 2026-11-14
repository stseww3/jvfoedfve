"""Test scene of the card sky/lights: the entrance front under its lights, once for each look.

Not the real front: a placeholder of plain blocks at the skeleton's numbers (seventeen bays in five
parts, plinth, base storey with small windows, string course, great windows, frieze, cornice,
parapet), so that what is judged is the light and nothing else. Windows are blocks and do not
change with the time, so every look has a front of its own, glazed by _lightkit.window_lit() for
that look and shot at that look's time. The fronts stand one behind the other, 100 blocks apart,
each hidden by the one before it:

    blue    x 0       the blue hour: the most windows lit
    deep    x -100    deep night: the entrance, the foot of the tower and a few more
    glow    x -200    the afterglow: fewer than blue
    levels  x -300    the north wing alone, bays 3, 5 and 7 lit with 9, 10 and 12 behind the glass

Each front has what throws light at the entrance: the open doorway with a lit hall behind it, an
iron canopy with a string of bulbs, the two bracket lamps and the two street lamps of props/lamps.
Nothing here places a light source: the lamps offer theirs, the windows are registered with
_lightkit.glazed(), and sky.build() (sky/lights.py) places all of them, the source in the doorway
and the wall wash.

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
BOARD_BAYS = range(2, 9)                    # the north wing with the bay at either end of it
BOARD_LEVELS = {3: 9, 5: 10, 7: 12}         # bay -> the level behind its glass; the bays between are dark

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
GROUND_X = (6, 80)
GROUND_Z = (-44, 44)


def rows(bay):
    """Rows of the window of a bay: three, or two next to a corner pier of an end pavilion."""
    return [z for z in range(S.pilaster_z(bay - 1) + 1, S.pilaster_z(bay)) if z not in END_PIER]


def table(bays=range(1, S.N_BAYS + 1)):
    """The windows of the entrance front, as main's table lists them (main._plan.windows())."""
    out = []
    for bay in bays:
        cells = [(S.east_wall_x(bay) + S.DEPTH_GLASS, z) for z in rows(bay)]
        for storey, y in (("base", BASE_WINDOW), ("main", S.WINDOW)):
            if storey == "main" or bay != DOOR_BAY:
                out.append(dict(front="east", bay=bay, storey=storey, cells=cells, inward=(-1, 0), y=y))
    return out


TABLE = table()


def face(z):
    """x of the east wall face of a row; a pilaster's row takes the face that stands further out."""
    k, r = divmod(z - S.PIL_Z0, S.BAY)
    bays = [b for b in ((k, k + 1) if r == 0 else (k + 1,)) if 1 <= b <= S.N_BAYS]
    return max(S.east_wall_x(b) for b in bays)


def _front(c, o, windows, glass):
    """The placeholder front for the bays of `windows`. glass(window) -> the block of its glass."""
    ox, oy, oz = o

    def put(x, y, z, state):
        c.set(ox + x, oy + y, oz + z, state)

    bays = sorted({w["bay"] for w in windows})
    for z in range(S.pilaster_z(bays[0] - 1), S.pilaster_z(bays[-1]) + 1):
        f = face(z)
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


def _ground(c, o, x0, x1, z0, z1, walk=False):
    ox, oy, oz = o
    c.box(ox + x0, oy + S.PAVING_Y, oz + z0, ox + x1, oy + S.PAVING_Y, oz + z1, FIELD)
    if walk:                                                # the walk to the door: the door bay and its pilasters
        c.box(ox + BACK, oy + S.PAVING_Y, oz + S.pilaster_z(8), ox + x1, oy + S.PAVING_Y, oz + S.pilaster_z(9), WALK)


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
    _ground(c, o, GROUND_X[0], GROUND_X[1], GROUND_Z[0], GROUND_Z[1], walk=True)
    _front(c, o, TABLE, lambda w: L.window_lit(w["front"], w["bay"], w["storey"], look=name, table=TABLE)[1].block)
    n = _entrance(c, o)
    n += lamps.build(c, o)                  # the bracket lamps beside the door, the two street lamps
    L.glazed(c, TABLE, origin=o, group=name, look=name)
    return n, sky.build(c, o)


def board_windows():
    """The windows of the levels board; a lit one carries the level asked for behind its glass."""
    return [dict(w, level=BOARD_LEVELS.get(w["bay"])) for w in table(BOARD_BAYS)]


def _board(c, o):
    _ground(c, o, GROUND_X[0], 40, S.pilaster_z(BOARD_BAYS[0] - 1) - 8, S.pilaster_z(BOARD_BAYS[-1]) + 8)
    windows = board_windows()
    _front(c, o, windows, lambda w: (B.WINDOW_FROSTED if w["level"] else B.WINDOW_DARK).block)
    L.glazed(c, windows, origin=o, group="levels")      # lit by the first sky.build() that follows


def build():
    c = Canvas()
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


def near(bay):
    """A close look at the surround of a bay's great window: the jamb, the sill, the pilaster's side."""
    wall, z = S.east_wall_x(bay), S.bay_center_z(bay)
    return (wall + 4.5, 9.5, z + 4.0), (wall + 0.0, 10.5, z + 0.0)


SURROUND_BAY = 3            # lit in every look
VIEWS = {   # name: (eye, looks at), from a front's origin
    "front": ((FRONT_X + 20.5, EYE, AXIS), (FRONT_X - 1.0, 8.5, AXIS)),            # 20 blocks, head on
    "axis": ((FRONT_X + 40.5, EYE, AXIS), (FRONT_X - 1.0, 11.0, AXIS)),            # the court's V2
    "far": ((FRONT_X + 60.5, EYE, AXIS), (FRONT_X - 1.0, 11.0, AXIS)),             # 60 blocks
    "slant": ((S.WALL_E + 13.5, EYE, -5.5), (S.WALL_E + 1.0, 8.5, -18.0)),         # 45 degrees, 12 blocks off
    "surround": near(SURROUND_BAY),
    "door": ((FRONT_X + 9.5, EYE, AXIS + 4.0), (FRONT_X - 1.0, 4.5, AXIS)),
    "wash": ((S.WALL_E + 9.5, EYE, -16.5), (S.WALL_E + 1.0, 2.0, -10.0)),
}
EVERY_LOOK = ("front", "axis", "far", "slant", "surround")
TWO_LOOKS = {"blue": ("door", "wash"), "deep": ("door", "wash")}
BOARD_MID = S.bay_center_z(5)


def shots():
    out = []

    def add(name, view, o, at):
        eye, target = view
        out.append({"name": name, "pos": [round(eye[i] + o[i], 2) for i in range(3)],
                    "look_at": [round(target[i] + o[i], 2) for i in range(3)], "time": at})

    for name, o in STATIONS.items():
        for view in EVERY_LOOK + TWO_LOOKS.get(name, ()):
            add(f"{name}_{view}", VIEWS[view], o, look.tick(name))
    board = ((S.WALL_E + 15.5, EYE, BOARD_MID + 0.5), (S.WALL_E + 0.0, 8.0, BOARD_MID + 0.5))
    add("levels_front", board, BOARD, look.tick("blue"))
    add("levels_front_deep", board, BOARD, look.tick("deep"))
    for bay, level in BOARD_LEVELS.items():
        add(f"levels_{level}", near(bay), BOARD, look.tick("blue"))
    return out
