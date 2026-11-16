#!/usr/bin/env python3
"""One trip into a save on a worker node: a world as it was exported for the Realm is opened by the
node's server just as it comes, the real client joins it, and what a visitor would see is shot.
The shuttle (nodetrip.py) shoots scenes that it places itself in the test world; this shoots a
save nobody touches -- the pictures by which a candidate for the Realm is accepted.

    bash c164-realms/tools/nodejob.sh --always --tail 40 --limit 780 python tools/savetrip.py \\
        --branch cursor/c164-dist-f4b8 --zip dist/A3/c164-A3.zip [--at <commit>] [--sha256 <hex>] \\
        [--board <commit>] [--only as_joined,v01_arrival,...] [--budget 600]     (timeout_sec=900)

The trip
  1. fetches the branch, tests the commit's provenance (tools/provenance.sh) and takes the zip out
     of it (git show: no checkout); the file's SHA-256 is worked out, and must be --sha256 when
     that is given;
  2. stops whatever an earlier job left running, and unpacks the save as server26/save/ -- the
     folder of an earlier trip goes first. The zip must hold one world: one folder with level.dat;
  3. reads level.dat: the game mode and the difficulty the world carries. The node's server is
     set to exactly these and to not forcing the mode, the way a Realm's slot is filled from an
     uploaded world; view distance 10 as a Realm has, render distance 12 as the board's;
  4. gives the client the save's own resource pack (resourcepacks/resources.zip in the save) as
     its pack; a save without one is shot with the game's own textures. Whether a Realm hands
     the pack to those who join is not shown by this trip: here the client has it either way;
  5. starts the server on the save and asks it, before anybody joins, for its hour, whether the
     clock runs, the difficulty and the data packs; starts the game, which joins as a new player.
     The note says which graphics backend the game came up with: Vulkan as a node has it, or
     OpenGL when the job is started with MC_GL=egl (env MC_GL=egl python tools/savetrip.py ...
     --name <name>-gl) -- a pack with shaders is to be seen under both;
  6. takes `as_joined`: the picture of where the save puts a newcomer, in the game mode it gives,
     with nothing asked of the server before it (no move, no game mode, no time) -- and asks the
     server where the player stands, which way it looks and in which mode;
  7. takes the twelve board views of this checkout (tools/win/shots/obs-board.json, around the
     plot origin 0 200 0, where the export puts the scene) as a spectator, the save's clock left
     alone (shoot.py --keep-clock): the hour in the pictures is the save's own;
  8. keeps the pictures as JPEGs in renders/real-save/<name>/ with real.txt (what was shot, of
     which file, at which distances, what the server answered), sheet.jpg, and beside.jpg: each
     board view as the test world's board has it (renders/real/obs/) beside the save's;
  9. keeps the log in renders/real/_trips/<time>-<commit>-save-<name>.log, what the game said on
     shaders and packs in ...-client.txt and the server's warnings and errors in ...-server.txt;
 10. stops everything and sets the node back to the test world, whatever happened before.

    --branch <name>          the branch that holds the zip
    --at <commit>            the commit of that branch (default: its head)
    --zip <path>             the zip's path in that commit, from c164-realms/
    --sha256 <hex>           what the zip's SHA-256 must be (the export's page names it)
    --name <name>            the folder under renders/real-save/ (default: the zip's name)
    --board <commit>         the assembly commit the save was exported from, for the note (the
                             stations are this checkout's either way; the trip says when the test
                             world's board in renders/real/obs/ is of another commit)
    --only <a,b>             only these of as_joined and the twelve views (and the stops of --also)
    --again <a,b>            these views three times more from where the camera stands, half a second
                             apart (<name>_2 .. _4): what comes and goes in a view is in one of them
    --also <file>            further stops after the twelve, a list in tools/win/shots/ (may be given
                             more than once). save-asked.json: the views somebody asked for in the save.
                             save-listen.json: beside the master clock, in the power house and at the
                             telegraph, inside the reach of the sounds played there, long enough for each
                             to come round; the trip's log says what the game complained of about sounds
    --view, --server-view, --clouds, --settle, --first-settle, --still   as nodetrip.py has them
    --budget <seconds>       the trip stops what it is doing after this long and closes down (600)

Exit code 0: every picture asked for was taken and is kept, the save's pack was loaded by the game,
and the server said nothing that counts as an error while it opened the save.
"""
import argparse
import gzip
import hashlib
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import time
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import nodetrip  # noqa: E402
import savelit  # noqa: E402
from nodetrip import ROOT, WORK, CLOSING, Trip, end, git  # noqa: E402

