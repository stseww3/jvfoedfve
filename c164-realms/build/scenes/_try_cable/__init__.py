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
CAST = B.IRON_CAST
PIPE = B.IRON_PIPE
ROD = B.IRON_ROD
BARS = B.IRON_BARS
HATCH = B.IRON_HATCH
TS = B.TUFF_SMOOTH
TB = B.TUFF_BRICK
SS = B.SLATE_SMOOTH
GLASS = B.SKYLIGHT.block
PANE = B.SKYLIGHT.pane


def pair(c, x, z, shaft, head=None, over=IRON):
    """The canopy's south girder as it stands: four long, tapered at its west end, on two columns."""
    c.set(x, 1, z, STAIR + "[half=top,facing=east]")
    c.set(x + 1, 1, z, over)
    c.set(x + 2, 1, z, IRON)
    c.set(x + 3, 1, z, over)
    for cx in (x + 1, x + 3):
        c.set(cx, FLOOR + 1, z, TS.block)
        top = 0 if head is None else -1
        for y in range(FLOOR + 2, top + 1):
            c.set(cx, y, z, shaft)
        if head is not None:
            c.set(cx, 0, z, head)
    for dx in range(4):                 # the roof's foot behind it, and a little glass
        c.set(x + dx, 1, z - 1, STAIR + "[facing=north]" if dx in (0, 3) else GLASS)
        c.set(x + dx, 2, z - 2, STAIR + "[facing=north]" if dx in (0, 3) else GLASS)
        c.set(x + dx, 3, z - 3, SLAB + "[type=bottom]")


def columns(c, z):
    pair(c, 0, z, SS.wall, CAST)
    pair(c, 8, z, SS.wall, None, CAST)
    pair(c, 16, z, SS.wall, None)
    pair(c, 24, z, SS.wall, IRON)
    pair(c, 32, z, TS.wall, CAST)


def truss(c, x0, z, kind):
    """A gable frame across x0..x0+4 in row z, eaves y 1, seen from the north."""
    for i in range(2):
        c.set(x0 + i, 1 + i, z, STAIR + "[facing=east]")
        c.set(x0 + 4 - i, 1 + i, z, STAIR + "[facing=west]")
    c.set(x0 + 2, 3, z, SLAB + "[type=bottom]")
    mid = range(x0 + 1, x0 + 4)
    if kind == 0:
        for x in mid:
            c.set(x, 1, z, SLAB + "[type=top]")
        c.set(x0 + 2, 2, z, PANE)
    elif kind == 1:
        for x in mid:
            c.set(x, 1, z, PIPE + "[axis=x]")
        c.set(x0 + 2, 2, z, PIPE + "[axis=y]")
    elif kind == 2:
        c.set(x0 + 1, 1, z, ROD + "[facing=west]")
        c.set(x0 + 2, 1, z, ROD + "[facing=west]")
        c.set(x0 + 3, 1, z, ROD + "[facing=east]")
        c.set(x0 + 2, 2, z, ROD + "[facing=down]")
    elif kind == 3:
        for x in mid:
            c.set(x, 1, z, BARS)
        c.set(x0 + 2, 2, z, BARS)
    elif kind == 4:
        for x in mid:
            c.set(x, 1, z, PANE)
        c.set(x0 + 2, 2, z, PANE)
    for x in (x0 - 1, x0 + 5):          # what it stands on
        for y in range(FLOOR + 1, 2):
            c.set(x, y, z, TS.block if y < 1 else IRON)
    for i in range(2):                  # a bay of glass behind it and a second frame
        for dz in (1, 2):
            c.set(x0 + i, 1 + i, z + dz, GLASS)
            c.set(x0 + 4 - i, 1 + i, z + dz, GLASS)
    for dz in (1, 2):
        c.set(x0 + 2, 3, z + dz, SLAB + "[type=bottom]")


def trusses(c, z):
    for k in range(5):
        truss(c, 8 * k, z, k)


def slab_at(h):
    if h == int(h):
        return int(h) - 1, "top"
    return int(h // 1), "bottom"


def trestle(c, x0, z, kind, n=14, h0=3.0, bents=(3, 9)):
    for i in range(n):
        x = x0 + i
        y, half = slab_at(h0 - 0.5 * i)
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
        y, half = slab_at(h0 - 0.5 * i)
        if kind == 0:
            cap = y - 1 if half == "bottom" else y
        elif kind == 1:
            cap = y - 1 if half == "top" else y - 2
        else:
            cap = y - 2
        for dz in (-1, 0, 1):
            c.set(x, cap, z + dz, IRON)
        if kind:
            for dz in (-1, 1):
                c.set(x - 1, cap, z + dz, STAIR + "[half=top,facing=east]")
                c.set(x + 1, cap, z + dz, STAIR + "[half=top,facing=west]")
        leg = SS.wall if kind == 2 else IRON
        foot = FLOOR + 1
        for yy in range(cap - 1, foot - 1, -1):
            for dz in (-1, 1):
                c.set(x, yy, z + dz, (TB.block if kind == 0 else TS.block) if yy == foot else leg)
            if yy > foot:
                c.set(x, yy, z, SLAB + "[type=top]" if (cap - yy) % 3 == 0 else BARS)


def build():
    c = Canvas()
    for x in range(-10, 50):
        for z in range(-10, 90):
            c.set(x, FLOOR, z, TB.block)
    columns(c, 0)
    trusses(c, 20)
    trestle(c, 0, 40, 0)
    trestle(c, 18, 40, 1)
    trestle(c, 0, 70, 2)
    trestle(c, 18, 70, 3)
    return c


def build_models():
    return {}


def write_pack(pack_dir):
    return materials.pack(pack_dir)
