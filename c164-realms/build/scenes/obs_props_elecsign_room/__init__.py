"""Test scene of the work package props/electrics-signs: the pieces that hang indoors, in a corner
of a room as the interiors line builds its rooms (plan/parts/L7-interiors.md: a dado of dark wood
under dressed stone, a floor of spruce boards, a boarded ceiling between iron beams).

  north wall   the wall telephone, hung by its foot on the dado's top edge, and beside it a signal
               desk with the telegraph key before the operator and a green desk lamp;
  west wall    a door, its number over it, and the way plates either side of it at the height of
               the eye: an arrow and S to the south of the door, N and an arrow to the north
               (who looks at the door has the south on his left).

The room is lit by four pendants of props/lamps at the top of their rank, two cells from each
wall, and by the desk lamp; the sky line places their sources. That leaves 9 to 11 on what hangs
on the two walls. Nothing of the night comes in: the room has no window.

The shots are written from the numbers below:  python -m scenes.obs_props_elecsign_room
"""
from artkit.canvas import Canvas

from scenes.obs import materials, sky
from scenes.obs.common import blocks as B
from scenes.obs.props import electrics, lamps, signs

BIOME = "obs_blue"
BIOME_MARGIN = 32
BIOME_MARGIN_Y = 32
TIME = 14000

# ---- the room: its clear inside, in cells -----------------------------------------------------------------
X0, X1 = 0, 6                   # seven wide
Z0, Z1 = 0, 6                   # seven deep; the north wall's face is z = Z0
FLOOR, CEILING = -1, 4          # the floor's boards and the ceiling's: the room is four high
DADO = 0                        # the row of dark wood at the walls' foot
BEAMS = (X0, (X0 + X1) // 2, X1)                    # the columns of the ceiling's iron beams
PENDANTS = tuple((x, z) for x in (X0 + 1.5, X1 - 0.5) for z in (Z0 + 1.5, Z1 - 0.5))
PENDANT_LEVEL = 12              # the top of a pendant's rank

# ---- what hangs and stands where --------------------------------------------------------------------------
PHONE = (X0 + 1.5, DADO + 1.0, float(Z0))           # the middle of its foot, on the north wall
DESK = (X0 + 3, X0 + 5)                             # its cells along the north wall; the top is DADO + 1
DESK_TOP = DADO + 1.0
KEY = ((DESK[0] + DESK[1] + 1) / 2.0, DESK_TOP, Z0 + 0.45)      # the middle of the key's foot
DESK_LAMP = (DESK[0] + 0.5, DESK_TOP, Z0 + 0.5)      # on the pedestal at the operator's left
DOOR_Z = Z0 + 3                                     # the door's cell in the west wall
PLATE_Y = DADO + 1.75                               # the way plates: the height of the eye
WAY = (("<", DOOR_Z + 2.45), ("S", DOOR_Z + 1.7), ("N", DOOR_Z - 0.7), (">", DOOR_Z - 1.45))    # label, z
NUMBER = ("12", DADO + 2.5)                         # the room's number, over the door


def _room(c):
    wood, stone = B.DARK_WOOD.block, B.ASHLAR_FINE.block
    for x in range(X0 - 1, X1 + 2):
        for z in range(Z0 - 1, Z1 + 2):
            inside = X0 <= x <= X1 and Z0 <= z <= Z1
            c.set(x, FLOOR, z, B.FLOOR_WOOD.block)
            c.set(x, CEILING, z, B.IRON_RIVETED.block if x in BEAMS else wood)
            if not inside:
                for y in range(DADO, CEILING):
                    c.set(x, y, z, wood if y == DADO else stone)
    for half, y in (("lower", DADO), ("upper", DADO + 1)):
        c.set(X0 - 1, y, DOOR_Z, f"{B.IRON_DOOR}[half={half},facing=west,hinge=left]")
    for x in range(DESK[0], DESK[1] + 1):
        c.set(x, DADO, Z0, wood if x in DESK else f"{B.DARK_WOOD.slab}[type=top]")


def build():
    c = Canvas()
    _room(c)
    n = 0
    for x, z in PENDANTS:
        n += lamps.place(c, "pendant", (x, float(CEILING), z), level=PENDANT_LEVEL)
    n += lamps.place(c, "desk_green", DESK_LAMP, facing="south")
    n += electrics.place(c, "wall_phone", PHONE, facing="south")
    n += electrics.place(c, "telegraph_key", KEY, facing="south")
    for label, z in WAY:
        n += signs.plate(c, label, (float(X0), PLATE_Y, z), facing="east")
    n += signs.plate(c, NUMBER[0], (float(X0), NUMBER[1], DOOR_Z + 0.5), facing="east")
    lit = sky.build(c, (0, 0, 0))   # A2's light sources go in last, when everything that glows is in place
    c.entity_counts = {"props": n, "sky": lit or 0}
    return c


def build_models():
    """The package's models and those of props/lamps: the room hangs four pendants and a desk lamp."""
    return {**lamps.models(), **signs.models(), **electrics.models()}


def write_pack(pack_dir):
    return list(materials.pack(pack_dir) or []) + list(sky.pack(pack_dir) or [])


# ---- the cameras ------------------------------------------------------------------------------------------
def shots():
    """The corner from the far end of the room; the telephone from its right and from its left;
    the key from the operator's chair and from its side, along the desk; the door with its
    plates, from under the row of pendants, and the southern pair from an arm's length."""
    out = []

    def shot(name, pos, look_at):
        out.append({"name": name, "pos": [round(float(v), 2) for v in pos],
                    "look_at": [round(float(v), 2) for v in look_at], "time": TIME})

    px, py, pz = PHONE
    kx, ky, kz = KEY
    door = DOOR_Z + 0.5
    shot("room", (X1 - 0.5, 1.62, Z1 - 0.5), (X0 + 0.9, 1.5, Z0 + 0.9))
    shot("phone_near", (px + 0.6, py + 0.8, pz + 1.5), (px, py + 0.72, pz + 0.2))
    shot("phone_left", (px - 0.95, py + 0.6, pz + 1.35), (px + 0.06, py + 0.75, pz + 0.2))
    shot("key_near", (kx - 0.2, ky + 0.55, kz + 1.05), (kx - 0.24, ky + 0.15, kz))
    shot("key_side", (kx - 0.6, ky + 0.3, kz + 0.35), (kx, ky + 0.12, kz))
    shot("door_plates", (X0 + 2.2, 1.62, door), (X0, 1.6, door))
    shot("way_near", (X0 + 0.75, PLATE_Y + 0.03, DOOR_Z + 2.15), (X0, PLATE_Y, DOOR_Z + 2.15))
    return out
