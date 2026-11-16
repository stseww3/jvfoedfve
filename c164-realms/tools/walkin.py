#!/usr/bin/env python3
"""Where a visitor walks into a model (plan/roles/INTERFACE.md, the fifth supplement of 11-16).

    walkin.py [<scene>] [--category machines] [--out <folder>] [--start x,y,z | <landmark>] [--plans]
        builds the scene (a whole `obs` on a worker node, never on the shared machine), works out
        with tools/walkreach.py where a person gets to on foot, lays the display entities of one
        category over that and says, piece by piece: where it stands, whether anybody gets to it,
        how much of it a person can stand inside, what barriers are in it and whether they keep
        within its outline, which whole cells its outline fills (where a barrier could stand) and
        where a person still gets a shoulder in beside those.

A display entity has no collision: the game lets a person walk through a boiler. The rule is that
a barrier may stand only inside a solid model that is seen (a shut door made of models; a large
solid piece one could walk into), never further out than the model's outline and never more than
two high; a slit left beside it is closed with something that is seen, not with more barriers.

How it is measured. The boxes of every display entity are read as the game shows them (the scene's
resource pack and the game's jar, tools/sightline.py) and sampled into voxels an eighth of a block
wide. Entities of one package that stand within NEAR of each other are one piece. A piece's
outline is its voxels filled downwards: in every column of voxels everything between its lowest
and its highest voxel counts as inside (a car's cabin is inside from floor to roof; the room under
an arch is not, nor what hangs over a head). A person is the game's player, 0.6 wide and 1.8
high, standing on the lattice of half blocks that walkreach uses:

    inside   half or more of the 0.6 square he stands on is inside the outline somewhere along his height
    brush    a fifth to a half of it
    deep     the share of his whole body's box that is inside the outline (1.0: wholly swallowed)
    dense    how much of that part of the outline is model and how much is the air the fill added
             (a boiler is near 1, a frame of rods near 0)

A barrier `fits` in a cell on the floor a person stands on when, over 95 % of the cell, the model
begins under the barrier's top and reaches it (TOL short of it at most): one high where the model
is a block high there, two high where it is two. Under a round belly the barrier's lower edge
stands in air that nobody can get into; the rule counts cells, and the cell is the model's.

A barrier of the scene is the piece's that most of it stands in. Of each one two shares are told:
`plan`, how much of the cell's ground square has the model over it somewhere in the cell's height
(the rest is where a walker is stopped by nothing he sees: the barrier stands out of the model
sideways), and `volume`, how much of the cell lies inside the outline (a car that hangs clear of
the floor leaves its lower cells half empty and is still the director's own example of the rule).
A barrier is told as standing out when its plan share is under 95 %.
Cells that hold a block already are left out. Then the walk is worked out once more with a barrier
in every such cell of every piece somebody stands in: the places inside a model that a person
still gets to are `left`, the slits the rule wants closed with something that is seen.

Doors of blocks are shut to walkreach; a visitor opens them. When the scene has any, a second
reach is worked out with every door block taken away, and a place reached only so is marked `door`.
"""
import argparse
import importlib
import math
import os
import shutil
import sys
import tempfile
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
BUILD = os.environ.get("C164_BUILD") or os.path.normpath(os.path.join(HERE, "..", "build"))
sys.path.insert(0, BUILD)
sys.path.insert(0, HERE)

import makepack  # noqa: E402
import sightline as SL  # noqa: E402
import walkreach as W  # noqa: E402
from artkit import models as M  # noqa: E402
from artkit.gameassets import Assets  # noqa: E402

RES = 8                     # voxels to the block
SAMPLE = 12.0               # sample points to the block along each edge of a model's box
NEAR = 0.75                 # blocks: entities of one package nearer than this are one piece
PAD = 2                     # blocks of empty voxels round a piece
INSIDE, BRUSH = 0.5, 0.2    # shares of the square a person stands on
FULL = 0.95                 # share of a cell the model has to take for a barrier to stay inside it
TOL = 2.0 / 16.0            # blocks a barrier's top may stand over the model's
BESIDE = 1.0                # blocks: a standing place this near a piece is "beside" it
BARRIER_HIGH = 2
KINDS = ("walk", "hop", "fall", "trap")
JAR = os.environ.get("MC_JAR") or os.path.join(os.environ.get("MC_ROOT", "/agent/realms-study"), "client26",
                                              "versions", "26.3", "26.3.jar")


