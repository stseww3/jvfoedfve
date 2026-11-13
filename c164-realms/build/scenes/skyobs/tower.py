"""Observatory tower: stone shaft, timber gallery, copper dome with an open slit and a telescope."""
import math

from artkit import arch as A
from artkit import blocks as B
from artkit.canvas import Mix, hash3

BASE = Mix({"cobblestone": 30, "mossy_cobblestone": 14, "stone_bricks": 26, "mossy_stone_bricks": 14,
            "andesite": 10, "cracked_stone_bricks": 6}, seed=31)
MID = Mix({"stone_bricks": 64, "cracked_stone_bricks": 9, "mossy_stone_bricks": 5, "andesite": 12,
           "cobblestone": 6, "stone": 4}, seed=32)
UP = Mix({"stone_bricks": 72, "cracked_stone_bricks": 8, "andesite": 14, "stone": 6}, seed=33)
TRIM = Mix({"stone_bricks": 62, "mossy_stone_bricks": 14, "cobblestone": 12, "andesite": 12}, seed=34)
APRON = Mix({"cobblestone": 34, "stone": 14, "andesite": 16, "mossy_cobblestone": 14, "stone_bricks": 14,
             "gravel": 8}, seed=35)
FOUND = Mix({"cobblestone": 50, "stone": 20, "mossy_cobblestone": 15, "andesite": 15}, seed=36)


