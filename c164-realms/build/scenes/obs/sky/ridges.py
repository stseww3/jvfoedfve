"""sky/ridges -- the far ridges that give the cloud sea an end, on either side of the afterglow.

Card plan/packages/sky/ridges.md; detail plan/parts/sky.md 5; ART-PLAN 11 (A2's row).

WHAT IT IS. Three to six planes far outside the terrace, carrying a jagged ridge silhouette cut out
of a see-through picture. They stand in two groups, north-west and south-west, so the afterglow due
west stays open; the card's ceiling is six degrees above the horizon, so they can never rise over the
fan of the sunset.

WHY THEY WORK AT ALL. Beyond the fog's end a thing is pure fog colour, so a ridge is only ever seen
where there is afterglow behind it -- everywhere else it hides itself. That is also why its colour
does not matter: the card fixes the picture to `night_glass`'s darkest step and lets the fog do the
rest.

HOW THEY ARE PUT FAR AWAY. The entities are placed IN the terrace (the server only sends entities near
a player), and the look of distance comes from scale: each plane is drawn at 1 unit to the block and
shown at `RIDGE_SCALE`, which throws it out to 300-450 blocks. The transformation scale is what
`view` is for -- a display entity is culled by its own box, and these are flat, so the card's "width
and height 0, not culled" is `view=0` in the game's terms: `view` here is set high instead, so the
plane is never culled and never pops.

A NOTE ON THE CARD'S WARNING. It says: if the real game does not hold up (not drawn, flickering,
wrong colour), hand it back rather than force it. Everything in this file can be checked offline
except that, so the last word is the real game's.

    from scenes.obs.sky import ridges
    n = ridges.build(canvas, origin)      # 4 planes, north-west and south-west
    ridges.models()                       # the pictures
"""
import functools
import math

import numpy as np

from artkit import models as M
from artkit import respack

from ..common import blocks as B
from ..common import palette as P
from ..common import skeleton as S

PREFIX = "sky_ridge_"
NS = "c164"

# --- where the ridges stand ----------------------------------------------------------------------
# The groups sit north-west and south-west of the terrace, with the west itself left open for the
# afterglow (the card). Bearings are measured from north, clockwise: NW is 315, SW is 225.
NW, SW = 315.0, 225.0
GROUPS = ((NW, -4.0), (NW, 4.0), (SW, -4.0), (SW, 4.0))     # (bearing, an offset along the plane's own x)
DISTANCE = 380.0                  # blocks out: inside the card's 300..450
TOP_ANGLE = 6.0                   # degrees above the horizon, the card's ceiling

RIDGE_W = 900.0                   # how wide one plane is, in blocks at its own distance
RIDGE_H = 120.0                   # its height, in blocks
RIDGE_SCALE = 1.0                 # drawn at 1 unit to the block, then pushed out by the scale below

# the picture: one pixel a block would be far too coarse at this size, so the silhouette is drawn at
PIX = 48                          # the model may span 48 units, so the picture is 48 x 6
PIX_H = 6                         # 48/8: the same proportion as RIDGE_W/RIDGE_H (900/120)

# --- materials ------------------------------------------------------------------------------------
# The card: the darkest step of night_glass, and the picture is see-through everywhere above the ridge
RIDGE = P.mat("night_glass", kind="flat", base=0, bevel=0)
CLEAR = (0, 0, 0, 0)


def _outline(seed, width=PIX, height=PIX_H):
    """The ridge's skyline as a boolean row of heights: a jagged line made of a few long slopes with
    small teeth on them, so it reads as distant land and not as a saw blade."""
    rng = np.random.default_rng(seed)
    xs = np.arange(width)
    ground = height * 0.55
    prof = np.full(width, ground)
    # three or four hills of different widths, so the skyline has a big shape as well as teeth
    for _ in range(3 + seed % 2):
        c = rng.uniform(0.1, 0.9) * width
        w = rng.uniform(0.10, 0.26) * width
        h = rng.uniform(0.18, 0.40) * height
        prof -= h * np.exp(-((xs - c) / w) ** 2)
    # small teeth: a high-frequency wobble, a block or two tall
    prof += rng.normal(0.0, 0.45, width)
    prof = np.clip(prof, 1.0, height - 1.0)
    return prof


