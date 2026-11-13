"""Custom models for the observatory island: the resource pack side of the scene.

Every model is drawn in sixteenths of a block around its anchor and shown through an item_display
(see artkit.models.display). `SCALE` holds the display scale each model was drawn for; its `px`
matches, so the textures keep the vanilla sixteen pixels per block.
"""
import math

from artkit import models as M
from artkit import pixelart as P

SCALE = {
    "lamp_post": 1.0, "telescope_tube": 5.0, "telescope_mount": 5.0, "armillary": 2.0, "armillary_core": 2.0,
    "weathervane": 1.0, "sign_board": 1.0, "crate": 1.0, "trunk": 1.0, "engine_pod_s": 2.0, "engine_pod_n": 2.0, "rope": 1.0,
    "windsock": 2.0, "bunting": 1.0, "signpost": 1.0, "cattail": 1.0, "ship_wheel": 1.0, "dome_rail": 5.0,
    "spyglass": 1.0,
}

# the rails beside the observing slit follow the dome: radius of their arc in blocks, and its
# extent in degrees from straight up (negative: behind the crown) down towards the sill
RAIL_R = 8.9
RAIL_ARC = (-18.0, 84.0)

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
FLAG = [
    "#####",
    "#####",
    "#####",
    ".###.",
    ".###.",
    "..#..",
]
DOCK_SIGN = [
    "..............",
    "...######.....",
    "..#########.#.",
    "..###########.",
    "...######...#.",
    ".....#..#.....",
    ".....####.....",
]
STARS_SIGN = [
    "..............",
    "..#.......#...",
    ".###..#..###..",
    "..#..###..#...",
    "......#.......",
    "..............",
]

LENS_A = P.Mat("lens_a", ["#1d3f57"], kind="flat", bevel=0)
LENS_B = P.Mat("lens_b", ["#3a7391"], kind="flat", bevel=0)
LENS_C = P.Mat("lens_c", ["#8cc4da"], kind="flat", bevel=0)
GLINT = P.Mat("glint", ["#eefaff"], kind="flat", bevel=0)
LEATHER = P.Mat("leather", ["#3b2418", "#4f3020", "#653e29", "#7b4d34", "#916040"], noise=0.18)
CANVAS = P.Mat("canvas", ["#27382a", "#334a36", "#415c44", "#507052", "#628563"], noise=0.22)
SOCK_IN = P.Mat("sock_in", ["#3d0f10"], kind="flat", bevel=0)
REED = P.Mat("reed", ["#3c5a24", "#4d7030", "#62893c", "#7ba24c"], kind="wood", bevel=0)
REED_HEAD = P.Mat("reed_head", ["#3a2414", "#4e311b", "#634024", "#7a512f"], noise=0.3, bevel=0)


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
    # wrought bracket: a quarter round under the arm with a small curl at its foot
    m.ring("z", (1.5, 41.0, 0), 7.0, 0.8, 0.8, P.IRON, sides=40, arc=(270.0, 360.0))
    m.ring("z", (2.9, 34.2, 0), 1.3, 0.6, 0.8, P.IRON, sides=12, arc=(-60.0, 210.0))
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
    m = M.Model("telescope_tube", px=5)
    m.tube("z", (0, 0), -33, 8, 2.5, P.BRASS, sides=24)
    # hollow dew shield with the lens set back inside it
    m.ring("z", (0, 0, -33.5), 3.0, 0.5, 5.0, P.BRASS_DARK, sides=24)
    m.ring("z", (0, 0, -35.7), 3.15, 0.5, 0.6, P.BRASS, sides=24)
    m.tube("z", (0, 0), -34.4, -33, 2.75, P.BRASS_DARK, sides=24, cap=LENS_A)
    m.tube("z", (0, 0), -34.5, -33, 2.0, P.BRASS_DARK, sides=16, cap=LENS_B)
    m.tube("z", (0, 0), -34.6, -33, 1.1, P.BRASS_DARK, sides=12, cap=LENS_C)
    m.box((-1.5, 0.7, -34.7), (-0.7, 1.5, -34.5), GLINT, skip="sewud", shade=False)
    for z in (-31, -20, -9):
        m.tube("z", (0, 0), z, z + 1, 2.85, P.BRASS_DARK, sides=24)
    m.tube("z", (0, 0), -2, 2, 2.9, P.IRON, sides=24)
    m.tube("z", (0, 0), 6, 8.2, 2.9, P.BRASS_DARK, sides=24)
    m.taper("z", (0, 0), 8.2, 10.5, 2.3, 1.5, P.BRASS_DARK, sides=16, steps=3)
    m.tube("z", (0, 0), 10.5, 11.6, 1.1, P.IRON, sides=12)
    m.tube("z", (0, 0), 11.6, 12, 1.35, P.BRASS, sides=12)
    m.tube("y", (0, 11.0), 0.6, 3.4, 0.8, P.BRASS)
    for sx in (-2.6, 1.7):
        m.box((sx, -0.5, 8.8), (sx + 0.9, 0.5, 9.8), P.IRON, seed=912)
    # finder scope on stalks
    m.tube("z", (0, 3.8), -19, -8, 0.7, P.BRASS_DARK, sides=12)
    m.tube("z", (0, 3.8), -19.6, -19, 0.9, P.BRASS, sides=12, cap=LENS_B)
    m.box((-0.3, 2.4, -17.5), (0.3, 3.3, -16.5), P.IRON, seed=902)
    m.box((-0.3, 2.4, -10.5), (0.3, 3.3, -9.5), P.IRON, seed=902)
    # trunnions
    m.box((-4.0, -1.2, -1.2), (-2.6, 1.2, 1.2), P.IRON, seed=903)
    m.box((2.6, -1.2, -1.2), (4.0, 1.2, 1.2), P.IRON, seed=903)
    return m


