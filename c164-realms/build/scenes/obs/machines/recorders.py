"""machines/recorders -- the drum recorder, the telegraph and the pneumatic tube of the time room.

Card plan/packages/machines/recorders.md; detail plan/parts/A5-machines.md 2.10; ART-PLAN 7.2, 8.
The card's fourth piece, the world-clock wall, was dropped before this round: the time room makes
its own five stopped slave dials (A0 #529), so what is left here is three standing things on the
room's console and east wall.

  mach_rec_drum       the drum recorder: a brass drum on a dark-wood base, cream chart paper round
                      the drum, a pen carriage on a brass slide above it, a paper supply reel at the
                      back and a tray at the front. Sits on the console's east end.
  mach_rec_telegraph  the telegraph register: a brass sounder with its armature and coil box, a
                      paper-tape reel on a spindle, the tape leaving east towards the drum.
  mach_rec_tube       the pneumatic tube terminal: a brass mouthpiece and dial on a cast-iron
                      bracket down the pier, the carrier door, the pipe stub going up to the ceiling.

THE ONE THING TO KNOW about the sizes: every model is drawn at px = scale, so the texture keeps
16 pixels to the block at any scale, the same density as the blocks and the other models (A5 1.2).

Axis points for A8 (this round everything is still; A0 #505 -- the drum and the tape do not turn).
The pieces are still cut apart and anchored on their turning centres, so switching them on later is
a matter of turning the entity, not redrawing it:

  mach_rec_drum        anchor = the drum's axis, at the middle of the drum, axis horizontal along x
                       (the drum's flat faces look east and west). A turn about x spins the drum.
  mach_rec_tape_out    anchor = the paper reel's axis, same way; a turn about x runs the tape.
  mach_rec_telegraph   anchor = the sounder's armature pivot (top of the coil box, on its centre
                       line); a small turn about x makes the armature clack.

The light: the drum's chart lamp is the room's warm point on the console, offered to A2 through
sky/_lightkit.take, level 7 (a recorder's lamp is a third-rank light, below a window).

Placing: build(canvas, origin, slots) takes the time room's own SLOTS table when it is in the tree
(interiors/timeroom.SLOTS: "drum", "telegraph", "tube"), and falls back to the same cells read from
the room's geometry when it is not:
  drum       (9.5, 8.0, -23.5) facing south     -- the console's east end
  telegraph  (7.5, 8.0, -23.5) facing south     -- the console just west of the telegraph key
  tube       (14.0, 8.0, <the pier south of the message desk>) facing west
Each piece can also be placed alone by its own function, which is what the room will call.
"""
import functools
import math

import numpy as np

from artkit import models as M
from artkit import pixelart as A

from ..common import blocks as B
from ..common import palette as P

PREFIX = "mach_rec_"

# the way a piece looks -> the yaw that points its +z that way (same table as props/_kit and clock.py)
FACING = {"south": 0.0, "west": 90.0, "north": 180.0, "east": -90.0}

# --- the room's cells, as interiors/timeroom.py has them (used when that module is not in the tree)
SILL = 8                  # the sill line: what stands on the console stands on this y
ROOM_X = (2, 13)          # the room's clear width
CONSOLE_Z = -24           # the console runs along the foot of the instrument wall
DRUM_X = 9                # the drum recorder's cell (the console's east end)
KEY_X = 7                 # the telegraph key's cell; the telegraph sits just west of it
EAST = 14                 # the east wall's face: x of the first air cell west of it
DESK_PIER_Z = -16         # the pier south of the message desk: the tube runs down this one
TUBE_TOP = 14             # the ceiling block: the pipe leaves the room here
TUBE_FOOT = 9.2           # the terminal's bottom, a hand above the sill

DEFAULT_SLOTS = {
    "drum": dict(pos=(DRUM_X + 0.5, float(SILL), CONSOLE_Z + 0.5), facing="south"),
    "telegraph": dict(pos=(KEY_X - 1.5, float(SILL), CONSOLE_Z + 0.5), facing="south"),
    "tube": dict(pos=(float(EAST), float(SILL), DESK_PIER_Z + 0.5), facing="west"),
}