def span(lo, hi):
    return f"{lo}" if lo == hi else f"{lo}..{hi}"


def cells_span(cells):
    """x 3..5, y 1, z -2..0 of a set of cells."""
    return ", ".join(f"{n} {span(min(c[k] for c in cells), max(c[k] for c in cells))}"
                     for k, n in enumerate("xyz"))


def model_ref(nbt):
    return ((nbt.get("item") or {}).get("components") or {}).get("minecraft:item_model")


def owners(category):
    """{model name: package} of every model the category's packages make."""
    from scenes.obs.common import assembly
    out = {}
    for mod in assembly.category(f"scenes.obs.{category}").parts():
        f = getattr(mod, "models", None)
        if f is None:
            continue
        for name in f() or {}:
            out[name] = mod.__name__.rpartition(".")[2]
    return out


def corners_of(box):
    inv, off, lo, hi = box[:4]
    return (SL._corners(lo, hi) - off) @ np.linalg.inv(inv).T


def samples_of(box):
    """Points inside one box of a display entity, in scene coordinates, SAMPLE to the block."""
    inv, off, lo, hi = box[:4]
    back = np.linalg.inv(inv)
    size = hi - lo
    lens = np.linalg.norm(back, axis=0) * size
    n = [max(1, int(math.ceil(v * SAMPLE))) for v in lens]
    axes = [lo[k] + (np.arange(n[k]) + 0.5) / n[k] * size[k] for k in range(3)]
    grid = np.stack(np.meshgrid(*axes, indexing="ij"), axis=-1).reshape(-1, 3)
    return (grid - off) @ back.T


class Piece:
    """The entities of one package that stand together, as voxels."""

    def __init__(self, package, members):
        self.package, self.members = package, members
        self.lo = np.min([m["lo"] for m in members], axis=0)
        self.hi = np.max([m["hi"] for m in members], axis=0)
        self.origin = np.floor(self.lo).astype(int) - PAD
        shape = (np.ceil(self.hi).astype(int) + PAD - self.origin) * RES
        self.occ = np.zeros(tuple(int(v) for v in shape), dtype=bool)
        for m in members:
            for box in m["boxes"]:
                idx = np.floor((samples_of(box) - self.origin) * RES).astype(int)
                ok = np.all((idx >= 0) & (idx < shape), axis=1)
                idx = idx[ok]
                self.occ[idx[:, 0], idx[:, 1], idx[:, 2]] = True
        ny = shape[1]
        any_ = self.occ.any(axis=1)
        self.ylo = np.where(any_, self.occ.argmax(axis=1), ny)                      # per column, voxels
        self.yhi = np.where(any_, ny - self.occ[:, ::-1, :].argmax(axis=1), 0)
        self.footprint = float(any_.sum()) / (RES * RES)                            # m2 of ground under it
        names = {}
        for m in members:
            names[m["ref"]] = names.get(m["ref"], 0) + 1
        self.names = sorted(names, key=lambda k: (-names[k], k))

    def cells(self):
        """The cells the model's own boxes reach into."""
        lo, hi = np.floor(self.lo + 1e-6).astype(int), np.ceil(self.hi - 1e-6).astype(int) - 1
        return lo, hi

    def _columns(self, x0, x1, z0, z1):
        """Voxel column ranges of a span in blocks; None when it lies outside the piece's voxels."""
        ix0 = int(math.floor((x0 - self.origin[0]) * RES + 1e-6))
        ix1 = int(math.ceil((x1 - self.origin[0]) * RES - 1e-6))
        iz0 = int(math.floor((z0 - self.origin[2]) * RES + 1e-6))
        iz1 = int(math.ceil((z1 - self.origin[2]) * RES - 1e-6))
        if ix0 < 0 or iz0 < 0 or ix1 > self.occ.shape[0] or iz1 > self.occ.shape[2] or ix1 <= ix0 or iz1 <= iz0:
            return None
        return ix0, ix1, iz0, iz1

    def within(self, x0, x1, z0, z1, y0, y1):
        """Of the box x0..x1, y0..y1, z0..z1 (blocks): the share of its ground square under which
        the outline is met along y0..y1, the share of its volume inside the outline, and the share
        of that inside part which is model."""
        got = self._columns(x0, x1, z0, z1)
        if got is None:
            return 0.0, 0.0, 0.0
        ix0, ix1, iz0, iz1 = got
        a = (y0 - self.origin[1]) * RES
        b = (y1 - self.origin[1]) * RES
        lo = np.maximum(self.ylo[ix0:ix1, iz0:iz1], a)
        hi = np.minimum(self.yhi[ix0:ix1, iz0:iz1], b)
        over = np.clip(hi - lo, 0.0, None)
        plan = float((over > 1e-9).mean())
        deep = float(over.mean() / (b - a))
        ia, ib = max(int(math.floor(a)), 0), min(int(math.ceil(b)), self.occ.shape[1])
        solid = float(self.occ[ix0:ix1, ia:ib, iz0:iz1].sum())
        dense = min(solid / float(over.sum()), 1.0) if over.sum() > 0 else 0.0
        return plan, deep, dense


