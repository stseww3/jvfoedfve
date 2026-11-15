"""obs_int_starhall: the test scene of the work package interiors/starhall (the star hall's
fitting-out; card plan/packages/interiors/starhall.md).

The main building stands twice, whole, on a slab of paving that reaches out to where the board's
view of the front is taken from (V2), with the star hall fitted out in it:

  at z 0      version a, "academic";
  at z 160    version b, "workshop"; so far off that neither shows in a view of the other.

Each copy is the main line (walls, drum, dome, shell) without the stand-in wall behind the
entrance; the two machines the hall is the background of -- the real ones where machines/orrery
and machines/clock are in the tree, else blocks in their place (interiors/_stubs.py); the hall's
own dress (starhall.dress), with blocks standing in for the pieces of the props line that are not
in the tree yet; and the light line's sources (sky/lights) where that package is in the tree. Not
the whole sky line: it would lay its cloud sea round each copy.

The hall is the master scene's from the day its switch (starhall.MOVED_IN) is set. This scene sets
it for the time of its own build, so that the facade and the light line treat the hall as moved in.

The shot names carry the version (a_*, b_*). v7 and v2 are the skeleton's locked views.
"""
import contextlib
import importlib
import importlib.util

from artkit.canvas import Canvas
from artkit.blocks import st

from scenes.obs.common import blocks as B
from scenes.obs.common import skeleton as S
from scenes.obs.interiors import _stubs, starhall
from scenes.obs.main import shell

BIOME = "obs_blue"
BIOME_MARGIN = 60
CATEGORY = "interiors"
SPACING = 160
ORIGINS = {"a": (0, 0, 0), "b": (0, 0, SPACING)}
LINES = ("materials", "main", "machines", "interiors", "props")        # whose models and pack files the scene shows
GROUND = (S.WALL_W - 14, S.Z_NORTH - 6, S.EAST_EDGE_X + 2, S.Z_SOUTH + 6)   # x -14..62, z -40..40
DOOR_LIGHT = ((S.east_wall_x(S.CENTRE_BAYS[1]) + S.DEPTH_GLASS, S.GROUND + 1, 0), 14)   # as sky/lights puts it in the doorway


def _line(name):
    return importlib.import_module(f"scenes.obs.{name}")


def _part(name):
    """A module of the master scene, or None while it is not in the tree."""
    full = f"scenes.obs.{name}"
    try:
        return importlib.import_module(full)
    except ModuleNotFoundError as e:
        if e.name != full:
            raise
        return None


@contextlib.contextmanager
def moved_in():
    was = starhall.MOVED_IN
    starhall.MOVED_IN = True
    try:
        yield
    finally:
        starhall.MOVED_IN = was


def machines(c, origin):
    """The orrery and the mother clock; returns the number of display entities."""
    ox, oy, oz = origin

    def put(x, y, z, state):
        c.set(ox + x, oy + y, oz + z, state)

    n = 0
    orrery, clock = _part("machines.orrery"), _part("machines.clock")
    if orrery is not None:
        n += orrery.build(c, origin)
    else:
        _stubs.orrery(put, starhall.ASK_SUN[0])
    if clock is not None:
        n += clock.master(c, origin)
    else:
        _stubs.mother_clock(put, starhall.ASK_CLOCK[0])
    return n


def lights(c, origin):
    """The light line's part: the windows of the front, the doorway, and the sources the hall, its
    lamps and the machines have asked for. Where sky/lights is not in the tree the lamps have put
    their sources down themselves; the doorway's is put here then, so the floor inside the door is
    lit as it will be."""
    kit, line = _part("sky._lightkit"), _part("sky.lights")
    if line is None:
        (x, y, z), level = DOOR_LIGHT
        c.set(origin[0] + x, origin[1] + y, origin[2] + z, st(B.LIGHT, level=level), keep=True)
        return 0
    if hasattr(kit, "dress"):
        kit.dress(c)                            # the front under its lights: V2 looks at it
    return line.build(c, origin)


def build():
    c = Canvas()
    x0, z0, x1, z1 = GROUND
    counts = {}
    with shell.hall_open(), moved_in():
        for version, origin in ORIGINS.items():
            ox, oy, oz = origin
            c.box(ox + x0, oy + S.PAVING_Y, oz + z0, ox + x1, oy + S.PAVING_Y, oz + z1, B.SLATE_SMOOTH.block)
            n = _line("main").build(c, origin) or 0
            n += machines(c, origin)
            got = starhall.dress(c, origin, version, standins=True)
            n += got["entities"]
            n += lights(c, origin) or 0
            counts[version] = dict(got, entities=n)
    c.starhall = counts                         # what each copy holds: entities, lights asked for, pieces left out
    return c


def build_models():
    out = {}
    for name in LINES:
        out.update(_line(name).models() or {})
    return out


def write_pack(pack_dir):
    """The hall paints nothing: it stands on the repainted blocks of the materials line, and shows
    the models of the lines above."""
    out = []
    for name in LINES:
        out += list(_line(name).pack(pack_dir) or [])
    return out
