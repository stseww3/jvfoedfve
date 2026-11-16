"""The material board (ART-PLAN 6.4, milestone M1): every block of the occupancy table on one board,
each material as a wall of eight by eight with its stairs, slabs and low walls at the foot, under
the light of the sky line.

Five tiers, each stepped back and up so that one picture holds them all; from the front:

    ground    what the observatory stands on: the mountain's rock, snow lying on it, the paving
              with the emblem let into it in thin brass line, the tones of the cloud sea (a bank
              of them, and a row of them let into the mountain's rock where the snow ends).
              The one tier whose floor is part of the show, so it is the lowest: the camera looks
              down on it. It has floor only where something lies on it: a shelf as deep as the
              mountain and the bank, and under the emblem a tongue as long as the meridian runs
    pieces    doors, hatches, bars, pipes, lamps, the brass pieces, signs: against fine stone, as
              they stand on the building
    stone     the four grey-white stones, the stones used as the game draws them, and one wall that
              puts them together as a facade does (plinth, rough base, string course, fine wall
              with sunk panels and emblems)
    metal     cast iron, verdigris, old copper, brass
    glass     the furnace window as the power house has it; the six windows shoulder to shoulder
              in one front of fine stone; the instrument panels; the woods

Repainted blocks show whatever the material packages paint today (stand-ins until a family is
painted); the other blocks are the game's. A lamp row stands at the foot of every tier except in
front of the windows, so each wall runs from lamp light at its base to sky light at its top. On
the ground tier there are two lamps: one at the far end of the bare rock, one before the marker
stone of the emblem. Snow and cloud are seen under the sky alone, as they lie on the mountain:
lamplight() counts what lamp light can come to them.

    python -m scenes.obs_mat_board        writes shots.json from the layout below
    python -m scenes.obs_mat_board plan   prints the ground tier from above, what the board lacks
                                          and the lamp light on snow and cloud

Versions are compared by scenes of their own (obs_mat_board_<tag>): the same board, the shots of
compare(), with write_pack() calling pack() for the versions wanted.
"""
import math

from artkit.blocks import st
from artkit.canvas import Canvas

from scenes import obs_mat_panels as panels_scene
from scenes.obs import sky
from scenes.obs.common import blocks as B
from scenes.obs.materials import _board
from scenes.obs.materials import _kit as K

BIOME = "obs_blue"
TIME = 14000                    # the default light version; 18000 and 12900 are the other two
FOV, ASPECT = 77.0, 16.0 / 9.0  # a shot's angle of view (vertical) and shape, as build/render.py takes it
DOWN = 27.0                     # the picture of the whole board looks this far down: at this angle the
#                                 board fills the picture both ways and the far walls are largest
N = 8                           # a wall is N by N
PITCH = N + 2                   # x from one wall to the next
WALLS = 8                       # the board is this many walls wide
RISE, BACK = 10, 12             # each tier stands this much higher and further back
SHELF = 12                      # the ground tier's floor comes this far forward of its walls ...
FRONT = 20                      # ... and under the emblem this far: there is floor only where something lies on it
FLOOR = B.SLATE_SMOOTH.block    # dark and plain: floors and the risers behind the walls
LAMP = 13
VERSIONS = {}                   # material package -> version; the default of every package when empty

# the ground tier: x of each thing
ROCK_AT, LEDGES_AT, SNOW_AT, INLAY_AT, CLOUD_AT = 0, PITCH, 2 * PITCH, 3 * PITCH, 5 * PITCH
TONES_AT, TONE = 8, 4           # the row of cloud tones in the mountain's rock: its first x, a tone's width
STRIP = B.TUFF_SMOOTH.block     # the paving's light stone: the meridian's flanks, the seat's border
SEAT = B.SLATE_TILE.block       # its darkest: under the emblem
EMBLEM_R = 5                    # the smallest ring that keeps a clear cell between ring, meridian and star
EMBLEM_STAR = (2, -2)           # east and south of the middle: inside the ring, to the upper right
RUN = 3                         # the meridian runs this far out of the seat, between its two flanks


PILASTERS = (2, 5)              # the two pilaster lines of the wall that puts the stones together


