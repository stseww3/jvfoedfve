"""Test scene of the work package props/electrics-signs: the cable station's name board
(props/signs, station_board) on the gable it is made for.

site/cablecar is not in the assembly yet. What stands here is its two houses as its branch builds
them (c338, cursor/c164-cable-cablecar-f3-9cf7 at 1f732aac), cell for cell and in the map's own
coordinates, on the real floor of the lower platform (site/lowerplatform): the station's raised
platform with its two steps on the west side, the waiting room with the lit window in its gable
and the seat the package keeps for the board in the course over it (SIGN), and behind it the winch
house, whose gable shows over the waiting room's roof. The track, the car, the glass roof over it
and the hill are left out: the shots stand west of the gable and north of the station's front, as
somebody does who walks from the grand stair to the car, and from there those lie behind the two
houses or beside the picture.

The board is hung by signs.station() on that seat, as signs.build() hangs it on the real station
once site/cablecar is in the tree and the switch signs.DRESS is on. Its light is what the place
has: the waiting room's window under it (the sky line lights it, _lightkit.glazed) and the sky.

The shots are written from the numbers below:  python -m scenes.obs_props_elecsign_station
"""
from artkit.canvas import Canvas

from scenes.obs import materials, sky
from scenes.obs.common import blocks as B
from scenes.obs.common import skeleton as S
from scenes.obs.props import signs
from scenes.obs.site import _kit as K
from scenes.obs.site import lowerplatform
from scenes.obs.sky import _lightkit

BIOME = "obs_blue"
BIOME_MARGIN = 32
BIOME_MARGIN_Y = 32
TIME = 14000                    # light version A, the default (INTERFACE: 18000 is B)
TIME_DEEP = 18000

