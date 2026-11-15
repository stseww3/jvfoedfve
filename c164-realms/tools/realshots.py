#!/usr/bin/env python3
"""Real-machine pictures, as they come back from the render station, into the repository.

    realshots.py --take <tag> [<scene> ...] [--from <folder>]
    realshots.py --list [<scene> ...]

A trip of the render station (bin/trip.py on the admin's computer, tools/win/shuttle.py) sends for
every scene <scene>-<tag>-<shot>.jpg, the game's own screenshots, and a note <scene>-<tag>-real.txt
that says for every shot its tick, the commit of the code it shows and the first 16 digits of the
picture file's SHA-256. They arrive in the inbox of the cloud machine, which is emptied whenever
that machine is started anew; pictures that are to be looked at later have to be in git.

--take checks every picture of a scene against the note (did it arrive, is it the file that was
sent) and then puts them into renders/real/<scene>/<shot>.jpg of this checkout, with the scene's
own note renders/real/<scene>/real.txt: shot, tick, commit, SHA-256, when it was taken. When a
picture of a scene is missing or is not the file the note describes, nothing of that scene is
touched and it says which; send again (bin/trip.py --send-only) and take again. A trip that shot
only some of a scene's shots replaces those and leaves the others, each with its own commit in the
note. Then commit and push: that is the render station's to do.

--list says what is kept: for every scene the shots and the commits they show.

Real-machine pictures are the look of the finished thing: fog, particles, the game's clouds, the
light as the client draws it. The pictures a package keeps of itself (renders/<scene>/, drawn
offline by tools/selfshots.py) are another matter and are not touched here.
"""
import argparse
import glob
import hashlib
import os
import re
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(HERE)
ROOT = os.environ.get("MC_ROOT", "/agent/realms-study")
KEPT = os.path.join(PROJECT, "renders", "real")
NOTE = "real.txt"
HEAD = "# real-machine pictures (tools/realshots.py): shot, tick, commit of the code the picture shows, " \
       "first 16 of the picture file's sha256, when it was taken"
NAME_OK = re.compile(r"[A-Za-z0-9_.\-]+\Z")


def digest(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()[:16]


def read_sent(path):
    """A trip's note for one scene: (when the pictures were taken, [(shot, tick, commit, sha)])."""
    taken, rows = "?", []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line.startswith("#"):
                m = re.search(r"taken (\d{4}-\d\d-\d\d) (\d\d:\d\d)", line)
                if m:
                    taken = f"{m.group(1)}T{m.group(2)}"
                continue
            parts = line.split()
            if len(parts) == 4 and NAME_OK.match(parts[0]):
                rows.append(tuple(parts))
            elif parts:
                raise SystemExit(f"{path}: a line that is not 'shot tick commit sha256': {line[:80]}")
    return taken, rows


def read_kept(path):
    """The note kept with a scene's pictures: {shot: (tick, commit, sha, taken)}, in the file's order."""
    kept = {}
    try:
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                parts = line.split()
                if len(parts) == 5 and not line.startswith("#"):
                    kept[parts[0]] = tuple(parts[1:])
    except OSError:
        pass
    return kept


def take(source, tag, scene):
    """Put one scene's pictures of one trip into renders/real/<scene>/. Returns (taken?, what to
    say); a scene that cannot be taken whole is left as it was."""
    stem = f"{scene}-{tag}-"
    note = os.path.join(source, stem + "real.txt")
    if not os.path.exists(note):
        return False, [f"{scene}: no note {stem}real.txt in {source} (not sent yet, or another tag)"]
    taken, rows = read_sent(note)
    if not rows:
        return False, [f"{scene}: the note names no picture"]
    wrong = []
    for shot, _, _, sha in rows:
        path = os.path.join(source, f"{stem}{shot}.jpg")
        if not os.path.exists(path):
            wrong.append(f"{shot}.jpg has not arrived")
        elif digest(path) != sha:
            wrong.append(f"{shot}.jpg is not the file that was sent")
    if wrong:
        return False, [f"{scene}: nothing taken: " + "; ".join(wrong)]
    folder = os.path.join(KEPT, scene)
    os.makedirs(folder, exist_ok=True)
    kept = read_kept(os.path.join(folder, NOTE))
    new, same = [], 0
    for shot, tick, commit, sha in rows:
        if kept.get(shot, ("", "", ""))[2] == sha and os.path.exists(os.path.join(folder, shot + ".jpg")):
            same += 1           # the very picture that is kept: its line stays as it is
            continue
        shutil.copyfile(os.path.join(source, f"{stem}{shot}.jpg"), os.path.join(folder, shot + ".jpg"))
        new.append(shot)
        kept[shot] = (tick, commit, sha, taken)
    with open(os.path.join(folder, NOTE), "w", encoding="utf-8", newline="\n") as fh:
        fh.write(HEAD + "\n" + "".join(f"{shot} {' '.join(row)}\n" for shot, row in kept.items()))
    commits = sorted({row[2] for row in rows})
    said = [f"{scene}: {len(rows)} pictures of {', '.join(commits)} in renders/real/{scene}/"
            + (f" ({len(new)} new or changed, {same} as they were)" if same else "")]
    return True, said


def listing(scenes):
    found = sorted(os.listdir(KEPT)) if os.path.isdir(KEPT) else []
    for scene in scenes or found:
        kept = read_kept(os.path.join(KEPT, scene, NOTE))
        if not kept:
            print(f"{scene}: nothing kept")
            continue
        by_commit = {}
        for shot, (_, commit, _, taken) in kept.items():
            by_commit.setdefault((commit, taken), []).append(shot)
        print(f"{scene}: {len(kept)} pictures")
        for (commit, taken), shots in by_commit.items():
            print(f"    {commit}, taken {taken}: {', '.join(shots)}")


def main():
    ap = argparse.ArgumentParser(description="real-machine pictures into renders/real/")
    ap.add_argument("scenes", nargs="*")
    ap.add_argument("--take", metavar="TAG")
    ap.add_argument("--from", dest="source", default=os.path.join(ROOT, "inbox"), metavar="FOLDER")
    ap.add_argument("--list", action="store_true")
    args = ap.parse_args()
    if args.list:
        listing(args.scenes)
        return 0
    if not args.take:
        ap.error("--take <tag> or --list")
    scenes = args.scenes
    if not scenes:
        tail = f"-{args.take}-real.txt"
        scenes = sorted(os.path.basename(p)[:-len(tail)] for p in glob.glob(os.path.join(args.source, "*" + tail)))
        if not scenes:
            print(f"no note *{tail} in {args.source}")
            return 1
    failed = 0
    for scene in scenes:
        ok, said = take(args.source, args.take, scene)
        failed += not ok
        print("\n".join(said))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