def together(c, x, y, z):
    """The stones in the order the main front stacks them (main/facade), flat and small: slate
    plinth, two courses of rough stone, the string course standing forward, fine stone above. On a
    pilaster line the fine stone runs up to an emblem block, the only place the front has one;
    between the lines a sunk panel under where a window stands, and the frieze of sunk panels."""
    c.box(x, y, z, x + N - 1, y, z, B.SLATE_BRICK.block)
    c.box(x, y + 1, z, x + N - 1, y + 2, z, B.ASHLAR_ROUGH.block)
    c.box(x, y + 3, z, x + N - 1, y + N - 1, z, B.ASHLAR_FINE.block)
    c.box(x, y + 3, z + 1, x + N - 1, y + 3, z + 1, st(B.ASHLAR_FINE.slab, type="top"))
    for dx in range(N):
        if dx in PILASTERS:
            c.set(x + dx, y + N - 1, z, B.ASHLAR_EMBLEM)
        else:
            c.set(x + dx, y + 4, z, B.ASHLAR_PANEL.block)
            c.set(x + dx, y + N - 1, z, B.ASHLAR_PANEL.block)


def furnace(c, x, y, z):
    """The furnace window as a boiler bay of the power house has it (site/powerhouse), flat and
    small: tuff brick, a sill of polished tuff, the three rows that glow as one sheet, the sill row
    first, under three rows of dark glass. There are no panes of it."""
    rows = len(B.WINDOW_FURNACE)
    c.box(x, y, z, x + N - 1, y + N - 1, z, B.TUFF_BRICK.block)
    c.box(x + 1, y, z, x + N - 2, y, z, B.TUFF_SMOOTH.block)
    for row, glass in enumerate(B.WINDOW_FURNACE):
        c.box(x + 1, y + 1 + row, z, x + N - 2, y + 1 + row, z, glass.block)
    c.box(x + 1, y + 1 + rows, z, x + N - 2, y + N - 2, z, B.WINDOW_DARK.block)


def instruments(c, x, y, z):
    """The sixteen panels as a cabinet wall: a riveted plinth, the bay that materials/panels sets
    out in its test scene (every kind is in it; the rules it is set out by are in that scene's
    note), plain plate above."""
    assert panels_scene.WIDE == N and panels_scene.HIGH < N - 1
    c.box(x, y, z, x + N - 1, y, z, B.IRON_RIVETED.block)
    c.box(x, y + 1 + panels_scene.HIGH, z, x + N - 1, y + N - 1, z, B.IRON_PLATE)
    panels_scene.bay(c, x, y + 1, z)


def woods(c, x, y, z):
    """The three woods side by side, the dark one widest: it carries the panelling. At the foot of
    each its stair and its slab."""
    c.box(x, y, z, x + 3, y + N - 1, z, B.DARK_WOOD.block)
    c.box(x + 4, y, z, x + 5, y + N - 1, z, B.FLOOR_WOOD.block)
    c.box(x + 6, y, z, x + N - 1, y + N - 1, z, B.PALE_WOOD.block)
    for dx in range(2):
        for dy in range(2):
            c.set(x + dx, y + dy, z + 1, st(B.WAINSCOT, facing="south", open="true"))
    for dx, wood in ((2, B.DARK_WOOD), (4, B.FLOOR_WOOD), (6, B.PALE_WOOD)):
        c.set(x + dx, y, z + 1, st(wood.stairs, facing="north"))
        c.set(x + dx + 1, y, z + 1, st(wood.slab, type="bottom"))


def copper(c, x, y, z):
    """Old copper: the cut plate with its steps, two courses of the plain plate on top."""
    _board.wall(c, B.OLD_COPPER_CUT, x, y, z)
    c.box(x, y + N - 2, z, x + N - 1, y + N - 1, z, B.OLD_COPPER)


