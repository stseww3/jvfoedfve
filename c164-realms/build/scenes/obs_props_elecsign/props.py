"""The models of the props/electrics-signs test scene, and how gallery.py lays them out one to a bay."""
from scenes.obs.props import electrics, lamps, signs

SCALE = {**lamps.SCALE, **signs.SCALE, **electrics.SCALE}
G, E = signs.PREFIX, electrics.PREFIX
WALL_Z = -7.49                  # a wall piece hangs on the backdrop, 7.5 blocks north of the bay's centre
UP = {"turns": (("x", -90.0),)}     # a drawn piece (it runs along +z from its anchor) set on end
ALONG = {"yaw": -90.0}              # ... and laid along +x, from its anchor to the right of the camera


def build_models():
    """The package's own models, and those of props/lamps: the scene hangs the entrance's lamps."""
    return {**lamps.models(), **signs.models(), **electrics.models()}


def _hung(name, model, y=3.5, cam=(1.6, 3.9, -5.0)):
    """One wall piece on the backdrop, its anchor y over the floor."""
    return (name, [(model, (0.0, y, WALL_Z), {})], cam, (0.0, y, WALL_Z + 0.3))


def _plates():
    """Every blue plate: the numbers in two rows of six, under them the arrows and the letters."""
    parts = []
    for i in range(12):
        at = (-2.25 + 0.9 * (i % 6), 4.3 - 0.8 * (i // 6), WALL_Z)
        parts.append((G + signs.plate_name(str(i + 1)), at, {}))
    for i, label in enumerate(("<", ">", "N", "S")):
        parts.append((G + signs.plate_name(label), (-1.35 + 0.9 * i, 2.7, WALL_Z), {}))
    return parts


def _line(y=4.0):
    """A line of two spans as electrics.run() strings it: a lead-in at each end over its elbow, an
    insulator between them, the wire from one to the next (a span is the cable's own 48 px)."""
    wire = WALL_Z + electrics.WIRE_OUT
    parts = [(E + "insulator", (0.0, y - electrics.WIRE_UP, WALL_Z), {})]
    for x in (-3.0, 3.0):
        parts.append((E + "lead_in", (x, y, WALL_Z), {}))
        parts.append((E + "elbow", (x, y - electrics.LEAD_DOWN, WALL_Z), {}))
    for x in (-3.0, 0.0):
        parts.append((E + "cable", (x, y, wire), ALONG))
    return parts


def _riser(y=1.5):
    """A junction box, the conduit that climbs out of it (its own 48 px, three blocks) held by a
    clip to the block, and the lead-in on top: the end ("box", y) of electrics.run()."""
    foot = y + electrics.BOX_UP
    top = foot + 3.0
    parts = [(E + "junction_box", (0.0, y, WALL_Z), {}),
             (E + "conduit", (0.0, foot, WALL_Z + electrics.AXIS_OUT), UP),
             (E + "lead_in", (0.0, top + electrics.LEAD_DOWN, WALL_Z), {})]
    for j in range(3):
        parts.append((E + "clip", (0.0, foot + 3.0 * (j + 1) / 4.0, WALL_Z), {}))
    return parts


def _flagpole():
    """The pole as signs.flagpole() builds it, three blocks of pole between foot and head (the
    pole's own 48 px), the flag under the ball. The cloth flies east here, its front to the camera."""
    head = signs.POLE_FOOT + 3.0
    return [(G + "pole_foot", None, {}),
            (G + "pole", (0.0, signs.POLE_FOOT, 0.0), UP),
            (G + "pole_head", (0.0, head, 0.0), {}),
            (G + "flag", (0.0, head + signs.POLE_HEAD - 0.25, 0.0), {})]


GREAT = (0.0, 4.0, WALL_Z)      # the great pieces: three blocks across, their middle four blocks up
VOLTS = [(G + "plate_220v", (-1.0, 3.5, WALL_Z), {}), (G + "plate_110v", (1.0, 3.5, WALL_Z), {})]
LEAD_IN = [(E + "lead_in", (0.0, 3.5, WALL_Z), {}), (E + "elbow", (0.0, 3.5 - electrics.LEAD_DOWN, WALL_Z), {})]
CLIP = [(E + "clip", (0.0, 3.5, WALL_Z), {}), (E + "conduit", (0.0, 2.0, WALL_Z + electrics.AXIS_OUT), UP)]
PHONE = [(E + "wall_phone", (0.0, 2.8, WALL_Z), {})]       # hung by its foot: its middle is at 3.5

# name, [(model, offset from the bay's floor centre or None to stand on it, display options)],
# camera, look-at; the backdrop wall is 7.5 blocks north of the bay's centre
GALLERY = [
    _hung("emblem", G + "emblem", cam=(1.2, 3.8, -5.6)),
    ("great_emblem", [(G + "great_emblem", GREAT, {})], (0.0, 4.0, -1.0), GREAT),
    ("great_emblem_side", [(G + "great_emblem", GREAT, {})], (4.6, 3.0, -3.2), GREAT),
    ("great_clock", [(G + "great_clock", GREAT, {})], (0.0, 4.0, -1.0), GREAT),
    ("plates", _plates(), (0.0, 3.5, -4.4), (0.0, 3.5, WALL_Z)),
    ("plates_volt", VOLTS, (0.0, 3.6, -5.4), (0.0, 3.5, WALL_Z)),
    ("station_board", [(G + "station_board", (0.0, 3.5, WALL_Z), {})], (0.0, 3.6, -4.9), (0.0, 3.5, WALL_Z)),
    ("line", _line(), (0.0, 3.9, -3.3), (0.0, 3.8, WALL_Z)),
    ("riser", _riser(), (1.9, 3.2, -3.6), (0.0, 3.2, WALL_Z)),
    _hung("insulator", E + "insulator", cam=(0.9, 3.8, -6.3)),
    ("lead_in", LEAD_IN, (0.9, 3.7, -6.3), (0.0, 3.4, -7.3)),
    _hung("junction_box", E + "junction_box", cam=(1.1, 3.8, -6.0)),
    ("clip", CLIP, (0.7, 3.7, -6.6), (0.0, 3.5, -7.4)),
    _hung("bell", E + "bell", cam=(1.2, 3.9, -5.8)),
    ("wall_phone", PHONE, (1.5, 3.7, -5.3), (0.0, 3.5, -7.2)),
    ("wall_phone_left", PHONE, (-1.5, 3.4, -5.6), (0.0, 3.5, -7.2)),
    ("telegraph_key", [(E + "telegraph_key", None, {})], (0.6, 0.55, 0.8), (0.0, 0.12, 0.0)),
    ("flagpole", _flagpole(), (2.5, 2.6, 6.5), (0.4, 2.5, 0.0)),
    ("flag", [(G + "flag", (-0.8, 3.3, 0.0), {})], (0.0, 2.9, 2.6), (0.0, 2.8, 0.0)),
    ("flag_back", [(G + "flag", (0.8, 3.3, 0.0), {"yaw": 180.0})], (0.0, 2.9, 2.6), (0.0, 2.8, 0.0)),
]
