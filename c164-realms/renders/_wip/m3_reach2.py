"""Second pass of the measurement for machines/cablecar-winch (c338): what stands on the lower
platform's east edge, every jump a visitor makes inside the station, and every step that takes him
off the platform eastward, each with the gentlest way to it from the spawn point.
Run in c164-realms/:  python renders/_wip/m3_reach2.py [<scene>]   -> renders/_wip/reach/m3_exits2.txt"""
import os
import sys
from collections import deque

sys.path.insert(0, "tools")
sys.path.insert(0, "build")
import walkreach as W  # noqa: E402

SCENE = sys.argv[1] if len(sys.argv) > 1 else "obs_mach_cablecar_winch"
START = (88.5, -4.0, -32.5)
ROWS = (-40.0, -26.0)           # the station's rows, as lattice z
OFF = 92.5                      # a middle at or east of this is off the platform (column 92 and on)
out = []


def say(text=""):
    out.append(text)


def pt(node):
    x, y, z = W.point(node)
    return f"({x:g}, {y:g}, {z:g})"


def hop(kind, rise):
    return kind in ("walk", "jump") or (kind == "drop" and -rise <= W.JUMP + W.EPS)


def ways(reach, allow):
    """{node: (previous node, kind, rise)} of the shortest ways from the start along allowed steps."""
    seen = {reach.start: None}
    todo = deque([reach.start])
    while todo:
        node = todo.popleft()
        for nxt, kind, rise in reach.out.get(node) or ():
            if nxt not in seen and allow(kind, rise):
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


def name_of(state):
    text = str(state)
    return text if len(text) < 70 else text[:67] + "..."


def main():
    cells = W.cells_of(SCENE)
    reach = W.reach_of(cells, START)

    say(f"{SCENE}: the blocks on the platform's east edge, y -5 .. -1 (columns x 90 .. 93; air left out)")
    for z in range(-41, -25):
        row = []
        for x in (90, 91, 92, 93):
            col = [f"y{y}:{name_of(cells[(x, y, z)])}" for y in range(-5, 0) if (x, y, z) in cells
                   and "air" not in str(cells[(x, y, z)])]
            if col:
                row.append(f"x{x} [" + " ".join(col) + "]")
        say(f"  z {z}: " + ("  ".join(row) if row else "nothing"))
    say()

    by_walk = ways(reach, lambda kind, rise: kind == "walk")
    by_hop = ways(reach, hop)
    by_any = ways(reach, lambda kind, rise: True)

    def how(node):
        if node in by_walk:
            return "walk", trail(by_walk, node)
        if node in by_hop:
            return "hop", trail(by_hop, node)
        return "fall", trail(by_any, node)

    say("every jump (a rise over 0.6) inside the station, x 75 .. 92.5, z -40 .. -26, with what its foot is reached by:")
    jumps = []
    for a, b, rise in reach.jumps:
        ax, ay, az = W.point(a)
        bx, by, bz = W.point(b)
        if 75.0 <= ax <= 92.5 and ROWS[0] <= az <= ROWS[1] and 75.0 <= bx <= 92.5:
            jumps.append((az, ax, a, b, rise))
    for az, ax, a, b, rise in sorted(jumps):
        say(f"  {pt(a)} -> {pt(b)}  +{rise:.2f}; foot reached by {how(a)[0]}")
    if not jumps:
        say("  none")
    say()

    say(f"every step that takes the middle from x < {OFF:g} to x >= {OFF:g}, rows z {ROWS[0]:g} .. {ROWS[1]:g} "
        "(off the platform's east edge), and the gentlest way to its foot:")
    exits = []
    for node, edges in reach.out.items():
        ax, ay, az = W.point(node)
        if ax >= OFF - 1e-9 or not (ROWS[0] <= az <= ROWS[1]):
            continue
        for nxt, kind, rise in edges or ():
            if W.point(nxt)[0] >= OFF - 1e-9:
                exits.append((az, ay, node, nxt, kind, rise))
    last = None
    for az, ay, node, nxt, kind, rise in sorted(exits):
        label, path = how(node)
        special = [(a, b, k, r) for a, b, k, r in path if k != "walk"]
        text = "; ".join(f"{k} {r:+.2f} {pt(a)}->{pt(b)}" for a, b, k, r in special) or "no jump, no drop"
        say(f"  z {az:6g}: {pt(node)} -> {pt(nxt)}  {kind} {rise:+.2f}; foot reached by {label}, {len(path)} steps: {text}")
        last = node
    if not exits:
        say("  none: nobody steps off the platform eastward in these rows")
    say()

    say("where the ground east of the platform leads (points with x >= 92.5 reached from the start):")
    east = [n for n in reach.kind if W.point(n)[0] >= OFF - 1e-9]
    count = {}
    for n in east:
        count[reach.kind[n]] = count.get(reach.kind[n], 0) + 1
    void = [n for n in east if n in reach.void]
    xs = [W.point(n)[0] for n in east] or [0.0]
    ys = [W.point(n)[1] for n in east] or [0.0]
    say(f"  {len(east)} points, x up to {max(xs):g}, feet {min(ys):g} .. {max(ys):g}; " + ", ".join(f"{k} {v}" for k, v in sorted(count.items()))
        + f"; {len(void)} points have a step off the scene")
    for n in sorted(void, key=lambda n: W.point(n))[:12]:
        say(f"    void beside {pt(n)}")
    track = [n for n in east if -34.5 <= W.point(n)[2] <= -31.0]
    if track:
        far = max(track, key=lambda n: W.point(n)[0])
        say(f"  along the track's rows (z -34.5 .. -31) the furthest point is {pt(far)}, reached by {how(far)[0]}")
    os.makedirs("renders/_wip/reach", exist_ok=True)
    with open("renders/_wip/reach/m3_exits2.txt", "w", encoding="utf-8") as fh:
        fh.write("\n".join(out) + "\n")
    print("\n".join(out))


main()
