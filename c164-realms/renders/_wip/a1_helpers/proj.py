"""project(shot, points): where points of the world fall in a 1280x720 picture taken as build/render.py takes it
(vertical angle of view FOV, looking from pos to look_at, up = +y)."""
import math
FOV, W, H = 77.0, 1280, 720

def project(pos, look_at, pts):
    fx, fy, fz = (look_at[i] - pos[i] for i in range(3))
    n = math.sqrt(fx * fx + fy * fy + fz * fz); fx, fy, fz = fx / n, fy / n, fz / n
    # right = forward x up(0,1,0)
    rx, ry, rz = -fz, 0.0, fx
    n = math.hypot(rx, rz); rx, rz = rx / n, rz / n
    ux, uy, uz = ry * fz - rz * fy, rz * fx - rx * fz, rx * fy - ry * fx
    t = math.tan(math.radians(FOV) / 2.0)
    out = []
    for p in pts:
        d = [p[i] - pos[i] for i in range(3)]
        f = d[0] * fx + d[1] * fy + d[2] * fz
        r = d[0] * rx + d[1] * ry + d[2] * rz
        u = d[0] * ux + d[1] * uy + d[2] * uz
        if f <= 0.01:
            out.append(None); continue
        out.append((round(W / 2 + r / (f * t) * (H / 2)), round(H / 2 - u / (f * t) * (H / 2))))
    return out

if __name__ == "__main__":
    import sys
    pos, look, pts = eval(sys.argv[1]), eval(sys.argv[2]), eval(sys.argv[3])
    for p, q in zip(pts, project(pos, look, pts)):
        print(p, "->", q, "" if q and 0 <= q[0] <= W and 0 <= q[1] <= H else "  OUT")
