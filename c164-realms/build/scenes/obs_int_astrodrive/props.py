from scenes.obs.interiors import _astrodrive
from scenes.obs.machines import astro


def build_models():
    return {**astro.models(), **_astrodrive.models()}