# --- sizes, in blocks (the room must leave these clear; the card's own numbers follow A5 2.10)
DRUM_W, DRUM_D, DRUM_H = 0.95, 0.72, 0.62     # the case under the drum
DRUM_R = 0.20                                  # the drum's radius; it lies across the machine
CHART_W = 0.30                                 # the drum's width, along its axis
TELE_W, TELE_D, TELE_H = 0.62, 0.44, 0.30     # the telegraph's base and its coil box
TUBE_R = 0.11                                  # the pneumatic pipe's radius

# the recorder's lamp: the console's one warm point (offered to A2; a third-rank light)
LAMP_LEVEL = 7
LAMP_ABOVE = 0.9                               # above the drum's axis, on its east side

# --- materials (palette only) ---------------------------------------------------------------------
BRASS = P.mat("brass")
BRASS_D = P.mat("brass_dark")
BRASS_F = P.mat("brass_flat")
IRON = P.mat("iron")
IRON_D = P.mat("iron_dark")
COPPER = P.mat("old_copper")
WOOD = P.mat("dark_wood")
WOOD_D = P.mat("dark_wood", base=1)
WOOD_L = P.mat("dark_wood", base=3)
CREAM = P.mat("cream")
CREAM_F = P.mat("cream", kind="flat", bevel=0)
PORCELAIN = P.mat("porcelain")


# ==================================================================================================
# the drum recorder
# ==================================================================================================
def _chart(rng, w, h):
    """A chart's worth of pen trace: one slow wave across the paper, drawn a pixel wide in a darker
    step of the cream ramp. Reads as a record being written, from a few blocks away."""
    grid = [["p" for _ in range(w)] for _ in range(h)]
    for x in range(w):
        y = h / 2 + 2.6 * math.sin(2 * math.pi * (x / float(w)) * 1.15 + 0.4) \
            + 0.9 * math.sin(2 * math.pi * (x / float(w)) * 3.4)
        yi = int(round(min(max(y, 1), h - 2)))
        grid[yi][x] = "t"
    return ["".join(row) for row in grid]


