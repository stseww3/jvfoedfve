"""The models of the props/steam-mains test scene, and how gallery.py lays them out one group to a bay.
The fittings of the main are the pipework family's: its own gallery shows them (obs_props_pipes)."""
from scenes.obs.props import lamps, pipes
from scenes.obs.props import steam_mains as steam

SCALE = {**pipes.SCALE, **{name: 1.0 for name in steam.models()}}
P = steam.PREFIX

WEST = {"turns": (("y", -90.0),)}       # a piece's +z laid to the west: the side that looks away from its wall
#                                         then looks south, at the camera


def build_models():
    """The package's models, the pipework family's, and the projector of the light line's wall wash,
    which stands at the foot of two pilasters of this stretch (sky/lights)."""
    wash = lamps.PREFIX + "uplight"
    return {**pipes.models(), **steam.models(), wash: lamps.models()[wash]}


def _bay():
    """A bay of the main: the plates, the bolted joint with the ring beside it, the two brackets."""
    return ("bay", [(P + "bay", (0.0, 1.0, 0.0), WEST)], (0.7, 1.5, 2.9), (0.0, 0.95, 0.0))


def _valve():
    """The bay with the stop valve and the steam trap; the main lies as far over the floor as the
    trap's foot is under it."""
    y = -steam.TRAP_FOOT / 16.0
    return ("valve", [(P + "valve", (-0.3, y, 0.0), WEST)], (0.5, 1.5, 2.3), (0.0, 0.6, 0.2))


def _loop():
    """The expansion bend, seen from above the side that looks away from the wall."""
    return ("loop", [(P + "loop", (-1.3, 1.0, 0.0), WEST)], (0.9, 2.3, 2.9), (0.0, 0.9, 0.5))


def _end():
    """The end of the stretch: the ring, the bend, the plate on the wall it goes into."""
    return ("end", [(P + "end", (0.3, 1.0, 0.0), WEST)], (1.0, 1.6, 1.9), (0.0, 0.95, -0.1))


# name, [(model, offset from the bay's floor centre or None to stand on it, display options)],
# camera, look-at; the backdrop wall is 7.5 blocks north of the bay's centre
GALLERY = [_bay(), _valve(), _loop(), _end()]