def telescope_mount():
    """Fork and pier that carry the tube. Anchor: the pivot, 12.8 units above the floor."""
    m = M.Model("telescope_mount", px=5)
    for sx in (-5.2, 4.0):
        m.box((sx, -7, -1.4), (sx + 1.2, 1.7, 1.4), P.IRON, seed=904)
    m.box((-5.2, -8.2, -1.4), (5.2, -7, 1.4), P.IRON, grain="x")
    m.tube("y", (0, 0), -9.0, -8.2, 3.2, P.BRASS_DARK, sides=16)
    m.tube("y", (0, 0), -11.8, -9.0, 2.0, P.IRON)
    m.tube("y", (0, 0), -12.8, -11.8, 3.4, P.IRON, sides=16)
    # handwheel on the east arm
    m.ring("x", (5.7, -3.5, 0), 1.6, 0.5, 0.4, P.BRASS, sides=8)
    m.box((5.2, -3.8, -0.3), (6.0, -3.2, 0.3), P.BRASS_DARK)
    m.box((5.55, -5.0, -0.2), (5.85, -2.0, 0.2), P.BRASS_DARK, seed=913)
    m.box((5.55, -3.7, -1.5), (5.85, -3.3, 1.5), P.BRASS_DARK, seed=914)
    return m


def armillary():
    """Three fixed brass rings in a cradle on a turned stand. Anchor: underside of the base."""
    m = M.Model("armillary", px=2, anchor=(0, -16, 0))
    m.ring("y", (0, 0, 0), 10.0, 1.0, 1.2, P.BRASS, sides=32)
    m.ring("x", (0, 0, 0), 10.0, 1.0, 1.0, P.BRASS_DARK, sides=32)
    m.ring("z", (0, 0, 0), 10.0, 1.0, 1.0, P.BRASS_DARK, sides=32)
    m.ring("z", (0, 0, 0), 11.3, 0.9, 1.6, P.IRON, sides=32, arc=(195.0, 345.0))
    for sx in (-1, 1):
        m.ball((sx * 11.0, -2.9, 0), 0.9, P.BRASS, sides=8, layers=4)
    m.tube("y", (0, 0), -13.6, -11.7, 0.8, P.BRASS_DARK, sides=12)
    m.ball((0, -12.9, 0), 1.3, P.BRASS, sides=12, layers=4)
    m.taper("y", (0, 0), -14.6, -13.6, 2.6, 1.0, P.BRASS_DARK, sides=16, steps=3)
    m.tube("y", (0, 0), -15.3, -14.6, 3.2, P.BRASS_DARK, sides=16)
    m.tube("y", (0, 0), -16, -15.3, 4.4, P.BRASS_DARK, sides=16)
    return m


