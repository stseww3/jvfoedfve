"""The trial scene of common/export without the look (see scenes/obs_export_probe): the same
platform, pack and models under the vanilla sky, for the pictures of the second trial save (T2).

The sky is the game's own at tick 20370, where its moon stands as our look keeps the comet. The
offline renderer wants a biome to read, so mood.py holds a copy of the game's void biome and
nothing else. This scene is for pictures only and is never placed: tools/export.py makes T2 from
obs_export_probe with the look switched off, and writes nothing of a registry.

shots.json is written from shots():  python -m scenes.obs_export_probe_plain  (in build/).
"""
from scenes import obs_export_probe as _probe

BIOME = "the_void"
TIME = _probe.TIME_PLAIN
SPAWN = _probe.SPAWN

build = _probe.build
build_models = _probe.build_models
write_pack = _probe.write_pack


def shots():
    return _probe.shots(TIME)