# ---- the station's numbers, as site/cablecar has them at 1f732aac ----------------------------------------
X0, Z0, X1, Z1 = S.CABLE_STATION        # x 75..91, z -40..-26
LOW = S.LOWER_GROUND                    # -6: feet on the lower platform; the lower of the platform's two courses
FEET = S.STATION_GROUND                 # -4: feet on the station platform
TOP = FEET - 1                          # -5: the platform's paving course
AXIS = K.CABLE_RIDGE_Z                  # -33: the row of the track's axis
HEAD = int(S.V1["pos"][0])              # 88: the last cell of the track
WINCH = (HEAD - 2, Z0, X1, AXIS - 3)    # x 86..91, z -40..-36: the winch house, walls included
WINCH_TOP = FEET + 6                    # 2: its top wall course; its eaves are at 3, its ridge at 5
WINCH_OPENING = dict(x=(WINCH[0] + 1, WINCH[2] - 1), y=(FEET, FEET + 4))    # its south side, open to the platform
WAIT = (WINCH[0] - 6, Z0, WINCH[0] - 1, Z0 + 3)     # x 80..85, z -40..-37: the waiting room
WAIT_TOP = FEET + 3                     # -1: its top wall course; its eaves are at 0, its roof's top at 1.5
DOOR = ((WAIT[0] + WAIT[2] + 1) // 2, WAIT[3])      # (83, -37)
STACK = dict(cell=(DOOR[0], WAIT[1]), y=(WAIT_TOP + 1, WAIT_TOP + 4))       # the chimney: (83, -40), y 0..3
# the seat of the name board: on the waiting room's gable, the course over its lit window
SIGN = dict(point=(float(WAIT[0]), WAIT_TOP + 0.5, (WAIT[1] + WAIT[3]) / 2.0 + 0.5), facing="west", width=2)

BODY = PAVE = WALL = B.TUFF_BRICK.block
KERB = COURSE = B.TUFF_SMOOTH.block     # kerb lines, the plinth course, the course under the eaves, the angle piers
STEP = CORBEL = B.TUFF_SMOOTH.stairs
ROOF = B.SLATE_TILE.stairs
ROOF_FLAT = B.SLATE_TILE.slab + "[type=bottom]"
IRON = B.IRON_RIVETED.block
FINIAL = B.IRON_ROD + "[facing=up]"
POT = B.SLATE_SMOOTH.wall
IRON_DOOR = B.IRON_DOOR
LIT = B.WINDOW_FROSTED
DARK = B.WINDOW_DARK.pane
SHUT = B.WINDOW_BLIND.pane


def windows():
    """The glass of the two houses, as records sky/_lightkit.glazed() takes. Lit are the waiting
    room's gable window and the two lights of the winch house's east wall; the front and the
    back are dark."""
    wx0, wz0, _, wz1 = WAIT
    hx0, hz0, hx1, hz1 = WINCH
    door = DOOR[0]
    mid = (hz0 + hz1) // 2
    low, tall = (FEET + 1, FEET + 2), (FEET + 1, FEET + 4)
    high, over, apex = (FEET + 2, FEET + 4), (FEET + 2, FEET + 2), (WINCH_TOP + 1, WINCH_TOP + 1)

    def window(front, bay, cells, inward, y, glass, storey="main"):
        return dict(front=f"station.{front}", bay=bay, storey=storey, cells=cells, inward=inward, y=y, glass=glass)

    return [
        window("west", wz0 + 1, [(wx0, z) for z in range(wz0 + 1, wz1)], (1, 0), low, LIT.pane),
        window("south", door - 2, [(door - 2, wz1)], (0, -1), low, SHUT),
        window("south", door, [(door, wz1)], (0, -1), over, DARK),
        window("south", door + 2, [(door + 2, wz1)], (0, -1), low, SHUT),
        window("north", door - 1, [(door - 1, wz0)], (0, 1), low, DARK),
        window("north", door + 1, [(door + 1, wz0)], (0, 1), low, DARK),
        window("east", hz0 + 1, [(hx1, hz0 + 1)], (-1, 0), tall, LIT.block),
        window("east", hz1 - 1, [(hx1, hz1 - 1)], (-1, 0), tall, LIT.block),
        window("north", hx0 + 1, [(hx0 + 1, hz0)], (0, 1), high, DARK),
        window("north", hx1 - 1, [(hx1 - 1, hz0)], (0, 1), high, DARK),
        window("west", mid, [(hx0, mid)], (1, 0), apex, DARK, storey="gable"),
    ]


def _platform(c):
    """Two courses over the station's footprint, the upper one paved; two steps down along the
    west side; a kerb line behind their head and the track's axis carried on to them; the
    railing of the north edge west of the waiting room."""
    for x in range(X0, X1 + 1):
        for z in range(Z0, Z1 + 1):
            c.set(x, LOW, z, BODY)
            c.set(x, TOP, z, PAVE)
    for z in range(Z0, Z1 + 1):
        c.set(X0, LOW, z, STEP + "[facing=east]")
        c.clear(X0, TOP, z)
        c.set(X0 + 1, TOP, z, STEP + "[facing=east]")
    for z in range(Z0, Z1 - 1):
        c.set(X0 + 2, TOP, z, KERB)
    for x in range(X0 + 3, HEAD):
        c.set(x, TOP, AXIS, KERB)
    north = [(x, Z0) for x in range(X0 + 2, WAIT[0])]
    K.rail(c, (0, 0, 0), north, north[:1], y=FEET, kerb=False)


def _shell(c, box, y0, y1):
    """Four walls: a polished course at the foot and at the top, polished angle piers, brick between."""
    x0, z0, x1, z1 = box
    for x in range(x0, x1 + 1):
        for z in range(z0, z1 + 1):
            if x not in (x0, x1) and z not in (z0, z1):
                continue
            corner = x in (x0, x1) and z in (z0, z1)
            for y in range(y0, y1 + 1):
                c.set(x, y, z, COURSE if corner or y in (y0, y1) else WALL)


def _gable_roof(c, box, y, gables=None):
    """A slate roof of two pitches over a box, the ridge east-west; the eaves course is y. The
    gable walls (at the x of `gables`, both ends by default) are filled under it."""
    x0, z0, x1, z1 = box
    half = (z1 - z0) // 2
    gables = (x0, x1) if gables is None else gables
    for x in range(x0, x1 + 1):
        for i in range(half):
            c.set(x, y + i, z0 + i, ROOF + "[facing=south]")
            c.set(x, y + i, z1 - i, ROOF + "[facing=north]")
            if x in gables:
                for z in range(z0 + i + 1, z1 - i):
                    c.set(x, y + i, z, WALL)
        for z in range(z0 + half, z1 - half + 1):
            c.set(x, y + half, z, ROOF_FLAT)


def _waiting_room(c):
    """The front: a shut door between two piers under a dark light, a window either side with its
    blind down; the row behind the front is walled up where the front has an opening, so the
    light of the gable window stays off that side. The chimney stands in the back wall."""
    x0, z0, x1, z1 = WAIT
    door = DOOR[0]
    _shell(c, (x0, z0, x1 + 1, z1), FEET, WAIT_TOP)
    c.set(door, FEET, z1, IRON_DOOR + "[half=lower,facing=south,hinge=left]")
    c.set(door, FEET + 1, z1, IRON_DOOR + "[half=upper,facing=south,hinge=left]")
    for w in windows():
        if w["front"] == "station.south":
            dx, dz = w["inward"]
            for x, z in w["cells"]:
                for y in range(FEET if x == door else w["y"][0], w["y"][1] + 1):
                    c.set(x + dx, y, z + dz, WALL)
    _gable_roof(c, WAIT, WAIT_TOP + 1, gables=(x0,))
    sx, sz = STACK["cell"]
    low, top = STACK["y"]
    for y in range(low, top + 1):
        c.set(sx, y, sz, POT if y == top else COURSE if y == top - 1 else WALL)


def _winch_house(c):
    """Its south side is one opening between the angle piers, under an iron girder on two
    corbels; its west gable shows over the waiting room's roof, an apex stone and a rod on it.
    The winch is not here: the room is empty."""
    x0, z0, x1, z1 = WINCH
    mid = (z0 + z1) // 2
    _shell(c, WINCH, FEET, WINCH_TOP)
    ox0, ox1 = WINCH_OPENING["x"]
    oy0, oy1 = WINCH_OPENING["y"]
    for x in range(ox0, ox1 + 1):
        for y in range(oy0, oy1 + 1):
            c.clear(x, y, z1)
        c.set(x, oy1 + 1, z1, IRON)
    c.set(ox0, oy1, z1, CORBEL + "[half=top,facing=west]")
    c.set(ox1, oy1, z1, CORBEL + "[half=top,facing=east]")
    _gable_roof(c, WINCH, WINCH_TOP + 1)
    c.set(x0, WINCH_TOP + 3, mid, COURSE)
    c.set(x0, WINCH_TOP + 4, mid, FINIAL)


def _glaze(c):
    for w in windows():
        for x, z in w["cells"]:
            for y in range(w["y"][0], w["y"][1] + 1):
                c.set(x, y, z, w["glass"])


def build():
    c = Canvas()
    lowerplatform.build(c)
    _platform(c)
    _waiting_room(c)
    _winch_house(c)
    _glaze(c)
    _lightkit.glazed(c, windows(), (0, 0, 0), group="station")
    n = signs.station(c, SIGN)
    lit = sky.build(c, (0, 0, 0))   # A2's light sources go in last, when everything that glows is in place
    c.entity_counts = {"props": n, "sky": lit or 0}
    return c


def build_models():
    """The models of props/signs: the stage hangs one of them."""
    return signs.models()


def write_pack(pack_dir):
    """The repainted stone, glass and iron, and the pictures of the map's sky (the stage stands in
    the map's hour, mood.py)."""
    return list(materials.pack(pack_dir) or []) + list(sky.pack(pack_dir) or [])


# ---- the cameras ------------------------------------------------------------------------------------------
def shots():
    """The board from the head of the steps before the gable; the whole gable from the foot of the
    steps, in the default light and in the deep night; the two houses from the yard, where the
    way from the grand stair comes to the station."""
    out = []

    def shot(name, pos, look_at, time=TIME):
        out.append({"name": name, "pos": [round(float(v), 2) for v in pos],
                    "look_at": [round(float(v), 2) for v in look_at], "time": time})

    bx, by, bz = SIGN["point"]
    shot("board_near", (X0 + 2.5, FEET + S.EYE, bz + 0.6), (bx, by - 0.1, bz))
    shot("board_gable", (X0 + 0.6, FEET + S.EYE, bz + 1.6), (bx, by - 0.7, bz - 0.2))
    shot("board_gable_deep", (X0 + 0.6, FEET + S.EYE, bz + 1.6), (bx, by - 0.7, bz - 0.2), TIME_DEEP)
    shot("board_yard", (X0 - 9.5, LOW + S.EYE, bz - 0.5), (bx, by - 0.5, bz))
    return out
