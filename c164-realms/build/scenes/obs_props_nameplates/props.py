"""The models of the props/nameplates test scene: every plate of the station's table."""
from scenes.obs.props import nameplates

SCALE = dict(nameplates.SCALE)


def build_models():
    return nameplates.models()
