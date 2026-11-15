"""Test scene of the work package props/lamps: the whole lamp family on one stage.

A long wall of dressed stone looks south and the cameras stand south of it. From west to east:
version A of the shade-and-bracket motif (three bracket lamps in a row at the spacing of the bays,
the caged lamp on iron plate, the pendant under an iron canopy), the same in version B, then the
lamps both versions share (signal lamp lit and dark, desk lamp, wall-washing uplight, a festoon
under a canopy). One street lamp stands by itself on the paving east of the wall, so its pool of
light and its outline are seen on their own, and beyond it a parapet pier with the low pier lamp on
its cap.

The shots are written from the numbers below:  python -m scenes.obs_props_lamps
"""
from artkit.canvas import Canvas

from scenes.obs import materials, sky
from scenes.obs.common import blocks as B
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


def build():
    c = Canvas()
    c.box(-3, -1, -1, int(STREET[0]) + 6, -1, 24, PAVING)
    c.box(-2, 0, -1, WALL_END, WALL_H - 1, -1, STONE)
    n = 0
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
    """The repainted stone and iron plate the lamps are judged against."""
    return materials.pack(pack_dir)


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
    return out
