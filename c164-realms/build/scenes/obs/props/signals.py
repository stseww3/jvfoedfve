"""props/signals -- the signalling of the rack railway (plan/round2.md, card props/signals; A0 g2
11-16 12:12: the train is how the map opens, and where its line comes into the station stands a
semaphore whose arm falls when the train comes; plan/fine.md: one thing, made fine in three
layers, before the next is begun).

One motif, the railway's own of the 1880s: a red blade on a slender iron mast, an oil lamp behind
a red glass, white enamel and black figures on what is read from the train.

The home signal. It stands where the line's owner puts poles and signals (site/_rail: on the left
of one going out, the side away from the mountain): beside the brow of the incline, HOME["s"]
along the line and HOME["out"] from its centre, on the rock beside the trestle. For the train
that climbs it is on the right, at the top of the slope, and it never stands between a passenger
and the observatory.

    far (60 blocks)    the post in two lengths (the shaft from the rock to the gear, four pixels
                       thick; the mast above it, three), the head and the arm: a mast, a blade to
                       one side, a lamp to the other. Nothing stands across the mast and it has
                       no ladder: a bracket against the sky, never a cross (plan red line 8).
    middle (10)        the head: a cap with a ball and a spike, the lamp on its shelf and strut
                       -- an iron case with a brass bezel, a chimney, a cowl and a handle --, the
                       spindle, the guide of the down rod. The arm: the blade with its band, the
                       casting at its root with two bolts and the boss with its oil cup, the
                       spectacle (a cast ring with the red glass), the crank. A block and a half
                       over the rails the gear: a collar where the post gets thinner, a clamp
                       with the bracket of the balance lever, the lever with its cast weight, a
                       brass wheel that turns the signal wire up to the lever, the number plate
                       on its two bands. The down rod from the crank to the lever; the wire from
                       the wheel back to the winch house, where the man who works the winch
                       works the signal, and where it goes into the wall a plate with a brass
                       roller under it. The shaft's lengths bolted flange to flange; the cast
                       foot on the rock.
    near (2)           the plate's figures; the bolt heads; rust run down the blade's white back
                       from the casting and down the shaft under every flange; oil run down the
                       mast under the spindle; soot on the cowl and the top of the lamp; the hub
                       and the set screw of the weight rubbed bright; the flame in the lamp's
                       back light.

The arm. A blade a block and a half long, red with a white band towards the train, white with a
black band towards the station; it turns on a spindle through the mast, and beyond the spindle it
carries the spectacle. At rest the blade is level (stop) and the red glass stands before the lamp:
the light is red. For a train the blade falls DROP degrees (the lower quadrant), the glass swings
up and away, and the lamp shows its own light: until the 1890s the light of "all right" was the
bare white one, which here is the amber every lamp of the hill has -- so the signal brings no new
colour of light, and red stays what it is everywhere else, a warning.

The lamp burns oil, the one flame among the hill's electric lamps: its lens shimmers, the red
glass before it with it, and in the small back light towards the station, by which the man in the
winch house sees that it burns, the flame itself stands and leans (moving pictures, artkit
pixelart.Frames: no command, no entity). The glass is lit only where the lamp stands behind it, so
the arm has two models: MODEL_STOP with the lit glass, MODEL_CLEAR with the same glass dark.

Moving pieces, for motion. Three entities, tagged TAG_ARM, TAG_ROD and TAG_WEIGHT, all placed at
"stop". The signal is worked as a real one is: the wire pulls the short end of the balance lever
down, the weight on its long end rises LIFT degrees, the down rod goes down TRAVEL with the
lever's eye and pulls the crank on the arm, and the blade falls; let go, the weight brings
everything back to stop. pose(clear), rod_pose(clear) and weight_pose(clear) are what one
`data merge` gives each entity for either position: the whole "transformation" (the anchors are
the spindle, the lever's eye and the lever's pin, not the middles of the models, so the
translation changes with the turn), and for the arm the item with the model of that position.
The train does not come round in a cycle: every trip is started by itself (motion/travel), and
the poses are hung on the trip. Until that is in the tree the arm stands at stop.

For the other lines:

    from scenes.obs.props import signals
    n += signals.signal(canvas, (x, y, z), yaw=point.yaw, origin=origin)

(x, y, z) is the point on the post's axis at the level of the rails; yaw is the way the front
looks, towards the train the signal speaks to (site/_rail: Point.yaw of one going out). build()
stands the home signal. Mounting and materials are _kit's. The test scene is
build/scenes/obs_props_signals.
"""
import functools
import math

from artkit import models as M
from artkit import pixelart

from ..common import palette as P
from . import _kit as K
from .signs import _picture, _plate_face

PREFIX = "prop_signal_"
DRESS = True                    # build() stands the home signal in the master scene

