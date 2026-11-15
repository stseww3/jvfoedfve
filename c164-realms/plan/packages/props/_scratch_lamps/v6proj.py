"""Where the lip's low lamps and the pipe bridge's head fall in the picture of S.V6 (1280x720, fov 77)."""
import math, sys
sys.path.insert(0, "/tmp/c164_lamps/trial/c164-realms/build")
from scenes.obs.common import skeleton as S
from scenes.obs.site import court, powerhouse as P

W, H, FOV = 1280, 720, 77.0
pos, at = S.V6["pos"], S.V6["look_at"]
f = [at[i] - pos[i] for i in range(3)]
n = math.sqrt(sum(v * v for v in f)); f = [v / n for v in f]
r = [-f[2], 0.0, f[0]]                      # right = f x up(0,1,0)  -> (f_y*0 - f_z*1, ..., ) check sign below
n = math.hypot(r[0], r[2]); r = [v / n for v in r]
u = [r[1] * f[2] - r[2] * f[1], r[2] * f[0] - r[0] * f[2], r[0] * f[1] - r[1] * f[0]]
t = math.tan(math.radians(FOV) / 2)

def px(p):
    d = [p[i] - pos[i] for i in range(3)]
    z = sum(d[i] * f[i] for i in range(3))
    x = sum(d[i] * r[i] for i in range(3)) / (z * t * W / H)
    y = sum(d[i] * u[i] for i in range(3)) / (z * t)
    return round((x + 1) / 2 * W), round((1 - y) / 2 * H), round(z, 1)

print("V6", pos, at)
print("lip piers", court.lip_piers())
print("lip lamps", court.lip_lamps())
print("PIPE_Z", P.PIPE_Z, "HEAD_X", P.HEAD_X, "PIPE_Y", P.PIPE_Y, "POSTS_X", P.POSTS_X, "X0", P.X0)
for z in court.lip_piers():
    if z > 0:
        print("pier z", z, "lamp foot", px((60.5, 1.5, z + 0.5)), "globe top", px((60.5, 2.75, z + 0.5)))
print("elbow box", px((58, 2, 33)), px((59, 3, 34)), "elbow middle", px((58.5, 2.5, 33.5)))
print("down pipe foot", px((58.5, 0.0, 33.5)), "cable box top", px((58.5, 4.0, 33.5)))
print("main at x 60, 62, 65, 67:", [px((x, 2.5, 33.5)) for x in (60, 62, 65, 67)])
print("portal posts foot/top:", [(px((x + 0.5, -6, 33.5)), px((x + 0.5, 2, 33.5))) for x in P.POSTS_X])
print("house NW corner top", px((67, 4, 20)), "door lamp", px(P.LAMP_AT["pos"]))
print()
from scenes.obs.props import lamps
for g, kind, p, level, aim in lamps.site_lamps():
    a, b = px(p), px((p[0], p[1] + (4.6 if kind == "street" else 1.2), p[2]))
    inside = 0 <= b[0] < W and 0 <= b[1] < H and a[2] > 0
    if a[2] > 0 and -200 < b[0] < W + 200:
        print(f"{g:8}{kind:8}{p}  foot {a}  top {b}  {'IN' if inside else 'out'}")
print("chimney foot box", px((P.TX0, -6, P.TZ0)), px((P.TX1 + 1, 6, P.TZ0)), "shaft top", px((P.TX0 + 3, 23, P.TZ0 + 3)))
print("house north front", px((P.X0, -6, P.Z0)), px((P.X1 + 1, 4, P.Z0)))
