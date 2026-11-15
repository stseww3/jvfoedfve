#!/usr/bin/env python3
"""The shuttle: one trip of the real-machine render station (plan/PIPELINE.md 7).

    python bin/job.py s1 --heavy -- ../tools/win/shuttle.py --tag <commit> --out @out/real <scene> [<scene> ...]

Use bin/trip.py: it runs this together with what has to happen before and after (bringing the code
up to date, making sure the game is closed, sending the pictures back). A trip takes minutes.

For the scenes named the trip
  1. writes the look (biomes, timelines) the scenes share into the test world and restarts the
     server when those files changed; a trip holds one look, scenes with another need their own;
  2. places every scene on its plot (plots.json beside this file; a scene that has none yet gets
     the next free one, which is noted in the test world and has to be added to the table);
  3. writes one resource pack that holds what all the scenes need and puts it where the client
     reads it; two scenes that want different files under one name stop the trip;
  4. starts the game once (winmc.py checks the free video memory first and keeps the window in the
     background), shoots every scene's shot list, and stops the game again -- also when something
     went wrong on the way;
  5. leaves the pictures in <out>/<tag>/<scene>/<shot>.png and, ready to be sent, in
     <out>/<tag>/send/ as <scene>-<tag>-<shot>.jpg beside a note <scene>-<tag>-real.txt that says
     for every shot its tick, the commit of the code it shows and the first 16 digits of the
     picture file's SHA-256 (tools/realshots.py reads it on the cloud machine).

    --project <dir>          the c164-realms whose scenes are shot (default: the one this file is in).
                             The station's own tools stay the ones beside this file, so a branch
                             that carries older tools, or none, can be shot all the same
    --shots <scene>=<file>   another shot list for a scene (default: scenes/<scene>/shots.json; a
                             relative path is taken from the project's build/). The word "board" is
                             the twelve board views, worked out from the project's skeleton by
                             tools/boardshots.py; it is the default for the master scene, obs
    --only <scene>=<a,b>     only these shots of a scene
    --plot <scene>=<n>       the plot of a scene the table does not hold yet
    --no-place               the scenes stand already; only the pack and the pictures
    --no-shoot               everything but the game: place and write the pack
    --keep-client            leave the game running at the end (only with the owner's consent)
    --settle, --first-settle seconds to wait before a picture, and before a scene's first one

Exit code: 0 all pictures taken; 3 not enough free video memory, nothing was started; 1 otherwise.
"""
import argparse
import datetime
import filecmp
import hashlib
import importlib
import json
import os
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.dirname(HERE)
ROOT = os.path.abspath(os.environ.get("MC_ROOT", os.getcwd()))
SERVER = os.path.join(ROOT, "server26")
GAME = os.path.join(ROOT, "client26", "game")
PACK = os.path.join(GAME, "resourcepacks", "c164art")
RCON_PORT = 25598
NAMESPACE = "c164art"
MASTER = "obs"              # the master scene: its default shot list is the board
BOARD = "board"
JPEG_QUALITY = 90
BUILD = None                # the build/ folder of the code that is shot; set in main()


def say(text):
    print(f"[shuttle {time.strftime('%H:%M:%S')}] {text}")
    sys.stdout.flush()


class Stop(Exception):
    def __init__(self, why, code=1):
        super().__init__(why)
        self.code = code


def run(script, *args, check=True, env=None):
    """Run a Python script with this Python, from the shot code's build/; its output goes to ours,
    line by line as it comes. Returns (exit code, output)."""
    proc = subprocess.Popen([sys.executable, "-u", script, *[str(a) for a in args]], cwd=BUILD, text=True,
                            encoding="utf-8", errors="replace", stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            env={**os.environ, "PYTHONIOENCODING": "utf-8", **(env or {})})
    lines = []
    for line in proc.stdout:
        lines.append(line.rstrip("\n"))
        print("    " + lines[-1])
        sys.stdout.flush()
    code = proc.wait()
    if check and code != 0:
        raise Stop(f"{os.path.basename(script)} {' '.join(str(a) for a in args[:1])} ended with {code}", code)
    return code, "\n".join(lines)


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
    from rcon import Rcon
    with open(os.path.join(SERVER, ".rcon_pw")) as fh:
        rc = Rcon(port=RCON_PORT, password=fh.read().strip(), timeout=120.0)
    try:
        return [rc.command(c) for c in commands]
    finally:
        rc.close()


def commit_of(project):
    """The commit the shot code is at (the checkout bin/sync.py made), or "?"."""
    git = os.path.join(ROOT, "git", "cmd", "git.exe")
    try:
        got = subprocess.run([git if os.path.exists(git) else "git", "-C", project, "rev-parse", "HEAD"],
                             capture_output=True, text=True)
    except OSError:
        return "?"
    return got.stdout.strip()[:9] if got.returncode == 0 and got.stdout.strip() else "?"


