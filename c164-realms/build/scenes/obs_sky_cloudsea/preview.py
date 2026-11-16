"""What the real client should show of the sea of clouds, worked out offline: a private aid of the
card sky/cloudsea for trying shapes and the join with the sky between two trips to the real client.

    cd build && python -m scenes.obs_sky_cloudsea.preview --out ../renders/_wip/pre
        [--scene obs_sky_cloudsea] [--only v12,sunset_west | --only none] [--looks blue,glow]
        [--sea haze,same] [--fog 60,150] [--haze 800] [--chunks 10] [--size 1280x720] [--plan]
        [--sheet 3] [--set "REACH=140.0" ...]

build/render.py draws a scene as the registry look shows it at fourteen chunks: one fog colour for
the whole picture, fog from 60 to 192 blocks, no afterglow, and where no block is, the fog colour
down to the nadir. The map will not be shown like that (the director's rulings of 11-16): the
server sends blocks for ten chunks round a player, and the look is drawn by the resource pack's
shaders (A2's), which paint the sky under the horizon as well. This draws what is agreed with A2
for that and the one thing that is not, to see beforehand what the sea is then:

  - blocks: only the chunks the game has loaded round the camera at --chunks (10), and the game's
    wall of fog over the last tenth of that distance. No cloud layer: the shaders take it out.
  - the sky above the horizon: the game's own with the look's values (26.3: sky.fsh over the sky
    disc, the afterglow's fan of SkyRenderer, the stars and the comet), the horizon's colour drawn
    towards the afterglow by how far the direction points west (the game does that for a whole
    frame by where the camera faces; a shader does it for every pixel).
  - the fog: every block is drawn towards the fog colour of its own direction by
    (distance - start) / (end - start), the distance taken from the eye (--fog start,end; 60 and
    150 are the director's). Above the horizon the fog colour is that of the sky's lowest ring in
    the direction of the compass, afterglow and all, and not the sky behind the block: a tower in
    the fog keeps its outline against the darker sky higher up.
  - under the horizon the far sea is painted: a level sea at the height of the block sea's face,
    seen from the camera's own height, in the look's "cloud" colour (level cloud as the look
    lights it), sunk into the colour of the lowest ring above it by how far off the eye meets it.
    How fast it sinks is what --sea tries:
      same   by the blocks' own fog, as if the block sea went on for ever: beyond the fog's end
             the sea is the ring's colour, and the fog colour under the horizon is the ring's too
      haze   by a haze of its own, 1 - exp(-distance / HAZE), far longer than the blocks' fog:
             the sea keeps its colour nearly to the horizon, and under the horizon a block is
             drawn towards the far sea of its own direction, so level cloud does not change
             colour in the fog at all and a head sinks into the sea's colour
    No star and no comet under the horizon.

The pictures are named <out>-<shot>-<look>-<sea>.png; with --sheet N they are laid side by side, N
to a row and half the size, in one picture <out>-sheet.png instead. --plan adds <out>-plan.png:
the sea from straight above in the tones the blue hour gives it, without fog, and prints what it
is made of; with --only none nothing else is drawn, and no ray is traced. --set NAME=VALUE changes
a constant of sky/cloudsea for this run, to try a shape without a commit. They are no evidence: the
card is settled on the real client's pictures. This only says beforehand what those should show
once the shaders do what is drawn here.
"""
import argparse
import atexit
import importlib
import math
import os
import shutil
import tempfile
import time

import numpy as np
from numba import njit, prange
from PIL import Image, ImageDraw

import render as offline
from artkit import gamelook, gamescene
from artkit import raytrace as R
from artkit.gameassets import Assets
from scenes.obs.sky import mood as sky

FOG = (60.0, 150.0)         # the blocks' fog (the director's): none nearer than the first, whole at the second
HAZE = 800.0                # --sea haze: the far sea has sunk into the horizon's colour by 1 - 1/e after this many blocks
SEAS = ("haze", "same")
# places in the array of numbers the drawing takes
Q_SKY, Q_FOG, Q_GLOW, Q_GLOW_A, Q_SIDE, Q_MIX, Q_SKY_END, Q_SEA, Q_HEIGHT, Q_HAZE = 0, 3, 6, 9, 10, 11, 12, 13, 16, 17
Q_START, Q_END, Q_FAR_START, Q_FAR_END, Q_LAW, Q_SIZE = 18, 19, 20, 21, 22, 23


