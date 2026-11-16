"""obs_int_timeroom: the box test scene of the time-service room (work package interiors/timeroom).

The room stands in a stand-in of its shell (box.py) on the skeleton's coordinates; the dressing is
scenes.obs.interiors.timeroom, the same call the master scene will make once the room moves in.
The resource pack is the materials line's; the models are listed in props.py (the lamps, the
room's own, and what the other packages bring once they are in the tree).

The light: the room offers its lamps to the light line; the sources behind the lit windows are the
light line's own. While sky/lights is not in the tree both are put down here, so the box is lit
the way the room will be.
"""
from artkit.canvas import Canvas

from scenes.obs import materials, sky
from scenes.obs.interiors import timeroom

from . import box

BIOME = "obs_blue"
CATEGORY = "interiors"


def build():
    c = Canvas()
    sources = box.build(c)
    timeroom.build_timeroom(c)
    box.light(c, sources)
    sky.build(c)
    return c


def write_pack(pack_dir):
    # the sky's pack too: the scene stands in the map's hour, and through its windows the game's own
    # sun would be a white and yellow square on the horizon
    return list(materials.pack(pack_dir) or []) + list(sky.pack(pack_dir) or [])
