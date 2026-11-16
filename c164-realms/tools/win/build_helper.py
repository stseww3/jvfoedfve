#!/usr/bin/env python3
"""Build the picture helper's class from win/CamHelper.java. Needs a JDK (javac).

    python tools/win/build_helper.py            build win/helper/CamHelper.class, note its source
    python tools/win/build_helper.py --check    exit 1 unless the kept class is of the present source

The Windows workspace has a Java runtime without a compiler, so the built class is kept in the
checkout beside a note of the source it was made from (win/helper/CamHelper.sha1). winmc.py
starts the client through the helper only when that note fits the source; after any change to
CamHelper.java run this again, on a machine with a JDK, and commit both files.
"""
import hashlib
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SOURCE = os.path.join(HERE, "CamHelper.java")
BUILT = os.path.join(HERE, "helper")


def source_mark(path=SOURCE):
    """Names the source whatever line endings the checkout gave it."""
    with open(path, "rb") as fh:
        return hashlib.sha1(fh.read().replace(b"\r\n", b"\n")).hexdigest()


def kept_mark():
    try:
        with open(os.path.join(BUILT, "CamHelper.sha1")) as fh:
            return fh.read().strip()
    except OSError:
        return None


def main():
    if "--check" in sys.argv:
        ok = kept_mark() == source_mark() and os.path.exists(os.path.join(BUILT, "CamHelper.class"))
        print("picture helper: " + ("the kept class is of the present source" if ok else
                                    "the kept class is NOT of the present source; run build_helper.py"))
        sys.exit(0 if ok else 1)
    with tempfile.TemporaryDirectory() as out:
        # Class files of Java 21 run on the workspace's Java 25 and on anything newer.
        subprocess.run(["javac", "--release", "21", "-Xlint:all", "-Werror", "-encoding", "UTF-8", "-d", out, SOURCE],
                       check=True)
        made = sorted(os.listdir(out))
        if made != ["CamHelper.class"]:
            raise SystemExit(f"expected one class file, got {made}")
        os.makedirs(BUILT, exist_ok=True)
        shutil.copyfile(os.path.join(out, "CamHelper.class"), os.path.join(BUILT, "CamHelper.class"))
    with open(os.path.join(BUILT, "CamHelper.sha1"), "w", newline="\n") as fh:
        fh.write(source_mark() + "\n")
    print(f"built {os.path.relpath(os.path.join(BUILT, 'CamHelper.class'))} "
          f"({os.path.getsize(os.path.join(BUILT, 'CamHelper.class'))} bytes) from source {source_mark()[:12]}")


if __name__ == "__main__":
    main()
