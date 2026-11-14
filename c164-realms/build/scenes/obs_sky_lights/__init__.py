"""Test scene of the card sky/lights: the main building under its lights, once for each look.

The building is the real one: what the main line and the props line build in the master scene
(their build() at the building's origin), on a plain terrace that ends where the map's does (x 60), with the lower
platform six blocks under it, so that V1 (skeleton) sees each front as the arriving visitor will.
Windows are blocks and do not change with the time, so every look has a building of its own, glazed
for that look (_lightkit.under) and shot at that look's time. The buildings stand one behind the
other, 200 blocks apart, each hidden by the one before it:

    blue    x 0       the blue hour: the most windows lit
    deep    x -200    deep night: the foot of the tower, the entrance, the foot of the small dome
    glow    x -400    the afterglow: fewer than blue
    levels  x -600    a flat run of eleven bays of plain blocks at the skeleton's numbers, every
                      second one lit: frosted glass with 9, 10 and 12 behind it, the amber glass with
                      10, the curtain with 8. What is judged there is the level and nothing else.

Nothing here places a light source: the lamps of props offer theirs, the windows of the board are
registered with _lightkit.glazed(), and sky.build() (sky/lights.py) places all of them, the sources
behind the lit windows of main's table, the light of the entrance and the wall wash. The scene asks
for the building's own lights with _lightkit.dress(), whatever the switch sky/lights.DRESS says.

    python -m scenes.obs_sky_lights      writes shots.json; prints the light report, the lighting
                                         maps of the three looks and the levels on the stone
"""
from artkit.canvas import Canvas

from scenes.obs import main as main_line          # not `main`, `props`: this folder has modules of those names
from scenes.obs import materials, sky
from scenes.obs import props as props_line
from scenes.obs.common import blocks as B
from scenes.obs.common import skeleton as S
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

SPACING = 200
STATIONS = {name: (-SPACING * i, 0, 0) for i, name in enumerate(look.LOOKS)}
GROUND_X = (-60, S.EAST_EDGE_X)             # the upper terrace, from behind the apse to its east edge
GROUND_Z = (-60, 60)
LOWER_X = S.EAST_EDGE_X + 39                # the lower platform reaches this far east (V1 stands at 88.5)
WALK_Z = (S.pilaster_z(8), S.pilaster_z(9))                 # the walk to the door: the middle bay and its pilasters

BOARD = (-SPACING * len(STATIONS), 0, 0)
BOARD_BAYS = range(1, 12)                   # eleven bays of the wing's kind
BOARD_GLASS = {                             # bay -> (its glass, the level behind it); the bays between are dark
    2: (B.WINDOW_FROSTED, 9), 4: (B.WINDOW_FROSTED, 10), 6: (B.WINDOW_FROSTED, 12),
    8: (B.WINDOW_LIT, 10), 10: (B.WINDOW_CURTAIN, 8),
}
BOARD_LEVELS = {bay: level for bay, (role, level) in BOARD_GLASS.items() if role is B.WINDOW_FROSTED}
WING_X = S.east_wall_x(5)                   # the wall face of a wing: the board stands at this x
BACK = WING_X - 3                           # the board is solid from this x to the wall face
BASE_WINDOW = (S.BASE[0] + 1, S.BASE[0] + 2)                # y 3..4, as in main's table


def _ground(c, o, x0, x1, z0, z1, walk=False, lower=None):
    """The floor round a building. walk: the lighter walk to the door. lower: the terrace ends at x1
    with a retaining wall, and the lower platform runs on from there to this x."""
    ox, oy, oz = o
    c.box(ox + x0, oy + S.PAVING_Y, oz + z0, ox + x1, oy + S.PAVING_Y, oz + z1, FIELD)
    if walk:
        c.box(ox + S.WALL_E, oy + S.PAVING_Y, oz + WALK_Z[0], ox + x1, oy + S.PAVING_Y, oz + WALK_Z[1], WALK)
    if lower is not None:
        c.box(ox + x1, oy + S.LOWER_PAVING_Y, oz + z0, ox + x1, oy + S.PAVING_Y - 1, oz + z1, PLINTH)
        c.box(ox + x1 + 1, oy + S.LOWER_PAVING_Y, oz + z0, ox + lower, oy + S.LOWER_PAVING_Y, oz + z1, FIELD)


def _station(c, name, o):
    """The building for one look. Returns the display entities placed: (the other lines', sky's own)."""
    _ground(c, o, GROUND_X[0], GROUND_X[1], GROUND_Z[0], GROUND_Z[1], walk=True, lower=LOWER_X)
    with L.under(name):
        n = int(main_line.build(c, o) or 0) + int(props_line.build(c, o) or 0)
    return n, sky.build(c, o)


def board_windows():
    """The windows of the levels board, as main's table lists windows; a lit one carries its glass
    and the level asked for behind it."""
    out = []
    for bay in BOARD_BAYS:
        cells = [(WING_X + S.DEPTH_GLASS, z) for z in range(S.pilaster_z(bay - 1) + 1, S.pilaster_z(bay))]
        role, level = BOARD_GLASS.get(bay, (B.WINDOW_DARK, None))
        for storey, y in (("base", BASE_WINDOW), ("main", S.WINDOW)):
            out.append(dict(front="east", bay=bay, storey=storey, cells=cells, inward=(-1, 0), y=y,
                            role=role, level=level))
    return out


