#!/usr/bin/env python3
"""Design sketches and numbers for the detailed design of the sky category (plan/parts/sky.md).

    python plan/parts/figs/sky_draft.py [--only looks,views,pano,sprites,clouds,tones,lights,timeline] [--size 720]
    python plan/parts/figs/sky_draft.py --numbers        # the tables quoted in sky.md and sky-notes.md

Small numpy pictures, a few seconds each; run them one at a time (nice) on the shared machine.

These are sketches, not pictures of the game. The sky, the fog, the sunset fan, the two sky sprites,
the cloud layer and the light table are computed with the formulas read from the 26.3 client
(SkyRenderer, AtmosphericFogEnvironment, clouds.fsh, lightmap.fsh), so colours and angles are the ones
the game would show. The buildings are plain boxes at the sizes of ART-PLAN section 4, there to
check sight lines and tone, not architecture. Camera positions are assumptions until the scene
skeleton fixes them.

The pictures were drawn before common/skeleton.py existed: the front court is 30 deep here (V2 at
x = 46), the fog ends at 144 and the comet stands at moon_angle 37. sky.md has since moved to the
skeleton's court (stair head at x = 60), fog end 192 and moon_angle 42; the test scenes of the sky
cards are the place for pictures with the final numbers, not this script.
"""
import argparse
import io
import math
import os
import sys
import zipfile

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(HERE))), "build"))

from artkit import gamelook as G  # noqa: E402

JAR = os.environ.get("MC_JAR", "/agent/realms-study/client26/versions/26.3/26.3.jar")
FONT = os.environ.get("PLAN_FONT", "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc")
BG, INK, DIM, GOLD = (20, 23, 42), (232, 228, 216), (150, 154, 178), (243, 217, 138)
FOV = 70.0


def hx(s):
    s = s.lstrip("#")
    return np.array([int(s[i:i + 2], 16) for i in (0, 2, 4)], dtype=float) / 255.0


def to_hex(c):
    return "#%02x%02x%02x" % tuple(int(round(float(v) * 255.0)) for v in np.clip(c, 0.0, 1.0))


def luma(c):
    return float(0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2])


def font(size):
    return ImageFont.truetype(FONT, size)


def label(dr, xy, text, size=18, fill=INK):
    dr.text(xy, text, font=font(size), fill=fill)


# ---------------------------------------------------------------------------------------------
# the three light versions: what the player should see, and the attribute values that give it

LOOKS = {
    "blue": dict(
        title="A 蓝调时刻（方案值，默认）", marker="c164art:blue", tick=14000, phase="full_moon",
        zenith="#0d1433", horizon="#383a74", sky_fog_end=96.0,
        glow="#e97c4c", glow_alpha=0.45, sun_angle=92.0, moon_angle=37.0, stars=0.60,
        sky_light="#7f93d8", sky_factor=0.40, lamp="#ffb45e", ambient="#161a2c",
        cloud="#565c8c", cloud_alpha=0.94, comet=1.0),
    "deep": dict(
        title="B 更深的夜", marker="c164art:deep", tick=18000, phase="waning_gibbous",
        zenith="#080c22", horizon="#24274f", sky_fog_end=128.0,
        glow="#c8553a", glow_alpha=0.25, sun_angle=97.0, moon_angle=37.0, stars=0.95,
        sky_light="#7388d8", sky_factor=0.26, lamp="#ffb45e", ambient="#141829",
        cloud="#3b4170", cloud_alpha=0.94, comet=1.25),
    "glow": dict(
        title="C 余晖更强", marker="c164art:glow", tick=12900, phase="third_quarter",
        zenith="#141a44", horizon="#4a4484", sky_fog_end=80.0,
        glow="#f0864f", glow_alpha=0.85, sun_angle=90.0, moon_angle=37.0, stars=0.30,
        sky_light="#8a96d8", sky_factor=0.48, lamp="#ffb45e", ambient="#191c31",
        cloud="#6a6a9a", cloud_alpha=0.94, comet=0.8),
}
FOG_START, FOG_END = 60.0, 144.0
CLOUD_TOP = -28.0            # top of the vanilla cloud layer, in scene levels (upper platform = 0)
CLOUD_THICK = 4.0
CLOUD_CELL = 12.0
CLOUD_FOG_END = 768.0

# the near cloud field built of blocks: a sheet lying on the vanilla layer, with billows on it
NEAR_TOP = -26.0             # top of the sheet
NEAR_BILLOW = 3.0            # billows stand this much higher
NEAR_CELL = 6.0              # size of a billow in the sketch
NEAR_SOLID, NEAR_END = 150.0, 215.0     # distance from the site centre: closed inside, thinning out to nothing
SITE_CENTRE = (30.0, 0.0)
NEAR_SHOWN = ("#666c9c", "#565c8c", "#474c7a")    # what billow tops, the sheet and its hollows should show in version A

# the timeline: (tick, version) keyframes over one day of 24000 ticks, and the named moments
KEYS = [(0, "blue"), (12000, "blue"), (12600, "glow"), (13200, "glow"), (13600, "blue"), (15000, "blue"),
        (16000, "deep"), (21000, "deep"), (22000, "blue")]
MARKERS = {"c164art:glow": 12900, "c164art:blue": 14000, "c164art:deep": 18000}
VANILLA_MARKERS = {"day": 1000, "noon": 6000, "night": 13000, "midnight": 18000}


def mix_share(sky_fog_end, render_chunks=32):
    """AtmosphericFogEnvironment: how far the fog colour is drawn towards the sky colour."""
    e = min(sky_fog_end / 16.0, float(render_chunks))
    return 1.0 - (0.25 + 0.75 * min(1.0, e / 32.0)) ** 0.25


def derive(v):
    """sky_color and fog_color to write so that the zenith and the horizon show the wanted colours
    (the game mixes the two: the horizon takes a share of the sky colour, the zenith a share of fog)."""
    z = 16.0 / v["sky_fog_end"]
    m = mix_share(v["sky_fog_end"])
    Z, H = hx(v["zenith"]), hx(v["horizon"])
    sky = np.clip((Z - z * H) / (1.0 - z), 0.0, 1.0)
    fog = np.clip((H - m * sky) / (1.0 - m), 0.0, 1.0)
    return sky, fog


def attrs(v):
    """What gamelook.lightmap wants."""
    return {"block_light_tint": hx(v["lamp"]), "sky_light_color": hx(v["sky_light"]),
            "ambient_light_color": hx(v["ambient"]), "sky_light_factor": v["sky_factor"]}


# ---------------------------------------------------------------------------------------------
# sky sprites, drawn the way the player sees them in the western sky (top = up, left = south)

