#!/usr/bin/env python3
"""The shuttle: one trip of the real-machine render station (plan/PIPELINE.md 7).

    python bin/job.py s1 -- ../tools/win/shuttle.py --tag <assembly commit> --out @out/real <scene> [<scene> ...]

A trip takes several minutes: start it through bin/bg.py and read logs/<name>.log.

For the scenes named (each has a plot in plots.json beside this file) the trip
  1. writes the look (biomes, timelines) the scenes share into the test world and restarts the
     server when those files changed; a trip holds one look, scenes with another need their own;
  2. places every scene on its plot;
  3. writes one resource pack that holds what all the scenes need and puts it where the client
     reads it; two scenes that want different files under one name stop the trip;
  4. starts the game once (winmc.py checks the free video memory first and keeps the window in the
     background), shoots every scene's shot list, and stops the game again -- also when something
     went wrong on the way;
  5. says where the pictures are: <out>/<tag>/<scene>/<shot>.png.

    --shots <scene>=<file>   another shot list for a scene (default: scenes/<scene>/shots.json;
                             a relative path is taken from build/)
    --no-place               the scenes stand already; only the pack and the pictures
    --no-shoot               everything but the game: place and write the pack
    --keep-client            leave the game running at the end (only with the owner's consent)
    --settle, --first-settle seconds to wait before a picture, and before a scene's first one

Exit code: 0 all pictures taken; 3 not enough free video memory, nothing was started; 1 otherwise.
"""
import argparse
import filecmp
import importlib
import json
import os
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.dirname(HERE)
BUILD = os.path.normpath(os.path.join(TOOLS, "..", "build"))
sys.path.insert(0, BUILD)
sys.path.insert(1, TOOLS)

from artkit import mood as MOOD  # noqa: E402
from rcon import Rcon  # noqa: E402

ROOT = os.path.abspath(os.environ.get("MC_ROOT", os.getcwd()))
SERVER = os.path.join(ROOT, "server26")
GAME = os.path.join(ROOT, "client26", "game")
PACK = os.path.join(GAME, "resourcepacks", "c164art")
RCON_PORT = 25598
NAMESPACE = "c164art"


def say(text):
    print(f"[shuttle {time.strftime('%H:%M:%S')}] {text}")
    sys.stdout.flush()


def run(script, *args, check=True):
    """Run one of the repository's scripts with this Python, from build/; its output goes to ours,
    line by line as it comes. Returns (exit code, output)."""
    proc = subprocess.Popen([sys.executable, "-u", script, *[str(a) for a in args]], cwd=BUILD, text=True,
                            encoding="utf-8", errors="replace", stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            env={**os.environ, "PYTHONIOENCODING": "utf-8"})
    lines = []
    for line in proc.stdout:
        lines.append(line.rstrip("\n"))
        print("    " + lines[-1])
        sys.stdout.flush()
    code = proc.wait()
    if check and code != 0:
        raise Stop(f"{os.path.basename(script)} {' '.join(str(a) for a in args[:1])} ended with {code}", code)
    return code, "\n".join(lines)


class Stop(Exception):
    def __init__(self, why, code=1):
        super().__init__(why)
        self.code = code


def winmc(command, check=True):
    return run(os.path.join(TOOLS, "winmc.py"), command, check=check)


def world():
    """The folder of the server's world. Only the level's name is read from the settings."""
    name = "world"
    try:
        with open(os.path.join(SERVER, "server.properties"), encoding="utf-8") as fh:
            for line in fh:
                if line.startswith("level-name="):
                    name = line.split("=", 1)[1].strip() or name
    except OSError:
        pass
    return os.path.join(SERVER, name)


def rcon(*commands):
    with open(os.path.join(SERVER, ".rcon_pw")) as fh:
        rc = Rcon(port=RCON_PORT, password=fh.read().strip(), timeout=120.0)
    try:
        return [rc.command(c) for c in commands]
    finally:
        rc.close()