@njit(cache=True)
def _afterglow(dx, dy, dz, alpha, side):
    """The share of the afterglow's alpha that lies over the sky in a direction (SkyRenderer's fan:
    the tip at (100 side, 0, 0), the rim at (120 side cos, 40 alpha cos, 120 sin))."""
    cx = 100.0 * side
    best = 0.0
    for i in range(16):
        t0, t1 = i * math.pi / 8.0, (i + 1) * math.pi / 8.0
        ax, ay, az = 120.0 * side * math.cos(t0) - cx, 40.0 * alpha * math.cos(t0), 120.0 * math.sin(t0)
        bx, by, bz = 120.0 * side * math.cos(t1) - cx, 40.0 * alpha * math.cos(t1), 120.0 * math.sin(t1)
        px, py, pz = dy * bz - dz * by, dz * bx - dx * bz, dx * by - dy * bx
        det = ax * px + ay * py + az * pz
        if abs(det) < 1e-9:
            continue
        u = (-cx * px) / det                        # the ray starts at the camera: minus the tip
        qx, qy, qz = 0.0, -(-cx) * az, (-cx) * ay   # (-cx, 0, 0) x (ax, ay, az)
        v = (dx * qx + dy * qy + dz * qz) / det
        t = (bx * qx + by * qy + bz * qz) / det
        if u >= 0.0 and v >= 0.0 and u + v <= 1.0 and t > 0.0:
            best = max(best, 1.0 - u - v)
    return best


@njit(cache=True)
def _horizon(q, ux):
    """The horizon's colour in a direction of the compass before the afterglow's fan is laid over
    it: the fog colour, warmer the further the direction points to the afterglow, a share of the
    sky colour in it."""
    tint = max(0.0, ux * q[Q_SIDE]) * q[Q_GLOW_A]
    r = q[Q_FOG] + (q[Q_GLOW] - q[Q_FOG]) * tint
    g = q[Q_FOG + 1] + (q[Q_GLOW + 1] - q[Q_FOG + 1]) * tint
    b = q[Q_FOG + 2] + (q[Q_GLOW + 2] - q[Q_FOG + 2]) * tint
    return r + (q[Q_SKY] - r) * q[Q_MIX], g + (q[Q_SKY + 1] - g) * q[Q_MIX], b + (q[Q_SKY + 2] - b) * q[Q_MIX]


@njit(cache=True)
def _ring(q, ux, uz):
    """The colour of the sky's lowest ring in a direction of the compass, afterglow and all."""
    r, g, b = _horizon(q, ux)
    a = q[Q_GLOW_A] * _afterglow(ux, 1e-3, uz, q[Q_GLOW_A], q[Q_SIDE])
    return r + (q[Q_GLOW] - r) * a, g + (q[Q_GLOW + 1] - g) * a, b + (q[Q_GLOW + 2] - b) * a


@njit(cache=True)
def _far_sea(q, ux, uz, dy):
    """The far sea in a direction under the horizon: the sea's colour, sunk into the ring's by how
    far off the eye meets the level of the sea's face."""
    r, g, b = _ring(q, ux, uz)
    t = q[Q_HEIGHT] / max(-dy, 1e-6)
    if q[Q_LAW] > 0.5:
        w = 1.0 - math.exp(-t / q[Q_HAZE])
    else:
        w = min(1.0, max(0.0, (t - q[Q_START]) / (q[Q_END] - q[Q_START])))
    return q[Q_SEA] + (r - q[Q_SEA]) * w, q[Q_SEA + 1] + (g - q[Q_SEA + 1]) * w, q[Q_SEA + 2] + (b - q[Q_SEA + 2]) * w


@njit(cache=True)
def _backdrop(q, dx, dy, dz):
    """What is seen in a direction where no block is, without the stars and the comet."""
    hx = math.sqrt(dx * dx + dz * dz)
    ux, uz = 1.0, 0.0
    if hx > 1e-9:
        ux, uz = dx / hx, dz / hx
    if dy <= 0.0:
        return _far_sea(q, ux, uz, dy)
    r, g, b = _horizon(q, ux)
    f = 1.0
    if dy > 1e-4:
        reach = 16.0 * hx / dy
        if reach < 512.0:
            f = min(1.0, (16.0 + 496.25 * reach / 512.0) / q[Q_SKY_END])
    r = q[Q_SKY] + (r - q[Q_SKY]) * f
    g = q[Q_SKY + 1] + (g - q[Q_SKY + 1]) * f
    b = q[Q_SKY + 2] + (b - q[Q_SKY + 2]) * f
    a = q[Q_GLOW_A] * _afterglow(dx, dy, dz, q[Q_GLOW_A], q[Q_SIDE])
    return r + (q[Q_GLOW] - r) * a, g + (q[Q_GLOW + 1] - g) * a, b + (q[Q_GLOW + 2] - b) * a


