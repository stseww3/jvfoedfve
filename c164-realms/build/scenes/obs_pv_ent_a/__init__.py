"""Director's preview, not for merging: the master scene with version A of the entrance."""
from scenes import obs as _obs
from scenes.obs.main import facade as _facade

BIOME = _obs.BIOME
BIOME_MARGIN = _obs.BIOME_MARGIN
BIOME_MARGIN_Y = _obs.BIOME_MARGIN_Y


def build():
    _facade.ENTRANCE = "A"
    return _obs.build()


build_models = _obs.build_models
write_pack = _obs.write_pack
