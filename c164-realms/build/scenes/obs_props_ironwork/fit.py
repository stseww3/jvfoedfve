"""props/ironwork on the real wall, by numbers: what can be told without a picture.

Builds the test scene and looks at every opening square on from outside, texel by texel (16 to
the block): the stone of A3's wall plane that bounds it (with the stairs hung in an arched head),
A1's net of glazing bars on the glass behind it, and the iron this family presses on it. It holds
the iron to what the review asked of it (plan/aesthetics/S3-reviews-v4.md, review 5 and after):

  1  a member covers two pixels of glass at most or a whole light: no light is left narrower or
     lower than five pixels (a whole light is seven; the two end ones keep five)
  2  the foot plate covers the bottom row of lights up to the first level bar; the transom lies
     on the 4.0 block line
  3  above the springing, glass shows inside the ring only, no iron stands inside the round, and
     what the ring leaves of the net is the same left and right
  4  the head of the entrance doorway is filled: no hole between the fan's glass and the ring
  5  a grille's bars ride on the upright bars of the net: every light keeps five pixels
  6  the iron stays in the reveal: in front of the glass, behind the wall face, between the jambs
     (the ring of a window may run a pixel into the stone beside its narrower jamb)

A rivet head on the reveal face of a jamb stands a pixel into the light beside it; that is the
head seen from the side, not a member, and is counted on its own.

    python -m scenes.obs_props_ironwork.fit            # drawings, numbers, findings
    python -m scenes.obs_props_ironwork.fit check      # numbers and findings (exit code 1 on a finding)
"""
import math
import sys

from artkit import models as M
from artkit.canvas import Canvas

from scenes.obs.common import blocks as B
from scenes.obs.main import _order as O
from scenes.obs.main import facade
from scenes.obs.materials import windows as glazing
from scenes.obs.props import _kit as K
from scenes.obs.props import ironwork

from . import _glass, build, door_table, plan

TILE = 16
SPRING = 4 * TILE                       # an opening six high springs its arch four blocks up
ON_GLASS = 2                            # what a jamb or the ring may cover of the glass, in texels
LIGHT = 5                               # the narrowest a light may be left
GLASSY = {f.block for f in B.LIT_WINDOWS + B.DARK_WINDOWS}
GLASS_RAMPS = ("glow", "opal", "night_glass")
WAY = {name: step for step, name in ironwork.OUT.items()}
FRAMES = ("window_arch", "door_frame", "gate")
MARK = {"iron": "I", "rivet": "o", "glass": "*"}


def _net():
    """A1's glazing bars in one block's picture: the texel columns from the left, the rows from the
    bottom (materials/windows keeps them from the top)."""
    bars = glazing._BARS[glazing.VERSION]
    return set(bars["cols"]), {TILE - 1 - row for row in bars["rows"]}


def _stone(state, right):
    """Which texels of a wall-plane cell are stone, seen from outside: f(from the left, from the
    bottom). A stair hung in the corner of an arched head is solid in its upper half and, below,
    on the side it faces. A light source is nothing."""
    name, _, props = (state or "").partition("[")
    if not name or name.split(":")[-1] == B.LIGHT:
        return lambda j, i: False
    props = dict(p.split("=") for p in props.rstrip("]").split(",") if p)
    if name.endswith("_stairs") and props.get("half") == "top":
        way = WAY[props["facing"]]
        side = way[0] * right[0] + way[1] * right[1]
        if side:
            return lambda j, i: i >= TILE // 2 or (j >= TILE // 2) == (side > 0)
    return lambda j, i: True


