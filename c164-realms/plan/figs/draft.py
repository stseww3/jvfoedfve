"""Shared pieces of the plan figures: the palette, draft block textures and small drawing helpers.

Everything here is a design draft. The colour ramps are the ones the art plan fixes
(plan/02-palette-materials.md); the 16x16 textures are quick drafts that show the intended kind of
surface, not the final art of the materials part.
"""
import io
import os
import zipfile

import numpy as np
from PIL import Image, ImageDraw, ImageFont

JAR = os.environ.get("MC_JAR", "/agent/realms-study/client26/versions/26.3/26.3.jar")
FONT = os.environ.get("PLAN_FONT", "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc")


def hx(s):
    s = s.lstrip("#")
    return tuple(int(s[i:i + 2], 16) for i in (0, 2, 4))


def hxf(s):
    return np.array(hx(s), dtype=float) / 255.0


# Sky and light of the fixed hour (just after sunset, looking west).
SKY = {
    "zenith": "#0d1433", "high": "#18214e", "mid": "#383a74", "low": "#84507c", "ember": "#e97c4c",
    "hot": "#ffc47c", "cloud_far": "#c98a8e", "cloud_near": "#565c8c", "cloud_gap": "#1d2246",
    "cool": "#7f93d8", "warm": "#ffb45e", "ambient": "#161a2c",
}

# Material ramps, dark to light. Blocks and models paint with the same ramps.
RAMPS = {
    "ashlar": ["#847f77", "#a09a8e", "#b7b0a1", "#c8c1b0", "#d6cfbf", "#e2dccd"],
    "iron": ["#12151a", "#1b2027", "#252b34", "#303844", "#414b59", "#5d6877", "#8591a0"],
    "brass": ["#5a3c12", "#7a551a", "#9c7424", "#bf9433", "#dcb650", "#f3d98a"],
    "verdigris": ["#2f6f5c", "#3d8a70", "#4fa487", "#6dbb9c", "#93d3b6"],
    "copper": ["#5e4636", "#7c5f4c", "#9b7a65", "#b3937c", "#c9ab94"],
    "wood": ["#2c1d10", "#3a2716", "#4a331d", "#5b4025", "#6c4d2e"],
    "slate": ["#1c1d22", "#26272d", "#303138", "#3b3c44", "#494a53"],
    "glow": ["#c96a1c", "#f09a2e", "#ffc65a", "#ffe9a6", "#fff8dc"],
    "phosphor": ["#0f3d2c", "#1c7a55", "#3fd08d", "#8dffc4", "#e3fff0"],
    "signal": ["#5e1410", "#a3201a", "#e8402e", "#ff8a6a"],
    "enamel": ["#0f1e3d", "#172c57", "#1f3a6e", "#2e4f8f", "#f2ead6"],
    "night_glass": ["#141a36", "#1c2548", "#27335f", "#3a4a80", "#5a6ea8"],
}


def ramp(name):
    return np.array([hx(c) for c in RAMPS[name]], dtype=np.uint8)


def from_idx(idx, r, alpha=255):
    out = np.zeros(idx.shape + (4,), np.uint8)
    out[..., :3] = r[np.clip(idx, 0, len(r) - 1)]
    out[..., 3] = alpha
    return out


def rng(seed):
    return np.random.default_rng(seed)


_zip = None


def vanilla(name):
    """A vanilla block texture (first frame) as 16x16 RGBA."""
    global _zip
    if _zip is None:
        _zip = zipfile.ZipFile(JAR)
    im = Image.open(io.BytesIO(_zip.read(f"assets/minecraft/textures/block/{name}.png"))).convert("RGBA")
    return np.array(im)[:16, :16].copy()


# ---------------------------------------------------------------------------------------------
# draft textures


def tex_ashlar(seed=0):
    """Fine ashlar: two courses to the block, stones a block long, joints staggered."""
    g = rng(seed)
    idx = np.full((16, 16), 3)
    tone = g.integers(-1, 2, size=2)
    idx[0:7] += tone[0]
    idx[8:15] += tone[1]
    idx[0] += 1
    idx[8] += 1
    idx[6] -= 1
    idx[14] -= 1
    idx[7] = 0
    idx[15] = 0
    idx[0:7, 15] = 1
    idx[8:15, 7] = 1
    for _ in range(8):
        y, x = g.integers(0, 16, 2)
        if idx[y, x] > 1:
            idx[y, x] -= 1
    return from_idx(idx, ramp("ashlar"))


