"""The models of the props/pipes test scene, and how gallery.py lays them out one group to a bay."""
from artkit import models as M
from scenes.obs.props import pipes

SCALE = pipes.SCALE
P = pipes.PREFIX

WALL = -7.49                            # just clear of the backdrop, 7.5 blocks north of a bay's centre
OUT = (pipes.GAP + pipes.DOWN_R) / 16.0                 # a downpipe's axis off the wall behind it
LONG = pipes.RUN / 16.0                 # a run's model at scale 1: three blocks, along its +z
UP, DOWN = {"turns": (("x", -90.0),)}, {"turns": (("x", 90.0),)}       # a model's +z stood up, hung down
EAST, WEST = {"turns": (("y", 90.0),)}, {"turns": (("y", -90.0),)}     # a model's +z laid to the east, the west
BACK = {"turns": (("y", 180.0),)}       # and turned to the north


def build_models():
    return pipes.models()


def _gauge_at(pos, how):
    """The gauge whose tapping is at pos, shown with the turns of `how`, and its needle at rest (a
    piece of its own: pipes.gauge() places the two and has the needle tremble)."""
    q = M.IDENT
    for axis, deg in how["turns"]:
        q = M._qmul(M.quat(axis, deg), q)
    d = M._qrot(q, (pipes.GAUGE_FACE / 16.0, pipes.GAUGE_DIAL / 16.0, 0.0))
    return [(P + "gauge", pos, how),
            (P + "gauge_needle", tuple(pos[i] + d[i] for i in range(3)),
             {"turns": (("x", pipes.NEEDLE_REST),) + tuple(how["turns"])})]


def _wall(name, pieces, y=1.5, back=3.0):
    """Wall pieces against the backdrop: [(model, across, height)]; the camera stands `back` blocks
    off the wall and looks at height y."""
    return (name, [(P + n, (x, h, WALL), {}) for n, x, h in pieces], (1.4, y + 0.4, WALL + back), (0.0, y, WALL))


def _downpipe():
    """A whole downpipe, three blocks of it: the hopper, the pipe hung from its socket down to a
    sleeve on the floor, a clip half way."""
    top = LONG - (pipes.HOPPER_SOCKET[0] + 1.5) / 16.0  # the hopper's anchor: the pipe starts 1.5 texels up its socket
    return ("downpipe", [(P + "down_hopper_right", (0.0, top, WALL), {}),
                         (P + "down", (0.0, LONG, WALL + OUT), DOWN),
                         (P + "down_clip", (0.0, 1.5, WALL), {}),
                         (P + "down_sleeve", (0.0, 0.01, WALL + OUT), UP)],
            (1.9, 2.2, WALL + 4.2), (0.0, 1.9, WALL))


def _drain():
    """A whole iron drain, three blocks of it: the head (its nozzle comes out of a gutter that is not
    there), the pipe hung from its socket down to a collar on the floor, a clip half way."""
    top = LONG - (pipes.DRAIN_SOCKET[0] + 1.5) / 16.0   # the head's anchor: the pipe starts 1.5 texels up its socket
    return ("drain", [(P + "drain_head", (0.0, top, WALL), {}),
                      (P + "drain", (0.0, LONG, WALL + OUT), DOWN),
                      (P + "drain_clip", (0.0, 1.5, WALL), {}),
                      (P + "drain_sleeve", (0.0, 0.01, WALL + OUT), UP)],
            (1.9, 2.2, WALL + 4.2), (0.0, 1.9, WALL))


def _mains():
    """The two bores side by side along the floor, each with a pair of flanges half way, and beside
    them the small copper pipe with its union."""
    parts = []
    for size, x in (("l", -0.5), ("m", 0.5)):
        y = (pipes.BORE[size] + 2.0) / 16.0             # the flanges stand on the floor
        parts += [(P + "main_" + size, (x, y, -LONG / 2.0), {}), (P + "flange_" + size, (x, y, 0.0), {})]
    y = (pipes.FINE_R + 1.0) / 16.0                     # and so does the union's nut
    parts += [(P + "fine", (1.2, y, -LONG / 2.0), {}), (P + "union", (1.2, y, 0.0), {})]
    return ("mains", parts, (2.4, 1.5, 1.6), (0.0, 0.2, 0.0))


def _clips():
    """The two brackets on the wall, each holding its run."""
    parts = []
    for size, y in (("l", 2.2), ("m", 1.2)):
        parts += [(P + "clip_" + size, (0.0, y, WALL), {}),
                  (P + "main_" + size, (-LONG / 2.0, y, WALL + pipes.STANDOFF[size] / 16.0), EAST)]
    return ("clips", parts, (1.6, 2.1, WALL + 3.2), (0.0, 1.7, WALL))


