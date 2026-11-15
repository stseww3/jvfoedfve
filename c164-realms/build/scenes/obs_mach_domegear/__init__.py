"""Test scene of the work package machines/domegear: the gear of the great dome in a stand-in dome
room (plan/packages/machines/domegear.md).

The shell is the assembly's own drum and dome (main/_dome), at the scene's true coordinates, so
every number is the skeleton's. What other cards will bring is stood in with plain blocks: the
dome-room floor with the hole of the pier envelope, the pier's cap, the fixed ring beam under the
ledge and the dome's foot ring above it (interiors/domeroom), and a bar of iron where the great
refractor points through the slit (machines/refractor). A few invisible lights stand in for the
room's lamps: they are this scene's, not handed to the lights package.

The shots are written from the numbers below:  python -m scenes.obs_mach_domegear
"""
import math

from artkit.canvas import Canvas

from scenes.obs import materials
from scenes.obs.common import blocks as B
from scenes.obs.common import skeleton as S
from scenes.obs.machines import dome
from scenes.obs.main import _dome as SHELL
from scenes.obs.main import _order as O

BIOME = "obs_blue"
BIOME_MARGIN = 48
BIOME_MARGIN_Y = 64
TIME = 14000                    # light version A, the default (INTERFACE: 18000 is B, 12900 is C)

CX, CZ = S.DOME_CENTRE
AX, AZ = S.DOME_AXIS
FLOOR, STAND = S.ROOF_FLOOR, S.ROOF_STAND
LEDGE_Y = S.DRUM[1]             # 23: the last course of the drum; the gear's ledge is its top
TUBE_DEG = 41.0                 # the refractor's elevation (A0, 11-15), due west
TUBE_PIVOT = (AX, S.PIER_TOP_Y + 5.0, AZ)
LAMPS = 10                      # stand-in lights round the room, and their level
LAMP_LEVEL = 12


def rings():
    """The drum's plan in rings of columns: the wall, the inner leaf behind it, the room."""
    body = O.disc(CX, CZ, S.DOME_R)
    inner = O.shrink(body)
    room = O.shrink(inner)
    return body - inner, inner - room, room


def build():
    c = Canvas()
    SHELL.build(c)
    _wall, leaf, room = rings()
    x0, z0, x1, z1 = S.PIER_ENVELOPE
    for x, z in room:
        if not (x0 <= x <= x1 and z0 <= z <= z1):
            c.set(x, FLOOR, z, B.FLOOR_WOOD.block)
    px0, pz0, px1, pz1 = S.PIER_CAP
    c.box(px0, FLOOR, pz0, px1, FLOOR, pz1, B.ASHLAR_FINE.block)
    edge = room - O.shrink(room)
    for x, z in edge:                                   # interiors/domeroom: the fixed ring beam
        c.set(x, LEDGE_Y, z, B.IRON_RIVETED.block)
    for x, z in leaf:                                   # interiors/domeroom: the dome's foot ring
        c.set(x, LEDGE_Y + 2, z, B.IRON_RIVETED.block)
    t = math.radians(TUBE_DEG)                          # machines/refractor: where the tube lies
    for i in range(-5, 11):
        c.set(int(math.floor(TUBE_PIVOT[0] - i * math.cos(t))), int(math.floor(TUBE_PIVOT[1] + i * math.sin(t))),
              int(math.floor(TUBE_PIVOT[2])), B.IRON_PLATE)
    n = dome.place(c)
    for k in range(LAMPS):
        a = 2 * math.pi * (k + 0.5) / LAMPS
        c.set(int(math.floor(AX + 9.0 * math.cos(a))), LEDGE_Y, int(math.floor(AZ + 9.0 * math.sin(a))),
              f"{B.LIGHT}[level={LAMP_LEVEL}]", keep=True)
    c.entity_counts = {"machines": n}
    return c


def write_pack(pack_dir):
    """The repainted stone and iron the gear is judged against."""
    return materials.pack(pack_dir)


def shots():
    """V8 as the card asks (the gear in one picture with the tube), the ring from close by, the foot
    of the slit, the hand gear, the whole room from a door."""
    out = []

    def shot(name, pos, look_at):
        out.append({"name": name, "pos": [round(v, 2) for v in pos], "look_at": [round(v, 2) for v in look_at],
                    "time": TIME})

    eye = STAND + S.EYE
    shot("v8", (AX + 9.5, eye, AZ + 1.5), (AX - 9.0, STAND + 9.0, AZ))
    shot("room", (AX + 6.5, eye, AZ - 8.0), (AX - 6.0, STAND + 5.0, AZ + 3.0))
    shot("ring_near", (AX - 4.0, STAND + 5.2, AZ + 6.0), (AX - 8.5, STAND + 6.3, AZ + 8.3))
    shot("ring_far", (AX + 7.0, STAND + 4.5, AZ - 3.0), (AX - 10.0, STAND + 6.3, AZ + 5.0))
    shot("slit_foot", (AX - 4.5, STAND + 3.0, AZ + 0.5), (AX - 11.0, STAND + 5.0, AZ))
    shot("weights", (AX - 6.0, eye, AZ + 5.0), (AX - 10.8, STAND + 3.0, AZ - 1.0))
    r = math.radians(dome.GEAR_DEG)
    gx, gz = AX + 10.9 * math.cos(r), AZ + 10.9 * math.sin(r)
    shot("hand_gear", (gx + 3.2, eye, gz + 2.6), (gx, STAND + 1.6, gz))
    shot("hand_gear_up", (gx + 4.5, eye, gz + 5.0), (gx, STAND + 4.5, gz))
    return out
