"""Which pairs of shuffles (A for columns, B for rows, rank = (A[x] + B[y]) % 7) give a dither whose
thin scatters hold no stroke: with the pixels of any two neighbouring ranks on (two sevenths), no
pixel has two or more of its eight neighbours on. x is not cyclic (a bar stands between lights),
y is (version b's lights are 14 high and repeat the rows). Not part of the repo.
"""
import itertools
import sys

import numpy as np

N = 7
perms = np.array([(0,) + p for p in itertools.permutations(range(1, N))], dtype=np.int8)   # 720 x 7


def clumps(G):
    """G: (..., 7, 7) ranks [y][x]. For each grid, the worst count over r of pixels (of ranks r, r+1) with two or
    more neighbours on; and the number of touching pairs summed over r."""
    worst = np.zeros(G.shape[:-2], dtype=np.int32)
    pairs = np.zeros(G.shape[:-2], dtype=np.int32)
    for r in range(N):
        on = (G == r) | (G == (r + 1) % N)
        cnt = np.zeros(G.shape, dtype=np.int8)
        for dy in (-1, 0, 1):
            rolled = np.roll(on, dy, axis=-2)
            for dx in (-1, 0, 1):
                if dx == 0 and dy == 0:
                    continue
                sh = np.zeros_like(on)
                if dx == 1:
                    sh[..., :, 1:] = rolled[..., :, :-1]
                elif dx == -1:
                    sh[..., :, :-1] = rolled[..., :, 1:]
                else:
                    sh = rolled
                cnt += sh
        bad = (on & (cnt >= 2)).sum(axis=(-1, -2))
        worst = np.maximum(worst, bad)
        pairs += (on * cnt).sum(axis=(-1, -2)) // 2
    return worst, pairs


def steps(P, cyclic):
    d = [(int(P[(i + 1) % N]) - int(P[i])) % N for i in range(N if cyclic else N - 1)]
    return [min(v, N - v) for v in d]


out = []
for A in perms:
    G = (A[None, None, :] + perms[:, :, None]) % N          # (720, 7, 7): [b][y][x]
    worst, pairs = clumps(G)
    for b in np.nonzero(worst == 0)[0]:
        B = perms[b]
        sa, sb = steps(A, False), steps(B, True)
        out.append((len(set(sa)) + len(set(sb)), int(pairs[b]), "".join(map(str, A)), "".join(map(str, B)), sa, sb))
print(len(out), "pairs hold no stroke")
out.sort(key=lambda t: (-t[0], t[1]))
for t in out[:60]:
    print(t)
import collections
print(collections.Counter(t[0] for t in out))
