"""Test scene of the work package interiors/starhall (plan/packages/interiors/starhall.md): the
hall in version a, "academy". Its twin obs_int_starhall_b shows version b, "workshop", from the
same cameras under the same names, so the two can be compared blind.

The scene is laid the way the master scene lays it: the main line whole (walls, shell, dome), the
two machines of the hall (machines/orrery, machines/clock), the hall's own dress, and the light
line last, which settles the sources everybody offered. No light is set by hand: with the hall
moved in (starhall.MOVED_IN) the light line keeps no source of its own in the hall or in its
doorway (A0, #58129).

shots.json is written by  python -m scenes.obs_int_starhall  (both scenes read the same file).

The light line's own lamps along the ways people walk (the stair hall's among them) hang in the
master scene and wherever a scene asks for the building's lights (_lightkit.dress): this one
does, because the first look is judged with them: the three arches behind the pier are to stay
darker than the pier's face (lights, #75636).

  C164_HALL_POOL=<level>   starhall.SUN_POOL at another level, to compare; 0: none
  C164_HALL_SPOT=<level>   starhall.SPOT_LEVEL likewise; 0: the globe and the board's ends take
                           the light of their cells
"""
import os

from artkit.canvas import Canvas

from scenes.obs import main, materials, sky
from scenes.obs.common import blocks as B
from scenes.obs.common import skeleton as S
from scenes.obs.interiors import starhall
from scenes.obs.machines import clock, orrery
from scenes.obs.main import shell
from scenes.obs.props import furniture, instruments, lamps, paper
from scenes.obs.sky import _lightkit

BIOME = "obs_blue"
BIOME_MARGIN = 60
VERSION = "a"
GROUND = (S.WALL_W - 14, S.Z_NORTH - 6, S.WALL_E + 15, S.Z_SOUTH + 6)  # paving under and before the building
ORIGIN = (0, 0, 0)
TRY = {"C164_HALL_POOL": "SUN_POOL", "C164_HALL_SPOT": "SPOT_LEVEL"}     # what the environment may set, to compare


def _machines(c):
    """The two machines the hall is the room of."""
    return orrery.build(c, ORIGIN) + clock.master(c, ORIGIN)


def build(version=VERSION):
    c = Canvas()
    x0, z0, x1, z1 = GROUND
    c.box(x0, S.PAVING_Y, z0, x1, S.PAVING_Y, z1, B.SLATE_SMOOTH.block)
    counts = {"materials": materials.build(c, ORIGIN)}
    counts["main"] = main.build(c, ORIGIN)       # the hall has moved in (starhall.MOVED_IN): no stand-in wall
    counts["machines"] = _machines(c)
    kept = {name: getattr(starhall, name) for name in TRY.values()}
    for env, name in TRY.items():
        if os.environ.get(env) is not None:
            setattr(starhall, name, int(os.environ[env]) or None)
    try:
        counts["interiors"] = starhall.dress(c, ORIGIN, version)
    finally:
        for name, value in kept.items():
            setattr(starhall, name, value)
    _lightkit.dress(c)
    counts["sky"] = sky.build(c, ORIGIN)
    c.entity_counts = {k: int(v or 0) for k, v in counts.items()}
    return c


def build_models():
    out = {}
    for package in (main, materials, sky, lamps, furniture, instruments, paper, orrery, clock, starhall):
        out.update(package.models() or {})
    return out


def write_pack(pack_dir):
    """The hall paints nothing; it stands on the repainted blocks as the materials line has them,
    under the sky's pictures (the scene stands in the map's hour)."""
    return list(materials.pack(pack_dir) or []) + list(sky.pack(pack_dir) or [])


def shots():
    """The cameras, the same for both versions. v7 is the skeleton's locked view and goes where the
    skeleton puts it; v7_in is its second from inside the doorway (A0 #365). door is where V7 stood
    first, between the leaves of the open door: A0 moves V7 two cells in (#71961) and keeps this
    one as the hall's own."""
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
    shot("door", (19.5, eye, cz), (10.0, 5.5, cz))                      # between the door's leaves, the arch as frame
    shot("v7_in", (16.5, eye, cz), (8.0, 5.0, cz))
    shot("west", (13.5, eye, cz), (4.0, 3.6, cz))                       # the pier and the clock, the arcade behind
    shot("clock", (9.6, eye, cz + 0.9), (6.2, 2.9, cz))
    shot("orrery", (14.2, eye, cz + 2.2), (cx, 9.0, cz))                # from the floor up into it, the boss over it
    shot("ceiling", (cx, gallery, 5.3), (cx, starhall.CEIL + 0.25, cz))  # from the south gallery up to the boss
    shot("floor", (cx, shell.DECK_Y + 0.4, cz), yaw=90.0, pitch=90.0)   # the plan of the floor, west at the top
    shot("gallery", (15.3, gallery, 5.4), (3.0, 7.2, -1.6))             # along the hall from the south gallery's east end
    shot("rail", (cx, gallery, 4.9), (cx, 5.5, cz))                     # over the south railing: the orrery over its roundel
    shot("gallery_w", (6.4, gallery, -4.6), (14.0, 7.6, 1.5))           # along the north gallery to the entrance wall
    shot("emblem", (8.4, eye, cz), (16.0, 4.6, cz))                     # back to the doorway: the second emblem
    shot("aisle_n", (14.6, eye, -2.4), (4.0, 2.2, -4.4))
    shot("aisle_s", (14.6, eye, 3.4), (4.0, 2.2, 5.4))
    shot("stair_n", (6.6, eye, -3.4), (-3.5, 3.2, -3.6))                # through the side arch to the stair foot
    shot("mezzanine", (0.5, gallery, cz + 2.2), (-7.0, 9.4, cz))        # the two lamps beside the great west window
    shot("way", (1.0, eye, cz), (-9.0, 2.2, cz))                        # under the vault to the west door, its two lamps
    shot("arches", (28.5, eye, cz), (16.0, 3.4, cz))                    # the three arches from the forecourt's axis
    return out