def armillary_core():
    """The tilted inner band, its axis, the globe and a small moon. Anchor: centre."""
    m = M.Model("armillary_core", px=2)
    m.ring("y", (0, 0, 0), 7.6, 0.9, 1.6, P.COPPER, sides=32)
    m.ring("x", (0, 0, 0), 7.5, 0.7, 0.7, P.BRASS_DARK, sides=32)
    m.tube("y", (0, 0), -9.5, 9.5, 0.35, P.IRON, sides=8)
    for sy in (-1, 1):
        m.ball((0, sy * 9.8, 0), 0.7, P.BRASS, sides=8, layers=4)
    m.ball((0, 0, 0), 2.4, P.VERDIGRIS, sides=12, layers=6)
    m.rod((0, 0, 0), (4.3, 0.9, 2.2), 0.18, P.IRON, sides=4)
    m.ball((4.5, 0.95, 2.3), 0.8, P.PARCHMENT, sides=8, layers=4)
    return m


def weathervane():
    """Rod with a compass cross and a shooting-star arrow whose head points to -x. Anchor: foot of the rod."""
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


def trunk():
    """Travel trunk with straps, brass corners and a lock. Anchor: centre of the underside."""
    m = M.Model("trunk")
    m.box((-7, 0, -4.5), (7, 6, 4.5), CANVAS, grain="x")
    m.box((-7.25, 6, -4.75), (7.25, 9, 4.75), CANVAS, grain="x")
    for x in (-4.5, 3):
        m.box((x, -0.01, -5), (x + 1.5, 9.25, 5), LEATHER, grain="y", seed=915)
    for x in (-7.5, 6):
        for z in (-5, 3.5):
            m.box((x, 0, z), (x + 1.5, 1.5, z + 1.5), P.BRASS, seed=916)
            m.box((x, 7.75, z), (x + 1.5, 9.25, z + 1.5), P.BRASS, seed=916)
    m.box((-1, 4.5, 4.5), (1, 7, 5.1), P.BRASS)
    for x in (-7.6, 7.0):
        m.box((x, 3.5, -1.5), (x + 0.6, 4.5, 1.5), LEATHER, seed=917)
    return m


def engine_pod(side=1):
    """Outboard engine with a four-bladed pusher propeller on its +x end.

    Two struts reach the hull on the -z side (side=1, model engine_pod_s) or on the +z side
    (side=-1, engine_pod_n). Anchor: where the struts meet the hull.
    """
    m = M.Model("engine_pod_s" if side > 0 else "engine_pod_n", px=2, anchor=(0, 0, -11.0 * side))
    za, zb = sorted((-11.0 * side, -1.6 * side))
    m.box((0.4, -0.4, za), (1.4, 0.4, zb), P.IRON, grain="z", seed=960)
    m.box((-3.0, -0.4, za), (-2.0, 0.4, zb), P.IRON, grain="z", seed=960)
    m.rod((-2.5, 0, -11.0 * side), (0.9, 0, -1.9 * side), 0.25, P.IRON, sides=4)   # diagonal stay
    # nacelle, rounded off at both ends
    m.taper("x", (0, 0), -5.8, -3.6, 1.0, 2.2, P.IRON, sides=12, steps=4)
    m.tube("x", (0, 0), -3.6, 2.2, 2.2, P.IRON, sides=12)
    m.taper("x", (0, 0), 2.2, 3.4, 2.2, 1.5, P.IRON, sides=12, steps=3)
    m.tube("x", (0, 0), -2.6, -1.8, 2.45, P.BRASS_DARK, sides=12)
    m.tube("x", (0, 0), 0.6, 1.4, 2.45, P.BRASS_DARK, sides=12)
    # exhaust stack, raked aft
    m.rod((-1.9, 1.7, 0), (-3.3, 4.8, 0), 0.55, P.IRON, sides=8)
    m.rod((-3.3, 4.8, 0), (-3.6, 5.5, 0), 0.8, P.BRASS_DARK, sides=8)
    # propeller: hub, spinner and four pitched blades with brass tips
    m.tube("x", (0, 0), 3.4, 4.9, 1.1, P.BRASS_DARK, sides=12)
    m.taper("x", (0, 0), 4.9, 6.7, 1.0, 0.3, P.BRASS, sides=12, steps=4)
    blade = P.PALE_WOOD
    for i in range(4):
        with m.turned(("x", 90.0 * i + 18.0), about=(4.15, 0, 0)), m.turned(("y", 26.0), about=(4.15, 0, 0)):
            m.box((3.95, 0.8, -0.5), (4.35, 3.0, 0.5), blade, grain="y", seed=918)
            m.box((3.95, 3.0, -1.15), (4.35, 8.0, 1.15), blade, grain="y", seed=919)
            m.box((3.95, 8.0, -0.8), (4.35, 9.0, 0.8), blade, grain="y", seed=920)
            m.box((3.9, 8.5, -0.85), (4.4, 9.2, 0.85), P.BRASS, seed=961)
    return m


