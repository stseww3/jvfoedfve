"""One trip of the real-machine render station, from the code on GitHub to the pictures on the cloud machine.

    python bin/trip.py [--ref <branch or commit>] [--tag <seven digits>] <scene> [<scene> ...]

The command of whoever holds the render key (bin/limits.json, "operators"); nobody else starts the
test server or the game. A trip takes minutes, so start it in the background and read its log:

    venv\\Scripts\\python.exe bin\\bg.py trip venv\\Scripts\\python.exe bin\\trip.py obs obs_props_lamps
    Get-Content logs\\trip.log -Tail 30          # logs\\trip.rc holds the exit code when it is over

What it does, in this order:
  1. brings the code that is shot, the copy in agents/s1-stage/repo, to --ref: the integration
     branch when nothing is said, or the branch somebody asked pictures of, or a commit (all its
     40 digits; a commit that is not a branch's newest can only be fetched so). --tag names the
     pictures; without it, it is the first seven digits of the commit that was fetched;
  2. looks at the machine (winmc.py status: the server, the game, the display, free video memory);
  3. runs the shuttle (tools/win/shuttle.py) through bin/job.py in a heavy slot, so that the game
     and an offline rendering never fill the cores together: the look, the scenes on their plots,
     one resource pack, the game opened once, every shot list, the game closed;
  4. closes the game once more, whatever became of the shuttle, stops the test server, and looks
     at the machine again: between trips nothing of the station runs;
  5. sends the pictures back (bin/send.py): <scene>-<tag>-<shot>.jpg and the note
     <scene>-<tag>-real.txt, for tools/realshots.py on the cloud machine.

The station's own tools are the copy in agents/s1/repo, not the code that is shot, so that a
branch with older tools, or none, can be photographed. That copy changes only when asked:
--tools <ref> brings it to a branch or commit first (the integration branch once the tools are in it).

    --shots, --only, --plot, --no-place, --no-shoot, --settle, --first-settle
                      go to the shuttle as they are (see tools/win/shuttle.py)
    --no-send         leave the pictures in agents/s1/out/real/<tag>/send
    --send-only       only step 5, for a trip whose pictures did not get through (--tag is needed)
    --keep-server     leave the test server running (the next trip starts sooner)
    --keep-client     leave the game and the server running (only with the owner's consent)
    --timeout <s>     the shuttle is stopped after this long (default 3000)
    --wait <s>        how long to stand in line for the heavy slot (default 1800)

Exit code: 0 pictures taken and sent; 2 taken, but some were not sent; 3 not enough free video
memory, the game was not started; 75 another trip is running, or no heavy slot came free; 1 otherwise.
"""
import argparse
import datetime
import glob
import json
import os
import re
import subprocess
import sys

BIN = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(BIN)
sys.path.insert(0, BIN)

import job  # noqa: E402
import sync  # noqa: E402

STATION, STAGE = "s1", "s1-stage"
LOCK = os.path.join(ROOT, "locks", "trip.lock")
SEND_AT_ONCE = 40


def say(text):
    print(f"[trip {datetime.datetime.now().strftime('%H:%M:%S')}] {text}", flush=True)


def call(script, *args):
    """Run one of bin's scripts with this Python; its output goes where ours goes."""
    return subprocess.run([sys.executable, os.path.join(BIN, script), *[str(a) for a in args]], cwd=ROOT,
                          stdin=subprocess.DEVNULL).returncode


def station(*args, heavy=None, timeout=None):
    """A job of the station's own copy; heavy is how long to wait for the slot."""
    head = [STATION]
    if heavy is not None:
        head += ["--heavy", "--wait", heavy]
    if timeout is not None:
        head += ["--timeout", timeout]
    return call("job.py", *head, "--", *args)


def head_of(repo):
    got = subprocess.run([sync.GIT, "-C", repo, "rev-parse", "HEAD"], capture_output=True, text=True)
    return got.stdout.strip() if got.returncode == 0 else ""


def take_lock():
    os.makedirs(os.path.dirname(LOCK), exist_ok=True)
    held = job.holder(LOCK)
    if held and job.alive(int(held.get("pid", 0))):
        return held
    with open(LOCK, "w") as fh:
        json.dump({"pid": os.getpid(), "since": datetime.datetime.now().strftime("%H:%M:%S"),
                   "what": " ".join(sys.argv[1:])}, fh)
    return None


def send(tag, scenes):
    """Send what the shuttle left ready. Returns (how many files there are, did all get through)."""
    folder = os.path.join(ROOT, "agents", STATION, "out", "real", tag, "send")
    notes, pictures = [], []
    for scene in scenes:
        for path in sorted(glob.glob(os.path.join(folder, f"{scene}-{tag}-*"))):
            (notes if path.endswith("-real.txt") else pictures).append(path)
    count = len(notes) + len(pictures)
    # the notes are small and go first: when the upload address is dead, that shows at once and
    # the pictures are not tried one by one
    if not notes or call("send.py", *notes) != 0:
        return count, False
    whole = True
    for i in range(0, len(pictures), SEND_AT_ONCE):
        whole = call("send.py", *pictures[i:i + SEND_AT_ONCE]) == 0 and whole
    return count, whole


