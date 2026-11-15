"""Trial only (never delivered): obs_trial_v6 with another list of the lip's lamps."""
from scenes import obs_trial_v6 as base
from scenes.obs_trial_v6 import BIOME, BIOME_MARGIN, BIOME_MARGIN_Y, build_models, write_pack  # noqa: F401

NORTH = [(60, -18), (60, -26), (60, -34)]
LIP = NORTH + [(60, 18)]


def build():
    return base.build_with(LIP)


def shots():
    return base.shots_for({"v6": base.base.BLUE})
