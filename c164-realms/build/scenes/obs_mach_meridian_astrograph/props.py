"""The models this test scene shows: the transit circle's and the astrograph's."""
from scenes.obs.machines import astro, meridian


def build_models():
    return {**meridian.models(), **astro.models()}
