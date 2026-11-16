#!/usr/bin/env python3
"""An author's look at a piece of work in the game: one view some times over, seconds apart.

Not called by hand: tools/look.sh, the one command of a node job of the author's own branch,
checks the render station's tools out beside the job's tree and runs this from there.

    looktrip.py --code <the job's c164-realms> --branch <its branch> --at <its commit> <scene>
                [--from X Y Z --to X Y Z | --only <shot>[,<shot>...]] [--shots 6] [--every 2] [--time <tick>]

<scene> is a test scene of the branch's build/scenes/, or obs for the whole observatory (which
takes some minutes to place). The view is --from (where the eye is) --to (the point looked at), in
the scene's own coordinates, as in its shots.json; or the shots of the scene's own list named
with --only (the board's views for obs: v01_arrival ...); or, without either, every shot of
the scene's list. Each view is taken --shots times, --every seconds apart, from the same place.

What comes home, in <code>/renders/_wip/look/<scene>/ (nodejob.sh --wip pushes it to
<branch>-wip):
    <shot>_0.jpg ... <shot>_<n-1>.jpg   the pictures
    <shot>_strip.jpg                    all of them on one sheet, in the order taken
    <shot>_moved.jpg                    the first one with a frame around every place that moved
    moved.txt                           per view: how many places moved, where (tools/moved.py)
    trip.log                            what the trip said, the game's complaints included
The lines of moved.txt are printed last, so they stand in the job's receipt.
"""
import argparse
import glob
import json
import os
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(HERE)
MASTER = "obs"
MOST = 48               # pictures a look, at most

sys.path.insert(0, HERE)


def base_shots(args):
    """The views asked for, as rows of a shot list."""
    if args.eye or args.to:
        if not (args.eye and args.to):
            sys.exit("--from X Y Z and --to X Y Z go together: where the eye is, and the point it looks at")
        return [{"name": "look", "pos": args.eye, "look_at": args.to}]
    build = os.path.join(args.code, "build")
    if args.scene == MASTER:
        path = os.path.join("/tmp", f"c164_look_board_{os.getpid()}.json")
        got = subprocess.run([sys.executable, os.path.join(HERE, "boardshots.py"), "--out", path],
                             env={**os.environ, "C164_BUILD": build}, capture_output=True, text=True)
        if got.returncode != 0:
            sys.exit("the board's views could not be worked out of this code:\n" + (got.stdout + got.stderr)[-600:])
    else:
        path = os.path.join(build, "scenes", args.scene, "shots.json")
        if not os.path.exists(path):
            sys.exit(f"{args.scene} has no build/scenes/{args.scene}/shots.json: say the view with --from X Y Z --to X Y Z")
    with open(path, encoding="utf-8") as fh:
        shots = json.load(fh)
    names = [s["name"] for s in shots]
    if args.only:
        asked = [n for n in args.only.split(",") if n]
        wrong = [n for n in asked if n not in names]
        if wrong:
            sys.exit(f"--only {','.join(wrong)}: {args.scene} has no such shot; it has {', '.join(names)}")
        shots = [s for s in shots if s["name"] in asked]
    if args.scene == MASTER and not args.only:
        sys.exit(f"obs: say the view with --from X Y Z --to X Y Z, or name board views with --only ({', '.join(names)})")
    return shots


