"""obs_main_dome with version b of the dome (eight main ribs and flush seams, a slatted curtain that
rolls up into a housing on the crown): kept for the comparison. Every shot has its twin of the same
name in obs_main_dome (version a); shots.json is written by python -m scenes.obs_main_dome.
"""
from scenes import obs_main_dome as base
from scenes.obs_main_dome import BIOME, BIOME_MARGIN, BIOME_MARGIN_Y, build_models, write_pack  # noqa: F401

VERSION = "b"


def build():
    return base.build(VERSION)
