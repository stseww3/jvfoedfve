"""props/signs -- the observatory's signs and its station emblem (plan ART-PLAN 2, 5.1, 7.3;
part A6-props 2.8; card plan/packages/props/electrics-signs.md).

The station emblem (plan 2) is the name of this observatory: a ring, a meridian line straight down
it, and a star on its upper-right shoulder. It has to read as one and the same mark wherever it is
seen -- over the entrance, in the forecourt paving, on the iron gates, on the cars. This module is
the one place that draws it as a model, and it holds the standard figure the other lines align to:
`emblem_cells(n)` gives the figure on an n-pixel grid (16 for one block, 48 for three) so a texture
or a floor of blocks can be laid to the same drawing; the models raise that same figure in brass.

The standard (A0 #231, c219 #228):
  * ring      centred on the tile, ten-sixteenths across, one line thick.
  * meridian  one line wide, straight down the ring's whole height.
  * star      a small star clear of the ring on its upper-right shoulder; on the 16 px grid its
              centre is the pixel (13, 2), a plus of five pixels, a clear cell off the ring.

Signs, all on the common palette, 16 texels to the block (px = scale):
    emblem        the brass emblem plaque (the 1x1 sign): the standard figure raised in brass.
    big_emblem    the one great emblem over the entrance (3x3, option A, A0 #186): a cast brass
                  emblem in low relief, old brass, with a light offered below (lit from the door
                  lamps at night).
    clock         the entrance clock (3x3, option B, A0 #186): a white enamel dial, black hands and
                  a brass bezel, of one family with the clock tower's face.
    nameplate     an enamel nameplate, cream figures on blue, in a brass frame; by a door.
    number        a small enamel number plate.
    flag          a cloth flag carrying the emblem (the flutter is A8's).
    meridian_mark the brass end-plate where the forecourt meridian line meets a stone.
    fingerpost    a timber fingerpost with painted fingers.

Mounting, materials, lights and rivets are _kit's; the sign helpers live here. The look is judged on
texture and on style, so the test scene is build/scenes/obs_props_elecsign (shared with electrics).
"""
import functools
import math

from artkit import models as M
from artkit.pixelart import Sprite

from ..common import palette as P
from ..common import skeleton as S
from . import _kit as K

PREFIX = "prop_sign_"
DRESS = False                   # build() dresses the master scene only when on (A0 #211): off until
                                # the family has passed review on the real wall

IRON, IRON_D = K.IRON, K.IRON_D
BRASS, BRASS_D = K.BRASS, K.BRASS_D
ENAMEL = K.ENAMEL
CREAM = K.CREAM
CLOTH = P.mat("cream_cloth")
ENAMEL_CLOTH = P.mat("enamel_cloth")
WOOD = P.mat("dark_wood")
SLATE = P.mat("slate")
GLASS_DIM, GLASS_MID = K.GLOW_DIM, K.GLOW_MID

# hex of the enamel and cream ramps, for the hand-drawn sign faces (sprites take hex, not Mat)
EN = P.RAMPS["enamel"]
CR = P.RAMPS["cream"]
BR = P.RAMPS["brass"]
IR = P.RAMPS["iron"]


