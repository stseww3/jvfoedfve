#!/usr/bin/env python3
"""Take in-game pictures: move the camera player with /tp over RCON, then save what the client shows
(the game's own screenshot, or its window or X display, see camera()).

    shoot.py --pw-file <server>/.rcon_pw --out <dir> shots.json

shots.json is a list of shots:
    {"name": "wide", "pos": [x, y, z], "look_at": [x, y, z]}          camera (eye) aimed at a point
    {"name": "front", "pos": [x, y, z], "yaw": 180, "pitch": 10}      explicit angles
    {"name": "as_joined", "stay": true}                               where the player stands
    {"name": "at_sign", "walk": true, "pos": [x, y, z], "look_at": [x, y, z]}    the player goes there itself
Optional per shot: "time" (e.g. "noon", "midnight" or a tick number; without it the shot is taken
at 14000, look A, as build/render.py does), "settle" (seconds to wait), "still" (seconds, instead
of --still; 0: the first picture after the wait is the one). --time <tick> takes every shot at
that time, whatever the list says: a scene built for another light version is shot at its tick.

A world that is shot as it comes -- a save exported for the Realm, opened by the server just as it
is (savetrip.py) -- is shot with --keep-clock: no time is set and the clock is not stopped, the
pictures show the hour the world itself keeps. A shot with "stay" is taken where the player stands
and as the player is: nothing is asked of the server for it, and while no other shot came before
it the player is still in the game mode the world gave (hand, hotbar and all: what a visitor sees
on joining). A shot with "walk" moves the player as a visitor would stand there: in the game
mode it joined in, on its feet (pos is still the eye), so that what the world does to somebody who
comes by is done to it -- a tag given on coming near, a title shown -- and the picture has the
hand, the hotbar and whatever the game writes over the view.

Two more keys, for a trip that tries what a world does: "do" is a list of commands sent to the
server before the move, "ask" a list sent after the picture is taken, each answer printed as
`asked at <shot>: <command> -> <answer>`; {player} in a command is the camera player's name.

How long the game needs after a move depends on the machine: a graphics card has the new view in
a second or two, a software renderer on a worker node may need many. --still <seconds> therefore
takes the picture again and again after the settling time, every few seconds, until two in a row
are alike -- chunks that are still arriving change whole pieces of a picture, stars, clouds and
smoke only a little -- or the seconds given are over; the last one is kept, and the line printed
for it says how long that took and whether it stood still.

The camera player must already be online (nodemc.py on a worker node, winmc.py on the admin's
computer). It is put into spectator mode before its first move so that no hand, hotbar or body
shows up.
"""
import argparse
import collections
import itertools
import json
import math
import os
import re
import shutil
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from rcon import Rcon  # noqa: E402


EYE = 1.62  # "pos" is where the camera's eye goes; /tp moves the feet
# A shot that names no time is taken in look A, the blue hour (plan/roles/INTERFACE.md 3); the same
# number as build/render.py's DEFAULT_TIME, so a shot list means the same picture in both.
DEFAULT_TIME = 14000
GAME_MODES = {0: "survival", 1: "creative", 2: "adventure", 3: "spectator"}     # as a player's data numbers them
WIP = ".wip.png"        # after a picture's name while it is being taken; EARLIER, the one before it
EARLIER = ".earlier.png"


def angles(pos, target):
    """Minecraft yaw/pitch for looking from pos to target (yaw 0 = +z, pitch > 0 = down)."""
    dx, dy, dz = (target[i] - pos[i] for i in range(3))
    yaw = -math.degrees(math.atan2(dx, dz))
    pitch = -math.degrees(math.atan2(dy, math.hypot(dx, dz)))
    return yaw, pitch


def empty(picture):
    return picture.getextrema() in (((0, 0),) * 3, ((255, 255),) * 3)


def why_empty():
    """What the desktop is doing, when that explains an empty picture from the window."""
    try:
        sys.path.insert(1, os.path.join(os.path.dirname(os.path.abspath(__file__)), "win"))
        import deskstate
        desk = deskstate.report()
    except (ImportError, OSError):
        return ""
    if desk["ok"] is False:
        return (f": the console display is {desk['display']}, and the desktop hands out the game's picture "
                "only while it is on (start the client through the helper, see winmc.py)")
    return ""


