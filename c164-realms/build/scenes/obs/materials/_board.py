"""Sample boards: repainted blocks set out to be looked at. The test scenes of the material packages
are put together from these pieces.

Everything stands on a floor at y = -1 in a row along x at one z, and is seen from the south. A
specimen is at most two blocks wide; a pair is a repainted block with, right beside it, the vanilla
block it shares its model and texture files with -- the one that must not have changed.
"""
import math

from artkit.blocks import st

from ..common import blocks as B

FLOOR = B.TUFF_SMOOTH.block         # vanilla, neutral
BACK = B.TUFF_BRICK.block
BASE = B.TUFF.block                 # something to stand on or hang from
PAIR = 5                            # x a pair takes: two specimens of two, and a gap


def twin(block):
    """The vanilla block that shares the files of a repainted copper block: the waxed twin of an
    oxidized one (verdigris), the unwaxed twin of waxed exposed copper."""
    return block[6:] if block.startswith("waxed_") else "waxed_" + block


def stage(c, x0, x1, z, height=6, lamps=True):
    """Floor, a backdrop two behind, and lamps three in front of the specimens at x0..x1."""
    c.box(x0 - 1, -1, z - 2, x1 + 1, -1, z + 7, FLOOR)
    c.box(x0 - 1, 0, z - 2, x1 + 1, height - 1, z - 2, BACK)
    if lamps:
        for x in range(x0, x1 + 1, 3):
            for y in (1, 4):
                c.set(x, y, z + 3, st(B.LIGHT, level=15))


# ---- specimens: each puts one block (or family) at x, x + 1 -------------------------------------------
def cube(c, block, x, z, h=3):
    c.box(x, 0, z, x + 1, h - 1, z, block)


def family(c, fam, x, z, h=3):
    """A wall of the family's block with a step at its foot: its stairs, its slab; its wall on top."""
    c.box(x, 0, z, x + 1, h - 1, z, fam.block)
    if fam.stairs:
        c.set(x, 0, z + 1, st(fam.stairs, facing="north"))
    if fam.slab:
        c.set(x + 1, 0, z + 1, st(fam.slab, type="bottom"))
    if fam.wall:
        c.set(x, h, z, st(fam.wall, east="low", up="true"))
        c.set(x + 1, h, z, st(fam.wall, west="low", up="true"))


def door(c, block, x, z):
    for dx, hinge in ((0, "left"), (1, "right")):
        for y, half in ((0, "lower"), (1, "upper")):
            c.set(x + dx, y, z, st(block, facing="north", half=half, hinge=hinge))


def hatch(c, block, x, z):
    """One shut on a base, one open and upright."""
    c.box(x, 0, z, x + 1, 0, z, BASE)
    c.set(x, 1, z, st(block, half="bottom", open="false"))
    c.set(x + 1, 1, z, st(block, half="bottom", open="true", facing="north"))


def run(c, block, x, z, h=3):
    """Bars, panes, fences: two wide, joined."""
    for y in range(h):
        c.set(x, y, z, st(block, east="true"))
        c.set(x + 1, y, z, st(block, west="true"))


def pipe(c, block, x, z):
    """The chain block along all three axes."""
    c.box(x, 0, z, x, 2, z, st(block, axis="y"))
    c.set(x + 1, 2, z, st(block, axis="x"))
    c.set(x + 1, 1, z, st(block, axis="z"))


def rod(c, block, x, z):
    c.set(x, 0, z, st(block, facing="up"))
    c.set(x, 1, z, st(block, facing="up"))
    c.set(x + 1, 0, z, BASE)
    c.set(x + 1, 0, z + 1, st(block, facing="south"))
    c.set(x + 1, 1, z, st(block, facing="up"))


def bulb(c, block, x, z):
    """All four states: unlit below, lit above; powered on the right."""
    for dx, powered in ((0, "false"), (1, "true")):
        for y, lit in ((0, "false"), (1, "true")):
            c.set(x + dx, y, z, st(block, lit=lit, powered=powered))


def lantern(c, block, x, z):
    """One standing on a base, one hanging from a beam."""
    c.set(x, 0, z, BASE)
    c.set(x, 1, z, st(block, hanging="false"))
    c.set(x + 1, 2, z, BASE)
    c.set(x + 1, 1, z, st(block, hanging="true"))


