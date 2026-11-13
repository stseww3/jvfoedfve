#!/usr/bin/env python3
"""Take in-game pictures: move the camera player with /tp over RCON, then grab what the client shows
(its X display on Linux, its window on Windows).

    shoot.py --pw-file <server>/.rcon_pw --out <dir> shots.json

shots.json is a list of shots:
    {"name": "wide", "pos": [x, y, z], "look_at": [x, y, z]}          camera (eye) aimed at a point
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


EYE = 1.62  # "pos" is where the camera's eye goes; /tp moves the feet


def angles(pos, target):
    """Minecraft yaw/pitch for looking from pos to target (yaw 0 = +z, pitch > 0 = down)."""
    dx, dy, dz = (target[i] - pos[i] for i in range(3))
    yaw = -math.degrees(math.atan2(dx, dz))
    pitch = -math.degrees(math.atan2(dy, math.hypot(dx, dz)))
    return yaw, pitch


def camera(args):
    """A function that saves what the client shows right now as a picture file.

    On Linux the client has an X display of its own and the whole display is grabbed. On Windows
    it is a window on a desktop in use: its picture is taken from the window itself, which works
    while it sits behind other windows (not while it is minimised).
    """
    if os.name != "nt":
        def take(path):
            subprocess.run(["import", "-display", f":{args.display}", "-window", "root", path], check=True)
        return take

    import winctl
    from PIL import Image

    with open(os.path.join(args.root, "client26", "client.pid")) as fh:
        pid = int(fh.read().strip())
    windows = winctl.game_windows(pid)
    if not windows:
        raise SystemExit("the client has no window")

    winctl.settle(windows[0])

    def take(path):
        got = winctl.grab(windows[0])
        if got is None:
            raise SystemExit("the window gave no picture (minimised?)")
        width, height, rows = got
        picture = Image.frombuffer("RGBA", (width, height), rows, "raw", "BGRA", 0, 1).convert("RGB")
        if picture.getextrema() in (((0, 0),) * 3, ((255, 255),) * 3):
            raise SystemExit("the window gave an empty picture")
        picture.save(path)
    return take


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("shots")
    ap.add_argument("--pw-file", required=True)
    ap.add_argument("--rcon-port", type=int, default=25598)
    ap.add_argument("--player", default="C164Cam")
    ap.add_argument("--display", default="164", help="X display number of the client (Linux)")
    ap.add_argument("--root", default=os.environ.get("MC_ROOT", os.getcwd()),
                    help="folder that holds client26/ (Windows, see winmc.py)")
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
    take = camera(args)

    with open(args.pw_file) as fh:
        rc = Rcon(port=args.rcon_port, password=fh.read().strip())
    if args.player not in rc.command("list"):
        raise SystemExit(f"{args.player} is not online")
    rc.command(f"gamemode spectator {args.player}")
    # The clock stands still while pictures are taken. Left running it moves on some 20 ticks for
    # every second of settling, and at dusk a few hundred ticks are a different picture.
    answer = rc.command("gamerule advance_time false")
    if "advance_time" not in answer:
        print(f"could not stop the clock: {answer.strip()}", file=sys.stderr)

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
        rc.command(f"tp {args.player} {pos[0]:.2f} {pos[1] - EYE:.2f} {pos[2]:.2f} {yaw:.2f} {pitch:.2f}")
        time.sleep(shot.get("settle", args.first_settle if i == 0 else args.settle))
        path = os.path.join(args.out, shot["name"] + ".png")
        take(path)
        print(path, flush=True)
    rc.close()


if __name__ == "__main__":
    main()
