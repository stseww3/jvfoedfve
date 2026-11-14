#!/usr/bin/env python3
"""A scene's own pictures, drawn offline here and kept in the repository (plan/roles/INTERFACE.md 7).

    selfshots.py <scene> [<scene> ...] [--only a,b]    draw renders/<scene>/<shot>.png for the shots of
                                                        build/scenes/<scene>/shots.json
    selfshots.py <scene> [<scene> ...] --verify         draw them again elsewhere and compare: are the
                                                        kept pictures what the code draws now?

Drawing is build/render.py's (1280x720, every shot at its own time; no game needed). A picture is
overwritten under its shot's name, a picture whose shot has left the list is removed, and
renders/<scene>/shots.txt notes for every shot its tick and the commit whose code it shows. So
commit the code first (drawing is refused otherwise; --dirty to look at a change before that),
draw, and commit the pictures once, before the delivery: a picture stays in the history for good.

--verify writes nothing and needs no clean worktree. It ends with 1 when a picture is missing, is
left over or is not what the code draws; the merge-key holder runs it on the delivered commit.
--project <dir> works on another checkout's c164-realms, with that checkout's code.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

import numpy as np
from PIL import Image

SIZE = "1280x720"
NOTE = "shots.txt"
HEAD = "# shot, tick, commit of the code the picture shows (tools/selfshots.py; drawn offline, {size})"
NAME_OK = re.compile(r"[A-Za-z0-9_.\-]+\Z")


def git(project, *args):
    got = subprocess.run(("git", "-C", project) + args, capture_output=True, text=True)
    return got.stdout if got.returncode == 0 else None


def shot_list(project, scene):
    path = os.path.join(project, "build", "scenes", scene, "shots.json")
    if not os.path.exists(path):
        sys.exit(f"{scene}: no shot list build/scenes/{scene}/shots.json")
    with open(path, encoding="utf-8") as fh:
        names = [s["name"] for s in json.load(fh)]
    bad = [n for n in names if not NAME_OK.match(n)] + sorted({n for n in names if names.count(n) > 1})
    if bad:
        sys.exit(f"{scene}: shot names that cannot name a picture (odd characters or used twice): {', '.join(bad)}")
    return path, names


def draw(project, scene, shots, only, out, jar):
    """Runs the checkout's build/render.py into the folder `out`. Returns {shot: (picture file, tick)}."""
    prefix = os.path.join(out, "s")
    cmd = [sys.executable, os.path.join(project, "build", "render.py"), scene, "--shots", shots,
           "--out", prefix, "--size", SIZE]
    if only:
        cmd += ["--only", ",".join(only)]
    if jar:
        cmd += ["--jar", jar]
    got = subprocess.run(cmd, cwd=project, capture_output=True, text=True)
    if got.returncode != 0:
        tail = "\n".join((got.stdout + got.stderr).strip().splitlines()[-12:])
        sys.exit(f"{scene}: build/render.py failed\n{tail}")
    made = {}
    for line in got.stdout.splitlines():
        cut = line.rfind(".png (tick ")
        if line.startswith(prefix + "-") and cut > 0:
            tick = re.match(r"-?\d+", line[cut + len(".png (tick "):])
            made[line[len(prefix) + 1:cut]] = (line[:cut + 4], tick.group(0) if tick else "?")
    return made


def read_note(folder):
    """{shot: (tick, commit)} of the folder's note; None without one."""
    path = os.path.join(folder, NOTE)
    if not os.path.exists(path):
        return None
    out = {}
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            parts = line.rstrip("\n").split("\t")
            if len(parts) == 3 and not line.startswith("#"):
                out[parts[0]] = (parts[1], parts[2])
    return out


def write(project, scene, only, dirty, jar):
    shots, names = shot_list(project, scene)
    unknown = [n for n in only if n not in names]
    if unknown:
        sys.exit(f"{scene}: not in the shot list: {', '.join(unknown)}")
    commit = (git(project, "rev-parse", "--short=8", "HEAD") or "").strip()
    if not commit:
        sys.exit(f"{project} is not in a git checkout")
    changed = (git(project, "status", "--porcelain", "--", "build") or "").splitlines()
    if changed and not dirty:
        shown = ", ".join(c[3:] for c in changed[:4]) + (f" and {len(changed) - 4} more" if len(changed) > 4 else "")
        sys.exit(f"{scene}: the code is not committed ({shown}), so no commit shows what the pictures would show.\n"
                 f"Commit it and draw again; --dirty draws anyway and notes the commit with a +.")
    folder = os.path.join(project, "renders", scene)
    tmp = tempfile.mkdtemp(prefix="c164-selfshots-")
    try:
        made = draw(project, scene, shots, only, tmp, jar)
        wanted = only or names
        missing = [n for n in wanted if n not in made]
        if missing:
            sys.exit(f"{scene}: build/render.py drew no picture of {', '.join(missing)}")
        os.makedirs(folder, exist_ok=True)
        note = read_note(folder) or {}
        total = 0
        for name in wanted:
            path, tick = made[name]
            target = os.path.join(folder, name + ".png")
            Image.open(path).save(target, optimize=True)
            total += os.path.getsize(target)
            note[name] = (tick, commit + ("+" if changed else ""))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    gone = []
    if not only:
        for f in sorted(os.listdir(folder)):
            if f.endswith(".png") and f[:-4] not in names:
                os.remove(os.path.join(folder, f))
                gone.append(f)
    with open(os.path.join(folder, NOTE), "w", encoding="utf-8", newline="\n") as fh:
        fh.write(HEAD.format(size=SIZE) + "\n")
        for name in names:
            if name in note:
                fh.write(f"{name}\t{note[name][0]}\t{note[name][1]}\n")
    print(f"renders/{scene}/: {len(wanted)} picture{'s' if len(wanted) != 1 else ''} of {commit}"
          f"{'+ (uncommitted code)' if changed else ''} drawn, {total / 1048576:.1f} MB"
          + (f"; removed (no such shot any more): {', '.join(gone)}" if gone else ""))
    absent = [n for n in names if not os.path.exists(os.path.join(folder, n + ".png"))]
    if absent:
        print(f"                still without a picture: {', '.join(absent)}")
    return True


