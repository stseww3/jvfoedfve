#!/usr/bin/env python3
"""Real-machine pictures, as they come back from the render station, into the repository.

    realshots.py --take <tag> [<scene> ...] [--from <folder>] [--into <folder>]
    realshots.py --list [<scene> ...] [--into <folder>]
    realshots.py --sheet <name> [--across <n>] [--title <text>] <scene>:<shot> ... [--into <folder>]
    realshots.py --columns <name> --shots <a,b,...> [--title <text>] <label>=<folder> ...

A trip of the render station (tools/nodetrip.py on a worker node, bin/trip.py on the admin's
computer; both run tools/win/shuttle.py) leaves for every scene <scene>-<tag>-<shot>.jpg, the game's
own screenshots, and a note <scene>-<tag>-real.txt that says for every shot its tick, the commit of
the code it shows, the first 16 digits of the picture file's SHA-256 and when it was taken, and in
its heading the distances the game drew at. On a node they lie in the trip's folder and nodetrip.py takes them
itself; from the admin's computer they arrived in the inbox of the cloud machine.

--take checks every picture of a scene against the note (did it arrive, is it the file that was
sent) and then puts them into renders/real/<scene>/<shot>.jpg of this checkout, with the scene's
own note renders/real/<scene>/real.txt: shot, tick, commit, SHA-256, when it was taken, and the
distances it was drawn at (view12,server10,clouds128: the client's render distance, the server's
view distance -- the game draws the smaller of the two -- and the cloud range, in chunks; a line
without server<n>, taken before 11-16 07:20, had the server at the client's distance; after them
windows-deep when the scene was built for a light version named to the shuttle, here "deep", and
dressed when the building's own lights were turned on for the picture, which the code keeps off).
When a picture of a scene is missing or is not the file the note describes, nothing of that scene is
touched and it says which; send again (bin/trip.py --send-only) and take again. A trip that shot
only some of a scene's shots replaces those and leaves the others, each with its own commit in the
note. Then commit and push: that is the render station's to do.

--list says what is kept: for every scene the shots and the commits they show.

--sheet puts kept pictures picked by hand on one sheet, in the order given and <n> across (2):
renders/real/_sheets/<name>.jpg, every picture under its scene, shot, tick and commit. For a
question that is answered by a few pictures side by side.

--columns puts the same shots of several kept folders side by side, one row a shot and one column
a folder: renders/real/_sheets/<name>.jpg. A folder is a scene's folder of pictures, given from
renders/ (real/obs, real-server12/obs, real-branch/<tag>/obs, board/<tag> for the offline board):
the same views at two distances, of two commits, by the game and by the offline renderer. Every
cell says its label and, where the folder has a note, the commit and the distances of its picture.

--into names another folder of this checkout than renders/real: pictures drawn at other distances
than the board's (the client's 12 chunks, the server's 10) are kept apart
(renders/real-view32/<scene>/, renders/real-server12/<scene>/), so that they never stand in for
the pictures the board is judged by.

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
       "first 16 of the picture file's sha256, when it was taken, the client's render distance, the server's " \
       "view distance (where none is given: the client's) and the cloud range in chunks"
NAME_OK = re.compile(r"[A-Za-z0-9_.\-]+\Z")


def digest(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()[:16]


def read_sent(path):
    """A trip's note for one scene: (when the trip took its pictures, the distances they were drawn
    at or None when the note does not say, [(shot, tick, commit, sha, when it was taken)]). A line
    says when its own picture was taken where the trip left pictures of an earlier one under the
    same distances in its note; a line that does not is of the head's time."""
    taken, view, rows = "?", None, []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line.startswith("#"):
                m = re.search(r"taken (\d{4}-\d\d-\d\d) (\d\d:\d\d)", line)
                if m:
                    taken = f"{m.group(1)}T{m.group(2)}"
                m = re.search(r"render distance (\d+), server view distance (\d+), cloud range (\d+)", line)
                if m:
                    view = ",".join(filter(None, [f"view{m.group(1)},server{m.group(2)},clouds{m.group(3)}", view]))
                m = re.match(r"# windows: lit by the table of look (\w+)", line)
                if m:
                    view = ",".join(filter(None, [view, f"windows-{m.group(1)}",
                                                  "dressed" if "the building's own lights on" in line else None]))
                continue
            parts = line.split()
            if len(parts) in (4, 5) and NAME_OK.match(parts[0]) \
                    and (len(parts) == 4 or re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d", parts[4])):
                rows.append(tuple(parts))
            elif parts:
                raise SystemExit(f"{path}: a line that is not 'shot tick commit sha256 [taken]': {line[:80]}")
    return taken, view, [row if len(row) == 5 else row + (taken,) for row in rows]


def read_kept(path):
    """The note kept with a scene's pictures: {shot: (tick, commit, sha, taken[, distances])}, in the
    file's order. Pictures taken before 11-16 carry no distances."""
    kept = {}
    try:
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                parts = line.split()
                if len(parts) in (5, 6) and not line.startswith("#"):
                    kept[parts[0]] = tuple(parts[1:])
    except OSError:
        pass
    return kept


def take(source, tag, scene, kept_in=None):
    """Put one scene's pictures of one trip into renders/real/<scene>/. Returns (taken?, what to
    say); a scene that cannot be taken whole is left as it was."""
    stem = f"{scene}-{tag}-"
    note = os.path.join(source, stem + "real.txt")
    if not os.path.exists(note):
        return False, [f"{scene}: no note {stem}real.txt in {source} (not sent yet, or another tag)"]
    taken, view, rows = read_sent(note)
    if not rows:
        return False, [f"{scene}: the note names no picture"]
    wrong = []
    for shot, _, _, sha, _ in rows:
        path = os.path.join(source, f"{stem}{shot}.jpg")
        if not os.path.exists(path):
            wrong.append(f"{shot}.jpg has not arrived")
        elif digest(path) != sha:
            wrong.append(f"{shot}.jpg is not the file that was sent")
    if wrong:
        return False, [f"{scene}: nothing taken: " + "; ".join(wrong)]
    folder = os.path.join(kept_in or KEPT, scene)
    os.makedirs(folder, exist_ok=True)
    kept = read_kept(os.path.join(folder, NOTE))
    new, same = [], 0
    for shot, tick, commit, sha, when in rows:
        if kept.get(shot, ("", "", ""))[2] == sha and os.path.exists(os.path.join(folder, shot + ".jpg")):
            same += 1           # the very picture that is kept: its line stays as it is
            continue
        shutil.copyfile(os.path.join(source, f"{stem}{shot}.jpg"), os.path.join(folder, shot + ".jpg"))
        new.append(shot)
        kept[shot] = (tick, commit, sha, when) + ((view,) if view else ())
    with open(os.path.join(folder, NOTE), "w", encoding="utf-8", newline="\n") as fh:
        fh.write(HEAD + "\n" + "".join(f"{shot} {' '.join(row)}\n" for shot, row in kept.items()))
    commits = sorted({row[2] for row in rows})
    said = [f"{scene}: {len(rows)} pictures of {', '.join(commits)} in {os.path.relpath(folder, PROJECT)}/"
            + (f" ({len(new)} new or changed, {same} as they were)" if same else "")]
    return True, said


def listing(scenes, kept_in=None):
    where = kept_in or KEPT
    # folders that begin with "_" are not scenes (_trips holds the logs of the node's trips)
    found = sorted(d for d in os.listdir(where) if not d.startswith("_") and os.path.isdir(os.path.join(where, d))) \
        if os.path.isdir(where) else []
    for scene in scenes or found:
        kept = read_kept(os.path.join(where, scene, NOTE))
        if not kept:
            print(f"{scene}: nothing kept")
            continue
        by_commit = {}
        for shot, row in kept.items():
            by_commit.setdefault((row[1], row[3], row[4] if len(row) > 4 else "distances not noted"), []).append(shot)
        print(f"{scene}: {len(kept)} pictures")
        for (commit, taken, view), shots in by_commit.items():
            print(f"    {commit}, taken {taken}, {view}: {', '.join(shots)}")


def sheet(name, picked, across, title, kept_in=None):
    """renders/real/_sheets/<name>.jpg of the kept pictures picked as <scene>:<shot>."""
    import boardrender
    where = kept_in or KEPT
    pictures, commits = [], []
    for pick in picked:
        scene, _, shot = pick.partition(":")
        row = read_kept(os.path.join(where, scene, NOTE)).get(shot)
        path = os.path.join(where, scene, shot + ".jpg")
        if not row or not os.path.exists(path):
            raise SystemExit(f"{pick}: no such picture is kept in {os.path.relpath(os.path.join(where, scene), PROJECT)}/")
        pictures.append((f"{scene}  {shot}  {row[0]}  {row[1]}", path))
        commits += [row[1]] if row[1] not in commits else []
    out = os.path.join(where, "_sheets", name + ".jpg")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    boardrender.cells(pictures, title or f"c164 real-machine pictures (the game 26.3), the code of {', '.join(commits)}",
                      out, across)
    print(f"{os.path.relpath(out, PROJECT)}: {len(pictures)} pictures, {across} across")


def columns(name, shots, picked, title):
    """renders/real/_sheets/<name>.jpg: the shots named, one row each, as several folders keep them,
    one column each. `picked` is ['<label>=<folder from renders/>', ...]."""
    import boardrender
    renders = os.path.join(PROJECT, "renders")
    folders = []
    for pick in picked:
        label, _, rel = pick.partition("=")
        folder = os.path.normpath(os.path.join(renders, rel))
        if not label or not rel or not folder.startswith(renders + os.sep) or not os.path.isdir(folder):
            raise SystemExit(f"{pick}: <label>=<folder>, a folder of kept pictures given from renders/")
        folders.append((label, folder, read_kept(os.path.join(folder, NOTE))))
    pictures = []
    for shot in shots:
        for label, folder, kept in folders:
            path = next((p for p in (os.path.join(folder, shot + ext) for ext in (".jpg", ".png")) if os.path.exists(p)), None)
            if path is None:
                raise SystemExit(f"{shot}: no such picture in {os.path.relpath(folder, PROJECT)}/")
            row = kept.get(shot)
            pictures.append((f"{shot}  {label}" + (f"  {row[1]}" + (f"  {row[4]}" if len(row) > 4 else "") if row else ""), path))
    out = os.path.join(KEPT, "_sheets", name + ".jpg")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    boardrender.cells(pictures, title or "c164, the same views side by side: " + ", ".join(label for label, _, _ in folders),
                      out, across=len(folders), size=(960, 540) if len(folders) <= 2 else (640, 360))
    print(f"{os.path.relpath(out, PROJECT)}: {len(shots)} views in {len(folders)} columns")


def main():
    ap = argparse.ArgumentParser(description="real-machine pictures into renders/real/")
    ap.add_argument("scenes", nargs="*")
    ap.add_argument("--take", metavar="TAG")
    ap.add_argument("--from", dest="source", default=os.path.join(ROOT, "inbox"), metavar="FOLDER")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--sheet", metavar="NAME")
    ap.add_argument("--columns", metavar="NAME")
    ap.add_argument("--shots", metavar="A,B", help="with --columns: the shots, one row each")
    ap.add_argument("--across", type=int, default=2)
    ap.add_argument("--title")
    ap.add_argument("--into", metavar="FOLDER", help="keep them in this folder of the checkout instead of renders/real")
    args = ap.parse_args()
    kept_in = os.path.join(PROJECT, args.into) if args.into else None
    if args.list:
        listing(args.scenes, kept_in)
        return 0
    if args.sheet:
        if not NAME_OK.match(args.sheet) or not args.scenes or args.across < 1:
            ap.error("--sheet <name> <scene>:<shot> ...: a name of letters, digits, - and _, and the pictures")
        sheet(args.sheet, args.scenes, args.across, args.title, kept_in)
        return 0
    if args.columns:
        shots = [name for name in (args.shots or "").split(",") if name]
        if not NAME_OK.match(args.columns) or not shots or len(args.scenes) < 2:
            ap.error("--columns <name> --shots <a,b,...> <label>=<folder> <label>=<folder> ...: a name of letters, "
                     "digits, - and _, the shots, and two folders or more")
        columns(args.columns, shots, args.scenes, args.title)
        return 0
    if not args.take:
        ap.error("--take <tag>, --list, --sheet <name> or --columns <name>")
    scenes = args.scenes
    if not scenes:
        tail = f"-{args.take}-real.txt"
        scenes = sorted(os.path.basename(p)[:-len(tail)] for p in glob.glob(os.path.join(args.source, "*" + tail)))
        if not scenes:
            print(f"no note *{tail} in {args.source}")
            return 1
    failed = 0
    for scene in scenes:
        ok, said = take(args.source, args.take, scene, kept_in)
        failed += not ok
        print("\n".join(said))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
