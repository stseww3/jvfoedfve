#!/usr/bin/env python3
"""Set cells of one person's row in plan/ROSTER.md (the aide's helper; the file itself is the record).

    roster_set.py <code> [--chat c321] [--node node41] [--branch cursor/c164-...-f3-xxxx ...] [--add-branch ...]

--branch replaces the "new branch" cell (several are joined), --add-branch appends to it.
Prints the row as it stands afterwards. Touches nothing else.
"""
import argparse
import sys

ROSTER = "/agent/repos/c164-aide-f3-b9ab/c164-realms/plan/ROSTER.md"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("code")
    ap.add_argument("--chat")
    ap.add_argument("--node")
    ap.add_argument("--branch", nargs="+")
    ap.add_argument("--add-branch", nargs="+")
    ap.add_argument("--show", action="store_true")
    args = ap.parse_args()

    with open(ROSTER, encoding="utf-8") as fh:
        lines = fh.read().split("\n")
    hits = [i for i, line in enumerate(lines) if line.startswith("| %s |" % args.code)]
    if len(hits) != 1:
        sys.exit("roster_set: %d rows for the code %r" % (len(hits), args.code))
    i = hits[0]
    cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
    if len(cells) != 7:
        sys.exit("roster_set: the row of %r has %d cells, not 7" % (args.code, len(cells)))
    if args.chat:
        cells[1] = args.chat
    if args.node:
        cells[2] = args.node
    if args.branch:
        cells[6] = "、".join("`%s`" % b for b in args.branch)
    if args.add_branch:
        have = [] if cells[6] == "—" else [cells[6]]
        for b in args.add_branch:
            if "`%s`" % b not in cells[6]:
                have.append("`%s`" % b)
        cells[6] = "、".join(have)
    lines[i] = "| " + " | ".join(cells) + " |"
    if not args.show:
        with open(ROSTER, "w", encoding="utf-8") as fh:
            fh.write("\n".join(lines))
    print("| " + " | ".join(cells[:4] + [cells[4][:24] + "…", "…", cells[6]]) + " |")


if __name__ == "__main__":
    main()