def look_of(scene):
    """(biomes, timelines) of a scene's mood module, or None when it has none."""
    try:
        look = importlib.import_module(f"scenes.{scene}.mood")
    except ModuleNotFoundError as e:
        if e.name != f"scenes.{scene}.mood":
            raise
        return None
    return look.BIOMES, getattr(look, "TIMELINES", None) or {}


def one_look(scenes):
    """The look the scenes share, or None when none of them carries one."""
    found = {}
    for scene in scenes:
        look = look_of(scene)
        if look is not None:
            found.setdefault(json.dumps(look, sort_keys=True), (look, []))[1].append(scene)
    if len(found) > 1:
        groups = "; ".join(", ".join(names) for _, names in found.values())
        raise Stop(f"these scenes carry different looks, and a trip holds one: {groups}. Run them in separate trips.")
    return next(iter(found.values()))[0] if found else None


def merge_pack(scenes, work):
    """One resource pack out of every scene's: <work>/pack. Returns how many files it holds."""
    merged = os.path.join(work, "pack")
    shutil.rmtree(work, ignore_errors=True)
    os.makedirs(merged)
    owner = {}
    for scene in scenes:
        part = os.path.join(work, "of-" + scene)
        run(os.path.join(BUILD, "makepack.py"), scene, "--out", part)
        for folder, _, names in os.walk(part):
            for name in names:
                src = os.path.join(folder, name)
                rel = os.path.relpath(src, part)
                dst = os.path.join(merged, rel)
                if rel in owner:
                    if rel != "pack.mcmeta" and not filecmp.cmp(src, dst, shallow=False):
                        raise Stop(f"{rel.replace(os.sep, '/')} differs between the packs of {owner[rel]} and "
                                   f"{scene}: they cannot be shown in one trip")
                    continue
                owner[rel] = scene
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                shutil.copyfile(src, dst)
    return merged, len(owner)


def same_tree(a, b):
    if not os.path.isdir(a) or not os.path.isdir(b):
        return False
    cmp = filecmp.dircmp(a, b)
    if cmp.left_only or cmp.right_only or cmp.funny_files:
        return False
    _, differ, errors = filecmp.cmpfiles(a, b, cmp.common_files, shallow=False)
    if differ or errors:
        return False
    return all(same_tree(os.path.join(a, d), os.path.join(b, d)) for d in cmp.common_dirs)


def client_runs():
    code, out = winmc("status", check=False)
    return code == 0 and "client: process" in out