# ---- the station emblem: one figure, every size ---------------------------------------------------
def emblem_cells(n=16):
    """The station emblem on an n x n grid (n = 16 for a one-block tile, 48 for a three-block one),
    pixels (x, y) with y running down as a texture does. Returns dict(ring, meridian, star): the
    same proportions at every n, so the mark reads the same at any size. This is the standard the
    materials emblem block (c204) and the court roundel (c221) align to.

    At n = 16 it is exactly A0's ruling (#231): the ring 4.2..4.9 from the centre, the meridian the
    column x = 7 from y 3 to 12, the star the plus centred on (13, 2)."""
    c = (n - 1) / 2.0
    k = n / 16.0
    r_in, r_out = 4.2 * k, 4.9 * k
    ring = [(x, y) for y in range(n) for x in range(n)
            if r_in <= math.hypot(x - c, y - c) <= r_out]
    mx = int(math.floor(c))                     # the column just left of centre (x = 7 at n = 16)
    mw = max(1, int(round(k)))                  # the meridian's width in pixels
    y0, y1 = int(round(3 * k)), int(round(13 * k)) - 1
    meridian = [(x, y) for x in range(mx, mx + mw) for y in range(y0, y1 + 1)]
    # the star, upper right, a clear cell off the ring. Its centre scales from the tile centre so the
    # NE offset (5.5, -5.5) is kept; at n = 16 that is (13, 2).
    sx, sy = int(round(c + 5.5 * k)), int(round(c - 5.5 * k))
    arm = max(1, int(round(k)))
    star = ([(sx + dx, sy) for dx in range(-arm, arm + 1)]
            + [(sx, sy + dy) for dy in range(-arm, arm + 1)])
    star = [(x, y) for (x, y) in star if 0 <= x < n and 0 <= y < n]
    return {"ring": ring, "meridian": meridian, "star": star}


def emblem_sprite(name, n, fg, star_fg=None, back=None):
    """The emblem as a Sprite: `fg` the ring and meridian, `star_fg` (or fg) the star, over `back`
    (a Mat) or transparent. For the flag, the paper letterheads, any painted face that wants it."""
    fig = emblem_cells(n)
    grid = [[" "] * n for _ in range(n)]
    for x, y in fig["ring"] + fig["meridian"]:
        grid[y][x] = "o"
    for x, y in fig["star"]:
        grid[y][x] = "*"
    rows = ["".join(r) for r in grid]
    cols = {"o": fg, "*": star_fg or fg}
    return Sprite(name, rows, cols, back=back)


def _emblem_relief(m, cx, cy, z0, k, ring_mat=BRASS, star_mat=None, proud=1.0):
    """Raise the standard figure at centre (cx, cy) in the model's x-y plane, standing `proud` of z0,
    at a size factor k (16 units across at k = 1). Model y is up, so the star lands upper-right."""
    star_mat = star_mat or ring_mat
    z1 = z0 + proud
    r_mid = 4.55 * k
    m.ring("z", (cx, cy, (z0 + z1) / 2.0), r_mid, 0.9 * k, proud, ring_mat, sides=24)
    m.box((cx - 0.5 * k, cy - 4.9 * k, z0), (cx + 0.5 * k, cy + 4.9 * k, z1), ring_mat, grain="y")
    sx, sy = cx + 5.0 * k, cy + 5.0 * k          # NE shoulder, a clear gap off the ring (model y up)
    a = max(0.5, 0.9 * k)
    for dx, dy in ((0, 0), (-1.6 * k, 0), (1.6 * k, 0), (0, -1.6 * k), (0, 1.6 * k)):
        m.box((sx + dx - a, sy + dy - a, z0), (sx + dx + a, sy + dy + a, z1), star_mat)
    return m


# ---- the models ----------------------------------------------------------------------------------
def _emblem():
    """The 1x1 brass emblem plaque: a square brass back and the standard figure raised on it.
    Anchor: on the wall, the plaque's foot centre."""
    m = M.Model(PREFIX + "emblem", px=1.0)
    m.box((1.0, 1.0, 0.0), (15.0, 15.0, 1.0), BRASS_D, grain="y")        # the back plate
    for sx in (1.5, 14.5):
        m.box((sx - 0.5, 1.0, 0.0), (sx + 0.5, 15.0, 1.2), BRASS, grain="y")   # a thin bead frame
    for sy in (1.5, 14.5):
        m.box((1.0, sy - 0.5, 0.0), (15.0, sy + 0.5, 1.2), BRASS, grain="x")
    _emblem_relief(m, 8.0, 8.0, 1.0, 1.0, ring_mat=BRASS, star_mat=BRASS)
    return m


