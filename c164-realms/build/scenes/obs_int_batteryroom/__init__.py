"""obs_int_batteryroom: the box test scene of the battery room (work package interiors/batteryroom).

The room stands in a slice of the real building (box.py) on the skeleton's coordinates; the
dressing is scenes.obs.interiors.batteryroom, the same call the master scene will make once the
room moves in. The resource pack is the materials line's; the models are listed in props.py.

The room offers its lamps to the light line; sky.build() settles them, as in the master scene.
"""
from artkit.canvas import Canvas

from scenes.obs import materials, sky
from scenes.obs.interiors import batteryroom

from . import box

BIOME = "obs_blue"
CATEGORY = "interiors"


def build():
    c = Canvas()
    box.build(c)
    room = batteryroom.build_batteryroom(c)
    sky.build(c)
    c.entity_counts = {"interiors": room["entities"]}
    return c


def write_pack(pack_dir):
    # the sky's pack too: the scene stands in the map's hour
    return list(materials.pack(pack_dir) or []) + list(sky.pack(pack_dir) or [])
