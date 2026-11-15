"""Test scene of the work package site/terrain (plan/packages/site/terrain.md).

The hilltop as it stands in the master scene: the site line whole (the mountain, the terraces and
the stand-in ring of cloud of site/terrain, the court, whatever else of the site is merged by now),
the main building behind it, the props line's lamps and instruments, and the sky line's light and
look last. The lines are built whole, in the master scene's order, so the picture keeps up with
them as their packages merge.

The views are the three the card is judged on -- V1 (arrival: the skeleton's eye and aim), V11 (from
the south lookout, three-quarter, afterglow in the west) and V12 (the plateau from above) -- with a
postage stamp of V1 for the silhouette, the sunset terrace and the prow under it, and the two flanks.

obs_site_terrain_nosnow is the same hill without its snow, on the four views the snow is judged
on: the review measures the snow by the difference between the two pictures of a view.
"""
from artkit.canvas import Canvas

from scenes.obs import main, materials, props, site, sky
from scenes.obs.site import terrain

BIOME = "obs_blue"
BIOME_MARGIN = 120
BIOME_MARGIN_Y = 160
LINES = (site, main, props, sky)


def build(snow=None):
    """snow: with the mountain's snow or without; None is the package's own switch (terrain.SNOW_ON)."""
    c = Canvas()
    was = terrain.SNOW_ON
    if snow is not None:
        terrain.SNOW_ON = bool(snow)
    try:
        for line in LINES:
            line.build(c, (0, 0, 0))
    finally:
        terrain.SNOW_ON = was
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
