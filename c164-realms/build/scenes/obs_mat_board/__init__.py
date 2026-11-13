"""The material board (ART-PLAN 6.4, milestone M1): every material of the map as a wall of eight by
eight with its stairs, slabs and low walls at the foot, under the light of the sky line.

Four tiers, each stepped back and up so that one picture holds them all:

    stone     the four grey-white stones, the stones used as the game draws them, and one wall that
              puts them together as a facade does (plinth, rough base, string course, fine wall
              with sunk panels and emblems)
    metal     cast iron, verdigris, old copper, brass
    glass     the six windows, the instrument panels, the woods
    pieces    doors, hatches, bars, pipes, lamps, signs

Repainted blocks show whatever the material packages paint today (stand-ins until a family is
painted); the other blocks are the game's. A lamp row stands at the foot of every tier except in
front of the windows, so each wall runs from lamp light at its base to sky light at its top.

    python -m scenes.obs_mat_board        writes shots.json from the layout below

Versions are compared by scenes of their own (obs_mat_board_<tag>): the same board and shots, with
write_pack() calling materials._kit.pack_with() for the versions wanted.
"""
from artkit.blocks import st
from artkit.canvas import Canvas

from scenes.obs.common import blocks as B
from scenes.obs.materials import _board
from scenes.obs.materials import _kit as K

BIOME = "obs_blue"
TIME = 14000                    # the default light version; 18000 and 12900 are the other two
N = 8                           # a wall is N by N
PITCH = N + 2                   # x from one wall to the next
RISE, BACK = 10, 12             # each tier stands this much higher and further back
FLOOR = B.SLATE_SMOOTH.block    # dark and plain: floors and the risers behind the walls
LAMP = 13
VERSIONS = {}                   # material package -> version; the default of every package when empty


def together(c, x, y, z):
    """The stones as a facade stacks them: slate plinth, two courses of rough stone, a projecting
    string course, fine stone above with sunk panels and two emblem blocks."""
    c.box(x, y, z, x + N - 1, y, z, B.SLATE_BRICK.block)
    c.box(x, y + 1, z, x + N - 1, y + 2, z, B.ASHLAR_ROUGH.block)
    c.box(x, y + 3, z, x + N - 1, y + 7, z, B.ASHLAR_FINE.block)
    c.box(x, y + 3, z + 1, x + N - 1, y + 3, z + 1, st(B.ASHLAR_FINE.slab, type="top"))
    for dx in (1, 2, 5, 6):
        c.set(x + dx, y + 5, z, B.ASHLAR_PANEL.block)
    for dx in (3, 4):
        c.set(x + dx, y + 7, z, B.ASHLAR_EMBLEM)


