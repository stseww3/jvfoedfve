"""Bring a copy of a repository branch in the shared workspace up to date.

    python bin/sync.py [branch or commit] [--to agents/a1]

Without --to the copy is the workspace's own (repo/c164-realms, the integration branch). With --to
it is <to>/repo/c164-realms: every part keeps the copy of its own branch in its own folder.

With the portable git in git/ only what changed is fetched and only the c164-realms folder is
checked out. Without it the branch is downloaded as a zip (the whole repository, every time).
Either way tracked files end up exactly as in the branch, files gone from the branch are removed,
and untracked files (__pycache__, outputs) are left alone.
"""
import argparse
import os
import subprocess
import sys
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = "stseww3/jvfoedfve"
MAIN = "cursor/c164-realms-map-b59c"
KEEP = "c164-realms"
GIT = os.path.join(ROOT, "git", "cmd", "git.exe")


def git(dest, *args, check=True):
    got = subprocess.run([GIT, "-C", dest, *args], capture_output=True, text=True, encoding="utf-8",
                         errors="replace")
    if check and got.returncode:
        sys.exit(f"git {' '.join(args)} failed:\n{got.stderr.strip()[-1500:]}")
    return got


def with_git(dest, ref):
    os.makedirs(dest, exist_ok=True)
    if not os.path.isdir(os.path.join(dest, ".git")):
        subprocess.run([GIT, "init", "-q", dest], check=True)
        git(dest, "config", "core.autocrlf", "false")
        git(dest, "config", "core.longpaths", "true")
        git(dest, "config", "advice.detachedHead", "false")
        git(dest, "remote", "add", "origin", f"https://github.com/{REPO}")
        git(dest, "config", "remote.origin.promisor", "true")
        git(dest, "config", "remote.origin.partialclonefilter", "blob:none")
        git(dest, "sparse-checkout", "set", KEEP)
    before = git(dest, "rev-parse", "-q", "--verify", "HEAD", check=False).stdout.strip()
    git(dest, "fetch", "-q", "--depth", "1", "--filter=blob:none", "origin", ref)
    git(dest, "checkout", "-q", "-f", "--detach", "FETCH_HEAD")
    after = git(dest, "rev-parse", "HEAD").stdout.strip()
    subject = git(dest, "log", "-1", "--format=%s").stdout.strip()
    if before and before != after:
        names = git(dest, "diff", "--name-only", before, after, check=False).stdout.split("\n")
        changed = f"{len([n for n in names if n.strip()])} files differ from the previous copy"
    elif before:
        changed = "no change"
    else:
        changed = "first copy"
    print(f"{os.path.relpath(dest, ROOT)} is at {after[:9]} ({subject}); {changed}")


def with_zip(dest, ref, scratch):
    os.makedirs(dest, exist_ok=True)
    os.makedirs(scratch, exist_ok=True)
    is_commit = len(ref) >= 7 and all(c in "0123456789abcdef" for c in ref)
    url = f"https://codeload.github.com/{REPO}/zip/{ref if is_commit else 'refs/heads/' + ref}"
    archive = os.path.join(scratch, "branch.zip")
    cmd = ["curl", "-sS", "-L", "--fail", "--retry", "3", "-o", archive, url]
    if os.name == "nt":
        cmd[1:1] = ["--ssl-revoke-best-effort"]
    subprocess.run(cmd, check=True)
    seen, changed = set(), 0
    with zipfile.ZipFile(archive) as z:
        commit = z.comment.decode("ascii", "replace")
        for info in z.infolist():
            parts = info.filename.split("/", 1)
            if len(parts) < 2 or not parts[1].startswith(KEEP + "/") or info.is_dir():
                continue
            out = os.path.join(dest, *parts[1].split("/"))
            seen.add(os.path.normcase(out))
            data = z.read(info)
            try:
                with open(out, "rb") as fh:
                    if fh.read() == data:
                        continue
            except FileNotFoundError:
                os.makedirs(os.path.dirname(out), exist_ok=True)
            with open(out, "wb") as fh:
                fh.write(data)
            changed += 1
    removed = 0
    for folder, _, files in os.walk(os.path.join(dest, KEEP)):
        if os.path.basename(folder) == "__pycache__":
            continue
        for name in files:
            path = os.path.join(folder, name)
            if os.path.normcase(path) not in seen:
                os.remove(path)
                removed += 1
    os.remove(archive)
    print(f"{os.path.relpath(dest, ROOT)}: {len(seen)} files at {commit[:9]}: {changed} written, "
          f"{removed} removed (zip)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ref", nargs="?", default=MAIN)
    ap.add_argument("--to", default="")
    args = ap.parse_args()
    home = os.path.normpath(os.path.join(ROOT, args.to))
    if args.to and os.path.dirname(os.path.relpath(home, ROOT)) != "agents":
        sys.exit("--to must be agents/<part>")
    os.makedirs(home, exist_ok=True)
    dest = os.path.join(home, "repo")
    if os.path.exists(GIT):
        with_git(dest, args.ref)
    else:
        with_zip(dest, args.ref, home if args.to else os.path.join(ROOT, "dl"))


if __name__ == "__main__":
    main()