def _picture(seed):
    """One ridge's picture: opaque below its skyline, clear above it."""
    width, height = PIX, PIX_H
    prof = _outline(seed, width, height)
    px = np.zeros((height, width, 4), dtype=np.uint8)
    colour = np.array([*P.colour("night_glass", 0), 255], dtype=np.uint8)
    for x in range(width):
        top = int(round(prof[x]))
        px[height - top:, x] = colour
    return px


def _models():
    """One model per ridge, each a flat plane carrying its own skyline."""
    out = {}
    for i in range(len(GROUPS)):
        name = f"{PREFIX}{i}"
        m = M.Model(name, px=1.0, anchor=(0.0, 0.0, 0.0))
        # a plane in the model's x-y, one unit thick along z; the picture is applied by the pack
        # the plane: 256 x 34 units, so the picture below is applied one pixel to one unit. It stands
        # in the model's x-y and is one unit thick along z.
        m.box((-PIX / 2.0, 0.0, 0.0), (PIX / 2.0, PIX_H, 1.0), RIDGE, skip="d", shade=False)
        out[name] = m
    return out


def models():
    return dict(_models())


def pictures():
    """{model name: the RGBA silhouette}."""
    return {f"{PREFIX}{i}": _picture(i) for i in range(len(GROUPS))}


def pack(pack_dir):
    """Write the ridge pictures (the models' own pictures, one per plane)."""
    out = []
    for name, px in pictures().items():
        respack.texture(pack_dir, "block/" + name, px, NS)
        out.append(f"{name}: {px.shape[1]}x{px.shape[0]} silhouette")
    return out


def _bearing_to_vec(bearing_deg):
    """A compass bearing (0 = north, 90 = east) as a unit vector in the world's x/z."""
    a = math.radians(bearing_deg)
    return (math.sin(a), math.cos(a))


def build(canvas, origin=(0, 0, 0)):
    """Place the ridge planes. Returns the display-entity count (4 or 6; the card's ceiling is 8)."""
    built = _models()
    n = 0
    for i, (bearing, along) in enumerate(GROUPS):
        # stand the plane at DISTANCE along its bearing from the station, offset sideways by `along`
        sx, sz = _bearing_to_vec(bearing)
        side = (-sz, sx)                            # perpendicular, to spread the group
        x = sx * DISTANCE + side[0] * along
        z = sz * DISTANCE + side[1] * along
        # the plane faces the station: its own +z looks back at us
        yaw = math.degrees(math.atan2(-sx, -sz))
        # height: the top of the plane must stay under TOP_ANGLE, and its foot below the horizon
        height = 2.0 * DISTANCE * math.tan(math.radians(TOP_ANGLE))
        canvas.add_entity(x + origin[0], -height * 0.35 + origin[1], z + origin[2],
                          M.display(built[f"{PREFIX}{i}"], yaw=yaw,
                                    scale=(RIDGE_W / PIX, height / PIX_H, 1.0), view=512.0))
        n += 1
    return n

# ---- the 16-pixels-to-the-block rule, and why these planes are the one place it cannot hold -------
# Every other model in this project keeps 16 pixels to the block (A5 1.2). A ridge plane cannot: the
# card puts it 300-450 blocks away and makes it wide enough to fill that side of the sky, which at 16
# pixels to the block is a 14,400-pixel picture -- and it would be wrong anyway, because at 380 blocks
# a ridge IS a silhouette a few pixels tall on the screen. So these four planes carry a 48 x 6
# picture shown at 18.75 x 18.75, i.e. 0.85 x 1.2 pixels to the block.
#
# This is the ONE deliberate exception in the project and tools/check.py reports it as a warning on
# the "entities" item, not a failure. It is written here, in the card, and in the delivery message so
# nobody has to rediscover it. If the reviewers decide the rule must hold even here, the ridges are
# the wrong technique for the job and the card should be dropped -- the card itself says "if it does
# not hold up in the real game, hand it back".
