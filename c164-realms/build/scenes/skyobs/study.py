"""The room under the dome: the astronomer's study around the telescope pier.

Seen from the hatch: the observer's steps under the eyepiece, the chart desk to the west, the
orrery and the star globe to the east, books along the ledge behind, lanterns on chains from the
ribs. The slit is to the south.
"""
import math

from artkit import arch as A

from . import props


def furnish(c, cx, cz, fy, yb):
    """(cx, cz): centre of the room on a block corner. fy: first air layer above the plank floor.
    yb: first layer of the dome shell (the ledge around the room is the layer below it)."""
    icx, icz = int(cx), int(cz)

    # ---- floor: a four-pointed star let into the planks, a dark border -----------------------
    p = 2.0 / 3.0
    for x, z in A.disc(cx, cz, 6.0):
        dx, dz = x + 0.5 - cx, z + 0.5 - cz
        u, v = (dx + dz) / math.sqrt(2.0), (dx - dz) / math.sqrt(2.0)
        if math.hypot(dx, dz) > 5.0:
            state = "dark_oak_planks"
        elif abs(dx) ** p + abs(dz) ** p <= 5.4 ** p:
            state = "dark_oak_planks"
        elif abs(u) ** p + abs(v) ** p <= 4.2 ** p:
            state = "birch_planks"
        else:
            state = "spruce_planks"
        c.set(x, fy - 1, z, state)

    # ---- hatch with a ladder from the room below, north-west ---------------------------------
    hx, hz = icx - 3, icz - 5
    for y in range(fy - 6, fy):
        c.set(hx, y, hz, "ladder[facing=south]")
    c.set(hx, fy, hz, "spruce_trapdoor[facing=south,half=bottom,open=true]")

    # ---- the observer's place under the eyepiece ---------------------------------------------
    props.place(c, "observer_steps", cx, fy, cz - 3.45)

    # ---- west: chart desk on a rug, a chair, the big star map behind -------------------------
    for x in range(icx - 6, icx - 2):
        for z in range(icz - 2, icz + 3):
            if A.dist(x, z, cx, cz) < 5.6:
                edge = x in (icx - 6, icx - 3) or z in (icz - 2, icz + 2)
                c.set(x, fy, z, "red_carpet" if not edge else "brown_carpet")
    props.place(c, "chart_desk", cx - 4.4, fy + 1.0 / 16.0, cz + 0.5, yaw=-90.0)
    c.set(icx - 3, fy, icz, "dark_oak_stairs[facing=east,half=bottom]")
    props.place(c, "star_easel", cx - 3.3, fy, cz + 4.0, yaw=-128.0)

    # ---- east: orrery on a stone drum, star globe --------------------------------------------
    ox, oz = icx + 3, icz - 4
    c.set(ox, fy, oz, "chiseled_stone_bricks")
    props.place(c, "orrery", ox + 0.5, fy + 1.0, oz + 0.5, yaw=20.0)
    c.set(ox, fy + 3, oz, "light[level=11]")
    props.place(c, "star_globe", cx + 3.9, fy, cz + 3.4, yaw=35.0)

    # ---- the ledge: books along the north, odds and ends elsewhere ---------------------------
    ledge = sorted(A.ring(cx, cz, 6.0, 7.0), key=lambda q: math.atan2(q[1] + 0.5 - cz, q[0] + 0.5 - cx))
    for x, z in ledge:
        if z == icz - 7 and icx - 3 <= x <= icx + 2:
            for k in (0, 1):
                slots = ",".join(f"slot_{i}_occupied={'true' if (x * 7 + i * 3 + k * 5) % 4 else 'false'}" for i in range(6))
                c.set(x, yb + k, z, f"chiseled_bookshelf[facing=south,{slots}]")
    dressing = [
        # dx, dz from the centre, what, turn
        (-6.5, -2.6, "book_pile", 20.0), (-6.5, 2.4, "book_row", -90.0), (-5.4, 4.3, "book_pile", -40.0),
        (6.5, -1.4, "book_row", 90.0), (6.5, 1.5, "book_pile", 75.0), (5.3, -4.4, "book_pile", 130.0),
        (-4.3, -5.3, "book_row", -140.0),
    ]
    for dx, dz, name, turn in dressing:
        props.place(c, name, cx + dx, yb, cz + dz, yaw=turn)
    for dx, dz, state in ((-6.5, 0.5, "candle[candles=3,lit=true]"), (6.5, 3.5, "candle[candles=2,lit=true]"),
                          (6.5, -3.5, "potted_fern"), (-5.5, -3.5, "candle[candles=1,lit=true]"),
                          (3.5, -6.5, "lantern[hanging=false]"), (-6.5, 3.5, "flower_pot"),
                          (5.5, 4.5, "decorated_pot"), (4.5, 5.5, "lantern[hanging=false]"),
                          (-4.5, 5.5, "lantern[hanging=false]")):
        x, z = math.floor(cx + dx), math.floor(cz + dz)
        if not c.has(x, yb, z):
            c.set(x, yb, z, state)

    # ---- lanterns on chains from the ribs ----------------------------------------------------
    for dx, dz in ((-4, -3), (3, -4), (-4, 3), (3, 3)):
        x, z = icx + dx, icz + dz
        skin = [y for y in range(yb + 10, fy + 2, -1) if c.has(x, y, z)]
        if not skin:
            continue
        under = min(skin) - 1   # first free cell below the copper
        low = max(fy + 3, under - 2)
        for y in range(low + 1, under + 1):
            c.set(x, y, z, "waxed_copper_chain[axis=y]")
        c.set(x, low, z, "waxed_copper_lantern[hanging=true]")
