"""Where materials/windows.line() puts the linings, checked without a picture.

    python -m scenes.obs_mat_windows_in.placement

Windows of several sizes are lined facing each of the four ways, and every display entity is
followed to where the game draws its model (DisplayRenderer and ItemTransform: the rule
artkit/gamescene.py draws by). Held to:

    pieces   a window takes as many pieces as its size asks for, and line() returns that number;
    cover    the pieces cover the room side of the glass, every cell once: each lies with its back
             on the glass, half a pixel thick, and spans whole cells;
    facing   a piece's picture looks into the room, and its right hand is the right hand of
             whoever looks at it;
    light    all the pieces of a window stand in one cell, the room's cell before the middle of
             the window. That cell lights them, so the lining is lit as one sheet (c219, g2 #38437);
    ends     of a curtain, the piece at the foot of its window carries the hem and the piece at
             its head the rail, a window of one piece both, and no piece between them either;
    once     glass that has its lining takes no second one, whoever asks again and for whichever
             glass: in the master scene the materials line lines every house (windows.build()),
             and a house that asks for its own windows as well gets nothing more.

The test scene's own windows are 3 by 6 and look one way; the sizes and the ways it does not show
are held here. So is what build() lines in the master scene, as far as the houses are in the tree.
"""
import sys

import numpy as np

from artkit.gameassets import rot

from scenes.obs.common import blocks as B
from scenes.obs.materials import windows as W

STEPS = {"south": (0, 1), "west": (-1, 0), "north": (0, -1), "east": (1, 0)}    # where the room lies
SIZES = ((1, 1), (2, 2), (3, 3), (3, 6), (4, 5), (6, 2), (7, 7))                # blocks wide, high
PLANE, FIRST, FOOT = -3, -4, 8          # the glass: its plane, its first column (a wide one crosses 0), its sill row
ORIGIN = (40, -3, 17)
EPS = 1e-6


class _Entities:
    """What line() asks of a canvas."""

    def __init__(self):
        self.entities = []

    def add_entity(self, x, y, z, nbt):
        self.entities.append((x, y, z, nbt))


def _glass(step, first, w, h):
    """The cells of a window w by h whose first column is `first`, [(x, y, z)]."""
    return [(PLANE, y, a) if step[0] else (a, y, PLANE) for a in range(first, first + w) for y in range(FOOT, FOOT + h)]


def _drawn(x, y, z, nbt, models):
    """Where the game draws a display entity of a lining: the low and the high corner of its model
    in the world, and where the model's +x and +z point."""
    tr = nbt["transformation"]
    plain = [float(v) for key in ("left_rotation", "right_rotation", "scale") for v in tr[key]]
    if not np.allclose(plain, [0, 0, 0, 1, 0, 0, 0, 1, 1, 1, 1], atol=1e-9):
        raise ValueError("placement: a lining is neither turned nor scaled, this one is")
    model = models[nbt["item"]["components"]["minecraft:item_model"].split(":", 1)[-1]]
    turn = rot("y", -float(nbt["Rotation"][0]))
    g = turn @ rot("y", 180.0)          # the item renderer turns a model half a turn about y
    centre = np.array([x, y, z], dtype=float) + turn @ np.array([float(v) for v in tr["translation"]])
    shift = np.array(model.shift())
    ends = [centre + g @ ((np.array(corner) + shift) / 16.0 - 0.5) for corner in model.bounds()]
    return np.minimum(*ends), np.maximum(*ends), g @ np.array([1.0, 0.0, 0.0]), g @ np.array([0.0, 0.0, 1.0])


