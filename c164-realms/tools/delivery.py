#!/usr/bin/env python3
"""Look at a delivered branch before it is merged: what it touches and whether anything in it
should not be in the repository. The merge-key holder runs it; it only reads (git, no checkout).

    delivery.py <category>/<package> <commit> [--base <commit>]      base: HEAD (the assembly copy)

  scope     the files changed, sorted into: the card's own (its module, the category's _helpers,
            its test scenes, its card, the parts files), common files (only the merge-key holder
            changes those: agreed beforehand or not?), other cards' files, the director's files
  files     no archives, programs, fonts or world files; pictures and sounds named; nothing large
  secrets   added lines that look like a token, a key or an address with a password in it
            (the finding is shown shortened, never whole)
  origin    added lines that speak of a copyright, a licence or a site that hands out assets
  commits   commit messages start with "c164-<code>: "
  merge     the branch merges into the base without conflicts; how far it is behind

The technical checks of what the code generates are tools/check.py's.
"""
import argparse
import os
import re
import subprocess
import sys

ROOT = "c164-realms/"
ABBR = {"materials": "mat", "sky": "sky", "main": "main", "site": "site", "machines": "mach",
        "props": "props", "interiors": "int", "motion": "mot", "common": "common"}
COMMON = ("build/artkit/", "tools/", "build/scenes/obs/common/", "build/scenes/obs/__init__.py",
          "build/scenes/obs/mood.py", "plan/STATUS.md", "plan/roles/INTERFACE.md")
DIRECTOR = ("plan/ART-PLAN.md", "plan/PIPELINE.md", "plan/roles/", "plan/reviews/")
BANNED = (".zip", ".jar", ".exe", ".dll", ".so", ".ttf", ".otf", ".woff", ".woff2", ".schem", ".schematic",
          ".litematic", ".mca", ".mcworld", ".mcpack", ".7z", ".rar", ".gz", ".tar", ".pyc", ".dat")
PICTURES = (".png", ".jpg", ".jpeg", ".gif", ".webp")
SOUNDS = (".ogg", ".wav", ".mp3", ".flac")
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
           f"build/scenes/obs_{ABBR[cat]}_", f"plan/packages/{cat}/", "plan/parts/")

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
    fails, warns = [], []
    for status, path in pairs:
        if status == "D":
            continue
        low = path.lower()
        size = int(git("cat-file", "-s", f"{merged}:{path}", check=False).stdout.strip() or 0)
        rel = path[len(ROOT):] if path.startswith(ROOT) else path
        if low.endswith(BANNED):
            fails.append(f"{rel}: this kind of file does not belong in the repository")
        elif low.endswith(PICTURES) and rel.startswith("build/"):
            warns.append(f"{rel}: a picture in the code tree; every texture is painted by code -- where is it from?")
        elif low.endswith(SOUNDS):
            warns.append(f"{rel}: a sound; the card has to say how it was made (nothing third-party)")
        if size > HUGE:
            fails.append(f"{rel}: {size / 1048576:.1f} MB")
        elif size > LARGE:
            warns.append(f"{rel}: {size / 1048576:.1f} MB")
    results.append(say("FAIL" if fails else "WARN" if warns else "PASS", "files",
                       "nothing that should not be in the repository" if not fails and not warns
                       else f"{len(fails)} not allowed, {len(warns)} to look at", fails + warns))

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
        if path.lower().endswith(PICTURES + SOUNDS) or path.endswith("tools/delivery.py"):
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
