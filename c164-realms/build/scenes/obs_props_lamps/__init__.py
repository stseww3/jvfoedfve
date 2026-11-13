"""Test scene of the work package props/lamps: the whole lamp family on one stage.

A long wall of dressed stone looks south and the cameras stand south of it. From west to east:
version A of the shade-and-bracket motif (bracket lamp on stone, caged lamp on iron plate, pendant
under an iron canopy), the same three in version B, then the lamps both versions share (signal lamp
lit and dark, desk lamp, wall-washing uplight, a festoon under a canopy). One street lamp stands by
itself on the paving east of the wall, so its pool of light and its outline are seen on their own.
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
SET_X = {"a": 0, "b": 12}       # where the set of each version starts
SHARED_X = 24
WALL_END = SHARED_X + 21
STREET = (54.5, 0.0, 8.5)


def _set(c, x0, version):
    """One version of the motif: its bracket lamp, caged lamp and pendant."""
    n = lamps.place(c, "bracket", (x0 + 2.5, 4.0, 0.0), version=version)
    c.box(x0 + 5, 0, -1, x0 + 7, WALL_H - 1, -1, PLATE)
    n += lamps.place(c, "cage", (x0 + 6.5, 3.5, 0.0), version=version)
    c.box(x0 + 8, 6, 0, x0 + 10, 6, 2, PLATE)
    n += lamps.place(c, "pendant", (x0 + 9.5, 6.0, 1.5), version=version)
    return n


def _shared(c, x0):
    n = lamps.place(c, "signal", (x0 + 1.5, 3.5, 0.0))
    n += lamps.place(c, "signal_off", (x0 + 3.5, 3.5, 0.0))
    c.box(x0 + 5, 0, 1, x0 + 6, 0, 1, WOOD)                     # a desk for the desk lamp
    n += lamps.place(c, "desk_green", (x0 + 6.0, 1.0, 1.5))
    n += lamps.place(c, "uplight", (x0 + 9.5, 0.0, 2.5), facing="north")
    c.box(x0 + 12, 6, 0, x0 + 19, 6, 2, PLATE)                  # a canopy, the festoon under its edge
    n += lamps.festoon(c, (x0 + 12.2, 5.8, 2.5), (x0 + 19.8, 5.8, 2.5))
    return n


def build():
    c = Canvas()
    c.box(-3, -1, -1, 60, -1, 14, PAVING)
    c.box(-2, 0, -1, WALL_END, WALL_H - 1, -1, STONE)
    n = 0
    for version, x0 in SET_X.items():
        n += _set(c, x0, version)
    n += _shared(c, SHARED_X)
    n += lamps.place(c, "street", STREET)
    sky.build(c, (0, 0, 0))         # A2's light sources go in last, when every lamp is in place
    c.entity_counts = {"props": n}
    return c


def write_pack(pack_dir):
    """The repainted stone and iron plate the lamps are judged against."""
    return materials.pack(pack_dir)
