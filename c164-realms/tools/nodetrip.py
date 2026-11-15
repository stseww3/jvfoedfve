#!/usr/bin/env python3
"""One real-machine trip on a worker node, as the one command of a node job.

    bash c164-realms/tools/nodejob.sh --always --tail 40 python tools/nodetrip.py --at <commit> [<scene> ...]

A node job lasts an hour at most and the node keeps nothing running between jobs, so the whole
trip is in it: the server is started, the scenes are placed, the game is opened once, the pictures
are taken, and everything is closed again. Without a scene the master scene, obs, is shot with
its twelve board views. The trip

  1. stops what an earlier job may have left running (nodemc.py down);
  2. makes the node ready (nodemc.py setup: the system's packages, Java 25, the game's files from
     Mojang, the settings) with the distances asked for -- 12 chunks of view and a cloud range of
     128 unless --view and --clouds say otherwise;
  3. runs the shuttle (win/shuttle.py): the look, the server, the scenes on their plots, the
     resource pack, the game, the shots;
  4. takes the pictures into renders/real/<scene>/ (realshots.py --take; pictures at another view
     distance than 12 go to renders/real-view<n>/<scene>/, they are not the board's) and draws
     sheet.jpg beside them; for the master scene also compare.jpg, each board view as the offline
     renderer drew it (renders/board/<tag>/) beside the game's;
  5. stops the game, the server and the display, whatever happened before;
  6. leaves the trip's log in renders/real/_trips/<time>-<tag>.log. The receipt of a node job is
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

    --at <commit>            the assembly commit the pictures are named after (default: its head);
                             with --branch, the commit of that branch to shoot (default: its head)
    --tag <name>             this checkout as it is, under this name
    --branch <name>          shoot the code of this branch instead of this checkout's
    --looks <a>,<b>[+dress]  the light versions the scenes are shot under, one after the other
    --view <n> --clouds <n>  render distance and cloud range in chunks (12 and 128)
    --settle, --first-settle, --still   seconds, passed to the shuttle (10, 60, 60)
    --only, --shots, --gallery, --plot, --again   passed to the shuttle as they are
    --no-place               the scenes stand from an earlier trip of the same code
    --budget <seconds>       the trip stops what it is doing after this long, takes what there is
                             and closes down (2700: a job's hour less the node's own start and
                             the push)

Exit code 0: every scene's pictures were all taken and are kept.
"""
import argparse
import os
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
BOARD_VIEW = 12         # the view distance the board is judged at

sys.path.insert(0, HERE)


def end(proc):
    """Stop a stage and what it started in its own process group: asked first, then killed. The
    server, the game and the display are not of that group; nodemc.py down stops them."""
    for sig in (signal.SIGTERM, signal.SIGKILL):
        try:
            os.killpg(proc.pid, sig)
        except OSError:
            return
        for _ in range(20):
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


def sheets(trip, scene, folder, tag, view, clouds):
    """sheet.jpg of a scene's kept pictures; for the master scene compare.jpg beside the offline board."""
    import boardrender
    import realshots
    kept = realshots.read_kept(os.path.join(folder, realshots.NOTE))
    names = [shot for shot in kept if os.path.exists(os.path.join(folder, shot + ".jpg"))]
    if not names:
        return
    commits = ", ".join(sorted({row[1] for row in kept.values()}))
    drawn = f"the game 26.3 on a node, view distance {view}, cloud range {clouds}"
    boardrender.sheet(folder, names, f"c164 {scene}, {drawn}, the code of {commits}", ext=".jpg")
    made = ["sheet.jpg"]
    board = os.path.join(PROJECT, "renders", "board", tag)
    if scene == MASTER and os.path.isdir(board):
        boardrender.side_by_side(board, folder, names, f"c164 board of {commits}: offline (build/render.py) beside {drawn}",
                                 os.path.join(folder, "compare.jpg"))
        made.append(f"compare.jpg (beside renders/board/{tag}/)")
    trip.say(f"{scene}: {', '.join(made)} in {os.path.relpath(folder, PROJECT)}/")


def look_sheets(trip, scene, base, runs, commit, view, clouds):
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
        boardrender.in_columns(columns, names, f"c164 {scene} of {commit}, the game 26.3 on a node, view distance {view}, "
                               f"cloud range {clouds}: each light version at its tick, the windows lit by its table"
                               + (", the building's own lights on (DRESS, off in the code)" if dressed else ""), out)
        trip.say(f"{scene}: {os.path.relpath(out, PROJECT)}, {len(names)} views under {len(columns)} light versions")


