"""Test scene of the work package props/lamps: the whole lamp family on one stage.

A long wall of dressed stone looks south and the cameras stand south of it. From west to east:
version A of the shade-and-bracket motif (three bracket lamps in a row at the spacing of the bays,
the caged lamp on iron plate, the pendant under an iron canopy), the same in version B, then the
lamps both versions share (signal lamp lit and dark, desk lamp, wall-washing uplight, a festoon
under a canopy). One street lamp stands by itself on the paving east of the wall, so its pool of
light and its outline are seen on their own, and beyond it a parapet pier with the low pier lamp on
its cap. West of the stage stands a short stretch of the main front, in its own courses as far up
as this wall goes, with two pilasters two bays apart: the bracket lamp of version A hangs on one
and that of version B on the other, where the pair at the entrance hangs, to be compared from as
far off as the entrance is looked at (the review, group #33010).

The shots are written from the numbers below:  python -m scenes.obs_props_lamps
"""
from artkit.canvas import Canvas

from scenes.obs import materials, sky
from scenes.obs.common import blocks as B
from scenes.obs.common import skeleton as S
from scenes.obs.props import lamps

BIOME = "obs_blue"
BIOME_MARGIN = 32
BIOME_MARGIN_Y = 32

STONE, PLATE, PAVING, WOOD = B.ASHLAR_FINE.block, B.IRON_PLATE, B.TUFF_SMOOTH.block, B.DARK_WOOD.block
WALL_H = 8
SET_X = {"a": 0, "b": 22}       # where the set of each version starts; a set is 20 wide
SHARED_X = 44
WALL_END = SHARED_X + 21
STREET = (WALL_END + 9.5, 0.0, 8.5)
PIER = (WALL_END + 13, 0, 3)    # the cell of a parapet pier as site/_kit.rail builds one: wall block, cap slab
PIER_TOP = 1.5                  # the cap's top above the ground
FRONT_X = (-30, -10)            # the stretch of the main front west of the stage
PAIR_X = {"a": -24, "b": -16}   # its two pilasters, and the version of the bracket lamp each carries
LAMP_Y = 4.0                    # where props/lamps hangs the pair at the entrance
TIME = 14000                    # light version A, the default (INTERFACE: 18000 is B, 12900 is C)


def _set(c, x0, version):
    """One version of the motif: its bracket lamp three times, its caged lamp and its pendant."""
    n = 0
    for i in range(3):
        n += lamps.place(c, "bracket", (x0 + 2.5 + 4 * i, 4.0, 0.0), version=version)
    c.box(x0 + 13, 0, -1, x0 + 15, WALL_H - 1, -1, PLATE)
    n += lamps.place(c, "cage", (x0 + 14.5, 3.5, 0.0), version=version)
    c.box(x0 + 16, 6, 0, x0 + 18, 6, 2, PLATE)
    n += lamps.place(c, "pendant", (x0 + 17.5, 6.0, 1.5), version=version)
    return n


def _shared(c, x0):
    n = lamps.place(c, "signal", (x0 + 1.5, 3.5, 0.0))
    n += lamps.place(c, "signal_off", (x0 + 3.5, 3.5, 0.0))
    c.box(x0 + 5, 0, 1, x0 + 6, 0, 1, WOOD)                     # a desk for the desk lamp
    n += lamps.place(c, "desk_green", (x0 + 6.0, 1.0, 1.5))
    n += lamps.place(c, "uplight", (x0 + 9.5, 0.0, 2.5), facing="north")
    c.box(x0 + 12, 6, 0, x0 + 19, 6, 2, PLATE)                  # a canopy, the festoon under its edge
    y = 6.0 - lamps.HANG
    n += lamps.festoon(c, (x0 + 12.2, y, 2.5), (x0 + 19.8, y, 2.5))
    return n


def _front(c):
    """The stretch of the main front: plinth, rusticated base storey, string course and dressed
    stone as main/facade lays them, the pilasters a block proud of the wall, and on each the
    bracket lamp of its version."""
    def course(y):
        return B.SLATE_BRICK.block if y <= S.PLINTH[1] else B.ASHLAR_ROUGH.block if y <= S.BASE[1] else STONE

    n = 0
    for y in range(WALL_H):
        c.box(FRONT_X[0], y, -1, FRONT_X[1], y, -1, course(y))
        for x in PAIR_X.values():
            c.set(x, y, 0, course(y))
    for version, x in PAIR_X.items():
        n += lamps.place(c, "bracket", (x + 0.5, LAMP_Y, 1.0), version=version)
    return n