def rope():
    """Three blocks of rope along +z, to be stretched between two points. Anchor: the near end."""
    m = M.Model("rope")
    m.box((-0.5, -0.5, 0), (0.5, 0.5, 48), P.ROPE, grain="z", skip="ns")
    return m


def windsock():
    """Striped windsock on a pole in a light breeze towards +x: it fills at the mouth and droops
    towards the tail. Anchor: foot of the pole."""
    m = M.Model("windsock", px=2)
    m.tube("y", (0, 0), 0, 40, 0.5, P.DARK_WOOD, sides=8)
    m.tube("y", (0, 0), 0, 1.5, 1.1, P.IRON, sides=8)
    m.ball((0, 40.7, 0), 0.9, P.BRASS, sides=8, layers=4)
    m.tube("y", (0, 0), 36.2, 37.8, 0.75, P.IRON, sides=8)
    # hoop held by four cords from the swivel
    hoop = (3.6, 37.0, 0.0)
    m.ring("x", hoop, 2.9, 0.5, 0.5, P.IRON, sides=16)
    for dy, dz in ((2.9, 0), (-2.9, 0), (0, 2.9), (0, -2.9)):
        m.rod((0.6, 37.0, 0), (hoop[0], hoop[1] + dy, dz), 0.14, P.ROPE, sides=4)
    pts, radii, mats = [hoop], [], []
    n = 8
    for i in range(n):
        t = (i + 0.5) / n
        fall = math.radians(4.0 + 58.0 * t ** 1.6)
        x, y, z = pts[-1]
        pts.append((x + 2.3 * math.cos(fall), y - 2.3 * math.sin(fall), z + 0.09 * i))
        radii.append(2.75 - 1.45 * t)
        mats.append(P.RED_CLOTH if i % 2 == 0 else P.CREAM_CLOTH)
    m.hose(pts, radii, mats, sides=12, cap=SOCK_IN)
    return m


def bunting():
    """One block of string with three pennants, running along +x. Anchor: the left end of the string."""
    m = M.Model("bunting")
    m.box((0, -0.25, -0.25), (16, 0.25, 0.25), P.ROPE, grain="x", skip="ew")
    colours = ("#b83a36", "#eadfc6", "#3d8a70", "#dcb650")
    for i in range(3):
        flag = P.Sprite(f"flag{i}", FLAG, {"#": colours[i]})
        x = 1.0 + 5.25 * i
        m.box((x, -6.2, -0.1), (x + 5, -0.2, 0.1), flag, skip="ewud")
    return m


def signpost():
    """Fingerpost with two boards: one pointing to -x, one to +x. Anchor: foot of the post."""
    dock = P.Sprite("sign_dock", DOCK_SIGN, {"#": "#eadbb1"}, back=P.DARK_WOOD)
    stars = P.Sprite("sign_stars", STARS_SIGN, {"#": "#dcb650"}, back=P.DARK_WOOD)
    m = M.Model("signpost")
    m.box((-1.25, 0, -1.25), (1.25, 30, 1.25), P.WOOD, grain="y")
    m.box((-1.75, 30, -1.75), (1.75, 31, 1.75), P.DARK_WOOD)
    m.box((-2, 0, -2), (2, 2, 2), P.STONE)
    m.box((-17, 22, 1.25), (1, 29, 2.25), P.DARK_WOOD, grain="x", faces={"s": dock, "n": dock})
    m.box((-19, 24, 1.25), (-17, 27, 2.25), P.DARK_WOOD, grain="x")
    m.box((-1, 13, -2.25), (17, 20, -1.25), P.DARK_WOOD, grain="x", faces={"s": stars, "n": stars})
    m.box((17, 15, -2.25), (19, 18, -1.25), P.DARK_WOOD, grain="x")
    return m


