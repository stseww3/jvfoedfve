"""site/outbuildings: the four small ancillary buildings on the hilltop (plan/ART-PLAN.md 4, 5.3,
card plan/packages/site/outbuildings.md). Shells and platforms only -- blocks, no display entities:

  - the meridian hut: a low stone hut over the brass meridian (skeleton MERIDIAN_HUT, centre (35,-30),
    9x9). The meridian cuts it in two: an open slot one block wide runs through the south gable (the
    door), along the roof and through the north gable, so the transit instrument (A5) sweeps the sky
    from horizon to horizon and the brass line runs out of the door into the court. It stands on the
    V1 sight line to the foot of the clock tower, so it is kept low: its top is at y 4.2, which hides
    the front only up to the string course and none of the great windows.
  - the water tower: four riveted legs with girts and knee braces, a walk with an iron rail, a round
    riveted tank under a low conical cap, a riser pipe and a ladder; north-west shoulder
    (S.WATER_TOWER). Its top stays a block under the cornice.
  - the weather station: a fenced instrument enclosure on the north slope (S.WEATHER_STATION) with a
    louvred shelter (a Stevenson screen), a wind mast, a rain gauge and a free pedestal.
  - the south lookout: a stone terrace with a prow toward the cloud sea (S.SOUTH_LOOKOUT), the site's
    rail round it and a stand left for a tripod telescope; V11 (the look back) is taken from here, so
    nothing on it stands in that picture's middle.
  - the three ways down from the upper terrace to the shelves.

The instruments themselves -- the meridian circle, the anemometer and vane, the thermometers, the
tripod telescope and the benches -- belong to the machines and props lines; this card leaves the
shells, the sockets and the clear spots for them. The terrain card lays each shelf's flat rock and the
neck that leads to it; these shells stand on the foot levels it gives (S.*["feet"], the stone block
one below) and bring a short footing of their own, laid into air only, so nothing floats before the
terrain is merged. Terrace edges use the site's one rail (site/_kit.rail).
"""
from artkit.canvas import Mix

from . import _kit as K
from ..common import blocks as B
from ..common import skeleton as S

ORDER = 70      # after the terrain (10) and the court paving (60); the shells go on the finished ground

# --- materials (occupancy-table roles only) -------------------------------------------------------
WALL = B.ASHLAR_ROUGH.block             # the darker, banded ashlar of the base storey: the hut's walls
JAMB = B.ASHLAR_FINE.block              # dressed stone, only for the jambs of the meridian slot
EMBLEM = B.ASHLAR_EMBLEM                # the emblem block at the head of each jamb
COPE = B.ASHLAR_PANEL.slab              # a grey-white slab: the cap of a pedestal
PLINTH = B.SLATE_BRICK.block            # dark plinths, footings, the steps' landings
POST = B.SLATE_BRICK.wall               # a slate post
ROOF_SLAB = B.SLATE_TILE.slab           # dark slate roof
BRASS = B.BRASS_INLAY                   # the brass meridian line
IRON = B.IRON_RIVETED.block             # riveted plate: legs, bands, decks
IRON_SLAB = B.IRON_RIVETED.slab
IRON_STAIR = B.IRON_RIVETED.stairs
PLATE = B.IRON_PLATE                    # plain plate: the tank
GRATE = B.IRON_GRATE                    # open grating: the walk round the tank
BARS = B.IRON_BARS                      # iron rail and ladders on iron structures (stone edges: K.rail)
HATCH = B.IRON_HATCH                    # hatch, shutter, louvre
ROD = B.IRON_ROD                        # thin rod: finials, the wind mast
PIPE = B.IRON_PIPE                      # thin pipe: the riser

# a dark broken mix for the shelves' own floors so none reads as one flat sheet
FOOTING = Mix({B.SLATE_BRICK.block: 10, B.SLATE_TILE.block: 3, B.SLATE_SMOOTH.block: 3}, seed=2292)
STEP = B.SLATE_BRICK.stairs             # the steps down to the shelves: the terrace's small dark stone

# The ways down from the upper terrace, agreed with the terrain card (c221 #21052): the terrain
# leaves its railing open in these cells and stands a gate pier either side; the steps are here.
LOOKOUT_WAY = (44, 46)      # x, through the terrace's south edge, on the lookout's middle line
WEATHER_WAY = (2, 4)        # x, through the north edge
TOWER_WAY = (-33, -31)      # z, through the west edge


