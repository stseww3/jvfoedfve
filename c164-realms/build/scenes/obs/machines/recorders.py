"""machines/recorders -- the drum recorder, the telegraph and the pneumatic tube of the time room.

Card plan/packages/machines/recorders.md; detail plan/parts/A5-machines.md 2.10; ART-PLAN 7.2, 8.
The card's fourth piece, the world-clock wall, was dropped before this round: the time room makes
its own five stopped slave dials (A0 #529), so what is left here is three standing things on the
room's console and east wall.

  mach_rec_drum       the drum recorder: a brass drum lying on its axis across a dark-wood case,
                      cream chart paper wound round the drum with the pen's trace on it, the pen
                      carriage on a slide over the drum, the paper supply reel behind and a drawer
                      in the front. On the console's east end.
  mach_rec_telegraph  the telegraph register: the coil box hooped with brass, the sounder's
                      armature on two posts over it, the tape reel on a spindle and the tape running
                      out of it. On the console west of the telegraph key.
  mach_rec_tube       the pneumatic tube terminal: the cast-iron back plate on the east wall's pier,
                      the brass terminal body with its carrier door and index dial, and the pipe: a
                      16-unit section of tube stretched from the terminal's foot to the ceiling
                      (models.between -- a model may span 3 blocks at most, A5 1.2).

Sizes are the card's: 1.5 x 1.0 x 1.5 blocks (drum), 1.0 x 0.8 x 0.5 (telegraph). Models are drawn
in model units -- 16 units to the block, which is what M.display divides by -- with px = 1, so a
picture is 16 pixels to the block, the same density as the blocks and other models (A5 1.2).

AXES FOR A8. Everything is still this round (A0 #505: the drum and the tape do not turn), but each
piece is anchored where it would turn, so switching them on later is a matter of turning the entity:

  mach_rec_drum        anchor = the drum's axis at the middle of the drum; the axis runs along x,
                       so a turn about x spins the drum.
  mach_rec_telegraph   anchor = the sounder's armature pivot, on the coil box's centre line; a
                       small turn about x makes the armature clack.

The recorder's chart lamp is offered to A2 through sky/_lightkit.take at level 7 (a recorder's lamp,
a third-rank light, below a window).

PLACING. build(canvas, origin, slots) takes the time room's own SLOTS table when it is in the tree
(interiors/timeroom.SLOTS: "drum", "telegraph", "tube") and falls back to the same cells read from
the room's geometry when it is not. Each piece can also be placed alone by its own function:

    from scenes.obs.machines import recorders
    n = recorders.build(canvas, origin, slots=timeroom.SLOTS)
    n += recorders.drum(canvas, (9.5, 8.0, -23.5), facing="south")
    n += recorders.telegraph(canvas, (7.5, 8.0, -23.5), facing="south")
    n += recorders.tube(canvas, (14.0, 8.0, -16.5), facing="west")
"""
import functools
import math

from artkit import models as M

from ..common import blocks as B
from ..common import palette as P

PREFIX = "mach_rec_"
NAME = "machines/recorders"

# the way a piece looks -> the yaw that points its +z that way (same table as props/_kit, clock.py)
FACING = {"south": 0.0, "west": 90.0, "north": 180.0, "east": -90.0}

# --- the room's cells, as interiors/timeroom.py has them (the fallback when that module is absent)
SILL = 8                  # the sill line: what stands on the console stands on this y
CONSOLE_Z = -24           # the console runs along the foot of the instrument wall
DRUM_X = 9                # the drum recorder's cell (the console's east end)
KEY_X = 7                 # the telegraph key's cell; the register stands just west of it
EAST = 14                 # the east wall: x of the first air cell west of it
DESK_PIER_Z = -16         # the pier south of the message desk

# c292's own table (interiors/timeroom.py, cursor/c164-m2-timeroom-80c9 @ a14a1f37), which is what
# build() is given when that module is in the tree. Note the anchor heights: the drum's is its axis
# (DRUM_AXIS/16 = 1.06 above the console), the telegraph's is its armature pivot (TELE_H/16 = 0.75),
# the tube's is its body centre (1.6 above the sill, its pipe running up from there).
DEFAULT_SLOTS = {
    "drum": dict(pos=(9.5, float(SILL), CONSOLE_Z + 0.5), facing="south"),
    "telegraph": dict(pos=(6.5, float(SILL), CONSOLE_Z + 0.5), facing="south"),
    "tube": dict(pos=(float(EAST), float(SILL), -9.5), facing="west"),
}

