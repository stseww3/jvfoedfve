"""Director's preview, not for merging: the master scene as it stands with every package branch
merged in (plan: cursor/c164-a0-preview-f427) and the dressing switches on, so the whole site can
be looked at before the packages have passed their reviews one by one."""
from scenes import obs as _obs
from scenes.obs.props import electrics as _electrics
from scenes.obs.props import ironwork as _ironwork
from scenes.obs.props import lamps as _lamps
from scenes.obs.props import signs as _signs
from scenes.obs.sky import lights as _lights

BIOME = _obs.BIOME
BIOME_MARGIN = _obs.BIOME_MARGIN
BIOME_MARGIN_Y = _obs.BIOME_MARGIN_Y

DRESSED = (_electrics, _ironwork, _lamps, _signs, _lights)


def build():
    for module in DRESSED:
        module.DRESS = True
    return _obs.build()


build_models = _obs.build_models
write_pack = _obs.write_pack