def _big_emblem():
    """Option A for the great emblem over the entrance (A0 #186): a cast brass emblem, 3x3, in low
    relief -- an outer bead rim, the standard ring, meridian and star inside it, old brass. Drawn in
    one 16-unit tile and shown at scale 3, so it is 48 texels across (px = scale keeps 16/block).
    Anchor: on the wall, its foot centre. A light is offered below it (the door lamps wash it up)."""
    m = M.Model(PREFIX + "big_emblem", px=3.0)
    c, dz = 8.0, 1.6
    m.tube("z", (c, c), 0.0, 1.0, 7.4, BRASS_D, sides=24)                # the round cast ground
    m.ring("z", (c, c, dz / 2.0 + 1.0), 7.0, 0.8, dz, BRASS, sides=28)   # outer bead rim
    _emblem_relief(m, c, c, 1.0, 1.0, ring_mat=BRASS, star_mat=BRASS, proud=dz)
    return m


def _clock():
    """Option B for the great piece over the entrance (A0 #186): a clock, 3x3, of one family with
    the clock tower's face -- a white enamel dial, black hands, a brass bezel. Drawn in one 16-unit
    tile at scale 3 (48 texels across). Anchor: on the wall, its foot centre. The dial glows faintly
    (a lit face at night); a light is offered at its middle."""
    m = M.Model(PREFIX + "clock", px=3.0)
    c = 8.0
    m.tube("z", (c, c), 0.0, 1.0, 7.4, BRASS_D, sides=24)                # back
    m.tube("z", (c, c), 1.0, 1.6, 7.0, BRASS, sides=28)                  # brass bezel ring seat
    m.ring("z", (c, c, 1.6), 6.6, 1.0, 1.4, BRASS, sides=28)             # the bezel
    K.glass_prism(m, "z", (c, c), 1.6, 2.0, 6.0, K.flat("cream", 3), cap=K.flat("cream", 3), emit=4)
    m.box((c, c, 2.0), (c, c, 2.0), BRASS)                               # (placeholder for seed)
    # the dial face: a cream sprite of ticks and the two hands, drawn at 48 px
    face = _clock_face(48)
    m.box((c - 6.0, c - 6.0, 1.9), (c + 6.0, c + 6.0, 2.0), K.flat("cream", 3),
          faces={"s": face}, emit=4, shade=False, grain="x")
    m.tube("z", (c, c), 2.0, 2.3, 0.6, BRASS_D, sides=8)                 # the hand boss
    return m


def _clock_face(n):
    """The clock dial as a Sprite: twelve ticks round a cream face and two black hands."""
    g = [[" "] * n for _ in range(n)]
    c = (n - 1) / 2.0
    r = n / 2.0 - 2.0
    for k in range(12):                                                  # hour ticks
        ang = math.radians(30 * k)
        for t in (r, r - (2.0 if k % 3 == 0 else 1.0)):
            x, y = int(round(c + t * math.sin(ang))), int(round(c - t * math.cos(ang)))
            if 0 <= x < n and 0 <= y < n:
                g[y][x] = "b"
    for ang, length in ((math.radians(300), r * 0.55), (math.radians(80), r * 0.8)):  # two hands
        for s in range(int(length)):
            x, y = int(round(c + s * math.sin(ang))), int(round(c - s * math.cos(ang)))
            if 0 <= x < n and 0 <= y < n:
                g[y][x] = "b"
    rows = ["".join(row) for row in g]
    return Sprite("clock_dial_%d" % n, rows, {"b": IR[0]}, back=None)


def _plate_sign(name, w, h, label, field_mat=ENAMEL, field=EN, frame=BR, text=CR, px=1.0):
    """A thin enamel sign w x h blocks: a brass frame, an enamel field and a cream label. field_mat
    is the plate's material; field/frame/text are the ramps the drawn face takes its colours from.
    Anchor: on the wall, the foot centre."""
    m = M.Model(name, px=px)
    uw, uh = w * 16.0, h * 16.0
    m.box((0.0, 0.0, 0.0), (uw, uh, 1.0), field_mat, grain="x")
    face = _label_sprite(name + "_face", int(uw), int(uh), label, field, text, frame)
    m.box((0.0, 0.0, 1.0), (uw, uh, 1.3), field_mat, faces={"s": face}, grain="x")
    return m