def build(c, land, cx, cz, y0):
    """(cx, cz) is the centre on a block corner; y0 is the first wall layer above the plateau."""
    icx, icz = int(cx), int(cz)

    def wall(x, y, z):
        t = (y - y0) + 3.0 * (hash3(x, y, z, 91) - 0.5)
        return BASE(x, y, z) if t < 3 else MID(x, y, z) if t < 13 else UP(x, y, z)

    def inward(x, z):
        return A.OPP[A.outward(x + 0.5 - cx, z + 0.5 - cz)]

    # ---- apron and footing -------------------------------------------------------------------
    for x, z in A.disc(cx, cz, 10.4):
        d = A.dist(x, z, cx, cz)
        if (x, z) not in land.top:
            continue
        for y in range(y0, y0 + 6):
            c.clear(x, y, z)
        if d <= 9.4:
            c.set(x, y0 - 1, z, APRON)
            A.fill_down(c, x, y0 - 2, z, FOUND(x, y0 - 2, z))
            land.kind[(x, z)] = "built"
            land.top[(x, z)] = y0 - 1
        elif land.top[(x, z)] == y0 - 1 and hash3(x, 1, z, 37) < 0.5:
            c.set(x, y0 - 1, z, APRON)
            land.kind[(x, z)] = "built"

    # ---- plinth and shaft --------------------------------------------------------------------
    for x, z in A.ring(cx, cz, 6.0, 8.0):
        for h in range(0, 3):
            c.set(x, y0 + h, z, wall)
    for x, z in A.ring(cx, cz, 7.0, 8.0):
        c.set(x, y0 + 3, z, B.stairs(TRIM(x, y0 + 3, z), inward(x, z)))
    top_wall = 26
    for x, z in A.ring(cx, cz, 6.0, 7.0):
        for h in range(0, top_wall + 1):
            c.set(x, y0 + h, z, wall)
    for x, z in A.disc(cx, cz, 6.0):
        for h in range(0, top_wall + 2):
            c.clear(x, y0 + h, z)
        c.set(x, y0 - 1, z, "polished_andesite" if (x + z) % 2 else "stone_bricks")
        for h in (4, 11, 20, 26):
            c.set(x, y0 + h, z, "spruce_planks")
    for h in (2, 9, 18, 24):
        c.set(icx - 3, y0 + h, icz - 3, "lantern[hanging=true]")
        c.set(icx + 2, y0 + h, icz + 2, "lantern[hanging=true]")
        c.set(icx - 3, y0 + h + 1, icz - 3, "spruce_fence", keep=True)
        c.set(icx + 2, y0 + h + 1, icz + 2, "spruce_fence", keep=True)

    # string course
    for x, z in A.ring(cx, cz, 7.0, 8.0):
        c.set(x, y0 + 10, z, B.stairs(TRIM(x, y0 + 10, z), inward(x, z), "top"))

    # ---- openings ----------------------------------------------------------------------------
    faces = {
        "south": ([(icx - 1, icz + 6), (icx, icz + 6)], (0, 1), ("west", "east")),
        "north": ([(icx - 1, icz - 7), (icx, icz - 7)], (0, -1), ("west", "east")),
        "west": ([(icx - 7, icz - 1), (icx - 7, icz)], (-1, 0), ("north", "south")),
        "east": ([(icx + 6, icz - 1), (icx + 6, icz)], (1, 0), ("north", "south")),
    }

    def window(face, h0, rows=3, arch=True, sill=True):
        cells, (ox, oz), (fa, fb) = faces[face]
        for i, (x, z) in enumerate(cells):
            for r in range(rows):
                c.set(x, y0 + h0 + r, z, "glass_pane")
            if arch:
                c.set(x, y0 + h0 + rows, z, B.stairs("stone_bricks", fa if i == 0 else fb, "top"))
                c.set(x, y0 + h0 + rows + 1, z, "stone_bricks")
            c.set(x, y0 + h0 - 1, z, "stone_bricks")
            if sill:
                c.set(x + ox, y0 + h0 - 1, z + oz, B.slab("stone_bricks", "top"))
        # clean jambs
        (x1, z1), (x2, z2) = cells
        tx, tz = x2 - x1, z2 - z1
        for r in range(-1, rows + 1):
            c.set(x1 - tx, y0 + h0 + r, z1 - tz, "stone_bricks")
            c.set(x2 + tx, y0 + h0 + r, z2 + tz, "stone_bricks")

    def glow(face, h):
        cells, (ox, oz), _ = faces[face]
        for (x, z) in cells:
            c.set(x - ox, y0 + h, z - oz, "light[level=15]", keep=True)

    for face in ("north", "east", "west", "south"):
        window(face, 5)
        window(face, 13)
        glow(face, 6)
        glow(face, 14)
    for face in ("north", "east", "west"):
        window(face, 22, rows=2, arch=False, sill=False)
        glow(face, 22)

    # ground door (south), recessed into the plinth
    for i, x in enumerate((icx - 1, icx)):
        for h in range(0, 3):
            c.clear(x, y0 + h, icz + 7)
        hinge = "right" if i == 0 else "left"
        c.set(x, y0, icz + 6, f"spruce_door[facing=south,half=lower,hinge={hinge}]")
        c.set(x, y0 + 1, icz + 6, f"spruce_door[facing=south,half=upper,hinge={hinge}]")
        c.set(x, y0 + 2, icz + 6, B.stairs("stone_bricks", "west" if i == 0 else "east", "top"))
        c.set(x, y0 + 3, icz + 7, "stone_bricks")
    for x in (icx - 2, icx + 1):
        for h in range(0, 3):
            c.set(x, y0 + h, icz + 7, "stone_bricks")
    for x in (icx - 3, icx + 2):
        c.set(x, y0, icz + 8, "stone_brick_wall")
        c.set(x, y0 + 1, icz + 8, "stone_brick_wall")
        c.set(x, y0 + 2, icz + 8, "lantern[hanging=false]")

    # ---- timber gallery ----------------------------------------------------------------------
    g = 20  # floor layer
    for x, z in A.ring(cx, cz, 7.0, 8.0):
        c.set(x, y0 + g - 2, z, B.stairs("spruce_planks", inward(x, z), "top"))
        c.set(x, y0 + g - 1, z, "spruce_planks")
    for x, z in A.ring(cx, cz, 8.0, 9.0):
        c.set(x, y0 + g - 1, z, B.stairs("spruce_planks", inward(x, z), "top"))
    for x, z in A.ring(cx, cz, 7.0, 9.2):
        c.set(x, y0 + g, z, "spruce_planks")
    for x, z in A.ring(cx, cz, 9.2, 10.2):
        c.set(x, y0 + g, z, "spruce_slab[type=top]")
    rail = A.outline(cx, cz, 10.2)
    for x, z in rail:
        c.set(x, y0 + g + 1, z, "spruce_fence")
    for k in range(8):
        a = k * math.pi / 4 + math.pi / 8
        px, pz = min(rail, key=lambda p: abs((math.atan2(p[1] + 0.5 - cz, p[0] + 0.5 - cx) - a + math.pi) % math.tau - math.pi))
        c.set(px, y0 + g + 2, pz, "spruce_fence")
        c.set(px, y0 + g + 3, pz, "lantern[hanging=false]")
    # door from the drum onto the gallery
    for i, x in enumerate((icx - 1, icx)):
        c.clear(x, y0 + g + 1, icz + 6)
        c.clear(x, y0 + g + 2, icz + 6)
        c.set(x, y0 + g + 3, icz + 6, B.stairs("stone_bricks", "west" if i == 0 else "east", "top"))

    # ---- cornice and dome --------------------------------------------------------------------
    for x, z in A.ring(cx, cz, 7.0, 8.0):
        c.set(x, y0 + top_wall, z, B.stairs("stone_bricks", inward(x, z), "top"))
    for x, z in A.ring(cx, cz, 6.0, 8.0):
        c.set(x, y0 + top_wall + 1, z, "stone_bricks")

    rd = 8.4
    yb = y0 + top_wall + 2
    slit = range(icx - 2, icx + 2)
    heights = {}
    for x, z in A.disc(cx, cz, rd):
        if x in slit and z >= icz - 2:
            continue  # the observing slit
        d = A.dist(x, z, cx, cz)
        heights[(x, z)] = yb + 0.6 + math.sqrt(rd * rd - d * d)
    for x, z in A.ring(cx, cz, 7.0, rd):
        c.set(x, yb - 1, z, "dark_prismarine")

    def dome_mat(x, y, z):
        dx, dz = x + 0.5 - cx, z + 0.5 - cz
        if (x in (icx - 3, icx + 2) and z >= icz - 3) or (z == icz - 3 and icx - 3 <= x <= icx + 2):
            return "dark_prismarine"
        if abs(abs(dx) - abs(dz)) < 0.75 and math.hypot(dx, dz) > 2.4:
            return "dark_prismarine"
        worn = 0.16 + (0.3 if y - yb < 2 else 0.0)
        if hash3(x // 2, y // 2, z // 2, 55) < worn:
            return "waxed_weathered_cut_copper"
        return "waxed_oxidized_cut_copper"

    A.shell(c, heights, dome_mat, yb)
    # the slit is closed at its foot by a low sill
    for x in slit:
        for z in range(icz + 5, icz + 9):
            if A.dist(x, z, cx, cz) <= rd:
                c.set(x, yb, z, "dark_prismarine")

    # ---- telescope: a slanted white tube with brass fittings, poking out of the slit --------
    n = 10
    for i, z in enumerate(range(icz - 2, icz - 2 + n)):
        ymid = y0 + top_wall + 3 + i
        for x in (icx - 1, icx):
            if i >= n - 2:
                mat = "waxed_cut_copper"
            elif i in (2, 6):
                mat = "polished_blackstone"
            else:
                mat = "smooth_quartz"
            c.set(x, ymid - 1, z, B.stairs(mat, "north", "top"))
            c.set(x, ymid, z, mat)
            c.set(x, ymid + 1, z, B.stairs(mat, "south"))
    for x in (icx - 1, icx):
        c.set(x, y0 + top_wall + 1, icz - 1, "polished_deepslate")
        c.set(x, y0 + top_wall + 1, icz, "polished_deepslate")