# How far the pieces are drawn (the bands of artkit.models; INTERFACE section 7: out of doors
# what counts in the outline or carries a light, and what stands on the line, stays in the far
# band; only the small parts on it come down a band).
VIEW_FAR, VIEW_SMALL = M.FAR, M.MID

IRON, IRON_D, BRASS_D = K.IRON, K.IRON_D, K.BRASS_D
POST = K.flat("iron", 3)        # mast and shaft: one tone, so drawing them out smears nothing
EDGE = K.flat("iron", 1)        # the edge and the back of a sheet
SOOT = K.flat("iron", 0)        # soot and oil; the wire
WORN = K.flat("iron", 5)        # iron rubbed bright
RUSTY = K.flat("old_copper", 1)
SG = P.RAMPS["signal"]
CR = P.RAMPS["cream"]
IR = P.RAMPS["iron"]
GL = P.RAMPS["glow"]
RUST = P.RAMPS["old_copper"]

# Measures in pixels (16 to the block): x to the right of whoever looks at the signal's front, y
# up, z towards him. The signal stands on the right of its track for the train it speaks to, so
# the track is on -x: the lamp is on that side, the blade and the balance weight on the other.
MAST_R = 1.5                    # the mast, from the gear up: three pixels thick
SHAFT_R = 2.0                   # the shaft, from the foot to the gear: four
BLADE = 23                      # the painted blade, from its tip to the casting at its root
ROOT = 3                        # the casting at the root reaches this far either side of the spindle
BLADE_H = 4
BAND = (3, 5)                   # the band across the blade: its pixels, counted from the tip
SHEET = (2.25, 2.75)            # the blade is a sheet this far before the mast's axis
LENS = (-7.5, 0.5)              # the lamp's axis: so far left of the spindle that the spectacle,
#                                 swung up by DROP, stands clear of the lens; half a pixel over it
CASE = 2.5                      # the lamp's case reaches this far from its axis: a cube of five
LAMP_Z = (-3.5, 1.5)            # ... from its back to its front; the bezel and the lens stand before it
FRAMES, PACE = 8, 2             # the moving pictures: so many frames, each so many ticks (a flame: A1's 2)
DROP = 45.0                     # degrees the arm falls from "stop" to "clear"
ROD = (3.0, 1.0)                # the down rod: x and z of its axis, from the mast's
ROD_LONG = 40.0                 # the rod's model is this long (with the wire under its eye a model stays within 48)
REACH = 4.0                     # the balance lever's pin stands this far beyond the rod
# The crank's pin stands over the spindle's level at "stop" as far as it stands under it at
# "clear", so the rod only goes up and down; the lever's short arm is so long that its eye does
# the same about the level of its pin.
CRANK = (ROD[0], ROD[0] * math.tan(math.radians(DROP / 2.0)))      # (3.0, 1.24): the pin at "stop", from the spindle
TRAVEL = 2.0 * CRANK[1]                                             # 2.49: the rod's travel
LIFT = 2.0 * math.degrees(math.atan2(CRANK[1], REACH))              # 34.5: degrees the balance lever turns
SHORT = math.hypot(REACH, CRANK[1])                                 # 4.19: the lever's short arm
PIVOT = (ROD[0] + REACH, 4.5)   # the balance lever's pin: x and y from the gear's anchor
WHEEL = (1.5, -1.5, 1.5)        # the wire's wheel on the gear: y and z of its axle, its radius
PLATE_UP = 8.0                  # the number plate's lower edge over the gear's anchor
CAP = 5.0                       # the mast ends this far over the spindle, under its cap
SWING = 16                      # ticks the arm takes from one position to the other
HEIGHT = 5.0                    # blocks from the rails to the spindle
GEAR_UP = 1.5                   # blocks from the rails to the collar, the gear's anchor: the lever, the wheel
#                                 and the plate stand at the height of the eye of who rides past
JOINT = 3.0                     # blocks: the shaft is cast in lengths of about this, bolted flange to flange
NUMBER = "73"                   # the figures on the plate: the signal is No. 73 of the hill (A6, plan/parts/numbers.md)
TAG_ARM, TAG_ROD, TAG_WEIGHT = "c164_signal_arm", "c164_signal_rod", "c164_signal_weight"
MODEL_STOP, MODEL_CLEAR = PREFIX + "arm", PREFIX + "arm_clear"

# The wire. It comes in level from behind the signal, WIRE_OFF to the right of the post's axis
# (as the front is seen) and WIRE_LEVEL over the rails at the plate on the wall it comes from.
WIRE_IN = (0.0, 1.0, 0.75)      # on that plate, where the wire goes into the wall: pixels from its anchor
WIRE_OFF = ROD[0] / 16.0
WIRE_LEVEL = GEAR_UP + (WHEEL[0] - WHEEL[2] - WIRE_IN[1]) / 16.0

