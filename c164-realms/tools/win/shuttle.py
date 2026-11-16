#!/usr/bin/env python3
"""The shuttle: one trip of the real-machine render station (plan/PIPELINE.md 7).

    python bin/job.py s1 --heavy -- ../tools/win/shuttle.py --tag <commit> --out @out/real <scene> [<scene> ...]

Use bin/trip.py on the admin's computer, tools/nodetrip.py on a worker node: they run this together
with what has to happen before and after (bringing the code up to date, making sure the game is
closed, bringing the pictures home). A trip takes minutes. The server and the game are driven
through winmc.py on Windows and through nodemc.py elsewhere; both take the same commands.

For the scenes named the trip
  1. writes the look (biomes, timelines) the scenes share into the test world and restarts the
     server when those files changed; a trip holds one look, scenes with another need their own;
  2. places every scene on its plot (plots.json beside this file; a scene that has none there gets
     one of the test world's own, from 200 on, which is noted in the test world);
  3. writes one resource pack that holds what all the scenes need and puts it where the client
     reads it; two scenes that want different files under one name stop the trip;
  4. starts the game once (winmc.py checks the free video memory first and keeps the window in the
     background), shoots every scene's shot list, and stops the game again -- also when something
     went wrong on the way;
  5. leaves the pictures in <out>/<tag>/<scene>/<shot>.png and, ready to be sent, in
     <out>/<tag>/send/ as <scene>-<tag>-<shot>.jpg beside a note <scene>-<tag>-real.txt that says
     for every shot its tick, the commit of the code it shows, the first 16 digits of the
     picture file's SHA-256 and when it was taken, and in its heading the distances the game
     drew at (the client's render distance, the server's view distance, the cloud range).
     tools/realshots.py reads it. A trip that takes only some of a scene's shots (--only) leaves
     the others of an earlier trip under the same tag in the note -- when that trip drew at the
     same distances and for the same light version; else they are not this note's to describe.

    --project <dir>          the c164-realms whose scenes are shot (default: the one this file is in).
                             The station's own tools stay the ones beside this file, so a branch
                             that carries older tools, or none, can be shot all the same
    --commit <commit>        the commit the note names as the code the pictures show (default: the
                             one the project's checkout stands on)
    --shots <scene>=<file>   another shot list for a scene (default: scenes/<scene>/shots.json; a
                             relative path is taken from the project's build/). The word "board" is
                             the twelve board views, worked out from the project's skeleton by
                             tools/boardshots.py; it is the default for the master scene, obs
    --only <scene>=<a,b>     only these shots of a scene
    --gallery <scene>        also lay out the scene's models in a row of bays (build/gallery.py,
                             beside the scene's plot) and shoot each bay by day: gal_<bay>. A
                             scene that has models but no shot list is shown by its gallery alone
    --plot <scene>=<n>       the plot of a scene the table does not hold yet
    --look <name>            the scenes are built for this light version (blue, deep, glow, or
                             a trial of the sky line) and every shot is taken at its tick,
                             whatever the list says: its table says which windows are lit, and
                             windows are blocks (tools/placelook.py; the scenes of the
                             observatory, whose fronts ask the sky line's light kit). The note
                             says so
    --dress                  with --look: the building's own lights are on as well, which the
                             code keeps off (sky/lights DRESS). The note says so
    --again <scene>=<shot>[:<seconds>][,...]
                             the shot is taken once more, so many seconds (2.5) after its
                             picture and from the same place, as <shot>_again: for what moves
    --step <scene>=<shot>[:<blocks>][,...]
                             the shot is taken once more from so many blocks (0.5) to the
                             camera's right, looking the same way, as <shot>_step: two stills a
                             step apart, for thin things that may shimmer when one walks past
                             (where a line breaks up differently in the two, it will)
    --after <scene>=<script> after the scene's shots, while it stands, the server runs and the
                             game is open, a script of the code that is shot (a path from its
                             build/) is run as <script> --pw-file <file> --port <n> --origin X Y Z:
                             what no picture shows, commands typed on the server and scoreboards
                             read. What it prints goes into <out>/<tag>/send/<scene>-<tag>-after.txt;
                             it has --after-budget seconds (300), and an exit code other than 0
                             counts as a failure of the trip. It must leave the server running
    --no-place               the scenes stand already; only the pack and the pictures
    --no-shoot               everything but the game: place and write the pack
    --keep-client            leave the game running at the end (only with the owner's consent)
    --settle, --first-settle seconds to wait before a picture, and before a scene's first one
    --still <seconds>        after that wait every picture is taken again until two in a row are
                             alike, this long at most (shoot.py; for a machine that draws slowly)

Exit code: 0 all pictures taken; 3 not enough free video memory, nothing was started; 1 otherwise.
"""
import argparse
import datetime
import filecmp
import hashlib
import importlib
import json
import math
import os
import re
import shutil
import signal
import subprocess
import sys
import threading
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
GALLERY_Z = 400             # a scene's gallery stands this far south of its plot's origin
AGAIN = "_again"            # the name of a shot's second picture (--again)
STEP = "_step"              # the name of a shot's picture from a step to the side (--step)
JPEG_QUALITY = 90
BUILD = None                # the build/ folder of the code that is shot; set in main()


