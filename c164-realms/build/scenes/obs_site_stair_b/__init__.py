"""The other floor of the lower platform on the scene of obs_site_stair: the same hill, and three of
its shots under the same names.

site/lowerplatform.FLOORS keeps two floors until the pictures have been judged: the one the master
scene shows (lowerplatform.FLOOR) is in obs_site_stair, the other one here. They are compared
picture by picture.
"""
from scenes import obs_site_stair as A
from scenes.obs.site import lowerplatform
from scenes.obs_site_stair import BIOME, BIOME_MARGIN, BIOME_MARGIN_Y, build_models, write_pack  # noqa: F401

FLOOR = next(name for name in lowerplatform.FLOORS if name != lowerplatform.FLOOR)


def build():
    shown = lowerplatform.FLOOR
    lowerplatform.FLOOR = FLOOR
    try:
        return A.build()
    finally:
        lowerplatform.FLOOR = shown