# Where the home signal stands, for site/_rail: so far along the line from the buffers and so far
# to the left of its centre for one going out (A4, 11-16: the cell north of the brow's last level
# column, which the platform sees; the lamp's case, the nearest thing to the track, then lies 2.4
# blocks from the centre line, outside the three rows the train needs). The wire goes into the
# east face of the winch house, at its south corner (site/cablecar).
HOME = dict(s=7.5, out=3.0)

# The spectacle, as the train sees it: i the cast ring, R the red glass, three pixels square, on
# the lamp's axis while the blade is level.
_SPECTACLE = (".iii.",
              "iRRRi",
              "iRRRi",
              "iRRRi",
              ".iii.")


# ---- the pictures ---------------------------------------------------------------------------------------
def _blade_face(front):
    """One face of the blade with the casting at its root, as whoever looks at that face sees it:
    the front red with a white band, the back white with a black one and the rust that has run
    from the casting's bolts. From the front the tip is on the right, from the back on the left."""
    w = BLADE + 2 * ROOT
    grid = [[None] * w for _ in range(BLADE_H)]
    for c in range(w):
        tip = w - 1 - c if front else c                 # pixels from the tip
        for r in range(BLADE_H):
            low = r == BLADE_H - 1
            if tip >= BLADE:
                grid[r][c] = IR[2] if low else IR[3]
            elif BAND[0] <= tip <= BAND[1]:
                grid[r][c] = (CR[1] if low else CR[2]) if front else IR[0]
            elif front:
                grid[r][c] = SG[1] if r else SG[2]
            else:
                grid[r][c] = CR[1] if low else CR[2]
    for r, tip in ((1, BLADE + 1), (2, BLADE + 4)):     # the two bolts through the casting
        grid[r][w - 1 - tip if front else tip] = IR[5]
    if not front:
        for r, tip, tone in ((2, BLADE - 1, RUST[1]), (3, BLADE - 1, RUST[0]), (3, BLADE - 2, RUST[2])):
            grid[r][tip] = tone
    return grid


def _spectacle_face(front):
    """One face of the spectacle: the ring and the glass, dark, with one lighter pixel."""
    tones = {"i": IR[2], "R": SG[0], ".": None}
    grid = [[tones[ch] for ch in row] for row in _SPECTACLE]
    grid[1][1] = SG[1]
    return grid if front else [row[::-1] for row in grid]


def _lit(name, grid, ramp, share):
    """A small lit picture that shimmers with the lamp's flame: its pixels go a step up or down
    `ramp` now and then. The first frame is the picture itself."""
    return pixelart.shimmer(name, _picture(name + "_still", grid).paint(len(grid[0]), len(grid)), ramp,
                            frames=FRAMES, frametime=PACE, share=share)


def _red_light():
    """The red glass with the lamp behind it."""
    return _lit("signal_red_light", [[SG[1], SG[2], SG[1]], [SG[2], SG[3], SG[2]], [SG[1], SG[2], SG[1]]], SG, 0.4)


def _lens():
    """The lamp's lens: an oil flame behind a bull's eye, more orange than a filament and never
    lighter than the middle of the glow ramp (the review's cap on a lamp's glass, #78243)."""
    return _lit("signal_lens", [[GL[0], GL[1], GL[0]], [GL[1], GL[2], GL[1]], [GL[0], GL[1], GL[0]]], GL[:3], 0.5)


def _case_side():
    """A side of the lamp's case: the door with its two hinges and its latch, three air holes
    under the top."""
    grid = [[IR[2]] * 5 for _ in range(5)]
    grid[0] = [IR[1]] * 5
    for c in (1, 2, 3):
        grid[1][c] = IR[0]
    grid[2][0] = grid[4][0] = IR[4]
    grid[3][4] = IR[5]
    return grid


def _case_back():
    """The back of the lamp's case: the dark opening of the back light, a rivet in each corner."""
    grid = [[IR[2]] * 5 for _ in range(5)]
    for r in (1, 2, 3):
        for c in (1, 2, 3):
            grid[r][c] = IR[0]
    for r, c in ((0, 0), (0, 4), (4, 0), (4, 4)):
        grid[r][c] = IR[4]
    return grid


