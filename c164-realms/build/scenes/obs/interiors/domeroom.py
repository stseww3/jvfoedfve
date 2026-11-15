"""Work package interiors/domeroom: the great dome room (plan ART-PLAN 8, view V8).

The star piece is the great refractor on its pier, pointing through the slit at the comet. The room
dresses whatever shell stands there and never builds it: the drum and the dome's skin are main/dome
(c222), the floor, the opening round the pier and its railing are main/shell (c231), the telescope
is machines/refractor (c237), the track, rollers, chains and winch are machines/domegear (c196).

What the room adds, from the wall up:

    18..19   the wall's foot: a dado of dark wood between the feet of the wall posts
    18..22   a wall post of riveted iron under every second rib
    23       the ring beam: iron corbelled out from the wall's top, fixed to the stone
    24       the ledge on the inner leaf, left empty: the track and its rollers (machines/domegear)
    25       the dome's base ring, which the ribs stand on and the rollers carry
    26..     twenty iron ribs under the skin, one under each rib outside, up to a collar ring;
             a heavier beam along either side of the slit and a trimmer across its east end

and on the floor: the observing platform at the eyepiece, the record desk with the small red lamp,
the instrument cabinet, the sidereal clock. Light: the slit's cold sky is the base; the red lamp and
the clock's dial are the warm points (plan 3.2).

Rough model (first commit): blocks only, stand-in furniture, no display entity; build() returns 0.

build() is what the master scene calls; it places nothing until MOVED_IN is set (c231's shell and
c222's dome in the master scene, the room reviewed). Until then the room lives in its box test
scene (build/scenes/obs_int_domeroom), which calls dress().
"""
import math

from ..common import blocks as B
from ..common import skeleton as S
from ..main import _order as O

ORDER = 80                  # after the shell and the dome (60)
MOVED_IN = False

CX, CZ = S.DOME_CENTRE
FEET = S.ROOF_STAND                             # 18: the row one stands in
WALL_TOP = S.DRUM[1]                            # 23: the last row of the drum's stone
LEDGE_Y = S.DOME_SPRING                         # 24: the row on top of the inner leaf (machines/domegear)
BASE_RING_Y = LEDGE_Y + 1                       # 25
RIBS = 20                                       # one under each rib of the dome outside
RIB_DEG = 360.0 / RIBS
COLLAR = (5.0, 6.0)                             # the ring the ribs run into, as outside
SLIT_HALF = S.SLIT_W // 2                       # 2: the slit is z -2..2
SLIT_PAST = 2                                   # and runs this far east of the apex
POST_EVERY = 2                                  # a wall post under every second rib
DOOR_CLEAR = 2.5                                # nothing of the dado or the posts this near a door

IRON = B.IRON_RIVETED
WOOD = B.DARK_WOOD

# --- light (cell, level): what the room offers to the light line; the box drops them itself -------
SLIT_SKY = 9                # the cold pool under the slit, the base of the room
RED_LAMP = 6                # the small red lamp at the record desk
CLOCK_DIAL = 5              # the sidereal clock's dial


# --- where things are ---------------------------------------------------------------------------
def room():
    """The columns of the room: inside both leaves of the drum (c231's floor and the pier's opening)."""
    return O.shrink(O.shrink(O.disc(CX, CZ, S.DOME_R)))


def leaf():
    """The columns of the drum's inner leaf: the ledge the dome's base ring runs over."""
    return O.shrink(O.disc(CX, CZ, S.DOME_R)) - room()


def envelope():
    """The opening round the pier and the curb its railing stands on (main/shell)."""
    x0, z0, x1, z1 = S.PIER_ENVELOPE
    return O.box(x0 - 1, z0 - 1, x1 + 1, z1 + 1)


def rib_angles():
    """Degrees round the dome's centre (0 = east, 90 = south): a gore, not a rib, lies on each axis."""
    return [(k + 0.5) * RIB_DEG for k in range(RIBS)]


def _polar(x, z):
    return math.hypot(x - CX, z - CZ), math.degrees(math.atan2(z - CZ, x - CX)) % 360.0


def _on_meridian(x, z, angle):
    dx, dz = x - CX, z - CZ
    ux, uz = math.cos(math.radians(angle)), math.sin(math.radians(angle))
    return dx * ux + dz * uz > 0 and abs(dx * uz - dz * ux) <= 0.5


def in_slit(x, z):
    return abs(z - CZ) <= SLIT_HALF and x <= CX + SLIT_PAST


def slit_frame(x, z):
    """The columns of the beams that frame the slit: one on either side, one across its east end."""
    if abs(z - CZ) == SLIT_HALF + 1 and x <= CX + SLIT_PAST + 1:
        return True
    return x == CX + SLIT_PAST + 1 and abs(z - CZ) <= SLIT_HALF


def doors():
    return list(S.DOME_ROOM_DOORS["cells"])


def _near_door(x, z):
    return any(math.hypot(x - dx, z - dz) <= DOOR_CLEAR + 1.0 for dx, dz in doors())


def eyepiece():
    """Where the telescope's eyepiece is (x, y, z in blocks). Read from machines/refractor once its
    module says it; until then worked out from the numbers the director gave (elevation 41 degrees,
    the axes cross 5 above the pier's top, the tube runs 5 back from there)."""
    try:
        from ..machines import scope
        for name in ("eyepiece", "EYEPIECE"):
            got = getattr(scope, name, None)
            if got is not None:
                return tuple(got() if callable(got) else got)
    except ImportError:
        pass
    ax, az = S.DOME_AXIS
    elev, back, cross = math.radians(41.0), 5.0, S.PIER_TOP_Y + 5.0
    return (ax + back * math.cos(elev), cross - back * math.sin(elev), az)


