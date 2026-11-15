"""The models of the props/ironwork test scene, and how gallery.py lays them out one to a bay."""
from scenes.obs.props import ironwork

SCALE = ironwork.SCALE
P = ironwork.PREFIX


def build_models():
    return ironwork.models()


def _wall(name, y):
    """A wall piece against the backdrop, its foot y blocks up."""
    return (name, [(P + name, (0.0, y, -7.49), {})], (1.8, y + 1.0, -4.0), (0.0, y + 1.0, -7.2))


def _tall(name):
    """A six-block arched window: the camera stands well back to frame it whole."""
    return (name, [(P + name, (0.0, 0.5, -7.49), {})], (0.0, 3.5, -0.5), (0.0, 3.5, -7.2))


def _floor(name):
    return (name, [(P + name, None, {})], (1.4, 1.4, 2.0), (0.0, 0.6, 0.0))


# name, [(model, offset from the bay's floor centre or None to stand on it, display options)],
# camera, look-at; the backdrop wall is 7.5 blocks north of the bay's centre
GALLERY = [
    _tall("window_arch"), _tall("window_arch_2"),
    _wall("window_grille", 2.0), _wall("window_grille_2", 2.0),
    _tall("door_frame"), _wall("door_leaf", 0.5), _tall("gate"), _wall("glazed_leaf", 0.5),
    _wall("canopy", 4.0), _wall("canopy_lamp", 3.0),
    _floor("railing_panel"),
    _wall("ladder", 0.5), _wall("ladder_cage", 0.5),
    _floor("vent_cowl"),
    _floor("grate_hatch"),
]