def say(text):
    print(f"[shuttle {time.strftime('%H:%M:%S')}] {text}")
    sys.stdout.flush()


class Stop(Exception):
    def __init__(self, why, code=1):
        super().__init__(why)
        self.code = code


# Whoever runs the trip may say that its time is over (SIGTERM; tools/nodetrip.py does at the end
# of the time a node job has). The scripts that run in our process group get the signal with us
# and end; the trip then makes ready what was shot so far, closes the game and ends: pictures
# that were taken are not lost with the ones that were not.
OVER = threading.Event()
APART = []                  # scripts in a session of their own (run(budget=...)): ended with us


def kill(proc):
    """End a script and what it started in a session of its own."""
    try:
        if hasattr(os, "killpg"):
            os.killpg(proc.pid, signal.SIGKILL)
        else:
            proc.kill()
    except OSError:
        pass


def asked_to_end(*_):
    OVER.set()
    for proc in list(APART):
        kill(proc)


def run(script, *args, check=True, env=None, budget=None, hide=None):
    """Run a Python script with this Python, from the shot code's build/; its output goes to ours,
    line by line as it comes. Returns (exit code, output). With `budget` the script and what it
    started are ended when so many seconds are over; the exit code is then 124. `hide` is a word
    that must not show in the output, whatever the script prints."""
    proc = subprocess.Popen([sys.executable, "-u", script, *[str(a) for a in args]], cwd=BUILD, text=True,
                            encoding="utf-8", errors="replace", stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            stdin=subprocess.DEVNULL, start_new_session=budget is not None,
                            env={**os.environ, "PYTHONIOENCODING": "utf-8", **(env or {})})
    over = threading.Event()

    def end():
        over.set()
        kill(proc)

    timer = threading.Timer(budget, end) if budget is not None else None
    if timer:
        timer.daemon = True
        timer.start()
        APART.append(proc)
    lines = []
    try:
        for line in proc.stdout:
            lines.append(line.rstrip("\n").replace(hide, "***") if hide else line.rstrip("\n"))
            print("    " + lines[-1])
            sys.stdout.flush()
        code = proc.wait()
    finally:
        if timer:
            timer.cancel()
            APART.remove(proc)
    if over.is_set():
        code = 124
    if check and code != 0:
        raise Stop(f"{os.path.basename(script)} {' '.join(str(a) for a in args[:1])} ended with {code}", code)
    return code, "\n".join(lines)


