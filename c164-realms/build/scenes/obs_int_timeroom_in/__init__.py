"""obs_int_timeroom_in: a look only, on the preview branch and never delivered. The time-service
room dressed in the real building: the materials line's linings of the lit windows, the whole main
line (walls, shell, dome) as the assembly has it, the room's dressing in it, and the light line
over all of it with the building dressed (the sources behind the lit windows, as sky/lights places
them). The shots are obs_int_timeroom's.

BEHIND is the level of the sources behind a tall lit window of a wing: None is the light line's own
(10 today); the twin scene obs_int_timeroom_in12 builds with 12, the director's ruling of 11-16 05:00.

Whatever of the other packages is in the tree is placed as in the box scene.
"""
from artkit.canvas import Canvas

from scenes.obs import main, materials, sky
from scenes.obs.interiors import timeroom
from scenes.obs.main import shell
from scenes.obs.sky import _lightkit as L

BIOME = "obs_blue"
BIOME_MARGIN = 60
CATEGORY = "interiors"
BEHIND = None


def build(behind=None):
    behind = BEHIND if behind is None else behind
    c = Canvas()
    materials.build(c, (0, 0, 0))
    with shell.hall_open():
        main.build(c, (0, 0, 0))
    timeroom.build_timeroom(c)
    L.dress(c)
    was = dict(L.BEHIND)
    if behind is not None:
        L.BEHIND[L.LIT] = (behind, L.BEHIND[L.LIT][1])
    try:
        sky.build(c)
    finally:
        L.BEHIND.clear()
        L.BEHIND.update(was)
    return c


def write_pack(pack_dir):
    return list(materials.pack(pack_dir) or []) + list(sky.pack(pack_dir) or [])
