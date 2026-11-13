"""Keeper's house: stone ground floor, jettied timber-framed upper floor, steep tiled roof.

The long axis runs east-west and the front faces south. Over the double door a gabled bay stands
out on two posts; a lean-to for firewood leans against the west gable beside the chimney, which
smokes.
"""
from artkit import arch as A
from artkit import blocks as B
from artkit.canvas import Mix

from . import lights

STONE = Mix({"cobblestone": 30, "stone_bricks": 34, "andesite": 14, "mossy_cobblestone": 10, "stone": 8,
             "mossy_stone_bricks": 4}, seed=41)
FOUND = Mix({"cobblestone": 55, "mossy_cobblestone": 25, "stone": 20}, seed=42)
PLASTER = Mix({"calcite": 100}, seed=43)
ROOF = Mix({"bricks": 72, "granite": 18, "mud_bricks": 10}, seed=44)
LOG_X, LOG_Y, LOG_Z = "spruce_log[axis=x]", "spruce_log[axis=y]", "spruce_log[axis=z]"
PANE = "glass_pane"


def _bay(c, land, xa, xb, zb, y0):
    """The gabled bay over the door: posts xa and xb of the front wall (line zb) carry it two
    blocks forward on two more posts; below is the porch."""
    yb = y0 + 4
    zf = zb + 2
    # porch: paving, posts, low rails at the sides, brackets under the beam, a lantern
    for x in range(xa, xb + 1):
        for z in range(zb, zf + 1):
            for y in range(y0, y0 + 4):
                c.clear(x, y, z)
            c.set(x, y0 - 1, z, "polished_andesite" if (x + z) % 2 else "stone_bricks")
            if (x, z) in land.top:
                land.kind[(x, z)] = "built"
    for x, inner in ((xa, "east"), (xb, "west")):
        for y in range(y0, y0 + 4):
            c.set(x, y, zf, LOG_Y)
        c.set(x, y0, zb + 1, "spruce_fence")
        c.set(x + (1 if inner == "east" else -1), y0 + 3, zf, B.stairs("spruce_planks", "west" if inner == "east" else "east", "top"))
    c.set(xb - 1, y0 + 3, zb + 1, "lantern[hanging=true]")
    # the room above: floor, beams, framed front with a window, plastered cheeks
    for x in range(xa, xb + 1):
        for z in (zb + 1, zf):
            c.set(x, yb, z, "spruce_planks")
        c.set(x, yb, zf, LOG_X)
        c.set(x, y0 + 7, zf, LOG_X)
    for x in (xa, xb):
        c.set(x, yb, zb + 1, LOG_Z)
        c.set(x, y0 + 7, zb + 1, LOG_Z)
        for y in (y0 + 5, y0 + 6):
            c.set(x, y, zf, LOG_Y)
            c.set(x, y, zb + 1, PLASTER)
    for x in range(xa + 1, xb):
        for y in (y0 + 5, y0 + 6):
            c.set(x, y, zf, PANE)
            c.clear(x, y, zb)                      # the bay opens into the upper room
        c.set(x, y0 + 8, zf, PLASTER)
        c.set(x, yb, zf + 1, "flowering_azalea_leaves[persistent=true]")
    lights.window(c, xa + 1, y0 + 5, zf, xb - 1, y0 + 6, zf, (0, 1))
    # its roof: a gable to the front, running back until it meets the main roof
    half = (xb - xa + 3) // 2
    for i in range(half):
        y = y0 + 7 + i
        for x, face in ((xa - 1 + i, "east"), (xb + 1 - i, "west")):
            for z in range(zf + 1, zb - i, -1):
                if z == zf + 1:
                    c.set(x, y, z, B.stairs("spruce_planks", face))
                    c.set(x, y - 1, z, B.stairs("spruce_planks", "west" if face == "east" else "east", "top"))
                else:
                    c.set(x, y, z, B.stairs(ROOF(x, y, z), face))
                # what is left of the main roof underneath is inside the bay now
                for yy in range(y0 + 7, y):
                    if z <= zb + 1 and c.name(x, yy, z) not in (None, "spruce_log"):
                        c.clear(x, yy, z)


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
    bay = door_dx // 3            # the panel over the door, where the bay stands out
    for p in range(panels):
        xa = x0 + 3 * p + 1
        if 0 < p < panels - 1:
            for x in (xa, xa + 1):
                for y in (y0 + 5, y0 + 6):
                    c.set(x, y, za, PANE)
                    if p != bay:
                        c.set(x, y, zb, PANE)
                if p != bay:
                    c.set(x, yb, zb + 1, "flowering_azalea_leaves[persistent=true]")
            if p != bay:
                lights.window(c, xa, y0 + 5, zb, xa + 1, y0 + 6, zb, (0, 1))
            lights.window(c, xa, y0 + 5, za, xa + 1, y0 + 6, za, (0, -1))
    for x in (x0, x1):
        for z in (z0 + 1, z0 + 2) if x == x0 else (z0 + 1, z0 + 2, z1 - 2, z1 - 1):
            for y in (y0 + 5, y0 + 6):
                c.set(x, y, z, PANE)
    lights.window(c, x0, y0 + 5, z0 + 1, x0, y0 + 6, z0 + 2, (-1, 0))
    lights.window(c, x1, y0 + 5, z0 + 1, x1, y0 + 6, z0 + 2, (1, 0))
    lights.window(c, x1, y0 + 5, z1 - 2, x1, y0 + 6, z1 - 1, (1, 0))
    for x, out in ((x0, -1), (x1, 1)):   # attic windows in the gables
        lights.window(c, x, y0 + 9, zm, x, y0 + 10, zm, (out, 0))

    xd = x0 + door_dx
    for i, x in enumerate((xd, xd + 1)):
        hinge = "right" if i == 0 else "left"
        c.set(x, y0, z1, f"spruce_door[facing=south,half=lower,hinge={hinge}]")
        c.set(x, y0 + 1, z1, f"spruce_door[facing=south,half=upper,hinge={hinge}]")
        c.set(x, y0 + 2, z1, "stone_bricks")
    _bay(c, land, x0 + 3 * bay, x0 + 3 * bay + 3, zb, y0)

    def ground_window(xa, z, out, shutters=True):
        for x in (xa, xa + 1):
            for y in (y0 + 1, y0 + 2):
                c.set(x, y, z, PANE)
            c.set(x, y0, z + out, B.stairs("stone_bricks", "north" if out > 0 else "south", "top"))
        lights.window(c, xa, y0 + 1, z, xa + 1, y0 + 2, z, (0, out))
        if shutters:
            face = "south" if out > 0 else "north"
            for x in (xa - 1, xa + 2):
                for y in (y0 + 1, y0 + 2):
                    c.set(x, y, z + out, f"spruce_trapdoor[facing={face},open=true]")

    for xa in (x0 + 1, x0 + 7, x0 + 10):
        if xa + 1 < x1 and not (xa <= xd + 1 and xd <= xa + 1):
            ground_window(xa, z1, 1)
    for xa in (x0 + 3, x0 + 8):
        ground_window(xa, z0, -1, shutters=False)
    for z in (zm - 1, zm):
        for y in (y0 + 1, y0 + 2):
            c.set(x1, y, z, PANE)
    lights.window(c, x1, y0 + 1, zm - 1, x1, y0 + 2, zm, (1, 0))

    # ---- dormers -----------------------------------------------------------------------------
    for xc in (x1 - 2,):
        for y in (y0 + 8, y0 + 9):
            c.set(xc - 1, y, zb, LOG_Y)
            c.set(xc + 1, y, zb, LOG_Y)
            c.set(xc, y, zb, PANE)
        lights.window(c, xc, y0 + 8, zb, xc, y0 + 9, zb, (0, 1))
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
        # the fire that makes the smoke sits in the head of the stack, inside an iron cowl
        c.set(xc, y0 + 15, z, "soul_campfire[lit=true,signal_fire=true]")
        c.set(xc - 1, y0 + 15, z, "iron_trapdoor[open=true,facing=west]")
        c.set(xc + 1, y0 + 15, z, "iron_trapdoor[open=true,facing=east]")
    c.set(xc, y0 + 15, zm, "iron_trapdoor[open=true,facing=north]")
    c.set(xc, y0 + 15, zm + 3, "iron_trapdoor[open=true,facing=south]")
    for z, face in ((zm, "south"), (zm + 3, "north")):
        for y in range(y0 - 1, y0 + 3):
            c.set(xc, y, z, STONE)
        A.fill_down(c, xc, y0 - 2, z, FOUND(xc, y0 - 2, z))
        c.set(xc, y0 + 3, z, B.stairs("stone_bricks", face))

    # ---- eaves: one more course, laid flatter, so the roof kicks out at its foot -------------
    for x in range(x0 - 1, x1 + 2):
        verge = x in (x0 - 1, x1 + 1)
        for z in (zb + 2, za - 2):
            if not c.has(x, y0 + 6, z) and not c.has(x, y0 + 7, z):
                c.set(x, y0 + 6, z, "spruce_slab[type=top]" if verge else B.slab(ROOF(x, y0 + 6, z), "top"))

    # ---- lean-to for the firewood, against the west gable north of the chimney ---------------
    for z in range(z0 - 1, zm):
        c.set(x0 - 1, y0 + 3, z, B.slab(ROOF(x0 - 1, y0 + 3, z), "top"))
        c.set(x0 - 2, y0 + 3, z, B.slab(ROOF(x0 - 2, y0 + 3, z), "bottom"))
        c.set(x0 - 3, y0 + 2, z, B.slab(ROOF(x0 - 3, y0 + 2, z), "top"))
        for x in (x0 - 1, x0 - 2):
            if (x, z) in land.top:
                c.set(x, y0 - 1, z, "coarse_dirt" if (x + z) % 3 else "gravel")
                land.kind[(x, z)] = "built"
                for y in range(y0, y0 + 3):
                    c.clear(x, y, z)
    for z in (z0, zm - 1):
        for y in range(y0, y0 + 3):
            c.set(x0 - 2, y, z, LOG_Y)
    c.set(x0 - 2, y0, z0 + 2, "barrel[facing=up]")

    # ---- light inside ------------------------------------------------------------------------
    for x in (x0 + 3, x1 - 3):
        c.set(x, y0 + 3, zm, "lantern[hanging=true]")
        c.set(x, y0 + 5, zm, "lantern[hanging=false]")
    # windows should glow at dusk: invisible light just inside the long walls
    for x in range(x0 + 1, x1, 2):
        for z in (z0 + 1, z1 - 1):
            for y in (y0 + 1, y0 + 6):
                c.set(x, y, z, "light[level=15]", keep=True)
    return {"ridge_y": y0 + 7 + half + 0.5, "ridge_z": ridge_z + 0.5}
