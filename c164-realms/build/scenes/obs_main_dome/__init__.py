"""Test scene of the work package main/dome (plan/packages/main/dome.md).

The rotunda where it stands in the master scene: the site under it, the whole main line, the
props line's lamps and the sky line's light sources last. The lines are built whole, in the master
scene's order, so the pictures keep up with them as their packages are merged.

The dome is the version the map is built with (dome.VERSION: b, eight main ribs and a slatted
curtain), its slit open as in the master scene. obs_main_dome_a is this scene with version a (twenty
flush seams, two leaves that part sideways), kept for the comparison; every shot has its twin of the
same name there. obs_main_dome_slit stands both versions side by side with the slit shut, half open
and open.

What the shots are for: v1 and v2_axis are the two main views (the dome is a stamp in the first and
the top of the picture in the second: its outline has to be a clean round, the drum has to show its
bays); v11 and aerial are the other two views it is in; roof, drum and gallery look at the drum,
the gallery and the dome's foot from close by, ridge at the same from the walkway on the south
wing's ridge; top, slit and west at the crown and the slit.

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
VERSION = None                  # None: the package's default
SLIT = "open"
TIME = 14000                    # light version A, the default (INTERFACE: 18000 is B, 12900 is C)
# The two main views are the skeleton's. The director raised both (group #304: V1 looks at
# (8, 34, 0.5), V2 stands at (58.5, 1.7, 0.5) and looks at (17, 19, 0.5)) and had V2 written into
# the skeleton; a skeleton that has no V2 yet is older than that ruling, and the ruling's own
# numbers stand in for it.
V1 = S.V1 if hasattr(S, "V2") else dict(pos=S.V1["pos"], look_at=(8, 34, 0.5))
V2 = getattr(S, "V2", dict(pos=(58.5, 1.7, 0.5), look_at=(17, 19, 0.5)))


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
    with _dome(version or VERSION or dome.VERSION, slit or SLIT):
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
    has them today (ashlar, the two verdigris sheets, riveted and cast iron, the window family),
    under the sky line's sky (without its pictures the game's own sun lies on the western horizon)."""
    return list(materials.pack(pack_dir) or []) + list(sky.pack(pack_dir) or [])


def shots():
    """The shot list, from the skeleton's numbers; the same for both versions."""
    cx, cz = S.DOME_CENTRE
    axis = cz + 0.5
    spring = float(S.DOME_SPRING)
    out = []

    def shot(name, pos, look_at):
        out.append({"name": name, "pos": [round(float(v), 2) for v in pos],
                    "look_at": [round(float(v), 2) for v in look_at], "time": TIME})

    # V1, the arrival: the dome is a stamp in it, and has to read as a round
    shot("v1", V1["pos"], V1["look_at"])
    # V2: the court's axis at eye height, the entrance front and the dome over it
    shot("v2_axis", V2["pos"], V2["look_at"])
    # V11: back from the south lookout, three quarters
    shot("v11", S.V11["pos"], S.V11["look_at"])
    # the roofs' level: the drum, the gallery and the dome's foot, from over the south wing
    shot("roof", (cx + 16.0, spring + 3.0, cz + 16.0), (cx + 4.0, spring, cz + 4.0))
    # the drum's bays, level with them, from the air in front of the building: pilasters, niches and
    # windows, the corbel course and the gallery's cove from below
    shot("drum", (cx + 22.0, spring - 2.0, cz + 12.0), (cx + 10.0, spring - 3.5, cz + 6.0))
    # standing on the gallery's walkway, north-east, looking along it to the south: the walkway and
    # the gutter going round, the ring beam and its axle boxes and the dome's foot on the right,
    # the court on the left
    shot("gallery", (cx + 11.5, spring + S.EYE, cz - 10.5), (cx + 16.2, spring + 0.2, cz - 2.5))
    # standing on the ridge walkway of the south wing, six blocks short of the gallery: the drum's
    # bays and the door of the dome room, the gallery from below, the dome over it (closer, under
    # the gallery, one sees only its underside)
    shot("ridge", (cx + 4.0, S.ROOF_STAND + 2.0 + S.EYE, cz + 21.5), (cx + 5.0, spring + 1.5, cz + 9.0))
    # from above, as V12 comes over the building from the south-east
    shot("aerial", (cx + 36.0, 60.0, cz + 30.0), (cx + 2.0, 20.0, cz))
    # from above on the slit's side: the crown, the slit and what shuts it
    shot("top", (cx - 21.0, 50.0, cz + 19.0), (cx, 26.0, cz))
    # the slit, close
    shot("slit", (cx - 22.0, 33.0, cz + 7.0), (cx - 7.0, 30.0, cz))
    # the west side whole: the apse, the drum, the dome with the slit in the middle
    shot("west", (cx - 42.0, 12.0, axis), (cx, 24.0, axis))
    return out
