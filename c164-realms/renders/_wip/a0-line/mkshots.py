import json, math, sys
sys.path.insert(0, "build")
from scenes.obs.site import _rail as R
from scenes.obs.common import skeleton as S

def P(s):
    q = R.at(s)
    return float(q.x), float(q.y), float(q.z)

print("at(0)", P(0), "at(4.5)", P(4.5), "at(24)", P(24), "at(123.75)", P(123.75), "at(179)", P(179))
EYE = 2.0          # a seated passenger's eye over the rails (car floor ~0.6, seat, head)
shots = []
def ride(name, s, ahead=18.0, toward=None, mix=0.0, up=0.0):
    x, y, z = P(s)
    ax, ay, az = P(max(s - ahead, 0.0))
    lx, ly, lz = ax, ay + EYE + up, az
    if toward is not None:
        lx = lx * (1 - mix) + toward[0] * mix
        ly = ly * (1 - mix) + toward[1] * mix
        lz = lz * (1 - mix) + toward[2] * mix
    shots.append(dict(name=name, pos=[round(x, 2), round(y + EYE, 2), round(z, 2)],
                      look_at=[round(lx, 2), round(ly, 2), round(lz, 2)], time=14000))
OBS = (20.0, 16.0, 0.0)
ride("ride_s150_out_of_cloud", 150.0, ahead=30.0, up=2.0)
ride("ride_s124_curve_begins", 124.0, ahead=25.0, toward=OBS, mix=0.35)
ride("ride_s095_broadside", 95.0, ahead=20.0, toward=OBS, mix=0.6)
ride("ride_s060_turning_in", 60.0, ahead=20.0, toward=OBS, mix=0.5)
ride("ride_s030_foot", 30.0, ahead=20.0, toward=(8.0, 30.0, 0.5), mix=0.5)
ride("ride_s010_brow", 10.0, ahead=8.0, toward=(8.0, 34.0, 0.5), mix=0.6)
# outside views
shots.append(dict(name="viaduct_from_southeast", pos=[222.0, -6.0, 96.0], look_at=[135.0, -12.0, 5.0], time=14000))
shots.append(dict(name="viaduct_from_stair", pos=[62.0, 2.0, 20.0], look_at=[150.0, -16.0, 20.0], time=14000))
shots.append(dict(name="station_engine", pos=[89.5, -2.3, -29.0], look_at=[97.5, -4.2, -32.5], time=14000))
shots.append(dict(name="line_from_platform", pos=[93.0, -1.8, -36.5], look_at=[150.0, -18.0, -5.0], time=14000))
shots.append(dict(name="v01_arrival", pos=list(S.V1["pos"]), look_at=list(S.V1["look_at"]), time=14000))
json.dump(shots, open("/tmp/c164_a0/ride/shots.json", "w"), indent=1)
for s in shots: print(s)
