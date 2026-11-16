"""A measurement for machines/cablecar-winch (c338 asked, a4's list): from the spawn point on the
lower platform, on foot and by jumping, where does a visitor get east of the platform's east edge
(x >= 91), and how. Run in c164-realms/:  python renders/_wip/m3_reach.py [<scene>]
Writes renders/_wip/reach/m3_exits.txt and prints the same. Uses tools/walkreach.py as it is."""
import os
import sys
from collections import deque

sys.path.insert(0, "tools")
sys.path.insert(0, "build")
import walkreach as W  # noqa: E402

SCENE = sys.argv[1] if len(sys.argv) > 1 else "obs_mach_cablecar_winch"
START = (88.5, -4.0, -32.5)
EDGE = 91.0                     # the platform's east edge column
Z = (-41.0, -25.0)              # the rows looked at
HOP = ("walk", "hop")

out = []


def say(text=""):
    out.append(text)


def pt(node):
    x, y, z = W.point(node)
    return f"({x:g}, {y:g}, {z:g})"


def allow_walk(kind, rise):
    return kind == "walk"


def allow_hop(kind, rise):
    return kind in ("walk", "jump") or (kind == "drop" and -rise <= W.JUMP + W.EPS)


def allow_any(kind, rise):
    return True


def way(reach, goals, allow):
    """The shortest way from the start to any node of `goals` along the edges `allow` lets through:
    [(from, to, kind, rise)], or None."""
    seen = {reach.start: None}
    todo = deque([reach.start])
    while todo:
        node = todo.popleft()
        if node in goals:
            path = []
            while seen[node] is not None:
                prev, kind, rise = seen[node]
                path.append((prev, node, kind, rise))
                node = prev
            return path[::-1]
        for nxt, kind, rise in reach.out.get(node) or ():
            if nxt not in seen and allow(kind, rise):
                seen[nxt] = (node, kind, rise)
                todo.append(nxt)
    return None


def pieces(reach, nodes):
    """The connected pieces of a set of nodes (a step either way joins two)."""
    nodes = set(nodes)
    near = {n: set() for n in nodes}
    for n in nodes:
        for nxt, kind, rise in reach.out.get(n) or ():
            if nxt in nodes:
                near[n].add(nxt)
                near[nxt].add(n)
    left, found = set(nodes), []
    while left:
        seed = left.pop()
        piece, todo = {seed}, [seed]
        while todo:
            for m in near[todo.pop()]:
                if m in left:
                    left.discard(m)
                    piece.add(m)
                    todo.append(m)
        found.append(piece)
    return sorted(found, key=lambda p: min((W.point(n)[2], W.point(n)[0]) for n in p))


