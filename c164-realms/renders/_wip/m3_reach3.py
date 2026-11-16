"""Third pass for machines/cablecar-winch (c338): what if the five copper bars on the lower
platform's east edge stood two blocks high. The blocks are changed in memory only; nothing of the
scene is touched. Run in c164-realms/:  python renders/_wip/m3_reach3.py  -> renders/_wip/reach/m3_whatif.txt"""
import os
import sys
from collections import deque

sys.path.insert(0, "tools")
sys.path.insert(0, "build")
import walkreach as W  # noqa: E402

SCENE = "obs_mach_cablecar_winch"
START = (88.5, -4.0, -32.5)
ROWS = (-40.0, -26.0)
OFF = 92.5
BARS = [(91, -35), (91, -31), (91, -29), (91, -28), (91, -27)]
out = []


def say(text=""):
    out.append(text)


def pt(node):
    x, y, z = W.point(node)
    return f"({x:g}, {y:g}, {z:g})"


def inside(reach):
    """{node: (previous, kind, rise)}: everything reached from the start without the middle ever
    standing at or east of OFF, by walking, jumping and dropping any height."""
    seen = {reach.start: None}
    todo = deque([reach.start])
    while todo:
        node = todo.popleft()
        for nxt, kind, rise in reach.out.get(node) or ():
            if nxt not in seen and W.point(nxt)[0] < OFF - 1e-9:
                seen[nxt] = (node, kind, rise)
                todo.append(nxt)
    return seen


def trail(seen, node):
    path = []
    while seen.get(node) is not None:
        prev, kind, rise = seen[node]
        path.append((prev, node, kind, rise))
        node = prev
    return path[::-1]


def look(cells, title):
    reach = W.reach_of(cells, START)        # walkreach keeps one world for each dictionary alive: no copies here
    seen = inside(reach)
    say(title)
    exits = []
    for node in seen:
        ax, ay, az = W.point(node)
        if not (ROWS[0] <= az <= ROWS[1]):
            continue
        for nxt, kind, rise in reach.out.get(node) or ():
            if W.point(nxt)[0] >= OFF - 1e-9:
                exits.append((az, node, nxt, kind, rise))
    for az, node, nxt, kind, rise in sorted(exits):
        special = [f"{k} {r:+.2f} {pt(a)}->{pt(b)}" for a, b, k, r in trail(seen, node) if k != "walk"]
        say(f"  off the edge at z {az:g}: {pt(node)} -> {pt(nxt)} {kind} {rise:+.2f}; by " + ("; ".join(special) or "walking alone"))
    if not exits:
        say(f"  no step takes a visitor off the east edge (rows z {ROWS[0]:g} .. {ROWS[1]:g}) who has stayed west of x {OFF:g}")
    top = [n for n in seen if 89.5 <= W.point(n)[0] <= 92.0 and -34.5 <= W.point(n)[2] <= -30.5 and W.point(n)[1] >= -2.5]
    say(f"  on top of the car's barriers (feet -2 or higher, x 89.5 .. 92, z -34.5 .. -30.5): {len(top)} points reached"
        + (", e.g. " + pt(sorted(top)[0]) if top else ""))
    lip = [n for n in seen if W.point(n)[0] == 92.0 and ROWS[0] <= W.point(n)[2] <= ROWS[1]]
    say(f"  on the lip outside the bars (x 92.0): {len(lip)} points reached" + (", e.g. " + pt(sorted(lip)[0]) if lip else ""))
    east_cols = sorted({W.point(n)[2] for n in seen if W.point(n)[0] >= 91.5 and ROWS[0] <= W.point(n)[2] <= ROWS[1]})
    say(f"  rows where a middle gets to x >= 91.5: {east_cols}")
    say()


def main():
    cells = W.cells_of(SCENE)
    look(cells, "as built:")
    raised = dict(cells)
    for x, z in BARS:
        state = cells.get((x, -4, z))
        say(f"  ({x}, -4, {z}) is {state}; the same block is put at y -3" + ("" if (x, -3, z) not in cells else f" (there stood {cells[(x, -3, z)]})"))
        raised[(x, -3, z)] = state
    say()
    look(raised, "with the five bars two blocks high:")
    os.makedirs("renders/_wip/reach", exist_ok=True)
    with open("renders/_wip/reach/m3_whatif.txt", "w", encoding="utf-8") as fh:
        fh.write("\n".join(out) + "\n")
    print("\n".join(out))


main()
