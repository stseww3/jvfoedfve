"""The models the test scene of the plate vault shows: the room's own and the lamps of props/lamps."""
from scenes.obs.interiors import platevault
from scenes.obs.props import lamps

SCALE = dict(lamps.SCALE)


def build_models():
    out = dict(lamps.models())
    out.update(platevault.models())
    return out
