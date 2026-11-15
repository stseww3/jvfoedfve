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

Both show the bridge with the props line's fittings on it (powerhouse.FITTINGS), once props/pipes is
in the tree.
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


@contextlib.contextmanager
def _as(version, run):
    """The site line builds its packages itself and hands them no choices: set the package's own
    defaults for the time of the build and put them back."""
    was = powerhouse.VERSION, powerhouse.RUN
    powerhouse.VERSION, powerhouse.RUN = version, run
    try:
        yield
    finally:
        powerhouse.VERSION, powerhouse.RUN = was


def _fit(c):
    """The fittings of the pipe bridge (powerhouse.FITTINGS: a valve head, three straps). They are
    the props line's, which places nothing of its own accord until its review is passed; the bridge
    is shown with them here. Nothing while props/pipes is not in the tree."""
    try:
        from scenes.obs.props import pipes
    except ImportError:
        return 0
    mount = getattr(pipes, "mount", None)
    if mount is None:
        return 0
    return sum(int(mount(c, kind, pos, origin=(0, 0, 0), **how) or 0) for kind, pos, how in powerhouse.FITTINGS)


def build(version=None, run=None):
    c = Canvas()
    with _as(version or VERSION, RUN if run is None else run):
        for line in LINES:
            if line is sky:
                _fit(c)             # before the light sources, which go last
            line.build(c, (0, 0, 0))
    return c


def build_models():
    out = {}
    for line in LINES:
        out.update(line.models() or {})
    return out


def write_pack(pack_dir):
    """The power house paints nothing itself; it stands on the repainted blocks as the materials
    line has them today (tuff, slate, cast iron, the window glasses)."""
    return materials.pack(pack_dir)
