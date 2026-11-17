#!/usr/bin/env python3
"""Which cells changed between two versions of the same views, by blank.py's measure.

    python celldiff.py <folder before> <folder now> <name> [<name> ...]

For every view (<name>.jpg in both folders, and <name>_b.jpg, the second frame taken two seconds
later, where there is one) it prints two lists of places, in 1280x720 coordinates:

  filled    blank before, worked now: where something was added
  emptied   worked before, blank now: where something went (a lamp out, a piece that fell out of
            its view band, a thing moved away)

A cell counts only when every frame of a version says the same of it, so a flame, a hand of a
clock or smoke passing through a cell does not make a change. Cells that touch, corners too, are
one place; a place is given by the box around it and the number of its cells.

It says where to look, no more: every place is to be looked at in the two pictures before
anything is said of it (a thing moved on purpose shows as one place emptied and one filled).
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import blank as B  # noqa: E402


def state(folder, name):
    """(blank in every frame, worked in every frame) of a view, or None when it has no picture."""
    paths = [os.path.join(folder, name + tail + ".jpg") for tail in ("", "_b")]
    frames = [B.measure(p) for p in paths if os.path.exists(p)]
    if not frames:
        return None
    blank = np.all([m["blank"] for m in frames], axis=0)
    worked = np.all([~m["blank"] & ~m["is_sky"] for m in frames], axis=0)
    return blank, worked


def places(mask, cell=40):
    out = []
    for cells in B.groups(mask, corners=True):
        rows = [r for r, _ in cells]
        cols = [c for _, c in cells]
        out.append((len(cells), min(cols) * cell, min(rows) * cell, (max(cols) + 1) * cell, (max(rows) + 1) * cell))
    return sorted(out, reverse=True)


def main():
    if len(sys.argv) < 4:
        print(__doc__)
        return 2
    before, now = sys.argv[1], sys.argv[2]
    for name in sys.argv[3:]:
        old, new = state(before, name), state(now, name)
        if old is None or new is None:
            print("%-18s no picture in %s" % (name, before if old is None else now))
            continue
        filled = old[0] & new[1]
        emptied = old[1] & new[0]
        print("%-18s filled %3d cells, emptied %3d cells" % (name, filled.sum(), emptied.sum()))
        for label, mask in (("filled ", filled), ("emptied", emptied)):
            for n, x0, y0, x1, y1 in places(mask):
                print("    %s %3d cells  box %d,%d,%d,%d" % (label, n, x0, y0, x1, y1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
