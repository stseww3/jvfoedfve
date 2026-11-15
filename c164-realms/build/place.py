#!/usr/bin/env python3
"""Generate a scene, export it into a world's datapack and place it on a running server.

    place.py skyobs --world <server>/<level-name> --pw-file <server>/.rcon_pw --at 0 200 0

The scene module (scenes/<name>/__init__.py) must provide build() -> Canvas. The world is cleared
around the previous placement first, so the command can be repeated while iterating on a design.

A scene may also carry a look (scenes/<name>/mood.py with BIOMES and TIMELINES, see artkit.mood).
Those files are written into the data pack first; when they changed the script says so, and the
server has to be restarted before the new look exists (`--look-only` writes just these files, to be
run while the server is down). `--biome-only --biome <name>` swaps the biome around an already
placed scene, for comparing looks.
"""
import argparse
import importlib
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "tools"))

from artkit import export as X  # noqa: E402
from artkit import mood as MOOD  # noqa: E402
from rcon import Rcon  # noqa: E402

WORLD_Y = (-64, 319)

RULES = [
    "gamerule max_block_modifications 200000000",
    "gamerule random_tick_speed 0",
    "gamerule spawn_mobs false",
    "gamerule advance_weather false",
    "gamerule block_drops false",
    "gamerule entity_drops false",
    "weather clear",
]


