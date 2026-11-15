"""Test scene of the work package motion/loop: the beat board.

A long wall of dressed stone looks south and the cameras stand south of it. Every part stands a
quarter of a block off the wall and turns about the wall's normal, counter-clockwise for the
cameras. From west to east (plan/parts/motion.md section 10 says what each station is to show):

    wheels      two spoked wheels centred on their axes, a quarter of a turn to the step; the
                second is not aimed ahead (lead 0), to see what the two ticks of lead are for
    arms        two arms that turn about one end, each on a pin that stands still. The first gets
                the steps the kit works out; the second is cut into 8 on purpose, and its eye
                should be seen to move about two pixels on the pin between the steps
    pendulums   8 poses there and back (slow at the ends) and 4 (an even to and fro)
    crank       a crank disc, a connecting rod and a crosshead with its piston rod, of the steam
                engine's size (crank 1 block, rod 4): do the three stay on their pins
    slider      a block that slides along a rail, stops, and slides back
    lamp        a lamp that changes between its lit and its dark model (no part of the map blinks
                in this version; this is the kit's blink(), kept in working order)
    bar         a bar drawn out between two points (artkit.models.between) that turns about one
                end: does a part that is not scaled alike along its axes turn without a skew

Without the loop every part stands as it was placed; that is what tools/check.py and the offline
pictures see. On the real machine the driver runs the scene's start function once the scene
stands. Every camera is in the shot list twice (the second time as <name>_again), so that
sky/_tones.py --diff of the pair shows what has moved in between; the game must not be frozen
(tick freeze) while the pictures are taken.

Two stations are driven by hand (the second wheel's lead, the second arm's steps), so the check's
item "motion" is WARN for this scene, by design.

The shots are written from the numbers below:  python -m scenes.obs_mot_loop
"""
import math

from artkit import models as M
from artkit.canvas import Canvas

from scenes.obs import materials
from scenes.obs.common import blocks as B
from scenes.obs.motion import _kit as MK

from . import props

BIOME = "obs_blue"
BIOME_MARGIN = 32
BIOME_MARGIN_Y = 32

STONE, PLATE, PAVING = B.ASHLAR_FINE.block, B.IRON_PLATE, B.TUFF_SMOOTH.block
WALL_H = 10
WALL_END = 61
OUT = 0.25                      # blocks the parts stand off the wall's face
SOUTH, EAST = (0, 0, 1), (1, 0, 0)
LAMP_LEVEL = 11                 # the invisible lights the wall and the parts are seen by
TIME = 14000                    # light version A, the default (INTERFACE: 18000 is B, 12900 is C)

WHEELS = (((2.5, 3.5), None), ((6.5, 3.5), 0))          # where; the lead (None: the kit's)
ARMS = (((13.5, 4.5), None), ((22.5, 4.5), 8))          # where the pin is; steps in a turn (None: the kit's)
PENDULUMS = (((28.5, 5.5), 8), ((31.5, 5.5), 4))        # where the pivot is; poses there and back
SHAFT = (35.5, 3.5)
CRANK, ROD = 1.0, 4.0           # blocks from the shaft to the crank pin, and on to the crosshead pin
ROD_OUT = OUT + 0.25            # the plane of the connecting rod: before the disc, round the crank pin
CYLINDER = (42, 44)             # the cells along x of the block the piston rod runs into
SLIDER = (48.5, 3.5)
TRAVEL = 1.5                    # blocks the slider goes
LAMP = (53.5, 3.5)
BAR = (57.5, 3.5)
BAR_REACH, BAR_RISE, BAR_REV = 2.5, 30.0, 240           # blocks long, degrees above level, ticks a turn


def light(level):
    return f"{B.LIGHT}[level={level}]"


def _put(c, name, x, y, z=OUT):
    """One sample part at its own density: a model drawn at two pixels to the unit goes at scale 2."""
    model = props.model(name)
    c.add_entity(x, y, z, M.display(model, scale=model.px))
    return 1


def _wheels(c):
    n = 0
    for (x, y), lead in WHEELS:
        n += _put(c, "wheel", x, y)
        MK.spin(c, SOUTH, MK.ENGINE_REV, lead=lead)
    return n


def _arms(c):
    n = 0
    for (x, y), keys in ARMS:
        n += _put(c, "pin", x, y)
        n += _put(c, "arm", x, y)
        MK.spin(c, SOUTH, MK.ORRERY["mercury"], keys=keys)
    return n