def fits(piece, cx, cz, base):
    """How high a barrier may stand in the cell (cx, base, cz) and keep within the piece: 0, 1 or 2."""
    got = piece._columns(cx, cx + 1, cz, cz + 1)
    if got is None:
        return 0
    ix0, ix1, iz0, iz1 = got
    lo = piece.ylo[ix0:ix1, iz0:iz1] / float(RES) + piece.origin[1]
    hi = piece.yhi[ix0:ix1, iz0:iz1] / float(RES) + piece.origin[1]
    high = 0
    for h in range(1, BARRIER_HIGH + 1):
        if float(((lo < base + 1 - TOL) & (hi >= base + h - TOL)).mean()) < FULL:
            break
        high = h
    return high


def gather(canvas, shapes, own):
    """The display entities of the category, by package, with their boxes and the box round them."""
    by_package, skipped = {}, {}
    for x, y, z, nbt in canvas.entities:
        ref = model_ref(nbt)
        if not ref:
            continue
        package = own.get(ref.split(":", 1)[-1])
        if package is None:
            continue
        boxes = SL.entity_boxes(shapes, x, y, z, nbt)
        if not boxes:
            skipped[ref] = skipped.get(ref, 0) + 1
            continue
        pts = np.concatenate([corners_of(b) for b in boxes])
        by_package.setdefault(package, []).append(
            {"ref": ref.split(":", 1)[-1], "boxes": boxes, "lo": pts.min(axis=0), "hi": pts.max(axis=0)})
    return by_package, skipped


def pieces_of(by_package):
    out = []
    for package in sorted(by_package):
        members = by_package[package]
        parent = list(range(len(members)))

        def find(i):
            while parent[i] != i:
                parent[i] = parent[parent[i]]
                i = parent[i]
            return i

        for i, a in enumerate(members):
            for j in range(i):
                b = members[j]
                if np.all(a["lo"] - NEAR <= b["hi"]) and np.all(b["lo"] - NEAR <= a["hi"]):
                    parent[find(i)] = find(j)
        groups = {}
        for i in range(len(members)):
            groups.setdefault(find(i), []).append(members[i])
        for group in sorted(groups.values(), key=lambda g: tuple(np.min([m["lo"] for m in g], axis=0))):
            out.append(Piece(package, group))
    return out


def name_of(state):
    return state.partition("[")[0].split(":", 1)[-1]


def key_of(x, y, z):
    """A standing place as whole numbers (half blocks, 32nds, half blocks)."""
    return int(round(x * 2)), int(round(y * 32)), int(round(z * 2))