# ---- plots -----------------------------------------------------------------------------------------
def plots(scenes, given):
    """{scene: plot number}. The table beside this file comes first. A scene it does not hold keeps
    the plot noted in the test world on an earlier trip, or takes the one given with --plot, or
    the next free one; what is new is noted in the test world, so that the scene stays where it is."""
    with open(os.path.join(HERE, "plots.json"), encoding="utf-8") as fh:
        table = json.load(fh)
    local_file = os.path.join(world(), "datapacks", NAMESPACE, "plots.local.json")
    try:
        with open(local_file, encoding="utf-8") as fh:
            local = json.load(fh)
    except (OSError, ValueError):
        local = {}
    for scene, n in local.items():
        if scene in table["plots"] and table["plots"][scene] != n:
            raise Stop(f"{scene} stands on plot {n} in the test world, but plots.json gives it "
                       f"{table['plots'][scene]}: one of the two is wrong")
    taken = {**local, **table["plots"]}
    for scene, n in taken.items():
        twice = sorted(s for s, m in taken.items() if m == n)
        if len(twice) > 1:
            raise Stop(f"plot {n} is given to {' and '.join(twice)} (plots.json and what the test world noted)")
    out, new = {}, {}
    for scene in scenes:
        if scene in taken:
            if scene in given and given[scene] != taken[scene]:
                raise Stop(f"{scene} has plot {taken[scene]} already, not {given[scene]}")
            out[scene] = taken[scene]
            continue
        n = given.get(scene, max(list(taken.values()) + list(new.values())) + 1)
        holder = [s for s, m in {**taken, **new}.items() if m == n]
        if holder:
            raise Stop(f"plot {n} is {holder[0]}'s")
        out[scene] = new[scene] = n
    if new:
        os.makedirs(os.path.dirname(local_file), exist_ok=True)
        with open(local_file, "w", encoding="utf-8") as fh:
            json.dump({**local, **new}, fh, indent=1, sort_keys=True)
        say("new plots, to be added to tools/win/plots.json: "
            + ", ".join(f'"{s}": {n}' for s, n in sorted(new.items(), key=lambda kv: kv[1])))
    return {s: [table["base"][0] + n * table["spacing"], table["base"][1], table["base"][2]] for s, n in out.items()}


# ---- the look and the pack ---------------------------------------------------------------------------
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


# ---- shot lists and the pictures to send ---------------------------------------------------------------
def shot_list(scene, lists, only, work):
    """The file with a scene's shots, and the shots that will be taken."""
    name = lists.get(scene, BOARD if scene == MASTER else os.path.join("scenes", scene, "shots.json"))
    if name == BOARD:
        path = os.path.join(work, f"board-{scene}.json")
        # the board is worked out from the skeleton of the code that is shot
        run(os.path.join(TOOLS, "boardshots.py"), "--out", path, env={"C164_BUILD": BUILD})
    else:
        path = os.path.join(BUILD, name)
    if not os.path.exists(path):
        raise Stop(f"{scene} has no shot list ({path}); give one with --shots {scene}=<file>")
    with open(path, encoding="utf-8") as fh:
        shots = json.load(fh)
    if scene in only:
        missing = [n for n in only[scene] if n not in {s["name"] for s in shots}]
        if missing:
            raise Stop(f"{scene} has no shot called {', '.join(missing)}")
        shots = [s for s in shots if s["name"] in only[scene]]
    if not shots:
        raise Stop(f"{scene}: the shot list {path} is empty")
    return path, shots


def to_send(scene, tag, commit, at, shots, target, send, some):
    """Turn a scene's pictures into the files that go back to the cloud machine: JPEGs under the
    names the pipeline gives real-machine pictures, and the note that goes with them. When only
    some of the scene's shots were taken, what an earlier trip under this tag left stays."""
    from PIL import Image
    import shoot
    os.makedirs(send, exist_ok=True)
    stem = f"{scene}-{tag}-"
    note = os.path.join(send, stem + "real.txt")
    rows = {}
    if some:
        try:
            with open(note, encoding="utf-8") as fh:
                for line in fh:
                    parts = line.split()
                    if len(parts) == 4 and not line.startswith("#") \
                            and os.path.exists(os.path.join(send, f"{stem}{parts[0]}.jpg")):
                        rows[parts[0]] = line.strip()
        except OSError:
            pass
    else:
        for old in os.listdir(send):
            if old.startswith(stem):
                os.remove(os.path.join(send, old))
    for shot in shots:
        png = os.path.join(target, shot["name"] + ".png")
        if not os.path.exists(png):
            continue
        jpg = os.path.join(send, f"{stem}{shot['name']}.jpg")
        with Image.open(png) as picture:
            picture.convert("RGB").save(jpg, "JPEG", quality=JPEG_QUALITY, subsampling=0)
        with open(jpg, "rb") as fh:
            digest = hashlib.sha256(fh.read()).hexdigest()[:16]
        rows[shot["name"]] = f"{shot['name']} {shot.get('time', shoot.DEFAULT_TIME)} {commit} {digest}"
    head = ["# real-machine pictures (tools/win/shuttle.py): shot, tick, commit of the code the picture shows, "
            "first 16 of the picture file's sha256",
            f"# scene {scene}, tag {tag}, plot {at[0]} {at[1]} {at[2]}, taken "
            f"{datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}, the game's own screenshots as JPEG {JPEG_QUALITY}"]
    with open(note, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(head + list(rows.values())) + "\n")
    return len(rows)


