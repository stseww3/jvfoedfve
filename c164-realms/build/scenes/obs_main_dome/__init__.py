"""Test scene of the work package main/dome (plan/packages/main/dome.md).

The rotunda where it stands in the master scene: the site under it, the whole main line, the
props line's lamps and the sky line's light sources last. The lines are built whole, in the master
scene's order, so the pictures keep up with them as their packages are merged.

The dome is version a here (twenty fine ribs, two leaves that part sideways), its slit open as in
the master scene. obs_main_dome_b is this scene with version b; every shot has its twin of the same
name there. obs_main_dome_slit stands both versions side by side with the slit shut, half open and
open.

    python -m scenes.obs_main_dome        writes shots.json of the three scenes
"""
import contextlib

from artkit.canvas import Canvas

from scenes.obs import main, materials, props, site, sky
from scenes.obs.common import skeleton as S
from scenes.obs.main import dome

BIOME = "obs_blue"
BIOME_MARGIN = 80
BIOME_MARGIN_Y = 140
LINES = (site, main, props, sky)
VERSION = "a"
SLIT = "open"
TIME = 14000                    # light version A, the default (INTERFACE: 18000 is B, 12900 is C)


@contextlib.contextmanager
def _dome(version, slit):
    """Build with one version of the dome and one state of its slit."""
    was = dome.VERSION, dome.SLIT
    dome.VERSION, dome.SLIT = version, slit
    try:
        yield
    finally:
        dome.VERSION, dome.SLIT = was


def build(version=None, slit=None):
    c = Canvas()
    with _dome(version or VERSION, slit or SLIT):
        for line in LINES:
            line.build(c, (0, 0, 0))
    return c


def build_models():
    out = {}
    for line in LINES:
        out.update(line.models() or {})
    return out


def write_pack(pack_dir):
    """The shell paints nothing itself: it stands in the repainted blocks as the materials line
    has them today (ashlar, the two verdigris sheets, riveted and cast iron, the window family)."""
    return materials.pack(pack_dir)


def shots():
    """The shot list, from the skeleton's numbers; the same for both versions."""
    cx, cz = S.DOME_CENTRE
    axis = cz + 0.5
    spring = float(S.DOME_SPRING)
    court = S.EAST_EDGE_X - 1.5                         # the east edge of the court, on the axis
    out = []

    def shot(name, pos, look_at):
        out.append({"name": name, "pos": [round(v, 2) for v in pos],
                    "look_at": [round(v, 2) for v in look_at], "time": TIME})

    # V1, the arrival: the dome is a stamp in it, and has to read as a round
    shot("v1", S.V1["pos"], S.V1["look_at"])
    # V2: the court's axis at eye height, the entrance front and the dome over it
    shot("v2_axis", (court, 1.7, axis), (17.0, 11.0, axis))
    # V11: back from the south lookout, three quarters
    shot("v11", S.V11["pos"], S.V11["look_at"])
    # the roofs' level: the drum, the gallery and the feet of the ribs, from over the south wing
    shot("roof", (cx + 16.0, spring + 3.0, cz + 16.0), (cx + 4.0, spring, cz + 4.0))
    # standing in the gallery's gutter on the east side: the ring beam, the axle boxes, the railing
    shot("gallery", (cx + 14.5, spring - 0.5 + S.EYE, cz - 3.5), (cx + 9.5, spring + 2.0, cz + 8.0))
    # from above, as V12 comes over the building from the south-east
    shot("aerial", (cx + 36.0, 60.0, cz + 30.0), (cx + 2.0, 20.0, cz))
    # from above on the slit's side: the crown, the slit and what shuts it
    shot("top", (cx - 21.0, 50.0, cz + 19.0), (cx, 26.0, cz))
    # the slit, close
    shot("slit", (cx - 22.0, 33.0, cz + 7.0), (cx - 7.0, 30.0, cz))
    # the west side whole: the apse, the drum, the dome with the slit in the middle
    shot("west", (cx - 42.0, 12.0, axis), (cx, 24.0, axis))
    return out
