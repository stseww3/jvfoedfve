"""Test scene of the work package main/facade (plan/packages/main/facade.md).

The main building where it stands in the master scene: the site under it, the whole main line,
the props line's lamps on it and the sky line's light sources last. The lines are built whole, in
the master scene's order, so the pictures keep up with them as their packages are merged.

The entrance is the version the package builds by default (facade.ENTRANCE). obs_main_facade_a
and obs_main_facade_c are this scene with the other two versions; every shot of theirs has its
twin of the same name here.

    python -m scenes.obs_main_facade        writes shots.json of the three scenes
"""
import contextlib

from artkit.canvas import Canvas

from scenes.obs import main, materials, props, site, sky
from scenes.obs.common import skeleton as S
from scenes.obs.main import _plan as P
from scenes.obs.main import facade

BIOME = "obs_blue"
BIOME_MARGIN = 80
BIOME_MARGIN_Y = 140
LINES = (site, main, props, sky)
ENTRANCE = None                 # None: the package's default
TIME = 14000                    # light version A, the default (INTERFACE: 18000 is B, 12900 is C; noon draws as A)
# The two main views are the skeleton's. The director raised both on 11-14 (group, 13:21: they look
# up about 22 degrees, the building in the lower half of the picture, the comet whole in the upper)
# and had V2 written into the skeleton; a skeleton that has no V2 yet is older than that ruling,
# and the ruling's own numbers stand in for it.
V1 = S.V1 if hasattr(S, "V2") else dict(pos=S.V1["pos"], look_at=(8, 34, 0.5))
V2 = getattr(S, "V2", dict(pos=(58.5, 1.7, 0.5), look_at=(17, 19, 0.5)))


@contextlib.contextmanager
def _entrance(version):
    """Build with one version of the entrance: whoever asks the package which one is built (the
    windows' table, the doorways' table, the lamps beside the door) gets the same answer."""
    was = facade.ENTRANCE
    facade.ENTRANCE = version or was
    try:
        yield
    finally:
        facade.ENTRANCE = was


def build(entrance=None):
    c = Canvas()
    with _entrance(entrance or ENTRANCE):
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
    has them today (ashlar, the window family, slate, iron)."""
    return materials.pack(pack_dir)


def shots(compare=False):
    """The shot list, from the skeleton's numbers. compare=True: the four shots in which the
    versions of the entrance differ (the other two scenes)."""
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
    ]
    if not compare:
        out += [
            # V3: two bays of the south wing, close, with the corner of the middle pavilion
            dict(name="v3_near", pos=[wing + 10.5, 2.2, z3 + 3.0], look_at=[wing + 1.0, 6.5, z3 - 1.5], time=TIME),
            dict(name="oblique", pos=[47.0, 5.0, 31.0], look_at=[14.0, 10.0, -2.0], time=TIME),
            # from above: the roofs, the gable walls, the parapets and what stands on them
            dict(name="roofs", pos=[58.0, 44.0, 34.0], look_at=[8.0, 14.0, 0.0], time=TIME),
            dict(name="west", pos=[-34.0, 6.0, -30.0], look_at=[4.0, 14.0, 0.0], time=TIME),
        ]
    return out
