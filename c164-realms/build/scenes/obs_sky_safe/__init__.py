"""obs_sky_safe: the whole observatory in a world without registry files (card sky/safe-look).

Realms takes no map whose data pack holds registry files. This scene is the master scene `obs`
as such a map has it: no biome and no timeline of ours (mood.py is empty, so place.py removes the
look's files from the data pack), the plot filled with a vanilla biome, the clock stopped where
the vanilla moon stands in the comet's place, and the look carried by the resource pack: the core
shaders sky/_shaders.py writes from mood.LOOKS.

The pictures are four of the board's views, to be laid beside the board's own from `obs` under the
registry look: V1 (the arrival), V2 (the axis), V4 (the entrance) and V12 (from above). Two more
look out over the cloud sea from where people stand, west into the afterglow and east away from
it: where the blocks end (160 away) nothing may be seen to end.
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
    out = [dict(shot, time=look.LOCK_TICK) for shot, _, _ in boardshots.views() if keys[shot["name"]] in VIEWS]
    west = obs_skeleton().SUNSET_PLATFORM["centre"]
    out.append(dict(name="sea_west", pos=[west[0] - 18.5, 1.62, west[1] + 0.5], look_at=[west[0] - 180.0, -16.0, west[1] + 12.0],
                    time=look.LOCK_TICK))
    out.append(dict(name="sea_east", pos=[obs_skeleton().LOWER_PLATFORM[2] - 1.5, obs_skeleton().LOWER_GROUND + 1.62, 0.5], look_at=[obs_skeleton().LOWER_PLATFORM[2] + 170.0, -24.0, 24.0],
                    time=look.LOCK_TICK))
    return out


def obs_skeleton():
    from scenes.obs.common import skeleton
    return skeleton
