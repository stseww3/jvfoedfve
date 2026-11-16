"""The models the battery room's test scene packs: the room's own (the battery, the gantries, the
cable, the small pieces) and the pieces of the other packages it places (the switchboard and its
bars, the lamps)."""
from scenes.obs.interiors import batteryroom


def build_models():
    return {**batteryroom.their_models(), **batteryroom.models()}
