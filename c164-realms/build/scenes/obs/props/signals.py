"""props/signals -- the signalling of the rack railway (plan/round2.md, card props/signals; A0 g2
11-16 12:12: the train is how the map opens, and where its line comes into the station stands a
semaphore whose arm falls when the train comes).

One motif, the railway's own of the 1880s: a red blade on a slender iron post, an oil lamp behind
two coloured glasses, white enamel and black figures on what is read from the train.

    home signal    a post five blocks high beside the track where it comes on to the platform,
                   on the left of whoever drives up. Four pieces: the cast foot, the post (drawn
                   out between foot and head), the head -- the top of the post under a pointed cap
                   and the lamp on its bracket -- and the arm, which is the only piece that moves.

The arm. A blade a block and a half long, red with a white band towards the train, white with a
black band towards the station; it turns on a spindle through the post, and beyond the spindle it
carries the spectacle, a cast ring with one red glass. At rest the blade is level (stop) and the
red glass stands before the lamp: the light is red. For a train the blade falls DROP degrees (the
lower quadrant), the glass swings up and away, and the lamp shows its own light: until the 1890s
the light of "all right" was the bare white one, which here is the amber every lamp of the hill
has -- so the signal brings no new colour of light, and red stays what it is everywhere else, a
warning. The blade is on one side of the post only and nothing stands across it: seen against the
sky the signal is a bracket, never a cross (plan red line 8), and it has no ladder.

The lamp burns oil: a small iron case with a chimney, its lens behind the spectacle and a small
back light towards the station, by which the signalman sees that it burns. The glass is lit only
where the lamp stands behind it, so the arm has two models: MODEL_STOP with the lit glass, and
MODEL_CLEAR with the same glass dark.

Moving pieces, for motion. The arm's entity is tagged TAG_ARM. It is placed at "stop". pose(clear)
is what one `data merge` gives it for either position: the whole "transformation" (the anchor is
the spindle, not the middle of the model, so the translation changes with the turn) and the item
with the model of that position. The train does not come round in a cycle: every trip is started
by itself (motion/_train), and the two poses are hung on the trip. Until that is in the tree the
arm stands at stop.

For the other lines:

    from scenes.obs.props import signals
    n += signals.signal(canvas, (x, y, z), facing="east", origin=origin)   # the foot; facing: towards the train

build() stands the home signal at the cable station (site/cablecar), in the railed bay south of
the track at the platform's east edge, facing down the line. Mounting and materials are _kit's.
The test scene is build/scenes/obs_props_signals.
"""
import functools
import math

from artkit import models as M

from ..common import palette as P
from . import _kit as K
from .signs import _picture

PREFIX = "prop_signal_"
DRESS = True                    # build() stands the home signal in the master scene
VIEW = M.MID                    # seen from the platform and from the train on the last of its climb

IRON, IRON_D = K.IRON, K.IRON_D
POST = K.flat("iron", 3)        # the post: one tone, so drawing it out smears nothing
EDGE = K.flat("iron", 1)        # the edge of a sheet
SG = P.RAMPS["signal"]
CR = P.RAMPS["cream"]
IR = P.RAMPS["iron"]
RED_LIT = (K.flat("signal_glow", 2), K.flat("signal_glow", 3))   # the lit glass: its field, its middle

# Measures in pixels (16 to the block), from the spindle: x to the right of whoever looks at the
# signal's front, y up, z towards him.
POST_R = 1.25                   # the post is two and a half pixels thick
BLADE = 23                      # the painted blade, from its tip to the casting at its root
ROOT = 3                        # the casting at the root reaches this far either side of the spindle
BLADE_H = 4
BAND = (3, 5)                   # the band across the blade: its pixels, counted from the tip
SHEET = (2.5, 3.0)              # the blade is a sheet this far before the post's axis
LENS = (5.5, 0.5)               # the lamp's axis: right of the spindle and half a pixel over it
STUB = 4.0                      # the head carries the post this far down from the spindle
DROP = 45.0                     # degrees the arm falls from "stop" to "clear"
HEIGHT = 5.0                    # blocks from the foot to the spindle
TAG_ARM = "c164_signal_arm"
MODEL_STOP, MODEL_CLEAR = PREFIX + "arm", PREFIX + "arm_clear"
SWING = 16                      # ticks the arm takes from one position to the other

# The spectacle, as the train sees it: i the cast ring, R the red glass, three pixels square, on
# the lamp's axis while the blade is level.
_SPECTACLE = (".iii.",
              "iRRRi",
              "iRRRi",
              "iRRRi",
              ".iii.")
