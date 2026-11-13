"""Stand-in box shells for the interior test scenes, sized to the locked skeleton.

A shell is the empty room the main-building line (c178) will hand over: floor, perimeter walls with
window and door openings, a ceiling, and -- for the double-height entrance hall -- a second-floor
gallery ledge with a railing around an open well plus the grand stair up to it. It is deliberately
plain: facade grammar, mouldings and finished materials are A3/A1's, not ours. This only gives the
interior the right room to stand in while A3's real shell is built, and is dropped once S2 moves the
room into the merged building.

Local frame of a room:
  lx  east   0 = west wall .. W = east wall (the facade/entrance side)
  lz  south  0 = north wall .. D = south wall
  ly  up     0 = floor/paving layer, 1..H = interior air, H+1 = ceiling
origin = (ox, oy, oz) places local (0, 0, 0) in the world. In the master scene oy is the paving
layer, world y = -1 (plan R1 0.3: y=0 is the first air above the paving).
"""
from dataclasses import dataclass

from artkit import blocks as VB
from scenes.obs.common import blocks as B


@dataclass
class Room:
    w: int                 # east span: west wall at lx 0, east wall at lx W
    d: int                 # south span: north wall at lz 0, south wall at lz D
    h: int                 # interior air layers (floor ly 0, ceiling ly H+1)
    name: str = ""
    gallery_y: int = 0     # ly of the gallery floor; 0 = no gallery


# plan R1 0.3 + A3 4.6 (world: star hall z -6..6 => 13 wide; x 5..16 => 12 deep inside walls at
# x4/x17; full height y0..13, ceiling y14; main-storey/gallery floor y6, walk y7).
# Replace with scenes.obs.common.skeleton when it lands.
STARHALL = Room(w=13, d=14, h=14, name="starhall", gallery_y=7)


def _stair(base, facing, half="bottom"):
    return VB.stairs(base, facing, half)


