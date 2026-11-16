#!/usr/bin/env python3
"""Which kept pictures are still what the code draws: tools/selfshots.py --verify on every scene that
keeps pictures, in one go. The round the merge-key holder makes after a batch of merges
(plan/roles/S2-integrator.md). A merge can change what another package's test scene shows (the
facade under the lights, a texture under a wall); the pictures kept of that scene then show a
building that is no longer the assembly's. Nothing here fails a delivery: the list says whose
pictures are to be drawn again.

    keptshots.py                      every scene with pictures in renders/<scene>/
    keptshots.py obs_sky_lights ...   the scenes named

    --out <folder>   <scene>.txt as selfshots.py prints it, beside summary.txt, which is what this
                     script prints (default renders/_wip/kept, the folder tools/nodejob.sh --wip
                     brings home)
    --jobs <n>       scenes drawn at a time (default: half the machine's cores)
    --jar <file>     passed on to selfshots.py

Heavy, every kept picture is drawn again: send it to your node,

    bash c164-realms/tools/nodejob.sh --wip --always python tools/keptshots.py

One line per scene: SAME (every kept picture is what the code draws), STALE with the shots that are
not, NOLIST for pictures of a scene without a shot list (nothing says how they were drawn), BROKEN
when selfshots.py ended without a result (its last lines are shown). The exit code is 1 only for
BROKEN; stale pictures are news, not a failure.
"""
import argparse
import concurrent.futures
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.normpath(os.path.join(HERE, ".."))
SCENES = os.path.join(PROJECT, "build", "scenes")
RENDERS = os.path.join(PROJECT, "renders")
WIDTH = 220                 # of a line of the summary
RESULT = re.compile(r"^\[(PASS|WARN|FAIL)\] selfshots (\S+) at (\S+): (\d+) of (\d+) kept pictures are what the "
                    r"code draws(?:, (\d+) not)?")


def pictures(scene):
    folder = os.path.join(RENDERS, scene)
    return sorted(f for f in os.listdir(folder) if f.endswith(".png")) if os.path.isdir(folder) else []


def kept_scenes():
    return sorted(n for n in os.listdir(RENDERS) if (n == "obs" or n.startswith("obs_")) and pictures(n))


def run(scene, out, jar):
    """One scene through selfshots.py --verify.
    Returns (scene, seconds, exit code, (same, looked, shots that differ, notes) or None, last lines)."""
    text = os.path.join(out, f"{scene}.txt")
    cmd = [sys.executable, os.path.join(HERE, "selfshots.py"), scene, "--verify"]
    if jar:
        cmd += ["--jar", jar]
    t0 = time.time()
    with open(text, "w", encoding="utf-8") as fh:
        code = subprocess.run(cmd, cwd=PROJECT, stdout=fh, stderr=subprocess.STDOUT).returncode
    with open(text, encoding="utf-8", errors="replace") as fh:
        said = fh.read().rstrip().split("\n")
    found = None
    for i, line in enumerate(said):
        m = RESULT.match(line)
        if m:
            # under the result line: what differs first, then the notes (selfshots.py, verify())
            under = [x.strip() for x in said[i + 1:] if x.startswith(" " * 16)]
            differ = int(m.group(6) or 0)
            found = (int(m.group(4)), int(m.group(5)), [x.split(":", 1)[0] for x in under[:differ]], under[differ:])
    return scene, time.time() - t0, code, found, said[-6:]


def main():
    ap = argparse.ArgumentParser(description="tools/selfshots.py --verify on every scene that keeps pictures")
    ap.add_argument("scenes", nargs="*")
    ap.add_argument("--out", default=os.path.join(RENDERS, "_wip", "kept"))
    ap.add_argument("--jobs", type=int, default=max(1, (os.cpu_count() or 2) // 2))
    ap.add_argument("--jar")
    args = ap.parse_args()
    scenes = args.scenes or kept_scenes()
    none = [s for s in scenes if not pictures(s)]
    if none:
        sys.exit(f"no pictures kept in renders/ of: {', '.join(none)}")
    listed = [s for s in scenes if os.path.exists(os.path.join(SCENES, s, "shots.json"))]
    out = os.path.abspath(args.out)
    os.makedirs(out, exist_ok=True)
    t0 = time.time()
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, args.jobs)) as pool:
        results = {r[0]: r for r in pool.map(lambda s: run(s, out, args.jar), listed)}
    lines, stale, broken, same_all, looked_all = [], [], [], 0, 0
    for scene in scenes:
        if scene not in results:
            lines.append(f"NOLIST {scene}: {len(pictures(scene))} pictures, no shot list build/scenes/{scene}/shots.json")
            continue
        _, secs, code, found, tail = results[scene]
        if found is None:
            broken.append(scene)
            lines.append(f"BROKEN {scene}: selfshots.py ended with {code} and no result ({secs:.0f} s)")
            lines += [f"           {line}"[:WIDTH] for line in tail]
            continue
        same, looked, differ, notes = found
        same_all, looked_all = same_all + same, looked_all + looked
        noted = f", {len(notes)} notes in {scene}.txt" if notes else ""
        if differ:
            stale.append(scene)
            lines.append(f"STALE  {scene}: {same} of {looked} are what the code draws; not: {', '.join(differ)}"
                         f"{noted} ({secs:.0f} s)")
        else:
            lines.append(f"SAME   {scene}: {same} of {looked}{noted} ({secs:.0f} s)")
    head = subprocess.run(("git", "rev-parse", "--short=8", "HEAD"), cwd=PROJECT, capture_output=True,
                          text=True).stdout.strip() or "?"
    lines.append(f"kept pictures at {head}: {len(scenes)} scenes, {looked_all} pictures in {time.time() - t0:.0f} s: "
                 f"{same_all} are what the code draws, {looked_all - same_all} not"
                 + (f" (in {len(stale)} scenes: {', '.join(stale)})" if stale else "")
                 + (f"; {len(broken)} BROKEN: {', '.join(broken)}" if broken else ""))
    print("\n".join(lines))
    with open(os.path.join(out, "summary.txt"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(lines) + "\n")
    sys.exit(1 if broken else 0)


if __name__ == "__main__":
    main()
