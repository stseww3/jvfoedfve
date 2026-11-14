#!/usr/bin/env python3
"""Look at a delivered branch before it is merged: what it touches and whether anything in it
should not be in the repository. The merge-key holder runs it; it only reads (git, no checkout).

    delivery.py <category>/<package> <commit> [--base <commit>]      base: HEAD (the assembly copy)

  scope     the files changed, sorted into: the card's own (its module, the category's _helpers,
            its test scenes and their kept pictures, its card, the parts files), common files (only
            the merge-key holder changes those: agreed beforehand or not?), other cards' files,
            the director's files
  files     no archives, programs, fonts, sounds or world files; nothing binary but pictures and
            the built helper classes (tools/win/helper/*.class: rebuilt here from the source beside
            them and compared byte for byte); pictures in the code tree named; nothing large
  secrets   added lines that look like a token, a key or an address with a password in it
            (the finding is shown shortened, never whole)
  origin    added lines that speak of a copyright, a licence or a site that hands out assets
  commits   commit messages start with "c164-<code>: "
  pictures  every test scene the delivery touches keeps a picture of each of its shots in
            renders/<scene>/ and a note of the commit they show (tools/selfshots.py draws them)
  merge     the branch merges into the base without conflicts; how far it is behind

The technical checks of what the code generates are tools/check.py's; whether the kept pictures
are what the delivered code draws is tools/selfshots.py --verify's (both need a checkout).
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

ROOT = "c164-realms/"
ABBR = {"materials": "mat", "sky": "sky", "main": "main", "site": "site", "machines": "mach",
        "props": "props", "interiors": "int", "motion": "mot", "common": "common"}
COMMON = ("build/artkit/", "tools/", "build/scenes/obs/common/", "build/scenes/obs/__init__.py",
          "build/scenes/obs/mood.py", "plan/STATUS.md", "plan/roles/INTERFACE.md")
DIRECTOR = ("plan/ART-PLAN.md", "plan/PIPELINE.md", "plan/roles/", "plan/reviews/")
BANNED = (".zip", ".jar", ".exe", ".dll", ".so", ".ttf", ".otf", ".woff", ".woff2", ".schem", ".schematic",
          ".litematic", ".mca", ".mcworld", ".mcpack", ".7z", ".rar", ".gz", ".tar", ".pyc", ".dat")
PICTURES = (".png", ".jpg", ".jpeg", ".gif", ".webp")
MAGIC = {".png": (b"\x89PNG\r\n\x1a\n",), ".jpg": (b"\xff\xd8\xff",), ".jpeg": (b"\xff\xd8\xff",),
         ".gif": (b"GIF87a", b"GIF89a"), ".webp": (b"RIFF",)}
SOUNDS = (".ogg", ".wav", ".mp3", ".flac")
# The one kind of binary that is not a picture (A0, 2026-11-14): a class of our own that the Windows
# workspace cannot build (its Java has no compiler), kept beside its source tools/win/<Name>.java and
# a note of that source's SHA-1, tools/win/helper/<Name>.sha1.
BUILT = re.compile(r"tools/win/helper/([A-Za-z0-9_]+)(\$[A-Za-z0-9_$]+)?\.class")
JAVAC = ("--release", "21", "-encoding", "UTF-8")      # as tools/win/build_helper.py builds it
LARGE, HUGE = 1 << 20, 5 << 20

SECRETS = [
    ("a GitHub token", re.compile(r"gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,}")),
    ("a Slack token", re.compile(r"xox[abprs]-[A-Za-z0-9-]{10,}")),
    ("an AWS key", re.compile(r"AKIA[0-9A-Z]{16}")),
    ("a private key", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("an address with a password", re.compile(r"[a-z][a-z0-9+.-]*://[^/\s:@'\"<>{}]+:[^/\s:@'\"<>{}]+@")),
    ("a bot token", re.compile(r"\b\d{8,10}:[A-Za-z0-9_-]{35}\b")),
    ("a literal password or key", re.compile(
        r"(?i)\b(password|passwd|secret|token|api[_-]?key)\b\s*[:=]\s*['\"][^'\"\s]{8,}['\"]")),
]
ORIGIN = re.compile(r"(?i)copyright|all rights reserved|licen[cs]ed under|creative ?commons|\bCC[- ]BY\b|"
                    r"planetminecraft|curseforge|modrinth|textures\.com|freesound|opengameart|sketchfab|"
                    r"vanillatweaks|faithful|optifine")
MESSAGE = re.compile(r"^c164(-[a-z0-9]+)?: ")


def git(*args, check=True):
    got = subprocess.run(("git",) + args, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if check and got.returncode != 0:
        sys.exit(f"git {' '.join(args[:3])} ... failed: {got.stderr.strip()[:300]}")
    return got


def blob(tree, path):
    got = subprocess.run(("git", "cat-file", "blob", f"{tree}:{path}"), capture_output=True)
    return got.stdout if got.returncode == 0 else None


def is_binary(data):
    if b"\0" in data[:8192]:
        return True
    try:
        data.decode("utf-8")
    except UnicodeDecodeError:
        return True
    return False


def built_class(tree, rel, data, cache):
    """Is the class file `rel` (a path of the project) what its source builds? Returns (fails, warns)."""
    name, folder = BUILT.fullmatch(rel).group(1), ROOT + "tools/win/"
    source = blob(tree, f"{folder}{name}.java")
    note = blob(tree, f"{folder}helper/{name}.sha1")
    if source is None:
        return [f"{rel}: a built class without its source tools/win/{name}.java beside it"], []
    mark = hashlib.sha1(source.replace(b"\r\n", b"\n")).hexdigest()
    if note is None or note.decode("ascii", "replace").strip() != mark:
        return [f"{rel}: the note tools/win/helper/{name}.sha1 does not name the present source ({mark[:12]})"], []
    if name not in cache:
        javac = os.environ.get("JAVAC") or shutil.which("javac")
        if javac is None:
            cache[name] = None
        else:
            out = tempfile.mkdtemp(prefix="c164-delivery-")
            src = os.path.join(out, "src")
            os.makedirs(src)
            with open(os.path.join(src, f"{name}.java"), "wb") as fh:
                fh.write(source)
            got = subprocess.run((javac,) + JAVAC + ("-d", out, os.path.join(src, f"{name}.java")),
                                 capture_output=True, text=True)
            made = {}
            for f in os.listdir(out):
                if f.endswith(".class"):
                    with open(os.path.join(out, f), "rb") as fh:
                        made[f] = fh.read()
            version = subprocess.run((javac, "-version"), capture_output=True, text=True)
            cache[name] = (got.returncode, made, (version.stdout + version.stderr).strip(),
                           got.stderr.strip().splitlines()[-1:] or [""])
            shutil.rmtree(out, ignore_errors=True)
    if cache[name] is None:
        return [], [f"{rel}: its note names the present source; not rebuilt (no javac here)"]
    code, made, version, last = cache[name]
    if code != 0:
        return [f"{rel}: the source does not build here ({version}): {last[0][:120]}"], []
    if made.get(os.path.basename(rel)) != data:
        return [f"{rel}: not what the source builds here ({version}, javac {' '.join(JAVAC)}); "
                f"rebuilt {len(made.get(os.path.basename(rel), b''))} bytes, kept {len(data)}"], []
    return [], []


def say(status, check, summary, details=()):
    print(f"[{status}] {check:8s} {summary}")
    for line in list(details)[:16]:
        print(f"                {line}")
    extra = len(list(details)) - 16
    if extra > 0:
        print(f"                ... and {extra} more")
    return status


def shorten(text):
    return text[:6] + "..." if len(text) > 9 else "..."


def main():
    ap = argparse.ArgumentParser(description="look at a delivered branch before merging it")
    ap.add_argument("card", help="<category>/<package>")
    ap.add_argument("commit")
    ap.add_argument("--base", default="HEAD")
    args = ap.parse_args()
    cat, _, pkg = args.card.partition("/")
    if cat not in ABBR or not pkg:
        sys.exit(f"card must be <category>/<package>; categories: {', '.join(ABBR)}")
    os.chdir(git("rev-parse", "--show-toplevel").stdout.strip())
    head = git("rev-parse", "--verify", args.commit + "^{commit}").stdout.strip()
    base = git("rev-parse", "--verify", args.base + "^{commit}").stdout.strip()
    fork = git("merge-base", base, head).stdout.strip()
    module = pkg.replace("-", "_")
    own = (f"build/scenes/obs/{cat}/{module}.py", f"build/scenes/obs/{cat}/_",
           f"build/scenes/obs_{ABBR[cat]}_", f"renders/obs_{ABBR[cat]}_", f"plan/packages/{cat}/", "plan/parts/")

    # What the merge would change in the base: the base against the merged tree. (The branch against
    # the fork point would also show what the branch took over from the assembly branch on the way.)
    tree = git("merge-tree", "--write-tree", "--name-only", base, head, check=False)
    if tree.returncode not in (0, 1):
        sys.exit("git merge-tree failed: " + tree.stderr.strip()[:300])
    merged = tree.stdout.split("\n", 1)[0].strip()
    conflicts = [x for x in tree.stdout.split("\n\n")[0].splitlines()[1:] if x] if tree.returncode == 1 else []
    changed = git("diff", "--name-status", "-z", base, merged).stdout.split("\0")
    pairs, i = [], 0
    while i + 1 < len(changed):
        status, path = changed[i], changed[i + 1]
        i += 2
        if status.startswith(("R", "C")) and i < len(changed):
            path = changed[i]
            i += 1
        pairs.append((status[:1], path))
    commits = git("log", "--format=%h%x09%p%x09%s", f"{fork}..{head}").stdout.strip().splitlines()
    print(f"delivery {args.card}: {head[:7]} against {base[:7]} (forked at {fork[:7]}), "
          f"{len(commits)} commits, {len(pairs)} files")
    results = []

    # ---- scope ----
    mine, common, director, others, outside = [], [], [], [], []
    for status, path in pairs:
        if not path.startswith(ROOT):
            outside.append(f"{status} {path}")
            continue
        rel = path[len(ROOT):]
        if rel.startswith(own):
            mine.append(rel)
        elif rel.startswith(DIRECTOR) and not rel.startswith(COMMON):
            director.append(f"{status} {rel}")
        elif rel.startswith(COMMON) or (rel.startswith("build/") and rel.count("/") == 1) or \
                re.fullmatch(r"build/scenes/obs/[a-z]+/__init__\.py", rel):
            common.append(f"{status} {rel}")
        else:
            others.append(f"{status} {rel}")
    details = ([f"the director's file: {p}" for p in director] + [f"outside the project folder: {p}" for p in outside]
               + [f"common file (merge-key holder's; agreed beforehand?): {p}" for p in common]
               + [f"not this card's file: {p}" for p in others])
    summary = f"{len(mine)} of {len(pairs)} files are the card's own"
    results.append(say("FAIL" if director or outside else "WARN" if common or others else "PASS", "scope",
                       summary, details))

    # ---- files ----
    fails, warns, binary, rebuilt, cache = [], [], set(), 0, {}
    for status, path in pairs:
        if status == "D":
            continue
        low = path.lower()
        data = blob(merged, path) or b""
        size = len(data)
        rel = path[len(ROOT):] if path.startswith(ROOT) else path
        ext = os.path.splitext(low)[1]
        if low.endswith(BANNED):
            fails.append(f"{rel}: this kind of file does not belong in the repository")
        elif low.endswith(SOUNDS):
            fails.append(f"{rel}: a sound file; the map uses the game's own sounds (ask A0 before adding one)")
        elif low.endswith(PICTURES):
            binary.add(path)
            if not data.startswith(MAGIC[ext]):
                fails.append(f"{rel}: named as a picture, but it is not one")
            elif rel.startswith("build/"):
                warns.append(f"{rel}: a picture in the code tree; every texture is painted by code -- "
                             f"where is it from?")
        elif is_binary(data):
            binary.add(path)
            if BUILT.fullmatch(rel) and path.startswith(ROOT):
                f, w = built_class(merged, rel, data, cache)
                fails += f
                warns += w
                rebuilt += not f and not w
            else:
                fails.append(f"{rel}: a binary file; only pictures and the built helper classes "
                             f"(tools/win/helper/*.class beside their source) may be")
        if size > HUGE:
            fails.append(f"{rel}: {size / 1048576:.1f} MB")
        elif size > LARGE:
            warns.append(f"{rel}: {size / 1048576:.1f} MB")
    note = f"; {rebuilt} built classes are byte for byte what their source builds here" if rebuilt else ""
    results.append(say("FAIL" if fails else "WARN" if warns else "PASS", "files",
                       "nothing that should not be in the repository" + note if not fails and not warns
                       else f"{len(fails)} not allowed, {len(warns)} to look at" + note, fails + warns))

    # ---- secrets and origin: the added lines only ----
    secrets, origin, path, n = [], [], None, 0
    for line in git("diff", "-U0", "--no-color", "--text", base, merged).stdout.splitlines():
        if line.startswith("+++ "):
            path = line[6:] if line.startswith("+++ b/") else None
            continue
        m = re.match(r"@@ -\d+(?:,\d+)? \+(\d+)", line)
        if m:
            n = int(m.group(1)) - 1
            continue
        if not line.startswith("+") or path is None:
            continue
        n += 1
        if path in binary or path.endswith("tools/delivery.py"):
            continue
        rel = path[len(ROOT):] if path.startswith(ROOT) else path
        for what, rx in SECRETS:
            m = rx.search(line)
            if m:
                secrets.append(f"{rel}:{n}: looks like {what} ({shorten(m.group(0))})")
        m = ORIGIN.search(line)
        if m:
            origin.append(f"{rel}:{n}: \"{m.group(0)}\"")
    results.append(say("FAIL" if secrets else "PASS", "secrets",
                       f"{len(secrets)} lines to remove before this can be merged" if secrets
                       else "nothing that looks like a token, a key or a password", secrets))
    results.append(say("WARN" if origin else "PASS", "origin",
                       f"{len(origin)} lines speak of a licence or of an asset site: read them" if origin
                       else "no mention of licences or asset sites", origin))

    # ---- commits ----
    odd = [f"{h} {s}" for h, parents, s in (c.split("\t", 2) for c in commits)
           if len(parents.split()) < 2 and not MESSAGE.match(s)]
    results.append(say("WARN" if odd else "PASS", "commits",
                       f"{len(odd)} commit messages do not start with \"c164-<code>: \"" if odd
                       else "commit messages are in form", odd))

    # ---- pictures: the package's test scenes and those the delivery touches, as they stand after the merge ----
    stem = f"obs_{ABBR[cat]}_{module}"
    scenes = {os.path.basename(p) for p in
              git("ls-tree", "--name-only", merged, f"{ROOT}build/scenes/", check=False).stdout.splitlines()
              if os.path.basename(p) == stem or os.path.basename(p).startswith(stem + "_")} if pairs else set()
    scenes = sorted(scenes | {m.group(1) for _, path in pairs for m in
                              [re.match(re.escape(ROOT) + r"(?:build/scenes|renders)/(obs_[a-z]+_[^/]+)/", path)] if m})
    code = [f"{ROOT}build/scenes/obs/{cat}/{module}.py", f":(glob){ROOT}build/scenes/obs/{cat}/_*"]
    notes, without, shown = [], [], 0
    for scene in scenes:
        shots = blob(merged, f"{ROOT}build/scenes/{scene}/shots.json")
        if shots is None:
            if blob(merged, f"{ROOT}build/scenes/{scene}/__init__.py") is None:
                notes.append(f"renders/{scene}/: pictures of a scene that is not there")
            continue
        try:
            names = [s["name"] for s in json.loads(shots.decode("utf-8"))]
        except (ValueError, KeyError, TypeError):
            notes.append(f"{scene}: its shots.json cannot be read")
            continue
        folder = f"{ROOT}renders/{scene}/"
        kept = {os.path.basename(p)[:-4] for p in
                git("ls-tree", "--name-only", merged, folder, check=False).stdout.splitlines() if p.endswith(".png")}
        if not kept:
            without.append(scene)
            continue
        shown += len(kept & set(names))
        missing = [n for n in names if n not in kept]
        if missing:
            notes.append(f"{scene}: no picture of {', '.join(missing)}")
        note = blob(merged, folder + "shots.txt")
        if note is None:
            notes.append(f"{scene}: no shots.txt, so which commit the pictures show is not noted")
            continue
        drawn, noted = {}, set()
        for line in note.decode("utf-8", "replace").splitlines():
            parts = line.split("\t")
            if len(parts) == 3 and not line.startswith("#"):
                noted.add(parts[0])
                if parts[0] in names:
                    drawn.setdefault(parts[2], []).append(parts[0])
        left = sorted((kept & noted) - set(names))
        if left:
            notes.append(f"{scene}: pictures left over, the list has no such shot any more: {', '.join(left)}")
        if not noted:
            notes.append(f"{scene}: shots.txt names no commit (not written by tools/selfshots.py)")
        for commit, of in sorted(drawn.items()):
            if commit.endswith("+"):
                notes.append(f"{scene}: {len(of)} pictures were drawn from uncommitted code ({commit})")
            elif git("merge-base", "--is-ancestor", commit, head, check=False).returncode != 0:
                notes.append(f"{scene}: {len(of)} pictures are noted as showing {commit}, which is not in the "
                             f"branch's history")
            else:
                since = git("diff", "--name-only", commit, head, "--", f"{ROOT}build/scenes/{scene}/", *code,
                            check=False).stdout.split()
                if since:
                    notes.append(f"{scene}: {len(of)} pictures show {commit}; the card's code has changed since "
                                 f"({', '.join(os.path.basename(p) for p in since[:4])}"
                                 f"{' ...' if len(since) > 4 else ''}): draw them again")
    notes = [f"{s}: no pictures kept (tools/selfshots.py {s}, then commit renders/{s}/)" for s in without] + notes
    results.append(say("WARN" if notes else "PASS", "pictures",
                       "no test scene with a shot list is touched" if not scenes
                       else f"{len(scenes)} test scene{'s' if len(scenes) != 1 else ''}, {shown} shots with a picture kept"
                       + ("" if notes else "; every shot has one"), notes))

    # ---- merge ----
    behind = len(git("rev-list", f"{head}..{base}").stdout.split())
    if conflicts:
        results.append(say("FAIL", "merge", f"conflicts in {len(conflicts)} files; the branch has to merge the "
                           f"assembly branch first", conflicts))
    else:
        results.append(say("PASS", "merge", f"merges cleanly; {behind} commits behind the base"))

    failed, warned = results.count("FAIL"), results.count("WARN")
    print(f"result: {'FAIL' if failed else 'PASS'} ({failed} failed, {warned} to look at)")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
