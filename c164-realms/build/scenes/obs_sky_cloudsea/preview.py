"""What the real client should show of the sea of clouds, worked out offline: a private aid of the
card sky/cloudsea for trying shapes and the laws of the join with the sky between two trips to the
real client.

    cd build && python -m scenes.obs_sky_cloudsea.preview --out ../renders/_wip/pre
        [--scene obs_sky_cloudsea] [--only v12,sunset_west | --only none] [--looks blue,glow]
        [--laws "a:1600,587,12;b:1600,28.6,8"] [--short 60,150] [--skin 8,12] [--chunks 10]
        [--size 1280x720] [--plan] [--sheet 2] [--set "REACH=140.0" ...]

build/render.py draws a scene as the registry look showed it: one fog colour for the whole
picture, no afterglow, and where no block is, the fog colour down to the nadir. The map is shown
otherwise (the director's rulings of 11-16): the server sends blocks for ten chunks round a player,
and the look is drawn by the resource pack's shaders (sky/_shaders.py, A2's), which paint the sky
under the horizon as well. This draws that, with the shaders' own arithmetic taken from where the
shaders take it:

  - how much fog lies on a thing: mood.fog_depth(), the air's haze and the mist that lies on the
    sea, along the line of sight (_depth() here is the same formula for the compiled loop, checked
    against mood.fog_depth() at every start). --laws tries other numbers for it, each set named
    and given as AIR,MIST,MIST_HEIGHT.
  - every colour: _shaders.Twin, called for every pixel's direction: band() is what the fog takes
    a thing to, behind() what is painted behind it (the band above the horizon, the far sea below
    it), sky_at() what is seen where no block is. The stars and the comet are the offline
    renderer's, above the horizon only.
  - the short law, for what lies on the sea: from --short's first number of blocks to its second
    a block is taken into what is painted behind it, whole up to --skin's first number of blocks
    over the sea's top and not at all from its second on. The block clouds end in the painted sea
    by it, and nothing that stands over the sea is touched. (A2 writes it into sky/mood.py as
    levelled(); until that has come this is the understanding of it.)
  - blocks: only the chunks the game has loaded round the camera at --chunks (10), and the game's
    own fog over the last tenth of that distance, into what is painted behind. No cloud layer:
    the shaders take it out.

The pictures are named <out>-<shot>-<look>-<law>.png; with --sheet N they are laid side by side, N
to a row and half the size, in one picture <out>-sheet.png instead. --plan adds <out>-plan.png:
the sea from straight above in the tones the blue hour gives it, without fog, and prints what it
is made of; with --only none nothing else is drawn, and no ray is traced. --set NAME=VALUE changes
a constant of sky/cloudsea for this run, to try a shape without a commit. They are no evidence: the
card is settled on the real client's pictures. This only says beforehand what those should show.
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

SHORT = (60.0, 150.0)       # the short law: none nearer than the first, whole at the second
SKIN = (8.0, 12.0)          # ... whole on what is no higher than the first over the sea's top, none from the second
# places in the array of numbers the compiled loop takes
Q_AIR, Q_MIST, Q_MIST_H, Q_HEIGHT, Q_SEA, Q_SHORT, Q_SKIN, Q_FAR, Q_SIZE = 0, 1, 2, 3, 4, 5, 7, 9, 11


@njit(cache=True)
def _depth(q, distance, rise):
    """mood.fog_depth() for one line of sight from the camera (main() checks the two against each
    other): the optical depth of the fog over `distance` blocks along a line that gains `rise` a
    block."""
    height = q[Q_HEIGHT]
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
def _behind(q, t, y, dx, dy, dz):
    """The share of what is painted behind it in a block t away, at grid height y: the short law
    for what lies on the sea, and the game's own fog at the rim of the view distance."""
    s = 0.0
    if q[Q_SHORT + 1] > q[Q_SHORT] and t > q[Q_SHORT]:
        s = min(1.0, (t - q[Q_SHORT]) / (q[Q_SHORT + 1] - q[Q_SHORT]))
        s *= min(1.0, max(0.0, (q[Q_SKIN + 1] - (y - q[Q_SEA])) / (q[Q_SKIN + 1] - q[Q_SKIN])))
    c = t * max(math.sqrt(dx * dx + dz * dz), abs(dy))
    e = 0.0
    if c > q[Q_FAR]:
        e = 1.0 if c >= q[Q_FAR + 1] else (c - q[Q_FAR]) / (q[Q_FAR + 1] - q[Q_FAR])
    return 1.0 - (1.0 - s) * (1.0 - e)


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
def _trace(w, q, px, py, pz, dx, dy, dz, band, behind, sky):
    """raytrace.trace with the fog of the shaders: every hit is taken towards the band of the
    ray's direction by the fog's depth and towards what is painted behind it by the short law and
    the rim; where the ray meets nothing the painted sky itself is seen, with the stars and the
    comet on it above the horizon."""
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
    sr, sg, sb = sky[0], sky[1], sky[2]
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
            f = 1.0 - math.exp(-_depth(q, at, dy))
            k = _behind(q, at, py + dy * at, dx, dy, dz)
            r, g, b = r + (band[0] - r) * f, g + (band[1] - g) * f, b + (band[2] - b) * f
            cr += trans * alpha * (r + (behind[0] - r) * k)
            cg += trans * alpha * (g + (behind[1] - g) * k)
            cb += trans * alpha * (b + (behind[2] - b) * k)
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
def _draw(w, q, cam, rays, band, behind, sky, out):
    height, width = out.shape[0], out.shape[1]
    for j in prange(height):
        for i in range(width):
            n = j * width + i
            r, g, b = _trace(w, q, cam[0], cam[1], cam[2], rays[n, 0], rays[n, 1], rays[n, 2], band[n], behind[n], sky[n])
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


