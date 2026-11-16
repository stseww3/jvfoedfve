"""obs_int_platevault: the box test scene of the plate vault and its darkroom (work package
interiors/platevault).

The room stands in a stand-in of its shell (box.py) on the skeleton's coordinates; the dressing is
scenes.obs.interiors.platevault, the same call the master scene makes once the room has moved in.
The east wall of the box is the wings' real east front (main/facade's sample), so the shot from
outside shows what the room does to the base storey: nothing, it stays a dark band.

The light sources are the light line's: the room offers them, sky.build() puts them down last.
"""
from artkit.canvas import Canvas

from scenes.obs import materials, sky
from scenes.obs.interiors import platevault

from . import box

BIOME = "obs_blue"
CATEGORY = "interiors"


def build():
    c = Canvas()
    box.build(c)
    n = platevault.build_platevault(c)
    sky.build(c)
    c.entity_counts = {"interiors": n}
    return c


def write_pack(pack_dir):
    """The materials' pack and the sky's: the scene stands in the map's hour, and without the
    sky's pictures the game's own sun would stand over the east front in the shot from outside."""
    return list(materials.pack(pack_dir) or []) + list(sky.pack(pack_dir) or [])
