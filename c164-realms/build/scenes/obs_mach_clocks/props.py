"""The models of the machines/clock test scene: the clocks', and the radio mast's when it is in the tree."""
from scenes.obs.machines import clock

try:
    from scenes.obs.machines import mast as radiomast
except ImportError:
    radiomast = None


def build_models():
    out = clock.models()
    if radiomast is not None:
        out.update(radiomast.models())
    return out
