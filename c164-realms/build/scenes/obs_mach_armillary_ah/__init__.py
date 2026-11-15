"""Version a of the court armillary with its horizon ring, on the stage of obs_mach_armillary.

Version a stands without the horizon ring: seen along the meridian the ring is a level bar across
the upright one of the meridian ring, a cross (red line). The director ruled that beforehand and
keeps the last word on it; this scene is what he looks at for it: the five shots the question
turns on, each the twin of the shot of the same name in obs_mach_armillary. Once he has ruled, the
scene and armillary.WITH_HORIZON go.

    python -m scenes.obs_mach_armillary_ah      writes shots.json
"""
from scenes.obs.machines import armillary
from scenes.obs_mach_armillary import (BIOME, BIOME_MARGIN, BIOME_MARGIN_Y, TIME, build_models,  # noqa: F401
                                       scene, write_pack)
from scenes.obs_mach_armillary import shots as _shots

VERSION = armillary.WITH_HORIZON
SHOTS = ("v2_axis", "v2_entrance", "meridian", "south_edge", "north_edge")


def build():
    return scene(VERSION)


def shots():
    return [s for s in _shots() if s["name"] in SHOTS]
