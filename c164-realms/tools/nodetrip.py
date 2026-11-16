#!/usr/bin/env python3
"""One real-machine trip on a worker node, as the one command of a node job.

    bash c164-realms/tools/nodejob.sh --always --tail 40 python tools/nodetrip.py --at <commit> [<scene> ...]

A node job lasts an hour at most and the node keeps nothing running between jobs, so the whole
trip is in it: the server is started, the scenes are placed, the game is opened once, the pictures
are taken, and everything is closed again. Without a scene the master scene, obs, is shot with
its twelve board views. The trip

  1. stops what an earlier job may have left running (nodemc.py down);
  2. makes the node ready (nodemc.py setup: the system's packages, Java 25, the game's files from
     Mojang, the settings) with the distances asked for -- the client's render distance 12, the
     server's view distance 10 and a cloud range of 128 unless --view, --server-view and --clouds
     say otherwise;
  3. runs the shuttle (win/shuttle.py): the look, the server, the scenes on their plots, the
     resource pack, the game, the shots;
  4. takes the pictures into renders/real/<scene>/ (realshots.py --take; pictures at other
     distances than the board's go to renders/real-view<n>/<scene>/ or
     renders/real-server<n>/<scene>/, they are not the board's) and draws
     sheet.jpg beside them; for the master scene also compare.jpg, each board view as the offline
     renderer drew it (renders/board/<tag>/) beside the game's -- when the offline board of that
     commit is not drawn yet, boardrender.py draws the sheet as it comes, and a compare.jpg of an
     earlier board is removed meanwhile;
  5. stops the game, the server and the display, whatever happened before;
  6. leaves the trip's log in renders/real/_trips/<time>-<tag>-<first scene>.log. The receipt of a node job is
     a retelling; what the trip really said comes home in this file, with the pictures.

The pictures are named after the assembly commit whose build/ this checkout carries, as the
offline board is (boardrender.py): its head, or the commit given with --at; a checkout whose
build/ is not the assembly's is shot with --tag <name>.

Somebody else's code -- a request names a scene, its shots and a commit of a work branch -- is shot
with --branch <name> [--at <commit>]: the branch is fetched, the commit (the branch's head without
--at) is tested for its provenance (tools/provenance.sh: nothing of the second shift is shot) and
checked out beside this checkout, and the shuttle shoots that code with the station's own tools.
Its test scenes are kept like any others, in renders/real/<scene>/; its master scene, which is not
the assembly's, in renders/real-branch/<commit>/obs/.

The light versions -- --looks blue,deep,glow -- are a trip of their own: windows are blocks, so
for every version named the scenes are placed anew, built for it (placelook.py: its table says
which windows are lit), and shot at its tick; the game stays open in between. A version named
with +dress (blue+dress) is built with the building's own lights on, which the code keeps off.
These pictures are not the board's: they are kept in renders/real-looks/<tag>/<look>/<scene>/,
with <scene>-looks.jpg beside the folders, one row a view and one column a version
(<scene>-looks-dressed.jpg for the versions with +dress).

Scenes that cannot share a trip of the shuttle -- versions of one thing that want different
files under one name in the resource pack -- are shot with --apart: one run of the shuttle a
scene, the game opened anew where the pack changed. --beside <name> then draws the shots the
scenes have in common side by side, one column a scene: renders/real/_beside/<name>.jpg.

    --at <commit>            the assembly commit the pictures are named after (default: its head);
                             with --branch, the commit of that branch to shoot (default: its head)
    --tag <name>             this checkout as it is, under this name
    --branch <name>          shoot the code of this branch instead of this checkout's
    --looks <a>,<b>[+dress]  the light versions the scenes are shot under, one after the other
    --apart                  every scene in a run of the shuttle of its own
    --beside <name>          the scenes' pictures of this trip side by side on one sheet
    --sheet <name>           this trip's pictures on one sheet, renders/real/_sheets/<name>.jpg, in
                             the order --only names them, --across <n> a row (2): a few shots picked
                             for a comparison
    --view <n> --clouds <n>  the client's render distance and cloud range in chunks (12 and 128)
    --server-view <n>        the server's view distance in chunks (10: what a Realm runs at and
                             cannot change. The client draws the smaller of the two, so no block
                             is seen further than 160 off; entities are sent no further either)
    --settle, --first-settle, --still   seconds, passed to the shuttle (10, 60, 60)
    --only, --shots, --gallery, --plot, --again, --step   passed to the shuttle as they are
    --after <scene>=<script> a script of the code that is shot (a path from its build/), run after
                             the scene's shots while the scene stands, the server runs and the game
                             is open: commands typed on the server, scoreboards read. What it prints
                             is kept as after.txt beside the scene's pictures; --after-budget
                             seconds at most (300)
    --no-place               the scenes stand from an earlier trip of the same code
    --budget <seconds>       the trip stops what it is doing after this long, takes what there is
                             and closes down (1500: nodejob.sh stops a command at 1700 s, and
                             the game must be closed by the trip itself before that, not left
                             running on the node). A longer trip says so in both places:
                             nodejob.sh --limit 3400 ... nodetrip.py --budget 3200, timeout_sec=3600

Exit code 0: every scene's pictures were all taken and are kept.
"""
import argparse
import os
import shutil
import signal
import subprocess
import sys
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(HERE)
ROOT = os.path.abspath(os.environ.get("MC_ROOT", "/agent/realms-study"))
WORK = os.environ.get("C164_TRIP_DIR", "/tmp/c164_s1/real")
MASTER = "obs"
BOARD_VIEW = 12         # the client's render distance the board is judged at
REALM_VIEW = 10         # the server's view distance on a Realm (Realms Map Guidelines: "View distance is
                        # set to 10. This cannot be altered."); the board is judged at it since 11-16 07:20
