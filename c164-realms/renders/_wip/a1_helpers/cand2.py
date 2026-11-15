import sys, math
sys.path.insert(0, "/tmp/c164_a1/proto")
from proj import project, W, H
K = {"seat back-left": (31, 0, 1), "seat back-right": (46, 0, 1), "seat front-left": (31, 0, 16), "seat front-right": (46, 0, 16),
     "run end": (38.5, 0, 19), "tongue front-left": (30, 0, 21), "tongue front-right": (47, 0, 21), "marker top": (38.5, 1.5, 0), "marker foot": (38.5, 0, 1),
     "ring left": (33, 0, 8.5), "ring right": (44, 0, 8.5), "drift": (28, 0, 5), "bank": (50, 0, 5)}
for pos, look in [((38.5, 13.5, 13.5), (38.5, 0, 10)), ((38.5, 13.5, 14), (38.5, 0, 10)), ((38.5, 14, 13.5), (38.5, 0, 10)), ((38.5, 13.5, 13.5), (38.5, 0, 9.5)), ((38.5, 14, 14), (38.5, 0, 10.5))]:
    got = project(pos, look, list(K.values()))
    pitch = math.degrees(math.atan2(pos[1] - look[1], math.hypot(pos[0] - look[0], pos[2] - look[2])))
    print(pos, look, "pitch %.0f" % pitch)
    print("   ", {k: q for k, q in zip(K, got)})
