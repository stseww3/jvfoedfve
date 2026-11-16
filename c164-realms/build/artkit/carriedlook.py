"""A scene under a look the resource pack carries (artkit.mood.Carried), drawn without the game.

A look that lives in the data pack's registry is drawn with the game's own arithmetic
(artkit.raytrace): one fog colour, fog between two distances, the fog colour where no block is. A
carried look is painted by the pack's core shaders, and what those do is the look's own affair. Its
module says the same arithmetic in numpy, the look's twin (Carried.offline), and this module draws
with that: every colour is asked of the twin for every pixel's direction, and how much of them a
block takes is worked out here, in the compiled loop, by the two laws below.

What the twin offers (directions are (n, 3) arrays of unit vectors, x east, y up, z south; colours
0..1; camera_y the world height of the eye):

    n                    the look's numbers, a dict. Read here: tick (the tick at which the look's
                         dictionary of attributes shows this look: the light on the blocks, the
                         stars and the bodies are taken from there, as before) and the numbers of
                         the laws below: air, mist, mist_height, fog_start, fog_end, level_full,
                         level_none, sea_y
    band(d)              the colour the haze takes a thing to
    behind(d, camera_y)  what is painted behind a thing: what it goes into where it is levelled,
                         and at the rim of the view distance
    sky_at(d, camera_y)  what is seen where no block is
    apply(colour, distance, d, camera_y, edge)
                         a thing's colour on the screen, `distance` away, `edge` being the share of
                         the game's fog at the rim of the view distance. The compiled loop's
                         arithmetic is held against this at every picture (checked()).

The laws (hazed(), for one hit `t` away along a line of sight):

    the haze   an optical depth along the line: t / air for the air's own haze, and the mist that
               lies on a level (sea_y): depth 1 after `mist` blocks along that level, thinning by
               1/e every mist_height blocks above it; below the level the line is counted as far
               as the level. exp(-depth) of the thing is left, the rest is the band.
    levelled   what lies low over the level is taken into what is painted behind it: not at all up
               to fog_start blocks away on the map, wholly from fog_end on; in full up to
               level_full blocks above the level, not at all from level_none on.
    the rim    the game's own fog over the last tenth of the view distance, measured on the map or
               straight up and down, whichever is more. It takes a thing into what is painted
               behind it too; of this and the levelling the greater counts.

The server sends blocks for `chunks` chunks round a player (10 on Realms), so only those columns
are drawn. The stars and the bodies are the offline renderer's own and are added above the horizon.
"""
import math

import numpy as np
from numba import njit, prange

from . import raytrace as R

CHUNKS = 10         # the view distance of the server the map is made for (Realms)
# places in the array of numbers the compiled loop takes
Q_AIR, Q_MIST, Q_MIST_H, Q_EYE, Q_NEAR, Q_LOW, Q_FAR, Q_SIZE = 0, 1, 2, 3, 4, 6, 8, 10


@njit(cache=True)
def _depth(q, distance, rise):
    """The optical depth of the haze over `distance` blocks along a line from the camera that gains
    `rise` a block."""
    height = max(q[Q_EYE], 0.0)
    reach = distance
    if rise < 0.0:
        reach = min(distance, height / max(-rise, 1e-5))
    a = reach * rise / q[Q_MIST_H]
    start = math.exp(-height / q[Q_MIST_H])
    if abs(a) < 1e-3:
        mist = reach * start * (1.0 - 0.5 * a)
    else:
        mist = (start - math.exp(-max(height + reach * rise, 0.0) / q[Q_MIST_H])) * q[Q_MIST_H] / rise
    return distance / q[Q_AIR] + mist / q[Q_MIST]


