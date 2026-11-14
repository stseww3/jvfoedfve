"""site/outbuildings: the four small ancillary buildings on the hilltop (plan/ART-PLAN.md 4, 5.3,
card plan/packages/site/outbuildings.md). Shells and platforms only -- blocks, no display entities:

  - the meridian hut: a low stone hut over the brass meridian (skeleton MERIDIAN_HUT, centre (35,-30),
    9x9), its slate roof split north-south by an open slit on the meridian so the transit instrument
    (A5) can sweep the sky, and a slit door on the same line facing south. It sits on the V1 sight
    line to the clock-tower foot, so it is kept to seven blocks tall and never masks the front.
  - the water tower: a riveted-iron frame on four braced legs carrying a riveted tank, with a caged
    ladder and a maintenance deck, on the north-west shoulder (S.WATER_TOWER).
  - the weather station: a small platform with a louvred instrument shelter (a Stevenson screen), a
    wind pole and a rain gauge, on the north slope (S.WEATHER_STATION).
  - the south lookout: a stone terrace that projects south over the cloud sea with the site's rail and
    a spot left for a tripod telescope; V11 (the arrival seen in reverse) is taken from here.

The instruments themselves -- the meridian circle, the anemometer and vane, the rain-gauge works, the
tripod telescope and the benches -- belong to the machines and props lines; this card leaves the
shells, the sockets and the clear spots for them. The terrain card (c221) lays each shelf's flat rock;
these shells stand on the foot levels it gives (S.*["feet"], the stone block one below) and carry a
short footing into the slope so they do not float before it is merged. Terrace edges use c221's one
site-wide rail (site/_kit.rail); the upper-terrace north edge and the mast-pad ring are his.
"""
from artkit.canvas import Mix

from . import _kit as K
from ..common import blocks as B
from ..common import skeleton as S

ORDER = 70      # after the terrain (10) and the court paving (60); the shells go on the finished ground

# --- materials (occupancy-table roles only) -------------------------------------------------------
STONE = B.ASHLAR_FINE.block             # dressed grey-white walls, like the main building family
QUOIN = B.ASHLAR_ROUGH.block            # rusticated corners
EMBLEM = B.ASHLAR_EMBLEM                 # lintels and heads
PLINTH = B.SLATE_BRICK.block            # dark plinths, footings, retaining
ROOF = B.SLATE_TILE.block               # dark slate roofs
ROOF_SLAB = B.SLATE_TILE.slab
BRASS = B.BRASS_INLAY                   # the brass meridian line
IRON = B.IRON_RIVETED.block            # riveted plate: frames, decks, bands
IRON_SLAB = B.IRON_RIVETED.slab
IRON_STAIR = B.IRON_RIVETED.stairs
PLATE = B.IRON_PLATE                    # plain plate: the tank and casings
GRATE = B.IRON_GRATE                    # open grating: decks and walkways
BARS = B.IRON_BARS                      # iron rail (on iron structures; stone edges use K.rail)
HATCH = B.IRON_HATCH                    # hatch / louvre
ROD = B.IRON_ROD                        # thin rod: finials, the wind-pole head

# a dark broken mix for footings so no retaining face reads flat (plan 6 flatwall)
FOOTING = Mix({B.SLATE_BRICK.block: 10, B.SLATE_TILE.block: 3, B.SLATE_SMOOTH.block: 3}, seed=2292)
STEP = B.SLATE_BRICK.stairs             # the steps down to the shelves: the terrace's small dark stone

# The ways down from the upper terrace, agreed with the terrain card (c221 #21052): the terrain
# leaves its railing open in these cells and stands a gate pier either side; the steps are here.
LOOKOUT_WAY = (44, 46)      # x, through the terrace's south edge, on the lookout's middle line
WEATHER_WAY = (2, 4)        # x, through the north edge
TOWER_WAY = (-33, -31)      # z, through the west edge


# --- small helpers --------------------------------------------------------------------------------
def _put(c, o, x, y, z, state):
    c.set(o[0] + x, o[1] + y, o[2] + z, state)


def _fill(c, o, x0, y0, z0, x1, y1, z1, state, keep=False):
    for x in range(min(x0, x1), max(x0, x1) + 1):
        for y in range(min(y0, y1), max(y0, y1) + 1):
            for z in range(min(z0, z1), max(z0, z1) + 1):
                c.set(o[0] + x, o[1] + y, o[2] + z, state, keep=keep)


