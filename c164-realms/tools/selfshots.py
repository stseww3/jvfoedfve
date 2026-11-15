#!/usr/bin/env python3
"""A scene's own pictures, drawn offline and kept in the repository (plan/roles/INTERFACE.md 5, 6).

Pictures are drawn on the admin's computer, through bin\\job.py, and never on the cloud machine
(the admin's ruling, 2026-11-14). A round goes:

  on the computer   selfshots.py <scene> [--only a,b] --out @out/shots
                        draws the shots of build/scenes/<scene>/shots.json with build/render.py
                        (1280x720, every shot at its own time) into that folder, as
                        <scene>-<shot>.png beside a note <scene>-shots.txt; bin\\send.py sends them
  on the cloud      selfshots.py <scene> --take [<folder>] [--prefix m2-]
                        puts the pictures that came back (default folder: the inbox) into
                        renders/<scene>/ of this checkout, each checked against the note; commit
                        and push them. Pictures drawn with plain build/render.py (no note; sent
                        as <code>-<commit>-<shot>.png) are taken with --prefix <code>-<commit>-
  on the computer   selfshots.py <scene> [<scene> ...] --verify [--only a,b]
                        draws again and compares pixel by pixel: are the kept pictures what the
                        code draws? The merge-key holder runs it on the delivered commit.

Without --out the pictures go straight into renders/<scene>/ of the checkout the tool runs in.

The note (renders/<scene>/shots.txt) says for every shot its tick, the commit whose code the picture
shows and the first 16 digits of the picture file's SHA-256, so that a picture changed or replaced
after it was drawn shows without drawing anything (tools/delivery.py reads it). A picture is
overwritten under its shot's name; a picture this tool drew whose shot has left the list is removed;
other pictures in the folder (a comparison sheet) are left alone. Drawing wants the code committed:
the copy bin\\sync.py makes always is; elsewhere --dirty draws anyway and notes the commit with a +.

--verify writes nothing. It ends with 1 when a kept picture is not what the code draws; a shot
without a picture and a picture left over are warnings. --project <dir> works on another checkout's
c164-realms, with that checkout's code.
"""
import argparse
import hashlib
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
HEAD = ("# shot, tick, commit of the code the picture shows, first 16 of the picture file's sha256 "
        "(tools/selfshots.py; drawn offline, {size})")
OURS = "# shot, tick, commit"
NAME_OK = re.compile(r"[A-Za-z0-9_.\-]+\Z")
ROOT = os.environ.get("MC_ROOT", "/agent/realms-study")
_GIT = []


def git_program():
    """git on the path, or the portable one of the shared workspace on the admin's computer."""
    if not _GIT:
        found = shutil.which("git")
        if not found:
            portable = os.path.join(ROOT, "git", "cmd", "git.exe")
            found = portable if os.path.exists(portable) else None
        _GIT.append(found)
    return _GIT[0]


def git(project, *args):
    """The command's output; None when it fails or there is no git."""
    program = git_program()
    if not program:
        return None
    got = subprocess.run((program, "-C", project) + args, capture_output=True, text=True, encoding="utf-8",
                         errors="replace")
    return got.stdout if got.returncode == 0 else None


def head_of(project):
    """Eight digits of the commit the checkout stands on; None where that cannot be told."""
    out = (git(project, "rev-parse", "--short=8", "HEAD") or "").strip()
    if out:
        return out
    d = project
    while not os.path.exists(os.path.join(d, ".git")):      # without git: a detached HEAD names the commit
        up = os.path.dirname(d)
        if up == d:
            return None
        d = up
    try:
        with open(os.path.join(d, ".git", "HEAD")) as fh:
            head = fh.read().strip()
    except OSError:
        return None
    return head[:8] if re.fullmatch(r"[0-9a-f]{40}", head) else None


