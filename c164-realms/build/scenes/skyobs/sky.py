"""What surrounds the island: a sea of cloud below it, cloud towers on the horizon, sun and moon.

The vanilla cloud layer is switched off in the look (mood.py), so every cloud in view is placed.
Light from the sky only travels straight down, so anything wide casts a shadow that never softens
with distance: the sea is kept out from under the island, and loose clouds are kept narrow.
"""
import numpy as np

from artkit import clouds, respack
from artkit import noise as N

from . import mood

SEA_Y = -84                        # underside of the cloud sea; the island's lowest rock is at -65
BOX = (-236, -236, 236, 172)       # x0, z0, x1, z1: reaches as far as the pictures look
TOP_Y = SEA_Y + 152
# middle of the five columns the pond's outlet drops down, measured in the placed world; the fall
# vanishes into a mound of cloud through a well
FALL = (29.0, 30.0)
FALL_OUT = (0.70, 0.72)            # unit vector from the island towards the open side of the fall

# x, z, length, width, height, heading, seed: piles that rise out of the sea
TOWERS = [
    (128, -92, 120, 70, 118, 20.0, 71),
    (-150, -120, 110, 64, 74, -25.0, 72),
    (-205, 40, 80, 50, 46, 80.0, 73),
    (30, -205, 150, 56, 40, 5.0, 74),
    (205, 70, 70, 46, 58, 95.0, 75),
]
# x, y, z, length, width, height, heading, seed: loose clouds adrift above the sea
WISPS = [
    (-128, -34, 58, 44, 13, 8, 15.0, 81),
    (112, -22, 104, 38, 12, 7, -12.0, 82),
    (70, 24, -150, 54, 14, 9, 4.0, 83),
    (-84, 44, -176, 62, 14, 10, 12.0, 84),
    (-176, 2, -40, 40, 12, 8, 70.0, 85),
]


def _shadow(c):
    """Per column of the box: how many blocks it lies inside the shadow of what is built so far.

    That is how far sky light has to creep sideways to get there, so the light level below is 15
    minus this number.
    """
    x0, z0, x1, z1 = BOX
    cover = np.zeros((x1 - x0 + 1, z1 - z0 + 1), dtype=bool)
    for x, _, z in c.b:
        if x0 <= x <= x1 and z0 <= z <= z1:
            cover[x - x0, z - z0] = True
    depth = np.where(cover, 99, 0)
    for _ in range(16):
        p = np.pad(depth, 1)
        around = np.minimum(np.minimum(p[:-2, 1:-1], p[2:, 1:-1]), np.minimum(p[1:-1, :-2], p[1:-1, 2:]))
        depth = np.where(cover, np.minimum(depth, around + 1), 0)
    return depth


def build(c, fall=FALL, out=FALL_OUT):
    """fall, out: where the last waterfall comes down and the side it is open to."""
    x0, z0, x1, z1 = BOX
    # thin the sea where the island dims it and leave it out where the shadow would turn it dark
    bar = N.smoothstep(1.5, 4.5, _shadow(c).astype(float))
    field = clouds.Field(x0, SEA_Y - 5, z0, x1, TOP_Y, z1)
    field.sea(SEA_Y, seed=41, cover=0.54, keep_out=lambda X, Z: bar)
    for x, z, length, width, height, heading, seed in TOWERS:
        field.cumulus(x, SEA_Y + 2, z, length, width, height, seed=seed, heading=heading)
    for x, y, z, length, width, height, heading, seed in WISPS:
        field.cumulus(x, y, z, length, width, height, seed=seed, heading=heading)
    fx, fz = fall
    field.cumulus(fx + 9 * out[0], SEA_Y, fz + 9 * out[1], 30, 26, 9, seed=91, puffs=16)
    field.well(fx, fz, 3.7)
    return field.write(c, seed=3)


# ---- sun and moon ------------------------------------------------------------------------------
def _hex(s):
    return np.array([int(s[i:i + 2], 16) for i in (1, 3, 5)], dtype=float)


def _celestial(radius, core, rim, glow, halo, marks=()):
    """Disc with a glow around it on black; the game adds these textures onto the sky.

    The disc is drawn on a 64 pixel grid like any other texture here, the glow on a grid four times
    finer so that it fades without rings. halo = [(strength, reach), ...]: each term starts at
    `strength` on the rim of the disc and falls to 1/e of that `reach` pixels further out.
    """
    fine = 4
    n = 64 * fine
    jj, ii = np.meshgrid((np.arange(n) + 0.5) / fine - 32.0, (np.arange(n) + 0.5) / fine - 32.0, indexing="ij")
    d = np.hypot(ii, jj)
    amount = sum(s * np.exp(-np.maximum(d - radius, 0.0) / reach) for s, reach in halo)
    amount = amount * (1.0 - N.smoothstep(24.0, 31.5, d))
    px = amount[..., None] * _hex(glow)[None, None, :]
    # the disc itself keeps whole pixels: test the middle of each coarse pixel
    cj, ci = np.floor(jj) + 0.5, np.floor(ii) + 0.5
    cd = np.hypot(ci, cj)
    px[cd <= radius] = _hex(rim)
    px[cd <= radius - 1.6] = _hex(core)
    for mx, my, mr, colour in marks:
        px[(np.hypot(ci - mx, cj - my) <= mr) & (cd <= radius - 0.8)] = _hex(colour)
    return np.clip(px, 0, 255).astype(np.uint8)


def write_pack(pack_dir):
    """Cloud tones, and the pictures for the one body in the sky (mood.PHASES): the moon object plays
    the sun too, so its eight phase textures hold two suns, the moon, their fades and a blank."""
    out = clouds.write_pack(pack_dir)
    # the moon's square is two thirds the size of the sun's, hence the large discs
    sun = _celestial(11.4, "#fffdf2", "#fff0b4", "#ffc878", [(0.40, 3.0), (0.16, 12.0)]).astype(float)
    warm = _celestial(11.4, "#fff6dc", "#ffd98a", "#ffa052", [(0.48, 3.2), (0.20, 12.0)]).astype(float)
    moon = _celestial(10.6, "#f2f6ff", "#d3ddf4", "#7fa2f0", [(0.30, 2.4), (0.10, 8.0)],
                      marks=[(-3.5, -2.5, 2.3, "#cdd8f0"), (3.0, 3.5, 1.8, "#cdd8f0"), (2.5, -4.5, 1.2, "#bcc9e6"),
                             (-4.5, 4.0, 1.2, "#bcc9e6"), (5.5, -0.5, 0.9, "#cdd8f0"), (-0.5, 1.0, 0.9, "#bcc9e6")]).astype(float)
    pictures = {
        "sun": sun, "sun_warm": warm, "sun_half": warm * 0.5, "sun_faint": warm * 0.2, "blank": sun * 0.0,
        "moon_faint": moon * 0.2, "moon_half": moon * 0.5, "moon": moon,
    }
    for role, px in pictures.items():
        phase = mood.PHASES[role]
        respack.texture(pack_dir, "environment/celestial/moon/" + phase, px.astype(np.uint8))
        out.append(f"{role} -> moon/{phase}")
    respack.texture(pack_dir, "environment/celestial/sun", (sun * 0.0).astype(np.uint8))
    out.append("sun texture blanked")
    return out
