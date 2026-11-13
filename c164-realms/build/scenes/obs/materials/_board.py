"""Sample boards: repainted blocks set out to be looked at. The test scenes of the material packages
are put together from these pieces.

Everything stands on a floor at y = -1 in a row along x at one z, and is seen from the south. A
specimen is at most two blocks wide; a pair is a repainted block with, right beside it, the vanilla
block it shares its model and texture files with -- the one that must not have changed.
"""
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


def brass(c, x, z):
    """The brass family (bamboo) and the small pieces."""
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
