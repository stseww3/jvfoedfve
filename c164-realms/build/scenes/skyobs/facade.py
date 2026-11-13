"""What hangs on the buildings: the astronomical clock on the tower and the banners under its gallery.

Registered through props.py (SCALE, MODELS and GALLERY are merged into its lists).
"""
import math

from artkit import models as M
from artkit import pixelart as P

SCALE = {"sky_clock": 2.0, "star_banner": 2.0}
CLOCK = 40                    # the clock face in model pixels: five blocks across at its scale
SUN_AT, MOON_AT = -58.0, 128.0   # where the two hands point, in degrees left of straight up

NIGHT = {"n": "#172152", "N": "#0d1433", "m": "#24337a", "g": "#dcb650", "G": "#f3d98a", "b": "#bf9433",
         "d": "#7a551a", "o": "#2c1d10", "s": "#fff2b0", "w": "#e8e4d0"}
GOLD = P.Mat("clock_gold", ["#dcb650", "#f3d98a"], kind="flat", bevel=0, base=1)
SILVER = P.Mat("clock_silver", ["#c9c6b4", "#e8e4d0"], kind="flat", bevel=0, base=1)
NAVY_FLAT = P.Mat("clock_navy", ["#172152"], kind="flat", bevel=0)
CLOTH = P.Mat("banner_cloth", ["#0f1740", "#172152", "#1f2c66"], kind="flat", bevel=0, base=1)


def clock_rows(n=CLOCK):
    """The clock face as pixels: a ring of hours with a tick for each of the twenty-four, inside it
    the night sky over a darker ground, and the off-centre ring of the zodiac."""
    c = (n - 1) / 2.0
    R = n / 2.0
    rows = []
    for j in range(n):
        row = ""
        for i in range(n):
            dx, dy = i - c, j - c
            r = math.hypot(dx, dy)
            a = math.degrees(math.atan2(dy, dx)) % 360.0
            if r >= R:
                ch = "."
            elif r >= R - 1.7:
                ch = "d"                                    # under the brass rim
            elif r >= R - 5.8:
                ch = "N"                                    # the ring of hours
                near = round(a / 15.0) * 15.0
                off = abs(r * math.sin(math.radians(a - near)))
                k = int(near) % 360
                if k % 90 == 0 and off < 1.0 and R - 5.4 <= r < R - 2.0:
                    ch = "G"
                elif k % 90 and off < 0.55 and R - 4.8 <= r < R - 2.6:
                    ch = "g"
            elif r >= R - 6.6:
                ch = "b"
            else:
                # sky above an arc of horizon, darker below it
                below = math.hypot(dx, dy - 21.0) < 16.5
                ch = "N" if below else "n"
                if abs(math.hypot(dx, dy - 21.0) - 16.5) < 0.6:
                    ch = "d"
                if not below and P._hash(i * 7 + 3, j * 11 + 5, 29) > 0.93:
                    ch = "s"
                zr = math.hypot(dx - 2.5, dy + 2.5)
                if 6.6 <= zr < 7.6:
                    ch = "g"
                    za = math.degrees(math.atan2(dy + 2.5, dx - 2.5)) % 30.0
                    if za < 4.0:
                        ch = "d"                            # the twelve signs are marked off
            row += ch
        rows.append(row)
    return rows


