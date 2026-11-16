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
  7  the open fan in the head of a gate: every opening between its rays holds a square of two
     pixels at least (a slit of one pixel smears at any distance), and the fan is the same left
     and right
  8  glass that glows shows its tones as painted to who stands before the wall: the game lights
     an item's faces by where they look, whatever they emit (ironwork.TILT), so a glowing face
     that looks out of the wall has to be lit 0.9 at least, and none may lie on the edge between
     two of its model's axes, where the last bit of a sum decides how it is lit. The lamp under
     the canopy is seen from all round and from under it: every glowing face of it is lit 0.9
     at least (ironwork.SLIDE for those that look down). And every display shows its model as
     the frame it was drawn in says, the anchor on the entity
  9  the lower third of a gate's leaves is shut: iron from stone to stone from the floor up, for
     a third of the rows under the transom at least (c164 #21988, #22558: a gate reads as a gate
     by what is solid below, the bars above it and the light behind them)
 10  who walks (c164 #522: a door people are to walk through stands open, a shut one is a wall;
     the director's desk, 11-16 05:07: a barrier may stand in a shut model door or gate and
     nowhere else): a gate stops him -- the bottom two rows of the plane behind its leaves are
     barriers, as wide as the leaves, and the scene holds no other barrier; a doorway lets him
     by -- nothing stands in its bottom two rows, in the wall line or behind it, and its leaves
     lie along the reveals, not across the opening. And he does not look into the iron: a
     model has no collision, his eye keeps 0.3 block from what stops him and the game draws
     nothing nearer to the eye than 0.05, so a gate's leaves stand 4 px out of the barriers at
     most and the plate of an open leaf 0.25 block off the reveal (ironwork.EYE, NEAR)

 11  no drawn face of a model stands on the edge between two of its axes (K.settle; a6 #75961):
     the game would light it by the last bit of a sum, one way in one copy and another in the
     next. The pieces in a leaning frame of their own are held to it by 8
 12  the globe of the lamp under the canopy is no brighter than OPAL[ironwork.LAMP_TOP] (c332,
     11-16: the head of the comet is the one white of the map)

A rivet head on the reveal face of a jamb stands a pixel into the light beside it; that is the
head seen from the side, not a member, and is counted on its own.

In the head of a window the ring cuts the net's lights; they are counted by their size. Whether
the small ones read as noise is for a picture to tell: closing them would step the round of glass.

    python -m scenes.obs_props_ironwork.fit            # drawings, numbers, findings
    python -m scenes.obs_props_ironwork.fit check      # numbers and findings (exit code 1 on a finding)
"""
import math
import sys

import numpy as np

from artkit import models as M
from artkit.canvas import Canvas
from artkit.gamescene import LAMPS

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
SLIT = 2                                # an opening of a gate's fan holds a square of this side at least
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
    on the side it faces; a half slab is solid in its own half (the one A3 may hang between the two
    stairs to close the crown, facade.CROWN). A light source is nothing."""
    name, _, props = (state or "").partition("[")
    if not name or name.split(":")[-1] == B.LIGHT:
        return lambda j, i: False
    props = dict(p.split("=") for p in props.rstrip("]").split(",") if p)
    if name.endswith("_stairs") and props.get("half") == "top":
        way = WAY[props["facing"]]
        side = way[0] * right[0] + way[1] * right[1]
        if side:
            return lambda j, i: i >= TILE // 2 or (j >= TILE // 2) == (side > 0)
    if name.endswith("_slab") and props.get("type", "bottom") != "double":
        upper = props.get("type") == "top"
        return lambda j, i: (i >= TILE // 2) == upper
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

    def pieces(self, rows):
        """The lights that lie in `rows`, each one a set of texels: glass that hangs together, with
        the glazing bars and the members between the lights left out."""
        return _pieces({(u, v) for u in range(self.w) for v in rows if self.light((u, v))})

    def holes(self, rows):
        """The openings that lie in `rows`, each one a set of texels: what neither stone nor iron
        covers and hangs together."""
        return _pieces({(u, v) for u in range(self.w) for v in rows if self.clear((u, v))})

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


def _pieces(todo):
    """A set of texels as the pieces that hang together (side by side or one over the other)."""
    todo, out = set(todo), []
    while todo:
        stack, piece = [todo.pop()], set()
        while stack:
            u, v = at = stack.pop()
            piece.add(at)
            for near in ((u + 1, v), (u - 1, v), (u, v + 1), (u, v - 1)):
                if near in todo:
                    todo.remove(near)
                    stack.append(near)
        out.append(piece)
    return out


def _square(piece):
    """The side of the largest square of texels that lies in a piece."""
    side = 1
    while any(all((u + a, v + b) in piece for a in range(side + 1) for b in range(side + 1)) for u, v in piece):
        side += 1
    return side


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


def cover(model, scale, view, turns=()):
    """Lay a wall model on a view, its anchor on the foot centre of the opening: every texel at
    least half covered gets (kind, how far out of the glass face in texels) of the nearest part
    over it; kind is "iron", "rivet" or "glass" (the model's own, a fanlight's). `turns` are those
    its display is placed with (a piece drawn in the tilted frame, ironwork.TILT). Returns the
    model's reach in texels: (left, right) of the opening's middle, (behind, before) the glass face."""
    across, deep = [], []
    q = M.IDENT
    for axis, deg in turns:
        q = M._qmul(M.quat(axis, deg), q)
    for part in model.parts:
        pts = [(x * scale + view.w / 2.0, y * scale, z * scale) for x, y, z in (M._qrot(q, p) for p in _corners(part))]
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


def _cut(pieces, what="the head keeps {} lights"):
    """The lights of a head as text: how many there are of each size, and how far the smallest reach."""
    if not pieces:
        return "no light in the head"
    sizes = {}
    for piece in pieces:
        sizes[len(piece)] = sizes.get(len(piece), 0) + 1
    least = min(sizes)
    spans = sorted({(max(u for u, _ in piece) - min(u for u, _ in piece) + 1,
                     max(v for _, v in piece) - min(v for _, v in piece) + 1)
                    for piece in pieces if len(piece) == least})
    return (what.format(len(pieces)) + ": "
            + ", ".join(f"{sizes[px]} of {px} px" for px in sorted(sizes, reverse=True))
            + f"; the smallest lie in {', '.join(f'{w} x {h}' for w, h in spans)} px")


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

    # the round the jambs ask for: it carries on their inner edges. In the row under the transom the
    # jambs are the iron that stands the frame's full depth: the top rail of a gate's leaves lies in
    # that row too, from jamb to jamb, but further back
    row = [(u, under) for u in range(view.w) if (u, under) in view.open]
    proud = max((view.iron[at][1] for at in row if at in view.member), default=0.0)
    between = [u for u, v in row if (u, v) not in view.member or view.iron[(u, v)][1] < proud - 0.5]
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
        leaf = SPRING - ON_GLASS                        # the rows under the transom
        solid = next((v for v in range(leaf) if v not in shut), leaf)
        if 3 * solid < leaf:
            found.append(f"the leaves are shut up to row {solid} only: less than a third of the {leaf} rows "
                         "under the transom")
        text.append(f"the leaves are shut from the floor for {solid} of the {leaf} rows under the transom")

        def share(rows):
            cells = [at for at in view.open if at[1] in rows]
            return sum(1 for at in cells if at not in view.iron) / max(1, len(cells))

        text.append(f"{share(range(view.h)):.0%} of the opening stays open: {share(range(leaf)):.0%} under the "
                    f"transom, {share(range(SPRING + ON_GLASS, view.h)):.0%} over it")
        # who walks into the gate stands against the barriers behind the leaves, his eye EYE out of the glass face
        out = max((view.iron[(u, v)][1] for u in range(between[0], between[-1] + 1) for v in range(leaf)
                   if (u, v) in view.iron), default=0.0)
        if out > ironwork.GATE_REACH * TILE + 1e-6:
            found.append(f"the leaves stand {out:g} px out of the glass face: more than {ironwork.GATE_REACH * TILE:g}, "
                         f"and an eye against the barriers ({ironwork.EYE * TILE:g} px out) looks into them")
        text.append(f"the leaves stand {out:g} px out of the glass face at most, an eye against them {ironwork.EYE * TILE:g}")
        fan = view.holes(range(SPRING + ON_GLASS, view.h))
        slits = [piece for piece in fan if _square(piece) < SLIT]
        if slits:
            found.append(f"{len(slits)} openings of the fan are slits ({sum(map(len, slits))} px): "
                         f"no square of {SLIT} px lies in them")
        odd = sum(1 for u in range(view.w) for v in range(SPRING + ON_GLASS, view.h)
                  if view.clear((u, v)) != view.clear((view.w - 1 - u, v)))
        if odd:
            found.append(f"{odd} px of the fan's openings have no mirror image about the middle of the gate")
        text.append(_cut(fan, "the head is an open fan of {} openings")
                    + f", none without a square of {min(map(_square, fan), default=0)} px; "
                    + f"{seen} px open of the round's {round_}")
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
            text.append(_cut(view.pieces(range(SPRING + ON_GLASS, view.h))))
        else:
            if seen:
                found.append(f"{seen} px of the doorway's head are a hole")
            text.append(f"filled, {seen} px of hole")
    text.append(depth)
    return "; ".join(text), found


AXIS = ((0.0, -1.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, -1.0), (0.0, 0.0, 1.0), (-1.0, 0.0, 0.0), (1.0, 0.0, 0.0))
LOOKS = ("out of the wall", "into the wall", "along the wall", "up", "down")
BRIGHT = 0.9                            # a glowing face that looks out of the wall is lit this much at least


def _dot(a, b):
    return sum(u * v for u, v in zip(a, b))


def _unit(v):
    return tuple(float(c) for c in np.asarray(v, dtype=float) / np.linalg.norm(v))


def glow(kind, facing="east"):
    """How the game lights the glowing faces of a piece of ironwork.SPEC on a wall that looks
    `facing`: ({where a face looks: (the least it is lit, the most, faces)}, faces on an edge).
    A face is lit as if it looked along the axis of its model nearest to its normal -- the first of
    down, up, north, south, west, east where two are equally near (FaceBakery.findClosestDirection)
    -- as the display shows that axis: by the inverse transpose of its matrix (PoseStack.Pose
    .mulPose, computeNormalMatrix), which is the turn itself where the display does no more than
    turn (ironwork.frame). By the two lamps of gamescene.LAMPS, 0.4 at least (the item shader)."""
    shown = np.linalg.inv(np.array(ironwork.frame(kind))).T
    yaw = K.FACING[facing]
    seen, edge = {}, 0
    for part in ironwork.models()[ironwork.PREFIX + kind].parts:
        if not part["emit"]:
            continue
        own = part["rot"][0] if part["rot"] else M.IDENT
        for letter, normal in M.NORMAL.items():
            if letter in part["skip"]:
                continue
            n = M._qrot(own, normal)
            near = sorted(((_dot(n, a), -i) for i, a in enumerate(AXIS)), reverse=True)
            edge += near[0][0] - near[1][0] < 1e-3
            lit_as = K.turn(yaw, _unit(shown @ AXIS[-near[0][1]]))
            shade = min(1.0, 0.4 + 0.6 * sum(max(0.0, _dot(lit_as, lamp)) for lamp in LAMPS))
            x, y, z = _unit(shown @ n)                      # where it looks, in the wall's frame: z out of it
            looks = max(((z, 0), (-z, 1), (abs(x), 2), (y, 3), (-y, 4)))[1]
            lo, hi, count = seen.get(looks, (1.0, 0.0, 0))
            seen[looks] = (min(lo, shade), max(hi, shade), count + 1)
    return seen, edge


def lights(found):
    """One line for every piece of the family that glows; what is wrong goes to `found`."""
    for kind in ironwork.SPEC:
        seen, edge = glow(kind)
        if not seen:
            continue
        print(f"{kind} glows: " + ", ".join(
            f"{LOOKS[k]} lit {lo:.2f}" + ("" if hi - lo < 0.005 else f" to {hi:.2f}") + f" ({count} faces)"
            for k, (lo, hi, count) in sorted(seen.items())))
        if edge:
            found.append(f"{kind}: {edge} glowing faces lie on the edge between two axes of the model")
        for k, (lo, _, _) in sorted(seen.items()):
            if lo < BRIGHT and (k == 0 or kind in ironwork.LAMP_PIECES):
                found.append(f"{kind}: glass that looks {LOOKS[k]} is lit {lo:.2f}, under {BRIGHT}")


def settled(found):
    """Item 11: the models that went over K.settle keep no drawn face between two axes. Item 12: the
    tones of the lamp's globe."""
    models = ironwork.models()
    over = [kind for kind, spec in ironwork.SPEC.items() if "turns" not in spec]
    left = {kind: K.unsettled(models[ironwork.PREFIX + kind]) for kind in over}
    for kind, faces in left.items():
        if faces:
            found.append(f"{kind}: {len(faces)} drawn faces stand between two axes of the model "
                         f"(parts {sorted({i for i, _, _ in faces})[:6]})")
    print(f"settled: {len(over)} models over K.settle, {sum(map(len, left.values()))} faces left between two axes; "
          f"{len(ironwork.SPEC) - len(over)} in a leaning frame of their own")
    allowed = {mat.name for mat in ironwork.OPAL[:ironwork.LAMP_TOP + 1]}
    for kind in ironwork.LAMP_PIECES:
        glass = {mat.name for part in models[ironwork.PREFIX + kind].parts if part["emit"]
                 for mat in [part["mat"], *part["faces"].values()]}
        if glass - allowed:
            found.append(f"{kind}: glass brighter than OPAL[{ironwork.LAMP_TOP}] on the globe: {sorted(glass - allowed)}")
    print(f"the lamp's globe: OPAL[{ironwork.LAMP_TOP}] {ironwork.P.RAMPS['opal'][ironwork.LAMP_TOP]} at the most, "
          f"in {len(ironwork.LAMP_PIECES)} pieces")


def _true(kind):
    """What the frame of a piece does to the faces it draws: (the most an edge is stretched, as a
    part of its length; the most two edges of a face, which are square in the model, lean to each
    other, as a cosine; faces). Nothing where the display does no more than turn; in the slid
    frame nothing either as long as every face drawn is level."""
    frame = np.array(ironwork.frame(kind))
    stretch, lean, faces = 0.0, 0.0, 0
    for part in ironwork.models()[ironwork.PREFIX + kind].parts:
        own = part["rot"][0] if part["rot"] else M.IDENT
        size = [part["hi"][i] - part["lo"][i] for i in range(3)]
        for letter, normal in M.NORMAL.items():
            if letter in part["skip"]:
                continue
            a, b = (frame @ np.array(M._qrot(own, tuple(float(i == k) for i in range(3))))
                    for k in range(3) if not normal[k] and size[k] > 1e-9)
            stretch = max(stretch, abs(np.linalg.norm(a) - 1.0), abs(np.linalg.norm(b) - 1.0))
            lean = max(lean, abs(float(a @ b)) / float(np.linalg.norm(a) * np.linalg.norm(b)))
            faces += 1
    return stretch, lean, faces


def displays(canvas, found):
    """Every display of the family against the frame its model was drawn in: what its
    transformation does to the model as the game puts it together (DisplayRenderer: left turn,
    scale, right turn, and the item renderer's half turn about the model's middle), and where
    the anchor lands. And a piece in the slid frame, whose display stretches along two axes
    (tools/check.py reads that off its scale as a model not 16 pixels to the block): every face
    it draws is shown as the rectangle it was drawn as. What is wrong goes to `found`."""
    models = ironwork.models()
    half = np.diag([-1.0, 1.0, -1.0])
    axes = ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0))
    off, away, kinds = 0.0, 0.0, {}
    for _, _, _, nbt in canvas.entities:
        name = nbt.get("item", {}).get("components", {}).get("minecraft:item_model", "").split(":")[-1]
        if not name.startswith(ironwork.PREFIX):
            continue
        kind, model, tr = name[len(ironwork.PREFIX):], models[name], nbt["transformation"]
        left, right = (np.array([M._qrot(tuple(float(v) for v in tr[key]), a) for a in axes]).T
                       for key in ("left_rotation", "right_rotation"))
        shows = left @ np.diag([float(v) for v in tr["scale"]]) @ right @ half
        frame = np.array(ironwork.frame(kind)) * ironwork.SPEC[kind]["scale"]
        shift = model.shift()
        anchor = np.array([(model.anchor[i] + shift[i] - 8.0) / 16.0 for i in range(3)])
        lands = np.array([float(v) for v in tr["translation"]]) + shows @ anchor
        wrong = float(np.abs(half @ shows - frame).max()), float(np.abs(lands).max())
        if max(wrong) > 1e-5:
            found.append(f"{kind}: its display shows the model {wrong[0]:.2g} off its frame, the anchor "
                         f"{wrong[1]:.2g} block off the entity")
        off, away = max(off, wrong[0]), max(away, wrong[1])
        kinds[kind] = kinds.get(kind, 0) + 1
    print(f"{sum(kinds.values())} displays of {len(kinds)} pieces show their models as drawn: {off:.1g} off the "
          f"frame at most, the anchor {away:.1g} block off the entity")
    for kind in sorted(k for k in ironwork.SPEC if ironwork.SPEC[k].get("slide")):
        stretch, lean, faces = _true(kind)
        tr = ironwork._slid_display(models[ironwork.PREFIX + kind], kind)
        dense = 16.0 * models[ironwork.PREFIX + kind].px / ironwork.SPEC[kind]["scale"]
        print(f"{kind} is drawn in the slid frame (its display's scale {' x '.join(f'{float(v):.3f}' for v in tr['scale'])}): "
              f"its {faces} faces are shown as the rectangles they were drawn as, {dense:g} pixels to the block "
              f"(stretched {stretch:.1g}, leaning {lean:.1g})")
        if max(stretch, lean) > 1e-6:
            found.append(f"{kind}: a face in the slid frame is not level: stretched {stretch:.2g}, leaning {lean:.2g}")
        if kind not in kinds:
            found.append(f"{kind}: the scene shows no piece of it")