def winmc(command, check=True):
    """A command to the station's server and game: winmc.py on Windows, nodemc.py on a worker node."""
    return run(os.path.join(TOOLS, "winmc.py" if os.name == "nt" else "nodemc.py"), command, check=check)


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
# The table (plots.json) holds the scenes of the assembly and gives them the plots below LOCAL_FROM
# (tools/boardnext.sh adds the new ones). A scene the table does not hold -- a work branch's, shot on
# request -- gets a plot of the test world's own from LOCAL_FROM on, noted in that test world. The
# two never meet: a station's note cannot take a number the table gives out later. (Until 11-16
# 09:35 the notes took the next number after the table's last, and the table then grew into them:
# "plot 78 is given to ..." on two nodes; the table skipped to 90 once, over those notes.)
LOCAL_FROM = 200


def plots(scenes, given):
    """{scene: plot number}. The table beside this file comes first. A scene it does not hold keeps
    the plot noted in the test world on an earlier trip, or takes the one given with --plot, or
    the next free one from LOCAL_FROM on; what is new is noted in the test world, so that the scene
    stays where it is. A noted scene the table holds by now takes the table's plot."""
    with open(os.path.join(HERE, "plots.json"), encoding="utf-8") as fh:
        table = json.load(fh)
    local_file = os.path.join(world(), "datapacks", NAMESPACE, "plots.local.json")
    try:
        with open(local_file, encoding="utf-8") as fh:
            local = json.load(fh)
    except (OSError, ValueError):
        local = {}
    moved = {}
    for scene, n in list(local.items()):
        if scene in table["plots"] and table["plots"][scene] != n:
            # a scene of a work branch that was shot here before the table held it, and has come into
            # the assembly since: the table's plot is the scene's from now on. What stands on the old
            # plot stays there; the table gives no number from LOCAL_FROM on, so nothing is put on it
            moved[scene] = local.pop(scene)
            say(f"{scene} stood on plot {moved[scene]} in this test world (a trip before the table held it); "
                f"the table gives it {table['plots'][scene]} now and it is placed there")
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
        # a plot of this test world's own: from LOCAL_FROM on, where the table never comes
        n = given.get(scene, max([LOCAL_FROM - 1] + list(taken.values()) + list(new.values())) + 1)
        holder = [s for s, m in {**taken, **new}.items() if m == n]
        if holder:
            raise Stop(f"plot {n} is {holder[0]}'s")
        out[scene] = new[scene] = n
    if new or moved:
        os.makedirs(os.path.dirname(local_file), exist_ok=True)
        with open(local_file, "w", encoding="utf-8") as fh:
            json.dump({**local, **new}, fh, indent=1, sort_keys=True)
    if new:
        say("new plots, this test world's own (a scene of the assembly gets its plot in tools/win/plots.json): "
            + ", ".join(f'"{s}": {n}' for s, n in sorted(new.items(), key=lambda kv: kv[1])))
    return {s: [table["base"][0] + n * table["spacing"], table["base"][1], table["base"][2]] for s, n in out.items()}


# ---- the look and the pack ---------------------------------------------------------------------------
def look_of(scene):
    """(biomes, timelines) of a scene's mood module, or None when it has none. A look that the
    resource pack carries (artkit.mood.Carried, in the code that has it) has no registry file: it
    is ({}, {}) here, so that step 1 only takes an earlier trip's biomes and timelines out of the
    data pack, as build/place.py does for such a look; build/makepack.py puts its files into the
    scene's pack and build/place.py holds the clock at its hour (held_clock)."""
    try:
        look = importlib.import_module(f"scenes.{scene}.mood")
    except ModuleNotFoundError as e:
        if e.name != f"scenes.{scene}.mood":
            raise
        return None
    from artkit import mood as MOOD
    if getattr(MOOD, "carried", lambda module: None)(look) is not None:
        return {}, {}
    return look.BIOMES, getattr(look, "TIMELINES", None) or {}


