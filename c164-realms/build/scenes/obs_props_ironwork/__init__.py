"""Test scene of the work package props/ironwork: the whole family on one stage.

A long dressed-stone wall looks south and the cameras stand south of it. From west to east: the great
arched window frame in version A over a glazed opening, the same opening in version B (so the two
heads can be compared blind), a base-storey grille, then the entrance -- the open door, the fanlight
and the glazed canopy. An inspection ladder climbs the wall at the east end. On the paving in front
stand a run of balustrade scroll panels, a roof vent cowl and a floor grating.

The shots are written from the numbers below:  python -m scenes.obs_props_ironwork
"""
from artkit.canvas import Canvas

from scenes.obs import materials, sky
from scenes.obs.common import blocks as B
from scenes.obs.props import ironwork

BIOME = "obs_blue"
BIOME_MARGIN = 32
BIOME_MARGIN_Y = 32

STONE = B.ASHLAR_FINE.block
PANEL = B.ASHLAR_PANEL.block
EMBLEM = B.ASHLAR_EMBLEM
GLASS = B.WINDOW_LIT.block
PAVING = B.TUFF_SMOOTH.block
WALL_Z = -1
WALL_H = 12
ARCH = {"a": 3, "b": 11}        # the two arch windows, one to a version
GRILLE_X = 19
DOOR_X = 28
LADDER_X = 38
WALL_W0, WALL_W1 = -3, 44
TIME = 14000                    # light version A, the default (INTERFACE: 18000 is B, 12900 is C)


def _window(c, cx, y0, w, h, lit=GLASS):
    """A glazed opening w wide (odd), h tall, centred on cx with its foot at y0, in the wall face."""
    c.box(cx - (w - 1) // 2, y0, WALL_Z, cx + (w - 1) // 2, y0 + h - 1, WALL_Z, lit)


def _arches(c):
    """Each arch frame over its glazed opening; version B gets a stone keystone in the gap it leaves."""
    n = 0
    for version, cx in ARCH.items():
        _window(c, cx, 3, 3, 7)
        c.box(cx - 1, 2, WALL_Z, cx + 1, 2, WALL_Z, PANEL)             # the sunk panel / sill course
        n += ironwork.place(c, "window_arch", (cx, 3.0, WALL_Z), facing="south", version=version)
        if version == "b":
            c.box(cx, 9, WALL_Z, cx, 9, WALL_Z, EMBLEM)                # A3's keystone in the crown gap
    return n


def _entrance(c):
    """The door hung open, the fanlight above and the canopy over it. The three-wide opening (door
    y0-5, fanlight y5-6) is left out of the wall in build(), so a player walks through."""
    return ironwork.entrance(c, (DOOR_X, 0.0, WALL_Z), facing="south")


def _floor(c):
    """The pieces that stand on the paving in front of the wall."""
    n = 0
    for cx in (4, 7, 10):                                              # a balustrade run
        n += ironwork.place(c, "railing_panel", (cx, 0.0, 7.0), facing="south")
    n += ironwork.place(c, "vent_cowl", (LADDER_X - 4, 0.0, 6.0))
    n += ironwork.place(c, "grate_hatch", (DOOR_X + 4, 0.0, 8.0))
    return n


def build():
    c = Canvas()
    c.box(WALL_W0 - 1, -1, -1, WALL_W1 + 4, -1, 14, PAVING)
    # the wall, with the three-wide entrance (x DOOR_X-1..+1, y 0..6) left out so a player walks through
    c.box(WALL_W0, 0, WALL_Z, DOOR_X - 2, WALL_H - 1, WALL_Z, STONE)
    c.box(DOOR_X + 2, 0, WALL_Z, WALL_W1, WALL_H - 1, WALL_Z, STONE)
    c.box(DOOR_X - 1, 7, WALL_Z, DOOR_X + 1, WALL_H - 1, WALL_Z, STONE)
    c.box(DOOR_X - 2, 7, WALL_Z, DOOR_X + 2, 7, WALL_Z, EMBLEM)             # the lintel over the opening
    n = _arches(c)
    _window(c, GRILLE_X, 3, 3, 2)
    n += ironwork.place(c, "window_grille", (GRILLE_X, 3.0, WALL_Z), facing="south")
    n += _entrance(c)
    n += ironwork.place(c, "ladder", (LADDER_X, 1.0, WALL_Z), facing="south")
    n += _floor(c)
    sky.build(c, (0, 0, 0))             # A2's light sources go in last, when every piece is in place
    c.entity_counts = {"props": n}
    return c


def write_pack(pack_dir):
    """The repainted stone and glass the ironwork is judged against."""
    return materials.pack(pack_dir)


def shots():
    """The cameras: the whole stage, the two arch heads framed alike for a blind comparison, and each
    piece from about three blocks."""
    out = []

    def shot(name, pos, look_at):
        out.append({"name": name, "pos": [round(v, 2) for v in pos],
                    "look_at": [round(v, 2) for v in look_at], "time": TIME})

    shot("far", (20.0, 6.0, 34.0), (20.0, 5.0, -1.0))
    for v, cx in ARCH.items():
        shot(f"arch_{v}", (cx, 6.0, 9.0), (cx, 6.0, -1.0))
        shot(f"arch_{v}_head", (cx, 8.5, 6.0), (cx, 8.0, -1.0))
    shot("grille", (GRILLE_X, 4.0, 6.0), (GRILLE_X, 4.0, -1.0))
    shot("entrance", (DOOR_X, 4.5, 12.0), (DOOR_X, 4.0, -1.0))
    shot("door_near", (DOOR_X + 2.0, 3.0, 4.5), (DOOR_X + 1.0, 3.0, -1.0))
    shot("fanlight_near", (DOOR_X, 6.0, 4.5), (DOOR_X, 5.6, -1.0))
    shot("canopy_near", (DOOR_X - 3.5, 5.0, 5.0), (DOOR_X, 6.6, 1.0))
    shot("ladder_near", (LADDER_X + 2.0, 3.0, 4.5), (LADDER_X, 3.0, -1.0))
    shot("railing", (7.0, 1.6, 11.5), (7.0, 0.8, 7.0))
    shot("vent", (LADDER_X - 4.0, 1.6, 10.0), (LADDER_X - 4.0, 1.0, 6.0))
    shot("grate", (DOOR_X + 4.0, 2.4, 11.0), (DOOR_X + 4.0, 0.2, 8.0))
    return out