def tex_rustic(seed=0):
    """Rock-faced stone for the ground storey: one stone to the block, deep joints, a rough face."""
    g = rng(seed)
    idx = np.full((16, 16), 2)
    for _ in range(11):                      # short chisel marks, lit above and dark below
        y, x, n = int(g.integers(3, 12)), int(g.integers(3, 12)), int(g.integers(1, 3))
        idx[y, x:x + n] = 3
        idx[y + 1, x:x + n] = 1
    idx[1, 1:15] = 3
    idx[1:15, 1] = 3
    idx[14, 1:15] = 1
    idx[1:15, 14] = 1
    idx[15] = 0
    idx[:, 15] = 0
    idx[0] = 1
    idx[:, 0] = 1
    return from_idx(idx, ramp("ashlar"))


def tex_moulding(flip=False):
    """A horizontal moulding profile: string courses, cornices, bases and capitals."""
    rows = [5, 4, 2, 3, 3, 4, 3, 3, 3, 3, 3, 4, 4, 2, 1, 0]
    idx = np.repeat(np.array(rows)[:, None], 16, axis=1)
    if flip:
        idx = idx[::-1]
    return from_idx(idx, ramp("ashlar"))


def tex_iron(seed=0, rivets=True):
    g = rng(seed)
    n = g.random((16, 16))
    idx = np.full((16, 16), 3) - (n < 0.18).astype(int) + (n > 0.92).astype(int)
    idx[0] = 4
    idx[:, 0] = 4
    idx[15] = 1
    idx[:, 15] = 1
    if rivets:
        for y, x in [(2, 2), (2, 13), (12, 2), (12, 13), (2, 7), (12, 8), (7, 2), (7, 13)]:
            idx[y, x] = 6
            idx[y + 1, x] = 1
    return from_idx(idx, ramp("iron"))


def tex_grate():
    """Walkway grating: bars with see-through gaps."""
    yy, xx = np.mgrid[0:16, 0:16]
    bar = (xx % 4 == 0) | (yy % 4 == 0)
    idx = np.where((xx % 4 == 0) & (yy % 4 == 0), 5, 3)
    out = from_idx(idx, ramp("iron"))
    out[..., 3] = np.where(bar, 255, 0)
    return out


def tex_brass(seed=0):
    g = rng(seed)
    idx = np.full((16, 16), 3) + (g.random((16, 1)) > 0.6).astype(int) - (g.random((16, 1)) < 0.25).astype(int)
    idx[0] = 5
    idx[15] = 1
    idx[:, 0] = np.maximum(idx[:, 0], 4)
    idx[:, 15] = 1
    for y, x in [(2, 2), (2, 13), (13, 2), (13, 13)]:
        idx[y, x] = 5
        idx[min(15, y + 1), x] = 0
    return from_idx(idx, ramp("brass"))


LIT_GLASS = ["#e8962e", "#f7b24a", "#ffc96a", "#ffdc8f", "#ffeebe"]