SERVER = os.path.join(ROOT, "server26")
GAME = os.path.join(ROOT, "client26", "game")
PACK = os.path.join(GAME, "resourcepacks", "c164art")
LEVEL = "save"                      # the folder under server26/ a save is unpacked as
ORIGIN = (0, 200, 0)                # where the export puts the scene: the plot origin of obs in the test world too
STATIONS = os.path.join(HERE, "win", "shots", "obs-board.json")
JOINED = "as_joined"
MODES = {0: "survival", 1: "creative", 2: "adventure", 3: "spectator"}
DIFFICULTIES = {0: "peaceful", 1: "easy", 2: "normal", 3: "hard"}
JPEG_QUALITY = 90
# The hour of the day the world keeps. 26.3 has clocks and timelines: `time query daytime` is no
# more, the day is the timeline minecraft:day ("Timeline minecraft:day is at 20370 tick(s)").
HOUR = "time query minecraft:day"
# What the node's server says of itself at every start, whatever world it opens: not the save's.
OWN_WORDS = re.compile(r"OFFLINE/INSECURE MODE|make no attempt to authenticate|possible to play without internet|"
                       r'set "online-mode" to "true"')
KEPT = os.path.join("renders", "real-save")
HEAD = ("# pictures of a save opened as it comes (tools/savetrip.py): shot, the save's hour (daytime) when it was "
        "taken, commit that holds the zip, first 16 of the picture file's sha256, when it was taken, the distances")


def digest(path, whole=False):
    with open(path, "rb") as fh:
        found = hashlib.sha256(fh.read()).hexdigest()
    return found if whole else found[:16]


def clean_commit(branch, at):
    """The commit of `branch` to take the zip from: fetched, of that branch, of clean provenance."""
    if git("fetch", "-q", "origin", branch) is None:
        sys.exit(f"--branch {branch}: cannot be fetched from origin")
    head = git("rev-parse", "FETCH_HEAD")
    if git("rev-parse", "--is-shallow-repository") == "true":
        if git("fetch", "-q", "--unshallow", "origin", branch) is None:
            sys.exit(f"--branch {branch}: this clone is cut short and its history could not be fetched")
    commit = head
    if at:
        commit = git("rev-parse", "--verify", "--quiet", at + "^{commit}")
        if not commit:
            sys.exit(f"--at {at}: no such commit in {branch}")
        if git("merge-base", "--is-ancestor", commit, head) is None:
            sys.exit(f"--at {at} is not a commit of {branch} (its head is {head[:8]})")
    clean = subprocess.run(["bash", os.path.join(HERE, "provenance.sh"), commit], capture_output=True, text=True)
    if clean.returncode != 0:
        sys.exit(f"{commit[:8]} of {branch} is not shot: tools/provenance.sh says\n"
                 + (clean.stdout + clean.stderr).strip()[-600:])
    return commit


def members(archive, what):
    """The names in a zip, none of which may lead out of the folder it is unpacked into."""
    names = archive.namelist()
    for name in names:
        parts = name.replace("\\", "/").split("/")
        if name.startswith(("/", "\\")) or ".." in parts or (parts[0].endswith(":")):
            raise SystemExit(f"{what}: the name {name!r} leads out of the folder")
    return names


def unpack(zip_path, into):
    """The save in `zip_path` as the folder `into`. Returns the name of the world's folder in the zip."""
    with zipfile.ZipFile(zip_path) as archive:
        names = members(archive, "the save's zip")
        tops = {name.split("/")[0] for name in names}
        worlds = [top for top in tops if f"{top}/level.dat" in names]
        if len(worlds) != 1 or len(tops) != 1:
            raise SystemExit(f"the zip does not hold one world: its top folders are {', '.join(sorted(tops))[:200]}, "
                             f"{len(worlds)} of them with level.dat")
        staging = into + ".unpacking"
        shutil.rmtree(staging, ignore_errors=True)
        archive.extractall(staging)
    shutil.rmtree(into, ignore_errors=True)
    os.replace(os.path.join(staging, worlds[0]), into)
    shutil.rmtree(staging, ignore_errors=True)
    return worlds[0], len(names)


