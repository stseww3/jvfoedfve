"""The models of the props/paper test scene: the paper family and the lamps that light the corner."""
from scenes.obs.props import lamps, paper

SCALE = {**lamps.SCALE, **paper.SCALE}


def build_models():
    return {**lamps.models(), **paper.models()}
