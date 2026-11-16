#!/usr/bin/env python3
"""Writes out-route.json, the outdoor walk's route (plan/packages/common/walk.md, card walk-out), as
tools/walk.py reads it. The way is the card's: the spawn on the station platform, the lower
platform, the grand stair, round the front court, the meridian hut, the mast pad, the weather
station, the water tower, the west side and the sunset terrace, the south lookout, the terrace's
east lip, round the power house and under the pipe bridge, back to the station.

    python plan/reviews/walk/out-route.py          (from c164-realms/; then tools/walk.py check)

The numbers are the skeleton's and the site packages' own (site/terrain: the gaps in the rail;
site/stair, site/lowerplatform, site/outbuildings, site/mastbase as built in the assembly at round
5959264, read off that round's reach plan; site/cablecar as it stands on its branch), so the way
lies where a visitor is meant to walk whether a package has landed or not: a station that finds
no floor says the package is not there yet, or that the floor moved.

Three kinds of point:
    pt(...)                a point of the way; with node="..." a junction, a doorway, a corner: six views
    edge(..., out=(dx, dz)) a point at a rail or a brink: the view ahead looks out over it, level,
                           and a second one 45 degrees down (views "fd"); the stations walk.py puts
                           between two points look along the way
    hop=True               the way does not run here from the point before
A stretch's stations are numbered in their order, so a point added at the end of a stretch leaves
the names before it alone; a point put in the middle renames what follows in that stretch.
"""
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.normpath(os.path.join(HERE, "..", "..", "..", "build")))

from scenes.obs.common import skeleton as S  # noqa: E402

EYE = S.EYE
UP, LOW, STATION = S.GROUND, S.LOWER_GROUND, S.STATION_GROUND       # feet at 0, -6, -4
N, E, SO, W = (0, -1), (1, 0), (0, 1), (-1, 0)                      # ways to look out
FAR = 24.0                                                          # how far off an edge's view aims

TX0, TZ0, TX1, TZ1 = S.UPPER_TERRACE                                # -10, -38, 60, 38: the rail's cells
IN_W, IN_N, IN_E, IN_S = TX0 + 1.5, TZ0 + 1.5, TX1 - 1.5, TZ1 - 1.5  # a cell in from the rail: -8.5, -36.5, 58.5, 36.5
AXIS = S.AXIS_Z                                                     # 0.5
MX = S.MERIDIAN_X + 0.5                                             # 35.5
FOOT_X = S.FRONT_COURT[0] + 4.5                                     # 20.5: the strip along the foot of the front
LX0, LZ0, LX1, LZ1 = S.LOWER_PLATFORM                               # 61, -42, 91, 43
CX0, CZ0, CX1, CZ1 = S.CABLE_STATION                                # 75, -40, 91, -26
HX0, HZ0, HX1, HZ1 = S.POWER_HOUSE["box"]                           # 67, 20, 89, 42
G = S.GRAND_STAIR
LINK_X = (CX0 + CX1) // 2 + 0.5                                     # 83.5: the walk from the station to the axis
SUN = (S.SUNSET_PLATFORM["centre"][0] + 0.5, S.SUNSET_PLATFORM["centre"][1] + 0.5)
SUN_WALK = S.SUNSET_PLATFORM["radius"] - 3.5                        # 16.5: two cells in from the arc's rail

stretches = []


def stretch(sid, name):
    stretches.append({"id": sid, "name": name, "points": []})


def pt(x, y, z, node=None, look=None, views=None, hop=False):
    p = {"at": [x, y, z]}
    if hop:
        p["hop"] = True
    if node:
        p["node"] = node
    if look:
        p["look"] = [round(v, 2) for v in look]
    if views:
        p["views"] = views
    stretches[-1]["points"].append(p)


def edge(x, y, z, out, hop=False, node=None):
    pt(x, y, z, look=(x + out[0] * FAR, y + EYE, z + out[1] * FAR), views="fd", hop=hop, node=node)


def arc(deg):
    """A point of the sunset terrace's walk, two cells in from the rail: 0 its north end, 90 the west
    tip, 180 its south end; and the way out from the centre there."""
    a = math.radians(deg)
    out = (-math.sin(a), -math.cos(a))
    return round(SUN[0] + SUN_WALK * out[0], 1), round(SUN[1] + SUN_WALK * out[1], 1), out


