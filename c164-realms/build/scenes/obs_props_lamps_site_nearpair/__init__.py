"""Test scene of props/lamps for the whole site, the second of a pair: obs_props_lamps_site with
the court's pair of street lamps nearest the stair head, which the site leaves out
(lamps.NEAR_PAIR; A0 #54472 picked "without" on the two v2 pictures).

That pair stands six cells before the eye of S.V2 and half-way out to either edge of the picture.
Everything else is obs_props_lamps_site's, and the cameras are its three board views under both
times, so the two sets are compared shot for shot: v2 for the pair itself, v1 and v12 for what the
chain of pairs gains with it.
"""
from scenes import obs_props_lamps_site as base
from scenes.obs_props_lamps_site import BIOME, BIOME_MARGIN, BIOME_MARGIN_Y, build_models, write_pack  # noqa: F401

NEAR_PAIR = True


def build():
    return base.build(near_pair=NEAR_PAIR)


def shots():
    board = set(base.BOARD) | {f"{name}_deep" for name in base.BOARD}
    return [s for s in base.shots() if s["name"] in board]
