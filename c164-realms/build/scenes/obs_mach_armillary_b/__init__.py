"""Version b of the court armillary on the stage of obs_mach_armillary: the same court, the same shots.

Both versions stand on the one cell where the meridian crosses the axis, so they cannot stand side
by side. They are compared picture by picture instead: every shot of this scene has its twin of
the same name in obs_mach_armillary.

    python -m scenes.obs_mach_armillary_b      writes shots.json (a copy of the other scene's)
"""
from scenes.obs_mach_armillary import (BIOME, BIOME_MARGIN, BIOME_MARGIN_Y, TIME, build_models,  # noqa: F401
                                       scene, shots, write_pack)

VERSION = "b"


def build():
    return scene(VERSION)
