"""Test scene of the work package interiors/starhall (plan/packages/interiors/starhall.md): the
hall in version a, "academy". Its twin obs_int_starhall_b shows version b, "workshop", from the
same cameras under the same names, so the two can be compared blind.

The scene is laid the way the master scene lays it: the main line whole (walls, shell, dome), the
two machines of the hall, the hall's own dress, and the light line last, which settles the sources
everybody offered and lights the doorway as it does in the master scene. No light is set by hand.

The orrery and the mother clock are the real ones as soon as machines/orrery and machines/clock
are in the tree; until then standins.py shows their envelope and offers their two lights.

shots.json is written by  python -m scenes.obs_int_starhall  (both scenes read the same file).

The doorway. A0 ruled (11-16) that the doorway's own source, which the light line sets while the
hall stands empty, goes when the hall moves in. sky/lights does that itself from its commit
d78e4151 on (_entrance asks facade.furnished()); until that is in the tree this scene takes the
source away after the light line has run, which comes to the same. The two pictures the ruling
was made on can still be drawn:
  C164_HALL_DOOR=<level>   the doorway's source back, at this level (the light line's is 14)
  C164_HALL_POOL=<level>   starhall.SUN_POOL at another level; 0: none
"""
import os

from artkit.canvas import Canvas

from scenes.obs import main, materials, sky
from scenes.obs.common import blocks as B
from scenes.obs.common import skeleton as S
from scenes.obs.interiors import starhall
from scenes.obs.main import shell
from scenes.obs.props import lamps
from scenes.obs.sky import _lightkit as L
from scenes.obs.sky import lights

from . import standins

BIOME = "obs_blue"
BIOME_MARGIN = 60
VERSION = "a"
GROUND = (S.WALL_W - 14, S.Z_NORTH - 6, S.WALL_E + 15, S.Z_SOUTH + 6)  # paving under and before the building
ORIGIN = (0, 0, 0)
OPTIONAL = ("machines.orrery", "machines.clock", "props.furniture", "props.instruments", "props.paper")
#          packages whose models the hall shows, each as soon as it is in the tree
DOOR_ENV, POOL_ENV = "C164_HALL_DOOR", "C164_HALL_POOL"


def _machines(c, version):
    """The orrery and the mother clock: machines' own when they are in the tree."""
    n = 0
    orrery = starhall._optional("machines.orrery")
    n += orrery.build(c, ORIGIN) if orrery is not None else standins.orrery(c, ORIGIN)
    clock = starhall._optional("machines.clock")
    n += clock.master(c, ORIGIN) if clock is not None else standins.clock(c, ORIGIN)
    return n


def _door(c):
    """The doorway's source goes with the hall moved in (the docstring); the environment puts it
    back at a level of its choosing."""
    level = int(os.environ.get(DOOR_ENV, "0"))
    for cell in lights.report(c)["doors"]:
        if level > 0:
            c.set(*cell, L.light(level))
        else:
            c.clear(*cell)


def build(version=VERSION):
    c = Canvas()
    x0, z0, x1, z1 = GROUND
    c.box(x0, S.PAVING_Y, z0, x1, S.PAVING_Y, z1, B.SLATE_SMOOTH.block)
    counts = {"materials": materials.build(c, ORIGIN)}
    counts["main"] = main.build(c, ORIGIN)       # the hall has moved in (starhall.MOVED_IN): no stand-in wall
    counts["machines"] = _machines(c, version)
    pool = starhall.SUN_POOL
    if os.environ.get(POOL_ENV) is not None:
        starhall.SUN_POOL = int(os.environ[POOL_ENV]) or None
    try:
        counts["interiors"] = starhall.dress(c, ORIGIN, version)
    finally:
        starhall.SUN_POOL = pool
    counts["sky"] = sky.build(c, ORIGIN)
    _door(c)
    c.entity_counts = {k: int(v or 0) for k, v in counts.items()}
    return c


def build_models():
    out = {}
    parts = [main.models(), materials.models(), sky.models(), lamps.models(), starhall.models(), standins.models()]
    for name in OPTIONAL:
        module = starhall._optional(name)
        if module is not None:
            parts.append(module.models())
    for part in parts:
        out.update(part or {})
    return out


def write_pack(pack_dir):
    """The hall paints nothing; it stands on the repainted blocks as the materials line has them,
    under the sky's pictures (the scene stands in the map's hour)."""
    return list(materials.pack(pack_dir) or []) + list(sky.pack(pack_dir) or [])


def shots():
    """The cameras, the same for both versions. v7 is the skeleton's locked view from outside the
    door, v7_in its second from inside the doorway (A0 #365)."""
    eye = S.EYE
    gallery = shell.DECK_Y + 1 + eye
    cx, cz = S.ORRERY_CENTRE
    out = []

    def shot(name, pos, look_at=None, **turn):
        entry = {"name": name, "pos": [round(v, 2) for v in pos]}
        if look_at is not None:
            entry["look_at"] = [round(v, 2) for v in look_at]
        entry.update(turn)
        out.append(entry)

    shot("v7", S.V7["pos"], S.V7["look_at"])
    shot("v7_in", (16.5, eye, cz), (8.0, 5.0, cz))
    shot("west", (13.5, eye, cz), (4.0, 3.6, cz))                       # the pier and the clock, the arcade behind
    shot("clock", (9.6, eye, cz + 0.9), (6.2, 2.9, cz))
    shot("orrery", (14.2, eye, cz + 2.2), (cx, 9.0, cz))                # from the floor up into it, the boss over it
    shot("ceiling", (cx, gallery, 5.3), (cx, starhall.CEIL + 0.25, cz))  # from the south gallery up to the boss
    shot("floor", (cx, shell.DECK_Y + 0.4, cz), yaw=90.0, pitch=90.0)   # the plan of the floor, west at the top
    shot("gallery", (15.3, gallery, 5.4), (3.0, 7.2, -1.6))             # along the hall from the south gallery's east end
    shot("rail", (cx, gallery, 4.9), (cx, 0.0, -1.2))                   # over the south railing: the orrery over its roundel
    shot("gallery_w", (2.6, gallery, -4.6), (13.0, 6.5, 2.5))           # from the gallery's west end to the entrance wall
    shot("door", (8.4, eye, cz), (16.0, 4.6, cz))                       # back to the doorway: the second emblem
    shot("aisle_n", (14.6, eye, -2.4), (4.0, 2.2, -4.4))
    shot("aisle_s", (14.6, eye, 3.4), (4.0, 2.2, 5.4))
    shot("stair_n", (6.6, eye, -3.4), (-3.5, 3.2, -3.6))                # through the side arch to the stair foot
    shot("mezzanine", (0.5, gallery, cz + 2.2), (-7.0, 9.4, cz))        # the two lamps beside the great west window
    shot("arches", (S.V7["pos"][0] + 9.0, eye, cz), (16.0, 3.4, cz))    # the three arches from the forecourt's axis
    return out
