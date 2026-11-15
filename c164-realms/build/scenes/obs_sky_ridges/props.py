"""The models this scene shows: the ridge panels of sky/ridges."""
from scenes.obs import sky


def build_models():
    return {**(sky.models() or {})}
