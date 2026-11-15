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
"""
import contextlib

from artkit.canvas import Canvas

from scenes.obs import main, materials, props, site, sky
from scenes.obs.site import powerhouse

BIOME = "obs_blue"
BIOME_MARGIN = 100
BIOME_MARGIN_Y = 150
LINES = (site, main, props, sky)
VERSION = "a"
RUN = True
FIRE = True     # both scenes: the boiler bays glow through the fire window, as the card wants them judged


@contextlib.contextmanager
def _as(version, run):
    """The site line builds its packages itself and hands them no choices: set the package's own
    defaults for the time of the build and put them back."""
    was = powerhouse.VERSION, powerhouse.RUN, powerhouse.FIRE
    powerhouse.VERSION, powerhouse.RUN, powerhouse.FIRE = version, run, FIRE
    try:
        yield
    finally:
        powerhouse.VERSION, powerhouse.RUN, powerhouse.FIRE = was


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