# ---- A: the arrival ---------------------------------------------------------------------------------
stretch("A", "arrival: the station platform, the walk to the axis")
pt(S.V1["pos"][0], STATION, S.V1["pos"][2], node="the spawn, at the head of the track", look=S.V1["look_at"])
pt(LINK_X, STATION, S.V1["pos"][2])
pt(LINK_X, STATION, CZ1 - 1.5, node="the head of the steps on the station's south side")
pt(LINK_X, LOW, CZ1 + 1.5)
pt(LINK_X, LOW, -10.5, node="the walk from the station comes into the forecourt")
pt(LINK_X, LOW, AXIS, node="the walk from the station meets the axis")
pt(LX1 - 1.5, LOW, AXIS, node="the east end of the axis, at the rail")

# ---- B: the axis and the grand stair ------------------------------------------------------------------
stretch("B", "the axis and the grand stair")
pt(79.5, LOW, AXIS)
pt(G["x1"] + 2.5, LOW, AXIS, node="the foot of the grand stair")
pt(G["x1"] + 0.5, LOW, AXIS)
pt(66.5, S.stair_top(66), AXIS, node="half way up the stair", views="flrb")
pt(TX1 + 0.5, UP, AXIS, node="the head of the stair")

# ---- C: the front court --------------------------------------------------------------------------------
stretch("C", "the front court: axis, meridian, the foot of the front")
pt(IN_E, UP, AXIS, node="on the terrace at the head of the stair (the place of V2)")
pt(45.5, UP, AXIS)
pt(MX + 3, UP, AXIS, node="before the armillary, on the axis")
pt(MX + 3, UP, -6.5)
pt(MX, UP, -10.5)
pt(MX, UP, S.MERIDIAN_HUT["door"][1] + 1.5, node="before the meridian hut's door")
pt(MX - 7, UP, S.MERIDIAN_HUT["door"][1] + 1.5)                     # clear of the hut's corner
pt(FOOT_X, UP, -28.5, node="the north-west corner of the court, at the foot of the front")
pt(FOOT_X, UP, -7.5)
pt(FOOT_X + 1, UP, AXIS, node="before the main door")
pt(FOOT_X, UP, 7.5)
pt(FOOT_X, UP, 28.5, node="the south-west corner of the court, at the foot of the front")
pt(MX, UP, 28.5, node="the south end of the meridian")
pt(MX, UP, 10.5)
pt(MX - 3, UP, 6.5)
pt(MX - 3, UP, AXIS, node="between the armillary and the door")

# ---- D: the north side ----------------------------------------------------------------------------------
PAD = S.MAST_PAD["box"]                                             # 17, -46, 29, -39
WS = S.WEATHER_STATION                                              # box -2, -49, 8, -43; feet -4
stretch("D", "the north side: the mast pad, the weather station")
pt(IN_E, UP, IN_N, node="the north-east corner of the terrace")
edge(50.5, UP, IN_N, N)
edge(42.5, UP, IN_N, N)
edge(34.5, UP, IN_N, N)
# the pad: the mast's base stands in its middle (x 21..25, z -42..-38), a walk three wide round it
PAD_E, PAD_W, PAD_N = PAD[2] - 2.5, PAD[0] + 2.5, PAD[1] + 1.5      # 26.5, 19.5, -44.5
pt(PAD_E, UP, IN_N)
pt(PAD_E, UP, -40.5, node="on the mast pad, beside the mast's base")
pt(PAD_E, UP, PAD_N, node="the mast pad, its north-east corner", look=(PAD_E, UP + EYE, PAD_N - FAR))
pt(PAD_W, UP, PAD_N, node="the mast pad, its north-west corner", look=(PAD_W - FAR, UP + EYE, PAD_N))
pt(PAD_W, UP, IN_N)
edge(12.5, UP, IN_N, N)
# the neck to the weather station: level through the gap, then a block down every row
pt(3.5, UP, IN_N, node="the gap in the rail: the way down to the weather station")
pt(3.5, UP, -38.5)
pt(3.5, -2, -40.5)
pt(3.5, WS["feet"], WS["box"][3] + 0.5)
pt(4.5, WS["feet"], -45.5, node="the weather station's shelf")
edge(4.5, WS["feet"], WS["box"][1] + 1.5, N)
edge(WS["box"][0] + 1.5, WS["feet"], -44.5, W, hop=True)
edge(WS["box"][2] - 1.5, WS["feet"], -44.5, E, hop=True)
edge(-2.5, UP, IN_N, N, hop=True)
pt(IN_W, UP, IN_N, node="the north-west corner of the terrace")

