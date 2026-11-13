"""Observatory tower: stone shaft, timber gallery, copper dome with an open slit and a brass telescope."""
import math

from artkit import arch as A
from artkit import blocks as B
from artkit.canvas import Mix, hash3

from . import instruments, lights, props, study

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
        lights.window(c, x1, y0 + h0, z1, x2, y0 + h0 + rows - 1, z2, (ox, oz))

    def glow(face, h):
        cells, (ox, oz), _ = faces[face]
        for (x, z) in cells:
            c.set(x - ox, y0 + h, z - oz, "light[level=15]", keep=True)

    for face in ("north", "east", "west", "south"):
        window(face, 5)
        glow(face, 6)
        if face != "south":   # the south face carries the clock there
            window(face, 13)
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

    # ---- the astronomical clock, on the string course of the south face ----------------------
    props.place(c, "sky_clock", cx, y0 + 14.5, cz + 7.02, brightness=(15, 9))

    # ---- buttresses on the four diagonals: three steps, each capped with a slope ---------------
    shaft = set(A.ring(cx, cz, 6.0, 7.0))
    for sx in (-1, 1):
        for sz in (-1, 1):
            def cell(a, b):
                return (icx + a if sx > 0 else icx - a - 1), (icz + b if sz > 0 else icz - b - 1)
            for (a, b), top in (((5, 5), 8), ((5, 6), 5), ((6, 5), 5), ((6, 6), 2)):
                x, z = cell(a, b)
                if (x, z) in shaft:
                    continue
                for h in range(-1, top + 1):
                    c.set(x, y0 + h, z, wall)
                if (a, b) == (6, 6):
                    c.set(x, y0 + top + 1, z, B.slab(TRIM(x, y0 + top + 1, z)))
                else:
                    c.set(x, y0 + top + 1, z, B.stairs(TRIM(x, y0 + top + 1, z), inward(x, z)))
                if (x, z) in land.top:
                    land.kind[(x, z)] = "built"

    # ---- ivy up the south-west side, thick at the foot and thinning out below the gallery ------
    for x, z in A.ring(cx, cz, 7.0, 8.0):
        ang = math.degrees(math.atan2(z + 0.5 - cz, x + 0.5 - cx)) % 360.0
        if not 118.0 <= ang <= 232.0:
            continue
        sides = [f for f, dx, dz in (("east", 1, 0), ("west", -1, 0), ("south", 0, 1), ("north", 0, -1))
                 if (x + dx, z + dz) in shaft]
        if not sides:
            continue
        reach = 9.0 + 9.0 * hash3(x // 2, 0, z // 2, 93) - 0.12 * abs(ang - 170.0)
        for h in range(4, 18):
            if c.has(x, y0 + h, z) or h > reach + 2.0 * hash3(x, h // 3, z, 94):
                continue
            if hash3(x, h, z, 95) < 0.86 - 0.03 * h:
                c.set(x, y0 + h, z, "vine[" + ",".join(f"{f}=true" for f in sides) + "]")
        if hash3(x, 1, z, 96) < 0.45 and not c.has(x, y0 + 4, z):
            c.set(x, y0 + 4, z, "azalea_leaves[persistent=true]")

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
        if k == 0:  # the east-south-east post carries the windsock instead of a lantern
            props.place(c, "windsock", px + 0.5, y0 + g + 3, pz + 0.5, brightness=(15, 0))
        else:
            c.set(px, y0 + g + 3, pz, "lantern[hanging=false]")
    # under its edge: a lantern on each of the four sides, a banner on each diagonal
    for dx, dz in ((9, 0), (-10, 0), (0, 9), (0, -10)):
        x, z = icx + dx, icz + dz
        c.set(x, y0 + g, z, "spruce_planks")
        c.set(x, y0 + g - 1, z, "lantern[hanging=true]")
    for sx in (-1, 1):
        for sz in (-1, 1):
            bx, bz = cx + 6.5 * sx, cz + 6.5 * sz
            props.place(c, "star_banner", bx, y0 + g - 0.08, bz, yaw=math.degrees(math.atan2(-sx, sz)))
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
    # inside, the copper is lined: a painted night sky springing from a timber cornice, two layers
    # above the ledge so that what stands there keeps the bare copper behind it
    skin = {(x, y, z) for (x, z), h in heights.items() for y in range(yb, int(h) + 2) if c.has(x, y, z)}
    lowest = {}
    for x, y, z in skin:
        lowest[(x, z)] = min(y, lowest.get((x, z), y))
    spring = yb + 2
    for (x, z), low in lowest.items():
        for y in range(spring, low):
            if any((x + dx, y + dy, z + dz) in skin
                   for dx, dy, dz in ((1, 0, 0), (-1, 0, 0), (0, 0, 1), (0, 0, -1), (0, 1, 0))):
                c.set(x, y, z, "dark_oak_planks" if y == spring else instruments.VAULT)
    # the observing slit is cut out of the finished skin, so its edges stay one block thick and
    # the room under the dome is one open space
    for (x, z), h in heights.items():
        if x in slit and z >= icz - 2:
            for y in range(yb, int(h) + 2):
                c.clear(x, y, z)
    # the slit is closed at its foot by a low sill
    for x in slit:
        for z in range(icz + 5, icz + 9):
            if A.dist(x, z, cx, cz) <= rd:
                c.set(x, yb, z, "dark_prismarine")

    # ---- telescope: custom models on a pier in the middle of the dome floor ------------------
    pivot = (cx, y0 + top_wall + 1 + 4.0, cz)
    props.place(c, "telescope_mount", *pivot, yaw=180.0, brightness=(15, 12))
    props.place(c, "telescope_tube", *pivot, yaw=180.0, turns=(("x", 45.0),), brightness=(15, 12))
    # brass rails on both edges of the slit: they give the stepped copper a clean curved line
    for side in (-2.5, 2.5):
        props.place(c, "dome_rail", cx + side, yb + 0.6, cz, brightness=(15, 0))
    study.furnish(c, cx, cz, y0 + top_wall + 1, yb)
