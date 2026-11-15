"""What the real client should show of this test scene, worked out offline: a private aid of the
card sky/cloudsea for trying fog laws and shapes between two trips to the real client.

    cd build && python -m scenes.obs_sky_cloudsea.preview --out ../renders/_wip/pre
        [--scene obs_sky_cloudsea] [--mood <scene>] [--only v12,sunset_west] [--laws blue,b768,k0]
        [--clouds fancy,fast,off] [--chunks 12] [--size 1280x720] [--plan] [--sheet 3]
        [--set "SEEN=(170, 185)" ...]

build/render.py draws the blocks in fog but not the vanilla cloud layer, and this card is about
the line where the two meet. Here the layer is laid into the ray tracer's picture by the game's
own arithmetic (26.3; clouds.vsh, clouds.fsh, CloudRenderer, AtmosphericFogEnvironment, SkyRenderer):

  - fancy: every cloud cell is a box 12 x 4 x 12 whose underside is at cloud_height; a camera above
    the layer is shown the top faces. fast: one flat face per cell at cloud_height, in the top's
    colour. A sheet without gaps is one plane either way, and only that is drawn here: clouds.png
    is taken as closed.
  - the colour is cloud_color as it stands (no fog colour, no light map); the opacity is
    cloud_color's alpha times 1 - distance / min(cloudRange * 16, cloud_fog_end_distance), the
    distance measured from the eye. The layer is blended over what is drawn behind it: blocks below
    its top, or the fog colour, the afterglow and the stars where nothing is.
  - the fog colour is one colour for the whole frame: the attribute, drawn towards the afterglow's
    colour as far as the camera faces it (the x of its forward vector times the colour's alpha),
    then towards the sky colour. So a camera that looks west has warm fog, and the blocks in the
    wall of fog and the emptiness under the horizon take that.
  - the afterglow is a shallow cone of sixteen triangles round the camera: its tip on the horizon
    where the sun set, with the colour's full alpha, its rim 120 out with none, lifted over the
    horizon on the tip's side and sunk under it on the far side. Under the horizon the cone lies
    below the camera, so whoever looks down sees the afterglow over the emptiness: a good half of
    its alpha straight down, all of it at the western horizon.
  - blocks: the ray tracer with the view distance set to 12 chunks (the board's; render.py takes
    14), so the wall of fog between 172.8 and 192 blocks is where the real client has it, and only
    the chunks the game would have loaded round the camera are drawn (ChunkTrackingView).

render.py draws neither the afterglow nor the fog's warm tint; both are laid in here, so a west
facing picture is not the one render.py gives. The two formulas were checked against S1's real V12
of the master scene (his looks/blue and looks/thin_soft at f824e60): at four points of the
emptiness under the horizon they give the picture's colour within two levels a channel (#7f5462
for #7f5364 top left, #624968 for #624968 top right). The pictures
are named <out>-<shot>-<law>[-fast|-off].png; with --sheet N they are laid side by side, N to a
row and half the size, in one picture <out>-sheet.png instead. --plan adds <out>-plan.png: the
sea from straight above without fog, the sheet's face and what stands out of it on the left, the
blocks alone on the right, with the rings where the board's aerial camera loses the blocks.
--set NAME=VALUE changes a constant of sky/cloudsea for this run, to try a shape without a commit.
They are no evidence: the card is settled on the real client's pictures. This only says beforehand
what those should show.
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

CLOUD_RANGE = 128           # the option's default and its upper end: the layer is built 2048 blocks out
CELL_HEIGHT = 4.0
KEYS = {"cloud_color": "#ccffffff", "cloud_height": 192.33, "cloud_fog_end_distance": 2048.0}


def sheet_at(tick, dimension, biome, lines):
    """cloud_color (r, g, b, a), cloud_height and cloud_fog_end_distance at a tick, through the same
    layers as gamelook.attributes(): the dimension, the biome, the timelines in the tag's order."""
    out = {k: gamelook._value(v) for k, v in KEYS.items()}
    for layer in (dimension.get("attributes", {}), biome.get("attributes", {})):
        for key, v in layer.items():
            name = key[len(gamelook.VISUAL):]
            if key.startswith(gamelook.VISUAL) and name in out:
                if isinstance(v, dict) and "argument" in v:
                    out[name] = gamelook._apply(out[name], v.get("modifier"), gamelook._value(v["argument"]))
                else:
                    out[name] = gamelook._value(v)
    for line in lines:
        for key, track in line.get("tracks", {}).items():
            name = key[len(gamelook.VISUAL):]
            if key.startswith(gamelook.VISUAL) and name in out:
                arg = gamelook._sample(track, tick, line.get("period_ticks", 24000))
                out[name] = gamelook._apply(out[name], track.get("modifier"), arg)
    return out