def cattail():
    """A clump of reeds with brown heads, tall enough to stand in a block of water. Anchor: centre of the foot."""
    m = M.Model("cattail")
    # stalks: foot x, z, height, lean towards (dx, dz) in units over the full height
    stalks = [(-3, -2, 34, -2.5, -1.0), (0, 1, 41, 0.8, 1.5), (3, -1, 30, 4.5, -2.0), (-1, 3, 27, -3.0, 4.0),
              (2, 3, 37, 2.2, 3.0)]
    for i, (x, z, h, dx, dz) in enumerate(stalks):
        top = (x + dx, h, z + dz)
        m.rod((x, 0, z), top, 0.4, REED, sides=4, seed=920 + i)
        if h > 28:
            a = tuple(p + (q - p) * (1 - 8.0 / h) for p, q in zip((x, 0, z), top))
            b = tuple(p + (q - p) * (1 - 2.0 / h) for p, q in zip((x, 0, z), top))
            m.rod(a, b, 0.85, REED_HEAD, sides=8, seed=930)
    # leaf blades: up, then bending over
    for i, (x, z, h, dx, dz) in enumerate(((-2, 1, 22, -5.0, 2.0), (1, -3, 20, 2.0, -6.0), (4, 1, 21, 6.0, 1.5),
                                         (-4, -1, 17, -5.5, -3.0))):
        knee = (x + dx * 0.35, h * 0.62, z + dz * 0.35)
        tip = (x + dx * 1.25, h * 0.9, z + dz * 1.25)
        m.beam((x, 0, z), knee, 1.7, 0.3, REED, seed=940 + i)
        m.beam(knee, tip, 1.3, 0.3, REED, seed=944 + i)
    return m


def ship_wheel():
    """Helm: an eight-spoked wheel on a short pedestal, wheel facing +x. Anchor: foot of the pedestal."""
    m = M.Model("ship_wheel")
    m.box((-1.5, 0, -1.5), (1.5, 9, 1.5), P.DARK_WOOD, grain="y")
    m.box((-2, 9, -2), (2, 10, 2), P.DARK_WOOD)
    m.box((-0.75, 10, -0.75), (1.5, 13.5, 0.75), P.DARK_WOOD)
    cx, cy = 3.0, 12.25
    m.tube("x", (cy, 0), 1.5, cx, 0.7, P.BRASS, sides=8)
    m.ring("x", (cx, cy, 0), 5.0, 1.0, 0.8, P.WOOD, sides=24)
    for i in range(8):
        with m.turned(("x", 45.0 * i + 11.0), about=(cx, cy, 0)):
            m.box((cx - 0.3, cy + 1.0, -0.4), (cx + 0.3, cy + 5.4, 0.4), P.DARK_WOOD, grain="y", seed=950)
            m.tube("y", (cx, 0), cy + 5.4, cy + 7.2, 0.42, P.DARK_WOOD, sides=8, seed=951)
            m.tube("y", (cx, 0), cy + 6.9, cy + 7.6, 0.62, P.DARK_WOOD, sides=8, seed=952)
    m.tube("x", (cy, 0), cx - 0.55, cx + 0.55, 1.5, P.DARK_WOOD, sides=12)
    m.tube("x", (cy, 0), cx + 0.55, cx + 0.9, 0.9, P.BRASS, sides=12)
    return m


def dome_rail():
    """Brass rail along one edge of the observing slit: an arc over the dome from behind the crown
    down to the sill. Anchor: the centre of the dome's curve; the arc lies in the plane x = 0 and
    comes down towards +z."""
    m = M.Model("dome_rail", px=5, anchor=(0, 0, 0))
    r = RAIL_R * 16.0 / SCALE["dome_rail"]
    m.ring("x", (0, 0, 0), r, 1.5, 1.7, P.BRASS_DARK, sides=48, arc=RAIL_ARC)
    m.ring("x", (0, 0, 0), r + 0.9, 0.5, 0.8, P.BRASS, sides=48, arc=RAIL_ARC)
    # rollers of the shutter gear, evenly along the rail
    for k in range(5):
        a = math.radians(RAIL_ARC[0] + (RAIL_ARC[1] - RAIL_ARC[0]) * (k + 0.5) / 5.0)
        y, z = (r + 1.1) * math.cos(a), (r + 1.1) * math.sin(a)
        m.tube("x", (y, z), -1.25, 1.25, 0.75, P.IRON, sides=8, seed=970)
    return m