def fill_biome(rc, at, lo, hi, biome, margin, margin_y):
    """Set the biome in the box around a placement, wide enough to hold every camera position.

    The sky and haze are sampled where the viewer stands, so the look has to reach well past the
    blocks themselves.
    """
    ox, oy, oz = at
    x0, x1 = ox + lo[0] - margin, ox + hi[0] + margin
    z0, z1 = oz + lo[2] - margin, oz + hi[2] + margin
    y0, y1 = max(WORLD_Y[0], oy + lo[1] - margin_y), min(WORLD_Y[1], oy + hi[1] + margin_y)
    step = 192  # 13 x 13 chunks at most: one forceload takes no more than 256
    boxes = [(x, z, min(x + step - 1, x1), min(z + step - 1, z1))
             for x in range(x0, x1 + 1, step) for z in range(z0, z1 + 1, step)]
    for x, z, xa, za in boxes:
        rc.command(f"forceload add {x} {z} {xa} {za}")
    total = 0
    for x, z, xa, za in boxes:
        cmd = f"fillbiome {x} {y0} {z} {xa} {y1} {za} {biome}"
        for attempt in range(6):
            out = rc.command(cmd).strip()
            if "not loaded" not in out:
                break
            time.sleep(1.5)
        head = out.split(" ", 1)[0]
        if head.isdigit():
            total += int(head)
        elif "No biome entries were changed" not in out:  # that one only means it was set already
            print("  !!", cmd, "->", out[:200])
    print(f"biome {biome}: {total} cells set in {len(boxes)} boxes, x {x0}..{x1} y {y0}..{y1} z {z0}..{z1}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("scene")
    ap.add_argument("--world", required=True, help="world folder of the running server")
    ap.add_argument("--pw-file", required=True)
    ap.add_argument("--rcon-port", type=int, default=25598)
    ap.add_argument("--at", type=int, nargs=3, default=[0, 200, 0], metavar=("X", "Y", "Z"))
    ap.add_argument("--no-place", action="store_true", help="only generate and export")
    ap.add_argument("--biome", help="biome to fill instead of the scene's own")
    ap.add_argument("--biome-only", action="store_true", help="only refill the biome around the placed scene")
    ap.add_argument("--look-only", action="store_true", help="only write the look files (before a server start)")
    args = ap.parse_args()

    scene = importlib.import_module(f"scenes.{args.scene}")
    pack = os.path.join(args.world, "datapacks", "c164art")
    state_file = os.path.join(pack, f"{args.scene}.placed.json")
    prev = None
    if os.path.exists(state_file):
        with open(state_file) as fh:
            prev = json.load(fh)
    try:
        look = importlib.import_module(f"scenes.{args.scene}.mood")
    except ModuleNotFoundError as e:
        if e.name != f"scenes.{args.scene}.mood":
            raise               # the look is there and fails to import something: that is not "no look"
        look = None
    own = getattr(scene, "BIOME", None)
    if own and ":" not in own and not args.biome and own not in getattr(look, "BIOMES", {}):
        # the fill would only say "unknown biome" for every box, after the scene is placed
        raise SystemExit(f"BIOME {own!r} of scene {args.scene} is not one of its look's biomes "
                         f"({', '.join(sorted(getattr(look, 'BIOMES', {}))) or 'the scene has no mood.py'})")
    biome = args.biome or own
    if biome and ":" not in biome:
        biome = f"c164art:{biome}"
    margin = getattr(scene, "BIOME_MARGIN", 4)
    margin_y = getattr(scene, "BIOME_MARGIN_Y", margin)

    if look is not None:
        changed = MOOD.write(pack, "c164art", look.BIOMES, getattr(look, "TIMELINES", None))
        if changed:
            print("look files changed (" + ", ".join(changed) + "): restart the server and reconnect the client")
    if args.look_only:
        return

    def connect():
        with open(args.pw_file) as fh:
            return Rcon(port=args.rcon_port, password=fh.read().strip(), timeout=600.0)

    if args.biome_only:
        if not prev or not biome:
            raise SystemExit("nothing placed yet, or no biome given")
        rc = connect()
        fill_biome(rc, prev["at"], prev["min"], prev["max"], biome, margin, margin_y)
        rc.close()
        return

    t0 = time.time()
    canvas = scene.build()
    print(f"built {len(canvas.b)} blocks, {len(canvas.entities)} entities in {time.time() - t0:.1f}s")
    t0 = time.time()
    man = X.export(canvas, pack, args.scene)
    print(f"exported {man['tiles']} tiles ({man['solid']} + {man['detail']} blocks) in {time.time() - t0:.1f}s")
    if args.no_place:
        return

    ox, oy, oz = args.at
    rc = connect()
    at = f"execute positioned {ox} {oy} {oz} run "
    for cmd in RULES:
        rc.command(cmd)
    print(rc.command("reload").strip() or "reloaded")
    rc.command(f"{at}function {man['namespace']}:{man['name']}/forceload")
    time.sleep(2.0)
    rc.command("tick freeze")
    try:
        if prev:
            px, py, pz = prev["at"]
            (ax, ay, az), (bx, by, bz) = prev["min"], prev["max"]
            n = 0
            for x in range(ax - 1, bx + 2, 32):
                for z in range(az - 1, bz + 2, 32):
                    rc.command(f"execute positioned {px} {py} {pz} run fill ~{x} ~{ay - 1} ~{z} "
                               f"~{min(x + 31, bx + 1)} ~{by + 1} ~{min(z + 31, bz + 1)} air strict")
                    n += 1
            rc.command(f"execute positioned {px + ax - 1} {py + ay - 1} {pz + az - 1} run kill "
                       f"@e[type=!player,dx={bx - ax + 2},dy={by - ay + 2},dz={bz - az + 2}]")
            print(f"cleared previous placement ({n} fills)")
        t0 = time.time()
        failed = 0
        with open(os.path.join(pack, "data", man["namespace"], "function", man["name"], "place.mcfunction")) as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                out = rc.command(at + line)
                if "Loaded template" not in out:
                    failed += 1
                    print("  !!", line, "->", out.strip()[:200])
        print(f"placed in {time.time() - t0:.1f}s, {failed} failed")
    finally:
        rc.command("tick unfreeze")
    if biome:
        fill_biome(rc, (ox, oy, oz), man["min"], man["max"], biome, margin, margin_y)
    with open(state_file, "w") as fh:
        json.dump({"at": [ox, oy, oz], "min": man["min"], "max": man["max"]}, fh)
    rc.close()


if __name__ == "__main__":
    main()