@njit(cache=True)
def _first_solid(grid, flags, px, py, pz, dx, dy, dz, reach):
    """How far along the ray the first whole opaque block lies; R.BIG if there is none within
    ``reach`` or inside the grid."""
    nx, ny, nz = grid.shape
    t0, t1 = 0.0, reach
    if abs(dx) > 1e-12:
        a, b = (0.0 - px) / dx, (nx - px) / dx
        t0, t1 = max(t0, min(a, b)), min(t1, max(a, b))
    elif px < 0.0 or px >= nx:
        return R.BIG
    if abs(dy) > 1e-12:
        a, b = (0.0 - py) / dy, (ny - py) / dy
        t0, t1 = max(t0, min(a, b)), min(t1, max(a, b))
    elif py < 0.0 or py >= ny:
        return R.BIG
    if abs(dz) > 1e-12:
        a, b = (0.0 - pz) / dz, (nz - pz) / dz
        t0, t1 = max(t0, min(a, b)), min(t1, max(a, b))
    elif pz < 0.0 or pz >= nz:
        return R.BIG
    if t0 >= t1:
        return R.BIG
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
    while t < t1:
        pal = grid[cx, cy, cz]
        if pal != 0 and flags[pal] & R.OPAQUE:
            return t
        if tmx <= tmy and tmx <= tmz:
            t = tmx
            cx += stx
            tmx += tdx
            if cx < 0 or cx >= nx:
                break
        elif tmy <= tmz:
            t = tmy
            cy += sty
            tmy += tdy
            if cy < 0 or cy >= ny:
                break
        else:
            t = tmz
            cz += stz
            tmz += tdz
            if cz < 0 or cz >= nz:
                break
    return R.BIG


def frame_fog(look, forward, chunks):
    """The fog colour of a frame whose camera looks along ``forward`` (a unit vector), and the
    afterglow as (r, g, b, alpha, the x of the side it lies on); AtmosphericFogEnvironment.getBaseColor."""
    a = look.attrs
    fog = np.array(a["fog_color"][:3], dtype=np.float64)
    side = -1.0 if math.sin(math.radians(look.sun_angle)) > 0.0 else 1.0
    glow = np.zeros(5)
    glow[4] = side
    if look.sunset is not None:
        glow[:4] = look.sunset
        facing = float(forward[0]) * side
        if facing > 0.0 and chunks >= 4:
            fog = fog + (glow[:3] - fog) * facing * glow[3]
    e = min(float(a["sky_fog_end_distance"]) / 16.0, float(chunks))
    mix = 1.0 - (0.25 + 0.75 * min(1.0, max(0.0, e / 32.0))) ** 0.25
    return fog + (np.array(a["sky_color"][:3], dtype=np.float64) - fog) * mix, glow


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