def reach_table(cells, start, bounds):
    """(points (n, 3): x, feet, z; kinds (n,) as indexes of KINDS; through a door (n,); door blocks;
    the cells with the doors of blocks taken away)."""
    reach = W.World(cells, bounds).reach(start)
    table = {node: (KINDS.index(kind), False) for node, kind in reach.kind.items()}
    doors = [p for p, s in cells.items() if name_of(s).endswith("_door")]
    opened = cells
    if doors:
        opened = {p: s for p, s in cells.items() if not name_of(s).endswith("_door")}
        for node, kind in W.World(opened, bounds).reach(start).kind.items():
            if node not in table:
                table[node] = (KINDS.index(kind), True)
    nodes = list(table)
    pts = np.array([W.point(n) for n in nodes], dtype=float).reshape(-1, 3)
    kinds = np.array([table[n][0] for n in nodes], dtype=int)
    door = np.array([table[n][1] for n in nodes], dtype=bool)
    return pts, kinds, door, len(doors), opened


def reach_keys(cells, start, bounds):
    return {key_of(*W.point(node)) for node in W.World(cells, bounds).reach(start).kind}


def look(piece, pts, kinds, door, mine, cells):
    """Everything the table says of one piece; `mine` {cell: (plan share, volume share)} are the
    barriers of the scene that stand in this piece."""
    lo, hi = piece.lo, piece.hi
    near = ((pts[:, 0] >= lo[0] - BESIDE - W.HALF) & (pts[:, 0] <= hi[0] + BESIDE + W.HALF)
            & (pts[:, 2] >= lo[2] - BESIDE - W.HALF) & (pts[:, 2] <= hi[2] + BESIDE + W.HALF)
            & (pts[:, 1] + W.HEIGHT > lo[1]) & (pts[:, 1] < hi[1]))
    rows = []
    for k in np.nonzero(near)[0]:
        x, y, z = pts[k]
        plan, deep, dense = piece.within(x - W.HALF, x + W.HALF, z - W.HALF, z + W.HALF, y, y + W.HEIGHT)
        rows.append((x, y, z, int(kinds[k]), bool(door[k]), plan, deep, dense))
    inside = [r for r in rows if r[5] >= INSIDE]
    brush = [r for r in rows if BRUSH <= r[5] < INSIDE]
    beside = [r for r in rows if r[5] < BRUSH]
    out = {"beside": beside, "inside": inside, "brush": brush}
    # the floor most of the inside places stand on, else the one most of the places beside do
    feet = [r[1] for r in (inside or rows)]
    out["floor"] = max(set(feet), key=feet.count) if feet else None
    clo, chi = piece.cells()
    out["barriers"] = sorted(mine)
    out["barriers_out"] = sorted(((c, plan) for c, (plan, _) in mine.items() if plan < FULL),
                                 key=lambda cs: (cs[1], cs[0]))
    out["barriers_fill"] = [deep for _, deep in mine.values()]
    # the floors people stand on inside it (else the one beside it), and where a barrier fits on each
    levels = {}
    for r in inside:
        levels[r[1]] = levels.get(r[1], 0) + 1
    out["levels"] = sorted(levels.items(), key=lambda kv: -kv[1])
    bases = sorted({int(math.floor(y + 1e-6)) for y in levels} or
                   ({int(math.floor(out["floor"] + 1e-6))} if out["floor"] is not None else set()))
    full = {}
    for base in bases:
        for cx in range(clo[0], chi[0] + 1):
            for cz in range(clo[2], chi[2] + 1):
                high = fits(piece, cx, cz, base)
                if high:
                    full[(cx, base, cz)] = high
    out["full"] = full
    # the cells a barrier would be put in: those of `full` that hold no block yet, one run to the
    # column, from the lowest floor people stand on (never more than two high)
    put = {}
    for (cx, base, cz), high in sorted(full.items(), key=lambda kv: kv[0][1]):
        if (cx, cz) in put:
            continue
        run = [(cx, base + h, cz) for h in range(high)]
        if any(name_of(cells.get(c, "air")) == "barrier" for c in run):
            put[(cx, cz)] = []                      # the column has its barrier
            continue
        put[(cx, cz)] = [c for c in run if name_of(cells.get(c, "air")) in W.NOTHING]
    out["put"] = sorted(c for run in put.values() for c in run) if inside else []
    out["sits"] = float(piece.lo[1] - out["floor"]) if out["floor"] is not None else None
    return out


