"""Test scene of the work package site/terrain (plan/packages/site/terrain.md).

The hilltop as it stands in the master scene: the mountain and cloud line (site/terrain), the
terrace paving under it (site/ground, site/court), the main building's silhouette behind it (the
white model, until the facade is merged) and the sky line's light and look last. The lines are
built whole, in the master scene's order, so the picture keeps up with them as their packages merge.
The views are the three the card is judged on -- V1 (arrival, the backlit silhouette over the
cloud), V11 (the sunset terrace, three-quarter, afterglow in the west) and V12 (the plateau from
above) -- with a postage-stamp of V1 for the silhouette and a few flanks.
"""
from artkit.canvas import Canvas

from scenes.obs import main, materials, site, sky

BIOME = "obs_blue"
BIOME_MARGIN = 120
BIOME_MARGIN_Y = 160
LINES = (site, main, sky)


def build():
    c = Canvas()
    for line in LINES:
        line.build(c, (0, 0, 0))
    return c


def build_models():
    out = {}
    for line in LINES:
        out.update(line.models() or {})
    return out


def write_pack(pack_dir):
    """The terrain paints nothing itself; it stands on the repainted blocks as the materials line
    has them today (ashlar, slate and the cloud stand-ins)."""
    return materials.pack(pack_dir)