@njit(cache=True)
def _fog_colour(q, dx, dy, dz):
    """The colour the fog takes a block to that is seen in a direction."""
    hx = math.sqrt(dx * dx + dz * dz)
    ux, uz = 1.0, 0.0
    if hx > 1e-9:
        ux, uz = dx / hx, dz / hx
    if dy < 0.0 and q[Q_LAW] > 0.5:
        return _far_sea(q, ux, uz, dy)
    return _ring(q, ux, uz)


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
def _fog(q, t, dx, dy, dz):
    """The share of the backdrop in a block t away along a direction."""
    f = 0.0
    if t > q[Q_START]:
        f = 1.0 if t >= q[Q_END] else (t - q[Q_START]) / (q[Q_END] - q[Q_START])
    c = t * max(math.sqrt(dx * dx + dz * dz), abs(dy))
    if c > q[Q_FAR_START]:
        f = max(f, 1.0 if c >= q[Q_FAR_END] else (c - q[Q_FAR_START]) / (q[Q_FAR_END] - q[Q_FAR_START]))
    return f


@njit(cache=True)
def _trace(w, q, px, py, pz, dx, dy, dz):
    """raytrace.trace with the fog of the proposal: every hit is drawn towards the backdrop of the
    ray's direction, and where the ray meets nothing the backdrop itself is seen, with the stars
    and the comet on it above the horizon."""
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
    t1 = min(t1, q[Q_FAR_END] / max(math.sqrt(dx * dx + dz * dz), abs(dy), 1e-9))
    br, bg, bb = _fog_colour(q, dx, dy, dz)
    sr, sg, sb = _backdrop(q, dx, dy, dz)
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
        if ent_t < ht and ent_t <= t_exit + 1e-6:
            f = _fog(q, ent_t, dx, dy, dz)
            cr += trans * ent_a * (ent_r + (br - ent_r) * f)
            cg += trans * ent_a * (ent_g + (bg - ent_g) * f)
            cb += trans * ent_a * (ent_b + (bb - ent_b) * f)
            trans *= 1.0 - ent_a
            if trans < 0.004:
                return cr, cg, cb
            tmin = ent_t + 1e-5
            ent_t, last = R.BIG, -1
            continue
        if he >= 0:
            r, g, b = R.block_colour(w, pal, he, hf, cx, cy, cz, hx, hy, hz, hr, hg, hb)
            f = _fog(q, ht, dx, dy, dz)
            cr += trans * ha * (r + (br - r) * f)
            cg += trans * ha * (g + (bg - g) * f)
            cb += trans * ha * (b + (bb - b) * f)
            trans *= 1.0 - ha
            if trans < 0.004:
                return cr, cg, cb
            tmin = ht + 1e-5
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
def _draw(w, q, cam, width, height, out):
    half = cam[12]
    aspect = width / height
    for j in prange(height):
        for i in range(width):
            x = ((i + 0.5) / width * 2.0 - 1.0) * half * aspect
            y = (1.0 - (j + 0.5) / height * 2.0) * half
            dx = cam[3] + x * cam[6] + y * cam[9]
            dy = cam[4] + x * cam[7] + y * cam[10]
            dz = cam[5] + x * cam[8] + y * cam[11]
            n = math.sqrt(dx * dx + dy * dy + dz * dz)
            r, g, b = _trace(w, q, cam[0], cam[1], cam[2], dx / n, dy / n, dz / n)
            out[j, i, 0] = r
            out[j, i, 1] = g
            out[j, i, 2] = b


def numbers(look, name, chunks, fog, haze, sea, height):
    """The numbers _draw takes: a look's colours, the join's laws, how far the camera is over the sea's face."""
    a = look.attrs
    q = np.zeros(Q_SIZE)
    q[Q_SKY:Q_SKY + 3] = a["sky_color"][:3]
    q[Q_FOG:Q_FOG + 3] = a["fog_color"][:3]
    q[Q_SIDE] = -1.0 if math.sin(math.radians(look.sun_angle)) > 0.0 else 1.0
    if look.sunset is not None and chunks >= 4:
        q[Q_GLOW:Q_GLOW + 4] = look.sunset
    e = min(float(a["sky_fog_end_distance"]) / 16.0, float(chunks))
    q[Q_MIX] = 1.0 - (0.25 + 0.75 * min(1.0, max(0.0, e / 32.0))) ** 0.25
    q[Q_SKY_END] = look.sky_end
    q[Q_SEA:Q_SEA + 3] = sky._rgb(sky.look(name)["cloud"])
    q[Q_HEIGHT], q[Q_HAZE] = max(1.0, height), haze
    q[Q_START], q[Q_END] = fog
    q[Q_FAR_START], q[Q_FAR_END] = look.far_start, look.far_end
    q[Q_LAW] = float(SEAS.index(sea) == 0)
    return q


