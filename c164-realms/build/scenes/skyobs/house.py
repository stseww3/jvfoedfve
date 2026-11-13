"""Keeper's house: stone ground floor, jettied timber-framed upper floor, steep slate roof.

The long axis runs east-west and the front faces south.
"""
from artkit import arch as A
from artkit import blocks as B
from artkit.canvas import Mix

STONE = Mix({"cobblestone": 30, "stone_bricks": 34, "andesite": 14, "mossy_cobblestone": 10, "stone": 8,
             "mossy_stone_bricks": 4}, seed=41)
FOUND = Mix({"cobblestone": 55, "mossy_cobblestone": 25, "stone": 20}, seed=42)
PLASTER = Mix({"calcite": 100}, seed=43)
ROOF = Mix({"bricks": 72, "granite": 18, "mud_bricks": 10}, seed=44)
LOG_X, LOG_Y, LOG_Z = "spruce_log[axis=x]", "spruce_log[axis=y]", "spruce_log[axis=z]"
PANE = "glass_pane"


def build(c, land, x0, x1, z0, z1, y0, door_dx=4):
    """Footprint x0..x1 by z0..z1 (inclusive); y0 is the first wall layer (floor is y0 - 1)."""
    zm = (z0 + z1) // 2
    za, zb = z0 - 1, z1 + 1

    # ---- site --------------------------------------------------------------------------------
    for x in range(x0 - 2, x1 + 3):
        for z in range(z0 - 3, z1 + 4):
            for y in range(y0, y0 + 18):
                c.clear(x, y, z)
    for x in range(x0, x1 + 1):
        for z in range(z0, z1 + 1):
            inside = x0 < x < x1 and z0 < z < z1
            c.set(x, y0 - 1, z, "spruce_planks" if inside else FOUND(x, y0 - 1, z))
            A.fill_down(c, x, y0 - 2, z, FOUND(x, y0 - 2, z))
            land.kind[(x, z)] = "built"
            land.top[(x, z)] = y0 - 1

    # ---- ground floor (stone) ----------------------------------------------------------------
    for y in range(y0, y0 + 4):
        for x in range(x0, x1 + 1):
            c.set(x, y, z0, STONE)
            c.set(x, y, z1, STONE)
        for z in range(z0, z1 + 1):
            c.set(x0, y, z, STONE)
            c.set(x1, y, z, STONE)

    # ---- jetty beams and upper floor ---------------------------------------------------------
    yb = y0 + 4
    for x in range(x0, x1 + 1):
        for z in range(z0, z1 + 1):
            c.set(x, yb, z, "spruce_planks")
        c.set(x, yb, za, LOG_X)
        c.set(x, yb, zb, LOG_X)
    for z in range(za, zb + 1):
        c.set(x0, yb, z, LOG_Z)
        c.set(x1, yb, z, LOG_Z)
    for x in range(x0, x1 + 1, 2):
        c.set(x, yb - 1, zb, B.stairs("spruce_planks", "north", "top"))
        c.set(x, yb - 1, za, B.stairs("spruce_planks", "south", "top"))

    # ---- timber-framed upper walls -----------------------------------------------------------
    for y in (y0 + 5, y0 + 6):
        for x in range(x0, x1 + 1):
            post = (x - x0) % 3 == 0
            c.set(x, y, za, LOG_Y if post else PLASTER)
            c.set(x, y, zb, LOG_Y if post else PLASTER)
        for z in range(za, zb + 1):
            post = z in (za, zb, zm)
            c.set(x0, y, z, LOG_Y if post else PLASTER)
            c.set(x1, y, z, LOG_Y if post else PLASTER)
    for x in range(x0, x1 + 1):
        c.set(x, y0 + 7, za, LOG_X)
        c.set(x, y0 + 7, zb, LOG_X)
    for z in range(za, zb + 1):
        c.set(x0, y0 + 7, z, LOG_Z)
        c.set(x1, y0 + 7, z, LOG_Z)

    # ---- roof --------------------------------------------------------------------------------
    n = (zb + 1) - (za - 1) + 1
    half = n // 2
    for x in range(x0 - 1, x1 + 2):
        verge = x in (x0 - 1, x1 + 1)
        for i in range(half):
            y = y0 + 7 + i
            zs, zn = zb + 1 - i, za - 1 + i
            if verge:
                c.set(x, y, zs, B.stairs("spruce_planks", "north"))
                c.set(x, y, zn, B.stairs("spruce_planks", "south"))
                c.set(x, y - 1, zs, B.stairs("spruce_planks", "south", "top"))
                c.set(x, y - 1, zn, B.stairs("spruce_planks", "north", "top"))
            else:
                c.set(x, y, zs, B.stairs(ROOF(x, y, zs), "north"))
                c.set(x, y, zn, B.stairs(ROOF(x, y, zn), "south"))
        ridge_z = za - 1 + half
        c.set(x, y0 + 7 + half, ridge_z, "spruce_slab[type=bottom]" if verge else B.slab(ROOF(x, 0, ridge_z)))
        if verge:
            c.set(x, y0 + 6 + half, ridge_z, "spruce_planks")

    # gables: tie beam, plaster, king post, attic window
    rows = half - 2
    for k in range(rows + 1):
        y = y0 + 8 + k
        for x in (x0, x1):
            for z in range(z0 + k, z1 - k + 1):
                if k == 0:
                    c.set(x, y, z, LOG_Z)
                elif z == zm and k >= 3:
                    c.set(x, y, z, LOG_Y)
                elif z == zm and k in (1, 2):
                    c.set(x, y, z, PANE)
                else:
                    c.set(x, y, z, PLASTER)

    # ---- windows and doors -------------------------------------------------------------------
    panels = (x1 - x0) // 3
    for p in range(panels):
        xa = x0 + 3 * p + 1
        if 0 < p < panels - 1:
            for x in (xa, xa + 1):
                for y in (y0 + 5, y0 + 6):
                    c.set(x, y, zb, PANE)
                    c.set(x, y, za, PANE)
                c.set(x, yb, zb + 1, "flowering_azalea_leaves[persistent=true]")
    for x in (x0, x1):
        for z in (z0 + 1, z0 + 2) if x == x0 else (z0 + 1, z0 + 2, z1 - 2, z1 - 1):
            for y in (y0 + 5, y0 + 6):
                c.set(x, y, z, PANE)

    xd = x0 + door_dx
    c.set(xd, y0, z1, "spruce_door[facing=south,half=lower,hinge=left]")
    c.set(xd, y0 + 1, z1, "spruce_door[facing=south,half=upper,hinge=left]")
    c.set(xd, y0 + 2, z1, "stone_bricks")
    c.set(xd + 1, y0 + 3, zb, "lantern[hanging=true]")

    def ground_window(xa, z, out, shutters=True):
        for x in (xa, xa + 1):
            for y in (y0 + 1, y0 + 2):
                c.set(x, y, z, PANE)
            c.set(x, y0, z + out, B.stairs("stone_bricks", "north" if out > 0 else "south", "top"))
        if shutters:
            face = "south" if out > 0 else "north"
            for x in (xa - 1, xa + 2):
                for y in (y0 + 1, y0 + 2):
                    c.set(x, y, z + out, f"spruce_trapdoor[facing={face},open=true]")

    for xa in (x0 + 1, x0 + 7, x0 + 10):
        if xa + 1 < x1 and not (xa <= xd <= xa + 1):
            ground_window(xa, z1, 1)
    for xa in (x0 + 3, x0 + 8):
        ground_window(xa, z0, -1, shutters=False)
    for z in (zm - 1, zm):
        for y in (y0 + 1, y0 + 2):
            c.set(x1, y, z, PANE)

    # ---- dormers -----------------------------------------------------------------------------
    for xc in (x0 + 3, x1 - 3):
        for y in (y0 + 8, y0 + 9):
            c.set(xc - 1, y, zb, LOG_Y)
            c.set(xc + 1, y, zb, LOG_Y)
            c.set(xc, y, zb, PANE)
        c.set(xc, y0 + 10, zb, PLASTER)
        for y, dx in ((y0 + 9, 2), (y0 + 10, 1)):
            for z in range(zb + 2 - (y - (y0 + 7)), zb + 2):
                c.set(xc - dx, y, z, B.stairs("bricks", "east"))
                c.set(xc + dx, y, z, B.stairs("bricks", "west"))
        for z in range(zb - 2, zb + 2):
            c.set(xc, y0 + 11, z, "brick_slab[type=bottom]")

    # ---- chimney on the west gable -----------------------------------------------------------
    xc = x0 - 1
    for z in (zm + 1, zm + 2):
        for y in range(y0 - 1, y0 + 15):
            c.set(xc, y, z, STONE)
        A.fill_down(c, xc, y0 - 2, z, FOUND(xc, y0 - 2, z))
        c.set(xc, y0 + 15, z, "stone_brick_wall")
    for z, face in ((zm, "south"), (zm + 3, "north")):
        for y in range(y0 - 1, y0 + 3):
            c.set(xc, y, z, STONE)
        A.fill_down(c, xc, y0 - 2, z, FOUND(xc, y0 - 2, z))
        c.set(xc, y0 + 3, z, B.stairs("stone_bricks", face))

    # ---- light inside ------------------------------------------------------------------------
    for x in (x0 + 3, x1 - 3):
        c.set(x, y0 + 3, zm, "lantern[hanging=true]")
        c.set(x, y0 + 5, zm, "lantern[hanging=false]")
    # windows should glow at dusk: invisible light just inside the long walls
    for x in range(x0 + 1, x1, 2):
        for z in (z0 + 1, z1 - 1):
            for y in (y0 + 1, y0 + 6):
                c.set(x, y, z, "light[level=15]", keep=True)
