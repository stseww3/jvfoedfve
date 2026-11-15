"""Test scene of the work package machines/mast: the radio mast, both ways, side by side.

Version a (all display models) stands on the real pad at the skeleton foot; version b (iron-block
legs plus models) stands 30 blocks east of it, each on its own placeholder pad with a placeholder
clock-tower stub so the antenna has something to meet. The two are framed alike -- full height, the
lattice close, from below, the tower join -- so the pictures can be compared blind, near and at 70
blocks, with a skyline angle like V1 and a bird's eye like V12. The pad, the guy-anchor piers and
the tower are c229's and c223's; here they are only stand-ins so the mast reads in context.

The shots are written from the numbers below:  python -m scenes.obs_mach_radiomast
"""
import math

from artkit.canvas import Canvas

from scenes.obs import materials, sky
from scenes.obs.common import blocks as B
from scenes.obs.common import skeleton as S
from scenes.obs.machines import mast

BIOME = "obs_blue"
BIOME_MARGIN = 80
BIOME_MARGIN_Y = 96
TIME = 14000                    # light version A, the default (INTERFACE: 18000 is B, 12900 is C)

GAP = 30                        # version b stands this far east of version a
PAVING = B.SLATE_SMOOTH.block
ANCHOR = B.SLATE_BRICK.block
TOWER = (B.SLATE_BRICK.block, B.ASHLAR_ROUGH.block)     # banded, so no stub face reads flat 5x5
BRACKET = B.IRON_BARS
MAST_CX, MAST_CZ = int(math.floor(mast.CX)), int(math.floor(mast.CZ))


def _context(c, ox):
    """The stand-ins one mast stands in: the stone pad, small anchor piers under the guys, and a
    banded clock-tower stub with an iron bracket on its north-east face at y 38."""
    x0, z0, x1, z1 = S.MAST_PAD["box"]
    c.box(ox + x0, -1, z0, ox + x1, -1, z1, PAVING)
    for ax, _ay, az in mast.GUY_ANCHORS:
        c.set(ox + int(math.floor(ax)), 0, int(math.floor(az)), ANCHOR)
    tx0, tx1 = S.CLOCK_SHAFT_X
    tz0, tz1 = S.CLOCK_SHAFT_Z
    for y in range(30, 42):
        c.box(ox + tx0, y, tz0, ox + tx1, y, tz1, TOWER[y % 2])
    c.set(ox + tx1, 38, tz0, BRACKET)


def build():
    c = Canvas()
    n = 0
    for v, ox in (("a", 0), ("b", GAP)):
        _context(c, ox)
        n += mast.build(c, (ox, 0, 0), version=v)
    sky.build(c, (0, 0, 0))             # A2's light sources go in last, when the mast is in place
    c.entity_counts = {"machines": n}
    return c


def write_pack(pack_dir):
    """The repainted iron and stone the mast is judged against."""
    return materials.pack(pack_dir)


def shots():
    """The cameras: each version full height near and at 70 blocks, its lattice close, from below
    and at the tower join -- framed alike for a blind read -- plus both together, a V1-like skyline
    and a V12-like bird's eye."""
    out = []

    def shot(name, pos, look_at):
        out.append({"name": name, "pos": [round(v, 2) for v in pos],
                    "look_at": [round(v, 2) for v in look_at], "time": TIME})

    cz = mast.CZ
    for v, ox in (("a", 0), ("b", GAP)):
        mx = mast.CX + ox
        tx = S.CLOCK_SHAFT_X[1] + ox + 0.8
        tz = S.CLOCK_SHAFT_Z[0] - 0.3
        shot(f"full_{v}", (mx + 24, 32, cz + 32), (mx, 31, cz))                 # whole mast, ~45 blocks
        shot(f"far70_{v}", (mx + 36, 34, cz + 60), (mx, 31, cz))                # whole mast at ~70 blocks
        shot(f"lattice_{v}", (mx + 4.5, 22, cz + 4.5), (mx, 22, cz))            # the lattice close, mid-height
        shot(f"below_{v}", (mx + 0.6, 1.6, cz + 0.6), (mx, 55, cz))             # from the foot, looking up
        shot(f"tower_{v}", (tx + 7, 42, tz + 8), (tx, 38, tz))                  # the antenna meeting the tower
    midx = mast.CX + GAP / 2.0
    shot("both", (midx, 34, cz + 66), (midx, 31, cz))                          # a and b in one frame
    shot("skyline", (mast.CX + 58, 8, cz + 40), (mast.CX, 34, cz))             # a V1-like three-quarter
    shot("aerial", (mast.CX + 44, 92, cz + 44), (mast.CX, 28, cz))            # a V12-like bird's eye
    return out
