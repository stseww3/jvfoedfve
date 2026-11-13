#!/usr/bin/env python3
"""Pictures of a scene as the game would draw it, made without the game.

    render.py skyobs --shots shots.json --out /tmp/skyobs [--only hero,low] [--size 1280x720]

Takes the same shot lists as tools/shoot.py (camera positions in scene coordinates, "time" per
shot). The scene's resource pack is written to a temporary directory and read back together with
the game's own files from the client jar, so blocks show the game's models and textures, display
entities show the scene's models, and light, shade, fog and sky follow the game's arithmetic
(artkit/raytrace.py). The first run compiles the ray tracer, which takes a few minutes.

What it does not draw: particles, block entities (chests, signs, banners), mobs, clouds of the
vanilla kind, and the slope of running water. Final pictures still come from the game; this is for
looking at a change before the game is started, or when it cannot be.
"""
import argparse
import importlib
import json
import os
import pickle
import sys
import tempfile
import time

from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from artkit import gamelook, gamescene, water  # noqa: E402
from artkit import models as M  # noqa: E402
from artkit.gameassets import Assets  # noqa: E402

ROOT = os.environ.get("MC_ROOT", "/agent/realms-study")
DATA = "data/minecraft/"


def write_pack(scene_name, out):
    """The same files makepack.py writes."""
    props = importlib.import_module(f"scenes.{scene_name}.props")
    M.write_pack(out, list(props.build_models().values()))
    extra = getattr(importlib.import_module(f"scenes.{scene_name}"), "write_pack", None)
    if extra:
        extra(out)


def timelines(assets, tag="in_overworld"):
    """The dimension's timelines in the order of its tag (vanilla data, read from the jar)."""
    out = []
    for value in assets.json(f"{DATA}tags/timeline/{tag}.json")["values"]:
        if value.startswith("#"):
            out += timelines(assets, value.partition(":")[2])
        else:
            out.append(assets.json(f"{DATA}timeline/{value.partition(':')[2]}.json"))
    return out


def tick_of(when, markers):
    if isinstance(when, (int, float)):
        return int(when)
    if str(when).lstrip("-").isdigit():
        return int(when)
    mark = markers[f"minecraft:{when}"]
    return int(mark["ticks"] if isinstance(mark, dict) else mark)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("scene")
    ap.add_argument("--shots", required=True, help="shot list as used by tools/shoot.py")
    ap.add_argument("--out", required=True, help="prefix of the pictures: <out>-<shot name>.png")
    ap.add_argument("--only", help="comma separated shot names")
    ap.add_argument("--size", default="1280x720")
    ap.add_argument("--ss", type=int, default=1,
                    help="rays per pixel along each side; 1 is what the game does (no smoothing of edges)")
    ap.add_argument("--fov", type=float, default=77.0,
                    help="vertical field of view; 77 is what tools/shoot.py gets: the option's 70, a tenth wider "
                         "because the camera player is flying")
    ap.add_argument("--time", help="take every shot at this time instead of its own")
    ap.add_argument("--jar", default=os.path.join(ROOT, "client26", "versions", "26.3", "26.3.jar"))
    ap.add_argument("--pack", help="resource pack directory to read instead of writing the scene's afresh")
    ap.add_argument("--place", type=int, nargs=3, default=[0, 200, 0], metavar=("X", "Y", "Z"),
                    help="where the scene stands in the world (decides block variants and plant offsets)")
    ap.add_argument("--still", action="store_true", help="draw the water as placed, without letting it run")
    ap.add_argument("--canvas", help="pickle of the built scene: read it if it exists, else build and write it")
    args = ap.parse_args()

    t0 = time.time()
    scene = importlib.import_module(f"scenes.{args.scene}")
    if args.canvas and os.path.exists(args.canvas):
        with open(args.canvas, "rb") as fh:
            saved = pickle.load(fh)
        cells, entities = saved["b"], saved["entities"]
    else:
        canvas = scene.build()
        cells, entities = canvas.b, canvas.entities
        if args.canvas:
            with open(args.canvas, "wb") as fh:
                pickle.dump({"b": cells, "entities": entities}, fh, protocol=4)
    print(f"{len(cells)} blocks, {len(entities)} entities ({time.time() - t0:.0f} s)")

    pack = args.pack
    if not pack:
        pack = tempfile.mkdtemp(prefix="c164pack-")
        write_pack(args.scene, pack)
        print(f"resource pack written to {pack} ({time.time() - t0:.0f} s)")
    assets = Assets(args.jar, [pack])

    cells = dict(cells)
    if not args.still:
        floor = min(k[1] for k in cells) - 1

        class _Canvas:
            b = cells

        flow = water.run(_Canvas, floor)
        for cell, amount in flow.w.items():
            cells[cell] = "water[level=8]" if amount == water.FALLING else f"water[level={8 - amount}]"
        for cell in flow.src:
            cells.setdefault(cell, "water")
        print(f"water: {len(flow.src)} sources, {len(flow.w)} cells of running water ({time.time() - t0:.0f} s)")

    look_mod = importlib.import_module(f"scenes.{args.scene}.mood")
    biome = look_mod.BIOMES[getattr(scene, "BIOME", sorted(look_mod.BIOMES)[0])]
    dimension = assets.json(f"{DATA}dimension_type/overworld.json")
    lines = timelines(assets) + [look_mod.TIMELINES[k] for k in sorted(getattr(look_mod, "TIMELINES", {}))]
    markers = assets.json(f"{DATA}timeline/day.json").get("time_markers", {})

    def look_at(tick):
        return gamelook.Look(tick, dimension, biome, lines)

    world = gamescene.Scene(assets, cells, entities, look_at(6000), place=args.place, say=lambda s: print(f"{s} ({time.time() - t0:.0f} s)"))
    if world.missing:
        print("not drawn:", ", ".join(f"{k} x{v}" for k, v in sorted(world.missing.items())))

    with open(args.shots) as fh:
        shots = json.load(fh)
    if args.only:
        wanted = args.only.split(",")
        shots = [s for s in shots if s["name"] in wanted]
    size = tuple(int(v) for v in args.size.split("x"))
    for shot in shots:
        t1 = time.time()
        tick = tick_of(args.time if args.time is not None else shot.get("time", "noon"), markers)
        cam = world.camera(shot["pos"], shot.get("look_at"), shot.get("yaw", 0.0), shot.get("pitch", 0.0), args.fov)
        img = world.picture(look_at(tick), cam, size, args.ss, args.fov)
        path = f"{args.out}-{shot['name']}.png"
        Image.fromarray(img).save(path)
        print(f"{path} (tick {tick}, {time.time() - t1:.0f} s)")


if __name__ == "__main__":
    main()