# ---- the models -----------------------------------------------------------------------------------------
def _arm(name, lit):
    """The arm: the blade, the casting at its root with the boss of the spindle and its oil cup,
    the crank behind it, and the spectacle on its neck beyond the spindle; `lit` with the lamp's
    light in the glass (the blade level), or dark. Anchor: the spindle, on the mast's axis; the
    blade lies along +x."""
    m = M.Model(name, px=1.0)
    z0, z1 = SHEET
    m.box((-ROOT, -BLADE_H / 2.0, z0), (BLADE + ROOT, BLADE_H / 2.0, z1), EDGE,
          faces={"s": _picture("signal_blade_front", _blade_face(True)),
                 "n": _picture("signal_blade_back", _blade_face(False))})
    lx, ly = LENS
    m.box((lx + CASE - 0.5, -1.0, z0), (-ROOT, 1.0, z1), IRON_D)            # the neck of the spectacle
    m.box((lx - CASE, ly - CASE, z0 + 0.05), (lx + CASE, ly + CASE, z1 + 0.05), EDGE, skip="ewud",
          faces={"s": _picture("signal_spectacle_front", _spectacle_face(True)),
                 "n": _picture("signal_spectacle_back", _spectacle_face(False))})
    if lit:
        m.box((lx - 1.5, ly - 1.5, z1 + 0.05), (lx + 1.5, ly + 1.5, z1 + 0.15), K.flat("signal_glow", 2),
              faces={"s": _red_light()}, skip="newud", emit=15, shade=False)
    m.tube("z", (0.0, 0.0), z0 - 0.5, z1 + 0.75, 1.5, IRON_D)               # the boss on the spindle
    m.tube("z", (0.0, 0.0), z1 + 0.75, z1 + 1.25, 0.75, WORN, sides=4)      # its nut
    m.tube("y", (0.0, z1 + 0.25), 1.5, 2.5, 0.5, BRASS_D, sides=4)          # the oil cup
    cx, cy = CRANK
    m.box((cx - 1.0, cy - 1.0, z0 - 0.75), (cx + 1.0, cy + 1.0, z0), IRON_D)        # the crank's lug
    m.tube("z", CRANK, ROD[1] - 0.5, z0 - 0.75, 0.5, IRON, sides=4)         # its pin, through the rod's eye
    return m


def _head():
    """The head, what the mast carries at its top: the cap with a ball and a spike, the spindle
    through the mast, and on a shelf beside it the lamp -- an iron case, a cube of five pixels,
    with a brass bezel round the lens towards the train, a back light towards the station, a
    chimney, a cowl black with soot and a handle -- and under the spindle the guide of the down
    rod and the oil that has run from the bearing. The mast itself is not in the model (it is
    drawn out through it), nor what burns in the lamp (_light). Anchor: the spindle, on the
    mast's axis."""
    m = M.Model(PREFIX + "head", px=1.0)
    m.tube("y", (0.0, 0.0), CAP - 0.5, CAP + 1.0, 2.25, IRON_D)             # the cap's moulding
    m.taper("y", (0.0, 0.0), CAP + 1.0, CAP + 3.0, 2.0, 1.0, IRON, steps=2)
    m.ball((0.0, CAP + 4.25, 0.0), 1.25, IRON_D, sides=8, layers=4)         # the ball
    m.taper("y", (0.0, 0.0), CAP + 5.5, CAP + 9.0, 0.6, 0.2, IRON, sides=4, steps=2)        # the spike
    m.tube("z", (0.0, 0.0), -2.5, SHEET[0] - 0.5, 0.75, IRON_D)             # the spindle
    m.tube("z", (0.0, 0.0), -3.0, -2.5, 1.25, IRON)                         # its collar at the back
    m.box((-0.5, -7.0, MAST_R), (0.5, -2.0, MAST_R + 0.05), SOOT, skip="newud")     # oil from the bearing
    lx, ly = LENS
    x0, x1, y0, y1 = lx - CASE, lx + CASE, ly - CASE, ly + CASE             # the case: x -10..-5, y -2..3
    z0, z1 = LAMP_Z
    m.tube("y", (0.0, 0.0), y0 - 2.0, y0, 2.0, IRON_D)                      # the clamp of the shelf
    m.box((x0 - 0.5, y0 - 1.0, z0 - 0.25), (-1.0, y0, z1 + 0.25), IRON)     # the shelf
    m.tube("y", (0.0, 0.0), y0 - 9.5, y0 - 8.0, 2.0, IRON_D)                # the clamp of its strut
    m.beam((-1.25, y0 - 8.75, -1.0), (x0 + 1.5, y0 - 1.0, -1.0), 0.75, 1.0, IRON_D)        # the strut
    side = _picture("signal_case_side", _case_side())
    m.box((x0, y0, z0), (x1, y1, z1), IRON_D,
          faces={"w": side, "e": side, "n": _picture("signal_case_back", _case_back()), "u": SOOT})
    m.box((lx - 2.0, ly - 2.0, z1), (lx + 2.0, ly + 2.0, z1 + 0.5), BRASS_D)        # the bezel
    m.tube("y", (lx, -1.0), y1, y1 + 1.5, 1.0, IRON)                        # the chimney
    m.taper("y", (lx, -1.0), y1 + 1.5, y1 + 2.5, 1.75, 0.75, SOOT, steps=2)         # its cowl
    for z in (-2.5, 0.0):                                                   # the handle over it
        m.box((lx - 0.25, y1 + 1.5, z), (lx + 0.25, y1 + 3.5, z + 0.5), IRON)
    m.box((lx - 0.25, y1 + 3.5, -2.5), (lx + 0.25, y1 + 4.0, 0.5), IRON)
    rx, rz = ROD
    m.box((MAST_R - 0.25, -16.0, rz - 0.75), (rx + 0.75, -15.0, rz + 0.75), IRON_D)         # the rod's guide
    return m