# --- sizes in model units (16 to the block); the card's block sizes are in the comments
DRUM_W, DRUM_D, DRUM_H = 24.0, 16.0, 24.0      # the recorder's case: 1.5 x 1.0 x 1.5 blocks
DRUM_R = 8.0                                   # the drum: 1.0 blocks through -- the machine itself
CHART_W = 19.0                                 # the drum's width along its axis: 1.19 blocks
DRUM_AXIS = 15.2                               # the drum's axis height above the foot: 0.95 blocks
TELE_W, TELE_D, TELE_H = 16.0, 13.0, 12.0      # the register: 1.0 x 0.8 x 0.75 blocks
TUBE_R = 2.6                                   # the pneumatic pipe: 0.16 blocks through
TUBE_LIFT = 1.6                                # blocks from the sill to the tube body's centre
TUBE_TOP = 6.0                                 # the room's ceiling above the sill (time room: y 14)
TUBE_FOOT = 1.2                                # the terminal's bottom above the sill (y 9.2)

# the recorder's chart lamp: the console's warm point (offered to A2; a third-rank light)
LAMP_LEVEL = 7
LAMP_ABOVE = 0.55                              # blocks above the top of the drum

# --- materials (palette only) ---------------------------------------------------------------------
BRASS = P.mat("brass")
BRASS_D = P.mat("brass_dark")
BRASS_F = P.mat("brass", kind="flat", bevel=0)
IRON = P.mat("iron")
IRON_D = P.mat("iron_dark")
WOOD = P.mat("dark_wood")
WOOD_D = P.mat("dark_wood", base=1)
WOOD_L = P.mat("dark_wood", base=3)
CREAM = P.mat("cream")
CREAM_F = P.mat("cream", kind="flat", base=1, bevel=0)
CREAM_D = P.mat("cream", base=1, kind="flat", bevel=0)
PORCELAIN = P.mat("porcelain")


