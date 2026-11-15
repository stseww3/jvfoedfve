"""obs_main_facade with version A of the entrance (one doorway in the middle bay, up through the
string course): kept for the comparison. Its four shots have their twins of the same name in
obs_main_facade (version B) and obs_main_facade_c; shots.json is written by
python -m scenes.obs_main_facade.
"""
from scenes import obs_main_facade as base
from scenes.obs_main_facade import BIOME, BIOME_MARGIN, BIOME_MARGIN_Y, build_models, write_pack  # noqa: F401

ENTRANCE = "A"


def build():
    return base.build(ENTRANCE)
