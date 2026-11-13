"""The models of the props/lamps test scene, and how gallery.py lays them out one to a bay."""
from scenes.obs.props import lamps

SCALE = lamps.SCALE
P = lamps.PREFIX


def build_models():
    return lamps.models()


def _wall(name):
    return (name, [(P + name, (0.0, 3.5, -7.49), {})], (1.6, 3.9, -5.0), (0.0, 3.5, -7.2))


def _hung(name):
    return (name, [(P + name, (0.0, 5.0, -5.0), {})], (1.8, 3.6, -2.6), (0.0, 4.2, -5.0))


# name, [(model, offset from the bay's floor centre or None to stand on it, display options)],
# camera, look-at; the backdrop wall is 7.5 blocks north of the bay's centre
GALLERY = [
    ("street", [(P + "street", None, {})], (3.5, 2.8, 5.5), (0.0, 2.8, 0.0)),
    _wall("bracket_a"), _wall("bracket_b"),
    _wall("cage_a"), _wall("cage_b"),
    _hung("pendant_a"), _hung("pendant_b"),
    ("desk_green", [(P + "desk_green", None, {})], (1.2, 1.2, 1.8), (0.0, 0.4, 0.0)),
    _wall("signal"), _wall("signal_off"),
    ("uplight", [(P + "uplight", None, {"yaw": 180.0})], (1.4, 1.2, 1.6), (0.0, 0.3, 0.0)),
    ("festoon", [(P + "wire", (-1.5, 3.0, -3.0), {"yaw": -90.0})]
     + [(P + "bulb", (x, 3.0, -3.0), {"yaw": -90.0}) for x in (-1.0, 0.0, 1.0)]
     + [(P + "hanger", (x, 3.0, -3.0), {"yaw": -90.0}) for x in (-1.5, 1.5)], (1.2, 3.0, -0.6), (0.0, 2.9, -3.0)),
]