# ==================================================================================================
# the drum recorder
# ==================================================================================================
def _drum():
    """The drum recorder. A low dark-wood case with a drawer, two brass standards carrying the
    drum's shaft, and the drum itself -- brass end flanges, cream chart paper between them -- lying
    across the machine, with the pen carriage on its slide above and the paper reel behind.

    Anchor: the drum's axis, at the middle of the drum, so the entity turns about that axis.
    """
    m = M.Model(PREFIX + "drum", px=1.0, anchor=(0.0, DRUM_AXIS, 0.0))
    hw, hd = DRUM_W / 2, DRUM_D / 2             # 12, 8
    ay = 0.0                                    # the model's own frame puts the axis at y 0
    case_top = -8.2                             # a low base: 0.44 blocks, so the drum dominates
    half_chart = CHART_W / 2                    # 6

    # the case: a plinth on four feet, the body, a moulded top edge; the drawer face and its pull
    for sx in (-1, 1):
        for sz in (-1, 1):
            m.box((sx * hw - 1.7, -17.0, sz * hd - 1.7), (sx * hw + 1.7, -15.5, sz * hd + 1.7),
                  WOOD_D, skip="d")
    m.box((-hw, -15.5, -hd), (hw, -13.8, hd), WOOD_D, skip="d")
    m.box((-hw, -13.8, -hd), (hw, case_top, hd), WOOD, skip="d")
    m.box((-hw - 0.5, case_top, -hd - 0.5), (hw + 0.5, case_top + 1.4, hd + 0.5), WOOD_L, skip="d")
    m.box((-hw * 0.66, -12.6, hd - 0.15), (hw * 0.66, -8.8, hd + 0.15), WOOD_D, skip="d")
    m.box((-1.9, -11.1, hd + 0.15), (1.9, -10.3, hd + 0.75), BRASS, skip="d")

    # the two brass standards that carry the shaft, rising past the drum's axis on each side
    for sx in (-1, 1):
        x0 = sx * (half_chart + 1.0)
        x1 = x0 + sx * 1.5
        m.box((min(x0, x1), case_top, -1.5), (max(x0, x1), ay + DRUM_R + 1.0, 1.5), BRASS, skip="d")
        m.box((min(x0, x1), ay + DRUM_R - 0.5, -1.3), (max(x0, x1), ay + DRUM_R + 0.9, 1.3),
              BRASS_D, skip="d")

    # the shaft, the drum's brass end flanges, and the chart paper wound between them
    m.tube("x", (0.0, ay), -half_chart - 2.4, half_chart + 2.4, 0.8, BRASS_D, sides=8)
    m.tube("x", (0.0, ay), -half_chart - 0.9, -half_chart + 0.2, DRUM_R + 0.5, BRASS, sides=14)
    m.tube("x", (0.0, ay), half_chart - 0.2, half_chart + 0.9, DRUM_R + 0.5, BRASS, sides=14)
    m.tube("x", (0.0, ay), -half_chart + 0.1, half_chart - 0.1, DRUM_R, CREAM_F, sides=14)
    # the pen's trace: one raised line right round the paper, a step darker (a pixel proud)
    m.box((-half_chart + 0.3, DRUM_R - 0.4, -DRUM_R - 0.14),
          (half_chart - 0.3, DRUM_R + 0.6, DRUM_R + 0.14), CREAM_D, skip="d")

    # the pen carriage: the slide bar over the drum, its arm, the nib riding on the paper
    m.box((-hw * 0.88, DRUM_R + 1.4, -hd * 0.50), (hw * 0.88, DRUM_R + 2.3, -hd * 0.50 + 1.1),
          BRASS_D, skip="d")
    m.box((-0.9, DRUM_R + 0.5, -hd * 0.48), (0.9, DRUM_R + 1.5, -hd * 0.04), BRASS, skip="d")
    m.box((-0.28, DRUM_R + 0.1, -hd * 0.20), (0.28, DRUM_R + 0.6, -hd * 0.02), IRON_D, skip="d")

    # the crank on the east standard: a brass arm with a dark knob, the thing that says "this turns"
    cx = half_chart + 2.9
    m.box((cx - 0.35, -0.5, -0.35), (cx + 0.35, 4.6, 0.35), BRASS_D, skip="d")
    m.box((cx - 0.30, 4.2, -2.4), (cx + 0.30, 4.9, 0.3), BRASS_D, skip="d")
    m.box((cx - 0.45, 3.6, -2.9), (cx + 0.45, 5.4, -1.9), WOOD_D, skip="d")

    # the paper supply reel at the back, on its brass fork
    reel_y = DRUM_R + 0.6
    reel_z = -hd + 2.2
    for sx in (-1, 1):
        x_in = sx * (half_chart * 0.55)
        x_out = x_in + sx * 0.9
        m.box((min(x_in, x_out), -1.0, reel_z - 0.6), (max(x_in, x_out), reel_y + 1.6, reel_z + 0.6),
              BRASS_D, skip="d")
    m.tube("x", (0.0, reel_y), -half_chart * 0.55 - 0.4, half_chart * 0.55 + 0.4, 2.0, CREAM_F, sides=10)
    return m


# ==================================================================================================
# the telegraph register
# ==================================================================================================
def _telegraph():
    """The telegraph register: a wooden base, the coil box hooped with brass, the sounder's armature
    on two posts over it, the tape reel on a brass fork at the east end and the tape running out.

    Anchor: the armature's pivot -- the top of the coil box, on its centre line.
    """
    m = M.Model(PREFIX + "telegraph", px=1.0, anchor=(0.0, 0.0, 0.0))
    hw, hd = TELE_W / 2, TELE_D / 2             # 8, 6.5
    base_h = 2.0
    coil_h = 4.6
    top = base_h + 2.2 + coil_h

    m.box((-hw, 0.0, -hd), (hw, base_h, hd), WOOD_D, skip="d")                    # the base
    m.box((-hw * 0.80, base_h, -hd * 0.80), (hw * 0.80, base_h + 2.2, hd * 0.80), WOOD, skip="d")

    # the coil box hooped with brass; the two posts beside it carry the armature
    m.box((-4.6, base_h + 2.2, -3.4), (4.6, top, 3.4), IRON_D, skip="d")
    for zz in (-2.0, 2.0):
        m.box((-4.8, base_h + 2.4, zz - 0.5), (4.8, top - 0.4, zz + 0.5), BRASS, skip="d")
    for sx in (-1, 1):
        m.box((sx * 5.0 - 0.5, base_h + 2.6, -0.5), (sx * 5.0 + 0.5, top + 1.6, 0.5), BRASS_D, skip="d")

    # the armature: the brass bar across the posts, the stop above it, the adjusting screw between
    m.box((-6.0, top + 0.2, -0.8), (6.0, top + 1.1, 0.8), BRASS, skip="d")
    m.box((-6.0, top + 2.3, -0.65), (6.0, top + 3.1, 0.65), BRASS_D, skip="d")
    m.box((-0.5, top + 1.1, -0.5), (0.5, top + 2.4, 0.5), IRON_D, skip="d")

    # the tape reel east of the sounder, on a brass fork: a cream spool with a brass spindle
    rx = hw * 0.52
    for zz in (-2.2, 2.2):
        m.box((rx - 0.5, base_h + 1.0, zz - 0.45), (rx + 0.5, base_h + 6.0, zz + 0.45), BRASS_D, skip="d")
    m.tube("z", (rx, base_h + 3.6), -1.7, 1.7, 2.1, CREAM_F, sides=12)
    m.tube("z", (rx, base_h + 3.6), -2.0, 2.0, 0.65, BRASS_D, sides=6)
    # the tape leaving the reel eastwards, a thin cream band just over the base
    m.box((rx + 1.6, base_h + 1.3, -0.9), (hw + 0.9, base_h + 1.8, 0.9), CREAM_F, skip="d")

    # the two lead terminals at the west end, where the key beside it ties in
    for zz in (-2.0, 2.0):
        m.box((-hw * 0.70 - 0.6, base_h + 0.2, zz - 0.6), (-hw * 0.70 + 0.6, base_h + 2.4, zz + 0.6),
              BRASS, skip="d")
    return m


