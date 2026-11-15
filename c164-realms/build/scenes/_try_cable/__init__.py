"""Scratch study (not kept): column, truss and trestle idioms side by side."""
from artkit.canvas import Canvas

from scenes.obs import materials
from scenes.obs.common import blocks as B

BIOME = "obs_blue"
BIOME_MARGIN = 100
BIOME_MARGIN_Y = 150

FLOOR = -5
IRON = B.IRON_RIVETED.block
SLAB = B.IRON_RIVETED.slab
STAIR = B.IRON_RIVETED.stairs
PIPE = B.IRON_PIPE
ROD = B.IRON_ROD
BARS = B.IRON_BARS
HATCH = B.IRON_HATCH
TS = B.TUFF_SMOOTH
TB = B.TUFF_BRICK
SS = B.SLATE_SMOOTH
GLASS = B.SKYLIGHT.block
PANE = B.SKYLIGHT.pane


def girder(c, x, z, y=1):
    for dx in (-1, 0, 1):
        c.set(x + dx, y, z, IRON)
    c.set(x - 2, y, z, STAIR + "[half=top,facing=east]")
    c.set(x + 2, y, z, STAIR + "[half=top,facing=west]")


def brackets(c, x, z, y=0):
    c.set(x - 1, y, z, STAIR + "[half=top,facing=east]")
    c.set(x + 1, y, z, STAIR + "[half=top,facing=west]")


def columns(c, z):
    def col(x, states, br=False):
        girder(c, x, z)
        for i, s in enumerate(states):
            c.set(x, FLOOR + 1 + i, z, s)
        if br:
            brackets(c, x, z)

    up = "[axis=y]"
    col(0, [TS.wall, TS.wall, PIPE + up, PIPE + up, B.IRON_CAST])
    col(6, [TS.block] + [SS.wall] * 4, br=True)
    col(12, [TS.block] + [ROD + "[facing=up]"] * 4, br=True)
    col(18, [TS.block] + [BARS] * 4, br=True)
    col(24, [TS.block] + [IRON] * 4, br=True)
    col(30, [TS.wall] + [PIPE + up] * 3 + [STAIR + "[half=top,facing=west]"])
    col(36, [TS.block] + [TS.wall] * 4, br=True)
    col(42, [SS.wall] * 5)
    col(48, [IRON] + [SS.wall] * 3 + [IRON])
    col(54, [TS.block] + [B.SLATE_TILE.wall] * 4, br=True)
    col(60, [TS.block, SS.wall, SS.wall, SS.wall, B.IRON_CAST])
    col(66, [TS.stairs + "[facing=east]"] + [SS.wall] * 4, br=True)


def truss(c, x, z0, kind):
    """A gable frame across z0..z0+4 at x, eaves y 1."""
    for i in range(2):
        c.set(x, 1 + i, z0 + i, STAIR + "[facing=south]")
        c.set(x, 1 + i, z0 + 4 - i, STAIR + "[facing=north]")
    c.set(x, 3, z0 + 2, SLAB + "[type=bottom]")
    if kind == 0:
        for z in range(z0 + 1, z0 + 4):
            c.set(x, 1, z, SLAB + "[type=top]")
        c.set(x, 2, z0 + 2, PANE)
    elif kind == 1:
        for z in range(z0 + 1, z0 + 4):
            c.set(x, 1, z, PIPE + "[axis=z]")
        c.set(x, 2, z0 + 2, PIPE + "[axis=y]")
    elif kind == 2:
        c.set(x, 1, z0 + 1, ROD + "[facing=north]")
        c.set(x, 1, z0 + 2, ROD + "[facing=north]")
        c.set(x, 1, z0 + 3, ROD + "[facing=south]")
        c.set(x, 2, z0 + 2, ROD + "[facing=down]")
    elif kind == 3:
        for z in range(z0 + 1, z0 + 4):
            c.set(x, 1, z, BARS)
        c.set(x, 2, z0 + 2, BARS)
    for z in (z0 - 1, z0 + 5):         # what it stands on
        for y in range(FLOOR + 1, 2):
            c.set(x, y, z, TS.block if y < 1 else IRON)


def trusses(c, z0):
    for k in range(4):
        truss(c, 6 * k, z0, k)
        for z in range(z0, z0 + 5):
            pass
        # a bay of glass behind it
        for i in range(2):
            c.set(6 * k + 1, 1 + i, z0 + i, GLASS)
            c.set(6 * k + 1, 1 + i, z0 + 4 - i, GLASS)
        c.set(6 * k + 1, 3, z0 + 2, SLAB + "[type=bottom]")


def top_of(h0, i):
    return h0 - 0.5 * i


def slab_at(h):
    if h == int(h):
        return int(h) - 1, "top"
    return int(h // 1), "bottom"


def trestle(c, x0, z, kind, n=14, h0=3.0, bents=(3, 9)):
    for i in range(n):
        x = x0 + i
        y, half = slab_at(top_of(h0, i))
        for dz in (-1, 1):
            if kind == 0:
                c.set(x, y, z + dz, SLAB + f"[type={half}]")
            elif kind == 1:                     # plate girder, one deep
                if half == "top":
                    c.set(x, y, z + dz, IRON)
                else:
                    c.set(x, y, z + dz, SLAB + "[type=bottom]")
                    c.set(x, y - 1, z + dz, SLAB + "[type=top]")
            else:                               # lattice girder
                c.set(x, y, z + dz, IRON if half == "top" else SLAB + "[type=bottom]")
                c.set(x, y - 1, z + dz, BARS)
                c.set(x, y - 2, z + dz, SLAB + "[type=top]")
        if half == "top":
            c.set(x, y, z, HATCH + "[half=top]")
    for i in bents:
        x = x0 + i
        y, half = slab_at(top_of(h0, i))
        if kind == 0:
            cap = y - 1 if half == "bottom" else y
        elif kind == 1:
            cap = y - 1 if half == "top" else y - 2
        else:
            cap = y - 2
        for dz in (-1, 0, 1):
            c.set(x, cap, z + dz, IRON)
        if kind in (1, 2, 3):
            for dz in (-1, 1):
                c.set(x - 1, cap, z + dz, STAIR + "[half=top,facing=east]")
                c.set(x + 1, cap, z + dz, STAIR + "[half=top,facing=west]")
        leg = IRON if kind in (0, 1) else SS.wall
        if kind == 3:
            leg = IRON
        foot = FLOOR + 1
        for yy in range(cap - 1, foot - 1, -1):
            for dz in (-1, 1):
                c.set(x, yy, z + dz, (TB.block if kind == 0 else TS.block) if yy == foot else leg)
            if yy > foot:
                if (cap - yy) % 3 == 0:
                    c.set(x, yy, z, SLAB + "[type=top]")
                else:
                    c.set(x, yy, z, BARS)


def build():
    c = Canvas()
    for x in range(-8, 80):
        for z in range(-8, 44):
            c.set(x, FLOOR, z, TB.block)
    columns(c, 0)
    trusses(c, 8)
    trestle(c, 0, 24, 0)
    trestle(c, 18, 24, 1)
    trestle(c, 36, 24, 2)
    trestle(c, 54, 24, 3, h0=4.0)
    return c


def build_models():
    return {}


def write_pack(pack_dir):
    return materials.pack(pack_dir)