def level_facts(world):
    """What level.dat says a Realm's slot is filled from: {"name", "mode", "difficulty", "spawn", "version",
    "commands", "packs"}; a value the file does not give in the way known here is None."""
    import nbtlib
    with gzip.open(os.path.join(world, "level.dat"), "rb") as fh:
        data = nbtlib.File.parse(fh).get("Data", {})
    mode = data.get("GameType")
    hard = data.get("difficulty_settings", {}).get("difficulty", data.get("Difficulty"))
    if hard is not None and not isinstance(hard, str):
        hard = DIFFICULTIES.get(int(hard))
    spawn = data.get("spawn", {})
    return {
        "name": str(data["LevelName"]) if "LevelName" in data else None,
        "mode": MODES.get(int(mode)) if mode is not None else None,
        "difficulty": str(hard) if hard in DIFFICULTIES.values() else None,
        "spawn": (f"{' '.join(str(int(v)) for v in spawn['pos'])}, yaw {float(spawn.get('yaw', 0)):.2f}, "
                  f"pitch {float(spawn.get('pitch', 0)):.2f}") if "pos" in spawn else None,
        "version": str(data.get("Version", {}).get("Name", "")) or None,
        "commands": bool(int(data["allowCommands"])) if "allowCommands" in data else None,
        "packs": [str(p) for p in data.get("DataPacks", {}).get("Enabled", [])],
    }


def give_pack(world):
    """The save's own resource pack as the client's. Returns what to say of it, and whether there is one."""
    inside = os.path.join(world, "resourcepacks", "resources.zip")
    older = os.path.join(world, "resources.zip")
    source = inside if os.path.exists(inside) else older if os.path.exists(older) else None
    shutil.rmtree(PACK, ignore_errors=True)
    if not source:
        return "the save holds no resource pack: the game draws with its own textures", False
    with zipfile.ZipFile(source) as archive:
        names = members(archive, "the save's resource pack")
        if "pack.mcmeta" not in names:
            raise SystemExit(f"{os.path.relpath(source, world)} has no pack.mcmeta at its top")
        os.makedirs(os.path.dirname(PACK), exist_ok=True)
        archive.extractall(PACK)
        with archive.open("pack.mcmeta") as fh:
            meta = " ".join(fh.read().decode("utf-8", "replace").split())[:160]
    files = sum(1 for name in names if not name.endswith("/"))
    return (f"{os.path.relpath(source, world)} of the save ({os.path.getsize(source)} bytes, sha256 "
            f"{digest(source, whole=True)[:16]}, {files} files, pack.mcmeta {meta}) is the client's pack"), True


def ask(trip, *commands):
    """Answers of the server to commands typed on its console, each told to the log."""
    from rcon import Rcon
    with open(os.path.join(SERVER, ".rcon_pw")) as fh:
        rc = Rcon(port=25598, password=fh.read().strip(), timeout=60.0)
    answers = []
    try:
        for command in commands:
            answers.append(" ".join(rc.command(command).split())[:300])
            trip.say(f"server, asked `{command}`: {answers[-1]}")
    finally:
        rc.close()
    return answers


def number(text):
    """The last whole number in an answer of the server, or None; None too when the server did not
    take the command (its answer then points at the place: <--[HERE])."""
    found = re.findall(r"-?\d+", text or "")
    return int(found[-1]) if found and "<--[HERE]" not in text else None


def console_size():
    """How long the server's output is now: what it says from here on is this trip's."""
    try:
        return os.path.getsize(os.path.join(SERVER, "console.log"))
    except OSError:
        return 0