@njit(cache=True)
def hazed(q, r, g, b, t, dx, dy, dz, band, behind):
    """The colour (r, g, b) of a hit t away along the unit direction (dx, dy, dz), as the look's
    shaders show it: taken towards the band by the haze, then towards what is painted behind it by
    the levelling or by the rim, whichever is more."""
    f = 1.0 - math.exp(-_depth(q, t, dy))
    across = t * math.sqrt(dx * dx + dz * dz)
    far = min(1.0, max(0.0, (across - q[Q_NEAR]) / (q[Q_NEAR + 1] - q[Q_NEAR])))
    low = min(1.0, max(0.0, (q[Q_LOW + 1] - (q[Q_EYE] + t * dy)) / (q[Q_LOW + 1] - q[Q_LOW])))
    rim = min(1.0, max(0.0, (max(across, t * abs(dy)) - q[Q_FAR]) / (q[Q_FAR + 1] - q[Q_FAR])))
    gone = max(far * low, rim)
    r, g, b = r + (band[0] - r) * f, g + (band[1] - g) * f, b + (band[2] - b) * f
    return r + (behind[0] - r) * gone, g + (behind[1] - g) * gone, b + (behind[2] - b) * gone


@njit(cache=True)
def _plain_sky(env, dx, dy, dz):
    """raytrace.sky_colour before it adds the stars and the bodies."""
    f = 1.0
    if dy > 1e-4:
        reach = 16.0 * math.sqrt(dx * dx + dz * dz) / dy
        if reach < 512.0:
            f = min(1.0, (16.0 + 496.25 * reach / 512.0) / env[R.SKY_END])
    return (env[R.SKY] + (env[R.FOG] - env[R.SKY]) * f, env[R.SKY + 1] + (env[R.FOG + 1] - env[R.SKY + 1]) * f,
            env[R.SKY + 2] + (env[R.FOG + 2] - env[R.SKY + 2]) * f)


