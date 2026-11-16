"""Where a point of a board picture lies in the world: the ray of a pixel of a 1280x720 board
picture (field of view 77 degrees), cut with a plane (x=, y=, z=) or the dome room's wall
(r= about the dome's axis).

    python unproject.py v10 y=7 300,650 560,600 ...
"""
import math
import sys

CAMS = {
    "v07": ((17.5, 1.62, 0.5), (9.0, 6.0, 0.5)),
    "v08": ((12.7, 19.62, -0.7), (0.0, 25.2, 0.9)),
    "v09": ((12.5, 8.62, 8.5), (4.0, 8.0, 21.0)),
    "v10": ((12.5, 8.62, -7.5), (4.0, 8.0, -20.0)),
}
F = 360.0 / math.tan(math.radians(77.0) / 2.0)
AXIS = (4.5, 0.5)


def basis(pos, at):
    f = [a - p for a, p in zip(at, pos)]
    n = math.sqrt(sum(c * c for c in f))
    f = [c / n for c in f]
    r = [-f[2], 0.0, f[0]]
    n = math.hypot(r[0], r[2])
    r = [c / n for c in r]
    u = [r[1] * f[2] - r[2] * f[1], r[2] * f[0] - r[0] * f[2], r[0] * f[1] - r[1] * f[0]]
    return f, r, u


def ray(cam, px, py):
    pos, at = CAMS[cam]
    f, r, u = basis(pos, at)
    a, b = (px - 640.0) / F, (360.0 - py) / F
    return pos, [f[i] + a * r[i] + b * u[i] for i in range(3)]


def hit(cam, px, py, kind, value):
    pos, d = ray(cam, px, py)
    if kind in "xyz":
        i = "xyz".index(kind)
        if abs(d[i]) < 1e-9:
            return None
        t = (value - pos[i]) / d[i]
    else:
        ox, oz = pos[0] - AXIS[0], pos[2] - AXIS[1]
        a = d[0] * d[0] + d[2] * d[2]
        b = 2 * (ox * d[0] + oz * d[2])
        c = ox * ox + oz * oz - value * value
        disc = b * b - 4 * a * c
        if disc < 0:
            return None
        t = (-b + math.sqrt(disc)) / (2 * a)
    if t <= 0:
        return None
    return tuple(pos[i] + t * d[i] for i in range(3))


def project(cam, p):
    pos, at = CAMS[cam]
    f, r, u = basis(pos, at)
    v = [p[i] - pos[i] for i in range(3)]
    depth = sum(v[i] * f[i] for i in range(3))
    if depth <= 0:
        return None
    return (640.0 + F * sum(v[i] * r[i] for i in range(3)) / depth,
            360.0 - F * sum(v[i] * u[i] for i in range(3)) / depth)


if __name__ == "__main__":
    cam = sys.argv[1]
    if sys.argv[2] == "p":
        for arg in sys.argv[3:]:
            p = tuple(float(c) for c in arg.split(","))
            q = project(cam, p)
            print(arg, "->", None if q is None else "(%.0f, %.0f)" % q)
    else:
        kind, value = sys.argv[2].split("=")
        for arg in sys.argv[3:]:
            px, py = (float(c) for c in arg.split(","))
            p = hit(cam, px, py, kind, float(value))
            print(arg, "->", None if p is None else "(%.1f, %.1f, %.1f)" % p)
