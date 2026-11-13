"""Light board for the card sky/look: what the three light versions do to sky, stone and lamps.

Not architecture. Everything stands on a paved strip so that one walk along it answers the card's
questions (plan/packages/sky/look.md):

    wall     five bays of placeholder wall at the skeleton's storey heights, facing east like the
             main front, with lit and dark windows and the invisible lights behind the glass
             (two of level 10 behind a great window, one of level 9 behind a small one), a wash
             light before the plinth and a lamp post: is the sky darkest, the wall a mid tone,
             the windows and lamps brightest?
    cards    three rows of single blocks (dressed stone, iron plate, verdigris). Along a row the
             east and top faces stand at block light 0, 5, 7, 8, 10, 12, 14
    posts    six pillars with a lit band, 30 to 200 blocks from the "posts" camera: the fog ramp
    sky      shots of the zenith, the west (afterglow, comet), east and south

The shot list is written from VIEWS and the look's times: python -m scenes.obs_sky_look (in build/).
Lights here are placed by hand; the placement tool is the card sky/lights.
"""
import math

from artkit.canvas import Canvas
from scenes.obs import materials, sky
from scenes.obs.common import blocks as B
from scenes.obs.common import skeleton as S
from scenes.obs.sky import mood as look

BIOME = "obs_blue"
BIOME_MARGIN = 80           # the look has to reach every camera position, not only the blocks
BIOME_MARGIN_Y = 120


def write_pack(pack_dir):
    """The sky's pictures and the repainted blocks the board is built of."""
    return list(sky.pack(pack_dir) or []) + list(materials.pack(pack_dir) or [])


PAVING = B.TUFF_SMOOTH.block
STONE = B.ASHLAR_FINE.block
BAYS = 5
Z0 = -(BAYS * S.BAY) // 2            # the north-most pilaster of the board
MAIN_GLASS = (B.WINDOW_LIT, B.WINDOW_CURTAIN, B.WINDOW_LIT, B.WINDOW_DARK, B.WINDOW_FROSTED)
BASE_GLASS = (B.WINDOW_LIT, B.WINDOW_DARK, B.WINDOW_LIT, B.WINDOW_LIT, B.WINDOW_BLIND)
CARD_LEVELS = (0, 5, 7, 8, 10, 12, 14)
CARD_ROWS = ((28, STONE), (32, B.IRON_PLATE), (36, B.VERDIGRIS))
CARD_STEP = 6
CARD_Z = 44                          # the rows' middle: south of the strip, out of the wall's pictures
POSTS_FROM = (40.0, -30.0)           # the "posts" camera stands here and looks north
POST_DISTANCES = (30, 60, 90, 120, 160, 200)


def light(level):
    return f"{B.LIGHT}[level={level}]"


def _wall(c):
    z1 = Z0 + BAYS * S.BAY
    top = S.PARAPET[1]
    # the room behind the glass: back wall, ends, floors
    c.box(-3, 0, Z0 - 1, -3, S.CORNICE, z1 + 1, B.DARK_WOOD.block)
    for z in (Z0 - 1, z1 + 1):
        c.box(-2, 0, z, 0, S.CORNICE, z, STONE)
    for y in (S.STRING, S.FRIEZE):
        c.box(-2, y, Z0, -2, y, z1, STONE)
    # glass plane (x = -1) and wall plane (x = 0), solid to begin with
    c.box(-1, 0, Z0, -1, S.CORNICE, z1, STONE)
    c.box(0, S.PLINTH[0], Z0, 0, S.PLINTH[1], z1, B.SLATE_BRICK.block)
    c.box(0, S.BASE[0], Z0, 0, S.BASE[1], z1, B.ASHLAR_ROUGH.block)
    c.box(0, S.STRING, Z0, 1, S.STRING, z1, STONE)
    c.box(0, S.PANEL, Z0, 0, S.PANEL, z1, B.ASHLAR_PANEL.block)
    c.box(0, S.WINDOW[0], Z0, 0, S.FRIEZE, z1, STONE)
    c.box(0, S.CORNICE, Z0, S.DEPTH_CORNICE, S.CORNICE, z1, STONE)
    c.box(0, S.PARAPET[0], Z0, 0, top, z1, STONE)
    for k in range(BAYS + 1):                      # pilasters stand one block proud of the wall
        z = Z0 + k * S.BAY
        c.box(-2, 0, z, -2, S.CORNICE, z, STONE)   # and a cross wall behind each keeps a bay's light to itself
        c.box(1, S.PLINTH[0], z, 1, S.PLINTH[1], z, B.SLATE_BRICK.block)
        c.box(1, S.BASE[0], z, 1, S.BASE[1], z, B.ASHLAR_ROUGH.block)
        c.box(1, S.PANEL, z, 1, S.WINDOW[1], z, STONE)
        c.set(1, S.FRIEZE, z, B.ASHLAR_EMBLEM)
    for j in range(BAYS):
        za, zb = Z0 + j * S.BAY + 1, Z0 + j * S.BAY + 3
        zc = za + 1
        glass = MAIN_GLASS[j]
        c.carve(0, S.WINDOW[0], za, 0, S.WINDOW[1], zb)
        c.set(0, S.WINDOW[1], za, STONE)           # the two top corners: a hint of the arch
        c.set(0, S.WINDOW[1], zb, STONE)
        c.box(-1, S.WINDOW[0], za, -1, S.WINDOW[1], zb, glass.block)
        if glass in B.LIT_WINDOWS:
            c.set(-2, S.WINDOW[0] + 1, zc, light(10))
            c.set(-2, S.WINDOW[0] + 4, zc, light(10))
        glass = BASE_GLASS[j]
        c.carve(0, 3, za, 0, 4, zb)
        c.box(-1, 3, za, -1, 4, zb, glass.block)
        if glass in B.LIT_WINDOWS:
            c.set(-2, 3, zc, light(9))