@njit(cache=True, parallel=True)
def _draw(w, above, cam, width, height, sheet, glow, out):
    """The ray tracer's picture with the afterglow and the cloud layer laid in. ``above`` is the same
    world without the cells below the layer's top; sheet = (the top's height in grid coordinates,
    r, g, b, alpha, the distance at which the layer has faded away, how far the layer is built;
    alpha 0: no layer); glow = (r, g, b, alpha, side) of the afterglow."""
    half = cam[12]
    aspect = width / height
    plane, alpha, fade, built = sheet[0], sheet[4], sheet[5], sheet[6]
    for j in prange(height):
        for i in range(width):
            x = ((i + 0.5) / width * 2.0 - 1.0) * half * aspect
            y = (1.0 - (j + 0.5) / height * 2.0) * half
            dx = cam[3] + x * cam[6] + y * cam[9]
            dy = cam[4] + x * cam[7] + y * cam[10]
            dz = cam[5] + x * cam[8] + y * cam[11]
            n = math.sqrt(dx * dx + dy * dy + dz * dz)
            dx, dy, dz = dx / n, dy / n, dz / n
            r, g, b = R.trace(w, cam[0], cam[1], cam[2], dx, dy, dz)
            sr, sg, sb = R.sky_colour(w, dx, dy, dz)
            r0, g0, b0 = r, g, b
            # the afterglow lies behind everything: a block that the fog has taken whole is drawn
            # over it in the fog's colour, and only the open sky shows it
            if (glow[3] > 0.0 and r == sr and g == sg and b == sb
                    and _first_solid(w.grid, w.pal_flags, cam[0], cam[1], cam[2], dx, dy, dz, 8192.0) >= R.BIG):
                f = glow[3] * _afterglow(dx, dy, dz, glow[3], glow[4])
                r, g, b = r + (glow[0] - r) * f, g + (glow[1] - g) * f, b + (glow[2] - b) * f
            if alpha > 0.0 and dy < -1e-9 and cam[1] > plane:
                t = (cam[1] - plane) / -dy
                a = alpha * (1.0 - min(1.0, t / fade))
                if a > 0.0 and t * max(abs(dx), abs(dz)) <= built:
                    # the layer shows where the ray comes down to it before it meets a whole block,
                    # and through whatever is drawn above it leaves open (bars, a rail, a pane)
                    if _first_solid(w.grid, w.pal_flags, cam[0], cam[1], cam[2], dx, dy, dz, t) >= t:
                        ar, ag, ab = R.trace(above, cam[0], cam[1], cam[2], dx, dy, dz)
                        if (ar != r0 or ag != g0 or ab != b0) or (ar == sr and ag == sg and ab == sb):
                            r = a * sheet[1] + (1.0 - a) * r
                            g = a * sheet[2] + (1.0 - a) * g
                            b = a * sheet[3] + (1.0 - a) * b
            out[j, i, 0] = r
            out[j, i, 1] = g
            out[j, i, 2] = b


def loaded(pos, lo, shape, chunks):
    """Which columns of the grid the game has loaded round a camera (ChunkTrackingView.isWithinDistance)."""
    cx, cz = math.floor(pos[0] / 16.0), math.floor(pos[2] / 16.0)
    dx = np.maximum(np.abs(np.floor((np.arange(shape[0]) + lo[0]) / 16.0) - cx) - 1, 0)
    dz = np.maximum(np.abs(np.floor((np.arange(shape[2]) + lo[2]) / 16.0) - cz) - 1, 0)
    return dx[:, None] ** 2 + dz[None, :] ** 2 < chunks * chunks


