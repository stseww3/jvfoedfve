#!/usr/bin/env python3
"""Generate a scene, export it into a world's datapack and place it on a running server.

    place.py skyobs --world <server>/<level-name> --pw-file <server>/.rcon_pw --at 0 200 0

The scene module (scenes/<name>/__init__.py) must provide build() -> Canvas. The world is cleared
around the previous placement first, so the command can be repeated while iterating on a design.
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
from rcon import Rcon  # noqa: E402

RULES = [
    "gamerule max_block_modifications 200000000",
    "gamerule random_tick_speed 0",
    "gamerule spawn_mobs false",
    "gamerule advance_weather false",
    "gamerule block_drops false",
    "gamerule entity_drops false",
    "weather clear",
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("scene")
    ap.add_argument("--world", required=True, help="world folder of the running server")
    ap.add_argument("--pw-file", required=True)
    ap.add_argument("--rcon-port", type=int, default=25598)
    ap.add_argument("--at", type=int, nargs=3, default=[0, 200, 0], metavar=("X", "Y", "Z"))
    ap.add_argument("--no-place", action="store_true", help="only generate and export")
    args = ap.parse_args()

    t0 = time.time()
    scene = importlib.import_module(f"scenes.{args.scene}")
    canvas = scene.build()
    print(f"built {len(canvas.b)} blocks, {len(canvas.entities)} entities in {time.time() - t0:.1f}s")

    pack = os.path.join(args.world, "datapacks", "c164art")
    state_file = os.path.join(pack, f"{args.scene}.placed.json")
    prev = None
    if os.path.exists(state_file):
        with open(state_file) as fh:
            prev = json.load(fh)
    t0 = time.time()
    man = X.export(canvas, pack, args.scene)
    print(f"exported {man['tiles']} tiles ({man['solid']} + {man['detail']} blocks) in {time.time() - t0:.1f}s")
    if args.no_place:
        return

    ox, oy, oz = args.at
    with open(args.pw_file) as fh:
        rc = Rcon(port=args.rcon_port, password=fh.read().strip(), timeout=600.0)
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
    with open(state_file, "w") as fh:
        json.dump({"at": [ox, oy, oz], "min": man["min"], "max": man["max"]}, fh)
    rc.close()


if __name__ == "__main__":
    main()