class View:
    """An opening seen square on from outside, w x h texels, (0, 0) its lower left corner.

    open    the texels the stone leaves open        glass   those with a pane behind them
    bar     those where a glazing bar is painted    iron    {texel: (kind, how far out)}, see cover()
    member  the texels a piece of iron covers that is not a rivet head
    """

    def __init__(self, canvas, cells, inward, y0, y1):
        out = (-inward[0], -inward[1])
        right = K.turn(K.FACING[ironwork.OUT[out]], (1.0, 0.0, 0.0))
        right = (int(round(right[0])), int(round(right[2])))
        cells = sorted(cells, key=lambda q: q[0] * right[0] + q[1] * right[1])
        self.w, self.h = TILE * len(cells), TILE * (y1 - y0 + 1)
        self.open, self.glass, self.bar, self.iron, self.member = set(), set(), set(), {}, set()
        cols, rows = _net()
        for k, (x, z) in enumerate(cells):
            for y in range(y0, y1 + 1):
                stone = _stone(canvas.get(x + out[0], y, z + out[1]), right)
                glazed = (canvas.get(x, y, z) or "").partition("[")[0] in GLASSY
                for j in range(TILE):
                    for i in range(TILE):
                        if stone(j, i):
                            continue
                        at = (TILE * k + j, TILE * (y - y0) + i)
                        self.open.add(at)
                        if glazed:
                            self.glass.add(at)
                            if j in cols or i in rows:
                                self.bar.add(at)

    def clear(self, at):
        """Open and with no iron over it: glass, a glazing bar or a hole in sight."""
        return at in self.open and at not in self.iron

    def light(self, at):
        """Glass that no stone, no glazing bar and no member covers."""
        return at in self.glass and at not in self.bar and at not in self.member

    def lights(self, rows):
        """The widths and the heights of the lights that lie in `rows`, as two sorted lists."""
        def runs(line):
            n, out = 0, set()
            for lit in list(line) + [False]:
                if lit:
                    n += 1
                elif n:
                    out.add(n)
                    n = 0
            return out

        wide, high = set(), set()
        for v in rows:
            wide |= runs(self.light((u, v)) for u in range(self.w))
        for u in range(self.w):
            high |= runs(self.light((u, v)) for v in rows)
        return sorted(wide), sorted(high)

    def shut(self, v):
        """True where iron closes row v from stone to stone."""
        row = [(u, v) for u in range(self.w) if (u, v) in self.open]
        return bool(row) and all(self.iron.get(at, ("",))[0] in ("iron", "rivet") for at in row)

    def drawing(self):
        """# stone, . glass, + glazing bar, I iron, o rivet, * the model's own glass, blank: a hole"""
        def mark(at):
            if at not in self.open:
                return "#"
            if at in self.iron:
                return MARK[self.iron[at][0]]
            return "+" if at in self.bar else "." if at in self.glass else " "

        return "\n".join("".join(mark((u, v)) for u in range(self.w)) for v in reversed(range(self.h)))


def _hull(points):
    """The convex outline of points in the plane, counter-clockwise."""
    points = sorted(set(points))

    def half(seq):
        out = []
        for p in seq:
            while len(out) >= 2 and ((out[-1][0] - out[-2][0]) * (p[1] - out[-2][1])
                                     - (out[-1][1] - out[-2][1]) * (p[0] - out[-2][0])) <= 1e-12:
                out.pop()
            out.append(p)
        return out[:-1]

    return half(points) + half(reversed(points))


def _within(poly, x, y):
    return all((b[0] - a[0]) * (y - a[1]) - (b[1] - a[1]) * (x - a[0]) >= -1e-9
               for a, b in zip(poly, poly[1:] + poly[:1]))


def _corners(part):
    c = [(part["lo"][i] + part["hi"][i]) / 2.0 for i in range(3)]
    h = [(part["hi"][i] - part["lo"][i]) / 2.0 for i in range(3)]
    q = part["rot"][0] if part["rot"] else M.IDENT
    for sx in (-1, 1):
        for sy in (-1, 1):
            for sz in (-1, 1):
                v = M._qrot(q, (sx * h[0], sy * h[1], sz * h[2]))
                yield tuple(c[i] + v[i] for i in range(3))