def build():
    c = Canvas()
    c.box(FRONT_X[0] - 2, -1, -1, int(STREET[0]) + 6, -1, 24, PAVING)
    c.box(-2, 0, -1, WALL_END, WALL_H - 1, -1, STONE)
    n = _front(c)
    for version, x0 in SET_X.items():
        n += _set(c, x0, version)
    n += _shared(c, SHARED_X)
    n += lamps.place(c, "street", STREET)
    px, py, pz = PIER
    c.set(px, py, pz, B.ASHLAR_ROUGH.wall)
    c.set(px, py + 1, pz, B.ASHLAR_ROUGH.slab)
    n += lamps.place(c, "post", (px + 0.5, py + PIER_TOP, pz + 0.5))
    sky.build(c, (0, 0, 0))         # A2's light sources go in last, when every lamp is in place
    c.entity_counts = {"props": n}
    return c


def write_pack(pack_dir):
    """The repainted stone and iron plate the lamps are judged against, and the pictures of the
    map's sky: the stage stands in the map's hour (mood.py), and without them the game's own sun
    lies on the open western horizon, the brightest thing in every picture that looks that way."""
    return list(materials.pack(pack_dir) or []) + list(sky.pack(pack_dir) or [])


def shots():
    """The cameras: the whole stage from afar, each version's row and set framed alike (so the two
    can be compared blind), every lamp from about three blocks, the street lamp near and far."""
    out = []

    def shot(name, pos, look_at):
        out.append({"name": name, "pos": [round(v, 2) for v in pos], "look_at": [round(v, 2) for v in look_at],
                    "time": TIME})

    mid = (WALL_END - 2) / 2.0
    shot("far", (mid, 7.0, 36.0), (mid, 3.0, 0.0))
    for v, x0 in SET_X.items():
        shot(f"row_{v}", (x0 - 1.0, 2.0, 6.0), (x0 + 7.5, 4.2, 0.0))
        shot(f"set_{v}", (x0 + 14.0, 3.4, 6.0), (x0 + 14.0, 3.8, 0.0))
        shot(f"bracket_{v}_near", (x0 + 4.4, 4.4, 2.6), (x0 + 2.5, 4.1 if v == "a" else 3.8, 0.55))
        shot(f"cage_{v}_near", (x0 + 16.0, 4.0, 2.4), (x0 + 14.5, 3.7, 0.2))
        shot(f"pendant_{v}_near", (x0 + 15.4, 3.9, 3.9), (x0 + 17.5, 4.9 if v == "a" else 5.1, 1.5))
        shot(f"under_{v}", (x0 + 17.5, 1.7, 2.6), (x0 + 17.5, 5.0, 1.5))
    x0 = SHARED_X
    shot("shared", (x0 + 10.5, 3.4, 10.5), (x0 + 10.5, 3.2, 0.5))
    shot("signal_near", (x0 + 2.5, 3.7, 2.6), (x0 + 2.5, 3.3, 0.2))
    shot("desk_near", (x0 + 7.4, 2.3, 3.4), (x0 + 6.0, 1.4, 1.5))
    shot("uplight_near", (x0 + 11.2, 1.6, 4.2), (x0 + 9.5, 0.5, 2.2))
    shot("festoon_near", (x0 + 14.0, 4.3, 5.6), (x0 + 16.5, 5.5, 2.5))
    sx, _, sz = STREET
    shot("street", (sx + 4.0, 2.6, sz + 6.0), (sx, 3.0, sz))
    shot("street_head", (sx + 1.8, 4.3, sz + 2.1), (sx, 4.45, sz))
    shot("street_far", (sx - 8.5, 2.0, sz + 13.5), (sx - 2.5, 3.0, sz - 2.5))
    px, pz = PIER[0] + 0.5, PIER[2] + 0.5
    shot("post", (px + 2.4, 2.1, pz + 3.0), (px, 1.3, pz))
    shot("post_near", (px + 0.9, 2.15, pz + 1.3), (px, 1.8, pz))
    pair = sum(PAIR_X.values()) / 2.0 + 0.5                     # from a standing eye, ten and eight cells off
    shot("pilasters", (pair, S.EYE, 11.0), (pair, LAMP_Y - 0.4, 1.0))
    for v, x in PAIR_X.items():
        shot(f"pilaster_{v}", (x + 0.5, S.EYE, 9.0), (x + 0.5, LAMP_Y - 0.2, 1.0))
    return out
