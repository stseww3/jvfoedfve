"""Scratch study (not kept), third look: trestle idioms under the thin deck."""
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
BARS = B.IRON_BARS
HATCH = B.IRON_HATCH
TS = B.TUFF_SMOOTH
TB = B.TUFF_BRICK
SS = B.SLATE_SMOOTH
N = 16
H0 = 3.5


def slab_at(h):
    if h == int(h):
        return int(h) - 1, "top"
    return int(h // 1), "bottom"


def deck(c, x0, z):
    """The thin deck as it stands: two rails of slabs, a tie in every second cell."""
    for i in range(N):
        y, half = slab_at(H0 - 0.5 * i)
        for dz in (-1, 1):
            c.set(x0 + i, y, z + dz, SLAB + f"[type={half}]")
        if half == "top":
            c.set(x0 + i, y, z, HATCH + "[half=top]")


def rail_cell(i):
    return slab_at(H0 - 0.5 * i)


def towers(c, x0, z, at=(2, 10)):
    """Lattice towers of bars, two cells by three, under a cap of four blocks."""
    deck(c, x0, z)
    for i in at:
        y, half = rail_cell(i)              # bottom type
        assert half == "bottom", i
        for k in (0, 1):
            x = x0 + i + k
            for dz in (-1, 1):
                c.set(x, y - 1, z + dz, IRON)
            c.set(x, y - 1, z, SLAB + "[type=top]")
            for yy in range(y - 2, FLOOR + 1, -1):
                for dz in (-1, 0, 1):
                    c.set(x, yy, z + dz, BARS)
            for dz in (-1, 0, 1):
                c.set(x, FLOOR + 1, z + dz, TS.block)


def bents(c, x0, z, leg, step=4, first=2, brace=True):
    """Bents close together: a cap of three blocks, two legs, bars between them."""
    deck(c, x0, z)
    for i in range(first, N, step):
        y, half = rail_cell(i)
        assert half == "bottom", i
        x = x0 + i
        for dz in (-1, 0, 1):
            c.set(x, y - 1, z + dz, IRON)
        for yy in range(y - 2, FLOOR, -1):
            foot = yy == FLOOR + 1
            for dz in (-1, 1):
                c.set(x, yy, z + dz, TS.block if foot else leg)
            if not foot and brace:
                c.set(x, yy, z, BARS)


def lattice(c, x0, z, at=(2, 10)):
    """The deck as the top chord of a lattice girder: bars under it, a chord of slabs below."""
    deck(c, x0, z)
    for i in range(N):
        y, half = rail_cell(i)
        web = y - 1
        for dz in (-1, 1):
            c.set(x0 + i, web, z + dz, BARS)
            c.set(x0 + i, web - 1, z + dz, SLAB + "[type=top]")
    for i in at:
        y, half = rail_cell(i)
        x = x0 + i
        cap = y - 2
        for dz in (-1, 0, 1):
            c.set(x, cap, z + dz, IRON)
        for yy in range(cap - 1, FLOOR, -1):
            foot = yy == FLOOR + 1
            for dz in (-1, 1):
                c.set(x, yy, z + dz, TS.block if foot else IRON)
            if not foot:
                c.set(x, yy, z, BARS)


def build():
    c = Canvas()
    for x in range(-12, 100):
        for z in range(10, 70):
            c.set(x, FLOOR, z, TB.block)
    towers(c, 0, 40)
    bents(c, 24, 40, IRON)
    bents(c, 48, 40, SS.wall)
    lattice(c, 72, 40)
    return c


def build_models():
    return {}


def write_pack(pack_dir):
    return materials.pack(pack_dir)
