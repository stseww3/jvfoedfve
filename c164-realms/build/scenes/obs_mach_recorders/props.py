"""The models the test scene of machines/recorders packs: what the time room's own test scene packs,
and the recorders'."""
from scenes.obs.machines import rec
from scenes.obs_int_timeroom import props as room


def build_models():
    return {**room.build_models(), **rec.models()}
