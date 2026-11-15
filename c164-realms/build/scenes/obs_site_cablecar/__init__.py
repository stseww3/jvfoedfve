"""Test scene of the work package site/cablecar (plan/packages/site/cablecar.md): the cable station
on the lower platform and the trestle that takes its track down into the cloud.

The hill as it stands in the master scene: the site line whole, the main building above it, the
props line and the sky line's light last. The lines are built whole, in the master scene's order,
so the pictures keep up with them as their packages are merged.

Two stand-ins, in this scene only, for what is still on other branches: the east flank of the
mountain with the ridge the trestle stands on (site/terrain's second draft; the ridge by the figures
of site/_kit.py) and a sheet of cloud round its foot (sky/cloudsea). They fill empty cells only, and
go when the real ones are merged.

The views: V1 as the skeleton fixes it (nothing of the station may stand in it), the platform from
the head of its steps, the station from the lower platform and from the head of the grand stair,
the canopy from below, the trestle from the platform's corner and from the side, and one from above.
"""
from artkit.canvas import Canvas, Mix

from scenes.obs import main, materials, props, site, sky
from scenes.obs.common import blocks as B
from scenes.obs.common import skeleton as S
from scenes.obs.site import _kit as K

BIOME = "obs_blue"
BIOME_MARGIN = 100
BIOME_MARGIN_Y = 150
LINES = (site, main, props, sky)

ROCK = Mix({B.TUFF.block: 5, B.ROCK_ANDESITE.block: 3, B.ROCK_COBBLED.block: 2, B.ROCK_DEEPSLATE: 3}, seed=226)
CLOUD = Mix({B.CLOUD[1]: 2, B.CLOUD[2]: 3, B.CLOUD[3]: 2}, seed=227)
CLOUD_Y = (-27, -26)            # the block cloud's two courses; its top face is at y -25
FLANK = (61, -62, 112, -18)     # where the stand-in mountain is drawn
SEA = (61, -96, 176, -10)       # where the stand-in cloud is drawn


def _crust(c, x, z, top, thick=3):
    for y in range(top, max(top - thick, K.ROCK_FLOOR) - 1, -1):
        c.set(x, y, z, ROCK, keep=True)


def _standins(c):
    lx0, lz0, lx1, lz1 = S.LOWER_PLATFORM
    for x in range(FLANK[0], FLANK[2] + 1):             # the slope below the lower platform's edges
        for z in range(FLANK[1], FLANK[3] + 1):
            d = max(lx0 - x, x - lx1, lz0 - z, z - lz1)
            if d > 0:
                top = int(round(S.LOWER_PAVING_Y - 1 - 1.6 * (d - 1)))
                if top >= K.ROCK_FLOOR:
                    _crust(c, x, z, top)
    for x in range(K.CABLE_RIDGE_X[0], K.CABLE_RIDGE_X[1] + 1):     # the ridge, falling two in one each side
        z, y = K.cable_ridge(x)
        for k in range(0, 14):
            top = y - 2 * max(0, k - 1)
            if top < K.ROCK_FLOOR:
                break
            for zz in {z - k, z + k}:
                _crust(c, x, zz, top)
    for x in range(SEA[0], SEA[2] + 1):
        for z in range(SEA[1], SEA[3] + 1):
            for y in CLOUD_Y:
                c.set(x, y, z, CLOUD, keep=True)


def build():
    c = Canvas()
    for line in LINES:
        line.build(c, (0, 0, 0))
        if line is site:
            _standins(c)
    return c


def build_models():
    out = {}
    for line in LINES:
        out.update(line.models() or {})
    return out


def write_pack(pack_dir):
    """The station paints nothing itself; it stands on the repainted blocks as the materials line
    has them today (cast iron, the roof light, the lit and dark windows)."""
    return materials.pack(pack_dir)