# ---- E: the west side -----------------------------------------------------------------------------------
WT = S.WATER_TOWER                                                  # box -21, -35, -13, -27; feet -2
stretch("E", "the west side: the water tower, the sunset terrace")
# the neck to the water tower: two blocks down in two columns; the tower stands on four legs in
# the shelf's middle (x -19..-15, z -33..-29), a walk round it
WT_E, WT_W, WT_N, WT_S = WT["box"][2] + 0.5, WT["box"][0] + 1.5, WT["box"][1] + 1.5, WT["box"][3] - 0.5
pt(IN_W, UP, -31.5, node="the gap in the rail: the way down to the water tower")
pt(TX0 - 0.5, UP, -31.5)
pt(WT_E, WT["feet"], -31.5)                                         # -12.5: the shelf's east walk
pt(WT_E, WT["feet"], WT_N)
pt(WT_W, WT["feet"], WT_N, node="the water tower's shelf, its north-west corner",
   look=(WT_W - FAR, WT["feet"] + EYE, WT_N))
pt(WT_W, WT["feet"], WT_S, node="the water tower's shelf, its south-west corner",
   look=(WT_W - FAR, WT["feet"] + EYE, WT_S + FAR))
pt(WT_E, WT["feet"], WT_S)
pt(WT_E, WT["feet"], -31.5)
pt(-16.5, WT["feet"], -31.5, node="under the water tower")
edge(IN_W, UP, -26.5, W, hop=True)
pt(IN_W, UP, -17.5, node="the north end of the sunset terrace's arc")
for deg in (25, 50, 75):
    x, z, out = arc(deg)
    edge(x, UP, z, out)
TIP = SUN[0] - S.SUNSET_PLATFORM["radius"] + 2.0                    # -26.5: a cell in from the rail at the tip
pt(TIP, UP, AXIS, node="the sunset terrace's west tip", look=(TIP - FAR, UP + EYE, AXIS), views="flrbd")
pt(-19.5, UP, AXIS, hop=True)
pt(TX0 - 1.5, UP, AXIS, node="before the west door")
for deg in (105, 130, 155):
    x, z, out = arc(deg)
    edge(x, UP, z, out, hop=deg == 105)
pt(IN_W, UP, 17.5, node="the south end of the sunset terrace's arc")
edge(IN_W, UP, 26.5, W)
pt(IN_W, UP, IN_S, node="the south-west corner of the terrace")

# ---- F: the south side ----------------------------------------------------------------------------------
SL = S.SOUTH_LOOKOUT                                                # box 40, 48, 50, 56; feet -5
stretch("F", "the south side: the south lookout")
for x in (-2.5, 5.5, 13.5, 21.5, 29.5, 37.5):
    edge(x, UP, IN_S, SO)
# the neck to the lookout: level through the gap, then a block down every two rows
pt(45.5, UP, IN_S, node="the gap in the rail: the way down to the south lookout")
pt(45.5, UP, 39.5)
pt(45.5, -2, 43.5)
pt(45.5, -4, 47.5)
pt(45.5, SL["feet"], SL["box"][1] + 0.5)
pt(S.V11["pos"][0], SL["feet"], S.V11["pos"][2], node="the south lookout (the place of V11)")
edge(SL["box"][2] - 1.5, SL["feet"], 51.5, E)
pt(45.5, SL["feet"], SL["box"][3] - 0.5, node="the lookout's prow",
   look=(45.5, SL["feet"] + EYE, SL["box"][3] + FAR), views="flrbd")
edge(SL["box"][0] + 2.5, SL["feet"], 51.5, W)
edge(52.5, UP, IN_S, SO, hop=True)
pt(IN_E, UP, IN_S, node="the south-east corner of the terrace")

# ---- G: the terrace's east lip --------------------------------------------------------------------------
stretch("G", "the terrace's east lip, over the lower platform")
pt(54.5, UP, 33.5, node="the head of the pipe bridge")
for z in (29.5, 21.5, 13.5):
    edge(IN_E, UP, z, E)
