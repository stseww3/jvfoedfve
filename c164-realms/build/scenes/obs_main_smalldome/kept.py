"""Nobody leaves the roofs: where a visitor gets to from the dome room's door, on the blocks of this
scene from the cornice's row up, worked out with the walk-through's tool (tools/walkreach.py: a
person 0.6 wide and 1.8 high who walks up 0.6, jumps 1.2 and drops any height).

The end terraces' flags are level with the parapet's coping. Until 11-16 a visitor walked out onto
it and dropped to the cornice, from where the only way on is down to the court (the walk-out of
11-16, plan/reviews/walk/1a0f1af/out-findings.md). main/roof.py lays a guard of barriers over the
parapets (roof.guard()). Told here: every place reached whose middle stands on a column of the wall
line or beyond it, up to the guard's top. Once with the guard's barriers taken out, where the
parapets and the cornice have to show (a proof that finds nothing either way proves nothing), and
once on the scene as built, where there must be none.

The tool goes from one lattice point to the next, so it knows no running jump over a gap. What
such a jump reaches is reckoned in the card (plan/packages/main/smalldome.md): the guard's top is
out of reach from every step of the gables.

    python -m scenes.obs_main_smalldome.kept      # from c164-realms/build; exit code 1 if anyone gets out
"""
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.normpath(os.path.join(HERE, "..", "..", "..", "tools")))

import walkreach as W  # noqa: E402
from scenes import obs_main_smalldome as scene  # noqa: E402
from scenes.obs.common import skeleton as S  # noqa: E402
from scenes.obs.main import facade, roof  # noqa: E402

FLOOR = S.CORNICE                       # 15: the blocks from this row up are read
TOP = roof.GUARD_Y[1] + 1.0             # 21: the guard's top; what stands higher is not the roofs' to keep
SHOWN = 6                               # places named in a line


def start():
    """A point on the plate before the dome room's south door, feet on the terrace."""
    x, z = roof.thresholds()[0]
    return (x + 0.5, float(roof.STAND), z + 0.5)


def _columns(v):
    """The columns a middle at v stands on along one axis: two on a joint between cells."""
    near = int(round(v))
    return (near - 1, near) if abs(v - near) < W.EPS else (int(math.floor(v)),)


def beyond(reach, inside):
    """The places reached, up to the guard's top, whose middle stands on no column inside the
    parapets: [(x, feet, z, kind)], sorted."""
    out = []
    for node, kind in reach.kind.items():
        x, feet, z = W.point(node)
        if feet <= TOP + W.EPS and not any((cx, cz) in inside for cx in _columns(x) for cz in _columns(z)):
            out.append((x, feet, z, kind))
    return sorted(out)


def _told(places):
    kinds = {}
    for _, _, _, kind in places:
        kinds[kind] = kinds.get(kind, 0) + 1
    feet = sorted({p[1] for p in places})
    words = ", ".join(f"{kinds[k]} {k}" for k in W.KINDS if k in kinds)
    first = ", ".join(f"({x:g}, {y:g}, {z:g}) {kind}" for x, y, z, kind in places[:SHOWN])
    return (f"{len(places)} on the parapets or beyond ({words}), feet {feet[0]:g} .. {feet[-1]:g}, "
            f"x {min(p[0] for p in places):g} .. {max(p[0] for p in places):g}, "
            f"z {min(p[2] for p in places):g} .. {max(p[2] for p in places):g}; first: {first}")


def run():
    canvas = scene.build()
    cells = {cell: state for cell, state in canvas.b.items() if cell[1] >= FLOOR}
    plan = facade.shell()
    inside = plan.leaf | plan.core
    guard = set(roof.guard())
    bare = {cell: state for cell, state in cells.items() if not (cell in guard and state == roof.GUARD)}
    tally = roof.guard_tally(canvas)
    print(f"the guard over the parapets, rows {roof.GUARD_Y[0]} and {roof.GUARD_Y[1]}, in the scene: "
          + ", ".join(f"{n} {kind}" for kind, n in sorted(tally.items())))
    print(f"    rows {roof.GUARD_LAMP_Y[0]} and {roof.GUARD_LAMP_Y[1]} in the two columns beside the corner terraces' "
          "lamps; the cell between them holds "
          + ", ".join(f"{(canvas.get(*cell) or 'air').partition('[')[0]} at {cell}" for cell in roof.guard_lamp_cells()))
    at = start()
    print(f"from {at}, the scene's blocks from y {FLOOR} up:")
    open_reach = W.reach_of(bare, at)
    was = beyond(open_reach, inside)
    print(f"    without the barriers: {len(open_reach.kind)} places reached, "
          + (_told(was) if was else "none on the parapets or beyond"))
    reach = W.reach_of(cells, at)
    out = beyond(reach, inside)
    print(f"    as built: {len(reach.kind)} places reached, "
          + (_told(out) if out else "none on the parapets or beyond"))
    guess = sorted(reach.world.census["guess"])
    if guess:
        print(f"    blocks taken for whole cubes, their shape not being written down in the tool: {', '.join(guess)}")
    if out:
        print(f"{len(out)} places on the parapets or beyond are reached: the guard is open")
        return 1
    if not was:
        print("nothing is reached beyond the parapets with the barriers taken out either: this proves nothing")
        return 2
    print("nobody leaves the roofs: on foot, by a jump or by a drop no place on the parapets or beyond is reached")
    return 0


if __name__ == "__main__":
    sys.exit(run())