# --- the dress ------------------------------------------------------------------------------------
def dress(c, origin=(0, 0, 0), lights=True):
    """Dress the dome room inside the shell that stands on the canvas. Returns the number of display
    entities placed. lights: drop the room's own light blocks (the box; in the master scene the
    light line places what offer_lights() names)."""
    ox, oy, oz = origin

    def put(x, y, z, state):
        c.set(ox + x, oy + y, oz + z, state)

    def under(x, z):
        """The row under the dome's skin over a column; None where the sky is open."""
        for y in range(LEDGE_Y, S.DOME_APEX + 4):
            if c.has(ox + x, oy + y, oz + z):
                return y - 1
        return None

    inside, ledge = room(), leaf()
    edge = inside - O.shrink(inside)
    soffit = {col: under(*col) for col in inside | ledge}

    _ring_beam(c, origin, ledge, edge)
    _vault(put, soffit, inside, ledge)
    _wall(put, edge)
    _floor(put, inside)
    if lights:
        for (x, y, z), level in offer_lights():
            if not c.has(ox + x, oy + y, oz + z):
                put(x, y, z, f"{B.LIGHT}[level={level}]")
    return 0


def _ring_beam(c, origin, ledge, edge):
    """The fixed ring beam: iron stairs hung under the wall's top row, turned towards the wall."""
    lay = O.Laying(c, None, origin, None)
    lay.mould(ledge, WALL_TOP, IRON.stairs, "top", only=edge)


def _vault(put, soffit, inside, ledge):
    """The dome's base ring, the ribs, the collar, the beams round the slit."""
    for x, z in ledge:
        if soffit[(x, z)] is not None and soffit[(x, z)] >= BASE_RING_Y and not in_slit(x, z):
            put(x, BASE_RING_Y, z, IRON.block)

    def run(cols, foot):
        """A beam under the skin along `cols` (ordered from the wall inwards): each column is filled
        up to the skin from where the one before it stopped, so the beam is one unbroken line."""
        last = None
        for col in cols:
            top = soffit.get(col)
            if top is None:
                continue
            low = foot if last is None else min(top, last + 1)
            for y in range(low, top + 1):
                put(col[0], y, col[1], IRON.block)
            last = top

    reach = inside | ledge
    for a in rib_angles():
        cols = [col for col in reach if _on_meridian(col[0], col[1], a) and _polar(*col)[0] >= COLLAR[1]
                and not in_slit(*col) and not slit_frame(*col)]
        run(sorted(cols, key=lambda col: -_polar(*col)[0]), BASE_RING_Y + 1)
    for col in inside:
        if COLLAR[0] <= _polar(*col)[0] < COLLAR[1] and not in_slit(*col) and soffit[col] is not None:
            put(col[0], soffit[col], col[1], IRON.block)
    for side in (-1, 1):
        z = CZ + side * (SLIT_HALF + 1)
        cols = sorted((col for col in reach if col[1] == z and slit_frame(*col)), key=lambda col: col[0])
        run(cols, BASE_RING_Y)
    for col in reach:
        if slit_frame(*col) and abs(col[1] - CZ) <= SLIT_HALF and soffit[col] is not None:
            put(col[0], soffit[col], col[1], IRON.block)


def _wall(put, edge):
    """Wall posts under every second rib and a dado of dark wood between them."""
    posts = set()
    for k, a in enumerate(rib_angles()):
        if k % POST_EVERY:
            continue
        col = min(edge, key=lambda e: (round(abs((_polar(*e)[1] - a + 180.0) % 360.0 - 180.0), 3), e))
        if not _near_door(*col):
            posts.add(col)
    for x, z in posts:
        for y in range(FEET, WALL_TOP):
            put(x, y, z, IRON.block)
    return posts


def _floor(put, inside):
    """Stand-ins for what stands on the floor: the observing platform at the eyepiece, the record
    desk, the instrument cabinet, the sidereal clock."""
    ex, _ey, ez = eyepiece()
    px, pz = int(math.floor(ex)) + 1, int(math.floor(ez))
    free = inside - envelope()
    for x in range(px, px + 4):
        for z in range(pz - 2, pz + 3):
            if (x, z) in free:
                rim = x in (px, px + 3) or z in (pz - 2, pz + 2)
                put(x, FEET, z, f"{(IRON if rim else B.FLOOR_WOOD).slab}[type=bottom]")
    dx, dz = DESK
    for x in (dx, dx + 1):
        put(x, FEET, dz, f"{WOOD.slab}[type=top]")
    cx, cz = CABINET
    for x in (cx, cx + 1):
        for y in (FEET, FEET + 1):
            put(x, y, cz, WOOD.block)
    kx, kz = CLOCK
    for y in (FEET, FEET + 1):
        put(kx, y, kz, WOOD.block)
    put(kx, FEET + 2, kz, B.PANELS["dial"] + "[facing=north]")


DESK = (6, 9)               # the record desk: two cells against the south wall, west cell first
CABINET = (5, -10)          # the instrument cabinet, against the north wall
CLOCK = (2, 10)             # the sidereal clock, beside the desk


def offer_lights():
    """[((x, y, z), level)] the light sources the room asks for, in scene cells."""
    dx, dz = DESK
    kx, kz = CLOCK
    return [((CX - 4, FEET + 3, CZ), SLIT_SKY),
            ((dx, FEET + 1, dz - 1), RED_LAMP),
            ((kx, FEET + 2, kz - 1), CLOCK_DIAL)]


def build(canvas, origin=(0, 0, 0)):
    if not MOVED_IN:
        return 0
    return dress(canvas, origin, lights=False)