SPECTACLE_AT = (LENS[0] - 2.5, LENS[1] + 2.5)   # its upper left corner, seen from the front


# ---- the models -----------------------------------------------------------------------------------------
def _blade_face(front):
    """One face of the blade with the casting at its root, as whoever looks at that face sees it:
    the front red with a white band, the back white with a black one. From the front the tip is
    on the left, from the back on the right."""
    w = BLADE + 2 * ROOT
    grid = [[None] * w for _ in range(BLADE_H)]
    for c in range(w):
        tip = c if front else w - 1 - c                 # pixels from the tip
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
    return grid


def _spectacle_face(front):
    """One face of the spectacle: the ring and the glass, dark, with one lighter pixel."""
    tones = {"i": IR[2], "R": SG[0], ".": None}
    grid = [[tones[ch] for ch in row] for row in _SPECTACLE]
    grid[1][1] = SG[1]
    return grid if front else [row[::-1] for row in grid]


def _arm(name, lit):
    """The arm: the blade, the casting at its root with the boss of the spindle, and the
    spectacle beyond it; `lit` with the lamp's light in the glass (the blade level), or dark.
    Anchor: the spindle, on the post's axis; the blade lies along -x."""
    m = M.Model(name, px=1.0)
    z0, z1 = SHEET
    m.box((-(BLADE + ROOT), -BLADE_H / 2.0, z0), (ROOT, BLADE_H / 2.0, z1), EDGE,
          faces={"s": _picture("signal_blade_front", _blade_face(True)),
                 "n": _picture("signal_blade_back", _blade_face(False))})
    x, y = SPECTACLE_AT
    w, h = len(_SPECTACLE[0]), len(_SPECTACLE)
    m.box((x, y - h, z0 + 0.05), (x + w, y, z1 + 0.05), EDGE, skip="ewud",
          faces={"s": _picture("signal_spectacle_front", _spectacle_face(True)),
                 "n": _picture("signal_spectacle_back", _spectacle_face(False))})
    if lit:
        lx, ly = LENS
        field, middle = RED_LIT
        m.box((lx - 1.5, ly - 1.5, z1 + 0.05), (lx + 1.5, ly + 1.5, z1 + 0.2), field,
              skip="n", emit=15, shade=False)
        m.box((lx - 0.5, ly - 0.5, z1 + 0.2), (lx + 0.5, ly + 0.5, z1 + 0.3), middle,
              skip="n", emit=15, shade=False)
    m.tube("z", (0.0, 0.0), z0 - 0.5, z1 + 0.6, 1.5, IRON_D)                # the boss on the spindle
    return m


def _head():
    """The head: the top of the post under a pointed cap, the spindle through it, and on a
    bracket beside it the lamp -- an iron case with a chimney and a cowl, the lens towards the
    train behind the spectacle, a small back light towards the station. Anchor: the spindle."""
    m = M.Model(PREFIX + "head", px=1.0)
    m.tube("y", (0.0, 0.0), -STUB, 5.0, POST_R, POST)                       # the top of the post
    m.taper("y", (0.0, 0.0), 5.0, 7.5, 2.0, 0.5, IRON_D, steps=3)           # its cap
    m.tube("z", (0.0, 0.0), -2.0, SHEET[0] - 0.5, 0.75, IRON_D)             # the spindle
    lx, ly = LENS
    m.box((POST_R - 0.25, ly - 2.5, -1.5), (lx - 2.0, ly - 1.5, -0.5), IRON)        # the bracket
    m.box((lx - 2.0, ly - 2.5, -2.5), (lx + 2.0, ly + 2.5, 1.5), IRON_D, grain="y")  # the case
    K.glass_prism(m, "z", LENS, 1.5, 2.25, 1.25, K.GLOW_MID)                # the lens
    K.glass_prism(m, "z", LENS, -3.0, -2.5, 0.75, K.GLOW_DIM)               # the back light
    m.tube("y", (lx, -0.5), ly + 2.5, ly + 3.5, 1.0, IRON)                  # the chimney
    m.taper("y", (lx, -0.5), ly + 3.5, ly + 4.5, 1.75, 0.75, IRON_D, steps=2)        # its cowl
    return m


def _post():
    """The post between foot and head: runs along +z from the anchor, 48 long, in one flat tone,
    and is drawn out to the length wanted (models.between)."""
    m = M.Model(PREFIX + "post", px=1.0)
    m.tube("z", (0.0, 0.0), 0.0, 48.0, POST_R, POST)
    return m