def _ring(x0, z0, x1, z1):
    """The perimeter cells of a rectangle, each once."""
    cells = []
    for x in range(x0, x1 + 1):
        cells.append((x, z0))
        if z1 != z0:
            cells.append((x, z1))
    for z in range(z0 + 1, z1):
        cells.append((x0, z))
        if x1 != x0:
            cells.append((x1, z))
    return cells


def _outward(x, z, x0, z0, x1, z1):
    """The horizontal face a perimeter cell turns outward (for a louvre panel); corners pick west/east."""
    if x == x0:
        return "west"
    if x == x1:
        return "east"
    if z == z0:
        return "north"
    return "south"


def _brace(c, o, ax, az, bx, bz, y0, y1, axis):
    """A diagonal riveted-iron brace climbing from one leg foot to the next leg higher up, on a face."""
    n = abs((bx - ax) if axis == "x" else (bz - az))
    if n == 0:
        return
    for i in range(1, n):
        y = y0 + round((y1 - y0) * i / n)
        if axis == "x":
            facing = "east" if bx > ax else "west"
            _put(c, o, ax + (1 if bx > ax else -1) * i, y, az, IRON_STAIR + f"[facing={facing},half=bottom]")
        else:
            facing = "south" if bz > az else "north"
            _put(c, o, ax, y, az + (1 if bz > az else -1) * i, IRON_STAIR + f"[facing={facing},half=bottom]")


def _flight(c, o, rows, drop, facing):
    """A way down over `rows` (each the cells across the way, the first row next to the terrace):
    `drop` stair blocks spread evenly along it, level steps between them. The first stair lies in
    the terrace's paving course. Every step brings two blocks of footing (into air only) and clears
    its own headroom, so the way holds whatever the slope under it is."""
    n = len(rows)
    at = {int(round(i * (n - 1) / float(max(1, drop - 1)))) for i in range(drop)}
    y = S.PAVING_Y
    for i, row in enumerate(rows):
        for x, z in row:
            _put(c, o, x, y, z, STEP + f"[facing={facing},half=bottom]" if i in at else PLINTH)
            for d in (1, 2):
                c.set(o[0] + x, o[1] + y - d, o[2] + z, PLINTH, keep=True)
            for d in (1, 2, 3):
                c.clear(o[0] + x, o[1] + y + d, o[2] + z)
        if i in at:
            y -= 1


def _ways_down(c, o):
    tx0, tz0, tx1, tz1 = S.UPPER_TERRACE
    lz0 = S.SOUTH_LOOKOUT["box"][1]
    rows = [[(x, z) for x in range(LOOKOUT_WAY[0], LOOKOUT_WAY[1] + 1)] for z in range(tz1 + 1, lz0)]
    _flight(c, o, rows, S.GROUND - S.SOUTH_LOOKOUT["feet"], "north")      # a step, a landing, five times
    wz1 = S.WEATHER_STATION["box"][3]
    rows = [[(x, z) for x in range(WEATHER_WAY[0], WEATHER_WAY[1] + 1)] for z in range(tz0 - 1, wz1, -1)]
    _flight(c, o, rows, S.GROUND - S.WEATHER_STATION["feet"], "south")    # a straight flight of four
    wx1 = S.WATER_TOWER["box"][2]
    rows = [[(x, z) for z in range(TOWER_WAY[0], TOWER_WAY[1] + 1)] for x in range(tx0 - 1, wx1, -1)]
    _flight(c, o, rows, S.GROUND - S.WATER_TOWER["feet"], "east")         # two steps