def spyglass():
    """Small brass telescope on a wooden tripod, looking towards -z and a little upwards.
    Anchor: the ground under the middle of the tripod."""
    m = M.Model("spyglass")
    for deg in (90.0, 210.0, 330.0):
        a = math.radians(deg)
        m.rod((6.5 * math.cos(a), 0.0, 6.5 * math.sin(a)), (0.6 * math.cos(a), 19.4, 0.6 * math.sin(a)), 0.55,
              P.DARK_WOOD, sides=4, seed=981)
    m.tube("y", (0, 0), 18.6, 20.4, 1.4, P.BRASS_DARK)
    m.tube("y", (0, 0), 20.4, 21.8, 0.6, P.IRON)
    m.box((-0.5, 21.4, -0.9), (0.5, 22.4, 0.9), P.IRON)
    with m.turned(("x", 16.0), about=(0, 23.2, 0)):
        m.tube("z", (0, 23.2), -9.0, 3.0, 1.3, P.BRASS, sides=12)
        m.tube("z", (0, 23.2), -10.4, -9.0, 1.65, P.BRASS_DARK, sides=12, cap=LENS_B)
        m.tube("z", (0, 23.2), -4.6, -3.8, 1.5, P.BRASS_DARK, sides=12)
        m.tube("z", (0, 23.2), 3.0, 6.4, 0.9, P.BRASS_DARK, sides=12)
        m.tube("z", (0, 23.2), 6.4, 7.1, 1.15, P.IRON, sides=12)
    return m


MODELS = [lamp_post, telescope_tube, telescope_mount, armillary, armillary_core, weathervane, sign_board, crate,
          trunk, rope, windsock, bunting, signpost, cattail, ship_wheel, dome_rail, spyglass]
_BUILT = None


def build_models():
    out = {}
    for f in MODELS + instruments.MODELS + skystone.MODELS:
        m = f()
        out[m.name] = m
    for side in (1, -1):
        m = engine_pod(side)
        out[m.name] = m
    return out


def models():
    global _BUILT
    if _BUILT is None:
        _BUILT = build_models()
    return _BUILT


def place(c, name, x, y, z, **opts):
    """Put a model into the scene with its anchor at (x, y, z); options as for artkit.models.display."""
    opts.setdefault("scale", SCALE[name])
    c.add_entity(x, y, z, M.display(models()[name], **opts))


def stretch(c, name, a, b, thick=1.0, **opts):
    """Span a model drawn along +z (a rope) from point a to point b. a must lie in open air: it lights the model."""
    c.add_entity(a[0], a[1], a[2], M.between(models()[name], a, b, thick=thick, **opts))


