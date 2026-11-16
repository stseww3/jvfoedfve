"""The models of the props/bells test scene: the bell's, and the lamp it hangs over."""
from scenes.obs.props import bells, lamps

SCALE = {**lamps.SCALE, **bells.SCALE}


def build_models():
    return {**lamps.models(), **bells.models()}