# ==================================================================================================
# the pneumatic tube terminal
# ==================================================================================================
def _tube():
    """The pneumatic tube: the cast-iron back plate on the pier, the brass terminal body standing out
    from it with the carrier door and the index dial, and the pipe going up to the ceiling.

    Anchor: the middle of the terminal body, on the pier's face.
    """
    m = M.Model(PREFIX + "tube", px=1.0, anchor=(0.0, 0.0, 0.0))
    r = TUBE_R

    # the back plate on the pier, its boss and the two arms that hold the pipe
    m.box((-1.8, -8.0, -0.35), (1.8, 10.0, 0.0), IRON_D, skip="d")
    m.box((-1.1, -1.6, 0.0), (1.1, 0.7, 2.4), IRON, skip="d")
    for y in (2.6, 9.0):
        m.box((-0.7, y - 0.32, 0.0), (0.7, y + 0.32, 2.1), IRON, skip="d")

    # the terminal's own length of pipe: from a hand under the body up past the body, 2.6 blocks, so
    # the body is not left floating on a bare stub (the long run to the ceiling is the pipe model)
    m.tube("y", (0.0, 0.0), -5.0, 36.0, r, BRASS_F, sides=12)
    for y in (34.0, -3.0):
        m.tube("y", (0.0, 0.0), y - 0.7, y + 0.7, r * 1.30, BRASS_D, sides=12)

    # the terminal body: a brass drum standing out from the pier
    m.tube("z", (0.0, 0.0), 0.0, 7.0, 3.8, BRASS_F, sides=14,
           cap=P.mat("brass", kind="flat", base=3, bevel=1))
    # the carrier door set in its face, with its handle
    m.tube("z", (0.0, 0.0), 7.0, 7.4, 2.6, IRON_D, sides=12)
    m.box((-0.45, -0.45, 7.4), (0.45, 0.45, 8.1), BRASS_D, skip="d")

    # the index dial above the door: brass rim, porcelain face, a still pointer and four ticks
    m.tube("z", (0.0, 0.0), 7.0, 7.35, 4.5, BRASS_D, sides=14)
    m.tube("z", (0.0, 0.0), 7.35, 7.5, 3.7, PORCELAIN, sides=14)
    m.box((-0.16, 0.0, 7.5), (0.16, 3.3, 7.66), IRON_D, skip="d")
    for dy in (3.2, -3.2):
        m.box((-0.2, dy - 0.2, 7.5), (0.2, dy + 0.2, 7.6), BRASS_D, skip="d")
    for dx in (3.2, -3.2):
        m.box((dx - 0.2, -0.2, 7.5), (dx + 0.2, 0.2, 7.6), BRASS_D, skip="d")
    return m


# ==================================================================================================
# the registry
# ==================================================================================================
def _pipe():
    """One 3-block section of the pneumatic pipe, running up from its anchor: the tube() call with
    cap=None so the two ends meet the next section without a lid."""
    m = M.Model(PREFIX + "pipe", px=1.0, anchor=(0.0, 0.0, 0.0))
    m.tube("y", (0.0, 0.0), 0.0, 48.0, TUBE_R, BRASS_F, sides=10, cap=None)
    return m