def _elbows():
    """The two bends, each with one leg up and one to the camera."""
    return ("elbows", [(P + "elbow_l", (-0.6, 0.8, 0.0), {}), (P + "elbow_m", (0.6, 0.8, 0.0), {})],
            (1.2, 1.5, 2.2), (0.0, 1.0, 0.2))


def _tees():
    """The two tees, the run from west to east, the branch up."""
    return ("tees", [(P + "tee_l", (-0.7, 0.8, 0.0), EAST), (P + "tee_m", (0.7, 0.8, 0.0), EAST)],
            (0.6, 1.4, 2.2), (0.0, 0.9, 0.0))


def _expansions():
    """The two expansion bends, the run from west to east, the loop up."""
    return ("expansions", [(P + "expansion_l", (0.0, 1.7, 0.0), EAST), (P + "expansion_m", (0.0, 0.5, 0.0), EAST)],
            (0.8, 1.6, 3.4), (0.0, 1.4, 0.0))


def _valves():
    """The straight stop valve in both bores, each in a run that crosses the bay."""
    parts = []
    for size, z in (("l", -0.8), ("m", 0.8)):
        parts += [(P + "main_" + size, (-LONG / 2.0, 1.0, z), EAST), (P + "valve_" + size, (0.0, 1.0, z), EAST)]
    return ("valves", parts, (1.3, 1.9, 3.0), (0.0, 1.0, 0.0))


def _angles():
    """The angle valve in both bores, standing on the floor, the wheels to the camera."""
    y = pipes.ANGLE / 16.0
    return ("valve_angles", [(P + "valve_angle_l", (-0.6, y, 0.0), BACK), (P + "valve_angle_m", (0.6, y, 0.0), BACK)],
            (0.9, 1.1, 2.0), (0.0, 0.5, 0.0))


def _inlet():
    """The inlet as pipes.inlet() builds it, with the backdrop for the grating: the plate, the short
    length with the gauge, the angle valve on the floor with its wheel towards the camera. The run
    is not drawn out here: it starts behind the backdrop and comes through it."""
    y = pipes.ANGLE / 16.0
    end = (pipes.INLET_VALVE - pipes.ANGLE + 1.0) / 16.0        # where the run stops, inside the valve's flanges
    return ("inlet", [(P + "plate_l", (0.0, y, WALL), {}),
                      (P + "main_l", (0.0, y, WALL + end - LONG), {}),
                      *_gauge_at((0.0, y + pipes.BORE["l"] / 16.0, WALL + pipes.INLET_GAUGE / 16.0), BACK),
                      (P + "valve_angle_l", (0.0, y, WALL + pipes.INLET_VALVE / 16.0), BACK)],
            (-1.7, 1.3, WALL + 2.7), (0.0, 0.6, WALL + 0.8))


def _gauge():
    """The gauge on a run that crosses the bay, its dial to the camera."""
    y = 1.0
    return ("gauge", [(P + "main_l", (-LONG / 2.0, y, 0.0), EAST),
                      *_gauge_at((0.0, y + pipes.BORE["l"] / 16.0, 0.0), WEST)],
            (0.5, 1.7, 1.8), (0.0, 1.5, 0.0))


def _band():
    """The strap for a main laid in blocks, stood up as round a block that is not there."""
    return ("band", [(P + "band", (0.0, 17.0 / 16.0 + 0.01, 0.0), UP)], (1.5, 1.4, 2.2), (0.0, 0.5, 0.0))


# name, [(model, offset from the bay's floor centre or None to stand on it, display options)],
# camera, look-at; the backdrop wall is 7.5 blocks north of the bay's centre
GALLERY = [
    _downpipe(),
    _wall("hoppers", [("down_hopper_left", -0.7, 2.0), ("down_hopper_right", 0.7, 2.0)], y=2.0),
    _wall("down_fixings", [("down_clip", -0.5, 1.6), ("down_sleeve", 0.5, 1.6)], y=1.6, back=2.2),
    _drain(),
    _mains(),
    _wall("plates", [("plate_l", -0.6, 1.5), ("plate_m", 0.6, 1.5)]),
    _clips(),
    _elbows(),
    _tees(),
    _expansions(),
    _valves(),
    _angles(),
    _inlet(),
    _gauge(),
    _wall("bonnet", [("bonnet", 0.0, 1.5)], back=2.6),
    _band(),
]
