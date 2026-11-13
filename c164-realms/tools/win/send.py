"""Send files from the shared workspace back to the cloud machine through its temporary upload address.

    python bin/send.py <file> [<file> ...] [--jpeg 92] [--prefix a1_]

The address (with its token) is read from dl/inbox.url; it is a secret and is never printed. Only
the files named are sent. They arrive in the cloud machine's inbox folder under their own names,
with --prefix in front, so every part should pass its own prefix.
--jpeg converts pictures to JPEG of that quality first (smaller, for looking at); without it files
go as they are.
"""
import argparse
import glob
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+")
    ap.add_argument("--jpeg", type=int)
    ap.add_argument("--prefix", default="")
    args = ap.parse_args()
    with open(os.path.join(ROOT, "dl", "inbox.url")) as fh:
        base = fh.read().strip().rstrip("/")
    paths = []
    for pattern in args.files:
        paths += sorted(glob.glob(pattern)) or [pattern]
    tmp = os.path.join(ROOT, "dl", f"send-{os.getpid()}.tmp")
    failed = 0
    for path in paths:
        name = args.prefix + os.path.basename(path)
        src = path
        if args.jpeg:
            from PIL import Image
            Image.open(path).convert("RGB").save(tmp, "JPEG", quality=args.jpeg, subsampling=0)
            src, name = tmp, os.path.splitext(name)[0] + ".jpg"
        cmd = ["curl", "-sS", "--fail", "--retry", "3", "--max-time", "120", "-T", src, f"{base}/{name}"]
        if os.name == "nt":
            cmd[1:1] = ["--ssl-revoke-best-effort"]
        got = subprocess.run(cmd, capture_output=True, text=True)
        ok = got.returncode == 0
        failed += not ok
        problem = got.stderr.strip()[:200].replace(base, "<inbox>")
        print(name, os.path.getsize(src), "ok" if ok else "FAILED " + problem, flush=True)
    if os.path.exists(tmp):
        os.remove(tmp)
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