@njit(cache=True)
def _trace(w, q, px, py, pz, dx, dy, dz, band, behind, beyond):
    """raytrace.trace, its loop as it stands there, with the look's shaders for the game's fog:
    every hit is hazed(), and where the ray meets nothing the painted sky itself is seen, with the
    stars and the bodies on it above the horizon."""
    env = w.env
    nx, ny, nz = w.grid.shape
    t0, t1 = 0.0, R.BIG
    if abs(dx) > 1e-12:
        a, b = (0.0 - px) / dx, (nx - px) / dx
        t0, t1 = max(t0, min(a, b)), min(t1, max(a, b))
    elif px < 0.0 or px >= nx:
        t1 = -1.0
    if abs(dy) > 1e-12:
        a, b = (0.0 - py) / dy, (ny - py) / dy
        t0, t1 = max(t0, min(a, b)), min(t1, max(a, b))
    elif py < 0.0 or py >= ny:
        t1 = -1.0
    if abs(dz) > 1e-12:
        a, b = (0.0 - pz) / dz, (nz - pz) / dz
        t0, t1 = max(t0, min(a, b)), min(t1, max(a, b))
    elif pz < 0.0 or pz >= nz:
        t1 = -1.0
    t1 = min(t1, q[Q_FAR + 1] / max(math.sqrt(dx * dx + dz * dz), abs(dy), 1e-9))
    sr, sg, sb = beyond[0], beyond[1], beyond[2]
    if dy > 0.0:
        fr, fg, fb = R.sky_colour(w, dx, dy, dz)
        pr, pg, pb = _plain_sky(env, dx, dy, dz)
        sr, sg, sb = min(1.0, sr + max(0.0, fr - pr)), min(1.0, sg + max(0.0, fg - pg)), min(1.0, sb + max(0.0, fb - pb))
    if t0 >= t1:
        return sr, sg, sb

    t = t0 + 1e-5
    cx = min(nx - 1, max(0, int(math.floor(px + dx * t))))
    cy = min(ny - 1, max(0, int(math.floor(py + dy * t))))
    cz = min(nz - 1, max(0, int(math.floor(pz + dz * t))))
    stx = 1 if dx > 0 else -1
    sty = 1 if dy > 0 else -1
    stz = 1 if dz > 0 else -1
    tdx = abs(1.0 / dx) if abs(dx) > 1e-12 else R.BIG
    tdy = abs(1.0 / dy) if abs(dy) > 1e-12 else R.BIG
    tdz = abs(1.0 / dz) if abs(dz) > 1e-12 else R.BIG
    tmx = (cx + (1 if dx > 0 else 0) - px) / dx if abs(dx) > 1e-12 else R.BIG
    tmy = (cy + (1 if dy > 0 else 0) - py) / dy if abs(dy) > 1e-12 else R.BIG
    tmz = (cz + (1 if dz > 0 else 0) - pz) / dz if abs(dz) > 1e-12 else R.BIG

    trans = 1.0
    cr = cg = cb = 0.0
    tmin = 0.0
    ent_t, ent_r, ent_g, ent_b, ent_a = R.BIG, 0.0, 0.0, 0.0, 0.0
    last = -1
    gy, gz = w.cg_start.shape[1], w.cg_start.shape[2]
    first = t0 == 0.0
    while True:
        t_exit = min(tmx, tmy, tmz)
        coarse = ((cx // R.COARSE) * gy + cy // R.COARSE) * gz + cz // R.COARSE
        if coarse != last:
            last = coarse
            s = w.cg_start[cx // R.COARSE, cy // R.COARSE, cz // R.COARSE]
            for i in range(s, s + w.cg_n[cx // R.COARSE, cy // R.COARSE, cz // R.COARSE]):
                et, er, eg, eb, ea = R.entity_hit(w, w.cg_list[i], px, py, pz, dx, dy, dz, tmin, env[R.PIXEL])
                if et < ent_t:
                    ent_t, ent_r, ent_g, ent_b, ent_a = et, er, eg, eb, ea
        pal = w.grid[cx, cy, cz]
        ht, he, hf = R.BIG, -1, 0
        hr = hg = hb = ha = 0.0
        hx = hy = hz = 0.0
        if pal != 0 and not (first and w.pal_flags[pal] & R.OPAQUE):
            ht, he, hf, hr, hg, hb, ha, hx, hy, hz = R.cell_hit(w, pal, cx, cy, cz, px, py, pz, dx, dy, dz, tmin, t_exit,
                                                                env[R.PIXEL])
        if (ent_t < ht and ent_t <= t_exit + 1e-6) or he >= 0:
            if ent_t < ht and ent_t <= t_exit + 1e-6:
                at, r, g, b, alpha = ent_t, ent_r, ent_g, ent_b, ent_a
                ent_t, last = R.BIG, -1
            else:
                r, g, b = R.block_colour(w, pal, he, hf, cx, cy, cz, hx, hy, hz, hr, hg, hb)
                at, alpha = ht, ha
            r, g, b = hazed(q, r, g, b, at, dx, dy, dz, band, behind)
            cr += trans * alpha * r
            cg += trans * alpha * g
            cb += trans * alpha * b
            trans *= 1.0 - alpha
            if trans < 0.004:
                return cr, cg, cb
            tmin = at + 1e-5
            continue
        if t_exit >= t1:
            break
        first = False
        if tmx <= tmy and tmx <= tmz:
            cx += stx
            tmx += tdx
            if cx < 0 or cx >= nx:
                break
        elif tmy <= tmz:
            cy += sty
            tmy += tdy
            if cy < 0 or cy >= ny:
                break
        else:
            cz += stz
            tmz += tdz
            if cz < 0 or cz >= nz:
                break
    return cr + trans * sr, cg + trans * sg, cb + trans * sb


@njit(cache=True, parallel=True)
def _draw(w, q, cam, rays, band, behind, beyond, out):
    height, width = out.shape[0], out.shape[1]
    for j in prange(height):
        for i in range(width):
            n = j * width + i
            r, g, b = _trace(w, q, cam[0], cam[1], cam[2], rays[n, 0], rays[n, 1], rays[n, 2], band[n], behind[n], beyond[n])
            out[j, i, 0] = r
            out[j, i, 1] = g
            out[j, i, 2] = b


def rays(cam, width, height):
    """The unit direction of every pixel, row by row (x east, y up, z south); cam as
    gamescene.Scene.camera() gives it."""
    x = ((np.arange(width) + 0.5) / width * 2.0 - 1.0) * cam[12] * width / height
    y = (1.0 - (np.arange(height) + 0.5) / height * 2.0) * cam[12]
    d = cam[3:6][None, None, :] + x[None, :, None] * cam[6:9][None, None, :] + y[:, None, None] * cam[9:12][None, None, :]
    d = d.reshape(-1, 3)
    return np.ascontiguousarray(d / np.linalg.norm(d, axis=1, keepdims=True))


def numbers(laws, look, camera_y):
    """The numbers the compiled loop takes: the laws', the camera's height over their level, the
    rim of the view distance (look: a gamelook.Look made for that view distance)."""
    q = np.zeros(Q_SIZE)
    q[Q_AIR], q[Q_MIST], q[Q_MIST_H] = laws["air"], laws["mist"], laws["mist_height"]
    q[Q_EYE] = camera_y - laws["sea_y"]
    q[Q_NEAR:Q_NEAR + 2] = laws["fog_start"], laws["fog_end"]
    q[Q_LOW:Q_LOW + 2] = laws["level_full"], laws["level_none"]
    q[Q_FAR:Q_FAR + 2] = look.far_start, look.far_end
    return q


def checked(q, twin, camera_y, n=4000):
    """hazed() against the twin's apply() on made-up hits: colours, distances and directions at
    random, the nearly level lines among them. Says by how much the two differ if they do."""
    g = np.random.default_rng(1)
    colour, distance = g.uniform(0.0, 1.0, (n, 3)), g.uniform(0.0, 400.0, n)
    d = g.normal(size=(n, 3))
    d[: n // 10, 1] *= 1e-5
    d /= np.linalg.norm(d, axis=1, keepdims=True)
    across = distance * np.hypot(d[:, 0], d[:, 2])
    rim = np.clip((np.maximum(across, distance * np.abs(d[:, 1])) - q[Q_FAR]) / (q[Q_FAR + 1] - q[Q_FAR]), 0.0, 1.0)
    band, behind = twin.band(d), twin.behind(d, camera_y)
    ours = np.array([hazed(q, *colour[i], distance[i], *d[i], band[i], behind[i]) for i in range(n)])
    theirs = twin.apply(colour, distance, d, camera_y, rim)
    if not np.allclose(ours, theirs, rtol=0.0, atol=1e-9):
        raise SystemExit(f"artkit.carriedlook: hazed() and the look's twin differ by up to {np.abs(ours - theirs).max():g}: "
                         f"the look's laws have changed and this module has not")


def loaded(pos, lo, shape, chunks):
    """Which columns of a grid the game has loaded round a camera (ChunkTrackingView.isWithinDistance).
    pos: the camera, lo: the grid's corner, both in the world's coordinates."""
    cx, cz = math.floor(pos[0] / 16.0), math.floor(pos[2] / 16.0)
    dx = np.maximum(np.abs(np.floor((np.arange(shape[0]) + lo[0]) / 16.0) - cx) - 1, 0)
    dz = np.maximum(np.abs(np.floor((np.arange(shape[2]) + lo[2]) / 16.0) - cz) - 1, 0)
    return dx[:, None] ** 2 + dz[None, :] ** 2 < chunks * chunks


def picture(scene, look, cam, pos, twin, size=(1280, 720), ss=1, fov=70.0, chunks=CHUNKS):
    """8-bit RGB picture (h, w, 3) of a gamescene.Scene under the look of `twin`, from the camera
    `cam` (scene.camera()) that stands at `pos` in the scene's coordinates. look: the gamelook.Look
    of the twin's tick, made for the client's view distance; chunks: the server's, which says what
    is loaded. ss: rays per pixel along each side, as in Scene.picture()."""
    width, height = size[0] * ss, size[1] * ss
    w = scene.world(look, 2.0 * math.tan(math.radians(fov) / 2.0) / height)
    at = np.asarray(pos, dtype=float) + scene.place
    there = loaded(at, scene.lo + scene.place, w.grid.shape, chunks)
    near = w.grid.copy()
    near[np.broadcast_to(~there[:, None, :], near.shape)] = 0
    w = w._replace(grid=near)
    cam = np.ascontiguousarray(cam, dtype=np.float64)
    d = rays(cam, width, height)
    q = numbers(twin.n, look, float(at[1]))
    checked(q, twin, float(at[1]))
    out = np.zeros((height, width, 3))
    _draw(w, q, cam, d, np.ascontiguousarray(twin.band(d)), np.ascontiguousarray(twin.behind(d, float(at[1]))),
          np.ascontiguousarray(twin.sky_at(d, float(at[1]))), out)
    if ss > 1:
        out = out.reshape(size[1], ss, size[0], ss, 3).mean(axis=(1, 3))
    return (np.clip(out, 0.0, 1.0) * 255.0 + 0.5).astype(np.uint8)
