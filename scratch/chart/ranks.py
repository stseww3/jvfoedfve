"""Search the pairs of rank tables (A for columns, B for rows, rank = (A[x] + B[y]) % 7) for the furnace
window's dither, and draw candidates. Not part of the repo.

    python ranks.py search            prints the best pairs by the measures below
    python ranks.py draw <out.png> A B [A B ...]     each A, B as seven digits, e.g. 0361425 0526314

Measures, per light of 7 x 7 (x not cyclic: a bar stands between lights; y cyclic: version b's lights are 14 high):
  same   pairs of pixels of one rank that touch at a corner (they show as a stroke when one rank is on)
  next   pairs of pixels of neighbouring ranks that touch along an edge (two points in a run: dust does that)
  steps  how many different steps A and B take from one column / row to the next (1 = a plain lattice)
"""
import itertools
import sys

import numpy as np
from PIL import Image

N = 7


def measures(A, B):
    a = [(A[x + 1] - A[x]) % N for x in range(N - 1)]
    b = [(B[(y + 1) % N] - B[y]) % N for y in range(N)]
    same = sum(1 for ax in a for by in b if (ax + by) % N == 0 or ax == by)
    nxt = sum(N for ax in a if ax in (1, N - 1)) + sum(N for by in b if by in (1, N - 1))
    diag_next = sum(1 for ax in a for by in b for d in ((ax + by) % N, (ax - by) % N) if d in (1, N - 1))
    return same, nxt, diag_next, len(set(a)), len(set(b)), a, b


def search():
    perms = [(0,) + p for p in itertools.permutations(range(1, N))]
    out = []
    for A in perms:
        a = [(A[x + 1] - A[x]) % N for x in range(N - 1)]
        for B in perms:
            same, nxt, diag_next, sa, sb, a, b = measures(A, B)
            out.append((same, nxt, -(sa + sb), diag_next, A, B))
    out.sort()
    return out


def draw(path, pairs, scale=6):
    amber, brown, bar = (201, 106, 28), (108, 77, 46), (27, 32, 39)
    rows = []
    for A, B in pairs:
        cells = []
        for k in range(1, N):                       # how many sevenths are the darker tone
            for start in (0, 3):
                px = np.zeros((N + 2, N + 2, 3), np.uint8)
                px[:] = bar
                for y in range(N):
                    for x in range(N):
                        rank = (A[x] + B[y] + start) % N
                        px[y + 1, x + 1] = brown if rank < k else amber
                cells.append(px)
        rows.append(np.hstack(cells))
    sheet = np.vstack(rows)
    img = Image.fromarray(sheet).resize((sheet.shape[1] * scale, sheet.shape[0] * scale), Image.NEAREST)
    img.save(path)
    print(path, img.size)


if __name__ == "__main__":
    if sys.argv[1] == "search":
        res = search()
        seen = 0
        for same, nxt, div, diag_next, A, B in res:
            if -div < 5:
                continue
            print(same, nxt, -div, diag_next, "".join(map(str, A)), "".join(map(str, B)))
            seen += 1
            if seen >= 40:
                break
    else:
        args = sys.argv[3:]
        pairs = [(tuple(int(c) for c in args[i]), tuple(int(c) for c in args[i + 1])) for i in range(0, len(args), 2)]
        for A, B in pairs:
            print("".join(map(str, A)), "".join(map(str, B)), measures(A, B))
        draw(sys.argv[2], pairs)
