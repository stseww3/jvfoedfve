"""Test scene of site/powerhouse, the second of the pair: roof "b", the iron barrel vault, and the
steam main going into the ground at the bridge head as the master scene has it (RUN off).

Everything else, and every camera, is obs_site_powerhouse's: the two sets of pictures are compared
shot for shot.
"""
from scenes import obs_site_powerhouse as base
from scenes.obs_site_powerhouse import BIOME, BIOME_MARGIN, BIOME_MARGIN_Y, build_models, write_pack  # noqa: F401

VERSION = "b"
RUN = False


def build():
    return base.build(VERSION, RUN)