def main():
    ap = argparse.ArgumentParser(description="one trip of the real-machine render station")
    ap.add_argument("scenes", nargs="+")
    ap.add_argument("--ref", default=sync.MAIN)
    ap.add_argument("--tag")
    ap.add_argument("--tools")
    ap.add_argument("--shots", action="append", default=[])
    ap.add_argument("--only", action="append", default=[])
    ap.add_argument("--plot", action="append", default=[])
    ap.add_argument("--no-place", action="store_true")
    ap.add_argument("--no-shoot", action="store_true")
    ap.add_argument("--settle")
    ap.add_argument("--first-settle")
    ap.add_argument("--no-send", action="store_true")
    ap.add_argument("--send-only", action="store_true")
    ap.add_argument("--keep-server", action="store_true")
    ap.add_argument("--keep-client", action="store_true")
    ap.add_argument("--timeout", type=int, default=3000)
    ap.add_argument("--wait", type=int, default=1800)
    args = ap.parse_args()
    if not os.path.isdir(os.path.join(ROOT, "server26")):
        sys.exit(f"{ROOT} is not the shared workspace: this is run as bin/trip.py there")
    if STATION not in job.limits().get("operators", ["a0"]):
        sys.exit(f"{STATION} is not among the operators in bin/limits.json")
    if args.send_only and not args.tag:
        sys.exit("--send-only wants --tag")
    if re.fullmatch(r"[0-9a-f]{7,39}", args.ref):
        sys.exit(f"--ref {args.ref}: a commit is given with all its 40 digits (or name the branch)")

    held = take_lock()
    if held:
        say(f"another trip is running (process {held.get('pid')}, since {held.get('since')}: {held.get('what')})")
        return 75
    try:
        tag = args.tag
        if not args.send_only:
            # ---- 1. the code ----
            if args.tools and call("sync.py", args.tools, "--to", f"agents/{STATION}") != 0:
                say("the station's tools could not be brought up to date")
                return 1
            if not os.path.exists(os.path.join(ROOT, "agents", STATION, "repo", "c164-realms", "tools", "win", "shuttle.py")):
                say(f"agents/{STATION}/repo holds no shuttle: give --tools <branch or commit that has tools/win/shuttle.py>")
                return 1
            if call("sync.py", args.ref, "--to", f"agents/{STAGE}") != 0:
                say(f"{args.ref} could not be fetched")
                return 1
            commit = head_of(os.path.join(ROOT, "agents", STAGE, "repo"))
            tag = tag or commit[:7]
            if not tag:
                say("the commit of the code is not known: give --tag")
                return 1
            say(f"shooting {args.ref} at {commit[:9] or '?'} as {tag}: {', '.join(args.scenes)}")

            # ---- 2. the machine before ----
            station(os.path.join("..", "tools", "winmc.py"), "status")

            # ---- 3. the shuttle ----
            options = []
            for name in ("shots", "only", "plot"):
                for value in getattr(args, name):
                    options += [f"--{name}", value]
            for name in ("no_place", "no_shoot", "keep_client"):
                if getattr(args, name):
                    options.append("--" + name.replace("_", "-"))
            for name in ("settle", "first_settle"):
                if getattr(args, name) is not None:
                    options += ["--" + name.replace("_", "-"), getattr(args, name)]
            code = station(os.path.join("..", "tools", "win", "shuttle.py"),
                           "--project", f"@root/agents/{STAGE}/repo/c164-realms", "--tag", tag, "--out", "@out/real",
                           *args.scenes, *options, heavy=args.wait, timeout=args.timeout)

            # ---- 4. the game is closed, the server stopped, the machine after ----
            if not args.keep_client:
                station(os.path.join("..", "tools", "winmc.py"), "client-down")
                if not args.keep_server:
                    station(os.path.join("..", "tools", "winmc.py"), "server-down")
            station(os.path.join("..", "tools", "winmc.py"), "status")
            if code == 3:
                say("not enough free video memory: the game was not started. Tell the director; "
                    "run the trip again with --no-place when there is room")
                return 3
            if code == 75:
                say("no heavy slot came free: an offline rendering is running; try again later")
                return 75
            if code != 0:
                say(f"the shuttle ended with {code}; what it took is sent all the same")
        else:
            code = 0

        # ---- 5. the pictures go back ----
        if args.no_send or args.no_shoot:
            say("nothing is sent")
            return 0 if code == 0 else 1
        count, whole = send(tag, args.scenes)
        if not count:
            say("there are no pictures to send")
            return 1
        folder = os.path.join("agents", STATION, "out", "real", tag, "send")
        if not whole:
            say(f"some of the {count} files did not get through (the upload address may be an old one: tell the "
                f"director). They stay in {folder}; send them again with: bin\\trip.py --send-only --tag {tag} "
                + " ".join(args.scenes))
            return 2
        say(f"{count} files sent from {folder}. On the cloud machine: tools/realshots.py --take {tag} "
            + " ".join(args.scenes))
        return 0 if code == 0 else 1
    finally:
        try:
            os.remove(LOCK)
        except OSError:
            pass


if __name__ == "__main__":
    sys.exit(main())
