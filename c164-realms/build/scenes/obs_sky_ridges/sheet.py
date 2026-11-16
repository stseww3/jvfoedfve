"""A preview of the far ridges by the game's arithmetic, to shape the ridge line on.

    python -m scenes.obs_sky_ridges.sheet <a folder outside the repository> [shot,shot...]
                                          [--alpha <afterglow opacity>] [--zoom]

The offline renderer cannot draw the ridges (the scene's own notes). This puts together what
plan/parts/sky-notes.md has of the game's sky, for the cameras of shots.json at 1280 x 720:

  the sky      zenith to horizon band by the distance over the sky's disc (section 3), the whole
               fog colour stained by the afterglow when the camera faces west
  the fan      the afterglow, laid over the sky (section 4; ridges.fan())
  the stars    the game's own 1500, adding the square of the star brightness
  the comet    the moon's square, added (scenes.obs.sky.comet)
  the ridges   the sheets of scenes.obs.sky.ridges in the fog's colour: everything beyond the fog's
               end is drawn in it
  the clouds   the vanilla layer as a flat face at mood.CLOUD_TOP in one colour, its opacity
               CLOUD_ALPHA x (1 - distance / CLOUD_FOG_END); where a sheet stands nearer, the
               sheet hides the layer behind it. (The layer is to go and the sky's shader is to
               paint a sea in its place, group #67329: then this part is out of date.)
  the site     the scene's stand-in blocks as flat dark shapes, so that the eye stands somewhere

Each shot is drawn twice, with the ridges (<shot>.png) and without (<shot>_bare.png); --zoom adds
the band about the horizon three times enlarged (<shot>_zoom.png: with above, without below).

It is not a rendering and proves nothing about the game: whether a sheet that far out is drawn at
all, and in which colour, is for the pictures from the game.
"""
import math
import os
import sys

import numpy as np
from PIL import Image

from artkit import gamescene as G
from scenes.obs.common import skeleton as S
from scenes.obs.sky import comet, mood, ridges

from . import ASPECT, CAMERAS, FOV, SKIRT_Y

SIZE = (1280, 720)
VIEW = 12 * 16.0                 # the view distance the map is shown at, in blocks
SITE = (0.085, 0.10, 0.17)       # the stand-in's blocks under the night's light, flat
WEST = np.array([-1.0, 0.0, 0.0])


def _rgb(text):
    return np.array([int(text[i:i + 2], 16) for i in (1, 3, 5)]) / 255.0


def rays(pos, at, size=SIZE):
    f = np.array(at, dtype=float) - np.array(pos, dtype=float)
    f /= np.linalg.norm(f)
    right = np.cross(f, (0.0, 1.0, 0.0))
    right /= np.linalg.norm(right)
    top = np.cross(right, f)
    half = math.tan(math.radians(FOV / 2.0))
    w, h = size
    u = ((np.arange(w) + 0.5) / w * 2.0 - 1.0) * half * ASPECT
    v = (1.0 - (np.arange(h) + 0.5) / h * 2.0) * half
    d = f[None, None, :] + u[None, :, None] * right + v[:, None, None] * top
    return d / np.linalg.norm(d, axis=-1, keepdims=True), f


def fan(d, alpha):
    """ridges.fan() for a whole picture of directions."""
    best = np.zeros(d.shape[:2])
    apex = np.array([-100.0, 0.0, 0.0])
    for j in range(16):
        ring = [np.array([-120.0 * math.cos(h), 40.0 * alpha * math.cos(h), 120.0 * math.sin(h)])
                for h in (j * math.pi / 8.0, (j + 1) * math.pi / 8.0)]
        m = np.column_stack([apex, ring[0], ring[1]])
        if abs(np.linalg.det(m)) < 1e-9:
            continue
        k = d @ np.linalg.inv(m).T
        total = k.sum(axis=-1)
        inside = (k >= -1e-9).all(axis=-1) & (total > 1e-12)
        share = np.where(inside, alpha * k[..., 0] / np.where(inside, total, 1.0), 0.0)
        best = np.maximum(best, share)
    return best


