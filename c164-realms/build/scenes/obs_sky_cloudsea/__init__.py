"""Test scene of the work package sky/cloudsea (plan/packages/sky/cloudsea.md): a placeholder
hilltop rising out of the sea of clouds, seen from the cameras the card is judged on.

The hilltop is a stand-in built from the skeleton's masses (the real mountain is site/terrain's, the
building is main's): the upper terrace, the sunset platform, the lower platform with the station
deck and the shelves, each a flat rock falling away into the cloud as the real slopes do, a pale
massing of the main building (a bar, a dome, a tower) so the silhouette over the sea can be judged,
and the cable trestle running down from the station into the sea. Only enough to answer the card's
questions: from V1, V11, V12, the sunset rail and close to the cloud, does the sea read as rolling
cloud and not as a table or as floes, does the rock rise out of cloud rather than stand in a level
cut, and is the track lost in the cloud or does it end in a hole?

The sea is built one way (sky/cloudsea: blocks alone). What the offline renderer shows of it is the
sea under the registry look, in one fog colour and with nothing under the horizon; the map will be
shown at ten chunks with the look drawn by A2's shaders, which paint the far sea there. preview.py
draws that beforehand; the card is judged on the real client's pictures.

    python -m scenes.obs_sky_cloudsea     # rewrites shots.json
"""
import math

import numpy as np

from artkit import noise as N
from artkit.canvas import Canvas, Mix
from scenes.obs import materials
from scenes.obs.common import blocks as B
from scenes.obs.common import skeleton as S
from scenes.obs.sky import cloudsea, comet

BIOME = "obs_blue"
BIOME_MARGIN = 240          # the look and the sea reach far past the hilltop
BIOME_MARGIN_Y = 160

# --- the placeholder mountain ------------------------------------------------------------------------
SLOPE = 0.72                # blocks of fall per block out from a flat (site/terrain's)
ROCK_FLOOR = -29            # the rock ends here, its last course under the sea's face (site's rim)
SEED = 227
SUN_C, SUN_R = S.SUNSET_PLATFORM["centre"], S.SUNSET_PLATFORM["radius"]
# (x0, z0, x1, z1, y of the top block) of every flat the mountain carries
FLATS = [
    (*S.UPPER_TERRACE, S.PAVING_Y),
    (*S.LOWER_PLATFORM, S.LOWER_PAVING_Y),
    (*S.MAST_PAD["box"], S.MAST_PAD["feet"] - 1),
    (*S.WEATHER_STATION["box"], S.WEATHER_STATION["feet"] - 1),
    (*S.WATER_TOWER["box"], S.WATER_TOWER["feet"] - 1),
    (*S.SOUTH_LOOKOUT["box"], S.SOUTH_LOOKOUT["feet"] - 1),
]
ROCK_HIGH = Mix({B.TUFF.block: 6, B.ROCK_ANDESITE.block: 3, B.ROCK_STONE.block: 2, B.ROCK_COBBLED.block: 1},
                seed=SEED)
ROCK_LOW = Mix({B.ROCK_DEEPSLATE: 6, B.ROCK_COBBLED.block: 3, B.TUFF.block: 2}, seed=SEED + 1)
ROCK_SPLIT = -12            # the high mix above, the low mix below
TRACK_END = -27             # site/cablecar's SINK: the upper face of the rails in the track's last column
BARS_FROM = -23             # site/cablecar: a tower is bars from here up and four thin pipes below
SUNK = cloudsea.TROUGH - 1  # the legs go down to the rock or to here (-31), through the sea
PAVE = B.SLATE_SMOOTH.block
STONE = B.ASHLAR_FINE.block
COPPER = B.VERDIGRIS_CUT.block
IRON = B.IRON_RIVETED


def _rock(x, y, z):
    return ROCK_HIGH(x, y, z) if y > ROCK_SPLIT else ROCK_LOW(x, y, z)