def verdigris(c, x, y, z):
    """Verdigris as the game draws it: cut plates, a darker streak, the plain and the cast block; at
    the foot the steps of the cut plate and, last, a stair and a slab of the streak."""
    _board.wall(c, B.VERDIGRIS_CUT, x, y, z)
    c.box(x, y + 4, z, x + N - 1, y + 5, z, B.VERDIGRIS_STREAK.block)
    c.box(x, y + N - 2, z, x + 3, y + N - 1, z, B.VERDIGRIS)
    c.box(x + 4, y + N - 2, z, x + N - 1, y + N - 1, z, B.VERDIGRIS_CAST)
    c.set(x + 6, y, z + 1, st(B.VERDIGRIS_STREAK.stairs, facing="north"))
    c.set(x + 7, y, z + 1, st(B.VERDIGRIS_STREAK.slab, type="bottom"))


def inlay(c, x, y, z):
    """The paving and the thin brass line in it: the emblem (ring, meridian, star) on a seat of the
    darkest slate bordered with the light stone, the meridian running on out of the seat between two
    flanks of the light stone, as the front court lays it. Where the line ends at the back stands
    the court's marker stone; beside it the paving stone's own stairs, slabs and low walls. One
    lamp, before the marker, on the meridian: the far half of the emblem is lamp-lit, the near half
    lies under the sky, and the lamp's light is spent where it comes to the snow on one side and
    the cloud on the other (lamplight()). Three whole cells of brass plate beside the seat, to
    compare. Two walls wide. The seat is deeper than the tier's floor: the floor comes forward
    under it as a tongue, a cell clear of it."""
    half = EMBLEM_R + 2                         # the ring, a clear cell, the border
    mx, az = x + half + 1, z + half + 1
    c.box(mx - half - 1, y - 1, z + SHELF + 1, mx + half + 1, y - 1, z + FRONT, FLOOR)
    c.box(mx - half, y - 1, az - half, mx + half, y - 1, az + half, STRIP)
    c.box(mx - half + 1, y - 1, az - half + 1, mx + half - 1, y - 1, az + half - 1, SEAT)
    c.box(mx - 1, y - 1, az + half + 1, mx + 1, y - 1, az + half + RUN, STRIP)
    _board.emblem(c, mx, y, az, EMBLEM_R, EMBLEM_STAR, az - half, az + half + RUN)
    c.set(mx, y, z, B.ASHLAR_EMBLEM)
    c.set(mx, y + 1, z, st(B.ASHLAR_PANEL.slab, type="bottom"))
    c.box(mx + half + 1, y, az - 1, mx + half + 1, y, az + 1, B.BRASS_INLAY)
    for dx in (-5, -4):
        c.set(mx + dx, y, z, st(B.SLATE_SMOOTH.stairs, facing="north"))
    for dx in (-2, 2):
        c.set(mx + dx, y, z, st(B.SLATE_SMOOTH.slab, type="bottom"))
    c.set(mx + 4, y, z, st(B.SLATE_SMOOTH.wall, east="low", up="true"))
    c.set(mx + 5, y, z, st(B.SLATE_SMOOTH.wall, west="low", up="true"))
    c.set(mx, y + 1, z + 2, st(B.LIGHT, level=LAMP - 1))     # a level under a wall's lamp: at 13, two come to the drift


def ground(c, x, y, z):
    """The mountain (rock, a cliff with snow on its ledges, snow), the paving, the cloud sea. The
    mountain stands on its own rock, not on the board's floor. Near the front edge of that rock the
    five tones of the cloud are let into it in a row, dark to light, the lightest two before the end
    of the drift: snow, rock and cloud in one plane under the sky alone, as the mountain has them
    where it goes down into the sea. Let in, not laid on: the tones have no shading of their own, so
    a block of one standing on the rock shows as a bent chip, and level with the rock as a plain
    patch of its tone, with rock on all four sides to read it against."""
    c.box(x - 1, y - 1, z, x + SNOW_AT + N, y - 1, z + SHELF, B.ROCK_COBBLED.block)
    _board.rock(c, x + ROCK_AT, y, z)
    _board.ledges(c, x + LEDGES_AT, y, z)
    _board.snow(c, x + SNOW_AT, y, z, N)
    for i, block in enumerate(B.CLOUD):
        c.box(x + TONES_AT + TONE * i, y - 1, z + SHELF - 2, x + TONES_AT + TONE * (i + 1) - 1, y - 1, z + SHELF - 1, block)
    inlay(c, x + INLAY_AT, y, z)
    _board.bank(c, x + CLOUD_AT, y, z, 3 * PITCH - 2, SHELF - 1)
    c.set(x + ROCK_AT, y + 1, z + 4, st(B.LIGHT, level=LAMP))        # one, at the end away from the snow