def tex_window(lit=True, seed=0):
    """Glazing with thin iron bars: eight-pixel panes, so a three-block window shows six across."""
    g = rng(seed)
    yy, xx = np.mgrid[0:16, 0:16]
    if lit:
        tone = g.choice([1, 2, 2, 2, 3], size=(2, 2))
        idx = tone[yy // 8, xx // 8]
        idx = idx + ((yy % 8 == 0) & (xx % 8 < 6)).astype(int)
        px = from_idx(idx, np.array([hx(c) for c in LIT_GLASS], dtype=np.uint8))
    else:
        idx = np.full((16, 16), 1)
        idx[np.abs(xx - yy + 4) <= 1] = 2
        idx[np.abs(xx - yy - 5) <= 0] = 3
        px = from_idx(idx, ramp("night_glass"))
    bars = (xx % 8 == 7) | (yy % 8 == 7)
    px[bars, :3] = hx(RAMPS["iron"][1])
    return px


def tex_panel(seed=0):
    """A sunk stone panel: aprons under windows, friezes."""
    idx = np.full((16, 16), 3)
    idx[2, 2:14] = 1
    idx[2:14, 2] = 1
    idx[13, 2:14] = 5
    idx[2:14, 13] = 5
    idx[3:13, 3:13] = 2
    idx[15] = 0
    return from_idx(idx, ramp("ashlar"))


def _casing(seed):
    px = tex_iron(seed, rivets=False)
    for y, x in [(1, 1), (1, 14), (14, 1), (14, 14)]:
        px[y, x, :3] = hx(RAMPS["iron"][6])
    return px


def tex_gauge(seed=0):
    """Instrument panel: a dial with a brass bezel and two pilot lamps."""
    px = _casing(seed)
    yy, xx = np.mgrid[0:16, 0:16]
    d = np.hypot(xx - 6.5, yy - 6.5)
    px[d <= 5.4, :3] = hx(RAMPS["brass"][3])
    px[(d <= 5.4) & (yy > xx), :3] = hx(RAMPS["brass"][2])
    px[d <= 4.3, :3] = hx(RAMPS["enamel"][4])
    px[(d <= 4.3) & (d > 3.4) & ((xx + yy) % 2 == 0), :3] = hx("#8a8371")
    for t in range(5):
        px[int(round(6.5 - t * 0.8)), int(round(6.5 + t * 0.6)), :3] = hx("#1b2027")
    px[6, 6, :3] = hx(RAMPS["brass"][1])
    px[12:14, 12:14, :3] = hx(RAMPS["glow"][2])
    px[12, 12, :3] = hx(RAMPS["glow"][4])
    px[12:14, 9:11, :3] = hx(RAMPS["phosphor"][2])
    px[12, 9, :3] = hx(RAMPS["phosphor"][4])
    return px


def tex_switches(seed=0):
    """Instrument panel: three knife switches on slate, fuses below."""
    px = _casing(seed)
    px[2:14, 2:14, :3] = hx("#2a2e36")
    for i, x in enumerate((3, 7, 11)):
        up = i != 1
        px[3:5, x:x + 2, :3] = hx(RAMPS["brass"][2])
        px[8:10, x:x + 2, :3] = hx(RAMPS["brass"][2])
        if up:
            px[3:9, x, :3] = hx(RAMPS["brass"][4])
            px[2:4, x:x + 2, :3] = hx("#0f1114")
        else:
            px[6:9, x + 1, :3] = hx(RAMPS["brass"][4])
            px[5:7, x:x + 2, :3] = hx("#0f1114")
        px[11:13, x:x + 2, :3] = hx(RAMPS["enamel"][4])
        px[12, x:x + 2, :3] = hx("#b9b19c")
    return px


def tex_tubes(seed=0):
    """Instrument panel: three glowing valves behind a guard, knobs below."""
    px = _casing(seed)
    px[2:11, 2:14, :3] = hx("#0c0e12")
    for x in (3, 7, 11):
        px[3:10, x:x + 2, :3] = hx(RAMPS["glow"][1])
        px[4:8, x:x + 2, :3] = hx(RAMPS["glow"][2])
        px[5:7, x, :3] = hx(RAMPS["glow"][4])
        px[3, x:x + 2, :3] = hx("#5d6877")
        px[10, x:x + 2, :3] = hx(RAMPS["brass"][1])
    px[6, 2:14, :3] = (px[6, 2:14, :3] * 0.55).astype(np.uint8)
    for x in (3, 7, 11):
        px[12:14, x:x + 2, :3] = hx(RAMPS["brass"][3])
        px[12, x, :3] = hx(RAMPS["brass"][5])
    return px


def tex_scope(seed=0):
    """Instrument panel: a round green screen with a trace."""
    px = _casing(seed)
    yy, xx = np.mgrid[0:16, 0:16]
    d = np.hypot(xx - 7.5, yy - 6.5)
    px[d <= 5.6, :3] = hx("#0c0e12")
    px[d <= 4.7, :3] = hx(RAMPS["phosphor"][0])
    px[(d <= 4.7) & ((xx % 3 == 1) | (yy % 3 == 0)), :3] = hx("#14503a")
    for x in range(4, 12):
        y = int(round(6.5 - 2.2 * np.sin((x - 4) * 0.9)))
        px[y, x, :3] = hx(RAMPS["phosphor"][3])
    for x in (3, 7, 11):
        px[13:15, x:x + 2, :3] = hx(RAMPS["brass"][3])
    return px


DIGITS = {"0": "111101101101111", "4": "101101111001001", "2": "111001111100111", "7": "111001001001001",
          "1": "010110010010111", "9": "111101111001111"}


def tex_counter(seed=0, text="0427"):
    """Instrument panel: a wheel counter above a row of jacks."""
    px = _casing(seed)
    px[2:9, 1:15, :3] = hx("#0c0e12")
    for i, ch in enumerate(text[:4]):
        x0 = 2 + i * 3 + (1 if i >= 2 else 0)
        px[3:8, x0:x0 + 3, :3] = hx(RAMPS["enamel"][4])
        bits = DIGITS[ch]
        for k, b in enumerate(bits):
            if b == "1":
                px[3 + k // 3, x0 + k % 3, :3] = hx("#1b2027")
    for x in (2, 5, 8, 11):
        px[11:13, x:x + 2, :3] = hx(RAMPS["brass"][2])
        px[11, x, :3] = hx("#0c0e12")
    return px


def tex_door():
    """A riveted iron door leaf with a porthole, 24 px wide and 64 px tall (one and a half blocks by four)."""
    g = rng(5)
    idx = np.full((64, 24), 3) - (g.random((64, 24)) < 0.15).astype(int)
    idx[:, 0] = 5
    idx[:, 23] = 1
    idx[0] = 5
    idx[63] = 1
    for y0, y1 in ((3, 28), (33, 60)):
        idx[y0, 3:21] = 1
        idx[y1, 3:21] = 5
        idx[y0:y1, 3] = 1
        idx[y0:y1, 20] = 5
    for y in (1, 30, 31, 62):
        for x in (2, 7, 12, 17, 21):
            idx[y, x] = 6
    out = from_idx(idx, ramp("iron"))
    yy, xx = np.mgrid[0:64, 0:24]
    d = np.hypot(xx - 11.5, yy - 15.5)
    out[d <= 6.5, :3] = hx(RAMPS["brass"][3])
    out[(d <= 6.5) & (yy > xx + 4), :3] = hx(RAMPS["brass"][1])
    out[d <= 4.6, :3] = hx(RAMPS["glow"][2])
    out[(d <= 4.6) & (d > 2.5), :3] = hx(RAMPS["glow"][1])
    out[(d <= 4.6) & (xx == 11), :3] = hx(RAMPS["iron"][1])
    out[40:50, 19:21, :3] = hx(RAMPS["brass"][4])
    out[50, 19:21, :3] = hx(RAMPS["brass"][1])
    return out


# ---------------------------------------------------------------------------------------------
# drawing helpers


def font(size):
    return ImageFont.truetype(FONT, size)


def upscale(a, k):
    return np.repeat(np.repeat(a, k, axis=0), k, axis=1)


def tile_block(tex, k=4, nx=3, ny=2, seeds=None):
    """nx by ny blocks of one texture, each texel k pixels; tex may be a function of a seed."""
    rows = []
    for j in range(ny):
        row = [tex(seeds[j * nx + i] if seeds else j * nx + i) if callable(tex) else tex for i in range(nx)]
        rows.append(np.concatenate(row, axis=1))
    return upscale(np.concatenate(rows, axis=0), k)


def on_dark(tex, back=(24, 27, 44)):
    """Flatten a texture with transparency onto a backdrop."""
    a = tex[..., 3:4].astype(float) / 255.0
    out = tex.copy()
    out[..., :3] = (tex[..., :3] * a + np.array(back) * (1 - a)).astype(np.uint8)
    out[..., 3] = 255
    return out


def label(draw, xy, text, size=18, fill=(232, 228, 216), anchor="la"):
    draw.text(xy, text, font=font(size), fill=fill, anchor=anchor)


def tag(draw, xy, n, r=13, fill=(243, 217, 138), ink=(20, 22, 34)):
    """A numbered callout disc."""
    x, y = xy
    draw.ellipse((x - r, y - r, x + r, y + r), fill=fill, outline=ink, width=2)
    draw.text((x, y - 1), str(n), font=font(int(r * 1.35)), fill=ink, anchor="mm")