def _mountain(c):
    """Every flat falls away at SLOPE with some crag; the highest wins. A watertight crust: a column
    is filled from its surface down to its lowest neighbour, the rim down to ROCK_FLOOR."""
    x0, x1, z0, z1 = -84, 138, -100, 104
    X, Z = np.meshgrid(np.arange(x0, x1 + 1), np.arange(z0, z1 + 1), indexing="ij")
    best = np.full(X.shape, -1e9)
    near = np.full(X.shape, 1e9)
    for fx0, fz0, fx1, fz1, top in FLATS:
        d = np.hypot(np.maximum(np.maximum(fx0 - X, X - fx1), 0), np.maximum(np.maximum(fz0 - Z, Z - fz1), 0))
        best, near = np.maximum(best, top - SLOPE * d), np.minimum(near, d)
    d = np.where(X <= SUN_C[0], np.maximum(np.hypot(X - SUN_C[0], Z - SUN_C[1]) - SUN_R, 0), 1e9)
    best, near = np.maximum(best, S.PAVING_Y - SLOPE * d), np.minimum(near, d)
    crag = 3.2 * N.fbm2(X / 26.0, Z / 26.0, SEED, octaves=3) + 1.2 * N.fbm2(X / 7.0, Z / 7.0, SEED + 1, octaves=2)
    h = np.rint(best + np.clip((near - 1.0) / 6.0, 0.0, 1.0) * crag).astype(int)
    h[h < ROCK_FLOOR] = ROCK_FLOOR - 1                       # no rock here
    p = np.pad(h, 1, constant_values=ROCK_FLOOR - 1)
    low = np.minimum(np.minimum(p[:-2, 1:-1], p[2:, 1:-1]), np.minimum(p[1:-1, :-2], p[1:-1, 2:]))
    floor = np.maximum(np.minimum(h, low + 1), ROCK_FLOOR)
    for i, j in zip(*np.nonzero(h >= ROCK_FLOOR)):
        x, z = int(X[i, j]), int(Z[i, j])
        for y in range(int(h[i, j]), int(floor[i, j]) - 1, -1):
            c.set(x, y, z, _rock(x, y, z))


def _sunset_cells():
    cx, cz = SUN_C
    return {(x, z) for x in range(cx - SUN_R, cx + 1) for z in range(cz - SUN_R, cz + SUN_R + 1)
            if math.hypot(x - cx, z - cz) <= SUN_R - 0.5}


def _paving(c):
    """Deep paving on the flats people stand on, the station deck two courses up on the lower
    platform (V1 stands on it), and a thin iron rail on the rim of the sunset platform."""
    x0, z0, x1, z1 = S.UPPER_TERRACE
    c.box(x0, S.PAVING_Y, z0, x1, S.PAVING_Y, z1, PAVE)
    x0, z0, x1, z1 = S.LOWER_PLATFORM
    c.box(x0, S.LOWER_PAVING_Y, z0, x1, S.LOWER_PAVING_Y, z1, PAVE)
    x0, z0, x1, z1 = S.CABLE_STATION
    c.box(x0, S.LOWER_PAVING_Y + 1, z0, x1, S.STATION_GROUND - 1, z1, PAVE)
    sun = _sunset_cells()
    for x, z in sun:
        c.set(x, S.PAVING_Y, z, PAVE)
        if x < S.UPPER_TERRACE[0] and any((x + i, z + k) not in sun for i, k in ((1, 0), (-1, 0), (0, 1), (0, -1))):
            c.set(x, S.GROUND, z, B.IRON_BARS)


def _shell(c, x0, y0, z0, x1, y1, z1, block):
    """The faces of a box, open underneath."""
    for x in range(x0, x1 + 1):
        for z in range(z0, z1 + 1):
            c.set(x, y1, z, block)
            if x in (x0, x1) or z in (z0, z1):
                for y in range(y0, y1):
                    c.set(x, y, z, block)