def _light():
    """What burns in the lamp, a small model of its own (a moving picture redraws its model's
    whole sheet at every frame): the lens in the bezel, towards the train, and the flame in the
    back light. Anchor: the spindle, as the head's."""
    m = M.Model(PREFIX + "light", px=1.0)
    lx, ly = LENS
    z0, z1 = LAMP_Z
    m.box((lx - 1.5, ly - 1.5, z1 + 0.5), (lx + 1.5, ly + 1.5, z1 + 0.7), K.GLOW_DIM,
          faces={"s": _lens()}, skip="newud", emit=15, shade=False)
    flame = pixelart.flame("signal_flame", (GL[0], GL[1], GL[2]), 3, 3, frames=FRAMES, frametime=PACE)
    m.box((lx - 1.5, ly - 1.5, z0 - 0.05), (lx + 1.5, ly + 1.5, z0), K.GLOW_DIM,
          faces={"n": flame}, skip="sewud", emit=15, shade=False)
    return m


def _gear():
    """The gear: the collar where the shaft becomes the mast, the clamp with the bracket and the
    pin of the balance lever, the brass wheel in its strap that turns the signal wire up to the
    lever, and over them the number plate on its two bands, towards the train. Neither mast nor
    shaft is in the model. Anchor: the collar's upper edge, on the post's axis."""
    m = M.Model(PREFIX + "gear", px=1.0)
    m.tube("y", (0.0, 0.0), -1.0, 0.0, 2.75, IRON_D)                        # the collar
    m.tube("y", (0.0, 0.0), 0.0, 1.0, 2.25, IRON)
    px, py = PIVOT
    m.tube("y", (0.0, 0.0), py - 1.5, py + 1.5, 2.25, IRON_D)               # the clamp
    m.box((1.25, py - 1.0, -1.0), (px + 1.0, py + 1.0, -0.25), IRON)        # the bracket, behind the lever
    m.tube("z", PIVOT, 0.25, 0.75, 1.0, IRON_D)                             # the washer before it
    m.tube("z", PIVOT, -1.5, 1.25, 0.5, WORN, sides=4)                      # the pin
    rx = ROD[0]
    wy, wz, wr = WHEEL
    m.tube("x", (wy, wz), rx - 0.5, rx + 0.5, wr, BRASS_D)                  # the wire's wheel
    m.tube("x", (wy, wz), rx - 1.0, rx + 1.25, 0.4, IRON_D, sides=4)        # its axle
    m.box((rx + 0.75, wy - 0.5, wz - 0.5), (rx + 1.25, py - 1.0, wz + 0.5), IRON)   # the strap it hangs in
    grid = _plate_face(NUMBER, "white")
    w, h = len(grid[0]), len(grid)
    m.box((-w / 2.0, PLATE_UP, MAST_R), (w / 2.0, PLATE_UP + h, MAST_R + 0.5), EDGE,
          faces={"s": _picture("signal_plate", grid)})
    for y in (PLATE_UP + 1.0, PLATE_UP + h - 2.0):                          # the bands the plate is bolted to
        m.tube("y", (0.0, 0.0), y, y + 1.0, 2.0, IRON_D)
    return m


def _weight():
    """The balance lever: a flat bar on its pin, the eye of the down rod and of the wire at its
    short end, a cast weight on the long one, its hub and its set screw rubbed bright. Anchor:
    the pin; the weight lies along +x."""
    m = M.Model(PREFIX + "weight", px=1.0)
    m.box((-SHORT - 0.5, -0.75, -0.25), (8.5, 0.75, 0.25), IRON)
    m.tube("z", (-SHORT, 0.0), -0.5, ROD[1] + 0.5, 0.5, IRON_D, sides=4)    # the eye's pin
    m.tube("z", (7.0, 0.0), -1.25, 1.25, 2.5, IRON_D)                       # the weight
    m.tube("z", (7.0, 0.0), -1.5, 1.5, 1.0, WORN)                           # its hub
    m.box((6.5, 2.5, -0.5), (7.5, 3.25, 0.5), WORN)                         # the set screw
    return m


