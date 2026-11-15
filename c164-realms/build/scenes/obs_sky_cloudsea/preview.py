"""What the real client should show of this test scene, worked out offline: a private aid of the
card sky/cloudsea for trying fog laws and shapes between two trips to the real client.

    cd build && python -m scenes.obs_sky_cloudsea.preview --out ../renders/_wip/pre
        [--scene obs_sky_cloudsea] [--only v12,sunset_west] [--laws blue,b768,s768]
        [--clouds fancy,fast,off] [--chunks 12] [--size 1280x720]

build/render.py draws the blocks in fog but not the vanilla cloud layer, and this card is about
the line where the two meet. Here the layer is laid into the ray tracer's picture by the game's
own arithmetic (26.3; clouds.vsh, clouds.fsh, CloudRenderer, AtmosphericFogEnvironment):

  - fancy: every cloud cell is a box 12 x 4 x 12 whose underside is at cloud_height; a camera above
    the layer is shown the top faces. fast: one flat face per cell at cloud_height, in the top's
    colour. A sheet without gaps is one plane either way, and only that is drawn here: clouds.png
    is taken as closed.
  - the colour is cloud_color as it stands (no fog colour, no light map); the opacity is
    cloud_color's alpha times 1 - distance / min(cloudRange * 16, cloud_fog_end_distance), the
    distance measured from the eye. The layer is blended over what is drawn behind it: blocks below
    its top, or the fog colour and the stars where nothing is.
  - blocks: the ray tracer with the view distance set to 12 chunks (the board's; render.py takes
    14), so the wall of fog between 172.8 and 192 blocks is where the real client has it.

Not drawn, as in render.py: the afterglow and the fog's warm tint towards the west. The pictures
are named <out>-<shot>-<law>[-fast|-off].png. They are no evidence: the card is settled on the real
client's pictures. This only says beforehand what those should show.
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
from PIL import Image

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


@njit(cache=True, parallel=True)
def _draw(w, above, cam, width, height, sheet, out):
    """The ray tracer's picture with the cloud layer laid in. ``above`` is the same world without
    the cells below the layer's top; sheet = (the top's height in grid coordinates, r, g, b, alpha,
    the distance at which the layer has faded away, how far the layer is built; alpha 0: no layer)."""
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
            if alpha > 0.0 and dy < -1e-9 and cam[1] > plane:
                t = (cam[1] - plane) / -dy
                a = alpha * (1.0 - min(1.0, t / fade))
                if a > 0.0 and t * max(abs(dx), abs(dz)) <= built:
                    # the layer shows where the ray comes down to it before it meets a whole block,
                    # and through whatever is drawn above it leaves open (bars, a rail, a pane)
                    if _first_solid(w.grid, w.pal_flags, cam[0], cam[1], cam[2], dx, dy, dz, t) >= t:
                        ar, ag, ab = R.trace(above, cam[0], cam[1], cam[2], dx, dy, dz)
                        sr, sg, sb = R.sky_colour(w, dx, dy, dz)
                        if (ar != r or ag != g or ab != b) or (ar == sr and ag == sg and ab == sb):
                            r = a * sheet[1] + (1.0 - a) * r
                            g = a * sheet[2] + (1.0 - a) * g
                            b = a * sheet[3] + (1.0 - a) * b
            out[j, i, 0] = r
            out[j, i, 1] = g
            out[j, i, 2] = b


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--scene", default="obs_sky_cloudsea")
    ap.add_argument("--out", required=True, help="prefix of the pictures: <out>-<shot>-<law>.png")
    ap.add_argument("--only", help="comma separated shot names (default: the scene's LAW_VIEWS)")
    ap.add_argument("--laws", default="blue", help="comma separated: laws of the scene's mood, looks or trials of the sky's")
    ap.add_argument("--clouds", default="fancy", help="comma separated: fancy, fast, off")
    ap.add_argument("--chunks", type=int, default=12, help="view distance in chunks")
    ap.add_argument("--size", default="1280x720")
    ap.add_argument("--fov", type=float, default=77.0)
    args = ap.parse_args()
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)

    t0 = time.time()
    scene = importlib.import_module(f"scenes.{args.scene}")
    look_mod = importlib.import_module(f"scenes.{args.scene}.mood")
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

    place = (0, 200, 0)
    world = gamescene.Scene(assets, cells, entities, look_at(6000), place=place,
                            say=lambda s: print(f"{s} ({time.time() - t0:.0f} s)"))
    views = {s["name"]: s for s in base.shots()}
    names = args.only.split(",") if args.only else list(base.LAW_VIEWS)
    size = tuple(int(v) for v in args.size.split("x"))
    pixel = 2.0 * math.tan(math.radians(args.fov) / 2.0) / size[1]
    for name in names:
        shot = views[name]
        cam = np.ascontiguousarray(world.camera(shot["pos"], shot.get("look_at"), 0.0, 0.0, args.fov), dtype=np.float64)
        for law in args.laws.split(","):
            tick = laws.tick(law)
            look = look_at(tick)
            w = world.world(look, pixel)
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
                _draw(w, w._replace(grid=grid), cam, size[0], size[1], sheet, out)
                path = f"{args.out}-{name}-{law}" + ("" if clouds == "fancy" else f"-{clouds}") + ".png"
                Image.fromarray((np.clip(out, 0.0, 1.0) * 255.0 + 0.5).astype(np.uint8)).save(path)
                print(f"{path} (tick {tick}, fog {look.fog_start:g}..{look.fog_end:g}, layer "
                      f"alpha {colour[3]:.2f} to {sheet[5]:g}, {time.time() - t1:.0f} s)")


if __name__ == "__main__":
    main()