def cover(model, scale, view):
    """Lay a wall model on a view, its anchor on the foot centre of the opening: every texel at
    least half covered gets (kind, how far out of the glass face in texels) of the nearest part
    over it; kind is "iron", "rivet" or "glass" (the model's own, a fanlight's). Returns the
    model's reach in texels: (left, right) of the opening's middle, (behind, before) the glass face."""
    across, deep = [], []
    for part in model.parts:
        pts = [(x * scale + view.w / 2.0, y * scale, z * scale) for x, y, z in _corners(part)]
        across += [p[0] - view.w / 2.0 for p in pts]
        deep += [p[2] for p in pts]
        near = max(p[2] for p in pts)
        poly = _hull([p[:2] for p in pts])
        mat = part["mat"]
        kind = "rivet" if mat is K.RIVET else "glass" if mat.name.partition("~")[0] in GLASS_RAMPS else "iron"
        for u in range(max(0, int(math.floor(min(p[0] for p in pts)))), min(view.w, int(math.ceil(max(p[0] for p in pts))))):
            for v in range(max(0, int(math.floor(min(p[1] for p in pts)))), min(view.h, int(math.ceil(max(p[1] for p in pts))))):
                if sum(_within(poly, u + a, v + b) for a in (0.25, 0.75) for b in (0.25, 0.75)) < 2:
                    continue
                if kind == "iron":
                    view.member.add((u, v))
                if near > view.iron.get((u, v), ("", -1e9))[1]:
                    view.iron[(u, v)] = (kind, near)
    return (min(across), max(across)), (min(deep), max(deep))


def _spans(rows):
    """Rows as text: [0, 1, 2, 7] -> "0-2, 7"."""
    out = []
    for v in sorted(rows):
        if out and v == out[-1][1] + 1:
            out[-1][1] = v
        else:
            out.append([v, v])
    return ", ".join(str(a) if a == b else f"{a}-{b}" for a, b in out) or "none"