def _long(name, radius):
    """A length of post: runs along +y from the anchor, 48 long, in one flat tone, and is drawn
    out to the length wanted."""
    m = M.Model(PREFIX + name, px=1.0)
    m.tube("y", (0.0, 0.0), 0.0, 48.0, radius, POST)
    return m


def _joint():
    """Where two lengths of the shaft are bolted together: two flanges, four bolts through them,
    and the rust that has run down the shaft from the joint. Anchor: the joint, on the post's
    axis."""
    m = M.Model(PREFIX + "joint", px=1.0)
    m.tube("y", (0.0, 0.0), -1.0, 0.0, 3.25, IRON_D)
    m.tube("y", (0.0, 0.0), 0.0, 1.0, 3.25, IRON)
    for x, z in ((2.5, 0.0), (-2.5, 0.0), (0.0, 2.5), (0.0, -2.5)):
        K.rivet(m, (x, 1.0, z), out="y")
        K.rivet(m, (x, -1.0, z), out="-y")
    m.box((-0.5, -6.0, SHAFT_R), (0.5, -1.0, SHAFT_R + 0.05), RUSTY, skip="newud")
    m.box((-SHAFT_R - 0.05, -4.0, -0.5), (-SHAFT_R, -1.0, 0.5), RUSTY, skip="nseud")
    return m


def _rod():
    """The down rod: half a pixel square, along +y from the anchor (the eye of the balance
    lever), ROD_LONG long, drawn out; and under the eye, in the lever's plane, the last of the
    signal wire, which comes up from the wheel."""
    m = M.Model(PREFIX + "rod", px=1.0)
    m.box((-0.25, 0.0, -0.25), (0.25, ROD_LONG, 0.25), EDGE)
    tail = PIVOT[1] + CRANK[1] - WHEEL[0]
    m.box((-0.2, -tail, -ROD[1] - 0.2), (0.2, 0.0, -ROD[1] + 0.2), SOOT)
    return m


def _wire():
    """The signal wire: runs along +z from the anchor, 48 long; drawn out (models.between)."""
    m = M.Model(PREFIX + "wire", px=1.0)
    m.box((-0.2, -0.2, 0.0), (0.2, 0.2, 48.0), SOOT)
    return m


def _wire_end():
    """Where the wire goes into the house: a plate bolted to the wall with the hole the wire runs
    through, and under the wire a brass roller in a fork, which carries it clear of the stone.
    Anchor: the middle of the plate's back, on the wall; the wire comes in at WIRE_IN."""
    m = M.Model(PREFIX + "wire_end", px=1.0)
    m.box((-2.5, -3.0, 0.0), (2.5, 3.0, 0.75), IRON, grain="y")
    for x in (-1.75, 1.75):
        for y in (-2.25, 2.25):
            K.rivet(m, (x, y, 0.75), out="z")
    m.box((-0.5, 0.5, 0.75), (0.5, 1.5, 0.8), SOOT, skip="newud")           # the hole
    for x0, x1 in ((-1.5, -0.9), (0.9, 1.5)):                               # the fork
        m.box((x0, -1.25, 0.75), (x1, 0.5, 3.5), IRON_D)
    m.tube("x", (-0.2, 2.5), -0.9, 0.9, 1.0, BRASS_D)                       # the roller
    m.tube("x", (-0.2, 2.5), -1.75, 1.75, 0.4, WORN, sides=4)               # its pin
    return m


def _foot():
    """The foot: a cast base bolted to the rock, a plinth and a moulded socket round the shaft
    (which is drawn out through it). Anchor: the middle of its underside; it is a block high."""
    m = M.Model(PREFIX + "foot", px=1.0)
    m.box((-5.0, 0.0, -5.0), (5.0, 1.5, 5.0), IRON_D, grain="x")
    for x in (-3.75, 3.75):
        for z in (-3.75, 3.75):
            K.rivet(m, (x, 1.5, z), out="y")
    m.tube("y", (0.0, 0.0), 1.5, 5.0, 3.75, IRON)
    m.tube("y", (0.0, 0.0), 5.0, 6.0, 4.25, IRON_D)
    m.taper("y", (0.0, 0.0), 6.0, 12.0, 3.75, 2.75, IRON, steps=3)
    m.tube("y", (0.0, 0.0), 12.0, 13.0, 3.25, IRON_D)
    m.tube("y", (0.0, 0.0), 13.0, 16.0, 2.5, IRON)
    return m


# ---- models and placing ---------------------------------------------------------------------------------
SPEC = {
    "foot": dict(build=_foot),
    "shaft": dict(build=lambda: _long("shaft", SHAFT_R)),
    "joint": dict(build=_joint),
    "gear": dict(build=_gear),
    "weight": dict(build=_weight),
    "mast": dict(build=lambda: _long("mast", MAST_R)),
    "rod": dict(build=_rod),
    "head": dict(build=_head),
    "light": dict(build=_light),
    "arm": dict(build=lambda: _arm(MODEL_STOP, True)),
    "arm_clear": dict(build=lambda: _arm(MODEL_CLEAR, False)),
    "wire": dict(build=_wire),
    "wire_end": dict(build=_wire_end),
}
SCALE = {PREFIX + kind: 1.0 for kind in SPEC}


