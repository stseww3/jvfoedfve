"""obs_int_astroroom: the test scene of the astrograph room (work package interiors/astroroom).

The small dome as main/smalldome builds it stands on a stand-in of the south pavilion's flat roof
(the deck, and the iron plate before the door), on the skeleton's coordinates; the astrograph is
machines/astro's own call. The dressing is scenes.obs.interiors.astroroom, the same call the master
scene makes once the room has moved in.

The light sources are the light line's: the room offers them, sky.build() puts them down last.

The shots (shots.json): int_door, the first look from the doorway, towards the desk and the two
lamps; int_plate, the desk from where one stands at it: the open plate box under the red lamp, the
log under the desk lamp; int_slit, from the observing steps up along the tube to the slit;
int_north, from the stool under the tube to the plate cabinet; ext_door, the door and the slit
from the terrace; ext_se, the dome from the south-east at the height of the roof, the side the
boards V2 and V11 see it from: no window is lit.
"""
from artkit.canvas import Canvas

from scenes.obs import materials, sky
from scenes.obs.common import blocks as B
from scenes.obs.common import skeleton as S
from scenes.obs.interiors import astroroom
from scenes.obs.machines import astro
from scenes.obs.main import smalldome

BIOME = "obs_blue"
CATEGORY = "interiors"

DECK_Y = S.ROOF_FLOOR                           # 17: the pavilion's flat roof, the room's floor block
DECK = (0, S.SMALL_DOME_Z[0] - 2, S.SMALL_DOME_X[1] + 1, S.SMALL_DOME_Z[1] + 2)     # x 0..17, z 24..36


def build():
    c = Canvas()
    x0, z0, x1, z1 = DECK
    c.box(x0, DECK_Y, z0, x1, DECK_Y, z1, B.SLATE_SMOOTH.block)
    door = smalldome.door_cells()[0]
    c.set(door[0] - 1, DECK_Y, door[2], B.IRON_RIVETED.block)
    smalldome.build(c, (0, 0, 0))
    machine = astro.build(c, (0, 0, 0))
    n = astroroom.build_astroroom(c)
    sky.build(c)
    c.entity_counts = {"interiors": n, "machines": machine}
    return c


def write_pack(pack_dir):
    """The materials' pack and the sky's: the scene stands in the map's hour."""
    return list(materials.pack(pack_dir) or []) + list(sky.pack(pack_dir) or [])