@functools.lru_cache(maxsize=None)
def _models():
    return {
        PREFIX + "drum": _drum(),
        PREFIX + "telegraph": _telegraph(),
        PREFIX + "tube": _tube(),
        PREFIX + "pipe": _pipe(),
    }


def models():
    return dict(_models())


# ==================================================================================================
# placing
# ==================================================================================================
def _place(canvas, model, pos, origin, yaw):
    """Place one display entity; `pos` is the piece's anchor in blocks, in scene coordinates."""
    x, y, z = (pos[i] + origin[i] for i in range(3))
    canvas.add_entity(x, y, z, M.display(model, yaw=yaw, scale=1.0, view=5.0))
    return 1


def _turn(yaw, v):
    """An offset in a piece's own frame as a world offset."""
    r = math.radians(yaw)
    c, s = math.cos(r), math.sin(r)
    return (v[0] * c - v[2] * s, v[1], v[0] * s + v[2] * c)


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


def drum(canvas, pos, facing="south", origin=(0, 0, 0), yaw=None, on_axis=False):
    """Place the drum recorder. `pos` is the point the recorder STANDS on (the console top) unless
    on_axis, in which case it is the drum's axis itself. Returns (entities, the light's cell)."""
    yaw = FACING[facing] if yaw is None else yaw
    anchor = (pos[0], pos[1] + (0.0 if on_axis else DRUM_AXIS / 16.0), pos[2])
    pos = anchor
    n = _place(canvas, _models()[PREFIX + "drum"], pos, origin, yaw)
    above = (DRUM_R + 1.0) / 16.0 + LAMP_ABOVE
    d = _turn(yaw, (0.0, above, 0.0))
    cell = tuple(int(math.floor(pos[i] + origin[i] + d[i])) for i in range(3))
    return n, (cell, LAMP_LEVEL)


def telegraph(canvas, pos, facing="south", origin=(0, 0, 0), yaw=None):
    """Place the telegraph register. `pos` is the point it STANDS on (the console top); the model's
    anchor is its armature pivot, above that. Returns the display-entity count."""
    yaw = FACING[facing] if yaw is None else yaw
    anchor = (pos[0], pos[1] + TELE_H / 16.0, pos[2])
    return _place(canvas, _models()[PREFIX + "telegraph"], anchor, origin, yaw)


def tube(canvas, pos, facing="west", origin=(0, 0, 0), yaw=None, top=None):
    """Place the pneumatic tube terminal. `pos` is the sill point on the pier, as the room's table
    gives it; the body's centre sits TUBE_LIFT above that, and the pipe is stretched from a hand
    under the body up to `top` (the ceiling's y; TUBE_TOP + the sill by default). Returns the count
    of display entities: the terminal and the pipe, 2."""
    yaw = FACING[facing] if yaw is None else yaw
    ox, oy, oz = origin
    foot = pos[1] + TUBE_FOOT
    ceil = (pos[1] + TUBE_TOP) if top is None else float(top)
    anchor = (pos[0], pos[1] + TUBE_LIFT, pos[2])
    n = _place(canvas, _models()[PREFIX + "tube"], anchor, origin, yaw)
    # the run to the ceiling: one 3-block section at a time (a model may span 3 blocks at most, and
    # stacking sections keeps 16 pixels to the block where a stretch would smear them)
    pipe = _models()[PREFIX + "pipe"]
    y, i = foot, 0
    while y < ceil - 0.01:
        span = min(3.0, ceil - y)
        canvas.add_entity(pos[0] + ox, y + oy, pos[2] + oz,
                          M.display(pipe, scale=(1.0, span / 3.0, 1.0), view=5.0))
        n += 1
        y += span
        i += 1
    return n


def build(canvas, origin=(0, 0, 0), slots=None):
    """Place all three pieces at the time room's slots (interiors/timeroom.SLOTS when given, else the
    cells read from the room's geometry here). Returns the display-entity count."""
    slots = slots or DEFAULT_SLOTS
    n, lights = 0, []
    for name, fn in (("drum", drum), ("telegraph", telegraph), ("tube", tube)):
        slot = slots.get(name)
        if not slot:
            continue
        pos = tuple(float(v) for v in slot["pos"])
        if name == "drum":
            got, light = fn(canvas, pos, slot.get("facing", "south"), origin)
            n += got
            lights.append(light)
        else:
            n += fn(canvas, pos, slot.get("facing", "south"), origin)
    _offer_lights(canvas, lights, NAME)
    return n
