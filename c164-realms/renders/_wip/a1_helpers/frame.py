"""Scratch: where the corners of things fall in a shot (pinhole, fov 77 vertical, 16:9). Not a render."""
import math, sys
sys.path.insert(0, ".")
import numpy as np
import scenes.obs_mat_board as S

TY = math.tan(math.radians(77.0) / 2.0)
TX = TY * 16.0 / 9.0

def project(pos, look, p):
    pos, look, p = (np.array(v, float) for v in (pos, look, p))
    f = look - pos; f /= np.linalg.norm(f)
    r = np.cross(f, [0, 1, 0]); r /= np.linalg.norm(r)
    u = np.cross(r, f)
    v = p - pos
    d = v @ f
    return (v @ r) / (d * TX), (v @ u) / (d * TY), d

def report(pos, look, pts):
    for name, p in pts:
        sx, sy, d = project(pos, look, p)
        flag = "" if abs(sx) <= 1 and abs(sy) <= 1 and d > 0 else "   <-- OUT"
        print(f"   {name:28s} x {sx:+.2f}  y {sy:+.2f}  depth {d:5.1f}{flag}")

w = S.width(); top = S.at(len(S.TIERS) - 1)[0] + S.N
board = [("ground floor front left", (-1, 0, S.FRONT + 1)), ("ground floor front right", (w + 1, 0, S.FRONT + 1)),
         ("ground wall foot left", (-1, 0, 0)), ("ground wall top left", (0, 8, 0)),
         ("glass wall top left", (0, top, S.at(len(S.TIERS) - 1)[1])), ("glass wall top right", (w, top, S.at(len(S.TIERS) - 1)[1])),
         ("glass wall foot left", (0, top - 8, S.at(len(S.TIERS) - 1)[1])),
         ("glass riser top", (w / 2, top + 1, S.at(len(S.TIERS) - 1)[1] - 1))]
args = sys.argv[1:]
if args and args[0] == "all":
    cy, cz, ly, lz = (float(a) for a in args[1:5])
    pos, look = (w / 2.0, cy, cz), (w / 2.0, ly, lz)
    print("all from", pos, "to", look)
    report(pos, look, board)
    # how large is a wall of the glass tier, in pixels of 1280
    a = project(pos, look, (0, top, S.at(len(S.TIERS) - 1)[1]))
    b = project(pos, look, (8, top, S.at(len(S.TIERS) - 1)[1]))
    print("   a glass wall is", round((b[0] - a[0]) * 640), "px wide")
else:
    for s in S.shots():
        print(s["name"], s["pos"], "->", s["look_at"])