def build_box(c, origin, room, *, floor="wood", gallery=None, door=None, windows=(),
              wings=True, stair="west"):
    """Draw the stand-in shell.

    floor    "checker" (ashlar/slate, entrance hall) or "wood" (spruce, the other rooms).
    gallery  None, "four" (ledge on all four interior edges) or "two" (north and south only).
    door     (lz0, lz1) opening in the east wall at ground, or None.
    windows  iterable of lz where a tall arched light sits in the east wall.
    wings    carve door openings in the north and south walls (to the flanking rooms).
    stair    "west" grand stair up to the gallery, or None.

    Returns dict(lights=[(x, y, z, level)], entities=0): the suggested invisible-light sources for
    A2 (level by plan 3.2: entrance 13, lit window 9, walkway 6) and the display-entity count (0 --
    the shell is all blocks).
    """
    W, D, H = room.w, room.d, room.h
    ox, oy, oz = origin
    put = lambda lx, ly, lz, s: c.set(ox + lx, oy + ly, oz + lz, s)
    lights = []

    ASH, SLATE, DWOOD = B.ASHLAR_FINE.block, B.SLATE_SMOOTH.block, B.DARK_WOOD.block
    FLOORW = B.FLOOR_WOOD.block
    IRON = B.IRON_RIVETED.block
    PLINTH = B.SLATE_BRICK.block

    # ---- foundation and floor ---------------------------------------------------------------
    for lx in range(0, W + 1):
        for lz in range(0, D + 1):
            put(lx, -1, lz, PLINTH)                                  # paving / footing
    for lx in range(1, W):
        for lz in range(1, D):
            if floor == "checker":
                put(lx, 0, lz, ASH if (lx + lz) % 2 == 0 else SLATE)
            else:
                put(lx, 0, lz, FLOORW)

    # ---- perimeter walls --------------------------------------------------------------------
    for ly in range(1, H + 1):
        for lx in range(0, W + 1):
            put(lx, ly, 0, ASH)
            put(lx, ly, D, ASH)
        for lz in range(0, D + 1):
            put(0, ly, lz, ASH)
            put(W, ly, lz, ASH)
    for lx in range(0, W + 1):                                       # a dark plinth course
        put(lx, 1, 0, PLINTH); put(lx, 1, D, PLINTH)
    for lz in range(0, D + 1):
        put(0, 1, lz, PLINTH); put(W, 1, lz, PLINTH)

    # ---- east wall openings: the entrance door + fanlight, and tall windows -----------------
    if door:
        z0, z1 = door
        for lz in range(z0, z1 + 1):
            for ly in range(1, 6):                                   # door, world y0..4
                c.clear(ox + W, oy + ly, oz + lz)
            put(W, 6, lz, B.WINDOW_LIT.pane); put(W, 7, lz, B.WINDOW_LIT.pane)  # fanlight y5..6
            lights.append((ox + W - 1, oy + 2, oz + lz, 13))         # entrance, first rank
    for lz in windows:                                               # arched light, world y8..13
        for ly in range(9, H + 1):
            put(W, ly, lz, B.WINDOW_DARK.pane if lz % 2 else B.WINDOW_LIT.pane)
        if lz % 2 == 0:
            lights.append((ox + W - 1, oy + 11, oz + lz, 9))         # lit window, second rank

    # ---- wing doorways in the north and south walls (ground + gallery) ----------------------
    if wings:
        for lx in (W // 2 - 1, W // 2, W // 2 + 1):
            for ly in range(1, 6):                                   # ground door to the wing
                c.clear(ox + lx, oy + ly, oz + 0)
                c.clear(ox + lx, oy + ly, oz + D)
            if room.gallery_y:                                       # gallery door to the wing
                for ly in range(room.gallery_y + 1, room.gallery_y + 5):
                    c.clear(ox + lx, oy + ly, oz + 0)
                    c.clear(ox + lx, oy + ly, oz + D)

    # ---- second-floor gallery ledge + railing around the open well --------------------------
    if gallery and room.gallery_y:
        gy = room.gallery_y
        width = 2
        edges = {"north", "south"} | ({"west", "east"} if gallery == "four" else set())

        def ledge(lx, lz):
            put(lx, gy, lz, DWOOD)                                   # gallery floor at y6

        for lx in range(1, W):
            for k in range(width):
                if "north" in edges:
                    ledge(lx, 1 + k)
                if "south" in edges:
                    ledge(lx, D - 1 - k)
        for lz in range(1, D):
            for k in range(width):
                if "west" in edges:
                    ledge(1 + k, lz)
                if "east" in edges:
                    ledge(W - 1 - k, lz)
        # railing on the inner edge of the ledge, facing the well
        rail = B.IRON_BARS
        if "north" in edges:
            for lx in range(1, W):
                put(lx, gy + 1, 1 + width, rail)
        if "south" in edges:
            for lx in range(1, W):
                put(lx, gy + 1, D - 1 - width, rail)
        if "west" in edges:
            for lz in range(1, D):
                put(1 + width, gy + 1, lz, rail)
        if "east" in edges:
            for lz in range(1, D):
                put(W - 1 - width, gy + 1, lz, rail)

    # ---- grand stair, west side, floor up to the gallery ------------------------------------
    if stair == "west" and room.gallery_y:
        for k in range(1, room.gallery_y + 1):
            lz = k
            put(1, k, lz, _stair(IRON, "south"))
            put(2, k, lz, IRON)
            c.clear(ox + 1, oy + k + 1, oz + lz)
        lights.append((ox + 2, oy + 2, oz + 1, 13))                 # stair foot, first rank

    # ---- ceiling: dark-wood soffit broken by riveted-iron beams -----------------------------
    cy = H + 1
    for lx in range(1, W):
        for lz in range(1, D):
            put(lx, cy, lz, DWOOD)
    for lz in range(2, D, 4):                                        # beams every four bays
        for lx in range(1, W):
            put(lx, cy, lz, IRON)

    return {"lights": lights, "entities": 0}
