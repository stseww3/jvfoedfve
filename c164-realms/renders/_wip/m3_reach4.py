"""Fourth pass for machines/cablecar-winch (c338's own fix, tried in memory): the bars beside the
track mouth, (91, -4, -35) and (91, -4, -31), become a wall with a bottom slab on it (1.5 high);
the cove's bars (91, -29 .. -27) stay. Is the way over the car and down the trestle shut, and where
does a visitor end who climbs out of the cove: all the way down to the cloud line, or on a ledge.
Run in c164-realms/:  python renders/_wip/m3_reach4.py  -> renders/_wip/reach/m3_fix.txt"""
import importlib
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
out = []


def say(text=""):
    out.append(text)


def pt(node):
    x, y, z = W.point(node)
    return f"({x:g}, {y:g}, {z:g})"


def flood(reach, sources, allow=lambda node: True):
    seen = {n: None for n in sources}
    todo = deque(sources)
    while todo:
        node = todo.popleft()
        for nxt, kind, rise in reach.out.get(node) or ():
            if nxt not in seen and allow(nxt):
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


def main():
    cells = W.cells_of(SCENE)
    wall, slab = cells.get((91, -4, -26)), cells.get((91, -3, -26))
    fixed = dict(cells)
    for z in (-35, -31):
        say(f"(91, -4, {z}) was {cells.get((91, -4, z))}: now {wall} with {slab} on y -3 (the collision of a wall and a bottom slab; "
            "the stone's own name does not matter to who walks)")
        fixed[(91, -4, z)], fixed[(91, -3, z)] = wall, slab
    try:
        line = float(importlib.import_module("scenes.obs.site.terrain").CLOUD_TOP + 1)
    except Exception as err:  # noqa: BLE001
        line = None
        say(f"no cloud line ({type(err).__name__}: {err})")
    say(f"the cloud line (feet at or under it: sent home): {line}")
    say()
    reach = W.reach_of(fixed, START)
    west = flood(reach, [reach.start], lambda n: W.point(n)[0] < OFF - 1e-9)      # never east of the edge

    top = [n for n in reach.kind if 89.5 <= W.point(n)[0] <= 92.0 and -34.5 <= W.point(n)[2] <= -30.5 and W.point(n)[1] >= -2.5]
    say(f"1. on top of the car's barriers or the two new piers (feet -2.5 or higher, x 89.5 .. 92, z -34.5 .. -30.5): "
        f"{len(top)} points reached from the start by any way at all" + (": " + " ".join(pt(n) for n in sorted(top)[:8]) if top else ""))
    mouth = [n for n in reach.kind if 92.0 <= W.point(n)[0] <= 96.0 and -34.0 <= W.point(n)[2] <= -31.0 and W.point(n)[1] >= -4.6]
    kinds = {}
    for n in mouth:
        kinds[reach.kind[n]] = kinds.get(reach.kind[n], 0) + 1
    say(f"   the level track east of the mouth (x 92 .. 96, z -34 .. -31, feet -4): {len(mouth)} points reached"
        + (", by " + ", ".join(f"{k} {v}" for k, v in sorted(kinds.items())) if mouth else ""))
    if mouth:
        first = min(mouth, key=lambda n: reach.steps[n])
        every = flood(reach, [reach.start])
        special = [f"{k} {r:+.2f} {pt(a)}->{pt(b)}" for a, b, k, r in trail(every, first) if k != "walk"]
        say(f"   the nearest of them, {pt(first)}, is reached by: " + ("; ".join(special[:14]) or "walking alone") + (" ..." if len(special) > 14 else ""))
    say()

    say(f"2. steps off the east edge (rows z {ROWS[0]:g} .. {ROWS[1]:g}) by a visitor who has stayed west of x {OFF:g}:")
    exits = []
    for node in west:
        az = W.point(node)[2]
        if not (ROWS[0] <= az <= ROWS[1]):
            continue
        for nxt, kind, rise in reach.out.get(node) or ():
            if W.point(nxt)[0] >= OFF - 1e-9:
                exits.append((az, node, nxt, kind, rise))
    for az, node, nxt, kind, rise in sorted(exits):
        special = [f"{k} {r:+.2f} {pt(a)}->{pt(b)}" for a, b, k, r in trail(west, node) if k != "walk"]
        say(f"   z {az:g}: {pt(node)} -> {pt(nxt)} {kind} {rise:+.2f}; by " + ("; ".join(special) or "walking alone"))
    if not exits:
        say("   none")
    say()

    landing = sorted({nxt for _, _, nxt, _, _ in exits})
    say(f"3. where he is then: the {len(landing)} landing points " + " ".join(pt(n) for n in landing[:10]))
    on = flood(reach, landing)
    kinds, low = {}, None
    for n in on:
        kinds[reach.kind[n]] = kinds.get(reach.kind[n], 0) + 1
        y = W.point(n)[1]
        low = y if low is None or y < low else low
    void = [n for n in on if n in reach.void]
    say(f"   from them he gets to {len(on)} points, feet down to {low}; kinds as reached from the spawn: "
        + ", ".join(f"{k} {v}" for k, v in sorted(kinds.items())) + f"; {len(void)} points with a step off the scene")
    if line is not None:
        under = [n for n in on if W.point(n)[1] <= line + 1e-9]
        say(f"   points at or under the cloud line {line:g}: {len(under)}" + (", the nearest way down: " if under else ""))
        if under:
            best = min(under, key=lambda n: len(trail(on, n)))
            path = trail(on, best)
            special = [f"{k} {r:+.2f} {pt(a)}->{pt(b)}" for a, b, k, r in path if k != "walk"]
            say(f"      to {pt(best)} in {len(path)} lattice steps: " + ("; ".join(special[:16]) or "walking alone") + (" ..." if len(special) > 16 else ""))
        stuck = reach.stuck(line)
        mine = sorted(n for n in on if n in stuck)
        say(f"   stuck places among them (trapped, no way down to the line nor off the scene): {len(mine)}"
            + (": " + " ".join(pt(n) for n in mine[:20]) + (" ..." if len(mine) > 20 else "") if mine else ""))
    back = {}
    for node, edges in reach.out.items():
        for nxt, kind, rise in edges or ():
            back.setdefault(nxt, []).append(node)
    home, todo = {reach.start}, deque([reach.start])
    while todo:
        node = todo.popleft()
        for prev in back.get(node, ()):
            if prev not in home:
                home.add(prev)
                todo.append(prev)
    lost = [n for n in on if n not in home]
    say(f"   of the {len(on)} points, {len(on) - len(lost)} have a way back to the spawn point (any jumps of up to 1.2), {len(lost)} have none")
    for n in landing[:10]:
        say(f"   landing {pt(n)}: " + ("a way back to the spawn exists" if n in home else "NO way back to the spawn"))
    os.makedirs("renders/_wip/reach", exist_ok=True)
    with open("renders/_wip/reach/m3_fix.txt", "w", encoding="utf-8") as fh:
        fh.write("\n".join(out) + "\n")
    print("\n".join(out))


main()