def kinds_of(rows):
    """walk 12, hop 3 (door 2)"""
    if not rows:
        return "none"
    words = []
    for i, kind in enumerate(KINDS):
        n = sum(1 for r in rows if r[3] == i)
        if n:
            words.append(f"{kind} {n}")
    through = sum(1 for r in rows if r[4])
    return ", ".join(words) + (f" ({through} only through a door of blocks)" if through else "")


def place_of(rows):
    xs, ys, zs = [r[0] for r in rows], [r[1] for r in rows], [r[2] for r in rows]
    return (f"x {min(xs):g}..{max(xs):g}, feet {min(ys):g}" + (f"..{max(ys):g}" if max(ys) > min(ys) else "")
            + f", z {min(zs):g}..{max(zs):g}")


def runs_of(cells):
    """How high the barriers of a piece stand: 'up to 2 high'."""
    columns = {}
    for x, y, z in cells:
        columns.setdefault((x, z), []).append(y)
    high = 0
    for ys in columns.values():
        ys = sorted(ys)
        run = best = 1
        for a, b in zip(ys, ys[1:]):
            run = run + 1 if b == a + 1 else 1
            best = max(best, run)
        high = max(high, best)
    return f"{len(columns)} columns, up to {high} high"


def shares_of(rows):
    """[(cell, share)] by share, the cells of one share together: '50%: (83,-5..-4,23) ...'."""
    by = {}
    for c, share in rows:
        by.setdefault(int(round(share * 100)), []).append(c)
    words = []
    for share in sorted(by):
        columns = {}
        for x, y, z in by[share]:
            columns.setdefault((x, z), []).append(y)
        words.append(f"{share}%: " + " ".join(f"({x},{span(min(ys), max(ys))},{z})" for (x, z), ys in sorted(columns.items())))
    return "; ".join(words)


def clusters_of(cells):
    """Cells that touch (corners count), as lists."""
    left, out = set(cells), []
    while left:
        todo = [left.pop()]
        group = []
        while todo:
            c = todo.pop()
            group.append(c)
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    for dz in (-1, 0, 1):
                        n = (c[0] + dx, c[1] + dy, c[2] + dz)
                        if n in left:
                            left.remove(n)
                            todo.append(n)
        out.append(sorted(group))
    return sorted(out)


def verdict(got):
    inside, mine = got["inside"], got["barriers"]
    easy = [r for r in inside if r[3] in (0, 1)]
    if not got["beside"] and not inside and not got["brush"]:
        return "nobody gets to it"
    if not inside:
        return "nobody can stand in it" + (" (barriers in it)" if mine else "")
    area = len(inside) * W.GRID * W.GRID
    deep = max(r[6] for r in inside)
    how = "on foot" if easy else "only by a fall"
    word = f"WALKED INTO {how}: {area:g} m2 of standing ground, up to {deep:.0%} of the body inside"
    if mine:
        word += f"; {len(mine)} barrier cells are in it and do not close it"
    else:
        word += "; no barrier"
    return word


LEGEND = ("      2 1 a barrier fits, two high or one  + the model takes half the cell or more  - a fifth or more  "
          "B a barrier stands there  . a person stands in the cell's middle beside the model  @ o he stands "
          "there inside it (@: where a barrier fits)")