def verify(project, scene, jar):
    shots, names = shot_list(project, scene)
    folder = os.path.join(project, "renders", scene)
    kept = sorted(f[:-4] for f in os.listdir(folder) if f.endswith(".png")) if os.path.isdir(folder) else []
    fails, warns = [], []
    tmp = tempfile.mkdtemp(prefix="c164-selfshots-")
    try:
        made = draw(project, scene, shots, None, tmp, jar)
        same = 0
        for name in names:
            path = os.path.join(folder, name + ".png")
            if name not in made:
                fails.append(f"{name}: build/render.py drew no picture")
            elif not os.path.exists(path):
                fails.append(f"{name}: no picture kept")
            else:
                a = np.asarray(Image.open(path).convert("RGB")).astype(np.int16)
                b = np.asarray(Image.open(made[name][0]).convert("RGB")).astype(np.int16)
                if a.shape != b.shape:
                    fails.append(f"{name}: kept {a.shape[1]}x{a.shape[0]}, drawn {b.shape[1]}x{b.shape[0]}")
                    continue
                off = np.abs(a - b).max(axis=2)
                if off.any():
                    fails.append(f"{name}: {int((off > 0).sum())} of {off.size} pixels are not what the code draws "
                                 f"(off by up to {int(off.max())} of 255)")
                else:
                    same += 1
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    fails += [f"{n}.png: left over, the list has no such shot" for n in kept if n not in names]
    note = read_note(folder)
    if note is None:
        warns.append(f"no {NOTE}: which commit the pictures show is not noted")
    else:
        for name in names:
            tick, commit = note.get(name, (None, None))
            if commit is None:
                warns.append(f"{name}: not in {NOTE}")
            elif commit.endswith("+"):
                warns.append(f"{name}: noted as drawn from uncommitted code ({commit})")
            elif git(project, "merge-base", "--is-ancestor", commit, "HEAD") is None:
                warns.append(f"{name}: noted commit {commit} is not in this branch's history")
            elif name in made and tick != made[name][1]:
                warns.append(f"{name}: noted at tick {tick}, drawn at {made[name][1]}")
    status = "FAIL" if fails else "WARN" if warns else "PASS"
    head = (git(project, "rev-parse", "--short=8", "HEAD") or "?").strip()
    print(f"[{status}] selfshots {scene} at {head}: {same} of {len(names)} kept pictures are what the code draws"
          + (f", {len(fails)} not" if fails else ""))
    for line in fails + warns:
        print(f"                {line}")
    return not fails


def main():
    ap = argparse.ArgumentParser(description="a scene's own offline pictures, kept in renders/<scene>/")
    ap.add_argument("scenes", nargs="+")
    ap.add_argument("--only", help="comma separated shot names: draw only these")
    ap.add_argument("--verify", action="store_true", help="compare the kept pictures with what the code draws")
    ap.add_argument("--dirty", action="store_true", help="draw although the code under build/ is not committed")
    ap.add_argument("--project", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."),
                    help="the c164-realms folder of the checkout to work on (default: this one)")
    ap.add_argument("--jar", help="the client jar, where it is not in build/render.py's usual place")
    args = ap.parse_args()
    project = os.path.abspath(args.project)
    only = [n for n in (args.only or "").split(",") if n]
    if args.verify and (only or args.dirty):
        sys.exit("--verify compares every shot of the list as the code stands; it takes neither --only nor --dirty")
    if only and len(args.scenes) > 1:
        sys.exit("--only names shots of one scene")
    good = True
    for scene in args.scenes:
        good = (verify(project, scene, args.jar) if args.verify else write(project, scene, only, args.dirty, args.jar)) \
            and good
    sys.exit(0 if good else 1)


if __name__ == "__main__":
    main()