def main():
    ap = argparse.ArgumentParser(description="one trip of the real-machine render station")
    ap.add_argument("scenes", nargs="+")
    ap.add_argument("--tag", required=True, help="names the pictures' folder: the assembly commit they show")
    ap.add_argument("--out", required=True)
    ap.add_argument("--shots", action="append", default=[], metavar="SCENE=FILE")
    ap.add_argument("--no-place", action="store_true")
    ap.add_argument("--no-shoot", action="store_true")
    ap.add_argument("--keep-client", action="store_true")
    ap.add_argument("--settle", type=float, default=4.0)
    ap.add_argument("--first-settle", type=float, default=12.0)
    args = ap.parse_args()

    with open(os.path.join(HERE, "plots.json"), encoding="utf-8") as fh:
        table = json.load(fh)
    lists = dict(item.split("=", 1) for item in args.shots)
    plan = []
    for scene in args.scenes:
        if scene not in table["plots"]:
            raise SystemExit(f"{scene} has no plot in tools/win/plots.json")
        at = [table["base"][0] + table["plots"][scene] * table["spacing"], table["base"][1], table["base"][2]]
        shots = os.path.join(BUILD, lists.get(scene, os.path.join("scenes", scene, "shots.json")))
        if not args.no_shoot and not os.path.exists(shots):
            raise SystemExit(f"{scene} has no shot list ({shots}); give one with --shots {scene}=<file>")
        plan.append((scene, at, shots))
    out = os.path.join(os.path.abspath(args.out), args.tag)
    work = os.path.join(os.path.abspath(args.out), "_trip")
    failed, taken, started = [], {}, False
    t0 = time.time()
    try:
        # ---- 1. the look ----
        look = one_look(args.scenes)
        restart = False
        data = os.path.join(world(), "datapacks", NAMESPACE)
        if look is not None:
            if not os.path.exists(os.path.join(data, "pack.mcmeta")):
                # a world that never held a scene: the data pack has to exist before the server
                # starts, or the look in it is not read
                run(os.path.join(BUILD, "place.py"), args.scenes[0], "--world", world(),
                    "--pw-file", os.path.join(SERVER, ".rcon_pw"), "--no-place")
                restart = True
            changed = MOOD.write(data, NAMESPACE, look[0], look[1])
            if changed:
                say("look files changed (" + ", ".join(changed) + "): the server is restarted")
                restart = True
        running = client_runs()
        if restart:
            if running:
                winmc("client-down")
                running = False
            winmc("server-down")
        winmc("server-up")

        # ---- 2. the scenes on their plots ----
        if not args.no_place:
            # what earlier trips kept loaded is let go; place.py loads what it places
            rcon("forceload remove all")
            for scene, at, _ in plan:
                say(f"placing {scene} at {at[0]} {at[1]} {at[2]}")
                _, text = run(os.path.join(BUILD, "place.py"), scene, "--world", world(),
                              "--pw-file", os.path.join(SERVER, ".rcon_pw"), "--at", *at)
                if "look files changed" in text:
                    raise Stop(f"{scene} changed the look while it was placed; the trip's look was not the scene's")
                if ", 0 failed" not in text:
                    failed.append(f"{scene}: not placed whole")

        # ---- 3. one resource pack ----
        merged, n = merge_pack(args.scenes, work)
        if same_tree(merged, PACK):
            say(f"resource pack: {n} files, the client has it already")
        else:
            if running:
                winmc("client-down")        # the game reads the pack when it starts
                running = False
            shutil.rmtree(PACK, ignore_errors=True)
            shutil.copytree(merged, PACK)
            say(f"resource pack: {n} files written to {os.path.relpath(PACK, ROOT)}")
        if args.no_shoot:
            return 1 if failed else 0

        # ---- 4. the game, once ----
        code, _ = winmc("client-up", check=False)
        if code == 3:
            say("not enough free video memory: the game was not started (the scenes stand and the pack is "
                "written; run the trip again with --no-place when there is room)")
            return 3
        if code != 0:
            raise Stop("the client did not come up", code)
        started = not running
        for scene, at, shots in plan:
            if any(f.startswith(scene + ":") for f in failed):
                continue
            target = os.path.join(out, scene)
            shutil.rmtree(target, ignore_errors=True)
            say(f"shooting {scene}")
            code, _ = run(os.path.join(TOOLS, "shoot.py"), shots, "--pw-file", os.path.join(SERVER, ".rcon_pw"),
                          "--out", target, "--origin", *at, "--settle", args.settle,
                          "--first-settle", args.first_settle, check=False)
            with open(shots, encoding="utf-8") as fh:
                wanted = len(json.load(fh))
            got = len([f for f in os.listdir(target) if f.endswith(".png")]) if os.path.isdir(target) else 0
            taken[scene] = (got, wanted)
            if code != 0 or got != wanted:
                failed.append(f"{scene}: {got} of {wanted} pictures")
    except Stop as stop:
        say(f"stopped: {stop}")
        failed.append(str(stop))
    finally:
        if not args.keep_client and not args.no_shoot:
            winmc("client-down", check=False)
    for scene, (got, wanted) in taken.items():
        say(f"{scene}: {got} of {wanted} pictures in {os.path.join(out, scene)}")
    say(("trip done" if not failed else "trip done with failures: " + "; ".join(failed))
        + f" ({time.time() - t0:.0f} s" + (", the game was opened once and is closed again)" if started else ")"))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