def plan_of(piece, got, pts, kinds, floor):
    """One floor of the piece as characters, a block a character, north up (LEGEND)."""
    base = int(math.floor(floor + 1e-6))
    clo, chi = piece.cells()
    barriers = {(c[0], c[2]) for c in got["barriers"] if base <= c[1] <= base + 1}
    reached = {}
    for k in np.nonzero((np.abs(pts[:, 1] - floor) <= W.STEP + 1e-6)
                        & (pts[:, 0] >= clo[0] - 1) & (pts[:, 0] <= chi[0] + 2)
                        & (pts[:, 2] >= clo[2] - 1) & (pts[:, 2] <= chi[2] + 2))[0]:
        x, _, z = pts[k]
        if x % 1.0 == 0.5 and z % 1.0 == 0.5:
            reached[(int(math.floor(x)), int(math.floor(z)))] = KINDS[kinds[k]][0]
    lines = [f"      floor at feet {floor:g}; x {clo[0] - 1}..{chi[0] + 1} left to right, z {clo[2] - 1}..{chi[2] + 1} top to bottom"]
    for cz in range(clo[2] - 1, chi[2] + 2):
        row = ""
        for cx in range(clo[0] - 1, chi[0] + 2):
            share = piece.within(cx, cx + 1, cz, cz + 1, floor, floor + W.HEIGHT)[0]
            high = got["full"].get((cx, base, cz), 0)
            if (cx, cz) in barriers:
                ch = "B"
            elif high:
                ch = str(high)
            elif share >= INSIDE:
                ch = "+"
            elif share >= BRUSH:
                ch = "-"
            else:
                ch = " "
            who = reached.get((cx, cz))
            if who and ch == " ":
                ch = "."
            elif who and ch in "12+":
                ch = "o" if ch == "+" else "@"
            row += ch
        lines.append("      |" + row + "|")
    return lines