def pieces(c, x, y, z):
    """The shaped blocks in front of a fine stone wall, each on its own two cells: the iron pieces in
    two groups, then the brass family and the signs. A vanilla iron piece stands a cell from the
    repainted one it is compared with."""
    c.box(x, y, z - 1, x + width(), y + 3, z - 1, B.ASHLAR_FINE.block)
    lifted = _Lifted(c, y)
    for dx, put, block in IRON:
        put(lifted, block, x + dx, z)
    _board.brass(lifted, x + BRASS_AT, z, staged=False)
    _board.hung(c, x + HUNG_AT, y, z)
    for lx in range(x + 1, x + width(), 4):
        c.set(lx, y + 1, z + 3, st(B.LIGHT, level=LAMP))     # no further forward: the snow wall's top is below


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
    ("ground", []),             # no walls of eight by eight in a row: see ground()
    ("pieces", []),             # no walls: one row of small things, see pieces()
    ("stone", [("slate_brick", _block(B.SLATE_BRICK), True), ("rough", _block(B.ASHLAR_ROUGH), True),
               ("fine", _block(B.ASHLAR_FINE), True), ("together", together, True),
               ("panel", _block(B.ASHLAR_PANEL), True), ("tuff_brick", _block(B.TUFF_BRICK), True),
               ("slate_tile", _block(B.SLATE_TILE), True), ("tuff_smooth", _block(B.TUFF_SMOOTH), True)]),
    ("metal", [("iron_plate", _block(B.IRON_PLATE), True), ("iron_riveted", _block(B.IRON_RIVETED), True),
               ("iron_cast", _block(B.IRON_CAST), True), ("iron_grate", _block(B.IRON_GRATE), True),
               ("verdigris", verdigris, True), ("old_copper", copper, True),
               ("brass_plate", _block(B.BRASS_PLATE), True), ("brass_pattern", _block(B.BRASS_PATTERN), True)]),
    ("glass", [("furnace", furnace, False),
               ("window_lit", _window(B.WINDOW_LIT), False), ("window_curtain", _window(B.WINDOW_CURTAIN), False),
               ("window_frosted", _window(B.WINDOW_FROSTED), False), ("window_dark", _window(B.WINDOW_DARK), False),
               ("window_blind", _window(B.WINDOW_BLIND), False), ("skylight", _window(B.SKYLIGHT), False),
               ("instruments", instruments, True), ("woods", woods, True)]),
]
ROWS = {"ground": ground, "pieces": pieces}      # the tiers that are laid out by a function of their own
# x of each wall of a tier that does not stand its walls a PITCH apart. The glass tier holds nine: the
# six windows stand shoulder to shoulder as one front (frame against frame, a pier of two between two
# windows), which leaves the furnace window a place of its own at the far end from the lamps of the
# instrument wall; the skylight, the instruments and the woods stand where a PITCH puts them.
PLACES = {"glass": (0,) + tuple(PITCH + N * i for i in range(5)) + (5 * PITCH, 6 * PITCH, 7 * PITCH)}
# The row of small things: x of each. The groups stand apart by what a close shot needs to hold one
# whole and nothing of the next: the lines and the openings, the bars and the lamps, the brass.
IRON = ((2, _board.door, B.IRON_DOOR), (6, _board.hatch, B.IRON_HATCH), (10, _board.rod, B.IRON_ROD),
        (14, _board.pipe, B.IRON_PIPE), (17, _board.pipe, B.VANILLA_CHAIN),
        (23, _board.run, B.IRON_BARS), (26, _board.run, B.VANILLA_BARS), (30, _board.bulb, B.IRON_BULB),
        (34, _board.lantern, B.IRON_LANTERN))
BRASS_AT = 42                   # where the brass pieces start
HUNG_AT = BRASS_AT + 31         # ... and the two signs on a bracket, after them


def at(tier):
    """(y of its floor's top, z of its walls) for a tier, by number or by name."""
    k = tier if isinstance(tier, int) else [name for name, _ in TIERS].index(tier)
    return RISE * k, -BACK * k