CLOSING = 120           # seconds of a trip's time that are kept for taking the pictures and closing down

sys.path.insert(0, HERE)


def end(proc, patience=30.0):
    """Stop a stage and what it started in its own process group: asked first, then killed after
    `patience` seconds. The shuttle, asked, still makes ready what it has shot and closes the
    game; that is what the patience is for. The server, the game and the display are not of that
    group; nodemc.py down stops them."""
    for sig, wait in ((signal.SIGTERM, patience), (signal.SIGKILL, 10.0)):
        try:
            os.killpg(proc.pid, sig)
        except OSError:
            return
        for _ in range(int(wait * 2)):
            if proc.poll() is not None:
                return
            time.sleep(0.5)


class Trip:
    def __init__(self, log_path, budget):
        self.t0 = time.monotonic()
        self.deadline = self.t0 + budget
        self.log_path = log_path
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        self.log = open(log_path, "w", encoding="utf-8", newline="\n")
        self.running = None             # the stage that runs now
        self.password = ("", 0.0)       # the server's remote-console password and when it was read

    def left(self):
        return self.deadline - time.monotonic()

    def secret(self):
        """The one secret of the station: it must not get into the log, whatever a tool prints."""
        word, read = self.password
        if time.monotonic() - read > 5:
            try:
                with open(os.path.join(ROOT, "server26", ".rcon_pw")) as fh:
                    word = fh.read().strip()
            except OSError:
                word = ""
            self.password = (word, time.monotonic())
        return word

    def write(self, line):
        secret = self.secret()
        if secret:
            line = line.replace(secret, "***")
        print(line, flush=True)
        self.log.write(line + "\n")
        self.log.flush()

    def say(self, text):
        self.write(f"[trip {time.strftime('%H:%M:%S')} +{time.monotonic() - self.t0:.0f}s] {text}")

    def stage(self, name, script, *args, budget, env=None):
        """Run one of the tools beside this file, its output into the log line by line; it is
        stopped when `budget` seconds are over. Returns (exit code, output)."""
        budget = max(5.0, budget)
        self.say(f"{name}: {os.path.basename(script)} {' '.join(str(a) for a in args)}  (up to {budget:.0f} s)")
        t0 = time.monotonic()
        proc = subprocess.Popen([sys.executable, "-u", script, *[str(a) for a in args]], cwd=PROJECT, text=True,
                                encoding="utf-8", errors="replace", stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                stdin=subprocess.DEVNULL, start_new_session=True,
                                env={**os.environ, "MC_ROOT": ROOT, "PYTHONIOENCODING": "utf-8",
                                     "PYTHONUNBUFFERED": "1", **(env or {})})
        over = threading.Event()

        def stop():
            over.set()
            end(proc)

        timer = threading.Timer(budget, stop)
        timer.daemon = True
        timer.start()
        self.running = proc
        lines = []
        try:
            for line in proc.stdout:
                lines.append(line.rstrip("\n"))
                self.write("    " + lines[-1])
            code = proc.wait()
        finally:
            timer.cancel()
            self.running = None
        if over.is_set():
            self.say(f"{name}: stopped after {budget:.0f} s, its time was over")
            code = code or 124
        self.say(f"{name}: exit {code}, {time.monotonic() - t0:.0f} s")
        return code, "\n".join(lines)


