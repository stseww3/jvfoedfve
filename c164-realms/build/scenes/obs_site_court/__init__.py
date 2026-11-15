"""Test scene of the work package site/court (plan/packages/site/court.md).

The court as it stands in the master scene: the terraces under it, the main building behind it
(the white model, until the main line's shell is merged), the props line's lamps on it, and the sky
line's light sources last. The lines are built whole, in the master scene's order, so the picture
keeps up with them as their packages are merged.

The site's own lamps are asked for as a test scene may (props/lamps.dress): the court names the
cells of the lamps of the way in and of the low lamps on the east lip (path_lamps, lip_lamps), and
nobody can tell whether they read without them in the picture. The master scene keeps DRESS off
until the director has seen them.
"""
from artkit.canvas import Canvas

from scenes.obs import main, materials, props, site, sky
from scenes.obs.props import lamps

BIOME = "obs_blue"
BIOME_MARGIN = 80
BIOME_MARGIN_Y = 140
LINES = (site, main, props, sky)


def build():
    c = Canvas()
    lamps.dress(c, True)
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