def pairs(items, what, number=False):
    out = {}
    for item in items:
        if "=" not in item:
            raise SystemExit(f"--{what} wants <scene>=<value>, not {item!r}")
        scene, value = item.split("=", 1)
        out[scene] = int(value) if number else value
    return out


def main():
    global BUILD
    ap = argparse.ArgumentParser(description="one trip of the real-machine render station")
    ap.add_argument("scenes", nargs="+")
    ap.add_argument("--tag", required=True, help="names the pictures: the commit they show, seven digits")
    ap.add_argument("--out", required=True)
    ap.add_argument("--project", default=os.path.dirname(TOOLS), help="the c164-realms whose scenes are shot")
    ap.add_argument("--shots", action="append", default=[], metavar="SCENE=FILE")
    ap.add_argument("--only", action="append", default=[], metavar="SCENE=A,B")
    ap.add_argument("--plot", action="append", default=[], metavar="SCENE=N")
    ap.add_argument("--no-place", action="store_true")
    ap.add_argument("--no-shoot", action="store_true")
    ap.add_argument("--keep-client", action="store_true")
    ap.add_argument("--settle", type=float, default=4.0)
    ap.add_argument("--first-settle", type=float, default=12.0)
    args = ap.parse_args()

    project = os.path.abspath(args.project)
    BUILD = os.path.join(project, "build")
    if not os.path.isdir(os.path.join(BUILD, "scenes")):
        raise SystemExit(f"no scenes in {BUILD}")
    # scenes and the kit they are written with come from the code that is shot; the station's
    # tools (the server, the game, the camera) are the ones beside this file
    sys.path.insert(0, BUILD)
    sys.path.insert(1, TOOLS)
    from artkit import mood as MOOD

    lists = pairs(args.shots, "shots")
    only = {scene: names.split(",") for scene, names in pairs(args.only, "only").items()}
    for scene in list(lists) + list(only):
        if scene not in args.scenes:
            raise SystemExit(f"{scene} is not one of this trip's scenes")
    commit = commit_of(os.path.dirname(project))
    out = os.path.join(os.path.abspath(args.out), args.tag)
    send = os.path.join(out, "send")
    work = os.path.join(os.path.abspath(args.out), "_trip")
    failed, taken, started = [], {}, False
    t0 = time.time()
    say(f"the code that is shot: {project} at {commit}; tag {args.tag}")
    try:
        shutil.rmtree(work, ignore_errors=True)
        os.makedirs(work)
        where = plots(args.scenes, pairs(args.plot, "plot", number=True))
        plan = []
        for scene in args.scenes:
            if args.no_shoot:
                plan.append((scene, where[scene], None, []))
            else:
                plan.append((scene, where[scene], *shot_list(scene, lists, only, work)))

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
            for scene, at, _, _ in plan:
                say(f"placing {scene} at {at[0]} {at[1]} {at[2]}")
                _, text = run(os.path.join(BUILD, "place.py"), scene, "--world", world(),
                              "--pw-file", os.path.join(SERVER, ".rcon_pw"), "--at", *at)
                if "look files changed" in text:
                    raise Stop(f"{scene} changed the look while it was placed; the trip's look was not the scene's")
                if ", 0 failed" not in text:
                    failed.append(f"{scene}: not placed whole")

        # ---- 3. one resource pack ----
        merged, n = merge_pack(args.scenes, os.path.join(work, "packs"))
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
        for scene, at, shots_file, shots in plan:
            if any(f.startswith(scene + ":") for f in failed):
                continue
            target = os.path.join(out, scene)
            if scene not in only:
                shutil.rmtree(target, ignore_errors=True)
            say(f"shooting {scene}: {len(shots)} shots of {os.path.relpath(shots_file, BUILD)}")
            code, _ = run(os.path.join(TOOLS, "shoot.py"), shots_file, "--pw-file", os.path.join(SERVER, ".rcon_pw"),
                          "--out", target, "--origin", *at, "--settle", args.settle,
                          "--first-settle", args.first_settle,
                          *(["--only", ",".join(only[scene])] if scene in only else []), check=False)
            got = len([s for s in shots if os.path.exists(os.path.join(target, s["name"] + ".png"))])
            taken[scene] = (got, len(shots))
            if code != 0 or got != len(shots):
                failed.append(f"{scene}: {got} of {len(shots)} pictures")
            # ---- 5. ready to be sent ----
            if got:
                to_send(scene, args.tag, commit, at, shots, target, send, scene in only)
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