def server_said(offset, out, secret=""):
    """The server's warnings and errors from `offset` of its output on (the file is added to by
    every start), whole records, written to `out`. Returns (warnings, errors)."""
    records, record = [], None
    try:
        with open(os.path.join(SERVER, "console.log"), "rb") as fh:
            fh.seek(offset)
            text = fh.read().decode("utf-8", "replace")
    except OSError:
        text = ""
    for line in text.split("\n"):
        if secret:
            line = line.replace(secret, "***")
        m = re.match(r"\[\d\d:\d\d:\d\d\] \[[^\]]*/(WARN|ERROR|FATAL)\]", line)
        if re.match(r"\[\d\d:\d\d:\d\d\]", line):
            record = [m.group(1), line[:600]] if m and not OWN_WORDS.search(line) else None
            if record:
                records.append(record)
        elif record is not None and len(record) < 42 and line.strip():
            record.append(line[:600])
    warnings = sum(1 for record in records if record[0] == "WARN")
    errors = len(records) - warnings
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(f"# the server's warnings and errors while it ran on the save: {warnings} warnings, {errors} errors "
                 f"(its four lines on running offline, which it says on any world, are left out)\n")
        fh.write("".join(line + "\n" for record in records[:400] for line in record[1:]))
    return warnings, errors


def backend():
    """What the game says it draws with -- "OpenGL, 4.5 (Core Profile) Mesa ..." or "Vulkan, ... llvmpipe ..." --
    from its output; None when it has not said. The game tries OpenGL first and goes on with Vulkan
    when that fails; on a node it is OpenGL only with MC_GL=egl (nodemc.py)."""
    found = None
    try:
        with open(os.path.join(ROOT, "client26", "client.log"), encoding="utf-8", errors="replace") as fh:
            for line in fh:
                m = re.search(r"Using graphics backend (\w+), using drivers: (.+)", line)
                if m:
                    found = f"{m.group(1)}, {' '.join(m.group(2).split())[:90]}"
    except OSError:
        pass
    return found


def sound_said(said_path):
    """The game's complaints about sounds among the lines kept of its output: a sound event the
    packs do not hold ("Unable to play unknown soundEvent"), one with no sound in it ("Unable to
    play empty soundEvent"), a sounds.json it could not read, a file an event names and no pack has."""
    try:
        with open(said_path, encoding="utf-8", errors="replace") as fh:
            return [line.rstrip("\n") for line in fh
                    if re.search(r"soundEvent|sounds\.json|cannot add it to event|Unable to play", line)]
    except OSError:
        return []


