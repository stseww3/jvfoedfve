"""obs_int_batteryroom_bare: the battery room's slice of the building with nothing in it (work package
interiors/batteryroom).

The same slice as obs_int_batteryroom (its box.py), the cavity under the time room closed and empty
as main/shell leaves it, and the same shot from the court, ext_base. What that scene's ext_base
shows more than this one's is what the room adds to the base storey as the court sees it: nothing
is to be brighter there.
"""
from artkit.canvas import Canvas

from scenes.obs import materials, sky
from scenes.obs_int_batteryroom import box

BIOME = "obs_blue"
CATEGORY = "interiors"


def build():
    c = Canvas()
    box.build(c, room=False)
    sky.build(c)
    c.entity_counts = {"interiors": 0}
    return c


def build_models():
    return {}


def write_pack(pack_dir):
    return list(materials.pack(pack_dir) or []) + list(sky.pack(pack_dir) or [])
