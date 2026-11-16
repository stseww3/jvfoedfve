"""Test scene of the work package main/facade (plan/packages/main/facade.md).

The main building where it stands in the master scene: the site under it, the whole main line,
the machines that stand on it and beside it (the clocks, the radio mast), the rooms as they move
in, the props line's lamps and the sky line's light sources last. The lines are built whole, in
the master scene's order, so the pictures keep up with them as their packages are merged.

The entrance is the version the package builds by default (facade.ENTRANCE). obs_main_facade_a
and obs_main_facade_c are this scene with the other two versions, obs_main_facade_nocrown is this
scene with the heads of the great windows and of the arches left open over the crown, as they
were (facade.CROWN off); every shot of theirs has its twin of the same name here.

    python -m scenes.obs_main_facade        writes shots.json of the four scenes
"""
import contextlib

from artkit.canvas import Canvas

from scenes.obs import interiors, machines, main, materials, props, site, sky
from scenes.obs.common import skeleton as S
from scenes.obs.main import _plan as P
from scenes.obs.main import facade

BIOME = "obs_blue"
BIOME_MARGIN = 80
BIOME_MARGIN_Y = 140
LINES = (site, main, machines, interiors, props, sky)
ENTRANCE = None                 # None: the package's default
TIME = 14000                    # light version A, the default (INTERFACE: 18000 is B, 12900 is C; noon draws as A)
# The two main views are the skeleton's (the director raised both on 11-14: they look up about 22
# degrees, the building in the lower half of the picture, the comet whole in the upper).
V1, V2 = S.V1, S.V2


# The shots in which the versions of the entrance differ, and those in which the two heads do
COMPARE = ("v2_axis", "v4_entrance", "v1_far", "arcade")
HEADS = COMPARE + ("v3_near",)


@contextlib.contextmanager
def _version(entrance, crown):
    """Build with one version of the entrance and of the heads: whoever asks the package which is
    built (the windows' table, the doorways' table, the lamps beside the door) gets the same
    answer."""
    was = facade.ENTRANCE, facade.CROWN
    facade.ENTRANCE = entrance or was[0]
    facade.CROWN = was[1] if crown is None else crown
    try:
        yield
    finally:
        facade.ENTRANCE, facade.CROWN = was


def build(entrance=None, crown=None):
    c = Canvas()
    with _version(entrance or ENTRANCE, crown):
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
    has them today (ashlar, the window family, slate, iron), under the sky line's sky."""
    return list(materials.pack(pack_dir) or []) + list(sky.pack(pack_dir) or [])


def shots(only=None):
    """The shot list, from the skeleton's numbers. only: the names a twin scene keeps of it
    (COMPARE, HEADS), in this list's order."""
    face = float(S.east_wall_x(P.AISLE_BAY))            # the wall plane of the middle pavilion
    wing = float(S.WALL_E)
    axis = 0.5
    z3 = S.pilaster_z(P.AISLE_BAY + 2) + 0.5            # the pilaster between the two bays of V3
    out = [
        # V2: the court's axis, at eye height -- the whole front, the dome over it and the sky over that
        dict(name="v2_axis", pos=[float(n) for n in V2["pos"]], look_at=[float(n) for n in V2["look_at"]], time=TIME),
        # V4: the entrance, from the court
        dict(name="v4_entrance", pos=[face + 14.0, 2.6, axis], look_at=[face, 6.0, axis], time=TIME),
        # V1: the arrival, from the platform of the cable car station
        dict(name="v1_far", pos=[float(n) for n in V1["pos"]], look_at=[float(n) for n in V1["look_at"]], time=TIME),
        # the arcade from beside the axis, close: how deep the arches are
        dict(name="arcade", pos=[face + 10.5, 1.7, 11.5], look_at=[face + 0.5, 4.5, axis - 0.5], time=TIME),
        # V7: from outside the door, the middle arch as the frame of what stands behind it
        dict(name="v7_door", pos=[float(n) for n in S.V7["pos"]], look_at=[float(n) for n in S.V7["look_at"]], time=TIME),
        # V3: two bays of the south wing, close, with the corner of the middle pavilion
        dict(name="v3_near", pos=[wing + 10.5, 2.2, z3 + 3.0], look_at=[wing + 1.0, 6.5, z3 - 1.5], time=TIME),
        dict(name="oblique", pos=[47.0, 5.0, 31.0], look_at=[14.0, 10.0, -2.0], time=TIME),
        # V11: looking back from the south lookout -- the south end wall and the east front in three-quarter view
        dict(name="v11_south", pos=[float(n) for n in S.V11["pos"]], look_at=[float(n) for n in S.V11["look_at"]], time=TIME),
        # from above: the roofs, the gable walls, the parapets and what stands on them
        dict(name="roofs", pos=[58.0, 44.0, 34.0], look_at=[8.0, 14.0, 0.0], time=TIME),
        dict(name="west", pos=[-34.0, 6.0, -30.0], look_at=[4.0, 14.0, 0.0], time=TIME),
        # the two windows of the base storey where somebody is at work (main/_nightwork.py), as plan/fine.md
        # asks: from ten blocks, the two of them and the pilaster between; and close, from where one stands
        # in the court before the desk's window and looks up at it (nearer, the sill hides the desk)
        dict(name="work_mid", pos=[wing + 10.5, 2.6, z3], look_at=[wing, 4.0, z3], time=TIME),
        dict(name="work_near", pos=[wing + 5.0, 1.62, z3 + 2.0], look_at=[wing, 4.2, z3 + 2.0], time=TIME),
    ]
    return [s for s in out if only is None or s["name"] in only]