def check(step, windows, origin=ORIGIN, glass=B.WINDOW_LIT):
    """Line the windows [(first column, w, h)] of one wall in one call, as windows of `glass`.
    Returns what is wrong, a list of sentences, and the cells the entities stand in."""
    dx, dz = step
    inward = dx + dz
    normal = 0 if dx else 2             # the axis the glass looks along; the wall runs along the other
    wall = 2 - normal
    models = W.models()
    c = _Entities()
    cells = [cell for first, w, h in windows for cell in _glass(step, first, w, h)]
    n = W.line(c, cells, step, glass, origin=origin)
    again = W.line(c, cells, step, glass, origin=origin) + W.line(c, cells[:1], step, B.WINDOW_FROSTED, origin=origin)
    kind = W.lining_of(glass)
    bad = []
    want = sum(-(-w // W.PIECE) * -(-h // W.PIECE) for _, w, h in windows)
    if n != want or len(c.entities) != want:
        bad.append(f"{want} pieces expected, {len(c.entities)} placed, {n} returned")
    if again:
        bad.append(f"asked for again, the windows took {again} more pieces")
    face = PLANE + origin[normal] + (1 if inward > 0 else 0)            # the inner face of the glass
    covered, stood = {}, {}
    for x, y, z, nbt in c.entities:
        lo, hi, right, front = _drawn(x, y, z, nbt, models)
        back, out = sorted((lo[normal], hi[normal]), key=lambda v: (v - face) * inward)
        if abs(back - face) > EPS or abs(abs(out - back) - W.THICK / 16.0) > EPS:
            bad.append(f"a piece lies from {back:.4f} to {out:.4f}, the glass ends at {face}")
        if not 0 < ((x, y, z)[normal] - face) * inward < 1:
            bad.append(f"an entity stands at {(x, y, z)[normal]:.4f}, not in the room's cell before the glass at {face}")
        if not np.allclose(front, (dx, 0, dz), atol=EPS):
            bad.append(f"a picture looks along {np.round(front, 3)}, the room lies along {(dx, 0, dz)}")
        if not np.allclose(right, (dz, 0, -dx), atol=EPS):
            bad.append(f"a picture's right hand points along {np.round(right, 3)}, not {(dz, 0, -dx)}")
        span = (lo[wall], hi[wall], lo[1], hi[1])
        if any(abs(v - round(v)) > EPS for v in span):
            bad.append("a piece does not span whole cells: " + ", ".join(f"{v:.4f}" for v in span))
            continue
        a0, a1, y0, y1 = (int(round(v)) for v in span)
        for a in range(a0, a1):
            for row in range(y0, y1):
                covered[(a, row)] = covered.get((a, row), 0) + 1
        if kind == "curtain":
            sill = FOOT + origin[1]
            tall = [h for first, w, h in windows if first <= a0 - origin[wall] < first + w]
            ends = ("", "_foot", "_head", "_whole")[(y0 == sill) + 2 * (bool(tall) and y1 == sill + tall[0])]
            name = nbt["item"]["components"]["minecraft:item_model"].split(":", 1)[-1]
            if name != W.lining_name(kind, a1 - a0, y1 - y0, W.PIECES[kind].index(ends)):
                bad.append(f"the piece over rows {y0 - sill} to {y1 - sill - 1} of its window is {name}, "
                           f"not the piece {ends or 'between'!r}")
        cell = tuple(int(np.floor(v)) for v in (x, y, z))
        stood[cell] = stood.get(cell, 0) + 1
    glass = {(cell[wall] + origin[wall], cell[1] + origin[1]) for cell in cells}
    if set(covered) != glass:
        bad.append(f"{len(glass - set(covered))} cells of glass are not covered, "
                   f"{len(set(covered) - glass)} cells beside the glass are")
    if any(v != 1 for v in covered.values()):
        bad.append(f"{sum(1 for v in covered.values() if v != 1)} cells are covered more than once")
    lamps = {}
    for first, w, h in windows:
        room = [0, 0, 0]
        room[normal] = PLANE + origin[normal] + inward
        room[wall] = first + w // 2 + origin[wall]
        room[1] = FOOT + h // 2 + origin[1]
        lamps[tuple(room)] = -(-w // W.PIECE) * -(-h // W.PIECE)
    if stood != lamps:
        bad.append(f"the pieces stand in {sorted(stood.items())}; the cells before the middle of the windows "
                   f"are {sorted(lamps.items())}")
    return bad, sorted(stood)


def _hung(step, windows):
    """The same windows with the curtain drawn: what is wrong with them, said as such."""
    bad, _ = check(step, windows, glass=B.WINDOW_CURTAIN)
    return [f"as a curtain: {words}" for words in bad]


def _master():
    """What build() lines in the master scene, of the houses that are in the tree: every window of
    lined() and no window twice, the fire windows of the power house with night glass, and nothing
    more for a house that asks for its own windows after it. Returns what is wrong, and the words
    for the table."""
    c = _Entities()
    table = W.lined()
    fire = [w for w in table if w["front"].startswith("power.")]
    n = W.build(c, ORIGIN)
    bad = []
    if n != len(c.entities) or n < len(table):
        bad.append(f"{len(table)} windows to line, {len(c.entities)} pieces placed, {n} returned")
    if W.build(c, ORIGIN):
        bad.append("built a second time, the windows took more pieces")
    for w in fire:
        if W.lining_of(w["glass"]) != "lit":
            bad.append(f"the fire window {w['front']} {w['bay']} is lined as {W.lining_of(w['glass'])}, not as night glass")
        cells = [(x, y, z) for x, z in w["cells"] for y in range(w["y"][0], w["y"][1] + 1)]
        if W.line(c, cells, w["inward"], B.WINDOW_CURTAIN, origin=ORIGIN):
            bad.append(f"the power house asking for its fire window {w['front']} {w['bay']} after build() got a second lining")
    station = [w for w in table if w["front"].startswith("station.")]
    for w in station:
        cells = [(x, y, z) for x, z in w["cells"] for y in range(w["y"][0], w["y"][1] + 1)]
        if W.line(c, cells, w["inward"], w["glass"], origin=ORIGIN):
            bad.append(f"the station asking for its light {w['front']} {w['bay']} after build() got a second lining")
    return bad, (f"{len(table)} windows, {len(fire)} of them fire windows of the power house, {len(station)} lights "
                 f"of the cable car's station, {n} pieces")


def _report(room, what, pieces, bad, stood):
    """One line of the table, and what is wrong under it. Returns 1 for a window that fails."""
    print(f"{room:6} {what:>7} {pieces:6}  {', '.join(str(cell) for cell in stood)}" + ("   FAIL" if bad else ""))
    for words in bad:
        print(f"       {words}")
    return 1 if bad else 0


def main():
    failed = 0
    print(f"{'room':6} {'window':>7} {'pieces':>6}  stands in")
    for room, step in STEPS.items():
        for w, h in SIZES:
            bad, stood = check(step, [(FIRST, w, h)])
            bad += _hung(step, [(FIRST, w, h)])
            failed += _report(room, f"{w}x{h}", -(-w // W.PIECE) * -(-h // W.PIECE), bad, stood)
        # two windows of one wall given in one call, a pier between them: each has its own light
        bad, stood = check(step, [(FIRST, 3, 6), (FIRST + 4, 3, 3)])
        bad += _hung(step, [(FIRST, 3, 6), (FIRST + 4, 3, 3)])
        failed += _report(room, "3x6+3x3", 3, bad, stood)
    bad, lines = _master()
    print(f"\nbuild(), the master scene: {lines}" + ("   FAIL" if bad else ""))
    for words in bad:
        print(f"       {words}")
    if failed or bad:
        print(f"\n{failed} windows and {'the master scene' if bad else 'nothing else'} are not lined as they should be")
        return 1
    print("\nevery window is covered once and takes no second lining, its picture looks into the room, its pieces "
          "stand in one cell, and a curtain has its rail at the head and its hem at the foot")
    return 0


if __name__ == "__main__":
    sys.exit(main())