def held_clock(scenes):
    """The tick the world's clock is held at under a look that the resource pack carries, or None
    when no scene of the trip stands under one. build/place.py stops the clock there and notes it
    as "clock" in <scene>.placed.json; the pack's sky is painted for that one hour and is the same
    over every plot, so the whole trip is shot in it, whatever "time" a shot names."""
    found = {}
    for scene in scenes:
        try:
            with open(os.path.join(world(), "datapacks", NAMESPACE, f"{scene}.placed.json"), encoding="utf-8") as fh:
                tick = json.load(fh).get("clock")
        except (OSError, ValueError, AttributeError):
            continue
        if tick is not None:
            found.setdefault(int(tick), []).append(scene)
    if len(found) > 1:
        groups = "; ".join(f"{tick}: {', '.join(names)}" for tick, names in sorted(found.items()))
        raise Stop(f"these scenes hold the clock at different hours, and a trip has one sky: {groups}. "
                   f"Run them in separate trips.")
    return next(iter(found), None)


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
def stepped(shot, blocks):
    """The shot from a place so many blocks to the camera's right, level, looking the same way."""
    pos = shot["pos"]
    if "look_at" in shot:
        fx, fz = shot["look_at"][0] - pos[0], shot["look_at"][2] - pos[2]
    else:
        yaw = math.radians(shot.get("yaw", 0.0))        # the game's yaw: 0 looks along +z
        fx, fz = -math.sin(yaw), math.cos(yaw)
    n = math.hypot(fx, fz)
    rx, rz = (-fz / n, fx / n) if n > 1e-9 else (1.0, 0.0)      # straight up or down: any side
    moved = {**shot, "name": shot["name"] + STEP,
             "pos": [round(pos[0] + rx * blocks, 3), pos[1], round(pos[2] + rz * blocks, 3)]}
    if "look_at" in shot:
        to = shot["look_at"]
        moved["look_at"] = [round(to[0] + rx * blocks, 3), to[1], round(to[2] + rz * blocks, 3)]
    return moved


def shot_list(scene, lists, only, work, again=None, step=None):
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
    more = [(option, end, asked[scene]) for option, end, asked in (("--again", AGAIN, again), ("--step", STEP, step))
            if asked and scene in asked]
    if more:
        names = {s["name"] for s in shots}
        for option, end, asked in more:
            wrong = [n for n in asked if n not in names or n + end in names]
            if wrong:
                raise Stop(f"{scene}: {option} names {', '.join(wrong)}, which is not one of the shots taken "
                           f"(or there is a shot called {wrong[0]}{end} already)")
        twice = []
        for shot in shots:
            twice.append(shot)
            if again and shot["name"] in again.get(scene, {}):
                # from the same place, so the camera does not move: only the wait, then one picture
                twice.append({**shot, "name": shot["name"] + AGAIN, "settle": again[scene][shot["name"]], "still": 0})
            if step and shot["name"] in step.get(scene, {}):
                twice.append(stepped(shot, step[scene][shot["name"]]))
        path, shots = os.path.join(work, f"shots-{scene}.json"), twice
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(shots, fh, indent=1)
    return path, shots


def gallery(scene, at, work):
    """Lay out a scene's gallery beside its plot. Returns the shot list's file and its shots: one a
    bay, by day, in the world's coordinates."""
    path = os.path.join(work, f"gallery-{scene}.json")
    run(os.path.join(BUILD, "gallery.py"), scene, "--pw-file", os.path.join(SERVER, ".rcon_pw"),
        "--at", at[0], at[1], at[2] + GALLERY_Z, "--shots", path)
    with open(path, encoding="utf-8") as fh:
        bays = json.load(fh)
    for bay in bays:
        bay["name"] = "gal_" + bay["name"]
        bay.setdefault("time", "noon")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(bays, fh, indent=1)
    return path, bays


def distances():
    """The distances the game draws at, as its own files give them: "render distance 12, server
    view distance 12, cloud range 128"; "?" where a file does not say."""
    def find(path, pattern):
        try:
            with open(path, encoding="utf-8") as fh:
                m = re.search(pattern, fh.read(), re.M)
        except OSError:
            return "?"
        return m.group(1) if m else "?"
    options = os.path.join(GAME, "options.txt")
    client = find(options, r"^renderDistance:(\d+)")
    server = find(os.path.join(SERVER, "server.properties"), r"^view-distance=(\d+)")
    clouds = find(options, r"^cloudRange:(\d+)")
    return f"render distance {client}, server view distance {server}, cloud range {clouds}"