def width():
    return WALLS * PITCH - 2


def places(tier):
    """x of each wall of a tier, left to right."""
    name, walls = TIERS[tier] if isinstance(tier, int) else next(t for t in TIERS if t[0] == tier)
    xs = PLACES.get(name) or tuple(i * PITCH for i in range(len(walls)))
    assert len(xs) == len(walls) and all(b - a >= N for a, b in zip(xs, xs[1:] + (width() + 2,))), name
    return xs


def build():
    c = Canvas()
    w = width()
    for k, (name, walls) in enumerate(TIERS):
        y, z = at(k)
        c.box(-1, y - 1, z - 1, w, y - 1, z + (SHELF if k == 0 else BACK - 2), FLOOR)   # the floor, up to the tier below
        c.box(-1, y, z - 1, w, y + RISE - 2, z - 1, FLOOR)                              # the riser behind the walls
        if name in ROWS:
            ROWS[name](c, 0, y, z)
        for x, (_, put, lamp) in zip(places(k), walls):
            put(c, x, y, z)
            if lamp:
                for dx in (1, 5):
                    c.set(x + dx, y + 1, z + 4, st(B.LIGHT, level=LAMP))
    return c


def build_models():
    return {}           # blocks only


def write_pack(pack_dir):
    return pack(pack_dir, **VERSIONS)


def pack(pack_dir, **versions):
    """The materials in the versions wanted, and the sky's pack with them: the board stands in the
    map's hour, and without the sky's pack the game's own sun is in its sky, a white and yellow
    square low in the west."""
    return list(K.pack_with(pack_dir, **versions) or []) + list(sky.pack(pack_dir) or [])


UNSEEN = (B.BARRIER,)       # in the occupancy table and nothing to look at: the collision of a door made of models


def lacking(c=None):
    """(repainted, vanilla): the blocks of the occupancy table that are not on the board. The card
    wants the first list empty; the second is kept empty too, so the board is the whole table,
    all but what draws nothing (UNSEEN; the invisible lamp does stand on the board, as its lamps)."""
    placed = {state.partition("[")[0] for state in (c or build()).b.values()}
    return ([b for b in B.ids(B.REPAINTED) if b not in placed],
            [b for b in B.ids(B.VANILLA) if b not in placed and b not in UNSEEN])


GLOWS = {B.LIGHT: None, B.IRON_LANTERN: 15, B.IRON_BULB: 15}    # what gives light: the most it gives (None: its level)


def lamplight(c=None):
    """(level, cell): the most lamp light that can come to snow or cloud. Counted for every cell of
    either and the six cells beside it, whole blocks of stone, snow and cloud left out (no light is
    in them); a level less for every cell from the lamp, as if nothing stood in the light's way: so
    it is never less than what the game gives, and on the open ground tier it is what the game
    gives. The board keeps it at 1 or less, which no picture shows (with 4 levels on it the drift
    measured a quarter more red at that end; with 1 its two ends measure the same): snow and cloud
    are seen under the sky alone, as they lie on the mountain."""
    c = c or build()
    pale = set(B.CLOUD) | {B.SNOW, B.SNOW_LAYER}
    whole = {e.block for e in B.VANILLA + B.REPAINTED[:3] if isinstance(e, B.Family)} | {B.ROCK_DEEPSLATE, B.SNOW, *B.CLOUD}
    lamps, cells = [], set()
    for (x, y, z), state in c.b.items():
        name, _, props = state.partition("[")
        if name in GLOWS:
            lamps.append((x, y, z, GLOWS[name] or int(props.partition("level=")[2].rstrip("]"))))
        elif name in pale:
            cells.update(((x, y, z), (x - 1, y, z), (x + 1, y, z), (x, y - 1, z), (x, y + 1, z), (x, y, z - 1), (x, y, z + 1)))
    cells = [cell for cell in cells if c.name(*cell) not in whole]
    return max(((level - abs(x - lx) - abs(y - ly) - abs(z - lz), (x, y, z))
                for x, y, z in cells for lx, ly, lz, level in lamps), default=(0, None))