# --- small helpers --------------------------------------------------------------------------------
def _put(c, o, x, y, z, state, keep=False):
    c.set(o[0] + x, o[1] + y, o[2] + z, state, keep=keep)


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
                _put(c, o, x, y - d, z, PLINTH, keep=True)
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
    h = S.MERIDIAN_HUT["size"] // 2
    x0, x1, z0, z1 = cx - h, cx + h, cz - h, cz + h     # x 31..39, z -34..-26
    dx, dz = S.MERIDIAN_HUT["door"]                     # (35, -26): the south end of the slot
    mx = S.MERIDIAN_X                                   # 35
    floor, on = S.PAVING_Y, S.GROUND                    # -1 the paving block, 0 the standing level
    eave = on + 3                                       # the roof course: a plinth and two courses under it

    # the floor: the terrace's own stones, the meridian's column in the middle tone, the brass on it
    for x in range(x0 + 1, x1):
        for z in range(z0 + 1, z1):
            _put(c, o, x, floor, z, K.STRIP if abs(x - mx) <= 1 else K.FIELD)
    _put(c, o, dx, floor, dz, K.STRIP)
    for z in range(z0 + 1, dz + 1):
        _put(c, o, mx, on, z, BRASS)

    # the walls: a slate plinth and two courses of banded ashlar; the slot stands on the plinth in
    # the north gable and comes down to the floor in the south one
    for x, z in _ring(x0, z0, x1, z1):
        if (x, z) == (dx, dz):
            continue
        _put(c, o, x, on, z, PLINTH)
        if x != mx:
            _put(c, o, x, on + 1, z, WALL)
            _put(c, o, x, on + 2, z, WALL)
    for z in (z0, z1):                                  # the gables rise one course more, to the roof's top
        for x in range(x0 + 1, x1):
            if abs(x - mx) == 1:                        # dressed jambs with the emblem at their heads
                _put(c, o, x, on + 1, z, JAMB)
                _put(c, o, x, on + 2, z, JAMB)
                _put(c, o, x, eave, z, EMBLEM)
            elif x != mx:
                _put(c, o, x, eave, z, WALL)
    for wx in (x0, x1):                                 # two small dark windows in each long wall
        for wz in (cz - 2, cz + 2):
            _put(c, o, wx, on + 2, wz, B.WINDOW_DARK.pane)

    # the roof: slate in two halves that rise half a block from the eaves, and along the slot the two
    # iron shutters, slid open and lying on the roof either side of it
    for z in range(z0, z1 + 1):
        for x in range(x0, x1 + 1):
            d = abs(x - mx)
            if d == 1:
                _put(c, o, x, eave + 1, z, HATCH + f"[facing={'east' if x < mx else 'west'},half=bottom,open=false]")
            elif d == h:
                _put(c, o, x, eave, z, ROOF_SLAB + "[type=bottom]")
            elif d > 1 and z0 < z < z1:
                _put(c, o, x, eave, z, ROOF_SLAB + "[type=top]")


