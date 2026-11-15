"""obs_sky_lights without the light the gold window over the door lends to the two curtained
windows beside it (_lightkit.LENDS off): each of the entrance's three windows lights its own
surround and no more. For comparison only: whether the lending stays is the director's to rule on
when he has seen both (plan/packages/sky/lights.md). The blue building stands here alone; its
three shots have their twins of the same name in obs_sky_lights; shots.json is written by
python -m scenes.obs_sky_lights.
"""
from scenes import obs_sky_lights as base
from scenes.obs_sky_lights import BIOME, BIOME_MARGIN, BIOME_MARGIN_Y, write_pack  # noqa: F401
from scenes.obs_sky_lights.props import build_models  # noqa: F401

LENDS = False


def build():
    return base.build(only=base.NOLEND_LOOKS, lends=LENDS)
