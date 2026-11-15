"""The trial scene of common/export without the look (see scenes/obs_export_probe): the same
platform, pack and models under the vanilla sky, for the pictures of the second trial save (T2).

No BIOME and no mood.py here, so nothing of a registry is written for this scene: the sky is the
game's own at tick 20800, where its moon stands as our look keeps the comet. tools/export.py does
not need this scene: it makes T2 from obs_export_probe with the look switched off.

shots.json is written from shots():  python -m scenes.obs_export_probe_plain  (in build/).
"""
from scenes import obs_export_probe as _probe

BIOME = None
TIME = _probe.TIME_PLAIN
SPAWN = _probe.SPAWN

build = _probe.build
build_models = _probe.build_models
write_pack = _probe.write_pack


def shots():
    return _probe.shots(TIME)
