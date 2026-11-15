"""The models the time room's test scene packs: the lamps, the room's own (the world clocks, the
patch cords, the chronometer), the pieces of the other packages the room places as far as those
packages are in the tree, and the linings of the lit windows once materials/windows has them."""
from scenes.obs.interiors import timeroom
from scenes.obs.materials import windows
from scenes.obs.props import lamps


def build_models():
    linings = getattr(windows, "models", dict)
    return {**lamps.models(), **timeroom.models(), **timeroom.their_models(), **linings()}