def pack_loaded(said_path):
    """The game's line that names the packs it loaded last, and whether the save's is among them."""
    last = None
    try:
        with open(said_path, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                if "Reloading ResourceManager" in line:
                    last = " ".join(line.split())[:240]
    except OSError:
        pass
    return last, bool(last and "file/c164art" in last)


def main():
    ap = argparse.ArgumentParser(description="one trip into a save on a worker node")
    ap.add_argument("--branch", required=True)
    ap.add_argument("--at", metavar="COMMIT")
    ap.add_argument("--zip", required=True, metavar="PATH")
    ap.add_argument("--sha256")
    ap.add_argument("--name")
    ap.add_argument("--board", metavar="COMMIT")
    ap.add_argument("--only")
    ap.add_argument("--also", action="append", default=[], metavar="FILE")
    ap.add_argument("--again", metavar="NAMES",
                    help="views taken three times more from where the camera stands, half a second apart "
                         "(<name>_2 .. _4): what comes and goes in a view, a particle every two seconds, is in one of them")
    ap.add_argument("--view", type=int, default=nodetrip.BOARD_VIEW)
    ap.add_argument("--server-view", type=int, default=nodetrip.REALM_VIEW)
    ap.add_argument("--clouds", type=int, default=128)
    ap.add_argument("--settle", type=float, default=10.0)
    ap.add_argument("--first-settle", type=float, default=60.0)
    ap.add_argument("--still", type=float, default=60.0)
    ap.add_argument("--budget", type=float, default=600.0)
    args = ap.parse_args()
    import boardrender
    import realshots
    name = args.name or os.path.splitext(os.path.basename(args.zip))[0]
    if not realshots.NAME_OK.match(name):
        sys.exit(f"--name {name}: a name of letters, digits, - and _")
    with open(STATIONS, encoding="utf-8") as fh:
        shots = [{"name": JOINED, "stay": True}] + json.load(fh)
    for extra in args.also:
        with open(os.path.join(os.path.dirname(STATIONS), os.path.basename(extra)), encoding="utf-8") as fh:
            shots += json.load(fh)
        if len({s["name"] for s in shots}) != len(shots):
            sys.exit(f"--also {extra}: a stop of it has the name of a view taken already")
    if args.only:
        wanted = args.only.split(",")
        missing = [n for n in wanted if n not in {s["name"] for s in shots}]
        if missing:
            sys.exit(f"--only: no view called {', '.join(missing)}")
        shots = [s for s in shots if s["name"] in wanted]
    if args.again:
        again = args.again.split(",")
        missing = [n for n in again if n not in {s["name"] for s in shots}]
        if missing:
            sys.exit(f"--again: no view called {', '.join(missing)} among those taken")
        shots = [more for s in shots for more in
                 [s] + ([{"name": f"{s['name']}_{k}", "stay": True, "settle": 0.5, "still": 0} for k in (2, 3, 4)]
                        if s["name"] in again else [])]

    commit = clean_commit(args.branch, args.at)
    work = os.path.join(WORK, "save", name)
    shutil.rmtree(work, ignore_errors=True)
    os.makedirs(work)
    zip_path = os.path.join(work, os.path.basename(args.zip))
    with open(zip_path, "wb") as fh:
        got = subprocess.run(["git", "-C", PROJECT, "show", f"{commit}:c164-realms/{args.zip}"], stdout=fh,
                             stderr=subprocess.PIPE)
    if got.returncode != 0:
        sys.exit(f"{commit[:8]} of {args.branch} has no c164-realms/{args.zip}: "
                 + got.stderr.decode("utf-8", "replace").strip()[-200:])
    sha = digest(zip_path, whole=True)
    if args.sha256 and sha != args.sha256.lower():
        sys.exit(f"{args.zip} of {commit[:8]} is not the file asked for: its sha256 is {sha}, not {args.sha256}")

    stamp = time.strftime("%Y%m%d-%H%M%S", time.gmtime())
    log_path = os.path.join(PROJECT, "renders", "real", "_trips", f"{stamp}-{commit[:7]}-save-{name}.log")
    trip = Trip(log_path, args.budget)
    started = time.time()

    def cut_short(*_):
        if trip.running is not None:
            end(trip.running, patience=4.0)
        sys.exit(143)
    signal.signal(signal.SIGTERM, cut_short)
    station = os.path.join(HERE, "nodemc.py")
    distances = {"MC_VIEW": str(args.view), "MC_SERVER_VIEW": str(args.server_view), "MC_CLOUDS": str(args.clouds)}
    at = f"view distance {args.view} (the server's {args.server_view}), cloud range {args.clouds}"
    view = f"view{args.view},server{args.server_view},clouds{args.clouds}"
    trip.say(f"trip into the save {args.zip} of {commit[:8]} ({args.branch}): {os.path.getsize(zip_path)} bytes, "
             f"sha256 {sha}" + (", as asked" if args.sha256 else "") + f"; {at}; {os.cpu_count()} cores, "
             f"{args.budget:.0f} s at most")
    failed, facts, kept_in, console = [], [], os.path.join(KEPT, name), console_size()
    facts.append(f"# the save: {args.zip} of {commit[:8]} ({args.branch}), {os.path.getsize(zip_path)} bytes, sha256 {sha}")
    if args.board:
        facts.append(f"# exported from the assembly commit {args.board}, as the one who asked for the trip says")
    try:
        trip.stage("clean", station, "down", budget=180)
        console = console_size()
        world = os.path.join(SERVER, LEVEL)
        os.makedirs(SERVER, exist_ok=True)
        top, count = unpack(zip_path, world)
        level = level_facts(world)
        trip.say(f"the save: the world folder {top} ({count} entries) is unpacked as server26/{LEVEL}/; level.dat: "
                 + ", ".join(f"{key} {value}" for key, value in level.items()))
        facts.append(f"# level.dat: world {level['name']}, game {level['version']}, game mode {level['mode']}, difficulty "
                     f"{level['difficulty']}, spawn {level['spawn']}, commands {'on' if level['commands'] else 'off'}, "
                     f"data packs {' '.join(level['packs'])}")
        # the light the save brings with it: a source that was placed after the light was worked out
        # is stored dark, and a chunk that says isLightOn is not lit again (tools/savelit.py)
        try:
            lit = savelit.line(savelit.survey(zip_path))
        except Exception as exc:        # a chunk layout this game writes and the script does not read
            lit = f"the save's stored light: not read ({type(exc).__name__}: {exc})"
        trip.say(lit)
        facts.append("# " + lit)
        mode, hard = level["mode"] or "adventure", level["difficulty"] or "peaceful"
        if not level["mode"] or not level["difficulty"]:
            trip.say(f"level.dat does not say the game mode or the difficulty in a way known here: opened as {mode}, {hard}")
        as_slot = {**distances, "MC_LEVEL": LEVEL, "MC_GAMEMODE": mode, "MC_FORCE_GAMEMODE": "false", "MC_DIFFICULTY": hard}
        facts.append(f"# the server: the node's test server on this save, game mode {mode} (not forced), difficulty {hard}, "
                     f"as a Realm's slot is filled from the world; the camera is no operator")
        code, _ = trip.stage("setup", station, "setup", budget=min(1500, trip.left() - 300), env=as_slot)
        if code != 0:
            failed.append("the node could not be made ready")
        else:
            said, has_pack = give_pack(world)
            trip.say("resource pack: " + said)
            facts.append("# resource pack: " + said + " (whether a Realm hands it to those who join is not shown here)")
            code, _ = trip.stage("server", station, "server-up", budget=min(400, trip.left() - CLOSING), env=as_slot)
            if code != 0:
                failed.append("the server did not come up on the save")
            else:
                before = ask(trip, HOUR, "time query gametime", "gamerule advance_time", "difficulty",
                             "datapack list enabled")
                facts.append(f"# the server, before anybody joined: {before[0]}; {before[2]}; {before[3]}; {before[4]}")
                code, _ = trip.stage("game", station, "client-up", budget=trip.left() - CLOSING, env=as_slot)
                if code != 0:
                    failed.append("the game did not come up or did not join")
                else:
                    cam = nodetrip_cam()
                    drawn_by = backend()
                    trip.say(f"the game draws with: {drawn_by or 'it has not said'}")
                    facts.append(f"# the game's graphics backend: {drawn_by or 'not said'}")
                    joined = ask(trip, f"data get entity {cam} Pos", f"data get entity {cam} Rotation",
                                 f"data get entity {cam} playerGameType", HOUR)
                    facts.append(f"# as joined: {joined[0]}; {joined[1]}; {joined[2]} "
                                 f"(0 survival, 1 creative, 2 adventure, 3 spectator)")
                    out = os.path.join(work, "shots")
                    shots_file = os.path.join(work, "shots.json")
                    with open(shots_file, "w", encoding="utf-8") as fh:
                        json.dump(shots, fh)
                    code, text = trip.stage("pictures", os.path.join(HERE, "shoot.py"), shots_file,
                                            "--pw-file", os.path.join(SERVER, ".rcon_pw"), "--out", out,
                                            "--origin", *ORIGIN, "--keep-clock", "--settle", args.settle,
                                            "--first-settle", args.first_settle, "--still", args.still,
                                            budget=trip.left() - CLOSING, env=as_slot)
                    after = ask(trip, HOUR, f"data get entity {cam} playerGameType")
                    tick_before, tick_after = number(joined[3]), number(after[0])
                    facts.append(f"# the save's clock: the day stood at {tick_before} when the player had joined, at "
                                 f"{tick_after} after the last picture ("
                                 + ("the server did not say" if tick_before is None or tick_after is None
                                    else "it stands" if tick_before == tick_after else "it runs") + ")")
                    made = [line for line in text.splitlines() if line.strip().startswith("pictures:")]
                    facts.append(f"# distances: client render distance {args.view}, server view distance {args.server_view}, "
                                 f"cloud range {args.clouds}; {made[-1].strip() if made else 'pictures: ?'}")
                    taken = [s["name"] for s in shots if os.path.exists(os.path.join(out, s["name"] + ".png"))]
                    if code != 0 or len(taken) != len(shots):
                        failed.append(f"{len(taken)} of {len(shots)} pictures")
                    if taken:
                        keep(trip, name, taken, out, kept_in, commit, tick_before, tick_after, view, facts,
                             at + (f", backend {drawn_by.split(',')[0]}" if drawn_by else ""), sha, whole=not args.only)
    except SystemExit as stop:
        if stop.code not in (0, None):
            trip.say(f"stopped: {stop}")
            failed.append(str(stop)[:200])
    finally:
        said_path = log_path[:-len(".log")] + "-client.txt"
        try:
            trip.stage("what the game said", station, "client-said", f"{started:.0f}", said_path, budget=30)
            heard = sound_said(said_path)
            trip.say(f"the game on sounds: {len(heard)} lines of an unknown or empty sound event or a bad sounds.json"
                     + "".join(f"\n    {line[:300]}" for line in heard[:12]))
            line, loaded = pack_loaded(said_path)
            trip.say(f"the packs the game loaded: {line or 'no line of the game says'}")
            if os.path.isdir(PACK) and not loaded:
                failed.append("the game did not load the save's resource pack")
        except Exception as exc:
            trip.say(f"what the game said could not be read ({exc})")
        try:
            warnings, errors = server_said(console, log_path[:-len(".log")] + "-server.txt", trip.secret())
            trip.say(f"the server on the save: {warnings} warnings, {errors} errors in its log "
                     f"({os.path.basename(log_path)[:-len('.log')]}-server.txt)")
            if errors:
                failed.append(f"the server logged {errors} errors on the save")
        except Exception as exc:
            trip.say(f"what the server said could not be read ({exc})")
        trip.stage("close", station, "down", budget=180)
        # the node is the test world's again: the next job finds it as every job expects it
        trip.stage("back to the test world", station, "setup", budget=120, env=distances)
        trip.say(("trip done" if not failed else "trip done with failures: " + "; ".join(failed))
                 + f"; pictures kept: {kept_in + '/' if os.path.isdir(os.path.join(PROJECT, kept_in)) else 'none'}; "
                 f"log {os.path.relpath(log_path, PROJECT)}")
        trip.log.close()
    return 1 if failed else 0


def nodetrip_cam():
    return os.environ.get("MC_CAM", "C164Cam")


def keep(trip, name, taken, out, kept_in, commit, tick_before, tick_after, view, facts, at, sha, whole):
    """The pictures as JPEGs in renders/real-save/<name>/ with their note and sheets."""
    from PIL import Image
    import boardrender
    import realshots
    folder = os.path.join(PROJECT, kept_in)
    if whole:
        shutil.rmtree(folder, ignore_errors=True)       # a trip of all the views leaves nothing of an earlier one
    os.makedirs(folder, exist_ok=True)
    note = os.path.join(folder, realshots.NOTE)
    kept = {} if whole else realshots.read_kept(note)
    when = time.strftime("%Y-%m-%dT%H:%M", time.gmtime())
    tick = "?" if tick_before is None else tick_before if tick_before == tick_after else f"{tick_before}-{tick_after}"
    for shot in taken:
        path = os.path.join(folder, shot + ".jpg")
        with Image.open(os.path.join(out, shot + ".png")) as picture:
            picture.convert("RGB").save(path, "JPEG", quality=JPEG_QUALITY)
        kept[shot] = (str(tick), commit[:8], digest(path), when, view)
    with open(note, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(HEAD + "\n" + "".join(line + "\n" for line in facts)
                 + "".join(f"{shot} {' '.join(row)}\n" for shot, row in kept.items()))
    names = [shot for shot in kept if os.path.exists(os.path.join(folder, shot + ".jpg"))]
    hour = f"the save's own hour {tick}" if tick_before is not None else "the save's own hour"
    title = f"c164 the save {name} (sha256 {sha[:12]}) opened as it comes: the game 26.3 on a node, {at}, {hour}"
    boardrender.sheet(folder, names, title, ext=".jpg")
    made = ["sheet.jpg"]
    board = os.path.join(PROJECT, "renders", "real", "obs")
    rows = realshots.read_kept(os.path.join(board, realshots.NOTE))
    views = [shot for shot in names if shot in rows and os.path.exists(os.path.join(board, shot + ".jpg"))]
    if views:
        of = ", ".join(sorted({rows[shot][1] for shot in views}))
        boardrender.in_columns([(f"test world, the board of {of}", board), (f"the save {name}", folder)], views,
                               f"c164 the board's views: the scene placed in the test world ({of}) | the save {name} as it "
                               f"comes, {hour}", os.path.join(folder, "beside.jpg"))
        made.append(f"beside.jpg (beside the board of {of})")
    trip.say(f"{len(taken)} pictures kept in {kept_in}/: {', '.join(taken)}; {', '.join(made)}")


if __name__ == "__main__":
    sys.exit(main())
