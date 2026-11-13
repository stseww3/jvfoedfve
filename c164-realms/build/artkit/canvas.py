"""Sparse voxel canvas: scenes are drawn here first and only then turned into game files."""
from . import blocks as B


def hash3(x, y, z, seed=0):
    """Deterministic pseudo-random number in [0, 1) for a cell."""
    h = (x * 374761393 + y * 668265263 + z * 2147483647 + seed * 1274126177) & 0xFFFFFFFF
    h = ((h ^ (h >> 13)) * 1274126177) & 0xFFFFFFFF
    h ^= h >> 16
    h = (h * 2246822519) & 0xFFFFFFFF
    h ^= h >> 15
    return (h & 0xFFFFFF) / 0x1000000


class Mix:
    """Weighted block mix; the pick depends only on the cell, never on drawing order."""

    def __init__(self, items, seed=0):
        if isinstance(items, dict):
            items = list(items.items())
        total = float(sum(w for _, w in items))
        acc = 0.0
        self.table = []
        for state, w in items:
            acc += w / total
            self.table.append((acc, B.canon(state)))
        self.seed = seed

    def __call__(self, x, y, z):
        r = hash3(x, y, z, self.seed)
        for acc, state in self.table:
            if r < acc:
                return state
        return self.table[-1][1]


class Canvas:
    def __init__(self):
        self.b = {}
        self.entities = []

    # ---- single cells -------------------------------------------------------------------------
    def set(self, x, y, z, state, keep=False):
        """Put a block. `state` is a state string or a function (x, y, z) -> state string.

        keep=True leaves cells that already hold something untouched.
        """
        key = (x, y, z)
        if keep and key in self.b:
            return False
        if callable(state):
            state = state(x, y, z)
        elif state not in B._cache:
            B.parse(state)
        self.b[key] = state
        return True

    def get(self, x, y, z):
        return self.b.get((x, y, z))

    def name(self, x, y, z):
        s = self.b.get((x, y, z))
        return None if s is None else s.partition("[")[0]

    def has(self, x, y, z):
        return (x, y, z) in self.b

    def clear(self, x, y, z):
        self.b.pop((x, y, z), None)

    # ---- bulk ---------------------------------------------------------------------------------
    def box(self, x1, y1, z1, x2, y2, z2, state, keep=False):
        for x in range(min(x1, x2), max(x1, x2) + 1):
            for y in range(min(y1, y2), max(y1, y2) + 1):
                for z in range(min(z1, z2), max(z1, z2) + 1):
                    self.set(x, y, z, state, keep)

    def carve(self, x1, y1, z1, x2, y2, z2):
        for x in range(min(x1, x2), max(x1, x2) + 1):
            for y in range(min(y1, y2), max(y1, y2) + 1):
                for z in range(min(z1, z2), max(z1, z2) + 1):
                    self.b.pop((x, y, z), None)

    def line(self, p, q, state, keep=False):
        """Thin 3D line of blocks from p to q (inclusive)."""
        n = max(abs(q[0] - p[0]), abs(q[1] - p[1]), abs(q[2] - p[2]))
        cells = []
        for i in range(n + 1):
            t = i / n if n else 0.0
            c = (round(p[0] + (q[0] - p[0]) * t), round(p[1] + (q[1] - p[1]) * t), round(p[2] + (q[2] - p[2]) * t))
            if not cells or cells[-1] != c:
                cells.append(c)
                self.set(c[0], c[1], c[2], state, keep)
        return cells

    def add_entity(self, x, y, z, nbt):
        self.entities.append((x, y, z, nbt))

    def top(self, x, z, y_hi, y_lo):
        """Highest occupied y in a column within [y_lo, y_hi], or None."""
        for y in range(y_hi, y_lo - 1, -1):
            if (x, y, z) in self.b:
                return y
        return None

    def bounds(self):
        xs = [k[0] for k in self.b]
        ys = [k[1] for k in self.b]
        zs = [k[2] for k in self.b]
        return (min(xs), min(ys), min(zs)), (max(xs), max(ys), max(zs))

    def count(self):
        out = {}
        for s in self.b.values():
            n = s.partition("[")[0]
            out[n] = out.get(n, 0) + 1
        return out