def _drum():
    """The drum recorder: a dark-wood case, the brass drum on its axis across the machine, cream
    chart paper wound round it, a pen carriage on a slide over the drum, the paper reel behind and
    a drawer under. Anchor: the drum's axis, middle of the drum, axis along x."""
    m = M.Model(PREFIX + "drum", px=1.0, anchor=(0.0, 0.0, 0.0))
    hw, hd = DRUM_W / 2, DRUM_D / 2

    # the case: a plinth, then the body with a moulded top edge; the drawer face and its pull
    m.box((-hw, 0.0, -hd), (hw, 0.07, hd), WOOD_D, skip="d")
    m.box((-hw, 0.07, -hd), (hw, DRUM_H - 0.12, hd), WOOD, skip="d")
    m.box((-hw - 0.015, DRUM_H - 0.12, -hd - 0.015), (hw + 0.015, DRUM_H - 0.08, hd + 0.015), WOOD_L, skip="d")
    # the drawer under the drum, with a brass pull
    m.box((-hw * 0.72, 0.13, hd - 0.004), (hw * 0.72, 0.30, hd + 0.004), WOOD_D, skip="d")
    m.box((-0.05, 0.20, hd), (0.05, 0.225, hd + 0.022), BRASS, skip="d")

    # the two brass standards that carry the drum's shaft, left and right
    for sx in (-1, 1):
        x0 = sx * (CHART_W / 2 + 0.055)
        x1 = x0 + sx * 0.045
        m.box((min(x0, x1), DRUM_H - 0.10, -0.055), (max(x0, x1), DRUM_H + DRUM_R + 0.10, 0.055), BRASS, skip="d")
        # the bearing block the shaft runs in
        m.box((min(x0, x1), DRUM_H + DRUM_R - 0.015, -0.045),
              (max(x0, x1), DRUM_H + DRUM_R + 0.045, 0.045), BRASS_D, skip="d")

    # the shaft, then the drum itself with its chart paper; the paper is a tube one pixel proud
    m.tube("x", (0.0, DRUM_H + DRUM_R), -CHART_W / 2 - 0.075, CHART_W / 2 + 0.075, 0.028, BRASS_D, sides=8)
    m.tube("x", (0.0, DRUM_H + DRUM_R), -CHART_W / 2, CHART_W / 2, DRUM_R, BRASS_F, sides=12)
    chart = P.mat("cream", kind="flat", base=2, bevel=0)
    m.tube("x", (0.0, DRUM_H + DRUM_R), -CHART_W / 2 + 0.004, CHART_W / 2 - 0.004, DRUM_R + 0.006,
           chart, sides=12, cap=None)
    # the chart's pen trace, a thin raised band on the paper (16 px to the block: one pixel is 1/16)
    px = 1 / 16.0
    for i in range(6):
        y = DRUM_H + DRUM_R + (i - 2.5) * px * 1.6
        m.box((-CHART_W / 2 + 0.01, y, DRUM_R + 0.004), (CHART_W / 2 - 0.01, y + px, DRUM_R + 0.012),
              P.mat("cream", base=0, kind="flat", bevel=0), skip="d")

    # the pen carriage: a slide bar over the drum and the pen arm hanging from it
    m.box((-hw * 0.92, DRUM_H + DRUM_R * 2 + 0.045, -hd * 0.55),
          (hw * 0.92, DRUM_H + DRUM_R * 2 + 0.075, -hd * 0.55 + 0.030), BRASS_D, skip="d")
    m.box((-0.028, DRUM_H + DRUM_R + 0.02, -hd * 0.52), (0.028, DRUM_H + DRUM_R * 2 + 0.050, -hd * 0.30), BRASS, skip="d")
    # the pen itself, a dark nib just touching the paper at the top of the drum
    m.box((-0.008, DRUM_H + DRUM_R * 2 - 0.004, -hd * 0.34), (0.008, DRUM_H + DRUM_R * 2 + 0.030, -hd * 0.30),
          IRON_D, skip="d")

    # the paper supply reel at the back, on its own brass fork, and the paper running to the drum
    reel_z = -hd + 0.10
    for sx in (-1, 1):
        m.box((sx * (CHART_W / 2 + 0.02), DRUM_H - 0.02, reel_z - 0.02),
              (sx * (CHART_W / 2 + 0.02) - 0.03 if sx > 0 else sx * (CHART_W / 2 + 0.02) + 0.03,
               DRUM_H + 0.20, reel_z + 0.02), BRASS_D, skip="d")
    m.tube("x", (0.0, DRUM_H + 0.10), -CHART_W / 2 - 0.01, CHART_W / 2 + 0.01, 0.075, CREAM_F, sides=10)
    return m