def _lamps(c):
    # wash light two cells before the plinth of the middle bay
    c.set(3, 0, 0, light(8))
    # a lamp post eight blocks off the wall: rod, opal globe, a level-14 source on either side
    x, z = 9, -6
    for y in range(0, 4):
        c.set(x, y, z, B.IRON_ROD + "[facing=up]")
    c.set(x, 4, z, B.WINDOW_FROSTED.block)
    c.set(x - 1, 4, z, light(14))
    c.set(x + 1, 4, z, light(14))


def _cards(c):
    for x, block in CARD_ROWS:
        for i, level in enumerate(CARD_LEVELS):
            z = CARD_Z + (i - len(CARD_LEVELS) // 2) * CARD_STEP
            c.set(x, 0, z, block)
            if level:
                # one step up and east of the block: its east and top faces both read `level`
                c.set(x + 1, 1, z, light(level + 1))


def post_positions():
    """[(x, z, distance)]: fanned out so that no pillar hides the next."""
    out = []
    for i, d in enumerate(POST_DISTANCES):
        a = math.radians(-15.0 + 6.0 * i)
        out.append((int(round(POSTS_FROM[0] + d * math.sin(a))), int(round(POSTS_FROM[1] - d * math.cos(a))), d))
    return out


def _posts(c):
    for x, z, _ in post_positions():
        c.box(x - 2, S.PAVING_Y, z - 2, x + 2, S.PAVING_Y, z + 2, PAVING)
        c.box(x - 1, 0, z - 1, x + 1, 11, z + 1, STONE)
        c.box(x - 1, 8, z + 1, x + 1, 9, z + 1, B.WINDOW_LIT.block)


EYE = 1.62
VIEWS = {   # name: (eye, looks at), scene coordinates
    "wall_near": ((24, EYE, 0), (0, 9, 0)),
    "wall_side": ((12, EYE, 14), (0, 8, 0)),
    "wall_mid": ((44, EYE, 0), (0, 10, 0)),        # as far off as the stair head is from the main front
    "wall_far": ((90, EYE, 0), (0, 12, 0)),        # as far off as the cable station
    "cards": ((46, 8, CARD_Z), (32, 0.5, CARD_Z)),
    "posts": ((POSTS_FROM[0], EYE, POSTS_FROM[1]), (POSTS_FROM[0], 6, POSTS_FROM[1] - 100)),
    "west": ((-30, EYE, 0), (-130, 26, 0)),
    "comet": ((-30, EYE, 0), (-130, 110, 0)),
    "zenith": ((60, EYE, 10), (59.9, 200, 10)),
    "east": ((60, EYE, 0), (160, 12, 0)),
    "south": ((60, EYE, 0), (60, 12, 100)),
}
EVERY_LOOK = ("wall_near", "wall_mid", "wall_far", "cards", "west", "comet", "zenith")
DEFAULT_ONLY = ("wall_side", "posts", "east", "south")
TRIAL_VIEWS = {"card": ("comet",), "pink": ("west", "wall_mid"), "near": ("posts",), "far": ("posts",)}


def shots():
    """The shot list: every look from the same places, each trial where it shows, one at noon."""
    out = []

    def add(name, view, at):
        eye, target = VIEWS[view]
        out.append({"name": f"{name}_{view}", "pos": list(eye), "look_at": list(target), "time": at})

    for name in look.LOOKS:
        for view in EVERY_LOOK + (DEFAULT_ONLY if name == look.DEFAULT else ()):
            add(name, view, look.tick(name))
    for name, views in TRIAL_VIEWS.items():
        for view in views:
            add(name, view, look.tick(name))
    add("noon", "wall_near", 6000)      # the drivers' default time shows the default look
    return out


def build():
    c = Canvas()
    c.box(-8, S.PAVING_Y, -22, 96, S.PAVING_Y, 22, PAVING)
    c.box(34, S.PAVING_Y, -34, 46, S.PAVING_Y, -22, PAVING)
    c.box(22, S.PAVING_Y, 22, 50, S.PAVING_Y, CARD_Z + 22, PAVING)
    _wall(c)
    _lamps(c)
    _cards(c)
    _posts(c)
    c.entity_counts = {}
    return c
