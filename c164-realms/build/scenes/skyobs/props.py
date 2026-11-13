"""Custom models for the observatory island (resource pack side) and where they stand."""
from artkit import models as M
from artkit import pixelart as P

STAR = [
    "...#...",
    "...#...",
    ".#.#.#.",
    "..###..",
    "#######",
    "..###..",
    ".#.#.#.",
    "...#...",
    "...#...",
]
ARROW = [
    "...#",
    "..##",
    ".###",
    "####",
    ".###",
    "..##",
    "...#",
]
EMBLEM = [
    "..........",
    ".......o..",
    "......ooo.",
    ".bb....o..",
    "..bbb.....",
    "...bbbb...",
    "....bbbb..",
    ".....kbb..",
    "....k.k...",
    "...k...k..",
    "..........",
]


def lamp_post():
    """Timber post with a braced arm and a hanging brass lantern. Anchor: centre of the foot."""
    m = M.Model("lamp_post")
    m.box((-3, 0, -3), (3, 3, 3), P.STONE)
    m.box((-2.5, 3, -2.5), (2.5, 4, 2.5), P.STONE)
    m.box((-1.5, 4, -1.5), (1.5, 46, 1.5), P.DARK_WOOD, grain="y")
    m.box((-2, 46, -2), (2, 47, 2), P.DARK_WOOD)
    m.box((-1, 47, -1), (1, 48, 1), P.DARK_WOOD)
    m.box((-2, 12, -2), (2, 13.5, 2), P.IRON)
    m.box((1.5, 41, -1), (11.5, 43, 1), P.DARK_WOOD, grain="x")
    m.box((4.25, 32.5, -0.75), (5.75, 42.5, 0.75), P.DARK_WOOD, rot=("z", -45.0, (5, 37.5, 0)), grain="y")
    m.box((-2, 40.5, -2), (2, 43.5, 2), P.IRON)
    # hook, chain and lantern
    m.box((8.5, 37.5, -0.5), (9.5, 41, 0.5), P.IRON)
    m.box((6.5, 36.5, -2.5), (11.5, 37.5, 2.5), P.BRASS_DARK)
    m.box((7.5, 37.5, -1.5), (10.5, 38.2, 1.5), P.BRASS_DARK)
    m.box((7, 31.5, -2), (11, 36.5, 2), P.LAMP_GLOW, emit=15, shade=False)
    for sx in (6.6, 10.6):
        for sz in (-2.4, 1.6):
            m.box((sx, 31.5, sz), (sx + 0.8, 36.5, sz + 0.8), P.BRASS_DARK, seed=901)
    m.box((6.5, 30.5, -2.5), (11.5, 31.5, 2.5), P.BRASS_DARK)
    m.box((8.25, 29.5, -0.75), (9.75, 30.5, 0.75), P.BRASS)
    return m


def telescope_tube():
    """Brass refractor, objective towards -z. Anchor: the pivot on the tube's axis."""
    m = M.Model("telescope_tube", px=3)
    m.tube("z", (0, 0), -26, 14, 3.0, P.BRASS)
    m.tube("z", (0, 0), -29.9, -25, 3.7, P.BRASS_DARK)
    m.box((-2.6, -2.6, -29.96), (2.6, 2.6, -29.8), P.LENS, skip="sewud", shade=False)
    m.tube("z", (0, 0), -12, -10, 3.45, P.BRASS_DARK)
    m.tube("z", (0, 0), 2, 4, 3.45, P.BRASS_DARK)
    m.tube("z", (0, 0), 12, 14.5, 3.45, P.BRASS_DARK)
    m.tube("z", (0, 0), 14.5, 17, 2.0, P.BRASS_DARK)
    m.tube("z", (0, 0), 17, 18, 1.3, P.IRON)
    # finder scope on stalks
    m.tube("z", (0, 4.9), -14, -2, 1.0, P.BRASS_DARK)
    m.box((-0.5, 3, -12.5), (0.5, 4.2, -11.5), P.IRON, seed=902)
    m.box((-0.5, 3, -4.5), (0.5, 4.2, -3.5), P.IRON, seed=902)
    # trunnion blocks
    m.box((-4.2, -1.5, -1.5), (-3, 1.5, 1.5), P.IRON, seed=903)
    m.box((3, -1.5, -1.5), (4.2, 1.5, 1.5), P.IRON, seed=903)
    return m


def telescope_mount():
    """Fork and pier that carry the tube. Anchor: the pivot."""
    m = M.Model("telescope_mount", px=3)
    for sx in (-5.6, 4.2):
        m.box((sx, -8, -1.6), (sx + 1.4, 2, 1.6), P.IRON, seed=904)
    m.box((-5.6, -9.5, -1.6), (5.6, -8, 1.6), P.IRON)
    m.tube("y", (0, 0), -11, -9.5, 3.2, P.BRASS_DARK)
    m.tube("y", (0, 0), -24, -11, 2.0, P.IRON)
    m.tube("y", (0, 0), -26, -24, 3.0, P.IRON)
    m.tube("y", (0, 0), -28, -26, 4.5, P.IRON)
    m.ring("x", (6.4, -4, 0), 2.2, 0.7, 0.6, P.BRASS, sides=8)
    m.box((5.6, -4.4, -0.4), (6.8, -3.6, 0.4), P.BRASS_DARK)
    return m


