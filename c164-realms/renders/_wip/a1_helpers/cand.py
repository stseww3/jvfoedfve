import sys, math
sys.path.insert(0, "/tmp/c164_a1/proto")
from proj import project, W, H
def show(name, pos, look, pts):
    got = project(pos, look, pts)
    bad = [(p, q) for p, q in zip(pts, got) if not (q and 0 <= q[0] <= W and 0 <= q[1] <= H)]
    xs = [q[0] for q in got if q]; ys = [q[1] for q in got if q]
    pitch = math.degrees(math.atan2(pos[1] - look[1], math.hypot(pos[0] - look[0], pos[2] - look[2])))
    print(f"{name:12s} pos {pos} look {look} pitch {pitch:4.1f}  x {min(xs)}..{max(xs)}  y {min(ys)}..{max(ys)}  out: {bad}")
    return got
L = [(0, 8, 0), (28, 8, 0), (-1, 0, 13), (29, 0, 13), (8, 0, 12), (28, 0, 12), (-1, 0, 0), (0, 10, 0)]
for pos, look in [((14, 11.5, 20.5), (14, 3.5, 1.0)), ((14, 13, 18), (14, 3.5, 5)), ((14, 13, 17.5), (14, 3, 5)), ((14, 14, 17), (14, 3, 5)),
                  ((14, 12.5, 18.5), (14, 3.0, 4.0)), ((14, 13.5, 17.0), (14, 3.0, 5.5)), ((14, 12.0, 19.0), (14, 3.0, 3.5)), ((14, 13.0, 18.5), (14, 2.5, 4.5))]:
    g = show("left", pos, look, L)
    print("      wall top y", g[0][1], " tier-above edge y", g[7][1], " floor front y", g[2][1], " tones y", g[4][1])
