"""Star hall -- the double-height entrance hall (plan section 8, view V7). Two compared versions.

a  "central well"  the orrery hangs dead-centre in a square light-well, a gallery runs round all
   four sides, the brass meridian crosses it straight north-south; formal and symmetric, the old
   observatory's great central hall.
b  "raking aisle"  the orrery is pushed west towards the rotunda and the gallery keeps to the north
   and south only, so from the east door the eye runs the length of the hall to the orrery and the
   grand stair beyond; the brass meridian rakes across as the main axis. More depth and lead-in.

Both read the same list: one hero (the hung orrery, A5, turning), three layers of small things on
floor/wall/ceiling, something moving (orrery, clock pendulum) and something glowing (lit fanlight,
lamps, dial). Machines (A5) and some props (c179) are stand-ins from stubs.py on fixed anchors.
"""
from artkit import blocks as VB
from scenes.obs.common import blocks as B

from . import shell, stubs

ROOM = shell.STARHALL
DOOR = (ROOM.d // 2 - 1, ROOM.d // 2 + 1)        # east door, world z -1..1
WINDOWS = (3, ROOM.d - 3)                          # tall east windows, world z -4 and +4


def _dado(c, origin):
    """Dark-wood wainscot on the lower walls with a brass belt rail, broken where openings are."""
    ox, oy, oz = origin
    W, D = ROOM.w, ROOM.d
    perim = [(lx, lz) for lx in range(0, W + 1) for lz in (0, D)]
    perim += [(lx, lz) for lz in range(1, D) for lx in (0, W)]
    for lx, lz in perim:
        for ly in range(1, 4):
            if c.has(ox + lx, oy + ly, oz + lz):
                c.set(ox + lx, oy + ly, oz + lz, B.DARK_WOOD.block)
        if c.has(ox + lx, oy + 4, oz + lz):
            c.set(ox + lx, oy + 4, oz + lz, B.BRASS_PLATE.block)


def _meridian(c, origin, version):
    """The brass meridian inlaid in the floor: straight north-south for a, raking for b."""
    ox, oy, oz = origin
    W, D = ROOM.w, ROOM.d
    for lz in range(1, D):
        if version == "a":
            lx = W // 2
        else:
            lx = max(2, min(W - 2, round((W - 1) * (D - lz) / D)))
        c.set(ox + lx, oy + 1, oz + lz, B.BRASS_INLAY)


def build_starhall(c, origin, roles=B, *, version="a"):
    """Draw the star hall at ``origin`` (world coords of local (0,0,0), the NW floor corner).

    Returns dict(version, entities, lights): display-entity count (0 here -- all blocks; machines
    and props add theirs when they land) and the suggested invisible-light sources for A2.
    """
    version = version.lower()
    W, D, H = ROOM.w, ROOM.d, ROOM.h
    gy = ROOM.gallery_y
    cx, cz = W // 2, D // 2

    res = shell.build_box(
        c, origin, ROOM, floor="checker",
        gallery="four" if version == "a" else "two",
        door=DOOR, windows=WINDOWS, wings=True, stair="west",
    )
    lights = list(res["lights"])
    _dado(c, origin)
    _meridian(c, origin, version)

    # ---- hero: the great orrery, hung from the ceiling --------------------------------------
    orx = cx if version == "a" else cx - 2
    orz = cz
    ory = gy + 4                                           # hangs above the gallery, in the well
    stubs.orrery(c, origin, orx, ory, orz)
    stubs.chain_up(c, origin, orx, ory + 3, orz, H + 1)
    lights.append((origin[0] + orx, origin[1] + ory + 2, origin[2] + orz, 10))   # halo, 2nd rank

    # ---- mother clock against the wall, on the entrance axis --------------------------------
    lights.append(stubs.mother_clock(c, origin, cx + (3 if version == "a" else 0), 1, 1,
                                     facing="south"))

    # ---- switchboard by the grand stair (west) ---------------------------------------------
    stubs.switchboard(c, origin, 1, 1, cz + 2, facing="east", width=3)

    # ---- star charts on the flank walls -----------------------------------------------------
    stubs.wall_chart(c, origin, 1, 3, 3, facing="east")
    stubs.wall_chart(c, origin, W - 1, 3, D - 4, facing="west")

    # ---- waiting benches by the door --------------------------------------------------------
    stubs.bench(c, origin, W - 2, 1, cz - 4, length=3, axis="z")
    stubs.bench(c, origin, W - 2, 1, cz + 2, length=3, axis="z")

    # ---- lamps: pendants in/around the well, bulbs on the gallery walkway -------------------
    if version == "a":
        for dx, dz in ((-3, -3), (3, -3), (-3, 3), (3, 3)):
            lights.append(stubs.pendant(c, origin, cx + dx, gy + 2, cz + dz, H + 1, level=9))
    else:
        for dz in (-4, 0, 4):
            lights.append(stubs.pendant(c, origin, cx + 2, gy + 2, cz + dz, H + 1, level=9))
    for lz in range(3, D, 4):                               # third-rank bulbs along the ledge
        lights.append(stubs.wall_lamp(c, origin, 1, gy + 2, lz, level=6))
        lights.append(stubs.wall_lamp(c, origin, W - 1, gy + 2, lz, level=6))

    return {"version": version, "entities": 0, "lights": lights}