def shots():
    """The whole board in the three light versions; each tier in two halves from where a material
    has to be told at a glance; the walls two by two from near; the ground tier's things one by one,
    the emblem from above and from a walker's height; the small pieces close."""
    out, w = [], width()

    def shot(name, pos, look_at, time=TIME):
        out.append({"name": name, "pos": [round(v, 1) for v in pos], "look_at": [round(v, 1) for v in look_at],
                    "time": time})

    for name, time in (("all", TIME), ("all_b", 18000), ("all_c", 12900)):
        shot(name, *whole(DOWN), time)
    for k, (tier, walls) in enumerate(TIERS):
        y, z = at(k)
        if tier == "ground":
            # the mountain on its rock, from the faces' top to the rock's front edge, the row of cloud
            # tones in it: steep enough to keep the tier above out of it but for its rim
            x = (SNOW_AT + N) / 2.0
            shot("ground_left", (x, y + 13.0, z + SHELF + 5.5), (x, y + 3.0, z + 5.0))
            # the paving and the cloud, from above: the whole seat and the whole bank
            x = (INLAY_AT + w) / 2.0 - 1.0
            shot("ground_right", (x, y + 16.0, z + FRONT + 7.0), (x, y, z + 7.0))
            # far and high enough to have the snow at the cliff's foot in the picture, and the wall's top
            shot("ground_rock", (LEDGES_AT - 1.0, y + 5.5, z + 10.5), (LEDGES_AT - 1.0, y + 3.0, z))
            # snow between rock and cloud: the wall, the drift down to its last thin layer, the bare
            # rock it ends on, the cloud's two lightest tones before it and the rock again
            shot("ground_snow", (SNOW_AT + N / 2.0, y + 6.0, z + SHELF + 4.0), (SNOW_AT + N / 2.0, y + 0.5, z + 5.5))
            mx, az = INLAY_AT + EMBLEM_R + 3.5, z + EMBLEM_R + 3.5
            # the emblem nearly in plan, the ring a ring: the seat from the marker to the end of the run,
            # the drift's edge on one side of it and the bank's foot on the other
            shot("ground_inlay", (mx, y + 13.5, az + 5.0), (mx, y, az + 1.5))
            shot("ground_inlay_walk", (mx + 3.0, y + 1.7, az + EMBLEM_R + 3.5), (mx - 0.5, y, az))
            x = CLOUD_AT + (w - CLOUD_AT) / 2.0
            shot("ground_cloud", (x, y + 8.0, z + SHELF + 7.0), (x, y + 1.5, z + 4.0))
            continue
        xs = places(k) or tuple(i * PITCH for i in range(WALLS))            # a row of small things: as if of walls
        left = [x for x in xs if x + N / 2.0 < w / 2.0]                    # the walls of the left half
        right = xs[len(left):]
        joined = right[0] - left[-1] == N           # no gap where the row is cut: frame stands against frame
        if joined:
            right = (left[-1],) + right             # ... and the wall at the cut is in both halves
        wide = math.tan(math.radians(FOV) / 2.0) * ASPECT       # half a picture's width, a cell from the camera
        for half, group in (("left", left), ("right", right)):
            # Four walls a PITCH apart from 16.5: from there the low walls that stand two cells forward
            # of a wall's right end are in the picture too. Small things stand nearer their wall. More
            # walls than four from where they are in the picture with a cell and a half to spare.
            span = group[-1] + N - group[0]
            back = max(15.5 if tier == "pieces" else 16.5, 1.0 + (span / 2.0 + 1.5) / wide)
            x = (group[0] + group[-1] + N) / 2.0                           # the middle of its walls
            if joined:      # the picture ends on the pier, 0.6 past the half's last frame: not in the next window's glass
                x = group[-1] + N + 0.6 - (back - 1.0) * wide if half == "left" else group[0] - 0.6 + (back - 1.0) * wide
            shot(f"{tier}_{half}", (x, y + 5.0, z + back), (x, y + 4.0, z))
        # two by two, counted from the right; with an odd number the first wall is seen beside the second.
        # From 9: the low walls at the right wall's foot are in the picture
        for i in sorted({max(i, 0) for i in range(len(walls) - 2, -2, -2)}):
            x = (xs[i] + xs[i + 1] + N) / 2.0                              # between the two walls
            shot(f"{tier}_{walls[i][0]}", (x, y + 4.5, z + 9.0), (x, y + 4.0, z))
    # The small things close, a group to a picture, all from the same distance: the nearest that holds
    # the signs. Each stands where its group is whole and nothing of the next group is in the picture;
    # only the brass hatch and the wall the signs are on stand a single cell apart, and each picture
    # of the two has an edge of the other's.
    y, z = at("pieces")
    for name, x in (("pieces_iron", 10.5), ("pieces_iron_2", 30.2), ("pieces_brass", BRASS_AT + 7.8),
                    ("pieces_signs", BRASS_AT + 27.0)):
        shot(name, (x, y + 2.6, z + 8.0), (x, y + 1.5, z))
    return out


