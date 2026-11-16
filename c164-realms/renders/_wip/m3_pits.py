"""The engine hall's two places without a floor at the level (x 79..83, z 23..25 and z 27..29), for
c323: what stands there, where feet land, whether a visitor gets in from the aisle and out again.
Run in c164-realms/:  python renders/_wip/m3_pits.py  -> renders/_wip/walkfix/pits.txt"""
import os
import sys
from collections import deque

sys.path.insert(0, "tools")
sys.path.insert(0, "build")
import walkreach as W  # noqa: E402

LEVEL = -6.0
START = (78.5, LEVEL, 31.5)                 # the middle of the engine hall, the route's own station
BOUNDS = (60, 8, 100, 52)
PITS = (("north", (79, 23, 83, 25)), ("south", (79, 27, 83, 29)))
out = []


def say(text=""):
    out.append(text)


def short(state):
    if state is None:
        return "-"
    name = str(state).split("[")[0].replace("minecraft:", "")
    extra = ""
    text = str(state)
    for key in ("type=", "half=", "open=", "waterlogged=true"):
        if key in text:
            at = text.index(key)
            extra += "/" + text[at:].split(",")[0].split("]")[0].replace("=", ":")
    return name + extra


def pt(node):
    x, y, z = W.point(node)
    return f"({x:g}, {y:g}, {z:g})"