pt(IN_E, UP, G["z1"] + 1.5, node="the lip beside the stair's south pedestal")
pt(IN_E, UP, G["z0"] - 0.5, node="the lip beside the stair's north pedestal", hop=True)
for z in (-13.5, -21.5, -29.5):
    edge(IN_E, UP, z, E)

# ---- H: the lower platform, south -----------------------------------------------------------------------
ALLEY = (LX0 + HX0) / 2.0 - 0.5                                     # 63.5: between the retaining wall and the house
stretch("H", "the lower platform, south: the way to the works, round the power house")
pt(74.5, LOW, 6.5)
pt(74.5, LOW, HZ0 - 1.5, node="before the power house's door")
pt(ALLEY + 1, LOW, HZ0 - 1.5)
pt(ALLEY, LOW, 26.5)
pt(ALLEY, LOW, 31.5, node="in the alley, under the pipe bridge")
pt(ALLEY, LOW, 37.5)
pt(LX0 + 1.5, LOW, LZ1 - 1.5, node="the south-west corner of the lower platform",
   look=(LX0 + 1.5 - FAR, LOW + EYE, LZ1 - 1.5 + FAR))
# behind the house there is the kerb alone, a row wide: the house's south wall on one side, the
# fall on the other (site/lowerplatform: no ground to rail off)
pt(HX0 + 1.5, LOW, LZ1 + 0.5, node="the kerb behind the power house, its west end", hop=True,
   look=(HX0 + 1.5 + FAR, LOW + EYE, LZ1 + 0.5))
for x in (74.5, 80.5, 86.5):
    edge(x, LOW, LZ1 + 0.5, SO)
pt(LX1 - 0.5, LOW, LZ1 - 1.5, node="the south-east corner of the lower platform", hop=True,
   look=(LX1 - 0.5 + FAR, LOW + EYE, LZ1 - 1.5 + FAR))
for z in (35.5, 27.5):
    edge(LX1 - 0.5, LOW, z, E)
pt(LX1 - 0.5, LOW, HZ0 - 1.5, node="the north-east corner of the power house")
edge(LX1 - 0.5, LOW, 10.5, E)

# ---- I: the lower platform, north, and back -------------------------------------------------------------
stretch("I", "the lower platform, north: its edges, the wall's foot, back to the station")
edge(LX1 - 0.5, LOW, -7.5, E)
edge(LX1 - 0.5, LOW, -15.5, E)
pt(LX1 - 0.5, LOW, CZ1 + 2.5, node="under the station's bay, on the east edge")
edge(CX0 - 2.5, LOW, LZ0 + 1.5, N, hop=True)
pt(LX0 + 1.5, LOW, LZ0 + 1.5, node="the north-west corner of the lower platform",
   look=(LX0 + 1.5 - FAR, LOW + EYE, LZ0 + 1.5 - FAR))
# along the retaining wall, a column clear of its buttresses (x 61..62)
pt(LX0 + 2.5, LOW, -36.5)
pt(LX0 + 2.5, LOW, -20.5)
pt(LX0 + 2.5, LOW, G["z0"] - 3.5, node="the foot of the retaining wall, north of the stair")
pt(CX0 - 1.5, LOW, S.V1["pos"][2], node="the foot of the station's west steps", hop=True)
pt(CX0 + 2.5, STATION, S.V1["pos"][2])
pt(S.V1["pos"][0], STATION, S.V1["pos"][2], node="back at the spawn", views="fb")

route = {"prefix": "out", "stretches": stretches}
path = os.path.join(HERE, "out-route.json")
with open(path, "w", encoding="utf-8", newline="\n") as fh:
    fh.write('{"prefix": "out",\n "stretches": [\n')
    for n, s in enumerate(stretches):
        fh.write('  {"id": %s, "name": %s,\n   "points": [\n' % (json.dumps(s["id"]), json.dumps(s["name"])))
        fh.write(",\n".join("    " + json.dumps(p) for p in s["points"]))
        fh.write("\n   ]}" + ("," if n + 1 < len(stretches) else "") + "\n")
    fh.write(" ]}\n")
print(f"{os.path.relpath(path)}: {len(stretches)} stretches, {sum(len(s['points']) for s in stretches)} points")
