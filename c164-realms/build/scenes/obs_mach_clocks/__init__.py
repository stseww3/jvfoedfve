"""Test scene of machines/clock (card plan/packages/machines/clocks.md): the master clock, the tower
clock and the time ball at their places in the skeleton, among stand-ins of what they hang on.

  the hall    the clear star hall as a plain box (x 2..15, z -6..6, the ceiling block at y 14): the
              front door on the axis with the three great windows over it, dark from inside; the
              thin telescope pier at the west end with the slate step at its east foot; the side
              galleries; and where the orrery hangs, a brass rim at the lower edge of its envelope,
              a stem and a lit block for its sun. The master clock stands on the step with its
              back on the pier. The box is lit by the orrery's sun and by the clock's own hidden
              light, nothing else.
  the tower   the shaft of the time tower as one piece of masonry from the ground (in the map it
              stands on the north pavilion): on each face the recess main/tower leaves for the
              dial (three wide, y 26..28, one deep, an iron plate at its back), a belfry, a stepped
              roof and a stand-in mast (a post as thick as main/tower's rod up to y 51, a thin rod
              on top). The lit frosted window in the east face, well under the dial, is the measure
              the dial is held against: the dial has to stay the darker of the two.
  the yard    the paving the cameras stand on.
  the mast    the radio mast (machines/mast) on a plain seat north of the tower, as soon as that
              package is in the tree: from V1 its red lamp stands close to the ball and the comet,
              and the ball's colour is chosen with the lamp in the picture. Until then: nothing.
  the pair    west of the hall, out of sight of every other shot: the two colours of the time ball
              side by side on two short masts (A0 picks one).

The ball on the tower is BALL. The twin scene obs_mach_clocks_b hangs the other colour there and
repeats the shots of the tower, picture by picture.

    python -m scenes.obs_mach_clocks        # writes shots.json from the numbers below
"""
import math

from artkit.blocks import st
from artkit.canvas import Canvas

from scenes.obs import materials, sky
from scenes.obs.common import blocks as B
from scenes.obs.common import skeleton as S
from scenes.obs.machines import clock

try:
    from scenes.obs.machines import mast as radiomast       # c239: its red lamp stands by the ball in V1
except ImportError:
    radiomast = None
try:
    from scenes.obs.site import mastbase                    # c229: the stone foot of that mast
except ImportError:
    mastbase = None

BIOME = "obs_blue"
BIOME_MARGIN = 80               # the look has to reach the far cameras, 42 blocks east of the paving
BIOME_MARGIN_Y = 160
TIME = 14000                    # the blue hour, the default look
BALL = clock.BALL               # the colour of the ball on the tower in this scene

LIGHT_STONE = B.ASHLAR_FINE.block
DARK_STONE = B.SLATE_SMOOTH.block
WALL = B.ASHLAR_FINE.block
QUOIN = B.ASHLAR_ROUGH.block
COURSE = B.ASHLAR_PANEL.block
SLATE = B.SLATE_BRICK.block
IRON = B.IRON_RIVETED.block
GRATE = B.IRON_GRATE
RAIL = B.IRON_BARS + "[east=true,west=true]"
ROOF = B.VERDIGRIS_CUT.block
POST = B.SLATE_SMOOTH.wall                  # a post 8 pixels thick: the mast the ball rides on
ROD = B.IRON_ROD + "[facing=up]"            # 4 pixels thick: the top of the mast

FLOOR_Y = S.PAVING_Y                        # -1, the floor block; feet at y 0

# --- the hall -----------------------------------------------------------------------------------
IX = (S.ROOM_X[0], S.east_wall_x(9) - 2)    # 2..15: the clear hall in x, up to the east wall
IZ = S.STAR_HALL_Z                          # -6..6
WX = (IX[0] - 1, IX[1] + 1)                 # the walls: x 1 and 16
WZ = (IZ[0] - 1, IZ[1] + 1)                 # z -7 and 7
CEIL_Y = S.STAR_HALL_CEIL                   # 14, the ceiling block
DOOR_Y = (0, 5)                             # the entrance, three wide
JOINT_X = (S.PIER_SHAFT[0] - 1, int(S.MOTHER_CLOCK["back_x"]) + 1)      # 2..7: the grating ring round pier and step
SUN_LIGHT = 12                              # the orrery's sun, the brightest thing in the hall (lights)
V7 = S.V7                                   # the star hall from outside the door (A0, 11-15)
# The arrival view as A0 lifted it on 11-15: the dial, the ball and the comet stand one over the other
# in it, and the colour of the ball is picked on it.
V1 = S.V1

