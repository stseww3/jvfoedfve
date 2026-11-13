#!/usr/bin/env python3
"""Take in-game pictures: move the camera player with /tp over RCON, then grab the client's X display.

    shoot.py --pw-file <server>/.rcon_pw --out <dir> shots.json

shots.json is a list of shots:
    {"name": "wide", "pos": [x, y, z], "look_at": [x, y, z]}          camera aimed at a point
    {"name": "front", "pos": [x, y, z], "yaw": 180, "pitch": 10}      explicit angles
Optional per shot: "time" (e.g. "noon", "midnight" or a tick number), "settle" (seconds to wait).

The camera player must already be online (see run_client.sh). It is put into spectator mode so that
no hand, hotbar or body shows up.
"""
import argparse
import json
import math
import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from rcon import Rcon  # noqa: E402


def angles(pos, target):
    """Minecraft yaw/pitch for looking from pos to target (yaw 0 = +z, pitch > 0 = down)."""
    dx, dy, dz = (target[i] - pos[i] for i in range(3))
    yaw = -math.degrees(math.atan2(dx, dz))
    pitch = -math.degrees(math.atan2(dy, math.hypot(dx, dz)))
    return yaw, pitch


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("shots")
    ap.add_argument("--pw-file", required=True)
    ap.add_argument("--rcon-port", type=int, default=25598)
    ap.add_argument("--player", default="C164Cam")
    ap.add_argument("--display", default="164")
    ap.add_argument("--out", required=True)
    ap.add_argument("--settle", type=float, default=6.0, help="seconds to wait after each move")
    ap.add_argument("--first-settle", type=float, default=15.0, help="wait for the first shot (chunks have to load)")
    ap.add_argument("--only", help="comma separated shot names")
    ap.add_argument("--origin", type=float, nargs=3, default=[0.0, 0.0, 0.0], metavar=("X", "Y", "Z"),
                    help="added to every pos/look_at, for shot lists written in scene coordinates")
    args = ap.parse_args()

    with open(args.shots) as fh:
        shots = json.load(fh)
    if args.only:
        wanted = set(args.only.split(","))
        shots = [s for s in shots if s["name"] in wanted]
    os.makedirs(args.out, exist_ok=True)

    with open(args.pw_file) as fh:
        rc = Rcon(port=args.rcon_port, password=fh.read().strip())
    if args.player not in rc.command("list"):
        raise SystemExit(f"{args.player} is not online")
    rc.command(f"gamemode spectator {args.player}")

    last_time = None
    for i, shot in enumerate(shots):
        pos = [shot["pos"][k] + args.origin[k] for k in range(3)]
        if "look_at" in shot:
            yaw, pitch = angles(pos, [shot["look_at"][k] + args.origin[k] for k in range(3)])
        else:
            yaw, pitch = shot.get("yaw", 0.0), shot.get("pitch", 0.0)
        when = shot.get("time", "noon")
        if when != last_time:
            rc.command(f"time set {when}")
            last_time = when
        rc.command(f"tp {args.player} {pos[0]:.2f} {pos[1]:.2f} {pos[2]:.2f} {yaw:.2f} {pitch:.2f}")
        time.sleep(shot.get("settle", args.first_settle if i == 0 else args.settle))
        path = os.path.join(args.out, shot["name"] + ".png")
        subprocess.run(["import", "-display", f":{args.display}", "-window", "root", path], check=True)
        print(path)
    rc.close()


if __name__ == "__main__":
    main()