# how the models are shown in the test gallery: name, parts (model, offset in blocks or None to stand
# it on the floor, display options), camera offset and the point it looks at
GALLERY = [
    ("lamp", [("lamp_post", None, {})], (2.6, 2.2, 3.6), (0.3, 1.7, 0)),
    ("telescope", [("telescope_mount", (0, 4.0, 0), {"yaw": 180.0}),
                   ("telescope_tube", (0, 4.0, 0), {"yaw": 180.0, "turns": (("x", 45.0),)})],
     (9.0, 5.5, 8.0), (0, 5.5, 2.0)),
    ("armillary", [("armillary", (0, 1.0, 0), {}), ("armillary_core", (0, 3.0, 0), {"turns": (("z", 23.5),)})],
     (2.6, 2.6, 3.4), (0, 2.8, 0)),
    ("weathervane", [("weathervane", (0, 1.0, 0), {"yaw": 20.0})], (1.2, 2.2, 2.4), (0, 2.0, 0)),
    ("sign", [("sign_board", (-0.5, 2.5, 0), {})], (1.4, 2.2, 2.4), (0, 2.0, 0)),
    ("cargo", [("crate", (0, 0, 0), {"yaw": 12.0}), ("crate", (1.1, 0, -0.2), {"yaw": -8.0}),
               ("crate", (0.5, 0.75, -0.1), {"yaw": 30.0}), ("trunk", (-1.3, 0, 0.2), {"yaw": -15.0}),
               ("trunk", (-1.25, 0.58, 0.15), {"yaw": 8.0})], (1.8, 1.7, 3.0), (0, 0.6, 0)),
    ("engine", [("engine_pod_s", (0, 2.0, -1.0), {}), ("engine_pod_n", (0, 2.0, -1.4), {})],
     (3.6, 2.8, 3.2), (0, 2.0, -1.0)),
    ("windsock", [("windsock", None, {})], (3.5, 3.5, 5.0), (1.0, 3.6, 0)),
    ("bunting", [("bunting", (-1.5 + i, 2.5, 0), {}) for i in range(3)], (0.8, 2.4, 2.6), (0, 2.2, 0)),
    ("signpost", [("signpost", None, {})], (1.6, 1.8, 3.0), (0, 1.3, 0)),
    ("cattail", [("cattail", None, {}), ("cattail", (0.8, 0, 0.5), {"yaw": 140.0})], (1.6, 1.8, 3.0), (0.3, 1.2, 0)),
    ("wheel", [("ship_wheel", None, {})], (2.0, 1.6, 1.6), (0, 0.8, 0)),
    ("rail", [("dome_rail", (0, 0, -3.0), {})], (7.0, 5.0, 6.0), (0, 4.5, 0)),
    ("spyglass", [("spyglass", None, {"yaw": 150.0})], (1.6, 1.9, 2.2), (0, 1.1, 0)),
]

from . import instruments, skystone  # noqa: E402  the room under the dome; crystal and chain

SCALE.update(instruments.SCALE)
SCALE.update(skystone.SCALE)
GALLERY = GALLERY + instruments.GALLERY + skystone.GALLERY


def chain(c, a, b, sag=0.0, scale=None, **opts):
    """Hang heavy chain from point a to point b, `sag` blocks below the straight line half way.

    Runs of three links follow the curve; the links are stretched a few per cent so that a whole
    number of runs ends exactly on b. Returns the number of runs placed.
    """
    s = scale or SCALE["chain_run"]
    n = 240
    pts = []
    for i in range(n + 1):
        t = i / n
        pts.append(tuple(a[k] + (b[k] - a[k]) * t - (sag * 4.0 * t * (1.0 - t) if k == 1 else 0.0) for k in range(3)))
    lengths = [0.0]
    for p, q in zip(pts, pts[1:]):
        lengths.append(lengths[-1] + math.dist(p, q))
    total = lengths[-1]
    lap = (skystone.CHAIN_RUN - skystone.CHAIN_STEP) * s / 16.0
    count = max(1, int(round((total - lap) / (skystone.CHAIN_STEP * s / 16.0))))
    stretch_by = total / (count * skystone.CHAIN_STEP * s / 16.0 + lap)
    step, run = skystone.CHAIN_STEP * s / 16.0 * stretch_by, skystone.CHAIN_RUN * s / 16.0 * stretch_by

    def at(length):
        length = min(max(length, 0.0), total)
        i = min(n - 1, max(0, next((j for j, v in enumerate(lengths) if v >= length), n) - 1))
        span = lengths[i + 1] - lengths[i]
        t = 0.0 if span < 1e-9 else (length - lengths[i]) / span
        return tuple(pts[i][k] + (pts[i + 1][k] - pts[i][k]) * t for k in range(3))

    for k in range(count):
        p, q = at(k * step), at(k * step + run)
        dx, dy, dz = (q[i] - p[i] for i in range(3))
        flat = math.hypot(dx, dz)
        yaw = math.degrees(math.atan2(-dx, dz)) if flat > 1e-6 else 0.0
        pitch = math.degrees(math.atan2(dy, flat))
        c.add_entity(p[0], p[1], p[2], M.display(models()["chain_run"], yaw=yaw, scale=(s, s, s * stretch_by),
                                                 turns=(("z", 90.0 * (k % 2)), ("x", -pitch)), **opts))
    return count
