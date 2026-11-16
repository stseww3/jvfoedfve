"""Test scene of the work package site/terrain (plan/packages/site/terrain.md).

The hilltop as it stands in the master scene: the site line whole (the mountain and the terraces
of site/terrain, the court, whatever else of the site is merged by now), the main building behind
it, the machines that stand in the open (the armillary, the clocks, the mast), the props line's
lamps and instruments, and the sky line last: its light, its look and the sea of clouds the mountain
stands in. The lines are built whole, in the master scene's order, so the picture keeps up with
them as their packages merge.

The views are the three the card is judged on -- V1 (arrival: the skeleton's eye and aim), V11 (from
the south lookout, three-quarter, afterglow in the west) and V12 (the plateau from above) -- with a
postage stamp of V1 for the silhouette, the sunset terrace and the prow under it, and the two flanks.
All of them in the map's hour (14000: the light is locked on the blue version), the hour the real
pictures of the board are taken in.

obs_site_terrain_nosnow is the same hill without its snow, on the four views the snow is judged
on: the review measures the snow by the difference between the two pictures of a view.
"""
from artkit.canvas import Canvas

from scenes.obs import machines, main, materials, props, site, sky
from scenes.obs.site import terrain

BIOME = "obs_blue"
BIOME_MARGIN = 120
BIOME_MARGIN_Y = 160
LINES = (site, main, machines, props, sky)


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
    """The models of the lines built here, and the materials line's own: other lines show those
    (the linings behind the building's windows)."""
    out = {}
    for line in (materials,) + LINES:
        out.update(line.models() or {})
    return out


def write_pack(pack_dir):
    """The terrain paints nothing itself; it stands on the repainted blocks as the materials line
    has them today (ashlar, slate, snow and the cloud stand-ins), under the sky line's own sky: the
    scene takes the map's hour, and without the sky's pictures the game's own sun would stand as a
    square on the western horizon of every shot that looks west."""
    return list(materials.pack(pack_dir) or []) + list(sky.pack(pack_dir) or [])