def armillary():
    """Three fixed brass rings on a short stem. Anchor: underside of the base."""
    m = M.Model("armillary", px=2, anchor=(0, -16, 0))
    m.ring("y", (0, 0, 0), 10.0, 1.0, 1.2, P.BRASS)
    m.ring("x", (0, 0, 0), 10.0, 1.0, 1.0, P.BRASS_DARK)
    m.ring("z", (0, 0, 0), 10.0, 1.0, 1.0, P.BRASS_DARK)
    m.box((-0.75, -14, -0.75), (0.75, -10.4, 0.75), P.BRASS_DARK)
    m.tube("y", (0, 0), -15, -14, 3.0, P.BRASS_DARK)
    m.tube("y", (0, 0), -16, -15, 4.2, P.BRASS_DARK)
    return m


def armillary_core():
    """The tilted inner ring, its axis and the globe. Anchor: centre."""
    m = M.Model("armillary_core", px=2)
    m.ring("y", (0, 0, 0), 7.6, 0.9, 1.0, P.COPPER)
    m.box((-0.4, -9.4, -0.4), (0.4, 9.4, 0.4), P.IRON)
    m.box((-2, -1.25, -1.25), (2, 1.25, 1.25), P.VERDIGRIS, seed=905)
    m.box((-1.25, -2, -1.25), (1.25, 2, 1.25), P.VERDIGRIS, seed=906)
    m.box((-1.25, -1.25, -2), (1.25, 1.25, 2), P.VERDIGRIS, seed=907)
    return m


def weathervane():
    """Rod with a compass cross and a shooting-star arrow. Anchor: foot of the rod."""
    star = P.Sprite("vane_star", STAR, {"#": "#dcb650"})
    head = P.Sprite("vane_head", ARROW, {"#": "#dcb650"})
    m = M.Model("weathervane")
    m.box((-0.5, 0, -0.5), (0.5, 22, 0.5), P.IRON, grain="y")
    m.box((-1.25, 0, -1.25), (1.25, 1.5, 1.25), P.IRON)
    m.box((-6, 8.6, -0.4), (6, 9.4, 0.4), P.IRON, grain="x")
    m.box((-0.4, 8.6, -6), (0.4, 9.4, 6), P.IRON, grain="z")
    for x, z in ((6, 0), (-6, 0), (0, 6), (0, -6)):
        m.box((x - 0.8, 8.2, z - 0.8), (x + 0.8, 9.8, z + 0.8), P.BRASS, seed=908)
    m.box((-8, 16.6, -0.4), (7, 17.4, 0.4), P.BRASS, grain="x")
    m.box((-12, 13.5, -0.2), (-8, 20.5, 0.2), head, skip="ewud", faces={"n": head.mirrored()})
    m.box((6, 12.5, -0.2), (13, 21.5, 0.2), star, skip="ewud")
    m.box((-1, 22, -1), (1, 24, 1), P.BRASS)
    return m


def sign_board():
    """Hanging shop sign on an iron bracket; the wall is at -x. Anchor: where the bracket meets the wall."""
    emblem = P.Sprite("emblem", EMBLEM, {"b": "#dcb650", "k": "#2a2c34", "o": "#fff2b0"}, back=P.DARK_WOOD)
    m = M.Model("sign_board")
    m.box((0, -0.5, -0.5), (15, 0.5, 0.5), P.IRON, grain="x")
    m.box((0, -5, -1), (1, 1.5, 1), P.IRON)
    m.box((1.75, -5, -0.4), (2.75, 0.5, 0.4), P.IRON, rot=("z", -45.0, (2.25, -2.25, 0)), seed=909)
    for x in (4.5, 12.5):
        m.box((x - 0.4, -2.5, -0.4), (x + 0.4, -0.5, 0.4), P.IRON, seed=910)
    m.box((3, -14.5, -0.6), (14, -2.5, 0.6), P.DARK_WOOD, grain="x", faces={"n": emblem, "s": emblem})
    m.box((2.5, -3, -0.9), (14.5, -2, 0.9), P.WOOD, grain="x")
    m.box((2.5, -15, -0.9), (14.5, -14, 0.9), P.WOOD, grain="x")
    return m


def crate():
    """Plank crate with corner posts. Anchor: centre of the underside."""
    m = M.Model("crate")
    m.box((-6, 0, -6), (6, 11, 6), P.WOOD, grain="x")
    for x in (-6.5, 5):
        for z in (-6.5, 5):
            m.box((x, 0, z), (x + 1.5, 11.5, z + 1.5), P.DARK_WOOD, grain="y", seed=911)
    m.box((-6.5, 4.5, -6.3), (6.5, 6.5, 6.3), P.DARK_WOOD, grain="x", skip="ud")
    m.box((-6.3, 4.5, -6.5), (6.3, 6.5, 6.5), P.DARK_WOOD, grain="z", skip="ud")
    m.box((-6.5, 11, -6.5), (6.5, 12, 6.5), P.WOOD, grain="z")
    return m


MODELS = [lamp_post, telescope_tube, telescope_mount, armillary, armillary_core, weathervane, sign_board, crate]


def build_models():
    return {f.__name__: f() for f in MODELS}