def pairs(c, x, z, items):
    """items = [(specimen function, repainted, vanilla twin), ...]: each pair side by side. Returns
    the x after the last."""
    for put, ours, theirs in items:
        put(c, ours, x, z)
        put(c, theirs, x + 2, z)
        x += PAIR
    return x


# ---- stations -------------------------------------------------------------------------------------------
def twins_plates(c, x, z):
    """Cast iron beside verdigris, old copper beside exposed copper: whole blocks and families."""
    assert [twin(b) for b in B.IRON_RIVETED.all()] == B.VERDIGRIS_CUT.all()
    bare = B.Family(*[twin(b) for b in B.OLD_COPPER_CUT.all()])        # exposed cut copper, unwaxed: vanilla
    end = pairs(c, x, z, [
        (cube, B.IRON_PLATE, B.VERDIGRIS),
        (family, B.IRON_RIVETED, B.VERDIGRIS_CUT),
        (cube, B.IRON_CAST, B.VERDIGRIS_CAST),
        (cube, B.IRON_GRATE, twin(B.IRON_GRATE)),
        (cube, B.OLD_COPPER, twin(B.OLD_COPPER)),
        (family, B.OLD_COPPER_CUT, bare),
    ])
    family(c, B.VERDIGRIS_STREAK, end, z)           # the darker verdigris: not a twin, shown for the colour
    stage(c, x, end + 1, z)
    return end + 3


def twins_shapes(c, x, z):
    """The shaped iron blocks beside their waxed twins."""
    end = pairs(c, x, z, [
        (door, B.IRON_DOOR, twin(B.IRON_DOOR)),
        (hatch, B.IRON_HATCH, twin(B.IRON_HATCH)),
        (run, B.IRON_BARS, twin(B.IRON_BARS)),
        (pipe, B.IRON_PIPE, twin(B.IRON_PIPE)),
        (rod, B.IRON_ROD, twin(B.IRON_ROD)),
        (bulb, B.IRON_BULB, twin(B.IRON_BULB)),
        (lantern, B.IRON_LANTERN, twin(B.IRON_LANTERN)),
    ])
    stage(c, x, end - 2, z)
    return end + 1


def stone(c, x, z):
    """The four stones: families with their steps, the panel and the emblem above a fine wall."""
    family(c, B.ASHLAR_ROUGH, x, z)
    c.box(x + 2, 0, z, x + 3, 2, z, B.ASHLAR_ROUGH.block)
    family(c, B.ASHLAR_FINE, x + 5, z)
    c.box(x + 7, 0, z, x + 8, 2, z, B.ASHLAR_FINE.block)
    for dx, shape in ((7, "outer_right"), (8, "straight")):     # a corner of a stair, to see the treads meet
        c.set(x + dx, 0, z + 1, st(B.ASHLAR_FINE.stairs, facing="north", shape=shape))
    c.box(x + 10, 0, z, x + 12, 0, z, B.ASHLAR_FINE.block)
    c.box(x + 10, 1, z, x + 12, 1, z, B.ASHLAR_PANEL.block)
    c.box(x + 10, 2, z, x + 12, 2, z, B.ASHLAR_EMBLEM)
    c.set(x + 10, 3, z, st(B.ASHLAR_PANEL.slab, type="bottom"))
    c.set(x + 11, 3, z, st(B.ASHLAR_FINE.slab, type="bottom"))
    c.set(x + 12, 3, z, st(B.ASHLAR_ROUGH.slab, type="bottom"))
    stage(c, x, x + 12, z)
    return x + 15


def windows(c, x, z):
    """The six windows: glass blocks two by three, and panes two by three, in a fine stone frame."""
    start = x
    for role in (B.WINDOW_LIT, B.WINDOW_CURTAIN, B.WINDOW_FROSTED, B.WINDOW_DARK, B.WINDOW_BLIND, B.SKYLIGHT):
        c.box(x, 0, z, x + 1, 2, z, role.block)
        run(c, role.pane, x + 2, z)
        c.box(x, 3, z, x + 3, 3, z, B.ASHLAR_FINE.block)
        x += PAIR
    stage(c, start, x - 2, z, lamps=False)      # lit and dark glass is judged without a lamp in front
    return x + 1