# --- the water tower (S.WATER_TOWER, north-west shoulder) -----------------------------------------
def _water_tower(c, o):
    x0, z0, x1, z1 = S.WATER_TOWER["box"]               # -21,-35,-13,-27
    foot = S.WATER_TOWER["feet"]                        # -2, where the legs stand
    cx, cz = (x0 + x1) // 2, (z0 + z1) // 2             # -17, -31
    legs = [(cx + sx * 2, cz + sz * 2) for sx in (-1, 1) for sz in (-1, 1)]
    deck_y = foot + 9                                   # 7
    tank_lo, tank_hi = deck_y + 1, deck_y + 4           # 8..11; the cap ends at 13.5, the vent at 14

    # until the terrain card's shelf is merged the shelf is a flat slab laid only where there is
    # nothing yet; the site's rail on the three sides over the drop, the uphill (east) side open
    _fill(c, o, x0, foot - 1, z0, x1, foot - 1, z1, FOOTING, keep=True)
    _fill(c, o, x0, foot - 2, z0, x1, foot - 3, z1, PLINTH, keep=True)
    edge = [(x, z) for x, z in _ring(x0, z0, x1, z1) if not (x == x1 and z0 < z < z1)]
    piers = {(x, bz) for bz in (z0, z1) for x in K.spaced([x0, x1])} | {(x0, z) for z in K.spaced([z0, z1])}
    K.rail(c, o, edge, piers, y=foot, kerb=True)

    # four riveted legs on slate footings; thin girts at two levels; a knee brace under the deck
    # either side of every leg
    for lx, lz in legs:
        _put(c, o, lx, foot - 1, lz, PLINTH)
        _put(c, o, lx, foot - 2, lz, PLINTH, keep=True)
        _fill(c, o, lx, foot, lz, lx, deck_y - 1, lz, IRON)
        tx, tz = (1 if lx < cx else -1), (1 if lz < cz else -1)
        _put(c, o, lx + tx, deck_y - 1, lz, IRON_STAIR + f"[facing={'west' if tx > 0 else 'east'},half=top]")
        _put(c, o, lx, deck_y - 1, lz + tz, IRON_STAIR + f"[facing={'north' if tz > 0 else 'south'},half=top]")
    for gy in (foot + 2, foot + 5):
        for x, z in _ring(cx - 2, cz - 2, cx + 2, cz + 2):
            if (x, z) not in legs:
                _put(c, o, x, gy, z, IRON_SLAB + "[type=top]")

    # the deck: a riveted floor under the tank, an open grating walk round it with an iron rail
    for x in range(cx - 3, cx + 4):
        for z in range(cz - 3, cz + 4):
            walk = max(abs(x - cx), abs(z - cz)) == 3
            _put(c, o, x, deck_y, z, GRATE if walk else IRON)
            if walk:
                _put(c, o, x, deck_y + 1, z, BARS)

    # the tank: a round riveted drum (five across, the corners off), a band top and bottom, a low
    # conical cap and a vent
    tank = [(x, z) for x in range(cx - 2, cx + 3) for z in range(cz - 2, cz + 3) if abs(x - cx) + abs(z - cz) < 4]
    for x, z in tank:
        for y in range(tank_lo, tank_hi + 1):
            _put(c, o, x, y, z, IRON if y in (tank_lo, tank_hi) else PLATE)
        rim = max(abs(x - cx), abs(z - cz)) == 2
        _put(c, o, x, tank_hi + 1, z, IRON_SLAB + "[type=bottom]" if rim else IRON)
        if not rim and (x, z) != (cx, cz):
            _put(c, o, x, tank_hi + 2, z, IRON_SLAB + "[type=bottom]")
    _put(c, o, cx, tank_hi + 2, cz, ROD + "[facing=up]")

    # the riser from a valve box on the ground up into the tank, and a ladder up the north-east leg,
    # where the way down from the terrace arrives, to a hatch in the walk
    _put(c, o, cx, foot, cz, PLATE)
    for y in range(foot + 1, deck_y):
        _put(c, o, cx, y, cz, PIPE + "[axis=y]")
    lx, lz = cx + 2, cz - 2
    for y in range(foot, deck_y):
        _put(c, o, lx + 1, y, lz, BARS)
    _put(c, o, lx + 1, deck_y, lz, HATCH + "[facing=west,half=top,open=true]")


