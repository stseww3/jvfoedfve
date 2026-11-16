"""What the real client should show of the sea of clouds, worked out offline: a private aid of the
card sky/cloudsea for trying shapes and the laws of the join with the sky between two trips to the
real client.

    cd build && python -m scenes.obs_sky_cloudsea.preview --out ../renders/_wip/pre
        [--scene obs_sky_cloudsea] [--only v12,sunset_west | --only none] [--looks blue,glow]
        [--laws "a:1600,587,12;b:1600,28.6,8,60,150,8,12"] [--chunks 10] [--size 1280x720]
        [--plan] [--sheet 2] [--set "REACH=140.0" ...]

build/render.py draws a scene as the registry look showed it: one fog colour for the whole
picture, no afterglow, and where no block is, the fog colour down to the nadir. The map is shown
otherwise (the director's rulings of 11-16): the server sends blocks for ten chunks round a player,
and the look is drawn by the resource pack's shaders (sky/_shaders.py, A2's), which paint the sky
under the horizon as well. This draws that, with the shaders' own arithmetic taken from where the
shaders take it:

  - every colour is _shaders.Twin's, called for every pixel's direction: band() is what the fog
    takes a thing to, behind() what is painted behind it (the band above the horizon, the far sea
    below it), sky_at() what is seen where no block is. The stars and the comet are the offline
    renderer's, above the horizon only.
  - how much of them a block takes is Twin.apply()'s arithmetic: mood.fog_depth(), the air's haze
    and the mist that lies on the sea, towards the band; then mood.levelled(), by which what lies
    on the sea goes into the far sea painted behind it, or the game's own fog over the last tenth
    of the view distance, whichever is more, towards what is painted behind. _hazed() here is that
    arithmetic for the compiled loop; every run checks it against Twin.apply() on a few thousand
    made-up hits and stops if the two differ.
  - blocks: only the chunks the game has loaded round the camera at --chunks (10). No cloud layer:
    the shaders take it out.

--laws tries other numbers than sky/mood's, each set named and given as AIR,MIST,MIST_HEIGHT and,
if wanted, FOG_START,FOG_END,LEVEL_FULL,LEVEL_NONE after them. The pictures are named
<out>-<shot>-<look>-<law>.png; with --sheet N they are laid side by side, N to a row and half the
size, in one picture <out>-sheet.png instead. --plan adds <out>-plan.png: the sea from straight
above in the tones the blue hour gives it, without fog, and prints what it is made of; with --only
none nothing else is drawn, and no ray is traced. --set NAME=VALUE changes a constant of
sky/cloudsea for this run, to try a shape without a commit. They are no evidence: the card is
settled on the real client's pictures. This only says beforehand what those should show.
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
from scenes.obs.sky import _shaders as shaders
from scenes.obs.sky import mood as sky

# places in the array of numbers the compiled loop takes
Q_AIR, Q_MIST, Q_MIST_H, Q_EYE, Q_NEAR, Q_LOW, Q_FAR, Q_SIZE = 0, 1, 2, 3, 4, 6, 8, 10


@njit(cache=True)
def _depth(q, distance, rise):
    """mood.fog_depth() for one line of sight from the camera: the optical depth of the fog over
    `distance` blocks along a line that gains `rise` a block."""
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
def _hazed(q, r, g, b, t, dx, dy, dz, band, behind):
    """Twin.apply() for one hit, t away along the unit direction (dx, dy, dz): the colour (r, g, b)
    taken towards the band by the fog's depth, then towards what is painted behind it by
    mood.levelled() or by the game's fog at the rim of the view distance, whichever is more."""
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
    """raytrace.trace with the fog of the shaders: every hit is hazed as Twin.apply() has it, and
    where the ray meets nothing the painted sky itself is seen, with the stars and the comet on it
    above the horizon."""
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
            r, g, b = _hazed(q, r, g, b, at, dx, dy, dz, band, behind)
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
    """The unit direction of every pixel, row by row (x east, y up, z south)."""
    x = ((np.arange(width) + 0.5) / width * 2.0 - 1.0) * cam[12] * width / height
    y = (1.0 - (np.arange(height) + 0.5) / height * 2.0) * cam[12]
    d = cam[3:6][None, None, :] + x[None, :, None] * cam[6:9][None, None, :] + y[:, None, None] * cam[9:12][None, None, :]
    d = d.reshape(-1, 3)
    return np.ascontiguousarray(d / np.linalg.norm(d, axis=1, keepdims=True))


