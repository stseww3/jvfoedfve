"""Placeholders for the heavy machines (A5) and the few props (c179) an interior needs to read,
built from occupancy-table blocks and palette colours only.

They are deliberately blocky: real orreries, clocks, switchboards and lamps are modelled by the
machine and prop lines and drop onto the same anchor points (the same centre/footprint arguments)
without changing the room code. Each helper works in a room's local frame plus an ``origin`` world
offset, matching shell.py. Lamp helpers return their suggested invisible-light source so the room
can hand the list to A2.
"""
from artkit import blocks as VB
from scenes.obs.common import blocks as B


def _set(c, origin, lx, ly, lz, state):
    ox, oy, oz = origin
    c.set(ox + lx, oy + ly, oz + lz, state)


def orrery(c, origin, lx, ly, lz):
    """Stand-in great orrery hung at (lx, ly, lz): a brass armillary of two rings about a verdigris
    sun, on a chain up to the ceiling. Replaced by A5's rotating model (hung from the same point)."""
    sun = B.VERDIGRIS
    arm = B.BRASS_PLATE.block
    for d in (-2, -1, 1, 2):                                   # horizontal brass ring (ecliptic)
        _set(c, origin, lx + d, ly, lz, arm)
        _set(c, origin, lx, ly, lz + d, arm)
    for d in (-2, -1, 1, 2):                                   # vertical brass ring (meridian ring)
        _set(c, origin, lx, ly + d, lz, arm)
    _set(c, origin, lx, ly, lz, sun)                           # the little sun at the centre
    _set(c, origin, lx + 2, ly, lz + 2, B.BRASS_COLUMN + "[axis=y]")   # six planet arms (stubbed)
    _set(c, origin, lx - 2, ly, lz - 2, B.BRASS_COLUMN + "[axis=y]")


def chain_up(c, origin, lx, ly0, lz, ly1):
    for ly in range(ly0, ly1):
        _set(c, origin, lx, ly, lz, B.VANILLA_CHAIN + "[axis=y]")


def mother_clock(c, origin, lx, ly, lz, facing="west"):
    """Stand-in long-case mother clock: a tall dark-wood case with a glowing dial. A5's precision
    clock with a swinging pendulum replaces it."""
    for dy in range(0, 4):
        _set(c, origin, lx, ly + dy, lz, B.DARK_WOOD.block)
    _set(c, origin, lx, ly + 3, lz, B.WINDOW_FROSTED.block)         # the lit dial
    _set(c, origin, lx, ly + 1, lz, B.BRASS_PLATE.block)
    return (origin[0] + lx, origin[1] + ly + 3, origin[2] + lz + 1, 8)  # dial glow in front, 3rd rank


def switchboard(c, origin, lx, ly, lz, facing="south", width=3):
    """Stand-in marble switchboard: a short run of panel blocks (gauges, knife switches) on a slate
    base. A5's board with real dials and levers replaces it."""
    base = B.SLATE_BRICK.block
    panels = [B.PANELS["gauges"], B.PANELS["knife_switch"], B.PANELS["dial"]]
    for k in range(width):
        _set(c, origin, lx, ly, lz + k, base)
        _set(c, origin, lx, ly + 1, lz + k, panels[k % len(panels)] + f"[facing={facing}]")
        _set(c, origin, lx, ly + 2, lz + k, panels[(k + 1) % len(panels)] + f"[facing={facing}]")


def wall_chart(c, origin, lx, ly, lz, facing="south"):
    """Stand-in framed star chart: brass frame about an enamel-blue field. Replaced by c179's
    paper_star_chart model."""
    frame = B.BRASS_PLATE.block
    field = "blue_glazed_terracotta" + f"[facing={facing}]"        # enamel blue (B.PANELS['nameplate'])
    for dy in (0, 1, 2):
        for dz in (0, 1):
            _set(c, origin, lx, ly + dy, lz + dz, field)
    for dy in (-1, 3):
        for dz in (-1, 0, 1, 2):
            _set(c, origin, lx, ly + dy, lz + dz, frame)
    for dy in (0, 1, 2):
        for dz in (-1, 2):
            _set(c, origin, lx, ly + dy, lz + dz, frame)


def bench(c, origin, lx, ly, lz, length=3, axis="z"):
    """Stand-in waiting bench: a dark-wood slab on low supports. Replaced by c179's furn_bench."""
    for k in range(length):
        dx, dz = (0, k) if axis == "z" else (k, 0)
        _set(c, origin, lx + dx, ly, lz + dz, VB.slab(B.DARK_WOOD.block, "bottom"))


def pendant(c, origin, lx, ly, lz, ceiling_ly, level=9):
    """A caged iron pendant lamp hung on a chain from the ceiling. An occupancy-table fixture, so it
    is real, not a stand-in; c179's enamel pendant can replace it for close shots."""
    chain_up(c, origin, lx, ly + 1, lz, ceiling_ly)
    _set(c, origin, lx, ly, lz, B.IRON_LANTERN + "[hanging=true]")
    return (origin[0] + lx, origin[1] + ly - 1, origin[2] + lz, level)


def wall_lamp(c, origin, lx, ly, lz, level=7):
    """A caged iron bulb on the wall; walkway / third-rank light."""
    _set(c, origin, lx, ly, lz, B.IRON_BULB + "[lit=true]")
    return (origin[0] + lx, origin[1] + ly, origin[2] + lz, level)