def game_camera(game, asks):
    """The game saves its own screenshot, the picture F2 would save, asked through the helper the
    client was started with (win/CamHelper.java). Works whatever the desktop or the display does."""
    from PIL import Image
    numbers = itertools.count(1)

    def take(path):
        ask = f"{os.getpid()}-{next(numbers)}"
        name = f"c164-{ask}.png"
        with open(os.path.join(asks, ask + ".tmp"), "w", encoding="utf-8") as fh:
            fh.write("shot " + name)
        os.replace(os.path.join(asks, ask + ".tmp"), os.path.join(asks, ask + ".req"))
        done, fail = os.path.join(asks, ask + ".done"), os.path.join(asks, ask + ".fail")
        end = time.monotonic() + 120
        while not os.path.exists(done):
            if os.path.exists(fail):
                with open(fail, encoding="utf-8") as fh:
                    raise SystemExit("the game could not take the picture: " + fh.read().strip())
            if time.monotonic() > end:
                raise SystemExit("the game did not answer the request for a picture")
            time.sleep(0.05)
        saved = os.path.join(game, "screenshots", name)
        try:
            with Image.open(saved) as shot:
                picture = shot.convert("RGB")
        except OSError as exc:
            raise SystemExit(f"the picture the game saved cannot be read ({exc})")
        if empty(picture):
            raise SystemExit("the game saved an empty picture")
        picture.save(path)
        os.remove(saved)
        os.remove(done)
    return take


def display_camera(display):
    """The whole X display of the client is grabbed: with ImageMagick's import where it is
    installed, else by Pillow."""
    if shutil.which("import"):
        def take(path):
            subprocess.run(["import", "-display", f":{display}", "-window", "root", path], check=True)
        return take

    from PIL import ImageGrab

    def take(path):
        try:
            picture = ImageGrab.grab(xdisplay=f":{display}").convert("RGB")
        except OSError as exc:
            raise SystemExit(f"the X display :{display} gave no picture ({exc})")
        if empty(picture):
            raise SystemExit("the X display gave an empty picture")
        picture.save(path)
    return take


class Camera:
    """Saves what the client shows as a picture file, by the first way that works: when the game
    cannot save its own screenshot, the pictures are taken off the display from then on. `last`
    is the way the last picture was made ("game", "display" or "window")."""

    def __init__(self, ways):
        self.ways = list(ways)                  # [(name, take)]
        self.last = None

    def __call__(self, path):
        while True:
            name, take = self.ways[0]
            try:
                take(path)
            except SystemExit as why:
                if len(self.ways) == 1:
                    raise
                print(f"{why}: the pictures are taken off the {self.ways[1][0]} instead", flush=True)
                del self.ways[0]
                continue
            self.last = name
            return


def summary(made):
    """One line the shuttle reads: how many pictures the game saved and how many came off the display."""
    off = sum(n for name, n in made.items() if name != "game")
    return f"pictures: {made.get('game', 0)} saved by the game itself, {off} taken off the display"


def moved(a, b, level=24):
    """The share of two pictures' pixels that differ by more than `level` in some channel."""
    from PIL import Image, ImageChops
    with Image.open(a) as one, Image.open(b) as other:
        if one.size != other.size:
            return 1.0
        red, green, blue = ImageChops.difference(one.convert("RGB"), other.convert("RGB")).split()
    most = ImageChops.lighter(ImageChops.lighter(red, green), blue)
    return sum(most.histogram()[level + 1:]) / float(most.size[0] * most.size[1])


def until_still(take, path, patience, gap=3.0, share=0.01):
    """Take the picture at `path` again every `gap` seconds until two in a row are alike (no more
    than `share` of their pixels differ) or `patience` seconds have passed; the last one stays.
    Returns (seconds it took, the share that differed between the last two, did it stand still)."""
    earlier = path + EARLIER
    t0 = time.monotonic()
    try:
        while True:
            os.replace(path, earlier)
            time.sleep(gap)
            take(path)
            differ = moved(earlier, path)
            if differ <= share or time.monotonic() - t0 >= patience:
                return time.monotonic() - t0, differ, differ <= share
    finally:
        if os.path.exists(earlier):
            os.remove(earlier)


