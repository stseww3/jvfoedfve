"""obs_int_starhall: the box test scene of the entrance hall (work package interiors/starhall).

The two versions stand side by side, each in a stand-in of the shell on the skeleton's coordinates:
version a (academic) at the scene origin, version b (workshop) SPACING blocks to the south, far enough
that neither shows in the other's views. The shot names carry the version (a_*, b_*).

The resource pack is the materials line's (the hall repaints only its blocks and places no model of its
own), so the room is seen in the same stone, iron, brass and wood it will wear once it moves in.
"""
from artkit.canvas import Canvas

from scenes.obs import materials
from scenes.obs.interiors import starhall

BIOME = "obs_blue"
CATEGORY = "interiors"
SPACING = 40
ORIGINS = {"a": (0, 0, 0), "b": (0, 0, SPACING)}


def build():
    c = Canvas()
    for version, origin in ORIGINS.items():
        starhall.build_box(c, origin, version)
    return c


def write_pack(pack_dir):
    return materials.pack(pack_dir)
