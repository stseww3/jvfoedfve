"""Which pieces of the small things' row a close shot holds whole, cuts, or leaves out.
usage: pieces.py c,D [c,D ...]   (camera at x = c, D in front of the row's cells; hung signs as two posts)"""
import sys, itertools
sys.path.insert(0, "/tmp/c164_a1/proto")
from proj import project, W, H

Y, Z = 10, -12
B = 42
def _pipe(n, x): return (n, [(x + .3, x + .7, 0, 3, 0.3, 0.7), (x + 1, x + 2, 2.3, 2.7, 0.3, 0.7), (x + 1.3, x + 1.7, 1.3, 1.7, 0, 1)])
PIECES = [   # name, boxes (x0, x1, y0, y1, depth0, depth1) with depth 0 = the back of the row's cells
    ("door", [(2, 4, 0, 2, 0.8, 1)]),
    ("hatch", [(6, 8, 0, 1, 0, 1), (6, 7, 1, 1.2, 0, 1), (7, 8, 1, 2, 0, 0.2)]),
    ("rod", [(10.37, 10.63, 0, 2, 0.37, 0.63), (11, 12, 0, 1, 0, 1), (11.37, 11.63, 1, 2, 0.37, 0.63),
             (11.37, 11.63, 0.37, 0.63, 1, 2)]),
    _pipe("pipe", 14), _pipe("v.chain", 17),
    ("bars", [(23, 25, 0, 3, 0.4, 0.6)]),
    ("v.bars", [(26, 28, 0, 3, 0.4, 0.6)]),
    ("bulb", [(30, 32, 0, 2, 0, 1)]),
    ("lantern", [(34, 35, 0, 1, 0, 1), (34.3, 34.7, 1, 1.6, 0.3, 0.7), (35, 36, 2, 3, 0, 1), (35.3, 35.7, 1.2, 2, 0.3, 0.7)]),
    ("plate", [(B, B + 2, 0, 4, 0, 1), (B, B + 1, 0, 1, 1, 2), (B + 1, B + 2, 0, 0.5, 1, 2)]),
    ("pattern", [(B + 2, B + 4, 0, 4, 0, 1), (B + 2, B + 3, 0, 1, 1, 2), (B + 3, B + 4, 0, 0.5, 1, 2)]),
    ("column", [(B + 5, B + 6, 0, 3, 0, 1), (B + 6, B + 7, 2, 3, 0, 1), (B + 6, B + 7, 0, 1, 0, 1)]),
    ("rail", [(B + 8, B + 10, 0, 1, 0.4, 0.6)]),
    ("gate", [(B + 10, B + 11, 0, 1, 0.4, 0.6)]),
    ("b.door", [(B + 12, B + 14, 0, 2, 0.8, 1)]),
    ("b.hatch", [(B + 15, B + 17, 0, 1, 0, 1), (B + 15, B + 16, 1, 1.2, 0, 1), (B + 16, B + 17, 1, 2, 0, 0.2)]),
    ("things", [(B + 18, B + 25, 0, 3, 0, 1.2)]),
    ("standing", [(B + 26.05, B + 27.95, 0, 1.9, 0.4, 0.6)]),
    ("hanging", [(B + 28, B + 30, 2, 3, 0, 1), (B + 28.05, B + 29.95, 1, 2, 0.4, 0.6)]),
    ("hung brass", [(B + 31.05, B + 31.95, 1, 2, 0.4, 0.6)]),
    ("post 1", [(B + 32, B + 33, 0, 3, 0, 1)]),
    ("hung enamel", [(B + 34.05, B + 34.95, 1, 2, 0.4, 0.6)]),
    ("post 2", [(B + 35, B + 36, 0, 3, 0, 1)]),
]

def span(pos, look, boxes):
    """(lowest x, highest x, lowest y, highest y) of the boxes' corners in the picture."""
    pts = [(x, Y + y, Z + d) for x0, x1, y0, y1, d0, d1 in boxes
           for x, y, d in itertools.product((x0, x1), (y0, y1), (d0, d1))]
    got = project(pos, look, pts)
    return min(q[0] for q in got), max(q[0] for q in got), min(q[1] for q in got), max(q[1] for q in got)

for arg in (sys.argv[1:] if __name__ == '__main__' else []):
    c, D = (float(v) for v in arg.split(","))
    pos, look = (c, Y + 2.6, Z + D), (c, Y + 1.5, Z)
    whole, cut = [], []
    for name, boxes in PIECES:
        x0, x1, y0, y1 = span(pos, look, boxes)
        if x1 <= 0 or x0 >= W:
            continue
        if x0 >= 0 and x1 <= W and y0 >= 0 and y1 <= H:
            whole.append(f"{name} {x0}..{x1}")
        else:
            cut.append(f"{name} {max(x0, 0)}..{min(x1, W)} (shows {min(x1, W) - max(x0, 0)} of {x1 - x0} px)")
    ends = project(pos, look, [(0, Y + 2, Z), (79, Y + 2, Z)])
    print(f"c {c} D {D}: whole: {'; '.join(whole)}\n    cut: {'; '.join(cut) or 'nothing'}\n    the wall's ends at x {ends[0][0]}, {ends[1][0]}")