def main():
    ap = argparse.ArgumentParser(description="one view of a piece of work some times over, seconds apart")
    ap.add_argument("scene")
    ap.add_argument("--code", required=True)
    ap.add_argument("--branch", required=True)
    ap.add_argument("--at", required=True)
    ap.add_argument("--from", dest="eye", nargs=3, type=float, metavar=("X", "Y", "Z"))
    ap.add_argument("--to", nargs=3, type=float, metavar=("X", "Y", "Z"))
    ap.add_argument("--only")
    ap.add_argument("--shots", type=int, default=6)
    ap.add_argument("--every", type=float, default=2.0)
    ap.add_argument("--time")
    ap.add_argument("--budget", type=float, default=1150.0)
    args = ap.parse_args()
    if not 2 <= args.shots <= 24 or not 0.2 <= args.every <= 60:
        sys.exit("--shots 2 to 24 pictures a view, --every 0.2 to 60 seconds")
    import boardrender
    import moved
    base = base_shots(args)
    if len(base) * args.shots > MOST:
        sys.exit(f"{len(base)} views of {args.shots} pictures are more than {MOST}: name fewer with --only, or fewer --shots")
    rows = []
    for shot in base:
        if args.time:
            shot = {**shot, "time": int(args.time) if args.time.lstrip("-").isdigit() else args.time}
        rows.append({**shot, "name": shot["name"] + "_0"})
        rows += [{**shot, "name": f"{shot['name']}_{i}", "settle": args.every, "still": 0} for i in range(1, args.shots)]
    listed = os.path.join("/tmp", f"c164_look_{os.getpid()}.json")
    with open(listed, "w", encoding="utf-8") as fh:
        json.dump(rows, fh, indent=1)
    whole = args.scene == MASTER
    trip = [sys.executable, "-u", os.path.join(HERE, "nodetrip.py"), "--branch", args.branch, "--at", args.at,
            "--into", "look", "--shots", f"{args.scene}={listed}", "--settle", 10 if whole else 3,
            "--first-settle", 60 if whole else 20, "--still", 40 if whole else 0, "--budget", args.budget, args.scene]
    t0 = time.time()
    print(f"look: {args.scene} of {args.branch} @ {args.at[:8]}: {len(base)} view(s), {args.shots} pictures each, "
          f"{args.every:g} s apart", flush=True)
    code = subprocess.run([str(a) for a in trip], cwd=PROJECT).returncode
    tag = args.at[:7]
    kept = os.path.join(PROJECT, "renders", "real-branch-look", tag, MASTER) if whole \
        else os.path.join(PROJECT, "renders", "real-look", args.scene)
    out = os.path.join(args.code, "renders", "_wip", "look", args.scene)
    shutil.rmtree(out, ignore_errors=True)
    os.makedirs(out)
    logs = sorted(glob.glob(os.path.join(PROJECT, "renders", "real", "_trips", "*.log")), key=os.path.getmtime)
    logs = [p for p in logs if os.path.getmtime(p) >= t0 - 5 and not p.endswith("-client.log")]
    if logs:
        shutil.copy(logs[-1], os.path.join(out, "trip.log"))
    said = [f"{args.scene} of {args.branch} @ {args.at[:8]}, in the game 26.3 on a node, "
            f"{time.strftime('%Y-%m-%dT%H:%MZ', time.gmtime())}; {args.shots} pictures a view, {args.every:g} s apart "
            f"(and the time a picture takes)"]
    missing = 0
    for shot in base:
        name = shot["name"]
        frames = []
        for i in range(args.shots):
            src = os.path.join(kept, f"{name}_{i}.jpg")
            if os.path.exists(src):
                shutil.copy(src, os.path.join(out, f"{name}_{i}.jpg"))
                frames.append(os.path.join(out, f"{name}_{i}.jpg"))
        missing += args.shots - len(frames)
        if len(frames) < 2:
            said.append(f"{name}: {len(frames)} of {args.shots} pictures were taken -- see trip.log")
            continue
        boardrender.sheet(out, [os.path.basename(f)[:-4] for f in frames],
                          f"c164 {args.scene} {name}: {len(frames)} pictures {args.every:g} s apart, the game 26.3 on a "
                          f"node, the code of {args.at[:8]}", ext=".jpg", out=os.path.join(out, f"{name}_strip.jpg"))
        found, share = moved.places(frames)
        moved.draw(frames[0], found, os.path.join(out, f"{name}_moved.jpg"))
        said.append(moved.told(name, found, share))
    with open(os.path.join(out, "moved.txt"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(said) + "\n")
    print(f"look: kept in renders/_wip/look/{args.scene}/ ({time.time() - t0:.0f} s; the trip's exit code {code})")
    print("\n".join(said), flush=True)
    sys.exit(code or (1 if missing else 0))


if __name__ == "__main__":
    main()