# --- the meridian hut (skeleton MERIDIAN_HUT) -----------------------------------------------------
def _meridian_hut(c, o):
    cx, cz = S.MERIDIAN_HUT["centre"]
    n = S.MERIDIAN_HUT["size"]
    h = n // 2
    x0, x1 = cx - h, cx + h                  # 31..39
    z0, z1 = cz - h, cz + h                  # -34..-26
    dx, dz = S.MERIDIAN_HUT["door"]          # (35, -26): the slit door, south wall, on the meridian
    mx = S.MERIDIAN_X                        # 35
    floor, on = S.PAVING_Y, S.GROUND         # -1 the paving block, 0 the carpet / standing level
    wall_top = 4                             # walls rise y1..4 on a y0 plinth (seven blocks tall in all)

    # interior floor: the terrace's own stones, the meridian column in the middle tone, brass on top
    for x in range(x0 + 1, x1):
        for z in range(z0 + 1, z1):
            _put(c, o, x, floor, z, K.STRIP if abs(x - mx) <= 1 else K.FIELD)
    _put(c, o, dx, floor, dz, K.STRIP)       # the door threshold
    for z in range(z0 + 1, z1 + 1):          # the brass meridian, running out through the door
        _put(c, o, mx, on, z, BRASS)

    # plinth and dressed walls, rusticated quoins at the corners, the slit door open on the meridian
    corners = {(x0, z0), (x1, z0), (x0, z1), (x1, z1)}
    for x, z in _ring(x0, z0, x1, z1):
        if (x, z) == (dx, dz):
            continue
        _put(c, o, x, 0, z, PLINTH)
        for y in range(1, wall_top + 1):
            _put(c, o, x, y, z, QUOIN if (x, z) in corners else STONE)
    for wx in (x0, x1):                      # a tall slit window on the east and west walls
        _put(c, o, wx, 2, cz, B.WINDOW_DARK.pane)
        _put(c, o, wx, 3, cz, B.WINDOW_DARK.pane)
    _put(c, o, dx - 1, wall_top, dz, EMBLEM)  # the door head
    _put(c, o, dx + 1, wall_top, dz, EMBLEM)

    # a low slate roof split by the open meridian slit, with two folded-up iron shutters flanking it
    roof_y = wall_top + 1                     # 5
    for x in range(x0, x1 + 1):
        for z in range(z0, z1 + 1):
            if x == mx:
                continue                      # the slit stays open along the meridian
            _put(c, o, x, roof_y, z, ROOF_SLAB + "[type=top]")
    for z in range(z0, z1 + 1):               # a full ridge course either side of the slit
        _put(c, o, mx - 1, roof_y, z, ROOF)
        _put(c, o, mx + 1, roof_y, z, ROOF)
    ridge_y = roof_y + 1                      # 6, the top of the hut
    for z in range(z0 + 1, z1):               # the opened iron roof shutters, standing up by the slit
        _put(c, o, mx - 1, ridge_y, z, HATCH + "[facing=east,half=bottom,open=true]")
        _put(c, o, mx + 1, ridge_y, z, HATCH + "[facing=west,half=bottom,open=true]")


