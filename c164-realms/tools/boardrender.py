#!/usr/bin/env python3
"""The twelve board views of the master scene, drawn offline and kept in the repository.

    boardrender.py                    all twelve, into renders/board/<assembly commit, 7 digits>/
    boardrender.py --at <commit>      named after this commit of the assembly branch instead of its
                                      head: the one the merge post announced, when commits that
                                      leave build/ alone (the roster) have been pushed on top
    boardrender.py --only v01_arrival,v07_hall
    boardrender.py --tag <name>       into renders/board/<name>/ (a checkout that is not the assembly's)

On the render station's node (plan/roles/COMMON.md 2.2), after a push:

    bash c164-realms/tools/nodejob.sh python tools/boardrender.py

The views are tools/boardshots.py's, worked out from the skeleton of this checkout; the pictures
are build/render.py's (1280x720, look A unless a view says otherwise). The folder is named after
the assembly commit whose build/ this checkout carries: the checkout's build/ has to be, file for
file, that of the assembly branch's head as the last fetch left it (or of the commit named with
--at, which has to be on that branch), and committed. Then a picture shows what the assembly
holds, whatever branch the tool ran on. A checkout whose build/ is something else is drawn only
with --tag, and the note says which commit it was.

What lands in the folder:
    <view>.png      the twelve pictures
    board.json      the shot list they were taken with (tools/shoot.py reads the same file)
    shots.txt       for every view its tick, the commit of the code it shows and the first 16
                    digits of the picture file's SHA-256 (the note tools/selfshots.py writes)
    sheet.jpg       all twelve on one sheet, four across, each with its name
and, when the real-machine pictures of the same commit are kept already (renders/real/obs/, a
trip of tools/nodetrip.py), renders/real/obs/compare.jpg: every view as drawn here beside the
game's picture of it. A trip that comes after the offline board draws that sheet itself.

With --only the pictures named are drawn again and the others, the note's lines for them and the
sheet's cells stay what they were.
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
import time

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(HERE)
BUILD = os.path.join(PROJECT, "build")
ASSEMBLY = "origin/cursor/c164-assembly-fable-a9f5"
SCENE = "obs"
SIZE = "1280x720"
NOTE = "shots.txt"
HEAD = ("# shot, tick, commit of the code the picture shows, first 16 of the picture file's sha256 "
        "(tools/boardrender.py; drawn offline, {size})")
CELL = (640, 360)
ACROSS = 4

sys.path.insert(0, HERE)
import boardshots  # noqa: E402


def git(*args):
    got = subprocess.run(("git", "-C", PROJECT) + args, capture_output=True, text=True)
    return got.stdout.strip() if got.returncode == 0 else None


def digest(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()[:16]


def which_commit(tag, at=None):
    """(folder name, commit the pictures show). Without --tag the checkout's build/ must be that of
    the assembly's head, or of the assembly commit named with `at`."""
    head = git("rev-parse", "--short=8", "HEAD")
    if not head:
        sys.exit(f"{PROJECT}: not a git checkout, so the pictures could not say what they show")
    dirty = git("status", "--porcelain", "--", "build")
    if dirty:
        sys.exit("build/ has changes that are not committed (" + ", ".join(line[3:] for line in dirty.splitlines()[:4])
                 + "): commit them, the pictures are named after a commit")
    if tag:
        return tag, head
    assembly = git("rev-parse", "--short=8", ASSEMBLY)
    if not assembly:
        sys.exit(f"{ASSEMBLY} is not here: git fetch origin {ASSEMBLY.split('/', 1)[1]} (tools/cloud_setup.sh does), "
                 f"or name the folder yourself with --tag")
    what = "head"
    if at:
        named = git("rev-parse", "--short=8", "--verify", "--quiet", at + "^{commit}")
        if not named:
            sys.exit(f"--at {at}: no such commit here")
        if git("merge-base", "--is-ancestor", named, ASSEMBLY) is None:
            sys.exit(f"--at {named} is not a commit of the assembly branch (its head is {assembly})")
        assembly, what = named, "commit"
    ours, theirs = git("rev-parse", "HEAD:c164-realms/build"), git("rev-parse", f"{assembly}:c164-realms/build")
    if not ours or ours != theirs:
        sys.exit(f"build/ of this checkout ({head}) is not build/ of the assembly {what} ({assembly}): merge the "
                 f"assembly, or draw this checkout as it is with --tag <name>")
    return assembly[:7], assembly