def _block(canvas, at):
    """The name of the block at a cell, or None where nothing stands (a light source is nothing)."""
    name = (canvas.get(*at) or "").partition("[")[0].split(":")[-1]
    return None if name in ("", "air", B.LIGHT) else name


def passage(canvas, doors, found):
    """One line for every doorway of the table: what who walks into it meets (rule 10)."""
    leaves = [(x, z, K.turn(float(nbt["Rotation"][0]) - 180.0, (1.0, 0.0, 0.0)))
              for x, _, z, nbt in canvas.entities
              if nbt.get("item", {}).get("components", {}).get("minecraft:item_model", "").endswith("_leaf")]
    plate = ironwork.LEAF_T / 2.0 * ironwork.SPEC["door_leaf"]["scale"] / TILE      # half a leaf's plate, in blocks
    barriers = 0
    for d in doors:
        name = f"{d['kind']}way, {d['front']} front, bay {d['bay']}"
        inward, rows = tuple(d["inward"]), range(d["y"][0], d["y"][0] + ironwork.WALK)
        line = [(x, y, z) for x, z in d["cells"] for y in rows]
        behind = [(x + inward[0], y, z + inward[1]) for x, y, z in line]
        if d["kind"] == "gate":
            barriers += len(behind)
            wrong = [at for at in behind if _block(canvas, at) != ironwork.BARRIER]
            wrong += [at for at in line if _block(canvas, at)]
            if wrong:
                found.append(f"{name}: not shut by barriers behind its leaves and by nothing else: {wrong}")
            print(f"{name}: shut to who walks by {len(behind) - len(wrong)} barriers behind the leaves, "
                  f"rows {_spans(rows)}")
            continue
        wrong = [(at, _block(canvas, at)) for at in line + behind if _block(canvas, at)]
        if wrong:
            found.append(f"{name}: something stands in the way of who walks through: {wrong}")
        xs, zs = [x for x, z in d["cells"]], [z for x, z in d["cells"]]
        mine = [(x, z, way) for x, z, way in leaves
                if min(xs) - 2.0 <= x <= max(xs) + 3.0 and min(zs) - 2.0 <= z <= max(zs) + 3.0]
        across = sum(1 for x, z, way in mine if abs(way[0] * inward[0] + way[2] * inward[1]) < math.sqrt(0.5))
        if across:
            found.append(f"{name}: {across} of its {len(mine)} leaves lie across the opening")
        # how far the room face of an open leaf's plate stands off its reveal: the eye of who walks
        # along the reveal is EYE off it, and the game cuts what is nearer to the eye than NEAR
        mid = (sum(xs) / len(xs) + 0.5, sum(zs) / len(zs) + 0.5)
        off = max((len(d["cells"]) / 2.0 - abs((x - mid[0]) * inward[1] - (z - mid[1]) * inward[0]) + plate
                   for x, z, way in mine), default=0.0)
        if off > ironwork.EYE - ironwork.NEAR + 1e-6:
            found.append(f"{name}: the plate of an open leaf stands {off:.3f} off the reveal: more than "
                         f"{ironwork.EYE - ironwork.NEAR:g}, and who walks along the reveal looks into it")
        print(f"{name}: open to who walks, nothing in rows {_spans(rows)}; "
              f"{len(mine) - across} of its {len(mine)} leaves lie along the reveals, the plate {off:.3f} off them at most")
    placed = sum(n for state, n in canvas.count().items() if state.partition("[")[0].split(":")[-1] == ironwork.BARRIER)
    if placed != barriers:
        found.append(f"the scene holds {placed} barriers, the gates ask for {barriers}")


