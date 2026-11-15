"""A half-tier shot (four walls of 8, two apart; the last with low walls at its foot): what its edges show.
usage: halves.py shift,back ...   (camera at y + 5 looking at y + 4)"""
import sys
sys.path.insert(0, "/tmp/c164_a1/proto")
from proj import project, W, H

def px(pos, look, pts):
    return [q[0] for q in project(pos, look, pts)]

for arg in sys.argv[1:]:
    s, back = (float(v) for v in arg.split(","))
    m, y, z = 0.0, 0.0, 0.0
    pos, look = (m + s, y + 5.0, z + back), (m + s, y + 4.0, z)
    P = lambda x, yy, d: (x, yy, z + d)
    left_wall = px(pos, look, [P(m - 19, 0, 1), P(m - 19, 8, 1)])
    right_wall = px(pos, look, [P(m + 19, 0, 1), P(m + 19, 8, 1)])
    low = px(pos, look, [P(m + 18.75, 0, 2.75), P(m + 18.75, 1, 2.75), P(m + 18.75, 0, 2.25)])
    stairs = px(pos, look, [P(m - 18, 0, 2), P(m - 18, 1, 2)])
    nb_r = px(pos, look, [P(m + 21, 0, 1), P(m + 21, 8, 1), P(m + 21, 0, 0), P(m + 21, 8, 0)])
    nb_l = px(pos, look, [P(m - 21, 0, 1), P(m - 21, 8, 1), P(m - 21, 0, 0), P(m - 21, 8, 0)])
    end_r = px(pos, look, [P(m + 20, -1, 0), P(m + 20, 8, 0)])      # the board's end, when the half is the right one
    print(f"shift {s} back {back}: left wall's edge at {min(left_wall)}, its stair {min(stairs)}; right wall's edge {max(right_wall)}, "
          f"low wall to {max(low)} ({'CUT' if max(low) > W else 'whole, %d to spare' % (W - max(low))}); "
          f"right neighbour: face from {min(nb_r[:2])}, side from {min(nb_r[2:])} ({max(0, W - min(nb_r[2:]))} px shown); "
          f"left neighbour: side to {max(nb_l[2:])} ({max(0, max(nb_l[2:]))} px shown), face to {max(nb_l[:2])}; board's end (right) at {min(end_r)}")