def draw(shots_file, only, out):
    """build/render.py into the folder `out`; {view: (picture file, tick, seconds)}."""
    prefix = os.path.join(out, "s")
    cmd = [sys.executable, "-u", os.path.join(BUILD, "render.py"), SCENE, "--shots", shots_file, "--out", prefix,
           "--size", SIZE]
    if only:
        cmd += ["--only", ",".join(only)]
    made = {}
    p = subprocess.Popen(cmd, cwd=BUILD, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                         encoding="utf-8", errors="replace")
    said = []
    for line in p.stdout:
        line = line.rstrip("\n")
        said.append(line)
        m = re.match(re.escape(prefix) + r"-(.+)\.png \(tick (-?\d+), (\d+) s\)$", line)
        if m:
            made[m.group(1)] = (f"{prefix}-{m.group(1)}.png", m.group(2), int(m.group(3)))
            line = f"{m.group(1)}.png (tick {m.group(2)}, {m.group(3)} s)"
        print(f"  {line}", flush=True)
    if p.wait() != 0:
        sys.exit("build/render.py failed\n" + "\n".join(said[-15:]))
    return made


def read_note(path):
    """{view: (tick, commit, digest)} of a note this tool wrote; {} without one."""
    out = {}
    try:
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                parts = line.rstrip("\n").split("\t")
                if len(parts) == 4 and not line.startswith("#"):
                    out[parts[0]] = tuple(parts[1:])
    except OSError:
        pass
    return out


def _font():
    try:
        return ImageFont.load_default(size=20)      # Pillow's own outline font
    except (TypeError, OSError):
        return ImageFont.load_default()


def _cell(img, pen, font, at, path, label, size=CELL):
    if os.path.exists(path):
        with Image.open(path) as picture:
            img.paste(picture.convert("RGB").resize(size, Image.LANCZOS), at)
    box = pen.textbbox((at[0] + 5, at[1] + 2), label, font=font)
    pen.rectangle((at[0], at[1], box[2] + 5, box[3] + 4), fill=(0, 0, 0))
    pen.text((at[0] + 5, at[1] + 2), label, fill=(255, 255, 255), font=font)