def openings(windows, doors):
    """Every opening of the scene's tables as (name, glass columns, inward, (y0, y1))."""
    for w in windows:
        yield f"{w['storey']} window, bay {w['bay']}", list(w["cells"]), tuple(w["inward"]), w["y"]
    for d in doors:
        inward = tuple(d["inward"])
        if len(d["cells"]) == 3 and d.get("arch"):
            yield f"{d['kind']}way, bay {d['bay']}", [(x + inward[0], z + inward[1]) for x, z in d["cells"]], inward, d["y"]


def _pieces_at(canvas, cells, inward, y0):
    """The wall pieces of this family that are anchored on an opening's glass face, as they were
    placed: the frame first, then what stands in it (a doorway's fanlight glass)."""
    pos, _ = ironwork._face(cells, inward, y0)
    at = (pos[0] - K.NUDGE * inward[0], pos[1], pos[2] - K.NUDGE * inward[1])
    out = []
    for x, y, z, nbt in canvas.entities:
        name = nbt["item"]["components"]["minecraft:item_model"].partition(":")[2]
        if name.startswith(ironwork.PREFIX) and max(abs(x - at[0]), abs(y - at[1]), abs(z - at[2])) < 1e-6:
            out.append(name[len(ironwork.PREFIX):])
    return out