def panels(c, x, z):
    """The sixteen instrument panels as a wall facing the viewer, and one turned each other way."""
    names = list(B.PANELS)
    for i, name in enumerate(names):
        c.set(x + i % 8, 1 - i // 8, z, st(B.PANELS[name], facing="south"))
    for dx, facing in ((9, "west"), (10, "north"), (11, "east")):       # only the side it faces shows the dial
        c.set(x + dx, 0, z, st(B.PANELS[names[0]], facing=facing))
    stage(c, x, x + 11, z)
    return x + 14


def brass(c, x, z, staged=True):
    """The brass family (bamboo) and the small pieces. staged=False leaves floor, backdrop and lamps
    to the caller."""
    start = x
    family(c, B.BRASS_PLATE, x, z)
    family(c, B.BRASS_PATTERN, x + 2, z)
    c.box(x + 5, 0, z, x + 5, 2, z, st(B.BRASS_COLUMN, axis="y"))
    c.set(x + 6, 2, z, st(B.BRASS_COLUMN, axis="x"))
    c.set(x + 6, 0, z, st(B.BRASS_COLUMN, axis="z"))
    run(c, B.BRASS_RAIL, x + 8, z, h=1)
    c.set(x + 10, 0, z, st(B.BRASS_GATE, facing="south"))
    door(c, B.BRASS_DOOR, x + 12, z)
    hatch(c, B.BRASS_HATCH, x + 15, z)
    # things that hang on a wall: button, shelf, signs
    c.box(x + 18, 0, z, x + 24, 2, z, BASE)
    c.set(x + 18, 1, z + 1, st(B.BRASS_BUTTON, face="wall", facing="south"))
    c.set(x + 19, 1, z + 1, st(B.BRASS_SHELF, facing="south"))
    c.set(x + 20, 1, z + 1, st(B.BRASS_SIGN[1], facing="south"))
    c.set(x + 21, 1, z + 1, st(B.ENAMEL_SIGN[1], facing="south"))
    for dx in (22, 23, 24):
        c.set(x + dx, 1, z + 1, st(B.WAINSCOT, facing="south", open="true"))
        c.set(x + dx, 0, z + 1, st(B.WAINSCOT, facing="south", open="true"))
    # standing and hanging signs, and the brass line in the floor
    c.set(x + 26, 0, z, st(B.BRASS_SIGN[0], rotation="0"))
    c.set(x + 27, 0, z, st(B.ENAMEL_SIGN[0], rotation="0"))
    c.box(x + 28, 2, z, x + 29, 2, z, BASE)
    c.set(x + 28, 1, z, st(B.BRASS_SIGN[2], rotation="0"))
    c.set(x + 29, 1, z, st(B.ENAMEL_SIGN[2], rotation="0"))
    c.box(x + 5, 0, z + 2, x + 16, 0, z + 2, B.BRASS_INLAY)
    if staged:
        stage(c, start, x + 29, z)
    return x + 32


def clouds(c, x, z):
    """The five tones of the cloud sea, dark to light, and a small bank of them: the darkest at the
    foot, the lightest on the crest. No lamps: a cloud is lit by the sky alone."""
    for i, block in enumerate(B.CLOUD):
        c.box(x + 3 * i, 0, z, x + 3 * i + 1, 2, z, block)
    x0, tones = x + 16, len(B.CLOUD)
    for i, block in enumerate(B.CLOUD):                 # layer i is 2 * (tones - i) - 1 wide, stepping back
        c.box(x0 + i, i, z - 1, x0 + 2 * tones - 2 - i, i, z + tones - 1 - i, block)
    stage(c, x, x0 + 2 * tones - 2, z, lamps=False)
    return x0 + 2 * tones + 1


# ---- the material board: walls of eight by eight ------------------------------------------------------
def steps(c, fam, x, y, z):
    """The shaped blocks of a family in a row of eight at the foot of its wall: two stairs to climb
    towards the wall, two slabs, two pieces of its low wall."""
    if fam.stairs:
        c.set(x + 1, y, z, st(fam.stairs, facing="north"))
        c.set(x + 2, y, z, st(fam.stairs, facing="north"))
    if fam.slab:
        c.set(x + 4, y, z, st(fam.slab, type="bottom"))
        c.set(x + 5, y, z, st(fam.slab, type="bottom"))
    if fam.wall:
        c.set(x + 6, y, z + 1, st(fam.wall, east="low", up="true"))
        c.set(x + 7, y, z + 1, st(fam.wall, west="low", up="true"))


def wall(c, what, x, y, z, n=8):
    """An n by n wall of a block, or of a family with its shaped blocks at the foot."""
    fam = what if isinstance(what, B.Family) else None
    c.box(x, y, z, x + n - 1, y + n - 1, z, fam.block if fam else what)
    if fam:
        steps(c, fam, x, y, z + 1)


def window_wall(c, role, x, y, z, frame, n=8):
    """A window of six by six glass blocks in a stone frame, and a small screen of its panes."""
    c.box(x, y, z, x + n - 1, y + n - 1, z, frame)
    c.box(x + 1, y + 1, z, x + n - 2, y + n - 2, z, role.block)
    for dy in (0, 1):
        c.set(x + 3, y + dy, z + 2, st(role.pane, east="true"))
        c.set(x + 4, y + dy, z + 2, st(role.pane, west="true"))


def hung(c, x, y, z):
    """The two signs that hang from a bracket on the side of a post, brass and enamel: each on the
    left of a post of its own, a cell between the two. On the two sides of one post the far sign is
    half behind the post's corner for whoever does not stand straight in front. Five cells wide."""
    for dx, sign in ((0, B.BRASS_SIGN[3]), (3, B.ENAMEL_SIGN[3])):
        c.set(x + dx, y + 1, z, st(sign, facing="south"))
        c.box(x + dx + 1, y, z, x + dx + 1, y + 2, z, BASE)


# ---- the mountain: natural rock and what lies on it ------------------------------------------------
ROCKS = {"d": B.ROCK_DEEPSLATE, "c": B.ROCK_COBBLED.block, "t": B.TUFF.block, "s": B.ROCK_STONE.block,
         "a": B.ROCK_ANDESITE.block}
# A face of the mountain, top row first: beds one to three blocks thick, the dark rock below, the
# lighter above, a bed here and there running out in a lens.
STRATA = ("ssssaaaa",
          "tttttttt",
          "ttaaattt",
          "tttttttt",
          "cccddddd",
          "dddddddd",
          "ddcccccc",
          "dddddddd")
SHAPED_ROCKS = (B.ROCK_COBBLED, B.TUFF, B.ROCK_STONE, B.ROCK_ANDESITE)


def strata(c, x, y, z, rows=STRATA, shift=0):
    """A wall of the mountain's rock, its beds as the letters of `rows` have them (top row first);
    shift slides the beds sideways, so that two faces side by side are not the same picture."""
    for dy, row in enumerate(reversed(rows)):
        for dx in range(len(row)):
            c.set(x + dx, y + dy, z, ROCKS[row[(dx + shift) % len(row)]])


def rock(c, x, y, z):
    """Eight by eight of the mountain, and at its foot the shaped blocks of the four rocks that have
    them: a slab before a stair of each, climbing to the face; three pieces of low wall."""
    strata(c, x, y, z)
    for dx, fam in enumerate(SHAPED_ROCKS):
        c.set(x + dx, y, z + 1, st(fam.stairs, facing="north"))
        c.set(x + dx, y, z + 2, st(fam.slab, type="bottom"))
    walls = [fam.wall for fam in SHAPED_ROCKS if fam.wall]
    for i, block in enumerate(walls):
        sides = {"up": "true"}
        if i > 0:
            sides["west"] = "low"
        if i < len(walls) - 1:
            sides["east"] = "low"
        c.set(x + 8 - len(walls) + i, y, z + 1, st(block, **sides))


# snow on a ledge: one figure per cell along x -- 0 bare rock, 1..7 that many layers, 8 a whole block
LEDGES = (
    # (cells out from the face, blocks of rock under the ledge, the snow of each row from the face out)
    (2, 4, ("88888840", "66543200")),
    (2, 2, ("00368888", "00135665")),
    (1, 0, ("00000232",)),
)


def snow_on(c, x, y, z, depth):
    """A cell of lying snow, `depth` eighths of a block deep."""
    if depth >= 8:
        c.set(x, y, z, B.SNOW)
    elif depth > 0:
        c.set(x, y, z, st(B.SNOW_LAYER, layers=depth))


def ledges(c, x, y, z):
    """The mountain as the site builds it, small: a cliff coming forward in two ledges, snow lying
    on each in one large patch that thins towards its edge, bare rock beside it. Six cells deep."""
    strata(c, x, y, z, shift=3)
    out = 1
    for depth, height, snow in LEDGES:
        for dz in range(depth):
            if height:
                for dy in range(height):
                    row = STRATA[len(STRATA) - 1 - dy]
                    for dx in range(8):
                        c.set(x + dx, y + dy, z + out + dz, ROCKS[row[(dx + 3 + 2 * (out + dz)) % 8]])
            for dx, figure in enumerate(snow[dz]):
                snow_on(c, x + dx, y + height, z + out + dz, int(figure))
        out += depth


def snow(c, x, y, z, n=8):
    """Snow as a wall of n by n, for its sides, and a drift at its foot for its top: n rows of lying
    snow, eight layers deep against the wall and one layer at the far edge."""
    c.box(x, y, z, x + n - 1, y + n - 1, z, B.SNOW)
    for row in range(n):
        for dx in range(n):
            snow_on(c, x + dx, y, z + 1 + row, max(1, 8 - row * 8 // n))


def bank(c, x, y, z, wide, deep):
    """The tones of the cloud sea as a bank: the darkest at the foot, the lightest on the crest, each
    a step of two cells. No lamp belongs near it: a cloud is lit by the sky alone."""
    for i, block in enumerate(B.CLOUD):
        if wide - 4 * i > 0 and deep - 2 * i > 0:
            c.box(x + 2 * i, y + i, z, x + wide - 1 - 2 * i, y + i, z + deep - 1 - 2 * i, block)


# ---- the thin brass line let into the paving --------------------------------------------------------
# line() and ring() are c194's (the test scene of materials/brass-oldcopper-small, where the rules of
# laying a line are written out): a cell of BRASS_LINE joins two of its sides and its shape names
# them; the cell under a line is a whole block; a cell of line has line in exactly the two neighbours
# its shape names, so two lines never lie side by side and the star keeps a cell clear of any line.
_SIDES = {(0, -1): "north", (0, 1): "south", (-1, 0): "west", (1, 0): "east"}
_ACROSS = {"north": "south", "south": "north", "west": "east", "east": "west"}
_SHAPES = {frozenset(pair): "_".join(pair) for pair in (("north", "south"), ("east", "west"), ("south", "east"),
                                                          ("south", "west"), ("north", "west"), ("north", "east"))}


def line(cells, closed=False):
    """The thin brass line along `cells`, a path of (x, z) in which every cell touches the next by a
    side: {(x, z): block state}. The end of an open path runs straight out of its cell."""
    out = {}
    for i, (x, z) in enumerate(cells):
        sides = set()
        for j in (i - 1, i + 1):
            if closed or 0 <= j < len(cells):
                other = cells[j % len(cells)]
                sides.add(_SIDES[(other[0] - x, other[1] - z)])
        if len(sides) == 1:
            sides.add(_ACROSS[min(sides)])
        out[(x, z)] = st(B.BRASS_LINE, shape=_SHAPES[frozenset(sides)])
    return out


def ring(r):
    """A ring of radius r about (0, 0) as a closed path of cells that touch by their sides: an
    octagon, a straight run across each axis and between two runs a path that steps sideways and
    onwards by turns, which the corners of the line draw as one slant."""
    h = max(0, round(r * math.tan(math.pi / 8) - 0.5))      # the straight run: cells -h..h
    quarter = [(r, z) for z in range(h + 2)]                # the east side, from the axis to its corner cell
    x, z = r, h + 1
    while (x, z) != (h + 1, r):
        x -= 1
        quarter.append((x, z))
        z += 1
        quarter.append((x, z))
    quarter += [(x, r) for x in range(h, 0, -1)]            # the south side, back to the axis
    cells = []
    for _ in range(4):
        cells += quarter
        quarter = [(-z, x) for x, z in quarter]             # a quarter turn on
    return cells


def emblem(c, mx, y, az, r, star, z0, z1, middle=True):
    """The station's emblem in thin line, lying in the cells at y: the meridian at x = mx from z0 to
    z1, a ring of radius r about (mx, az) with a crossing where the meridian passes through it, and
    the star `star` = (east, south) of the middle. middle=False leaves the middle cell empty, for
    what stands on it (in the front court, the armillary)."""
    for z in range(z0, z1 + 1):
        if middle or z != az:
            c.set(mx, y, z, st(B.BRASS_LINE, shape="north_south"))
    for (dx, dz), state in line(ring(r), closed=True).items():
        c.set(mx + dx, y, az + dz, st(B.BRASS_CROSS, shape="north_south") if dx == 0 else state)
    c.set(mx + star[0], y, az + star[1], st(B.BRASS_STAR, shape="north_south"))