# a 3x5 figure font: digits, a few symbols and the little English the plan allows (V, A, N)
_FONT = {
    "0": ["111", "101", "101", "101", "111"], "1": ["010", "110", "010", "010", "111"],
    "2": ["111", "001", "111", "100", "111"], "3": ["111", "001", "111", "001", "111"],
    "4": ["101", "101", "111", "001", "001"], "5": ["111", "100", "111", "001", "111"],
    "6": ["111", "100", "111", "101", "111"], "7": ["111", "001", "010", "010", "010"],
    "8": ["111", "101", "111", "101", "111"], "9": ["111", "101", "111", "001", "111"],
    "V": ["101", "101", "101", "101", "010"], "A": ["111", "101", "111", "101", "101"],
    "N": ["101", "111", "111", "111", "101"], "+": ["000", "010", "111", "010", "000"],
    "-": ["000", "000", "111", "000", "000"], ".": ["00", "00", "00", "00", "10"],
    ">": ["100", "010", "001", "010", "100"], " ": ["00", "00", "00", "00", "00"],
}


def _label_sprite(name, w, h, label, field, text, frame):
    """An enamel sign face w x h texels: a one-pixel brass frame, the field, and `label` in cream
    figures (3x5, one pixel apart), centred."""
    g = [["f"] * w for _ in range(h)]
    for y in range(1, h - 1):
        for x in range(1, w - 1):
            g[y][x] = "e"
    glyphs = [_FONT.get(ch, _FONT[" "]) for ch in label]
    tw = sum(len(gl[0]) + 1 for gl in glyphs) - 1 if glyphs else 0
    ox = max(1, (w - tw) // 2)
    oy = max(1, (h - 5) // 2)
    x = ox
    for gl in glyphs:
        for j, row in enumerate(gl):
            for i, ch in enumerate(row):
                if ch == "1" and 0 <= oy + j < h and 0 <= x + i < w:
                    g[oy + j][x + i] = "t"
        x += len(gl[0]) + 1
    rows = ["".join(r) for r in g]
    cols = {"f": (frame[3] if isinstance(frame, tuple) else "#bf9433"),
            "e": (field[1] if isinstance(field, tuple) else "#172c57"),
            "t": (text[3] if isinstance(text, tuple) else "#f2ead6")}
    return Sprite(name, rows, cols)


def _nameplate():
    """A 1.5 x 0.5 enamel nameplate -- a voltage warning, cream on blue, brass frame."""
    return _plate_sign(PREFIX + "nameplate", 1.5, 0.5, "500V")


def _number():
    """A 0.5 x 0.5 enamel number plate."""
    return _plate_sign(PREFIX + "number", 0.5, 0.5, "7")


def _flag():
    """A 1 x 1.5 cloth flag on a short pole, the emblem in cream on enamel blue. The flutter is
    A8's; this is the still flag. Anchor: on the wall, the foot of the pole."""
    m = M.Model(PREFIX + "flag", px=1.0)
    m.tube("y", (1.0, 0.5), 0.0, 24.0, 1.0, IRON, sides=8)               # the pole
    m.tube("y", (1.0, 0.5), 24.0, 25.5, 1.2, BRASS, sides=8)             # a finial
    cloth = emblem_sprite("flag_face", 16, CR[3], star_fg=CR[3], back=ENAMEL_CLOTH)
    m.box((2.0, 8.0, 0.0), (18.0, 24.0, 0.6), ENAMEL_CLOTH, faces={"s": cloth, "n": cloth},
          grain="x")
    return m


def _meridian_mark():
    """A 1 x 0.5 brass end-plate for the forecourt meridian line, lying in the paving: a short run of
    the brass band with the emblem stamped on its head. Anchor: the foot centre, it lies flat."""
    m = M.Model(PREFIX + "meridian_mark", px=1.0)
    m.box((6.0, 0.0, 0.0), (10.0, 1.0, 16.0), BRASS, grain="z")          # the band
    m.box((1.0, 0.0, 1.0), (15.0, 1.1, 15.0), BRASS_D, grain="z")        # the stamped head
    stamp = emblem_sprite("mark_face", 16, BR[4], star_fg=BR[5], back=None)
    m.box((1.0, 1.1, 1.0), (15.0, 1.2, 15.0), BRASS_D, faces={"u": stamp}, grain="z")
    return m


def _fingerpost():
    """A 2 x 2 timber fingerpost: a post and two painted fingers. Anchor: the foot centre, it stands
    on the ground."""
    m = M.Model(PREFIX + "fingerpost", px=1.0)
    m.tube("y", (16.0, 16.0), 0.0, 30.0, 1.5, WOOD, sides=8)             # the post
    m.tube("y", (16.0, 16.0), 30.0, 32.0, 2.0, BRASS, sides=8)           # a cap
    for y, side, label in ((24.0, 1.0, "7"), (18.0, -1.0, ">")):        # two fingers
        x0, x1 = (16.0, 30.0) if side > 0 else (2.0, 16.0)
        m.box((x0, y, 15.0), (x1, y + 7.0, 17.0), ENAMEL, grain="x")
        face = _label_sprite("finger_%d" % int(y), int(x1 - x0), 7, label, EN, CR, BR)
        m.box((x0, y, 17.0), (x1, y + 7.0, 17.1), ENAMEL, faces={"s": face}, grain="x")
    return m


# name -> how it is mounted, its scale, where its glowing/lit part is (blocks, model frame) and the
# light level A2 asked for (None: throws no light)
SPEC = {
    "emblem": dict(build=_emblem, mount="wall", scale=1.0, light=None),
    "big_emblem": dict(build=_big_emblem, mount="wall", scale=3.0, light=(0.0, -1.0, 0.3), level=8),
    "clock": dict(build=_clock, mount="wall", scale=3.0, light=(0.0, 0.0, 0.2), level=6),
    "nameplate": dict(build=_nameplate, mount="wall", scale=1.0, light=None),
    "number": dict(build=_number, mount="wall", scale=1.0, light=None),
    "flag": dict(build=_flag, mount="wall", scale=1.0, light=None),
    "meridian_mark": dict(build=_meridian_mark, mount="floor", scale=1.0, light=None),
    "fingerpost": dict(build=_fingerpost, mount="floor", scale=1.0, light=None),
}
SCALE = {PREFIX + name: spec["scale"] for name, spec in SPEC.items()}


@functools.lru_cache(maxsize=None)
def _models():
    return {PREFIX + name: spec["build"]() for name, spec in SPEC.items()}


def models():
    return dict(_models())


def place(canvas, kind, pos, facing="south", origin=(0, 0, 0), light=True, level=None, yaw=None,
          **opts):
    """Place one sign and, if it is a lit one, offer its light to A2. Returns the entity count."""
    spec = SPEC[kind]
    yaw = K.FACING[facing] if yaw is None else yaw
    n = K.put(canvas, _models()[PREFIX + kind], pos, mount=spec["mount"], yaw=yaw,
              scale=spec["scale"], origin=origin, **opts)
    if light and spec.get("light") is not None:
        cell = K.light_cell(pos, yaw, spec["light"], origin)
        K.offer_lights(canvas, [(cell, level if level is not None else spec.get("level", 8))],
                       f"props/signs:{kind}")
    return n


def build(canvas, origin=(0, 0, 0)):
    """What signs place in the master scene: nothing until DRESS is on and A3's fronts give a place
    to hang them. Off, so the master scene always generates and a reworked card shows only in the
    test scene (A0 #211)."""
    if not DRESS:
        return 0
    return 0