def numbers(look, eye):
    """The numbers the compiled loop takes: the fog's as sky/mood has them now, the camera's height
    over the sea's top, the rim of the view distance."""
    q = np.zeros(Q_SIZE)
    q[Q_AIR], q[Q_MIST], q[Q_MIST_H], q[Q_EYE] = sky.AIR, sky.MIST, sky.MIST_HEIGHT, eye
    q[Q_NEAR:Q_NEAR + 2] = sky.FOG_START, sky.FOG_END
    q[Q_LOW:Q_LOW + 2] = sky.LEVEL_FULL, sky.LEVEL_NONE
    q[Q_FAR:Q_FAR + 2] = look.far_start, look.far_end
    return q


def checked(q, twin, camera_y, n=4000):
    """_hazed() against Twin.apply() on made-up hits: colours, distances and directions at random,
    the nearly level lines among them."""
    g = np.random.default_rng(1)
    colour, distance = g.uniform(0.0, 1.0, (n, 3)), g.uniform(0.0, 400.0, n)
    d = g.normal(size=(n, 3))
    d[: n // 10, 1] *= 1e-5
    d /= np.linalg.norm(d, axis=1, keepdims=True)
    across = distance * np.hypot(d[:, 0], d[:, 2])
    rim = np.clip((np.maximum(across, distance * np.abs(d[:, 1])) - q[Q_FAR]) / (q[Q_FAR + 1] - q[Q_FAR]), 0.0, 1.0)
    band, behind = twin.band(d), twin.behind(d, camera_y)
    ours = np.array([_hazed(q, *colour[i], distance[i], *d[i], band[i], behind[i]) for i in range(n)])
    theirs = twin.apply(colour, distance, d, camera_y, rim)
    if not np.allclose(ours, theirs, rtol=0.0, atol=1e-9):
        raise SystemExit(f"preview: _hazed() and Twin.apply() differ by up to {np.abs(ours - theirs).max():g}")


class Far(shaders.Twin):
    """The twin with the far sea's face painted on it (cloudsea.far_colour), until sky/_shaders
    paints it itself. ``at`` is the camera in the world."""
    at = (0.0, 0.0, 0.0)

    def sea(self, d, camera_y):
        from scenes.obs.sky import cloudsea
        height = max(camera_y - self.n["sea_y"], 0.5)
        reach = height / np.maximum(-d[:, 1], 1e-5)
        colour = np.empty((len(d), 3))
        colour[...] = self.sea_colour
        down = d[:, 1] < 0.0
        colour[down] = cloudsea.far_colour(self.sea_colour, self.at[0] + d[down, 0] * reach[down],
                                           self.at[2] + d[down, 2] * reach[down], reach[down], height)
        return self._mix(colour, self.band(d), self.fogged(reach, camera_y, d[:, 1]))


def agreement(cells):
    """How the far sea's painting agrees with the blocks: over the columns of the open face (the
    top block at the face's own levels, no cloud column higher than those within six blocks), the
    tone build() gave against far_tone()."""
    from scenes.obs.common import blocks as B
    from scenes.obs.sky import cloudsea
    names = {name: i for i, name in enumerate(B.CLOUD)}
    top = {}
    for (x, y, z), state in cells.items():
        i = names.get(state.partition("[")[0].split(":")[-1])
        if i is not None and y > top.get((x, z), (-999, 0))[0]:
            top[(x, z)] = (y, i)
    cols = np.array(sorted(top))
    ys = np.array([top[tuple(c)][0] for c in cols])
    tones = np.array([top[tuple(c)][1] for c in cols])
    x0, z0 = cols.min(axis=0)
    high = np.zeros(tuple(cols.max(axis=0) - (x0, z0) + 1), dtype=bool)
    high[cols[:, 0] - x0, cols[:, 1] - z0] = ys > cloudsea.MEAN + 1
    near = np.zeros_like(high)
    for dx in range(-6, 7):
        for dz in range(-6, 7):
            near |= np.roll(np.roll(high, dx, axis=0), dz, axis=1)
    calm = ~near[cols[:, 0] - x0, cols[:, 1] - z0]
    theirs = cloudsea.far_tone(cols[calm, 0], cols[calm, 1])
    table = np.zeros((5, 5), dtype=int)
    np.add.at(table, (tones[calm], theirs), 1)
    print(f"the far sea against the blocks, {calm.sum()} columns of the open face (rows: the block's tone, columns: the painted)")
    for i, row in enumerate(table):
        print(f"  {i}: " + " ".join(f"{v:7d}" for v in row))
    print(f"  the same tone on {np.trace(table) / max(1, table.sum()):.1%}; painted shares "
          + ", ".join(f"{v:.3f}" for v in table.sum(axis=0) / max(1, table.sum())))


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
    ap.add_argument("--laws", default="",
                    help='the fog\'s numbers to try, "name:AIR,MIST,MIST_HEIGHT[,FOG_START,FOG_END,LEVEL_FULL,LEVEL_NONE];..." '
                         "(default: sky/mood's own)")
    ap.add_argument("--chunks", type=int, default=10, help="view distance in chunks")
    ap.add_argument("--size", default="1280x720")
    ap.add_argument("--fov", type=float, default=77.0)
    ap.add_argument("--plan", action="store_true", help="also write <out>-plan.png")
    ap.add_argument("--flat", action="store_true", help="the far sea as sky/_shaders paints it now: one colour")
    ap.add_argument("--agree", action="store_true", help="print how the far sea's painting agrees with the blocks")
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
    if args.agree:
        agreement(cells)
    if not names:
        return
    views = {s["name"]: s for s in base.shots()}
    names_of = ("AIR", "MIST", "MIST_HEIGHT", "FOG_START", "FOG_END", "LEVEL_FULL", "LEVEL_NONE")
    own = tuple(float(getattr(sky, key)) for key in names_of)
    laws = []
    for item in (item for item in args.laws.split(";") if item):
        name, _, values = item.partition(":")
        values = tuple(float(v) for v in values.split(","))
        if len(values) not in (3, 7):
            raise SystemExit(f"--laws {item}: three numbers ({', '.join(names_of[:3])}) or all seven ({', '.join(names_of)})")
        laws.append((name, values + own[len(values):]))
    laws = laws or [("mood", own)]
    place = (0, sky.GROUND_Y, 0)
    world = gamescene.Scene(assets, cells, entities, look_at(6000), place=place,
                            say=lambda s: print(f"{s} ({time.time() - t0:.0f} s)"))
    size = tuple(int(v) for v in args.size.split("x"))
    pixel = 2.0 * math.tan(math.radians(args.fov) / 2.0) / size[1]
    tiles = []
    for name in names:
        shot = views[name]
        cam = np.ascontiguousarray(world.camera(shot["pos"], shot.get("look_at"), 0.0, 0.0, args.fov), dtype=np.float64)
        there = loaded(shot["pos"], world.lo, world.grid.shape, args.chunks)
        eye = float(shot["pos"][1]) + sky.GROUND_Y                      # the camera's world height
        d = rays(cam, size[0], size[1])
        for which in args.looks.split(","):
            look = look_at(sky.tick(which))
            w = world.world(look, pixel)
            near = w.grid.copy()
            near[~there[:, None, :] & np.ones((1, near.shape[1], 1), dtype=bool)] = 0
            w = w._replace(grid=near)
            for law, values in laws:
                t1 = time.time()
                for key, value in zip(names_of, values):
                    setattr(sky, key, value)
                twin = (shaders.Twin if args.flat else Far)(which if which in sky.LOOKS else sky.DEFAULT)
                twin.at = (float(shot["pos"][0]) + place[0], eye, float(shot["pos"][2]) + place[2])
                q = numbers(look, eye - twin.n["sea_y"])
                checked(q, twin, eye)
                out = np.zeros((size[1], size[0], 3))
                _draw(w, q, cam, d, np.ascontiguousarray(twin.band(d)), np.ascontiguousarray(twin.behind(d, eye)),
                      np.ascontiguousarray(twin.sky_at(d, eye)), out)
                label = f"{name}-{which}-{law}" + ("-flat" if args.flat else "")
                picture = Image.fromarray((np.clip(out, 0.0, 1.0) * 255.0 + 0.5).astype(np.uint8))
                if args.sheet:
                    tiles.append((label, picture.resize((size[0] // 2, size[1] // 2), Image.LANCZOS)))
                else:
                    picture.save(f"{args.out}-{label}.png")
                print(f"{args.out}-{label} (tick {look.tick}, {args.chunks} chunks, the eye {q[Q_EYE]:g} over the sea; "
                      + ", ".join(f"{key} {value:g}" for key, value in zip(names_of, values)) + f"; {time.time() - t1:.0f} s)")
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