def git(*args, cwd=PROJECT):
    got = subprocess.run(("git", "-C", cwd) + args, capture_output=True, text=True)
    return got.stdout.strip() if got.returncode == 0 else None


def other_code(branch, at):
    """The code of a commit of another branch, checked out beside this checkout: (its c164-realms
    folder, the commit's eight digits). Stops when the commit is not that branch's or not clean."""
    if git("fetch", "-q", "origin", branch) is None:
        sys.exit(f"--branch {branch}: cannot be fetched from origin")
    head = git("rev-parse", "FETCH_HEAD")
    if git("rev-parse", "--is-shallow-repository") == "true":
        # the test of provenance reads the whole history: a clone cut short would pass anything
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
    where = os.path.join(os.path.dirname(WORK), "shot", commit[:8])
    if git("rev-parse", "HEAD", cwd=where) != commit:
        git("worktree", "remove", "--force", where)
        git("worktree", "prune")
        if git("worktree", "add", "--detach", where, commit) is None:
            sys.exit(f"{commit[:8]} of {branch} could not be checked out at {where}")
    project = os.path.join(where, "c164-realms")
    if not os.path.isdir(os.path.join(project, "build", "scenes")):
        sys.exit(f"{commit[:8]} of {branch} has no c164-realms/build/scenes")
    return project, commit[:8]


def sheets(trip, scene, folder, tag, at):
    """sheet.jpg of a scene's kept pictures; for the master scene compare.jpg beside the offline board."""
    import boardrender
    import realshots
    kept = realshots.read_kept(os.path.join(folder, realshots.NOTE))
    names = [shot for shot in kept if os.path.exists(os.path.join(folder, shot + ".jpg"))]
    if not names:
        return
    commits = ", ".join(sorted({row[1] for row in kept.values()}))
    drawn = f"the game 26.3 on a node, {at}"
    boardrender.sheet(folder, names, f"c164 {scene}, {drawn}, the code of {commits}", ext=".jpg")
    made = ["sheet.jpg"]
    if scene == MASTER:
        # beside the offline board of the same commit, if that is drawn already (else boardrender.py
        # draws the sheet when it comes); never a sheet of an earlier board beside these pictures
        made.append(boardrender.beside_game(tag, folder, drawn, stale_goes=True))
    trip.say(f"{scene}: {', '.join(m for m in made if m)} in {os.path.relpath(folder, PROJECT)}/")


def look_sheets(trip, scene, base, runs, commit, at):
    """<scene>-looks.jpg: the scene's views under every light version of the trip, one column a
    version; the versions shot with the building's own lights on have a sheet of their own."""
    import boardrender
    import realshots
    for dressed in (False, True):
        columns, names = [], []
        for look, dress in runs:
            if dress != dressed:
                continue
            folder = os.path.join(base, look + ("-dressed" if dress else ""), scene)
            kept = realshots.read_kept(os.path.join(folder, realshots.NOTE))
            if not kept:
                continue
            ticks = sorted({row[0] for row in kept.values()})
            columns.append((f"{look} {'/'.join(ticks)}", folder))
            names += [shot for shot in kept if shot not in names]
        if not columns:
            continue
        out = os.path.join(base, f"{scene}-looks{'-dressed' if dressed else ''}.jpg")
        boardrender.in_columns(columns, names, f"c164 {scene} of {commit}, the game 26.3 on a node, {at}: "
                               f"each light version at its tick, the windows lit by its table"
                               + (", the building's own lights on (DRESS, off in the code)" if dressed else ""), out,
                               size=(960, 540) if len(columns) <= 3 else (640, 360))
        trip.say(f"{scene}: {os.path.relpath(out, PROJECT)}, {len(names)} views under {len(columns)} light versions")