def survey(canvas=None):
    """[(name, kind, view, text, findings)] for every opening of the scene that carries a piece,
    and the names of those left bare (the control window, the base windows that keep A3's bars)."""
    canvas = canvas or build()
    windows = O.build(Canvas(), plan(), facade.order(), glass=_glass)
    models = ironwork.models()
    out, bare = [], []
    for name, cells, inward, (y0, y1) in openings(windows, door_table()):
        kinds = _pieces_at(canvas, cells, inward, y0)
        if not kinds:
            bare.append(name)
            continue
        view = View(canvas, cells, inward, y0, y1)
        reach = []
        for kind in kinds:
            key = ironwork.PREFIX + kind
            reach.append(cover(models[key], ironwork.SCALE[key], view, ironwork.SPEC[kind].get("turns", ())))
        reach = tuple((min(r[k][0] for r in reach), max(r[k][1] for r in reach)) for k in (0, 1))
        out.append((name, kinds[0], view) + judge(view, kinds[0], reach))
    return out, bare


def main(args):
    canvas = build()
    rows, bare = survey(canvas)
    found, drawn = [], set()
    for name, kind, view, text, wrong in rows:
        if "check" not in args and kind not in drawn:
            drawn.add(kind)
            print(f"\n{kind} in the {name}, {view.w} x {view.h} px ({View.drawing.__doc__}):\n")
            print(view.drawing() + "\n")
        print(f"{name}: {kind}. {text}")
        found += [f"{name}, {kind}: {line}" for line in wrong]
    print(f"left bare: {'; '.join(bare) or 'none'}")
    passage(canvas, door_table(), found)
    lights(found)
    settled(found)
    displays(canvas, found)
    print("\n".join(found) if found else f"fit: {len(rows)} dressed openings, nothing found")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
