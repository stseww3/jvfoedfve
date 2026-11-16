"""Test scene of the work package site/powerhouse (plan/packages/site/powerhouse.md).

The power house where it stands in the master scene: the terraces, the lower platform and the
retaining wall round it as the site line has them, the main building behind the court (the white
model until the main line's shell is merged), the props line's things, the sky line's light sources
last. The lines are built whole, in the master scene's order, so the picture keeps up with them as
their packages are merged.

Two roofs are to be compared (INTERFACE: a package with versions shows them side by side). They
stand on the same walls in the same place, so they are shown from the same cameras in twin scenes:

    obs_site_powerhouse     roof "a", the saw teeth; the main laid on along the upper terrace (RUN on)
    obs_site_powerhouse_b   roof "b", the iron vault; the main into the ground at the bridge head,
                            as the master scene has it (RUN off)

so the same pair of pictures also shows the terrace with and without the run.

Both show what the finished site has round the house and the props line still keeps behind its
switch: the fittings on the bridge and the gutter's pipes (powerhouse.FITTINGS, DRAINS), which
appear once their package is in the tree. The lamps of the site are the props line's own by now
(props/lamps.DRESS): the street lamps of the way in, two of which stand in the yard before the
house, and the low lamps on the terrace's lip.

The cameras are VIEWS; the two that the skeleton locks are read from it (S.V6, the power house
from the grand stair, here stair_south; S.V1, the arrival), so they turn when it turns them.

    python -m scenes.obs_site_powerhouse      (in build/) writes shots.json for both scenes
"""
import contextlib

from artkit.canvas import Canvas

from scenes.obs import main, materials, props, site, sky
from scenes.obs.common import skeleton as S
from scenes.obs.site import powerhouse

BIOME = "obs_blue"
BIOME_MARGIN = 100
BIOME_MARGIN_Y = 150
LINES = (site, main, props, sky)
VERSION = "a"
RUN = True
FIRE = True     # both scenes: the boiler bays glow through the fire window, as the card wants them judged

TIME = 14000
LOW = S.LOWER_GROUND + S.EYE        # -4.38: the eye of a person on the lower platform
HIGH = S.GROUND + S.EYE             # 1.62: on the upper terrace
VIEWS = [
    ("door_axis", (74.5, LOW, 2.5), (78.5, 6.0, 31.5)),             # on the door's axis, from the yard's north edge
    ("yard_west", (63.5, LOW, 12.5), (78.0, 4.0, 31.0)),            # the north-west corner, from south of the stair
    ("stair_south", S.V6["pos"], S.V6["look_at"]),                  # the locked view of the house
    ("stair_axis", (66.5, S.V6["pos"][1], 0.5), (76.5, 8.0, 32.5)), # the same tread, on the stair's axis
    ("v1", S.V1["pos"], S.V1["look_at"]),                           # the arrival: the bridge must not touch the main building
    ("court_back", (46.5, HIGH, 8.5), (80.0, 6.0, 30.0)),           # from the court: the roof's glazed side
    ("lip_south", (58.5, HIGH, 12.5), (80.0, 5.0, 30.0)),           # from the terrace's lip
    ("chimney_up", (82.5, LOW, 1.5), (89.0, 5.5, 22.5)),            # the chimney and the fire window, from the yard
    ("bridge_near", (64.5, LOW, 21.5), (62.5, 0.0, 33.5)),          # under the pipe bridge
    ("bridge_head", (41.5, HIGH, 35.5), (60.0, 1.5, 32.5)),         # along the main on the terrace to the bridge head
    ("head_west", (53.5, HIGH, 34.5), (58.5, 1.3, 33.4)),           # the bridge head as one walks up to it
    ("head_walk", (54.5, HIGH, 33.5), (59.5, HIGH, 38.5)),          # the walk-through's station G01, looking right
    ("head_north", (56.5, HIGH, 28.5), (59.0, 1.2, 33.5)),          # the head from the north: the pipe, the knee, the railing
    ("lookout_east", (48.5, S.SOUTH_LOOKOUT["feet"] + S.EYE, 50.5), (78.0, 3.0, 31.0)),     # the south-west corner
    ("aerial", (58.0, 34.0, 4.0), (78.0, 0.0, 31.0)),
    ("aerial_back", (100.0, 30.0, 56.0), (78.0, 0.0, 31.0)),
]


def shots():
    """The shot list both scenes are drawn from."""
    return [{"name": name, "pos": [round(float(v), 2) for v in pos],
             "look_at": [round(float(v), 2) for v in look_at], "time": TIME}
            for name, pos, look_at in VIEWS]


@contextlib.contextmanager
def _as(version, run):
    """The site line builds its packages itself and hands them no choices: set the package's own
    defaults for the time of the build and put them back."""
    was = powerhouse.VERSION, powerhouse.RUN, powerhouse.FIRE, powerhouse.VENTS_ON
    powerhouse.VERSION, powerhouse.RUN, powerhouse.FIRE, powerhouse.VENTS_ON = version, run, FIRE, True
    try:
        yield
    finally:
        powerhouse.VERSION, powerhouse.RUN, powerhouse.FIRE, powerhouse.VENTS_ON = was


def _fit(c):
    """What the props line hangs on the shell (powerhouse.FITTINGS, DRAINS). props/pipes reads the
    tables itself (pipes.fittings) and places nothing of its own accord while its switch is off;
    here the house is shown with them. Nothing while that function is not in the tree, and
    nothing once the switch is on: the props line has placed them already."""
    try:
        from scenes.obs.props import pipes
    except ImportError:
        return 0
    fittings = getattr(pipes, "fittings", None)
    if fittings is None or getattr(pipes, "DRESS", False):
        return 0
    return int(fittings(c, (0, 0, 0)) or 0)


def build(version=None, run=None):
    c = Canvas()
    with _as(version or VERSION, RUN if run is None else run):
        for line in LINES:
            if line is sky:         # after the props line; before the light sources, which go last
                _fit(c)
                powerhouse.lining(c)    # the materials line is not built here: the fire windows' room side
            line.build(c, (0, 0, 0))
    return c


def build_models():
    out = {}
    for line in LINES:
        out.update(line.models() or {})
    try:
        from scenes.obs.materials import windows
    except ImportError:
        windows = None
    if getattr(windows, "line", None) is not None:
        out.update(windows.models())        # the linings of the fire windows (powerhouse.lining)
    return out


def write_pack(pack_dir):
    """The power house paints nothing itself; it stands on the repainted blocks as the materials
    line has them today (tuff, slate, cast iron, the window glasses), under the map's sky: the
    scene stands in the map's hour, and without the sky's pack the game's own sun is a white and
    yellow square on the western horizon."""
    return list(materials.pack(pack_dir) or []) + list(sky.pack(pack_dir) or [])
