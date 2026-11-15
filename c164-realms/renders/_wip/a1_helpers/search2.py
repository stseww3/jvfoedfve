import sys, itertools
sys.path.insert(0, "/tmp/c164_a1/proto")
from proj import project, W, H
from search import best, fr
jobs = {
    "ground_left": (14.0, [(0, 8, 0), (28, 8, 0), (-1, 0, 13), (29, 0, 13), (8, 0, 12), (28, 0, 12), (-1, 0, 0)], fr(6, 24), fr(14, 30), fr(0, 5), fr(0, 10)),
    "ground_snow": (24.0, [(20, 8, 0), (28, 8, 0), (20, 0, 9), (28, 0, 9), (20, 0, 12), (28, 0, 12), (20, 0, 13), (28, 0, 13)], fr(6, 20), fr(12, 24), fr(0, 5), fr(0, 10)),
    "ground_snow_wide": (22.0, [(20, 8, 0), (28, 8, 0), (20, 0, 9), (28, 0, 9), (16, 0, 12), (28, 0, 12), (16, 0, 13), (28, 0, 13)], fr(6, 20), fr(12, 24), fr(0, 5), fr(0, 10)),
}
for name in (sys.argv[1:] or jobs):
    cx, pts, hs, zs, lys, lzs = jobs[name]
    print(name)
    for area, pos, look, box in best(cx, pts, hs, zs, lys, lzs, top=6):
        print("   area %7d  pos %s look %s  box x %d..%d y %d..%d" % (area, pos, look, *box))
