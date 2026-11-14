"""The models this scene shows: the lamps of props/lamps (the wall wash's projector is one of them)."""
from scenes.obs.props import lamps


def build_models():
    return lamps.models()