def star_list(angle):
    """The game's stars (SkyRenderer.buildStars, as artkit.gamescene draws them): (centre, a, b,
    half size) with the directions in the scene's axes for a star angle."""
    back = (G.rot("x", -angle) @ G.rot("y", 90.0)).T
    rnd, out = G._Random(10842), []
    for _ in range(1500):
        v = np.array([rnd.float() * 2 - 1, rnd.float() * 2 - 1, rnd.float() * 2 - 1])
        size = 0.15 + rnd.float() * 0.1
        d2 = float(v @ v)
        if d2 <= 0.010000001 or d2 >= 1.0:
            continue
        turn = rnd.double() * math.pi * 2.0
        c = v / math.sqrt(d2)
        a = np.cross(c, (0.0, 1.0, 0.0) if abs(c[1]) < 0.99 else (1.0, 0.0, 0.0))
        a /= np.linalg.norm(a)
        b = np.cross(c, a)
        a, b = a * math.cos(turn) + b * math.sin(turn), b * math.cos(turn) - a * math.sin(turn)
        out.append((back @ c, back @ a, back @ b, size))
    return out


def stars(d, forward, angle):
    """1 where a star covers the pixel."""
    h, w = d.shape[:2]
    out = np.zeros((h, w))
    # the pixel a direction falls on: undo rays()
    right = np.cross(forward, (0.0, 1.0, 0.0))
    right /= np.linalg.norm(right)
    top = np.cross(right, forward)
    half = math.tan(math.radians(FOV / 2.0))
    for c, a, b, size in star_list(angle):
        along = c @ forward
        if along <= 0.05:
            continue
        x = (c @ right / along / (half * ASPECT) * 0.5 + 0.5) * w
        y = (0.5 - c @ top / along / half * 0.5) * h
        if not (-4 <= x < w + 4 and -4 <= y < h + 4):
            continue
        x0, x1, y0, y1 = max(0, int(x) - 4), min(w, int(x) + 5), max(0, int(y) - 4), min(h, int(y) + 5)
        if x0 >= x1 or y0 >= y1:
            continue
        box = d[y0:y1, x0:x1]
        ahead = box @ c
        p = box * (100.0 / np.maximum(ahead, 1e-9))[..., None] - c * 100.0
        out[y0:y1, x0:x1] = np.maximum(out[y0:y1, x0:x1], (np.abs(p @ a) <= size) & (np.abs(p @ b) <= size) & (ahead > 0))
    return out


def comet_light(d, look):
    """What the comet adds: the moon's square as scenes.obs.sky.comet.directions() lays it."""
    th = math.radians(mood.MOON_ANGLE)
    centre = np.array([-math.sin(th), math.cos(th), 0.0])
    north, up = np.array([0.0, 0.0, -1.0]), np.array([math.cos(th), math.sin(th), 0.0])
    along = d @ centre
    ok = along > 0.2
    q = d / np.where(ok, along, 1.0)[..., None] - centre
    kn, ku = q @ north / 0.2, q @ up / 0.2
    ok &= (np.abs(kn) < 1.0) & (np.abs(ku) < 1.0)
    px = comet.comet(comet.DEFAULT_STYLE, comet.STRENGTH[look], comet.TAIL[look])
    n = px.shape[0]
    col = np.clip(((kn * 0.5 + 0.5) * n).astype(int), 0, n - 1)
    row = np.clip(((-ku * 0.5 + 0.5) * n).astype(int), 0, n - 1)
    return np.where(ok[..., None], px[row, col], 0.0)