def _board(c, o):
    """The levels board: a flat front of plain blocks at the skeleton's numbers (plinth, base storey
    with small windows, string course, great windows, frieze, cornice, parapet)."""
    ox, oy, oz = o

    def put(x, y, z, state):
        c.set(ox + x, oy + y, oz + z, state)

    z0, z1 = S.pilaster_z(BOARD_BAYS[0] - 1), S.pilaster_z(BOARD_BAYS[-1])
    _ground(c, o, BACK - 3, WING_X + 28, z0 - 8, z1 + 8)
    out = WING_X + S.DEPTH_PILASTER
    for z in range(z0, z1 + 1):
        pilaster = (z - S.PIL_Z0) % S.BAY == 0
        for x in range(BACK, WING_X + 1):
            for y in range(S.PLINTH[0], S.PARAPET[1] + 1):
                put(x, y, z, STONE)
        for y in range(S.PLINTH[0], S.PLINTH[1] + 1):       # the plinth is solid to the pilaster plane
            put(WING_X, y, z, PLINTH)
            put(out, y, z, PLINTH)
        for y in range(S.BASE[0], S.BASE[1] + 1):
            put(WING_X, y, z, ROUGH)
        put(out, S.STRING, z, STONE)
        put(WING_X, S.PANEL, z, STONE if pilaster else PANEL)
        for x in range(WING_X + 1, WING_X + S.DEPTH_CORNICE + 1):
            put(x, S.CORNICE, z, STONE)
        if pilaster:
            for y in range(S.BASE[0], S.BASE[1] + 1):
                put(out, y, z, ROUGH)
            for y in range(S.PANEL, S.WINDOW[1] + 1):
                put(out, y, z, STONE)
            put(out, S.FRIEZE, z, EMBLEM)
    windows = board_windows()
    for w in windows:
        y0, y1 = w["y"]
        zs = [z for _, z in w["cells"]]
        for x, z in w["cells"]:
            for y in range(y0, y1 + 1):
                c.clear(ox + x - S.DEPTH_GLASS, oy + y, oz + z)             # the opening in the wall
                put(x, y, z, w["role"].block)                               # the glass, one cell back
                c.clear(ox + x + w["inward"][0], oy + y, oz + z + w["inward"][1])   # the room behind it
        if w["storey"] == "main":                           # the two top corners: a hint of the arch
            put(WING_X, y1, zs[0], B.ASHLAR_FINE.stairs + "[half=top,facing=north]")
            put(WING_X, y1, zs[-1], B.ASHLAR_FINE.stairs + "[half=top,facing=south]")
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
EYE = S.EYE
FRONT_X = S.east_wall_x(9) + S.DEPTH_PILASTER       # the plane the distances are counted from
AXIS = S.AXIS_Z
APSE_X = S.SUNSET_PLATFORM["centre"][0]             # the west door stands here


def near(wall, bay):
    """A close look at the surround of a bay's great window: the jamb, the sill, the pilaster's side."""
    z = S.bay_center_z(bay)
    return (wall + 4.5, 9.5, z + 4.0), (wall + 0.0, 10.5, z + 0.0)


def surround_bay():
    """A bay in the middle of a wing whose great window is lit under every look."""
    for bay in (4, 5, 6, 12, 13, 14):
        if all(L.window_lit("east", bay, "main", look=name)[0] >= L.LIT for name in STATIONS):
            return bay
    return next(bay for bay in (4, 5, 6, 12, 13, 14) if L.window_lit("east", bay, "main", look="blue")[0] >= L.LIT)


SURROUND_BAY = surround_bay()
VIEWS = {   # name: (eye, looks at), from a building's origin
    "front": ((FRONT_X + 20.5, EYE, AXIS), (FRONT_X - 1.0, 8.5, AXIS)),            # 20 blocks, head on
    "axis": ((FRONT_X + 40.5, EYE, AXIS), (FRONT_X - 1.0, 13.0, AXIS)),            # the court's V2
    "v1": (S.V1["pos"], S.V1["look_at"]),                                          # the arrival view, 80 blocks
    "slant": ((S.WALL_E + 13.5, EYE, -10.5), (S.WALL_E + 1.0, 8.5, -23.0)),        # 45 degrees, 12 blocks off
    "surround": near(S.east_wall_x(SURROUND_BAY), SURROUND_BAY),
    "door": ((FRONT_X + 9.5, EYE, AXIS + 4.0), (FRONT_X - 1.0, 4.5, AXIS)),
    "wash": ((S.WALL_E + 9.5, EYE, -16.5), (S.WALL_E + 1.0, 2.0, -10.0)),
    "west": ((APSE_X - 28.5, EYE, AXIS), (APSE_X, 10.0, AXIS)),                    # from the sunset platform
}
EVERY_LOOK = ("front", "axis", "v1", "slant", "surround")
SOME_LOOKS = {"blue": ("door", "wash", "west"), "deep": ("door", "wash")}
BOARD_MID = (S.pilaster_z(BOARD_BAYS[0] - 1) + S.pilaster_z(BOARD_BAYS[-1])) / 2.0 + 0.5


def shots():
    out = []

    def add(name, view, o, at):
        eye, target = view
        out.append({"name": name, "pos": [round(eye[i] + o[i], 2) for i in range(3)],
                    "look_at": [round(target[i] + o[i], 2) for i in range(3)], "time": at})

    for name, o in STATIONS.items():
        for view in EVERY_LOOK + SOME_LOOKS.get(name, ()):
            add(f"{name}_{view}", VIEWS[view], o, look.tick(name))
    board = ((WING_X + 20.5, EYE, BOARD_MID), (WING_X + 0.0, 8.0, BOARD_MID))
    add("levels_front", board, BOARD, look.tick("blue"))
    add("levels_front_deep", board, BOARD, look.tick("deep"))
    for bay, level in BOARD_LEVELS.items():
        add(f"levels_{level}", near(WING_X, bay), BOARD, look.tick("blue"))
    return out
