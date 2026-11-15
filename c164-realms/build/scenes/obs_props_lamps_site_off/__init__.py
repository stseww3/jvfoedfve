"""Test scene of props/lamps for the whole site with the lamps of the site OFF: the master scene as
it stands in this tree, with the switches left as the assembly has them (lamps.DRESS off, so only
the pair of bracket lamps at the entrance and the two street lamps before it stand).

The same cameras and times as obs_props_lamps_site, shot for shot, so the two sets of pictures pair
up under their shot's name: what the lamps of the site add to the way in is seen by putting one
against the other. The card asks for both sets (packages/props/lamps.md, the pictures owed), and the
way in was judged this way before: V1's front from y 4 up 12.6% hidden with the lamps off against
12.8% with them on (the card, record of the site lamps).
"""
from scenes import obs
from scenes.obs_props_lamps_site import BIOME, BIOME_MARGIN, BIOME_MARGIN_Y  # noqa: F401
from scenes.obs_props_lamps_site import build_models, write_pack, shots          # noqa: F401


def build():
    """Every line in the master scene's order, with neither the site's lamps nor the building's own
    lights asked for: the switches as they stand when the master scene is assembled."""
    c = obs.build()
    return c
