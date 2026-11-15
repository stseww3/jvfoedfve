"""A pair shot (two walls of 8, two apart, the right one with low walls at its foot): what its edges show.
usage: pairs.py shift,back ..."""
import sys
sys.path.insert(0, "/tmp/c164_a1/proto")
from proj import project, W, H

def px(pos, look, pts):
    return [q[0] for q in project(pos, look, pts)]

for arg in sys.argv[1:]:
    s, back = (float(v) for v in arg.split(","))
    m, y, z = 0.0, 0.0, 0.0                       # the middle between the two walls; depth d is z = -d
    pos, look = (m + s, y + 4.5, z + back), (m + s, y + 4.0, z)
    P = lambda x, yy, d: (x, yy, z + d)           # depth 0 = the walls' back; the camera is at depth `back`
    left_wall = px(pos, look, [P(m - 9, 0, 1), P(m - 9, 8, 1)])
    right_wall = px(pos, look, [P(m + 9, 0, 1), P(m + 9, 8, 1)])
    low = px(pos, look, [P(m + 8.75, 0, 2.75), P(m + 8.75, 1, 2.75), P(m + 8.75, 0, 2.25)])
    stairs = px(pos, look, [P(m - 8, 0, 2), P(m - 8, 1, 2)])      # the left wall's first stair, its near corner
    nb_r = px(pos, look, [P(m + 11, 0, 1), P(m + 11, 8, 1), P(m + 11, 0, 0), P(m + 11, 8, 0)])
    nb_l = px(pos, look, [P(m - 11, 0, 1), P(m - 11, 8, 1), P(m - 11, 0, 0), P(m - 11, 8, 0)])
    print(f"shift {s} back {back}: left wall's edge at {min(left_wall)}, its stair {min(stairs)}; right wall's edge {max(right_wall)}, "
          f"low wall to {max(low)} ({'CUT' if max(low) > W else 'whole, %d to spare' % (W - max(low))}); "
          f"right neighbour: face from {min(nb_r[:2])}, side from {min(nb_r[2:])} ({max(0, W - min(nb_r[2:]))} px shown); "
          f"left neighbour: side to {max(nb_l[2:])} ({max(0, max(nb_l[2:]))} px shown), face to {max(nb_l[:2])}")
