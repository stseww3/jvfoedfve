"""Test scene of the work package site/court (plan/packages/site/court.md).

The court as it stands in the master scene: the terraces under it, the main building behind it
(the white model, until the main line's shell is merged), the props line's lamps on it, and the sky
line's light sources last. The lines are built whole, in the master scene's order, so the picture
keeps up with them as their packages are merged.
"""
from artkit.canvas import Canvas

from scenes.obs import main, materials, props, site, sky

BIOME = "obs_blue"
BIOME_MARGIN = 80
BIOME_MARGIN_Y = 140
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
    """The court paints nothing itself; it stands on the repainted blocks as the materials line has
    them today (ashlar, brass inlay, cast iron)."""
    return materials.pack(pack_dir)
