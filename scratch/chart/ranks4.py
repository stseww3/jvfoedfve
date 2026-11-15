"""Measure every pair of shuffles (A columns, B rows; rank = (A[x] + B[y]) % 7) for strokes in its thin
scatters. x not cyclic, y cyclic. Saves /tmp/c164_chart/f3/ranks4.npz. Not part of the repo.

  m1  with one rank on (a seventh): the most pixels, over the ranks, that have two or more neighbours on
  t1  with one rank on: touching pairs, summed over the ranks
  m2  with two neighbouring ranks on: pixels with two or more neighbours on, summed over the ranks
  t2  with two neighbouring ranks on: touching pairs, summed over the ranks
"""
import itertools

import numpy as np

N = 7
perms = np.array([(0,) + p for p in itertools.permutations(range(1, N))], dtype=np.int8)   # 720 x 7


def neighbours(on):
    cnt = np.zeros(on.shape, dtype=np.int8)
    for dy in (-1, 0, 1):
        rolled = np.roll(on, dy, axis=-2)
        for dx in (-1, 0, 1):
            if dx == 0 and dy == 0:
                continue
            if dx == 1:
                cnt[..., :, 1:] += rolled[..., :, :-1]
            elif dx == -1:
                cnt[..., :, :-1] += rolled[..., :, 1:]
            else:
                cnt += rolled
    return cnt


M1 = np.zeros((720, 720), np.int16)
T1 = np.zeros((720, 720), np.int16)
M2 = np.zeros((720, 720), np.int16)
T2 = np.zeros((720, 720), np.int16)
for a, A in enumerate(perms):
    G = (A[None, None, :] + perms[:, :, None]) % N          # (720, 7, 7): [b][y][x]
    for r in range(N):
        one = G == r
        c1 = neighbours(one)
        M1[a] = np.maximum(M1[a], (one & (c1 >= 2)).sum(axis=(-1, -2)))
        T1[a] += (one * c1).sum(axis=(-1, -2)) // 2
        two = one | (G == (r + 1) % N)
        c2 = neighbours(two)
        M2[a] += (two & (c2 >= 2)).sum(axis=(-1, -2))
        T2[a] += (two * c2).sum(axis=(-1, -2)) // 2
np.savez("/tmp/c164_chart/f3/ranks4.npz", perms=perms, M1=M1, T1=T1, M2=M2, T2=T2)
print("saved")
for m1 in range(0, 4):
    sel = M1 == m1
    print("m1", m1, "pairs", int(sel.sum()), "m2 min", int(M2[sel].min()) if sel.any() else None)
sel = M1 == 0
vals, counts = np.unique(M2[sel], return_counts=True)
print("m1 == 0: m2 histogram", dict(zip(vals.tolist(), counts.tolist())))