def _massing(c):
    """A pale stand-in for the main building: the long block, the drum and dome, the clock tower."""
    _shell(c, S.WALL_W, S.GROUND, S.Z_NORTH, S.WALL_E, S.PARAPET[1], S.Z_SOUTH, STONE)
    dx, dz = S.DOME_CENTRE
    for y in range(S.DRUM_BASE, S.DOME_APEX + 1):
        rad = S.DOME_R if y < S.DOME_SPRING else S.dome_profile(y)
        over = S.DOME_R if y < S.DOME_SPRING else (S.dome_profile(y + 1) or 0.0)
        block = STONE if y < S.DOME_SPRING else COPPER
        for x in range(dx - S.DOME_R, dx + S.DOME_R + 1):
            for z in range(dz - S.DOME_R, dz + S.DOME_R + 1):
                d = math.hypot(x - dx, z - dz)
                if min(rad, over) - 1.6 < d <= rad + 0.3:
                    c.set(x, y, z, block)
    _shell(c, S.CLOCK_SHAFT_X[0], S.GROUND, S.CLOCK_SHAFT_Z[0], S.CLOCK_SHAFT_X[1], S.CLOCK_SHAFT_TOP,
           S.CLOCK_SHAFT_Z[1], STONE)
    cx, cz = (S.CLOCK_SHAFT_X[0] + S.CLOCK_SHAFT_X[1]) // 2, (S.CLOCK_SHAFT_Z[0] + S.CLOCK_SHAFT_Z[1]) // 2
    for y in range(S.CLOCK_SHAFT_TOP + 1, S.CLOCK_TOP + 1):          # the spire
        r = max(0, 3 - (y - S.CLOCK_SHAFT_TOP - 1) // 3)
        c.box(cx - r, y, cz - r, cx + r, y, cz + r, COPPER)
    for y in range(S.CLOCK_TOP + 1, S.CLOCK_BALL_MAST + 1):         # the time-ball mast
        c.set(cx, y, cz, B.IRON_ROD)


def _trestle(c):
    """A stand-in for the cable trestle, on site/cablecar's figures: two rails of riveted slabs leave
    the station deck in V1's row, run level for four cells and then fall one in two, a third of a
    cell north for every cell east, and end where their upper face is one block over the sea's face
    (x 141). Every six cells, as far as x 128, a tower: a girder across, two legs down to the rock or
    into the surf, bars as far down as y -23 and thin pipes below. The last towers stand in the sea
    and the track ends just over it: the card has to show how the cloud takes them."""
    x1, axis = S.CABLE_STATION[2], int(S.V1["pos"][2] // 1)          # 91, -33
    x = x1
    while True:
        x += 1
        top = S.STATION_GROUND - 0.5 * max(0, x - x1 - 4)            # the upper face of the rails
        z = int(round(axis - (x - x1 - 1) / 3.0))
        y, half = (int(top) - 1, "top") if top == int(top) else (int(top // 1), "bottom")
        for dz in (-1, 1):
            c.set(x, y, z + dz, IRON.slab + f"[type={half}]")
        if top <= TRACK_END:
            break                                                     # the track's last column
        cap = y if half == "top" else y - 1
        if (x - x1 - 7) % 6 or cap - 1 <= cloudsea.LOW:
            continue
        for dz in (-1, 0, 1):                                         # a tower: x 98, 104 .. 128
            c.set(x, cap, z + dz, IRON.block)
            for yy in range(cap - 1, SUNK - 1, -1):
                if c.has(x, yy, z + dz):
                    break                                             # down to the rock
                if yy >= BARS_FROM:
                    c.set(x, yy, z + dz, B.IRON_BARS)
                elif dz:
                    c.set(x, yy, z + dz, B.IRON_PIPE + "[axis=y]")


def build():
    c = Canvas()
    _mountain(c)
    _paving(c)
    _massing(c)
    _trestle(c)
    cloudsea.build(c, (0, 0, 0), dress=True)
    return c


def write_pack(pack_dir):
    out = list(materials.pack(pack_dir) or [])
    out += list(comet.pack(pack_dir) or [])                       # the sun painted out, the comet
    out += list(cloudsea.pack(pack_dir) or [])
    return out


# scene coordinates: the eye, what it looks at, the time (14000 blue, 12900 glow)
RAIL_X = SUN_C[0] - SUN_R + 2                                     # two inside the west rim
# V12 is not in the skeleton yet: this is the render station's proposal for the board (its
# tools/boardshots.py, worked out from the skeleton as here), which the director lets stand until
# he has seen the pictures. Once the skeleton holds V12 it is read from there.
V12 = getattr(S, "V12", None)
V12 = ((V12["pos"], V12["look_at"]) if V12 else
       ((S.EAST_EDGE_X + 20.0, 90.0, S.Z_SOUTH + 46.0), (S.MERIDIAN_X, S.GROUND, S.AXIS_Z - 5.5)))
VIEWS = {
    "v1": (S.V1["pos"], S.V1["look_at"], 14000),                  # the arrival view (A0 #171)
    "v11": (S.V11["pos"], S.V11["look_at"], 12900),               # the south lookout, afterglow on the left
    "v12": (V12[0], V12[1], 14000),                               # the whole site from above (the board's)
    "plate": ((66, 72, 58), (8, -2, 0), 14000),                   # nearer and lower: the plate test
    "sunset_west": ((RAIL_X, S.GROUND + S.EYE, 0.5), (RAIL_X - 100, -14, 0.5), 12900),
    "sunset_sw_down": ((RAIL_X + 3, S.GROUND + S.EYE, 9.5), (RAIL_X - 42, -26, 52), 12900),
    "east": ((-92, -14, 0.5), (10, 10, 0.5), 14000),              # from over the sea, the rock rising
    "skim": ((-58, -19.4, 24.5), (-118, -23, -8), 14000),         # low, skimming the cloud face
    "roof_down": ((1.5, S.ROOF_STAND + S.EYE, -20.5), (-52, -26, -34), 14000),   # from the roof terrace
    # outwards where the sea ends nearest to where people stand: is its end seen?
    "station_east": ((S.CABLE_STATION[2] - 0.5, S.STATION_GROUND + S.EYE, -29.5),
                     (S.CABLE_STATION[2] + 110, -27, -52), 14000),                # down the trestle
    "north_out": ((3.5, S.WEATHER_STATION["feet"] + S.EYE, S.WEATHER_STATION["box"][1] + 0.5),
                  (3.5, -26, -174), 14000),                                       # from the weather station
}

# What preview.py draws when it is not told which: the whole site from above, the sunset rail
# towards the west, down the trestle towards the east, down from the roof terrace.
MAIN_VIEWS = ("v12", "sunset_west", "station_east", "roof_down")


def _shot(name, eye, at, t):
    return {"name": name, "pos": [round(float(v), 2) for v in eye], "look_at": [float(v) for v in at], "time": t}


def shots():
    return [_shot(name, *view) for name, view in VIEWS.items()]
