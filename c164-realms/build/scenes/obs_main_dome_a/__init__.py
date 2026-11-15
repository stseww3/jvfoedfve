"""obs_main_dome with version a of the dome (twenty flush seams, their feet stained, two leaves that
part sideways): the version the map is not built with, kept for the comparison. Every shot has its
twin of the same name in obs_main_dome (the map's version, b); shots.json is written by
python -m scenes.obs_main_dome.
"""
from scenes import obs_main_dome as base
from scenes.obs_main_dome import BIOME, BIOME_MARGIN, BIOME_MARGIN_Y, build_models, write_pack  # noqa: F401

VERSION = "a"


def build():
    return base.build(VERSION)