def whole(down, margin=0.06):
    """(pos, look_at) of the nearest stand on the board's middle line from which a picture looking
    `down` degrees below the level holds the whole board, every corner keeping `margin` of the half
    picture clear of the edge. Worked in the plane of the board's side view, where the camera's up
    and forward are two axes: a corner at (u, f) is in the picture of a camera at (cu, cf) when
    |u - cu| <= t (f - cf), t the tangent of half the angle of view less the margin."""
    p = math.radians(down)
    up, fwd = (math.cos(p), -math.sin(p)), (-math.sin(p), -math.cos(p))         # as (y, z)
    t = (1.0 - margin) * math.tan(math.radians(FOV) / 2.0)
    outline = [(0.0, FRONT + 1.0)]                                              # the side view: (y, z)
    for k in range(len(TIERS)):
        y, z = at(k)
        outline += [(float(y), float(z)), (y + RISE - 1.0, z - 1.0)]            # a tier's foot, its riser's top
    pts = [(y * up[0] + z * up[1], y * fwd[0] + z * fwd[1]) for y, z in outline]
    cf = (min(u + t * f for u, f in pts) - max(u - t * f for u, f in pts)) / (2.0 * t)
    cf = min(cf, min(f for _, f in pts) - (width() / 2.0 + 1.0) / (t * ASPECT))    # ... and wide enough
    cu = (max(u - t * (f - cf) for u, f in pts) + min(u + t * (f - cf) for u, f in pts)) / 2.0
    mid, cy, cz = width() / 2.0, cu * up[0] + cf * fwd[0], cu * up[1] + cf * fwd[1]
    return (mid, cy, cz), (mid, cy + 60.0 * fwd[0], cz + 60.0 * fwd[1])


def compare(*tiers):
    """The shots a scene that compares versions takes: the whole board in its three lights and the
    shots of the named tiers, each the twin of the master board's shot of the same name."""
    return [s for s in shots() if s["name"].split("_")[0] in ("all",) + tiers]


def plan(c=None, y=0):
    """The cells at height y from above, one letter a cell (north at the top), for reading a layout
    without a picture: # rock, s snow, c cloud, = brass line, + crossing, * star, o brass plate,
    t light stone, d dark stone, p the paving stone's shaped blocks, m marker, L lamp (one above),
    . the board's floor."""
    c = c or build()
    w = width()
    letters = {B.BRASS_LINE: "=", B.BRASS_CROSS: "+", B.BRASS_STAR: "*", B.BRASS_INLAY: "o", B.SNOW: "s",
               B.SNOW_LAYER: "s", B.ASHLAR_EMBLEM: "m", STRIP: "t", SEAT: "d", FLOOR: "."}
    letters.update({block: "c" for block in B.CLOUD})
    letters.update({block: "#" for block in B.ids(_board.SHAPED_ROCKS) + [B.ROCK_DEEPSLATE]})
    letters.update({block: "p" for block in B.SLATE_SMOOTH.all()[1:]})
    rows = []
    for z in range(-1, FRONT + 1):
        row = ""
        for x in range(-1, w + 1):
            if c.name(x, y + 1, z) == B.LIGHT:
                row += "L"
                continue
            for dy in (0, -1):
                name = c.name(x, y + dy, z)
                if name:
                    row += letters.get(name, "?")
                    break
            else:
                row += " "
        rows.append(row)
    return "\n".join(rows)