def instruments(c, x, y, z):
    """The sixteen panels twice over, as a cabinet wall: a riveted base, four rows of instruments,
    plain plate above."""
    names = list(B.PANELS)
    c.box(x, y, z, x + N - 1, y, z, B.IRON_RIVETED.block)
    c.box(x, y + 5, z, x + N - 1, y + N - 1, z, B.IRON_PLATE)
    for i in range(4 * N):
        name = names[(i * 5 + 3 * (i // 16)) % 16]        # each kind once in a pair of rows, shuffled
        c.set(x + i % N, y + 1 + i // N, z, st(B.PANELS[name], facing="south"))


def woods(c, x, y, z):
    """The three woods side by side, and the panelling in front of the dark one."""
    c.box(x, y, z, x + 2, y + N - 1, z, B.DARK_WOOD.block)
    c.box(x + 3, y, z, x + 5, y + N - 1, z, B.FLOOR_WOOD.block)
    c.box(x + 6, y, z, x + N - 1, y + N - 1, z, B.PALE_WOOD.block)
    for dx in range(3):
        for dy in range(2):
            c.set(x + dx, y + dy, z + 1, st(B.WAINSCOT, facing="south", open="true"))
    c.set(x + 3, y, z + 1, st(B.FLOOR_WOOD.stairs, facing="north"))
    c.set(x + 4, y, z + 1, st(B.FLOOR_WOOD.slab, type="bottom"))
    c.set(x + 6, y, z + 1, st(B.PALE_WOOD.stairs, facing="north"))
    c.set(x + 7, y, z + 1, st(B.PALE_WOOD.slab, type="bottom"))


def copper(c, x, y, z):
    """Old copper: the cut plate with its steps, two courses of the plain plate on top."""
    _board.wall(c, B.OLD_COPPER_CUT, x, y, z)
    c.box(x, y + N - 2, z, x + N - 1, y + N - 1, z, B.OLD_COPPER)


def verdigris(c, x, y, z):
    """Verdigris as the game draws it: cut plates, a darker streak, the plain and the cast block."""
    _board.wall(c, B.VERDIGRIS_CUT, x, y, z)
    c.box(x, y + 4, z, x + N - 1, y + 5, z, B.VERDIGRIS_STREAK.block)
    c.box(x, y + N - 2, z, x + 3, y + N - 1, z, B.VERDIGRIS)
    c.box(x + 4, y + N - 2, z, x + N - 1, y + N - 1, z, B.VERDIGRIS_CAST)


def iron_pieces(c, x, y, z):
    """The shaped iron blocks, each on its own two cells."""
    at = lambda put, block, i: put(_Lifted(c, y), block, x + 3 * i, z)      # noqa: E731
    at(_board.door, B.IRON_DOOR, 0)
    at(_board.hatch, B.IRON_HATCH, 1)
    at(_board.run, B.IRON_BARS, 2)
    at(_board.pipe, B.IRON_PIPE, 3)
    at(_board.rod, B.IRON_ROD, 4)
    at(_board.bulb, B.IRON_BULB, 5)
    at(_board.lantern, B.IRON_LANTERN, 6)
    at(_board.run, B.VANILLA_BARS, 7)
    at(_board.pipe, B.VANILLA_CHAIN, 8)


class _Lifted:
    """A canvas whose y = 0 is a tier's floor: the specimens of materials/_board.py stand on y = 0."""

    def __init__(self, c, y):
        self.c, self.y = c, y

    def set(self, x, y, z, state):
        self.c.set(x, y + self.y, z, state)

    def box(self, x1, y1, z1, x2, y2, z2, state):
        self.c.box(x1, y1 + self.y, z1, x2, y2 + self.y, z2, state)


def _block(what):
    return lambda c, x, y, z: _board.wall(c, what, x, y, z)


def _window(role):
    return lambda c, x, y, z: _board.window_wall(c, role, x, y, z, B.ASHLAR_FINE.block)


# name -> the walls of the tier, left to right: (short name, how to put it, lamp in front?)
TIERS = [
    ("stone", [("slate_brick", _block(B.SLATE_BRICK), True), ("rough", _block(B.ASHLAR_ROUGH), True),
               ("fine", _block(B.ASHLAR_FINE), True), ("together", together, True),
               ("panel", _block(B.ASHLAR_PANEL), True), ("tuff_brick", _block(B.TUFF_BRICK), True),
               ("slate_tile", _block(B.SLATE_TILE), True), ("tuff_smooth", _block(B.TUFF_SMOOTH), True)]),
    ("metal", [("iron_plate", _block(B.IRON_PLATE), True), ("iron_riveted", _block(B.IRON_RIVETED), True),
               ("iron_cast", _block(B.IRON_CAST), True), ("iron_grate", _block(B.IRON_GRATE), True),
               ("verdigris", verdigris, True), ("old_copper", copper, True),
               ("brass_plate", _block(B.BRASS_PLATE), True), ("brass_pattern", _block(B.BRASS_PATTERN), True)]),
    ("glass", [("window_lit", _window(B.WINDOW_LIT), False), ("window_curtain", _window(B.WINDOW_CURTAIN), False),
               ("window_frosted", _window(B.WINDOW_FROSTED), False), ("window_dark", _window(B.WINDOW_DARK), False),
               ("window_blind", _window(B.WINDOW_BLIND), False), ("skylight", _window(B.SKYLIGHT), False),
               ("instruments", instruments, True), ("woods", woods, True)]),
]
PIECES = len(TIERS)             # the tier of the shaped blocks stands on top


def at(tier):
    """(y of its floor's top, z of its walls) for a tier."""
    return RISE * tier, -BACK * tier


def width():
    return max(len(walls) for _, walls in TIERS) * PITCH - 2


def build():
    c = Canvas()
    w = width()
    for k in range(PIECES + 1):
        y, z = at(k)
        c.box(-1, y - 1, z - 1, w, y - 1, z + BACK - 2, FLOOR)             # the floor, up to the tier below
        c.box(-1, y, z - 1, w, y + RISE - 2, z - 1, FLOOR)                 # the riser behind the walls
    for k, (_, walls) in enumerate(TIERS):
        y, z = at(k)
        for i, (_, put, lamp) in enumerate(walls):
            put(c, i * PITCH, y, z)
            if lamp:
                for dx in (1, 5):
                    c.set(i * PITCH + dx, y + 1, z + 4, st(B.LIGHT, level=LAMP))
    y, z = at(PIECES)
    iron_pieces(c, 0, y, z)
    _board.brass(_Lifted(c, y), 30, z)
    for x in range(1, w, 4):
        c.set(x, y + 1, z + 4, st(B.LIGHT, level=LAMP))
    return c


def build_models():
    return {}           # blocks only


def write_pack(pack_dir):
    return K.pack_with(pack_dir, **VERSIONS)


def shots():
    """The whole board in the three light versions, each tier, and the walls two by two."""
    out, w = [], width()
    mid = w / 2.0
    top = at(PIECES)[0] + 4
    for name, time in (("all", TIME), ("all_b", 18000), ("all_c", 12900)):
        out.append({"name": name, "pos": [mid, top / 2.0 + 6, 44.0], "look_at": [mid, top / 2.0 - 1, -BACK * 1.5], "time": time})
    for k, (tier, walls) in enumerate(TIERS + [("pieces", [])]):
        y, z = at(k)
        out.append({"name": tier, "pos": [mid, y + 7.0, z + 30.0], "look_at": [mid, y + 3.5, z], "time": TIME})
        for i in range(0, len(walls), 2):
            x = i * PITCH + PITCH - 1.0                                    # between the two walls
            out.append({"name": f"{tier}_{walls[i][0]}", "pos": [x, y + 4.5, z + 13.0], "look_at": [x, y + 3.5, z], "time": TIME})
    y, z = at(PIECES)
    for name, x in (("pieces_iron", 13.0), ("pieces_brass", 45.0)):
        out.append({"name": name, "pos": [x, y + 3.0, z + 11.0], "look_at": [x, y + 1.5, z], "time": TIME})
    return out
