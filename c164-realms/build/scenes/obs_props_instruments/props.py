"""The models of the props/instruments test scene, and how gallery.py lays them out one to a bay."""
from scenes.obs.props import instruments, lamps

try:                                    # see the scene: the furniture is used once it is merged
    from scenes.obs.props import furniture
except ImportError:
    furniture = None

SCALE = {**lamps.SCALE, **instruments.SCALE, **(getattr(furniture, "SCALE", None) or {})}
P = instruments.PREFIX
WALL_Z = -7.49                          # the backdrop wall is 7.5 blocks north of a bay's centre


def build_models():
    """The instruments, the lamps that light the stage and, when it is in the tree, the furniture
    that gives the scale."""
    out = {**lamps.models(), **instruments.models()}
    if furniture is not None:
        out.update(furniture.models())
    return out


def _floor(name, height, turn=0.0):
    """A standing piece `height` blocks tall, seen from a little above its middle."""
    return (name, [(P + name, None, {"yaw": turn})], (0.9 + height * 0.5, height * 0.75 + 0.5, 1.2 + height),
            (0.0, height * 0.5, 0.0))


def _wall(name, foot, more=()):
    """A wall piece two blocks tall, its foot `foot` blocks up the backdrop."""
    return (name, [(P + name, (0.0, foot, WALL_Z), {})] + list(more), (1.0, foot + 1.3, -4.6), (0.0, foot + 1.0, -7.3))


def _edge_on(name, away):
    """The celestial globe turned so that the camera stands in the plane of its half meridian: one
    upright line under the level band of the horizon ring, none above it (red line 8, near and far)."""
    turned = {"yaw": instruments.GLOBE_YAW - 90.0}
    return (name, [(P + "celestial_globe", None, turned)], (0.0, 1.62, away), (0.0, 1.1, 0.0))


def _from_behind(name, away):
    """The comet's telescope seen from behind, as from the walk that leads up to it: the tube stands
    over the fork and the tripod (red line 8, near and far)."""
    return (name, [(P + "tripod_scope_comet", None, {"yaw": 180.0})], (0.0, 1.62, away), (0.0, 1.5, 0.0))


_PIVOT = instruments.PENDULUM["pivot"]
_PENDULUM = (P + "regulator_pendulum", (_PIVOT[0], 0.5 + _PIVOT[1], WALL_Z + _PIVOT[2]), {})

# name, [(model, offset from the bay's floor centre or None to stand on it, display options)],
# camera, look-at
GALLERY = [
    _floor("tripod_scope", 2.0, turn=-90.0),
    _floor("tripod_scope_comet", 2.4, turn=-90.0),
    _from_behind("tripod_scope_comet_behind", 4.0),
    _from_behind("tripod_scope_comet_behind_far", 10.0),
    _floor("celestial_globe", 2.0),
    _edge_on("celestial_globe_edge", 3.5),
    _edge_on("celestial_globe_edge_far", 9.0),
    _floor("globe", 1.0),
    _floor("sextant", 1.0),
    _wall("barometer", 1.0),
    _floor("louvre_box", 2.0),
    _wall("regulator_clock", 0.5, more=[_PENDULUM]),
    _floor("calc_machine", 0.6),
    _floor("sunshine_recorder", 0.6),
]