# --- the water tower (S.WATER_TOWER, north-west shoulder) -----------------------------------------
def _water_tower(c, o):
    x0, z0, x1, z1 = S.WATER_TOWER["box"]     # -21,-35,-13,-27
    foot = S.WATER_TOWER["feet"]              # -2, where the legs stand (the shelf rock is one below)
    legs_x = (x0 + 2, x1 - 2)                 # -19, -15
    legs_z = (z0 + 2, z1 - 2)                 # -33, -29
    deck_y = foot + 10                        # 8, the maintenance deck under the tank
    tank_lo, tank_hi = deck_y + 1, deck_y + 5  # 9..13 (the tank top stays below the cornice, 15)

    # until the terrain card's shelf is merged the shelf is a flat slab laid only where there is
    # nothing yet; the site's rail on the three sides over the drop, the uphill (east) side open
    _fill(c, o, x0, foot - 1, z0, x1, foot - 1, z1, FOOTING, keep=True)
    _fill(c, o, x0, foot - 2, z0, x1, foot - 3, z1, PLINTH, keep=True)
    edge = [(x, z) for x, z in _ring(x0, z0, x1, z1) if not (x == x1 and z0 < z < z1)]
    piers = {(x, bz) for bz in (z0, z1) for x in K.spaced([x0, x1])} | {(x0, z) for z in K.spaced([z0, z1])}
    K.rail(c, o, edge, piers, y=foot, kerb=True)

    # four riveted legs on stone footings, carried a little into the slope so they do not float
    for lx in legs_x:
        for lz in legs_z:
            _put(c, o, lx, foot - 1, lz, PLINTH)
            _put(c, o, lx, foot - 2, lz, PLINTH)
            _fill(c, o, lx, foot, lz, lx, deck_y, lz, IRON)
    # girts round the frame and a diagonal brace on each face of the lower panel
    for gy in (foot + 3, foot + 7, deck_y):
        _fill(c, o, legs_x[0], gy, legs_z[0], legs_x[1], gy, legs_z[0], IRON)
        _fill(c, o, legs_x[0], gy, legs_z[1], legs_x[1], gy, legs_z[1], IRON)
        _fill(c, o, legs_x[0], gy, legs_z[0], legs_x[0], gy, legs_z[1], IRON)
        _fill(c, o, legs_x[1], gy, legs_z[0], legs_x[1], gy, legs_z[1], IRON)
    _brace(c, o, legs_x[0], legs_z[0], legs_x[1], legs_z[0], foot + 1, foot + 3, axis="x")
    _brace(c, o, legs_x[0], legs_z[1], legs_x[1], legs_z[1], foot + 1, foot + 3, axis="x")
    _brace(c, o, legs_x[0], legs_z[0], legs_x[0], legs_z[1], foot + 1, foot + 3, axis="z")
    _brace(c, o, legs_x[1], legs_z[0], legs_x[1], legs_z[1], foot + 1, foot + 3, axis="z")

    # the maintenance deck with an iron rail, the tank standing in the middle
    tx0, tz0, tx1, tz1 = x0 + 1, z0 + 1, x1 - 1, z1 - 1
    _fill(c, o, tx0 - 1, deck_y, tz0 - 1, tx1 + 1, deck_y, tz1 + 1, GRATE, keep=True)
    for x, z in _ring(tx0 - 1, tz0 - 1, tx1 + 1, tz1 + 1):
        _put(c, o, x, deck_y + 1, z, BARS)

    # the riveted tank: a plate drum with chamfered corners and a band top and bottom, a vent finial
    for y in range(tank_lo, tank_hi + 1):
        band = y in (tank_lo, tank_hi)
        for x, z in _ring(tx0, tz0, tx1, tz1):
            _put(c, o, x, y, z, IRON if band else PLATE)
    for cx_, cz_ in ((tx0, tz0), (tx1, tz0), (tx0, tz1), (tx1, tz1)):
        for y in range(tank_lo, tank_hi + 1):
            c.clear(o[0] + cx_, o[1] + y, o[2] + cz_)
    _fill(c, o, tx0, tank_hi, tz0, tx1, tank_hi, tz1, PLATE)
    _put(c, o, (tx0 + tx1) // 2, tank_hi + 1, (tz0 + tz1) // 2, ROD + "[facing=up]")

    # a caged ladder up the south-east leg to the deck
    lxx, lzz = legs_x[1], legs_z[1]
    for y in range(foot, deck_y + 1):
        _put(c, o, lxx + 1, y, lzz, BARS)


# --- the weather station (S.WEATHER_STATION, north slope) -----------------------------------------
def _weather_station(c, o):
    x0, z0, x1, z1 = S.WEATHER_STATION["box"]  # -2,-49,8,-43
    foot = S.WEATHER_STATION["feet"]           # -4
    pave = foot - 1                            # -5, the paving block; feet stand at foot

    # a small dressed platform footed a little into the slope; the site's rail on the three sides
    # over the drop (a fenced instrument enclosure), the uphill (south) side open to the steps
    _fill(c, o, x0, pave, z0, x1, pave, z1, FOOTING)
    _fill(c, o, x0, pave - 1, z0, x1, pave - 3, z1, PLINTH, keep=True)
    edge = [(x, z) for x, z in _ring(x0, z0, x1, z1) if not (z == z1 and x0 < x < x1)]
    piers = {(x, z0) for x in K.spaced([x0, x1])} | {(bx, z) for bx in (x0, x1) for z in K.spaced([z0, z1])}
    K.rail(c, o, edge, piers, y=foot, kerb=True)

    # the louvred instrument shelter (a Stevenson screen): an iron box on short legs, a louvre on each
    # face, open inside for the instrument (A5/A6); a plate roof with a small eave
    bx0, bz0, bx1, bz1 = x0 + 1, z0 + 2, x0 + 3, z0 + 4      # a 3x3 box at the west end
    for x, z in ((bx0, bz0), (bx1, bz0), (bx0, bz1), (bx1, bz1)):
        _put(c, o, x, foot, z, IRON)                        # short legs lift it off the platform
    for x, z in _ring(bx0, bz0, bx1, bz1):
        for y in (foot + 1, foot + 2, foot + 3):
            _put(c, o, x, y, z, HATCH + f"[facing={_outward(x, z, bx0, bz0, bx1, bz1)},half=bottom,open=false]")
    _fill(c, o, bx0 - 1, foot + 4, bz0 - 1, bx1 + 1, foot + 4, bz1 + 1, PLATE)   # the overhanging roof

    # the wind pole: a riveted stand with a thin rod head and a stub cross-arm (anemometer/vane: A5)
    wx, wz = x1 - 2, z0 + 3
    _fill(c, o, wx, foot, wz, wx, foot + 2, wz, IRON)
    _fill(c, o, wx, foot + 3, wz, wx, foot + 6, wz, ROD + "[facing=up]")
    _put(c, o, wx - 1, foot + 6, wz, IRON_SLAB)
    _put(c, o, wx + 1, foot + 6, wz, IRON_SLAB)

    # the rain gauge: a short plate cylinder with an open mouth
    gx, gz = x1 - 2, z1 - 1
    _fill(c, o, gx, foot, gz, gx, foot + 1, gz, PLATE)
    _put(c, o, gx, foot + 2, gz, IRON)


# --- the south lookout (S.SOUTH_LOOKOUT, south ridge; V11) ----------------------------------------
def _south_lookout(c, o):
    x0, z0, x1, z1 = S.SOUTH_LOOKOUT["box"]   # 40,48,50,56
    foot = S.SOUTH_LOOKOUT["feet"]            # -5, where a person stands (V11); the deck block is one below
    pave = foot - 1                           # -6, the floor block
    split = z0 + 4                            # z52: a stone terrace to the north, an iron deck projecting south

    # the stone half joins the ridge; a dressed floor on a buttressed plinth carried into the slope
    _fill(c, o, x0, pave, z0, x1, pave, split, FOOTING)
    _fill(c, o, x0, pave - 1, z0, x1, pave - 4, split, PLINTH, keep=True)
    for z in range(z0, split + 1):            # buttresses on the outer east and west faces
        for bx in (x0, x1):
            if (z - z0) % 3 == 0:
                _fill(c, o, bx, pave - 1, z, bx, pave - 5, z, PLINTH)

    # the iron half: an open grate deck projecting south over the cloud, on riveted knee brackets
    _fill(c, o, x0, pave, split + 1, x1, pave, z1, GRATE)
    for x in range(x0, x1 + 1):              # brackets under the far (south) edge
        _put(c, o, x, pave - 1, z1, IRON_STAIR + "[facing=north,half=top]")
    for z in range(split + 1, z1 + 1):       # brackets under the east and west edges
        for bx in (x0, x1):
            _put(c, o, bx, pave - 1, z, IRON_STAIR + ("[facing=east,half=top]" if bx == x0 else "[facing=west,half=top]"))

    # the site's rail round the whole edge (the ridge that leads here is three wide, so the north
    # edge hangs free too); the way in is left open, a gate pier either side of it in line with the
    # terrain's gate posts on the upper terrace. The north corners turn in bars, not piers, so no
    # two piers stand closer than the beat.
    wx0, wx1 = LOOKOUT_WAY
    edge = [(x, z) for x, z in _ring(x0, z0, x1, z1) if not (z == z0 and wx0 <= x <= wx1)]
    piers = {(wx0 - 1, z0), (wx1 + 1, z0)}
    piers |= {(x, z1) for x in K.spaced([x0, x1])}
    piers |= {(bx, z) for bx in (x0, x1) for z in K.spaced([z0, z1])[1:]}
    K.rail(c, o, edge, piers, y=foot, kerb=True)

    # the tripod telescope spot (A5/A6): a mounting ring on the south edge, the socket left open
    tx, tz = (x0 + x1) // 2, z1 - 2
    for dx, dz in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        _put(c, o, tx + dx, pave, tz + dz, IRON)


def build(canvas, origin=(0, 0, 0)):
    _meridian_hut(canvas, origin)
    _water_tower(canvas, origin)
    _weather_station(canvas, origin)
    _south_lookout(canvas, origin)
    _ways_down(canvas, origin)
    return 0