def how_made(*said):
    """How the pictures were made, from what shoot.py said of them (its closing line)."""
    game = off = 0
    for text in said:
        for a, b in re.findall(r"^pictures: (\d+) saved by the game itself, (\d+) taken off the display\s*$", text, re.M):
            game, off = game + int(a), off + int(b)
    if off and game:
        return f"{game} of the game's own screenshots and {off} pictures taken off the client's display"
    return "pictures taken off the client's display" if off else "the game's own screenshots"


def to_send(scene, tag, commit, at, shots, target, send, some, how="the game's own screenshots", time=None,
            look=None, dress=False, trial=None):
    """Turn a scene's pictures into the files that go back to the cloud machine: JPEGs under the
    names the pipeline gives real-machine pictures, and the note that goes with them. When only
    some of the scene's shots were taken, what an earlier trip under this tag left stays, each
    picture with the time it was taken at -- but only when that trip drew under what this one
    draws under (the distances, the light version): the note's head says these once for all its
    pictures, so pictures drawn under anything else are not kept under it."""
    from PIL import Image
    import shoot
    os.makedirs(send, exist_ok=True)
    stem = f"{scene}-{tag}-"
    note = os.path.join(send, stem + "real.txt")
    now = datetime.datetime.now()
    under = [f"# distances: {distances()}"]
    if look:
        under.append(f"# windows: lit by the table of look {look} (the scene was built for that light version)"
                     + (f"; shot as its trial {trial}" if trial else "")
                     + ("; the building's own lights on (sky/lights DRESS, which the code keeps off)" if dress else ""))
    rows = {}
    if some:
        was_under, was_taken, earlier = [], None, []
        try:
            with open(note, encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if line.startswith(("# distances:", "# windows:")):
                        was_under.append(line)
                    elif line.startswith("#"):
                        m = re.search(r"taken (\d{4}-\d\d-\d\d) (\d\d:\d\d)", line)
                        was_taken = f"{m.group(1)}T{m.group(2)}" if m else was_taken
                    elif len(line.split()) in (4, 5):
                        earlier.append(line.split())
        except OSError:
            pass
        if was_under == under:
            for parts in earlier:
                if os.path.exists(os.path.join(send, f"{stem}{parts[0]}.jpg")):
                    # a line of four is of a note written before the lines said when: the head's time
                    rows[parts[0]] = " ".join(parts + ([was_taken] if len(parts) == 4 and was_taken else []))
        elif earlier:
            left = [parts[0] for parts in earlier if parts[0] not in {shot["name"] for shot in shots}]
            for name in left:
                if os.path.exists(os.path.join(send, f"{stem}{name}.jpg")):
                    os.remove(os.path.join(send, f"{stem}{name}.jpg"))
            say(f"{scene}: the earlier trip under tag {tag} drew under other distances or another light version "
                f"({'; '.join(line[2:] for line in was_under) or 'its note does not say which'}): "
                + (f"its {len(left)} other pictures ({', '.join(left)}) are not carried into this trip's note"
                   if left else "none of its pictures is carried into this trip's note"))
    else:
        for old in os.listdir(send):
            if old.startswith(stem):
                os.remove(os.path.join(send, old))
    for shot in shots:
        png = os.path.join(target, shot["name"] + ".png")
        if not os.path.exists(png):
            continue
        jpg = os.path.join(send, f"{stem}{shot['name']}.jpg")
        try:
            with Image.open(png) as picture:
                picture.convert("RGB").save(jpg, "JPEG", quality=JPEG_QUALITY, subsampling=0)
        except OSError as exc:      # half a file, of a run that was cut short while it wrote it
            say(f"{scene}: {shot['name']}.png cannot be read ({exc}); it is left out")
            if os.path.exists(jpg):
                os.remove(jpg)
            continue
        with open(jpg, "rb") as fh:
            digest = hashlib.sha256(fh.read()).hexdigest()[:16]
        rows[shot["name"]] = (f"{shot['name']} {time if time is not None else shot.get('time', shoot.DEFAULT_TIME)} "
                              f"{commit} {digest} {now.strftime('%Y-%m-%dT%H:%M')}")
    head = ["# real-machine pictures (tools/win/shuttle.py): shot, tick, commit of the code the picture shows, "
            "first 16 of the picture file's sha256, when it was taken",
            f"# scene {scene}, tag {tag}, plot {at[0]} {at[1]} {at[2]}, taken "
            f"{now.strftime('%Y-%m-%d %H:%M')}, {how} as JPEG {JPEG_QUALITY}"] + under
    with open(note, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(head + list(rows.values())) + "\n")
    return len(rows)


def shown(path):
    """A file's path as the log shows it: from build/ when it is the project's, else its name."""
    return os.path.relpath(path, BUILD) if path.startswith(BUILD + os.sep) else os.path.basename(path)


def asked_after(scene, script, at, budget, send, tag, commit):
    """Run a script of the code that is shot while its scene stands, the server runs and the game
    is open: what no picture shows (commands typed on the server, scoreboards read). It is run as
    <script> --pw-file <file> --port <n> --origin X Y Z from the shot code's build/, with that
    folder, the station's tools and the shot code's own on its Python path. What it prints is kept
    beside the pictures to send. Returns what went wrong, as a list."""
    project = os.path.dirname(BUILD)
    path = os.path.normpath(os.path.join(BUILD, script))
    if os.path.isabs(script) or not path.startswith(project + os.sep) or not os.path.isfile(path):
        return [f"{scene}: no script {script} in the code that is shot (--after wants a path from its build/)"]
    secret_file = os.path.join(SERVER, ".rcon_pw")
    try:
        with open(secret_file) as fh:
            secret = fh.read().strip()
    except OSError:
        secret = ""
    say(f"{scene}: the scene's own script {shown(path)}, {budget:.0f} s at most")
    t0 = time.time()
    # whatever the script prints, the server's password stays on this machine
    code, text = run(path, "--pw-file", secret_file, "--port", RCON_PORT, "--origin", *at, check=False, budget=budget,
                     hide=secret, env={"PYTHONPATH": os.pathsep.join([BUILD, TOOLS, os.path.join(project, "tools")])})
    os.makedirs(send, exist_ok=True)
    with open(os.path.join(send, f"{scene}-{tag}-after.txt"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write(f"# {shown(path)} of {commit}, run after the shots of {scene} (plot {at[0]} {at[1]} {at[2]}), "
                 f"{datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}: exit code {code}, {time.time() - t0:.0f} s"
                 + (f"; it was stopped, its {budget:.0f} s were over" if code == 124 else "") + "\n" + text + "\n")
    say(f"{scene}: {os.path.basename(path)} ended with {code} after {time.time() - t0:.0f} s")
    return [] if code == 0 else [f"{scene}: {os.path.basename(path)} ended with {code}"]


def pairs(items, what, number=False, names=False):
    """<scene>=<value> options as a dict. With `names` the value is a list of names, and an option
    given twice for one scene adds to the list; any other option given twice for one scene is a
    mistake, not something to take the last of."""
    out = {}
    for item in items:
        if "=" not in item:
            raise SystemExit(f"--{what} wants <scene>=<value>, not {item!r}")
        scene, value = item.split("=", 1)
        if scene in out and not names:
            raise SystemExit(f"--{what} is given twice for {scene}")
        out[scene] = int(value) if number else (out[scene] + "," + value if scene in out else value)
    return out


def main():
    global BUILD
    ap = argparse.ArgumentParser(description="one trip of the real-machine render station")
    ap.add_argument("scenes", nargs="+")
    ap.add_argument("--tag", required=True, help="names the pictures: the commit they show, seven digits")
    ap.add_argument("--out", required=True)
    ap.add_argument("--project", default=os.path.dirname(TOOLS), help="the c164-realms whose scenes are shot")
    ap.add_argument("--commit", help="the commit the note names (default: the project's checkout's)")
    ap.add_argument("--shots", action="append", default=[], metavar="SCENE=FILE")
    ap.add_argument("--only", action="append", default=[], metavar="SCENE=A,B")
    ap.add_argument("--plot", action="append", default=[], metavar="SCENE=N")
    ap.add_argument("--gallery", action="append", default=[], metavar="SCENE")
    ap.add_argument("--look")
    ap.add_argument("--dress", action="store_true")
    ap.add_argument("--again", action="append", default=[], metavar="SCENE=SHOT[:SECONDS]")
    ap.add_argument("--step", action="append", default=[], metavar="SCENE=SHOT[:BLOCKS]")
    ap.add_argument("--after", action="append", default=[], metavar="SCENE=SCRIPT")
    ap.add_argument("--after-budget", type=float, default=300.0)
    ap.add_argument("--no-place", action="store_true")
    ap.add_argument("--no-shoot", action="store_true")
    ap.add_argument("--keep-client", action="store_true")
    ap.add_argument("--settle", type=float, default=4.0)
    ap.add_argument("--first-settle", type=float, default=12.0)
    ap.add_argument("--still", type=float, default=0.0)
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
    only = {scene: names.split(",") for scene, names in pairs(args.only, "only", names=True).items()}
    again, step = {}, {}
    for option, given, into, usual, unit in (("again", args.again, again, 2.5, "seconds"),
                                             ("step", args.step, step, 0.5, "blocks")):
        for scene, names in pairs(given, option, names=True).items():
            into[scene] = {}
            for name in names.split(","):
                shot, _, number = name.partition(":")
                try:
                    into[scene][shot] = float(number or usual)
                except ValueError:
                    raise SystemExit(f"--{option} {scene}={name}: {number!r} is not a number of {unit}")
    after = pairs(args.after, "after")
    for scene in list(lists) + list(only) + list(again) + list(step) + list(after) + args.gallery:
        if scene not in args.scenes:
            raise SystemExit(f"{scene} is not one of this trip's scenes")
    if args.dress and not args.look:
        raise SystemExit("--dress goes with --look <name> (blue is the default light version)")
    placelook = os.path.join(TOOLS, "placelook.py")
    # a scene that is only a set of models (no shot list, a gallery asked for) is not placed
    models_only = {scene for scene in args.gallery if scene not in lists and scene != MASTER
                   and not os.path.exists(os.path.join(BUILD, "scenes", scene, "shots.json"))}
    commit = args.commit or commit_of(os.path.dirname(project))
    out = os.path.join(os.path.abspath(args.out), args.tag)
    send = os.path.join(out, "send")
    work = os.path.join(os.path.abspath(args.out), "_trip")
    failed, taken, started = [], {}, False
    t0 = time.time()
    signal.signal(signal.SIGTERM, asked_to_end)
    say(f"the code that is shot: {project} at {commit}; tag {args.tag}")
    try:
        shutil.rmtree(work, ignore_errors=True)
        os.makedirs(work)
        where = plots(args.scenes, pairs(args.plot, "plot", number=True))
        plan = []
        for scene in args.scenes:
            if args.no_shoot or scene in models_only:
                plan.append((scene, where[scene], None, []))
            else:
                plan.append((scene, where[scene], *shot_list(scene, lists, only, work, again, step)))
        when = windows = None
        if args.look:
            # the tick of that light version and the look whose windows it has, as the code that is
            # shot says them; an unknown look stops here
            _, text = run(placelook, "--tick", args.look)
            when, windows = text.strip().splitlines()[-1].split()
            say(f"look {args.look}: shot at tick {when}" + (f", a trial of {windows}" if windows != args.look else ""))

        # ---- 1. the look ----
        look = one_look(args.scenes)
        restart = False
        data = os.path.join(world(), "datapacks", NAMESPACE)
        if look is not None:
            if not os.path.exists(os.path.join(data, "pack.mcmeta")):
                # a world that never held a scene: the data pack has to exist before the server
                # starts, or the look in it is not read. A scene that carries the look writes it.
                first = next(scene for scene in args.scenes if look_of(scene) is not None)
                run(os.path.join(BUILD, "place.py"), first, "--world", world(),
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
                if scene in models_only:
                    continue
                say(f"placing {scene} at {at[0]} {at[1]} {at[2]}" + (f", built for look {args.look}" if args.look else ""))
                place = [placelook, args.look] + (["--dress"] if args.dress else []) if args.look \
                    else [os.path.join(BUILD, "place.py")]
                _, text = run(*place, scene, "--world", world(),
                              "--pw-file", os.path.join(SERVER, ".rcon_pw"), "--at", *at)
                if "look files changed" in text:
                    raise Stop(f"{scene} changed the look while it was placed; the trip's look was not the scene's")
                if ", 0 failed" not in text:
                    failed.append(f"{scene}: not placed whole")
        clock = held_clock([scene for scene, _, _, _ in plan if scene not in models_only])
        if clock is not None:
            say(f"the look is carried by the resource pack and the clock is held at {clock}: every picture of this "
                f"trip is taken at that tick" + (f", not at look {args.look}'s {when}" if when is not None else ""))

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
            if OVER.is_set():
                raise Stop(f"asked to end before {scene} was shot")
            if any(f.startswith(scene + ":") for f in failed):
                continue
            target = os.path.join(out, scene)
            if scene not in only:
                shutil.rmtree(target, ignore_errors=True)
            else:
                # a shot that fails now must not be stood in for by an earlier trip's picture of it
                for shot in shots:
                    if os.path.exists(os.path.join(target, shot["name"] + ".png")):
                        os.remove(os.path.join(target, shot["name"] + ".png"))
            code, said, said_too = 0, "", ""
            if shots_file:
                say(f"shooting {scene}: {len(shots)} shots of {shown(shots_file)}")
                code, said = run(os.path.join(TOOLS, "shoot.py"), shots_file,
                              "--pw-file", os.path.join(SERVER, ".rcon_pw"),
                              "--out", target, "--origin", *at, "--settle", args.settle,
                              "--first-settle", args.first_settle, "--still", args.still,
                              *(["--clock", clock] if clock is not None else ["--time", when] if when is not None else []),
                              *(["--only", ",".join(s["name"] for s in shots)] if scene in only else []), check=False)
            if scene in args.gallery:
                bays_file, bays = gallery(scene, at, work)
                say(f"shooting {scene}'s gallery: {len(bays)} bays")
                again, said_too = run(os.path.join(TOOLS, "shoot.py"), bays_file,
                               "--pw-file", os.path.join(SERVER, ".rcon_pw"), "--out", target,
                               "--settle", args.settle, "--first-settle", args.first_settle,
                               "--still", args.still, *(["--clock", clock] if clock is not None else []), check=False)
                code, shots = code or again, shots + bays
            got = len([s for s in shots if os.path.exists(os.path.join(target, s["name"] + ".png"))])
            taken[scene] = (got, len(shots))
            if code != 0 or got != len(shots):
                failed.append(f"{scene}: {got} of {len(shots)} pictures")
            # ---- 5. ready to be sent ----
            if got:
                to_send(scene, args.tag, commit, at, shots, target, send, scene in only, how_made(said, said_too),
                        clock if clock is not None else when, windows, args.dress,
                        args.look if windows != args.look else None)
            if OVER.is_set():
                raise Stop(f"asked to end while {scene} was shot; what was taken of it is ready")
            # ---- 6. what the scene's author wants asked of the server while the scene stands ----
            if scene in after:
                failed += asked_after(scene, after[scene], at, args.after_budget, send, args.tag, commit)
    except Stop as stop:
        say(f"stopped: {stop}" + (" (the trip was asked to end: its time was over)" if OVER.is_set() else ""))
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