def loaded(pos, lo, shape, chunks):
    """Which columns of the grid the game has loaded round a camera (ChunkTrackingView.isWithinDistance)."""
    cx, cz = math.floor(pos[0] / 16.0), math.floor(pos[2] / 16.0)
    dx = np.maximum(np.abs(np.floor((np.arange(shape[0]) + lo[0]) / 16.0) - cx) - 1, 0)
    dz = np.maximum(np.abs(np.floor((np.arange(shape[2]) + lo[2]) / 16.0) - cz) - 1, 0)
    return dx[:, None] ** 2 + dz[None, :] ** 2 < chunks * chunks


def plan(cells, look, path, scale=2):
    """The sea from straight above, without fog, in the tones the look gives it; what stands in it
    is dark. Prints what the sea is made of."""
    from scenes.obs.common import blocks as B
    from scenes.obs.common import palette as P
    from scenes.obs.sky import cloudsea
    lit = look.lightmap[15][0]
    tones = [np.clip(np.array(P.colour("cloud", i)) / 255.0 * lit, 0.0, 1.0) for i in range(len(B.CLOUD))]
    index = {name: i for i, name in enumerate(B.CLOUD)}
    x0, z0, nx, nz = cloudsea._grid()
    high = np.full((nx, nz), -10 ** 6)
    tone = np.full((nx, nz), -1)
    total = 0
    for (x, y, z), state in cells.items():
        i, j = x - x0, z - z0
        t = index.get(state.partition("[")[0].split(":")[-1], -2)
        total += t >= 0
        if 0 <= i < nx and 0 <= j < nz and y > high[i, j]:
            high[i, j], tone[i, j] = y, t
    img = np.empty((nx, nz, 3))
    img[...] = (0.02, 0.02, 0.05)
    img[tone == -2] = (0.10, 0.10, 0.13)
    for t, colour in enumerate(tones):
        img[tone == t] = colour
    img = np.transpose(img, (1, 0, 2))              # north up, west left
    img = np.repeat(np.repeat(img, scale, axis=0), scale, axis=1)
    Image.fromarray((np.clip(img, 0.0, 1.0) * 255.0 + 0.5).astype(np.uint8)).save(path)
    cloud = tone >= 0
    levels = {int(y): int(((high == y) & cloud).sum()) for y in np.unique(high[cloud])}
    swell = cloud & (high <= cloudsea.MEAN + 1)
    share = {t: round(float(((tone == t) & swell).sum()) / max(1, int(swell.sum())), 3) for t in range(len(tones))}
    print(f"{path}: {total} blocks of cloud on {int(cloud.sum())} columns; columns by the y of their top block "
          f"{levels}; the tones of the swell (top block at {cloudsea.MEAN + 1} or lower), dark to light {share}; "
          f"x {x0}..{x0 + nx - 1}, z {z0}..{z0 + nz - 1}, {scale} px a block")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--scene", default="obs_sky_cloudsea")
    ap.add_argument("--out", required=True, help="prefix of the pictures: <out>-<shot>-<look>.png")
    ap.add_argument("--only", help="comma separated shot names (default: the test scene's MAIN_VIEWS); none: no shot")
    ap.add_argument("--looks", default="blue", help="comma separated looks or trials of the sky's")
    ap.add_argument("--sea", default="haze", help="comma separated: how the far sea sinks into the horizon, haze or same")
    ap.add_argument("--fog", default=f"{FOG[0]:g},{FOG[1]:g}", help="where the blocks' fog begins and where it is whole")
    ap.add_argument("--haze", type=float, default=HAZE)
    ap.add_argument("--chunks", type=int, default=10, help="view distance in chunks")
    ap.add_argument("--size", default="1280x720")
    ap.add_argument("--fov", type=float, default=77.0)
    ap.add_argument("--plan", action="store_true", help="also write <out>-plan.png")
    ap.add_argument("--sheet", type=int, default=0, help="one picture <out>-sheet.png, this many views to a row")
    ap.add_argument("--set", action="append", default=[], metavar="NAME=VALUE",
                    help="a constant of scenes.obs.sky.cloudsea for this run (a Python expression)")
    args = ap.parse_args()
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)

    t0 = time.time()
    sea = importlib.import_module("scenes.obs.sky.cloudsea")
    for item in args.set:
        key, _, value = item.partition("=")
        if not hasattr(sea, key.strip()):
            raise SystemExit(f"--set {item}: sky/cloudsea has no {key.strip()}")
        setattr(sea, key.strip(), eval(value, {"sea": sea}))
        print(f"sky/cloudsea.{key.strip()} = {getattr(sea, key.strip())!r} for this run")
    scene = importlib.import_module(f"scenes.{args.scene}")
    look_mod = importlib.import_module(f"scenes.{args.scene}.mood")
    base = importlib.import_module("scenes.obs_sky_cloudsea")
    canvas = scene.build()
    cells, entities = dict(canvas.b), canvas.entities
    print(f"{args.scene}: {len(cells)} blocks ({time.time() - t0:.0f} s)")
    names = [] if args.only == "none" else args.only.split(",") if args.only else list(base.MAIN_VIEWS)
    pack = tempfile.mkdtemp(prefix="c164pack-")
    atexit.register(shutil.rmtree, pack, ignore_errors=True)
    if names:
        offline.write_pack(args.scene, pack)
    assets = Assets(os.path.join(offline.ROOT, "client26", "versions", "26.3", "26.3.jar"), [pack])
    biome = look_mod.BIOMES[getattr(scene, "BIOME", sorted(look_mod.BIOMES)[0])]
    dimension = assets.json(f"{offline.DATA}dimension_type/overworld.json")
    lines = offline.timelines(assets) + [look_mod.TIMELINES[k] for k in sorted(look_mod.TIMELINES)]

    def look_at(tick):
        return gamelook.Look(tick, dimension, biome, lines, render_chunks=args.chunks)

    if args.plan:
        plan(cells, look_at(sky.tick("blue")), f"{args.out}-plan.png")
    if not names:
        return
    views = {s["name"]: s for s in base.shots()}
    fog = tuple(float(v) for v in args.fog.split(","))
    place = (0, 200, 0)
    world = gamescene.Scene(assets, cells, entities, look_at(6000), place=place,
                            say=lambda s: print(f"{s} ({time.time() - t0:.0f} s)"))
    size = tuple(int(v) for v in args.size.split("x"))
    pixel = 2.0 * math.tan(math.radians(args.fov) / 2.0) / size[1]
    tiles = []
    for name in names:
        shot = views[name]
        cam = np.ascontiguousarray(world.camera(shot["pos"], shot.get("look_at"), 0.0, 0.0, args.fov), dtype=np.float64)
        there = loaded(shot["pos"], world.lo, world.grid.shape, args.chunks)
        height = float(shot["pos"][1]) - sea.FACE
        for which in args.looks.split(","):
            look = look_at(sky.tick(which))
            w = world.world(look, pixel)
            near = w.grid.copy()
            near[~there[:, None, :] & np.ones((1, near.shape[1], 1), dtype=bool)] = 0
            w = w._replace(grid=near)
            for law in args.sea.split(","):
                t1 = time.time()
                out = np.zeros((size[1], size[0], 3))
                _draw(w, numbers(look, which, args.chunks, fog, args.haze, law, height), cam, size[0], size[1], out)
                label = f"{name}-{which}-{law}"
                picture = Image.fromarray((np.clip(out, 0.0, 1.0) * 255.0 + 0.5).astype(np.uint8))
                if args.sheet:
                    tiles.append((label, picture.resize((size[0] // 2, size[1] // 2), Image.LANCZOS)))
                else:
                    picture.save(f"{args.out}-{label}.png")
                print(f"{args.out}-{label} (tick {look.tick}, {args.chunks} chunks, fog {fog[0]:g}..{fog[1]:g}, the far "
                      f"sea {sky.look(which)['cloud']} from {height:g} over it, "
                      + (f"hazed over {args.haze:g}" if law == "haze" else "in the blocks' fog")
                      + f", {time.time() - t1:.0f} s)")
    if tiles:
        w, h = tiles[0][1].size
        rows = -(-len(tiles) // args.sheet)
        page = Image.new("RGB", (args.sheet * w, rows * h))
        for n, (label, tile) in enumerate(tiles):
            page.paste(tile, ((n % args.sheet) * w, (n // args.sheet) * h))
            ImageDraw.Draw(page).text(((n % args.sheet) * w + 6, (n // args.sheet) * h + 4), label, fill=(255, 255, 255))
        page.save(f"{args.out}-sheet.png")
        print(f"{args.out}-sheet.png: {len(tiles)} views, {args.sheet} to a row")


if __name__ == "__main__":
    main()