def _pendulums(c):
    n = 0
    for (x, y), keys in PENDULUMS:
        n += _put(c, "pendulum", x, y)
        MK.swing(c, SOUTH, 5.0, MK.PENDULUM, keys=keys)
    return n


def _crank(c):
    """The rest pose is the dead centre with the crank pin towards the cylinder: disc, rod and
    piston rod in one line, the crosshead as far east as it goes."""
    x, y = SHAFT
    head = x + CRANK + ROD
    n = _put(c, "disc", x, y)
    MK.spin(c, SOUTH, MK.ENGINE_REV)
    n += _put(c, "guide", head, y, ROD_OUT)
    n += _put(c, "crosshead", head, y, ROD_OUT)
    MK.crank(c, SOUTH, EAST, CRANK, ROD, MK.ENGINE_REV, turn=False)
    n += _put(c, "rod", head, y, ROD_OUT)
    MK.crank(c, SOUTH, EAST, CRANK, ROD, MK.ENGINE_REV)
    c.box(CYLINDER[0], int(y), 0, CYLINDER[1], int(y), 0, PLATE)
    return n


def _slider(c):
    x, y = SLIDER
    n = _put(c, "rail", x, y)
    n += _put(c, "slider", x, y)
    MK.slide(c, EAST, [(0, TRAVEL, 30), (60, 0.0, 30)], 120)
    return n


def _lamp(c):
    x, y = LAMP
    n = _put(c, "lamp", x, y, 0.01)
    MK.blink(c, props.PREFIX + "lamp_dark", *MK.BLINK)
    return n


def _bar(c):
    x, y = BAR
    rise = math.radians(BAR_RISE)
    a = (x, y, OUT)
    b = (x + BAR_REACH * math.cos(rise), y + BAR_REACH * math.sin(rise), OUT)
    c.add_entity(a[0], a[1], a[2], M.between(props.model("bar"), a, b))
    MK.spin(c, SOUTH, BAR_REV)
    return 1


def build():
    c = Canvas()
    c.box(-3, -1, -1, WALL_END + 2, -1, 28, PAVING)
    c.box(-1, 0, -1, WALL_END, WALL_H - 1, -1, STONE)
    n = _wheels(c) + _arms(c) + _pendulums(c) + _crank(c) + _slider(c) + _lamp(c) + _bar(c)
    for x in range(1, WALL_END, 3):
        c.set(x, 4, 1, light(LAMP_LEVEL), keep=True)
    c.entity_counts = {"motion": n}
    return c


def write_pack(pack_dir):
    """The repainted stone and iron plate the parts are seen against."""
    return materials.pack(pack_dir)


def shots():
    """The cameras, each twice: the whole board, then station by station, with a close look at
    the pins of the arms and of the crank."""
    views = []

    def view(name, pos, look_at):
        views.append((name, pos, look_at))

    mid = (WALL_END - 1) / 2.0
    view("far", (mid, 5.0, 26.0), (mid, 4.0, 0.0))
    x = (WHEELS[0][0][0] + WHEELS[1][0][0]) / 2.0
    y = WHEELS[0][0][1]
    view("wheels", (x, y, 4.5), (x, y, 0.0))
    for name, ((x, y), _keys) in zip(("arm", "arm_coarse"), ARMS):
        view(name, (x, y, 6.0), (x, y, 0.0))
        view(name + "_pin", (x, y, 1.6), (x, y, OUT))
    x = (PENDULUMS[0][0][0] + PENDULUMS[1][0][0]) / 2.0
    y = PENDULUMS[0][0][1] - 1.0
    view("pendulums", (x, y, 4.0), (x, y, 0.0))
    x, y = SHAFT
    view("crank", (x + 4.0, y, 5.0), (x + 4.0, y, 0.0))
    view("crank_pins", (x + 2.0, y + 0.2, 2.2), (x + 2.0, y, ROD_OUT))
    x, y = SLIDER
    view("slider", (x + TRAVEL / 2.0, y, 3.0), (x + TRAVEL / 2.0, y, 0.0))
    x, y = LAMP
    view("lamp", (x, y, 2.0), (x, y, 0.0))
    x, y = BAR
    view("bar", (x, y, 4.5), (x, y, 0.0))
    out = []
    for again in ("", "_again"):
        for name, pos, look_at in views:
            out.append({"name": name + again, "pos": [round(float(v), 2) for v in pos],
                        "look_at": [round(float(v), 2) for v in look_at], "time": TIME})
    return out