def _slab(pos, d, lo, hi):
    """Distance along each ray to an axis-aligned box, inf where it misses."""
    with np.errstate(divide="ignore", invalid="ignore"):
        t0 = (np.array(lo, dtype=float) - pos) / d
        t1 = (np.array(hi, dtype=float) - pos) / d
    near, far = np.minimum(t0, t1).max(axis=-1), np.maximum(t0, t1).min(axis=-1)
    return np.where((far >= near) & (far > 0.0), np.maximum(near, 0.0), np.inf)


def site(pos, d):
    """Distance to the stand-in's masses (the scene's masses()); of the half-round sunset platform
    only the floor, which is all that the cameras on it and behind the terrace can see of it."""
    t = np.full(d.shape[:2], np.inf)
    x0, z0, x1, z1 = S.UPPER_TERRACE
    t = np.minimum(t, _slab(pos, d, (x0, SKIRT_Y, z0), (x1 + 1, S.GROUND, z1 + 1)))
    x0, z0, x1, z1 = S.LOWER_PLATFORM
    t = np.minimum(t, _slab(pos, d, (x0, SKIRT_Y, z0), (x1 + 1, S.LOWER_GROUND, z1 + 1)))
    x0, z0, x1, z1 = S.SOUTH_LOOKOUT["box"]
    t = np.minimum(t, _slab(pos, d, (x0, SKIRT_Y, z0), (x1 + 1, S.SOUTH_LOOKOUT["feet"], z1 + 1)))
    t = np.minimum(t, _slab(pos, d, (S.WALL_W, S.GROUND, S.Z_NORTH), (S.WALL_E + 1, S.CORNICE + 1, S.Z_SOUTH + 1)))
    with np.errstate(divide="ignore", invalid="ignore"):
        tg = (S.GROUND - pos[1]) / d[..., 1]
    cx, cz = S.SUNSET_PLATFORM["centre"]
    hit = pos[None, None, :] + d * np.where(np.isfinite(tg), tg, 0.0)[..., None]
    inside = (tg > 0) & (np.hypot(hit[..., 0] - cx - 0.5, hit[..., 2] - cz - 0.5) <= S.SUNSET_PLATFORM["radius"] + 0.5)
    return np.minimum(t, np.where(inside, tg, np.inf))


def sheets(pos, d):
    """Distance to the nearest ridge along each ray, inf where there is none."""
    t = np.full(d.shape[:2], np.inf)
    for name in ridges.SHEETS:
        low_left, low_right, up_left, _ = ridges.corners(name)
        across = (low_right - low_left) / ridges.WIDTH
        normal = np.cross(across, (0.0, 1.0, 0.0))
        with np.errstate(divide="ignore", invalid="ignore"):
            tt = ((low_left - pos) @ normal) / (d @ normal)
        ok = np.isfinite(tt) & (tt > 0)
        hit = pos[None, None, :] + d * np.where(ok, tt, 0.0)[..., None]
        col = np.floor((hit - low_left) @ across).astype(int)
        row = np.floor(up_left[1] - hit[..., 1]).astype(int)
        ok &= (col >= 0) & (col < ridges.WIDTH) & (row >= 0) & (row < ridges.HEIGHT)
        solid = ridges.picture(name)[..., 3] > 0
        ok &= solid[np.clip(row, 0, ridges.HEIGHT - 1), np.clip(col, 0, ridges.WIDTH - 1)]
        t = np.minimum(t, np.where(ok, tt, np.inf))
    return t