def _foot():
    """The foot: a cast-iron shoe bolted to the paving, the post standing in its socket. Anchor:
    the middle of its foot; it is one block high."""
    m = M.Model(PREFIX + "foot", px=1.0)
    m.box((-3.5, 0.0, -3.5), (3.5, 1.5, 3.5), IRON, grain="x")
    for x in (-2.5, 2.5):
        for z in (-2.5, 2.5):
            K.rivet(m, (x, 1.5, z), out="y")
    m.taper("y", (0.0, 0.0), 1.5, 8.0, 2.75, 1.75, IRON_D, steps=3)
    m.tube("y", (0.0, 0.0), 8.0, 9.0, 2.25, IRON)
    m.tube("y", (0.0, 0.0), 9.0, 16.0, POST_R, POST)
    return m


# ---- models and placing ---------------------------------------------------------------------------------
SPEC = {
    "foot": dict(build=_foot, mount="floor"),
    "post": dict(build=_post, mount="floor"),
    "head": dict(build=_head, mount="floor"),
    "arm": dict(build=lambda: _arm(MODEL_STOP, True), mount="floor"),
    "arm_clear": dict(build=lambda: _arm(MODEL_CLEAR, False), mount="floor"),
}
SCALE = {PREFIX + kind: 1.0 for kind in SPEC}


@functools.lru_cache(maxsize=None)
def _models():
    return {PREFIX + kind: K.settle(spec["build"]()) for kind, spec in SPEC.items()}


def models():
    return dict(_models())


def pose(clear=False):
    """What the arm's entity is given for a position, as display NBT: dict(transformation, item).
    "stop" (the default, the pose it is placed in): the blade level, the glass lit. "clear": the
    blade DROP degrees down, the glass dark and away from the lamp."""
    model = _models()[MODEL_CLEAR if clear else MODEL_STOP]
    nbt = M.display(model, turns=(("z", DROP if clear else 0.0),))
    return {"transformation": nbt["transformation"], "item": nbt["item"]}


def signal(canvas, foot, facing="east", height=HEIGHT, origin=(0, 0, 0), view=VIEW):
    """Stand a semaphore signal at `foot` (the middle of its foot on the ground, scene
    coordinates), the spindle `height` blocks over it. `facing` is the way its front looks:
    towards the train it speaks to. The blade lies to the left of the post for that train and the
    lamp to the right, so the signal stands on the left of its track. It is placed at "stop".
    Returns the number of display entities (four: foot, post, head, arm)."""
    if height < 2.0:
        raise ValueError(f"a signal's spindle is at least 2 blocks over its foot, not {height:g}")
    built = _models()
    yaw = K.FACING[facing]
    x, y, z = (foot[i] + origin[i] for i in range(3))
    spindle = (foot[0], foot[1] + height, foot[2])
    n = K.put(canvas, built[PREFIX + "foot"], foot, yaw=yaw, origin=origin, view=view)
    lower, upper = y + 1.0, y + height - STUB / 16.0
    canvas.add_entity(x, lower, z, M.between(built[PREFIX + "post"], (x, lower, z), (x, upper, z), view=view))
    n += 1 + K.put(canvas, built[PREFIX + "head"], spindle, yaw=yaw, origin=origin, view=view)
    n += K.put(canvas, built[MODEL_STOP], spindle, yaw=yaw, origin=origin, view=view)
    canvas.entities[-1][3]["Tags"].append(TAG_ARM)
    return n


def _home():
    """Where the home signal stands: dict(foot, facing), read off site/cablecar -- the cell of the
    railed bay in the platform's east row, next to the canopy's south girder, three cells south
    of the track's axis; it faces east, down the line -- or None while that package is not in the
    tree."""
    try:
        from ..site import cablecar
    except ImportError:
        return None
    try:
        east, girder, feet = cablecar.X1, cablecar.GIRDER_Z, cablecar.FEET
    except AttributeError:
        return None
    return dict(foot=(east - 0.5, float(feet), girder + 1.5), facing="east")


def build(canvas, origin=(0, 0, 0)):
    """What signals place in the master scene: the home signal at the cable station. Nothing is
    stood where the platform's paving is not on the canvas or the cell over it is taken by
    anything but a light source."""
    if not DRESS:
        return 0
    seat = _home()
    if seat is None:
        return 0
    x, y, z = (int(math.floor(seat["foot"][i] + origin[i] + 1e-6)) for i in range(3))
    if not canvas.has(x, y - 1, z) or canvas.name(x, y, z) not in (None, "light"):
        return 0
    return signal(canvas, seat["foot"], facing=seat["facing"], origin=origin)
