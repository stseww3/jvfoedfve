"""The models of the props/steam-mains test scene, and how gallery.py lays them out one group to a bay.
The fittings of the main are the pipework family's: its own gallery shows them (obs_props_pipes)."""
from scenes.obs.props import pipes, steam

SCALE = {**pipes.SCALE, **{name: 1.0 for name in steam.models()}}
P = steam.PREFIX

LONG = pipes.RUN / 16.0                 # a length's model at scale 1: three blocks, along its +z
EAST = {"turns": (("y", 90.0),)}        # a model's +z laid to the east
SOUTH = {}                              # and left as it is built: its +z to the south, towards the camera


def build_models():
    return {**pipes.models(), **steam.models()}


def _main():
    """A length of the copper main beside a length of the iron one, with a bolted joint each."""
    return ("main", [(P + "main", (-LONG / 2.0, 1.3, 0.0), EAST), (pipes.PREFIX + "flange_l", (0.0, 1.3, 0.0), EAST),
                     (pipes.PREFIX + "main_l", (-LONG / 2.0, 0.6, 0.0), EAST),
                     (pipes.PREFIX + "flange_l", (0.0, 0.6, 0.0), EAST)],
            (0.9, 1.5, 2.6), (0.0, 0.95, 0.0))


def _trap():
    """The steam trap on a length of the main that crosses the bay, the pot towards the camera; the
    main lies as far over the floor as the trap's foot is under it."""
    y = -steam.TRAP_FOOT / 16.0
    return ("trap", [(P + "main", (-LONG / 2.0, y, 0.0), EAST), (P + "trap", (0.0, y, 0.0), SOUTH)],
            (0.9, 1.3, 1.9), (0.0, 0.5, 0.2))


# name, [(model, offset from the bay's floor centre or None to stand on it, display options)],
# camera, look-at; the backdrop wall is 7.5 blocks north of the bay's centre
GALLERY = [_main(), _trap()]