def draw(pos, at, look, with_ridges=True, alpha=None):
    pos = np.array(pos, dtype=float)
    v = mood.look(look)
    alpha = v["glow_alpha"] if alpha is None else alpha
    zenith, horizon, glow = _rgb(v["zenith"]), _rgb(v["horizon"]), _rgb(v["glow"])
    d, forward = rays(pos, at)
    # the fog's colour, stained when the camera faces west
    fog = horizon + (glow - horizon) * max(0.0, float(forward @ WEST)) * alpha
    reach_end = min(VIEW, v["sky_fog_end"])
    z = 16.0 / reach_end
    sky = (zenith - z * horizon) / (1.0 - z)
    up = d[..., 1]
    with np.errstate(divide="ignore", invalid="ignore"):
        rho = 16.0 * np.hypot(d[..., 0], d[..., 2]) / up
    f = np.where((up > 1e-4) & (rho < 512.0), np.minimum(1.0, (16.0 + 496.25 * rho / 512.0) / reach_end), 1.0)
    out = sky + (fog - sky) * f[..., None]
    out = out + (glow - out) * fan(d, alpha)[..., None]
    out = out + (stars(d, forward, v.get("star_angle", mood.STAR_ANGLE)) * v["stars"] ** 2)[..., None]
    out = out + comet_light(d, look if look in comet.STRENGTH else mood.DEFAULT)
    out = np.clip(out, 0.0, 1.0)

    t_sheet = sheets(pos, d) if with_ridges else np.full(d.shape[:2], np.inf)
    out = np.where(np.isfinite(t_sheet)[..., None], fog, out)
    # the cloud layer's face, where nothing stands before it
    with np.errstate(divide="ignore", invalid="ignore"):
        t_cloud = np.where(up < -1e-6, (mood.CLOUD_TOP - pos[1]) / up, np.inf)
    reach = t_cloud * np.hypot(d[..., 0], d[..., 2])
    share = np.where(np.isfinite(t_cloud) & (t_cloud < t_sheet),
                     mood.CLOUD_ALPHA * np.clip(1.0 - np.where(np.isfinite(reach), reach, 1e9) / mood.CLOUD_FOG_END, 0.0, 1.0), 0.0)
    out = out + (_rgb(v["cloud"]) - out) * share[..., None]
    t_site = site(pos, d)
    out = np.where(np.isfinite(t_site)[..., None], np.array(SITE), out)
    return (np.clip(out, 0.0, 1.0) * 255.0 + 0.5).astype(np.uint8)


def horizon_band(pos, at, img, zoom=3, size=SIZE):
    """The rows about the horizon, enlarged."""
    _, forward = rays(pos, at)
    half = math.tan(math.radians(FOV / 2.0))
    pitch = math.asin(forward[1])
    row = lambda e: int((0.5 - math.tan(math.radians(e) - pitch) / half * 0.5) * size[1])
    r0, r1 = max(0, row(9.0)), min(size[1], row(-7.0))
    c0 = size[0] // 2 - size[0] // (2 * zoom)
    crop = img[r0:r1, c0:c0 + size[0] // zoom]
    return np.repeat(np.repeat(crop, zoom, axis=0), zoom, axis=1)


def main(argv):
    args = [a for a in argv if not a.startswith("--")]
    alpha = float(argv[argv.index("--alpha") + 1]) if "--alpha" in argv else None
    if alpha is not None:
        args.remove(argv[argv.index("--alpha") + 1])
    if not args:
        raise SystemExit(__doc__)
    folder = args[0]
    if os.path.abspath(folder).startswith(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")) + os.sep):
        raise SystemExit("the preview is not a kept picture: give a folder outside the repository")
    os.makedirs(folder, exist_ok=True)
    wanted = args[1].split(",") if len(args) > 1 else list(CAMERAS)
    for name in wanted:
        pos, at, look = CAMERAS[name]
        with_, bare = (draw(pos, at, look, flag, alpha) for flag in (True, False))
        Image.fromarray(with_).save(os.path.join(folder, name + ".png"))
        Image.fromarray(bare).save(os.path.join(folder, name + "_bare.png"))
        if "--zoom" in argv:
            both = np.concatenate([horizon_band(pos, at, with_), horizon_band(pos, at, bare)], axis=0)
            Image.fromarray(both).save(os.path.join(folder, name + "_zoom.png"))
        print(os.path.join(folder, name + ".png"))


if __name__ == "__main__":
    main(sys.argv[1:])
