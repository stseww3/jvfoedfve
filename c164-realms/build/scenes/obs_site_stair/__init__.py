"""Test scene of the work package site/stair (plan/packages/site/stair.md): the grand stair, the
retaining wall under the upper terrace, the floor and the edge of the lower platform.

The hill as it stands in the master scene: the site line whole (the terrain, the terraces, the court
and whatever stands on the lower platform by now), the main building above it, the props line's
lamps and the sky line's light sources last. The lines are built whole, in the master scene's
order, so the picture keeps up with them as their packages are merged.

The views: V1 as the skeleton fixes it (the arrival view the package is judged on: the wall is the
band under the building, the stair comes down on the left), the stair on its axis from the yard,
the look back down it from the terrace, the wall and a cheek from near, and two from above.
"""
from artkit.canvas import Canvas

from scenes.obs import main, materials, props, site, sky

BIOME = "obs_blue"
BIOME_MARGIN = 100
BIOME_MARGIN_Y = 150
LINES = (site, main, props, sky)


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
    """The stair paints nothing itself; it stands on the repainted blocks as the materials line has
    them today (ashlar, cast iron)."""
    return materials.pack(pack_dir)
