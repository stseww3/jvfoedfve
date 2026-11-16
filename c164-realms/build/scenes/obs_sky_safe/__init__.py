"""obs_sky_safe: the whole observatory in a world without registry files (card sky/safe-look).

Realms takes no map whose data pack holds registry files. This scene is the master scene `obs`
as such a map has it: no biome and no timeline of ours (mood.py is empty, so place.py removes the
look's files from the data pack), the plot filled with a vanilla biome, the clock stopped where
the vanilla moon stands in the comet's place, and the look carried by the resource pack: the core
shaders sky/_shaders.py writes from mood.LOOKS.

The pictures are four of the board's views, to be laid beside the board's own from `obs` under the
registry look: V1 (the arrival), V2 (the axis), V4 (the entrance) and V12 (from above).
"""
import os
import sys

from scenes import obs
from scenes.obs.sky import _shaders
from scenes.obs.sky import mood as look

ORIGIN = obs.ORIGIN
BIOME = "minecraft:the_void"        # no weather, nothing spawns; its colours of water and grass are the game's
BIOME_MARGIN = obs.BIOME_MARGIN
BIOME_MARGIN_Y = obs.BIOME_MARGIN_Y
VIEWS = ("V1", "V2", "V4", "V12")


def build():
    return obs.build()


def build_models():
    return obs.build_models()


def write_pack(pack_dir):
    return list(obs.write_pack(pack_dir) or []) + _shaders.pack(pack_dir)


def shots():
    """The board's views of VIEWS, at the hour the clock is stopped at."""
    tools = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "tools"))
    if tools not in sys.path:
        sys.path.insert(0, tools)
    import boardshots
    keys = {name: key for name, _, key, _ in boardshots.VIEWS}
    return [dict(shot, time=look.LOCK_TICK) for shot, _, _ in boardshots.views() if keys[shot["name"]] in VIEWS]
