"""Faces of the set's models that would flicker in the game.

Two faces that lie in one plane, look the same way and cover each other are drawn at the same depth,
and the game shows now one, now the other: it flickers, and worse when the part turns. The offline
pictures do not show it. This looks for such pairs in the engine's thirteen models: every box is
taken with its rotation and put where its piece stands, so faces of different pieces are compared
as well (moving pieces in their rest pose). A pair is told only where nothing else covers it.

Left out: the slabs of one tube and the sides of one ring (same model, same seed, same paint), which
carry the same picture, and faces that look down from the floor's level, which nobody sees.

    python -m scenes.obs_mach_engine_dynamo.planes [piece ...]     about a minute for the whole set

The way out of a pair is always the same: one of the two stands half a texel proud of the other,
or ends where the other begins.
"""
import collections
import math
import sys

import numpy as np

from artkit import models as M
from scenes.obs.machines import engine

NORMAL = {"w": (-1, 0, 0), "e": (1, 0, 0), "d": (0, -1, 0), "u": (0, 1, 0), "n": (0, 0, -1), "s": (0, 0, 1)}
SAME = 2e-4                 # blocks: planes closer than this are one plane
STEP = 1.0 / 48.0           # blocks between the points a face is tried at: a third of a texel
OUT = 0.003                 # blocks before a face that have to be free for it to be seen


def _rot(q, v):
    return np.array(M._qrot(q, tuple(float(x) for x in v)))


def _boxes(pieces):
    """[(piece, index, centre, half sizes, turn, the model's own record)] in blocks, in the set's frame."""
    out = []
    for name, d in pieces.items():
        at = np.array(d.at)
        for i, p in enumerate(d.m.parts):
            lo, hi = np.array(p["lo"]), np.array(p["hi"])
            out.append((name, i, at + (lo + hi) / 2.0 / d.u, (hi - lo) / 2.0 / d.u, p["rot"][0] if p["rot"] else M.IDENT, p))
    return out


def _faces(boxes):
    """[(box, letter, normal, the plane's offset, middle, half edge, half edge, material)]"""
    out = []
    for b, (_name, _i, c, half, q, p) in enumerate(boxes):
        for letter, nl in NORMAL.items():
            if letter in p["skip"]:
                continue
            k = [abs(v) for v in nl].index(1)
            o1, o2 = [j for j in range(3) if j != k]
            n = _rot(q, nl)
            mid = c + n * half[k]
            e1, e2 = [0.0] * 3, [0.0] * 3
            e1[o1], e2[o2] = half[o1], half[o2]
            out.append((b, letter, n, float(n @ mid), mid, _rot(q, e1), _rot(q, e2), p["faces"].get(letter, p["mat"])))
    return out


def flicker(pieces, only=()):
    """[(piece, piece, paint, paint, normal, where, texels seen, pairs)]: the places where two faces
    of `pieces` ({name: a drawing with .m, .at and .u}) share a plane and are both seen."""
    boxes = _boxes(pieces)
    faces = _faces(boxes)
    centre = np.array([b[2] for b in boxes])
    reach = np.array([np.linalg.norm(b[3]) for b in boxes])
    back = [tuple(-x for x in b[4][:3]) + (b[4][3],) for b in boxes]

    def inside(pt, b):
        return bool(np.all(np.abs(_rot(back[b], pt - boxes[b][2])) < boxes[b][3] - 1e-5))

    def on(pt, f):
        v = pt - f[4]
        for t in (f[5], f[6]):
            ln = float(t @ t)
            if ln < 1e-12 or abs(float(v @ t)) > ln - 1e-5 * math.sqrt(ln):
                return False
        return True

    def seen(f1, f2):
        """Texels of f1 that lie on f2 as well with nothing before them."""
        l1, l2 = 2.0 * np.linalg.norm(f1[5]), 2.0 * np.linalg.norm(f1[6])
        n1, n2 = (max(3, min(120, int(math.ceil(v / STEP)))) for v in (l1, l2))
        hit = 0
        for i1 in range(n1):
            for i2 in range(n2):
                pt = f1[4] + f1[5] * ((i1 + 0.5) / n1 * 2.0 - 1.0) + f1[6] * ((i2 + 0.5) / n2 * 2.0 - 1.0)
                if not on(pt, f2):
                    continue
                before = pt + f1[2] * OUT
                near = np.nonzero(np.linalg.norm(centre - before, axis=1) < reach + 0.01)[0]
                if not any(inside(before, int(b)) for b in near if b not in (f1[0], f2[0])):
                    hit += 1
        return l1 * l2 * 256.0 * hit / (n1 * n2)

    by_way = collections.defaultdict(list)
    for f in faces:
        by_way[tuple(int(round(v * 500)) for v in f[2])].append(f)
    places = collections.OrderedDict()
    for group in by_way.values():
        group.sort(key=lambda f: f[3])
        for a, fa in enumerate(group):
            for fb in group[a + 1:]:
                if fb[3] - fa[3] > SAME:
                    break
                if fa[0] == fb[0]:
                    continue
                ba, bb = boxes[fa[0]], boxes[fb[0]]
                if only and ba[0] not in only and bb[0] not in only:
                    continue
                if ba[0] == bb[0] and ba[5]["seed"] == bb[5]["seed"] and fa[7].name == fb[7].name:
                    continue
                if fa[2][1] < -0.999 and abs(fa[4][1]) < SAME:
                    continue
                if np.linalg.norm(fa[4] - fb[4]) > sum(np.linalg.norm(v) for v in (fa[5], fa[6], fb[5], fb[6])):
                    continue
                area = max(seen(fa, fb), seen(fb, fa))
                if not area:
                    continue
                key = (ba[0], bb[0], fa[7].name, fb[7].name, tuple(round(float(v), 2) for v in fa[2]), round(fa[3], 4))
                place = places.setdefault(key, [fa[4], 0.0, 0])
                place[1] += area
                place[2] += 1
    return [key[:5] + (tuple(round(float(v), 3) for v in where), area, pairs)
            for key, (where, area, pairs) in places.items()], len(boxes), len(faces)


def main(argv):
    found, boxes, faces = flicker(engine._drawn(), set(argv))
    for a, b, paint_a, paint_b, way, where, area, pairs in sorted(found):
        print(f"{a} / {b}: {paint_a} / {paint_b}{' (one paint)' if paint_a == paint_b else ''}; looking "
              f"{' '.join(f'{v:+.2f}' for v in way)} near {' '.join(f'{v:.3f}' for v in where)}; "
              f"{area:.1f} texels in {pairs} pairs of faces")
    print(f"{boxes} boxes, {faces} faces: {len(found)} places where two faces share a plane and both are seen")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
