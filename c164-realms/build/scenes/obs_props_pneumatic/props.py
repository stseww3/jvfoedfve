"""The models the test scene of props/pneumatic packs: what the time room's own test scene packs,
and the family's."""
from scenes.obs.props import pneumatic
from scenes.obs_int_timeroom import props as room


def build_models():
    return {**room.build_models(), **pneumatic.models()}
