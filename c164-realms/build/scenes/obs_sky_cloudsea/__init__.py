"""Test scene of the work package sky/cloudsea (plan/packages/sky/cloudsea.md): a placeholder
hilltop rising out of the sea of clouds, seen from the cameras the card is judged on.

The hilltop is a stand-in built from the skeleton's masses (the real mountain is site/terrain's, the
building is main's): the upper terrace, the sunset platform, the lower platform with the station
deck and the shelves, each a flat rock falling away into the cloud, a pale massing of the main
building (a bar, a dome, a tower) so the silhouette over the sea can be judged, and the cable
trestle running down from the station into the sea. Only enough to answer the card's questions:
from V1, V11, V12, the sunset rail and close to the cloud face, is an edge of the sea seen
anywhere, does the rock rise out of cloud rather than sit on a plate, and is the track lost in the
cloud or does it end in a hole?

The three ways to make the sea are three scenes with the same hilltop and the same shots, compared
picture by picture: this one is version "c" (block sea and vanilla layer, what the master scene
builds), obs_sky_cloudsea_a is "a" (vanilla layer only), obs_sky_cloudsea_b is "b" (blocks only).
The offline renderer draws the fog but not the vanilla layer, the afterglow or the warm fog towards
the west, so offline "c" and "b" are one picture -- the block sea in fog -- and "a" is the bare
hilltop. On the real client S1 renders each version, every camera with the cloud setting on fancy,
fast and off, and this scene's trials.json besides: two of the cameras under the sky's trial
moments (the vanilla layer in three colours, the fog ending sooner and later).

    python -m scenes.obs_sky_cloudsea     # rewrites shots.json and trials.json
"""
import math

import numpy as np

from artkit import noise as N
from artkit.canvas import Canvas, Mix
from scenes.obs import materials
from scenes.obs.common import blocks as B
from scenes.obs.common import skeleton as S
from scenes.obs.sky import cloudsea, comet, mood

BIOME = "obs_blue"
BIOME_MARGIN = 240          # the look and the sea reach far past the hilltop
BIOME_MARGIN_Y = 160

VERSION = "c"

# --- the placeholder mountain ------------------------------------------------------------------------
SLOPE = 1.25                # blocks of fall per block out from a flat
ROCK_FLOOR = -29            # the rock ends here, three below the cloud line (site's K.ROCK_FLOOR)
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
PAVE = B.SLATE_SMOOTH.block
STONE = B.ASHLAR_FINE.block
COPPER = B.VERDIGRIS_CUT.block
IRON = B.IRON_RIVETED


def _rock(x, y, z):
    return ROCK_HIGH(x, y, z) if y > ROCK_SPLIT else ROCK_LOW(x, y, z)


def _mountain(c):
    """Every flat falls away at SLOPE with some crag; the highest wins. A watertight crust: a column
    is filled from its surface down to its lowest neighbour, the rim down to ROCK_FLOOR."""
    x0, x1, z0, z1 = -64, 124, -84, 90
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
    cell north for every cell east, until they are under the cloud. Every six cells a bent: a girder
    across, two legs down to the rock or to the rock's floor, bars between the legs. The last bents
    stand in the sea and the track ends in it: the card has to show how the cloud takes them."""
    x1, axis = S.CABLE_STATION[2], int(S.V1["pos"][2] // 1)          # 91, -33
    x = x1
    while True:
        x += 1
        top = S.STATION_GROUND - 0.5 * max(0, x - x1 - 4)            # the upper face of the rails
        if top <= ROCK_FLOOR + 2:
            break                                                     # under the cloud: the track ends
        z = int(round(axis - (x - x1 - 1) / 3.0))
        y, half = (int(top) - 1, "top") if top == int(top) else (int(top // 1), "bottom")
        for dz in (-1, 1):
            c.set(x, y, z + dz, IRON.slab + f"[type={half}]")
        if (x - x1 - 7) % 6:
            continue
        cap = y if half == "top" else y - 1                           # a bent: x 98, 104 ..
        for dz in (-1, 0, 1):
            c.set(x, cap, z + dz, IRON.block)
            for yy in range(cap - 1, ROCK_FLOOR - 1, -1):
                if c.has(x, yy, z + dz):
                    break                                             # down to the rock
                c.set(x, yy, z + dz, IRON.block if dz else B.IRON_BARS)


def build(version=VERSION):
    c = Canvas()
    _mountain(c)
    _paving(c)
    _massing(c)
    _trestle(c)
    cloudsea.build(c, (0, 0, 0), version=version)
    return c


def write_pack(pack_dir, version=VERSION):
    out = list(materials.pack(pack_dir) or [])
    out += list(comet.pack(pack_dir) or [])                       # the sun painted out, the comet
    out += list(cloudsea.pack(pack_dir, version=version) or [])
    return out


# scene coordinates: the eye, what it looks at, the time (14000 blue, 12900 glow)
RAIL_X = SUN_C[0] - SUN_R + 2                                     # two inside the west rim
VIEWS = {
    "v1": (S.V1["pos"], S.V1["look_at"], 14000),                  # the arrival view (A0 #171)
    "v11": (S.V11["pos"], S.V11["look_at"], 12900),               # the south lookout, afterglow on the left
    "v12": ((66, 72, 58), (8, -2, 0), 14000),                     # the plateau from above: the plate test
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

# The sky's trial moments (sky/mood.TRIALS: the blue hour with one value changed, held for 200 ticks
# in the morning) on the two cameras that show where the block sea ends and the vanilla layer goes
# on. They are for the real client and kept apart in trials.json: the offline renderer does not
# draw the vanilla layer, and a scene keeps an offline picture of every shot in shots.json.
#   mist, veil, fogged   the vanilla layer's colour drawn to the fog's in three steps. The layer
#                        takes no fog, so where the fog ends it stands a tone and a half lighter
#                        than the block sea beside it and draws the sea's outline.
#   near, far            the fog ending at 144 and at 256 instead of 192: how much of the sea's end
#                        it hides.
#   glowed               the end the director ruled for (11-16 00:33): the vanity layer drawn at the
#                        colour the void actually shows in the real game, #755064 -- the fog colour
#                        with the afterglow fan over it, measured off 4ef326f's v12_aerial by a2. The
#                        block sea sinks to #383a74 there and the two read a brightness and a whole
#                        warm-to-cool turn apart; this moment shows the join with that closed.
# The ticks are sky/mood's; the numbers here stand in for a trial that is not in the tree yet (the
# picture is then the plain blue hour).
TRIALS = {"mist": 8100, "veil": 9100, "fogged": 10100, "glowed": 11100, "near": 5100, "far": 7100}
TRIAL_VIEWS = ("v12", "station_east")


def _shot(name, eye, at, t):
    return {"name": name, "pos": [round(float(v), 2) for v in eye], "look_at": [float(v) for v in at], "time": t}


def shots():
    return [_shot(name, *view) for name, view in VIEWS.items()]


def trial_shots():
    return [_shot(f"{view}_{name}", *VIEWS[view][:2], mood.tick(name) if name in mood.TRIALS else t)
            for view in TRIAL_VIEWS for name, t in TRIALS.items()]