def main():
    ap = argparse.ArgumentParser(description="where a visitor walks into a model")
    ap.add_argument("scene", nargs="?", default="obs")
    ap.add_argument("--category", default="machines")
    ap.add_argument("--out", help="folder for walkin-<category>.txt")
    ap.add_argument("--start", help="x,y,z of the feet, or a landmark of walkreach (default: the spawn)")
    ap.add_argument("--jar", default=JAR)
    ap.add_argument("--plans", action="store_true", help="draw the floor of every piece somebody can stand in")
    args = ap.parse_args()
    from scenes.obs.common import blocks as B
    from scenes.obs.common import skeleton as S

    t0 = time.time()
    scene = importlib.import_module(f"scenes.{args.scene}")
    canvas = scene.build()
    models = makepack.builder_of(scene, args.scene)()
    work = tempfile.mkdtemp(prefix="walkin_")
    out = []

    def say(text=""):
        out.append(text)
        print(text, flush=True)

    try:
        pack = os.path.join(work, "resourcepack")
        M.write_pack(pack, list(models.values()))
        if hasattr(scene, "write_pack"):
            scene.write_pack(pack)
        shapes = SL.Shapes(Assets(args.jar, packs=(pack,)))
        own = owners(args.category)
        by_package, skipped = gather(canvas, shapes, own)
        pieces = pieces_of(by_package)
    finally:
        shutil.rmtree(work, ignore_errors=True)
    points = W.landmarks()
    start = points["spawn"] if not args.start else points[args.start] if args.start in points else tuple(
        float(v) for v in args.start.split(","))
    m = S.mass_bounds()
    bounds = (m[0] - 40, m[2] - 40, m[3] + 40, m[5] + 40)
    pts, kinds, door, doors, opened = reach_table(canvas.b, start, bounds)
    barriers = {p for p, s in canvas.b.items() if name_of(s) == B.BARRIER}
    owned = [{} for _ in pieces]                    # a barrier is the piece's that most of it stands in
    stray = []
    for c in sorted(barriers):
        shares = [piece.within(c[0], c[0] + 1, c[2], c[2] + 1, c[1], c[1] + 1)[:2] for piece in pieces]
        best = int(np.argmax([deep for _, deep in shares])) if shares else -1
        if best >= 0 and shares[best][1] > 0.0:
            owned[best][c] = shares[best]
        else:
            stray.append(c)
    looks = [look(piece, pts, kinds, door, owned[i], canvas.b) for i, piece in enumerate(pieces)]
    closed = dict(opened)
    for got in looks:
        for c in got["put"]:
            closed[c] = B.BARRIER
    after = reach_keys(closed, start, bounds) if len(closed) != len(opened) or any(g["put"] for g in looks) else None
    for got in looks:
        got["left"] = [r for r in got["inside"] if after is None or key_of(r[0], r[1], r[2]) in after]
    say(f"walkin {args.scene}, category {args.category}: {len(canvas.b)} blocks, {len(canvas.entities)} entities, "
        f"{sum(len(v) for v in by_package.values())} of them the category's in {len(pieces)} pieces; "
        f"{len(pts)} standing places reached from {tuple(round(float(v), 2) for v in start)}"
        f"{f' ({int(door.sum())} only through one of {doors} door blocks)' if doors else ''}; "
        f"{len(barriers)} barrier cells in the scene ({time.time() - t0:.0f} s)")
    if skipped:
        say("  not measured (no boxes to read): " + ", ".join(f"{k} x{v}" for k, v in sorted(skipped.items())))
    walked = 0
    for n, (piece, got) in enumerate(zip(pieces, looks), 1):
        clo, chi = piece.cells()
        word = verdict(got)
        walked += word.startswith("WALKED")
        say()
        say(f"{n:2d}. {piece.package}: {len(piece.members)} entities ({', '.join(piece.names[:3])}"
            f"{' ...' if len(piece.names) > 3 else ''})")
        say(f"    cells x {span(clo[0], chi[0])}, y {span(clo[1], chi[1])}, z {span(clo[2], chi[2])}"
            f"   ->  {word}")
        say(f"    body: {piece.footprint:.1f} m2 of ground under it, {piece.hi[1] - piece.lo[1]:.1f} high"
            + (f", its lowest point {got['sits']:+.2f} from the floor at feet {got['floor']:g}"
               if got["floor"] is not None else ""))
        say(f"    beside it: {kinds_of(got['beside'])}")
        if got["inside"]:
            rows = got["inside"]
            dense = float(np.mean([r[7] for r in rows]))
            say(f"    inside it: {kinds_of(rows)} at {place_of(rows)}; the outline there is {dense:.0%} model"
                + ("; by floor: " + ", ".join(f"feet {y:g}: {n}" for y, n in got["levels"])
                   if len(got["levels"]) > 1 else ""))
        if got["brush"]:
            say(f"    brushed:   {kinds_of(got['brush'])} at {place_of(got['brush'])}")
        if got["barriers"]:
            fill = got["barriers_fill"]
            say(f"    barriers:  {len(got['barriers'])} cells ({cells_span(got['barriers'])}), "
                f"{runs_of(got['barriers'])}; the model fills {min(fill):.0%}..{max(fill):.0%} of a cell's volume"
                + (f"; {len(got['barriers_out'])} of them stand out of the model sideways (the share of the cell's "
                   f"ground the model is over): " + shares_of(got["barriers_out"])
                   if got["barriers_out"] else "; none stands out of the model sideways"))
        if got["inside"] and got["put"]:
            put = got["put"]
            columns = {}
            for c in put:
                columns.setdefault((c[0], c[2]), []).append(c[1])
            two = sum(1 for ys in columns.values() if len(ys) >= 2)
            say(f"    a barrier fits in {len(put)} cells, {len(columns)} columns, {two} of them two high "
                f"({cells_span(put)}): " + " ".join(f"({x},{span(min(ys), max(ys))},{z})"
                                                    for (x, z), ys in sorted(columns.items())))
            left = got["left"]
            say(f"    with those in: {kinds_of(left)}" + (f" still inside it at {place_of(left)} -- the slits beside"
                                                        if left else " inside it -- that closes it"))
        elif got["inside"]:
            say("    a barrier fits in no cell: it would stand out of the model everywhere"
                + (" (the cells it fills hold blocks already)" if got["full"] else ""))
        if args.plans and (got["inside"] or got["barriers"]):
            floors = [y for y, _ in got["levels"][:2]] or [got["floor"]]
            for floor in floors:
                for line in plan_of(piece, got, pts, kinds, floor):
                    say(line)
    say()
    if stray:
        say(f"barriers of the scene in no model of this category: {len(stray)} cells -- "
            + "; ".join(f"{len(g)} at {cells_span(g)}" for g in clusters_of(stray)))
    if args.plans:
        say(LEGEND.strip())
    say(f"result: {walked} of {len(pieces)} pieces can be walked into")
    if args.out:
        os.makedirs(args.out, exist_ok=True)
        path = os.path.join(args.out, f"walkin-{args.category}.txt")
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write("\n".join(out) + "\n")
        print(f"written: {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