def comet(n=256, strength=1.0, lean=12.0, tail=16.0, spread=2.3):
    """The comet for the moon's square (22.6 degrees wide): head low, tails up.

    Head and tail core sit on a 64 pixel grid like other textures; the glow is drawn at full
    resolution so that it fades without rings. Colours add onto the sky."""
    deg = 22.62 / n                                   # degrees per pixel
    yy, xx = np.meshgrid((np.arange(n) + 0.5), (np.arange(n) + 0.5), indexing="ij")
    hx_, hy_ = n * 0.5, n * 0.5 + 7.0 / deg           # the head: 7 degrees below the middle
    x = (xx - hx_) * deg                              # degrees right of the head
    y = (hy_ - yy) * deg                              # degrees above the head
    cream, white, blue = hx("#ffe9a6"), hx("#fff8dc"), hx("#7f93d8")
    out = np.zeros((n, n, 3))
    # dust tail: leans and curves to the right (north), widens with height
    t = np.clip(y / tail, 0.0, 1.2)
    centre = math.tan(math.radians(lean)) * y + 2.2 * t * t
    width = 0.55 + spread * t
    dust = np.exp(-0.5 * ((x - centre) / width) ** 2) * np.exp(-2.6 * t) * (y > -0.3) * (t < 1.15)
    dust *= np.clip((1.15 - t) / 0.25, 0.0, 1.0)
    # ion tail: straight, thin, a little to the left of the dust tail
    ion_c = -math.tan(math.radians(4.0)) * y
    ion = np.exp(-0.5 * ((x - ion_c) / 0.32) ** 2) * np.exp(-1.7 * np.clip(y / (tail * 1.12), 0, 2)) * (y > 0.2)
    ion *= np.clip((tail * 1.12 - y) / 3.0, 0.0, 1.0)
    # coma
    r = np.hypot(x, y)
    coma = np.exp(-r / 0.9)
    out += cream[None, None, :] * (0.62 * dust)[..., None]
    out += blue[None, None, :] * (0.45 * ion)[..., None]
    out += white[None, None, :] * (0.9 * coma)[..., None]
    # the pixel core: 64-grid cells, hard-edged
    cell = n // 64
    cy, cx = int(hy_ // cell), int(hx_ // cell)
    core = [(0, 0, 1.0), (-1, 0, 0.8), (1, 0, 0.8), (0, -1, 0.8), (0, 1, 0.8), (-1, -1, 0.45), (1, -1, 0.45),
            (-2, 0, 0.5), (-3, 0, 0.32), (-4, 1, 0.22), (-2, 1, 0.36), (-3, 1, 0.26)]
    for dy, dx, a in core:                            # dy < 0 is up the tail
        r0, c0 = (cy + dy) * cell, (cx + dx) * cell
        out[r0:r0 + cell, c0:c0 + cell] = np.maximum(out[r0:r0 + cell, c0:c0 + cell], white * a)
    edge = np.minimum(np.minimum(xx, n - xx), np.minimum(yy, n - yy)) / (n * 0.06)
    return np.clip(out * strength * np.clip(edge, 0.0, 1.0)[..., None], 0.0, 1.0)


def pixelled(seen, grid=64, levels=5):
    """The same picture on a coarse grid with few steps of brightness, the way the vanilla sun and
    moon are drawn."""
    k = seen.shape[0] // grid
    small = seen.reshape(grid, k, grid, k, 3).mean(axis=(1, 3))
    peak = small.max(axis=2, keepdims=True)
    step = np.clip(np.ceil(np.clip(peak, 0.0, 1.0) ** 0.6 * levels - 0.35) / levels, 0.0, 1.0) ** (1.0 / 0.6)
    small = np.where(peak > 1e-6, small / np.maximum(peak, 1e-6) * step, 0.0)
    return np.repeat(np.repeat(small, k, axis=0), k, axis=1)


def hot_core(n=128):
    """The last light on the horizon for the sun's square (33.4 degrees wide): a flat lens of gold
    with a wider mauve haze. Colours add onto the sunset fan."""
    deg = 33.4 / n
    yy, xx = np.meshgrid((np.arange(n) + 0.5), (np.arange(n) + 0.5), indexing="ij")
    x, y = (xx - n / 2) * deg, (n / 2 - yy) * deg
    lens = np.exp(-0.5 * ((x / 8.5) ** 2 + (y / np.where(y > 0, 2.6, 1.6)) ** 2))
    haze = np.exp(-0.5 * ((x / 12.0) ** 2 + (y / np.where(y > 0, 6.0, 2.5)) ** 2))
    out = hx("#5a4a16")[None, None, :] * lens[..., None] * 1.0 + hx("#3a1430")[None, None, :] * haze[..., None] * 0.7
    edge = np.minimum(np.minimum(xx, n - xx), np.minimum(yy, n - yy)) / (n * 0.10)
    return np.clip(out * np.clip(edge, 0.0, 1.0)[..., None], 0.0, 1.0)


def moon_png(seen):
    """Moon quad: the picture file is upside down against what the player sees in the west."""
    return seen[::-1].copy()


def sun_png(seen):
    """Sun quad: the picture file is mirrored left to right against what the player sees in the west."""
    return seen[:, ::-1].copy()


# ---------------------------------------------------------------------------------------------
# the vanilla cloud layer: which cells are filled

def periodic_noise(n, sx, sz, seed):
    rng = np.random.default_rng(seed)
    white = rng.standard_normal((n, n))
    fx, fz = np.fft.fftfreq(n)[:, None], np.fft.fftfreq(n)[None, :]
    f = np.fft.ifft2(np.fft.fft2(white) * np.exp(-2.0 * math.pi ** 2 * ((fx * sx) ** 2 + (fz * sz) ** 2))).real
    return (f - f.mean()) / f.std()


def cloud_cells(n=256, cover=0.88, seed=11):
    """Square, tiling map of filled cloud cells: pads of cloud parted by thin creases, a few lakes.
    Axis 0 is x (east), axis 1 is z (south); the creases run mostly north-south."""
    g1, g2 = periodic_noise(n, 5.0, 11.0, seed), periodic_noise(n, 7.0, 15.0, seed + 1)
    keep = periodic_noise(n, 14.0, 14.0, seed + 2) > -0.35
    lakes = periodic_noise(n, 6.0, 9.0, seed + 3) > 2.05
    lo, hi = 0.0, 0.6
    for _ in range(30):
        w = (lo + hi) / 2.0
        gap = (((np.abs(g1) < w) | (np.abs(g2) < w * 0.8)) & keep) | lakes
        if 1.0 - gap.mean() > cover:
            lo = w
        else:
            hi = w
    return ~gap


def vanilla_cells():
    with zipfile.ZipFile(JAR) as z:
        im = Image.open(io.BytesIO(z.read("assets/minecraft/textures/environment/clouds.png"))).convert("RGBA")
    return np.asarray(im)[..., 3].T >= 10


class NearField:
    """The block-built cloud field around the site, as far as the sketch needs it: where there is
    cloud, where a billow stands on the sheet, where the sheet is hollow (darker tone)."""

    def __init__(self, seed=5, n=256):
        self.n = n
        i = (np.arange(n) + 0.5) * NEAR_CELL
        x = (i[:, None] + n * NEAR_CELL / 2.0) % (n * NEAR_CELL) - n * NEAR_CELL / 2.0      # world x of the cell
        z = (i[None, :] + n * NEAR_CELL / 2.0) % (n * NEAR_CELL) - n * NEAR_CELL / 2.0
        r = np.hypot(x - SITE_CENTRE[0], z - SITE_CENTRE[1])
        thin = np.clip((r - NEAR_SOLID) / (NEAR_END - NEAR_SOLID), 0.0, 1.0)
        self.there = (thin <= 0.0) | ((thin < 1.0) & (periodic_noise(n, 2.2, 2.2, seed) > thin * 5.0 - 2.5))
        self.billow = periodic_noise(n, 2.6, 3.4, seed + 1) > 0.25
        self.hollow = periodic_noise(n, 3.0, 4.0, seed + 2) < -0.7
        light = G.lightmap(attrs(LOOKS["blue"]), 0.5)[15, 0]
        self.albedo = [np.clip(hx(c) / light, 0.0, 1.0) for c in NEAR_SHOWN]

    def cell(self, p):
        return (np.floor(p[:, 0] / NEAR_CELL).astype(int) % self.n, np.floor(p[:, 2] / NEAR_CELL).astype(int) % self.n)

    def trace(self, o, d):
        """Distance, albedo and face shade where rays from above meet the field (inf where they pass)."""
        down = d[:, 1] < -1e-5
        div = np.where(down, d[:, 1], -1.0)
        ta = np.where(down, (NEAR_TOP + NEAR_BILLOW - o[1]) / div, np.inf)
        tb = np.where(down, (NEAR_TOP - o[1]) / div, np.inf)
        pa, pb = o + d * np.where(down, ta, 0.0)[:, None], o + d * np.where(down, tb, 0.0)[:, None]
        ia, ja = self.cell(pa)
        ib, jb = self.cell(pb)
        # the maps repeat; only the copy around the site is the field
        ina = np.hypot(pa[:, 0] - SITE_CENTRE[0], pa[:, 2] - SITE_CENTRE[1]) < NEAR_END + NEAR_CELL
        inb = np.hypot(pb[:, 0] - SITE_CENTRE[0], pb[:, 2] - SITE_CENTRE[1]) < NEAR_END + NEAR_CELL
        top = down & ina & self.there[ia, ja] & self.billow[ia, ja]
        side = down & ~top & inb & self.there[ib, jb] & self.billow[ib, jb]
        sheet = down & ~top & ~side & inb & self.there[ib, jb]
        t = np.where(top, ta, np.where(side | sheet, tb, np.inf))
        alb = np.zeros((len(d), 3))
        alb[top | side] = self.albedo[0]
        alb[sheet] = self.albedo[1]
        alb[sheet & self.hollow[ib, jb]] = self.albedo[2]
        shade = np.where(side, np.where(ib != ia, 0.6, 0.8), 1.0)
        return t, alb, shade


# ---------------------------------------------------------------------------------------------
# the sky as the game draws it

class Sky:
    def __init__(self, v, sprites=True, fan=True):
        self.v = v
        self.sky, self.fog = derive(v)
        self.glow = hx(v["glow"])
        self.alpha = v["glow_alpha"] if fan else 0.0
        self.end = v["sky_fog_end"]
        self.mix = mix_share(self.end)
        self.sun = sun_png(hot_core()) if sprites else None
        self.moon = moon_png(comet(strength=v["comet"])) if sprites else None
        rng = np.random.default_rng(10842)
        s = rng.standard_normal((1500, 3))
        self.star_dirs = s / np.linalg.norm(s, axis=1, keepdims=True)
        self.star_size = rng.uniform(0.15, 0.25, 1500) / 100.0

    def fog_colour(self, forward):
        """FogColor for a camera looking along `forward`: tinted by the sunset colour when it looks
        west, then drawn towards the sky colour."""
        k = max(0.0, -float(forward[0])) * self.alpha
        f = self.fog + (self.glow - self.fog) * k
        return f + (self.sky - f) * self.mix

    def fan(self, d):
        """Opacity of the sunrise/sunset fan along each ray (N, 3)."""
        a = self.alpha
        op = np.zeros(len(d))
        if a <= 0.001:
            return op
        A = np.array([-100.0, 0.0, 0.0])
        t = np.arange(17) * (2.0 * math.pi / 16.0)
        ring = np.stack([-120.0 * np.cos(t), 40.0 * a * np.cos(t), 120.0 * np.sin(t)], axis=1)
        for i in range(16):
            e1, e2 = ring[i] - A, ring[i + 1] - A
            h = np.cross(d, e2)
            det = h @ e1
            ok = np.abs(det) > 1e-9
            inv = np.where(ok, 1.0 / np.where(ok, det, 1.0), 0.0)
            sv = -A
            u = (h @ sv) * inv
            q = np.cross(sv, e1)
            w = (d @ q) * inv
            tt = (q @ e2) * inv
            hit = ok & (u >= 0.0) & (w >= 0.0) & (u + w <= 1.0) & (tt > 0.0)
            op = np.where(hit, 1.0 - (1.0 - op) * (1.0 - a * (1.0 - u - w)), op)
        return op

    def body(self, d, angle, half, png, flip):
        r = math.radians(angle)
        b = np.array([-math.sin(r), math.cos(r), 0.0])
        vv = np.array([-math.cos(r), -math.sin(r), 0.0])
        along = d @ b
        ok = along > 1e-6
        U = np.where(ok, d[:, 2] / np.where(ok, along, 1.0) / half, 9.0)
        V = np.where(ok, (d @ vv) / np.where(ok, along, 1.0) / half, 9.0)
        ok &= (np.abs(U) < 1.0) & (np.abs(V) < 1.0)
        n = png.shape[0]
        fu, fv = U * 0.5 + 0.5, V * 0.5 + 0.5
        if flip:
            fu, fv = 1.0 - fu, 1.0 - fv
        col = np.clip((fu * n).astype(int), 0, n - 1)
        row = np.clip((fv * n).astype(int), 0, n - 1)
        return np.where(ok[:, None], png[row, col], 0.0)

    def colour(self, d, forward):
        """Sky colour along unit rays d (N, 3) for a camera looking along forward, and the fog
        colour of that camera. Stars are added afterwards (add_stars)."""
        fogc = self.fog_colour(forward)
        dy = d[:, 1]
        reach = 16.0 * np.hypot(d[:, 0], d[:, 2]) / np.maximum(dy, 1e-6)
        f = np.where((dy > 1e-4) & (reach < 512.0), np.minimum(1.0, (16.0 + 496.25 * reach / 512.0) / self.end), 1.0)
        c = self.sky[None, :] + (fogc - self.sky)[None, :] * f[:, None]
        op = self.fan(d)
        c = c + (self.glow[None, :] - c) * op[:, None]
        if self.sun is not None:
            c = c + self.body(d, self.v["sun_angle"], 0.30, self.sun, False)
            c = c + self.body(d, self.v["moon_angle"], 0.20, self.moon, True)
        return np.clip(c, 0.0, 1.0), fogc


def add_stars(img, sky, cam, mask):
    """Splat the stars into a picture (H, W, 3) where mask says the sky shows."""
    H, W = mask.shape
    pos, f, r, u, tanv = cam
    aspect = W / H
    for sd, size in zip(sky.star_dirs, sky.star_size):
        z = sd @ f
        if z <= 0.05:
            continue
        px = (sd @ r) / z / (tanv * aspect)
        py = (sd @ u) / z / tanv
        if abs(px) >= 1 or abs(py) >= 1:
            continue
        i, j = int((px * 0.5 + 0.5) * W), int((0.5 - py * 0.5) * H)
        rad = max(1, int(round(size / z / tanv * H * 0.5)))
        j0, j1, i0, i1 = max(0, j - rad + 1), min(H, j + rad), max(0, i - rad + 1), min(W, i + rad)
        if j0 >= j1 or i0 >= i1 or not mask[j0:j1, i0:i1].all():
            continue
        img[j0:j1, i0:i1] = np.clip(img[j0:j1, i0:i1] + sky.v["stars"], 0.0, 1.0)


# ---------------------------------------------------------------------------------------------
# the site as plain masses (ART-PLAN section 4 with the numbers of reviews/R1-first-designs.md),
# x east, y up, z south, upper platform floor = 0

STONE, PAVE, SLATE, TUFF, VERDI, ROCK = hx("#c8c1b0"), hx("#b7b0a1"), hx("#3b3c44"), hx("#6d6f66"), hx("#4fa487"), hx("#55565c")
WINDOW, WINDOW_DIM = hx("#ffc65a"), hx("#f09a2e")
DARK_BAYS = {2, 6, 12, 15}          # bays whose windows stay dark in the sketch (bay 8 is the entrance)
BOXES = [
    # x0, y0, z0, x1, y1, z1, colour, kind
    (-30, -60, -46, 45, 0, 46, PAVE, "ground"),          # upper platform and the mountain under it
    (45, -60, -46, 88, -9, 46, TUFF, "ground"),          # lower platform
    (0, 0, -34, 16, 17, 34, STONE, "main"),              # main building up to the parapet
    (16, 0, -6, 18, 18, 6, STONE, "entrance"),           # the middle three bays stand 2 forward
    (16, 0, -34, 17, 17, -26, STONE, "main"),            # north end pavilion, 1 forward: the foot of the tower
    (16, 0, 26, 17, 17, 34, STONE, "main"),              # south end pavilion, 1 forward
    (1, 17, -25, 15, 19, 25, SLATE, "roof"),
    (10, 17, -33, 17, 31, -26, STONE, "tower"),          # time tower, its front flush with the pavilion
    (11, 31, -32, 16, 35, -27, VERDI, "roof"), (12, 35, -31, 15, 39, -28, VERDI, "roof"), (13, 39, -30, 14, 41, -29, VERDI, "roof"),
    (13.3, 41, -29.7, 13.7, 52, -29.3, SLATE, "roof"),   # time-ball mast
    (8, 17, 26, 17, 20.5, 35, STONE, "main"),            # drum of the small dome on the south pavilion
    (56, -9, -40, 72, -3, -26, TUFF, "station"),         # cable-car station
    (62, -9, 20, 84, 1, 42, TUFF, "power"),              # powerhouse
    (79, 1, 37, 82, 21, 40, hx("#5e4636"), "power"),     # chimney
]
BOXES += [(45 + i, -60, -8, 46 + i, -1 - i, 8, PAVE, "ground") for i in range(9)]     # grand stair
DOMES = [((4.0, 24.0, 0.0), 13.0, "big"), ((12.5, 20.5, 30.5), 4.5, "small")]
DRUM = ((4.0, 0.0), 13.0, 0.0, 24.0)       # centre, radius, y0, y1 of the rotunda under the dome

# invisible lights of the sketch: x, y, z, level
LIGHTS = []
LIGHTS += [(18.5, 2, 0, 14)]                                                      # the open door: light of the hall
LIGHTS += [(19.5, 6, z, 13) for z in (-2, 0, 2)]                                  # bulbs under the entrance canopy
LIGHTS += [(18.5, 3, z, 12) for z in (-3, 3)]                                     # wall lamps by the door
LIGHTS += [(x, 5, z, 14) for x in (24, 42) for z in (-27, -13, 13, 27)]           # street lamps of the forecourt
LIGHTS += [(46 + 4 * i, -1 - 4 * i + 4, z, 14) for i in range(3) for z in (-9, 9)]  # lamps down the grand stair
LIGHTS += [(x, -5, z, 13) for x in (58, 70) for z in (-24, -8, 8)]                # lower platform
LIGHTS += [(18.5, 1, 4 * k - 32, 8) for k in range(5, 12) if k not in (7, 8, 9)]  # wash on the bays next to the middle
BAYS = [(k, 4 * k - 32) for k in range(17)]                                       # bay number (from 0), z of its middle


def front(z):
    """x of the east face of the wall at z (middle three bays 2 forward, end pavilions 1 forward)."""
    return 18.0 if abs(z) < 6 else 17.0 if abs(z) > 26 else 16.0


LIGHTS += [(front(z) + 0.5, 11, z, 9) for k, z in BAYS if k not in DARK_BAYS and abs(z) > 2]
LIGHTS += [(front(z) + 0.5, 4, z, 8) for k, z in BAYS if k not in DARK_BAYS and abs(z) > 2]
LIGHTS = np.array(LIGHTS, dtype=float)
LAMPS = [l for l in LIGHTS if l[3] >= 13]


def block_level(p):
    """Block light level at points (N, 3): the brightest of the lights after one level per block."""
    best = np.zeros(len(p))
    for x, y, z, lv in LIGHTS:
        best = np.maximum(best, lv - (np.abs(p[:, 0] - x) + np.abs(p[:, 1] - y) + np.abs(p[:, 2] - z)))
    return np.clip(best, 0.0, 15.0)


def lit(table, level):
    """Row sky = 15 of the light table at fractional block levels."""
    lo = np.clip(np.floor(level).astype(int), 0, 15)
    hi = np.clip(lo + 1, 0, 15)
    w = (level - lo)[:, None]
    return table[15, lo] * (1.0 - w) + table[15, hi] * w


def camera(pos, target, fov=FOV):
    pos, target = np.array(pos, float), np.array(target, float)
    f = target - pos
    f /= np.linalg.norm(f)
    r = np.cross(f, (0.0, 1.0, 0.0))
    r /= np.linalg.norm(r)
    u = np.cross(r, f)
    return pos, f, r, u, math.tan(math.radians(fov) / 2.0)


def rays(cam, W, H):
    pos, f, r, u, tanv = cam
    px = ((np.arange(W) + 0.5) / W * 2.0 - 1.0) * tanv * W / H
    py = (1.0 - (np.arange(H) + 0.5) / H * 2.0) * tanv
    d = f[None, None, :] + px[None, :, None] * r[None, None, :] + py[:, None, None] * u[None, None, :]
    d /= np.linalg.norm(d, axis=2, keepdims=True)
    return d.reshape(-1, 3)


def trace_site(o, d):
    """Nearest hit of rays from o with the masses: distance, albedo, shade of the face, normal, kind."""
    n = len(d)
    best = np.full(n, np.inf)
    alb = np.zeros((n, 3))
    shade = np.ones(n)
    normal = np.zeros((n, 3))
    kind = np.full(n, -1)
    inv = 1.0 / np.where(np.abs(d) < 1e-9, 1e-9, d)
    kinds = sorted({b[7] for b in BOXES}) + ["dome", "drum"]
    for x0, y0, z0, x1, y1, z1, col, kd in BOXES:
        lo, hi = (np.array([x0, y0, z0]) - o) * inv, (np.array([x1, y1, z1]) - o) * inv
        tn, tf = np.minimum(lo, hi), np.maximum(lo, hi)
        t0, t1 = tn.max(axis=1), tf.min(axis=1)
        hit = (t1 >= t0) & (t0 > 1e-3) & (t0 < best)
        if not hit.any():
            continue
        axis = tn.argmax(axis=1)
        best = np.where(hit, t0, best)
        alb[hit] = col
        kind[hit] = kinds.index(kd)
        nn = np.zeros((n, 3))
        nn[np.arange(n), axis] = -np.sign(d[np.arange(n), axis])
        normal[hit] = nn[hit]
    for (cx, cy, cz), rad, _name in DOMES:
        oc = o - np.array([cx, cy, cz])
        b = d @ oc
        disc = b * b - (oc @ oc - rad * rad)
        t = -b - np.sqrt(np.maximum(disc, 0.0))
        p = o + d * t[:, None]
        hit = (disc > 0) & (t > 1e-3) & (t < best) & (p[:, 1] >= cy)
        best = np.where(hit, t, best)
        alb[hit] = VERDI
        kind[hit] = kinds.index("dome")
        normal[hit] = ((p - np.array([cx, cy, cz])) / rad)[hit]
    (cx, cz), rad, y0, y1 = DRUM
    a = d[:, 0] ** 2 + d[:, 2] ** 2
    bb = d[:, 0] * (o[0] - cx) + d[:, 2] * (o[2] - cz)
    cc = (o[0] - cx) ** 2 + (o[2] - cz) ** 2 - rad * rad
    disc = bb * bb - a * cc
    t = (-bb - np.sqrt(np.maximum(disc, 0.0))) / np.maximum(a, 1e-9)
    p = o + d * t[:, None]
    hit = (disc > 0) & (t > 1e-3) & (t < best) & (p[:, 1] >= y0) & (p[:, 1] <= y1)
    best = np.where(hit, t, best)
    alb[hit] = STONE
    kind[hit] = kinds.index("drum")
    nn = np.stack([(p[:, 0] - cx) / rad, np.zeros(n), (p[:, 2] - cz) / rad], axis=1)
    normal[hit] = nn[hit]
    # the game shades faces by the way they point: top 1.0, north/south 0.8, east/west 0.6, bottom 0.5
    w = normal ** 2
    shade = w[:, 0] * 0.6 + w[:, 2] * 0.8 + w[:, 1] * np.where(normal[:, 1] > 0, 1.0, 0.5)
    return best, alb, shade, normal, kind, kinds


def facade_glow(p, normal, kind, kinds):
    """Lit windows on the east faces, the clock face, the slit of the dome: (mask, colour)."""
    n = len(p)
    on = np.zeros(n, dtype=bool)
    col = np.zeros((n, 3))
    east = normal[:, 0] > 0.9
    y, z = p[:, 1], p[:, 2]
    wall = east & ((kind == kinds.index("main")) | (kind == kinds.index("entrance")))
    for k, zc in BAYS:
        if k in DARK_BAYS:
            continue
        dz = np.abs(z - zc)
        big = wall & (y >= 8.0) & (y <= 14.0) & (dz <= 1.5 - 0.9 * np.clip(y - 13.0, 0.0, 1.0) ** 2) & (abs(zc) > 2)
        small = wall & (dz <= 1.5) & (y >= 3.0) & (y <= 5.0) & (abs(zc) > 2)
        fan = wall & (abs(zc) <= 2) & (dz <= 1.5) & (y >= 5.2) & (y <= 6.8)
        m = big | small | fan
        bars = ((np.abs((z * 2.0) % 1.0 - 0.5) > 0.42) | (np.abs((y * 2.0) % 1.0 - 0.5) > 0.42))
        col[m] = np.where(bars[m][:, None], WINDOW * 0.55, WINDOW if k % 3 else WINDOW_DIM)
        on |= m
    door = wall & (np.abs(z) <= 1.5) & (y >= 0.0) & (y <= 5.0)          # the doors stand open on the lit hall
    col[door] = hx("#ffe9a6") * np.clip(0.75 + 0.05 * y[door], 0.0, 1.0)[:, None]
    on |= door
    tower = east & (kind == kinds.index("tower")) & (np.hypot(z + 29.5, y - 26.0) <= 2.2)
    col[tower] = hx("#ffe9a6")
    on |= tower
    slit = (kind == kinds.index("dome")) & (np.abs(z) < 2.5) & (p[:, 0] < 6.5) & (p[:, 1] > 24.5)
    col[slit] = hx("#c96a1c")
    on |= slit
    return on, col


def ridge_elevation(az):
    """Far ridges as an elevation over the horizon (degrees) by azimuth (degrees north of west)."""
    def peak(c, w, h):
        return h * np.clip(1.0 - np.abs(az - c) / w, 0.0, 1.0)
    e = np.maximum.reduce([peak(-40.0, 18.0, 5.5), peak(-27.0, 9.0, 7.5), peak(-52.0, 14.0, 4.0),
                           peak(31.0, 12.0, 8.5), peak(46.0, 16.0, 5.0), peak(22.0, 7.0, 4.5),
                           peak(118.0, 20.0, 5.0), peak(-125.0, 24.0, 6.0)])
    jag = 0.5 * np.sin(az * 0.9) + 0.35 * np.sin(az * 2.3 + 1.0)
    return np.where(e > 0.6, e + jag, 0.0)


SIZE = [720, 405]            # size of one sketch picture; --size changes it


def picture(v, pos, target, size=None, clouds="fancy", cells=None, ridges=True, gamma=0.5, fan=True,
            sprites=True, site=True, near=None):
    W, H = size or SIZE
    cam = camera(pos, target)
    o, fwd = cam[0], cam[1]
    d = rays(cam, W, H)
    sky = Sky(v, sprites=sprites, fan=fan)
    c, fogc = sky.colour(d, fwd)
    sky_mask = np.ones(len(d), dtype=bool)
    if ridges:
        az = np.degrees(np.arctan2(-d[:, 2], -d[:, 0]))          # degrees north of west
        el = np.degrees(np.arcsin(np.clip(d[:, 1], -1, 1)))
        m = (el < ridge_elevation(az)) & (el > -3.0)
        c[m] = fogc
        sky_mask &= ~m
    table = G.lightmap(attrs(v), gamma)
    t_site = np.full(len(d), np.inf)
    if site:
        t_site, alb, shade, normal, kind, kinds = trace_site(o, d)
        hit = np.isfinite(t_site)
        p = o + d * np.where(hit, t_site, 0.0)[:, None]
        level = block_level(p + normal * 0.5)
        col = alb * lit(table, level) * shade[:, None]
        on, glow = facade_glow(p, normal, kind, kinds)
        col = np.where(on[:, None], glow, col)
        fogv = np.clip((t_site - FOG_START) / (FOG_END - FOG_START), 0.0, 1.0)
        col = col + (fogc - col) * fogv[:, None]
        c = np.where(hit[:, None], col, c)
        sky_mask &= ~hit
    t_near = np.full(len(d), np.inf)
    if near is not None and o[1] > NEAR_TOP + NEAR_BILLOW:
        t_near, alb_n, shade_n = near.trace(o, d)
        t_near = np.where(t_near < t_site, t_near, np.inf)
        hit = np.isfinite(t_near)
        col = alb_n * table[15, 0][None, :] * shade_n[:, None]
        fogv = np.clip((t_near - FOG_START) / (FOG_END - FOG_START), 0.0, 1.0)
        col = col + (fogc - col) * fogv[:, None]
        c = np.where(hit[:, None], col, c)
        sky_mask &= ~hit
    if clouds != "off" and o[1] > CLOUD_TOP:
        cells = cloud_cells() if cells is None else cells
        n = cells.shape[0]
        cloud = hx(v["cloud"])
        down = d[:, 1] < -1e-5
        plane = CLOUD_TOP if clouds == "fancy" else CLOUD_TOP - CLOUD_THICK
        tc = np.where(down, (plane - o[1]) / np.where(down, d[:, 1], -1.0), np.inf)
        pc = o + d * np.where(down, tc, 0.0)[:, None]
        ix = np.floor(pc[:, 0] / CLOUD_CELL).astype(int) % n
        iz = np.floor(pc[:, 2] / CLOUD_CELL).astype(int) % n
        filled = cells[ix, iz] & down
        face = np.ones(len(d))
        if clouds == "fancy":       # a gap: the ray may still meet the side of the next cell before it leaves below
            tb = np.where(down, (CLOUD_TOP - CLOUD_THICK - o[1]) / np.where(down, d[:, 1], -1.0), np.inf)
            pb = o + d * np.where(down, tb, 0.0)[:, None]
            jx = np.floor(pb[:, 0] / CLOUD_CELL).astype(int) % n
            jz = np.floor(pb[:, 2] / CLOUD_CELL).astype(int) % n
            side = down & ~filled & cells[jx, jz]
            face = np.where(side, np.where(jx != ix, 0.9, 0.8), 1.0)
            filled |= side
        a = v["cloud_alpha"] * np.clip(1.0 - tc / CLOUD_FOG_END, 0.0, 1.0)
        show = filled & (tc < t_site) & (tc < t_near)
        c = np.where(show[:, None], c + (cloud[None, :] * face[:, None] - c) * a[:, None], c)
        sky_mask &= ~show
    img = c.reshape(H, W, 3)
    add_stars(img, sky, cam, sky_mask.reshape(H, W))
    # lamp heads: a bright dot with a faint halo, hidden when something stands in front
    if site:
        depth = t_site.reshape(H, W)
        pos_, f, r, u, tanv = cam
        for x, y, z, lv in LAMPS:
            q = np.array([x, y, z]) - pos_
            zc = q @ f
            if zc <= 0.5:
                continue
            px, py = (q @ r) / zc / (tanv * W / H), (q @ u) / zc / tanv
            if abs(px) >= 1 or abs(py) >= 1:
                continue
            i, j = int((px * 0.5 + 0.5) * W), int((0.5 - py * 0.5) * H)
            if depth[j, i] < np.linalg.norm(q) - 0.6:
                continue
            rad = 0.35 / zc / tanv * H * 0.5
            fogv = min(1.0, max(0.0, (np.linalg.norm(q) - FOG_START) / (FOG_END - FOG_START)))
            R = int(rad * 7) + 2
            j0, j1, i0, i1 = max(0, j - R), min(H, j + R + 1), max(0, i - R), min(W, i + R + 1)
            jj, ii = np.meshgrid(np.arange(j0, j1), np.arange(i0, i1), indexing="ij")
            dist = np.hypot(jj - j, ii - i)
            halo = 0.30 * np.exp(-0.5 * (dist / (rad * 2.6)) ** 2) * (1.0 - fogv)
            img[j0:j1, i0:i1] = np.clip(img[j0:j1, i0:i1] + hx("#ffb45e")[None, None, :] * halo[..., None], 0, 1)
            dot = dist <= max(rad, 0.8)
            img[j0:j1, i0:i1][dot] = hx("#fff8dc") * (1.0 - fogv) + fogc * fogv
    return (np.clip(img, 0, 1) * 255.0 + 0.5).astype(np.uint8)


# ---------------------------------------------------------------------------------------------
# camera positions of the sketches (eye height 1.62 above the floor)

VIEWS = {
    "V2": dict(name="V2 前庭正轴（大台阶口）", pos=(46.0, 1.62, 0.0), target=(4.0, 22.0, 0.0)),
    "V1a": dict(name="V1 到站 · 站在轴线上", pos=(70.0, -7.38, 0.0), target=(4.0, 20.0, 0.0)),
    "V1b": dict(name="V1 到站 · 站在北半（z=-22）", pos=(70.0, -7.38, -22.0), target=(4.0, 20.0, -6.0)),
    "V11": dict(name="V11 南观景台回望", pos=(30.0, -2.4, 62.0), target=(4.0, 16.0, 4.0)),
    "west": dict(name="落日平台朝西", pos=(-27.0, 1.62, 0.0), target=(-127.0, 12.0, 0.0)),
    "east": dict(name="大台阶口回头朝东", pos=(44.0, 1.62, 0.0), target=(144.0, -6.0, 10.0)),
}


def titled(img, text, sub=None):
    im = Image.fromarray(img)
    dr = ImageDraw.Draw(im, "RGBA")
    dr.rectangle((0, 0, im.width, 30), fill=(10, 12, 24, 170))
    label(dr, (10, 4), text, 18)
    if sub:
        w = dr.textlength(sub, font=font(14))
        label(dr, (im.width - w - 10, 7), sub, 14, DIM)
    return im


def sheet(tiles, cols, title, note, pad=14):
    w, h = tiles[0].size
    rows = (len(tiles) + cols - 1) // cols
    W, H = cols * w + (cols + 1) * pad, rows * h + (rows + 1) * pad + 74
    im = Image.new("RGB", (W, H), BG)
    dr = ImageDraw.Draw(im)
    label(dr, (pad, 12), title, 26)
    label(dr, (pad, 46), note, 15, DIM)
    for k, t in enumerate(tiles):
        im.paste(t, (pad + (k % cols) * (w + pad), 74 + pad + (k // cols) * (h + pad)))
    return im


def save(im, out, name):
    os.makedirs(out, exist_ok=True)
    path = os.path.join(out, name)
    im.convert("RGB").save(path, quality=90, subsampling=0)
    print(path, im.size)


NOTE = "按 26.3 客户端的公式算的示意图，不是真机图。建筑只是按总方案尺寸摆的体块，机位是暂定的。"


def fig_looks(out):
    cells, near = cloud_cells(), NearField()
    tiles = []
    for key in ("glow", "blue", "deep"):
        v = LOOKS[key]
        for view in ("V2", "west"):
            vw = VIEWS[view]
            tiles.append(titled(picture(v, vw["pos"], vw["target"], cells=cells, near=near), v["title"], vw["name"]))
    save(sheet(tiles, 2, "三个光线版本（同一条时间线上的三个时刻）", NOTE), out, "sky-looks.jpg")


def fig_views(out):
    cells, near = cloud_cells(), NearField()
    v = LOOKS["blue"]
    tiles = [titled(picture(v, VIEWS[k]["pos"], VIEWS[k]["target"], cells=cells, near=near), VIEWS[k]["name"], "A 蓝调时刻")
             for k in ("V1a", "V1b", "V11", "east")]
    save(sheet(tiles, 2, "彗星和余晖在几个机位里落在哪（A 蓝调时刻）", NOTE), out, "sky-views.jpg")


def fig_clouds(out):
    new, old, near = cloud_cells(), vanilla_cells(), NearField()
    v = LOOKS["blue"]
    pos, target = (-29.5, 1.62, 0.0), (-129.5, -20.0, 34.0)

    def shot(text, **kw):
        return titled(picture(v, pos, target, ridges=False, **kw), text)
    tiles = [
        shot("① 只有原版云层，原版云图（覆盖 %.0f%%），只降高度、改颜色" % (old.mean() * 100), cells=old),
        shot("② 只有原版云层，重画的云图（覆盖 %.0f%%）" % (new.mean() * 100), cells=new),
        shot("③ 本稿做法：近处方块云 + 远处原版云层（高品质云）", cells=new, near=near),
        shot("④ 本稿做法，玩家选了“快速”云", cells=new, near=near, clouds="fast"),
        shot("⑤ 本稿做法，玩家关了云：近处的方块云还在", near=near, clouds="off"),
        shot("⑥ 没有方块云，又关了云：只剩雾和地平线下的暖色", clouds="off"),
    ]
    im = sheet(tiles, 2, "云海：从落日平台边上往西南下方看（A 蓝调时刻）", NOTE)
    # the two cell maps, top down
    k = 2
    maps = Image.new("RGB", (2 * 256 * k + 3 * 14, 256 * k + 2 * 14 + 30), BG)
    dr = ImageDraw.Draw(maps)
    for i, (cells, name) in enumerate(((old, "原版 clouds.png：%.1f%%" % (old.mean() * 100)),
                                       (new, "重画：%.1f%%，南北向的细缝加少量云洞" % (new.mean() * 100)))):
        a = np.where(cells.T[..., None], hx(v["cloud"]) * 255, hx("#1d2246") * 255).astype(np.uint8)
        maps.paste(Image.fromarray(a).resize((256 * k, 256 * k), Image.NEAREST), (14 + i * (256 * k + 14), 14 + 30))
        label(dr, (14 + i * (256 * k + 14), 12), name + "（俯视，上北；一格 = 12×12 个方块）", 16)
    full = Image.new("RGB", (im.width, im.height + maps.height + 10), BG)
    full.paste(im, (0, 0))
    full.paste(maps, ((im.width - maps.width) // 2, im.height))
    save(full, out, "sky-clouds.jpg")


def fig_sprites(out):
    k, pad = 2, 16
    soft = comet()
    comets = [("甲 柔光长尾：细网格画光晕，彗核画在粗网格上", soft),
              ("乙 硬像素：64 格、五级亮度，和原版日月一个画法", pixelled(soft)),
              ("丙 宽扇尾：尾巴短而宽，轮廓更像一把扇子", comet(lean=20.0, tail=12.0, spread=4.6))]
    core = hot_core()
    W = 3 * 256 * k + 4 * pad + 2 * 128 * k + pad
    im = Image.new("RGB", (W, 256 * k + 150), BG)
    dr = ImageDraw.Draw(im)
    label(dr, (pad, 10), "天上的两张贴图（按玩家在西边天上看到的方向画；底色是该处的天色）", 24)
    back = hx("#151a3c")
    for i, (name, c) in enumerate(comets):
        a = np.clip(back[None, None, :] + c, 0, 1)
        x0 = pad + i * (256 * k + pad)
        im.paste(Image.fromarray((a * 255).astype(np.uint8)).resize((256 * k, 256 * k), Image.NEAREST), (x0, 60))
        label(dr, (x0, 60 + 256 * k + 6), "彗星 " + name, 15)
    x0 = pad + 3 * (256 * k + pad)
    a = np.clip(hx("#8a5357")[None, None, :] + core, 0, 1)
    im.paste(Image.fromarray((a * 255).astype(np.uint8)).resize((256 * k, 256 * k), Image.BILINEAR), (x0, 60))
    label(dr, (x0, 60 + 256 * k + 6), "地平线上最后一点金色（太阳位）：128×128，宽 33.4 度", 15)
    label(dr, (pad, 60 + 256 * k + 34), "彗星放在月亮位：贴图 256×256，在天上宽 22.6 度。彗头在贴图中心下方 7 度，尘尾向北弯，蓝色离子尾笔直。三个草样是彗星卡要比选的三种想法。", 15, DIM)
    label(dr, (pad, 60 + 256 * k + 58), "游戏把这两张图加到天色上（黑色等于不画）。月亮位的图文件要上下颠倒着存，太阳位的要左右镜像着存（按代码推的，首次真机用箭头图核对）。", 15, DIM)
    save(im, out, "sky-sprites.jpg")


def fig_pano(out):
    """The whole sky unrolled: azimuth across (west in the middle), elevation up."""
    v = LOOKS["blue"]
    W, H = 1440, 520
    az = (np.arange(W) + 0.5) / W * 360.0 - 180.0                 # degrees north of west
    el = 90.0 - (np.arange(H) + 0.5) / H * 120.0                  # +90 .. -30
    sky = Sky(v)
    img = np.zeros((H, W, 3))
    for i in range(W):                                            # each column: the camera turned that way
        a = math.radians(az[i])
        fwd = np.array([-math.cos(a), 0.0, -math.sin(a)])
        e = np.radians(el)
        d = np.stack([-np.cos(e) * math.cos(a), np.sin(e), -np.cos(e) * math.sin(a)], axis=1)
        img[:, i], _ = sky.colour(d, fwd)
    im = Image.fromarray((img * 255).astype(np.uint8))
    dr = ImageDraw.Draw(im, "RGBA")
    for e in (60, 30, 0):
        y = (90 - e) / 120.0 * H
        dr.line((0, y, W, y), fill=(255, 255, 255, 50))
        label(dr, (6, y - 20), "仰角 %d°" % e, 14, DIM)
    for a, name in ((-180, "东"), (-90, "南"), (0, "西"), (90, "北")):
        x = (a + 180) / 360.0 * W
        dr.line((x, 0, x, H), fill=(255, 255, 255, 40))
        label(dr, (x + 6, H - 24), name, 16)
    label(dr, (W - 24, H - 24), "东", 16)
    canvas = Image.new("RGB", (W + 28, H + 88), BG)
    cd = ImageDraw.Draw(canvas)
    label(cd, (14, 12), "整片天空展开图（A 蓝调时刻）：横向是方位，正中是正西；纵向是仰角", 24)
    label(cd, (14, 46), "每一列按“镜头正对这个方向”来算，所以朝西那一段的地平线和雾都偏暖，朝东是蓝紫。地平线以下是没有云和山时的底色。", 15, DIM)
    canvas.paste(im, (14, 74))
    save(canvas, out, "sky-pano.jpg")


TIERS = [("一级 13–14：入口、路灯、站台", 13, "#fff8dc"), ("二级 9–12：窗后、门边", 9, "#ffc65a"),
         ("三级 5–8：洗墙、走道、机器", 0, "#e08a3a")]


def tier_colour(level):
    return next(col for _name, lo, col in TIERS if level >= lo)


def ground_height(x, z):
    """Floor level of the sketch site at (x, z); nan where there is no floor."""
    h = np.full(x.shape, np.nan)
    h[(x >= 45) & (x < 88) & (np.abs(z) < 46)] = -9.0
    stair = (x >= 45) & (x < 54) & (np.abs(z) < 8)
    h[stair] = -1.0 - np.floor(x[stair] - 45.0)
    h[(x >= -30) & (x < 45) & (np.abs(z) < 46)] = 0.0
    return h


def plan_of_lights(v, s=8):
    """Top view of the site: the floors as sky and lamps light them, the invisible lights marked."""
    x0, x1, z0, z1 = -36, 94, -52, 52
    X, Z = np.meshgrid(np.arange(x0, x1) + 0.5, np.arange(z0, z1) + 0.5)     # rows z (north on top), columns x
    h = ground_height(X, Z)
    table = G.lightmap(attrs(v), 0.5)
    ok = ~np.isnan(h)
    img = np.empty(X.shape + (3,))
    img[:] = hx("#2a2f57")
    floor = np.where((X[ok] >= 45)[:, None], TUFF[None, :], PAVE[None, :])
    img[ok] = floor * lit(table, block_level(np.stack([X[ok], h[ok] + 0.5, Z[ok]], axis=1)))
    roof = table[15, 0]
    for bx0, _by0, bz0, bx1, _by1, bz1, col, kind in BOXES:
        if kind != "ground":
            c = SLATE if kind in ("main", "entrance") else col
            img[int(round(bz0 - z0)):int(round(bz1 - z0)), int(round(bx0 - x0)):int(round(bx1 - x0))] = c * roof * 0.9
    for (cx, _cy, cz), rad, _n in DOMES:
        img[np.hypot(X - cx, Z - cz) <= rad] = VERDI * roof
    im = Image.fromarray((np.clip(img, 0, 1) * 255).astype(np.uint8)).resize(((x1 - x0) * s, (z1 - z0) * s), Image.NEAREST)
    dr = ImageDraw.Draw(im)

    def at(x, z):
        return (x - x0) * s, (z - z0) * s
    for x, _y, z, lv in LIGHTS:
        px, pz = at(x, z)
        r = 6 if lv >= 13 else 4 if lv >= 9 else 3
        dr.ellipse((px - r, pz - r, px + r, pz + r), fill=tier_colour(lv), outline=(20, 20, 30))
    for (x, z), (tx, tz), text in (((24, -27), (27, -41), "路灯 14（灯头高 5）"), ((19.5, -2), (25, -6.5), "雨棚灯泡 13 ×3"), ((18.5, 0), (25, -1), "敞开的大门 14"),
                                   ((18.5, 3), (25, 5), "门边壁灯 12"), ((18.5, -12), (22, -19.5), "洗墙 8"),
                                   ((16.5, 20), (21, 18), "窗后 9–10"), ((50, 9), (56, 14), "台阶灯 14"),
                                   ((70, 8), (74, 3), "下平台灯 13")):
        dr.line(at(x, z) + at(tx, tz), fill=(232, 228, 216), width=1)
        label(dr, (at(tx, tz)[0] + 3, at(tx, tz)[1] - 9), text, 14)
    for text, (x, z) in (("主楼", (5, -17)), ("大穹顶", (1, -1)), ("报时塔", (10.2, -31)), ("前庭", (30, 30)), ("落日平台", (-27, -1)),
                         ("大台阶", (46, -16)), ("下平台", (60, -2)), ("缆车站", (59, -34)), ("发电房", (67, 30))):
        label(dr, at(x, z), text, 14, DIM)
    dr.line(at(-33, 46) + at(-23, 46), fill=INK, width=2)
    label(dr, (at(-33, 46)[0], at(-33, 46)[1] + 4), "10 格", 13)
    label(dr, at(-34, -51), "北 ↑", 15)
    return im


def section_of_lights(v, s=30):
    """Cut through one window bay of the east front: where the invisible lights sit, and the block
    light level in every cell (one level less per block, through air and glass, not through walls)."""
    u0, u1, y0, y1 = -6, 9, -1, 19               # u: columns, + is outside (east), 0 is the face of the wall
    W, H = u1 - u0, y1 - y0
    solid, glass = np.zeros((H, W), dtype=bool), np.zeros((H, W), dtype=bool)

    def cell(u, y):
        return y1 - 1 - y, u - u0
    for u in range(u0, u1):
        solid[cell(u, -1)] = True                                    # floors
    for y in range(0, 18):
        solid[cell(0, y)] = solid[cell(-1, y)] = True                # the wall, two deep
    for y in list(range(8, 14)) + [3, 4]:                            # windows: open at the face, glass one back
        solid[cell(0, y)] = solid[cell(-1, y)] = False
        glass[cell(-1, y)] = True
    solid[cell(1, 0)] = solid[cell(1, 1)] = True                     # plinth
    solid[cell(1, 15)] = solid[cell(2, 15)] = True                   # cornice
    for u in range(u0, -1):
        solid[cell(u, 6)] = solid[cell(u, 15)] = True                # floor of the main storey, roof
    sources = [(-2, 9, 10), (-2, 12, 10), (-2, 3, 9), (3, 1, 8)]
    level = np.zeros((H, W), dtype=int)
    for u, y, lv in sources:
        front = [cell(u, y)]
        seen = {front[0]: lv}
        while front:
            nxt = []
            for (r, c) in front:
                for dr_, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    q = (r + dr_, c + dc)
                    if 0 <= q[0] < H and 0 <= q[1] < W and not solid[q] and q not in seen and seen[(r, c)] > 1:
                        seen[q] = seen[(r, c)] - 1
                        nxt.append(q)
            front = nxt
        for q, lv_ in seen.items():
            level[q] = max(level[q], lv_)
    table = G.lightmap(attrs(v), 0.5)
    im = Image.new("RGB", (W * s + 150, H * s + 8), BG)
    dr = ImageDraw.Draw(im)
    lamp = hx(v["lamp"])
    for r in range(H):
        for c in range(W):
            x, y = c * s, r * s
            if solid[r, c]:
                dr.rectangle((x, y, x + s - 1, y + s - 1), fill=(64, 62, 60))
                for dr_, dc, shade, box in ((0, 1, 0.6, (x + s - 7, y, x + s - 1, y + s - 1)), (0, -1, 0.6, (x, y, x + 6, y + s - 1)),
                                            (-1, 0, 1.0, (x, y, x + s - 1, y + 6)), (1, 0, 0.5, (x, y + s - 7, x + s - 1, y + s - 1))):
                    q = (r + dr_, c + dc)
                    if 0 <= q[0] < H and 0 <= q[1] < W and not solid[q]:
                        sky = 15 if (c + dc + u0) >= 0 else 0
                        col = STONE * table[sky, level[q]] * shade
                        dr.rectangle(box, fill=tuple(int(k * 255 + 0.5) for k in col))
            else:
                base = np.array(BG) / 255.0
                col = base + (lamp * 0.75 - base) * (level[r, c] / 15.0) ** 1.2
                if glass[r, c]:
                    col = hx("#ffc65a")
                dr.rectangle((x, y, x + s - 1, y + s - 1), fill=tuple(int(k * 255 + 0.5) for k in col))
                if level[r, c] and not glass[r, c]:
                    label(dr, (x + (9 if level[r, c] < 10 else 5), y + 6), str(level[r, c]), 14,
                          (20, 20, 30) if level[r, c] >= 11 else (214, 205, 190))
    for u, y, lv in sources:
        r, c = cell(u, y)
        dr.rectangle((c * s, r * s, c * s + s - 1, r * s + s - 1), outline=(255, 255, 255), width=2)
    r, c = cell(3, 0)
    dr.rectangle((c * s + 8, r * s + 14, c * s + s - 9, r * s + s - 1), fill=(30, 34, 44))                   # floodlight
    x = W * s + 8
    for y_, text in ((16.5, "女儿墙 16–17"), (15, "檐口 15"), (10.5, "主层大拱窗"), (3.5, "底层小窗"), (0.5, "勒脚 0–1")):
        label(dr, (x, (y1 - 1 - y_) * s + 6), text, 14, DIM)
    label(dr, (6, 6), "室内", 15, DIM)
    label(dr, ((W - 4) * s, 6), "前庭一侧", 15, DIM)
    return im


def fig_lights(out):
    v = LOOKS["blue"]
    plan, sec = plan_of_lights(v), section_of_lights(v)
    pad = 14
    im = Image.new("RGB", (plan.width + sec.width + 3 * pad, max(plan.height, sec.height + 150) + 96 + pad), BG)
    dr = ImageDraw.Draw(im)
    label(dr, (pad, 12), "隐形光源怎么摆（A 蓝调时刻）", 26)
    label(dr, (pad, 46), "左：俯视，地面按天光加灯光显示的颜色画，圆点是隐形光源（示意布置，数量和位置以骨架和 A6 的灯具为准）。"
          "右：切过一跨窗的剖面，数字是那一格的方块光等级，白框是隐形光源。", 15, DIM)
    im.paste(plan, (pad, 96))
    x = plan.width + 2 * pad
    im.paste(sec, (x, 96))
    y = 96 + sec.height + 12
    for name, _lo, col in TIERS:
        dr.ellipse((x, y + 3, x + 14, y + 17), fill=col)
        label(dr, (x + 22, y), name, 15)
        y += 24
    for line in ("窗后第一格放 9–10：窗框和窗台外沿得到 7–8，",
                 "正是灯光颜色最纯的两级；再亮就发白。",
                 "洗墙灯 8 放在基座前两格，只把墙脚到窗台染暖。",
                 "路灯 14 挂在 5 格高：脚下地面 9–10，四五格外融进冷色；",
                 "离大墙面至少 8 格，到墙上只剩 5 以下（这张剖面里没有画）。"):
        label(dr, (x, y + 4), line, 14, DIM)
        y += 21
    save(im, out, "sky-lights.jpg")


def at_tick(tick):
    """The look between keyframes: (weights by version)."""
    keys = KEYS + [(KEYS[0][0] + 24000, KEYS[0][1])]
    for (t0, a), (t1, b) in zip(keys, keys[1:]):
        if t0 <= tick <= t1:
            w = 0.0 if t1 == t0 else (tick - t0) / (t1 - t0)
            return a, b, w
    return keys[-1][1], keys[-1][1], 0.0


def fig_timeline(out):
    W, pad = 1440, 14
    im = Image.new("RGB", (W + 2 * pad, 436), BG)
    dr = ImageDraw.Draw(im)
    label(dr, (pad, 12), "时间线：一天 24000 刻里三个版本各占哪一段", 26)
    label(dr, (pad, 46), "任何时刻都是一套完整的光线；三个命名时刻落在各自的平台中间。原版的 day / noon / night / midnight 也都落在平台上。", 15, DIM)
    strip = np.zeros((96, W, 3))
    curves = {"stars": [], "sky_factor": [], "glow_alpha": []}
    for i in range(W):
        a, b, w = at_tick((i + 0.5) / W * 24000.0)
        va, vb = LOOKS[a], LOOKS[b]

        def mixc(k):
            return hx(va[k]) * (1 - w) + hx(vb[k]) * w

        def mixs(k):
            return va[k] * (1 - w) + vb[k] * w
        zen, hor, glow = mixc("zenith"), mixc("horizon"), mixc("glow")
        strip[0:32, i] = zen
        strip[32:64, i] = hor
        strip[64:96, i] = hor + (glow - hor) * mixs("glow_alpha")
        for k in curves:
            curves[k].append(mixs(k))
    y0 = 122
    im.paste(Image.fromarray((strip * 255).astype(np.uint8)), (pad, y0))
    for j, name in enumerate(("天顶", "地平线", "西边余晖")):
        label(dr, (pad + 6, y0 + 7 + 32 * j), name, 14)
    names = {"blue": "A 蓝调", "deep": "B 深夜", "glow": "C 余晖"}
    for n, (t, key) in enumerate(KEYS):
        x = pad + t / 24000.0 * W
        drop = 100 + 15 * (n % 3)
        dr.line((x, y0 - 6, x, y0 + drop + 13), fill=(232, 228, 216), width=1)
        label(dr, (x + 3, y0 + drop), "%d %s" % (t, names[key].split(" ")[0]), 13, DIM)
    for name, t in MARKERS.items():
        x = pad + t / 24000.0 * W
        dr.polygon((x - 7, y0 - 22, x + 7, y0 - 22, x, y0 - 8), fill=GOLD)
        text = "%s = %d" % (name, t)
        w = dr.textlength(text, font=font(14))
        label(dr, (x - w - 12 if name.endswith("glow") else x + 12 if name.endswith("blue") else x - w / 2, y0 - 34 if not name.endswith("deep") else y0 - 44), text, 14, GOLD)
    for name, t in VANILLA_MARKERS.items():
        x = pad + t / 24000.0 * W
        dr.polygon((x - 5, y0 + 162, x + 5, y0 + 162, x, y0 + 152), fill=DIM)
        label(dr, (x - 20, y0 + 164), "%s %d" % (name, t), 13, DIM)
    gy, gh = y0 + 196, 100
    dr.rectangle((pad, gy, pad + W, gy + gh), outline=(60, 64, 90))
    for k, col, name in (("stars", (232, 228, 216), "星星亮度"), ("sky_factor", (127, 147, 216), "天光强度"),
                         ("glow_alpha", (233, 124, 76), "余晖不透明度")):
        pts = [(pad + i, gy + gh - 4 - curves[k][i] * (gh - 8)) for i in range(W)]
        dr.line(pts, fill=col, width=2)
        i = {"stars": 430, "sky_factor": 250, "glow_alpha": 60}[k]
        label(dr, (pad + i, pts[i][1] - 20), name, 14, col)
    label(dr, (pad + W - 150, gy + 4), "刻度：0 在底，1 在顶", 13, DIM)
    save(im, out, "sky-timeline.jpg")


MATERIALS = [("灰白石 #c8c1b0", "#c8c1b0"), ("铺地 #b7b0a1", "#b7b0a1"), ("铜绿 #4fa487", "#4fa487"),
             ("凝灰岩", "#6d6f66"), ("深板岩", "#3b3c44"), ("铸铁 #303844", "#303844")]
CASES = [("无天光\n无灯", 0, 0, 1.0), ("天光\n顶面", 15, 0, 1.0), ("天光\n南北面", 15, 0, 0.8), ("天光\n东西面", 15, 0, 0.6),
         ("灯 5\n东西面", 15, 5, 0.6), ("灯 7", 15, 7, 0.6), ("灯 9", 15, 9, 0.6), ("灯 10", 15, 10, 0.6),
         ("灯 12", 15, 12, 0.6), ("灯 14", 15, 14, 0.6), ("灯 10\n顶面", 15, 10, 1.0), ("灯 14\n顶面", 15, 14, 1.0)]


def fig_tones(out):
    sw, sh, pad, left = 92, 46, 6, 170
    blocks = []
    for key in ("blue", "deep", "glow"):
        v = LOOKS[key]
        table = G.lightmap(attrs(v), 0.5)
        W = left + len(CASES) * (sw + pad) + 150
        im = Image.new("RGB", (W, 64 + (len(MATERIALS) + 1) * (sh + pad) + 8), BG)
        dr = ImageDraw.Draw(im)
        label(dr, (10, 6), v["title"], 20, GOLD)
        for j, (name, _s, _b, _f) in enumerate(CASES):
            for n, line in enumerate(name.split("\n")):
                label(dr, (left + j * (sw + pad) + 4, 30 + n * 15), line, 13, DIM)
        for i, (name, col) in enumerate([("光本身（白板）", "#ffffff")] + MATERIALS):
            y = 64 + i * (sh + pad)
            label(dr, (10, y + 14), name, 15)
            for j, (_n, s, b, f) in enumerate(CASES):
                c = hx(col) * table[s, b] * (f if i else 1.0)
                x = left + j * (sw + pad)
                dr.rectangle((x, y, x + sw, y + sh), fill=tuple(int(q * 255 + 0.5) for q in c))
                label(dr, (x + 4, y + sh - 17), to_hex(c), 12, (255, 255, 255) if luma(c) < 0.45 else (20, 20, 30))
        x = left + len(CASES) * (sw + pad) + 10
        for i, (name, col) in enumerate((("天顶", v["zenith"]), ("地平线", v["horizon"]), ("余晖", v["glow"]),
                                         ("云", v["cloud"]), ("亮窗", "#ffc65a"), ("灯罩", "#fff8dc"))):
            y = 64 + i * (sh + pad)
            dr.rectangle((x, y, x + 60, y + sh), fill=tuple(int(q * 255 + 0.5) for q in hx(col)))
            label(dr, (x + 66, y + 6), name, 14)
            label(dr, (x + 66, y + 24), col, 12, DIM)
        blocks.append(im)
    W = max(b.width for b in blocks)
    im = Image.new("RGB", (W + 28, sum(b.height for b in blocks) + 96), BG)
    dr = ImageDraw.Draw(im)
    label(dr, (14, 12), "明暗阶梯：各种材质在三个版本的光里显示成什么颜色（亮度设置 50%）", 24)
    label(dr, (14, 46), "色块 = 固有色 × 游戏的光照表 × 面的朝向系数（顶面 1.0，南北面 0.8，东西面 0.6）。“灯 N”是落在这个面上的方块光等级。右侧是不受光照表影响的颜色。", 15, DIM)
    y = 80
    for b in blocks:
        im.paste(b, (14, y))
        y += b.height
    save(im, out, "sky-tones.jpg")


# ---------------------------------------------------------------------------------------------
# numbers quoted in the draft

def numbers():
    print("== attributes to write ==")
    for key, v in LOOKS.items():
        sky, fog = derive(v)
        print(key, "sky_color", to_hex(sky), "fog_color", to_hex(fog), "mix share %.3f" % mix_share(v["sky_fog_end"]),
              "zenith fog share %.3f" % (16.0 / v["sky_fog_end"]))
        s = Sky(v)
        west = s.fog_colour(np.array([-1.0, 0.0, 0.0]))
        print("   horizon looking west", to_hex(west), "looking elsewhere", to_hex(s.fog_colour(np.array([1.0, 0, 0]))),
              "fan apex over it", to_hex(west + (s.glow - west) * s.alpha))
    print("== sky gradient: share of horizon colour by elevation ==")
    for end in (64, 80, 96, 128, 160, 512):
        row = []
        for e in (5, 10, 15, 20, 30, 45, 60, 90):
            reach = 16.0 / math.tan(math.radians(e)) if e < 90 else 0.0
            row.append("%d°:%.2f" % (e, min(1.0, (16.0 + 496.25 * reach / 512.0) / end)))
        print("  sky_fog_end %3d (mix %.3f)" % (end, mix_share(end)), " ".join(row))
    print("== sunset fan opacity (share of its alpha) ==")
    for a in (0.25, 0.45, 0.85):
        s = Sky(dict(LOOKS["blue"], glow_alpha=a), sprites=False)
        up = []
        for e in (0.5, 3, 6, 9, 12, 15):
            r = math.radians(e)
            up.append("%g°:%.2f" % (e, s.fan(np.array([[-math.cos(r), math.sin(r), 0.0]]))[0] / a))
        along = []
        for az in (0, 22.5, 45, 67.5, 85):
            r = math.radians(az)
            along.append("%g°:%.2f" % (az, s.fan(np.array([[-math.cos(r), 0.004, math.sin(r)]]))[0] / a))
        below = []
        for name, dd in (("west -10°", (-math.cos(math.radians(10)), -math.sin(math.radians(10)), 0)),
                         ("west -30°", (-math.cos(math.radians(30)), -math.sin(math.radians(30)), 0)),
                         ("down", (0, -1, 0)),
                         ("east -30°", (math.cos(math.radians(30)), -math.sin(math.radians(30)), 0)),
                         ("east -15°", (math.cos(math.radians(15)), -math.sin(math.radians(15)), 0))):
            below.append("%s:%.2f" % (name, s.fan(np.array([dd], dtype=float))[0] / a))
        print("  alpha %.2f top %.1f°" % (a, math.degrees(math.atan(40 * a / 120))), "| up from due west", " ".join(up))
        print("             along the horizon from west", " ".join(along), "| below", " ".join(below))
    print("== comet over the dome (apex 37, centre (4, 0)); head at 46°, tail tip near 62° ==")
    for name, (x, y, z) in (("V2 x=46", (46, 1.62, 0)), ("V2 x=40", (40, 1.62, 0)), ("V2 x=34", (34, 1.62, 0)),
                            ("V1 axis x=70", (70, -7.38, 0)), ("V1 north x=70 z=-22", (70, -7.38, -22)),
                            ("V1 north x=62 z=-30", (62, -7.38, -30))):
        apex = math.degrees(math.atan2(37 - y, math.hypot(x - 4, z)))
        off = math.degrees(math.atan2(-z, x - 4))
        tower = math.degrees(math.atan2(-29.5 - z, x - 13.5))
        print("  %-22s dome apex at %.1f° elevation, %.1f° south of due west; tower %.1f° north of due west" % (name, apex, off, -tower))
    print("== tone ladder (brightness 50%) ==")
    for key, v in LOOKS.items():
        for gamma in (0.0, 0.5, 1.0):
            t = G.lightmap(attrs(v), gamma)
            stone = hx("#c8c1b0")
            row = [("ambient only", t[0, 0] * stone), ("sky top", t[15, 0] * stone), ("sky N/S", t[15, 0] * stone * 0.8),
                   ("sky E/W", t[15, 0] * stone * 0.6), ("wash 7 E/W", t[15, 7] * stone * 0.6),
                   ("lamp 10 E/W", t[15, 10] * stone * 0.6), ("lamp 12 E/W", t[15, 12] * stone * 0.6),
                   ("lamp 10 top", t[15, 10] * stone), ("lamp 14 top", t[15, 14] * stone)]
            print("  %s brightness %.1f: " % (key, gamma) + "; ".join("%s %s Y%.2f" % (n, to_hex(c), luma(c)) for n, c in row))
        print("  %s sky: zenith Y%.2f horizon Y%.2f glow Y%.2f cloud Y%.2f | window #ffc65a Y%.2f" % (
            key, luma(hx(v["zenith"])), luma(hx(v["horizon"])), luma(hx(v["glow"])), luma(hx(v["cloud"])), luma(hx("#ffc65a"))))
    print("== block light: brightness and share of white by level ==")
    for lv in range(4, 16):
        x = lv / 15.0
        print("  level %2d: brightness %.2f white share %.2f" % (lv, x / (4 - 3 * x) * 1.4, 0.9 * (2 * x - 1) ** 2))
    cells = cloud_cells()
    print("== cloud map == cover %.3f (vanilla %.4f)" % (cells.mean(), vanilla_cells().mean()))


FIGS = {"looks": fig_looks, "views": fig_views, "pano": fig_pano, "sprites": fig_sprites, "clouds": fig_clouds,
        "tones": fig_tones, "lights": fig_lights, "timeline": fig_timeline}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=HERE)
    ap.add_argument("--only", default="")
    ap.add_argument("--size", type=int, default=SIZE[0], help="width of one sketch picture")
    ap.add_argument("--numbers", action="store_true")
    a = ap.parse_args()
    SIZE[:] = [a.size, a.size * 9 // 16]
    if a.numbers:
        numbers()
        return
    for name in (a.only.split(",") if a.only else FIGS):
        FIGS[name](a.out)


if __name__ == "__main__":
    main()
