"""obs_main_facade with the heads of the great windows and of the entrance's arches shut over the
crown (facade.CROWN on: a slab hung between the two corner stairs), for the comparison with the
heads as they are built by default. Its five shots have their twins of the same name in
obs_main_facade; shots.json is written by python -m scenes.obs_main_facade.
"""
from scenes import obs_main_facade as base
from scenes.obs_main_facade import BIOME, BIOME_MARGIN, BIOME_MARGIN_Y, build_models, write_pack  # noqa: F401

CROWN = True


def build():
    return base.build(crown=CROWN)