def sky_clock():
    """The astronomical clock of the observatory: a night-blue face in a brass case, a sun hand and
    a moon hand that stay bright after dark. It looks to +z. Anchor: the middle of its back."""
    face = P.Sprite("sky_clock_face", clock_rows(), NIGHT)
    m = M.Model("sky_clock", px=2, anchor=(0, 0, 0))
    R = CLOCK / 2.0
    m.tube("z", (0, 0), 0.0, 1.6, R - 0.4, P.BRASS_DARK, sides=24)
    m.box((-R, -R, 1.2), (R, R, 1.7), NAVY_FLAT, faces={"s": face}, skip="newud")
    m.ring("z", (0, 0, 1.6), R - 1.1, 1.8, 1.4, P.BRASS, sides=24)
    m.ring("z", (0, 0, 2.2), R - 0.5, 0.6, 0.6, P.BRASS_DARK, sides=24)
    # the sun hand: a gold bar with the sun at two thirds of its length
    with m.turned(("z", SUN_AT)):
        m.box((-0.5, -3.0, 2.0), (0.5, 15.5, 2.4), GOLD, emit=15, shade=False)
        m.tube("z", (0, 10.5), 2.0, 2.8, 2.3, GOLD, sides=12, emit=15, shade=False)
        for k in range(8):
            with m.turned(("z", 45.0 * k), about=(0, 10.5, 0)):
                m.box((-0.35, 13.2, 2.1), (0.35, 14.4, 2.5), GOLD, emit=15, shade=False)
    # the moon hand: shorter, silver, the moon a disc with its dark side let in
    with m.turned(("z", MOON_AT)):
        m.box((-0.4, -2.0, 2.5), (0.4, 12.0, 2.8), SILVER, emit=13, shade=False)
        m.tube("z", (0, 9.0), 2.5, 3.2, 1.9, SILVER, sides=12, emit=15, shade=False)
        m.tube("z", (0.9, 9.5), 2.6, 3.3, 1.45, NAVY_FLAT, sides=12)
    m.tube("z", (0, 0), 1.7, 3.5, 1.5, P.BRASS, sides=12)
    m.tube("z", (0, 0), 3.5, 3.9, 0.8, P.BRASS_DARK, sides=8)
    return m


STAR = ("..GG..", "..GG..", "..GG..", ".gGGg.", "GGGGGG", ".gGGg.", "..GG..", "..GG..", "..GG..")
MOON = ("..www.", ".ww...", "ww....", "ww....", ".ww...", "..www.")


def banner_rows(w=10, h=28):
    """A swallow-tailed banner: night blue with a gold edge, the star over the crescent moon."""
    c = (w - 1) / 2.0
    rows = []
    for j in range(h):
        row = ""
        for i in range(w):
            cut = (j - (h - 7)) * 0.85            # half the width of the cut between the two tails
            if j >= h - 6 and abs(i - c) < cut:
                ch = "."
            elif i in (0, w - 1) or j == 0 or (j >= h - 6 and abs(i - c) < cut + 1.0):
                ch = "g"
            else:
                ch = "n"
                for glyph, top in ((STAR, 3), (MOON, 14)):
                    if top <= j < top + len(glyph) and 2 <= i < 8 and glyph[j - top][i - 2] != ".":
                        ch = glyph[j - top][i - 2]
            row += ch
        rows.append(row)
    return rows


def star_banner():
    """A banner hanging from a rod, with a little slack in the cloth; it looks to +z.
    Anchor: the middle of the rod."""
    rows = banner_rows()
    m = M.Model("star_banner", px=2, anchor=(0, 0, 0))
    m.tube("x", (0, 0), -6.5, 6.5, 0.45, P.BRASS_DARK, sides=8)
    for sx in (-6.9, 6.9):
        m.ball((sx, 0, 0), 0.8, P.BRASS, sides=8, layers=4)
    y, z = -0.3, 0.0
    for k, tilt in enumerate((5.0, -4.0, 6.0, -3.0)):
        part = P.Sprite(f"star_banner{k}", rows[7 * k:7 * k + 7], NIGHT)
        with m.turned(("x", tilt), about=(0, y, z)):
            m.box((-5, y - 7.0, z - 0.12), (5, y, z + 0.12), CLOTH, faces={"s": part, "n": part.mirrored()}, skip="ewud")
        y, z = y - 7.0 * math.cos(math.radians(tilt)), z - 7.0 * math.sin(math.radians(tilt))
    return m


MODELS = [sky_clock, star_banner]

GALLERY = [
    ("clock", [("sky_clock", (0, 3.0, 0), {"brightness": (15, 9)})], (2.6, 3.4, 6.0), (0, 3.0, 0)),
    ("banner", [("star_banner", (0, 4.0, 0), {})], (1.2, 3.0, 3.6), (0, 2.4, 0)),
]