@functools.lru_cache(maxsize=None)
def _models():
    return {PREFIX + kind: K.settle(spec["build"]()) for kind, spec in SPEC.items()}


def models():
    return dict(_models())


def _arm_turn(clear):
    return (("z", -DROP if clear else 0.0),)


def _lever_turn(clear):
    return (("z", LIFT / 2.0 if clear else -LIFT / 2.0),)


def _rod_length(height):
    """Blocks from the lever's eye to the crank's pin: the rod."""
    return height - GEAR_UP - PIVOT[1] / 16.0


def _rod_display(yaw, height, clear, view):
    """The rod's display NBT: drawn out to its length, and at "clear" TRAVEL lower."""
    nbt = M.display(_models()[PREFIX + "rod"], yaw=yaw, scale=(1.0, _rod_length(height) * 16.0 / ROD_LONG, 1.0),
                    view=view)
    if clear:
        move = nbt["transformation"]["translation"]
        move[1] = type(move[1])(float(move[1]) - TRAVEL / 16.0)
    return nbt


def pose(clear=False):
    """What the arm's entity is given for a position, as display NBT: dict(transformation, item).
    "stop" (the default, the pose it is placed in): the blade level, the glass lit. "clear": the
    blade DROP degrees down, the glass dark and away from the lamp."""
    nbt = M.display(_models()[MODEL_CLEAR if clear else MODEL_STOP], turns=_arm_turn(clear))
    return {"transformation": nbt["transformation"], "item": nbt["item"]}


def rod_pose(clear=False, height=HEIGHT):
    """What the down rod's entity is given for a position: dict(transformation). At "clear" it
    hangs TRAVEL pixels lower. `height` is the signal's."""
    return {"transformation": _rod_display(0.0, height, clear, VIEW_SMALL)["transformation"]}


def weight_pose(clear=False):
    """What the balance lever's entity is given for a position: dict(transformation). At "stop"
    the weight hangs half of LIFT under the level of its pin, at "clear" as far over it."""
    nbt = M.display(_models()[PREFIX + "weight"], turns=_lever_turn(clear))
    return {"transformation": nbt["transformation"]}


def _drawn(canvas, model, foot, length, yaw, view):
    """One entity of a model that runs 48 along +y, drawn out to `length` blocks from `foot`."""
    canvas.add_entity(foot[0], foot[1], foot[2],
                      M.display(model, yaw=yaw, scale=(1.0, length * 16.0 / 48.0, 1.0), view=view))
    return 1


