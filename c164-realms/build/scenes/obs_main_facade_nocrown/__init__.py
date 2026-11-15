"""obs_main_facade with the heads of the great windows and of the entrance's arches as they were
before the director had them shut (facade.CROWN off: the two corner stairs alone, the middle
column open to the lintel). For comparison only: that head is not a candidate any more. Its five
shots have their twins of the same name in obs_main_facade; shots.json is written by
python -m scenes.obs_main_facade.
"""
from scenes import obs_main_facade as base
from scenes.obs_main_facade import BIOME, BIOME_MARGIN, BIOME_MARGIN_Y, build_models, write_pack  # noqa: F401

CROWN = False


def build():
    return base.build(crown=CROWN)