def helper_listens(root):
    """(process id of the client, was it started through the picture helper and is that listening)"""
    def number(path):
        try:
            with open(path) as fh:
                return int(fh.read().strip())
        except (OSError, ValueError):
            return None
    pid = number(os.path.join(root, "client26", "client.pid"))
    return pid, pid is not None and number(os.path.join(root, "client26", "game", "c164cam", "ready")) == pid


def camera(args):
    """A Camera: called with a path, it saves what the client shows right now as a picture file.

    There are two ways (--capture; "auto" takes the first when the client runs with the helper):
      game    the game saves its own screenshot, the picture F2 would save, asked through the
              helper it was started with (win/CamHelper.java). Works whatever the desktop does.
      window  on Linux the client has an X display of its own and the whole display is grabbed;
              "auto" falls back to this when the game cannot save its own picture.
              On Windows it is a window on a desktop in use, behind the other windows and without
              the keyboard, and the desktop hands out the window's picture (winctl.grab): that
              works behind other windows, but not while the window is minimised or the display
              is asleep.
    """
    game = os.path.join(args.root, "client26", "game")
    asks = os.path.join(game, "c164cam")
    pid, helped = helper_listens(args.root)
    if args.capture == "game" and not helped:
        raise SystemExit("the client was not started through the picture helper (see nodemc.py, winmc.py)")

    if os.name != "nt":
        ways = [("display", display_camera(args.display))]
        if helped and args.capture != "window":
            ways.insert(0, ("game", game_camera(game, asks)))
        return Camera(ways[:1] if args.capture == "game" else ways)

    import winctl
    from PIL import Image

    if pid is None:
        raise SystemExit("no client26/client.pid: the client was not started by winmc.py")
    windows = winctl.game_windows(pid)
    if not windows:
        raise SystemExit("the client has no window")

    winctl.settle(windows[0])

    if helped and args.capture != "window":
        return Camera([("game", game_camera(game, asks))])

    def take(path):
        got = winctl.grab(windows[0])
        if got is None:
            raise SystemExit("the window gave no picture (minimised?)")
        width, height, rows = got
        picture = Image.frombuffer("RGBA", (width, height), rows, "raw", "BGRA", 0, 1).convert("RGB")
        if empty(picture):
            raise SystemExit("the window gave an empty picture" + why_empty())
        picture.save(path)
    return Camera([("window", take)])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("shots")
    ap.add_argument("--pw-file", required=True)
    ap.add_argument("--rcon-port", type=int, default=25598)
    ap.add_argument("--player", default="C164Cam")
    ap.add_argument("--display", default="164", help="X display number of the client (Linux)")
    ap.add_argument("--root", default=os.environ.get("MC_ROOT", os.getcwd()),
                    help="folder that holds client26/ (see nodemc.py, winmc.py)")
    ap.add_argument("--capture", choices=("auto", "game", "window"), default="auto",
                    help="who makes the picture: the game itself, or the desktop from the window or the X display")
    ap.add_argument("--out", required=True)
    ap.add_argument("--settle", type=float, default=6.0, help="seconds to wait after each move")
    ap.add_argument("--first-settle", type=float, default=15.0, help="wait for the first shot (chunks have to load)")
    ap.add_argument("--still", type=float, default=0.0, metavar="SECONDS",
                    help="after settling, take each picture again until two in a row are alike, this long at most")
    ap.add_argument("--only", help="comma separated shot names")
    ap.add_argument("--time", help="every shot is taken at this time, whatever the list says")
    ap.add_argument("--clock", type=int, metavar="TICK",
                    help="the same, under the name build/place.py gives it: a look that the resource pack carries "
                         "has one hour, which place.py holds the clock at and notes in <scene>.placed.json")
    ap.add_argument("--keep-clock", action="store_true",
                    help="the world's own clock is left alone: no time is set and the clock is not stopped")
    ap.add_argument("--walk-as", choices=tuple(GAME_MODES.values()), metavar="MODE",
                    help="the game mode of the shots that walk (default: the one the player has before its first move)")
    ap.add_argument("--origin", type=float, nargs=3, default=[0.0, 0.0, 0.0], metavar=("X", "Y", "Z"),
                    help="added to every pos/look_at, for shot lists written in scene coordinates")
    args = ap.parse_args()
    if args.clock is not None:
        if args.time is not None and str(args.time) != str(args.clock):
            raise SystemExit(f"--time {args.time} and --clock {args.clock}: one hour for every shot, not two")
        args.time = args.clock
    if args.keep_clock and args.time is not None:
        raise SystemExit("--keep-clock leaves the world's clock alone and --time sets it: one or the other")

    with open(args.shots) as fh:
        shots = json.load(fh)
    if args.only:
        wanted = set(args.only.split(","))
        shots = [s for s in shots if s["name"] in wanted]
    os.makedirs(args.out, exist_ok=True)
    for left in os.listdir(args.out):       # what a run that was cut short was working on
        if left.endswith((WIP, EARLIER)):
            os.remove(os.path.join(args.out, left))
    take = camera(args)

    with open(args.pw_file) as fh:
        rc = Rcon(port=args.rcon_port, password=fh.read().strip())
    if args.player not in rc.command("list"):
        raise SystemExit(f"{args.player} is not online")
    if not args.keep_clock:
        # The clock stands still while pictures are taken. Left running it moves on some 20 ticks for
        # every second of settling, and at dusk a few hundred ticks are a different picture.
        answer = rc.command("gamerule advance_time false")
        if "advance_time" not in answer:
            print(f"could not stop the clock: {answer.strip()}", file=sys.stderr)

    last_time = None
    spectator = False
    joined_as = args.walk_as    # the game mode of the shots that walk: the one the player had before its first move
    made = collections.Counter()
    try:
        for i, shot in enumerate(shots):
            when = args.time if args.time is not None else shot.get("time", DEFAULT_TIME)
            if when != last_time and not args.keep_clock:
                rc.command(f"time set {when}")
                last_time = when
            for command in shot.get("do", ()):
                command = command.replace("{player}", args.player)
                print(f"done at {shot['name']}: {command} -> {' '.join(rc.command(command).split())[:300]}", flush=True)
            if not shot.get("stay"):
                if joined_as is None:
                    found = re.search(r"(\d+)\s*$", rc.command(f"data get entity {args.player} playerGameType"))
                    joined_as = GAME_MODES.get(int(found.group(1)) if found else -1, "adventure")
                if shot.get("walk"):
                    if spectator:
                        rc.command(f"gamemode {joined_as} {args.player}")
                        spectator = False
                elif not spectator:
                    rc.command(f"gamemode spectator {args.player}")
                    spectator = True
                pos = [shot["pos"][k] + args.origin[k] for k in range(3)]
                if "look_at" in shot:
                    yaw, pitch = angles(pos, [shot["look_at"][k] + args.origin[k] for k in range(3)])
                else:
                    yaw, pitch = shot.get("yaw", 0.0), shot.get("pitch", 0.0)
                rc.command(f"tp {args.player} {pos[0]:.2f} {pos[1] - EYE:.2f} {pos[2]:.2f} {yaw:.2f} {pitch:.2f}")
            time.sleep(shot.get("settle", args.first_settle if i == 0 else args.settle))
            path = os.path.join(args.out, shot["name"] + ".png")
            # A picture gets its name when it is done. A run that is cut short leaves no half
            # file and no picture that was still waited for under a shot's name.
            wip = path + WIP
            take(wip)
            still = float(shot.get("still", args.still))
            if still > 0:
                took, differ, stood = until_still(take, wip, still)
                os.replace(wip, path)
                print(f"{path} ({'still' if stood else 'STILL CHANGING'} after {took:.0f} s more, "
                      f"{differ:.2%} of it moved between the last two)", flush=True)
            else:
                os.replace(wip, path)
                print(path, flush=True)
            made[take.last] += 1
            for command in shot.get("ask", ()):
                command = command.replace("{player}", args.player)
                print(f"asked at {shot['name']}: {command} -> {' '.join(rc.command(command).split())[:400]}", flush=True)
    finally:
        print(summary(made), flush=True)        # also when a shot failed: the note says how the others were made
    rc.close()


if __name__ == "__main__":
    main()