def main():
    cells = W.cells_of("obs")
    reach = W.reach_of(cells, START, BOUNDS)
    world = reach.world
    say(f"ways from {START} within {BOUNDS}: {len(reach.kind)} places" + ("; CUT SHORT" if reach.cut else ""))
    back = {}
    for node, edges in reach.out.items():
        for nxt, kind, rise in edges or ():
            back.setdefault(nxt, []).append((node, kind, rise))
    for name, (x0, z0, x1, z1) in PITS:
        say()
        say(f"==== the {name} place: x {x0}..{x1}, z {z0}..{z1}")
        say("-- the blocks, one line a level (y), rows z north to south, columns x west to east, a cell wider all round; - is air")
        for y in range(-4, -12, -1):
            names = {}
            rows = []
            for z in range(z0 - 1, z1 + 2):
                row = []
                for x in range(x0 - 1, x1 + 2):
                    s = short(cells.get((x, y, z)))
                    if s in ("-", "air", "cave_air"):
                        row.append("-")
                    else:
                        names.setdefault(s, chr(ord("A") + len(names)) if len(names) < 26 else "?")
                        row.append(names[s])
                rows.append("".join(row))
            if all(set(r) == {"-"} for r in rows):
                say(f"y {y}: all air")
                continue
            say(f"y {y}: " + "  ".join(f"z{z0 - 1 + n}:{r}" for n, r in enumerate(rows)))
            say("      " + ", ".join(f"{v}={k}" for k, v in names.items()))
        say("-- where feet stand at the middle of every cell (every height with a person's room over it, between y -13 and -3), and how that place is reached")
        inside = set()
        for z in range(z0, z1 + 1):
            row = []
            for x in range(x0, x1 + 1):
                i, j = world.lattice(x + 0.5, z + 0.5)
                tops = [(top, room) for top, room in world.stand(i, j) if -13.0 <= top <= -3.0]
                parts = []
                for top, room in tops:
                    node = (i, j, int(round(top * W.Q)))
                    parts.append(f"{top:g}{'/' + reach.kind[node] if node in reach.kind else '/not reached'}")
                row.append(f"x{x}: " + (" ".join(parts) or "nowhere"))
            say(f"z {z}: " + "; ".join(row))
        for node in reach.kind:
            x, y, z = W.point(node)
            if x0 - 0.01 <= x <= x1 + 1.01 and z0 - 0.01 <= z <= z1 + 1.01 and y < LEVEL - 0.3:
                inside.add(node)
        kinds = {}
        for n in inside:
            kinds[reach.kind[n]] = kinds.get(reach.kind[n], 0) + 1
        heights = sorted({W.point(n)[1] for n in inside})
        say(f"-- places reached under the hall's level inside the rectangle (the lattice of half blocks): {len(inside)}; feet at {heights}; "
            + (", ".join(f"{k} {v}" for k, v in sorted(kinds.items())) or "none"))
        say("-- the steps that lead in (from a place at the hall's level or over it to one under it):")
        entries = {}
        for n in inside:
            for prev, kind, rise in back.get(n, ()):
                if prev not in inside and W.point(prev)[1] >= LEVEL - 0.3:
                    entries.setdefault((kind, round(rise, 2), reach.kind[prev], W.point(prev)[1]), []).append((prev, n))
        for (kind, rise, pk, py), pairs in sorted(entries.items()):
            a, b = pairs[0]
            say(f"   {kind} {rise:+.2f} from a place reached by '{pk}' with feet {py:g}: {len(pairs)} steps, e.g. {pt(a)} -> {pt(b)}")
        if not entries:
            say("   none")
        rim = set()
        for pairs in entries.values():
            for prev, _ in pairs:
                rim.add(prev)
        rk = {}
        for n in rim:
            rk[reach.kind[n]] = rk.get(reach.kind[n], 0) + 1
        say(f"   the {len(rim)} places they start from are reached by: " + (", ".join(f"{k} {v}" for k, v in sorted(rk.items())) or "-"))
        if rim:
            first = min(rim, key=lambda n: reach.steps.get(n, 1e9))
            seen, todo = {reach.start: None}, deque([reach.start])
            while todo:
                node = todo.popleft()
                if node == first:
                    break
                for nxt, kind, rise in reach.out.get(node) or ():
                    if nxt not in seen:
                        seen[nxt] = (node, kind, rise)
                        todo.append(nxt)
            path, node = [], first
            while seen.get(node) is not None:
                prev, kind, rise = seen[node]
                path.append((prev, node, kind, rise))
                node = prev
            special = [f"{k} {r:+.2f} {pt(a)}->{pt(b)}" for a, b, k, r in path[::-1] if k != "walk"]
            say(f"   the nearest of them to the hall's middle, {pt(first)}, is reached by: " + ("; ".join(special) or "walking alone"))
        say("-- and out again: from every place inside, the easiest way back to a walked place at the hall's level")
        outs = {}
        for n in sorted(inside):
            best = None
            for name2, allow in (("walking", lambda k, r: k == "walk"),
                                 ("a jump of a block or less", lambda k, r: k == "walk" or (k == "jump" and r <= 1.0 + 1e-6) or k == "drop"),
                                 ("a jump of up to 1.2", lambda k, r: True)):
                seen, todo = {n}, deque([n])
                found = False
                while todo and not found:
                    node = todo.popleft()
                    for nxt, kind, rise in reach.out.get(node) or ():
                        if nxt in seen or not allow(kind, rise):
                            continue
                        if nxt not in inside and reach.kind.get(nxt) == "walk" and abs(W.point(nxt)[1] - LEVEL) < 0.3:
                            found = True
                            break
                        seen.add(nxt)
                        todo.append(nxt)
                if found:
                    best = name2
                    break
            outs.setdefault(best or "NO WAY OUT", []).append(n)
        for how, nodes in outs.items():
            say(f"   {how}: {len(nodes)} places, e.g. " + " ".join(pt(n) for n in nodes[:4]))
        jumps = [(a, b, r) for a, b, r in reach.jumps if a in inside]
        say(f"   jumps that start inside: {len(jumps)}" + (", e.g. " + "; ".join(f"{pt(a)}->{pt(b)} {r:+.2f}" for a, b, r in jumps[:6]) if jumps else ""))
    os.makedirs("renders/_wip/walkfix", exist_ok=True)
    with open("renders/_wip/walkfix/pits.txt", "w", encoding="utf-8") as fh:
        fh.write("\n".join(out) + "\n")
    print("\n".join(out))


main()
