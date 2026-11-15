"""The models the test scene of the time room shows: the lamps of props/lamps."""
from scenes.obs.props import lamps

SCALE = lamps.SCALE


def build_models():
    return lamps.models()