def beside(trip, name, shot, tag, at):
    """renders/real/_beside/<name>.jpg: what the scenes of this trip were shot of, one column a
    scene, one row a shot. `shot` is [(scene, its folder, [shots taken])]."""
    import boardrender
    names = []
    for _, _, taken in shot:
        names += [n for n in taken if n not in names]
    out = os.path.join(PROJECT, "renders", "real", "_beside", name + ".jpg")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    boardrender.in_columns([(scene, folder) for scene, folder, _ in shot], names,
                           f"c164 {', '.join(scene for scene, _, _ in shot)} of {tag}: the game 26.3 on a node, {at}", out)
    trip.say(f"{os.path.relpath(out, PROJECT)}: {len(names)} shots of {len(shot)} scenes side by side")


def main():
    ap = argparse.ArgumentParser(description="one real-machine trip on a worker node")
    ap.add_argument("scenes", nargs="*", default=[MASTER])
    ap.add_argument("--at", metavar="COMMIT")
    ap.add_argument("--tag")
    ap.add_argument("--branch")
    ap.add_argument("--view", type=int, default=BOARD_VIEW)
    ap.add_argument("--server-view", type=int, default=REALM_VIEW)
    ap.add_argument("--clouds", type=int, default=128)
    ap.add_argument("--settle", type=float, default=10.0)
    ap.add_argument("--first-settle", type=float, default=60.0)
    ap.add_argument("--still", type=float, default=60.0)
    ap.add_argument("--only", action="append", default=[], metavar="SCENE=A,B")
    ap.add_argument("--shots", action="append", default=[], metavar="SCENE=FILE")
    ap.add_argument("--gallery", action="append", default=[], metavar="SCENE")
    ap.add_argument("--plot", action="append", default=[], metavar="SCENE=N")
    ap.add_argument("--again", action="append", default=[], metavar="SCENE=SHOT[:SECONDS]")
    ap.add_argument("--step", action="append", default=[], metavar="SCENE=SHOT[:BLOCKS]")
    ap.add_argument("--after", action="append", default=[], metavar="SCENE=SCRIPT")
    ap.add_argument("--after-budget", type=float, default=300.0)
    ap.add_argument("--looks", metavar="LOOK[+dress],...")
    ap.add_argument("--apart", action="store_true")
    ap.add_argument("--beside", metavar="NAME")
    ap.add_argument("--sheet", metavar="NAME")
    ap.add_argument("--across", type=int, default=2)
    ap.add_argument("--no-place", action="store_true")
    ap.add_argument("--budget", type=float, default=1500.0)
    args = ap.parse_args()
    import boardrender
    import realshots
    if args.tag and (args.at or args.branch):
        sys.exit("--tag names this checkout as it is; --at and --branch name a commit: one or the other")
    per_scene = (("--only", args.only), ("--shots", args.shots), ("--gallery", args.gallery),
                 ("--plot", args.plot), ("--again", args.again), ("--step", args.step), ("--after", args.after))
    for name, values in per_scene:
        for value in values:
            if value.split("=", 1)[0] not in args.scenes:
                sys.exit(f"{name} {value}: {value.split('=', 1)[0]} is not one of this trip's scenes")
    # the runs of the shuttle: (light version or None for the code as it builds, its own lights on, the scenes)
    runs = [(None, False, [scene]) for scene in args.scenes] if args.apart else [(None, False, args.scenes)]
    if args.looks:
        names = [name for name in args.looks.split(",") if name]
        runs = [(name.partition("+")[0], name.endswith("+dress"), args.scenes) for name in names]
        wrong = [name for name in names if name.partition("+")[2] not in ("", "dress")]
        if wrong or not runs or len(set(names)) != len(names):
            sys.exit(f"--looks {args.looks}: light versions by name, each once, +dress for the building's own lights")
        if args.no_place or args.apart or args.beside or args.sheet:
            sys.exit("--looks places the scenes anew for every light version and draws its own sheet: "
                     "--no-place, --apart, --beside and --sheet cannot go with it")
    for option, name in (("--beside", args.beside), ("--sheet", args.sheet)):
        if name and not realshots.NAME_OK.match(name):
            sys.exit(f"{option} {name}: a name of letters, digits, - and _")
    if args.sheet and (args.across < 1 or (args.branch and MASTER in args.scenes)):
        sys.exit("--sheet draws test scenes and the assembly's master scene, --across <n> pictures a row (1 or more)")

    project = None
    if args.branch:
        project, commit = other_code(args.branch, args.at)
        tag = commit[:7]
    else:
        tag, commit = boardrender.which_commit(args.tag, args.at)
    # pictures at other distances than the board's are kept apart: they never stand in for the board's
    apart = (f"-view{args.view}" if args.view != BOARD_VIEW else "") \
        + (f"-server{args.server_view}" if args.server_view != REALM_VIEW else "")
    kept_in = os.path.join("renders", "real" + apart)
    at = f"view distance {args.view} (the server's {args.server_view}), cloud range {args.clouds}"
    # a branch's master scene is not the assembly's: it does not take the place of the board's pictures
    own_in = os.path.join("renders", "real-branch" + apart, tag) if project else kept_in
    looks_in = os.path.join(own_in, "looks") if project else os.path.join("renders", kept_in.split(os.sep)[-1] + "-looks", tag)
    # four nodes shoot at once and push to one branch: two trips of one commit that start in the
    # same minute must not write the same file
    log_path = os.path.join(PROJECT, "renders", "real", "_trips",
                            f"{time.strftime('%Y%m%d-%H%M%S', time.gmtime())}-{tag}-{args.scenes[0]}"
                            + (f"-server{args.server_view}" if args.server_view != REALM_VIEW else "")
                            + ("-looks" if args.looks else "") + ".log")
    trip = Trip(log_path, args.budget)
    started = time.time()

    def cut_short(*_):
        # The job is being ended from outside (nodejob.sh at its limit kills what it asked to stop
        # 15 s later): no time for the pictures, but the closing steps are started at once, and
        # `nodemc.py down`, once started, goes on by itself.
        if trip.running is not None:
            end(trip.running, patience=4.0)
        sys.exit(143)
    signal.signal(signal.SIGTERM, cut_short)
    station = os.path.join(HERE, "nodemc.py")
    distances = {"MC_VIEW": str(args.view), "MC_SERVER_VIEW": str(args.server_view), "MC_CLOUDS": str(args.clouds)}
    trip.say(f"trip of {', '.join(args.scenes)}: the code of {commit} (tag {tag})"
             + (f" of {args.branch}, checked out at {os.path.dirname(project)}" if project else "")
             + (f", under the light versions {args.looks}" if args.looks else "")
             + f", {at}; {os.cpu_count()} cores, {args.budget:.0f} s at most")
    failed, kept = [], []
    try:
        trip.stage("clean", station, "down", budget=180)
        code, _ = trip.stage("setup", station, "setup", budget=min(1500, trip.left() - 300), env=distances)
        if code != 0:
            failed.append("the node could not be made ready")
        else:
            trip.stage("station", station, "status", budget=60)
            common = ["--tag", tag, "--commit", commit, "--settle", args.settle,
                      "--first-settle", args.first_settle, "--still", args.still, "--after-budget", args.after_budget]
            scripted = {value.split("=", 1)[0] for value in args.after}
            if args.no_place:
                common.append("--no-place")
            if project:
                common += ["--project", project]
            shot = []           # (scene, the folder its pictures are kept in, the shots of this trip)
            for i, (look, dress, scenes) in enumerate(runs):
                version = f"{look}{'-dressed' if dress else ''}" if look else ""
                work = os.path.join(WORK, "looks", version) if look else WORK
                options = common + ["--out", work]
                for name, values in per_scene:
                    for value in values:
                        if value.split("=", 1)[0] in scenes:
                            options += [name, value]
                if look:
                    options += ["--look", look] + (["--dress"] if dress else [])
                if i < len(runs) - 1:
                    options.append("--keep-client")     # the game stays open for the next run, if the pack is the same
                name = f"shuttle, {version}" if look else f"shuttle, {scenes[0]}" if args.apart else "shuttle"
                # what is left after the shuttle is for the closing steps: the pictures are taken in a
                # second and `down` took 2 s on node34; its worst case (a server that has to be killed)
                # is about 115 s
                code, _ = trip.stage(name, os.path.join(HERE, "win", "shuttle.py"), *options, *scenes,
                                     budget=trip.left() - CLOSING, env=distances)
                if code != 0:
                    failed.append(f"the {name} ended with {code}")
                send = os.path.join(work, tag, "send")
                for scene in scenes:
                    if scene in args.gallery and not os.path.exists(os.path.join(send, f"{scene}-{tag}-real.txt")):
                        continue        # a scene of models alone that was not shot: the shuttle said why
                    into = os.path.join(looks_in, version) if look else own_in if scene == MASTER else kept_in
                    answer = os.path.join(send, f"{scene}-{tag}-after.txt")
                    if scene in scripted and os.path.exists(answer):
                        # what the scene's own script said (--after) is kept beside its pictures
                        os.makedirs(os.path.join(PROJECT, into, scene), exist_ok=True)
                        shutil.copyfile(answer, os.path.join(PROJECT, into, scene, "after.txt"))
                        trip.say(f"{scene}: what its script said is in {into}/{scene}/after.txt")
                    ok, said = realshots.take(send, tag, scene, os.path.join(PROJECT, into))
                    for line in said:
                        trip.say(line)
                    if not ok:
                        failed.append(f"{scene}: no pictures kept" + (f" of {version}" if look else ""))
                        continue
                    kept.append(f"{into}/{scene}/")
                    if look:
                        continue
                    _, _, rows = realshots.read_sent(os.path.join(send, f"{scene}-{tag}-real.txt"))
                    shot.append((scene, os.path.join(PROJECT, into, scene), [row[0] for row in rows]))
                    try:
                        sheets(trip, scene, os.path.join(PROJECT, into, scene), tag, at)
                    except Exception as exc:        # the pictures are kept; a sheet is a convenience
                        trip.say(f"{scene}: the sheet could not be drawn ({exc})")
            if args.looks:
                for scene in args.scenes:
                    try:
                        look_sheets(trip, scene, os.path.join(PROJECT, looks_in), [run[:2] for run in runs], commit, at)
                    except Exception as exc:
                        trip.say(f"{scene}: the sheet of the light versions could not be drawn ({exc})")
            if args.beside and shot:
                try:
                    beside(trip, args.beside, shot, tag, at)
                except Exception as exc:
                    trip.say(f"--beside {args.beside}: the sheet could not be drawn ({exc})")
            if args.sheet and shot:
                # this trip's pictures on one sheet, in the order --only names them (else the list's)
                asked = {value.split("=", 1)[0]: value.split("=", 1)[1].split(",") for value in args.only}
                picked = [f"{scene}:{name}" for scene, _, taken in shot
                          for name in asked.get(scene, taken) if name in taken]
                try:
                    realshots.sheet(args.sheet, picked, args.across,
                                    f"c164 {', '.join(scene for scene, _, _ in shot)} of {commit}: the game 26.3 on a "
                                    f"node, {at}",
                                    kept_in=os.path.join(PROJECT, kept_in))
                    trip.say(f"{kept_in}/_sheets/{args.sheet}.jpg: {len(picked)} pictures, {args.across} a row")
                except (Exception, SystemExit) as exc:
                    trip.say(f"--sheet {args.sheet}: the sheet could not be drawn ({exc})")
    finally:
        # the game's own words on shaders and packs, beside the log: a pack whose shaders do not
        # compile is thrown out by the game, and the pictures then show the vanilla ones
        said_path = log_path[:-len(".log")] + "-client.txt"
        try:
            trip.stage("what the game said", station, "client-said", f"{started:.0f}", said_path, budget=30)
        except Exception as exc:
            trip.say(f"what the game said could not be read ({exc})")
        trip.stage("close", station, "down", budget=180)
        where = ", ".join(kept) or "none"
        trip.say(("trip done" if not failed else "trip done with failures: " + "; ".join(failed))
                 + f"; pictures kept: {where}; log {os.path.relpath(log_path, PROJECT)}")
        trip.log.close()
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
