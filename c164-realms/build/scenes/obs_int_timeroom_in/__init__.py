"""obs_int_timeroom_in: a look only, on the preview branch and never delivered. The time-service
room dressed in the real building: the materials line's linings of the lit windows, the whole main
line (walls, shell, dome) as the assembly has it, the room's dressing in it, and the light line
over all of it with the building dressed (the sources of the lit windows and the wall wash, as
sky/lights' wash round places them). The shots are obs_int_timeroom's.

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


def build():
    c = Canvas()
    materials.build(c, (0, 0, 0))
    with shell.hall_open():
        main.build(c, (0, 0, 0))
    timeroom.build_timeroom(c)
    L.dress(c)
    sky.build(c)
    return c


def write_pack(pack_dir):
    return list(materials.pack(pack_dir) or []) + list(sky.pack(pack_dir) or [])