# --- the weather station (S.WEATHER_STATION, north slope) -----------------------------------------
def _weather_station(c, o):
    x0, z0, x1, z1 = S.WEATHER_STATION["box"]           # -2,-49,8,-43
    foot = S.WEATHER_STATION["feet"]                    # -4
    pave = foot - 1                                     # -5, the paving block

    # a small paved platform footed a little into the slope, a landing in the middle stone where the
    # steps arrive; the site's rail on the three sides over the drop (a fenced instrument enclosure),
    # the uphill (south) side open
    _fill(c, o, x0, pave, z0, x1, pave, z1, FOOTING)
    _fill(c, o, WEATHER_WAY[0], pave, z1 - 1, WEATHER_WAY[1], pave, z1, K.STRIP)
    _fill(c, o, x0, pave - 1, z0, x1, pave - 3, z1, PLINTH, keep=True)
    edge = [(x, z) for x, z in _ring(x0, z0, x1, z1) if not (z == z1 and x0 < x < x1)]
    piers = {(x, z0) for x in K.spaced([x0, x1])} | {(bx, z) for bx in (x0, x1) for z in K.spaced([z0, z1])}
    K.rail(c, o, edge, piers, y=foot, kerb=True)

    # the instrument shelter (a Stevenson screen): a louvred box two cells long and two high on two
    # iron posts, a thin cap; open inside for the thermometers (A5/A6)
    sx, sz = x0 + 2, z0 + 3                             # (0, -46) and the cell east of it
    for x in (sx, sx + 1):
        _put(c, o, x, foot, sz, BARS)
        _put(c, o, x, foot + 3, sz, IRON_SLAB + "[type=bottom]")
        for y in (foot + 1, foot + 2):
            _put(c, o, x, y, sz - 1, HATCH + "[facing=north,half=bottom,open=true]")
            _put(c, o, x, y, sz + 1, HATCH + "[facing=south,half=bottom,open=true]")
    for y in (foot + 1, foot + 2):
        _put(c, o, sx - 1, y, sz, HATCH + "[facing=west,half=bottom,open=true]")
        _put(c, o, sx + 2, y, sz, HATCH + "[facing=east,half=bottom,open=true]")

    # the wind mast: a riveted foot, a thin rod eight blocks up and a cross-arm near its head for the
    # anemometer and the vane (A5)
    wx, wz = x1 - 2, z0 + 2                             # (6, -47)
    _put(c, o, wx, foot, wz, IRON)
    for y in range(foot + 1, foot + 9):
        _put(c, o, wx, y, wz, ROD + "[facing=up]")
    _put(c, o, wx - 1, foot + 7, wz, ROD + "[facing=west]")
    _put(c, o, wx + 1, foot + 7, wz, ROD + "[facing=east]")

    # the rain gauge: a short plate drum under a lid; and a free stone pedestal (sunshine recorder: A6)
    gx, gz = x1 - 2, z1 - 2                             # (6, -45)
    _put(c, o, gx, foot, gz, PLATE)
    _put(c, o, gx, foot + 1, gz, HATCH + "[facing=north,half=bottom,open=false]")
    px, pz = (x0 + x1) // 2, z0 + 2                     # (3, -47)
    _put(c, o, px, foot, pz, POST)
    _put(c, o, px, foot + 1, pz, COPE + "[type=bottom]")


# --- the south lookout (S.SOUTH_LOOKOUT, south ridge; V11) ----------------------------------------
def _south_lookout(c, o):
    x0, z0, x1, z1 = S.SOUTH_LOOKOUT["box"]             # 40,48,50,56
    foot = S.SOUTH_LOOKOUT["feet"]                      # -5, where a person stands (V11)
    pave = foot - 1                                     # -6, the floor block
    cut = 3                                             # the two south corners are cut off: a prow
    cells = [(x, z) for x in range(x0, x1 + 1) for z in range(z0, z1 + 1)
             if min(x - x0, x1 - x) + (z1 - z) >= cut]
    wx0, wx1 = LOOKOUT_WAY
    tx, tz = (x0 + x1) // 2, z1 - 2                     # the telescope stand, on the middle line in the prow

    # the floor: dark slate, a walk in the middle stone from the steps to a round stand in the prow,
    # where a riveted ring is let in for the tripod telescope (A5/A6); a footing into the slope
    for x, z in cells:
        walk = wx0 <= x <= wx1 and z < tz
        stand = abs(x - tx) + abs(z - tz) <= 2
        _put(c, o, x, pave, z, K.STRIP if walk or stand else FOOTING)
        for d in (1, 2, 3):
            _put(c, o, x, pave - d, z, PLINTH, keep=True)
    for ddx, ddz in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        _put(c, o, tx + ddx, pave, tz + ddz, IRON)

    # the site's rail round the whole edge (the neck that leads here is three wide, so the north
    # edge hangs free too), open where the steps arrive. Piers only at the four knuckles of the prow:
    # V11 looks north-west over the north edge, and a pier there stands in the middle of the picture.
    edge = [p for p in K.outline(cells) if not (p[1] == z0 and wx0 <= p[0] <= wx1)]
    piers = {(x0, z1 - cut), (x1, z1 - cut), (x0 + cut, z1), (x1 - cut, z1)}
    K.rail(c, o, edge, piers, y=foot, kerb=True)


def build(canvas, origin=(0, 0, 0)):
    _meridian_hut(canvas, origin)
    _water_tower(canvas, origin)
    _weather_station(canvas, origin)
    _south_lookout(canvas, origin)
    _ways_down(canvas, origin)
    return 0