def sheet(folder, names, title, ext=".png", out="sheet.jpg"):
    """All the views on one sheet, in the order given; a view without a picture leaves its cell dark."""
    rows = -(-len(names) // ACROSS)
    font = _font()
    band = 34
    img = Image.new("RGB", (CELL[0] * ACROSS, band + CELL[1] * rows), (16, 16, 20))
    pen = ImageDraw.Draw(img)
    pen.text((8, 5), title, fill=(230, 230, 230), font=font)
    for i, name in enumerate(names):
        at = (i % ACROSS * CELL[0], band + i // ACROSS * CELL[1])
        _cell(img, pen, font, at, os.path.join(folder, name + ext), name)
    img.save(os.path.join(folder, out), "JPEG", quality=88)


def side_by_side(left, right, names, title, out, exts=(".png", ".jpg"), labels=("offline", "game")):
    """Every view twice, the picture from `left` beside the one from `right`, two views a row."""
    rows = -(-len(names) // 2)
    font = _font()
    band = 34
    img = Image.new("RGB", (CELL[0] * 4, band + CELL[1] * rows), (16, 16, 20))
    pen = ImageDraw.Draw(img)
    pen.text((8, 5), title, fill=(230, 230, 230), font=font)
    for i, name in enumerate(names):
        x, y = i % 2 * 2 * CELL[0], band + i // 2 * CELL[1]
        _cell(img, pen, font, (x, y), os.path.join(left, name + exts[0]), f"{name}  {labels[0]}")
        _cell(img, pen, font, (x + CELL[0], y), os.path.join(right, name + exts[1]), f"{name}  {labels[1]}")
    img.save(out, "JPEG", quality=88)


def beside_game(tag, real=None, drawn=None, stale_goes=False):
    """compare.jpg of the master scene's real-machine pictures: every board view as it is drawn
    offline (renders/board/<tag>/) beside the game's picture of it. The two sets come from
    different machines at different times, so whichever arrives second draws the sheet: this tool
    after an offline board, tools/nodetrip.py after a trip. It is drawn only when both sets show
    the same commit. `stale_goes` is for the trip, whose pictures are new: a sheet it cannot draw
    again is one of an earlier board, and is removed rather than left beside pictures it does not
    show. Returns what happened, in a few words ('' when there is nothing to say)."""
    import realshots
    real = real or os.path.join(realshots.KEPT, SCENE)
    out = os.path.join(real, "compare.jpg")
    board = os.path.join(PROJECT, "renders", "board", tag)
    kept = realshots.read_kept(os.path.join(real, realshots.NOTE))
    names = [shot for shot in kept if os.path.exists(os.path.join(real, shot + ".jpg"))]
    of_game = sorted({kept[shot][1] for shot in names})
    of_board = sorted({row[1] for row in read_note(os.path.join(board, NOTE)).values()})
    if names and of_game == of_board:
        if drawn is None:
            distances = sorted({kept[shot][4] for shot in names if len(kept[shot]) > 4})
            drawn = "the game 26.3 on a node" + (f" ({', '.join(distances)})" if distances else "")
        side_by_side(board, real, names, f"c164 board of {', '.join(of_game)}: offline (build/render.py) beside {drawn}", out)
        return f"compare.jpg (beside renders/board/{tag}/)"
    if stale_goes and os.path.exists(out):
        os.remove(out)
        return (f"no compare.jpg (renders/board/{tag}/ " + ("is not drawn yet" if not of_board else
                f"shows {', '.join(of_board)}, the game's pictures {', '.join(of_game) or 'nothing'}")
                + "; the sheet of an earlier board is removed)")
    return ""


def cells(pictures, title, out, across=2, size=(960, 540)):
    """Pictures picked by hand on one sheet, in the order given: `pictures` is [(label, file)]."""
    font = _font()
    band = 34
    rows = -(-len(pictures) // across)
    img = Image.new("RGB", (size[0] * across, band + size[1] * rows), (16, 16, 20))
    pen = ImageDraw.Draw(img)
    pen.text((8, 5), title, fill=(230, 230, 230), font=font)
    for i, (label, path) in enumerate(pictures):
        _cell(img, pen, font, (i % across * size[0], band + i // across * size[1]), path, label, size)
    img.save(out, "JPEG", quality=88)


def in_columns(columns, names, title, out, ext=".jpg", size=(960, 540)):
    """One row a view, one column a folder: `columns` is [(label, folder)]. The same views under
    several light versions, to be told apart at a glance."""
    font = _font()
    band = 34
    img = Image.new("RGB", (size[0] * len(columns), band + size[1] * len(names)), (16, 16, 20))
    pen = ImageDraw.Draw(img)
    pen.text((8, 5), title, fill=(230, 230, 230), font=font)
    for row, name in enumerate(names):
        for col, (label, folder) in enumerate(columns):
            _cell(img, pen, font, (col * size[0], band + row * size[1]), os.path.join(folder, name + ext),
                  f"{name}  {label}", size)
    img.save(out, "JPEG", quality=88)


def main():
    ap = argparse.ArgumentParser(description="the twelve board views of the master scene, drawn offline")
    ap.add_argument("--only", help="comma separated views")
    ap.add_argument("--tag", help="name of the folder under renders/board/ (default: the assembly commit)")
    ap.add_argument("--at", metavar="COMMIT", help="the assembly commit the pictures are named after (default: its head)")
    args = ap.parse_args()
    if args.tag and args.at:
        sys.exit("--tag names the folder of a checkout that is not the assembly's; --at names an assembly commit: one of the two")
    t0 = time.time()
    views = [shot for shot, _, _ in boardshots.views()]
    names = [v["name"] for v in views]
    only = args.only.split(",") if args.only else []
    unknown = [n for n in only if n not in names]
    if unknown:
        sys.exit("not a board view: " + ", ".join(unknown))
    tag, commit = which_commit(args.tag, args.at)
    folder = os.path.join(PROJECT, "renders", "board", tag)
    os.makedirs(folder, exist_ok=True)
    board = os.path.join(folder, "board.json")
    with open(board, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(boardshots.text())
    print(f"board of {commit} into renders/board/{tag}/: {len(only or names)} of {len(names)} views", flush=True)

    note_path = os.path.join(folder, NOTE)
    note = read_note(note_path) if only else {}
    tmp = tempfile.mkdtemp(prefix="c164-board-")
    try:
        made = draw(board, only, tmp)
        missing = [n for n in (only or names) if n not in made]
        if missing:
            sys.exit("build/render.py drew no picture of " + ", ".join(missing))
        total, slow = 0, []
        for name in only or names:
            path, tick, secs = made[name]
            target = os.path.join(folder, name + ".png")
            with Image.open(path) as picture:
                picture.save(target, optimize=True)
            total += os.path.getsize(target)
            note[name] = (tick, commit, digest(target))
            slow.append((secs, name))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    with open(note_path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(HEAD.format(size=SIZE) + "\n")
        for name in names:
            if name in note:
                fh.write("\t".join((name,) + tuple(note[name])) + "\n")
    drawn = sorted({note[n][1] for n in names if n in note})
    sheet(folder, names, f"c164 board, offline (build/render.py), the code of {', '.join(drawn)}, {SIZE}, look A")
    slow.sort(reverse=True)
    print(f"renders/board/{tag}/: {len(only or names)} pictures of {commit}, {total / 1048576:.1f} MB, "
          f"{time.time() - t0:.0f} s in all; slowest " + ", ".join(f"{n} {s} s" for s, n in slow[:3]))
    absent = [n for n in names if not os.path.exists(os.path.join(folder, n + ".png"))]
    if absent:
        print("still without a picture: " + ", ".join(absent))
    try:
        said = beside_game(tag)
    except Exception as exc:            # the board is drawn and kept; this sheet is a convenience
        said = f"compare.jpg could not be drawn ({exc})"
    if said:
        print(f"renders/real/{SCENE}/: {said}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