def plan(cells, look, path, aerial, chunks, scale=2):
    """The sea from straight above, without fog: left the sheet's face (the tone it shows) with what
    stands out of it, right the deck and what stands on it (the game's clouds switched off)."""
    from scenes.obs.common import blocks as B
    from scenes.obs.common import palette as P
    from scenes.obs.sky import cloudsea
    lit = look.lightmap[15][0]
    tones = [np.clip(np.array(P.colour("cloud", i)) / 255.0 * lit, 0.0, 1.0) for i in range(len(B.CLOUD))]
    index = {name: i for i, name in enumerate(B.CLOUD)}
    x0, z0, nx, nz = cloudsea._grid()
    high = np.full((2, nx, nz), -10 ** 6)
    tone = np.full((2, nx, nz), -1)
    counts = {"over the face": 0, "bodies": 0, "deck": 0}
    for (x, y, z), state in cells.items():
        i, j = x - x0, z - z0
        if not (0 <= i < nx and 0 <= j < nz):
            continue
        t = index.get(state.partition("[")[0].split(":")[-1], -2)
        if t >= 0:
            counts["over the face" if y >= cloudsea.FACE else "bodies" if y > cloudsea.DECK_Y else "deck"] += 1
        for k in (0, 1):
            if (k == 1 or t < 0 or y >= cloudsea.FACE) and y > high[k, i, j]:
                high[k, i, j], tone[k, i, j] = y, t
    face = np.array(P.colour("cloud", 3)) / 255.0 * lit
    out = np.zeros((nx, 2 * nz, 3))
    for k in (0, 1):
        img = np.empty((nx, nz, 3))
        img[...] = face if k == 0 else np.array([0.02, 0.02, 0.05])
        land = (tone[k] == -2) & (high[k] >= (cloudsea.FACE if k == 0 else cloudsea.DECK_Y))
        img[land] = (0.10, 0.10, 0.13)
        for t, colour in enumerate(tones):
            img[tone[k] == t] = colour
        X, Z = np.meshgrid(np.arange(nx) + x0, np.arange(nz) + z0, indexing="ij")
        ring = np.hypot(X + 0.5 - aerial[0], Z + 0.5 - aerial[2])
        for r, colour in ((chunks * 16.0 * 0.9, (0.9, 0.6, 0.2)), (chunks * 16.0, (0.9, 0.3, 0.2))):
            img[np.abs(ring - r) < 0.5] = colour
        edge = loaded(aerial, (x0, 0, z0), (nx, 0, nz), chunks)
        rim = edge & ~(np.roll(edge, 1, 0) & np.roll(edge, -1, 0) & np.roll(edge, 1, 1) & np.roll(edge, -1, 1))
        img[rim] = (0.9, 0.9, 0.3)
        out[:, k * nz:(k + 1) * nz] = img
    # north up, west left: the picture's rows run along z, its columns along x
    halves = [np.transpose(out[:, k * nz:(k + 1) * nz], (1, 0, 2)) for k in (0, 1)]
    img = np.concatenate(halves, axis=1)
    img = np.repeat(np.repeat(img, scale, axis=0), scale, axis=1)
    Image.fromarray((np.clip(img, 0.0, 1.0) * 255.0 + 0.5).astype(np.uint8)).save(path)
    print(f"{path}: {counts}, x {x0}..{x0 + nx - 1}, z {z0}..{z0 + nz - 1}, {scale} px a block; orange: the "
          f"aerial camera's wall of fog begins, red: it is whole, yellow: its last loaded chunks")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--scene", default="obs_sky_cloudsea")
    ap.add_argument("--mood", help="the scene whose look is drawn (default: the scene's own): the master scene "
                                   "knows no laws, --scene obs --mood obs_sky_cloudsea draws it under them")
    ap.add_argument("--out", required=True, help="prefix of the pictures: <out>-<shot>-<law>.png")
    ap.add_argument("--only", help="comma separated shot names (default: the scene's LAW_VIEWS)")
    ap.add_argument("--laws", default="blue", help="comma separated: laws of the scene's mood, looks or trials of the sky's")
    ap.add_argument("--clouds", default="fancy", help="comma separated: fancy, fast, off")
    ap.add_argument("--chunks", type=int, default=12, help="view distance in chunks")
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
    look_mod = importlib.import_module(f"scenes.{args.mood or args.scene}.mood")
    base = importlib.import_module("scenes.obs_sky_cloudsea")
    laws = importlib.import_module("scenes.obs_sky_cloudsea.mood")
    canvas = scene.build()
    cells, entities = dict(canvas.b), canvas.entities
    pack = tempfile.mkdtemp(prefix="c164pack-")
    atexit.register(shutil.rmtree, pack, ignore_errors=True)
    offline.write_pack(args.scene, pack)
    assets = Assets(os.path.join(offline.ROOT, "client26", "versions", "26.3", "26.3.jar"), [pack])
    biome = look_mod.BIOMES[getattr(scene, "BIOME", sorted(look_mod.BIOMES)[0])]
    dimension = assets.json(f"{offline.DATA}dimension_type/overworld.json")
    lines = offline.timelines(assets) + [look_mod.TIMELINES[k] for k in sorted(look_mod.TIMELINES)]

    def look_at(tick):
        return gamelook.Look(tick, dimension, biome, lines, render_chunks=args.chunks)

    views = {s["name"]: s for s in base.shots()}
    if args.plan:
        plan(cells, look_at(laws.tick("blue")), f"{args.out}-plan.png", views["v12"]["pos"], args.chunks)
    place = (0, 200, 0)
    world = gamescene.Scene(assets, cells, entities, look_at(6000), place=place,
                            say=lambda s: print(f"{s} ({time.time() - t0:.0f} s)"))
    names = args.only.split(",") if args.only else list(base.LAW_VIEWS)
    size = tuple(int(v) for v in args.size.split("x"))
    pixel = 2.0 * math.tan(math.radians(args.fov) / 2.0) / size[1]
    tiles = []
    for name in names:
        shot = views[name]
        cam = np.ascontiguousarray(world.camera(shot["pos"], shot.get("look_at"), 0.0, 0.0, args.fov), dtype=np.float64)
        there = loaded(shot["pos"], world.lo, world.grid.shape, args.chunks)
        for law in args.laws.split(","):
            tick = laws.tick(law)
            look = look_at(tick)
            forward = np.array(shot["look_at"], dtype=np.float64) - np.array(shot["pos"], dtype=np.float64)
            look.fog, glow = frame_fog(look, forward / np.linalg.norm(forward), args.chunks)
            w = world.world(look, pixel)
            near = w.grid.copy()
            near[~there[:, None, :] & np.ones((1, near.shape[1], 1), dtype=bool)] = 0
            w = w._replace(grid=near)
            got = sheet_at(tick, dimension, biome, lines)
            for clouds in args.clouds.split(","):
                t1 = time.time()
                top = got["cloud_height"] + (CELL_HEIGHT if clouds == "fancy" else 0.0) - place[1] - float(world.lo[1])
                grid = w.grid.copy()
                grid[:, :max(0, int(math.floor(top + 1e-6))), :] = 0
                colour = got["cloud_color"]
                sheet = np.array([top, colour[0], colour[1], colour[2], 0.0 if clouds == "off" else colour[3],
                                  min(CLOUD_RANGE * 16.0, got["cloud_fog_end_distance"]), CLOUD_RANGE * 16.0])
                out = np.zeros((size[1], size[0], 3))
                _draw(w, w._replace(grid=grid), cam, size[0], size[1], sheet, glow, out)
                label = f"{name}-{law}" + ("" if clouds == "fancy" else f"-{clouds}")
                picture = Image.fromarray((np.clip(out, 0.0, 1.0) * 255.0 + 0.5).astype(np.uint8))
                if args.sheet:
                    tiles.append((label, picture.resize((size[0] // 2, size[1] // 2), Image.LANCZOS)))
                else:
                    picture.save(f"{args.out}-{label}.png")
                print(f"{args.out}-{label} (tick {tick}, fog {look.fog_start:g}..{look.fog_end:g}, layer "
                      f"alpha {colour[3]:.2f} to {sheet[5]:g}, {time.time() - t1:.0f} s)")
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
