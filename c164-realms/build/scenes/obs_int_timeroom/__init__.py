"""obs_int_timeroom: the box test scene of the time-service room (work package interiors/timeroom).

The room stands in a stand-in of its shell (box.py) on the skeleton's coordinates; the dressing is
scenes.obs.interiors.timeroom, the same call the master scene will make once the room moves in.
The resource pack is the materials line's: the room repaints nothing and has no model of its own.

    python -m scenes.obs_int_timeroom        prints the instrument wall and the plan of the room
"""
from artkit.canvas import Canvas

from scenes.obs import materials
from scenes.obs.interiors import timeroom

from . import box

BIOME = "obs_blue"
CATEGORY = "interiors"


def build():
    c = Canvas()
    box.build(c)
    got = timeroom.build_timeroom(c)
    box.light(c, got["lights"])
    return c


def write_pack(pack_dir):
    return materials.pack(pack_dir)
