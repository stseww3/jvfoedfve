"""Version b of the clock tower's spire (the iron platform) in the scene of obs_main_tower: the same
building, the same shots. The two are compared picture by picture: every shot of this scene has its
twin of the same name in obs_main_tower.

    python -m scenes.obs_main_tower      writes shots.json for both
"""
from scenes import obs_main_tower as _a
from scenes.obs_main_tower import BIOME, BIOME_MARGIN, BIOME_MARGIN_Y, TIME, build_models, shots, write_pack  # noqa: F401

SPIRE = "b"


def build():
    return _a.build(SPIRE)