def judge(view, kind, reach):
    """The numbers of one dressed opening and what is wrong with it: (text, [findings])."""
    found = []
    (left, right), (behind, before) = reach
    if min(left, -right) < -view.w / 2.0 - ON_GLASS:
        found.append(f"the iron is wider than the opening: {left:+.1f} .. {right:+.1f} px of its middle")
    if behind < -1e-6 or before > TILE + 1e-6:
        found.append(f"the iron leaves the reveal: {behind:.1f} .. {before:.1f} px from the glass face")
    depth = f"stands {before:.0f} px out of the glass face"
    heads = sum(1 for at in view.iron if at in view.glass and at not in view.bar and at not in view.member)
    if not kind.startswith(FRAMES):                     # a grille on a base window
        wide, high = view.lights(range(view.h))
        if wide != [LIGHT]:
            found.append(f"the lights between the bars are {wide} px wide, not all {LIGHT}")
        if high and high[0] < LIGHT:
            found.append(f"a light is only {high[0]} px high")
        return f"lights {wide} px wide, {high} px high; {depth}", found

    glazed = kind.startswith("window_arch")
    under = SPRING - ON_GLASS - 1                       # the row under the transom
    shut = [v for v in range(view.h) if view.shut(v)]
    want = list(range(SPRING - ON_GLASS, SPRING + ON_GLASS))
    text = []
    if glazed:
        wide, high = view.lights(range(under + 1))
        want = list(range(TILE // 2)) + want
        if wide and wide[0] < LIGHT or high and high[0] < LIGHT:
            found.append(f"a light under the transom is left {wide} px wide, {high} px high: less than {LIGHT}")
        text.append(f"lights under the transom {wide} px wide, {high} px high, rivet heads over {heads} px of them")
        if [v for v in shut if v < SPRING + ON_GLASS] != want:
            found.append(f"foot plate and transom close rows {_spans(shut)}, not {_spans(want)}")
    elif not set(want) <= set(shut):
        found.append(f"the transom closes rows {_spans(shut)}, not {_spans(want)}")
    text.append(f"iron from stone to stone in rows {_spans(v for v in shut if v < SPRING + ON_GLASS)}")

    # the round the jambs ask for: it carries on their inner edges
    between = [u for u in range(view.w) if (u, under) in view.open and (u, under) not in view.member]
    mid, r = (between[0] + between[-1] + 1) / 2.0, (between[-1] + 1 - between[0]) / 2.0
    leak = inside = seen = round_ = 0
    for u, v in view.open:
        if v < SPRING + ON_GLASS:
            continue
        d = math.hypot(u + 0.5 - mid, v + 0.5 - SPRING)
        round_ += d <= r
        if (u, v) not in view.iron:
            seen += 1
            leak += d > r + 1.0
        elif glazed and d < r - 1.0:
            inside += 1
    text.append(f"the round: radius {r:g} px about {mid:g} px from the left")
    if kind.startswith("gate"):
        text.append("the head is an open fan")
    else:
        what = "glass" if glazed else "hole"
        if leak:
            found.append(f"{leak} px of {what} in sight outside the ring")
        if inside:
            found.append(f"{inside} px of iron inside the round of the head")
        if glazed:
            odd = sum(1 for u in range(1, view.w) for v in range(view.h)
                      if view.clear((u, v)) != view.clear((view.w - u, v)))
            if odd:
                found.append(f"{odd} px of the glass in sight have no mirror image about the middle of the net")
            text.append(f"{seen} px of glass in sight in it (the whole round is {round_}), {leak} outside the ring, "
                        f"{odd} not mirrored")
        else:
            if seen:
                found.append(f"{seen} px of the doorway's head are a hole")
            text.append(f"filled, {seen} px of hole")
    text.append(depth)
    return "; ".join(text), found


def openings(windows, doors):
    """Every opening of the scene's tables as (name, glass columns, inward, (y0, y1))."""
    for w in windows:
        yield f"{w['storey']} window, bay {w['bay']}", list(w["cells"]), tuple(w["inward"]), w["y"]
    for d in doors:
        inward = tuple(d["inward"])
        if len(d["cells"]) == 3 and d.get("arch"):
            yield f"{d['kind']}way, bay {d['bay']}", [(x + inward[0], z + inward[1]) for x, z in d["cells"]], inward, d["y"]


def _piece(canvas, cells, inward, y0):
    """The wall piece of this family that is anchored on an opening's glass face, or None."""
    pos, _ = ironwork._face(cells, inward, y0)
    at = (pos[0] - K.NUDGE * inward[0], pos[1], pos[2] - K.NUDGE * inward[1])
    for x, y, z, nbt in canvas.entities:
        name = nbt["item"]["components"]["minecraft:item_model"].partition(":")[2]
        if name.startswith(ironwork.PREFIX) and max(abs(x - at[0]), abs(y - at[1]), abs(z - at[2])) < 1e-6:
            return name[len(ironwork.PREFIX):]
    return None


def survey():
    """[(name, kind, view, text, findings)] for every opening of the scene that carries a piece,
    and the names of those left bare (the control window, the base windows that keep A3's bars)."""
    canvas = build()
    windows = O.build(Canvas(), plan(), facade.order(), glass=_glass)
    models = ironwork.models()
    out, bare = [], []
    for name, cells, inward, (y0, y1) in openings(windows, door_table()):
        kind = _piece(canvas, cells, inward, y0)
        if kind is None:
            bare.append(name)
            continue
        view = View(canvas, cells, inward, y0, y1)
        key = ironwork.PREFIX + kind
        reach = cover(models[key], ironwork.SCALE[key], view)
        out.append((name, kind, view) + judge(view, kind, reach))
    return out, bare


def main(args):
    rows, bare = survey()
    found, drawn = [], set()
    for name, kind, view, text, wrong in rows:
        if "check" not in args and kind not in drawn:
            drawn.add(kind)
            print(f"\n{kind} in the {name}, {view.w} x {view.h} px ({View.drawing.__doc__}):\n")
            print(view.drawing() + "\n")
        print(f"{name}: {kind}. {text}")
        found += [f"{name}, {kind}: {line}" for line in wrong]
    print(f"left bare: {'; '.join(bare) or 'none'}")
    print("\n".join(found) if found else f"fit: {len(rows)} dressed openings, nothing found")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
