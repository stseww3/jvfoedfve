"""obs_main_facade with version C of the entrance (the doorway and the great window over it joined
into one arch the height of the front). Its four shots have their twins of the same name in
obs_main_facade (version B) and obs_main_facade_a; shots.json is written by
python -m scenes.obs_main_facade.
"""
from scenes import obs_main_facade as base
from scenes.obs_main_facade import BIOME, BIOME_MARGIN, BIOME_MARGIN_Y, build_models, write_pack  # noqa: F401

ENTRANCE = "C"


def build():
    return base.build(ENTRANCE)
