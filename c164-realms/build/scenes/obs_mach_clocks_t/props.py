"""The models of the trial scene: the tower scene's, the clocks' and the radio mast's."""
from scenes import obs_main_tower as base
from scenes.obs.machines import clock
from scenes.obs.machines import mast as radiomast


def build_models():
    out = dict(base.build_models())
    out.update(clock.models())
    out.update(radiomast.models())
    return out