def main():
    ap = argparse.ArgumentParser(description="one real-machine trip on a worker node")
    ap.add_argument("scenes", nargs="*", default=[MASTER])
    ap.add_argument("--at", metavar="COMMIT")
    ap.add_argument("--tag")
    ap.add_argument("--branch")
    ap.add_argument("--view", type=int, default=BOARD_VIEW)
    ap.add_argument("--clouds", type=int, default=128)
    ap.add_argument("--settle", type=float, default=10.0)
    ap.add_argument("--first-settle", type=float, default=60.0)
    ap.add_argument("--still", type=float, default=60.0)
    ap.add_argument("--only", action="append", default=[], metavar="SCENE=A,B")
    ap.add_argument("--shots", action="append", default=[], metavar="SCENE=FILE")
    ap.add_argument("--gallery", action="append", default=[], metavar="SCENE")
    ap.add_argument("--plot", action="append", default=[], metavar="SCENE=N")
    ap.add_argument("--again", action="append", default=[], metavar="SCENE=SHOT[:SECONDS]")
    ap.add_argument("--looks", metavar="LOOK[+dress],...")
    ap.add_argument("--no-place", action="store_true")
    ap.add_argument("--budget", type=float, default=2700.0)
    args = ap.parse_args()
    if args.tag and (args.at or args.branch):
        sys.exit("--tag names this checkout as it is; --at and --branch name a commit: one or the other")
    runs = [(None, False)]              # (light version or None for the code as it builds, its own lights on)
    if args.looks:
        runs = [(name.partition("+")[0], name.endswith("+dress")) for name in args.looks.split(",") if name]
        wrong = [name for name in args.looks.split(",") if name and name.partition("+")[2] not in ("", "dress")]
        if wrong or not runs or len(set(runs)) != len(runs):
            sys.exit(f"--looks {args.looks}: light versions by name, each once, +dress for the building's own lights")
        if args.no_place:
            sys.exit("--looks places the scenes anew for every light version; --no-place cannot go with it")

    import boardrender
    import realshots
    project = None
    if args.branch:
        project, commit = other_code(args.branch, args.at)
        tag = commit[:7]
    else:
        tag, commit = boardrender.which_commit(args.tag, args.at)
    kept_in = os.path.join("renders", "real" if args.view == BOARD_VIEW else f"real-view{args.view}")
    # a branch's master scene is not the assembly's: it does not take the place of the board's pictures
    own_in = os.path.join("renders", "real-branch", tag) if project else kept_in
    looks_in = os.path.join(own_in, "looks") if project else os.path.join("renders", kept_in.split(os.sep)[-1] + "-looks", tag)
    log_path = os.path.join(PROJECT, "renders", "real", "_trips", f"{time.strftime('%Y%m%d-%H%M', time.gmtime())}-{tag}.log")
    trip = Trip(log_path, args.budget)

    def cut_short(*_):          # the job is being ended from outside: the closing steps still run
        if trip.running is not None:
            end(trip.running)
        sys.exit(143)
    signal.signal(signal.SIGTERM, cut_short)
    station = os.path.join(HERE, "nodemc.py")
    distances = {"MC_VIEW": str(args.view), "MC_CLOUDS": str(args.clouds)}
    trip.say(f"trip of {', '.join(args.scenes)}: the code of {commit} (tag {tag})"
             + (f" of {args.branch}, checked out at {os.path.dirname(project)}" if project else "")
             + (f", under the light versions {args.looks}" if args.looks else "")
             + f", view distance {args.view}, cloud range {args.clouds}; {os.cpu_count()} cores, {args.budget:.0f} s at most")
    failed, kept = [], []
    try:
        trip.stage("clean", station, "down", budget=180)
        code, _ = trip.stage("setup", station, "setup", budget=min(1500, trip.left() - 300), env=distances)
        if code != 0:
            failed.append("the node could not be made ready")
        else:
            trip.stage("station", station, "status", budget=60)
            options = ["--tag", tag, "--commit", commit, "--settle", args.settle,
                       "--first-settle", args.first_settle, "--still", args.still]
            for name, values in (("--only", args.only), ("--shots", args.shots), ("--gallery", args.gallery),
                                 ("--plot", args.plot), ("--again", args.again)):
                for value in values:
                    options += [name, value]
            if args.no_place:
                options.append("--no-place")
            if project:
                options += ["--project", project]
            for i, (look, dress) in enumerate(runs):
                version = f"{look}{'-dressed' if dress else ''}" if look else ""
                work = os.path.join(WORK, "looks", version) if look else WORK
                under = ["--out", work]
                if look:
                    under += ["--look", look] + (["--dress"] if dress else [])
                if i < len(runs) - 1:
                    under.append("--keep-client")       # the game stays open for the next light version
                name = f"shuttle, {version}" if look else "shuttle"
                code, _ = trip.stage(name, os.path.join(HERE, "win", "shuttle.py"), *options, *under, *args.scenes,
                                     budget=trip.left() - 240, env=distances)
                if code != 0:
                    failed.append(f"the {name} ended with {code}")
                send = os.path.join(work, tag, "send")
                for scene in args.scenes:
                    if scene in args.gallery and not os.path.exists(os.path.join(send, f"{scene}-{tag}-real.txt")):
                        continue        # a scene of models alone that was not shot: the shuttle said why
                    into = os.path.join(looks_in, version) if look else own_in if scene == MASTER else kept_in
                    ok, said = realshots.take(send, tag, scene, os.path.join(PROJECT, into))
                    for line in said:
                        trip.say(line)
                    if not ok:
                        failed.append(f"{scene}: no pictures kept" + (f" of {version}" if look else ""))
                        continue
                    kept.append(f"{into}/{scene}/")
                    if look:
                        continue
                    try:
                        sheets(trip, scene, os.path.join(PROJECT, into, scene), tag, args.view, args.clouds)
                    except Exception as exc:        # the pictures are kept; a sheet is a convenience
                        trip.say(f"{scene}: the sheet could not be drawn ({exc})")
            if args.looks:
                for scene in args.scenes:
                    try:
                        look_sheets(trip, scene, os.path.join(PROJECT, looks_in), runs, commit, args.view, args.clouds)
                    except Exception as exc:
                        trip.say(f"{scene}: the sheet of the light versions could not be drawn ({exc})")
    finally:
        trip.stage("close", station, "down", budget=180)
        where = ", ".join(kept) or "none"
        trip.say(("trip done" if not failed else "trip done with failures: " + "; ".join(failed))
                 + f"; pictures kept: {where}; log {os.path.relpath(log_path, PROJECT)}")
        trip.log.close()
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