# ==================================================================================================
# the telegraph register
# ==================================================================================================
def _telegraph():
    """The telegraph: a wooden base, the coil box, the sounder's armature over it on two posts, the
    tape reel on a brass spindle at the east end and the tape leaving it. Anchor: the armature's
    pivot (the top of the coil box's centre line)."""
    m = M.Model(PREFIX + "telegraph", px=1.0, anchor=(0.0, TELE_H, 0.0))
    hw, hd = TELE_W / 2, TELE_D / 2

    m.box((-hw, 0.0, -hd), (hw, 0.035, hd), WOOD_D, skip="d")                    # base
    m.box((-hw * 0.86, 0.035, -hd * 0.86), (hw * 0.86, TELE_H - 0.09, hd * 0.86), WOOD, skip="d")

    # the coil box, ribbed with two brass hoops, and the two posts that carry the armature
    m.box((-0.13, TELE_H - 0.13, -0.10), (0.13, TELE_H - 0.055, 0.10), IRON_D, skip="d")
    for zz in (-0.055, 0.055):
        m.box((-0.135, TELE_H - 0.125, zz - 0.012), (0.135, TELE_H - 0.060, zz + 0.012), BRASS, skip="d")
    for sx in (-1, 1):
        m.box((sx * 0.135 - 0.014, TELE_H - 0.09, -0.014), (sx * 0.135 + 0.014, TELE_H - 0.012, 0.014),
              BRASS_D, skip="d")

    # the armature: a brass bar across the posts with the stop above it and the adjusting screw
    m.box((-0.16, TELE_H - 0.018, -0.020), (0.16, TELE_H + 0.004, 0.020), BRASS, skip="d")
    m.box((-0.16, TELE_H + 0.030, -0.016), (0.16, TELE_H + 0.048, 0.016), BRASS_D, skip="d")
    m.box((-0.012, TELE_H + 0.004, -0.012), (0.012, TELE_H + 0.032, 0.012), IRON_D, skip="d")

    # the tape reel at the east end: a brass spool on a fork, cream tape wound on it
    rx = hw * 0.60
    for zz in (-0.045, 0.045):
        m.box((rx - 0.012, TELE_H - 0.16, zz - 0.010), (rx + 0.012, TELE_H - 0.05, zz + 0.010), BRASS_D, skip="d")
    m.tube("z", (rx, TELE_H - 0.115), -0.036, 0.036, 0.052, CREAM_F, sides=10)
    m.tube("z", (rx, TELE_H - 0.115), -0.042, 0.042, 0.016, BRASS_D, sides=6)
    # the tape leaving the reel eastwards, a thin cream band just above the base's top
    m.box((rx + 0.04, TELE_H - 0.150, -0.022), (hw + 0.02, TELE_H - 0.128, 0.022), CREAM_F, skip="d")

    # the key's own two terminals on the west end, waiting for props/electrics' key beside it
    for zz in (-0.05, 0.05):
        m.box((-hw * 0.72 - 0.014, TELE_H - 0.075, zz - 0.014), (-hw * 0.72 + 0.014, TELE_H - 0.020, zz + 0.014),
              BRASS, skip="d")
    return m


# ==================================================================================================
# the pneumatic tube terminal
# ==================================================================================================
def _tube():
    """The pneumatic tube: the cast-iron bracket on the pier, the brass terminal body with its
    carrier door and index dial, the pipe stub going up. The length of pipe to the ceiling is placed
    by the room (it knows its own ceiling height), so this model stops a hand above the bracket.
    Anchor: the middle of the terminal body, on the pier's face."""
    m = M.Model(PREFIX + "tube", px=1.0, anchor=(0.0, 0.0, 0.0))
    r = TUBE_R

    # the bracket: a back plate on the pier, a boss, and the two arms that hold the pipe
    m.box((-0.075, -0.02, -0.014), (0.075, 0.62, 0.0), IRON_D, skip="d")
    m.box((-0.048, 0.20, 0.0), (0.048, 0.26, 0.10), IRON, skip="d")
    for y in (0.30, 0.56):
        m.box((-0.030, y - 0.014, 0.0), (0.030, y + 0.014, 0.085), IRON, skip="d")

    # the pipe stub and its brass collar where it leaves this piece
    m.tube("y", (0.0, 0.0), 0.10, 1.10, r, BRASS_F, sides=12)
    m.tube("y", (0.0, 0.0), 0.96, 1.02, r * 1.28, BRASS_D, sides=12)

    # the terminal body: a brass drum with a dark carrier door and its handle
    m.tube("z", (0.0, 0.62), 0.0, 0.30, 0.155, BRASS_F, sides=14,
           cap=P.mat("brass", kind="flat", base=3, bevel=1))
    m.tube("z", (0.0, 0.62), 0.30, 0.315, 0.105, IRON_D, sides=12)          # the door, set in
    m.box((-0.020, 0.60, 0.315), (0.020, 0.640, 0.345), BRASS_D, skip="d")   # its handle

    # the index dial above the door: a cream face with brass rim and a still pointer
    m.tube("z", (0.0, 0.62), 0.30, 0.312, 0.185, BRASS_D, sides=14)
    m.tube("z", (0.0, 0.62), 0.312, 0.318, 0.150, PORCELAIN, sides=14)
    m.box((-0.006, 0.62, 0.318), (0.006, 0.755, 0.324), IRON_D, skip="d")     # the pointer, up
    # the four station ticks on the dial
    for yy in (0.62 + 0.135, 0.62 - 0.135):
        m.box((-0.008, yy - 0.008, 0.318), (0.008, yy + 0.008, 0.322), BRASS_D, skip="d")
    for xx in (0.135, -0.135):
        m.box((xx - 0.008, 0.612, 0.318), (xx + 0.008, 0.628, 0.322), BRASS_D, skip="d")
    return m


