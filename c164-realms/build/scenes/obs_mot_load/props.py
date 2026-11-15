"""The one model of the load scene (card motion/loop): a small wheel, centred on its axis, so it
turns a quarter of a turn to the step. It is this scene's own and not meant for the map."""
import functools

from artkit import models as M

from scenes.obs.common import palette as P

PREFIX = "mot_"


@functools.lru_cache(maxsize=None)
def _models():
    m = M.Model(PREFIX + "load_cog")
    m.tube("z", (0.0, 0.0), -1.0, 1.0, 5.0, P.mat("iron"))
    m.tube("z", (0.0, 0.0), 1.0, 1.5, 1.5, P.mat("iron_dark"))
    m.box((-0.5, 1.5, 1.0), (0.5, 4.5, 1.5), P.mat("brass"), grain="y")     # a mark, to see it go round
    return {m.name: m}


def model(name):
    return _models()[PREFIX + name]


def build_models():
    return dict(_models())