def numbers(look, height, sea_y, short, skin):
    """The numbers the compiled loop takes: the fog's as sky/mood has them now, how high the
    camera is over the sea's top, the sea's top in the grid, the short law, the rim."""
    q = np.zeros(Q_SIZE)
    q[Q_AIR], q[Q_MIST], q[Q_MIST_H] = sky.AIR, sky.MIST, sky.MIST_HEIGHT
    q[Q_HEIGHT], q[Q_SEA] = max(height, 0.0), sea_y
    q[Q_SHORT:Q_SHORT + 2] = short
    q[Q_SKIN:Q_SKIN + 2] = skin
    q[Q_FAR:Q_FAR + 2] = look.far_start, look.far_end
    return q


def checked(q):
    """_depth() against mood.fog_depth() on a thousand lines of sight."""
    g = np.random.default_rng(1)
    distance, rise = g.uniform(0.0, 600.0, 1000), g.uniform(-1.0, 1.0, 1000)
    rise[:40] = g.uniform(-2e-5, 2e-5, 40)
    ours = np.array([_depth(q, d, r) for d, r in zip(distance, rise)])
    theirs = sky.fog_depth(distance, q[Q_HEIGHT], rise)
    if not np.allclose(ours, theirs, rtol=1e-9, atol=1e-12):
        raise SystemExit(f"preview: _depth() and mood.fog_depth() differ by up to {np.abs(ours - theirs).max():g}")


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
    ap.add_argument("--laws", default="", help='the fog\'s numbers to try, "name:AIR,MIST,MIST_HEIGHT;..." '
                                               "(default: sky/mood's own)")
    ap.add_argument("--short", default=f"{SHORT[0]:g},{SHORT[1]:g}", help="the short law: from, to (0,0: none)")
    ap.add_argument("--skin", default=f"{SKIN[0]:g},{SKIN[1]:g}",
                    help="... whole up to this high over the sea's top, none from this high")
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
    short = tuple(float(v) for v in args.short.split(","))
    skin = tuple(float(v) for v in args.skin.split(","))
    laws = [(name, tuple(float(v) for v in values.split(",")))
            for name, _, values in (item.partition(":") for item in args.laws.split(";") if item)]
    laws = laws or [("mood", (sky.AIR, sky.MIST, sky.MIST_HEIGHT))]
    place = (0, sky.GROUND_Y, 0)
    world = gamescene.Scene(assets, cells, entities, look_at(6000), place=place,
                            say=lambda s: print(f"{s} ({time.time() - t0:.0f} s)"))
    size = tuple(int(v) for v in args.size.split("x"))
    pixel = 2.0 * math.tan(math.radians(args.fov) / 2.0) / size[1]
    sea_y = float(sky.CLOUD_TOP - world.lo[1])                          # the sea's top in the grid
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
            for law, (air, mist, mist_height) in laws:
                t1 = time.time()
                sky.AIR, sky.MIST, sky.MIST_HEIGHT = air, mist, mist_height
                twin = shaders.Twin(which if which in sky.LOOKS else sky.DEFAULT)
                q = numbers(look, eye - twin.n["sea_y"], sea_y, short, skin)
                checked(q)
                out = np.zeros((size[1], size[0], 3))
                _draw(w, q, cam, d, np.ascontiguousarray(twin.band(d)), np.ascontiguousarray(twin.behind(d, eye)),
                      np.ascontiguousarray(twin.sky_at(d, eye)), out)
                label = f"{name}-{which}-{law}"
                picture = Image.fromarray((np.clip(out, 0.0, 1.0) * 255.0 + 0.5).astype(np.uint8))
                if args.sheet:
                    tiles.append((label, picture.resize((size[0] // 2, size[1] // 2), Image.LANCZOS)))
                else:
                    picture.save(f"{args.out}-{label}.png")
                print(f"{args.out}-{label} (tick {look.tick}, {args.chunks} chunks, the eye {q[Q_HEIGHT]:g} over the sea; "
                      f"fog: air {air:g}, mist {mist:g} thinning by {mist_height:g}; short law {short[0]:g}..{short[1]:g} "
                      f"up to {skin[0]:g}..{skin[1]:g} over the sea, {time.time() - t1:.0f} s)")
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
