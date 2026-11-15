"""Is a box of the scene inside the frame of any of its shots? Run in build/ with PYTHONPATH=.

    python inframe.py <scene> x0 y0 z0 x1 y1 z1 [more boxes ...]

For every shot the corners and the edges' points of each box are projected (1280x720, vertical
field of view 77); a box counts as in the frame when any point of it is before the camera and
inside the picture. Nothing is said about what hides it."""
import importlib
import itertools
import math
import sys

W, H, FOV = 1280, 720, 77.0


def camera(pos, at):
    f = [at[i] - pos[i] for i in range(3)]
    n = math.sqrt(sum(v * v for v in f))
    f = [v / n for v in f]
    r = [-f[2], 0.0, f[0]]
    n = math.hypot(r[0], r[2]) or 1.0
    r = [v / n for v in r]
    u = [r[1] * f[2] - r[2] * f[1], r[2] * f[0] - r[0] * f[2], r[0] * f[1] - r[1] * f[0]]
    t = math.tan(math.radians(FOV) / 2)

    def px(p):
        d = [p[i] - pos[i] for i in range(3)]
        z = sum(d[i] * f[i] for i in range(3))
        if z <= 0.05:
            return None
        x = sum(d[i] * r[i] for i in range(3)) / (z * t * W / H)
        y = sum(d[i] * u[i] for i in range(3)) / (z * t)
        return (x + 1) / 2 * W, (1 - y) / 2 * H, z
    return px


def points(box, step=1.0):
    x0, y0, z0, x1, y1, z1 = box
    xs = [x0 + i * step for i in range(int((x1 - x0) / step) + 1)] + [x1]
    ys = [y0 + i * step for i in range(int((y1 - y0) / step) + 1)] + [y1]
    zs = [z0 + i * step for i in range(int((z1 - z0) / step) + 1)] + [z1]
    for x, y, z in itertools.product(xs, ys, zs):
        if x in (x0, x1) or y in (y0, y1) or z in (z0, z1):
            yield x, y, z


CLEAR = ("light", "glass", "bars", "_pane", "chain", "rod")


def hidden(canvas, a, b, inside):
    """Does a block of the canvas stand between a and b? Blocks one sees through do not count, nor
    do those inside the box looked for."""
    d = [b[i] - a[i] for i in range(3)]
    n = max(2, int(math.sqrt(sum(v * v for v in d)) / 0.2))
    for k in range(1, n):
        p = [a[i] + d[i] * k / n for i in range(3)]
        if all(inside[i] - 0.01 <= p[i] <= inside[i + 3] + 0.01 for i in range(3)):
            continue
        cell = (math.floor(p[0]), math.floor(p[1]), math.floor(p[2]))
        state = canvas.b.get(cell)
        if state is not None and not any(w in state for w in CLEAR):
            return True
    return False


def main():
    scene = sys.argv[1]
    nums = [float(v) for v in sys.argv[2:]]
    boxes = [nums[i:i + 6] for i in range(0, len(nums), 6)]
    mod = importlib.import_module("scenes." + scene)
    canvas = mod.build()
    for shot in mod.shots():
        px = camera(shot["pos"], shot["look_at"])
        for k, box in enumerate(boxes):
            hits = [(p, q) for p, q in ((px(q), q) for q in points(box)) if p and 0 <= p[0] < W and 0 <= p[1] < H]
            seen = [(p, q) for p, q in hits if not hidden(canvas, shot["pos"], q, box)]
            if hits:
                xs, ys = [p[0] for p, _ in hits], [p[1] for p, _ in hits]
                line = (f"{shot['name']:20} box {k}: in the frame, x {min(xs):.0f}..{max(xs):.0f}, "
                        f"y {min(ys):.0f}..{max(ys):.0f}, {min(p[2] for p, _ in hits):.0f} to "
                        f"{max(p[2] for p, _ in hits):.0f} blocks off; ")
                if seen:
                    xs, ys = [p[0] for p, _ in seen], [p[1] for p, _ in seen]
                    line += f"SEEN: {len(seen)} of {len(hits)} points, x {min(xs):.0f}..{max(xs):.0f}, y {min(ys):.0f}..{max(ys):.0f}"
                else:
                    line += "all of it hidden"
                print(line)
    print("done:", len(mod.shots()), "shots,", len(boxes), "boxes")


if __name__ == "__main__":
    main()