# ==================================================================================================
# the registry
# ==================================================================================================
@functools.lru_cache(maxsize=None)
def _models():
    return {
        PREFIX + "drum": _drum(),
        PREFIX + "telegraph": _telegraph(),
        PREFIX + "tube": _tube(),
    }


def models():
    return dict(_models())


# ==================================================================================================
# placing
# ==================================================================================================
def _place(canvas, model, pos, origin, yaw, scale, brightness=None):
    """Place one display entity; pos is the piece's anchor in scene coordinates. Returns 1."""
    x, y, z = (pos[i] + origin[i] for i in range(3))
    canvas.add_entity(x, y, z, M.display(model, yaw=yaw, scale=scale, brightness=brightness))
    return 1


def _offer_lights(canvas, lights, why):
    """Hand light sources to A2 (sky/_lightkit.take); until that tool is in the tree the blocks are
    put down here, never over a block that is already there."""
    lights = [((int(x), int(y), int(z)), int(level)) for (x, y, z), level in lights]
    if not lights:
        return
    try:
        from ..sky import _lightkit
        take = getattr(_lightkit, "take", None)
    except ImportError:
        take = None
    if take is not None:
        take(canvas, lights, why)
        return
    for (x, y, z), level in lights:
        canvas.set(x, y, z, f"{B.LIGHT}[level={level}]", keep=True)


def _turn(yaw, v):
    """An offset in a piece's own frame as a world offset."""
    r = math.radians(yaw)
    c, s = math.cos(r), math.sin(r)
    return (v[0] * c - v[2] * s, v[1], v[0] * s + v[2] * c)


def drum(canvas, pos, facing="south", origin=(0, 0, 0), yaw=None):
    """Place the drum recorder with its anchor at `pos`. Returns (entities, the light cell)."""
    yaw = FACING[facing] if yaw is None else yaw
    n = _place(canvas, _models()[PREFIX + "drum"], pos, origin, yaw, 1.0)
    # the chart lamp: a warm point above the drum, offered to A2
    d = _turn(yaw, (0.0, DRUM_H + DRUM_R + LAMP_ABOVE, 0.0))
    cell = tuple(int(math.floor(pos[i] + origin[i] + d[i])) for i in range(3))
    return n, (cell, LAMP_LEVEL)


def telegraph(canvas, pos, facing="south", origin=(0, 0, 0), yaw=None):
    """Place the telegraph register with its anchor at `pos`. Returns the entity count."""
    yaw = FACING[facing] if yaw is None else yaw
    return _place(canvas, _models()[PREFIX + "telegraph"], pos, origin, yaw, 1.0)


def tube(canvas, pos, facing="west", origin=(0, 0, 0), yaw=None, top=None, foot=None):
    """Place the pneumatic tube terminal with its anchor at `pos`; the pipe is run up to `top` (the
    ceiling block) from `foot`, so the room can give its own ceiling. Returns the entity count."""
    yaw = FACING[facing] if yaw is None else yaw
    return _place(canvas, _models()[PREFIX + "tube"], pos, origin, yaw, 1.0)


def build(canvas, origin=(0, 0, 0), slots=None):
    """Place all three pieces at the time room's slots (interiors/timeroom.SLOTS when given, else the
    cells read from the room's geometry here). Returns the display-entity count."""
    slots = slots or DEFAULT_SLOTS
    built = _models()
    n, lights = 0, []

    for name, fn in (("drum", drum), ("telegraph", telegraph), ("tube", tube)):
        slot = slots.get(name)
        if not slot:
            continue
        pos = tuple(float(v) for v in slot["pos"])
        facing = slot.get("facing", "south")
        if name == "drum":
            got, light = fn(canvas, pos, facing, origin)
            n += got
            lights.append(light)
        else:
            n += fn(canvas, pos, facing, origin)

    _offer_lights(canvas, lights, NAME)
    return n


NAME = "machines/recorders"