def main():
    cells = W.cells_of(SCENE)
    reach = W.reach_of(cells, START)
    kinds = {}
    for node, kind in reach.kind.items():
        kinds[kind] = kinds.get(kind, 0) + 1
    say(f"{SCENE}: from {START} the start node is {pt(reach.start)}; reached {len(reach.kind)} lattice points: "
        + ", ".join(f"{k} {kinds.get(k, 0)}" for k in W.KINDS))
    say("a lattice point is the middle of a person 0.6 wide; x 91.0 is the joint of columns 90|91, x 91.5 the middle of column 91")
    say()

    # ---- a map of the edge, a character a lattice point -------------------------------------------
    east = [n for n in reach.kind if W.point(n)[0] >= EDGE - 1e-9 and Z[0] <= W.point(n)[2] <= Z[1]]
    xs = [90.0 + 0.5 * i for i in range(0, 21)]
    say("map (rows z, columns x 90.0 .. 100.0 by halves; W walk, h hop, f fall, T trap, . nobody stands; the highest feet when two)")
    say("          " + "".join(f"{x:5g}" if x == int(x) else "     " for x in xs))
    letter = {"walk": "W", "hop": "h", "fall": "f", "trap": "T"}
    by_xz = {}
    for n in reach.kind:
        x, y, z = W.point(n)
        by_xz.setdefault((x, z), []).append((y, reach.kind[n]))
    z = Z[0]
    while z <= Z[1] + 1e-9:
        row = ""
        for x in xs:
            here = sorted(by_xz.get((x, z), []))
            row += ("    " + letter[here[-1][1]]) if here else "    ."
        say(f"z {z:6g}  {row}")
        z += 0.5
    say()
    say("the same, the feet's height (the highest when two)")
    z = Z[0]
    while z <= Z[1] + 1e-9:
        row = ""
        for x in xs:
            here = sorted(by_xz.get((x, z), []))
            row += f"{here[-1][0]:5.1f}" if here else "    ."
        say(f"z {z:6g}  {row}")
        z += 0.5
    say()

    # ---- every step that crosses the edge ---------------------------------------------------------
    say(f"steps that cross x = {EDGE:g} eastward (from a point west of it to a point at or east of it), rows z {Z[0]:g} .. {Z[1]:g}:")
    crossings = []
    for node, edges in reach.out.items():
        ax, ay, az = W.point(node)
        if ax >= EDGE - 1e-9 or not (Z[0] <= az <= Z[1]):
            continue
        for nxt, kind, rise in edges or ():
            bx, by, bz = W.point(nxt)
            if bx >= EDGE - 1e-9:
                crossings.append((az, node, nxt, kind, rise))
    for az, node, nxt, kind, rise in sorted(crossings):
        say(f"  z {az:6g}: {pt(node)} -> {pt(nxt)}  {kind} {rise:+.2f}; the west point is reached by: {reach.kind[node]}")
    if not crossings:
        say("  none")
    say()

    # ---- the pieces east of the edge, and the gentlest way to each ---------------------------------
    say(f"reached ground at or east of x = {EDGE:g} (rows z {Z[0]:g} .. {Z[1]:g}), in connected pieces:")
    for k, piece in enumerate(pieces(reach, east), 1):
        px = [W.point(n) for n in piece]
        count = {}
        for n in piece:
            count[reach.kind[n]] = count.get(reach.kind[n], 0) + 1
        void = sum(1 for n in piece if n in reach.void)
        say(f"piece {k}: {len(piece)} points, x {min(p[0] for p in px):g} .. {max(p[0] for p in px):g}, "
            f"z {min(p[2] for p in px):g} .. {max(p[2] for p in px):g}, feet {min(p[1] for p in px):g} .. {max(p[1] for p in px):g}; "
            + ", ".join(f"{k2} {v}" for k2, v in sorted(count.items()))
            + (f"; {void} of them have a step off the scene (void)" if void else ""))
        cols = sorted({(int(p[0] // 1), int(p[2] // 1)) for p in px if p[0] != int(p[0]) and p[2] != int(p[2])})
        say(f"   block columns whose middle is reached (x, z): {cols[:60]}{' ...' if len(cols) > 60 else ''}")
        for label, allow in (("on foot alone", allow_walk), ("with jumps and drops of up to 1.2", allow_hop),
                             ("only with a deeper drop", allow_any)):
            path = way(reach, piece, allow)
            if path is None:
                continue
            notable = [(a, b, kind, rise) for a, b, kind, rise in path if kind != "walk"]
            last = path[-1] if path else None
            say(f"   the gentlest way there: {label}, {len(path)} lattice steps"
                + (f"; it enters at {pt(last[0])} -> {pt(last[1])} ({last[2]} {last[3]:+.2f})" if last else ""))
            for a, b, kind, rise in notable:
                say(f"      {kind} {rise:+.2f}: {pt(a)} -> {pt(b)}")
            thin = [path[i][0] for i in range(0, len(path), 4)] + ([path[-1][1]] if path else [])
            say("      by way of " + " ".join(pt(n) for n in thin[:40]) + (" ..." if len(thin) > 40 else ""))
            break
    if not east:
        say("  none: nobody gets east of the edge")
    say()

    # ---- the cells c338 named ---------------------------------------------------------------------
    say("the cells asked about (the middle of each column; feet nearest the platform's -4):")
    named = ([("ridge", 92, z) for z in (-37, -36, -35)] + [("track mouth", 91, z) for z in (-34, -33, -32)]
             + [("railing", 91, -35), ("railing", 91, -31)]
             + [("east edge", 91, z) for z in range(-40, -25) if z not in (-35, -34, -33, -32, -31)])
    for what, x, z in named:
        got = []
        for (lx, lz), here in by_xz.items():
            if x <= lx <= x + 1 and z <= lz <= z + 1:
                got += [(lx, y, lz, kind) for y, kind in here]
        mid = [g for g in got if g[0] == x + 0.5 and g[2] == z + 0.5]
        say(f"  {what} ({x}, {z}): " + ("; ".join(f"middle reached, feet {y:g}, {kind}" for _, y, _, kind in sorted(mid)) if mid
                                         else "the middle is not reached")
            + (f"; {len(got) - len(mid)} points on its joints are" if len(got) > len(mid) else ""))
    os.makedirs("renders/_wip/reach", exist_ok=True)
    with open("renders/_wip/reach/m3_exits.txt", "w", encoding="utf-8") as fh:
        fh.write("\n".join(out) + "\n")
    print("\n".join(out))


main()
