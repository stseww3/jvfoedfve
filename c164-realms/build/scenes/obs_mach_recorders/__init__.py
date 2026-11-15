"""Test scene of the work package machines/recorders (plan/packages/machines/recorders.md).

The time room's console and east wall as a box: the room's clear space is x 2..13, z -25..-7, feet
at y 7, so the floor slab is y 6 and the ceiling block y 14. Everything here is a stand-in for what
other lines build -- the shell (main/shell), the instrument wall and the world clocks
(interiors/timeroom), the console and the desks (props/furniture), the lights (sky/_lightkit). What
this scene is for is the three pieces of machines/recorders, seen where the room will see them:

  console      the drum recorder and the telegraph on the console at the foot of the instrument
               wall, looked at from the door along the room's long axis (V10's line), then close.
  drum / tele  the two instruments from a hand away, at the height of an operator standing before
               the console, then from above.
  tube         the pneumatic tube on the east wall's pier, from the middle of the room and from
               below, so the bracket, the dial and the pipe up to the ceiling all read.

The room's own lamp is left out of the first two shots on purpose: what is judged is the metal, the
paper and the form, not the room's lighting.

    python -m scenes.obs_mach_recorders      writes shots.json from the layout below
"""
from artkit.blocks import st
from artkit.canvas import Canvas

from scenes.obs import materials
from scenes.obs.common import blocks as B
from scenes.obs.machines import recorders

BIOME = "obs_blue"
CATEGORY = "machines"
TIME = 14000

# the room, as interiors/timeroom.py has it
X0, X1 = 2, 13          # clear width
Z0, Z1 = -25, -7        # the instrument wall is the north end (z -25), the door the south (z -7)
FEET, CEIL = 7, 14      # the floor the room stands on; the ceiling block
FLOOR = FEET - 1        # the floor slab's own y
SILL = FEET             # the sill line: what stands on the console stands here

WALL = B.TUFF_BRICK.block if hasattr(B, "TUFF_BRICK") else B.TUFF.block
CONSOLE_Z = recorders.CONSOLE_Z         # -24, the console runs along the foot of the rack
CONSOLE_H = 1.0                         # props/furniture's console is a hand or so high
CONSOLE_DEEP = 1.0
WORK_LIGHT = 14                         # the test scene's work light: the light line's top, never 15


def _room(c):
    """The box: floor, four walls, ceiling. The room's own dressing (rack, clocks, desks) is left
    out; only the console the two instruments stand on is built, so they stand at the height and the
    set-back the room gives them."""
    for x in range(X0, X1 + 1):
        for z in range(Z0, Z1 + 1):
            c.set(x, FLOOR, z, WALL)
            c.set(x, CEIL, z, WALL)
    for y in range(FEET, CEIL):
        for x in range(X0, X1 + 1):
            c.set(x, y, Z0, WALL)        # the instrument wall
            c.set(x, y, Z1, WALL)        # the south wall (the door is a hole in it)
        for z in range(Z0, Z1 + 1):
            c.set(X0 - 1, y, z, WALL)    # west
            c.set(X1 + 1, y, z, WALL)    # east
    # the door: a two-wide, three-high hole in the south wall, on the room's long axis
    c.carve(7, FEET, Z1, 8, FEET + 2, Z1)

    # the console along the foot of the instrument wall, from x 6 to 10 (the middle bay and its
    # piers): a dark-wood top on two legs, clear under it
    for x in range(6, 11):
        c.set(x, FEET, CONSOLE_Z, B.WAINSCOT)
        c.set(x, FEET + 1, CONSOLE_Z, B.WAINSCOT)     # one block high; the pieces stand on top

    # the work light of the test scene: one invisible source over the console, at the level the
    # room's own console pendant will be. A test scene must see what it judges (main/shell does the
    # same); the room itself is lit by sky/_lightkit when it is in the tree.
    c.set(8, CEIL - 1, CONSOLE_Z + 1, f"{B.LIGHT}[level={WORK_LIGHT}]")
    return c


def console_top(x, z=None):
    """The y a piece stands on when it stands on the console."""
    return float(FEET + 2)


# the anchors: the drum's is its axis (17 units = 1.06 blocks above the machine's foot), the
# telegraph's is its armature pivot (12 units = 0.75 blocks up), the tube's is its body centre.
def drum_axis_y(y):
    """The y of the drum's axis when the recorder stands on `y`."""
    return y + recorders.DRUM_AXIS / 16.0


SLOTS = {
    "drum": dict(pos=(9.5, drum_axis_y(console_top(9)), CONSOLE_Z + 0.5), facing="south"),
    "telegraph": dict(pos=(6.5, console_top(6), CONSOLE_Z + 0.5), facing="south"),
    "tube": dict(pos=(float(X1 + 1), float(FEET + 1.6), -16.5), facing="west"),
}


def layout(c=None):
    c = c or Canvas()
    _room(c)
    n = recorders.build(c, (0, 0, 0), SLOTS)
    return c, n


def build():
    c, _ = layout()
    return c


def build_models():
    return recorders.models()


def write_pack(pack_dir):
    return materials.pack(pack_dir)


def shots():
    """The room's own view line from the door, then the pieces close."""
    out = []

    def shot(name, pos, look_at, time=TIME):
        out.append({"name": name, "pos": [round(v, 2) for v in pos], "look_at": [round(v, 2) for v in look_at],
                    "time": time})

    # V10's line: from the doorway, along the room's long axis at the instrument wall
    shot("v10_door", (7.5, FEET + 1.62, Z1 - 1.0), (7.5, FEET + 1.55, Z0))
    shot("console", (8.0, FEET + 2.10, -20.0), (8.0, FEET + 2.05, CONSOLE_Z + 0.5))
    # the drum recorder, from where the operator stands: the drum's axis is at y 10.13
    shot("drum", (9.5, FEET + 2.75, -21.6), (9.5, FEET + 2.05, CONSOLE_Z + 0.5))
    shot("drum_down", (9.5, FEET + 4.10, -22.0), (9.5, FEET + 2.00, CONSOLE_Z + 0.5))
    shot("drum_side", (11.9, FEET + 2.60, -22.8), (9.5, FEET + 2.00, CONSOLE_Z + 0.5))
    # the telegraph register, same three ways (it is a lower piece: top at y 9.5)
    shot("telegraph", (6.5, FEET + 2.40, -21.7), (6.5, FEET + 1.95, CONSOLE_Z + 0.5))
    shot("telegraph_down", (6.5, FEET + 3.60, -22.1), (6.5, FEET + 1.95, CONSOLE_Z + 0.5))
    shot("telegraph_side", (4.2, FEET + 2.35, -22.6), (6.5, FEET + 1.92, CONSOLE_Z + 0.5))
    # the pneumatic tube on the east wall's pier: from the room, and from below up the pipe
    shot("tube", (10.6, FEET + 2.05, -16.5), (X1 + 0.4, FEET + 2.00, -16.5))
    shot("tube_up", (11.6, FEET + 1.35, -16.5), (X1 + 0.4, FEET + 3.60, -16.5))
    # the whole console run from the south-west, so the pieces read as one room
    shot("all", (3.6, FEET + 2.55, -12.6), (10.0, FEET + 2.05, CONSOLE_Z + 0.6))
    return out
