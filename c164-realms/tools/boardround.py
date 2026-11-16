#!/usr/bin/env python3
"""One round of the board in one job of a node: the twelve views of a commit drawn offline and shot
in the game, and the two beside each other.

    python tools/boardround.py --at <commit> [--budget <seconds>] [--offline-only | --game-only]

Runs tools/boardrender.py --at <commit> (renders/board/<tag>/, the offline renderer) and then
tools/nodetrip.py --at <commit> (the game: renders/real/obs/ with sheet.jpg, and compare.jpg since
the offline board of the same commit is there by then). The commit is one of the assembly's whose
build/ this checkout has: tools/boardnext.sh merges the assembly, names the commit and prints the
job that runs this. On an empty node the first round also fetches the game (tools/nodemc.py setup,
about two minutes); a round is about five minutes after that.

When one of the two fails the other is still made; the round then ends with 1 and says which.
"""
import argparse
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(HERE)


def run(words, tail):
    t0 = time.time()
    done = subprocess.run([sys.executable] + words, cwd=PROJECT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                          text=True, errors="replace")
    lines = done.stdout.rstrip().splitlines()
    print(f"python {' '.join(words)}\nexit {done.returncode}, {time.time() - t0:.0f} s")
    for line in lines[-tail:]:
        print("  " + line)
    sys.stdout.flush()
    return done.returncode


def main():
    ap = argparse.ArgumentParser(description="the board of a commit, offline and in the game, in one job")
    ap.add_argument("--at", required=True, metavar="COMMIT", help="the assembly commit the pictures are named after")
    ap.add_argument("--budget", type=float, default=600.0, help="seconds the game's trip may take")
    ap.add_argument("--offline-only", action="store_true")
    ap.add_argument("--game-only", action="store_true")
    args = ap.parse_args()
    failed = []
    if not args.game_only:
        if run(["tools/boardrender.py", "--at", args.at], 6):
            failed.append("the offline board")
    if not args.offline_only:
        if run(["tools/nodetrip.py", "--at", args.at, "--budget", f"{args.budget:.0f}"], 12):
            failed.append("the game's board")
    if not args.offline_only and not args.game_only and not os.path.exists(os.path.join(PROJECT, "renders", "real", "obs", "compare.jpg")):
        # the trip draws it when the offline board of the same commit is there; say so when it is not
        failed.append("compare.jpg (not drawn)")
    print("board round of " + args.at[:8] + ": " + ("FAILED: " + ", ".join(failed) if failed else "done"))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
