"""obs_int_chartroom: the box test scene of the chart room (work package interiors/chartroom).

The room stands in a stand-in of its shell (box.py) on the skeleton's coordinates; the dressing is
scenes.obs.interiors.chartroom, the same call the master scene will make once the room moves in.
The resource pack is the materials line's; the models are the room's own, the lamps of props/lamps
and whatever else of the props line is in the tree (props.py).

The light: the room offers its lamps to the light line; the sources at the lit windows are the
light line's own. While sky/lights is not in the tree both are put down here, so the box is lit
the way the room will be.
"""
from artkit.canvas import Canvas

from scenes.obs import materials, sky
from scenes.obs.interiors import chartroom

from . import box

BIOME = "obs_blue"
CATEGORY = "interiors"


def build():
    c = Canvas()
    sources = box.build(c)
    chartroom.build_chartroom(c)
    box.light(c, sources)
    sky.build(c)
    return c


def write_pack(pack_dir):
    """The materials' pack and the sky's: the scene stands in the map's hour, and without the
    sky's pictures the game's own sun would hang in the windows."""
    return list(materials.pack(pack_dir) or []) + list(sky.pack(pack_dir) or [])
