"""The models of the props/instruments test scene, and how gallery.py lays them out one to a bay."""
from scenes.obs.props import instruments, lamps

SCALE = {**lamps.SCALE, **instruments.SCALE}
P = instruments.PREFIX


def build_models():
    """The instruments, and the lamps that light the stage."""
    return {**lamps.models(), **instruments.models()}


# name, [(model, offset from the bay's floor centre or None to stand on it, display options)],
# camera, look-at; the backdrop wall is 7.5 blocks north of the bay's centre
GALLERY = [
    ("tripod_scope", [(P + "tripod_scope", None, {"yaw": -90.0})], (1.6, 1.8, 2.6), (0.0, 1.3, 0.0)),
    ("celestial_globe", [(P + "celestial_globe", None, {})], (1.4, 1.8, 2.4), (0.0, 1.1, 0.0)),
]
