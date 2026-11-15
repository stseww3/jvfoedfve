import sys
sys.path.insert(0, "/tmp/c164_a1/proto")
from proj import project, W, H
from scenes import obs_mat_board as M

KEY = {
    "ground_left": [(0, 8, 0), (28, 8, 0), (-1, 0, 13), (29, 0, 13), (8, 0, 12), (28, 0, 12), (-1, 0, 0)],
    "ground_right": [(31, 0, 1), (31, 0, 16), (46, 0, 16), (37, 0, 19), (40, 0, 19), (30, 0, 21), (47, 0, 21), (50, 0, 11), (78, 0, 11), (78, 0, 0), (58, 5, 0), (70, 5, 0), (79, 0, 13)],
    "ground_rock": [(0, 8, 0), (18, 8, 0), (0, 0, 3), (18, 0, 7), (10, 5, 3)],
    "ground_snow": [(20, 8, 0), (28, 8, 0), (20, 0, 9), (28, 0, 9), (20, 0, 12), (28, 0, 12), (16, 0, 12), (20, 0, 13), (28, 0, 13)],
    "ground_inlay": [(31, 0, 1), (46, 0, 1), (31, 0, 16), (46, 0, 16), (38, 0, 19), (30, 0, 21), (47, 0, 21), (38, 2, 0)],
    "ground_inlay_walk": [(38, 0, 19), (38, 0, 1), (33, 0, 8), (44, 0, 8), (38, 2, 0)],
    "ground_cloud": [(50, 0, 11), (78, 0, 11), (58, 5, 0), (70, 5, 0), (50, 0, 0), (78, 0, 0), (49, 0, 13), (79, 0, 13)],
}
shots = {s["name"]: s for s in M.shots()}
for name, pts in KEY.items():
    s = shots[name]
    got = project(s["pos"], s["look_at"], pts)
    bad = [(p, q) for p, q in zip(pts, got) if not (q and 0 <= q[0] <= W and 0 <= q[1] <= H)]
    xs = [q[0] for q in got if q]; ys = [q[1] for q in got if q]
    print(f"{name:18s} pos {s['pos']} look {s['look_at']}  x {min(xs)}..{max(xs)}  y {min(ys)}..{max(ys)}  out: {bad}")
