"""Test scene of the work package sky/cloudsea (plan/packages/sky/cloudsea.md): a placeholder
hilltop rising out of the sea of clouds, seen from the cameras the card is judged on.

The hilltop is a stand-in built from the skeleton's masses (the real mountain is site/terrain's, the
building is main's): the upper terrace, the sunset platform, the lower platform with the station
deck and the shelves, each a flat rock falling away into the cloud, and a pale massing of the main
building (a bar, a dome, a tower) so the silhouette over the sea can be judged. Only enough to
answer the card's questions: from V1, V11, V12, the sunset rail and close to the cloud face, is an
edge of the sea seen anywhere, and does the rock rise out of cloud rather than sit on a plate?

The three ways to make the sea are chosen by the environment variable CLOUDSEA_VERSION (a vanilla
layer only, b blocks only, c both). It defaults to "b": the offline renderer draws the fog but not
the vanilla layer, the afterglow or the warm fog towards the west, so what it can show is the block
sea in fog. On the real client S1 renders each version, every camera with the cloud setting on
fancy, fast and off.

    python -m scenes.obs_sky_cloudsea     # rewrites shots.json
"""
import math
import os

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

VERSION = os.environ.get("CLOUDSEA_VERSION", "b")

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


def _station(c):
    """The cable station's deck, two courses on the lower platform; V1 stands on it."""
    x0, z0, x1, z1 = S.CABLE_STATION
    c.box(x0, S.LOWER_PAVING_Y + 1, z0, x1, S.STATION_GROUND - 1, z1, PAVE)


def _massing(c):
    """A pale stand-in for the main building: the long block, the drum and dome, the clock tower."""
    c.box(S.WALL_W, S.GROUND, S.Z_NORTH, S.WALL_E, S.PARAPET[1], S.Z_SOUTH, STONE)
    dx, dz = S.DOME_CENTRE
    for y in range(S.DRUM_BASE, S.DOME_APEX + 1):
        rad = S.DOME_R if y < S.DOME_SPRING else S.dome_profile(y)
        block = STONE if y < S.DOME_SPRING else COPPER
        for x in range(dx - S.DOME_R, dx + S.DOME_R + 1):
            for z in range(dz - S.DOME_R, dz + S.DOME_R + 1):
                if math.hypot(x - dx, z - dz) <= rad + 0.3:
                    c.set(x, y, z, block)
    c.box(S.CLOCK_SHAFT_X[0], S.GROUND, S.CLOCK_SHAFT_Z[0], S.CLOCK_SHAFT_X[1], S.CLOCK_SHAFT_TOP,
          S.CLOCK_SHAFT_Z[1], STONE)
    cx, cz = (S.CLOCK_SHAFT_X[0] + S.CLOCK_SHAFT_X[1]) // 2, (S.CLOCK_SHAFT_Z[0] + S.CLOCK_SHAFT_Z[1]) // 2
    for y in range(S.CLOCK_SHAFT_TOP + 1, S.CLOCK_TOP + 1):          # the spire
        r = max(0, 3 - (y - S.CLOCK_SHAFT_TOP - 1) // 3)
        c.box(cx - r, y, cz - r, cx + r, y, cz + r, COPPER)
    for y in range(S.CLOCK_TOP + 1, S.CLOCK_BALL_MAST + 1):         # the time-ball mast
        c.set(cx, y, cz, B.IRON_ROD)


def _sunset_rail(c):
    """A thin iron rail on the rim of the sunset platform; the camera looks west through it."""
    cx, cz = SUN_C
    for x in range(cx - SUN_R, cx + 1):
        for z in range(cz - SUN_R, cz + SUN_R + 1):
            r = math.hypot(x - cx, z - cz)
            if SUN_R - 1.0 < r <= SUN_R:
                c.set(x, S.GROUND, z, B.IRON_BARS)


def build():
    c = Canvas()
    _mountain(c)
    _station(c)
    _massing(c)
    _sunset_rail(c)
    cloudsea.build(c, (0, 0, 0), version=VERSION)
    return c


def write_pack(pack_dir):
    out = list(materials.pack(pack_dir) or [])
    out += list(comet.pack(pack_dir) or [])                       # the sun painted out, the comet
    out += list(cloudsea.pack(pack_dir, version=VERSION) or [])
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
}


def shots():
    return [{"name": name, "pos": [round(float(v), 2) for v in eye], "look_at": [float(v) for v in at],
             "time": t} for name, (eye, at, t) in VIEWS.items()]
