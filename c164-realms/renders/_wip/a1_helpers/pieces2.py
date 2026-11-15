"""For each group of the small things' row: the (c, D) from which it is whole and its neighbours out."""
import sys
sys.path.insert(0, "/tmp/c164_a1/proto")
from pieces import PIECES, span, W, H, Y, Z

names = [n for n, _ in PIECES]
GROUPS = {"iron": ("door", "v.chain", 90, 130), "iron_2": ("bars", "lantern", 290, 320), "brass": ("plate", "b.hatch", 485, 505), "signs": ("things", "post 2", 680, 700)}
for g, (a, b, k0, k1) in GROUPS.items():
    i, j = names.index(a), names.index(b)
    for D in (8.0,):
        best = []
        for k in range(k0, k1):
            c = k / 10.0
            pos, look = (c, Y + 2.6, Z + D), (c, Y + 1.5, Z)
            spans = [span(pos, look, boxes) for _, boxes in PIECES]
            if not all(s[0] >= 12 and s[1] <= W - 12 for s in spans[i:j + 1]):
                continue
            seen = sum(max(0, min(s[1], W) - max(s[0], 0)) for n, s in enumerate(spans) if not i <= n <= j)
            left, right = min(s[0] for s in spans[i:j + 1]), W - max(s[1] for s in spans[i:j + 1])
            best.append((seen, abs(left - right), c, left, right))
        best.sort()
        print(g, "D", D, [f"c {c}: others {seen} px, margins {l}/{r}" for seen, _, c, l, r in best[:4]] or "does not fit")
