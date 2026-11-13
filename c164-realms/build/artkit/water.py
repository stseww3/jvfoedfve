"""Where the water goes: the game's rules for running water, worked out on a canvas.

Scenes only place still water (sources); the game lets it run. run() predicts the result before
anything is placed, so a pool can be checked to catch a fall, and a previewer can draw the falls.
It follows FlowingFluid of the Java edition for water: a block of running water first tries to go
down; only where it cannot (or where it is a source) does it spread sideways, one step weaker per
block, and then only towards the nearest drop if there is one within four blocks. Two sources next
to a cell over solid ground make a third.
"""
from collections import deque

SIDES = ((1, 0), (-1, 0), (0, 1), (0, -1))
# FlowingFluid.canHoldAnyFluid: running water takes the place of things without a body, unless they
# can be waterlogged (lanterns, chains, hanging roots, glow lichen, light blocks: those stay and the
# water goes round them) or are on the game's list of exceptions (sugar cane, ladders, signs, doors).
WASHED = {
    "short_grass", "tall_grass", "fern", "large_fern", "short_dry_grass", "tall_dry_grass", "bush", "firefly_bush",
    "dead_bush", "vine", "leaf_litter", "pink_petals", "wildflowers", "dandelion", "golden_dandelion", "poppy",
    "blue_orchid", "allium", "azure_bluet", "red_tulip", "orange_tulip", "white_tulip", "pink_tulip", "oxeye_daisy",
    "cornflower", "lily_of_the_valley", "wither_rose", "torchflower", "open_eyeblossom", "closed_eyeblossom",
    "sunflower", "lilac", "rose_bush", "peony", "pitcher_plant", "brown_mushroom", "red_mushroom", "crimson_fungus",
    "warped_fungus", "crimson_roots", "warped_roots", "nether_sprouts", "sweet_berry_bush", "wheat", "carrots",
    "potatoes", "beetroots", "melon_stem", "pumpkin_stem", "attached_melon_stem", "attached_pumpkin_stem",
    "torchflower_crop", "pitcher_crop", "spore_blossom", "pale_hanging_moss", "lily_pad", "cobweb", "redstone_wire",
    "lever", "snow", "cave_vines", "cave_vines_plant", "weeping_vines", "weeping_vines_plant", "twisting_vines",
    "twisting_vines_plant", "flower_pot", "fire", "soul_fire", "nether_wart", "cocoa", "tripwire", "tripwire_hook",
}
WASHED_ENDINGS = ("_sapling", "_carpet", "torch", "_button", "_head", "_skull")
SOURCE, FALLING = 8, 9   # amounts: 1..7 running water, 8 a source, 9 falling water (counts as 8)


def washed(name):
    """Does running water take the place of this block?"""
    return name in WASHED or name.endswith(WASHED_ENDINGS) or name.startswith("potted_")


class Flow:
    def __init__(self, canvas, floor):
        self.c = canvas
        self.floor = floor            # nothing is followed below this y
        self.w = {}                   # cell -> amount, for water that is not a source
        self.src = {k for k, v in canvas.b.items() if v.startswith("water")}

    def open(self, p):
        """Can running water be in this cell?"""
        if p in self.src:
            return False
        s = self.c.b.get(p)
        return s is None or washed(s.partition("[")[0])

    def amount(self, p):
        if p in self.src:
            return SOURCE
        return self.w.get(p, 0)

    def wet(self, p):
        return p in self.src or p in self.w

    def hole(self, p):
        """Would water in cell p go down?"""
        below = (p[0], p[1] - 1, p[2])
        return below[1] >= self.floor and (self.wet(below) or self.open(below))

    def wanted(self, p):
        """What a cell that can hold water should hold, going by its neighbours (getNewLiquid)."""
        best, sources = 0, 0
        for dx, dz in SIDES:
            n = (p[0] + dx, p[1], p[2] + dz)
            a = self.amount(n)
            if a == SOURCE:
                sources += 1
            best = max(best, min(a, 8))
        below = (p[0], p[1] - 1, p[2])
        if sources >= 2 and (below in self.src or not (self.open(below) or below in self.w)):
            return SOURCE
        if self.wet((p[0], p[1] + 1, p[2])):
            return FALLING
        return max(0, best - 1)

    def slope(self, p, came, depth):
        """Steps from p to the nearest drop, looking no further than four blocks."""
        best = 1000
        for dx, dz in SIDES:
            if (dx, dz) == (-came[0], -came[1]):
                continue
            n = (p[0] + dx, p[1], p[2] + dz)
            if not self.open(n):
                continue
            if self.hole(n):
                return depth
            if depth < 4:
                best = min(best, self.slope(n, (dx, dz), depth + 1))
        return best

    def run(self, limit=400000):
        queue = deque(self.src)
        queued = set(queue)
        n = 0
        while queue and n < limit:
            n += 1
            p = queue.popleft()
            queued.discard(p)
            if p not in self.src:
                a = self.wanted(p) if self.open(p) else 0
                if a == SOURCE:
                    self.src.add(p)
                    self.w.pop(p, None)
                elif a:
                    self.w[p] = a
                elif p in self.w:
                    del self.w[p]
                if not self.wet(p):
                    self._wake(p, queue, queued)
                    continue
            below = (p[0], p[1] - 1, p[2])
            targets = []
            if below[1] >= self.floor and self.open(below) and below not in self.w:
                targets.append(below)
                if sum(self.amount((p[0] + dx, p[1], p[2] + dz)) == SOURCE for dx, dz in SIDES) >= 3:
                    targets += self._sides(p)
            elif p in self.src or not self.hole(p):
                targets += self._sides(p)
            for t in targets:
                a = self.wanted(t)
                if a == SOURCE:
                    self.src.add(t)
                    self.w.pop(t, None)
                elif a and self.w.get(t) != a:
                    self.w[t] = a
                else:
                    continue
                self._wake(t, queue, queued, itself=True)
        return self

    def _sides(self, p):
        if self.amount(p) <= 1:
            return []
        reach = {}
        for dx, dz in SIDES:
            n = (p[0] + dx, p[1], p[2] + dz)
            if self.open(n):
                reach[n] = 0 if self.hole(n) else self.slope(n, (dx, dz), 1)
        if not reach:
            return []
        least = min(reach.values())
        return [n for n, d in reach.items() if d == least]

    def _wake(self, p, queue, queued, itself=False):
        cells = [(p[0] + dx, p[1], p[2] + dz) for dx, dz in SIDES] + [(p[0], p[1] - 1, p[2]), (p[0], p[1] + 1, p[2])]
        if itself:
            cells.append(p)
        for q in cells:
            if q not in queued and (self.wet(q) or q == p):
                queue.append(q)
                queued.add(q)


def run(canvas, floor):
    """Let the water run. Returns the Flow: .w = {cell: amount} for running (1..7) and falling (9)
    water, .src = all cells that hold a source in the end."""
    return Flow(canvas, floor).run()


def falls(flow):
    """The falls as columns: {(x, z): [(top y, bottom y), ...]} for every unbroken run of falling
    water three or more blocks long."""
    cols = {}
    for (x, y, z), a in flow.w.items():
        if a == FALLING:
            cols.setdefault((x, z), []).append(y)
    out = {}
    for key, ys in cols.items():
        ys.sort(reverse=True)
        runs, start, last = [], ys[0], ys[0]
        for y in ys[1:]:
            if y != last - 1:
                runs.append((start, last))
                start = y
            last = y
        runs.append((start, last))
        runs = [r for r in runs if r[0] - r[1] >= 2]
        if runs:
            out[key] = runs
    return out