def signal(canvas, at, facing="east", yaw=None, ground=None, height=HEIGHT, wire_to=None, clear=False,
           origin=(0, 0, 0)):
    """Stand a semaphore signal. `at` is the point on its post's axis at the level of the rails
    (scene coordinates). `yaw` (or `facing`) is the way its front looks: towards the train it
    speaks to; the blade lies to the right of the mast for that train and the lamp to the left,
    so the signal stands on the right of its track. `ground` is the y its foot stands on (found
    on the canvas under `at` when not given: the first block down). The spindle is `height`
    blocks over the rails. `wire_to` is the point on a wall behind the signal where its wire
    goes in, the middle of the plate there, with the way that wall looks: ((x, y, z), facing);
    for a level wire the point is WIRE_LEVEL over the rails and WIRE_OFF to the right of the
    post as the front is seen. None hangs no wire. The signal is placed at "stop"; clear=True
    places it at "clear" (for a picture). Returns the number of display entities: nine, one more
    for every joint of the shaft (a joint to every JOINT blocks of it), two more with the wire."""
    if height < GEAR_UP + 3.0:
        raise ValueError(f"a signal's spindle is at least {GEAR_UP + 3.0:g} blocks over the rails, not {height:g}")
    built = _models()
    yaw = K.FACING[facing] if yaw is None else yaw
    x, y, z = (at[i] + origin[i] for i in range(3))
    if ground is None:
        cell = [int(math.floor(x)), int(math.floor(y + 1e-6)), int(math.floor(z))]
        while cell[1] > y - 64 and not canvas.has(*cell):
            cell[1] -= 1
        if not canvas.has(*cell):
            raise ValueError(f"no ground under the signal at ({x:g}, {y:g}, {z:g})")
        ground = cell[1] + 1.0
    else:
        ground = ground + origin[1]
    collar, spindle, top = y + GEAR_UP, y + height, y + height + CAP / 16.0
    put = functools.partial(K.put, canvas, yaw=yaw)

    def tag(name):
        canvas.entities[-1][3]["Tags"].append(name)

    n = put(built[PREFIX + "foot"], (x, ground, z), view=VIEW_SMALL)
    n += _drawn(canvas, built[PREFIX + "shaft"], (x, ground, z), collar - ground, yaw, VIEW_FAR)
    lengths = max(1, int(round((collar - ground) / JOINT)))
    for i in range(1, lengths):
        n += put(built[PREFIX + "joint"], (x, ground + (collar - ground) * i / lengths, z), view=VIEW_SMALL)
    n += _drawn(canvas, built[PREFIX + "mast"], (x, collar, z), top - collar, yaw, VIEW_FAR)
    n += put(built[PREFIX + "gear"], (x, collar, z), view=VIEW_SMALL)
    px, py = PIVOT
    dx, dy, dz = K.turn(yaw, (px / 16.0, py / 16.0, 0.0))
    n += put(built[PREFIX + "weight"], (x + dx, collar + dy, z + dz), view=VIEW_SMALL, turns=_lever_turn(clear))
    tag(TAG_WEIGHT)
    dx, dy, dz = K.turn(yaw, (ROD[0] / 16.0, (py + CRANK[1]) / 16.0, ROD[1] / 16.0))        # the lever's eye at "stop"
    canvas.add_entity(x + dx, collar + dy, z + dz, _rod_display(yaw, height, clear, VIEW_SMALL))
    n += 1
    tag(TAG_ROD)
    n += put(built[PREFIX + "head"], (x, spindle, z), view=VIEW_FAR)
    n += put(built[PREFIX + "light"], (x, spindle, z), view=VIEW_FAR)
    n += put(built[MODEL_CLEAR if clear else MODEL_STOP], (x, spindle, z), view=VIEW_FAR, turns=_arm_turn(clear))
    tag(TAG_ARM)
    if wire_to is not None:
        (wx, wy, wz), wall = wire_to
        wx, wy, wz = wx + origin[0], wy + origin[1], wz + origin[2]
        n += K.put(canvas, built[PREFIX + "wire_end"], (wx, wy, wz), mount="wall", facing=wall, view=VIEW_SMALL)
        ex, ey, ez = K.turn(K.FACING[wall], tuple(v / 16.0 for v in WIRE_IN))
        a = (wx + ex, wy + ey, wz + ez)
        dx, dy, dz = K.turn(yaw, (ROD[0] / 16.0, (WHEEL[0] - WHEEL[2]) / 16.0, WHEEL[1] / 16.0))    # under the wheel
        b = (x + dx, collar + dy, z + dz)
        canvas.add_entity(a[0], a[1], a[2], M.between(built[PREFIX + "wire"], a, b, view=VIEW_SMALL))
        n += 1
    return n


def _home():
    """Where the home signal stands: dict(at, yaw, wire_to), read off site/_rail (the line) and
    site/cablecar (the winch house, where the wire goes in), or None while the line is not in
    the tree."""
    try:
        from ..site import _rail
    except ImportError:
        return None
    point = _rail.at(HOME["s"])
    seat = dict(at=point.off(-HOME["out"]), yaw=point.yaw, wire_to=None)
    try:
        from ..site import cablecar
        box = cablecar.WINCH
    except (ImportError, AttributeError):
        return seat
    x, y, z = seat["at"]
    _, _, dz = K.turn(point.yaw, (WIRE_OFF, 0.0, 0.0))
    seat["wire_to"] = ((box[2] + 1.0, y + WIRE_LEVEL, z + dz), "east")
    return seat


def build(canvas, origin=(0, 0, 0)):
    """What signals place in the master scene: the home signal beside the brow of the incline.
    Nothing is stood while the line is not in the tree or there is no rock under the place; the
    wire is hung only where the wall it goes into stands on the canvas."""
    if not DRESS:
        return 0
    seat = _home()
    if seat is None:
        return 0
    x, y, z = (seat["at"][i] + origin[i] for i in range(3))
    cell = [int(math.floor(x)), int(math.floor(y + 1e-6)), int(math.floor(z))]
    if canvas.has(*cell):
        return 0                # something is built where the post would pass the rails
    while cell[1] > y - 16 and not canvas.has(*cell):
        cell[1] -= 1
    if not canvas.has(*cell):
        return 0
    wire = seat["wire_to"]
    if wire is not None:
        wx, wy, wz = (wire[0][i] + origin[i] for i in range(3))
        if not canvas.has(int(math.floor(wx - 0.5)), int(math.floor(wy)), int(math.floor(wz))):
            wire = None
    return signal(canvas, seat["at"], yaw=seat["yaw"], wire_to=wire, origin=origin)
