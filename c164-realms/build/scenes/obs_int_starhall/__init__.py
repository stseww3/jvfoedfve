"""obs_int_starhall: the box test scene of the entrance hall (work package interiors/starhall).

The two versions stand side by side, each in a stand-in of the shell on the skeleton's coordinates:
version a at the scene origin, version b SPACING blocks to the south, far enough that neither shows
in the other's views. The shot names carry the version (a_*, b_*).

The models and the resource pack are the master scene's, so the room is seen in the same materials
and with the same props as it will be once it moves in.
"""
from artkit.canvas import Canvas

import scenes.obs as obs
from scenes.obs.interiors import starhall

BIOME = "obs_blue"
SPACING = 40
ORIGINS = {"a": (0, 0, 0), "b": (0, 0, SPACING)}


def build():
    c = Canvas()
    for version, origin in ORIGINS.items():
        starhall.build_box(c, origin, version)
    return c


def build_models():
    return obs.build_models()


def write_pack(pack_dir):
    return obs.write_pack(pack_dir)