def digest(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()[:16]


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
    """Runs the checkout's build/render.py into the folder `out`, passing on what it says as it goes.
    Returns {shot: (picture file, tick)}."""
    prefix = os.path.join(out, "s")
    cmd = [sys.executable, os.path.join(project, "build", "render.py"), scene, "--shots", shots,
           "--out", prefix, "--size", SIZE]
    if only:
        cmd += ["--only", ",".join(only)]
    if jar:
        cmd += ["--jar", jar]
    made, said = {}, []
    p = subprocess.Popen(cmd, cwd=project, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                         encoding="utf-8", errors="replace")
    for line in p.stdout:
        line = line.rstrip("\n")
        said.append(line)
        cut = line.rfind(".png (tick ")
        if line.startswith(prefix + "-") and cut > 0:
            tick = re.match(r"-?\d+", line[cut + len(".png (tick "):])
            name = line[len(prefix) + 1:cut]
            made[name] = (line[:cut + 4], tick.group(0) if tick else "?")
            line = f"{name}{line[cut + 4:]}"
        print(f"  {scene}: {line}", file=sys.stderr, flush=True)
    if p.wait() != 0:
        sys.exit(f"{scene}: build/render.py failed\n" + "\n".join(said[-12:]))
    return made


def read_note(path, ours=False):
    """{shot: (tick, commit, digest or None)} of a note; None without one. With `ours`, a note this
    tool did not write (and would overwrite) ends the run."""
    if not os.path.exists(path):
        return None
    out = {}
    with open(path, encoding="utf-8") as fh:
        lines = fh.read().split("\n")
    if ours and lines and not lines[0].startswith(OURS):
        sys.exit(f"{path} was not written by this tool, which would overwrite it. "
                 f"Move what it says to another file (notes.txt) and draw again.")
    for line in lines:
        parts = line.split("\t")
        if len(parts) in (3, 4) and not line.startswith("#"):
            out[parts[0]] = (parts[1], parts[2], parts[3] if len(parts) == 4 else None)
    return out


def write_note(path, names, note):
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(HEAD.format(size=SIZE) + "\n")
        for name in names:
            if name in note:
                fh.write("\t".join(v for v in (name,) + tuple(note[name]) if v is not None) + "\n")


def clear_left_over(folder, names, note):
    """Only what this tool drew is removed: a picture the note lists whose shot has left the list.
    Other pictures in the folder (a comparison sheet of the author's) are not its business."""
    gone = []
    for name in sorted(n for n in note if n not in names):
        path = os.path.join(folder, name + ".png")
        if os.path.exists(path):
            os.remove(path)
            gone.append(name + ".png")
    return gone


def write(project, scene, only, dirty, jar, out):
    shots, names = shot_list(project, scene)
    unknown = [n for n in only if n not in names]
    if unknown:
        sys.exit(f"{scene}: not in the shot list: {', '.join(unknown)}")
    commit = head_of(project)
    if not commit:
        sys.exit(f"{project}: which commit this copy stands on cannot be told (no git checkout), so the "
                 f"pictures could not say what they show")
    status = git(project, "status", "--porcelain", "--", "build")
    changed = (status or "").splitlines()
    if changed and not dirty:
        shown = ", ".join(c[3:] for c in changed[:4]) + (f" and {len(changed) - 4} more" if len(changed) > 4 else "")
        sys.exit(f"{scene}: the code is not committed ({shown}), so no commit shows what the pictures would show.\n"
                 f"Commit it and draw again; --dirty draws anyway and notes the commit with a +.")
    if out:
        folder, stem, note_path, note = out, scene + "-", os.path.join(out, f"{scene}-{NOTE}"), {}
    else:
        folder, stem = os.path.join(project, "renders", scene), ""
        note_path = os.path.join(folder, NOTE)
        note = read_note(note_path, ours=True) or {}
    tmp = tempfile.mkdtemp(prefix="c164-selfshots-")
    try:
        made = draw(project, scene, shots, only, tmp, jar)
        wanted = only or names
        missing = [n for n in wanted if n not in made]
        if missing:
            sys.exit(f"{scene}: build/render.py drew no picture of {', '.join(missing)}")
        os.makedirs(folder, exist_ok=True)
        total = 0
        for name in wanted:
            path, tick = made[name]
            target = os.path.join(folder, stem + name + ".png")
            Image.open(path).save(target, optimize=True)
            total += os.path.getsize(target)
            note[name] = (tick, commit + ("+" if changed else ""), digest(target))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    gone = clear_left_over(folder, names, note) if not only and not out else []
    write_note(note_path, names, note)
    where = f"{folder}{os.sep}{scene}-*" if out else f"renders/{scene}/"
    print(f"{where}: {len(wanted)} picture{'s' if len(wanted) != 1 else ''} of {commit}"
          f"{'+ (uncommitted code)' if changed else ''} drawn, {total / 1048576:.1f} MB"
          + ("" if status is not None else " (no git here: uncommitted changes were not looked for)")
          + (f"; removed (no such shot any more): {', '.join(gone)}" if gone else ""))
    if out:
        print(f"                next: send {scene}-* from that folder (bin\\send.py), then on the cloud "
              f"tools/selfshots.py {scene} --take")
    else:
        absent = [n for n in names if not os.path.exists(os.path.join(folder, n + ".png"))]
        if absent:
            print(f"                still without a picture: {', '.join(absent)}")
    return True


def whole_picture(path):
    """None for a complete PNG of the size the tool draws, else what is wrong with the file."""
    try:
        with Image.open(path) as img:
            if img.format != "PNG" or f"{img.size[0]}x{img.size[1]}" != SIZE:
                return f"not a {SIZE} PNG"
            img.load()
    except (OSError, ValueError, SyntaxError):
        return "not a whole picture (cut short on the way?): send it again"
    return None


def same_picture(a, b):
    """Do two picture files hold the same pixels? (The same picture written on two machines is not
    the same file byte for byte.)"""
    try:
        with Image.open(a) as x, Image.open(b) as y:
            return x.size == y.size and np.array_equal(np.asarray(x.convert("RGBA")), np.asarray(y.convert("RGBA")))
    except (OSError, ValueError, SyntaxError):
        return False


def ticks_of(project, scene, jar):
    """{shot: tick as build/render.py takes it}, read off the shot list; "?" where a named time
    cannot be looked up (no client jar here)."""
    with open(os.path.join(project, "build", "scenes", scene, "shots.json"), encoding="utf-8") as fh:
        shots = json.load(fh)
    default = "14000"
    try:
        with open(os.path.join(project, "build", "render.py"), encoding="utf-8") as fh:
            m = re.search(r"^DEFAULT_TIME = (\d+)", fh.read(), re.M)
            default = m.group(1) if m else default
    except OSError:
        pass
    markers = None
    out = {}
    for shot in shots:
        when = str(shot.get("time", default))
        if not when.lstrip("-").isdigit():
            if markers is None:
                markers = {}
                try:
                    import zipfile
                    with zipfile.ZipFile(jar or os.path.join(ROOT, "client26", "versions", "26.3", "26.3.jar")) as z:
                        markers = json.loads(z.read("data/minecraft/timeline/day.json")).get("time_markers", {})
                except (OSError, KeyError, ValueError):
                    pass
            mark = markers.get(f"minecraft:{when}")
            when = "?" if mark is None else str(mark["ticks"] if isinstance(mark, dict) else mark)
        out[shot["name"]] = str(int(when)) if when != "?" else when
    return out


def arrivals(project, scene, source, prefix, names):
    """What has arrived of the scene: (prefix, stem of the picture files, {shot: (tick, commit,
    digest or None)}, drawn by this tool?). Pictures drawn with --out come with their note;
    pictures drawn with plain build/render.py (--out @out/rt/<commit>) come as
    <prefix><shot>.png, and the commit is what the prefix ends with."""
    tail = f"{scene}-{NOTE}"
    if prefix is None:
        found = sorted(f for f in (os.listdir(source) if os.path.isdir(source) else [])
                       if f == tail or f.endswith("-" + tail))
        if not found:
            sys.exit(f"{scene}: no {tail} in {source}: nothing drawn with --out has arrived of this scene.\n"
                     f"Pictures drawn with plain build/render.py are taken with --prefix <code>-<commit>-")
        if len(found) > 1:
            shown = ", ".join(repr(f[:-len(tail)]) for f in found)
            sys.exit(f"{scene}: notes of this scene from several senders are in {source}; say whose with "
                     f"--prefix: {shown}")
        prefix = found[0][:-len(tail)]
    note_path = os.path.join(source, prefix + tail)
    if os.path.exists(note_path):
        arrived = read_note(note_path, ours=True)
        if not arrived:
            sys.exit(f"{scene}: {note_path} lists no picture")
        return prefix, f"{prefix}{scene}-", arrived, True
    there = [n for n in names if os.path.exists(os.path.join(source, f"{prefix}{n}.png"))]
    if not there:
        sys.exit(f"{scene}: neither {prefix}{tail} nor a picture {prefix}<shot>.png of this scene's shots is in {source}")
    m = re.search(r"(?:^|[-_])([0-9a-f]{7,40})[-_]$", prefix)
    commit = (git(project, "rev-parse", "--short=8", "--verify", m.group(1) + "^{commit}") or "").strip() if m else ""
    if not commit:
        sys.exit(f"{scene}: pictures without a note are taken by the commit their names carry "
                 f"(<code>-<commit>-<shot>.png), and {prefix!r} "
                 + ("names none" if not m else f"names {m.group(1)}, which this checkout does not have"))
    ticks = ticks_of(project, scene, None)
    return prefix, prefix, {n: (ticks.get(n, "?"), commit, None) for n in there}, False


def take(project, scene, source, prefix):
    """Pictures drawn on the admin's computer, as they arrived in the folder `source`, into this
    checkout's renders/<scene>/. Nothing is copied unless every picture named is there, whole, and
    (drawn with --out) the very file its note describes."""
    _, names = shot_list(project, scene)
    prefix, stem, arrived, ours = arrivals(project, scene, source, prefix, names)
    problems, commits = [], set()
    for name, (tick, commit, noted) in arrived.items():
        path = os.path.join(source, f"{stem}{name}.png")
        commits.add(commit)
        if name not in names:
            problems.append(f"{name}: not in this checkout's shot list")
        elif ours and noted is None:
            problems.append(f"{name}: the note gives no SHA-256 for it (drawn by an older selfshots.py)")
        elif not os.path.exists(path):
            problems.append(f"{name}: {os.path.basename(path)} has not arrived")
        elif ours and digest(path) != noted:
            problems.append(f"{name}: {os.path.basename(path)} is not the file the note describes "
                            f"(cut short on the way, or of another round): send it again")
        else:
            wrong = whole_picture(path)
            if wrong:
                problems.append(f"{name}: {os.path.basename(path)} is {wrong}")
    for commit in sorted(commits):
        if git(project, "merge-base", "--is-ancestor", commit.rstrip("+"), "HEAD") is None:
            problems.append(f"the pictures show {commit}, which is not in this branch's history: another "
                            f"branch's pictures, or a commit this checkout does not have")
    if problems:
        sys.exit(f"{scene}: nothing taken from {source}\n" + "\n".join(f"                {p}" for p in problems))
    folder = os.path.join(project, "renders", scene)
    note_here = os.path.join(folder, NOTE)
    note = read_note(note_here, ours=True) or {}
    os.makedirs(folder, exist_ok=True)
    total, new, changed = 0, [], []
    for name, (tick, commit, noted) in arrived.items():
        path, target = os.path.join(source, f"{stem}{name}.png"), os.path.join(folder, name + ".png")
        # The same picture as the one kept (drawn again, nothing in it changed): the kept file stays,
        # so the history does not take another copy of it; the note moves on to the new commit.
        if not os.path.exists(target):
            new.append(name)
        elif not same_picture(path, target):
            changed.append(name)
        if name in new or name in changed:
            shutil.copyfile(path, target)
            total += os.path.getsize(target)
        note[name] = (tick, commit, digest(target))
    gone = clear_left_over(folder, names, note)
    write_note(note_here, names, note)
    still = len(arrived) - len(new) - len(changed)
    print(f"renders/{scene}/: {len(arrived)} picture{'s' if len(arrived) != 1 else ''} of "
          f"{', '.join(sorted(commits))} taken from {source} ({stem}*): {len(new)} new, {len(changed)} changed"
          + (f" ({', '.join(changed)})" if changed and still else "")
          + f", {still} the same picture as the one kept (file left as it is); {total / 1048576:.1f} MB written"
          + (f"; removed (no such shot any more): {', '.join(gone)}" if gone else ""))
    if not ours:
        print(f"                drawn with plain build/render.py: that they show {', '.join(sorted(commits))} is "
              f"the file names' word, not the drawing tool's (selfshots.py --out reads it off the copy it draws)")
    for commit in sorted(commits):
        since = (git(project, "diff", "--name-only", commit.rstrip("+"), "HEAD", "--", "build") or "").split()
        if since:
            print(f"                the code under build/ has changed since {commit} "
                  f"({', '.join(os.path.basename(p) for p in since[:4])}{' ...' if len(since) > 4 else ''}): "
                  f"where a picture shows what changed, draw it again")
        if commit.endswith("+"):
            print(f"                {commit}: drawn from uncommitted code")
    absent = [n for n in names if not os.path.exists(os.path.join(folder, n + ".png"))]
    if absent:
        print(f"                still without a picture: {', '.join(absent)}")
    return True


def verify(project, scene, jar, only):
    shots, names = shot_list(project, scene)
    unknown = [n for n in only if n not in names]
    if unknown:
        sys.exit(f"{scene}: not in the shot list: {', '.join(unknown)}")
    looked = only or names
    folder = os.path.join(project, "renders", scene)
    kept = sorted(f[:-4] for f in os.listdir(folder) if f.endswith(".png")) if os.path.isdir(folder) else []
    fails, warns, absent = [], [], []
    tmp = tempfile.mkdtemp(prefix="c164-selfshots-")
    try:
        made = draw(project, scene, shots, only, tmp, jar)
        same = 0
        for name in looked:
            path = os.path.join(folder, name + ".png")
            if name not in made:
                fails.append(f"{name}: build/render.py drew no picture")
            elif not os.path.exists(path):
                absent.append(name)
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
    note = read_note(os.path.join(folder, NOTE))
    if absent:
        warns.append(f"no picture kept of {', '.join(absent)}")
    left = [n for n in kept if n not in names and n in (note or {})]
    if left:
        warns.append(f"left over, the list has no such shot any more: {', '.join(left)}")
    if note is None:
        warns.append(f"no {NOTE}: which commit the pictures show is not noted")
    else:
        unnoted = [n for n in looked if n not in note and n not in absent]
        if unnoted:
            warns.append(f"{NOTE} does not note the commit of " + (f"{', '.join(unnoted)}" if note else
                         f"any shot (not written by this tool)"))
        # a copy made by bin\sync.py holds one commit only: whether an older one is in the branch's
        # history cannot be told there (tools/delivery.py looks at that on the cloud)
        whole = (git(project, "rev-parse", "--is-shallow-repository") or "").strip() == "false"
        for name in looked:
            tick, commit, noted = note.get(name, (None, None, None))
            if commit is None:
                continue
            path = os.path.join(folder, name + ".png")
            if noted and os.path.exists(path) and digest(path) != noted:
                warns.append(f"{name}: the kept file is not the one the note describes (changed after it was drawn)")
            if commit.endswith("+"):
                warns.append(f"{name}: noted as drawn from uncommitted code ({commit})")
            elif whole and git(project, "merge-base", "--is-ancestor", commit, "HEAD") is None:
                warns.append(f"{name}: noted commit {commit} is not in this branch's history")
            elif name in made and tick not in ("?", made[name][1]):
                warns.append(f"{name}: noted at tick {tick}, drawn at {made[name][1]}")
    status = "FAIL" if fails else "WARN" if warns else "PASS"
    print(f"[{status}] selfshots {scene} at {head_of(project) or '?'}: {same} of {len(looked) - len(absent)} kept "
          f"pictures are what the code draws" + (f", {len(fails)} not" if fails else "")
          + (f"; {len(absent)} of {len(looked)} shots have none" if absent else "")
          + (f" (looked at {len(looked)} of the {len(names)} shots)" if only else ""))
    for line in fails + warns:
        print(f"                {line}")
    return not fails


def main():
    ap = argparse.ArgumentParser(description="a scene's own offline pictures, kept in renders/<scene>/")
    ap.add_argument("scenes", nargs="+")
    ap.add_argument("--only", help="comma separated shot names: draw (or verify) only these")
    ap.add_argument("--out", help="draw into this folder as <scene>-<shot>.png with <scene>-shots.txt, to be sent "
                                  "and taken elsewhere, instead of into renders/<scene>/")
    ap.add_argument("--take", nargs="?", const=os.path.join(ROOT, "inbox"), metavar="FOLDER",
                    help="put pictures drawn with --out, as they arrived in the folder (default: the inbox), "
                         "into renders/<scene>/")
    ap.add_argument("--prefix", help="with --take: what the sender put before the file names (bin\\send.py "
                                     "--prefix); found by itself when only one sender's note is there")
    ap.add_argument("--verify", action="store_true", help="compare the kept pictures with what the code draws")
    ap.add_argument("--dirty", action="store_true", help="draw although the code under build/ is not committed")
    ap.add_argument("--project", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."),
                    help="the c164-realms folder of the checkout to work on (default: this one)")
    ap.add_argument("--jar", help="the client jar, where it is not in build/render.py's usual place")
    args = ap.parse_args()
    project = os.path.abspath(args.project)
    only = [n for n in (args.only or "").split(",") if n]
    if args.verify and (args.dirty or args.out or args.take):
        sys.exit("--verify compares the kept pictures with the code as it stands; it takes --only and nothing else")
    if args.take and (only or args.dirty or args.out or args.jar):
        sys.exit("--take copies what the note in the folder lists; it takes --prefix and nothing else")
    if args.prefix is not None and not args.take:
        sys.exit("--prefix goes with --take")
    if only and len(args.scenes) > 1:
        sys.exit("--only names shots of one scene")
    good = True
    for scene in args.scenes:
        if args.take:
            done = take(project, scene, os.path.abspath(args.take), args.prefix)
        elif args.verify:
            done = verify(project, scene, args.jar, only)
        else:
            done = write(project, scene, only, args.dirty, args.jar, os.path.abspath(args.out) if args.out else None)
        good = done and good
    sys.exit(0 if good else 1)


if __name__ == "__main__":
    main()
