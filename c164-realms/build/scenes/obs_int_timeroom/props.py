"""The models the time room's test scene packs: the lamps, and the pieces of the other packages
the room places, as far as those packages are in the tree."""
from scenes.obs.interiors import timeroom
from scenes.obs.props import lamps


def build_models():
    return {**lamps.models(), **timeroom.their_models()}
