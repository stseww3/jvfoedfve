"""Test scene of the work package site/outbuildings (plan/packages/site/outbuildings.md).

The four small buildings as they stand in the master scene: the terraces and shelves under them, the
main building behind them (the white model, until the main line's shell is merged), the props line on
the ground, and the sky line's light sources last. The lines are built whole, in the master scene's
order, so the picture keeps up with them as their packages are merged.
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
    """The outbuildings paint nothing themselves; they stand on the repainted blocks as the
    materials line has them today (ashlar, slate, cast iron)."""
    return materials.pack(pack_dir)