# --- the tower ----------------------------------------------------------------------------------
TX, TZ = S.CLOCK_SHAFT_X, S.CLOCK_SHAFT_Z                   # 10..16, -33..-27
TCX, TCZ = (TX[0] + TX[1]) // 2, (TZ[0] + TZ[1]) // 2       # the axis column (13, -30)
NICHE = (26, 28)                            # the rows of the dial's recess: three wide, one block deep
NICHE_BACK = B.IRON_PLATE                   # its back, as main/tower builds it (c223, 11-15)
BELFRY = (S.CLOCK_SHAFT_TOP + 1, 36)        # 32..36
MAST_THICK = 50                             # the last cell of the post: main/tower's rod ends at y 51
WINDOW_LIGHT = 10                           # behind the frosted window, as the front has it

# --- the pair -----------------------------------------------------------------------------------
PAIR = {"copper": (-8.5, 2.75, 3.5), "red": (-4.5, 2.75, 3.5)}      # the centres of the two balls


def _wall(a, y):
    """One wall cell of the hall: a pilaster strip every fourth column (so no face runs flat over
    5x5), a string course at the gallery floor, plain ashlar between."""
    if a % 4 == 0:
        return QUOIN
    return COURSE if y == S.STRING else WALL


def _floor(x, y, z):
    """The hall floor (A0, 11-15): a pale band three wide along the axis between two slate lines, a
    chequer of two-block squares on either side. Round the foot of the pier and of the clock's step
    runs the iron grating that covers the gap between the pier and the building; inside that ring
    the floor is the pier's own stone (main/shell, 11-15: the ring is x 2..7, z -2..2)."""
    d = abs(z)
    if JOINT_X[0] <= x <= JOINT_X[1] and d <= 2:
        return GRATE if x in JOINT_X or d == 2 else SLATE
    if d <= 1:
        return LIGHT_STONE
    if d == 2:
        return DARK_STONE
    return LIGHT_STONE if ((x - IX[0]) // 2 + (d - 3) // 2) % 2 == 0 else DARK_STONE


def _ground(c):
    c.box(WX[1] + 1, FLOOR_Y, TZ[0] - 3, 46, FLOOR_Y, WZ[1], DARK_STONE)        # the court: x 17..46
    c.box(TX[0] - 2, FLOOR_Y, TZ[0] - 3, WX[1], FLOOR_Y, WZ[0] - 1, DARK_STONE)  # under and round the tower
    c.box(-12, FLOOR_Y, -1, WX[0] - 1, FLOOR_Y, 12, DARK_STONE)                  # under the pair


def _hall(c):
    x0, x1 = IX
    z0, z1 = IZ
    wx0, wx1 = WX
    wz0, wz1 = WZ
    c.box(wx0, FLOOR_Y, wz0, wx1, FLOOR_Y, wz1, _floor)
    c.box(JOINT_X[0], FLOOR_Y - 1, -2, JOINT_X[1], FLOOR_Y - 1, 2, DARK_STONE)      # the pit under the grating
    c.box(wx0, CEIL_Y, wz0, wx1, CEIL_Y, wz1, COURSE)
    for y in range(0, CEIL_Y):
        for x in range(wx0, wx1 + 1):
            c.set(x, y, wz0, _wall(x, y))
            c.set(x, y, wz1, _wall(x, y))
        for z in range(wz0, wz1 + 1):
            c.set(wx0, y, z, _wall(z, y))
            c.set(wx1, y, z, _wall(z, y))

    # the east front: the entrance on the axis, the three great windows over it
    c.carve(wx1, DOOR_Y[0], -1, wx1, DOOR_Y[1], 1)
    for zc in (-4, 0, 4):
        c.box(wx1, S.WINDOW[0], zc - 1, wx1, S.WINDOW[1], zc + 1, B.WINDOW_DARK.block)

    # the telescope pier, and at its east foot the step the clock stands on (interiors/starhall)
    px0, pz0, px1, pz1 = S.PIER_SHAFT
    c.box(px0, 0, pz0, px1, CEIL_Y - 1, pz1, WALL)
    c.box(px0, 0, pz0, px1, 1, pz1, SLATE)
    step = int(S.MOTHER_CLOCK["back_x"])
    c.box(step, 0, pz0, step, int(S.MOTHER_CLOCK["y"][0]) - 1, pz1, SLATE)

    # the side galleries, a rail on the edge of the well
    for g0, g1, rail in ((z0, -4, -4), (4, z1, 4)):
        c.box(x0, S.STRING, g0, S.ROOM_X[1], S.STRING, g1, IRON)
        c.box(x0, S.STAND, rail, S.ROOM_X[1], S.STAND, rail, RAIL)


def _orrery(c):
    """Where the orrery hangs, for the views that hold the clock and it together: a brass rim at
    the lower edge of its envelope, the stem up to the ceiling, a lit block where its sun is and
    under that the light the sun gives the hall."""
    cx, cz = (int(math.floor(v)) for v in S.ORRERY_CENTRE)
    low = S.ORRERY_BODY_Y[0]
    y = int(math.floor(low))
    rim = st(B.BRASS_PLATE.slab, type="top" if low - y >= 0.5 else "bottom")
    reach = int(math.ceil(S.ORRERY_R))
    for x in range(cx - reach, cx + reach + 1):
        for z in range(cz - reach, cz + reach + 1):
            if S.ORRERY_R - 1.0 < math.hypot(x - cx, z - cz) <= S.ORRERY_R + 0.25:
                c.set(x, y, z, rim)
    sun = int(math.floor(S.ORRERY_RING_Y))
    for up in range(sun + 1, CEIL_Y):
        c.set(cx, up, cz, st(B.BRASS_COLUMN, axis="y"))
    c.set(cx, sun, cz, B.WINDOW_LIT.block)
    c.set(cx, sun - 1, cz, st(B.LIGHT, level=SUN_LIGHT), keep=True)


def _shaft(x, y, z):
    """One cell of the tower's shaft: a slate course on the ground, a rusticated base, dressed
    stone between rusticated corners (the plain strip is five wide), three courses."""
    if y == 0:
        return SLATE
    if y in (S.STRING, 23, S.CLOCK_SHAFT_TOP):
        return COURSE
    if y <= 5 or (x in TX and z in TZ):
        return QUOIN
    return WALL


def _belfry(x, y, z):
    return QUOIN if x in TX and z in TZ else IRON


def _tower(c):
    x0, x1 = TX
    z0, z1 = TZ
    c.box(x0, 0, z0, x1, S.CLOCK_SHAFT_TOP, z1, _shaft)

    # the recess of each dial: three by three, one block deep, the darkest thing on the shaft
    for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        for a in (-1, 0, 1):
            for y in range(NICHE[0], NICHE[1] + 1):
                if dx:
                    x = x1 if dx > 0 else x0
                    c.clear(x, y, TCZ + a)
                    c.set(x - dx, y, TCZ + a, NICHE_BACK)
                else:
                    z = z1 if dz > 0 else z0
                    c.clear(TCX + a, y, z)
                    c.set(TCX + a, y, z - dz, NICHE_BACK)

    # the measure: a lit frosted window in the east face, made as the front makes its great windows
    # (the opening, the glass one block in, a free cell behind it that holds the two hidden lights)
    glass, room = x1 - 1, x1 - 2
    c.carve(x1, S.WINDOW[0], TCZ - 1, x1, S.WINDOW[1], TCZ + 1)
    c.box(glass, S.WINDOW[0], TCZ - 1, glass, S.WINDOW[1], TCZ + 1, B.WINDOW_FROSTED.block)
    c.carve(room, S.WINDOW[0], TCZ - 1, room, S.WINDOW[1], TCZ + 1)
    for y in (S.WINDOW[0] + 1, S.WINDOW[1] - 1):
        c.set(room, y, TCZ, st(B.LIGHT, level=WINDOW_LIGHT))

    # the belfry, its cornice, the stepped roof up to CLOCK_TOP
    c.box(x0, BELFRY[0], z0, x1, BELFRY[1], z1, _belfry)
    c.box(x0, BELFRY[1] + 1, z0, x1, BELFRY[1] + 1, z1, COURSE)
    top = S.CLOCK_TOP
    c.box(x0 + 1, top - 3, z0 + 1, x1 - 1, top - 2, z1 - 1, ROOF)
    c.box(x0 + 2, top - 1, z0 + 2, x1 - 2, top - 1, z1 - 2, ROOF)
    c.set(TCX, top, TCZ, ROOF)

    # the mast: a post where main/tower has its rod (a model 7 pixels thick, y 42.6..51), a thin
    # rod above it for what stands on the top there
    for y in range(top + 1, S.CLOCK_BALL_MAST):
        c.set(TCX, y, TCZ, POST if y <= MAST_THICK else ROD)


def _radiomast(c):
    """The radio mast north of the tower, as soon as machines/mast is in the tree: from V1 its red
    lamp stands close to the time ball and the comet, and the colour of the ball is chosen with the
    lamp in the picture (A0, cr2). Its stone foot is site/mastbase when that is in the tree; until
    then a plain seat, four anchor blocks and a post. Nothing joins it to the tower: the mast hangs
    no aerial (A0, 11-16). Returns the entity count."""
    if radiomast is None:
        return 0
    x0, z0, x1, _z1 = S.MAST_PAD["box"]
    c.box(x0, FLOOR_Y, z0, x1, FLOOR_Y, TZ[0] - 4, DARK_STONE)
    if mastbase is not None:
        mastbase.build(c, (0, 0, 0))
    else:
        fx, fz = S.RADIO_MAST["foot"]
        c.box(fx - 1, 0, fz - 1, fx + 1, int(math.ceil(radiomast.BASE_Y)) - 1, fz + 1, SLATE)
        for ax, ay, az in radiomast.GUY_ANCHORS:
            x, z = int(math.floor(ax)), int(math.floor(az))
            c.box(x, 0, z, x, int(math.ceil(ay)) - 1, z, SLATE)
        px, py, pz = radiomast.LEAD_POST
        x, z = int(math.floor(px)), int(math.floor(pz))
        c.box(x, 0, z, x, int(math.ceil(py)) - 1, z, ROD)
    return radiomast.build(c, (0, 0, 0))


def _pair(c):
    """The two colours of the ball on two short masts; returns the entity count."""
    n = 0
    for colour, (x, y, z) in PAIR.items():
        cx, cz = int(math.floor(x)), int(math.floor(z))
        c.set(cx, 0, cz, POST)
        for up in range(1, 5):
            c.set(cx, up, cz, ROD)
        n += clock.ball(c, (x, y, z), colour)
    return n


def build(ball=None):
    c = Canvas()
    _ground(c)
    _hall(c)
    _orrery(c)
    _tower(c)
    if ball in (None, clock.BALL):
        n = clock.build(c, (0, 0, 0))               # the package as the master scene calls it
    else:
        n = clock.master(c) + clock.tower(c, colour=ball)
    n += _pair(c)
    n += _radiomast(c)
    sky.build(c, (0, 0, 0))                         # the sky line's light sources go in last
    c.entity_counts = {"machines": n}
    return c


def write_pack(pack_dir):
    """The repainted stone, iron, glass and brass the clocks are judged against, and the sky's
    pictures: the comet stands over the mast in the far views."""
    return list(sky.pack(pack_dir) or []) + list(materials.pack(pack_dir) or [])


def shots():
    """The cameras. Hall: three blocks from the clock, close on the dial, close on the trunk, V7
    (the skeleton's), from the front door 30 blocks away, down from the north gallery. Tower: V1
    (the skeleton's), straight in front of the east dial from the same distance, V5 from the court,
    steeply up from the foot, three on a dial, one on the top. And the pair of balls."""
    out = []

    def shot(name, pos, look_at):
        out.append({"name": name, "pos": [round(v, 2) for v in pos], "look_at": [round(v, 2) for v in look_at],
                    "time": TIME})

    x, y, z = clock.MASTER_AT                       # the middle of the case's foot, on the pier
    front = x + 0.75                                # the front of the case
    shot("master_close", (front + 2.8, y + 1.9, z + 1.1), (x + 0.4, y + 2.0, z))
    shot("master_dial", (front + 1.25, y + 3.4, z + 0.4), (x + 0.5, y + 3.15, z))
    shot("master_trunk", (front + 1.55, y + 1.6, z - 0.8), (x + 0.4, y + 1.6, z))
    shot("v7", V7["pos"], V7["look_at"])
    shot("master_door", (front + 30.0, S.EYE, z), (front, y + 2.0, z))
    shot("master_gallery", (9.5, S.STAND + S.EYE, -3.2), (x + 0.4, y + 2.2, z))

    ax, az = clock.BALL_AXIS                        # the tower's axis
    east = S.CLOCK_SHAFT_X[1] + 1.0                 # its east face
    dial = clock.DIAL_Y
    v1 = V1
    shot("v1_tower", v1["pos"], v1["look_at"])
    shot("tower_far", (v1["pos"][0], v1["pos"][1], az), (east, dial, az))
    shot("v5_up", (44.5, 1.7, -22.5), (ax, 33.0, az))
    shot("tower_foot", (east + 22.0, 1.7, az), (east, dial, az))
    shot("dial_close", (east + 13.0, 22.0, az + 6.0), (east, dial, az))
    shot("dial_front", (east + 6.0, dial, az), (east, dial, az))
    shot("dial_south", (east + 10.0, 25.0, az + 13.5), (ax + 1.5, dial, az + 2.0))
    shot("top_close", (east + 14.0, 45.0, az + 11.0), (ax, clock.BALL_HALF_Y - 1.0, az))

    (cx, cy, cz), (rx, _ry, _rz) = PAIR["copper"], PAIR["red"]
    shot("balls_pair", ((cx + rx) / 2.0, S.EYE, cz + 8.0), ((cx + rx) / 2.0, cy + 0.15, cz))
    return out
