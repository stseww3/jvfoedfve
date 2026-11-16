"""The models the battery room's test scene packs: the room's own (the battery, the gantries, the
stand-ins of the bus bars and of the switchboard) and the pieces of the other packages it places."""
from scenes.obs.interiors import batteryroom


def build_models():
    return {**batteryroom.their_models(), **batteryroom.models()}
