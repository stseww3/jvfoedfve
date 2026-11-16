#!/usr/bin/env python3
"""Scratch of comet (c330), not for delivery: a look at every lamp sky/lights hangs along the ways,
at the gates and on the ring stair of the master scene (lights' request #79567).

    python _comet_probe/lampcheck.py facts <out folder>
        builds the master scene and writes <out>/lamps.txt (per lamp: where it hangs, what holds
        it, whether somebody walks through its cell, what else is anchored beside it, from which
        of the board's views it is seen) and <out>/shots.json (one close view per lamp, for
        build/render.py)
    python _comet_probe/lampcheck.py sheets <prefix of the pictures> <out folder> [per sheet]
        puts the close views <prefix>-<name>.png on sheets <out>/sheet_<n>.jpg

Run from c164-realms/ with tools/darkfloor.py of cursor/c164-sound-lightaudit-f3-cbc6 in /tmp.
"""
import json
import math
import os
import re
import sys

VIEWS = ("V4", "V7", "V8", "V11")
FOV = 77.0
SIZE = (1280, 720)
KINDS = (("way", "ways"), ("gate", "gates"), ("stair", "stair"))


def facts(out):
    sys.path[:0] = ["/tmp", os.path.join(os.getcwd(), "tools")]
    import darkfloor as D
    from scenes.obs.sky import lights

    S = D.S
    os.makedirs(out, exist_ok=True)
    canvas = D.obs.build()
    cells = canvas.b
    r = lights.report(canvas)
    placed = r["placed"]
    names, stops = {}, {}

    def name(cell):
        state = cells.get(cell)
        if state is None:
            return ""
        if state not in names:
            names[state] = D.AB.name_of(state)
        return names[state]

    def shut(cell):
        state = cells.get(cell)
        if state is None:
            return False
        if state not in stops:
            stops[state] = D.L._stops_light(state)
        return stops[state]

    def free(cell):
        return cells.get(cell) is None or name(cell) == D.B.LIGHT

    def seen(a, b, skip=()):
        """Does nothing that shuts light stand between two points? Cells of `skip` do not count."""
        d = [b[i] - a[i] for i in range(3)]
        n = max(1, int(math.sqrt(sum(c * c for c in d)) / 0.2))
        for k in range(1, n):
            p = tuple(int(math.floor(a[i] + d[i] * k / n)) for i in range(3))
            if p not in skip and shut(p):
                return False
        return True

    # where a person stands, as tools/darkfloor.py finds it
    m = S.mass_bounds()
    world = D.W.World(cells, (m[0] - 40, m[2] - 40, m[3] + 40, m[5] + 40))
    points, _order = D.route_points(os.getcwd())
    starts = [("spawn", D.W.landmarks()["spawn"])] + [(f"{label} #{n}", at) for n, (label, at) in enumerate(points)]
    found, _fell, _used, _lost = D.standing(world, starts)
    feet = {(i // 2, int(math.floor(hq / float(D.W.Q) + 1e-6)), j // 2) for (i, j, hq) in found if i % 2 and j % 2}
    heads = {(x, y + 1, z) for x, y, z in feet}

    entities = [(float(e[0]), float(e[1]), float(e[2]), e[3]) for e in canvas.entities]

    def model(data):
        found_names = re.findall(r"c164art:[a-z0-9_/]+", json.dumps(data, default=str))
        return found_names[0] if found_names else "?"

    asked = {}
    for (wx, wy, wz), facing, level, what in lights.way_lamps():
        dx, dz = lights.FACE[facing]
        asked[(wx + dx, wy, wz + dz)] = ((wx, wy, wz), facing, level, what)

    lamps = []
    for kind, key in KINDS:
        for cell in r.get(key, ()):
            cell = tuple(cell)
            level, why = placed.get(cell, (None, "?"))
            centre = (cell[0] + 0.5, cell[1] + 0.5, cell[2] + 0.5)
            near = sorted((math.dist(centre, e[:3]), e) for e in entities if math.dist(centre, e[:3]) <= 1.01)
            lamps.append(dict(kind=kind, cell=cell, level=level, why=why, near=near, asked=asked.get(cell)))
    hung = {lamp["cell"] for lamp in lamps}
    missing = [(cell, v) for cell, v in sorted(asked.items()) if cell not in hung]

    cameras = {}
    for v in VIEWS:
        cam = getattr(S, v, None)
        if isinstance(cam, dict) and "pos" in cam:
            cameras[v] = (tuple(float(c) for c in cam["pos"]), tuple(float(c) for c in cam["look_at"]))

    def in_view(cam, p):
        pos, at = cam
        f = [at[i] - pos[i] for i in range(3)]
        n = math.sqrt(sum(c * c for c in f))
        f = [c / n for c in f]
        right = [-f[2], 0.0, f[0]]
        n = math.sqrt(sum(c * c for c in right)) or 1.0
        right = [c / n for c in right]
        up = [right[1] * f[2] - right[2] * f[1], right[2] * f[0] - right[0] * f[2], right[0] * f[1] - right[1] * f[0]]
        v = [p[i] - pos[i] for i in range(3)]
        depth = sum(v[i] * f[i] for i in range(3))
        if depth <= 0.1:
            return None
        t = math.tan(math.radians(FOV / 2.0))
        x = sum(v[i] * right[i] for i in range(3)) / depth / (t * SIZE[0] / SIZE[1])
        y = sum(v[i] * up[i] for i in range(3)) / depth / t
        if abs(x) > 1.0 or abs(y) > 1.0:
            return None
        return int(round((x + 1.0) / 2.0 * SIZE[0])), int(round((1.0 - y) / 2.0 * SIZE[1])), math.sqrt(sum(c * c for c in v))

    lines, shots = [], []
    lines.append(f"{len(lamps)} lamps of sky/lights hang in the master scene: "
                 + ", ".join(f"{sum(1 for l in lamps if l['kind'] == k)} {k}" for k, _ in KINDS)
                 + f"; {len(missing)} of way_lamps() do not hang; {len(placed)} sources in all; {len(feet)} standing cells")
    for cell, (wall, facing, level, what) in missing:
        why = "its wall does not stand" if not cells.get(wall) or name(wall) == D.B.LIGHT else f"the cell before the wall holds {name(cell) or 'nothing'}"
        lines.append(f"  NOT HUNG {cell} on {wall} looking {facing}, level {level}: {what} ({why})")
    for n, lamp in enumerate(lamps):
        cell = lamp["cell"]
        tag = f"{lamp['kind']}{n:02d}"
        flags = []
        if lamp["near"]:
            anchor = lamp["near"][0][1][:3]
            mine = model(lamp["near"][0][1][3])
        else:
            anchor, mine = (cell[0] + 0.5, cell[1] + 0.5, cell[2] + 0.5), None
            flags.append("NO MODEL within a block of the source")
        head = f"{tag} source {cell} level {lamp['level']} ({lamp['why']})"
        if lamp["asked"]:
            wall, facing, level, what = lamp["asked"]
            wname = name(wall)
            whole = shut(wall)
            head += f"; on {wall} [{wname}] looking {facing}: {what}"
            if not whole:
                flags.append(f"the wall block {wname} is not a whole cube")
            behind = (wall[0] - lights.FACE[facing][0], wall[1], wall[2] - lights.FACE[facing][1])
            head += f"; behind the wall {name(behind) or 'air'}"
            over, under = (wall[0], wall[1] + 1, wall[2]), (wall[0], wall[1] - 1, wall[2])
            if not cells.get(over):
                flags.append("nothing stands over the wall block (the lamp is at the top of a low wall)")
            if not cells.get(under):
                flags.append("nothing stands under the wall block")
        else:
            below = (cell[0], cell[1] - 1, cell[2])
            head += f"; over [{name(below) or 'air'}]"
        lines.append(head)
        lines.append(f"    model {mine} anchored at ({anchor[0]:.2f}, {anchor[1]:.2f}, {anchor[2]:.2f})")
        if cell in feet:
            flags.append("its cell is one somebody's FEET stand in")
        if cell in heads:
            flags.append("its cell is one somebody's HEAD is in")
        floor = next((k for k in range(1, 6) if (cell[0], cell[1] - k, cell[2]) in feet), None)
        if floor is None:
            ground = next((k for k in range(1, 9) if shut((cell[0], cell[1] - k, cell[2]))), None)
            lines.append(f"    nobody stands under it; the first whole block under it is {ground} down" if ground
                         else "    nobody stands under it; nothing under it within 8")
        else:
            lines.append(f"    somebody stands under it: feet {floor} below its cell")
        around = []
        for dx, dy, dz in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)):
            c = (cell[0] + dx, cell[1] + dy, cell[2] + dz)
            around.append(f"{'+x' if dx > 0 else '-x' if dx < 0 else '+y' if dy > 0 else '-y' if dy < 0 else '+z' if dz > 0 else '-z'}="
                          f"{name(c).replace('minecraft:', '') or '.'}")
        lines.append("    beside its cell: " + " ".join(around))
        others = [(d, e) for d, e in ((math.dist(anchor, e[:3]), e) for e in entities) if 1e-6 < d <= 1.5]
        for d, e in sorted(others)[:6]:
            lines.append(f"    another model {model(e[3])} {d:.2f} away at ({e[0]:.2f}, {e[1]:.2f}, {e[2]:.2f})")
        if len([1 for d, _ in others if d <= 0.75]) > 0:
            flags.append("another model is anchored within 0.75 of it")
        for v, cam in cameras.items():
            at = in_view(cam, anchor)
            if at and seen(cam[0], anchor, skip=(cell,)):
                lines.append(f"    in {v}: at pixel ({at[0]}, {at[1]}) of {SIZE[0]}x{SIZE[1]}, {at[2]:.1f} blocks from the camera")
                flags.append(f"seen in {v}")
        for flag in flags:
            lines.append(f"    !! {flag}")
        # a close view: from a free cell three or four blocks before the lamp
        if lamp["asked"]:
            fx, fz = lights.FACE[lamp["asked"][1]]
            base = math.atan2(fz, fx)
        else:
            base = 0.0
        shot = None
        turns = (0, 25, -25, 50, -50, 70, -70) if lamp["asked"] else tuple(range(0, 360, 30))
        for dist in (3.5, 3.0, 4.0, 2.5, 4.5, 2.0, 1.5):
            for turn in turns:
                for up in (0.5, 1.0, 0.0, 1.5):
                    a = base + math.radians(turn)
                    pos = (anchor[0] + dist * math.cos(a), anchor[1] + up, anchor[2] + dist * math.sin(a))
                    c = tuple(int(math.floor(v)) for v in pos)
                    if free(c) and seen(pos, anchor, skip=(cell,)):
                        shot = pos
                        break
                if shot:
                    break
            if shot:
                break
        if shot:
            shots.append(dict(name=tag, pos=[round(v, 2) for v in shot], look_at=[round(v, 2) for v in anchor], time=14000))
            lines.append(f"    close view from ({shot[0]:.1f}, {shot[1]:.1f}, {shot[2]:.1f})")
        else:
            lines.append("    !! no free place found for a close view")
    for key in ("problems", "notes", "isolated"):
        for item in r.get(key, ()):
            lines.append(f"sky/lights {key}: {item}")
    with open(os.path.join(out, "lamps.txt"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(lines) + "\n")
    with open(os.path.join(out, "shots.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(shots, fh, indent=1)
    flagged = [line for line in lines if "!!" in line]
    print(lines[0])
    print(f"{len(shots)} close views in shots.json; {len(flagged)} flags:")
    count = {}
    for line in flagged:
        key = re.sub(r"[0-9.]+", "#", line.strip())
        count[key] = count.get(key, 0) + 1
    for key, n in sorted(count.items(), key=lambda kv: -kv[1]):
        print(f"  {n:3d} x {key}")


def sheets(prefix, out, per=12):
    from PIL import Image, ImageDraw

    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, "shots.json"), encoding="utf-8") as fh:
        shots = json.load(fh)
    cols = 4
    tw, th = 480, 270
    pictures = []
    for shot in shots:
        path = f"{prefix}-{shot['name']}.png"
        if os.path.exists(path):
            pictures.append((shot["name"], Image.open(path).convert("RGB").resize((tw, th), Image.LANCZOS)))
    while len(pictures) > 4 * per:                  # four sheets at the most
        per += cols
    n = 0
    for start in range(0, len(pictures), per):
        part = pictures[start:start + per]
        rows = (len(part) + cols - 1) // cols
        sheet = Image.new("RGB", (cols * tw, rows * (th + 14)), (16, 16, 16))
        draw = ImageDraw.Draw(sheet)
        for k, (name, im) in enumerate(part):
            x, y = (k % cols) * tw, (k // cols) * (th + 14)
            sheet.paste(im, (x, y + 14))
            draw.text((x + 4, y + 1), name, fill=(255, 255, 255))
        n += 1
        sheet.save(os.path.join(out, f"sheet_{n}.jpg"), quality=88)
    print(f"{len(pictures)} of {len(shots)} close views on {n} sheets")


if __name__ == "__main__":
    if sys.argv[1] == "facts":
        facts(sys.argv[2])
    else:
        sheets(sys.argv[2], sys.argv[3], int(sys.argv[4]) if len(sys.argv) > 4 else 12)
